"""Offline tests for the fixed single-request historical account witness."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bitwise_witness", ROOT / "analysis/12_collect_bitwise_parent_witness.py")
witness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(witness)


class BitwiseParentWitnessTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.calls, self.pauses = [], []
        guard = patch.object(witness.capture.http.client, "HTTPSConnection",
                             side_effect=AssertionError("Live network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)
        output = redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)

    def result(self):
        return {"block_hash": witness.PARENT_HASH, "block_height": witness.PARENT_HEIGHT,
                "amount": "12345678901234567890123456789", "locked": "99999999999999999999999999999",
                "code_hash": "fixture-code-hash", "storage_usage": 100, "storage_paid_at": 0}

    def transport(self, raw):
        self.calls.append(raw)
        self.assertEqual(raw, witness.REQUEST.read_bytes())
        self.response = witness.capture.json_bytes({
            "jsonrpc": "2.0", "id": witness.request()["id"], "result": self.result()})
        return {"http_status": 200, "body_complete": True, "transport_error": None,
                "response_headers": [["Content-Type", "application/json"]]}, self.response

    def test_durable_comparison_and_provenance_inputs(self):
        raw = witness.COMPARISON.read_bytes()
        self.assertEqual(witness.capture.sha256(raw), witness.COMPARISON_SHA256)
        provenance = witness.capture.decode(witness.PROVENANCE.read_bytes())
        self.assertEqual(provenance["sha256"], witness.COMPARISON_SHA256)
        self.assertEqual(provenance["bytes"], len(raw))
        self.assertTrue(provenance["derivation_method"])
        self.assertIn("not confirmed", " ".join(provenance["interpretation_limits"]))
        inputs, position = witness.preflight()
        self.assertGreaterEqual(len(inputs), 31)
        self.assertIsInstance(position, int)

    def test_exact_request_and_offline_plan(self):
        self.assertEqual(witness.request(), {
            "jsonrpc": "2.0", "id": "A-bitwise-parent-account", "method": "query",
            "params": {"request_type": "view_account", "account_id": "bitwise_1.poolv1.near",
                       "block_id": "FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2"}})
        self.assertEqual(witness.main(["plan"]), 0)

    def test_one_capture_preserves_bytes_and_records_no_monetary_change(self):
        directory = witness.collect(self.root, self.transport, self.pauses.append)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.pauses, [65])
        stem = witness.request()["id"]
        self.assertEqual((directory / f"{stem}.response.body").read_bytes(), self.response)
        self.assertEqual((directory / f"{stem}.request.json").read_bytes(), witness.REQUEST.read_bytes())
        metadata = witness.capture.decode((directory / f"{stem}.metadata.json").read_bytes())
        self.assertEqual(metadata["endpoint"], "https://archival-rpc.mainnet.near.org")
        self.assertEqual(metadata["http_status"], 200)
        self.assertEqual(metadata["response_sha256"], witness.capture.sha256(self.response))
        self.assertIn("started_at", metadata)
        self.assertIn("finished_at", metadata)
        self.assertEqual(witness.main(["validate", "--witness-dir", str(directory)]), 0)
        report = witness.validate_saved(directory)
        for field in ("monetary_change", "independently_measured_issuance", "independently_measured_actual_burn"):
            self.assertIsNone(report[field])

    def test_wrong_identity_partial_or_inexact_account_fields_rejected(self):
        for field, value in (("block_hash", "wrong"), ("block_height", 216877934),
                             ("block_height", "216877933"), ("amount", None),
                             ("locked", 123), ("storage_usage", None),
                             ("code_hash", ""), ("account_id", "another.near")):
            with self.subTest(field=field, value=value):
                result = self.result()
                result[field] = value
                with self.assertRaises(ValueError):
                    witness.validate_account(result)

    def test_bad_http_transport_and_rpc_errors_stop_after_one_attempt(self):
        for status, complete, error, body in (
            (429, True, None, b"rate limited"),
            (302, True, None, b"redirect"),
            (200, False, "TimeoutError", b"partial response\x00\xff"),
            (200, True, None, witness.capture.json_bytes({
                "jsonrpc": "2.0", "id": witness.request()["id"],
                "error": {"code": -32000, "message": "unavailable history"}})),
        ):
            with self.subTest(status=status, complete=complete, error=error):
                calls = []
                def failure(raw):
                    calls.append(raw)
                    return {"http_status": status, "body_complete": complete,
                            "transport_error": error, "response_headers": []}, body
                output = self.root / str(len(list(self.root.iterdir())))
                with self.assertRaises(ValueError):
                    witness.collect(output, failure, self.pauses.append)
                self.assertEqual(len(calls), 1)
                saved = list(output.rglob("*.response.body"))
                self.assertEqual(len(saved), 1)
                self.assertEqual(saved[0].read_bytes(), body)
                self.assertFalse((saved[0].parent / "validation.json").exists())

    def test_changed_prepared_parameters_stop_before_capture(self):
        altered = witness.request()
        altered["params"]["block_id"] = "another-block"
        path = self.root / "changed-request.json"
        path.write_bytes(witness.capture.json_bytes(altered))
        with patch.object(witness, "REQUEST", path), self.assertRaisesRegex(ValueError, "Prepared request"):
            witness.collect(self.root / "not-created", self.transport, self.pauses.append)
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / "not-created").exists())

    def test_wrong_returned_block_is_retained_but_not_validated(self):
        original = self.result()
        original["block_hash"] = "wrong"
        with patch.object(self, "result", return_value=original):
            with self.assertRaisesRegex(ValueError, "block identity"):
                witness.collect(self.root, self.transport, self.pauses.append)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(len(list(self.root.rglob("*.response.body"))), 1)
        self.assertEqual(list(self.root.rglob("validation.json")), [])

    def test_validate_command_cannot_collect(self):
        with patch.object(witness, "collect", side_effect=AssertionError("Cannot collect")):
            with redirect_stderr(io.StringIO()):
                self.assertEqual(witness.main(["validate", "--witness-dir", str(self.root)]), 1)


if __name__ == "__main__":
    unittest.main()
