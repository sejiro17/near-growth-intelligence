"""Independent formula walkthrough and major-assumption scenario checks."""

import copy
import importlib.util
from decimal import Decimal, localcontext
from pathlib import Path

if __package__:
    from . import conditional_model as model
else:
    try:
        import conditional_model as model
    except ModuleNotFoundError as exc:
        if exc.name!="conditional_model":raise
        spec=importlib.util.spec_from_file_location("review_model_core",Path(__file__).with_name("conditional_model.py"))
        model=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(model)

ARTIFACT = model.ROOT/"results/91_conditional_model_formula_review.json"
REBUILD = model.ROOT/"analysis/39_review_model_and_attribution.py"


def calculate(values):
    """Reviewed entry point; exact allocation bounds even for tiny fractions."""
    parsed=model.assumptions(values)
    with localcontext() as context:
        context.prec=320
        model.require(parsed["destruction_allocation"]+parsed["custody_allocation"]<=1,
                      "Allocations exceed the single captured-fee budget")
    return model.calculate(values)


def evaluate(values):
    a=model.assumptions(values)
    calculated=calculate(values)
    with localcontext() as context:
        context.prec=model.PRECISION
        reward=a["reward_mint_near_per_week"]
        price=a["price_usd_per_near"]
        target_usd=reward*price
        ad,c,f=(a[key] for key in ("destruction_allocation","capture_fraction","fee_rate"))
        revenue=Decimal(0) if target_usd==0 else target_usd/ad if ad else None
        gross_fees=Decimal(0) if revenue==0 else revenue/c if revenue is not None and c else None
        activity=Decimal(0) if gross_fees==0 else gross_fees/f if gross_fees is not None and f else None
        direct=calculated["thresholds"]["reward_only_activity_threshold"]
        # Default finite decimals divide exactly; arbitrary repeating scenarios
        # may differ only through Decimal's stated ratio rounding.
        difference=activity-Decimal(direct["value"]) if activity is not None else None
        return {"classification":"ILLUSTRATIVE_OR_USER_EDITED_SCENARIO_NOT_MEASURED_CAPTURE",
            "walkthrough":[
                {"Step":"Dated reward baseline repeated as an assumption","Value":model.text(reward),"Unit":"NEAR/week","Calculation":"I_reward"},
                {"Step":"Purchase budget needed for destruction","Value":model.text(target_usd),"Unit":"USD/week","Calculation":"I_reward × P"},
                {"Step":"Captured revenue needed","Value":model.text(revenue),"Unit":"USD/week","Calculation":"required destruction budget / a_d"},
                {"Step":"Eligible gross fees needed","Value":model.text(gross_fees),"Unit":"USD/week","Calculation":"required captured revenue / c"},
                {"Step":"Eligible activity needed","Value":model.text(activity),"Unit":"USD/week","Calculation":"required eligible gross fees / f"}],
            "formula": "V_required = I_reward × P / (f × c × a_d)",
            "units":"(NEAR/week × USD/NEAR) / three dimensionless fractions = USD/week",
            "formula_comparison_discrepancy_usd_per_week":model.text(difference),
            "direct_formula_threshold":direct,
            "target_scope":"Dated 21–27 September 2026 epoch-reward minting baseline only; not independently measured total issuance including subsidies, full supply neutrality, observed fee capture or verified revenue.",
            "defaults_not_direct_inputs_to_this_threshold":{
                "eligible_activity_usd_per_week":"Comparator for required capture and achieved destruction, not an input to the required-activity threshold.",
                "custody_allocation":"Does not enter this formula; constrains feasible destruction allocation through a_d + a_h <= 1.",
                "retained_budget_hurdle_usd_per_week":"Separate retained-budget target, not part of reward coverage.",
                "horizon_weeks":"Weekly threshold is unchanged: reward target and scenario flows scale by the same T.",
                "optional_supply_components":"Not assumed zero. Excluded from reward-only target; their absence blocks full supply-neutral calculation."},
            "price_treatment":"Assumed constant effective USD/NEAR purchase price including assumed purchase costs; no live quote, price impact, feedback, mark-to-market return or endogenous price forecast."}


def sensitivity(values):
    """One-at-a-time cases, always explicitly hypothetical; never fit to flows."""
    a=model.assumptions(values)
    scenarios=[("Applied baseline",None,dict(values),"No assumption change")]
    for key in ("reward_mint_near_per_week","price_usd_per_near","eligible_activity_usd_per_week","fee_rate","capture_fraction","destruction_allocation","custody_allocation","retained_budget_hurdle_usd_per_week","horizon_weeks"):
        factors=("0","0.5","2") if key in model.RATES else ("0.5","2")
        if key=="horizon_weeks":factors=("2",)
        for factor in factors:
            with localcontext() as context:
                context.prec=model.PRECISION
                value=a[key]*Decimal(factor)
                bound=Decimal(1)
                if key in {"destruction_allocation","custody_allocation"}:
                    other="custody_allocation" if key=="destruction_allocation" else "destruction_allocation"
                    bound=1-a[other]
                if key in model.RATES:value=min(value,bound)
                if key=="horizon_weeks":value=min(value,Decimal(520))
                value=min(value,Decimal("1e24"))
                case=dict(values);case[key]=model.text(value)
                note=f"{key} × {factor}"
                if a[key]*Decimal(factor)!=value:note+="; capped at feasible input bound"
                scenarios.append((key,key,case,note))
    # Show that missing supply terms require explicit assumptions, not silent zero filling.
    explicit=dict(values)
    for key in model.OPTIONAL:
        if explicit[key] is None:explicit[key]="0"
    scenarios.append(("Explicit missing supply terms = 0",None,explicit,"Only this scenario assumes zero for previously unavailable terms"))
    for key,change in (("additional_issuance_near_per_week","100"),("other_destruction_near_per_week","100"),("other_supply_adjustment_near_per_week","100"),("other_supply_adjustment_near_per_week","-100")):
        case=dict(explicit)
        with localcontext() as context:
            context.prec=model.PRECISION
            case[key]=model.text(Decimal(case[key])+Decimal(change))
        scenarios.append((key,key,case,"Explicit supply scenario; zero only where a missing term was explicitly filled in this case"))
    rows=[]
    for label,key,case,note in scenarios:
        try:
            result=calculate(case)
        except ValueError as exc:
            rows.append({"scenario":label,"changed_assumption":key,"changed_value":case[key] if key else None,
                         "qualification":"OUTSIDE_ACCEPTED_INPUT_DOMAIN","note":str(exc),"assumptions":case,
                         "weekly":{},"horizon_totals":{},"thresholds":{},"horizon_weeks":case["horizon_weeks"]})
            continue
        rows.append({"scenario":label,"changed_assumption":key,"changed_value":case[key] if key else None,
                     "qualification":"ILLUSTRATIVE_OR_USER_EDITED_HYPOTHETICAL_CASE",
                     "note":note,"assumptions":case,"weekly":result["weekly"],"horizon_totals":result["horizon_totals"],
                     "thresholds":result["thresholds"],"horizon_weeks":result["horizon_weeks"]})
    return rows


def applied_report(saved,values):
    """Keep v1 evidence intact while replacing all applied scenario calculations."""
    calculate(values)
    result=copy.deepcopy(saved)
    result["assumptions"]=dict(values)
    result["scenario"]=calculate(values)
    result["sensitivity"]=sensitivity(values)
    result["formula_review"]=evaluate(values)
    result["display_mode"]="ILLUSTRATIVE_DEFAULT_SCENARIO" if values==saved["assumptions"] else "USER_EDITED_HYPOTHETICAL_SCENARIO"
    baseline=Decimal(saved["evidence"]["reward_baseline"]["reward_mint_near"])
    result["assumption_status"]={key:"UNAVAILABLE" if value is None else ("DATED_BASELINE_REPEATED_AS_SCENARIO" if key=="reward_mint_near_per_week" and Decimal(value)==baseline else "EXPLICIT_SCENARIO_ASSUMPTION") for key,value in values.items()}
    result["sources"][str(Path(__file__).relative_to(model.ROOT))]=model.identity(Path(__file__))
    result["sources"][str(ARTIFACT.relative_to(model.ROOT))]=model.identity(ARTIFACT)
    return result


def report():
    original=model.verify_saved()
    values=original["assumptions"]
    rows=sensitivity(values)
    return {"schema_version":1,"status":"OFFLINE_REVIEW_ILLUSTRATIVE_DEFAULTS_NOT_OBSERVED_ECONOMIC_CAPTURE",
        "original_result_preserved":str(model.ARTIFACT.relative_to(model.ROOT)),
        "corrections":["Every displayed applied-result group explicitly identifies illustrative defaults or user-edited hypothetical assumptions.","Sensitivity now covers every major assumption, including explicit supply scenarios, without changing measured unavailable values.","The reviewed calculation entry point checks allocation bounds at 320-digit precision, preventing an extremely small over-allocation from rounding down in the historical validator.","Zero-target walkthroughs remain zero even when capture or allocation is zero; positive targets with zero coefficients stay unreachable."],
        "review":evaluate(values),"major_assumption_sensitivity":rows,
        "sources":{str(path.relative_to(model.ROOT)):model.identity(path) for path in (model.ARTIFACT,Path(__file__),REBUILD)},
        "source_requests":0}


def verify_saved():
    saved=model.decode(ARTIFACT.read_bytes())
    for name,expected in saved["sources"].items():
        model.require(model.identity(model.ROOT/name)==expected,f"Model review source changed: {name}")
    model.require(model.json_bytes(report())==ARTIFACT.read_bytes(),"Model review result does not reproduce")
    return saved
