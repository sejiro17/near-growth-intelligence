# Conditional model formula review

[Result 90](../results/90_conditional_investment_model.json) and its original
calculation sources remain unchanged. [Result 91](../results/91_conditional_model_formula_review.json)
adds an independently evaluated walkthrough, one-at-a-time sensitivity for every
major assumption and reviewed input guards. No measured input is recalibrated.

## Exact illustrative default calculation

The target is **618,436.074970164323861118656646 NEAR/week**, the independently
recorded and historically validated epoch-reward mint during **21–27 September
2026 only**. Repeating it as a weekly scenario is an assumption. It does not
cover independently measured total issuance including subsidies; that measurement
remains unavailable.

| Illustrative-default step | Exact value | Unit |
| --- | ---: | --- |
| Reward target `I_reward` | 618436.074970164323861118656646 | NEAR/week |
| Multiply by assumed effective price `P = 5 USD/NEAR` | 3092180.374850821619305593283230 | USD/week required for purchase/destruction |
| Divide by destruction allocation `a_d = 0.25` | 12368721.49940328647722237313292 | USD/week captured revenue required |
| Divide by assumed capture `c = 0.5` | 24737442.99880657295444474626584 | USD/week eligible gross fees required |
| Divide by assumed fee rate `f = 0.001` | 24737442998.80657295444474626584 | USD/week eligible economic activity required |

Thus `V_required = I_reward × P / (f × c × a_d)`, approximately
**$24.74 billion/week in the illustrative default scenario**. Units are
`(NEAR/week × USD/NEAR) / dimensionless fractions = USD/week`. This is not a
threshold calibrated from observed fee capture, verified product revenue or
wallet inflows. It is not an investment break-even price or expected return.

The other defaults have separate functions:

- `$100 million/week` of eligible activity is the illustrative comparator, not
  an input to `V_required`. It produces $100,000/week gross eligible fees,
  $50,000/week captured fee revenue, $12,500/week destruction budget and
  2,500 NEAR/week purchased/destroyed at the assumed price. These remain
  illustrative results, not observations.
- The `0.25` custody allocation is absent from the threshold formula. It shares
  the single captured budget with destruction, so `a_d + a_h <= 1`. At fixed
  `a_d`, changing custody changes the remaining budget and held purchases, not
  reward-only coverage. The illustrative custody quantity is 2,500 NEAR/week;
  the illustrative remaining budget is $25,000/week before costs/taxes.
- The `$1 million/week` remaining-budget hurdle is a different chosen target.
  It produces a separate illustrative $4 billion/week activity threshold; it
  does not set the $24.74 billion reward-only threshold.
- The `1-week` horizon scales totals, not the weekly threshold. Repeating all
  weekly inputs for `T` weeks multiplies both the reward target and funding
  flows by `T`; `T` cancels in the weekly threshold. No compounding,
  annual-issuance observation or expected-return extrapolation is introduced.
- Additional issuance, other disjoint destruction and signed adjustments are
  null, not zero. Their absence blocks full supply-neutral calculations. Only
  separately labeled sensitivity cases explicitly assume zeros for these terms.

Price is a hypothetical constant **effective purchase price**, including assumed
purchase costs. Doubling it doubles the required activity and halves purchased
NEAR for the same dollar budget. The model has no live quote, slippage curve,
price feedback or mark-to-market return. It does not convert native inflows into
USD revenue.

## Review findings and corrections

The default threshold agrees exactly with the direct formula. Revenue is the
parent funding flow: destruction budget + custody budget + remaining budget =
captured revenue. These are uses of one budget, not extra inflows. Only assumed
destruction reduces supply; held purchases are not burned. Operating costs,
taxes, beneficial ownership and holder distributions remain unmodeled.

Positive reward targets with zero capture, fee rate or destruction allocation
are unreachable: the threshold is null with an explicit unreachable status, not
zero. A zero target has a zero threshold. Full supply neutrality remains null
unless every required supply component is explicitly assumed.

The historical validator could round an extremely small allocation excess back
to one at 80-digit precision. The reviewed calculation entry point checks the
allocation bound at 320-digit precision before running the unchanged historical
calculator. This guard is used by the current UI and reviewed custom-scenario
export. The saved original result and its original source fingerprints remain
reproducible; no original evidence is rewritten.

The UI now labels each result group and table row **Illustrative default** or
**User-edited hypothetical**. The formula walkthrough carries units at every
step. Expanded sensitivity covers reward minting, price, eligible activity, fee,
capture, both allocations, the remaining-budget hurdle, horizon and optional
supply assumptions. Input-domain bounds are explicit; unsupported sensitivity
cases remain unavailable. Sensitivity is not a price or return forecast.

Reproduce the original artifacts, model review and priority-4 plan offline:

```bash
python3 -B analysis/39_review_model_and_attribution.py --with-model --check
```

For reviewed custom assumptions use an unused output:

```bash
python3 -B analysis/39_review_model_and_attribution.py --assumptions /path/to/scenario.json --output /path/to/new_reviewed_scenario.json
```

Both commands disable source requests. The older analysis-38 command remains the
reproduction path for immutable result 90; current UI/custom scenarios use the
reviewed guard. The browser visual-review gap remains open; headless checks do
not establish browser presentation.
