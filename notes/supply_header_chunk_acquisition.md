# Lossless supply header/chunk acquisition specification

[Result 72](../results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json)
identifies 618,436.074970164323861118656646 NEAR of protocol-validated epoch reward
minting for 21–27 September. Exact endpoint supply movement is
+611,555.974235517852937718656646 NEAR. Their difference,
6,880.100734646470923400000000 NEAR, is **implied net debit**, not independently
measured weekly debit or actual burn. Direct boundary-header debits total
0.104122811923337500000000 NEAR across only 23 application blocks. Gross burn,
subsidies and the full eight-week reconciliation remain unavailable/open.

The machine-readable handoff is
[result 73](../results/73_supply_header_chunk_acquisition_spec_2026-09-23.json).
It is an acquisition specification, not evidence of an accessible bulk source.

[Result 83](../results/83_neardata_canonical_block_A_comparison_2026-09-23.json)
now establishes anonymous Neardata archive access with exact supply, inclusion
fields and all ten chunk debit strings at block A. The five newly included
headers match the canonical net debit exactly. This is a verified point source,
not an acquired A→B interval or independently established bulk retention. The
range, completeness and cost gates below remain open. The separate
[100-slot header pilot](neardata_contiguous_header_pilot.md) prepares actual
size/throughput measurement and observed continuity checks; the full interval
has not been collected or scheduled.

## Exact pilot interval and controls

| Role | Height | Hash |
| --- | ---: | --- |
| Opening predecessor, excluded from debit sum | 216877933 | `FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2` |
| First included block A | 216877934 | `HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG` |
| Last included block, B's parent | 216921133 | `2Q7yUNdaLfnTkWduSkMYJfueFFg7dgHYpMb4chiS5MZi` |
| Following boundary B, excluded from debit sum | 216921134 | `J6jyjUSFFatXnCKEG3nKaD9qQLzQrY4xWyFkB5a5mJHB` |

The acquisition interval is `[216877934, 216921134)` on canonical mainnet, epoch
4793. A's timestamp is 23 September 07:11:26.203722296 UTC; B's parent's timestamp
is 14:44:30.307780019 UTC. These are inclusion boundaries, not receipt execution
dates. There are 43,200 numerical height slots, not an assumed number of produced
blocks. The saved ten-shard layout implies at most 432,000 manifest entries.
Actual produced-block count, byte size, compression and acquisition cost remain
unestablished.

## Required export

Each produced block needs height, hash, predecessor hash/height, exact nanosecond
UTC timestamp, epoch and next-epoch IDs, exact total-supply string, ordered chunk
mask and included-chunk count. Preserve the complete ordered chunk manifest:
array index, shard ID, chunk hash, creation predecessor hash, creation height,
inclusion height and exact `balance_burnt` string. All monetary values are
original integer yoctoNEAR strings with no upstream FLOAT conversion.

The manifest records network, source implementation/version, canonical selection
rule, schema/units, declared coverage, actual row counts, export/retrieval UTC
times, file sizes and SHA-256 hashes, retention, read permissions and bounded cost.
An NDJSON structure with header/chunks objects matching the saved RPC controls
or an equivalent lossless typed export is suitable. File format alone does not
establish monetary precision or canonical completeness.

## Acceptance and arithmetic

1. Match the saved range-edge hashes, timestamps and opening predecessor. Reject
   conflicting hash/height keys. Every produced block must link to the preceding
   exported produced block through `prev_hash`; allow legal skipped heights.
2. Verify the epoch ID and protocol/layout against saved A configuration. Match
   shard count/IDs, ordered mask, inclusion count and unique within-manifest keys.
   Retain carried-forward headers; they are expected repeated observations.
3. Sum a chunk debit only when `height_included == inclusion_block.height`.
   Preserve earlier creation predecessors for delayed chunks. They need not equal
   the inclusion block's immediate predecessor. Do not globally deduplicate by
   chunk hash and accidentally remove a newly included observation.
4. Independently sum exact inclusion-timed debits, then compare
   `S_last − S_opening_predecessor = recorded_mint_at_A − summed_net_debits`
   using the reviewed historical protocol path and separately recorded mint.
   Preserve any discrepancy; tolerance is zero yoctoNEAR. Missing rows or partial
   manifests make complete totals unavailable, not zero.

The historical
[block implementation](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/block.rs#L145)
supports inclusion-time accounting. Its net debit does not separate gross burn
from subsidies. Those runtime components remain a separate retention dependency.

## Supported retrieval options and current access status

| Option | What it could supply | Current status |
| --- | --- | --- |
| Read-only export from an already retained archive | Canonical block records and ordered chunk headers can supply the required exact fields. | Requires an existing archive owner/export tool and permission; no operator or accessible path is established. No infrastructure provisioning is proposed. |
| Existing lossless object export | A suitable object path could be read after schema, lineage, retention and cost checks. | No suitable accessible path is established. Permissions and cost must be supplied before acquisition. |
| Existing public BigQuery tables | Current schemas and predecessor fields are verified. | Required inclusion/debit fields are absent; FLOAT supply cannot be made lossless by casting. |
| Documented GCS `block_chunks` Avro export | Existing source research identifies its path and requester-pays setup. | Selected columns omit inclusion/debit data and use a chunk-originated join; access would not repair that omission. Retention, precision, permissions and charges remain unverified. |
| Public archival `block` RPC | Suitable for the point controls already saved. | Individual-block scans are excluded; a point API is not evidence of bulk availability. |
| Neardata REST via reviewed archive routing | Result 83 confirms all required supply/chunk inclusion and net-debit fields at block A, matching the canonical control exactly. | One historical point is validated. Result 84 prepares at most 100 header slots to measure size, throughput and continuity. Full A→B collection stays disabled pending review; no range-retention or bulk-cost claim is made. |

No provider contact, object retrieval, query, dry run or additional chain-data
request is needed to record this dependency. Existing source research remains
in [bulk-source feasibility](supply_bulk_source_feasibility.md) and
[schema validation](supply_schema_inventory_validation.md).

## Eight-week extension

The established epoch method can extend exact endpoint movement, actual epoch
application census and independently recorded/protocol-validated epoch reward
minting week by week. Reuse saved Sunday hashes and already captured endpoints,
walk actual start/parent identities, apply successor-epoch reward-response
offsets, and cache captures across week boundaries. Seven of the nine full-window
endpoint headers remain uncaptured; their saved hashes are available. Review
actual historical configurations for each new epoch or a genuinely complete
activation record. Reward responses after a window edge may still describe
minting applied inside it. Fixed epoch lengths and positive supply movements do
not replace the census.

Full-window independently measured net debits require complete inclusion-timed
bulk evidence. Even a successful A→B pilot is not full-week or eight-week
coverage. Separately measuring gross burn and subsidies requires the retained
runtime breakdown. The eight-week accounting remains open, and the original
supply-versus-validator residual is neither replaced nor repaired by result 72.
