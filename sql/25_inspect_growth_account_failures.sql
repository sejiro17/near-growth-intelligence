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
        block_timestamp_utc AS transaction_timestamp_utc,
        transaction_hash,
        signer_account_id,
        receiver_account_id,
        converted_into_receipt_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
        AND signer_account_id = 'tinykoala595.near'
),
selected_receipts AS (
    SELECT DISTINCT converted_into_receipt_id AS receipt_id
    FROM selected_transactions
    WHERE converted_into_receipt_id IS NOT NULL
        AND TRIM(converted_into_receipt_id) != ''
),
outcome_records AS (
    SELECT
        o.receipt_id,
        o.block_timestamp_utc AS execution_timestamp_utc,
        o.executor_account_id,
        o.status,
        TO_JSON_STRING(o.logs) AS logs_json,
        COUNT(*) OVER (
            PARTITION BY o.receipt_id
        ) AS matching_outcome_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
        AS o
    INNER JOIN selected_receipts AS r
        ON o.receipt_id = r.receipt_id
    WHERE o.block_date BETWEEN DATE '2026-08-24'
                               AND DATE '2026-10-19'
),
failed_receipts AS (
    SELECT
        t.week_start,
        t.transaction_timestamp_utc,
        t.transaction_hash,
        t.signer_account_id,
        t.receiver_account_id,
        o.receipt_id,
        o.execution_timestamp_utc,
        o.executor_account_id,
        o.status,
        o.logs_json,
        o.matching_outcome_rows,
        ROW_NUMBER() OVER (
            PARTITION BY t.week_start
            ORDER BY
                FARM_FINGERPRINT(t.transaction_hash),
                t.transaction_hash
        ) AS sample_rank
    FROM selected_transactions AS t
    INNER JOIN outcome_records AS o
        ON t.converted_into_receipt_id = o.receipt_id
    WHERE o.matching_outcome_rows = 1
        AND o.status = 'FAILURE'
)
SELECT *
FROM failed_receipts
WHERE sample_rank <= 3
ORDER BY week_start, sample_rank;