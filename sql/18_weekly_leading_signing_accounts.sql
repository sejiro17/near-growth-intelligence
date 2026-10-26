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

WITH account_weeks AS (
    SELECT
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        signer_account_id,
        COUNT(*) AS transactions,
        COUNT(DISTINCT block_date) AS active_days
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
    GROUP BY week_start, signer_account_id
),
ranked_accounts AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY week_start
            ORDER BY transactions DESC, signer_account_id
        ) AS activity_rank
    FROM account_weeks
),
weekly_totals AS (
    SELECT
        week_start,
        SUM(transactions) AS weekly_transactions,
        COUNT(*) AS weekly_active_signing_accounts,
        SUM(
            IF(activity_rank <= 10, transactions, 0)
        ) AS top_10_accounts_transactions,
        SUM(
            IF(activity_rank > 10, transactions, 0)
        ) AS outside_top_10_transactions
    FROM ranked_accounts
    GROUP BY week_start
),
selected_accounts AS (
    SELECT DISTINCT signer_account_id
    FROM ranked_accounts
    WHERE activity_rank <= 20
),
account_history AS (
    SELECT
        a.signer_account_id,
        SUM(a.transactions) AS full_period_transactions,
        COUNT(*) AS weeks_active,
        COUNTIF(a.activity_rank <= 10) AS weeks_in_top_10,
        COUNTIF(a.activity_rank <= 20) AS weeks_in_top_20
    FROM ranked_accounts AS a
    INNER JOIN selected_accounts AS s
        ON a.signer_account_id = s.signer_account_id
    GROUP BY a.signer_account_id
),
account_week_grid AS (
    SELECT
        w.week_start,
        s.signer_account_id
    FROM weekly_totals AS w
    CROSS JOIN selected_accounts AS s
)
SELECT
    g.week_start,
    DATE_ADD(g.week_start, INTERVAL 6 DAY) AS week_end,
    g.signer_account_id,
    COALESCE(a.transactions, 0) AS transactions,
    COALESCE(a.active_days, 0) AS active_days,
    a.activity_rank,
    COALESCE(a.activity_rank <= 10, FALSE) AS in_weekly_top_10,
    COALESCE(a.activity_rank <= 20, FALSE) AS in_weekly_top_20,
    ROUND(
        100.0 * SAFE_DIVIDE(
            COALESCE(a.transactions, 0),
            w.weekly_transactions
        ),
        4
    ) AS weekly_transaction_share_pct,
    h.full_period_transactions,
    h.weeks_active,
    h.weeks_in_top_10,
    h.weeks_in_top_20,
    w.weekly_transactions,
    w.weekly_active_signing_accounts,
    w.top_10_accounts_transactions,
    w.outside_top_10_transactions
FROM account_week_grid AS g
LEFT JOIN ranked_accounts AS a
    ON g.week_start = a.week_start
    AND g.signer_account_id = a.signer_account_id
INNER JOIN account_history AS h
    ON g.signer_account_id = h.signer_account_id
INNER JOIN weekly_totals AS w
    ON g.week_start = w.week_start
ORDER BY
    h.full_period_transactions DESC,
    g.signer_account_id,
    g.week_start;