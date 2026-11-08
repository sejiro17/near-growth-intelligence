"""Four-slot, five-candidate Sweat -> jars diagnostic; no pagination or retries.

collect explicitly accesses free documented history/status APIs. report is offline.
Each stage reuses matching validated captures or consumes one immutable slot.
"""

import argparse
import base64
import importlib.util
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jars_transport", ROOT/"analysis/42_trace_wx_cruce.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)
c = w.c
SIGNER = "sweat-relayer.near"
RECEIVER = "jars-oracle.sweat"
OUTPUT = ROOT/"results/sweat_jars_attribution_2026-09-23"
ARTIFACT = ROOT/"results/106_sweat_jars_selected_mechanism_2026-09-23.json"
STAGES = ("history", "details", "status", "header")


def history_request():
    lower, upper = w.day_bounds()
    return {"account_id": RECEIVER, "is_receiver": True, "from_tx_block_height": lower,
            "to_tx_block_height": upper, "limit": 5, "desc": False}


def history_identity(result):
    c.require(isinstance(result, dict) and "error" not in result, "History API error")
    rows = result.get("account_txs")
    c.require(isinstance(rows, list) and 1 <= len(rows) <= 5, "No candidates or five-candidate cap exceeded; stop without pagination")
    lower, upper = w.day_bounds()
    hashes, positions = set(), []
    for row in rows:
        w.trace.hash_id(row.get("transaction_hash"))
        c.require(row.get("account_id") == RECEIVER and row.get("is_receiver") is True, "Wrong indexed receiver role")
        height, index = (c.integer(row.get(k), k) for k in ("tx_block_height", "tx_index"))
        stamp = row.get("tx_block_timestamp")
        c.require(lower <= height < upper and isinstance(stamp, str) and stamp.isascii() and stamp.isdigit()
                  and datetime.fromtimestamp(int(stamp)//10**9, timezone.utc).date().isoformat() == "2026-09-23", "Candidate outside selected day")
        c.require(row["transaction_hash"] not in hashes, "Duplicate candidate hash")
        hashes.add(row["transaction_hash"])
        positions.append((height, index))
    c.require(positions == sorted(set(positions)), "Ambiguous/unordered candidate positions")
    return rows


def directory(stage):
    return ROOT/c.decode((OUTPUT/(stage+".attempt.json")).read_bytes())["directory"]


def load(stage, endpoint, payload):
    reuse = OUTPUT/(stage+".reuse.json")
    if reuse.exists():
        reference = c.decode(reuse.read_bytes())
        original = ROOT/reference["request_path"]
        c.require(w.trace.identity(original) == reference["request_identity"], "Reused request changed")
        return read_reusable(original, endpoint, payload)
    return w.saved(directory(stage), stage, endpoint, payload)


def page():
    return history_identity(load("history", w.HISTORY_ENDPOINT, history_request()))


def details_request():
    return {"tx_hashes": [r["transaction_hash"] for r in page()]}


def select(result, candidates):
    c.require(isinstance(result, dict) and "error" not in result, "Indexed details API error")
    items = result.get("transactions")
    c.require(isinstance(items, list) and len(items) == len(candidates) <= 5, "Partial or oversized indexed batch")
    expected = {r["transaction_hash"]: r for r in candidates}
    observed, eligible, audit = set(), [], []
    for item in items:
        tx = item.get("transaction", {})
        txhash = tx.get("hash")
        c.require(txhash in expected and txhash not in observed, "Unknown/duplicate indexed identity")
        observed.add(txhash)
        c.account_id(tx.get("signer_id")); c.account_id(tx.get("receiver_id"))
        c.require(isinstance(tx.get("actions"), list) and tx["actions"], "Missing indexed actions")
        matches = tx["signer_id"] == SIGNER and tx["receiver_id"] == RECEIVER
        audit.append({"transaction_hash": txhash, "network_signer": tx["signer_id"],
                      "receiver": tx["receiver_id"], "eligible": matches})
        if matches:
            eligible.append((expected[txhash], tx))
    c.require(observed == set(expected), "Missing indexed candidate")
    c.require(eligible, "No Sweat-to-jars candidate among at most five records; no further lookup")
    candidate, tx = min(eligible, key=lambda pair: (pair[0]["tx_block_height"], pair[0]["tx_index"]))
    return candidate, tx, audit


def selection():
    return select(load("details", w.TRANSACTIONS_ENDPOINT, details_request()), page())


def status_request(candidate):
    return {"jsonrpc": "2.0", "id": "jars-transaction-status", "method": "EXPERIMENTAL_tx_status",
            "params": {"tx_hash": candidate["transaction_hash"], "sender_account_id": SIGNER, "wait_until": "FINAL"}}


def status_gate(result, candidate, indexed):
    tx = result.get("transaction", {})
    c.require(result.get("final_execution_status") == "FINAL" and tx.get("hash") == candidate["transaction_hash"]
              and tx.get("signer_id") == SIGNER and tx.get("receiver_id") == RECEIVER, "Canonical signer/receiver/transaction conflict")
    c.require(tx["actions"] == indexed["actions"], "Indexed/canonical ordered actions differ")
    root = result.get("transaction_outcome", {})
    c.require(root.get("id") == tx["hash"] and root.get("outcome", {}).get("executor_id") == SIGNER, "Wrong transaction outcome")
    initial = root["outcome"].get("status", {}).get("SuccessReceiptId")
    c.require(initial is not None and initial in root["outcome"].get("receipt_ids", []), "No initial receipt from transaction conversion")
    outcomes = [r for r in result.get("receipts_outcome", []) if r.get("id") == initial]
    receipts = [r for r in result.get("receipts", []) if r.get("receipt_id") == initial]
    c.require(len(outcomes) == len(receipts) == 1 and outcomes[0]["outcome"]["executor_id"] == RECEIVER
              and receipts[0]["receiver_id"] == RECEIVER, "Missing/ambiguous initial receiver/outcome")
    status = outcomes[0]["outcome"]["status"]
    c.require(isinstance(status, dict) and len(status) == 1
              and next(iter(status)) in {"Failure", "SuccessValue", "SuccessReceiptId"}, "Unknown initial status")
    w.trace.hash_id(root.get("block_hash"))
    return {"transaction_hash": tx["hash"], "network_signer": SIGNER, "receiver": RECEIVER,
            "submission_block_hash": root["block_hash"], "initial_receipt_id": initial,
            "initial_outcome_status": status, "indexed_receiver_and_ordered_actions_match_canonical": True}


def status():
    candidate, indexed, audit = selection()
    result = load("status", c.ENDPOINT, status_request(candidate))
    return candidate, result, status_gate(result, candidate, indexed), audit


def header_request(gate):
    return {"jsonrpc": "2.0", "id": "jars-submission-block", "method": "block",
            "params": {"block_id": gate["submission_block_hash"]}}


def read_reusable(path, endpoint, payload):
    original = c.decode(path.read_bytes())
    c.require({k:v for k,v in original.items() if k != "id"} == {k:v for k,v in payload.items() if k != "id"}, "Reused parameters differ")
    if path.name == "request.json":
        run = c.decode((path.parent/"run.json").read_bytes())
        return w.saved(path.parent, run["stage"], endpoint, original)
    c.require(endpoint == c.ENDPOINT, "Only verified canonical legacy capture reuse supported")
    return c.recorded(path.parent, original)


def reuse_existing(stage, endpoint, payload):
    for p in sorted((ROOT/"results").rglob("*request.json")):
        if p.is_relative_to(OUTPUT):
            continue
        original = c.decode(p.read_bytes())
        if {k:v for k,v in original.items() if k != "id"} != {k:v for k,v in payload.items() if k != "id"}:
            continue
        result = read_reusable(p, endpoint, payload)  # Matching failed evidence stops; never retries it.
        OUTPUT.mkdir(parents=True, exist_ok=True)
        c.write_new(OUTPUT/(stage+".reuse.json"), c.json_bytes({"request_path": str(p.relative_to(ROOT)), "request_identity": w.trace.identity(p)}))
        return result
    return None


def stage_inputs(stage):
    if stage == "history":
        return w.HISTORY_ENDPOINT, history_request(), history_identity
    if stage == "details":
        candidates = page()
        return w.TRANSACTIONS_ENDPOINT, details_request(), lambda r: {"selected_transaction": select(r, candidates)[0]["transaction_hash"], "candidate_count": len(candidates)}
    candidate, indexed, _ = selection()
    if stage == "status":
        return c.ENDPOINT, status_request(candidate), lambda r: status_gate(r, candidate, indexed)
    candidate, _, gate, _ = status()
    return c.ENDPOINT, header_request(gate), lambda r: w.header_gate(r, gate, candidate)


def collect():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    snapshot = OUTPUT/"diagnostic.py"
    if not snapshot.exists():
        c.write_new(snapshot, Path(__file__).read_bytes())
    for stage in STAGES:
        endpoint, payload, validate = stage_inputs(stage)
        if (OUTPUT/(stage+".attempt.json")).exists() or (OUTPUT/(stage+".reuse.json")).exists():
            validate(load(stage, endpoint, payload))
            continue
        reused = reuse_existing(stage, endpoint, payload)
        if reused is not None:
            validate(reused)
            continue
        w.capture(stage, endpoint, payload, validate, output=OUTPUT)


def decoded_calls(result):
    rows = []
    def visit(actions, where, receiver, predecessor):
        for i, action in enumerate(actions):
            call = action.get("FunctionCall")
            if call:
                text = base64.b64decode(call["args"], validate=True).decode("utf-8")
                # Preserve exact decimal lexemes and raw text; do not pass through float.
                args = json.loads(text, parse_float=str, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite call argument")))
                rows.append({"location": f"{where}[{i}]", "receiver": receiver, "predecessor": predecessor,
                             "method": call["method_name"], "raw_args_base64": call["args"], "args_utf8": text,
                             "decoded_args": args, "decimal_number_lexemes": "Unquoted JSON decimal numbers are strings in this mirror; raw UTF-8 remains authoritative",
                             "deposit_yocto": call["deposit"], "gas": call["gas"]})
            delegate = action.get("Delegate", {}).get("delegate_action")
            if delegate:
                visit(delegate["actions"], f"{where}[{i}].Delegate.actions", delegate["receiver_id"], delegate["sender_id"])
    tx = result["transaction"]
    visit(tx["actions"], "transaction.actions", tx["receiver_id"], tx["signer_id"])
    for i, receipt in enumerate(result["receipts"]):
        action = receipt["receipt"].get("Action")
        if action:
            visit(action["actions"], f"receipts[{i}].actions", receipt["receiver_id"], receipt["predecessor_id"])
    return rows


def report():
    candidate, result, gate, audit = status()
    header = w.header_gate(load("header", c.ENDPOINT, header_request(gate)), gate, candidate)
    graph = w.trace.interpret(result)
    coverage = c.decode((ROOT/"results/97_priority4_attribution_coverage.json").read_bytes())
    row = next(r for r in coverage["coverage_table"] if r["account_id"] == SIGNER)
    bucket = next(r["transactions"] for r in row["original_receivers"] if r["receiver"] == RECEIVER)
    paths = [Path(__file__), Path(w.__file__), Path(w.trace.__file__), w.SUPPLY,
             ROOT/"results/97_priority4_attribution_coverage.json", ROOT/"results/19_leading_account_activity_2026-08-24_to_2026-10-18.csv"]
    paths += [p for p in OUTPUT.rglob("*") if p.is_file() and p.name != ".lock"]
    for stage in STAGES:
        reuse = OUTPUT/(stage+".reuse.json")
        if reuse.exists():
            request = ROOT/c.decode(reuse.read_bytes())["request_path"]
            paths += [p for p in request.parent.iterdir() if p.is_file()]
    metadata = [c.decode(p.read_bytes()) for p in OUTPUT.rglob("metadata.json")]
    with localcontext() as ctx:
        ctx.prec = 80
        population = {"selected_transactions": 1, "saved_destination_bucket_transactions": bucket,
                      "share_of_saved_destination_bucket_pct": format(Decimal(100)/bucket, "f"),
                      "saved_signer_transactions": row["transactions"],
                      "share_of_saved_signer_transactions_pct": format(Decimal(100)/row["transactions"], "f"),
                      "denominator_scope": "24 August–18 October saved weekly top-20 original-receiver bucket, not a complete descendant population or a 23 September census"}
        charge = format(Decimal(graph["recorded_transaction_and_receipt_execution_charge_yocto"])/Decimal(10**24), "f")
    return {"classification": "SELECTED_SWEAT_JARS_MECHANISM_NOT_POPULATION_SUCCESS", "candidate": candidate,
            "selection_audit": audit, "identity_gate": gate, "canonical_submission": header,
            "returned_graph": graph, "decoded_calls": decoded_calls(result), "population_coverage": population,
            "recorded_charge_near": charge,
            "collection": {"maximum_requests": 4, "new_requests": len(metadata), "response_bytes": sum(m["response_bytes"] for m in metadata),
                           "maximum_candidates": 5, "pagination": False, "retries": 0, "response_cap_bytes_per_request": w.BODY_CAP,
                           "spacing_seconds": 65, "timeouts_seconds": [15,60], "reused_stages": [s for s in STAGES if (OUTPUT/(s+".reuse.json")).exists()]},
            "qualification": "One earliest eligible signer/receiver case among at most five indexed candidates, without outcome-based selection. Not representative of the saved destination bucket. Explicit Delegate actions alone establish declared delegation; differing predecessors do not. Returned graph coverage is not independent historical completeness. Recorded charges are not revenue or native supply burn; observed methods do not establish human adoption, economic purpose or holder value.",
            "sources": {w.trace.reference(p): w.trace.identity(p) for p in sorted(set(paths))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["collect", "report"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "collect":
        c.require(not args.output and not args.check, "Captures use immutable stage output only")
        collect()
        print("Four-stage diagnostic complete; no further requests scheduled.")
        return
    def deny(event, _):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen", "os.system"}:
            raise RuntimeError("Source access disabled during report")
    sys.addaudithook(deny)
    raw = c.json_bytes(report())
    if args.output is None:
        sys.stdout.write(raw.decode())
    elif args.check:
        c.require(args.output.read_bytes() == raw, "Saved jars report does not reproduce")
        print("Selected jars report reproduced offline; source requests: 0")
    else:
        c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
