"""Bounded transport and receipt interpretation fixtures; live sockets blocked."""

import copy
import hashlib
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("sweat_trace",ROOT/"analysis/40_trace_sweat_relayer.py")
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)
ALPHABET="123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def hash_id(label):
    raw=hashlib.sha256(label.encode()).digest();n=int.from_bytes(raw,"big");text=""
    while n:n,d=divmod(n,58);text=ALPHABET[d]+text
    return "1"*(len(raw)-len(raw.lstrip(b"\0")))+text


class SweatTraceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.output=self.root/"captures"
        for name in ("socket.socket.connect","socket.create_connection"):
            g=patch(name,side_effect=AssertionError("Live network forbidden"));g.start();self.addCleanup(g.stop)
        self.prepared=m.plan();plan=self.root/"plan.json";plan.write_bytes(m.c.json_bytes(self.prepared))
        g=patch.object(m,"PLAN",plan);g.start();self.addCleanup(g.stop)
        self.calls=[];self.pauses=[];self.txhash=hash_id("tx");self.initial=hash_id("initial")
        self.origin={"transaction_hash":self.txhash,"sender_account_id":m.SIGNER}
        self.result=self.fixture()

    def outcome(self,rid,executor,children,status):
        return {"id":rid,"block_hash":m.c.TARGETS["A"]["hash"],"outcome":{"executor_id":executor,"gas_burnt":1,"tokens_burnt":"1","logs":[],"receipt_ids":children,"status":status}}

    def fixture(self):
        target=m.source_target();actor=target["predecessor_id"]
        call={"FunctionCall":{"args":"e30=","deposit":"0","gas":100000000000000,"method_name":"relay"}}
        initial={"receipt_id":self.initial,"predecessor_id":m.SIGNER,"receiver_id":actor,"receipt":{"Action":{"signer_id":m.SIGNER,"actions":[call],"input_data_ids":[],"output_data_receivers":[]}}}
        tx={"hash":self.txhash,"signer_id":m.SIGNER,"public_key":"ed25519:fixture","receiver_id":actor,"actions":[call]}
        return {"final_execution_status":"FINAL","status":{"SuccessValue":""},"transaction":tx,
            "transaction_outcome":self.outcome(self.txhash,m.SIGNER,[self.initial],{"SuccessReceiptId":self.initial}),
            "receipts":[initial,target],"receipts_outcome":[self.outcome(self.initial,actor,[m.TARGET],{"SuccessReceiptId":m.TARGET}),self.outcome(m.TARGET,"claim.sweat",[],{"SuccessValue":""})]}

    def transport(self,raw):
        payload=m.c.decode(raw);self.calls.append(payload)
        result=self.origin if payload["id"]=="priority4-sweat-origin" else self.result
        return {"http_status":200,"response_headers":[],"body_complete":True,"transport_error":None},m.c.json_bytes({"jsonrpc":"2.0","id":payload["id"],"result":result})

    def collect(self,stage,origin=None,transport=None):
        with redirect_stdout(io.StringIO()):return m.collect(stage,origin,self.output,transport or self.transport,self.pauses.append)

    def test_two_manual_stages_identity_caps_and_no_automatic_second_request(self):
        origin=self.collect("origin")
        self.assertEqual(len(self.calls),1);self.assertEqual(self.pauses,[65])
        before={p:p.read_bytes() for p in origin.iterdir()}
        request=m.status_request(m.saved_origin(origin))
        self.assertEqual(request["params"],{"tx_hash":self.txhash,"sender_account_id":m.SIGNER,"wait_until":"FINAL"})
        self.assertEqual(len(self.calls),1)
        status=self.collect("status",origin)
        self.assertEqual(len(self.calls),2);self.assertEqual(self.pauses,[65,65])
        report=m.validate_status(status)
        self.assertEqual(report["network_signer"],m.SIGNER)
        self.assertEqual(report["target_path_from_transaction"],[self.txhash,self.initial,m.TARGET])
        self.assertTrue(report["coverage"]["observed_graph_consistent_and_covered"])
        self.assertTrue(all(p.read_bytes()==raw for p,raw in before.items()))
        for stage,root in (("origin",None),("status",origin)):
            with self.assertRaisesRegex(ValueError,"slot already reserved"):self.collect(stage,root)
        self.assertEqual(len(self.calls),2)

    def test_differing_predecessor_is_not_delegation(self):
        report=m.status_identity(self.result,self.origin)
        self.assertEqual(report["delegation_status"],"NOT_ESTABLISHED_BY_RETURNED_ACTIONS")
        self.assertEqual(report["declared_delegate_sender_ids"],[])
        self.assertFalse(report["target_receipt"]["delegated_signer_inferred_from_predecessor"])
        self.assertEqual(report["coverage"]["returned_receipt_payloads"],2)
        self.assertEqual(report["coverage"]["returned_receipt_outcomes"],2)

    def test_explicit_delegate_is_preserved_without_ownership_inference(self):
        delegated={"Delegate":{"delegate_action":{"sender_id":m.source_target()["predecessor_id"],"receiver_id":"claim.sweat","public_key":"ed25519:delegated","nonce":1,"max_block_height":216877935,"actions":m.source_target()["receipt"]["Action"]["actions"]},"signature":"ed25519:signature"}}
        self.result["transaction"]["actions"]=[delegated]
        self.result["receipts"][0]["receipt"]["Action"]["actions"]=[delegated]
        report=m.status_identity(self.result,self.origin)
        self.assertEqual(report["delegation_status"],"EXPLICIT_DELEGATE_RETURNED")
        self.assertEqual(report["declared_delegate_sender_ids"],[m.source_target()["predecessor_id"]])
        self.assertEqual(report["delegate_observations"][0]["inner_actions"],m.source_target()["receipt"]["Action"]["actions"])

    def test_missing_outcome_payload_duplicate_and_wrong_identity_safeguards(self):
        for field in ("receipts_outcome","receipts"):
            value=copy.deepcopy(self.result);value[field].append(copy.deepcopy(value[field][0]))
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"Duplicate"):m.status_identity(value,self.origin)
        value=copy.deepcopy(self.result);value["receipts_outcome"].pop()
        with self.assertRaisesRegex(ValueError,"target executor"):m.status_identity(value,self.origin)
        value=copy.deepcopy(self.result);value["transaction"]["signer_id"]="wrong.near"
        with self.assertRaisesRegex(ValueError,"Wrong transaction"):m.status_identity(value,self.origin)
        value=copy.deepcopy(self.result);value["receipts"][1]["receipt"]["Action"]["actions"][0]["FunctionCall"]["deposit"]="1"
        with self.assertRaisesRegex(ValueError,"payload differs"):m.status_identity(value,self.origin)

    def test_missing_descendant_and_failed_receipt_are_not_success_or_zero(self):
        missing=hash_id("missing")
        value=copy.deepcopy(self.result);value["receipts_outcome"][-1]["outcome"]["receipt_ids"]=[missing]
        report=m.interpret(value)
        self.assertFalse(report["coverage"]["observed_graph_consistent_and_covered"])
        self.assertEqual(report["coverage"]["missing_emitted_action_outcomes"],[missing])
        value=copy.deepcopy(self.result);value["receipts_outcome"][-1]["outcome"]["status"]={"Failure":{"error":"synthetic"}}
        report=m.status_identity(value,self.origin)
        self.assertTrue(report["coverage"]["observed_graph_consistent_and_covered"])
        self.assertFalse(report["coverage"]["all_observed_receipt_outcomes_successful"])

    def test_callbacks_data_delivery_and_unmatched_dependencies(self):
        value=copy.deepcopy(self.result);data_id=hash_id("data")
        initial=value["receipts"][0]["receipt"]["Action"]
        initial["output_data_receivers"]=[{"data_id":data_id,"receiver_id":"claim.sweat"}]
        value["receipts"][1]["receipt"]["Action"]["input_data_ids"]=[data_id]
        report=m.interpret(value)
        self.assertTrue(report["coverage"]["observed_graph_consistent_and_covered"])
        value["receipts"].append({"receipt_id":hash_id("data-delivery"),"predecessor_id":m.SIGNER,"receiver_id":"claim.sweat","receipt":{"Data":{"data_id":data_id,"data":None}}})
        self.assertTrue(m.interpret(value)["coverage"]["observed_graph_consistent_and_covered"])
        initial["output_data_receivers"]=[];value["receipts"].pop()
        self.assertFalse(m.interpret(value)["coverage"]["observed_graph_consistent_and_covered"])

    def test_population_fraction_is_conditional_and_never_representative(self):
        coverage=m.population_coverage()
        self.assertEqual(coverage["identity_validated_trace_transactions"],0)
        self.assertIsNone(coverage["transaction_submission_window_membership"])
        report=m.status_identity(self.result,self.origin)
        self.assertTrue(report["population_coverage"]["transaction_submission_window_membership"])
        self.assertEqual(report["population_coverage"]["saved_signer_transactions"],13704363)
        self.assertLess(Decimal(coverage["one_trace_share_of_saved_signer_population_pct_if_membership_confirmed"]),Decimal("0.00001"))
        self.result["transaction_outcome"]["block_hash"]=hash_id("unknown-submission")
        coverage=m.status_identity(self.result,self.origin)["population_coverage"]
        self.assertIsNone(coverage["transaction_submission_window_membership"])
        self.assertIsNone(coverage["confirmed_trace_members_in_saved_window"])

    def test_http_jsonrpc_and_partial_errors_retain_bytes_and_consume_slot(self):
        for index,(status,body,complete) in enumerate(((429,b"limited",True),(200,m.c.json_bytes({"jsonrpc":"2.0","id":"priority4-sweat-origin","error":{"code":-32000,"message":"UNKNOWN_RECEIPT"}}),True),(200,b"partial",False))):
            self.output=self.root/f"failed-{index}"
            def transport(raw):return {"http_status":status,"response_headers":[],"body_complete":complete,"transport_error":None if complete else "incomplete"},body
            with self.assertRaises(ValueError):self.collect("origin",transport=transport)
            self.assertTrue(any(p.read_bytes()==body for p in self.output.rglob("*.response.body")))
            with self.assertRaisesRegex(ValueError,"slot already reserved"):self.collect("origin")
            self.assertTrue(list(self.output.rglob("stopped.json")))

    def test_changed_checksums_and_wrong_origin_sender_block_status(self):
        origin=self.collect("origin");body=origin/"priority4-sweat-origin.response.body"
        body.write_bytes(body.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError,"checksum"):m.saved_origin(origin)
        with self.assertRaisesRegex(ValueError,"conflicts"):m.validate_origin({**self.origin,"sender_account_id":"wrong.near"})
        with self.assertRaises(ValueError):self.collect("status")
        self.assertEqual(len(self.calls),1)

    def test_all_18_saved_controls_have_covered_but_failed_graphs(self):
        report=m.controls_report();self.assertEqual(len(report["controls"]),18)
        for row in report["controls"]:
            self.assertTrue(row["coverage"]["observed_graph_consistent_and_covered"])
            self.assertFalse(row["coverage"]["all_observed_receipt_outcomes_successful"])
            self.assertEqual(row["coverage"]["returned_receipt_outcomes"],3)
        self.assertEqual(report["source_requests"],0)

    def test_transport_byte_cap_retains_prefix_without_retry_or_redirect(self):
        class Sock:
            def settimeout(self,value):pass
        class Response:
            status=302;version=11;reason="Redirect";length=20
            def __init__(self):self.remaining=b"x"*20
            def getheaders(self):return [("Location","https://unverified.test/")]
            def getheader(self,name):return None
            def isclosed(self):return not self.remaining
            def read1(self,n):value,self.remaining=self.remaining[:n],self.remaining[n:];self.length-=len(value);return value
            def close(self):pass
        class Connection:
            def __init__(self,*a,**k):self.sock=Sock()
            def connect(self):pass
            def putrequest(self,*a,**k):pass
            def putheader(self,*a,**k):pass
            def endheaders(self,*a,**k):pass
            def getresponse(self):return Response()
            def close(self):pass
        with patch.object(m,"BODY_CAP",8),patch.object(m.c.http.client,"HTTPSConnection",side_effect=Connection) as factory:
            meta,body=m.bounded_fetch(m.c.json_bytes(m.origin_request()))
        self.assertEqual(body,b"x"*8);self.assertFalse(meta["body_complete"])
        self.assertIn("cap",meta["transport_error"]);self.assertEqual(factory.call_count,1)


if __name__=="__main__":unittest.main()
