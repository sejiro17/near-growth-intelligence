"""Synthetic captures and saved-input checks only; live networking forbidden."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("historical_balances", ROOT / "analysis/31_wallet_historical_balances.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class HistoricalBalanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for target in ("socket.socket", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("Live networking forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.plan = m.plan()
        self.ledger = m.c.decode(m.sidecar.DECODED.read_bytes())
        self.calls, self.pauses = [], []
        path = self.root / "plan.json"
        path.write_bytes(m.c.json_bytes(self.plan))
        patched = patch.object(m, "PLAN", path)
        patched.start()
        self.addCleanup(patched.stop)

    def envelope(self, payload):
        target = m.BOUNDARIES[payload["id"].split("-")[0]]
        amount = 10**26+1 if payload["id"].startswith("opening") else 2*10**26+2
        return {"jsonrpc": "2.0", "id": payload["id"], "result": {
            "block_hash": target["hash"], "block_height": target["height"],
            "amount": str(amount), "locked": "7", "storage_usage": 123,
            "code_hash": "11111111111111111111111111111111"}}

    def error(self, payload, name="UNKNOWN_ACCOUNT"):
        target = m.BOUNDARIES[payload["id"].split("-")[0]]
        return {"jsonrpc": "2.0", "id": payload["id"], "error": {
            "name": "HANDLER_ERROR", "cause": {"name": name, "info": {
                "requested_account_id": payload["params"]["account_id"],
                "block_height": target["height"], "block_hash": target["hash"]}},
            "code": -32000, "message": "Server error", "data": "fixture"}}

    def transport(self, raw):
        payload = m.c.decode(raw)
        self.calls.append(payload)
        body = m.c.json_bytes(self.envelope(payload))
        return {"http_status": 200, "response_headers": [["Content-Type", "application/json"]],
                "body_complete": True, "transport_error": None}, body

    def collect(self, transport=None):
        with redirect_stdout(io.StringIO()):
            return m.collect(self.root / "captures", transport=transport or self.transport, pause=self.pauses.append)

    def test_six_exact_requests_bytes_pacing_and_unexplained_difference(self):
        directory = self.collect()
        self.assertEqual(self.calls, [i["request"] for i in self.plan["requests"]])
        self.assertEqual(self.pauses, [65]*6)
        result = m.validate(directory)
        self.assertEqual(result, m.c.decode((directory / "validation.json").read_bytes()))
        for row in result["accounts"]:
            self.assertEqual(row["opening"]["amount"], str(10**26+1))
            self.assertEqual(row["opening"]["locked"], "7")
            self.assertEqual(row["opening"]["storage_usage"], 123)
            self.assertEqual(row["combined_balance_change_yocto"], str(10**26+1))
            self.assertNotEqual(row["unexplained_stock_flow_difference_yocto"], "0")
            self.assertIsNone(row["attributed_fees_yocto"])
            self.assertFalse(row["complete_balance_reconciliation"])
        self.assertIsNone(result["verified_revenue_yocto"])
        self.assertIsNone(result["actual_supply_burn_yocto"])
        # Function-call deposits are measured components already in flows.
        one_cs = result["accounts"][1]
        self.assertEqual(one_cs["measured_function_call_deposits_already_in_native_totals"],
                         {"inflow_yocto": "600000000000000000000000", "outflow_yocto": "1"})
        self.assertEqual(m.near(-1), "-0.000000000000000000000001")

    def test_absence_is_explicit_null_not_zero_and_collection_remains_bounded(self):
        def transport(raw):
            meta, body = self.transport(raw)
            payload = m.c.decode(raw)
            return meta, m.c.json_bytes(self.error(payload)) if payload["id"] == "opening-2" else body
        result = m.validate(self.collect(transport))
        self.assertEqual(len(self.calls), 6)
        account = result["accounts"][1]
        self.assertEqual(account["opening"]["account_state"], "EXPLICIT_UNKNOWN_ACCOUNT")
        self.assertIsNone(account["opening"]["amount"])
        self.assertIsNone(account["combined_balance_change_yocto"])
        self.assertIsNone(account["unexplained_stock_flow_difference_yocto"])
        self.assertIsNone(result["group_combined_balance_change_yocto"])
        self.assertIsNotNone(result["group_observed_external_native_net_yocto"])

    def test_http_history_and_partial_errors_stop_without_retries(self):
        for mode in ("http", "history", "partial"):
            with self.subTest(mode=mode):
                self.calls.clear()
                def transport(raw):
                    meta, body = self.transport(raw)
                    if mode == "http":
                        meta["http_status"] = 429
                    elif mode == "history":
                        body = m.c.json_bytes(self.error(m.c.decode(raw), "GARBAGE_COLLECTED_BLOCK"))
                    else:
                        meta.update(body_complete=False, transport_error="fixture incomplete read")
                        body = body[:17]
                    return meta, body
                with self.assertRaises(ValueError):
                    self.collect(transport)
                self.assertEqual(len(self.calls), 1)
                directory = max((self.root / "captures").iterdir(), key=lambda p: p.stat().st_mtime_ns)
                self.assertTrue((directory / "opening-1.response.body").exists())
                self.assertEqual(m.c.decode((directory / "stopped.json").read_bytes())["attempts"], 1)
                self.assertFalse((directory / "validation.json").exists())

    def test_wrong_id_hash_height_monetary_values_and_absence_identity(self):
        payload = self.plan["requests"][0]["request"]
        target = m.BOUNDARIES["opening"]
        good = self.envelope(payload)
        mutations = [lambda x: x.update(id="wrong"),
                     lambda x: x["result"].update(block_hash="wrong"),
                     lambda x: x["result"].update(block_height=target["height"]+1),
                     lambda x: x["result"].update(amount=1),
                     lambda x: x["result"].update(amount="NaN"),
                     lambda x: x["result"].update(locked=str(2**128)),
                     lambda x: x["result"].update(storage_usage=None),
                     lambda x: x["result"].update(error="history unavailable"),
                     lambda x: x.update(error={"name": "INTERNAL_ERROR"})]
        for mutate in mutations:
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(ValueError):
                m.state(m.c.json_bytes(bad), payload, target)
        bad = self.error(payload)
        bad["error"]["cause"]["info"]["block_hash"] = "wrong"
        with self.assertRaisesRegex(ValueError, "absence identity"):
            m.state(m.c.json_bytes(bad), payload, target)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            m.state(b'{"jsonrpc":"2.0","id":"opening-1","id":"opening-2"}', payload, target)

    def test_tampering_missing_and_duplicate_states_are_rejected(self):
        directory = self.collect()
        item = self.plan["requests"][0]
        path = directory / "opening-1.response.body"
        raw = path.read_bytes()
        path.write_bytes(raw+b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.saved_state(directory, item)
        path.write_bytes(raw)
        states = [m.saved_state(directory, item) for item in self.plan["requests"]]
        with self.assertRaisesRegex(ValueError, "Incomplete/duplicate"):
            m.compare(states[:-1], self.ledger)
        with self.assertRaisesRegex(ValueError, "Incomplete/duplicate"):
            m.compare(states[:-1]+[states[0]], self.ledger)
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete/unexpected"):
            m.validate(directory)

    def test_boundary_dates_and_ledger_height_window_are_verified(self):
        raw = m.BASELINE.read_bytes()
        self.assertEqual(m.boundaries(raw, self.ledger)[1], 2254)
        with self.assertRaisesRegex(ValueError, "baseline dates"):
            m.boundaries(b"\n".join(raw.splitlines()[:-1]), self.ledger)
        bad = copy.deepcopy(self.ledger)
        action = next(a for a in bad["actions"] if a["execution_window"] == "IN_TARGET_WINDOW")
        action["execution_block_height"] = m.BOUNDARIES["opening"]["height"]
        with self.assertRaisesRegex(ValueError, "outside saved balance anchors"):
            m.boundaries(raw, bad)

    def test_zero_difference_does_not_establish_complete_reconciliation(self):
        states = []
        flows = {w["account_id"]: int(w["observed_action_layer_net_yocto"]) for w in self.ledger["wallets"]}
        for item in self.plan["requests"]:
            payload = item["request"]
            envelope = self.envelope(payload)
            envelope["result"]["amount"] = str(10**36 + (flows[item["account_id"]] if item["boundary"] == "closing" else 0))
            state = m.state(m.c.json_bytes(envelope), payload, m.BOUNDARIES[item["boundary"]])
            state["boundary"] = item["boundary"]
            states.append(state)
        result = m.compare(states, self.ledger)
        self.assertEqual(result["group_unexplained_stock_flow_difference_yocto"], "0")
        for row in result["accounts"]:
            self.assertEqual(row["unexplained_stock_flow_difference_yocto"], "0")
            self.assertIsNone(row["attributed_fees_yocto"])
            self.assertFalse(row["complete_balance_reconciliation"])
        self.assertIsNone(result["verified_revenue_yocto"])


if __name__ == "__main__":
    unittest.main()
