"""Validate saved result 50 and prepare one bounded candidate-credit trace.

check, plan and prepare-status are offline. collect-origin is a LIVE command
making one request through the existing capture code; prepare-status only prints
the next manual request for the same candidate after validating its saved origin.
No lookback queries or recursive counterparty-history collection are supported.
"""

import argparse
import base64
import importlib.util
import json
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("withdrawal_trace", ROOT / "analysis/15_trace_frontend_transfer_origin.py")
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)
c = trace.capture
d = trace.decoder
SOURCE = ROOT / "results/50_intents_internal_account_event_candidates_2026-09-23.json"
SOURCE_HASH = "d4f613697c659fb0ae9afdce8bb357d16ef8c3a0dcf6448f728a02de262468e1"
SUMMARY = ROOT / "results/51_internal_credit_validation_2026-09-23.json"
REQUEST = ROOT / "results/52_internal_credit_origin_request_2026-09-23.json"
OUTPUT_ROOT = ROOT / "results/internal_credit_origin_trace_2026-09-23"
ACCOUNT = "a8c56ebbdabc6b6709d4f946d54679db1e4006f5eeb6b3d49c897c86c70ba6cd"
KEY = "ed25519:CMp71Rp8hx8BimTnGZ2BuVkd92Eak2oYSaW5Fqek9a5r"
ASSET = "nep141:wrap.near"
ANCHOR = "Fnt2xfvuLebRXp4cSupgdHbdeDmDXaWRkUTaJQctwjTK"
ANCHOR_HASH = "5RCDGcbp8sZ4PtgD3U72GNmtMPPcg9d5AwKZTq5VQg6s"
ORIGIN = ROOT / "results/frontend_origin_trace_2026-09-23/20261106T211752Z_97d93531faa2"
STATUS = ROOT / "results/frontend_origin_trace_2026-09-23/20261106T212650Z_c1faefff5ad8"
E, S = "event_outcome_record.", "summary_record."


def exact(value):
    c.money(value, "event amount")
    return int(value)


def events(source):
    """Decode only observed event versions; preserve log/data/token offsets."""
    logs = source["logs"]
    c.require(isinstance(logs, dict) and set(logs) == {"list"}
              and isinstance(logs["list"], list), "Unsupported BigQuery log encoding")
    result, changes = [], []
    supported = {("dip4", "0.3.0", "transfer"), ("dip4", "0.3.0", "native_withdraw"),
                 ("dip4", "0.3.1", "intents_executed"), ("nep245", "1.0.0", "mt_transfer"),
                 ("nep245", "1.0.0", "mt_burn")}
    for offset, item in enumerate(logs["list"]):
        c.require(isinstance(item, dict) and set(item) == {"element"}
                  and isinstance(item["element"], str) and item["element"].startswith("EVENT_JSON:"),
                  "Unsupported or unavailable log entry")
        raw = item["element"]
        event = c.decode(raw[len("EVENT_JSON:"):])
        c.require((event["standard"], event["version"], event["event"]) in supported
                  and isinstance(event["data"], list), "Unsupported event schema/version")
        result.append({"log_index": offset, "raw_log": raw, "decoded": event})
        for position, data in enumerate(event["data"]):
            if event["standard"] == "dip4":
                c.account_id(data["account_id"])
                c.require(isinstance(data["intent_hash"], str) and data["intent_hash"], "Missing intent hash")
                if event["event"] == "transfer":
                    c.account_id(data["receiver_id"])
                    c.require(isinstance(data["tokens"], dict), "Missing token map")
                    for amount in data["tokens"].values():
                        exact(amount)
                elif event["event"] == "native_withdraw":
                    c.account_id(data["receiver_id"])
                    exact(data["amount"])
                else:
                    c.require(len(base64.b64decode(data["nonce"], validate=True)) == 32, "Invalid intent nonce")
                continue  # Intent logs contextualize, rather than duplicate, MT amounts.
            ids, amounts = data["token_ids"], data["amounts"]
            c.require(isinstance(ids, list) and isinstance(amounts, list) and len(ids) == len(amounts)
                      and ids and len(set(ids)) == len(ids), "Unequal/duplicate token/amount arrays")
            if event["event"] == "mt_transfer":
                old, new = c.account_id(data["old_owner_id"]), c.account_id(data["new_owner_id"])
                direction = int(new == ACCOUNT) - int(old == ACCOUNT)
            else:
                old, new = c.account_id(data["owner_id"]), None
                direction = -int(old == ACCOUNT)
            for token_index, (asset, amount) in enumerate(zip(ids, amounts)):
                value = exact(amount)
                c.require(isinstance(asset, str) and asset, "Missing asset ID")
                if direction:
                    changes.append({"log_index": offset, "data_index": position, "token_index": token_index,
                        "asset": asset, "amount_base_units": amount, "signed_change_base_units": str(direction * value),
                        "old_owner_id": old, "new_owner_id": new, "memo": data.get("memo"),
                        "mechanism": event["event"], "economic_classification": "UNCLASSIFIED_INTERNAL_ACTIVITY"})
    return result, changes


def validate_export(rows):
    c.require(isinstance(rows, list) and rows, "Expected result-row array")
    summaries = [r for r in rows if r.get("row_kind") == "SUMMARY"]
    details = [r for r in rows if r.get("row_kind") == "OUTCOME_CANDIDATE"]
    c.require(len(summaries) == 1 and len(rows) == 1 + len(details), "Missing/duplicate SUMMARY or unexpected rows")
    summary, records, receipt_ids = summaries[0], [], set()
    counts = Counter(output_candidate_rows=len(details))
    for row in rows:
        c.require(row["observation_date"] == d.DATE, "Wrong observation date")
        c.require(set(row) == set(summary), "Export column schema differs between rows")
        other = E if row["row_kind"] == "SUMMARY" else S
        c.require(all(v is None for k, v in row.items() if k.startswith(other)), "Cross-kind nonnull fields")
    mapping = {"block_date": "block_date", "receipt_id": "receipt_id", "executor_account_id": "executor_account_id",
        "status": "status", "source_block_height_text": "block_height", "source_timestamp_nanoseconds_text": "block_timestamp",
        "source_block_hash": "block_hash", "executed_in_block_hash": "executed_in_block_hash",
        "source_chunk_hash": "chunk_hash", "source_shard_id_text": "shard_id", "source_index_in_chunk_text": "index_in_chunk"}
    for row in details:
        source = c.decode(row[E + "source_row_json"])
        c.require(source["receipt_id"] not in receipt_ids, "Duplicate receipt identity")
        receipt_ids.add(source["receipt_id"])
        for derived, original in mapping.items():
            c.require(row[E + derived] == str(source[original]), f"Source identity mismatch: {derived}")
        c.require(source["block_date"] == d.DATE and source["executor_account_id"] == "intents.near",
                  "Wrong source date/executor")
        for field in ("receipt_id", "block_hash", "executed_in_block_hash", "chunk_hash"):
            trace.validate_origin({"transaction_hash": source[field], "sender_account_id": "intents.near"})
        c.require(row[E + "economic_classification"] == "UNCLASSIFIED_INTERNAL_ACTIVITY", "Unsupported economic label")
        c.require(d.count(row[E + "same_day_receipt_rows"]) == 1, "Duplicate source diagnostic")
        utc = d.timestamp(source["block_timestamp_utc"])
        c.require(utc == d.timestamp(row[E + "block_timestamp_utc"]), "Timestamp fields disagree")
        for field in ("block_height", "shard_id", "index_in_chunk"):
            c.require(type(source[field]) is int and source[field] >= 0, "Invalid ordering integer")
        seconds, fraction = divmod(d.count(source["block_timestamp"]), 10**9)
        c.require(utc == datetime.fromtimestamp(seconds, timezone.utc).replace(microsecond=fraction // 1000),
                  "Nanosecond timestamp disagrees")
        logs = c.decode(row[E + "source_logs_json"])
        c.require(logs == source["logs"], "Retained log representations disagree")
        checks = {"is_known_withdrawal_anchor": source["receipt_id"] == ANCHOR,
            "account_text_in_logs": ACCOUNT in row[E + "source_logs_json"],
            "public_key_text_in_logs": KEY in row[E + "source_logs_json"],
            "target_asset_text_in_logs": ASSET in row[E + "source_logs_json"],
            "app_fee_text_in_logs": "APP_FEE" in row[E + "source_logs_json"]}
        for key, value in checks.items():
            c.require(row[E + key] == str(value).lower(), f"Diagnostic flag mismatch: {key}")
        c.require(checks["account_text_in_logs"] or checks["public_key_text_in_logs"] or checks["is_known_withdrawal_anchor"],
                  "Row does not satisfy SQL selection")
        counts[{"SUCCESS_VALUE": "success_value_candidates", "SUCCESS_RECEIPT_ID": "success_receipt_id_candidates",
                "FAILURE": "failure_candidates"}[source["status"]]] += 1
        if checks["is_known_withdrawal_anchor"]:
            counts["observed_withdrawal_anchor_rows"] += 1
            counts["anchor_rows_matching_saved_rpc_identifiers"] += int(source["block_hash"] == source["executed_in_block_hash"]
                == ANCHOR_HASH and source["status"] == "SUCCESS_VALUE")
        decoded, changes = events(source)
        records.append({"receipt_id": source["receipt_id"], "block_height": source["block_height"],
            "block_hash": source["block_hash"], "executed_in_block_hash": source["executed_in_block_hash"],
            "chunk_hash": source["chunk_hash"], "shard_id": source["shard_id"], "index_in_chunk": source["index_in_chunk"],
            "timestamp_nanoseconds": source["block_timestamp"], "timestamp_utc": source["block_timestamp_utc"],
            "status": source["status"], "child_receipt_ids": [x["element"] for x in source["outcome_receipt_ids"]["list"]],
            "events": decoded, "internal_changes": changes})
    counts["distinct_candidate_receipt_ids"] = len(receipt_ids)
    for name in ("output_candidate_rows", "distinct_candidate_receipt_ids", "candidates_with_duplicate_receipt_keys",
                 "candidates_with_invalid_identity_or_status", "candidates_without_available_ordering_fields",
                 "success_value_candidates", "success_receipt_id_candidates", "failure_candidates",
                 "observed_withdrawal_anchor_rows", "anchor_rows_matching_saved_rpc_identifiers"):
        c.require(d.count(summary[S + name]) == counts[name], f"Summary/detail mismatch: {name}")
    c.require(counts["observed_withdrawal_anchor_rows"] == counts["anchor_rows_matching_saved_rpc_identifiers"] == 1,
              "Known withdrawal anchor unavailable/ambiguous")
    c.require(d.count(summary[S + "observed_partition_outcome_rows"])
              >= d.count(summary[S + "observed_intents_outcome_rows"]) >= len(details), "Invalid partition counts")
    for name in ("unavailable_executor_rows", "intents_rows_without_available_logs"):
        c.require(d.count(summary[S + name]) == 0, "Reported selection coverage unavailable")
    for name in ("opening_internal_balance", "verified_fee_credit_amount", "withdrawal_revenue_attribution"):
        c.require(summary[S + name] is None, "Unsupported balance/fee attribution in summary")
    c.require(summary[S + "discovery_check"] == "OBSERVED_CANDIDATES_REQUIRE_OFFLINE_EVENT_VALIDATION",
              "Unexpected discovery status")
    return {k.removeprefix(S): v for k, v in summary.items() if k.startswith(S)}, records


def report():
    raw = SOURCE.read_bytes()
    c.require(c.sha256(raw) == SOURCE_HASH, "Result 50 changed; review input first")
    summary, records = validate_export(c.decode(raw))
    prior = trace.recorded_origin(ORIGIN)
    rpc = c.recorded(STATUS, trace.status_request(prior))
    trace.validate_status_identity(rpc, prior)
    anchor = next(r for r in records if r["receipt_id"] == ANCHOR)
    canonical = next(r for r in rpc["receipts_outcome"] if r["id"] == ANCHOR)
    c.require([e["raw_log"] for e in anchor["events"]] == canonical["outcome"]["logs"]
              and anchor["block_hash"] == canonical["block_hash"]
              and anchor["child_receipt_ids"] == canonical["outcome"]["receipt_ids"],
              "Anchor differs from canonical capture")
    # These two saved observations each have one monetary intent and one MT
    # movement. Verify the redundant representations without counting both.
    for record in records:
        contexts = [data for e in record["events"] if e["decoded"]["standard"] == "dip4"
                    and e["decoded"]["event"] in ("transfer", "native_withdraw") for data in e["decoded"]["data"]]
        executed = [data for e in record["events"] if e["decoded"]["event"] == "intents_executed"
                    for data in e["decoded"]["data"]]
        c.require(len(contexts) == len(record["internal_changes"]) == 1, "Ambiguous monetary event representations")
        context, change = contexts[0], record["internal_changes"][0]
        c.require(sum((x["account_id"], x["intent_hash"]) == (context["account_id"], context["intent_hash"])
                      for x in executed) == 1, "Missing/ambiguous intent execution event")
        amount = context["tokens"][ASSET] if "tokens" in context else context["amount"]
        c.require(amount == change["amount_base_units"] and change["asset"] == ASSET
                  and context["account_id"] == change["old_owner_id"], "DIP4 and NEP245 representations disagree")
        if change["mechanism"] == "mt_transfer":
            c.require(context["receiver_id"] == change["new_owner_id"], "Transfer receiver representations disagree")
        else:
            c.require(amount == trace.target()["amount_yoctonear"], "Withdrawal amount differs from saved native payout")
    c.require(d.count(summary["observed_partition_outcome_rows"]) == d.count(c.decode(d.SOURCE.read_bytes())[0][
        "summary_record.observed_outcome_partition_rows"]), "Saved partition counts disagree with result 47")
    candidates = []
    for record in records:
        for change in record["internal_changes"]:
            if (change["asset"] == ASSET and int(change["signed_change_base_units"]) > 0
                    and record["status"] == "SUCCESS_VALUE"
                    and record["block_hash"] == record["executed_in_block_hash"]
                    and record["block_height"] < anchor["block_height"]
                    and int(record["timestamp_nanoseconds"]) < int(anchor["timestamp_nanoseconds"])):
                candidates.append({**{k: v for k, v in record.items() if k not in ("events", "internal_changes")}, **change})
    c.require(len(candidates) == 1, "Expected exactly one unambiguous pre-debit credit; no automatic selection")
    selected = candidates[0]
    total = sum(int(x["signed_change_base_units"]) for r in records if r["status"] == "SUCCESS_VALUE"
                for x in r["internal_changes"] if x["asset"] == ASSET)
    paths = {SOURCE, ROOT / "sql/40_intents_internal_account_event_candidates.sql", d.SOURCE, d.OUTPUT, trace.REQUEST,
             Path(__file__), Path(trace.__file__), Path(d.__file__), Path(c.__file__)}
    paths.update(p for directory in (ORIGIN, STATUS) for p in directory.rglob("*") if p.is_file())
    inputs = {str(p.relative_to(ROOT)): {"sha256": c.sha256(p.read_bytes()), "bytes": p.stat().st_size} for p in sorted(paths)}
    return {"input_hashes": inputs, "derivation_method": "Validate dotted export and retained JSON; decode only supported event versions; integer u128 amounts; count NEP245 movements once and use DIP4 logs as context; compare anchor to saved RPC.",
        "summary_validation": summary, "decoded_records": records, "selected_credit": selected,
        "comparison": {"amount_near": d.near(exact(selected["amount_base_units"])),
            "blocks_before_debit": anchor["block_height"] - selected["block_height"],
            "nanoseconds_before_debit": str(int(anchor["timestamp_nanoseconds"]) - int(selected["timestamp_nanoseconds"])),
            "observed_selected_movements_net_base_units": str(total),
            "net_interpretation": "Only selected logged movements; no opening/closing balance or economic reconciliation."},
        "attribution": {"verified_fee_credit_amount": None, "withdrawal_revenue_origin": None,
            "classification": "UNCLASSIFIED_INTERNAL_TRANSFER_CREDIT", "memo": selected["memo"],
            "remaining_question": "What mechanism generated this credit, and does independent historical configuration establish its fee origin?"},
        "boundary": {"selected_credit_receipts": 1, "additional_lookback_days_planned": 0,
            "stop": "After this one credit's origin/transaction-status trace, consolidate and move to returning-account activity. No counterparty-history recursion or 22 September query is prepared."},
        "limitations": ["Reported global partition diagnostics describe observed source records, not independently established completeness.",
            "Exact amount equality and temporal precedence do not establish fee origin or allocation within commingled balances.",
            "The internal account's fee-recipient identity and opening balance remain unverified; no burn/buyback claim is established."],
        "priority3_preparation": "Result 11 saves cohort counts, not membership IDs; results 13/36 save network spending, not returner spending. Design cohort-specific success and cost measurements, separating initial-receipt success from downstream settlement and submission dates from execution dates."}


def request():
    return {"jsonrpc": "2.0", "id": "internal-credit-origin", "method": "EXPERIMENTAL_receipt_to_tx",
            "params": {"receipt_id": report()["selected_credit"]["receipt_id"]}}


def preflight():
    document = report()
    c.require(SUMMARY.read_bytes() == c.json_bytes(document), "Derived summary does not reproduce")
    c.require(REQUEST.read_bytes() == c.json_bytes(request()), "Prepared candidate request differs")
    return document


def origin_saved(directory):
    preflight()
    manifest = c.decode((directory / "run.json").read_bytes())
    c.require(manifest.get("endpoint") == c.ENDPOINT and manifest.get("request_count") == 1
              and manifest.get("request") == request(), "Wrong candidate-origin manifest")
    c.require(len(list(directory.glob("*.metadata.json"))) == 1, "Expected one origin capture")
    for relative, expected in manifest["input_hashes"].items():
        path = (ROOT / relative).resolve()
        c.require(path.is_relative_to(ROOT), "Input outside repository")
        raw = path.read_bytes()
        c.require(c.sha256(raw) == expected["sha256"] and len(raw) == expected["bytes"], "Changed origin prerequisite")
    return trace.validate_origin(c.recorded(directory, request()))


def collect_origin(output_root=OUTPUT_ROOT, transport=None, pause=None):
    document = preflight()
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    inputs = {**document["input_hashes"], **{str(p.relative_to(ROOT)): {"sha256": c.sha256(p.read_bytes()),
        "bytes": p.stat().st_size} for p in (SUMMARY, REQUEST)}}
    c.write_new(directory / "run.json", c.json_bytes({"endpoint": c.ENDPOINT, "created_at": c.utc_now(),
        "request_count": 1, "request": request(), "input_hashes": inputs,
        "spacing_seconds": c.SPACING_SECONDS, "connect_timeout_seconds": c.CONNECT_TIMEOUT,
        "request_timeout_seconds": c.REQUEST_TIMEOUT, "boundary": document["boundary"]}))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    trace.validate_origin(c.capture(directory, request(), transport, pause))
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    check = subs.add_parser("check", help="OFFLINE: validate and emit derived JSON")
    check.add_argument("--output", type=Path)
    subs.add_parser("plan", help="OFFLINE: validate prepared inputs and print one request")
    subs.add_parser("collect-origin", help="LIVE: one candidate-origin request; no retries/scans/fallback")
    prepare = subs.add_parser("prepare-status", help="OFFLINE: validate origin capture and print same-candidate status request")
    prepare.add_argument("--origin-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            raw = c.json_bytes(report())
            if args.output:
                c.write_new(args.output, raw)
            else:
                print(raw.decode(), end="")
        elif args.command == "plan":
            preflight()
            print(json.dumps({"endpoint": c.ENDPOINT, "request": request(), "request_count": 1,
                "output_root": str(OUTPUT_ROOT), "boundary": report()["boundary"]}, indent=2))
        elif args.command == "collect-origin":
            collect_origin()
        else:
            print(c.json_bytes(trace.status_request(origin_saved(args.origin_dir))).decode(), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}. No automatic retry, lookback or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
