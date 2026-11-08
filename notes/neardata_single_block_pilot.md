# Neardata: one historical block capability check

This note records the initial one-block design and its subsequent manual capture.
[Result 81](../results/81_neardata_single_block_pilot_plan.json) preserves the
original request plan; result 82 records reviewed archive routing, and
[result 83](../results/83_neardata_canonical_block_A_comparison_2026-09-23.json)
validates the saved archive document. No bulk scan is included.

## Validated historical point

The archive hop returned complete HTTP 200 with a 191,778-byte JSON body,
SHA-256 `42338102d2847e49473bd76d760d6d3bab7fafa1f660a0db8f8651725c2611ba`.
Both hops' request/response bytes, metadata, retrieval times and hashes validate.
Copies of the original hop match byte-for-byte. Result 83 reproduces the
recovery's `validation.json` byte-for-byte, and independent integer arithmetic
agrees with its monetary comparisons.

Block 216877934, its hash, predecessor, epoch IDs, nanosecond timestamp, exact
supply, chunk mask, inclusion count and ten ordered chunk headers match the saved
canonical RPC control. All ten `balance_burnt` fields are exact integer strings
matching the control; no reviewed header field is missing.

| Comparison | Exact result |
| --- | ---: |
| Newly included chunks, shards 10, 9, 6, 12, 13 | 5 |
| Inclusion-timed net header debit | 2206853430760200000000 yoctoNEAR |
| Same net debit in NEAR | 0.002206853430760200000000 |
| Discrepancy versus canonical control | 0 yoctoNEAR |
| Carried-forward header debit excluded | 1680380063688100000000 yoctoNEAR |

Block A is already included in result 72's 23 boundary-header observations.
This source confirmation is not added again to that debit total and does not
increase the number of independently observed inclusion blocks.

All ten expected shard IDs have payload records; five have a null chunk payload.
Their arrays contain 477 observed state-change records and two observed receipt
outcomes in total. These describe returned records, not independently established
all-shard state or receipt completeness. The GET sent no credentials/cookies;
response headers are preserved as received.

This establishes anonymous historical access and the required lossless header
fields at one known block. A→B range retention, complete predecessor coverage,
bulk volume/cost and independent weekly debit remain unestablished. Gross burn,
subsidies and full eight-week reconciliation remain unavailable. No additional
collection follows automatically.

The subsequent [contiguous header pilot](neardata_contiguous_header_pilot.md)
is separately capped at 100 height slots, reuses A and its parent, and prepares
actual download/throughput measurements. It does not begin the full interval.

The existing [bulk-source assessment](supply_bulk_source_feasibility.md) remains
open. FastNear's [Neardata overview](https://docs.fastnear.com/neardata) describes
a recent-block surface; it does not establish retained coverage of the research
window or a lossless bulk path. The documented
[final block by height](https://docs.fastnear.com/neardata/block) operation is an
anonymous GET with an optional API-key parameter. This pilot supplies no key,
credentials or billing configuration. The initial plan left anonymous historical
availability untested; result 83 now confirms this one block. An authorization
failure remains a blocker, not permission to provision a paid service or
substitute another endpoint.

## Single target and request

```text
GET https://mainnet.neardata.xyz/v0/block/216877934
```

Compare only saved canonical block A, hash
`HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG`, predecessor
`FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2`. Its nanosecond timestamp is
`1790147486203722296` and exact total supply is
`1307081318396302606160667252596139` yoctoNEAR. The saved active protocol-86
configuration and ten ordered chunk headers are reused without additional RPC
or configuration requests. This point is already part of the epoch supply pilot.

The [published schema](https://docs.fastnear.com/assets/files/neardata-3ad3f0506033a28203f9dec32a5664c8.json)
describes `block.header`, `block.chunks` and `shards`. It lists exact supply and
nanosecond strings and chunk creation/inclusion identifiers. `balance_burnt` is
not explicitly listed; chunk headers allow additional properties. Its actual
presence and precision were checked in result 83 rather than inferred from the
schema: all ten observed values match the saved canonical exact strings.

## Validation and decision

- Require exact hash/height, predecessor, epoch IDs, timestamp and quoted supply
  agreement with the saved canonical RPC response. Reject numeric/float monetary
  replacements. Retain missing optional header fields, including mask, as limits.
- Require the ten ordered chunk identities, shard IDs, predecessor hashes and
  creation/inclusion heights to match. Check any returned `balance_burnt` as an
  original quoted u128 string against the saved value. Invalid values stop.
- Sum net debit only for the five chunks newly included at A. The saved control
  is exactly `2206853430760200000000` yoctoNEAR. Missing needed monetary fields
  leave the Neardata sum and discrepancy null; carried-forward headers are not
  charged again. This is net header debit, not gross burn.
- Report shard payload IDs, missing payloads, chunkless payloads and observed
  state/outcome counts. These checks do not independently establish complete
  historical state-change or receipt retention.

If identity and exact monetary fields match, this establishes one historical
point with the fields needed for an inclusion-timed net-debit comparison. It
does not establish A→B range retention, a canonical predecessor census, bulk
permissions, volume/cost, weekly debit or eight-week reconciliation. Those remain
separate gates before any broader collection. Gross burn and subsidies remain
unavailable even if the one-block net-debit comparison closes.

A `null` body, missing history, HTTP 401/403/404/429, redirects, incomplete bodies,
an unexpected document or identity mismatch stops this attempt with evidence
retained. `null` is not zero activity. No retries, fallback, key acquisition or
additional requests follow. Valid headers with unavailable debit fields produce
an explicit capability limitation rather than an invented monetary total.

## Manual command and files

```bash
.venv/bin/python analysis/34_neardata_single_block_pilot.py collect
```

The initial command above produced the saved redirect. It is retained as procedure
history, not a request to collect it again. That collector attempts one GET after
65 seconds, with a 15-second connection and
60-second request deadline and a fixed 32 MiB body cap. The byte cap is a local
transport guard, not a billing or bulk-cost estimate. No block loop is included.
The collector writes a new exclusive directory:

```text
results/neardata_supply_block_pilot_2026-09-23/<UTC>_<id>/
  run.json
  block-A.request.http
  block-A.request.json
  block-A.response.body
  block-A.metadata.json
  validation.json              # only after local validation
  stopped.json                 # only on failure
```

Request bytes, body bytes and array order are preserved with HTTP status/headers,
endpoint, UTC retrieval times, lengths and SHA-256. Partial/error responses stay
saved. The future offline command is `validate --run-dir <saved-directory>`;
`plan` prints result 81 without making data requests.

Tests use synthetic Neardata-shaped documents derived from the saved RPC control,
not fetched Neardata evidence. They block live networking and verify exact
arithmetic, missing fields, reordered/partial manifests, identity/type failures,
null/auth/redirect/partial/oversize errors, one-request scope and preservation.

## Saved archive redirect

The first manual attempt returned a complete 302 with an unchanged-height
Location at `a3.mainnet.neardata.xyz`. Its original stop policy retained the
response without following it. The [archive-routing recovery assessment](neardata_archive_redirect_recovery.md)
verifies the route against pinned official source. Its manually collected
exact-URL hop now validates as result 83 with the original limits. The original
capture, collector and results 81–82 remain unchanged.
