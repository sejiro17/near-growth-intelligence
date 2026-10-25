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

WITH outcome_ids AS (
    SELECT
        receipt_id,
        COUNT(*) AS outcome_rows,
        COUNT(DISTINCT block_date) AS outcome_dates,
        COUNT(DISTINCT status) AS outcome_statuses
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
    WHERE block_date BETWEEN DATE '2026-07-01'
                             AND DATE '2026-10-24'
    GROUP BY receipt_id
),
receipt_ids AS (
    SELECT
        receipt_id,
        COUNT(*) AS receipt_rows,
        COUNTIF(receipt_kind = 'ACTION') AS action_rows,
        COUNTIF(receipt_kind = 'DATA') AS data_rows
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.receipt_details`
    WHERE block_date BETWEEN DATE '2026-06-30'
                             AND DATE '2026-10-25'
    GROUP BY receipt_id
),
matched AS (
    SELECT
        o.*,
        r.receipt_rows,
        CASE
            WHEN r.receipt_id IS NULL
                THEN 'NO_RECEIPT_MATCH_IN_LOOKUP_WINDOW'
            WHEN r.receipt_rows > 1
                THEN 'MULTIPLE_RECEIPT_ROWS'
            WHEN r.action_rows = 1
                THEN 'ACTION_RECEIPT_MATCH'
            WHEN r.data_rows = 1
                THEN 'DATA_RECEIPT_MATCH'
            ELSE 'OTHER_OR_MISSING_RECEIPT_KIND'
        END AS receipt_match
    FROM outcome_ids AS o
    LEFT JOIN receipt_ids AS r
        ON o.receipt_id = r.receipt_id
)
SELECT
    receipt_match,
    COUNT(*) AS distinct_outcome_identifiers,
    SUM(outcome_rows) AS outcome_rows,
    COUNTIF(outcome_rows > 1) AS repeated_outcome_identifiers,
    SUM(outcome_rows - 1) AS rows_above_unique_identifier_count,
    COUNTIF(outcome_dates > 1) AS identifiers_on_multiple_dates,
    COUNTIF(outcome_statuses > 1) AS identifiers_with_multiple_statuses
FROM matched
GROUP BY receipt_match
ORDER BY receipt_match;