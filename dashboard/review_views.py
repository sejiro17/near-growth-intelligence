"""Current integrated measurements and selected mechanisms; saved files only."""

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
ARTIFACT = ROOT / "results/100_integrated_research_review.json"


def fmt(value, places=2):
    return "Unavailable" if value is None else f"{Decimal(value):,.{places}f}"


def signature():
    data = json.loads(ARTIFACT.read_bytes())
    paths = [ARTIFACT]+[ROOT/name for name in data["sources"]]
    return tuple((str(p.relative_to(ROOT)), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)


@st.cache_data(max_entries=2, show_spinner=False)
def load_evidence(source_signature):
    data = json.loads(ARTIFACT.read_bytes())
    if data.get("schema_version") != 1 or data.get("status") != "INTEGRATED_WITH_OPEN_DELIVERABLES":
        raise ValueError("Invalid integrated research review")
    for name, expected in data["sources"].items():
        path = (ROOT/name).resolve()
        if not path.is_relative_to(ROOT/"results"):
            raise ValueError("Review source is outside saved results")
        raw = path.read_bytes()
        if len(raw) != expected["bytes"] or hashlib.sha256(raw).hexdigest() != expected["sha256"]:
            raise ValueError(f"Saved review evidence changed: {name}")
    if any(x is not None for x in data["unavailable"].values()):
        raise ValueError("Unavailable economic measurement was filled")
    return data


def download(label, filename, key):
    path = ROOT/filename
    st.download_button(label, data=path.read_bytes(), file_name=path.name, mime="application/json", key=key)


def opening(data):
    st.caption("Current evidence adds one protocol-validated reward week, a three-wallet native ledger, "
               "selected Sweat/wx mechanisms and failed tinykoala controls. These do not establish "
               "population settlement, attributed revenue, full issuance/burn reconciliation or holder returns.")
    with st.expander("Current research review and offline reproduction"):
        st.write("The conditional model separates hypothetical revenue, purchase-and-destruction and custody purchases. "
                 "Measured economic gaps remain unavailable. The five-deliverable status is in Decision priorities.")
        st.code(".venv/bin/python -B analysis/44_rebuild_integrated_research.py --check", language="bash")
        st.caption(data["source_validation_scope"])
        download("Download current integrated evidence (JSON)", str(ARTIFACT.relative_to(ROOT)), "current_review_download")


def supply_and_wallets(data):
    st.subheader("One exact reward week; full supply accounting remains open")
    week, prefix = data["supply_week"], data["header_prefix"]
    with st.container(horizontal=True):
        st.metric("Epoch reward minting · 21–27 September", fmt(week["recorded_reward_maps_near"])+" NEAR")
        st.metric("Exact endpoint supply movement · same week", fmt(week["exact_supply_movement_near"])+" NEAR")
    st.write(f"All {week['application_epochs']} reward applications have historical protocol checks. "
             f"Their difference from supply movement is {fmt(week['conditional_reward_map_implied_weekly_net_debit_near'])} NEAR "
             "of implied net debit. It is not independently measured weekly debit or gross burn; subsidies remain unavailable.")
    st.info(f"Independent inclusion-timed header coverage is {prefix['produced_blocks']} blocks "
            f"({prefix['first_height']}–{prefix['last_height']}), with {fmt(prefix['net_debit_near'], 8)} NEAR net debit "
            "and zero integer arithmetic discrepancy. The prefix is not extrapolated; it has no independent canonical tail control.")
    with st.expander("Exact supply scopes and source precision"):
        st.json(week)
        st.json(prefix)
        st.caption("The 23 application-block debits total "+fmt(week["observed_boundary_header_debits_near"], 8)+
                   " NEAR. They overlap the prefix and are not added to it. Header net debit is not a gross burn/subsidy split. "
                   "Exact RPC integers are distinct from the FLOAT-derived eight-week observational comparison.")
        download("Download exact reward-week evidence (JSON)", "results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json", "reward_evidence_download")

    ledger = data["native_ledger"]
    st.subheader("Three-wallet native ledger · flows remain unclassified")
    st.write("24 August–18 October UTC · historical liquid-plus-locked endpoints and successful native action flows.")
    rows = [{"Wallet": r["account_id"], "Opening NEAR": r["opening_near"], "Closing NEAR": r["closing_near"],
             "Native inflow NEAR": r["inflow_near"], "Native outflow NEAR": r["outflow_near"],
             "Unallocated difference NEAR": r["residual_near"]} for r in ledger["wallets"]]
    presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch", near_places=4,
                       alt="Native wallet endpoints and flows; the 1cs stock-flow difference remains unallocated")
    st.warning(f"External native net inflow is {fmt(ledger['external_net_near'])} NEAR. "
               f"{ledger['internal_transfer_count']} internal transfers totalling {fmt(ledger['internal_transfer_near'])} NEAR "
               "cancel between these wallets and are excluded from external net inflow. "
               f"The group difference is {fmt(ledger['unallocated_residual_near'], 8)} NEAR, entirely unallocated at 1csfundsadmin. "
               "These flows do not establish revenue, purchases or burn; even a zero arithmetic difference does not prove a complete balance reconciliation.")
    st.caption("The native layer excludes token and internal Verifier balances; one known internal owner–asset comparison is shown separately below. "
               "The account named buybacks.multisignature.near does not establish buyback execution. "
               "Fees, deposits, refunds, rewards, deletion proceeds, funding timing and missing coverage may affect balance identities; unknown adjustments are not allocated.")
    with st.expander("Native coverage, weekly flows and exact balances"):
        st.json(ledger["coverage"])
        weekly = [{"Week starting": r["week_start"], "Wallet": w["account_id"],
                   "Native inflow yoctoNEAR": w["observed_inflow_yocto"], "Native outflow yoctoNEAR": w["observed_outflow_yocto"]}
                  for r in ledger["weekly"] for w in r["wallets"]]
        presentation.table(pd.DataFrame(weekly), hide_index=True, width="stretch", alt="Exact weekly native action flows, not weekly closing balances")
        st.caption("YoctoNEAR columns are exact integer strings. Weekly endpoint balances and complete stock reconciliation are unavailable. "
                   "Lookup edges extend 23 August–24 October; accepted flows use actual execution dates in the target window. "
                   "There are 244 outside-window rows and 3 failed action rows, excluded from accepted flows.")
        st.json({r["account_id"]: {k: v for k, v in r.items() if k.endswith("_yocto")} for r in ledger["wallets"]})
        download("Download exact native ledger (JSON)", "results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json", "native_ledger_download")

    assets = data["wallet_asset_ledger"]
    known, = assets["known_owner_asset_reconciliations"]
    st.subheader("One known owner–asset balance reconciliation")
    st.write(f"{known['owner']} · {known['asset_id']} inside {known['contract']} · "
             "the same saved 23 August and 18 October closing anchors as the native ledger.")
    values = [("Opening internal balance", known["opening"]["balance_base_units"]),
              ("Closing internal balance", known["closing"]["balance_base_units"]),
              ("Closing minus opening", known["stock_change_base_units"]),
              ("Selected successful transfer net", known["selected_observed_internal_flow_net_base_units"]),
              ("Stock change minus selected flow net", known["stock_change_minus_selected_flow_base_units"])]
    presentation.table(pd.DataFrame([{"Comparison": label, "Exact internal asset base units": value} for label, value in values]),
                       hide_index=True, width="stretch", alt="One known internal asset: exact endpoint balance decrease equals one saved successful transfer net")
    st.write("The endpoint decrease equals the saved successful internal transfer. "
             "This reconciles one known owner–asset pair for one of three selected wallets.")
    st.caption("Not complete asset coverage or complete flow history: other offsetting movements could exist, "
               "and the total asset-pair denominator is unknown. Recipient ownership, fee origin and purchases remain unverified. "
               "This internal asset movement is not added to native flows or supply destruction; the native residual stays unallocated.")
    with st.expander("Known asset identities, coverage and exact evidence"):
        st.json(known)
        st.json(assets["coverage"])
        st.caption("These are saved observed day-close anchors, not independent canonical midnight-edge proofs. "
                   "Missing assets remain unavailable, not zero. The closed withdrawal-provenance investigation is unchanged.")
        download("Download current wallet ledger (JSON)", assets["source_artifact"], "wallet_asset_ledger_download")
        download("Download exact known-asset comparison (JSON)", "results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json", "known_asset_comparison_download")


def attribution(data):
    attribution = data["attribution"]
    st.subheader("Selected mechanisms alongside population measurements")
    st.caption("Population counts below come from saved signer/action and initial-outcome exports. "
               "The selected traces are purposive examples, not representative samples or estimates of population success, independent users or economic demand.")
    rows = []
    for case in attribution["selected_cases"]:
        rows.append({"Signer": case["account_id"], "Selected mechanism": case["label"],
                     "Population transactions": case["signed_population"], "Selected transactions": case["selected_transactions"],
                     "Selected share of signed population": fmt(case["share_of_signed_population_pct"], 10)+"%",
                     "Selection denominator": f"{case['eligible_population']:,} {case['eligible_population_label']}",
                     "Share of selection denominator": fmt(case["share_of_eligible_population_pct"], 10)+"%"})
    presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch", alt="Selected Sweat, wx and tinykoala traces with separate population and selection denominators")
    options = [c.get("selection_key", c["account_id"]) for c in attribution["selected_cases"]]
    selected = st.selectbox("Inspect a selected mechanism", options, key="attribution_case")
    case = next(c for c in attribution["selected_cases"] if c.get("selection_key", c["account_id"]) == selected)
    st.write(case["mechanism"])
    presentation.table(pd.DataFrame([{"Selected transactions": case["selected_transactions"],
        "Returned receipt outcomes": case["returned_receipt_outcomes"], "Covered returned graphs": case["covered_graph_transactions"],
        "Graphs with a returned failure": case["transactions_with_returned_failure"],
        "Missing emitted outcomes": case["missing_emitted_outcomes"],
        "Unresolved callback dependencies": case["unresolved_callback_dependencies"]}]), hide_index=True, width="stretch",
        alt="Returned-graph coverage and failures for the selected case set only")
    st.caption("Recorded transaction-plus-receipt charges for this selected set: "+fmt(case["recorded_charge_near"], 12)+
               " NEAR. Charges are counted once per outcome, not once per action. They are not revenue or actual supply burn. "
               "A covered graph may contain failure; initial SuccessReceiptId alone does not establish descendant success.")
    with st.expander("Case identities, exact charges and population coverage"):
        st.json(case)
        st.caption("The selected Sweat claim and jars cases have explicit Delegate authorization; wx has no returned Delegate action. "
                   "Different receipt predecessors alone do not prove delegation. Returned graph coverage is not independent historical ingestion completeness. "
                   "The 18 tinykoala controls were selected from failures and do not establish population error-cause frequencies.")
        st.caption("Two selected cases share the Sweat signer population. Their rows are separate mechanism examples; population denominators repeat and are not added. "
                   "The jars destination denominator is a saved eight-week original-receiver bucket, not a count of 23 September transactions or descendant outcomes.")
        download("Download selected case evidence (JSON)", case["source_artifact"], "attribution_case_download")
    with st.expander("Largest saved signers and growth contributors: population coverage"):
        table = []
        for r in attribution["population_table"]:
            outcomes = r["initial_outcomes"]
            receivers = r["original_receivers"] or r["growth_receiver_action_buckets"] or []
            table.append({"Signer": r["account_id"], "Transactions": r["transactions"],
                "Delegate-action transactions": f"{r['delegate_action_transactions']:,}" if r["delegate_action_transactions"] is not None else "Unavailable",
                "Receiving-contract evidence": ", ".join(x["receiver"] for x in receivers) or "Unavailable",
                "Initial outcomes": "; ".join(f"{k}: {v:,}" for k, v in outcomes.items()) if outcomes else "Unavailable"})
        presentation.table(pd.DataFrame(table), hide_index=True, width="stretch", alt="Selected signer populations and observed initial outcomes; absent profiles are unavailable, not zero")
        st.caption(attribution["population_scope"]+". Receiver profiles are weekly top-20 original destinations or overlapping receiver/action buckets, not a downstream census. "
                   "The largest named endpoint increases were tinykoala +148,950, wx +137,767 and 0here.tg +137,531; these are changes, not period totals. Population descendant rates remain unmeasured.")


def deliverables(data):
    st.subheader("Five deliverables: outputs and remaining evidence")
    presentation.table(pd.DataFrame([{"Deliverable": r["deliverable"], "Status": r["status"], "Remaining evidence": r["gap"]}
                                    for r in data["deliverables"]]), hide_index=True, width="stretch", alt="Five-deliverable status; partial supply, ledger and attribution work remain open")
    with st.expander("Completion criteria and useful work from saved inputs"):
        for r in data["deliverables"]:
            st.markdown(f"**{r['deliverable']} — {r['status']}**")
            st.write("Criterion: "+r["criterion"])
            st.write("Completed output: "+r["completed"])
            st.write("Possible from saved inputs: "+r["saved_work"])
            st.write("Missing source or access: "+r["source_dependency"])
            st.write("Investment conclusion affected: "+r["investment_conclusion_affected"])
        st.caption("The original submission history is preserved. Completed scoped outputs do not close missing economic components, wider attribution or empirical model calibration.")
    with st.expander("Model input provenance: dated evidence, illustrative assumptions and unavailable inputs"):
        provenance = data["model_input_provenance"]
        presentation.table(pd.DataFrame([{"Input": r["label"], "Default value": r["default_value"] if r["default_value"] is not None else "Unavailable",
            "Unit": r["unit"], "Status": r["status"].replace("_", " ").capitalize(), "Source": r["source"], "Basis": r["basis"]}
            for r in provenance["inputs"]]), hide_index=True, width="stretch", alt="Model defaults with explicit units and dated, illustrative or unavailable provenance")
        st.caption(provenance["qualification"]+" This table describes defaults; applied model downloads retain the user's edited values and assumption statuses.")
