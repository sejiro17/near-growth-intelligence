# Data Checks

## 25 October 2026 — Historical Partition Coverage

I checked daily partition metadata for transactions, receipt_actions, execution_outcomes and accounts before selecting the observation period.

The transactions, receipt_actions and execution_outcomes tables each returned 2,275 nonempty daily partitions, spanning 23 July 2020 to 25 October 2026.

All three tables had nonempty partitions for all 116 days in the candidate window of 1 July–24 October 2026. This establishes daily partition availability, not completeness of the underlying records.

The accounts table did not appear in the filtered results. I have not established the reason and will not interpret its absence as evidence that it contains no data.

The observation period remains provisional pending data-quality checks and query-cost estimates.

Query: `sql/01_check_partition_coverage.sql`
Results: `results/01_partition_coverage_2026-10-25.csv`

## 25 October 2026 — Daily Partition Counts

I inspected daily partition row counts for transactions, receipt_actions and execution_outcomes from 1 July to 24 October 2026.

The results contain all 116 expected dates, with no missing or zero counts across the three tables.

The counts show several abrupt changes, including a transaction increase on 27 September and elevated receipt-action and execution-outcome counts on 10–11 October. On 15 October, receipt-action rows substantially exceeded execution-outcome rows.

These tables represent different units, so their row counts are not expected to match directly. I have not established whether the changes reflect underlying activity, ingestion issues or other causes.

This check establishes nonempty daily coverage. It does not establish record uniqueness or completeness.

Query: `sql/02_daily_partition_counts.sql`
Results: `results/02_daily_partition_counts_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Daily Transaction Validation

I checked transaction records from 1 July to 24 October 2026 across all 116 expected dates.

The results contain 86,547,133 transaction rows. Each day's row count matched its distinct transaction-hash count, with no duplicate hashes within a day. Daily counts also matched the previously exported partition metadata.

I found no missing transaction hashes, signing accounts, receiving accounts or timestamps. All timestamps matched their block dates, and every day contained activity in all 24 UTC hours.

Daily active signing accounts ranged from 42,517 to 177,196. These are account identifiers, not verified individuals.

These checks support further analysis but do not establish complete ingestion or transaction-hash uniqueness across different days. The counts include all recorded transaction statuses.

Query: `sql/03_daily_transaction_checks.sql`
Results: `results/03_daily_transaction_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Transaction Status and Hash Uniqueness

I inspected transaction statuses and checked transaction-hash uniqueness across the full candidate window of 1 July–24 October 2026.

All 86,547,133 transaction rows had status SUCCESS_RECEIPT_ID, with no missing statuses. Daily status totals matched the transaction counts from query 03.

The full-window distinct transaction-hash count also equalled 86,547,133, establishing that hashes were unique across the selected records.

I will not interpret SUCCESS_RECEIPT_ID as proof of successful downstream execution. Execution outcomes require separate analysis.

Query: `sql/04_transaction_status_checks.sql`
Results: `results/04_transaction_status_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Execution-Outcome Validation

I inspected execution-outcome records from 1 July to 24 October 2026.

The results contain 486,375,712 outcome rows across 116 days: 437,621,841 with status SUCCESS_VALUE, 36,472,564 with SUCCESS_RECEIPT_ID and 12,281,307 with FAILURE. Daily totals matched the partition counts from query 02.

I found no missing receipt identifiers, executor accounts or timestamps, and no timestamp-date mismatches. Gas and token-cost fields contained no missing, negative or nonfinite values.

Within each date-and-status group, row counts matched distinct receipt-identifier counts. This does not establish identifier uniqueness across groups.

Before calculating receipt-level failure rates or network execution costs, I will verify the execution units represented and check for duplication across groups.

Query: `sql/05_daily_execution_outcome_checks.sql`
Results: `results/05_daily_execution_outcome_checks_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Execution Units on 15 October

I matched execution-outcome identifiers dated 15 October against transaction hashes and receipt identifiers recorded from 14–16 October.

All 14,335,195 outcome rows matched exactly one ACTION receipt. None matched a transaction hash, a DATA receipt or both identifier types, and none remained unmatched within the lookup window.

The status counts reconciled exactly to query 05: 132,614 FAILURE, 340,772 SUCCESS_RECEIPT_ID and 13,861,809 SUCCESS_VALUE.

Within each resulting group, outcome counts matched distinct identifier counts. No outcome matched multiple lookup rows.

This establishes the execution units for the inspected day only. It also shows that SUCCESS_RECEIPT_ID is present among ACTION receipt outcomes and cannot by itself identify transaction-processing records.

Query: `sql/06_inspect_execution_units.sql`
Results: `results/06_execution_units_2026-10-15.csv`

## 25 October 2026 — Full-Window Outcome Matching

I checked execution-outcome identifier uniqueness across 1 July–24 October 2026 and matched identifiers against receipt_details records dated 30 June–25 October.

All 486,375,712 outcome identifiers were unique across the selected window, with no identifiers repeated across dates or statuses.

Of these, 482,361,311 matched exactly one ACTION receipt. The remaining 4,014,401 outcomes (0.83%) had no receipt match within the lookup window. The total reconciled to query 05.

I have not established why these identifiers were unmatched. I will retain them for investigation before calculating receipt-level rates or interpreting aggregate execution costs.

Query: `sql/07_full_window_outcome_matching.sql`
Results: `results/07_full_window_outcome_matching_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Unmatched Outcome Investigation

I examined the 4,014,401 outcomes that did not match receipt_details within the lookup window.

All unmatched outcomes were dated 1 July–22 August 2026. None occurred from 23 August to 24 October.

The unmatched records comprised 3,841,814 SUCCESS_VALUE, 144,068 SUCCESS_RECEIPT_ID and 28,519 FAILURE outcomes. Their total reconciled to query 07.

None of their identifiers matched transaction hashes recorded from 30 June to 25 October. The results therefore do not support classifying them as transaction-processing outcomes on that basis.

The cause remains unresolved. I will account for this matching limitation when choosing the observation period and defining receipt-based metrics.

Query: `sql/08_inspect_unmatched_outcomes.sql`
Results: `results/08_unmatched_outcomes_2026-07-01_to_2026-10-24.csv`

## 25 October 2026 — Weekly Activity Baseline

I summarised the validated daily transaction results into eight complete Monday–Sunday weeks from 24 August to 18 October 2026.

The weekly totals reconcile to 44,284,794 transactions across 56 dates. All weekly averages and week-to-week percentage changes reconciled to the daily source.

Weekly transactions peaked at 6,590,352 during 28 September–4 October. In the final week, transactions declined 23.31% and average daily active signing accounts declined 39.50% from the preceding week.

Compared with the first week, the final week recorded 3.69% more transactions but 29.87% fewer average daily active signing accounts. I have not established the causes of these differences.

Signing-account-days count an identifier once per active day. They are not weekly distinct accounts, and account identifiers are not verified individuals.

Script: `analysis/01_weekly_activity_baseline.py`
Results: `results/09_weekly_activity_baseline_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Signing Activity and Concentration

I counted distinct transaction-signing accounts within each of the eight complete weeks from 24 August to 18 October.

Weekly transaction totals and signing-account-days reconciled to the previous baseline, covering 44,284,794 transactions. All reported averages, concentration shares and weekly account changes reconciled to the exported counts.

Weekly active signing accounts peaked at 457,768 during 28 September–4 October, an increase of 198.16% from the preceding week. Of these accounts, 376,771 (82.31%) were active on only one day within that week.

Weekly active signing accounts fell to 129,446 in the final week, down 66.33% from the preceding week and 7.38% below the first week.

The ten busiest signing accounts contributed between 48.17% and 67.76% of weekly transactions. Rankings were calculated separately for each week; these are not necessarily the same accounts throughout.

These results describe signing-account identifiers, not verified individuals. Activity within a week does not establish return activity across weeks, and the causes of the observed changes remain unverified.

Query: `sql/10_weekly_signing_activity.sql`
Results: `results/10_weekly_signing_activity_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Account Returns

I measured subsequent weekly activity among signing accounts active in each of the eight starting weeks.

All cohort sizes reconciled to the weekly signing-activity results. The export contained 30 eligible cohort-follow-up combinations, with correct percentages and no incomplete follow-up weeks. Every starting-week count matched its cohort size.

Next-week active shares ranged from 18.14% to 77.96% across the seven cohorts with an observed following week.

Of the 457,768 signing accounts active during 28 September–4 October, 83,037 (18.14%) were active the following week and 77,133 (16.85%) were active two weeks later.

Four-week active shares ranged from 47.70% to 51.65% across the four cohorts with complete four-week follow-up.

Each cohort includes all signing accounts active in its starting week, not necessarily newly acquired users. Accounts may belong to multiple cohorts. Each follow-up measures activity during that particular week; it does not require continuous participation or measure cumulative returns.

Account identifiers are not verified individuals, and the causes of the observed differences remain unverified.

Query: `sql/11_weekly_account_returns.sql`
Results: `results/11_weekly_account_returns_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Receiver Activity

I ranked transaction receivers by transaction count within each of the eight complete weeks from 24 August to 18 October.

The export contained 20 receivers per week, giving 160 rows. Weekly transaction totals reconciled to the previous baseline. Receiver rankings, transaction shares and top-10 and top-20 concentration totals reconciled to the exported counts.

The ten busiest receivers accounted for 60.85%–70.22% of weekly transactions. The twenty busiest accounted for 70.48%–80.81%.

game.hot.tg ranked first in the first two weeks. v2.ref-finance.near ranked first in the remaining six weeks.

These are original transaction destinations, not necessarily downstream execution destinations or verified applications. Signing-account counts can overlap across receivers and must not be summed as weekly unique accounts.

The export contains only each week's twenty busiest receivers. A receiver's absence from another week's ranking does not establish zero activity.

Query: `sql/12_weekly_receiver_activity.sql`
Results: `results/12_weekly_receiver_activity_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Weekly Receipt Execution Costs

I aggregated execution outcomes by execution date across the eight complete weeks from 24 August to 18 October.

Weekly outcome counts and status breakdowns reconciled to the validated daily results, totalling 280,743,473 receipt execution outcomes. Every week contained seven observed dates, with zero unexpected statuses or invalid gas and token-cost values.

Recorded execution costs totalled approximately 65,878.09 NEAR, including 4,218.49 NEAR associated with failed receipts. Reported failure shares, cost shares and average costs reconciled to the exported figures.

Weekly recorded execution costs peaked at approximately 11,950.25 NEAR during 5–11 October. The final week recorded approximately 10,544.79 NEAR, compared with 5,770.56 NEAR in the first week.

These figures describe receipt executions occurring during each week. They do not trace the complete execution chain of transactions submitted that week or include transaction receipt-conversion costs. They do not establish protocol revenue, permanent token burning or value accruing to token holders.

Amounts are approximate because the source cost fields use floating-point storage.

Query: `sql/13_weekly_execution_costs.sql`
Results: `results/13_weekly_execution_costs_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Combined Weekly Growth and Costs

I combined the weekly activity, signing-account and receipt execution-cost exports into one table covering eight complete weeks.

All source values were preserved. Week boundaries, overlapping transaction totals and signing-account-days reconciled across the inputs. Growth indices and weekly cost changes calculated correctly.

With the first week indexed to 100, the final week recorded 103.69 for transactions, 92.62 for weekly active signing accounts and 182.73 for recorded receipt execution costs.

Activity and recorded execution costs therefore changed at different rates during the observation period. These comparisons do not establish the causes of the differences or demonstrate economic value accruing to token holders.

Transactions are grouped by submission date, while receipt costs are grouped by execution date. The indices compare weekly trends rather than matching transaction submissions to their complete execution costs.

Script: `analysis/02_weekly_execution_costs.py`
Results: `results/14_weekly_growth_and_costs_2026-08-24_to_2026-10-18.csv`

## 25 October 2026 — Receiver Activity by Subsequent Account Participation

I divided signing accounts active during 28 September–4 October into two groups according to whether they were active during 5–11 October. I then ranked each group's transaction receivers during the starting week.

The groups reconciled to 457,768 signing accounts and 6,590,352 starting-week transactions. Receiver rankings, transaction shares and account-interaction percentages reconciled to the exported counts.

The 83,037 accounts active the following week represented 18.14% of the cohort and generated 5,788,805 starting-week transactions (87.84%). The remaining 374,731 accounts generated 801,547 transactions (12.16%).

Among accounts active the following week, v2.ref-finance.near received the most starting-week transactions: 1,139,455. Among accounts absent the following week, wallet.kaiching ranked first with 134,826 transactions from two signing accounts. This receiver therefore does not explain the group's large account count.

The export contains only the twenty busiest receivers per group, and account-interaction counts can overlap across receivers. These associations do not establish what caused the spike or identify genuine users, automated activity or campaigns.

Absence in the following week does not establish permanent departure. Signing-account identifiers are not verified individuals.

Query: `sql/15_spike_cohort_receivers.sql`
Results: `results/15_spike_cohort_receivers_2026-09-28_to_2026-10-11.csv`

## 25 October 2026 — Spike Cohort Transaction Actions

I compared submitted transaction action types during 28 September–4 October between accounts active and absent during the following week.

Group account and transaction totals reconciled to the previous cohort results. Reported percentages calculated correctly. Matched records had zero missing action indices and zero duplicate indices within each transaction-action-kind group.

Among accounts absent the following week, 309,286 (82.54%) submitted transactions containing DELETE_ACCOUNT actions. These accounted for 309,601 transactions.

Among accounts active the following week, 80,191 (96.57%) submitted transactions containing FUNCTION_CALL actions. DELEGATE_ACTION appeared in 1,945,506 transactions from 28 signing accounts.

There were 474 transactions without matching action records in the selected lookup window: seven from returning accounts and 467 from accounts absent the following week. The reason remains unresolved.

These results describe submitted actions, not confirmed execution outcomes. DELETE_ACCOUNT actions do not by themselves establish successful deletion or that the deleted account was the signing account.

Transactions and signing accounts can appear under multiple action types. Their counts must not be summed across action kinds as distinct totals. Delegated payload contents were not expanded.

Query: `sql/16_spike_cohort_actions.sql`
Results: `results/16_spike_cohort_actions_2026-09-28_to_2026-10-11.csv`

## 25 October 2026 — Spike Account Deletion Outcomes

I checked the initial receipt execution outcomes for transactions containing DELETE_ACCOUNT actions during 28 September–4 October, allowing outcomes through 11 October.

All 309,642 deletion transactions reconciled to the previous action results. Each matched exactly one execution outcome. In every case, the transaction signer equalled the receiver, and the execution account matched that receiver.

Among accounts absent the following week, 309,587 deletion transactions from 309,280 distinct signing accounts had SUCCESS_VALUE outcomes. These accounts represented 82.53% of the absent group and 67.56% of the full starting-week cohort.

A further 14 deletion transactions from 11 accounts in the absent group failed. Account counts can overlap between successful and failed outcome groups.

Among accounts active the following week, 41 self-deletion transactions from nine accounts had SUCCESS_VALUE outcomes. Subsequent activity under those identifiers does not establish continuity of ownership; account recreation or other lifecycle activity has not been investigated.

The results establish successful receipt executions containing self-deletion actions. They do not establish why the accounts were deleted, who controlled them or whether the identifiers were later recreated.

The large absent-account count should not be interpreted as ordinary user churn without accounting for this deletion activity.

Query: `sql/17_spike_account_deletion_checks.sql`
Results: `results/17_spike_account_deletion_checks_2026-09-28_to_2026-10-11.csv`

## 26 October 2026 — Leading Signing Accounts

I identified each week's twenty busiest signing accounts during 24 August–18 October, then tracked the combined set across all eight weeks.

The export contains 408 account-week rows covering 51 distinct signing accounts. Weekly transaction totals, active signing-account counts and top-ten transaction counts reconcile with result 10. Account histories, rank flags and reported transaction shares passed the checks performed.

sweat-relayer.near ranked first every week and submitted 13,704,363 transactions, representing 30.95% of the period's total. Its weekly transactions declined from 1,954,610 to 1,301,312 between the first and final weeks, a decrease of 33.42%.

Five accounts appeared in the top ten every week: sweat-relayer.near, intents.near, closemeat6237.near, omni-relayer.bridge.near and meteor-relayer.near.

Transactions outside each week's top ten increased from 1,539,788 to 2,063,276, or 34.00%, between the first and final weeks. These groups change membership, so this comparison does not track a fixed set of accounts or establish independent user demand.

Account roles and ownership remain unverified. Weekly totals and full-period account summaries repeat across rows and must not be summed without deduplication.

Query: `sql/18_weekly_leading_signing_accounts.sql`
Results: `results/18_weekly_leading_signing_accounts_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Leading Account Destinations

I examined the original transaction receivers of the five signing accounts that ranked in the top ten during every week of the observation period.

The export contains 399 receiver rows across 40 account-week groups. Account transaction totals and active days reconcile with result 18. Receiver rankings, transaction shares and top-twenty coverage totals passed the checks performed. No missing or empty receiver identifiers were reported.

sweat-relayer.near submitted transactions to between 120,242 and 223,109 distinct original receivers per week. meteor-relayer.near submitted transactions to between 16,691 and 17,694.

Across the period, their weekly top-twenty receiver lists captured 69.98% and 2.98% of their respective transactions. These percentages aggregate transactions covered by each week's ranking; they do not describe a single fixed receiver list.

All 2,769,479 transactions signed by intents.near targeted intents.near. Most transactions signed by omni-relayer.bridge.near targeted omni.bridge.near, btc-connector.bridge.near and zcash-connector.bridge.near.

closemeat6237.near had five distinct receivers each week. v2.ref-finance.near ranked first throughout and received 914,376 of its 1,620,042 transactions.

These results show that signing-account concentration can coexist with many transaction destinations. They do not establish account ownership, distinct users, independent demand or successful execution. Original receivers also do not identify every participant or downstream destination in delegated execution.

Account-week summary fields repeat across receiver rows and must be deduplicated before aggregation.

Query: `sql/19_leading_account_activity.sql`
Results: `results/19_leading_account_activity_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Leading Account Actions

I examined submitted action types and function-call methods for the five accounts consistently ranked among the ten busiest signing accounts.

The export contains 178 rows across 40 account-week groups. Transaction totals reconcile with result 18. Every selected transaction matched an action record within the lookup window. No matched action rows had missing indices, and no FUNCTION_CALL rows had missing method names.

DELEGATE_ACTION appeared in 13,246,938 transactions signed by sweat-relayer.near, representing 96.66% of its transactions. For meteor-relayer.near, it appeared in 1,239,064 transactions, or 98.02%.

All 2,769,479 transactions signed by intents.near contained an execute_intents function call.

For closemeat6237.near, 901,581 transactions contained swap calls and 702,584 contained ft_transfer_call calls, representing 55.65% and 43.37% respectively.

Methods submitted by omni-relayer.bridge.near included sign_btc_transaction, sign_transfer, claim_fee, fin_transfer, verify_deposit_v2 and verify_withdraw_v2.

The results distinguish delegated submissions from direct function calls and other actions. They support examining intermediary activity before interpreting signing-account concentration as end-user concentration.

Delegated payload contents were not expanded. Submitted methods do not establish successful execution, operator identity or independent user demand. A transaction can contain multiple action or method categories, so category transaction counts must not be summed as unique transactions.

Query: `sql/20_leading_account_actions.sql`
Results: `results/20_leading_account_actions_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Growth Outside a Fixed Account Group

I held the ten busiest signing accounts from 24–30 August fixed and compared their transaction activity with all remaining signing accounts across eight weeks.

All eight weekly rows reconcile with results 10 and 18. Fixed-group totals, remaining transaction counts, active-account counts, shares and growth percentages passed independent checks.

Network transactions increased from 4,734,816 to 4,909,532 between the first and final weeks, or 3.69%.

Transactions signed by the fixed group declined from 3,195,028 to 2,561,335, or 19.83%. Transactions outside it increased from 1,539,788 to 2,348,197, or 52.50%.

The increase of 808,409 transactions outside the group offset its decline of 633,693. The fixed group's network transaction share fell from 67.48% to 52.17%. All ten selected accounts remained active each week.

Transactions outside the group peaked at 3,673,647 during 28 September–4 October. The final week was 36.08% below that peak.

Growth was not confined to the signing accounts that dominated the first week. However, the remaining activity includes other large accounts, intermediaries and account lifecycle events. It does not establish independent users, application diversity or sustained adoption.

Group membership was selected using first-week transaction rankings and held constant. This is a descriptive comparison, not a simulation of the network without those accounts.

Script: `analysis/03_fixed_account_growth.py`
Results: `results/21_fixed_account_growth_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Account Contributions to Transaction Growth

I decomposed the first-to-final-week transaction change using the 51 account histories in result 18 and the fixed-group comparison in result 21.

The 52 output rows contain 51 individual accounts and one aggregate remainder for all untracked accounts. Endpoint counts, changes, network shares and contribution percentages reconcile with the source exports.

Outside the fixed first-week top ten, transactions increased by 808,409. The other 41 tracked accounts contributed a net increase of 454,289, or 56.20%. Untracked accounts combined contributed 354,120, or 43.80%.

Transactions from the untracked remainder increased from 1,163,267 to 1,517,387, or 30.44%. Untracked means outside the union of accounts appearing in any weekly top-twenty signing-account ranking during the selected period. It does not mean verified users or independent applications.

The largest positive contributions among tracked accounts outside the fixed group came from tinykoala595.near and wx-cruce.near: 148,950 and 137,767 transactions respectively. These represented 18.43% and 17.04% of the outside-group net increase.

Both accounts had zero transactions in the first week. This does not establish when they were created or first used.

The results show growth beyond the original leading accounts, alongside contributions from other prominent accounts. They do not establish how growth was distributed within the untracked remainder, account ownership or the causes of the changes.

Contributions use the outside-group net increase as their denominator. Negative contributions and contributions above 100% are possible because increases and decreases offset each other. The comparison concerns the first and final weeks, not cumulative growth across the period.

Script: `analysis/04_account_growth_contributions.py`
Results: `results/22_account_growth_contributions_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Activity of Two Growth-Contributing Accounts

I examined transaction destinations, submitted action types and function-call methods for tinykoala595.near and wx-cruce.near, the two largest positive contributors among tracked accounts outside the fixed first-week top ten.

The export contains 101 rows across ten account-week groups with observed transactions. Weekly totals reconcile with result 18. Weeks absent from the export correspond to zero transactions in that result.

Every selected transaction matched an action record within the lookup window. No matched action rows had missing indices or missing FUNCTION_CALL method names.

Of 778,588 transactions signed by tinykoala595.near, 778,338 contained a swap call to v2.ref-finance.near, representing 99.97%.

Of 413,281 transactions signed by wx-cruce.near, 200,667 contained ft_transfer_call to 17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1, representing 48.55%. Another 199,869 contained ft_transfer_call to wrap.near, representing 48.36%.

These findings associate two substantial growth contributions with specific contract interactions. They do not establish operator identity, automated behaviour, independent users, economic volume or successful execution.

A transaction may contain several action or method categories. Category transaction counts overlap and must not be summed as unique transactions. The export does not expand function-call payloads or trace downstream execution.

Query: `sql/23_growth_account_activity.sql`
Results: `results/23_growth_account_activity_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Initial Outcomes of Growth-Contributing Accounts

I matched transactions signed by tinykoala595.near and wx-cruce.near to their initial receipt execution outcomes, allowing outcomes through 19 October.

The export contains 30 rows across ten active account-week groups. Transaction counts reconcile with result 18. Within each account-week, transaction hashes and nonnull initial receipt identifiers were distinct.

Every selected transaction matched exactly one initial receipt outcome. No missing or multiple outcome matches were reported, and every executor matched the original transaction receiver.

Of 778,588 transactions signed by tinykoala595.near, 715,518 had FAILURE outcomes (91.90%), 62,955 had SUCCESS_VALUE outcomes (8.09%), and 115 had SUCCESS_RECEIPT_ID outcomes (0.01%).

Of 413,281 transactions signed by wx-cruce.near, 6,441 had FAILURE outcomes (1.56%), 7,872 had SUCCESS_VALUE outcomes (1.90%), and 398,968 had SUCCESS_RECEIPT_ID outcomes (96.54%).

These results qualify the earlier growth contribution findings. Submitted transaction growth does not establish successful economic activity. Most initial receipts associated with tinykoala595.near failed.

Most initial receipts associated with wx-cruce.near returned SUCCESS_RECEIPT_ID. This does not establish the final outcome of downstream execution.

The analysis does not establish failure causes, retries, operator motives, completed swaps or economic volume. Outcomes were grouped by account and week, rather than directly cross-tabulated with submitted methods.

Query: `sql/24_growth_account_outcomes.sql`
Results: `results/24_growth_account_outcomes_2026-08-24_to_2026-10-18.csv`

## 26 October 2026 — Sampled Failure Logs

I selected three failed initial receipts per active week for tinykoala595.near, using a deterministic transaction-hash ordering.

The sample contains 18 distinct receipts across six weeks. Each receipt had one matched FAILURE outcome, and every executor matched the original receiver.

All 18 exported log arrays were empty. The sample therefore provides no diagnostic error messages and does not establish a common failure cause, retries or operator intent.

The sample is intended for diagnostic inspection, not for estimating the prevalence of particular error causes. Further investigation requires execution details from another source.

Query: `sql/25_inspect_growth_account_failures.sql`
Results: `results/25_growth_account_failure_sample_2026-08-24_to_2026-10-18.csv`