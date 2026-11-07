"""Focused checks against disposable copies of the saved evidence."""

import csv
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "analysis" / "10_supply_comparison_check.py"
SPEC = importlib.util.spec_from_file_location("supply_comparison_check", SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class SupplyComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        for filename in checker.SOURCES.values():
            (self.directory / filename).write_bytes((checker.RESULTS / filename).read_bytes())

    def edit(self, key, change):
        path = self.directory / checker.SOURCES[key]
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fields, rows = reader.fieldnames, list(reader)
        change(fields, rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def restore(self, key):
        filename = checker.SOURCES[key]
        (self.directory / filename).write_bytes((checker.RESULTS / filename).read_bytes())

    def test_missing_and_duplicate_dates_in_every_source(self):
        for key in checker.SOURCES:
            with self.subTest(source=key, case="missing"):
                self.edit(key, lambda fields, rows: rows.pop())
                with self.assertRaisesRegex(ValueError, "incomplete or unexpected dates"):
                    checker.audit(self.directory)
                self.restore(key)
            with self.subTest(source=key, case="duplicate"):
                self.edit(key, lambda fields, rows: rows.append(dict(rows[0])))
                with self.assertRaisesRegex(ValueError, "duplicate date"):
                    checker.audit(self.directory)
                self.restore(key)

    def test_unexpected_date_and_incomplete_week(self):
        self.edit("validators", lambda fields, rows: rows[-1].update(block_date="2026-10-19"))
        with self.assertRaisesRegex(ValueError, "incomplete or unexpected dates"):
            checker.audit(self.directory)
        self.restore("validators")
        self.edit("conversions", lambda fields, rows: rows[0].update(week_end="2026-08-29"))
        with self.assertRaisesRegex(ValueError, "incomplete week"):
            checker.audit(self.directory)

    def test_required_columns_in_every_source(self):
        for key in checker.SOURCES:
            with self.subTest(source=key):
                def remove_column(fields, rows):
                    field = fields.pop()
                    for row in rows:
                        del row[field]
                self.edit(key, remove_column)
                with self.assertRaisesRegex(ValueError, "missing required columns"):
                    checker.audit(self.directory)
                self.restore(key)

    def test_nonfinite_numbers_in_every_source(self):
        for key in checker.SOURCES:
            field = next(k for k in checker.COLUMNS[key].split() if k not in checker.TEXT_FIELDS)
            for value in ("NaN", "sNaN", "Infinity", "-Infinity"):
                with self.subTest(source=key, value=value):
                    self.edit(key, lambda fields, rows: rows[0].update({field: value}))
                    with self.assertRaisesRegex(ValueError, "nonfinite"):
                        checker.audit(self.directory)
                    self.restore(key)

    def test_decimal_digits_are_preserved_directly_from_csv(self):
        value = "1304386568.8725951234567890123456789"
        self.edit("supply", lambda fields, rows: rows[0].update(closing_total_supply_near=value))
        parsed = checker.read_table(self.directory, "supply")
        actual = parsed[checker.BASELINE]["closing_total_supply_near"]
        self.assertIsInstance(actual, Decimal)
        self.assertEqual(actual, Decimal(value))

    def test_counts_are_exact_integers_not_tolerance_comparisons(self):
        for value in ("141802.000001", "141803", "-1"):
            with self.subTest(value=value):
                self.edit("movements", lambda fields, rows: rows[0].update(block_records=value))
                with self.assertRaisesRegex(ValueError, "integer count|block counts disagree"):
                    checker.audit(self.directory)
                self.restore("movements")

    def test_nonzero_coverage_diagnostics_and_unmatched_records(self):
        cases = [
            ("supply", "missing_block_hashes", "1"),
            ("validators", "comparison_check", "NO_PREVIOUS_RECORD_IN_LOOKUP"),
            ("movements", "comparison_check", "PREVIOUS_HASH_MISMATCH"),
            ("receipts", "invalid_token_cost_values", "1"),
            ("conversions", "missing_cost_records", "1"),
        ]
        for key, field, value in cases:
            with self.subTest(source=key, field=field):
                self.edit(key, lambda fields, rows: rows[0].update({field: value}))
                with self.assertRaisesRegex(ValueError, "diagnostic|unmatched"):
                    checker.audit(self.directory)
                self.restore(key)

    def test_broken_arithmetic_identities(self):
        cases = [
            ("movements", "observed_positive_supply_movements_near"),
            ("movements", "net_observed_supply_change_near"),
            ("validators", "raw_matched_balance_change_near"),
            ("receipts", "average_recorded_cost_per_receipt_near"),
            ("conversions", "recorded_conversion_cost_per_transaction_near"),
            ("economic", "net_supply_change_minus_validator_change_near"),
            ("spending", "combined_recorded_execution_spending_near"),
        ]
        for key, field in cases:
            with self.subTest(source=key, field=field):
                def break_identity(fields, rows):
                    rows[0][field] = str(Decimal(rows[0][field]) + 1)
                self.edit(key, break_identity)
                with self.assertRaisesRegex(ValueError, "arithmetic discrepancy"):
                    checker.audit(self.directory)
                self.restore(key)

    def test_missing_daily_number_is_not_zero_filled(self):
        self.edit("supply", lambda fields, rows: rows[1].update(observed_daily_supply_change_near="null"))
        with self.assertRaisesRegex(ValueError, "missing daily comparison"):
            checker.audit(self.directory)

    def test_movement_parts_must_agree_directly_with_block_net(self):
        # Both can separately be within tolerance of endpoints while disagreeing
        # with each other by more than tolerance. Check this identity directly.
        def change_parts(fields, rows):
            offset = checker.TOLERANCE * Decimal("0.75")
            row = rows[0]
            row["net_observed_supply_change_near"] = str(
                Decimal(row["net_observed_supply_change_near"]) + offset)
            row["observed_positive_supply_movements_near"] = str(
                Decimal(row["observed_positive_supply_movements_near"]) - offset)
        self.edit("movements", change_parts)
        with self.assertRaisesRegex(ValueError, "positive minus decrease vs block net"):
            checker.audit(self.directory)

    def test_arithmetic_pass_preserves_unexplained_residual_and_unavailable_flows(self):
        report = checker.audit(self.directory)
        self.assertEqual(len(report["daily"]), 56)
        self.assertEqual(len(report["weekly"]), 8)
        self.assertEqual(report["totals"]["residual"], Decimal("16599.51437846169"))
        self.assertGreater(abs(report["totals"]["residual"]), checker.TOLERANCE)
        self.assertTrue(all(abs(value) <= checker.TOLERANCE for _, value in report["discrepancies"]))
        self.assertIsNone(report["independent_issuance"])
        self.assertIsNone(report["actual_burn"])
        largest = max(report["daily"], key=lambda row: abs(row["residual"]))
        self.assertEqual(str(largest["start"]), "2026-09-23")
        self.assertEqual(largest["residual"], Decimal("11427.31386968814"))
        self.assertEqual(report["totals"]["combined_spending"], Decimal("67988.90517751203043"))
        output = io.StringIO()
        checker.print_report(report, output)
        text = output.getvalue()
        self.assertIn("Saved arithmetic consistency: PASS", text)
        self.assertIn("it remains unexplained", text)
        self.assertIn("unavailable (neither is zero)", text)
        self.assertIn("Largest daily residual: 2026-09-23: 11427.31386968814 NEAR", text)
        self.assertIn("Daily spending: unavailable", text)

    def test_prior_report_is_checked_not_substituted(self):
        previous = checker.PREVIOUSLY_REPORTED_RESIDUAL
        try:
            checker.PREVIOUSLY_REPORTED_RESIDUAL = previous + 1
            with self.assertRaisesRegex(ValueError, "computed period residual vs previously reported"):
                checker.audit(self.directory)
        finally:
            checker.PREVIOUSLY_REPORTED_RESIDUAL = previous

    def test_cli_is_read_only_and_prints_to_stdout(self):
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        result = subprocess.run(
            [sys.executable, "-B", str(SCRIPT), "--results-dir", str(self.directory)],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("Full-period totals", result.stdout)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.directory.iterdir()})

    def test_cli_returns_failure_for_bad_input(self):
        self.edit("validators", lambda fields, rows: rows.pop())
        error = io.StringIO()
        with redirect_stderr(error):
            status = checker.main(["--results-dir", str(self.directory)])
        self.assertEqual(status, 1)
        self.assertIn("Supply comparison failed", error.getvalue())


if __name__ == "__main__":
    unittest.main()
