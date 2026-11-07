"""Final manually invoked status request for the single selected internal credit.

plan/validate are offline; collect makes exactly one credential-free request.
Existing origin collectors remain unchanged because their hashes are evidence.
No lookback, retry, fallback or recursive counterparty collection is supported.
"""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("credit_evidence", ROOT / "analysis/16_internal_credit_evidence.py")
credit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(credit)
c = credit.c
ORIGIN = ROOT / "results/internal_credit_origin_trace_2026-09-23/20261106T220603Z_aa17a137070d"
REQUEST = ROOT / "results/53_internal_credit_transaction_status_request_2026-09-23.json"
OUTPUT_ROOT = ROOT / "results/internal_credit_origin_trace_2026-09-23/credit_transaction_status"


def request():
    payload = credit.trace.status_request(credit.origin_saved(ORIGIN))
    payload["id"] = "internal-credit-transaction-status"
    return payload


def preflight():
    payload = request()
    c.require(REQUEST.read_bytes() == c.json_bytes(payload), "Prepared status request differs")
    manifest = c.decode((ORIGIN / "run.json").read_bytes())
    inputs = dict(manifest["input_hashes"])
    for p in [*ORIGIN.iterdir(), REQUEST, Path(__file__)]:
        c.require(p.is_file(), "Unexpected origin capture structure")
        raw = p.read_bytes()
        inputs[str(p.relative_to(ROOT))] = {"sha256": c.sha256(raw), "bytes": len(raw)}
    return payload, inputs


def validate_result(result):
    """Validate transaction and target logs, leaving full economic review offline."""
    payload = request()
    selected = credit.preflight()["selected_credit"]
    document = credit.preflight()
    source = next(r for r in document["decoded_records"] if r["receipt_id"] == selected["receipt_id"])
    c.require(isinstance(result, dict) and result.get("final_execution_status") == "FINAL", "Nonfinal/partial result")
    tx = result.get("transaction", {})
    c.require(tx.get("hash") == payload["params"]["tx_hash"]
              and tx.get("signer_id") == payload["params"]["sender_account_id"], "Transaction/signer mismatch")
    outcomes = result.get("receipts_outcome")
    receipts = result.get("receipts")
    c.require(isinstance(outcomes, list) and isinstance(receipts, list) and outcomes, "Receipt data unavailable")
    for records, key in ((outcomes, "id"), (receipts, "receipt_id")):
        ids = [r.get(key) for r in records]
        c.require(all(isinstance(v, str) and v for v in ids) and len(ids) == len(set(ids)), "Missing/duplicate receipt IDs")
    matches = [r for r in outcomes if r["id"] == selected["receipt_id"]]
    c.require(len(matches) == 1, "Selected credit outcome unavailable/ambiguous")
    item = matches[0]
    outcome = item.get("outcome", {})
    c.require(item.get("block_hash") == selected["block_hash"]
              and outcome.get("executor_id") == "intents.near" and "SuccessValue" in outcome.get("status", {})
              and outcome.get("logs") == [e["raw_log"] for e in source["events"]]
              and outcome.get("receipt_ids") == selected["child_receipt_ids"], "Credit observations differ from result 50")
    returned = [r for r in receipts if r["receipt_id"] == selected["receipt_id"]]
    if not returned:
        # A same-account transaction can omit its initial receipt payload.
        root = result.get("transaction_outcome", {})
        c.require(tx.get("signer_id") == tx.get("receiver_id") == "intents.near"
                  and root.get("id") == tx["hash"]
                  and selected["receipt_id"] in root.get("outcome", {}).get("receipt_ids", []),
                  "Missing credit payload is not an established initial-receipt omission")
    return {"validation": "TRANSACTION_AND_TARGET_LOGS_VALIDATED_GRAPH_REVIEW_PENDING",
            "transaction_hash": tx["hash"], "receipt_id": selected["receipt_id"],
            "revenue_attribution": None, "verified_fee_amount": None,
            "boundary": "Final request for one candidate credit; no upstream history or additional lookback."}


def validate_saved(directory):
    preflight()
    manifest = c.decode((directory / "run.json").read_bytes())
    c.require(manifest.get("endpoint") == c.ENDPOINT and manifest.get("request_count") == 1
              and manifest.get("request") == request(), "Unexpected status capture manifest")
    c.require(len(list(directory.glob("*.metadata.json"))) == 1, "Expected exactly one status capture")
    for relative, expected in manifest["input_hashes"].items():
        p = (ROOT / relative).resolve()
        c.require(p.is_relative_to(ROOT), "Evidence input outside repository")
        raw = p.read_bytes()
        c.require(c.sha256(raw) == expected["sha256"] and len(raw) == expected["bytes"], "Changed status prerequisite")
    return validate_result(c.recorded(directory, request()))


def collect(output_root=OUTPUT_ROOT, transport=None, pause=None):
    payload, inputs = preflight()
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    c.write_new(directory / "run.json", c.json_bytes({"endpoint": c.ENDPOINT, "created_at": c.utc_now(),
        "request_count": 1, "request": payload, "input_hashes": inputs,
        "spacing_seconds": c.SPACING_SECONDS, "connect_timeout_seconds": c.CONNECT_TIMEOUT,
        "request_timeout_seconds": c.REQUEST_TIMEOUT}))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    report = validate_result(c.capture(directory, payload, transport, pause))
    c.write_new(directory / "validation.json", c.json_bytes(report))
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("plan", help="OFFLINE: validate inputs and print the final request")
    subs.add_parser("collect", help="LIVE: one final status request; no retries or fallback")
    validate = subs.add_parser("validate", help="OFFLINE: check one saved status capture")
    validate.add_argument("--status-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            payload, _ = preflight()
            print(json.dumps({"endpoint": c.ENDPOINT, "request": payload, "request_count": 1,
                              "output_root": str(OUTPUT_ROOT)}, indent=2))
        elif args.command == "collect":
            collect()
        else:
            print(c.json_bytes(validate_saved(args.status_dir)).decode(), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}. No retry, fallback or broader collection.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
