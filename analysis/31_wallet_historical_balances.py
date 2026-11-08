"""Six manually invoked historical view_account captures; plan/validate offline.

Exact account stocks versus execution-dated native action flows, not revenue,
beneficial holdings, a complete multi-asset ledger or actual supply burn.
"""

import argparse
import csv
import importlib.util
import io
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


c = module("balance_capture", "11_collect_canonical_validator_evidence.py")
sidecar = module("balance_ledger", "30_wallet_saved_evidence_ledger.py")
m = sidecar.m
require = c.require
BASELINE = ROOT / "results/28_daily_supply_checks_2026-08-23_to_2026-10-18.csv"
SIDECAR = ROOT / "results/76_three_wallet_saved_evidence_ledger_validation.json"
PLAN = ROOT / "results/77_three_wallet_historical_balance_request_plan.json"
OUTPUT = ROOT / "results/three_wallet_native_balances_2026-08-24_to_2026-10-18"
PINS = {
    BASELINE: "874e7d867e663dcb02c3e021c0fe37b9476b94de4212dc03bd3305b0f50fbe37",
    m.SOURCE: "48015cf9e13629c4ce751b88b160d07779cf7820ad9517f745c69f7a436a2b67",
    sidecar.DECODED: "b32bd48f35ef4adc7507ef6802458d723e5bd3642afe66141b6219979c71c5ec",
    SIDECAR: "36cad11a7f133d3ad29c45ddbe3a12d3526aa0bbe90d7f81ee9f00f8661d5212",
}
BOUNDARIES = {
    "opening": {"date": "2026-08-23", "height": 212636216,
                "hash": "ACuCLP9DEHaHn3ET8ohyQCJBfw6gnTLhNeMsjTgD3Lfu"},
    "closing": {"date": "2026-10-18", "height": 220581912,
                "hash": "76ZA6NE6s1MK1tk61djKwXs1kPbRmU4ofVtJfmKPENj1"},
}
SOURCES = ["https://docs.near.org/api/rpc/providers",
           "https://docs.near.org/api/rpc/contracts#view-account",
           "https://raw.githubusercontent.com/near/nearcore/2.9.0/chain/jsonrpc-primitives/src/types/query.rs"]


def money(value):
    require(isinstance(value, str) and value.isascii() and value.isdigit()
            and 1 <= len(value) <= 39 and int(value) < 2**128, "Expected exact u128 monetary string")
    return value


def near(value):
    return ("-" if value < 0 else "") + m.prior.near(abs(value))


def boundaries(raw, ledger):
    """Saved observed UTC edges, not an independent proof of canonical edges."""
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    dates = [r["block_date"] for r in rows]
    expected = {str(m.START-timedelta(days=1)+timedelta(days=i)) for i in range(57)}
    require(len(dates) == len(set(dates)) == 57 and set(dates) == expected, "Missing/duplicate boundary baseline dates")
    for row in rows:
        require(m.number(row["block_rows"]) > 0
                and row["block_rows"] == row["distinct_block_heights"] == row["distinct_block_hashes"], "Invalid observed block uniqueness")
        require(all(m.number(row[k]) == 0 for k in ("missing_block_heights", "missing_block_hashes", "missing_timestamps", "timestamp_date_mismatches")), "Invalid saved edge diagnostics")
    by_date = {r["block_date"]: r for r in rows}
    result = {}
    for label, target in BOUNDARIES.items():
        row = by_date[target["date"]]
        stamp = row["closing_block_timestamp_utc"]
        require(row["closing_block_hash"] == target["hash"]
                and m.number(row["closing_block_height"]) == target["height"] == m.number(row["last_block_height"])
                and m.stamp(stamp) == m.stamp(row["last_timestamp_utc"])
                and m.stamp(stamp).date().isoformat() == target["date"], "Saved boundary hash/height/time changed")
        result[label] = {**target, "saved_timestamp_utc": stamp}
    start = datetime(2026, 8, 24, tzinfo=timezone.utc)
    end = datetime(2026, 10, 19, tzinfo=timezone.utc)
    require(m.stamp(result["opening"]["saved_timestamp_utc"]) < start
            <= m.stamp(by_date[str(m.START)]["first_timestamp_utc"])
            and m.number(by_date[str(m.START)]["first_block_height"]) == result["opening"]["height"]+1
            and m.stamp(result["closing"]["saved_timestamp_utc"]) < end, "UTC ledger edge mismatch")
    target_actions = [a for a in ledger["actions"] if a["execution_window"] == "IN_TARGET_WINDOW"]
    for a in target_actions:
        stamp = m.stamp(a["execution_timestamp_utc"])
        require(start <= stamp < end and result["opening"]["height"] < m.number(a["execution_block_height"]) <= result["closing"]["height"]
                and m.stamp(result["opening"]["saved_timestamp_utc"]) < stamp <= m.stamp(result["closing"]["saved_timestamp_utc"]), "Ledger action outside saved balance anchors")
    return result, len(target_actions)


def request(label, account):
    return {"jsonrpc": "2.0", "id": f"{label}-{m.WALLETS.index(account)+1}", "method": "query",
            "params": {"request_type": "view_account", "account_id": account,
                       "block_id": BOUNDARIES[label]["hash"]}}


def plan():
    for path, pin in PINS.items():
        require(c.sha256(path.read_bytes()) == pin, f"Changed validated input: {path.name}")
    require(c.json_bytes(sidecar.report()) == SIDECAR.read_bytes(), "Result 76 does not reproduce")
    ledger = c.decode(sidecar.DECODED.read_bytes())
    edges, checked = boundaries(BASELINE.read_bytes(), ledger)
    inputs = list(PINS) + [Path(__file__), Path(c.__file__), Path(sidecar.__file__),
                           Path(m.__file__), Path(m.prior.__file__), m.SQL, ROOT / "sql/28_daily_supply_checks.sql"]
    return {"network": "mainnet", "endpoint": c.ENDPOINT, "request_count": 6,
            "window_start_inclusive": "2026-08-24T00:00:00Z", "window_end_exclusive": "2026-10-19T00:00:00Z",
            "boundaries": edges, "in_window_actions_checked": checked,
            "boundary_status": "SAVED_OBSERVED_DAY_CLOSES_MATCH_LEDGER_NOT_INDEPENDENT_CANONICAL_EDGE_PROOF",
            "boundary_precision": "Saved UTC timestamps have microsecond precision; view_account echoes height/hash, not timestamps",
            "requests": [{"boundary": label, "account_id": account, "request": request(label, account)}
                         for label in BOUNDARIES for account in m.WALLETS],
            "spacing_seconds": c.SPACING_SECONDS, "connect_timeout_seconds": c.CONNECT_TIMEOUT,
            "request_timeout_seconds": c.REQUEST_TIMEOUT, "automatic_retries": 0, "fallback_endpoints": [],
            "output_root": str(OUTPUT.relative_to(ROOT)), "references": SOURCES,
            "nonexistent_policy": "Exact structured UNKNOWN_ACCOUNT with matching account/hash/height is explicit absence; balances remain null pending lifecycle evidence",
            "comparison": "(closing amount+locked - opening amount+locked) - (successful execution-dated native inflows-outflows)",
            "source_hashes": {str(p.relative_to(ROOT)): m.prior.fingerprint(p) for p in inputs}}


def state(raw, payload, target):
    value = c.decode(raw)
    require(isinstance(value, dict) and value.get("jsonrpc") == "2.0" and value.get("id") == payload["id"], "JSON-RPC response identity mismatch")
    require(("result" in value) != ("error" in value), "Ambiguous result/error envelope")
    account = payload["params"]["account_id"]
    if "error" in value:
        error = value["error"]
        require(isinstance(error, dict), "Malformed RPC error")
        cause = error.get("cause", {})
        require(error.get("name") == "HANDLER_ERROR" and isinstance(cause, dict)
                and cause.get("name") == "UNKNOWN_ACCOUNT", f"RPC error; no retry: {error}")
        info = cause.get("info", {})
        require(isinstance(info, dict) and info.get("requested_account_id") == account
                and info.get("block_hash") == target["hash"] and type(info.get("block_height")) is int
                and info["block_height"] == target["height"], "Unverified account absence identity")
        return {"account_id": account, "block_hash": target["hash"], "block_height": target["height"],
                "account_state": "EXPLICIT_UNKNOWN_ACCOUNT", "amount": None, "locked": None,
                "storage_usage": None, "combined_yocto": None, "saved_error": error}
    result = value["result"]
    require(isinstance(result, dict) and "error" not in result, "Missing/error account result")
    require(result.get("block_hash") == target["hash"] and type(result.get("block_height")) is int
            and result["block_height"] == target["height"], "Historical account block identity mismatch")
    require("account_id" not in result or result["account_id"] == account, "Wrong echoed account")
    amount, locked = money(result.get("amount")), money(result.get("locked"))
    storage = c.integer(result.get("storage_usage"), "storage_usage")
    require(isinstance(result.get("code_hash"), str) and result["code_hash"], "Missing account code hash")
    if "storage_paid_at" in result:
        c.integer(result["storage_paid_at"], "storage_paid_at")
    return {"account_id": account, "block_hash": result["block_hash"], "block_height": result["block_height"],
            "account_state": "PRESENT", "amount": amount, "locked": locked, "storage_usage": storage,
            "code_hash": result["code_hash"], "storage_paid_at": result.get("storage_paid_at"),
            "combined_yocto": str(int(amount)+int(locked)),
            "account_identity_basis": "Exact recorded request and JSON-RPC ID; account need not be echoed"}


def saved_state(directory, item):
    payload = item["request"]
    stem = payload["id"]
    raw = (directory / f"{stem}.request.json").read_bytes()
    body = (directory / f"{stem}.response.body").read_bytes()
    meta = c.decode((directory / f"{stem}.metadata.json").read_bytes())
    require(raw == c.json_bytes(payload), "Changed saved request bytes")
    require(meta.get("endpoint") == c.ENDPOINT and meta.get("body_complete") is True
            and not meta.get("transport_error") and meta.get("http_status") == 200
            and meta.get("request_http_method") == "POST" and meta.get("request_path") == "/", "Failed/incomplete HTTP transport; evidence retained")
    require(meta.get("request_sha256") == c.sha256(raw) and meta.get("response_sha256") == c.sha256(body)
            and meta.get("request_bytes") == len(raw) and meta.get("response_bytes") == len(body), "Capture checksum/length mismatch")
    require(m.stamp(meta["finished_at"]) >= m.stamp(meta["started_at"]), "Invalid retrieval timestamps")
    result = state(body, payload, BOUNDARIES[item["boundary"]])
    result.update(boundary=item["boundary"], evidence={"directory": str(directory.resolve()),
                  "request": m.prior.fingerprint(directory / f"{stem}.request.json"),
                  "response": m.prior.fingerprint(directory / f"{stem}.response.body"),
                  "metadata": m.prior.fingerprint(directory / f"{stem}.metadata.json"),
                  "endpoint": c.ENDPOINT, "http_status": meta["http_status"],
                  "started_at": meta["started_at"], "finished_at": meta["finished_at"]})
    return result


def compare(states, ledger):
    by_key = {(s["boundary"], s["account_id"]): s for s in states}
    expected = {(label, w) for label in BOUNDARIES for w in m.WALLETS}
    require(len(states) == len(by_key) == 6 and set(by_key) == expected, "Incomplete/duplicate account boundary states")
    rows = []
    for wallet in ledger["wallets"]:
        account = wallet["account_id"]
        opening, closing = by_key[("opening", account)], by_key[("closing", account)]
        observed_net = int(wallet["valid_inflow_subtotal_yocto"])-int(wallet["valid_outflow_subtotal_yocto"])
        require(wallet["observed_action_layer_net_yocto"] == str(observed_net), "Ledger native-flow identity mismatch")
        change = None if opening["combined_yocto"] is None or closing["combined_yocto"] is None else int(closing["combined_yocto"])-int(opening["combined_yocto"])
        delta = None if change is None else change-observed_net
        fc = [a for a in ledger["actions"] if a["accepted_local_native_amount"] and a["action_kind"] == "FUNCTION_CALL"]
        rows.append({"account_id": account, "opening": opening, "closing": closing,
                     "combined_balance_change_yocto": str(change) if change is not None else None,
                     "combined_balance_change_near": near(change) if change is not None else None,
                     "successful_native_inflow_yocto": wallet["valid_inflow_subtotal_yocto"],
                     "successful_native_outflow_yocto": wallet["valid_outflow_subtotal_yocto"],
                     "observed_native_action_net_yocto": str(observed_net),
                     "unexplained_stock_flow_difference_yocto": str(delta) if delta is not None else None,
                     "unexplained_stock_flow_difference_near": near(delta) if delta is not None else None,
                     "measured_function_call_deposits_already_in_native_totals": {
                         "inflow_yocto": str(sum(int(a["amount_yocto"]) for a in fc if a["receiver"] == account)),
                         "outflow_yocto": str(sum(int(a["amount_yocto"]) for a in fc if a["predecessor"] == account))},
                     "independent_additional_adjustments_yocto": None, "attributed_fees_yocto": None,
                     "complete_balance_reconciliation": False})
    stocks = {label: None if any(r[label]["combined_yocto"] is None for r in rows)
              else sum(int(r[label]["combined_yocto"]) for r in rows) for label in BOUNDARIES}
    group_change = None if any(v is None for v in stocks.values()) else stocks["closing"]-stocks["opening"]
    external_net = int(ledger["group_observed_external_net_yocto"])
    require(sum(int(r["observed_native_action_net_yocto"]) for r in rows) == external_net, "Internal legs do not cancel")
    return {"accounts": rows,
            "group_opening_combined_yocto": str(stocks["opening"]) if stocks["opening"] is not None else None,
            "group_closing_combined_yocto": str(stocks["closing"]) if stocks["closing"] is not None else None,
            "group_combined_balance_change_yocto": str(group_change) if group_change is not None else None,
            "group_observed_external_native_net_yocto": str(external_net),
            "group_unexplained_stock_flow_difference_yocto": str(group_change-external_net) if group_change is not None else None,
            "independent_additional_adjustments_yocto": None, "verified_revenue_yocto": None,
            "verified_purchases_yocto": None, "actual_supply_burn_yocto": None,
            "scope": "EXACT_ACCOUNT_STOCK_COMPARISON_TO_OBSERVED_EXECUTION_DATED_NATIVE_ACTION_LAYER",
            "zero_difference_would_not_establish_completeness": True}


def validate(directory):
    manifest = c.decode((directory / "run.json").read_bytes())
    prepared = plan()
    require(manifest.get("plan") == prepared, "Run plan/input provenance changed")
    m.stamp(manifest["created_at"])
    for suffix in ("request.json", "response.body", "metadata.json"):
        require({p.name for p in directory.glob(f"*.{suffix}")} == {f'{i["request"]["id"]}.{suffix}' for i in prepared["requests"]}, "Incomplete/unexpected captures")
    require(not (directory / "stopped.json").exists(), "Collection stopped; review saved failure before reconciliation")
    states = [saved_state(directory, item) for item in prepared["requests"]]
    result = compare(states, c.decode(sidecar.DECODED.read_bytes()))
    result.update(status="SIX_BOUNDARY_RESPONSES_VALIDATED_NATIVE_STOCK_FLOW_COMPARISON_ONLY",
                  boundaries=prepared["boundaries"], boundary_status=prepared["boundary_status"],
                  boundary_precision=prepared["boundary_precision"], source_hashes=prepared["source_hashes"],
                  manifest=m.prior.fingerprint(directory / "run.json"), references=SOURCES)
    return result


def collect(output_root=OUTPUT, transport=None, pause=None):
    prepared = plan()
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Saved request plan differs; review offline")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12])
    directory.mkdir()
    c.write_new(directory / "run.json", c.json_bytes({"created_at": c.utc_now(), "plan": prepared}))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    transport = c.fetch if transport is None else transport
    pause = time.sleep if pause is None else pause
    for attempt, item in enumerate(prepared["requests"], 1):
        stem = item["request"]["id"]
        try:
            raw = c.json_bytes(item["request"])
            c.write_new(directory / f"{stem}.request.json", raw)
            print(f"Waiting {c.SPACING_SECONDS}s before {stem}; one attempt, no retries.", flush=True)
            pause(c.SPACING_SECONDS)
            started = c.utc_now()
            meta, body = transport(raw)
            meta.update(endpoint=c.ENDPOINT, started_at=started, finished_at=c.utc_now(),
                        request_http_method="POST", request_path="/", request_sha256=c.sha256(raw),
                        response_sha256=c.sha256(body), request_bytes=len(raw), response_bytes=len(body))
            c.write_new(directory / f"{stem}.response.body", body)
            c.write_new(directory / f"{stem}.metadata.json", c.json_bytes(meta))
            saved_state(directory, item)
        except (Exception, KeyboardInterrupt) as exc:
            c.write_new(directory / "stopped.json", c.json_bytes({"request_id": stem, "attempts": attempt,
                         "error": f"{type(exc).__name__}: {exc}", "automatic_retry": False}))
            raise
    report = validate(directory)
    c.write_new(directory / "validation.json", c.json_bytes(report))
    print("Six responses captured. Stock-flow differences remain unexplained, not fees or revenue.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("plan", help="OFFLINE: verify inputs and print the six requests")
    p.add_argument("--output", type=Path)
    subs.add_parser("collect", help="LIVE/manual only: six sequential requests, no retries/fallback")
    p = subs.add_parser("validate", help="OFFLINE: validate six saved responses and compare stocks/flows")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            collect()
            return 0
        report = plan() if args.command == "plan" else validate(args.run_dir)
        raw = c.json_bytes(report)
        if args.output:
            c.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No automatic retry or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
