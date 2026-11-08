# Supply schema inventory: validated 7 November 2026

Result 64 is a complete SQL 44 metadata export: one SUMMARY and 20 COLUMN rows,
matching all three summary counts; no NESTED rows or duplicate field keys occur.
The metadata timestamp is 2026-11-07T08:58:00.904410Z. There are 16 visible
tables; only `blocks` and `chunks` match the inventory's candidate-name filter.
This establishes the current visible schema, not September row coverage or
the absence of relevant sources in other datasets.

| Measurement | Actual exposed fields | Consequence |
| --- | --- | --- |
| Block identity and predecessors | `blocks.block_hash` STRING, `block_height` INT64, `prev_block_hash` STRING; date, INT64 timestamp and TIMESTAMP UTC fields | Supports predecessor diagnostics if rows are collected. Metadata does not prove uniqueness, connectivity, canonical completeness or historical population. Existing SQL 33/38 already provide bounded observed coverage diagnostics. |
| Supply | `blocks.total_supply` FLOAT64 | Existing SQL treats this as yoctoNEAR and divides by 10^24. Exact integer supply cannot be recovered by casting or Decimal parsing. |
| Epoch boundaries/rewards | No `epoch_id`, `next_epoch_id`, nested header or matching epoch/reward table | The deployment cannot supply an epoch census or independent epoch minting through these fields. Positive supply movements remain observations. |
| Chunk identity | `chunks.block_hash` STRING, `block_height` INT64, `chunk_hash` STRING, `shard_id` INT64; timestamps/date, author and signature | Observed chunk/block association is available. These fields alone do not distinguish newly included from carried-forward headers or prove expected shard coverage. |
| Inclusion and net debit | No `height_created`, `height_included`, chunk predecessor, chunk mask or `balance_burnt`; no nested chunk object | No independent inclusion-timed debit total can be extracted from these tables. Flat row block identity must not substitute for inclusion identity. |
| Gas | Block `gas_price`, chunk `gas_used` and `gas_limit`: FLOAT64 | These are not independent actual burn or subsidy measurements. |

Both tables are partitioned on `block_date`; all 20 columns are declared nullable.
Every future chain-table extraction needs direct date predicates and actual
null/duplicate coverage checks. Missing epoch/debit fields are absent from the
observed schema, whereas unexported predecessor rows are missing saved evidence
for fields that do exist. The published silver mapping does not override this
deployment evidence. Other documented bulk-source limitations remain in
`notes/supply_bulk_source_feasibility.md`.

At approximately 1.3 billion NEAR, binary64 storage of yoctoNEAR has spacing
2^58 yoctoNEAR (0.000000288230376151711744 NEAR); conversion to FLOAT64 NEAR
adds another rounding step. This is a representation limit, not an error bound
for the pipeline or a tolerance for summing millions of differences. The saved
0.00001 NEAR arithmetic tolerance remains a consistency check only. Exact
integer monetary strings and zero-yocto arithmetic checks apply to RPC evidence.

## SQL 43 identity

The tracked `sql/43_persistent_activity_shared_week_initial_receipts.sql` is the
authoritative input referenced by analyses 21/22 and results 59/61. Its untracked
`sql/43_persistent_activity_shared_week_initial_receipts 2.sql` copy is byte-identical:
23,662 bytes each, SHA-256
`1b6add55a7a34c75d55d7da331a5e13a939cd7b8abab1f0df485b66fdc20dc98`.
Neither file is changed or removed.

Result 59 records the earlier 23,661-byte version, SHA-256
`b1d0fd263f612360b3ea50a55321b78be68da5d412a3b8cadaa89e8b8525d658`.
Removing only the space after the current final semicolon in memory reproduces
that fingerprint. Result 61 records this exact difference and the current hash;
the historical reports are preserved. The duplicate contains no unique SQL work
and was not referenced by existing validators or saved source-hash records.

## Smallest weekly endpoint pilot

No further BigQuery schema query is needed. The missing fields block an
independent eight-week mint/debit extraction from this dataset. A two-request
pilot can improve the exact weekly endpoint component without pretending to
resolve the missing components. Use the week containing the validated 23 September
event, reusing result 28's observed closing identities:

| Endpoint | Height | Hash |
| --- | --- | --- |
| 20 September closing / 21 September opening | 216553375 | `5sUCEyrF5p3RZvx5DzE6zD4gtknwHf8kMmHnH7ViGPWk` |
| 27 September closing | 217555961 | `5VLWBqYvC98Q5qUzbQ8nHN1wcGZ9CnLxShZgojz4ohUa` |

Result 66 records the exact requests, input hashes, limits and output directory.
Both use the documented [`block`](https://docs.near.org/api/rpc/block-chunk)
method with `params.block_id` set to the saved hash. The official
[provider list](https://docs.near.org/api/rpc/providers) documents
`https://archival-rpc.mainnet.near.org` as public, archival and severely rate
limited. Availability at these two historical blocks is not yet verified.

Manual collection from the repository root:

```bash
.venv/bin/python analysis/25_supply_source_inventory.py collect-week
```

This makes exactly two attempts on a successful run, with 65 seconds before
each request, no retries, no fallback and the existing 15/60-second connection/
request timeouts. It stops at the first HTTP, RPC, identity, amount or manifest
error. Complete request/response bytes, HTTP metadata, endpoint, UTC retrieval
times and SHA-256 values are saved exclusively under a fresh directory in
`results/supply_weekly_header_pilot_2026-09-21_to_2026-09-27/`. The collector
prints its exact path; raw array order and monetary strings are preserved.
The derived output is `<run-directory>/validation.json`.

Validation checks saved hash, height and microsecond timestamp agreement,
unsigned integer-string supply, nonempty predecessor/epoch IDs, unique observed
chunk/shard keys, inclusion heights, mask consistency and new-chunk predecessor
hashes when creation and inclusion heights match. Newly included headers created
earlier retain their own creation predecessor; that comparison is reported as
unchecked rather than forced to match the inclusion block's parent.
This does not independently establish the expected shard layout or that
each saved endpoint is the final canonical block before midnight. Historical
supplies have not been collected by this preparation step.

Two exact endpoint supplies would measure their net movement and provide epoch-ID
seeds. They would not measure the intervening weekly reward issuance or net
debit. A complete canonical epoch/boundary census and inclusion manifests remain
necessary before collecting all reward maps or asserting weekly reconciliation.
Across eight weeks, nine shared endpoint headers would suffice for endpoint
supplies only; this pilot authorizes no automatic extension. Gross burn and
subsidies remain separately unavailable, and a balancing subtraction cannot
replace an independently collected debit component.

Offline reproduction and validation:

```bash
.venv/bin/python analysis/25_supply_source_inventory.py inventory
.venv/bin/python analysis/25_supply_source_inventory.py plan
.venv/bin/python -m unittest discover -s tests -p test_supply_source_inventory.py -v
.venv/bin/python analysis/25_supply_source_inventory.py validate-week --run-dir <saved-run-directory>
```

The inventory and plan commands default to stdout. `--output` creates a new file
exclusively and refuses to overwrite existing evidence. The test transport is
synthetic and the real HTTPS constructor is blocked throughout the offline tests.
