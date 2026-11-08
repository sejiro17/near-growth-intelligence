"""Offline sharp bounds on initial success outside each population's top ten.

Reviewed query definitions and saved controls establish population alignment;
aggregate exports cannot independently reconstruct full membership/receipt sets.
Missing or ambiguous coverage suppresses every bound. No source requests.
"""

import argparse
import hashlib
import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("shared_validation", ROOT/"analysis/22_validate_shared_week_receipts.py")
validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validation)
b = validation.b
OUTPUT = ROOT/"results/105_returner_initial_success_outside_top10_bounds.json"
SQL_PINS = {
    "sql/41_persistent_activity_transaction_pilot.sql": "c0f42f4f0e4e99ab216db83a783378cd1a6e3f7655a862943356846996f18060",
    "sql/42_persistent_activity_initial_receipt_pilot.sql": "7abac312aab63d910d92b9ade5ef9c41002fceaed9f65a5a178b8e981d2a9dea",
    "sql/43_persistent_activity_shared_week_initial_receipts.sql": "1b6add55a7a34c75d55d7da331a5e13a939cd7b8abab1f0df485b66fdc20dc98",
}
EXCLUSIONS = set("EXECUTION_AFTER_LOOKUP_CUTOFF EXECUTION_BLOCK_UNAVAILABLE_OR_BOUNDARY EXECUTOR_MISMATCH_OR_UNAVAILABLE INVALID_EXECUTION_BLOCK INVALID_INITIAL_RECEIPT_ID INVALID_OUTCOME_RECORD_TIME MISSING_EXECUTION_HASH MISSING_INITIAL_RECEIPT_ID MULTIPLE_EXECUTION_BLOCK_OBSERVATIONS MULTIPLE_OUTCOME_OBSERVATIONS NEGATIVE_EXECUTION_LAG NO_OUTCOME_IN_LOOKUP_WINDOW SHARED_INITIAL_RECEIPT_ID STATUS_UNAVAILABLE_OR_UNRECOGNIZED".split())
CASES = [("2026-08-10", "AUG10_EXACT_WEEK8", 61), ("2026-08-17", "EXACT_WEEK_8_RETURNERS", 59)]


def path(number):
    found, = (ROOT/"results").glob(f"{number}_*.json")
    return found


def count(value):
    b.require(type(value) is int and value >= 0, "Missing/invalid integer count")
    return value


def display_pct(numerator, denominator, *, upper=False):
    """Outward rounding by integer arithmetic; never overstate a lower bound."""
    if denominator == 0:
        return None
    scaled, remainder = divmod(count(numerator)*10000, count(denominator))
    scaled += bool(upper and remainder)
    return f"{scaled//100}.{scaled%100:02d}"


def bounds(total, top, success):
    total, top, success = (count(x) for x in (total, top, success))
    b.require(top <= total and success <= total, "Counts exceed transaction population")
    outside = total-top
    lower, upper = max(0, success-top), min(success, outside)
    return {"outside_top10_transactions": outside,
            "successful_initial_receipts_outside_top10_lower": lower,
            "successful_initial_receipts_outside_top10_upper": upper,
            "outside_success_fraction_lower": {"numerator": lower, "denominator": outside},
            "outside_success_fraction_upper": {"numerator": upper, "denominator": outside},
            "outside_initial_success_pct_lower_display": display_pct(lower, outside),
            "outside_initial_success_pct_upper_display": display_pct(upper, outside, upper=True)}


def compare(checkpoint, population, summary, *, definitions_verified, expected_population):
    checkpoint = checkpoint if isinstance(checkpoint, dict) else {}
    population = population if isinstance(population, dict) else {}
    summary = summary if isinstance(summary, dict) else {}
    result = {"cohort_week": checkpoint.get("cohort_week"), "submission_week": checkpoint.get("followup_week"),
              "population": population.get("population"), "status": "UNAVAILABLE", "bounds": None,
              "unit": "one assessed initial receipt per submitted transaction", "suppression_reason": None}
    try:
        b.require(definitions_verified is True, "Query definitions/transaction units not verified")
        c, p, s = checkpoint, population["observed"], summary
        b.require(c["followup_complete"] is True and c["measurement_available"] is True
                  and c["source_controls_passed"] is True and p["result56_controls_passed"] is True
                  and s["result56_controls_passed"] is True, "Incomplete follow-up or failed source controls")
        b.require(population["population"] == p["population"] == expected_population, "Wrong population or repeated subset")
        b.require(p["cohort_week"] == c["cohort_week"] and p["submission_week"] == c["followup_week"]
                  and s["submission_week"] == c["followup_week"] and count(c["week_offset"]) == 8
                  and date.fromisoformat(c["cohort_week"])+timedelta(weeks=8) == date.fromisoformat(c["followup_week"]), "Cohort/submission week mismatch")
        b.require(c["followup_week_end"] == s["submission_week_end"]
                  == str(date.fromisoformat(c["followup_week"])+timedelta(days=6)), "Submission week-end mismatch")
        if expected_population == "AUG10_EXACT_WEEK8":
            b.require(p["return_definition"] == "EXACT_WEEK_RETURNERS" and p["week_offset"] == 8
                      and p["group_matches_result56"] is True
                      and count(p["expected_cohort_accounts"]) == count(c["cohort_accounts"])
                      and count(p["expected_accounts"]) == count(c["returning_accounts"])
                      and count(p["expected_transactions"]) == count(c["returning_transactions"]), "Membership definition/group controls mismatch")
        elif expected_population == "EXACT_WEEK_8_RETURNERS":
            b.require(s["cohort_week"] == c["cohort_week"]
                      and count(s["cohort_accounts"]) == count(c["cohort_accounts"])
                      and count(s["exact_week_8_accounts"]) == count(c["returning_accounts"]), "Starting-week/exact-week membership mismatch")
        else:
            raise ValueError("Unreviewed population definition")
        n = count(p["transactions"])
        accounts = count(c["returning_accounts"])
        b.require(count(p["observed_accounts"]) == accounts <= n
                  and n == count(c["returning_transactions"]) == count(p["distinct_transaction_hashes"]), "Population denominator/transaction uniqueness mismatch")
        b.require(count(s["transaction_rows"]) == count(s["distinct_transaction_hashes"])
                  and count(s["selected_transactions"]) == count(s["classified_transaction_rows"])
                  == count(s["classified_distinct_transaction_hashes"]) == count(s["selected_distinct_receipt_ids"])
                  == count(s["receipt_ids_with_observed_outcomes"]) == count(s["selected_outcome_observations"])
                  and count(s["receipt_ids_with_multiple_outcomes"]) == 0, "Missing/ambiguous transaction/initial-receipt/outcome mapping")
        b.require(count(p["assessed_initial_receipts"]) == n and count(p["unassessed_initial_receipts"]) == 0
                  and p["lookup_days_observed"] is True, "Incomplete assessed initial-receipt coverage")
        exclusions = population["exclusion_counts"]
        b.require(set(exclusions) == EXCLUSIONS and all(count(x) == 0 for x in exclusions.values()), "Missing or nonzero exclusion diagnostics")
        status = {}
        for row in population["by_status"]:
            key = row["observed_initial_status"]
            b.require(key in {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID", "FAILURE"} and key not in status, "Unknown/duplicate initial status bucket")
            status[key] = count(row["transactions"])
        success = count(population["successful_initial_receipts"])
        failure = count(population["failed_initial_receipts"])
        b.require(success == status.get("SUCCESS_VALUE", 0)+status.get("SUCCESS_RECEIPT_ID", 0)
                  and failure == status.get("FAILURE", 0) and success+failure == n, "Initial status totals disagree")
        top = count(c["top_10_transactions"])
        b.require(top <= n and (accounts > 10 or top == n), "Invalid own-top-ten count")
        result.update(status="AVAILABLE_OBSERVED_INITIAL_RECEIPT_BOUNDS", bounds=bounds(n, top, success),
                      total_transactions=n, returning_accounts=accounts, own_top10_transactions=top,
                      total_successful_initial_receipts=success, total_failed_initial_receipts=failure,
                      one_assessed_initial_receipt_per_transaction=True,
                      membership_verification="Reviewed SQL definitions plus matching exported cohort/group controls; complete membership lists are not exported")
    except (KeyError, TypeError, ValueError) as exc:
        result["suppression_reason"] = str(exc)
    return result


def report():
    for name, sha in SQL_PINS.items():
        b.require(hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha, "Unreviewed query definition: "+name)
    b.require(b.json_bytes(validation.report()) == path(61).read_bytes(), "Saved cohort/outcome validation does not reproduce")
    concentration = b.decode(path(57).read_bytes())
    rows = []
    for cohort, population_id, number in CASES:
        checkpoints = [p for p in concentration["checkpoint_metrics"] if p["cohort_week"] == cohort and p["week_offset"] == 8]
        outcomes = b.decode(path(number).read_bytes())
        populations = [p for p in outcomes["populations"] if p["population"] == population_id]
        b.require(len(checkpoints) == len(populations) == 1, "Missing/duplicate selected population")
        rows.append(compare(checkpoints[0], populations[0], outcomes["source_summary"],
                            definitions_verified=True, expected_population=population_id))
    sources = [path(n) for n in (56, 57, 58, 59, 60, 61)] + [ROOT/p for p in SQL_PINS]
    sources += [Path(__file__), Path(validation.__file__), Path(validation.p.__file__), Path(b.__file__)]
    return {"schema_version": 1, "classification": "TRANSACTION_LEVEL_INITIAL_SUCCESS_BOUNDS_NOT_ACCOUNT_RATES",
            "populations": rows, "formula": {"N": "population transactions", "T": "transactions from this population's own ten leading returners", "S": "successful assessed initial receipts", "B": "N-T", "lower": "max(0,S-T)", "upper": "min(S,B)"},
            "display_rounding": "Lower percentages rounded down and upper percentages up to two decimals using integer division. Exact counts and rational numerators/denominators are authoritative. Zero outside denominator has no percentage.",
            "membership_and_unit_review": {"SQL41": "Starting-week signer membership intersected with exact follow-up-week activity; own ranking by transactions DESC, signer ID; top-ten transactions summed once per account.",
                "SQL42": "17 August members active in 12–18 October; all selected submission-week transactions; EXACT_WEEK_8_RETURNERS excludes no account for missing +1/+4 activity.",
                "SQL43": "10 August members active in 5–11 October; AUG10_EXACT_WEEK8 distinct from repeated-checkpoint subset. Counts and frozen expected membership controls match SQL41.",
                "unit": "Submitted transactions, each with one assessed initial receipt; actions and descendant receipts are not denominators."},
            "limitations": ["Proves minimum successful initial receipts beyond each population's own ten leading signers within observed coverage, not measured account-level success rates, independent humans, revenue or complete-chain settlement.",
                "Cohorts overlap and use different submission weeks; never sum their bounds or interpret differences causally.",
                "Complete membership and receipt lists are not exported. Alignment uses reviewed, hashed SQL definitions and validated aggregate controls; no independent row-level set-equality or ingestion-completeness proof is available.",
                "Six-day initial-execution tails and observed receipt-owner uniqueness windows remain unchanged. Spending is not allocated outside the top ten by these counts."],
            "source_requests": 0, "sources": {str(p.relative_to(ROOT)): validation.p.prior.identity(p) for p in sources}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    def deny(event, _):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen", "os.system"}:
            raise RuntimeError("Offline bounds analysis cannot access sources")
    sys.addaudithook(deny)
    raw = b.json_bytes(report())
    if args.output is None:
        sys.stdout.write(raw.decode())
    elif args.check:
        b.require(args.output.read_bytes() == raw, "Bounds artifact does not reproduce")
        print("Bounds reproduced offline; source requests: 0")
    else:
        with args.output.open("xb") as handle:
            handle.write(raw)


if __name__ == "__main__":
    main()
