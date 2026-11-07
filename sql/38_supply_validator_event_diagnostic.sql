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

/*
One UTC-day observational diagnostic. All table reads use 23 September only.
The opening block is the saved result-28 closing observation for 22 September;
its supply is approximate and its identifier is not independently authenticated.

Account predecessors are restricted to this day. Missing predecessors remain
unavailable; matched available records do not establish complete state history.
The published lakehouse pipeline filters account changes to account_update and
derives index_in_block within each chunk's state_changes array. Cross-chunk
ordering for an account at one height is therefore treated as ambiguous.

Monetary FLOAT values are retained in validator audits. BIGNUMERIC conversion
before arithmetic preserves the converted representation, not protocol accuracy.
No balance delta, spending field or residual is labelled issuance or actual burn.
Block-header burn accounting can refer to previous chunk execution; same-block
spending comparisons alone do not establish that accounting relationship.

Chunk/shard lookups and final joins use unique aggregated keys to avoid row
multiplication. Shard counts describe observed records; expected membership is
unavailable. Incomplete predecessor groups return NULL totals, never partial
sums. Output contains day controls, positive/validator event blocks and block
identifier/chain anomalies. Day controls are computed before that output filter.

Mapping reference (deployment in crypto_near_mainnet_us remains unverified):
https://github.com/near/near-public-lakehouse/blob/4de8e1a6b2a97b21f39b8cf8c050a43eb09f4291/src/lakehouse/notebooks/Silver%20Lake%20Mainnet.sql
*/

WITH block_source AS (
    SELECT
        block_height,
        block_hash,
        prev_block_hash,
        block_timestamp_utc,
        total_supply AS source_total_supply_yocto_float,
        CASE
            WHEN total_supply > 0
                AND NOT IS_NAN(total_supply)
                AND NOT IS_INF(total_supply)
                THEN SAFE_CAST(total_supply AS BIGNUMERIC)
                    / BIGNUMERIC '1000000000000000000000000'
        END AS converted_supply_near
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date = DATE '2026-09-23'
),
block_groups AS (
    SELECT
        block_height,
        block_hash,
        COUNT(*) AS source_block_rows,
        COUNTIF(
            block_timestamp_utc IS NULL
            OR DATE(block_timestamp_utc) != DATE '2026-09-23'
        ) AS invalid_block_timestamps,
        ARRAY_AGG(
            STRUCT(
                prev_block_hash,
                block_timestamp_utc,
                source_total_supply_yocto_float,
                converted_supply_near
            )
            ORDER BY block_timestamp_utc, prev_block_hash
            LIMIT 1
        )[OFFSET(0)] AS observation
    FROM block_source
    GROUP BY block_height, block_hash
),
block_observations AS (
    SELECT
        *,
        SUM(source_block_rows) OVER (
            PARTITION BY block_height
        ) AS rows_at_height,
        FALSE AS saved_baseline
    FROM block_groups

    UNION ALL

    SELECT
        216835291 AS block_height,
        '63L8dv1fwBtQNQDTyqUWwxqWAmW5DoHWDbuaEdrbUAmr' AS block_hash,
        1 AS source_block_rows,
        0 AS invalid_block_timestamps,
        STRUCT(
            CAST(NULL AS STRING) AS prev_block_hash,
            TIMESTAMP '2026-09-22 23:59:59.748372+00' AS block_timestamp_utc,
            CAST(NULL AS FLOAT64) AS source_total_supply_yocto_float,
            BIGNUMERIC '1307054581.149431' AS converted_supply_near
        ) AS observation,
        1 AS rows_at_height,
        TRUE AS saved_baseline
),
block_predecessors AS (
    SELECT
        *,
        LAG(
            STRUCT(
                block_height,
                block_hash,
                rows_at_height,
                invalid_block_timestamps,
                observation,
                saved_baseline
            )
        ) OVER (
            ORDER BY block_height, block_hash
        ) AS previous_block,
        LEAD(block_hash) OVER (
            ORDER BY block_height, block_hash
        ) AS next_observed_block_hash
    FROM block_observations
),
checked_blocks AS (
    SELECT
        *,
        CASE
            WHEN block_height IS NULL
                OR NULLIF(TRIM(block_hash), '') IS NULL
                THEN 'MISSING_BLOCK_IDENTIFIER'
            WHEN rows_at_height != 1
                THEN 'DUPLICATE_CURRENT_HEIGHT'
            WHEN previous_block.block_height IS NULL
                THEN 'NO_PREVIOUS_BLOCK'
            WHEN previous_block.rows_at_height != 1
                THEN 'DUPLICATE_PREVIOUS_HEIGHT'
            WHEN NULLIF(TRIM(previous_block.block_hash), '') IS NULL
                THEN 'INVALID_PREVIOUS_BLOCK_IDENTIFIER'
            WHEN observation.prev_block_hash IS NULL
                OR observation.prev_block_hash != previous_block.block_hash
                THEN 'PREVIOUS_HASH_MISMATCH'
            WHEN observation.converted_supply_near IS NULL
                OR previous_block.observation.converted_supply_near IS NULL
                THEN 'INVALID_SUPPLY'
            WHEN invalid_block_timestamps != 0
                OR previous_block.invalid_block_timestamps != 0
                THEN 'INVALID_BLOCK_TIMESTAMP'
            ELSE 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
        END AS block_comparison_check
    FROM block_predecessors
    WHERE NOT saved_baseline
),
block_movements AS (
    SELECT
        *,
        IF(
            block_comparison_check = 'MATCHED_AVAILABLE_PREVIOUS_BLOCK',
            observation.converted_supply_near
                - previous_block.observation.converted_supply_near,
            NULL
        ) AS observed_supply_change_near
    FROM checked_blocks
),
chunk_groups AS (
    SELECT
        block_height,
        block_hash,
        shard_id,
        chunk_hash,
        COUNT(*) AS rows_per_chunk,
        COUNTIF(shard_id IS NULL OR NULLIF(TRIM(chunk_hash), '') IS NULL)
            AS invalid_chunk_identifiers
    FROM `bigquery-public-data.crypto_near_mainnet_us.chunks`
    WHERE block_date = DATE '2026-09-23'
    GROUP BY block_height, block_hash, shard_id, chunk_hash
),
chunk_lookup AS (
    SELECT
        block_height,
        block_hash,
        chunk_hash,
        SUM(rows_per_chunk) AS chunk_source_rows,
        COUNT(DISTINCT shard_id) AS shard_id_count,
        IF(
            COUNT(*) = 1 AND SUM(rows_per_chunk) = 1
                AND SUM(invalid_chunk_identifiers) = 0,
            MAX(shard_id),
            NULL
        ) AS observed_shard_id
    FROM chunk_groups
    GROUP BY block_height, block_hash, chunk_hash
),
account_raw AS (
    SELECT
        block_height,
        block_hash,
        chunk_hash,
        block_timestamp_utc,
        index_in_block,
        affected_account_id,
        update_reason,
        caused_by_transaction_hash,
        caused_by_receipt_id,
        affected_account_nonstaked_balance AS source_nonstaked_yocto_float,
        affected_account_staked_balance AS source_staked_yocto_float,
        CASE
            WHEN affected_account_nonstaked_balance >= 0
                AND affected_account_staked_balance >= 0
                AND NOT IS_NAN(affected_account_nonstaked_balance)
                AND NOT IS_INF(affected_account_nonstaked_balance)
                AND NOT IS_NAN(affected_account_staked_balance)
                AND NOT IS_INF(affected_account_staked_balance)
                THEN (
                    SAFE_CAST(affected_account_nonstaked_balance AS BIGNUMERIC)
                    + SAFE_CAST(affected_account_staked_balance AS BIGNUMERIC)
                ) / BIGNUMERIC '1000000000000000000000000'
        END AS converted_balance_near,
        COUNT(*) OVER (
            PARTITION BY
                affected_account_id, block_height, block_hash,
                chunk_hash, index_in_block
        ) AS ordering_key_rows,
        COUNT(DISTINCT chunk_hash) OVER (
            PARTITION BY affected_account_id, block_height
        ) AS account_chunks_at_height,
        COUNT(DISTINCT block_hash) OVER (
            PARTITION BY affected_account_id, block_height
        ) AS account_hashes_at_height
    FROM `bigquery-public-data.crypto_near_mainnet_us.account_changes`
    WHERE block_date = DATE '2026-09-23'
),
account_source AS (
    SELECT
        a.*,
        c.observed_shard_id,
        c.chunk_source_rows,
        c.shard_id_count,
        b.block_comparison_check AS account_block_check
    FROM account_raw AS a
    LEFT JOIN chunk_lookup AS c USING (block_height, block_hash, chunk_hash)
    LEFT JOIN block_movements AS b USING (block_height, block_hash)
),
account_predecessors AS (
    SELECT
        *,
        LAG(
            STRUCT(
                block_height,
                block_hash,
                chunk_hash,
                observed_shard_id,
                chunk_source_rows,
                shard_id_count,
                account_block_check,
                block_timestamp_utc,
                index_in_block,
                ordering_key_rows,
                account_chunks_at_height,
                account_hashes_at_height,
                source_nonstaked_yocto_float,
                source_staked_yocto_float,
                converted_balance_near
            )
        ) OVER (
            PARTITION BY affected_account_id
            ORDER BY block_height, block_hash, chunk_hash, index_in_block
        ) AS previous_record
    FROM account_source
),
checked_accounts AS (
    SELECT
        *,
        CASE
            WHEN NULLIF(TRIM(affected_account_id), '') IS NULL
                OR block_height IS NULL
                OR NULLIF(TRIM(block_hash), '') IS NULL
                OR NULLIF(TRIM(chunk_hash), '') IS NULL
                OR index_in_block IS NULL OR index_in_block < 0
                THEN 'INVALID_CURRENT_IDENTIFIER_OR_ORDER'
            WHEN COALESCE(account_block_check, '')
                    != 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
                OR observed_shard_id IS NULL
                OR COALESCE(chunk_source_rows, 0) != 1
                OR COALESCE(shard_id_count, 0) != 1
                THEN 'INVALID_CURRENT_BLOCK_OR_CHUNK_MAPPING'
            WHEN ordering_key_rows != 1
                OR account_chunks_at_height != 1
                OR account_hashes_at_height != 1
                THEN 'AMBIGUOUS_CURRENT_ORDER'
            WHEN block_timestamp_utc IS NULL
                OR DATE(block_timestamp_utc) != DATE '2026-09-23'
                THEN 'INVALID_CURRENT_TIMESTAMP'
            WHEN previous_record.block_height IS NULL
                THEN 'NO_PREVIOUS_RECORD_THIS_DAY'
            WHEN previous_record.index_in_block IS NULL
                OR previous_record.index_in_block < 0
                OR NULLIF(TRIM(previous_record.block_hash), '') IS NULL
                OR NULLIF(TRIM(previous_record.chunk_hash), '') IS NULL
                OR previous_record.ordering_key_rows != 1
                OR previous_record.account_chunks_at_height != 1
                OR previous_record.account_hashes_at_height != 1
                THEN 'INVALID_OR_AMBIGUOUS_PREVIOUS_ORDER'
            WHEN COALESCE(previous_record.account_block_check, '')
                    != 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
                OR previous_record.observed_shard_id IS NULL
                OR COALESCE(previous_record.chunk_source_rows, 0) != 1
                OR COALESCE(previous_record.shard_id_count, 0) != 1
                THEN 'INVALID_PREVIOUS_BLOCK_OR_CHUNK_MAPPING'
            WHEN previous_record.block_timestamp_utc IS NULL
                OR DATE(previous_record.block_timestamp_utc) != DATE '2026-09-23'
                THEN 'INVALID_PREVIOUS_TIMESTAMP'
            WHEN converted_balance_near IS NULL
                OR previous_record.converted_balance_near IS NULL
                THEN 'INVALID_BALANCE'
            ELSE 'MATCHED_AVAILABLE_RECORD_THIS_DAY'
        END AS account_comparison_check
    FROM account_predecessors
),
account_deltas AS (
    SELECT
        *,
        IF(
            account_comparison_check = 'MATCHED_AVAILABLE_RECORD_THIS_DAY',
            converted_balance_near - previous_record.converted_balance_near,
            NULL
        ) AS matched_available_balance_change_near
    FROM checked_accounts
),
account_reason_groups AS (
    SELECT
        block_height,
        block_hash,
        chunk_hash,
        update_reason,
        COUNT(*) AS update_records,
        COUNT(DISTINCT affected_account_id) AS affected_accounts,
        COUNTIF(
            account_comparison_check != 'MATCHED_AVAILABLE_RECORD_THIS_DAY'
        ) AS unmatched_or_invalid_records,
        COUNTIF(
            block_timestamp_utc IS NULL
            OR DATE(block_timestamp_utc) != DATE '2026-09-23'
        ) AS invalid_timestamps,
        COUNTIF(NULLIF(TRIM(caused_by_receipt_id), '') IS NOT NULL)
            AS records_with_receipt_id,
        COUNTIF(NULLIF(TRIM(caused_by_transaction_hash), '') IS NOT NULL)
            AS records_with_transaction_hash,
        IF(
            COUNTIF(
                account_comparison_check != 'MATCHED_AVAILABLE_RECORD_THIS_DAY'
            ) = 0,
            SUM(matched_available_balance_change_near),
            NULL
        ) AS change_if_all_available_predecessors_matched_near
    FROM account_deltas
    GROUP BY block_height, block_hash, chunk_hash, update_reason
),
accounts_by_block AS (
    SELECT
        block_height,
        block_hash,
        SUM(update_records) AS account_change_rows,
        SUM(IF(update_reason = 'validator_accounts_update', update_records, 0))
            AS validator_update_records,
        SUM(IF(
            update_reason = 'validator_accounts_update',
            unmatched_or_invalid_records,
            0
        )) AS unmatched_validator_records,
        IF(
            SUM(IF(update_reason = 'validator_accounts_update', update_records, 0)) > 0
                AND SUM(IF(update_reason = 'validator_accounts_update',
                    unmatched_or_invalid_records, 0)) = 0,
            SUM(IF(update_reason = 'validator_accounts_update',
                change_if_all_available_predecessors_matched_near, NULL)),
            NULL
        ) AS validator_change_if_all_available_predecessors_matched_near,
        ARRAY_AGG(
            STRUCT(
                chunk_hash,
                update_reason,
                update_records,
                affected_accounts,
                unmatched_or_invalid_records,
                invalid_timestamps,
                records_with_receipt_id,
                records_with_transaction_hash,
                change_if_all_available_predecessors_matched_near
            )
            ORDER BY chunk_hash, update_reason
        ) AS changes_by_chunk_and_reason
    FROM account_reason_groups
    GROUP BY block_height, block_hash
),
validator_audits AS (
    SELECT
        block_height,
        block_hash,
        ARRAY_AGG(
            STRUCT(
                chunk_hash,
                observed_shard_id,
                chunk_source_rows,
                shard_id_count,
                affected_account_id,
                index_in_block,
                ordering_key_rows,
                account_chunks_at_height,
                account_comparison_check,
                source_nonstaked_yocto_float,
                source_staked_yocto_float,
                converted_balance_near,
                previous_record,
                matched_available_balance_change_near
            )
            ORDER BY chunk_hash, affected_account_id, index_in_block
        ) AS validator_account_audit
    FROM account_deltas
    WHERE update_reason = 'validator_accounts_update'
    GROUP BY block_height, block_hash
),
chunks_by_block AS (
    SELECT
        block_height,
        block_hash,
        SUM(rows_per_chunk) AS chunk_rows,
        COUNT(DISTINCT shard_id) AS observed_shards,
        COUNT(*) - COUNT(DISTINCT shard_id) AS extra_chunk_keys_at_shard,
        ARRAY_AGG(
            STRUCT(shard_id, chunk_hash, rows_per_chunk, invalid_chunk_identifiers)
            ORDER BY shard_id, chunk_hash
        ) AS observed_chunk_audit
    FROM chunk_groups
    GROUP BY block_height, block_hash
),
all_keys AS (
    SELECT block_height, block_hash FROM block_movements
    UNION DISTINCT
    SELECT block_height, block_hash FROM accounts_by_block
    UNION DISTINCT
    SELECT block_height, block_hash FROM chunks_by_block
    UNION DISTINCT
    SELECT CAST(NULL AS INT64), CAST(NULL AS STRING)
),
event_membership AS (
    SELECT
        k.block_height,
        k.block_hash,
        COALESCE(b.observed_supply_change_near > 0, FALSE) AS positive_movement,
        COALESCE(a.validator_update_records > 0, FALSE) AS validator_updates
    FROM all_keys AS k
    LEFT JOIN block_movements AS b USING (block_height, block_hash)
    LEFT JOIN accounts_by_block AS a USING (block_height, block_hash)
    WHERE k.block_height IS NOT NULL OR k.block_hash IS NOT NULL
),
event_alignment AS (
    SELECT
        COUNTIF(positive_movement) AS observed_positive_supply_keys,
        COUNTIF(validator_updates) AS observed_validator_update_keys,
        COUNTIF(positive_movement AND validator_updates) AS observed_common_keys,
        COUNTIF(positive_movement != validator_updates) AS observed_unmatched_keys,
        IF(
            COUNTIF(positive_movement OR validator_updates) > 0,
            COUNTIF(positive_movement != validator_updates) = 0,
            NULL
        ) AS observed_height_hash_sets_equal,
        ARRAY_AGG(
            IF(
                positive_movement OR validator_updates,
                STRUCT(block_height, block_hash, positive_movement, validator_updates),
                NULL
            ) IGNORE NULLS ORDER BY block_height, block_hash
        ) AS observed_event_keys
    FROM event_membership
),
day_controls AS (
    SELECT
        (SELECT COUNT(*) FROM block_source) AS day_source_block_rows,
        (SELECT COUNT(*) FROM account_source) AS day_source_account_rows,
        (SELECT COUNTIF(
            block_height IS NULL OR NULLIF(TRIM(block_hash), '') IS NULL
        ) FROM account_source) AS day_unjoinable_account_rows,
        (SELECT SUM(rows_per_chunk) FROM chunk_groups) AS day_source_chunk_rows,
        (SELECT SUM(IF(
            block_height IS NULL OR NULLIF(TRIM(block_hash), '') IS NULL,
            rows_per_chunk,
            0
        )) FROM chunk_groups) AS day_unjoinable_chunk_rows,
        (SELECT COUNTIF(
            block_comparison_check != 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
        ) FROM block_movements) AS day_invalid_block_comparisons,
        (SELECT IF(
            COUNT(*) > 0 AND COUNTIF(
                block_comparison_check != 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
            ) = 0,
            SUM(observed_supply_change_near), NULL
        ) FROM block_movements) AS day_supply_change_if_all_comparisons_valid_near,
        (SELECT AS STRUCT
            COUNT(*) AS observed_update_records,
            COUNTIF(account_comparison_check = 'MATCHED_AVAILABLE_RECORD_THIS_DAY')
                AS matched_records,
            COUNTIF(account_comparison_check != 'MATCHED_AVAILABLE_RECORD_THIS_DAY')
                AS unmatched_or_invalid_records,
            COUNTIF(block_height IS NULL OR NULLIF(TRIM(block_hash), '') IS NULL)
                AS unjoinable_records,
            IF(
                COUNT(*) > 0 AND COUNTIF(
                    account_comparison_check != 'MATCHED_AVAILABLE_RECORD_THIS_DAY'
                ) = 0,
                SUM(matched_available_balance_change_near), NULL
            ) AS change_if_all_available_predecessors_matched_near
         FROM account_deltas
         WHERE update_reason = 'validator_accounts_update')
            AS validator_predecessor_coverage
)
SELECT
    DATE '2026-09-23' AS observation_date,
    IF(
        k.block_height IS NULL AND k.block_hash IS NULL,
        'DAY_COVERAGE',
        'BLOCK_DIAGNOSTIC'
    ) AS row_kind,
    k.block_height,
    k.block_hash,
    b.observation.block_timestamp_utc AS block_timestamp_utc,
    b.observation.prev_block_hash AS declared_previous_block_hash,
    b.previous_block.block_height AS previous_observed_block_height,
    b.previous_block.block_hash AS previous_observed_block_hash,
    b.next_observed_block_hash,
    b.previous_block.saved_baseline AS previous_is_saved_baseline,
    b.source_block_rows,
    b.rows_at_height,
    b.invalid_block_timestamps,
    COALESCE(b.block_comparison_check, 'NO_MATCHING_BLOCK_KEY')
        AS block_comparison_check,
    b.observation.source_total_supply_yocto_float,
    b.observation.converted_supply_near,
    b.observed_supply_change_near,
    b.observed_supply_change_near > 0 AS positive_supply_movement,
    COALESCE(a.validator_update_records, 0) AS observed_validator_update_records,
    b.observed_supply_change_near > 0
        AND COALESCE(a.validator_update_records, 0) > 0
        AS positive_movement_with_validator_updates,
    a.unmatched_validator_records,
    a.validator_change_if_all_available_predecessors_matched_near,
    a.account_change_rows,
    a.changes_by_chunk_and_reason,
    v.validator_account_audit,
    c.chunk_rows,
    c.observed_shards AS observed_shard_count,
    CAST(NULL AS INT64) AS independently_expected_shard_count,
    'OBSERVED_RECORDS_ONLY' AS shard_coverage_basis,
    c.extra_chunk_keys_at_shard,
    c.observed_chunk_audit,
    a.account_change_rows IS NOT NULL AND b.block_height IS NULL
        AS account_rows_without_block_key,
    c.chunk_rows IS NOT NULL AND b.block_height IS NULL
        AS chunk_rows_without_block_key,
    d AS day_coverage_controls,
    h AS day_event_alignment,
    IF(
        d.day_source_block_rows > 0 AND d.day_invalid_block_comparisons = 0
            AND d.validator_predecessor_coverage.unjoinable_records = 0,
        h.observed_height_hash_sets_equal,
        NULL
    ) AS observed_event_sets_equal_if_identifiers_valid,
    d.day_supply_change_if_all_comparisons_valid_near
        - d.validator_predecessor_coverage.change_if_all_available_predecessors_matched_near
        AS day_supply_minus_validator_change_if_all_comparisons_available_near,
    CAST(NULL AS BIGNUMERIC) AS independently_measured_issuance_near,
    CAST(NULL AS BIGNUMERIC) AS independently_measured_actual_burn_near
FROM all_keys AS k
LEFT JOIN block_movements AS b USING (block_height, block_hash)
LEFT JOIN accounts_by_block AS a USING (block_height, block_hash)
LEFT JOIN validator_audits AS v USING (block_height, block_hash)
LEFT JOIN chunks_by_block AS c USING (block_height, block_hash)
CROSS JOIN day_controls AS d
CROSS JOIN event_alignment AS h
WHERE (k.block_height IS NULL AND k.block_hash IS NULL)
    OR b.observed_supply_change_near > 0
    OR a.validator_update_records > 0
    OR COALESCE(b.block_comparison_check, '') != 'MATCHED_AVAILABLE_PREVIOUS_BLOCK'
ORDER BY k.block_height, k.block_hash;
