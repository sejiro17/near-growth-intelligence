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

WITH source_blocks AS (
    SELECT
        block_date,
        block_height,
        block_hash,
        prev_block_hash,
        CASE
            WHEN total_supply IS NOT NULL
                AND NOT IS_NAN(total_supply)
                AND NOT IS_INF(total_supply)
                AND total_supply > 0
                THEN total_supply / 1e24
        END AS total_supply_near,
        COUNT(*) OVER (
            PARTITION BY block_height
        ) AS rows_at_height
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date BETWEEN DATE '2026-08-23'
                             AND DATE '2026-10-18'
),
with_previous_block AS (
    SELECT
        *,
        LAG(
            STRUCT(
                block_height,
                block_hash,
                total_supply_near,
                rows_at_height
            )
        ) OVER (
            ORDER BY block_height, block_hash
        ) AS previous_block
    FROM source_blocks
),
checked_blocks AS (
    SELECT
        *,
        CASE
            WHEN block_height IS NULL
                OR block_hash IS NULL
                OR TRIM(block_hash) = ''
                THEN 'MISSING_BLOCK_IDENTIFIER'
            WHEN rows_at_height != 1
                THEN 'DUPLICATE_CURRENT_HEIGHT'
            WHEN previous_block.block_height IS NULL
                THEN 'NO_PREVIOUS_BLOCK'
            WHEN previous_block.rows_at_height != 1
                THEN 'DUPLICATE_PREVIOUS_HEIGHT'
            WHEN prev_block_hash IS NULL
                OR prev_block_hash != previous_block.block_hash
                THEN 'PREVIOUS_HASH_MISMATCH'
            WHEN total_supply_near IS NULL
                OR previous_block.total_supply_near IS NULL
                THEN 'MISSING_OR_INVALID_SUPPLY'
            ELSE 'MATCHED_PREVIOUS_BLOCK'
        END AS comparison_check
    FROM with_previous_block
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
),
supply_movements AS (
    SELECT
        *,
        CASE
            WHEN comparison_check = 'MATCHED_PREVIOUS_BLOCK'
                THEN total_supply_near
                    - previous_block.total_supply_near
        END AS observed_supply_change_near
    FROM checked_blocks
)
SELECT
    block_date,
    comparison_check,
    COUNT(*) AS block_records,
    COUNTIF(
        observed_supply_change_near > 0
    ) AS blocks_with_supply_increase,
    COUNTIF(
        observed_supply_change_near < 0
    ) AS blocks_with_supply_decrease,
    COUNTIF(
        observed_supply_change_near = 0
    ) AS blocks_with_unchanged_supply,
    SUM(
        observed_supply_change_near
    ) AS net_observed_supply_change_near,
    SUM(
        CASE
            WHEN observed_supply_change_near > 0
                THEN observed_supply_change_near
            WHEN observed_supply_change_near IS NOT NULL
                THEN 0
        END
    ) AS observed_positive_supply_movements_near,
    SUM(
        CASE
            WHEN observed_supply_change_near < 0
                THEN -observed_supply_change_near
            WHEN observed_supply_change_near IS NOT NULL
                THEN 0
        END
    ) AS observed_supply_decrease_magnitude_near,
    MIN(
        observed_supply_change_near
    ) AS minimum_block_supply_change_near,
    MAX(
        observed_supply_change_near
    ) AS maximum_block_supply_change_near
FROM supply_movements
GROUP BY block_date, comparison_check
ORDER BY block_date, comparison_check;


