"""Population alignment, coverage suppression and sharp integer bounds."""

import copy
import importlib.util
import itertools
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("execution_bounds", ROOT/"analysis/48_returner_execution_bounds.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class ReturnerBoundsTests(unittest.TestCase):
    def inputs(self):
        checkpoints = m.b.decode(m.path(57).read_bytes())["checkpoint_metrics"]
        cp = next(p for p in checkpoints if p["cohort_week"] == "2026-08-10" and p["week_offset"] == 8)
        source = m.b.decode(m.path(61).read_bytes())
        pop = next(p for p in source["populations"] if p["population"] == "AUG10_EXACT_WEEK8")
        return copy.deepcopy(cp), copy.deepcopy(pop), copy.deepcopy(source["source_summary"])

    def compare(self, *args, verified=True):
        return m.compare(*args, definitions_verified=verified, expected_population="AUG10_EXACT_WEEK8")

    def test_population_alignment_and_exact_denominators(self):
        row = self.compare(*self.inputs())
        self.assertEqual(row["status"], "AVAILABLE_OBSERVED_INITIAL_RECEIPT_BOUNDS")
        self.assertEqual(row["bounds"]["outside_success_fraction_lower"], {"numerator": 686154, "denominator": 1011853})
        self.assertEqual(row["bounds"]["successful_initial_receipts_outside_top10_upper"], 1011853)
        self.assertTrue(row["one_assessed_initial_receipt_per_transaction"])

    def test_definition_membership_week_and_transaction_mismatches_suppress(self):
        mutations = [(0, "cohort_week", "2026-08-17"), (0, "followup_complete", False),
                     (0, "measurement_available", None), (0, "week_offset", 8.0),
                     (1, "population", "AUG10_REPEATED_CHECKPOINTS"),
                     (2, "submission_week", "2026-10-12"), (2, "submission_week_end", "2026-10-12")]
        for index, key, value in mutations:
            args = self.inputs()
            args[index][key] = value
            with self.subTest(key=key):
                row = self.compare(*args)
                self.assertIsNone(row["bounds"])
                self.assertEqual(row["status"], "UNAVAILABLE")
        for key, value in [("return_definition", "ANY_RETURN"), ("submission_week", "2026-10-12"),
                           ("expected_accounts", 1), ("expected_transactions", 1),
                           ("distinct_transaction_hashes", 1), ("group_matches_result56", False)]:
            cp, pop, summary = self.inputs()
            pop["observed"][key] = value
            with self.subTest(key=key):
                self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        self.assertIsNone(self.compare(*self.inputs(), verified=False)["bounds"])

    def test_missing_or_ambiguous_receipts_suppress(self):
        for key, value in [("assessed_initial_receipts", 1), ("unassessed_initial_receipts", 1),
                           ("lookup_days_observed", False)]:
            cp, pop, summary = self.inputs()
            pop["observed"][key] = value
            self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        for key in ["receipt_ids_with_multiple_outcomes", "selected_distinct_receipt_ids", "selected_outcome_observations"]:
            cp, pop, summary = self.inputs()
            summary[key] += 1
            self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        for reason in m.EXCLUSIONS:
            cp, pop, summary = self.inputs()
            pop["exclusion_counts"][reason] = 1
            self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        cp, pop, summary = self.inputs()
        del pop["exclusion_counts"]["SHARED_INITIAL_RECEIPT_ID"]
        self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        self.assertIsNone(self.compare(None, None, None)["bounds"])

    def test_status_buckets_must_reconcile(self):
        cp, pop, summary = self.inputs()
        pop["by_status"].append(copy.deepcopy(pop["by_status"][0]))
        self.assertIsNone(self.compare(cp, pop, summary)["bounds"])
        cp, pop, summary = self.inputs()
        pop["successful_initial_receipts"] += 1
        self.assertIsNone(self.compare(cp, pop, summary)["bounds"])

    def test_bounds_are_sharp_for_all_small_populations(self):
        for n in range(13):
            for top, success in itertools.product(range(n+1), repeat=2):
                possible = [outside for outside in range(n-top+1) if 0 <= success-outside <= top]
                result = m.bounds(n, top, success)
                self.assertEqual(result["successful_initial_receipts_outside_top10_lower"], min(possible))
                self.assertEqual(result["successful_initial_receipts_outside_top10_upper"], max(possible))

    def test_display_rounds_outward_and_zero_denominator_is_unavailable(self):
        self.assertEqual(m.display_pct(1, 3), "33.33")
        self.assertEqual(m.display_pct(1, 3, upper=True), "33.34")
        self.assertEqual(m.display_pct(2, 3), "66.66")
        self.assertEqual(m.display_pct(2, 3, upper=True), "66.67")
        self.assertIsNone(m.display_pct(0, 0))
        result = m.bounds(10, 10, 4)
        self.assertEqual(result["successful_initial_receipts_outside_top10_lower"], 0)
        self.assertEqual(result["successful_initial_receipts_outside_top10_upper"], 0)
        self.assertIsNone(result["outside_initial_success_pct_lower_display"])

    def test_invalid_counts_never_become_zero(self):
        for bad in (None, True, "1", 1.0, -1, float("nan"), float("inf")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m.bounds(10, bad, 1)
        for args in [(10, 11, 1), (10, 1, 11)]:
            with self.assertRaises(ValueError):
                m.bounds(*args)

    def test_saved_report_reproduces_offline_and_keeps_cohorts_separate(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No collection")):
            result = m.report()
        self.assertEqual(m.b.json_bytes(result), m.OUTPUT.read_bytes())
        self.assertEqual([r["cohort_week"] for r in result["populations"]], ["2026-08-10", "2026-08-17"])
        self.assertEqual([r["bounds"]["successful_initial_receipts_outside_top10_lower"] for r in result["populations"]], [686154, 630408])


if __name__ == "__main__":
    unittest.main()
