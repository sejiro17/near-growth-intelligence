"""Two separately invoked manual RPC stages for one receipt's origin trace.

plan and prepare-status are offline. Each collect command makes exactly one
request through the existing byte-preserving collector, without retries/fallback.
Origin lookup omits scan hints: it requires the historical receipt-origin index.
Reference: https://docs.near.org/api-reference/post-experimental_receipt_to_tx
Implementation: near/nearcore, tag 2.13.3, chain/client/src/view_client_actor.rs.
Transaction details: https://docs.near.org/api/rpc/transactions
"""

import argparse
import importlib.util
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


decoder = module("frontend_decoder", "14_decode_frontend_native_transfers.py")
capture = module("origin_capture", "11_collect_canonical_validator_evidence.py")
RECEIPT = "5z6sNxeEzHdQuU1P8j7o5DiTcLxXJdHj9nbFvX5H1wFK"
SOURCE_SHA256 = "d69601fb513e4276eaa0db9126ee415a2899768eca5f599034f822570992f9cf"
REQUEST = ROOT / "results/49_frontend_transfer_origin_request_2026-09-23.json"
OUTPUT_ROOT = ROOT / "results/frontend_origin_trace_2026-09-23"


def origin_request():
    return {"jsonrpc": "2.0", "id": "transfer-origin",
            "method": "EXPERIMENTAL_receipt_to_tx", "params": {"receipt_id": RECEIPT}}


def target():
    report = decoder.report()
    capture.require(report["source"]["sha256"] == SOURCE_SHA256, "Result 47 changed")
    matches = [row for row in report["transfers"] if row["receipt_id"] == RECEIPT]
    capture.require(len(matches) == 1, "Missing/ambiguous target action")
    row = matches[0]
    capture.require(row["block_height"] == 216859521
                    and row["block_hash"] == "8gAqfFuPUhwZwwKy1uyEW2wSXyiSbX6A44kS3UR28ajH"
                    and row["amount_yoctonear"] == "1252862790024676320487808800",
                    "Target identity or amount differs")
    capture.require(REQUEST.read_bytes() == capture.json_bytes(origin_request()),
                    "Prepared origin request differs")
    return row


def validate_origin(result):
    capture.require(isinstance(result, dict)
                    and isinstance(result.get("transaction_hash"), str)
                    and re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", result["transaction_hash"]),
                    "Missing/invalid originating transaction hash")
    text = result["transaction_hash"]
    number = 0
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    for character in text:
        number = number * 58 + alphabet.index(character)
    capture.require(len(text) - len(text.lstrip("1")) + (number.bit_length() + 7) // 8 == 32,
                    "Transaction hash must decode to 32 bytes")
    capture.account_id(result.get("sender_account_id"))
    return result


def recorded_origin(directory):
    target()
    capture.require(len(list(directory.glob("*.metadata.json"))) == 1,
                    "Expected exactly one origin capture")
    manifest = capture.decode((directory / "run.json").read_bytes())
    capture.require(manifest.get("endpoint") == capture.ENDPOINT
                    and manifest.get("request_count") == 1
                    and manifest.get("request") == origin_request(), "Wrong origin manifest")
    for path, expected in manifest["input_hashes"].items():
        input_path = (ROOT / path).resolve()
        capture.require(input_path.is_relative_to(ROOT), "Origin input outside repository")
        raw = input_path.read_bytes()
        capture.require(capture.sha256(raw) == expected["sha256"] and len(raw) == expected["bytes"],
                        f"Changed origin input: {path}")
    return validate_origin(capture.recorded(directory, origin_request()))


def status_request(origin):
    validate_origin(origin)
    return {"jsonrpc": "2.0", "id": "transfer-transaction-status",
            "method": "EXPERIMENTAL_tx_status",
            "params": {"tx_hash": origin["transaction_hash"],
                       "sender_account_id": origin["sender_account_id"], "wait_until": "FINAL"}}


def validate_status_identity(result, origin):
    """Identity gate only; receipt graph/callback completeness requires offline review."""
    capture.require(isinstance(result, dict) and result.get("final_execution_status") == "FINAL",
                    "Unavailable or nonfinal transaction details")
    tx = result.get("transaction", {})
    capture.require(tx.get("hash") == origin["transaction_hash"]
                    and tx.get("signer_id") == origin["sender_account_id"], "Wrong transaction/signer")
    outcomes = result.get("receipts_outcome")
    receipts = result.get("receipts")
    capture.require(isinstance(outcomes, list) and isinstance(receipts, list) and outcomes and receipts,
                    "Missing receipt details/outcomes; historical coverage unresolved")
    for items, field in ((outcomes, "id"), (receipts, "receipt_id")):
        ids = [x.get(field) for x in items]
        capture.require(all(isinstance(x, str) and x for x in ids) and len(set(ids)) == len(ids),
                        "Missing/duplicate receipt identity; no canonical selection")
    matches = [x for x in outcomes if x["id"] == RECEIPT]
    payloads = [x for x in receipts if x["receipt_id"] == RECEIPT]
    saved = target()
    capture.require(len(matches) == len(payloads) == 1, "Target absent/ambiguous in transaction details")
    item, receipt = matches[0], payloads[0]
    capture.require(item.get("block_hash") == saved["block_hash"]
                    and item.get("outcome", {}).get("executor_id") == saved["receiver_account_id"]
                    and isinstance(item["outcome"].get("status"), dict)
                    and "SuccessValue" in item["outcome"]["status"], "Target execution identity/status differs")
    capture.require(receipt.get("predecessor_id") == saved["predecessor_account_id"]
                    and receipt.get("receiver_id") == saved["receiver_account_id"], "Target counterparties differ")
    actions = receipt.get("receipt", {}).get("Action", {}).get("actions", [])
    capture.require(len(actions) > saved["action_index"]
                    and actions[saved["action_index"]] == {"Transfer": {"deposit": saved["amount_yoctonear"]}},
                    "Target exact Transfer deposit differs")


def collect(payload, output_root=OUTPUT_ROOT, origin_dir=None, transport=None, pause=None):
    """One explicit invocation, one request, immutable capture files."""
    target()
    capture.require(payload == origin_request() or (origin_dir is not None
                    and payload == status_request(recorded_origin(origin_dir))), "Unapproved trace request")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                               + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    paths = [decoder.SOURCE, REQUEST, Path(__file__), Path(decoder.__file__), Path(capture.__file__)]
    inputs = {str(p.relative_to(ROOT)): {k: v for k, v in decoder.fingerprint(p).items() if k != "path"}
              for p in paths}
    if origin_dir:
        # Save the complete prerequisite origin capture as a local snapshot,
        # retaining exact bytes even if its original directory is moved later.
        snapshot = directory / "origin_input"
        snapshot.mkdir()
        for path in sorted(origin_dir.iterdir()):
            if path.is_file():
                capture.write_new(snapshot / path.name, path.read_bytes())
    capture.write_new(directory / "run.json", capture.json_bytes({
        "endpoint": capture.ENDPOINT, "created_at": capture.utc_now(),
        "request_count": 1, "request": payload, "input_hashes": inputs,
        "spacing_seconds": capture.SPACING_SECONDS,
        "interpretation": "Origin/transaction identity evidence only; payments remain UNCLASSIFIED_TRANSFER."}))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    result = capture.capture(directory, payload, transport, pause)
    if payload == origin_request():
        validate_origin(result)
    else:
        validate_status_identity(result, recorded_origin(origin_dir))
        print("Transaction/target identity checks passed. Parent graph, callbacks and attribution require offline review.", flush=True)
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("plan", help="OFFLINE: print prepared first request")
    subs.add_parser("collect-origin", help="LIVE: exactly one index-only origin request")
    prepare = subs.add_parser("prepare-status", help="OFFLINE: validate origin capture; print next request")
    prepare.add_argument("--origin-dir", required=True, type=Path)
    collect_status = subs.add_parser("collect-status", help="LIVE: exactly one transaction-status request")
    collect_status.add_argument("--origin-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        target()
        if args.command == "plan":
            print(json.dumps({"endpoint": capture.ENDPOINT, "request_count": 1,
                              "request": origin_request(), "output_root": str(OUTPUT_ROOT),
                              "historical_index_availability": "UNVERIFIED; stop on lookup error",
                              "second_stage": "After validating saved origin response: EXPERIMENTAL_tx_status with returned transaction_hash and sender_account_id, wait_until FINAL; one separate manual invocation.",
                              "offline_review_criteria": [
                                  "Group outcomes by id and receipt payloads by receipt_id; retain duplicates as ambiguity, never select one or multiply joins.",
                                  "Find the unique outcome whose receipt_ids contains the target; walk unique parent edges to transaction_outcome. A missing edge leaves ancestry unresolved.",
                                  "Retain transaction signer/actions and every parent receipt action in order, including raw FunctionCall args and logs/status. Multiple function calls may prevent attribution to one action.",
                                  "Match the target's exact block hash, predecessor, receiver, action index and integer deposit; verify saved child receipt IDs against RPC receipt_ids.",
                                  "Check all child outcome links and match output_data_receivers data_id/receiver_id to callback input_data_ids. Missing payloads or outcomes are unavailable evidence, not successful settlement.",
                                  "FINAL and top-level success do not prove every callback succeeded. Retain each receipt's status and inspect settlement/refund callbacks.",
                                  "The same-account initial receipt can be omitted from receipts; distinguish transaction-action reconstruction from a returned receipt payload.",
                                  "A withdrawal mechanism alone does not establish whether the withdrawn balance came from fees, principal, refunds or internal movements."
                              ]}, indent=2))
        elif args.command == "collect-origin":
            collect(origin_request())
        else:
            origin = recorded_origin(args.origin_dir)
            payload = status_request(origin)
            if args.command == "prepare-status":
                print(capture.json_bytes(payload).decode(), end="")
            else:
                collect(payload, origin_dir=args.origin_dir)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Stopped: {exc}. No retry, scan hints or endpoint fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
