import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

OUTPUT = RESULTS / f"35_account_profiles_{PERIOD}.json"

PROFILES = {
    "intents.near": {
        "service": "NEAR Intents",
        "evidence_status": "Documented contract role",
        "role": "Verifier contract; metrics here describe transactions it signed.",
        "source": "https://github.com/near/intents",
    },
    "omni-relayer.bridge.near": {
        "service": "Omni Bridge",
        "evidence_status": "Documented relayer role",
        "role": (
            "Documented as finalizing bridge transfers on NEAR. "
            "Operator and full historical coverage remain unverified."
        ),
        "source": "https://doc.aurora.dev/blog/omnibridge-tutorial/",
    },
    "sweat-relayer.near": {
        "service": None,
        "evidence_status": "Pending verification",
        "role": "Observed signing account; service attribution unverified.",
        "source": None,
    },
    "meteor-relayer.near": {
        "service": None,
        "evidence_status": "Pending verification",
        "role": "Observed signing account; service attribution unverified.",
        "source": None,
    },
    "closemeat6237.near": {
        "service": None,
        "evidence_status": "Pending verification",
        "role": "Observed signing account; ownership and role unverified.",
        "source": None,
    },
}

WEEKS = [
    (date(2026, 8, 24) + timedelta(weeks=i)).isoformat()
    for i in range(8)
]


def read_csv(number, name):
    path = RESULTS / f"{number}_{name}_{PERIOD}.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(row, field):
    value = int(row[field])
    require(value >= 0, f"Negative {field}: {row}")
    return value


def consistent(rows, field):
    values = {integer(row, field) for row in rows}
    require(len(values) == 1, f"Inconsistent {field}")
    return values.pop()


def group_rows(rows):
    grouped = defaultdict(list)
    for row in rows:
        key = (row["signer_account_id"], row["week_start"])
        grouped[key].append(row)
    return grouped


def main():
    baseline = read_csv("18", "weekly_leading_signing_accounts")
    destinations = read_csv("19", "leading_account_activity")
    actions = read_csv("20", "leading_account_actions")

    baseline_groups = group_rows(baseline)
    destination_groups = group_rows(destinations)
    action_groups = group_rows(actions)

    expected = {
        (account, week)
        for account in PROFILES
        for week in WEEKS
    }

    require(
        set(destination_groups) == expected,
        "Destination coverage differs from the expected 40 account-weeks.",
    )
    require(
        set(action_groups) == expected,
        "Action coverage differs from the expected 40 account-weeks.",
    )

    profiles = []

    for account, attribution in PROFILES.items():
        weekly = []

        for week in WEEKS:
            key = (account, week)
            base_rows = baseline_groups.get(key, [])
            require(len(base_rows) == 1, f"Expected one baseline row: {key}")
            base = base_rows[0]
            total = integer(base, "transactions")

            receiver_rows = destination_groups[key]
            action_rows = action_groups[key]

            require(
                consistent(receiver_rows, "account_week_transactions") == total,
                f"Destination total does not match baseline: {key}",
            )
            require(
                consistent(action_rows, "account_week_transactions") == total,
                f"Action total does not match baseline: {key}",
            )
            require(
                consistent(receiver_rows, "account_active_days")
                == integer(base, "active_days"),
                f"Active-day mismatch: {key}",
            )

            receivers = []
            receiver_ids = set()
            ranks = set()

            for row in receiver_rows:
                receiver = row["receiver_account_id"]
                rank = integer(row, "receiver_rank")
                count = integer(row, "transactions")

                require(receiver not in receiver_ids, f"Duplicate receiver: {key}")
                require(rank not in ranks, f"Duplicate receiver rank: {key}")
                require(1 <= rank <= 20, f"Invalid receiver rank: {key}")
                require(count <= total, f"Receiver count exceeds total: {key}")

                receiver_ids.add(receiver)
                ranks.add(rank)
                receivers.append({
                    "receiver_account_id": receiver,
                    "rank": rank,
                    "transactions": count,
                    "active_days": integer(row, "receiver_active_days"),
                })

            top_total = consistent(receiver_rows, "top_20_receiver_transactions")
            outside = consistent(
                receiver_rows, "outside_top_20_receiver_transactions"
            )

            require(
                sum(row["transactions"] for row in receivers) == top_total,
                f"Top receiver rows do not reconcile: {key}",
            )
            require(
                top_total + outside == total,
                f"Receiver coverage does not reconcile: {key}",
            )

            matched = consistent(action_rows, "transactions_with_action_records")
            missing = consistent(action_rows, "transactions_without_action_records")
            require(matched + missing == total, f"Action coverage mismatch: {key}")

            categories = []
            category_keys = set()

            for row in action_rows:
                category = (row["action_kind"], row["method_name"])
                require(
                    category not in category_keys,
                    f"Duplicate action category: {key}",
                )
                category_keys.add(category)

                count = integer(row, "transactions")
                action_count = integer(row, "action_rows")
                require(count <= matched, f"Action transactions exceed matches: {key}")
                require(action_count >= count, f"Too few action rows: {key}")

                categories.append({
                    "action_kind": row["action_kind"],
                    "method_name": row["method_name"] or None,
                    "transactions": count,
                    "action_rows": action_count,
                    "action_rows_without_index": integer(
                        row, "action_rows_without_index"
                    ),
                    "function_call_rows_without_method": integer(
                        row, "function_call_rows_without_method"
                    ),
                })

            weekly.append({
                "week_start": week,
                "week_end": base["week_end"],
                "transactions": total,
                "active_days": integer(base, "active_days"),
                "network_transactions": integer(base, "weekly_transactions"),
                "network_transaction_share_pct": round(
                    100 * total / integer(base, "weekly_transactions"), 4
                ),
                "distinct_receivers": consistent(receiver_rows, "distinct_receivers"),
                "self_directed_transactions": consistent(
                    receiver_rows, "self_directed_transactions"
                ),
                "missing_or_empty_receiver_transactions": consistent(
                    receiver_rows, "missing_or_empty_receiver_transactions"
                ),
                "outside_top_20_receiver_transactions": outside,
                "transactions_with_action_records": matched,
                "transactions_without_action_records": missing,
                "top_receivers": sorted(receivers, key=lambda row: row["rank"]),
                "action_categories": sorted(
                    categories,
                    key=lambda row: (
                        -row["transactions"],
                        row["action_kind"],
                        row["method_name"] or "",
                    ),
                ),
            })

        period_total = sum(row["transactions"] for row in weekly)
        reported_totals = {
            integer(baseline_groups[(account, week)][0], "full_period_transactions")
            for week in WEEKS
        }
        require(
            reported_totals == {period_total},
            f"Full-period total does not reconcile: {account}",
        )

        profiles.append({
            "account_id": account,
            **attribution,
            "full_period_transactions": period_total,
            "weekly": weekly,
        })

    document = {
        "period_start": WEEKS[0],
        "period_end": "2026-10-18",
        "attribution_review_date": "2026-10-27",
        "source_files": [
            f"18_weekly_leading_signing_accounts_{PERIOD}.csv",
            f"19_leading_account_activity_{PERIOD}.csv",
            f"20_leading_account_actions_{PERIOD}.csv",
        ],
        "measurement_boundaries": [
            "Metrics describe transactions signed by each selected account.",
            "Signing identifiers are not application user counts.",
            "Profiles do not establish complete application coverage.",
            "Receiver breakdowns contain weekly top 20 destinations.",
            "Action-category transaction counts can overlap and must not be summed.",
            "Current attribution evidence does not prove historical ownership.",
        ],
        "profiles": profiles,
    }

    OUTPUT.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("Validated five profiles across 40 account-weeks.")
    print("Weekly totals, destination coverage and action coverage reconcile.")
    for profile in profiles:
        print(
            f"{profile['account_id']}: "
            f"{profile['full_period_transactions']:,} transactions"
        )
    print(f"Results saved: {OUTPUT}")


if __name__ == "__main__":
    main()