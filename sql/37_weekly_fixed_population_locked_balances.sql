WITH weeks AS (
    SELECT
        week_start,
        DATE_ADD(week_start, INTERVAL 6 DAY) AS observation_date
    FROM UNNEST(GENERATE_DATE_ARRAY(
        DATE '2026-08-24', DATE '2026-10-12', INTERVAL 7 DAY
    )) AS week_start
),
pilot_input AS (
    SELECT account_id
    FROM UNNEST(@pilot_accounts) AS account_id
),
pilot_population AS (
    SELECT DISTINCT account_id
    FROM pilot_input
    WHERE account_id IS NOT NULL AND TRIM(account_id) != ''
),
population_checks AS (
    SELECT
        (SELECT COUNT(*) FROM pilot_input) AS input_accounts,
        COUNT(*) AS fixed_population_accounts,
        TO_HEX(SHA256(STRING_AGG(account_id, '\n' ORDER BY account_id)))
            AS population_sha256
    FROM pilot_population
),
source AS (
    SELECT
        block_date,
        block_height,
        block_timestamp_utc,
        index_in_block,
        affected_account_id,
        affected_account_staked_balance AS source_locked_yocto,
        SAFE_CAST(affected_account_staked_balance AS BIGNUMERIC)
            AS locked_yocto,
        COUNT(*) OVER (
            PARTITION BY
                block_date,
                affected_account_id,
                block_height,
                index_in_block
        ) AS ordering_key_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
    WHERE block_date IN UNNEST(GENERATE_DATE_ARRAY(
        DATE '2026-08-30', DATE '2026-10-18', INTERVAL 7 DAY
    ))
        AND update_reason = 'validator_accounts_update'
),
daily_boundaries AS (
    SELECT
        block_date,
        MAX(block_height) AS observation_height,
        COUNTIF(block_height IS NULL) AS null_height_rows_on_observation_date
    FROM source
    GROUP BY block_date
),
boundaries AS (
    SELECT
        w.week_start,
        w.observation_date,
        d.observation_height,
        COALESCE(d.null_height_rows_on_observation_date, 0)
            AS null_height_rows_on_observation_date
    FROM weeks AS w
    LEFT JOIN daily_boundaries AS d
        ON d.block_date = w.observation_date
),
selected_updates AS (
    SELECT s.*
    FROM source AS s
    INNER JOIN boundaries AS b
        ON s.block_date = b.observation_date
        AND s.block_height = b.observation_height
),
boundary_checks AS (
    SELECT
        b.observation_date,
        MIN(s.block_timestamp_utc) AS first_recorded_timestamp_utc,
        MAX(s.block_timestamp_utc) AS last_recorded_timestamp_utc,
        COUNT(DISTINCT s.block_timestamp_utc) AS distinct_recorded_timestamps,
        COUNTIF(
            s.block_height IS NOT NULL
            AND (
                s.block_timestamp_utc IS NULL
                OR DATE(s.block_timestamp_utc) != b.observation_date
            )
        ) AS invalid_timestamp_rows,
        COUNTIF(
            s.block_height IS NOT NULL
            AND (
                s.affected_account_id IS NULL
                OR TRIM(s.affected_account_id) = ''
            )
        ) AS invalid_account_id_rows
    FROM boundaries AS b
    LEFT JOIN selected_updates AS s
        ON s.block_date = b.observation_date
    GROUP BY b.observation_date
),
account_updates AS (
    SELECT
        block_date AS observation_date,
        affected_account_id AS account_id,
        COUNT(*) AS update_rows,
        COUNTIF(index_in_block IS NULL OR index_in_block < 0)
            AS invalid_index_rows,
        COUNTIF(ordering_key_rows > 1) AS duplicate_key_rows,
        COUNTIF(source_locked_yocto IS NULL) AS missing_balance_rows,
        COUNTIF(source_locked_yocto < 0) AS negative_balance_rows,
        COUNTIF(IS_NAN(source_locked_yocto) OR IS_INF(source_locked_yocto))
            AS nonfinite_balance_rows,
        COUNTIF(locked_yocto IS NULL) AS unconvertible_balance_rows,
        IF(COUNT(*) = 1, MAX(locked_yocto), NULL) AS single_locked_yocto,
        ARRAY_AGG(
            STRUCT(
                index_in_block AS index_in_block,
                block_timestamp_utc AS block_timestamp_utc,
                source_locked_yocto AS source_locked_yocto,
                locked_yocto AS converted_locked_yocto,
                ordering_key_rows AS ordering_key_rows
            )
            ORDER BY index_in_block
        ) AS recorded_updates
    FROM selected_updates
    WHERE affected_account_id IS NOT NULL
        AND TRIM(affected_account_id) != ''
    GROUP BY observation_date, account_id
),
membership AS (
    SELECT
        b.observation_date,
        COUNT(a.account_id) AS observed_update_accounts,
        COUNTIF(a.account_id IS NOT NULL AND p.account_id IS NULL)
            AS additional_observed_accounts,
        ARRAY_AGG(
            IF(a.account_id IS NOT NULL AND p.account_id IS NULL,
                a.account_id, NULL)
            IGNORE NULLS ORDER BY a.account_id
        ) AS additional_account_ids
    FROM boundaries AS b
    LEFT JOIN account_updates AS a
        ON a.observation_date = b.observation_date
    LEFT JOIN pilot_population AS p
        ON p.account_id = a.account_id
    GROUP BY b.observation_date
),
fixed_summary AS (
    SELECT
        b.week_start,
        b.observation_date,
        b.observation_height,
        b.null_height_rows_on_observation_date,
        COUNTIF(a.account_id IS NOT NULL) AS observed_fixed_accounts,
        COUNTIF(p.account_id IS NOT NULL AND a.account_id IS NULL)
            AS missing_fixed_accounts,
        ARRAY_AGG(
            IF(p.account_id IS NOT NULL AND a.account_id IS NULL,
                p.account_id, NULL)
            IGNORE NULLS ORDER BY p.account_id
        ) AS missing_account_ids,
        COUNTIF(a.update_rows > 1) AS fixed_accounts_with_multiple_updates,
        SUM(COALESCE(a.update_rows, 0)) AS fixed_update_rows,
        SUM(COALESCE(a.invalid_index_rows, 0)) AS invalid_fixed_index_rows,
        SUM(COALESCE(a.duplicate_key_rows, 0)) AS duplicate_fixed_key_rows,
        SUM(COALESCE(a.missing_balance_rows, 0)) AS missing_fixed_balance_rows,
        SUM(COALESCE(a.negative_balance_rows, 0)) AS negative_fixed_balance_rows,
        SUM(COALESCE(a.nonfinite_balance_rows, 0)) AS nonfinite_fixed_balance_rows,
        SUM(COALESCE(a.unconvertible_balance_rows, 0))
            AS unconvertible_fixed_balance_rows,
        SUM(a.single_locked_yocto) AS candidate_fixed_locked_yocto,
        ARRAY_AGG(
            STRUCT(
                p.account_id AS account_id,
                IF(a.account_id IS NULL, 'MISSING_AT_SELECTED_HEIGHT', 'OBSERVED')
                    AS observation_status,
                COALESCE(a.update_rows, 0) AS update_rows,
                a.invalid_index_rows AS invalid_index_rows,
                a.duplicate_key_rows AS duplicate_key_rows,
                a.missing_balance_rows AS missing_balance_rows,
                a.negative_balance_rows AS negative_balance_rows,
                a.nonfinite_balance_rows AS nonfinite_balance_rows,
                a.unconvertible_balance_rows AS unconvertible_balance_rows,
                a.recorded_updates AS recorded_updates
            )
            ORDER BY p.account_id
        ) AS fixed_account_audit
    FROM boundaries AS b
    LEFT JOIN pilot_population AS p ON TRUE
    LEFT JOIN account_updates AS a
        ON a.observation_date = b.observation_date
        AND a.account_id = p.account_id
    GROUP BY
        b.week_start,
        b.observation_date,
        b.observation_height,
        b.null_height_rows_on_observation_date
),
checked AS (
    SELECT
        f.*,
        p.input_accounts AS pilot_input_accounts,
        p.fixed_population_accounts,
        p.population_sha256,
        c.first_recorded_timestamp_utc,
        c.last_recorded_timestamp_utc,
        c.distinct_recorded_timestamps,
        c.invalid_timestamp_rows,
        c.invalid_account_id_rows,
        m.observed_update_accounts,
        m.additional_observed_accounts,
        m.additional_account_ids,
        (p.input_accounts = 465 AND p.fixed_population_accounts = 465
            AND p.population_sha256 =
                '40144fbb99d2f921b6f5b6d47d27c3b929664ded71ee740626fc36389050779e'
            AND f.missing_fixed_accounts = 0 AND m.additional_observed_accounts = 0
            AND c.invalid_account_id_rows = 0
            AND f.observation_height IS NOT NULL) AS membership_matches_pilot,
        (
            p.input_accounts = 465
            AND p.fixed_population_accounts = 465
            AND p.population_sha256 =
                '40144fbb99d2f921b6f5b6d47d27c3b929664ded71ee740626fc36389050779e'
            AND f.observation_height IS NOT NULL
            AND f.null_height_rows_on_observation_date = 0
            AND c.distinct_recorded_timestamps = 1
            AND c.invalid_timestamp_rows = 0
            AND c.invalid_account_id_rows = 0
            AND f.observed_fixed_accounts = 465
            AND f.missing_fixed_accounts = 0
            AND f.fixed_update_rows = 465
            AND f.fixed_accounts_with_multiple_updates = 0
            AND f.invalid_fixed_index_rows = 0
            AND f.duplicate_fixed_key_rows = 0
            AND f.missing_fixed_balance_rows = 0
            AND f.negative_fixed_balance_rows = 0
            AND f.nonfinite_fixed_balance_rows = 0
            AND f.unconvertible_fixed_balance_rows = 0
        ) AS fixed_population_checks_pass
    FROM fixed_summary AS f
    CROSS JOIN population_checks AS p
    INNER JOIN boundary_checks AS c USING (observation_date)
    INNER JOIN membership AS m USING (observation_date)
)
SELECT
    * EXCEPT (candidate_fixed_locked_yocto),
    'Protocol-locked balances recorded in observed validator updates.'
        AS measurement_label,
    'Fixed 465-account population from result 40' AS population_label,
    TIMESTAMP_DIFF(
        TIMESTAMP(DATE_ADD(observation_date, INTERVAL 1 DAY)),
        TIMESTAMP(last_recorded_timestamp_utc),
        SECOND
    ) AS seconds_before_next_utc_midnight,
    IF(
        fixed_population_checks_pass,
        candidate_fixed_locked_yocto / BIGNUMERIC '1000000000000000000000000',
        NULL
    ) AS observed_fixed_population_locked_balance_near
FROM checked
ORDER BY week_start;
