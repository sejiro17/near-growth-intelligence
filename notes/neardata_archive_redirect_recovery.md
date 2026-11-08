# Neardata archive-routing recovery for block A

The saved pilot
`results/neardata_supply_block_pilot_2026-09-23/20261107T154218Z_8ca556d6bf23`
contains a complete HTTP 302 response, not a transport failure or an absent block
document. Request bytes, descriptor, metadata and zero-byte response match their
recorded hashes and lengths. The original manifest matches frozen result 81.
Its only `Location` is:

```text
https://a3.mainnet.neardata.xyz/v0/block/216877934
```

The first collector stopped at its original redirect guard. The empty redirect
body supplies no monetary or historical-retention measurement. The subsequent
manual archive response now validates as
[result 83](../results/83_neardata_canonical_block_A_comparison_2026-09-23.json):
complete HTTP 200, exact canonical block-A identity and all ten exact chunk
net-debit fields. Its five newly included chunks sum to
0.002206853430760200000000 NEAR with zero-yocto discrepancy. Both hops and the
original capture remain unchanged; the report reproduces the saved validation
byte-for-byte. This proves one historical point, not bulk or weekly coverage.

## Official mechanism and destination verification

The official [Neardata README](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/README.md)
documents archive-owner redirects on finalized `/v0/block/:height` requests,
the mainnet base and credential-free access. The pinned
[implementation](https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/src/api.rs)
has `check_archive_redirects`: it chooses an archive index from the configured
height boundaries and emits HTTP Found with
`https://a{index}.{domain_name}/v0/block/{height}`. `redirect_or_map` preserves
that route for the full block document. The constructor's cache duration is
86,400 seconds, also present in the saved response.

Reviewed commit: `7324d9131e7e8285306606ba05822b007e44c53a`.
Git blob IDs are `16fdd9ce6e866395e96245016731eb1a2524ed6f` for `src/api.rs`
and `4e3540252225ac19e48c95fdfdad2ccbdda984c1` for `README.md`.
Current [overview documentation](https://docs.fastnear.com/neardata) also
discusses redirects, while the pinned server source establishes the archive
route specifically.

The saved Location fits this implementation with index 3, retains HTTPS, remains
within the documented mainnet domain and preserves the exact requested block
path. This supported following that particular route. Production archive boundary
configuration and the exact deployed binary remain unestablished; the subsequent
capture establishes availability for this one block. The recovery retains default
certificate and hostname verification. It does not whitelist arbitrary `aN`
hosts, an entire domain suffix or URLs merely resembling the verified URL.

## Bounded manual procedure

[Analysis 35](../analysis/35_recover_neardata_archive_redirect.py) and
[result 82](../results/82_neardata_archive_redirect_recovery_plan.json) prepare
one additional GET to the exact URL above. The original mainnet hop is reused;
it is not requested again. The collector and frozen plan 81 remain unchanged.

The completed manual capture used:

```bash
.venv/bin/python analysis/35_recover_neardata_archive_redirect.py recover \
  --original-run-dir results/neardata_supply_block_pilot_2026-09-23/20261107T154218Z_8ca556d6bf23
```

Saved recovery directory:

```text
results/neardata_supply_block_pilot_recovery_2026-09-23/20261107T154218Z_8ca556d6bf23_recovery_01/
  run.json
  hop-00-original/             # exact copies of all six original files
  hop-01-archive/
    block-A.request.http
    block-A.request.json
    block-A.response.body
    block-A.metadata.json
  validation.json             # only after successful comparison
  stopped.json                # only on failure
```

All original files stay byte-for-byte unchanged. Their hashes and copied bytes
are rechecked before the combined report is accepted. Directory creation and
file writes are exclusive; re-invoking the command against that recovery path
refuses before another request.

The archive hop uses a private instance of the original HTTP transport with
only Host/URL changed to the verified destination. Block 216877934, GET method,
65-second spacing, 15-second connection timeout, 60-second request deadline and
32 MiB response limit remain unchanged. Combined response-body bytes across both
hops are also limited to 32 MiB; the original body contributes zero bytes.

Only freshly constructed Host, Accept, Accept-Encoding, Connection and User-Agent
headers are sent. No Authorization, proxy credentials, Cookie, Referer, query
key, environment credential or previous response header is forwarded. No
cookies are acquired or replayed. The response's CORS credentials permission
does not require the client to send credentials.

There are at most two retained response hops including the original, and one
new HTTP attempt. A second redirect is saved and stops recovery, even if its
destination looks like another archive host. No destination is dynamically
added to the allowlist. Queries, fragments, userinfo, ports, altered paths,
different heights, HTTP downgrades and deceptive host suffixes are rejected.
There are no automatic retries, provider fallback or further block requests.

## Validation and limits

The archive response must be complete HTTP 200. Raw request/body bytes, HTTP
status and headers, URL, UTC retrieval times, lengths and SHA-256 are retained.
Any further redirect, authentication error, partial response, null document or
canonical identity mismatch is preserved with a stop record. No valid result
or zero amount is substituted.

Successful responses use the original block-A comparison: exact hash, height,
predecessor, epoch IDs, nanosecond timestamp, total-supply string and ordered chunk
identities. Any available exact net-debit fields must match the saved canonical
values; missing fields stay unavailable. Only newly included chunk headers enter
the net-debit sum. This neither separates gross burn/subsidies nor establishes
bulk retention, weekly coverage or eight-week reconciliation.

Offline commands are `plan --original-run-dir <original-directory>` and, after
manual capture, `validate --run-dir <recovery-directory>`. The latter reproduces
the new `validation.json` without source requests.

Focused tests block live networking and use synthetic archive responses. They
check original integrity, one-request scope, strict destination validation,
credential-free headers, unchanged limits, exact preservation of both hops,
canonical comparison, additional-redirect/error stops and overwrite refusal.
