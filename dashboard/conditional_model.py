"""Saved-input conditional economics. Decimal only; no network or collectors."""

import hashlib
import json
import re
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/"config/conditional_model_assumptions.json"
ARTIFACT = ROOT/"results/90_conditional_investment_model.json"
PRECISION = 80
SOURCE_NAMES = (
    "62_integrated_research_evidence.json",
    "72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json",
    "80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json",
    "85_neardata_header_pilot_validation_216877934_to_216878033.json",
    "88_neardata_optimized_segment_validation_216878034_to_216879033.json",
    "89_neardata_optimized_prefix_rate_limit_assessment.json",
)
FIELDS = {
    "horizon_weeks": ("Hypothetical horizon", "weeks", False),
    "reward_mint_near_per_week": ("Reward minting assumption", "NEAR/week", False),
    "price_usd_per_near": ("Effective purchase price", "USD/NEAR", False),
    "eligible_activity_usd_per_week": ("Eligible economic activity", "USD/week", False),
    "fee_rate": ("Fee rate on eligible activity", "fraction", False),
    "capture_fraction": ("Captured share of eligible fees", "fraction", False),
    "destruction_allocation": ("Captured budget allocated to purchase and destruction", "fraction", False),
    "custody_allocation": ("Captured budget allocated to purchases held in custody", "fraction", False),
    "retained_budget_hurdle_usd_per_week": ("Chosen retained-budget hurdle", "USD/week", False),
    "additional_issuance_near_per_week": ("Additional issuance beyond reward minting", "NEAR/week", True),
    "other_destruction_near_per_week": ("Other destruction, disjoint from modeled purchases", "NEAR/week", True),
    "other_supply_adjustment_near_per_week": ("Other signed supply adjustment", "NEAR/week", True),
}
RATES = {"fee_rate", "capture_fraction", "destruction_allocation", "custody_allocation"}
OPTIONAL = {key for key, (_, _, optional) in FIELDS.items() if optional}
FORMULAS = {
    "gross_eligible_fees_usd_per_week": "V * f",
    "captured_fee_revenue_usd_per_week": "R = V * f * c",
    "purchase_and_destruction_budget_usd_per_week": "R * a_d",
    "custody_purchase_budget_usd_per_week": "R * a_h",
    "retained_budget_before_operating_costs_usd_per_week": "R * (1 - a_d - a_h)",
    "purchased_and_destroyed_near_per_week": "D = R * a_d / P",
    "purchased_and_held_near_per_week": "H = R * a_h / P; H does not reduce total supply",
    "conditional_supply_change_near_per_week": "I_reward + I_additional + A_other - B_other - D; unavailable if any required component is null",
    "reward_only_activity_threshold_usd_per_week": "I_reward * P / (f * c * a_d); offsets reward baseline only, excludes missing supply components",
    "full_supply_neutral_activity_threshold_usd_per_week": "max(0, I_reward + I_additional + A_other - B_other) * P / (f * c * a_d); requires all supply assumptions",
    "reward_only_required_capture_fraction": "I_reward * P / (V * f * a_d); values above 1 are infeasible at this activity/price/allocation",
    "retained_budget_activity_threshold_usd_per_week": "chosen hurdle / (f * c * (1 - a_d - a_h))",
    "retained_budget_required_capture_fraction": "chosen hurdle / (V * f * (1 - a_d - a_h))",
    "horizon_totals": "weekly scenario flows * assumed weeks; constant inputs throughout, no forecast, compounding or discounting",
}
CONCLUSION = (
    "Persistent signing accounts generated successful initial execution and recorded NEAR expenditure. "
    "Growth is sensitive to the comparison window and returner transactions remain concentrated. "
    "The saved evidence does not establish attributable product revenue, implemented buybacks, actual gross burn "
    "or holder cash flows. A token investment case remains conditional on verified economic capture and its scale; "
    "no fair value, price target or expected investment return is established."
)
CONDITIONS = [
    {"direction": "Strengthen", "test": "At least three starting-week cohorts with complete +8 follow-up each show >=40% exact +8 return and <=50% top-ten share of returner transactions; disclose membership overlap.", "basis": "Analyst-selected adoption hurdle, not an observed result or independent-cohort assumption."},
    {"direction": "Weaken", "test": "At least three complete +8 cohorts show <25% exact returns or >80% top-ten returner transaction concentration.", "basis": "Analyst-selected contrary-evidence rule; missing follow-up is unavailable, not failure."},
    {"direction": "Execution evidence", "test": "At least three comparable complete checkpoint weeks show >=95% initial-receipt success with >=99.9% unique link/cost coverage; descendant settlement must be separately established before any complete-chain claim.", "basis": "Analyst-selected scoped execution hurdle; transaction groups may overlap."},
    {"direction": "Economic capture", "test": "Eight complete weekly asset ledgers independently classify fee origin and settlement, reconcile balances and avoid principal/refund/internal-transfer double counting; compare measured capture with the explicitly chosen model hurdle.", "basis": "Measured capture is currently unavailable. Meeting a scenario threshold alone is insufficient."},
    {"direction": "Supply conclusion", "test": "Eight weekly canonical identities independently identify issuance, gross burn, subsidies and other adjustments with zero integer arithmetic discrepancy and complete inclusion coverage.", "basis": "No extrapolation of sampled header debit, and no substitution of validator changes or spending."},
    {"direction": "Weaken economic mechanism", "test": "Across eight independently attributed weeks, capture remains below the declared hurdle or claimed purchase/destruction deployments are not verified.", "basis": "A falsification test for a specified capture/deployment claim, not proof of absent distributions today."},
]


def require(value, message):
    if not value:
        raise ValueError(message)


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def bad(value):
        raise ValueError(f"Nonfinite JSON number: {value}")
    return json.loads(raw, parse_float=Decimal, parse_constant=bad, object_pairs_hook=pairs)


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+"\n").encode()


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def decimal(value, name):
    require(isinstance(value, str) and len(value) <= 90 and re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", value) is not None,
            f"{name}: use a finite decimal string without commas or exponents")
    result = Decimal(value)
    require(result.is_finite() and result.copy_abs() <= Decimal("1e24") and len(result.as_tuple().digits) <= 60,
            f"{name}: value is outside the supported finite range")
    return result


def assumptions(values):
    require(isinstance(values, dict) and set(values) == set(FIELDS), "Missing or unexpected assumption fields")
    result = {}
    for key in FIELDS:
        value = values[key]
        result[key] = None if value is None and key in OPTIONAL else decimal(value, key)
    for key, value in result.items():
        if value is not None and key != "other_supply_adjustment_near_per_week":
            require(value >= 0, f"{key}: must be nonnegative")
        if key in RATES:
            require(value <= 1, f"{key}: fraction must be between 0 and 1")
    require(result["price_usd_per_near"] > 0, "price_usd_per_near: must be positive")
    h = result["horizon_weeks"]
    require(h == h.to_integral_value() and 1 <= h <= 520, "horizon_weeks: use an integer from 1 to 520")
    with localcontext() as context:
        context.prec = PRECISION
        require(result["destruction_allocation"]+result["custody_allocation"] <= 1, "Allocations exceed the single captured-fee budget")
    return result


def text(value):
    return None if value is None else format(value, "f")


def threshold(target, coefficient, unit, fraction=False):
    if target == 0:
        return {"value": "0", "unit": unit, "status": "ZERO_TARGET"}
    if coefficient == 0:
        return {"value": None, "unit": unit, "status": "UNREACHABLE_WITH_ZERO_COEFFICIENT"}
    value = target/coefficient
    return {"value": text(value), "unit": unit,
            "status": "EXCEEDS_FEASIBLE_FRACTION" if fraction and value > 1 else "CONDITIONAL_THRESHOLD"}


def calculate(values):
    a = assumptions(values)
    with localcontext() as ctx:
        ctx.prec = PRECISION
        v, f, c = (a[key] for key in ("eligible_activity_usd_per_week", "fee_rate", "capture_fraction"))
        price, ad, ah = (a[key] for key in ("price_usd_per_near", "destruction_allocation", "custody_allocation"))
        # Finite input products must conserve their funding budget exactly.
        # Division-based scenario quantities and thresholds use PRECISION below.
        with localcontext() as budget_context:
            budget_context.prec = 320
            retained = 1-ad-ah
            fees, revenue = v*f, v*f*c
            destruction_budget, custody_budget, retained_budget = revenue*ad, revenue*ah, revenue*retained
            require(destruction_budget+custody_budget+retained_budget == revenue, "Budget allocation identity failed")
        destroyed, held = destruction_budget/price, custody_budget/price
        reward = a["reward_mint_near_per_week"]
        supply_complete = all(a[key] is not None for key in OPTIONAL)
        supply_target = (reward+a["additional_issuance_near_per_week"]+a["other_supply_adjustment_near_per_week"]-a["other_destruction_near_per_week"]) if supply_complete else None
        weekly = {"gross_eligible_fees_usd_per_week": fees, "captured_fee_revenue_usd_per_week": revenue,
                  "purchase_and_destruction_budget_usd_per_week": destruction_budget,
                  "custody_purchase_budget_usd_per_week": custody_budget,
                  "retained_budget_before_operating_costs_usd_per_week": retained_budget,
                  "purchased_and_destroyed_near_per_week": destroyed, "purchased_and_held_near_per_week": held,
                  "conditional_total_destruction_near_per_week": destroyed+a["other_destruction_near_per_week"] if a["other_destruction_near_per_week"] is not None else None,
                  "conditional_supply_change_near_per_week": supply_target-destroyed if supply_complete else None}
        limits = {
            "reward_only_activity_threshold": threshold(reward*price, f*c*ad, "USD/week"),
            "reward_only_capture_threshold": threshold(reward*price, v*f*ad, "fraction", True),
            "retained_budget_activity_threshold": threshold(a["retained_budget_hurdle_usd_per_week"], f*c*retained, "USD/week"),
            "retained_budget_capture_threshold": threshold(a["retained_budget_hurdle_usd_per_week"], v*f*retained, "fraction", True),
            "full_supply_neutral_activity_threshold": threshold(max(Decimal(0), supply_target)*price, f*c*ad, "USD/week") if supply_complete else {"value": None, "unit": "USD/week", "status": "UNAVAILABLE_MISSING_SUPPLY_ASSUMPTIONS"}}
        return {"classification": "SCENARIO_NOT_OBSERVED_OR_EXPECTED_RETURN",
                "weekly": {key: text(value) for key, value in weekly.items()},
                "horizon_weeks": text(a["horizon_weeks"]),
                "horizon_totals": {key.replace("_per_week", ""): text(value*a["horizon_weeks"]) if value is not None else None for key,value in weekly.items()},
                "thresholds": limits, "budget_discrepancy_usd": "0",
                "missing_supply_assumptions": sorted(key for key in OPTIONAL if a[key] is None),
                "allocation_rule": "Revenue is the parent funding flow: destruction budget + custody budget + remaining budget = captured revenue. Do not add parent revenue to these uses. Held purchases never reduce supply; purchase-and-destruction quantities are one use counted once.",
                "cost_boundary": "Captured eligible fees exclude principal, pass-through settlements, rebates and refunds by assumption. Remaining budget is before unspecified operating costs and taxes, not profit or holder distribution. Effective price includes assumed purchase costs; realized execution and destruction are unverified. Held purchases assume no resale or release during the horizon; their cumulative total is not a measured wallet closing balance or a supply reduction."}


def evidence():
    saved = {name: decode((ROOT/"results"/name).read_bytes()) for name in SOURCE_NAMES}
    integrated, week, ledger, pilot, prefix, rate = (saved[name] for name in SOURCE_NAMES)
    require(week["protocol_checks_missing"] == 0 and len(week["boundaries"]) == week["application_epochs"] == 23,
            "Weekly reward baseline lacks completed saved protocol checks")
    require(len({x["height"] for x in week["boundaries"]}) == 23 and all(x["protocol_verified"] for x in week["boundaries"]), "Reward boundary identity/coverage mismatch")
    reward = int(week["protocol_validated_weekly_epoch_reward_mint_yocto"])
    require(sum(int(x["recorded_reward_map_yocto"]) for x in week["boundaries"]) == reward, "Reward-map sum mismatch")
    with localcontext() as ctx:
        ctx.prec = PRECISION
        require(Decimal(week["protocol_validated_mint_subtotal_near"]) == Decimal(reward)/10**24, "Reward unit conversion mismatch")
        coverage_count = pilot["last_produced_height"]-pilot["pilot_interval"][0]+1+prefix["segment_produced_blocks"]
        require(coverage_count == 144 and prefix["last_validated_height"] == 216878077 and not prefix["complete"], "Changed bounded Neardata coverage; review evidence")
        require(rate["restriction"]["response_reported_blocks_per_minute"] == 30, "Observed provider restriction changed")
        require(all(ledger[key] is None for key in ("verified_revenue_yocto", "verified_buybacks_yocto", "actual_supply_burn_yocto")), "Review newly available economic attribution")
        return {"reward_baseline": {"status": "PROTOCOL_VALIDATED_DATED_REWARD_MINTING_ONLY", "week": week["week"], "application_events": 23,
                    "reward_mint_yocto": str(reward), "reward_mint_near": text(Decimal(reward)/10**24),
                    "exact_supply_movement_near": week["exact_supply_movement_near"],
                    "implied_weekly_net_debit_near": week["conditional_reward_map_implied_weekly_net_debit_near"],
                    "qualification": "21–27 September 2026 only. Subsidies/additional issuance are separately unavailable. Repeating this amount for a hypothetical horizon is a scenario, not a forecast or eight-week issuance measurement."},
                "neardata": {"status": "BULK_COLLECTION_PAUSED_NO_RETRY_HOST_IP_ROTATION_CAP_INCREASE_OR_SLOWER_RECOVERY",
                    "observed_error_blocks_per_minute": 30, "validated_height_interval": [216877934,216878077],
                    "validated_blocks": coverage_count, "sampled_net_header_debit_near": text(Decimal(prefix["cumulative_net_debit_including_pilot_yocto"])/10**24),
                    "sample_extrapolation": "NONE; sampled debit is never extrapolated to an epoch or week",
                    "full_epoch_accounting_complete": False, "full_week_accounting_complete": False},
                "activity": {"cohorts": integrated["cohorts"], "shared_week_overlap": integrated["shared_week"]["overlap"],
                    "returner_concentration": [{"cohort_week": x["cohort_week"], "top_ten_transaction_share_pct": x["top_10_returner_transaction_share_pct"]} for x in integrated["checkpoints"] if x["week_offset"] == 8 and x["measurement_available"]],
                    "initial_success_share_pct": [x["initial_success_share_pct"] for x in integrated["shared_week"]["populations"]]+[x["successful_initial_receipt_share_pct"] for x in integrated["october12_pilot"]["populations"]],
                    "growth_comparison": integrated["growth_comparison"], "initial_receipt_scope": "Selected initial receipts only, overlapping populations, six-day execution tails, FLOAT-derived spending; no complete-chain or revenue inference."},
                "native_wallet_context": {"window": ledger["window"], "external_native_net_near": text(Decimal(ledger["native_group"]["group_observed_external_native_net_yocto"])/10**24),
                    "unallocated_difference_near": text(Decimal(ledger["native_group"]["group_unexplained_stock_flow_difference_yocto"])/10**24),
                    "classification": "UNCLASSIFIED_NATIVE_FLOWS_NOT_REVENUE_OR_PURCHASES", "closed_provenance": "Successful signed internal transfer and native withdrawal; revenue origin unverified. Investigation stays closed."},
                "measured_unavailable": {key: None for key in ("full_window_independent_issuance_near", "independent_full_week_net_debit_near", "actual_gross_supply_burn_near", "subsidies_near", "attributed_product_revenue_usd", "verified_purchase_and_custody_near", "eligible_economic_activity_usd", "historical_fee_rate", "historical_capture_fraction", "holder_cash_flows_usd", "expected_investment_return")}}


def report(config=CONFIG, values=None):
    document = decode(config.read_bytes())
    require(document.get("schema_version") == 1, "Unsupported assumption schema")
    chosen = document["assumptions"] if values is None else values
    measured = evidence()
    base = calculate(chosen)
    activity = measured["activity"]
    growth = {row["metric"]: row for row in activity["growth_comparison"]}
    pct = lambda value: f"{Decimal(value):.2f}%"
    returns = " and ".join(pct(x["checkpoint_return_shares_pct"]["8"]) for x in activity["cohorts"][:2])
    concentrations = " and ".join(pct(x["top_ten_transaction_share_pct"]) for x in activity["returner_concentration"])
    success = [Decimal(value) for value in activity["initial_success_share_pct"]]
    assessment = [
        {"Direction": "Supporting", "Finding": f"Exact +8 returns of {returns} for the 10/17 August activity cohorts.", "Qualification": "Overlapping signing-account cohorts, not acquired users or continuous weekly activity. Sources 56–62."},
        {"Direction": "Supporting", "Finding": f"Selected initial-receipt success spans {pct(min(success))}–{pct(max(success))} with recorded execution spending.", "Qualification": "Initial receipts only; overlapping groups, six-day tails and FLOAT-derived spending. No complete-chain or fee-origin inference. Sources 58–62."},
        {"Direction": "Supporting", "Finding": f"Four-week average transactions increased {pct(growth['average_weekly_transactions']['relative_change_pct'])}.", "Qualification": "Selected comparison periods; final four weeks contain the account spike. Sources 39 and 62."},
        {"Direction": "Contrary", "Finding": f"Active days per active account-week changed {pct(growth['active_days_per_active_account_week']['relative_change_pct'])}.", "Qualification": "Composition-sensitive participation measure. Fifteen-week transaction/account endpoints also declined 10.63%/24.65%; growth is baseline-sensitive. Sources 39 and 62."},
        {"Direction": "Contrary", "Finding": f"Top ten returners generated {concentrations} of exact +8 transactions.", "Qualification": "Signing concentration does not identify independent people, applications or fee payers. Sources 56–62."},
        {"Direction": "Economic gap", "Finding": "Revenue origin, verified purchases, gross burn and holder cash flows remain unavailable.", "Qualification": "Native flows and sampled net header debits cannot fill these inputs. Full-epoch/week accounting is incomplete; Neardata bulk collection is paused. Sources 72, 80, 85, 88–89."},
    ]
    sensitivity = []
    with localcontext() as ctx:
        ctx.prec = PRECISION
        for price_multiple in ("0.5", "1", "2"):
            for capture_multiple in ("0", "0.5", "1"):
                case = dict(chosen)
                case["price_usd_per_near"] = text(decimal(chosen["price_usd_per_near"], "price")*Decimal(price_multiple))
                case["capture_fraction"] = text(decimal(chosen["capture_fraction"], "capture")*Decimal(capture_multiple))
                modeled = calculate(case)
                sensitivity.append({"price_usd_per_near": case["price_usd_per_near"], "capture_fraction": case["capture_fraction"],
                    "purchased_and_destroyed_near_per_week": modeled["weekly"]["purchased_and_destroyed_near_per_week"],
                    "purchased_and_held_near_per_week": modeled["weekly"]["purchased_and_held_near_per_week"],
                    "captured_fee_revenue_usd_per_week": modeled["weekly"]["captured_fee_revenue_usd_per_week"],
                    "reward_only_activity_threshold": modeled["thresholds"]["reward_only_activity_threshold"]})
    paths = [ROOT/"results"/name for name in SOURCE_NAMES]+[config,Path(__file__),ROOT/"analysis/38_conditional_investment_model.py"]
    return {"schema_version": 1, "status": "IMPLEMENTED_CONDITIONAL_MODEL_NOT_VALUATION_OR_RETURN_FORECAST",
            "conclusion": CONCLUSION, "evidence_assessment": assessment, "change_of_mind_conditions": CONDITIONS,
            "evidence": measured, "assumptions": chosen,
            "assumption_status": {key: "UNAVAILABLE" if value is None else ("DATED_BASELINE_REPEATED_AS_SCENARIO" if key == "reward_mint_near_per_week" and Decimal(value) == Decimal(measured["reward_baseline"]["reward_mint_near"]) else "EXPLICIT_SCENARIO_ASSUMPTION") for key,value in chosen.items()},
            "assumption_units": {key: value[1] for key,value in FIELDS.items()},
            "scenario": base, "sensitivity": sensitivity, "formulas": FORMULAS,
            "numerical_method": "Decimal inputs parsed from strings; finite funding-budget products use 320 significant digits and conserve allocations exactly. Scenario quantities/ratios use 80 significant digits; repeating ratios are rounded at that precision. Saved integer yoctoNEAR amounts remain exact. Continuous scenario quantities are not executable transfer instructions.",
            "sources": {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path): identity(path) for path in paths},
            "source_requests": 0}


def verify_saved():
    saved = decode(ARTIFACT.read_bytes())
    require(saved.get("schema_version") == 1, "Unsupported model artifact")
    for name, expected in saved["sources"].items():
        require(identity(ROOT/name) == expected, f"Model source changed; rebuild review needed: {name}")
    require(json_bytes(report()) == ARTIFACT.read_bytes(), "Conditional model artifact does not reproduce")
    return saved
