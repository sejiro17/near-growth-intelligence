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
    WHERE block_date BETWEEN DATE '2026-07-06'
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
weekly_summary AS (
    SELECT
        week_start,
        COUNT(*) AS weekly_active_signing_accounts,
        SUM(transactions) AS transactions,
        SUM(active_days) AS signing_account_days,
        COUNTIF(active_days = 1) AS accounts_active_one_day,
        COUNTIF(active_days = 7) AS accounts_active_all_seven_days,
        SUM(
            IF(activity_rank = 1, transactions, 0)
        ) AS top_1_account_transactions,
        SUM(
            IF(activity_rank <= 10, transactions, 0)
        ) AS top_10_accounts_transactions,
        SUM(
            IF(activity_rank <= 100, transactions, 0)
        ) AS top_100_accounts_transactions
    FROM ranked_accounts
    GROUP BY week_start
),
with_previous_week AS (
    SELECT
        *,
        LAG(weekly_active_signing_accounts) OVER (
            ORDER BY week_start
        ) AS previous_week_active_accounts
    FROM weekly_summary
)
SELECT
    week_start,
    DATE_ADD(week_start, INTERVAL 6 DAY) AS week_end,
    weekly_active_signing_accounts,
    transactions,
    signing_account_days,
    accounts_active_one_day,
    accounts_active_all_seven_days,
    ROUND(
        SAFE_DIVIDE(
            transactions,
            weekly_active_signing_accounts
        ),
        2
    ) AS transactions_per_weekly_active_account,
    ROUND(
        SAFE_DIVIDE(
            signing_account_days,
            weekly_active_signing_accounts
        ),
        2
    ) AS average_active_days_per_account,
    top_1_account_transactions,
    top_10_accounts_transactions,
    top_100_accounts_transactions,
    ROUND(
        100.0 * SAFE_DIVIDE(
            top_1_account_transactions,
            transactions
        ),
        2
    ) AS top_1_account_transaction_share_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            top_10_accounts_transactions,
            transactions
        ),
        2
    ) AS top_10_accounts_transaction_share_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            top_100_accounts_transactions,
            transactions
        ),
        2
    ) AS top_100_accounts_transaction_share_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            weekly_active_signing_accounts
                - previous_week_active_accounts,
            previous_week_active_accounts
        ),
        2
    ) AS weekly_active_accounts_change_pct
FROM with_previous_week
ORDER BY week_start;