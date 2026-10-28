import csv
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-07-06_to_2026-10-18"

SOURCE = RESULTS / (
    f"38_extended_weekly_signing_activity_{PERIOD}.csv"
)
OUTPUT = RESULTS / (
    f"39_extended_activity_comparison_{PERIOD}.csv"
)

COUNT_FIELDS = [
    "weekly_active_signing_accounts",
    "transactions",
    "signing_account_days",
    "accounts_active_one_day",
    "accounts_active_all_seven_days",
    "top_1_account_transactions",
    "top_10_accounts_transactions",
    "top_100_accounts_transactions",
]


def rounded(value, places=4):
    quantum = Decimal(1).scaleb(-places)
    return str(value.quantize(quantum, rounding=ROUND_HALF_UP))


def load_results():
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))

    if len(rows) != 15:
        raise ValueError(f"Expected 15 weeks; found {len(rows)}.")

    rows.sort(key=lambda row: row["week_start"])

    for index, row in enumerate(rows):
        expected_start = date(2026, 7, 6) + timedelta(weeks=index)
        expected_end = expected_start + timedelta(days=6)

        if (
            row["week_start"] != expected_start.isoformat()
            or row["week_end"] != expected_end.isoformat()
        ):
            raise ValueError("Weeks are missing, duplicated or misaligned.")

        for field in COUNT_FIELDS:
            row[field] = int(row[field])

            if row[field] < 0:
                raise ValueError(f"Negative count in {field}.")

        accounts = row["weekly_active_signing_accounts"]
        transactions = row["transactions"]
        account_days = row["signing_account_days"]

        if accounts <= 0 or transactions <= 0:
            raise ValueError("Account and transaction counts must be positive.")

        if not accounts <= account_days <= 7 * accounts:
            raise ValueError("Signing-account-days are outside valid bounds.")

        if account_days > transactions:
            raise ValueError("Account-days exceed transaction counts.")

        if (
            row["accounts_active_one_day"]
            + row["accounts_active_all_seven_days"]
            > accounts
        ):
            raise ValueError("Participation categories exceed account totals.")

        if not (
            row["top_1_account_transactions"]
            <= row["top_10_accounts_transactions"]
            <= row["top_100_accounts_transactions"]
            <= transactions
        ):
            raise ValueError("Concentration counts do not reconcile.")

        ratios = {
            "transactions_per_weekly_active_account": (
                Decimal(transactions) / accounts
            ),
            "average_active_days_per_account": (
                Decimal(account_days) / accounts
            ),
            "top_1_account_transaction_share_pct": (
                Decimal(100)
                * row["top_1_account_transactions"]
                / transactions
            ),
            "top_10_accounts_transaction_share_pct": (
                Decimal(100)
                * row["top_10_accounts_transactions"]
                / transactions
            ),
            "top_100_accounts_transaction_share_pct": (
                Decimal(100)
                * row["top_100_accounts_transactions"]
                / transactions
            ),
        }

        for field, expected in ratios.items():
            actual = Decimal(row[field])

            if not actual.is_finite() or actual != Decimal(
                rounded(expected, 2)
            ):
                raise ValueError(f"Reported ratio differs for {field}.")

        previous_change = row["weekly_active_accounts_change_pct"]

        if index == 0:
            if previous_change.strip().lower() not in ("", "null"):
                raise ValueError("First-week change should be missing.")
        else:
            previous_accounts = rows[index - 1][
                "weekly_active_signing_accounts"
            ]
            expected_change = (
                Decimal(100)
                * (accounts - previous_accounts)
                / previous_accounts
            )

            if Decimal(previous_change) != Decimal(
                rounded(expected_change, 2)
            ):
                raise ValueError("Weekly account change does not reconcile.")

    return rows


def summarise(rows):
    weeks = len(rows)

    transactions = sum(row["transactions"] for row in rows)
    account_weeks = sum(
        row["weekly_active_signing_accounts"] for row in rows
    )
    account_days = sum(row["signing_account_days"] for row in rows)
    top_ten_transactions = sum(
        row["top_10_accounts_transactions"] for row in rows
    )

    return {
        "average_weekly_transactions": (
            Decimal(transactions) / weeks
        ),
        "average_weekly_active_signing_accounts": (
            Decimal(account_weeks) / weeks
        ),
        "active_days_per_active_account_week": (
            Decimal(account_days) / account_weeks
        ),
        "weekly_top_10_transaction_share_pct": (
            Decimal(100) * top_ten_transactions / transactions
        ),
    }


def main():
    rows = load_results()

    first_period = rows[:4]
    final_period = rows[-4:]

    first_summary = summarise(first_period)
    final_summary = summarise(final_period)

    definitions = {
        "average_weekly_transactions": (
            "transactions per week",
            "Total transactions divided by four weeks.",
        ),
        "average_weekly_active_signing_accounts": (
            "signing accounts per week",
            "Sum of weekly distinct signing-account counts divided "
            "by four; not distinct accounts across the four-week period.",
        ),
        "active_days_per_active_account_week": (
            "days per active account-week",
            "Signing-account-days divided by the sum of weekly active "
            "signing accounts; weighted across account-weeks.",
        ),
        "weekly_top_10_transaction_share_pct": (
            "percent",
            "Transactions from each week's top ten divided by all "
            "transactions across the four weeks; membership varies weekly.",
        ),
    }

    output_rows = []

    for metric, first_value in first_summary.items():
        final_value = final_summary[metric]
        difference = final_value - first_value
        relative_change = Decimal(100) * difference / first_value
        unit, definition = definitions[metric]

        output_rows.append({
            "metric": metric,
            "unit": unit,
            "first_period_start": first_period[0]["week_start"],
            "first_period_end": first_period[-1]["week_end"],
            "final_period_start": final_period[0]["week_start"],
            "final_period_end": final_period[-1]["week_end"],
            "weeks_per_period": 4,
            "first_period_value": rounded(first_value),
            "final_period_value": rounded(final_value),
            "absolute_change": rounded(difference),
            "absolute_change_unit": (
                "percentage points" if unit == "percent" else unit
            ),
            "relative_change_pct": rounded(relative_change),
            "definition": definition,
        })

    temporary = OUTPUT.with_suffix(".csv.tmp")

    with temporary.open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(output_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    temporary.replace(OUTPUT)

    print("Validated 15 complete weeks.")
    print(
        "First comparison period: "
        f"{first_period[0]['week_start']} to "
        f"{first_period[-1]['week_end']}"
    )
    print(
        "Final comparison period: "
        f"{final_period[0]['week_start']} to "
        f"{final_period[-1]['week_end']}"
    )

    for row in output_rows:
        print(
            f"{row['metric']}: "
            f"{row['first_period_value']} -> "
            f"{row['final_period_value']} | "
            f"relative change {row['relative_change_pct']}%"
        )

    print(f"\nResults saved: {OUTPUT}")
    print(
        "Weekly account counts are not four-week unique accounts. "
        "Top-ten membership is selected separately each week."
    )
    print(
        "The final period includes the account spike. This comparison "
        "does not adjust for deletion activity or establish user retention, "
        "causes or long-term adoption."
    )


if __name__ == "__main__":
    main()