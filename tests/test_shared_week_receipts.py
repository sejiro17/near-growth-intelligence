"""Saved shared-week arithmetic, overlap and coverage regression checks."""
import copy
import importlib.util
import unittest
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shared", ROOT / "analysis/22_validate_shared_week_receipts.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SharedWeekTests(unittest.TestCase):
    def records(self):
        return [{**r, "record_json": m.b.decode(r["record_json"])} for r in m.b.decode(m.SOURCE.read_bytes())]

    def encode(self, rows):
        return m.b.json_bytes([{**r, "record_json": m.b.json_bytes(r["record_json"]).decode()} for r in rows])

    def test_saved_controls_overlap_and_scope(self):
        r = m.report()
        self.assertEqual(r["export_rows"], 75)
        self.assertTrue(r["publication_ready"])
        self.assertEqual(r["overlap"]["august_and_september_accounts"], 58957)
        self.assertEqual(r["overlap"]["august_and_september_transactions"], 3871009)
        self.assertIsNone(r["overlap"]["union_or_intersection_receipt_spending_near"])
        self.assertEqual([p["failed_initial_receipts"] for p in r["populations"]], [325699, 324904, 913574])
        self.assertEqual([p["tail_transactions"] for p in r["populations"]], [1, 1, 1])
        self.assertIsNone(r["populations"][1]["observed"]["expected_transactions"])
        self.assertIsNone(r["unavailable"]["actual_native_burn_near"])

    def test_missing_or_duplicate_rows_and_changed_membership(self):
        rows = self.records()
        with self.assertRaisesRegex(ValueError, "Incomplete export"):
            m.validate(self.encode(rows[:-1]))
        buckets = [r for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET"]
        buckets[-1]["record_json"] = copy.deepcopy(buckets[0]["record_json"])
        with self.assertRaisesRegex(ValueError, "Duplicate assessment"):
            m.validate(self.encode(rows))
        rows = self.records()
        next(r["record_json"] for r in rows if r["row_kind"] == "POPULATION")["observed_accounts"] += 1
        with self.assertRaisesRegex(ValueError, "membership"):
            m.validate(self.encode(rows))

    def test_duplicate_global_outcomes_cannot_remain_assessed(self):
        rows = self.records()
        s = next(r["record_json"] for r in rows if r["row_kind"] == "SUMMARY")
        s["receipt_ids_with_multiple_outcomes"] = 1
        s["selected_outcome_observations"] += 1
        with self.assertRaisesRegex(ValueError, "contradict union"):
            m.validate(self.encode(rows))

    def test_timestamps_status_nonfinite_and_internal_cost_discrepancies(self):
        for field, value in (("execution_week", "2026-10-12"), ("observed_initial_status", "UNKNOWN"),
                             ("valid_assessed_initial_spending_subtotal_near", "NaN")):
            rows = self.records()
            r = next(r["record_json"] for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET")
            r[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.validate(self.encode(rows))
        rows = self.records()
        r = next(r["record_json"] for r in rows if r["row_kind"] == "POPULATION")
        with localcontext() as c:
            c.prec = 80
            r["complete_initial_receipt_spending_near"] = str(Decimal(r["complete_initial_receipt_spending_near"])+Decimal("0.000001"))
        with self.assertRaisesRegex(ValueError, "Monetary arithmetic"):
            m.validate(self.encode(rows))

    def test_missing_cost_keeps_total_null_and_blocks_publication_claim(self):
        rows = self.records()
        for pop in m.POPS:
            tail = next(r["record_json"] for r in rows if r["row_kind"] == "ASSESSMENT_BUCKET"
                        and r["record_json"]["population"] == pop and r["record_json"]["execution_date"] == "2026-10-12")
            old = tail["valid_assessed_initial_spending_subtotal_near"]
            tail.update(cost_check="MISSING_COST", valid_initial_cost_transactions=0, valid_assessed_initial_spending_subtotal_near=None)
            p = next(r["record_json"] for r in rows if r["row_kind"] == "POPULATION" and r["record_json"]["population"] == pop)
            p["valid_initial_cost_transactions"] -= 1
            p["invalid_assessed_cost_rows"] += 1
            p["complete_initial_receipt_spending_near"] = None
            with localcontext() as c:
                c.prec = 80
                p["valid_assessed_initial_spending_subtotal_near"] = str(Decimal(p["valid_assessed_initial_spending_subtotal_near"])-Decimal(old))
        r = m.validate(self.encode(rows))
        self.assertFalse(r["publication_ready"])
        self.assertTrue(all(p["observed"]["complete_initial_receipt_spending_near"] is None for p in r["populations"]))


if __name__ == "__main__":
    unittest.main()
