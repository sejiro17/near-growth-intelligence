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

WITH boundaries AS (
    SELECT block_height
    FROM UNNEST([
        212644334,
        212687534,
        212730734,
        212773934
    ]) AS block_height
),
source AS (
    SELECT
        block_height,
        index_in_block,
        affected_account_id,
        affected_account_staked_balance AS source_locked_yocto,
        SAFE_CAST(
            affected_account_staked_balance AS BIGNUMERIC
        ) AS locked_yocto,
        COUNT(*) OVER (
            PARTITION BY
                affected_account_id,
                block_height,
                index_in_block
        ) AS ordering_key_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
    WHERE block_date = DATE '2026-08-24'
        AND block_height IN (
            212644334,
            212687534,
            212730734,
            212773934
        )
        AND update_reason = 'validator_accounts_update'
),
source_checks AS (
    SELECT
        COUNTIF(
            affected_account_id IS NULL
            OR TRIM(affected_account_id) = ''
        ) AS invalid_account_id_rows
    FROM source
),
population AS (
    SELECT DISTINCT affected_account_id
    FROM source
    WHERE affected_account_id IS NOT NULL
        AND TRIM(affected_account_id) != ''
),
account_updates AS (
    SELECT
        affected_account_id,
        block_height,
        COUNT(*) AS update_rows,
        COUNTIF(
            index_in_block IS NULL OR index_in_block < 0
        ) AS invalid_index_rows,
        COUNTIF(ordering_key_rows > 1) AS duplicate_key_rows,
        COUNTIF(source_locked_yocto IS NULL) AS missing_balance_rows,
        COUNTIF(source_locked_yocto < 0) AS negative_balance_rows,
        COUNTIF(
            IS_NAN(source_locked_yocto) OR IS_INF(source_locked_yocto)
        ) AS nonfinite_balance_rows,
        COUNTIF(locked_yocto IS NULL) AS unconvertible_balance_rows,
        IF(COUNT(*) = 1, MAX(locked_yocto), NULL) AS single_locked_yocto,
        ARRAY_AGG(
            STRUCT(
                index_in_block AS index_in_block,
                source_locked_yocto AS source_locked_yocto,
                locked_yocto AS converted_locked_yocto,
                ordering_key_rows AS ordering_key_rows
            )
            ORDER BY index_in_block
        ) AS recorded_updates
    FROM source
    WHERE affected_account_id IN (
        SELECT affected_account_id FROM population
    )
    GROUP BY affected_account_id, block_height
),
boundary_summary AS (
    SELECT
        b.block_height,
        COUNT(p.affected_account_id) AS population_accounts,
        COUNTIF(a.affected_account_id IS NOT NULL) AS observed_accounts,
        COUNTIF(
            p.affected_account_id IS NOT NULL
            AND COALESCE(a.update_rows, 0) = 0
        ) AS missing_population_accounts,
        COUNTIF(a.update_rows > 1) AS accounts_with_multiple_updates,
        SUM(COALESCE(a.update_rows, 0)) AS update_rows,
        SUM(COALESCE(a.invalid_index_rows, 0)) AS invalid_index_rows,
        SUM(COALESCE(a.duplicate_key_rows, 0)) AS duplicate_key_rows,
        SUM(COALESCE(a.missing_balance_rows, 0)) AS missing_balance_rows,
        SUM(COALESCE(a.negative_balance_rows, 0)) AS negative_balance_rows,
        SUM(COALESCE(a.nonfinite_balance_rows, 0)) AS nonfinite_balance_rows,
        SUM(COALESCE(a.unconvertible_balance_rows, 0))
            AS unconvertible_balance_rows,
        SUM(a.single_locked_yocto) AS candidate_locked_yocto,
        ARRAY_AGG(
            STRUCT(
                p.affected_account_id AS account_id,
                COALESCE(a.update_rows, 0) AS update_rows,
                a.invalid_index_rows AS invalid_index_rows,
                a.duplicate_key_rows AS duplicate_key_rows,
                a.missing_balance_rows AS missing_balance_rows,
                a.negative_balance_rows AS negative_balance_rows,
                a.nonfinite_balance_rows AS nonfinite_balance_rows,
                a.unconvertible_balance_rows AS unconvertible_balance_rows,
                a.recorded_updates AS recorded_updates
            )
            ORDER BY p.affected_account_id
        ) AS account_audit
    FROM boundaries AS b
    LEFT JOIN population AS p ON TRUE
    LEFT JOIN account_updates AS a
        ON a.block_height = b.block_height
        AND a.affected_account_id = p.affected_account_id
    GROUP BY b.block_height
),
checked AS (
    SELECT
        s.*,
        c.invalid_account_id_rows,
        (
            c.invalid_account_id_rows = 0
            AND s.population_accounts = 465
            AND s.observed_accounts = 465
            AND s.update_rows = 465
            AND s.missing_population_accounts = 0
            AND s.accounts_with_multiple_updates = 0
            AND s.invalid_index_rows = 0
            AND s.duplicate_key_rows = 0
            AND s.missing_balance_rows = 0
            AND s.negative_balance_rows = 0
            AND s.nonfinite_balance_rows = 0
            AND s.unconvertible_balance_rows = 0
        ) AS structural_checks_pass
    FROM boundary_summary AS s
    CROSS JOIN source_checks AS c
)
SELECT
    DATE '2026-08-24' AS observation_date,
    block_height,
    'Protocol-locked balances recorded in observed validator updates.'
        AS measurement_label,
    population_accounts,
    observed_accounts,
    update_rows,
    missing_population_accounts,
    accounts_with_multiple_updates,
    invalid_index_rows,
    duplicate_key_rows,
    invalid_account_id_rows,
    missing_balance_rows,
    negative_balance_rows,
    nonfinite_balance_rows,
    unconvertible_balance_rows,
    structural_checks_pass,
    IF(
        structural_checks_pass,
        candidate_locked_yocto / BIGNUMERIC '1000000000000000000000000',
        NULL
    ) AS observed_validator_update_locked_balance_near,
    account_audit
FROM checked
ORDER BY block_height;
