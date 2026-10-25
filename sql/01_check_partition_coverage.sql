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

-- Check available daily partitions before choosing the analysis period.
-- Nonempty partitions do not establish that each day is complete.

WITH daily_partitions AS (
    SELECT
        table_name,
        SAFE.PARSE_DATE('%Y%m%d', partition_id) AS partition_date,
        total_rows
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.INFORMATION_SCHEMA.PARTITIONS`
    WHERE table_name IN (
        'transactions',
        'receipt_actions',
        'execution_outcomes',
        'accounts'
    )
        AND REGEXP_CONTAINS(partition_id, r'^[0-9]{8}$')
),
coverage AS (
    SELECT
        table_name,
        MIN(partition_date) AS earliest_nonempty_date,
        MAX(partition_date) AS latest_nonempty_date,
        COUNT(DISTINCT partition_date) AS nonempty_days,
        COUNT(DISTINCT IF(
            partition_date BETWEEN DATE '2026-07-01'
                                   AND DATE '2026-10-24',
            partition_date,
            NULL
        )) AS nonempty_days_in_candidate_window
    FROM daily_partitions
    WHERE total_rows > 0
    GROUP BY table_name
)
SELECT
    *,
    DATE_DIFF(
        DATE '2026-10-24',
        DATE '2026-07-01',
        DAY
    ) + 1 AS expected_days_in_candidate_window
FROM coverage
ORDER BY table_name;