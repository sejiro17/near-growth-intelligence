"""Validate the saved SQL 43 export offline; preserve all monetary strings.

No collection code is executed. Default output is stdout; explicit outputs are
exclusive. Current SQL 43's proven trailing-space difference is recorded rather
than modifying either SQL or historical validation artifacts.
"""

import argparse
import hashlib
import importlib.util
import sys
from collections import Counter, defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("initial_validation", ROOT / "analysis/21_validate_initial_receipt_pilot.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
b = p.b
SOURCE = ROOT / "results/60_persistent_activity_shared_week_initial_receipts.json"
SAVED = ROOT / "results/59_persistent_activity_initial_receipt_validation.json"
SQL = ROOT / "sql/43_persistent_activity_shared_week_initial_receipts.sql"
START, END, TAIL = date(2026, 10, 5), date(2026, 10, 17), date(2026, 10, 12)
WEEKS = {"2026-08-10", "2026-08-17", "2026-09-07", "2026-09-28", "2026-10-05"}
POPS = ("AUG10_EXACT_WEEK8", "AUG10_REPEATED_CHECKPOINTS", "SEP28_EXACT_WEEK1")
SCHEMAS = {**p.SCHEMAS,
    "SUMMARY": p.SCHEMAS["SUMMARY"] - {"cohort_week", "cohort_accounts", "exact_week_8_accounts", "repeated_checkpoint_accounts"} | {"matching_group_controls"},
    "POPULATION": p.SCHEMAS["POPULATION"] | set("week_offset return_definition expected_cohort_accounts expected_accounts expected_transactions expected_conversion_near group_matches_result56".split())}


def preflight():
    saved = b.decode(SAVED.read_bytes())
    regenerated = p.report()
    exact = b.json_bytes(regenerated) == SAVED.read_bytes()
    provenance = {"result59_exact_with_current_files": exact, "recorded_inputs_and_metrics_reproduced": True}
    if not exact:
        relative = str(SQL.relative_to(ROOT))
        current, expected = SQL.read_bytes(), saved["source_hashes"][relative]
        # Accept only the observed space after the final statement, proven by SHA.
        candidate = current[:-2]+current[-1:]
        b.require(current.endswith(b"; \n") and len(candidate) == expected["bytes"]
                  and hashlib.sha256(candidate).hexdigest() == expected["sha256"], "Unverified SQL 43 change")
        regenerated["source_hashes"][relative] = expected
        b.require(b.json_bytes(regenerated) == SAVED.read_bytes(), "Result 59 metrics/other inputs changed")
        provenance.update({"difference": "One extra space after SQL 43's final semicolon and before its final LF; recorded bytes/hash recovered in memory only.",
                           "recorded_sql43": expected, "current_sql43": p.prior.identity(SQL)})
    baseline = b.decode(p.SAVED.read_bytes())
    points = {(r["cohort_week"], r["week_offset"]): r for r in baseline["checkpoint_metrics"]}
    a, z = points[("2026-08-10", 8)], points[("2026-09-28", 1)]
    expected = {
        POPS[0]: (a["cohort_week"], 8, "EXACT_WEEK_RETURNERS", a["cohort_accounts"], a["returning_accounts"], a["returning_transactions"], a["recorded_conversion_spending_near"]),
        POPS[1]: (a["cohort_week"], 8, "ALL_THREE_EXACT_CHECKPOINTS_1_4_8", a["cohort_accounts"], a["repeated_checkpoint_returners_accounts"], None, None),
        POPS[2]: (z["cohort_week"], 1, "EXACT_WEEK_RETURNERS", z["cohort_accounts"], z["returning_accounts"], z["returning_transactions"], z["recorded_conversion_spending_near"])}
    return baseline, expected, provenance


def validate(raw):
    baseline, expected, provenance = preflight()
    rows = b.decode(raw)
    b.require(isinstance(rows, list), "Expected JSON array")
    export_rows = len(rows)
    groups = defaultdict(list)
    for row in rows:
        b.require(isinstance(row, dict) and set(row) == {"row_kind", "record_json"}
                  and row["row_kind"] in SCHEMAS and isinstance(row["record_json"], str), "Unexpected outer schema")
        record = b.decode(row["record_json"])
        b.require(isinstance(record, dict) and set(record) == SCHEMAS[row["row_kind"]], "Unexpected nested schema")
        groups[row["row_kind"]].append(record)
    b.require(len(groups["SUMMARY"]) == 1, "Expected one summary")
    s = groups["SUMMARY"][0]
    b.require(len(groups["WEEK_CONTROL"]) == b.count(s["week_control_records"]) == 5
              and len(groups["POPULATION"]) == b.count(s["population_records"]) == 3
              and len(groups["ASSESSMENT_BUCKET"]) == b.count(s["bucket_records"])
              and export_rows == 9+b.count(s["bucket_records"]), "Incomplete export")
    b.require((s["submission_week"], s["submission_week_end"], s["lookup_end"]) == (str(START), "2026-10-11", str(END)), "Wrong observation dates")
    b.require(s["scope"] == "OVERLAPPING_GROUPS_INITIAL_RECEIPTS_ONLY_NOT_COMPLETE_CHAIN_OR_REVENUE"
              and s["coverage_basis"] == "OWNERSHIP_COUNTS_BOUNDED_TO_FIVE_TX_WEEKS_OBSERVED_COVERAGE_ONLY", "Wrong evidence scope")
    for key, value in s.items():
        if key not in {"submission_week", "submission_week_end", "lookup_end", "scope", "coverage_basis", "result56_controls_passed"}:
            b.count(value)
    weeks = b.keyed(groups["WEEK_CONTROL"], "week_start")
    b.require(set(weeks) == WEEKS, "Missing/duplicate/unexpected source weeks")
    old_weeks = {r["week_start"]: r for r in baseline["weekly_controls"]}
    for key, row in weeks.items():
        for field in ("transactions", "distinct_transaction_hashes", "active_accounts", "observed_days", "observed_hours", "invalid_conversion_cost_rows"):
            b.require(b.count(row[field]) == b.count(old_weeks[key][field]), "Saved weekly count discrepancy")
        b.require(row["matches_result56"] is True and row["invalid_conversion_cost_rows"] == 0, "Weekly controls failed")
        p.compare_money(row["recorded_conversion_spending_near"], old_weeks[key]["recorded_conversion_spending_near"], b.ARITHMETIC_TOLERANCE)
    b.require(s["result56_controls_passed"] is True and b.count(s["transaction_rows"]) == b.count(s["distinct_transaction_hashes"])
              == sum(b.count(r["transactions"]) for r in weeks.values()) and s["observed_days"] == 35 and s["observed_hours"] == 840
              and s["invalid_identity_or_timestamp_rows"] == 0 and s["matching_week_controls"] == 5 and s["matching_group_controls"] == 3,
              "Source identity/coverage controls failed")
    union_tx, union_accounts = b.count(s["selected_transactions"]), b.count(s["selected_accounts"])
    b.require(b.count(s["classified_transaction_rows"]) == b.count(s["classified_distinct_transaction_hashes"]) == union_tx,
              "Classification multiplied or lost transactions")
    ids, matched, multi, observations = (b.count(s[k]) for k in ("selected_distinct_receipt_ids", "receipt_ids_with_observed_outcomes",
                                                               "receipt_ids_with_multiple_outcomes", "selected_outcome_observations"))
    b.require(multi <= matched <= ids <= union_tx and observations >= matched+multi, "Outcome count diagnostics disagree")
    if multi == 0:
        b.require(observations == matched, "Unique outcome observations disagree")
    b.require(0 <= s["observed_outcome_days"] <= 13 and 0 <= s["observed_block_days"] <= 13
              and s["observed_outcome_partition_rows"] >= observations and s["observed_block_partition_rows"] >= s["observed_block_days"], "Invalid lookup coverage")
    lookup_complete = s["observed_outcome_days"] == s["observed_block_days"] == 13
    populations = b.keyed(groups["POPULATION"], "population")
    b.require(set(populations) == set(POPS), "Wrong populations")
    buckets, keys, samples, sample_keys = defaultdict(list), set(), {}, set()
    sample_receipt_owners = {}
    mismatches = defaultdict(Counter)
    for row in groups["ASSESSMENT_BUCKET"]:
        pop = row["population"]
        b.require(pop in POPS and row["submission_week"] == str(START), "Wrong bucket population/date")
        key = (pop, row["assessment"], row["observed_initial_status"], row["cost_check"], row["execution_date"], row["execution_week"])
        b.require(key not in keys, "Duplicate assessment bucket")
        keys.add(key)
        n = b.count(row["transactions"])
        b.require(n > 0 and b.count(row["distinct_transaction_hashes"]) == n and row["assessment"] in p.ASSESSMENTS
                  and row["observed_initial_status"] in p.STATUSES, "Invalid bucket counts/status")
        assessed = row["assessment"] == "ASSESSED_INITIAL_RECEIPT"
        valid = assessed and row["cost_check"] == "VALID_COST"
        if assessed:
            day = date.fromisoformat(row["execution_date"])
            b.require(START <= day <= END and row["execution_week"] == str(day-timedelta(days=day.weekday()))
                      and row["observed_initial_status"] != "UNAVAILABLE_OR_OTHER" and row["cost_check"] in p.BAD_COSTS | {"VALID_COST"}
                      and b.count(row["matched_outcome_observations"]) == n, "Invalid assessed attribution")
        else:
            b.require(row["execution_date"] is None and row["execution_week"] is None
                      and row["cost_check"] == "UNASSESSED_LINK_OR_EXECUTION", "Unassessed attribution was filled")
        b.require(b.count(row["valid_initial_cost_transactions"]) == (n if valid else 0), "Cost coverage discrepancy")
        if valid:
            p.money(row["valid_assessed_initial_spending_subtotal_near"])
        else:
            b.require(row["valid_assessed_initial_spending_subtotal_near"] is None, "Missing-cost null safeguard broken")
        b.require(b.count(row["partial_tail_transactions"]) == (n if assessed and day >= TAIL else 0), "Tail count discrepancy")
        examples = row["diagnostic_examples"]
        b.require(isinstance(examples, list) and len(examples) == min(3, n)
                  and row["example_scope"] == "UP_TO_THREE_EXAMPLES_NOT_CANONICAL_MATCH_SELECTION", "Truncated diagnostic examples")
        b.require([e["transaction_hash"] for e in examples] == sorted(e["transaction_hash"] for e in examples), "Example ordering mismatch")
        for e in examples:
            b.require(set(e) == p.EXAMPLE_SCHEMA, "Unexpected example schema")
            p.chain_id(e["transaction_hash"])
            sample_key = (pop, e["transaction_hash"])
            b.require(sample_key not in sample_keys, "Duplicate example transaction within group")
            sample_keys.add(sample_key)
            other = samples.get(e["transaction_hash"])
            b.require(other is None or other == e, "Shared example identity disagreement")
            samples[e["transaction_hash"]] = e
            if assessed:
                for field in ("converted_into_receipt_id", "outcome_record_hash", "executed_in_block_hash"):
                    p.chain_id(e[field])
                rid = e["converted_into_receipt_id"]
                b.require(rid not in sample_receipt_owners or sample_receipt_owners[rid] == e["transaction_hash"], "Shared initial receipt in assessed examples")
                sample_receipt_owners[rid] = e["transaction_hash"]
                actual, record = p.stamp(e["execution_time"]), p.stamp(e["outcome_record_time"])
                b.require(actual.date() == day and str(record.date()) == e["outcome_record_date"] and START <= record.date() <= END
                          and e["raw_status"] == row["observed_initial_status"], "Example timestamp/status disagreement")
                mismatches[pop]["hash"] += e["outcome_record_hash"] != e["executed_in_block_hash"]
                mismatches[pop]["time"] += actual != record
        buckets[pop].append(row)
    reports = []
    network_tx = b.count(weeks[str(START)]["transactions"])
    for pop in POPS:
        row, parts = populations[pop], buckets[pop]
        cohort, offset, definition, cohort_n, accounts, expected_tx, expected_cost = expected[pop]
        for field, value in (("cohort_week", cohort), ("week_offset", offset), ("return_definition", definition),
                             ("expected_cohort_accounts", cohort_n), ("expected_accounts", accounts), ("expected_transactions", expected_tx)):
            b.require(row[field] == value, "Frozen cohort/group controls disagree")
        p.nullable_money(row["expected_conversion_near"], expected_cost)
        b.require(row["observed_accounts"] == accounts and row["group_matches_result56"] is True
                  and row["result56_controls_passed"] is True and row["lookup_days_observed"] is lookup_complete
                  and row["submission_week"] == str(START), "Population membership/coverage failed")
        n = b.count(row["transactions"])
        b.require(accounts <= n <= network_tx and n == b.count(row["distinct_transaction_hashes"])
                  == sum(b.count(r["transactions"]) for r in parts), "Population transaction totals disagree")
        if expected_tx is not None:
            b.require(n == expected_tx, "Saved returner transactions disagree")
        invalid_conversion = b.count(row["invalid_conversion_rows"])
        b.require(invalid_conversion == 0 and row["recorded_conversion_spending_near"] is not None, "Conversion controls failed")
        p.money(row["recorded_conversion_spending_near"])
        if expected_cost is not None:
            p.compare_money(row["recorded_conversion_spending_near"], expected_cost, b.ARITHMETIC_TOLERANCE)
        assessed = [r for r in parts if r["assessment"] == "ASSESSED_INITIAL_RECEIPT"]
        assessed_n = sum(b.count(r["transactions"]) for r in assessed)
        valid_n = sum(b.count(r["valid_initial_cost_transactions"]) for r in parts)
        invalid_n = sum(b.count(r["transactions"]) for r in assessed if r["cost_check"] != "VALID_COST")
        for field, value in (("assessed_initial_receipts", assessed_n), ("unassessed_initial_receipts", n-assessed_n),
                             ("valid_initial_cost_transactions", valid_n), ("invalid_assessed_cost_rows", invalid_n)):
            b.require(b.count(row[field]) == value, "Population/bucket coverage discrepancy")
        subtotal = p.sum_money(r["valid_assessed_initial_spending_subtotal_near"] for r in parts if r["valid_assessed_initial_spending_subtotal_near"] is not None)
        p.nullable_money(row["valid_assessed_initial_spending_subtotal_near"], subtotal)
        p.nullable_money(row["complete_initial_receipt_spending_near"], subtotal if valid_n == n and lookup_complete else None)
        success = sum(b.count(r["transactions"]) for r in assessed if r["observed_initial_status"] in p.SUCCESS)
        failure = assessed_n-success
        a, sa, fa = (b.count(row[k]) for k in ("accounts_with_assessed_initial_receipts", "accounts_with_successful_initial_receipts", "accounts_with_failed_initial_receipts"))
        b.require(a <= min(accounts, assessed_n) and sa <= min(a, success) and fa <= min(a, failure)
                  and a <= sa+fa <= 2*a and (assessed_n != n or a == accounts), "Outcome account counts disagree")
        lo, hi = row["minimum_assessed_execution_lag_microseconds"], row["maximum_assessed_execution_lag_microseconds"]
        b.require((lo is None) == (hi is None) == (assessed_n == 0), "Lag null safeguard broken")
        if assessed_n:
            b.require(b.count(lo) <= b.count(hi) <= 13*86400*1000000, "Invalid execution-lag bounds")
        b.require(mismatches[pop]["hash"] <= b.count(row["record_execution_hash_disagreements"])
                  and mismatches[pop]["time"] <= b.count(row["record_execution_time_disagreements"]), "Hash/time summary disagrees with examples")
        reports.append({"population": pop, "observed": row, "exact_return_share_pct": b.ratio(accounts, cohort_n, 100),
            "transaction_share_of_observed_week_pct": b.ratio(n, network_tx, 100), "successful_initial_receipts": success,
            "failed_initial_receipts": failure, "initial_success_share_pct": b.ratio(success, n, 100),
            "initial_failure_share_pct": b.ratio(failure, n, 100), "accounts_with_both_success_and_failure": sa+fa-a,
            "by_status": p.aggregate(assessed, "observed_initial_status"), "by_execution_date": p.aggregate(parts, "execution_date"),
            "exclusion_counts": {reason: sum(b.count(r["transactions"]) for r in parts if r["assessment"] == reason)
                                 for reason in sorted(p.ASSESSMENTS - {"ASSESSED_INITIAL_RECEIPT"})},
            "tail_transactions": sum(b.count(r["partial_tail_transactions"]) for r in parts),
            "tail_spending_subtotal_near": p.sum_money(r["valid_assessed_initial_spending_subtotal_near"] for r in parts
                if r["partial_tail_transactions"] and r["valid_assessed_initial_spending_subtotal_near"] is not None)})
    a, repeated, z = (populations[k] for k in POPS)
    for field in ("transactions", "observed_accounts", "assessed_initial_receipts", "unassessed_initial_receipts", "valid_initial_cost_transactions", "invalid_assessed_cost_rows"):
        b.require(b.count(repeated[field]) <= b.count(a[field]), "Repeated subset exceeds August exact-return group")
    for row in buckets[POPS[1]]:
        match = next((r for r in buckets[POPS[0]] if all(r[k] == row[k] for k in ("assessment", "observed_initial_status", "cost_check", "execution_date"))), None)
        b.require(match is not None and row["transactions"] <= match["transactions"], "Repeated bucket exceeds enclosing population")
        if row["valid_assessed_initial_spending_subtotal_near"] is not None:
            b.require(p.money(row["valid_assessed_initial_spending_subtotal_near"]) <= p.money(match["valid_assessed_initial_spending_subtotal_near"]), "Repeated spending exceeds enclosing bucket")
    for field, union in (("transactions", union_tx), ("observed_accounts", union_accounts)):
        b.require(max(a[field], z[field]) <= union <= a[field]+z[field], "Invalid population union")
    b.require(union_tx <= network_tx and union_accounts <= weeks[str(START)]["active_accounts"], "Union exceeds observed week")
    overlap_accounts = a["observed_accounts"]+z["observed_accounts"]-union_accounts
    overlap_tx = a["transactions"]+z["transactions"]-union_tx
    all_assessed = all(r["unassessed_initial_receipts"] == 0 for r in populations.values())
    if all_assessed:
        b.require(ids == matched == observations == union_tx and multi == 0, "Assessed groups contradict union receipt/outcome diagnostics")
    ready = lookup_complete and all_assessed and all(r["invalid_assessed_cost_rows"] == 0 for r in populations.values())
    return {"validation": "STRUCTURAL_ARITHMETIC_AND_SAVED_CONTROL_CHECKS_PASSED", "publication_ready": ready,
        "measurement_phase": "CLOSED_WITH_STATED_LIMITATIONS" if ready else "REVIEW_REQUIRED_FOR_EXECUTION_CLAIMS",
        "source_export_sha256": hashlib.sha256(raw).hexdigest(), "source_export_bytes": len(raw), "export_rows": export_rows,
        "row_kinds": {k: len(v) for k, v in sorted(groups.items())}, "prior_validation_provenance": provenance,
        "source_summary": s, "weekly_controls": [weeks[k] for k in sorted(weeks)], "populations": reports,
        "unique_diagnostic_transactions_checked": len(samples), "diagnostic_example_occurrences_checked": len(sample_keys),
        "overlap": {"basis": "SQL 43's unique selected union includes August exact +8 and September exact +1; the repeated group is a subset of the former. Inclusion-exclusion uses saved aggregate counts, not independently reconstructed IDs.",
            "union_accounts": union_accounts, "union_transactions": union_tx, "august_and_september_accounts": overlap_accounts,
            "august_and_september_transactions": overlap_tx, "august_transactions_also_in_september_share_pct": b.ratio(overlap_tx, a["transactions"], 100),
            "repeated_transactions_share_of_august_exact_pct": b.ratio(repeated["transactions"], a["transactions"], 100),
            "union_or_intersection_receipt_spending_near": None, "repeated_and_september_exact_membership": None},
        "limitations": ["Populations overlap and follow-up horizons differ. Descriptive outcome/spending differences do not identify a causal cohort effect. Accounts are outer signers, not verified people or newly created accounts.",
            "Observed source weeks/days and matching diagnostics do not independently establish complete ingestion. Receipt-owner uniqueness is bounded to five transaction weeks.",
            "Only initial receipts are assessed. SUCCESS_RECEIPT_ID is not complete-chain success; descendant costs and outcomes remain unavailable.",
            "Execution lookups cover 5–17 October. The 12–17 October tail is six days, not a complete UTC week; elapsed follow-up varies by submission date. Missing matches/costs remain unavailable.",
            "Monetary strings and Decimal preserve saved arithmetic, not integer source accuracy. Costs originate as FLOAT. The 0.00001 NEAR baseline screen is not an economic or source-precision tolerance; internal subtotal identities are exact.",
            "Diagnostic examples do not include submission timestamps, executor IDs or execution heights, so SQL's lag/executor/height tests cannot be independently recomputed for every transaction offline.",
            "Recorded conversion and initial-receipt spending are distinct components; neither demonstrates revenue, fresh token purchases, burn, persistent holdings or holder value. Independent issuance and actual supply burn remain unresolved."],
        "unavailable": {"complete_chain_success": None, "descendant_spending_near": None, "revenue_origin": None, "independent_issuance_near": None, "actual_native_burn_near": None}}


def report(source=SOURCE):
    result = validate(source.read_bytes())
    paths = {ROOT / path for path in b.decode(SAVED.read_bytes())["source_hashes"]}
    paths.update({source, SAVED, Path(__file__)})
    result["source_hashes"] = {str(path.relative_to(ROOT)): p.prior.identity(path) for path in sorted(paths)}
    result["derivation"] = "python3 -B analysis/22_validate_shared_week_receipts.py; saved inputs only, strict duplicate-key JSON decoding, integer counts and 80-digit Decimal monetary sums via analysis/21 helpers; ratios at 60 digits. No source requests."
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = b.json_bytes(report(args.source.resolve()))
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(raw)
        else:
            print(raw.decode(), end="")
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Validation stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
