"""Offline validation of exact deposits and the fixed two-stage origin procedure."""

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


decoder = module("decoder_test", "14_decode_frontend_native_transfers.py")
trace = module("trace_test", "15_trace_frontend_transfer_origin.py")


class FrontendNativeTransfersTests(unittest.TestCase):
    def setUp(self):
        self.raw = decoder.SOURCE.read_bytes()
        self.rows = decoder.decode(self.raw)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        guard = patch.object(trace.capture.http.client, "HTTPSConnection",
                             side_effect=AssertionError("Live network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def rewrite_deposit(self, value):
        row = self.rows[1]
        args = json.dumps({"deposit": value})
        source = decoder.decode(row[decoder.A + "source_row_json"])
        source["args"] = args
        row[decoder.A + "source_row_json"] = json.dumps(source)
        row[decoder.A + "raw_args_json"] = json.dumps(args)
        row[decoder.A + "raw_args_scalar_text"] = args

    def test_saved_export_exact_totals_and_unclassified_labels(self):
        report = decoder.report()
        self.assertEqual(report["summary"], {"transfer_rows": 22,
            "amount_yoctonear": "8000969220749197522847764034",
            "amount_near": "8000.969220749197522847764034"})
        self.assertEqual(report["source"]["sha256"], trace.SOURCE_SHA256)
        target = next(x for x in report["transfers"] if x["receipt_id"] == trace.RECEIPT)
        self.assertEqual(target["amount_yoctonear"], "1252862790024676320487808800")
        self.assertEqual(target["amount_near"], "1252.862790024676320487808800")
        self.assertTrue(all(x["economic_classification"] == "UNCLASSIFIED_TRANSFER"
                            and x["originating_transaction"] is None for x in report["transfers"]))
        self.assertEqual(decoder.SOURCE.read_bytes(), self.raw)
        if decoder.OUTPUT.exists():
            self.assertEqual(decoder.json_bytes(report), decoder.OUTPUT.read_bytes())

    def test_float_sized_integer_remains_exact_and_string_is_preserved(self):
        self.rewrite_deposit("9007199254740993")
        row = decoder.validate_rows(self.rows)[0]
        self.assertEqual(row["amount_yoctonear"], "9007199254740993")
        self.assertEqual(row["amount_near"], "0.000000009007199254740993")
        self.rewrite_deposit("0009")
        self.assertEqual(decoder.validate_rows(self.rows)[0]["amount_yoctonear"], "0009")

    def test_invalid_or_inexact_deposits_rejected(self):
        for value in (123, 1.5, None, True, "1e24", "-1", "+1", "1.0", "", "NaN", str(2**128)):
            with self.subTest(value=value):
                self.rewrite_deposit(value)
                with self.assertRaises(ValueError):
                    decoder.validate_rows(self.rows)

    def test_encoding_layers_and_duplicate_keys_rejected(self):
        for raw in ('{"deposit":"1","deposit":"2"}', 'NaN', 'Infinity'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                decoder.decode(raw)
        row = self.rows[1]
        row[decoder.A + "raw_args_json"] = '{"deposit":"1"}'
        with self.assertRaisesRegex(ValueError, "representations"):
            decoder.validate_rows(self.rows)
        row[decoder.A + "raw_args_json"] = json.dumps('{"deposit":"1"}')
        with self.assertRaisesRegex(ValueError, "representations"):
            decoder.validate_rows(self.rows)

    def test_summary_missing_duplicate_and_changed_classification_rejected(self):
        for mutation in (
            lambda x: x.pop(),
            lambda x: x.append(copy.deepcopy(x[1])),
            lambda x: x.append(copy.deepcopy(x[0])),
            lambda x: x[0].update({"summary_record.c.missing_same_day_initial_tx_matches": "0"}),
            lambda x: x[1].update({"transfer_record.economic_classification": "REVENUE"}),
        ):
            rows = copy.deepcopy(self.rows)
            mutation(rows)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                decoder.validate_rows(rows)
        # Match the summary so duplicate identity is independently tested.
        rows = copy.deepcopy(self.rows)
        rows[2] = copy.deepcopy(rows[1])
        with self.assertRaisesRegex(ValueError, "Duplicate action identity"):
            decoder.validate_rows(rows)

    def test_outcome_ambiguity_invalid_coverage_and_source_mismatch_rejected(self):
        for field, value in (
            (decoder.O + "outcome_rows", "0"), (decoder.O + "outcome_rows", "2"),
            (decoder.E + "execution_block_match_rows", "2"),
            (decoder.O + "unresolved_execution_block_rows", "1"),
            (decoder.E + "executed_in_block_hash", "wrong"),
            (decoder.A + "source_shard_id_text", "0"),
            (decoder.A + "source_timestamp_utc", "2026-09-24 00:00:00 UTC"),
        ):
            rows = copy.deepcopy(self.rows)
            rows[1][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                decoder.validate_rows(rows)

    def test_stdout_reproduction_and_no_overwrite(self):
        output = self.root / "decoded.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(decoder.main(["--output", str(output)]), 0)
            before = output.read_bytes()
            self.assertEqual(decoder.main(["--output", str(output)]), 1)
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(decoder.main([]), 0)
            self.assertEqual(stdout.getvalue().encode(), before)
        self.assertEqual(output.read_bytes(), before)

    def origin(self):
        return {"transaction_hash": "5sjupQ9Lm2kVrmWD923ghdAxRNx5zWpzix1PHLSFYYFF",
                "sender_account_id": "fixture-signer.near"}

    def transport(self, result=None, status=200, error=None):
        def send(raw):
            request = trace.capture.decode(raw)
            self.calls.append(request)
            envelope = {"jsonrpc": "2.0", "id": request["id"]}
            envelope["error" if error else "result"] = error or result or self.origin()
            return {"http_status": status, "response_headers": [], "body_complete": True,
                    "transport_error": None}, trace.capture.json_bytes(envelope)
        return send

    def collect_origin(self, **kwargs):
        self.calls, self.pauses = [], []
        with redirect_stdout(io.StringIO()):
            return trace.collect(trace.origin_request(), self.root, transport=self.transport(**kwargs),
                                 pause=self.pauses.append)

    def test_origin_exact_one_request_then_offline_status_preparation(self):
        self.assertEqual(trace.origin_request()["params"], {"receipt_id": trace.RECEIPT})
        directory = self.collect_origin()
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.pauses, [65])
        self.assertEqual(trace.recorded_origin(directory), self.origin())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(trace.main(["prepare-status", "--origin-dir", str(directory)]), 0)
        request = decoder.decode(stdout.getvalue())
        self.assertEqual(request, {"jsonrpc": "2.0", "id": "transfer-transaction-status",
            "method": "EXPERIMENTAL_tx_status", "params": {"tx_hash": self.origin()["transaction_hash"],
                "sender_account_id": "fixture-signer.near", "wait_until": "FINAL"}})
        self.assertEqual(len(self.calls), 1)
        path = directory / "transfer-origin.response.body"
        raw = path.read_bytes()
        path.write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            trace.recorded_origin(directory)

    def test_http_and_rpc_errors_stop_after_one_attempt_and_preserve_response(self):
        for kwargs in ({"status": 429}, {"error": {"code": -32000, "message": "UNKNOWN_RECEIPT"}},
                       {"error": {"code": -32601, "message": "Method not found"}}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.collect_origin(**kwargs)
            self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(list(self.root.rglob("*.response.body"))), 3)

    def test_invalid_origin_and_wrong_or_partial_transaction_rejected(self):
        for result in ({}, {"transaction_hash": trace.RECEIPT, "sender_account_id": None},
                       {"transaction_hash": "1" * 44, "sender_account_id": "x.near"}):
            with self.subTest(result=result), self.assertRaises(ValueError):
                trace.validate_origin(result)
        for result in ({}, {"final_execution_status": "FINAL", "transaction": {
            "hash": self.origin()["transaction_hash"], "signer_id": "another.near"}}):
            with self.assertRaises(ValueError):
                trace.validate_status_identity(result, self.origin())

    def test_separately_invoked_status_uses_resolved_pair_and_exact_target_amount(self):
        origin_dir = self.collect_origin()
        saved = trace.target()
        result = {"final_execution_status": "FINAL", "transaction": {
            "hash": self.origin()["transaction_hash"], "signer_id": self.origin()["sender_account_id"]},
            "receipts_outcome": [{"id": trace.RECEIPT, "block_hash": saved["block_hash"],
                "outcome": {"executor_id": decoder.ACCOUNT, "status": {"SuccessValue": ""}}}],
            "receipts": [{"receipt_id": trace.RECEIPT, "predecessor_id": "intents.near",
                "receiver_id": decoder.ACCOUNT, "receipt": {"Action": {"actions": [
                    {"Transfer": {"deposit": saved["amount_yoctonear"]}}]}}}]}
        payload = trace.status_request(self.origin())
        with redirect_stdout(io.StringIO()):
            directory = trace.collect(payload, self.root, origin_dir=origin_dir,
                transport=self.transport(result=result), pause=self.pauses.append)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.calls[-1]["params"]["tx_hash"], self.origin()["transaction_hash"])
        self.assertEqual((directory / "origin_input/transfer-origin.response.body").read_bytes(),
                         (origin_dir / "transfer-origin.response.body").read_bytes())
        # This gate validates identities, not completeness of this deliberately
        # minimal fixture's absent parent/callback graph.
        result["receipts"][0]["receipt"]["Action"]["actions"][0]["Transfer"]["deposit"] = "1"
        with self.assertRaisesRegex(ValueError, "deposit"):
            trace.validate_status_identity(result, self.origin())


if __name__ == "__main__":
    unittest.main()
