# Stopped epoch discovery: audit and manual recovery

The source capture is
`results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4`.
Its original manifest, stopped report and all request/response bytes are retained.
Analysis 26 and result 67 remain unchanged, preserving the original code/input
fingerprints. Analysis 27 adds an offline audit and separate manual recovery
stages; it reuses the original epoch validator rather than changing its scope.

## Validated evidence and incomplete coverage

All 53 request/response pairs pass byte-length and SHA-256 integrity checks,
including the failed capture's zero-byte response. The first 52 have HTTP 200,
complete transport and valid matching JSON-RPC envelopes: 19 `validators`
responses and 33 block responses. Exact monetary fields, validator IDs, block
request identities and saved metadata validate offline. The original discovery
walk reproduces the 77 successful-response lookup entries in `stopped.json`
exactly before reaching the failed request.

There are 18 fully validated application boundaries, epoch ordinals 4808 down
to 4791, with their adjacent parent links and offset reward responses:

| Coverage point | Height | UTC application timestamp, seconds shown |
| --- | --- | --- |
| Newest validated boundary | 217525934 | 27 September 2026 19:02:44 |
| Saved B control | 216921134 | 23 September 2026 14:44:30 |
| Saved A control | 216877934 | 23 September 2026 07:11:26 |
| Oldest validated boundary | 216791534 | 22 September 2026 16:39:48 |
| Pending epoch 4790 | 216748334 | Application header not captured; timestamp unavailable |

Exact nanosecond timestamps and hashes are retained in result 68. The complete
A reward-map control and both saved A/B block controls pass. Epoch 4790 has a
validated metadata response but lacks its first-block response. The opening
epoch sentinel has not been reached; earlier weekly boundaries remain
undiscovered. No fixed epoch length is extrapolated to fill them.

## Exact failure

```json
{
  "id": "epoch-053-block",
  "jsonrpc": "2.0",
  "method": "block",
  "params": {"block_id": 216748334}
}
```

The request began at `2026-11-07T10:41:48.940285+00:00` and stopped at
`2026-11-07T10:42:15.683353+00:00`. Saved transport error:

```text
TimeoutError: _ssl.c:993: The handshake operation timed out
```

No HTTP status, headers or response-body bytes were received. The empty body's
SHA-256 is
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
This is a transport failure, not evidence that the block or historical epoch
is unavailable. The incomplete response is neither used as a header nor
replaced by a successful response in place.

Saved UTC timing gaps have a minimum of 64.990265 seconds, before request 006;
all other gaps are at least 65 seconds. The original collector calls a
65-second sleep, but monotonic sleep durations were not saved. UTC differences
alone cannot verify exact monotonic pacing or explain that small discrepancy.
Recovery retains the same configured sleep and timeout behaviour.

## Recovery stages and unchanged budget

The original scope remains 21–27 September UTC, with the saved weekly endpoint
anchors, opening-epoch sentinel, A/B controls, reward-response offset and
32-application-epoch ceiling. The 97-attempt cap is cumulative:

- Original attempts: 53, including the unsuccessful request.
- Stage one: one explicitly invoked attempt for that same request, bringing
  the cumulative count to 54 if invoked.
- Stage two: at most 43 further attempts. Already successful requests are
  supplied from the validated cache, including block height/hash aliases.

Both stages preserve original request/response bytes and write only to a new
recovery directory. The failed-request payload is reproduced byte-for-byte in
its separate `failed/` directory. Stage two replays the original full walk from
cache and begins source collection only at its next missing request. Replaying
the full walk preserves the cumulative epoch ceiling rather than resetting it
to 32 additional epochs.

The endpoint remains `https://archival-rpc.mainnet.near.org`, with 65-second
spacing, a 15-second connection timeout and 60-second request deadline. No
automatic retry, fallback, source-query execution or cap increase is added.
Any recovery failure saves an error report and raw evidence, then stops.
Existing recovery stages cannot be overwritten or automatically resumed.

## Exact manual commands

First, recover only request 53:

```bash
.venv/bin/python analysis/27_recover_supply_epoch_discovery.py recover-failed \
  --run-dir results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4 \
  --recovery-dir results/supply_epoch_discovery_recovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4_recovery_01
```

This creates `run.json`, one capture triplet under `failed/`, and
`failed_validation.json`. The offline validation checks the recovered block's
request identity, epoch, start height and UTC application bounds using the
original walker. It reports the next missing evidence and keeps weekly totals
unavailable. It does not collect the next parent or another epoch automatically.
Review the report and optionally reproduce it offline:

```bash
.venv/bin/python analysis/27_recover_supply_epoch_discovery.py validate-failed \
  --recovery-dir results/supply_epoch_discovery_recovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4_recovery_01
```

Only after successful stage-one validation, continue remaining collection:

```bash
.venv/bin/python analysis/27_recover_supply_epoch_discovery.py continue \
  --recovery-dir results/supply_epoch_discovery_recovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4_recovery_01
```

New capture triplets go under `remaining/`, numbered from `epoch-055-...`.
Successful completion produces `validation.json`; a stop produces
`stopped.json`. The original empty response and metadata remain at their
original paths. Every triplet retains the endpoint, HTTP metadata, retrieval
timestamps, exact response strings, array order and SHA-256 hashes.

## Interpretation and offline reproduction

The current 18-boundary prefix is not complete weekly issuance. Its reward-map
sums are partial observations. Active historical protocol coverage remains
unverified outside the saved A/B configurations; incomplete collection must not
be presented as a weekly total or zero for missing epochs. Independent weekly
net debit, gross burn and subsidies remain unavailable. Even eventual issuance
minus exact supply movement is only an implied net debit, not independently
verified burn or reconciliation.

Result 68 is the reproducible stopped-run audit; result 69 is the recovery plan.
All non-collection commands default to stdout and refuse explicit output
overwrites:

```bash
.venv/bin/python analysis/27_recover_supply_epoch_discovery.py inspect \
  --run-dir results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4
.venv/bin/python analysis/27_recover_supply_epoch_discovery.py plan \
  --run-dir results/supply_epoch_discovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4
.venv/bin/python -m unittest discover -s tests -p test_supply_epoch_recovery.py -v
```

The focused tests forbid real HTTPS connections. Synthetic recovery responses
exist only in temporary directories to test stages, reuse, integer safeguards,
checksums, errors and cumulative caps; they are not historical evidence.
