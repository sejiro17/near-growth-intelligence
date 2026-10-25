# NEAR: Growth Quality & Investment Intelligence

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

## Purpose

I will examine whether growth in headline activity is accompanied by repeat participation, broader activity distribution and increased demand for network execution.

This research is intended for investors and ecosystem analysts evaluating NEAR's long-term prospects.

## Analysis

1. Activity trends: I will examine daily and weekly transactions and active signing accounts.
2. Repeat participation: I will measure whether accounts active in a given period return in later periods.
3. Concentration: I will examine how activity is distributed across signing accounts and receiving contracts.
4. Execution costs: I will assess whether recorded execution costs increase alongside activity.

## Data and Tools

I will use the public BigQuery dataset:

`bigquery-public-data.crypto_near_mainnet_us`

I will use SQL for extraction and validation, Python for analysis, and an interactive dashboard to present the findings.

I will choose the observation period after checking data coverage and query costs.

## Deliverables

- One interactive dashboard covering the four analysis areas.
- Reproducible SQL queries, Python scripts and result exports.
- One concise investment research report explaining the findings, risks and limitations.

## Interpretation

I will treat accounts as identifiers rather than verified individuals. I will label receiving contracts as applications only where a documented mapping supports that interpretation.

I will distinguish recorded execution costs from revenue and token-holder returns. I will not attribute activity patterns to campaigns, bots or other causes without supporting evidence.

I will separate observed evidence from assumptions and explain what the findings support about NEAR's long-term prospects.

## Observation Period

I will use 24 August–18 October 2026 as the primary analysis period. This covers eight complete Monday–Sunday weeks in UTC.

The period falls within the interval where all inspected execution-outcome identifiers matched exactly one ACTION receipt. Transaction validation also found unique hashes, no missing key identifiers or timestamps, and activity in every UTC hour.

I will retain 19–24 October as additional follow-up data and exclude that partial week from full-week growth comparisons.

I selected the period based on matching coverage and calendar alignment. These checks do not establish complete ingestion.

For cohort comparisons, I will use equal follow-up periods and omit observations that have not had enough time to mature. First observed will mean first seen within the available observation window, not first-ever use.

The earlier validation results remain documented, including unresolved receipt matching for outcomes dated 1 July–22 August.