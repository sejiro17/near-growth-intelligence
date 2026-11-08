"""One bounded continuation page and one five-hash batch after an ineligible case.

At most four separately invoked requests here; two original requests are retained.
No retry, automatic pagination, endpoint fallback or block scan.
"""

import argparse
import base64
import importlib.util
import sys
from pathlib import Path
from decimal import Decimal, localcontext

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wx_collector", ROOT/"analysis/42_trace_wx_cruce.py")
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)
c = w.c
OUTPUT = w.OUTPUT/"bounded_continuation"


def directory(stage):
    return ROOT/c.decode((OUTPUT/(stage+".attempt.json")).read_bytes())["directory"]


def page_request():
    original = w.saved(w.known_directory("history"), "history", w.HISTORY_ENDPOINT, w.history_request())
    w.history_identity(original)
    c.require((w.known_directory("status")/"stopped.json").is_file(), "Original candidate must have stopped")
    stop = c.decode((w.known_directory("status")/"stopped.json").read_bytes())
    c.require(stop["error"] == "Selected initial outcome is not SUCCESS_RECEIPT_ID; stop without another candidate", "Different original failure; do not expand")
    old = w.known_directory("status")
    candidate = w.history_identity(original)
    payload = w.status_request(candidate)
    raw = (old/"response.body").read_bytes()
    meta = c.decode((old/"metadata.json").read_bytes())
    c.require(meta["http_status"] == 200 and meta["body_complete"] and not meta["transport_error"]
              and meta["response_bytes"] == len(raw) and meta["response_sha256"] == c.sha256(raw)
              and (old/"request.json").read_bytes() == c.json_bytes(payload)
              and (old/"request.http").read_bytes() == w.http_bytes(c.ENDPOINT, payload), "Original rejection capture failed identity/transport checks")
    rejected = c.envelope(raw, payload)
    c.require(rejected["transaction"]["hash"] == candidate["transaction_hash"]
              and rejected["transaction"]["signer_id"] == w.ACCOUNT, "Original rejected transaction identity changed")
    token = original.get("resume_token")
    c.require(isinstance(token, str) and token.isdigit(), "No documented continuation cursor")
    return {**w.history_request(), "limit": 5, "resume_token": token}


def page_identity(result):
    rows = result.get("account_txs") if isinstance(result, dict) else None
    c.require(isinstance(rows, list) and 1 <= len(rows) <= 5, "No bounded continuation candidates")
    checked = [w.history_identity({"account_txs": [r]}) for r in rows]
    c.require(len({r["transaction_hash"] for r in checked}) == len(checked), "Duplicate candidate hashes")
    c.require([(r["tx_block_height"], r["tx_index"]) for r in checked] == sorted((r["tx_block_height"], r["tx_index"]) for r in checked), "Unordered continuation")
    return checked


def page():
    return page_identity(w.saved(directory("history"), "history", w.HISTORY_ENDPOINT, page_request()))


def details_request():
    return {"tx_hashes": [r["transaction_hash"] for r in page()]}


def details_identity(result):
    items = result.get("transactions") if isinstance(result, dict) else None
    c.require(isinstance(items, list) and 1 <= len(items) <= 5 and all(isinstance(x, dict) for x in items), "Invalid indexed transaction batch")
    return {"returned_transactions": len(items), "interpretation": "Raw indexed records retained; no descendant interpretation before canonical identity/date/initial-status gates"}


def selection():
    result = w.saved(directory("details"), "details", w.TRANSACTIONS_ENDPOINT, details_request())
    details_identity(result)
    expected = {r["transaction_hash"]: r for r in page()}
    observed = set()
    eligible = []
    audit = []
    for item in result["transactions"]:
        tx = item.get("transaction", {})
        c.require(isinstance(tx, dict) and tx.get("hash") in expected and tx["hash"] not in observed, "Unknown/duplicate indexed transaction identity")
        observed.add(tx["hash"])
        c.require(tx.get("signer_id") == w.ACCOUNT, "Indexed signer conflict")
        actions = tx.get("actions")
        c.require(isinstance(actions, list), "Missing indexed actions")
        methods = [a["FunctionCall"]["method_name"] for a in actions if "FunctionCall" in a]
        audit.append({"transaction_hash": tx["hash"], "receiver": tx.get("receiver_id"), "methods": methods})
        if "ft_transfer_call" in methods:
            eligible.append(expected[tx["hash"]])
    c.require(observed == set(expected), "Missing indexed candidate records; do not substitute")
    c.require(eligible, "No forwarding-method candidate in five records; stop without more pages")
    candidate = min(eligible, key=lambda r: (r["tx_block_height"], r["tx_index"]))
    return candidate, audit


def status():
    candidate, audit = selection()
    result = w.saved(directory("status"), "status", c.ENDPOINT, w.status_request(candidate))
    gate = w.initial_gate(result, candidate)
    indexed = w.saved(directory("details"), "details", w.TRANSACTIONS_ENDPOINT, details_request())
    match = [r["transaction"] for r in indexed["transactions"] if r["transaction"]["hash"] == candidate["transaction_hash"]]
    c.require(len(match) == 1 and result["transaction"]["receiver_id"] == match[0]["receiver_id"]
              and result["transaction"]["actions"] == match[0]["actions"], "Indexed/canonical receiver or ordered action mismatch")
    gate["indexed_receiver_and_ordered_actions_match_canonical"] = True
    return candidate, audit, result, gate


def report():
    candidate, audit, result, gate = status()
    block = w.saved(directory("header"), "header", c.ENDPOINT, w.header_request(gate))
    header = w.header_gate(block, gate, candidate)
    graph = w.trace.interpret(result)
    paths = [ROOT/"results/98_wx_cruce_candidate_source_assessment.json", w.OUTPUT/"saved_input_inventory.json", Path(__file__), Path(w.__file__),
             ROOT/"analysis/40_trace_sweat_relayer.py", w.SUPPLY]
    captures = [w.known_directory("history"), w.known_directory("status")]+[directory(s) for s in ["history", "details", "status", "header"]]
    for d in captures:
        paths.extend(p for p in d.iterdir() if p.is_file())
    with localcontext() as ctx:
        ctx.prec = 70
        population = {"saved_signed_transactions": 413281, "saved_forwarded_initial_outcomes": 398968,
                      "selected_transactions": 1, "share_of_signed_transactions_pct": str(Decimal(100)/413281),
                      "share_of_forwarded_initial_outcomes_pct": str(Decimal(100)/398968)}
    return {"classification": "SELECTED_WX_FORWARDING_MECHANISM_CASE", "candidate": candidate,
            "selection_audit": audit, "original_candidate": "Ineligible storage_deposit: initial SuccessValue; original captures preserved, no descendants interpreted for that candidate",
            "identity_gate": gate, "canonical_submission": header, "population_coverage": population,
            "returned_graph": graph, "decoded_calls": [{**r, "decoded_utf8": base64.b64decode(r["raw_args_base64"], validate=True).decode()} for r in graph["function_calls"]],
            "recorded_charge_near": format(Decimal(graph["recorded_transaction_and_receipt_execution_charge_yocto"])/Decimal(10**24), "f"),
            "collection": {"history_pages": 2, "indexed_batch_requests": 1, "canonical_status_requests": 2, "submission_headers": 1,
                           "data_requests_total": 6, "maximum_continuation_candidates": 5, "retries": 0, "further_pagination": False},
            "index_source": {"documentation": "https://tx.main.fastnear.com/", "source_commit": "7dcbdb449eb400a9a78883b3ae9d53fa42282fbe",
                             "access_observation": "Credential-free history and five-hash lookup; availability for this sample does not establish complete retained history"},
            "qualification": "One purposively selected ft_transfer_call case after one ineligible storage-deposit candidate. Not representative; successful initial forwarding does not establish descendant or economic success. Returned-graph completeness differs from independent ingestion completeness. Charges/token events are not product revenue or native supply burn; actor keys are not people.",
            "sources": {w.trace.reference(p): w.trace.identity(p) for p in paths}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["history", "details", "status", "header", "selection", "report"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "history":
        w.capture("history", w.HISTORY_ENDPOINT, page_request(), page_identity, output=OUTPUT)
    elif args.stage == "details":
        w.capture("details", w.TRANSACTIONS_ENDPOINT, details_request(), details_identity, output=OUTPUT)
    elif args.stage == "status":
        candidate, _ = selection()
        w.capture("status", c.ENDPOINT, w.status_request(candidate), lambda r: w.initial_gate(r, candidate), output=OUTPUT)
    elif args.stage == "header":
        candidate, _, _, gate = status()
        w.capture("header", c.ENDPOINT, w.header_request(gate), lambda r: w.header_gate(r, gate, candidate), output=OUTPUT)
    else:
        def deny(event, _):
            if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
                raise RuntimeError("Source requests disabled during offline interpretation")
        sys.addaudithook(deny)
        value = report() if args.stage == "report" else selection()
        raw = c.json_bytes(value)
        if args.output is None:
            sys.stdout.write(raw.decode())
        elif args.check:
            c.require(args.output.read_bytes() == raw, "Generated-file mismatch")
            print("Offline report reproduced; source requests: 0")
        else:
            c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
