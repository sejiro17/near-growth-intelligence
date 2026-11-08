# Neardata contiguous header pilot: first 100 height slots

[Result 83](../results/83_neardata_canonical_block_A_comparison_2026-09-23.json)
establishes one exact historical block document and reviewed archive routing.
[Result 84](../results/84_neardata_contiguous_header_pilot_plan.json) prepares
the next bounded measurement. No pilot requests have been executed in preparation.

The full A→B target remains **216877934–216921133 inclusive**, 43,200 numerical
height slots. The first pilot is **216877934–216878033 inclusive**, at most 100
slots. Produced-block counts are not assumed. Block A and its opening predecessor
216877933 are reused from verified saved evidence. Other valid in-scope saved RPC
block responses are indexed, with checksums and identity checks; conflicting
saved identities stop preparation. Currently A is the only cached pilot block,
so 99 heights may require new retrieval. The opening predecessor is not fetched
or included in the debit sum.

## Rate, routing and request bounds

The official [Neardata README](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/README.md)
documents **180 requests/minute per IP** and the smaller
`/v0/block/{height}/headers` response, which returns the block envelope directly.
The collector waits **one second before each HTTP request, after the previous
response**, and runs sequentially. That keeps this collector below roughly
60 requests/minute, including redirects, without inheriting the legacy archival
RPC's 65-second pause. Other clients sharing an IP can consume the same quota;
HTTP errors stop rather than trigger retries or increased caps.

Each missing height first requests:

```text
GET https://mainnet.neardata.xyz/v0/block/{height}/headers
```

At most one 302 may be followed, only to the exact same height and `/headers`
path on the already verified HTTPS host `a3.mainnet.neardata.xyz`. The pinned
[server implementation](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/src/api.rs)
constructs archive URLs and preserves the `/headers` suffix through
`redirect_or_map`. No other host, query string, userinfo, port, fragment, path,
height or HTTP downgrade is accepted. A second redirect stops and remains saved.
Fresh request headers send no Authorization, Cookie, Referer or API key; no
response cookies or environment credentials are forwarded. TLS certificate and
hostname verification remain enabled.

There are at most **198 HTTP attempts per invocation**, 99 uncached heights
times two hops. There is **one attempt per missing height per invocation**,
without automatic retry. A second, explicitly invoked manual run may make one
additional attempt at an unsuccessful height; the lifetime cap is two attempts
per height and at most 396 HTTP attempts overall. Successful blocks are reused,
not requested again. The full interval is disabled by a hard 100-slot scope check
and has no collection flag.

Connection and request deadlines remain 15 and 60 seconds. Each response has a
32 MiB body guard. A separate **64 MiB retained response-body budget across all
attempts and resumes** bounds this pilot. Failed/partial bodies and interrupted
body drafts consume that budget. No cap is automatically increased; cap-detection
partial bytes remain evidence.

## Chain, monetary and chunk checks

Required source values include exact u128 monetary strings, integer nanosecond
timestamps, height/hash/predecessor height/hash, epoch IDs, mask and inclusion
count, and the full ordered ten-shard chunk-header manifest. FLOAT values,
nonfinite numbers, duplicate JSON keys, missing fields, inconsistent types,
conflicting hashes and invalid ordering are rejected. All pilot blocks must stay
in A's reviewed epoch and configuration scope.

Each produced header must link to the previous produced header through both
`prev_height` and `prev_hash`, with increasing timestamps. The chain starts at
the saved canonical parent and A. The pilot tail has no independent saved
canonical tip control, so successful continuity is an observed Neardata chain,
not an independently verified census. A later full A→B acquisition must also
match the already saved B-parent hash at height 216921133.

A literal HTTP-200 JSON `null` is retained as **unresolved**, not a skipped block
or a zero monetary amount. One bounded successor probe inside the 100-slot window
is allowed. A skip is accepted only when that produced successor's predecessor
height/hash exactly bypasses the null slot and links to the last produced block.
The null capture and successor identifiers are recorded together. Two consecutive
nulls, a trailing null without an in-window witness, an unexplained predecessor
jump, HTTP 404/history errors or partial responses stop. Nothing outside the
pilot is fetched to explain a gap. Already ambiguous null responses are not
blindly re-requested on resume.

For each manifest:

- The shard order, unique chunk hashes, mask and `chunks_included` count must
  agree. A carried-forward header must equal the corresponding predecessor
  manifest entry and is excluded from this block's debit.
- A new inclusion is counted only when `height_included == block.height`.
  Repeated chunk hashes with changed fields are conflicts, not a deduplication
  shortcut. New chunk hashes are not globally discarded.
- Fresh chunks must identify the immediate predecessor. Delayed chunks retain
  their earlier creation predecessor, which can differ from the inclusion
  predecessor. In-scope unexplained references stop; creation predecessors
  outside saved scope remain explicit coverage limits without extra retrieval.

Only accepted produced blocks contribute to the independent inclusion-timed net
header sum. Skipped-slot rows retain null monetary fields. A partial pilot has
an observed prefix subtotal but no complete pilot debit total.

The same-epoch historical constructor path is checked by
`S_current = S_previous - newly_included_net_header_debits`; it has no new epoch
reward-mint input. Block A's independently recorded/protocol-validated reward map
comes from result 72, not a balancing supply difference. A complete pilot also
checks opening parent supply plus that reward mint minus the pilot header sum
against the last produced supply, with zero integer discrepancy. Gross burn,
subsidies and weekly net debit remain unavailable. Overlapping block A is not
added again to the earlier 23-boundary debit total.

## Resumption and evidence retention

The [collector](../analysis/36_neardata_header_pilot.py) uses an exclusive
process lock. Its store manifest freezes plan 84, source hashes and seed records.
Every height attempt and response hop gets a new directory. Request HTTP bytes,
request description, raw response, HTTP status/headers, endpoint, UTC retrieval
times, monotonic request duration, byte lengths and SHA-256 are saved. Each
response is validated before another height is attempted.

Completed files are published atomically and exclusively. Interrupted drafts
remain preserved, and completed valid captures can be revalidated/reused even
if the previous session stopped before producing a report. HTTP/transport
failures may be retried only by a separate manual invocation, within the two-
attempt cap. Corrupted evidence or conflicting/invalid data stops before further
requests. No old capture or session report is overwritten. Resume does not
silently change a frozen plan, accept unexplained gaps or extend the interval.

## Raw storage and benchmark gate

New raw files are outside the repository and dashboard runtime:

```text
../near-growth-intelligence-evidence/
  neardata_headers_216877934_216921133/
    pilot_216877934_216878033/
      manifest.json
      attempts/<height>/<01-or-02>/hop-00|hop-01/
      sessions/<invocation>/started.json
      sessions/<invocation>/finished.json | stopped.json
      sessions/<invocation>/validation.json
```

The 64 MiB payload budget includes retained response bodies and body drafts.
HTTP request/metadata files, their interrupted drafts, store manifests and derived
reports require additional disk space. Logical raw-store size is
reported separately from network-body bytes. Validation reports are excluded
from their own raw-input footprint so reproduction is stable; no raw files are
staged or copied into dashboard data paths. Any later proposal to commit or
distribute captures or reports must first review their measured size and retention.
Plan 84 can remain in the repository; future result 85 is a derived validation
artifact, not a raw archive.

The benchmark records actual downloaded bytes including failed attempts, body
size minimum/maximum/p95 for non-null HTTP-200 documents, transport time, bytes
per transport second, session wall time including pacing/local checks, bytes per
wall second, request counts and logical storage. Cached A contributes no new
download bytes. Interrupted sessions retain unknown wall-time status rather
than invented throughput. Full-interval volume/throughput projections remain
null until actual pilot measurements and coverage are reviewed. The 191,778-byte
full-block response in result 83 is not used to estimate the smaller headers
endpoint or the remaining interval.

## One next manual command

```bash
.venv/bin/python analysis/36_neardata_header_pilot.py collect
```

The same command explicitly resumes the same external store. It does not start
the full interval. `validate` is offline and prints the current report from saved
inputs; an alternate external store may be supplied with `--store`. After manual
capture, the intended validation filename is
`results/85_neardata_header_pilot_validation_216877934_to_216878033.json`.
An unused `--output` may be passed to the offline validator; existing exports
cannot be overwritten.

Focused tests use synthetic blocks and block live networking. They cover the
100-slot/198-request limit, saved-block reuse, one-second pacing, explicit resume,
attempt/session/body caps, legitimate and unexplained gaps, trailing nulls,
carried/delayed chunks, conflicting identities, bad precision/types, hash
tampering, interrupted drafts and immutable evidence.
