/* @datacloud.settings
{
  "version": 1,
  "service": "BIG_QUERY",
  "connectionInfo": {
    "billingProjectId": "INHERIT"
  },
  "dialect": "GOOGLE_SQL"
}
*/

WITH account_weeks AS (
    SELECT DISTINCT
        DATE_TRUNC(block_date, WEEK(MONDAY)) AS week_start,
        signer_account_id
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date BETWEEN DATE '2026-08-24'
                             AND DATE '2026-10-18'
),
cohort_sizes AS (
    SELECT
        week_start AS cohort_week,
        COUNT(*) AS cohort_accounts
    FROM account_weeks
    GROUP BY week_start
),
eligible_followups AS (
    SELECT
        c.cohort_week,
        c.cohort_accounts,
        week_offset,
        DATE_ADD(
            c.cohort_week,
            INTERVAL week_offset WEEK
        ) AS followup_week
    FROM cohort_sizes AS c
    CROSS JOIN UNNEST(GENERATE_ARRAY(0, 4)) AS week_offset
    WHERE DATE_ADD(
        c.cohort_week,
        INTERVAL week_offset WEEK
    ) <= DATE '2026-10-12'
),
return_counts AS (
    SELECT
        starting.week_start AS cohort_week,
        DATE_DIFF(
            returning.week_start,
            starting.week_start,
            WEEK(MONDAY)
        ) AS week_offset,
        COUNT(*) AS active_cohort_accounts
    FROM account_weeks AS starting
    INNER JOIN account_weeks AS returning
        ON starting.signer_account_id = returning.signer_account_id
        AND returning.week_start BETWEEN starting.week_start
            AND DATE_ADD(starting.week_start, INTERVAL 4 WEEK)
    GROUP BY cohort_week, week_offset
)
SELECT
    e.cohort_week,
    DATE_ADD(e.cohort_week, INTERVAL 6 DAY) AS cohort_week_end,
    e.cohort_accounts,
    e.week_offset,
    e.followup_week,
    DATE_ADD(e.followup_week, INTERVAL 6 DAY) AS followup_week_end,
    COALESCE(r.active_cohort_accounts, 0) AS active_cohort_accounts,
    ROUND(
        100.0 * SAFE_DIVIDE(
            COALESCE(r.active_cohort_accounts, 0),
            e.cohort_accounts
        ),
        2
    ) AS cohort_active_share_pct
FROM eligible_followups AS e
LEFT JOIN return_counts AS r
    ON e.cohort_week = r.cohort_week
    AND e.week_offset = r.week_offset
ORDER BY e.cohort_week, e.week_offset;