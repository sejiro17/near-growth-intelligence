# Data Checks

This log records the checks performed, results observed and interpretation
boundaries identified during the research. Earlier entries describe what
was established at that stage; later entries record subsequent findings.

## 25 October 2026 — Historical Partition Coverage

I checked partition metadata for transactions, receipt_actions,
execution_outcomes and accounts before selecting the observation period.

The transactions, receipt_actions and execution_outcomes tables each
returned 2,275 nonempty daily partitions, spanning 23 July 2020 to
25 October 2026. All three had nonempty partitions for the 116 dates
from 1 July to 24 October.

The accounts table did not appear in the filtered results. The reason
was not established; its absence does not demonstrate that it contains
no data.

This established partition availability rather than record completeness.
The observation period remained provisional pending further checks.

Query: `sql/01_check_partition_coverage.sql`
Results: `results/01_partition_coverage_2026-10-25.csv`

## 25 October 2026 — Daily Partition Counts

I inspected daily partition row counts for transactions, receipt_actions
and execution_outcomes across the 116 candidate dates.

All expected dates were present, with no missing or zero counts.

Counts changed sharply on several dates, including a transaction increase
on 27 September and elevated receipt-action and outcome counts on
10–11 October. Receipt-action rows substantially exceeded outcome rows
on 15 October.

The tables represent different units, so their counts need not match.
The check did not establish whether changes reflected activity, ingestion
issues or other causes.

Query: `sql/02_daily_partition_counts.sql`
Results: `results/02_daily_partition_counts_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Daily Transaction Validation

I checked transaction records across all 116 candidate dates.

The results contained 86,547,133 rows. Daily row counts matched distinct
transaction-hash counts and the partition metadata exported previously.

There were no missing transaction hashes, signing accounts, receiving
accounts or timestamps. Timestamps matched their block dates, and every
day contained activity in all 24 UTC hours.

Daily active signing accounts ranged from 42,517 to 177,196.

These checks established daily uniqueness among the selected hashes,
not uniqueness across dates or complete ingestion. Counts included all
recorded transaction statuses.

Query: `sql/03_daily_transaction_checks.sql`
Results: `results/03_daily_transaction_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Transaction Status and Hash Uniqueness

All 86,547,133 candidate-window transactions had SUCCESS_RECEIPT_ID
status, with no missing statuses. Daily totals matched result 03.

The full-window distinct transaction-hash count also equalled 86,547,133,
establishing uniqueness across the selected records.

SUCCESS_RECEIPT_ID was not interpreted as successful downstream execution.

Query: `sql/04_transaction_status_checks.sql`
Results: `results/04_transaction_status_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Execution-Outcome Validation

The candidate window contained 486,375,712 outcome rows:

| Status | Rows |
|---|---:|
| SUCCESS_VALUE | 437,621,841 |
| SUCCESS_RECEIPT_ID | 36,472,564 |
| FAILURE | 12,281,307 |

Daily totals matched result 02. There were no missing receipt identifiers,
executor accounts or timestamps, and no timestamp-date mismatches.
Gas and token-cost values were present, finite and nonnegative.

Within each date-and-status group, row counts matched distinct receipt
identifiers. Uniqueness across groups and the execution units represented
still required separate checks.

Query: `sql/05_daily_execution_outcome_checks.sql`
Results: `results/05_daily_execution_outcome_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Execution Units on 15 October

I matched outcome identifiers dated 15 October against transaction hashes
and receipt identifiers recorded from 14–16 October.

All 14,335,195 outcomes matched exactly one ACTION receipt. None matched
transaction hashes, DATA receipts or both identifier types, and none
remained unmatched.

Status counts reconciled to result 05:

- FAILURE: 132,614.
- SUCCESS_RECEIPT_ID: 340,772.
- SUCCESS_VALUE: 13,861,809.

Counts matched distinct identifiers within each resulting group.
No outcome matched multiple lookup rows.

This established the execution units for the inspected day. It also
showed that SUCCESS_RECEIPT_ID occurs among ACTION receipt outcomes
and cannot alone identify transaction-processing records.

Query: `sql/06_inspect_execution_units.sql`
Results: `results/06_execution_units_2026-10-15.csv`

## 25 October 2026 — Full-Window Outcome Matching

I checked outcome-identifier uniqueness across 1 July–24 October and
matched identifiers against receipt_details dated 30 June–25 October.

All 486,375,712 identifiers were unique across the selected dates and
statuses. Of these, 482,361,311 matched exactly one ACTION receipt.

The remaining 4,014,401 outcomes, approximately 0.83%, had no receipt
match within the lookup window. Counts reconciled to result 05.

The unmatched records were retained for investigation.

Query: `sql/07_full_window_outcome_matching.sql`
Results: `results/07_full_window_outcome_matching_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Unmatched Outcome Investigation

All 4,014,401 unmatched outcomes were dated 1 July–22 August.
None occurred from 23 August to 24 October.

The unmatched records comprised:

- 3,841,814 SUCCESS_VALUE outcomes.
- 144,068 SUCCESS_RECEIPT_ID outcomes.
- 28,519 FAILURE outcomes.

Their total reconciled to result 07. None of their identifiers matched
transaction hashes recorded from 30 June to 25 October.

The cause remained unresolved. These results informed the selection
of the later primary observation period.

Query: `sql/08_inspect_unmatched_outcomes.sql`
Results: `results/08_unmatched_outcomes_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Weekly Activity Baseline

I summarised validated daily transactions into eight complete
Monday–Sunday weeks from 24 August to 18 October.

Totals reconciled to 44,284,794 transactions across 56 dates.
Weekly averages and percentage changes reconciled to the daily source.

Transactions peaked at 6,590,352 during 28 September–4 October.
In the final week, transactions declined 23.31% and average daily active
signing accounts declined 39.50% from the preceding week.

Against the first week, final-week transactions increased 3.69%, while
average daily active signing accounts declined 29.87%.

Signing-account-days count an identifier once per active day.
They are not weekly distinct accounts.

Script: `analysis/01_weekly_activity_baseline.py`
Results: `results/09_weekly_activity_baseline_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Signing Activity and Concentration

Weekly transaction totals and signing-account-days reconciled to the
baseline. Reported averages, concentration shares and account changes
reconciled to the exported counts.

Weekly active signing accounts peaked at 457,768 during
28 September–4 October, up 198.16% from the preceding week.
Of these, 376,771, or 82.31%, were active on only one day.

Final-week active signing accounts fell to 129,446: down 66.33% from
the preceding week and 7.38% below the first week.

The ten busiest signing accounts generated 48.17%–67.76% of weekly
transactions. Rankings were recalculated each week.

These results describe identifiers rather than verified people.
Within-week activity does not establish participation in later weeks.

Query: `sql/10_weekly_signing_activity.sql`
Results: `results/10_weekly_signing_activity_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Account Returns

I measured later weekly activity among accounts active in each starting
week.

All cohort sizes reconciled to result 10. The export contained 30 eligible
cohort-follow-up combinations, with correct percentages and no incomplete
follow-up weeks. Starting-week counts matched their cohort sizes.

Next-week active shares ranged from 18.14% to 77.96%.

Of the 457,768 accounts active during 28 September–4 October:

- 83,037, or 18.14%, were active the following week.
- 77,133, or 16.85%, were active two weeks later.

Four-week active shares ranged from 47.70% to 51.65% among the four
cohorts with complete follow-up.

Cohorts include all active signing accounts, not necessarily new users.
They overlap. Follow-ups measure activity in a particular week, not
continuous participation or cumulative returns.

Query: `sql/11_weekly_account_returns.sql`
Results: `results/11_weekly_account_returns_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Receiver Activity

The export contained twenty receivers per week, giving 160 rows.
Weekly totals, rankings, transaction shares and concentration totals
reconciled to the saved counts.

The ten busiest receivers accounted for 60.85%–70.22% of weekly
transactions. The twenty busiest accounted for 70.48%–80.81%.

game.hot.tg ranked first in the first two weeks.
v2.ref-finance.near ranked first in the remaining six.

These are original transaction destinations, not necessarily verified
applications or downstream destinations. Receiver-level signing-account
counts can overlap and must not be summed as network-wide unique accounts.

Absence from a top-twenty ranking does not establish zero activity.

Query: `sql/12_weekly_receiver_activity.sql`
Results: `results/12_weekly_receiver_activity_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Receipt Execution Costs

Weekly counts and status breakdowns reconciled to the validated daily
results, totalling 280,743,473 receipt execution outcomes.

Each week contained seven dates, with no unexpected statuses or invalid
gas and token-cost values.

Recorded receipt execution costs totalled approximately 65,878.09 NEAR,
including 4,218.49 NEAR associated with failed receipts. Failure shares,
cost shares and average costs reconciled.

Weekly costs peaked at approximately 11,950.25 NEAR during 5–11 October.
Final-week costs were approximately 10,544.79 NEAR, compared with
5,770.56 NEAR in the first week.

These figures use receipt execution dates and exclude transaction
receipt-conversion costs. They do not trace complete transaction chains
or independently measure revenue, permanent burning or holder value.

Source cost fields use floating-point storage, so amounts are approximate.

Query: `sql/13_weekly_execution_costs.sql`
Results: `results/13_weekly_execution_costs_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Combined Weekly Growth and Costs

I combined weekly activity, signing-account and receipt-cost exports.

Source values were preserved. Week boundaries, overlapping totals and
signing-account-days reconciled. Indices and weekly changes calculated
correctly.

With the first week indexed to 100, the final week recorded:

- Transactions: 103.69.
- Weekly active signing accounts: 92.62.
- Recorded receipt execution costs: 182.73.

The series changed at different rates. Transactions use submission dates,
while receipt costs use execution dates. The indices compare weekly
trends rather than matched transaction-chain costs.

Script: `analysis/02_weekly_execution_costs.py`
Results: `results/14_weekly_growth_and_costs_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Receiver Activity by Subsequent Account Participation

I grouped accounts active during 28 September–4 October according to
their participation during 5–11 October, then ranked their starting-week
receivers.

The groups reconciled to 457,768 accounts and 6,590,352 transactions.
Rankings, transaction shares and interaction percentages reconciled.

The 83,037 returning accounts represented 18.14% of the cohort and
generated 5,788,805 starting-week transactions, or 87.84%.

The remaining 374,731 accounts generated 801,547 transactions, or 12.16%.

Among returning accounts, v2.ref-finance.near received the most
starting-week transactions: 1,139,455.

Among absent accounts, wallet.kaiching ranked first with 134,826
transactions from two signing accounts. This receiver therefore did
not explain the group's large account count.

Only twenty receivers per group were exported, and account-interaction
counts can overlap. The associations do not identify causes, independent
users, automation or campaigns.

Query: `sql/15_spike_cohort_receivers.sql`
Results: `results/15_spike_cohort_receivers_2026-09-28_to_2026-10-11.csv`

## 25 October 2026 — Spike Cohort Transaction Actions

I compared starting-week action types between accounts active and absent
the following week.

Group totals and percentages reconciled. Matched records had no missing
action indices or duplicate indices within transaction-action-kind groups.

Among absent accounts, 309,286, or 82.54%, submitted transactions
containing DELETE_ACCOUNT actions. These accounted for 309,601
transactions.

Among returning accounts, 80,191, or 96.57%, submitted transactions
containing FUNCTION_CALL actions. DELEGATE_ACTION appeared in 1,945,506
transactions from 28 signing accounts.

There were 474 transactions without matching action records:
seven from returning accounts and 467 from absent accounts.
The reason remained unresolved.

Submitted deletion actions did not alone establish successful deletion
or that the signer was the deleted account. Transactions and accounts
can appear under several action types; counts must not be summed as
distinct totals. Delegated payloads were not expanded.

Query: `sql/16_spike_cohort_actions.sql`
Results: `results/16_spike_cohort_actions_2026-09-28_to_2026-10-11.csv`

## 25 October 2026 — Spike Account Deletion Outcomes

I checked initial receipt outcomes for transactions containing
DELETE_ACCOUNT actions during 28 September–4 October, allowing
outcomes through 11 October.

All 309,642 deletion transactions reconciled to the previous action
results and matched exactly one outcome. In every case, the signer
equalled the receiver and the executor matched that receiver.

Among absent accounts:

- 309,587 deletion transactions from 309,280 accounts had SUCCESS_VALUE
  outcomes.
- Those accounts represented 82.53% of the absent group and 67.56%
  of the full starting-week cohort.
- Fourteen deletion transactions from eleven accounts failed.

Account counts can overlap between successful and failed groups.

Among returning accounts, 41 self-deletion transactions from nine
accounts had SUCCESS_VALUE outcomes. Later activity under those
identifiers does not establish continuity of ownership.

The results establish successful receipt executions containing
self-deletion actions. Motives, ownership and later recreation were
not established. The large absent-account count should not be treated
as ordinary user churn.

Query: `sql/17_spike_account_deletion_checks.sql`
Results: `results/17_spike_account_deletion_checks_2026-09-28_to_2026-10-11.csv`

## 26 October 2026 — Leading Signing Accounts

I identified each week's twenty busiest signing accounts and tracked
their combined set across all eight weeks.

The export contained 408 account-week rows covering 51 accounts.
Weekly totals, active-account counts and top-ten transaction counts
reconciled to result 10. Histories, rank flags and shares passed checks.

sweat-relayer.near ranked first every week and submitted 13,704,363
transactions, or 30.95% of the period total. Its weekly transactions
declined from 1,954,610 to 1,301,312: a decrease of 33.42%.

Five accounts appeared in the top ten every week:

- sweat-relayer.near
- intents.near
- closemeat6237.near
- omni-relayer.bridge.near
- meteor-relayer.near

Transactions outside each week's top ten increased from 1,539,788 to
2,063,276, or 34.00%. Membership changes across weekly rankings, so
this does not track a fixed account group.

Roles and ownership were unverified at this stage. Repeated weekly
and full-period summary fields require deduplication before aggregation.

Query: `sql/18_weekly_leading_signing_accounts.sql`
Results: `results/18_weekly_leading_signing_accounts_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Leading Account Destinations

I examined original receivers for the five accounts ranked in the
top ten every week.

The export contained 399 receiver rows across forty account-weeks.
Transaction totals and active days reconciled to result 18.
Rankings, shares and coverage totals passed checks. No missing or
empty receiver identifiers were reported.

Weekly distinct receivers ranged from:

- 120,242 to 223,109 for sweat-relayer.near.
- 16,691 to 17,694 for meteor-relayer.near.

Their weekly top-twenty receiver lists captured 69.98% and 2.98%
respectively of their transactions across the period. These are
aggregated weekly rankings, not fixed receiver lists.

All 2,769,479 transactions signed by intents.near targeted itself.
Most omni-relayer.bridge.near transactions targeted omni.bridge.near,
btc-connector.bridge.near and zcash-connector.bridge.near.

closemeat6237.near had five receivers each week. v2.ref-finance.near
ranked first throughout and received 914,376 of its 1,620,042 transactions.

Signing concentration can coexist with many destinations. Original
receivers do not identify all downstream participants, particularly
in delegated execution.

Account-week summaries repeat across rows and require deduplication.

Query: `sql/19_leading_account_activity.sql`
Results: `results/19_leading_account_activity_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Leading Account Actions

The export contained 178 rows across forty account-weeks.
Transaction totals reconciled to result 18. Every selected transaction
matched an action record, with no missing indices or FUNCTION_CALL
method names.

DELEGATE_ACTION appeared in:

- 13,246,938 sweat-relayer.near transactions: 96.66%.
- 1,239,064 meteor-relayer.near transactions: 98.02%.

All 2,769,479 intents.near transactions contained execute_intents calls.

For closemeat6237.near, 901,581 transactions contained swap calls and
702,584 contained ft_transfer_call calls: 55.65% and 43.37% respectively.

omni-relayer.bridge.near methods included sign_btc_transaction,
sign_transfer, claim_fee, fin_transfer, verify_deposit_v2 and
verify_withdraw_v2.

The results distinguish delegated submissions from direct calls.
Delegated inner actions were not expanded. Submitted methods do not
establish execution success or ownership. Category transaction counts
can overlap and must not be summed as unique transactions.

Query: `sql/20_leading_account_actions.sql`
Results: `results/20_leading_account_actions_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Growth Outside a Fixed Account Group

I held the first week's ten busiest signing accounts fixed across
all eight weeks.

Weekly rows reconciled to results 10 and 18. Group totals, remaining
transactions, active-account counts, shares and changes passed checks.

Between the endpoints:

- Network transactions increased from 4,734,816 to 4,909,532: +3.69%.
- Fixed-group transactions declined from 3,195,028 to 2,561,335: −19.83%.
- Transactions outside the group increased from 1,539,788 to 2,348,197:
  +52.50%.

The outside increase of 808,409 offset the fixed group's decline of
633,693. The fixed group's network share fell from 67.48% to 52.17%.
All ten selected accounts remained active each week.

Outside-group transactions peaked at 3,673,647 during
28 September–4 October. The final week was 36.08% below that peak.

Growth extended beyond the original leaders, but the outside group
includes intermediaries, other large accounts and lifecycle activity.
This is a descriptive comparison, not a counterfactual network
without the selected accounts.

Script: `analysis/03_fixed_account_growth.py`
Results: `results/21_fixed_account_growth_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Account Contributions to Transaction Growth

I decomposed the endpoint change using the 51 account histories in
result 18 and fixed-group comparison in result 21.

The 52 output rows contain 51 accounts and one untracked remainder.
Endpoint counts, changes, shares and contribution percentages reconciled.

Of the 808,409 increase outside the fixed group:

- The other 41 tracked accounts contributed 454,289: 56.20%.
- Untracked accounts contributed 354,120: 43.80%.

Untracked transactions increased from 1,163,267 to 1,517,387: +30.44%.
Untracked means outside every weekly top-twenty signing-account ranking,
not verified users or independent applications.

The largest positive tracked contributions outside the fixed group were:

- tinykoala595.near: 148,950 transactions, or 18.43%.
- wx-cruce.near: 137,767 transactions, or 17.04%.

Both had zero first-week transactions. This does not establish creation
dates or first-ever use.

Contribution percentages use the outside-group net increase as their
denominator. Negative contributions or values above 100% are possible
because increases and decreases offset. The comparison is between
endpoints, not cumulative growth.

Script: `analysis/04_account_growth_contributions.py`
Results: `results/22_account_growth_contributions_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Activity of Two Growth-Contributing Accounts

I examined destinations, action types and methods for tinykoala595.near
and wx-cruce.near.

The export contained 101 rows across ten active account-weeks.
Totals reconciled to result 18. Missing weeks corresponded to zero
transactions. All transactions matched action records, with no missing
indices or FUNCTION_CALL method names.

Of 778,588 tinykoala595.near transactions, 778,338 contained swap calls
to v2.ref-finance.near: 99.97%.

Of 413,281 wx-cruce.near transactions:

- 200,667 contained ft_transfer_call to
  17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1:
  48.55%.
- 199,869 contained ft_transfer_call to wrap.near: 48.36%.

These observations associate growth with particular interactions.
They do not establish ownership, automation, economic volume or success.

Action-category transaction counts overlap. Payloads and downstream
execution were not expanded.

Query: `sql/23_growth_account_activity.sql`
Results: `results/23_growth_account_activity_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Initial Outcomes of Growth-Contributing Accounts

I matched the two selected accounts' transactions to initial receipt
outcomes, allowing outcomes through 19 October.

The export contained thirty rows across ten active account-weeks.
Counts reconciled to result 18. Transaction hashes and nonnull initial
receipt identifiers were distinct within each account-week.

Every transaction matched exactly one outcome, with the executor
matching the original receiver.

| Account | FAILURE | SUCCESS_VALUE | SUCCESS_RECEIPT_ID |
|---|---:|---:|---:|
| tinykoala595.near | 715,518 (91.90%) | 62,955 (8.09%) | 115 (0.01%) |
| wx-cruce.near | 6,441 (1.56%) | 7,872 (1.90%) | 398,968 (96.54%) |

Most tinykoala595.near initial receipts failed. Most wx-cruce.near
initial receipts returned SUCCESS_RECEIPT_ID, which does not establish
downstream success.

Outcomes were grouped by account and week rather than cross-tabulated
against every submitted method. The analysis did not establish failure
causes, retries, completed swaps or economic volume.

Query: `sql/24_growth_account_outcomes.sql`
Results: `results/24_growth_account_outcomes_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Sampled Failure Logs

I selected three failed initial receipts per active week for
tinykoala595.near using deterministic transaction-hash ordering.

The sample contained eighteen distinct receipts across six weeks.
Each had exactly one FAILURE outcome, with the executor matching
the original receiver.

All exported log arrays were empty, providing no diagnostic messages
through this source. Further inspection required execution details
from another source.

The sample was diagnostic, not designed to estimate error frequencies.

Query: `sql/25_inspect_growth_account_failures.sql`
Results: `results/25_growth_account_failure_sample_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Detailed Errors for Sampled Failures

I retrieved execution details for all eighteen receipts and checked
transaction hashes, signing accounts, receipt identifiers, executors
and failure statuses against result 25.

Seventeen reported E68: slippage error. One reported E22: not enough
tokens in deposit. All executed on v2.ref-finance.near.

These are reported contract errors within the sample, not estimates
of causes across all 715,518 failures or proof of retries or automation.

The original archival endpoint returned five validated responses before
HTTP 429 responses and a deprecation message. The remaining thirteen
lookups succeeded through FastNear's archival endpoint. Earlier failed
attempts remain preserved in the completed JSON.

Empty BigQuery log arrays did not imply that diagnostic information
was unavailable: RPC receipt statuses contained execution errors.

Script: `analysis/05_fetch_failure_details.py`
Results: `results/26_growth_account_failure_details_2026-08-24_to_2026-10-18.json`

## 26 October 2026 — Execution Costs of Selected Growth Accounts

All 1,191,869 selected transactions reconciled to result 24 and matched
exactly one initial receipt outcome. Executors matched the original
receivers, and costs were present, finite and nonnegative.

| Account | Initial-receipt costs | Failed-receipt costs | Failed cost share |
|---|---:|---:|---:|
| tinykoala595.near | 243.3451 NEAR | 211.1629 NEAR | 86.78% |
| wx-cruce.near | 115.0938 NEAR | 1.0978 NEAR | 0.95% |

Failures represented 91.90% and 1.56% respectively of the accounts'
transactions.

Costs cover initial receipts only, grouped by transaction submission
week. They exclude conversion costs and downstream receipts.
Amounts are approximate because source cost fields use floating-point
storage.

The selected accounts do not represent the network. Their costs are
not an additional component to add to network-wide receipt totals.

Query: `sql/27_growth_account_execution_costs.sql`
Results: `results/27_growth_account_execution_costs_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Daily Total Supply Checks

I examined block records for 57 dates from 23 August to 18 October.
The closing observation on 23 August provides the opening baseline.

All dates contained records. Daily counts matched distinct block
heights and hashes. No missing heights, hashes or timestamps,
timestamp-date mismatches, or invalid supply values were found.

Each day's highest recorded block had its latest timestamp.
Closing observations were within one second of the following UTC
midnight. These checks do not prove every produced block was indexed.

Closing total supply increased from approximately 1,304,386,568.87 NEAR
to 1,309,322,552.85 NEAR.

The net increase was approximately 4,935,983.98 NEAR, or 0.3784%.
All 56 daily changes were positive and reconciled to the endpoints.

This measures observed net total-supply movement, not separate gross
issuance, permanent burning or circulating supply. Staking and storage
commitments are not automatically changes in total supply.

Amounts are approximate and use the last recorded blocks of each date.

Query: `sql/28_daily_supply_checks.sql`
Results: `results/28_daily_supply_checks_2026-08-23_to_2026-10-18.csv`

## 27 October 2026 — Validator Balance Changes and Supply Reconciliation

I investigated account-change records as a possible explanation for
observed supply movement.

On 24 August, four update reasons appeared: receipt_processing,
action_receipt_gas_reward, transaction_processing and
validator_accounts_update.

Validator updates comprised 1,860 records affecting 465 accounts at
four block heights. All matched usable previous records. Combined
staked and nonstaked balances increased approximately 108,245.80 NEAR.

Forty comparisons showed decreases totalling approximately
0.000000000580 NEAR. Their scale was consistent with floating-point
precision effects rather than evidence of meaningful slashing or burning.

Across 24 August–18 October, all 83,864 validator updates matched
usable previous records, using 23 August as additional history.

The raw validator-update net balance increase was approximately
4,919,384.47 NEAR. No individual decrease exceeded 0.000001 NEAR.
Raw changes and within-tolerance amounts were retained separately.

The tolerance is an analytical choice, not a protocol rule or guarantee
of source accuracy.

Separately, 7,930,886 block records matched their recorded predecessor
hashes. Positive supply movements totalled approximately 4,990,242.56 NEAR
and decreases 54,258.58 NEAR, reconciling to the net increase in result 28.

Positive movements exceeded the validator-update increase by
70,858.09 NEAR. The net supply increase exceeded it by 16,599.51 NEAR.
These differences remained unresolved.

The measurements were not classified as complete gross issuance or
permanent burning. Effects can offset within a block, and matching
available records does not prove complete economic-flow coverage.

The inspected chunks schema contained gas usage but no explicit
issuance or token-burning amount. Further decomposition was paused
with the gap retained in the research record.

All amounts derived from floating-point fields are approximate.

Queries:

- `sql/29_inspect_account_change_reasons.sql`
- `sql/30_inspect_validator_balance_changes.sql`
- `sql/31_inspect_negative_validator_changes.sql`
- `sql/32_daily_validator_balance_changes.sql`
- `sql/33_daily_block_supply_movements.sql`

Results:

- `results/29_account_change_reasons_2026-08-24.csv`
- `results/30_validator_balance_changes_2026-08-24.csv`
- `results/31_negative_validator_changes_2026-08-24.csv`
- `results/32_daily_validator_balance_changes_2026-08-24_to_2026-10-18.csv`
- `results/33_daily_block_supply_movements_2026-08-24_to_2026-10-18.csv`

## 27 October 2026 — Weekly Economic Comparison

I combined saved activity and receipt-cost results with daily supply
movements and validator-update balance changes. No new scan was required.

All eight weeks reconciled to results 14, 28, 32 and 33.
Weekly supply changes used the preceding Sunday's closing supply
and reconciled to the full-period endpoint difference.

Between the first and final weeks:

- Transactions increased 3.69%.
- Receipt outcomes increased 66.85%.
- Recorded receipt costs increased 82.73%.
- Average recorded cost per receipt increased 9.52%.

Receipt volume and average costs both increased. This describes
arithmetic relationships, not their causes or matched transaction-chain
costs.

Observed supply increased 4,935,983.98 NEAR. Validator-update balances
increased 4,919,384.47 NEAR, leaving an unresolved 16,599.51 NEAR gap.

Costs, supply movements and validator balances remain separate measures.
They do not establish complete issuance, burning, revenue or holder
returns.

Decimal arithmetic preserves exported precision during aggregation;
it does not restore precision absent from floating-point source fields.

Script: `analysis/06_weekly_economic_comparison.py`
Results: `results/34_weekly_economic_comparison_2026-08-24_to_2026-10-18.csv`

## 27 October 2026 — Account Profiles

I combined saved signing-account, destination and action results into
five profiles covering eight weeks each.

All forty account-weeks matched baseline transaction totals.
Top-twenty receiver rows reconciled to their reported totals, and those
totals plus the outside-group remainder matched weekly transactions.

Transactions with and without action records reconciled to weekly
totals. Each account's eight weeks matched its full-period total.

Attribution is separate from activity. NEAR Intents has a documented
contract role, and the Omni Bridge account has a documented relayer role.
The other three service associations remain unverified.

Profiles describe transactions signed by selected accounts, not complete
application activity or user counts. Action-category transaction counts
can overlap.

The subsequent profile clarification describes observed delegated
transactions and function calls for sweat-relayer.near without assigning
a verified service affiliation.

Script: `analysis/07_account_profiles.py`
Results: `results/35_account_profiles_2026-08-24_to_2026-10-18.json`
Attribution: `notes/account_attribution.md`

## 28 October 2026 — Transaction Receipt-Conversion Costs

The export covered eight complete weeks and reconciled to 44,284,794
transactions. Weekly transaction counts matched distinct hashes.

Missing, negative and nonfinite cost counts were zero.
Reported averages reconciled to weekly costs divided by transactions.

Recorded conversion costs totalled approximately 2,110.82 NEAR.
Weekly costs increased from 213.34 NEAR to 413.28 NEAR: +93.72%
between the endpoints.

This measured transaction receipt conversion separately from receipt
execution. It did not establish the causes of the change, protocol
revenue or permanent burning.

Query: `sql/34_weekly_transaction_conversion_costs.sql`
Results: `results/36_weekly_transaction_conversion_costs_2026-08-24_to_2026-10-18.csv`

## 28 October 2026 — Combined Recorded Execution Spending

I combined transaction conversion and receipt execution costs across
eight complete weeks.

Dates and transaction totals matched the existing economic comparison.
Conversion coverage checks passed, and per-transaction and per-receipt
averages reconciled.

| Component | Recorded spending |
|---|---:|
| Transaction conversion | 2,110.8191 NEAR |
| Receipt execution | 65,878.0861 NEAR |
| Combined | 67,988.9052 NEAR |

Conversion contributed 3.1047% of combined spending.
Combined weekly spending increased 83.13% between the endpoints.

Conversion uses transaction submission dates; receipt costs use
execution dates. This is a calendar-period comparison, not a matched
calculation of complete transaction-chain fees.

The amounts measure recorded execution expenditure in NEAR.
They do not independently establish permanent burning, protocol revenue,
persistent token holdings, external purchases or holder returns.

Script: `analysis/08_execution_spending.py`
Results: `results/37_weekly_execution_spending_2026-08-24_to_2026-10-18.csv`

## 28 October 2026 — Extended Weekly Signing Activity

Extended the transaction-based comparison to 6 July–18 October 2026, covering fifteen complete UTC weeks.

Query: `sql/35_extended_weekly_signing_activity.sql`

Export: `results/38_extended_weekly_signing_activity_2026-07-06_to_2026-10-18.csv`

Checks:
- The export contains fifteen consecutive Monday–Sunday weeks.
- Weekly transaction totals and signing-account-days reconcile to the existing daily transaction checks across 105 dates.
- The eight overlapping weeks reconcile to result 10, except for the expected change in the first overlapping week's previous-week comparison.
- For 24 August, the extended query reports a −1.09% change in active signing accounts. The original query left this blank because its observation window started that week.
- Reported averages, concentration shares and weekly account changes reconcile to their underlying counts.

The extended period contained 79,171,891 transactions. Between the first and final weeks, transactions declined 10.63% and weekly active signing accounts declined 24.65%. The top-ten signing accounts' transaction share fell from 66.19% to 57.97%, a decrease of 8.22 percentage points.

The longer window shows that endpoint growth depends on the selected baseline. Lower signing-account concentration does not independently establish broader user demand.

This extension covers transaction activity only. It does not extend receipt execution costs or resolve the earlier receipt-matching differences. Signing accounts remain identifiers rather than verified individuals.