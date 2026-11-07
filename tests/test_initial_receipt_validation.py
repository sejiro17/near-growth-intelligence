"""Offline SQL 42 export validation and bounded SQL 43 scope regressions."""

import copy
import importlib.util
import io
import re
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("initial_receipt", ROOT / "analysis/21_validate_initial_receipt_pilot.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class InitialReceiptTests(unittest.TestCase):
    def records(self):
        return [{**r, "record_json": m.b.decode(r["record_json"])} for r in m.b.decode(m.SOURCE.read_bytes())]

    def encode(self, rows):
        return m.b.json_bytes([{**r, "record_json": m.b.json_bytes(r["record_json"]).decode()} for r in rows])

    def summary(self, rows):
        return next(r["record_json"] for r in rows if r["row_kind"] == "SUMMARY")

    def population(self, rows, pop=m.POPS[0]):
        return next(r["record_json"] for r in rows if r["row_kind"] == "POPULATION" and r["record_json"]["population"] == pop)

    def bucket(self, rows, pop=m.POPS[0]):
        return next(r["record_json"] for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET" and r["record_json"]["population"] == pop)

    def test_saved_evidence_full_coverage_spending_and_overlap(self):
        before = m.SOURCE.read_bytes()
        r = m.report()
        self.assertEqual(r["export_rows"], 51)
        self.assertEqual(r["row_kinds"], {"SUMMARY": 1, "WEEK_CONTROL": 4, "POPULATION": 2, "ASSESSMENT_BUCKET": 44})
        exact, repeated = r["populations"]
        self.assertEqual((exact["observed"]["observed_accounts"], exact["observed"]["transactions"]), (65251, 3528043))
        self.assertEqual((repeated["observed"]["observed_accounts"], repeated["observed"]["transactions"]), (53455, 3475043))
        self.assertEqual((exact["successful_initial_receipts"], exact["failed_initial_receipts"]), (3280589, 247454))
        self.assertEqual(exact["accounts_with_both_success_and_failure"], 1109)
        self.assertEqual(exact["observed"]["recorded_conversion_spending_near"], "163.70758505454832910422016")
        self.assertEqual(exact["observed"]["complete_initial_receipt_spending_near"], "1312.24525168980803277846528")
        self.assertEqual(exact["tail_transactions"], 1)
        self.assertEqual(Decimal(exact["tail_spending_subtotal_near"]), Decimal("0.00064349229576029995008"))
        self.assertEqual(exact["diagnostic_example_occurrences_checked"], 64)
        self.assertTrue(r["result57_reproduction"]["all_recorded_inputs_and_metrics_reproduced"])
        self.assertTrue(r["extension_assessment"]["coverage_supports_bounded_replication"])
        self.assertEqual(m.SOURCE.read_bytes(), before)

    def test_missing_rows_duplicate_buckets_and_nested_schema(self):
        rows = self.records()
        with self.assertRaisesRegex(ValueError, "Incomplete export"):
            m.validate(self.encode(rows[:-1]))
        buckets = [r for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET"]
        buckets[-1]["record_json"] = copy.deepcopy(buckets[0]["record_json"])
        with self.assertRaisesRegex(ValueError, "Duplicate assessment"):
            m.validate(self.encode(rows))
        rows = self.records()
        self.bucket(rows)["unexpected"] = 1
        with self.assertRaisesRegex(ValueError, "nested schema"):
            m.validate(self.encode(rows))

    def test_saved_membership_and_transaction_denominators(self):
        for field, value in (("exact_week_8_accounts", 65252), ("selected_transactions", 3528044),
                             ("repeated_checkpoint_accounts", 53456)):
            with self.subTest(field=field):
                rows = self.records()
                self.summary(rows)[field] = value
                with self.assertRaisesRegex(ValueError, "membership/transaction"):
                    m.validate(self.encode(rows))

    def test_missing_or_duplicate_outcomes_cannot_remain_fully_assessed(self):
        for missing in (True, False):
            rows = self.records()
            s = self.summary(rows)
            if missing:
                s["receipt_ids_with_observed_outcomes"] -= 1
                s["selected_outcome_observations"] -= 1
            else:
                s["receipt_ids_with_multiple_outcomes"] += 1
                s["selected_outcome_observations"] += 1
            with self.subTest(missing=missing), self.assertRaisesRegex(ValueError, "outcome observations"):
                m.validate(self.encode(rows))

    def test_status_dates_tail_and_example_truncation(self):
        mutations = [lambda b: b.update(observed_initial_status="UNKNOWN"),
                     lambda b: b.update(execution_week="2026-10-19"),
                     lambda b: b.update(partial_tail_transactions=1),
                     lambda b: b["diagnostic_examples"].pop(),
                     lambda b: b["diagnostic_examples"][0].update(execution_time="2026-10-24T00:00:00Z")]
        for mutate in mutations:
            rows = self.records()
            mutate(self.bucket(rows))
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                m.validate(self.encode(rows))

    def test_reported_zero_hash_disagreements_checked_against_examples(self):
        rows = self.records()
        examples = self.bucket(rows)["diagnostic_examples"]
        examples[0]["executed_in_block_hash"] = examples[1]["executed_in_block_hash"]
        with self.assertRaisesRegex(ValueError, "hash-time disagreement|sample identity disagreement"):
            m.validate(self.encode(rows))

    def test_nonfinite_amount_and_filled_unavailable_amount_rejected(self):
        for value in ("NaN", "Infinity", None):
            rows = self.records()
            self.bucket(rows)["valid_assessed_initial_spending_subtotal_near"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validate(self.encode(rows))

    def test_internal_arithmetic_discrepancy_below_baseline_screen_is_rejected(self):
        rows = self.records()
        p = self.population(rows)
        with localcontext() as ctx:
            ctx.prec = 80
            p["complete_initial_receipt_spending_near"] = str(Decimal(p["complete_initial_receipt_spending_near"])+Decimal("0.000001"))
        with self.assertRaisesRegex(ValueError, "Monetary arithmetic discrepancy"):
            m.validate(self.encode(rows))

    def test_missing_cost_preserves_null_complete_total_and_disables_replication_claim(self):
        rows = self.records()
        for pop in m.POPS:
            tail = next(r["record_json"] for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET"
                        and r["record_json"]["population"] == pop and r["record_json"]["execution_date"] == "2026-10-19")
            old = tail["valid_assessed_initial_spending_subtotal_near"]
            tail.update(cost_check="MISSING_COST", valid_initial_cost_transactions=0, valid_assessed_initial_spending_subtotal_near=None)
            p = self.population(rows, pop)
            p["valid_initial_cost_transactions"] -= 1
            p["invalid_assessed_cost_rows"] += 1
            p["complete_initial_receipt_spending_near"] = None
            with localcontext() as ctx:
                ctx.prec = 80
                p["valid_assessed_initial_spending_subtotal_near"] = str(Decimal(p["valid_assessed_initial_spending_subtotal_near"])-Decimal(old))
        r = m.validate(self.encode(rows))
        self.assertFalse(r["extension_assessment"]["coverage_supports_bounded_replication"])
        for pop in r["populations"]:
            self.assertIsNone(pop["observed"]["complete_initial_receipt_spending_near"])
            self.assertIsNone(pop["tail_spending_subtotal_near"])

    def test_duplicate_outcome_is_excluded_and_never_arbitrarily_costed(self):
        rows = self.records()
        summary = self.summary(rows)
        summary["receipt_ids_with_multiple_outcomes"] = 1
        summary["selected_outcome_observations"] += 1
        for pop in m.POPS:
            tail = next(r["record_json"] for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET"
                        and r["record_json"]["population"] == pop and r["record_json"]["execution_date"] == "2026-10-19")
            old = tail["valid_assessed_initial_spending_subtotal_near"]
            tail.update(assessment="MULTIPLE_OUTCOME_OBSERVATIONS", observed_initial_status="UNAVAILABLE_OR_OTHER",
                        cost_check="UNASSESSED_LINK_OR_EXECUTION", execution_date=None, execution_week=None,
                        matched_outcome_observations=2, valid_initial_cost_transactions=0, partial_tail_transactions=0,
                        valid_assessed_initial_spending_subtotal_near=None)
            for example in tail["diagnostic_examples"]:
                for field in m.EXAMPLE_SCHEMA - {"transaction_hash", "converted_into_receipt_id"}:
                    example[field] = None
            p = self.population(rows, pop)
            p["assessed_initial_receipts"] -= 1
            p["unassessed_initial_receipts"] += 1
            p["valid_initial_cost_transactions"] -= 1
            p["complete_initial_receipt_spending_near"] = None
            with localcontext() as ctx:
                ctx.prec = 80
                p["valid_assessed_initial_spending_subtotal_near"] = str(Decimal(p["valid_assessed_initial_spending_subtotal_near"])-Decimal(old))
        r = m.validate(self.encode(rows))
        for pop in r["populations"]:
            self.assertEqual(pop["exclusion_counts"]["MULTIPLE_OUTCOME_OBSERVATIONS"], 1)
            self.assertIsNone(pop["observed"]["complete_initial_receipt_spending_near"])

    def test_replication_sql_sources_filters_membership_and_dependencies(self):
        code = re.sub(r'/\*.*?\*/', '', m.EXTENSION.read_text(), flags=re.S)
        for table in ("transactions", "execution_outcomes", "blocks"):
            self.assertEqual(code.count(f'`bigquery-public-data.crypto_near_mainnet_us.{table}`'), 1)
        self.assertIn("WHERE t.block_date BETWEEN DATE '2026-08-10' AND DATE '2026-08-23'", code)
        self.assertIn("WHERE o.block_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-17'", code)
        self.assertIn("WHERE block_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-17'", code)
        self.assertIn('WHERE n.outcome_rows = 1', code)
        self.assertIn('WHERE n.block_rows = 1', code)
        self.assertIn('WHERE at_1 AND at_4 AND at_8', code)
        self.assertIn("'AUG10_REPEATED_CHECKPOINTS'", code)
        self.assertNotIn('SEP28_REPEATED', code)
        self.assertNotIn('transaction_actions', code)
        self.assertNotIn('ANY_VALUE', code)
        self.assertNotIn('ROW_NUMBER', code)
        self.assertIn('p.valid_initial_cost_transactions = p.transactions', code)
        definitions = re.findall(r'^(?:WITH )?([a-z_]+) AS \(', code, re.M)
        self.assertEqual(len(definitions), len(set(definitions)))
        references = re.findall(r'\b(?:FROM|JOIN) ([a-z_]+)\b', code)
        self.assertTrue(set(references) <= set(definitions), set(references)-set(definitions))
        self.assertIn('outcome_partition', definitions)
        self.assertIn('unique_blocks', definitions)

    def test_stdout_exclusive_output_and_raw_preservation(self):
        raw = m.SOURCE.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'validation.json'
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(m.main(['--output', str(output)]), 0)
                first = output.read_bytes()
                self.assertEqual(m.main(['--output', str(output)]), 1)
            self.assertEqual(output.read_bytes(), first)
        self.assertEqual(m.SOURCE.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
