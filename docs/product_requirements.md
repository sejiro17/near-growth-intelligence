# NEAR Growth Intelligence — Product Requirements

Status: historical dashboard implemented; Latest activity implemented locally
but inactive. No daily schedule or initial latest-activity export exists.

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

## Separate daily-refreshed activity

- Show daily transactions and exact distinct transaction-signing identifiers
  separately from research. Describe refresh as daily when operated daily,
  never real-time or currently active.
- Until a validated export exists, show “Daily refresh not yet activated.”
  Never fabricate data or trigger BigQuery/RPC calls from dashboard visits.
- Deliver separate data, candidate-state, status and backup files through the
  private repository to Streamlit. Retain 30 calendar days of published history.
- Keep the workflow manual-only, gated by enablement, confirmation and `main`.
  Scheduling requires separate approval. Use repository/owner/branch/workflow-
  restricted WIF; keep credentials out of code, exports, logs and Git history.
- Query four completed UTC date partitions in `us-east1`. New jobs require a
  dry run and configurable maximum-bytes-billed cap: default 5 GiB, never
  automatically increased. Reuse existing daily jobs before requiring a dry run.

## Eligibility, freshness and failures

- Validate identifiers, timestamps, hash uniqueness, all 24 UTC hours and
  five-minute day-boundary coverage. Missing or partial observations are not zero.
- Require matching summaries from independent observations at least 20 hours
  apart and day age of 48 hours, using query start times. Cached retrieval is
  not new evidence. Eligibility checks do not prove complete ingestion.
- Preserve unresolved revisions beyond the lookback until independently
  resolved or their published rows leave retained history.
- Show observation date, source verification, publication, ages and gaps.
  Recalculate locally every 60 seconds in active sessions. Mark overdue source
  verification after 30 hours, delayed dates, failures, revisions and fallback stale.
- Validate before per-file atomic replacement. Incomplete status and data/state
  checksums must prevent mixed bundles appearing current. Preserve valid data
  and fallback; multiple files are not one atomic transaction or a disk-recovery guarantee.
- Publish one Git revision without force pushes or weaker branch protection.
  Rejected delivery leaves remote data unchanged; the app detects overdue
  delivery but cannot immediately identify an unpublished failure.

Operational details, costs and setup: [refresh runbook](latest_activity_setup.md).

## Explicit exclusions

No real-time feed, visitor extraction, automatic activation, unbounded backfills,
fabricated data, historical rewrites, new delivery infrastructure or access changes.
No verified user counts, complete-chain success, valuation forecasts, guaranteed
holder benefits or inferred net staking inflows. Staking extension results are
inconclusive; historical distributions and buybacks remain unverified, not disproven.

## Acceptance checklist

Tested locally with fixtures and mocked cloud clients; not end-to-end cloud validation:

- [x] Seven historical tabs survive missing, corrupt or stale latest data.
- [x] No initial latest export; disabled runner does not submit queries.
- [x] Validation, stability/age, persistent revisions and cached timestamps pass regressions.
- [x] Billing caps, job reuse and creation conflicts pass mocked tests.
- [x] Mixed/interrupted writes, rollback, fallback, gaps and freshness are checked.
- [x] Periodic fragment registration and manual guards are checked; action pins verified upstream.
- [ ] Verify live WIF/IAM authentication and public-dataset access.
- [ ] Validate live SQL/schema compatibility and review a capped dry-run byte estimate.
- [ ] Verify GitHub dispatch, repository publication permissions and protected-branch failure behavior.
- [ ] Verify deployed Streamlit synchronization, rendering and periodic freshness behavior with unchanged access restrictions.

The 34 passing local tests do not establish cloud or deployment readiness.

## Submission readiness

- Align figures, scopes, evidence links, reproduction commands and limitations
  across README, notes and dashboard. Present counterevidence and a conditional thesis.
- Verify intended reviewers can access restricted materials through authorised
  channels; preserve repository/dashboard privacy.
- Review pending changes and checks. Historical submission does not require
  refresh activation: disclose it as inactive. Claim operating refresh only
  after separately approved setup and end-to-end validation; approve scheduling separately.
