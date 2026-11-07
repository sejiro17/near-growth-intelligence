"""Read-only comparisons of the saved eight-week economic exports.

No network access, result regeneration, or output-file writes. Decimal preserves
exported digits; it cannot restore accuracy lost in source floating-point fields.
"""

import argparse
import csv
import sys
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext
from pathlib import Path


START = date(2026, 8, 24)
END = date(2026, 10, 18)
BASELINE = START - timedelta(days=1)
PERIOD = f"{START}_to_{END}"
RESULTS = Path(__file__).resolve().parents[1] / "results"
TOLERANCE = Decimal("0.00001")
# A comparison target from the earlier audit, never substituted for input data.
PREVIOUSLY_REPORTED_RESIDUAL = Decimal("16599.51437846")
ZERO = Decimal(0)

SOURCES = {
    "supply": "28_daily_supply_checks_2026-08-23_to_2026-10-18.csv",
    "validators": f"32_daily_validator_balance_changes_{PERIOD}.csv",
    "movements": f"33_daily_block_supply_movements_{PERIOD}.csv",
    "receipts": f"13_weekly_execution_costs_{PERIOD}.csv",
    "conversions": f"36_weekly_transaction_conversion_costs_{PERIOD}.csv",
    "economic": f"34_weekly_economic_comparison_{PERIOD}.csv",
    "spending": f"37_weekly_execution_spending_{PERIOD}.csv",
}

# Explicit schemas also identify numerical columns, including unused diagnostics.
COLUMNS = {
    "supply": """block_date block_rows distinct_block_heights distinct_block_hashes
        missing_block_heights missing_block_hashes missing_timestamps
        timestamp_date_mismatches missing_or_invalid_supply_values first_block_height
        last_block_height first_timestamp_utc last_timestamp_utc closing_block_height
        closing_block_hash closing_block_timestamp_utc closing_total_supply_near
        previous_day_closing_supply_near observed_daily_supply_change_near
        observed_daily_supply_change_pct""",
    "validators": """block_date comparison_check update_records affected_accounts
        update_block_heights increases_above_tolerance decreases_below_negative_tolerance
        changes_within_tolerance raw_matched_balance_change_near
        positive_balance_change_above_tolerance_near negative_balance_change_below_tolerance_near
        balance_change_within_tolerance_near minimum_balance_change_near
        maximum_balance_change_near comparison_tolerance_near""",
    "movements": """block_date comparison_check block_records blocks_with_supply_increase
        blocks_with_supply_decrease blocks_with_unchanged_supply net_observed_supply_change_near
        observed_positive_supply_movements_near observed_supply_decrease_magnitude_near
        minimum_block_supply_change_near maximum_block_supply_change_near""",
    "receipts": """week_start week_end observed_days receipt_execution_outcomes
        failed_receipt_outcomes success_value_outcomes success_receipt_id_outcomes
        other_or_missing_statuses recorded_gas_tgas recorded_execution_cost_near
        failed_receipt_cost_near failed_receipt_share_pct failed_receipt_cost_share_pct
        average_recorded_cost_per_receipt_near invalid_gas_values invalid_token_cost_values""",
    "conversions": """week_start week_end transactions distinct_transaction_hashes
        missing_cost_records negative_cost_records nonfinite_cost_records
        recorded_conversion_cost_near recorded_conversion_cost_per_transaction_near""",
    "economic": """week_start week_end transactions weekly_active_signing_accounts
        receipt_execution_outcomes recorded_receipt_execution_cost_near
        failed_receipt_execution_cost_near average_recorded_cost_per_receipt_near
        transaction_change_pct weekly_active_accounts_change_pct recorded_cost_change_pct
        opening_supply_baseline_date opening_observed_supply_near closing_observed_supply_near
        net_observed_supply_change_near net_observed_supply_change_pct validator_update_records
        validator_update_net_balance_change_near observed_positive_supply_movements_near
        observed_supply_decrease_magnitude_near positive_supply_movements_minus_validator_change_near
        net_supply_change_minus_validator_change_near""",
    "spending": """week_start week_end transactions receipt_execution_outcomes
        recorded_conversion_cost_near recorded_receipt_execution_cost_near
        combined_recorded_execution_spending_near conversion_share_of_recorded_spending_pct
        receipt_share_of_recorded_spending_pct""",
}
TEXT_FIELDS = set("""block_date comparison_check first_timestamp_utc last_timestamp_utc
    closing_block_hash closing_block_timestamp_utc week_start week_end
    opening_supply_baseline_date""".split())
NULLABLE = {
    "supply": set("""previous_day_closing_supply_near observed_daily_supply_change_near
        observed_daily_supply_change_pct""".split()),
    "economic": set("""transaction_change_pct weekly_active_accounts_change_pct
        recorded_cost_change_pct""".split()),
}
COUNTS = {
    "supply": """block_rows distinct_block_heights distinct_block_hashes missing_block_heights
        missing_block_hashes missing_timestamps timestamp_date_mismatches
        missing_or_invalid_supply_values first_block_height last_block_height closing_block_height""",
    "validators": """update_records affected_accounts update_block_heights increases_above_tolerance
        decreases_below_negative_tolerance changes_within_tolerance""",
    "movements": """block_records blocks_with_supply_increase blocks_with_supply_decrease
        blocks_with_unchanged_supply""",
    "receipts": """observed_days receipt_execution_outcomes failed_receipt_outcomes
        success_value_outcomes success_receipt_id_outcomes other_or_missing_statuses
        invalid_gas_values invalid_token_cost_values""",
    "conversions": """transactions distinct_transaction_hashes missing_cost_records
        negative_cost_records nonfinite_cost_records""",
    "economic": """transactions weekly_active_signing_accounts receipt_execution_outcomes
        validator_update_records""",
    "spending": "transactions receipt_execution_outcomes",
}


def require(condition, description):
    if not condition:
        raise ValueError(description)


def expected_dates(start, end, step=1):
    return {start + timedelta(days=i) for i in range(0, (end - start).days + 1, step)}


def read_table(directory, key):
    """Parse CSV strings straight into Decimal; reject malformed or incomplete data."""
    path = directory / SOURCES[key]
    required = COLUMNS[key].split()
    daily = key in {"supply", "validators", "movements"}
    date_field = "block_date" if daily else "week_start"
    expected = expected_dates(BASELINE if key == "supply" else START, END, 1 if daily else 7)
    indexed = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        require(len(headers) == len(set(headers)), f"{path.name}: duplicate columns")
        require(set(required) <= set(headers),
                f"{path.name}: missing required columns: {sorted(set(required) - set(headers))}")
        for line, raw in enumerate(reader, 2):
            label = f"{path.name}:{line}"
            require(None not in raw and all(raw[k] is not None for k in required),
                    f"{label}: malformed CSV row")
            row = {}
            for field in required:
                value = raw[field].strip()
                if value.lower() in {"", "null"} and field in NULLABLE.get(key, set()):
                    row[field] = None
                elif field in TEXT_FIELDS:
                    require(bool(value), f"{label}: empty {field}")
                    row[field] = value
                else:
                    try:
                        number = Decimal(value)
                    except InvalidOperation as exc:
                        raise ValueError(f"{label}: invalid number in {field}") from exc
                    require(number.is_finite(), f"{label}: nonfinite {field}")
                    row[field] = number
            try:
                day = date.fromisoformat(row[date_field])
            except ValueError as exc:
                raise ValueError(f"{label}: invalid {date_field}") from exc
            require(day not in indexed, f"{path.name}: duplicate date {day}")
            for field in COUNTS[key].split():
                value = row[field]
                require(value >= 0 and value == value.to_integral_value(),
                        f"{label}: invalid integer count {field}")
            if not daily:
                require(row["week_end"] == str(day + timedelta(days=6)),
                        f"{label}: incomplete week")
            indexed[day] = row
    require(set(indexed) == expected,
            f"{path.name}: incomplete or unexpected dates; "
            f"missing={sorted(expected - set(indexed))}, extra={sorted(set(indexed) - expected)}")
    return indexed


def total(rows, field):
    return sum((row[field] for row in rows), ZERO)


def audit(directory=RESULTS):
    # Local context avoids changing callers' Decimal settings.
    with localcontext() as context:
        context.prec = 50
        return _audit(Path(directory))


def _audit(directory):
    tables = {key: read_table(directory, key) for key in SOURCES}
    s, v, m = (tables[key] for key in ("supply", "validators", "movements"))
    discrepancies = []

    def near(actual, expected, label):
        difference = actual - expected
        require(abs(difference) <= TOLERANCE,
                f"{label}: arithmetic discrepancy {difference} NEAR exceeds {TOLERANCE}")
        discrepancies.append((label, difference))

    def zero_diagnostics(row, fields, label):
        require(all(row[field] == 0 for field in fields.split()),
                f"{label}: nonzero coverage/validity diagnostic")

    for day, row in s.items():
        label = f"supply {day}"
        zero_diagnostics(row, """missing_block_heights missing_block_hashes missing_timestamps
            timestamp_date_mismatches missing_or_invalid_supply_values""", label)
        require(row["block_rows"] == row["distinct_block_heights"]
                == row["distinct_block_hashes"] > 0, f"{label}: block counts disagree")
        require(row["first_block_height"] <= row["last_block_height"]
                == row["closing_block_height"], f"{label}: closing height disagrees")
        require(row["closing_total_supply_near"] > 0, f"{label}: nonpositive supply")
        if day == BASELINE:
            require(all(row[k] is None for k in NULLABLE["supply"]),
                    f"{label}: unexpected baseline comparison")
        else:
            require(all(row[k] is not None for k in NULLABLE["supply"]),
                    f"{label}: missing daily comparison")

    def comparison(days):
        opening = s[days[0] - timedelta(days=1)]["closing_total_supply_near"]
        closing = s[days[-1]]["closing_total_supply_near"]
        vr, mr = [v[d] for d in days], [m[d] for d in days]
        result = {
            "opening_supply": opening, "closing_supply": closing,
            "supply_change": closing - opening,
            "block_net": total(mr, "net_observed_supply_change_near"),
            "positive_movements": total(mr, "observed_positive_supply_movements_near"),
            "decrease_magnitude": total(mr, "observed_supply_decrease_magnitude_near"),
            "validator_change": total(vr, "raw_matched_balance_change_near"),
        }
        result["residual"] = result["supply_change"] - result["validator_change"]
        result["positive_minus_validator"] = result["positive_movements"] - result["validator_change"]
        label = f"{days[0]}..{days[-1]}"
        near(result["block_net"], result["supply_change"], f"{label} block net vs endpoints")
        near(result["positive_movements"] - result["decrease_magnitude"],
             result["supply_change"], f"{label} positive minus decrease vs endpoints")
        near(result["positive_movements"] - result["decrease_magnitude"],
             result["block_net"], f"{label} positive minus decrease vs block net")
        return result

    daily = []
    for day in sorted(v):
        vr, mr = v[day], m[day]
        require(vr["comparison_check"] == "MATCHED_PREVIOUS_RECORD",
                f"validators {day}: unmatched records")
        require(mr["comparison_check"] == "MATCHED_PREVIOUS_BLOCK",
                f"movements {day}: unmatched blocks")
        require(sum(vr[k] for k in ("increases_above_tolerance",
                "decreases_below_negative_tolerance", "changes_within_tolerance"))
                == vr["update_records"] > 0, f"validators {day}: category counts disagree")
        require(0 < vr["affected_accounts"] <= vr["update_records"]
                and 0 < vr["update_block_heights"] <= vr["update_records"],
                f"validators {day}: invalid coverage counts")
        require(vr["comparison_tolerance_near"] == Decimal("0.000001"),
                f"validators {day}: unexpected diagnostic threshold")
        require(vr["positive_balance_change_above_tolerance_near"] >= 0
                and vr["negative_balance_change_below_tolerance_near"] <= 0
                and vr["minimum_balance_change_near"] <= vr["maximum_balance_change_near"],
                f"validators {day}: invalid signed balance diagnostics")
        near(vr["raw_matched_balance_change_near"], sum(vr[k] for k in (
            "positive_balance_change_above_tolerance_near",
            "negative_balance_change_below_tolerance_near", "balance_change_within_tolerance_near")),
            f"validators {day} raw vs diagnostic parts")
        require(sum(mr[k] for k in ("blocks_with_supply_increase", "blocks_with_supply_decrease",
                "blocks_with_unchanged_supply")) == mr["block_records"] == s[day]["block_rows"],
                f"movements {day}: block counts disagree")
        require(mr["observed_positive_supply_movements_near"] >= 0
                and mr["observed_supply_decrease_magnitude_near"] >= 0
                and mr["minimum_block_supply_change_near"] <= mr["maximum_block_supply_change_near"],
                f"movements {day}: invalid movement diagnostics")
        row = comparison([day])
        row["start"] = row["end"] = day
        near(s[day]["previous_day_closing_supply_near"], row["opening_supply"],
             f"supply {day} saved previous close")
        near(s[day]["observed_daily_supply_change_near"], row["supply_change"],
             f"supply {day} saved daily change")
        near(s[day]["observed_daily_supply_change_pct"] * row["opening_supply"] / 100,
             row["supply_change"], f"supply {day} saved daily percentage expressed in NEAR")
        daily.append(row)

    weekly = []
    for week in sorted(tables["receipts"]):
        days = [week + timedelta(days=i) for i in range(7)]
        row = comparison(days)
        row.update(start=week, end=days[-1])
        receipt, conversion, economic, spending = (
            tables[k][week] for k in ("receipts", "conversions", "economic", "spending"))
        require(receipt["observed_days"] == 7, f"receipts {week}: incomplete week")
        zero_diagnostics(receipt, "other_or_missing_statuses invalid_gas_values invalid_token_cost_values",
                         f"receipts {week}")
        require(sum(receipt[k] for k in ("failed_receipt_outcomes", "success_value_outcomes",
                "success_receipt_id_outcomes")) == receipt["receipt_execution_outcomes"] > 0,
                f"receipts {week}: outcome counts disagree")
        zero_diagnostics(conversion, "missing_cost_records negative_cost_records nonfinite_cost_records",
                         f"conversions {week}")
        require(conversion["transactions"] == conversion["distinct_transaction_hashes"]
                == economic["transactions"] == spending["transactions"] > 0,
                f"spending {week}: transaction counts disagree")
        require(receipt["receipt_execution_outcomes"] == economic["receipt_execution_outcomes"]
                == spending["receipt_execution_outcomes"], f"spending {week}: receipt counts disagree")
        require(economic["validator_update_records"] == total([v[d] for d in days], "update_records"),
                f"economic {week}: validator counts disagree")
        require(economic["opening_supply_baseline_date"] == str(week - timedelta(days=1)),
                f"economic {week}: wrong opening baseline date")
        require(all(economic[k] is not None for k in NULLABLE["economic"]) if week != START
                else all(economic[k] is None for k in NULLABLE["economic"]),
                f"economic {week}: unexpected missing percentage comparison")
        row["conversion_spending"] = conversion["recorded_conversion_cost_near"]
        row["receipt_spending"] = receipt["recorded_execution_cost_near"]
        row["combined_spending"] = row["conversion_spending"] + row["receipt_spending"]
        require(row["conversion_spending"] >= 0 and row["receipt_spending"] > 0
                and receipt["recorded_gas_tgas"] >= 0
                and 0 <= receipt["failed_receipt_cost_near"] <= row["receipt_spending"],
                f"spending {week}: invalid spending amounts")
        near(conversion["recorded_conversion_cost_per_transaction_near"] * conversion["transactions"],
             row["conversion_spending"], f"conversions {week} average times count")
        for source, label in ((receipt, "receipts"), (economic, "economic")):
            near(source["average_recorded_cost_per_receipt_near"] * receipt["receipt_execution_outcomes"],
                 row["receipt_spending"], f"{label} {week} average times count")
        for field, numerator, denominator in (
            ("failed_receipt_share_pct", receipt["failed_receipt_outcomes"], receipt["receipt_execution_outcomes"]),
            ("failed_receipt_cost_share_pct", receipt["failed_receipt_cost_near"], row["receipt_spending"]),
        ):
            require(receipt[field] == (100 * numerator / denominator).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP), f"receipts {week}: rounded {field} disagrees")
        expected_economic = {
            "opening_observed_supply_near": row["opening_supply"],
            "closing_observed_supply_near": row["closing_supply"],
            "net_observed_supply_change_near": row["supply_change"],
            "validator_update_net_balance_change_near": row["validator_change"],
            "observed_positive_supply_movements_near": row["positive_movements"],
            "observed_supply_decrease_magnitude_near": row["decrease_magnitude"],
            "positive_supply_movements_minus_validator_change_near": row["positive_minus_validator"],
            "net_supply_change_minus_validator_change_near": row["residual"],
            "recorded_receipt_execution_cost_near": row["receipt_spending"],
            "failed_receipt_execution_cost_near": receipt["failed_receipt_cost_near"],
        }
        for field, expected in expected_economic.items():
            near(economic[field], expected, f"economic {week} {field}")
        near(economic["net_observed_supply_change_pct"] * row["opening_supply"] / 100,
             row["supply_change"], f"economic {week} supply percentage expressed in NEAR")
        for field, metric in (("recorded_conversion_cost_near", "conversion_spending"),
                              ("recorded_receipt_execution_cost_near", "receipt_spending"),
                              ("combined_recorded_execution_spending_near", "combined_spending")):
            near(spending[field], row[metric], f"spending {week} {field}")
        for field, metric in (("conversion_share_of_recorded_spending_pct", "conversion_spending"),
                              ("receipt_share_of_recorded_spending_pct", "receipt_spending")):
            near(spending[field] * row["combined_spending"] / 100, row[metric],
                 f"spending {week} {field} expressed in NEAR")
        weekly.append(row)

    totals = comparison(sorted(v))
    for field in ("conversion_spending", "receipt_spending", "combined_spending"):
        totals[field] = total(weekly, field)
    totals["validator_update_records"] = total(list(v.values()), "update_records")
    totals["block_records"] = total(list(m.values()), "block_records")
    totals["transactions"] = total(list(tables["conversions"].values()), "transactions")
    totals["receipt_execution_outcomes"] = total(list(tables["receipts"].values()), "receipt_execution_outcomes")
    for label, rows in (("daily", daily), ("weekly", weekly)):
        near(total(rows, "supply_change"), totals["supply_change"], f"period sum of {label} endpoint changes")
        near(total(rows, "residual"), totals["residual"], f"period sum of {label} comparison residuals")
    near(totals["residual"], PREVIOUSLY_REPORTED_RESIDUAL,
         "computed period residual vs previously reported residual (not a zero target)")
    return {"daily": daily, "weekly": weekly, "totals": totals, "discrepancies": discrepancies,
            "independent_issuance": None, "actual_burn": None}


def print_report(report, stream=None):
    stream = sys.stdout if stream is None else stream
    def emit(value=""):
        print(value, file=stream)

    emit(f"Saved supply comparison: {START} through {END}, UTC; opening baseline {BASELINE} close")
    emit("Units: NEAR unless a field is a count. Decimal arithmetic preserves exported digits only.")
    emit(f"Saved arithmetic consistency: PASS (absolute tolerance {TOLERANCE} NEAR).")
    emit("This tolerance proves neither source accuracy nor economic reconciliation.")
    emit("Supply movement, raw validator balance change and recorded execution spending are separate observations.")
    emit("Validator changes are not independently measured issuance; decreases/spending are not measured actual burn.")
    emit("Independently measured issuance: unavailable; actual burn: unavailable (neither is zero).")
    emit("Residual = endpoint supply change minus raw validator balance change; it remains unexplained.")
    fields = ["opening_supply", "closing_supply", "supply_change", "block_net", "positive_movements",
              "decrease_magnitude", "validator_change", "residual", "positive_minus_validator"]
    for label, rows in (("Daily", report["daily"]), ("Weekly", report["weekly"])):
        emit()
        emit(label + " observational comparisons")
        metrics = fields + (["conversion_spending", "receipt_spending", "combined_spending"] if label == "Weekly" else [])
        if label == "Daily":
            emit("Daily spending: unavailable from these weekly spending exports; no allocation is assumed.")
        else:
            emit("Spending uses conversion submission dates and receipt execution dates, not matched transaction chains.")
        emit(" | ".join(["start", "end"] + metrics))
        for row in rows:
            emit(" | ".join([str(row["start"]), str(row["end"])] + [str(row[k]) for k in metrics]))
    emit()
    emit("Full-period totals (supply levels are endpoints, never sums)")
    for key, value in report["totals"].items():
        emit(f"{key}: {value}")
    emit(f"Earlier reported residual: {PREVIOUSLY_REPORTED_RESIDUAL}; computed value above passes saved consistency check.")
    emit()
    emit("Arithmetic discrepancies: actual minus expected, NEAR; exact zeros omitted")
    for label, difference in report["discrepancies"]:
        if difference != 0:
            emit(f"{label}: {difference}")
    emit(f"Checks passed: {len(report['discrepancies'])}; maximum absolute discrepancy: "
         f"{max(abs(value) for _, value in report['discrepancies'])} NEAR")
    emit()
    emit("Dates ranked by absolute unexplained residual (signed NEAR; ties ordered by date)")
    ranked = sorted(report["daily"], key=lambda row: (-abs(row["residual"]), row["start"]))
    for rank, row in enumerate(ranked, 1):
        emit(f"{rank}. {row['start']}: {row['residual']}")
    emit(f"Largest daily residual: {ranked[0]['start']}: {ranked[0]['residual']} NEAR")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=RESULTS,
                        help="directory containing the seven saved exports (read only)")
    args = parser.parse_args(argv)
    try:
        report = audit(args.results_dir)
    except (OSError, ValueError, InvalidOperation) as exc:
        print(f"Supply comparison failed: {exc}", file=sys.stderr)
        return 1
    print_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
