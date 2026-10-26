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
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        transaction_hash,
        signer_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
        AND signer_account_id IN (
            'sweat-relayer.near',
            'intents.near',
            'closemeat6237.near',
            'omni-relayer.bridge.near',
            'meteor-relayer.near'
        )
),
selected_actions AS (
    SELECT
        transaction_hash,
        action_kind,
        index_in_transaction,
        CASE
            WHEN action_kind = 'FUNCTION_CALL'
            THEN NULLIF(
                TRIM(JSON_VALUE(args, '$.method_name')),
                ''
            )
        END AS method_name
    FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
        AND signer_account_id IN (
            'sweat-relayer.near',
            'intents.near',
            'closemeat6237.near',
            'omni-relayer.bridge.near',
            'meteor-relayer.near'
        )
),
joined_records AS (
    SELECT
        t.week_start,
        t.signer_account_id,
        t.transaction_hash,
        a.transaction_hash IS NOT NULL AS action_record_matched,
        CASE
            WHEN a.transaction_hash IS NULL
                THEN 'NO_MATCHING_ACTION_RECORD'
            ELSE COALESCE(
                NULLIF(TRIM(a.action_kind), ''),
                'MISSING_ACTION_KIND'
            )
        END AS action_kind,
        a.method_name,
        a.index_in_transaction
    FROM selected_transactions AS t
    LEFT JOIN selected_actions AS a
        ON t.transaction_hash = a.transaction_hash
),
transaction_coverage AS (
    SELECT
        week_start,
        signer_account_id,
        transaction_hash,
        LOGICAL_OR(action_record_matched) AS has_action_record
    FROM joined_records
    GROUP BY
        week_start,
        signer_account_id,
        transaction_hash
),
weekly_coverage AS (
    SELECT
        week_start,
        signer_account_id,
        COUNT(*) AS account_week_transactions,
        COUNTIF(has_action_record) AS transactions_with_action_records,
        COUNTIF(
            NOT has_action_record
        ) AS transactions_without_action_records
    FROM transaction_coverage
    GROUP BY week_start, signer_account_id
),
action_summary AS (
    SELECT
        week_start,
        signer_account_id,
        action_kind,
        method_name,
        COUNT(DISTINCT transaction_hash) AS transactions,
        COUNTIF(action_record_matched) AS action_rows,
        COUNTIF(
            action_record_matched
            AND index_in_transaction IS NULL
        ) AS action_rows_without_index,
        COUNTIF(
            action_record_matched
            AND action_kind = 'FUNCTION_CALL'
            AND method_name IS NULL
        ) AS function_call_rows_without_method
    FROM joined_records
    GROUP BY
        week_start,
        signer_account_id,
        action_kind,
        method_name
)
SELECT
    s.week_start,
    DATE_ADD(s.week_start, INTERVAL 6 DAY) AS week_end,
    s.signer_account_id,
    s.action_kind,
    s.method_name,
    s.transactions,
    s.action_rows,
    s.action_rows_without_index,
    s.function_call_rows_without_method,
    ROUND(
        100.0 * SAFE_DIVIDE(
            s.transactions,
            c.account_week_transactions
        ),
        4
    ) AS account_transaction_share_pct,
    c.account_week_transactions,
    c.transactions_with_action_records,
    c.transactions_without_action_records
FROM action_summary AS s
INNER JOIN weekly_coverage AS c
    ON s.week_start = c.week_start
    AND s.signer_account_id = c.signer_account_id
ORDER BY
    s.signer_account_id,
    s.week_start,
    s.transactions DESC,
    s.action_kind,
    s.method_name;