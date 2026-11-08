# NEAR: growth quality and conditional investment thesis

## Current conclusion

**What grew?** First-four-week versus final-four-week averages increased 16.39%
for transactions and 79.47% for active signing accounts. Fifteen-week endpoints
instead declined 10.63% and 24.65%. The final four weeks include the account spike;
active days per account-week fell 52.59%. Growth depends on the baseline.

**How much persisted?** Of accounts active in the 10 and 17 August starting weeks,
47.41% and 46.18% returned at exact week +8; 37.48% and 37.83% were active at all
three +1/+4/+8 checkpoints. These overlapping activity cohorts are not newly
acquired or verified users. Their top ten returners produced 73.98% and 75.12%
of +8 transactions: persistence was material, but concentrated.

**What executed successfully?** Three exact-return initial-receipt pilots recorded
82.35–92.99% success, with complete observed matching/cost controls and explicit
six-day lookup tails. Initial success does not establish descendant success.
Separate selected Sweat and wx graphs are covered and successful; 18 selected
tinykoala graphs each contain failure. Those examples do not estimate population
settlement rates.

**What economic demand or value capture is demonstrated?** Recorded execution
spending establishes use of execution capacity. A dated week of epoch reward
minting and a native wallet ledger improve the economic evidence, but full-window
issuance/burn reconciliation, fee-origin attribution, actual purchase execution
and holder value capture remain incomplete. The reviewed model tests hypothetical
capture thresholds; it does not establish a fair value, expected return or price target.

The current conclusion is conditional: persistent useful execution is supported
within the measured scope, while a durable holder-value mechanism is unproven.
Unverified mechanisms are not evidence that distributions or economic effects
did not occur. The [five-deliverable review](deliverable_status.md) distinguishes
validated outputs from the remaining completion criteria.

## Scope and contrary activity evidence

Transaction research covers **6 July–18 October 2026**, fifteen complete UTC weeks
and 79,171,891 transactions. Network calendar-period economics cover **24 August–18
October**, eight weeks and 44,284,794 transactions. Selected cohorts start on
10 August, with initial-receipt lookups through 24 October. The earlier unmatched
outcome coverage is not resolved by the transaction-only extension.

| Measure | First four weeks | Final four weeks | Change |
| --- | ---: | ---: | ---: |
| Average weekly transactions | 5,132,084.50 | 5,973,048.50 | +16.39% |
| Average weekly active signing accounts | 156,738.50 | 281,297.00 | +79.47% |
| Active days per active account-week | 4.0409 | 1.9158 | −52.59% |
| Weekly top-ten transaction share | 67.3087% | 52.3887% | −14.9200 percentage points |

The comparison is 6 July–2 August versus 21 September–18 October. Average weekly
accounts are not four-week unique accounts; account-week participation and
transaction-weighted concentration have different denominators. Lower signer
concentration does not establish diverse independent owners or economic demand.

In the original eight weeks, endpoint transactions rose 3.69% while active
signers fell 7.38%. Transactions outside the fixed first-week top ten increased
52.50%; that original leading group's transactions fell 19.83%. Largest named
endpoint increases included tinykoala +148,950, wx +137,767 and 0here.tg +137,531.
They are changes, not period totals or newly acquired users. Sources: results
18–24, 38–39 and [attribution coverage](priority4_attribution_plan.md).

## Persistence and initial execution

The cohort layer measures four starting-week activity cohorts and nine complete
exact-week checkpoints. Three incomplete checkpoints stay unavailable. Repeated
return means all three selected +1/+4/+8 checkpoints, not every intervening week;
any-return unions are separate measures. Initial-receipt execution coverage is
limited to the following three exact-return groups and their two overlapping
repeated-checkpoint subsets:

| Population | Submission week | Transactions | Initial success | Conversion NEAR | Initial-receipt NEAR |
| --- | --- | ---: | ---: | ---: | ---: |
| 10 Aug +8 | 2026-10-05 | 3,888,965 | 91.63% | 178.09129530 | 1,449.81277262 |
| 10 Aug all checkpoints | 2026-10-05 | 3,831,697 | 91.52% | 176.09711249 | 1,430.08964496 |
| 28 Sep +1 | 2026-10-05 | 5,174,834 | 82.35% | 224.11412340 | 2,316.49986074 |
| 17 Aug +8 | 2026-10-12 | 3,528,043 | 92.99% | 163.70758505 | 1,312.24525169 |
| 17 Aug all checkpoints | 2026-10-12 | 3,475,043 | 92.91% | 161.91744775 | 1,286.26544448 |

These rows overlap and cannot be added. During 5–11 October, the August +8 and
September +1 groups share **58,957 accounts and 3,871,009 transactions**. The
August repeated-checkpoint group is a subset of its +8 group. Spending for the
union/intersection is unavailable. Different starting weeks, horizons and
shared membership prevent a causal comparison of success rates.

Conversion follows submission weeks. Initial-receipt spending follows unique
execution blocks/dates, includes failed receipts and excludes descendants.
The six-day tails are 12–17 and 19–24 October, with one distinct selected receipt
in each tail. Those partial weeks do not provide equal elapsed follow-up for
every submission. Zero observed link/cost exclusions and matching executors do
not prove independently complete ingestion. Costs are FLOAT-derived; decimal
summation preserves saved arithmetic, not original integer precision. Sources:
results 56–62 and [data checks](data_checks.md).

Concentration and lifecycle context remain contrary evidence. Only 18.14% of
spike-week accounts returned the next week; 309,280 absent accounts had successful
receipts containing self-deletion actions, 82.53% of the absent group. Absence
is not automatically user churn. Three execution pilots below 95% initial
success and returner concentration above 70% limit a claim of broad, reliable use.

Successful initial execution nevertheless extends beyond each +8 population's
own ten leading signers. [Result 105](../results/105_returner_initial_success_outside_top10_bounds.json)
uses matching cohort, submission-week and transaction definitions with one
assessed initial receipt per transaction:

| Starting cohort → +8 submission week | Transactions outside own top ten | Successful initial receipts outside top ten: lower–upper bound | Transaction success fraction: outward-rounded bounds |
| --- | ---: | ---: | ---: |
| 10 August → 5–11 October | 1,011,853 | 686,154–1,011,853 | 67.81%–100.00% |
| 17 August → 12–18 October | 877,862 | 630,408–877,862 | 71.81%–100.00% |

For N population transactions, T own-top-ten transactions and S successful
initial receipts, the bounds are `max(0, S−T)` and `min(S, N−T)`, with denominator
`N−T`. Lower percentages round down, upper percentages up; exact integer counts
and rational fractions are retained. These prove minimum numbers of successful
initial receipts beyond the ten leading signers, **not measured account-level
success rates, broad human adoption or complete-chain settlement**. The cohorts
overlap and remain separate. The result strengthens evidence of execution use
beyond the leading group without removing concentration or establishing value
capture. Membership alignment rests on reviewed SQL and matching exported
controls; full row-level membership sets and independent ingestion completeness
remain unavailable. Missing or ambiguous receipt coverage suppresses the bounds.
Spending outside the top ten is not inferred. See [bounds methodology](returner_execution_bounds.md).

## Population execution and selected mechanisms

Tinykoala's 715,518 failed initial receipts are 91.90% of its 778,588 signed
transactions, with approximately 211.1629 NEAR of recorded failed-initial-receipt
costs. Wx has 6,441 failures, 7,872 SUCCESS_VALUE and 398,968 SUCCESS_RECEIPT_ID
initial outcomes among 413,281 transactions. The forwarding status alone does
not establish successful descendants. These are selected contributor populations,
not network-wide failure rates.

| Signer | Selected mechanism | Coverage of signed population | Selection denominator | Returned graph evidence |
| --- | --- | --- | --- | --- |
| sweat-relayer.near | Delegated claim | 1 / 13,704,363 (0.0000072969%) | 13,246,938 DELEGATE_ACTION transactions: 0.0000075489% selected | 8 receipt outcomes; 0 selected graphs with failure |
| wx-cruce.near | Accepted transfer-call | 1 / 413,281 (0.0002419661%) | 398,968 Initial SUCCESS_RECEIPT_ID outcomes: 0.0002506467% selected | 6 receipt outcomes; 0 selected graphs with failure |
| tinykoala595.near | Failed execution controls | 18 / 778,588 (0.0023118774%) | 715,518 Failed initial receipts: 0.0025156600% selected | 54 receipt outcomes; 18 selected graphs with failure |
| sweat-relayer.near → jars-oracle.sweat | Delegated jar deposit | 1 / 13,704,363 (0.0000072969%) | 3,039,759 saved destination-bucket transactions: 0.0000328973% selected | 8 successful receipt outcomes; booster application rejected |

Sweat's explicit Delegate authorizes a distinct on-chain sender into claim.sweat,
then token.sweat and a claim callback. It has eight successful receipt outcomes
and 0.0007690267153439 NEAR of recorded transaction/receipt charges. Submission
is exactly 23 September, 07:11:24.906615725 UTC. Declared authority is not verified
human identity, ownership, service affiliation or an economic funding source.

A separate selected Sweat case, submitted at **23 September,
00:00:02.273417299 UTC**, explicitly delegates from `jars-oracle.sweat` to
`token.sweat.ft_transfer_call`, then `v2.jars.sweat.ft_on_transfer` and the token
resolver. A transfer and jar deposit are recorded for exactly
`3000000000000000000` token base units; the receiver returns unused amount
`"0"` and the resolver returns the full amount. All eight returned receipt
outcomes succeed, with no missing children and one matched callback dependency.
Nevertheless, the application's `apply_booster` event rejects the beneficiary.
Receipt success therefore does not establish every requested application effect.
The payload type is `airdrop`; its economic purpose, beneficiary ownership and
human adoption are not independently established. Recorded charges are exactly
**0.0012424938755553 NEAR**, not revenue or actual burn.

This one case covers **0.000032897344822402…%** of the saved 3,039,759-transaction
destination bucket, not a representative sample or success rate. Its underlying
delegated actor is a named account rather than proof of an independent user.
Neither this mechanism nor its outcome is assigned to the rest of that bucket.
The two Sweat rows share a signer population and are not added. Sources:
[result 106](../results/106_sweat_jars_selected_mechanism_2026-09-23.json) and
[selected jars case](sweat_jars_case_study.md).

Wx's direct-signed transfer-call goes wrap.near → v2.ref-finance.near → resolver.
Its six returned receipt outcomes succeed, with matched callback data and
0.0007174786101312 NEAR of recorded charges. Submission is exactly 23 September,
16:17:16.824648967 UTC. The amount is `2041882904280066641796431` raw wrap.near
token units with empty msg. Receiver return is "0" and resolver return is the full
amount: an accepted transfer-and-callback, consistent with funding/deposit.
There is no swap/output-asset evidence or independently verified internal exchange
credit. No explicit Delegate action appears; a differing predecessor alone would
not establish delegation.

The 18 tinykoala controls were selected from failures: each has one failed and
two successful receipt outcomes. Seventeen sampled slippage errors and one
insufficient-deposit error do not establish population error-cause frequencies.
All three case sets have covered returned graphs without missing emitted action
outcomes or unresolved callback dependencies. A covered graph may contain failure;
coverage is not independent proof of historical completeness or business purpose.
Selected charges are already within their respective network records and are not
added again to network spending. Sources: results 26, 95–99,
[Sweat/coverage](priority4_attribution_plan.md) and [wx case](wx_cruce_case_study.md).

## Supply: measured components and remaining accounting

| Measurement | Scope | Result / limitation |
| --- | --- | --- |
| Observed net supply movement | Closing 23 August to closing 18 October | +4,935,983.9798346 NEAR, FLOAT-derived; total supply is not circulating supply. |
| Supply minus raw validator balance change | Same eight weeks | +16,599.51437846169 NEAR; 0.336296% of net movement and 0.00127259% of opening supply. |
| Sum of absolute daily residuals | Same eight weeks | 84,284.66902631883 NEAR; netting hides cancellation. 23 September remains +11,427.31386968814 NEAR. |
| Protocol-validated epoch reward minting | 21–27 September only, 23 applications | Exact 618,436.074970164323861118656646 NEAR. Separately unavailable subsidies are excluded. |
| Exact endpoint supply movement | Same dated week | +611,555.974235517852937718656646 NEAR. |
| Implied weekly net debit | Reward minting minus exact movement | 6,880.1007346464709234 NEAR; not independently measured weekly debit or gross burn. |
| Independently summed header net debits | 23 application blocks; separately a 144-block prefix | Boundary-only 0.1041228119233375 NEAR; prefix 0.5486610196812742 NEAR. Scopes overlap and are not added or extrapolated. |
| Full-window issuance, full-week independent debit, gross burn and subsidies | Original target | Unavailable, not zero. Eight weekly gross-component identities remain open. |

At two exact block hashes, 231 validator update records were absent from selected
BigQuery evidence; all 449 blank-chunk observations examined were valid RPC
updates. One omitted account's exact parent/post change was
+1,128.147246190549662124317432 NEAR. This is an account balance change, not issuance.
The ingestion-collision explanation remains unconfirmed and cannot be generalized
to other dates or unrelated transaction findings. Recovered updates cannot simply
be added to daily totals because later predecessor comparisons may already include
their effects. This is not a balancing adjustment.

Exact RPC integer identities are distinguished from original FLOAT-derived
observations. The 0.00001 NEAR tolerance checks saved arithmetic only. Validator
balance changes are not issuance; spending, negative supply movements and named
account transfers are not measured destruction. The 144-block prefix has zero
integer identity discrepancy but no separate canonical tail control; bulk
collection is paused. Sources: results 42–46, 72, 85, 88–89 and
[supply protocol/source limits](supply_protocol_assessment.md).

## Native wallet ledger and revenue attribution

The native layer covers successful execution-dated flows during 24 August–18
October and exact opening/closing liquid-plus-locked states for three accounts.
All flows remain economically unclassified; account names do not establish fees,
revenue, buybacks or ownership. Displayed stock/flow values below are rounded;
[result 80](../results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json)
preserves every exact integer.

| Account | Opening NEAR | Closing NEAR | Native net flow NEAR | Unallocated stock-flow difference NEAR |
| --- | ---: | ---: | ---: | ---: |
| fefundsadmin.sputnik-dao.near | 1,610,269.316441 | 1,913,463.450662 | 303,194.134221 | 0 |
| 1csfundsadmin.sputnik-dao.near | 502,798.938526 | 270.875891 | -502,528.063720 | 0.0010849311842748 |
| buybacks.multisignature.near | 858,247.431222 | 2,014,526.467298 | 1,156,279.036077 | 0 |

Two internal transfers totalling **502,794 NEAR** cancel between the selected
wallets; they are excluded from external net inflow of exactly
**956,945.106578107785216431387923 NEAR**. The **0.0010849311842748 NEAR** difference
is entirely unallocated at 1csfundsadmin. A zero difference elsewhere does not
prove a complete reconciliation. Fees, function-call deposits, refunds, rewards,
deletion proceeds, receipt-funding timing or missing coverage may affect balances;
none is assigned as an unexplained balancing amount. Weekly flows are saved;
weekly opening/closing stocks are unavailable.

The separate one-day diagnostic found 22 successful native transfers totalling
8,000.969220749197522847764034 NEAR to fefundsadmin. A bounded trace validates a
successful signed internal transfer followed by a 1,252.862790024676320487808800
NEAR withdrawal after unwrapping. Its generic signed credit, memo=null, does not
establish fee origin, historical fee-role configuration or allocation from
commingled balances. This withdrawal is already in the native ledger and is not
added again. The one-credit provenance investigation remains closed; internal
mt_burn is not native supply destruction.

One separate **known owner–asset balance reconciliation** now supplements the
native ledger. For `1csfundsadmin.sputnik-dao.near`, the `nep141:wrap.near`
balance inside `intents.near` was exactly `990000000000000000000000000` base
units at the saved 23 August close and `1000100010001000100010` at the saved
18 October close. The decrease, `989998999899989998999899990` base units,
equals the one saved successful internal transfer to
`c0addac935f49baee1909a6fb4f08b57352a6d8c8ce7da27c59545fe45c5838c`.
The difference is zero using integer arithmetic. This links known holdings
to an observed movement; it does not establish recipient ownership, a purchase
or fee origin. It covers **one known pair for one of three wallets**; the total
asset-pair denominator is unknown. Other offsetting movements could exist.
The saved day-close anchors are not independent canonical midnight-edge proofs.
No amounts are added to native flows, no native residual is allocated, and no
model capture assumption is calibrated from this balance decrease. Sources:
[exact comparison 103](../results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json)
and [current layered ledger 104](../results/104_wallet_ledger_with_known_asset_reconciliation.json).

Complete token/internal Verifier balances and transfers, historical role/source-policy
matches and explicit purchase settlement remain incomplete. Native flows cannot
supply a complete multi-asset revenue/buyback ledger. Unverified distributions
do not prove nonoccurrence. Sources: results 47–54, 74–80 and
[ledger limits](three_wallet_ledger_consolidation.md) and
[known-asset coverage](known_asset_wallet_coverage.md). Complete discovery needs
retained historical token events indexed by owners/recipients and verified
internal-account associations; no accessible complete index is established by
the saved evidence. Missing assets remain unavailable, not zero balances or flows.

## Reviewed conditional model

The [editable model](conditional_investment_model.md) in Decision priorities is
an arithmetic scenario tool, not an investment return forecast. For eligible
fee-bearing activity V (USD/week), fee fraction f, captured share c and effective
purchase price P (USD/NEAR):

- Hypothetical captured fee revenue: **R = V × f × c**, USD/week.
- Purchase-and-destruction: **D = R × a_d / P**, NEAR/week.
- Purchases held in custody: **H = R × a_h / P**, NEAR/week; holdings do not reduce supply.
- Remaining budget before costs/taxes: **R × (1 − a_d − a_h)**, USD/week.

Allocations are nonnegative and a_d + a_h ≤ 1. Revenue funds these disjoint uses;
adding revenue to its uses double counts. Custody assumes no release during the
hypothetical horizon, without establishing observed closing balances or circulating
supply effects. Horizon totals multiply weekly flows by an explicit number of
weeks; the dated reward baseline's repetition is an assumption. Price is an
editable hypothetical execution price, not a live quote or valuation input.

**Illustrative defaults:** $100 million/week of eligible activity × 0.1% fee ×
50% capture = $50,000/week captured revenue. At $5/NEAR and 25% allocation to each
purchase channel, this gives 2,500 NEAR/week destroyed, 2,500 NEAR/week held and
$25,000/week remaining budget. These are illustrative scenario outputs, not
observed fees, trades, burn, revenue or expected investment returns.

The **illustrative default reward-offset threshold** is
618,436.074970164323861118656646 NEAR/week × $5/NEAR ÷
(0.001 × 0.5 × 0.25) = approximately **$24.74 billion/week** of eligible activity.
It covers only the dated epoch-reward baseline, not independently measured total
issuance including subsidies. Required capture at the default $100 million volume
exceeds 100%, so that target is infeasible under those assumptions. It is not an
investment break-even price. Zero capture can make targets unreachable; missing
supply inputs keep full conditional neutrality unavailable. Implied debit, wallet
flows and spending never fill those missing components. Sources: preserved result
90, reviewed result 91 and [formula/sensitivity review](conditional_model_review.md).

## Conditions that would change the thesis

These are analyst-selected decision rules, not protocol requirements or tests of
statistical significance. They remain editable and are not outcomes already met.

| Premise | Evidence that would strengthen it | Evidence that would weaken it / current limit |
| --- | --- | --- |
| Persistence and breadth | Three complete cohorts with ≥40% exact +8 returns and ≤50% top-ten returner transaction share. | Three below 25% returns or above 80% concentration. Only two complete +8 cohorts are measured here, with concentration above 70%. |
| Reliable execution | ≥95% initial-receipt success and ≥99.9% unique link/cost coverage across three comparable checkpoints; descendant evidence for chain-level claims. | Pilot initial success is 82.35–92.99%. Observed matching is complete, but wider descendants and ingestion remain unverified. |
| Revenue and deployment | Eight historically attributed, classified and reconciled weekly multi-asset ledgers; verified purchases/destruction and capture meeting the explicitly chosen hurdle. | Capture below that hurdle over eight independently attributed weeks, or unverified deployment behind a purchase/destruction claim. Native inflows and a successful withdrawal do not meet the test. |
| Supply account | Eight complete weekly independent issuance/burn/adjustment identities with zero integer discrepancies and canonical coverage. | Missing gross components, unverified historical semantics or incomplete coverage keep that claim unavailable. Current one-week/prefix evidence is partial. |
| Underlying demand | Population attribution links concentrated infrastructure to durable independent uses and funders. | Selected successful cases coexist with substantial failed activity and unknown actor ownership; no population extrapolation follows. |

Useful execution, concentration and supply growth do not alone determine an
investment outcome. The evidence supports continued conditional evaluation of a
value mechanism; it does not establish whether that mechanism is attractive at
any price. Fresh purchases, durable holdings, holder distributions and net selling
pressure remain unmeasured.

## Completion status and reproduction

The [five-deliverable table](deliverable_status.md) records original criteria,
validated outputs, remaining gaps and concrete work possible from saved inputs.
The revenue/buyback ledger, full issuance/burn reconciliation and broad relayer
attribution remain incomplete. Cohort measurements are validated within their
scope; wider execution coverage remains partial. Conditional-model implementation
is validated, while its empirical economic calibration remains incomplete.

```bash
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```

The unified rebuild disables network/subprocess operations, reproduces current
published artifacts and checks that existing files match without overwriting
raw evidence. Large external raw header revalidation requires retained external
paths; integrated prefix arithmetic uses saved validated summaries. Source
precision, lookup tails and historical manifests remain qualified. See
[integration validation](integration_validation.md), [data checks](data_checks.md),
[original research plan](research_plan.md) and [economic mechanisms](economic_mechanisms.md).
The submission tag and original history are preserved.
