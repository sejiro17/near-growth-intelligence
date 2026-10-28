# NEAR Economic Mechanisms

## Purpose

This note separates NEAR's documented economic mechanisms from the
execution spending and supply movements measured in this project.

The analysis covers 24 August–18 October 2026. The supply comparison
uses closing supply on 23 August as its opening baseline.

Official sources were initially reviewed on 25 October 2026, with
execution-fee and tokenomics references rechecked on 28 October.
Current documentation does not independently establish the parameters
active throughout the historical period.

## Execution Fees

NEAR charges execution fees in NEAR. Gas measures the resources used,
while the gas price affects the corresponding token cost.

The documentation also describes contract rewards associated with
execution. The dataset's `tokens_burnt` field is therefore not treated
as an independently reconciled measurement of permanent supply reduction.

### Measured spending

| Component | Eight-week recorded spending |
|---|---:|
| Transaction receipt conversion | 2,110.82 NEAR |
| Receipt execution | 65,878.09 NEAR |
| Combined | 67,988.91 NEAR |

Conversion contributed 3.10% of combined spending. Combined weekly
spending increased 83.13% between the first and final weeks.

Within the receipt-execution component, outcome counts increased 66.85%
and average recorded cost per receipt increased 9.52%. Together, these
account arithmetically for the 82.73% increase in receipt execution costs.

The results do not isolate the contributions of gas prices, execution
complexity or changes in operation mix.

Conversion costs use transaction submission dates. Receipt execution
costs use execution dates. The combined total is a calendar-period
comparison, not the complete fees of a matched transaction cohort.

### Economic interpretation

These measurements establish expenditure denominated in NEAR for
network execution.

They do not measure external token purchases, holding periods or net
market demand. Fees may be paid from existing balances, through
sponsored transactions or after acquiring tokens shortly before use.
Failed execution can also incur costs.

Recorded spending has not been fully reconciled to fee distributions,
permanent burning or economic value accruing to holders.

Source: [Gas and execution fees](https://docs.near.org/protocol/transactions/gas)

Evidence: results 13, 14, 34, 36 and 37.

## Storage Requirements

Storage staking requires balances to support stored data. Removing data
can release some of that requirement.

This creates a use for NEAR balances, but commitments can change over
time. Releasing a storage requirement is not permanent token destruction.

The account-deletion findings make lifecycle activity relevant to the
research. They do not quantify released storage balances or establish
why accounts were deleted.

Source: [Storage staking](https://docs.near.org/protocol/storage/storage-staking)

Evidence: results 16 and 17.

## Staking and Network Security

NEAR uses proof-of-stake validation. Staking commits tokens to network
security, while validators receive rewards.

Staked tokens remain part of total supply. Staking is not permanent
token destruction.

The project compared combined nonstaked and staked balances around
records labelled `validator_accounts_update`. This is not a complete
measurement of network-wide staking positions, validator rewards or
gross issuance.

Transaction growth alone cannot establish changes in staking demand.

Source: [Validators](https://docs.near.org/protocol/network/validators)

Evidence: results 29–34.

## Product Revenue and Governance

NEAR's February 2026 tokenomics article describes an operating Intents
fee-sharing mechanism with payouts denominated in NEAR.

It also describes governance-controlled uses of revenue, including
buybacks and staking or locking acquired tokens. These should not be
assumed to occur automatically or produce a guaranteed supply outcome.

Product revenue is separate from network execution spending. This
project has not independently reconciled Intents fees, treasury receipts,
distributions or realised buybacks during the observation period.

A buyback changes who holds tokens. Staking and locking affect their
availability under particular conditions. A permanent burn reduces
supply. These events must not be combined into one measure of token
destruction.

Source: [Evolving NEAR Tokenomics, 24 February 2026](https://near.org/blog/evolving-near-tokenomics)

## Observed Supply and Reconciliation

Closing total supply increased from approximately 1,304,386,568.87 NEAR
on 23 August to 1,309,322,552.85 NEAR on 18 October.

The net increase was approximately 4,935,983.98 NEAR, or 0.3784% of
opening supply. All eight weekly closing-supply comparisons were positive.

| Measurement | Approximate NEAR |
|---|---:|
| Observed positive block supply movements | 4,990,242.56 |
| Observed block supply decrease magnitude | 54,258.58 |
| Net observed supply increase | 4,935,983.98 |
| Validator-update net balance change | 4,919,384.47 |
| Net supply increase minus validator-update change | 16,599.51 |
| Positive supply movements minus validator-update change | 70,858.09 |

Positive block movements minus the decrease magnitude reconcile to
the net supply change. Validator-update balance changes do not fully
reconcile with these movements; the differences remain unresolved.

The project therefore does not classify validator-update changes as
complete gross issuance or block supply decreases as complete permanent
burning. A block can contain offsetting effects.

Recorded execution spending must not be subtracted from net supply
growth to infer issuance. The measurements have different meanings,
and fee allocation has not been fully reconciled.

Total supply is not circulating supply. The observations also do not
establish what supply would have been without the measured activity.

Source fields use floating-point storage, so amounts are approximate.
The 0.000001 NEAR tolerance applied to individual validator balance
comparisons is an analytical choice, not a protocol rule.

Evidence: results 28–34.

## Implication for the Investment Thesis

The project quantifies one economic channel: recorded execution
expenditure in NEAR.

Storage, staking and product-revenue mechanisms provide additional
connections to investigate. Their presence in documentation does not
establish their realised magnitude or benefit to holders.

A stronger investment argument requires persistent useful activity
linked to economic flows of meaningful scale, with supply changes,
distributions and potential selling pressure considered.

No fixed inflation rate, burning percentage or buyback assumption has
been applied to the historical results. No valuation or expected token
return has been derived.

The argument is developed in [investment_thesis.md](investment_thesis.md).
Detailed validation and unresolved differences are recorded in
[data_checks.md](data_checks.md).