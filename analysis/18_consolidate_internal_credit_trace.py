"""Consolidate the completed single-credit trace using saved evidence only.

Default output is stdout; --output creates a new derived artifact exclusively.
All capture bytes and previously recorded collector hashes remain unchanged.
"""

import argparse
import base64
import importlib.util
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("credit_status", ROOT / "analysis/17_collect_internal_credit_status.py")
status = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(status)
c = status.c
CAPTURE = ROOT / "results/internal_credit_origin_trace_2026-09-23/credit_transaction_status/20261106T222108Z_637914f4225b"
OUTPUT = ROOT / "results/54_internal_credit_trace_consolidation_2026-09-23.json"


def interpret(result, document):
    selected = document["selected_credit"]
    tx = result["transaction"]
    c.require(result["final_execution_status"] == "FINAL" and result["status"] == {"SuccessValue": ""},
              "Transaction is incomplete or unsuccessful")
    c.require(tx["signer_id"] == tx["receiver_id"] == "intents.near" and len(tx["actions"]) == 1,
              "Unexpected initiating transaction")
    call = tx["actions"][0]["FunctionCall"]
    c.require(call["method_name"] == "execute_intents" and call["deposit"] == "0", "Unexpected method/deposit")
    raw = base64.b64decode(call["args"], validate=True)
    c.require(base64.b64encode(raw).decode() == call["args"], "Noncanonical argument encoding")
    args = c.decode(raw)
    c.require(len(args["signed"]) == 1, "Multiple signed messages; interpretation ambiguous")
    signed = args["signed"][0]
    message = c.decode(signed["payload"]["message"])
    c.require(signed["standard"] == "nep413" and signed["payload"]["recipient"] == "intents.near"
              and len(message["intents"]) == 1, "Unexpected signed-intent structure")
    intent = message["intents"][0]
    c.require(intent == {"intent": "transfer", "receiver_id": status.credit.ACCOUNT,
              "tokens": {status.credit.ASSET: selected["amount_base_units"]}, "memo": None}
              and message["signer_id"] == selected["old_owner_id"], "Signed transfer differs from result 50")
    status.credit.exact(intent["tokens"][status.credit.ASSET])
    source = next(r for r in document["decoded_records"] if r["receipt_id"] == selected["receipt_id"])
    executed = [x for e in source["events"] if e["decoded"]["event"] == "intents_executed"
                for x in e["decoded"]["data"]]
    c.require(len(executed) == 1 and signed["payload"]["nonce"] == executed[0]["nonce"]
              and len(base64.b64decode(signed["payload"]["nonce"], validate=True)) == 32,
              "Signed nonce differs from execution event")
    scheme, key = signed["public_key"].split(":", 1)
    alphabet, number = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz", 0
    for char in key:
        number = number * 58 + alphabet.index(char)
    key_bytes = b"\0" * (len(key) - len(key.lstrip("1"))) + number.to_bytes((number.bit_length() + 7) // 8, "big")
    c.require(scheme == "ed25519" and len(key_bytes) == 32 and key_bytes.hex() == message["signer_id"],
              "Public key does not match the internal signer account")
    outcomes = [result["transaction_outcome"], *result["receipts_outcome"]]
    by_id = {x["id"]: x for x in outcomes}
    parents = defaultdict(list)
    c.require(len(by_id) == len(outcomes) == 3, "Duplicate or unexpected outcome records")
    for outcome in outcomes:
        for child in outcome["outcome"]["receipt_ids"]:
            parents[child].append(outcome["id"])
    c.require(set(parents) == set(by_id) - {tx["hash"]} and all(len(v) == 1 for v in parents.values()),
              "Missing child outcome or ambiguous parent")
    credit_id = selected["receipt_id"]
    c.require(result["transaction_outcome"]["id"] == tx["hash"]
              and result["transaction_outcome"]["outcome"]["status"] == {"SuccessReceiptId": credit_id}
              and result["transaction_outcome"]["outcome"]["receipt_ids"] == [credit_id]
              and all(x["outcome"]["status"] == {"SuccessValue": ""} for x in result["receipts_outcome"]),
              "Unexpected creation path/status")
    c.require(len(result["receipts"]) == 1, "Unexpected application receipt/callback payloads")
    refund = result["receipts"][0]
    action = refund["receipt"]["Action"]
    c.require(refund["receipt_id"] == selected["child_receipt_ids"][0]
              and parents[refund["receipt_id"]] == [credit_id]
              and by_id[refund["receipt_id"]]["outcome"]["receipt_ids"] == []
              and refund["predecessor_id"] == "system" and refund["receiver_id"] == "intents.near"
              and action["gas_price"] == "0" and action["input_data_ids"] == action["output_data_receivers"] == []
              and len(action["actions"]) == 1 and "Transfer" in action["actions"][0],
              "Unexpected system-return/callback evidence")
    c.money(action["actions"][0]["Transfer"]["deposit"], "system return")
    return {"transaction_hash": tx["hash"], "network_signer": tx["signer_id"], "transaction_receiver": tx["receiver_id"],
        "network_signer_public_key": tx["public_key"], "method": call["method_name"],
        "raw_args_base64": call["args"], "decoded_args_utf8": raw.decode("utf-8"), "signed_message": message,
        "signed_intent_public_key": signed["public_key"], "public_key_account_mapping": "MATCHES",
        "internal_sender": message["signer_id"], "internal_recipient": intent["receiver_id"],
        "asset": status.credit.ASSET, "amount_base_units": selected["amount_base_units"],
        "amount_near_equivalent": document["comparison"]["amount_near"], "memo": intent["memo"],
        "receipt_path": [tx["hash"], credit_id, refund["receipt_id"]],
        "receipt_outcome_count": 2, "returned_receipt_payload_count": 1,
        "system_return_amount_yoctonear": action["actions"][0]["Transfer"]["deposit"],
        "graph_validation": "Unique parent links and no missing child outcomes within the returned graph; no additional application callback payloads.",
        "payload_limitation": "Initial same-account receipt payload is omitted; initiating action is reconstructed from transaction.actions.",
        "mechanism": "SUCCESSFUL_SIGNED_INTERNAL_TRANSFER",
        "economic_classification": "UNCLASSIFIED_INTERNAL_TRANSFER_CREDIT",
        "verified_fee_amount": None, "withdrawal_revenue_origin": None,
        "limitations": ["Public-key/account correspondence does not establish organizational ownership or fee-collector role.",
            "No fee calculation, swap intent or APP_FEE memo occurs in this signed message; this does not exclude earlier fee funding.",
            "Opening balance, commingling and allocation to the subsequent withdrawal remain unresolved.",
            "No independently measured native burn or buyback is established."]}


def report():
    status.validate_saved(CAPTURE)
    result = c.recorded(CAPTURE, status.request())
    document = status.credit.preflight()
    conclusion = interpret(result, document)
    _, inputs = status.preflight()
    for path in [*CAPTURE.iterdir(), Path(__file__)]:
        c.require(path.is_file(), "Unexpected capture structure")
        raw = path.read_bytes()
        inputs[str(path.relative_to(ROOT))] = {"sha256": c.sha256(raw), "bytes": len(raw)}
    return {"input_hashes": inputs,
        "derivation_method": "Validate saved HTTP/JSON-RPC/checksums and input provenance; compare target logs with result 50; strictly decode base64/JSON; validate exact integer transfer, signed account/nonce and unique returned outcome graph.",
        "credit_trace": conclusion, "subsequent_withdrawal_comparison": document["comparison"],
        "closure": {"single_candidate_trace": "COMPLETE", "fee_origin": "UNRESOLVED",
            "additional_collection": "NONE; agreed one-candidate boundary reached"},
        "priority3_preparation": document["priority3_preparation"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = c.json_bytes(report())
        if args.output:
            c.write_new(args.output, raw)
        else:
            print(raw.decode(), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Validation stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
