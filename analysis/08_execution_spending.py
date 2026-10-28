import csv
import math
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

ECONOMIC_SOURCE = RESULTS / (
    f"34_weekly_economic_comparison_{PERIOD}.csv"
)

CONVERSION_SOURCE = RESULTS / (
    f"36_weekly_transaction_conversion_costs_{PERIOD}.csv"
)

OUTPUT = RESULTS / (
    f"37_weekly_execution_spending_{PERIOD}.csv"
)

EXPECTED_WEEKS = {
    (date(2026, 8, 24) + timedelta(weeks=i)).isoformat()
    for i in range(8)
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_weeks(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    require(len(rows) == 8, f"Expected eight rows: {path.name}")

    weeks = {}
    for row in rows:
        week = row["week_start"]
        require(week not in weeks, f"Duplicate week: {path.name}")
        weeks[week] = row

    require(
        set(weeks) == EXPECTED_WEEKS,
        f"Unexpected observation weeks: {path.name}",
    )

    return weeks


def number(row, field):
    value = float(row[field])
    require(math.isfinite(value), f"Nonfinite value: {field}")
    return value


def count(row, field):
    value = number(row, field)
    require(
        value >= 0 and value.is_integer(),
        f"Invalid count: {field}",
    )
    return int(value)


def nonnegative(row, field):
    value = number(row, field)
    require(value >= 0, f"Negative value: {field}")
    return value


def main():
    economic = read_weeks(ECONOMIC_SOURCE)
    conversions = read_weeks(CONVERSION_SOURCE)
    combined = []

    for week in sorted(EXPECTED_WEEKS):
        e = economic[week]
        c = conversions[week]

        expected_end = (
            date.fromisoformat(week) + timedelta(days=6)
        ).isoformat()

        require(
            e["week_end"] == c["week_end"] == expected_end,
            f"Week-end mismatch: {week}",
        )

        transactions = count(c, "transactions")

        require(
            transactions > 0
            and transactions == count(e, "transactions")
            and transactions == count(c, "distinct_transaction_hashes"),
            f"Transaction totals do not reconcile: {week}",
        )

        for field in (
            "missing_cost_records",
            "negative_cost_records",
            "nonfinite_cost_records",
        ):
            require(
                count(c, field) == 0,
                f"Invalid conversion-cost coverage: {week}, {field}",
            )

        conversion_cost = nonnegative(
            c, "recorded_conversion_cost_near"
        )
        receipt_cost = nonnegative(
            e, "recorded_receipt_execution_cost_near"
        )

        require(
            math.isclose(
                conversion_cost / transactions,
                nonnegative(
                    c,
                    "recorded_conversion_cost_per_transaction_near",
                ),
                rel_tol=1e-10,
                abs_tol=1e-12,
            ),
            f"Conversion-cost average mismatch: {week}",
        )

        receipt_count = count(e, "receipt_execution_outcomes")
        require(receipt_count > 0, f"No receipt outcomes: {week}")

        require(
            math.isclose(
                receipt_cost / receipt_count,
                nonnegative(
                    e, "average_recorded_cost_per_receipt_near"
                ),
                rel_tol=1e-10,
                abs_tol=1e-12,
            ),
            f"Receipt-cost average mismatch: {week}",
        )

        total = conversion_cost + receipt_cost
        require(total > 0, f"No recorded spending: {week}")

        combined.append({
            "week_start": week,
            "week_end": expected_end,
            "transactions": transactions,
            "receipt_execution_outcomes": receipt_count,
            "recorded_conversion_cost_near": conversion_cost,
            "recorded_receipt_execution_cost_near": receipt_cost,
            "combined_recorded_execution_spending_near": total,
            "conversion_share_of_recorded_spending_pct": (
                100 * conversion_cost / total
            ),
            "receipt_share_of_recorded_spending_pct": (
                100 * receipt_cost / total
            ),
        })

    require(
        sum(row["transactions"] for row in combined) == 44_284_794,
        "Full-period transaction total differs from the baseline.",
    )

    conversion_total = math.fsum(
        row["recorded_conversion_cost_near"] for row in combined
    )
    receipt_total = math.fsum(
        row["recorded_receipt_execution_cost_near"] for row in combined
    )
    spending_total = math.fsum(
        row["combined_recorded_execution_spending_near"]
        for row in combined
    )

    require(
        math.isclose(
            spending_total,
            conversion_total + receipt_total,
            rel_tol=1e-12,
            abs_tol=1e-8,
        ),
        "Combined spending does not reconcile.",
    )

    with OUTPUT.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(combined[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(combined)

    endpoint_change = 100 * (
        combined[-1]["combined_recorded_execution_spending_near"]
        / combined[0]["combined_recorded_execution_spending_near"]
        - 1
    )

    print("Validated eight complete weeks.")
    print(f"Transaction conversion: {conversion_total:,.4f} NEAR")
    print(f"Receipt execution: {receipt_total:,.4f} NEAR")
    print(f"Combined recorded spending: {spending_total:,.4f} NEAR")
    print(
        "Conversion share of recorded spending: "
        f"{100 * conversion_total / spending_total:.4f}%"
    )
    print(
        "First-to-final-week combined spending change: "
        f"{endpoint_change:+.2f}%"
    )
    print(f"Results saved: {OUTPUT}")
    print(
        "Calendar-period comparison: transaction conversion uses "
        "submission dates; receipt execution uses execution dates."
    )
    print(
        "This is not a matched transaction-chain fee calculation, "
        "permanent burning, protocol revenue or holder returns."
    )


if __name__ == "__main__":
    main()