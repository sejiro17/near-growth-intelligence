# Latest activity refresh

The feature is implemented but inactive. There is no scheduled workflow.
The only trigger is manual dispatch, and the refresh job is skipped unless
`LATEST_REFRESH_ENABLED` is explicitly set to `true`, the confirmation is
`REFRESH`, and the dispatch uses `main`. No initial observations are supplied.
Until a validated export exists, the app displays “Daily refresh not yet activated.”

The historical research exports, observation windows and conclusions remain
separate. The latest section reads files and never imports the BigQuery runner.
This feature is daily refreshed when operated daily; it is not real-time.

## Data flow and eligibility

`sql/38_latest_daily_activity.sql` reads only the four completed UTC dates
before the extraction date, using `block_date BETWEEN @start_date AND @end_date`.
It counts transactions and exact distinct transaction-signing identifiers,
including all recorded statuses. It also checks transaction hash uniqueness,
missing identifiers, timestamp validity and daily coverage. Missing partitions
are represented as missing, never zero-filled.

A day is eligible only after its UTC close is at least 48 hours old and its
validated summary matches two distinct extraction observations at least
20 hours apart. Both intervals use the BigQuery job's execution start time,
not its completion, retrieval or publication time. This is a source-read-time
proxy, not an upstream ingestion watermark. Full-day checks require all 24 UTC hours and observations
within five minutes of both day boundaries. A change resets stability;
partial or missing coverage resets that day's candidate history. These are
conservative operational checks, not proof of complete ingestion. Stable
summaries can conceal omissions, and late backfills remain possible. The
normal newest observation is approximately three UTC dates behind today.

The first successful extraction only establishes candidates. A later manual
run with overlapping dates and sufficient separation can publish data.
Reusing the same completed daily job does not advance stability. Only the
four-date lookback is rechecked; revisions to older published dates can go
undetected. No claim of finality is made for any observation.

Once a revision or loss of coverage is detected for a published date, its
marker and detection time persist in both candidate state and the data export.
They survive the date leaving the lookback. Resolution requires matching
qualifying observations beginning no earlier than detection; pre-detection
cached evidence cannot clear a marker. Otherwise the marker remains until
the affected row leaves the 30-day retained history. The bounded runner does
not query older dates automatically to resolve these markers. Revalidation
outside its lookback would require a separately approved investigation.

The runner keeps a 30-calendar-day published window and four dates of
candidate state in `latest_activity_data/`:

| File | Purpose |
|---|---|
| `activity.json` | Last validated daily history, source observation time, publication time and unresolved revisions. |
| `activity.previous.json` | Previous valid export for recovery from corrupt primary data. |
| `candidates.json` | Fingerprints, source observation times and persistent unresolved revisions. |
| `status.json` | Last attempt, publishing/success/pending/failure status, data/state checksums and query costs. |

No files in this directory are prepopulated. The runner validates its output
before writing. Each JSON replacement uses a same-directory temporary file,
flush, fsync and atomic rename. This does not make the collection of files
one filesystem transaction or guarantee recovery from disk failure.

Publication first writes a `publishing` status, then the previous-data backup,
candidate state and changed data. The final status is written last and binds
both data and candidate state with checksums. The app requires matching data,
state and final status before showing a current badge; an incomplete status,
missing state or mixed revisions are stale. Ordinary exceptions after replacing
data trigger an attempt to restore the previous primary export. Abrupt process
termination can leave a mixed local bundle, which stays stale. The previous
export remains available as a backup. No atomic multi-file rollback is claimed.

The workflow publishes related files in one Git commit, providing a single
remote revision. A deployment's checkout can still replace files separately;
the same checksum and incomplete-publication rules apply to readers during
that transition. Run only one publisher at a time; the workflow has a
non-cancelling concurrency group, and local operators must also serialize runs.

Failed extraction or validation writes a generic failure status without
exception contents and retains the previous data. Revisions to published
candidate dates retain the previous values until stable and are marked stale.
Corrupt primary data falls back to the previous validated export. Invalid
latest data cannot stop the historical tabs from rendering.

The app distinguishes the daily observation date, source observation time
(query execution start), each day's qualifying source-verification time,
export publication time and last attempt time recorded in status. Reusing a
job preserves its original source time and does not change the data export's
publication time unless data or revision metadata actually changes. Source
verification age and publication age are displayed separately.

It marks data stale after 30 hours without a qualifying source verification,
when the latest eligible date is delayed, on a reported failure or pending
revision, or when using fallback/mismatched status or candidate state. A
Streamlit fragment rereads local files and recalculates freshness every
60 seconds while its session is active, without importing the query runner
or submitting BigQuery calls. Historical tabs do not rerun on that timer.
If a workflow never starts or cannot push its failure status,
the app cannot immediately know the failure; the deadline and observation
lag still cause an overdue warning. Missing values are never displayed as zero.

Git push rejection, including branch protection or a non-fast-forward race,
leaves the remote data unchanged by that attempt. There is no force push,
automatic branch-protection change or alternative delivery infrastructure.
Even when extraction and local publication succeeded, an unpublished failure
cannot be reported immediately by the deployed dashboard. It can detect
overdue delivery from its last delivered source timestamp, without knowing
the failure's cause. GitHub Actions remains the source of delivery diagnostics.

## Cost controls

The default cap is 5,368,709,120 bytes (5 GiB) per extraction job, controlled
by `LATEST_MAX_BYTES_BILLED`. Invalid or nonpositive caps fail closed. There
is no automatic increase. An actual refresh first retrieves its existing
daily job when available, validates its SQL, dates and original billing cap,
and reuses it without another dry run or extraction. For a new job, the runner
performs a dry run and rejects an estimate above the cap; the actual job also
sets `maximum_bytes_billed`. Explicit `--dry-run` mode always requests only
an estimate and never starts or retrieves an extraction job.
Queries use `us-east1` and an explicit billing project.

The job ID is `near_growth_intelligence_latest_YYYYMMDD` in that project.
Reruns retrieve the existing daily job and require the same SQL and date
parameters. Failed daily jobs are not retried under another ID automatically.
This permits at most one actual extraction job per UTC date through this
runner. Do not reuse the job namespace for other programs. Changes to SQL or
date parameters after a job exists fail until a new date; do not bypass this
guard to force additional scans.

At the default cap, 31 daily jobs have a maximum billed-query volume of
155 GiB. Actual charges depend on processed data and current BigQuery pricing.
GitHub Actions minutes may incur charges beyond the repository plan's quota;
small result-transfer charges may also apply. No bucket, database or permanent
compute service is introduced. Billing alerts are monitoring, not hard caps.

## Future cloud and repository setup

Perform these steps only after separately approving activation:

1. Choose the billing-enabled Google Cloud project and enable the BigQuery,
   IAM Credentials and Security Token Service APIs as required. Verify access
   to the public dataset in `us-east1`. The service account needs
   `roles/bigquery.jobUser` on the billing project; do not grant broad project
   data access for a public source.
2. Create a dedicated service account and a Workload Identity Federation pool
   and OIDC provider for `https://token.actions.githubusercontent.com`.
   Map `google.subject=assertion.sub`,
   `attribute.repository_id=assertion.repository_id`,
   `attribute.repository_owner_id=assertion.repository_owner_id`,
   `attribute.ref=assertion.ref` and
   `attribute.workflow_ref=assertion.workflow_ref`.
3. Restrict the provider condition to the exact numeric repository and owner
   IDs, `assertion.ref == 'refs/heads/main'`, and
   `assertion.workflow_ref == 'sejiro17/near-growth-intelligence/.github/workflows/latest-activity.yml@refs/heads/main'`.
   Use the actual numeric IDs, not account names alone. Bind
   `roles/iam.workloadIdentityUser` on this service account only to
   `principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/POOL_ID/attribute.repository_id/REPOSITORY_ID`.
4. Create a GitHub environment named `latest-activity`, restricted to `main`,
   with required reviewers when supported by the repository plan. Set the
   non-secret environment/repository variables below. Leave the enable flag
   unset or false until activation is approved. No service-account keys are
   required. Authentication uses short-lived GitHub OIDC credentials.
5. Verify that the existing Streamlit deployment follows `main`, automatically
   reloads after data commits, and keeps its existing restricted access.
   Confirm repository rules allow the narrow data publication. Do not weaken
   branch protection; if direct bot publication is disallowed, stop and agree
   a delivery alternative before activation. Do not add an app credential.
6. Review the pinned action revisions below before activation. They were
   resolved from the official upstream repositories and fetched to verify
   that each SHA names a Git commit containing `action.yml`. Actions are
   referenced by immutable commit IDs, with no version-tag references.

| Action | Verified upstream ref | Pinned commit |
|---|---|---|
| [actions/checkout](https://github.com/actions/checkout/commit/11d5960a326750d5838078e36cf38b85af677262) | `v4`, checked 28 October 2026 | `11d5960a326750d5838078e36cf38b85af677262` |
| [actions/setup-python](https://github.com/actions/setup-python/commit/a26af69be951a213d495a4c3e4e4022e16d87065) | `v5` / `v5.6.0`, checked 28 October 2026 | `a26af69be951a213d495a4c3e4e4022e16d87065` |
| [google-github-actions/auth](https://github.com/google-github-actions/auth/commit/c200f3691d83b41bf9bbd8638997a462592937ed) | `v2` / `v2.1.13`, checked 28 October 2026 | `c200f3691d83b41bf9bbd8638997a462592937ed` |

| Variable | Value |
|---|---|
| `LATEST_REFRESH_ENABLED` | Unset/`false` now; `true` only after approval. Must be a repository variable for the job-level guard. |
| `LATEST_BILLING_PROJECT` | Billing project ID. |
| `LATEST_WIF_PROVIDER` | Full `projects/.../locations/global/workloadIdentityPools/.../providers/...` resource. |
| `LATEST_SERVICE_ACCOUNT` | Dedicated service-account email. |
| `LATEST_MAX_BYTES_BILLED` | Explicit positive byte cap; default `5368709120`. |

The auth action's temporary `gha-creds-*.json` file is ignored by Git and
cleaned up by the action. Never put credentials in exports, repository files,
workflow inputs, environment examples or logs. The workflow stages only
`latest_activity_data/`. The app requires no new secrets or BigQuery dependency.
Repository delivery requires the Streamlit Git integration to synchronize
`main`; the workflow does not upload files directly to Streamlit. Do not rely
on a separate Actions push-triggered deployment workflow being triggered by
commits made with `GITHUB_TOKEN`.

## Local checks and future manual operation

Install the app and refresh dependencies in an isolated environment:

```bash
python -m pip install -r requirements.txt -r requirements-refresh.txt
python -m unittest discover -s tests -v
```

Tests use generated temporary fixtures and mocked clients; they do not submit
queries, authenticate to Google Cloud or create an initial repository export.

After future authentication and explicit approval, a dry run can be requested:

```bash
LATEST_REFRESH_ENABLED=true LATEST_BILLING_PROJECT=YOUR_PROJECT_ID LATEST_MAX_BYTES_BILLED=5368709120 python -m latest_activity.refresh --dry-run
```

This validates the query against BigQuery and prints an estimate without
publishing data. Review it before manually dispatching the GitHub workflow on
`main` with confirmation `REFRESH`. Inspect job costs and status after each
run. A failed extraction remains a failed workflow even if its failure status
was successfully published. A single run does not skip the stability rule.

No scheduled trigger is included. Adding a daily schedule is a separate change
requiring approval; until then the section's timestamps describe actual manual
refreshes and must not be presented as an operating daily schedule.
