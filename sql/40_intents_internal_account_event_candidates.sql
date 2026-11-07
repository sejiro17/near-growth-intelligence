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
One-day candidate discovery for a single Intents internal account. This is not
a balance ledger or a fee/revenue classification. All monetary strings and log
array order remain in the retained source-row/log JSON. No numeric amount casts,
joins, array expansion, truncation limits or receipt-origin assumptions are used.

Source table/partition fields are established by working SQL 05/39. Result 47
preserves the BigQuery outcome-row representation; the manually saved canonical
transaction trace establishes the withdrawal anchor receipt and block hash below.
Optional identifiers are read from row JSON rather than asserting new columns.

The recorded asset is nep141:wrap.near, not nep141.near. Selection deliberately
does not filter by asset or event name: credits from conversions can involve
other assets, and historical event versions may differ. Exact account/key text
matches locate candidate records only. They do not prove which event data item
affects this account or establish its ownership or economic role.

Read the complete 23 September UTC partition, including observations after the
anchor. Backward attribution must order against the DEBIT at the anchor receipt,
not the later native transfer at height 216859521. Keep source and execution
hashes distinct. Same-block cross-chunk order is unresolved unless independently
established; index_in_chunk is not a block-global ordering key.

After export, validate the actual log encoding, decode EVENT_JSON strings with
their array offsets, and retain standard/version/event/data-item positions.
Pair token_ids and amounts by equal-length array indices; never cross-join them.
Keep FAILURE records for diagnosis, excluding them from state-change totals.
SuccessReceiptId records require interpretation of their callbacks. Duplicate
receipt observations require resolution before monetary aggregation.

Logs can be absent, incomplete or insufficient to reconstruct state changes.
Text selection cannot detect unlogged changes or account IDs hidden in opaque
encodings. A zero candidate count is only no observed text matches. The summary
and known anchor are controls for observed records, not completeness proofs.

Historical methodology references (deployment equivalence remains unverified):
https://github.com/near/intents/blob/32a7836f825e8c984c26149f4456793ec7e3d49a/crates/near/nep245/src/events.rs
https://github.com/defuse-protocol/sdk-monorepo/blob/d287210315f3ff1ae2263df9702ee1d84a2d8385/packages/internal-utils/src/utils/messageFactory.ts
The SDK's APP_FEE memo is a candidate signal, not an authenticated fee label or
a required marker for all 1Click flows. Protocol fees_collected is separate from
front-end app fees. Internal mt_burn does not measure native NEAR destruction.
*/

WITH outcome_partition AS (
    SELECT
        o.block_date,
        o.receipt_id,
        o.executor_account_id,
        o.status,
        o.block_timestamp_utc,
        TO_JSON_STRING(o) AS source_row_json,
        COUNT(*) OVER (PARTITION BY o.receipt_id) AS same_day_receipt_rows
    FROM `bigquery-public-data.crypto_near_mainnet_us.execution_outcomes` AS o
    WHERE o.block_date = DATE '2026-09-23'
),
observations AS (
    SELECT
        *,
        JSON_QUERY(source_row_json, '$.logs') AS source_logs_json,
        JSON_VALUE(source_row_json, '$.block_height') AS source_block_height_text,
        JSON_VALUE(source_row_json, '$.block_timestamp') AS source_timestamp_nanoseconds_text,
        JSON_VALUE(source_row_json, '$.block_hash') AS source_block_hash,
        JSON_VALUE(source_row_json, '$.executed_in_block_hash') AS executed_in_block_hash,
        JSON_VALUE(source_row_json, '$.chunk_hash') AS source_chunk_hash,
        JSON_VALUE(source_row_json, '$.shard_id') AS source_shard_id_text,
        JSON_VALUE(source_row_json, '$.index_in_chunk') AS source_index_in_chunk_text,
        receipt_id = 'Fnt2xfvuLebRXp4cSupgdHbdeDmDXaWRkUTaJQctwjTK'
            AS is_known_withdrawal_anchor
    FROM outcome_partition
),
marked AS (
    SELECT
        *,
        COALESCE(STRPOS(source_logs_json,
            'a8c56ebbdabc6b6709d4f946d54679db1e4006f5eeb6b3d49c897c86c70ba6cd') > 0, FALSE)
            AS account_text_in_logs,
        COALESCE(STRPOS(source_logs_json,
            'ed25519:CMp71Rp8hx8BimTnGZ2BuVkd92Eak2oYSaW5Fqek9a5r') > 0, FALSE)
            AS public_key_text_in_logs,
        COALESCE(STRPOS(source_logs_json, 'nep141:wrap.near') > 0, FALSE)
            AS target_asset_text_in_logs,
        COALESCE(STRPOS(source_logs_json, 'APP_FEE') > 0, FALSE)
            AS app_fee_text_in_logs
    FROM observations
),
candidates AS (
    SELECT *
    FROM marked
    WHERE (executor_account_id = 'intents.near'
            AND (account_text_in_logs OR public_key_text_in_logs))
        OR is_known_withdrawal_anchor
),
detail_rows AS (
    SELECT STRUCT(
        'UNCLASSIFIED_INTERNAL_ACTIVITY' AS economic_classification,
        block_date,
        receipt_id,
        executor_account_id,
        status,
        block_timestamp_utc,
        source_block_height_text,
        source_timestamp_nanoseconds_text,
        source_block_hash,
        executed_in_block_hash,
        source_chunk_hash,
        source_shard_id_text,
        source_index_in_chunk_text,
        same_day_receipt_rows,
        is_known_withdrawal_anchor,
        account_text_in_logs,
        public_key_text_in_logs,
        target_asset_text_in_logs,
        app_fee_text_in_logs,
        source_logs_json,
        source_row_json
    ) AS event_outcome_record
    FROM candidates
),
summary AS (
    SELECT STRUCT(
        CASE
            WHEN (SELECT COUNT(*) FROM marked) = 0
                THEN 'SOURCE_PARTITION_EMPTY_EVIDENCE_UNAVAILABLE'
            WHEN (SELECT COUNTIF(NULLIF(TRIM(executor_account_id), '') IS NULL)
                  FROM marked) > 0
                OR (SELECT COUNTIF(executor_account_id = 'intents.near'
                    AND (source_logs_json IS NULL OR source_logs_json = 'null'))
                    FROM marked) > 0
                THEN 'TEXT_SELECTION_PARTIAL_OR_UNAVAILABLE'
            WHEN COUNT(*) = 0 THEN 'NO_OBSERVED_CANDIDATE_TEXT_MATCHES_OR_ANCHOR'
            ELSE 'OBSERVED_CANDIDATES_REQUIRE_OFFLINE_EVENT_VALIDATION'
        END AS discovery_check,
        (SELECT COUNT(*) FROM marked) AS observed_partition_outcome_rows,
        (SELECT COUNTIF(executor_account_id = 'intents.near') FROM marked)
            AS observed_intents_outcome_rows,
        (SELECT COUNTIF(NULLIF(TRIM(executor_account_id), '') IS NULL) FROM marked)
            AS unavailable_executor_rows,
        (SELECT COUNTIF(executor_account_id = 'intents.near'
            AND (source_logs_json IS NULL OR source_logs_json = 'null')) FROM marked)
            AS intents_rows_without_available_logs,
        COUNT(*) AS output_candidate_rows,
        COUNT(DISTINCT receipt_id) AS distinct_candidate_receipt_ids,
        COUNTIF(same_day_receipt_rows != 1) AS candidates_with_duplicate_receipt_keys,
        COUNTIF(NULLIF(TRIM(receipt_id), '') IS NULL OR block_timestamp_utc IS NULL
            OR DATE(block_timestamp_utc) != DATE '2026-09-23'
            OR NULLIF(TRIM(status), '') IS NULL) AS candidates_with_invalid_identity_or_status,
        COUNTIF(NULLIF(TRIM(source_block_hash), '') IS NULL
            OR NULLIF(TRIM(executed_in_block_hash), '') IS NULL
            OR source_block_height_text IS NULL OR source_chunk_hash IS NULL
            OR source_shard_id_text IS NULL OR source_index_in_chunk_text IS NULL)
            AS candidates_without_available_ordering_fields,
        COUNTIF(status = 'SUCCESS_VALUE') AS success_value_candidates,
        COUNTIF(status = 'SUCCESS_RECEIPT_ID') AS success_receipt_id_candidates,
        COUNTIF(status = 'FAILURE') AS failure_candidates,
        COUNTIF(is_known_withdrawal_anchor) AS observed_withdrawal_anchor_rows,
        COUNTIF(is_known_withdrawal_anchor AND executor_account_id = 'intents.near'
            AND source_block_hash = '5RCDGcbp8sZ4PtgD3U72GNmtMPPcg9d5AwKZTq5VQg6s'
            AND executed_in_block_hash = '5RCDGcbp8sZ4PtgD3U72GNmtMPPcg9d5AwKZTq5VQg6s'
            AND status = 'SUCCESS_VALUE') AS anchor_rows_matching_saved_rpc_identifiers,
        'OBSERVED_RECORDS_AND_TEXT_MATCHES_ONLY_NOT_INDEPENDENT_COMPLETENESS' AS coverage_basis,
        'NO_OBSERVED_MATCHES_IS_NOT_PROOF_OF_NO_INTERNAL_ACTIVITY' AS empty_result_interpretation,
        'EVENT_ENCODING_AND_VERSION_VALIDATION_REQUIRED_BEFORE_AMOUNT_DECODING' AS decoding_status,
        CAST(NULL AS STRING) AS opening_internal_balance,
        CAST(NULL AS STRING) AS verified_fee_credit_amount,
        CAST(NULL AS STRING) AS withdrawal_revenue_attribution
    ) AS summary_record
    FROM candidates
)
SELECT
    DATE '2026-09-23' AS observation_date,
    'SUMMARY' AS row_kind,
    (SELECT summary_record FROM summary) AS summary_record,
    (SELECT event_outcome_record FROM detail_rows WHERE FALSE) AS event_outcome_record

UNION ALL

SELECT
    DATE '2026-09-23',
    'OUTCOME_CANDIDATE',
    (SELECT summary_record FROM summary WHERE FALSE),
    event_outcome_record
FROM detail_rows
ORDER BY row_kind DESC, event_outcome_record.block_timestamp_utc,
         event_outcome_record.receipt_id, event_outcome_record.source_row_json;
