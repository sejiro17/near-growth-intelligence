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
Metadata-only inventory for supply-source feasibility; no chain tables are read.
Use the configured project and us-east1. No query or dry run is performed by
the offline preparation workflow. No billing/cap setting is changed.

Inspect complete top-level types AND nested paths. Candidate table names are
discovered from metadata, not assumed to exist. The summary lists all visible
table names, allowing raw or epoch sources to be assessed without querying them.
JSON/STRING contents and September field population are not established by this
inventory. A missing saved export is not evidence of an unavailable source field.
FLOAT64-to-STRING/BIGNUMERIC casts cannot recover exact protocol amounts.

One SUMMARY row is always returned on successful metadata access. Its
metadata_summary JSON string contains expected_export_rows for truncation checks.
An access/query error is not an empty schema. Metadata has no block_date partition
filter; every future chain-table read will need a direct partition predicate.

Intended export: results/64_supply_source_schema_inventory.json
References:
https://cloud.google.com/bigquery/docs/information-schema-columns
https://cloud.google.com/bigquery/docs/information-schema-column-field-paths
*/

WITH all_columns AS (
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable,
        is_partitioning_column
    FROM `bigquery-public-data.crypto_near_mainnet_us.INFORMATION_SCHEMA.COLUMNS`
),
candidate_tables AS (
    SELECT DISTINCT table_name
    FROM all_columns
    WHERE table_name IN ('blocks', 'chunks')
        OR REGEXP_CONTAINS(
            table_name,
            r'(?i)(block|chunk|epoch|validator|reward|mint|raw|bronze)'
        )
),
metadata_fields AS (
    SELECT
        'COLUMN' AS row_kind,
        c.table_name,
        c.column_name,
        c.column_name AS field_path,
        c.data_type,
        c.is_nullable,
        c.is_partitioning_column,
        CAST(NULL AS STRING) AS description
    FROM all_columns AS c
    INNER JOIN candidate_tables AS t USING (table_name)

    UNION ALL

    SELECT
        'NESTED' AS row_kind,
        p.table_name,
        p.column_name,
        p.field_path,
        p.data_type,
        CAST(NULL AS STRING) AS is_nullable,
        CAST(NULL AS STRING) AS is_partitioning_column,
        p.description
    FROM `bigquery-public-data.crypto_near_mainnet_us.INFORMATION_SCHEMA.COLUMN_FIELD_PATHS` AS p
    INNER JOIN candidate_tables AS t USING (table_name)
    WHERE p.field_path != p.column_name
),
output AS (
    SELECT
        'SUMMARY' AS row_kind,
        CAST(NULL AS STRING) AS table_name,
        CAST(NULL AS STRING) AS column_name,
        CAST(NULL AS STRING) AS field_path,
        CAST(NULL AS STRING) AS data_type,
        CAST(NULL AS STRING) AS is_nullable,
        CAST(NULL AS STRING) AS is_partitioning_column,
        CAST(NULL AS STRING) AS description,
        TO_JSON_STRING(STRUCT(
            CURRENT_TIMESTAMP() AS metadata_time_utc,
            'bigquery-public-data.crypto_near_mainnet_us' AS source_dataset,
            (SELECT COUNT(*) + 1 FROM metadata_fields) AS expected_export_rows,
            (SELECT COUNTIF(row_kind = 'COLUMN') FROM metadata_fields) AS top_level_rows,
            (SELECT COUNTIF(row_kind = 'NESTED') FROM metadata_fields) AS nested_rows,
            ARRAY(
                SELECT DISTINCT table_name
                FROM all_columns
                ORDER BY table_name
            ) AS visible_tables,
            ARRAY(
                SELECT table_name
                FROM candidate_tables
                ORDER BY table_name
            ) AS inspected_tables
        )) AS metadata_summary

    UNION ALL

    SELECT
        row_kind,
        table_name,
        column_name,
        field_path,
        data_type,
        is_nullable,
        is_partitioning_column,
        description,
        CAST(NULL AS STRING) AS metadata_summary
    FROM metadata_fields
)
SELECT
    row_kind,
    table_name,
    column_name,
    field_path,
    data_type,
    is_nullable,
    is_partitioning_column,
    description,
    metadata_summary
FROM output
ORDER BY
    CASE WHEN row_kind = 'SUMMARY' THEN 0 ELSE 1 END,
    table_name,
    field_path,
    row_kind;
