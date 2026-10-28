import hashlib
import json
import os
import tempfile
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path


UTC = timezone.utc
SOURCE = "bigquery-public-data.crypto_near_mainnet_us.transactions"
DATA_NAME = "activity.json"
BACKUP_NAME = "activity.previous.json"
STATE_NAME = "candidates.json"
STATUS_NAME = "status.json"
MIN_AGE = timedelta(hours=48)
MIN_STABILITY = timedelta(hours=20)
REFRESH_DEADLINE = timedelta(hours=30)
COUNT_FIELDS = (
    "transactions", "distinct_transaction_hashes", "signing_accounts",
    "missing_hashes", "missing_signers", "missing_timestamps",
    "timestamp_date_mismatches", "observed_hours",
)


def timestamp(value):
    if not isinstance(value, str):
        raise ValueError("Invalid timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("Timestamp requires a timezone")
    return result.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def integer(value):
    if type(value) is not int or value < 0:
        raise ValueError("Counts must be nonnegative integers")
    return value


def encode(document):
    return (json.dumps(document, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()


def digest(document):
    return hashlib.sha256(encode(document)).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def atomic_json(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = encode(document)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def candidate_dates(now):
    today = now.astimezone(UTC).date()
    return [today - timedelta(days=offset) for offset in range(4, 0, -1)]


def validate_observation(row):
    day = date.fromisoformat(row["observation_date"])
    if row["transactions"] is None:
        if any(row.get(field) is not None for field in COUNT_FIELDS):
            raise ValueError("Inconsistent missing partition")
        return None
    clean = {field: integer(row[field]) for field in COUNT_FIELDS}
    if (
        clean["transactions"] <= 0
        or clean["distinct_transaction_hashes"] != clean["transactions"]
        or not 0 < clean["signing_accounts"] <= clean["transactions"]
        or any(clean[field] != 0 for field in (
            "missing_hashes", "missing_signers", "missing_timestamps",
            "timestamp_date_mismatches",
        ))
        or not 1 <= clean["observed_hours"] <= 24
    ):
        raise ValueError("Daily source checks failed")
    first = timestamp(row["first_timestamp_utc"])
    last = timestamp(row["last_timestamp_utc"])
    if first.date() != day or last.date() != day or first > last:
        raise ValueError("Invalid daily timestamp range")
    clean.update(observation_date=day.isoformat(),
                 first_timestamp_utc=iso(first), last_timestamp_utc=iso(last))
    opening = datetime.combine(day, time.min, UTC)
    closing = opening + timedelta(days=1)
    if (clean["observed_hours"] != 24 or first > opening + timedelta(minutes=5)
            or last < closing - timedelta(minutes=5)):
        return None
    return clean


def validate_data(document):
    if document["schema_version"] != 1 or document["source"] != SOURCE:
        raise ValueError("Unsupported latest-activity export")
    published = timestamp(document["published_at"])
    source_observed = timestamp(document["source_observed_at"])
    rows = document["rows"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 30:
        raise ValueError("Invalid latest-activity history")
    dates = []
    for row in rows:
        day = date.fromisoformat(row["date"])
        verified = timestamp(row["verified_at"])
        if (
            integer(row["transactions"]) <= 0
            or not 0 < integer(row["signing_accounts"]) <= row["transactions"]
            or verified > source_observed or source_observed > published
            or datetime.combine(day + timedelta(days=1), time.min, UTC)
                + MIN_AGE > verified
        ):
            raise ValueError("Invalid published observation")
        dates.append(day)
    if dates != sorted(set(dates)) or (dates[-1] - dates[0]).days > 29:
        raise ValueError("Invalid observation dates")
    if document["latest_observation_date"] != dates[-1].isoformat():
        raise ValueError("Latest date does not match rows")
    if source_observed != max(timestamp(row["verified_at"]) for row in rows):
        raise ValueError("Source observation time does not match verification records")
    validate_revisions(document["pending_revision_dates"], {d.isoformat() for d in dates})
    validate_revision_observations(document)
    return document


def load_data(directory):
    directory = Path(directory)
    errors = []
    for name in (DATA_NAME, BACKUP_NAME):
        path = directory / name
        if not path.exists():
            continue
        try:
            document = validate_data(read_json(path))
            return document, name == BACKUP_NAME
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            errors.append(name)
    if errors:
        raise ValueError("No valid latest-activity export")
    return None, False


def validate_revisions(revisions, retained=None):
    if not isinstance(revisions, list) or revisions != sorted(set(revisions)):
        raise ValueError("Invalid revision dates")
    for day in revisions:
        date.fromisoformat(day)
    if retained is not None and not set(revisions).issubset(retained):
        raise ValueError("Revision date is outside retained history")
    return revisions


def validate_state(state):
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Unsupported candidate state")
    if not isinstance(state.get("candidates"), dict) or len(state["candidates"]) > 4:
        raise ValueError("Invalid candidate history")
    for day, record in state["candidates"].items():
        date.fromisoformat(day)
        if (not isinstance(record["fingerprint"], str) or len(record["fingerprint"]) != 64
                or integer(record["observations"]) < 1
                or timestamp(record["first_seen_at"]) > timestamp(record["last_seen_at"])):
            raise ValueError("Invalid candidate record")
    validate_revisions(state["pending_revision_dates"])
    validate_revision_observations(state)
    return state


def validate_revision_observations(document):
    markers = document["pending_revisions"]
    if not isinstance(markers, dict) or sorted(markers) != document["pending_revision_dates"]:
        raise ValueError("Revision observations do not match pending dates")
    for detected_at in markers.values():
        timestamp(detected_at)


def validate_status(status):
    if (not isinstance(status, dict) or status.get("schema_version") != 1
            or status.get("state") not in ("success", "pending", "failed", "publishing")):
        raise ValueError("Invalid refresh status")
    timestamp(status["attempted_at"])
    if status["state"] != "failed":
        for field in ("data_sha256", "state_sha256"):
            value = status[field]
            if value is not None and (not isinstance(value, str) or len(value) != 64):
                raise ValueError("Invalid publication checksum")
        validate_revisions(status["pending_revision_dates"])
    return status


def prepare_refresh(raw_rows, previous_state, previous_data, observed_at, now, job_id):
    if observed_at > now or observed_at.date() != now.astimezone(UTC).date():
        raise ValueError("Extraction timestamp does not match this run date")
    expected = candidate_dates(now)
    if [row["observation_date"] for row in raw_rows] != [d.isoformat() for d in expected]:
        raise ValueError("Expected exactly four ordered candidate dates")
    if previous_state is None:
        previous_state = {"schema_version": 1, "candidates": {},
                          "pending_revision_dates": [], "pending_revisions": {}}
    validate_state(previous_state)
    if previous_data is not None:
        validate_data(previous_data)
    candidates = {}
    eligible = {}
    pending = dict(previous_state["pending_revisions"])
    if previous_data:
        for key, detected_at in previous_data["pending_revisions"].items():
            if key not in pending or timestamp(pending[key]) < timestamp(detected_at):
                pending[key] = detected_at
    missing = []
    old_candidates = previous_state["candidates"]
    published = {r["date"]: r for r in previous_data["rows"]} if previous_data else {}
    for raw in raw_rows:
        key = raw["observation_date"]
        clean = validate_observation(raw)
        if clean is None:
            missing.append(key)
            if key in published:
                pending.setdefault(key, iso(observed_at))
            continue
        fingerprint = digest(clean)
        old = old_candidates.get(key)
        current = {"fingerprint": fingerprint, "first_seen_at": iso(observed_at),
                   "last_seen_at": iso(observed_at), "observations": 1}
        if old and old["fingerprint"] == fingerprint:
            first_seen = timestamp(old["first_seen_at"])
            last_seen = timestamp(old["last_seen_at"])
            count = integer(old["observations"])
            if first_seen > last_seen or last_seen > observed_at or count < 1:
                raise ValueError("Invalid candidate observation history")
            current.update(first_seen_at=iso(first_seen),
                           observations=count + int(observed_at > last_seen))
        if key in pending and timestamp(current["first_seen_at"]) < timestamp(pending[key]):
            current.update(first_seen_at=iso(observed_at), observations=1)
        candidates[key] = current
        closing = datetime.combine(date.fromisoformat(key) + timedelta(days=1), time.min, UTC)
        stable = (current["observations"] >= 2
                  and observed_at - timestamp(current["first_seen_at"]) >= MIN_STABILITY)
        if stable and observed_at - closing >= MIN_AGE:
            eligible[key] = {"date": key, "transactions": clean["transactions"],
                             "signing_accounts": clean["signing_accounts"],
                             "verified_at": iso(observed_at)}
            pending.pop(key, None)
        elif key in published:
            pending.setdefault(key, iso(observed_at))
    merged = dict(published)
    merged.update(eligible)
    data = previous_data
    if merged:
        latest_day = date.fromisoformat(max(merged))
        earliest = latest_day - timedelta(days=29)
        history = [row for key, row in sorted(merged.items())
                   if date.fromisoformat(key) >= earliest]
        retained = {row["date"] for row in history}
        pending = {key: value for key, value in pending.items() if key in retained}
        source_observed_at = max(timestamp(row["verified_at"]) for row in history)
        if (not previous_data or previous_data["rows"] != history
                or previous_data["pending_revision_dates"] != sorted(pending)
                or previous_data["pending_revisions"] != pending):
            data = validate_data({"schema_version": 1, "source": SOURCE,
                                  "published_at": iso(now), "job_id": job_id,
                                  "source_observed_at": iso(source_observed_at),
                                  "pending_revision_dates": sorted(pending),
                                  "pending_revisions": pending,
                                  "latest_observation_date": history[-1]["date"],
                                  "rows": history})
    else:
        pending.clear()
    state = validate_state({"schema_version": 1, "candidates": candidates,
                            "pending_revision_dates": sorted(pending),
                            "pending_revisions": pending})
    status = {"schema_version": 1, "attempted_at": iso(now),
              "state": "success" if eligible else "pending",
              "data_sha256": digest(data) if data else None,
              "state_sha256": digest(state),
              "pending_revision_dates": sorted(pending),
              "ineligible_candidate_dates": missing,
              "job_id": job_id}
    return data, state, status


def publish(directory, data, state, status):
    directory = Path(directory)
    validate_status(status)
    validate_state(state)
    if status["state"] not in ("success", "pending"):
        raise ValueError("Cannot publish an incomplete refresh")
    if (status["state_sha256"] != digest(state)
            or status["pending_revision_dates"] != state["pending_revision_dates"]):
        raise ValueError("Candidate state checksum mismatch")
    old, _ = load_data(directory)
    if data is not None:
        validate_data(data)
        if status["data_sha256"] != digest(data):
            raise ValueError("Publication checksum mismatch")
        if data["pending_revision_dates"] != status["pending_revision_dates"]:
            raise ValueError("Published revision markers do not match")
        if data["pending_revisions"] != state["pending_revisions"]:
            raise ValueError("Revision observation records do not match")
    elif status["data_sha256"] is not None or state["pending_revisions"]:
        raise ValueError("Publication has no data for its status")
    pending_status = dict(status, state="publishing")
    atomic_json(directory / STATUS_NAME, pending_status)
    data_replaced = False
    try:
        if old is not None and data != old:
            atomic_json(directory / BACKUP_NAME, old)
        atomic_json(directory / STATE_NAME, state)
        if data is not None and data != old:
            atomic_json(directory / DATA_NAME, data)
            data_replaced = True
        atomic_json(directory / STATUS_NAME, status)
    except Exception:
        if data_replaced:
            if old is not None:
                atomic_json(directory / DATA_NAME, old)
            else:
                (directory / DATA_NAME).unlink(missing_ok=True)
        raise


def failure_status(directory, now):
    atomic_json(Path(directory) / STATUS_NAME, {
        "schema_version": 1, "attempted_at": iso(now), "state": "failed",
        "message": "Refresh failed; previous validated data retained.",
    })


def assess_freshness(data, status, now, fallback=False, candidate_state=None):
    validate_data(data)
    published = timestamp(data["published_at"])
    source_observed = timestamp(data["source_observed_at"])
    latest = date.fromisoformat(data["latest_observation_date"])
    expected = (now - MIN_AGE).date() - timedelta(days=1)
    reasons = []
    if source_observed > now or published > now or now - source_observed > REFRESH_DEADLINE:
        reasons.append("Source verification or delivery overdue")
    if latest < expected:
        reasons.append("Latest eligible observation is delayed")
    if fallback:
        reasons.append("Using the previous validated export")
    if not status:
        reasons.append("Refresh status unavailable")
    elif status.get("state") == "failed":
        reasons.append("Refresh failed; showing previous validated data")
    else:
        if status.get("state") == "publishing":
            reasons.append("Publication incomplete")
        if status.get("data_sha256") != digest(data):
            reasons.append("Refresh status does not match the loaded export")
        if candidate_state is None:
            reasons.append("Candidate publication state unavailable")
        elif status.get("state_sha256") != digest(candidate_state):
            reasons.append("Candidate state does not match the publication")
    if (data["pending_revision_dates"] or (status or {}).get("pending_revision_dates")
            or (candidate_state or {}).get("pending_revision_dates")):
        reasons.append("Source revisions are awaiting validation")
    actual = {date.fromisoformat(row["date"]) for row in data["rows"]}
    first = min(actual)
    gaps = [(first + timedelta(days=i)).isoformat()
            for i in range((latest - first).days + 1)
            if first + timedelta(days=i) not in actual]
    return {"stale": bool(reasons), "reasons": reasons, "gaps": gaps,
            "observation_age_days": (now.date() - latest).days,
            "source_age_hours": max(0, (now - source_observed).total_seconds() / 3600),
            "publication_age_hours": max(0, (now - published).total_seconds() / 3600)}
