"""Saved-evidence and interaction coverage for every dashboard selector/download."""

import base64
import csv
import io
import json
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import streamlit as st
from streamlit.testing.v1 import AppTest

from dashboard import presentation


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"


def vector(value):
    if isinstance(value, dict) and "bdata" in value:
        return np.frombuffer(base64.b64decode(value["bdata"]), dtype=value["dtype"]).tolist()
    return value


class DashboardAuditTests(unittest.TestCase):
    def setUp(self):
        guard = patch("socket.socket.connect", side_effect=AssertionError("Source requests forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def app(self):
        return AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=30).run()

    def healthy(self, app):
        self.assertFalse(app.exception)
        self.assertFalse(app.error)

    def test_published_values_overlaps_unavailable_cells_and_display_precision(self):
        app = self.app()
        self.healthy(app)
        evidence = json.loads((RESULTS / "62_integrated_research_evidence.json").read_bytes())
        cohorts = next(x.value for x in app.dataframe if "All +1/+4/+8" in x.value)
        self.assertEqual(cohorts["Accounts"].tolist(), [x["cohort_accounts"] for x in evidence["cohorts"]])
        self.assertEqual(cohorts["+8 return"].tolist(), ["47.41%", "46.18%", "Unavailable", "Unavailable"])
        self.assertEqual(cohorts["+4 return"].iloc[-1], "Unavailable")
        spending = next(x.value for x in app.dataframe if list(x.value.columns) ==
                        ["Group", "Submission week", "Conversion NEAR", "Initial receipt NEAR"])
        groups = evidence["shared_week"]["populations"] + evidence["october12_pilot"]["populations"]
        self.assertEqual(spending["Conversion NEAR"].tolist(),
                         [Decimal(g["observed"]["recorded_conversion_spending_near"]) for g in groups])
        metrics = {x.label: x.value for x in app.metric}
        self.assertEqual(metrics["Supply minus raw validator change"], "16,599.51 NEAR")
        self.assertEqual(metrics["Combined spending · eight weeks"], "67,988.91 NEAR")
        text = "\n".join(x.value for kind in (app.markdown, app.caption, app.warning, app.info) for x in kind)
        self.assertIn("3,871,009", text)
        self.assertIn("Supply reconciliation is ongoing", text)
        self.assertIn("Full-window issuance", text)
        self.assertIn("six-day", text)
        self.assertIn("descendants are excluded", text)
        overlap_warning = next(x.value for x in app.warning if "Some accounts belong" in x.value)
        self.assertIn("group totals cannot be combined", overlap_warning)
        self.assertIn("unavailable", overlap_warning)
        self.assertNotIn("Do not", overlap_warning)
        methodology = next(x for x in app.expander if x.label == "Methodology: overlap, execution dates and coverage")
        methodology_text = "\n".join(x.value for x in methodology.markdown)
        overlap = evidence["shared_week"]["overlap"]
        self.assertIn(f"{overlap['august_and_september_accounts']:,}", methodology_text)
        self.assertIn(f"{overlap['august_and_september_transactions']:,}", methodology_text)
        self.assertIn("subset", methodology_text)
        self.assertIn("union or the intersection", methodology_text)
        for node in app.dataframe:
            config = json.loads(node.proto.columns)
            for column in node.value.columns:
                if pd.api.types.is_integer_dtype(node.value[column]):
                    self.assertEqual(config[column]["type_config"]["format"], "%,d")

    def test_every_selector_option_and_profile_week_renders_from_saved_inputs(self):
        app = self.app()
        leading = pd.read_csv(RESULTS / f"18_weekly_leading_signing_accounts_{PERIOD}.csv")
        options = list(app.selectbox(key="drivers_signing_account").options)
        for account in options:
            with self.subTest(driver=account):
                app.selectbox(key="drivers_signing_account").set_value(account).run()
                self.healthy(app)
                charts = [json.loads(x.proto.spec) for x in app.tabs[1].get("plotly_chart")]
                line, = [x for x in charts if x["data"][0]["type"] == "scatter"]
                expected = leading.loc[leading.signer_account_id.eq(account)].sort_values("week_start")
                self.assertEqual(vector(line["data"][0]["y"]), expected.transactions.tolist())
        for label in ("Inspect initial receipt outcomes", "Who are you researching for?", "Choose an investigation priority"):
            selected = next(x for x in app.selectbox if x.label == label)
            for choice in list(selected.options):
                with self.subTest(selector=label, choice=choice):
                    next(x for x in app.selectbox if x.label == label).set_value(choice).run()
                    self.healthy(app)
        receivers = pd.read_csv(RESULTS / f"12_weekly_receiver_activity_{PERIOD}.csv")
        for week in sorted(receivers.week_start.unique()):
            with self.subTest(receiver_week=week):
                next(x for x in app.selectbox if x.label == "Inspect transaction receivers for the week starting").set_value(pd.Timestamp(week)).run()
                self.healthy(app)
                table = next(x.value for x in app.dataframe if "receiver_rank" in x.value)
                expected = receivers.loc[receivers.week_start.eq(week)].sort_values("receiver_rank")
                self.assertEqual(table.transactions.tolist(), expected.transactions.tolist())
        document = json.loads((RESULTS / f"35_account_profiles_{PERIOD}.json").read_bytes())
        for profile in document["profiles"]:
            app.selectbox(key="explorer_account").set_value(profile["account_id"]).run()
            for week in profile["weekly"]:
                with self.subTest(profile=profile["account_id"], week=week["week_start"]):
                    app.selectbox(key="explorer_week").set_value(week["week_start"]).run()
                    self.healthy(app)
                    table = next(x.value for x in app.dataframe if list(x.value.columns) ==
                                 ["receiver_account_id", "rank", "transactions", "active_days"])
                    self.assertEqual(table.to_dict("records"), week["top_receivers"])

    def test_downloads_preserve_original_bytes_and_filtered_cell_strings(self):
        outputs = []
        original = st.download_button

        def record(*args, **kwargs):
            outputs.append(kwargs)
            return original(*args, **kwargs)

        with patch.object(st, "download_button", side_effect=record):
            app = self.app()
            self.healthy(app)
        filenames = {item["file_name"] for item in outputs}
        self.assertTrue({"conditional_scenario_applied.json", "100_integrated_research_review.json",
                         "103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json",
                         "104_wallet_ledger_with_known_asset_reconciliation.json",
                         "105_returner_initial_success_outside_top10_bounds.json"} <= filenames)
        scenario = next(x for x in outputs if x["file_name"] == "conditional_scenario_applied.json")
        applied = json.loads(scenario["data"])
        self.assertEqual(applied["scenario"]["classification"], "SCENARIO_NOT_OBSERVED_OR_EXPECTED_RETURN")
        self.assertIsNone(applied["evidence"]["measured_unavailable"]["attributed_product_revenue_usd"])
        for item in outputs:
            source = RESULTS / item["file_name"]
            if source.exists():
                self.assertEqual(item["data"], source.read_bytes())
        for account in ("tinykoala595.near", "wx-cruce.near"):
            name = f"27_growth_account_execution_costs_{PERIOD}.csv"
            raw = presentation.saved_csv(name, {"signer_account_id": account})
            expected = [r for r in csv.DictReader(io.StringIO((RESULTS / name).read_text())) if r["signer_account_id"] == account]
            self.assertEqual(list(csv.DictReader(io.StringIO(raw.decode()))), expected)
            if account == "tinykoala595.near":
                item = next(x for x in outputs if x["file_name"].startswith(f"27_{account}_"))
                self.assertEqual(item["data"], raw)
        document = json.loads((RESULTS / f"35_account_profiles_{PERIOD}.json").read_bytes())
        item = next(x for x in outputs if x["file_name"].endswith("_profile.json"))
        self.assertEqual(json.loads(item["data"]), document["profiles"][0])
        priorities = next(x for x in outputs if x["file_name"].startswith("decision_priorities"))
        priority_rows = list(csv.DictReader(io.StringIO(priorities["data"].decode())))
        priority_table = next(x.value for x in app.dataframe if "Priority" in x.value.columns)
        self.assertEqual(priority_rows, priority_table.to_dict("records"))
        with self.assertRaises(ValueError):
            presentation.saved_csv(name, {"signer_account_id": "absent.near"})


if __name__ == "__main__":
    unittest.main()
