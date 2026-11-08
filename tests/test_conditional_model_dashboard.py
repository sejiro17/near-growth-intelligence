"""Exercise applied assumptions, downloads and invalid-input handling offline."""

import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest
from dashboard import conditional_model as model

ROOT=Path(__file__).resolve().parents[1]


class ConditionalDashboardTests(unittest.TestCase):
    def setUp(self):
        g=patch("socket.socket.connect",side_effect=AssertionError("Source requests forbidden"));g.start();self.addCleanup(g.stop)

    def app(self):
        return AppTest.from_file(str(ROOT/"dashboard/app.py"),default_timeout=30).run()

    def test_opening_model_nulls_and_paused_collection_render(self):
        app=self.app();self.assertFalse(app.exception);self.assertFalse(app.error)
        metrics={x.label:x.value for x in app.metric}
        self.assertEqual(metrics["Illustrative default · captured fee revenue"],"$50,000.00 /week")
        self.assertEqual(metrics["Illustrative default · purchased and destroyed"],"2,500.00 NEAR/week")
        self.assertEqual(metrics["Illustrative default · purchased and held"],"2,500.00 NEAR/week")
        text="\n".join(x.value for kind in (app.markdown,app.caption,app.info,app.warning) for x in kind)
        self.assertIn("Neardata bulk collection is paused",text)
        self.assertIn("30-block/minute",text)
        self.assertIn("Unavailable NEAR/week",text)
        self.assertIn("not expected investment returns",text)
        for table in app.dataframe:
            if "Conditional threshold" in table.value or "Use of captured budget" in table.value:
                self.assertTrue(all(x=="Illustrative default scenario" for x in table.value["Basis"]))
        self.assertEqual(len(app.tabs),7)

    def test_edit_form_applies_decimal_values_and_download_matches_applied_scenario(self):
        captured=[];original=st.download_button
        def record(*args,**kwargs):
            captured.append(kwargs);return original(*args,**kwargs)
        with patch.object(st,"download_button",side_effect=record):
            app=self.app()
            updates={"price_usd_per_near":"2","eligible_activity_usd_per_week":"1000","fee_rate":"0.01","capture_fraction":"0.5","destruction_allocation":"0.5","custody_allocation":"0.25","horizon_weeks":"4"}
            for key,value in updates.items():app.text_input(key="scenario_"+key).set_value(value)
            app.button(key="apply_conditional_scenario").click().run()
        self.assertFalse(app.exception);self.assertFalse(app.error)
        metrics={x.label:x.value for x in app.metric}
        self.assertEqual(metrics["User-edited hypothetical · captured fee revenue"],"$5.00 /week")
        self.assertEqual(metrics["User-edited hypothetical · purchased and destroyed"],"1.25 NEAR/week")
        latest=next(x for x in reversed(captured) if x["file_name"]=="conditional_scenario_applied.json")
        document=model.decode(latest["data"])
        self.assertEqual(document["display_mode"],"USER_EDITED_HYPOTHETICAL_SCENARIO")
        self.assertEqual(document["assumptions"]["fee_rate"],"0.01")
        self.assertEqual(document["scenario"]["weekly"],model.calculate(document["assumptions"])["weekly"])
        self.assertEqual(Decimal(document["scenario"]["horizon_totals"]["purchased_and_destroyed_near"]),Decimal(5))
        self.assertIsNone(document["evidence"]["measured_unavailable"]["actual_gross_supply_burn_near"])

    def test_invalid_allocation_is_rejected_and_last_applied_result_retained(self):
        app=self.app()
        app.text_input(key="scenario_destruction_allocation").set_value("0.9")
        app.text_input(key="scenario_custody_allocation").set_value("0.9")
        app.button(key="apply_conditional_scenario").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Allocations exceed" in x.value for x in app.error))
        self.assertEqual(next(x.value for x in app.metric if x.label=="Illustrative default · captured fee revenue"),"$50,000.00 /week")

    def test_zero_capture_is_hypothetical_and_tiny_overallocation_is_rejected(self):
        app=self.app()
        app.text_input(key="scenario_capture_fraction").set_value("0")
        app.button(key="apply_conditional_scenario").click().run()
        self.assertFalse(app.exception);self.assertFalse(app.error)
        self.assertEqual(next(x.value for x in app.metric if x.label=="User-edited hypothetical · captured fee revenue"),"$0.00 /week")
        table=next(x.value for x in app.dataframe if "Conditional threshold" in x.value)
        self.assertTrue(any(x=="Unreachable with zero coefficient" for x in table['Status']))
        app.text_input(key="scenario_destruction_allocation").set_value("1")
        app.text_input(key="scenario_custody_allocation").set_value("0."+"0"*85+"1")
        app.button(key="apply_conditional_scenario").click().run()
        self.assertFalse(app.exception)
        self.assertTrue(any("Allocations exceed" in x.value for x in app.error))


if __name__=="__main__":unittest.main()
