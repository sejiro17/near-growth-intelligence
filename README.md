# NEAR: Growth Quality & Investment Intelligence

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

I built this project to examine what sits behind headline activity figures: how many accounts participate, whether they return, how concentrated transactions are, and how recorded execution costs change alongside activity.

## Key Findings

### Transaction growth and account participation diverged

The eight-week period contained 44,284,794 transactions.

Compared with the first week, the final week recorded 3.69% more transactions but 7.38% fewer weekly active signing accounts.

Weekly active signing accounts peaked at 457,768 during 28 September–4 October, an increase of 198.16% from the preceding week. Of these accounts, 82.31% were active on only one day within that week.

### Accounts active again generated most starting-week transactions

Of the accounts active during 28 September–4 October, 83,037 (18.14%) were active again during 5–11 October.

These accounts generated 5,788,805 transactions during the starting week: 87.84% of that week's total.

The remaining 81.86% of accounts generated 12.16% of transactions. Account counts and transaction counts therefore describe different aspects of the spike.

These shares describe starting-week activity. They do not measure how much transaction activity those accounts maintained the following week.

### Successful self-deletions change the interpretation of account returns

Further checks found that 309,280 accounts absent the following week had successful receipt executions containing self-deletion actions during the starting week.

They represented 82.53% of the absent group and 67.56% of the full starting-week cohort.

This finding is important context for the low return share. The absence of these identifiers should not be presented as ordinary user churn.

The reasons for deletion, account ownership and any later recreation remain unverified. The results do not establish how much deletion activity explains the increase from the preceding week.

### Transactions were concentrated

The ten busiest signing accounts contributed 48.17%–67.76% of weekly transactions.

The ten busiest original transaction receivers accounted for 60.85%–70.22%.

Accounts were ranked separately each week. Receiver accounts have not been systematically mapped to verified applications.

Concentration at the account level does not establish equivalent concentration in applications, ownership or end users.

### Recorded execution costs increased faster than transactions

Across 280,743,473 receipt execution outcomes, recorded execution costs totalled approximately 65,878.09 NEAR.

The final week recorded approximately 10,544.79 NEAR, an increase of 82.73% from the first week.

These amounts describe receipt executions occurring during each week. They exclude transaction receipt-conversion costs and do not establish protocol revenue, permanent token burning or investment returns.

## Investment Interpretation

NEAR maintained substantial transaction activity during the selected eight weeks. However, the results do not demonstrate that participation was broadening or establish how much economic value accrued to NEAR holders.

My assessment is conditional: an investment argument based on adoption growth needs stronger evidence of persistent application demand and a measurable connection between that demand and NEAR's economics.

Transaction activity ended above its starting level, while weekly active signing accounts ended below theirs. Successful self-deletion activity was widespread among accounts absent after the participation spike, making a straightforward user-churn interpretation inappropriate.

Transaction concentration makes the roles of major participants important to the assessment. Higher recorded execution costs establish increased spending on receipt execution, but do not quantify token-holder returns.

These findings support further due diligence. They are insufficient on their own to justify an investment based on claims of broad, sustained adoption.

The [investment assessment](notes/investment_thesis.md) explains the evidence, decision implications and conditions that would strengthen or weaken this position. The [economic mechanisms note](notes/economic_mechanisms.md) distinguishes documented mechanisms from the economic flows measured in this project.

## Dashboard

The dashboard presents the investment assessment, its supporting evidence and the conditions that would change it.

Four views allow readers to explore the underlying results:

- **Growth:** Weekly account participation and indexed comparisons of transactions, active signing accounts and recorded receipt execution costs.
- **Account returns:** Weekly activity-cohort returns, the spike cohort's account shares versus transaction shares, and self-deletion context.
- **Concentration:** Signing-account transaction shares and a weekly explorer of the twenty busiest transaction receivers.
- **Execution costs:** Recorded receipt execution costs and failed receipts' shares of outcomes and costs.

[Hosted dashboard](https://near-growth-intelligence.streamlit.app) — access is currently restricted to authorised viewers.

The dashboard uses saved CSV exports. Opening it does not run BigQuery queries or refresh the source data.

## Run Locally

Use Python 3.12.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

## Data and Methodology

The analysis covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC. Weekly account returns use complete follow-up weeks within this period.

Source dataset:

`bigquery-public-data.crypto_near_mainnet_us`

### Activity measures

Transactions are grouped by submission date. Receipt execution outcomes and their costs are grouped by execution date.

Weekly active signing accounts count each transaction-signing identifier once within a week. Signing-account-days count an identifier once per active day and are not weekly unique accounts.

Signing accounts may represent people, automated services, relayers or other participants. They are not verified individuals.

### Account returns

Each activity cohort contains all signing accounts active in its starting week.

Follow-up percentages measure participation during a particular subsequent week. They do not require continuous participation or measure cumulative returns.

Cohorts can overlap and do not necessarily represent newly acquired users. Incomplete follow-up weeks are excluded.

### Concentration

Rankings are calculated separately for each week.

Receiver-level signing-account counts can overlap and must not be summed as network-wide unique accounts.

Receiver exports contain each week's twenty busiest original transaction destinations. Absence from a ranking does not establish zero activity.

### Spike investigation

The spike analysis follows accounts active during 28 September–4 October and groups them by whether they were active during 5–11 October.

Receiver and action comparisons describe their starting-week transactions.

Deletion checks link transactions containing DELETE_ACCOUNT actions to their initial receipt outcomes, allowing outcomes through 11 October. They check whether the signer equals the receiver and whether execution occurred on that receiver.

Successful self-deletion does not establish the reason for deletion, permanent loss of the identifier or continuity of ownership if it later reappears.

Excluding accounts with deletion activity would not, by itself, produce a verified user-retention measure.

### Execution costs

Recorded token costs are converted from yoctoNEAR to NEAR by dividing by 10^24.

Source cost fields use floating-point storage, so amounts are approximate.

Growth indices set the first week to 100. They compare changes across metrics with different units; they do not match individual transactions to their complete execution costs.

### Economic interpretation

Economic mechanisms are documented separately using official sources.

These sources provide context for interpreting network activity. They do not establish that every mechanism or parameter applied unchanged throughout the observation period.

The analysis does not calculate net issuance, permanent token burning, staking returns or total value accruing to NEAR holders.

## Validation and Coverage

The research includes checks for:

- Historical partition coverage and daily record counts.
- Transaction-hash uniqueness, account fields and timestamp coverage.
- Execution-outcome identifiers, statuses and cost-field validity.
- Execution-outcome matching to receipt records.
- Reconciliation of weekly exports and derived calculations.
- Spike cohort totals and deletion receipt outcomes.

Earlier exploratory checks found unmatched execution outcomes during 1 July–22 August. Their cause remains unresolved. The primary period was selected within the later interval where all checked outcomes matched exactly one ACTION receipt, using complete calendar weeks.

The spike action analysis found 474 transactions without matching transaction-action records in its selected lookup window. This remains a documented coverage limitation.

All 309,642 selected deletion transactions matched exactly one initial receipt outcome. Every selected deletion transaction targeted its signing account, and the execution account matched the receiver. Successful and failed outcomes were examined separately.

Detailed checks and findings are recorded in [notes/data_checks.md](notes/data_checks.md).

## Limitations

- Eight weeks cannot establish long-term adoption.
- Signing accounts are not verified people.
- Activity cohorts are not necessarily newly acquired users.
- Account deletion complicates interpretation of participation and return figures.
- Account ownership, deletion motives and later recreation remain unverified.
- Transaction receivers are not automatically applications or downstream execution destinations.
- Transaction submissions, actions and receipt executions measure different units.
- Receipt outcomes do not establish the final result of every transaction's execution chain.
- Submitted actions do not by themselves establish successful execution.
- Delegated payload contents were not expanded in the transaction-action comparison.
- Observed changes do not establish their causes.
- Recorded execution costs alone do not establish economic value accruing to NEAR holders.
- Current economic documentation does not independently verify historical parameters.

## Reproduce the Derived Tables

After activating the project environment, run:

```bash
python analysis/01_weekly_activity_baseline.py
python analysis/02_weekly_execution_costs.py
```

These scripts use saved exports and do not require another BigQuery scan.

SQL queries are stored in `sql/`. Running them requires BigQuery access and may incur query charges.

## Research Notes

- [Research plan](notes/research_plan.md)
- [Data checks and findings](notes/data_checks.md)
- [Growth quality and investment assessment](notes/investment_thesis.md)
- [NEAR economic mechanisms and measurement boundaries](notes/economic_mechanisms.md)

## Future Research

- Extend the observation period to assess persistence across more market conditions.
- Verify account and application roles where reliable evidence is available.
- Investigate deletion motives, later account recreation and ownership continuity.
- Investigate unresolved coverage gaps.
- Reconcile execution activity with a broader measurement of NEAR's economics.

## Tools

- SQL and Google BigQuery
- Python, pandas, Plotly and Streamlit
- VS Code
- Git and GitHub

## Repository Structure

- `sql/`: Extraction, validation and analytical queries.
- `analysis/`: Python scripts for derived tables.
- `results/`: Exported query results and derived tables.
- `dashboard/`: Interactive Streamlit dashboard.
- `notes/`: Research plan, data checks, investment assessment and economic mechanisms.