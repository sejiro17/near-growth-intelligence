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

WITH transaction_ids AS (
    SELECT
        transaction_hash,
        COUNT(*) AS matching_transaction_rows
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-10-14'
                             AND DATE '2026-10-16'
    GROUP BY transaction_hash
),
receipt_ids AS (
    SELECT
        receipt_id,
        COUNT(*) AS matching_receipt_rows,
        COUNTIF(receipt_kind = 'ACTION') AS action_receipt_rows,
        COUNTIF(receipt_kind = 'DATA') AS data_receipt_rows
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.receipt_details`
    WHERE block_date BETWEEN DATE '2026-10-14'
                             AND DATE '2026-10-16'
    GROUP BY receipt_id
),
classified_outcomes AS (
    SELECT
        o.receipt_id,
        o.status,
        t.matching_transaction_rows,
        r.matching_receipt_rows,
        CASE
            WHEN t.matching_transaction_rows IS NOT NULL
                AND r.matching_receipt_rows IS NOT NULL
                THEN 'MATCHES_BOTH'
            WHEN t.matching_transaction_rows IS NOT NULL
                THEN 'TRANSACTION_HASH_MATCH'
            WHEN r.matching_receipt_rows = 1
                AND r.action_receipt_rows = 1
                THEN 'ACTION_RECEIPT_MATCH'
            WHEN r.matching_receipt_rows = 1
                AND r.data_receipt_rows = 1
                THEN 'DATA_RECEIPT_MATCH'
            WHEN r.matching_receipt_rows IS NOT NULL
                THEN 'OTHER_OR_MULTIPLE_RECEIPT_ROWS'
            ELSE 'NO_MATCH_IN_LOOKUP_WINDOW'
        END AS identifier_match
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    LEFT JOIN transaction_ids AS t
        ON o.receipt_id = t.transaction_hash
    LEFT JOIN receipt_ids AS r
        ON o.receipt_id = r.receipt_id
    WHERE o.block_date = DATE '2026-10-15'
)
SELECT
    identifier_match,
    status,
    COUNT(*) AS outcome_rows,
    COUNT(DISTINCT receipt_id) AS distinct_outcome_identifiers,
    COUNTIF(
        matching_transaction_rows > 1
    ) AS outcomes_with_multiple_transaction_rows,
    COUNTIF(
        matching_receipt_rows > 1
    ) AS outcomes_with_multiple_receipt_rows
FROM classified_outcomes
GROUP BY identifier_match, status
ORDER BY identifier_match, status;