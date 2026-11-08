# Research Plan

The current [five-deliverable status table](deliverable_status.md) reviews the
original completion criteria against saved results through 104. Cohort measurements
and scenario implementation are validated outputs; wider execution coverage and
economic calibration remain incomplete. Supply, the full revenue/buyback ledger
and broad population attribution are still partial. The
[integration validation](integration_validation.md) records the unified offline
command, checks and remaining visual-review gap; older rebuild commands below
preserve their historical checkpoints.

Result 103 adds **one known owner–asset balance reconciliation** at the saved
full-window anchors, incorporated alongside the native ledger in result 104.
It is not complete asset coverage, complete flow history or fee/purchase
attribution. The closed withdrawal investigation and unallocated native
residual are unchanged. The status table separates useful saved-input work,
specific source/access dependencies and the investment conclusion each gap
prevents. Current result 100 also records model default provenance; no wallet
stock decrease calibrates fee capture, purchases or destruction.

The prioritized next requirement is an access decision for the existing
[lossless header/chunk acquisition specification](supply_header_chunk_acquisition.md):
retained A→B heights 216877934–216921133, with saved predecessor and independent
closing controls. An accessible export under declared permission/volume limits
would advance independent epoch net-debit coverage. It would not by itself
separate gross burn/subsidies or complete eight weeks. Neardata bulk remains
paused; this step launches no collection, provider contact or access changes.

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what
does that imply for its long-term investment case?

## Purpose

I examine whether headline growth is accompanied by repeat account
participation, activity beyond the leading contributors and successful
execution.

The economic analysis measures recorded execution spending and observed
supply movements, then considers what they support about demand for NEAR.

The project is intended for research analysts, ecosystem teams and
developers investigating the quality of network growth.

## Observation Period

The primary analysis covers 24 August–18 October 2026: eight complete
Monday–Sunday weeks in UTC.

I selected this period after checking historical coverage, transaction
records and execution-outcome matching. Within the primary period,
checked outcomes matched exactly one ACTION receipt.

Records through 24 October were retained for potential follow-up.
The partial week after 18 October is excluded from full-week growth
comparisons. The weekly return analysis uses complete follow-up weeks
within the primary period.

Closing supply on 23 August provides the opening baseline for supply
comparisons.

The completed transaction-only extension covers 6 July–18 October 2026:
fifteen complete UTC weeks and 79,171,891 transactions (results 38 and 39).
It compares both first-to-final-week endpoints and the first four weeks
(6 July–2 August) with the final four weeks (21 September–18 October).
The dashboard presents both comparisons alongside the original analyses.

Endpoint transactions and active signing accounts declined 10.63% and
24.65%; four-week averages increased 16.39% and 79.47%, respectively.
Growth direction therefore depends on the comparison period. The final
four weeks include the account spike and are not adjusted for deletion
activity. These descriptive comparisons do not establish causality,
sustained adoption or user retention. Average weekly accounts are not
four-week unique accounts; participation frequency is weighted across
account-weeks and top-ten concentration by transactions, with weekly
rankings recalculated.

Extended weekly totals and account-days reconcile to the saved daily
checks; overlapping weeks reconcile to the original signing results,
except for the newly available prior-week change on 24 August. Script
`analysis/09_extended_activity_comparison.py` validates result 38 and
produces result 39. Economic measurements, detailed execution analysis
and receipt-matching conclusions remain scoped to the original eight
weeks; the extension does not resolve earlier outcome-matching gaps.

Earlier unresolved outcome matching during 1 July–22 August remains
documented. The coverage checks do not establish complete ingestion.

## Analytical Approach

| Area | Approach |
|---|---|
| Activity | Compare weekly transactions and active signing accounts across complete weeks. |
| Account returns | Follow activity cohorts into later complete weeks and examine lifecycle context. |
| Concentration | Measure leading signers' and original receivers' transaction shares. |
| Growth drivers | Hold the first week's leading group fixed and decompose endpoint changes by account. |
| Execution quality | Examine selected contributors' actions, initial receipt outcomes, costs and diagnostic errors. |
| Account profiles | Combine weekly activity, destinations and actions with documented attribution evidence. |
| Economics | Compare receipt volume, average costs, transaction conversion costs and observed supply movements. |
| Decision implications | Connect findings to investigation priorities and a conditional investment argument. |

Cohort follow-ups use comparable weekly intervals. Unavailable follow-up
periods are excluded rather than counted as zero returns.

The fixed-account comparison holds membership constant. Weekly rankings,
by contrast, are recalculated each week. These answer different questions
about concentration and growth.

## Data and Workflow

Source dataset:

`bigquery-public-data.crypto_near_mainnet_us`

The workflow uses:

1. SQL to extract, validate and summarise public blockchain records.
2. Saved CSV and JSON exports to preserve the analytical inputs.
3. Python to validate derived comparisons and prepare account profiles.
4. Archival RPC responses to investigate selected failed receipts.
5. Streamlit and Plotly to present the evidence interactively.

The dashboard reads saved exports. Opening it does not query BigQuery,
make RPC requests or refresh the data.

## Deliverables

- An interactive dashboard with seven views: Growth, Growth drivers,
  Account returns, Concentration, Economics, Decision priorities and
  Account explorer.
- Reproducible SQL, Python scripts and saved results.
- An investment thesis connecting activity evidence to token-economic
  mechanisms, risks and conditions for further evaluation.
- Supporting notes covering validation, economic mechanisms, account
  attribution and decision priorities.

## Interpretation Rules

Accounts are treated as identifiers rather than verified people.
Service associations require supporting evidence; unknown roles remain
unverified.

Transactions, actions and receipts are analysed as separate units.
Initial receipt outcomes are not treated as complete execution-chain
results, and overlapping action-category counts are not summed.

First observed means first seen within the available window, not
first-ever use. Account absence is not automatically user churn.

Recorded execution spending is distinguished from product revenue,
permanent burning, persistent token holdings and holder returns.
Conversion and receipt costs are combined by calendar period rather
than attributed to matched transaction chains.

Observed patterns are not attributed to bots, campaigns, retries or
other causes without supporting evidence. Economic mechanisms described
in current documentation are not assumed to establish historical
parameters.

## Validation and Review

Checks cover record uniqueness, dates, account fields, outcome matching,
cost validity, cohort totals, account-profile coverage and reconciliation
of derived results.

Unresolved coverage and supply-reconciliation differences remain in the
investigation record.

Dashboard checks assess whether controls and exports work. Reader feedback
is used to assess clarity and navigation, separately from technical
validation or professional investment review.

## Supporting Notes

- [Data checks and investigation history](data_checks.md)
- [Investment thesis](investment_thesis.md)
- [Economic mechanisms](economic_mechanisms.md)
- [Account attribution](account_attribution.md)
- [Decision priorities](decision_priorities.md)

## Post-Submission Measurement Sequence

The supply and bounded wallet-provenance findings are consolidated in
[the 6 November validation record](data_checks.md#6-november-2026--priorities-12-consolidated).
Supply reconciliation and revenue origin remain unresolved; these components
are unavailable inputs to an investment model rather than assumed value capture.

The bounded [persistent economic activity](persistent_activity_plan.md) phase
is complete. Results 56–61 validate nine complete transaction checkpoints,
three exact-return initial-receipt measurements and two corresponding
repeated-checkpoint subsets. Three incomplete transaction follow-ups and
unmeasured receipt checkpoints remain unavailable. Results 60–61 compare two
overlapping cohorts during one shared submission week, without causal claims.

The dashboard and investment thesis integrate the validated supply, bounded
withdrawal and persistence findings through result 62. Result 90 adds the dated
weekly reward baseline, current evidence limits and an implemented conditional
scenario model. Full-window independent issuance, actual gross burn, revenue
origin and holder value capture remain unresolved.
No further collection is part of this measurement phase. Published derived
evidence is rebuilt with `python3 -B analysis/23_rebuild_published_results.py`
using saved inputs only; publication follows a separate review.

## Remaining Research Tasks and Completion Criteria

The published version is an intermediate checkpoint. The five original research
deliverables below remain the objective; a bounded pilot or a documented blocker
is not a completed full ledger, reconciliation or attribution census. The plan
distinguishes intermediate measurements from full completion criteria. The
bounded withdrawal-provenance investigation stays closed.

Current supply evidence adds a validated 23-epoch walk for 21–27 September,
exact weekly endpoints and offset reward maps. Result 72 validates the 21 newly
captured configurations together with A/B, completing active configuration
coverage and identifying this week's epoch reward minting. Results 70–71 retain
the original request plan and pre-collection status. The
[configuration and source assessment](supply_protocol_assessment.md)
records the offline reproduction command and the blocked bulk-header dependency.
The [lossless acquisition specification](supply_header_chunk_acquisition.md)
and result 73 define the exact A→B pilot and its acceptance criteria. Anonymous
point/header access is now established; complete range retention is not. The
[three-account native ledger plan](three_wallet_native_ledger_plan.md) begins
priority 2 with SQL 45, preserving the closed provenance result and unverified
economic classifications. Saved results 74–76 now validate the native action
layer and eight weekly subledgers, including internal-movement cancellation and
bounded DAO/log evidence. Exact balance bridges, full multi-asset coverage and
economic attribution remain unresolved; BigQuery access is unavailable.
Results 78–80 now add all six historical native states, an exact stock-flow
comparison and a consolidated ledger. The `1csfundsadmin` difference remains
unallocated, with no collection solely to explain it. Token/internal-asset
coverage and explicit fee/purchase attribution remain incomplete. The separate
[one-block Neardata pilot](neardata_single_block_pilot.md) now validates saved
supply block A in result 83: exact header/chunk fields and inclusion-timed net
debit match the canonical control. This resolves one-point archive access, not
A→B retention, bulk volume/cost, weekly debit or gross burn/subsidy decomposition.
No additional collection is scheduled by that validation.
The separately bounded [header pilot](neardata_contiguous_header_pilot.md) passed
for 100 heights in result 85. The optimized segment retained 44 additional valid
blocks before HTTP 429; results 88–89 preserve that stopped run. Current validated
coverage is **216877934–216878077: 144 blocks**, with 0.5486610196812742 NEAR of
independently summed inclusion-timed net header debit and zero integer supply
identity discrepancy. This sampled debit is **not extrapolated** to an epoch or
week and does not separate gross burn from subsidies. The error response states
**30 blocks/minute** for this route; the configured 120-request/minute start gate
was not exceeded. The observed restriction supersedes the earlier throughput
assumption for this acquisition; its exact bucket/shared-IP behaviour is unknown.

**Neardata bulk collection is paused. No retries, host/IP rotation, cap increases
or slower recovery are authorized.** Raw captures remain outside the repository;
results 88–89 and the submission tag are preserved. Full-epoch/week and the
eight-week gross-component accounting remain incomplete. No source collection,
provider contact or access/billing changes are scheduled.
The original eight-week validator residual is not replaced by this week's
conditional reward-map subtraction.

| Order and original deliverable | Remaining technical work | Full completion criteria and current limit |
| --- | --- | --- |
| 1. Supply reconciliation | Preserve the completed 23-epoch checks, weekly reward-mint result and 144-block header coverage. Bulk collection is paused: no retries, host/IP rotation, cap increases or slower recovery. Retain the exact missing-range and gross-component dependencies without extrapolating sampled debit. | Full target: eight weekly opening/closing identities with independent issuance, inclusion-timed actual burn and other verified adjustments, canonical/precision coverage and zero exact arithmetic discrepancies. Completed intermediate measurements: protocol-validated reward minting for 21–27 September and a bounded header prefix. Full-epoch/week independent debit, gross burn and subsidy decomposition remain incomplete. |
| 2. Evidence-based revenue/buyback ledger | Preserve results 74–80 and current layered ledger 104: native entries, exact full-window endpoint states, weekly flow observations, internal-leg cancellation and the one known owner–asset balance reconciliation in result 103. Keep the 1cs difference unallocated without residual-specific collection. Require complete token/internal-asset coverage, historical asset balances/associations, contract policy/source evidence and explicit fee/purchase settlement before classification. BigQuery access is unavailable; no access retries or new wallet collection. The closed withdrawal trace remains closed. | Full target: historically supported accounts/assets/roles, eight-week opening/closing balances and classified flows distinguishing fees, customer principal, solver settlements, refunds, internal movements, distributions and verified buybacks. Native endpoints and one known owner–asset balance reconciliation do not complete that ledger or establish complete flow history. Historical fee-origin, multi-asset and exact balance-adjustment coverage remain dependencies. |
| 3. Persistent economic activity | Preserve the completed cohort measurements; verify consistency of saved results, display denominators, concentration, overlap, missing follow-up and deletion context before final integration. No new cohort extraction. | Completed within measured scope: several starting-week activity cohorts, complete exact +1/+4/+8 checkpoints, all-three-checkpoint return subsets, transaction contributions, selected initial-receipt outcomes/spending and explicit execution tails. Incomplete follow-ups stay unavailable; repeated return is not continuous weekly activity and initial-receipt success is not complete-chain settlement. |
| 4. Deeper attribution and execution | Preserve the Sweat delegated-claim case in results 96–97 and the wx transfer-and-callback case in results 98–99, their exact submission timestamps, returned graphs and recorded charges. Compare selected cases separately with population action/initial-outcome statistics and the 18 failed tinykoala controls. The bounded public history lookup resolved one wx identity dependency; no further collection is scheduled. Neither case estimates a population settlement rate. | Full target: reproducible attribution and execution coverage across the original window without duplicated transactions/actions/receipts, with verified historical role anchors. Completed intermediate measurements: one explicit delegation, one accepted FT transfer-call and a reproducible coverage table. Broad relayer/user attribution, economic funder/ownership, internal exchange balances and complete population descendant coverage remain incomplete. |
| 5. Conditional investment model | Implemented in result 90, analysis 38 and the dashboard Decision priorities view: editable assumptions, dated baseline, explicit units/equations, mutually exclusive budget uses, sensitivity, activity/capture thresholds and measurable change-of-mind conditions. Preserve the distinction between modeled destruction, purchases held and revenue. Remaining empirical calibration depends on deliverables 1–2 and 4; do not replace missing inputs with transfers or spending. | Conditional-model implementation complete within its stated scenario scope after offline tests/rebuild. Full evidence-backed economic calibration remains incomplete. Missing supply components stay null unless explicitly assumed. The model establishes no fair value, expected return, staking APR, observed revenue yield or price target. |
| Integration and final review | Rebuild published derived outputs offline, reconcile evidence/claim tables, run relevant tests and dashboard interaction checks, review downloads and sensitive/unrelated files, and resolve confirmed validation failures. Incorporate only validated claims. Retain the known visual-review gap unless browser access permits an actual review. | Reviewable, reproducible release candidate with no raw evidence changes, population overlaps and material economic limitations visible. Model equations must work without invented balances, percentages or cash flows. Publication remains a distinct step. |

The supply bulk acceptance gate requires an existing retained lossless export or
object path, schema and source precision, canonical interval/predecessor coverage,
read permission and bounded cost. The documented BigQuery schema and GCS joined
export do not supply inclusion-timed debit fields. No provider contact,
infrastructure provisioning or repeated unsuccessful source search is scheduled.
If this dependency remains unresolved, full supply reconciliation remains
incomplete; missing evidence is not replaced by a balancing figure.

Model calculations supported now are exact observed net total-supply growth and
explicit conditional stock/flow scenarios. The 23-map reward sum is now
protocol-validated epoch reward minting for 21–27 September and supports a weekly
epoch-reward issuance rate, excluding separately unavailable subsidies. This
does not establish issuance across the full eight-week window.

The [conditional model specification](conditional_investment_model.md) documents
the funding identity, disjoint supply/custody channels, threshold definitions and
analyst-selected decision criteria. Reproduce the existing published evidence
and model from saved inputs with:

```bash
python3 -B analysis/38_conditional_investment_model.py --with-published --check
```

The rebuild disables network operations and verifies existing files without
overwriting them. The historical `analysis/23_rebuild_published_results.py`
command remains available for the original 17 published derived artifacts.

The [model formula review](conditional_model_review.md) preserves result 90 and
adds exact illustrative derivation, all-major-assumption sensitivity and reviewed
input guards in result 91. Current UI results label illustrative defaults and
user-edited hypothetical scenarios explicitly. Review and the bounded priority-4
plan reproduce with `python3 -B analysis/39_review_model_and_attribution.py
--with-model --check`.

Priority 4 now has a [selected delegated-claim case and coverage table](priority4_attribution_plan.md).
Result 96 validates one explicit network Delegate action, its distinct declared
sender and claim.sweat/token.sweat calls, eight returned successful receipt
outcomes and 0.0007690267153439 NEAR of recorded charges. Result 97 preserves
that result and adds one exact submission-header check establishing membership
in the original window. The case is one of 13,704,363 saved Sweat transactions;
it does not estimate users or population settlement. The largest explicit
forwarding gap in the saved growth-outcome comparison is wx-cruce's 398,968
SUCCESS_RECEIPT_ID initial outcomes without population-wide descendant coverage.
Results 98–99 now resolve one identity dependency through a bounded free account
lookup and validate one accepted transfer-call into v2.ref-finance.near. All six
returned receipt outcomes succeeded, with matched callback data and an exact
submission-header timestamp. Empty msg and the recorded calls/logs provide no
swap/output-asset or revenue evidence; internal exchange credit remains
unverified. No further scan or bulk collection is scheduled; broad historical
attribution and full downstream coverage remain unfinished. Results 92–97
preserve the earlier plans, controls and Sweat case unchanged.
An issuance-minus-supply difference remains implied net debit until
inclusion-timed evidence independently measures it. Neither that difference nor
execution spending supplies actual burn, product revenue or holder returns.

Completion review must continue to state whether the full revenue/buyback ledger,
full issuance/burn reconciliation, broad relayer attribution and conditional
investment model have individually met their criteria. Progress on a bounded
component does not close the other deliverables.
