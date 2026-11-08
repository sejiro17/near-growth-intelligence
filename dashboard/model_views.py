"""Interactive conditional model; saved files and in-memory calculations only."""

import pandas as pd
import streamlit as st
from decimal import Decimal

if __package__:
    from . import conditional_model as model, model_review as review, presentation
else:
    import conditional_model as model
    import model_review as review
    import presentation


def fmt(value, places=2):
    if value is None:
        return "Unavailable"
    number = Decimal(value)
    return f"{number:.2E}" if number != 0 and abs(number) < Decimal(10)**(-places) else f"{number:,.{places}f}"


def signature():
    data = model.decode(model.ARTIFACT.read_bytes())
    checked = model.decode(review.ARTIFACT.read_bytes())
    paths = [model.ARTIFACT,review.ARTIFACT]+[model.ROOT/name for name in set(data["sources"])|set(checked["sources"])]
    return tuple((str(path),path.stat().st_mtime_ns,path.stat().st_size) for path in paths)


@st.cache_data(max_entries=2,show_spinner=False)
def load_saved(source_signature):
    review.verify_saved()
    return model.verify_saved()


def render():
    saved = load_saved(signature())
    st.subheader("Conditional investment model")
    st.write(saved["conclusion"])
    presentation.table(pd.DataFrame(saved["evidence_assessment"]),hide_index=True,width="stretch",alt="Evidence supporting and challenging the conditional investment thesis, with material qualifications")
    st.warning("Scenario calculations are economic thresholds, not expected investment returns. Measured product revenue, verified purchases and actual gross burn remain unavailable.")
    evidence = saved["evidence"]
    baseline = evidence["reward_baseline"]
    st.caption(f"Dated issuance baseline: {fmt(baseline['reward_mint_near'],6)} NEAR of protocol-validated reward minting during 21–27 September 2026 only. Additional issuance/subsidies are unavailable. Repeating this weekly amount is an explicit scenario.")
    st.info("Neardata bulk collection is paused. The archive returned a stated 30-block/minute restriction. Validated coverage is 144 blocks, 216877934–216878077; full-epoch/week accounting remains incomplete. No sampled debit is extrapolated.")
    with st.expander("Measured evidence and unresolved accounting"):
        rows = [
            {"Input": "Reward minting · 21–27 September", "Value": fmt(baseline["reward_mint_near"],6)+" NEAR", "Status": "Protocol-validated dated baseline"},
            {"Input": "Exact supply movement · same week", "Value": fmt(baseline["exact_supply_movement_near"],6)+" NEAR", "Status": "Endpoint observation"},
            {"Input": "Implied weekly debit", "Value": fmt(baseline["implied_weekly_net_debit_near"],6)+" NEAR", "Status": "Subtraction only; not independent debit or burn"},
            {"Input": "Three-wallet external native net · eight weeks", "Value": fmt(evidence["native_wallet_context"]["external_native_net_near"],6)+" NEAR", "Status": "Unclassified flow; not revenue or purchases"},
            {"Input": "Native stock-flow difference", "Value": fmt(evidence["native_wallet_context"]["unallocated_difference_near"],8)+" NEAR", "Status": "Unallocated; incomplete multi-asset coverage"},
            {"Input": "Actual gross burn / subsidies", "Value": "Unavailable", "Status": "Never replaced with zero or spending"},
            {"Input": "Attributable revenue / verified custody purchases", "Value": "Unavailable", "Status": "Closed withdrawal trace does not establish fee origin"},
        ]
        presentation.table(pd.DataFrame(rows),hide_index=True,width="stretch",alt="Measured dated baselines, unclassified flows and unavailable model inputs")
        st.caption("Persistent-activity populations overlap. Initial-receipt success is scoped to selected receipts with six-day tails; it does not establish complete-chain settlement. Execution spending is FLOAT-derived and is not a fee-revenue input to this model.")

    st.session_state.setdefault("conditional_applied_assumptions",dict(saved["assumptions"]))
    with st.expander("Edit scenario assumptions",expanded=False):
        st.caption("All numerical defaults are illustrative assumptions, except the dated reward observation repeated as a scenario. Rates and allocations are fractions: 0.001 means 0.1%, not a verified historical rate. Price is hypothetical USD/NEAR, not a live quote. Blank optional supply fields remain unavailable; an entered 0 is an explicit assumption.")
        with st.form("conditional_assumptions_form"):
            inputs = {}
            left,right = st.columns(2)
            for index,(key,(label,unit,optional)) in enumerate(model.FIELDS.items()):
                with (left if index%2==0 else right):
                    inputs[key] = st.text_input(f"{label} ({unit})",value=saved["assumptions"][key] or "",key="scenario_"+key,max_chars=90)
            submitted = st.form_submit_button("Apply scenario",key="apply_conditional_scenario")
        if submitted:
            candidate = {key: None if key in model.OPTIONAL and not value.strip() else value.strip() for key,value in inputs.items()}
            try:
                review.calculate(candidate)
            except ValueError as exc:
                st.error(f"Scenario not applied: {exc}")
            else:
                st.session_state["conditional_applied_assumptions"] = candidate
        st.caption("The applied assumptions remain in this browser session. Downloads include the applied values; no project file is edited.")

    result = review.applied_report(saved,st.session_state["conditional_applied_assumptions"])
    scenario, weekly = result["scenario"],result["scenario"]["weekly"]
    mode = "Illustrative default" if result["display_mode"]=="ILLUSTRATIVE_DEFAULT_SCENARIO" else "User-edited hypothetical"
    st.markdown(f"**{mode} scenario · weekly flows, not measured fee capture or verified revenue**")
    with st.container(horizontal=True):
        st.metric(f"{mode} · captured fee revenue", "$"+fmt(weekly["captured_fee_revenue_usd_per_week"])+" /week",border=True)
        st.metric(f"{mode} · purchased and destroyed", fmt(weekly["purchased_and_destroyed_near_per_week"])+" NEAR/week",border=True)
        st.metric(f"{mode} · purchased and held", fmt(weekly["purchased_and_held_near_per_week"])+" NEAR/week",border=True)
    st.caption("Captured revenue funds the displayed allocations; it is not an additional flow to add to them. Custody purchases do not destroy supply. Purchase/destruction is assumed here, not observed; price effects and investment returns are unmodeled.")
    budgets = [
        {"Use of captured budget": "Purchase and destruction", "USD/week": fmt(weekly["purchase_and_destruction_budget_usd_per_week"])},
        {"Use of captured budget": "Purchases held in custody", "USD/week": fmt(weekly["custody_purchase_budget_usd_per_week"])},
        {"Use of captured budget": "Remaining budget before costs/taxes", "USD/week": fmt(weekly["retained_budget_before_operating_costs_usd_per_week"])},
    ]
    for row in budgets:row["Basis"] = mode+" scenario"
    presentation.table(pd.DataFrame(budgets),hide_index=True,width="stretch",alt="Illustrative or user-edited mutually exclusive uses of one assumed captured-fee budget")
    st.write(f"{mode} scenario · conditional total supply change: "+fmt(weekly["conditional_supply_change_near_per_week"])+" NEAR/week.")
    if scenario["missing_supply_assumptions"]:
        st.caption("Full supply-neutral calculation is unavailable until additional issuance, other destruction and other supply adjustments are explicitly assumed. The reward-only threshold below excludes those unknowns.")
    labels = {
        "reward_only_activity_threshold": "Activity needed to offset dated reward minting only",
        "reward_only_capture_threshold": "Capture fraction needed to offset dated reward minting only",
        "retained_budget_activity_threshold": "Activity needed for chosen retained-budget hurdle",
        "retained_budget_capture_threshold": "Capture fraction needed for chosen retained-budget hurdle",
        "full_supply_neutral_activity_threshold": "Activity needed for full conditional supply neutrality",
    }
    rows = [{"Conditional threshold": labels[key],"Value":fmt(item["value"],4 if item["unit"]=="fraction" else 2),"Unit":item["unit"],"Status":item["status"].replace("_"," ").capitalize(),"Basis":mode+" scenario"} for key,item in scenario["thresholds"].items()]
    presentation.table(pd.DataFrame(rows),hide_index=True,width="stretch",alt="Economic activity and capture thresholds, including infeasible and unavailable cases")
    st.caption("These are arithmetic coverage hurdles, not investment break-even prices or expected returns. A required capture fraction above 1 is infeasible at the applied activity/price/allocation. Zero-coefficient targets can be unreachable; unavailable does not mean zero.")
    with st.expander("Sensitivity, equations and exact reproducibility"):
        st.caption(f"{mode} scenario · formula walkthrough. The target is dated epoch-reward minting only; total issuance including subsidies is unavailable.")
        walkthrough=[{**row,"Value":fmt(row["Value"],6),"Basis":mode+" scenario"} for row in result["formula_review"]["walkthrough"]]
        presentation.table(pd.DataFrame(walkthrough),hide_index=True,width="stretch",alt="Illustrative or user-edited step-by-step reward-only activity threshold, with explicit units")
        sensitivity = [{"Scenario":x["scenario"],"Assumption value":x["changed_value"] or "Multiple / baseline","Revenue USD/week":fmt(x["weekly"].get("captured_fee_revenue_usd_per_week")),"Destroyed NEAR/week":fmt(x["weekly"].get("purchased_and_destroyed_near_per_week")),"Held NEAR/week":fmt(x["weekly"].get("purchased_and_held_near_per_week")),"Reward-only activity USD/week":fmt(x["thresholds"].get("reward_only_activity_threshold",{}).get("value")),"Retained-hurdle activity USD/week":fmt(x["thresholds"].get("retained_budget_activity_threshold",{}).get("value")),"Full conditional supply-neutral activity USD/week":fmt(x["thresholds"].get("full_supply_neutral_activity_threshold",{}).get("value")),"Basis":mode+" sensitivity scenario","Note":x["note"]} for x in result["sensitivity"]]
        presentation.table(pd.DataFrame(sensitivity),hide_index=True,width="stretch",alt="Illustrative or user-edited one-at-a-time sensitivity to each major assumption; no measured capture or return prediction")
        st.json({"scenario_classification":result["display_mode"],"applied_assumptions":result["assumptions"],"units":result["assumption_units"],"formulas":result["formulas"],"horizon_totals":scenario["horizon_totals"]})
        st.caption(result["numerical_method"])
        st.caption("Reproduce the original saved result 90 offline with analysis/38_conditional_investment_model.py --check. For reviewed custom assumptions use analysis/39_review_model_and_attribution.py --assumptions <file> --output <unused-file>; existing results are never overwritten.")
        st.caption("Unified integration reproduction: .venv/bin/python -B analysis/44_rebuild_integrated_research.py --check. Result 90 remains unchanged; result 91 adds this reviewed walkthrough, allocation guard and expanded sensitivity.")
    with st.expander("Measurable conditions for changing the thesis"):
        presentation.table(pd.DataFrame(result["change_of_mind_conditions"]),hide_index=True,width="stretch",alt="Analyst-selected measurable thesis conditions, distinct from observed outcomes")
    st.download_button("Download applied conditional scenario (JSON)",data=model.json_bytes(result),file_name="conditional_scenario_applied.json",mime="application/json",key="conditional_scenario_download")
