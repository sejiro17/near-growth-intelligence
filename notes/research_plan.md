# Research Plan

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what
does that imply for its long-term investment case?

## Purpose

I examine whether headline growth is accompanied by repeat account
participation, activity beyond the leading contributors and successful
execution.

The economic analysis measures recorded execution spending and observed
supply movements, then considers what they support about demand for NEAR.

The project is intended for research analysts, ecosystem teams and
developers investigating the quality of network growth.

## Observation Period

The primary analysis covers 24 August–18 October 2026: eight complete
Monday–Sunday weeks in UTC.

I selected this period after checking historical coverage, transaction
records and execution-outcome matching. Within the primary period,
checked outcomes matched exactly one ACTION receipt.

Records through 24 October were retained for potential follow-up.
The partial week after 18 October is excluded from full-week growth
comparisons. The weekly return analysis uses complete follow-up weeks
within the primary period.

Closing supply on 23 August provides the opening baseline for supply
comparisons.

The completed transaction-only extension covers 6 July–18 October 2026:
fifteen complete UTC weeks and 79,171,891 transactions (results 38 and 39).
It compares both first-to-final-week endpoints and the first four weeks
(6 July–2 August) with the final four weeks (21 September–18 October).
The dashboard presents both comparisons alongside the original analyses.

Endpoint transactions and active signing accounts declined 10.63% and
24.65%; four-week averages increased 16.39% and 79.47%, respectively.
Growth direction therefore depends on the comparison period. The final
four weeks include the account spike and are not adjusted for deletion
activity. These descriptive comparisons do not establish causality,
sustained adoption or user retention. Average weekly accounts are not
four-week unique accounts; participation frequency is weighted across
account-weeks and top-ten concentration by transactions, with weekly
rankings recalculated.

Extended weekly totals and account-days reconcile to the saved daily
checks; overlapping weeks reconcile to the original signing results,
except for the newly available prior-week change on 24 August. Script
`analysis/09_extended_activity_comparison.py` validates result 38 and
produces result 39. Economic measurements, detailed execution analysis
and receipt-matching conclusions remain scoped to the original eight
weeks; the extension does not resolve earlier outcome-matching gaps.

Earlier unresolved outcome matching during 1 July–22 August remains
documented. The coverage checks do not establish complete ingestion.

## Analytical Approach

| Area | Approach |
|---|---|
| Activity | Compare weekly transactions and active signing accounts across complete weeks. |
| Account returns | Follow activity cohorts into later complete weeks and examine lifecycle context. |
| Concentration | Measure leading signers' and original receivers' transaction shares. |
| Growth drivers | Hold the first week's leading group fixed and decompose endpoint changes by account. |
| Execution quality | Examine selected contributors' actions, initial receipt outcomes, costs and diagnostic errors. |
| Account profiles | Combine weekly activity, destinations and actions with documented attribution evidence. |
| Economics | Compare receipt volume, average costs, transaction conversion costs and observed supply movements. |
| Decision implications | Connect findings to investigation priorities and a conditional investment argument. |

Cohort follow-ups use comparable weekly intervals. Unavailable follow-up
periods are excluded rather than counted as zero returns.

The fixed-account comparison holds membership constant. Weekly rankings,
by contrast, are recalculated each week. These answer different questions
about concentration and growth.

## Data and Workflow

Source dataset:

`bigquery-public-data.crypto_near_mainnet_us`

The workflow uses:

1. SQL to extract, validate and summarise public blockchain records.
2. Saved CSV and JSON exports to preserve the analytical inputs.
3. Python to validate derived comparisons and prepare account profiles.
4. Archival RPC responses to investigate selected failed receipts.
5. Streamlit and Plotly to present the evidence interactively.

The dashboard reads saved exports. Opening it does not query BigQuery,
make RPC requests or refresh the data.

## Deliverables

- An interactive dashboard with seven views: Growth, Growth drivers,
  Account returns, Concentration, Economics, Decision priorities and
  Account explorer.
- Reproducible SQL, Python scripts and saved results.
- An investment thesis connecting activity evidence to token-economic
  mechanisms, risks and conditions for further evaluation.
- Supporting notes covering validation, economic mechanisms, account
  attribution and decision priorities.

## Interpretation Rules

Accounts are treated as identifiers rather than verified people.
Service associations require supporting evidence; unknown roles remain
unverified.

Transactions, actions and receipts are analysed as separate units.
Initial receipt outcomes are not treated as complete execution-chain
results, and overlapping action-category counts are not summed.

First observed means first seen within the available window, not
first-ever use. Account absence is not automatically user churn.

Recorded execution spending is distinguished from product revenue,
permanent burning, persistent token holdings and holder returns.
Conversion and receipt costs are combined by calendar period rather
than attributed to matched transaction chains.

Observed patterns are not attributed to bots, campaigns, retries or
other causes without supporting evidence. Economic mechanisms described
in current documentation are not assumed to establish historical
parameters.

## Validation and Review

Checks cover record uniqueness, dates, account fields, outcome matching,
cost validity, cohort totals, account-profile coverage and reconciliation
of derived results.

Unresolved coverage and supply-reconciliation differences remain in the
investigation record.

Dashboard checks assess whether controls and exports work. Reader feedback
is used to assess clarity and navigation, separately from technical
validation or professional investment review.

## Supporting Notes

- [Data checks and investigation history](data_checks.md)
- [Investment thesis](investment_thesis.md)
- [Economic mechanisms](economic_mechanisms.md)
- [Account attribution](account_attribution.md)
- [Decision priorities](decision_priorities.md)