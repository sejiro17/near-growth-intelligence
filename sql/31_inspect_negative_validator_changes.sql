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

WITH selected_accounts AS (
    SELECT DISTINCT affected_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
    WHERE block_date = DATE '2026-08-24'
        AND update_reason = 'validator_accounts_update'
),
account_history AS (
    SELECT
        a.block_date,
        a.block_height,
        a.index_in_block,
        a.affected_account_id,
        a.update_reason,
        CASE
            WHEN a.affected_account_nonstaked_balance IS NOT NULL
                AND a.affected_account_staked_balance IS NOT NULL
                AND NOT IS_NAN(a.affected_account_nonstaked_balance)
                AND NOT IS_INF(a.affected_account_nonstaked_balance)
                AND NOT IS_NAN(a.affected_account_staked_balance)
                AND NOT IS_INF(a.affected_account_staked_balance)
                AND a.affected_account_nonstaked_balance >= 0
                AND a.affected_account_staked_balance >= 0
                THEN
                    a.affected_account_nonstaked_balance / 1e24
                    + a.affected_account_staked_balance / 1e24
        END AS total_balance_near,
        COUNT(*) OVER (
            PARTITION BY
                a.affected_account_id,
                a.block_height,
                a.index_in_block
        ) AS ordering_key_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
        AS a
    INNER JOIN selected_accounts AS s
        ON a.affected_account_id = s.affected_account_id
    WHERE a.block_date BETWEEN DATE '2026-08-23'
                               AND DATE '2026-08-24'
),
with_previous_record AS (
    SELECT
        *,
        LAG(
            STRUCT(
                block_height,
                index_in_block,
                update_reason,
                total_balance_near,
                ordering_key_rows
            )
        ) OVER (
            PARTITION BY affected_account_id
            ORDER BY block_height, index_in_block
        ) AS previous_record
    FROM account_history
),
checked_updates AS (
    SELECT
        *,
        CASE
            WHEN block_height IS NULL
                OR index_in_block IS NULL
                THEN 'MISSING_ORDERING_KEY'
            WHEN ordering_key_rows != 1
                THEN 'DUPLICATE_CURRENT_ORDERING_KEY'
            WHEN previous_record.block_height IS NULL
                THEN 'NO_PREVIOUS_RECORD_IN_LOOKUP'
            WHEN previous_record.index_in_block IS NULL
                THEN 'MISSING_PREVIOUS_ORDERING_KEY'
            WHEN previous_record.ordering_key_rows != 1
                THEN 'DUPLICATE_PREVIOUS_ORDERING_KEY'
            WHEN total_balance_near IS NULL
                OR previous_record.total_balance_near IS NULL
                THEN 'MISSING_OR_INVALID_BALANCE'
            ELSE 'MATCHED_PREVIOUS_RECORD'
        END AS comparison_check
    FROM with_previous_record
    WHERE block_date = DATE '2026-08-24'
        AND update_reason = 'validator_accounts_update'
)
SELECT
    block_height,
    index_in_block,
    affected_account_id,
    comparison_check,
    previous_record.block_height AS previous_block_height,
    previous_record.index_in_block AS previous_index_in_block,
    previous_record.update_reason AS previous_update_reason,
    previous_record.total_balance_near AS previous_total_balance_near,
    total_balance_near AS current_total_balance_near,
    total_balance_near
        - previous_record.total_balance_near
        AS observed_balance_change_near
FROM checked_updates
WHERE comparison_check = 'MATCHED_PREVIOUS_RECORD'
    AND total_balance_near < previous_record.total_balance_near
ORDER BY
    observed_balance_change_near,
    block_height,
    affected_account_id;