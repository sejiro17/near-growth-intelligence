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

WITH weekly_costs AS (
    SELECT
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        COUNT(DISTINCT block_date) AS observed_days,
        COUNT(*) AS receipt_execution_outcomes,
        COUNTIF(status = 'FAILURE') AS failed_receipt_outcomes,
        COUNTIF(status = 'SUCCESS_VALUE') AS success_value_outcomes,
        COUNTIF(
            status = 'SUCCESS_RECEIPT_ID'
        ) AS success_receipt_id_outcomes,
        COUNTIF(
            status IS NULL
            OR status NOT IN (
                'FAILURE',
                'SUCCESS_VALUE',
                'SUCCESS_RECEIPT_ID'
            )
        ) AS other_or_missing_statuses,
        SUM(gas_burnt) / 1e12 AS recorded_gas_tgas,
        SUM(tokens_burnt) / 1e24 AS recorded_execution_cost_near,
        SUM(
            IF(status = 'FAILURE', tokens_burnt, 0)
        ) / 1e24 AS failed_receipt_cost_near,
        COUNTIF(
            gas_burnt IS NULL
            OR gas_burnt < 0
            OR IS_NAN(gas_burnt)
            OR IS_INF(gas_burnt)
        ) AS invalid_gas_values,
        COUNTIF(
            tokens_burnt IS NULL
            OR tokens_burnt < 0
            OR IS_NAN(tokens_burnt)
            OR IS_INF(tokens_burnt)
        ) AS invalid_token_cost_values
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
    GROUP BY week_start
)
SELECT
    week_start,
    DATE_ADD(week_start, INTERVAL 6 DAY) AS week_end,
    observed_days,
    receipt_execution_outcomes,
    failed_receipt_outcomes,
    success_value_outcomes,
    success_receipt_id_outcomes,
    other_or_missing_statuses,
    recorded_gas_tgas,
    recorded_execution_cost_near,
    failed_receipt_cost_near,
    ROUND(
        100.0 * SAFE_DIVIDE(
            failed_receipt_outcomes,
            receipt_execution_outcomes
        ),
        2
    ) AS failed_receipt_share_pct,
    ROUND(
        100.0 * SAFE_DIVIDE(
            failed_receipt_cost_near,
            recorded_execution_cost_near
        ),
        2
    ) AS failed_receipt_cost_share_pct,
    SAFE_DIVIDE(
        recorded_execution_cost_near,
        receipt_execution_outcomes
    ) AS average_recorded_cost_per_receipt_near,
    invalid_gas_values,
    invalid_token_cost_values
FROM weekly_costs
ORDER BY week_start;