"""Offline coverage, return-definition and compact-export validation checks."""

import copy
import importlib.util
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("persistent_activity", ROOT / "analysis/19_persistent_activity_plan.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PersistentActivityTests(unittest.TestCase):
    def activity(self):
        start = m.START
        values = {0: [("a.near", 10), ("b.near", 5)], 1: [("a.near", 3), ("outside.near", 7)],
                  2: [("b.near", 4)], 4: [("a.near", 2)], 8: [("a.near", 6)]}
        rows = [{"week_start": start + timedelta(weeks=k), "signer": signer, "transactions": tx,
                 "conversion_cost_near": "0.000000000000000000000001"}
                for k, items in values.items() for signer, tx in items]
        return rows, set(m.weeks(start, start + timedelta(weeks=8)))

    def fixture(self):
        _, weekly, old, conversion = m.controls()
        total = sum(m.count(weekly[str(w)]["transactions"]) for w in m.weeks())
        result = [{"row_kind": "SUMMARY", "record_json": {
            "source_start": str(m.START), "source_end": str(m.END), "transaction_rows": total,
            "distinct_transaction_hashes": total, "observed_days": 70, "observed_hours": 1680,
            "missing_transaction_hashes": 0, "missing_signer_accounts": 0, "missing_receiver_accounts": 0,
            "invalid_timestamps": 0, "invalid_conversion_cost_rows": 0, "source_controls_passed": True,
            "cohort_count": 4, "week_control_rows": 10, "checkpoint_rows": 12}}]
        for week in m.weeks():
            key = str(week)
            result.append({"row_kind": "WEEK_CONTROL", "record_json": {"week_start": key,
                "week_end": str(week + timedelta(days=6)), "transactions": m.count(weekly[key]["transactions"]),
                "distinct_transaction_hashes": m.count(weekly[key]["transactions"]),
                "active_accounts": m.count(weekly[key]["weekly_active_signing_accounts"]),
                "observed_days": 7, "observed_hours": 168, "invalid_conversion_cost_rows": 0,
                "recorded_conversion_spending_near": conversion.get(key, {}).get("recorded_conversion_cost_near", "1000")}})
        for cohort in m.COHORTS:
            size = m.count(weekly[str(cohort)]["weekly_active_signing_accounts"])
            returning = {}
            for k in m.OFFSETS:
                target = cohort + timedelta(weeks=k)
                if target + timedelta(days=6) <= m.END:
                    saved = old.get((str(cohort), k))
                    returning[k] = m.count(saved["active_cohort_accounts"]) if saved else min(size,
                        m.count(weekly[str(target)]["weekly_active_signing_accounts"])) // 2
            pair = min(returning[1], returning[4]) if 4 in returning else None
            repeated = min(pair, returning[8]) if 8 in returning else None
            for k in m.OFFSETS:
                target = cohort + timedelta(weeks=k)
                complete = target + timedelta(days=6) <= m.END
                n = returning.get(k)
                result.append({"row_kind": "CHECKPOINT", "record_json": {
                    "cohort_week": str(cohort), "cohort_week_end": str(cohort + timedelta(days=6)), "week_offset": k,
                    "followup_week": str(target), "followup_week_end": str(target + timedelta(days=6)),
                    "followup_complete": complete, "source_controls_passed": True, "measurement_available": complete,
                    "cohort_accounts": size, "observed_week_transactions": m.count(weekly[str(target)]["transactions"]) if complete else None,
                    "returning_accounts": n, "returning_transactions": n,
                    "top_1_transactions": 1 if complete else None,
                    "top_10_transactions": min(n, 10) if complete else None,
                    "top_20_transactions": min(n, 20) if complete else None,
                    "sum_squared_returner_transactions": str(n) if complete else None,
                    "invalid_conversion_cost_rows": 0 if complete else None,
                    "recorded_conversion_spending_near": "0" if complete else None,
                    "return_at_1_and_4_accounts": pair, "repeated_checkpoint_returners_accounts": repeated,
                    "any_return_weeks_1_to_4_accounts": size if pair is not None else None,
                    "any_return_weeks_1_to_8_accounts": size if repeated is not None else None,
                    "attribution_scope": "SUBMISSION_WEEK_OUTER_SIGNER_INITIAL_RECEIPT_ECONOMICS_NOT_EXTRACTED"}})
        return result

    def encoded(self, rows):
        return m.json_bytes([{**r, "record_json": m.json_bytes(r["record_json"]).decode()} for r in rows])

    def test_saved_coverage_and_available_returns(self):
        p = m.plan()
        self.assertEqual(p["expected_source_transactions"], 53959076)
        self.assertEqual(sum(r["complete_saved_transaction_followup"] for r in p["cohort_points"]), 9)
        missing = next(r for r in p["cohort_points"] if r["cohort_week"] == "2026-08-24" and r["week_offset"] == 8)
        self.assertEqual(missing["missing_saved_dates"], ["2026-10-25"])
        earlier = next(r for r in p["cohort_points"] if r["cohort_week"] == "2026-08-10" and r["week_offset"] == 1)
        self.assertEqual(earlier["initial_receipt_reference_window"], "UNAVAILABLE_IN_INITIAL_EXECUTION_PILOT")
        self.assertIsNone(earlier["saved_exact_return_accounts"])
        self.assertEqual(p["saved_spike_lifecycle_comparison"]["absent_accounts"], 374731)
        self.assertEqual(p["saved_spike_lifecycle_comparison"]["successful_self_delete_absent_accounts"], 309280)

    def test_exact_return_union_repeated_and_network_denominator(self):
        rows, complete = self.activity()
        out = m.reference_metrics(rows, m.START, 1, complete)
        self.assertEqual(out["cohort_accounts"], 2)
        self.assertEqual(out["returning_accounts"], 1)
        self.assertEqual(out["returning_transactions"], 3)
        self.assertEqual(out["observed_week_transactions"], 10)
        self.assertEqual(out["any_return_weeks_1_to_4_accounts"], 2)
        self.assertEqual(out["return_at_1_and_4_accounts"], 1)
        self.assertEqual(out["repeated_checkpoint_returners_accounts"], 1)
        self.assertEqual(out["recorded_conversion_spending_near"], "1E-24")

    def test_incomplete_followup_is_unavailable_and_does_not_change_short_horizon(self):
        rows, complete = self.activity()
        complete.remove(m.START + timedelta(weeks=8))
        out = m.reference_metrics(rows, m.START, 8, complete)
        self.assertIsNone(out["returning_accounts"])
        self.assertIsNone(out["recorded_conversion_spending_near"])
        self.assertIsNone(out["repeated_checkpoint_returners_accounts"])
        self.assertEqual(out["return_at_1_and_4_accounts"], 1)

    def test_zero_returns_and_missing_cost_are_distinct(self):
        rows, complete = self.activity()
        rows = [r for r in rows if r["week_start"] != m.START + timedelta(weeks=8)]
        rows.append({"week_start": m.START + timedelta(weeks=8), "signer": "new.near", "transactions": 2,
                     "conversion_cost_near": "1"})
        out = m.reference_metrics(rows, m.START, 8, complete)
        self.assertEqual(out["returning_accounts"], 0)
        self.assertEqual(out["recorded_conversion_spending_near"], "0")
        next(r for r in rows if r["week_start"] == m.START + timedelta(weeks=1) and r["signer"] == "a.near")["conversion_cost_near"] = None
        self.assertIsNone(m.reference_metrics(rows, m.START, 1, complete)["recorded_conversion_spending_near"])

    def test_duplicate_account_week_and_bad_numbers_rejected(self):
        rows, complete = self.activity()
        rows.append(copy.deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate account/week"):
            m.reference_metrics(rows, m.START, 1, complete)
        for value in ("NaN", "Infinity", "-1", "1.5", True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.count(value)

    def test_compact_export_and_saved_overlap_validate(self):
        result = m.validate_export(self.encoded(self.fixture()))
        self.assertEqual(result["validation"], "STRUCTURAL_AND_SAVED_CONTROL_CHECKS_PASSED")
        self.assertEqual(len(result["checkpoint_metrics"]), 12)
        point = next(r for r in result["checkpoint_metrics"] if r["cohort_week"] == "2026-08-24" and r["week_offset"] == 1)
        self.assertEqual(point["returning_accounts"], 108956)

    def test_missing_duplicate_and_zero_filled_incomplete_export_rejected(self):
        rows = self.fixture()
        with self.assertRaises(ValueError):
            m.validate_export(self.encoded(rows[:-1]))
        rows = self.fixture()
        points = [r for r in rows if r["row_kind"] == "CHECKPOINT"]
        points[-1]["record_json"] = copy.deepcopy(points[0]["record_json"])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            m.validate_export(self.encoded(rows))
        rows = self.fixture()
        next(r["record_json"] for r in rows if r["row_kind"] == "CHECKPOINT" and not r["record_json"]["followup_complete"])["returning_accounts"] = 0
        with self.assertRaisesRegex(ValueError, "zero-filled"):
            m.validate_export(self.encoded(rows))

    def test_concentration_intersection_spending_and_source_controls_rejected(self):
        mutations = [lambda r: r[0]["record_json"].update(source_controls_passed=False),
                     lambda r: r[-12]["record_json"].update(top_10_transactions=999999999),
                     lambda r: r[-12]["record_json"].update(repeated_checkpoint_returners_accounts=999999999),
                     lambda r: r[-12]["record_json"].update(recorded_conversion_spending_near=None)]
        for mutate in mutations:
            rows = self.fixture()
            mutate(rows)
            with self.assertRaises(ValueError):
                m.validate_export(self.encoded(rows))

    def test_saved_cost_discrepancy_is_review_required_not_source_accuracy_claim(self):
        rows = self.fixture()
        row = next(r["record_json"] for r in rows if r["row_kind"] == "WEEK_CONTROL" and r["record_json"]["week_start"] == "2026-08-24")
        row["recorded_conversion_spending_near"] = "99999"
        result = m.validate_export(self.encoded(rows))
        self.assertEqual(result["validation"], "SAVED_ARITHMETIC_REVIEW_REQUIRED")
        self.assertEqual(len(result["warnings"]), 1)

    def test_sql_one_partitioned_source_and_intentional_nulls(self):
        code = (ROOT / "sql/41_persistent_activity_transaction_pilot.sql").read_text()
        code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
        self.assertEqual(code.count('`bigquery-public-data.crypto_near_mainnet_us.transactions`'), 1)
        self.assertIn("WHERE block_date BETWEEN DATE '2026-08-10' AND DATE '2026-10-18'", code)
        self.assertNotIn('execution_outcomes', code)
        self.assertNotIn('transaction_actions', code)
        self.assertIn('GROUP BY week_start, signer_account_id', code)
        self.assertIn('UNNEST([1, 4, 8])', code)
        self.assertIn('g.source_valid AND p.followup_complete', code)

    def test_cli_stdout_and_exclusive_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['plan', '--output', str(path)]), 0)
                before = path.read_bytes()
                self.assertEqual(m.main(['plan', '--output', str(path)]), 1)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
