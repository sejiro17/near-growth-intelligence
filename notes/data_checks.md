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