# NEAR: Growth Quality & Investment Intelligence

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

## Project Status

Research setup and data validation. I have not drawn any investment conclusions.

## Scope

I will examine activity trends, repeat account participation, concentration and recorded execution costs.

The primary analysis covers 24 August–18 October 2026: eight complete weeks in UTC. Records through 24 October provide additional follow-up.

## Data and Tools

- NEAR public blockchain data: `bigquery-public-data.crypto_near_mainnet_us`
- SQL and Google BigQuery
- Python
- Interactive dashboard

## Research Plan

The planned analysis and interpretation boundaries are documented in [notes/research_plan.md](notes/research_plan.md).

## Repository Structure

- `sql/`: Extraction, validation and analytical queries.
- `analysis/`: Python scripts.
- `results/`: Exported query results.
- `dashboard/`: Dashboard files.
- `notes/`: Research plan, data checks and findings.