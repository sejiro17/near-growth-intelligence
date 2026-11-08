"""Offline checks; synthetic rewards/parent supplies are never saved as evidence."""

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("supply_epoch_pilot", ROOT / "analysis/24_supply_epoch_pilot.py")
pilot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pilot)


class SupplyEpochPilotTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(pilot.capture.http.client, "HTTPSConnection",
                             side_effect=AssertionError("Network forbidden in offline tests"))
        guard.start()
        self.addCleanup(guard.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.temporary = Path(temporary.name)
        self.blocks, self.configs, self.witness, _ = pilot.saved_inputs()
        self.block = copy.deepcopy(self.blocks["A"])
        self.config = copy.deepcopy(self.configs["A"])
        self.debit = pilot.chunk_debit(self.block, self.config)
        self.response = {"epoch_start_height": 216921134, "epoch_height": 9000,
                         "current_validators": [{"account_id": pilot.ACCOUNT}],
                         "validator_reward_paid_prev_epoch": {
                             pilot.ACCOUNT: self.witness["change"]["combined_yocto"],
                             "treasury.near": "2", "another-payee.near": "3"}}
        self.reward = pilot.reward_mint(self.response, "treasury.near", self.witness)
        h = self.block["header"]
        self.parent = {"header": {"hash": h["prev_hash"], "height": h["height"] - 1,
            "epoch_id": "synthetic-previous-epoch", "next_epoch_id": h["epoch_id"],
            "timestamp_nanosec": str(int(h["timestamp_nanosec"]) - 1),
            "total_supply": str(int(h["total_supply"]) - int(self.reward["epoch_reward_mint_yocto"])
                                + int(self.debit["net_header_debit_yocto"]))}}

    def test_only_new_chunk_headers_count_exactly(self):
        self.assertEqual(self.debit["newly_included_chunks"], 5)
        self.assertEqual(self.debit["carried_forward_chunks_excluded"], 5)
        self.assertEqual(self.debit["net_header_debit_yocto"], "2206853430760200000000")
        self.assertEqual(self.debit["net_header_debit_near"], "0.002206853430760200000000")
        self.assertEqual(self.debit["excluded_carried_forward_debit_yocto"], "1680380063688100000000")
        stale = next(x for x in self.block["chunks"] if x["height_included"] != 216877934)
        stale["balance_burnt"] = "999999999999999999999999999999"
        self.assertEqual(pilot.chunk_debit(self.block, self.config)["net_header_debit_yocto"],
                         self.debit["net_header_debit_yocto"])

    def test_invalid_money_and_duplicate_json_keys_rejected(self):
        for value in (None, 1, 1.0, "NaN", "Infinity", "-1", "1e24", str(2**128)):
            with self.subTest(value=value), self.assertRaises(ValueError):
                pilot.yocto(value, "test")
        for raw in (b'{"x":"1","x":"2"}', b'{"x":NaN}'):
            with self.assertRaises(ValueError):
                pilot.capture.decode(raw)

    def test_chunk_identity_layout_and_configuration_safeguards(self):
        for field, value in (("shard_id", self.block["chunks"][1]["shard_id"]),
                             ("chunk_hash", self.block["chunks"][1]["chunk_hash"]),
                             ("prev_block_hash", "wrong"), ("balance_burnt", None)):
            bad = copy.deepcopy(self.block)
            bad["chunks"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                pilot.chunk_debit(bad, self.config)
        for kind in ("mask", "version", "subsidy", "layout"):
            bad, config = copy.deepcopy(self.block), copy.deepcopy(self.config)
            if kind == "mask":
                bad["header"]["chunk_mask"][0] = False
            elif kind == "version":
                config["protocol_version"] = 180
            elif kind == "subsidy":
                config["runtime_config"]["wasm_config"]["one_yocto_on_promise"] = False
            else:
                config["shard_layout"]["V3"]["shard_ids"].pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                pilot.chunk_debit(bad, config)

    def test_reward_epoch_offset_and_full_map_sum(self):
        self.assertEqual(pilot.requests()[0]["params"], {"epoch_id": self.blocks["B"]["header"]["epoch_id"]})
        self.assertNotEqual(pilot.requests()[0]["params"]["epoch_id"], self.block["header"]["epoch_id"])
        self.assertEqual(self.reward["reward_payees"], 3)
        self.assertEqual(int(self.reward["epoch_reward_mint_yocto"]),
                         int(self.witness["change"]["combined_yocto"]) + 5)
        self.assertEqual(self.reward["full_reward_map_yocto"], self.response["validator_reward_paid_prev_epoch"])

    def test_unavailable_rewards_wrong_anchor_and_witness_mismatch_stop(self):
        for mode in ("missing", "empty", "treasury_missing", "degenerate", "wrong_anchor", "witness", "float", "float_height"):
            bad = copy.deepcopy(self.response)
            if mode == "missing":
                del bad["validator_reward_paid_prev_epoch"]
            elif mode == "empty":
                bad["validator_reward_paid_prev_epoch"] = {}
            elif mode == "treasury_missing":
                del bad["validator_reward_paid_prev_epoch"]["treasury.near"]
            elif mode == "degenerate":
                bad["validator_reward_paid_prev_epoch"] = {"treasury.near": "2"}
            elif mode == "wrong_anchor":
                bad["epoch_start_height"] = 216877934
            elif mode == "witness":
                bad["validator_reward_paid_prev_epoch"][pilot.ACCOUNT] = "1"
            elif mode == "float":
                bad["validator_reward_paid_prev_epoch"]["treasury.near"] = 2.0
            else:
                bad["epoch_start_height"] = 216921134.0
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                pilot.reward_mint(bad, "treasury.near", self.witness)

    def test_one_yocto_mismatch_is_not_tolerated_or_used_to_fill_components(self):
        report = pilot.compare(self.parent, self.block, self.reward, self.debit)
        self.assertEqual(report["status"], "EXACT_HEADER_IDENTITY_MATCH")
        self.assertEqual(report["arithmetic_discrepancy_yocto"], "0")
        for field in ("gross_actual_burn_yocto", "subsidized_amount_yocto", "gross_issuance_including_subsidy_yocto"):
            self.assertIsNone(report[field])
        self.parent["header"]["total_supply"] = str(int(self.parent["header"]["total_supply"]) + 1)
        bad = pilot.compare(self.parent, self.block, self.reward, self.debit)
        self.assertEqual(bad["status"], "HEADER_IDENTITY_MISMATCH")
        self.assertEqual(bad["arithmetic_discrepancy_yocto"], "-1")
        self.assertEqual(bad["epoch_reward_mint_yocto"], report["epoch_reward_mint_yocto"])

    def test_parent_identity_epoch_and_timestamp_checks(self):
        for key, value in (("hash", "wrong"), ("height", 216877932),
                           ("epoch_id", self.block["header"]["epoch_id"]),
                           ("next_epoch_id", "wrong"),
                           ("timestamp_nanosec", self.block["header"]["timestamp_nanosec"])):
            bad = copy.deepcopy(self.parent)
            bad["header"][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                pilot.compare(bad, self.block, self.reward, self.debit)

    def transport(self, calls, mode=None):
        def fake(raw):
            payload = json.loads(raw)
            calls.append(payload)
            result = self.response if len(calls) == 1 else self.parent
            envelope = {"jsonrpc": "2.0", "id": payload["id"], "result": copy.deepcopy(result)}
            status = 200
            if mode == "http":
                status = 429
            elif mode == "rpc":
                envelope = {"jsonrpc": "2.0", "id": payload["id"], "error": {"message": "unavailable history"}}
            elif mode == "empty":
                envelope["result"]["validator_reward_paid_prev_epoch"] = {}
            elif mode == "identity":
                envelope["id"] = "wrong"
            body = pilot.capture.json_bytes(envelope)
            return {"http_status": status, "body_complete": mode != "partial"}, body
        return fake

    def test_mock_collection_exactly_two_requests_and_revalidates_offline(self):
        calls, sleeps = [], []
        with redirect_stdout(io.StringIO()):
            directory = pilot.collect(self.temporary, self.transport(calls), sleeps.append)
        self.assertEqual(calls, pilot.requests())
        self.assertEqual(sleeps, [65, 65])
        report = pilot.validate(directory)
        self.assertEqual(report["status"], "EXACT_HEADER_IDENTITY_MATCH")
        raw = (directory / "A-parent-block.response.body").read_bytes()
        (directory / "A-parent-block.response.body").write_bytes(raw + b" ")
        with self.assertRaisesRegex(ValueError, "checksum/length"):
            pilot.validate(directory)

    def test_collection_errors_stop_after_first_and_retain_bytes(self):
        for mode in ("http", "rpc", "empty", "identity", "partial"):
            calls = []
            output = self.temporary / mode
            with self.subTest(mode=mode), redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                pilot.collect(output, self.transport(calls, mode), lambda _: None)
            self.assertEqual(len(calls), 1)
            directory, = output.iterdir()
            self.assertTrue((directory / "A-next-epoch-rewards.response.body").is_file())
            self.assertTrue((directory / "A-next-epoch-rewards.metadata.json").is_file())
            self.assertFalse((directory / "A-parent-block.request.json").exists())

    def test_offline_plan_exclusive_output_and_saved_inputs_unchanged(self):
        before = pilot.saved_inputs()[3]
        output = self.temporary / "plan.json"
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(pilot.main(["plan", "--output", str(output)]), 0)
            raw = output.read_bytes()
            self.assertEqual(pilot.main(["plan", "--output", str(output)]), 1)
        self.assertEqual(raw, output.read_bytes())
        self.assertEqual(before, pilot.saved_inputs()[3])
        self.assertEqual(json.loads(raw)["max_requests"], 2)
        self.assertIsNone(json.loads(raw)["epoch_reward_mint_yocto"])

    def test_result63_reproduces_offline_byte_for_byte(self):
        expected = ROOT / "results/63_supply_epoch_boundary_pilot_plan.json"
        self.assertEqual(pilot.capture.json_bytes(pilot.plan()), expected.read_bytes())


if __name__ == "__main__":
    unittest.main()
