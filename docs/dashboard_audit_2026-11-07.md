# Dashboard audit — 7 November 2026

Scope: all seven dashboard tabs, the opening narrative, shared footer, conditional
expanders, selectors and named downloads. Evidence: saved results 10–62, the
investment thesis, source CSVs and profile JSON. The separate supply pilot remains
pending research and is not folded into the published eight-week results.

## Prioritized findings

| Priority | Type | Evidence | Correction |
| --- | --- | --- | --- |
| P1 | Download precision | Pandas reserialization changed 45 cells in the economic CSV download, including `0.0002221269850580216056787899502` becoming `0.0002221269850580216`; null markers also changed. Activity and contribution downloads changed 24 and 55 cells respectively, including formatting-only differences. | Named whole-source CSV downloads now return original bytes. Selected-account cost downloads filter original strings without float parsing. |
| P1 | Research status | Decision priorities stated that the bounded supply investigation was closed. Reconciliation is ongoing, while the published persistence checkpoint and bounded withdrawal trace are complete. | Corrected the status banner, README and thesis scope. Full-window issuance remains unavailable; a separate epoch pilot does not establish full-window coverage. |
| P2 | Execution scope | The growth-account heading asked whether accounts executed successfully; the selected evidence covers initial receipts. The README's success summary omitted the measured failure rates. | Heading now explicitly says initial receipts; README reports the 82.35%–92.99% success range for the three overlapping exact-return pilots, without claiming complete-chain success. |
| P2 | Discovery scope | The withdrawal section described native transfers but did not explicitly state exclusions there. | Added token-transfer/internal-Verifier-balance exclusions beside the finding. Revenue origin, buybacks and actual native burn remain unverified. |
| P2 | Readability | Unconfigured count columns lacked thousands separators; core monetary summaries showed 8–24 decimal places. The persistence summary combined ten columns of outcomes and spending. | Added display-only numeric/date configuration, separated outcome and spending tables, and retained exact values in technical expanders and evidence downloads. Numeric sorting and underlying unrounded values are preserved. |
| P2 | Narrative density | Four detailed opening answers preceded the dashboard. Supply and withdrawal warnings mixed conclusions, exact arithmetic and diagnostics. | Added short conclusions with adjacent qualifications; retained the full opening evidence, precise amounts and methodological detail in expanders. |
| P3 | Accessibility and documentation | Plotly charts lacked accessible names. README described dashboard testing as exclusively in-process despite the console-launch regression. | Added chart descriptions and documented both test paths. |

## Coverage and consistency

The original default render contained seven tabs, 14 expanders, 21 tables,
18 charts, seven selectors and seven named downloads. The revised default render
contains 17 expanders, 23 tables and eight named downloads; tab and chart counts
are unchanged. Additional action-detail expanders appear for relevant accounts.

The selector audit exercises:

- All 51 tracked signing accounts in Growth drivers, checking chart vectors
  against result 18.
- Both selected growth accounts' initial outcomes.
- All eight receiver weeks, checking receiver transaction counts against result 12.
- All three audiences and five investigation priorities.
- All five account profiles across all eight weeks, checking destination tables
  against result 35.

Default chart data remains unchanged across all 18 charts. The saved-input rebuild
verifies all 17 published derived artifacts. Counts, checkpoint denominators,
overlapping memberships, submission/execution timing, tails and unavailable
follow-ups agree with the validated evidence. No new numerical contradiction was
found. README and thesis relative links resolve to existing files.

All eight named download payloads are checked. Whole-source CSVs and integrated
evidence JSON match saved bytes; filtered cost exports preserve every original
cell string; selected-profile JSON matches its source object. Decision-priority
CSV contains the five displayed research interpretations. Table-toolbar exports
are presentation datasets, not guaranteed original source files.

## Checks

```bash
.venv/bin/python -B analysis/23_rebuild_published_results.py --check
.venv/bin/python -B -m unittest discover -s tests -v
git diff --check
```

The interaction tests disable source network connections. The separate startup
regression launches the actual Streamlit console executable in a temporary
directory with `PYTHONPATH` and `PYTHONHOME` removed, then checks the opening and
all tab bodies over the local Streamlit protocol.

Validation passed: 124 tests, all 17 derived-artifact reconciliation checks,
changed-Python parsing and whitespace checks. The final download assertions were
also rerun successfully after strengthening the payload comparisons.

Raw exports, provenance, canonical captures, pending supply work and the
submission tag are preserved. The audit does not complete the revenue/buyback
ledger, issuance/burn reconciliation, broad relayer attribution or conditional
investment model.

## Unverified presentation checks

Desktop and narrow-screen browser rendering, pixel-level table/chart clipping,
actual tab/expander browser clicks and real browser download behavior have not
been visually verified. A saved browser permission setting blocked the local
dashboard URL despite session approval. Offline rendered-element tests do not
establish responsive layout quality. Visual sign-off remains outstanding;
publication must not be described as browser-verified. The audit itself did not
change the public deployment.
Current external attribution-site reachability was not rechecked; profile review
dates and historical-attribution qualifications are retained.
