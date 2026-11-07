"""Presentation of validated, saved research; no source requests or fee models."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st


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
    for item in data["opening"]:
        st.markdown(f"**{item['question']}** {item['answer']}")
    st.caption("NEAR mainnet · saved research · activity cohorts are starting-week outer signers, not verified people or newly acquired users. Sources: results 39, 46, 54, 57, 59 and 61.")


def persistent_activity(data):
    st.subheader("Persistence and scoped execution")
    st.caption("Starting-week activity cohorts · UTC · exact-week returns and all-three-checkpoint intersections")
    cohort_rows = []
    for row in data["cohorts"]:
        cohort_rows.append({"Starting week": row["cohort_week"], "Accounts": row["cohort_accounts"],
            "+1 return": fmt(row["checkpoint_return_shares_pct"]["1"], suffix="%"),
            "+4 return": fmt(row["checkpoint_return_shares_pct"]["4"], suffix="%"),
            "+8 return": fmt(row["checkpoint_return_shares_pct"]["8"], suffix="%"),
            "All +1/+4/+8": fmt(row["repeated_checkpoint_return_share_pct"], suffix="%")})
    st.dataframe(pd.DataFrame(cohort_rows), hide_index=True, width="stretch", alt="Four activity cohorts with exact-week and all-three-checkpoint return shares; incomplete follow-ups are unavailable")
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
            "Conversion NEAR": fmt(row["recorded_conversion_spending_near"], 8),
            "Initial receipt NEAR": fmt(row["complete_initial_receipt_spending_near"], 8),
            "Unassessed receipts": row["unassessed_initial_receipts"]})
    st.dataframe(pd.DataFrame(population_rows), hide_index=True, width="stretch", alt="Overlapping returner groups with transactions, initial-receipt outcomes and separate recorded conversion and receipt spending")
    overlap = data["shared_week"]["overlap"]
    st.warning(f"These groups overlap. The shared 5–11 October week contains {overlap['august_and_september_accounts']:,} accounts and {overlap['august_and_september_transactions']:,} transactions in both exact-return groups. The August repeated-checkpoint population is a subset. Do not add totals or infer causal differences between horizons. Union/intersection spending is unavailable.")
    st.markdown("**Concentration and contrary evidence.** The top ten returners contributed 73.98% and 75.12% of the August cohorts’ +8 transactions. The September +1 group’s top ten contributed 59.59%. Its initial-receipt failure rate was 17.65%; the August shared-week groups were 8.37% and 8.48%. The September account spike also has separately measured self-deletion context; low account return is not verified user churn.")
    st.caption("All selected initial receipts in both execution pilots have one observed outcome, valid execution attribution and valid costs; no link exclusions were reported. This describes selected observed records, not independent ingestion completeness. Receipt-owner uniqueness covers four/five source transaction weeks. Initial success includes SUCCESS_VALUE and SUCCESS_RECEIPT_ID, not complete-chain success. Source costs are FLOAT-derived; extra decimal digits preserve arithmetic, not source accuracy.")
    with st.expander("Execution dates, statuses and coverage"):
        rows = []
        for group in (*data["shared_week"]["populations"], *data["october12_pilot"]["populations"]):
            for part in group["by_execution_date"]:
                rows.append({"Group": NAMES[group["population"]], "Execution date": part["execution_date"],
                    "Transactions": part["transactions"], "Valid-cost transactions": part["valid_cost_transactions"],
                    "Initial receipt NEAR": part["recorded_initial_receipt_spending_subtotal_near"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Exact saved initial-receipt spending by actual execution date and overlapping population")
        st.write("Each submission week has a six-day execution tail: 12–17 October or 19–24 October. Each pilot has one distinct selected receipt in its tail, also present in its overlapping groups. The tails are partial UTC weeks. Elapsed follow-up varies by submission date; descendants are excluded.")
        statuses = [{"Group": NAMES[g["population"]], "Submission week": g["observed"]["submission_week"],
                     "Status": s["observed_initial_status"], "Transactions": s["transactions"],
                     "Initial receipt NEAR": s["recorded_initial_receipt_spending_subtotal_near"]}
                    for g in (*data["shared_week"]["populations"], *data["october12_pilot"]["populations"]) for s in g["by_status"]]
        st.dataframe(pd.DataFrame(statuses), hide_index=True, width="stretch", alt="Initial-receipt status counts and costs, including failed execution")
        st.caption("The exports contain aggregates and up to three diagnostic examples per bucket; complete account memberships, submission timestamps and every executor/height comparison cannot be independently reconstructed offline. Monetary totals become unavailable if matching/cost coverage fails.")


def supply_and_trace(data):
    st.subheader("Supply reconciliation remains open")
    supply = data["supply"]
    period, cancellation = supply["period"], supply["cancellation"]
    left, right = st.columns(2)
    left.metric("Supply minus raw validator change", fmt(period["residual_near"], 8)+" NEAR")
    right.metric("Sum of absolute daily residuals", fmt(cancellation["sum_absolute_daily_residuals_near"], 8)+" NEAR")
    st.write(f"The period residual is {fmt(cancellation['period_residual_as_pct_of_net_supply_change'], 6)}% of net supply movement and {fmt(cancellation['period_residual_as_pct_of_opening_supply'], 8)}% of opening supply. Netting hides daily cancellation. The 23 September residual remains +11,427.31386968814 NEAR.")
    labels = {"start": "Week starting", "opening_supply_near": "Opening supply NEAR", "closing_supply_near": "Closing supply NEAR",
        "net_supply_movement_near": "Net supply movement NEAR", "raw_validator_balance_change_near": "Raw validator change NEAR", "residual_near": "Residual NEAR"}
    rows = [{label: row[key] for key, label in labels.items()} for row in supply["weekly"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Eight-week observational supply comparison with opening and closing supply, raw validator changes and unexplained residuals")
    canonical = supply["canonical_comparison"]
    st.warning(f"At two exact block hashes, {canonical['additional_validator_updates']} RPC validator updates were absent from selected BigQuery evidence; {canonical['blank_chunk_validator_updates_confirmed']} blank-chunk observations were valid updates. One parent/post witness measures exactly +{canonical['witness_change_near']} NEAR. {canonical['hypothesis']} {canonical['no_adjustment']}")
    st.caption("Independent issuance and actual native supply burn remain unavailable. Validator balance changes are not issuance; execution costs, negative supply movements and internal mt_burn are not measured native destruction. Decimal preserves saved digits from FLOAT-derived sources. The 0.00001 NEAR threshold checks saved arithmetic only. Sources: results 42–46.")
    st.subheader("A verified withdrawal with unverified revenue origin")
    trace = data["withdrawal"]
    st.write(f"On 23 September, the native-transfer diagnostic found {trace['transfer_rows']} successful transfers to fefundsadmin.sputnik-dao.near, totalling {trace['amount_near']} NEAR. One traced payout of {trace['traced_withdrawal_near']} NEAR followed a successful signed internal transfer and native withdrawal after unwrapping.")
    st.warning(trace["limits"]+" A documented recipient, matching amount or successful withdrawal does not establish fee origin, a buyback or holder cash flow. The bounded provenance investigation is closed.")
    st.caption("All discovered payments remain economically unclassified. Missing attribution is not evidence that distributions did not occur. Sources: results 47–54; one day and one candidate trace only.")
    st.dataframe(pd.DataFrame([
        {"Investment input": "Independent issuance", "Status": "Unavailable", "Implication": "No reconciled issuance or fee-offset inflation estimate"},
        {"Investment input": "Actual supply burn", "Status": "Unavailable", "Implication": "No measured permanent destruction or burn-based valuation"},
        {"Investment input": "Revenue origin and holder distributions", "Status": "Unverified", "Implication": "No attributable revenue yield, buyback return or holder cash-flow valuation"},
        {"Investment input": "Persistent purchases and balance commitments", "Status": "Unmeasured", "Implication": "Recorded spending alone does not establish net buying or durable holdings"}
    ]), hide_index=True, width="stretch", alt="Unavailable investment-model inputs and the conclusions they prevent")
    st.caption("The revenue/buyback ledger, full issuance/burn reconciliation, broad relayer attribution and conditional investment model remain incomplete. The input summary is not an implemented valuation model.")
