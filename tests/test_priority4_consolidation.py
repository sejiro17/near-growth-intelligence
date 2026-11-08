"""Offline identity, coverage and single-attempt safeguards for priority 4."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("priority4", ROOT / "analysis/41_consolidate_priority4.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class Priority4Tests(unittest.TestCase):
    def setUp(self):
        self.guard = patch("socket.socket.connect", side_effect=AssertionError("Network forbidden in offline checks"))
        self.guard.start()
        self.addCleanup(self.guard.stop)

    def fixture(self):
        _, successor = m.prior()
        return {"header": {"hash": m.SUBMISSION_HASH, "height": successor["height"]-1,
            "timestamp_nanosec": str(int(successor["timestamp_nanosec"])-1), "total_supply": "123"}}

    def test_timestamp_is_exact_and_anchored_to_saved_successor(self):
        report = m.validate_time(self.fixture())
        self.assertTrue(report["within_original_window"])
        self.assertTrue(report["timestamp_utc"].endswith("Z"))
        for field, value in [("hash", "wrong"), ("height", 999999999), ("timestamp_nanosec", "NaN")]:
            bad = self.fixture()
            bad["header"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.validate_time(bad)
        bad = self.fixture()
        bad["header"]["timestamp"] = 1
        with self.assertRaisesRegex(ValueError, "Conflicting"):
            m.validate_time(bad)

    def test_single_attempt_http_error_retained_and_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            calls = []
            def transport(raw):
                calls.append(raw)
                return {"http_status": 429, "body_complete": True, "transport_error": None}, b"limited"
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "HTTP 429"):
                m.collect(output, transport, lambda _: None)
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(list(output.rglob("stopped.json"))), 1)
            self.assertEqual(next(output.rglob("*.response.body")).read_bytes(), b"limited")
            with self.assertRaisesRegex(ValueError, "already attempted"):
                m.collect(output, transport, lambda _: None)
            self.assertEqual(len(calls), 1)

    def test_coverage_preserves_unavailable_and_selected_examples(self):
        case, _ = m.prior()
        args = [m.c.decode(m.trace.ASSESSMENT.read_bytes())] + [m.csv_rows(n)[0] for n in [18, 20, 19, 23, 24]] + [case]
        rows = m.coverage_rows(*args)
        lookup = {r["account_id"]: r for r in rows}
        self.assertEqual(lookup["sweat-relayer.near"]["transactions"], 13704363)
        self.assertIsNone(lookup["sweat-relayer.near"]["initial_outcomes"])
        self.assertEqual(lookup["sweat-relayer.near"]["selected_downstream_evidence"]["selected_transactions"], 1)
        self.assertIsNone(lookup["0here.tg"]["delegate_action_transactions"])
        self.assertIsNone(lookup["wx-cruce.near"]["original_receivers"])
        self.assertEqual(lookup["wx-cruce.near"]["initial_outcomes"]["SUCCESS_RECEIPT_ID"], 398968)
        self.assertIsNone(lookup["wx-cruce.near"]["selected_downstream_evidence"])
        self.assertEqual(lookup["tinykoala595.near"]["selected_downstream_evidence"]["transactions_with_a_returned_failure"], 18)
        bad = copy.deepcopy(args)
        bad[5][0]["transactions"] = str(int(bad[5][0]["transactions"])+1)
        with self.assertRaisesRegex(ValueError, "Outcome coverage"):
            m.coverage_rows(*bad)
        bad = copy.deepcopy(args)
        bad[1].append(bad[1][0])
        with self.assertRaisesRegex(ValueError, "Duplicate signer-week"):
            m.coverage_rows(*bad)

    def test_saved_consolidation_reproduces_and_counts_each_charge_once(self):
        directory = ROOT / "results/sweat_submission_block_time/20261108T004552Z_9f57ad2f6291"
        report = m.consolidate(directory)
        self.assertEqual(m.c.json_bytes(report), m.REPORT.read_bytes())
        case = report["case_study"]
        self.assertEqual(case["submission_block"]["timestamp_utc"], "2026-09-23T07:11:24.906615725Z")
        self.assertEqual(case["population_coverage"]["confirmed_trace_members_in_saved_window"], 1)
        graph = case["complete_returned_graph"]
        nodes = [graph["transaction_outcome"]] + graph["receipt_outcomes"]
        self.assertEqual(len({n["id"] for n in nodes}), 9)
        self.assertEqual(sum(int(n["recorded_execution_charge_yocto"]) for n in nodes),
                         int(case["recorded_charge_yocto"]))
        self.assertEqual(case["recorded_charge_near"], "0.0007690267153439")
        self.assertTrue(graph["coverage"]["observed_graph_consistent_and_covered"])
        self.assertIsNone(graph["coverage"]["independent_historical_ingestion_completeness"])
        notes = (ROOT / "notes/priority4_attribution_plan.md").read_text()
        self.assertTrue(all(n["id"] in notes for n in nodes))


if __name__ == "__main__":
    unittest.main()
