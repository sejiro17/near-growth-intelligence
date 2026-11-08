# NEAR Growth Intelligence

**A reproducible investment thesis connecting NEAR’s network growth, returning accounts, execution quality and token economics.**

NEAR demonstrates persistent execution use, concentrated among leading accounts.
Whether that usage produces durable token value capture remains unproven. This
project tests that gap with onchain evidence, a native-wallet ledger and an
editable economic scenario model.

**[Dashboard](https://near-growth-intelligence.streamlit.app)** ·
**[Investment thesis](THESIS.md)** ·
**[Conditional model](notes/conditional_investment_model.md)** ·
**[Demo post](https://x.com/insightX01/status/2117243839995855107)**

## Check it in 60 seconds

Open the dashboard tabs, or inspect the linked saved evidence. Each row gives a
specific observation to check.

| Check | Where | What to observe |
| --- | --- | --- |
| Growth depends on the baseline | **Growth** → Four-week averages; [comparison](results/39_extended_activity_comparison_2026-07-06_to_2026-10-18.csv) | Four-week averages rise; fifteen-week endpoints fall. |
| Persistence has limits | **Account returns** → Persistence and scoped execution; [thesis table](notes/investment_thesis.md#persistence-and-initial-execution) | Exact +8 returns near 47% and 46%, concentrated transactions, overlapping groups and scoped initial success. |
| Supply components differ | **Economics** → One exact reward week; [reward evidence](results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json) | 23 validated reward applications; implied debit remains distinct from independently measured burn. |
| Wallet inflow is not revenue | **Economics** → Three-wallet native ledger; [ledger](notes/three_wallet_ledger_consolidation.md) | Native stocks/flows, internal-transfer cancellation and an unallocated difference. |
| Follow actual execution | **Growth drivers** → Inspect a selected mechanism; [cases and coverage](notes/priority4_attribution_plan.md) | Sweat delegation, wx transfer-and-callback, and failed tinykoala controls; selected examples have explicit population denominators. |
| Challenge the investment assumptions | **Decision priorities** → Conditional investment model; [formula review](notes/conditional_model_review.md) | Edit price, fee/capture and allocations. Revenue, destruction and custody remain separate; missing measurements stay unavailable. |

## What this research adds

1. **Persistence measured alongside execution and concentration.** The 10 and
   17 August 2026 activity cohorts have exact +8 returns of **47.41% / 46.18%**
   of starting-week accounts. Their top ten returners produce **73.98% / 75.12%**
   of returning accounts’ +8 transactions. Three initial-receipt pilots for the
   5–11 and 12–18 October 2026 submission weeks show **82.35–92.99%** initial-receipt
   success among the selected returner populations, with six-day execution tails. Cohorts overlap;
   initial success is not complete-chain success. [Validated cohort evidence](results/62_integrated_research_evidence.json).

   ![Exact +8 account returns and top-ten returner transaction shares for two August 2026 cohorts.](docs/assets/persistence_and_concentration.svg)

   *Nearly half returned at +8, while leading returners dominated transactions; the denominators differ and cohorts overlap. [Evidence](results/62_integrated_research_evidence.json).*

2. **Independent economic observations, with the gaps preserved.** During
   **21–27 September 2026**, 23 epoch applications record **618,436.07 NEAR of
   protocol-validated reward minting**. Across **24 August–18 October**, three
   wallets receive **956,945.11 NEAR of external net native inflow**; two internal
   transfers cancel. The **0.0010849311842748 NEAR** stock-flow difference remains
   unallocated. Native inflows are unclassified, not revenue; reward minting
   excludes separately unavailable subsidies. [Supply evidence](results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json) · [Native ledger](results/80_three_wallet_native_ledger_and_asset_assessment_2026-08-24_to_2026-10-18.json).
3. **Mechanisms connected to a testable investment model.** Two selected Sweat
   cases each have **eight successful receipt outcomes**; the jar-deposit case
   nevertheless reports a **rejected booster application**. Other controls retain **six successful wx receipt
   outcomes**, and **18 tinykoala graphs containing failure**. They are not
   population success estimates; [coverage percentages and denominators](notes/priority4_attribution_plan.md)
   are disclosed. The implemented model converts explicit assumptions into
   capture thresholds. Its **illustrative default** reward-only threshold is
   **$24.74 billion/week** of eligible activity at a 0.1% fee, 50% capture,
   25% destruction allocation and $5/NEAR effective price. This covers the dated
   reward baseline, not total issuance including subsidies, observed revenue or
   expected returns. [Selected jars case](notes/sweat_jars_case_study.md) · [Selected wx graph](notes/wx_cruce_case_study.md) · [Model derivation](notes/conditional_model_review.md#exact-illustrative-default-calculation).

   ![Illustrative scenario: required weekly eligible activity falls as assumed fee capture rises.](docs/assets/model_capture_sensitivity.svg)

   *Higher assumed capture lowers the required eligible activity with other assumptions fixed. [Model](notes/model_sensitivity_chart.md) · [Exact scenario data](results/101_model_capture_sensitivity.json).*

## The investment case

**Supporting evidence:** repeat account activity, successful initial execution
and recorded NEAR spending demonstrate execution use. The dated reward week,
native balance bridge and selected downstream graphs make parts of the economic
account auditable. They do not establish fresh purchases or holder cash flows.

**Contrary evidence:** across **6 July–18 October 2026**, endpoint transactions
fell **10.63%** and active signing accounts **24.65%**, despite higher four-week
averages. Returner transactions are concentrated; **91.90%** of tinykoala’s
778,588 primary-window transactions had failed initial receipts. Selected
successes do not remove those population findings. [Evidence and interpretation](notes/investment_thesis.md).

**What would change the conclusion:** three complete cohorts with ≥40% exact
+8 returns and ≤50% top-ten transaction concentration would strengthen the
persistence premise; three below 25% returns or above 80% concentration would
weaken it. Economic strengthening requires eight classified, reconciled weekly
asset ledgers and attributed capture meeting the chosen model hurdle, alongside
independent supply accounting. These are analyst-selected tests, not outcomes
already met. [Execution, supply and economic revision conditions](notes/investment_thesis.md#conditions-that-would-change-the-thesis).

## Verify it locally

Use Python 3.12 from the repository root. One-time setup:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Run the unified offline verification:

```bash
.venv/bin/python -B analysis/44_rebuild_integrated_research.py --check
```

Expect exit code **0**, `source_requests: 0`, and verification of the original
published results, reviewed model, saved reward/wallet/case evidence,
[result 100](results/100_integrated_research_review.json), this figure and the
[five-deliverable status table](notes/deliverable_status.md). Network operations
and subprocess launches are disabled; existing evidence is never overwritten.
Header-prefix arithmetic uses saved validated summaries; full raw-header
revalidation requires the retained external files. [Rebuild details and checks](notes/integration_validation.md).

Launch the saved-data dashboard with
`.venv/bin/python -m streamlit run dashboard/app.py`. No BigQuery credentials or
custom `PYTHONPATH` are required. The conditional model is editable in
**Decision priorities**; its assumptions are illustrative, not measured fee capture.

## Coverage and material limitations

NEAR mainnet, UTC: transaction context covers **6 July–18 October 2026**
(**79,171,891 transactions**, fifteen complete weeks); network economics cover
**24 August–18 October** (**44,284,794 transactions**, eight weeks). Selected
cohorts begin on 10 August; initial-receipt lookup tails end on 24 October.

- Accounts are identifiers, not verified people or new users. Exact-week returns
  differ from any-return unions; repeated return means all +1/+4/+8 checkpoints,
  not continuous weekly activity. Incomplete follow-ups remain unavailable.
- The eight-week supply-versus-validator residual remains **+16,599.51 NEAR**.
  Validator changes are not issuance. Full-window issuance, full-week independent
  debit, gross burn and subsidies remain incomplete; the 144-block header prefix
  is not extrapolated. Spending is not actual burn.
- Native flows are one asset layer. Fee origin, complete token/internal balances
  and purchase execution remain unverified. The bounded withdrawal-provenance
  investigation is closed; missing attribution does not prove nonoccurrence.
- Original BigQuery cost/supply fields are FLOAT-derived. Exact RPC integers and
  saved decimal strings are preserved; rounding is for display. The model is
  implemented, while empirical calibration remains incomplete. No fair value,
  price target or expected investment return is established.

Full-window supply, the multi-asset revenue/buyback ledger and broad attribution
remain partial; validated cohort outputs do not complete wider execution
coverage. [Original criteria and current status](notes/deliverable_status.md) ·
[Detailed methodology and checks](notes/data_checks.md).

## Repository map

| Path | Contents |
| --- | --- |
| [THESIS.md](THESIS.md) | Entry point to the maintained investment argument and revision conditions. |
| [dashboard/](dashboard/) | Interactive views and reviewed conditional model. |
| [sql/](sql/) · [analysis/](analysis/) | Source-query definitions, offline validators and rebuild tooling. |
| [results/](results/) | Saved exports, derived evidence and bounded captures. |
| [notes/](notes/) · [docs/](docs/) | Methods, accounting investigations, research status and visual assets. |
