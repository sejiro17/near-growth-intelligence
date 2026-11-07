"""Offline regression checks for derived supply and canonical-account evidence."""

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "consolidation", ROOT / "analysis/13_consolidate_supply_evidence.py")
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


class SupplyEvidenceConsolidationTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(summary.capture.http.client, "HTTPSConnection",
                             side_effect=AssertionError("Network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name).resolve()

    def test_comparison_reproduces_result43_without_reading_the_target(self):
        expected = summary.witness.COMPARISON.read_bytes()
        with patch.object(summary.witness, "COMPARISON", self.temporary / "absent.json"):
            actual = summary.capture.json_bytes(summary.comparison_report())
        self.assertEqual(actual, expected)
        report = summary.capture.decode(actual)
        self.assertEqual(report["additional_validator_population"]["update_records_across_AB"], 231)
        self.assertEqual([report["blocks"][x]["counts"]["bq_only_validator_accounts"] for x in "AB"], [0, 0])
        self.assertIn("not established", report["blocks"]["A"]["collision_candidate"]["caution"])
        for block in report["blocks"].values():
            self.assertTrue(all(x["monetary_change"] is None
                                for x in block["rpc_only_validator_post_states"]))

    def test_changed_or_outside_inputs_rejected(self):
        path = self.temporary / "input.json"
        path.write_bytes(b"original")
        inputs = {"input.json": {"sha256": summary.capture.sha256(b"original"), "bytes": 8}}
        with patch.object(summary, "ROOT", self.temporary):
            summary.verify_inputs(inputs)
            path.write_bytes(b"changed!")
            with self.assertRaisesRegex(ValueError, "hash/length mismatch"):
                summary.verify_inputs(inputs)
            with self.assertRaisesRegex(ValueError, "outside repository"):
                summary.verify_inputs({"../other.json": inputs["input.json"]})

    def test_binary64_reconstruction_ties_and_invalid_values(self):
        from fractions import Fraction
        self.assertEqual(summary.binary64("9007199254740993")[0], Fraction(9007199254740992))
        self.assertEqual(summary.binary64("9007199254740995")[0], Fraction(9007199254740996))
        self.assertEqual(summary.binary64("0")[0], Fraction(0))
        for value in ("NaN", "Infinity", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summary.binary64(value)

    def test_saved_positive_and_validator_event_height_hash_sets_match(self):
        parents, audits, _ = summary.result42(summary.capture.DIAGNOSTIC.read_bytes())
        positive = {(int(row["block_height"]), block_hash) for block_hash, row in parents.items()
                    if row.get("positive_supply_movement") == "true"}
        validators = {(int(row["block_height"]), block_hash) for block_hash, row in parents.items()
                      if block_hash and int(row["observed_validator_update_records"]) > 0}
        self.assertEqual(positive, validators)
        self.assertEqual(len(positive), 3)
        self.assertEqual(sum(len(x) for x in audits.values()), 1154)

    def test_witness_exact_integer_arithmetic_and_provenance(self):
        report = summary.witness_report()
        before, after = report["parent"], report["post"]
        expected = int(after["amount_yocto"]) + int(after["locked_yocto"]) - int(before["amount_yocto"]) - int(before["locked_yocto"])
        self.assertEqual(str(expected), report["change"]["combined_yocto"])
        self.assertEqual(expected, 1128147246190549662124317432)
        self.assertEqual(report["change"]["combined_near"], "1128.147246190549662124317432")
        self.assertEqual(report["change"]["liquid_yocto"], "0")
        self.assertEqual(after["block_height"], before["block_height"] + 1)
        self.assertEqual(after["cause"]["type"], "validator_accounts_update")
        self.assertGreaterEqual(len(report["source_hashes"]), 40)
        summary.verify_inputs(report["source_hashes"])
        self.assertIsNone(report["independently_measured_issuance_near"])
        self.assertIsNone(report["independently_measured_actual_burn_near"])

    def test_near_formatting_does_not_round_even_in_low_decimal_precision(self):
        with localcontext() as context:
            context.prec = 3
            self.assertEqual(summary.near_integer(1128147246190549662124317432),
                             "1128.147246190549662124317432")
            self.assertEqual(summary.near_integer(-1), "-0.000000000000000000000001")

    def test_supply_coverage_cancellation_and_unavailable_components(self):
        report = summary.supply_report()
        self.assertEqual(len(report["weekly"]), 8)
        self.assertEqual(len(report["daily"]), 56)
        with localcontext() as context:
            context.prec = 50
            weekly = report["weekly"]
            for i, value in enumerate(weekly):
                start = date(2026, 8, 24) + timedelta(days=7 * i)
                self.assertEqual(value["start"], str(start))
                self.assertEqual(value["end"], str(start + timedelta(days=6)))
                if i:
                    self.assertEqual(value["opening_supply_near"], weekly[i - 1]["closing_supply_near"])
            daily_abs = sum(abs(Decimal(x["residual_near"])) for x in report["daily"])
            daily_signed = sum(Decimal(x["residual_near"]) for x in report["daily"])
            weekly_abs = sum(abs(Decimal(x["residual_near"])) for x in weekly)
            self.assertEqual(daily_signed, Decimal(report["period"]["residual_near"]))
            self.assertEqual(daily_abs, Decimal(report["cancellation"]["sum_absolute_daily_residuals_near"]))
            self.assertGreater(daily_abs, weekly_abs)
            self.assertGreater(weekly_abs, abs(daily_signed))
            self.assertEqual(daily_abs, Decimal("84284.66902631883"))
            period = report["period"]
            self.assertEqual(Decimal(report["cancellation"]["period_residual_as_pct_of_net_supply_change"]),
                             100 * daily_signed / Decimal(period["net_supply_movement_near"]))
            self.assertEqual(Decimal(report["cancellation"]["period_residual_as_pct_of_opening_supply"]),
                             100 * daily_signed / Decimal(period["opening_supply_near"]))
        for value in report["weekly"] + report["daily"] + [report["period"]]:
            self.assertIsNone(value["independently_measured_issuance_near"])
            self.assertIsNone(value["independently_measured_actual_burn_near"])

    def test_cli_defaults_to_stdout_and_refuses_overwrite(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(summary.capture, "write_new", side_effect=AssertionError("No writes")):
            self.assertEqual(summary.main(["witness"]), 0)
        self.assertEqual(json.loads(output.getvalue())["account_id"], "bitwise_1.poolv1.near")
        path = self.temporary / "comparison.json"
        self.assertEqual(summary.main(["comparison", "--output", str(path)]), 0)
        before = path.read_bytes()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(summary.main(["comparison", "--output", str(path)]), 1)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
