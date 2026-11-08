"""One-block fixtures only; network constructors are blocked."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("neardata_pilot", ROOT / "analysis/34_neardata_single_block_pilot.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class NeardataPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for target in ("socket.socket", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("Live network forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.canonical = m.controls()[0]
        self.document = {"block": copy.deepcopy(self.canonical), "shards": [
            {"shard_id": c["shard_id"], "chunk": None, "state_changes": [], "receipt_execution_outcomes": []}
            for c in self.canonical["chunks"]]}
        plan = self.root / "plan.json"
        plan.write_bytes(m.c.json_bytes(m.plan()))
        guard = patch.object(m, "PLAN", plan)
        guard.start()
        self.addCleanup(guard.stop)
        self.calls, self.pauses = [], []

    def transport(self, raw):
        self.calls.append(raw)
        return {"http_status": 200, "response_headers": [], "body_complete": True, "transport_error": None}, m.c.json_bytes(self.document)

    def collect(self, transport=None):
        with redirect_stdout(io.StringIO()):
            return m.collect(self.root / "captures", transport=transport or self.transport, pause=self.pauses.append)

    def test_exact_one_get_bytes_and_saved_control_net_debit(self):
        directory = self.collect()
        self.assertEqual(self.calls, [m.request_bytes()])
        self.assertEqual(self.pauses, [65])
        self.assertTrue(self.calls[0].startswith(b"GET /v0/block/216877934 HTTP/1.1\r\n"))
        self.assertNotIn(b"Authorization", self.calls[0])
        self.assertNotIn(b"apiKey", self.calls[0])
        result = m.validate(directory)
        self.assertEqual(result, m.c.decode((directory / "validation.json").read_bytes()))
        self.assertEqual(result["newly_included_chunks"], 5)
        self.assertEqual(result["included_chunk_net_debit_yocto"], "2206853430760200000000")
        self.assertEqual(result["monetary_discrepancy_yocto"], "0")
        self.assertIsNone(result["gross_actual_burn_yocto"])
        self.assertIsNone(result["independent_weekly_net_debit_yocto"])
        self.assertFalse(result["bulk_retention_or_acquisition_established"])

    def test_missing_fields_are_unavailable_not_zero(self):
        for chunk in self.document["block"]["chunks"]:
            chunk.pop("balance_burnt")
        self.document["block"]["header"].pop("chunk_mask")
        result = m.compare(m.c.json_bytes(self.document), self.canonical)
        self.assertIsNone(result["included_chunk_net_debit_yocto"])
        self.assertIsNone(result["monetary_discrepancy_yocto"])
        self.assertEqual(len(result["missing_chunk_monetary_field_shards"]), 10)
        self.assertIn("chunk_mask", result["missing_header_fields"])
        self.document["shards"].pop()
        result = m.compare(m.c.json_bytes(self.document), self.canonical)
        self.assertFalse(result["all_manifest_shards_have_payload_records"])
        self.assertIsNone(result["independent_all_shard_state_receipt_completeness"])

    def test_wrong_identity_partial_manifest_float_money_order_and_duplicates_stop(self):
        mutations = [lambda d: d["block"]["header"].update(hash="wrong"),
                     lambda d: d["block"]["header"].update(total_supply=123),
                     lambda d: d["block"]["chunks"][0].update(balance_burnt=1),
                     lambda d: d["block"]["chunks"][0].update(balance_burnt="NaN"),
                     lambda d: d["block"]["chunks"].reverse(),
                     lambda d: d["block"]["chunks"].pop(),
                     lambda d: d["shards"].append(copy.deepcopy(d["shards"][0]))]
        for mutation in mutations:
            bad = copy.deepcopy(self.document)
            mutation(bad)
            with self.assertRaises(ValueError):
                m.compare(m.c.json_bytes(bad), self.canonical)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            m.compare(b'{"block":{},"block":{}}', self.canonical)

    def test_null_http_auth_redirect_partial_and_oversize_stop_with_no_retry(self):
        for mode in ("null", "auth", "redirect", "partial", "cap"):
            with self.subTest(mode=mode):
                self.calls.clear()
                def transport(raw):
                    meta, body = self.transport(raw)
                    if mode == "null":
                        body = b"null"
                    elif mode == "auth":
                        meta["http_status"] = 403
                    elif mode == "redirect":
                        meta["http_status"] = 302
                        meta["response_headers"] = [["Location", "https://unrequested.example/"]]
                    elif mode == "partial":
                        meta.update(body_complete=False, transport_error="fixture incomplete")
                        body = body[:23]
                    return meta, body
                context = patch.object(m, "MAX_BODY", 10) if mode == "cap" else patch.object(m, "MAX_BODY", m.MAX_BODY)
                with context:
                    # Freeze the fixture plan for the fixed cap in this case.
                    m.PLAN.write_bytes(m.c.json_bytes(m.plan()))
                    with self.assertRaises(ValueError):
                        self.collect(transport)
                self.assertEqual(len(self.calls), 1)
                directory = max((self.root / "captures").iterdir(), key=lambda p: p.stat().st_mtime_ns)
                self.assertTrue((directory / "block-A.response.body").exists())
                self.assertTrue((directory / "stopped.json").exists())
                self.assertFalse((directory / "validation.json").exists())

    def test_tampered_saved_response_is_rejected(self):
        directory = self.collect()
        path = directory / "block-A.response.body"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.validate(directory)


if __name__ == "__main__":
    unittest.main()
