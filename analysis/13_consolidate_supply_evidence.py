"""Reproduce saved supply comparisons and one account witness entirely offline.

Commands: comparison, witness, supply (JSON), table (rounded Markdown), check.
Default output is stdout. --output creates a new file exclusively; no overwrite.
No collection functions are invoked. Monetary arithmetic never passes through float.
"""

import argparse
import importlib.util
import json
import sys
from bisect import bisect_right
from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


witness = module("saved_witness", "12_collect_bitwise_parent_witness.py")
checker = module("saved_supply", "10_supply_comparison_check.py")
capture = witness.capture
WITNESS_RUN = ROOT / "results/canonical_rpc_2026-09-23/bitwise_parent_witness/20261106T141203Z_c466a88d812f"
WITNESS_SUMMARY = ROOT / "results/45_bitwise_validator_update_witness_2026-09-23.json"
SUPPLY_SUMMARY = ROOT / "results/46_observational_supply_comparison_2026-08-24_to_2026-10-18.json"


def fingerprints(paths):
    return {str(path.relative_to(ROOT)): {"sha256": capture.sha256(path.read_bytes()),
                                         "bytes": path.stat().st_size}
            for path in sorted(set(paths))}


def verify_inputs(inputs):
    for relative, expected in inputs.items():
        path = ROOT / relative
        capture.require(path.resolve().is_relative_to(ROOT), "Input path outside repository")
        raw = path.read_bytes()
        capture.require(capture.sha256(raw) == expected["sha256"]
                        and len(raw) == expected["bytes"], f"Input hash/length mismatch: {relative}")


def result42(raw):
    """Reconstruct independent arrays, never zip flattened child arrays together."""
    parents, audits, reasons, current = {}, {}, {}, None
    for row in capture.decode(raw):
        if "row_kind" in row:
            current = row.get("block_hash")
            parents[current], audits[current], reasons[current] = row, [], []
        for prefix, field, output in (
            ("validator_account_audit.", "affected_account_id", audits),
            ("changes_by_chunk_and_reason.", "update_reason", reasons),
        ):
            if row.get(prefix + field):
                output[current].append({key.removeprefix(prefix): value
                                        for key, value in row.items() if key.startswith(prefix)})
    return parents, audits, reasons


def power2(exponent):
    return Fraction(2**exponent) if exponent >= 0 else Fraction(1, 2**-exponent)


def binary64(value):
    """Nearest finite nonnegative binary64 value and spacing, using integers only."""
    number = Decimal(value)
    capture.require(number.is_finite() and number >= 0, "Invalid monetary source number")
    x = Fraction(number)
    if not x:
        return x, power2(-1074)
    exponent = x.numerator.bit_length() - x.denominator.bit_length()
    if x < power2(exponent):
        exponent -= 1
    capture.require(exponent <= 1023, "Value exceeds finite binary64 range")
    unit = power2(max(exponent, -1022) - 52)
    scaled = x / unit
    quotient, remainder = divmod(scaled.numerator, scaled.denominator)
    if 2 * remainder > scaled.denominator or (2 * remainder == scaled.denominator and quotient % 2):
        quotient += 1
    return quotient * unit, unit


def decimal(fraction):
    return Decimal(fraction.numerator) / Decimal(fraction.denominator)


def comparison_report():
    provenance = capture.decode(witness.PROVENANCE.read_bytes())
    verify_inputs(provenance["inputs"])
    manifests = [ROOT / path for path in provenance["inputs"]
                 if path.endswith("/run.json")]
    capture.require(len(manifests) == 1, "Ambiguous recorded canonical run")
    run = manifests[0].parent
    capture.validate_stage2(run)
    raw = (run / "diagnostic_input.json").read_bytes()
    capture.require(raw == capture.DIAGNOSTIC.read_bytes(), "Result 42 snapshot differs")
    parents, audits, reasons = result42(raw)
    # Preserve the original location from a recorded input, even in another checkout.
    recorded_root = Path(capture.decode(manifests[0].read_bytes())["diagnostic_source"]).parents[1]
    report = {
        "scope": "Offline comparison of saved validator_accounts_update records; no new network requests.",
        "run_directory": str(recorded_root / run.relative_to(ROOT)),
        "result42_sha256": capture.sha256(raw),
        "numeric_method": "Decimal/Fraction only; exact binary64 reconstruction from saved shortest decimal strings; two-ULP screen is a conservative comparison screen, not a demonstrated ingestion error bound.",
        "coverage_limitation": capture.LIMITATION, "blocks": {},
    }
    with localcontext() as context:
        context.prec = 110
        unions, _, _ = capture.validate_stage1(run)
        for label, target in capture.TARGETS.items():
            block = capture.recorded(run / "stage1", capture.request(label, "block"))
            protocol = capture.recorded(run / "stage1", capture.request(label, "protocol"))
            rpc = capture.recorded(run / "stage2", capture.request(label, "changes", unions[label]))
            changes = rpc["changes"]
            q = {x["affected_account_id"]: x for x in audits[target["hash"]]}
            capture.require(len(q) == len(audits[target["hash"]]), "Duplicate BigQuery account")
            by = defaultdict(list)
            for index, change in enumerate(changes):
                by[change["change"]["account_id"]].append((index, change))
            validators = {x["change"]["account_id"]: (i, x) for i, x in enumerate(changes)
                          if x["cause"]["type"] == "validator_accounts_update"}
            common = sorted(validators.keys() & q.keys())
            only = sorted(validators.keys() - q.keys())
            bqonly = sorted(q.keys() - validators.keys())
            layout = protocol["shard_layout"]["V3"]
            boundaries, shard_ids = layout["boundary_accounts"], layout["shard_ids"]
            capture.require(boundaries == sorted(boundaries)
                            and len(shard_ids) == len(boundaries) + 1, "Invalid saved V3 layout")

            def shard(account):
                return shard_ids[bisect_right(boundaries, account)]

            chunks = {x["shard_id"]: x for x in block["chunks"]}
            missing = {s for s, chunk in chunks.items() if chunk["height_included"] < target["height"]}
            grouped = defaultdict(list)
            for account in validators:
                grouped[shard(account)].append(account)
            rank = {account: i for ids in grouped.values() for i, account in enumerate(sorted(ids))}
            field_checks, combined, blank = [], [], []
            nearest_bad, maximum = Counter(), {}
            for account in common:
                saved, value = q[account], validators[account][1]["change"]
                fields = []
                for field, source in (("amount", "source_nonstaked_yocto_float"),
                                      ("locked", "source_staked_yocto_float")):
                    exact = Fraction(Decimal(value[field]))
                    stored, unit = binary64(saved[source])
                    rounded, _ = binary64(value[field])
                    difference, ratio = exact - stored, abs(exact - stored) / unit
                    capture.require(ratio <= 2, "Outside conservative two-ULP comparison screen")
                    nearest_bad[field] += stored != rounded
                    check = {"account_id": account, "field": field,
                             "rpc_exact_yocto": value[field],
                             "bigquery_float_decimal_text": saved[source],
                             "bigquery_binary64_exact_yocto": str(decimal(stored)),
                             "rpc_minus_bigquery_near": str(decimal(difference) / 10**24),
                             "absolute_error_ULPs": str(decimal(ratio)),
                             "same_nearest_binary64": stored == rounded}
                    field_checks.append(check)
                    fields.append(stored)
                    if field not in maximum or abs(difference) > maximum[field][0]:
                        maximum[field] = abs(difference), check
                recovered = sum((decimal(x) for x in fields)) / 10**24
                capture.require(recovered == Decimal(saved["converted_balance_near"]),
                                "Saved balance conversion differs")
                difference = (Decimal(value["amount"]) + Decimal(value["locked"])) / 10**24 - recovered
                combined.append({"account_id": account,
                                 "rpc_minus_bigquery_combined_near": str(difference)})
                if not saved["chunk_hash"]:
                    blank.append(account)
                    capture.require(int(saved["index_in_block"]) == rank[account],
                                    "Inferred shard rank does not match saved blank-chunk index")
                else:
                    capture.require(saved["chunk_hash"] == chunks[shard(account)]["chunk_hash"]
                                    and int(saved["observed_shard_id"]) == shard(account),
                                    "Saved nonblank chunk mapping differs")
            indices = {int(q[a]["index_in_block"]) for a in blank}
            counts = Counter(i for s, ids in grouped.items() if s in missing
                             for i, account in enumerate(sorted(ids)))
            capture.require(len(indices) == len(blank) and set(counts) == indices
                            and sum(counts.values()) - len(counts) == len(only)
                            and all(shard(a) in missing for a in blank + only),
                            "Candidate collision pattern differs")
            causes = Counter(x["cause"]["type"] for x in changes)
            bq_causes = Counter()
            for value in reasons[target["hash"]]:
                bq_causes[value["update_reason"]] += int(value["update_records"])
            capture.require(sum(bq_causes.values()) == int(parents[target["hash"]]["account_change_rows"]),
                            "BigQuery reason counts disagree")
            capture.require({k: v for k, v in causes.items() if k != "validator_accounts_update"}
                            == {k: v for k, v in bq_causes.items() if k != "validator_accounts_update"},
                            "Non-validator record counts differ")
            capture.require(all(len(records) == 1 for a, records in by.items() if a in validators)
                            and all(x["type"] == "account_update" for x in changes),
                            "Unreviewed account update ordering")
            for records in by.values():
                capture.require([i for i, _ in records] == list(range(records[0][0], records[-1][0] + 1)),
                                "Noncontiguous within-account records")
            blank_ranges = {}
            for s in sorted(missing):
                accounts = [a for a in blank if shard(a) == s]
                if accounts:
                    blank_ranges[str(s)] = {"count": len(accounts),
                                            "min_index": min(int(q[a]["index_in_block"]) for a in accounts),
                                            "max_index": max(int(q[a]["index_in_block"]) for a in accounts)}
            report["blocks"][label] = {
                "height": target["height"], "hash": target["hash"], "parent_hash": target["parent"],
                "counts": {"rpc_all_accounts": len(by), "rpc_all_update_records": len(changes),
                           "rpc_validator_accounts": len(validators),
                           "rpc_validator_update_records": causes["validator_accounts_update"],
                           "bq_all_update_records": int(parents[target["hash"]]["account_change_rows"]),
                           "bq_all_distinct_accounts": None, "bq_validator_accounts": len(q),
                           "bq_validator_update_records": int(parents[target["hash"]]["observed_validator_update_records"]),
                           "both_validator_accounts": len(common), "rpc_only_validator_accounts": len(only),
                           "bq_only_validator_accounts": len(bqonly), "bq_blank_chunk_validator_records": len(blank)},
                "membership": {"both_validator_accounts": common, "rpc_only_validator_accounts": only,
                               "bq_only_validator_accounts": bqonly},
                "records_by_cause": dict(causes), "bigquery_records_by_cause": dict(bq_causes),
                "rpc_only_accounts_by_calculated_shard": {
                    str(s): sorted(a for a in only if shard(a) == s) for s in sorted(missing)},
                "no_new_chunk_shards": sorted(missing),
                "rpc_validator_counts_by_calculated_shard": dict(Counter(str(shard(a)) for a in validators)),
                "blank_chunk_saved_index_ranges_by_calculated_shard": blank_ranges,
                "collision_candidate": {
                    "rpc_records_in_no_new_chunk_shards": sum(counts.values()),
                    "unique_candidate_indices": len(counts),
                    "number_lost_if_collapse_by_blank_chunk_and_index": sum(counts.values()) - len(counts),
                    "caution": "Shard placement and sorted-account rank are derived locally from the saved V3 layout; RPC changes do not expose shard IDs or source index_in_block. Actual ingestion key or deduplication operation is not established."},
                "precision": {"field_comparisons": len(field_checks),
                              "nearest_binary64_mismatches_by_field": dict(nearest_bad),
                              "max_abs_error_by_field": {f: value[1] for f, value in maximum.items()},
                              "max_combined_error": max(combined, key=lambda x: abs(Decimal(x["rpc_minus_bigquery_combined_near"]))),
                              "field_checks": field_checks},
                "rpc_within_account_order": {
                    a: [{"response_array_index": i, "cause": x["cause"], "type": x["type"],
                         "amount": x["change"].get("amount"), "locked": x["change"].get("locked")}
                        for i, x in records] for a, records in by.items()},
                "rpc_only_validator_post_states": [
                    {"account_id": a, "amount": validators[a][1]["change"]["amount"],
                     "locked": validators[a][1]["change"]["locked"],
                     "valid_before_state": None, "monetary_change": None} for a in only],
                "independently_measured_issuance": None, "independently_measured_actual_burn": None,
            }
        a = set(report["blocks"]["A"]["membership"]["rpc_only_validator_accounts"])
        b = set(report["blocks"]["B"]["membership"]["rpc_only_validator_accounts"])
        report["additional_validator_population"] = {
            "distinct_accounts_across_AB": len(a | b), "update_records_across_AB": len(a) + len(b),
            "in_both_rpc_only_sets": len(a & b)}
    return report


def near_integer(value):
    whole, fraction = divmod(abs(value), 10**24)
    return f"{'-' if value < 0 else ''}{whole}.{fraction:024d}"


def derivation(command, method):
    return {"offline_command": f"python3 -B analysis/13_consolidate_supply_evidence.py {command}",
            "method": method, "code_hashes": fingerprints([
                Path(__file__), ROOT / "analysis/10_supply_comparison_check.py",
                ROOT / "analysis/11_collect_canonical_validator_evidence.py",
                ROOT / "analysis/12_collect_bitwise_parent_witness.py"])}


def witness_report():
    witness.validate_saved(WITNESS_RUN)
    witness.preflight()
    before = capture.recorded(WITNESS_RUN, witness.request())
    unions, _, _ = capture.validate_stage1(witness.CANONICAL_RUN)
    block = capture.recorded(witness.CANONICAL_RUN / "stage1", capture.request("A", "block"))
    updates = capture.recorded(witness.CANONICAL_RUN / "stage2", capture.request("A", "changes", unions["A"]))
    records = [(i, x) for i, x in enumerate(updates["changes"])
               if x["change"]["account_id"] == witness.ACCOUNT]
    capture.require(len(records) == 1, "Ambiguous witness account ordering")
    position, record = records[0]
    after = record["change"]
    manifest = capture.decode((WITNESS_RUN / "run.json").read_bytes())
    capture.require(position == manifest["post_state_response_array_index"]
                    and record["cause"]["type"] == "validator_accounts_update"
                    and record["type"] == "account_update"
                    and updates["block_hash"] == manifest["post_state_block_hash"] == block["header"]["hash"]
                    and block["header"]["prev_hash"] == before["block_hash"]
                    and block["header"]["height"] == before["block_height"] + 1,
                    "Witness predecessor/post-state identity differs")
    paths = [ROOT / path for path in manifest["input_hashes"]]
    paths += [p for p in WITNESS_RUN.iterdir() if p.is_file()]

    def state(value, height, block_hash):
        return {"block_height": height, "block_hash": block_hash,
                "amount_yocto": value["amount"], "locked_yocto": value["locked"],
                "combined_yocto": str(int(value["amount"]) + int(value["locked"])),
                "code_hash": value["code_hash"], "storage_usage": value["storage_usage"]}

    liquid = int(after["amount"]) - int(before["amount"])
    locked = int(after["locked"]) - int(before["locked"])
    return {
        "account_id": witness.ACCOUNT,
        "parent": state(before, before["block_height"], before["block_hash"]),
        "post": {**state(after, block["header"]["height"], updates["block_hash"]),
                 "response_array_index": position, "cause": record["cause"], "type": record["type"]},
        "change": {"liquid_yocto": str(liquid), "locked_yocto": str(locked),
                   "combined_yocto": str(liquid + locked), "combined_near": near_integer(liquid + locked)},
        "source_hashes": fingerprints(paths),
        "derivation": derivation("witness", "Validate saved request/response and input hashes, parent linkage, one validator update for the account and its RPC array position. Subtract parent liquid-plus-locked integer yoctoNEAR from the validator post-state; format NEAR by integer division by 10^24."),
        "interpretation": "One BigQuery-omitted account balance change. Not an adjustment to the old daily total or independently measured issuance. Later predecessor comparisons may already incorporate omitted changes.",
        "independently_measured_issuance_near": None, "independently_measured_actual_burn_near": None,
    }


def supply_report():
    report = checker.audit()
    with localcontext() as context:
        context.prec = 50
        totals = report["totals"]

        def row(value):
            return {"start": str(value["start"]), "end": str(value["end"]),
                    **{output: str(value[field]) for output, field in (
                        ("opening_supply_near", "opening_supply"), ("closing_supply_near", "closing_supply"),
                        ("net_supply_movement_near", "supply_change"),
                        ("raw_validator_balance_change_near", "validator_change"), ("residual_near", "residual"))},
                    "independently_measured_issuance_near": None, "independently_measured_actual_burn_near": None}

        positive = sum((max(x["residual"], Decimal(0)) for x in report["daily"]), Decimal(0))
        negative = sum((min(x["residual"], Decimal(0)) for x in report["daily"]), Decimal(0))
        absolute = sum((abs(x["residual"]) for x in report["daily"]), Decimal(0))
        capture.require(positive + negative == totals["residual"] and positive - negative == absolute,
                        "Daily residual cancellation identity failed")
        period = {**totals, "start": checker.START, "end": checker.END}
        largest = max(report["daily"], key=lambda x: abs(x["residual"]))
        return {
            "period": row(period), "opening_baseline_date": str(checker.BASELINE),
            "weekly": [row(x) for x in report["weekly"]], "daily": [row(x) for x in report["daily"]],
            "cancellation": {"period_residual_as_pct_of_net_supply_change": str(100 * totals["residual"] / totals["supply_change"]),
                             "period_residual_as_pct_of_opening_supply": str(100 * totals["residual"] / totals["opening_supply"]),
                             "sum_positive_daily_residuals_near": str(positive),
                             "sum_negative_daily_residuals_near": str(negative),
                             "sum_absolute_daily_residuals_near": str(absolute),
                             "largest_absolute_daily_residual_date": str(largest["start"]),
                             "largest_absolute_daily_residual_signed_near": str(largest["residual"])},
            "saved_arithmetic_checks": {"count": len(report["discrepancies"]),
                                        "tolerance_near": str(checker.TOLERANCE),
                                        "maximum_absolute_discrepancy_near": str(max(abs(x) for _, x in report["discrepancies"]))},
            "source_hashes": fingerprints([checker.RESULTS / name for name in checker.SOURCES.values()]),
            "derivation": derivation("supply", "Reuse analysis/10 validation of seven saved exports and all expected daily/weekly coverage. Compute endpoint movement from the 23 August close, sum raw saved validator changes, and subtract. Use Decimal precision 50; retain exported digits. Sum absolute daily residuals before any weekly or period netting."),
            "limitations": ["Source FLOAT precision is not recovered by Decimal or BIGNUMERIC conversion.",
                            "The 0.00001 NEAR tolerance checks saved arithmetic only, not source accuracy or economic reconciliation.",
                            "This table preserves the original observed series. No recovered RPC changes are added.",
                            "Validator balance changes are not independently measured issuance. Execution spending and supply decreases are not independently measured actual burn.",
                            "The two-block RPC discrepancy is not evidence of the same discrepancy throughout the dataset or a reassessment of unrelated transaction findings."],
        }


def table(report):
    lines = ["All dates are in 2026; values are NEAR rounded to 0.01 for display.",
             "Opening baseline: 23 August closing supply. Issuance and actual burn remain unavailable.", "",
             "| Week | Opening supply | Closing supply | Net movement | Raw validator change | Residual |",
             "|---|---:|---:|---:|---:|---:|"]
    for value in report["weekly"] + [report["period"]]:
        label = value["start"][5:] + "–" + value["end"][5:]
        values = [format(Decimal(value[key]), ",.2f") for key in (
            "opening_supply_near", "closing_supply_near", "net_supply_movement_near",
            "raw_validator_balance_change_near", "residual_near")]
        lines.append("| " + " | ".join([label] + values) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("comparison", "witness", "supply", "table", "check"))
    parser.add_argument("--output", type=Path, help="create a new derived file; refuse overwrite")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            for path, producer in ((witness.COMPARISON, comparison_report),
                                   (WITNESS_SUMMARY, witness_report), (SUPPLY_SUMMARY, supply_report)):
                capture.require(path.read_bytes() == capture.json_bytes(producer()),
                                f"Regenerated artifact differs: {path.name}")
            raw = b"Three derived artifacts reproduce byte-for-byte; saved arithmetic and identity checks passed.\n"
        elif args.command == "table":
            raw = table(supply_report()).encode()
        else:
            producer = {"comparison": comparison_report, "witness": witness_report,
                        "supply": supply_report}[args.command]
            raw = capture.json_bytes(producer())
        if args.output:
            capture.require(args.output.resolve() not in {
                ROOT / path for path in capture.decode(witness.PROVENANCE.read_bytes())["inputs"]},
                "Output is a recorded input")
            capture.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, TypeError, KeyError, ArithmeticError) as exc:
        print(f"Offline consolidation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
