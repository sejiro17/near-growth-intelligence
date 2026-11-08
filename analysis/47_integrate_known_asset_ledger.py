"""Offline current ledger projection; frozen native and asset evidence unchanged."""

import argparse
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("known_asset", ROOT/"analysis/46_known_asset_wallet_coverage.py")
asset = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(asset)
c = asset.c
OUTPUT = ROOT/"results/104_wallet_ledger_with_known_asset_reconciliation.json"
INVENTORY = ROOT/"results/102_known_asset_wallet_coverage_2026-08-24_to_2026-10-18.json"
COMPARISON = ROOT/"results/103_known_internal_asset_stock_comparison_2026-08-24_to_2026-10-18.json"


def report():
    c.require(INVENTORY.read_bytes() == c.json_bytes(asset.report()), "Result 102 does not reproduce")
    comparison = asset.validate()
    c.require(COMPARISON.read_bytes() == c.json_bytes(comparison), "Result 103 does not reproduce")
    native = c.decode(asset.SOURCE.read_bytes())
    opening, closing = (comparison["states"][b] for b in ("opening", "closing"))
    c.require(opening["owner"] == closing["owner"] == asset.OWNER
              and opening["asset_id"] == closing["asset_id"] == asset.ASSET, "Owner/asset mismatch")
    movement = asset.inventory(native)["observed_movements"]
    c.require(len(movement) == 1 and movement[0]["old_owner_id"] == asset.OWNER, "Selected event scope changed")
    row = {"classification": "ONE_KNOWN_OWNER_ASSET_BALANCE_RECONCILIATION",
           "owner": asset.OWNER, "contract": asset.CONTRACT, "asset_id": asset.ASSET,
           "unit": "internal asset base units; no display conversion assumed",
           "opening": opening, "closing": closing, "selected_movement": movement[0],
           **{k: comparison[k] for k in ("stock_change_base_units", "selected_observed_internal_flow_net_base_units",
                                        "stock_change_minus_selected_flow_base_units", "boundary_qualification")},
           "complete_flow_history": None, "recipient_is_verified_buyback_wallet_alias": None,
           "economic_classification": "UNCLASSIFIED_INTERNAL_ASSET_TRANSFER",
           "limitation": "One known owner–asset stock reconciliation. Zero residual does not rule out offsetting movements or establish complete asset coverage, revenue origin or purchases."}
    return {"schema_version": 1, "window": native["window"],
            "native_ledger_source": str(asset.SOURCE.relative_to(ROOT)),
            "native_wallets": native["native_wallets"], "native_group": native["native_group"],
            "native_coverage": native["native_coverage"],
            "known_owner_asset_reconciliations": [row],
            "coverage": {"native_wallets": 3, "native_boundary_states": 6,
                         "known_owner_asset_pairs_reconciled": 1, "known_asset_boundary_states": 2,
                         "complete_asset_pair_denominator": None, "complete_multi_asset_coverage": None,
                         "weekly_multi_asset_stock_reconciliation": None},
            "closed_withdrawal_provenance": native["closed_withdrawal_provenance"],
            "native_residual_allocation": "UNCHANGED_UNALLOCATED_NO_RESIDUAL_DRIVEN_COLLECTION",
            "verified_revenue": None, "verified_purchases": None, "actual_native_supply_burn": None,
            "model_calibration": "Context only: neither native inflows nor the internal balance decrease measures economic fee-bearing activity, capture, purchases or destruction. No scenario default is recalibrated.",
            "sources": [asset.source(p) for p in (asset.SOURCE, INVENTORY, COMPARISON, Path(__file__))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    def deny(event, _):
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto", "subprocess.Popen", "os.system"}:
            raise RuntimeError("Source access disabled in offline ledger integration")
    sys.addaudithook(deny)
    raw = c.json_bytes(report())
    if args.output is None:
        sys.stdout.write(raw.decode())
    elif args.check:
        c.require(args.output.read_bytes() == raw, "Current ledger does not reproduce")
        print("Current ledger reproduced offline; source requests: 0")
    else:
        c.write_new(args.output, raw)


if __name__ == "__main__":
    main()
