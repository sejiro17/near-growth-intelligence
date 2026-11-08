"""Presentation of validated, saved research; no source requests or fee models."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__:
    from . import presentation
else:
    import presentation


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results/62_integrated_research_evidence.json"
NAMES = {"AUG10_EXACT_WEEK8": "10 August · exact +8", "AUG10_REPEATED_CHECKPOINTS": "10 August · all checkpoints",
         "SEP28_EXACT_WEEK1": "28 September · exact +1", "EXACT_WEEK_8_RETURNERS": "17 August · exact +8",
         "REPEATED_CHECKPOINT_RETURNERS": "17 August · all checkpoints"}


def fmt(value, places=2, suffix=""):
    return "Unavailable" if value is None else f"{Decimal(value):,.{places}f}{suffix}"


def signature():
    data = json.loads(ARTIFACT.read_bytes())
    paths = [ARTIFACT, *(ROOT / name for name in data["sources"])]
    return tuple((str(p.relative_to(ROOT)), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)


@st.cache_data(max_entries=2, show_spinner=False)
def load_evidence(source_signature):
    data = json.loads(ARTIFACT.read_bytes())
    if data.get("schema_version") != 1 or data.get("measurement_phase") != "CLOSED_WITH_STATED_LIMITATIONS":
        raise ValueError("The integrated evidence is not a validated measurement release")
    for relative, expected in data["sources"].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT / "results"):
            raise ValueError("Evidence source is outside the saved results directory")
        raw = path.read_bytes()
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError(f"Saved evidence changed: {relative}")
    if any(value is not None for value in data["unavailable"].values()):
        raise ValueError("Unmeasured economic claims were filled")
    return data


def overview(data):
    growth = {row["metric"]: row for row in data["growth_comparison"]}
    august = data["cohorts"][:2]
    a, _, september = data["shared_week"]["populations"]
    st.markdown("**What grew?** Four-week averages rose "
                f"{fmt(growth['average_weekly_transactions']['relative_change_pct'])}% for transactions and "
                f"{fmt(growth['average_weekly_active_signing_accounts']['relative_change_pct'])}% for signing accounts. "
                "Fifteen-week endpoints declined; the final four weeks include the account spike.")
    st.markdown("**How much persisted?** "
                f"{fmt(august[0]['checkpoint_return_shares_pct']['8'])}% and "
                f"{fmt(august[1]['checkpoint_return_shares_pct']['8'])}% of the 10 and 17 August cohorts returned at exact week +8. "
                "These are overlapping account cohorts; returner transactions are highly concentrated.")
    st.markdown("**What executed successfully?** Initial-receipt success was "
                f"{fmt(a['initial_success_share_pct'])}% for the August +8 group and "
                f"{fmt(september['initial_success_share_pct'])}% for the September +1 group during 5–11 October. "
                "The groups overlap; descendant success is unmeasured.")
    st.markdown("**What economic demand or value capture is demonstrated?** Recorded spending establishes execution use. "
                "Fresh purchases, durable holdings and holder value capture are unmeasured; "
                "eight-week supply reconciliation and revenue attribution remain unresolved.")
    st.caption("NEAR mainnet · UTC 2026 · starting-week signing accounts, not verified people or newly acquired users. "
               "The population/cohort checkpoint uses saved results 39, 46, 54, 57, 59 and 61; the current review adds results through 106. "
               "Named evidence downloads preserve saved precision; table-toolbar exports contain presentation data.")
    with st.expander("Opening evidence and measurement scope"):
        for item in data["opening"]:
            answer = item["answer"].replace("Independent issuance and actual supply burn remain unavailable.",
                "Full-window independent issuance and actual supply burn remain unavailable; the dated reward week is shown separately.")
            answer = answer.replace("Descendant outcomes remain unavailable.", "For these cohort populations, descendant outcomes remain unavailable.")
            st.markdown(f"**{item['question']}** {answer}")
        st.caption("Economic unavailability in this checkpoint refers to the full eight-week accounting. "
                   "The ongoing supply investigation does not change these published window totals.")
        st.download_button("Download integrated research evidence (JSON)", data=ARTIFACT.read_bytes(),
                           file_name=ARTIFACT.name, mime="application/json", key="integrated_evidence_download")


def persistent_activity(data, execution_bounds):
    st.subheader("Persistence and scoped execution")
    st.caption("Starting-week activity cohorts · UTC · exact-week returns and all-three-checkpoint intersections")
    cohort_rows = []
    for row in data["cohorts"]:
        cohort_rows.append({"Starting week": row["cohort_week"], "Accounts": row["cohort_accounts"],
            "+1 return": fmt(row["checkpoint_return_shares_pct"]["1"], suffix="%"),
            "+4 return": fmt(row["checkpoint_return_shares_pct"]["4"], suffix="%"),
            "+8 return": fmt(row["checkpoint_return_shares_pct"]["8"], suffix="%"),
            "All +1/+4/+8": fmt(row["repeated_checkpoint_return_share_pct"], suffix="%")})
    presentation.table(pd.DataFrame(cohort_rows), hide_index=True, width="stretch", alt="Four activity cohorts with exact-week and all-three-checkpoint return shares; incomplete follow-ups are unavailable")
    st.info("Returning means starting-week membership plus activity in the selected exact week. Repeated means activity at all three +1/+4/+8 checkpoints, without requiring intervening weekly activity. Any-return unions are separate measures. Three incomplete checkpoints remain unavailable.")
    population_rows = []
    for group in (*data["shared_week"]["populations"], *data["october12_pilot"]["populations"]):
        row = group["observed"]
        success = group.get("initial_success_share_pct", group.get("successful_initial_receipt_share_pct"))
        denominator = next(p["observed_week_transactions"] for p in data["checkpoints"]
                           if p["followup_week"] == row["submission_week"] and p["measurement_available"])
        transaction_share = Decimal(100)*row["transactions"]/denominator
        population_rows.append({"Group": NAMES[group["population"]], "Submission week": row["submission_week"],
            "Accounts": row["observed_accounts"], "Transactions": row["transactions"],
            "Week transaction share": fmt(transaction_share, suffix="%"),
            "Initial success": fmt(success, suffix="%"), "Failed initial receipts": group["failed_initial_receipts"],
            "Conversion NEAR": row["recorded_conversion_spending_near"],
            "Initial receipt NEAR": row["complete_initial_receipt_spending_near"],
            "Unassessed receipts": row["unassessed_initial_receipts"]})
    populations = pd.DataFrame(population_rows)
    presentation.table(populations[["Group", "Submission week", "Accounts", "Transactions", "Week transaction share", "Initial success"]],
                       hide_index=True, width="stretch", alt="Overlapping returner groups with transaction contribution and initial-receipt success")
    overlap = data["shared_week"]["overlap"]
    st.warning("Some accounts belong to more than one returner group, so the group totals cannot be combined. "
               "Differences between groups are descriptive; they do not establish why accounts returned. "
               "Spending for the combined, deduplicated population is unavailable.")
    st.markdown("**Recorded spending for the same overlapping groups**")
    presentation.table(populations[["Group", "Submission week", "Conversion NEAR", "Initial receipt NEAR"]],
                       near_places=4, hide_index=True, width="stretch", alt="Separate recorded conversion and initial-receipt spending for overlapping groups")
    st.caption("Conversion uses submission weeks; initial-receipt spending uses actual execution dates and includes the six-day tails. "
               "Failed receipts are included; descendants are excluded. These are FLOAT-derived recorded costs, not revenue or fresh purchases.")
    st.markdown("**Concentration and contrary evidence.** The top ten returners contributed 73.98% and 75.12% of the August cohorts’ +8 transactions. The September +1 group’s top ten contributed 59.59%. Its initial-receipt failure rate was 17.65%; the August shared-week groups were 8.37% and 8.48%. The September account spike also has separately measured self-deletion context; low account return is not verified user churn.")
    st.caption("All selected initial receipts have one observed outcome and valid attribution/costs. "
               "This is observed-record consistency, not independent ingestion completeness or complete-chain success.")
    st.markdown("**Successful initial execution beyond the ten leading signers**")
    bound_rows = []
    for row in execution_bounds["populations"]:
        values = row["bounds"]
        bound_rows.append({"Starting cohort": row["cohort_week"], "Submission week": row["submission_week"],
            "Transactions outside own top ten": values["outside_top10_transactions"] if values else None,
            "Minimum successful initial receipts": values["successful_initial_receipts_outside_top10_lower"] if values else None,
            "Maximum successful initial receipts": values["successful_initial_receipts_outside_top10_upper"] if values else None,
            "Outside transaction success bounds": values["outside_initial_success_pct_lower_display"]+"%–"+values["outside_initial_success_pct_upper_display"]+"%" if values and values["outside_initial_success_pct_lower_display"] is not None else "Unavailable"})
    presentation.table(pd.DataFrame(bound_rows), hide_index=True, width="stretch",
                       alt="Separate August +8 populations: bounds on successful initial receipts outside each population's own top ten signers")
    st.caption("Where coverage controls pass, the lower counts establish a minimum number of successful initial receipts beyond each population’s own ten leading signers within observed coverage. "
               "These are bounds on transactions, not measured account-level success rates, broad human adoption or complete-chain settlement. "
               "The cohorts overlap and are not added. Missing or ambiguous coverage suppresses the bounds.")
    with st.expander("Methodology: overlap, execution dates and coverage"):
        st.markdown(f"During 5–11 October, {overlap['august_and_september_accounts']:,} accounts and "
                    f"{overlap['august_and_september_transactions']:,} transactions belong to both exact-return groups. "
                    "The August repeated-checkpoint group is a subset of the August +8 group. "
                    "Totals therefore overlap, and the different cohort starting dates and return horizons "
                    "do not support a causal comparison. Spending for either the union or the intersection "
                    "of the groups was not separately measured.")
        presentation.table(populations[["Group", "Submission week", "Failed initial receipts", "Unassessed receipts"]],
                           hide_index=True, width="stretch", alt="Failed and unassessed initial-receipt counts for each overlapping group")
        rows = []
        for group in (*data["shared_week"]["populations"], *data["october12_pilot"]["populations"]):
            for part in group["by_execution_date"]:
                rows.append({"Group": NAMES[group["population"]], "Execution date": part["execution_date"],
                    "Transactions": part["transactions"], "Valid-cost transactions": part["valid_cost_transactions"],
                    "Initial receipt NEAR": part["recorded_initial_receipt_spending_subtotal_near"]})
        presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Saved initial-receipt spending by actual execution date and overlapping population")
        st.write("Each submission week has a six-day execution tail: 12–17 October or 19–24 October. Each pilot has one distinct selected receipt in its tail, also present in its overlapping groups. The tails are partial UTC weeks. Elapsed follow-up varies by submission date; descendants are excluded.")
        statuses = [{"Group": NAMES[g["population"]], "Submission week": g["observed"]["submission_week"],
                     "Status": s["observed_initial_status"], "Transactions": s["transactions"],
                     "Initial receipt NEAR": s["recorded_initial_receipt_spending_subtotal_near"]}
                    for g in (*data["shared_week"]["populations"], *data["october12_pilot"]["populations"]) for s in g["by_status"]]
        presentation.table(pd.DataFrame(statuses), hide_index=True, width="stretch", alt="Initial-receipt status counts and costs, including failed execution")
        st.caption("Receipt-owner uniqueness covers four/five selected source transaction weeks. Initial success includes SUCCESS_VALUE and SUCCESS_RECEIPT_ID. "
                   "Zero link exclusions were reported. Source costs are FLOAT-derived; extra saved digits do not establish source accuracy.")
        st.caption("The exports contain aggregates and up to three diagnostic examples per bucket; complete account memberships, submission timestamps and every executor/height comparison cannot be independently reconstructed offline. Monetary totals become unavailable if matching/cost coverage fails.")
        st.write("For N population transactions, T transactions from that population's own top ten and S successful initial receipts, "
                 "outside success lies between max(0, S−T) and min(S, N−T). The denominator is N−T. "
                 "Lower percentages round down and upper percentages round up to two decimals. "
                 "Membership alignment uses reviewed, hashed SQL definitions and matching cohort/group controls; full row-level sets are not exported. "
                 "Spending outside the top ten is not estimated from these counts.")
        st.json(execution_bounds["populations"])
        bounds_file = ROOT/"results/105_returner_initial_success_outside_top10_bounds.json"
        st.download_button("Download exact outside-top-ten bounds (JSON)", data=bounds_file.read_bytes(),
                           file_name=bounds_file.name, mime="application/json", key="returner_bounds_download")


def supply_and_trace(data):
    st.subheader("Supply reconciliation remains open")
    supply = data["supply"]
    period, cancellation = supply["period"], supply["cancellation"]
    left, right = st.columns(2)
    left.metric("Supply minus raw validator change", fmt(period["residual_near"])+" NEAR")
    right.metric("Sum of absolute daily residuals", fmt(cancellation["sum_absolute_daily_residuals_near"])+" NEAR")
    st.write(f"The period residual is {fmt(cancellation['period_residual_as_pct_of_net_supply_change'])}% of net supply movement and {fmt(cancellation['period_residual_as_pct_of_opening_supply'], 6)}% of opening supply. Netting hides daily cancellation. The 23 September residual remains +11,427.31 NEAR.")
    labels = {"start": "Week starting", "opening_supply_near": "Opening supply NEAR", "closing_supply_near": "Closing supply NEAR",
        "net_supply_movement_near": "Net supply movement NEAR", "raw_validator_balance_change_near": "Raw validator change NEAR", "residual_near": "Residual NEAR"}
    rows = [{label: row[key] for key, label in labels.items()} for row in supply["weekly"]]
    presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Eight-week observational supply comparison with opening and closing supply, raw validator changes and unexplained residuals")
    canonical = supply["canonical_comparison"]
    st.warning(f"At two exact block hashes, {canonical['additional_validator_updates']:,} RPC validator updates were absent from selected BigQuery evidence; {canonical['blank_chunk_validator_updates_confirmed']:,} blank-chunk observations were valid updates. "
               "The ingestion cause is unconfirmed and the finding is limited to those blocks. Recovered updates are not adjustments to the original daily total.")
    st.caption("Full-window issuance and actual native supply burn remain unavailable. Validator balance changes are not issuance; "
               "execution spending and negative supply movements are not measured native destruction. Sources: results 42–46.")
    with st.expander("Exact supply comparisons and accounting limits"):
        st.json({"period_residual_near": period["residual_near"],
                 "sum_absolute_daily_residuals_near": cancellation["sum_absolute_daily_residuals_near"],
                 "witness_change_near": canonical["witness_change_near"]})
        st.write(canonical["hypothesis"])
        st.write(canonical["no_adjustment"])
        st.caption("The witness measures one account balance change. Decimal preserves saved FLOAT-derived digits; "
                   "the 0.00001 NEAR threshold checks saved arithmetic only, not source accuracy or economic reconciliation. "
                   "The eight-week decomposition remains open; the separate epoch pilot does not establish full-window coverage.")
    st.subheader("A verified withdrawal with unverified revenue origin")
    trace = data["withdrawal"]
    st.write(f"On 23 September, the native-transfer diagnostic found {trace['transfer_rows']:,} successful transfers to fefundsadmin.sputnik-dao.near, totalling {fmt(trace['amount_near'], 4)} NEAR. One traced payout of {fmt(trace['traced_withdrawal_near'], 4)} NEAR followed a successful signed internal transfer and native withdrawal after unwrapping.")
    st.warning(trace["limits"]+" A documented recipient, matching amount or successful withdrawal does not establish fee origin, a buyback or holder cash flow. The bounded provenance investigation is closed.")
    st.caption("All discovered payments remain economically unclassified. Native-only discovery excludes tokens and internal Verifier balances. "
               "Missing attribution is not evidence that distributions did not occur. Sources: results 47–54; one day and one candidate trace only.")
    with st.expander("Exact withdrawal amounts and attribution limits"):
        st.json({"discovered_native_transfers_near": trace["amount_near"],
                 "traced_withdrawal_near": trace["traced_withdrawal_near"], "revenue_origin": trace["revenue_origin"]})
        st.caption("A successful internal transfer and withdrawal establish a mechanism, not the withdrawn funds' revenue origin. "
                   "Internal mt_burn does not establish native NEAR destruction.")
    presentation.table(pd.DataFrame([
        {"Investment input": "Full-window issuance", "Status": "Unavailable", "Implication": "No reconciled issuance or fee-offset inflation estimate"},
        {"Investment input": "Actual supply burn", "Status": "Unavailable", "Implication": "No measured permanent destruction or burn-based valuation"},
        {"Investment input": "Revenue origin and holder distributions", "Status": "Unverified", "Implication": "No attributable revenue yield, buyback return or holder cash-flow valuation"},
        {"Investment input": "Persistent purchases and balance commitments", "Status": "Unmeasured", "Implication": "Recorded spending alone does not establish net buying or durable holdings"}
    ]), hide_index=True, width="stretch", alt="Unavailable investment-model inputs and the conclusions they prevent")
    st.caption("The revenue/buyback ledger, full issuance/burn reconciliation and broad relayer attribution remain incomplete. The Decision priorities view implements a separate conditional scenario model; it does not establish valuation or expected returns.")
