"""Offline receipt links, asset separation and saved-result reproducibility."""
import copy
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wallet_sidecar", ROOT / "analysis/30_wallet_saved_evidence_ledger.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SavedLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
                patch("socket.create_connection", side_effect=AssertionError("Network forbidden")):
            cls.report = m.report()

    def test_saved_counts_weekly_identity_and_unavailable_classifications(self):
        r = self.report
        self.assertEqual(r["observed_distinct_receipts"], 2498)
        self.assertEqual(len(r["function_calls"]), 19)
        self.assertEqual(sum(w["accepted_action_count"] for w in r["weekly_native_flows"]), 2251)
        for wallet in r["wallets"]:
            weekly = [next(x for x in w["wallets"] if x["account_id"] == wallet["account_id"]) for w in r["weekly_native_flows"]]
            self.assertEqual(sum(int(w["observed_inflow_yocto"]) for w in weekly), int(wallet["valid_inflow_subtotal_yocto"]))
            self.assertEqual(sum(int(w["observed_outflow_yocto"]) for w in weekly), int(wallet["valid_outflow_subtotal_yocto"]))
            self.assertIsNone(wallet["complete_native_balance_net_yocto"])
        self.assertIsNone(r["verified_revenue_yocto"])
        self.assertIsNone(r["verified_buyback_yocto"])

    def test_native_children_and_failed_callbacks_are_kept_separate(self):
        paths = self.report["between_wallet_paths"]
        self.assertEqual(len(paths), 2)
        self.assertEqual(sum(int(p["transfer"]["amount_yocto"]) for p in paths), 502794 * 10**24)
        for path in paths:
            self.assertEqual(path["transfer"]["execution_check"], "SUCCESS_LOCAL_RECEIPT")
            self.assertEqual(len(path["direct_observed_parent_receipt_ids"]), 1)
            self.assertEqual([c["status"] for c in path["sibling_callbacks"]], ["FAILURE"])
            self.assertTrue(path["unobserved_direct_children"])

    def test_internal_asset_and_attached_native_deposit_are_different(self):
        events = self.report["logged_internal_asset_transfers"]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["asset_id"], "nep141:wrap.near")
        self.assertEqual(event["amount_base_units"], "989998999899989998999899990")
        self.assertEqual(event["matching_call"]["attached_native_yocto"], "1")
        self.assertTrue(event["separate_from_native_flow_totals"])

    def test_bad_event_arrays_amounts_and_nested_lists_stop(self):
        log = self.report["logged_internal_asset_transfers"][0]["raw_log"]
        original = m.decode(log[len("EVENT_JSON:"):])
        for amount in (1, "NaN", str(2**128)):
            bad = copy.deepcopy(original)
            bad["data"][0]["amounts"] = [amount]
            with self.assertRaisesRegex(ValueError, "u128"):
                m.events(["EVENT_JSON:" + m.m.prior.json_bytes(bad).decode()])
        bad = copy.deepcopy(original)
        bad["data"][0]["amounts"] = []
        with self.assertRaisesRegex(ValueError, "arrays"):
            m.events(["EVENT_JSON:" + m.m.prior.json_bytes(bad).decode()])
        with self.assertRaisesRegex(ValueError, "encoding"):
            m.elements([])
        self.assertEqual(m.elements({"list": [{"element": "b"}, {"element": "a"}]}), ["b", "a"])

    def test_failed_outcome_raw_status_is_validated(self):
        rows = m.decode(m.m.SOURCE.read_bytes())
        for row in rows:
            if row["row_kind"] != "ACTION":
                continue
            value = m.decode(row["record_json"])
            if value["outcome_check"] != "FAILED_LOCAL_RECEIPT":
                continue
            observed = value["outcome_audit"]["observations"][0]
            original = m.decode(observed["source_outcome_row_json"])
            observed["source_outcome_row_json"] = observed["source_outcome_row_json"].replace('"status":"FAILURE"', '"status":"SUCCESS_VALUE"')
            self.assertEqual(original["status"], "FAILURE")
            row["record_json"] = m.m.prior.json_bytes(value).decode()
            break
        with self.assertRaisesRegex(ValueError, "Raw outcome"):
            m.inspect_saved(m.m.prior.json_bytes(rows), m.decode(m.DECODED.read_bytes()))


if __name__ == "__main__":
    unittest.main()
