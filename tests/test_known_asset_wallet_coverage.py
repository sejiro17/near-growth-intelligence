"""Known internal stocks stay separate from complete discovery and attribution."""

import base64
import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("known_asset", ROOT/"analysis/46_known_asset_wallet_coverage.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def response(boundary, value="123456789012345678901234567890"):
    target = m.c.decode(m.PLAN.read_bytes())["boundaries"][boundary]
    return {"block_hash": target["hash"], "block_height": target["height"],
            "result": list(m.c.json_bytes(value)), "logs": []}


class KnownAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("socket.socket", side_effect=AssertionError("No network")):
            cls.report = m.report()

    def test_inventory_and_denominators(self):
        inv = self.report["inventory"]
        self.assertEqual(inv["observed_asset_ids"], ["nep141:wrap.near"])
        self.assertEqual(inv["request_context_counts"], {"DIRECT_OBSERVED_CALL": 1, "PROPOSAL_REQUEST_ONLY": 7})
        self.assertEqual(len(inv["observed_movements"]), 1)
        self.assertEqual(inv["proposal_link_count"], 1)
        self.assertEqual(len(inv["opaque_proposal_recipients"]), 3)
        self.assertIsNone(inv["complete_asset_universe"])
        self.assertIsNone(inv["verified_revenue"])
        self.assertTrue(all(a["verified_wallet_alias"] is None for a in inv["opaque_proposal_recipients"]))
        self.assertEqual(self.report["pilot"]["maximum_requests"], 2)
        self.assertEqual(self.report["pilot"]["denominator"]["selected_wallets"], 3)

    def test_exact_request_and_historical_response(self):
        for boundary in ("opening", "closing"):
            payload = m.request(boundary)
            args = m.c.decode(base64.b64decode(payload["params"]["args_base64"], validate=True))
            self.assertEqual(args, {"account_id": m.OWNER, "token_id": m.ASSET})
            self.assertEqual(payload["params"]["method_name"], "mt_balance_of")
            self.assertEqual(m.balance(response(boundary), boundary)["balance_base_units"], "123456789012345678901234567890")
        self.assertEqual(m.balance(response("opening", "0"), "opening")["balance_base_units"], "0")

    def test_invalid_or_unavailable_is_not_zero(self):
        for bad in (None, 123, -1, "NaN", "1.5", "-1", str(2**128), "١"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m.balance(response("opening", bad), "opening")
        for key, value in (("block_hash", "wrong"), ("block_height", 42), ("result", [True]), ("logs", None)):
            bad = response("opening")
            bad[key] = value
            with self.assertRaises(ValueError):
                m.balance(bad, "opening")
        with self.assertRaisesRegex(ValueError, "JSON-RPC error"):
            m.c.envelope(m.c.json_bytes({"jsonrpc": "2.0", "id": "known-asset-opening", "error": {"message": "unavailable"}}), m.request("opening"))

    def test_duplicate_and_disagreeing_events_rejected(self):
        original = m.c.decode(m.SOURCE.read_bytes())
        duplicate = copy.deepcopy(original)
        duplicate["asset_layer"]["observed_successful_internal_transfers"] *= 2
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            m.inventory(duplicate)
        bad = copy.deepcopy(original)
        bad["asset_layer"]["observed_successful_internal_transfers"][0]["amount_base_units"] = "1"
        with self.assertRaisesRegex(ValueError, "disagree"):
            m.inventory(bad)

    def test_capture_two_request_cap_reuse_and_checksums(self):
        attempts = []
        def transport(endpoint, payload):
            boundary = payload["id"].removeprefix("known-asset-")
            attempts.append(boundary)
            raw = m.c.json_bytes({"jsonrpc": "2.0", "id": payload["id"], "result": response(boundary, "100" if boundary == "opening" else "200")})
            return {"http_status": 200, "body_complete": True, "transport_error": None, "response_headers": []}, raw
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.object(m, "OUTPUT", Path(temp)), patch.object(m, "report", return_value=self.report):
            m.collect(transport=transport, pause=lambda _: None)
            m.collect(transport=transport, pause=lambda _: None)
            self.assertEqual(attempts, ["opening", "closing"])
            result = m.validate()
            self.assertEqual(result["stock_change_base_units"], "100")
            self.assertEqual(result["selected_observed_internal_flow_net_base_units"], "-989998999899989998999899990")
            self.assertEqual(result["stock_change_minus_selected_flow_base_units"], "989998999899989998999900090")
            self.assertIsNone(result["verified_revenue"])
            directory = Path(temp)/Path(m.c.decode((Path(temp)/"opening.attempt.json").read_bytes())["directory"]).name
            (directory/"response.body").write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, "checksum"):
                m.saved_balance("opening")

    def test_failure_retained_without_retry_or_second_request(self):
        attempts = []
        def transport(endpoint, payload):
            attempts.append(payload)
            return {"http_status": 503, "body_complete": True, "transport_error": None}, b'unavailable'
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.object(m, "OUTPUT", Path(temp)), patch.object(m, "report", return_value=self.report):
            with self.assertRaisesRegex(ValueError, "HTTP 503"):
                m.collect(transport=transport, pause=lambda _: None)
            with self.assertRaisesRegex(ValueError, "Stopped capture"):
                m.collect(transport=transport, pause=lambda _: None)
            self.assertEqual(len(attempts), 1)
            self.assertFalse((Path(temp)/"closing.attempt.json").exists())
            self.assertEqual(len(list(Path(temp).glob('*/stopped.json'))), 1)

    def test_saved_two_state_result_reproduces_without_economic_attribution(self):
        with patch("socket.socket", side_effect=AssertionError("No network")):
            result = m.validate()
        saved = ROOT/"results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json"
        self.assertEqual(m.c.json_bytes(result), saved.read_bytes())
        self.assertEqual(result["stock_change_base_units"], result["selected_observed_internal_flow_net_base_units"])
        self.assertEqual(result["stock_change_minus_selected_flow_base_units"], "0")
        self.assertIsNone(result["complete_asset_universe"])
        self.assertIsNone(result["verified_purchases"])
        self.assertIsNone(result["verified_revenue"])


if __name__ == "__main__":
    unittest.main()
