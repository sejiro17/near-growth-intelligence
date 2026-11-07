# NEAR Growth Intelligence

An interactive research dashboard for investigating the quality of NEAR's activity growth.

I built this project to help analysts, ecosystem teams and developers examine what headline figures leave out: who contributes to activity, whether accounts return, how concentrated transactions are, and whether additional submissions translate into successful execution.

Fixed transaction research observations cover **6 July–18 October 2026: fifteen complete UTC weeks**, containing **79,171,891 transactions**. Network calendar-period economics cover **24 August–18 October 2026: eight complete UTC weeks**, containing **44,284,794 transactions**. Selected activity cohorts start on 10 August; bounded initial-receipt lookups include six-day execution tails through 24 October.

Across fifteen-week endpoints, transactions declined **10.63%** and weekly active signing accounts declined **24.65%**. First-four-week versus final-four-week averages increased **16.39%** and **79.47%**, respectively. Growth direction depends on the comparison period; the final four weeks include the account spike.

The completed persistence phase finds exact +8 returns of **47.41%** and **46.18%** for the 10 and 17 August activity cohorts, with **37.48%** and **37.83%** active at all three selected checkpoints. Their top ten returners generated **73.98%** and **75.12%** of +8 transactions. Initial-receipt success ranged from **82.35% to 92.99%** across the three exact-return execution pilots. These overlapping groups also include failed receipts; complete-chain success remains unavailable.

The supply residual remains **+16,599.51437846169 NEAR**. Two exact blocks establish 231 validator updates absent from selected BigQuery evidence; an ingestion-collision explanation remains unconfirmed. A verified native withdrawal has **unverified revenue origin**. Full-window independent issuance, actual native burn and holder value capture remain unresolved. The dashboard and [investment thesis](notes/investment_thesis.md) present these qualifications beside the findings.

The revenue/buyback ledger, full issuance/burn reconciliation, broad relayer attribution and conditional investment model remain incomplete. The current thesis organizes evidence and unresolved inputs; it does not implement a valuation model.

## Explore the Dashboard

**[Open NEAR Growth Intelligence](https://near-growth-intelligence.streamlit.app)**

The dashboard uses saved, dated research exports. Interactions do not query external data sources.

See [product requirements](docs/product_requirements.md) for scope, interpretation boundaries and acceptance criteria.

## Three Findings Behind the Project — 24 August–18 October 2026

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
| Account returns | Exact +1/+4/+8 activity returns, repeated-checkpoint intersections, concentration and scoped initial-receipt outcomes/spending; lifecycle context for the spike. |
| Concentration | How much activity depended on leading signing accounts and original transaction receivers. |
| Economics | Recorded spending, the eight-week observational supply residual, bounded canonical evidence and the withdrawal trace's unresolved revenue origin. |
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

During **24 August–18 October 2026**, combined recorded execution spending totalled approximately **67,988.91 NEAR**:

| Component | Recorded spending |
|---|---:|
| Transaction receipt conversion | 2,110.82 NEAR |
| Receipt execution | 65,878.09 NEAR |
| **Combined** | **67,988.91 NEAR** |

Transaction conversion contributed **3.10%** of combined spending. Weekly combined spending increased **83.13%** between the first and final weeks.

This is a calendar-period comparison, not a matched transaction-chain fee calculation. Execution expenditure measures token use during the period; it does not establish persistent holdings or net market buying.

Observed total supply increased approximately **4,935,983.98 NEAR** during **24 August–18 October 2026**, using closing supply on 23 August as the opening baseline. Supply movement and execution spending are separate measurements. Validator-update balances and supply movements remain incompletely reconciled.

The detailed evidence is available in:

- [Data checks, coverage and findings](notes/data_checks.md)
- [Growth quality and investment thesis](notes/investment_thesis.md)
- [Economic mechanisms and measurement boundaries](notes/economic_mechanisms.md)
- [Account attribution and sources](notes/account_attribution.md)
- [Decision priorities](notes/decision_priorities.md)
- [Research plan](notes/research_plan.md)

## Interpretation Boundaries

- Fifteen weeks of transactions cannot establish long-term adoption. Network calendar-period economics cover eight weeks; selected initial-receipt pilots have explicit six-day tails through 24 October.
- Starting-week activity cohorts overlap and are not newly acquired users. Repeated return means activity at all exact +1/+4/+8 checkpoints, not continuous weekly activity. Incomplete follow-ups remain unavailable.
- Signing accounts are identifiers, not verified people. Relayers can submit transactions for other participants.
- Account absence is not automatically user churn, and documented service associations do not prove historical ownership.
- Transactions, actions and receipt executions measure different units. An initial receipt outcome does not establish complete downstream success.
- Selected account investigations and diagnostic samples do not represent the whole network.
- Recorded execution spending is not protocol revenue, permanent token burning or holder returns. The supply analysis is not a complete economic-flow or valuation model.

Earlier unmatched outcomes, action-record coverage gaps and unresolved economic differences are documented in the data-check notes.

## Reproduce the Derived Results

After activating the environment, one command rebuilds and reconciles the published derived evidence from saved inputs and provenance manifests:

```bash
python3 -B analysis/23_rebuild_published_results.py
```

The command runs legacy builders in an isolated temporary copy, revalidates saved canonical and withdrawal captures, validates the cohort exports, and reproduces results 61–62. It verifies 17 derived artifacts. Missing named derived outputs are created exclusively; an existing output must match byte-for-byte and is never overwritten. Raw exports/captures and historical provenance remain unchanged. Network operations are disabled; no BigQuery query, dry run or RPC collector is invoked.

Use `--check` for verification without creating missing outputs:

```bash
python3 -B analysis/23_rebuild_published_results.py --check
```

Results 57 and 59 retain their recorded SQL identities. Proven trailing-whitespace differences in current SQL 42/43 are documented in the validation reports and verified in memory, without rewriting historical reports. A mismatch beyond those verified differences stops validation.

Run the offline analysis and dashboard smoke tests in the installed environment:

```bash
python3 -B -m unittest discover -s tests -v
```

Dashboard checks include in-process Streamlit AppTest interactions and a separate console-launch regression that starts a temporary local server without a custom PYTHONPATH. Named source CSV downloads preserve saved bytes, or exact original cell strings for filtered selections; table-toolbar exports contain presentation data. Source collection remains a separate manual workflow.

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
