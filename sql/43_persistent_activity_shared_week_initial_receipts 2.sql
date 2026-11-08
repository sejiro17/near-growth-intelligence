/* @datacloud.settings
{
  "version": 1,
  "service": "BIG_QUERY",
  "connectionInfo": {"billingProjectId": "INHERIT"},
  "dialect": "GOOGLE_SQL"
}
*/

/*
Bounded replication of SQL 42: one shared submission week, 5–11 October 2026.
Groups: 10 August activity cohort at +8; its all-three-checkpoint subset; and
28 September activity cohort at +1. The groups overlap; never add their totals.
The 28 September +4/+8 follow-ups remain unavailable; no repeated group is emitted.

Result 58 establishes complete observed initial-receipt matching for the separate
12–18 October pilot. It does not establish this week's ingestion completeness.
Each group must reproduce its available result-56 counts and conversion controls.
Unknown baseline transactions/costs for the repeated subset remain NULL controls;
its observed outputs are computed from source rows, not supplied by controls.

Five transaction weeks reconstruct these groups. Outcome and block lookups cover
5–17 October only, with a six-day partial execution-week tail, 12–17 October.
A fixed cutoff gives unequal elapsed follow-up for different submission dates.
Schema and classification follow SQL 42. Counts are grouped before joining;
all duplicate outcome/block matches are excluded rather than arbitrarily selected.
Receipt-owner uniqueness is bounded to these five transaction weeks only.
Classification precedes intentional expansion into overlapping population groups.

Only initial receipts are assessed; success does not establish descendant or
complete-chain success. Costs are FLOAT-derived observed spending associated with
outer signers, not verified economic payers, revenue, purchases, burn or holder
value. The 0.00001 NEAR baseline screen tests saved arithmetic, not source accuracy.
Missing costs/matches remain unavailable; complete totals require full valid-cost
coverage. Valid subtotals carry their assessed count. Actual execution time comes
from unique block-hash matches. Source and execution identities/times are separate.
Diagnostic examples retain exact identifiers but are limited to three per bucket.
Bucket matched-outcome counts are transaction-weighted, not unique-receipt totals.
Account success and failure groups may overlap. No actions/deletions are read.
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
    WHERE t.block_date BETWEEN DATE '2026-08-10' AND DATE '2026-08-23'
        OR t.block_date BETWEEN DATE '2026-09-07' AND DATE '2026-09-13'
        OR t.block_date BETWEEN DATE '2026-09-28' AND DATE '2026-10-11'
),
expected_weeks AS (
    SELECT DATE '2026-08-10' AS week_start, 4521998 AS transactions, 139856 AS accounts,
        BIGNUMERIC '210.057205399162793005236224' AS conversion_near
    UNION ALL SELECT DATE '2026-08-17', 5152284, 141295, BIGNUMERIC '232.762463065152844901859328'
    UNION ALL SELECT DATE '2026-09-07', 5076874, 132731, BIGNUMERIC '227.700051211935637929254912'
    UNION ALL SELECT DATE '2026-09-28', 6590352, 457768, BIGNUMERIC '275.529289708540204041216'
    UNION ALL SELECT DATE '2026-10-05', 6401624, 384444, BIGNUMERIC '262.343948111339008871845888'
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
group_definitions AS (
    SELECT 'AUG10_EXACT_WEEK8' AS population, DATE '2026-08-10' AS cohort_week, 8 AS week_offset,
        'EXACT_WEEK_RETURNERS' AS return_definition, 139856 AS expected_cohort_accounts,
        66309 AS expected_accounts, 3888965 AS expected_transactions,
        BIGNUMERIC '178.091295295805881218842624' AS expected_conversion_near
    UNION ALL SELECT 'AUG10_REPEATED_CHECKPOINTS', DATE '2026-08-10', 8,
        'ALL_THREE_EXACT_CHECKPOINTS_1_4_8', 139856, 52423, CAST(NULL AS INT64), CAST(NULL AS BIGNUMERIC)
    UNION ALL SELECT 'SEP28_EXACT_WEEK1', DATE '2026-09-28', 1,
        'EXACT_WEEK_RETURNERS', 457768, 83037, 5174834, BIGNUMERIC '224.114123400778586446954496'
),
aug10_flags AS (
    SELECT m.signer_account_id,
        LOGICAL_OR(a.week_start = DATE '2026-08-17') AS at_1,
        LOGICAL_OR(a.week_start = DATE '2026-09-07') AS at_4,
        LOGICAL_OR(a.week_start = DATE '2026-10-05') AS at_8
    FROM account_weeks AS m INNER JOIN account_weeks AS a ON a.signer_account_id = m.signer_account_id
    WHERE m.week_start = DATE '2026-08-10'
    GROUP BY m.signer_account_id
),
group_membership AS (
    SELECT 'AUG10_EXACT_WEEK8' AS population, signer_account_id FROM aug10_flags WHERE at_8
    UNION ALL
    SELECT 'AUG10_REPEATED_CHECKPOINTS', signer_account_id FROM aug10_flags WHERE at_1 AND at_4 AND at_8
    UNION ALL
    SELECT 'SEP28_EXACT_WEEK1', m.signer_account_id
    FROM account_weeks AS m INNER JOIN account_weeks AS a ON a.signer_account_id = m.signer_account_id
    WHERE m.week_start = DATE '2026-09-28' AND a.week_start = DATE '2026-10-05'
),
group_membership_counts AS (
    SELECT population, COUNT(*) AS membership_rows, COUNT(DISTINCT signer_account_id) AS distinct_members
    FROM group_membership GROUP BY population
),
selected_signers AS (
    SELECT DISTINCT signer_account_id FROM group_membership
),
selected_transactions AS (
    SELECT t.* FROM transactions AS t INNER JOIN selected_signers AS s USING(signer_account_id)
    WHERE t.block_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-11'
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
    WHERE o.block_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-17'
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
    WHERE block_date BETWEEN DATE '2026-10-05' AND DATE '2026-10-17'
),
block_counts AS (
    SELECT block_hash, COUNT(*) AS block_rows FROM block_partition GROUP BY block_hash
),
unique_blocks AS (
    SELECT b.* FROM block_partition AS b INNER JOIN block_counts AS n USING(block_hash)
    WHERE n.block_rows = 1
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
        WHEN execution_time >= TIMESTAMP '2026-10-18 00:00:00+00' THEN 'EXECUTION_AFTER_LOOKUP_CUTOFF'
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
    SELECT m.population, c.* FROM classified AS c
    INNER JOIN group_membership AS m ON m.signer_account_id = c.signer_account_id
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
        COUNTIF(execution_date BETWEEN DATE '2026-10-12' AND DATE '2026-10-17') AS partial_tail_transactions,
        ARRAY_AGG(STRUCT(transaction_hash, converted_into_receipt_id, outcome_record_date, outcome_record_hash,
            outcome_record_time, executed_in_block_hash, execution_time, raw_status)
            ORDER BY transaction_hash LIMIT 3) AS diagnostic_examples
    FROM population_rows
    GROUP BY population, assessment, observed_initial_status, cost_check, execution_date, execution_week
),
group_reproductions AS (
    SELECT d.population,
        COALESCE(p.accounts = d.expected_accounts
            AND p.transactions = p.distinct_transaction_hashes AND p.invalid_conversion_rows = 0
            AND m.membership_rows = m.distinct_members AND m.distinct_members = d.expected_accounts
            AND (d.expected_transactions IS NULL OR p.transactions = d.expected_transactions)
            AND (d.expected_conversion_near IS NULL
                OR ABS(p.conversion_yocto / BIGNUMERIC '1000000000000000000000000' - d.expected_conversion_near)
                    <= BIGNUMERIC '0.00001'), FALSE) AS matches_result56
    FROM group_definitions AS d LEFT JOIN population_stats AS p USING(population)
    LEFT JOIN group_membership_counts AS m USING(population)
),
controls AS (
    SELECT tc.*, sc.transactions AS selected_transactions, sc.accounts AS selected_accounts,
        (SELECT COUNTIF(matches_result56) FROM week_comparisons) AS matching_week_controls,
        (SELECT COUNTIF(matches_result56) FROM group_reproductions) AS matching_group_controls,
        tc.transaction_rows = tc.distinct_transaction_hashes AND tc.observed_days = 35
            AND tc.observed_hours = 840 AND tc.invalid_identity_or_timestamp_rows = 0
            AND sc.transactions = sc.distinct_transaction_hashes AND sc.invalid_conversion_rows = 0
            AND (SELECT COUNTIF(matches_result56) FROM week_comparisons) = 5
            AND (SELECT COUNTIF(matches_result56) FROM group_reproductions) = 3 AS result56_controls_passed,
        (SELECT COUNT(*) FROM outcome_partition) AS observed_outcome_partition_rows,
        (SELECT COUNT(DISTINCT outcome_record_date) FROM outcome_partition) AS observed_outcome_days,
        (SELECT COUNT(*) FROM selected_receipts) AS selected_distinct_receipt_ids,
        (SELECT COUNT(*) FROM outcome_counts) AS receipt_ids_with_observed_outcomes,
        (SELECT COUNTIF(outcome_rows > 1) FROM outcome_counts) AS receipt_ids_with_multiple_outcomes,
        (SELECT COUNT(*) FROM outcome_candidates) AS selected_outcome_observations,
        (SELECT COUNT(*) FROM block_partition) AS observed_block_partition_rows,
        (SELECT COUNT(DISTINCT block_date) FROM block_partition) AS observed_block_days
    FROM transaction_controls AS tc CROSS JOIN selected_controls AS sc
),
summary_record AS (
    SELECT TO_JSON_STRING(STRUCT(
        DATE '2026-10-05' AS submission_week, DATE '2026-10-11' AS submission_week_end,
        DATE '2026-10-17' AS lookup_end,
        g.transaction_rows, g.distinct_transaction_hashes, g.observed_days, g.observed_hours,
        g.invalid_identity_or_timestamp_rows, g.selected_transactions, g.selected_accounts,
        g.matching_week_controls, g.matching_group_controls, g.result56_controls_passed,
        g.observed_outcome_partition_rows, g.observed_outcome_days,
        g.selected_distinct_receipt_ids, g.receipt_ids_with_observed_outcomes,
        g.receipt_ids_with_multiple_outcomes, g.selected_outcome_observations,
        g.observed_block_partition_rows, g.observed_block_days,
        (SELECT COUNT(*) FROM classified) AS classified_transaction_rows,
        (SELECT COUNT(DISTINCT transaction_hash) FROM classified) AS classified_distinct_transaction_hashes,
        5 AS week_control_records, 3 AS population_records,
        (SELECT COUNT(*) FROM bucket_stats) AS bucket_records,
        'OVERLAPPING_GROUPS_INITIAL_RECEIPTS_ONLY_NOT_COMPLETE_CHAIN_OR_REVENUE' AS scope,
        'OWNERSHIP_COUNTS_BOUNDED_TO_FIVE_TX_WEEKS_OBSERVED_COVERAGE_ONLY' AS coverage_basis
    )) AS record_json FROM controls AS g
),
population_records AS (
    SELECT TO_JSON_STRING(STRUCT(
        n.population, n.cohort_week, n.week_offset, n.return_definition,
        n.expected_cohort_accounts, n.expected_accounts, n.expected_transactions,
        CAST(n.expected_conversion_near AS STRING) AS expected_conversion_near,
        r.matches_result56 AS group_matches_result56, DATE '2026-10-05' AS submission_week,
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
    FROM group_definitions AS n CROSS JOIN controls AS g
    LEFT JOIN group_reproductions AS r ON r.population = n.population
    LEFT JOIN population_stats AS p ON p.population = n.population
),
bucket_records AS (
    SELECT TO_JSON_STRING(STRUCT(
        b.population, DATE '2026-10-05' AS submission_week,
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
