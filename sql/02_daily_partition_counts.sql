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

WITH dates AS (
    SELECT block_date
    FROM UNNEST(
        GENERATE_DATE_ARRAY(
            DATE '2026-07-01',
            DATE '2026-10-24'
        )
    ) AS block_date
),
partition_counts AS (
    SELECT
        table_name,
        SAFE.PARSE_DATE('%Y%m%d', partition_id) AS block_date,
        SUM(total_rows) AS recorded_rows
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.INFORMATION_SCHEMA.PARTITIONS`
    WHERE table_name IN (
        'transactions',
        'receipt_actions',
        'execution_outcomes'
    )
        AND REGEXP_CONTAINS(partition_id, r'^[0-9]{8}$')
    GROUP BY table_name, block_date
)
SELECT
    d.block_date,
    MAX(IF(
        p.table_name = 'transactions',
        p.recorded_rows,
        NULL
    )) AS transaction_rows,
    MAX(IF(
        p.table_name = 'receipt_actions',
        p.recorded_rows,
        NULL
    )) AS receipt_action_rows,
    MAX(IF(
        p.table_name = 'execution_outcomes',
        p.recorded_rows,
        NULL
    )) AS execution_outcome_rows
FROM dates AS d
LEFT JOIN partition_counts AS p
    ON d.block_date = p.block_date
GROUP BY d.block_date
ORDER BY d.block_date;