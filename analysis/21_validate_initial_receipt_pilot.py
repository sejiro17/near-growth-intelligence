"""Offline validation of manually collected SQL 42 initial-receipt evidence.

Reproduces result 57's recorded inputs/metrics, checks SQL 42 identities and examples,
and derives status/date distributions using Decimal. No network code is used.
Default output is stdout; --output exclusively creates a new derived artifact.
"""

import argparse
import hashlib
import importlib.util
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("persistence_validation", ROOT / "analysis/20_validate_persistent_activity_pilot.py")
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
b = prior.base
SOURCE = ROOT / "results/58_persistent_activity_initial_receipt_pilot.json"
SAVED = ROOT / "results/57_persistent_activity_pilot_validation.json"
EXTENSION = ROOT / "sql/43_persistent_activity_shared_week_initial_receipts.sql"
POPS = ("EXACT_WEEK_8_RETURNERS", "REPEATED_CHECKPOINT_RETURNERS")
WEEKS = {"2026-08-17", "2026-08-24", "2026-09-14", "2026-10-12"}
START, END = date(2026, 10, 12), date(2026, 10, 24)
SUCCESS = {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID"}
STATUSES = SUCCESS | {"FAILURE", "UNAVAILABLE_OR_OTHER"}
BAD_COSTS = {"MISSING_COST", "NONFINITE_COST", "NEGATIVE_COST", "UNREPRESENTABLE_COST"}
ASSESSMENTS = {"MISSING_INITIAL_RECEIPT_ID", "INVALID_INITIAL_RECEIPT_ID", "SHARED_INITIAL_RECEIPT_ID",
    "NO_OUTCOME_IN_LOOKUP_WINDOW", "MULTIPLE_OUTCOME_OBSERVATIONS", "MISSING_EXECUTION_HASH",
    "EXECUTION_BLOCK_UNAVAILABLE_OR_BOUNDARY", "MULTIPLE_EXECUTION_BLOCK_OBSERVATIONS",
    "INVALID_EXECUTION_BLOCK", "INVALID_OUTCOME_RECORD_TIME", "EXECUTOR_MISMATCH_OR_UNAVAILABLE",
    "STATUS_UNAVAILABLE_OR_UNRECOGNIZED", "NEGATIVE_EXECUTION_LAG", "EXECUTION_AFTER_LOOKUP_CUTOFF",
    "ASSESSED_INITIAL_RECEIPT"}
SCHEMAS = {
    "SUMMARY": set("cohort_week submission_week submission_week_end lookup_end transaction_rows distinct_transaction_hashes "
        "observed_days observed_hours invalid_identity_or_timestamp_rows cohort_accounts exact_week_8_accounts "
        "repeated_checkpoint_accounts selected_transactions selected_accounts matching_week_controls result56_controls_passed "
        "observed_outcome_partition_rows observed_outcome_days selected_distinct_receipt_ids receipt_ids_with_observed_outcomes "
        "receipt_ids_with_multiple_outcomes selected_outcome_observations observed_block_partition_rows observed_block_days "
        "classified_transaction_rows classified_distinct_transaction_hashes week_control_records population_records bucket_records scope coverage_basis".split()),
    "WEEK_CONTROL": set("week_start transactions distinct_transaction_hashes active_accounts observed_days observed_hours "
        "invalid_conversion_cost_rows matches_result56 recorded_conversion_spending_near".split()),
    "POPULATION": set("population cohort_week submission_week result56_controls_passed lookup_days_observed observed_accounts "
        "transactions distinct_transaction_hashes invalid_conversion_rows recorded_conversion_spending_near assessed_initial_receipts "
        "unassessed_initial_receipts accounts_with_assessed_initial_receipts accounts_with_successful_initial_receipts "
        "accounts_with_failed_initial_receipts minimum_assessed_execution_lag_microseconds maximum_assessed_execution_lag_microseconds "
        "valid_initial_cost_transactions invalid_assessed_cost_rows valid_assessed_initial_spending_subtotal_near "
        "complete_initial_receipt_spending_near record_execution_hash_disagreements record_execution_time_disagreements".split()),
    "ASSESSMENT_BUCKET": set("population submission_week assessment observed_initial_status cost_check execution_date execution_week "
        "transactions distinct_transaction_hashes matched_outcome_observations valid_initial_cost_transactions partial_tail_transactions "
        "valid_assessed_initial_spending_subtotal_near diagnostic_examples example_scope".split()),
}
EXAMPLE_SCHEMA = set("transaction_hash converted_into_receipt_id outcome_record_date outcome_record_hash outcome_record_time "
                     "executed_in_block_hash execution_time raw_status".split())


def money(value):
    result = b.number(value)
    b.require(result >= 0, "Negative monetary amount")
    return result


def sum_money(values):
    values = list(values)
    if not values:
        return None
    with localcontext() as ctx:
        ctx.prec = 80
        return str(sum((money(x) for x in values), Decimal(0)))


def compare_money(actual, expected, tolerance=Decimal(0)):
    with localcontext() as ctx:
        ctx.prec = 80
        b.require(abs(money(actual) - money(expected)) <= tolerance, "Monetary arithmetic discrepancy")


def nullable_money(actual, expected):
    b.require((actual is None) == (expected is None), "Missing-cost null safeguard broken")
    if expected is not None:
        compare_money(actual, expected)


def stamp(value):
    b.require(isinstance(value, str), "Missing timestamp")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    b.require(result.tzinfo is not None and result.utcoffset() == timedelta(0), "Timestamp must identify UTC")
    return result


def chain_id(value):
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    b.require(isinstance(value, str) and value and all(c in alphabet for c in value), "Invalid saved hash/receipt identity")
    integer = 0
    for char in value:
        integer = integer*58 + alphabet.index(char)
    size = (integer.bit_length()+7)//8 + len(value)-len(value.lstrip("1"))
    b.require(size == 32, "Saved hash/receipt identity is not 32 bytes")


def aggregate(buckets, key):
    groups = defaultdict(list)
    for row in buckets:
        groups[row[key]].append(row)
    output = []
    for value, rows in sorted(groups.items(), key=lambda item: str(item[0])):
        n = sum(b.count(r["transactions"]) for r in rows)
        valid = sum(b.count(r["valid_initial_cost_transactions"]) for r in rows)
        output.append({key: value, "transactions": n, "valid_cost_transactions": valid,
            "recorded_initial_receipt_spending_subtotal_near": sum_money(r["valid_assessed_initial_spending_subtotal_near"]
                for r in rows if r["valid_assessed_initial_spending_subtotal_near"] is not None),
            "complete_bucket_cost_coverage": valid == n})
    return output


def validate(raw):
    # Retain the prior scripts byte-for-byte: result 57 pins them and SQL 42.
    saved = b.decode(SAVED.read_bytes())
    regenerated = prior.report()
    exact_reproduction = b.json_bytes(regenerated) == SAVED.read_bytes()
    reproduction = {"byte_for_byte_with_current_files": exact_reproduction,
                    "all_recorded_inputs_and_metrics_reproduced": True}
    if not exact_reproduction:
        relative = "sql/42_persistent_activity_initial_receipt_pilot.sql"
        current = (ROOT / relative).read_bytes()
        expected = saved["source_hashes"][relative]
        b.require(current.endswith(b"\n\n") and len(current)-1 == expected["bytes"]
                  and hashlib.sha256(current[:-1]).hexdigest() == expected["sha256"],
                  "SQL 42 changed beyond the verified extra trailing newline")
        regenerated["source_hashes"][relative] = expected
        b.require(b.json_bytes(regenerated) == SAVED.read_bytes(), "Result 57 metrics or other recorded inputs changed")
        reproduction.update({"difference": "Current SQL 42 has exactly one extra trailing LF; removing it in memory recovers the recorded bytes/hash. No file was altered.",
            "recorded_sql42_identity": expected, "current_sql42_identity": prior.identity(ROOT / relative)})
    rows = b.decode(raw)
    b.require(isinstance(rows, list), "Expected JSON array")
    export_record_count = len(rows)
    grouped = defaultdict(list)
    for row in rows:
        b.require(isinstance(row, dict) and set(row) == {"row_kind", "record_json"}
                  and row["row_kind"] in SCHEMAS and isinstance(row["record_json"], str), "Unexpected outer schema")
        record = b.decode(row["record_json"])
        b.require(isinstance(record, dict) and set(record) == SCHEMAS[row["row_kind"]], "Unexpected nested schema")
        grouped[row["row_kind"]].append(record)
    b.require(len(grouped["SUMMARY"]) == 1, "Expected one summary")
    s = grouped["SUMMARY"][0]
    b.require(len(grouped["WEEK_CONTROL"]) == b.count(s["week_control_records"]) == 4
              and len(grouped["POPULATION"]) == b.count(s["population_records"]) == 2
              and len(grouped["ASSESSMENT_BUCKET"]) == b.count(s["bucket_records"])
              and len(rows) == 7+b.count(s["bucket_records"]), "Incomplete export/result-row count discrepancy")
    b.require((s["cohort_week"], s["submission_week"], s["submission_week_end"], s["lookup_end"])
              == ("2026-08-17", str(START), "2026-10-18", str(END)), "Wrong pilot dates")
    b.require(s["scope"] == "INITIAL_RECEIPTS_ONLY_OUTER_SIGNER_ASSOCIATION_NOT_COMPLETE_CHAIN_OR_REVENUE"
              and s["coverage_basis"] == "OWNERSHIP_COUNTS_BOUNDED_TO_FOUR_TX_WEEKS_OBSERVED_COVERAGE_ONLY", "Scope mismatch")
    for key, value in s.items():
        if key not in {"cohort_week", "submission_week", "submission_week_end", "lookup_end", "scope", "coverage_basis", "result56_controls_passed"}:
            b.count(value)
    b.require(s["result56_controls_passed"] is True and b.count(s["invalid_identity_or_timestamp_rows"]) == 0,
              "Invalid source controls")
    controls = b.keyed(grouped["WEEK_CONTROL"], "week_start")
    expected_weeks = {r["week_start"]: r for r in saved["weekly_controls"]}
    b.require(set(controls) == WEEKS, "Unexpected or missing transaction weeks")
    for week, row in controls.items():
        expected = expected_weeks[week]
        for field in ("transactions", "distinct_transaction_hashes", "active_accounts", "observed_days", "observed_hours", "invalid_conversion_cost_rows"):
            b.require(b.count(row[field]) == b.count(expected[field]), "Weekly result-56 count mismatch")
        b.require(row["matches_result56"] is True and row["invalid_conversion_cost_rows"] == 0, "Invalid weekly controls")
        compare_money(row["recorded_conversion_spending_near"], expected["recorded_conversion_spending_near"], b.ARITHMETIC_TOLERANCE)
    total = sum(b.count(r["transactions"]) for r in controls.values())
    b.require(b.count(s["transaction_rows"]) == b.count(s["distinct_transaction_hashes"]) == total
              and b.count(s["observed_days"]) == 28 and b.count(s["observed_hours"]) == 672
              and b.count(s["matching_week_controls"]) == 4, "Source totals/coverage disagree")
    baseline = saved["next_extraction"]
    for field, expected in (("cohort_accounts", baseline["expected_cohort_accounts"]),
                            ("exact_week_8_accounts", baseline["expected_exact_week_8_accounts"]),
                            ("repeated_checkpoint_accounts", baseline["expected_repeated_checkpoint_accounts"]),
                            ("selected_accounts", baseline["expected_exact_week_8_accounts"]),
                            ("selected_transactions", baseline["expected_exact_week_8_transactions"]),
                            ("classified_transaction_rows", baseline["expected_exact_week_8_transactions"]),
                            ("classified_distinct_transaction_hashes", baseline["expected_exact_week_8_transactions"])):
        b.require(b.count(s[field]) == b.count(expected), "Saved membership/transaction controls disagree")
    n = b.count(s["selected_transactions"])
    ids, matched, multi, observations = (b.count(s[k]) for k in ("selected_distinct_receipt_ids", "receipt_ids_with_observed_outcomes",
                                                               "receipt_ids_with_multiple_outcomes", "selected_outcome_observations"))
    b.require(multi <= matched <= ids <= n and observations >= matched+multi, "Receipt/outcome count diagnostics inconsistent")
    if multi == 0:
        b.require(observations == matched, "Unique outcome count discrepancy")
    b.require(0 <= b.count(s["observed_outcome_days"]) <= 13 and 0 <= b.count(s["observed_block_days"]) <= 13
              and b.count(s["observed_outcome_partition_rows"]) >= observations
              and b.count(s["observed_block_partition_rows"]) >= b.count(s["observed_block_days"]), "Invalid lookup coverage")
    lookup_complete = s["observed_outcome_days"] == s["observed_block_days"] == 13
    populations = b.keyed(grouped["POPULATION"], "population")
    b.require(set(populations) == set(POPS), "Missing/unexpected population")
    buckets, seen_keys, samples, receipts = defaultdict(list), set(), {}, {}
    seen_sample_keys = set()
    sample_occurrences, sample_hash_mismatch, sample_time_mismatch = Counter(), Counter(), Counter()
    for row in grouped["ASSESSMENT_BUCKET"]:
        pop = row["population"]
        b.require(pop in POPS and row["submission_week"] == str(START), "Wrong bucket population/submission week")
        key = (pop, row["assessment"], row["observed_initial_status"], row["cost_check"], row["execution_date"], row["execution_week"])
        b.require(key not in seen_keys, "Duplicate assessment bucket")
        seen_keys.add(key)
        b.require(row["assessment"] in ASSESSMENTS and row["observed_initial_status"] in STATUSES, "Unknown assessment/status")
        count = b.count(row["transactions"])
        b.require(count > 0 and b.count(row["distinct_transaction_hashes"]) == count, "Bucket duplicates or invalid count")
        assessed = row["assessment"] == "ASSESSED_INITIAL_RECEIPT"
        valid = assessed and row["cost_check"] == "VALID_COST"
        if assessed:
            execution = date.fromisoformat(row["execution_date"])
            b.require(START <= execution <= END and row["execution_week"] == str(execution-timedelta(days=execution.weekday()))
                      and row["observed_initial_status"] != "UNAVAILABLE_OR_OTHER"
                      and row["cost_check"] in BAD_COSTS | {"VALID_COST"}, "Invalid assessed date/status/cost category")
            b.require(b.count(row["matched_outcome_observations"]) == count, "Assessed receipt lacks unique outcome")
        else:
            b.require(row["execution_date"] is None and row["execution_week"] is None
                      and row["cost_check"] == "UNASSESSED_LINK_OR_EXECUTION", "Unassessed attribution was filled")
        b.require(b.count(row["valid_initial_cost_transactions"]) == (count if valid else 0), "Valid-cost coverage discrepancy")
        if valid:
            money(row["valid_assessed_initial_spending_subtotal_near"])
        else:
            b.require(row["valid_assessed_initial_spending_subtotal_near"] is None, "Missing-cost null safeguard broken")
        b.require(b.count(row["partial_tail_transactions"]) == (count if assessed and execution >= date(2026, 10, 19) else 0), "Tail count discrepancy")
        examples = row["diagnostic_examples"]
        b.require(isinstance(examples, list) and len(examples) == min(3, count)
                  and row["example_scope"] == "UP_TO_THREE_EXAMPLES_NOT_CANONICAL_MATCH_SELECTION", "Truncated/mislabelled diagnostic examples")
        b.require([e["transaction_hash"] for e in examples] == sorted(e["transaction_hash"] for e in examples), "Diagnostic example order mismatch")
        for e in examples:
            b.require(set(e) == EXAMPLE_SCHEMA, "Unexpected diagnostic-example schema")
            chain_id(e["transaction_hash"])
            if assessed:
                chain_id(e["converted_into_receipt_id"])
            pair = (pop, e["transaction_hash"])
            b.require(pair not in seen_sample_keys, "Duplicate sample transaction within population")
            seen_sample_keys.add(pair)
            other = samples.get(e["transaction_hash"])
            b.require(other is None or other == e, "Cross-population sample identity disagreement")
            samples[e["transaction_hash"]] = e
            rid = e["converted_into_receipt_id"]
            if assessed:
                b.require(rid not in receipts or receipts[rid] == e["transaction_hash"], "Shared initial receipt among examples")
                receipts[rid] = e["transaction_hash"]
            if assessed:
                chain_id(e["outcome_record_hash"])
                chain_id(e["executed_in_block_hash"])
                actual = stamp(e["execution_time"])
                record = stamp(e["outcome_record_time"])
                b.require(actual.date() == execution and str(record.date()) == e["outcome_record_date"]
                          and START <= record.date() <= END and e["raw_status"] == row["observed_initial_status"], "Example date/status mismatch")
                sample_hash_mismatch[pop] += e["outcome_record_hash"] != e["executed_in_block_hash"]
                sample_time_mismatch[pop] += actual != record
            sample_occurrences[pop] += 1
        buckets[pop].append(row)

    reports = []
    for pop in POPS:
        p, rows = populations[pop], buckets[pop]
        b.require(p["cohort_week"] == "2026-08-17" and p["submission_week"] == str(START)
                  and p["result56_controls_passed"] is True and p["lookup_days_observed"] is lookup_complete, "Population identity/coverage mismatch")
        expected_accounts = baseline["expected_exact_week_8_accounts"] if pop == POPS[0] else baseline["expected_repeated_checkpoint_accounts"]
        tx, accounts = b.count(p["transactions"]), b.count(p["observed_accounts"])
        b.require(accounts == expected_accounts and accounts <= tx and b.count(p["distinct_transaction_hashes"]) == tx
                  == sum(b.count(r["transactions"]) for r in rows), "Population membership/transaction mismatch")
        assessed = [r for r in rows if r["assessment"] == "ASSESSED_INITIAL_RECEIPT"]
        assessed_count = sum(b.count(r["transactions"]) for r in assessed)
        valid_count = sum(b.count(r["valid_initial_cost_transactions"]) for r in rows)
        invalid_count = sum(b.count(r["transactions"]) for r in assessed if r["cost_check"] != "VALID_COST")
        b.require(b.count(p["assessed_initial_receipts"]) == assessed_count
                  and b.count(p["unassessed_initial_receipts"]) == tx-assessed_count
                  and b.count(p["valid_initial_cost_transactions"]) == valid_count
                  and b.count(p["invalid_assessed_cost_rows"]) == invalid_count, "Population bucket-coverage discrepancy")
        subtotal = sum_money(r["valid_assessed_initial_spending_subtotal_near"] for r in rows
                             if r["valid_assessed_initial_spending_subtotal_near"] is not None)
        nullable_money(p["valid_assessed_initial_spending_subtotal_near"], subtotal)
        nullable_money(p["complete_initial_receipt_spending_near"], subtotal if valid_count == tx and tx > 0 and lookup_complete else None)
        invalid_conversion = b.count(p["invalid_conversion_rows"])
        b.require(invalid_conversion <= tx and (p["recorded_conversion_spending_near"] is None) == (invalid_conversion > 0), "Conversion null safeguard broken")
        if p["recorded_conversion_spending_near"] is not None:
            money(p["recorded_conversion_spending_near"])
        if pop == POPS[0]:
            b.require(tx == n and invalid_conversion == 0, "Exact returner denominator/conversion mismatch")
            compare_money(p["recorded_conversion_spending_near"], baseline["expected_exact_week_8_conversion_spending_near"], b.ARITHMETIC_TOLERANCE)
            if ids == n:
                b.require(sum(b.count(r["matched_outcome_observations"]) for r in rows) == observations, "Source/bucket outcome observations disagree")
        success_tx = sum(b.count(r["transactions"]) for r in assessed if r["observed_initial_status"] in SUCCESS)
        failure_tx = sum(b.count(r["transactions"]) for r in assessed if r["observed_initial_status"] == "FAILURE")
        a, sa, fa = (b.count(p[k]) for k in ("accounts_with_assessed_initial_receipts", "accounts_with_successful_initial_receipts", "accounts_with_failed_initial_receipts"))
        b.require(a <= min(accounts, assessed_count) and sa <= min(a, success_tx) and fa <= min(a, failure_tx)
                  and a <= sa+fa <= 2*a and (assessed_count != tx or a == accounts), "Assessed/success/failure account counts disagree")
        lo, hi = p["minimum_assessed_execution_lag_microseconds"], p["maximum_assessed_execution_lag_microseconds"]
        b.require((lo is None) == (hi is None) == (assessed_count == 0), "Lag-null safeguard broken")
        if assessed_count:
            b.require(b.count(lo) <= b.count(hi) <= 13*86400*1000000, "Invalid execution-lag bounds")
        b.require(sample_hash_mismatch[pop] <= b.count(p["record_execution_hash_disagreements"])
                  and sample_time_mismatch[pop] <= b.count(p["record_execution_time_disagreements"]), "Sample/summary hash-time disagreement")
        reports.append({"population": pop, "observed": p, "successful_initial_receipts": success_tx, "failed_initial_receipts": failure_tx,
            "successful_initial_receipt_share_pct": b.ratio(success_tx, tx, 100),
            "failed_initial_receipt_share_pct": b.ratio(failure_tx, tx, 100),
            "assessed_initial_receipt_coverage_pct": b.ratio(assessed_count, tx, 100),
            "accounts_with_both_success_and_failure": sa+fa-a,
            "assessed_accounts_with_failure_only": a-sa,
            "exclusion_counts": {reason: sum(b.count(r["transactions"]) for r in rows if r["assessment"] == reason)
                                 for reason in sorted(ASSESSMENTS - {"ASSESSED_INITIAL_RECEIPT"})},
            "by_status": aggregate(assessed, "observed_initial_status"), "by_execution_date": aggregate(rows, "execution_date"),
            "by_assessment": aggregate(rows, "assessment"), "by_cost_check": aggregate(rows, "cost_check"),
            "tail_transactions": sum(b.count(r["partial_tail_transactions"]) for r in rows),
            "tail_spending_subtotal_near": sum_money(r["valid_assessed_initial_spending_subtotal_near"] for r in rows
                if r["partial_tail_transactions"] and r["valid_assessed_initial_spending_subtotal_near"] is not None),
            "diagnostic_example_occurrences_checked": sample_occurrences[pop]})
    exact, repeated = populations[POPS[0]], populations[POPS[1]]
    for field in ("transactions", "observed_accounts", "assessed_initial_receipts", "unassessed_initial_receipts",
                  "valid_initial_cost_transactions", "invalid_assessed_cost_rows", "invalid_conversion_rows",
                  "accounts_with_assessed_initial_receipts", "accounts_with_successful_initial_receipts", "accounts_with_failed_initial_receipts"):
        b.require(b.count(repeated[field]) <= b.count(exact[field]), "Repeated population exceeds enclosing group")
    for field in ("recorded_conversion_spending_near", "valid_assessed_initial_spending_subtotal_near"):
        if exact[field] is not None and repeated[field] is not None:
            b.require(money(repeated[field]) <= money(exact[field]), "Repeated monetary subtotal exceeds enclosing group")
    exact_buckets = {tuple(r[k] for k in ("assessment", "observed_initial_status", "cost_check", "execution_date")): r for r in buckets[POPS[0]]}
    for row in buckets[POPS[1]]:
        other = exact_buckets.get(tuple(row[k] for k in ("assessment", "observed_initial_status", "cost_check", "execution_date")))
        b.require(other is not None and b.count(row["transactions"]) <= b.count(other["transactions"]), "Repeated bucket exceeds enclosing group")
        if row["valid_assessed_initial_spending_subtotal_near"] is not None:
            b.require(money(row["valid_assessed_initial_spending_subtotal_near"]) <= money(other["valid_assessed_initial_spending_subtotal_near"]), "Repeated bucket spending exceeds enclosing group")
    no_exclusions = all(p["unassessed_initial_receipts"] == p["invalid_assessed_cost_rows"] == 0 for p in populations.values())
    remaining = [{"cohort_week": p["cohort_week"], "week_offset": p["week_offset"],
        "followup_week": p["followup_week"], "followup_week_end": p["followup_week_end"],
        "returning_accounts": p["returning_accounts"], "returning_transactions": p["returning_transactions"],
        "recorded_conversion_spending_near": p["recorded_conversion_spending_near"],
        "within_agreed_initial_receipt_window": p["followup_week"] >= "2026-08-24",
        "initial_receipt_spending_near": None}
        for p in saved["checkpoint_metrics"] if p["measurement_available"]
        and (p["cohort_week"], p["week_offset"]) != ("2026-08-17", 8)]
    with localcontext() as ctx:
        ctx.prec = 80
        conversion_delta = str(money(exact["recorded_conversion_spending_near"])
                               - money(baseline["expected_exact_week_8_conversion_spending_near"]))
    return {"validation": "STRUCTURAL_ARITHMETIC_AND_SAVED_CONTROL_CHECKS_PASSED", "export_rows": export_record_count,
        "row_kinds": {k: len(v) for k, v in sorted(grouped.items())}, "result57_reproduction": reproduction,
        "unique_diagnostic_sample_transactions_checked": len(samples),
        "source_summary": s, "weekly_controls": [controls[k] for k in sorted(controls)], "populations": reports,
        "repeated_subset_transaction_share_pct": b.ratio(b.count(repeated["transactions"]), b.count(exact["transactions"]), 100),
        "exact_returner_conversion_difference_from_result56_near": conversion_delta,
        "population_relationship": "Repeated means starting-cohort accounts active at all exact +1/+4/+8 checkpoints, not continuous weekly activity. Its +8 transactions are a subset of the exact +8 group; never add the two groups.",
        "source_export_sha256": hashlib.sha256(raw).hexdigest(), "source_export_bytes": len(raw),
        "unmeasured": {"descendant_receipt_spending_near": None, "complete_chain_successful_transactions": None,
                       "revenue": None, "fresh_token_purchases": None, "holder_value": None},
        "limitations": ["Aggregate checks and up-to-three examples per bucket cannot independently reconstruct all account memberships or all receipt/block links. Full source records are not exported.",
            "Receipt-owner uniqueness is checked only within four selected transaction weeks. Observed day/hour counts do not independently prove ingestion completeness or historical coverage elsewhere.",
            "Examples do not include submission timestamps, executor account IDs or block heights. Lag bounds and executor/height checks can be inspected in SQL and reconciled as aggregate diagnostics, not independently recomputed for every transaction offline.",
            "The 19–24 October execution tail is six days of a UTC week, not a complete week. The fixed cutoff gives unequal elapsed follow-up by submission date; zero unmatched initial receipts does not establish descendant coverage.",
            "Monetary strings retain FLOAT-derived source precision limitations. Decimal preserves saved arithmetic; the 0.00001 NEAR baseline screen is not a source-accuracy or economic-reconciliation tolerance.",
            "Only initial-receipt outcomes and spending associated with outer signers are measured. Initial success is not complete-chain success. Recorded spending is not revenue, fresh token purchases, permanent burn or holder value."],
        "extension_assessment": {"coverage_supports_bounded_replication": lookup_complete and no_exclusions,
            "other_transaction_complete_checkpoints": len(remaining),
            "other_checkpoints_within_agreed_initial_receipt_window": sum(p["within_agreed_initial_receipt_window"] for p in remaining),
            "remaining_complete_points": remaining,
            "remaining_unavailable_checkpoints": 3,
            "excluded_early_point": "10 August +1: 17–23 August lies outside the agreed initial-receipt pilot window.",
            "reason": "Complete observed matching and valid-cost coverage supports testing the method on other dates, not assuming their coverage. Use the shared 5–11 October week for 10 August +8 and 28 September +1, with the 10 August repeated-checkpoint subset.",
            "sql": str(EXTENSION.relative_to(ROOT)), "intended_result": "results/60_persistent_activity_shared_week_initial_receipts.json",
            "submission_week": "2026-10-05", "lookup_end": "2026-10-17",
            "transaction_weeks": ["2026-08-10", "2026-08-17", "2026-09-07", "2026-09-28", "2026-10-05"]}}


def report(source=SOURCE):
    result = validate(source.read_bytes())
    paths = {ROOT / p for p in b.decode(SAVED.read_bytes())["source_hashes"]}
    paths.update({source, SAVED, Path(__file__), EXTENSION})
    result["source_hashes"] = {str(p.relative_to(ROOT)): prior.identity(p) for p in sorted(paths)}
    result["derivation"] = "python3 -B analysis/21_validate_initial_receipt_pilot.py; offline only; reuse unchanged analysis/19–20 to reproduce result 57 and validate result 56. Strict duplicate-key JSON parsing, integer counts, Decimal monetary sums/comparisons at 80 digits and ratios at 60 digits; check examples without any chain requests."
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
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
