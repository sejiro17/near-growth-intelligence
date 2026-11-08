import json
from collections import Counter
from decimal import Decimal
from math import isclose, isfinite
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
import research_views
import presentation
import model_views
import review_views


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"
EXTENDED_PERIOD = "2026-07-06_to_2026-10-18"

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
    "Failure": COLORS[3],
    "Success value": COLORS[0],
    "Success receipt ID": COLORS[1],
}

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = COLORS


def load_csv(filename, date_columns):
    frame = pd.read_csv(RESULTS / filename)

    if frame.empty:
        raise ValueError(f"{filename} is empty.")

    for column in date_columns:
        frame[column] = pd.to_datetime(
            frame[column], errors="raise"
        )
        if frame[column].isna().any():
            raise ValueError(f"Missing dates in {filename}: {column}")

    return frame


def close(a, b):
    return isclose(
        float(a), float(b), rel_tol=1e-12, abs_tol=1e-5
    )


def validate_numbers(frame, fields, nonnegative=False):
    for field in fields:
        frame[field] = pd.to_numeric(frame[field], errors="raise")

        if not frame[field].map(isfinite).all():
            raise ValueError(f"Nonfinite values in {field}.")

        if nonnegative and frame[field].lt(0).any():
            raise ValueError(f"Negative values in {field}.")


def validate_weeks(frame, name):
    expected = pd.date_range("2026-08-24", periods=8, freq="7D")

    if (
        len(frame) != 8
        or frame["week_start"].duplicated().any()
        or frame["week_start"].tolist() != expected.tolist()
        or not frame["week_end"].eq(
            frame["week_start"] + pd.Timedelta(days=6)
        ).all()
    ):
        raise ValueError(f"{name} does not cover eight complete weeks.")


def validate_extended_activity(extended, comparison, original):
    expected = pd.date_range("2026-07-06", periods=15, freq="7D")
    if (
        extended["week_start"].tolist() != expected.tolist()
        or not extended["week_end"].eq(
            extended["week_start"] + pd.Timedelta(days=6)
        ).all()
    ):
        raise ValueError("Extended activity must cover fifteen complete weeks.")

    fields = [field for field in original.columns
              if field not in ("week_start", "week_end")]
    validate_numbers(extended, [field for field in fields
                               if field != "weekly_active_accounts_change_pct"])
    counts = ["weekly_active_signing_accounts", "transactions",
              "signing_account_days", "accounts_active_one_day",
              "accounts_active_all_seven_days", "top_1_account_transactions",
              "top_10_accounts_transactions", "top_100_accounts_transactions"]
    for field in counts:
        if extended[field].lt(0).any() or extended[field].mod(1).ne(0).any():
            raise ValueError(f"Invalid extended count: {field}.")
    accounts = extended["weekly_active_signing_accounts"]
    transactions = extended["transactions"]
    days = extended["signing_account_days"]
    if (
        accounts.le(0).any() or transactions.le(0).any()
        or days.lt(accounts).any() or days.gt(7 * accounts).any()
        or days.gt(transactions).any()
        or (extended["accounts_active_one_day"]
            + extended["accounts_active_all_seven_days"]).gt(accounts).any()
    ):
        raise ValueError("Extended participation counts do not reconcile.")
    ratios = {
        "transactions_per_weekly_active_account": transactions / accounts,
        "average_active_days_per_account": days / accounts,
    }
    previous = extended["top_1_account_transactions"]
    for rank in (1, 10, 100):
        count = extended[f"top_{rank}_account{'s' if rank != 1 else ''}_transactions"]
        if count.lt(previous).any() or count.gt(transactions).any():
            raise ValueError("Extended concentration counts do not reconcile.")
        field = f"top_{rank}_account{'s' if rank != 1 else ''}_transaction_share_pct"
        ratios[field] = 100 * count / transactions
        previous = count
    for field, expected_ratio in ratios.items():
        if (extended[field] - expected_ratio).abs().gt(0.005001).any():
            raise ValueError(f"Extended ratio does not reconcile: {field}.")
    changes = pd.to_numeric(
        extended["weekly_active_accounts_change_pct"], errors="raise"
    )
    if not pd.isna(changes.iloc[0]) or (
        changes.iloc[1:] - 100 * (accounts / accounts.shift(1) - 1).iloc[1:]
    ).abs().gt(0.005001).any() or changes.iloc[1:].isna().any():
        raise ValueError("Extended weekly account changes do not reconcile.")

    overlap = extended.loc[extended["week_start"].isin(original["week_start"])]
    for field in original.columns:
        # The original first week has no previous week within its window.
        start = 1 if field == "weekly_active_accounts_change_pct" else 0
        if not overlap[field].iloc[start:].reset_index(drop=True).equals(
            original[field].iloc[start:].reset_index(drop=True)
        ):
            raise ValueError(f"Extended overlap differs from result 10: {field}.")

    def summary(frame):
        return {
            "average_weekly_transactions": frame["transactions"].sum() / 4,
            "average_weekly_active_signing_accounts":
                frame["weekly_active_signing_accounts"].sum() / 4,
            "active_days_per_active_account_week":
                frame["signing_account_days"].sum()
                / frame["weekly_active_signing_accounts"].sum(),
            "weekly_top_10_transaction_share_pct":
                100 * frame["top_10_accounts_transactions"].sum()
                / frame["transactions"].sum(),
        }

    first_summary = summary(extended.iloc[:4])
    final_summary = summary(extended.iloc[-4:])
    if len(comparison) != 4 or set(comparison["metric"]) != set(first_summary):
        raise ValueError("Unexpected four-week comparison metrics.")
    validate_numbers(comparison, [
        "weeks_per_period", "first_period_value", "final_period_value",
        "absolute_change", "relative_change_pct",
    ])
    for row in comparison.to_dict("records"):
        if (
            row["first_period_start"] != pd.Timestamp("2026-07-06")
            or row["first_period_end"] != pd.Timestamp("2026-08-02")
            or row["final_period_start"] != pd.Timestamp("2026-09-21")
            or row["final_period_end"] != pd.Timestamp("2026-10-18")
            or row["weeks_per_period"] != 4
        ):
            raise ValueError("Unexpected four-week comparison periods.")
        first_value = first_summary[row["metric"]]
        final_value = final_summary[row["metric"]]
        for field, value in {
            "first_period_value": first_value,
            "final_period_value": final_value,
            "absolute_change": final_value - first_value,
            "relative_change_pct": 100 * (final_value / first_value - 1),
        }.items():
            if not isfinite(float(row[field])) or abs(row[field] - value) > 0.000051:
                raise ValueError(f"Four-week comparison differs: {field}.")


def download_csv(label, frame, filename, *, source=None, filters=None):
    st.download_button(
        label,
        data=(presentation.saved_csv(source, filters) if source
              else frame.to_csv(index=False).encode("utf-8")),
        file_name=filename,
        mime="text/csv",
    )


try:
    research = research_views.load_evidence(research_views.signature())
    review = review_views.load_evidence(review_views.signature())
    weekly = load_csv(
        f"14_weekly_growth_and_costs_{PERIOD}.csv",
        ["week_start", "week_end"],
    ).sort_values("week_start").reset_index(drop=True)

    extended = load_csv(
        f"38_extended_weekly_signing_activity_{EXTENDED_PERIOD}.csv",
        ["week_start", "week_end"],
    ).sort_values("week_start").reset_index(drop=True)
    extended_comparison = load_csv(
        f"39_extended_activity_comparison_{EXTENDED_PERIOD}.csv",
        ["first_period_start", "first_period_end",
         "final_period_start", "final_period_end"],
    )
    original_signing = load_csv(
        f"10_weekly_signing_activity_{PERIOD}.csv",
        ["week_start", "week_end"],
    ).sort_values("week_start").reset_index(drop=True)
    validate_weeks(original_signing, "Original signing activity")
    validate_extended_activity(extended, extended_comparison, original_signing)
    for field in original_signing.columns:
        if not original_signing[field].equals(weekly[field]):
            raise ValueError(f"Result 10 differs from result 14: {field}.")

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
    ).sort_values("week_start").reset_index(drop=True)

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
        ["week_start", "week_end", "opening_supply_baseline_date"],
    ).sort_values("week_start").reset_index(drop=True)

    spending = load_csv(
        f"37_weekly_execution_spending_{PERIOD}.csv",
        ["week_start", "week_end"],
    ).sort_values("week_start").reset_index(drop=True)

    for frame, name in [
        (weekly, "Weekly activity"),
        (fixed, "Fixed-account results"),
        (economics, "Economic comparison"),
        (spending, "Execution spending"),
    ]:
        validate_weeks(frame, name)

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
    validate_numbers(economics, economic_fields)

    economic_pairs = {
        "transactions": "transactions",
        "weekly_active_signing_accounts":
            "weekly_active_signing_accounts",
        "receipt_execution_outcomes": "receipt_execution_outcomes",
        "recorded_receipt_execution_cost_near":
            "recorded_execution_cost_near",
    }

    for economic_field, weekly_field in economic_pairs.items():
        if not all(
            close(a, b)
            for a, b in zip(
                economics[economic_field], weekly[weekly_field]
            )
        ):
            raise ValueError(
                f"Economic results differ for {economic_field}."
            )

    previous_close = None

    for row in economics.to_dict("records"):
        if row["opening_supply_baseline_date"] != (
            row["week_start"] - pd.Timedelta(days=1)
        ):
            raise ValueError("Unexpected opening supply baseline date.")

        if min(
            row["opening_observed_supply_near"],
            row["closing_observed_supply_near"],
            row["receipt_execution_outcomes"],
        ) <= 0:
            raise ValueError("Supply and receipt counts must be positive.")

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
                row["positive_supply_movements_minus_validator_change_near"],
            ),
            (
                row["recorded_receipt_execution_cost_near"]
                / row["receipt_execution_outcomes"],
                row["average_recorded_cost_per_receipt_near"],
            ),
        ]

        if previous_close is not None:
            checks.append(
                (previous_close, row["opening_observed_supply_near"])
            )

        if not all(close(a, b) for a, b in checks):
            raise ValueError("Economic arithmetic does not reconcile.")

        previous_close = row["closing_observed_supply_near"]

    spending_fields = [
        "transactions",
        "receipt_execution_outcomes",
        "recorded_conversion_cost_near",
        "recorded_receipt_execution_cost_near",
        "combined_recorded_execution_spending_near",
        "conversion_share_of_recorded_spending_pct",
        "receipt_share_of_recorded_spending_pct",
    ]
    validate_numbers(spending, spending_fields, nonnegative=True)

    for field in [
        "transactions",
        "receipt_execution_outcomes",
        "recorded_receipt_execution_cost_near",
    ]:
        if not all(
            close(a, b)
            for a, b in zip(spending[field], economics[field])
        ):
            raise ValueError(
                f"Execution spending differs from result 34: {field}."
            )

    for row in spending.to_dict("records"):
        combined = row["combined_recorded_execution_spending_near"]

        if (
            combined <= 0
            or row["transactions"] <= 0
            or row["receipt_execution_outcomes"] <= 0
        ):
            raise ValueError("Spending and activity totals must be positive.")

        checks = [
            (
                row["recorded_conversion_cost_near"]
                + row["recorded_receipt_execution_cost_near"],
                combined,
            ),
            (
                100 * row["recorded_conversion_cost_near"] / combined,
                row["conversion_share_of_recorded_spending_pct"],
            ),
            (
                100 * row["recorded_receipt_execution_cost_near"] / combined,
                row["receipt_share_of_recorded_spending_pct"],
            ),
            (
                row["conversion_share_of_recorded_spending_pct"]
                + row["receipt_share_of_recorded_spending_pct"],
                100,
            ),
        ]

        if not all(close(a, b) for a, b in checks):
            raise ValueError("Combined execution spending does not reconcile.")

    if (
        not fixed["network_transactions"].eq(
            weekly["transactions"]
        ).all()
        or not (
            fixed["fixed_group_transactions"]
            + fixed["outside_fixed_group_transactions"]
        ).eq(fixed["network_transactions"]).all()
    ):
        raise ValueError("Fixed-account totals do not reconcile.")

    if leading.duplicated(["week_start", "signer_account_id"]).any():
        raise ValueError("Duplicate leading-account records.")

    expected_weeks = set(weekly["week_start"])

    for _, group in leading.groupby("signer_account_id"):
        if len(group) != 8 or set(group["week_start"]) != expected_weeks:
            raise ValueError("Incomplete tracked-account weekly series.")

    if (
        contributions["first_week_transactions"].sum()
        != weekly.iloc[0]["transactions"]
        or contributions["final_week_transactions"].sum()
        != weekly.iloc[-1]["transactions"]
        or not (
            contributions["final_week_transactions"]
            - contributions["first_week_transactions"]
        ).eq(contributions["transaction_change"]).all()
    ):
        raise ValueError("Growth contributions do not reconcile.")

    if (
        not outcomes["initial_receipt_status"].isin(STATUS_LABELS).all()
        or not outcomes["executor_check"].eq(
            "EXECUTOR_MATCHES_RECEIVER"
        ).all()
        or not outcomes["matched_outcome_rows"].eq(
            outcomes["transactions"]
        ).all()
    ):
        raise ValueError("Unexpected initial receipt matching results.")

    for (week, account), group in outcomes.groupby(
        ["week_start", "signer_account_id"]
    ):
        expected = leading.loc[
            leading["week_start"].eq(week)
            & leading["signer_account_id"].eq(account),
            "transactions",
        ]

        if len(expected) != 1 or group["transactions"].sum() != expected.iloc[0]:
            raise ValueError("Account outcome totals do not reconcile.")

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
        raise ValueError("Invalid or duplicate selected-account costs.")

    validate_numbers(
        account_costs,
        ["recorded_initial_receipt_cost_near"],
        nonnegative=True,
    )

    cost_counts = account_costs.set_index(
        cost_keys
    )["transactions"].sort_index()

    outcome_counts = outcomes.set_index(
        cost_keys
    )["transactions"].sort_index()

    if not cost_counts.equals(outcome_counts):
        raise ValueError("Selected-account costs differ from result 24.")

    diagnostic_path = RESULTS / (
        f"26_growth_account_failure_details_{PERIOD}.json"
    )
    diagnostics = json.loads(
        diagnostic_path.read_text(encoding="utf-8")
    )
    records = diagnostics["records"]

    if (
        len(records) != 18
        or len({
            record["sample"]["receipt_id"] for record in records
        }) != 18
    ):
        raise ValueError("Expected 18 distinct diagnostic receipts.")

    for record in records:
        sample = record["sample"]
        matched = record["matched_receipt"]

        if (
            record["retrieval_status"] != "VALIDATED_FAILURE"
            or matched["receipt_id"] != sample["receipt_id"]
            or matched["executor_id"] != sample["executor_account_id"]
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
        count for message, count in error_messages.items()
        if "E68:" in message
    )
    deposit_count = sum(
        count for message, count in error_messages.items()
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
        raise ValueError("Diagnostic evidence differs from the sample.")

    group_summary = spike[
        ["return_group", "group_accounts", "group_transactions"]
    ].drop_duplicates()

    if (
        len(group_summary) != 2
        or set(group_summary["return_group"]) != {
            "ACTIVE_FOLLOWING_WEEK",
            "NOT_ACTIVE_FOLLOWING_WEEK",
        }
    ):
        raise ValueError("Inconsistent spike cohort group totals.")

    starting_week = pd.Timestamp("2026-09-28")
    following_week = pd.Timestamp("2026-10-05")

    if (
        not spike["cohort_week"].eq(starting_week).all()
        or not spike["followup_week"].eq(following_week).all()
    ):
        raise ValueError("Inconsistent spike cohort dates.")

    starting = weekly.loc[weekly["week_start"].eq(starting_week)]
    followup = returns.loc[
        returns["cohort_week"].eq(starting_week)
        & returns["week_offset"].eq(1)
    ]

    if len(starting) != 1 or len(followup) != 1:
        raise ValueError("Unable to reconcile the spike cohort.")

    if (
        group_summary["group_accounts"].sum()
        != starting.iloc[0]["weekly_active_signing_accounts"]
        or group_summary["group_transactions"].sum()
        != starting.iloc[0]["transactions"]
    ):
        raise ValueError("Spike cohort totals do not reconcile.")

    returned_accounts = group_summary.loc[
        group_summary["return_group"].eq("ACTIVE_FOLLOWING_WEEK"),
        "group_accounts",
    ].iloc[0]

    if returned_accounts != followup.iloc[0]["active_cohort_accounts"]:
        raise ValueError("Spike return count does not reconcile.")

except (OSError, ValueError, KeyError, TypeError) as error:
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
    st.plotly_chart(fig, width="stretch", alt="Weekly " + (fig.layout.yaxis.title.text or "saved observations") + " during 24 August–18 October 2026")


def percentage_change(frame, field):
    first_value = float(frame.iloc[0][field])
    last_value = float(frame.iloc[-1][field])

    if first_value == 0:
        raise ValueError(f"Cannot calculate change from zero: {field}")

    return 100 * (last_value / first_value - 1)


first = weekly.iloc[0]
last = weekly.iloc[-1]

conversion_total = spending["recorded_conversion_cost_near"].sum()
receipt_total = spending["recorded_receipt_execution_cost_near"].sum()
combined_total = spending[
    "combined_recorded_execution_spending_near"
].sum()

combined_change = percentage_change(
    spending, "combined_recorded_execution_spending_near"
)
conversion_change = percentage_change(
    spending, "recorded_conversion_cost_near"
)
receipt_change = percentage_change(
    spending, "recorded_receipt_execution_cost_near"
)
conversion_share = 100 * conversion_total / combined_total

opening_supply = Decimal(research["supply"]["period"]["opening_supply_near"])
closing_supply = Decimal(research["supply"]["period"]["closing_supply_near"])
net_supply = Decimal(research["supply"]["period"]["net_supply_movement_near"])

top_ten_min = weekly["top_10_accounts_transaction_share_pct"].min()
top_ten_max = weekly["top_10_accounts_transaction_share_pct"].max()


st.title("NEAR Growth Intelligence")
research_views.overview(research)
review_views.opening(review)

st.markdown(
    "**Reading the comparisons · 2026 (UTC)**\n\n"
    "- **Eight-week research:** 24 August–18 October. "
    "Detailed growth, cohort, execution and economic analysis.\n"
    "- **Fifteen-week transaction context:** 6 July–18 October. "
    "Broader transaction activity and signing-account comparisons.\n"
    "- **Four-week averages:** 6 July–2 August versus 21 September–18 October. "
    "Two groups of four weeks within the transaction context, rather than "
    "individual endpoints."
)
st.caption(
    "Network calendar-period economics cover 24 August–18 October. "
    "Starting activity cohorts extend back to 10 August; bounded initial-receipt lookups extend through 24 October. "
    "Sources: saved public NEAR mainnet BigQuery exports and bounded canonical RPC captures."
)

with st.sidebar:
    st.header("About this research")
    st.write(
        "Explore activity, growth drivers, account returns, "
        "concentration, economic comparisons, decision priorities "
        "and selected account profiles."
    )
    st.caption(
        "The dashboard uses saved research exports rather than a live feed."
    )
    st.markdown(
        "**Reading the metrics**\n\n"
        "- Signing accounts are identifiers, not verified people.\n"
        "- Transaction receivers are not automatically applications.\n"
        "- Initial receipt outcomes do not establish complete "
        "execution-chain results.\n"
        "- Execution spending is separate from protocol revenue "
        "and holder returns.\n"
        "- The observation windows do not establish long-term adoption."
    )

st.subheader("Eight-week research · final week")
a, b, c = st.columns(3)

a.metric(
    "Transactions",
    f"{int(last['transactions']):,}",
    f"{percentage_change(weekly, 'transactions'):+.2f}% vs 24–30 August",
    delta_color="off",
)
b.metric(
    "Active signing accounts",
    f"{int(last['weekly_active_signing_accounts']):,}",
    (
        f"{percentage_change(weekly, 'weekly_active_signing_accounts'):+.2f}% "
        "vs 24–30 August"
    ),
    delta_color="off",
)
c.metric(
    "Combined execution spending",
    (
        f"{spending.iloc[-1]['combined_recorded_execution_spending_near']:,.2f}"
        " NEAR"
    ),
    f"{combined_change:+.2f}% vs 24–30 August",
    delta_color="off",
)
st.caption(
    "Final week: 12–18 October; changes compare with 24–30 August. "
    "Combined spending includes transaction receipt conversion "
    "and receipt execution recorded during the calendar period."
)

st.subheader("Investment assessment")
st.info(
    "Two August activity cohorts show exact +8 returns and successful initial-receipt execution with recorded spending. "
    "Concentration, failed execution, deletion context and declining longer-window endpoints qualify that evidence. "
    "The supply decomposition and the traced withdrawal's revenue origin remain unresolved. "
    "The conditional investment case has evidence of execution use, but no verified holder cash-flow valuation."
)

with st.expander(
    "What supports the assessment, and what would change it?"
):
    st.markdown(
        "**Participation · Eight-week research:** Final-week transactions were "
        f"{percentage_change(weekly, 'transactions'):+.2f}% versus "
        "the first week, while weekly active signing accounts were "
        f"{percentage_change(weekly, 'weekly_active_signing_accounts'):+.2f}%. "
        "Longer-term participation associated with verified account "
        "roles would strengthen the adoption argument."
    )
    st.markdown(
        "**Account lifecycle:** Successful self-deletion receipts "
        "appeared among 82.53% of accounts absent after the spike "
        "week. The following-week absence share is therefore not "
        "an ordinary user-churn rate."
    )
    st.markdown(
        "**Concentration · Eight-week research:** The ten busiest signing accounts "
        f"generated {top_ten_min:.2f}%–{top_ten_max:.2f}% of weekly "
        "transactions. Their roles matter when distinguishing "
        "shared infrastructure from independent participation."
    )
    st.markdown(
        f"**Execution use · Eight-week research:** Combined recorded spending totalled "
        f"**{combined_total:,.2f} NEAR**, comprising "
        f"{conversion_total:,.2f} NEAR in transaction conversion "
        f"and {receipt_total:,.2f} NEAR in receipt execution. "
        f"Weekly combined spending increased {combined_change:.2f}% "
        "between the endpoints."
    )
    st.markdown(
        "**Economic interpretation:** Execution expenditure measures "
        "token use during the period. It does not establish persistent "
        "holdings, net market buying, protocol revenue or holder "
        "returns. Supply increased during the same period, and "
        "the economic decomposition remains incompletely reconciled."
    )
    st.markdown(
        "**What would strengthen the case:** Persistent participation "
        "linked to identifiable applications, successful execution "
        "and reconciled evidence connecting usage to token demand "
        "and economic flows."
    )
    st.markdown(
        "**What would weaken the case:** Repeated growth dominated "
        "by temporary lifecycle activity, declining comparable-cohort "
        "participation, or dependence on a few participants without "
        "evidence of broader demand."
    )
    st.caption(
        "Sources: saved results 10–17, 21–27, 34, 37, 38 and 39. "
        "The repository contains the investment thesis and "
        "economic mechanisms note."
    )

(
    growth_tab,
    drivers_tab,
    returns_tab,
    concentration_tab,
    costs_tab,
    decisions_tab,
    explorer_tab,
) = st.tabs([
    "Growth",
    "Growth drivers",
    "Account returns",
    "Concentration",
    "Economics",
    "Decision priorities",
    "Account explorer",
])


with growth_tab:
    st.subheader("Fifteen-week transaction context")
    st.caption("6 July–18 October 2026 · Transaction activity only · Saved results 38 and 39")
    left, middle, right = st.columns(3)
    left.metric("Endpoint transactions",
                f"{percentage_change(extended, 'transactions'):+.2f}%")
    middle.metric("Endpoint active accounts",
                 f"{percentage_change(extended, 'weekly_active_signing_accounts'):+.2f}%")
    top_ten_endpoint_change = (
        extended.iloc[-1]["top_10_accounts_transaction_share_pct"]
        - extended.iloc[0]["top_10_accounts_transaction_share_pct"]
    )
    right.metric("Endpoint top-ten share",
                 f"{top_ten_endpoint_change:+.2f} pp".replace("-", "−"))
    st.caption("Endpoints compare 6–12 July with 12–18 October · pp = percentage points.")
    st.subheader("Four-week averages")
    labels = {
        "average_weekly_transactions": "Average weekly transactions",
        "average_weekly_active_signing_accounts": "Average weekly active signing accounts",
        "active_days_per_active_account_week": "Active days per active account-week",
        "weekly_top_10_transaction_share_pct": "Weekly top-ten transaction share (%)",
    }
    display = extended_comparison.copy()
    display["Measure"] = display["metric"].map(labels)
    display["Change"] = display.apply(
        lambda row: (f"{row['absolute_change']:+.2f} pp"
                     if row["metric"] == "weekly_top_10_transaction_share_pct"
                     else f"{row['relative_change_pct']:+.2f}%"), axis=1,
    )
    # Format a presentation copy; retain full precision in the source data.
    for field in ("first_period_value", "final_period_value"):
        display[field] = display[field].map(lambda value: f"{value:,.2f}")
    presentation.table(display.rename(columns={
        "first_period_value": "6 July–2 August",
        "final_period_value": "21 September–18 October",
    })[["Measure", "6 July–2 August", "21 September–18 October", "Change"]],
        hide_index=True, width="stretch")
    st.info(
        "The direction of growth depends on the comparison period: "
        "fifteen-week endpoints show declines, while first-four-week versus "
        "final-four-week averages show increases in transactions and accounts. "
        "The final four weeks include the account spike; figures are not "
        "adjusted for deletion activity and do not establish sustained adoption."
    )
    st.caption(
        "Average weekly accounts are not unique accounts across four weeks. "
        "Active days are weighted across account-weeks; top-ten shares are "
        "weighted by transactions, with membership ranked each week. "
        "These measures do not establish user retention or independent demand."
    )
    st.subheader("Eight-week research")
    st.caption("24 August–18 October 2026 · Network calendar-period economics. Separate cohort receipt lookups include six-day execution tails through 24 October.")
    st.subheader("Activity and spending followed different paths")
    st.write(
        "Compare changes from the first week, indexed to 100. "
        "An index of 150 means a value is 50% above its starting level."
    )

    indexed = weekly[
        ["week_start", "transactions", "weekly_active_signing_accounts"]
    ].copy()
    indexed["Combined recorded execution spending"] = spending[
        "combined_recorded_execution_spending_near"
    ]
    indexed = indexed.rename(columns={
        "transactions": "Transactions",
        "weekly_active_signing_accounts":
            "Weekly active signing accounts",
    })

    series = [
        "Transactions",
        "Weekly active signing accounts",
        "Combined recorded execution spending",
    ]
    for field in series:
        indexed[field] = 100 * indexed[field] / indexed.iloc[0][field]

    fig = px.line(
        indexed,
        x="week_start",
        y=series,
        markers=True,
        labels={
            "value": "Index · first week = 100",
            "variable": "Metric",
        },
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#888888")
    show_weekly_chart(fig)

    st.caption(
        "Conversion costs use transaction submission dates; receipt "
        "costs use execution dates. The index compares calendar-period "
        "trends rather than matched transaction-chain fees."
    )

    st.subheader("Weekly participation")
    show_weekly_chart(px.bar(
        weekly,
        x="week_start",
        y="weekly_active_signing_accounts",
        labels={
            "weekly_active_signing_accounts":
                "Distinct active signing accounts"
        },
    ))


with drivers_tab:
    st.caption("Eight-week research · 24 August–18 October 2026")
    st.subheader("Where did transaction growth come from?")
    st.write(
        "Keep the first week's ten busiest signing accounts fixed "
        "across all eight weeks, then compare their activity with "
        "every other account."
    )

    left, right = st.columns(2)
    left.metric(
        "First-week leaders · transaction change",
        f"{percentage_change(fixed, 'fixed_group_transactions'):+.2f}%",
    )
    right.metric(
        "All other accounts · transaction change",
        (
            f"{percentage_change(fixed, 'outside_fixed_group_transactions'):+.2f}%"
        ),
    )

    fixed_labels = {
        "fixed_group_transactions": "First-week top 10 accounts",
        "outside_fixed_group_transactions": "All other signing accounts",
    }
    show_weekly_chart(px.bar(
        fixed.rename(columns=fixed_labels),
        x="week_start",
        y=list(fixed_labels.values()),
        barmode="stack",
        labels={"value": "Transactions", "variable": "Account group"},
    ))
    st.caption(
        "Membership was selected during 24–30 August and stays fixed. "
        "This is an accounting comparison, not a counterfactual "
        "network without these accounts."
    )

    st.subheader("Contributions to the first-to-final-week change")
    group_names = {
        "FIRST_WEEK_TOP_10": "First-week top 10 accounts",
        "OTHER_TRACKED_ACCOUNT": "Other tracked accounts",
        "ALL_UNTRACKED_ACCOUNTS": "All untracked accounts combined",
    }
    contribution_groups = contributions.groupby(
        "comparison_group", as_index=False
    )[[
        "first_week_transactions",
        "final_week_transactions",
        "transaction_change",
    ]].sum()
    contribution_groups["Account group"] = (
        contribution_groups["comparison_group"].map(group_names)
    )

    st.plotly_chart(
        px.bar(
            contribution_groups,
            x="Account group",
            y="transaction_change",
            text_auto=",.0f",
            labels={"transaction_change": "Change in transactions"},
        ),
        width="stretch",
        alt="Changes in transactions by fixed first-week leaders, other tracked accounts and all untracked accounts",
    )
    st.caption(
        "Tracked accounts are the union of the weekly top 20. "
        "The untracked group combines all remaining accounts. "
        "The three changes sum to the network's net transaction change."
    )

    with st.expander("Inspect individual growth contributions"):
        display = contributions.copy()
        display["signer_account_id"] = display[
            "signer_account_id"
        ].fillna("All untracked accounts combined")
        presentation.table(
            display.sort_values("transaction_change", ascending=False),
            hide_index=True,
            width="stretch",
        )

    st.subheader("Inspect the accounts behind the counts")
    account_options = (
        leading.groupby("signer_account_id")["transactions"]
        .sum().sort_values(ascending=False).index.tolist()
    )
    chosen_account = st.selectbox(
        "Signing account",
        account_options,
        key="drivers_signing_account",
    )
    account_series = leading.loc[
        leading["signer_account_id"].eq(chosen_account)
    ].sort_values("week_start")
    show_weekly_chart(px.line(
        account_series,
        x="week_start",
        y="transactions",
        markers=True,
        labels={"transactions": "Transactions"},
    ))
    st.caption(
        "All eight weeks are included. An account name alone "
        "does not verify ownership, role or number of users."
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
                        fields, dropna=False, as_index=False
                    )[["transactions", "action_rows"]]
                    .sum().sort_values("transactions", ascending=False)
                )
                presentation.table(
                    action_totals, hide_index=True, width="stretch"
                )
                st.caption(
                    "Transactions can overlap across action categories. "
                    "These aggregate profiles do not expand DELEGATE_ACTION payloads; selected mechanisms are shown below. "
                    "Action records alone do not establish success."
                )

    st.subheader(
        "How did selected accounts' initial receipts execute?"
    )
    selected_account = st.selectbox(
        "Inspect initial receipt outcomes",
        sorted(outcomes["signer_account_id"].unique()),
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
    left.metric("Selected account · transactions", f"{total:,}")
    right.metric("Failed initial receipts", f"{failed / total:.2%}")

    plot_outcomes = account_outcomes.groupby(
        ["week_start", "initial_receipt_status"], as_index=False
    )["transactions"].sum()
    plot_outcomes["Initial receipt status"] = plot_outcomes[
        "initial_receipt_status"
    ].map(STATUS_LABELS)
    show_weekly_chart(px.bar(
        plot_outcomes,
        x="week_start",
        y="transactions",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={"transactions": "Transactions"},
    ))
    st.caption(
        "Each selected transaction matched one initial receipt outcome. "
        "SUCCESS_RECEIPT_ID does not establish downstream success. "
        "These selected accounts do not estimate network-wide failure "
        "rates. Weeks without transactions have no outcome bars."
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
    left.metric("All initial receipts", f"{total_cost:,.4f} NEAR")
    middle.metric("Failed initial-receipt spending", f"{failed_cost:,.4f} NEAR")
    right.metric(
        "Failed share of initial-receipt cost",
        f"{failed_cost / total_cost:.2%}" if total_cost > 0 else "N/A",
    )

    selected_costs["Initial receipt status"] = selected_costs[
        "initial_receipt_status"
    ].map(STATUS_LABELS)
    show_weekly_chart(px.bar(
        selected_costs,
        x="week_start",
        y="recorded_initial_receipt_cost_near",
        color="Initial receipt status",
        barmode="stack",
        color_discrete_map=STATUS_COLORS,
        labels={
            "recorded_initial_receipt_cost_near":
                "Recorded initial-receipt execution cost (NEAR)"
        },
    ))
    st.caption(
        "Initial receipts only, grouped by the originating transaction's "
        "submission week. Conversion and downstream receipt costs are "
        "excluded. These costs are already part of network receipt "
        "activity and must not be added to network totals again."
    )

    with st.expander("Inspect and download selected-account costs"):
        presentation.table(
            selected_costs, hide_index=True, width="stretch"
        )
        download_csv(
            "Download selected-account costs",
            selected_costs,
            f"27_{selected_account}_initial_receipt_costs_{PERIOD}.csv",
            source=f"27_growth_account_execution_costs_{PERIOD}.csv",
            filters={"signer_account_id": selected_account},
        )

    st.subheader("What did the sampled failures report?")
    diagnostic_table = pd.DataFrame([
        {
            "Reported execution error": message,
            "Sampled receipts": count,
        }
        for message, count in error_messages.most_common()
    ])
    presentation.table(
        diagnostic_table, hide_index=True, width="stretch"
    )
    st.write(
        "All 18 sampled failed receipts executed on v2.ref-finance.near: "
        "17 reported E68 slippage errors and one reported E22 "
        "insufficient deposited tokens."
    )
    st.caption(
        "Three selected receipts per active week for tinykoala595.near. "
        "The sample does not estimate error frequencies across all "
        "715,518 failures or establish retries, automation or intentions."
    )

    with st.expander("Inspect the sampled receipt evidence"):
        evidence = pd.DataFrame([
            {
                "Transaction hash": record["sample"]["transaction_hash"],
                "Receipt ID": record["sample"]["receipt_id"],
                "Executor": record["matched_receipt"]["executor_id"],
                "Execution error": "; ".join(
                    record["matched_receipt"]["execution_errors"]
                ),
            }
            for record in records
        ])
        presentation.table(evidence, hide_index=True, width="stretch")

    download_csv(
        "Download growth contributions",
        contributions,
        f"22_account_growth_contributions_{PERIOD}.csv",
        source=f"22_account_growth_contributions_{PERIOD}.csv",
    )


    review_views.attribution(review)


with returns_tab:
    research_views.persistent_activity(research, review["returner_execution_bounds"])
    st.caption("Original eight-week cohort series · 24 August–18 October 2026")
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
    ).sort_index().reindex(columns=range(5))
    heatmap.index = heatmap.index.strftime("%d %b %Y")
    heatmap.columns = [
        "Starting week", "Week +1", "Week +2", "Week +3", "Week +4"
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
    st.plotly_chart(fig, width="stretch", alt="Exact-week activity shares by overlapping starting-week cohort; incomplete follow-ups are blank")
    st.caption(
        "Blank cells lack a complete follow-up week; they are not zero "
        "returns. Cohorts overlap and are not newly acquired users. "
        "Participation need not be continuous."
    )

    with st.expander("Inspect cohort results"):
        presentation.table(returns, hide_index=True, width="stretch")

    st.info(
        "During 28 September–4 October, 309,280 accounts absent the "
        "following week had successful receipts containing self-deletion "
        "actions: 82.53% of the absent group. This absence is not an "
        "ordinary user-churn measure. Deletion reasons and later "
        "recreation remain unverified."
    )

    st.subheader("The spike: account counts versus transaction activity")
    st.write(
        "Among accounts active during 28 September–4 October, how "
        "much starting-week activity came from accounts active again "
        "during 5–11 October?"
    )

    group_labels = {
        "ACTIVE_FOLLOWING_WEEK": "Active the following week",
        "NOT_ACTIVE_FOLLOWING_WEEK": "Absent the following week",
    }
    group_summary = group_summary.copy()
    group_summary["Participation"] = group_summary[
        "return_group"
    ].map(group_labels)
    group_summary["Share of accounts (%)"] = (
        100 * group_summary["group_accounts"]
        / group_summary["group_accounts"].sum()
    )
    group_summary["Share of starting-week transactions (%)"] = (
        100 * group_summary["group_transactions"]
        / group_summary["group_transactions"].sum()
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
    fig.update_layout(xaxis_title=None, legend_title_text="")
    st.plotly_chart(fig, width="stretch", alt="Account share versus starting-week transaction share for spike accounts that returned or were absent the following week")
    st.caption(
        "The groups cover the same starting-week cohort. Account and "
        "transaction shares have different denominators. Absence does "
        "not establish permanent departure."
    )

    with st.expander("Inspect spike cohort group totals"):
        presentation.table(
            group_summary[[
                "Participation",
                "group_accounts",
                "group_transactions",
                "Share of accounts (%)",
                "Share of starting-week transactions (%)",
            ]],
            hide_index=True,
            width="stretch",
        )


with concentration_tab:
    st.caption("Eight-week research · 24 August–18 October 2026")
    st.subheader("How broadly was activity distributed?")
    signer_shares = {
        "top_1_account_transaction_share_pct": "Top signing account",
        "top_10_accounts_transaction_share_pct": "Top 10 signing accounts",
        "top_100_accounts_transaction_share_pct": "Top 100 signing accounts",
    }
    fig = px.line(
        weekly.rename(columns=signer_shares),
        x="week_start",
        y=list(signer_shares.values()),
        markers=True,
        labels={"value": "Share of transactions (%)", "variable": "Group"},
    )
    fig.update_yaxes(range=[0, 100])
    show_weekly_chart(fig)
    st.caption(
        "Groups are nested and must not be added together. "
        "Accounts are ranked separately each week."
    )

    selected_week = st.selectbox(
        "Inspect transaction receivers for the week starting",
        weekly["week_start"].tolist(),
        format_func=lambda value: value.strftime("%d %B %Y"),
    )
    selected = receivers.loc[
        receivers["week_start"].eq(selected_week)
    ].sort_values("receiver_rank")

    if selected.empty:
        st.error("No receiver results are available for this week.")
    else:
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
        st.plotly_chart(fig, width="stretch", alt="Twenty leading original transaction receivers for the selected submission week")
        st.caption(
            "Only the twenty busiest original transaction receivers "
            "are shown. Absence from a ranking does not mean zero "
            "activity. Receiver-level signing-account counts can overlap."
        )

        with st.expander("Inspect receiver results"):
            presentation.table(
                selected[[
                    "receiver_rank",
                    "receiver_account_id",
                    "transactions",
                    "signing_accounts",
                    "weekly_transaction_share_pct",
                ]],
                hide_index=True,
                width="stretch",
            )


with costs_tab:
    st.caption("Eight-week research · 24 August–18 October 2026")
    st.subheader("Recorded execution spending")
    st.write(
        "Combine transaction receipt-conversion costs and receipt "
        "execution costs recorded during 24 August–18 October 2026 (eight weeks)."
    )

    a, b, c = st.columns(3)
    a.metric("Combined spending · eight weeks", f"{combined_total:,.2f} NEAR")
    b.metric("Transaction conversion", f"{conversion_total:,.2f} NEAR")
    c.metric("Receipt execution", f"{receipt_total:,.2f} NEAR")

    a, b = st.columns(2)
    a.metric("Conversion share of spending", f"{conversion_share:.2f}%")
    b.metric(
        "First-to-final-week combined change",
        f"{combined_change:+.2f}%",
        delta_color="off",
    )

    spending_labels = {
        "recorded_conversion_cost_near": "Transaction conversion",
        "recorded_receipt_execution_cost_near": "Receipt execution",
    }
    show_weekly_chart(px.bar(
        spending.rename(columns=spending_labels),
        x="week_start",
        y=list(spending_labels.values()),
        barmode="stack",
        labels={
            "value": "Recorded execution spending (NEAR)",
            "variable": "Component",
        },
    ))
    st.caption(
        "Conversion uses transaction submission dates; receipt "
        "execution uses execution dates. This is calendar-period "
        "spending, not a matched transaction-chain fee calculation. "
        "Source: saved result 37."
    )

    st.markdown("#### What this means for token demand")
    st.write(
        "The measured expenditure shows NEAR being used for network "
        "execution. Expenditure is a flow: it does not establish how "
        "long tokens were held or how much was purchased on the market. "
        "Persistent holdings, net buying pressure, revenue and holder "
        "returns require separate evidence."
    )

    with st.expander("Inspect and download combined execution spending"):
        presentation.table(spending, hide_index=True, width="stretch")
        download_csv(
            "Download combined execution spending",
            spending,
            f"37_weekly_execution_spending_{PERIOD}.csv",
            source=f"37_weekly_execution_spending_{PERIOD}.csv",
        )

    st.subheader("Activity and spending changed at different rates")
    comparison_items = [
        ("Transactions", percentage_change(weekly, "transactions")),
        ("Receipt execution outcomes", percentage_change(
            economics, "receipt_execution_outcomes"
        )),
        ("Transaction conversion cost", conversion_change),
        ("Receipt execution cost", receipt_change),
        ("Combined execution spending", combined_change),
        ("Average cost per receipt", percentage_change(
            economics, "average_recorded_cost_per_receipt_near"
        )),
    ]
    changes = pd.DataFrame(
        comparison_items,
        columns=["Measure", "First-to-final-week change (%)"],
    )
    st.plotly_chart(
        px.bar(
            changes,
            x="Measure",
            y="First-to-final-week change (%)",
            text_auto=".2f",
        ),
        width="stretch",
        alt="First-to-final-week percentage changes in transactions, receipt outcomes and separate recorded spending components",
    )

    receipt_count_change = percentage_change(
        economics, "receipt_execution_outcomes"
    )
    average_cost_change = percentage_change(
        economics, "average_recorded_cost_per_receipt_near"
    )
    st.write(
        f"Receipt outcomes increased {receipt_count_change:.2f}% and "
        f"average recorded cost per receipt increased "
        f"{average_cost_change:.2f}%. Together, these describe the "
        f"{receipt_change:.2f}% increase in receipt execution costs. "
        f"Including conversion costs, combined spending increased "
        f"{combined_change:.2f}%."
    )
    st.caption(
        "These comparisons describe changes between the first and "
        "final weeks. They do not identify the contribution of gas "
        "prices, execution complexity or changes in operation mix."
    )

    st.subheader("Observed total-supply movement")
    left, right = st.columns(2)
    left.metric("Net observed supply change", f"{net_supply:+,.2f} NEAR")
    right.metric(
        "Change from opening supply",
        f"{100 * net_supply / opening_supply:+.4f}%",
    )
    show_weekly_chart(px.bar(
        economics,
        x="week_start",
        y="net_observed_supply_change_near",
        labels={
            "net_observed_supply_change_near":
                "Net observed supply change (NEAR)"
        },
    ))
    st.caption(
        "Each week compares the preceding Sunday's closing supply "
        "with the current Sunday's close. Total supply is not "
        "circulating supply. Spending must not be subtracted from "
        "supply movement to infer issuance or burning."
    )

    research_views.supply_and_trace(research)
    review_views.supply_and_wallets(review)

    with st.expander("Inspect and download the weekly economic comparison"):
        presentation.table(economics, hide_index=True, width="stretch")
        download_csv(
            "Download weekly economic comparison",
            economics,
            f"34_weekly_economic_comparison_{PERIOD}.csv",
            source=f"34_weekly_economic_comparison_{PERIOD}.csv",
        )

    st.subheader("Receipt execution costs by outcome")
    cost_chart = weekly[[
        "week_start",
        "recorded_execution_cost_near",
        "failed_receipt_cost_near",
    ]].copy()
    cost_chart["Non-failed receipt outcomes"] = (
        cost_chart["recorded_execution_cost_near"]
        - cost_chart["failed_receipt_cost_near"]
    )
    cost_chart = cost_chart.rename(columns={
        "failed_receipt_cost_near": "Failed receipt outcomes"
    })
    show_weekly_chart(px.bar(
        cost_chart,
        x="week_start",
        y=["Non-failed receipt outcomes", "Failed receipt outcomes"],
        barmode="stack",
        labels={
            "value": "Recorded receipt execution cost (NEAR)",
            "variable": "Outcome group",
        },
    ))
    st.caption(
        "Receipt execution only; transaction conversion is excluded "
        "from this outcome breakdown. Recorded costs do not measure "
        "protocol revenue or permanent token burning."
    )

    st.subheader("Failures: share of outcomes versus share of receipt cost")
    failure_labels = {
        "failed_receipt_share_pct": "Failed share of receipt outcomes",
        "failed_receipt_cost_share_pct": "Failed share of receipt cost",
    }
    fig = px.line(
        weekly.rename(columns=failure_labels),
        x="week_start",
        y=list(failure_labels.values()),
        markers=True,
        labels={"value": "Share (%)", "variable": "Metric"},
    )
    fig.update_yaxes(rangemode="tozero")
    show_weekly_chart(fig)


with decisions_tab:
    st.info("The published persistence measurements and bounded withdrawal-provenance investigation are complete within their stated limits. Supply reconciliation is ongoing. Full-window issuance, actual burn, revenue origin and holder cash flows remain unresolved investment inputs; no valuation or causal cohort effect is established.")
    model_views.render()
    review_views.deliverables(review)
    st.caption("Eight-week research · 24 August–18 October 2026")
    st.subheader("Turn the evidence into investigation priorities")
    st.write(
        "Choose what needs checking before relying on a growth claim, "
        "evaluating application activity or allocating support."
    )

    audience_guidance = {
        "Investors and research analysts":
            "Test adoption and economic claims before using them "
            "in an investment thesis. No valuation or expected-return "
            "forecast is provided.",
        "NEAR ecosystem teams":
            "Identify growth requiring lifecycle, account-role or "
            "execution-quality checks before allocating support.",
        "Application developers":
            "Use action patterns, receipt outcomes and reported "
            "errors to frame investigations.",
    }
    audience = st.selectbox(
        "Who are you researching for?", list(audience_guidance)
    )
    st.write(audience_guidance[audience])

    priorities = [
        {
            "Priority": "Check lifecycle before interpreting account returns",
            "Evidence":
                "309,280 accounts absent after the spike week had "
                "successful self-deletion receipts: 82.53% of the absent group.",
            "Decision implication":
                "The absence rate is not an ordinary user-churn measure.",
            "Next action":
                "Examine deletion, recreation and account roles before "
                "evaluating acquisition or retention.",
            "Evidence boundary":
                "Deletion motives, ownership and later recreation remain unverified.",
            "Sources": "Results 11, 16 and 17",
        },
        {
            "Priority": "Check execution quality behind growth",
            "Evidence":
                "tinykoala595.near had 715,518 failed initial receipts "
                "(91.90% of its transactions), costing approximately "
                "211.1629 NEAR.",
            "Decision implication":
                "More submissions and spending do not necessarily "
                "represent successful application interactions.",
            "Next action":
                "Review receipt outcomes and reported contract errors "
                "alongside transaction growth.",
            "Evidence boundary":
                "Selected accounts and eighteen diagnostic receipts "
                "do not establish network-wide error frequencies.",
            "Sources": "Results 22–27",
        },
        {
            "Priority": "Verify the roles behind concentration",
            "Evidence":
                f"Weekly top-ten signers generated {top_ten_min:.2f}%"
                f"–{top_ten_max:.2f}% of transactions. Leading-account "
                "records include delegated actions.",
            "Decision implication":
                "Signing concentration does not directly measure "
                "concentration among users or application owners.",
            "Next action":
                "Verify major account roles and delegated interactions.",
            "Evidence boundary":
                "Delegated payloads have not been expanded; names "
                "alone do not verify ownership.",
            "Sources": "Results 10, 18–20 and 35",
        },
        {
            "Priority": "Follow growth beyond the original leaders",
            "Evidence":
                "Transactions outside the first week's top ten rose "
                "52.50%, while the fixed leaders fell 19.83%. Untracked "
                "accounts contributed 43.80% of the outside group's net increase.",
            "Decision implication":
                "The original leaders do not explain all growth.",
            "Next action":
                "Investigate contributor roles, persistence and execution quality.",
            "Evidence boundary":
                "The untracked aggregate does not identify ordinary "
                "users. Contributions describe arithmetic changes.",
            "Sources": "Results 18 and 21–24",
        },
        {
            "Priority": "Connect execution use to measured economic flows",
            "Evidence":
                f"Combined spending totalled {combined_total:,.2f} NEAR "
                f"and increased {combined_change:.2f}% between the "
                "endpoints. Total supply increased approximately "
                "4.936 million NEAR across the period.",
            "Decision implication":
                "Execution expenditure demonstrates token use, but "
                "does not establish persistent holdings, net market "
                "buying or holder returns.",
            "Next action":
                "Keep expenditure and supply movement separate; "
                "identify and reconcile relevant economic flows.",
            "Evidence boundary":
                "Validator-update balances remain incompletely "
                "reconciled with supply. No complete valuation "
                "is provided. The conditional scenario model tests explicit assumptions; it does not resolve these missing inputs.",
            "Sources": "Results 28–34, 36 and 37",
        },
    ]

    chosen_priority = st.selectbox(
        "Choose an investigation priority",
        [item["Priority"] for item in priorities],
    )
    priority = next(
        item for item in priorities
        if item["Priority"] == chosen_priority
    )
    for field in ["Evidence", "Decision implication", "Next action"]:
        st.markdown(f"**{field}:** {priority[field]}")
    st.caption(
        f"Evidence boundary: {priority['Evidence boundary']} "
        f"Sources: {priority['Sources']}."
    )

    with st.expander("Compare all investigation priorities"):
        priority_table = pd.DataFrame(priorities)
        presentation.table(
            priority_table, hide_index=True, width="stretch"
        )
        download_csv(
            "Download decision priorities",
            priority_table,
            f"decision_priorities_{PERIOD}.csv",
        )

    st.caption(
        "Priorities are research interpretations rather than automated "
        "scores, application rankings or buy-and-sell signals."
    )


with explorer_tab:
    st.caption("Eight-week research · 24 August–18 October 2026")
    st.subheader("Account explorer")
    st.write(
        "Inspect selected signing accounts, their weekly activity, "
        "destinations and transaction actions. Profiles cover selected "
        "accounts rather than complete applications."
    )

    profile_path = RESULTS / f"35_account_profiles_{PERIOD}.json"

    try:
        document = json.loads(
            profile_path.read_text(encoding="utf-8")
        )
        profiles = document["profiles"]
        account_ids = [profile["account_id"] for profile in profiles]

        if not profiles or len(set(account_ids)) != len(account_ids):
            raise ValueError("Missing or duplicate account profiles.")

        expected_profile_weeks = set(
            weekly["week_start"].dt.strftime("%Y-%m-%d")
        )

        for profile in profiles:
            rows = profile["weekly"]

            if (
                len(rows) != 8
                or {row["week_start"] for row in rows}
                != expected_profile_weeks
            ):
                raise ValueError(
                    "Profile weeks do not match the observation period."
                )

            if sum(
                row["transactions"] for row in rows
            ) != profile["full_period_transactions"]:
                raise ValueError("Profile transaction totals do not reconcile.")

    except (OSError, ValueError, KeyError, TypeError) as error:
        st.error(f"Unable to load account profiles: {error}")

    else:
        accounts = {
            profile["account_id"]: profile for profile in profiles
        }
        selected_profile_account = st.selectbox(
            "Signing account", list(accounts), key="explorer_account"
        )
        profile = accounts[selected_profile_account]

        st.markdown("**Evidence status:** " + profile["evidence_status"])
        if profile.get("service"):
            st.write("Associated service: " + profile["service"])
        st.write(profile["role"])

        if profile.get("source"):
            st.link_button("Open attribution source", profile["source"])

        st.caption(
            "Attribution reviewed "
            + document["attribution_review_date"]
            + ". Current sources do not independently prove "
            "historical ownership."
        )

        history = pd.DataFrame([
            {
                key: value for key, value in row.items()
                if key not in ("top_receivers", "action_categories")
            }
            for row in profile["weekly"]
        ]).sort_values("week_start")
        history["week_start"] = pd.to_datetime(history["week_start"])

        start_count = int(history.iloc[0]["transactions"])
        end_count = int(history.iloc[-1]["transactions"])

        c1, c2, c3 = st.columns(3)
        c1.metric(
            "Transactions signed · eight weeks",
            f"{profile['full_period_transactions']:,}",
        )
        c2.metric("Final-week transactions", f"{end_count:,}")
        c3.metric(
            "First-to-final-week change",
            (
                f"{100 * (end_count / start_count - 1):+.2f}%"
                if start_count else "Not defined"
            ),
            delta_color="off",
        )

        show_weekly_chart(px.line(
            history,
            x="week_start",
            y="transactions",
            markers=True,
            labels={"transactions": "Transactions signed"},
        ))
        show_weekly_chart(px.bar(
            history,
            x="week_start",
            y="network_transaction_share_pct",
            labels={
                "network_transaction_share_pct":
                    "Network transaction share (%)"
            },
        ))

        profile_weeks = {
            row["week_start"]: row for row in profile["weekly"]
        }
        selected_profile_week = st.selectbox(
            "Inspect a week",
            sorted(profile_weeks),
            format_func=lambda value: (
                value + " to " + profile_weeks[value]["week_end"]
            ),
            key="explorer_week",
        )
        chosen_week = profile_weeks[selected_profile_week]

        st.markdown("#### Transaction destinations")
        st.caption(
            "Weekly top 20 original receivers, not a complete "
            "downstream execution trace."
        )
        presentation.table(
            pd.DataFrame(chosen_week["top_receivers"]),
            hide_index=True,
            width="stretch",
        )
        st.write(
            "Transactions outside the top 20 destinations: "
            f"{chosen_week['outside_top_20_receiver_transactions']:,}. "
            f"Distinct receivers: {chosen_week['distinct_receivers']:,}."
        )

        st.markdown("#### Transaction actions")
        st.info(
            "A transaction can appear in several action categories. "
            "Category transaction counts must not be summed or "
            "interpreted as users."
        )
        presentation.table(
            pd.DataFrame(chosen_week["action_categories"]),
            hide_index=True,
            width="stretch",
        )
        st.write(
            "Transactions with action records: "
            f"{chosen_week['transactions_with_action_records']:,}. "
            "Without matching action records: "
            f"{chosen_week['transactions_without_action_records']:,}."
        )

        with st.expander("Measurement boundaries and profile export"):
            for boundary in document["measurement_boundaries"]:
                st.write("• " + boundary)
            st.caption(
                "Relayer signing-account participation does not measure "
                "the participation or retention of the people it serves."
            )
            st.download_button(
                "Download selected account profile",
                data=json.dumps(profile, indent=2, ensure_ascii=False),
                file_name=selected_profile_account + "_profile.json",
                mime="application/json",
                key="explorer_download",
            )


st.divider()

with st.expander("Inspect and download weekly activity and receipt costs"):
    presentation.table(weekly, hide_index=True, width="stretch")
    download_csv(
        "Download weekly activity and receipt costs",
        weekly,
        f"14_weekly_growth_and_costs_{PERIOD}.csv",
        source=f"14_weekly_growth_and_costs_{PERIOD}.csv",
    )

st.caption(
    "Observed differences do not establish their causes, "
    "user churn or investment returns."
)
