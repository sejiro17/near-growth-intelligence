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
One-day native TRANSFER discovery, not a revenue ledger. Every source read is
restricted directly to the 23 September 2026 partition. Missing same-day links
remain unresolved: descendant receipts and boundary crossings are not searched.
Native-only coverage excludes fungible tokens and internal Verifier balances.

Repository evidence: SQL 01/02 and results 01/02 establish receipt_actions
partition availability. SQL 05-08 establish receipt/outcome fields and matching;
SQL 17/24/25/27 establish transactions.converted_into_receipt_id as the INITIAL
receipt link. No existing working SQL verifies a receipt_origin table name.
The transactions lookup below is explicitly initial-receipt-only, not a complete
receipt-to-origin lookup. Blocks/identifiers are established by SQL 28/38.

No saved receipt-action schema or raw TRANSFER args example establishes the
remaining column names or amount encoding. Optional fields are inspected through
row JSON rather than asserted as typed schema columns. Missing selector fields
make selection unavailable/partial, not a verified zero. Raw args are retained;
all monetary amounts remain NULL until their receipt-action encoding is verified.
TO_JSON_STRING preserves the stored row representation, not pre-ingestion bytes.

Published reference only; deployment/schema equivalence remains unverified:
https://github.com/near/near-public-lakehouse/blob/76e0b2cd217b0efc6959363b8e83c561f5ca7d96/src/lakehouse/notebooks/BQ%20Writer%20Stream.py

Match arrays have no truncation limit. Each lookup is grouped before joining;
duplicate observations remain in arrays and are never arbitrarily selected.
The summary is emitted even for zero selected actions. A source access/schema
error fails the query and cannot produce a summary or establish zero activity.
All coverage statements describe observed records, not independent completeness.
*/

WITH action_partition AS (
    SELECT
        a.block_date,
        TO_JSON_STRING(a) AS source_row_json
    FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions` AS a
    WHERE a.block_date = DATE '2026-09-23'
),
action_fields AS (
    SELECT
        *,
        JSON_VALUE(source_row_json, '$.receipt_id') AS receipt_id,
        JSON_VALUE(source_row_json, '$.action_kind') AS action_kind,
        JSON_VALUE(source_row_json, '$.receipt_receiver_account_id') AS receiver,
        JSON_VALUE(source_row_json, '$.receipt_predecessor_account_id') AS predecessor,
        JSON_VALUE(source_row_json, '$.index_in_action_receipt') AS source_action_index_text,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.index_in_action_receipt') AS INT64)
            AS action_index,
        JSON_VALUE(source_row_json, '$.block_hash') AS source_block_hash,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.block_height') AS INT64)
            AS source_block_height,
        JSON_VALUE(source_row_json, '$.block_timestamp_utc') AS source_timestamp_text,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.block_timestamp_utc') AS TIMESTAMP)
            AS source_timestamp_utc,
        JSON_VALUE(source_row_json, '$.chunk_hash') AS source_chunk_hash,
        JSON_VALUE(source_row_json, '$.shard_id') AS source_shard_id_text,
        JSON_VALUE(source_row_json, '$.signer_account_id') AS source_signer_account_id,
        JSON_VALUE(source_row_json, '$.signer_public_key') AS source_signer_public_key,
        JSON_VALUE(source_row_json, '$.is_delegate_action') AS source_delegation_text,
        JSON_QUERY(source_row_json, '$.args') AS raw_args_json,
        JSON_VALUE(source_row_json, '$.args') AS raw_args_scalar_text
    FROM action_partition
),
action_keys AS (
    SELECT
        *,
        COUNT(*) OVER (PARTITION BY receipt_id, action_index)
            AS same_day_action_key_rows
    FROM action_fields
),
selected_actions AS (
    SELECT *
    FROM action_keys
    WHERE action_kind = 'TRANSFER'
        AND receiver = 'fefundsadmin.sputnik-dao.near'
),
selected_receipts AS (
    SELECT DISTINCT receipt_id
    FROM selected_actions
    WHERE NULLIF(TRIM(receipt_id), '') IS NOT NULL
),
outcome_partition AS (
    SELECT
        o.block_date,
        o.receipt_id,
        o.status,
        o.executor_account_id,
        o.block_timestamp_utc,
        TO_JSON_STRING(o) AS source_outcome_row_json
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    WHERE o.block_date = DATE '2026-09-23'
),
block_partition AS (
    SELECT block_hash, block_height, block_timestamp_utc
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date = DATE '2026-09-23'
),
block_groups AS (
    SELECT
        block_hash,
        COUNT(*) AS block_rows,
        COUNTIF(block_height IS NULL OR NULLIF(TRIM(block_hash), '') IS NULL
                OR block_timestamp_utc IS NULL
                OR DATE(block_timestamp_utc) != DATE '2026-09-23') AS invalid_block_rows,
        ARRAY_AGG(STRUCT(block_height, block_hash, block_timestamp_utc)
                  ORDER BY block_height, block_timestamp_utc) AS observations
    FROM block_partition
    GROUP BY block_hash
),
outcome_candidates AS (
    SELECT
        o.*,
        JSON_VALUE(source_outcome_row_json, '$.block_hash') AS outcome_record_block_hash,
        JSON_VALUE(source_outcome_row_json, '$.block_height') AS outcome_record_block_height_text,
        JSON_VALUE(source_outcome_row_json, '$.chunk_hash') AS outcome_record_chunk_hash,
        JSON_VALUE(source_outcome_row_json, '$.shard_id') AS outcome_record_shard_id_text,
        JSON_VALUE(source_outcome_row_json, '$.executed_in_block_hash') AS executed_in_block_hash
    FROM outcome_partition AS o
    WHERE o.receipt_id IN (SELECT receipt_id FROM selected_receipts)
),
outcome_groups AS (
    SELECT
        o.receipt_id,
        COUNT(*) AS outcome_rows,
        COUNTIF(NULLIF(TRIM(o.status), '') IS NULL) AS missing_status_rows,
        COUNTIF(o.block_timestamp_utc IS NULL
                OR DATE(o.block_timestamp_utc) != DATE '2026-09-23') AS invalid_outcome_timestamp_rows,
        COUNTIF(o.executor_account_id IS NULL
                OR o.executor_account_id != 'fefundsadmin.sputnik-dao.near') AS executor_mismatch_rows,
        COUNTIF(NULLIF(TRIM(o.executed_in_block_hash), '') IS NULL)
            AS unavailable_execution_hash_rows,
        COUNTIF(COALESCE(b.block_rows, 0) != 1 OR b.invalid_block_rows != 0)
            AS unresolved_execution_block_rows,
        ARRAY_AGG(STRUCT(
            o.block_date AS outcome_partition_date,
            o.outcome_record_block_hash,
            o.outcome_record_block_height_text,
            o.block_timestamp_utc AS outcome_record_timestamp_utc,
            o.outcome_record_chunk_hash,
            o.outcome_record_shard_id_text,
            o.executed_in_block_hash,
            b.block_rows AS execution_block_match_rows,
            b.invalid_block_rows AS execution_block_invalid_rows,
            b.observations AS execution_block_observations,
            o.status,
            o.executor_account_id,
            o.source_outcome_row_json
        ) ORDER BY o.executed_in_block_hash, o.block_timestamp_utc,
                   o.source_outcome_row_json) AS observations
    FROM outcome_candidates AS o
    LEFT JOIN block_groups AS b ON o.executed_in_block_hash = b.block_hash
    GROUP BY o.receipt_id
),
transaction_partition AS (
    SELECT
        t.block_date,
        t.transaction_hash,
        t.converted_into_receipt_id,
        t.signer_account_id,
        t.receiver_account_id,
        TO_JSON_STRING(t) AS source_transaction_row_json
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions` AS t
    WHERE t.block_date = DATE '2026-09-23'
),
initial_origin_groups AS (
    SELECT
        converted_into_receipt_id AS receipt_id,
        COUNT(*) AS initial_origin_rows,
        COUNTIF(NULLIF(TRIM(transaction_hash), '') IS NULL) AS missing_transaction_hash_rows,
        ARRAY_AGG(STRUCT(
            block_date AS transaction_partition_date,
            transaction_hash,
            converted_into_receipt_id,
            signer_account_id,
            receiver_account_id,
            JSON_VALUE(source_transaction_row_json, '$.block_hash') AS transaction_block_hash,
            JSON_VALUE(source_transaction_row_json, '$.block_height') AS transaction_block_height_text,
            JSON_VALUE(source_transaction_row_json, '$.block_timestamp_utc') AS transaction_timestamp_text,
            source_transaction_row_json
        ) ORDER BY transaction_hash, source_transaction_row_json) AS observations
    FROM transaction_partition
    WHERE converted_into_receipt_id IN (SELECT receipt_id FROM selected_receipts)
    GROUP BY converted_into_receipt_id
),
classified AS (
    SELECT
        a,
        o AS outcome_audit,
        t AS initial_origin_audit,
        CASE
            WHEN NULLIF(TRIM(a.receipt_id), '') IS NULL
                OR a.action_index IS NULL OR a.action_index < 0
                OR a.source_block_height IS NULL
                OR NULLIF(TRIM(a.source_block_hash), '') IS NULL
                THEN 'UNAVAILABLE_OR_INVALID_ACTION_IDENTITY'
            WHEN a.same_day_action_key_rows != 1 THEN 'DUPLICATE_ACTION_KEY'
            WHEN a.source_timestamp_utc IS NULL
                OR DATE(a.source_timestamp_utc) != DATE '2026-09-23'
                THEN 'UNAVAILABLE_OR_INVALID_SOURCE_TIMESTAMP'
            ELSE 'OBSERVED_ACTION_KEY_AND_TIMESTAMP_CONSISTENT'
        END AS action_check,
        CASE
            WHEN o.receipt_id IS NULL
                THEN 'NO_SAME_DAY_OUTCOME_BOUNDARY_OR_COVERAGE_UNRESOLVED'
            WHEN o.outcome_rows != 1 THEN 'MULTIPLE_OUTCOMES_NO_CANONICAL_SELECTION'
            WHEN o.missing_status_rows != 0 OR o.invalid_outcome_timestamp_rows != 0
                OR o.executor_mismatch_rows != 0
                THEN 'INVALID_OR_UNAVAILABLE_OUTCOME_FIELDS'
            WHEN o.unavailable_execution_hash_rows != 0
                OR o.unresolved_execution_block_rows != 0
                THEN 'EXECUTION_BLOCK_BOUNDARY_OR_COVERAGE_UNRESOLVED'
            ELSE 'UNIQUE_SAME_DAY_OUTCOME_OBSERVATION_STATUS_RETAINED'
        END AS outcome_check,
        CASE
            WHEN t.receipt_id IS NULL
                THEN 'NO_INITIAL_TX_MATCH_DESCENDANT_OR_BOUNDARY_OR_COVERAGE_UNRESOLVED'
            WHEN t.initial_origin_rows != 1 THEN 'MULTIPLE_INITIAL_TX_MATCHES_NO_SELECTION'
            WHEN t.missing_transaction_hash_rows != 0 THEN 'INVALID_TRANSACTION_HASH'
            ELSE 'UNIQUE_INITIAL_RECEIPT_TX_MATCH_ONLY'
        END AS initial_origin_check
    FROM selected_actions AS a
    LEFT JOIN outcome_groups AS o ON a.receipt_id = o.receipt_id
    LEFT JOIN initial_origin_groups AS t ON a.receipt_id = t.receipt_id
),
detail_rows AS (
    SELECT STRUCT(
        'UNCLASSIFIED_TRANSFER' AS economic_classification,
        a AS source_action,
        action_check,
        outcome_audit,
        outcome_check,
        initial_origin_audit,
        initial_origin_check,
        'INITIAL_RECEIPT_ONLY_FULL_RECEIPT_ORIGIN_UNAVAILABLE' AS origin_lookup_scope,
        CAST(NULL AS STRING) AS transfer_amount_yoctonear,
        CAST(NULL AS STRING) AS transfer_amount_near,
        'UNAVAILABLE_UNVERIFIED_RECEIPT_TRANSFER_ARGS_ENCODING' AS amount_check,
        JSON_TYPE(SAFE.PARSE_JSON(a.raw_args_json)) AS observed_args_json_type,
        a.predecessor = 'system' AS predecessor_is_system,
        a.predecessor = a.receiver AS predecessor_equals_receiver,
        a.predecessor IN (
            'fefundsadmin.sputnik-dao.near',
            '1csfundsadmin.sputnik-dao.near',
            'buybacks.multisignature.near'
        ) AS predecessor_in_current_candidate_wallet_list,
        a.predecessor = 'intents.near' AS predecessor_is_intents_contract,
        'COUNTERPARTY_FLAGS_ONLY_NOT_REVENUE_REFUND_OR_OWNERSHIP_CLASSIFICATIONS'
            AS counterparty_flag_basis
    ) AS transfer_record
    FROM classified
),
selection_controls AS (
    SELECT
        COUNT(*) AS observed_action_partition_rows,
        COUNTIF(NULLIF(TRIM(action_kind), '') IS NULL
                OR NULLIF(TRIM(receiver), '') IS NULL) AS unavailable_selector_rows,
        COUNTIF(action_kind = 'TRANSFER') AS observed_partition_transfer_rows
    FROM action_fields
),
candidate_controls AS (
    SELECT
        COUNT(*) AS selected_action_rows,
        COUNT(DISTINCT a.receipt_id) AS distinct_selected_receipt_ids,
        COUNTIF(action_check != 'OBSERVED_ACTION_KEY_AND_TIMESTAMP_CONSISTENT')
            AS unavailable_or_invalid_action_rows,
        COUNTIF(outcome_audit.receipt_id IS NULL) AS missing_same_day_outcome_matches,
        COUNTIF(outcome_audit.outcome_rows > 1) AS actions_with_duplicate_outcome_matches,
        COUNTIF(initial_origin_audit.receipt_id IS NULL) AS missing_same_day_initial_tx_matches,
        COUNTIF(initial_origin_audit.initial_origin_rows > 1) AS actions_with_duplicate_initial_tx_matches,
        COUNTIF(a.raw_args_json IS NULL OR a.raw_args_json = 'null') AS unavailable_raw_args_rows
    FROM classified
),
summary AS (
    SELECT STRUCT(
        CASE
            WHEN s.observed_action_partition_rows = 0
                THEN 'SOURCE_ACTION_PARTITION_EMPTY_EVIDENCE_UNAVAILABLE'
            WHEN s.unavailable_selector_rows > 0
                THEN 'SELECTION_PARTIAL_OR_UNAVAILABLE_SELECTOR_FIELDS_MISSING'
            WHEN c.selected_action_rows = 0
                THEN 'NO_OBSERVED_MATCHES_IN_SELECTED_PARTITION'
            ELSE 'OBSERVED_TRANSFER_CANDIDATES_NOT_ECONOMICALLY_CLASSIFIED'
        END AS discovery_check,
        s,
        c,
        (SELECT COUNT(*) FROM outcome_partition) AS observed_outcome_partition_rows,
        (SELECT COUNT(*) FROM transaction_partition) AS observed_transaction_partition_rows,
        (SELECT COUNT(*) FROM block_partition) AS observed_block_partition_rows,
        CASE
            WHEN (SELECT COUNT(*) FROM outcome_partition) = 0
                OR (SELECT COUNT(*) FROM transaction_partition) = 0
                OR (SELECT COUNT(*) FROM block_partition) = 0
                THEN 'ONE_OR_MORE_LOOKUP_PARTITIONS_EMPTY_EVIDENCE_UNAVAILABLE'
            ELSE 'OBSERVED_LOOKUP_PARTITIONS_NONEMPTY_NOT_COMPLETENESS_PROOF'
        END AS lookup_partition_check,
        (SELECT COUNT(*) FROM detail_rows) AS output_transfer_rows,
        CAST(NULL AS STRING) AS total_transfer_amount_yoctonear,
        CAST(NULL AS STRING) AS total_transfer_amount_near,
        'NOT_EVALUATED_ENCODING_UNVERIFIED' AS amount_validity_check,
        c.selected_action_rows AS unavailable_transfer_amount_rows,
        'NOT_VERIFIED_IN_EXISTING_REPOSITORY_SQL' AS receipt_origin_table_status,
        'OBSERVED_RECORDS_ONLY_NOT_INDEPENDENT_COMPLETENESS' AS coverage_basis,
        'NO_SAME_DAY_MATCH_IS_NOT_FAILURE_OR_NONOCCURRENCE' AS missing_link_interpretation
    ) AS summary_record
    FROM selection_controls AS s
    CROSS JOIN candidate_controls AS c
)
SELECT
    DATE '2026-09-23' AS observation_date,
    'fefundsadmin.sputnik-dao.near' AS target_account_id,
    'NATIVE_ONLY_EXCLUDES_TOKENS_AND_INTERNAL_VERIFIER_BALANCES' AS asset_scope,
    'SUMMARY' AS row_kind,
    (SELECT summary_record FROM summary) AS summary_record,
    (SELECT transfer_record FROM detail_rows WHERE FALSE) AS transfer_record

UNION ALL

SELECT
    DATE '2026-09-23',
    'fefundsadmin.sputnik-dao.near',
    'NATIVE_ONLY_EXCLUDES_TOKENS_AND_INTERNAL_VERIFIER_BALANCES',
    'TRANSFER',
    (SELECT summary_record FROM summary WHERE FALSE),
    transfer_record
FROM detail_rows
ORDER BY row_kind, transfer_record.source_action.source_block_height,
         transfer_record.source_action.receipt_id,
         transfer_record.source_action.action_index;
