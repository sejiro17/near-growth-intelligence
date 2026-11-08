"""Offline gates and error retention for the single wx candidate trace."""

import copy
import base64
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wx_trace", ROOT/"analysis/42_trace_wx_cruce.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
CONT = importlib.util.spec_from_file_location("wx_continuation", ROOT/"analysis/43_select_wx_forwarding_case.py")
continuation = importlib.util.module_from_spec(CONT)
CONT.loader.exec_module(continuation)


class WxTests(unittest.TestCase):
    def candidate(self):
        return {"account_id": m.ACCOUNT, "is_signer": True,
                "transaction_hash": "4Hy1wk5EDGHDwAVd4FvFkUPALcsracRWZAW8Z8aB8gB4",
                "tx_block_height": 216877932, "tx_index": 0, "tx_block_timestamp": "1790147484906615725"}

    def result(self):
        row = self.candidate()
        return {"final_execution_status": "FINAL", "transaction": {"hash": row["transaction_hash"], "signer_id": m.ACCOUNT, "receiver_id": "wrap.near"},
            "transaction_outcome": {"id": row["transaction_hash"], "block_hash": "F14YmYFQmFAjgy4DYqg4dK8o2NizhPQbm12VUWuNrz63",
                "outcome": {"executor_id": m.ACCOUNT, "receipt_ids": [m.trace.TARGET], "status": {"SuccessReceiptId": m.trace.TARGET}}},
            "receipts": [{"receipt_id": m.trace.TARGET, "receiver_id": "wrap.near"}],
            "receipts_outcome": [{"id": m.trace.TARGET, "outcome": {"executor_id": "wrap.near", "status": {"SuccessReceiptId": row["transaction_hash"]}}}]}

    def test_one_history_row_and_exact_day_scope(self):
        request = m.history_request()
        self.assertEqual(request["limit"], 1)
        self.assertNotIn("resume_token", request)
        self.assertNotIn("is_success", request)
        self.assertEqual(request["to_tx_block_height"], 216976125)
        self.assertEqual(m.history_identity({"account_txs": [self.candidate()]}), self.candidate())
        for rows in [[], [self.candidate(), self.candidate()]]:
            with self.assertRaises(ValueError):
                m.history_identity({"account_txs": rows})
        row = self.candidate()
        row["is_signer"] = False
        with self.assertRaisesRegex(ValueError, "signer role"):
            m.history_identity({"account_txs": [row]})

    def test_initial_scope_gate_before_descendant_interpretation(self):
        result = self.result()
        gate = m.initial_gate(result, self.candidate())
        self.assertEqual(gate["receiver"], "wrap.near")
        for mutation in ["signer", "initial", "duplicate"]:
            bad = copy.deepcopy(result)
            if mutation == "signer":
                bad["transaction"]["signer_id"] = "wrong.near"
            elif mutation == "initial":
                bad["receipts_outcome"][0]["outcome"]["status"] = {"SuccessValue": ""}
            else:
                bad["receipts_outcome"].append(bad["receipts_outcome"][0])
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                m.initial_gate(bad, self.candidate())
        h = {"header": {"hash": gate["submission_block_hash"], "height": 216877932,
            "timestamp_nanosec": self.candidate()["tx_block_timestamp"]}}
        self.assertEqual(m.header_gate(h, gate, self.candidate())["timestamp_utc"], "2026-09-23T07:11:24.906615725Z")
        h["header"]["timestamp_nanosec"] = "1"
        with self.assertRaises(ValueError):
            m.header_gate(h, gate, self.candidate())

    def test_failed_transport_is_preserved_and_consumes_only_slot(self):
        with tempfile.TemporaryDirectory() as temp, patch("socket.socket.connect", side_effect=AssertionError("No network")):
            output = Path(temp)
            calls = []
            def transport(endpoint, payload):
                calls.append(payload)
                return {"http_status": 403, "body_complete": True, "transport_error": None}, b"Forbidden"
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "HTTP 403"):
                m.capture("history", m.HISTORY_ENDPOINT, m.history_request(), m.history_identity,
                          output, transport, lambda _: None)
            self.assertEqual(next(output.rglob("response.body")).read_bytes(), b"Forbidden")
            self.assertTrue(list(output.rglob("stopped.json")))
            with self.assertRaisesRegex(ValueError, "already attempted"):
                m.capture("history", m.HISTORY_ENDPOINT, m.history_request(), m.history_identity,
                          output, transport, lambda _: None)
            self.assertEqual(len(calls), 1)

    def test_canonical_date_must_pass_before_graph_interpretation(self):
        row, result = self.candidate(), self.result()
        gate = m.initial_gate(result, row)
        bad = {"header": {"hash": gate["submission_block_hash"], "height": row["tx_block_height"],
                          "timestamp_nanosec": "1"}}
        with patch.object(m, "prior_status", return_value=(row, result, gate)), \
             patch.object(m, "known_directory", return_value=ROOT), \
             patch.object(m, "saved", return_value=bad), \
             patch.object(m.trace, "interpret") as interpreter:
            with self.assertRaisesRegex(ValueError, "timestamp mismatch"):
                m.report()
            interpreter.assert_not_called()

    def test_continuation_is_one_bounded_page_and_method_selection_is_not_success(self):
        request = continuation.page_request()
        self.assertEqual(request["limit"], 5)
        self.assertTrue(request["resume_token"].isdigit())
        self.assertNotIn("is_success", request)
        row = self.candidate()
        raw = {"transactions": [{"transaction": {"hash": row["transaction_hash"],
               "signer_id": m.ACCOUNT, "receiver_id": "wrap.near",
               "actions": [{"FunctionCall": {"method_name": "ft_transfer_call"}}]}}]}
        with patch.object(continuation, "page", return_value=[row]), \
             patch.object(continuation, "directory", return_value=ROOT), \
             patch.object(continuation.w, "saved", return_value=raw):
            chosen, audit = continuation.selection()
            self.assertEqual(chosen, row)
            self.assertNotIn("success", audit[0])
            raw["transactions"].append(raw["transactions"][0])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                continuation.selection()

    def test_saved_case_reproduces_exact_returns_charges_and_covered_graph(self):
        with patch("socket.socket.connect", side_effect=AssertionError("Offline only")):
            report = continuation.report()
        path = ROOT/"results/99_wx_cruce_forwarding_case_2026-09-23.json"
        self.assertEqual(m.c.json_bytes(report), path.read_bytes())
        self.assertEqual(report["canonical_submission"]["timestamp_utc"], "2026-09-23T16:17:16.824648967Z")
        graph = report["returned_graph"]
        self.assertEqual(graph["coverage"]["returned_receipt_outcomes"], 6)
        self.assertTrue(graph["coverage"]["observed_graph_consistent_and_covered"])
        self.assertTrue(graph["coverage"]["all_observed_receipt_outcomes_successful"])
        self.assertIsNone(graph["coverage"]["independent_historical_ingestion_completeness"])
        self.assertEqual(graph["callback_dependencies"][0]["status"], "MATCHED")
        self.assertEqual(graph["delegation_status"], "NOT_ESTABLISHED_BY_RETURNED_ACTIONS")
        nodes = [graph["transaction_outcome"]]+graph["receipt_outcomes"]
        self.assertEqual(len({n["id"] for n in nodes}), 7)
        self.assertEqual(sum(int(n["recorded_execution_charge_yocto"]) for n in nodes),
                         int(graph["recorded_transaction_and_receipt_execution_charge_yocto"]))
        self.assertEqual(report["recorded_charge_near"], "0.0007174786101312")
        arguments = m.c.decode(base64.b64decode(graph["transaction"]["actions"][0]["FunctionCall"]["args"]))
        receiver = next(n for n in nodes if n["executor_id"] == "v2.ref-finance.near")
        resolver_id = graph["callback_dependencies"][0]["callback_receipt_id"]
        resolver = next(n for n in nodes if n["id"] == resolver_id)
        unused = m.c.decode(base64.b64decode(receiver["status"]["SuccessValue"]))
        used = m.c.decode(base64.b64decode(resolver["status"]["SuccessValue"]))
        self.assertEqual(unused, "0")
        self.assertEqual(int(unused)+int(used), int(arguments["amount"]))
        self.assertEqual(arguments["msg"], "")
        self.assertEqual(report["collection"]["data_requests_total"], 6)


if __name__ == "__main__":
    unittest.main()
