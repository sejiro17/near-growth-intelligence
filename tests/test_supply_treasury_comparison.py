"""Offline tests for analysis/51_supply_treasury_comparison.py (result 108). No network access."""

import copy
import importlib.util
import json
import socket
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("treasury_comparison_under_test", ROOT / "analysis/51_supply_treasury_comparison.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class Offline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._connect = socket.socket.connect
        def blocked(*_a, **_k):
            raise AssertionError("network access attempted in offline test")
        socket.socket.connect = blocked
        cls.ledger, cls.bounds, _, _ = m.load_inputs()
        cls.saved = json.loads(m.RESULT.read_bytes())

    @classmethod
    def tearDownClass(cls):
        socket.socket.connect = cls._connect

    def test_result_108_reproduces_byte_for_byte(self):
        data = (json.dumps(m.report(), ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
        self.assertEqual(m.RESULT.read_bytes(), data)

    def test_states_are_at_the_issuance_anchor_blocks(self):
        blocks = self.saved["same_block_reconciliation"]
        self.assertEqual(blocks["opening"]["block_hash"], self.bounds["anchors"][0]["anchor_hash"])
        self.assertEqual(blocks["closing"]["block_hash"], self.bounds["anchors"][-1]["anchor_hash"])
        self.assertEqual(blocks["states_checked"], 6)

    def test_mismatched_block_stops_comparison(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["native_wallets"][1]["closing"]["block_hash"] = "DIFFERENT"
        with self.assertRaisesRegex(ValueError, "not at the issuance anchor block"):
            m.same_blocks(ledger, self.bounds)
        ledger = copy.deepcopy(self.ledger)
        ledger["window"]["end_exclusive"] = "2026-10-20T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "window differs"):
            m.same_blocks(ledger, self.bounds)

    def test_internal_transfers_cancel_and_are_not_external(self):
        g = self.saved["three_wallet_group"]
        self.assertEqual(g["between_wallet_inflow_yocto"], g["between_wallet_outflow_yocto"])
        self.assertEqual(int(g["balance_change_yocto"]),
                         int(g["external_net_inflow_yocto"]) + int(g["unallocated_stock_flow_difference_yocto"]))
        ledger = copy.deepcopy(self.ledger)
        ledger["native_internal_transfers"][0]["transfer"]["amount_yocto"] = "1"
        lower, upper = (int(self.bounds["window_total"][k]) for k in ("issuance_lower_bound_yocto", "issuance_upper_bound_yocto"))
        with self.assertRaisesRegex(ValueError, "do not cancel"):
            m.group(m.wallet_rows(ledger, lower, upper), ledger, lower, upper)

    def test_tampered_stock_flow_identity_is_rejected(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["native_wallets"][0]["unexplained_stock_flow_difference_yocto"] = "5"
        with self.assertRaisesRegex(ValueError, "stock-flow identity"):
            m.wallet_rows(ledger, 1, 2)

    def test_shares_are_exact_fractions_of_the_bounds(self):
        d = self.saved["denominators"]
        lower, upper = int(d["issuance_lower_bound_yocto"]), int(d["issuance_upper_bound_yocto"])
        for w in self.saved["wallets"] + [self.saved["three_wallet_group"]]:
            for key, share in w["share_of_issuance"].items():
                amount = int(w[key + "_yocto"])
                self.assertEqual(share["against_issuance_upper_bound"]["fraction_exact"],
                                 f"{Fraction(amount, upper).numerator}/{Fraction(amount, upper).denominator}")
                self.assertEqual(share["against_issuance_lower_bound"]["fraction_exact"],
                                 f"{Fraction(amount, lower).numerator}/{Fraction(amount, lower).denominator}")
        g = self.saved["three_wallet_group"]["share_of_issuance"]["external_net_inflow"]
        self.assertEqual((g["against_issuance_upper_bound"]["percent_display"], g["against_issuance_lower_bound"]["percent_display"]),
                         ("19.0777", "19.3871"))

    def test_no_economic_classification_is_filled(self):
        self.assertTrue(all(v is None for v in self.saved["unavailable"].values()))
        self.assertTrue(all(w["classification"] == "UNCLASSIFIED_NATIVE_FLOWS_AND_CUSTODIAL_BALANCE" for w in self.saved["wallets"]))
        self.assertEqual(self.saved["network_requests"], 0)
        text = " ".join(self.saved["interpretation_limits"])
        for phrase in ("not measured value capture", "remain part of total supply", "not the complete treasury system"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
