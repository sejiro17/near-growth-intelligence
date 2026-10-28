WITH dates AS (
    SELECT observation_date
    FROM UNNEST(GENERATE_DATE_ARRAY(@start_date, @end_date)) AS observation_date
),
activity AS (
    SELECT
        block_date AS observation_date,
        COUNT(*) AS transactions,
        COUNT(DISTINCT transaction_hash) AS distinct_transaction_hashes,
        COUNT(DISTINCT NULLIF(TRIM(signer_account_id), '')) AS signing_accounts,
        COUNTIF(NULLIF(TRIM(transaction_hash), '') IS NULL) AS missing_hashes,
        COUNTIF(NULLIF(TRIM(signer_account_id), '') IS NULL) AS missing_signers,
        COUNTIF(block_timestamp_utc IS NULL) AS missing_timestamps,
        COUNTIF(DATE(block_timestamp_utc) != block_date) AS timestamp_date_mismatches,
        COUNT(DISTINCT TIMESTAMP_TRUNC(block_timestamp_utc, HOUR)) AS observed_hours,
        MIN(block_timestamp_utc) AS first_timestamp_utc,
        MAX(block_timestamp_utc) AS last_timestamp_utc
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN @start_date AND @end_date
    GROUP BY block_date
)
SELECT d.observation_date, a.* EXCEPT (observation_date)
FROM dates AS d
LEFT JOIN activity AS a USING (observation_date)
ORDER BY d.observation_date;
