"""Affected formula, sensitivity, preservation and bounded-plan checks."""

import copy
import importlib.util
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

from dashboard import conditional_model as m, model_review as review

ROOT=Path(__file__).resolve().parents[1]


class ModelReviewTests(unittest.TestCase):
    def setUp(self):
        self.values=m.decode(m.CONFIG.read_bytes())["assumptions"]
        self.guard=patch("socket.socket.connect",side_effect=AssertionError("Source requests forbidden"))
        self.guard.start();self.addCleanup(self.guard.stop)

    def test_exact_default_formula_walkthrough_units_and_original_preservation(self):
        before=m.ARTIFACT.read_bytes();r=review.evaluate(self.values)
        expected=("618436.074970164323861118656646","3092180.374850821619305593283230","12368721.49940328647722237313292","24737442.99880657295444474626584","24737442998.80657295444474626584")
        self.assertEqual([Decimal(x["Value"]) for x in r["walkthrough"]],[Decimal(x) for x in expected])
        self.assertEqual([x["Unit"] for x in r["walkthrough"]],["NEAR/week"]+["USD/week"]*4)
        self.assertEqual(Decimal(r["formula_comparison_discrepancy_usd_per_week"]),0)
        self.assertIn("not independently measured total issuance",r["target_scope"])
        m.verify_saved();self.assertEqual(m.ARTIFACT.read_bytes(),before)

    def test_threshold_sensitivity_to_each_direct_driver(self):
        base=Decimal(review.evaluate(self.values)["walkthrough"][-1]["Value"])
        with localcontext() as context:
            context.prec=80
            for key in ("reward_mint_near_per_week","price_usd_per_near","fee_rate","capture_fraction","destruction_allocation"):
                values=dict(self.values);values[key]=format(Decimal(values[key])*2,"f")
                target=Decimal(review.evaluate(values)["walkthrough"][-1]["Value"])
                self.assertEqual(target,base*2 if key in {"reward_mint_near_per_week","price_usd_per_near"} else base/2)

    def test_volume_custody_hurdle_and_horizon_do_not_set_reward_only_weekly_threshold(self):
        base=review.evaluate(self.values)["direct_formula_threshold"]
        for key,value in (("eligible_activity_usd_per_week","200000000"),("custody_allocation","0.5"),("retained_budget_hurdle_usd_per_week","500"),("horizon_weeks","8")):
            values=dict(self.values);values[key]=value
            self.assertEqual(review.evaluate(values)["direct_formula_threshold"],base)
        values=dict(self.values);values["horizon_weeks"]="8"
        self.assertEqual(Decimal(m.calculate(values)["horizon_totals"]["purchased_and_destroyed_near"]),20000)

    def test_zero_capture_fee_or_destruction_is_unreachable_not_observed_zero(self):
        for key in ("capture_fraction","fee_rate","destruction_allocation"):
            values=dict(self.values);values[key]="0";result=review.evaluate(values)
            self.assertIsNone(result["walkthrough"][-1]["Value"])
            self.assertEqual(result["direct_formula_threshold"]["status"],"UNREACHABLE_WITH_ZERO_COEFFICIENT")
        values=dict(self.values);values.update(reward_mint_near_per_week="0",capture_fraction="0",fee_rate="0",destruction_allocation="0")
        self.assertEqual(review.evaluate(values)["walkthrough"][-1]["Value"],"0")

    def test_tiny_overallocation_is_rejected_without_rounding_into_feasible_range(self):
        values=dict(self.values);values.update(destruction_allocation="1",custody_allocation="0."+"0"*85+"1")
        with self.assertRaisesRegex(ValueError,"Allocations exceed"):review.calculate(values)

    def test_major_assumptions_all_covered_and_missing_supply_stays_explicit(self):
        before=copy.deepcopy(self.values);cases=review.sensitivity(self.values)
        changed={x["changed_assumption"] for x in cases}
        self.assertEqual(changed-{None},set(m.FIELDS))
        self.assertEqual(self.values,before)
        self.assertIsNone(cases[0]["thresholds"]["full_supply_neutral_activity_threshold"]["value"])
        explicit=next(x for x in cases if x["scenario"]=="Explicit missing supply terms = 0")
        self.assertTrue(all(explicit["assumptions"][key]=="0" for key in m.OPTIONAL))
        self.assertIsNotNone(explicit["thresholds"]["full_supply_neutral_activity_threshold"]["value"])
        self.assertTrue(all("HYPOTHETICAL" in x["qualification"] for x in cases))

    def test_extreme_accepted_price_does_not_crash_sensitivity(self):
        values=dict(self.values);values["price_usd_per_near"]="1000000000000000000000000"
        self.assertTrue(review.sensitivity(values))

    def test_bounded_attribution_plan_uses_saved_receipt_and_two_requests_only(self):
        spec=importlib.util.spec_from_file_location("review_builder",ROOT/"analysis/39_review_model_and_attribution.py")
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        r=builder.attribution()
        self.assertEqual(r["selected_signers"],51)
        self.assertEqual(r["leaders"][0]["account_id"],"sweat-relayer.near")
        self.assertEqual(r["leaders"][0]["transactions"],13704363)
        self.assertEqual(r["leaders"][0]["delegate_action_transactions"],13246938)
        self.assertEqual(r["target"]["receipt_receiver_id"],"claim.sweat")
        self.assertNotEqual(r["target"]["original_signer_id"],r["target"]["receipt_predecessor_id"])
        self.assertEqual(r["target"]["decoded_args_utf8"],"{}")
        self.assertIsNone(r["target"]["execution_outcome_in_saved_block"])
        self.assertIsNone(r["target"]["originating_transaction_hash"])
        self.assertEqual(r["proposed_sequence"]["maximum_new_requests"],2)
        self.assertFalse(r["proposed_sequence"]["execution_authorized"])
        self.assertEqual(r["proposed_sequence"]["first"]["method"],"EXPERIMENTAL_receipt_to_tx")
        self.assertEqual(r["proposed_sequence"]["second_template"]["method"],"EXPERIMENTAL_tx_status")
        self.assertEqual(len(r["downstream_coverage"]["failure_controls"]),18)
        self.assertEqual(r["source_requests"],0)


if __name__=="__main__":unittest.main()
