# Historical native balances: six-state comparison

This pilot compares exact native account stocks with the saved execution-dated
action layer for 24 August–18 October 2026 UTC. It does not identify revenue,
purchases, beneficial holdings, buybacks or actual supply burn. It cannot
complete a multi-asset ledger or weekly balance reconciliation from two states.

## Validated six-state result

[Result 78](../results/78_three_wallet_native_balance_comparison_2026-08-24_to_2026-10-18.json)
reproduces the recovery's `validation.json` byte-for-byte from the two original
successes and four recovery responses. All six are HTTP-200/JSON-RPC successes,
with matching request identities, block hashes/heights, byte lengths, checksums
and exact monetary strings. The original failed `opening-3` capture remains
unchanged. Independent raw-response integer arithmetic agrees with each stock
change and result-75 flow sum. No new source request accompanies validation.

Exact native comparisons in NEAR:

| Account | Closing combined balance − opening | Successful native inflows − outflows | Unexplained difference |
| --- | ---: | ---: | ---: |
| fefundsadmin.sputnik-dao.near | 303194.134220968599240887798125 | 303194.134220968599240887798125 | 0 |
| 1csfundsadmin.sputnik-dao.near | -502528.062634587711999572284820 | -502528.063719518896274372284820 | +0.001084931184274800000000 |
| buybacks.multisignature.near | 1156279.036076658082249915874618 | 1156279.036076658082249915874618 | 0 |

Group combined native balances rise from
2971315.686188380873639952660501 to 3928260.793851419843131184048424 NEAR:
an increase of 956945.107663038969491231387923 NEAR. The external action-layer
net is 956945.106578107785216431387923 NEAR after cancellation of the
502,794 NEAR between-wallet legs. The group difference, entirely in `1csfundsadmin`,
is exactly `1084931184274800000000` yoctoNEAR. No tolerance is applied.

All returned locked balances are explicitly `"0"`; no nonexistent accounts
were reported. `1csfundsadmin` storage usage increases from 550,056 to 553,750
bytes (+3,694). The other two storage values are unchanged. Each account's code
hash matches between endpoints; this does not verify unchanged contract policy,
economic purpose or beneficial ownership. Storage bytes are not another balance
debit to subtract.

The two exact zero stock-flow differences strengthen the bounded native-action
comparison but do not establish complete historical coverage or revenue origin.
The positive difference is not attributed to fees: refunds, contract rewards,
receipt-funding timing and missing credit/debit coverage remain possible net
contributors without independent adjustment measurements. Exact function-call
deposits are already in flows. Canonical midnight-edge qualifications remain.
All accounts retain `complete_balance_reconciliation=false`; fees, additional
adjustments, revenue, purchases and actual supply burn remain unavailable.
Native account stocks do not establish a complete multi-asset ledger, purchases
or holder value. The bounded withdrawal-provenance investigation stays closed.

## Saved boundaries and window alignment

SQL 28/result 28 select the maximum observed block height for each UTC day.
The saved anchors are:

| State | Height | Block hash | Saved timestamp UTC |
| --- | ---: | --- | --- |
| Opening | 212636216 | `ACuCLP9DEHaHn3ET8ohyQCJBfw6gnTLhNeMsjTgD3Lfu` | 2026-08-23 23:59:59.540769 |
| Closing | 220581912 | `76ZA6NE6s1MK1tk61djKwXs1kPbRmU4ofVtJfmKPENj1` | 2026-10-18 23:59:59.997115 |

These bracket the `[2026-08-24T00:00:00Z, 2026-10-19T00:00:00Z)` ledger
window. The first saved 24 August block is 212636217 at 00:00:00.148296 UTC.
All 2,254 in-window result-75 actions, including three failed callbacks, lie
after the opening anchor and at or before the closing anchor in both height
and timestamp. Only the 2,251 accepted successful local actions enter flows.

The baseline has 57 unique expected dates, observed block uniqueness and zero
missing hash/height/time or date-mismatch diagnostics. These are observed-source
checks. No saved canonical successor proof establishes the final block before
each midnight. The opening anchor is 459,231 microseconds before the start;
the closing anchor is 2,885 microseconds before the end. These time gaps do not
themselves establish missing blocks. Canonical edge completeness remains
qualified. Saved timestamps have microsecond precision; the account API echoes
height/hash rather than timestamps. No extra header request is included.

## Requests, retention and errors

[Result 77](../results/77_three_wallet_historical_balance_request_plan.json)
records six exact requests, inputs and source-code hashes. Each of
`fefundsadmin.sputnik-dao.near`, `1csfundsadmin.sputnik-dao.near` and
`buybacks.multisignature.near` is queried at each saved hash. No current/finality
substitution is allowed:

```json
{
  "jsonrpc": "2.0",
  "id": "<opening-or-closing>-<1-to-3>",
  "method": "query",
  "params": {
    "request_type": "view_account",
    "account_id": "<exact account>",
    "block_id": "<saved boundary hash>"
  }
}
```

The [documented account API](https://docs.near.org/api/rpc/contracts#view-account)
returns exact quoted `amount` and `locked`, integer `storage_usage`, `code_hash`,
block height and hash. A successful response must match the requested hash and
saved height. Account identity follows the recorded request and JSON-RPC ID;
the response need not echo it. Preserve any `storage_paid_at` and all raw fields.
Only ASCII unsigned u128 monetary strings are accepted; no float conversion or
display rounding enters arithmetic. Storage usage is bytes, not a monetary
adjustment to subtract again from account balance.

Use the existing public credential-free archival endpoint
`https://archival-rpc.mainnet.near.org`, listed in the
[official provider directory](https://docs.near.org/api/rpc/providers).
The endpoint is severely rate limited; retained history and availability for
these requests have not been tested during preparation.

[Analysis 31](../analysis/31_wallet_historical_balances.py) reuses the existing
byte-preserving HTTPS transport. There are at most six sequential attempts,
65 seconds before each, 15-second connection and 60-second request deadlines,
no automatic retries, redirects, endpoint fallback or credentials. A new run
directory receives the frozen plan/manifest and complete request bytes, response
body bytes, HTTP status/headers, endpoint, UTC retrieval timestamps, byte lengths
and SHA-256 in separate files. Creation is exclusive. Partial/error bodies and
the failed request are retained with `stopped.json`; no later request follows
an unsupported method, unavailable history, transport failure or ambiguous result.

The documented structured `HANDLER_ERROR/UNKNOWN_ACCOUNT` is a special explicit
absence observation. Its `requested_account_id`, `block_hash` and `block_height`
must match exactly. The [implementation's query error type](https://raw.githubusercontent.com/near/nearcore/2.9.0/chain/jsonrpc-primitives/src/types/query.rs)
includes these identifiers. Such absence is retained, and collection may proceed
to the other fixed requests. Liquid/locked/combined balances and affected deltas
remain null pending lifecycle evidence. An unstructured “not found”, wrong
account/block or missing history is not accepted as absence or zero balance.

## Comparison and adjustment register

For each account, using integer yoctoNEAR throughout:

```text
B_open  = opening.amount + opening.locked
B_close = closing.amount + closing.locked
delta_B = B_close - B_open
N       = successful native action inflows - successful native action outflows
R       = delta_B - N
```

`R` is an unexplained stock-flow difference, not a fee estimate or balancing
entry. Missing states leave `delta_B` and `R` null; observed flows remain
available separately. The group comparison sums the three stocks and uses the
external native net. Its 502,794 NEAR between-wallet legs cancel exactly.
Individual action nets are 303194.134220968599240887798125,
-502528.063719518896274372284820 and 1156279.036076658082249915874618 NEAR;
group external net is 956945.106578107785216431387923 NEAR.

| Component | Measured evidence or unresolved hypothesis |
| --- | --- |
| Successful TRANSFER actions | Exact native deposits already included in `N`; their economic purposes remain unclassified. A system predecessor alone does not establish a refund. |
| Function-call deposits | Exact accepted deposits already included: 0.6 NEAR received by `1csfundsadmin`, one yoctoNEAR sent by it to `intents.near`. Do not add them again as adjustments. Proposed nested transfer amounts are not payments. |
| Transaction conversion, prepaid gas and receipt execution charges | Wallet-attributable debits remain unmeasured. The transaction signer, predecessor and eventual fee funder can differ. Failed callbacks can consume gas while transferring no deposit. Recorded receipt `tokens_burnt` is not an exact wallet charge or actual supply burn; summing it would misattribute fees. |
| Unused-gas refunds and failed-action deposit refunds | Some may already appear as accepted native inflows. Exact purpose, payer/beneficiary, failure semantics and missing coverage require evidence before classification or any additional adjustment. |
| Contract execution rewards, epoch/staking rewards or other protocol changes | No wallet-specific exact adjustments are independently measured here. Require identified balance changes and causes; do not import network-wide reward amounts. |
| Creation/deletion and beneficiary proceeds | Require account lifecycle and beneficiary evidence. Explicit absence is not silently assigned zero. The selected action layer does not independently establish complete coverage of these changes. |
| Liquid/locked and storage context | Pure lock/unlock changes cancel in `amount+locked`. Storage collateral constrains spendability within the account amount and is not another stock debit. Storage usage changes alone do not establish fees. |
| Receipt funding/escrow at boundaries | Account funding/debit can precede receipt execution. Transfers committed before opening or still in flight at closing can make execution-dated `N` differ from stock changes. Exact funding and refund timing is missing; one-day source lookback/six-day tail is not a boundary-completeness proof. |
| Source/asset coverage | Missing ingestion, delayed or older-source receipts and canonical edge uncertainty remain possible. Tokens and internal Verifier balances need separate ledgers; the saved NEP-245 event is not native NEAR flow. |

The unresolved categories can overlap; they are not an independently measured
additive decomposition. `independent_additional_adjustments_yocto` and attributed
fees remain null. Exact zero arithmetic discrepancy would validate the comparison,
not prove complete coverage, revenue origin or economic reconciliation. No
0.00001-NEAR tolerance is needed for integer arithmetic; source/coverage limits
remain even when integer checks pass.

## Manual collection and offline validation

The one next manual collection command is:

```bash
.venv/bin/python analysis/31_wallet_historical_balances.py collect
```

Expected captures are saved under
`results/three_wallet_native_balances_2026-08-24_to_2026-10-18/<UTC>_<id>/`.
There are six request/response/metadata triples plus `run.json` and, after all
six validate, `validation.json`. No historical balances have yet been collected
by this preparation.

After the raw capture is available, validation is offline:

```bash
.venv/bin/python analysis/31_wallet_historical_balances.py validate \
  --run-dir results/three_wallet_native_balances_2026-08-24_to_2026-10-18/<UTC>_<id>
```

The intended durable comparison filename is
`results/78_three_wallet_native_balance_comparison_2026-08-24_to_2026-10-18.json`.
It can be supplied as a new `--output` path after capture validation; it is not
currently a measured result. Existing outputs are never overwritten. All raw
fields remain in the capture even when not projected into the comparison.

Focused checks use synthetic responses and block live networking:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_wallet*.py' -v
```

## Stopped opening-state capture and bounded recovery

The saved run
`results/three_wallet_native_balances_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a`
contains two validated HTTP-200/JSON-RPC-success opening states. Request/response
hashes, lengths, identities, timestamps and exact fields validate:

| Request | Account | Liquid yoctoNEAR | Locked yoctoNEAR | Storage bytes |
| --- | --- | ---: | ---: | ---: |
| opening-1 | fefundsadmin.sputnik-dao.near | 1610269316440681058391094897654 | 0 | 550832 |
| opening-2 | 1csfundsadmin.sputnik-dao.near | 502798938526000132848385595843 | 0 | 550056 |

Both echo the planned opening hash and height 212636216. The frozen plan and
all original source hashes reproduce unchanged. `opening-3` requested
`buybacks.multisignature.near` through `query/view_account` at
`ACuCLP9DEHaHn3ET8ohyQCJBfw6gnTLhNeMsjTgD3Lfu`. Its transport reports
`RemoteDisconnected: Remote end closed connection without response`, no HTTP
status, `body_complete=false` and a zero-byte response. The failed request/body
hashes and lengths match their metadata. This establishes transport failure.
Account absence, rate limiting and historical availability cannot be inferred.
No closing requests were attempted; a complete stock-flow comparison is
unavailable.

[Analysis 32](../analysis/32_recover_wallet_historical_balances.py) audits the
successful prefix and failed capture without changing analysis 31, result 77
or the original directory. [Result 79](../results/79_three_wallet_balance_recovery_plan.json)
records the audit, exact states, failure metadata, hashes of every original file
and four pending requests in their original order:
`opening-3`, `closing-1`, `closing-2`, `closing-3`.
Result 78 remains reserved for a validated complete stock-flow comparison.

The next manual command is:

```bash
.venv/bin/python analysis/32_recover_wallet_historical_balances.py recover \
  --original-run-dir results/three_wallet_native_balances_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a
```

The new directory will be
`results/three_wallet_native_balance_recovery_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a_recovery_01/`.
Creation is exclusive: a second invocation refuses before making requests.
The existing endpoint, 65-second spacing, timeouts, raw-byte retention,
account-absence rules and exact monetary validation are unchanged. Each of the
four pending states receives at most one attempt. This is an explicit manual
reattempt of the failed request plus three unattempted requests, with no
automatic retry or fallback. There are still six unique account/boundary pairs;
the combined attempt ceiling is seven, including the original failed attempt.

The two original successes are reused by validated reference, not recopied or
requested again. The failed original capture remains part of provenance even
after a later success. Any new failure stops recovery with its bytes retained;
no complete comparison is produced. On success, `validation.json` combines all
six states using the original comparison and its economic qualifications.
The comparison does not classify unexplained differences as fees or revenue.

Offline reproduction of result 79:

```bash
.venv/bin/python analysis/32_recover_wallet_historical_balances.py plan \
  --original-run-dir results/three_wallet_native_balances_2026-08-24_to_2026-10-18/20261107T145515Z_13ac190f879a
```

After manual recovery, `validate --recovery-dir <new-directory>` reproduces the
combined report without source requests. Focused recovery checks use local
fixtures, reject changed original/failed bytes and unexpected files, verify
four-request scope and pacing, retain null economic attribution and prevent
overwrites:

```bash
.venv/bin/python -m unittest discover -s tests -p test_wallet_balance_recovery.py -v
```
