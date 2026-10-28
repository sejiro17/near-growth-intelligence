import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from latest_activity.core import (
    STATE_NAME, candidate_dates,
    failure_status, iso, load_data, prepare_refresh, publish, read_json,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAP = 5 * 1024 ** 3
LOCATION = "us-east1"


def billing_cap(value):
    if not isinstance(value, str) or not value.isdecimal() or int(value) <= 0:
        raise ValueError("LATEST_MAX_BYTES_BILLED must be a positive integer")
    return int(value)


def normalize_rows(rows):
    normalized = []
    for source in rows:
        row = dict(source)
        row["observation_date"] = row["observation_date"].isoformat()
        for key in ("first_timestamp_utc", "last_timestamp_utc"):
            if row[key] is not None:
                value = row[key]
                if value.tzinfo is None:
                    value = value.replace(tzinfo=timezone.utc)
                row[key] = iso(value)
        normalized.append(row)
    return normalized


def extract(project, cap, now, dry_run=False):
    from google.api_core.exceptions import Conflict, NotFound
    from google.cloud import bigquery

    client = bigquery.Client(project=project, location=LOCATION)
    days = candidate_dates(now)
    query = (ROOT / "sql/38_latest_daily_activity.sql").read_text()
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", days[0]),
        bigquery.ScalarQueryParameter("end_date", "DATE", days[-1]),
    ]
    job_id = "near_growth_intelligence_latest_" + now.strftime("%Y%m%d")
    job = None
    reused = False
    estimated_bytes = None
    if not dry_run:
        try:
            job = client.get_job(job_id, location=LOCATION)
            reused = True
        except NotFound:
            pass
    if job is None:
        config = bigquery.QueryJobConfig(
            query_parameters=parameters, dry_run=True, use_query_cache=False,
            maximum_bytes_billed=cap,
        )
        estimate = client.query(query, job_config=config, location=LOCATION)
        estimated_bytes = estimate.total_bytes_processed
        print(f"Dry-run estimated bytes: {estimated_bytes}; cap: {cap}")
        if estimated_bytes is None or estimated_bytes > cap:
            raise ValueError("Dry-run estimate exceeds the configured billing cap")
        if dry_run:
            return None
        config.dry_run = False
        try:
            job = client.query(query, job_config=config, job_id=job_id,
                               location=LOCATION)
        except Conflict:
            job = client.get_job(job_id, location=LOCATION)
            reused = True
    expected_parameters = [p.to_api_repr() for p in parameters]
    actual_parameters = [p.to_api_repr() for p in job.query_parameters]
    if job.query != query or actual_parameters != expected_parameters:
        raise ValueError("Existing daily job differs from this extraction")
    if job.maximum_bytes_billed is None or int(job.maximum_bytes_billed) > cap:
        raise ValueError("Existing daily job used a larger or missing billing cap")
    rows = normalize_rows(job.result(timeout=600))
    if job.started is None or job.ended is None or job.started > job.ended:
        raise ValueError("Extraction has invalid execution timestamps")
    metadata = {"job_id": job_id, "estimated_bytes": estimated_bytes,
                "bytes_processed": job.total_bytes_processed,
                "bytes_billed": job.total_bytes_billed,
                "maximum_bytes_billed": int(job.maximum_bytes_billed),
                "source_observed_at": iso(job.started),
                "query_completed_at": iso(job.ended), "reused_job": reused}
    return rows, job.started.astimezone(timezone.utc), metadata


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if os.environ.get("LATEST_REFRESH_ENABLED", "false").lower() != "true":
        print("Daily refresh is disabled. No query submitted.")
        return 0
    now = datetime.now(timezone.utc)
    directory = ROOT / "latest_activity_data"
    try:
        cap = billing_cap(os.environ.get("LATEST_MAX_BYTES_BILLED", str(DEFAULT_CAP)))
        project = os.environ.get("LATEST_BILLING_PROJECT")
        if not project:
            raise ValueError("LATEST_BILLING_PROJECT is required")
        result = extract(project, cap, now, dry_run=args.dry_run)
        if args.dry_run:
            return 0
        raw_rows, observed_at, metadata = result
        now = datetime.now(timezone.utc)
        previous, _ = load_data(directory)
        state_path = directory / STATE_NAME
        state = read_json(state_path) if state_path.exists() else None
        data, state, status = prepare_refresh(
            raw_rows, state, previous, observed_at, now, metadata["job_id"]
        )
        status["query"] = metadata
        publish(directory, data, state, status)
        print("Refresh validated. Publication state: " + status["state"])
        return 0
    except Exception as error:
        if not args.dry_run:
            try:
                failure_status(directory, datetime.now(timezone.utc))
            except OSError:
                pass
        print(f"Refresh failed ({type(error).__name__}); previous data retained.",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
