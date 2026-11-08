# Bounded sweat-relayer receipt trace

[Analysis 40](../analysis/40_trace_sweat_relayer.py) implements the two-stage
[priority-4 plan](priority4_attribution_plan.md) for receipt
`2iLefvugZmJmpNn52hcyMBjxcfYGGz5d6R8h4W1dXaDS`.
[Result 94](../results/94_sweat_relayer_bounded_trace_plan.json) freezes the
target, limits, collector sources and input hashes. The two stages are now
completed in result 96; result 97 adds the separately bounded submission-header
check. The commands below document the consumed stages and are not retry
commands. Existing origin/status request builders, JSON-RPC validation,
checksums, capture naming and timestamp checks are reused from analyses 11/15;
their files and the closed withdrawal investigation remain unchanged.

## Two separate manual stages

The first command is:

```bash
.venv/bin/python analysis/40_trace_sweat_relayer.py collect-origin
```

It makes exactly one `EXPERIMENTAL_receipt_to_tx` request with the exact saved
receipt ID and no scan hints. The endpoint is the existing credential-free
`https://archival-rpc.mainnet.near.org`. It does not query transaction status.
The returned hash must decode to 32 bytes, and sender_account_id must equal the
saved receipt signer, `sweat-relayer.near`.

After inspecting the saved origin response, prepare the second request offline:

```bash
.venv/bin/python analysis/40_trace_sweat_relayer.py prepare-status --origin-dir <printed-origin-directory>
```

This verifies saved HTTP/JSON-RPC success, hashes, timestamps, frozen inputs and
request identity, then prints the exact status payload. It uses the returned
transaction hash and sender_account_id, never a receipt ID as a transaction hash.
The second manual stage is separately invoked:

```bash
.venv/bin/python analysis/40_trace_sweat_relayer.py collect-status --origin-dir <printed-origin-directory>
```

It makes one `EXPERIMENTAL_tx_status` request with `wait_until: FINAL`. The
transaction hash/signer and unique target receipt payload/executor must match.
Its target execution block is preserved separately from the source block where
the receipt payload was observed; those dates/hashes are not assumed identical.

There are **at most two live requests**, one reserved slot per stage. A root lock
prevents concurrent writers. Each stage slot is reserved before transport and
remains consumed on error/interruption. Reinvocation cannot silently retry or
create a third request. The status stage requires this trace's validated origin
capture and copies its bytes into `origin_input` without overwriting the original.

## Bounds and evidence retention

- Every request waits 65 seconds before its single attempt. Connection and
  request deadlines are 15 and 60 seconds.
- Each response has an **8 MiB body limit**. On an oversized or incomplete
  response, the received prefix is retained and marked incomplete; it is not
  parsed as valid evidence. At most 16 MiB of new network-response bodies can be
  received across the two attempts. Metadata, the origin snapshot and derived
  reports require additional disk space.
- No redirects, retries, alternative hosts, authentication, scan hints or
  automatic cap changes are used. HTTP/JSON-RPC errors stop and retain bytes.
- Exact request JSON and HTTP request bytes, complete/partial response bytes,
  ordered HTTP headers/status, UTC retrieval timestamps, lengths and SHA-256
  values are saved. Raw monetary strings and array order remain intact.
- All capture files use exclusive creation. Changed checksums, input lineage or
  target fields block interpretation; duplicate identities are rejected rather
  than selected or multiplied through joins.

Captures are separate from all earlier evidence:

```text
results/sweat_relayer_attribution_2026-09-23/
  request_attempts/origin.json | status.json
  <UTC timestamp>_<unique suffix>/
    run.json
    request.http
    priority4-sweat-origin.request.json | priority4-sweat-status.request.json
    priority4-sweat-origin.response.body | priority4-sweat-status.response.body
    priority4-sweat-origin.metadata.json | priority4-sweat-status.metadata.json
    validation.json | stopped.json
    origin_input/                         # status stage only
```

The one selected trace remains small and is not loaded by the dashboard. It does
not resume Neardata bulk collection or alter its preserved plans/captures.

## Offline interpretation and transaction coverage

```bash
.venv/bin/python analysis/40_trace_sweat_relayer.py validate --run-dir <printed-stage-directory>
```

Default output is stdout. `--output <unused-file>` saves a new derived report
exclusively; existing files are never overwritten. No source request occurs.

The interpreter reports network signer/public key and transaction receiver,
receipt predecessor/receiver/action signer, ordered calls and raw arguments,
execution blocks/executors/status/logs, unique parent paths and callback data
dependencies. It reports a delegate sender only from an explicit returned
`Delegate`/SignedDelegate payload, retaining sender_id, receiver_id, public key,
nonce, max_block_height, signature and ordered inner actions. Unsupported
delegate encodings remain unresolved. A different predecessor alone never
establishes delegation. A delegate in another receipt branch is not automatically
the selected target's actor. Declared key authority is not beneficial ownership
or a distinct human/user count.

Coverage distinguishes returned receipt payloads, returned receipt outcomes,
emitted child identities, known data receipts, missing outcomes/payloads,
ambiguous links, disconnected records and callback producers. A same-account
initial payload reconstructed from transaction actions is explicitly labeled;
it is not counted as a returned payload. Known Data receipts do not require an
action execution outcome. Missing or ambiguous callback dependencies stay
unresolved. Receipt-level parent paths do not identify a unique generating
action when a parent contains multiple actions.

`FINAL`, top-level success and SUCCESS_RECEIPT_ID are not treated as complete
business settlement. Observed graph coverage and whether all returned receipts
succeeded are separate fields; independent historical ingestion completeness
remains unavailable. Exact recorded token charges are not actual supply burn,
revenue or proof of the economic fee funder. Deposits and attached gas are not
execution-spending measurements.

At preparation, the target had **one saved payload and no matching outcome
in that block's observed subset**. Result 96 now supplies the validated origin,
explicit Delegate action and successful returned transaction graph. Analysis 40
does not make a third request. The separate analysis-41 timestamp check preserves
the two original captures and result 96 unchanged.

## Population coverage and reusable controls

The saved eight-week population is **13,704,363 signed transactions** for
sweat-relayer.near. A single trace would be **0.0000072969462353%** of that
observed population only after its submission-window membership is established.
The **13,246,938 DELEGATE_ACTION transactions** form a different denominator:
one trace is **0.0000075489143227%** only if the network transaction actually
contains a delegate action and belongs to the same window. A delegate observed
only in a later receipt does not qualify for that transaction-action denominator.

There is now **one identity-validated Sweat transaction** in this trace. Result
96 retains its original conditional window-membership fields: the saved pilot
headers did not include the submission header. Result 97 adds a single separate
header lookup, matching both the transaction outcome's exact block hash and
the saved canonical successor's predecessor. Submission occurred at
2026-09-23T07:11:24.906615725Z, confirming the original-window membership and
both fractions above. The receipt's container date was not substituted for
submission time. This purposively selected trace is never representative.

[Result 95](../results/95_sweat_trace_tinykoala_controls.json) runs the same
interpreter offline on the **18 existing tinykoala failure controls**. Each has
three returned payloads, three receipt outcomes and no missing emitted action
outcome; each contains one failed receipt plus two successful receipts. These
controls demonstrate that a covered graph may still contain failure. They are
0.0025156599834% of the saved 715,518 failed tinykoala initial receipts, not new
sweat-relayer coverage or population-wide error frequencies.

Focused checks:

```bash
.venv/bin/python -m unittest discover -s tests -p test_sweat_attribution_trace.py -v
.venv/bin/python analysis/40_trace_sweat_relayer.py controls
```

The origin, returned transaction/receipt details, parent/callback linkage and
submission timestamp are now available for this one case. Ownership, service
role, economic funding, independent historical ingestion completeness and
population representativeness remain unresolved. See the
[consolidation](priority4_attribution_plan.md) for exact coverage and offline
reproduction; the original two request slots remain consumed.
