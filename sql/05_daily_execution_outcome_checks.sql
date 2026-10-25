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

SELECT
    block_date,
    status,
    COUNT(*) AS outcome_rows,
    COUNT(DISTINCT receipt_id) AS distinct_receipt_ids,
    COUNTIF(
        NULLIF(TRIM(receipt_id), '') IS NULL
    ) AS missing_receipt_ids,
    COUNTIF(
        NULLIF(TRIM(executor_account_id), '') IS NULL
    ) AS missing_executor_accounts,
    COUNTIF(
        block_timestamp_utc IS NULL
    ) AS missing_timestamps,
    COUNTIF(
        DATE(block_timestamp_utc) != block_date
    ) AS timestamp_date_mismatches,
    COUNTIF(
        gas_burnt IS NULL
    ) AS missing_gas_values,
    COUNTIF(
        gas_burnt < 0
    ) AS negative_gas_values,
    COUNTIF(
        IS_NAN(gas_burnt) OR IS_INF(gas_burnt)
    ) AS nonfinite_gas_values,
    COUNTIF(
        tokens_burnt IS NULL
    ) AS missing_token_cost_values,
    COUNTIF(
        tokens_burnt < 0
    ) AS negative_token_cost_values,
    COUNTIF(
        IS_NAN(tokens_burnt) OR IS_INF(tokens_burnt)
    ) AS nonfinite_token_cost_values,
    MIN(block_timestamp_utc) AS first_timestamp_utc,
    MAX(block_timestamp_utc) AS last_timestamp_utc
FROM
    `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes`
WHERE block_date BETWEEN DATE '2026-07-01'
                         AND DATE '2026-10-24'
GROUP BY block_date, status
ORDER BY block_date, status;
