# NEAR Economic Mechanisms

## Purpose

I reviewed official NEAR documentation to distinguish the network's documented economic mechanisms from the activity, execution costs and supply movements measured in this project.

Sources were initially reviewed on 25 October 2026 and rechecked on 27 October. Current documentation does not independently establish which parameters applied throughout the historical observation period.

The primary analysis covers 24 August–18 October 2026. The supply comparison uses the closing observation on 23 August as its opening baseline.

## Execution Fees

NEAR's documentation states that execution consumes gas and that gas fees are charged in NEAR. Operations consume gas, while the network's gas price affects their cost in NEAR.

The documentation also describes contract rewards associated with execution. I therefore do not treat the dataset's tokens_burnt field as a direct measurement of permanent token supply reduction.

Across the selected eight weeks, recorded receipt execution costs totalled approximately 65,878.09 NEAR.

Between the first and final weeks:

- Receipt execution outcomes increased 66.85%.
- Average recorded cost per receipt increased 9.52%.
- Total recorded receipt execution costs increased 82.73%.

Receipt count multiplied by average recorded cost gives total recorded receipt cost. This describes the arithmetic of the increase without identifying its underlying causes.

The results do not isolate the contributions of gas prices, execution complexity or changes in the mix of operations.

Costs exclude transaction receipt-conversion costs. They have not been reconciled to all fee distributions or supply effects.

Source: [Gas and execution fees](https://docs.near.org/protocol/transactions/gas)

Evidence: results 13, 14 and 34.

## Storage Requirements

NEAR uses storage staking, which requires balances to support stored contract data. Removing data can release some of that balance.

This connects state storage to demand for NEAR balances, but those requirements can change as data is added or removed.

The self-deletion findings make account lifecycle activity relevant to the research. They do not quantify released storage balances or establish why accounts were deleted.

Releasing a storage requirement is different from destroying tokens. The deletion results should not be treated as a measurement of permanent burning.

Source: [Storage staking](https://docs.near.org/protocol/storage/storage-staking)

Evidence: results 16 and 17.

## Staking and Network Security

NEAR uses proof-of-stake validation. Validators participate in securing the network and receive rewards.

Staking creates a use for the token. Staked balances should not be treated as permanent token destruction.

The economic investigation compared combined nonstaked and staked account balances around records labelled validator_accounts_update.

That comparison is not a complete measurement of network-wide staking positions, validator rewards or gross issuance. It remains incompletely reconciled with observed supply movements.

Transaction growth alone cannot establish changes in staking demand or validator economics.

Source: [Validators](https://docs.near.org/protocol/network/validators)

Evidence: results 29–34.

## Product Revenue and Governance

NEAR's February 2026 tokenomics article reports an operating Intents fee-sharing mechanism with payouts denominated in NEAR.

It also describes governance-controlled uses of product revenue, including buybacks and staking or locking acquired tokens. Whether, when and how these tools are used remains subject to governance discretion.

I therefore do not assume that product revenue automatically produces recurring buybacks or a guaranteed supply outcome.

Product revenue is separate from the receipt execution costs measured here. This project has not independently reconciled Intents fees, treasury receipts, buyback transactions or their timing during the selected period.

A buyback, staking commitment, lock and permanent burn are different events. They should not be combined into a single measure of total-supply reduction.

Source: [Evolving NEAR Tokenomics, 24 February 2026](https://near.org/blog/evolving-near-tokenomics)

## Observed Total-Supply Movement

Closing total supply increased from approximately 1,304,386,568.87 NEAR on 23 August to 1,309,322,552.85 NEAR on 18 October.

The net observed increase was approximately 4,935,983.98 NEAR, or 0.3784% of opening supply.

Every weekly closing-supply comparison in the selected period showed a positive net change.

This measures the net movement in recorded total supply. It does not separately identify gross issuance and permanent burning, and it is not a measurement of circulating supply.

The observed increase also does not establish what supply would have been without the measured activity. That would require an additional model and verified assumptions.

Evidence: results 28, 33 and 34.

## Supply Reconciliation

I compared block-level supply movements with changes in combined nonstaked and staked balances recorded under validator_accounts_update.

| Measurement | Approximate NEAR |
|---|---:|
| Observed positive block supply movements | 4,990,242.56 |
| Observed block supply decrease magnitude | 54,258.58 |
| Net observed supply increase | 4,935,983.98 |
| Validator-update net balance change | 4,919,384.47 |
| Net supply increase minus validator-update change | 16,599.51 |
| Positive supply movements minus validator-update change | 70,858.09 |

The positive block movements minus the decrease magnitude reconcile to the net observed supply change.

The validator-update balance comparison does not fully reconcile with supply movements. These differences remain unresolved.

I therefore do not present:

- Validator-update balance changes as complete gross issuance.
- Block supply decreases as complete permanent burning.
- Recorded receipt execution costs as a substitute for either measure.

A block can contain offsetting economic effects. Its net supply movement does not necessarily expose every component separately.

Source balance, supply and cost fields use floating-point storage, so amounts are approximate.

The validator comparison applied a 0.000001 NEAR analytical tolerance to individual balance differences. This is a research choice for handling the observed small differences, not a protocol rule or a guarantee of source accuracy.

Evidence: results 29–34.

## What the Results Establish

The project measures:

- Transaction activity, account participation and concentration.
- Growth contributions from fixed and tracked account groups.
- Initial receipt outcomes and costs for two selected growth accounts.
- Reported errors in eighteen sampled failed receipts.
- Network-wide recorded receipt execution costs.
- Observed total-supply movement during the selected period.

The results also show that successful self-deletion activity was widespread among accounts absent after the spike week.

These measurements do not provide a complete reconciliation of:

- Gross issuance and permanent burning.
- Fee distributions and product revenue.
- Storage commitments or network-wide staked balances.
- Treasury receipts or realised buyback expenditure.
- Economic value accruing to NEAR holders.

No token valuation or expected investment return has been derived.

## Implications for the Investment Assessment

My interpretation is that sustained useful activity could support demand for execution, storage and network security. Whether that translates into durable economic value depends on the scale of those requirements, the relevant rules and how revenues are used.

The current findings make the measurement boundaries clearer: execution spending increased between the endpoints, while recorded total supply increased across the period.

Neither observation alone establishes the economic benefit of network activity to holders.

A stronger assessment would connect persistent, identifiable usage to reconciled economic flows while distinguishing fees, issuance, burning, staking, locking and buybacks.

The practical priority is to require that reconciliation before making supply or valuation claims.

The broader interpretation is documented in [investment_thesis.md](investment_thesis.md), with investigation priorities in [decision_priorities.md](decision_priorities.md).

## Historical Verification Boundary

I have not applied a fixed inflation rate, fee-burning percentage or buyback assumption to the eight-week results.

Before modelling those effects, I would need to verify the rules active during the observation period and reconcile the relevant on-chain flows.

Current documentation and statements of intended policy are not substitutes for historical verification.

The unresolved decomposition remains documented in [data_checks.md](data_checks.md). It does not change the separately measured net increase in observed total supply.