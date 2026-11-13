"""Unified saved-input rebuild of published evidence, model and integration.

No collection functions are invoked. Network and subprocess launch are disabled.
Existing outputs must match; missing generated outputs use exclusive creation.
"""

import argparse
import importlib.util
import json
import sys
from collections import Counter
from decimal import Decimal, localcontext
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
ARTIFACT = RESULTS / "100_integrated_research_review.json"
VISUAL = ROOT / "docs/assets/persistence_and_concentration.svg"
STATUS = ROOT / "notes/deliverable_status.md"


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / name)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    # Historical wallet reports retain their original absolute capture directory.
    # Rebind only that descriptive string after validating identical evidence;
    # file reads and hash checks still use this checkout's actual local paths.
    pending, seen = [value], set()
    while pending:
        child = pending.pop()
        if id(child) in seen:
            continue
        seen.add(id(child))
        filename = getattr(child, "__file__", None)
        if not filename or not Path(filename).resolve().is_relative_to(ROOT/"analysis"):
            continue
        if Path(filename).name == "31_wallet_historical_balances.py" and not getattr(child, "_portable_provenance", False):
            recorded = read(78)
            references = {(state["account_id"], state["block_hash"]): state["evidence"]
                          for row in recorded["accounts"] for state in (row["opening"], row["closing"])}
            original = child.saved_state
            def saved_state(directory, item, _original=original, _references=references):
                state = _original(directory, item)
                expected = _references[(state["account_id"], state["block_hash"])]
                require({k:v for k,v in state["evidence"].items() if k != "directory"}
                        == {k:v for k,v in expected.items() if k != "directory"}, "Relocated wallet evidence differs")
                state["evidence"]["directory"] = expected["directory"]
                return state
            child.saved_state = saved_state
            child._portable_provenance = True
        pending.extend(x for x in vars(child).values() if isinstance(x, ModuleType))
    return value


def path(number):
    found, = RESULTS.glob(f"{number}_*.json")
    return found


def read(number):
    return json.loads(path(number).read_bytes(), parse_float=Decimal)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def near(value):
    with localcontext() as ctx:
        ctx.prec = 100
        return format(Decimal(value)/Decimal(10**24), "f")


def pct(n, d):
    with localcontext() as ctx:
        ctx.prec = 70
        return format(Decimal(n)*100/Decimal(d), "f")


def deliverables():
    return [
        {"deliverable": "1. Supply reconciliation", "status": "Partial",
         "criterion": "Eight weekly identities with independent issuance, actual burn and verified adjustments, canonical coverage and exact arithmetic.",
         "completed": "Eight-week observational comparison; one protocol-validated 23-epoch reward week; exact weekly endpoints; 144 inclusion-timed header blocks.",
         "gap": "Seven other reward weeks, complete inclusion-timed debits, gross burn/subsidies and full-window canonical coverage. Implied debit is not independent burn.",
         "saved_work": "Reproduce reward maps, protocol checks, endpoints and overlapping debit scopes; enumerate missing canonical coverage without extrapolating it.",
         "source_dependency": "Lossless retained canonical headers/chunks with predecessor links and inclusion-timed net debits; seven other reward-week endpoint/epoch/configuration captures. Gross burn/subsidy splitting needs retained runtime statistics not established as public API fields.",
         "investment_conclusion_affected": "Full-window net issuance, independently verified burn and fee-offset inflation cannot be estimated from implied debit or the sampled prefix."},
        {"deliverable": "2. Revenue/buyback ledger", "status": "Partial",
         "criterion": "Historically attributed accounts/assets, eight-week reconciled opening/closing balances and classified fees, principal, settlements, refunds and verified purchases.",
         "completed": "Three-wallet native flows, six endpoint states, eight weekly flow observations, internal-leg cancellation, closed withdrawal trace and one known owner–asset balance reconciliation (result 103).",
         "gap": "Complete token/internal-asset coverage, historical roles, fee origin, purchase settlement and balance adjustments. The 1cs difference stays unallocated.",
         "saved_work": "Reproduce native and known internal-asset stocks/flows separately, with exact identities and unavailable economic classifications. One asset reconciliation is not complete flow history. No residual-driven collection.",
         "source_dependency": "Retained historical NEP-141/NEP-245 events indexed by owner/recipient; historical internal-account associations, role/policy/fee configuration and successful exchange settlement. Native-counterparty SQL 45 cannot discover all assets; no accessible complete index is established.",
         "investment_conclusion_affected": "Attributable revenue yield, verified buyback spend, purchased holdings and holder benefit cannot be inferred from wallet inflows or one internal stock decrease."},
        {"deliverable": "3. Persistent activity", "status": "Cohort layer validated; execution coverage partial",
         "criterion": "Several starting-week activity cohorts, exact +1/+4/+8 checkpoints wherever follow-up is complete, transaction contribution, concentration and scoped outcomes/spending.",
         "completed": "Four activity cohorts; nine complete checkpoints; three incomplete checkpoints remain null; three exact-return initial-receipt pilots and two overlapping repeated-checkpoint subsets.",
         "gap": "No continuous-week or human retention claim, no execution result for other checkpoints, no descendant census, six-day lookup tails and aggregate/FLOAT source limits.",
         "saved_work": "Reproduce denominators, overlap, returner contribution/concentration and scoped execution-date spending; keep the three incomplete follow-ups unavailable.",
         "source_dependency": "Retained transaction-to-initial-receipt/outcome exports for other complete checkpoints, longer execution tails and later follow-up weeks. Saved aggregates cannot recover missing account-level links or descendant outcomes.",
         "investment_conclusion_affected": "Persistent signing-account use is supported in scope; broad human retention, execution across every cohort and complete-chain economic demand remain unestablished."},
        {"deliverable": "4. Attribution/execution", "status": "Partial",
         "criterion": "Reproducible population attribution and descendant coverage with historical roles, submitter/inner actor distinctions and no join duplication.",
         "completed": "Selected Sweat claim and delegated jar deposit (with booster rejection), accepted wx transfer-call, 18 failed tinykoala controls, canonical submission dates and saved population coverage table.",
         "gap": "Population-wide descendant success, independent actor/funder/ownership mapping and internal exchange credit or swap evidence. Selected cases are not representative.",
         "saved_work": "Revalidate returned DAGs, callbacks, exact charges and selection denominators alongside population signer/receiver statistics; keep selected cases separate.",
         "source_dependency": "Population-linked delegated identities, historical actor/funder roles and a declared sampling frame with descendant receipt outcomes. Bounded RPC traces establish selected mechanisms, not a population census.",
         "investment_conclusion_affected": "Independent-user breadth, economic payer identity and population downstream settlement/success cannot be inferred from signer rankings or selected examples."},
        {"deliverable": "5. Conditional investment model", "status": "Implemented; empirical calibration incomplete",
         "criterion": "Editable assumptions, units/formulas, disjoint revenue/destruction/custody outputs, thresholds, sensitivity and measurable revision conditions.",
         "completed": "Reviewed Decimal model, zero-capture and allocation guards, horizon scaling, 27 sensitivity cases and reproducible hypothetical outputs.",
         "gap": "Measured fee capture, purchases, destruction and full supply components remain unavailable; scenarios do not establish fair value or expected returns.",
         "saved_work": "Reproduce formulas, sensitivity, units, allocation constraints and field-level provenance; distinguish the dated reward baseline from illustrative and unavailable inputs.",
         "source_dependency": "Historically attributed fee-bearing activity/capture, independently verified purchases/destruction and complete supply components from deliverables 1–2; actor attribution constrains demand interpretation.",
         "investment_conclusion_affected": "Conditional activity/capture hurdles are calculable; fair value, expected returns and observed economic or investment break-even are unsupported."},
    ]


def model_input_provenance():
    model = module("38_conditional_investment_model.py").model
    assumptions = read(90)["assumptions"]
    require(assumptions["reward_mint_near_per_week"] == read(72)["recorded_reward_maps_near"], "Model reward provenance mismatch")
    rows = []
    for key, (label, unit, _) in model.FIELDS.items():
        value = assumptions[key]
        dated = key == "reward_mint_near_per_week"
        rows.append({"input": key, "label": label, "unit": unit, "default_value": value,
                     "status": "UNAVAILABLE" if value is None else "DATED_BASELINE_REPEATED_AS_SCENARIO" if dated else "ILLUSTRATIVE_ASSUMPTION",
                     "source": str(path(72).relative_to(ROOT)) if dated else "config/conditional_model_assumptions.json",
                     "basis": "21–27 September 2026 protocol-validated epoch rewards only; repetition is assumed, subsidies excluded" if dated else "No measured value; an entered value would be an explicit assumption" if value is None else "Editable scenario default; no observed economic calibration"})
    return {"inputs": rows, "context_only_sources": [str(path(n).relative_to(ROOT)) for n in (80, 103, 104)],
            "wallet_stock_reconciliation_used_to_calibrate_capture": False,
            "measured_fee_capture": None, "measured_purchase_or_destruction": None,
            "qualification": "Native and internal asset stocks are context, not fee-bearing USD activity, revenue, purchases or supply destruction. The reward-only target excludes independently unavailable subsidies; scenario outputs are not expected returns."}


def case(account, label, signed, eligible, eligible_label, reports, source, mechanism, date=None):
    statuses = Counter()
    charges = 0
    for r in reports:
        statuses.update(r["coverage"]["receipt_status_counts"])
        charges += int(r["recorded_transaction_and_receipt_execution_charge_yocto"])
    selected = len(reports)
    return {"account_id": account, "label": label, "selection": "PURPOSIVELY_SELECTED_NOT_REPRESENTATIVE",
        "signed_population": signed, "eligible_population": eligible, "eligible_population_label": eligible_label,
        "selected_transactions": selected, "share_of_signed_population_pct": pct(selected, signed),
        "share_of_eligible_population_pct": pct(selected, eligible), "receipt_status_counts": dict(statuses),
        "returned_receipt_outcomes": sum(r["coverage"]["returned_receipt_outcomes"] for r in reports),
        "covered_graph_transactions": sum(r["coverage"]["observed_graph_consistent_and_covered"] for r in reports),
        "all_returned_receipts_successful_transactions": sum(r["coverage"]["all_observed_receipt_outcomes_successful"] is True for r in reports),
        "transactions_with_returned_failure": sum(r["coverage"]["all_observed_receipt_outcomes_successful"] is False for r in reports),
        "missing_emitted_outcomes": sum(len(r["coverage"]["missing_emitted_action_outcomes"]) for r in reports),
        "unresolved_callback_dependencies": sum(sum(x["status"] != "MATCHED" for x in r["callback_dependencies"]) for r in reports),
        "recorded_charge_yocto": str(charges), "recorded_charge_near": near(charges),
        "independent_ingestion_completeness": None, "mechanism": mechanism,
        "submission": date, "source_artifact": str(path(source).relative_to(ROOT)),
        "transaction_hashes": [r["transaction_hash"] for r in reports]}


def build():
    base, supply, ledger, prefix, restriction = [read(n) for n in (62, 72, 80, 88, 89)]
    sweat, wx, jars = read(96), read(99), read(106)
    interpreter = module("40_trace_sweat_relayer.py")
    failures = [interpreter.interpret(x["rpc_response"]["result"]) for x in read(26)["records"]]
    cases = [case("sweat-relayer.near", "Delegated claim", 13704363, 13246938, "DELEGATE_ACTION transactions", [sweat], 97,
                  "Explicit Delegate → claim.sweat.claim → token.sweat.ft_transfer → claim callback; no verified human/operator or revenue attribution.", read(97)["case_study"]["submission_block"]),
             case("wx-cruce.near", "Accepted transfer-call", 413281, 398968, "Initial SUCCESS_RECEIPT_ID outcomes", [wx["returned_graph"]], 99,
                  "wrap.near.ft_transfer_call → Ref ft_on_transfer → resolver, empty msg; consistent with funding/deposit, no swap/output-asset evidence or independently verified internal credit.", wx["canonical_submission"]),
             case("tinykoala595.near", "Failed execution controls", 778588, 715518, "Failed initial receipts", failures, 95,
                  "18 preselected failed transactions; each returned graph has one failure and two successful receipts. Seventeen sampled slippage errors and one insufficient-deposit error; not population error frequencies.")]
    jars_case = case("sweat-relayer.near", "Delegated jar deposit",
        jars["population_coverage"]["saved_signer_transactions"], jars["population_coverage"]["saved_destination_bucket_transactions"],
        "Saved jars-oracle.sweat original-receiver bucket", [jars["returned_graph"]], 106,
        "Explicit Delegate from jars-oracle.sweat to token.sweat.ft_transfer_call targeting v2.jars.sweat. "
        "The receiver logs a deposit and the resolver accepts the full token amount; apply_booster rejects the beneficiary despite successful receipt outcomes. "
        "Airdrop is the payload type, not verified human adoption, economic purpose, revenue or native supply destruction.", jars["canonical_submission"])
    jars_case["selection_key"] = "sweat-relayer.near → jars-oracle.sweat"
    jars_case["delegation_status"] = jars["returned_graph"]["delegation_status"]
    jars_case["observed_behavior"] = jars["observed_behavior"]
    cases.append(jars_case)
    with localcontext() as ctx:
        ctx.prec = 100
        require(Decimal(supply["recorded_reward_maps_near"])-Decimal(supply["exact_supply_movement_near"]) == Decimal(supply["conditional_reward_map_implied_weekly_net_debit_near"]), "Weekly implied debit arithmetic")
    require(supply["protocol_checks_missing"] == 0 and supply["application_epochs"] == 23, "Incomplete reward-week protocol checks")
    require(all(supply[k] is None for k in ["gross_actual_burn_yocto", "subsidies_yocto", "independently_measured_weekly_net_debit_yocto"]), "Unknown supply component filled")
    require(prefix["cumulative_produced_blocks_including_pilot"] == 144 and prefix["cumulative_supply_identity_discrepancy_yocto"] == "0", "Prefix coverage mismatch")
    require(int(read(85)["observed_prefix_net_debit_yocto"])+int(prefix["observed_segment_prefix_net_debit_yocto"]) == int(prefix["cumulative_net_debit_including_pilot_yocto"]), "Prefix debit mismatch")
    wallets = []
    for row in ledger["native_wallets"]:
        opening, closing = (int(row[t]["combined_yocto"]) for t in ("opening", "closing"))
        inflow, outflow = (int(row[k]) for k in ("successful_native_inflow_yocto", "successful_native_outflow_yocto"))
        residual = closing-opening-inflow+outflow
        require(str(residual) == row["unexplained_stock_flow_difference_yocto"], "Native wallet stock-flow identity")
        values = {"opening": opening, "closing": closing, "balance_change": closing-opening,
                  "inflow": inflow, "outflow": outflow, "net_flow": inflow-outflow, "residual": residual}
        wallets.append({"account_id": row["account_id"], **{k+"_yocto": str(v) for k, v in values.items()},
            **{k+"_near": near(v) for k, v in values.items()}, "classification": "UNCLASSIFIED_NATIVE_FLOWS",
            "external_inflow_yocto": row["flow_scopes"]["EXTERNAL_COUNTERPARTY"]["inflow_yocto"],
            "external_outflow_yocto": row["flow_scopes"]["EXTERNAL_COUNTERPARTY"]["outflow_yocto"],
            "internal_inflow_yocto": row["flow_scopes"]["BETWEEN_SELECTED_WALLETS"]["inflow_yocto"],
            "internal_outflow_yocto": row["flow_scopes"]["BETWEEN_SELECTED_WALLETS"]["outflow_yocto"],
            "opening_liquid_yocto": row["opening"]["amount"], "opening_locked_yocto": row["opening"]["locked"],
            "closing_liquid_yocto": row["closing"]["amount"], "closing_locked_yocto": row["closing"]["locked"],
            "complete_balance_reconciliation": False})
    internal = sum(int(r["transfer"]["amount_yocto"]) for r in ledger["native_internal_transfers"])
    require(internal == sum(int(r["internal_inflow_yocto"]) for r in wallets) == sum(int(r["internal_outflow_yocto"]) for r in wallets), "Internal legs do not cancel")
    group = ledger["native_group"]
    require(sum(int(r["net_flow_yocto"]) for r in wallets) == int(group["group_observed_external_net_yocto"]), "Group net double counted")
    require(all(ledger[k] is None for k in ("verified_revenue_yocto", "verified_buybacks_yocto", "actual_supply_burn_yocto")), "Economic classification filled")
    wallet_assets = read(104)
    require(wallet_assets["coverage"]["known_owner_asset_pairs_reconciled"] == 1
            and wallet_assets["coverage"]["complete_multi_asset_coverage"] is None, "Asset scope overstated")
    require(wallet_assets["closed_withdrawal_provenance"] == ledger["closed_withdrawal_provenance"], "Closed provenance changed")
    sources = [path(n) for n in (26, 62, 72, 80, 85, 88, 89, 90, 91, 95, 96, 97, 99, 102, 103, 104, 105, 106)]
    return {"schema_version": 1, "status": "INTEGRATED_WITH_OPEN_DELIVERABLES", "network": "NEAR mainnet",
        "primary_window": ["2026-08-24", "2026-10-18"], "historical_checkpoint": "submission-2026-11-02",
        "supply_week": {k: supply[k] for k in ("week", "application_epochs", "recorded_reward_maps_near", "exact_supply_movement_near", "observed_boundary_header_debits_near", "conditional_reward_map_implied_weekly_net_debit_near", "gross_actual_burn_yocto", "subsidies_yocto", "independently_measured_weekly_net_debit_yocto")},
        "header_prefix": {"first_height": 216877934, "last_height": 216878077, "produced_blocks": 144,
            "net_debit_yocto": prefix["cumulative_net_debit_including_pilot_yocto"], "net_debit_near": near(prefix["cumulative_net_debit_including_pilot_yocto"]),
            "identity_discrepancy_yocto": "0", "reported_blocks_per_minute": restriction["restriction"]["response_reported_blocks_per_minute"],
            "scope": "Prefix only; no independent canonical tail control; no extrapolation to epoch/week. External raw captures are not dashboard inputs."},
        "native_ledger": {"window": ledger["window"], "wallets": wallets,
            "external_net_near": near(group["group_observed_external_net_yocto"]),
            "external_net_yocto": group["group_observed_external_net_yocto"],
            "unallocated_residual_near": near(group["group_unexplained_stock_flow_difference_yocto"]),
            "internal_transfer_count": len(ledger["native_internal_transfers"]), "internal_transfer_near": near(internal),
            "weekly": ledger["weekly_native_flow_observations"], "coverage": ledger["native_coverage"],
            "revenue_near": None, "verified_purchases_near": None, "actual_native_burn_near": None,
            "scope": "Native actions and six endpoint account states; not complete token/internal-asset coverage, weekly stock reconciliation or independently attributed revenue/buybacks."},
        "attribution": {"population_scope": read(97)["ranking_scope"], "population_table": [{k: v for k, v in r.items() if k != "selected_downstream_evidence"} for r in read(97)["coverage_table"]], "selected_cases": cases,
            "scope": "Selected mechanisms and failure controls are separate from population statistics. No population descendant-success, human-user or economic-funder estimate."},
        "persistence_visual": [{"cohort": r["cohort_week"], "exact_week8_return_pct": r["checkpoint_return_shares_pct"]["8"],
            "top10_returner_transactions_pct": next(p["top_10_returner_transaction_share_pct"] for p in base["checkpoints"] if p["cohort_week"] == r["cohort_week"] and p["week_offset"] == 8)} for r in base["cohorts"][:2]],
        "wallet_asset_ledger": {"known_owner_asset_reconciliations": wallet_assets["known_owner_asset_reconciliations"],
            "coverage": wallet_assets["coverage"], "source_artifact": str(path(104).relative_to(ROOT)),
            "scope": "One known owner–asset balance reconciliation; not complete asset coverage or complete flow history. Native residual stays unallocated; revenue and purchases remain unavailable."},
        "model_input_provenance": model_input_provenance(),
        "returner_execution_bounds": read(105),
        "deliverables": deliverables(), "unavailable": {"full_window_independent_issuance": None, "actual_gross_native_burn": None,
            "subsidies": None, "attributed_product_revenue": None, "verified_buybacks": None, "population_descendant_success_rate": None},
        "source_validation_scope": "Unified rebuild revalidates reward/configuration and wallet/case captures. Header-prefix arithmetic is reproduced from saved validated summary exports; independently revalidating large external raw headers needs their retained external paths.",
        "sources": {str(p.relative_to(ROOT)): module("40_trace_sweat_relayer.py").identity(p) for p in sources}}


def visual(data):
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="960" height="300" viewBox="0 0 960 300" role="img" aria-labelledby="title desc">',
        '<title id="title">Persistence was real, but transactions were concentrated</title>',
        '<desc id="desc">Two August activity cohorts: about 47 and 46 percent returned at exact week eight. Their top ten returners produced about 74 and 75 percent of returner transactions. Different denominators; cohorts overlap.</desc>',
        '<rect width="960" height="300" fill="#f8fafc"/>',
        '<g font-family="Arial, sans-serif" fill="#172033"><text x="28" y="35" font-size="22" font-weight="bold">Persistence was real. Transactions were concentrated.</text>',
        '<text x="28" y="59" font-size="13">NEAR mainnet · 2026 · exact +8 weeks · overlapping starting-week activity cohorts</text>']
    for col, (field, title, subtitle, color) in enumerate([
        ("exact_week8_return_pct", "Accounts returning at +8", "% of accounts active in the starting week", "#137c8b"),
        ("top10_returner_transactions_pct", "Top ten returners’ transaction share", "% of returning accounts’ +8 transactions", "#9a4e12")]):
        x = 28+col*470
        parts += [f'<text x="{x}" y="96" font-size="17" font-weight="bold">{title}</text>', f'<text x="{x}" y="117" font-size="12">{subtitle}</text>']
        for index, row in enumerate(data["persistence_visual"]):
            y = 153+index*56
            value = Decimal(row[field])
            width = format(value*Decimal("2.8"), ".4f")
            label = "10 Aug" if index == 0 else "17 Aug"
            parts += [f'<text x="{x}" y="{y+15}" font-size="14">{label}</text>',
                f'<rect x="{x+65}" y="{y}" width="280" height="24" fill="#e2e8f0"/>',
                f'<rect x="{x+65}" y="{y}" width="{width}" height="24" fill="{color}"/>',
                f'<text x="{x+355}" y="{y+17}" font-size="15" font-weight="bold">{value:.2f}%</text>']
    parts += ['<text x="28" y="277" font-size="12">Account return is not verified user retention. Returner concentration limits claims of broad demand. Source: saved results 57 and 62.</text></g></svg>\n']
    return "\n".join(parts).encode()


def status_markdown(data):
    lines = ["# Five-deliverable status", "", "The submission is an intermediate checkpoint. Completion is assessed against the original measurement criteria; bounded cases do not close population or economic accounting gaps.", "",
             "| Deliverable | Status / completed output | Useful work from saved inputs | Missing source / access dependency | Investment conclusion affected |", "| --- | --- | --- | --- | --- |"]
    for row in data["deliverables"]:
        lines.append(f"| {row['deliverable']} | **{row['status']}**. {row['completed']} | {row['saved_work']} | {row['source_dependency']} | {row['investment_conclusion_affected']} |")
    lines += ["", "## Completion criteria", ""]
    lines += [f"- **{row['deliverable']}:** {row['criterion']}" for row in data["deliverables"]]
    lines += ["", "Sources: [integrated review](../results/100_integrated_research_review.json), [research plan](research_plan.md), [thesis](investment_thesis.md). All amounts absent from source evidence remain unavailable, not zero. No new collection is part of this integration.", ""]
    lines += issuance_status_lines()
    return "\n".join(lines).encode()


def issuance_status_lines():
    """Evidence added after result 100; result 100 itself is unchanged."""
    bounds = read(107)
    total, control = bounds["window_total"], bounds["control"]
    require(bounds["status"] == "VALIDATED_PROTOCOL_DERIVED_BOUNDS" and control["measured_within_bounds"]
            and all(v is None for v in bounds["unavailable"].values()), "Result 107 scope changed")
    share = Decimal(int(total["net_debit_share_of_issuance_upper_bound"]["exact"].split("/")[0])) * 100 / Decimal(int(total["net_debit_share_of_issuance_upper_bound"]["exact"].split("/")[1]))
    def n(value, places=2):
        return f"{Decimal(value):,.{places}f}"
    return ["## Supply evidence added after the integrated review", "",
            f"[Result 107](../results/107_eight_week_issuance_bounds_2026-08-24_to_2026-10-18.json) adds exact supplies, epoch boundaries and protocol configuration at the nine weekly anchors "
            f"(45 archival point requests). Across {total['epoch_reward_applications']} epoch-reward applications, 24 August–18 October, exact supply movement is "
            f"{n(total['exact_supply_movement_near'])} NEAR; protocol-derived epoch-reward issuance lies between {n(total['issuance_lower_bound_near'])} and "
            f"{n(total['issuance_upper_bound_near'])} NEAR; net header debit lies between 0 and {n(total['net_header_debit_upper_bound_near'])} NEAR, at most {share:.2f}% of issuance. "
            f"The measured {control['week'].replace('/', '–')} reward minting lies inside its week's bounds.", "",
            "Deliverable 1 remains **Partial**: these are protocol-derived bounds, not measured minting outside the control week, independently measured debit, gross burn or a subsidy split. "
            "Protocol version 86 and the 1/40 inflation parameter are verified at the anchor epochs and the control week, not at every intervening epoch. "
            "Deliverable 5 gains a measured eight-week net-supply-growth target; fee capture, purchases and destruction remain unavailable.", ""]


def validate_new_evidence():
    checks = {}
    protocol = module("28_supply_protocol_checks.py")
    directory = ROOT / next(iter(read(72)["configuration_capture_inputs"])).rsplit("/", 1)[0]
    checks[path(72)] = protocol.capture.json_bytes(protocol.validate(directory))
    ledger = module("33_consolidate_three_wallet_ledger.py")
    checks[path(80)] = ledger.c.json_bytes(ledger.report())
    assets = module("46_known_asset_wallet_coverage.py")
    checks[path(102)] = assets.c.json_bytes(assets.report())
    checks[path(103)] = assets.c.json_bytes(assets.validate())
    trace = module("40_trace_sweat_relayer.py")
    checks[path(95)] = trace.c.json_bytes(trace.controls_report())
    prior = module("41_consolidate_priority4.py")
    checks[path(96)] = trace.c.json_bytes(trace.validate_status(prior.STATUS))
    timestamp = ROOT / "results/sweat_submission_block_time/20261108T004552Z_9f57ad2f6291"
    checks[path(97)] = trace.c.json_bytes(prior.consolidate(timestamp))
    wx = module("43_select_wx_forwarding_case.py")
    checks[path(99)] = wx.c.json_bytes(wx.report())
    bounds = module("48_returner_execution_bounds.py")
    checks[path(105)] = bounds.b.json_bytes(bounds.report())
    jars = module("49_trace_sweat_jars.py")
    checks[path(106)] = jars.c.json_bytes(jars.report())
    issuance = module("50_eight_week_issuance_bounds.py")
    checks[path(107)] = issuance.cap.json_bytes(issuance.validate(issuance.single_capture()))
    for p, raw in checks.items():
        require(p.read_bytes() == raw, f"Generated-file mismatch: {p.name}")
    return len(checks)


def rebuild(check=False):
    previous = module("39_review_model_and_attribution.py").rebuild(check=check, with_model=True)
    count = validate_new_evidence()
    data = build()
    outputs = {ARTIFACT: (json.dumps(data, sort_keys=True, indent=2)+"\n").encode(),
               VISUAL: visual(data), STATUS: status_markdown(data)}
    ledger = module("47_integrate_known_asset_ledger.py")
    outputs[ledger.OUTPUT] = ledger.c.json_bytes(ledger.report())
    outputs.update(module("45_model_sensitivity_chart.py").outputs())
    for p, raw in outputs.items():
        if p.exists():
            require(p.read_bytes() == raw, f"Generated-file mismatch: {p}")
        else:
            require(not check, f"Missing generated output: {p}")
    for p, raw in outputs.items():
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with p.open("xb") as handle:
                handle.write(raw)
    return {"source_requests": 0, "new_evidence_artifacts_reproduced": count,
            "integration_outputs_verified": [str(p.relative_to(ROOT)) for p in outputs], "previous": previous,
            "external_header_raw_scope": data["source_validation_scope"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    def deny(event, _):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen", "os.system"}:
            raise RuntimeError("Source requests and subprocess launch disabled in offline rebuild")
    sys.addaudithook(deny)
    print(json.dumps(rebuild(args.check), indent=2))


if __name__ == "__main__":
    main()
