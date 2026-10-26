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
        block_date,
        signer_account_id,
        receiver_account_id
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
account_week_totals AS (
    SELECT
        week_start,
        signer_account_id,
        COUNT(*) AS account_week_transactions,
        COUNT(DISTINCT block_date) AS account_active_days,
        COUNT(DISTINCT receiver_account_id) AS distinct_receivers,
        COUNTIF(
            receiver_account_id = signer_account_id
        ) AS self_directed_transactions,
        COUNTIF(
            receiver_account_id IS NULL
            OR TRIM(receiver_account_id) = ''
        ) AS missing_or_empty_receiver_transactions
    FROM selected_transactions
    GROUP BY week_start, signer_account_id
),
receiver_counts AS (
    SELECT
        week_start,
        signer_account_id,
        receiver_account_id,
        COUNT(*) AS transactions,
        COUNT(DISTINCT block_date) AS receiver_active_days
    FROM selected_transactions
    GROUP BY
        week_start,
        signer_account_id,
        receiver_account_id
),
ranked_receivers AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY week_start, signer_account_id
            ORDER BY transactions DESC, receiver_account_id
        ) AS receiver_rank
    FROM receiver_counts
),
receiver_coverage AS (
    SELECT
        week_start,
        signer_account_id,
        SUM(
            IF(receiver_rank <= 20, transactions, 0)
        ) AS top_20_receiver_transactions,
        SUM(
            IF(receiver_rank > 20, transactions, 0)
        ) AS outside_top_20_receiver_transactions
    FROM ranked_receivers
    GROUP BY week_start, signer_account_id
)
SELECT
    r.week_start,
    DATE_ADD(r.week_start, INTERVAL 6 DAY) AS week_end,
    r.signer_account_id,
    r.receiver_rank,
    r.receiver_account_id,
    r.transactions,
    r.receiver_active_days,
    ROUND(
        100.0 * SAFE_DIVIDE(
            r.transactions,
            a.account_week_transactions
        ),
        4
    ) AS account_transaction_share_pct,
    a.account_week_transactions,
    a.account_active_days,
    a.distinct_receivers,
    a.self_directed_transactions,
    a.missing_or_empty_receiver_transactions,
    c.top_20_receiver_transactions,
    c.outside_top_20_receiver_transactions
FROM ranked_receivers AS r
INNER JOIN account_week_totals AS a
    ON r.week_start = a.week_start
    AND r.signer_account_id = a.signer_account_id
INNER JOIN receiver_coverage AS c
    ON r.week_start = c.week_start
    AND r.signer_account_id = c.signer_account_id
WHERE r.receiver_rank <= 20
ORDER BY
    r.signer_account_id,
    r.week_start,
    r.receiver_rank;


    
