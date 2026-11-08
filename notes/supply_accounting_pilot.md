# Independent supply accounting: one epoch-boundary pilot

The existing eight-week comparison remains observational. Result 46 records a
net supply change of 4,935,983.9798346 NEAR and raw validator balance changes of
4,919,384.46545613831 NEAR, leaving +16,599.51437846169 NEAR. The 23 September
residual is +11,427.31386968814 NEAR. Neither residual measures issuance or burn.
Results 42–45 already establish the selected event alignment, omitted updates,
valid blank-chunk records and one exact account witness. This pilot does not
reconstruct those investigations or adjust their daily totals.

## Missing measurement and independent evidence

The smallest useful new monetary measurement is the epoch reward mint recorded
in historical epoch metadata, independently of account balance differences and
the sign of the supply movement. Use block A, height **216877934**, hash
`HezadGLh22Yco1SLiakvzQ5ftw6F8pAf7zej4rn8BaVG`.

The saved A/B protocol configurations report mainnet protocol 86. The reviewed
implementation is nearcore **2.13.3**, released 4 August 2026, pinned to commit
[`5af9ca74631e6cf0dae33e77d1a632e94d2952ce`](https://github.com/near/nearcore/releases/tag/2.13.3),
before the observation window. Its stable protocol is 86; the Spice supply path
is inactive. This provides a historically applicable protocol path, rather than
relying on current documentation alone. The archive server's binary version and
historical retention are not established by the saved protocol configuration.

The documented [`validators`](https://docs.near.org/api-reference/post-validators)
method accepts an `epoch_id`. Its
[`validator_reward_paid_prev_epoch`](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/views.rs#L2612)
map contains exact validator and treasury rewards paid at the start of the
**previous** epoch. Query A's **next** epoch, not A's epoch:

| Item | Exact identity |
| --- | --- |
| Requested epoch ID | `FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2` |
| Saved next-epoch anchor B | 216921134 / `J6jyjUSFFatXnCKEG3nKaD9qQLzQrY4xWyFkB5a5mJHB` |
| A parent | 216877933 / `FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2` |

The epoch ID happens to equal the parent block hash; the requests use their
distinct parameter names and purposes. B is reused, with no new B request.
For response epoch E, the rewards were earned in E−2 and applied at E−1's start
(A). Accrual time must not determine the supply-recognition week.

The historical [epoch manager](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/lib.rs#L1553)
returns the epoch reward map. The
[reward calculator](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/reward_calculator.rs#L48)
returns that map and a minted amount equal to its complete sum in the populated
validator branch. The collector rejects the zero-validator/treasury-only special
case. The [block producer](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/client/src/client.rs#L1113)
selects the next epoch's `minted_amount` at an epoch transition. No configured
inflation percentage, assumed treasury share, supply difference or selected set
of 462 validator accounts supplies the pilot's mint measurement. All returned
payees, including treasury and validators no longer in the current set, count.

Result 45's exact bitwise witness, +1,128.147246190549662124317432 NEAR, is only an
alignment cross-check against one reward-map entry. It is not added to existing
daily totals or used to construct the map total. A mismatch stops interpretation.

## Supply identity, inclusion timing and gross-burn limitation

For this non-Spice historical path:

```text
S_A = S_parent + M_epoch − D_A
D_A = sum(chunk.balance_burnt where chunk.height_included == A.height)
```

The [block implementation](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/block.rs#L145)
counts only newly included chunk headers. The RPC field is the chunk header's
previous execution balance debit, validated against the predecessor ChunkExtra;
it is not a sum of receipts executing at A. Preserve the inclusion block hash,
shard ID, chunk hash, predecessor hash, creation/inclusion heights and array
position. Account for a debit on its canonical supply-inclusion block, not by
receipt execution date or chunk creation date. Carried-forward headers must not
be counted again.

Saved A has ten configured shard headers and five newly included chunks. Their
exact net debit is **2,206,853,430,760,200,000,000 yoctoNEAR**, or
**0.002206853430760200000000 NEAR**. The five carried-forward headers' debit of
1,680,380,063,688,100,000,000 yoctoNEAR is excluded. Source SHA-256 values and the
full ordered chunk audit are recorded in result 63.

Crucially, the historical
[runtime adapter](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/chain/src/runtime/mod.rs#L387)
computes:

```text
B_gross = tx_burnt_amount + other_burnt_amount + slashed_burnt_amount
D = B_gross − subsidized_amount
S_A = S_parent + M_epoch − B_gross + U_subsidy
```

The saved historical WASM flag `one_yocto_on_promise` is true. That flag allows
subsidized attached deposits in specified zero-balance-contract cases; it does
not establish that any subsidy occurred in the referenced executions. Therefore
`balance_burnt` supports a **net header debit**, not a separately measured gross
burn or proof of zero subsidies. If subsidy is instead included in a broader
gross-issuance definition, it must not also be counted as an adjustment.

Execution outcome `tokens_burnt` is recorded before the contract reward deduction
in this implementation; the runtime burn statistics reflect that deduction.
Neither outcome spending nor a universal assumed burn percentage substitutes for
these statistics. Validator staking, unstaking and transfers redistribute balances
and do not independently measure minting.

The precise missing gross evidence is the exact historical
[`ChunkApplyStats` balance breakdown](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/chunk_apply_stats.rs#L243):
`tx_burnt_amount`, `other_burnt_amount`, `slashed_burnt_amount` and
`subsidized_amount`. Historical stats are
[stored by block hash and shard ID](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/store/src/adapter/chunk_store.rs).
A usable export must retain its format/version, execution block hash/height,
shard ID/UID, new/missing-chunk application context and the link to the
ChunkExtra referenced by each included header. It must reconcile gross burn
minus subsidy to that header's exact debit, including any intervening missing
chunk applications. These fields are not saved, not present in the verified
BigQuery chunk schema, and not established as available through the public
block/chunk RPC responses. Historical storage/replay availability requires
confirmation; no unverified RPC method is proposed. Gross burn and subsidy remain
null even if the pilot's net header identity closes exactly.

## Two-request manual pilot

Use the [documented free public archival endpoint](https://docs.near.org/api/rpc/providers)
`https://archival-rpc.mainnet.near.org`, without credentials:

1. `validators`, `{"epoch_id":"FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2"}`.
   Require epoch start height 216921134, nonempty historical validator information,
   the complete nonempty reward map, treasury membership, exact unsigned u128
   strings and agreement with the saved witness. Missing history, unsupported
   field/method, empty or ambiguous output stops before request 2. An empty map
   is not zero minting. The response does not echo epoch ID: request identity,
   saved B's epoch ID/start height and the witness provide the alignment checks.
2. `block`, `{"block_id":"FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2"}`.
   This supplies the missing exact parent supply. Require the exact hash and
   height, an earlier timestamp, a changed epoch ID and
   `parent.next_epoch_id == A.epoch_id`.

From the repository root, the single next manual collection command is:

```bash
python3 -B analysis/24_supply_epoch_pilot.py collect
```

The script waits 65 seconds before each request, uses the existing 15-second
connect/60-second request timeout, and makes no automatic retries, redirects or
endpoint fallback. It preserves complete request and response bytes, array order,
exact monetary strings, endpoint, timestamps, HTTP status/headers, lengths and
SHA-256 in a new unique directory:

```text
results/supply_epoch_pilot_2026-09-23/<UTC>_<unique-id>/
  run.json
  A-next-epoch-rewards.request.json / .response.body / .metadata.json
  A-parent-block.request.json / .response.body / .metadata.json
  validation.json
```

No existing capture is overwritten or resumed. HTTP/JSON-RPC/transport errors
retain the failed capture and stop. After both valid captures, integer arithmetic
must close with **zero yoctoNEAR discrepancy**; a mismatch retains a report and
stops. The 0.00001 NEAR tolerance for saved FLOAT-derived arithmetic has no role
in this exact-integer test. Exact closure verifies this header identity, not
independent worldwide completeness or the missing gross decomposition.

Offline commands:

```bash
python3 -B analysis/24_supply_epoch_pilot.py plan
python3 -B analysis/24_supply_epoch_pilot.py validate results/supply_epoch_pilot_2026-09-23/<capture-directory>
python3 -B -m unittest discover -s tests -p test_supply_epoch_pilot.py -v
```

Result 63 is reproducible with `plan --output <new-path>`; exclusive creation
prevents overwriting an existing result. No network is used by plan or validate.

## Conditional extension to the eight weeks

If the independent reward map and exact parent test pass, the method can measure
reward minting at each actual epoch boundary. Enumerate real epoch IDs and start
headers rather than assuming every 43,200 heights represents an epoch. Check
protocol versions and subsidy semantics throughout the window; a rule change
requires a separately reviewed path. Assign minting to the application header's
UTC week.

The saved daily-supply export already identifies the nine closing endpoint
hashes needed for the opening baseline and weekly endpoints (23/30 August;
6/13/20/27 September; 4/11/18 October), but its monetary supply fields are
FLOAT-derived. Lossless endpoint supplies and complete canonical header/chunk
inclusion coverage are not saved for the full interval. Validate chain links,
heights, shard layouts, chunk masks, duplicates and missing records before
weekly aggregation. Group net debits by inclusion block timestamp, even when
their execution precedes the weekly boundary. Then obtain independently retained
gross/subsidy statistics for precisely those debits before publishing the target
gross accounting identity. No expanded collection is prepared in this pilot.

This pilot can establish an independent reward-mint component and test one exact
net supply transition. It cannot yet close weekly gross issuance/burn accounting
or explain the old balance-change residual by adding recovered updates. The
selected two-block indexing discrepancy and unconfirmed ingestion-collision
hypothesis remain bounded to their saved evidence.
