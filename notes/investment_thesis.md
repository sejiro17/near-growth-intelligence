# NEAR: Growth Quality and Investment Assessment

## Research Question

Is NEAR's activity growth persistent and broadly distributed, and what does that imply for its long-term investment case?

## Investment Assessment

NEAR maintained substantial transaction activity during the selected eight weeks. Transactions outside the first week’s ten busiest signing accounts grew, even as activity from that fixed group declined. This is evidence that activity growth extended beyond the original leaders, but it does not establish broader participation by independent users or quantify economic value accruing to NEAR holders.

My assessment is conditional: an investment argument based on adoption growth needs stronger evidence of persistent application demand and a measurable connection between that demand and NEAR's economics.

Five findings shape this position:

- Transaction activity ended above its starting level, while weekly active signing accounts ended below theirs.
- Transactions outside the first week’s top ten signing accounts increased 52.50%; activity from the original ten declined 19.83%.
- Checks on two growth-contributing accounts showed different execution outcomes. One had a 91.90% failure rate for initial receipts, demonstrating why transaction growth needs an execution-quality check.

- Successful self-deletion activity was widespread among accounts absent after the participation spike, making a straightforward user-churn interpretation inappropriate.

- Transactions were concentrated among a small number of signing accounts and original receivers whose roles remain unverified.

Recorded receipt execution costs also increased substantially between the first and final weeks. This establishes increased recorded spending on receipt execution, but its contribution to token-holder value remains unquantified.

These findings support further due diligence. They are insufficient on their own to justify an investment based on claims of broad, sustained adoption.

## Observation Period

The primary analysis covers 24 August–18 October 2026: eight complete Monday–Sunday weeks in UTC.

The period contained 44,284,794 transactions and 280,743,473 receipt execution outcomes. These are different units and should not be treated as interchangeable measures of usage.

Signing accounts are identifiers, not verified individuals. They may represent people, automated services, relayers or other participants.

The conclusions apply to this observation window. They do not establish NEAR's long-term trajectory.

## What the Evidence Shows

### Transaction activity continued, but growth was uneven

Weekly transactions increased from 4,734,816 in the first week to a peak of 6,590,352 during 28 September–4 October.

The final week recorded 4,909,532 transactions, 3.69% above the first week but 23.31% below the preceding week.

Weekly active signing accounts ended at 129,446, compared with 139,759 in the first week: a decline of 7.38%.

Transaction activity therefore continued without a corresponding increase in weekly signing-account participation between the two endpoints.

This weakens the use of transaction growth alone as evidence of broader adoption. It does not establish that the remaining activity lacked useful demand, because account roles and the purposes of transactions have not been verified.

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

This provides evidence that most starting-week transaction activity came from identifiers that also participated in the following week. The large number of absent accounts did not represent an equally large share of starting-week transactions.

However, these figures describe the composition of starting-week activity. They do not measure how much transaction volume those accounts maintained in the following week, or whether they represented independent users.

Evidence: results 11 and 15.

### Transaction concentration makes participant roles important

The ten busiest signing accounts contributed 48.17%–67.76% of weekly transactions. The ten busiest original transaction receivers accounted for 60.85%–70.22%.

Changes involving a small number of accounts could therefore materially affect headline transaction figures.

For an investment assessment, the next question is what these accounts represent: independent applications, shared infrastructure, relayers, automated services or other participants.

Concentration alone does not establish manipulation or weak demand. Shared infrastructure can serve many users while concentrating transactions under a small number of identifiers.

The findings establish concentration at the account level. They do not establish equivalent concentration in application ownership, economic activity or end users.

Evidence: results 10 and 12.

### Growth extended beyond the original leading accounts

I fixed the ten busiest signing accounts from 24–30 August and followed the same identifiers across all eight weeks. Their combined weekly transactions declined from 3,195,028 to 2,561,335: a decrease of 19.83%.

Transactions from all other accounts increased from 1,539,788 to 2,348,197, or 52.50%. Their increase of 808,409 transactions more than offset the original leaders’ decline of 633,693, leaving the network’s net increase of 174,716 transactions.

This is a more informative comparison than removing each week’s top ten, because the group membership stays fixed. It establishes growth outside the original leaders, rather than showing whether NEAR would have grown without them.

The increase outside the fixed group was not confined to other accounts that entered the weekly leader rankings. Accounts never appearing in any week’s top twenty contributed 354,120 transactions, or 43.80% of the outside group’s net increase. Other tracked accounts contributed the remaining 454,289, or 56.20%.

These are contributions to a net change, not shares of all transactions. The untracked group combines many identifiers; its growth does not establish more users, independent ownership or useful application demand.

Evidence: results 18, 21 and 22.

### Account action records reveal different forms of activity

The leading-account investigation found that DELEGATE_ACTION appeared in 96.66% of transactions signed by sweat-relayer.near and 98.02% of those signed by meteor-relayer.near. These records make it important to examine delegated activity before interpreting signing-account concentration as equivalent concentration among end users. I have not expanded the delegated actions or verified the participants behind them.

All 2,769,479 transactions signed by intents.near contained execute_intents calls to the same account. Other investigated accounts interacted with multiple receivers and methods. These observations describe recorded actions and destinations; they do not verify operators’ identities or the final results of execution chains.

The distinction matters for the investment assessment: a concentrated signing identifier can represent a different activity pattern from an account submitting direct contract calls. Account counts alone do not resolve that difference.

Evidence: results 18–20.

### Selected growth included substantial failed execution activity

Two accounts outside the fixed group, tinykoala595.near and wx-cruce.near, contributed 148,950 and 137,767 transactions respectively to the first-to-final-week increase. They represented 18.43% and 17.04% of the outside group’s net increase. Neither had transactions in the first week; this does not establish when either account was created or first used.

Across the full observation period, tinykoala595.near signed 778,588 transactions. Of these, 778,338 contained swap calls targeting v2.ref-finance.near. Separately, matching each transaction to its initial receipt showed 715,518 failures: 91.90% of the account’s transactions.

The action and outcome summaries do not cross-tabulate every method against every outcome. I therefore do not claim that all 715,518 failures were swap failures. They do establish that a growth-contributing account combined predominantly swap-related submissions with a high initial-receipt failure rate.

For wx-cruce.near, 6,441 of 413,281 initial receipts failed, or 1.56%. Most returned SUCCESS_RECEIPT_ID: 398,968, or 96.54%. That status does not prove successful downstream execution or completed economic activity.

These accounts were selected for investigation because of their growth contributions. Their outcome shares cannot be extrapolated to all other accounts or used as network-wide failure rates.

Evidence: results 22–24.

### The diagnostic sample identified reported contract errors

I inspected three selected failed receipts per active week for tinykoala595.near, covering eighteen receipts across six weeks. All eighteen returned validated failures executing on v2.ref-finance.near.

Seventeen reported E68: slippage error. One reported E22: not enough tokens in deposit. These reported errors establish that at least two error causes occurred within the sample. They do not estimate the distribution of causes across all 715,518 failures, establish retries or identify automation or operator intent.

The BigQuery log arrays for the sampled receipts were empty, but the RPC receipt statuses contained execution errors. Empty log arrays therefore did not mean there was no diagnostic information available.

Evidence: results 25 and 26.

### Recorded execution costs increased faster than transactions

Recorded receipt execution costs totalled approximately 65,878.09 NEAR across the eight weeks.

The final week's recorded costs were approximately 10,544.79 NEAR, 82.73% above the first week's, compared with a 3.69% increase in transactions.

Transaction counts alone therefore do not describe changes in recorded execution spending.

This analysis has not established the contribution of execution complexity, receipt volume, gas prices or other factors to the difference.

Receipt costs are grouped by execution date, while transactions are grouped by submission date. The comparison does not match individual transactions to their complete execution costs.

These figures exclude transaction receipt-conversion costs and do not measure protocol revenue, permanent token burning or holder returns.

Evidence: results 13 and 14.

## What This Means for the Investment Case

The positive evidence is continued transaction activity, growth outside the original leading accounts, and the substantial contribution of accounts observed in consecutive weeks to starting-week transactions.

The main reservations are that broader participation by independent users was not demonstrated, account lifecycle events complicate return measures, and major participants’ roles remain unverified. The selected-account findings also show that growth can include substantial failed execution activity. This does not erase growth elsewhere, but it weakens an interpretation that treats every additional transaction as successful application demand.

The economic conclusion is also incomplete. Higher recorded execution spending establishes one aspect of network use, but does not quantify the resulting benefit to NEAR holders.

My current position is therefore that the adoption-led investment case remains unproven by this dataset. This is a conclusion about the evidence examined, rather than a claim that NEAR has no investment merit.

### Evidence and decision implications

| Finding | Implication for the assessment | Evidence needed next |

|---|---|---|

| Final-week transactions were 3.69% above the first week, while weekly active signing accounts were 7.38% lower | Transaction growth alone does not demonstrate broader participation | Longer-term participation trends with account roles and lifecycle events examined |

| Successful self-deletion appeared among 82.53% of accounts absent after the spike week | The low return share cannot support a straightforward user-churn argument | Cohort comparisons that distinguish lifecycle activity from ongoing application participation |

| The ten busiest signing accounts generated 48.17%–67.76% of weekly transactions | Headline activity is sensitive to a limited set of identifiers | Verification of major account roles and the independent demand they represent |

| Transactions outside the first-week top ten rose 52.50%, while the fixed leaders’ activity fell 19.83% | Activity growth extended beyond the original leaders | Establish how many independent participants and identifiable uses account for that growth |
| tinykoala595.near contributed to growth but had 91.90% failed initial receipts across its observed activity | Additional submissions do not necessarily represent successful application activity | Broader outcome coverage and checks on complete execution chains |
| Recorded receipt execution costs increased 82.73% between the first and final weeks | Execution spending increased, but token-holder value capture remains unquantified | Reconciliation of relevant fee distributions, issuance and other economic flows |

## Connection to NEAR's Economics

Official documentation describes uses for NEAR through execution fees, storage requirements and staking. Product revenues and governance-controlled uses of those revenues provide additional mechanisms to investigate.

The investment question is whether persistent, useful activity creates durable demand for the token or produces other measurable economic effects.

My execution-cost results measure only part of this relationship. They do not establish net issuance, permanent token burning, changes in storage commitments or staked balances, or realised buyback expenditure.

I reviewed the mechanisms and their measurement boundaries in [economic_mechanisms.md](economic_mechanisms.md).

Historical parameters and economic flows would need separate verification before building a supply or valuation model. Current documentation does not prove that every described rule applied unchanged throughout the observation period.

## What Would Change My Assessment?

### Evidence that would strengthen the investment case

- Participation and transaction activity sustained across longer periods, with lifecycle events examined separately.

- Verified applications attracting repeated interaction from participants whose roles are understood.

- Evidence that concentrated infrastructure activity serves persistent, independent demand.
- Growth outside the original leaders that persists across periods and is supported by successful, identifiable application interactions.

- Reconciled economic flows showing how measured usage connects to demand for NEAR, fee allocation and supply changes.

### Evidence that would weaken the investment case

- Repeated headline growth without persistent application participation once account lifecycle activity is examined.

- Declining participation across comparable cohorts with consistent definitions and complete follow-up.

- Activity increasingly dependent on a few participants, accompanied by evidence of weakening independent demand.
- Broader evidence that transaction growth is dominated by failed or temporary activity rather than persistent successful interactions.

- Economic measurements showing that greater activity does not produce the token-demand or supply effects assumed in an investment argument.

These are conditions for further testing. The current analysis has not established all of them.

## How the Research Supports Decisions

### Investors and research analysts

The dashboard helps test whether headline activity growth is accompanied by broader participation, repeat activity and changes in execution spending.

The fixed-account comparison separates growth outside the original leaders from changes within them. The execution checks then show why the quality of that growth needs investigation before it supports an adoption-led investment argument.

### NEAR ecosystem teams

The results show why account growth should be examined alongside lifecycle events and concentration before it is used to evaluate adoption or allocate ecosystem support.

Receiver rankings and account-level growth contributions identify destinations for investigation. The sampled contract errors provide specific diagnostic leads for examining execution friction. They do not establish the size of a network-wide problem or form a verified ranking of application quality or impact.

### Application developers

The project provides a framework for comparing participation and return activity while distinguishing signing identifiers from people.

The diagnostic sample illustrates how receipt-level errors can add context to activity counts. Application-level conclusions would require additional mapping of accounts, relayers, relevant interactions and complete execution chains.

## Data Quality and Remaining Uncertainty

Transaction-hash uniqueness, timestamp coverage, account fields and weekly reconciliations passed the checks performed.

Within the primary period, checked execution outcomes matched exactly one ACTION receipt. Earlier unmatched outcomes during 1 July–22 August remain unresolved.

The spike action analysis found 474 transactions without matching transaction-action records in its selected lookup window. These remain a documented coverage limitation.

The deletion analysis matched all 309,642 selected deletion transactions to exactly one initial receipt outcome. Successful and failed outcomes were examined separately.

The leading-account series includes all eight weeks for the 51 identifiers appearing in at least one weekly top-twenty ranking. The fixed-account and growth-contribution tables reconcile to the network transaction totals.

For the two selected growth accounts, all 1,191,869 transactions matched exactly one initial receipt outcome, with the executor matching the original receiver. This matching does not establish the result of every downstream receipt.

All eighteen diagnostic responses matched the sampled transaction hashes, signing accounts, receipt identifiers, executors and failure statuses. Raw RPC responses and earlier unsuccessful retrieval attempts are preserved in result 26.

These checks support the reported measurements. They do not establish account ownership, deletion motives, permanent loss of an identifier, or population-wide error frequencies.

No price forecast, valuation model or expected token return has been derived from this analysis.

## Reproducibility

The SQL queries, exported results and Python scripts are stored in this repository.

The derived fixed-account comparison and contribution tables can be regenerated from saved exports using analysis/03_fixed_account_growth.py and analysis/04_account_growth_contributions.py. The diagnostic retrieval script preserves validated saved responses and resumes incomplete lookups.

The dashboard can be run using the instructions in [README.md](../README.md). It uses saved exports rather than querying BigQuery when opened.

Detailed checks and investigation notes are recorded in [data_checks.md](data_checks.md).
