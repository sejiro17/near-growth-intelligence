# Selected wx-cruce transfer-and-callback case

[Result 98](../results/98_wx_cruce_candidate_source_assessment.json) records the
saved-identifier search and initial bounded lookup specification.
[Result 99](../results/99_wx_cruce_forwarding_case_2026-09-23.json) preserves
canonical identities, the complete returned graph, exact arguments, logs,
callback links and input hashes. It is one selected mechanism case, not a
population success estimate.

## Candidate acquisition and exclusions

The pre-collection inventory fingerprints 512 saved result files. Seven contain
wx-cruce.near, but their aggregate/coverage records expose no eligible transaction
or receipt ID. Existing header-only prefixes do not supply transaction IDs.
The [public FastNear Transactions API](https://tx.main.fastnear.com/) documents
POST /v0/account with signer-role filters, height bounds, cursor and a row limit,
and POST /v0/transactions for up to 20 hashes. The reviewed
[source schema](https://github.com/fastnear/explorer-api/blob/7dcbdb449eb400a9a78883b3ae9d53fa42282fbe/openapi/openapi.yaml)
specifies an inclusive lower and exclusive upper height bound. Anonymous access
worked for these samples; this is not a guarantee of complete historical retention
or unrestricted service availability. No credentials or paid access were used.

The lookup used saved 23 September bounds [216835292, 216976125), is_signer=true,
ascending order and no success filter. The first one-row candidate,
`7wtUpRBRj8wWXx9trTrDaNtB69vDphwhkwPacfGwwqrd`, is signed by wx-cruce.near and
calls wrap.near.storage_deposit. Canonical initial outcome was SuccessValue,
so it was ineligible for the requested forwarding case. Its scope-rejection
capture remains intact; no descendants were interpreted for that candidate.
This was not an HTTP/JSON-RPC failure and was not counted as a forwarding failure.

After that exclusion, one explicitly bounded continuation page returned five
identities. One indexed five-hash batch exposed their ordered methods: two
storage_deposit calls, one register_tokens and two ft_transfer_call calls.
The earlier ft_transfer_call by (submission height, transaction index) was selected.
The index's success flag was not an eligibility or downstream-success test.
Canonical status then verified its signer, receiver, exact ordered actions and
initial SuccessReceiptId; one exact submission-header request established the
date before descendant interpretation. No receipt-origin lookup was necessary.

The six data requests comprised two tiny history pages, one five-hash batch,
two canonical status lookups and one submission header. All returned HTTP 200
and complete bodies, totaling **70,091 bytes**. Each retained exact request JSON
and HTTP bytes, response bytes, ordered HTTP headers/status, UTC retrieval times
and SHA-256, with an 8 MiB cap, 65-second pacing, 15/60-second timeouts and no
retry, redirect, host fallback or further pagination. The first candidate and
its stopped.json were preserved separately. No block scan or BigQuery query ran.

## Canonical identities and scope

- Transaction: `9KwjactRhTarKjtjGYTZK9igXwub963qhS5anWFXP9NN`.
- Network signer: `wx-cruce.near`; receiver: `wrap.near`.
- Submission: block **216929956**, hash `5g9o6GLjnU2r56PkRkVY92PQEFNQp82733mmULRDXFTW`,
  **2026-09-23T16:17:16.824648967Z**. Indexed height/timestamp exactly match the
  canonical header, placing the transaction in the original research window.
- Initial receipt: `G4nXXsrwfdJhAJxoUymRJ7Qbo1wgqPrzrwjtorzPaQ6s`.
  Its SuccessReceiptId points to the resolver callback, not directly to the
  receiver's ft_on_transfer receipt.
- No explicit Delegate action appears. Receipt predecessors distinguish
  wx-cruce.near, wrap.near and system; they do not establish another delegated
  signer, a human identity, beneficial ownership or the economic fee funder.

## Returned receipt graph

| Outcome ID | Executor / method | Parent | Status |
| --- | --- | --- | --- |
| `9KwjactRhTarKjtjGYTZK9igXwub963qhS5anWFXP9NN` | wx-cruce.near / transaction | — | SuccessReceiptId |
| `G4nXXsrwfdJhAJxoUymRJ7Qbo1wgqPrzrwjtorzPaQ6s` | wrap.near / ft_transfer_call | transaction | SuccessReceiptId |
| `DrL6tNW3monGWuP7TLk1tHF6JpfjHPUPjX5aaC8iyvz2` | v2.ref-finance.near / ft_on_transfer | ft_transfer_call | SuccessValue |
| `ASWbjqakfJyLhtEhye8R7iEZvdNsBDHd9pgSWke5LnLh` | wx-cruce.near / Transfer | ft_on_transfer | SuccessValue |
| `9s1PkW3w87pnqDE8kcHLW4pBx8r1bipTFACyaURZgdAf` | wrap.near / ft_resolve_transfer | ft_transfer_call | SuccessValue |
| `HUZnU3PXpZBRS31bQh8usaXiC2VqXCNems7E13CFVMTV` | wx-cruce.near / Transfer | ft_resolve_transfer | SuccessValue |
| `9hy8qJne3FfGFJDTzcAVLbJ55xyUVVEcGwsM6uu6TPUG` | wx-cruce.near / Transfer | ft_transfer_call | SuccessValue |

There are six distinct returned receipt payloads and six receipt outcomes,
plus the transaction root. Five receipt outcomes are SuccessValue and one is
SuccessReceiptId. All six emitted child IDs are covered, with no missing action
payload/outcome, duplicate key, ambiguous parent, disconnected outcome or
unresolved return receipt. One callback data dependency is matched: Ref's
ft_on_transfer produces the data consumed by wrap.near.ft_resolve_transfer.
The three system-predecessor transfer branches also succeeded. This is
consistency and coverage of the **returned graph**, not independent proof of
historical ingestion completeness or a population settlement rate.

## Exact arguments, returns and interpretation

The transaction and initial receipt represent the same ft_transfer_call; they
are not two transfers. Raw base64 arguments are retained in result 99. Decoded:

```json
{"receiver_id":"v2.ref-finance.near","amount":"2041882904280066641796431","msg":""}
```

The exact amount is **`2041882904280066641796431` raw wrap.near token units**,
with 1 attached yoctoNEAR. The initial log records that amount moving from
wx-cruce.near to v2.ref-finance.near. Ref receives ft_on_transfer with
sender_id=wx-cruce.near, the same amount and empty msg. Its successful return
is JSON string `"0"`. The resolver receives the same sender/receiver/amount,
then successfully returns JSON string `"2041882904280066641796431"`;
the transaction's final return matches.

[NEP-141](https://github.com/near/NEPs/blob/master/neps/nep-0141.md#ft_on_transfer)
defines the receiver return as unused tokens, and the resolver return as tokens
spent by the sender. These observations are consistent with zero unused tokens
and acceptance of the full transferred amount. Historical deployed contract
code and Ref's exact internal account credit were not independently verified;
the standard alone does not prove a particular internal accounting policy.
Token decimals are not assumed or converted here.

**Strongest supported classification: successful token transfer-and-callback
into v2.ref-finance.near, consistent with funding/deposit.** The empty message,
returned calls and logs supply no swap action, output asset, price or purchase
record. They do not independently establish internal exchange balances, later
trades, fee attribution, revenue, fresh native-token purchases or holder value.
Absence of such evidence in this selected graph is not proof those activities
never occurred elsewhere.

Recorded transaction-plus-receipt execution charges total exact
`717478610131200000000` yoctoNEAR = **0.0007174786101312 NEAR**. Each outcome is
counted once. Attached deposits, raw FT amounts and system-predecessor transfers
are not added as spending; recorded charges are not actual native supply burn
or product revenue.

## Population coverage and remaining gap

This case covers **1 / 413,281 = 0.0002419661199%** of saved wx signed transactions,
and **1 / 398,968 = 0.0002506466684%** of its initial SUCCESS_RECEIPT_ID population.
The selection is purposive and conditional on method/eligibility; it supplies no
population success rate, swap rate, user count or revenue estimate. The other
screened records are not added to downstream-coverage counts. The 18 tinykoala
controls and selected Sweat case remain separate evidence sets.

The missing-identifier dependency is resolved for this one case without
BigQuery or broad retrieval. Population-wide receiving-contract/descendant
coverage, economic actor/funder attribution and actual exchange execution
remain incomplete. No further collection is part of this case.

## Offline reproduction

```bash
.venv/bin/python analysis/43_select_wx_forwarding_case.py report \
  --output results/99_wx_cruce_forwarding_case_2026-09-23.json --check
```

The report command disables network operations. Collection commands consume
separate immutable slots and are not retry commands. Input fingerprints and
raw captures live under results/wx_cruce_attribution_2026-09-23, outside the
dashboard's runtime inputs. Existing evidence, model results, paused bulk work
and the submission tag are preserved.
