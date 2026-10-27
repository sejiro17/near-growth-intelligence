# NEAR: Growth Quality & Investment Intelligence

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

I built this project to look beyond headline activity figures: who contributes to growth, whether accounts return, how concentrated transactions are, and whether additional submissions translate into successful execution.

The analysis also compares recorded execution spending with observed total-supply movements and translates the findings into investigation priorities for analysts, ecosystem teams and developers.

The observation period covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC.

## Key Findings

### Transaction growth and account participation diverged

The period contained 44,284,794 transactions.

Compared with the first week, the final week recorded 3.69% more transactions but 7.38% fewer weekly active signing accounts.

Weekly active signing accounts peaked at 457,768 during 28 September–4 October, an increase of 198.16% from the preceding week. Of these accounts, 82.31% were active on only one day that week.

### Growth extended beyond the original leading accounts

I followed the same ten busiest signing accounts from the first week across all eight weeks.

Their combined weekly transactions declined 19.83%, from 3,195,028 to 2,561,335. Transactions from all other signing accounts increased 52.50%, from 1,539,788 to 2,348,197.

The increase outside the original leaders was 808,409 transactions, offsetting their decline of 633,693 and leaving a network-wide net increase of 174,716.

Accounts never appearing in any week's top-twenty signing-account ranking contributed 43.80% of the outside group's net increase. Other tracked accounts contributed 56.20%.

This establishes growth outside the original leaders. It does not establish more independent users or successful application demand.

### Selected growth included substantial failed execution activity

Two growth-contributing accounts, tinykoala595.near and wx-cruce.near, accounted for 18.43% and 17.04% of the outside group's net transaction increase.

Across the observation period, tinykoala595.near signed 778,588 transactions. Matching each transaction to its initial receipt showed 715,518 failures: 91.90%.

Separately, action records showed that 778,338 of its transactions contained swap calls targeting v2.ref-finance.near. The summaries do not cross-tabulate every action against every outcome, so they do not establish that all failures were swap failures.

Failed initial receipts accounted for approximately 211.1629 NEAR, or 86.78% of this account's recorded initial-receipt execution costs.

For wx-cruce.near, 1.56% of initial receipts failed and 96.54% returned SUCCESS_RECEIPT_ID. That status does not establish successful downstream execution. Failed initial receipts contributed approximately 1.0978 NEAR, or 0.95% of its recorded initial-receipt costs.

These accounts were selected for investigation. Their outcome shares are not network-wide failure rates.

### Sampled failures contained specific contract errors

I retrieved detailed execution responses for eighteen sampled failed receipts from tinykoala595.near.

All eighteen executed on v2.ref-finance.near. Seventeen reported E68: slippage error, and one reported E22: not enough tokens in deposit.

The sample identifies reported errors in those receipts. It does not estimate error frequencies across all failures, establish retries or identify automation.

### Account lifecycle events change how returns should be interpreted

Of the accounts active during 28 September–4 October, 83,037, or 18.14%, were active again during 5–11 October.

These returning identifiers generated 87.84% of starting-week transactions. The remaining 81.86% of accounts generated 12.16%.

Further checks found that 309,280 accounts absent the following week had successful receipt executions containing self-deletion actions during the starting week. They represented 82.53% of the absent group.

The low return share should therefore not be presented as ordinary user churn. Deletion motives, ownership and later recreation remain unverified.

### Transactions were concentrated

The ten busiest signing accounts contributed 48.17%–67.76% of weekly transactions. The ten busiest original transaction receivers accounted for 60.85%–70.22%.

Action checks found different activity patterns among leading accounts, including delegated actions and direct contract calls.

Account-level concentration does not establish equivalent concentration in ownership, applications or end users.

### Receipt volume and average cost changed alongside execution spending

Across 280,743,473 receipt execution outcomes, recorded execution costs totalled approximately 65,878.09 NEAR.

Between the first and final weeks:

| Measure | Change |
|---|---:|
| Transactions | +3.69% |
| Receipt execution outcomes | +66.85% |
| Recorded receipt execution cost | +82.73% |
| Average recorded cost per receipt | +9.52% |

The cost increase reflects both more receipt outcomes and a higher average recorded cost per receipt between the endpoints. This is an arithmetic comparison, not an explanation of the underlying causes.

Transactions use submission dates; receipt outcomes and costs use execution dates. These figures do not match individual transactions to their complete execution costs.

Recorded costs exclude transaction receipt-conversion costs and do not establish protocol revenue, permanent token burning or investment returns.

### Observed total supply increased

Closing total supply increased from approximately 1,304,386,568.87 NEAR on 23 August to 1,309,322,552.85 NEAR on 18 October.

The net observed increase was approximately 4,935,983.98 NEAR, or 0.3784% of opening supply.

Block supply movements reconcile to that net increase. The validator-update balance comparison does not fully reconcile with supply movements, so I have not classified those balance changes as complete gross issuance or block supply decreases as complete permanent burning.

The research establishes observed total-supply movement. Its economic decomposition remains incomplete.

## Investment Interpretation

Activity continued, and transactions outside the original leading accounts increased. However, selected-account checks show that additional submissions can include substantial failed execution activity. The participation spike also included widespread self-deletion activity.

My assessment remains conditional: an investment argument based on adoption growth needs stronger evidence of persistent application demand and a measurable connection between that demand and NEAR's economics.

The economic comparison measures recorded execution spending and observed total-supply change separately. It does not quantify the benefit of network activity to NEAR holders.

The findings do not establish that growth outside the original leaders lacked useful demand. They show why account roles, lifecycle events, execution outcomes and economic flows need examination before headline growth supports a broader investment argument.

The [investment assessment](notes/investment_thesis.md) explains the evidence and conditions that would strengthen or weaken this interpretation. The [economic mechanisms note](notes/economic_mechanisms.md) separates documented mechanisms from measured economic flows.

## Decision Priorities

The research identifies five practical priorities:

1. Examine account lifecycle events before interpreting return rates.
2. Check execution quality alongside transaction growth.
3. Verify the account roles behind concentration.
4. Investigate growth beyond the original leading accounts.
5. Reconcile economic flows before making supply or valuation claims.

Each priority connects evidence to a decision implication, a next action and a measurement boundary.

These are qualitative research priorities, not automated scores, verified application rankings or buy-and-sell signals.

The full rationale is recorded in [notes/decision_priorities.md](notes/decision_priorities.md).

## Dashboard

Six views allow readers to explore the evidence:

- **Growth:** Weekly participation and indexed comparisons of transactions, active signing accounts and recorded receipt execution costs.
- **Growth drivers:** Fixed-account comparisons, growth contributions, account activity, selected initial receipt outcomes and costs, and sampled execution errors.
- **Account returns:** Weekly activity-cohort returns, spike cohort account shares versus transaction shares, and self-deletion context.
- **Concentration:** Signing-account transaction shares and a weekly explorer of the twenty busiest original transaction receivers.
- **Economics:** Changes in receipt volume and average cost, recorded execution spending, observed supply movements and unresolved reconciliation differences.
- **Decision priorities:** Audience guidance and evidence-based investigation priorities, with supporting findings, next actions and downloadable tables.

[Hosted dashboard](https://near-growth-intelligence.streamlit.app) — access is currently restricted to authorised viewers.

The dashboard uses saved CSV and JSON exports. Opening it does not run BigQuery queries, make RPC requests or refresh the source data.

## Run Locally

Use Python 3.12.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

Open the local URL printed in the terminal. Leave that terminal running while using the dashboard.

Press Ctrl + C in that terminal to stop the dashboard.

## Data and Methodology

Source dataset:

`bigquery-public-data.crypto_near_mainnet_us`

### Activity and account returns

Transactions are grouped by submission date. Receipt execution outcomes and their costs are grouped by execution date.

Weekly active signing accounts count each transaction-signing identifier once within a week. Signing-account-days count an identifier once per active day and are not weekly unique accounts.

Each activity cohort contains all signing accounts active in its starting week. Follow-up percentages measure participation during a particular subsequent week, rather than continuous participation or cumulative returns.

Cohorts overlap and do not necessarily represent newly acquired users. Incomplete follow-up weeks are excluded.

### Concentration and growth contributions

Weekly rankings are calculated separately for each week.

The tracked-account series follows the 51 identifiers appearing in at least one week's top-twenty signing-account ranking. It includes all eight weeks for each identifier.

The fixed-account comparison selects the first week's top ten signing accounts and holds membership constant. Contributions compare transaction counts in the first and final weeks.

The untracked group combines all accounts outside the tracked set. It is not a classification of ordinary users or independent demand.

Receiver exports contain each week's twenty busiest original transaction destinations. Absence from a ranking does not establish zero activity. Receiver-level signing-account counts can overlap.

### Actions and execution outcomes

Action comparisons describe recorded transaction actions and methods. Counts can overlap across action categories, and delegated payload contents have not been expanded.

For the two selected growth accounts, transactions are linked to initial receipt outcomes using converted receipt identifiers. The outcome lookup includes records through 19 October.

An initial receipt outcome does not establish the result of the complete execution chain. SUCCESS_RECEIPT_ID is not treated as proof of downstream success.

Selected-account initial-receipt costs are grouped by transaction submission week. Their scope differs from network-wide receipt costs grouped by execution date.

### Diagnostic sample

The failure sample contains three selected receipts per active week for tinykoala595.near: eighteen receipts across six weeks.

RPC responses were checked against transaction hashes, signing accounts, receipt identifiers, executors and failure statuses. Raw responses and earlier unsuccessful retrieval attempts are preserved.

The sample is diagnostic and does not estimate population error frequencies.

### Account deletion

The spike analysis follows accounts active during 28 September–4 October and groups them by participation during 5–11 October.

Deletion checks link transactions containing DELETE_ACCOUNT actions to initial receipt outcomes, allowing outcomes through 11 October. They check whether the signer equals the receiver and whether execution occurred on that receiver.

Successful self-deletion does not establish its cause, permanent loss of the identifier or continuity of ownership if it later reappears.

Excluding these accounts would not, by itself, produce a verified user-retention measure.

### Execution costs and supply

Recorded token costs are converted from yoctoNEAR to NEAR by dividing by 10^24.

Average recorded cost per receipt divides weekly recorded receipt costs by weekly receipt execution outcomes.

Growth indices set the first week to 100. They compare changes across metrics with different units rather than matching transactions to complete execution costs.

Supply comparisons use daily closing values from the blocks table. The closing observation on 23 August provides the opening baseline for the primary period.

Weekly supply changes compare each Sunday's close with the preceding Sunday's close. Total supply is not circulating supply.

Block supply increases and decreases are compared with validator-update changes in combined nonstaked and staked balances. The comparison remains incompletely reconciled.

Balance, supply and cost fields use floating-point storage, so amounts are approximate. Exact arithmetic on exported values does not restore precision absent from the source.

Economic mechanisms are documented separately using official sources. Current documentation does not independently verify every historical parameter.

## Validation and Coverage

Checks include:

- Historical partition coverage and daily record counts.
- Transaction-hash uniqueness, account fields and timestamp coverage.
- Execution-outcome identifiers, statuses and cost-field validity.
- Execution-outcome matching to receipt records.
- Reconciliation of weekly exports, fixed-account groups and growth contributions.
- Spike cohort totals and deletion receipt outcomes.
- Selected growth-account action coverage, initial receipt matching and cost reconciliation.
- Diagnostic RPC response identities and failure statuses.
- Daily closing-supply observations, block supply movements and validator balance comparisons.
- Reconciliation of weekly economic results to the underlying exports.

Earlier exploratory checks found unmatched execution outcomes during 1 July–22 August. Their cause remains unresolved. The primary period uses complete calendar weeks within the later interval where all checked outcomes matched exactly one ACTION receipt.

The spike action analysis found 474 transactions without matching transaction-action records in its selected lookup window.

All 309,642 selected deletion transactions matched exactly one initial receipt outcome. Successful and failed outcomes were examined separately.

For the two selected growth accounts, all 1,191,869 transactions matched exactly one initial receipt outcome, with the executor matching the original receiver.

The supply investigation covers 57 closing-supply dates, including the opening baseline, and 56 days of block movements and validator balance comparisons. The validator-to-supply reconciliation remains unresolved.

Detailed checks and findings are recorded in [notes/data_checks.md](notes/data_checks.md).

## Limitations

- Eight weeks cannot establish long-term adoption.
- Signing identifiers are not verified people; ownership and account roles remain incompletely understood.
- Lifecycle events complicate participation and return measures.
- Transaction receivers are not automatically applications or downstream destinations.
- Transactions, actions and receipt executions measure different units.
- Submitted actions and initial receipt outcomes do not establish completed execution chains or economic activity.
- Selected growth accounts and diagnostic receipts do not represent the whole network.
- Growth contributions describe changes in transaction counts, not their causes.
- Recorded costs and observed supply changes do not provide a complete economic-flow or valuation model.
- Current economic documentation does not independently verify historical parameters.

## Reproduce the Derived Tables

After activating the project environment, run:

```bash
python analysis/01_weekly_activity_baseline.py
python analysis/02_weekly_execution_costs.py
python analysis/03_fixed_account_growth.py
python analysis/04_account_growth_contributions.py
python analysis/06_weekly_economic_comparison.py
```

These scripts use saved exports and do not require another BigQuery scan.

To validate saved diagnostic responses or resume incomplete RPC lookups:

```bash
python analysis/05_fetch_failure_details.py
```

If all eighteen saved responses validate, the script makes no RPC requests and leaves the results unchanged. Incomplete lookups require network access.

SQL queries are stored in `sql/`. Running them requires BigQuery access and may incur query charges.

## Research Notes

- [Research plan](notes/research_plan.md)
- [Data checks and findings](notes/data_checks.md)
- [Growth quality and investment assessment](notes/investment_thesis.md)
- [NEAR economic mechanisms and measurement boundaries](notes/economic_mechanisms.md)
- [Decision priorities](notes/decision_priorities.md)

## Future Research

- Extend the observation period and compare additional cohorts.
- Verify account roles and expand delegated actions where practical.
- Examine outcomes across a broader set of growth-contributing accounts.
- Investigate downstream execution before classifying completed application activity.
- Examine deletion motives, recreation and ownership continuity.
- Resolve documented coverage and economic-reconciliation gaps.
- Connect persistent, identifiable usage to a broader measurement of NEAR's economic flows.

## Tools

- SQL and Google BigQuery
- Python, pandas, Plotly and Streamlit
- Public NEAR archival RPC
- VS Code
- Git and GitHub

## Repository Structure

- `sql/`: Extraction, validation and analytical queries.
- `analysis/`: Derived-table and diagnostic retrieval scripts.
- `results/`: Exported query results, derived tables and RPC evidence.
- `dashboard/`: Interactive Streamlit dashboard.
- `notes/`: Research plan, data checks, investment assessment, economic mechanisms and decision priorities.