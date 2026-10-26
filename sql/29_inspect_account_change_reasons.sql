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
    update_reason,
    COUNT(*) AS change_records,
    COUNT(DISTINCT affected_account_id) AS affected_accounts,
    COUNT(DISTINCT block_height) AS distinct_block_heights,
    COUNTIF(
        affected_account_id IS NULL
        OR TRIM(affected_account_id) = ''
    ) AS records_without_account,
    COUNTIF(
        caused_by_transaction_hash IS NOT NULL
        AND TRIM(caused_by_transaction_hash) != ''
    ) AS records_with_transaction_hash,
    COUNTIF(
        caused_by_receipt_id IS NOT NULL
        AND TRIM(caused_by_receipt_id) != ''
    ) AS records_with_receipt_id,
    MIN(block_timestamp_utc) AS first_timestamp_utc,
    MAX(block_timestamp_utc) AS last_timestamp_utc
FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
WHERE block_date = DATE '2026-08-24'
GROUP BY update_reason
ORDER BY change_records DESC, update_reason;