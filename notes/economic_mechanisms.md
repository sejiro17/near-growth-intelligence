# NEAR Economic Mechanisms

## Purpose

I reviewed official NEAR documentation to distinguish the economic mechanisms described by the network from the activity and execution costs measured in this project.

Sources were reviewed on 25 October 2026. Current documentation does not independently establish which parameters applied throughout the historical observation period.

## Execution Fees

NEAR's documentation states that execution consumes gas and that gas fees are charged in NEAR. Different operations consume different amounts of gas, while the network's gas price affects their cost in NEAR.

The documentation also describes contract rewards associated with execution. I therefore do not treat the dataset's tokens_burnt field as a direct measurement of permanent token supply reduction.

My analysis measured approximately 65,878.09 NEAR in recorded receipt execution costs during the selected eight weeks. It did not reconcile those amounts to fee distributions, transaction receipt-conversion costs or changes in total token supply.

Source: [Gas and execution fees](https://docs.near.org/protocol/transactions/gas)

## Storage Requirements

NEAR uses storage staking, which requires balances to support stored contract data. Removing data can release some of that balance.

This provides a connection between state storage and demand for NEAR balances. However, storage commitments can change as data is added or removed.

The account-deletion findings make account lifecycle activity relevant to the research, but they do not quantify released storage balances or establish why accounts were deleted.

Source: [Storage staking](https://docs.near.org/protocol/storage/storage-staking)

## Staking and Network Security

NEAR uses proof-of-stake validation. Validators commit NEAR to participate in securing the network and receive rewards.

Staking creates a use for the token, but staked tokens remain part of total supply. Staking should not be treated as permanent token destruction.

This project has not measured changes in staked balances, validator rewards or issuance during the observation period. Transaction growth alone cannot establish changes in those measures.

Source: [Validators](https://docs.near.org/protocol/network/validators)

## Product Revenue and Governance

NEAR's February 2026 tokenomics article reports an operating Intents fee-sharing mechanism with payouts denominated in NEAR. It also discusses governance-controlled uses of product revenue, including buybacks and staking or locking acquired tokens.

The article explicitly leaves these uses to governance discretion. I do not assume that revenue automatically produces recurring buybacks or a guaranteed supply outcome.

Product revenue is separate from the receipt execution costs measured here. This project has not independently reconciled Intents fees, treasury receipts, buyback transactions or their timing during the selected period.

Source: [Evolving NEAR Tokenomics, 24 February 2026](https://near.org/blog/evolving-near-tokenomics)

## What the Current Results Establish

The analysis establishes transaction activity, account participation, concentration and recorded receipt execution costs within the selected window.

It also establishes that successful self-deletion activity affected a large share of accounts absent after the spike week.

These findings do not establish:

- Net token issuance or permanent supply reduction.
- Changes in storage commitments or staked balances.
- Product revenue or realised buyback expenditure.
- A token valuation or expected investment return.

## Implications for the Investment Assessment

My interpretation is that sustained useful activity could support demand for execution, storage and network security. Whether that translates into durable economic value depends on the scale of those requirements, the relevant protocol rules and how revenues are used.

The current evidence does not quantify that full relationship. Higher transaction counts or recorded execution costs should therefore not be presented as proof of stronger token value.

A stronger assessment would connect persistent, identifiable usage to measured economic flows while keeping burning, staking, locking and buybacks separate.

## Historical Verification Boundary

I have not applied a fixed inflation rate, fee-burning percentage or buyback assumption to the eight-week results.

Before modelling those effects, I would need to verify the rules active during the observation period and reconcile the relevant on-chain flows. Current documentation and statements of intended policy are not substitutes for that historical verification.