"""Synthetic short-range fixtures; no Neardata or RPC calls are permitted."""

import copy
import hashlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("header_pilot", ROOT/"analysis/36_neardata_header_pilot.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def identifier(label):
    raw = hashlib.sha256(label.encode()).digest()
    value, result = int.from_bytes(raw, "big"), ""
    while value:
        value, digit = divmod(value, 58)
        result = m.ALPHABET[digit]+result
    return "1"*(len(raw)-len(raw.lstrip(b"\0")))+result


class HeaderPilotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for target in ("socket.socket", "socket.create_connection"):
            guard = patch(target, side_effect=AssertionError("Live networking forbidden"))
            guard.start()
            self.addCleanup(guard.stop)
        guard = patch.object(m, "END", m.START+3)
        guard.start()
        self.addCleanup(guard.stop)
        self.prepared = m.plan()
        plan_path = self.root/"plan.json"
        plan_path.write_bytes(m.c.json_bytes(self.prepared))
        guard = patch.object(m, "PLAN", plan_path)
        guard.start()
        self.addCleanup(guard.stop)
        self.store = self.root/"raw-store"
        self.calls, self.pauses = [], []
        self.make_blocks()

    def make_blocks(self, nulls=(), carried=False, delayed=False):
        control = m.b.controls()[0]
        prev = control
        self.blocks = {m.START: control}
        for height in range(m.START+1, m.END+1):
            if height in nulls:
                self.blocks[height] = None
                continue
            block = copy.deepcopy(prev)
            h, p = block["header"], prev["header"]
            h.update(height=height, hash=identifier(f"block-{height}"), prev_height=p["height"], prev_hash=p["hash"],
                     timestamp=p["timestamp"]+10**9, timestamp_nanosec=str(p["timestamp"]+10**9))
            debit, mask = 0, []
            for i, chunk in enumerate(block["chunks"]):
                if carried and i == 0:
                    mask.append(False)
                    continue
                chunk.update(chunk_hash=identifier(f"chunk-{height}-{i}"), height_created=height, height_included=height,
                             prev_block_hash=p["hash"], balance_burnt=str(10**16+i))
                if delayed and height == m.START+2 and i == 1:
                    chunk.update(height_created=height-1, prev_block_hash=self.blocks[m.START]["header"]["hash"])
                mask.append(True)
                debit += int(chunk["balance_burnt"])
            h.update(total_supply=str(int(p["total_supply"])-debit), chunk_mask=mask, chunks_included=sum(mask))
            self.blocks[height] = block
            prev = block

    def transport(self, url, raw):
        parsed = urlsplit(url)
        height = int(parsed.path.split("/")[-2])
        self.calls.append((url, raw))
        self.assertTrue(m.START < height <= m.END)  # saved A must never be fetched
        meta = {"http_status": 200, "response_headers": [], "body_complete": True, "transport_error": None}
        if parsed.hostname == m.HOSTS[0]:
            meta.update(http_status=302, response_headers=[["Location", m.endpoint(m.HOSTS[1], height)]])
            return meta, b""
        return meta, m.c.json_bytes(self.blocks[height])

    def collect(self, transport=None):
        with redirect_stdout(io.StringIO()):
            return m.collect(self.store, transport=transport or self.transport, pause=self.pauses.append)

    def test_pacing_saved_A_reuse_exact_identity_and_stable_offline_report(self):
        report = self.collect()
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(self.pauses, [1]*6)
        self.assertTrue(report["complete"])
        self.assertEqual(report["pilot_supply_identity_discrepancy_yocto"], "0")
        self.assertEqual(report, m.validate(self.store))
        self.assertEqual(m.c.json_bytes(report), (self.store/"sessions/0001/validation.json").read_bytes())
        self.assertEqual(report["performance"]["new_http_responses_recorded"], 6)
        self.assertGreater(report["performance"]["downloaded_body_bytes_all_attempts"], 0)
        self.assertIsNotNone(report["performance"]["session_records"][0]["downloaded_body_bytes_per_wall_second"])
        self.assertIsNone(report["performance"]["full_interval_volume_or_throughput_projection"])
        self.assertIsNone(report["gross_actual_burn_yocto"])
        before = {str(p.relative_to(self.store)): p.read_bytes() for p in (self.store/"attempts").rglob("*") if p.is_file()}
        again = self.collect()
        self.assertTrue(again["complete"])
        self.assertEqual(len(self.calls), 6)
        self.assertEqual(before, {str(p.relative_to(self.store)): p.read_bytes() for p in (self.store/"attempts").rglob("*") if p.is_file()})

    def test_resume_only_missing_after_failure_preserving_success_and_error(self):
        failed_once = False
        def failing(url, raw):
            nonlocal failed_once
            meta, body = self.transport(url, raw)
            if url == m.endpoint(m.HOSTS[1], m.START+2) and not failed_once:
                failed_once = True
                meta["http_status"] = 503
            return meta, body
        with self.assertRaisesRegex(ValueError, "HTTP/transport"):
            self.collect(failing)
        self.assertEqual(len(self.calls), 4)
        valid = self.store/f"attempts/{m.START+1}/01/hop-01/response.body"
        before = valid.read_bytes()
        report = self.collect()
        self.assertTrue(report["complete"])
        self.assertEqual(len(self.calls), 8)
        self.assertEqual(valid.read_bytes(), before)
        self.assertTrue((self.store/f"attempts/{m.START+2}/01/hop-01/response.body").exists())
        self.assertTrue((self.store/f"attempts/{m.START+2}/02/hop-01/response.body").exists())
        self.assertEqual([r["status"] for r in report["performance"]["session_records"]], ["STOPPED", "COMPLETE"])

    def test_null_needs_exact_successor_bypass_and_has_no_invented_zero_amount(self):
        self.make_blocks(nulls={m.START+1})
        result = self.collect()
        gap = next(r for r in result["rows"] if r["height"] == m.START+1)
        self.assertEqual(gap["status"], "SKIP_SUPPORTED_BY_SUCCESSOR_PREDECESSOR")
        self.assertEqual(gap["successor_height"], m.START+2)
        self.assertEqual(gap["prev_height"], m.START)
        self.assertIsNone(gap["net_debit_yocto"])
        self.assertTrue(gap["null_response_sources"])
        self.assertEqual(result["pilot_supply_identity_discrepancy_yocto"], "0")

    def test_unexplained_consecutive_and_trailing_nulls_stop_inside_scope(self):
        self.make_blocks(nulls={m.START+1, m.START+2})
        with self.assertRaisesRegex(ValueError, "consecutive nulls"):
            self.collect()
        self.assertEqual(len(self.calls), 4)
        with self.assertRaisesRegex(ValueError, "consecutive nulls"):
            self.collect()
        self.assertEqual(len(self.calls), 4)
        self.store = self.root/"trailing-store"
        self.calls.clear()
        self.make_blocks(nulls={m.END})
        with self.assertRaisesRegex(ValueError, "Trailing null"):
            self.collect()
        partial = m.validate(self.store)
        self.assertFalse(partial["complete"])
        self.assertIsNone(partial["net_debit_complete_yocto"])
        self.assertEqual(partial["pending_null_heights"], [m.END])
        self.assertTrue(partial["unresolved_null_observations"])
        self.assertTrue(all(int(urlsplit(u).path.split("/")[-2]) <= m.END for u, _ in self.calls))

    def test_carried_and_delayed_chunks_are_not_double_counted(self):
        self.make_blocks(carried=True, delayed=True)
        report = self.collect()
        self.assertEqual(report["pilot_supply_identity_discrepancy_yocto"], "0")
        self.assertEqual(report["outside_scope_creation_predecessors"], [])
        future = [x for x in report["rows"] if x["height"] > m.START]
        for row in future:
            self.assertNotEqual(row["chunks"][0]["height_included"], row["height"])
            expected = sum(int(x["balance_burnt"]) for x in row["chunks"] if x["height_included"] == row["height"])
            self.assertEqual(int(row["net_debit_yocto"]), expected)

    def test_missing_data_is_not_skipped_and_manual_attempts_are_capped(self):
        def missing(url, raw):
            meta, body = self.transport(url, raw)
            if urlsplit(url).hostname == m.HOSTS[1]:
                meta["http_status"] = 404
            return meta, body
        for _ in range(2):
            with self.assertRaisesRegex(ValueError, "HTTP/transport"):
                self.collect(missing)
        count = len(self.calls)
        with self.assertRaisesRegex(ValueError, "attempt cap"):
            self.collect(missing)
        self.assertEqual(len(self.calls), count)
        self.assertEqual(count, 4)

    def test_precision_conflicts_invalid_masks_and_unsafe_destinations(self):
        control = self.blocks[m.START]
        good = self.blocks[m.START+1]
        mutations = [lambda x: x["header"].update(total_supply=1.5),
                     lambda x: x["chunks"][0].update(balance_burnt="NaN"),
                     lambda x: x["chunks"][0].update(balance_burnt=str(2**128)),
                     lambda x: x["header"].update(chunk_mask=[1]*10),
                     lambda x: x["chunks"].pop(),
                     lambda x: x["header"].update(epoch_id=identifier("other-epoch"))]
        for mutation in mutations:
            bad = copy.deepcopy(good)
            mutation(bad)
            with self.assertRaises(ValueError):
                m.normalize(bad, m.START+1, control)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON"):
            m.c.decode('{"header":{},"header":{}}')
        with self.assertRaises(ValueError):
            m.redirect([["Location", "https://a3.mainnet.neardata.xyz.evil.test/"]], m.START+1)
        with self.assertRaises(ValueError):
            m.endpoint(m.HOSTS[0], m.END+1)
        with self.assertRaises(ValueError):
            m.collect(ROOT/"results/unwanted-raw-store")

    def test_conflicting_predecessor_and_tampered_capture_stop_before_more_requests(self):
        self.blocks[m.START+1]["header"]["prev_hash"] = identifier("not-the-parent")
        with self.assertRaisesRegex(ValueError, "predecessor continuity"):
            self.collect()
        self.assertEqual(len(self.calls), 2)
        with self.assertRaisesRegex(ValueError, "predecessor continuity"):
            self.collect()
        self.assertEqual(len(self.calls), 2)
        path = self.store/f"attempts/{m.START+1}/01/hop-01/response.body"
        path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError, "checksum"):
            m.collect(self.store, transport=self.transport, pause=self.pauses.append)
        self.assertEqual(len(self.calls), 2)

    def test_atomic_exclusive_files_preserve_completed_and_interrupted_bytes(self):
        path = self.root/"proof"
        m.write_new(path, b"original")
        with self.assertRaises(FileExistsError):
            m.write_new(path, b"replacement")
        self.assertEqual(path.read_bytes(), b"original")
        draft = self.root/"proof2.writing-interrupted"
        draft.write_bytes(b"partial evidence")
        m.write_new(self.root/"proof2", b"complete replacement attempt")
        self.assertEqual(draft.read_bytes(), b"partial evidence")

    def test_interrupted_drafts_are_preserved_and_valid_uncheckpointed_blocks_reused(self):
        self.store.mkdir()
        m.write_new(self.store/"manifest.json", m.c.json_bytes({"created_at": m.c.utc_now(), "plan": self.prepared}))
        hop = self.store/f"attempts/{m.START+1}/01/hop-00"
        hop.mkdir(parents=True)
        (hop/"request.http").write_bytes(b"interrupted request")
        draft = hop/"response.body.writing-interrupted"
        draft.write_bytes(b"partial body")
        self.collect()
        self.assertEqual(draft.read_bytes(), b"partial body")
        self.assertTrue((self.store/f"attempts/{m.START+1}/02/hop-01/response.body").exists())
        calls = len(self.calls)
        (self.store/"sessions/0001/finished.json").unlink()
        (self.store/"sessions/0001/validation.json").unlink()
        report = self.collect()
        self.assertEqual(len(self.calls), calls)
        self.assertEqual(report["performance"]["session_records"][0]["status"], "INTERRUPTED_OR_RUNNING")

    def test_conflicting_valid_cached_hashes_are_not_arbitrarily_selected(self):
        self.collect()
        source = self.store/f"attempts/{m.START+1}/01"
        duplicate = source.with_name("02")
        shutil.copytree(source, duplicate)
        path = duplicate/"hop-01/response.body"
        block = m.c.decode(path.read_bytes())
        block["header"]["hash"] = identifier("conflicting-branch")
        body = m.c.json_bytes(block)
        path.write_bytes(body)
        meta_path = duplicate/"hop-01/metadata.json"
        meta = m.c.decode(meta_path.read_bytes())
        meta.update(response_bytes=len(body), response_sha256=m.c.sha256(body))
        meta_path.write_bytes(m.c.json_bytes(meta))
        calls = len(self.calls)
        with self.assertRaisesRegex(ValueError, "Conflicting cached"):
            self.collect()
        self.assertEqual(len(self.calls), calls)

    def test_session_and_lifetime_caps_stop_without_automatic_increases(self):
        with patch.object(m, "MAX_SESSION_REQUESTS", 1):
            m.PLAN.write_bytes(m.c.json_bytes(m.plan()))
            with self.assertRaisesRegex(ValueError, "Session request cap"):
                self.collect()
            self.assertEqual(len(self.calls), 1)
        self.store = self.root/"body-budget-store"
        self.calls.clear()
        with patch.object(m, "TOTAL_BODY_CAP", 1):
            m.PLAN.write_bytes(m.c.json_bytes(m.plan()))
            with self.assertRaisesRegex(ValueError, "body cap"):
                self.collect()
            self.assertEqual(len(self.calls), 2)

    def test_full_interval_is_disabled_even_if_end_is_changed(self):
        with patch.object(m, "END", m.FULL_END):
            with self.assertRaisesRegex(ValueError, "at-most-100"):
                m.plan()

    def test_full_100_height_fixture_stays_within_198_requests(self):
        with patch.object(m, "END", m.START+99):
            m.PLAN.write_bytes(m.c.json_bytes(m.plan()))
            self.make_blocks()
            report = self.collect()
            self.assertEqual(len(report["rows"]), 100)
            self.assertEqual(len(self.calls), 198)
            self.assertEqual(self.pauses, [1]*198)
            requested = {int(urlsplit(url).path.split("/")[-2]) for url, _ in self.calls}
            self.assertEqual(requested, set(range(m.START+1, m.START+100)))
            self.assertEqual(report["pilot_supply_identity_discrepancy_yocto"], "0")


if __name__ == "__main__":
    unittest.main()
