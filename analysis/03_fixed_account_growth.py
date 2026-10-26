import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

LEADERS_FILE = RESULTS / (
    f"18_weekly_leading_signing_accounts_{PERIOD}.csv"
)
WEEKLY_FILE = RESULTS / (
    f"10_weekly_signing_activity_{PERIOD}.csv"
)
OUTPUT_FILE = RESULTS / (
    f"21_fixed_account_growth_{PERIOD}.csv"
)


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    if not rows:
        raise ValueError(f"{path.name} is empty.")

    return rows


def percentage(numerator, denominator):
    if denominator == 0:
        return ""

    value = Decimal(numerator) * 100 / Decimal(denominator)
    return str(
        value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


def change_from_first(value, first_value):
    return percentage(value - first_value, first_value)


def main():
    leaders = read_csv(LEADERS_FILE)
    weekly_rows = read_csv(WEEKLY_FILE)

    expected_weeks = [
        (date(2026, 8, 24) + timedelta(weeks=i)).isoformat()
        for i in range(8)
    ]

    weekly = {}
    for row in weekly_rows:
        week = row["week_start"]
        if week in weekly:
            raise ValueError(f"Duplicate weekly summary: {week}")
        weekly[week] = row

    if sorted(weekly) != expected_weeks:
        raise ValueError("Weekly summaries do not cover the expected weeks.")

    by_week = {week: {} for week in expected_weeks}

    for row in leaders:
        week = row["week_start"]
        account = row["signer_account_id"]

        if week not in by_week:
            raise ValueError(f"Unexpected week: {week}")
        if account in by_week[week]:
            raise ValueError(f"Duplicate account-week: {account}, {week}")

        by_week[week][account] = row

    accounts = set(by_week[expected_weeks[0]])

    if not accounts:
        raise ValueError("No account histories found.")

    for week in expected_weeks:
        if set(by_week[week]) != accounts:
            raise ValueError(f"Incomplete account grid: {week}")

    first_week = expected_weeks[0]
    fixed_accounts = {
        account
        for account, row in by_week[first_week].items()
        if row["in_weekly_top_10"].strip().lower() == "true"
    }

    if len(fixed_accounts) != 10:
        raise ValueError("The first-week group must contain ten accounts.")

    first_ranks = {
        int(by_week[first_week][account]["activity_rank"])
        for account in fixed_accounts
    }

    if first_ranks != set(range(1, 11)):
        raise ValueError("First-week top-ten ranks are inconsistent.")

    for account in accounts:
        history = [
            by_week[week][account]
            for week in expected_weeks
        ]
        full_period_values = {
            int(row["full_period_transactions"])
            for row in history
        }

        if len(full_period_values) != 1:
            raise ValueError(f"Inconsistent history total: {account}")

        if sum(int(row["transactions"]) for row in history) != next(
            iter(full_period_values)
        ):
            raise ValueError(f"History does not reconcile: {account}")

    output = []

    for week in expected_weeks:
        rows = list(by_week[week].values())
        summary = weekly[week]
        total = int(summary["transactions"])

        if {
            int(row["weekly_transactions"]) for row in rows
        } != {total}:
            raise ValueError(f"Network totals do not reconcile: {week}")

        ranked_top_ten = [
            row
            for row in rows
            if row["in_weekly_top_10"].strip().lower() == "true"
        ]
        current_top_ten_total = sum(
            int(row["transactions"])
            for row in ranked_top_ten
        )

        if (
            len(ranked_top_ten) != 10
            or current_top_ten_total
            != int(summary["top_10_accounts_transactions"])
        ):
            raise ValueError(f"Weekly top ten do not reconcile: {week}")

        fixed_total = sum(
            int(by_week[week][account]["transactions"])
            for account in fixed_accounts
        )
        outside_total = total - fixed_total

        if outside_total < 0:
            raise ValueError(f"Negative remaining transactions: {week}")

        output.append({
            "week_start": week,
            "week_end": (
                date.fromisoformat(week) + timedelta(days=6)
            ).isoformat(),
            "fixed_group_selection_week": first_week,
            "fixed_group_accounts": len(fixed_accounts),
            "fixed_group_active_accounts": sum(
                int(by_week[week][account]["transactions"]) > 0
                for account in fixed_accounts
            ),
            "network_transactions": total,
            "fixed_group_transactions": fixed_total,
            "outside_fixed_group_transactions": outside_total,
            "fixed_group_transaction_share_pct": percentage(
                fixed_total, total
            ),
        })

    first = output[0]

    for row in output:
        for field in (
            "network_transactions",
            "fixed_group_transactions",
            "outside_fixed_group_transactions",
        ):
            row[f"{field}_change_from_first_pct"] = change_from_first(
                row[field], first[field]
            )

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(output[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output)

    print("Validated eight weeks and the fixed first-week top ten.")
    print("Fixed group:")
    for account in sorted(fixed_accounts):
        print(f"  {account}")
    print(f"Results saved: {OUTPUT_FILE}")
    print(
        "Remaining transactions are not a measure of independent users "
        "or a counterfactual network without these accounts."
    )


if __name__ == "__main__":
    main()