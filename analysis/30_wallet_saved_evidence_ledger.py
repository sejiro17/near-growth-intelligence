"""Reproduce result 75 and prepare a ledger sidecar from saved result 74 only.

Default stdout; --output creates a new file exclusively. No source requests.
Native flows, proposal requests and logged internal assets are separate layers.
"""

import argparse
import base64
import contextlib
import importlib.util
import io
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("native_candidates", ROOT / "analysis/29_wallet_native_flow_candidates.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
require, decode = m.require, m.decode
DECODED = ROOT / "results/75_three_wallet_native_flows_decoded_2026-08-24_to_2026-10-18.json"


def elements(value):
    """Only the list/element encoding actually retained by this export."""
    require(isinstance(value, dict) and set(value) == {"list"} and isinstance(value["list"], list), "Unsupported nested list encoding")
    result = []
    for item in value["list"]:
        require(isinstance(item, dict) and set(item) == {"element"} and isinstance(item["element"], str), "Invalid nested list element")
        result.append(item["element"])
    return result


def exact_u128(value):
    require(isinstance(value, str) and value.isascii() and value.isdigit()
            and 1 <= len(value) <= 39 and int(value) < 2**128, "Invalid exact u128 amount")
    return value


def events(logs):
    result = []
    for log_index, raw in enumerate(logs):
        if not raw.startswith("EVENT_JSON:"):
            continue
        event = decode(raw[len("EVENT_JSON:"):])
        if (event.get("standard"), event.get("version"), event.get("event")) != ("nep245", "1.0.0", "mt_transfer"):
            continue
        require(isinstance(event["data"], list), "Invalid event data")
        for data_index, item in enumerate(event["data"]):
            tokens, amounts = item["token_ids"], item["amounts"]
            require(isinstance(tokens, list) and isinstance(amounts, list) and len(tokens) == len(amounts) > 0, "Mismatched event asset/amount arrays")
            require(all(isinstance(item[k], str) and item[k] for k in ("old_owner_id", "new_owner_id")), "Invalid event owners")
            for asset_index, (token, amount) in enumerate(zip(tokens, amounts)):
                require(isinstance(token, str) and token, "Invalid asset ID")
                result.append({"log_index": log_index, "data_index": data_index, "asset_index": asset_index,
                               "old_owner_id": item["old_owner_id"], "new_owner_id": item["new_owner_id"],
                               "asset_id": token, "amount_base_units": exact_u128(amount),
                               "raw_log": raw, "economic_classification": "UNCLASSIFIED_INTERNAL_ASSET_TRANSFER"})
    return result


def inspect_saved(raw, ledger):
    outcomes, calls = {}, []
    rows = [decode(r["record_json"]) for r in decode(raw) if r["row_kind"] == "ACTION"]
    for row in rows:
        a = row["source_action"]
        source = decode(a["source_row_json"])
        require(m.number(source["block_height"]) == m.number(a["source_block_height"])
                and m.stamp(source["block_timestamp_utc"]) == m.stamp(a["source_timestamp_utc"]), "Raw source height/time mismatch")
        audit = row["outcome_audit"]
        require(audit is not None and len(audit["observations"]) == 1, "Sidecar requires unique observed outcomes")
        observed = audit["observations"][0]
        original = decode(observed["source_outcome_row_json"])
        block = observed["execution_block_observations"][0]
        require(original["receipt_id"] == a["receipt_id"] and original["status"] == observed["status"]
                and original["executor_account_id"] == observed["executor_account_id"] == a["receiver"]
                and original["executed_in_block_hash"] == observed["executed_in_block_hash"] == block["block_hash"]
                and m.stamp(original["block_timestamp_utc"]) == m.stamp(observed["outcome_record_timestamp_utc"])
                and m.stamp(row["execution_timestamp_utc"]) == m.stamp(block["block_timestamp_utc"]), "Raw outcome identity/status/time mismatch")
        receipt = a["receipt_id"]
        require(receipt not in outcomes or outcomes[receipt]["raw"] == observed["source_outcome_row_json"], "Conflicting receipt outcomes")
        children = elements(original["outcome_receipt_ids"])
        require(len(set(children)) == len(children), "Duplicate child receipt IDs")
        logs = elements(original["logs"])
        outcomes[receipt] = {"raw": observed["source_outcome_row_json"], "children": children,
                             "logs": logs, "status": observed["status"]}
        if a["action_kind"] == "FUNCTION_CALL":
            args = decode(a["raw_args_scalar_text"])
            text = base64.b64decode(args["args_base64"], validate=True).decode("utf-8")
            call = {"receipt_id": receipt, "action_index": a["action_index"], "predecessor": a["predecessor"],
                    "receiver": a["receiver"], "method": args["method_name"], "args_base64": args["args_base64"],
                    "args_utf8": text, "args": decode(text), "attached_native_yocto": exact_u128(args["deposit"]),
                    "status": observed["status"], "execution_timestamp_utc": row["execution_timestamp_utc"],
                    "execution_block_hash": block["block_hash"], "execution_block_height": block["block_height"],
                    "child_receipt_ids": children, "logs": logs,
                    "economic_classification": "UNCLASSIFIED_ACTION_CANDIDATE"}
            calls.append(call)
    parents = defaultdict(list)
    for receipt, outcome in outcomes.items():
        for child in outcome["children"]:
            parents[child].append(receipt)
    by_receipt = defaultdict(list)
    for call in calls:
        by_receipt[call["receipt_id"]].append(call)
    paths = []
    for action in ledger["actions"]:
        if not (action["accepted_local_native_amount"] and action["movement_scope"] == "BETWEEN_SELECTED_WALLETS"):
            continue
        direct = parents[action["receipt_id"]]
        require(len(direct) <= 1, "Ambiguous observed native-transfer parent")
        parent_calls = by_receipt[direct[0]] if direct else []
        callbacks = [call for parent in direct for child in outcomes[parent]["children"]
                     for call in by_receipt[child] if call["method"] == "on_proposal_callback"]
        for call in parent_calls:
            if call["method"] == "act_proposal" and "Transfer" in call["args"].get("proposal", {}):
                transfer = call["args"]["proposal"]["Transfer"]
                require(transfer["token_id"] == "" and transfer["receiver_id"] == action["receiver"]
                        and exact_u128(transfer["amount"]) == action["amount_yocto"]
                        and call["receiver"] == action["predecessor"]
                        and call["status"] in {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID"}, "Linked proposal/transfer mismatch")
        paths.append({"transfer": action, "direct_observed_parent_receipt_ids": direct,
                      "parent_function_calls": parent_calls, "sibling_callbacks": callbacks,
                      "unobserved_direct_children": [child for parent in direct for child in outcomes[parent]["children"] if child not in outcomes],
                      "scope": "SUCCESSFUL_NATIVE_CHILD_NOT_COMPLETE_CHAIN_OR_VERIFIED_REVENUE_OR_BUYBACK"})
    assets = []
    for receipt, outcome in outcomes.items():
        for event in events(outcome["logs"]):
            matches = [c for c in by_receipt[receipt] if c["method"] == "mt_transfer"
                       and c["args"].get("receiver_id") == event["new_owner_id"]
                       and c["predecessor"] == event["old_owner_id"]
                       and c["args"].get("token_id") == event["asset_id"]
                       and c["args"].get("amount") == event["amount_base_units"]]
            require(len(matches) == 1 and outcome["status"] in {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID"}, "Event/request/success mismatch")
            assets.append({**event, "receipt_id": receipt, "matching_call": matches[0],
                           "separate_from_native_flow_totals": True})
    return {"observed_distinct_receipts": len(outcomes), "function_calls": calls,
            "method_counts": dict(Counter(c["method"] for c in calls)), "between_wallet_paths": paths,
            "logged_internal_asset_transfers": assets,
            "weekly_native_flows": weekly(ledger["actions"]),
            "limitations": ["Selected receipt graph is incomplete; unobserved children remain unresolved",
                            "Proposal creation is not linked to numeric proposal IDs by amount resemblance",
                            "Failed sibling callbacks do not undo a separately successful native child",
                            "No historical account-balance bridge or complete multi-asset ledger",
                            "Economic origin, ultimate ownership and completed buybacks remain unverified"]}


def weekly(actions):
    rows = []
    for i in range(8):
        start = m.START + timedelta(days=7*i)
        end = start + timedelta(days=6)
        selected = [a for a in actions if a["accepted_local_native_amount"] and start <= m.stamp(a["execution_timestamp_utc"]).date() <= end]
        rows.append({"week_start": str(start), "week_end": str(end), "accepted_action_count": len(selected),
                     "wallets": [{"account_id": w,
                                  "observed_inflow_yocto": str(sum(int(a["amount_yocto"]) for a in selected if a["receiver"] == w)),
                                  "observed_outflow_yocto": str(sum(int(a["amount_yocto"]) for a in selected if a["predecessor"] == w))}
                                 for w in m.WALLETS]})
    return rows


def report():
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        status = m.main([])
    require(status == 0 and stream.getvalue().encode() == DECODED.read_bytes(), "Result 75 does not reproduce")
    ledger = decode(stream.getvalue())
    require(ledger["saved_control_matches"] and not ledger["action_layer_coverage_unresolved"], "Observed action/control checks unresolved")
    result = inspect_saved(m.SOURCE.read_bytes(), ledger)
    result.update(status="VALIDATED_SAVED_NATIVE_ACTION_LAYER_AND_BOUNDED_MECHANISMS",
                  source_summary=ledger["source_summary"], wallets=ledger["wallets"],
                  verified_revenue_yocto=None, verified_buyback_yocto=None,
                  sources=[m.prior.fingerprint(p) for p in (m.SOURCE, DECODED)],
                  derivation=[m.prior.fingerprint(p) for p in (Path(__file__), Path(m.__file__), Path(m.prior.__file__), m.SQL)])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = m.prior.json_bytes(report())
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No source requests made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
