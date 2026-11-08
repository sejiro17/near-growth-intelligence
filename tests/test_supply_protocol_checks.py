"""Offline historical-config targeting, monetary checks and scope safeguards."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("protocol_checks", ROOT / "analysis/28_supply_protocol_checks.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SupplyProtocolChecksTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(m.capture.http.client, "HTTPSConnection", side_effect=AssertionError("Network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def reference(self):
        report, resolver = m.saved()
        config = resolver.get(m.METHOD, {"block_id": m.capture.TARGETS["A"]["hash"]})
        block = resolver.get("block", {"block_id": m.capture.TARGETS["A"]["hash"]})
        return config, block

    def test_plan_exact_missing_targets_reuses_AB_and_ignores_advertisements(self):
        p = m.plan()
        self.assertEqual(len(p["requests"]), 21)
        self.assertEqual(p["reused_protocol_epochs"], [4793, 4794])
        self.assertEqual(len({r["hash"] for r in p["requests"]}), 21)
        self.assertEqual(p["requests"][0]["epoch_height"], 4786)
        self.assertEqual(p["requests"][-1]["epoch_height"], 4808)
        for row in p["requests"]:
            self.assertEqual(row["request"]["method"], m.METHOD)
            self.assertEqual(row["request"]["params"], {"block_id": row["hash"]})
        config, block = self.reference()
        block["header"]["latest_protocol_version"] = 999
        self.assertEqual(m.validate_configuration(config, block, config)["active_protocol_version"], 86)

    def test_exact_status_and_no_independent_weekly_debit_or_burn(self):
        s = m.status()
        self.assertEqual(s["recorded_reward_maps_near"], "618436.074970164323861118656646")
        self.assertEqual(s["protocol_validated_mint_subtotal_near"], "54916.738274594577977943352544")
        self.assertEqual(s["observed_boundary_header_debits_near"], "0.104122811923337500000000")
        self.assertEqual(s["conditional_reward_map_implied_weekly_net_debit_near"], "6880.100734646470923400000000")
        self.assertEqual(s["protocol_checks_missing"], 21)
        self.assertIsNone(s["protocol_validated_weekly_epoch_reward_mint_yocto"])
        self.assertIsNone(s["independently_measured_weekly_net_debit_yocto"])
        self.assertIsNone(s["gross_actual_burn_yocto"])
        self.assertIsNone(s["subsidies_yocto"])

    def test_unknown_active_versions_layout_or_runtime_changes_stop(self):
        reference, block = self.reference()
        for key, value in (("protocol_version", 87), ("protocol_version", 86.0),
                           ("protocol_treasury_account", "another.near"), ("max_inflation_rate", [1, 20])):
            changed = copy.deepcopy(reference)
            changed[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                m.validate_configuration(changed, block, reference)
        changed = copy.deepcopy(reference)
        changed["runtime_config"]["wasm_config"]["one_yocto_on_promise"] = False
        with self.assertRaises(ValueError):
            m.validate_configuration(changed, block, reference)

    def test_missing_duplicate_float_chunk_fields_and_broken_identity(self):
        _, block = self.reference()
        for mode in ("duplicate", "float", "mask"):
            changed = copy.deepcopy(block)
            if mode == "duplicate":
                changed["chunks"][1] = copy.deepcopy(changed["chunks"][0])
            elif mode == "float":
                changed["chunks"][0]["balance_burnt"] = 1.0
            else:
                changed["header"]["chunk_mask"].pop()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                m.net_header_debit(changed)
        report, resolver = m.saved()
        changed = resolver.get("block", {"block_id": report["boundaries_descending"][0]["hash"]})
        chunk = next(c for c in changed["chunks"] if c["height_included"] == changed["header"]["height"])
        chunk["balance_burnt"] = str(int(chunk["balance_burnt"])+1)
        with self.assertRaisesRegex(ValueError, "monetary identity"):
            m.status(report, resolver)

    def test_mock_21_request_capture_replay_validates_mint_without_claiming_burn(self):
        reference, _ = self.reference()
        calls = []
        def transport(raw):
            q = m.capture.decode(raw)
            calls.append(q)
            return {"http_status": 200, "body_complete": True, "transport_error": None}, m.configuration_bytes({
                "jsonrpc": "2.0", "id": q["id"], "result": copy.deepcopy(reference)})
        with patch.object(m, "OUTPUT", self.directory / "mock"), redirect_stdout(io.StringIO()):
            directory = m.collect(transport=transport, pause=lambda _: None)
            self.assertEqual(len(calls), 21)
            self.assertEqual(len({q["params"]["block_id"] for q in calls}), 21)
            result = m.validate(directory)
            self.assertEqual(result["protocol_checks_missing"], 0)
            self.assertEqual(result["protocol_validated_weekly_epoch_reward_mint_yocto"], result["recorded_reward_maps_yocto"])
            self.assertIsNone(result["independently_measured_weekly_net_debit_yocto"])
            self.assertIsNone(result["gross_actual_burn_yocto"])
            self.assertEqual(m.capture.json_bytes(result), (directory / "validation.json").read_bytes())
            with self.assertRaisesRegex(ValueError, "Prior protocol attempt"):
                m.collect(transport=transport, pause=lambda _: None)

    def test_failed_transport_stops_after_one_and_no_output_overwrite(self):
        calls = []
        def transport(raw):
            calls.append(raw)
            return {"http_status": None, "body_complete": False, "transport_error": "synthetic timeout"}, b""
        with patch.object(m, "OUTPUT", self.directory / "failed"), redirect_stdout(io.StringIO()):
            with self.assertRaises(ValueError):
                m.collect(transport=transport, pause=lambda _: None)
        self.assertEqual(len(calls), 1)
        stopped = next(self.directory.rglob("stopped.json"))
        self.assertIsNone(m.capture.decode(stopped.read_bytes())["validated_weekly_epoch_reward_mint_yocto"])
        target = self.directory / "keep.json"
        target.write_bytes(b"keep")
        with patch("sys.stderr", io.StringIO()):
            self.assertEqual(m.main(["plan", "--output", str(target)]), 1)
        self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
