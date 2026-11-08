/* @datacloud.settings
{"version":1,"service":"BIG_QUERY","connectionInfo":{"billingProjectId":"INHERIT"},"dialect":"GOOGLE_SQL"}
*/

/*
Three specified mainnet accounts; native receipt-action candidate layer only.
Target execution interval: [2026-08-24, 2026-10-19) UTC.
All chain reads have direct 2026-08-23..2026-10-24 partition predicates.
The one-day lookback and six-day tail are lookup bounds, not completeness proofs.
Older-source receipts, delayed indexing and out-of-boundary links stay unresolved.

Verified deployed evidence: SQL 39/result 47 preserve actual receipt_actions,
execution_outcomes and blocks fields. Result 48 establishes TRANSFER args as a
JSON-encoded string containing a deposit-only object with an integer STRING.
Function-call/other action args are retained for encoding and balance diagnostics.
No monetary SQL casts or sums: offline strict JSON decoding must reject duplicate
keys and preserve integer yoctoNEAR. All observations are economically unclassified.

Every lookup is grouped before joining. Duplicate observations are retained in
untruncated arrays and excluded from accepted local-execution comparisons.
No receipt-origin join is attempted: result 64 establishes the actual table name
receipt_origin_transaction, but its columns/descendant coverage are not saved.
transactions.converted_into_receipt_id is initial-only and is not substituted.

Internal movement means a native action between the three selected account IDs;
it does not mean an internal Verifier credit. Signer/predecessor are not proven
funding owners. Success is local receipt execution, not complete-chain settlement.
Function-call deposits, refunds, fees, storage, staking and deletion proceeds can
require additional evidence. Tokens and internal Verifier balances are excluded.
No observed match is not proof of no payment. Source access/schema errors fail.
Intended export: results/74_three_wallet_native_flow_candidates_2026-08-24_to_2026-10-18.json
*/

WITH wallets AS (
    SELECT account_id FROM UNNEST([
        'fefundsadmin.sputnik-dao.near',
        '1csfundsadmin.sputnik-dao.near',
        'buybacks.multisignature.near'
    ]) AS account_id
),
action_partition AS (
    SELECT a.block_date, a.receipt_id, a.action_kind,
        a.receipt_predecessor_account_id AS predecessor,
        a.receipt_receiver_account_id AS receiver,
        TO_JSON_STRING(a) AS source_row_json
    FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions` AS a
    WHERE a.block_date BETWEEN DATE '2026-08-23' AND DATE '2026-10-24'
),
action_daily AS (
    SELECT block_date, COUNT(*) AS observed_action_rows,
        COUNTIF(NULLIF(TRIM(action_kind), '') IS NULL
            OR NULLIF(TRIM(predecessor), '') IS NULL
            OR NULLIF(TRIM(receiver), '') IS NULL) AS unavailable_selector_rows
    FROM action_partition GROUP BY block_date
),
selected AS (
    SELECT *,
        JSON_VALUE(source_row_json, '$.index_in_action_receipt') AS action_index_text,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.index_in_action_receipt') AS INT64) AS action_index,
        JSON_VALUE(source_row_json, '$.block_hash') AS source_block_hash,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.block_height') AS INT64) AS source_block_height,
        SAFE_CAST(JSON_VALUE(source_row_json, '$.block_timestamp_utc') AS TIMESTAMP) AS source_timestamp_utc,
        JSON_VALUE(source_row_json, '$.block_timestamp') AS source_timestamp_nanosec,
        JSON_VALUE(source_row_json, '$.chunk_hash') AS source_chunk_hash,
        JSON_VALUE(source_row_json, '$.shard_id') AS source_shard_id_text,
        JSON_VALUE(source_row_json, '$.signer_account_id') AS signer_account_id,
        JSON_VALUE(source_row_json, '$.signer_public_key') AS signer_public_key,
        JSON_VALUE(source_row_json, '$.is_delegate_action') AS delegation_text,
        JSON_QUERY(source_row_json, '$.args') AS raw_args_json,
        JSON_VALUE(source_row_json, '$.args') AS raw_args_scalar_text
    FROM action_partition
    WHERE predecessor IN (SELECT account_id FROM wallets)
        OR receiver IN (SELECT account_id FROM wallets)
),
selected_receipts AS (
    SELECT DISTINCT receipt_id FROM selected WHERE NULLIF(TRIM(receipt_id), '') IS NOT NULL
),
action_key_counts AS (
    SELECT k.receipt_id, k.index_in_action_receipt AS action_index,
        COUNT(*) AS action_key_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions` AS k
    WHERE k.block_date BETWEEN DATE '2026-08-23' AND DATE '2026-10-24'
        AND k.receipt_id IN (SELECT receipt_id FROM selected_receipts)
    GROUP BY k.receipt_id, k.index_in_action_receipt
),
outcome_candidates AS (
    SELECT o.receipt_id, o.block_date AS outcome_record_date,
        o.status, o.executor_account_id, o.block_timestamp_utc AS outcome_record_timestamp_utc,
        JSON_VALUE(TO_JSON_STRING(o), '$.executed_in_block_hash') AS executed_in_block_hash,
        TO_JSON_STRING(o) AS source_outcome_row_json
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    WHERE o.block_date BETWEEN DATE '2026-08-23' AND DATE '2026-10-24'
        AND o.receipt_id IN (SELECT receipt_id FROM selected_receipts)
),
block_candidates AS (
    SELECT block_date, block_hash, block_height, block_timestamp_utc,
        CAST(block_timestamp AS STRING) AS block_timestamp_nanosec
    FROM `bigquery-public-data.crypto_near_mainnet_us.blocks`
    WHERE block_date BETWEEN DATE '2026-08-23' AND DATE '2026-10-24'
        AND (block_hash IN (SELECT source_block_hash FROM selected)
            OR block_hash IN (SELECT executed_in_block_hash FROM outcome_candidates))
),
block_groups AS (
    SELECT block_hash, COUNT(*) AS block_rows,
        COUNTIF(block_height IS NULL OR block_height < 0 OR block_timestamp_utc IS NULL
            OR DATE(block_timestamp_utc) != block_date
            OR NULLIF(TRIM(block_hash), '') IS NULL) AS invalid_block_rows,
        ARRAY_AGG(STRUCT(block_height, block_hash, block_timestamp_utc, block_timestamp_nanosec)
            ORDER BY block_height, block_timestamp_utc) AS observations
    FROM block_candidates GROUP BY block_hash
),
outcome_groups AS (
    SELECT o.receipt_id, COUNT(*) AS outcome_rows,
        ARRAY_AGG(STRUCT(o.outcome_record_date, o.status, o.executor_account_id,
            o.outcome_record_timestamp_utc, o.executed_in_block_hash,
            o.source_outcome_row_json, b.block_rows AS execution_block_rows,
            b.invalid_block_rows AS execution_block_invalid_rows,
            b.observations AS execution_block_observations)
            ORDER BY o.executed_in_block_hash, o.source_outcome_row_json) AS observations
    FROM outcome_candidates AS o
    LEFT JOIN block_groups AS b ON o.executed_in_block_hash = b.block_hash
    GROUP BY o.receipt_id
),
joined AS (
    SELECT a, k.action_key_rows, s AS source_block_audit, o AS outcome_audit,
        IF(o.outcome_rows = 1, o.observations[SAFE_OFFSET(0)], NULL) AS unique_outcome
    FROM selected AS a
    LEFT JOIN action_key_counts AS k ON a.receipt_id = k.receipt_id AND a.action_index = k.action_index
    LEFT JOIN block_groups AS s ON a.source_block_hash = s.block_hash
    LEFT JOIN outcome_groups AS o ON a.receipt_id = o.receipt_id
),
assessed AS (
    SELECT *,
        CASE
            WHEN NULLIF(TRIM(a.receipt_id), '') IS NULL OR a.action_index IS NULL OR a.action_index < 0
                OR a.source_block_height IS NULL OR a.source_block_height < 0 OR a.source_timestamp_utc IS NULL
                OR DATE(a.source_timestamp_utc) != a.block_date
                OR NULLIF(TRIM(a.source_block_hash), '') IS NULL THEN 'INVALID_ACTION_IDENTITY_OR_TIME'
            WHEN COALESCE(action_key_rows, 0) != 1 THEN 'DUPLICATE_OR_MISSING_ACTION_KEY'
            WHEN COALESCE(source_block_audit.block_rows, 0) != 1
                OR source_block_audit.invalid_block_rows != 0 THEN 'SOURCE_BLOCK_UNRESOLVED'
            WHEN source_block_audit.observations[SAFE_OFFSET(0)].block_height != a.source_block_height
                OR source_block_audit.observations[SAFE_OFFSET(0)].block_timestamp_utc != a.source_timestamp_utc
                THEN 'SOURCE_BLOCK_UNRESOLVED'
            ELSE 'UNIQUE_OBSERVED_ACTION'
        END AS action_check,
        CASE
            WHEN outcome_audit IS NULL THEN 'UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN'
            WHEN outcome_audit.outcome_rows != 1 THEN 'DUPLICATE_OUTCOMES_EXCLUDED'
            WHEN unique_outcome.executor_account_id IS NULL OR unique_outcome.executor_account_id != a.receiver
                OR unique_outcome.outcome_record_timestamp_utc IS NULL
                OR DATE(unique_outcome.outcome_record_timestamp_utc) != unique_outcome.outcome_record_date
                THEN 'INVALID_OUTCOME_IDENTITY_OR_TIME'
            WHEN COALESCE(unique_outcome.execution_block_rows, 0) != 1
                OR unique_outcome.execution_block_invalid_rows != 0 THEN 'EXECUTION_BLOCK_UNRESOLVED'
            WHEN unique_outcome.status IN ('SUCCESS_VALUE', 'SUCCESS_RECEIPT_ID') THEN 'SUCCESS_LOCAL_RECEIPT'
            WHEN unique_outcome.status = 'FAILURE' THEN 'FAILED_LOCAL_RECEIPT'
            ELSE 'UNRECOGNIZED_STATUS'
        END AS outcome_check,
        IF(unique_outcome.execution_block_rows = 1,
            unique_outcome.execution_block_observations[SAFE_OFFSET(0)].block_timestamp_utc,
            NULL) AS execution_timestamp_utc,
        CASE
            WHEN a.predecessor = a.receiver THEN 'SELF_MOVEMENT'
            WHEN a.predecessor IN (SELECT account_id FROM wallets)
                AND a.receiver IN (SELECT account_id FROM wallets) THEN 'BETWEEN_SELECTED_WALLETS'
            ELSE 'EXTERNAL_COUNTERPARTY'
        END AS movement_scope
    FROM joined
),
details AS (
    SELECT *,
        CASE WHEN execution_timestamp_utc IS NULL THEN 'UNRESOLVED_EXECUTION_DATE'
            WHEN execution_timestamp_utc >= TIMESTAMP '2026-08-24 00:00:00+00'
                AND execution_timestamp_utc < TIMESTAMP '2026-10-19 00:00:00+00' THEN 'IN_TARGET_WINDOW'
            ELSE 'OUTSIDE_TARGET_WINDOW' END AS execution_window
    FROM assessed
),
daily AS (
    SELECT day, COALESCE(a.observed_action_rows, 0) AS observed_action_rows,
        COALESCE(a.unavailable_selector_rows, 0) AS unavailable_selector_rows,
        (SELECT COUNT(*) FROM selected AS s WHERE s.block_date = day) AS selected_action_rows
    FROM UNNEST(GENERATE_DATE_ARRAY(DATE '2026-08-23', DATE '2026-10-24')) AS day
    LEFT JOIN action_daily AS a ON a.block_date = day
),
wallet_counts AS (
    SELECT w.account_id,
        (SELECT COUNT(*) FROM details WHERE a.predecessor = w.account_id OR a.receiver = w.account_id) AS selected_rows,
        (SELECT COUNT(*) FROM details WHERE (a.predecessor = w.account_id OR a.receiver = w.account_id)
            AND action_check = 'UNIQUE_OBSERVED_ACTION' AND outcome_check = 'SUCCESS_LOCAL_RECEIPT'
            AND execution_window = 'IN_TARGET_WINDOW') AS successful_local_action_candidates,
        (SELECT COUNT(*) FROM details WHERE (a.predecessor = w.account_id OR a.receiver = w.account_id)
            AND movement_scope = 'BETWEEN_SELECTED_WALLETS') AS internal_movement_rows
    FROM wallets AS w
),
output AS (
    SELECT 'SUMMARY' AS row_kind, TO_JSON_STRING(STRUCT(
        '2026-08-24' AS target_start, '2026-10-18' AS target_end,
        '2026-08-23' AS lookup_start, '2026-10-24' AS lookup_end,
        'NATIVE_ACTION_CANDIDATES_NOT_COMPLETE_BALANCE_OR_MULTI_ASSET_LEDGER' AS scope,
        'EXECUTION_DATE_FOR_ACCEPTED_FLOWS_SOURCE_DATE_RETAINED' AS time_basis,
        'OBSERVED_RECORDS_NOT_INDEPENDENT_COMPLETENESS' AS coverage_basis,
        63 AS expected_lookup_days,
        (SELECT COUNTIF(observed_action_rows > 0) FROM daily) AS observed_action_days,
        (SELECT SUM(unavailable_selector_rows) FROM daily) AS unavailable_selector_rows,
        (SELECT COUNT(*) FROM details) AS output_action_rows,
        (SELECT COUNT(*) FROM details WHERE a.action_kind = 'TRANSFER') AS transfer_action_rows,
        (SELECT COUNT(*) FROM details WHERE a.action_kind = 'FUNCTION_CALL') AS function_call_rows,
        (SELECT COUNT(*) FROM details WHERE action_check != 'UNIQUE_OBSERVED_ACTION') AS excluded_action_rows,
        (SELECT COUNT(*) FROM details WHERE outcome_check = 'DUPLICATE_OUTCOMES_EXCLUDED') AS duplicate_outcome_action_rows,
        (SELECT COUNT(*) FROM details WHERE outcome_check = 'UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN') AS unmatched_outcome_action_rows,
        (SELECT COUNT(*) FROM details WHERE outcome_check = 'FAILED_LOCAL_RECEIPT') AS failed_action_rows,
        (SELECT COUNT(*) FROM details WHERE action_check = 'UNIQUE_OBSERVED_ACTION'
            AND outcome_check = 'SUCCESS_LOCAL_RECEIPT' AND execution_window = 'IN_TARGET_WINDOW') AS successful_local_action_candidates,
        (SELECT COUNT(*) FROM details WHERE movement_scope = 'BETWEEN_SELECTED_WALLETS') AS internal_movement_rows,
        (SELECT COUNT(*) FROM details WHERE execution_window = 'UNRESOLVED_EXECUTION_DATE') AS unresolved_execution_date_rows,
        (SELECT COUNT(*) FROM details WHERE execution_window = 'OUTSIDE_TARGET_WINDOW') AS outside_execution_window_rows,
        (SELECT COUNT(*) + 67 FROM details) AS expected_export_rows,
        'OFFLINE_STRICT_JSON_INTEGER_DECODING_REQUIRED_NO_SQL_MONETARY_TOTAL' AS amount_scope,
        'RECEIPT_ORIGIN_FIELDS_UNVERIFIED_NO_INITIAL_ONLY_SUBSTITUTE' AS origin_scope,
        'UNCLASSIFIED_TRANSFER_UNTIL_INDEPENDENT_ATTRIBUTION' AS economic_scope
    )) AS record_json
    UNION ALL
    SELECT 'DAILY_CONTROL', TO_JSON_STRING(STRUCT(day, observed_action_rows, unavailable_selector_rows, selected_action_rows)) FROM daily
    UNION ALL
    SELECT 'WALLET_CONTROL', TO_JSON_STRING(STRUCT(account_id, selected_rows, successful_local_action_candidates, internal_movement_rows)) FROM wallet_counts
    UNION ALL
    SELECT 'ACTION', TO_JSON_STRING(STRUCT(a AS source_action, action_key_rows, source_block_audit, outcome_audit,
        action_check, outcome_check, execution_timestamp_utc, execution_window, movement_scope,
        IF(a.action_kind = 'TRANSFER', 'UNCLASSIFIED_TRANSFER', 'UNCLASSIFIED_ACTION_CANDIDATE') AS economic_classification,
        a.predecessor = 'system' AS system_predecessor_diagnostic,
        'NOT_PROOF_OF_REFUND_REVENUE_PURCHASE_OR_COMMON_OWNERSHIP' AS counterparty_flag_scope,
        'RAW_ARGS_RETAINED_OFFLINE_EXACT_DECODING' AS amount_check))
    FROM details
)
SELECT row_kind, record_json FROM output ORDER BY row_kind, record_json;




