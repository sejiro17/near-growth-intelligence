/* @datacloud.settings
{
  "version": 1,
  "service": "BIG_QUERY",
  "connectionInfo": {
    "billingProjectId": "INHERIT"
  },
  "dialect": "GOOGLE_SQL"
}
*/

WITH selected_transactions AS (
    SELECT
        block_date,
        transaction_hash,
        signer_account_id,
        receiver_account_id,
        converted_into_receipt_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-11'
),
following_week_accounts AS (
    SELECT DISTINCT
        signer_account_id
    FROM selected_transactions
    WHERE block_date BETWEEN DATE '2026-10-05'
                             AND DATE '2026-10-11'
),
deletion_actions AS (
    SELECT
        transaction_hash,
        COUNT(*) AS deletion_action_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-04'
        AND action_kind = 'DELETE_ACCOUNT'
    GROUP BY transaction_hash
),
deletion_transactions AS (
    SELECT
        t.transaction_hash,
        t.signer_account_id,
        t.receiver_account_id,
        t.converted_into_receipt_id,
        d.deletion_action_rows,
        CASE
            WHEN f.signer_account_id IS NOT NULL
                THEN 'ACTIVE_FOLLOWING_WEEK'
            ELSE 'NOT_ACTIVE_FOLLOWING_WEEK'
        END AS return_group,
        CASE
            WHEN t.signer_account_id = t.receiver_account_id
                THEN 'SIGNER_EQUALS_RECEIVER'
            ELSE 'SIGNER_DIFFERS_FROM_RECEIVER'
        END AS deletion_target
    FROM selected_transactions AS t
    INNER JOIN deletion_actions AS d
        ON t.transaction_hash = d.transaction_hash
    LEFT JOIN following_week_accounts AS f
        ON t.signer_account_id = f.signer_account_id
    WHERE t.block_date BETWEEN DATE '2026-09-28'
                               AND DATE '2026-10-04'
),
receipt_outcomes AS (
    SELECT
        receipt_id,
        COUNT(*) AS matching_outcome_rows,
        MAX(status) AS outcome_status,
        MAX(executor_account_id) AS executor_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-11'
        AND receipt_id IN (
            SELECT converted_into_receipt_id
            FROM deletion_transactions
            WHERE converted_into_receipt_id IS NOT NULL
        )
    GROUP BY receipt_id
),
classified AS (
    SELECT
        t.*,
        COALESCE(o.matching_outcome_rows, 0) AS matching_outcome_rows,
        CASE
            WHEN NULLIF(
                TRIM(t.converted_into_receipt_id), ''
            ) IS NULL
                THEN 'MISSING_INITIAL_RECEIPT_ID'
            WHEN o.receipt_id IS NULL
                THEN 'NO_OUTCOME_IN_LOOKUP_WINDOW'
            WHEN o.matching_outcome_rows != 1
                THEN 'MULTIPLE_MATCHING_OUTCOMES'
            WHEN NULLIF(TRIM(o.outcome_status), '') IS NULL
                THEN 'MISSING_OUTCOME_STATUS'
            ELSE o.outcome_status
        END AS initial_receipt_status,
        CASE
            WHEN o.matching_outcome_rows = 1
                AND o.executor_account_id = t.receiver_account_id
                THEN 'EXECUTOR_MATCHES_RECEIVER'
            WHEN o.matching_outcome_rows = 1
                THEN 'EXECUTOR_MISSING_OR_DIFFERENT'
            ELSE 'NOT_CHECKABLE'
        END AS executor_check
    FROM deletion_transactions AS t
    LEFT JOIN receipt_outcomes AS o
        ON t.converted_into_receipt_id = o.receipt_id
)
SELECT
    DATE '2026-09-28' AS cohort_week,
    DATE '2026-10-04' AS cohort_week_end,
    DATE '2026-10-05' AS followup_week,
    DATE '2026-10-11' AS followup_week_end,
    return_group,
    deletion_target,
    initial_receipt_status,
    executor_check,
    COUNT(*) AS deletion_transactions,
    COUNT(DISTINCT signer_account_id) AS signing_accounts,
    COUNT(DISTINCT receiver_account_id) AS target_accounts,
    SUM(deletion_action_rows) AS deletion_action_rows,
    SUM(matching_outcome_rows) AS matching_outcome_rows
FROM classified
GROUP BY
    return_group,
    deletion_target,
    initial_receipt_status,
    executor_check
ORDER BY
    return_group,
    deletion_target,
    initial_receipt_status,
    executor_check;
