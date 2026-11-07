/* @datacloud.settings
{
  "version": 1,
  "service": "BIG_QUERY",
  "connectionInfo": {"billingProjectId": "INHERIT"},
  "dialect": "GOOGLE_SQL"
}
*/

/*
Transactions-only persistence pilot: four activity cohorts; exact +1/+4/+8.
Verified columns/table: SQL 03, 11, 34 and 35. One direct partitioned source
read. Signer/week aggregation precedes cohort joins; no actions/receipts join.
Overlapping cohorts are separate views and must not be summed as disjoint sets.

Last complete saved week ends 18 October. Incomplete follow-up metrics are NULL,
not zero. Repeated checkpoint return requires all exact +1/+4/+8 weeks; any-return
unions use every intervening week and remain separately named. No creation or
human-user attribution is established. Source diagnostics describe observed
coverage only. Global uniqueness/identity/coverage failures suppress metrics.

Conversion costs use submission weeks. Finite nonnegative source FLOAT amounts
are SAFE_CAST to BIGNUMERIC before summation; this cannot recover source precision.
Invalid costs suppress a complete spending total. No receipt execution spending,
complete-chain success, deletion adjustment, revenue or holder return is measured.

The export is 23 compact records: SUMMARY, 10 WEEK_CONTROL, 12 CHECKPOINT.
record_json avoids ambiguous flattening of independent nested arrays. Concentration
is represented by exact count numerators, not rounded shares or a membership list.
*/

WITH source_transactions AS (
    SELECT block_date, transaction_hash, signer_account_id, receiver_account_id,
        block_timestamp_utc,
        IF(receipt_conversion_tokens_burnt IS NOT NULL
            AND NOT IS_NAN(receipt_conversion_tokens_burnt)
            AND NOT IS_INF(receipt_conversion_tokens_burnt)
            AND receipt_conversion_tokens_burnt >= 0,
            SAFE_CAST(receipt_conversion_tokens_burnt AS BIGNUMERIC), NULL) AS cost_yocto
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-10' AND DATE '2026-10-18'
),
source_counts AS (
    SELECT COUNT(*) AS transaction_rows,
        COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT block_date) AS observed_days,
        COUNT(DISTINCT TIMESTAMP_TRUNC(block_timestamp_utc, HOUR)) AS observed_hours,
        COUNTIF(NULLIF(TRIM(transaction_hash), '') IS NULL) AS missing_transaction_hashes,
        COUNTIF(NULLIF(TRIM(signer_account_id), '') IS NULL) AS missing_signer_accounts,
        COUNTIF(NULLIF(TRIM(receiver_account_id), '') IS NULL) AS missing_receiver_accounts,
        COUNTIF(block_timestamp_utc IS NULL OR DATE(block_timestamp_utc) != block_date)
            AS invalid_timestamps,
        COUNTIF(cost_yocto IS NULL) AS invalid_conversion_cost_rows
    FROM source_transactions
),
source_controls AS (
    SELECT *, transaction_rows = distinct_transaction_hashes
        AND observed_days = 70 AND observed_hours = 1680
        AND missing_transaction_hashes = 0 AND missing_signer_accounts = 0
        AND missing_receiver_accounts = 0 AND invalid_timestamps = 0 AS source_valid
    FROM source_counts
),
account_weeks AS (
    SELECT DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start, signer_account_id,
        COUNT(*) AS transactions, COUNTIF(cost_yocto IS NULL) AS invalid_costs,
        SUM(cost_yocto) AS valid_cost_yocto
    FROM source_transactions
    GROUP BY week_start, signer_account_id
),
week_counts AS (
    SELECT DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        COUNT(*) AS transactions, COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT signer_account_id) AS active_accounts,
        COUNT(DISTINCT block_date) AS observed_days,
        COUNT(DISTINCT TIMESTAMP_TRUNC(block_timestamp_utc, HOUR)) AS observed_hours,
        COUNTIF(cost_yocto IS NULL) AS invalid_costs, SUM(cost_yocto) AS valid_cost_yocto
    FROM source_transactions
    GROUP BY week_start
),
cohorts AS (
    SELECT cohort_week FROM UNNEST([
        DATE '2026-08-10', DATE '2026-08-17', DATE '2026-08-24', DATE '2026-09-28'
    ]) AS cohort_week
),
members AS (
    SELECT c.cohort_week, a.signer_account_id
    FROM cohorts AS c
    INNER JOIN account_weeks AS a ON a.week_start = c.cohort_week
),
member_history AS (
    SELECT m.cohort_week, m.signer_account_id,
        MAX(IF(DATE_DIFF(a.week_start, m.cohort_week, WEEK(MONDAY)) = 1, 1, 0)) AS at_1,
        MAX(IF(DATE_DIFF(a.week_start, m.cohort_week, WEEK(MONDAY)) = 4, 1, 0)) AS at_4,
        MAX(IF(DATE_DIFF(a.week_start, m.cohort_week, WEEK(MONDAY)) = 8, 1, 0)) AS at_8,
        MAX(IF(DATE_DIFF(a.week_start, m.cohort_week, WEEK(MONDAY)) BETWEEN 1 AND 4, 1, 0)) AS any_1_4,
        MAX(IF(DATE_DIFF(a.week_start, m.cohort_week, WEEK(MONDAY)) BETWEEN 1 AND 8, 1, 0)) AS any_1_8
    FROM members AS m
    INNER JOIN account_weeks AS a ON a.signer_account_id = m.signer_account_id
        AND a.week_start BETWEEN m.cohort_week AND DATE_ADD(m.cohort_week, INTERVAL 8 WEEK)
    GROUP BY m.cohort_week, m.signer_account_id
),
cohort_counts AS (
    SELECT cohort_week, COUNT(*) AS cohort_accounts,
        COUNTIF(at_1 = 1 AND at_4 = 1) AS at_1_and_4,
        COUNTIF(at_1 = 1 AND at_4 = 1 AND at_8 = 1) AS at_1_and_4_and_8,
        COUNTIF(any_1_4 = 1) AS any_1_4,
        COUNTIF(any_1_8 = 1) AS any_1_8
    FROM member_history
    GROUP BY cohort_week
),
points AS (
    SELECT cohort_week, week_offset,
        DATE_ADD(cohort_week, INTERVAL week_offset WEEK) AS followup_week,
        DATE_ADD(DATE_ADD(cohort_week, INTERVAL week_offset WEEK), INTERVAL 6 DAY) AS followup_week_end,
        DATE_ADD(DATE_ADD(cohort_week, INTERVAL week_offset WEEK), INTERVAL 6 DAY) <= DATE '2026-10-18'
            AS followup_complete
    FROM cohorts CROSS JOIN UNNEST([1, 4, 8]) AS week_offset
),
returner_accounts AS (
    SELECT p.cohort_week, p.week_offset, a.signer_account_id,
        a.transactions, a.invalid_costs, a.valid_cost_yocto,
        ROW_NUMBER() OVER (PARTITION BY p.cohort_week, p.week_offset
            ORDER BY a.transactions DESC, a.signer_account_id) AS activity_rank
    FROM points AS p
    INNER JOIN members AS m ON m.cohort_week = p.cohort_week
    INNER JOIN account_weeks AS a ON a.signer_account_id = m.signer_account_id
        AND a.week_start = p.followup_week
    WHERE p.followup_complete
),
returner_counts AS (
    SELECT cohort_week, week_offset, COUNT(*) AS returning_accounts,
        SUM(transactions) AS returning_transactions, SUM(invalid_costs) AS invalid_costs,
        SUM(valid_cost_yocto) AS valid_cost_yocto,
        SUM(IF(activity_rank = 1, transactions, 0)) AS top_1_transactions,
        SUM(IF(activity_rank <= 10, transactions, 0)) AS top_10_transactions,
        SUM(IF(activity_rank <= 20, transactions, 0)) AS top_20_transactions,
        SUM(CAST(transactions AS NUMERIC) * CAST(transactions AS NUMERIC)) AS squared_transactions
    FROM returner_accounts
    GROUP BY cohort_week, week_offset
),
checkpoint_records AS (
    SELECT TO_JSON_STRING(STRUCT(
        p.cohort_week, DATE_ADD(p.cohort_week, INTERVAL 6 DAY) AS cohort_week_end,
        p.week_offset, p.followup_week, p.followup_week_end, p.followup_complete,
        g.source_valid AS source_controls_passed,
        g.source_valid AND p.followup_complete AS measurement_available,
        IF(g.source_valid, COALESCE(cc.cohort_accounts, 0), NULL) AS cohort_accounts,
        IF(g.source_valid AND p.followup_complete, COALESCE(w.transactions, 0), NULL)
            AS observed_week_transactions,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.returning_accounts, 0), NULL)
            AS returning_accounts,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.returning_transactions, 0), NULL)
            AS returning_transactions,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.top_1_transactions, 0), NULL)
            AS top_1_transactions,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.top_10_transactions, 0), NULL)
            AS top_10_transactions,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.top_20_transactions, 0), NULL)
            AS top_20_transactions,
        IF(g.source_valid AND p.followup_complete, CAST(COALESCE(r.squared_transactions, 0) AS STRING), NULL)
            AS sum_squared_returner_transactions,
        IF(g.source_valid AND p.followup_complete, COALESCE(r.invalid_costs, 0), NULL)
            AS invalid_conversion_cost_rows,
        IF(g.source_valid AND p.followup_complete AND COALESCE(r.invalid_costs, 0) = 0,
            CAST(COALESCE(r.valid_cost_yocto, 0) / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
            AS recorded_conversion_spending_near,
        IF(g.source_valid AND DATE_ADD(p.cohort_week, INTERVAL 34 DAY) <= DATE '2026-10-18',
            COALESCE(cc.at_1_and_4, 0), NULL) AS return_at_1_and_4_accounts,
        IF(g.source_valid AND DATE_ADD(p.cohort_week, INTERVAL 62 DAY) <= DATE '2026-10-18',
            COALESCE(cc.at_1_and_4_and_8, 0), NULL) AS repeated_checkpoint_returners_accounts,
        IF(g.source_valid AND DATE_ADD(p.cohort_week, INTERVAL 34 DAY) <= DATE '2026-10-18',
            COALESCE(cc.any_1_4, 0), NULL) AS any_return_weeks_1_to_4_accounts,
        IF(g.source_valid AND DATE_ADD(p.cohort_week, INTERVAL 62 DAY) <= DATE '2026-10-18',
            COALESCE(cc.any_1_8, 0), NULL) AS any_return_weeks_1_to_8_accounts,
        'SUBMISSION_WEEK_OUTER_SIGNER_INITIAL_RECEIPT_ECONOMICS_NOT_EXTRACTED' AS attribution_scope
    )) AS record_json
    FROM points AS p
    CROSS JOIN source_controls AS g
    LEFT JOIN cohort_counts AS cc ON cc.cohort_week = p.cohort_week
    LEFT JOIN returner_counts AS r ON r.cohort_week = p.cohort_week AND r.week_offset = p.week_offset
    LEFT JOIN week_counts AS w ON w.week_start = p.followup_week
)
SELECT 'SUMMARY' AS row_kind, TO_JSON_STRING(STRUCT(
    DATE '2026-08-10' AS source_start, DATE '2026-10-18' AS source_end,
    g.transaction_rows, g.distinct_transaction_hashes, g.observed_days, g.observed_hours,
    g.missing_transaction_hashes, g.missing_signer_accounts, g.missing_receiver_accounts,
    g.invalid_timestamps, g.invalid_conversion_cost_rows, g.source_valid AS source_controls_passed,
    4 AS cohort_count, 10 AS week_control_rows, 12 AS checkpoint_rows,
    'OBSERVED_RECORDS_ONLY_NOT_INDEPENDENT_COMPLETENESS' AS coverage_basis
)) AS record_json
FROM source_controls AS g

UNION ALL

SELECT 'WEEK_CONTROL', TO_JSON_STRING(STRUCT(
    week_start, DATE_ADD(week_start, INTERVAL 6 DAY) AS week_end,
    transactions, distinct_transaction_hashes, active_accounts, observed_days, observed_hours,
    invalid_costs AS invalid_conversion_cost_rows,
    IF(invalid_costs = 0, CAST(valid_cost_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
        AS recorded_conversion_spending_near
))
FROM week_counts

UNION ALL

SELECT 'CHECKPOINT', record_json FROM checkpoint_records
ORDER BY row_kind DESC, record_json;
