# Priority 4: attribution coverage and selected delegated claim

[Result 97](../results/97_priority4_attribution_coverage.json) consolidates the
saved populations and [result 96](../results/96_sweat_relayer_attribution_trace_2026-09-23.json).
It preserves result 96 unchanged, adds the exact submission-block timestamp,
and records input paths and SHA-256 hashes. Result 92 retains the original
pre-collection assessment; it is not the current coverage status.

## Population evidence

The population window is **24 August–18 October 2026 UTC**. Rankings are among
**51 saved signing accounts**, the union of weekly top-20 signers, with eight
weekly rows per account. They are not an exhaustive period ranking or a count
of people/applications. The network denominator is **44,284,794 transactions**.
Receiver observations in result 19 are weekly top-20 original receivers, not
inner delegated destinations or a complete downstream census. Result 23 has
joint receiver/action/method buckets; a transaction can enter multiple buckets.

V = initial SUCCESS_VALUE; R = initial SUCCESS_RECEIPT_ID; F = initial FAILURE.
Unavailable means the selected export does not measure that component. Zero
DELEGATE_ACTION counts below are observed in result 20 for profiled accounts;
they do not exclude other authorization mechanisms. Selected examples are
separate from population statistics.

| Signer | Period transactions | DELEGATE_ACTION transactions | Receiving-contract evidence | Population initial outcomes | Selected downstream traces / unresolved coverage |
| --- | ---: | ---: | --- | --- | --- |
| sweat-relayer.near | 13,704,363 | 13,246,938 | Original: jars-oracle.sweat, spin.sweat, oracle.sweat. One inner case: claim.sweat → token.sweat. | Unavailable | One selected delegated claim: eight returned receipt outcomes, all successful. Population actors and settlement remain unmeasured. |
| intents.near | 2,769,479 | 0 | intents.near (all 2,769,479 original receivers) | Unavailable | No population-linked downstream case in this comparison. Verifier role does not establish swaps, users or revenue. |
| closemeat6237.near | 1,620,042 | 0 | v2.ref-finance.near; wrap.near; token account `17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1` | Unavailable | Ownership, economic funder and settlement remain unverified. |
| omni-relayer.bridge.near | 1,367,509 | 0 | omni.bridge.near, btc-connector.bridge.near, zcash-connector.bridge.near | Unavailable | Documented relayer association; no selected complete-chain census. |
| meteor-relayer.near | 1,264,098 | 1,239,064 | Selected original receivers include near, brn1.near, wrongzone2119.near; inner destinations unavailable. | Unavailable | No selected downstream trace; service/operator attribution remains unverified. |
| 0here.tg | 946,561 | Unavailable | No aggregate receiver profile in selected exports | Unavailable | No selected validated transaction graph. Endpoint increase +137,531. |
| bridge-mng.near | 938,958 | Unavailable | Unavailable | Unavailable | No selected validated graph or historical role anchor in this comparison. |
| escrow.ai.near | 894,583 | Unavailable | Unavailable | Unavailable | No selected validated graph or historical role anchor in this comparison. |
| tinykoala595.near | 778,588 | Unavailable | Result-23 joint buckets mainly v2.ref-finance.near / swap; wrap.near also observed. | F 715,518; V 62,955; R 115 | 18 preselected failed traces: each has three returned receipt outcomes and one failure. Endpoint increase +148,950. |
| relay.aurora | 743,318 | Unavailable | No selected receiver profile | Unavailable | Documented association; no selected downstream graph or historical operator verification. |
| wx-cruce.near | 413,281 | Unavailable | Result-23 joint buckets include the token account above and wrap.near / ft_transfer_call. | F 6,441; V 7,872; R 398,968 | Result 99 adds one selected transfer-call: six returned receipt outcomes, all successful. Population descendants remain unmeasured. Endpoint increase +137,767. |

Sources: results 18–20, 22–27, 35, 92, 95–97 and the
[account attribution register](account_attribution.md). Tinykoala's outcome
observations cover its six active weeks starting 7 September; wx-cruce's cover
its four active weeks starting 21 September. Their initial-outcome sums equal
their full-period signed transaction totals; earlier saved weeks have zero
transactions for those two accounts. Matching initial executor/receiver and
row counts establish observed-record consistency, not independent ingestion
completeness. The untracked endpoint increase of +354,120 is an aggregate,
not another account. Endpoint growth is not a period transaction total.

## Selected delegated-claim case

Transaction `4Hy1wk5EDGHDwAVd4FvFkUPALcsracRWZAW8Z8aB8gB4` is signed by
`sweat-relayer.near`. Its explicit Delegate action declares sender
`f5998a73a0b8172c8573c5dcff0ed342e6a3df46be1a26cdee6eaa4ec891ebb6`, receiver
`claim.sweat`, and one `claim` call with raw args `e30=` (UTF-8 `{}`), zero
attached yoctoNEAR and 300,000,000,000,000 gas units. The same authorization
appears in the initial receipt; these are two representations of one delegation,
not two actors. Public key, signature, nonce and maximum height are preserved
in result 96. The signature is not independently cryptographically verified;
account authority is not beneficial ownership or a human-user count.

One additional bounded archival `block` request establishes submission at
**216877932**, hash `F14YmYFQmFAjgy4DYqg4dK8o2NizhPQbm12VUWuNrz63`, timestamp
**2026-09-23T07:11:24.906615725Z**. Its hash matches the transaction outcome and
the saved canonical successor's prev_hash. The selected receipt's presence in
block A is kept separate from its execution block; a container date is not
substituted for submission or execution time.

The entire returned graph follows. Full block hashes, payloads, ordered actions,
parent edges and callback data IDs are retained in results 96–97.

| Outcome ID | Executor / action | Parent | Outcome |
| --- | --- | --- | --- |
| `4Hy1wk5EDGHDwAVd4FvFkUPALcsracRWZAW8Z8aB8gB4` | sweat-relayer.near / transaction | — | SuccessReceiptId |
| `H2MWGcWGCsxnThJg65QSNcpeHAjCvRcrhHPJRdqUTABp` | f5998a73a0b8172c8573c5dcff0ed342e6a3df46be1a26cdee6eaa4ec891ebb6 / Delegate | transaction | SuccessValue |
| `2iLefvugZmJmpNn52hcyMBjxcfYGGz5d6R8h4W1dXaDS` | claim.sweat / claim | initial receipt | SuccessReceiptId |
| `J4nAiTfwJzKGRrMxsSx3icnyThTmpJ8PWYd8fydasNuV` | token.sweat / ft_transfer | claim | SuccessValue |
| `MJmEDreQcta6okjyvXxBS3yKB77NNme9dgXpVArL42j` | sweat-relayer.near / Transfer (system predecessor) | ft_transfer | SuccessValue |
| `6rM6uHX6pXq3wB2kQoedaVzdsGy72UuFji28kgbodeDn` | claim.sweat / on_transfer | claim | SuccessValue |
| `Hp1tyRGgtwAHgu7NC2rfrBUZ9i9Nm7vQW4ZAceYrHsPy` | sweat-relayer.near / Transfer (system predecessor) | on_transfer | SuccessValue |
| `6Rx7mKFRgRneSEJWFNwKbf9A62fmLzs1JYNb5i7WJ9kb` | sweat-relayer.near / Transfer (system predecessor) | claim | SuccessValue |
| `J2nnH3MP6s9oqSd5C36MGHRsELQczSjxDn2mTo6CVnPS` | sweat-relayer.near / Transfer (system predecessor) | initial receipt | SuccessValue |

The response contains eight distinct receipt payloads and eight receipt outcomes:
seven SuccessValue and one SuccessReceiptId, plus the transaction root. All eight
emitted child identities have outcomes and payloads. Parent links and the one
callback dependency are unambiguous; no disconnected outcome, unresolved return
receipt, missing action payload or missing emitted outcome was detected. This
is a **complete returned graph**, not an independent proof of historical source
completeness or a population-wide success rate.

The ft_transfer argument and NEP-141 event both record exact amount
`66301094010694993` raw token units, from claim.sweat to the delegated account.
The callback returns `{"total":"66301094010694993"}` and emits a claim event
with the same claimed amount. The callback field/event value
`amount_to_burn` / `burnt` is `14455357019285`; it does not establish native
NEAR destruction, nor is token supply destruction independently measured here.
No token-decimal conversion is assumed.

Recorded transaction-plus-receipt charges sum to exact
`769026715343900000000` yoctoNEAR = **0.0007690267153439 NEAR**, counting each
outcome once. Deposits, attached gas and system-predecessor transfers are not
added as execution charges. The charge is not product revenue, actual supply
burn or proof of the economic fee funder.

With submission-window membership now established, one selected trace covers
**1 / 13,704,363 = 0.0000072969462353%** of saved Sweat signed transactions and
**1 / 13,246,938 = 0.0000075489143227%** of its DELEGATE_ACTION transactions.
Neither percentage supports extrapolation. The 18 tinykoala failure controls
remain a separate, purposively selected diagnostic set, not Sweat coverage.
The closed withdrawal-provenance investigation is not reopened or treated as
population evidence.

## Most material next attribution gap

Among the measured growth contributors, wx-cruce has **398,968 forwarded
initial outcomes** without population-wide descendant coverage. This is the largest explicit
forwarding population in the saved growth-outcome comparison. Whether those
calls reach successful receiving-contract execution or failed/missing callbacks
is material to interpreting its +137,767 endpoint contribution. It is separate
from the broader unresolved mapping of high-volume relayers to underlying
actors and economic funders.

The smallest mechanism test is **one EXPERIMENTAL_tx_status request** with
`wait_until: FINAL`, sender_account_id `wx-cruce.near`, and one independently
pinned transaction hash whose initial outcome is SUCCESS_RECEIPT_ID. Require
exact transaction/signer/initial-receipt identities, raw ordered arguments,
receiving contracts, all emitted outcomes and callback data links; count costs
once in exact units. Preserve the existing 8 MiB response cap, 65-second spacing,
15/60-second timeouts, one attempt, immutable bytes and no fallback. Stop after
one transaction or any error/partial/conflicting response. The result would
answer one mechanism/settlement case, not the population success rate.

**Identity dependency at result 97:** result 24 contains aggregates without success-bucket
transaction IDs. Result 25 samples failed tinykoala transactions, and the saved
cohort diagnostics do not pin a wx success identity. Saved header-only prefixes
cannot supply it. A receipt ID cannot substitute for a transaction hash, and
standard transaction-status RPC does not enumerate an account's history.
A one-day selection on 23 September from the verified `transactions`,
`execution_outcomes` and `blocks` tables could supply one candidate: preserve transaction
hash/signer/receiver/submission time/block hash/converted_into_receipt_id;
aggregate receipt matches before joining; require one transaction row, one
selected owner, one outcome, matching executor, SUCCESS_RECEIPT_ID and a known
execution block/time from a unique executed_in_block_hash lookup. Aggregate block
matches before joining as well. Direct day filters apply to every table. Boundary-crossing
or duplicate matches remain excluded/unresolved. Select the earliest eligible
candidate deterministically and report candidate/duplicate/missing counts.
That proposed selection required source access and separate BigQuery authorization,
which remained unavailable. It was not executed. The bounded free lookup below
subsequently supplied a candidate without that query.

## Selected wx transfer-call and bounded public history access

[Results 98–99](wx_cruce_case_study.md) add a saved-input identifier audit and
one successful transfer-and-callback case. The documented credential-free
FastNear account-history endpoint supports signer and height-range filters.
After excluding an initial storage_deposit / SuccessValue candidate, one bounded
five-row continuation and one indexed method-screening batch supplied an
ft_transfer_call candidate. Its exact canonical receiver/actions, initial
SuccessReceiptId and submission header were then validated. Six data requests
in total returned 70,091 bytes; there were no retries, block scans, BigQuery
queries or further history pages. The excluded capture remains unchanged.

Transaction `9KwjactRhTarKjtjGYTZK9igXwub963qhS5anWFXP9NN` was signed by
wx-cruce.near at **2026-09-23T16:17:16.824648967Z**, block **216929956**.
The returned chain is wrap.near.ft_transfer_call →
v2.ref-finance.near.ft_on_transfer → wrap.near.ft_resolve_transfer, with three
successful system-predecessor transfer branches. All six returned receipt
outcomes succeeded, with no missing emitted action outcome or unresolved
callback dependency. Recorded charges are **0.0007174786101312 NEAR**, counted
once per outcome including conversion at the transaction root. No explicit
Delegate action appears; the signer is not a verified person or beneficial owner.

The exact transfer amount is `2041882904280066641796431` raw wrap.near token
units and msg is empty. Receiver return is JSON string "0"; resolver/final
return is the full amount. This supports one accepted transfer-and-callback,
consistent with funding/deposit. It supplies no swap/output-asset, revenue or
purchase evidence, and Ref's internal credit is not independently verified.
The case is **1 / 413,281** signed wx transactions and **1 / 398,968** forwarded
initial outcomes. Population settlement rates remain unmeasured; the table
keeps this selected case separate from aggregate initial statuses. The original
result 97 and its earlier missing-identity assessment are preserved unchanged.

## Offline reproduction

```bash
.venv/bin/python analysis/41_consolidate_priority4.py report \
  --run-dir results/sweat_submission_block_time/20261108T004552Z_9f57ad2f6291 \
  --output results/97_priority4_attribution_coverage.json --check
```

The report path, checksums and generation are deterministic. Report/validation
commands disable network operations; collect-time is a separate, consumed
one-request slot. Result 96, all original captures, Neardata's paused bulk work
and the submission tag are preserved. Broad historical attribution, full-window
execution-chain coverage and economic funder/ownership attribution remain open.
