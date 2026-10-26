import csv
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

START = date(2026, 8, 24)
END = date(2026, 10, 18)
BASELINE = START - timedelta(days=1)

OUTPUT = RESULTS / f"34_weekly_economic_comparison_{PERIOD}.csv"
TOLERANCE = Decimal("0.00001")


def read_csv(filename):
    with (RESULTS / filename).open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"{filename} is empty.")

    return rows


def number(row, field):
    value = Decimal(row[field])

    if not value.is_finite():
        raise ValueError(f"Nonfinite value in {field}.")

    return value


def index_dates(rows, field, start, end):
    indexed = {}

    for row in rows:
        day = date.fromisoformat(row[field])

        if day in indexed:
            raise ValueError(f"Duplicate date: {day}.")

        indexed[day] = row

    expected = {
        start + timedelta(days=offset)
        for offset in range((end - start).days + 1)
    }

    if set(indexed) != expected:
        raise ValueError(f"Incomplete or unexpected dates in {field}.")

    return indexed


def close_enough(left, right, description):
    if abs(left - right) > TOLERANCE:
        raise ValueError(f"Reconciliation failed: {description}.")


def total(rows, field):
    return sum(
        (number(row, field) for row in rows),
        Decimal(0),
    )


def main():
    weekly = read_csv(
        f"14_weekly_growth_and_costs_{PERIOD}.csv"
    )
    supply_rows = read_csv(
        "28_daily_supply_checks_2026-08-23_to_2026-10-18.csv"
    )
    validator_rows = read_csv(
        f"32_daily_validator_balance_changes_{PERIOD}.csv"
    )
    movement_rows = read_csv(
        f"33_daily_block_supply_movements_{PERIOD}.csv"
    )

    supply = index_dates(
        supply_rows, "block_date", BASELINE, END
    )
    validators = index_dates(
        validator_rows, "block_date", START, END
    )
    movements = index_dates(
        movement_rows, "block_date", START, END
    )

    expected_weeks = {
        START + timedelta(weeks=offset)
        for offset in range(8)
    }

    week_dates = [
        date.fromisoformat(row["week_start"])
        for row in weekly
    ]

    if len(weekly) != 8 or set(week_dates) != expected_weeks:
        raise ValueError("Expected eight distinct complete weeks.")

    supply_checks = [
        "missing_block_heights",
        "missing_block_hashes",
        "missing_timestamps",
        "timestamp_date_mismatches",
        "missing_or_invalid_supply_values",
    ]

    for day, row in supply.items():
        if any(number(row, field) != 0 for field in supply_checks):
            raise ValueError(f"Supply validation issue on {day}.")

        block_rows = number(row, "block_rows")

        if (
            block_rows <= 0
            or block_rows != number(row, "distinct_block_heights")
            or block_rows != number(row, "distinct_block_hashes")
        ):
            raise ValueError(f"Block count issue on {day}.")

        if number(row, "closing_total_supply_near") <= 0:
            raise ValueError(f"Invalid closing supply on {day}.")

    for day in sorted(validators):
        validator = validators[day]
        movement = movements[day]

        if validator["comparison_check"] != "MATCHED_PREVIOUS_RECORD":
            raise ValueError(f"Unmatched validator updates on {day}.")

        if movement["comparison_check"] != "MATCHED_PREVIOUS_BLOCK":
            raise ValueError(f"Unmatched block records on {day}.")

        validator_count = sum(
            number(validator, field)
            for field in [
                "increases_above_tolerance",
                "decreases_below_negative_tolerance",
                "changes_within_tolerance",
            ]
        )
        close_enough(
            validator_count,
            number(validator, "update_records"),
            f"validator counts on {day}",
        )

        block_count = sum(
            number(movement, field)
            for field in [
                "blocks_with_supply_increase",
                "blocks_with_supply_decrease",
                "blocks_with_unchanged_supply",
            ]
        )
        close_enough(
            block_count,
            number(movement, "block_records"),
            f"movement counts on {day}",
        )
        close_enough(
            block_count,
            number(supply[day], "block_rows"),
            f"supply and movement block counts on {day}",
        )

        previous_day = day - timedelta(days=1)
        endpoint_change = (
            number(supply[day], "closing_total_supply_near")
            - number(
                supply[previous_day],
                "closing_total_supply_near",
            )
        )

        close_enough(
            number(movement, "net_observed_supply_change_near"),
            endpoint_change,
            f"daily supply change on {day}",
        )
        close_enough(
            number(
                movement,
                "observed_positive_supply_movements_near",
            )
            - number(
                movement,
                "observed_supply_decrease_magnitude_near",
            ),
            endpoint_change,
            f"positive and negative movements on {day}",
        )

    output_rows = []

    for row in sorted(weekly, key=lambda item: item["week_start"]):
        week_start = date.fromisoformat(row["week_start"])
        week_end = week_start + timedelta(days=6)

        if (
            row["week_end"] != week_end.isoformat()
            or int(row["observed_days"]) != 7
        ):
            raise ValueError(f"Incomplete week starting {week_start}.")

        if (
            number(row, "invalid_gas_values") != 0
            or number(row, "invalid_token_cost_values") != 0
        ):
            raise ValueError(f"Invalid execution costs for {week_start}.")

        days = [
            week_start + timedelta(days=offset)
            for offset in range(7)
        ]
        week_validators = [validators[day] for day in days]
        week_movements = [movements[day] for day in days]

        opening_supply = number(
            supply[week_start - timedelta(days=1)],
            "closing_total_supply_near",
        )
        closing_supply = number(
            supply[week_end],
            "closing_total_supply_near",
        )
        net_supply_change = closing_supply - opening_supply

        validator_change = total(
            week_validators,
            "raw_matched_balance_change_near",
        )
        positive_movements = total(
            week_movements,
            "observed_positive_supply_movements_near",
        )
        decrease_magnitude = total(
            week_movements,
            "observed_supply_decrease_magnitude_near",
        )

        close_enough(
            total(
                week_movements,
                "net_observed_supply_change_near",
            ),
            net_supply_change,
            f"weekly supply endpoints for {week_start}",
        )

        receipt_count = number(row, "receipt_execution_outcomes")
        recorded_cost = number(row, "recorded_execution_cost_near")

        if receipt_count <= 0:
            raise ValueError(f"No receipt outcomes for {week_start}.")

        output_rows.append(
            {
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "transactions": row["transactions"],
                "weekly_active_signing_accounts":
                    row["weekly_active_signing_accounts"],
                "receipt_execution_outcomes":
                    row["receipt_execution_outcomes"],
                "recorded_receipt_execution_cost_near":
                    recorded_cost,
                "failed_receipt_execution_cost_near":
                    number(row, "failed_receipt_cost_near"),
                "average_recorded_cost_per_receipt_near":
                    recorded_cost / receipt_count,
                "transaction_change_pct":
                    row["transaction_change_pct"],
                "weekly_active_accounts_change_pct":
                    row["weekly_active_accounts_change_pct"],
                "recorded_cost_change_pct":
                    row["recorded_cost_change_pct"],
                "opening_supply_baseline_date":
                    (week_start - timedelta(days=1)).isoformat(),
                "opening_observed_supply_near":
                    opening_supply,
                "closing_observed_supply_near":
                    closing_supply,
                "net_observed_supply_change_near":
                    net_supply_change,
                "net_observed_supply_change_pct":
                    Decimal(100) * net_supply_change / opening_supply,
                "validator_update_records":
                    int(total(week_validators, "update_records")),
                "validator_update_net_balance_change_near":
                    validator_change,
                "observed_positive_supply_movements_near":
                    positive_movements,
                "observed_supply_decrease_magnitude_near":
                    decrease_magnitude,
                "positive_supply_movements_minus_validator_change_near":
                    positive_movements - validator_change,
                "net_supply_change_minus_validator_change_near":
                    net_supply_change - validator_change,
            }
        )

    close_enough(
        total(output_rows, "net_observed_supply_change_near"),
        number(supply[END], "closing_total_supply_near")
        - number(supply[BASELINE], "closing_total_supply_near"),
        "full-period supply change",
    )

    temporary = OUTPUT.with_suffix(".csv.tmp")

    with temporary.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(output_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    temporary.replace(OUTPUT)

    print("Validated eight complete weeks and 56 daily comparisons.")
    print(f"Results saved: {OUTPUT}")
    print(
        "Supply movements and validator balance changes are separate "
        "observations; reconciliation differences remain unresolved."
    )
    print(
        "Recorded receipt costs are grouped by execution date. "
        "They are not measured permanent burning or holder returns."
    )


if __name__ == "__main__":
    main()