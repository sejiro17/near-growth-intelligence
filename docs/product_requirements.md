# NEAR Growth Intelligence — Product Requirements

Status: hosted interactive dashboard backed by saved, dated research exports.
No automatic extraction or daily refresh. Zero additional project spending is
a firm requirement; using the dashboard requires no paid services or cloud credentials.

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

Supply uses the 23 August closing baseline. Explain baseline sensitivity and
the final period's account spike. Never refresh historical exports or conclusions.

Preserve all seven dashboard views:

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

## Saved-data operation

- Read only the included CSV and JSON research exports. Dashboard visits must
  not submit BigQuery queries, make RPC requests or extract new source data.
- Display the fixed observation periods explicitly; do not describe the data
  as current, daily refreshed or real-time.
- Keep local interaction, filters and charts independent of cloud authentication,
  billing accounts and paid services. Preserve credential-ignore rules.
- Preserve existing data validation and report missing or invalid research
  inputs rather than fabricating or silently replacing observations.
- Keep historical SQL and reproduction scripts available for research review.
  Reproducing derived tables from saved exports requires no new source queries;
  optional source extraction may incur charges and is not required to use the app.

## Explicit exclusions

No daily-refresh feature, executable refresh workflow, automatic extraction,
real-time feed, visitor queries, paid-service setup, unbounded backfills, fabricated
data, historical rewrites, new delivery infrastructure or access changes.
No verified user counts, complete-chain success, valuation forecasts, guaranteed
holder benefits or inferred net staking inflows. Staking extension results are
inconclusive; historical distributions and buybacks remain unverified, not disproven.

## Acceptance checklist

Local checks, distinct from hosted deployment verification:

- [x] All seven historical views render from the saved exports without app errors.
- [x] Historical research, exports, validation scripts and investment findings remain unchanged.
- [x] Refresh workflow, runner, SQL, dependencies, tests and dashboard integration are removed.
- [x] No executable refresh workflow remains; credential-ignore rules are preserved.
- [x] README and product requirements describe saved-data operation and fixed scopes.
- [ ] Verify the hosted Streamlit deployment serves the reviewed revision and all seven views.
- [ ] Confirm intended reviewers can access the hosted dashboard with existing restrictions.

Local checks do not establish deployed availability or reviewer access. Live cloud
SQL, WIF authentication and refresh delivery are excluded, not readiness requirements.

## Submission readiness

- Align figures, scopes, evidence links, reproduction commands and limitations
  across README, notes and dashboard. Present counterevidence and a conditional thesis.
- Verify intended reviewers can access restricted materials through authorised
  channels; preserve repository/dashboard privacy.
- Review the diff and local rendering checks before committing. Verify hosted
  rendering after an authorised delivery, without enabling paid services or refresh.
