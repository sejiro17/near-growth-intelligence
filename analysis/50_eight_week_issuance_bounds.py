"""Protocol-bounded eight-week epoch-reward issuance and net header debit.

Commands
--------
plan      Print the frozen request plan (offline).
collect   Manual, capped collection: 9 saved weekly closing anchors x 5 sequential
          point requests (block, validators, epoch first block, its parent,
          EXPERIMENTAL_protocol_config) = at most 45 requests. One attempt each,
          65-second spacing, no retries, fallbacks or resumes. Stops on the first
          failed or unexpected response and keeps every byte received.
validate  Offline replay of a capture directory into the bound report.
report    Offline: validate the single retained capture and write (exclusively)
          or --check result 107.

Protocol semantics (nearcore 2.13.3, commit 5af9ca7; see notes/eight_week_issuance_bounds.md):

* block total_supply = prev total_supply + minted_amount (first block of an
  epoch only) - balance_burnt, where balance_burnt is an unsigned u128 sum of
  newly included chunk headers' net debits (core/primitives/src/block.rs).
* minted_amount applied at the first block of epoch E was computed when epoch
  E-1 was finalized: total_supply(last block of E-1) * max_inflation_rate *
  (ts(last block of E-1) - ts(last block of E-2)) / (31,536,000 s * 1e9) is the
  total epoch reward; withheld validator shares and floor rounding are never
  minted (chain/epoch-manager/src/{lib.rs,reward_calculator.rs}).

For one anchor-delimited week (c_prev, c] with D = ts(parent(first block of the
epoch containing c)) - ts(parent(first block of the epoch containing c_prev)),
x = max_inflation_rate * D / (31,536,000e9):

    supply movement <= minted <= floor(S(c_prev) * x / (1 - x))
    0 <= net header debit = minted - supply movement <= upper - movement

The lower bound uses only the unsigned debit; the upper bound uses the reward
formula and compounding of intra-week mints. Neither is a measurement of gross
burn, subsidies or other adjustments, which remain null.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


cap = module("canonical_capture_for_issuance_bounds", "11_collect_canonical_validator_evidence.py")
require = cap.require

SUPPLY_CSV = ROOT / "results/28_daily_supply_checks_2026-08-23_to_2026-10-18.csv"
RESULT_72 = ROOT / "results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json"
REFERENCE_CONFIG = sorted((ROOT / "results/supply_protocol_checks_2026-09-21_to_2026-09-27").glob(
    "*/protocol-epoch-4786.response.body"))
OUTPUT_ROOT = ROOT / "results/eight_week_issuance_anchors_2026-08-23_to_2026-10-18"
RESULT = ROOT / "results/107_eight_week_issuance_bounds_2026-08-24_to_2026-10-18.json"
NEARCORE_COMMIT = "5af9ca74631e6cf0dae33e77d1a632e94d2952ce"
SECONDS_PER_YEAR = 24 * 60 * 60 * 365  # NUM_SECONDS_IN_A_YEAR in reward_calculator.rs
NS = 10**9
YOCTO = 10**24
STEPS = ("block", "validators", "first", "parent", "config")
MAX_REQUESTS = 9 * len(STEPS)
CONTROL_WEEK = "2026-09-21/2026-09-27"
REVIEW_KEYS = ("chain_id", "protocol_version", "max_inflation_rate", "protocol_reward_rate",
               "protocol_treasury_account", "epoch_length", "online_min_threshold",
               "online_max_threshold", "num_blocks_per_year")
SOURCES = {
    "supply_update": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/core/primitives/src/block.rs#L140-L198",
    "minted_amount_application": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/chain/chain/src/chain.rs#L2520-L2531",
    "finalize_epoch_duration_and_supply": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/chain/epoch-manager/src/lib.rs#L797-L857",
    "epoch_total_reward": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/chain/epoch-manager/src/reward_calculator.rs#L51-L130",
    "seconds_per_year": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/chain/epoch-manager/src/reward_calculator.rs#L10",
    "protocol_version_voting": f"https://github.com/near/nearcore/blob/{NEARCORE_COMMIT}/chain/epoch-manager/src/lib.rs#L562-L580",
}


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return str(path.relative_to(ROOT))


def near(value):
    sign = "-" if value < 0 else ""
    whole, fraction = divmod(abs(value), YOCTO)
    return f"{sign}{whole}.{fraction:024d}"


def ratio(value, digits=12):
    """Exact rational plus a display decimal (half-up), never used for arithmetic."""
    value = Fraction(value)
    scaled = value * 10**digits
    rounded = (scaled.numerator * 2 + scaled.denominator) // (2 * scaled.denominator)
    sign = "-" if rounded < 0 else ""
    whole, fraction = divmod(abs(rounded), 10**digits)
    return {"exact": f"{value.numerator}/{value.denominator}", "display": f"{sign}{whole}.{fraction:0{digits}d}"}


def anchors():
    raw = SUPPLY_CSV.read_bytes()
    rows = list(csv.DictReader(raw.decode().splitlines()))
    selected = []
    for row in rows:
        day = datetime.strptime(row["block_date"], "%Y-%m-%d").date()
        if day.weekday() == 6:  # Sunday closing anchors: 23 Aug .. 18 Oct
            selected.append({"date": row["block_date"], "height": int(row["closing_block_height"]),
                             "hash": row["closing_block_hash"]})
    require([a["date"] for a in selected] == ["2026-08-23", "2026-08-30", "2026-09-06", "2026-09-13",
                                              "2026-09-20", "2026-09-27", "2026-10-04", "2026-10-11",
                                              "2026-10-18"], "Unexpected saved weekly anchors")
    return selected


def request(index, anchor, step, params):
    method = {"block": "block", "first": "block", "parent": "block", "validators": "validators",
              "config": "EXPERIMENTAL_protocol_config"}[step]
    return {"jsonrpc": "2.0", "id": f"a{index}-{anchor['date']}-{step}", "method": method, "params": params}


def plan():
    return {
        "status": "MANUAL_EIGHT_WEEK_ISSUANCE_BOUND_ANCHORS",
        "network": "mainnet", "endpoint": cap.ENDPOINT, "anchors": anchors(),
        "steps_per_anchor": list(STEPS), "max_requests": MAX_REQUESTS,
        "spacing_seconds": cap.SPACING_SECONDS, "connect_timeout_seconds": cap.CONNECT_TIMEOUT,
        "request_timeout_seconds": cap.REQUEST_TIMEOUT, "automatic_retries": 0, "fallback_endpoints": [],
        "source_hashes": {relative(SUPPLY_CSV): sha256_file(SUPPLY_CSV)},
        "historical_commit": NEARCORE_COMMIT, "authoritative_sources": SOURCES,
        "scope": "Point requests at saved weekly closing anchors only. No header ranges, reward-map walk, chunk scan or BigQuery.",
    }


def header(result):
    h = result.get("header")
    require(isinstance(h, dict), "Missing block header")
    cap.money(h.get("total_supply"), "total_supply")
    ts = h.get("timestamp_nanosec")
    require(isinstance(ts, str) and ts.isdigit(), "Missing exact timestamp_nanosec")
    for key in ("hash", "prev_hash", "epoch_id", "next_epoch_id"):
        require(isinstance(h.get(key), str) and h[key], f"Missing header {key}")
    require(type(h.get("height")) is int, "Missing header height")
    return h


def utc_date(ts):
    return datetime.fromtimestamp(int(ts) // NS, timezone.utc).date().isoformat()


def reference_config():
    require(len(REFERENCE_CONFIG) == 1, "Expected one saved reviewed epoch-4786 configuration")
    value = cap.decode(REFERENCE_CONFIG[0].read_bytes())["result"]
    return {k: value[k] for k in REVIEW_KEYS}


def check_anchor(index, anchor, get, reference):
    """Run/replay the five dependent requests for one anchor. `get(payload)` returns an RPC result."""
    block = header(get(request(index, anchor, "block", {"block_id": anchor["hash"]})))
    require(block["hash"] == anchor["hash"] and block["height"] == anchor["height"], "Anchor identity mismatch")
    require(utc_date(block["timestamp_nanosec"]) == anchor["date"], "Anchor UTC date mismatch")
    epoch = block["epoch_id"]
    info = get(request(index, anchor, "validators", {"epoch_id": epoch}))
    start, epoch_height = info.get("epoch_start_height"), info.get("epoch_height")
    require(type(start) is int and type(epoch_height) is int and 0 < start <= block["height"],
            "Invalid epoch start for anchor epoch")
    first = header(get(request(index, anchor, "first", {"block_id": start})))
    require(first["height"] == start and first["epoch_id"] == epoch, "First block is not in the anchor epoch")
    require(int(first["timestamp_nanosec"]) <= int(block["timestamp_nanosec"]), "First block after anchor")
    parent = header(get(request(index, anchor, "parent", {"block_id": first["prev_hash"]})))
    require(parent["hash"] == first["prev_hash"] and parent["height"] < first["height"], "Parent link mismatch")
    require(parent["epoch_id"] != epoch and parent["next_epoch_id"] == epoch, "Parent is not the previous epoch's last block")
    require(int(parent["timestamp_nanosec"]) < int(first["timestamp_nanosec"]), "Parent timestamp ordering")
    config = get(request(index, anchor, "config", {"block_id": anchor["hash"]}))
    require(config.get("chain_id") == "mainnet", "Wrong chain")
    require(config.get("protocol_version") == 86, "Unreviewed protocol version at anchor; stop")
    require(config.get("max_inflation_rate") == [1, 40], "Unreviewed max_inflation_rate; stop")
    mismatched = [k for k in REVIEW_KEYS if config.get(k) != reference[k]]
    require(not mismatched, f"Reviewed economic configuration changed: {mismatched}; stop")
    return {"date": anchor["date"], "anchor_height": block["height"], "anchor_hash": block["hash"],
            "anchor_timestamp_nanosec": block["timestamp_nanosec"], "total_supply_yocto": block["total_supply"],
            "epoch_id": epoch, "epoch_height": epoch_height, "epoch_first_block_height": first["height"],
            "epoch_first_block_hash": first["hash"], "epoch_first_block_timestamp_nanosec": first["timestamp_nanosec"],
            "previous_epoch_last_block_height": parent["height"], "previous_epoch_last_block_hash": parent["hash"],
            "previous_epoch_last_block_timestamp_nanosec": parent["timestamp_nanosec"],
            "active_protocol_version": config["protocol_version"],
            "max_inflation_rate": config["max_inflation_rate"],
            "reviewed_economic_fields_match_saved_epoch_4786": True}


def week_bound(opening, closing, rate):
    s_open, s_close = int(opening["total_supply_yocto"]), int(closing["total_supply_yocto"])
    duration = int(closing["previous_epoch_last_block_timestamp_nanosec"]) - int(opening["previous_epoch_last_block_timestamp_nanosec"])
    applications = closing["epoch_height"] - opening["epoch_height"]
    require(duration > 0 and applications > 0, "Non-increasing epoch sequence between anchors")
    x = Fraction(rate[0], rate[1]) * Fraction(duration, SECONDS_PER_YEAR * NS)
    require(0 < x < 1, "Invalid compounding fraction")
    movement = s_close - s_open
    upper = (s_open * x / (1 - x)).__floor__()
    lower = max(0, movement)
    require(lower <= upper, "Supply movement exceeds protocol issuance ceiling; semantics rejected, stop")
    return {
        "week": f"{(datetime.fromisoformat(opening['date']).date().toordinal() + 1)}",  # replaced below
        "opening_anchor": opening["date"], "closing_anchor": closing["date"],
        "epoch_reward_applications": applications,
        "first_applied_epoch_height": opening["epoch_height"] + 1, "last_applied_epoch_height": closing["epoch_height"],
        "earned_epoch_duration_nanosec": str(duration),
        "opening_supply_yocto": str(s_open), "closing_supply_yocto": str(s_close),
        "exact_supply_movement_yocto": str(movement), "exact_supply_movement_near": near(movement),
        "issuance_lower_bound_yocto": str(lower), "issuance_lower_bound_near": near(lower),
        "issuance_upper_bound_yocto": str(upper), "issuance_upper_bound_near": near(upper),
        "net_header_debit_lower_bound_yocto": "0",
        "net_header_debit_upper_bound_yocto": str(upper - movement), "net_header_debit_upper_bound_near": near(upper - movement),
        "compounding_fraction_x": ratio(x, 15),
    }


def iso_week(opening_date):
    start = datetime.fromordinal(datetime.fromisoformat(opening_date).toordinal() + 1).date()
    end = datetime.fromordinal(start.toordinal() + 6).date()
    return f"{start.isoformat()}/{end.isoformat()}"


def compute(rows):
    rates = {tuple(r["max_inflation_rate"]) for r in rows}
    require(rates == {(1, 40)}, "Inflation rate differs across anchors")
    rate = (1, 40)
    weeks = []
    for opening, closing in zip(rows, rows[1:]):
        w = week_bound(opening, closing, rate)
        w["week"] = iso_week(opening["date"])
        weeks.append(w)
    total = {k: sum(int(w[k]) for w in weeks) for k in (
        "exact_supply_movement_yocto", "issuance_lower_bound_yocto", "issuance_upper_bound_yocto",
        "net_header_debit_upper_bound_yocto", "earned_epoch_duration_nanosec", "epoch_reward_applications")}
    s_open = int(rows[0]["total_supply_yocto"])
    s_close = int(rows[-1]["total_supply_yocto"])
    require(total["exact_supply_movement_yocto"] == s_close - s_open, "Weekly movements do not telescope")
    upper, lower = total["issuance_upper_bound_yocto"], total["issuance_lower_bound_yocto"]
    debit_upper = total["net_header_debit_upper_bound_yocto"]
    year_ns = SECONDS_PER_YEAR * NS
    duration = total["earned_epoch_duration_nanosec"]
    window = {
        "opening_anchor": rows[0]["date"], "closing_anchor": rows[-1]["date"],
        "epoch_reward_applications": total["epoch_reward_applications"],
        "earned_epoch_duration_nanosec": str(duration),
        "opening_supply_yocto": str(s_open), "closing_supply_yocto": str(s_close),
        "exact_supply_movement_yocto": str(s_close - s_open), "exact_supply_movement_near": near(s_close - s_open),
        "issuance_lower_bound_yocto": str(lower), "issuance_lower_bound_near": near(lower),
        "issuance_upper_bound_yocto": str(upper), "issuance_upper_bound_near": near(upper),
        "issuance_bound_width_near": near(upper - lower),
        "net_header_debit_lower_bound_yocto": "0",
        "net_header_debit_upper_bound_yocto": str(debit_upper), "net_header_debit_upper_bound_near": near(debit_upper),
        "net_header_debit_upper_bound_per_week_average_near": near(debit_upper // 8),
        "net_debit_share_of_issuance_upper_bound": ratio(Fraction(debit_upper, lower), 12),
        "annualised_issuance_rate_on_opening_supply_lower": ratio(Fraction(lower * year_ns, s_open * duration), 12),
        "annualised_issuance_rate_on_opening_supply_upper": ratio(Fraction(upper * year_ns, s_open * duration), 12),
        "protocol_maximum_annual_rate": ratio(Fraction(1, 40), 12),
    }
    return weeks, window


def control(weeks, rows):
    """Compare the 21-27 September week with the independently measured reward maps (result 72)."""
    r72 = cap.decode(RESULT_72.read_bytes())
    week = next(w for w in weeks if w["week"] == CONTROL_WEEK)
    measured = int(r72["protocol_validated_weekly_epoch_reward_mint_yocto"])
    require(week["opening_supply_yocto"] == r72["opening_supply_yocto"], "Control opening supply differs from result 72")
    require(week["exact_supply_movement_yocto"] == r72["exact_supply_movement_yocto"], "Control movement differs from result 72")
    require(week["epoch_reward_applications"] == r72["application_epochs"] == 23, "Control application count differs")
    heights = sorted(b["epoch_height"] for b in r72["boundaries"])
    require(week["first_applied_epoch_height"] == heights[0] and week["last_applied_epoch_height"] == heights[-1],
            "Control epoch range differs from result 72")
    closing = next(r for r in rows if r["date"] == "2026-09-27")
    last = max(r72["boundaries"], key=lambda b: b["epoch_height"])
    require(closing["epoch_first_block_height"] == last["height"] and closing["epoch_first_block_hash"] == last["hash"],
            "Control closing epoch boundary differs from result 72")
    lower, upper = int(week["issuance_lower_bound_yocto"]), int(week["issuance_upper_bound_yocto"])
    require(lower <= measured <= upper, "Measured control minting lies outside the derived bounds; stop")
    return {"week": CONTROL_WEEK, "source": relative(RESULT_72),
            "measured_epoch_reward_mint_yocto": str(measured), "measured_epoch_reward_mint_near": near(measured),
            "issuance_lower_bound_near": week["issuance_lower_bound_near"],
            "issuance_upper_bound_near": week["issuance_upper_bound_near"],
            "measured_within_bounds": True,
            "measured_share_of_upper_bound": ratio(Fraction(measured, upper), 12),
            "measured_implied_net_debit_near": near(measured - int(week["exact_supply_movement_yocto"])),
            "net_header_debit_upper_bound_near": week["net_header_debit_upper_bound_near"],
            "matching_checks": ["opening supply", "exact movement", "23 applications", "epoch range 4786-4808",
                                "closing epoch first block 4808"]}


def validate(run_dir):
    run_dir = Path(run_dir).resolve()
    proposal = plan()
    require(cap.decode((run_dir / "run.json").read_bytes()) == proposal, "Run plan/provenance differs")
    files = {p.name for p in run_dir.iterdir()}
    require(len([f for f in files if f.endswith(".request.json")]) == MAX_REQUESTS
            and len([f for f in files if f.endswith(".response.body")]) == MAX_REQUESTS
            and len([f for f in files if f.endswith(".metadata.json")]) == MAX_REQUESTS
            and "stopped.json" not in files, "Incomplete, stopped or excess capture")
    reference = reference_config()
    rows = [check_anchor(i, a, lambda p: cap.recorded(run_dir, p), reference)
            for i, a in enumerate(proposal["anchors"])]
    for a, b in zip(rows, rows[1:]):
        require(b["epoch_height"] > a["epoch_height"] and b["anchor_height"] > a["anchor_height"], "Anchor ordering")
    weeks, window = compute(rows)
    hashes = {}
    for path in sorted(run_dir.iterdir()):
        hashes[relative(path)] = sha256_file(path)
    for path in (SUPPLY_CSV, RESULT_72, REFERENCE_CONFIG[0], Path(__file__)):
        hashes[relative(path)] = sha256_file(path)
    return {
        "status": "VALIDATED_PROTOCOL_DERIVED_BOUNDS",
        "window": "2026-08-24/2026-10-18 (intervals between saved Sunday closing anchors)",
        "classification": {
            "measured": ["exact anchor total supplies and weekly supply movements", "epoch boundary heights, hashes and timestamps",
                         "active protocol version and max_inflation_rate at each anchor"],
            "protocol_derived_bounds": ["issuance lower bound from unsigned net header debit",
                                        "issuance upper bound from the nearcore epoch-reward ceiling",
                                        "net header debit range implied by those bounds"],
            "assumptions_and_qualifications": [
                "Protocol version 86 and max_inflation_rate 1/40 are verified at the nine anchor epochs and all 23 control-week epochs; the other earned epochs are not individually checked. Version selection is a stake vote, not a proof of monotonicity.",
                "Semantics are read from nearcore 2.13.3 (protocol 86); consensus requires every node binary to apply identical protocol-86 rules.",
                "Anchors are the saved observed day-close blocks; weeks are the exact intervals between them.",
                "RPC-derived evidence from one public archival endpoint; not an independent chain proof."],
        },
        "anchors": rows, "weeks": weeks, "window_total": window, "control": control(weeks, rows),
        "unavailable": {"independently_measured_net_header_debit_yocto": None, "gross_actual_burn_yocto": None,
                        "subsidies_yocto": None, "gross_issuance_including_subsidies_yocto": None,
                        "exact_epoch_reward_mint_outside_control_week_yocto": None},
        "interpretation": ("Over the eight weeks, epoch-reward issuance lies between the exact supply movement and the "
                           "protocol ceiling. The bounded net header debit is the net quantity that offsets issuance in the "
                           "supply identity; it is not gross burn, does not separate subsidies and is not execution spending."),
        "authoritative_sources": SOURCES, "capture": relative(run_dir), "source_hashes": hashes,
        "network_requests_during_validation": 0,
    }


def single_capture():
    runs = sorted(p for p in OUTPUT_ROOT.iterdir() if p.is_dir()) if OUTPUT_ROOT.exists() else []
    require(len(runs) == 1, f"Expected exactly one capture directory, found {len(runs)}")
    return runs[0]


def collect(transport=None, pause=None, output_root=OUTPUT_ROOT):
    output_root.mkdir(parents=True, exist_ok=True)
    require(not any(p.is_dir() for p in output_root.iterdir()), "A capture attempt already exists; no automatic resume")
    run_dir = output_root / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:12]}"
    run_dir.mkdir()
    proposal = plan()
    cap.write_new(run_dir / "run.json", cap.json_bytes(proposal))
    reference = reference_config()
    count = {"n": 0}

    def get(payload):
        count["n"] += 1
        require(count["n"] <= MAX_REQUESTS, "Request cap exceeded")
        return cap.capture(run_dir, payload, transport=transport, pause=pause)

    try:
        for i, a in enumerate(proposal["anchors"]):
            check_anchor(i, a, get, reference)
    except Exception as exc:
        cap.write_new(run_dir / "stopped.json", cap.json_bytes(
            {"stopped": True, "reason": f"{type(exc).__name__}: {exc}", "requests_sent": count["n"],
             "totals": None}))
        raise
    print(run_dir)
    return run_dir


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan")
    sub.add_parser("collect")
    v = sub.add_parser("validate")
    v.add_argument("--run-dir", required=True)
    r = sub.add_parser("report")
    r.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "plan":
        sys.stdout.buffer.write(cap.json_bytes(plan()))
    elif args.command == "collect":
        collect()
    elif args.command == "validate":
        sys.stdout.buffer.write(cap.json_bytes(validate(args.run_dir)))
    else:
        data = cap.json_bytes(validate(single_capture()))
        if args.check:
            require(RESULT.read_bytes() == data, "Result 107 does not reproduce")
            print(f"{relative(RESULT)} reproduces byte-for-byte")
        else:
            cap.write_new(RESULT, data)
            print(relative(RESULT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
