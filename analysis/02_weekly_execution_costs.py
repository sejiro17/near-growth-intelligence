import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

ACTIVITY = RESULTS / (
    "09_weekly_activity_baseline_2026-08-24_to_2026-10-18.csv"
)
ACCOUNTS = RESULTS / (
    "10_weekly_signing_activity_2026-08-24_to_2026-10-18.csv"
)
COSTS = RESULTS / (
    "13_weekly_execution_costs_2026-08-24_to_2026-10-18.csv"
)
OUTPUT = RESULTS / (
    "14_weekly_growth_and_costs_2026-08-24_to_2026-10-18.csv"
)

EXPECTED_WEEKS = [
    date(2026, 8, 24) + timedelta(weeks=i)
    for i in range(8)
]


def load_weeks(path):
    with path.open(newline="", encoding="utf-8-sig") as source:
        rows = list(csv.DictReader(source))

    indexed = {}

    for row in rows:
        week = date.fromisoformat(row["week_start"])

        if week in indexed:
            raise ValueError(f"{path.name}: duplicate week {week}")

        expected_end = week + timedelta(days=6)
        if date.fromisoformat(row["week_end"]) != expected_end:
            raise ValueError(f"{path.name}: incorrect week end")

        indexed[week] = row

    if set(indexed) != set(EXPECTED_WEEKS):
        raise ValueError(f"{path.name}: unexpected or missing weeks")

    return indexed


def number(value):
    result = Decimal(value)

    if not result.is_finite():
        raise ValueError(f"Nonfinite value: {value}")

    return result


def rounded(value):
    return format(
        value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        ".2f",
    )


def main():
    activity = load_weeks(ACTIVITY)
    accounts = load_weeks(ACCOUNTS)
    costs = load_weeks(COSTS)

    first = EXPECTED_WEEKS[0]
    base_transactions = number(activity[first]["transactions"])
    base_accounts = number(
        accounts[first]["weekly_active_signing_accounts"]
    )
    base_cost = number(costs[first]["recorded_execution_cost_near"])

    if min(base_transactions, base_accounts, base_cost) <= 0:
        raise ValueError("First-week index denominators must be positive")

    output_rows = []
    previous_cost = None

    for week in EXPECTED_WEEKS:
        a = activity[week]
        s = accounts[week]
        c = costs[week]

        if int(a["observed_days"]) != 7 or int(c["observed_days"]) != 7:
            raise ValueError(f"{week}: incomplete week")

        for field in ("transactions", "signing_account_days"):
            if int(a[field]) != int(s[field]):
                raise ValueError(f"{week}: inconsistent {field}")

        for field in (
            "other_or_missing_statuses",
            "invalid_gas_values",
            "invalid_token_cost_values",
        ):
            if int(c[field]) != 0:
                raise ValueError(f"{week}: nonzero {field}")

        outcome_count = int(c["receipt_execution_outcomes"])
        status_total = sum(
            int(c[field])
            for field in (
                "failed_receipt_outcomes",
                "success_value_outcomes",
                "success_receipt_id_outcomes",
            )
        )

        if outcome_count <= 0 or outcome_count != status_total:
            raise ValueError(f"{week}: inconsistent outcome counts")

        transactions = number(a["transactions"])
        active_accounts = number(s["weekly_active_signing_accounts"])
        cost = number(c["recorded_execution_cost_near"])
        failed_cost = number(c["failed_receipt_cost_near"])

        if min(transactions, active_accounts, cost) <= 0:
            raise ValueError(f"{week}: nonpositive activity or cost")

        if not Decimal(0) <= failed_cost <= cost:
            raise ValueError(f"{week}: invalid failed-receipt cost")

        merged = dict(a)

        for source in (s, c):
            for field, value in source.items():
                if field not in merged:
                    merged[field] = value

        merged["transactions_index_first_week_100"] = rounded(
            100 * transactions / base_transactions
        )
        merged["weekly_active_accounts_index_first_week_100"] = rounded(
            100 * active_accounts / base_accounts
        )
        merged["recorded_cost_index_first_week_100"] = rounded(
            100 * cost / base_cost
        )
        merged["recorded_cost_change_pct"] = (
            ""
            if previous_cost is None
            else rounded(100 * (cost / previous_cost - 1))
        )

        output_rows.append(merged)
        previous_cost = cost

    with OUTPUT.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=list(output_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("Validated and combined eight complete weeks.")
    print(f"Results saved: {OUTPUT}")
    print(
        "Costs are grouped by receipt execution date; "
        "transactions are grouped by submission date."
    )
    print(
        "The indices compare weekly trends. "
        "They do not measure transaction-level fees or protocol revenue."
    )


if __name__ == "__main__":
    main()