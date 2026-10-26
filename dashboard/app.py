import json
from collections import Counter
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
        raise ValueError("Fixed-account totals do not reconcile.")

    if leading.duplicated(
        ["week_start", "signer_account_id"]
    ).any():
        raise ValueError("Duplicate leading-account records.")

    if not leading.groupby("signer_account_id").size().eq(
        len(weekly)
    ).all():
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
        not account_costs["cost_check"].eq("VALID_COST").all()
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
        lambda value: pd.notna(value)
        and 0 <= value < float("inf")
    ).all():
        raise ValueError(
            "Selected-account costs must be finite and nonnegative."
        )

    cost_counts = account_costs.set_index(cost_keys)[
        "transactions"
    ].sort_index()

    outcome_counts = outcomes.set_index(cost_keys)[
        "transactions"
    ].sort_index()

    if not cost_counts.equals(outcome_counts):
        raise ValueError(
            "Selected-account costs do not reconcile to result 24."
        )

    records = diagnostics["records"]

    if (
        len(records) != 18
        or len(
            {record["sample"]["receipt_id"] for record in records}
        ) != 18
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
            raise ValueError("Unvalidated diagnostic receipt.")

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
        ["return_group", "group_accounts", "group_transactions"]
    ].drop_duplicates()

    expected_groups = {
        "ACTIVE_FOLLOWING_WEEK",
        "NOT_ACTIVE_FOLLOWING_WEEK",
    }

    if (
        len(group_summary) != 2
        or set(group_summary["return_group"]) != expected_groups
    ):
        raise ValueError(
            "The spike cohort group totals are inconsistent."
        )

    starting_week = pd.Timestamp("2026-09-28")
    following_week = pd.Timestamp("2026-10-05")

    if (
        not spike["cohort_week"].eq(starting_week).all()
        or not spike["followup_week"].eq(following_week).all()
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

    if returned_accounts != followup.iloc[0][
        "active_cohort_accounts"
    ]:
        raise ValueError(
            "The spike return count does not reconcile."
        )

except (OSError, ValueError, KeyError, TypeError) as error:
    st.error(f"Unable to load the research results: {error}")
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
        "concentration and recorded receipt execution costs."
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
    return 100 * (last[field] / first[field] - 1)


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
    f"{change('weekly_active_signing_accounts'):+.2f}% vs first week",
    delta_color="off",
)
c.metric(
    "Final-week receipt execution cost",
    f"{last['recorded_execution_cost_near']:,.2f} NEAR",
    f"{change('recorded_execution_cost_near'):+.2f}% vs first week",
    delta_color="off",
)

st.subheader("Investment assessment")
st.info(
    "Network activity continued, but this eight-week window does not "
    "demonstrate broader, persistent participation or quantify economic "
    "value accruing to NEAR holders. An adoption-led investment case "
    "therefore remains conditional on stronger evidence of durable "
    "application demand and measurable token value capture. "
    "Activity outside the first week's ten leading accounts increased, "
    "but selected-account checks show that transaction growth can also "
    "include substantial failed execution activity."
)
st.caption(
    "This assessment concerns the evidence examined; it is not a finding "
    "that NEAR has no investment merit."
)

with st.expander(
    "What supports the assessment, and what would change it?"
):
    st.markdown(
        "**Participation:** Final-week transactions were "
        f"{change('transactions'):+.2f}% versus the first week, while "
        "weekly active signing accounts were "
        f"{change('weekly_active_signing_accounts'):+.2f}%. "
        "Transaction growth alone does not establish broader adoption. "
        "Longer-term participation associated with verified account roles "
        "would strengthen the assessment."
    )
    st.markdown(
        "**Account lifecycle:** Successful receipt executions containing "
        "self-deletion actions appeared among 82.53% of accounts absent "
        "after the spike week. The low return share is not a verified "
        "user-churn rate. Lifecycle-aware cohort comparisons are needed; "
        "simply excluding deleted accounts would not establish retention."
    )
    st.markdown(
        "**Concentration:** The ten busiest signing accounts generated "
        f"{weekly['top_10_accounts_transaction_share_pct'].min():.2f}%–"
        f"{weekly['top_10_accounts_transaction_share_pct'].max():.2f}% "
        "of weekly transactions. Verifying their roles would help establish "
        "whether this reflects shared infrastructure serving independent "
        "demand or dependence on a few participants."
    )
    st.markdown(
        "**Economics:** Recorded receipt execution costs changed by "
        f"{change('recorded_execution_cost_near'):+.2f}% between the first "
        "and final weeks. This measures execution spending, not holder "
        "returns. Relevant fee distributions, issuance and other economic "
        "flows need separate reconciliation."
    )
    st.markdown(
        "**What would weaken the case:** Declining comparable-cohort "
        "participation after lifecycle effects are examined; increasing "
        "dependence accompanied by weakening independent demand; or "
        "economic flows that do not support the assumed token-demand "
        "or supply effects. These conditions have not all been tested."
    )
    st.caption(
        "Self-deletion evidence: saved result 17. Weekly figures use the "
        "combined weekly results. Growth drivers and selected-account "
        "execution evidence are available in the Growth drivers tab. "
        "The full investment assessment and economic mechanisms note "
        "are included in the repository."
    )

growth_tab, drivers_tab, returns_tab, concentration_tab, costs_tab = st.tabs(
    [
        "Growth",
        "Growth drivers",
        "Account returns",
        "Concentration",
        "Execution costs",
    ]
)


with growth_tab:
    st.subheader("Activity and costs followed different paths")
    st.write(
        "Compare changes from the first week, indexed to 100. "
        "An index of 150 means a value is 50% above its starting level."
    )

    index_columns = {
        "transactions_index_first_week_100": "Transactions",
        "weekly_active_accounts_index_first_week_100":
            "Weekly active signing accounts",
        "recorded_cost_index_first_week_100":
            "Recorded receipt execution cost",
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
        "Transactions use submission dates; receipt costs use execution "
        "dates. These series do not match individual transactions to "
        "their complete execution costs."
    )

    st.subheader("Weekly participation")

    fig = px.bar(
        weekly,
        x="week_start",
        y="weekly_active_signing_accounts",
        labels={
            "week_start": "Week starting",
            "weekly_active_signing_accounts":
                "Distinct active signing accounts",
        },
    )
    show_weekly_chart(fig)


with drivers_tab:
    st.subheader("Where did transaction growth come from?")
    st.write(
        "Keep the first week's ten busiest signing accounts fixed across "
        "all eight weeks, then compare their activity with every other account."
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
        "fixed_group_transactions": "First-week top 10 accounts",
        "outside_fixed_group_transactions": "All other signing accounts",
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
        "The group was selected using transaction counts for 24–30 August. "
        "Membership stays fixed. This is an accounting comparison, not a "
        "counterfactual network without these accounts."
    )

    st.subheader("Contributions to the first-to-final-week change")

    group_names = {
        "FIRST_WEEK_TOP_10": "First-week top 10 accounts",
        "OTHER_TRACKED_ACCOUNT": "Other tracked accounts",
        "ALL_UNTRACKED_ACCOUNTS": "All untracked accounts combined",
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

    contribution_groups["Account group"] = contribution_groups[
        "comparison_group"
    ].map(group_names)

    fig = px.bar(
        contribution_groups,
        x="Account group",
        y="transaction_change",
        text_auto=",.0f",
        labels={
            "transaction_change": "Change in transactions",
        },
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Tracked accounts are the union of the weekly top 20 signing accounts. "
        "The untracked group combines all remaining accounts; it does not "
        "identify ordinary users or independent demand. The three changes "
        "sum to the network's net transaction change."
    )

    with st.expander("Inspect individual growth contributions"):
        display = contributions.copy()
        display["signer_account_id"] = display[
            "signer_account_id"
        ].fillna("All untracked accounts combined")

        st.dataframe(
            display.sort_values(
                "transaction_change",
                ascending=False,
            ),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Inspect the accounts behind the counts")

    account_options = (
        leading.groupby("signer_account_id")["transactions"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    chosen_account = st.selectbox(
        "Signing account",
        options=account_options,
    )

    account_series = leading.loc[
        leading["signer_account_id"].eq(chosen_account)
    ].sort_values("week_start")

    fig = px.line(
        account_series,
        x="week_start",
        y="transactions",
        markers=True,
        labels={"transactions": "Transactions"},
    )
    show_weekly_chart(fig)

    st.caption(
        "All eight weeks are included for each tracked account. An account "
        "name alone does not verify its owner, role or number of users."
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
            ["receiver_account_id", "action_kind", "method_name"],
        ),
    ]

    for title, frame, fields in action_views:
        selected_actions = frame.loc[
            frame["signer_account_id"].eq(chosen_account)
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
                    .sort_values("transactions", ascending=False)
                )

                st.dataframe(
                    action_totals,
                    hide_index=True,
                    width="stretch",
                )
                st.caption(
                    "Transaction counts can overlap across action categories. "
                    "DELEGATE_ACTION rows have not been expanded into their "
                    "inner actions. Action records alone do not establish success."
                )

    st.subheader("Did the selected growth accounts execute successfully?")

    selected_account = st.selectbox(
        "Inspect initial receipt outcomes",
        options=sorted(outcomes["signer_account_id"].unique()),
    )

    account_outcomes = outcomes.loc[
        outcomes["signer_account_id"].eq(selected_account)
    ]

    outcome_totals = account_outcomes.groupby(
        "initial_receipt_status"
    )["transactions"].sum()

    total = int(outcome_totals.sum())
    failed = int(outcome_totals.get("FAILURE", 0))

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

    plot_outcomes["Initial receipt status"] = plot_outcomes[
        "initial_receipt_status"
    ].map(STATUS_LABELS)

    fig = px.bar(
        plot_outcomes,
        x="week_start",
        y="transactions",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={"transactions": "Transactions"},
    )
    show_weekly_chart(fig)

    st.caption(
        "Each selected transaction matched one initial receipt outcome. "
        "SUCCESS_RECEIPT_ID is not proof of successful downstream execution. "
        "These two accounts were selected for investigation, so their outcome "
        "shares do not estimate network-wide failure rates. Weeks without "
        "transactions have no outcome bars."
    )

    st.subheader("What did these initial receipts cost?")

    selected_costs = account_costs.loc[
        account_costs["signer_account_id"].eq(selected_account)
    ].copy()

    total_cost = selected_costs[
        "recorded_initial_receipt_cost_near"
    ].sum()

    failed_cost = selected_costs.loc[
        selected_costs["initial_receipt_status"].eq("FAILURE"),
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
        f"{failed_cost / total_cost:.2%}" if total_cost > 0 else "N/A",
    )

    selected_costs["Initial receipt status"] = selected_costs[
        "initial_receipt_status"
    ].map(STATUS_LABELS)

    fig = px.bar(
        selected_costs,
        x="week_start",
        y="recorded_initial_receipt_cost_near",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={
            "recorded_initial_receipt_cost_near":
                "Recorded initial-receipt execution cost (NEAR)",
        },
    )
    show_weekly_chart(fig)

    st.caption(
        "Approximate costs from saved result 27, grouped by the originating "
        "transaction's submission week. These cover initial receipts only "
        "and exclude transaction receipt-conversion costs and downstream "
        "receipts. They do not measure protocol revenue, permanent token "
        "burning or value accruing to holders. Their scope differs from the "
        "network-wide costs grouped by execution date in the Execution costs tab."
    )

    with st.expander("Inspect and download selected-account costs"):
        st.dataframe(
            selected_costs,
            hide_index=True,
            width="stretch",
        )
        st.download_button(
            "Download selected-account costs",
            data=selected_costs.to_csv(index=False).encode("utf-8"),
            file_name=(
                f"27_{selected_account}_initial_receipt_costs_{PERIOD}.csv"
            ),
            mime="text/csv",
        )

    st.subheader("What did the sampled failures report?")

    diagnostic_table = pd.DataFrame(
        [
            {
                "Reported execution error": message,
                "Sampled receipts": count,
            }
            for message, count in error_messages.most_common()
        ]
    )

    st.dataframe(
        diagnostic_table,
        hide_index=True,
        width="stretch",
    )
    st.write(
        "All 18 sampled failed receipts executed on v2.ref-finance.near: "
        "17 reported E68 slippage errors and one reported E22 insufficient "
        "deposited tokens. These are reported contract errors, not a diagnosis "
        "of the operators' intentions."
    )
    st.caption(
        "The sample covers three selected receipts per active week for "
        "tinykoala595.near. It does not estimate error frequencies across "
        "all 715,518 failures, establish retries, or identify automation. "
        "Sources: saved results 25 and 26."
    )

    with st.expander("Inspect the sampled receipt evidence"):
        evidence = pd.DataFrame(
            [
                {
                    "Transaction hash":
                        record["sample"]["transaction_hash"],
                    "Receipt ID":
                        record["sample"]["receipt_id"],
                    "Executor":
                        record["matched_receipt"]["executor_id"],
                    "Execution error": "; ".join(
                        record["matched_receipt"]["execution_errors"]
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
        data=contributions.to_csv(index=False).encode("utf-8"),
        file_name=f"22_account_growth_contributions_{PERIOD}.csv",
        mime="text/csv",
    )


with returns_tab:
    st.subheader("Did accounts participate in later weeks?")
    st.write(
        "Each cohort contains all signing accounts active in its "
        "starting week. Cells show the percentage active in a "
        "particular later week."
    )

    heatmap = returns.pivot(
        index="cohort_week",
        columns="week_offset",
        values="cohort_active_share_pct",
    ).sort_index()

    heatmap = heatmap.reindex(columns=range(5))
    heatmap.index = heatmap.index.strftime("%d %b %Y")
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
    fig.update_traces(hoverongaps=False)
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Blank cells have no complete follow-up week. They are not "
        "zero returns. Cohorts overlap and do not represent newly "
        "acquired users. Participation need not be continuous."
    )

    with st.expander("Inspect cohort results"):
        st.dataframe(
            returns,
            hide_index=True,
            width="stretch",
        )

    st.info(
        "Account deletion changes how these returns should be read. "
        "During 28 September–4 October, 309,280 accounts absent the "
        "following week had successful receipt executions containing "
        "self-deletion actions. They represented 82.53% of the absent "
        "group. This absence should not be interpreted as ordinary "
        "user churn. Reasons for deletion and later account recreation "
        "remain unverified."
    )

    st.subheader("The spike: account counts versus transaction activity")
    st.write(
        "Among accounts active during 28 September–4 October, "
        "how much starting-week activity came from accounts "
        "that participated again during 5–11 October?"
    )

    group_labels = {
        "ACTIVE_FOLLOWING_WEEK": "Active the following week",
        "NOT_ACTIVE_FOLLOWING_WEEK": "Absent the following week",
    }

    group_summary = group_summary.copy()
    group_summary["Participation"] = group_summary[
        "return_group"
    ].map(group_labels)

    account_total = group_summary["group_accounts"].sum()
    transaction_total = group_summary["group_transactions"].sum()

    group_summary["Share of accounts (%)"] = (
        100 * group_summary["group_accounts"] / account_total
    )
    group_summary["Share of starting-week transactions (%)"] = (
        100 * group_summary["group_transactions"] / transaction_total
    )

    returned = group_summary.loc[
        group_summary["return_group"].eq("ACTIVE_FOLLOWING_WEEK")
    ].iloc[0]

    left, right = st.columns(2)

    left.metric(
        "Accounts active the following week",
        f"{returned['Share of accounts (%)']:.2f}%",
    )
    right.metric(
        "Their share of starting-week transactions",
        f"{returned['Share of starting-week transactions (%)']:.2f}%",
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
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "The two groups cover the same starting-week cohort. "
        "Account shares and transaction shares have different "
        "denominators. Absence the following week does not establish "
        "permanent departure, and accounts are not verified people."
    )

    with st.expander("Inspect spike cohort group totals"):
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
    st.subheader("How broadly was activity distributed?")

    signer_shares = {
        "top_1_account_transaction_share_pct":
            "Top signing account",
        "top_10_accounts_transaction_share_pct":
            "Top 10 signing accounts",
        "top_100_accounts_transaction_share_pct":
            "Top 100 signing accounts",
    }

    fig = px.line(
        weekly.rename(columns=signer_shares),
        x="week_start",
        y=list(signer_shares.values()),
        markers=True,
        labels={
            "week_start": "Week starting",
            "value": "Share of transactions (%)",
            "variable": "Group",
        },
    )
    fig.update_yaxes(range=[0, 100])
    show_weekly_chart(fig)

    st.caption(
        "Groups are nested and must not be added together. "
        "Accounts are ranked separately each week."
    )

    selected_week = st.selectbox(
        "Inspect transaction receivers for the week starting",
        options=weekly["week_start"].tolist(),
        format_func=lambda value: value.strftime("%d %B %Y"),
    )

    selected = receivers.loc[
        receivers["week_start"].eq(selected_week)
    ].sort_values("receiver_rank")

    if selected.empty:
        st.error("No receiver results are available for this week.")
        st.stop()

    receiver_summary = selected.iloc[0]
    left, right = st.columns(2)

    left.metric(
        "Top 10 receivers · transaction share",
        f"{receiver_summary['top_10_receiver_transaction_share_pct']:.2f}%",
    )
    right.metric(
        "Top 20 receivers · transaction share",
        f"{receiver_summary['top_20_receiver_transaction_share_pct']:.2f}%",
    )

    fig = px.bar(
        selected.sort_values("transactions"),
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
            "weekly_transaction_share_pct":
                "Share of weekly transactions (%)",
        },
        height=700,
    )
    fig.update_layout(
        yaxis=dict(categoryorder="total ascending"),
        margin=dict(t=30, b=40),
    )
    st.plotly_chart(fig, width="stretch")

    st.caption(
        "Only the twenty busiest original transaction receivers are "
        "shown. Absence from a ranking does not mean zero activity. "
        "Receiver-level signing-account counts can overlap."
    )

    with st.expander("Inspect receiver results"):
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
    st.subheader("Recorded receipt execution costs")

    cost_chart = weekly[
        [
            "week_start",
            "recorded_execution_cost_near",
            "failed_receipt_cost_near",
        ]
    ].copy()

    cost_chart["Non-failed receipt outcomes"] = (
        cost_chart["recorded_execution_cost_near"]
        - cost_chart["failed_receipt_cost_near"]
    )

    cost_chart = cost_chart.rename(
        columns={
            "failed_receipt_cost_near": "Failed receipt outcomes"
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
        "Costs exclude transaction receipt-conversion costs and do "
        "not establish protocol revenue or permanent token burning."
    )

    st.subheader("Failures: share of outcomes versus share of cost")

    failure_labels = {
        "failed_receipt_share_pct": "Failed share of outcomes",
        "failed_receipt_cost_share_pct": "Failed share of cost",
    }

    fig = px.line(
        weekly.rename(columns=failure_labels),
        x="week_start",
        y=list(failure_labels.values()),
        markers=True,
        labels={
            "week_start": "Week starting",
            "value": "Share (%)",
            "variable": "Metric",
        },
    )
    fig.update_yaxes(rangemode="tozero")
    show_weekly_chart(fig)


st.divider()

with st.expander("Inspect and download the combined weekly results"):
    st.dataframe(
        weekly,
        hide_index=True,
        width="stretch",
    )
    st.download_button(
        "Download weekly results",
        data=weekly.to_csv(index=False).encode("utf-8"),
        file_name=f"14_weekly_growth_and_costs_{PERIOD}.csv",
        mime="text/csv",
    )

st.caption(
    "Research in progress. Observed differences do not establish "
    "their causes, user churn or investment returns."
)