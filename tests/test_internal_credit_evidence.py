"""Offline checks for result 50 and the single selected credit-origin request."""

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
SPEC = importlib.util.spec_from_file_location("internal_credit", ROOT / "analysis/16_internal_credit_evidence.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class InternalCreditEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.raw = m.SOURCE.read_bytes()
        self.rows = m.c.decode(self.raw)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        guard = patch.object(m.c.http.client, "HTTPSConnection", side_effect=AssertionError("Live network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def test_saved_summary_control_exact_movements_and_reproduction(self):
        report = m.report()
        self.assertEqual(len(report["decoded_records"]), 2)
        self.assertEqual(sum(len(r["events"]) for r in report["decoded_records"]), 6)
        credit = report["selected_credit"]
        self.assertEqual(credit["receipt_id"], "CBEA6sgmmaxoVwLE8iMDHQQ1G8CQRVvo76mDWYfLP5Pm")
        self.assertEqual(credit["amount_base_units"], "1252862790024676320487808800")
        self.assertIsNone(credit["memo"])
        self.assertEqual(report["comparison"]["blocks_before_debit"], 5)
        self.assertEqual(report["comparison"]["nanoseconds_before_debit"], "2910324742")
        self.assertEqual(report["comparison"]["observed_selected_movements_net_base_units"], "0")
        self.assertIsNone(report["attribution"]["verified_fee_credit_amount"])
        self.assertIsNone(report["attribution"]["withdrawal_revenue_origin"])
        self.assertEqual(report["boundary"]["additional_lookback_days_planned"], 0)
        self.assertEqual(m.c.json_bytes(report), m.SUMMARY.read_bytes())
        self.assertEqual(self.raw, m.SOURCE.read_bytes())

    def test_missing_duplicate_and_inconsistent_summary_rejected(self):
        for mutate in (lambda x: x.pop(), lambda x: x.append(copy.deepcopy(x[0])),
                       lambda x: x[0].update({m.S + "output_candidate_rows": "999"}),
                       lambda x: x[0].update({m.S + "verified_fee_credit_amount": "1"})):
            rows = copy.deepcopy(self.rows)
            mutate(rows)
            with self.assertRaises((ValueError, KeyError)):
                m.validate_export(rows)
        self.rows[2] = copy.deepcopy(self.rows[1])
        with self.assertRaisesRegex(ValueError, "Duplicate receipt"):
            m.validate_export(self.rows)

    def test_source_duplicate_flags_and_ordering_mismatches_rejected(self):
        for field, value in (("same_day_receipt_rows", "2"), ("source_block_height_text", "1"),
                             ("source_shard_id_text", "0"), ("app_fee_text_in_logs", "true"),
                             ("source_logs_json", '{"list":[]}')):
            rows = copy.deepcopy(self.rows)
            rows[1][m.E + field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.validate_export(rows)

    def test_amount_types_nonfinite_and_misaligned_arrays_rejected(self):
        for value in (1, "NaN", "Infinity", "1e24", "-1", str(2**128)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.exact(value)
        for raw in ('NaN', 'Infinity', '{"a":1,"a":2}'):
            with self.assertRaises(ValueError):
                m.c.decode(raw)
        source = m.c.decode(self.rows[1][m.E + "source_row_json"])
        event = m.c.decode(source["logs"]["list"][2]["element"][len("EVENT_JSON:"):])
        event["data"][0]["amounts"] = []
        source["logs"]["list"][2]["element"] = "EVENT_JSON:" + json.dumps(event)
        with self.assertRaisesRegex(ValueError, "arrays"):
            m.events(source)

    def test_unsupported_event_version_is_not_guessed(self):
        source = m.c.decode(self.rows[1][m.E + "source_row_json"])
        text = source["logs"]["list"][0]["element"]
        source["logs"]["list"][0]["element"] = text.replace('"version":"0.3.0"', '"version":"99.0.0"')
        with self.assertRaisesRegex(ValueError, "Unsupported event"):
            m.events(source)

    def test_one_manual_request_then_offline_same_candidate_status_plan(self):
        calls, pauses = [], []
        origin = {"transaction_hash": "FFwediesLXUhqu8RwxeEpY2F6sRakHmysAjzwxZbXjXi",
                  "sender_account_id": "fixture-signer.near"}
        def transport(raw):
            request = m.c.decode(raw)
            calls.append(request)
            return {"http_status": 200, "body_complete": True, "transport_error": None,
                    "response_headers": []}, m.c.json_bytes({"jsonrpc": "2.0", "id": request["id"], "result": origin})
        with redirect_stdout(io.StringIO()):
            directory = m.collect_origin(self.root, transport, pauses.append)
        self.assertEqual(len(calls), 1)
        self.assertEqual(pauses, [65])
        self.assertEqual(calls[0]["params"], {"receipt_id": m.report()["selected_credit"]["receipt_id"]})
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(m.main(["prepare-status", "--origin-dir", str(directory)]), 0)
        request = m.c.decode(stdout.getvalue())
        self.assertEqual(request["params"], {"tx_hash": origin["transaction_hash"],
            "sender_account_id": origin["sender_account_id"], "wait_until": "FINAL"})
        self.assertEqual(request["method"], "EXPERIMENTAL_tx_status")
        self.assertEqual(len(calls), 1)
        path = directory / "internal-credit-origin.response.body"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.origin_saved(directory)

    def test_http_and_unknown_history_errors_stop_with_saved_bytes(self):
        for status, body in ((429, b"rate limited"), (200, m.c.json_bytes({"jsonrpc": "2.0",
                "id": "internal-credit-origin", "error": {"code": -32000, "message": "UNKNOWN_RECEIPT"}}))):
            calls = []
            def transport(raw):
                calls.append(raw)
                return {"http_status": status, "body_complete": True, "transport_error": None,
                        "response_headers": []}, body
            with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                m.collect_origin(self.root, transport, lambda _: None)
            self.assertEqual(len(calls), 1)
            self.assertTrue(any(p.read_bytes() == body for p in self.root.rglob("*.response.body")))

    def test_default_stdout_and_exclusive_output(self):
        path = self.root / "summary.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(m.main(["check", "--output", str(path)]), 0)
            before = path.read_bytes()
            self.assertEqual(m.main(["check", "--output", str(path)]), 1)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
