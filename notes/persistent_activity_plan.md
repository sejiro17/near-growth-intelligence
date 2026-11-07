# Persistent Economic Activity Measurement

## Completion — 7 November 2026

The bounded phase is closed. Result 56 measures nine complete transaction
checkpoints for four starting-week activity cohorts. Results 58–59 and 60–61
measure initial receipts for three exact-return checkpoints and the two available
repeated-checkpoint subsets. Five other execution-eligible checkpoints remain
unmeasured, one earlier checkpoint lies outside the agreed execution window,
and three incomplete transaction checkpoints remain unavailable.

Result 61 validates all 75 shared-week export records, source/group controls,
bucket totals, monetary identities and diagnostic examples. Its August +8 and
September +1 populations overlap by 58,957 accounts and 3,871,009 transactions.
Do not add group totals or interpret descriptive outcome differences causally.
Result 62 integrates the verified observations and their limitations into the
dashboard. The supply decomposition and revenue origin remain unresolved.

Rebuild the published derived evidence with
`python3 -B analysis/23_rebuild_published_results.py`. This uses saved inputs
only and preserves existing outputs. The extraction commands below document
the original design; no further collection is included in this phase.

## Population and Coverage

An account is the outer `transactions.signer_account_id`, not a verified person,
application owner or economic fee payer. Sponsored and delegated transactions
remain attributed to that observed outer signer; inner actors are not substituted.

Each cohort contains distinct accounts active in its Monday–Sunday starting week
in UTC. Creation history is not established, so these are activity cohorts rather
than newly acquired accounts. Membership is fixed at the starting week. Cohorts
overlap and their transactions must not be pooled as disjoint populations.

Saved daily checks cover 1 July–24 October 2026. The last complete saved UTC week
is 12–18 October; 19–25 October lacks 25 October. Result 38 supplies validated
weekly transaction controls from 6 July–18 October. The initial extraction uses
only 10 August–18 October: ten complete weeks, including every intervening week
needed for the selected complete horizons.

| Starting activity week | Exact +1 week | Exact +4 week | Exact +8 week |
|---|---|---|---|
| 10–16 August | 17–23 August | 7–13 September | 5–11 October |
| 17–23 August | 24–30 August | 14–20 September | 12–18 October |
| 24–30 August | 31 August–6 September | 21–27 September | 19–25 October: unavailable |
| 28 September–4 October | 5–11 October | 26 October–1 November: unavailable | 23–29 November: unavailable |

Source days/hours and record diagnostics describe observed coverage, not proof
of complete ingestion. Initial-receipt economics before 24 August are not
prevalidated by the original economic window. In particular, +1 for the
10 August cohort uses transaction records and any valid conversion costs only;
initial-receipt economics remain unavailable in this pilot. Later outcomes require
fresh matching diagnostics even where earlier saved checks were satisfactory.

## Return Definitions

For starting membership C and exact follow-up week W+k, a returning account is
in C and signs at least one transaction in W+k. The exact-week return share is
the number of these accounts divided by |C|. No activity in intervening weeks is
required. Incomplete follow-up produces unavailable metrics, not zero returns.

The primary repeatedly-returning population is the intersection of C with
activity in **all three exact weeks +1, +4 and +8**. It is available only when
all three weeks are completely observed. This is checkpoint persistence, not
continuous weekly activity. A separate +1-and-+4 intersection has its own name
and denominator; it is not substituted for the eight-week measure.

Any-return-within-weeks-1–4 and any-return-within-weeks-1–8 are separate unions
over every intervening week. Each requires the full interval. Exact-week shares
cannot be added to infer those unions or the repeated-return intersection.

## Stage 1: Transactions, Returns and Concentration

SQL 41 reads only the verified `transactions` table, with a direct partition
filter for 10 August–18 October. It aggregates to one signer/week before cohort
joins. Fixed membership and exact follow-up joins preserve that grain; neither
actions nor receipts are joined. Global hash uniqueness, identity/timestamp,
weekly-day and cost diagnostics accompany the measurements.

The compact export contains one source summary, ten weekly controls and twelve
cohort/checkpoint records. It does not export complete account membership or
claim that current saved aggregates establish returners' individual activity.

For each complete checkpoint, measure:

- Active returning accounts and their exact-week share of starting accounts.
- All transactions signed by those accounts during the exact follow-up week,
  divided by all observed transactions in that week. Transactions from cohort
  accounts that did not return in that week do not enter the numerator.
- Top-1, top-10 and top-20 returner transaction counts, ranked independently for
  each cohort/checkpoint, and the sum of squared per-account counts. These give
  concentration shares and transaction HHI without exporting every account.
- Recorded transaction-conversion spending in NEAR by submission week, including
  failed activity. Invalid/missing costs remain diagnosed and prevent a complete
  spending total; they are not zero-filled.
- Fixed-horizon +1-and-+4 and +1-and-+4-and-+8 intersections, and separate any-return
  unions where their full intervals exist.

Counts reconcile exactly to source controls and overlapping saved result 11
return counts. Conversion spending starts from source FLOAT values. Casting
finite values to BIGNUMERIC before summing does not recover lost precision.
Decimal arithmetic is used offline. A 0.00001 NEAR comparison threshold can flag
differences against saved conversion aggregates; it is a saved-arithmetic screen,
not a source-accuracy bound or economic reconciliation tolerance. Count checks
have no numerical tolerance.

## Stage 2: Initial Receipts and Recorded Spending

After validating stage 1, reuse its exact cohort and signer/week definitions.
The next extraction is restricted to those follow-up submission weeks and their
initial receipt IDs; it must reproduce stage-1 transaction denominators first.
No complete account-week export needs to be uploaded or persisted as a table.
For cohorts with complete +8 follow-up, report a separate repeatedly-returning
subset using the fixed all-three-checkpoint definition. It overlaps the
exact-week returner population and must not be added to it as a disjoint group.

Link `transactions.converted_into_receipt_id` to `execution_outcomes.receipt_id`.
Count transactions per initial receipt ID before the join and count outcomes per
receipt ID across the lookup partitions before joining either group. Require one
transaction and one valid outcome for attribution. Missing IDs, shared receipt
IDs, duplicate matches, executor/receiver disagreement, invalid timestamps and
invalid costs remain separate diagnostics. Aggregate outcome observations before
joining; never select an arbitrary record with MAX, LIMIT or array position.

Preserve the outcome record's block hash/timestamp separately from
`executed_in_block_hash`. Verify actual execution time against uniquely grouped
`blocks` observations before allocating execution-date spending; apply direct
partition filters to that lookup as well. Missing, duplicate or boundary-crossing
block matches leave execution-date attribution unavailable. Require a valid
nonnegative execution lag relative to submission; do not substitute a source
record timestamp for an unresolved execution timestamp.

Use source outcomes from 24 August through 24 October at most, with direct
partition filters. For comparability, each submission-week cohort has a bounded
lookup ending six days after its Sunday; the final submission week therefore
looks through 24 October. A missing outcome is unresolved/right-censored within
that window, not a failed receipt. Earlier +1 economics for the 10 August cohort
remain unavailable in the initial pilot rather than silently extending the
original execution scope across known earlier matching gaps.
This common week-relative cutoff is not equal elapsed follow-up for every
transaction; execution lags and unresolved-match counts must accompany it.

Retain SUCCESS_VALUE, SUCCESS_RECEIPT_ID, FAILURE and unavailable/invalid status
categories. Successful initial receipts do not prove complete-chain success.
SUCCESS_RECEIPT_ID in particular schedules or returns downstream execution.
Accounts with at least one successful initial receipt can form a separately
labelled initial-receipt-success subset after matching coverage is established.

Two date bases must remain explicit:

1. Submission-cohort allocation: conversion costs plus uniquely matched initial
   receipt costs associated with transactions submitted in the follow-up week.
   This is partial transaction-associated spending, excluding later descendants.
2. Execution-date allocation: the same matched initial receipts grouped by their
   actual execution date/week. Preserve the submission-week key alongside it;
   this is not interchangeable with network calendar-week execution spending.

The 19–24 October execution tail is only part of a UTC week. Label its six-day
coverage explicitly and do not compare it as a complete calendar-week total.

Report matching and valid-cost numerators/denominators, failed-receipt spending
and separate conversion/initial-receipt components. Missing costs suppress a
complete total; any supported subtotal must carry its assessed coverage. Do not
attribute costs by `executor_account_id IN cohort`: that field identifies the
executing recipient, not the transaction-signing cohort. Costs retain source
FLOAT limitations and do not establish revenue, NEAR purchases or holder value.

## Lifecycle Context

Result 17 already establishes successful self-deletion actions for 309,280
accounts absent from the week following the 28 September cohort, and nine
accounts active in that following week. This is context for that specific
cohort, not an adjustment that can be applied to every return rate. The saved
export contains counts rather than those membership IDs.
The grouped export does not establish the deletion's execution time relative to
follow-up submissions, recreation or continuous control. Failed and successful
deletion groups may share account IDs and must not be added as disjoint sets.

If stage-1 results warrant an extension, restrict `transaction_actions` to the
relevant cohort/follow-up dates and DELETE_ACCOUNT actions. Group actions by
transaction hash before joining transactions; count each transaction once and
retain action-row counts separately. Require a unique successful initial outcome
and executor matching the receiver before calling an observed self-delete
successful. Signer=receiver defines the observed self-deletion case. Other
targets and delegated inner actions need separate treatment. Do not infer an
inner action or recreation from an outer action alone.
The saved grouping establishes transactions containing deletion actions and a
successful initial receipt; a delegated target requires additional action-level
identity evidence before interpreting the deletion as a signer's own lifecycle.

Report lifecycle flags for returning and absent accounts without removing them
from cohort denominators. A returning identifier may have been deleted and
recreated; account identity does not establish continuous control or a retained
human user. Repeated addresses and roles remain distinct from verified users.

## Manual Sequence and Stopping Conditions

Validate the offline plan and saved baselines, then manually dry-run SQL 41.
Review the reported scan before any manual execution. Save the complete result
as result 56 before offline validation. No query, dry run or RPC request is part
of the offline tools. The supplied CLI export limit accommodates the expected
23 result rows; row-kind counts and keys are checked after saving.

Stop on missing days, duplicate hashes, identity failures, unexplained control
differences or a truncated export. Do not expand source windows to repair a
metric silently. Stage-2 SQL is prepared only after stage-1 evidence is saved and
validated; its matching controls must pass before an economic comparison is
reported. Deletion scope extends only where the proposed lifecycle question
requires it. The closed wallet-provenance investigation is not reopened.

Offline reproduction and the first manual dry run:

```bash
python3 -B analysis/19_persistent_activity_plan.py plan
python3 -B -m unittest discover -s tests -p 'test_persistent_activity_plan.py' -v
bq --project_id=web3-512316 --location=us-east1 query \
  --use_legacy_sql=false --dry_run \
  < sql/41_persistent_activity_transaction_pilot.sql
```

After reviewing the dry-run estimate, manual JSON export without overwriting:

```bash
(
  set -o noclobber
  bq --project_id=web3-512316 --location=us-east1 --format=prettyjson query \
    --use_legacy_sql=false --max_rows=1000 \
    < sql/41_persistent_activity_transaction_pilot.sql \
    > results/56_persistent_activity_transaction_pilot_2026-08-10_to_2026-10-18.json
)
```

Then validate the saved export offline:

```bash
python3 -B analysis/19_persistent_activity_plan.py validate \
  --source results/56_persistent_activity_transaction_pilot_2026-08-10_to_2026-10-18.json
```

Result 55 preserves the reproducible coverage plan and saved cohort baselines;
it does not contain newly extracted returning-account metrics. No command above
changes billing, credentials, configuration or a maximum-bytes cap. Source
compilation and scan size remain unverified until the manual dry run.
