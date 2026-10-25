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
    COUNT(*) AS transaction_rows,
    COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
    COUNTIF(
        NULLIF(TRIM(transaction_hash), '') IS NULL
    ) AS missing_transaction_hashes,
    COUNTIF(
        NULLIF(TRIM(signer_account_id), '') IS NULL
    ) AS missing_signer_accounts,
    COUNTIF(
        NULLIF(TRIM(receiver_account_id), '') IS NULL
    ) AS missing_receiver_accounts,
    COUNTIF(
        block_timestamp_utc IS NULL
    ) AS missing_timestamps,
    COUNTIF(
        DATE(block_timestamp_utc) != block_date
    ) AS timestamp_date_mismatches,
    MIN(block_timestamp_utc) AS first_timestamp_utc,
    MAX(block_timestamp_utc) AS last_timestamp_utc,
    COUNT(DISTINCT
        TIMESTAMP_TRUNC(block_timestamp_utc, HOUR)
    ) AS observed_hours,
    COUNT(DISTINCT
        NULLIF(TRIM(signer_account_id), '')
    ) AS active_signing_accounts,
    COUNT(DISTINCT
        NULLIF(TRIM(receiver_account_id), '')
    ) AS distinct_receiving_accounts
FROM
    `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date BETWEEN DATE '2026-07-01'
                         AND DATE '2026-10-24'
GROUP BY block_date
ORDER BY block_date;
