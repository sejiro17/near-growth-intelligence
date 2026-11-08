"""Saved asset inventory and two bounded historical internal-balance views.

report/validate are offline. collect queries one known owner/asset at two saved
boundary hashes, with immutable captures, no retries and no asset discovery.
"""

import argparse
import base64
import fcntl
import importlib.util
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ledger = module("asset_ledger", "33_consolidate_three_wallet_ledger.py")
http = module("asset_http", "42_trace_wx_cruce.py")
c = ledger.c
SOURCE = ROOT / "results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json"
PLAN = ROOT / "results/77_three_wallet_historical_balance_request_plan.json"
OUTPUT = ROOT / "results/known_asset_wallet_stocks_2026-08-24_to_2026-10-18"
OWNER = "1csfundsadmin.sputnik-dao.near"
ASSET = "nep141:wrap.near"
CONTRACT = "intents.near"
STANDARD = "https://github.com/near/NEPs/blob/master/neps/nep-0245.md"


def exact(value):
    c.money(value, "internal token base units")
    return value


def source(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(raw), "sha256": c.sha256(raw)}


def request(boundary):
    c.require(boundary in {"opening", "closing"}, "Unknown boundary")
    target = c.decode(PLAN.read_bytes())["boundaries"][boundary]
    args = c.json_bytes({"account_id": OWNER, "token_id": ASSET})
    return {"jsonrpc": "2.0", "id": "known-asset-"+boundary, "method": "query",
            "params": {"request_type": "call_function", "account_id": CONTRACT,
                       "method_name": "mt_balance_of", "args_base64": base64.b64encode(args).decode(),
                       "block_id": target["hash"]}}


def inventory(saved):
    layer = saved["asset_layer"]
    requests = layer["decoded_asset_requests"]
    movements = layer["observed_successful_internal_transfers"]
    identities = set()
    rows = []
    for movement in movements:
        key = tuple(movement[k] for k in ("receipt_id", "log_index", "data_index", "asset_index"))
        c.require(key not in identities, "Duplicate internal event identity")
        identities.add(key)
        call = movement["matching_call"]
        event = c.decode(movement["raw_log"].removeprefix("EVENT_JSON:"))
        datum = event["data"][movement["data_index"]]
        i = movement["asset_index"]
        c.require(event["standard"] == "nep245" and event["event"] == "mt_transfer"
                  and len(datum["token_ids"]) == len(datum["amounts"]), "Invalid token event")
        c.require(call["receipt_id"] == movement["receipt_id"] and call["receiver"] == CONTRACT
                  and call["status"] == "SUCCESS_VALUE" and call["method"] == "mt_transfer"
                  and datum["old_owner_id"] == movement["old_owner_id"] == call["predecessor"]
                  and datum["new_owner_id"] == movement["new_owner_id"] == call["args"]["receiver_id"]
                  and datum["token_ids"][i] == movement["asset_id"] == call["args"]["token_id"]
                  and exact(datum["amounts"][i]) == exact(movement["amount_base_units"]) == exact(call["args"]["amount"]),
                  "Event and successful action disagree")
        rows.append({k: movement[k] for k in ("receipt_id", "log_index", "data_index", "asset_index",
                    "old_owner_id", "new_owner_id", "asset_id", "amount_base_units", "economic_classification")}
                    | {"execution_block_height": call["execution_block_height"],
                       "execution_block_hash": call["execution_block_hash"],
                       "execution_timestamp_utc": call["execution_timestamp_utc"], "contract": call["receiver"]})
    opaque = sorted({r["receiver_id"] for r in requests})
    closed = layer["closed_saved_conversion_context"]["closed_internal_credit"]
    return {"known_token_contracts": ["wrap.near"], "known_internal_contract": CONTRACT,
            "observed_asset_ids": sorted({r["asset_id"] for r in rows} | {closed["asset"]}),
            "observed_movements": rows, "request_record_count": len(requests),
            "request_context_counts": dict(Counter(r["context"] for r in requests)),
            "proposal_link_count": sum(r["execution_link"] is not None for r in requests),
            "opaque_proposal_recipients": [{"account_id": a, "verified_wallet_alias": None} for a in opaque],
            "closed_trace_accounts": [{"account_id": closed[k], "verified_fee_role": None,
                                        "additional_provenance_collection": "NONE"}
                                       for k in ("internal_sender", "internal_recipient")],
            "historical_role_evidence": saved["historical_contract_evidence"],
            "complete_asset_universe": None, "complete_token_flows": None,
            "verified_revenue": None, "verified_exchange_purchases": None,
            "discovery_dependency": "A retained, success-qualified owner-indexed NEP-141/NEP-245 event history plus historical internal-account associations. SQL 45 selects native counterparties only; neither native account RPC nor one known-token view enumerates all assets. No accessible complete index is established by saved evidence."}


def report():
    saved = c.decode(SOURCE.read_bytes())
    c.require(c.json_bytes(ledger.report()) == SOURCE.read_bytes(), "Result 80 does not reproduce")
    boundaries = c.decode(PLAN.read_bytes())["boundaries"]
    return {"network": "mainnet", "window": saved["window"], "inventory": inventory(saved),
            "pilot": {"owner": OWNER, "asset_id": ASSET, "contract": CONTRACT,
                      "maximum_requests": 2, "endpoint": c.ENDPOINT,
                      "requests": {b: request(b) for b in ("opening", "closing")}, "boundaries": boundaries,
                      "spacing_seconds": 65, "response_cap_bytes": http.BODY_CAP,
                      "timeouts_seconds": [15, 60], "automatic_retries": 0,
                      "denominator": {"selected_wallets": 3, "known_owner_asset_pairs_tested": 1,
                                      "complete_asset_pair_denominator": None, "boundary_states": 2},
                      "scope": "One owner's known internal asset stocks, not complete discovery, flows, fee origin or purchases",
                      "historical_method_availability": "Must be established by each historical response; standard alone is insufficient",
                      "boundary_qualification": saved["boundary_qualification"], "abi_reference": STANDARD},
            "sources": [source(SOURCE), source(PLAN), source(Path(__file__)),
                        source(Path(http.__file__)), source(Path(c.__file__))]}


def balance(result, boundary):
    target = c.decode(PLAN.read_bytes())["boundaries"][boundary]
    c.require(result.get("block_hash") == target["hash"]
              and type(result.get("block_height")) is int and result["block_height"] == target["height"], "Wrong historical block identity")
    raw = result.get("result")
    c.require(isinstance(raw, list) and 0 < len(raw) <= 128
              and all(type(n) is int and 0 <= n <= 255 for n in raw), "Invalid view-result byte array")
    c.require(isinstance(result.get("logs"), list) and all(isinstance(s, str) for s in result["logs"]), "Missing view logs")
    amount = exact(c.decode(bytes(raw)))
    return {"owner": OWNER, "asset_id": ASSET, "contract": CONTRACT,
            "block_hash": target["hash"], "block_height": target["height"],
            "balance_base_units": amount, "raw_result_utf8": bytes(raw).decode(), "logs": result["logs"]}


def saved_balance(boundary):
    marker = c.decode((OUTPUT/(boundary+".attempt.json")).read_bytes())
    directory = ROOT/marker["directory"]
    c.require(not (directory/"stopped.json").exists(), "Stopped capture; no retry")
    payload = request(boundary)
    c.require((directory/"request.json").read_bytes() == c.json_bytes(payload)
              and (directory/"request.http").read_bytes() == http.http_bytes(c.ENDPOINT, payload), "Saved request mismatch")
    meta = c.decode((directory/"metadata.json").read_bytes())
    raw = (directory/"response.body").read_bytes()
    c.require(meta["endpoint"] == c.ENDPOINT and meta["http_status"] == 200
              and meta["body_complete"] and not meta["transport_error"]
              and meta["response_bytes"] == len(raw) <= http.BODY_CAP
              and meta["response_sha256"] == c.sha256(raw)
              and meta["request_sha256"] == c.sha256(c.json_bytes(payload))
              and meta["request_http_sha256"] == c.sha256(http.http_bytes(c.ENDPOINT, payload)), "Saved transport/checksum mismatch")
    times = [datetime.fromisoformat(meta[k]) for k in ("started_at", "finished_at")]
    c.require(all(t.utcoffset() == timezone.utc.utcoffset(t) for t in times) and times[1] >= times[0], "Invalid retrieval timestamps")
    state = balance(c.envelope(raw, payload), boundary)
    return state, [source(p) for p in sorted(directory.iterdir()) if p.is_file()]


def collect(transport=None, pause=time.sleep):
    report()  # Validate frozen evidence before any request.
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with (OUTPUT/".lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for boundary in ("opening", "closing"):
            marker = OUTPUT/(boundary+".attempt.json")
            if marker.exists():
                saved_balance(boundary)  # Reuse success; failed attempt stops, never retries.
                continue
            directory = OUTPUT/(boundary+"_"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12])
            directory.mkdir()
            payload = request(boundary)
            c.write_new(marker, c.json_bytes({"directory": str(directory.relative_to(ROOT)), "maximum_requests": 1}))
            c.write_new(directory/"request.json", c.json_bytes(payload))
            c.write_new(directory/"request.http", http.http_bytes(c.ENDPOINT, payload))
            c.write_new(directory/"collector.py", Path(__file__).read_bytes())
            c.write_new(directory/"run.json", c.json_bytes({"endpoint": c.ENDPOINT, "request_count": 1,
                "body_cap_bytes": http.BODY_CAP, "spacing_seconds": 65, "timeouts_seconds": [15, 60],
                "retries": 0, "fallbacks": [], "redirects": False, "credentials": False}))
            print(f"Evidence directory: {directory}\nWaiting 65s before {boundary}; one attempt, no retries.", flush=True)
            try:
                pause(65)
                started = c.utc_now()
                meta, raw = (http.fetch if transport is None else transport)(c.ENDPOINT, payload)
                meta.update(endpoint=c.ENDPOINT, started_at=started, finished_at=c.utc_now(),
                            response_sha256=c.sha256(raw), response_bytes=len(raw),
                            request_sha256=c.sha256(c.json_bytes(payload)),
                            request_http_sha256=c.sha256(http.http_bytes(c.ENDPOINT, payload)))
                c.write_new(directory/"response.body", raw)
                c.write_new(directory/"metadata.json", c.json_bytes(meta))
                c.require(meta.get("body_complete") and not meta.get("transport_error")
                          and len(raw) <= http.BODY_CAP, "Incomplete/capped transport; stop")
                c.require(meta.get("http_status") == 200, f"HTTP {meta.get('http_status')}; no retry/fallback")
                result = balance(c.envelope(raw, payload), boundary)
                c.write_new(directory/"validation.json", c.json_bytes(result))
            except BaseException as exc:
                c.write_new(directory/"stopped.json", c.json_bytes({"error": str(exc), "automatic_retry": False}))
                raise


def validate():
    base = report()
    states, sources = {}, []
    for boundary in ("opening", "closing"):
        states[boundary], refs = saved_balance(boundary)
        sources.extend(refs)
    change = int(states["closing"]["balance_base_units"])-int(states["opening"]["balance_base_units"])
    rows = base["inventory"]["observed_movements"]
    net = sum(int(r["amount_base_units"])*((r["new_owner_id"] == OWNER)-(r["old_owner_id"] == OWNER))
              for r in rows if r["asset_id"] == ASSET)
    return {"states": states, "stock_change_base_units": str(change),
            "selected_observed_internal_flow_net_base_units": str(net),
            "stock_change_minus_selected_flow_base_units": str(change-net),
            "coverage": base["pilot"]["denominator"], "boundary_qualification": base["pilot"]["boundary_qualification"],
            "classification": "KNOWN_INTERNAL_ASSET_STOCK_COMPARISON_INCOMPLETE_FLOW_COVERAGE",
            "interpretation": "Difference is unmeasured net movements relative to a selected flow subset, not fees, revenue, a balancing transfer or proof of complete history. Native NEAR and its internal representation are separate ledgers, not additive value capture.",
            "complete_asset_universe": None, "verified_revenue": None, "verified_purchases": None,
            "sources": base["sources"]+sources}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["report", "collect", "validate"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.stage == "collect":
        c.require(args.output is None and not args.check, "Collection has immutable capture output only")
        collect()
        print("Two known-asset stocks validated; complete asset discovery remains unavailable.")
        return
    def deny(event, _):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            raise RuntimeError("Offline command cannot access network")
    sys.addaudithook(deny)
    raw = c.json_bytes(report() if args.stage == "report" else validate())
    if args.output is None:
        sys.stdout.write(raw.decode())
    elif args.check:
        c.require(args.output.read_bytes() == raw, "Derived artifact mismatch")
        print("Offline result reproduced; source requests: 0")
    else:
        c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
