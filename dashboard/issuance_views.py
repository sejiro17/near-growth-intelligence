"""Eight-week protocol-bounded issuance (result 107); saved files and in-memory arithmetic only."""

import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pandas as pd
import streamlit as st

if __package__:
    from . import presentation
else:
    import presentation

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "results/107_eight_week_issuance_bounds_2026-08-24_to_2026-10-18.json"
COMPARISON = ROOT / "results/108_supply_treasury_same_block_comparison_2026-08-24_to_2026-10-18.json"
YOCTO = 10**24


def fmt(value, places=2):
    if value is None:
        return "Unavailable"
    return f"{Decimal(value):,.{places}f}"


def signature():
    return (str(ARTIFACT), ARTIFACT.stat().st_mtime_ns, ARTIFACT.stat().st_size) if ARTIFACT.exists() else None


@st.cache_data(max_entries=2, show_spinner=False)
def load(source_signature):
    if source_signature is None:
        return None
    data = json.loads(ARTIFACT.read_bytes())
    total = data["window_total"]
    if not (data["status"] == "VALIDATED_PROTOCOL_DERIVED_BOUNDS" and data["control"]["measured_within_bounds"]
            and all(v is None for v in data["unavailable"].values())
            and int(total["issuance_lower_bound_yocto"]) <= int(total["issuance_upper_bound_yocto"])):
        raise ValueError("Result 107 failed its saved invariants")
    return data


def pct(ratio_item, places=2):
    n, d = (int(x) for x in ratio_item["exact"].split("/"))
    with localcontext() as ctx:
        ctx.prec = 50
        return f"{Decimal(n) * 100 / Decimal(d):.{places}f}%"


def weekly_average_near(yocto_text, weeks=8):
    return Fraction(int(yocto_text), weeks * YOCTO)


def economics():
    data = load(signature())
    if data is None:
        return
    total, control = data["window_total"], data["control"]
    st.subheader("Eight-week issuance is bounded; net supply debit offsets little of it")
    with st.container(horizontal=True):
        st.metric("Epoch-reward issuance · 24 Aug–18 Oct", f"{fmt(total['issuance_lower_bound_near'], 0)}–{fmt(total['issuance_upper_bound_near'], 0)} NEAR",
                  border=True)
        st.metric("Exact supply movement · same eight weeks", fmt(total["exact_supply_movement_near"]) + " NEAR", border=True)
        st.metric("Net header debit · protocol-derived upper bound", "≤ " + fmt(total["net_header_debit_upper_bound_near"], 0) + " NEAR",
                  border=True)
    st.write(f"Across {total['epoch_reward_applications']} epoch-reward applications, the net supply debit that offsets issuance is at most "
             f"**{pct(total['net_debit_share_of_issuance_upper_bound'])} of issuance**. Annualised on opening supply, issuance lies between "
             f"{pct(total['annualised_issuance_rate_on_opening_supply_lower'], 3)} and {pct(total['annualised_issuance_rate_on_opening_supply_upper'], 3)}, "
             f"against the protocol maximum of {pct(total['protocol_maximum_annual_rate'], 1)}.")
    st.info(f"Control week {control['week'].replace('/', '–')}: independently measured reward minting of {fmt(control['measured_epoch_reward_mint_near'])} NEAR "
            f"lies inside its derived range ({fmt(control['issuance_lower_bound_near'])}–{fmt(control['issuance_upper_bound_near'])} NEAR), "
            f"at {pct(control['measured_share_of_upper_bound'])} of the protocol ceiling.")
    st.caption("Lower bound: net header debit is an unsigned protocol quantity, so issuance is at least the exact supply movement. Upper bound: nearcore's "
               "epoch-reward ceiling (total supply × 1/40 × epoch duration ÷ 365 days); withheld validator rewards are never minted. "
               "These are protocol-derived bounds, not measured minting outside the control week. The net debit is not gross burn and does not separate "
               "subsidies; neither is assumed zero. Execution spending is not used. Source: result 107.")
    with st.expander("Weekly bounds, method qualifications and exact values"):
        rows = [{"Week": w["week"].replace("/", "–"), "Applications": w["epoch_reward_applications"],
                 "Exact supply movement NEAR": fmt(w["exact_supply_movement_near"]),
                 "Issuance lower bound NEAR": fmt(w["issuance_lower_bound_near"]),
                 "Issuance upper bound NEAR": fmt(w["issuance_upper_bound_near"]),
                 "Net debit upper bound NEAR": fmt(w["net_header_debit_upper_bound_near"])} for w in data["weeks"]]
        presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch",
                           alt="Eight weekly protocol-derived issuance and net header debit bounds with exact supply movements")
        for item in data["classification"]["assumptions_and_qualifications"]:
            st.caption(item)
        st.json(total)
        st.download_button("Download eight-week issuance bounds (JSON)", data=ARTIFACT.read_bytes(),
                           file_name=ARTIFACT.name, mime="application/json", key="issuance_bounds_download")
    treasury_comparison()


def comparison_signature():
    return (str(COMPARISON), COMPARISON.stat().st_mtime_ns, COMPARISON.stat().st_size) if COMPARISON.exists() else None


@st.cache_data(max_entries=2, show_spinner=False)
def load_comparison(source_signature):
    if source_signature is None:
        return None
    data = json.loads(COMPARISON.read_bytes())
    if not (data["status"] == "VALIDATED_SAME_BLOCK_SCALE_COMPARISON" and all(v is None for v in data["unavailable"].values())):
        raise ValueError("Result 108 failed its saved invariants")
    return data


def share_range(item, places=2):
    """Outward-rounded percentage range from the exact fractions (lower rounds down, upper rounds up)."""
    def scaled(key):
        n, d = (int(x) for x in item[key]["fraction_exact"].split("/"))
        return Fraction(n * 100 * 10**places, d)
    low, high = scaled("against_issuance_upper_bound"), scaled("against_issuance_lower_bound")
    low, high = min(low, high), max(low, high)
    def text(value):
        sign = "-" if value < 0 else ""
        whole, fraction = divmod(abs(value), 10**places)
        return f"{sign}{whole}.{fraction:0{places}d}"
    return f"{text(low.__floor__())}–{text(high.__ceil__())}%"


def treasury_comparison():
    data = load_comparison(comparison_signature())
    if data is None:
        return
    group, blocks = data["three_wallet_group"], data["same_block_reconciliation"]
    st.markdown("**Same blocks, three wallets · treasury-named balances compared with issuance**")
    st.write(f"The three-wallet native ledger was measured at the same opening and closing blocks as the issuance bounds "
             f"({blocks['opening']['block_height']:,} and {blocks['closing']['block_height']:,}). Its external net native inflow of "
             f"{fmt(group['external_net_inflow_near'])} NEAR equals **{share_range(group['share_of_issuance']['external_net_inflow'])} "
             f"of eight-week issuance**. Transfers among the three wallets ({fmt(group['between_wallet_transfer_total_near'])} NEAR) cancel and are excluded.")
    rows = [{"Account": w["account_id"], "Balance change NEAR": fmt(w["balance_change_near"]),
             "Gross inflow NEAR": fmt(w["gross_successful_inflow_near"]),
             "External net inflow NEAR": fmt(w["external_net_inflow_near"]),
             "Between-wallet net NEAR": fmt(w["between_wallet_net_near"]),
             "External net as share of issuance": share_range(w["share_of_issuance"]["external_net_inflow"])} for w in data["wallets"]]
    rows.append({"Account": "Three-wallet group", "Balance change NEAR": fmt(group["balance_change_near"]),
                 "Gross inflow NEAR": fmt(group["gross_successful_inflow_near"]),
                 "External net inflow NEAR": fmt(group["external_net_inflow_near"]), "Between-wallet net NEAR": "0.00",
                 "External net as share of issuance": share_range(group["share_of_issuance"]["external_net_inflow"])})
    presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch",
                       alt="Three-wallet native balance changes and flows over the same blocks as the issuance bounds, with shares of issuance")
    st.caption("A scale comparison, not value capture. Inflows are unclassified: none is classified as revenue, a buyback, profit or a holder return. "
               "Balances held by these accounts remain part of total supply, and nothing here measures circulating supply. "
               "Three named native-layer wallets are not the complete treasury system; internal Intents balances, other tokens and other accounts are not covered. "
               "Share ranges divide by the upper and lower issuance bounds. Source: result 108.")


def model_context(applied):
    """Observed net-supply hurdle under the applied price/fee/capture/allocation assumptions."""
    data = load(signature())
    if data is None:
        return
    total = data["window_total"]
    growth = weekly_average_near(total["exact_supply_movement_yocto"])
    reward = Fraction(Decimal(applied["reward_mint_near_per_week"]))
    st.markdown("**Eight-week evidence check · net supply growth versus the reward-only target**")
    try:
        coefficient = (Fraction(Decimal(applied["fee_rate"])) * Fraction(Decimal(applied["capture_fraction"]))
                       * Fraction(Decimal(applied["destruction_allocation"])))
        price = Fraction(Decimal(applied["price_usd_per_near"]))
    except (KeyError, TypeError, ArithmeticError):
        st.caption("Unavailable for the applied assumptions.")
        return
    hurdle = None if coefficient == 0 else growth * price / coefficient
    rows = [
        {"Quantity": "Average weekly exact net supply growth · eight weeks", "Value": fmt(Decimal(growth.numerator) / Decimal(growth.denominator)) + " NEAR/week",
         "Basis": "Measured exact anchor supplies (result 107)"},
        {"Quantity": "Applied reward-minting target", "Value": fmt(Decimal(reward.numerator) / Decimal(reward.denominator)) + " NEAR/week",
         "Basis": "Dated 21–27 September baseline or user-edited value"},
        {"Quantity": "Activity needed to destroy the average observed net supply growth",
         "Value": "Unreachable at zero capture/allocation" if hurdle is None else "$" + fmt(Decimal(hurdle.numerator) / Decimal(hurdle.denominator)) + "/week",
         "Basis": "Applied price, fee, capture and destruction allocation; historical growth repeated as a scenario"},
    ]
    presentation.table(pd.DataFrame(rows), hide_index=True, width="stretch",
                       alt="Eight-week exact net supply growth compared with the applied reward-only target, and the activity needed to offset it")
    st.caption(f"Net supply growth already includes every protocol supply term (epoch minting less net header debit), so this target needs no assumption "
               f"about subsidies or burn. Because the bounded net debit is at most {pct(total['net_debit_share_of_issuance_upper_bound'])} of issuance, "
               "it barely lowers the requirement relative to reward minting alone. Repeating past growth is a scenario; this is not a forecast, fair value or return.")
