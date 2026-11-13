# Eight-week issuance and net supply debit: protocol-derived bounds

[Result 107](../results/107_eight_week_issuance_bounds_2026-08-24_to_2026-10-18.json)
bounds NEAR's epoch-reward issuance and net header debit for every week of the
24 August–18 October 2026 economic window. It uses only exact integer supplies,
epoch boundaries and protocol configuration at the nine saved weekly closing
anchors, the nearcore supply and reward rules, and the measured 21–27 September
reward week as an independent control. It adds bounds; it does not replace
result 72, the eight-week observational comparison or the 144-block header prefix.

## Result

| Quantity, 24 August–18 October 2026 | NEAR | Classification |
| --- | ---: | --- |
| Exact total-supply movement, 23 Aug close → 18 Oct close | +4,935,983.979834754311012798611813 | Measured (exact anchor headers) |
| Epoch-reward issuance, 184 applications | 4,935,983.98 – 5,016,044.06 | Protocol-derived bounds |
| Net header debit (protocol net of subsidies) | 0 – 80,060.076856675035903096374704 | Protocol-derived bounds |
| Net debit as a share of issuance | at most 1.6220% | Derived from the bounds |
| Issuance, annualised on opening supply | 2.4654% – 2.5053% | Derived; protocol maximum 2.5% |
| Gross burn, subsidies, other adjustments | Unavailable | Not measured; not zero |

Weekly rows are in result 107. Every week shows the same pattern: exact supply
movement of 596,080–632,797 NEAR and a net debit bound of 7,336–13,420 NEAR,
which is at most 1.18–2.17% of that week's issuance.

**Control week.** For 21–27 September the derived range is 611,555.97–621,464.57
NEAR. The independently recorded and protocol-checked reward maps total
618,436.07 NEAR (result 72): inside the range, at 99.51% of the ceiling.
Opening supply, exact movement, 23 applications, epochs 4786–4808 and the
closing epoch's first block all match result 72 exactly.

## Why the bounds hold

Semantics are read from nearcore 2.13.3, commit `5af9ca7`, the implementation
already pinned for protocol 86 in this project.

1. **Supply identity.** Each block's `total_supply` equals the previous
   supply plus `minted_amount`, which is non-zero only at an epoch's first
   block, minus `balance_burnt` summed over newly included chunk headers
   ([block.rs](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/block.rs#L140-L198),
   [chain.rs](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/chain/src/chain.rs#L2520-L2531)).
   `balance_burnt` is an unsigned u128, so the net header debit is never
   negative. Hence **issuance ≥ supply movement** within any anchor interval.
2. **Reward ceiling.** When epoch T is finalised, its total reward is
   `total_supply(last block of T) × max_inflation_rate × (ts(last block of T) − ts(last block of T−1)) / (31,536,000 s × 10⁹)`.
   It is minted at the first block of epoch T+1. Validators below the uptime
   threshold earn less or nothing, and withheld amounts and floor rounding are
   never minted
   ([lib.rs](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/lib.rs#L797-L857),
   [reward_calculator.rs](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/reward_calculator.rs#L51-L130)).
3. **Epoch alignment.** For a week between anchors c₀ and c₁, the applied
   rewards are those of epochs X(c₀)+1 … X(c₁), where X(c) is the epoch
   containing anchor c. Their earned-epoch durations telescope to
   `ts(parent of first block of X(c₁)) − ts(parent of first block of X(c₀))`.
   Each anchor therefore needs its epoch's first block and that block's parent,
   which the collector verifies through epoch IDs and `next_epoch_id` links.
4. **Compounding.** Supply only decreases between mints, so the supply used
   for each earned epoch is at most the opening anchor supply plus earlier
   mints in the week. With x = (1/40) × D / year,
   `minted ≤ S_open × (e^x − 1) ≤ S_open × x / (1 − x)`, floored to yoctoNEAR.
5. **Net debit.** By the identity, net debit = issuance − supply movement,
   so it lies between 0 and the upper bound minus the movement.

**Release applicability.** `reward_calculator.rs` is byte-identical in nearcore
2.12.0, 2.13.3 and 2.14.0, and `calculate_reward` ignores its protocol-version
argument. The total-supply update lines in `block.rs` and the reward inputs in
`finalize_epoch` (epoch duration, block total supply, `max_inflation_rate`) are
also identical across those three releases. The bounds therefore do not depend
on which of these releases a validator ran. The protocol-dependent input,
`max_inflation_rate`, is read from historical configuration at every anchor.

**Annualisation.** The upper annualised rate (2.5053%) slightly exceeds the 2.5%
maximum for two reasons: it is expressed on opening supply while supply grows
during the window, and the compounding allowance in step 4 is conservative.
Without that allowance the summed weekly ceiling is 2,407.00 NEAR lower.

A property test simulates 300 random weeks with nearcore-style integer minting,
partial uptime and unsigned burns. In every case the true minting and net debit
fall inside the derived bounds (`tests/test_eight_week_issuance_bounds.py`).

## Evidence collected

Forty-five sequential point requests to `https://archival-rpc.mainnet.near.org`,
five per saved weekly closing anchor: `block` (exact supply, epoch), `validators`
(epoch start), the epoch's first block, its parent, and
`EXPERIMENTAL_protocol_config`. They used 65-second spacing, one attempt each,
no retries, fallbacks or resumes. All 45 returned HTTP 200 with matching JSON-RPC
IDs. Each anchor's hash, height and UTC date match result 28. Raw request bytes,
response bodies, metadata and SHA-256 hashes are retained under
`results/eight_week_issuance_anchors_2026-08-23_to_2026-10-18/`. No header range,
reward-map walk, chunk scan or BigQuery query was used.

## What is and is not established

- **Measured:** exact weekly and eight-week total-supply movements (replacing
  FLOAT-derived endpoints for this purpose), epoch boundaries, and protocol
  version 86 with `max_inflation_rate` 1/40 and the reviewed economic fields at
  all nine anchor epochs.
- **Protocol-derived:** the issuance and net-debit ranges above. Outside the
  control week, minting is bounded, not measured.
- **Qualification:** protocol version and parameters are checked at the anchor
  epochs and all 23 control-week epochs, not at each of the other intervening
  epochs. Version selection is a stake vote and is not assumed monotonic. A
  change and reversal between anchors would be needed to invalidate the 1/40
  rate. Protocol 86 rules are consensus-wide, so the reviewed source applies to
  every node producing these blocks.
- **Not established:** independently measured net header debit outside the
  144-block prefix, gross burn, subsidies or their split. Net debit is not
  gross burn and is not execution spending. The anchors are the saved observed
  day-close blocks, not independent proofs of the final block before midnight.
  The weeks are the exact intervals between those blocks. Evidence is
  RPC-derived from one public endpoint, not an independent chain proof.

## Investment implication

Over eight weeks, net supply debit offsets at most 1.62% of epoch-reward
issuance. NEAR's total supply therefore grew at essentially its reward rate,
roughly 2.47–2.51% annualised, and at observed activity levels the protocol's
net debit (fee burning net of subsidies) cannot materially change that. This
measured net supply increase constrains a *supply-based* investment argument:
fee burning does not make supply contract or stay flat. It does not decide the
investment case. Other value-capture mechanisms remain incompletely
attributed: product revenue, governance-directed purchases, staking or locking
demand, and storage commitments. This project neither measures them fully nor
rules them out.
For the conditional model, average exact net supply growth is
exactly one eighth of the measured movement, about 616,998.00 NEAR/week. This is the destruction rate needed
for supply neutrality under these historical conditions. It includes every
total-supply term in the protocol identity, so it needs no assumption about
subsidies or burn.

## Reproduction

```bash
.venv/bin/python -B analysis/50_eight_week_issuance_bounds.py report --check
.venv/bin/python -B -m unittest tests/test_eight_week_issuance_bounds.py -v
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```

Validation and reports are offline. The `collect` command refuses to start when
a capture already exists.
