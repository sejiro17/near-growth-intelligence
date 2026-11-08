"""Current integration: arithmetic, evidence levels, UI coverage and downloads."""

import hashlib
import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("current_rebuild", ROOT/"analysis/44_rebuild_integrated_research.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class IntegratedReviewTests(unittest.TestCase):
    def setUp(self):
        p = patch("socket.socket.connect", side_effect=AssertionError("Source requests forbidden"))
        p.start()
        self.addCleanup(p.stop)

    def test_unified_rebuild_preserves_all_inputs_and_reproduces_visual(self):
        paths = [p for p in (ROOT/"results").rglob("*") if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
        result = m.rebuild(check=True)
        self.assertEqual(result["source_requests"], 0)
        self.assertEqual(result["new_evidence_artifacts_reproduced"], 10)
        self.assertTrue(all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items()))
        visual = ET.fromstring(m.VISUAL.read_bytes())
        self.assertEqual(visual.attrib["role"], "img")
        data = m.build()
        self.assertEqual(m.VISUAL.read_bytes(), m.visual(data))
        self.assertEqual(m.STATUS.read_bytes(), m.status_markdown(data))

    def test_native_internal_cancellation_unallocated_residual_and_unknowns(self):
        data = m.build()
        ledger = data["native_ledger"]
        self.assertEqual(sum(int(w["net_flow_yocto"]) for w in ledger["wallets"]), int(ledger["external_net_yocto"]))
        self.assertEqual(ledger["internal_transfer_near"], "502794")
        for w in ledger["wallets"]:
            self.assertEqual(int(w["closing_yocto"])-int(w["opening_yocto"])-int(w["net_flow_yocto"]), int(w["residual_yocto"]))
            self.assertFalse(w["complete_balance_reconciliation"])
        self.assertEqual(ledger["unallocated_residual_near"], "0.0010849311842748")
        self.assertTrue(all(v is None for v in data["unavailable"].values()))
        self.assertIsNone(ledger["verified_purchases_near"])
        self.assertEqual(len(data["deliverables"]), 5)
        self.assertEqual(data["deliverables"][0]["status"], "Partial")
        self.assertIn("partial", data["deliverables"][2]["status"])

    def test_known_asset_layer_and_model_provenance_remain_scoped(self):
        data = m.build()
        assets = data["wallet_asset_ledger"]
        row, = assets["known_owner_asset_reconciliations"]
        self.assertEqual(row["classification"], "ONE_KNOWN_OWNER_ASSET_BALANCE_RECONCILIATION")
        self.assertEqual(row["owner"], "1csfundsadmin.sputnik-dao.near")
        self.assertEqual(row["asset_id"], "nep141:wrap.near")
        self.assertEqual(int(row["closing"]["balance_base_units"])-int(row["opening"]["balance_base_units"]), int(row["stock_change_base_units"]))
        self.assertEqual(row["stock_change_minus_selected_flow_base_units"], "0")
        self.assertIsNone(row["complete_flow_history"])
        self.assertIsNone(assets["coverage"]["complete_asset_pair_denominator"])
        self.assertIsNone(assets["coverage"]["complete_multi_asset_coverage"])
        provenance = data["model_input_provenance"]
        assumptions = m.read(90)["assumptions"]
        self.assertEqual({r["input"]: r["default_value"] for r in provenance["inputs"]}, assumptions)
        statuses = {r["input"]: r["status"] for r in provenance["inputs"]}
        self.assertEqual(sum(s == "DATED_BASELINE_REPEATED_AS_SCENARIO" for s in statuses.values()), 1)
        self.assertEqual(sum(s == "UNAVAILABLE" for s in statuses.values()), 3)
        self.assertFalse(provenance["wallet_stock_reconciliation_used_to_calibrate_capture"])
        self.assertIsNone(provenance["measured_fee_capture"])
        self.assertTrue(all(r["source_dependency"] and r["investment_conclusion_affected"] and r["saved_work"] for r in data["deliverables"]))

    def test_selected_controls_are_not_population_success_and_precision_is_kept(self):
        data = m.build()
        sweat, wx, tiny = data["attribution"]["selected_cases"][:3]
        self.assertEqual(wx["selected_transactions"], 1)
        self.assertEqual(wx["returned_receipt_outcomes"], 6)
        self.assertEqual(tiny["returned_receipt_outcomes"], 54)
        self.assertEqual(tiny["transactions_with_returned_failure"], 18)
        self.assertEqual(tiny["all_returned_receipts_successful_transactions"], 0)
        self.assertEqual(sweat["recorded_charge_near"], "0.0007690267153439")
        self.assertEqual(wx["recorded_charge_near"], "0.0007174786101312")
        self.assertGreater(Decimal(sweat["share_of_signed_population_pct"]), 0)
        self.assertNotIn("selected_downstream_evidence", data["attribution"]["population_table"][0])

    def test_render_cases_ledger_and_lossless_downloads(self):
        captured = []
        original = st.download_button
        def record(*args, **kwargs):
            captured.append(kwargs)
            return original(*args, **kwargs)
        with patch.object(st, "download_button", side_effect=record):
            app = AppTest.from_file(str(ROOT/"dashboard/app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            cases = m.build()["attribution"]["selected_cases"]
            for case in cases:
                app.selectbox(key="attribution_case").set_value(case.get("selection_key", case["account_id"])).run()
                self.assertFalse(app.exception)
                table = next(x.value for x in app.dataframe if "Graphs with a returned failure" in x.value)
                self.assertEqual(table["Graphs with a returned failure"].iloc[0], case["transactions_with_returned_failure"])
                download = next(x for x in reversed(captured) if x.get("key") == "attribution_case_download")
                self.assertEqual(download["data"], (ROOT/case["source_artifact"]).read_bytes())
                if case["account_id"] == "wx-cruce.near":
                    self.assertIn("no swap/output-asset evidence", "\n".join(x.value for x in app.markdown))
        for item in captured:
            source = ROOT/"results"/item["file_name"]
            if source.is_file():
                self.assertEqual(item["data"], source.read_bytes())
        weekly = next(x.value for x in app.dataframe if "Native inflow yoctoNEAR" in x.value)
        self.assertTrue(all(isinstance(x, str) and x.isdigit() for x in weekly["Native inflow yoctoNEAR"]))
        self.assertEqual(len(app.tabs), 7)
        outside = next(x.value for x in app.dataframe if "Minimum successful initial receipts" in x.value)
        self.assertEqual(outside["Minimum successful initial receipts"].tolist(), [686154, 630408])
        self.assertEqual(outside["Maximum successful initial receipts"].tolist(), [1011853, 877862])
        self.assertEqual(outside["Outside transaction success bounds"].tolist(), ["67.81%–100.00%", "71.81%–100.00%"])
        bounds_download = next(x for x in captured if x.get("key") == "returner_bounds_download")
        self.assertEqual(bounds_download["data"], m.path(105).read_bytes())
        internal = next(x.value for x in app.dataframe if "Exact internal asset base units" in x.value)
        self.assertEqual(internal["Exact internal asset base units"].tolist(), ["990000000000000000000000000", "1000100010001000100010", "-989998999899989998999899990", "-989998999899989998999899990", "0"])
        self.assertTrue(all(isinstance(x, str) for x in internal["Exact internal asset base units"]))
        known_download = next(x for x in captured if x.get("key") == "known_asset_comparison_download")
        self.assertEqual(known_download["data"], m.path(103).read_bytes())
        current_download = next(x for x in captured if x.get("key") == "wallet_asset_ledger_download")
        self.assertEqual(current_download["data"], m.path(104).read_bytes())
        text = "\n".join(x.value for kind in (app.markdown, app.caption, app.warning, app.info) for x in kind)
        for qualifier in ["not independently measured", "not representative", "unallocated", "no independent canonical tail control"]:
            self.assertIn(qualifier, text)

    def test_all_default_plotly_charts_replay_identically(self):
        snapshots = []
        for _ in range(2):
            app = AppTest.from_file(str(ROOT/"dashboard/app.py"), default_timeout=30).run()
            self.assertFalse(app.exception)
            snapshots.append([json.loads(x.proto.spec) for x in app.get("plotly_chart")])
        self.assertGreater(len(snapshots[0]), 10)
        self.assertEqual(snapshots[0], snapshots[1])


if __name__ == "__main__":
    unittest.main()
