# Data Checks

## 25 October 2026 — Historical Partition Coverage

I checked daily partition metadata for transactions, receipt_actions, execution_outcomes and accounts before selecting the observation period.

The transactions, receipt_actions and execution_outcomes tables each returned 2,275 nonempty daily partitions, spanning 23 July 2020 to 25 October 2026.

All three tables had nonempty partitions for all 116 days in the candidate window of 1 July–24 October 2026. This establishes daily partition availability, not completeness of the underlying records.

The accounts table did not appear in the filtered results. I have not established the reason and will not interpret its absence as evidence that it contains no data.

The observation period remains provisional pending data-quality checks and query-cost estimates.

Query: `sql/01_check_partition_coverage.sql`
Results: `results/01_partition_coverage_2026-10-25.csv`