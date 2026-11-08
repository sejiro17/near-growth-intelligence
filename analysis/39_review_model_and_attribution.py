"""Offline formula review and bounded priority-4 plan; no source collector."""

import argparse
import base64
import csv
import importlib.util
import json
import sys
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("model_review",ROOT/"dashboard/model_review.py")
review=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
model=review.model
PLAN=ROOT/"results/92_priority4_saved_attribution_assessment.json"
REQUEST=ROOT/"results/93_priority4_sweat_receipt_origin_request.json"
BLOCK=ROOT/"results/neardata_supply_block_pilot_recovery_2026-09-23/20261107T154218Z_8ca556d6bf23_recovery_01/hop-01-archive/block-A.response.body"
TARGET="2iLefvugZmJmpNn52hcyMBjxcfYGGz5d6R8h4W1dXaDS"
PERIOD="2026-08-24_to_2026-10-18"


def rows(number):
    path=next((ROOT/"results").glob(f"{number:02d}_*.csv"))
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle)),path


def origin_request():
    return {"jsonrpc":"2.0","id":"priority4-sweat-origin","method":"EXPERIMENTAL_receipt_to_tx","params":{"receipt_id":TARGET}}


def attribution():
    leading,p18=rows(18);actions,p20=rows(20);receivers,p19=rows(19);growth,p22=rows(22)
    by_account=defaultdict(list)
    keys=set()
    weeks={f"2026-{x}" for x in ("08-24","08-31","09-07","09-14","09-21","09-28","10-05","10-12")}
    weekly_totals={}
    for row in leading:
        key=(row["signer_account_id"],row["week_start"])
        model.require(key not in keys,"Duplicate signer/week in result 18");keys.add(key)
        by_account[row["signer_account_id"]].append(row)
        if row["week_start"] in weekly_totals:model.require(weekly_totals[row["week_start"]]==int(row["weekly_transactions"]),"Network-week denominator conflict")
        weekly_totals[row["week_start"]]=int(row["weekly_transactions"])
    totals={}
    for account,group in by_account.items():
        model.require({x["week_start"] for x in group}==weeks,"Incomplete signer-week coverage")
        totals[account]=sum(int(x["transactions"]) for x in group)
        model.require(all(int(x["full_period_transactions"])==totals[account] for x in group),"Repeated full-period total mismatch")
    denominator=sum(weekly_totals.values())
    model.require(denominator==44284794 and len(by_account)==51,"Unexpected saved selected-account scope")
    profiles=model.decode((ROOT/f"results/35_account_profiles_{PERIOD}.json").read_bytes())
    roles={x["account_id"]:x for x in profiles["profiles"]}
    leaders=[]
    with localcontext() as context:
        context.prec=80
        for account,total in sorted(totals.items(),key=lambda x:(-x[1],x[0]))[:10]:
            delegate=sum(int(x["transactions"]) for x in actions if x["signer_account_id"]==account and x["action_kind"]=="DELEGATE_ACTION")
            rx=Counter()
            for row in receivers:
                if row["signer_account_id"]==account:rx[row["receiver_account_id"]]+=int(row["transactions"])
            leaders.append({"account_id":account,"transactions":total,"observed_network_transaction_share_pct":format(Decimal(total)*100/denominator,"f"),
                "role_status":roles[account]["evidence_status"] if account in roles else ("Documented Aurora association in saved register; no selected-action profile or historical operator verification" if account=="relay.aurora" else "No profile role anchor in selected saved register"),
                "delegate_action_transactions":delegate if account in roles else None,
                "delegate_action_share_pct":format(Decimal(delegate)*100/total,"f") if account in roles else None,
                "largest_observed_original_receivers":[{"receiver":key,"transactions":value} for key,value in rx.most_common(3)],
                "receiver_coverage":"Weekly top-20 original receivers only; not decoded inner destinations or a full downstream census"})
    model.require(model.identity(BLOCK)["sha256"]=="42338102d2847e49473bd76d760d6d3bab7fafa1f660a0db8f8651725c2611ba","Saved canonical-A block changed")
    metadata=model.decode(BLOCK.with_name("block-A.metadata.json").read_bytes())
    model.require(metadata["http_status"]==200 and metadata["body_complete"] and not metadata["transport_error"]
                  and metadata["response_sha256"]==model.identity(BLOCK)["sha256"],"Saved block transport/checksum mismatch")
    block=model.decode(BLOCK.read_bytes())
    model.require(block["block"]["header"]["height"]==216877934 and block["block"]["header"]["hash"]=="HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG","Wrong saved block anchor")
    candidates=[(s["shard_id"],r) for s in block["shards"] if s["chunk"] for r in s["chunk"]["receipts"] if r["receipt_id"]==TARGET]
    model.require(len(candidates)==1,"Ambiguous/missing saved target receipt")
    shard,receipt=candidates[0]
    action=receipt["receipt"]["Action"]
    model.require(action["signer_id"]=="sweat-relayer.near" and receipt["receiver_id"]=="claim.sweat" and len(action["actions"])==1,"Target role/action changed")
    call=action["actions"][0]["FunctionCall"]
    decoded=base64.b64decode(call["args"],validate=True).decode("utf-8")
    model.require(call["method_name"]=="claim" and model.decode(decoded)=={} and call["deposit"]=="0","Target call fields changed")
    outcomes=[x for s in block["shards"] for x in s["receipt_execution_outcomes"] if x["execution_outcome"]["id"]==TARGET]
    model.require(not outcomes,"New target execution evidence; revise plan")
    failures=model.decode((ROOT/f"results/26_growth_account_failure_details_{PERIOD}.json").read_bytes())
    failure_audits=[]
    for item in failures["records"]:
        result=item["rpc_response"]["result"]
        outcomes=[result["transaction_outcome"]]+result["receipts_outcome"]
        ids=[x["id"] for x in outcomes]
        model.require(len(ids)==len(set(ids)),"Duplicate saved failure outcome")
        children={child for x in outcomes for child in x["outcome"]["receipt_ids"]}
        failure_audits.append({"transaction_hash":result["transaction"]["hash"],"signer":result["transaction"]["signer_id"],
                              "outcomes":len(outcomes),"missing_emitted_outcome_ids":sorted(children-set(ids)),
                              "final_execution_status":result["final_execution_status"]})
    outcome_rows,p24=rows(24)
    coverage=defaultdict(Counter)
    for row in outcome_rows:coverage[row["signer_account_id"]][row["initial_receipt_status"]]+=int(row["transactions"])
    growth_leaders=[{"account_id":r["signer_account_id"],"group":r["comparison_group"],"first_week_transactions":int(r["first_week_transactions"]),
                     "final_week_transactions":int(r["final_week_transactions"]),"endpoint_change":int(r["transaction_change"])}
                    for r in sorted(growth,key=lambda x:(-int(x["transaction_change"]),x["signer_account_id"])) if r["signer_account_id"] and int(r["transaction_change"])>0][:6]
    sources=[p18,p19,p20,p22,p24,ROOT/f"results/26_growth_account_failure_details_{PERIOD}.json",ROOT/f"results/35_account_profiles_{PERIOD}.json",
             BLOCK,BLOCK.with_name("block-A.metadata.json"),ROOT/"notes/account_attribution.md",ROOT/"results/83_neardata_canonical_block_A_comparison_2026-09-23.json",ROOT/"analysis/15_trace_frontend_transfer_origin.py",Path(__file__)]
    return {"status":"BOUNDED_ATTRIBUTION_DESIGN_ONLY_NO_COLLECTION", "source_requests":0,
        "network":"NEAR mainnet","window":"2026-08-24/2026-10-18","network_transactions":denominator,"selected_signers":51,
        "ranking_scope":"Full-period totals among saved union of weekly top-20 signers; not an exhaustive all-account ranking",
        "leaders":leaders,"largest_named_endpoint_growth_contributors":growth_leaders,
        "untracked_group_endpoint_increase":sum(int(r["transaction_change"]) for r in growth if not r["signer_account_id"]),
        "downstream_coverage":{"tinykoala_and_wx_initial_status_counts":{a:dict(v) for a,v in coverage.items()},
            "failure_controls":failure_audits,"failure_control_scope":"18 preselected failed tinykoala transactions; retained receipt graphs, not a representative network sample or relayer census",
            "other_census":"Cohort results 58–62 cover initial receipts only. 398,968 wx transactions have SUCCESS_RECEIPT_ID, which does not establish downstream success. Five-account profiles expose action kinds/original receivers without delegated inner payloads.",
            "closed_provenance":"Results 47–54 remain closed and are not reused as a revenue-origin or relayer-population inference."},
        "target":{"receipt_id":TARGET,"source_shard_id":shard,"observed_container_block_height":216877934,"observed_container_block_hash":block["block"]["header"]["hash"],
            "original_signer_id":action["signer_id"],"receipt_predecessor_id":receipt["predecessor_id"],"receipt_receiver_id":receipt["receiver_id"],
            "method_name":call["method_name"],"raw_args_base64":call["args"],"decoded_args_utf8":decoded,"deposit_yocto":call["deposit"],"gas":call["gas"],
            "execution_outcome_in_saved_block":None,"originating_transaction_hash":None,
            "interpretation":"Saved receipt distinguishes signer, predecessor and called contract. It does not prove predecessor is a delegated inner signer, verify beneficial ownership, establish execution success or expose its originating transaction."},
        "proposed_sequence":{"maximum_new_requests":2,"execution_authorized":False,
            "first":origin_request(),
            "second_template":{"jsonrpc":"2.0","id":"priority4-sweat-status","method":"EXPERIMENTAL_tx_status","params":{"tx_hash":"<validated origin transaction_hash>","sender_account_id":"<validated origin sender_account_id>","wait_until":"FINAL"}},
            "endpoint":"https://archival-rpc.mainnet.near.org","automatic_retries":0,"fallbacks":[],"scan_hints":None,
            "validation":["Verify origin response checksum, JSON-RPC identity, 32-byte transaction hash and sender matching saved receipt signer sweat-relayer.near; stop on conflict. Never pass a receipt ID as tx_hash.",
                "Validate FINAL transaction details, exact signer/hash and the selected receipt payload. Preserve ordered actions and raw arguments.",
                "Distinguish outer signer from SignedDelegate sender_id/receiver_id/public_key/nonce/max_block_height where actually present. Absence of a delegate action leaves the mechanism different or unresolved; do not force that explanation.",
                "Preserve receiving contracts, executors, predecessor IDs, generated receipt_ids, logs/status and callback data dependencies. Aggregate each identity before linking; duplicate/ambiguous IDs remain unresolved.",
                "Validate every emitted child has an outcome, with explicit exceptions for data receipts; match callback data IDs to producers. FINAL or top-level success alone is insufficient.",
                "Keep costs, deposits and token amounts in exact raw units; do not infer fee payer/user ownership from signer or predecessor alone."],
            "stop_conditions":["Stop after this one transaction trace; no broad block download or account-history scan.","Stop on unsupported origin index, missing historical data, HTTP/JSON-RPC error, ambiguous identity or response cap; retain bytes and report missing evidence.","Preserve existing 65-second spacing, 15/60-second timeouts and immutable checksummed bytes. Require a new explicit 8 MiB response guard before any collection: the legacy analysis-11 transport has no byte cap. No live collector is prepared or run by this offline plan."],
            "decision":"Can establish whether one high-volume signer's transaction relays a distinct on-chain actor into claim.sweat, and whether that transaction's receipt/callback graph settled. Cannot establish population user counts, service ownership, revenue, buyback or burn."},
        "sources":{str(path.relative_to(ROOT)):model.identity(path) for path in sources}}


def rebuild(check=False,with_model=False):
    model_check=None
    if with_model:
        spec=importlib.util.spec_from_file_location("model_builder",ROOT/"analysis/38_conditional_investment_model.py")
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        model_check=builder.rebuild(check=check,with_published=True)
    generated={review.ARTIFACT:model.json_bytes(review.report()),PLAN:model.json_bytes(attribution()),REQUEST:model.json_bytes(origin_request())}
    for path,raw in generated.items():
        if path.exists():model.require(path.read_bytes()==raw,f"Generated-file mismatch: {path}")
        else:model.require(not check,f"Missing derived result: {path}")
    for path,raw in generated.items():
        if not path.exists():
            with path.open("xb") as handle:handle.write(raw)
    return {"verified_artifacts":len(generated),"source_requests":0,"model_and_published":model_check,"outputs":[str(x.relative_to(ROOT)) for x in generated]}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--check",action="store_true");parser.add_argument("--with-model",action="store_true")
    parser.add_argument("--assumptions",type=Path);parser.add_argument("--output",type=Path);args=parser.parse_args()
    def deny(event,args):
        if event in {"socket.connect","socket.getaddrinfo","socket.sendto"}:raise RuntimeError("Source requests disabled during review")
    sys.addaudithook(deny)
    try:
        if args.assumptions is not None:
            model.require(args.output is not None,"A custom scenario needs an unused --output")
            document=model.decode(args.assumptions.read_bytes())
            result=review.applied_report(model.verify_saved(),document["assumptions"])
            result["sources"][str(args.assumptions.resolve())]=model.identity(args.assumptions)
            raw=model.json_bytes(result)
            if args.output.exists():model.require(args.output.read_bytes()==raw,"Custom scenario output exists with different bytes")
            else:
                model.require(not args.check,"Custom scenario output missing")
                with args.output.open("xb") as handle:handle.write(raw)
            print(json.dumps({"source_requests":0,"scenario_output":str(args.output)},indent=2))
        else:
            model.require(args.output is None,"--output requires --assumptions")
            print(json.dumps(rebuild(args.check,args.with_model),indent=2))
    except (OSError,ValueError,KeyError,TypeError,RuntimeError) as exc:
        print(f"Offline review stopped: {exc}",file=sys.stderr);return 1
    return 0


if __name__=="__main__":raise SystemExit(main())
