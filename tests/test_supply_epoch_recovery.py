"""Saved partial-run audit and synthetic two-stage recovery; no real network."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("recovery", ROOT / "analysis/27_recover_supply_epoch_discovery.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
ORIGINAL = ROOT / "results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4"


class EpochRecoveryTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(m.capture.http.client, "HTTPSConnection", side_effect=AssertionError("Network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original_hashes = m.d.pilot.fingerprint([p for p in ORIGINAL.iterdir() if p.is_file()])
        self.addCleanup(self.assert_original_unchanged)

    def assert_original_unchanged(self):
        self.assertEqual(self.original_hashes, m.d.pilot.fingerprint([p for p in ORIGINAL.iterdir() if p.is_file()]))

    def test_saved_partial_run_integrity_counts_coverage_and_failure(self):
        report, resolver = m.audit(ORIGINAL)
        self.assertEqual(report["validated_completed_responses"], 52)
        self.assertEqual(report["completed_response_types"], {"block": 33, "validators": 19})
        self.assertEqual(report["validated_application_boundaries"], 18)
        self.assertEqual(report["saved_AB_controls_observed"], [216877934, 216921134])
        self.assertEqual(report["boundaries_descending"][0]["epoch_height"], 4808)
        self.assertEqual(report["boundaries_descending"][-1]["epoch_height"], 4791)
        self.assertEqual(report["pending_epoch"]["boundary_height"], 216748334)
        self.assertEqual(report["failed_capture"]["metadata"]["response_bytes"], 0)
        self.assertIsNone(report["failed_capture"]["metadata"]["http_status"])
        self.assertEqual(report["remaining_attempt_budget"], 44)
        self.assertTrue(report["stopped_transcript_reproduces"])
        self.assertFalse(report["opening_epoch_reached"])
        self.assertIsNone(report["weekly_issuance_yocto"])
        self.assertEqual(resolver.new_requests, 0)

    def synthetic_responses(self):
        """Counterfactual headers ONLY for transport/replay tests in temp dirs."""
        report, resolver = m.audit(ORIGINAL)
        anchor_payload = m.capture.decode((ORIGINAL / "epoch-051-block.request.json").read_bytes())
        anchor = m.capture.recorded(ORIGINAL, anchor_payload)
        opening, closing = m.d.weekly.validate_week(m.d.WEEK_CAPTURE)["endpoints"]
        pending = report["pending_epoch"]["epoch_id"]
        first_epoch = opening["next_epoch_id"]
        def block(height, block_hash, epoch, successor, prev_height, stamp):
            result = copy.deepcopy(anchor)
            result["header"].update(height=height, hash=block_hash, epoch_id=epoch,
                next_epoch_id=successor, prev_hash=successor, prev_height=prev_height,
                timestamp_nanosec=str(stamp), timestamp=stamp)
            return result
        recovered = block(216748334, closing["hash"], pending, anchor["header"]["next_epoch_id"], 216748333,
                          m.d.START_NS+86400*10**9)
        # Unique synthetic hash: the real closing hash already exists in cache.
        recovered["header"]["hash"] = "11111111111111111111111111111112"
        parent = block(216748333, anchor["header"]["next_epoch_id"], first_epoch, pending, 216748332,
                       m.d.START_NS+(86400-1)*10**9)
        first = block(216600000, "11111111111111111111111111111113", first_epoch, pending, 216599999,
                      m.d.START_NS+101*10**9)
        last_opening = block(216599999, pending, opening["epoch_id"], first_epoch, 216599998,
                             m.d.START_NS+100*10**9)
        metadata = {"epoch_height": 4789, "epoch_start_height": 216600000,
                    "current_validators": [{"account_id": "synthetic.near"}],
                    "validator_reward_paid_prev_epoch": {"treasury.near": "1", "synthetic.near": "2"}}
        items = [("block", {"block_id": 216748334}, recovered),
                 ("block", {"block_id": parent["header"]["hash"]}, parent),
                 ("validators", {"epoch_id": first_epoch}, metadata),
                 ("block", {"block_id": 216600000}, first),
                 ("block", {"block_id": last_opening["header"]["hash"]}, last_opening)]
        return {m.d.semantic_key(method, params): result for method, params, result in items}

    def test_separate_successful_stages_reuse_every_success_and_replay_offline(self):
        responses, calls = self.synthetic_responses(), []
        directory = self.directory / "recovery"
        def transport(raw):
            request = m.capture.decode(raw)
            key = m.d.semantic_key(request["method"], request["params"])
            calls.append(key)
            return {"http_status": 200, "body_complete": True, "transport_error": None}, m.capture.json_bytes({
                "jsonrpc": "2.0", "id": request["id"], "result": responses[key]})
        with redirect_stdout(io.StringIO()):
            m.recover_failed(ORIGINAL, directory, transport=transport, pause=lambda _: None)
            self.assertEqual(len(calls), 1)
            original_request = (ORIGINAL / "epoch-053-block.request.json").read_bytes()
            self.assertEqual((directory / "failed/epoch-053-block.request.json").read_bytes(), original_request)
            partial = m.validate_failed(directory)
            self.assertEqual(partial["cumulative_attempts"], 54)
            self.assertEqual(partial["remaining_attempt_budget"], 43)
            self.assertIsNone(partial["validated_prefix"]["weekly_issuance_yocto"])
            result = m.continue_collection(directory, transport=transport, pause=lambda _: None)
        self.assertEqual(len(calls), 5)
        self.assertEqual(len(set(calls)), 5)
        self.assertEqual(result["remaining_collection_attempts"], 4)
        self.assertEqual(result["cumulative_attempts"], 58)
        self.assertEqual(result["application_epochs"], 20)  # Synthetic completion, not measured history.
        self.assertIsNone(result["independently_identified_weekly_epoch_reward_mint_yocto"])
        self.assertIsNone(result["independently_measured_weekly_net_debit_yocto"])
        self.assertEqual(m.capture.json_bytes(m.validate_remaining(directory)), (directory / "validation.json").read_bytes())
        with self.assertRaises(FileExistsError):
            m.recover_failed(ORIGINAL, directory, transport=transport, pause=lambda _: None)
        with self.assertRaises(FileExistsError):
            m.continue_collection(directory, transport=transport, pause=lambda _: None)

    def test_failed_manual_recovery_stops_once_and_retains_error_body(self):
        directory = self.directory / "failed"
        calls = []
        def transport(raw):
            calls.append(raw)
            return {"http_status": 429, "body_complete": True, "transport_error": None}, b"rate limited"
        with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            m.recover_failed(ORIGINAL, directory, transport=transport, pause=lambda _: None)
        self.assertEqual(len(calls), 1)
        self.assertEqual((directory / "failed/epoch-053-block.response.body").read_bytes(), b"rate limited")
        stopped = m.capture.decode((directory / "failed_stopped.json").read_bytes())
        self.assertEqual(stopped["cumulative_attempts"], 54)
        self.assertIsNone(stopped["weekly_issuance_yocto"])
        with self.assertRaises(ValueError):
            m.validate_failed(directory)

    def test_continuation_failure_counts_prior_attempts_and_never_resets_cap(self):
        directory = self.directory / "continued"
        responses = self.synthetic_responses()
        def initial(raw):
            request = m.capture.decode(raw)
            return {"http_status": 200, "body_complete": True, "transport_error": None}, m.capture.json_bytes({
                "jsonrpc": "2.0", "id": request["id"], "result": responses[m.d.semantic_key(request["method"], request["params"])]})
        with redirect_stdout(io.StringIO()):
            m.recover_failed(ORIGINAL, directory, transport=initial, pause=lambda _: None)
        calls = []
        def fail(raw):
            calls.append(m.capture.decode(raw))
            return {"http_status": None, "body_complete": False, "transport_error": "synthetic timeout"}, b""
        with redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
            m.continue_collection(directory, transport=fail, pause=lambda _: None)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["id"], "epoch-055-block")
        stopped = m.capture.decode((directory / "stopped.json").read_bytes())
        self.assertEqual(stopped["cumulative_attempts"], 55)
        resolver = m.ReuseResolver((), live=True, destination=self.directory, transport=fail, pause=lambda _: None)
        resolver.new_requests = 97
        with self.assertRaisesRegex(ValueError, "Request cap"):
            resolver.get("block", {"block_id": 1})
        self.assertEqual(len(calls), 1)

    def test_tampering_with_even_failed_capture_is_rejected_and_outputs_are_exclusive(self):
        payload = m.capture.decode((ORIGINAL / "epoch-053-block.request.json").read_bytes())
        for suffix in ("request.json", "metadata.json", "response.body"):
            (self.directory / (payload["id"]+"."+suffix)).write_bytes((ORIGINAL / (payload["id"]+"."+suffix)).read_bytes())
        body = self.directory / (payload["id"]+".response.body")
        body.write_bytes(b"altered")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.integrity(self.directory, payload)
        output = self.directory / "keep.json"
        output.write_bytes(b"keep")
        with patch("sys.stderr", io.StringIO()):
            self.assertEqual(m.main(["plan", "--run-dir", str(ORIGINAL), "--output", str(output)]), 1)
        self.assertEqual(output.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
