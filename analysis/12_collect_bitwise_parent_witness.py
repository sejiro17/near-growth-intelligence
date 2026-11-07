"""One manually invoked historical account request; plan/validate are offline.

Uses the existing collector's byte-preserving capture, pacing and error handling.
Endpoint reference: https://docs.near.org/api/rpc/providers
Method reference: https://docs.near.org/api/rpc/contracts#view-account
No monetary change, issuance or burn is calculated by this collector.
"""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canonical_capture", ROOT / "analysis/11_collect_canonical_validator_evidence.py")
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)

ACCOUNT = "bitwise_1.poolv1.near"
PARENT_HASH = "FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2"
PARENT_HEIGHT = 216877933
CANONICAL_RUN = ROOT / "results/canonical_rpc_2026-09-23/20261106T133436Z_2e1218e30fbc"
COMPARISON = ROOT / "results/43_canonical_rpc_bigquery_comparison_2026-09-23.json"
PROVENANCE = COMPARISON.with_suffix(".provenance.json")
COMPARISON_SHA256 = "97cab9a4c9b54adae0b1862fcd40a2b620106173af26582251f679a9c7be27bb"
REQUEST = ROOT / "results/44_bitwise_parent_account_request_2026-09-23.json"
OUTPUT_ROOT = ROOT / "results/canonical_rpc_2026-09-23/bitwise_parent_witness"


def request():
    return {"jsonrpc": "2.0", "id": "A-bitwise-parent-account", "method": "query",
            "params": {"request_type": "view_account", "account_id": ACCOUNT,
                       "block_id": PARENT_HASH}}


def preflight():
    """Validate saved evidence and the prepared request without network access."""
    require = capture.require
    capture.validate_stage2(CANONICAL_RUN)
    provenance = capture.decode(PROVENANCE.read_bytes())
    require(capture.sha256(COMPARISON.read_bytes()) == COMPARISON_SHA256
            == provenance.get("sha256"), "Derived comparison checksum mismatch")
    inputs = provenance["inputs"]
    for relative, expected in inputs.items():
        path = ROOT / relative
        raw = path.read_bytes()
        require(capture.sha256(raw) == expected["sha256"] and len(raw) == expected["bytes"],
                f"Changed comparison input: {relative}")
    raw = REQUEST.read_bytes()
    require(capture.decode(raw) == request() and raw == capture.json_bytes(request()),
            "Prepared request bytes or parameters differ")
    block = capture.recorded(CANONICAL_RUN / "stage1", capture.request("A", "block"))
    require(block["header"]["prev_hash"] == PARENT_HASH
            and block["header"]["height"] == PARENT_HEIGHT + 1,
            "Saved block A predecessor differs")
    result = capture.recorded(CANONICAL_RUN / "stage2", capture.request(
        "A", "changes", capture.validate_stage1(CANONICAL_RUN)[0]["A"]))
    records = [(i, x) for i, x in enumerate(result["changes"])
               if x["change"]["account_id"] == ACCOUNT]
    require(len(records) == 1 and records[0][1]["type"] == "account_update"
            and records[0][1]["cause"]["type"] == "validator_accounts_update",
            "Ambiguous saved validator post-state")
    comparison = capture.decode(COMPARISON.read_bytes())
    require(ACCOUNT in comparison["blocks"]["A"]["membership"]["rpc_only_validator_accounts"],
            "Witness account is not an omitted block-A observation")
    return {**inputs, **{
        str(p.relative_to(ROOT)): {"sha256": capture.sha256(p.read_bytes()),
                                  "bytes": p.stat().st_size}
        for p in (COMPARISON, PROVENANCE, REQUEST, Path(__file__))}}, records[0][0]


def validate_account(result):
    capture.require(result.get("block_hash") == PARENT_HASH
                    and type(result.get("block_height")) is int
                    and result["block_height"] == PARENT_HEIGHT,
                    "Historical account response block identity mismatch")
    for field in ("amount", "locked"):
        capture.money(result.get(field), field)
    capture.integer(result.get("storage_usage"), "storage_usage")
    capture.require(isinstance(result.get("code_hash"), str) and result["code_hash"],
                    "Missing account code hash; incomplete response")
    if "account_id" in result:
        capture.require(result["account_id"] == ACCOUNT, "Wrong response account ID")
    if "storage_paid_at" in result:
        capture.integer(result["storage_paid_at"], "storage_paid_at")


def validate_saved(directory):
    capture.require(len(list(directory.glob("*.metadata.json"))) == 1,
                    "Expected exactly one saved capture")
    manifest = capture.decode((directory / "run.json").read_bytes())
    capture.require(manifest.get("endpoint") == capture.ENDPOINT
                    and manifest.get("request_count") == 1,
                    "Unexpected witness manifest")
    for relative, expected in manifest["input_hashes"].items():
        raw = (ROOT / relative).read_bytes()
        capture.require(capture.sha256(raw) == expected["sha256"]
                        and len(raw) == expected["bytes"], f"Changed witness input: {relative}")
    validate_account(capture.recorded(directory, request()))
    return {"status": "OBSERVED_RESPONSE_IDENTITY_VALIDATED", "account_id": ACCOUNT,
            "block_hash": PARENT_HASH, "block_height": PARENT_HEIGHT,
            "account_identity_basis": "Recorded request and JSON-RPC ID; account ID need not be echoed.",
            "monetary_change": None, "independently_measured_issuance": None,
            "independently_measured_actual_burn": None}


def collect(output_root=OUTPUT_ROOT, transport=None, pause=None):
    inputs, position = preflight()
    output_root.mkdir(parents=True, exist_ok=True)
    name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12]
    directory = output_root / name
    directory.mkdir()
    capture.write_new(directory / "run.json", capture.json_bytes({
        "created_at": capture.utc_now(), "endpoint": capture.ENDPOINT, "request_count": 1,
        "input_hashes": inputs, "post_state_response_array_index": position,
        "post_state_block_hash": capture.TARGETS["A"]["hash"],
        "spacing_seconds": capture.SPACING_SECONDS,
        "connect_timeout_seconds": capture.CONNECT_TIMEOUT,
        "request_timeout_seconds": capture.REQUEST_TIMEOUT,
        "interpretation": "One account before-state; no daily-total adjustment or issuance measurement.",
    }))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    result = capture.capture(directory, request(), transport, pause)
    validate_account(result)
    report = validate_saved(directory)
    capture.write_new(directory / "validation.json", capture.json_bytes(report))
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("plan", help="OFFLINE: validate inputs and print the one prepared request")
    subs.add_parser("collect", help="LIVE: make exactly one request; no retries or fallback")
    validator = subs.add_parser("validate", help="OFFLINE: validate one saved witness capture")
    validator.add_argument("--witness-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            preflight()
            print(json.dumps({"endpoint": capture.ENDPOINT, "request_count": 1,
                              "request": request()}, indent=2))
        elif args.command == "collect":
            collect()
        else:
            print(json.dumps(validate_saved(args.witness_dir), indent=2))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Stopped: {exc}. No automatic retry or endpoint fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
