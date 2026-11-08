# Proposed A→B header acquisition

Status: proposal only. No additional chain data has been requested. The existing
100-height collector remains capped at its original scope; this proposal does
not enable full collection or change its frozen plan. Estimates are derived from
[result 85](../results/85_neardata_header_pilot_validation_216877934_to_216878033.json),
with calculations in [result 86](../results/86_neardata_full_interval_collection_proposal.json).

## Scope and reuse

The complete inclusion interval is **216877934–216921133 inclusive**, epoch 4793,
43,200 numerical height slots. Reuse the 100 validated pilot blocks and the saved
canonical closing block at 216921133. That leaves **43,099 missing heights**,
216878034–216921132 inclusive. Revalidate original captures and freeze their
paths/hashes in the new manifest; do not copy or overwrite them. Numerical slots
are not an assumed produced-block count.

| Control | Height | Hash |
| --- | ---: | --- |
| Opening parent, excluded from debit sum | 216877933 | `FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2` |
| A, first included block | 216877934 | `HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG` |
| Saved pilot tail | 216878033 | `4Uyi9g22QYaxGgE8YBe5Y3SbmipqLRJa8CMHoExv2sEs` |
| Canonical closing block, included | 216921133 | `2Q7yUNdaLfnTkWduSkMYJfueFFg7dgHYpMb4chiS5MZi` |
| B, next epoch boundary, excluded | 216921134 | `J6jyjUSFFatXnCKEG3nKaD9qQLzQrY4xWyFkB5a5mJHB` |

The closing block is the validated `epoch-044-block` RPC capture in
`results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4/`.
Its body SHA-256 is
`c7192b4a9aaa04e937cd8e2024470be70cd36d00208ddf5da97be647302fd2af`.
It has the same epoch/next-epoch IDs and shard order as A. Match its complete
normalized header/chunk manifest and timestamp, and verify the last newly
retrieved produced block links to its saved predecessor hash/height. Saved B's
predecessor also identifies this closing hash. No new closing-control request is
needed. This supplies an independent RPC chain endpoint absent from the small
pilot; it is not independent validation of every chunk's runtime statistics.

## Measured baseline and estimates

The pilot downloaded 99 new headers with 99 zero-body redirects: 198 HTTP
requests, 1,937,585 response-body bytes and 385.888691542 seconds wall time.
Mean archive latency was 0.903844044535 seconds; mean redirect latency was
0.903429764778 seconds. Mean header size was about 19,571.57 bytes; observed
minimum/maximum were 17,444/21,365 bytes and p95 was 20,987 bytes.

| Remaining acquisition option | First-pass HTTP requests | Estimated elapsed time |
| --- | ---: | --- |
| Existing sequential base → archive, one-second pause after each response | 86,198 | 46.67 hours at measured wall time per height |
| Direct verified archive, sequential, same one-second pause | 43,099 | 22.79 hours at measured archive latency |
| Base → archive, four workers, global 120 requests/minute | 86,198 | 11.97-hour request-scheduling floor; actual longer |
| Direct archive, four workers, global 120 requests/minute | 43,099 | 5.99-hour request-scheduling floor; planning range 6–8 hours, unmeasured |

The advertised 180 requests/minute ceiling would imply a 3.99-hour direct-route
floor, not a recommended setting or a measured throughput. At four workers the
pilot mean latency permits the proposed two starts/second, but long-tail latency,
server load, connection setup, local persistence and pauses can make it slower.
Use a pooled HTTPS client to reuse connections if supported; no speedup from
connection reuse is assumed in the estimates.

Remaining response bodies at the pilot mean would be **843.5 MB** (decimal).
Using the observed p95 for every remaining response gives 904.5 MB; using the
pilot maximum gives 920.8 MB. These are scenarios, not bounds or confidence
intervals. A two-times-mean scenario is 1.69 GB; four-times mean is 3.37 GB.
Responses elsewhere may be larger, even within the same epoch.

The measured archive-hop files imply about **943.2 MB logical raw files** for
the remaining range, including request/metadata files at pilot proportions.
The current per-height four-file layout would create 172,396 files plus
directories. On the pilot filesystem, its allocated-file footprint extrapolates
to about **1.44 GB**, excluding directory overhead and derived reports. These
are filesystem-dependent estimates. Repeating result 85's verbose rows would
add roughly 0.29 GB; prefer indexed, bounded checkpoint files and a compact final
summary over repeatedly embedding the whole chain. Existing captures stay
outside the checkout and dashboard runtime. No raw archive should be committed
without a separate retention/storage review.

## Documented options

The official [README](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/README.md)
documents free anonymous access, 180 requests/minute/IP, `/headers`, possible
archive routing and potential throttling under excessive parallelism. The
[server routing implementation](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/src/api.rs)
selects a host by height range and preserves `/headers`. The saved 99 pilot
redirects already establish `a3.mainnet.neardata.xyz` for that prefix. Direct
requests to this verified archive remove repeated front-door routing; ownership
of the remaining range is still subject to response validation. An unexpected
redirect stops collection rather than authorizing a new host or fallback.

The official [fetcher](https://github.com/fastnear/libs/blob/main/neardata-fetcher/src/fetcher.rs)
implements bounded worker counts and `.tgz` archive synchronization. Its reviewed
[constants](https://github.com/fastnear/libs/blob/main/neardata-fetcher/src/utils.rs)
use **10 heights per archive**; the server's archive grouping is configurable.
For this range, a ten-height layout would intersect 4,321 archives for the whole
interval, or 4,311 for the still-missing range. It would download full block
documents and some already saved/out-of-range records, not just headers.
The client's archive-host boundaries do not reproduce our verified a3 routing,
and the pinned server's application routes do not establish current public
`/raw/` hosting. Public availability, deployed grouping, compressed/expanded
size and response limits for these objects remain unverified. Archive fetching
is therefore an alternative requiring a separate bounded pilot, not an
immediately supported lower-volume replacement. R2 configuration is restricted
to older heights and carries a separate authentication/rate-limit warning.
The stock fetcher also retries until success and interprets nulls as skips;
those behaviours do not meet this investigation's preservation/coverage rules.

## Recommended bounded design

Recommend direct verified-a3 `/headers` requests, at most **four in flight**,
with one shared limiter for all workers, sessions and allowed hosts: at most
120 starts in any rolling 60 seconds, at least 0.5 seconds between starts and no
burst allowance. Count every HTTP attempt, including errors and any redirects;
other clients on the same IP consume the provider's allowance too. Do not shard
limits by hostname or worker. HTTP 429 stops with evidence; no automatic retry.

These are proposed new limits requiring implementation/review; the pilot's
64 MiB/198-request limits remain unchanged:

- First pass: at most 43,099 new HTTP requests, one per missing height. Lifetime:
  at most 86,198 new requests, two manually initiated attempts per missing height.
  The pilot's 198 completed requests remain separately recorded (86,396 combined
  maximum). No successful height is fetched again. No automatic fallback or retry.
- At most 4,096 requests per invocation, with durable checkpoints at least every
  1,000 accepted heights. A proposed initial optimized segment stops after 1,000
  new heights so direct-route/concurrency behaviour can be reviewed before the
  rest. This segment is part of the same interval, not duplicate collection.
- Retained response bodies, including errors/partials/drafts: 2 GiB across the
  new collection and all resumes; total new store: 8 GiB. Neither cap increases
  automatically. Reserve capacity for every in-flight response so concurrency
  cannot overshoot the cap. Keep the original 32 MiB response guard, 15-second
  connect deadline and 60-second request deadline. Require 10 GiB free before
  starting and stop scheduling if free space falls below 2 GiB.
- One coordinator owns counters, checkpoint publication and the external-store
  lock. Retain exact request/response bytes, URL, UTC and monotonic timestamps,
  HTTP status/headers, body-completeness status, length and SHA-256 for each
  attempt. Publish files atomically/exclusively; preserve interrupted drafts.
- Validate each response's schema/identity before accepting it. Buffer at most
  16 ahead-of-chain results and advance the validated prefix in height order.
  On a failure stop scheduling; retain and validate already in-flight captures
  without accepting an unexplained gap. On resume recheck the frozen plan, seed
  and capture hashes and reuse every valid response, including those beyond a
  checkpoint. No overwrite or full-store rescanning per fetched block.
- Allow only verified HTTPS a3 URLs with the exact requested height and
  `/headers` path, no credentials, query parameters or automatic redirects.
  Unexpected routing, HTTP errors, unavailable history, invalid/ambiguous data,
  conflicting identity or cap exhaustion stops. Any recovery is separately
  invoked within the same lifetime counters.

## Coverage and arithmetic acceptance

Retain every requested height's outcome. An HTTP-200 literal null remains
unresolved until the next produced header bypasses exactly that height and links
to the previous accepted hash/height. Keep the small pilot's conservative rule:
one in-range successor probe, then stop on consecutive or unsupported nulls.
404s, missing responses and transport failures never establish skipped blocks.
The saved closing control may witness the last gap; do not request past the
range. Keep skip amounts null and distinguish produced count from slot count.

Every produced header must remain in A's saved epoch/next-epoch scope and match
the protocol-86 ten-shard ordered layout. Do not use advertised
`latest_protocol_version` as an active-version measurement. Unexpected epoch,
layout, schema or required-semantic changes stop; do not generalize the current
normalizer across upgrades. Preserve exact u128 monetary strings, nanosecond
timestamps, predecessor IDs, chunk creation/inclusion IDs, mask and counts.
Check duplicates, complete manifests, carried-header equality and delayed-chunk
creation ancestry. Sum `balance_burnt` only for `height_included == block.height`;
carried headers are excluded without dropping newly included observations.

With canonical endpoint linkage and complete inclusion coverage, independently
sum net debits and test, with **zero integer-yoctoNEAR tolerance**:

`S_B_parent = S_A_parent + protocol_validated_reward_mint_at_A − summed_net_debits`.

The saved endpoint movement is **+26,624.788099202759864197967723 NEAR** and A's
validated reward mint is **26,971.051860538713462297967723 NEAR**. Their difference,
**346.2637613359535981 NEAR**, is currently an **implied interval net debit**.
It must not be inserted as a missing chunk amount or used to accept an incomplete
range. Preserve discrepancies and incomplete totals explicitly. Reuse A and its
small-pilot debit once; do not add overlapping boundary/pilot subtotals twice.

## What completion would establish

Successful acquisition and validation would complete the observed net-header
accounting identity for **one entire epoch inclusion interval**, [A, B), rather
than just 100 blocks. It would combine independently recorded and historically
validated reward minting, exact supply endpoints and independently summed net
header debits. Net header debit combines gross burn and subsidies; it does not
separate actual gross supply burn from subsidy issuance. Thus even an exact
identity does not complete the requested gross-component accounting.

For 21–27 September, result 72 already covers all 23 reward application events,
but the other inclusion blocks, including partial epochs at the weekly edges,
still need independent header/debit coverage. Match weekly canonical cuts and
deduplicate shared captures by their verified identities. The eight-week target
(24 August–18 October, with 23 August closing baseline) additionally needs its
remaining exact weekly endpoint headers, actual epoch census, offset reward maps
and active historical configuration coverage, plus all inclusion manifests.
Do not extrapolate fixed epoch lengths or the pilot's byte sizes. Gross burn and
subsidies require retained runtime breakdowns beyond these public headers and
remain unavailable until independently measured. The eight-week reconciliation
stays open.
