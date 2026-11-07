/* @datacloud.settings
{
  "version": 1,
  "service": "BIG_QUERY",
  "connectionInfo": {"billingProjectId": "INHERIT"},
  "dialect": "GOOGLE_SQL"
}
*/

/*
Bounded initial-receipt pilot: 17 August activity cohort, +8 submissions during
12–18 October. Compare exact-week returners with the subset active at all three
+1/+4/+8 checkpoints. These populations overlap and must never be added together.
Four transaction weeks reconstruct membership; outcomes/blocks cover 12–24 October
only. The six-day tail after Sunday is right-censored and a partial execution week.
The lookup cutoff gives unequal elapsed follow-up by submission date. Matched
execution-lag minima/maxima are reported in microseconds for each population.

Schema evidence: SQL 03/24/27/34/39 and retained BigQuery row JSON in results 47/50
establish the fields used here, including outcome block_hash/executed_in_block_hash.
Result 56 SHA256: 6dbc05ee3c0deea1c4bfd2c1ad955da2f236cb0b1b580b1fd5cbea97c0cd6c09
Expected controls below test observed values; they do not supply measured outputs.

Aggregate owner/outcome/block counts BEFORE joining. Unique-observation CTEs
exclude all multi-match keys; no arbitrary MAX, LIMIT or array-position selection
is used to choose a canonical outcome. Receipt ownership uniqueness is bounded
to the four extracted transaction weeks, not independently proven globally.
Classification happens once per transaction before deliberate population expansion.

Actual execution dates come from unique block-hash lookups. Source-record dates,
hashes and timestamps are retained in diagnostic examples and counted separately.
Missing/duplicate/out-of-window matches, bad status/executor/time or invalid cost
are unavailable evidence, not failures or zero spending. Valid-cost subtotals
carry their assessed transaction count; a complete total requires every row.

Costs originate as FLOAT. BIGNUMERIC summation cannot restore source precision.
The 0.00001 NEAR control tolerance is saved-arithmetic consistency only. Initial
receipt success is not complete-chain success; descendants are not costed here.
Spending is associated with outer signing accounts, not verified economic payers,
revenue, purchases, permanent burn or holder value. No actions/deletions are read.
Diagnostic examples are explicitly limited to three per bucket; their counts
describe the full bucket. The aggregate export has no row truncation limit.
Matched outcome observation counts in buckets are transaction-weighted diagnostics;
they are not unique receipts or spending. Account outcome groups may overlap.
*/

WITH transactions AS (
    SELECT t.block_date, t.transaction_hash, t.signer_account_id, t.receiver_account_id,
        t.block_timestamp_utc AS submission_time, t.converted_into_receipt_id,
        IF(t.receipt_conversion_tokens_burnt IS NOT NULL
            AND NOT IS_NAN(t.receipt_conversion_tokens_burnt)
            AND NOT IS_INF(t.receipt_conversion_tokens_burnt)
            AND t.receipt_conversion_tokens_burnt >= 0,
            SAFE_CAST(t.receipt_conversion_tokens_burnt AS BIGNUMERIC), NULL) AS conversion_yocto
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions` AS t
    WHERE t.block_date BETWEEN DATE '2026-08-17' AND DATE '2026-08-30'
        OR t.block_date BETWEEN DATE '2026-09-14' AND DATE '2026-09-20'
        OR t.block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-18'
),
expected_weeks AS (
    SELECT DATE '2026-08-17' AS week_start, 5152284 AS transactions, 141295 AS accounts,
        BIGNUMERIC '232.762463065152844901859328' AS conversion_near
    UNION ALL SELECT DATE '2026-08-24', 4734816, 139759, BIGNUMERIC '213.339983351673216549040128'
    UNION ALL SELECT DATE '2026-09-14', 5689381, 145183, BIGNUMERIC '243.611538798105782119837696'
    UNION ALL SELECT DATE '2026-10-12', 4909532, 129446, BIGNUMERIC '413.27789919813321358522368'
),
week_controls AS (
    SELECT DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start, COUNT(*) AS transactions,
        COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT signer_account_id) AS active_accounts,
        COUNT(DISTINCT block_date) AS observed_days,
        COUNT(DISTINCT TIMESTAMP_TRUNC(submission_time, HOUR)) AS observed_hours,
        COUNTIF(conversion_yocto IS NULL) AS invalid_conversion_cost_rows,
        SUM(conversion_yocto) AS conversion_yocto
    FROM transactions GROUP BY week_start
),
week_comparisons AS (
    SELECT e.week_start, w.* EXCEPT(week_start),
        COALESCE(w.transactions = e.transactions AND w.distinct_transaction_hashes = e.transactions
            AND w.active_accounts = e.accounts AND w.observed_days = 7 AND w.observed_hours = 168
            AND w.invalid_conversion_cost_rows = 0
            AND ABS(w.conversion_yocto / BIGNUMERIC '1000000000000000000000000' - e.conversion_near)
                <= BIGNUMERIC '0.00001', FALSE) AS matches_result56
    FROM expected_weeks AS e LEFT JOIN week_controls AS w ON w.week_start = e.week_start
),
transaction_controls AS (
    SELECT COUNT(*) AS transaction_rows, COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT block_date) AS observed_days,
        COUNT(DISTINCT TIMESTAMP_TRUNC(submission_time, HOUR)) AS observed_hours,
        COUNTIF(NULLIF(TRIM(transaction_hash), '') IS NULL OR NULLIF(TRIM(signer_account_id), '') IS NULL
            OR NULLIF(TRIM(receiver_account_id), '') IS NULL OR submission_time IS NULL
            OR DATE(submission_time) != block_date) AS invalid_identity_or_timestamp_rows
    FROM transactions
),
account_weeks AS (
    SELECT DISTINCT DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start, signer_account_id FROM transactions
),
cohort_flags AS (
    SELECT m.signer_account_id,
        LOGICAL_OR(a.week_start = DATE '2026-08-24') AS at_1,
        LOGICAL_OR(a.week_start = DATE '2026-09-14') AS at_4,
        LOGICAL_OR(a.week_start = DATE '2026-10-12') AS at_8
    FROM account_weeks AS m INNER JOIN account_weeks AS a ON a.signer_account_id = m.signer_account_id
    WHERE m.week_start = DATE '2026-08-17'
    GROUP BY m.signer_account_id
),
cohort_counts AS (
    SELECT COUNT(*) AS cohort_accounts, COUNTIF(at_8) AS exact_week_8_accounts,
        COUNTIF(at_1 AND at_4 AND at_8) AS repeated_checkpoint_accounts FROM cohort_flags
),
selected_transactions AS (
    SELECT t.*, f.at_1 AND f.at_4 AND f.at_8 AS repeatedly_returning
    FROM transactions AS t INNER JOIN cohort_flags AS f ON f.signer_account_id = t.signer_account_id
    WHERE t.block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-18' AND f.at_8
),
selected_controls AS (
    SELECT COUNT(*) AS transactions, COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT signer_account_id) AS accounts, COUNTIF(conversion_yocto IS NULL) AS invalid_conversion_rows,
        SUM(conversion_yocto) AS conversion_yocto FROM selected_transactions
),
receipt_owners AS (
    SELECT converted_into_receipt_id AS receipt_id, COUNT(*) AS transaction_owner_rows
    FROM transactions WHERE NULLIF(TRIM(converted_into_receipt_id), '') IS NOT NULL
    GROUP BY converted_into_receipt_id
),
selected_receipts AS (
    SELECT DISTINCT converted_into_receipt_id AS receipt_id FROM selected_transactions
    WHERE NULLIF(TRIM(converted_into_receipt_id), '') IS NOT NULL
),
outcome_partition AS (
    SELECT o.block_date AS outcome_record_date, o.receipt_id, o.status AS raw_status,
        o.executor_account_id, o.block_timestamp_utc AS outcome_record_time,
        o.block_hash AS outcome_record_hash, o.executed_in_block_hash,
        SAFE_CAST(o.tokens_burnt AS BIGNUMERIC) AS cost_yocto,
        CASE WHEN o.tokens_burnt IS NULL THEN 'MISSING_COST'
            WHEN IS_NAN(o.tokens_burnt) OR IS_INF(o.tokens_burnt) THEN 'NONFINITE_COST'
            WHEN o.tokens_burnt < 0 THEN 'NEGATIVE_COST'
            WHEN SAFE_CAST(o.tokens_burnt AS BIGNUMERIC) IS NULL THEN 'UNREPRESENTABLE_COST'
            ELSE 'VALID_COST' END AS raw_cost_check
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    WHERE o.block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-24'
),
outcome_candidates AS (
    SELECT * FROM outcome_partition WHERE receipt_id IN (SELECT receipt_id FROM selected_receipts)
),
outcome_counts AS (
    SELECT receipt_id, COUNT(*) AS outcome_rows FROM outcome_candidates GROUP BY receipt_id
),
unique_outcomes AS (
    SELECT o.* FROM outcome_candidates AS o INNER JOIN outcome_counts AS n USING(receipt_id)
    WHERE n.outcome_rows = 1
),
block_partition AS (
    SELECT block_date, block_hash, block_height, block_timestamp_utc
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-24'
),
block_counts AS (
    SELECT block_hash, COUNT(*) AS block_rows FROM block_partition GROUP BY block_hash
),
unique_blocks AS (
    SELECT b.* FROM block_partition AS b INNER JOIN block_counts AS n USING(block_hash)
    WHERE n.block_rows = 1
),
controls AS (
    SELECT tc.*, cc.*, sc.transactions AS selected_transactions, sc.accounts AS selected_accounts,
        (SELECT COUNTIF(matches_result56) FROM week_comparisons) AS matching_week_controls,
        tc.transaction_rows = tc.distinct_transaction_hashes AND tc.observed_days = 28
            AND tc.observed_hours = 672 AND tc.invalid_identity_or_timestamp_rows = 0
            AND (SELECT COUNTIF(matches_result56) FROM week_comparisons) = 4
            AND cc.cohort_accounts = 141295 AND cc.exact_week_8_accounts = 65251
            AND cc.repeated_checkpoint_accounts = 53455 AND sc.accounts = 65251
            AND sc.transactions = 3528043 AND sc.distinct_transaction_hashes = 3528043
            AND sc.invalid_conversion_rows = 0
            AND ABS(sc.conversion_yocto / BIGNUMERIC '1000000000000000000000000'
                - BIGNUMERIC '163.70758505454832910422016') <= BIGNUMERIC '0.00001'
            AS result56_controls_passed,
        (SELECT COUNT(*) FROM outcome_partition) AS observed_outcome_partition_rows,
        (SELECT COUNT(DISTINCT outcome_record_date) FROM outcome_partition) AS observed_outcome_days,
        (SELECT COUNT(*) FROM selected_receipts) AS selected_distinct_receipt_ids,
        (SELECT COUNT(*) FROM outcome_counts) AS receipt_ids_with_observed_outcomes,
        (SELECT COUNTIF(outcome_rows > 1) FROM outcome_counts) AS receipt_ids_with_multiple_outcomes,
        (SELECT COUNT(*) FROM outcome_candidates) AS selected_outcome_observations,
        (SELECT COUNT(*) FROM block_partition) AS observed_block_partition_rows,
        (SELECT COUNT(DISTINCT block_date) FROM block_partition) AS observed_block_days
    FROM transaction_controls AS tc CROSS JOIN cohort_counts AS cc CROSS JOIN selected_controls AS sc
),
joined AS (
    SELECT t.*, ro.transaction_owner_rows, COALESCE(n.outcome_rows, 0) AS outcome_rows,
        u.* EXCEPT(receipt_id), COALESCE(bn.block_rows, 0) AS block_rows,
        b.block_date AS execution_block_date, b.block_height AS execution_height,
        b.block_timestamp_utc AS execution_time
    FROM selected_transactions AS t
    LEFT JOIN receipt_owners AS ro ON ro.receipt_id = t.converted_into_receipt_id
    LEFT JOIN outcome_counts AS n ON n.receipt_id = t.converted_into_receipt_id
    LEFT JOIN unique_outcomes AS u ON u.receipt_id = t.converted_into_receipt_id
    LEFT JOIN block_counts AS bn ON bn.block_hash = u.executed_in_block_hash
    LEFT JOIN unique_blocks AS b ON b.block_hash = u.executed_in_block_hash
),
assessments AS (
    SELECT *, CASE
        WHEN NULLIF(TRIM(converted_into_receipt_id), '') IS NULL THEN 'MISSING_INITIAL_RECEIPT_ID'
        WHEN converted_into_receipt_id != TRIM(converted_into_receipt_id) THEN 'INVALID_INITIAL_RECEIPT_ID'
        WHEN COALESCE(transaction_owner_rows, 0) != 1 THEN 'SHARED_INITIAL_RECEIPT_ID'
        WHEN outcome_rows = 0 THEN 'NO_OUTCOME_IN_LOOKUP_WINDOW'
        WHEN outcome_rows != 1 THEN 'MULTIPLE_OUTCOME_OBSERVATIONS'
        WHEN NULLIF(TRIM(executed_in_block_hash), '') IS NULL THEN 'MISSING_EXECUTION_HASH'
        WHEN block_rows = 0 THEN 'EXECUTION_BLOCK_UNAVAILABLE_OR_BOUNDARY'
        WHEN block_rows != 1 THEN 'MULTIPLE_EXECUTION_BLOCK_OBSERVATIONS'
        WHEN execution_time IS NULL OR execution_height IS NULL OR execution_height < 0
            OR DATE(execution_time) != execution_block_date THEN 'INVALID_EXECUTION_BLOCK'
        WHEN outcome_record_time IS NULL OR DATE(outcome_record_time) != outcome_record_date
            THEN 'INVALID_OUTCOME_RECORD_TIME'
        WHEN executor_account_id IS NULL OR executor_account_id != receiver_account_id THEN 'EXECUTOR_MISMATCH_OR_UNAVAILABLE'
        WHEN raw_status IS NULL OR raw_status NOT IN ('SUCCESS_VALUE', 'SUCCESS_RECEIPT_ID', 'FAILURE')
            THEN 'STATUS_UNAVAILABLE_OR_UNRECOGNIZED'
        WHEN execution_time < submission_time THEN 'NEGATIVE_EXECUTION_LAG'
        WHEN execution_time >= TIMESTAMP '2026-10-25 00:00:00+00' THEN 'EXECUTION_AFTER_LOOKUP_CUTOFF'
        ELSE 'ASSESSED_INITIAL_RECEIPT' END AS assessment
    FROM joined
),
classified AS (
    SELECT *, IF(raw_status IN ('SUCCESS_VALUE', 'SUCCESS_RECEIPT_ID', 'FAILURE'), raw_status, 'UNAVAILABLE_OR_OTHER')
            AS observed_initial_status,
        IF(assessment = 'ASSESSED_INITIAL_RECEIPT', raw_cost_check, 'UNASSESSED_LINK_OR_EXECUTION') AS cost_check,
        IF(assessment = 'ASSESSED_INITIAL_RECEIPT', DATE(execution_time), NULL) AS execution_date,
        IF(assessment = 'ASSESSED_INITIAL_RECEIPT' AND raw_cost_check = 'VALID_COST', cost_yocto, NULL)
            AS assessed_cost_yocto
    FROM assessments
),
population_rows AS (
    SELECT 'EXACT_WEEK_8_RETURNERS' AS population, c.* FROM classified AS c
    UNION ALL
    SELECT 'REPEATED_CHECKPOINT_RETURNERS', c.* FROM classified AS c WHERE repeatedly_returning
),
population_names AS (
    SELECT 'EXACT_WEEK_8_RETURNERS' AS population UNION ALL SELECT 'REPEATED_CHECKPOINT_RETURNERS'
),
population_stats AS (
    SELECT population, COUNT(*) AS transactions, COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT signer_account_id) AS accounts,
        COUNTIF(conversion_yocto IS NULL) AS invalid_conversion_rows, SUM(conversion_yocto) AS conversion_yocto,
        COUNTIF(assessment = 'ASSESSED_INITIAL_RECEIPT') AS assessed_initial_receipts,
        COUNTIF(assessment != 'ASSESSED_INITIAL_RECEIPT') AS unassessed_initial_receipts,
        COUNT(DISTINCT IF(assessment = 'ASSESSED_INITIAL_RECEIPT', signer_account_id, NULL)) AS accounts_with_assessed_initial_receipts,
        COUNT(DISTINCT IF(assessment = 'ASSESSED_INITIAL_RECEIPT'
            AND raw_status IN ('SUCCESS_VALUE', 'SUCCESS_RECEIPT_ID'), signer_account_id, NULL)) AS accounts_with_successful_initial_receipts,
        COUNT(DISTINCT IF(assessment = 'ASSESSED_INITIAL_RECEIPT'
            AND raw_status = 'FAILURE', signer_account_id, NULL)) AS accounts_with_failed_initial_receipts,
        MIN(IF(assessment = 'ASSESSED_INITIAL_RECEIPT', TIMESTAMP_DIFF(execution_time, submission_time, MICROSECOND), NULL))
            AS minimum_assessed_execution_lag_microseconds,
        MAX(IF(assessment = 'ASSESSED_INITIAL_RECEIPT', TIMESTAMP_DIFF(execution_time, submission_time, MICROSECOND), NULL))
            AS maximum_assessed_execution_lag_microseconds,
        COUNTIF(assessed_cost_yocto IS NOT NULL) AS valid_initial_cost_transactions,
        SUM(assessed_cost_yocto) AS valid_initial_cost_yocto,
        COUNTIF(assessment = 'ASSESSED_INITIAL_RECEIPT' AND cost_check != 'VALID_COST') AS invalid_assessed_cost_rows,
        COUNTIF(outcome_rows = 1 AND outcome_record_hash != executed_in_block_hash) AS record_execution_hash_disagreements,
        COUNTIF(block_rows = 1 AND outcome_record_time != execution_time) AS record_execution_time_disagreements
    FROM population_rows GROUP BY population
),
bucket_stats AS (
    SELECT population, assessment, observed_initial_status, cost_check, execution_date,
        DATE_TRUNC(execution_date, WEEK(MONDAY)) AS execution_week,
        COUNT(*) AS transactions, COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        SUM(outcome_rows) AS matched_outcome_observations,
        COUNTIF(assessed_cost_yocto IS NOT NULL) AS valid_initial_cost_transactions,
        SUM(assessed_cost_yocto) AS valid_initial_cost_yocto,
        COUNTIF(execution_date BETWEEN DATE '2026-10-19' AND DATE '2026-10-24') AS partial_tail_transactions,
        ARRAY_AGG(STRUCT(transaction_hash, converted_into_receipt_id, outcome_record_date, outcome_record_hash,
            outcome_record_time, executed_in_block_hash, execution_time, raw_status)
            ORDER BY transaction_hash LIMIT 3) AS diagnostic_examples
    FROM population_rows
    GROUP BY population, assessment, observed_initial_status, cost_check, execution_date, execution_week
),
summary_record AS (
    SELECT TO_JSON_STRING(STRUCT(
        DATE '2026-08-17' AS cohort_week, DATE '2026-10-12' AS submission_week,
        DATE '2026-10-18' AS submission_week_end, DATE '2026-10-24' AS lookup_end,
        g.transaction_rows, g.distinct_transaction_hashes, g.observed_days, g.observed_hours,
        g.invalid_identity_or_timestamp_rows, g.cohort_accounts, g.exact_week_8_accounts,
        g.repeated_checkpoint_accounts, g.selected_transactions, g.selected_accounts,
        g.matching_week_controls, g.result56_controls_passed,
        g.observed_outcome_partition_rows, g.observed_outcome_days,
        g.selected_distinct_receipt_ids, g.receipt_ids_with_observed_outcomes,
        g.receipt_ids_with_multiple_outcomes, g.selected_outcome_observations,
        g.observed_block_partition_rows, g.observed_block_days,
        (SELECT COUNT(*) FROM classified) AS classified_transaction_rows,
        (SELECT COUNT(DISTINCT transaction_hash) FROM classified) AS classified_distinct_transaction_hashes,
        4 AS week_control_records, 2 AS population_records,
        (SELECT COUNT(*) FROM bucket_stats) AS bucket_records,
        'INITIAL_RECEIPTS_ONLY_OUTER_SIGNER_ASSOCIATION_NOT_COMPLETE_CHAIN_OR_REVENUE' AS scope,
        'OWNERSHIP_COUNTS_BOUNDED_TO_FOUR_TX_WEEKS_OBSERVED_COVERAGE_ONLY' AS coverage_basis
    )) AS record_json FROM controls AS g
),
population_records AS (
    SELECT TO_JSON_STRING(STRUCT(
        n.population, DATE '2026-08-17' AS cohort_week, DATE '2026-10-12' AS submission_week,
        g.result56_controls_passed, g.observed_outcome_days = 13 AND g.observed_block_days = 13 AS lookup_days_observed,
        COALESCE(p.accounts, 0) AS observed_accounts, COALESCE(p.transactions, 0) AS transactions,
        COALESCE(p.distinct_transaction_hashes, 0) AS distinct_transaction_hashes,
        COALESCE(p.invalid_conversion_rows, 0) AS invalid_conversion_rows,
        IF(g.result56_controls_passed AND p.invalid_conversion_rows = 0,
            CAST(p.conversion_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL) AS recorded_conversion_spending_near,
        COALESCE(p.assessed_initial_receipts, 0) AS assessed_initial_receipts,
        COALESCE(p.unassessed_initial_receipts, 0) AS unassessed_initial_receipts,
        COALESCE(p.accounts_with_assessed_initial_receipts, 0) AS accounts_with_assessed_initial_receipts,
        COALESCE(p.accounts_with_successful_initial_receipts, 0) AS accounts_with_successful_initial_receipts,
        COALESCE(p.accounts_with_failed_initial_receipts, 0) AS accounts_with_failed_initial_receipts,
        p.minimum_assessed_execution_lag_microseconds, p.maximum_assessed_execution_lag_microseconds,
        COALESCE(p.valid_initial_cost_transactions, 0) AS valid_initial_cost_transactions,
        COALESCE(p.invalid_assessed_cost_rows, 0) AS invalid_assessed_cost_rows,
        IF(g.result56_controls_passed AND p.valid_initial_cost_transactions > 0,
            CAST(p.valid_initial_cost_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
            AS valid_assessed_initial_spending_subtotal_near,
        IF(g.result56_controls_passed AND g.observed_outcome_days = 13 AND g.observed_block_days = 13
            AND p.valid_initial_cost_transactions = p.transactions AND p.transactions > 0,
            CAST(p.valid_initial_cost_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
            AS complete_initial_receipt_spending_near,
        COALESCE(p.record_execution_hash_disagreements, 0) AS record_execution_hash_disagreements,
        COALESCE(p.record_execution_time_disagreements, 0) AS record_execution_time_disagreements
    )) AS record_json
    FROM population_names AS n CROSS JOIN controls AS g
    LEFT JOIN population_stats AS p ON p.population = n.population
),
bucket_records AS (
    SELECT TO_JSON_STRING(STRUCT(
        b.population, DATE '2026-10-12' AS submission_week,
        b.assessment, b.observed_initial_status, b.cost_check, b.execution_date, b.execution_week,
        b.transactions, b.distinct_transaction_hashes, b.matched_outcome_observations,
        b.valid_initial_cost_transactions, b.partial_tail_transactions,
        IF(g.result56_controls_passed AND b.valid_initial_cost_transactions > 0,
            CAST(b.valid_initial_cost_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
            AS valid_assessed_initial_spending_subtotal_near,
        b.diagnostic_examples, 'UP_TO_THREE_EXAMPLES_NOT_CANONICAL_MATCH_SELECTION' AS example_scope
    )) AS record_json FROM bucket_stats AS b CROSS JOIN controls AS g
)
SELECT 'SUMMARY' AS row_kind, record_json FROM summary_record
UNION ALL
SELECT 'WEEK_CONTROL', TO_JSON_STRING(STRUCT(
    week_start, transactions, distinct_transaction_hashes, active_accounts, observed_days, observed_hours,
    invalid_conversion_cost_rows, matches_result56,
    IF(invalid_conversion_cost_rows = 0, CAST(conversion_yocto / BIGNUMERIC '1000000000000000000000000' AS STRING), NULL)
        AS recorded_conversion_spending_near
)) FROM week_comparisons
UNION ALL
SELECT 'POPULATION', record_json FROM population_records
UNION ALL
SELECT 'ASSESSMENT_BUCKET', record_json FROM bucket_records
ORDER BY row_kind DESC, record_json;

