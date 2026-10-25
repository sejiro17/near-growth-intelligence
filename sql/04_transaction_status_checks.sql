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
        status
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-07-01'
                             AND DATE '2026-10-24'
),
window_checks AS (
    SELECT
        COUNT(*) AS window_transaction_rows,
        COUNT(DISTINCT transaction_hash)
            AS window_distinct_transaction_hashes
    FROM selected_transactions
),
daily_status_counts AS (
    SELECT
        block_date,
        status,
        COUNT(*) AS transaction_rows
    FROM selected_transactions
    GROUP BY block_date, status
)
SELECT
    d.block_date,
    d.status,
    d.transaction_rows,
    w.window_transaction_rows,
    w.window_distinct_transaction_hashes,
    w.window_transaction_rows
        - w.window_distinct_transaction_hashes
        AS rows_above_distinct_hash_count
FROM daily_status_counts AS d
CROSS JOIN window_checks AS w
ORDER BY d.block_date, d.status;