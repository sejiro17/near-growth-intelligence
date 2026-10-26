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

WITH calendar AS (
    SELECT block_date
    FROM UNNEST(
        GENERATE_DATE_ARRAY(
            DATE '2026-08-23',
            DATE '2026-10-18'
        )
    ) AS block_date
),
source_blocks AS (
    SELECT
        block_date,
        block_height,
        block_hash,
        block_timestamp_utc,
        total_supply,
        CASE
            WHEN total_supply IS NOT NULL
                AND NOT IS_NAN(total_supply)
                AND NOT IS_INF(total_supply)
                AND total_supply > 0
                THEN total_supply / 1e24
        END AS total_supply_near
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date BETWEEN DATE '2026-08-23'
                             AND DATE '2026-10-18'
),
daily_checks AS (
    SELECT
        block_date,
        COUNT(*) AS block_rows,
        COUNT(DISTINCT block_height) AS distinct_block_heights,
        COUNT(DISTINCT block_hash) AS distinct_block_hashes,
        COUNTIF(block_height IS NULL) AS missing_block_heights,
        COUNTIF(
            block_hash IS NULL
            OR TRIM(block_hash) = ''
        ) AS missing_block_hashes,
        COUNTIF(block_timestamp_utc IS NULL) AS missing_timestamps,
        COUNTIF(
            DATE(block_timestamp_utc) != block_date
        ) AS timestamp_date_mismatches,
        COUNTIF(
            total_supply_near IS NULL
        ) AS missing_or_invalid_supply_values,
        MIN(block_height) AS first_block_height,
        MAX(block_height) AS last_block_height,
        MIN(block_timestamp_utc) AS first_timestamp_utc,
        MAX(block_timestamp_utc) AS last_timestamp_utc,
        ARRAY_AGG(
            STRUCT(
                block_height,
                block_hash,
                block_timestamp_utc,
                total_supply_near
            )
            ORDER BY
                block_height DESC,
                block_timestamp_utc DESC,
                block_hash DESC
            LIMIT 1
        )[OFFSET(0)] AS closing_block
    FROM source_blocks
    GROUP BY block_date
),
daily_supply AS (
    SELECT
        c.block_date,
        COALESCE(d.block_rows, 0) AS block_rows,
        d.distinct_block_heights,
        d.distinct_block_hashes,
        d.missing_block_heights,
        d.missing_block_hashes,
        d.missing_timestamps,
        d.timestamp_date_mismatches,
        d.missing_or_invalid_supply_values,
        d.first_block_height,
        d.last_block_height,
        d.first_timestamp_utc,
        d.last_timestamp_utc,
        d.closing_block.block_height AS closing_block_height,
        d.closing_block.block_hash AS closing_block_hash,
        d.closing_block.block_timestamp_utc
            AS closing_block_timestamp_utc,
        d.closing_block.total_supply_near
            AS closing_total_supply_near
    FROM calendar AS c
    LEFT JOIN daily_checks AS d
        ON c.block_date = d.block_date
),
with_previous_day AS (
    SELECT
        *,
        LAG(closing_total_supply_near) OVER (
            ORDER BY block_date
        ) AS previous_day_closing_supply_near
    FROM daily_supply
)
SELECT
    *,
    closing_total_supply_near
        - previous_day_closing_supply_near
        AS observed_daily_supply_change_near,
    100.0 * SAFE_DIVIDE(
        closing_total_supply_near
            - previous_day_closing_supply_near,
        previous_day_closing_supply_near
    ) AS observed_daily_supply_change_pct
FROM with_previous_day
ORDER BY block_date;