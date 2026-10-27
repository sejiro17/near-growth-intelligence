# Account Attribution

## Purpose

This register documents the evidence linking selected accounts to services
and technical roles. Account names alone are not sufficient verification.

## Initial Review — 27 October 2026

| Account | Associated service | Evidence status | Supported interpretation |
|---|---|---|---|
| intents.near | NEAR Intents | Documented contract role | The NEAR Intents Verifier contract. Its role as a transaction signer is analysed separately from calls received by the contract. |
| relay.aurora | Aurora | Documented association | Aurora documentation uses this account in an example linking Aurora execution to an underlying NEAR transaction. Complete operational coverage has not been established. |
| sweat-relayer.near | Not yet established | Pending verification | A leading transaction-signing account in the selected dataset. Service attribution remains unverified. |
| meteor-relayer.near | Not yet established | Pending verification | A leading transaction-signing account in the selected dataset. Service attribution remains unverified. |
| omni-relayer.bridge.near | Omni Bridge | Documented relayer role | Aurora's official Omni Bridge tutorial identifies this account as finalizing transfers on NEAR. Operator identity and complete historical coverage have not been independently established. |

## Sources

### NEAR Intents

https://github.com/near/intents

The official repository describes the Verifier contract and links to its
deployed account:

https://nearblocks.io/address/intents.near

The Verifier evaluates signed intents and supports their atomic execution.
This establishes the contract's documented purpose. It does not mean every
transaction signed by this account represents a completed swap.

### Aurora

https://doc.aurora.dev/blog/evm-gas-near-gas-on-aurora/

The official article uses relay.aurora in a NEAR transaction-status request
when explaining the relationship between Aurora and NEAR execution.

This supports an association with Aurora's transaction infrastructure.
The example alone does not establish the account's complete operational
scope or its role throughout the observation period.

### Omni Bridge

https://github.com/near-one/omni-bridge

The official repository identifies omni.bridge.near as the NEAR bridge
contract.

https://doc.aurora.dev/blog/omnibridge-tutorial/

Aurora's official tutorial explicitly identifies omni-relayer.bridge.near
as the account that automatically finalizes the illustrated transfer on
NEAR.

This supports its bridge-relaying role. It does not establish the account's
operator or imply that every transaction it signs represents a completed
cross-chain transfer.

### Pending Verification

Direct official confirmation of the exact account-to-service relationship
has not yet been recorded for:

- sweat-relayer.near
- meteor-relayer.near

These accounts remain available for account-level analysis without a
verified service label. Pending verification does not imply suspicious
activity.

## Measurement Boundaries

- Signing-account activity and contract-receiver activity are separate measures.
- A relayer may submit transactions for other participants.
- A signing identifier is not a count of an application's users.
- Selected accounts do not necessarily cover an entire application's activity.
- A documented service association does not establish account ownership.
- Current documentation does not independently establish historical ownership
  or configuration throughout the observation period.
- Transaction counts do not establish completed swaps or cross-chain transfers.
- Unverified accounts remain visible without an assumed application label.

## Use in the Dashboard

Profiles will identify the selected account, its supported role, the evidence
status and the source.

Metrics will describe the account's observed activity within the selected
period. They will not be presented as complete application activity or
application user counts.

Any future grouping of multiple accounts under one service will document
its membership and attribution evidence. Overlapping groups will not be
summed as independent ecosystem activity.