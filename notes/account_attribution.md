# Account Attribution

This register records the sources supporting account roles and service
associations used in the research. Observed activity is kept separate
from claims about ownership or application coverage.

Initial review: 27 October 2026.
Register updated: 28 October 2026.

## Account Register

| Account | Service association | Evidence status | Role or observation |
|---|---|---|---|
| intents.near | NEAR Intents | Documented contract role | The Verifier contract. The explorer measures transactions it signed, separately from calls it received. |
| omni-relayer.bridge.near | Omni Bridge | Documented relayer role | Aurora's official tutorial identifies it as finalizing a bridge transfer on NEAR. |
| relay.aurora | Aurora | Documented association | Appears in Aurora's official example connecting Aurora execution to a NEAR transaction. |
| sweat-relayer.near | Unverified | Service attribution pending | Recorded activity includes delegated transactions and function calls. |
| meteor-relayer.near | Unverified | Pending verification | Recorded activity includes delegated transactions. |
| closemeat6237.near | Unverified | Pending verification | A selected signing account with destination and action breakdowns. |

“Documented” describes what the cited source supports. It does not
independently establish historical ownership or complete operational
coverage. Unverified entries retain their account identifiers without
an assumed service label.

## Supporting Sources

### NEAR Intents

[Official contract repository](https://github.com/near/intents)

The repository describes the Verifier and links to its deployment at
[intents.near](https://nearblocks.io/address/intents.near). The contract
evaluates signed intents and supports atomic execution.

This documents the contract's purpose. It does not classify every
transaction signed by the account as a completed swap.

### Omni Bridge

[Official bridge repository](https://github.com/near-one/omni-bridge)

The repository identifies omni.bridge.near as the NEAR bridge contract.

[Aurora's Omni Bridge tutorial](https://doc.aurora.dev/blog/omnibridge-tutorial/)

The tutorial explicitly identifies omni-relayer.bridge.near as finalizing
the illustrated transfer on NEAR. This supports a relaying role without
establishing the operator's identity.

### Aurora

[Aurora's gas comparison article](https://doc.aurora.dev/blog/evm-gas-near-gas-on-aurora/)

The article uses relay.aurora in a transaction-status request when
connecting Aurora execution to an underlying NEAR transaction.
The example supports the association recorded here.

### Accounts Without Confirmed Service Attribution

No direct official confirmation of service affiliation has been recorded
for sweat-relayer.near, meteor-relayer.near or closemeat6237.near.

Their activity descriptions come from the saved transaction, destination
and action results. Names and action patterns alone do not establish
ownership.

Evidence: results 18–20 and 35.

## Dashboard Coverage

The Account Explorer contains five profiles:

- intents.near
- omni-relayer.bridge.near
- sweat-relayer.near
- meteor-relayer.near
- closemeat6237.near

Each includes eight weeks of signing-account activity, destination and
action breakdowns, and an attribution status. Source links are displayed
where a documented role is recorded.

relay.aurora remains in this register but is not profiled because the
selected destination and action exports do not cover it.

## Reading the Profiles

Signing-account activity and contract-receiver activity are different
measures. A relayer can submit transactions for other participants,
so its signing identifier is not an application user count.

Profiles cover selected accounts rather than entire applications.
Delegated inner actions have not been expanded, and transaction counts
alone do not establish completed swaps or cross-chain transfers.

Any later service-level grouping should record its account membership,
supporting sources and overlap with other groups.