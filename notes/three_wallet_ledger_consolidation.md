# Three-wallet native ledger and missing asset layer

[Result 80](../results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json)
consolidates results 74–79 without changing them. It contains all 2,251 accepted
native action entries, eight weekly flow observations, exact boundary states,
external/internal movement splits and source hashes. Every payment remains
economically unclassified. The positive `1csfundsadmin` difference remains
unallocated; no additional collection is scheduled solely to explain it.

The current layered ledger is
[result 104](../results/104_wallet_ledger_with_known_asset_reconciliation.json).
It preserves result 80's native wallet/group comparisons and adds result 103 as
**one known owner–asset balance reconciliation**, not complete asset coverage.
For `1csfundsadmin.sputnik-dao.near` inside `intents.near`, asset
`nep141:wrap.near`, opening `990000000000000000000000000` and closing
`1000100010001000100010` base units give a decrease of
`989998999899989998999899990`, exactly the one saved successful internal
transfer. Integer discrepancy is zero. The two states cover one known pair
for one of three wallets; the complete asset-pair denominator is unknown.
Offsetting flows could exist. Recipient ownership, fee origin and purchases
remain unavailable. Neither native totals nor the closed withdrawal trace is
changed, and the internal amount is not added to native flows or value capture.
See [known-asset coverage and source limits](known_asset_wallet_coverage.md).
Offline current-ledger reproduction is included in the unified rebuild:

```bash
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```

## Native stocks and flows

All figures below are exact NEAR. Account stocks are `amount + locked`; all six
captured locked values are explicitly zero. The execution window is
`[2026-08-24T00:00:00Z, 2026-10-19T00:00:00Z)`.

| Account | Opening combined balance | Closing combined balance |
| --- | ---: | ---: |
| fefundsadmin.sputnik-dao.near | 1610269.316440681058391094897654 | 1913463.450661649657631982695779 |
| 1csfundsadmin.sputnik-dao.near | 502798.938526000132848385595843 | 270.875891412420848813311023 |
| buybacks.multisignature.near | 858247.431221699682400472167004 | 2014526.467298357764650388041622 |

| Account | External native inflow | External native outflow |
| --- | ---: | ---: |
| fefundsadmin.sputnik-dao.near | 303194.134220968599240887798125 | 0 |
| 1csfundsadmin.sputnik-dao.near | 265.936280481103725627715181 | 0.000000000000000000000001 |
| buybacks.multisignature.near | 653485.036076658082249915874618 | 0 |

Two successful native transfers from `1csfundsadmin` to `buybacks` are separate
internal legs: 1 NEAR on 28 August and 502,793 NEAR on 9 September. Their exact
receipt IDs and DAO parent/callback records are retained in results 76 and 80.
Each transfer is counted once, with an outflow/inflow leg, and the 502,794 NEAR
cancels from group external totals. The successful transfer receipts have failed
sibling DAO callbacks; complete-chain settlement and final proposal state are
not inferred from local transfer success.

| Account | Stock change minus successful native flow net |
| --- | ---: |
| fefundsadmin.sputnik-dao.near | 0 |
| 1csfundsadmin.sputnik-dao.near | +0.001084931184274800000000 |
| buybacks.multisignature.near | 0 |

Group external inflow is 956945.106578107785216431387924 NEAR and outflow is
one yoctoNEAR. The resulting net is 956945.106578107785216431387923 NEAR,
against a combined stock increase of 956945.107663038969491231387923 NEAR.
The difference is exactly `1084931184274800000000` yoctoNEAR. It is not booked
as fees, refunds, rewards or revenue. Existing evidence does not independently
allocate those adjustments. Successful function-call deposits are already in
native flows: 0.6 NEAR received by `1csfundsadmin` and one yoctoNEAR sent by it.
Storage usage is not subtracted again as a monetary debit.

The saved day-close hashes bracket every observed in-window action, but are
not independent canonical midnight-edge proofs. Result 74's 63 source/lookup
days, export counts and duplicate/missing-match controls pass; this establishes
observed-record consistency, not complete historical ingestion. Its 244
outside-window actions and three failed callbacks remain excluded from accepted
flows. Fees, refunds, protocol credits and receipt funding can affect the bridge;
execution time is not necessarily sender debit time. Zero differences do not
establish complete coverage. Eight weekly flow tables do not supply eight weekly
stock reconciliations: only the full-window opening and closing states exist.

## Observed asset evidence and request-only records

The saved evidence distinguishes these layers:

| Layer | Supported observation | Limit |
| --- | --- | --- |
| Native account stocks | Exact liquid/locked values at six historical states. | Account control, beneficial ownership and multi-asset holdings are separate questions. |
| Direct internal asset movement | Successful `mt_transfer` receipt `4sBxF4Uut6w9Kv6kgcwzLBVKk8MTgEEu6yaETfDNN3QL` at `intents.near`, with a matching NEP-245 log. | Movement is not a swap, purchase or verified fee distribution. |
| Proposal/vote requests | Seven nested `mt_transfer` request records, plus the one direct observed call. | Repeated votes, an add-proposal call and a rejected vote are not additional transfers. One parent is linked to the actual child by receipt ID and exact args; the others remain requests. |
| Closed withdrawal context | Saved internal transfer credit, internal `mt_burn`, `wrap.near/near_withdraw` call and native payout already traced in results 47–54. | Unwrapping and internal asset debiting are not actual native supply destruction or a purchase; fee origin remains unverified. Native payout is already in result 80 and is not added again. |
| Exchange execution | No explicit verified order/fill or asset-for-asset purchase record in this saved subset. | Verified purchase amount remains null; absence in this subset does not establish nonoccurrence. |

The direct internal transfer debits `1csfundsadmin.sputnik-dao.near` and credits
`c0addac935f49baee1909a6fb4f08b57352a6d8c8ce7da27c59545fe45c5838c`, asset
`nep141:wrap.near`, exact amount `989998999899989998999899990` base units.
Its one-yoctoNEAR attached deposit is separate and already in native outflow.
The opaque recipient is not assigned to the native buyback wallet from a proposal
description. No asset decimals are assumed for this layer's ledger amounts.

The selected native receipt outcomes contain one NEP-245 transfer log and no
NEP-141 transfer logs. This is a query-selection limit: token transfers generally
execute on token contracts and may mention the wallet only in args/logs; relayed
Verifier calls may mention it only as an internal owner. Such rows need not have
one of the three wallets as native predecessor or receiver and can be absent
from SQL 45. A zero observed log count is not a complete token-flow total.

The closed result-54 context records `1252862790024676320487808800` base units
of `nep141:wrap.near` credited to internal account
`a8c56ebbdabc6b6709d4f946d54679db1e4006f5eeb6b3d49c897c86c70ba6cd`, followed
by the previously validated withdrawal. That internal account is not a verified
wallet alias or fee collector. The matching credit/debit amounts do not allocate
commingled funds or establish revenue origin. The provenance investigation stays
closed; this consolidation only projects its saved evidence.

## Historical contract evidence

All three accounts have matching reported code hashes at their two endpoints.
`fefundsadmin` and `1csfundsadmin` report
`4zSoHkLjJWZm34Psd4Eq2WUXHELt6LxtKmUXpsZWAECp`; `buybacks` reports
`2v9kZJHN4sogHuKtKHaqYAqQBazkqH2cjY1rrjQYvNQa`.
The saved `1csfundsadmin` calls expose `add_proposal`, `act_proposal` and
`on_proposal_callback` request interfaces. This does not establish a particular
Sputnik source release, a complete ABI, historical permissions or a buyback
implementation. No saved deployed WASM/source-version match or historical policy
state establishes those meanings. Matching endpoints do not rule out intermediate
code changes or configuration changes with unchanged code.

Proposal descriptions containing `payment-transfer`, `Network Fee`, signatures
or a named recipient are preserved as unverified metadata. They are not fee
calculations tied to product activity, exchange fills or proof of destination
ownership. Native balance accumulation, fee attribution and exchange execution
remain distinct measurements.

## Requirements that need additional data

1. Complete success-qualified NEP-141/NEP-245 logs and receipt identities across
   the target window, selecting owners/recipients in event data and arguments,
   not only native counterparties. Deduplicate by receipt/log/data/asset position
   and retain execution outcomes/callback coverage.
2. Asset metadata/units, exact historical token and internal-account boundary
   balances, and evidence associating internal IDs with the selected wallets.
   One internal transfer and one closed withdrawal are not that census.
3. Historical deployed contract artifacts/source matches and policy/fee-recipient
   configuration, plus fee-source/payer/calculation evidence separating revenue
   from principal, settlements, refunds and internal transfers.
4. Explicit exchange order/fill or signed settlement evidence linking assets
   paid and received to successful execution and beneficiary. Naming a wallet
   `buybacks` or transferring to it cannot supply this evidence.

Complete native adjustment/edge coverage also remains missing. The small
`1csfundsadmin` difference stays unallocated without residual-specific collection.
BigQuery access remains unavailable; this note prepares no new asset extraction
or wallet requests. Revenue, buybacks and actual supply burn remain null.

Offline reproduction to stdout:

```bash
.venv/bin/python analysis/33_consolidate_three_wallet_ledger.py
```

Source and code hashes are retained; raw captures and results 74–79 are unchanged.
