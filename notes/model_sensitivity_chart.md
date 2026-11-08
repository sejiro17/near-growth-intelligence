# Illustrative capture sensitivity

The [README chart](../docs/assets/model_capture_sensitivity.svg) varies one
assumption: the share of eligible fees captured. It is scenario arithmetic,
not observed revenue, a forecast or investment break-even.

The reward-only activity threshold is:

`V_required = I_reward × P / (fee_rate × capture_fraction × destruction_allocation)`

Units are `(NEAR/week × USD/NEAR) / dimensionless fractions = USD/week`.
The vertical axis displays USD billions/week of economically eligible
fee-bearing activity, not transaction counts or observed chain volume.

| Fixed input | Value / scope |
| --- | --- |
| Dated epoch-reward baseline | 618,436.074970164323861118656646 NEAR during 21–27 September 2026; [protocol-validated result 72](../results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json). Repeating this week is an assumption. |
| Effective purchase price | Illustrative $5/NEAR, not a live quote or price forecast. |
| Fee rate | Illustrative 0.1% of eligible activity. |
| Purchase-and-destruction allocation | Illustrative 25% of captured fees. |
| Other saved assumptions | Custody allocation 25%, one-week horizon, $100m/week activity comparator and $1m/week retained-budget hurdle. These do not set the reward-only weekly threshold; disjoint budget constraints still apply. |
| Missing supply components | Additional issuance, other destruction and adjustments stay null. Subsidies and full supply neutrality remain unavailable. |

The curve uses the existing reviewed Decimal calculator at each percentage point
from 25% to 100% capture. Exact model values in
[result 101](../results/101_model_capture_sensitivity.json) remain USD/week
strings; chart labels round to two decimals in billions/week. The 25%, 50% and
100% anchors reproduce the corresponding saved
[result 91](../results/91_conditional_model_formula_review.json) cases exactly.
Zero capture is unreachable for a positive reward target and is not plotted as
a zero activity requirement.

[Analysis 45](../analysis/45_model_sensitivity_chart.py) creates the scenario
data and SVG from preserved results 72, 90 and 91. The original model/results
and persistence SVG remain unchanged. Both figure generation steps are included
in the unified offline command:

```bash
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```

Higher assumed capture lowers required activity with all other inputs fixed;
it does not establish that such capture exists or is feasible. Revenue funds
the disjoint destruction/custody budgets and is not added to its uses. See the
[model review](conditional_model_review.md) and
[five-deliverable status](deliverable_status.md) for the unclosed evidence gaps.
