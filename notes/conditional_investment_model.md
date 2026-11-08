# Conditional investment model

The current conclusion is **persistent execution use is demonstrated; durable
holder value capture is not**. Supporting evidence includes exact +8 returns of
47.41% and 46.18% for the August activity cohorts, successful selected initial
execution and recorded spending. Contrary evidence includes baseline-sensitive
growth, a 52.59% decline in active days per account-week, 73.98%/75.12% top-ten
concentration among +8 returner transactions and material initial failures.
Populations overlap; initial-receipt success is not complete-chain success.
Sources: results 39 and 56–62, as consolidated in the unchanged result 62.

[Result 90](../results/90_conditional_investment_model.json) is a reproducible
conditional economics model, not a fair-value estimate, expected-return forecast
or price target. It neither converts wallet inflows into revenue nor fills supply
components from observed spending or implied debit. The bounded withdrawal
provenance investigation remains closed with revenue origin unverified.

[The formula review](conditional_model_review.md) preserves result 90 and adds
result 91: exact default derivation, expanded major-assumption sensitivity,
explicit illustrative labels and a reviewed guard against extremely small
over-allocation. The current UI and reviewed custom export use that guard.

## Measured inputs and unavailable measurements

| Saved evidence | Supported input | Limit |
| --- | --- | --- |
| Result 72 | 618,436.074970164323861118656646 NEAR of protocol-validated reward minting during 21–27 September 2026; exact net supply movement +611,555.974235517852937718656646 NEAR | One dated week, excluding separately unavailable subsidies. Their difference is implied debit, not verified burn. |
| Results 85 and 88–89 | 144 validated blocks, 216877934–216878077; sampled inclusion-timed net debit 0.5486610196812742 NEAR | No debit extrapolation. Full-epoch/week accounting remains incomplete. The route returned a stated 30-block/minute restriction. Bulk collection is paused without retry, host/IP rotation, cap increase or slower recovery. |
| Result 80 | Three-wallet native flows and historical balance comparison; external net native inflow 956,945.106578107785216431387923 NEAR | Unclassified, not revenue or purchases. Stock-flow difference 0.0010849311842748 NEAR stays unallocated; multi-asset coverage incomplete. |
| Results 103–104 | One known owner–asset balance reconciliation: the 1csfundsadmin internal `nep141:wrap.near` endpoint decrease equals one saved successful transfer | Context only, not model calibration. It does not establish complete assets/flows, fee origin, recipient ownership or purchases. Neither a zero residual nor holdings determine a fee/take rate or capture fraction. |
| Results 54 and 62 | Successful signed internal transfer followed by native withdrawal | Revenue origin and any holder beneficiary remain unverified. Internal mt_burn is not native destruction. |
| Results 56–62 | Account checkpoint participation, transaction contribution, selected initial-receipt outcomes and recorded spending | Cohort overlap, six-day execution tails, initial-receipt scope and FLOAT-derived cost precision remain explicit. No conversion to fee revenue or dollar activity. |

Observed product revenue, economic fee-bearing USD volume, historical fee/capture
rates, verified purchases held, actual gross burn, subsidies and holder cash
flows are null. They remain null even when scenario outputs are numeric. Saved
baseline values and provenance are preserved exactly; displayed values alone are
rounded.

The current integrated evidence also records every model default's value, unit,
source and status in `model_input_provenance`. Only the reward value comes from
the dated measured reward week, and repeating it is a scenario assumption.
The remaining numerical defaults are illustrative; optional supply components
remain unavailable. Results 103–104 do not change any default or reviewed
scenario result. The dashboard exposes this provenance alongside the model;
applied exports separately identify user-edited assumptions.

## Editable inputs

The saved defaults are in
[config/conditional_model_assumptions.json](../config/conditional_model_assumptions.json).
The dashboard form edits an in-memory copy and its JSON download includes every
applied value, unit and assumption classification.

| Symbol / input | Unit | Default and status |
| --- | --- | --- |
| `T`: horizon | Whole weeks | 1; hypothetical constant-input horizon, allowed 1–520 |
| `I_reward`: reward minting | NEAR/week | Exact dated reward baseline repeated as an editable scenario |
| `I_additional`: additional minting | NEAR/week | Null; optional explicit assumption, including subsidies if supplied |
| `B_other`: other destruction | NEAR/week | Null; optional explicit assumption, disjoint from modeled purchase/destruction |
| `A_other`: other signed supply adjustment | NEAR/week | Null; optional explicit signed assumption |
| `P`: effective purchase price | USD/NEAR | 5; illustrative, including assumed purchase costs, not a market quote |
| `V`: eligible economic activity | USD/week | 100,000,000; illustrative fee-bearing activity, not observed chain volume or transaction count |
| `f`: product fee rate | Fraction | 0.001 (0.1%); illustrative, not a universal historical rate |
| `c`: captured share of eligible fees | Fraction | 0.5; illustrative after principal, pass-through settlements, refunds and rebates are excluded |
| `a_d`: purchase/destruction allocation | Fraction of captured budget | 0.25; assumed implementation, not observed deployment |
| `a_h`: custody-purchase allocation | Fraction of captured budget | 0.25; purchases assumed held without resale/release during the horizon |
| `Q`: remaining-budget hurdle | USD/week | 1,000,000; chosen analyst hurdle, not observed profit or required holder yield |

Fractions are restricted to [0, 1], `a_d + a_h <= 1`, and price must be positive.
Except signed adjustments, amounts must be nonnegative finite decimal strings.
No float is used to parse an assumption. Empty optional supply values remain
null; entering zero is an explicit scenario assumption and does not alter the
measured record. Operating costs/taxes, price impact, market liquidity, inventory
resales and holder distributions are not modeled.

## Accounting and separate outputs

```text
Eligible gross fees (USD/week)       = V × f
Captured fee revenue R (USD/week)    = V × f × c
Destruction purchase budget         = R × a_d
Custody purchase budget             = R × a_h
Remaining budget before costs/taxes  = R × (1 − a_d − a_h)
Purchased and destroyed D (NEAR/week)= R × a_d / P
Purchased and held H (NEAR/week)     = R × a_h / P

Destruction budget + custody budget + remaining budget = R
Conditional supply change (NEAR/week)
    = I_reward + I_additional + A_other − B_other − D
```

Revenue is a parent funding flow; adding it to its uses double counts. The same
purchased NEAR cannot be in both allocations. `H` never reduces total supply.
`D` represents one assumed purchase followed by destruction and is counted once.
The additional `B_other` input must represent a distinct destruction channel.
The remaining budget is not profit or a holder cash distribution. Holding
purchases for the horizon does not measure wallet closing balances or reduce
total/circulating supply. No combined “value capture” sum or investment return is
produced.

The default arithmetic gives R = $50,000/week, D = 2,500 NEAR/week,
H = 2,500 NEAR/week and $25,000/week remaining before costs/taxes. All are
**scenario outputs**. Full conditional supply change remains unavailable because
the three optional supply assumptions are missing. Horizon totals multiply
weekly flows by `T`; they assume fixed inputs, no resale and no compounding.
Repeating a dated reward baseline is not an annual issuance estimate or forecast.

## Economic activity and capture thresholds

```text
Reward-only activity hurdle (USD/week)
    = I_reward × P / (f × c × a_d)
Reward-only required capture fraction
    = I_reward × P / (V × f × a_d)

Full conditional supply-neutral activity hurdle (USD/week)
    = max(0, I_reward + I_additional + A_other − B_other)
      × P / (f × c × a_d)

Remaining-budget activity hurdle (USD/week)
    = Q / (f × c × (1 − a_d − a_h))
Remaining-budget required capture fraction
    = Q / (V × f × (1 − a_d − a_h))
```

These are arithmetic coverage thresholds, not investment break-even prices or
expected returns. The reward-only hurdle deliberately excludes missing supply
components; it is not full supply neutrality. The full threshold is null until
all required supply assumptions are explicit. A positive target with zero
coefficient is **unreachable**, with a null numeric result; it is not a zero
threshold. A required capture fraction above one is infeasible at the chosen
activity, price and allocation. A zero target has a zero threshold.

At the defaults, the reward-only activity threshold is approximately
**$24.74 billion/week** and the $1 million/week remaining-budget hurdle requires
**$4 billion/week** of eligible activity. No observed economic volume is available
for comparison. Sensitivity cases halve/double the assumed price and reduce the
assumed capture share, including zero. They preserve the distinction between
cash revenue, custody and destruction and do not calculate price returns.

Finite funding-budget products use 320 significant Decimal digits to preserve
the allocation identity for the accepted input range. Scenario ratios use 80
significant digits; repeating ratios are rounded there. This arithmetic policy
does not establish source accuracy. Integer source amounts remain exact. A
continuous model quantity is not an executable integer-yoctoNEAR transfer plan.

## Measurable change-of-mind conditions

These thresholds are explicitly analyst-selected decision rules, not protocol
parameters, results already observed or significance tests:

- Strengthen persistence: at least three complete +8 starting-week cohorts each
  have >=40% exact +8 returns and <=50% top-ten returner transaction share.
  Disclose cohort membership overlap; do not treat them as independent users.
- Weaken persistence: three complete +8 cohorts have <25% returns or >80%
  top-ten transaction share. Missing follow-up is not failure.
- Strengthen scoped execution: three comparable checkpoint weeks each have
  >=95% initial success with >=99.9% unique link/cost coverage. Complete-chain
  settlement still requires descendant evidence.
- Strengthen economic capture: eight classified and reconciled weekly asset
  ledgers establish fee origin, payer/asset/amount and successful settlement,
  then compare measured capture with the chosen model hurdle. Below-hurdle
  capture over eight independently attributed weeks or unverified claimed
  deployment weakens that specified mechanism.
- Change the gross supply conclusion only after eight complete canonical weekly
  identities independently identify issuance, burn, subsidies and adjustments
  with zero integer arithmetic discrepancy. Sampled debit is not extrapolated.

No new collection is authorized by these conditions. The five-deliverable
[research plan](research_plan.md) retains the outstanding accounting, multi-asset
ledger and broad attribution/execution requirements.

## Reproduction and verification

```bash
python3 -B analysis/39_review_model_and_attribution.py --with-model --check
```

This checks the original 17 published artifacts, result 90 and review/attribution
results 91–93, using saved
inputs only with network operations disabled. Without `--check`, missing named
derived artifacts are created exclusively. Existing artifacts must reproduce
byte-for-byte and are never overwritten. Results 88–89 and all raw exports are
unchanged. The dashboard reads the compact saved inputs, not the external raw
header store, and only performs in-memory scenario calculations.

For another saved assumption file, copy the config, edit its decimal strings,
and select an unused output filename:

```bash
python3 -B analysis/39_review_model_and_attribution.py --assumptions /path/to/scenario.json --output /path/to/new_reviewed_scenario_result.json
```

The dashboard's default artifact/config remain a consistent reproducible pair;
interactive edits are exported separately and do not write repository files.
Unit tests check null-versus-zero semantics, exact baseline precision, allocation
limits, separate custody/supply effects, threshold inversion, infeasibility,
price/horizon sensitivity, invalid inputs and immutable offline rebuilds. UI
tests exercise form submission, invalid assumptions and exported applied values.
The existing browser visual-review gap remains explicit; headless rendering is
not browser verification.
