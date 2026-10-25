# NEAR: Growth Quality & Investment Intelligence

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

I built this project to examine what sits behind headline activity figures: how many accounts participate, whether they return, how concentrated transactions are, and how recorded execution costs change alongside activity.

## Project Status

Analysis in progress. The initial interactive dashboard runs locally and includes activity trends, weekly account returns, concentration and receipt execution costs.

The primary analysis covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC. The current weekly return analysis uses complete follow-up weeks within this period.

The results provide evidence about activity during the selected window. They do not establish long-term adoption or a complete investment thesis.

## Initial Findings

### Transaction growth and account participation diverged

The eight-week period contained 44,284,794 transactions.

Compared with the first week, the final week recorded 3.69% more transactions but 7.38% fewer weekly active signing accounts.

Weekly active signing accounts peaked at 457,768 during 28 September–4 October, an increase of 198.16% from the preceding week. Of these accounts, 82.31% were active on only one day within that week.

### A minority of accounts generated most activity during the spike

Of the accounts active during 28 September–4 October, 83,037 (18.14%) were active again during 5–11 October.

Those returning accounts generated 5,788,805 transactions during the starting week: 87.84% of that week's total.

This distinction matters when interpreting the spike. A large account count and a large transaction count describe different aspects of participation.

Absence in the following week does not establish permanent departure. Signing-account identifiers are not verified individuals.

Further checks found that 309,280 accounts absent the following week had successfully executed receipts containing self-deletion actions during the starting week. They represented 82.53% of the absent group. Account deletion is therefore important context for interpreting the low return share; the result should not be presented as ordinary user churn. The reasons for deletion and any later recreation remain unverified.

### Transactions were concentrated

The ten busiest signing accounts contributed between 48.17% and 67.76% of weekly transactions.

The ten busiest transaction receivers accounted for 60.85%–70.22% of weekly transactions.

Accounts were ranked separately each week. Receiver accounts have not yet been systematically mapped to verified applications.

### Recorded execution costs increased faster than transactions

Receipt execution outcomes recorded approximately 65,878.09 NEAR in execution costs across the eight weeks.

The final week recorded approximately 10,544.79 NEAR, an increase of 82.73% from the first week.

These amounts describe receipt executions occurring during each week. They exclude transaction receipt-conversion costs and do not establish protocol revenue, permanent token burning or investment returns.

## Dashboard

The dashboard contains four views:

- **Growth:** Weekly account participation and indexed comparisons of transactions, active signing accounts and recorded receipt execution costs.
- **Account returns:** Weekly activity-cohort returns and the spike cohort's account shares versus transaction shares.
- **Concentration:** Signing-account transaction shares and a weekly explorer of the twenty busiest transaction receivers.
- **Execution costs:** Recorded receipt execution costs and failed receipts' shares of outcomes and costs.

The dashboard uses saved CSV exports. Opening it does not run BigQuery queries or refresh the source data.

## Run Locally

Use Python 3.12. The dashboard has been checked locally with Python 3.12.10.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

Open the local URL printed in the terminal.

To stop the dashboard, press Ctrl + C in the terminal running Streamlit.

## Data and Methodology

Source dataset:

`bigquery-public-data.crypto_near_mainnet_us`

Transactions are grouped by submission date. Receipt execution outcomes and their costs are grouped by execution date.

Weekly active signing accounts count each transaction-signing identifier once within a week. Signing-account-days count an identifier once per active day and are not weekly unique accounts.

Each activity cohort contains all signing accounts active in its starting week. Follow-up percentages measure participation during a particular subsequent week, rather than continuous participation or cumulative returns. Incomplete follow-up weeks are excluded.

Concentration rankings are calculated separately for each week. Receiver-level signing-account counts can overlap and must not be summed as network-wide unique accounts.

Recorded token costs are converted from yoctoNEAR to NEAR by dividing by 10^24. Source cost fields use floating-point storage, so amounts are approximate.

Growth indices set the first week to 100. They compare changes across metrics with different units; they do not match individual transactions to their complete execution costs.

## Validation

The research includes checks for:

- Historical partition coverage and daily record counts.
- Transaction-hash uniqueness, account fields and timestamp coverage.
- Execution-outcome identifiers, statuses and cost-field validity.
- Execution-outcome matching to receipt records.
- Reconciliation of weekly exports and derived calculations.

Earlier exploratory checks found unmatched execution outcomes during 1 July–22 August. Their cause remains unresolved. The primary period was selected within the later interval where all checked outcomes matched exactly one ACTION receipt, using complete calendar weeks.

Detailed checks and findings are recorded in [notes/data_checks.md](notes/data_checks.md).

## Limitations

- Eight weeks cannot establish long-term adoption.
- Signing accounts may include automated services and relayers; they are not verified people.
- Activity cohorts are not necessarily newly acquired users.
- Transaction receivers are not automatically applications or downstream execution destinations.
- Transaction submissions and receipt executions measure different units.
- Receipt outcomes do not establish the final result of every transaction's execution chain.
- Observed changes do not establish their causes.
- Recorded execution costs alone do not establish economic value accruing to NEAR holders.

## Reproduce the Derived Tables

The following scripts use saved exports and do not require another BigQuery scan:

```bash
python analysis/01_weekly_activity_baseline.py
python analysis/02_weekly_execution_costs.py
```

SQL queries are stored in `sql/`. Running them requires BigQuery access and may incur query charges.

## Next Steps

- Investigate the composition of the account spike and verify relevant account roles.
- Assess how the findings support or weaken the long-term investment case.
- Document the economic mechanisms separately from measured execution costs.
- Complete the research report and prepare a hosted dashboard.

The research plan is documented in [notes/research_plan.md](notes/research_plan.md).

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
- `notes/`: Research plan, data checks and findings.