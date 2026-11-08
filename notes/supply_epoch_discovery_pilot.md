# Bounded weekly epoch discovery: 21–27 September 2026

This pilot enumerates observed epoch application boundaries and saves their
offset reward responses. It does not collect intervening chunk headers or
independently measure weekly net debit, gross burn or subsidies. Existing
weekly endpoints and the validated single-boundary monetary pilot are reused.

## Historical implementation and public method limits

The reviewed implementation is nearcore 2.13.3, commit
[`5af9ca74631e6cf0dae33e77d1a632e94d2952ce`](https://github.com/near/nearcore/releases/tag/2.13.3),
released 4 August 2026. The saved A/B historical configurations establish
protocol 86 at those application blocks. Other discovered epochs' active
protocol configurations are not inferred from the producer's
`header.latest_protocol_version` vote.

| Source | Supported interpretation |
| --- | --- |
| [`types.rs`, epoch identifier](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/types.rs#L534) | An epoch E's ID is the last block hash of E−2. Consequently a header's `next_epoch_id` identifies both epoch E+1 and, as a block hash, the last block of E−1. The method parameter determines which meaning is requested. |
| [`EpochValidatorInfo`](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/views.rs#L2594) | `epoch_start_height` and `epoch_height` describe the requested epoch. Its reward map contains rewards earned in E−2 and applied at the first block of E−1. It does not expose a previous-epoch ID. |
| [Epoch-manager response construction](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/lib.rs#L1314) and [stored start lookup](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/lib.rs#L1752) | The response uses retained epoch metadata and the stored actual start height, rather than a duration extrapolation. The server's internal next-epoch information is not exposed as a previous-ID field in the response. |
| [Public dispatch and debug-route gate](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/jsonrpc/src/lib.rs#L2992) | `validators` is a public JSON-RPC method. `epoch_info` appears in optional `/debug/api/epoch_info/{epoch_id}` HTTP routes behind `enable_debug_rpc`, which defaults false. This implementation does not establish a public JSON-RPC method named `epoch_info`. |
| [Debug response shape](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/client-primitives/src/debug.rs#L28) | Debug epoch views can contain an epoch ID, height, optional first-block hash/time, validator information and protocol version. They do not expose a direct previous-ID chain. Availability and historical retention on the public endpoint are not established. No debug request is included. |
| [Reward calculator](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/reward_calculator.rs#L48) | In the reviewed populated-validator branch the complete validator/treasury reward sum supplies epoch reward minting. A missing map or exceptional empty-validator branch must not become zero issuance. |

The current [validators documentation](https://docs.near.org/api-reference/post-validators)
establishes the public request/response interface; historical implementation
supplies the payout offset. The public [block method](https://docs.near.org/api/rpc/block-chunk)
supports exact hashes and heights. The official
[provider list](https://docs.near.org/api/rpc/providers) lists
`https://archival-rpc.mainnet.near.org` as public, archival and severely rate
limited. Availability of the specific epoch history remains unverified until
manual collection. A local database reader or optional debug route is not proof
of public availability.

## Initial anchors and algorithm

Saved closing block 217555961,
`5VLWBqYvC98Q5qUzbQ8nHN1wcGZ9CnLxShZgojz4ohUa`, supplies:

- Closing epoch E: `8sJjEAeKkjwYRCLVGVf5usUt8tPZh3TkWT1YrBp345u8`.
- Successor reward-response epoch: `6BnXKEWs1VGEdZFhRE6v3dMnzpnNH8Pz2qFyVJ7sfaRT`.

The opening anchor is saved 20 September closing block 216553375,
`5sUCEyrF5p3RZvx5DzE6zD4gtknwHf8kMmHnH7ViGPWk`. Its epoch
`QfvBtUDeixTQpGVPh8cXVpBoJnUtzeJj9fYFNveHiTX` is the stopping sentinel.
Its issuance application predates the opening header; it is excluded.

For each epoch E, newest first:

1. `validators`, `{"epoch_id": E}` obtains its actual start height H and epoch
   ordinal. The first request uses the closing epoch ID above.
2. `block`, `{"block_id": H}` obtains the application header. Check its epoch,
   successor ID, actual height and nanosecond UTC timestamp. Require application
   inside `[2026-09-21T00:00:00Z, 2026-09-28T00:00:00Z)` and no later than the
   saved closing anchor.
3. `block`, `{"block_id": first_header.prev_hash}` obtains the actual parent.
   Check hash, `prev_height`, timestamp ordering and transition identities:
   parent epoch differs, parent `next_epoch_id == E`, and the parent's hash
   equals E's `next_epoch_id`. The parent's `epoch_id` supplies the preceding
   epoch. Numerical height adjacency is not required.
4. The reward response for E's application is `validators` of E's
   `next_epoch_id`. Fetch this once for the newest E. For every earlier E it is
   the metadata response already obtained for its successor. Require successor
   ordinal exactly E+1 and its actual start to match the already visited next
   boundary; the newest successor's start must be after the closing anchor.
5. Continue from the parent header until its epoch matches the opening anchor's
   epoch. Check its successor ID and endpoint ordering against that anchor.
   Reject a different epoch whose first block falls before the window instead
   of silently accepting a partial walk.

Every returned reward-map amount remains an unsigned integer yoctoNEAR string;
array order and all original response bytes are retained. No selected validator
subset, fixed epoch duration, configured inflation rate or supply-sign filter
defines the census. The UTC interval itself has exact integer boundaries.

The observed adjacent transitions plus the opening-epoch sentinel establish
the RPC-derived census. They do not provide an independent chain proof or prove
that the original exported endpoint was the final canonical block of its day.
`validators` does not echo the requested epoch ID; identity is bound by saved
request bytes, the documented method contract, consecutive epoch ordinals,
first-block epoch IDs and adjacent boundary checks, rather than an invented
response identity field.

## Existing controls, request budget and stop conditions

The complete walk must encounter both saved 23 September boundaries:

- A: 216877934 / `HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG`.
- B: 216921134 / `J6jyjUSFFatXnCKEG3nKaD9qQLzQrY4xWyFkB5a5mJHB`.

Their exact timestamps, A's parent and the complete A reward map are already
saved. The response requested for B's epoch has `epoch_height=4794` and
`epoch_start_height=216921134`, while its reward map applies at A, not B.
This is an explicit regression control for the response offset.

For K application epochs, the discovery sequence requires **3K+1** requests
before cache reuse. Four mandatory calls are already saved: A's first block,
A's parent, B's first block, and the `validators` response for B's epoch.
Thus a successful complete walk requires at most **3K−3 new requests**; the
actual count can be lower if any request identities alias. Saved A/B protocol
responses are reused locally and add no requests. The cache indexes blocks by
verified hash and height, ignores JSON-RPC ID differences for semantic reuse,
and rejects conflicting retained responses. No already cached semantic request
is fetched again.

The operational ceiling is **32 application epochs**, with a hard transport
ceiling of **97 requests**. With the four required reuses a successful complete
walk has an upper bound of **93 new requests**. These are safety bounds, not
an epoch-count estimate or extrapolation of epoch lengths. Reaching either cap
before the opening sentinel yields an incomplete capture, not a zero total.

Collection also stops on HTTP/RPC errors, unavailable history, missing/empty
reward maps, noninteger monetary values, transport truncation, duplicate JSON
keys, conflicting cached identities, cycles, nonconsecutive epoch ordinals,
bad boundary dates, parent-link disagreements or a missing A/B control. A
failure preserves raw bytes and a `stopped.json` report with unavailable totals.
There are no retries, fallbacks, automatic resumes or cap increases. The
collector refuses to start over if its output root already contains an attempt.

## Interpretation and remaining monetary coverage

Successful discovery retains the complete returned reward maps and their exact
sums, application identities and times, response epochs and earned-epoch
ordinals. It does not establish independent server-side completeness of map
entries beyond the method contract and saved A control.

Only the saved A/B protocol configurations are reused. Other epochs' protocol
coverage remains unverified; no additional configuration requests are bundled
into the discovery pilot. Therefore the aggregate is labelled a **recorded
reward-map sum**, while independently identified weekly epoch reward minting
remains null unless historical applicability is verified for every row.
Exceptional or incomplete monetary evidence cannot be filled with zero.

Even after complete issuance identification, `issuance − supply movement`
would be an **implied net debit**, not an independent debit measurement, actual
burn or a completed reconciliation. The report exposes this value only when all
rows pass its protocol checks and labels its derivation explicitly. Gross burn,
subsidies, gross issuance including subsidies and independent weekly net debit
remain null. No intervening inclusion-timed chunk evidence is collected here.

## Manual command and offline validation

The reproducible plan is `results/67_supply_epoch_discovery_pilot_plan.json`.
From the repository root, manual collection is:

```bash
.venv/bin/python analysis/26_supply_epoch_discovery.py collect
```

The collector prints a new directory under
`results/supply_epoch_discovery_2026-09-21_to_2026-09-27/<UTC>_<unique-id>/`.
It preserves exclusive request JSON, raw response bodies and metadata files
containing endpoint, HTTP status/headers, retrieval UTC times, byte lengths and
SHA-256 hashes. It uses the existing 65-second spacing, 15-second connection
timeout and 60-second request deadline. Responses are sequential and no debug
endpoint, fallback provider or source query is contacted.

On success, `validation.json` records the boundary list, reward maps, null
safeguards, actual new-request count, reused response paths and input hashes.
The same report can be regenerated offline:

```bash
.venv/bin/python analysis/26_supply_epoch_discovery.py validate --run-dir <capture-directory>
.venv/bin/python analysis/26_supply_epoch_discovery.py plan
.venv/bin/python -m unittest discover -s tests -p test_supply_epoch_discovery.py -v
```

Plan/validate default to stdout; optional `--output` refuses overwrites. The
focused tests block the HTTPS constructor and use synthetic transports only.
They cover variable epoch spans, skipped block heights, payout offsets,
missing/nonfinite monetary fields, boundary/control disagreements, caps, cache
reuse, raw-checksum failures, saved HTTP/RPC errors and offline replay. Synthetic
responses exist only in temporary test directories and are not research evidence.
