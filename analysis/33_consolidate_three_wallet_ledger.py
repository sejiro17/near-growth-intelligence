"""Consolidate saved native balances/flows and bounded asset evidence offline.

Default stdout; --output creates a new artifact exclusively. No source requests.
The 1csfundsadmin stock-flow difference stays unallocated; no residual tracing.
"""

import argparse
import base64
import importlib.util
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ledger_recovery", ROOT / "analysis/32_recover_wallet_historical_balances.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
b, c = r.b, r.c
require = c.require
RECOVERY = ROOT / "results/three_wallet_native_balance_recovery_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a_recovery_01"
BALANCES = ROOT / "results/78_three_wallet_native_balance_comparison_2026-08-24_to_2026-10-18.json"
RECOVERY_PLAN = ROOT / "results/79_three_wallet_balance_recovery_plan.json"
CLOSED = ROOT / "results/54_internal_credit_trace_consolidation_2026-09-23.json"
WITHDRAWAL_CAPTURE = ROOT / "results/frontend_origin_trace_2026-09-23/20261106T212650Z_c1faefff5ad8"


def closed_conversion(closed):
    """Project already traced conversion evidence; do not extend provenance."""
    payload = {"jsonrpc": "2.0", "id": "transfer-transaction-status", "method": "EXPERIMENTAL_tx_status",
               "params": {"sender_account_id": "intents.near", "tx_hash": "FFwediesLXUhqu8RwxeEpY2F6sRakHmysAjzwxZbXjXi", "wait_until": "FINAL"}}
    saved = c.recorded(WITHDRAWAL_CAPTURE, payload)
    require(saved["transaction"]["hash"] == payload["params"]["tx_hash"]
            and saved["final_execution_status"] == "FINAL" and saved["status"] == {"SuccessValue": ""}, "Closed withdrawal control changed")
    burns = []
    for outcome in saved["receipts_outcome"]:
        for index, log in enumerate(outcome["outcome"]["logs"]):
            if not log.startswith("EVENT_JSON:"):
                continue
            event = c.decode(log[len("EVENT_JSON:"):])
            if (event.get("standard"), event.get("event")) == ("nep245", "mt_burn"):
                burns.append({"receipt_id": outcome["id"], "log_index": index, "executor": outcome["outcome"]["executor_id"],
                              "status": outcome["outcome"]["status"], "raw_log": log, "event": event})
    require(len(burns) == 1 and burns[0]["status"] == {"SuccessValue": ""}, "Closed internal debit control changed")
    datum = burns[0]["event"]["data"][0]
    require(datum["owner_id"] == closed["credit_trace"]["internal_recipient"]
            and datum["token_ids"] == [closed["credit_trace"]["asset"]]
            and datum["amounts"] == [closed["credit_trace"]["amount_base_units"]], "Closed internal asset control changed")
    unwraps = []
    for receipt in saved["receipts"]:
        for action in receipt.get("receipt", {}).get("Action", {}).get("actions", []):
            call = action.get("FunctionCall")
            if call and receipt["receiver_id"] == "wrap.near" and call["method_name"] == "near_withdraw":
                text = base64.b64decode(call["args"], validate=True).decode("utf-8")
                args = c.decode(text)
                require(args["amount"] == datum["amounts"][0], "Closed unwrap amount changed")
                unwraps.append({"receipt_id": receipt["receipt_id"], "contract": receipt["receiver_id"],
                                "predecessor": receipt["predecessor_id"], "method": call["method_name"],
                                "raw_args_base64": call["args"], "args_utf8": text, "amount_base_units": args["amount"]})
    require(len(unwraps) == 1, "Closed unwrap control changed")
    return {"source_transaction_hash": payload["params"]["tx_hash"], "internal_debit": burns[0], "unwrap_request": unwraps[0],
            "closed_internal_credit": {k: closed["credit_trace"][k] for k in ("transaction_hash", "internal_sender", "internal_recipient", "asset", "amount_base_units", "mechanism")},
            "internal_owner_is_verified_native_wallet_alias": None,
            "mechanism": "SAVED_INTERNAL_ASSET_DEBIT_AND_UNWRAP_TO_NATIVE_WITHDRAWAL",
            "native_transfer_already_counted": True, "independently_measured_native_supply_burn": None,
            "verified_fee_origin": None, "verified_exchange_purchase": None,
            "capture_sources": [b.m.prior.fingerprint(WITHDRAWAL_CAPTURE/f'transfer-transaction-status.{suffix}') for suffix in ("request.json", "response.body", "metadata.json")]}


def inner_request(call, contract, method, encoded, context, proposal_id=None, action=None, description=None):
    text = base64.b64decode(encoded, validate=True).decode("utf-8")
    args = c.decode(text)
    require(isinstance(args, dict), "Nested action arguments are not an object")
    amount = args.get("amount")
    if method in {"mt_transfer", "mt_transfer_call", "ft_transfer", "ft_transfer_call"}:
        amount = b.sidecar.exact_u128(amount)
    return {"source_receipt_id": call["receipt_id"], "source_action_index": call["action_index"],
            "execution_timestamp_utc": call["execution_timestamp_utc"], "source_status": call["status"],
            "context": context, "contract": contract, "method": method, "raw_args_base64": encoded,
            "args_utf8": text, "args": args, "asset_id": args.get("token_id") if method.startswith("mt_") else contract,
            "amount_base_units": amount, "receiver_id": args.get("receiver_id"),
            "proposal_id": proposal_id, "proposal_action": action, "description_unverified": description,
            "economic_classification": "UNCLASSIFIED_ASSET_REQUEST", "execution_link": None}


def asset_requests(calls):
    requests = []
    for call in calls:
        method = call["method"]
        if method in {"mt_transfer", "mt_transfer_call", "ft_transfer", "ft_transfer_call"}:
            requests.append(inner_request(call, call["receiver"], method, call["args_base64"], "DIRECT_OBSERVED_CALL"))
        if method not in {"add_proposal", "act_proposal"}:
            continue
        proposal = call["args"].get("proposal", {})
        kind = proposal.get("kind", proposal)
        if "FunctionCall" not in kind:
            continue
        function = kind["FunctionCall"]
        for index, action in enumerate(function["actions"]):
            record = inner_request(call, function["receiver_id"], action["method_name"], action["args"],
                                   "PROPOSAL_REQUEST_ONLY", call["args"].get("id"), call["args"].get("action"), proposal.get("description"))
            record["nested_action_index"] = index
            matches = [child for child in calls if child["receipt_id"] in call["child_receipt_ids"]
                       and child["receiver"] == record["contract"] and child["method"] == record["method"]
                       and child["predecessor"] == call["receiver"] and child["args"] == record["args"]]
            require(len(matches) <= 1, "Ambiguous observed nested-action execution link")
            if matches:
                record["execution_link"] = {"receipt_id": matches[0]["receipt_id"], "status": matches[0]["status"],
                                             "basis": "DIRECT_OUTCOME_CHILD_ID_AND_EXACT_ACTION_ARGS"}
            requests.append(record)
    return requests


def wallet_rows(ledger, balance_report):
    accepted = [a for a in ledger["actions"] if a["accepted_local_native_amount"]]
    rows = []
    for state in balance_report["accounts"]:
        w = state["account_id"]
        sums = {}
        for scope in ("EXTERNAL_COUNTERPARTY", "BETWEEN_SELECTED_WALLETS", "SELF_MOVEMENT"):
            selected = [a for a in accepted if a["movement_scope"] == scope]
            sums[scope] = {"inflow_yocto": str(sum(int(a["amount_yocto"]) for a in selected if a["receiver"] == w)),
                           "outflow_yocto": str(sum(int(a["amount_yocto"]) for a in selected if a["predecessor"] == w))}
        inflow, outflow = (sum(int(v[k]) for v in sums.values()) for k in ("inflow_yocto", "outflow_yocto"))
        require(str(inflow) == state["successful_native_inflow_yocto"]
                and str(outflow) == state["successful_native_outflow_yocto"], "Wallet scope sums disagree")
        change = int(state["closing"]["combined_yocto"])-int(state["opening"]["combined_yocto"])
        residual = change-inflow+outflow
        require(str(change) == state["combined_balance_change_yocto"]
                and str(residual) == state["unexplained_stock_flow_difference_yocto"], "Wallet stock-flow arithmetic disagrees")
        rows.append({**state, "flow_scopes": sums, "difference_allocation": "UNALLOCATED",
                     "residual_driven_collection": "NONE"})
    return rows


def event_inventory(raw):
    seen, inventory = set(), Counter()
    for item in c.decode(raw):
        if item["row_kind"] != "ACTION":
            continue
        row = c.decode(item["record_json"])
        key = row["source_action"]["receipt_id"]
        if key in seen:
            continue
        seen.add(key)
        observations = row["outcome_audit"]["observations"]
        require(len(observations) == 1, "Cannot inventory ambiguous outcome logs")
        source = c.decode(observations[0]["source_outcome_row_json"])
        for log in b.sidecar.elements(source["logs"]):
            if log.startswith("EVENT_JSON:"):
                event = c.decode(log[len("EVENT_JSON:"):])
                inventory[(event.get("standard"), event.get("version"), event.get("event"))] += 1
    return [{"standard": k[0], "version": k[1], "event": k[2], "observed_log_count": v}
            for k, v in sorted(inventory.items())]


def report():
    balance = r.validate(RECOVERY)
    require(c.json_bytes(balance) == BALANCES.read_bytes(), "Result 78 does not reproduce")
    original = ROOT / c.decode(RECOVERY_PLAN.read_bytes())["original_run_dir"]
    require(c.json_bytes(r.audit(original)) == RECOVERY_PLAN.read_bytes(), "Result 79 does not reproduce")
    ledger = c.decode(b.sidecar.DECODED.read_bytes())
    side = c.decode(b.SIDECAR.read_bytes())
    calls = side["function_calls"]
    wallets = wallet_rows(ledger, balance)
    external = {k: ledger[k] for k in ("group_valid_external_inflow_subtotal_yocto", "group_valid_external_outflow_subtotal_yocto", "group_observed_external_net_yocto")}
    require(sum(int(w["flow_scopes"]["EXTERNAL_COUNTERPARTY"]["inflow_yocto"]) for w in wallets) == int(external["group_valid_external_inflow_subtotal_yocto"])
            and sum(int(w["flow_scopes"]["EXTERNAL_COUNTERPARTY"]["outflow_yocto"]) for w in wallets) == int(external["group_valid_external_outflow_subtotal_yocto"]), "Group external scopes disagree")
    closed = c.decode(CLOSED.read_bytes())
    require(closed["closure"]["fee_origin"] == "UNRESOLVED" and closed["closure"]["single_candidate_trace"] == "COMPLETE", "Closed provenance status changed")
    native_entries = [{"source_action_position_in_result75": index, **action} for index, action in enumerate(ledger["actions"]) if action["accepted_local_native_amount"]]
    withdrawal_id = "5z6sNxeEzHdQuU1P8j7o5DiTcLxXJdHj9nbFvX5H1wFK"
    withdrawal = [a for a in native_entries if a["receipt_id"] == withdrawal_id]
    require(len(withdrawal) == 1 and withdrawal[0]["receiver"] == b.m.WALLETS[0]
            and withdrawal[0]["amount_near"] == closed["subsequent_withdrawal_comparison"]["amount_near"], "Closed withdrawal not represented exactly once in native ledger")
    sources = [b.m.SOURCE, b.sidecar.DECODED, b.SIDECAR, b.PLAN, BALANCES, RECOVERY_PLAN, CLOSED]
    return {"status": "CONSOLIDATED_OBSERVED_NATIVE_LEDGER_WITH_UNALLOCATED_DIFFERENCE_AND_PARTIAL_ASSET_EVIDENCE",
            "window": {"start_inclusive": "2026-08-24T00:00:00Z", "end_exclusive": "2026-10-19T00:00:00Z"},
            "native_wallets": wallets, "native_entries": native_entries, "native_coverage": ledger["source_summary"],
            "native_group": {**external, **{k: v for k, v in balance.items() if k.startswith("group_")}},
            "native_internal_transfers": side["between_wallet_paths"], "weekly_native_flow_observations": side["weekly_native_flows"],
            "weekly_stock_reconciliation": None, "boundary_qualification": balance["boundary_status"],
            "asset_layer": {"event_inventory_all_selected_receipts": event_inventory(b.m.SOURCE.read_bytes()),
                            "decoded_asset_requests": asset_requests(calls),
                            "observed_successful_internal_transfers": side["logged_internal_asset_transfers"],
                            "closed_saved_conversion_context": closed_conversion(closed),
                            "explicit_verified_exchange_purchase_records": [], "verified_purchase_amount": None,
                            "full_ft_mt_transfer_totals": None, "historical_ft_mt_opening_closing_balances": None,
                            "coverage": "Selected native predecessor/receiver receipts omit unrelated token contracts and relayed Verifier transfers; requests/memos are not settlement"},
            "historical_contract_evidence": [{"account_id": w["account_id"],
                 "opening_code_hash": w["opening"]["code_hash"], "closing_code_hash": w["closing"]["code_hash"],
                 "equal_endpoint_code_hashes": w["opening"]["code_hash"] == w["closing"]["code_hash"],
                 "observed_called_methods": sorted({a["method"] for a in calls if a["receiver"] == w["account_id"]}),
                 "wasm_to_source_version_match": None, "historical_policy_and_beneficial_ownership": None,
                 "intermediate_contract_or_configuration_changes": "NOT_ESTABLISHED_BY_ENDPOINTS"} for w in wallets],
            "closed_withdrawal_provenance": {"source": b.m.prior.fingerprint(CLOSED), "status": closed["closure"],
                 "mechanism": closed["credit_trace"]["mechanism"], "native_withdrawal_in_native_entries_not_added_again": True,
                 "native_receipt_id": withdrawal_id, "native_action_position_in_result75": withdrawal[0]["source_action_position_in_result75"],
                 "internal_burn_is_not_native_supply_destruction": True, "additional_collection": "NONE"},
            "verified_revenue_yocto": None, "verified_buybacks_yocto": None, "actual_supply_burn_yocto": None,
            "remaining_data_dependencies": [
                "Complete execution-success-qualified NEP-141 and NEP-245 event/receipt coverage where wallet IDs occur in arguments/logs rather than native counterparties",
                "Asset metadata/decimals, historical asset opening/closing balances and verified internal-account associations",
                "Historical deployed WASM/source match and policy/configuration changes, fee-recipient role and fee-source attribution",
                "Explicit exchange order/fill or signed settlement records with assets paid/received, identities and final callbacks",
                "Native adjustment and canonical edge coverage; the 1cs residual remains unallocated without further collection solely to explain it"],
            "sources": [b.m.prior.fingerprint(p) for p in sources],
            "derivation": [b.m.prior.fingerprint(p) for p in (Path(__file__), Path(r.__file__), Path(b.__file__), Path(b.sidecar.__file__), Path(b.m.__file__), Path(b.m.prior.__file__))]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = c.json_bytes(report())
        if args.output:
            c.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No source requests made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
