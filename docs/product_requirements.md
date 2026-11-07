# NEAR Growth Intelligence — Product Requirements

A hosted interactive research dashboard. The dashboard uses saved, dated research exports. Interactions do not query external data sources.

## Problem, users and decisions

Connect activity, participation, concentration, execution and spending evidence
to a conditional long-term NEAR investment case. Headline growth alone does
not establish durable adoption or economic value for holders.

| Intended user | Decision supported |
|---|---|
| Investors and research analysts | Assess growth quality, counterevidence and gaps before forming an investment argument. |
| Ecosystem teams | Identify activity needing lifecycle, account-role or execution-quality investigation before allocating support. |
| Application developers | Inspect selected accounts, actions, receipt outcomes and diagnostic errors. |

Distinguish account identifiers from people, and token expenditure from
persistent demand and holder benefits.

## Fixed historical research

| Scope | Period, UTC | Coverage |
|---|---|---|
| Transaction comparison | 6 July–18 October 2026 | Fifteen complete weeks; 79,171,891 transactions. Show endpoints and first-four-week versus final-four-week comparisons. |
| Economics and detailed investigations | 24 August–18 October 2026 | Eight complete weeks; 44,284,794 transactions. Includes returns, growth contributors, execution, profiles and economic measurements. |
| Bounded persistence phase | Starting activity weeks from 10 August; complete transaction follow-ups through 18 October | Nine complete transaction checkpoints; initial receipts for three exact-return points and two overlapping repeated subsets. Execution lookups have six-day tails ending 17/24 October. Other receipt checkpoints and incomplete returns remain unavailable. |

These windows are fixed research observations. Supply uses the 23 August
closing baseline. Explain baseline sensitivity and the final period's account spike.

The opening narrative answers what grew, how much persisted, what initially
executed successfully and what economic use/value capture is demonstrated.
Show concentration, failed activity, overlapping populations and material gaps
beside the claims. Independent issuance, actual burn and withdrawal revenue
origin remain unresolved; neither a full revenue ledger nor a valuation is established.

Provide seven dashboard views:

| View | Required purpose |
|---|---|
| Growth | Compare activity and spending, with separate transaction comparison windows. |
| Growth drivers | Inspect fixed-group changes, contributors and selected execution evidence. |
| Account returns | Show weekly cohort participation and account-lifecycle context. |
| Concentration | Show leading signers and original transaction receivers. |
| Economics | Show conversion/receipt spending and observed supply, with measurement limits. |
| Decision priorities | Connect evidence to bounded investigation decisions. |
| Account explorer | Inspect five selected profiles, destinations, actions and attribution status. |

Evidence: [research plan](../notes/research_plan.md),
[thesis](../notes/investment_thesis.md), [data checks](../notes/data_checks.md).

## Requirements

- Use included CSV and JSON research exports for dashboard interactions,
  filters, charts and downloads, without external queries or cloud credentials.
- Display fixed observation periods explicitly and reconcile figures with the
  saved evidence. Report missing or invalid inputs rather than fabricating data.
- Provide evidence links and reproduction instructions. Derived-table scripts
  use saved exports; optional SQL extraction may incur BigQuery charges and is
  not required to use the dashboard.
- Protect credentials through ignore rules; keep secrets out of code, exports
  and Git history.

## Exclusions and interpretation boundaries

Live data feeds and automatic source extraction are outside the product scope.
Signing accounts are not verified people. Initial receipt outcomes do not
establish complete-chain success. The product does not provide valuation
forecasts or guaranteed holder benefits.

Recorded execution spending measures token use, not persistent token demand,
protocol revenue or holder returns. Supply changes remain incompletely
reconciled. Staking extension results are inconclusive; balance changes are not
net staking inflows. Historical distributions and buybacks remain unverified,
not disproven.

## Acceptance criteria

- All seven views render from saved exports without application errors in the
  hosted Streamlit dashboard.
- Figures reconcile with saved evidence and use consistent units and definitions.
- Research scopes, dates, reproduction commands and interpretation boundaries
  are explicit and agree across README, notes and dashboard; the investment case
  includes counterevidence.
- Evidence links resolve and downloads contain the corresponding displayed data.
- Dashboard interactions require no external queries or cloud credentials.
- Credentials remain excluded from repository files and exports.
- Intended users can access the dashboard and supporting evidence.
