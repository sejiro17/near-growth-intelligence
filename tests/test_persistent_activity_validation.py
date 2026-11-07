"""Offline validation regressions using the saved SQL 41 export."""

import copy
import importlib.util
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_persistence", ROOT / "analysis/20_validate_persistent_activity_pilot.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PersistentActivityValidationTests(unittest.TestCase):
    def records(self):
        rows = m.base.decode(m.SOURCE.read_bytes())
        return [{**r, "record_json": m.base.decode(r["record_json"])} for r in rows]

    def encoded(self, rows):
        return m.base.json_bytes([{**r, "record_json": m.base.json_bytes(r["record_json"]).decode()} for r in rows])

    def point(self, rows, cohort="2026-08-17", offset=8):
        return next(r["record_json"] for r in rows if r["row_kind"] == "CHECKPOINT"
                    and r["record_json"]["cohort_week"] == cohort and r["record_json"]["week_offset"] == offset)

    def test_actual_export_controls_concentration_and_comparisons(self):
        before = m.SOURCE.read_bytes()
        result = m.report()
        self.assertEqual(result["validation"], "STRUCTURAL_AND_SAVED_CONTROL_CHECKS_PASSED")
        self.assertTrue(result["result55_reproduced_byte_for_byte"])
        self.assertEqual(result["source_summary"]["transaction_rows"], 53959076)
        self.assertEqual((result["complete_checkpoints"], result["unavailable_checkpoints"]), (9, 3))
        self.assertEqual(result["overlapping_result11_counts_checked"], 3)
        self.assertEqual(result["maximum_difference_week"], "2026-10-12")
        self.assertEqual(Decimal(result["maximum_absolute_conversion_difference_near"]), Decimal("7.2853641477632E-10"))
        point = next(p for p in result["checkpoint_metrics"] if p["cohort_week"] == "2026-08-17" and p["week_offset"] == 8)
        with localcontext() as ctx:
            ctx.prec = 60
            self.assertEqual(Decimal(point["returner_hhi"]), Decimal(point["sum_squared_returner_transactions"])/Decimal(3528043**2))
            self.assertEqual(Decimal(point["top_10_returner_transaction_share_pct"]), Decimal(100)*2650181/3528043)
        self.assertEqual(m.SOURCE.read_bytes(), before)

    def test_truncated_and_duplicate_checkpoint_exports_rejected(self):
        rows = self.records()
        with self.assertRaisesRegex(ValueError, "23-row"):
            m.validate(self.encoded(rows[:-1]))
        points = [r for r in rows if r["row_kind"] == "CHECKPOINT"]
        points[-1]["record_json"] = copy.deepcopy(points[0]["record_json"])
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            m.validate(self.encoded(rows))

    def test_schema_changes_and_duplicate_nested_keys_rejected(self):
        rows = self.records()
        self.point(rows)["unexpected"] = 1
        with self.assertRaisesRegex(ValueError, "nested schema"):
            m.validate(self.encoded(rows))
        raw = m.base.decode(m.SOURCE.read_bytes())
        raw[0]["record_json"] = '{"duplicate":1,"duplicate":2}'
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            m.validate(m.base.json_bytes(raw))

    def test_denominator_followup_and_transaction_controls_rejected(self):
        for field, value in (("cohort_accounts", 141296), ("followup_week_end", "2026-10-17"),
                             ("observed_week_transactions", 4909533)):
            with self.subTest(field=field):
                rows = self.records()
                self.point(rows)[field] = value
                with self.assertRaises(ValueError):
                    m.validate(self.encoded(rows))

    def test_incomplete_returns_stay_null_and_repeated_counts_are_fixed_checkpoints(self):
        result = m.validate(m.SOURCE.read_bytes())
        for p in result["checkpoint_metrics"]:
            if not p["measurement_available"]:
                self.assertIsNone(p["returning_accounts"])
                self.assertIsNone(p["recorded_conversion_spending_near"])
                self.assertIsNone(p["repeated_checkpoint_returners_accounts"])
        rows = self.records()
        self.point(rows, "2026-08-24", 8)["returning_accounts"] = 0
        with self.assertRaisesRegex(ValueError, "zero-filled"):
            m.validate(self.encoded(rows))
        cohort = next(c for c in result["cohort_summary"] if c["cohort_week"] == "2026-08-17")
        self.assertEqual(cohort["repeated_checkpoint_returners_accounts"], 53455)
        self.assertLess(cohort["repeated_checkpoint_returners_accounts"], cohort["checkpoint_returners"]["8"])
        self.assertIn("+1/+4/+8", result["definitions"]["repeated_checkpoint_return"])

    def test_nonfinite_and_rounded_squared_counts_rejected(self):
        for value in ("NaN", "Infinity", "-Infinity"):
            rows = self.records()
            self.point(rows)["recorded_conversion_spending_near"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Nonfinite"):
                m.validate(self.encoded(rows))
        rows = self.records()
        self.point(rows)["sum_squared_returner_transactions"] = "1.5"
        with self.assertRaisesRegex(ValueError, "Invalid count"):
            m.validate(self.encoded(rows))

    def test_exact_monetary_string_is_preserved_without_float(self):
        rows = self.records()
        exact = "0.12345678901234567890123456789012345678"
        self.point(rows)["recorded_conversion_spending_near"] = exact
        result = m.validate(self.encoded(rows))
        point = next(p for p in result["checkpoint_metrics"] if p["cohort_week"] == "2026-08-17" and p["week_offset"] == 8)
        self.assertEqual(point["recorded_conversion_spending_near"], exact)

    def test_missing_cost_is_unavailable_and_consistent_with_week_and_source(self):
        rows = self.records()
        point = self.point(rows)
        point["invalid_conversion_cost_rows"] = 1
        point["recorded_conversion_spending_near"] = None
        with self.assertRaisesRegex(ValueError, "exceeds whole week"):
            m.validate(self.encoded(rows))
        week = next(r["record_json"] for r in rows if r["row_kind"] == "WEEK_CONTROL" and r["record_json"]["week_start"] == "2026-10-12")
        week["invalid_conversion_cost_rows"] = 1
        week["recorded_conversion_spending_near"] = None
        next(r["record_json"] for r in rows if r["row_kind"] == "SUMMARY")["invalid_conversion_cost_rows"] = 1
        result = m.validate(self.encoded(rows))
        point = next(p for p in result["checkpoint_metrics"] if p["cohort_week"] == "2026-08-17" and p["week_offset"] == 8)
        self.assertIsNone(point["recorded_conversion_spending_near"])

    def test_impossible_concentration_and_unexpected_cost_null_rejected(self):
        rows = self.records()
        self.point(rows)["top_20_transactions"] = 3528043
        with self.assertRaises(ValueError):
            m.validate(self.encoded(rows))
        rows = self.records()
        self.point(rows)["recorded_conversion_spending_near"] = None
        with self.assertRaisesRegex(ValueError, "null safeguard"):
            m.validate(self.encoded(rows))

    def test_next_sql_scope_partition_filters_and_duplicate_exclusion(self):
        code = re.sub(r'/\*.*?\*/', '', m.NEXT_SQL.read_text(), flags=re.S)
        self.assertEqual(code.count('`bigquery-public-data.crypto_near_mainnet_us.transactions`'), 1)
        self.assertEqual(code.count('`bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`'), 1)
        self.assertEqual(code.count('`bigquery-public-data.crypto_near_mainnet_us.blocks`'), 1)
        self.assertNotIn('transaction_actions', code)
        self.assertIn("WHERE t.block_date BETWEEN DATE '2026-08-17' AND DATE '2026-08-30'", code)
        self.assertIn("WHERE o.block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-24'", code)
        self.assertIn("WHERE block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-24'", code)
        self.assertIn('WHERE n.outcome_rows = 1', code)
        self.assertIn('WHERE n.block_rows = 1', code)
        self.assertNotIn('ROW_NUMBER', code)
        self.assertNotIn('ANY_VALUE', code)
        self.assertIn("sc.transactions = 3528043", code)
        self.assertIn("cc.repeated_checkpoint_accounts = 53455", code)
        self.assertIn('f.at_1 AND f.at_4 AND f.at_8', code)
        self.assertIn('p.valid_initial_cost_transactions = p.transactions', code)
        self.assertNotIn('COALESCE(cost_yocto', code)
        self.assertIn('NO_OUTCOME_IN_LOOKUP_WINDOW', code)

    def test_stdout_and_exclusive_derived_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'validation.json'
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(m.main(['--output', str(path)]), 0)
                before = path.read_bytes()
                self.assertEqual(m.main(['--output', str(path)]), 1)
                self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(before)["source_export_sha256"], m.identity(m.SOURCE)["sha256"])


if __name__ == '__main__':
    unittest.main()
