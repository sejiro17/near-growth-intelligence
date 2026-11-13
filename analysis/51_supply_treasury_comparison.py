"""Same-block comparison of three-wallet native balances/flows with eight-week issuance bounds.

Offline only. Inputs are the validated results 80 (three-wallet native ledger) and
107 (protocol-bounded issuance). Both are first reproduced from their own saved
evidence; the comparison then requires identical opening and closing block hashes
and heights, re-checks every wallet stock-flow identity and the cancellation of
between-wallet transfers, and expresses each wallet quantity as an exact fraction
of the issuance bounds.

Interpretation limits (also written into result 108):
* Wallet inflows are unclassified; none is classified as revenue, a buyback, profit
  or a holder return.
* A custodial balance remains part of total supply; nothing here measures
  circulating supply.
* Three named wallets on the native NEAR layer are not the complete treasury
  system; internal Intents balances, other tokens and other accounts are outside it.

Commands
--------
report [--check]   Build result 108 (exclusive create) or verify it byte-for-byte.
"""

import argparse
import importlib.util
import json
import sys
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "results/108_supply_treasury_same_block_comparison_2026-08-24_to_2026-10-18.json"
YOCTO = 10**24
SCOPES = ("EXTERNAL_COUNTERPARTY", "BETWEEN_SELECTED_WALLETS", "SELF_MOVEMENT")


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def require(condition, message):
    if not condition:
        raise ValueError(message)


def near(value):
    sign = "-" if value < 0 else ""
    whole, fraction = divmod(abs(value), YOCTO)
    return f"{sign}{whole}.{fraction:024d}"


def percent(numerator, denominator, digits=4):
    """Exact fraction plus a half-up display percentage; display never feeds arithmetic."""
    value = Fraction(numerator, denominator)
    scaled = value * 100 * 10**digits
    rounded = (scaled.numerator * 2 + scaled.denominator) // (2 * scaled.denominator)
    sign = "-" if rounded < 0 else ""
    whole, fraction = divmod(abs(rounded), 10**digits)
    return {"fraction_exact": f"{value.numerator}/{value.denominator}", "percent_display": f"{sign}{whole}.{fraction:0{digits}d}"}


def share_of_bounds(amount, lower, upper):
    """amount / issuance. Dividing by the upper bound gives the smaller share."""
    return {"against_issuance_upper_bound": percent(amount, upper),
            "against_issuance_lower_bound": percent(amount, lower)}


def load_inputs():
    # The unified rebuild's loader rebinds result 80's recorded capture directory so
    # the ledger reproduces from any checkout location; file hashes are still checked.
    rebuild = module("rebuild_for_108", "44_rebuild_integrated_research.py")
    ledger_module = rebuild.module("33_consolidate_three_wallet_ledger.py")
    bounds_module = module("bounds_for_108", "50_eight_week_issuance_bounds.py")
    paths = {"ledger": next((ROOT / "results").glob("80_*.json")), "bounds": bounds_module.RESULT}
    ledger_bytes, bounds_bytes = paths["ledger"].read_bytes(), paths["bounds"].read_bytes()
    require(ledger_bytes == ledger_module.c.json_bytes(ledger_module.report()), "Result 80 no longer reproduces")
    require(bounds_bytes == bounds_module.cap.json_bytes(bounds_module.validate(bounds_module.single_capture())),
            "Result 107 no longer reproduces")
    return json.loads(ledger_bytes), json.loads(bounds_bytes), paths, bounds_module


def same_blocks(ledger, bounds):
    opening, closing = bounds["anchors"][0], bounds["anchors"][-1]
    require(opening["date"] == "2026-08-23" and closing["date"] == "2026-10-18", "Unexpected issuance anchors")
    for wallet in ledger["native_wallets"]:
        for side, anchor in (("opening", opening), ("closing", closing)):
            state = wallet[side]
            require(state["block_hash"] == anchor["anchor_hash"] and state["block_height"] == anchor["anchor_height"],
                    f"{wallet['account_id']} {side} state is not at the issuance anchor block; stop")
    require(ledger["window"] == {"start_inclusive": "2026-08-24T00:00:00Z", "end_exclusive": "2026-10-19T00:00:00Z"},
            "Ledger flow window differs from the issuance window")
    return {"opening": {"date": opening["date"], "block_height": opening["anchor_height"], "block_hash": opening["anchor_hash"]},
            "closing": {"date": closing["date"], "block_height": closing["anchor_height"], "block_hash": closing["anchor_hash"]},
            "wallets_checked": len(ledger["native_wallets"]), "states_checked": 2 * len(ledger["native_wallets"])}


def wallet_rows(ledger, lower, upper):
    rows = []
    for w in ledger["native_wallets"]:
        opening, closing = int(w["opening"]["combined_yocto"]), int(w["closing"]["combined_yocto"])
        inflow, outflow = int(w["successful_native_inflow_yocto"]), int(w["successful_native_outflow_yocto"])
        scope = {k: (int(w["flow_scopes"][k]["inflow_yocto"]), int(w["flow_scopes"][k]["outflow_yocto"])) for k in SCOPES}
        require(set(w["flow_scopes"]) == set(SCOPES), "Unexpected flow scopes")
        require(sum(v[0] for v in scope.values()) == inflow and sum(v[1] for v in scope.values()) == outflow,
                "Flow scopes do not sum to gross flows")
        change = closing - opening
        residual = change - (inflow - outflow)
        require(change == int(w["combined_balance_change_yocto"]) and residual == int(w["unexplained_stock_flow_difference_yocto"]),
                "Wallet stock-flow identity differs from result 80")
        require(w["difference_allocation"] == "UNALLOCATED" and w["attributed_fees_yocto"] is None, "Wallet classification changed")
        external_net = scope["EXTERNAL_COUNTERPARTY"][0] - scope["EXTERNAL_COUNTERPARTY"][1]
        internal_net = scope["BETWEEN_SELECTED_WALLETS"][0] - scope["BETWEEN_SELECTED_WALLETS"][1]
        values = {"opening_balance": opening, "closing_balance": closing, "balance_change": change,
                  "gross_successful_inflow": inflow, "gross_successful_outflow": outflow,
                  "external_inflow": scope["EXTERNAL_COUNTERPARTY"][0], "external_outflow": scope["EXTERNAL_COUNTERPARTY"][1],
                  "external_net_inflow": external_net,
                  "between_wallet_inflow": scope["BETWEEN_SELECTED_WALLETS"][0],
                  "between_wallet_outflow": scope["BETWEEN_SELECTED_WALLETS"][1], "between_wallet_net": internal_net,
                  "unallocated_stock_flow_difference": residual}
        rows.append({"account_id": w["account_id"],
                     **{k + "_yocto": str(v) for k, v in values.items()}, **{k + "_near": near(v) for k, v in values.items()},
                     "share_of_issuance": {k: share_of_bounds(values[k], lower, upper)
                                           for k in ("balance_change", "gross_successful_inflow", "external_net_inflow")},
                     "classification": "UNCLASSIFIED_NATIVE_FLOWS_AND_CUSTODIAL_BALANCE"})
    return rows


def group(rows, ledger, lower, upper):
    total = {k: sum(int(r[k + "_yocto"]) for r in rows) for k in (
        "opening_balance", "closing_balance", "balance_change", "gross_successful_inflow", "gross_successful_outflow",
        "external_inflow", "external_outflow", "external_net_inflow", "between_wallet_inflow", "between_wallet_outflow",
        "unallocated_stock_flow_difference")}
    internal = sum(int(t["transfer"]["amount_yocto"]) for t in ledger["native_internal_transfers"])
    require(total["between_wallet_inflow"] == total["between_wallet_outflow"] == internal, "Between-wallet transfers do not cancel")
    require(total["balance_change"] == total["external_net_inflow"] + total["unallocated_stock_flow_difference"],
            "Group balance change does not equal external net plus unallocated difference")
    g = ledger["native_group"]
    require(str(total["external_net_inflow"]) == g["group_observed_external_net_yocto"]
            and str(total["balance_change"]) == g["group_combined_balance_change_yocto"]
            and str(total["unallocated_stock_flow_difference"]) == g["group_unexplained_stock_flow_difference_yocto"],
            "Group totals differ from result 80")
    return {**{k + "_yocto": str(v) for k, v in total.items()}, **{k + "_near": near(v) for k, v in total.items()},
            "between_wallet_transfers": len(ledger["native_internal_transfers"]),
            "between_wallet_transfer_total_near": near(internal),
            "between_wallet_note": "Transfers among the three wallets cancel at group level and are excluded from external net inflow.",
            "share_of_issuance": {k: share_of_bounds(total[k], lower, upper)
                                  for k in ("balance_change", "external_inflow", "external_net_inflow")}}


def report():
    ledger, bounds, paths, bounds_module = load_inputs()
    blocks = same_blocks(ledger, bounds)
    window = bounds["window_total"]
    lower, upper = int(window["issuance_lower_bound_yocto"]), int(window["issuance_upper_bound_yocto"])
    require(lower == int(window["exact_supply_movement_yocto"]) and 0 < lower <= upper, "Unexpected issuance bounds")
    rows = wallet_rows(ledger, lower, upper)
    totals = group(rows, ledger, lower, upper)
    require(all(ledger[k] is None for k in ("verified_revenue_yocto", "verified_buybacks_yocto", "actual_supply_burn_yocto")),
            "Result 80 economic classification changed")
    return {
        "status": "VALIDATED_SAME_BLOCK_SCALE_COMPARISON",
        "window": "2026-08-24/2026-10-18",
        "same_block_reconciliation": blocks,
        "denominators": {
            "issuance_lower_bound_yocto": str(lower), "issuance_lower_bound_near": near(lower),
            "issuance_upper_bound_yocto": str(upper), "issuance_upper_bound_near": near(upper),
            "basis": "Protocol-derived epoch-reward issuance bounds from result 107 over the same anchor blocks. The lower bound equals the exact total-supply movement. Dividing by the upper bound gives the smaller share.",
        },
        "wallets": rows, "three_wallet_group": totals,
        "definitions": {
            "gross_successful_inflow": "All successful native NEAR received by the wallet, including transfers from the other two wallets.",
            "external_net_inflow": "Successful native NEAR received from accounts outside the three wallets, minus native NEAR sent to them.",
            "between_wallet": "Native transfers among the three wallets; they cancel at group level.",
            "balance_change": "Closing minus opening liquid-plus-locked native balance at the anchor blocks; equals net flow plus the unallocated stock-flow difference.",
        },
        "interpretation_limits": [
            "Inflows are unclassified. None is classified as revenue, a buyback, profit or a holder return; account names do not establish purpose.",
            "Balances held by these accounts remain part of total supply. Nothing here measures circulating supply or establishes that balances are withheld from the market.",
            "Coverage is three named accounts on the native NEAR layer only: not the complete treasury system, internal Intents balances, other tokens or other accounts.",
            "Percentages compare scale over identical blocks. They are not measured value capture, an issuance offset or an investment return.",
        ],
        "unavailable": {"verified_revenue_yocto": None, "verified_buybacks_yocto": None, "circulating_supply_effect_yocto": None,
                        "complete_treasury_coverage": None},
        "sources": {str(p.relative_to(ROOT)): bounds_module.sha256_file(p) for p in (paths["ledger"], paths["bounds"], Path(__file__))},
        "network_requests": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    r = sub.add_parser("report")
    r.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    data = (json.dumps(report(), ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode()
    if args.check:
        require(RESULT.read_bytes() == data, "Result 108 does not reproduce")
        print(f"{RESULT.relative_to(ROOT)} reproduces byte-for-byte")
    else:
        with RESULT.open("xb") as handle:
            handle.write(data)
        print(RESULT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
