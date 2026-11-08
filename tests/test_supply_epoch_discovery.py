"""Offline variable-length epoch walks, reward offsets and bounded capture tests."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("epoch_discovery", ROOT / "analysis/26_supply_epoch_discovery.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def identifier(number):
    raw = number.to_bytes(32, "big")
    value, result = number, ""
    while value:
        value, remainder = divmod(value, 58)
        result = m.BASE58[remainder] + result
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + result


class EpochDiscoveryTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(m.capture.http.client, "HTTPSConnection", side_effect=AssertionError("Network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def fixture(self, protocol=False):
        e0, e1, e2, e3 = [identifier(n) for n in (1, 2, 3, 4)]
        def block(n, height, epoch, successor, timestamp, prev=None, prev_height=None):
            return {"header": {"hash": identifier(n), "height": height,
                    "prev_hash": identifier(n + 1000) if prev is None else prev,
                    "prev_height": height - 1 if prev_height is None else prev_height,
                    "epoch_id": epoch, "next_epoch_id": successor,
                    "timestamp_nanosec": str(timestamp), "timestamp": timestamp,
                    "total_supply": str(10**33 + height)},
                    "chunks": [{"shard_id": 0}]}
        opening = block(10, 100, e0, e1, m.START_NS - 10**9)
        closing = block(90, 900, e2, e3, m.END_NS - 10**9)
        b1 = block(30, 300, e1, e2, m.START_NS + 3600*10**9, e2, 297)
        p1 = block(3, 297, e0, e1, m.START_NS + 3599*10**9)
        b2 = block(70, 700, e2, e3, m.START_NS + 4*86400*10**9, e3, 694)
        p2 = block(4, 694, e1, e2, m.START_NS + (4*86400-1)*10**9)
        infos = {e1: {"epoch_height": 501, "epoch_start_height": 300,
                     "current_validators": [{"account_id": "validator.near"}],
                     "validator_reward_paid_prev_epoch": {"treasury.near": "1", "validator.near": "5"}},
                 e2: {"epoch_height": 502, "epoch_start_height": 700,
                     "current_validators": [{"account_id": "validator.near"}],
                     "validator_reward_paid_prev_epoch": {"treasury.near": "1", "validator.near": "10"}},
                 e3: {"epoch_height": 503, "epoch_start_height": 1001,
                     "current_validators": [{"account_id": "validator.near"}],
                     "validator_reward_paid_prev_epoch": {"treasury.near": "2", "validator.near": "17"}}}
        resolver = m.Resolver(())
        def register(method, params, result):
            payload = {"jsonrpc": "2.0", "id": identifier(len(resolver.cache)+100), "method": method, "params": params}
            resolver.register(self.directory, payload, result)
        for b in (opening, closing, b1, p1, b2, p2):
            register("block", {"block_id": b["header"]["hash"]}, b)
        for e, info in infos.items():
            register("validators", {"epoch_id": e}, info)
        if protocol:
            config = {"chain_id": "mainnet", "protocol_version": 86,
                      "protocol_treasury_account": "treasury.near", "shard_layout": {"V0": {"num_shards": 1}}}
            for b in (b1, b2):
                register("EXPERIMENTAL_protocol_config", {"block_id": b["header"]["hash"]}, copy.deepcopy(config))
        return resolver, opening, closing, (b1, p1, b2, p2), infos

    def test_plan_saved_inputs_and_known_reuses_without_network(self):
        p = m.plan()
        self.assertEqual(p["max_new_requests"], 97)
        self.assertEqual(p["max_application_epochs"], 32)
        self.assertEqual(p["first_request"]["params"]["epoch_id"], "8sJjEAeKkjwYRCLVGVf5usUt8tPZh3TkWT1YrBp345u8")
        self.assertEqual(m.START_NS, 1789948800000000000)
        self.assertEqual(m.END_NS - m.START_NS, 7*86400*10**9)
        resolver = m.Resolver(m.CACHE_DIRS)
        for target in m.capture.TARGETS.values():
            self.assertEqual(resolver.get("block", {"block_id": target["height"]}), resolver.get("block", {"block_id": target["hash"]}))
        self.assertTrue(resolver.has("validators", {"epoch_id": m.pilot.NEXT_EPOCH}))
        self.assertEqual(resolver.new_requests, 0)

    def test_complete_variable_length_walk_offset_and_unverified_protocol_remain_null(self):
        resolver, opening, closing, blocks, infos = self.fixture()
        r = m.discover(resolver, opening, closing)
        self.assertEqual(r["application_epochs"], 2)
        self.assertEqual([row["height"] for row in r["boundaries_descending"]], [700, 300])
        self.assertEqual([row["recorded_reward_map_sum_yocto"] for row in r["boundaries_descending"]], ["19", "11"])
        self.assertEqual(r["recorded_reward_maps_sum_yocto"], "30")
        self.assertEqual(r["epochs_without_protocol_verification"], 2)
        self.assertIsNone(r["independently_identified_weekly_epoch_reward_mint_yocto"])
        self.assertIsNone(r["implied_net_debit_yocto"])
        for row in r["boundaries_descending"]:
            self.assertEqual(row["reward_response_epoch_height"], row["epoch_height"]+1)
            self.assertEqual(row["rewards_earned_epoch_height"], row["epoch_height"]-1)
            self.assertLess(row["parent_height"], row["height"]-1)  # Legal skipped heights.

    def test_implied_debit_never_becomes_independently_measured_burn(self):
        resolver, opening, closing, _, _ = self.fixture(protocol=True)
        r = m.discover(resolver, opening, closing)
        self.assertEqual(r["independently_identified_weekly_epoch_reward_mint_yocto"], "30")
        self.assertEqual(r["implied_net_debit_yocto"], "-770")
        self.assertIsNone(r["independently_measured_weekly_net_debit_yocto"])
        self.assertIsNone(r["gross_actual_burn_yocto"])
        self.assertIsNone(r["subsidies_yocto"])

    def test_boundary_dates_ids_parents_and_controls_rejected_on_disagreement(self):
        for mode in ("date", "epoch", "parent_height", "parent_epoch", "offset", "controls"):
            resolver, opening, closing, (b1, p1, b2, p2), infos = self.fixture()
            controls = {}
            if mode == "date":
                b1["header"].update(timestamp_nanosec=str(m.START_NS-1), timestamp=m.START_NS-1)
            elif mode == "epoch":
                b2["header"]["epoch_id"] = identifier(999)
            elif mode == "parent_height":
                b2["header"]["prev_height"] += 1
            elif mode == "parent_epoch":
                p2["header"]["next_epoch_id"] = identifier(999)
            elif mode == "offset":
                infos[closing["header"]["next_epoch_id"]]["epoch_height"] = 999
            else:
                controls = {700: {"hash": identifier(999), "timestamp_nanosec": b2["header"]["timestamp_nanosec"]}}
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                m.discover(resolver, opening, closing, controls)

    def test_nonconsecutive_epochs_and_caps_stop_incomplete(self):
        resolver, opening, closing, blocks, infos = self.fixture()
        infos[blocks[0]["header"]["epoch_id"]]["epoch_height"] -= 1
        with self.assertRaisesRegex(ValueError, "Nonconsecutive"):
            m.discover(resolver, opening, closing)
        resolver, opening, closing, _, _ = self.fixture()
        with patch.object(m, "MAX_EPOCHS", 1), self.assertRaisesRegex(ValueError, "cap reached"):
            m.discover(resolver, opening, closing)
        resolver = m.Resolver((), live=True, destination=self.directory)
        with patch.object(m, "MAX_REQUESTS", 0), self.assertRaisesRegex(ValueError, "Request cap"):
            resolver.get("validators", {"epoch_id": identifier(5)})
        self.assertEqual(resolver.new_requests, 0)

    def test_missing_nonfinite_float_and_duplicate_reward_evidence_rejected(self):
        for value in (None, {}, {"treasury.near": "NaN"}, {"treasury.near": 1.0}):
            _, _, _, _, infos = self.fixture()
            info = next(iter(infos.values()))
            info["validator_reward_paid_prev_epoch"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.validator_info(info)
        for raw in (b'{"x":"1","x":"2"}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                m.capture.decode(raw)
        resolver = m.Resolver(())
        with self.assertRaisesRegex(ValueError, "offline validation"):
            resolver.get("validators", {"epoch_id": identifier(1)})

    def test_capture_http_rpc_and_partial_errors_preserve_bytes_and_stop_once(self):
        cases = [(429, True, b'{}'), (200, True, b'{"jsonrpc":"2.0","id":"epoch-001-validators","error":{"code":-32000}}'),
                 (200, False, b'{"jsonrpc":')]
        for index, (status, complete, body) in enumerate(cases):
            output = self.directory / str(index)
            def transport(raw):
                return {"http_status": status, "body_complete": complete, "transport_error": None}, body
            with self.subTest(status=status, complete=complete), patch.object(m, "OUTPUT", output), \
                    patch.object(m.capture.time, "sleep"), redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):
                    m.collect(transport=transport)
                captures = list(output.glob("*"))
                self.assertEqual(len(captures), 1)
                self.assertEqual(len(list(captures[0].glob("*.response.body"))), 1)
                stopped = m.capture.decode((captures[0]/"stopped.json").read_bytes())
                self.assertEqual(stopped["new_requests_attempted"], 1)
                self.assertIsNone(stopped["weekly_issuance_yocto"])
                with self.assertRaisesRegex(ValueError, "Prior discovery attempt"):
                    m.collect(transport=transport)

    def test_successful_capture_and_offline_replay_need_only_three_k_plus_one(self):
        source, opening, closing, _, _ = self.fixture()
        base, fresh = self.directory / "base", self.directory / "fresh"
        base.mkdir()
        fresh.mkdir()
        calls = []
        def transport(raw):
            request = m.capture.decode(raw)
            result = source.get(request["method"], request["params"])
            calls.append((request["method"], request["params"]))
            return {"http_status": 200, "body_complete": True, "transport_error": None}, m.capture.json_bytes({
                "jsonrpc": "2.0", "id": request["id"], "result": result})
        with redirect_stdout(io.StringIO()):
            for index, block in enumerate((opening, closing)):
                payload = {"jsonrpc": "2.0", "id": f"seed-{index}", "method": "block", "params": {"block_id": block["header"]["hash"]}}
                m.capture.capture(base, payload, transport=transport, pause=lambda _: None)
            calls.clear()
            live = m.Resolver((base,), live=True, destination=fresh, transport=transport, pause=lambda _: None)
            result = m.discover(live, opening, closing)
            offline = m.Resolver((base, fresh))
            replay = m.discover(offline, opening, closing)
        self.assertEqual(len(calls), 7)
        self.assertEqual(len({m.semantic_key(method, params) for method, params in calls}), 7)
        self.assertEqual(result, replay)
        self.assertEqual(live.new_requests, 7)
        self.assertEqual(offline.new_requests, 0)

    def test_saved_capture_tampering_and_exclusive_outputs(self):
        resolver, opening, _, _, _ = self.fixture()
        payload = {"jsonrpc": "2.0", "id": "test-block", "method": "block", "params": {"block_id": opening["header"]["hash"]}}
        def transport(raw):
            return {"http_status": 200, "body_complete": True, "transport_error": None}, m.capture.json_bytes({"jsonrpc": "2.0", "id": payload["id"], "result": opening})
        with redirect_stdout(io.StringIO()):
            m.capture.capture(self.directory, payload, transport=transport, pause=lambda _: None)
        self.assertEqual(m.Resolver((self.directory,)).get("block", payload["params"]), opening)
        body = self.directory / "test-block.response.body"
        body.write_bytes(body.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.Resolver((self.directory,))
        path = self.directory / "keep.json"
        path.write_bytes(b"keep")
        with patch("sys.stderr", io.StringIO()):
            self.assertEqual(m.main(["plan", "--output", str(path)]), 1)
        self.assertEqual(path.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
