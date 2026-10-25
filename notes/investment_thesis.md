# NEAR: Growth Quality and Investment Assessment

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

## Initial Assessment

My findings show substantial transaction activity, concentrated usage and a sharp increase in active signing accounts that requires careful interpretation.

The strongest finding is that account activity can reflect account deletion as well as ongoing participation. During the peak week, most accounts absent the following week had successfully executed receipts containing self-deletion actions.

I therefore do not interpret the account spike as evidence of successful user acquisition, or the subsequent decline as ordinary user churn.

The evidence supports investigating NEAR's activity beyond headline counts. It does not yet establish sustained adoption or economic value accruing to NEAR holders.

## Observation Period

The primary analysis covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC.

The period contained 44,284,794 transactions and 280,743,473 receipt execution outcomes. These are different units and should not be treated as interchangeable measures of usage.

Signing accounts are identifiers, not verified individuals. They may represent people, automated services, relayers or other participants.

## What the Evidence Shows

### Transaction activity persisted, but growth was uneven

Weekly transactions increased from 4,734,816 in the first week to a peak of 6,590,352 during 28 September–4 October.

The final week recorded 4,909,532 transactions, 3.69% above the first week but 23.31% below the preceding week.

Activity continued throughout the observation period. However, the increase was not maintained at its peak, and eight weeks cannot establish long-term growth.

Evidence: results 09 and 14.

### The account spike was heavily affected by deletion activity

Weekly active signing accounts increased 198.16% to 457,768 during 28 September–4 October. Only 83,037 (18.14%) were active the following week.

Further checks found that 309,280 accounts absent the following week had successful receipt executions containing self-deletion actions. They represented 82.53% of the absent group and 67.56% of the full starting-week cohort.

This finding changes the interpretation of the return figures. The data records account activity, including successful deletion, rather than directly measuring people adopting or abandoning applications.

The reasons for deletion, account ownership and later recreation remain unverified. The results do not establish that deletion explains every part of the increase from the preceding week.

Evidence: results 10, 11, 16 and 17.

### Accounts that returned generated most starting-week transactions

The 18.14% of accounts active again the following week generated 5,788,805 transactions during the starting week: 87.84% of that week's total.

The remaining 81.86% of accounts generated 12.16% of transactions.

This shows why account counts and transaction counts need to be considered together. A large change in account participation can coexist with activity dominated by a smaller group.

These shares describe the selected cohort. They do not establish whether returning accounts represented independent users or automated activity.

Evidence: results 11 and 15.

### Concentration creates dependence on a limited set of accounts

The ten busiest signing accounts contributed 48.17%–67.76% of weekly transactions. The ten busiest original transaction receivers attracted 60.85%–70.22%.

This concentration makes the identity and role of major participants important to the investment assessment. Changes involving a small number of accounts could materially affect network-level activity.

Concentration alone does not establish manipulation or weak demand. Relayers and shared infrastructure can also concentrate transaction activity. Account roles require verification before drawing application-level conclusions.

Evidence: results 10 and 12.

### Execution costs rose faster than transaction activity

Recorded receipt execution costs totalled approximately 65,878.09 NEAR across the eight weeks.

The final week's recorded costs were 82.73% above the first week's, compared with a 3.69% increase in transactions.

The different growth rates show that transaction counts alone do not describe changes in execution costs. This analysis has not established the contribution of execution complexity, receipt volume, gas prices or other factors to that difference.

Receipt costs are grouped by execution date, while transactions are grouped by submission date. The comparison does not match individual transactions to their complete execution costs.

These figures exclude transaction receipt-conversion costs and do not measure protocol revenue, permanent token burning or holder returns.

Evidence: results 13 and 14.

## Implications for the Investment Case

The evidence supporting further investigation is that NEAR sustained transaction activity throughout the selected period, while accounts active again the following week generated most transactions during the peak week.

The main concerns are activity concentration and the difficulty of interpreting account counts without understanding account roles and lifecycle events.

The account spike is not sufficient evidence of adoption. Equally, the low following-week return share is not sufficient evidence of ordinary user churn, given the successful self-deletions.

My current position is that headline activity growth provides an incomplete basis for a long-term investment argument. A stronger case requires persistent participation associated with identifiable uses, alongside a supported explanation of how that activity creates demand for NEAR or affects its economics.

## Connection to NEAR's Economics

Official documentation describes demand for NEAR through execution fees, storage requirements and staking. Product revenues and governance-controlled uses of those revenues provide additional mechanisms to investigate.

My execution-cost results measure only part of this picture. They do not establish net issuance, permanent token burning, changes in staked balances or realised buyback expenditure.

I reviewed these mechanisms and their measurement boundaries in [economic_mechanisms.md](economic_mechanisms.md). Historical parameters and economic flows would need separate verification before building a supply or valuation model.

## What Would Strengthen or Weaken This Assessment?

Evidence that would strengthen the case includes:

- Participation that persists across longer periods and remains visible after accounting for deletion activity.
- Verified applications attracting sustained interaction across a broader set of accounts.
- Evidence distinguishing infrastructure activity from end-user participation.
- A documented connection between measured network activity and NEAR's economic mechanisms.

Evidence that would weaken the case includes:

- Repeated activity increases dominated by temporary account lifecycle events.
- Declining participation across comparable cohorts after lifecycle effects are examined.
- Continued dependence on a few participants whose activity does not reflect broader demand.

These are questions for further testing, not conclusions already established.

## Data Quality and Remaining Uncertainty

Transaction-hash uniqueness, timestamp coverage, account fields and weekly reconciliations passed the checks performed.

Within the primary period, checked execution outcomes matched exactly one ACTION receipt. Earlier unmatched outcomes during 1 July–22 August remain unresolved.

The spike action analysis also found 474 transactions without matching transaction-action records in its selected lookup window. These remain documented as a coverage limitation.

The deletion analysis matched every selected deletion transaction to exactly one initial receipt outcome. It does not establish account ownership or permanent deletion of an identifier.

No price forecast, valuation model or expected token return has been derived from this analysis.

## Reproducibility

The SQL queries, exported results and Python scripts are stored in this repository.

The dashboard can be run using the instructions in [README.md](../README.md). Detailed checks and investigation notes are recorded in [data_checks.md](data_checks.md).