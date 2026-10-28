import copy
import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from latest_activity import core, refresh


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 28, 6, 17, tzinfo=timezone.utc)


def observations(now):
    result = []
    for day in core.candidate_dates(now):
        count = day.toordinal()
        result.append({
            "observation_date": day.isoformat(), "transactions": count,
            "distinct_transaction_hashes": count, "signing_accounts": 100,
            "missing_hashes": 0, "missing_signers": 0, "missing_timestamps": 0,
            "timestamp_date_mismatches": 0, "observed_hours": 24,
            "first_timestamp_utc": day.isoformat() + "T00:00:01Z",
            "last_timestamp_utc": day.isoformat() + "T23:59:59Z",
        })
    return result


def warmed_data(now=NOW):
    before = now - timedelta(days=1)
    _, state, _ = core.prepare_refresh(observations(before), None, None,
                                       before, before, "first")
    return core.prepare_refresh(observations(now), state, None, now, now, "second")


class ValidationTests(unittest.TestCase):
    def test_first_run_never_fabricates_an_export(self):
        data, state, status = core.prepare_refresh(
            observations(NOW), None, None, NOW, NOW, "first"
        )
        self.assertIsNone(data)
        self.assertEqual(status["state"], "pending")
        self.assertEqual(len(state["candidates"]), 4)
        with tempfile.TemporaryDirectory() as folder:
            core.publish(folder, data, state, status)
            self.assertFalse((Path(folder) / core.DATA_NAME).exists())

    def test_two_observations_and_age_are_required(self):
        data, _, _ = warmed_data()
        self.assertEqual(data["latest_observation_date"], "2026-10-25")
        self.assertEqual([r["date"] for r in data["rows"]],
                         ["2026-10-24", "2026-10-25"])
        first = NOW - timedelta(hours=19)
        _, state, _ = core.prepare_refresh(observations(first), None, None,
                                           first, first, "first")
        data, _, _ = core.prepare_refresh(observations(NOW), state, None,
                                          NOW, NOW, "second")
        self.assertIsNone(data)

    def test_replayed_job_does_not_increment_stability(self):
        _, state, _ = core.prepare_refresh(observations(NOW), None, None,
                                           NOW, NOW, "same")
        data, next_state, _ = core.prepare_refresh(
            observations(NOW), state, None, NOW, NOW + timedelta(hours=1), "same"
        )
        self.assertIsNone(data)
        self.assertTrue(all(c["observations"] == 1
                            for c in next_state["candidates"].values()))

    def test_changed_summary_restarts_stability(self):
        before = NOW - timedelta(days=1)
        _, state, _ = core.prepare_refresh(observations(before), None, None,
                                           before, before, "first")
        rows = observations(NOW)
        rows[1]["signing_accounts"] += 1
        data, state, _ = core.prepare_refresh(rows, state, None, NOW, NOW, "second")
        self.assertEqual(state["candidates"]["2026-10-25"]["observations"], 1)
        self.assertEqual(data["latest_observation_date"], "2026-10-24")

    def test_missing_or_incomplete_partitions_are_not_zero(self):
        rows = observations(NOW)
        missing = {key: None for key in rows[0]}
        missing["observation_date"] = rows[0]["observation_date"]
        self.assertIsNone(core.validate_observation(missing))
        rows[0]["observed_hours"] = 23
        self.assertIsNone(core.validate_observation(rows[0]))
        rows = observations(NOW)
        rows[0]["first_timestamp_utc"] = rows[0]["observation_date"] + "T00:06:00Z"
        self.assertIsNone(core.validate_observation(rows[0]))

    def test_invalid_source_rows_are_rejected(self):
        changes = [
            ("transactions", -1), ("signing_accounts", 0),
            ("signing_accounts", 10**20), ("missing_hashes", 1),
            ("missing_signers", 1), ("missing_timestamps", 1),
            ("timestamp_date_mismatches", 1), ("distinct_transaction_hashes", 1),
            ("observed_hours", 25), ("transactions", float("nan")),
            ("transactions", True), ("transactions", 1.5),
        ]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                row = observations(NOW)[0]
                row[field] = value
                with self.assertRaises(ValueError):
                    core.validate_observation(row)

    def test_wrong_or_duplicate_candidate_dates_fail(self):
        rows = observations(NOW)
        rows[0]["observation_date"] = rows[1]["observation_date"]
        with self.assertRaises(ValueError):
            core.prepare_refresh(rows, None, None, NOW, NOW, "bad")

    def test_published_revision_is_retained_and_flagged(self):
        data, state, _ = warmed_data()
        tomorrow = NOW + timedelta(days=1)
        rows = observations(tomorrow)
        rows[0]["signing_accounts"] += 1
        updated, state, status = core.prepare_refresh(
            rows, state, data, tomorrow, tomorrow, "third"
        )
        original = next(r for r in data["rows"] if r["date"] == "2026-10-25")
        self.assertEqual(next(r for r in updated["rows"] if r["date"] == "2026-10-25"), original)
        self.assertEqual(status["pending_revision_dates"], ["2026-10-25"])
        self.assertTrue(core.assess_freshness(updated, status, tomorrow, candidate_state=state)["stale"])

    def test_revision_survives_lookback_expiry_until_row_is_retired(self):
        data, state, _ = warmed_data()
        tomorrow = NOW + timedelta(days=1)
        rows = observations(tomorrow)
        rows[0]["signing_accounts"] += 1
        data, state, status = core.prepare_refresh(rows, state, data, tomorrow, tomorrow, "third")
        self.assertEqual(status["pending_revision_dates"], ["2026-10-25"])
        for offset in range(2, 36):
            now = NOW + timedelta(days=offset)
            data, state, status = core.prepare_refresh(
                observations(now), state, data, now, now, str(offset)
            )
            retained = any(row["date"] == "2026-10-25" for row in data["rows"])
            self.assertEqual(data["pending_revision_dates"], ["2026-10-25"] if retained else [])
            self.assertEqual(state["pending_revision_dates"], data["pending_revision_dates"])
            self.assertEqual(status["pending_revision_dates"], data["pending_revision_dates"])
            self.assertEqual(core.assess_freshness(data, status, now, candidate_state=state)["stale"], retained)
        self.assertNotIn("2026-10-25", [row["date"] for row in data["rows"]])

    def test_old_cached_evidence_cannot_clear_a_known_revision(self):
        data, old_state, _ = warmed_data()
        known = "2026-10-25"
        detected = NOW + timedelta(minutes=1)
        data["pending_revision_dates"] = [known]
        data["pending_revisions"] = {known: core.iso(detected)}
        data["published_at"] = core.iso(detected)
        unchanged, state, status = core.prepare_refresh(
            observations(NOW), old_state, data, NOW, NOW + timedelta(hours=1), "second"
        )
        self.assertEqual(unchanged["pending_revision_dates"], [known])
        self.assertEqual(state["pending_revision_dates"], [known])
        self.assertEqual(status["pending_revision_dates"], [known])

    def test_revision_requires_independent_post_detection_observations(self):
        data, state, _ = warmed_data()
        detected = NOW + timedelta(hours=1)
        rows = observations(detected)
        rows[1]["signing_accounts"] += 1
        data, state, status = core.prepare_refresh(rows, state, data, detected, detected, "changed")
        self.assertEqual(data["pending_revision_dates"], ["2026-10-25"])
        later = detected + timedelta(hours=20)
        rows = observations(later)
        next(row for row in rows if row["observation_date"] == "2026-10-25")["signing_accounts"] += 1
        data, state, status = core.prepare_refresh(rows, state, data, later, later, "independent")
        self.assertEqual(data["pending_revision_dates"], [])
        self.assertEqual(next(row for row in data["rows"] if row["date"] == "2026-10-25")["signing_accounts"], 101)

    def test_reused_job_does_not_change_source_or_publication_timestamp(self):
        data, state, _ = warmed_data()
        original = copy.deepcopy(data)
        later = NOW + timedelta(hours=10)
        data, state, status = core.prepare_refresh(
            observations(NOW), state, data, NOW, later, "second"
        )
        self.assertEqual(data, original)
        self.assertEqual(data["source_observed_at"], core.iso(NOW))
        self.assertEqual(data["published_at"], core.iso(NOW))
        self.assertEqual(status["attempted_at"], core.iso(later))

    def test_history_and_candidate_state_remain_bounded(self):
        data, state = None, None
        for offset in range(40):
            now = NOW + timedelta(days=offset)
            data, state, _ = core.prepare_refresh(
                observations(now), state, data, now, now, str(offset)
            )
        self.assertEqual(len(data["rows"]), 30)
        self.assertEqual(len(state["candidates"]), 4)
        self.assertEqual(data["latest_observation_date"], "2026-12-03")


class PublicationTests(unittest.TestCase):
    def test_atomic_failure_keeps_last_valid_export(self):
        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            core.publish(folder, data, state, status)
            old_bytes = (Path(folder) / core.DATA_NAME).read_bytes()
            tomorrow = NOW + timedelta(days=1)
            new, state, status = core.prepare_refresh(
                observations(tomorrow), state, data, tomorrow, tomorrow, "third"
            )
            replace = os.replace

            def fail_primary(source, destination):
                if Path(destination).name == core.DATA_NAME:
                    raise OSError("Fixture publication failure")
                return replace(source, destination)

            with patch("latest_activity.core.os.replace", side_effect=fail_primary):
                with self.assertRaises(OSError):
                    core.publish(folder, new, state, status)
            self.assertEqual((Path(folder) / core.DATA_NAME).read_bytes(), old_bytes)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             sorted([core.DATA_NAME, core.BACKUP_NAME,
                                     core.STATE_NAME, core.STATUS_NAME]))

    def test_failure_status_preserves_data_and_marks_it_stale(self):
        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            core.publish(folder, data, state, status)
            original = (Path(folder) / core.DATA_NAME).read_bytes()
            core.failure_status(folder, NOW)
            self.assertEqual((Path(folder) / core.DATA_NAME).read_bytes(), original)
            status = core.read_json(Path(folder) / core.STATUS_NAME)
            self.assertTrue(core.assess_freshness(data, status, NOW, candidate_state=state)["stale"])

    def test_invalid_primary_falls_back_to_valid_previous(self):
        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            core.atomic_json(Path(folder) / core.BACKUP_NAME, data)
            (Path(folder) / core.DATA_NAME).write_text("{bad")
            loaded, fallback = core.load_data(folder)
            self.assertEqual(loaded, data)
            self.assertTrue(fallback)

    def test_staleness_and_gaps_are_computed_at_read_time(self):
        data, state, status = warmed_data()
        self.assertFalse(core.assess_freshness(data, status, NOW, candidate_state=state)["stale"])
        self.assertTrue(core.assess_freshness(data, status, NOW + timedelta(hours=31), candidate_state=state)["stale"])
        data = copy.deepcopy(data)
        old = copy.deepcopy(data["rows"][0])
        old["date"] = "2026-10-22"
        data["rows"].insert(0, old)
        status["data_sha256"] = core.digest(data)
        self.assertEqual(core.assess_freshness(data, status, NOW, candidate_state=state)["gaps"], ["2026-10-23"])

    def test_all_mixed_bundles_are_stale(self):
        data, state, status = warmed_data()
        later = NOW + timedelta(hours=1)
        new_data, new_state, new_status = core.prepare_refresh(
            observations(later), state, data, later, later, "independent"
        )
        bundles = [(data, new_data), (state, new_state), (status, new_status)]
        for data_version in (0, 1):
            for state_version in (0, 1):
                for status_version in (0, 1):
                    with self.subTest(versions=(data_version, state_version, status_version)):
                        chosen_data = bundles[0][data_version]
                        chosen_state = bundles[1][state_version]
                        chosen_status = bundles[2][status_version]
                        mixed = len({data_version, state_version, status_version}) != 1
                        self.assertEqual(core.assess_freshness(
                            chosen_data, chosen_status, later, candidate_state=chosen_state
                        )["stale"], mixed)

    def test_abrupt_interruption_at_each_incomplete_publication_step_is_stale(self):
        data, state, status = warmed_data()
        later = NOW + timedelta(hours=1)
        new_data, new_state, new_status = core.prepare_refresh(
            observations(later), state, data, later, later, "independent"
        )
        for step in range(1, 5):
            with self.subTest(step=step), tempfile.TemporaryDirectory() as folder:
                core.publish(folder, data, state, status)
                write = core.atomic_json
                calls = []

                def interrupt(path, document):
                    write(path, document)
                    calls.append(path)
                    if len(calls) == step:
                        raise KeyboardInterrupt

                with patch.object(core, "atomic_json", side_effect=interrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        core.publish(folder, new_data, new_state, new_status)
                loaded, fallback = core.load_data(folder)
                loaded_state = core.read_json(Path(folder) / core.STATE_NAME)
                loaded_status = core.read_json(Path(folder) / core.STATUS_NAME)
                self.assertEqual(loaded_status["state"], "publishing")
                self.assertTrue(core.assess_freshness(
                    loaded, loaded_status, later, fallback, loaded_state
                )["stale"])

    def test_failed_final_manifest_restores_previous_data(self):
        data, state, status = warmed_data()
        later = NOW + timedelta(hours=1)
        new_data, new_state, new_status = core.prepare_refresh(
            observations(later), state, data, later, later, "independent"
        )
        with tempfile.TemporaryDirectory() as folder:
            core.publish(folder, data, state, status)
            original = (Path(folder) / core.DATA_NAME).read_bytes()
            write = core.atomic_json

            def fail_final(path, document):
                if Path(path).name == core.STATUS_NAME and document["state"] == "success":
                    raise OSError("Fixture final manifest failure")
                return write(path, document)

            with patch.object(core, "atomic_json", side_effect=fail_final):
                with self.assertRaises(OSError):
                    core.publish(folder, new_data, new_state, new_status)
            self.assertEqual((Path(folder) / core.DATA_NAME).read_bytes(), original)
            self.assertEqual(core.read_json(Path(folder) / core.STATUS_NAME)["state"], "publishing")


class RunnerTests(unittest.TestCase):
    def test_dry_run_over_cap_never_submits_an_extraction(self):
        from google.api_core.exceptions import NotFound
        from google.cloud import bigquery

        client = Mock()
        client.get_job.side_effect = NotFound("Fixture absent job")
        client.query.return_value.total_bytes_processed = 101
        with patch.object(bigquery, "Client", return_value=client):
            with self.assertRaises(ValueError):
                refresh.extract("fixture-project", 100, NOW)
        self.assertEqual(client.query.call_count, 1)
        self.assertTrue(client.query.call_args.kwargs["job_config"].dry_run)
        client.get_job.assert_called_once()

    def test_dry_run_only_does_not_start_or_retrieve_a_paid_job(self):
        from google.cloud import bigquery

        client = Mock()
        client.query.return_value.total_bytes_processed = 50
        with patch.object(bigquery, "Client", return_value=client):
            self.assertIsNone(refresh.extract("fixture-project", 100, NOW, dry_run=True))
        self.assertEqual(client.query.call_count, 1)
        client.get_job.assert_not_called()

    def test_extraction_passes_cap_and_reuses_daily_job(self):
        from google.api_core.exceptions import NotFound
        from google.cloud import bigquery

        client = Mock()
        job = Mock()
        job.query = (ROOT / "sql/38_latest_daily_activity.sql").read_text()
        job.maximum_bytes_billed = 100
        days = core.candidate_dates(NOW)
        job.query_parameters = [
            bigquery.ScalarQueryParameter("start_date", "DATE", days[0]),
            bigquery.ScalarQueryParameter("end_date", "DATE", days[-1]),
        ]
        job.ended = NOW
        job.started = NOW
        raw = observations(NOW)
        for row in raw:
            row["observation_date"] = days.pop(0)
            for key in ("first_timestamp_utc", "last_timestamp_utc"):
                row[key] = core.timestamp(row[key])
        job.result.return_value = raw
        submitted = []

        def submit(query, job_config, **kwargs):
            submitted.append((job_config.dry_run, job_config.maximum_bytes_billed, kwargs))
            return Mock(total_bytes_processed=50) if job_config.dry_run else job

        client.query.side_effect = submit
        client.get_job.side_effect = NotFound("Fixture absent job")
        with patch.object(bigquery, "Client", return_value=client):
            rows, at, metadata = refresh.extract("fixture-project", 100, NOW)
            self.assertEqual(rows, observations(NOW))
            self.assertEqual(at, NOW)
            self.assertEqual(metadata["maximum_bytes_billed"], 100)
            self.assertFalse(metadata["reused_job"])
            self.assertEqual(submitted[1][2]["job_id"], "near_growth_intelligence_latest_20261028")
            client.get_job.side_effect = None
            client.get_job.return_value = job
            before = len(submitted)
            _, at, metadata = refresh.extract("fixture-project", 100, NOW)
            self.assertEqual(len(submitted), before)
            self.assertTrue(metadata["reused_job"])
            self.assertEqual(at, NOW)
        self.assertEqual([x[:2] for x in submitted], [(True, 100), (False, 100)])

    def test_reuse_never_requires_a_new_dry_run_and_uses_original_start_time(self):
        from google.cloud import bigquery

        client = Mock()
        job = Mock()
        job.query = (ROOT / "sql/38_latest_daily_activity.sql").read_text()
        job.maximum_bytes_billed = 100
        days = core.candidate_dates(NOW)
        job.query_parameters = [
            bigquery.ScalarQueryParameter("start_date", "DATE", days[0]),
            bigquery.ScalarQueryParameter("end_date", "DATE", days[-1]),
        ]
        job.started = NOW - timedelta(minutes=5)
        job.ended = NOW
        job.result.return_value = []
        client.get_job.return_value = job
        client.query.side_effect = AssertionError("No query should be submitted for reuse")
        with patch.object(bigquery, "Client", return_value=client):
            _, at, metadata = refresh.extract("fixture-project", 100, NOW)
            self.assertEqual(at, job.started)
            self.assertEqual(metadata["query_completed_at"], core.iso(NOW))
            self.assertTrue(metadata["reused_job"])
            job.maximum_bytes_billed = 101
            with self.assertRaises(ValueError):
                refresh.extract("fixture-project", 100, NOW)
        client.query.assert_not_called()

    def test_job_creation_conflict_reuses_the_existing_capped_job(self):
        from google.api_core.exceptions import Conflict, NotFound
        from google.cloud import bigquery

        client = Mock()
        job = Mock()
        job.query = (ROOT / "sql/38_latest_daily_activity.sql").read_text()
        job.maximum_bytes_billed = 100
        days = core.candidate_dates(NOW)
        job.query_parameters = [
            bigquery.ScalarQueryParameter("start_date", "DATE", days[0]),
            bigquery.ScalarQueryParameter("end_date", "DATE", days[-1]),
        ]
        job.started = NOW
        job.ended = NOW
        job.result.return_value = []
        client.get_job.side_effect = [NotFound("Fixture race"), job]
        client.query.side_effect = [Mock(total_bytes_processed=50), Conflict("Fixture existing job")]
        with patch.object(bigquery, "Client", return_value=client):
            _, _, metadata = refresh.extract("fixture-project", 100, NOW)
        self.assertTrue(metadata["reused_job"])
        self.assertEqual(client.query.call_count, 2)
        self.assertEqual(client.get_job.call_count, 2)

    def test_disabled_by_default_without_importing_or_calling_bigquery(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(refresh, "extract") as extract:
            self.assertEqual(refresh.main([]), 0)
            extract.assert_not_called()

    def test_billing_cap_cannot_be_missing_invalid_or_implicitly_increased(self):
        self.assertEqual(refresh.billing_cap("5368709120"), 5368709120)
        for value in ("", "0", "-1", "5.5", "unlimited"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                refresh.billing_cap(value)

    def test_query_failure_leaves_existing_data_unchanged(self):
        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            directory = root / "latest_activity_data"
            core.publish(directory, data, state, status)
            original = (directory / core.DATA_NAME).read_bytes()
            with patch.object(refresh, "ROOT", root), patch.dict(os.environ, {
                "LATEST_REFRESH_ENABLED": "true", "LATEST_BILLING_PROJECT": "fixture-project",
            }), patch.object(refresh, "extract", side_effect=RuntimeError("private fixture value")):
                self.assertEqual(refresh.main([]), 1)
            self.assertEqual((directory / core.DATA_NAME).read_bytes(), original)
            self.assertNotIn("private fixture value", (directory / core.STATUS_NAME).read_text())

    def test_manual_workflow_has_no_automatic_triggers(self):
        workflow = (ROOT / ".github/workflows/latest-activity.yml").read_text()
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("push:", workflow)
        self.assertNotIn("pull_request:", workflow)
        self.assertIn("vars.LATEST_REFRESH_ENABLED == 'true'", workflow)
        uses = [line.split("uses: ", 1)[1] for line in workflow.splitlines() if "uses: " in line]
        self.assertEqual(uses, [
            "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
            "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
            "google-github-actions/auth@c200f3691d83b41bf9bbd8638997a462592937ed",
        ])


class DashboardTests(unittest.TestCase):
    def make_app(self, folder):
        root = Path(folder)
        (root / "dashboard").mkdir()
        app = root / "dashboard/app.py"
        app.write_text((ROOT / "dashboard/app.py").read_text())
        (root / "results").symlink_to(ROOT / "results", target_is_directory=True)
        return app

    def test_inactive_and_malformed_latest_data_do_not_break_historical_tabs(self):
        from streamlit.testing.v1 import AppTest

        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in (ROOT / "results").iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_app(folder)
            app = AppTest.from_file(str(path)).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(len(app.tabs), 7)
            self.assertTrue(any(i.value == "Daily refresh not yet activated." for i in app.info))
            data_path = Path(folder) / "latest_activity_data" / core.DATA_NAME
            data_path.parent.mkdir()
            data_path.write_text("{broken")
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(app.error)
            self.assertEqual(len(app.tabs), 7)
            self.assertTrue(any("Latest activity is unavailable" in w.value for w in app.warning))
            control = next(s for s in app.selectbox if s.key == "explorer_account")
            control.select(control.options[-1])
            app.run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 7)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (ROOT / "results").iterdir() if p.is_file()}
        self.assertEqual(before, after)

    def test_fallback_data_show_metrics_and_stale_warning(self):
        from streamlit.testing.v1 import AppTest

        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_app(folder)
            directory = Path(folder) / "latest_activity_data"
            core.publish(directory, data, state, status)
            core.atomic_json(directory / core.BACKUP_NAME, data)
            (directory / core.DATA_NAME).write_text("{broken")
            app = AppTest.from_file(str(path)).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 7)
            self.assertTrue(any(m.label == "Daily transactions" for m in app.metric))
            self.assertTrue(any("previous validated export" in w.value for w in app.warning))

    def test_bad_status_does_not_hide_valid_data_or_historical_tabs(self):
        from streamlit.testing.v1 import AppTest

        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_app(folder)
            directory = Path(folder) / "latest_activity_data"
            core.publish(directory, data, state, status)
            core.atomic_json(directory / core.STATUS_NAME, {"state": "unknown"})
            app = AppTest.from_file(str(path)).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.tabs), 7)
            self.assertTrue(any(m.label == "Daily transactions" for m in app.metric))
            self.assertTrue(any("Refresh status unavailable" in w.value for w in app.warning))

    def test_periodic_section_recalculates_source_age_without_bigquery(self):
        import inspect
        from google.cloud import bigquery
        from streamlit.testing.v1 import AppTest
        from latest_activity import view

        self.assertIn('@st.fragment(run_every="60s")', inspect.getsource(view.render_latest_activity))
        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_app(folder)
            core.publish(Path(folder) / "latest_activity_data", data, state, status)
            clock = Mock()
            clock.now.return_value = NOW
            with patch.object(view, "datetime", clock), patch.object(bigquery, "Client") as client:
                app = AppTest.from_file(str(path)).run(timeout=30)
                self.assertFalse(app.exception)
                self.assertTrue(any("current under" in item.value for item in app.success))
                self.assertTrue(any("Source observation (query start)" in item.value
                                    and "Export published" in item.value for item in app.caption))
                clock.now.return_value = NOW + timedelta(hours=31)
                app.run(timeout=30)
                self.assertFalse(app.exception)
                self.assertTrue(any("verification or delivery overdue" in item.value for item in app.warning))
                self.assertEqual(len(app.tabs), 7)
                client.assert_not_called()

    def test_incomplete_publication_cannot_render_as_current(self):
        from streamlit.testing.v1 import AppTest

        data, state, status = warmed_data()
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_app(folder)
            directory = Path(folder) / "latest_activity_data"
            core.publish(directory, data, state, status)
            core.atomic_json(directory / core.STATUS_NAME, dict(status, state="publishing"))
            app = AppTest.from_file(str(path)).run(timeout=30)
            self.assertFalse(app.exception)
            self.assertFalse(any("current under" in item.value for item in app.success))
            self.assertTrue(any("Publication incomplete" in item.value for item in app.warning))
            self.assertEqual(len(app.tabs), 7)


if __name__ == "__main__":
    unittest.main()
