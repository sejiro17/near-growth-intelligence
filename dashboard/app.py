import json
from collections import Counter
from math import isclose, isfinite
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

st.set_page_config(
    page_title="NEAR Growth Intelligence",
    page_icon="📊",
    layout="wide",
)

COLORS = ["#00A884", "#5470F5", "#F3A536", "#D65D75"]

STATUS_LABELS = {
    "FAILURE": "Failure",
    "SUCCESS_VALUE": "Success value",
    "SUCCESS_RECEIPT_ID": "Success receipt ID",
}

STATUS_COLORS = {
    "Failure": "#D65D75",
    "Success value": "#00A884",
    "Success receipt ID": "#5470F5",
}

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = COLORS


def load_csv(filename, date_columns):
    frame = pd.read_csv(RESULTS / filename)

    for column in date_columns:
        frame[column] = pd.to_datetime(frame[column])

    if frame.empty:
        raise ValueError(f"{filename} is empty.")

    return frame


try:
    weekly = load_csv(
        f"14_weekly_growth_and_costs_{PERIOD}.csv",
        ["week_start", "week_end"],
    ).sort_values("week_start")

    returns = load_csv(
        f"11_weekly_account_returns_{PERIOD}.csv",
        ["cohort_week", "followup_week"],
    )

    receivers = load_csv(
        f"12_weekly_receiver_activity_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    spike = load_csv(
        "15_spike_cohort_receivers_2026-09-28_to_2026-10-11.csv",
        ["cohort_week", "followup_week"],
    )

    fixed = load_csv(
        f"21_fixed_account_growth_{PERIOD}.csv",
        ["week_start", "week_end", "fixed_group_selection_week"],
    ).sort_values("week_start")

    contributions = load_csv(
        f"22_account_growth_contributions_{PERIOD}.csv",
        ["first_week_start", "final_week_start"],
    )

    leading = load_csv(
        f"18_weekly_leading_signing_accounts_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    leading_actions = load_csv(
        f"20_leading_account_actions_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    growth_actions = load_csv(
        f"23_growth_account_activity_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    outcomes = load_csv(
        f"24_growth_account_outcomes_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    account_costs = load_csv(
        f"27_growth_account_execution_costs_{PERIOD}.csv",
        ["week_start", "week_end"],
    )

    economics = load_csv(
        f"34_weekly_economic_comparison_{PERIOD}.csv",
        [
            "week_start",
            "week_end",
            "opening_supply_baseline_date",
        ],
    ).sort_values("week_start").reset_index(drop=True)

    if (
        len(economics) != 8
        or economics["week_start"].duplicated().any()
        or not economics["week_start"].equals(
            weekly["week_start"].reset_index(drop=True)
        )
        or not economics["week_end"].equals(
            weekly["week_end"].reset_index(drop=True)
        )
    ):
        raise ValueError(
            "Economic results do not cover the eight weekly periods."
        )

    economic_fields = [
        "transactions",
        "weekly_active_signing_accounts",
        "receipt_execution_outcomes",
        "recorded_receipt_execution_cost_near",
        "average_recorded_cost_per_receipt_near",
        "opening_observed_supply_near",
        "closing_observed_supply_near",
        "net_observed_supply_change_near",
        "validator_update_net_balance_change_near",
        "observed_positive_supply_movements_near",
        "observed_supply_decrease_magnitude_near",
        "net_supply_change_minus_validator_change_near",
        "positive_supply_movements_minus_validator_change_near",
    ]

    for field in economic_fields:
        economics[field] = pd.to_numeric(
            economics[field],
            errors="raise",
        )

        if not economics[field].map(isfinite).all():
            raise ValueError(
                f"Nonfinite economic values in {field}."
            )

    economic_pairs = {
        "transactions": "transactions",
        "weekly_active_signing_accounts": (
            "weekly_active_signing_accounts"
        ),
        "receipt_execution_outcomes": "receipt_execution_outcomes",
        "recorded_receipt_execution_cost_near": (
            "recorded_execution_cost_near"
        ),
    }

    for economic_field, weekly_field in economic_pairs.items():
        if not all(
            isclose(
                float(a),
                float(b),
                rel_tol=1e-12,
                abs_tol=1e-5,
            )
            for a, b in zip(
                economics[economic_field],
                weekly[weekly_field],
            )
        ):
            raise ValueError(
                f"Economic results differ for {economic_field}."
            )

    previous_close = None

    for row in economics.to_dict("records"):
        if (
            row["opening_supply_baseline_date"]
            != row["week_start"] - pd.Timedelta(days=1)
        ):
            raise ValueError(
                "Unexpected opening supply baseline date."
            )

        if (
            min(
                row["opening_observed_supply_near"],
                row["closing_observed_supply_near"],
            ) <= 0
            or row["receipt_execution_outcomes"] <= 0
        ):
            raise ValueError(
                "Supply and receipt counts must be positive."
            )

        checks = [
            (
                row["closing_observed_supply_near"]
                - row["opening_observed_supply_near"],
                row["net_observed_supply_change_near"],
            ),
            (
                row["observed_positive_supply_movements_near"]
                - row["observed_supply_decrease_magnitude_near"],
                row["net_observed_supply_change_near"],
            ),
            (
                row["net_observed_supply_change_near"]
                - row["validator_update_net_balance_change_near"],
                row["net_supply_change_minus_validator_change_near"],
            ),
            (
                row["observed_positive_supply_movements_near"]
                - row["validator_update_net_balance_change_near"],
                row[
                    "positive_supply_movements_minus_validator_change_near"
                ],
            ),
            (
                row["recorded_receipt_execution_cost_near"]
                / row["receipt_execution_outcomes"],
                row["average_recorded_cost_per_receipt_near"],
            ),
        ]

        if previous_close is not None:
            checks.append(
                (
                    previous_close,
                    row["opening_observed_supply_near"],
                )
            )

        if not all(
            isclose(
                float(a),
                float(b),
                rel_tol=1e-12,
                abs_tol=1e-5,
            )
            for a, b in checks
        ):
            raise ValueError(
                "Economic comparison arithmetic does not reconcile."
            )

        previous_close = row["closing_observed_supply_near"]

    diagnostic_path = RESULTS / (
        f"26_growth_account_failure_details_{PERIOD}.json"
    )

    with diagnostic_path.open(encoding="utf-8") as handle:
        diagnostics = json.load(handle)

    if (
        fixed["week_start"].duplicated().any()
        or not fixed["week_start"].reset_index(drop=True).equals(
            weekly["week_start"].reset_index(drop=True)
        )
    ):
        raise ValueError(
            "Fixed-account results do not cover the weekly period."
        )

    if (
        not (
            fixed["network_transactions"].to_numpy()
            == weekly["transactions"].to_numpy()
        ).all()
        or not (
            fixed["fixed_group_transactions"]
            + fixed["outside_fixed_group_transactions"]
            == fixed["network_transactions"]
        ).all()
    ):
        raise ValueError(
            "Fixed-account totals do not reconcile."
        )

    if leading.duplicated(
        ["week_start", "signer_account_id"]
    ).any():
        raise ValueError(
            "Duplicate leading-account records."
        )

    if not leading.groupby(
        "signer_account_id"
    ).size().eq(len(weekly)).all():
        raise ValueError(
            "Incomplete tracked-account weekly series."
        )

    if (
        contributions["first_week_transactions"].sum()
        != weekly.iloc[0]["transactions"]
        or contributions["final_week_transactions"].sum()
        != weekly.iloc[-1]["transactions"]
        or not (
            contributions["final_week_transactions"]
            - contributions["first_week_transactions"]
            == contributions["transaction_change"]
        ).all()
    ):
        raise ValueError(
            "Growth contributions do not reconcile."
        )

    if (
        not outcomes["initial_receipt_status"].isin(
            STATUS_LABELS
        ).all()
        or not outcomes["executor_check"].eq(
            "EXECUTOR_MATCHES_RECEIVER"
        ).all()
        or not outcomes["matched_outcome_rows"].eq(
            outcomes["transactions"]
        ).all()
    ):
        raise ValueError(
            "Unexpected initial receipt matching results."
        )

    for (week, account), group in outcomes.groupby(
        ["week_start", "signer_account_id"]
    ):
        expected = leading.loc[
            leading["week_start"].eq(week)
            & leading["signer_account_id"].eq(account),
            "transactions",
        ]

        if (
            len(expected) != 1
            or group["transactions"].sum() != expected.iloc[0]
        ):
            raise ValueError(
                "Account outcome totals do not reconcile."
            )

    cost_keys = [
        "week_start",
        "signer_account_id",
        "initial_receipt_status",
        "executor_check",
    ]

    if (
        not account_costs["cost_check"].eq(
            "VALID_COST"
        ).all()
        or not account_costs[
            "account_week_unassessed_or_invalid_costs"
        ].eq(0).all()
        or account_costs.duplicated(cost_keys).any()
    ):
        raise ValueError(
            "Selected-account costs contain invalid or duplicate rows."
        )

    cost_values = account_costs[
        "recorded_initial_receipt_cost_near"
    ]

    if not cost_values.map(
        lambda value: (
            pd.notna(value)
            and 0 <= value < float("inf")
        )
    ).all():
        raise ValueError(
            "Selected-account costs must be finite and nonnegative."
        )

    cost_counts = account_costs.set_index(
        cost_keys
    )["transactions"].sort_index()

    outcome_counts = outcomes.set_index(
        cost_keys
    )["transactions"].sort_index()

    if not cost_counts.equals(outcome_counts):
        raise ValueError(
            "Selected-account costs do not reconcile to result 24."
        )

    records = diagnostics["records"]

    if (
        len(records) != 18
        or len({
            record["sample"]["receipt_id"]
            for record in records
        }) != 18
    ):
        raise ValueError(
            "Expected 18 distinct diagnostic receipts."
        )

    for record in records:
        sample = record["sample"]
        matched = record["matched_receipt"]

        if (
            record["retrieval_status"] != "VALIDATED_FAILURE"
            or matched["receipt_id"] != sample["receipt_id"]
            or matched["executor_id"]
            != sample["executor_account_id"]
            or "Failure" not in matched["status"]
        ):
            raise ValueError(
                "Unvalidated diagnostic receipt."
            )

    error_messages = Counter(
        message
        for record in records
        for message in set(
            record["matched_receipt"]["execution_errors"]
        )
    )

    slippage_count = sum(
        count
        for message, count in error_messages.items()
        if "E68:" in message
    )

    deposit_count = sum(
        count
        for message, count in error_messages.items()
        if "E22:" in message
    )

    if (
        slippage_count != 17
        or deposit_count != 1
        or any(
            record["matched_receipt"]["executor_id"]
            != "v2.ref-finance.near"
            or record["sample"]["signer_account_id"]
            != "tinykoala595.near"
            for record in records
        )
    ):
        raise ValueError(
            "Diagnostic evidence differs from the reported sample."
        )

    group_summary = spike[
        [
            "return_group",
            "group_accounts",
            "group_transactions",
        ]
    ].drop_duplicates()

    expected_groups = {
        "ACTIVE_FOLLOWING_WEEK",
        "NOT_ACTIVE_FOLLOWING_WEEK",
    }

    if (
        len(group_summary) != 2
        or set(group_summary["return_group"])
        != expected_groups
    ):
        raise ValueError(
            "The spike cohort group totals are inconsistent."
        )

    starting_week = pd.Timestamp("2026-09-28")
    following_week = pd.Timestamp("2026-10-05")

    if (
        not spike["cohort_week"].eq(starting_week).all()
        or not spike["followup_week"].eq(
            following_week
        ).all()
    ):
        raise ValueError(
            "The spike cohort dates are inconsistent."
        )

    starting = weekly.loc[
        weekly["week_start"].eq(starting_week)
    ]

    followup = returns.loc[
        returns["cohort_week"].eq(starting_week)
        & returns["week_offset"].eq(1)
    ]

    if len(starting) != 1 or len(followup) != 1:
        raise ValueError(
            "Unable to reconcile the spike cohort."
        )

    if (
        group_summary["group_accounts"].sum()
        != starting.iloc[0]["weekly_active_signing_accounts"]
        or group_summary["group_transactions"].sum()
        != starting.iloc[0]["transactions"]
    ):
        raise ValueError(
            "The spike cohort totals do not reconcile."
        )

    returned_accounts = group_summary.loc[
        group_summary["return_group"].eq(
            "ACTIVE_FOLLOWING_WEEK"
        ),
        "group_accounts",
    ].iloc[0]

    if (
        returned_accounts
        != followup.iloc[0]["active_cohort_accounts"]
    ):
        raise ValueError(
            "The spike return count does not reconcile."
        )

except (
    OSError,
    ValueError,
    KeyError,
    TypeError,
) as error:
    st.error(
        f"Unable to load the research results: {error}"
    )
    st.stop()


def show_weekly_chart(fig):
    fig.update_xaxes(
        tickmode="array",
        tickvals=weekly["week_start"].tolist(),
        ticktext=weekly["week_start"].dt.strftime(
            "%d %b"
        ).tolist(),
        title_text="Week starting · 2026",
    )

    fig.update_layout(
        legend_title_text="",
        margin=dict(t=30, b=40),
    )

    st.plotly_chart(fig, width="stretch")


st.title("NEAR Growth Intelligence")

st.write(
    "Does higher network activity translate into broader, "
    "more persistent participation?"
)

st.caption(
    "24 August–18 October 2026 · Eight complete UTC weeks · "
    "Source: public NEAR mainnet data in Google BigQuery"
)

with st.sidebar:
    st.header("About this research")

    st.write(
        "Explore activity, growth drivers, account returns, "
        "concentration, economic comparisons, decision priorities "
        "and selected account profiles."
    )

    st.caption(
        "This dashboard displays saved research exports. "
        "It is not a live network feed."
    )

    st.markdown(
        "**Reading the metrics**\n\n"
        "- Signing accounts are identifiers, not verified people.\n"
        "- Transaction receivers are not automatically applications.\n"
        "- Initial receipt outcomes do not establish complete "
        "execution-chain results.\n"
        "- Receipt execution costs are not protocol revenue.\n"
        "- Eight weeks do not establish long-term adoption."
    )


first = weekly.iloc[0]
last = weekly.iloc[-1]


def change(field):
    return 100 * (
        last[field] / first[field] - 1
    )


a, b, c = st.columns(3)

a.metric(
    "Final-week transactions",
    f"{int(last['transactions']):,}",
    f"{change('transactions'):+.2f}% vs first week",
    delta_color="off",
)

b.metric(
    "Final-week active signing accounts",
    f"{int(last['weekly_active_signing_accounts']):,}",
    (
        f"{change('weekly_active_signing_accounts'):+.2f}% "
        "vs first week"
    ),
    delta_color="off",
)

c.metric(
    "Final-week receipt execution cost",
    f"{last['recorded_execution_cost_near']:,.2f} NEAR",
    (
        f"{change('recorded_execution_cost_near'):+.2f}% "
        "vs first week"
    ),
    delta_color="off",
)

st.subheader("Investment assessment")

st.info(
    "Network activity continued, but this eight-week window "
    "does not demonstrate broader, persistent participation or "
    "quantify economic value accruing to NEAR holders. An "
    "adoption-led investment case therefore remains conditional "
    "on stronger evidence of durable application demand and "
    "measurable token value capture. Activity outside the first "
    "week's ten leading accounts increased, but selected-account "
    "checks show that transaction growth can also include "
    "substantial failed execution activity."
)

st.caption(
    "This assessment concerns the evidence examined; "
    "it is not a finding that NEAR has no investment merit."
)

with st.expander(
    "What supports the assessment, and what would change it?"
):
    st.markdown(
        "**Participation:** Final-week transactions were "
        f"{change('transactions'):+.2f}% versus the first week, "
        "while weekly active signing accounts were "
        f"{change('weekly_active_signing_accounts'):+.2f}%. "
        "Transaction growth alone does not establish broader "
        "adoption. Longer-term participation associated with "
        "verified account roles would strengthen the assessment."
    )

    st.markdown(
        "**Account lifecycle:** Successful receipt executions "
        "containing self-deletion actions appeared among 82.53% "
        "of accounts absent after the spike week. The low return "
        "share is not a verified user-churn rate. Lifecycle-aware "
        "cohort comparisons are needed; simply excluding deleted "
        "accounts would not establish retention."
    )

    st.markdown(
        "**Concentration:** The ten busiest signing accounts "
        "generated "
        f"{weekly['top_10_accounts_transaction_share_pct'].min():.2f}%"
        "–"
        f"{weekly['top_10_accounts_transaction_share_pct'].max():.2f}% "
        "of weekly transactions. Verifying their roles would help "
        "establish whether this reflects shared infrastructure "
        "serving independent demand or dependence on a few "
        "participants."
    )

    st.markdown(
        "**Economics:** Recorded receipt execution costs changed "
        f"by {change('recorded_execution_cost_near'):+.2f}% "
        "between the first and final weeks. This measures execution "
        "spending, not holder returns. Relevant fee distributions, "
        "issuance and other economic flows need separate "
        "reconciliation."
    )

    st.markdown(
        "**What would weaken the case:** Declining comparable-cohort "
        "participation after lifecycle effects are examined; "
        "increasing dependence accompanied by weakening independent "
        "demand; or economic flows that do not support the assumed "
        "token-demand or supply effects. These conditions have not "
        "all been tested."
    )

    st.caption(
        "Self-deletion evidence: saved result 17. Weekly figures "
        "use the combined weekly results. Growth drivers and "
        "selected-account execution evidence are available in the "
        "Growth drivers tab. The full investment assessment and "
        "economic mechanisms note are included in the repository."
    )


(
    growth_tab,
    drivers_tab,
    returns_tab,
    concentration_tab,
    costs_tab,
    decisions_tab,
    explorer_tab,
) = st.tabs(
    [
        "Growth",
        "Growth drivers",
        "Account returns",
        "Concentration",
        "Economics",
        "Decision priorities",
        "Account explorer",
    ]
)


with growth_tab:
    st.subheader(
        "Activity and costs followed different paths"
    )

    st.write(
        "Compare changes from the first week, indexed to 100. "
        "An index of 150 means a value is 50% above its "
        "starting level."
    )

    index_columns = {
        "transactions_index_first_week_100": "Transactions",
        "weekly_active_accounts_index_first_week_100": (
            "Weekly active signing accounts"
        ),
        "recorded_cost_index_first_week_100": (
            "Recorded receipt execution cost"
        ),
    }

    indexed = weekly[
        ["week_start", *index_columns]
    ].rename(columns=index_columns)

    fig = px.line(
        indexed,
        x="week_start",
        y=list(index_columns.values()),
        markers=True,
        labels={
            "week_start": "Week starting",
            "value": "Index · first week = 100",
            "variable": "Metric",
        },
    )

    fig.add_hline(
        y=100,
        line_dash="dot",
        line_color="#888888",
    )

    show_weekly_chart(fig)

    st.caption(
        "Transactions use submission dates; receipt costs use "
        "execution dates. These series do not match individual "
        "transactions to their complete execution costs."
    )

    st.subheader("Weekly participation")

    fig = px.bar(
        weekly,
        x="week_start",
        y="weekly_active_signing_accounts",
        labels={
            "week_start": "Week starting",
            "weekly_active_signing_accounts": (
                "Distinct active signing accounts"
            ),
        },
    )

    show_weekly_chart(fig)


with drivers_tab:
    st.subheader(
        "Where did transaction growth come from?"
    )

    st.write(
        "Keep the first week's ten busiest signing accounts "
        "fixed across all eight weeks, then compare their "
        "activity with every other account."
    )

    fixed_first = fixed.iloc[0]
    fixed_last = fixed.iloc[-1]

    fixed_change = 100 * (
        fixed_last["fixed_group_transactions"]
        / fixed_first["fixed_group_transactions"]
        - 1
    )

    outside_change = 100 * (
        fixed_last["outside_fixed_group_transactions"]
        / fixed_first["outside_fixed_group_transactions"]
        - 1
    )

    left, right = st.columns(2)

    left.metric(
        "First-week leaders · transaction change",
        f"{fixed_change:+.2f}%",
    )

    right.metric(
        "All other accounts · transaction change",
        f"{outside_change:+.2f}%",
    )

    fixed_labels = {
        "fixed_group_transactions": (
            "First-week top 10 accounts"
        ),
        "outside_fixed_group_transactions": (
            "All other signing accounts"
        ),
    }

    fig = px.bar(
        fixed.rename(columns=fixed_labels),
        x="week_start",
        y=list(fixed_labels.values()),
        barmode="stack",
        labels={
            "value": "Transactions",
            "variable": "Account group",
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "The group was selected using transaction counts for "
        "24–30 August. Membership stays fixed. This is an "
        "accounting comparison, not a counterfactual network "
        "without these accounts."
    )

    st.subheader(
        "Contributions to the first-to-final-week change"
    )

    group_names = {
        "FIRST_WEEK_TOP_10": "First-week top 10 accounts",
        "OTHER_TRACKED_ACCOUNT": "Other tracked accounts",
        "ALL_UNTRACKED_ACCOUNTS": (
            "All untracked accounts combined"
        ),
    }

    contribution_groups = contributions.groupby(
        "comparison_group",
        as_index=False,
    )[
        [
            "first_week_transactions",
            "final_week_transactions",
            "transaction_change",
        ]
    ].sum()

    contribution_groups["Account group"] = (
        contribution_groups["comparison_group"].map(
            group_names
        )
    )

    fig = px.bar(
        contribution_groups,
        x="Account group",
        y="transaction_change",
        text_auto=",.0f",
        labels={
            "transaction_change": "Change in transactions"
        },
    )

    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Tracked accounts are the union of the weekly top 20 "
        "signing accounts. The untracked group combines all "
        "remaining accounts; it does not identify ordinary "
        "users or independent demand. The three changes sum "
        "to the network's net transaction change."
    )

    with st.expander(
        "Inspect individual growth contributions"
    ):
        display = contributions.copy()

        display["signer_account_id"] = (
            display["signer_account_id"].fillna(
                "All untracked accounts combined"
            )
        )

        st.dataframe(
            display.sort_values(
                "transaction_change",
                ascending=False,
            ),
            hide_index=True,
            width="stretch",
        )

    st.subheader(
        "Inspect the accounts behind the counts"
    )

    account_options = (
        leading.groupby(
            "signer_account_id"
        )["transactions"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    chosen_account = st.selectbox(
        "Signing account",
        options=account_options,
        key="drivers_signing_account",
    )

    account_series = leading.loc[
        leading["signer_account_id"].eq(
            chosen_account
        )
    ].sort_values("week_start")

    fig = px.line(
        account_series,
        x="week_start",
        y="transactions",
        markers=True,
        labels={
            "transactions": "Transactions"
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "All eight weeks are included for each tracked account. "
        "An account name alone does not verify its owner, role "
        "or number of users."
    )

    action_views = [
        (
            "Original transaction actions",
            leading_actions,
            ["action_kind", "method_name"],
        ),
        (
            "Growth-account destinations and actions",
            growth_actions,
            [
                "receiver_account_id",
                "action_kind",
                "method_name",
            ],
        ),
    ]

    for title, frame, fields in action_views:
        selected_actions = frame.loc[
            frame["signer_account_id"].eq(
                chosen_account
            )
        ]

        if not selected_actions.empty:
            with st.expander(title):
                action_totals = (
                    selected_actions.groupby(
                        fields,
                        dropna=False,
                        as_index=False,
                    )[["transactions", "action_rows"]]
                    .sum()
                    .sort_values(
                        "transactions",
                        ascending=False,
                    )
                )

                st.dataframe(
                    action_totals,
                    hide_index=True,
                    width="stretch",
                )

                st.caption(
                    "Transaction counts can overlap across "
                    "action categories. DELEGATE_ACTION rows "
                    "have not been expanded into their inner "
                    "actions. Action records alone do not "
                    "establish success."
                )

    st.subheader(
        "Did the selected growth accounts execute successfully?"
    )

    selected_account = st.selectbox(
        "Inspect initial receipt outcomes",
        options=sorted(
            outcomes["signer_account_id"].unique()
        ),
    )

    account_outcomes = outcomes.loc[
        outcomes["signer_account_id"].eq(
            selected_account
        )
    ]

    outcome_totals = account_outcomes.groupby(
        "initial_receipt_status"
    )["transactions"].sum()

    total = int(outcome_totals.sum())
    failed = int(
        outcome_totals.get("FAILURE", 0)
    )

    left, right = st.columns(2)

    left.metric(
        "Selected account · transactions",
        f"{total:,}",
    )

    right.metric(
        "Failed initial receipts",
        f"{failed / total:.2%}",
    )

    plot_outcomes = account_outcomes.groupby(
        ["week_start", "initial_receipt_status"],
        as_index=False,
    )["transactions"].sum()

    plot_outcomes["Initial receipt status"] = (
        plot_outcomes["initial_receipt_status"].map(
            STATUS_LABELS
        )
    )

    fig = px.bar(
        plot_outcomes,
        x="week_start",
        y="transactions",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={
            "transactions": "Transactions"
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "Each selected transaction matched one initial receipt "
        "outcome. SUCCESS_RECEIPT_ID is not proof of successful "
        "downstream execution. These two accounts were selected "
        "for investigation, so their outcome shares do not "
        "estimate network-wide failure rates. Weeks without "
        "transactions have no outcome bars."
    )

    st.subheader(
        "What did these initial receipts cost?"
    )

    selected_costs = account_costs.loc[
        account_costs["signer_account_id"].eq(
            selected_account
        )
    ].copy()

    total_cost = selected_costs[
        "recorded_initial_receipt_cost_near"
    ].sum()

    failed_cost = selected_costs.loc[
        selected_costs["initial_receipt_status"].eq(
            "FAILURE"
        ),
        "recorded_initial_receipt_cost_near",
    ].sum()

    left, middle, right = st.columns(3)

    left.metric(
        "All initial receipts",
        f"{total_cost:,.4f} NEAR",
    )

    middle.metric(
        "Failed initial receipts",
        f"{failed_cost:,.4f} NEAR",
    )

    right.metric(
        "Failed share of initial-receipt cost",
        (
            f"{failed_cost / total_cost:.2%}"
            if total_cost > 0
            else "N/A"
        ),
    )

    selected_costs["Initial receipt status"] = (
        selected_costs["initial_receipt_status"].map(
            STATUS_LABELS
        )
    )

    fig = px.bar(
        selected_costs,
        x="week_start",
        y="recorded_initial_receipt_cost_near",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={
            "recorded_initial_receipt_cost_near": (
                "Recorded initial-receipt execution cost (NEAR)"
            )
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "Approximate costs from saved result 27, grouped by "
        "the originating transaction's submission week. These "
        "cover initial receipts only and exclude transaction "
        "receipt-conversion costs and downstream receipts. "
        "They do not measure protocol revenue, permanent token "
        "burning or value accruing to holders. Their scope "
        "differs from the network-wide costs grouped by "
        "execution date in the Economics tab."
    )

    with st.expander(
        "Inspect and download selected-account costs"
    ):
        st.dataframe(
            selected_costs,
            hide_index=True,
            width="stretch",
        )

        st.download_button(
            "Download selected-account costs",
            data=selected_costs.to_csv(
                index=False
            ).encode("utf-8"),
            file_name=(
                f"27_{selected_account}_"
                f"initial_receipt_costs_{PERIOD}.csv"
            ),
            mime="text/csv",
        )

    st.subheader(
        "What did the sampled failures report?"
    )

    diagnostic_table = pd.DataFrame(
        [
            {
                "Reported execution error": message,
                "Sampled receipts": count,
            }
            for message, count
            in error_messages.most_common()
        ]
    )

    st.dataframe(
        diagnostic_table,
        hide_index=True,
        width="stretch",
    )

    st.write(
        "All 18 sampled failed receipts executed on "
        "v2.ref-finance.near: 17 reported E68 slippage errors "
        "and one reported E22 insufficient deposited tokens. "
        "These are reported contract errors, not a diagnosis "
        "of the operators' intentions."
    )

    st.caption(
        "The sample covers three selected receipts per active "
        "week for tinykoala595.near. It does not estimate error "
        "frequencies across all 715,518 failures, establish "
        "retries, or identify automation. Sources: saved "
        "results 25 and 26."
    )

    with st.expander(
        "Inspect the sampled receipt evidence"
    ):
        evidence = pd.DataFrame(
            [
                {
                    "Transaction hash": (
                        record["sample"]["transaction_hash"]
                    ),
                    "Receipt ID": (
                        record["sample"]["receipt_id"]
                    ),
                    "Executor": (
                        record["matched_receipt"]["executor_id"]
                    ),
                    "Execution error": "; ".join(
                        record["matched_receipt"][
                            "execution_errors"
                        ]
                    ),
                }
                for record in records
            ]
        )

        st.dataframe(
            evidence,
            hide_index=True,
            width="stretch",
        )

    st.download_button(
        "Download growth contributions",
        data=contributions.to_csv(
            index=False
        ).encode("utf-8"),
        file_name=(
            f"22_account_growth_contributions_{PERIOD}.csv"
        ),
        mime="text/csv",
    )


with returns_tab:
    st.subheader(
        "Did accounts participate in later weeks?"
    )

    st.write(
        "Each cohort contains all signing accounts active "
        "in its starting week. Cells show the percentage "
        "active in a particular later week."
    )

    heatmap = returns.pivot(
        index="cohort_week",
        columns="week_offset",
        values="cohort_active_share_pct",
    ).sort_index()

    heatmap = heatmap.reindex(
        columns=range(5)
    )

    heatmap.index = heatmap.index.strftime(
        "%d %b %Y"
    )

    heatmap.columns = [
        "Starting week",
        "Week +1",
        "Week +2",
        "Week +3",
        "Week +4",
    ]

    fig = px.imshow(
        heatmap,
        text_auto=".2f",
        aspect="auto",
        zmin=0,
        zmax=100,
        color_continuous_scale="Teal",
        labels={
            "x": "Follow-up",
            "y": "Cohort starting",
            "color": "Active share (%)",
        },
    )

    fig.update_traces(
        hoverongaps=False
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "Blank cells have no complete follow-up week. They "
        "are not zero returns. Cohorts overlap and do not "
        "represent newly acquired users. Participation need "
        "not be continuous."
    )

    with st.expander(
        "Inspect cohort results"
    ):
        st.dataframe(
            returns,
            hide_index=True,
            width="stretch",
        )

    st.info(
        "Account deletion changes how these returns should "
        "be read. During 28 September–4 October, 309,280 "
        "accounts absent the following week had successful "
        "receipt executions containing self-deletion actions. "
        "They represented 82.53% of the absent group. This "
        "absence should not be interpreted as ordinary user "
        "churn. Reasons for deletion and later account "
        "recreation remain unverified."
    )

    st.subheader(
        "The spike: account counts versus transaction activity"
    )

    st.write(
        "Among accounts active during 28 September–4 October, "
        "how much starting-week activity came from accounts "
        "that participated again during 5–11 October?"
    )

    group_labels = {
        "ACTIVE_FOLLOWING_WEEK": (
            "Active the following week"
        ),
        "NOT_ACTIVE_FOLLOWING_WEEK": (
            "Absent the following week"
        ),
    }

    group_summary = group_summary.copy()

    group_summary["Participation"] = (
        group_summary["return_group"].map(
            group_labels
        )
    )

    account_total = group_summary[
        "group_accounts"
    ].sum()

    transaction_total = group_summary[
        "group_transactions"
    ].sum()

    group_summary["Share of accounts (%)"] = (
        100
        * group_summary["group_accounts"]
        / account_total
    )

    group_summary[
        "Share of starting-week transactions (%)"
    ] = (
        100
        * group_summary["group_transactions"]
        / transaction_total
    )

    returned = group_summary.loc[
        group_summary["return_group"].eq(
            "ACTIVE_FOLLOWING_WEEK"
        )
    ].iloc[0]

    left, right = st.columns(2)

    left.metric(
        "Accounts active the following week",
        f"{returned['Share of accounts (%)']:.2f}%",
    )

    right.metric(
        "Their share of starting-week transactions",
        (
            f"{returned['Share of starting-week transactions (%)']:.2f}%"
        ),
    )

    comparison = group_summary.melt(
        id_vars="Participation",
        value_vars=[
            "Share of accounts (%)",
            "Share of starting-week transactions (%)",
        ],
        var_name="Measure",
        value_name="Share (%)",
    )

    fig = px.bar(
        comparison,
        x="Measure",
        y="Share (%)",
        color="Participation",
        barmode="stack",
        text_auto=".2f",
        range_y=[0, 100],
        color_discrete_map={
            "Active the following week": COLORS[0],
            "Absent the following week": COLORS[1],
        },
        category_orders={
            "Participation": [
                "Active the following week",
                "Absent the following week",
            ]
        },
    )

    fig.update_layout(
        xaxis_title=None,
        legend_title_text="",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "The two groups cover the same starting-week cohort. "
        "Account shares and transaction shares have different "
        "denominators. Absence the following week does not "
        "establish permanent departure, and accounts are not "
        "verified people."
    )

    with st.expander(
        "Inspect spike cohort group totals"
    ):
        st.dataframe(
            group_summary[
                [
                    "Participation",
                    "group_accounts",
                    "group_transactions",
                    "Share of accounts (%)",
                    "Share of starting-week transactions (%)",
                ]
            ],
            hide_index=True,
            width="stretch",
        )


with concentration_tab:
    st.subheader(
        "How broadly was activity distributed?"
    )

    signer_shares = {
        "top_1_account_transaction_share_pct": (
            "Top signing account"
        ),
        "top_10_accounts_transaction_share_pct": (
            "Top 10 signing accounts"
        ),
        "top_100_accounts_transaction_share_pct": (
            "Top 100 signing accounts"
        ),
    }

    fig = px.line(
        weekly.rename(
            columns=signer_shares
        ),
        x="week_start",
        y=list(signer_shares.values()),
        markers=True,
        labels={
            "week_start": "Week starting",
            "value": "Share of transactions (%)",
            "variable": "Group",
        },
    )

    fig.update_yaxes(
        range=[0, 100]
    )

    show_weekly_chart(fig)

    st.caption(
        "Groups are nested and must not be added together. "
        "Accounts are ranked separately each week."
    )

    selected_week = st.selectbox(
        "Inspect transaction receivers for the week starting",
        options=weekly["week_start"].tolist(),
        format_func=lambda value: value.strftime(
            "%d %B %Y"
        ),
    )

    selected = receivers.loc[
        receivers["week_start"].eq(
            selected_week
        )
    ].sort_values("receiver_rank")

    if selected.empty:
        st.error(
            "No receiver results are available for this week."
        )
        st.stop()

    receiver_summary = selected.iloc[0]

    left, right = st.columns(2)

    left.metric(
        "Top 10 receivers · transaction share",
        (
            f"{receiver_summary['top_10_receiver_transaction_share_pct']:.2f}%"
        ),
    )

    right.metric(
        "Top 20 receivers · transaction share",
        (
            f"{receiver_summary['top_20_receiver_transaction_share_pct']:.2f}%"
        ),
    )

    fig = px.bar(
        selected.sort_values(
            "transactions"
        ),
        x="transactions",
        y="receiver_account_id",
        orientation="h",
        hover_data={
            "signing_accounts": True,
            "weekly_transaction_share_pct": ":.2f",
        },
        labels={
            "transactions": "Transactions",
            "receiver_account_id": "Receiver account",
            "signing_accounts": "Distinct signing accounts",
            "weekly_transaction_share_pct": (
                "Share of weekly transactions (%)"
            ),
        },
        height=700,
    )

    fig.update_layout(
        yaxis=dict(
            categoryorder="total ascending"
        ),
        margin=dict(t=30, b=40),
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.caption(
        "Only the twenty busiest original transaction "
        "receivers are shown. Absence from a ranking does "
        "not mean zero activity. Receiver-level signing-account "
        "counts can overlap."
    )

    with st.expander(
        "Inspect receiver results"
    ):
        st.dataframe(
            selected[
                [
                    "receiver_rank",
                    "receiver_account_id",
                    "transactions",
                    "signing_accounts",
                    "weekly_transaction_share_pct",
                ]
            ],
            hide_index=True,
            width="stretch",
        )


with costs_tab:
    st.subheader(
        "Activity, execution spending and supply"
    )

    st.write(
        "Compare network activity with recorded execution "
        "spending and observed supply movement. These measures "
        "answer different economic questions."
    )

    econ_first = economics.iloc[0]
    econ_last = economics.iloc[-1]

    comparison_fields = {
        "transactions": "Transactions",
        "receipt_execution_outcomes": (
            "Receipt execution outcomes"
        ),
        "recorded_receipt_execution_cost_near": (
            "Recorded receipt execution cost"
        ),
        "average_recorded_cost_per_receipt_near": (
            "Average cost per receipt"
        ),
    }

    changes = pd.DataFrame(
        [
            {
                "Measure": label,
                "First-to-final-week change (%)": (
                    100
                    * (
                        econ_last[field]
                        / econ_first[field]
                        - 1
                    )
                ),
            }
            for field, label
            in comparison_fields.items()
        ]
    )

    fig = px.bar(
        changes,
        x="Measure",
        y="First-to-final-week change (%)",
        text_auto=".2f",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    st.write(
        "Receipt execution outcomes increased "
        f"{changes.iloc[1]['First-to-final-week change (%)']:.2f}%, "
        "while average recorded cost per receipt increased "
        f"{changes.iloc[3]['First-to-final-week change (%)']:.2f}%. "
        "Together, these describe the rise in recorded receipt "
        "execution costs. The comparison does not identify "
        "its underlying causes."
    )

    st.caption(
        "Transaction counts use submission dates; receipt "
        "counts and costs use execution dates. These are "
        "endpoint comparisons across eight weeks, not matched "
        "transaction-chain costs or a causal model."
    )

    st.subheader(
        "Observed total-supply movement"
    )

    opening_supply = float(
        econ_first["opening_observed_supply_near"]
    )

    closing_supply = float(
        econ_last["closing_observed_supply_near"]
    )

    net_supply = (
        closing_supply - opening_supply
    )

    left, right = st.columns(2)

    left.metric(
        "Net observed supply change",
        f"{net_supply:+,.2f} NEAR",
    )

    right.metric(
        "Change from opening supply",
        (
            f"{100 * net_supply / opening_supply:+.4f}%"
        ),
    )

    fig = px.bar(
        economics,
        x="week_start",
        y="net_observed_supply_change_near",
        labels={
            "net_observed_supply_change_near": (
                "Net observed supply change (NEAR)"
            )
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "Each week compares the preceding Sunday's closing "
        "supply with the current Sunday's close. Total supply "
        "is not circulating supply. Net supply movement does "
        "not separately measure issuance and burning."
    )

    with st.expander(
        "Inspect supply reconciliation and measurement boundaries"
    ):
        validator_change = economics[
            "validator_update_net_balance_change_near"
        ].sum()

        positive_supply = economics[
            "observed_positive_supply_movements_near"
        ].sum()

        decreases = economics[
            "observed_supply_decrease_magnitude_near"
        ].sum()

        reconciliation = pd.DataFrame(
            [
                {
                    "Measurement": (
                        "Observed positive block supply movements"
                    ),
                    "NEAR": positive_supply,
                },
                {
                    "Measurement": (
                        "Observed block supply decrease magnitude"
                    ),
                    "NEAR": decreases,
                },
                {
                    "Measurement": (
                        "Net observed supply change"
                    ),
                    "NEAR": net_supply,
                },
                {
                    "Measurement": (
                        "Validator-update net balance change"
                    ),
                    "NEAR": validator_change,
                },
                {
                    "Measurement": (
                        "Net supply change minus validator change"
                    ),
                    "NEAR": (
                        net_supply - validator_change
                    ),
                },
                {
                    "Measurement": (
                        "Positive supply movements minus validator change"
                    ),
                    "NEAR": (
                        positive_supply - validator_change
                    ),
                },
            ]
        )

        st.dataframe(
            reconciliation,
            hide_index=True,
            width="stretch",
        )

        st.write(
            "The validator-update balance comparison does "
            "not fully reconcile with supply movements. "
            "These differences remain unresolved. Block-level "
            "increases and decreases can contain offsetting "
            "effects; they are not complete measurements of "
            "gross issuance and permanent burning. Recorded "
            "receipt costs must not be substituted for either."
        )

        st.caption(
            "Source fields use floating-point storage. "
            "Amounts are approximate. Underlying validation "
            "and the 0.000001 NEAR analytical tolerance for "
            "individual validator balance comparisons are "
            "documented in the data-check notes. Sources: "
            "results 28 and 32–34."
        )

    with st.expander(
        "Inspect and download the weekly economic comparison"
    ):
        st.dataframe(
            economics,
            hide_index=True,
            width="stretch",
        )

        st.download_button(
            "Download weekly economic comparison",
            data=economics.to_csv(
                index=False
            ).encode("utf-8"),
            file_name=(
                f"34_weekly_economic_comparison_{PERIOD}.csv"
            ),
            mime="text/csv",
        )

    st.subheader(
        "Recorded receipt execution costs"
    )

    cost_chart = weekly[
        [
            "week_start",
            "recorded_execution_cost_near",
            "failed_receipt_cost_near",
        ]
    ].copy()

    cost_chart[
        "Non-failed receipt outcomes"
    ] = (
        cost_chart["recorded_execution_cost_near"]
        - cost_chart["failed_receipt_cost_near"]
    )

    cost_chart = cost_chart.rename(
        columns={
            "failed_receipt_cost_near": (
                "Failed receipt outcomes"
            )
        }
    )

    fig = px.bar(
        cost_chart,
        x="week_start",
        y=[
            "Non-failed receipt outcomes",
            "Failed receipt outcomes",
        ],
        barmode="stack",
        labels={
            "week_start": "Week starting",
            "value": "Recorded execution cost (NEAR)",
            "variable": "Outcome group",
        },
    )

    show_weekly_chart(fig)

    st.caption(
        "Approximate amounts from floating-point source fields. "
        "Costs exclude transaction receipt-conversion costs "
        "and do not establish protocol revenue or permanent "
        "token burning."
    )

    st.subheader(
        "Failures: share of outcomes versus share of cost"
    )

    failure_labels = {
        "failed_receipt_share_pct": (
            "Failed share of outcomes"
        ),
        "failed_receipt_cost_share_pct": (
            "Failed share of cost"
        ),
    }

    fig = px.line(
        weekly.rename(
            columns=failure_labels
        ),
        x="week_start",
        y=list(failure_labels.values()),
        markers=True,
        labels={
            "week_start": "Week starting",
            "value": "Share (%)",
            "variable": "Metric",
        },
    )

    fig.update_yaxes(
        rangemode="tozero"
    )

    show_weekly_chart(fig)


with decisions_tab:
    st.subheader(
        "Turn the evidence into investigation priorities"
    )

    st.write(
        "Use these findings to decide what needs checking "
        "before relying on a growth claim, evaluating "
        "application activity or allocating support."
    )

    audience = st.selectbox(
        "Who are you researching for?",
        [
            "Investors and research analysts",
            "NEAR ecosystem teams",
            "Application developers",
        ],
    )

    audience_guidance = {
        "Investors and research analysts": (
            "Test adoption and economic claims before using "
            "them in an investment thesis. The project does "
            "not provide a valuation or an expected-return "
            "forecast."
        ),
        "NEAR ecosystem teams": (
            "Identify growth that needs lifecycle, account-role "
            "or execution-quality checks before it informs "
            "ecosystem support. These are not application-impact "
            "rankings."
        ),
        "Application developers": (
            "Use action patterns, receipt outcomes and "
            "diagnostic errors to frame investigations. "
            "The selected accounts do not represent every "
            "application's users."
        ),
    }

    st.write(
        audience_guidance[audience]
    )

    priorities = [
        {
            "Priority": (
                "Check lifecycle before interpreting account returns"
            ),
            "Evidence": (
                "309,280 accounts absent after the spike week "
                "had successful self-deletion receipts: "
                "82.53% of the absent group."
            ),
            "Decision implication": (
                "Do not interpret the absence rate as "
                "ordinary user churn."
            ),
            "Next action": (
                "Examine deletion, recreation and account "
                "roles before evaluating acquisition or retention."
            ),
            "Evidence boundary": (
                "Deletion motives, ownership and later "
                "recreation remain unverified."
            ),
            "Sources": "Results 11, 16 and 17",
        },
        {
            "Priority": (
                "Check execution quality behind growth"
            ),
            "Evidence": (
                "tinykoala595.near had 715,518 failed initial "
                "receipts (91.90% of its transactions), costing "
                "approximately 211.1629 NEAR."
            ),
            "Decision implication": (
                "Additional submissions and execution costs "
                "do not necessarily represent successful "
                "application interactions."
            ),
            "Next action": (
                "Use receipt outcomes and reported contract "
                "errors alongside growth when selecting "
                "activity for investigation."
            ),
            "Evidence boundary": (
                "The two accounts and eighteen diagnostic "
                "receipts do not establish network-wide "
                "failure or error frequencies."
            ),
            "Sources": "Results 22–27",
        },
        {
            "Priority": (
                "Verify the roles behind concentration"
            ),
            "Evidence": (
                "Weekly top-ten signers generated "
                f"{weekly['top_10_accounts_transaction_share_pct'].min():.2f}%"
                "–"
                f"{weekly['top_10_accounts_transaction_share_pct'].max():.2f}% "
                "of transactions; leading-account records "
                "include delegated actions."
            ),
            "Decision implication": (
                "Signing concentration is not equivalent "
                "to concentration among end users or "
                "application owners."
            ),
            "Next action": (
                "Verify major account roles and delegated "
                "interactions before interpreting concentration "
                "as broad demand or weak demand."
            ),
            "Evidence boundary": (
                "Delegated payloads have not been expanded "
                "and account names do not verify ownership."
            ),
            "Sources": "Results 10 and 18–20",
        },
        {
            "Priority": (
                "Follow growth beyond the original leaders"
            ),
            "Evidence": (
                "Transactions outside the first week's top "
                "ten rose 52.50%, while the fixed leaders' "
                "activity fell 19.83%. Untracked accounts "
                "contributed 43.80% of the outside group's "
                "net increase."
            ),
            "Decision implication": (
                "The original leaders do not explain all "
                "growth. Other contributors deserve "
                "investigation before support decisions."
            ),
            "Next action": (
                "Examine contributor roles, persistence "
                "and execution quality."
            ),
            "Evidence boundary": (
                "The untracked aggregate is not a "
                "classification of ordinary users, and "
                "contributions describe net transaction changes."
            ),
            "Sources": "Results 18 and 21–24",
        },
        {
            "Priority": (
                "Require reconciliation before making economic claims"
            ),
            "Evidence": (
                "Receipt costs rose 82.73% between the "
                "endpoints while total supply increased "
                "approximately 4.936 million NEAR over "
                "the period."
            ),
            "Decision implication": (
                "Higher execution spending does not by "
                "itself establish permanent burning, "
                "protocol revenue or holder value."
            ),
            "Next action": (
                "Keep cost and supply measurements separate "
                "and require identified economic flows "
                "before making supply or valuation claims."
            ),
            "Evidence boundary": (
                "Validator-update balances and supply "
                "movements remain incompletely reconciled; "
                "no complete value-capture model is provided."
            ),
            "Sources": "Results 13, 14 and 28–34",
        },
    ]

    chosen_priority = st.selectbox(
        "Choose an investigation priority",
        [
            item["Priority"]
            for item in priorities
        ],
    )

    priority = next(
        item
        for item in priorities
        if item["Priority"] == chosen_priority
    )

    st.markdown(
        f"**Evidence:** {priority['Evidence']}"
    )

    st.markdown(
        "**Decision implication:** "
        + priority["Decision implication"]
    )

    st.markdown(
        f"**Next action:** {priority['Next action']}"
    )

    st.caption(
        "Evidence boundary: "
        + priority["Evidence boundary"]
        + " Sources: "
        + priority["Sources"]
        + "."
    )

    with st.expander(
        "Compare all investigation priorities"
    ):
        priority_table = pd.DataFrame(
            priorities
        )

        st.dataframe(
            priority_table,
            hide_index=True,
            width="stretch",
        )

        st.download_button(
            "Download decision priorities",
            data=priority_table.to_csv(
                index=False
            ).encode("utf-8"),
            file_name=(
                f"decision_priorities_{PERIOD}.csv"
            ),
            mime="text/csv",
        )

    st.caption(
        "Priorities reflect research interpretation, not "
        "automated scores, application rankings or buy-and-sell "
        "signals. The written rationale is recorded in "
        "notes/decision_priorities.md."
    )


with explorer_tab:
    st.subheader("Account explorer")

    st.write(
        "Inspect selected signing accounts, their weekly "
        "activity, destinations and transaction actions. "
        "Profiles cover selected accounts rather than "
        "complete applications."
    )

    profile_path = RESULTS / (
        f"35_account_profiles_{PERIOD}.json"
    )

    try:
        document = json.loads(
            profile_path.read_text(
                encoding="utf-8"
            )
        )

        profiles = document["profiles"]

        account_ids = [
            profile["account_id"]
            for profile in profiles
        ]

        if (
            not profiles
            or len(set(account_ids))
            != len(account_ids)
        ):
            raise ValueError(
                "Missing or duplicate account profiles."
            )

        expected_weeks = set(
            weekly["week_start"].dt.strftime(
                "%Y-%m-%d"
            )
        )

        for profile in profiles:
            rows = profile["weekly"]

            if (
                len(rows) != 8
                or {
                    row["week_start"]
                    for row in rows
                } != expected_weeks
            ):
                raise ValueError(
                    "Profile weeks do not match "
                    "the observation period."
                )

            if (
                sum(
                    row["transactions"]
                    for row in rows
                )
                != profile["full_period_transactions"]
            ):
                raise ValueError(
                    "Profile transaction totals "
                    "do not reconcile."
                )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        st.error(
            f"Unable to load account profiles: {error}"
        )

    else:
        accounts = {
            profile["account_id"]: profile
            for profile in profiles
        }

        selected_profile_account = st.selectbox(
            "Signing account",
            list(accounts),
            key="explorer_account",
        )

        profile = accounts[
            selected_profile_account
        ]

        st.markdown(
            "**Evidence status:** "
            + profile["evidence_status"]
        )

        if profile.get("service"):
            st.write(
                "Associated service: "
                + profile["service"]
            )

        st.write(profile["role"])

        if profile.get("source"):
            st.link_button(
                "Open attribution source",
                profile["source"],
            )

        st.caption(
            "Attribution reviewed "
            + document["attribution_review_date"]
            + ". Current sources do not independently "
            "prove historical ownership."
        )

        history = pd.DataFrame(
            [
                {
                    key: value
                    for key, value in row.items()
                    if key not in (
                        "top_receivers",
                        "action_categories",
                    )
                }
                for row in profile["weekly"]
            ]
        ).sort_values("week_start")

        history["week_start"] = pd.to_datetime(
            history["week_start"]
        )

        start_count = int(
            history.iloc[0]["transactions"]
        )

        end_count = int(
            history.iloc[-1]["transactions"]
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Transactions signed · eight weeks",
            (
                f"{profile['full_period_transactions']:,}"
            ),
        )

        c2.metric(
            "Final-week transactions",
            f"{end_count:,}",
        )

        if start_count:
            percentage_change = (
                100
                * (
                    end_count / start_count
                    - 1
                )
            )

            c3.metric(
                "First-to-final-week change",
                f"{percentage_change:+.2f}%",
                delta_color="off",
            )
        else:
            c3.metric(
                "First-to-final-week change",
                "Not defined",
            )

        fig = px.line(
            history,
            x="week_start",
            y="transactions",
            markers=True,
            labels={
                "week_start": "Week starting",
                "transactions": "Transactions signed",
            },
        )

        show_weekly_chart(fig)

        fig = px.bar(
            history,
            x="week_start",
            y="network_transaction_share_pct",
            labels={
                "week_start": "Week starting",
                "network_transaction_share_pct": (
                    "Network transaction share (%)"
                ),
            },
        )

        show_weekly_chart(fig)

        profile_weeks = {
            row["week_start"]: row
            for row in profile["weekly"]
        }

        selected_profile_week = st.selectbox(
            "Inspect a week",
            options=sorted(profile_weeks),
            format_func=lambda value: (
                value
                + " to "
                + profile_weeks[value]["week_end"]
            ),
            key="explorer_week",
        )

        chosen_week = profile_weeks[
            selected_profile_week
        ]

        st.markdown(
            "#### Transaction destinations"
        )

        st.caption(
            "Weekly top 20 receivers only. These are "
            "original transaction destinations, not a "
            "complete downstream execution trace."
        )

        profile_receivers = pd.DataFrame(
            chosen_week["top_receivers"]
        )

        st.dataframe(
            profile_receivers,
            hide_index=True,
            width="stretch",
        )

        st.write(
            "Transactions outside the top 20 destinations: "
            f"{chosen_week['outside_top_20_receiver_transactions']:,}. "
            "Distinct receivers: "
            f"{chosen_week['distinct_receivers']:,}."
        )

        st.markdown(
            "#### Transaction actions"
        )

        st.info(
            "A transaction can appear in several action "
            "categories. Category transaction counts must "
            "not be summed or interpreted as users."
        )

        st.dataframe(
            pd.DataFrame(
                chosen_week["action_categories"]
            ),
            hide_index=True,
            width="stretch",
        )

        st.write(
            "Transactions with action records: "
            f"{chosen_week['transactions_with_action_records']:,}. "
            "Without matching action records: "
            f"{chosen_week['transactions_without_action_records']:,}."
        )

        with st.expander(
            "Measurement boundaries and profile export"
        ):
            for boundary in document[
                "measurement_boundaries"
            ]:
                st.write(
                    "• " + boundary
                )

            st.caption(
                "Relayer signing-account participation "
                "does not measure the participation or "
                "retention of the people it serves."
            )

            st.download_button(
                "Download selected account profile",
                data=json.dumps(
                    profile,
                    indent=2,
                    ensure_ascii=False,
                ),
                file_name=(
                    selected_profile_account
                    + "_profile.json"
                ),
                mime="application/json",
                key="explorer_download",
            )


st.divider()

with st.expander(
    "Inspect and download the combined weekly results"
):
    st.dataframe(
        weekly,
        hide_index=True,
        width="stretch",
    )

    st.download_button(
        "Download weekly results",
        data=weekly.to_csv(
            index=False
        ).encode("utf-8"),
        file_name=(
            f"14_weekly_growth_and_costs_{PERIOD}.csv"
        ),
        mime="text/csv",
    )

st.caption(
    "Research in progress. Observed differences do not "
    "establish their causes, user churn or investment returns."
)