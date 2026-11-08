"""Saved ledger arithmetic, asset separation and request-only safeguards."""

import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ledger_consolidation", ROOT / "analysis/33_consolidate_three_wallet_ledger.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class LedgerConsolidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("socket.socket", side_effect=AssertionError("Live network forbidden")), patch("socket.create_connection", side_effect=AssertionError("Live network forbidden")):
            cls.result = m.report()

    def test_stock_external_and_internal_legs_reconcile_exactly(self):
        r = self.result
        self.assertEqual(len(r["native_entries"]), 2251)
        self.assertEqual(sum(w["accepted_action_count"] for w in r["weekly_native_flow_observations"]), 2251)
        self.assertEqual(sum(int(p["transfer"]["amount_yocto"]) for p in r["native_internal_transfers"]), 502794*10**24)
        for w in r["native_wallets"]:
            flow = sum(int(x["inflow_yocto"])-int(x["outflow_yocto"]) for x in w["flow_scopes"].values())
            change = int(w["closing"]["combined_yocto"])-int(w["opening"]["combined_yocto"])
            self.assertEqual(change-flow, int(w["unexplained_stock_flow_difference_yocto"]))
        self.assertEqual([w["unexplained_stock_flow_difference_yocto"] for w in r["native_wallets"]], ["0", "1084931184274800000000", "0"])
        self.assertEqual(r["native_wallets"][1]["difference_allocation"], "UNALLOCATED")
        self.assertEqual(r["native_wallets"][1]["residual_driven_collection"], "NONE")

    def test_proposals_and_rejected_votes_are_not_observed_asset_transfers(self):
        asset = self.result["asset_layer"]
        self.assertEqual(len(asset["observed_successful_internal_transfers"]), 1)
        self.assertEqual(asset["observed_successful_internal_transfers"][0]["amount_base_units"], "989998999899989998999899990")
        proposals = [x for x in asset["decoded_asset_requests"] if x["context"] == "PROPOSAL_REQUEST_ONLY"]
        self.assertTrue(any(x["proposal_action"] == "VoteReject" for x in proposals))
        linked = [x for x in proposals if x["execution_link"] is not None]
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0]["execution_link"]["receipt_id"], "4sBxF4Uut6w9Kv6kgcwzLBVKk8MTgEEu6yaETfDNN3QL")
        self.assertTrue(any(x["description_unverified"] and "Network Fee" in x["description_unverified"] for x in proposals))
        self.assertEqual(asset["explicit_verified_exchange_purchase_records"], [])
        self.assertIsNone(asset["verified_purchase_amount"])
        self.assertIsNone(asset["full_ft_mt_transfer_totals"])
        conversion = asset["closed_saved_conversion_context"]
        self.assertEqual(conversion["internal_debit"]["event"]["event"], "mt_burn")
        self.assertEqual(conversion["unwrap_request"]["method"], "near_withdraw")
        self.assertTrue(conversion["native_transfer_already_counted"])
        self.assertIsNone(conversion["independently_measured_native_supply_burn"])
        self.assertIsNone(conversion["verified_fee_origin"])
        self.assertIsNone(conversion["internal_owner_is_verified_native_wallet_alias"])

    def test_endpoint_code_hashes_do_not_establish_source_ownership_or_revenue(self):
        for row in self.result["historical_contract_evidence"]:
            self.assertTrue(row["equal_endpoint_code_hashes"])
            self.assertIsNone(row["wasm_to_source_version_match"])
            self.assertIsNone(row["historical_policy_and_beneficial_ownership"])
        self.assertIsNone(self.result["verified_revenue_yocto"])
        self.assertIsNone(self.result["verified_buybacks_yocto"])
        self.assertEqual(self.result["closed_withdrawal_provenance"]["additional_collection"], "NONE")

    def test_broken_native_identity_is_rejected(self):
        ledger = m.c.decode(m.b.sidecar.DECODED.read_bytes())
        balance = m.c.decode(m.BALANCES.read_bytes())
        bad = copy.deepcopy(balance)
        bad["accounts"][0]["successful_native_inflow_yocto"] = "1"
        with self.assertRaisesRegex(ValueError, "scope sums"):
            m.wallet_rows(ledger, bad)


if __name__ == "__main__":
    unittest.main()
