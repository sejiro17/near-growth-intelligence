# Supply source feasibility — 7 November 2026

The validated single-boundary epoch pilot remains separate from the published
eight-week comparison. This assessment prepares metadata discovery only. No
source query, dry run, RPC request or bulk-data retrieval has been executed.

## Established evidence and missing measurements

| Requirement | Established locally | Still unverified |
| --- | --- | --- |
| Block identity and predecessors | SQL 28/33/38 successfully use `blocks.block_height`, `block_hash`, `prev_block_hash`, `block_date` and `block_timestamp_utc`. Result 33 reports 7,930,886 matched predecessor comparisons for 24 August–18 October. | Full block-level rows are not exported. An observed connected sequence is not an independently authenticated index. |
| Exact supply endpoints | Nine weekly closing hashes are saved in result 28; the epoch pilot has exact integer-string RPC supplies at its boundary. | Result 28's amounts are FLOAT-derived. Exact weekly supplies must come from lossless fields or independently captured headers. |
| Epoch membership and boundaries | Exact epoch IDs and one boundary are saved in the A/B RPC captures. | Deployment of nested epoch fields in BigQuery and their historical population are not captured in a saved schema inventory. Positive supply changes are not an epoch census. |
| Newly included chunk net debits | Canonical A/B headers expose exact `balance_burnt` strings and inclusion heights. The validated A debit is 2206853430760200000000 yoctoNEAR. | The old flat chunk inspection does not establish absence of a nested header field. BigQuery nested types, inclusion semantics and coverage require verification. |
| Independent epoch-reward issuance | The pilot's complete historical reward map independently sums to 26971051860538713462297967723 yoctoNEAR and closes its header identity exactly. | All other epoch reward maps are not saved. A table called `rewards` is not evidence of protocol minting. |
| Gross burn and subsidies | Historical nearcore identifies their runtime fields and how they form the net debit. | Retained access to those statistics remains unestablished; neither component is zero-filled. |

## Published mapping is a reference, not the deployed schema

The reviewed [mainnet silver mapping](https://github.com/near/near-public-lakehouse/blob/4de8e1a6b2a97b21f39b8cf8c050a43eb09f4291/src/lakehouse/notebooks/Silver%20Lake%20Mainnet.sql)
retains whole `header` and `chunks` objects in `silver_blocks` and a whole `chunk`
object in `silver_chunks`. Candidate paths therefore include:

- `blocks.header.epoch_id`, `header.next_epoch_id`, `header.prev_hash`,
  `header.prev_height`, `header.timestamp_nanosec` and `header.total_supply`.
- The block's `chunks` array: `shard_id`, `chunk_hash`, `prev_block_hash`,
  `height_created`, `height_included` and `balance_burnt`, plus
  `header.chunk_mask` for manifest checks.
- `chunks.chunk.header` equivalents if the block manifest is not available.

These are candidate paths, not assertions that the BigQuery deployment has them.
The block manifest is preferable to an execution-chunk table for counting newly
included headers, because it retains carried-forward headers and the shard mask.
The silver chunk mapping uses a predecessor-based join; actual inclusion block
identity, duplicates and missing-shard behaviour must be checked rather than
assuming the flat chunk row's date is the supply-recognition date.

The [loader](https://github.com/near/near-public-lakehouse/blob/76e0b2cd217b0efc6959363b8e83c561f5ca7d96/src/lakehouse/notebooks/Mainnet%20Loader.py#L25)
enables type inference. Neither the word `header` nor a later STRING conversion
guarantees lossless monetary lineage. Verify declared types and exact values
against the already saved canonical event before scaling.

The repository also contains an
[epoch/validator pipeline](https://github.com/near/near-public-lakehouse/blob/76e0b2cd217b0efc6959363b8e83c561f5ca7d96/src/lakehouse/notebooks/Epochs%20and%20validators%20Silver%20Pipeline.py).
It groups observed blocks into epoch minima/maxima and retains RPC
`current_validators`, not the pilot's complete `validator_reward_paid_prev_epoch`
map. Its delegator `reward` calculation is based on a DOUBLE balance difference,
clipped at zero and later rounded. Those derived rewards cannot substitute for
independent minting. Deployment or public access to these tables is unverified.
Schema discovery searches table names rather than assuming those tables exist.

## Precision and interpretation

| Representation | Permitted conclusion |
| --- | --- |
| Original integer yoctoNEAR STRING | Candidate exact amount after digit/u128 validation, unit verification and lineage/event checks. |
| Exact decimal/integer storage | Candidate exact amount only if the declared range/scale fits, units are established and no upstream FLOAT conversion occurred. |
| FLOAT64, or a cast from FLOAT64 | Approximate source representation. Decimal/BIGNUMERIC conversion preserves the converted value, not lost protocol digits. |
| JSON or STRING containing an object/array | Metadata alone cannot establish contents or precision. Quoted monetary strings must be inspected without passing through float. |
| A field named `reward`, positive supply change or validator balance delta | No independent issuance classification without mechanism and timing evidence. |

If available, exact weekly net accounting is:

```text
closing supply = opening supply + epoch_reward_mint − included_header_net_debit
included_header_net_debit = gross_burn − subsidy
```

Issuance is assigned to its application block, not the epoch when rewards were
earned. Debits are assigned to canonical inclusion blocks, not receipt execution
dates. Only headers with `height_included == inclusion_block_height` count;
carried-forward headers are excluded. A closing-supply difference cannot fill an
unmeasured independent debit. Gross burn, subsidies and total issuance including
subsidies remain separately unavailable even when this net identity closes.

## One metadata-only discovery query

`sql/44_supply_source_schema_inventory.sql` reads only the dataset's
`INFORMATION_SCHEMA.COLUMNS` and `COLUMN_FIELD_PATHS` views. It inventories full
top-level types, nested paths and partition columns for blocks/chunks and any
visible block/chunk/epoch/validator/reward/mint/raw/bronze table names. One summary
also lists all visible table names. No underlying data or partitions are read.
This does not establish historical row coverage or infer keys inside JSON/STRING.

From the repository root, the following manual command uses the configured
billing project and `us-east1`, preserves existing caps and refuses to overwrite
an existing export:

```bash
(
  set -C
  bq --location=us-east1 --format=prettyjson query \
    --use_legacy_sql=false --max_rows=10000 \
    < sql/44_supply_source_schema_inventory.sql \
    > results/64_supply_source_schema_inventory.json
)
```

This command has not been executed. Metadata-only is not a zero-charge guarantee;
no billing setting or cap is changed. Preserve any saved error rather than
interpreting it as an empty schema. Validate one SUMMARY row, parse its
`metadata_summary` JSON string and reconcile `expected_export_rows` to the export
array length before interpreting absent paths.

## Eight-week extension after schema validation

If usable nested fields exist, BigQuery can process the full partitioned interval
server-side and export eight weekly totals, an actual epoch-boundary census and
coverage/anomaly diagnostics. It need not export all 7,930,886 block records or
retrieve them individually by RPC. First validate a bounded event comparison
against the saved A/parent controls; no additional extraction query is prepared
before schema inspection.

The eventual extraction must retain 23 August closing supply as the opening
baseline; validate predecessor hashes, timestamp/week boundaries, unique block
and chunk keys, expected shard manifests and inclusion masks. Height gaps can be
legal skipped blocks: use `prev_hash`/available predecessor height rather than
requiring numerical height adjacency. Epoch observed minima/maxima require edge
coverage checks before being called complete boundaries. Protocol/layout changes
must be reviewed throughout the interval. Incomplete monetary groups remain null.

Exact reward maps can then be collected per actual epoch, using the validated
next-epoch offset and complete payee maps including treasury. Epochs whose reward
metadata lies after 18 October may still be needed to measure minting applied
inside the window. Bulk boundary fields identify events; they do not themselves
measure minting. Existing positive/negative supply aggregates remain observations.

## Alternative bulk-source limitations

The published
[`NEAR Public Datasets` notebook](https://github.com/near/near-public-lakehouse/blob/76e0b2cd217b0efc6959363b8e83c561f5ca7d96/src/lakehouse/notebooks/NEAR%20Public%20Datasets.py#L58)
documents Avro exports under
`gs://near-lakehouse-public/mainnet/avro/block_chunks/<processed-hour>/`.
The selected fields include block identity, predecessor hash, supply, epoch ID,
shard/chunk identity and gas usage, but omit chunk inclusion heights and
`balance_burnt`. Its inner join starts from chunks and repeats block information
per chunk; it does not by itself guarantee preservation of chunkless blocks or
complete canonical predecessor coverage. Deduplication and a separate complete
block manifest would be needed before treating it as a boundary census. Supply
precision is inherited from the upstream field, not established by the Avro
container. The notebook enables requester-pays access, and object paths use
processing hour rather than block date. Neither target-window retention nor
zero-charge access is verified. No objects or listings were requested.

[Official NEAR documentation](https://docs.near.org/data-infrastructure/big-query)
states that the AWS NEAR Lake source stopped indexing new blocks on 24 March
2026 while BigQuery remains available. The repository README still describes
S3 ingestion. These documents do not establish the post-retirement ingestion
lineage or a free raw Lake archive covering August–October 2026. Saved BigQuery
exports establish observed records during that window, not the missing lineage.

Nearcore's cloud-archive shard format can contain runtime statistics, but a public
location, permissions and the target historical coverage remain unverified.
FastNEAR's [current snapshot documentation](https://docs.fastnear.com/snapshots)
provides request-based archival access rather than a working public self-service
flow. Its [NEAR Data API](https://docs.fastnear.com/neardata) documents a recent
block surface, not guaranteed eight-week historical bulk coverage. None of these
sources currently establishes an accessible replacement for the missing exact
bulk fields. That initial assessment fetched no archive objects, API data,
snapshots or chain records; the subsequent manual point capture is recorded below.

## Validated single-block Neardata comparison

The [one-block pilot](neardata_single_block_pilot.md) and results 81–83 establish
anonymous historical access at saved block A, height 216877934. The manual
response follows reviewed archive routing to `a3.mainnet.neardata.xyz`; its exact
supply, ordered chunk identities, inclusion fields and all ten quoted
`balance_burnt` values match the retained canonical RPC control. Included net
debit is 2206853430760200000000 yoctoNEAR with zero discrepancy. This resolves
point availability and required-field representation even though the published
schema does not explicitly list `balance_burnt`.

Retained A→B or weekly coverage, canonical predecessor continuity and bulk
volume/cost remain unestablished. The separate
[100-slot header pilot](neardata_contiguous_header_pilot.md), result 84, prepares
bounded manual measurement with cached controls and resumable external storage;
the full interval and additional configuration requests remain disabled.
Gross burn/subsidies still require their
separate runtime breakdown. Raw captures are preserved; result 83 reproduces
offline without additional requests.
