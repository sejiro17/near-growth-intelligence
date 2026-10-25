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

WITH unmatched_outcomes AS (
    SELECT
        o.block_date,
        o.receipt_id,
        o.status,
        o.executor_account_id
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    WHERE o.block_date BETWEEN DATE '2026-07-01'
                               AND DATE '2026-10-24'
        AND NOT EXISTS (
            SELECT 1
            FROM
                `bigquery-public-data.crypto_near_mainnet_us.receipt_details` AS r
            WHERE r.block_date BETWEEN DATE '2026-06-30'
                                       AND DATE '2026-10-25'
                AND r.receipt_id = o.receipt_id
        )
),
transaction_ids AS (
    SELECT DISTINCT
        transaction_hash
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-06-30'
                             AND DATE '2026-10-25'
),
classified AS (
    SELECT
        o.*,
        CASE
            WHEN t.transaction_hash IS NOT NULL
                THEN 'TRANSACTION_HASH_MATCH'
            ELSE 'NO_TRANSACTION_HASH_MATCH'
        END AS identifier_match
    FROM unmatched_outcomes AS o
    LEFT JOIN transaction_ids AS t
        ON o.receipt_id = t.transaction_hash
)
SELECT
    block_date,
    status,
    identifier_match,
    COUNT(*) AS outcome_rows,
    COUNT(DISTINCT executor_account_id) AS distinct_executor_accounts,
    STRING_AGG(
        DISTINCT executor_account_id,
        ', ' ORDER BY executor_account_id LIMIT 3
    ) AS sample_executor_accounts,
    STRING_AGG(
        receipt_id,
        ', ' ORDER BY receipt_id LIMIT 3
    ) AS sample_outcome_identifiers
FROM classified
GROUP BY block_date, status, identifier_match
ORDER BY block_date, status, identifier_match;