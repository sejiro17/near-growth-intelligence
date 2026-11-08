"""Offline attribution consolidation and one separately invoked block-time check.

Only collect-time accesses the network: one fixed block request, no retries.
"""

import argparse
import base64
import csv
import fcntl
import importlib.util
import json
import ssl
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sweat_trace", ROOT / "analysis/40_trace_sweat_relayer.py")
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)
c = trace.c
STATUS = ROOT / "results/sweat_relayer_attribution_2026-09-23/20261108T003543Z_4a22f8412868"
RESULT96 = ROOT / "results/96_sweat_relayer_attribution_trace_2026-09-23.json"
PARENT = ROOT / "results/supply_epoch_pilot_2026-09-23/20261107T075015Z_18b7f0e7ee4f"
OUTPUT = ROOT / "results/sweat_submission_block_time"
REPORT = ROOT / "results/97_priority4_attribution_coverage.json"
PERIOD = "2026-08-24_to_2026-10-18"
SUBMISSION_HASH = "F14YmYFQmFAjgy4DYqg4dK8o2NizhPQbm12VUWuNrz63"


def request():
    return {"jsonrpc": "2.0", "id": "sweat-submission-block", "method": "block",
            "params": {"block_id": SUBMISSION_HASH}}


def prior():
    value = trace.validate_status(STATUS)
    c.require(c.json_bytes(value) == RESULT96.read_bytes(), "Result 96 does not reproduce")
    c.require(value["transaction_outcome_block_hash"] == SUBMISSION_HASH, "Submission identity changed")
    parent = c.recorded(PARENT, {"jsonrpc": "2.0", "id": "A-parent-block", "method": "block",
                                 "params": {"block_id": c.TARGETS["A"]["parent"]}})
    c.require(parent["header"]["hash"] == c.TARGETS["A"]["parent"]
              and parent["header"]["prev_hash"] == SUBMISSION_HASH, "Saved canonical successor mismatch")
    return value, parent["header"]


def validate_time(result):
    _, successor = prior()
    header = result.get("header", {})
    c.require(header.get("hash") == SUBMISSION_HASH, "Wrong submission block hash")
    c.integer(header.get("height"), "height")
    c.require(header["height"] < successor["height"], "Invalid predecessor height ordering")
    stamp = header.get("timestamp_nanosec")
    c.require(isinstance(stamp, str) and stamp.isdigit(), "Missing exact timestamp string")
    if "timestamp" in header:
        c.require(str(header["timestamp"]) == stamp, "Conflicting timestamp fields")
    c.require(int(stamp) < int(successor["timestamp_nanosec"]), "Invalid timestamp ordering")
    c.money(header.get("total_supply"), "total_supply")
    seconds, ns = divmod(int(stamp), 10**9)
    utc = datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + f".{ns:09d}Z"
    return {"hash": header["hash"], "height": header["height"], "timestamp_nanosec": stamp,
            "timestamp_utc": utc, "canonical_successor_hash": successor["hash"],
            "within_original_window": "2026-08-24" <= utc[:10] <= "2026-10-18",
            "identity_basis": "Exact transaction-outcome block hash and saved canonical successor prev_hash; heights are not assumed consecutive"}


def fetch(raw):
    c.require(c.decode(raw) == request(), "Unexpected live request")
    meta = {"http_status": None, "response_headers": [], "body_complete": False,
            "transport_error": None, "response_size_limit_bytes": trace.BODY_CAP}
    body = bytearray()
    response = None
    connection = c.http.client.HTTPSConnection(c.HOST, timeout=15, context=ssl.create_default_context())
    deadline = time.monotonic() + 60
    try:
        connection.connect()
        sock = connection.sock
        sock.settimeout(max(.001, deadline-time.monotonic()))
        connection.putrequest("POST", "/", skip_host=True, skip_accept_encoding=True)
        for k, v in trace.HEADERS + [["Content-Length", str(len(raw))]]:
            connection.putheader(k, v)
        connection.endheaders(raw)
        response = connection.getresponse()
        meta.update(http_status=response.status, response_headers=response.getheaders())
        c.require(response.getheader("Content-Encoding") in (None, "identity"), "Unexpected encoding")
        while not response.isclosed():
            c.require(len(body) < trace.BODY_CAP, "Response cap reached")
            remaining = deadline-time.monotonic()
            c.require(remaining > 0, "Request deadline exceeded")
            sock.settimeout(remaining)
            chunk = response.read1(min(65536, trace.BODY_CAP-len(body)))
            if not chunk:
                break
            body.extend(chunk)
        c.require(response.length in (None, 0), "Incomplete Content-Length response")
        meta["body_complete"] = True
    except (Exception, KeyboardInterrupt) as exc:
        if isinstance(exc, c.http.client.IncompleteRead):
            body.extend(exc.partial[:max(0, trace.BODY_CAP-len(body))])
        meta["transport_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            response.close()
        connection.close()
    return meta, bytes(body)


def collect(output=OUTPUT, transport=None, pause=None):
    prior()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        c.require(not (output / "attempt.json").exists(), "Request already attempted; no retry")
        directory = output / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12])
        directory.mkdir()
        c.write_new(output / "attempt.json", c.json_bytes({"directory": str(directory.relative_to(ROOT)) if directory.is_relative_to(ROOT) else str(directory), "maximum_requests": 1}))
        inputs = [RESULT96, Path(__file__), PARENT / "A-parent-block.response.body"]
        c.write_new(directory / "run.json", c.json_bytes({"request": request(), "endpoint": c.ENDPOINT,
            "request_count": 1, "response_body_cap_bytes": trace.BODY_CAP, "spacing_seconds": 65,
            "retries": 0, "fallbacks": [], "inputs": {trace.reference(p): trace.identity(p) for p in inputs}}))
        c.write_new(directory / "request.http", trace.request_http(request()))
        try:
            result = c.capture(directory, request(), transport=fetch if transport is None else transport, pause=pause)
            report = validate_time(result)
            c.write_new(directory / "validation.json", c.json_bytes(report))
        except BaseException as exc:
            c.write_new(directory / "stopped.json", c.json_bytes({"error": str(exc), "automatic_retry": False}))
            raise
        print(directory, flush=True)
        return directory


def saved_time(directory):
    manifest = c.decode((directory / "run.json").read_bytes())
    c.require(manifest["request"] == request() and manifest["request_count"] == 1
              and manifest["endpoint"] == c.ENDPOINT and manifest["response_body_cap_bytes"] == trace.BODY_CAP,
              "Wrong timestamp capture manifest")
    for p, expected in manifest["inputs"].items():
        c.require(trace.identity(ROOT / p) == expected, f"Changed timestamp input: {p}")
    c.require(not (directory / "stopped.json").exists(), "Stopped timestamp capture")
    c.require((directory / "request.http").read_bytes() == trace.request_http(request()), "Changed HTTP request")
    body = directory / "sweat-submission-block.response.body"
    c.require(body.stat().st_size <= trace.BODY_CAP, "Oversized saved block")
    return validate_time(c.recorded(directory, request()))


def csv_rows(number):
    path, = (ROOT / "results").glob(f"{number:02d}_*.csv")
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle)), path


def coverage_rows(assessment, leading, actions, destinations, growth_actions, outcomes, case):
    totals = Counter()
    keys = set()
    for row in leading:
        key = row["signer_account_id"], row["week_start"]
        c.require(key not in keys, "Duplicate signer-week")
        keys.add(key)
        totals[key[0]] += int(row["transactions"])
    for row in leading:
        c.require(totals[row["signer_account_id"]] == int(row["full_period_transactions"]), "Signer population mismatch")
    action_keys = set()
    for row in actions:
        key = tuple(row[k] for k in ("signer_account_id", "week_start", "action_kind", "method_name"))
        c.require(key not in action_keys, "Duplicate action bucket")
        action_keys.add(key)
        c.require(int(row["transactions_without_action_records"]) == 0, "Missing selected action records")
    outcome_keys = set()
    for row in outcomes:
        key = tuple(row[k] for k in ("signer_account_id", "week_start", "initial_receipt_status", "executor_check"))
        c.require(key not in outcome_keys, "Duplicate outcome bucket")
        outcome_keys.add(key)
        c.require(row["executor_check"] == "EXECUTOR_MATCHES_RECEIVER"
                  and int(row["transactions"]) == int(row["matched_outcome_rows"]), "Outcome coverage mismatch")
    leaders = assessment["leaders"]
    growth = assessment["largest_named_endpoint_growth_contributors"][:3]
    selected = [r["account_id"] for r in leaders]
    selected += [r["account_id"] for r in growth if r["account_id"] not in selected]
    rows = []
    for account in selected:
        group = [r for r in actions if r["signer_account_id"] == account]
        delegate = sum(int(r["transactions"]) for r in group if r["action_kind"] == "DELEGATE_ACTION") if group else None
        status = Counter()
        for r in outcomes:
            if r["signer_account_id"] == account:
                status[r["initial_receipt_status"]] += int(r["transactions"])
        if status:
            c.require(sum(status.values()) == totals[account], "Initial outcomes do not cover saved signer population")
        receiver_counts = Counter()
        for r in destinations:
            if r["signer_account_id"] == account:
                receiver_counts[r["receiver_account_id"]] += int(r["transactions"])
        buckets = [dict(receiver=r["receiver_account_id"], action=r["action_kind"], method=r["method_name"], transactions=int(r["transactions"]))
                   for r in growth_actions if r["signer_account_id"] == account]
        summed = Counter()
        for r in buckets:
            summed[(r["receiver"], r["action"], r["method"])] += r["transactions"]
        evidence = None
        if account == trace.SIGNER:
            evidence = {"selected_transactions": 1, "source": str(RESULT96.relative_to(ROOT)),
                        "returned_receipt_outcomes": case["coverage"]["returned_receipt_outcomes"],
                        "all_returned_outcomes_successful": case["coverage"]["all_observed_receipt_outcomes_successful"]}
        elif account == "tinykoala595.near":
            controls = trace.controls_report()["controls"]
            evidence = {"selected_transactions": len(controls), "source": str(trace.CONTROLS.relative_to(ROOT)),
                        "returned_receipt_outcomes": sum(r["coverage"]["returned_receipt_outcomes"] for r in controls),
                        "transactions_with_a_returned_failure": sum(not r["coverage"]["all_observed_receipt_outcomes_successful"] for r in controls)}
        rows.append({"account_id": account, "transactions": totals[account],
            "endpoint_growth_transactions": next((r["endpoint_change"] for r in growth if r["account_id"] == account), None),
            "delegate_action_transactions": delegate,
            "delegate_coverage": "Result 20 distinct-transaction action buckets; categories may overlap" if group else "Unavailable in selected action export; not zero",
            "original_receivers": [{"receiver": k, "transactions": n} for k, n in receiver_counts.most_common(3)] or None,
            "growth_receiver_action_buckets": [{"receiver": k[0], "action": k[1], "method": k[2], "transactions": n} for k, n in summed.most_common(3)] or None,
            "receiver_scope": "Weekly top-20 original receivers in result 19; result 23 joint receiver/action buckets overlap and are not added to infer unique transactions or inner actors",
            "initial_outcomes": dict(status) if status else None,
            "initial_outcome_weeks": sorted({r["week_start"] for r in outcomes if r["signer_account_id"] == account}) or None,
            "selected_downstream_evidence": evidence,
            "unresolved": "Population-wide inner actors, economic funders, descendant settlement and human/beneficial ownership are unmeasured; absence from selected exports is unavailable coverage, not no activity"})
    return rows


def consolidate(directory):
    case, _ = prior()
    timestamp = saved_time(directory)
    assessment = c.decode(trace.ASSESSMENT.read_bytes())
    leading, p18 = csv_rows(18)
    actions, p20 = csv_rows(20)
    destinations, p19 = csv_rows(19)
    growth_actions, p23 = csv_rows(23)
    outcomes, p24 = csv_rows(24)
    rows = coverage_rows(assessment, leading, actions, destinations, growth_actions, outcomes, case)
    population = case["population_coverage"].copy()
    population["transaction_submission_window_membership"] = timestamp["within_original_window"]
    population["confirmed_trace_members_in_saved_window"] = int(timestamp["within_original_window"])
    population["confirmed_network_delegate_trace_members_in_saved_window"] = int(timestamp["within_original_window"] and case["network_transaction_has_delegate_action"])
    population["qualification"] = "One purposively selected mechanism trace, not representative. Window membership is now checked against an exact saved RPC submission header; result 96's earlier conditional coverage is preserved unchanged."
    calls = [{**r, "decoded_utf8": base64.b64decode(r["raw_args_base64"], validate=True).decode("utf-8")} for r in case["function_calls"]]
    inputs = [RESULT96, trace.ASSESSMENT, trace.CONTROLS, p18, p19, p20, p23, p24, Path(__file__)]
    for root in (STATUS, directory):
        inputs += [p for p in root.rglob("*") if p.is_file()]
    return {"window": ["2026-08-24", "2026-10-18"], "source_requests_during_rebuild": 0,
            "ranking_scope": assessment["ranking_scope"], "network_transactions": assessment["network_transactions"],
            "coverage_table": rows, "case_study": {"classification": "SELECTED_DELEGATED_CLAIM",
                "submission_block": timestamp, "population_coverage": population, "decoded_calls": calls,
                "complete_returned_graph": {k: case[k] for k in ("transaction_hash", "transaction_outcome", "receipt_roles", "receipt_outcomes", "parent_links", "callback_dependencies", "coverage")},
                "recorded_charge_yocto": case["recorded_transaction_and_receipt_execution_charge_yocto"],
                "recorded_charge_near": format(Decimal(case["recorded_transaction_and_receipt_execution_charge_yocto"])/Decimal(10**24), "f"),
                "qualification": "Returned graph is covered and successful; no proof of independent historical completeness, human identity, revenue, economic fee funder or native supply destruction. Contract-specific burnt/amount_to_burn is not native NEAR burn."},
            "most_material_gap": {"population": "wx-cruce.near", "forwarding_initial_outcomes": 398968,
                "question": "Which downstream contracts and callback outcomes follow the successful forwarding initial receipts underlying this growth contributor?",
                "minimum_collection": "One FINAL EXPERIMENTAL_tx_status response for one saved, identity-checked wx transaction with a SUCCESS_RECEIPT_ID initial outcome; follow all returned descendants and callback inputs locally.",
                "identity_dependency": "The selected result-24 aggregates expose no transaction/receipt IDs for that success bucket; result 25 samples failed tinykoala transactions only. No eligible wx success identity is currently pinned.",
                "candidate_acquisition": "A bounded one-day source selection of one wx transaction with one matching SUCCESS_RECEIPT_ID initial outcome and preserved signer/receiver/transaction/receipt/block identities. BigQuery remains unauthorized/unavailable; no request can be constructed with a guessed transaction hash.",
                "stopping_condition": "One eligible transaction status, at most 8 MiB, no retries/fallback/scan; stop on missing or ambiguous identities/history. One mechanism case cannot estimate the 398,968-transaction settlement rate."},
            "sources": {trace.reference(p): trace.identity(p) for p in sorted(set(inputs))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["collect-time", "validate-time", "report"])
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.command == "collect-time":
        collect()
    else:
        c.require(args.run_dir is not None, "--run-dir required")
        def deny(event, _):
            if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
                raise RuntimeError("Source requests disabled during offline validation")
        sys.addaudithook(deny)
        value = saved_time(args.run_dir) if args.command == "validate-time" else consolidate(args.run_dir)
        raw = c.json_bytes(value)
        if args.output is None:
            sys.stdout.write(raw.decode())
        elif args.check:
            c.require(args.output.read_bytes() == raw, "Generated-file mismatch")
            print("Offline result matches saved evidence; source requests: 0")
        else:
            c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
