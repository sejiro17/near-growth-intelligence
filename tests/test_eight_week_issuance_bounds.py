"""Offline tests for analysis/50_eight_week_issuance_bounds.py. No network access."""

import importlib.util
import json
import random
import socket
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("issuance_bounds_under_test", ROOT / "analysis/50_eight_week_issuance_bounds.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)

YEAR_NS = m.SECONDS_PER_YEAR * m.NS


class NoNetwork(unittest.TestCase):
    def setUp(self):
        self._connect = socket.socket.connect
        def blocked(*_a, **_k):
            raise AssertionError("network access attempted in offline test")
        socket.socket.connect = blocked

    def tearDown(self):
        socket.socket.connect = self._connect


def row(date, supply, epoch_height, parent_ts):
    return {"date": date, "total_supply_yocto": str(supply), "epoch_height": epoch_height,
            "previous_epoch_last_block_timestamp_nanosec": str(parent_ts), "max_inflation_rate": [1, 40]}


def simulate_week(rng, supply, epochs):
    """Exact nearcore-style evolution: mint at epoch starts, unsigned burns otherwise.

    Returns (opening supply, closing supply, true minted, total earned duration).
    Minted reward = floor(S_end_of_earned_epoch * duration / (40 * year)) scaled by uptime <= 1.
    """
    opening, minted, duration = supply, 0, 0
    for _ in range(epochs):
        burn = rng.randrange(0, 10**28)          # burns before the epoch closes (unsigned)
        supply -= burn
        d = rng.randrange(20_000, 30_000) * m.NS  # earned epoch duration
        ceiling = supply * d // (40 * YEAR_NS)
        uptime = Fraction(rng.randrange(900, 1001), 1000)
        mint = int(ceiling * uptime)
        supply += mint
        minted += mint
        duration += d
    supply -= rng.randrange(0, 10**28)            # burns after the final mint, before the anchor
    return opening, supply, minted, duration


class BoundArithmetic(NoNetwork):
    def test_bounds_contain_simulated_true_minting(self):
        rng = random.Random(20261113)
        for _ in range(300):
            s0 = rng.randrange(10**32, 2 * 10**33)
            epochs = rng.randrange(1, 30)
            opening, closing, minted, duration = simulate_week(rng, s0, epochs)
            w = m.week_bound(row("2026-09-20", opening, 100, 0), row("2026-09-27", closing, 100 + epochs, duration), (1, 40))
            self.assertLessEqual(int(w["issuance_lower_bound_yocto"]), minted)
            self.assertLessEqual(minted, int(w["issuance_upper_bound_yocto"]))
            true_debit = opening + minted - closing
            self.assertGreaterEqual(true_debit, 0)
            self.assertLessEqual(true_debit, int(w["net_header_debit_upper_bound_yocto"]))

    def test_exact_formula_and_floor(self):
        s, d = 1_306_866_141 * 10**24, 7 * 86400 * m.NS
        w = m.week_bound(row("2026-09-20", s, 1, 0), row("2026-09-27", s + 10**29, 24, d), (1, 40))
        x = Fraction(d, 40 * YEAR_NS)
        self.assertEqual(int(w["issuance_upper_bound_yocto"]), (s * x / (1 - x)).__floor__())
        self.assertEqual(w["issuance_lower_bound_yocto"], str(10**29))
        self.assertEqual(w["epoch_reward_applications"], 23)
        self.assertEqual(w["net_header_debit_lower_bound_yocto"], "0")

    def test_negative_movement_keeps_zero_lower_bound(self):
        w = m.week_bound(row("2026-09-20", 10**33, 1, 0), row("2026-09-27", 10**33 - 5, 2, 10**15), (1, 40))
        self.assertEqual(w["issuance_lower_bound_yocto"], "0")

    def test_movement_above_ceiling_rejects_semantics(self):
        with self.assertRaisesRegex(ValueError, "exceeds protocol issuance ceiling"):
            m.week_bound(row("2026-09-20", 10**33, 1, 0), row("2026-09-27", 2 * 10**33, 2, 10**15), (1, 40))

    def test_non_increasing_epochs_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-increasing"):
            m.week_bound(row("2026-09-20", 10**33, 5, 0), row("2026-09-27", 10**33, 5, 10**15), (1, 40))

    def test_rate_change_across_anchors_rejected(self):
        a, b = row("2026-08-23", 10**33, 1, 0), row("2026-08-30", 10**33, 2, 10**15)
        b["max_inflation_rate"] = [1, 20]
        with self.assertRaisesRegex(ValueError, "Inflation rate differs"):
            m.compute([a, b])


def fake_chain(anchors, reference, overrides=None):
    overrides = overrides or {}
    def transport(raw):
        p = json.loads(raw)
        i = int(p["id"].split("-")[0][1:]); a = anchors[i]; step = p["id"].rsplit("-", 1)[1]
        from datetime import datetime
        ts = int(datetime.fromisoformat(a["date"] + "T23:59:59+00:00").timestamp()) * m.NS
        ep = 100 + 23 * i
        def hdr(height, h, e, ne, t):
            return {"header": {"hash": h, "prev_hash": "P" + h, "epoch_id": e, "next_epoch_id": ne, "height": height,
                               "timestamp_nanosec": str(t), "total_supply": str(10**33 + i * 10**29)}}
        result = {"block": lambda: hdr(a["height"], a["hash"], f"E{ep}", f"E{ep+1}", ts),
                  "validators": lambda: {"epoch_start_height": a["height"] - 10, "epoch_height": ep},
                  "first": lambda: hdr(a["height"] - 10, f"F{i}", f"E{ep}", f"E{ep+1}", ts - 10**9),
                  "parent": lambda: hdr(a["height"] - 11, f"PF{i}", f"E{ep-1}", f"E{ep}", ts - 2 * 10**9),
                  "config": lambda: dict(reference)}[step]()
        result = overrides.get((i, step), lambda r: r)(result)
        if result == "HTTP500":
            return {"http_status": 500, "response_headers": [], "body_complete": True, "transport_error": None}, b"{}"
        body = json.dumps({"jsonrpc": "2.0", "id": p["id"], "result": result}).encode()
        return {"http_status": 200, "response_headers": [], "body_complete": True, "transport_error": None}, body
    return transport


class Collection(NoNetwork):
    def run_collect(self, overrides):
        reference = m.reference_config()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError) as ctx:
                m.collect(transport=fake_chain(m.anchors(), reference, overrides), pause=lambda _s: None, output_root=root)
            run, = [p for p in root.iterdir() if p.is_dir()]
            stopped = json.loads((run / "stopped.json").read_text())
            return str(ctx.exception), stopped, len(list(run.glob("*.response.body")))

    def test_stops_on_unreviewed_protocol_version(self):
        def bump(c):
            c = dict(c); c["protocol_version"] = 87; return c
        message, stopped, responses = self.run_collect({(0, "config"): bump})
        self.assertIn("Unreviewed protocol version", message)
        self.assertEqual(stopped["requests_sent"], 5)
        self.assertIsNone(stopped["totals"])
        self.assertEqual(responses, 5)

    def test_stops_on_http_error_without_retry(self):
        message, stopped, responses = self.run_collect({(1, "validators"): lambda _r: "HTTP500"})
        self.assertIn("HTTP 500", message)
        self.assertEqual(stopped["requests_sent"], 7)
        self.assertEqual(responses, 7)

    def test_stops_when_parent_is_not_previous_epoch_end(self):
        def same_epoch(r):
            r["header"]["epoch_id"] = "E100"; return r
        message, _, _ = self.run_collect({(0, "parent"): same_epoch})
        self.assertIn("previous epoch", message)

    def test_refuses_second_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "existing").mkdir()
            with self.assertRaisesRegex(ValueError, "already exists"):
                m.collect(transport=lambda _r: None, pause=lambda _s: None, output_root=Path(tmp))


class SavedResult(NoNetwork):
    def test_result_107_reproduces_offline(self):
        if not m.RESULT.exists():
            self.skipTest("result 107 not yet generated")
        self.assertEqual(m.RESULT.read_bytes(), m.cap.json_bytes(m.validate(m.single_capture())))

    def test_result_107_keeps_unmeasured_components_null(self):
        if not m.RESULT.exists():
            self.skipTest("result 107 not yet generated")
        data = json.loads(m.RESULT.read_text())
        self.assertTrue(all(v is None for v in data["unavailable"].values()))
        self.assertTrue(data["control"]["measured_within_bounds"])
        self.assertEqual(data["network_requests_during_validation"], 0)
        for w in data["weeks"]:
            self.assertLessEqual(int(w["issuance_lower_bound_yocto"]), int(w["issuance_upper_bound_yocto"]))


if __name__ == "__main__":
    unittest.main()


class DashboardIntegration(unittest.TestCase):
    def test_economics_section_and_model_check_respond_to_assumptions(self):
        import sys
        from unittest.mock import patch
        from streamlit.testing.v1 import AppTest
        with patch("socket.socket.connect", side_effect=AssertionError("No source requests")), \
                patch.object(sys, "path", [str(ROOT / "dashboard"), *sys.path]):
            at = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=120).run()
            self.assertFalse(at.exception)
            self.assertIn("Eight-week issuance is bounded; net supply debit offsets little of it", [h.value for h in at.subheader])

            def check():
                frame = next(df.value for df in at.dataframe if "Quantity" in df.value.columns)
                return list(frame["Value"])
            self.assertEqual(check()[2], "$24,679,919,899.17/week")
            self.assertEqual(len(next(df.value for df in at.dataframe if "Issuance upper bound NEAR" in df.value.columns)), 8)
            at.text_input(key="scenario_price_usd_per_near").set_value("10")
            at.button(key="apply_conditional_scenario").click().run()
            self.assertFalse(at.exception)
            self.assertEqual(check()[2], "$49,359,839,798.35/week")
            at.text_input(key="scenario_capture_fraction").set_value("0")
            at.button(key="apply_conditional_scenario").click().run()
            self.assertEqual(check()[2], "Unreachable at zero capture/allocation")
