# Known wallet assets and remaining discovery coverage

[Result 102](../results/102_known_asset_wallet_coverage_2026-08-24_to_2026-10-18.json)
reproduces result 80 before projecting its asset evidence. It preserves exact
base-unit strings, unique receipt/log/data/asset positions, source hashes and
unavailable classifications. It does not revise the native ledger or reopen
the closed withdrawal-provenance investigation.

## Supported identities and historical evidence

All identifiers below concern mainnet. The ledger execution window is
24 August–18 October 2026 UTC.

| Identity | Evidence already retained | Historical role limit |
| --- | --- | --- |
| `wrap.near`; internal asset `nep141:wrap.near` on `intents.near` | Successful NEP-245 transfer on 9 September and the closed result-54 unwrapping context. | One identified asset, not a census of token contracts. Base units remain exact; this pilot makes no metadata/decimals request. |
| `1csfundsadmin.sputnik-dao.near` as an internal owner | Receipt `4sBxF4Uut6w9Kv6kgcwzLBVKk8MTgEEu6yaETfDNN3QL` successfully transferred `989998999899989998999899990` units to the internal recipient below. Matching action and log identify the sender explicitly. | A direct association with this internal owner is established, independently of a withdrawal destination. Purpose, fee origin and beneficial ownership remain unverified. |
| `c0addac935f49baee1909a6fb4f08b57352a6d8c8ce7da27c59545fe45c5838c` | Recipient of that successful internal transfer. Proposal 10 has a parent-child link to the call. | A description names the buyback wallet; no saved evidence verifies this opaque ID as its alias or proves a purchase. |
| `c19da9ebe8e0c14892a98403fe6ae4bc4b81ac1fd83cb568b849ec685716c5e2` | Proposal/vote requests for `990000000000000000000000000` units of the same asset. | Request evidence only; no successful execution link in this subset. |
| `c6c1294fba977ddd14fc98e4f1de62b492d62a5d167ff3a43f0da8878a713819` | Proposal requests, including a rejected vote, for `990099009900990099009900991` units. | Neither proposal creation nor a rejected vote establishes a transfer. |
| `a8c56ebbdabc6b6709d4f946d54679db1e4006f5eeb6b3d49c897c86c70ba6cd` | Closed result 54: internal credit followed by the verified withdrawal. | Fee-collector role and native-wallet alias remain unverified. No additional provenance requests. |
| `51e8f94d77b5e90dc9852ca6113771e11e8382ce69473a75e313e41665de7cbe` | Sender of the signed internal credit in the same closed case. | Public-key correspondence does not establish organizational ownership or fee origin. |

The eight decoded request records are seven nested proposal/vote observations
and one direct call. One proposal observation links to that direct call; it is
not a second movement. Only one unique successful internal transfer appears in
the selected native-counterparty export.

Historical wallet evidence remains limited to endpoint code hashes and observed
interfaces. Both DAO accounts report
`4zSoHkLjJWZm34Psd4Eq2WUXHELt6LxtKmUXpsZWAECp` at the saved opening and closing
states. The buyback-named account reports
`2v9kZJHN4sogHuKtKHaqYAqQBazkqH2cjY1rrjQYvNQa` at both states.
`1csfundsadmin` has observed `add_proposal`, `act_proposal` and
`on_proposal_callback` calls. There is no saved deployed-WASM/source match,
historical policy or fee configuration establishing revenue/buyback roles for
the full window. Matching endpoint hashes do not exclude intermediate code or
configuration changes. Recipient descriptions and account names do not fill
these gaps.

## Bounded stock pilot

Two `query` calls use `request_type: call_function`, contract `intents.near`,
method `mt_balance_of`, arguments
`{"account_id":"1csfundsadmin.sputnik-dao.near","token_id":"nep141:wrap.near"}`.
The [NEP-245 interface](https://github.com/near/NEPs/blob/master/neps/nep-0245.md)
defines this view and exact U128-string result. That standard is an interface
reference, not proof that a particular historical deployment exposes it;
each response must pass the historical identity and result checks.

| Boundary | Saved height | Exact block hash |
| --- | ---: | --- |
| 23 August close | 212636216 | `ACuCLP9DEHaHn3ET8ohyQCJBfw6gnTLhNeMsjTgD3Lfu` |
| 18 October close | 220581912 | `76ZA6NE6s1MK1tk61djKwXs1kPbRmU4ofVtJfmKPENj1` |

These are the native ledger's saved observed day-close anchors. They bracket
the selected actions; independently complete canonical midnight edges remain
unestablished. The pilot measures two stocks for **one known owner–asset pair,
one of three selected wallets**. The complete asset-pair denominator is unknown.
It does not measure complete flows, revenue or purchases.

Maximum collection is two sequential free archival requests, with 65-second
spacing, 15/60-second connection/request timeouts and an 8 MiB body cap per
request. No retries, redirects, alternate endpoints or credentials are used.
Immutable captures retain request bytes, response bytes, HTTP status/headers,
UTC retrieval times and hashes. Successful captures are reused; failed captures
stop collection without retry. Unavailable history, unsupported methods,
nonexistent accounts and malformed responses remain unavailable, not zero.

Offline interpretation compares the exact closing-minus-opening internal stock
with the net of the **selected** saved internal movements. Any difference
remains unmeasured net movements relative to that subset. It is not booked as
fees, revenue, an invented balancing transfer or native-balance adjustment.
Wrapping and internal representations are separate asset ledgers and cannot be
added as extra economic capture to the already counted native withdrawal.

## Validated two-state result

[Result 103](../results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json)
validates the two HTTP-200 captures, request identities, returned block hashes
and heights, exact result bytes, retrieval timestamps and checksums. The view
calls at both historical hashes returned valid balances. The two bodies total
481 bytes; no other chain requests were made for this pilot.

| Comparison | Exact `nep141:wrap.near` base units |
| --- | ---: |
| Opening internal balance | `990000000000000000000000000` |
| Closing internal balance | `1000100010001000100010` |
| Closing minus opening | `-989998999899989998999899990` |
| Net of the one selected successful transfer | `-989998999899989998999899990` |
| Stock change minus selected flow net | `0` |

The observed transfer accounts exactly for this known owner's endpoint decrease
in this asset. This is a stronger stock-and-movement link than a proposal amount
or native inflow alone. It does not prove that no other offsetting movements
occurred, enumerate other assets, establish the opaque recipient's ownership or
identify exchange execution or fee origin. No amounts are added to native flows,
revenue or purchases. The native `1csfundsadmin` difference remains unallocated.

Captures are retained separately under
`results/known_asset_wallet_stocks_2026-08-24_to_2026-10-18/`, with one immutable
opening and one closing directory. Result 103 records every capture-file hash.
Its independent offline reproduction command is:

```bash
.venv/bin/python -B analysis/46_known_asset_wallet_coverage.py validate --check --output results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json
```

## Remaining evidence requirement

Complete discovery needs a retained historical owner/recipient index of
success-qualified NEP-141 and NEP-245 events, including mint, burn, transfer,
reversions and receipt/outcome links, plus historical internal-account
associations. SQL 45 selects native predecessor/receiver accounts; token
transfers can mention owners only inside args/logs and fall outside that
selection. A native `view_account` response has no complete asset list. A
known-token balance call also cannot discover other contracts or assets held
and fully spent during the window. A current holdings list would not solve that
historical-flow problem.

No accessible complete index is established by the saved evidence. BigQuery
access is unavailable, and neither an unverified replacement index nor a scan
is assumed. Missing assets, balances and flows remain null, not zero. Beyond
discovery, fee-origin attribution still needs historical recipient/configuration
and payer/calculation evidence; purchase attribution needs successful exchange
execution identifying both paid and received assets. Native holdings, internal
holdings, product revenue and exchange execution remain separate measurements.

Offline reproduction and checks:

```bash
.venv/bin/python -B analysis/46_known_asset_wallet_coverage.py report --check --output results/102_known_asset_wallet_coverage_2026-08-24_to_2026-10-18.json
.venv/bin/python -B -m unittest discover -s tests -p 'test_known_asset_wallet_coverage.py' -v
```

The inventory and validation commands disable network access. Explicit output
creation is exclusive; existing evidence is never overwritten. Collection is
isolated behind the `collect` command and has the fixed scope above.
