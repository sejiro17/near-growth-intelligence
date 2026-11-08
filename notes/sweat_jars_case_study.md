# Selected Sweat → jars-oracle mechanism

The diagnostic targets one transaction submitted on **23 September 2026 UTC**
with network signer `sweat-relayer.near` and transaction receiver
`jars-oracle.sweat`. The saved receiver bucket contains 3,039,759 transactions
across 24 August–18 October, as summed from weekly top-20 original-receiver
records. It is not a complete descendant census or a one-day count.

## Selection and evidence limits

The fixed sequence has four request slots:

1. One public FastNear account-history page for `jars-oracle.sweat` in receiver
   role, ascending within saved 23 September heights `[216835292, 216976125)`,
   capped at five candidates. No cursor is followed.
2. One indexed transaction-details batch for precisely those returned hashes.
   Missing or duplicate records stop selection. The earliest candidate with
   both the target signer and receiver is selected, without a success/method
   filter. No eligible record means no further lookup.
3. One canonical archival `EXPERIMENTAL_tx_status` request for that hash and
   `sender_account_id: sweat-relayer.near`, with `wait_until: FINAL`.
4. One canonical submission-block request verifying height, hash and exact
   nanosecond timestamp against the index and selected UTC date. Existing
   validated matching captures are reused instead of requesting again.

Indexed identities, canonical ordered transaction actions and initial-receipt
receiver/outcome must agree. Initial failure is retained rather than replaced
with another candidate. Descendants are interpreted only after the canonical
submission-date gate. Complete returned graph coverage is assessed from unique
outcomes/payloads, emitted children, return pointers, parent links and callback
data dependencies; it does not independently establish source retention.

Each new request has 65-second spacing, 15/60-second connect/request timeouts and
an 8 MiB body cap. There are no automatic retries, redirects, alternate endpoints,
credentials or pagination. Requests/responses, HTTP status/headers, UTC retrieval
times, SHA-256 hashes, code snapshots, validation results and errors are retained
immutably under `results/sweat_jars_attribution_2026-09-23/`.

The public index is the already reviewed
[FastNear Transactions API](https://tx.main.fastnear.com/), with documented
account and five-hash batch methods. Canonical controls use the same free
`https://archival-rpc.mainnet.near.org` endpoint as earlier selected cases. A
successful response establishes point availability, not complete historical
index coverage or unrestricted service access.

Explicit returned `Delegate` actions establish declared delegation; a changed
receipt predecessor does not. Ordered raw actions, exact deposits, gas, base64
arguments, decoded UTF-8 and execution logs are retained. Decimal JSON argument
lexemes are strings in the decoded mirror, with the raw text authoritative.
Recorded `tokens_burnt` charges are summed once per transaction/receipt outcome,
not once per method/action occurrence. They are not attributed product revenue
or independently measured native supply destruction.

This is one selected mechanism case. No population success rate, human-adoption
claim, verified economic purpose or holder-value effect follows from it. The
earlier selected delegated claim remains separate; neither case is extrapolated
to other methods, dates or destination records. The closed withdrawal-provenance
investigation and other original completion criteria are unaffected.

## Validated selected case

[Result 106](../results/106_sweat_jars_selected_mechanism_2026-09-23.json)
reproduces the four captures and the interpretation. All five indexed candidates
matched the signer/receiver requirements; selection was by earliest height/index,
not method or outcome. The selected transaction is
`5WPinUvUZgj9hETPGEHooRNUSVW56g7cAeagLSk5vPug`, submitted at height 216835295,
hash `EfqWgHidykoyeXWxuD9Zf5NUhGqvRnP8ezo4BGBVAXwQ`, at exactly
**2026-09-23T00:00:02.273417299Z**. Indexed and canonical identities/actions agree.
The four HTTP-200 responses total 84,617 body bytes. No matching prior captures
were found for reuse; no retries, cursor requests or additional requests occurred.

Network signer is `sweat-relayer.near`. Original receiver and explicit delegated
sender are `jars-oracle.sweat`; the delegated receiver is `token.sweat`.
The signed Delegate and key are retained, without independent cryptographic
signature or beneficial-ownership verification.

| Step | Receipt ID | Observed behavior |
| --- | --- | --- |
| Delegate processing | `9bLGRCP2dUAMbghFMMjBgk9scXm5rswjDEc8ZdgbyvyK` | jars-oracle processes the Delegate and emits the token call. |
| Token transfer-call | `4UijpeS5JPTtXHbzqSn1KDG2VxwSRNqE2rRgj4j8srvi` | `token.sweat.ft_transfer_call`: exact amount `3000000000000000000` base units, receiver `v2.jars.sweat`, one yoctoNEAR attached. NEP-141 log matches the transfer. |
| Receiver application | `7GmQFW6evEgXx7ucHwE38WUfpMERYJHNcqdZUwLkeRpc` | `v2.jars.sweat.ft_on_transfer`: deposit log records the beneficiary/product/amount; return is JSON string `"0"`. |
| Resolver callback | `A9vZqVjbfJqoVUC5JzUUhjumrgMjLZkjBRL3TCSU3xyd` | `token.sweat.ft_resolve_transfer`: matched data dependency; return is the full amount, consistent with acceptance. |

The payload's `msg.type` is `airdrop`, with product ID
`steps_365d_20000_10000_tiered_v1`, beneficiary
`bf64bc9bba2145608d50859f3b1ae145df34d6d9cdf352ab7896292cd68ef33c`,
booster 3000 and booster timestamp 1789963200000. Raw base64, UTF-8, nested
message, ticket fields/signature and exact monetary strings are retained.
No token-metadata request was made; amounts remain raw base units.

**Application qualification:** the receiver's `sweat_jar` v4.2.3 deposit event
records the beneficiary and amount, but its `apply_booster` event has
`applied: []` and that beneficiary in `rejected`. All eight returned receipt
outcomes succeed (seven SuccessValue, one SuccessReceiptId), with one matched
callback dependency and no missing children, payloads, ambiguous parents or
unresolved returns. Receipt success therefore does not establish every requested
application effect. Four additional successful terminal receipts return to the
relayer; all identifiers and raw actions remain in the complete returned graph.

Recorded transaction-plus-receipt charges are exactly
**0.0012424938755553 NEAR**, counted once per outcome, not once per repeated
transaction/receipt action description. Successful transfer, recorded deposit
and rejected booster are observed. Independent beneficiary state, genuine
beneficial ownership, product participation, revenue, token purchases, native
burn and investment value are not established.

Coverage is **one selected transaction / 3,039,759 saved destination-bucket
transactions = 0.000032897344822402…%**, also one / 13,704,363 Sweat-signed
transactions. These are selection fractions, never success rates. The bucket
covers the original eight-week window; there is no complete one-day denominator.
The result establishes a second selected Sweat mechanism, distinct from the
earlier delegated claim. It does not classify the whole bucket as airdrops,
deposits, successful activity or independent users.

Offline reproduction, with no collection:

```bash
.venv/bin/python -B analysis/49_trace_sweat_jars.py report --check --output results/106_sweat_jars_selected_mechanism_2026-09-23.json
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```
