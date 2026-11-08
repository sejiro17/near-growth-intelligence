"""Offline metadata completeness and bounded weekly-endpoint safeguards."""

import copy
import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("supply_inventory", ROOT / "analysis/25_supply_source_inventory.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class SupplySourceInventoryTests(unittest.TestCase):
    def setUp(self):
        guard = patch.object(m.capture.http.client, "HTTPSConnection", side_effect=AssertionError("Network forbidden"))
        guard.start()
        self.addCleanup(guard.stop)

    def rows(self):
        return m.capture.decode(m.SOURCE.read_bytes())

    def test_saved_schema_completeness_types_and_unavailability(self):
        r = m.inventory()
        self.assertEqual(r["export_rows"], 21)
        self.assertEqual(r["row_counts"], {"COLUMN": 20, "SUMMARY": 1})
        self.assertEqual(r["fields"]["blocks"]["total_supply"]["data_type"], "FLOAT64")
        self.assertEqual(r["fields"]["blocks"]["prev_block_hash"]["data_type"], "STRING")
        self.assertEqual(r["fields"]["chunks"]["block_date"]["is_partitioning_column"], "YES")
        self.assertNotIn("balance_burnt", r["fields"]["chunks"])
        self.assertNotIn("epoch_id", r["fields"]["blocks"])
        self.assertIsNone(r["independent_epoch_mint_yocto"])
        self.assertIsNone(r["gross_actual_burn_yocto"])
        self.assertTrue(r["sql43_comparison"]["byte_identical"])

    def test_truncation_duplicates_and_candidate_table_coverage(self):
        rows = self.rows()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            m.validate(m.capture.json_bytes(rows[:-1]))
        rows[-1] = copy.deepcopy(rows[-2])
        with self.assertRaisesRegex(ValueError, "Duplicate metadata"):
            m.validate(m.capture.json_bytes(rows))
        rows = self.rows()
        s = m.capture.decode(rows[0]["metadata_summary"])
        s["visible_tables"].append("validator_rewards")
        s["visible_tables"].sort()
        rows[0]["metadata_summary"] = m.capture.json_bytes(s).decode()
        with self.assertRaisesRegex(ValueError, "Candidate selection"):
            m.validate(m.capture.json_bytes(rows))

    def test_ambiguous_json_and_invalid_field_flags_rejected(self):
        for raw in (b'[{"row_kind":"COLUMN","row_kind":"SUMMARY"}]', b'[NaN]'):
            with self.assertRaises(ValueError):
                m.validate(raw)
        rows = self.rows()
        rows[1]["is_partitioning_column"] = "MAYBE"
        with self.assertRaisesRegex(ValueError, "top-level"):
            m.validate(m.capture.json_bytes(rows))

    def test_plan_uses_saved_ids_and_exactly_two_requests(self):
        p = m.plan()
        self.assertEqual(p["request_count"], 2)
        self.assertEqual([t["height"] for t in p["targets"]], [216553375, 217555961])
        for t in p["targets"]:
            self.assertEqual(t["request"]["method"], "block")
            self.assertEqual(t["request"]["params"], {"block_id": t["hash"]})

    def endpoint(self, target):
        p = ROOT / "results/canonical_rpc_2026-09-23/20261106T133436Z_2e1218e30fbc/stage1/A-block.response.body"
        result = copy.deepcopy(m.capture.decode(p.read_bytes())["result"])
        h = result["header"]
        offset = target["height"] - h["height"]
        h.update(hash=target["hash"], height=target["height"])
        stamp = datetime.strptime(target["saved_timestamp_utc"], "%Y-%m-%d %H:%M:%S.%f UTC").replace(tzinfo=timezone.utc)
        delta = stamp - datetime(1970, 1, 1, tzinfo=timezone.utc)
        h["timestamp_nanosec"] = str(((delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds) * 1000)
        for c in result["chunks"]:
            c["height_created"] += offset
            c["height_included"] += offset
        return result

    def test_wrong_identity_timestamp_money_and_chunk_manifest_stop(self):
        target = m.plan()["targets"][0]
        good = self.endpoint(target)
        r = m.validate_endpoint(good, target)
        self.assertFalse(r["expected_protocol_shard_coverage_verified"])
        delayed = copy.deepcopy(good)
        c = next(c for c in delayed["chunks"] if c["height_included"] == target["height"])
        c["height_created"] -= 2
        c["prev_block_hash"] = "synthetic-creation-predecessor"
        self.assertEqual(m.validate_endpoint(delayed, target)["new_headers_with_earlier_creation_predecessor_unchecked"], 1)
        for field, value in (("hash", "wrong"), ("total_supply", 1.0),
                             ("timestamp_nanosec", "1"), ("epoch_id", None)):
            bad = copy.deepcopy(good)
            bad["header"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                m.validate_endpoint(bad, target)
        for mode in ("duplicate", "mask", "predecessor"):
            bad = copy.deepcopy(good)
            if mode == "duplicate":
                bad["chunks"][1] = copy.deepcopy(bad["chunks"][0])
            elif mode == "mask":
                bad["header"]["chunk_mask"].pop()
            else:
                next(c for c in bad["chunks"] if c["height_included"] == target["height"])["prev_block_hash"] = "wrong"
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                m.validate_endpoint(bad, target)

    def test_manual_collector_success_is_exact_and_errors_do_not_retry(self):
        proposal = m.plan()
        def transport(raw):
            request = m.capture.decode(raw)
            target = next(t for t in proposal["targets"] if t["id"] == request["id"])
            return ({"http_status": 200, "body_complete": True, "transport_error": None},
                    m.capture.json_bytes({"jsonrpc": "2.0", "id": request["id"], "result": self.endpoint(target)}))
        with tempfile.TemporaryDirectory() as temp, patch.object(m, "OUTPUT", Path(temp) / "captures"), \
                patch.object(m.capture, "fetch", side_effect=transport) as fetch, \
                patch.object(m.capture.time, "sleep"), redirect_stdout(io.StringIO()):
            directory = m.collect_week()
            self.assertEqual(fetch.call_count, 2)
            r = m.validate_week(directory)
            self.assertEqual(r["net_supply_movement_yocto"], "0")  # Synthetic endpoints, not evidence.
            self.assertIsNone(r["independent_weekly_mint_yocto"])
            self.assertIsNone(r["gross_actual_burn_yocto"])
            response = next(directory.glob("*.response.body"))
            response.write_bytes(response.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "checksum"):
                m.validate_week(directory)
        for status, payload in ((429, b'{}'), (200, b'{"jsonrpc":"2.0","id":"week-opening","error":{"code":-32000}}')):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp, \
                    patch.object(m, "OUTPUT", Path(temp) / "captures"), \
                    patch.object(m.capture, "fetch", return_value=(
                        {"http_status": status, "body_complete": True, "transport_error": None}, payload)) as fetch, \
                    patch.object(m.capture.time, "sleep"), redirect_stdout(io.StringIO()):
                with self.assertRaises(ValueError):
                    m.collect_week()
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual(len(list(Path(temp).rglob("*.response.body"))), 1)

    def test_output_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "report.json"
            target.write_bytes(b"keep")
            with patch("sys.stderr", io.StringIO()):
                self.assertEqual(m.main(["inventory", "--output", str(target)]), 1)
            self.assertEqual(target.read_bytes(), b"keep")


if __name__ == "__main__":
    unittest.main()
