# NEAR: Growth Quality and Investment Assessment

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

## Investment Assessment

NEAR maintained substantial transaction activity during the selected eight weeks. Transactions outside the first week's ten busiest signing accounts grew, even as activity from that fixed group declined. Growth therefore extended beyond the original leaders, but this does not establish broader participation by independent users.

My assessment remains conditional: an investment argument based on adoption growth needs stronger evidence of persistent application demand and a measurable connection between that demand and NEAR's economics.

The findings show why headline activity needs context:

- Final-week transactions were above their starting level, while weekly active signing accounts were below theirs.
- Transactions outside the first week's top ten signing accounts increased 52.50%; activity from that fixed group declined 19.83%.
- One investigated growth-contributing account had a 91.90% initial-receipt failure rate.
- Successful self-deletion activity was widespread among accounts absent after the participation spike.
- Transactions were concentrated among signing accounts and original receivers whose roles remain unverified.
- Recorded receipt execution costs increased 82.73% between the first and final weeks, while observed total supply increased approximately 4.936 million NEAR across the period.

The economic findings establish increased execution spending and a net increase in observed total supply. They do not provide a complete reconciliation of issuance, fee allocation, permanent burning or value accruing to holders.

These results support specific investigation priorities. They are insufficient on their own to justify an investment argument based on broad, sustained adoption.

## Observation Period

The primary analysis covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC.

The period contained 44,284,794 transactions and 280,743,473 receipt execution outcomes. These are different units and should not be treated as interchangeable measures of usage.

Signing accounts are identifiers, not verified individuals. They may represent people, automated services, relayers or other participants.

The supply comparison uses the closing supply on 23 August as its opening baseline and the closing supply on 18 October as its endpoint.

The conclusions apply to this observation window. They do not establish NEAR's long-term trajectory.

## What the Evidence Shows

### Transaction activity continued, but growth was uneven

Weekly transactions increased from 4,734,816 in the first week to a peak of 6,590,352 during 28 September–4 October.

The final week recorded 4,909,532 transactions, 3.69% above the first week but 23.31% below the preceding week.

Weekly active signing accounts ended at 129,446, compared with 139,759 in the first week: a decline of 7.38%.

Transaction activity therefore continued without a corresponding increase in weekly signing-account participation between the two endpoints.

This weakens the use of transaction growth alone as evidence of broader adoption. It does not establish that the remaining activity lacked useful demand, because account roles and transaction purposes have not been verified.

Evidence: results 09, 10 and 14.

### Self-deletion activity was widespread within the spike cohort

Weekly active signing accounts increased 198.16% to 457,768 during 28 September–4 October. Of these accounts, 82.31% were active on only one day that week.

Only 83,037 accounts, or 18.14% of the starting cohort, were active during 5–11 October.

Further checks found that 309,280 accounts absent the following week had successful receipt executions containing self-deletion actions during the starting week. They represented 82.53% of the absent group and 67.56% of the full starting-week cohort.

The account spike therefore includes extensive lifecycle activity. It should not be treated as a direct measurement of newly acquired users, and the low following-week return share should not be presented as ordinary user churn.

The reasons for deletion, account ownership and later recreation remain unverified. The results do not establish how much deletion activity explains the increase from the preceding week.

Removing these accounts from a denominator would not, by itself, produce a verified user-retention measure.

Evidence: results 10, 11, 16 and 17.

### Accounts active again generated most starting-week transactions

The 18.14% of accounts active again the following week generated 5,788,805 transactions during the starting week: 87.84% of that week's total.

The remaining 81.86% of accounts generated 12.16% of transactions.

Most starting-week transaction activity therefore came from identifiers that also participated in the following week. The large number of absent accounts did not represent an equally large share of starting-week transactions.

These figures describe the composition of starting-week activity. They do not measure how much transaction activity those accounts maintained in the following week, or whether they represented independent users.

Evidence: results 11 and 15.

### Transaction concentration makes participant roles important

The ten busiest signing accounts contributed 48.17%–67.76% of weekly transactions. The ten busiest original transaction receivers accounted for 60.85%–70.22%.

Changes involving a small number of accounts could therefore materially affect headline transaction figures.

The next question is what these accounts represent: independent applications, shared infrastructure, relayers, automated services or other participants.

Concentration alone does not establish manipulation or weak demand. Shared infrastructure can serve many users while concentrating transactions under a small number of identifiers.

The findings establish concentration at the account level. They do not establish equivalent concentration in application ownership, economic activity or end users.

Evidence: results 10 and 12.

### Growth extended beyond the original leading accounts

I fixed the ten busiest signing accounts from 24–30 August and followed the same identifiers across all eight weeks. Their combined weekly transactions declined from 3,195,028 to 2,561,335: a decrease of 19.83%.

Transactions from all other accounts increased from 1,539,788 to 2,348,197, or 52.50%. Their increase of 808,409 transactions more than offset the original leaders' decline of 633,693, leaving the network's net increase of 174,716 transactions.

Keeping membership fixed establishes growth outside the original leaders. It does not show whether NEAR would have grown without them.

The increase outside the fixed group was not confined to other accounts appearing in weekly leader rankings. Accounts never appearing in any week's top twenty contributed 354,120 transactions, or 43.80% of the outside group's net increase. Other tracked accounts contributed the remaining 454,289, or 56.20%.

These are contributions to a net change, not shares of all transactions. The untracked group combines many identifiers; its growth does not establish more users, independent ownership or useful application demand.

Evidence: results 18, 21 and 22.

### Account action records reveal different forms of activity

DELEGATE_ACTION appeared in 96.66% of transactions signed by sweat-relayer.near and 98.02% of those signed by meteor-relayer.near.

These records make it important to examine delegated activity before interpreting signing-account concentration as equivalent concentration among end users. I have not expanded the delegated actions or verified the participants behind them.

All 2,769,479 transactions signed by intents.near contained execute_intents calls to the same account. Other investigated accounts interacted with multiple receivers and methods.

These observations describe recorded actions and destinations. They do not verify operators' identities or the final results of execution chains.

A concentrated signing identifier can therefore represent a different activity pattern from an account submitting direct contract calls. Account counts alone do not resolve that difference.

Evidence: results 18–20.

### Selected growth included substantial failed execution activity

Two accounts outside the fixed group, tinykoala595.near and wx-cruce.near, contributed 148,950 and 137,767 transactions respectively to the first-to-final-week increase. They represented 18.43% and 17.04% of the outside group's net increase.

Neither had transactions in the first week. This does not establish when either account was created or first used.

Across the full observation period, tinykoala595.near signed 778,588 transactions. Of these, 778,338 contained swap calls targeting v2.ref-finance.near. Separately, matching each transaction to its initial receipt showed 715,518 failures: 91.90% of the account's transactions.

The action and outcome summaries do not cross-tabulate every method against every outcome. I therefore do not claim that all 715,518 failures were swap failures. They establish that a growth-contributing account combined predominantly swap-related submissions with a high initial-receipt failure rate.

For wx-cruce.near, 6,441 of 413,281 initial receipts failed, or 1.56%. Most returned SUCCESS_RECEIPT_ID: 398,968, or 96.54%. That status does not prove successful downstream execution or completed economic activity.

These accounts were selected because of their growth contributions. Their outcome shares cannot be extrapolated to other accounts or used as network-wide failure rates.

Evidence: results 22–24.

### Failed initial receipts also contributed execution costs

For tinykoala595.near, recorded initial-receipt execution costs totalled approximately 243.3451 NEAR. Failed receipts accounted for 211.1629 NEAR, or 86.78% of those costs, compared with 91.90% of its transactions.

For wx-cruce.near, recorded initial-receipt costs totalled approximately 115.0938 NEAR. Failed receipts contributed 1.0978 NEAR, or 0.95% of costs, compared with 1.56% of transactions.

Execution spending can therefore include failed activity. Higher recorded costs need to be examined alongside execution outcomes before supporting an argument about successful application demand.

These amounts cover initial receipts only, grouped by transaction submission week. They exclude transaction receipt-conversion costs and downstream receipts. They do not measure protocol revenue, permanent token burning or value accruing to holders.

Evidence: result 27.

### The diagnostic sample identified reported contract errors

I inspected three selected failed receipts per active week for tinykoala595.near, covering eighteen receipts across six weeks. All eighteen returned validated failures executing on v2.ref-finance.near.

Seventeen reported E68: slippage error. One reported E22: not enough tokens in deposit.

The sample establishes two reported error messages. It does not estimate their frequencies across all 715,518 failures, establish retries, identify automation or explain the underlying operational causes.

The BigQuery log arrays for the sampled receipts were empty, but the RPC receipt statuses contained execution errors. Empty log arrays therefore did not mean that diagnostic information was unavailable.

Evidence: results 25 and 26.

### Receipt volume and average cost help explain the spending comparison

Recorded receipt execution costs totalled approximately 65,878.09 NEAR across the eight weeks.

The first and final weeks differed as follows:

| Measure | First week | Final week | Change |
|---|---:|---:|---:|
| Transactions | 4,734,816 | 4,909,532 | +3.69% |
| Receipt execution outcomes | 25,978,633 | 43,344,970 | +66.85% |
| Recorded receipt execution cost | 5,770.56 NEAR | 10,544.79 NEAR | +82.73% |
| Average recorded cost per receipt | 0.00022213 NEAR | 0.00024328 NEAR | +9.52% |

The cost comparison reflects both more receipt execution outcomes and a higher average recorded cost per receipt between the endpoints.

This is an arithmetic relationship: total recorded receipt cost equals the number of receipt outcomes multiplied by average recorded cost per outcome. It does not establish why receipt counts or average costs changed.

Execution complexity, gas prices and changes in the mix of operations remain possible subjects for separate investigation. Their individual contributions have not been measured here.

Transactions are grouped by submission date; receipt outcomes and their costs are grouped by execution date. The comparison does not match individual transactions to their complete execution costs.

These figures exclude transaction receipt-conversion costs and do not measure protocol revenue, permanent token burning or holder returns.

Evidence: results 13, 14 and 34.

### Observed total supply increased during the period

Closing total supply increased from approximately 1,304,386,568.87 NEAR on 23 August to 1,309,322,552.85 NEAR on 18 October.

The net observed increase was approximately 4,935,983.98 NEAR, or 0.3784% of opening supply.

Each of the eight weekly closing-supply comparisons showed a positive net change.

This establishes a net increase in the total-supply values recorded in the dataset. Total supply is different from circulating supply, and the result does not separately quantify gross issuance and permanent burning.

The increase occurred during a period with substantial recorded execution spending. Execution costs alone therefore cannot be treated as evidence that total supply declined.

The comparison does not establish what supply would have been without that activity or attribute the net change to particular economic mechanisms.

Evidence: results 28, 33 and 34.

### The supply reconciliation remains incomplete

I compared observed block supply movements with balance changes recorded under validator_accounts_update.

Across the period:

| Measurement | Approximate NEAR |
|---|---:|
| Observed positive block supply movements | 4,990,242.56 |
| Observed block supply decrease magnitude | 54,258.58 |
| Net observed supply increase | 4,935,983.98 |
| Validator-update net balance change | 4,919,384.47 |
| Net supply increase minus validator-update change | 16,599.51 |
| Positive supply movements minus validator-update change | 70,858.09 |

Positive block supply movements minus the decrease magnitude reconcile to the net observed supply change.

The validator-update balance comparison does not fully reconcile with those supply movements. The differences remain unresolved.

I therefore do not label validator-update balance changes as a complete measurement of gross issuance, or block supply decreases as a complete measurement of permanent burning. Changes within a block can contain offsetting effects.

The tiny negative validator balance differences inspected for 24 August were within the analytical tolerance subsequently applied. No individual negative validator balance change exceeded 0.000001 NEAR in magnitude in the full-period comparison.

That tolerance is an analytical choice for handling the observed floating-point differences. It is not a protocol rule or a guarantee of source precision.

The unresolved reconciliation limits the economic decomposition. It does not erase the separately measured net increase in observed total supply.

Evidence: results 29–34.

## What This Means for the Investment Case

The positive evidence is continued transaction activity, growth outside the original leading accounts, and the substantial contribution of accounts observed in consecutive weeks to starting-week transactions.

The main reservations are that broader participation by independent users was not demonstrated, lifecycle events complicate return measures, and major participants' roles remain unverified.

The selected-account findings also show that growth can include substantial failed execution activity. This does not erase growth elsewhere, but it weakens an interpretation that treats every additional transaction as successful application demand.

The economic comparison now distinguishes receipt volume, average recorded cost and observed total-supply movement. It shows that recorded receipt costs rose faster than transactions between the endpoints, while total supply increased across the period.

It does not quantify the benefit of that activity to NEAR holders. Fee distributions and the components of supply movement remain incompletely reconciled.

My assessment is therefore that this evidence does not establish an adoption-led investment case. This is a conclusion about the evidence examined, rather than a claim that NEAR has no investment merit.

## Decision Priorities

The findings support five practical investigation priorities.

| Priority | Decision implication | Next action |
|---|---|---|
| Check lifecycle before interpreting account returns | Absence after the spike is not a verified user-churn measure | Examine deletion, recreation and account roles before evaluating acquisition or retention |
| Check execution quality behind growth | More submissions and execution spending do not necessarily mean more successful application interactions | Examine receipt outcomes and diagnostic errors alongside transaction growth |
| Verify the roles behind concentration | Signing-account concentration does not directly establish end-user or application-ownership concentration | Verify major account roles and examine delegated interactions |
| Follow growth beyond the original leaders | The original leaders do not explain all observed growth | Investigate other contributors' roles, persistence and execution quality |
| Require reconciliation before making economic claims | Higher recorded costs do not establish permanent burning, protocol revenue or holder value | Identify and reconcile economic flows before making supply or valuation claims |

These priorities are qualitative interpretations of the research. They are not automated scores, verified application-impact rankings or buy-and-sell signals.

The evidence, actions and measurement boundaries are documented in [decision_priorities.md](decision_priorities.md).

## Connection to NEAR's Economics

Official documentation describes uses for NEAR through execution fees, storage requirements and staking. Product revenues and governance-controlled uses of those revenues provide additional mechanisms to investigate.

The investment question is whether persistent, useful activity creates durable demand for the token or produces other measurable economic effects.

This project measures recorded receipt execution costs and observed total-supply movement. It does not provide a complete reconciliation of gross issuance, permanent burning, fee allocation, storage commitments, staked balances or realised buyback expenditure.

I reviewed the mechanisms and their measurement boundaries in [economic_mechanisms.md](economic_mechanisms.md).

Historical parameters and relevant economic flows would need separate verification before building a supply or valuation model. Current documentation does not prove that every described rule applied unchanged throughout the observation period.

## What Would Change My Assessment?

### Evidence that would strengthen the investment case

- Participation and transaction activity sustained across longer periods, with lifecycle events examined separately.
- Verified applications attracting repeated interaction from participants whose roles are understood.
- Evidence that concentrated infrastructure activity serves persistent, independent demand.
- Growth outside the original leaders that persists and includes successful, identifiable application interactions.
- Reconciled economic flows connecting measured usage to demand for NEAR, fee allocation and supply changes.

### Evidence that would weaken the investment case

- Repeated headline growth without persistent application participation once lifecycle activity is examined.
- Declining participation across comparable cohorts with consistent definitions and complete follow-up.
- Increasing dependence on a few participants, accompanied by evidence of weakening independent demand.
- Broader evidence that transaction growth is dominated by failed or temporary activity.
- Economic measurements that do not support the token-demand or supply effects assumed in an investment argument.

These are conditions for further testing. The current analysis has not established all of them.

## How the Research Supports Decisions

### Investors and research analysts

The dashboard helps test whether headline activity growth is accompanied by broader participation, repeat activity and changes in execution spending.

The fixed-account comparison identifies growth beyond the original leaders. Execution checks examine the quality of selected growth, while the economic comparison separates recorded costs from observed supply movement.

Together, these views help identify which assumptions require more evidence before they enter an investment thesis.

### NEAR ecosystem teams

The results show why account growth should be examined alongside lifecycle events, concentration and execution outcomes before informing ecosystem support.

Receiver rankings and growth contributions identify activity for investigation. Reported contract errors provide diagnostic leads, while the decision-priority view connects findings to practical next actions.

These results do not establish a verified ranking of application quality or ecosystem impact.

### Application developers

The project provides a framework for examining participation and return activity while distinguishing signing identifiers from people.

Receipt outcomes, reported contract errors and execution costs add context to transaction counts. Application-level conclusions would require verified account mapping, relevant interactions and complete execution-chain analysis.

## Data Quality and Remaining Uncertainty

Transaction-hash uniqueness, timestamp coverage, account fields and weekly reconciliations passed the checks performed.

Within the primary period, checked execution outcomes matched exactly one ACTION receipt. Earlier unmatched outcomes during 1 July–22 August remain unresolved.

The spike action analysis found 474 transactions without matching transaction-action records in its selected lookup window. These remain a documented coverage limitation.

The deletion analysis matched all 309,642 selected deletion transactions to exactly one initial receipt outcome. Successful and failed outcomes were examined separately.

The leading-account series includes all eight weeks for the 51 identifiers appearing in at least one weekly top-twenty ranking. The fixed-account and growth-contribution tables reconcile to network transaction totals.

For the two selected growth accounts, all 1,191,869 transactions matched exactly one initial receipt outcome, with the executor matching the original receiver. Their cost results reconcile to those outcome counts. This does not establish the results of downstream receipts.

All eighteen diagnostic responses matched the sampled transaction hashes, signing accounts, receipt identifiers, executors and failure statuses. Raw RPC responses and earlier unsuccessful retrieval attempts are preserved in result 26.

The supply investigation checked 57 daily closing-supply observations, including the opening baseline, and 56 days of block supply movements and validator balance comparisons. Weekly supply changes reconcile to the closing-supply observations and the aggregated block movements.

The validator-update comparison remains incompletely reconciled with supply movements. Source balance, cost and supply fields use floating-point storage, so reported amounts are approximate.

These checks support the measurements reported. They do not establish account ownership, deletion motives, permanent loss of an identifier, population-wide error frequencies or a complete economic-flow model.

No price forecast, valuation model or expected token return has been derived from this analysis.

## Reproducibility

The SQL queries, exported results and Python scripts are stored in this repository.

The fixed-account comparison and contribution tables can be regenerated from saved exports using:

- `analysis/03_fixed_account_growth.py`
- `analysis/04_account_growth_contributions.py`

The weekly economic comparison can be regenerated using `analysis/06_weekly_economic_comparison.py`.

The diagnostic retrieval script, `analysis/05_fetch_failure_details.py`, preserves validated saved responses and resumes incomplete lookups. Retrieving missing responses requires RPC access.

The dashboard can be run using the instructions in [README.md](../README.md). It displays saved exports rather than querying BigQuery when opened.

Detailed checks and investigation notes are recorded in [data_checks.md](data_checks.md).