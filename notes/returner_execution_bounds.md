# Initial execution beyond each returner population's top ten

[Result 105](../results/105_returner_initial_success_outside_top10_bounds.json)
calculates transaction-level bounds from saved concentration and initial-receipt
outcomes. It adds no extraction and does not change source exports or cohort
membership. Both cohorts are starting-week active signing accounts, not verified
new accounts or people. Their overlapping populations remain separate.

## Population and unit alignment

SQL 41 forms distinct starting-week signer memberships, intersects them with
activity in each exact follow-up week, and ranks that population's returners by
transaction count descending, then signer ID. `top_10_transactions` sums the
first ten accounts' transactions. It is not a network-wide top-ten count.

SQL 43's `AUG10_EXACT_WEEK8` selects the 10 August membership active during
5–11 October. SQL 42's `EXACT_WEEK_8_RETURNERS` selects the 17 August membership
active during 12–18 October, without restricting it to the repeated-checkpoint
subset. Both outcome populations include all selected submission-week
transactions, not just successes. Results 57, 59 and 61 reproduce the relevant
expected cohort, account and transaction counts. The new analysis pins the
reviewed SQL hashes, including the established trailing-whitespace distinction
handled by the existing validator; it never substitutes the duplicate-named
SQL 43 file.

The denominator unit is a submitted transaction. Bounds require every selected
transaction to have exactly one assessed initial receipt and observed outcome.
Saved export/validator checks cover transaction hash uniqueness, receipt-owner
uniqueness in the selected source weeks, outcome uniqueness, recognized statuses,
execution lookup and all exclusion diagnostics. `SUCCESS_VALUE` and
`SUCCESS_RECEIPT_ID` both count as initial success; neither establishes successful
descendants. Missing, ambiguous or inconsistent evidence suppresses the bounds
instead of assuming zero or dropping problematic rows.

The exports contain aggregates and diagnostic examples, not complete membership
or receipt lists. Alignment is established at the reviewed-query-definition and
validated exported-control level. Independent row-level set equality and complete
historical ingestion cannot be proved from these inputs; the conclusion retains
that observed-coverage qualification. Existing six-day execution tails remain.

## Arithmetic and results

Let N be population transactions, T be transactions of that population's own top
ten, S be successful assessed initial receipts and B = N−T. Then:

- Minimum successful initial receipts outside the top ten: `max(0, S−T)`.
- Maximum successful initial receipts outside the top ten: `min(S, B)`.
- Fraction denominator: B, the transactions outside the top ten—not accounts.

These bounds are sharp given the aggregate information: they allow any allocation
of the observed successes between the top ten and other signers consistent with
their transaction counts. No independence, average-success or equal-rate
assumption is made.

| Cohort → exact +8 submission week | N | T | S | B | Successful outside: lower–upper | Outside transaction fraction bounds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 August → 5–11 October | 3,888,965 | 2,877,112 | 3,563,266 | 1,011,853 | 686,154–1,011,853 | 67.81%–100.00% |
| 17 August → 12–18 October | 3,528,043 | 2,650,181 | 3,280,589 | 877,862 | 630,408–877,862 | 71.81%–100.00% |

Counts use integer arithmetic. Result 105 retains exact fraction numerators and
denominators; displayed lower percentages round down and upper percentages round
up to two decimals using integer division. With no outside transactions, count
bounds are zero and percentages remain unavailable. Invalid/unavailable counts
are never converted to zero. The counts do not use FLOAT-derived spending or a
monetary tolerance, and no spending is allocated outside the top ten.

## Investment interpretation and reproduction

Within observed coverage, successful initial execution cannot all belong to the
ten leading signers. This strengthens evidence of execution use beyond the most
active group, while leaving concentration unchanged. It proves minimum successful
initial-receipt counts, not measured account-level success rates, broad human
adoption, independent users, revenue, token purchases or complete-chain settlement.
The cohorts cannot be added or treated as a causal comparison. Wider checkpoint
execution coverage and all other original completion criteria remain open.

```bash
.venv/bin/python -B analysis/48_returner_execution_bounds.py --check --output results/105_returner_initial_success_outside_top10_bounds.json
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
.venv/bin/python -B -m unittest discover -s tests -p 'test_returner_execution_bounds.py' -v
```

The first command reproduces the exact bounds artifact. The unified rebuild
also reproduces it and verifies the current dashboard integration. Offline
commands disable source access, preserve existing files and record input/code
hashes. A new output may be created explicitly with `--output <unused-path>`;
existing exports are never overwritten by the analysis command.
