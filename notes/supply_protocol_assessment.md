# Supply status and bounded configuration checks — 7 November 2026

The 21–27 September epoch walk is complete within observed-response scope:
23 application epochs, 4786–4808, with the saved opening sentinel reached.
Its final validation report reproduces byte-for-byte. The 21 additional
configuration responses have also been captured and validated, completing
active application-epoch configuration coverage together with the reused A/B
evidence. No further configuration collection is needed for this week.

## Active historical configuration: why 21 direct checks

The pinned historical implementation is nearcore 2.13.3, commit
`5af9ca74631e6cf0dae33e77d1a632e94d2952ce`.

- [`GetProtocolConfig`](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/client/src/view_client_actor.rs#L1629)
  resolves the requested block header and asks for that header's epoch configuration.
- [`get_protocol_config`](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/chain/src/runtime/mod.rs#L1583)
  obtains the epoch's active protocol version, actual shard layout, epoch settings
  and runtime configuration. It does not substitute the producer's advertised
  `latest_protocol_version`.
- The [version-selection implementation](https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/chain/epoch-manager/src/lib.rs#L544)
  uses stake-weighted epoch votes and schedules a later epoch version. This code
  and two equal sampled versions do not establish a complete intervening
  activation/configuration history.
- The official [2.14 rollout tracker](https://github.com/near/devex/issues/63)
  described a mainnet PV87/PV88 schedule for November, updated 13 October 2026.
  This is useful dated context, not a canonical record of every active September
  configuration. A release or scheduled activation does not replace execution
  evidence. No official retained activation census covering all target epochs
  is established by the reviewed sources.

A complete authoritative activation history could cover multiple epochs if it
bound every change to canonical epoch/block identities, established the
unchanged intervals and covered all economically relevant parameters. Such
evidence would remove the need for repeated identical checks. In its absence,
the direct verification used one request for each of the 21 application epochs
that lacked a saved configuration. The existing A/B protocol-86 responses were
reused. No monotonic-version assumption or advertised-version inference was
used to interpolate the other epochs.

The documented method is
[`EXPERIMENTAL_protocol_config`](https://docs.near.org/api/rpc/protocol), with
`params.block_id` equal to each saved application block's exact hash. The response
does not echo that block hash; request bytes, RPC ID, saved header linkage and
the method contract bind the response. Raw bytes and hashes remain the provenance
source. The collector checks mainnet, integer active version 86, the actual
configured shard IDs against the saved manifest, treasury identity and reviewed
runtime/economic fields against A/B. Unreviewed versions or configuration changes
stop collection and remain available for inspection rather than being accepted
as zero or extrapolated.

These checks establish application-path applicability. They do not recompute
rewards from the application epoch's inflation rate, treasury fraction or epoch
length: rewards were earned earlier, and the independently recorded full map is
the monetary input. Original integer strings and exact Decimal configuration
numbers are preserved without float conversion. Gross issuance including
subsidies remains a separate unavailable quantity.

## Completed configuration capture and offline validation

The original request list, hashes and limits remain in
`results/70_supply_protocol_configuration_plan.json`. The completed manual
capture is saved at:

```text
results/supply_protocol_checks_2026-09-21_to_2026-09-27/20261107T115319Z_136187c69e9d/
```

All 21 planned responses have HTTP 200, complete transport, matching JSON-RPC IDs,
valid byte lengths and SHA-256 hashes. Exact block-hash request parameters match
the saved application headers. Each response reports active protocol 86 and
matches the reviewed A/B economic/runtime fields; configured shard IDs agree
with the corresponding header manifest. The saved raw responses, their array
order and Decimal settings remain unchanged. This is RPC-derived configuration
evidence, not a server-binary attestation or independent chain proof.

Together with A/B, all 23 application epochs now have configuration coverage.
Every returned reward-map amount is validated as an integer string, all boundary
monetary identities close with zero-yocto discrepancy, and the completed report
reproduces the capture's `validation.json` byte-for-byte. A durable derived copy
is saved as `results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json`.
The earlier plan (result 70) and pre-collection status (result 71) are preserved
as historical artifacts; result 72 records the completed checks.

The collector used the existing public archival endpoint with 65-second spacing,
15-second connection and 60-second request timeouts, without retries or fallback.
Only configurations were newly collected; A/B, headers and reward maps were
reused. No bulk-header access or full-week debit coverage follows from these
configuration responses.

Offline commands:

```bash
.venv/bin/python analysis/28_supply_protocol_checks.py validate \
  --run-dir results/supply_protocol_checks_2026-09-21_to_2026-09-27/20261107T115319Z_136187c69e9d
.venv/bin/python -m unittest discover -s tests -p test_supply_protocol_checks.py -v
```

These commands are offline. Validation defaults to stdout; explicit `--output`
refuses overwrites. Synthetic test transports cannot make real HTTPS connections.
The `plan` and `status` commands reproduce the original pre-collection baseline;
the completed `validate` command above reproduces result 72.

## Practical bulk-header dependency: no further source search

The existing [bulk-source assessment](supply_bulk_source_feasibility.md) and
[actual schema validation](supply_schema_inventory_validation.md) are sufficient
to identify the dependency. No object listing, provider contact, infrastructure
provisioning or repeated source search is needed for this status decision.

| Candidate | Established | Missing or unsuitable |
| --- | --- | --- |
| Verified BigQuery `blocks`/`chunks` | Identity/predecessor fields and current schema are saved in result 64. | No inclusion heights, chunk mask or `balance_burnt`; supply is FLOAT64. An exact independent debit extraction cannot be written against absent fields. |
| Documented `gs://near-lakehouse-public/mainnet/avro/block_chunks/<processed-hour>/` | Published notebook documents the path and requester-pays setup. | Exported selection omits inclusion/debit fields and starts from a chunk join. Target retention, read/list permissions, requester-pays project, monetary precision and actual charges are unverified. Access alone would not make these selected fields sufficient. |
| Retained raw headers from an existing archive | Saved RPC responses prove the required exact strings and manifests exist at sampled blocks. | No accessible lossless bulk path, granted permissions, retention statement or cost is established. A local statistics reader is not a public export service. |

The exact next dependency is a read-only export or existing object path from an
already retained archive, with permission and cost information, for A's epoch:
**216877934 through 216921133**, plus the already saved preceding baseline.
The interval has 43,200 numerical height slots; produced canonical block count
must be measured using predecessor links, not assumed from that span. At the
saved ten-shard layout this is at most 432,000 manifest entries. Byte volume,
compression and access/processing charges are not established. No zero-cost
claim follows from those counts.

Required fields are inclusion block hash/height/UTC timestamp and predecessor,
epoch ID, ordered shard/chunk identities, creation/inclusion heights, chunk mask
and exact integer `balance_burnt` strings. A sample must reproduce saved A and
B-parent controls before extending to every canonical inclusion block in that
epoch. Sum only newly included headers; retain coverage diagnostics and null
incomplete totals. This would measure a net debit, not separately gross burn
and subsidy. Schema, lineage, retained coverage, read permissions and bounded
cost are the acceptance gates. Until supplied, the bulk pilot is blocked.
Individual-block scans are excluded from this pilot.

## Current supply status and model use

Result 72 reproduces this status with exact integer arithmetic. NEAR figures
below retain source precision; the boundary-debit total covers only 23 blocks.

| Measurement, 21–27 September | NEAR | Status |
| --- | ---: | --- |
| Exact endpoint supply movement | +611,555.974235517852937718656646 | Captured endpoints; final canonical daily-close coverage remains an observed-source qualification. |
| Independently recorded reward maps, 23 applications | 618,436.074970164323861118656646 | Exact full-map sum and offset alignment; all 23 application configurations checked. |
| Protocol-validated epoch reward issuance, 23 applications | 618,436.074970164323861118656646 | This week only; excludes separately unavailable subsidies and does not establish full-window issuance. |
| Independently observed boundary header net debits | 0.104122811923337500000000 | 23 sampled application headers; all boundary arithmetic discrepancies are zero yoctoNEAR. |
| Implied weekly net debit | 6,880.100734646470923400000000 | Protocol-validated epoch reward minting minus exact supply movement; not an independent debit or actual burn measurement. |
| Full-week independent net debit | Unavailable | Intervening inclusion manifests are missing. |
| Gross actual supply burn and subsidies | Both unavailable | Neither is zero; net debit cannot separate them. |

Supported model calculations are observed weekly net total-supply growth
`delta_supply / opening_supply` and mechanical changes in the share represented
by a hypothetical fixed token balance, explicitly conditional on holding that
balance constant. These are supply calculations, not holder investment returns.
The completed configuration checks support a weekly epoch-reward issuance rate
calculated from epoch reward minting divided by opening supply; it excludes any
unmeasured subsidy issuance and is not automatically an annual forecast.

The reward-map subtraction can enter only a labelled conditional sensitivity,
not a verified fee-offset, gross-burn rate or reconciled supply identity. Boundary
debits cannot be scaled to the week without a sampling design and full coverage.
Staking APR requires eligible stake, time, reward allocation and commissions;
these maps divided by total supply do not supply it. Revenue/buyback yields,
holder cash flows, net purchases, fair value and expected returns remain
unsupported. Spending and the closed withdrawal trace cannot fill those inputs.

The [research plan](research_plan.md#remaining-research-tasks-and-completion-criteria)
records the remaining technical tasks, dependencies and completion criteria.
