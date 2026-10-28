# Decision Priorities

This research helps readers identify which growth claims need closer
examination before they inform investment research, ecosystem support
or application development.

The priorities are based on the eight-week findings. They are qualitative
investigation guides, not automated scores, application rankings or
buy-and-sell signals.

## 1. Check Account Lifecycle Before Interpreting Returns

Among accounts absent after the spike week, 309,280 had successfully
executed receipts containing self-deletion actions during the starting
week. They represented 82.53% of the absent group.

**Implication:** absence is not sufficient evidence of ordinary user
churn or poor application retention.

**Next action:** examine deletion, recreation and account roles before
interpreting acquisition or return rates. Removing deleted accounts
alone would not produce a verified user-retention measure.

Evidence: results 11, 16 and 17.

## 2. Check Execution Quality Behind Growth

One investigated growth contributor, tinykoala595.near, had 715,518 failed
initial receipts: 91.90% of its transactions. Those failures incurred
approximately 211.1629 NEAR in recorded initial-receipt costs.

**Implication:** more submissions and execution spending do not
necessarily mean more successful application interactions.

**Next action:** examine receipt outcomes alongside transaction growth.
Use sampled contract errors as diagnostic leads without extrapolating
their frequencies to the whole account or network. Initial receipt
success does not establish complete downstream success.

Evidence: results 22–27.

## 3. Verify the Roles Behind Concentration

The ten busiest signing accounts generated 48.17%–67.76% of weekly
transactions. Leading-account records included delegated activity
and direct contract calls.

**Implication:** concentrated signing activity does not independently
establish concentration among users or application owners.

**Next action:** use the Account Explorer to inspect trends, destinations
and action patterns. Check attribution sources and preserve unverified
labels. Examine delegated inner actions before drawing conclusions
about the participants being served.

Evidence: results 10, 18–20 and 35.
Sources: [account_attribution.md](account_attribution.md).

## 4. Investigate Growth Beyond the Original Leaders

The first week's ten leading signing accounts recorded a 19.83% decline
between the endpoints. All other accounts combined recorded a 52.50%
increase.

Accounts outside every weekly top-twenty ranking contributed 43.80%
of the outside group's net increase.

**Implication:** the original leaders do not explain all observed growth,
but growth contribution alone does not establish application quality.

**Next action:** investigate other contributors' roles, persistence
and execution outcomes before using their growth to inform ecosystem
support. The untracked aggregate is not a classification of ordinary
users or independent demand.

Evidence: results 18 and 21–24.

## 5. Distinguish Execution Spending From Token Value Capture

Combined recorded execution spending totalled approximately
67,988.91 NEAR: 2,110.82 NEAR in transaction conversion and
65,878.09 NEAR in receipt execution costs.

Combined weekly spending increased 83.13% between the endpoints.
Observed total supply increased approximately 4.936 million NEAR
across the period, while the validator-to-supply comparison remained
incompletely reconciled.

**Implication:** execution provides a measured use for NEAR, but spending
does not establish persistent holdings, net market demand, permanent
burning, protocol revenue or holder returns.

**Next action:** present spending and supply movement separately.
Economic claims should identify the relevant flows and distinguish
documented mechanisms from verified implementation. Do not subtract
recorded spending from supply growth to infer issuance.

The combined spending comparison uses conversion submission dates and
receipt execution dates, rather than matched transaction-chain costs.

Evidence: results 13, 14, 28–34, 36 and 37.

## Who Can Use These Priorities?

| Reader | Decision supported | Evidence boundary |
|---|---|---|
| Investors and research analysts | Identify adoption and economic claims requiring further due diligence. | No valuation, expected return or complete token-value model. |
| NEAR ecosystem teams | Select activity for lifecycle, concentration and execution-quality investigation before support decisions. | No verified ranking of application impact. |
| Application developers | Frame diagnostic questions using activity patterns and execution outcomes. | Selected accounts and sampled errors do not represent every application or user. |

The broader argument is developed in
[investment_thesis.md](investment_thesis.md). Economic mechanisms are
explained in [economic_mechanisms.md](economic_mechanisms.md), with
validation and coverage recorded in [data_checks.md](data_checks.md).