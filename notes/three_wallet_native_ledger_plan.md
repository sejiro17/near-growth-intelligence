# Three-account native flow ledger: design and saved-export validation

The target accounts are exactly:

- `fefundsadmin.sputnik-dao.near`
- `1csfundsadmin.sputnik-dao.near`
- `buybacks.multisignature.near`

All are mainnet account identifiers. Selection does not verify their historical
ownership or revenue/buyback roles. The target execution interval is
24 August–18 October 2026 UTC. Native NEAR is one asset layer: token transfers
and internal Verifier balances are outside this extraction.

## Existing evidence and closed provenance

SQL 39 and result 47 preserve actual `receipt_actions`, `execution_outcomes` and
`blocks` rows, including source identifiers, predecessor/receiver, signer,
delegation flag, nested-JSON args, local status and execution block identity.
Result 48 reproducibly decodes 22 successful transfers to the first account on
23 September, totalling 8,000.969220749197522847764034 NEAR. These remain
economically unclassified; the new export must be compared with their exact
receipt/action keys, counterparties and integer amounts.

Result 54 establishes one successful signed internal transfer followed by a
native withdrawal after unwrapping. It does not establish fee origin or
allocation within commingled balances. The traced internal account/key is not
assumed to be a fee collector, and this provenance investigation remains closed.
No additional credit tracing is part of this extraction.

Result 64 establishes the deployed table name `receipt_origin_transaction`.
Its field schema and descendant mapping are not saved. SQL 45 therefore makes
no guessed origin-table join and does not substitute the initial-only
`transactions.converted_into_receipt_id` link. Wallet-to-wallet counterparties
do not require an origin transaction join; historical economic attribution does.

## Smallest useful full-window candidate extraction

[SQL 45](../sql/45_three_wallet_native_flow_candidates.sql) reads three verified
chain tables. Every read has direct partition predicates for **23 August–24
October**, 63 dates. This adds one source lookback day and six lookup-tail days
to the 56-day target. It does not assume older-source receipts or later indexing
cannot cross those boundaries. Unmatched evidence remains unresolved; no wider
lookback or tail is silently added.

Select receipt actions whose predecessor or receiver is one of the three
accounts. Retain all action kinds, not just TRANSFER, so function-call deposits,
staking/deletion and other balance-change leads remain visible. Inclusion in
the export does not establish a monetary transfer. Accept flows by **actual
execution timestamp**, retaining source and outcome-record dates separately.
Observed failures, outside-window executions, duplicate keys, ambiguous outcomes
and unavailable fields are retained as diagnostics, not counted as successful
native payments.
Same-block cross-shard order remains unresolved; an action index is local to
its receipt, not a global ordering key. Period flow totals do not establish
within-block account before-states.
Delegate envelopes are retained without expanding their inner actions; their
unmeasured native amounts remain an explicit coverage gap.

Required identities include receipt/action index, source block hash/height/time,
chunk/shard identity, predecessor/receiver, signer/public key, delegation flag,
raw stored row and args. Outcomes retain status, executor, execution hash and all
matching block observations. Counts are grouped before joins; no array is
truncated and no duplicate is resolved with an arbitrary first match. A unique
array member is used only after its match count equals one.

The action-key diagnostic checks every observation of selected receipts across
the lookup range, including records whose other counterparty fields differ.
Outcome and block groups also span the full lookup range. Source access/schema
errors fail the query. One SUMMARY, 63 DAILY_CONTROL, three WALLET_CONTROL rows
and all ACTION rows are returned even when no wallet matches are observed.
`expected_export_rows` and nested counts detect truncated exports. Nonempty
source days establish observed records, not independent ingestion completeness.

No monetary amount is cast or summed in SQL. Offline
[analysis 29](../analysis/29_wallet_native_flow_candidates.py) uses strict JSON
parsing and integer arithmetic. TRANSFER's observed representation must be a
JSON-encoded deposit-only object with a quoted u128 decimal string. Duplicate
JSON keys, unquoted numeric deposits, overflow and unsupported encodings yield
unavailable amounts.

Function calls are decoded only when the actual exported row matches the
full reference shape: quoted deposit/gas, method name and base64 args. The
[published mapping](https://github.com/near/near-public-lakehouse/blob/4de8e1a6b2a97b21f39b8cf8c050a43eb09f4291/src/lakehouse/notebooks/Silver%20Lake%20Mainnet.sql#L551)
documents that shape; it is a reference, not proof of deployed schema equivalence.
Mismatching rows remain unavailable for monetary aggregation. Raw args and their
stored representation are always preserved. This does not restore upstream
precision to unrelated FLOAT-derived fields.

Successful execution means one matching local receipt with SUCCESS_VALUE or
SUCCESS_RECEIPT_ID, a matching executor, unique block and valid timestamps. It
does not establish complete callback settlement. Later refunds and callback
flows require their own ledger observations.

## Classification and overlap

Economic classification remains UNCLASSIFIED_TRANSFER or an unclassified action
candidate until independent evidence supports a category. Verified revenue,
purchase/buyback and refund totals remain null; their categories are distinct
from unknown flows, not zero-filled. Named accounts, APP_FEE memos, system
predecessors, rate resemblance and successful calls do not establish those roles.

Movement scope is a separate diagnostic: external counterparty, between selected
wallets, or self movement. A between-wallet action is recorded once, with equal
outflow/inflow legs for the individual accounts. Group external totals exclude
both internal and self movements. This prevents adding overlapping wallet
amounts into a misleading group-volume or revenue total. Unknown ownership
outside this selected set remains unknown. Here “internal” means between the
three native accounts, not an internal Verifier credit.

The validator reports valid observed amount subtotals separately from totals
with unresolved coverage. Complete native account-balance reconciliation remains
null even when every selected action is valid.

## Historical balances and other adjustments

The saved closing hashes provide six prospective `query/view_account` checks:
three accounts at each boundary, with no additional header lookup required for
request preparation:

| Boundary | Height | Exact block ID |
| --- | ---: | --- |
| Opening: 23 August close | 212636216 | `ACuCLP9DEHaHn3ET8ohyQCJBfw6gnTLhNeMsjTgD3Lfu` |
| Closing: 18 October close | 220581912 | `76ZA6NE6s1MK1tk61djKwXs1kPbRmU4ofVtJfmKPENj1` |

For each account and boundary, prospective parameters are
`{"request_type":"view_account","account_id":"<one exact account above>","block_id":"<saved hash>"}`,
method `query`. No balance requests are executed or bundled with SQL 45.
Returned block identity, exact `amount`/`locked` strings, storage usage, raw bytes
and hashes must validate. Account absence/history errors remain unresolved until
creation/deletion evidence supports interpretation; they are not automatic zero
opening balances. These are saved observed daily-close anchors, not independent
proof that no canonical block followed before midnight.

For total account balance use liquid plus locked, keeping spendable balance
and storage collateral distinct. Transfers alone need not explain its change:
function-call deposits, prepaid execution/conversion charges, gas/deposit refunds,
contract rewards, staking rewards, slashing, account creation/deletion beneficiary
payments and lock/unlock movements may matter. Lock/unlock redistributes liquid
and locked balances without itself changing their sum; storage usage is not a
second monetary debit to subtract from account amount. Token wrapping/unwrapping
and internal representations require separate asset accounting. Recorded
`tokens_burnt` is not automatically the wallet's charge or actual native burn.
Native deposits can also be committed to in-flight receipts at the boundaries.
An execution-dated action is not proof that the sender's account was debited on
that date. Reconcile receipt funding/escrow and the actual account-change times
before treating this action layer as an opening-to-closing balance bridge.

Receipt predecessor and transaction signer do not by themselves establish the
ultimate payer or beneficiary of every adjustment, especially with delegation.
FLOAT-derived `account_changes` can provide cause diagnostics but cannot supply
exact integer before/after reconciliation. Missing adjustments remain unmeasured;
no balancing entry is called revenue, refund or burn.

## Saved result 74 validation — 7 November 2026

Result 74 is a valid JSON row array containing actual SQL-45-shaped data, not
an access-error payload. Its SHA-256 is
`48015cf9e13629c4ce751b88b160d07779cf7820ad9517f745c69f7a436a2b67`.
No saved job/retrieval metadata establishes execution provenance or restored
BigQuery access. No query, dry run or access retry accompanies this validation.

All 2,565 rows reconcile: one SUMMARY, 63 distinct DAILY_CONTROL rows, three
WALLET_CONTROL rows and 2,498 distinct receipt/action observations. Each selected
receipt has one observed action and one outcome. The action kinds are 2,479
TRANSFER and 19 FUNCTION_CALL. All source/lookup arrays reconcile; action,
outcome and block duplicate diagnostics, unmatched outcomes, unavailable
selectors and unresolved execution dates are zero. All 63 source days contain
observed records. These checks validate this export, not independently complete
historical ingestion or the source-window boundaries.

There are 244 outside-target executions, three failed in-target callbacks and
2,251 successful local in-target actions. All 2,498 deposit encodings decode to
exact u128 integer strings without float. Failures and outside-target actions
remain in the evidence but do not enter accepted monetary totals. All 22 saved
23 September transfers in result 48 match keys, counterparties, exact amounts
and execution hashes; their 8,000.969220749197522847764034 NEAR subtotal matches.

[Result 75](../results/75_three_wallet_native_flows_decoded_2026-08-24_to_2026-10-18.json)
preserves every decoded action and exact amounts. Accepted execution-date
subtotals, in NEAR:

| Account | Observed native inflow | Observed native outflow |
| --- | ---: | ---: |
| fefundsadmin.sputnik-dao.near | 303194.134220968599240887798125 | 0 |
| 1csfundsadmin.sputnik-dao.near | 265.936280481103725627715181 | 502794.000000000000000000000001 |
| buybacks.multisignature.near | 1156279.036076658082249915874618 | 0 |

Zeros describe observed selected-action outflows only. They do not establish
absence of buybacks or other assets/adjustments. Inbound action counts are
704, 27 and 1,519 respectively; nine of the 27 are zero-deposit calls rather
than positive payments. All 704 first-wallet inflows are from `intents.near`,
which does not establish revenue origin.

Two transfers from `1csfundsadmin` to `buybacks` total exactly 502,794 NEAR.
They are retained once as transfers with both wallet legs. Excluding these
internal movements, group observed external inflow is
956945.106578107785216431387924 NEAR, outflow is one yoctoNEAR, and action-layer
net is 956945.106578107785216431387923 NEAR. This is not account-balance change,
net revenue or purchases. All economic classifications remain unavailable or
unclassified, including refunds and customer principal.

## Next ledger step from saved evidence

[Analysis 30](../analysis/30_wallet_saved_evidence_ledger.py) reproduces result 75
before constructing [result 76](../results/76_three_wallet_saved_evidence_ledger_validation.json).
It prepares eight weekly native inflow/outflow tables and decodes all 19 saved
function-call requests, keeping raw base64/UTF-8, array positions and identifiers.
Requests and proposal amounts are not booked as completed payments. Source and
derivation hashes are recorded; output creation is exclusive.

The saved outcome child IDs directly link both native transfers to successful
`act_proposal` calls, requests 5 and 9. Their successful child transfers are
1 NEAR (`AWa5AZv74ixovSe88AH34BphxAtxaf4mqsXX2c7YBLMv`) and 502,793 NEAR
(`6bnALp1E4P2rLBDKcp3UA6YGzwpssQ1Xus2suXzYvtvH`). Both have failed sibling
`on_proposal_callback` receipts. These are actual parent links, not joins on
matching amounts. Other child receipts are absent from the selected-wallet
export. Thus local transfer success is supported; complete-chain settlement and
final DAO proposal state remain unresolved. Failed siblings do not undo the
separately successful native children.

One successful `mt_transfer` call to `intents.near`, receipt
`4sBxF4Uut6w9Kv6kgcwzLBVKk8MTgEEu6yaETfDNN3QL`, has a matching NEP-245 log:
`1csfundsadmin.sputnik-dao.near` to
`c0addac935f49baee1909a6fb4f08b57352a6d8c8ce7da27c59545fe45c5838c`, asset
`nep141:wrap.near`, amount `989998999899989998999899990` base units.
The attached native deposit is one yoctoNEAR, already included in native
outflow; the logged asset amount is separate and is not added to native flows.
This sampled internal-asset observation does not make SQL 45 a complete token
or internal-balance ledger. Ultimate recipient ownership and economic purpose
remain unverified. The earlier withdrawal-provenance investigation stays closed.

## Dependencies before any additional collection

The immediate saved-evidence step is complete: eight weekly action-layer
subledgers and the bounded proposal/log sidecar are reproducible offline. A
complete ledger still needs:

1. Six exact historical boundary account states using the saved hashes above.
   These alone do not reconcile balances: fees, rewards, refunds, staking,
   deletion/beneficiary flows and receipt funding/escrow timing require their
   own evidence. FLOAT-derived account changes cannot supply exact adjustments.
2. Complete FT/NEP-245/internal-balance coverage, verified historical account
   associations and asset units. The one saved internal transfer is a lead,
   not complete asset history or a purchase.
3. Historical fee-source/purpose evidence and, where required, complete receipt
   ancestry/callback outcomes. SQL 45 has no verified descendant-origin schema;
   proposal request descriptions, fee-like memos and wallet names do not fill
   that gap. BigQuery access is unavailable; no new extraction or replacement
   source is presumed available.

These dependencies precede proposing a collection plan. No new chain collection
is scheduled by this validation. Revenue, buybacks, refunds and full native
balance reconciliation remain unavailable, rather than zero or balancing entries.

Offline reproduction to stdout, preserving saved outputs:

```bash
.venv/bin/python analysis/29_wallet_native_flow_candidates.py
.venv/bin/python analysis/30_wallet_saved_evidence_ledger.py
.venv/bin/python -m unittest discover -s tests -p 'test_wallet*.py' -v
```

The first command reproduces result 75. The second verifies that reproduction
and reproduces result 76. A new `--output <unused-path>` may be supplied; existing
exports are never overwritten. Raw result 74 and prior captures remain unchanged.

## Prepared historical balance pilot

The next bounded step is specified in the
[six-state comparison plan](three_wallet_native_balance_comparison.md) and
[result 77](../results/77_three_wallet_historical_balance_request_plan.json).
Analysis 31 prepares six historical `query/view_account` requests using the
saved opening/closing hashes. All 2,254 in-window ledger observations fall within
their height and timestamp anchors, with the canonical day-edge qualification
retained. Collection remains manual. Exact liquid/locked stocks are compared
with execution-dated native flows; unexplained differences are not fees, revenue
or actual burn. Explicit account absence remains null pending lifecycle evidence.

The original and manual recovery captures now supply all six states.
[Result 78](../results/78_three_wallet_native_balance_comparison_2026-08-24_to_2026-10-18.json)
validates and reproduces their comparison. Two accounts' native stock changes
equal observed flow nets exactly. `1csfundsadmin` has a positive unexplained
difference of 0.001084931184274800000000 NEAR. This remains unallocated; a
complete native balance bridge, multi-asset coverage and revenue attribution
remain open. The [validated six-state result](three_wallet_native_balance_comparison.md#validated-six-state-result)
records exact arithmetic and source qualifications. No further collection is
scheduled by this validation.

## Consolidated ledger and asset-layer assessment

[Result 80](../results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json)
now combines results 74–79, including all accepted native entries, exact stocks,
external flows, internal legs, residuals and eight weekly flow observations.
The [consolidation note](three_wallet_ledger_consolidation.md) records the asset
and historical contract evidence, the seven request-only proposal/vote records
and one directly observed internal asset call. The closed withdrawal context is
reused without further provenance collection. No explicit verified purchase is
established. The `1csfundsadmin` difference remains unallocated, with no collection
solely to explain it. Full token/internal-balance coverage, historical role and
fee attribution, policy/source matches and exchange settlement remain dependencies.
