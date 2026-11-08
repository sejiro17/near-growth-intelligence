"""Meaningful accounting, availability, sensitivity and offline rebuild checks."""

import copy
import importlib.util
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from unittest.mock import patch

from dashboard import conditional_model as m

ROOT=Path(__file__).resolve().parents[1]


class ConditionalModelTests(unittest.TestCase):
    def setUp(self):
        self.values=m.decode(m.CONFIG.read_bytes())["assumptions"]
        self.guard=patch("socket.socket.connect",side_effect=AssertionError("Source requests forbidden"))
        self.guard.start();self.addCleanup(self.guard.stop)

    def complete_supply(self):
        self.values.update(additional_issuance_near_per_week="0",other_destruction_near_per_week="0",other_supply_adjustment_near_per_week="0")

    def test_dated_baseline_remains_exact_and_missing_economics_never_filled(self):
        evidence=m.evidence();reward=evidence["reward_baseline"]
        self.assertEqual(reward["week"],"2026-09-21/2026-09-27")
        self.assertEqual(reward["reward_mint_yocto"],"618436074970164323861118656646")
        self.assertEqual(reward["reward_mint_near"],"618436.074970164323861118656646")
        self.assertTrue(all(x is None for x in evidence["measured_unavailable"].values()))
        scenario=m.calculate(self.values)
        self.assertEqual(Decimal(scenario["weekly"]["captured_fee_revenue_usd_per_week"]),50000)
        self.assertIsNone(evidence["measured_unavailable"]["attributed_product_revenue_usd"])
        self.assertEqual(evidence["neardata"]["validated_blocks"],144)
        self.assertEqual(evidence["neardata"]["observed_error_blocks_per_minute"],30)
        self.assertIn("NONE",evidence["neardata"]["sample_extrapolation"])

    def test_one_funding_budget_and_three_distinct_outputs(self):
        r=m.calculate(self.values);w=r["weekly"]
        self.assertEqual(Decimal(w["purchased_and_destroyed_near_per_week"]),2500)
        self.assertEqual(Decimal(w["purchased_and_held_near_per_week"]),2500)
        allocated=sum(Decimal(w[k]) for k in ("purchase_and_destruction_budget_usd_per_week","custody_purchase_budget_usd_per_week","retained_budget_before_operating_costs_usd_per_week"))
        self.assertEqual(allocated,Decimal(w["captured_fee_revenue_usd_per_week"]))
        self.assertIsNone(w["conditional_supply_change_near_per_week"])
        self.assertIsNone(r["thresholds"]["full_supply_neutral_activity_threshold"]["value"])

    def test_custody_purchases_do_not_reduce_supply_and_unknown_is_not_zero(self):
        self.complete_supply();self.values["reward_mint_near_per_week"]="100"
        before=m.calculate(self.values)
        self.values["custody_allocation"]="0.5"
        after=m.calculate(self.values)
        self.assertEqual(before["weekly"]["conditional_supply_change_near_per_week"],after["weekly"]["conditional_supply_change_near_per_week"])
        self.assertNotEqual(before["weekly"]["purchased_and_held_near_per_week"],after["weekly"]["purchased_and_held_near_per_week"])
        self.assertEqual(Decimal(after["weekly"]["conditional_supply_change_near_per_week"]),Decimal(-2400))
        self.values["additional_issuance_near_per_week"]=None
        self.assertIsNone(m.calculate(self.values)["weekly"]["conditional_supply_change_near_per_week"])

    def test_zero_capture_or_allocation_is_unreachable_not_a_zero_threshold(self):
        for key in ("capture_fraction","fee_rate","destruction_allocation"):
            values=dict(self.values);values[key]="0"
            r=m.calculate(values)
            self.assertEqual(r["thresholds"]["reward_only_activity_threshold"]["status"],"UNREACHABLE_WITH_ZERO_COEFFICIENT")
            self.assertIsNone(r["thresholds"]["reward_only_activity_threshold"]["value"])
            self.assertEqual(Decimal(r["weekly"]["purchased_and_destroyed_near_per_week"]),0)
        self.values.update(destruction_allocation="0.5",custody_allocation="0.5")
        self.assertEqual(m.calculate(self.values)["thresholds"]["retained_budget_activity_threshold"]["status"],"UNREACHABLE_WITH_ZERO_COEFFICIENT")

    def test_break_even_threshold_reproduces_target_and_capture_infeasibility(self):
        self.values["reward_mint_near_per_week"]="100"
        r=m.calculate(self.values)
        target=r["thresholds"]["reward_only_activity_threshold"]["value"]
        self.values["eligible_activity_usd_per_week"]=target
        self.assertEqual(Decimal(m.calculate(self.values)["weekly"]["purchased_and_destroyed_near_per_week"]),100)
        self.values["eligible_activity_usd_per_week"]="1"
        threshold=m.calculate(self.values)["thresholds"]["reward_only_capture_threshold"]
        self.assertEqual(threshold["status"],"EXCEEDS_FEASIBLE_FRACTION")
        self.assertGreater(Decimal(threshold["value"]),1)

    def test_price_sensitivity_and_horizon_are_scenarios_not_annualized_observations(self):
        original=m.calculate(self.values)
        self.values.update(price_usd_per_near="10",horizon_weeks="4")
        changed=m.calculate(self.values)
        self.assertEqual(Decimal(original["weekly"]["purchased_and_destroyed_near_per_week"])/2,Decimal(changed["weekly"]["purchased_and_destroyed_near_per_week"]))
        self.assertEqual(original["weekly"]["captured_fee_revenue_usd_per_week"],changed["weekly"]["captured_fee_revenue_usd_per_week"])
        self.assertEqual(Decimal(changed["horizon_totals"]["purchased_and_held_near"]),5000)
        with localcontext() as context:
            context.prec=80
            self.assertEqual(Decimal(changed["thresholds"]["reward_only_activity_threshold"]["value"]),2*Decimal(original["thresholds"]["reward_only_activity_threshold"]["value"]))

    def test_rejects_nonfinite_float_negative_prices_bad_horizons_and_double_allocation(self):
        for value in ("NaN","Infinity","-Infinity",5.0,True,"1e3","1,000"):
            candidate=dict(self.values);candidate["price_usd_per_near"]=value
            with self.subTest(value=value),self.assertRaises(ValueError):m.calculate(candidate)
        for field,value in (("price_usd_per_near","0"),("fee_rate","1.1"),("capture_fraction","-0.1"),("horizon_weeks","1.5"),("horizon_weeks","0"),("horizon_weeks","521"),("additional_issuance_near_per_week","-1")):
            candidate=dict(self.values);candidate[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):m.calculate(candidate)
        self.values.update(destruction_allocation="0.9",custody_allocation="0.2")
        with self.assertRaisesRegex(ValueError,"Allocations exceed"):m.calculate(self.values)
        self.values.update(destruction_allocation="1",custody_allocation="0.000000000000000000000000000000000000000000000000000000001")
        with self.assertRaisesRegex(ValueError,"Allocations exceed"):m.calculate(self.values)
        with self.assertRaises(ValueError):m.decode('{"a":1,"a":2}')

    def test_signed_adjustments_and_zero_targets(self):
        self.complete_supply()
        self.values.update(reward_mint_near_per_week="0",other_supply_adjustment_near_per_week="-100",retained_budget_hurdle_usd_per_week="0",capture_fraction="0")
        r=m.calculate(self.values)
        self.assertEqual(r["thresholds"]["full_supply_neutral_activity_threshold"]["value"],"0")
        self.assertEqual(r["thresholds"]["retained_budget_activity_threshold"]["status"],"ZERO_TARGET")
        self.assertEqual(Decimal(r["weekly"]["conditional_supply_change_near_per_week"]),-100)

    def test_saved_report_rebuild_preserves_raw_and_rejects_mismatch(self):
        spec=importlib.util.spec_from_file_location("model_rebuild",ROOT/"analysis/38_conditional_investment_model.py")
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        before={ROOT/"results"/name:(ROOT/"results"/name).read_bytes() for name in m.SOURCE_NAMES}
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/"derived.json"
            builder.rebuild(output=output)
            original=output.read_bytes()
            builder.rebuild(output=output,check=True)
            self.assertEqual(output.read_bytes(),original)
            changed=Path(directory)/"assumptions.json"
            document=m.decode(m.CONFIG.read_bytes());document["assumptions"]["fee_rate"]="0.01"
            changed.write_bytes(m.json_bytes(document))
            with self.assertRaisesRegex(ValueError,"Generated-file mismatch"):builder.rebuild(changed,output)
            self.assertEqual(output.read_bytes(),original)
        self.assertTrue(all(path.read_bytes()==raw for path,raw in before.items()))


if __name__=="__main__":unittest.main()
