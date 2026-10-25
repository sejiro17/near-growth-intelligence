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
        signer_account_id,
        receiver_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-11'
),
account_activity AS (
    SELECT
        signer_account_id,
        COUNTIF(
            block_date BETWEEN DATE '2026-09-28'
                               AND DATE '2026-10-04'
        ) AS starting_week_transactions,
        COUNTIF(
            block_date BETWEEN DATE '2026-10-05'
                               AND DATE '2026-10-11'
        ) AS following_week_transactions
    FROM selected_transactions
    GROUP BY signer_account_id
),
cohort AS (
    SELECT
        signer_account_id,
        starting_week_transactions,
        CASE
            WHEN following_week_transactions > 0
                THEN 'ACTIVE_FOLLOWING_WEEK'
            ELSE 'NOT_ACTIVE_FOLLOWING_WEEK'
        END AS return_group
    FROM account_activity
    WHERE starting_week_transactions > 0
),
group_totals AS (
    SELECT
        return_group,
        COUNT(*) AS group_accounts,
        SUM(starting_week_transactions) AS group_transactions
    FROM cohort
    GROUP BY return_group
),
receiver_activity AS (
    SELECT
        c.return_group,
        t.receiver_account_id,
        COUNT(*) AS transactions,
        COUNT(DISTINCT t.signer_account_id) AS signing_accounts
    FROM selected_transactions AS t
    INNER JOIN cohort AS c
        ON t.signer_account_id = c.signer_account_id
    WHERE t.block_date BETWEEN DATE '2026-09-28'
                               AND DATE '2026-10-04'
    GROUP BY c.return_group, t.receiver_account_id
),
ranked_receivers AS (
    SELECT
        r.*,
        g.group_accounts,
        g.group_transactions,
        ROW_NUMBER() OVER (
            PARTITION BY r.return_group
            ORDER BY r.transactions DESC, r.receiver_account_id
        ) AS receiver_rank,
        COUNT(*) OVER (
            PARTITION BY r.return_group
        ) AS group_distinct_receivers
    FROM receiver_activity AS r
    INNER JOIN group_totals AS g
        ON r.return_group = g.return_group
)
SELECT
    DATE '2026-09-28' AS cohort_week,
    DATE '2026-10-04' AS cohort_week_end,
    DATE '2026-10-05' AS followup_week,
    DATE '2026-10-11' AS followup_week_end,
    return_group,
    group_accounts,
    group_transactions,
    group_distinct_receivers,
    receiver_rank,
    receiver_account_id,
    transactions,
    signing_accounts,
    ROUND(
        100.0 * SAFE_DIVIDE(
            transactions,
            group_transactions
        ),
        2
    ) AS group_transaction_share_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            signing_accounts,
            group_accounts
        ),
        2
    ) AS group_accounts_interacting_with_receiver_pct
FROM ranked_receivers
WHERE receiver_rank <= 20
ORDER BY return_group, receiver_rank;