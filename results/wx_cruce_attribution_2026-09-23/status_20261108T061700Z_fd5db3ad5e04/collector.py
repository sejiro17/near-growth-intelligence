"""One indexed candidate, canonical status and submission-header check; no scans.

Each collect command consumes one immutable request slot. No pagination, retries,
redirects, alternate endpoints or automatic additional requests are supported.
"""

import argparse
import base64
import csv
import fcntl
import importlib.util
import ssl
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("trace_interpreter", ROOT / "analysis/40_trace_sweat_relayer.py")
trace = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace)
c = trace.c
ACCOUNT = "wx-cruce.near"
OUTPUT = ROOT / "results/wx_cruce_attribution_2026-09-23"
HISTORY_ENDPOINT = "https://tx.main.fastnear.com/v0/account"
SUPPLY = ROOT / "results/28_daily_supply_checks_2026-08-23_to_2026-10-18.csv"
BODY_CAP = 8 * 1024**2


def day_bounds():
    with SUPPLY.open(newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["block_date"] == "2026-09-23"]
    c.require(len(rows) == 1, "Ambiguous saved day bounds")
    return int(rows[0]["first_block_height"]), int(rows[0]["last_block_height"])+1


def history_request():
    lower, upper = day_bounds()
    return {"account_id": ACCOUNT, "is_signer": True, "from_tx_block_height": lower,
            "to_tx_block_height": upper, "limit": 1, "desc": False}


def history_identity(result):
    c.require(isinstance(result, dict) and "error" not in result, "History API error or invalid response")
    rows = result.get("account_txs")
    c.require(isinstance(rows, list) and len(rows) == 1, "No unique candidate in bounded history response; no pagination")
    row = rows[0]
    trace.helper.validate_origin({"transaction_hash": row.get("transaction_hash"), "sender_account_id": ACCOUNT})
    lower, upper = day_bounds()
    c.require(row.get("account_id") == ACCOUNT and row.get("is_signer") is True, "Wrong indexed account/signer role")
    c.integer(row.get("tx_block_height"), "tx_block_height")
    c.require(lower <= row["tx_block_height"] < upper, "Candidate outside requested height bounds")
    stamp = row.get("tx_block_timestamp")
    c.require(isinstance(stamp, str) and stamp.isdigit(), "Missing exact indexed timestamp")
    c.require(datetime.fromtimestamp(int(stamp)//10**9, timezone.utc).date().isoformat() == "2026-09-23", "Wrong indexed date")
    return row


def status_request(candidate):
    return {"jsonrpc": "2.0", "id": "wx-transaction-status", "method": "EXPERIMENTAL_tx_status",
            "params": {"tx_hash": candidate["transaction_hash"], "sender_account_id": ACCOUNT, "wait_until": "FINAL"}}


def initial_gate(result, candidate):
    c.require(result.get("final_execution_status") == "FINAL", "Historical transaction not final")
    tx = result.get("transaction", {})
    c.require(tx.get("hash") == candidate["transaction_hash"] and tx.get("signer_id") == ACCOUNT, "Wrong canonical transaction/signer")
    c.account_id(tx.get("receiver_id"))
    root = result.get("transaction_outcome", {})
    c.require(root.get("id") == tx["hash"] and root.get("outcome", {}).get("executor_id") == ACCOUNT, "Wrong root outcome")
    initial = root["outcome"].get("status", {}).get("SuccessReceiptId")
    c.require(initial is not None and initial in root["outcome"].get("receipt_ids", []), "Missing initial receipt link")
    outcomes = [r for r in result.get("receipts_outcome", []) if r.get("id") == initial]
    receipts = [r for r in result.get("receipts", []) if r.get("receipt_id") == initial]
    c.require(len(outcomes) == len(receipts) == 1, "Missing/duplicate initial receipt/outcome")
    c.require(outcomes[0]["outcome"].get("executor_id") == tx["receiver_id"]
              and receipts[0].get("receiver_id") == tx["receiver_id"], "Initial receiver/executor mismatch")
    returned = outcomes[0]["outcome"].get("status", {}).get("SuccessReceiptId")
    c.require(returned is not None, "Selected initial outcome is not SUCCESS_RECEIPT_ID; stop without another candidate")
    trace.hash_id(root.get("block_hash"))
    trace.hash_id(returned)
    return {"transaction_hash": tx["hash"], "network_signer": tx["signer_id"], "receiver": tx["receiver_id"],
            "submission_block_hash": root["block_hash"], "initial_receipt_id": initial,
            "initial_outcome_status": outcomes[0]["outcome"]["status"],
            "indexed_submission_timestamp_nanosec": candidate["tx_block_timestamp"],
            "date_gate": "Indexed date/height validated; canonical header required before descendant interpretation"}


def header_request(gate):
    return {"jsonrpc": "2.0", "id": "wx-submission-block", "method": "block",
            "params": {"block_id": gate["submission_block_hash"]}}


def header_gate(result, gate, candidate):
    h = result.get("header", {})
    c.require(h.get("hash") == gate["submission_block_hash"] and h.get("height") == candidate["tx_block_height"], "Wrong submission header")
    c.require(h.get("timestamp_nanosec") == candidate["tx_block_timestamp"], "Indexed/canonical timestamp mismatch")
    if "timestamp" in h:
        c.require(str(h["timestamp"]) == h["timestamp_nanosec"], "Conflicting canonical timestamps")
    sec, ns = divmod(int(h["timestamp_nanosec"]), 10**9)
    utc = datetime.fromtimestamp(sec, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")+f".{ns:09d}Z"
    c.require(utc.startswith("2026-09-23T"), "Canonical date outside selected day")
    return {"hash": h["hash"], "height": h["height"], "timestamp_nanosec": h["timestamp_nanosec"], "timestamp_utc": utc,
            "within_research_window": True}


def http_bytes(endpoint, payload):
    host, _, path = endpoint.removeprefix("https://").partition("/")
    raw = c.json_bytes(payload)
    headers = [["Host", host], ["Content-Type", "application/json"], ["Accept", "application/json"],
               ["Accept-Encoding", "identity"], ["Connection", "close"],
               ["User-Agent", "near-growth-intelligence-bounded-wx-trace/1"], ["Content-Length", str(len(raw))]]
    return ("POST /"+path+" HTTP/1.1\r\n"+"".join(k+": "+v+"\r\n" for k, v in headers)+"\r\n").encode()+raw


def fetch(endpoint, payload):
    c.require(endpoint in (HISTORY_ENDPOINT, c.ENDPOINT), "Unapproved endpoint")
    raw = http_bytes(endpoint, payload)
    head, body = raw.split(b"\r\n\r\n", 1)
    lines = head.decode().split("\r\n")
    host = next(v.split(": ", 1)[1] for v in lines if v.startswith("Host: "))
    path = lines[0].split()[1]
    connection = c.http.client.HTTPSConnection(host, timeout=15, context=ssl.create_default_context())
    meta = {"http_status": None, "response_headers": [], "body_complete": False, "transport_error": None}
    response = None
    received = bytearray()
    deadline = time.monotonic()+60
    try:
        connection.connect()
        sock = connection.sock
        sock.settimeout(max(.001, deadline-time.monotonic()))
        connection.putrequest("POST", path, skip_host=True, skip_accept_encoding=True)
        for line in lines[1:]:
            key, value = line.split(": ", 1)
            connection.putheader(key, value)
        connection.endheaders(body)
        response = connection.getresponse()
        meta.update(http_status=response.status, response_headers=response.getheaders())
        c.require(response.getheader("Content-Encoding") in (None, "identity"), "Unexpected encoded response")
        while not response.isclosed():
            c.require(len(received) < BODY_CAP, "Response byte cap reached")
            remaining = deadline-time.monotonic()
            c.require(remaining > 0, "Request deadline exceeded")
            sock.settimeout(remaining)
            part = response.read1(min(65536, BODY_CAP-len(received)))
            if not part:
                break
            received.extend(part)
        c.require(response.length in (None, 0), "Incomplete Content-Length")
        meta["body_complete"] = True
    except (Exception, KeyboardInterrupt) as exc:
        if isinstance(exc, c.http.client.IncompleteRead):
            received.extend(exc.partial[:max(0, BODY_CAP-len(received))])
        meta["transport_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            response.close()
        connection.close()
    return meta, bytes(received)


def capture(stage, endpoint, payload, validate, output=OUTPUT, transport=None, pause=time.sleep):
    c.require(stage in {"history", "status", "header"}, "Unknown stage")
    output.mkdir(parents=True, exist_ok=True)
    with (output/".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker = output/(stage+".attempt.json")
        c.require(not marker.exists(), "Stage already attempted; no retries")
        directory = output/(stage+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12])
        directory.mkdir()
        c.write_new(marker, c.json_bytes({"directory": trace.reference(directory), "maximum_requests": 1}))
        c.write_new(directory/"request.json", c.json_bytes(payload))
        c.write_new(directory/"request.http", http_bytes(endpoint, payload))
        c.write_new(directory/"collector.py", Path(__file__).read_bytes())
        c.write_new(directory/"run.json", c.json_bytes({"stage": stage, "endpoint": endpoint, "request_count": 1,
            "body_cap_bytes": BODY_CAP, "spacing_seconds": 65, "timeouts_seconds": [15, 60], "retries": 0,
            "fallbacks": [], "redirects": False, "credentials": False}))
        print(f"Evidence directory: {directory}\nWaiting 65s before {stage}; one attempt, no retries.", flush=True)
        try:
            pause(65)
            started = c.utc_now()
            meta, body = (fetch if transport is None else transport)(endpoint, payload)
            meta.update(endpoint=endpoint, started_at=started, finished_at=c.utc_now(),
                response_sha256=c.sha256(body), response_bytes=len(body),
                request_sha256=c.sha256(c.json_bytes(payload)), request_bytes=len(c.json_bytes(payload)),
                request_http_sha256=c.sha256(http_bytes(endpoint, payload)), body_cap_bytes=BODY_CAP)
            c.write_new(directory/"response.body", body)
            c.write_new(directory/"metadata.json", c.json_bytes(meta))
            c.require(len(body) <= BODY_CAP and meta.get("body_complete") and not meta.get("transport_error"), "Incomplete/capped transport; stop")
            c.require(meta.get("http_status") == 200, f"HTTP {meta.get('http_status')}; stop without fallback")
            result = c.decode(body) if stage == "history" else c.envelope(body, payload)
            report = validate(result)
            c.write_new(directory/"validation.json", c.json_bytes(report))
            print("Stage validated; no next request was started.", flush=True)
        except BaseException as exc:
            c.write_new(directory/"stopped.json", c.json_bytes({"error": str(exc), "automatic_retry": False}))
            raise
    return directory


def saved(directory, stage, endpoint, payload):
    c.require(not (directory/"stopped.json").exists(), "Stopped capture; no automatic retry")
    manifest = c.decode((directory/"run.json").read_bytes())
    c.require(manifest["stage"] == stage and manifest["endpoint"] == endpoint and manifest["request_count"] == 1
              and manifest["body_cap_bytes"] == BODY_CAP, "Wrong saved stage/limits")
    c.require((directory/"request.json").read_bytes() == c.json_bytes(payload)
              and (directory/"request.http").read_bytes() == http_bytes(endpoint, payload), "Wrong saved request")
    meta = c.decode((directory/"metadata.json").read_bytes())
    body = (directory/"response.body").read_bytes()
    c.require(meta["http_status"] == 200 and meta["body_complete"] and not meta["transport_error"], "Failed saved HTTP response")
    c.require(len(body) <= BODY_CAP and len(body) == meta["response_bytes"] and c.sha256(body) == meta["response_sha256"]
              and meta["request_sha256"] == c.sha256(c.json_bytes(payload))
              and meta["request_bytes"] == len(c.json_bytes(payload))
              and meta["request_http_sha256"] == c.sha256(http_bytes(endpoint, payload)), "Saved checksum mismatch")
    started, ended = [datetime.fromisoformat(meta[k]) for k in ("started_at", "finished_at")]
    c.require(started.utcoffset() == ended.utcoffset() == timezone.utc.utcoffset(started) and ended >= started, "Invalid UTC retrieval times")
    return c.decode(body) if stage == "history" else c.envelope(body, payload)


def known_directory(stage):
    path = c.decode((OUTPUT/(stage+".attempt.json")).read_bytes())["directory"]
    return ROOT/path


def prior_status():
    candidate = history_identity(saved(known_directory("history"), "history", HISTORY_ENDPOINT, history_request()))
    result = saved(known_directory("status"), "status", c.ENDPOINT, status_request(candidate))
    return candidate, result, initial_gate(result, candidate)


def report():
    candidate, result, gate = prior_status()
    block = saved(known_directory("header"), "header", c.ENDPOINT, header_request(gate))
    header = header_gate(block, gate, candidate)
    graph = trace.interpret(result)
    calls = [{**r, "decoded_utf8": base64.b64decode(r["raw_args_base64"], validate=True).decode()} for r in graph["function_calls"]]
    paths = [SUPPLY, Path(__file__), ROOT/"analysis/40_trace_sweat_relayer.py"]
    for stage in ("history", "status", "header"):
        paths += [p for p in known_directory(stage).iterdir() if p.is_file()]
    return {"classification": "SELECTED_WX_FORWARDING_MECHANISM_CASE", "candidate": candidate,
        "identity_gate": gate, "canonical_submission": header, "returned_graph": graph, "decoded_calls": calls,
        "recorded_charge_near": format(Decimal(graph["recorded_transaction_and_receipt_execution_charge_yocto"])/Decimal(10**24), "f"),
        "qualification": "One selected account-history candidate, not representative of 413,281 wx transactions or 398,968 initial SUCCESS_RECEIPT_ID outcomes. Returned-graph coverage does not establish independent ingestion completeness, business purpose, economic payer, revenue or native supply destruction.",
        "sources": {trace.reference(p): trace.identity(p) for p in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["history", "status", "header", "report"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "history":
        capture("history", HISTORY_ENDPOINT, history_request(), history_identity)
    elif args.stage == "status":
        candidate = history_identity(saved(known_directory("history"), "history", HISTORY_ENDPOINT, history_request()))
        capture("status", c.ENDPOINT, status_request(candidate), lambda r: initial_gate(r, candidate))
    elif args.stage == "header":
        candidate, _, gate = prior_status()
        capture("header", c.ENDPOINT, header_request(gate), lambda r: header_gate(r, gate, candidate))
    else:
        def deny(event, _):
            if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
                raise RuntimeError("Network disabled during offline interpretation")
        sys.addaudithook(deny)
        raw = c.json_bytes(report())
        if args.output is None:
            sys.stdout.write(raw.decode())
        elif args.check:
            c.require(args.output.read_bytes() == raw, "Generated-file mismatch")
            print("Offline report reproduced; source requests: 0")
        else:
            c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
