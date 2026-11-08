"""Reproducible illustrative capture sensitivity from validated saved inputs."""

import importlib.util
import json
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("chart_review", ROOT/"dashboard/model_review.py")
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)
DATA = ROOT/"results/101_model_capture_sensitivity.json"
VISUAL = ROOT/"docs/assets/model_capture_sensitivity.svg"


def report():
    saved_review = review.verify_saved()
    saved_model = review.model.verify_saved()
    assumptions = saved_model["assumptions"]
    reward = review.model.decode((ROOT/"results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json").read_bytes())
    review.model.require(assumptions["reward_mint_near_per_week"] == reward["recorded_reward_maps_near"], "Dated baseline mismatch")
    points = []
    for percent in range(25, 101):
        capture = format(Decimal(percent)/100, "f")
        varied = {**assumptions, "capture_fraction": capture}
        threshold = review.calculate(varied)["thresholds"]["reward_only_activity_threshold"]
        review.model.require(threshold["unit"] == "USD/week" and threshold["value"] is not None, "Invalid finite chart point")
        points.append({"capture_fraction": capture, "capture_pct": percent,
                       "required_activity_usd_per_week": threshold["value"]})
    # Three points are already recorded in the validated one-at-a-time review.
    anchors = [r for r in saved_review["major_assumption_sensitivity"]
               if r["changed_assumption"] == "capture_fraction" or r["scenario"] == "Applied baseline"]
    for point in points:
        if point["capture_pct"] not in (25, 50, 100):
            continue
        matches = [r for r in anchors if Decimal(r["assumptions"]["capture_fraction"]) == Decimal(point["capture_fraction"])]
        review.model.require(len(matches) == 1 and matches[0]["thresholds"]["reward_only_activity_threshold"]["value"] == point["required_activity_usd_per_week"], "Saved sensitivity anchor mismatch")
    zero = review.calculate({**assumptions, "capture_fraction": "0"})["thresholds"]["reward_only_activity_threshold"]
    review.model.require(zero["value"] is None and "UNREACHABLE" in zero["status"], "Zero capture plotted as finite activity")
    sources = [ROOT/"results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json",
               ROOT/"results/90_conditional_investment_model.json", review.ARTIFACT,
               ROOT/"dashboard/model_review.py", ROOT/"dashboard/conditional_model.py"]
    return {"classification": "ILLUSTRATIVE_SCENARIO_NOT_OBSERVED_REVENUE_FORECAST_OR_INVESTMENT_BREAK_EVEN",
        "varied_assumption": "capture_fraction", "x_unit": "share of eligible fees captured (%)",
        "y_unit": "eligible activity USD/week", "display_y_unit": "USD billions/week",
        "formula": "V_required = I_reward * P / (fee_rate * capture_fraction * destruction_allocation)",
        "dated_baseline": {"period": "2026-09-21/2026-09-27", "epoch_reward_mint_near_per_week": assumptions["reward_mint_near_per_week"],
            "scope": "Protocol-validated epoch rewards only; total issuance including subsidies remains unavailable. Repeating this dated week is a scenario assumption."},
        "fixed_assumptions": {k: v for k, v in assumptions.items() if k != "capture_fraction"},
        "points": points, "zero_capture": zero,
        "qualifications": ["Capture is assumed, not measured from wallet flows or fees.",
            "Custody allocation, comparator activity and horizon do not set this reward-only weekly threshold; the disjoint budget constraint still applies.",
            "Zero-capture unreachability is not a zero activity requirement. No data-source-accuracy or economic-reconciliation tolerance is implied.",
            "No price forecast, investment return, purchase execution or actual supply destruction is established."],
        "numerical_method": "Decimal string inputs; reviewed 80-digit scenario calculation; display-only rounding for axes and SVG coordinates.",
        "source_requests": 0, "sources": {str(p.relative_to(ROOT)): review.model.identity(p) for p in sources}}


def visual(data):
    with localcontext() as ctx:
        ctx.prec = 80
        fixed = data["fixed_assumptions"]
        anchors = {p["capture_pct"]: Decimal(p["required_activity_usd_per_week"])/Decimal(10**9)
                   for p in data["points"] if p["capture_pct"] in (25, 50, 100)}
        baseline = Decimal(data["dated_baseline"]["epoch_reward_mint_near_per_week"])
        def xy(point):
            x = Decimal(90)+Decimal(650)*(Decimal(point["capture_pct"])-25)/75
            y = Decimal(330)-Decimal(205)*Decimal(point["required_activity_usd_per_week"])/Decimal(10**9)/55
            return x, y
        parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="800" height="486" viewBox="0 0 800 486" role="img" aria-labelledby="title desc">',
            '<title id="title">Illustrative scenario: required weekly activity versus assumed capture</title>',
            f'<desc id="desc">At fixed price, fee rate and destruction allocation, raising assumed fee capture from 25 to 50 to 100 percent lowers required eligible activity from {anchors[25]:.2f} to {anchors[50]:.2f} to {anchors[100]:.2f} billion US dollars per week. The target is dated epoch rewards, not total issuance or investment break-even.</desc>',
            '<rect width="800" height="486" fill="#f8fafc"/>', '<g font-family="Arial, sans-serif" fill="#172033">',
            '<text x="24" y="31" font-size="24" font-weight="bold">Illustrative scenario</text>',
            '<text x="24" y="56" font-size="17">Activity required to offset the dated epoch-reward baseline</text>',
            f'<text x="24" y="80" font-size="14">Baseline: {baseline:,.2f} NEAR/week · 21–27 September 2026</text>',
            '<text x="24" y="108" font-size="14">Required eligible activity (USD billions/week)</text>']
        for tick in range(0, 51, 10):
            y = Decimal(330)-Decimal(205)*tick/55
            parts += [f'<line x1="90" y1="{y:.4f}" x2="740" y2="{y:.4f}" stroke="#dce2e9"/>',
                      f'<text x="75" y="{y+5:.4f}" text-anchor="end" font-size="14">{tick}</text>']
        for tick in (25, 50, 75, 100):
            x = Decimal(90)+Decimal(650)*(tick-25)/75
            parts.append(f'<text x="{x:.4f}" y="353" text-anchor="middle" font-size="14">{tick}%</text>')
        coords = " ".join(f"{x:.4f},{y:.4f}" for x, y in map(xy, data["points"]))
        parts.append(f'<polyline points="{coords}" fill="none" stroke="#137c8b" stroke-width="3"/>')
        for point in data["points"]:
            if point["capture_pct"] not in (25, 50, 100):
                continue
            x, y = xy(point)
            default = point["capture_pct"] == 50
            color = "#9a4e12" if default else "#137c8b"
            label = f"{Decimal(point['required_activity_usd_per_week'])/Decimal(10**9):.2f}"+(" (default)" if default else "")
            tx = x-12 if point["capture_pct"] == 100 else x+12
            anchor = "end" if point["capture_pct"] == 100 else "start"
            parts += [f'<circle cx="{x:.4f}" cy="{y:.4f}" r="5" fill="{color}"/>',
                      f'<text x="{tx:.4f}" y="{y-12:.4f}" text-anchor="{anchor}" font-size="15" font-weight="bold" fill="{color}">{label}</text>']
        parts += ['<text x="415" y="379" text-anchor="middle" font-size="15">Assumed share of eligible fees captured (%)</text>',
            f'<text x="24" y="408" font-size="14">Fixed: ${Decimal(fixed["price_usd_per_near"]).normalize():g}/NEAR price · {(Decimal(fixed["fee_rate"])*100).normalize():g}% fee · {(Decimal(fixed["destruction_allocation"])*100).normalize():g}% purchase-and-destruction allocation.</text>',
            f'<text x="24" y="431" font-size="14">Custody allocation {(Decimal(fixed["custody_allocation"])*100).normalize():g}%; {Decimal(fixed["horizon_weeks"]).normalize():g}-week horizon. Neither sets this weekly threshold.</text>',
            '<text x="24" y="454" font-size="14">0% capture: unreachable, not zero. Subsidies remain unavailable.</text>',
            '<text x="24" y="477" font-size="14">Not observed revenue, a forecast or investment break-even.</text>', '</g></svg>\n']
    return "\n".join(parts).encode()


def outputs():
    data = report()
    return {DATA: (json.dumps(data, sort_keys=True, indent=2)+"\n").encode(), VISUAL: visual(data)}
