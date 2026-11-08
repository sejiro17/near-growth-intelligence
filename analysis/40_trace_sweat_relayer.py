"""Two manually invoked, byte-capped RPC stages for one sweat-relayer receipt.

plan/prepare-status/validate/controls are offline. No retries, scans or fallback.
"""

import argparse
import base64
import fcntl
import importlib.util
import ssl
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("saved_origin_helpers",ROOT/"analysis/15_trace_frontend_transfer_origin.py")
helper=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(helper)
c=helper.capture
TARGET="2iLefvugZmJmpNn52hcyMBjxcfYGGz5d6R8h4W1dXaDS"
SIGNER="sweat-relayer.near"
PLAN=ROOT/"results/94_sweat_relayer_bounded_trace_plan.json"
CONTROLS=ROOT/"results/95_sweat_trace_tinykoala_controls.json"
REQUEST=ROOT/"results/93_priority4_sweat_receipt_origin_request.json"
ASSESSMENT=ROOT/"results/92_priority4_saved_attribution_assessment.json"
PILOT=ROOT/"results/85_neardata_header_pilot_validation_216877934_to_216878033.json"
BLOCK=ROOT/"results/neardata_supply_block_pilot_recovery_2026-09-23/20261107T154218Z_8ca556d6bf23_recovery_01/hop-01-archive/block-A.response.body"
FAILURES=ROOT/"results/26_growth_account_failure_details_2026-08-24_to_2026-10-18.json"
OUTPUT=ROOT/"results/sweat_relayer_attribution_2026-09-23"
BODY_CAP=8*1024**2
HEADERS=[["Host",c.HOST],["Content-Type","application/json"],["Accept","application/json"],
         ["Accept-Encoding","identity"],["Connection","close"],["User-Agent","near-growth-intelligence-bounded-sweat-trace/1"]]


def identity(path):
    raw=path.read_bytes()
    return {"bytes":len(raw),"sha256":c.sha256(raw)}


def reference(path):
    path=path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def hash_id(value):
    helper.validate_origin({"transaction_hash":value,"sender_account_id":SIGNER})
    return value


def source_target():
    assessment=c.decode(ASSESSMENT.read_bytes())
    expected=assessment["sources"][str(BLOCK.relative_to(ROOT))]
    c.require(identity(BLOCK)==expected,"Changed saved block")
    document=c.decode(BLOCK.read_bytes())
    matches=[r for sh in document["shards"] if sh["chunk"] for r in sh["chunk"]["receipts"] if r["receipt_id"]==TARGET]
    c.require(len(matches)==1,"Missing/ambiguous selected receipt")
    row=matches[0]
    c.require(row["receipt"]["Action"]["signer_id"]==SIGNER and row["receiver_id"]=="claim.sweat","Changed target signer/receiver")
    c.require(row["receipt"]["Action"]["actions"]==[{"FunctionCall":{"args":"e30=","deposit":"0","gas":300000000000000,"method_name":"claim"}}],"Changed target actions")
    return row


def origin_request():
    payload={"jsonrpc":"2.0","id":"priority4-sweat-origin","method":"EXPERIMENTAL_receipt_to_tx","params":{"receipt_id":TARGET}}
    c.require(REQUEST.read_bytes()==c.json_bytes(payload),"Request 93 changed")
    return payload


def validate_origin(value):
    helper.validate_origin(value)
    c.require(value["sender_account_id"]==SIGNER,"Origin sender conflicts with saved receipt signer")
    return value


def status_request(origin):
    validate_origin(origin)
    payload=helper.status_request(origin)
    payload["id"]="priority4-sweat-status"
    return payload


def plan():
    target=source_target()
    paths=[ASSESSMENT,REQUEST,BLOCK,BLOCK.with_name("block-A.metadata.json"),PILOT,FAILURES,Path(__file__),Path(helper.__file__),Path(c.__file__)]
    return {"target_receipt":TARGET,"network":"NEAR mainnet","endpoint":c.ENDPOINT,"target_payload":target,
        "origin_request":origin_request(),"status_stage":"Only after saved origin identity/checksums validate; one EXPERIMENTAL_tx_status with returned tx_hash and sender_account_id, wait_until FINAL",
        "maximum_requests":2,"maximum_attempts_per_stage":1,"response_body_cap_bytes":BODY_CAP,
        "maximum_new_response_body_bytes":2*BODY_CAP,"spacing_seconds":65,"connect_timeout_seconds":15,"request_timeout_seconds":60,
        "retries":0,"fallbacks":[],"redirects":False,"scan_hints":None,
        "output_root":str(OUTPUT.relative_to(ROOT)),"limits":"A stage is reserved before transport. Any failed/incomplete attempt consumes its single slot; rerunning cannot silently retry. No third request is available for missing graph/history/header data.",
        "inputs":{str(path.relative_to(ROOT)):identity(path) for path in paths}}


def preflight():
    value=plan()
    c.require(PLAN.read_bytes()==c.json_bytes(value),"Frozen plan 94 differs; review offline")
    return value


def request_http(payload):
    raw=c.json_bytes(payload)
    headers=HEADERS+[["Content-Length",str(len(raw))]]
    return ("POST / HTTP/1.1\r\n"+"".join(k+": "+v+"\r\n" for k,v in headers)+"\r\n").encode("ascii")+raw


def bounded_fetch(raw):
    """One HTTPS POST, no redirect/retry; retain partial bytes at the byte cap."""
    payload=c.decode(raw)
    c.require(payload.get("id") in {"priority4-sweat-origin","priority4-sweat-status"},"Unexpected request stage")
    body=bytearray();response=None
    meta={"http_status":None,"response_headers":[],"body_complete":False,"transport_error":None,"response_size_limit_bytes":BODY_CAP}
    connection=c.http.client.HTTPSConnection(c.HOST,timeout=15,context=ssl.create_default_context())
    deadline=time.monotonic()+60
    try:
        connection.connect();sock=connection.sock
        sock.settimeout(max(0.001,deadline-time.monotonic()))
        connection.putrequest("POST","/",skip_host=True,skip_accept_encoding=True)
        for key,value in HEADERS+[["Content-Length",str(len(raw))]]:connection.putheader(key,value)
        connection.endheaders(raw)
        response=connection.getresponse()
        meta.update(http_status=response.status,response_headers=response.getheaders(),http_reason=response.reason,http_version=response.version)
        c.require(response.getheader("Content-Encoding") in (None,"identity"),"Unexpected encoded response")
        # Even an oversized declared response is read only up to the fixed cap,
        # retaining the received prefix rather than following another endpoint.
        while not response.isclosed():
            c.require(len(body)<BODY_CAP,"Response byte cap reached before completion")
            remaining=deadline-time.monotonic();c.require(remaining>0,"Request deadline exceeded")
            sock.settimeout(remaining)
            chunk=response.read1(min(65536,BODY_CAP-len(body)))
            if not chunk:break
            body.extend(chunk)
        c.require(response.length in (None,0),"Truncated Content-Length response")
        meta["body_complete"]=True
    except (Exception,KeyboardInterrupt) as exc:
        if isinstance(exc,c.http.client.IncompleteRead):body.extend(exc.partial[:max(0,BODY_CAP-len(body))])
        meta["transport_error"]=f"{type(exc).__name__}: {exc}"
    finally:
        if response is not None:response.close()
        connection.close()
    return meta,bytes(body)


def saved(directory,payload):
    manifest=c.decode((directory/"run.json").read_bytes())
    c.require(manifest["endpoint"]==c.ENDPOINT and manifest["request"]==payload and manifest["request_count"]==1,"Wrong saved stage/request")
    expected_inputs={**preflight()["inputs"],reference(PLAN):identity(PLAN)}
    c.require(manifest["inputs"]==expected_inputs,"Saved stage input lineage changed")
    for name,expected in manifest["inputs"].items():c.require(identity(ROOT/name)==expected,f"Input changed: {name}")
    c.require(not (directory/"stopped.json").exists(),"Saved stage stopped; inspect retained error, no retry")
    c.require((directory/"request.http").read_bytes()==request_http(payload),"Saved HTTP request changed")
    metadata=c.decode((directory/(payload["id"]+".metadata.json")).read_bytes())
    c.require(metadata.get("request_http_sha256")==c.sha256(request_http(payload)) and metadata.get("request_http_bytes")==len(request_http(payload))
              and metadata.get("response_size_limit_bytes")==BODY_CAP,"HTTP bytes or response-limit provenance changed")
    raw=(directory/(payload["id"]+".response.body")).read_bytes()
    c.require(len(raw)<=BODY_CAP,"Saved response exceeds cap")
    return c.recorded(directory,payload)


def saved_origin(directory):
    preflight()
    return validate_origin(saved(directory,origin_request()))


def actions_report(actions,location):
    c.require(isinstance(actions,list),"Missing ordered actions")
    calls=[];delegates=[];unknown=[]
    for index,action in enumerate(actions):
        c.require(isinstance(action,dict) and len(action)==1,"Ambiguous action encoding")
        kind,value=next(iter(action.items()));where=f"{location}[{index}]"
        if kind=="FunctionCall":
            c.require(isinstance(value,dict),"Malformed FunctionCall")
            c.money(value.get("deposit"),"deposit");c.integer(value.get("gas"),"gas")
            raw=base64.b64decode(value["args"],validate=True)
            c.require(base64.b64encode(raw).decode()==value["args"],"Noncanonical arguments")
            calls.append({"location":where,"method_name":value["method_name"],"raw_args_base64":value["args"],
                          "args_sha256":c.sha256(raw),"deposit_yocto":value["deposit"],"attached_gas":value["gas"]})
        elif kind=="Delegate":
            c.require(isinstance(value,dict) and isinstance(value.get("delegate_action"),dict) and isinstance(value.get("signature"),str),"Unsupported/incomplete SignedDelegate")
            delegated=value["delegate_action"]
            for key in ("sender_id","receiver_id"):c.account_id(delegated.get(key))
            for key in ("nonce","max_block_height"):c.integer(delegated.get(key),key)
            c.require(isinstance(delegated.get("public_key"),str),"Missing delegate public key")
            nested=actions_report(delegated.get("actions"),where+".delegate_action.actions")
            delegates.append({"location":where,"sender_id":delegated["sender_id"],"receiver_id":delegated["receiver_id"],
                              "public_key":delegated["public_key"],"nonce":delegated["nonce"],"max_block_height":delegated["max_block_height"],
                              "signature":value["signature"],"inner_actions":delegated["actions"],"nested_calls":nested["calls"],
                              "qualification":"Declared delegate authority in returned transaction/receipt; signature is preserved, not independently cryptographically verified or mapped to beneficial ownership"})
        elif "delegate" in kind.lower():unknown.append({"location":where,"kind":kind,"status":"UNSUPPORTED_DELEGATE_ENCODING_NOT_INFERRED"})
    return {"calls":calls,"delegates":delegates,"unknown_delegate_encodings":unknown}


def interpret(result):
    """Generic returned-graph audit, also run against the 18 saved controls."""
    c.require(isinstance(result,dict) and result.get("final_execution_status")=="FINAL","Unavailable/nonfinal transaction")
    tx=result["transaction"];hash_id(tx["hash"])
    c.account_id(tx["signer_id"]);c.account_id(tx["receiver_id"])
    receipts=result.get("receipts");returned=result.get("receipts_outcome")
    c.require(isinstance(receipts,list) and isinstance(returned,list),"Missing receipt arrays")
    outcomes=[result["transaction_outcome"]]+returned
    ids=[x["id"] for x in outcomes];rids=[x["receipt_id"] for x in receipts]
    c.require(len(ids)==len(set(ids)) and len(rids)==len(set(rids)),"Duplicate receipt/outcome identities; no arbitrary selection")
    c.require(ids[0]==tx["hash"],"Transaction outcome identity conflict")
    by_id={x["id"]:x for x in outcomes};payloads={x["receipt_id"]:x for x in receipts}
    parent=defaultdict(list);children=set();calls=[];delegates=[];unknown=[];producers=defaultdict(list);delivered=defaultdict(list);data=set();inputs=[]
    top=actions_report(tx["actions"],"transaction.actions")
    calls+=top["calls"];delegates+=top["delegates"];unknown+=top["unknown_delegate_encodings"]
    nodes=[];spending=0
    for item in outcomes:
        hash_id(item["id"]);hash_id(item["block_hash"])
        out=item["outcome"];c.account_id(out["executor_id"])
        c.money(out["tokens_burnt"],"recorded execution charge");c.integer(out["gas_burnt"],"gas_burnt")
        c.require(isinstance(out["logs"],list) and all(isinstance(x,str) for x in out["logs"]),"Missing logs")
        c.require(isinstance(out["status"],dict) and len(out["status"])==1 and next(iter(out["status"])) in {"Failure","SuccessValue","SuccessReceiptId"},"Unknown outcome status")
        child=out["receipt_ids"];c.require(isinstance(child,list) and len(child)==len(set(child)),"Duplicate child references")
        for rid in child:hash_id(rid);children.add(rid);parent[rid].append(item["id"])
        spending+=int(out["tokens_burnt"])
        nodes.append({"id":item["id"],"block_hash":item["block_hash"],"executor_id":out["executor_id"],"status":out["status"],
                      "child_receipt_ids":child,"logs":out["logs"],"recorded_execution_charge_yocto":out["tokens_burnt"],"gas_burnt":out["gas_burnt"]})
    for index,receipt in enumerate(receipts):
        hash_id(receipt["receipt_id"]);c.account_id(receipt["predecessor_id"]);c.account_id(receipt["receiver_id"])
        if "Data" in receipt["receipt"]:
            data.add(receipt["receipt_id"])
            delivered[(receipt["receipt"]["Data"]["data_id"],receipt["receiver_id"])].append(receipt["receipt_id"])
        if "Action" not in receipt["receipt"]:continue
        a=receipt["receipt"]["Action"];c.account_id(a["signer_id"])
        parsed=actions_report(a["actions"],f"receipts[{index}].Action.actions")
        calls+=parsed["calls"];delegates+=parsed["delegates"];unknown+=parsed["unknown_delegate_encodings"]
        for output in a["output_data_receivers"]:producers[(output["data_id"],output["receiver_id"])].append(receipt["receipt_id"])
        for dep in a["input_data_ids"]:inputs.append((receipt["receipt_id"],dep,receipt["receiver_id"]))
    reachable=set();pending=[tx["hash"]]
    while pending:
        value=pending.pop()
        if value in reachable:continue
        reachable.add(value)
        if value in by_id:pending+=by_id[value]["outcome"]["receipt_ids"]
    ambiguous={key:value for key,value in parent.items() if len(value)!=1}
    missing_children=sorted(children-set(ids)-data)
    disconnected=sorted(set(ids)-reachable)
    unlinked_payloads=sorted(set(rids)-data-reachable)
    unresolved_returns=sorted({x["outcome"]["status"]["SuccessReceiptId"] for x in outcomes if "SuccessReceiptId" in x["outcome"]["status"]}-set(ids)-data)
    root_pointer=result["transaction_outcome"]["outcome"]["status"].get("SuccessReceiptId")
    reconstructed=[]
    if root_pointer not in payloads and root_pointer in by_id and tx["signer_id"]==tx["receiver_id"] and parent[root_pointer]==[tx["hash"]]:
        reconstructed=[root_pointer]
    missing_payloads=sorted((set(ids)-{tx["hash"]})-set(rids)-set(reconstructed))
    dependencies=[{"callback_receipt_id":rid,"data_id":dep,"receiver_id":receiver,"producer_receipt_ids":sorted(set(producers[(dep,receiver)])),
                   "delivered_data_receipt_ids":sorted(set(delivered[(dep,receiver)])),
                   "status":"MATCHED" if len(set(producers[(dep,receiver)]))==1 and len(set(delivered[(dep,receiver)]))<=1 or not producers[(dep,receiver)] and len(set(delivered[(dep,receiver)]))==1 else "MISSING_OR_AMBIGUOUS"} for rid,dep,receiver in inputs]
    graph_complete=not (missing_children or disconnected or unlinked_payloads or tx["hash"] in parent or unresolved_returns or ambiguous or missing_payloads or unknown or any(x["status"]!="MATCHED" for x in dependencies))
    return {"network_signer":tx["signer_id"],"network_signer_public_key":tx["public_key"],"transaction_hash":tx["hash"],"transaction_receiver":tx["receiver_id"],
        "transaction_outcome_block_hash":result["transaction_outcome"]["block_hash"],"final_execution_status":result["final_execution_status"],"top_level_status":result["status"],
        "transaction":tx,"ordered_transaction_actions":tx["actions"],"function_calls":calls,"delegate_observations":delegates,"unknown_delegate_encodings":unknown,
        "declared_delegate_sender_ids":sorted({x["sender_id"] for x in delegates}),"network_transaction_has_delegate_action":bool(top["delegates"]),
        "delegation_status":"EXPLICIT_DELEGATE_RETURNED" if delegates else "NOT_ESTABLISHED_BY_RETURNED_ACTIONS",
        "delegate_scope":"Occurrences retain their transaction/receipt action locations. A delegate in another branch is not automatically the actor behind the selected target; no beneficial owner or distinct-user count is inferred.",
        "receipt_roles":[{"receipt_id":r["receipt_id"],"predecessor_id":r["predecessor_id"],"receiver_id":r["receiver_id"],"action_signer_id":r["receipt"].get("Action",{}).get("signer_id"),"payload":r["receipt"]} for r in receipts],
        "receipt_outcomes":nodes[1:],"transaction_outcome":nodes[0],"parent_links":dict(parent),"callback_dependencies":dependencies,
        "coverage":{"returned_receipt_payloads":len(receipts),"returned_receipt_outcomes":len(returned),"emitted_distinct_child_ids":len(children),
            "data_receipts_without_execution_outcome_expected":sorted(data),"reconstructed_same_account_initial_payloads":reconstructed,
            "missing_emitted_action_outcomes":missing_children,"missing_action_payloads":missing_payloads,"ambiguous_parent_links":ambiguous,
            "disconnected_outcomes":disconnected,"unlinked_action_payloads":unlinked_payloads,"root_returned_as_child":tx["hash"] in parent,
            "unresolved_return_receipt_ids":unresolved_returns,"observed_graph_consistent_and_covered":graph_complete,
            "all_observed_receipt_outcomes_successful":all("Failure" not in x["outcome"]["status"] for x in returned) if returned else None,
            "receipt_status_counts":dict(Counter(next(iter(x["outcome"]["status"])) for x in returned)),
            "independent_historical_ingestion_completeness":None},
        "recorded_transaction_and_receipt_execution_charge_yocto":str(spending),
        "economic_qualification":"Recorded charges are not measured supply destruction or revenue. Signer/predecessor/delegate authority does not establish beneficial ownership or economic funding. Graph coverage is not successful business settlement."}


def population_coverage(report=None):
    assessment=c.decode(ASSESSMENT.read_bytes());leader=next(x for x in assessment["leaders"] if x["account_id"]==SIGNER)
    membership=None
    if report:
        blockhash=report["transaction_outcome_block_hash"]
        pilot=c.decode(PILOT.read_bytes())
        headers=[x["header"] for x in pilot["rows"] if x["status"]=="PRODUCED"]+[pilot["opening_parent"]]
        match=[h for h in headers if h["hash"]==blockhash]
        if match:
            stamp=int(match[0]["timestamp_nanosec"])
            date=datetime.fromtimestamp(stamp//10**9,timezone.utc).date().isoformat()
            membership="2026-08-24"<=date<="2026-10-18"
    with localcontext() as ctx:
        ctx.prec=70
        return {"saved_signer_transactions":leader["transactions"],"saved_delegate_action_transactions":leader["delegate_action_transactions"],
            "identity_validated_trace_transactions":1 if report else 0,"confirmed_trace_members_in_saved_window":None if report and membership is None else int(bool(report and membership is True)),
            "transaction_submission_window_membership":membership,
            "one_trace_share_of_saved_signer_population_pct_if_membership_confirmed":str(Decimal(100)/leader["transactions"]),
            "one_trace_share_of_saved_delegate_population_pct_only_if_network_transaction_delegate_and_membership_confirmed":str(Decimal(100)/leader["delegate_action_transactions"]),
            "confirmed_network_delegate_trace_members_in_saved_window":None if report and membership is None else int(bool(report and membership is True and report["network_transaction_has_delegate_action"])),
            "qualification":"One selected mechanism trace is not representative. Date membership requires a saved submission-block identity/timestamp, not the target receipt's container date. No third header request is automatic. A differing predecessor is not delegation; the source-20 delegate denominator requires an explicit delegate in network transaction actions, not merely another receipt branch."}


def status_identity(result,origin):
    validate_origin(origin)
    c.require(result.get("final_execution_status")=="FINAL","Nonfinal/missing historical transaction")
    tx=result.get("transaction",{})
    c.require(tx.get("hash")==origin["transaction_hash"] and tx.get("signer_id")==SIGNER,"Wrong transaction/signer")
    matches=[r for r in result.get("receipts",[]) if r.get("receipt_id")==TARGET]
    c.require(len(matches)==1,"Missing/duplicate target payload")
    target=source_target()
    for key in ("predecessor_id","receiver_id","receipt"):
        c.require(matches[0].get(key)==target[key],f"Target payload differs: {key}")
    outcomes=[x for x in result.get("receipts_outcome",[]) if x.get("id")==TARGET]
    c.require(len(outcomes)==1 and outcomes[0]["outcome"]["executor_id"]==target["receiver_id"],"Missing/duplicate/wrong target executor")
    report=interpret(result)
    ancestry=[];cursor=TARGET;seen=set()
    while cursor not in seen:
        seen.add(cursor);ancestry.append(cursor)
        if cursor==tx["hash"]:break
        parents=report["parent_links"].get(cursor,[])
        if len(parents)!=1:break
        cursor=parents[0]
    report["target_path_from_transaction"]=list(reversed(ancestry)) if ancestry[-1]==tx["hash"] else None
    report["partial_target_ancestry_from_receipt"]=ancestry
    report["target_receipt"]={"receipt_id":TARGET,"predecessor_id":target["predecessor_id"],"receiving_contract":target["receiver_id"],
        "execution_block_hash":outcomes[0]["block_hash"],"status":outcomes[0]["outcome"]["status"],
        "delegated_signer_inferred_from_predecessor":False}
    report["population_coverage"]=population_coverage(report)
    return report


def controls_report():
    records=c.decode(FAILURES.read_bytes())["records"]
    c.require(len(records)==18,"Changed saved control population")
    reports=[]
    for record in records:
        c.require(record["retrieval_status"]=="VALIDATED_FAILURE","Invalid saved failure control")
        result=c.envelope(c.json_bytes(record["rpc_response"]),record["request"])
        report=interpret(result)
        c.require(report["network_signer"]=="tinykoala595.near" and report["transaction_hash"]==record["sample"]["transaction_hash"],"Wrong control identity")
        reports.append({"transaction_hash":report["transaction_hash"],"coverage":report["coverage"],"delegation_status":report["delegation_status"]})
    with localcontext() as context:
        context.prec=70
        selected_fraction=str(Decimal(18)*100/Decimal(715518))
    return {"source":identity(FAILURES),"validator":{"path":reference(Path(__file__)),**identity(Path(__file__))},"controls":reports,"scope":"18 selected failed tinykoala traces, not sweat-relayer population evidence",
        "selected_control_share_of_saved_715518_failed_initial_receipts_pct":selected_fraction,
        "sweat_population_coverage_before_collection":population_coverage(),"source_requests":0}


def validate_status(directory):
    preflight()
    origin=saved_origin(directory/"origin_input")
    return status_identity(saved(directory,status_request(origin)),origin)


def collect(stage,origin_dir=None,output=OUTPUT,transport=None,pause=None):
    prepared=preflight()
    origin=saved_origin(origin_dir) if stage=="status" and origin_dir is not None else None
    c.require(stage=="origin" or (stage=="status" and origin is not None),"Status requires a validated saved origin")
    payload=origin_request() if stage=="origin" else status_request(origin)
    output.mkdir(parents=True,exist_ok=True)
    with (output/".trace.lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        attempts=output/"request_attempts";attempts.mkdir(exist_ok=True)
        if stage=="status":
            prior=attempts/"origin.json"
            c.require(prior.exists() and Path(c.decode(prior.read_bytes())["directory"])==origin_dir.resolve(),"Status requires this trace's reserved origin capture")
        marker=attempts/(stage+".json")
        c.require(not marker.exists(),f"{stage} request slot already reserved; validate saved evidence, no retry")
        c.require(len(list(attempts.glob("*.json")))<2,"Two-request lifetime cap")
        directory=output/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"_"+uuid.uuid4().hex[:12]);directory.mkdir()
        c.write_new(marker,c.json_bytes({"stage":stage,"directory":str(directory.resolve()),"created_at":c.utc_now(),"maximum_attempts":1}))
        c.write_new(directory/"run.json",c.json_bytes({"endpoint":c.ENDPOINT,"request_count":1,"request":payload,"stage":stage,
            "created_at":c.utc_now(),"inputs":{**prepared["inputs"],reference(PLAN):identity(PLAN)},"response_body_cap_bytes":BODY_CAP}))
        if origin_dir:
            snapshot=directory/"origin_input";snapshot.mkdir()
            for path in origin_dir.iterdir():
                c.require(path.is_file(),"Unexpected origin capture directory")
                c.write_new(snapshot/path.name,path.read_bytes())
        c.write_new(directory/"request.http",request_http(payload))
        print(f"Evidence directory: {directory.resolve()}",flush=True)
        def bounded_transport(raw):
            meta,body=(transport or bounded_fetch)(raw)
            c.require(len(body)<=BODY_CAP,"Injected transport exceeded byte cap")
            meta.update(request_http_sha256=c.sha256(request_http(payload)),request_http_bytes=len(request_http(payload)),response_size_limit_bytes=BODY_CAP)
            return meta,body
        try:
            result=c.capture(directory,payload,bounded_transport,pause)
            report=validate_origin(result) if stage=="origin" else status_identity(result,origin)
            c.write_new(directory/"validation.json",c.json_bytes(report))
        except (Exception,KeyboardInterrupt) as exc:
            c.write_new(directory/"stopped.json",c.json_bytes({"error":f"{type(exc).__name__}: {exc}","stage":stage,"automatic_retry":False,"request_slot_consumed":True}))
            raise
        print("Saved identity validation complete. No next request was executed.",flush=True)
        return directory


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest="command",required=True)
    for name in ("plan","controls"):
        q=sub.add_parser(name);q.add_argument("--output",type=Path)
    sub.add_parser("collect-origin")
    for name in ("prepare-status","collect-status"):
        q=sub.add_parser(name);q.add_argument("--origin-dir",required=True,type=Path)
    q=sub.add_parser("validate");q.add_argument("--run-dir",required=True,type=Path);q.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="collect-origin":collect("origin");return 0
        if args.command=="collect-status":collect("status",args.origin_dir);return 0
        if args.command=="prepare-status":result=status_request(saved_origin(args.origin_dir))
        elif args.command=="plan":result=plan()
        elif args.command=="controls":result=controls_report()
        else:
            manifest=c.decode((args.run_dir/"run.json").read_bytes())
            result=saved_origin(args.run_dir) if manifest["stage"]=="origin" else validate_status(args.run_dir)
        raw=c.json_bytes(result)
        if getattr(args,"output",None):c.write_new(args.output,raw)
        else:sys.stdout.write(raw.decode())
    except (OSError,ValueError,TypeError,KeyError,IndexError) as exc:
        print(f"Stopped: {exc}. No retries, fallback or extra requests.",file=sys.stderr);return 1
    return 0


if __name__=="__main__":raise SystemExit(main())
