# Bounded optimized Neardata header segment

The collector in [analysis 37](../analysis/37_neardata_optimized_segment.py)
implements the direct-archive option from
[result 86](../results/86_neardata_full_interval_collection_proposal.json).
Only **216878034–216879033 inclusive** is enabled: 1,000 numerical height slots
after the validated 100-height pilot. Full-interval and weekly collection remain
disabled. [Result 87](../results/87_neardata_optimized_segment_plan.json) freezes
the implementation, saved evidence and request/storage limits before execution.

Four workers share one gate: at most 120 request starts in a rolling 60 seconds,
at least 0.5 seconds between starts, with no burst allowance. Recent starts are
restored on explicit resume. Connections may be reused within a worker; failed
connections are not retried. Only anonymous HTTPS GETs to the verified
`a3.mainnet.neardata.xyz/v0/block/{height}/headers` path are allowed. Redirects,
HTTP errors, incomplete transport, invalid data and unexplained gaps stop
collection. No credentials, cookies or fallback hosts are used.

The existing pilot captures and saved canonical closing header are reused by
reference, with their hashes checked. New raw evidence lives outside the checkout:

```text
../near-growth-intelligence-evidence/neardata_headers_216877934_216921133/
  optimized_216878034_216879033/
    manifest.json
    attempts/<height>/01|02/
      request.http
      request.json
      response.body
      metadata.json
    sessions/<invocation>/
      started.json
      checkpoint.json
      finished.json | stopped.json
      validation.json
```

Files are published exclusively and atomically. Interrupted drafts remain
evidence. Resume revalidates all saved attempts and reuses successful responses,
including responses that completed beyond the last accepted prefix. Invalid
schema or conflicting identities require review; they are not retried. A process
lock prevents simultaneous writers to the same store. Metadata preserves URL,
UTC and monotonic retrieval times, HTTP status/ordered headers, lengths and
SHA-256 checksums. Raw request bytes, body bytes, monetary strings and source
array order are retained.

The proposed full-interval limits are implemented without enabling that interval:
at most 4,096 requests per invocation, 86,198 lifetime requests, two explicitly
initiated attempts per missing height, 2 GiB retained response bodies across
resumes and 8 GiB total logical store. The narrower segment also limits each
invocation to at most 1,000 requests. The per-response guard is 32 MiB, with
15-second connection and 60-second request deadlines. Start requires 10 GiB free;
scheduling stops below 2 GiB free. Capacity is reserved for all in-flight response
bodies and metadata before scheduling. Caps never increase automatically.

Up to four requests run concurrently; accepted chain state advances in height
order, with at most 16 ahead-of-prefix results. An in-scope produced successor
must positively support any null-as-skipped classification. Consecutive nulls
and an unwitnessed trailing null stop. Missing responses and HTTP errors are not
skips. Carried chunk headers must agree with their prior observations and are
excluded from the debit sum. Newly included headers retain creation predecessors
and must match inclusion heights, masks, shard order and historical epoch scope.

Validation tests every produced block's supply identity using integer yoctoNEAR,
with zero tolerance. The new segment is within the same epoch and introduces no
new epoch reward mint: segment supply movement plus independently summed net
header debit must be zero. The cumulative identity includes the prior pilot and
A's independently recorded, protocol-validated reward mint once. Gross burn,
subsidies and independent full-epoch/weekly debits remain unavailable. The saved
canonical closing control at 216921133 is outside this segment and is not yet
connected to its tail.

Commands:

```bash
.venv/bin/python analysis/37_neardata_optimized_segment.py collect
.venv/bin/python analysis/37_neardata_optimized_segment.py validate --output results/88_neardata_optimized_segment_validation_216878034_to_216879033.json
.venv/bin/python -m unittest discover -s tests -p test_neardata_optimized_segment.py -v
```

`collect` is the only command that requests chain data. Repeating it is an
explicit bounded resume of this same segment; it does not advance to another
segment. `plan` and `validate` are offline, and output files cannot be overwritten.
The reproducible validation report includes measured runtime, rate audit, body
bytes, raw file sizes, errors, exact accounting and sample-based full-epoch/week
scenarios. Those scenarios are not bounds: other epochs, shard layouts, archive
routes, skipped slots, latency and filesystem overhead may differ. A weekly
acquisition requires a separate reviewed scope and limits; this collector cannot
silently expand into it.

## Saved execution outcome

[Result 88](../results/88_neardata_optimized_segment_validation_216878034_to_216879033.json)
reproduces the stopped run offline. The 1,000-height segment is **incomplete**:
44 successful blocks cover 216878034–216878077. After 22.665232459 seconds,
45 responses had been retained: 44 HTTP 200 and one HTTP 429 at height
216878078. Downloaded bodies total 857,247 bytes, including the 137-byte error
body. There were no recorded transport errors. Of 48 scheduled attempt
directories, three contain request files without response/metadata files;
scheduled attempts are not the same count as recorded HTTP responses.

The actual 429 body states `rate-limit exceeded of 30 blocks per minute`.
Its `Retry-After: 0` did not trigger a retry. The limiter audit shows a minimum
500,126,125-nanosecond start gap and at most 45 starts in this session's rolling
60-second window, below the configured 120. Thus the public 180-request/minute
description did not establish this route's enforced free block allowance.
The response does not establish the exact bucket algorithm, shared-IP use or
guaranteed sustainable throughput. Collection stopped; no fallback, retry,
subscription or limit change occurred.

The valid prefix independently sums **0.1220740481414838 NEAR** of net header
debit and the exact supply movement is **−0.1220740481414838 NEAR**, giving zero
integer-yoctoNEAR discrepancy. Across the prior pilot and this prefix, 144 blocks
sum **0.5486610196812742 NEAR**, with zero cumulative mint/supply/debit discrepancy.
There are 956 unvalidated segment heights. Complete-segment, epoch and weekly
debit totals remain unavailable, as do gross burn and subsidies.

[Result 89](../results/89_neardata_optimized_prefix_rate_limit_assessment.json)
records the raw error, counters, exact arithmetic and revised scenarios. It is
an assessment of a 44-block prefix, not a completed 1,000-height benchmark.

| Remaining scope | Request slots before other saved reuse | 30 blocks/minute scheduling floor | 25/minute scenario, unverified | Bodies at prefix mean |
| --- | ---: | ---: | ---: | ---: |
| A→B, reusing prefix and canonical closing header | 43,055 | 23.92 hours | 28.70 hours | 838.7 MB |
| 21–27 September, subtracting known prefix and epoch closing only | 1,002,441 | 556.91 hours | 668.29 hours | 19.53 GB |

The successful responses average 19,479.77 bytes (17,931–21,112 observed).
Remaining epoch raw files extrapolate to 943.2 MB logical / 1.43 GB allocated
on this filesystem; the weekly scenario gives 21.96 GB logical / 33.22 GB
allocated, before directory overhead and reports. A twice-/four-times-mean body
scenario gives 1.68/3.35 GB for the epoch and 39.05/78.11 GB for the week. These
are conditional size/rate scenarios, not bounds or verified sustainable service.
Other saved headers can reduce requests. The observed two-starts/second prefix
ended in rejection and cannot support the earlier six-hour sustained forecast.
Weekly volume would exceed existing caps; none were increased.

A slower recovery needs a separately reviewed frozen plan preserving the
original attempts and reusing every valid response. The current `collect`
command retains its original 120/minute plan and must not be used as an
automatic response to the 429. No recovery was executed.

## Collection status

**Bulk collection is paused. Do not retry, rotate hosts/IPs, increase caps or
start a slower recovery.** Results 88–89 and raw captures remain unchanged. The
validated interval is 216877934–216878077 inclusive, 144 blocks including the
earlier pilot. The prefix's net debit is not extrapolated. Full-epoch and weekly
independent debit, gross burn and subsidy accounting remain incomplete. The
throughput/volume scenarios above are historical feasibility assessments, not
an active collection plan.
