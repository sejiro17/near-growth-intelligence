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
        signer_account_id,
        receiver_account_id,
        converted_into_receipt_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
        AND signer_account_id IN (
            'tinykoala595.near',
            'wx-cruce.near'
        )
),
selected_receipts AS (
    SELECT DISTINCT converted_into_receipt_id AS receipt_id
    FROM selected_transactions
    WHERE converted_into_receipt_id IS NOT NULL
        AND TRIM(converted_into_receipt_id) != ''
),
receipt_outcomes AS (
    SELECT
        o.receipt_id,
        COUNT(*) AS outcome_rows,
        MAX(o.status) AS outcome_status,
        MAX(o.executor_account_id) AS executor_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
        AS o
    INNER JOIN selected_receipts AS r
        ON o.receipt_id = r.receipt_id
    WHERE o.block_date BETWEEN DATE '2026-08-24'
                               AND DATE '2026-10-19'
    GROUP BY o.receipt_id
),
classified_transactions AS (
    SELECT
        t.week_start,
        t.transaction_hash,
        t.signer_account_id,
        t.receiver_account_id,
        t.converted_into_receipt_id,
        COALESCE(o.outcome_rows, 0) AS outcome_rows,
        CASE
            WHEN t.converted_into_receipt_id IS NULL
                OR TRIM(t.converted_into_receipt_id) = ''
                THEN 'MISSING_INITIAL_RECEIPT_ID'
            WHEN o.receipt_id IS NULL
                THEN 'NO_MATCHING_OUTCOME'
            WHEN o.outcome_rows != 1
                THEN 'MULTIPLE_MATCHING_OUTCOMES'
            ELSE COALESCE(
                NULLIF(TRIM(o.outcome_status), ''),
                'MISSING_STATUS'
            )
        END AS initial_receipt_status,
        CASE
            WHEN COALESCE(o.outcome_rows, 0) != 1
                THEN 'NOT_ASSESSED'
            WHEN o.executor_account_id IS NULL
                OR TRIM(o.executor_account_id) = ''
                THEN 'MISSING_EXECUTOR'
            WHEN o.executor_account_id = t.receiver_account_id
                THEN 'EXECUTOR_MATCHES_RECEIVER'
            ELSE 'EXECUTOR_DIFFERS_FROM_RECEIVER'
        END AS executor_check
    FROM selected_transactions AS t
    LEFT JOIN receipt_outcomes AS o
        ON t.converted_into_receipt_id = o.receipt_id
),
weekly_totals AS (
    SELECT
        week_start,
        signer_account_id,
        COUNT(*) AS account_week_transactions,
        COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT converted_into_receipt_id)
            AS distinct_nonnull_initial_receipt_ids
    FROM selected_transactions
    GROUP BY week_start, signer_account_id
),
outcome_summary AS (
    SELECT
        week_start,
        signer_account_id,
        initial_receipt_status,
        executor_check,
        COUNT(*) AS transactions,
        SUM(outcome_rows) AS matched_outcome_rows
    FROM classified_transactions
    GROUP BY
        week_start,
        signer_account_id,
        initial_receipt_status,
        executor_check
)
SELECT
    s.week_start,
    DATE_ADD(s.week_start, INTERVAL 6 DAY) AS week_end,
    s.signer_account_id,
    s.initial_receipt_status,
    s.executor_check,
    s.transactions,
    s.matched_outcome_rows,
    ROUND(
        100.0 * SAFE_DIVIDE(
            s.transactions,
            w.account_week_transactions
        ),
        4
    ) AS account_transaction_share_pct,
    w.account_week_transactions,
    w.distinct_transaction_hashes,
    w.distinct_nonnull_initial_receipt_ids
FROM outcome_summary AS s
INNER JOIN weekly_totals AS w
    ON s.week_start = w.week_start
    AND s.signer_account_id = w.signer_account_id
ORDER BY
    s.signer_account_id,
    s.week_start,
    s.initial_receipt_status,
    s.executor_check;