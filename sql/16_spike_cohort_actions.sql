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
        signer_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-11'
),
account_activity AS (
    SELECT
        signer_account_id,
        COUNTIF(
            block_date <= DATE '2026-10-04'
        ) AS starting_week_transactions,
        COUNTIF(
            block_date >= DATE '2026-10-05'
        ) AS following_week_transactions
    FROM selected_transactions
    GROUP BY signer_account_id
),
cohort_transactions AS (
    SELECT
        t.transaction_hash,
        t.signer_account_id,
        CASE
            WHEN a.following_week_transactions > 0
                THEN 'ACTIVE_FOLLOWING_WEEK'
            ELSE 'NOT_ACTIVE_FOLLOWING_WEEK'
        END AS return_group
    FROM selected_transactions AS t
    INNER JOIN account_activity AS a
        ON t.signer_account_id = a.signer_account_id
    WHERE t.block_date BETWEEN DATE '2026-09-28'
                               AND DATE '2026-10-04'
),
group_totals AS (
    SELECT
        return_group,
        COUNT(*) AS group_transactions,
        COUNT(DISTINCT signer_account_id) AS group_accounts
    FROM cohort_transactions
    GROUP BY return_group
),
actions_by_transaction_kind AS (
    SELECT
        transaction_hash,
        action_kind,
        COUNT(*) AS action_rows,
        COUNTIF(
            index_in_transaction IS NULL
        ) AS missing_action_indices,
        COUNT(index_in_transaction)
            - COUNT(DISTINCT index_in_transaction)
            AS duplicate_action_indices_within_kind
    FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
    WHERE block_date BETWEEN DATE '2026-09-28'
                             AND DATE '2026-10-04'
    GROUP BY transaction_hash, action_kind
),
action_summary AS (
    SELECT
        t.return_group,
        CASE
            WHEN a.transaction_hash IS NULL
                THEN 'NO_MATCHING_ACTION_RECORD'
            WHEN NULLIF(TRIM(a.action_kind), '') IS NULL
                THEN 'MISSING_ACTION_KIND'
            ELSE a.action_kind
        END AS action_kind,
        COUNT(*) AS transactions_containing_action_kind,
        COUNT(DISTINCT t.signer_account_id) AS signing_accounts,
        SUM(COALESCE(a.action_rows, 0)) AS action_rows,
        SUM(
            COALESCE(a.missing_action_indices, 0)
        ) AS missing_action_indices,
        SUM(
            COALESCE(a.duplicate_action_indices_within_kind, 0)
        ) AS duplicate_action_indices_within_kind
    FROM cohort_transactions AS t
    LEFT JOIN actions_by_transaction_kind AS a
        ON t.transaction_hash = a.transaction_hash
    GROUP BY t.return_group, action_kind
)
SELECT
    DATE '2026-09-28' AS cohort_week,
    DATE '2026-10-04' AS cohort_week_end,
    DATE '2026-10-05' AS followup_week,
    DATE '2026-10-11' AS followup_week_end,
    s.return_group,
    g.group_accounts,
    g.group_transactions,
    s.action_kind,
    s.action_rows,
    s.transactions_containing_action_kind,
    s.signing_accounts,
    ROUND(
        100.0 * SAFE_DIVIDE(
            s.transactions_containing_action_kind,
            g.group_transactions
        ),
        2
    ) AS group_transactions_containing_kind_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            s.signing_accounts,
            g.group_accounts
        ),
        2
    ) AS group_accounts_using_kind_pct,
    s.missing_action_indices,
    s.duplicate_action_indices_within_kind
FROM action_summary AS s
INNER JOIN group_totals AS g
    ON s.return_group = g.return_group
ORDER BY s.return_group, s.action_rows DESC, s.action_kind;