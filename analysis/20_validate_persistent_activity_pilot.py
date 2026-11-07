"""Offline SQL 41 validation, saved-baseline comparisons and SQL 42 controls.

Uses the unchanged result-55 validator. Reads monetary strings as Decimal and
writes only stdout unless an exclusive, previously nonexistent --output is given.
No network, query execution, credentials or configuration access.
"""

import argparse
import hashlib
import importlib.util
import sys
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("persistence_plan", ROOT / "analysis/19_persistent_activity_plan.py")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)
SOURCE = ROOT / "results/56_persistent_activity_pilot.json"
PLAN = ROOT / "results/55_persistent_activity_plan_and_saved_baselines.json"
NEXT_SQL = ROOT / "sql/42_persistent_activity_initial_receipt_pilot.sql"
SCHEMAS = {
    "SUMMARY": set("source_start source_end transaction_rows distinct_transaction_hashes observed_days observed_hours "
                   "missing_transaction_hashes missing_signer_accounts missing_receiver_accounts invalid_timestamps "
                   "invalid_conversion_cost_rows source_controls_passed cohort_count week_control_rows checkpoint_rows coverage_basis".split()),
    "WEEK_CONTROL": set("week_start week_end transactions distinct_transaction_hashes active_accounts observed_days observed_hours "
                        "invalid_conversion_cost_rows recorded_conversion_spending_near".split()),
    "CHECKPOINT": set("cohort_week cohort_week_end week_offset followup_week followup_week_end followup_complete source_controls_passed "
                      "measurement_available cohort_accounts observed_week_transactions returning_accounts returning_transactions "
                      "top_1_transactions top_10_transactions top_20_transactions sum_squared_returner_transactions "
                      "invalid_conversion_cost_rows recorded_conversion_spending_near return_at_1_and_4_accounts "
                      "repeated_checkpoint_returners_accounts any_return_weeks_1_to_4_accounts any_return_weeks_1_to_8_accounts attribution_scope".split()),
}


def identity(path):
    raw = path.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def validate(raw):
    saved_plan = base.decode(PLAN.read_bytes())
    for relative, expected in saved_plan["source_hashes"].items():
        base.require(identity(ROOT / relative) == expected, f"Result 55 input identity changed: {relative}")
    base.require(base.json_bytes(base.plan()) == PLAN.read_bytes(), "Result 55 did not reproduce byte-for-byte")
    rows = base.decode(raw)
    base.require(isinstance(rows, list), "Expected JSON array")
    for row in rows:
        base.require(isinstance(row, dict) and set(row) == {"row_kind", "record_json"}
                     and row["row_kind"] in SCHEMAS and isinstance(row["record_json"], str), "Unexpected outer schema")
        record = base.decode(row["record_json"])
        base.require(isinstance(record, dict) and set(record) == SCHEMAS[row["row_kind"]], "Unexpected nested schema")
        if row["row_kind"] == "SUMMARY":
            base.require(record["coverage_basis"] == "OBSERVED_RECORDS_ONLY_NOT_INDEPENDENT_COMPLETENESS", "Coverage scope changed")
        if row["row_kind"] == "CHECKPOINT":
            base.require(record["attribution_scope"] == "SUBMISSION_WEEK_OUTER_SIGNER_INITIAL_RECEIPT_ECONOMICS_NOT_EXTRACTED",
                         "Attribution scope changed")

    result = base.validate_export(raw)
    _, weekly, old_returns, conversion = base.controls()
    week_records = {r["week_start"]: r for r in result["weekly_controls"]}
    differences = []
    for key, row in week_records.items():
        base.require(base.count(row["invalid_conversion_cost_rows"]) <= base.count(row["transactions"]),
                     "Invalid weekly cost count exceeds transactions")
        if key in conversion and row["recorded_conversion_spending_near"] is not None:
            with localcontext() as ctx:
                ctx.prec = 80
                current = base.number(row["recorded_conversion_spending_near"])
                previous = base.number(conversion[key]["recorded_conversion_cost_near"])
                delta = current - previous
                differences.append({"week_start": key, "result56_near": str(current), "result36_near": str(previous),
                    "result56_minus_result36_near": str(delta),
                    "within_saved_arithmetic_screen": abs(delta) <= base.ARITHMETIC_TOLERANCE})

    overlap = 0
    for row in result["checkpoint_metrics"]:
        if not row["measurement_available"]:
            continue
        tx, n = base.count(row["returning_transactions"]), base.count(row["returning_accounts"])
        base.require(base.count(row["invalid_conversion_cost_rows"])
                     <= base.count(week_records[row["followup_week"]]["invalid_conversion_cost_rows"]),
                     "Returner invalid-cost count exceeds whole week")
        a, b, c = (base.count(row[f"top_{k}_transactions"]) for k in (1, 10, 20))
        baseline = weekly[row["followup_week"]]
        base.require(a <= base.count(baseline["top_1_account_transactions"])
                     and b <= base.count(baseline["top_10_accounts_transactions"])
                     and c <= base.count(baseline["top_100_accounts_transactions"]), "Concentration exceeds whole-week subset bound")
        base.require(b <= min(10, n)*a and c <= min(20, n)*a and c <= 2*b, "Impossible ranked concentration counts")
        base.require(all(min(k, n) <= amount <= tx - max(n-k, 0)
                         for k, amount in ((1, a), (10, b), (20, c))),
                     "Concentration leaves active accounts without a transaction")
        row["top_1_returner_transaction_share_pct"] = base.ratio(a, tx, 100)
        row["top_10_returner_transaction_share_pct"] = base.ratio(b, tx, 100)
        row["top_20_returner_transaction_share_pct"] = base.ratio(c, tx, 100)
        if (row["cohort_week"], base.count(row["week_offset"])) in old_returns:
            overlap += 1
    cohort_summary = []
    for cohort in base.COHORTS:
        points = [p for p in result["checkpoint_metrics"] if p["cohort_week"] == str(cohort)]
        row = points[0]
        repeated = row["repeated_checkpoint_returners_accounts"]
        cohort_summary.append({"cohort_week": str(cohort), "cohort_accounts": base.count(row["cohort_accounts"]),
            "repeated_checkpoint_returners_accounts": None if repeated is None else base.count(repeated),
            "repeated_checkpoint_return_share_pct": None if repeated is None else base.ratio(base.count(repeated), base.count(row["cohort_accounts"]), 100),
            "checkpoint_returners": {str(p["week_offset"]): p["returning_accounts"] for p in points},
            "checkpoint_return_shares_pct": {str(p["week_offset"]): p.get("exact_return_share_pct") for p in points}})
    focus = next(p for p in result["checkpoint_metrics"] if p["cohort_week"] == "2026-08-17" and p["week_offset"] == 8)
    maximum = max(differences, key=lambda r: abs(Decimal(r["result56_minus_result36_near"])))
    result.update({
        "source_export_sha256": hashlib.sha256(raw).hexdigest(), "source_export_bytes": len(raw),
        "result55_reproduced_byte_for_byte": True,
        "expected_export_records": 23, "complete_checkpoints": 9, "unavailable_checkpoints": 3,
        "overlapping_result11_counts_checked": overlap,
        "cohort_summary": cohort_summary,
        "conversion_comparisons": differences,
        "maximum_absolute_conversion_difference_near": str(abs(Decimal(maximum["result56_minus_result36_near"]))),
        "maximum_difference_week": maximum["week_start"],
        "arithmetic_screen_near": str(base.ARITHMETIC_TOLERANCE),
        "arithmetic_screen_scope": "Saved aggregate consistency only; not source accuracy or economic reconciliation.",
        "conversion_difference_assessment": "No count discrepancies. SQL 34 sums scaled FLOAT costs; SQL 41 sums BIGNUMERIC casts before scaling. The small differences are compatible with numeric conversion and aggregation order; aggregate exports cannot establish the exclusive cause.",
        "concentration_validation_scope": "Recomputed shares and HHI, integer squared-count bounds and whole-week subset bounds. No account IDs/count distributions are exported, so membership, rankings and squared sums cannot be independently reconstructed.",
        "missing_cost_validation_scope": ("All observed invalid-cost counts are zero. Null safeguards are checked structurally and with synthetic tests; this export does not exercise missing-cost cases."
            if base.count(result["source_summary"]["invalid_conversion_cost_rows"]) == 0
            else "Missing/invalid conversion costs suppress affected complete totals; subset invalid counts are bounded by whole-week counts."),
        "definitions": saved_plan["definitions"],
        "next_extraction": {
            "sql": str(NEXT_SQL.relative_to(ROOT)), "intended_result": "results/58_persistent_activity_initial_receipt_pilot.json",
            "cohort_week": "2026-08-17", "submission_week": "2026-10-12", "submission_week_end": "2026-10-18",
            "transaction_weeks": ["2026-08-17", "2026-08-24", "2026-09-14", "2026-10-12"],
            "outcome_and_block_lookup_start": "2026-10-12", "outcome_and_block_lookup_end": "2026-10-24",
            "expected_cohort_accounts": base.count(focus["cohort_accounts"]),
            "expected_exact_week_8_accounts": base.count(focus["returning_accounts"]),
            "expected_repeated_checkpoint_accounts": base.count(focus["repeated_checkpoint_returners_accounts"]),
            "expected_exact_week_8_transactions": base.count(focus["returning_transactions"]),
            "expected_exact_week_8_conversion_spending_near": focus["recorded_conversion_spending_near"],
            "population_warning": "Repeated checkpoint returners are a subset of exact-week +8 returners; groups overlap.",
            "scope": "Unique initial-receipt outcomes and recorded spending only, attributed to outer signers. Conversion uses submission week; initial-receipt costs use uniquely resolved execution dates. Six-day tail is a partial week; unresolved matches/costs remain unavailable. No descendants or complete-chain success.",
        },
    })
    return result


def report(source=SOURCE):
    result = validate(source.read_bytes())
    paths = {*base.FILES.values(), PLAN, source, ROOT / "sql/41_persistent_activity_transaction_pilot.sql",
             ROOT / "analysis/19_persistent_activity_plan.py", Path(__file__), NEXT_SQL,
             ROOT / "sql/34_weekly_transaction_conversion_costs.sql"}
    result["source_hashes"] = {str(p.relative_to(ROOT)): identity(p) for p in sorted(paths)}
    result["derivation"] = "python3 analysis/20_validate_persistent_activity_pilot.py; read saved inputs only, parse monetary strings as Decimal, reuse unchanged analysis/19 validation and reproduce result 55, calculate ratios at 60 digits and monetary differences at 80 digits. No source FLOAT precision is restored."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        with localcontext() as ctx:
            ctx.prec = 80
            raw = base.json_bytes(report(args.source.resolve()))
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
