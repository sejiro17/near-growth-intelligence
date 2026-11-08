"""Saved 302 audit and synthetic archive hop; live networking is forbidden."""

import copy
import importlib.util
import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("archive_recovery", ROOT / "analysis/35_recover_neardata_archive_redirect.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
ORIGINAL = ROOT / "results/neardata_supply_block_pilot_2026-09-23/20261107T154218Z_8ca556d6bf23"


class ArchiveRedirectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root/"original"
        shutil.copytree(ORIGINAL, self.original)
        self.original_bytes = {p.name: p.read_bytes() for p in self.original.iterdir()}
        for target in ("socket.socket", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("Live network forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.prepared = m.plan(self.original)
        path = self.root/"plan.json"
        path.write_bytes(m.c.json_bytes(self.prepared))
        guard = patch.object(m, "PLAN", path)
        guard.start()
        self.addCleanup(guard.stop)
        self.calls, self.pauses = [], []
        canonical = m.b.controls()[0]
        self.body = m.c.json_bytes({"block": canonical, "shards": [{"shard_id": x["shard_id"], "chunk": None,
                  "state_changes": [], "receipt_execution_outcomes": []} for x in canonical["chunks"]]})

    def transport(self, raw):
        self.calls.append(raw)
        return {"http_status": 200, "response_headers": [], "body_complete": True, "transport_error": None}, self.body

    def recover(self, transport=None, label="recovery"):
        with redirect_stdout(io.StringIO()):
            return m.recover(self.original, output_root=self.root/label, transport=transport or self.transport, pause=self.pauses.append)

    def assert_original_unchanged(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.original.iterdir()}, self.original_bytes)

    def test_saved_302_is_valid_complete_routing_response(self):
        r = self.prepared
        self.assertEqual(r["original_http_status"], 302)
        self.assertEqual(r["original_response_bytes"], 0)
        self.assertEqual(r["allowed_destinations"], [m.DESTINATION])
        self.assertEqual(r["additional_request_count"], 1)
        self.assertEqual(r["maximum_response_hops_including_original"], 2)
        self.assertEqual(r["response_body_cap_bytes"], 32*1024*1024)
        self.assertEqual(r["connect_timeout_seconds"], 15)
        self.assertEqual(r["request_timeout_seconds"], 60)
        self.assert_original_unchanged()

    def test_only_verified_https_url_without_credentials_or_changed_block(self):
        self.assertEqual(m.verified_url(m.DESTINATION), m.DESTINATION)
        invalid = ["http://a3.mainnet.neardata.xyz/v0/block/216877934",
                   "https://a3.mainnet.neardata.xyz.evil.example/v0/block/216877934",
                   "https://a4.mainnet.neardata.xyz/v0/block/216877934",
                   "https://user:password@a3.mainnet.neardata.xyz/v0/block/216877934",
                   "https://a3.mainnet.neardata.xyz:443/v0/block/216877934",
                   m.DESTINATION+"?apiKey=secret", m.DESTINATION+"#fragment",
                   m.DESTINATION.replace("216877934", "216877935"),
                   "/v0/block/216877934", "//a3.mainnet.neardata.xyz/v0/block/216877934",
                   m.DESTINATION+"\r\nAuthorization: secret"]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.verified_url(value)
        with self.assertRaisesRegex(ValueError, "duplicate Location"):
            m.location([["Location", m.DESTINATION], ["location", m.DESTINATION]])

    def test_one_archive_get_two_preserved_hops_and_no_repeated_invocation(self):
        directory = self.recover()
        self.assertEqual(len(self.calls), 1)
        raw = self.calls[0]
        self.assertIn(b"Host: a3.mainnet.neardata.xyz\r\n", raw)
        for forbidden in (b"Authorization:", b"Cookie:", b"Referer:", b"apiKey="):
            self.assertNotIn(forbidden, raw)
        self.assertEqual(self.pauses, [65])
        for name, body in self.original_bytes.items():
            self.assertEqual((directory/"hop-00-original"/name).read_bytes(), body)
        report = m.validate(directory)
        self.assertEqual(report, m.c.decode((directory/"validation.json").read_bytes()))
        self.assertEqual(report["included_chunk_net_debit_yocto"], "2206853430760200000000")
        self.assertIsNone(report["gross_actual_burn_yocto"])
        self.assertIsNone(report["independent_weekly_net_debit_yocto"])
        with self.assertRaises(FileExistsError):
            self.recover()
        self.assertEqual(len(self.calls), 1)
        self.assert_original_unchanged()

    def test_further_redirect_is_saved_and_never_followed(self):
        def redirected(raw):
            meta, _ = self.transport(raw)
            meta.update(http_status=302, response_headers=[["Location", "https://unverified.example/secret"]])
            return meta, b""
        with self.assertRaisesRegex(ValueError, "Archive HTTP 302"):
            self.recover(redirected)
        self.assertEqual(len(self.calls), 1)
        directory = self.root/"recovery/original_recovery_01"
        self.assertTrue((directory/"stopped.json").exists())
        self.assertFalse((directory/"validation.json").exists())
        meta = m.c.decode((directory/"hop-01-archive/block-A.metadata.json").read_bytes())
        self.assertEqual(meta["response_headers"], [["Location", "https://unverified.example/secret"]])
        self.assert_original_unchanged()

    def test_transport_auth_and_null_failures_stop_without_retries(self):
        for mode in ("partial", "auth", "null"):
            with self.subTest(mode=mode):
                self.calls.clear()
                def failed(raw):
                    meta, body = self.transport(raw)
                    if mode == "partial":
                        meta.update(body_complete=False, transport_error="fixture incomplete")
                        body = body[:11]
                    elif mode == "auth":
                        meta["http_status"] = 403
                    else:
                        body = b"null"
                    return meta, body
                with self.assertRaises(ValueError):
                    self.recover(failed, label=mode)
                self.assertEqual(len(self.calls), 1)
                directory = self.root/mode/"original_recovery_01"
                self.assertTrue((directory/"hop-01-archive/block-A.response.body").exists())
                self.assertTrue((directory/"stopped.json").exists())
                self.assert_original_unchanged()

    def test_changed_original_checksums_and_wrong_location_prevent_requests(self):
        path = self.original/"block-A.response.body"
        path.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.recover()
        self.assertEqual(self.calls, [])
        path.write_bytes(self.original_bytes[path.name])
        path = self.original/"block-A.metadata.json"
        meta = m.c.decode(path.read_bytes())
        for pair in meta["response_headers"]:
            if pair[0].lower() == "location":
                pair[1] = "https://unverified.example/v0/block/216877934"
        path.write_bytes(m.c.json_bytes(meta))
        with self.assertRaisesRegex(ValueError, "Unverified destination"):
            self.recover()
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
