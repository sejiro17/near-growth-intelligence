"""Offline persistence coverage plan, reference metrics and SQL 41 export checks.

plan reuses saved daily/weekly/cohort controls. validate reads a manually saved
SQL 41 JSON export. Default output is stdout; --output never overwrites a file.
No BigQuery, RPC or network code is imported or invoked.
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
COHORTS = tuple(date.fromisoformat(x) for x in ("2026-08-10", "2026-08-17", "2026-08-24", "2026-09-28"))
OFFSETS = (1, 4, 8)
START, END = date(2026, 8, 10), date(2026, 10, 18)
ARITHMETIC_TOLERANCE = Decimal("0.00001")
FILES = {
    "daily_counts": RESULTS / "02_daily_partition_counts_2026-07-01_to_2026-10-24.csv",
    "daily_checks": RESULTS / "03_daily_transaction_checks_2026-07-01_to_2026-10-24.csv",
    "weekly": RESULTS / "38_extended_weekly_signing_activity_2026-07-06_to_2026-10-18.csv",
    "returns": RESULTS / "11_weekly_account_returns_2026-08-24_to_2026-10-18.csv",
    "conversion": RESULTS / "36_weekly_transaction_conversion_costs_2026-08-24_to_2026-10-18.csv",
    "deletions": RESULTS / "17_spike_account_deletion_checks_2026-09-28_to_2026-10-11.csv",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value):
    require(type(value) in (str, int, Decimal), "Unexpected numeric representation")
    result = Decimal(value)
    require(result.is_finite(), "Nonfinite number")
    return result


def count(value):
    result = number(value)
    require(result >= 0 and result == result.to_integral_value(), "Invalid count")
    return int(result)


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")
    return json.loads(raw, parse_float=Decimal, parse_constant=invalid, object_pairs_hook=unique)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames and len(set(reader.fieldnames)) == len(reader.fieldnames), "Duplicate/missing CSV columns")
        rows = list(reader)
    require(rows and all(None not in row for row in rows), "Empty/malformed CSV")
    return rows


def keyed(rows, field):
    result = {row[field]: row for row in rows}
    require(len(result) == len(rows), f"Duplicate {field}")
    return result


def dates(start, end):
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def weeks(start=START, end=END):
    return [start + timedelta(weeks=i) for i in range((end - start).days // 7 + 1)]


def ratio(numerator, denominator, scale=1):
    if not denominator:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        return str(Decimal(scale) * numerator / denominator)


def controls():
    daily = keyed(read_csv(FILES["daily_checks"]), "block_date")
    daily_counts = keyed(read_csv(FILES["daily_counts"]), "block_date")
    expected = {str(x) for x in dates(date(2026, 7, 1), date(2026, 10, 24))}
    require(set(daily) == set(daily_counts) == expected, "Missing/unexpected saved daily coverage")
    invalid = ("missing_transaction_hashes", "missing_signer_accounts", "missing_receiver_accounts",
               "missing_timestamps", "timestamp_date_mismatches")
    for key, row in daily.items():
        require(count(row["transaction_rows"]) == count(row["distinct_transaction_hashes"])
                == count(daily_counts[key]["transaction_rows"]), "Saved transaction count mismatch")
        require(count(row["observed_hours"]) == 24 and all(count(row[x]) == 0 for x in invalid),
                "Saved day has invalid identity/coverage diagnostics")
    weekly = keyed(read_csv(FILES["weekly"]), "week_start")
    require(set(weekly) == {str(x) for x in weeks(date(2026, 7, 6), END)}, "Missing/unexpected weekly coverage")
    for key, row in weekly.items():
        start = date.fromisoformat(key)
        require(row["week_end"] == str(start + timedelta(days=6)), "Misaligned week end")
        require(count(row["transactions"]) == sum(count(daily[str(day)]["transaction_rows"]) for day in dates(start, start + timedelta(days=6))),
                "Daily/weekly transaction mismatch")
        require(count(row["signing_account_days"]) == sum(count(daily[str(day)]["active_signing_accounts"]) for day in dates(start, start + timedelta(days=6))),
                "Daily/weekly account-day mismatch")
    old_returns = {}
    for row in read_csv(FILES["returns"]):
        key = (row["cohort_week"], count(row["week_offset"]))
        require(key not in old_returns, "Duplicate saved cohort point")
        start, offset = date.fromisoformat(key[0]), key[1]
        require(row["followup_week"] == str(start + timedelta(weeks=offset))
                and row["followup_week_end"] == str(start + timedelta(weeks=offset, days=6)), "Saved follow-up date mismatch")
        size, active = count(row["cohort_accounts"]), count(row["active_cohort_accounts"])
        require(size == count(weekly[str(start)]["weekly_active_signing_accounts"]) and active <= size, "Saved cohort denominator mismatch")
        expected_pct = (Decimal(100) * active / size).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        require(number(row["cohort_active_share_pct"]) == expected_pct, "Saved return percentage mismatch")
        old_returns[key] = row
    conversion = keyed(read_csv(FILES["conversion"]), "week_start")
    for key, row in conversion.items():
        require(count(row["transactions"]) == count(weekly[key]["transactions"])
                == count(row["distinct_transaction_hashes"]), "Saved conversion transaction mismatch")
        require(all(count(row[x]) == 0 for x in ("missing_cost_records", "negative_cost_records", "nonfinite_cost_records")),
                "Saved conversion diagnostics invalid")
        require(number(row["recorded_conversion_cost_near"]) >= 0, "Invalid saved spending")
    return daily, weekly, old_returns, conversion


def plan():
    daily, weekly, old_returns, _ = controls()
    available = {date.fromisoformat(x) for x in daily}
    points = []
    for cohort in COHORTS:
        for offset in OFFSETS:
            start = cohort + timedelta(weeks=offset)
            end = start + timedelta(days=6)
            missing = [str(x) for x in dates(start, end) if x not in available]
            old = old_returns.get((str(cohort), offset))
            complete = not missing
            points.append({"cohort_week": str(cohort), "cohort_week_end": str(cohort + timedelta(days=6)),
                "cohort_accounts_saved": count(weekly[str(cohort)]["weekly_active_signing_accounts"]),
                "week_offset": offset, "followup_week": str(start), "followup_week_end": str(end),
                "complete_saved_transaction_followup": complete, "missing_saved_dates": missing,
                "initial_receipt_reference_window": "CHECKED_REFERENCE_REQUIRE_NEW_INITIAL_LINK_DIAGNOSTICS"
                    if complete and start >= date(2026, 8, 24) else "UNAVAILABLE_IN_INITIAL_EXECUTION_PILOT",
                "saved_exact_return_accounts": count(old["active_cohort_accounts"]) if old else None,
                "saved_exact_return_share_pct": old["cohort_active_share_pct"] if old else None,
                "returner_transactions": None, "returner_initial_receipt_spending_near": None})
    deletion_context = read_csv(FILES["deletions"])
    require(len(deletion_context) == 3, "Unexpected saved deletion context")
    for row in deletion_context:
        require(row["cohort_week"] == "2026-09-28" and row["followup_week"] == "2026-10-05"
                and row["deletion_target"] == "SIGNER_EQUALS_RECEIVER"
                and row["executor_check"] == "EXECUTOR_MATCHES_RECEIVER"
                and count(row["matching_outcome_rows"]) == count(row["deletion_transactions"]),
                "Deletion context identity/matching controls disagree")
    deletion_success = keyed([r for r in deletion_context if r["initial_receipt_status"] == "SUCCESS_VALUE"], "return_group")
    require(set(deletion_success) == {"ACTIVE_FOLLOWING_WEEK", "NOT_ACTIVE_FOLLOWING_WEEK"}, "Missing deletion context groups")
    spike = old_returns[("2026-09-28", 1)]
    absent = count(spike["cohort_accounts"]) - count(spike["active_cohort_accounts"])
    deleted_absent = count(deletion_success["NOT_ACTIVE_FOLLOWING_WEEK"]["signing_accounts"])
    require(deleted_absent <= absent, "Deletion accounts exceed absent cohort")
    paths = [*FILES.values(), Path(__file__), ROOT / "sql/41_persistent_activity_transaction_pilot.sql"]
    return {"source_hashes": {str(p.relative_to(ROOT)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size}
                              for p in sorted(paths)},
        "source_start": str(START), "source_end": str(END), "expected_source_days": 70,
        "expected_source_transactions": sum(count(weekly[str(w)]["transactions"]) for w in weeks()),
        "expected_export_rows": {"SUMMARY": 1, "WEEK_CONTROL": 10, "CHECKPOINT": 12},
        "cohort_points": points, "saved_spike_deletion_context": deletion_context,
        "saved_spike_lifecycle_comparison": {"cohort_accounts": count(spike["cohort_accounts"]),
            "exact_week_1_returners": count(spike["active_cohort_accounts"]), "absent_accounts": absent,
            "successful_self_delete_absent_accounts": deleted_absent,
            "successful_self_delete_absent_share_pct": ratio(deleted_absent, absent, 100),
            "successful_self_delete_returning_accounts": count(deletion_success["ACTIVE_FOLLOWING_WEEK"]["signing_accounts"]),
            "limitation": "Grouped observations do not establish deletion-before-return ordering, recreation, continuity or disjointness of failed/successful deletion account sets."},
        "definitions": {"population": "Distinct outer signers active in the starting week; creation history unavailable.",
            "exact_return": "Starting-week account active in the exact +k week; no intervening-week requirement.",
            "repeated_checkpoint_return": "Active at all exact +1/+4/+8 checkpoints, requiring all three complete follow-ups.",
            "any_return": "Separate union across every week in a complete 1..4 or 1..8 interval.",
            "transaction_share": "Returners' follow-up-week submissions divided by all observed submissions in that week.",
            "spending": "Stage 1 measures recorded transaction conversion by submission week; initial receipts require stage 2."},
        "limitations": ["Accounts and overlapping cohorts are not independent people or disjoint populations.",
            "Saved cohort/network aggregates cannot identify returners' transaction or execution-cost numerators.",
            "Observed daily coverage is not independent ingestion completeness.",
            "Incomplete follow-ups remain unavailable; earlier execution matching is separately qualified.",
            "Source FLOAT precision is not restored by Decimal or BIGNUMERIC; spending is not revenue or purchases."]}


def reference_metrics(rows, cohort, offset, complete_weeks):
    """Pure account/week reference for metric and join-grain regression tests."""
    require(cohort in complete_weeks, "Unavailable cohort baseline")
    by_week = defaultdict(dict)
    for row in rows:
        week, signer = row["week_start"], row["signer"]
        require(signer not in by_week[week], "Duplicate account/week grain")
        require(count(row["transactions"]) > 0, "Account/week must be active")
        if row.get("conversion_cost_near") is not None:
            require(number(row["conversion_cost_near"]) >= 0, "Negative reference spending")
        by_week[week][signer] = row
    membership = set(by_week[cohort])
    target = cohort + timedelta(weeks=offset)
    complete = target in complete_weeks
    active = membership & set(by_week[target]) if complete else set()
    counts = sorted((count(by_week[target][a]["transactions"]) for a in active), reverse=True)
    total = sum(count(r["transactions"]) for r in by_week[target].values()) if complete else None
    def intersection(offsets):
        wanted = [cohort + timedelta(weeks=k) for k in offsets]
        return len(membership.intersection(*(set(by_week[w]) for w in wanted))) if all(w in complete_weeks for w in wanted) else None
    def union(horizon):
        wanted = [cohort + timedelta(weeks=k) for k in range(1, horizon + 1)]
        return len(membership & set().union(*(set(by_week[w]) for w in wanted))) if all(w in complete_weeks for w in wanted) else None
    costs = [by_week[target][a].get("conversion_cost_near") for a in active]
    with localcontext() as ctx:
        ctx.prec = 78
        cost = str(sum((number(x) for x in costs), Decimal(0))) if complete and all(x is not None for x in costs) else None
    return {"cohort_accounts": len(membership), "returning_accounts": len(active) if complete else None,
        "returning_transactions": sum(counts) if complete else None, "observed_week_transactions": total,
        "top_1_transactions": sum(counts[:1]) if complete else None,
        "top_10_transactions": sum(counts[:10]) if complete else None,
        "top_20_transactions": sum(counts[:20]) if complete else None,
        "sum_squared_returner_transactions": sum(x*x for x in counts) if complete else None,
        "recorded_conversion_spending_near": cost,
        "return_at_1_and_4_accounts": intersection((1, 4)),
        "repeated_checkpoint_returners_accounts": intersection(OFFSETS),
        "any_return_weeks_1_to_4_accounts": union(4), "any_return_weeks_1_to_8_accounts": union(8)}


def validate_export(raw):
    daily, weekly, old_returns, conversion = controls()
    rows = decode(raw)
    require(isinstance(rows, list) and len(rows) == 23, "Expected complete 23-row export")
    grouped = defaultdict(list)
    for row in rows:
        require(set(row) == {"row_kind", "record_json"} and isinstance(row["record_json"], str), "Unexpected export schema")
        grouped[row["row_kind"]].append(decode(row["record_json"]))
    require({k: len(v) for k, v in grouped.items()} == {"SUMMARY": 1, "WEEK_CONTROL": 10, "CHECKPOINT": 12}, "Row kinds/counts disagree")
    summary = grouped["SUMMARY"][0]
    require(summary["source_controls_passed"] is True and summary["source_start"] == str(START)
            and summary["source_end"] == str(END), "Invalid source coverage/identity controls")
    require(count(summary["transaction_rows"]) == count(summary["distinct_transaction_hashes"])
            == sum(count(weekly[str(w)]["transactions"]) for w in weeks()), "Global transaction controls disagree")
    require(count(summary["observed_days"]) == 70 and count(summary["observed_hours"]) == 1680, "Incomplete days/hours")
    require(count(summary["cohort_count"]) == 4 and count(summary["week_control_rows"]) == 10
            and count(summary["checkpoint_rows"]) == 12, "Summary record counts disagree")
    for key in ("missing_transaction_hashes", "missing_signer_accounts", "missing_receiver_accounts", "invalid_timestamps"):
        require(count(summary[key]) == 0, "Invalid source records")
    week_records = keyed(grouped["WEEK_CONTROL"], "week_start")
    require(set(week_records) == {str(w) for w in weeks()}, "Unexpected/missing week controls")
    warnings = []
    for key, row in week_records.items():
        require(row["week_end"] == str(date.fromisoformat(key) + timedelta(days=6)), "Wrong week end")
        require(count(row["observed_days"]) == 7 and count(row["observed_hours"]) == 168, "Incomplete weekly coverage")
        require(count(row["transactions"]) == count(row["distinct_transaction_hashes"]) == count(weekly[key]["transactions"])
                and count(row["active_accounts"]) == count(weekly[key]["weekly_active_signing_accounts"]), "Weekly controls disagree")
        cost = row["recorded_conversion_spending_near"]
        require((cost is None) == (count(row["invalid_conversion_cost_rows"]) > 0), "Cost-null safeguard broken")
        if cost is not None:
            require(number(cost) >= 0, "Negative spending")
            if key in conversion and abs(number(cost) - number(conversion[key]["recorded_conversion_cost_near"])) > ARITHMETIC_TOLERANCE:
                warnings.append({"week": key, "check": "SAVED_CONVERSION_AGGREGATE_DIFFERENCE_REQUIRES_REVIEW"})
    require(sum(count(r["invalid_conversion_cost_rows"]) for r in week_records.values())
            == count(summary["invalid_conversion_cost_rows"]), "Global/weekly invalid-cost counts disagree")
    points = {}
    monetary_counts = ("returning_accounts", "returning_transactions", "observed_week_transactions", "top_1_transactions",
        "top_10_transactions", "top_20_transactions", "sum_squared_returner_transactions", "invalid_conversion_cost_rows")
    for row in grouped["CHECKPOINT"]:
        cohort, offset = date.fromisoformat(row["cohort_week"]), count(row["week_offset"])
        key = (str(cohort), offset)
        require(cohort in COHORTS and offset in OFFSETS and key not in points, "Duplicate/unexpected cohort checkpoint")
        points[key] = row
        target = cohort + timedelta(weeks=offset)
        complete = target + timedelta(days=6) <= END
        require(row["cohort_week_end"] == str(cohort + timedelta(days=6)) and row["followup_week"] == str(target)
                and row["followup_week_end"] == str(target + timedelta(days=6)), "Checkpoint dates disagree")
        require(row["source_controls_passed"] is True and row["followup_complete"] is complete
                and row["measurement_available"] is complete, "Follow-up availability mismatch")
        size = count(row["cohort_accounts"])
        require(size == count(weekly[str(cohort)]["weekly_active_signing_accounts"]), "Cohort size mismatch")
        for field, horizon in (("return_at_1_and_4_accounts", 4), ("any_return_weeks_1_to_4_accounts", 4),
                               ("repeated_checkpoint_returners_accounts", 8), ("any_return_weeks_1_to_8_accounts", 8)):
            available = cohort + timedelta(weeks=horizon, days=6) <= END
            require((row[field] is not None) == available, "Incomplete-horizon safeguard broken")
            if available:
                require(count(row[field]) <= size, "Return subset exceeds cohort")
        if not complete:
            require(all(row[k] is None for k in (*monetary_counts, "recorded_conversion_spending_near")), "Incomplete follow-up was zero-filled")
            continue
        for field in monetary_counts:
            count(row[field])
        n, tx = count(row["returning_accounts"]), count(row["returning_transactions"])
        require(n <= size and n <= count(week_records[str(target)]["active_accounts"])
                and n <= tx <= count(row["observed_week_transactions"]) == count(weekly[str(target)]["transactions"]), "Returner count/share bounds invalid")
        a, b, e = (count(row[k]) for k in ("top_1_transactions", "top_10_transactions", "top_20_transactions"))
        require(0 <= a <= b <= e <= tx and (n > 0 or (tx == a == b == e == 0)), "Concentration counts invalid")
        squared = count(row["sum_squared_returner_transactions"])
        require(tx <= squared <= a*tx and squared*n >= tx*tx, "Invalid squared counts")
        require(count(row["invalid_conversion_cost_rows"]) <= tx, "Invalid-cost rows exceed transactions")
        if n <= 10:
            require(b == tx, "Top ten omit observed returners")
        if n <= 20:
            require(e == tx, "Top twenty omit observed returners")
        if key in old_returns:
            require(n == count(old_returns[key]["active_cohort_accounts"]), "Overlap with result 11 disagrees")
        cost = row["recorded_conversion_spending_near"]
        require((cost is None) == (count(row["invalid_conversion_cost_rows"]) > 0), "Returner cost-null safeguard broken")
        if cost is not None:
            require(number(cost) >= 0, "Negative returner spending")
            total_cost = week_records[str(target)]["recorded_conversion_spending_near"]
            if total_cost is not None:
                require(number(cost) <= number(total_cost), "Returner spending exceeds week total")
        row["exact_return_share_pct"] = ratio(n, size, 100)
        row["returner_transaction_share_pct"] = ratio(tx, count(row["observed_week_transactions"]), 100)
        row["returner_hhi"] = ratio(count(row["sum_squared_returner_transactions"]), tx*tx)
    require(set(points) == {(str(c), k) for c in COHORTS for k in OFFSETS}, "Missing checkpoint keys")
    for cohort in COHORTS:
        group = [points[(str(cohort), k)] for k in OFFSETS]
        for field in ("cohort_accounts", "return_at_1_and_4_accounts", "repeated_checkpoint_returners_accounts",
                      "any_return_weeks_1_to_4_accounts", "any_return_weeks_1_to_8_accounts"):
            require(all(r[field] == group[0][field] for r in group), "Cohort-level repeated metric differs between checkpoints")
        first, fourth, eighth = group
        pair, repeated = first["return_at_1_and_4_accounts"], first["repeated_checkpoint_returners_accounts"]
        if pair is not None:
            size = count(first["cohort_accounts"])
            require(max(0, count(first["returning_accounts"]) + count(fourth["returning_accounts"]) - size)
                    <= count(pair) <= min(count(first["returning_accounts"]), count(fourth["returning_accounts"]))
                    and count(first["any_return_weeks_1_to_4_accounts"]) >= max(count(first["returning_accounts"]), count(fourth["returning_accounts"])), "Intersection/union bounds invalid")
        if repeated is not None:
            require(max(0, count(pair) + count(eighth["returning_accounts"]) - count(first["cohort_accounts"]))
                    <= count(repeated) <= min(count(pair), count(eighth["returning_accounts"]))
                    and count(first["any_return_weeks_1_to_8_accounts"]) >= max(count(first["any_return_weeks_1_to_4_accounts"]), count(eighth["returning_accounts"])), "Eight-week bounds invalid")
    return {"validation": "SAVED_ARITHMETIC_REVIEW_REQUIRED" if warnings else "STRUCTURAL_AND_SAVED_CONTROL_CHECKS_PASSED", "warnings": warnings,
            "source_summary": summary, "weekly_controls": [week_records[k] for k in sorted(week_records)],
            "checkpoint_metrics": [points[k] for k in sorted(points)],
            "limitation": "Aggregate checks cannot independently reconstruct membership; initial-receipt outcomes/spending are not extracted."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    planner = subs.add_parser("plan")
    validator = subs.add_parser("validate")
    validator.add_argument("--source", type=Path, required=True)
    for sub in (planner, validator):
        sub.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = plan() if args.command == "plan" else validate_export(args.source.read_bytes())
        raw = json_bytes(result)
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(raw)
        else:
            print(raw.decode(), end="")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
