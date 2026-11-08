"""Offline partial-run audit and synthetic four-request recovery; no live RPC."""

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
SPEC = importlib.util.spec_from_file_location("wallet_recovery", ROOT / "analysis/32_recover_wallet_historical_balances.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)
ORIGINAL = ROOT / "results/three_wallet_native_balances_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a"


class WalletBalanceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "original"
        shutil.copytree(ORIGINAL, self.original)
        self.original_bytes = {p.name: p.read_bytes() for p in self.original.iterdir()}
        for target in ("socket.socket", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("Live networking forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        self.prepared = m.audit(self.original)
        path = self.root / "recovery_plan.json"
        path.write_bytes(m.c.json_bytes(self.prepared))
        guard = patch.object(m, "PLAN", path)
        guard.start()
        self.addCleanup(guard.stop)
        self.calls, self.pauses = [], []

    def transport(self, raw):
        payload = m.c.decode(raw)
        self.calls.append(payload)
        boundary = payload["id"].split("-")[0]
        target = m.b.BOUNDARIES[boundary]
        body = m.c.json_bytes({"jsonrpc": "2.0", "id": payload["id"], "result": {
            "block_hash": target["hash"], "block_height": target["height"],
            "amount": "7000000000000000000000001", "locked": "1", "storage_usage": 200,
            "code_hash": "11111111111111111111111111111111"}})
        return {"http_status": 200, "response_headers": [], "body_complete": True, "transport_error": None}, body

    def recover(self, transport=None):
        with redirect_stdout(io.StringIO()):
            return m.recover(self.original, output_root=self.root / "recovery", transport=transport or self.transport, pause=self.pauses.append)

    def assert_original_unchanged(self):
        self.assertEqual({p.name: p.read_bytes() for p in self.original.iterdir()}, self.original_bytes)

    def test_partial_capture_audit_including_failed_bytes_and_exact_states(self):
        r = self.prepared
        self.assertEqual(r["validated_request_ids"], ["opening-1", "opening-2"])
        self.assertEqual(r["recovery_request_count"], 4)
        self.assertEqual([i["request"]["id"] for i in r["pending_requests"]], ["opening-3", "closing-1", "closing-2", "closing-3"])
        self.assertEqual(r["maximum_combined_attempts"], 7)
        self.assertEqual(r["unique_account_boundary_pairs"], 6)
        self.assertIsNone(r["complete_stock_flow_comparison"])
        self.assertEqual(r["validated_states"][0]["amount"], "1610269316440681058391094897654")
        self.assertEqual(r["validated_states"][1]["locked"], "0")
        self.assertEqual(r["failed_capture"]["transport"]["response_bytes"], 0)
        self.assertIn("RemoteDisconnected", r["failed_capture"]["transport"]["transport_error"])
        self.assert_original_unchanged()

    def test_only_missing_requests_pacing_complete_comparison_and_no_overwrite(self):
        directory = self.recover()
        self.assertEqual(self.calls, [i["request"] for i in self.prepared["pending_requests"]])
        self.assertEqual(self.pauses, [65]*4)
        self.assertFalse((directory / "opening-1.response.body").exists())
        r = m.validate(directory)
        self.assertEqual(r, m.c.decode((directory / "validation.json").read_bytes()))
        self.assertEqual(len(r["accounts"]), 3)
        self.assertEqual(r["reused_request_ids"], ["opening-1", "opening-2"])
        self.assertIsNone(r["verified_revenue_yocto"])
        self.assertIsNone(r["actual_supply_burn_yocto"])
        self.assertTrue(all(x["attributed_fees_yocto"] is None for x in r["accounts"]))
        with self.assertRaises(FileExistsError):
            self.recover()
        self.assertEqual(len(self.calls), 4)
        self.assert_original_unchanged()

    def test_recovery_failure_stops_after_one_and_preserves_both_attempts(self):
        def failed(raw):
            meta, body = self.transport(raw)
            meta.update(body_complete=False, transport_error="fixture disconnected", http_status=None)
            return meta, body[:13]
        with self.assertRaisesRegex(ValueError, "transport"):
            self.recover(failed)
        self.assertEqual([p["id"] for p in self.calls], ["opening-3"])
        directory = self.root / "recovery/original_recovery_01"
        self.assertTrue((directory / "opening-3.response.body").exists())
        self.assertFalse((directory / "validation.json").exists())
        with self.assertRaisesRegex(ValueError, "Incomplete/unexpected"):
            m.validate(directory)
        self.assert_original_unchanged()

    def test_failed_capture_checksums_and_changed_original_are_not_silently_recollected(self):
        path = self.original / "opening-3.response.body"
        path.write_bytes(b"changed failed evidence")
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.recover()
        self.assertEqual(self.calls, [])
        path.write_bytes(self.original_bytes[path.name])
        directory = self.recover()
        # A previously valid original response may not be substituted after recovery.
        path = self.original / "opening-1.response.body"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.validate(directory)

    def test_extra_missing_and_inconsistent_prefix_files_are_rejected(self):
        path = self.original / "extra.json"
        path.write_text("{}")
        with self.assertRaisesRegex(ValueError, "unexpected original"):
            m.audit(self.original)
        path.unlink()
        stopped_path = self.original / "stopped.json"
        stopped = m.c.decode(stopped_path.read_bytes())
        bad = copy.deepcopy(stopped)
        bad["request_id"] = "closing-3"
        stopped_path.write_bytes(m.c.json_bytes(bad))
        with self.assertRaisesRegex(ValueError, "Stopped request"):
            m.audit(self.original)
        stopped_path.write_bytes(self.original_bytes[stopped_path.name])
        (self.original / "opening-1.metadata.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing/unexpected"):
            m.audit(self.original)


if __name__ == "__main__":
    unittest.main()
