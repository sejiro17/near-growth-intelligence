"""Manually invoked, staged RPC capture for two fixed September 2026 blocks.

stage1: six requests; stage2: two requests after offline stage1 validation.
validate-stage1 / validate-stage2 never access the network. No witness requests.

Endpoint and method references:
https://docs.near.org/api/rpc/providers
https://docs.near.org/api/rpc/block-chunk
https://docs.near.org/api/rpc/protocol
https://docs.near.org/api/rpc/contracts#view-account-changes

Successful validation establishes observed-response consistency only. The RPC
does not supply a proof of retained state-change coverage across all shards.
"""

import argparse
import hashlib
import http.client
import json
import re
import ssl
import sys
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTIC = ROOT / "results/42_supply_validator_event_diagnostic_2026-09-23.json"
DIAGNOSTIC_SHA256 = "0aa9b53e0ba261d2ad468bf0f16c769a08fe5c21a717ca943845adb8d0514e64"
OUTPUT_ROOT = ROOT / "results/canonical_rpc_2026-09-23"
ENDPOINT = "https://archival-rpc.mainnet.near.org"
HOST = "archival-rpc.mainnet.near.org"
SPACING_SECONDS = 65
CONNECT_TIMEOUT = 15
REQUEST_TIMEOUT = 60
TARGETS = {
    "A": {
        "height": 216877934,
        "hash": "HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG",
        "parent": "FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2",
        "saved_records": 302,
    },
    "B": {
        "height": 216921134,
        "hash": "J6jyjUSFFatXnCKEG3nKaD9qQLzQrY4xWyFkB5a5mJHB",
        "parent": "2Q7yUNdaLfnTkWduSkMYJfueFFg7dgHYpMb4chiS5MZi",
        "saved_records": 390,
    },
}
LIMITATION = "Observed responses only; all-shard historical retention is not independently verified."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(raw, parse_float=Decimal, parse_constant=invalid,
                      object_pairs_hook=unique)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()


def write_new(path, raw):
    with path.open("xb") as handle:
        handle.write(raw)


def account_id(value):
    require(isinstance(value, str) and 2 <= len(value) <= 64
            and re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value),
            "Invalid or missing account ID")
    return value


def integer(value, label):
    require(type(value) is int and value >= 0, f"Invalid integer: {label}")
    return value


def money(value, label):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]+", value)
            and int(value) < 2**128, f"Expected exact yoctoNEAR string: {label}")


def saved_accounts(raw):
    """Read the pinned flattened display export without altering it."""
    require(sha256(raw) == DIAGNOSTIC_SHA256, "Result 42 checksum changed; review input first")
    rows = decode(raw)
    require(isinstance(rows, list), "Result 42 must be a JSON array")
    all_ids, by_target = set(), {label: set() for label in TARGETS}
    current = None
    parents = 0
    for row in rows:
        require(isinstance(row, dict), "Malformed result 42 object")
        if "row_kind" in row:
            parents += 1
            require(row.get("observation_date") == "2026-09-23", "Wrong diagnostic date")
            current = next((label for label, target in TARGETS.items()
                            if row.get("block_hash") == target["hash"]), None)
            if current:
                target = TARGETS[current]
                require(row.get("block_height") == str(target["height"])
                        and row.get("declared_previous_block_hash") == target["parent"],
                        "Diagnostic block identity mismatch")
        value = row.get("validator_account_audit.affected_account_id")
        if value is not None:
            all_ids.add(account_id(value))
            if current:
                require(value not in by_target[current], "Duplicate saved validator account")
                by_target[current].add(value)
    require(parents == 4 and len(all_ids) == 462, "Incomplete diagnostic population")
    for label, target in TARGETS.items():
        require(len(by_target[label]) == target["saved_records"], "Incomplete saved event audit")
    return all_ids, by_target


def request(label, kind, ids=None):
    target = TARGETS[label]
    methods = {"block": "block", "protocol": "EXPERIMENTAL_protocol_config",
               "effects": "block_effects", "changes": "changes"}
    params = {"block_id": target["height"] if kind == "block" else target["hash"]}
    if kind == "changes":
        require(ids and len(ids) == len(set(ids)), "Empty or duplicate account union")
        params.update(changes_type="account_changes", account_ids=sorted(ids))
    return {"jsonrpc": "2.0", "id": f"{label}-{kind}",
            "method": methods[kind], "params": params}


def envelope(raw, payload):
    value = decode(raw)
    require(isinstance(value, dict), "Ambiguous response: expected one JSON-RPC object")
    require("error" not in value, f"JSON-RPC error: {value.get('error')}")
    require(value.get("jsonrpc") == "2.0" and value.get("id") == payload["id"],
            "JSON-RPC identity mismatch")
    result = value.get("result")
    require(isinstance(result, dict) and "error" not in result, "Missing or erroneous RPC result")
    return result


def validate_block(result, target):
    header = result.get("header", {})
    require(header.get("hash") == target["hash"]
            and header.get("height") == target["height"]
            and header.get("prev_hash") == target["parent"], "Wrong block/parent identity")
    money(header.get("total_supply"), "total_supply")
    timestamp = header.get("timestamp_nanosec", header.get("timestamp"))
    require(isinstance(timestamp, (str, int)) and not isinstance(timestamp, bool)
            and str(timestamp).isdigit(), "Missing exact block timestamp")
    day = datetime.fromtimestamp(int(timestamp) // 10**9, timezone.utc).date().isoformat()
    require(day == "2026-09-23", "Wrong block date")
    chunks = result.get("chunks")
    require(isinstance(chunks, list) and chunks, "Missing chunk-header manifest")
    shards = set()
    for chunk in chunks:
        shard = integer(chunk.get("shard_id"), "shard_id")
        require(shard not in shards, "Duplicate shard in block manifest")
        shards.add(shard)
        require(isinstance(chunk.get("chunk_hash"), str) and chunk["chunk_hash"], "Missing chunk hash")
        created = integer(chunk.get("height_created"), "height_created")
        included = integer(chunk.get("height_included"), "height_included")
        require(created <= included <= target["height"], "Ambiguous chunk inclusion heights")
    mask = header.get("chunk_mask")
    if mask is not None:
        require(isinstance(mask, list) and len(mask) == len(chunks)
                and all(type(x) is bool for x in mask), "Invalid chunk mask")
        require(mask == [c["height_included"] == target["height"] for c in chunks],
                "Chunk mask disagrees with inclusion heights")
    return shards


def validate_protocol(result, header_shards):
    require(result.get("chain_id") == "mainnet", "Wrong chain")
    require(result.get("protocol_version") == 86, "Unreviewed historical protocol version; stop")
    layout = result.get("shard_layout")
    require(isinstance(layout, dict) and len(layout) == 1, "Missing or ambiguous shard layout")
    version, fields = next(iter(layout.items()))
    require(isinstance(fields, dict), "Malformed shard layout")
    if version == "V0":
        count = integer(fields.get("num_shards"), "num_shards")
        require(0 < count <= 1024, "Invalid shard count")
        shards = set(range(count))
    elif version == "V1":
        boundaries = fields.get("boundary_accounts")
        require(isinstance(boundaries, list), "Missing shard boundaries")
        shards = set(range(len(boundaries) + 1))
    else:
        require(version in {"V2", "V3"}, "Unreviewed shard layout version")
        ids = fields.get("shard_ids")
        require(isinstance(ids, list) and ids, "Missing shard IDs")
        shards = {integer(x, "layout shard ID") for x in ids}
        require(len(shards) == len(ids), "Duplicate configured shard IDs")
    require(shards == header_shards, "Configured layout and header shards disagree; stop")


def touched_accounts(result, target, known):
    require(result.get("block_hash") == target["hash"], "Wrong effects block hash")
    changes = result.get("changes")
    require(isinstance(changes, list) and changes, "Empty effects: unavailable history is possible")
    ids, keys = set(), set()
    for change in changes:
        require(isinstance(change, dict) and isinstance(change.get("type"), str), "Malformed block effect")
        require(change["type"] in {"account_touched", "access_key_touched", "data_touched",
                                   "contract_code_touched"}, "Unreviewed block effect type")
        account_id(change.get("account_id"))
        if change["type"] == "account_touched":
            value = account_id(change.get("account_id"))
            require(value not in keys, "Duplicate account_touched effect")
            keys.add(value)
            ids.add(value)
    require(ids and known <= ids, "Effects omit saved validator IDs; ambiguous/partial history")
    return ids


def account_union(touched, saved):
    require(touched and len(saved) == 462, "Missing touched accounts or saved population")
    return sorted({account_id(x) for x in touched | saved})


def validate_changes(result, target, requested, touched, known):
    require(result.get("block_hash") == target["hash"], "Wrong account-changes block hash")
    changes = result.get("changes")
    require(isinstance(changes, list) and changes, "Empty changes: not evidence of no activity")
    observed, validators = set(), set()
    for change in changes:
        require(isinstance(change, dict) and isinstance(change.get("cause"), dict)
                and isinstance(change["cause"].get("type"), str), "Missing state-change cause")
        data = change.get("change")
        require(isinstance(data, dict), "Missing account change data")
        value = account_id(data.get("account_id"))
        require(value in requested, "Unrequested account in response")
        observed.add(value)
        require(change.get("type") in {"account_update", "account_deletion"}, "Unexpected account-change type")
        if change["type"] == "account_update":
            money(data.get("amount"), "amount")
            money(data.get("locked"), "locked")
        if change["cause"]["type"] == "validator_accounts_update":
            require(change["type"] == "account_update" and value not in validators,
                    "Ambiguous repeated/deleted validator update")
            validators.add(value)
    require(observed == touched, "Effects/changes membership disagrees; ambiguous/partial response")
    require(validators and known <= validators,
            "Saved validator updates not returned; absence versus partial history is unresolved")
    return validators


def fetch(payload):
    """Exactly one credential-free HTTPS attempt; no redirects or retries."""
    body = bytearray()
    result = {"http_status": None, "response_headers": [], "body_complete": False,
              "transport_error": None}
    response = None
    connection = http.client.HTTPSConnection(HOST, timeout=CONNECT_TIMEOUT,
                                             context=ssl.create_default_context())
    deadline = time.monotonic() + REQUEST_TIMEOUT
    try:
        connection.connect()
        active_socket = connection.sock
        active_socket.settimeout(max(1, deadline - time.monotonic()))
        connection.request("POST", "/", body=payload, headers={
            "Content-Type": "application/json", "Accept": "application/json",
            "Accept-Encoding": "identity", "Connection": "close",
            "User-Agent": "near-growth-intelligence-canonical-evidence/1",
        })
        response = connection.getresponse()
        result.update(http_status=response.status, response_headers=response.getheaders(),
                      http_version=response.version, http_reason=response.reason)
        while not response.isclosed():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Request deadline exceeded")
            active_socket.settimeout(remaining)
            chunk = response.read1(65536)
            if not chunk:
                break
            body.extend(chunk)
        require(response.length in (None, 0), "Truncated Content-Length response")
        result["body_complete"] = True
    except (Exception, KeyboardInterrupt) as exc:
        if isinstance(exc, http.client.IncompleteRead):
            body.extend(exc.partial)
        result["transport_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:
            response.close()
        connection.close()
    return result, bytes(body)


def capture(directory, payload, transport=None, pause=None):
    transport = fetch if transport is None else transport
    pause = time.sleep if pause is None else pause
    stem = payload["id"]
    raw = json_bytes(payload)
    write_new(directory / f"{stem}.request.json", raw)
    print(f"Waiting {SPACING_SECONDS}s before {stem}; one attempt, no retries.", flush=True)
    pause(SPACING_SECONDS)
    started = utc_now()
    metadata, response = transport(raw)
    metadata.update(endpoint=ENDPOINT, started_at=started, finished_at=utc_now(),
                    request_http_method="POST", request_path="/",
                    request_sha256=sha256(raw), response_sha256=sha256(response),
                    request_bytes=len(raw), response_bytes=len(response))
    write_new(directory / f"{stem}.response.body", response)
    write_new(directory / f"{stem}.metadata.json", json_bytes(metadata))
    require(metadata.get("body_complete") and not metadata.get("transport_error"),
            f"{stem}: incomplete transport; evidence retained, stop")
    require(metadata.get("http_status") == 200, f"{stem}: HTTP {metadata.get('http_status')}; stop")
    return envelope(response, payload)


def recorded(directory, payload):
    stem = payload["id"]
    raw = (directory / f"{stem}.request.json").read_bytes()
    response = (directory / f"{stem}.response.body").read_bytes()
    meta = decode((directory / f"{stem}.metadata.json").read_bytes())
    require(decode(raw) == payload, f"{stem}: unexpected saved request")
    require(meta.get("endpoint") == ENDPOINT and meta.get("body_complete")
            and not meta.get("transport_error") and meta.get("http_status") == 200,
            f"{stem}: failed or incomplete saved response")
    require(meta.get("request_sha256") == sha256(raw)
            and meta.get("response_sha256") == sha256(response)
            and meta.get("request_bytes") == len(raw)
            and meta.get("response_bytes") == len(response), f"{stem}: evidence checksum/length mismatch")
    started = datetime.fromisoformat(meta.get("started_at", ""))
    finished = datetime.fromisoformat(meta.get("finished_at", ""))
    require(started.utcoffset() == timezone.utc.utcoffset(started)
            and finished.utcoffset() == timezone.utc.utcoffset(finished)
            and finished >= started, f"{stem}: invalid UTC retrieval timestamps")
    return envelope(response, payload)


def run_input(run_dir):
    manifest = decode((run_dir / "run.json").read_bytes())
    require(manifest.get("endpoint") == ENDPOINT
            and manifest.get("diagnostic_sha256") == DIAGNOSTIC_SHA256,
            "Run endpoint or input provenance mismatch")
    return saved_accounts((run_dir / "diagnostic_input.json").read_bytes())


def validate_stage1(run_dir):
    saved, known = run_input(run_dir)
    require(len(list((run_dir / "stage1").glob("*.metadata.json"))) == 6,
            "Stage1 must contain six completed captures")
    unions, touched = {}, {}
    for label, target in TARGETS.items():
        shards = validate_block(recorded(run_dir / "stage1", request(label, "block")), target)
        validate_protocol(recorded(run_dir / "stage1", request(label, "protocol")), shards)
        touched[label] = touched_accounts(recorded(run_dir / "stage1", request(label, "effects")), target, known[label])
        unions[label] = account_union(touched[label], saved)
    return unions, touched, known


def collect_stage1(output_root=OUTPUT_ROOT, diagnostic=DIAGNOSTIC, transport=None, pause=None):
    raw = diagnostic.read_bytes()
    saved, known = saved_accounts(raw)
    output_root.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12]
    run_dir = output_root / name
    run_dir.mkdir()
    (run_dir / "stage1").mkdir()
    write_new(run_dir / "diagnostic_input.json", raw)
    write_new(run_dir / "run.json", json_bytes({
        "created_at": utc_now(), "endpoint": ENDPOINT,
        "diagnostic_source": str(diagnostic.resolve()), "diagnostic_sha256": sha256(raw),
        "spacing_seconds": SPACING_SECONDS, "connect_timeout_seconds": CONNECT_TIMEOUT,
        "request_timeout_seconds": REQUEST_TIMEOUT, "stage1_requests": 6, "stage2_requests": 2,
        "targets": TARGETS, "collector_sha256": sha256(Path(__file__).read_bytes()),
        "coverage_limitation": LIMITATION,
    }))
    print(f"Evidence directory: {run_dir.resolve()}", flush=True)
    for label, target in TARGETS.items():
        shards = validate_block(capture(run_dir / "stage1", request(label, "block"), transport, pause), target)
        validate_protocol(capture(run_dir / "stage1", request(label, "protocol"), transport, pause), shards)
        touched_accounts(capture(run_dir / "stage1", request(label, "effects"), transport, pause), target, known[label])
    unions, _, _ = validate_stage1(run_dir)
    write_new(run_dir / "stage1_validation.json", json_bytes({
        "status": "OBSERVED_RESPONSES_CONSISTENT", "union_counts": {k: len(v) for k, v in unions.items()},
        "coverage_limitation": LIMITATION,
    }))
    print("Stage1 complete. Review offline validation before invoking stage2.")
    return run_dir


def collect_stage2(run_dir, transport=None, pause=None):
    unions, touched, known = validate_stage1(run_dir)
    directory = run_dir / "stage2"
    directory.mkdir()  # An existing attempt is never overwritten or resumed.
    for label, target in TARGETS.items():
        ids = unions[label]
        result = capture(directory, request(label, "changes", ids), transport, pause)
        validate_changes(result, target, set(ids), touched[label], known[label])
    return validate_stage2(run_dir, write_report=True)


def validate_stage2(run_dir, write_report=False):
    unions, touched, known = validate_stage1(run_dir)
    require(len(list((run_dir / "stage2").glob("*.metadata.json"))) == 2,
            "Stage2 must contain two completed captures")
    counts = {}
    for label, target in TARGETS.items():
        result = recorded(run_dir / "stage2", request(label, "changes", unions[label]))
        ids = validate_changes(result, target, set(unions[label]), touched[label], known[label])
        counts[label] = len(ids)
    report = {"status": "OBSERVED_RESPONSES_CONSISTENT", "validator_account_counts": counts,
              "coverage_limitation": LIMITATION, "independently_measured_issuance": None,
              "independently_measured_actual_burn": None}
    if write_report:
        write_new(run_dir / "stage2_validation.json", json_bytes(report))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("stage1", help="LIVE: collect six requests into a fresh directory")
    for command in ("stage2", "validate-stage1", "validate-stage2"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage1":
            collect_stage1()
        elif args.command == "stage2":
            print(json.dumps(collect_stage2(args.run_dir), indent=2))
        elif args.command == "validate-stage1":
            unions, _, _ = validate_stage1(args.run_dir)
            print(json.dumps({"union_counts": {k: len(v) for k, v in unions.items()},
                              "coverage_limitation": LIMITATION}, indent=2))
        else:
            print(json.dumps(validate_stage2(args.run_dir), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Stopped: {exc}. No automatic retry or endpoint fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
