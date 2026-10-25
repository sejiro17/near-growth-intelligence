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
        raise ValueError("The spike cohort group totals are inconsistent.")

    starting_week = pd.Timestamp("2026-09-28")
    following_week = pd.Timestamp("2026-10-05")

    if (
        not spike["cohort_week"].eq(starting_week).all()
        or not spike["followup_week"].eq(following_week).all()
    ):
        raise ValueError("The spike cohort dates are inconsistent.")

    starting = weekly.loc[
        weekly["week_start"] == starting_week
    ]

    followup = returns.loc[
        (returns["cohort_week"] == starting_week)
        & (returns["week_offset"] == 1)
    ]

    if len(starting) != 1 or len(followup) != 1:
        raise ValueError("Unable to reconcile the spike cohort.")

    if (
        group_summary["group_accounts"].sum()
        != starting.iloc[0]["weekly_active_signing_accounts"]
        or group_summary["group_transactions"].sum()
        != starting.iloc[0]["transactions"]
    ):
        raise ValueError("The spike cohort totals do not reconcile.")

    returned_accounts = group_summary.loc[
        group_summary["return_group"] == "ACTIVE_FOLLOWING_WEEK",
        "group_accounts",
    ].iloc[0]

    if returned_accounts != followup.iloc[0]["active_cohort_accounts"]:
        raise ValueError("The spike return count does not reconcile.")

except (OSError, ValueError, KeyError) as error:
    st.error(f"Unable to load the research results: {error}")
    st.stop()


def show_weekly_chart(fig):
    fig.update_xaxes(
        tickmode="array",
        tickvals=weekly["week_start"].tolist(),
        ticktext=weekly["week_start"].dt.strftime("%d %b").tolist(),
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
        "Explore activity, account returns, concentration "
        "and recorded receipt execution costs."
    )
    st.caption(
        "This dashboard displays saved research exports. "
        "It is not a live network feed."
    )
    st.markdown(
        "**Reading the metrics**\n\n"
        "- Signing accounts are identifiers, not verified people.\n"
        "- Transaction receivers are not automatically applications.\n"
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

growth_tab, returns_tab, concentration_tab, costs_tab = st.tabs(
    ["Growth", "Account returns", "Concentration", "Execution costs"]
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
    group_summary["Participation"] = (
        group_summary["return_group"].map(group_labels)
    )

    account_total = group_summary["group_accounts"].sum()
    transaction_total = group_summary["group_transactions"].sum()

    group_summary["Share of accounts (%)"] = (
        100 * group_summary["group_accounts"] / account_total
    )
    group_summary["Share of starting-week transactions (%)"] = (
        100 * group_summary["group_transactions"] / transaction_total
    )

    returned = group_summary.loc[
        group_summary["return_group"] == "ACTIVE_FOLLOWING_WEEK"
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
        "top_1_account_transaction_share_pct": "Top signing account",
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

    selected = receivers[
        receivers["week_start"] == selected_week
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