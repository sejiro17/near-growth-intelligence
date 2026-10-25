import csv
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT / "results"
    / "03_daily_transaction_checks_2026-07-01_to_2026-10-24.csv"
)
OUTPUT = (
    ROOT / "results"
    / "09_weekly_activity_baseline_2026-08-24_to_2026-10-18.csv"
)

START = date(2026, 8, 24)
END = date(2026, 10, 18)

CHECK_FIELDS = (
    "missing_transaction_hashes",
    "missing_signer_accounts",
    "missing_receiver_accounts",
    "missing_timestamps",
    "timestamp_date_mismatches",
)


def main():
    with SOURCE.open(newline="", encoding="utf-8") as source:
        rows = list(csv.DictReader(source))

    selected = {}
    for row in rows:
        day = date.fromisoformat(row["block_date"])
        if not START <= day <= END:
            continue

        if day in selected:
            raise ValueError(f"Duplicate date: {day}")

        if any(int(row[field]) != 0 for field in CHECK_FIELDS):
            raise ValueError(f"Unresolved validation check: {day}")

        transactions = int(row["transaction_rows"])
        accounts = int(row["active_signing_accounts"])

        if transactions != int(row["distinct_transaction_hashes"]):
            raise ValueError(f"Transaction counts do not reconcile: {day}")

        if int(row["observed_hours"]) != 24:
            raise ValueError(f"Hourly coverage check failed: {day}")

        if not 0 < accounts <= transactions:
            raise ValueError(f"Invalid signing-account count: {day}")

        selected[day] = {
            "transactions": transactions,
            "accounts": accounts,
        }

    expected = {
        START + timedelta(days=offset)
        for offset in range((END - START).days + 1)
    }
    if set(selected) != expected:
        raise ValueError("Missing dates in the primary analysis period.")

    weeks = defaultdict(list)
    for day, values in sorted(selected.items()):
        week_start = day - timedelta(days=day.weekday())
        weeks[week_start].append(values)

    if len(weeks) != 8:
        raise ValueError("Expected eight complete weeks.")

    output_rows = []
    previous_transactions = None
    previous_account_days = None

    with localcontext() as context:
        context.prec = 30

        for week_start, days in sorted(weeks.items()):
            if len(days) != 7:
                raise ValueError(f"Incomplete week: {week_start}")

            transactions = sum(day["transactions"] for day in days)
            account_days = sum(day["accounts"] for day in days)

            transaction_change = ""
            account_change = ""

            if previous_transactions is not None:
                transaction_change = format(
                    (
                        Decimal(transactions)
                        / Decimal(previous_transactions) - 1
                    ) * 100,
                    ".2f",
                )
                account_change = format(
                    (
                        Decimal(account_days)
                        / Decimal(previous_account_days) - 1
                    ) * 100,
                    ".2f",
                )

            output_rows.append({
                "week_start": week_start.isoformat(),
                "week_end": (
                    week_start + timedelta(days=6)
                ).isoformat(),
                "observed_days": len(days),
                "transactions": transactions,
                "average_daily_transactions": format(
                    Decimal(transactions) / 7, ".2f"
                ),
                "signing_account_days": account_days,
                "average_daily_active_signing_accounts": format(
                    Decimal(account_days) / 7, ".2f"
                ),
                "transaction_change_pct": transaction_change,
                "average_daily_active_accounts_change_pct":
                    account_change,
            })

            previous_transactions = transactions
            previous_account_days = account_days

    with OUTPUT.open("w", newline="", encoding="utf-8") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=list(output_rows[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("Validated 56 dates across eight complete weeks.")
    print(f"Results saved: {OUTPUT}")
    print(
        "Signing-account-days count an account once per active day; "
        "they are not weekly distinct accounts."
    )


if __name__ == "__main__":
    main()