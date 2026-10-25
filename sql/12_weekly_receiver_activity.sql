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

WITH receiver_weeks AS (
    SELECT
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        receiver_account_id,
        COUNT(*) AS transactions,
        COUNT(DISTINCT signer_account_id) AS signing_accounts,
        COUNT(DISTINCT block_date) AS active_days
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
    GROUP BY week_start, receiver_account_id
),
ranked_receivers AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY week_start
            ORDER BY transactions DESC, receiver_account_id
        ) AS receiver_rank,
        SUM(transactions) OVER (
            PARTITION BY week_start
        ) AS weekly_transactions,
        COUNT(*) OVER (
            PARTITION BY week_start
        ) AS weekly_distinct_receivers
    FROM receiver_weeks
),
with_concentration AS (
    SELECT
        *,
        SUM(
            IF(receiver_rank <= 10, transactions, 0)
        ) OVER (
            PARTITION BY week_start
        ) AS top_10_receiver_transactions,
        SUM(
            IF(receiver_rank <= 20, transactions, 0)
        ) OVER (
            PARTITION BY week_start
        ) AS top_20_receiver_transactions
    FROM ranked_receivers
)
SELECT
    week_start,
    DATE_ADD(week_start, INTERVAL 6 DAY) AS week_end,
    receiver_rank,
    receiver_account_id,
    transactions,
    signing_accounts,
    active_days,
    ROUND(
        100.0 * SAFE_DIVIDE(
            transactions,
            weekly_transactions
        ),
        2
    ) AS weekly_transaction_share_pct,
    weekly_transactions,
    weekly_distinct_receivers,
    top_10_receiver_transactions,
    ROUND(
        100.0 * SAFE_DIVIDE(
            top_10_receiver_transactions,
            weekly_transactions
        ),
        2
    ) AS top_10_receiver_transaction_share_pct,
    top_20_receiver_transactions,
    ROUND(
        100.0 * SAFE_DIVIDE(
            top_20_receiver_transactions,
            weekly_transactions
        ),
        2
    ) AS top_20_receiver_transaction_share_pct
FROM with_concentration
WHERE receiver_rank <= 20
ORDER BY week_start, receiver_rank;