"""Offline fixtures only. Live HTTPS construction is forbidden by these tests."""

import copy
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "canonical_collector", ROOT / "analysis/11_collect_canonical_validator_evidence.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class CanonicalCollectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.saved, cls.known = collector.saved_accounts(collector.DIAGNOSTIC.read_bytes())

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.calls, self.pauses = [], []
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        guard = patch.object(collector.http.client, "HTTPSConnection",
                             side_effect=AssertionError("Live networking forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def block(self, label):
        target = collector.TARGETS[label]
        timestamp = (date(2026, 9, 23) - date(1970, 1, 1)).days * 86400 * 10**9
        return {"header": {"height": target["height"], "hash": target["hash"],
                "prev_hash": target["parent"], "total_supply": "1307081318396302700000000000000000",
                "timestamp_nanosec": str(timestamp), "chunk_mask": [True]},
                "chunks": [{"shard_id": 0, "chunk_hash": "fixture-chunk",
                            "height_created": target["height"], "height_included": target["height"]}]}

    def effects(self, label):
        return {"block_hash": collector.TARGETS[label]["hash"],
                "changes": [{"type": "account_touched", "account_id": x} for x in sorted(self.saved)]}

    def changes(self, label):
        return {"block_hash": collector.TARGETS[label]["hash"], "changes": [
            {"type": "account_update", "cause": {"type": "validator_accounts_update"},
             "change": {"account_id": x, "amount": "1000000000000000000000001",
                        "locked": "123456789012345678901234567890"}} for x in sorted(self.saved)]}

    def transport(self, raw):
        payload = collector.decode(raw)
        self.calls.append(payload)
        label, kind = payload["id"].split("-")
        if kind == "block":
            result = self.block(label)
        elif kind == "protocol":
            result = {"chain_id": "mainnet", "protocol_version": 86,
                      "shard_layout": {"V3": {"shard_ids": [0]}}}
        elif kind == "effects":
            result = self.effects(label)
        else:
            self.assertEqual(kind, "changes")
            result = self.changes(label)
        body = collector.json_bytes({"jsonrpc": "2.0", "id": payload["id"], "result": result})
        return {"http_status": 200, "response_headers": [["Content-Type", "application/json"]],
                "body_complete": True, "transport_error": None}, body

    def collect(self):
        return collector.collect_stage1(self.root, transport=self.transport, pause=self.pauses.append)

    def test_two_explicit_stages_exact_request_counts_and_no_witnesses(self):
        run = self.collect()
        self.assertEqual(len(self.calls), 6)
        self.assertFalse((run / "stage2").exists())
        unions, _, _ = collector.validate_stage1(run)
        self.assertEqual(unions, {"A": sorted(self.saved), "B": sorted(self.saved)})
        report = collector.collect_stage2(run, self.transport, self.pauses.append)
        self.assertEqual(len(self.calls), 8)
        self.assertEqual([p["method"] for p in self.calls[-2:]], ["changes", "changes"])
        self.assertEqual(self.pauses, [65] * 8)
        self.assertEqual(report["validator_account_counts"], {"A": 462, "B": 462})
        self.assertIsNone(report["independently_measured_issuance"])
        self.assertIsNone(report["independently_measured_actual_burn"])
        for label in collector.TARGETS:
            path = run / "stage2" / f"{label}-changes.response.body"
            raw = path.read_bytes()
            self.assertIn(b'"1000000000000000000000001"', raw)
            result = collector.decode(raw)["result"]
            self.assertEqual([x["change"]["account_id"] for x in result["changes"]], sorted(self.saved))
        self.assertEqual((run / "diagnostic_input.json").read_bytes(), collector.DIAGNOSTIC.read_bytes())

    def test_union_adds_touched_accounts_and_preserves_saved_population(self):
        result = collector.account_union({"new-touched.near", next(iter(self.saved))}, self.saved)
        self.assertEqual(result, sorted(self.saved | {"new-touched.near"}))
        self.assertEqual(len(result), 463)
        with self.assertRaisesRegex(ValueError, "Missing touched"):
            collector.account_union(set(), self.saved)

    def test_wrong_block_parent_date_or_manifest_rejected(self):
        for field, value in (("height", 1), ("hash", "wrong"), ("prev_hash", "wrong")):
            with self.subTest(field=field):
                result = self.block("A")
                result["header"][field] = value
                with self.assertRaisesRegex(ValueError, "Wrong block"):
                    collector.validate_block(result, collector.TARGETS["A"])
        result = self.block("A")
        result["chunks"].append(copy.deepcopy(result["chunks"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate shard"):
            collector.validate_block(result, collector.TARGETS["A"])
        result = self.block("A")
        result["header"]["timestamp_nanosec"] = "0"
        with self.assertRaisesRegex(ValueError, "Wrong block date"):
            collector.validate_block(result, collector.TARGETS["A"])

    def test_historical_protocol_and_layout_must_be_reviewed_and_consistent(self):
        for result in (
            {"chain_id": "testnet", "protocol_version": 86, "shard_layout": {"V3": {"shard_ids": [0]}}},
            {"chain_id": "mainnet", "protocol_version": 88, "shard_layout": {"V3": {"shard_ids": [0]}}},
            {"chain_id": "mainnet", "protocol_version": 86, "shard_layout": {"V3": {"shard_ids": [0, 1]}}},
        ):
            with self.subTest(result=result), self.assertRaises(ValueError):
                collector.validate_protocol(result, {0})

    def test_empty_and_partial_effects_stop(self):
        result = self.effects("A")
        result["changes"] = []
        with self.assertRaisesRegex(ValueError, "Empty effects"):
            collector.touched_accounts(result, collector.TARGETS["A"], self.known["A"])
        result["changes"] = [{"type": "account_touched", "account_id": "other.near"}]
        with self.assertRaisesRegex(ValueError, "partial history"):
            collector.touched_accounts(result, collector.TARGETS["A"], self.known["A"])

    def test_json_rpc_errors_ids_duplicate_keys_nonfinite_and_truncation_rejected(self):
        payload = collector.request("A", "effects")
        cases = [
            b'{"jsonrpc":"2.0","id":"A-effects","error":{"code":-32601,"message":"Method not found"}}',
            b'{"jsonrpc":"2.0","id":"wrong","result":{}}',
            b'{"id":1,"id":2}', b'{"value":NaN}', b'{"result":',
        ]
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                collector.envelope(raw, payload)

    def test_http_errors_redirects_and_partial_bytes_retained_without_retry(self):
        for status, complete, error in ((500, True, None), (302, True, None),
                                        (200, False, "TimeoutError")):
            directory = self.root / str(status) / str(complete)
            directory.mkdir(parents=True)
            calls = []
            body = b'raw error or partial response\x00\xff'
            def fail(raw):
                calls.append(raw)
                return {"http_status": status, "response_headers": [], "body_complete": complete,
                        "transport_error": error}, body
            with self.assertRaises(ValueError):
                collector.capture(directory, collector.request("A", "block"), fail, self.pauses.append)
            self.assertEqual(len(calls), 1)
            self.assertEqual((directory / "A-block.response.body").read_bytes(), body)
            meta = collector.decode((directory / "A-block.metadata.json").read_bytes())
            self.assertEqual(meta["response_sha256"], collector.sha256(body))
            self.assertEqual(meta["endpoint"], collector.ENDPOINT)

    def test_transport_detects_short_content_length_without_live_network(self):
        response = Mock()
        response.status, response.version, response.reason = 200, 11, "OK"
        response.getheaders.return_value = [("Content-Length", "100")]
        response.isclosed.return_value = False
        response.read1.side_effect = [b'{"partial":', b'']
        response.length = 89
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(collector.http.client, "HTTPSConnection", return_value=connection) as factory:
            meta, body = collector.fetch(b'{"jsonrpc":"2.0"}')
        factory.assert_called_once()
        self.assertEqual(factory.call_args.args[0], collector.HOST)
        connection.connect.assert_called_once()
        connection.request.assert_called_once()
        self.assertFalse(meta["body_complete"])
        self.assertIn("Truncated Content-Length", meta["transport_error"])
        self.assertEqual(body, b'{"partial":')
        response.close.assert_called_once()
        connection.close.assert_called_once()

    def test_transport_accepts_complete_body_when_response_closes_after_last_read(self):
        response = Mock()
        response.status, response.version, response.reason = 200, 11, "OK"
        response.getheaders.return_value = [("Content-Length", "2")]
        response.isclosed.side_effect = [False, True]
        response.read1.return_value = b'{}'
        response.length = 0
        connection = Mock()
        connection.getresponse.return_value = response
        with patch.object(collector.http.client, "HTTPSConnection", return_value=connection):
            meta, body = collector.fetch(b'{}')
        self.assertTrue(meta["body_complete"])
        self.assertIsNone(meta["transport_error"])
        self.assertEqual(body, b'{}')
        response.read1.assert_called_once()

    def test_first_invalid_response_stops_stage1(self):
        def wrong(raw):
            self.calls.append(collector.decode(raw))
            return {"http_status": 200, "body_complete": True, "transport_error": None}, b'{}'
        with self.assertRaises(ValueError):
            collector.collect_stage1(self.root, transport=wrong, pause=self.pauses.append)
        self.assertEqual(len(self.calls), 1)

    def test_stage2_requires_six_valid_saved_responses_before_network(self):
        run = self.collect()
        (run / "stage1/B-effects.response.body").write_bytes(b'{}')
        before = len(self.calls)
        with self.assertRaisesRegex(ValueError, "checksum"):
            collector.collect_stage2(run, self.transport, self.pauses.append)
        self.assertEqual(len(self.calls), before)
        self.assertFalse((run / "stage2").exists())

    def test_evidence_is_never_overwritten_or_stage_resumed(self):
        run = self.collect()
        collector.collect_stage2(run, self.transport, self.pauses.append)
        before = len(self.calls)
        with self.assertRaises(FileExistsError):
            collector.collect_stage2(run, self.transport, self.pauses.append)
        self.assertEqual(len(self.calls), before)
        path = self.root / "existing"
        path.write_bytes(b"keep")
        with self.assertRaises(FileExistsError):
            collector.write_new(path, b"replace")
        self.assertEqual(path.read_bytes(), b"keep")

    def test_empty_partial_wrong_hash_or_inexact_monetary_changes_rejected(self):
        target = collector.TARGETS["A"]
        result = self.changes("A")
        cases = []
        empty = copy.deepcopy(result); empty["changes"] = []; cases.append(empty)
        partial = copy.deepcopy(result); partial["changes"].pop(); cases.append(partial)
        wrong = copy.deepcopy(result); wrong["block_hash"] = "wrong"; cases.append(wrong)
        inexact = copy.deepcopy(result); inexact["changes"][0]["change"]["amount"] = 1; cases.append(inexact)
        for value in cases:
            with self.subTest(case=value.get("block_hash")), self.assertRaises(ValueError):
                collector.validate_changes(value, target, self.saved, self.saved, self.known["A"])

    def test_offline_cli_validation_never_calls_transport(self):
        run = self.collect()
        with patch.object(collector, "fetch", side_effect=AssertionError("Network forbidden")):
            self.assertEqual(collector.main(["validate-stage1", "--run-dir", str(run)]), 0)

    def test_changed_diagnostic_is_rejected_before_capture(self):
        path = self.root / "changed.json"
        path.write_bytes(collector.DIAGNOSTIC.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            collector.collect_stage1(self.root, diagnostic=path,
                                     transport=self.transport, pause=self.pauses.append)
        self.assertEqual(self.calls, [])

    def test_saved_timestamp_metadata_is_validated_offline(self):
        run = self.collect()
        path = run / "stage1/A-block.metadata.json"
        meta = collector.decode(path.read_bytes())
        meta["finished_at"] = "2020-01-01T00:00:00+00:00"
        path.write_bytes(collector.json_bytes(meta))
        with self.assertRaisesRegex(ValueError, "retrieval timestamps"):
            collector.validate_stage1(run)


if __name__ == "__main__":
    unittest.main()
