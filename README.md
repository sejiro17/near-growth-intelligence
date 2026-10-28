# NEAR Growth Intelligence

An interactive research dashboard for investigating the quality of NEAR's activity growth.

I built this project to help analysts, ecosystem teams and developers examine what headline figures leave out: who contributes to activity, whether accounts return, how concentrated transactions are, and whether additional submissions translate into successful execution.

The analysis covers **24 August–18 October 2026: eight complete UTC weeks**, containing **44,284,794 transactions**.

## Explore the Dashboard

**[Open NEAR Growth Intelligence](https://near-growth-intelligence.streamlit.app)**

Access is currently restricted to authorised viewers. You can also run the dashboard locally using the instructions below.

The dashboard reads saved research exports. Opening it does not run BigQuery queries, make RPC requests or refresh the source data.

## Three Findings Behind the Project

### More transactions did not mean broader account participation

Compared with the first week, the final week recorded **3.69% more transactions** but **7.38% fewer weekly active signing accounts**.

Transactions outside the first week's ten leading signing accounts increased **52.50%**, while those original leaders' transactions declined **19.83%**.

### Low account returns needed lifecycle context

Only **18.14%** of accounts active during the spike week participated the following week. However, **309,280 absent accounts** had successfully executed receipts containing self-deletion actions during the starting week.

They represented **82.53% of the absent group**. The low return share therefore cannot simply be interpreted as ordinary user churn.

### Transaction growth could include failed execution

One selected growth-contributing account, `tinykoala595.near`, signed **778,588 transactions**, of which **91.90%** had failed initial receipts.

Eighteen sampled failed receipts reported specific contract errors: seventeen slippage errors and one insufficient-deposit error. This diagnostic sample does not establish error frequencies across all failures.

These findings show why activity counts need account, lifecycle and execution context.

## What You Can Explore

| View | What it helps investigate |
|---|---|
| Growth | Whether transactions, signing-account participation and combined recorded execution spending moved together. |
| Growth drivers | Which accounts contributed to changes, including selected execution outcomes, costs and diagnostic errors. |
| Account returns | Weekly cohort participation and the lifecycle context behind the account spike. |
| Concentration | How much activity depended on leading signing accounts and original transaction receivers. |
| Economics | Transaction conversion and receipt execution spending, receipt volume, average receipt cost and observed supply changes. |
| Decision priorities | What needs investigation before findings inform adoption, support or economic claims. |
| Account explorer | Five selected signing accounts, with weekly trends, destinations, actions and attribution evidence. |

Account profiles distinguish documented roles from unverified service attribution. They describe selected signing-account activity, not complete applications or application user counts.

## Run Locally

Use Python 3.12. From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run dashboard/app.py
```

Open the local URL printed in the terminal. Keep that terminal running while using the dashboard; press **Ctrl + C** to stop it.

Saved CSV and JSON exports are included, so launching the dashboard does not require BigQuery credentials.

## Data, Methods and Validation

**Source:** `bigquery-public-data.crypto_near_mainnet_us`

The workflow combines SQL extraction and validation, saved results, Python-derived tables and a Streamlit dashboard.

Transactions and their receipt-conversion costs are grouped by submission date. Network receipt outcomes and execution costs are grouped by execution date. Account cohorts, weekly rankings and a fixed first-week account group provide different views of participation and concentration.

Validation includes transaction uniqueness, outcome matching, cost-field checks, cohort reconciliation, diagnostic response identities, account-profile totals, spending reconciliation and supply comparisons.

Combined recorded execution spending totalled approximately **67,988.91 NEAR**:

| Component | Recorded spending |
|---|---:|
| Transaction receipt conversion | 2,110.82 NEAR |
| Receipt execution | 65,878.09 NEAR |
| **Combined** | **67,988.91 NEAR** |

Transaction conversion contributed **3.10%** of combined spending. Weekly combined spending increased **83.13%** between the first and final weeks.

This is a calendar-period comparison, not a matched transaction-chain fee calculation. Execution expenditure measures token use during the period; it does not establish persistent holdings or net market buying.

Observed total supply increased approximately **4,935,983.98 NEAR** across the period. Supply movement and execution spending are separate measurements. Validator-update balances and supply movements remain incompletely reconciled.

The detailed evidence is available in:

- [Data checks, coverage and findings](notes/data_checks.md)
- [Growth quality and investment thesis](notes/investment_thesis.md)
- [Economic mechanisms and measurement boundaries](notes/economic_mechanisms.md)
- [Account attribution and sources](notes/account_attribution.md)
- [Decision priorities](notes/decision_priorities.md)
- [Research plan](notes/research_plan.md)

## Interpretation Boundaries

- Eight weeks cannot establish long-term adoption.
- Signing accounts are identifiers, not verified people. Relayers can submit transactions for other participants.
- Account absence is not automatically user churn, and documented service associations do not prove historical ownership.
- Transactions, actions and receipt executions measure different units. An initial receipt outcome does not establish complete downstream success.
- Selected account investigations and diagnostic samples do not represent the whole network.
- Recorded execution spending is not protocol revenue, permanent token burning or holder returns. The supply analysis is not a complete economic-flow or valuation model.

Earlier unmatched outcomes, action-record coverage gaps and unresolved economic differences are documented in the data-check notes.

## Reproduce the Derived Results

After activating the environment:

```bash
python analysis/01_weekly_activity_baseline.py
python analysis/02_weekly_execution_costs.py
python analysis/03_fixed_account_growth.py
python analysis/04_account_growth_contributions.py
python analysis/06_weekly_economic_comparison.py
python analysis/07_account_profiles.py
python analysis/08_execution_spending.py
```

These scripts use saved exports and do not require new BigQuery scans or RPC requests.

To validate saved diagnostic responses or resume incomplete lookups:

```bash
python analysis/05_fetch_failure_details.py
```

When all eighteen saved responses validate, no RPC requests are made and the results are left unchanged. Incomplete lookups require network access.

Running the SQL queries requires BigQuery access and may incur query charges.

## Repository Structure

| Directory | Contents |
|---|---|
| `sql/` | Extraction, validation and analytical queries. |
| `analysis/` | Derived-table, account-profile and diagnostic retrieval scripts. |
| `results/` | Query exports, derived tables, account profiles and RPC evidence. |
| `dashboard/` | Interactive Streamlit application. |
| `notes/` | Research methods, findings, attribution evidence and interpretation boundaries. |

**Built with:** SQL, Google BigQuery, Python, pandas, Plotly and Streamlit.