"""Rebuild dashboard-derived evidence from saved exports, without source requests.

Legacy builders run in an isolated temporary copy. Existing repository outputs
must match byte-for-byte; they are never overwritten. Missing named derived
outputs can be created exclusively. --check requires every output to exist.
Historical validation/provenance manifests remain immutable inputs.
"""

import argparse
import contextlib
import importlib.util
import io
import json
import runpy
import shutil
import sys
import tempfile
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"
EXTENDED = "2026-07-06_to_2026-10-18"
LEGACY = (
    ("01_weekly_activity_baseline.py", f"09_weekly_activity_baseline_{PERIOD}.csv"),
    ("02_weekly_execution_costs.py", f"14_weekly_growth_and_costs_{PERIOD}.csv"),
    ("03_fixed_account_growth.py", f"21_fixed_account_growth_{PERIOD}.csv"),
    ("04_account_growth_contributions.py", f"22_account_growth_contributions_{PERIOD}.csv"),
    ("06_weekly_economic_comparison.py", f"34_weekly_economic_comparison_{PERIOD}.csv"),
    ("07_account_profiles.py", f"35_account_profiles_{PERIOD}.json"),
    ("08_execution_spending.py", f"37_weekly_execution_spending_{PERIOD}.csv"),
    ("09_extended_activity_comparison.py", f"39_extended_activity_comparison_{EXTENDED}.csv"))
VALIDATION = RESULTS / "61_persistent_activity_shared_week_validation.json"
PUBLISHED = RESULTS / "62_integrated_research_evidence.json"


def module(filename):
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
        raise RuntimeError("Network operations are disabled during the saved-input rebuild")


def legacy_outputs():
    generated = {}
    with tempfile.TemporaryDirectory(prefix="near-saved-rebuild-") as directory:
        temporary = Path(directory)
        (temporary / "analysis").mkdir()
        (temporary / "results").mkdir()
        for path in RESULTS.iterdir():
            if path.is_file():
                shutil.copyfile(path, temporary / "results" / path.name)
        before = {p.name: p.read_bytes() for p in (temporary / "results").iterdir()}
        for script, output in LEGACY:
            target = temporary / "analysis" / script
            shutil.copyfile(ROOT / "analysis" / script, target)
            with contextlib.redirect_stdout(io.StringIO()):
                runpy.run_path(str(target), run_name="__main__")
            generated[RESULTS / output] = (temporary / "results" / output).read_bytes()
        names = {name for _, name in LEGACY}
        if any(p.read_bytes() != before[p.name] for p in (temporary / "results").iterdir() if p.name not in names):
            raise ValueError("A legacy builder changed an input in the isolated copy")
    return generated


def published(shared):
    load = lambda name: json.loads((RESULTS / name).read_bytes())
    previous = load("59_persistent_activity_initial_receipt_validation.json")
    persistence = load("57_persistent_activity_pilot_validation.json")
    supply = load(f"46_observational_supply_comparison_{PERIOD}.json")
    canonical = load("43_canonical_rpc_bigquery_comparison_2026-09-23.json")
    witness = load("45_bitwise_validator_update_witness_2026-09-23.json")
    withdrawal = load("54_internal_credit_trace_consolidation_2026-09-23.json")
    discovery = load("48_frontend_wallet_native_transfers_decoded_2026-09-23.json")
    validator = module("22_validate_shared_week_receipts.py")
    validator.b.require(shared["publication_ready"], "Shared-week coverage blocks the execution claims")
    a, repeated, z = shared["populations"]
    growth_rows = validator.b.read_csv(RESULTS / f"39_extended_activity_comparison_{EXTENDED}.csv")
    growth = {row["metric"]: row for row in growth_rows}
    pct = lambda value: f"{Decimal(value):.2f}"
    opening = [
        {"question": "What grew?", "answer": f"First-four-week versus final-four-week averages increased {pct(growth['average_weekly_transactions']['relative_change_pct'])}% for transactions and {pct(growth['average_weekly_active_signing_accounts']['relative_change_pct'])}% for active signing accounts. Fifteen-week endpoints instead declined 10.63% and 24.65%. The final four weeks include the account spike, while active days per account-week fell 52.59%. Growth depends on the baseline."},
        {"question": "How much persisted?", "answer": "Of the accounts active in the 10 and 17 August starting weeks, 47.41% and 46.18% returned in the exact +8 week; 37.48% and 37.83% were active at all three +1/+4/+8 checkpoints. This is checkpoint persistence, not continuous weekly activity or verified user retention. The top ten returners produced 73.98% and 75.12% of their +8 transactions."},
        {"question": "What executed successfully?", "answer": f"During 5–11 October, {pct(a['initial_success_share_pct'])}% of the August +8 group's initial receipts and {pct(z['initial_success_share_pct'])}% of the September +1 group's initial receipts succeeded. Observed initial-receipt links and costs were fully assessed. The groups share {shared['overlap']['august_and_september_transactions']:,} transactions; the rates are descriptive, not a causal comparison. Descendant outcomes remain unavailable."},
        {"question": "What economic demand or value capture is demonstrated?", "answer": "Recorded NEAR-denominated conversion and receipt execution spending demonstrates measured execution use. It does not establish fresh purchases, persistent holdings, net market demand or holder value capture. The supply comparison retains a +16,599.5144 NEAR residual; a traced 1,252.862790 NEAR withdrawal has unverified revenue origin. Independent issuance and actual supply burn remain unavailable. No holder cash-flow valuation follows."}]
    paths = [VALIDATION, RESULTS / "59_persistent_activity_initial_receipt_validation.json",
             RESULTS / "57_persistent_activity_pilot_validation.json", RESULTS / f"46_observational_supply_comparison_{PERIOD}.json",
             RESULTS / "43_canonical_rpc_bigquery_comparison_2026-09-23.json", RESULTS / "45_bitwise_validator_update_witness_2026-09-23.json",
             RESULTS / "54_internal_credit_trace_consolidation_2026-09-23.json", RESULTS / "48_frontend_wallet_native_transfers_decoded_2026-09-23.json",
             RESULTS / f"39_extended_activity_comparison_{EXTENDED}.csv", RESULTS / f"37_weekly_execution_spending_{PERIOD}.csv"]
    data = {"schema_version": 1, "measurement_phase": shared["measurement_phase"], "network": "NEAR mainnet",
        "opening": opening, "growth_comparison": growth_rows,
        "cohorts": persistence["cohort_summary"], "checkpoints": persistence["checkpoint_metrics"],
        "shared_week": {"submission_week": "2026-10-05", "lookup_end": "2026-10-17", "populations": shared["populations"], "overlap": shared["overlap"]},
        "october12_pilot": {"submission_week": "2026-10-12", "lookup_end": "2026-10-24", "populations": previous["populations"]},
        "supply": {"period": supply["period"], "weekly": supply["weekly"], "cancellation": supply["cancellation"],
            "saved_arithmetic_checks": supply["saved_arithmetic_checks"],
            "canonical_comparison": {"blocks_compared": 2, "additional_validator_updates": canonical["additional_validator_population"]["update_records_across_AB"],
                "distinct_additional_accounts": canonical["additional_validator_population"]["distinct_accounts_across_AB"],
                "blank_chunk_validator_updates_confirmed": sum(v["counts"]["bq_blank_chunk_validator_records"] for v in canonical["blocks"].values()),
                "witness_change_near": witness["change"]["combined_near"], "witness_change_yocto": witness["change"]["combined_yocto"],
                "hypothesis": "Ingestion collisions involving blank chunks and reused indices remain unconfirmed. Two blocks do not establish a dataset-wide discrepancy.",
                "no_adjustment": "Recovered updates cannot simply be added to the original daily total: later predecessor comparisons may already contain omitted changes."}},
        "withdrawal": {"discovery_date": "2026-09-23", **discovery["summary"],
            "traced_withdrawal_near": withdrawal["subsequent_withdrawal_comparison"]["amount_near"],
            "prior_credit_mechanism": withdrawal["credit_trace"]["mechanism"], "revenue_origin": None,
            "mechanism": "Successful signed internal transfer followed by verified native withdrawal after unwrapping.",
            "limits": "One day's native transfer discovery is not a revenue or buyback ledger. Internal account role, prior funding, opening balances and commingled-balance allocation remain unresolved. Internal mt_burn is not native supply destruction."},
        "limitations": shared["limitations"], "unavailable": shared["unavailable"],
        "sources": {str(path.relative_to(ROOT)): validator.p.prior.identity(path) for path in paths},
        "rebuild": "python3 -B analysis/23_rebuild_published_results.py"}
    # This manifest tracks the builder, not dashboard/notes, avoiding output cycles.
    data["builder"] = {"path": str(Path(__file__).relative_to(ROOT)), **validator.p.prior.identity(Path(__file__))}
    return validator.b.json_bytes(data)


def rebuild(check=False):
    shared_module = module("22_validate_shared_week_receipts.py")
    outputs = legacy_outputs()
    supply = module("13_consolidate_supply_evidence.py")
    outputs.update({supply.witness.COMPARISON: supply.capture.json_bytes(supply.comparison_report()),
                    supply.WITNESS_SUMMARY: supply.capture.json_bytes(supply.witness_report()),
                    supply.SUPPLY_SUMMARY: supply.capture.json_bytes(supply.supply_report())})
    for script, target in (("14_decode_frontend_native_transfers.py", "48_frontend_wallet_native_transfers_decoded_2026-09-23.json"),
                           ("16_internal_credit_evidence.py", "51_internal_credit_validation_2026-09-23.json"),
                           ("18_consolidate_internal_credit_trace.py", "54_internal_credit_trace_consolidation_2026-09-23.json")):
        producer = module(script)
        outputs[RESULTS / target] = shared_module.b.json_bytes(producer.report())
    planner = shared_module.b
    outputs[RESULTS / "55_persistent_activity_plan_and_saved_baselines.json"] = planner.json_bytes(planner.plan())
    shared = shared_module.report()
    outputs[VALIDATION] = planner.json_bytes(shared)
    # Validate every existing output before writing any missing one.
    for path, raw in outputs.items():
        if path.exists():
            planner.require(path.read_bytes() == raw, f"Generated-file mismatch: {path.relative_to(ROOT)}")
        elif check:
            raise ValueError(f"Missing generated artifact: {path.relative_to(ROOT)}")
    created = []
    for path, raw in outputs.items():
        if not path.exists():
            with path.open("xb") as handle:
                handle.write(raw)
            created.append(str(path.relative_to(ROOT)))
    raw = published(shared)
    if PUBLISHED.exists():
        planner.require(PUBLISHED.read_bytes() == raw, "Generated-file mismatch: results/62_integrated_research_evidence.json")
    elif check:
        raise ValueError("Missing generated artifact: results/62_integrated_research_evidence.json")
    else:
        with PUBLISHED.open("xb") as handle:
            handle.write(raw)
        created.append(str(PUBLISHED.relative_to(ROOT)))
    return {"derived_artifacts_verified": len(outputs)+1, "created": created,
            "historical_manifest_note": "Results 57 and 59 are validated through the recorded SQL fingerprints; their proven trailing-whitespace differences remain recorded in results 59 and 61. Immutable historical exports are not rewritten.",
            "source_requests": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify all generated files without writing")
    args = parser.parse_args(argv)
    sys.addaudithook(deny_network)
    try:
        print(json.dumps(rebuild(args.check), indent=2))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
        print(f"Saved-input rebuild stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
