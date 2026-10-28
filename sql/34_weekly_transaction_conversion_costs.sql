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

WITH weekly_checks AS (
    SELECT
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        COUNT(*) AS transactions,
        COUNT(DISTINCT transaction_hash)
            AS distinct_transaction_hashes,
        COUNTIF(
            receipt_conversion_tokens_burnt IS NULL
        ) AS missing_cost_records,
        COUNTIF(
            receipt_conversion_tokens_burnt < 0
        ) AS negative_cost_records,
        COUNTIF(
            IS_NAN(receipt_conversion_tokens_burnt)
            OR IS_INF(receipt_conversion_tokens_burnt)
        ) AS nonfinite_cost_records,
        SUM(
            CASE
                WHEN receipt_conversion_tokens_burnt >= 0
                    AND NOT IS_NAN(
                        receipt_conversion_tokens_burnt
                    )
                    AND NOT IS_INF(
                        receipt_conversion_tokens_burnt
                    )
                THEN receipt_conversion_tokens_burnt / 1e24
            END
        ) AS recorded_conversion_cost_near
    FROM
        `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
    GROUP BY week_start
)
SELECT
    week_start,
    DATE_ADD(
        week_start,
        INTERVAL 6 DAY
    ) AS week_end,
    transactions,
    distinct_transaction_hashes,
    missing_cost_records,
    negative_cost_records,
    nonfinite_cost_records,
    recorded_conversion_cost_near,
    SAFE_DIVIDE(
        recorded_conversion_cost_near,
        transactions
    ) AS recorded_conversion_cost_per_transaction_near
FROM weekly_checks
ORDER BY week_start;