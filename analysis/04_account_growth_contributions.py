import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

SOURCE = RESULTS / (
    f"18_weekly_leading_signing_accounts_{PERIOD}.csv"
)
BASELINE = RESULTS / (
    f"21_fixed_account_growth_{PERIOD}.csv"
)
OUTPUT = RESULTS / (
    f"22_account_growth_contributions_{PERIOD}.csv"
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


def main():
    source = read_csv(SOURCE)
    baseline = read_csv(BASELINE)

    baseline_by_week = {}
    for row in baseline:
        week = row["week_start"]
        if week in baseline_by_week:
            raise ValueError(f"Duplicate baseline week: {week}")
        baseline_by_week[week] = row

    if len(baseline_by_week) != 8:
        raise ValueError("Expected eight baseline weeks.")

    weeks = sorted(baseline_by_week)
    first_week, final_week = weeks[0], weeks[-1]

    if (
        first_week != "2026-08-24"
        or final_week != "2026-10-12"
    ):
        raise ValueError("Unexpected comparison dates.")

    histories = {}
    for row in source:
        week = row["week_start"]
        account = row["signer_account_id"]

        if week not in baseline_by_week:
            raise ValueError(f"Unexpected source week: {week}")

        history = histories.setdefault(account, {})
        if week in history:
            raise ValueError(f"Duplicate account-week: {account}, {week}")

        history[week] = row

        if int(row["weekly_transactions"]) != int(
            baseline_by_week[week]["network_transactions"]
        ):
            raise ValueError(f"Network total mismatch: {week}")

    for account, history in histories.items():
        if sorted(history) != weeks:
            raise ValueError(f"Incomplete account history: {account}")

    fixed_accounts = {
        account
        for account, history in histories.items()
        if history[first_week]["in_weekly_top_10"].lower() == "true"
    }

    if len(fixed_accounts) != 10:
        raise ValueError("Expected ten first-week leading accounts.")

    for week in weeks:
        fixed_total = sum(
            int(histories[account][week]["transactions"])
            for account in fixed_accounts
        )
        if fixed_total != int(
            baseline_by_week[week]["fixed_group_transactions"]
        ):
            raise ValueError(f"Fixed group mismatch: {week}")

    first_total = int(
        baseline_by_week[first_week]["network_transactions"]
    )
    final_total = int(
        baseline_by_week[final_week]["network_transactions"]
    )
    outside_change = (
        int(
            baseline_by_week[final_week][
                "outside_fixed_group_transactions"
            ]
        )
        - int(
            baseline_by_week[first_week][
                "outside_fixed_group_transactions"
            ]
        )
    )

    output = []

    def make_row(account, group, first_count, final_count):
        difference = final_count - first_count

        return {
            "first_week_start": first_week,
            "final_week_start": final_week,
            "signer_account_id": account,
            "comparison_group": group,
            "first_week_transactions": first_count,
            "final_week_transactions": final_count,
            "transaction_change": difference,
            "transaction_change_pct": percentage(
                difference, first_count
            ),
            "first_week_network_share_pct": percentage(
                first_count, first_total
            ),
            "final_week_network_share_pct": percentage(
                final_count, final_total
            ),
            "contribution_to_outside_group_net_change_pct": (
                ""
                if group == "FIRST_WEEK_TOP_10"
                else percentage(difference, outside_change)
            ),
        }

    for account, history in histories.items():
        group = (
            "FIRST_WEEK_TOP_10"
            if account in fixed_accounts
            else "OTHER_TRACKED_ACCOUNT"
        )
        output.append(
            make_row(
                account,
                group,
                int(history[first_week]["transactions"]),
                int(history[final_week]["transactions"]),
            )
        )

    tracked_first = sum(
        int(history[first_week]["transactions"])
        for history in histories.values()
    )
    tracked_final = sum(
        int(history[final_week]["transactions"])
        for history in histories.values()
    )

    remaining_first = first_total - tracked_first
    remaining_final = final_total - tracked_final

    if min(remaining_first, remaining_final) < 0:
        raise ValueError("Tracked counts exceed network totals.")

    output.append(
        make_row(
            "",
            "ALL_UNTRACKED_ACCOUNTS",
            remaining_first,
            remaining_final,
        )
    )

    if sum(row["first_week_transactions"] for row in output) != first_total:
        raise ValueError("First-week decomposition does not reconcile.")

    if sum(row["final_week_transactions"] for row in output) != final_total:
        raise ValueError("Final-week decomposition does not reconcile.")

    outside_rows = [
        row
        for row in output
        if row["comparison_group"] != "FIRST_WEEK_TOP_10"
    ]

    if sum(row["transaction_change"] for row in outside_rows) != outside_change:
        raise ValueError("Outside-group change does not reconcile.")

    output.sort(
        key=lambda row: (
            row["comparison_group"],
            -row["transaction_change"],
            row["signer_account_id"],
        )
    )

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(output[0]),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(output)

    print(f"Validated {len(histories)} account histories.")
    print("First-week, final-week and outside-group changes reconcile.")
    print(f"Results saved: {OUTPUT}")
    print(
        "The untracked remainder combines multiple accounts. "
        "Contributions describe arithmetic changes, not their causes."
    )


if __name__ == "__main__":
    main()