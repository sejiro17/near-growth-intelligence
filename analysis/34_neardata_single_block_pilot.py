"""One manually invoked Neardata GET; plan/validate use saved files only.

Compare block A with its saved canonical RPC control. One point tests source
fields/availability, not bulk retention, gross burn or full-period coverage.
"""

import argparse
import http.client
import importlib.util
import ssl
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("neardata_control", ROOT / "analysis/11_collect_canonical_validator_evidence.py")
c = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(c)
require = c.require
CONTROL = ROOT / "results/canonical_rpc_2026-09-23/20261106T133436Z_2e1218e30fbc/stage1"
PLAN = ROOT / "results/81_neardata_single_block_pilot_plan.json"
OUTPUT = ROOT / "results/neardata_supply_block_pilot_2026-09-23"
HOST = "mainnet.neardata.xyz"
PATH = "/v0/block/216877934"
URL = "https://"+HOST+PATH
MAX_BODY = 32*1024*1024
HEADERS = [["Host", HOST], ["Accept", "application/json"], ["Accept-Encoding", "identity"],
           ["Connection", "close"], ["User-Agent", "near-growth-intelligence-single-block-pilot/1"]]
REFERENCES = ["https://docs.fastnear.com/neardata", "https://docs.fastnear.com/neardata/block",
              "https://docs.fastnear.com/assets/files/neardata-3ad3f0506033a28203f9dec32a5664c8.json"]


def fingerprint(path):
    path = path.resolve()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": c.sha256(path.read_bytes()), "bytes": path.stat().st_size}


def money(value):
    require(isinstance(value, str) and value.isascii() and value.isdigit()
            and 1 <= len(value) <= 39 and int(value) < 2**128, "Monetary field must be an exact u128 string")
    return int(value)


def description():
    return {"method": "GET", "url": URL, "path": PATH, "headers": HEADERS, "body_bytes": 0}


def request_bytes():
    return ("GET "+PATH+" HTTP/1.1\r\n"+"".join(k+": "+v+"\r\n" for k, v in HEADERS)+"\r\n").encode("ascii")


def controls():
    block = c.recorded(CONTROL, c.request("A", "block"))
    protocol = c.recorded(CONTROL, c.request("A", "protocol"))
    shards = c.validate_block(block, c.TARGETS["A"])
    c.validate_protocol(protocol, shards)
    return block, protocol


def plan():
    block, protocol = controls()
    return {"network": "mainnet", "request_count": 1, "request": description(),
            "target": {k: c.TARGETS["A"][k] for k in ("height", "hash", "parent")},
            "active_protocol_version_from_saved_configuration": protocol["protocol_version"],
            "spacing_seconds": c.SPACING_SECONDS, "connect_timeout_seconds": c.CONNECT_TIMEOUT,
            "request_timeout_seconds": c.REQUEST_TIMEOUT, "response_body_cap_bytes": MAX_BODY,
            "automatic_retries": 0, "fallback_endpoints": [], "credentials": "NONE",
            "expected_fields": {"header": ["hash", "height", "prev_hash", "epoch_id", "next_epoch_id", "timestamp_nanosec", "total_supply"],
                                "chunks": ["shard_id", "chunk_hash", "prev_block_hash", "height_created", "height_included", "balance_burnt"]},
            "saved_header": {k: block["header"][k] for k in ("hash", "height", "prev_hash", "epoch_id", "next_epoch_id", "timestamp_nanosec", "total_supply")},
            "availability": "Anonymous documented operation; historical retention, access and returned monetary fields remain untested",
            "output_root": str(OUTPUT.relative_to(ROOT)), "references": REFERENCES,
            "does_not_establish": "Bulk access/volume/cost, canonical predecessor census, complete receipt/state-change retention, gross burn/subsidies or weekly debit",
            "source_files": [fingerprint(p) for p in [Path(__file__), Path(c.__file__)] +
                             [CONTROL/f"A-{kind}.{suffix}" for kind in ("block", "protocol") for suffix in ("request.json", "response.body", "metadata.json")]]}


def compare(raw, canonical):
    value = c.decode(raw)
    require(value is not None, "Neardata returned null; retained document unavailable, not zero activity")
    require(isinstance(value, dict) and "error" not in value and isinstance(value.get("block"), dict)
            and isinstance(value.get("shards"), list), "Missing/error/ambiguous Neardata block document")
    block = value["block"]
    h = block.get("header", {})
    expected = canonical["header"]
    for k in ("hash", "height", "prev_hash", "epoch_id", "next_epoch_id", "timestamp_nanosec", "total_supply"):
        require(k in h and type(h[k]) is type(expected[k]) and h[k] == expected[k], f"Canonical header mismatch: {k}")
    money(h["total_supply"])
    require(isinstance(h["timestamp_nanosec"], str) and h["timestamp_nanosec"].isascii() and h["timestamp_nanosec"].isdigit(), "Invalid exact timestamp")
    optional_missing = []
    for k in ("prev_height", "timestamp", "chunks_included", "chunk_mask"):
        if k not in h:
            optional_missing.append(k)
        else:
            require(type(h[k]) is type(expected[k]) and h[k] == expected[k], f"Canonical header mismatch: {k}")
    if "chunk_mask" in h:
        require(all(type(x) is bool for x in h["chunk_mask"]), "Chunk mask must contain booleans")
    chunks = block.get("chunks")
    require(isinstance(chunks, list) and len(chunks) == len(canonical["chunks"]), "Partial chunk-header manifest")
    audit, seen = [], set()
    for index, (chunk, saved) in enumerate(zip(chunks, canonical["chunks"])):
        require(isinstance(chunk, dict), "Invalid chunk header")
        for k in ("shard_id", "chunk_hash", "prev_block_hash", "height_created", "height_included"):
            require(k in chunk and type(chunk[k]) is type(saved[k]) and chunk[k] == saved[k], f"Canonical ordered chunk mismatch: {k}")
        require(chunk["shard_id"] not in seen, "Duplicate shard/chunk key")
        seen.add(chunk["shard_id"])
        present = chunk.get("balance_burnt") is not None
        debit = money(chunk["balance_burnt"]) if present else None
        if present:
            require(chunk["balance_burnt"] == saved["balance_burnt"], "Canonical chunk monetary value mismatch")
        audit.append({"array_index": index, **{k: chunk[k] for k in ("shard_id", "chunk_hash", "prev_block_hash", "height_created", "height_included")},
                      "newly_included": chunk["height_included"] == h["height"],
                      "net_header_debit_yocto": str(debit) if present else None,
                      "monetary_field_status": "EXACT_STRING_MATCH" if present else "UNAVAILABLE"})
    included = [x for x in audit if x["newly_included"]]
    net = sum(int(x["net_header_debit_yocto"]) for x in included) if all(x["net_header_debit_yocto"] is not None for x in included) else None
    reference = sum(money(x["balance_burnt"]) for x in canonical["chunks"] if x["height_included"] == h["height"])
    require(net is None or net == reference, "Included net-header debit mismatch")
    shards, seen_payload = [], set()
    for index, shard in enumerate(value["shards"]):
        require(isinstance(shard, dict) and type(shard.get("shard_id")) is int
                and shard["shard_id"] in seen and shard["shard_id"] not in seen_payload, "Invalid/duplicate shard payload")
        seen_payload.add(shard["shard_id"])
        payload = shard.get("chunk")
        if payload is not None:
            require(isinstance(payload, dict) and isinstance(payload.get("header"), dict), "Invalid shard chunk payload")
            saved = next(x for x in canonical["chunks"] if x["shard_id"] == shard["shard_id"])
            require(payload["header"].get("chunk_hash") == saved["chunk_hash"]
                    and payload["header"].get("shard_id") == shard["shard_id"], "Shard/chunk identity mismatch")
        row = {"array_index": index, "shard_id": shard["shard_id"], "has_chunk_payload": payload is not None}
        for field in ("state_changes", "receipt_execution_outcomes"):
            require(field not in shard or isinstance(shard[field], list), f"Malformed shard array: {field}")
            row[field+"_observed_records"] = len(shard[field]) if field in shard else None
        shards.append(row)
    return {"status": "ONE_BLOCK_CANONICAL_IDENTITY_MATCH_FIELDS_AS_REPORTED",
            "height": h["height"], "hash": h["hash"],
            "header": {k: h[k] for k in ("hash", "height", "prev_hash", "epoch_id", "next_epoch_id", "timestamp_nanosec", "total_supply", "prev_height", "timestamp", "chunks_included", "chunk_mask") if k in h},
            "chunk_audit": audit,
            "missing_header_fields": optional_missing, "newly_included_chunks": len(included),
            "included_chunk_net_debit_yocto": str(net) if net is not None else None,
            "saved_canonical_net_debit_yocto": str(reference),
            "monetary_discrepancy_yocto": str(net-reference) if net is not None else None,
            "missing_chunk_monetary_field_shards": [x["shard_id"] for x in audit if x["net_header_debit_yocto"] is None],
            "shard_payload_audit": shards, "all_manifest_shards_have_payload_records": seen_payload == seen,
            "independent_all_shard_state_receipt_completeness": None,
            "gross_actual_burn_yocto": None, "subsidies_yocto": None,
            "independent_weekly_net_debit_yocto": None, "bulk_retention_or_acquisition_established": False}


def fetch(raw_request):
    require(raw_request == request_bytes(), "Unexpected single-block HTTP request")
    connection = http.client.HTTPSConnection(HOST, timeout=c.CONNECT_TIMEOUT, context=ssl.create_default_context())
    response, body = None, bytearray()
    meta = {"http_status": None, "response_headers": [], "body_complete": False, "transport_error": None}
    deadline = time.monotonic()+c.REQUEST_TIMEOUT
    try:
        connection.connect()
        sock = connection.sock
        sock.settimeout(max(1, deadline-time.monotonic()))
        connection.putrequest("GET", PATH, skip_host=True, skip_accept_encoding=True)
        for key, value in HEADERS:
            connection.putheader(key, value)
        connection.endheaders()
        response = connection.getresponse()
        meta.update(http_status=response.status, response_headers=response.getheaders(), http_version=response.version, http_reason=response.reason)
        while not response.isclosed():
            remaining = deadline-time.monotonic()
            require(remaining > 0, "Request deadline exceeded")
            sock.settimeout(remaining)
            piece = response.read1(min(65536, MAX_BODY-len(body)+1))
            if not piece:
                break
            body.extend(piece)
            require(len(body) <= MAX_BODY, "Single-block response exceeds fixed byte cap")
        require(response.length in (None, 0), "Truncated Content-Length response")
        meta["body_complete"] = True
    except (Exception, KeyboardInterrupt) as exc:
        if isinstance(exc, http.client.IncompleteRead):
            body.extend(exc.partial)
        meta["transport_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            response.close()
        connection.close()
    return meta, bytes(body)


def validate(directory):
    prepared = plan()
    manifest = c.decode((directory / "run.json").read_bytes())
    require(manifest.get("plan") == prepared, "Run/input provenance changed")
    raw = (directory / "block-A.request.http").read_bytes()
    description_raw = (directory / "block-A.request.json").read_bytes()
    body = (directory / "block-A.response.body").read_bytes()
    meta = c.decode((directory / "block-A.metadata.json").read_bytes())
    require(raw == request_bytes() and description_raw == c.json_bytes(description()), "Saved request changed")
    require(meta.get("request_sha256") == c.sha256(raw) and meta.get("request_bytes") == len(raw)
            and meta.get("request_description_sha256") == c.sha256(description_raw)
            and meta.get("response_sha256") == c.sha256(body) and meta.get("response_bytes") == len(body), "Request/response checksum/length mismatch")
    require(meta.get("endpoint") == URL and meta.get("http_status") == 200 and meta.get("body_complete") is True
            and meta.get("request_http_method") == "GET" and meta.get("request_path") == PATH
            and not meta.get("transport_error") and len(body) <= MAX_BODY, f"Failed/incomplete HTTP transport/status: {meta.get('http_status')}; evidence retained")
    stamps = []
    for name in ("started_at", "finished_at"):
        stamp = datetime.fromisoformat(meta[name])
        require(stamp.utcoffset() == timedelta(0), "Invalid UTC retrieval timestamp")
        stamps.append(stamp)
    require(stamps[1] >= stamps[0], "Reversed retrieval timestamps")
    require(not (directory / "stopped.json").exists(), "Stopped capture; review saved failure")
    require(len(list(directory.glob("*.response.body"))) == 1, "Unexpected extra responses")
    report = compare(body, controls()[0])
    report.update(source_files=prepared["source_files"], references=REFERENCES,
                  capture_files=[fingerprint(directory/name) for name in ("run.json", "block-A.request.http", "block-A.request.json", "block-A.response.body", "block-A.metadata.json")])
    return report


def collect(output_root=OUTPUT, transport=None, pause=None):
    prepared = plan()
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Frozen single-request plan differs")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12])
    directory.mkdir()
    c.write_new(directory / "run.json", c.json_bytes({"created_at": c.utc_now(), "plan": prepared}))
    raw, descriptor = request_bytes(), c.json_bytes(description())
    c.write_new(directory / "block-A.request.http", raw)
    c.write_new(directory / "block-A.request.json", descriptor)
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    pause = time.sleep if pause is None else pause
    transport = fetch if transport is None else transport
    try:
        print(f"Waiting {c.SPACING_SECONDS}s before block-A; one GET, no retries.", flush=True)
        pause(c.SPACING_SECONDS)
        started = c.utc_now()
        meta, response = transport(raw)
        meta.update(endpoint=URL, started_at=started, finished_at=c.utc_now(), request_http_method="GET", request_path=PATH,
                    request_sha256=c.sha256(raw), request_bytes=len(raw), request_description_sha256=c.sha256(descriptor),
                    response_sha256=c.sha256(response), response_bytes=len(response))
        c.write_new(directory / "block-A.response.body", response)
        c.write_new(directory / "block-A.metadata.json", c.json_bytes(meta))
        report = validate(directory)
        c.write_new(directory / "validation.json", c.json_bytes(report))
    except (Exception, KeyboardInterrupt) as exc:
        c.write_new(directory / "stopped.json", c.json_bytes({"error": f"{type(exc).__name__}: {exc}", "attempts": 1, "automatic_retry": False}))
        raise
    print("Single-block comparison saved; no bulk retention or weekly reconciliation established.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("plan", help="OFFLINE: print the one prepared GET and controls")
    p.add_argument("--output", type=Path)
    subs.add_parser("collect", help="LIVE/manual: exactly one anonymous GET; no retries or fallback")
    p = subs.add_parser("validate", help="OFFLINE: compare one saved document with canonical A")
    p.add_argument("--run-dir", required=True, type=Path)
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
        print(f"Stopped: {exc}. No automatic retry, credentials or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
