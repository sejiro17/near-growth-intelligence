"""Bounded, manually invoked weekly epoch discovery; plan/validate are offline.

Use validators start heights and actual boundary/parent headers, never a fixed
epoch length or positive supply changes. Discovery records complete reward maps;
it does not independently measure weekly header debits, gross burn or subsidies.
"""

import argparse
import importlib.util
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "analysis" / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


weekly = module("discovery_weekly", "25_supply_source_inventory.py")
pilot = module("discovery_pilot", "24_supply_epoch_pilot.py")
capture, require = weekly.capture, weekly.require
WEEK_CAPTURE = ROOT / "results/supply_weekly_header_pilot_2026-09-21_to_2026-09-27/20261107T091552Z_88ac7dd4bce1"
PILOT_CAPTURE = ROOT / "results/supply_epoch_pilot_2026-09-23/20261107T075015Z_18b7f0e7ee4f"
CACHE_DIRS = (WEEK_CAPTURE, PILOT_CAPTURE, pilot.SAVED)
OUTPUT = ROOT / "results/supply_epoch_discovery_2026-09-21_to_2026-09-27"
MAX_EPOCHS, MAX_REQUESTS = 32, 97
START_NS, END_NS = [
    (datetime(2026, 9, day, tzinfo=timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)).days * 86400 * 10**9
    for day in (21, 28)
]
BASE58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def chain_id(value):
    require(isinstance(value, str) and value and all(c in BASE58 for c in value), "Invalid chain identifier")
    number = 0
    for char in value:
        number = number * 58 + BASE58.index(char)
    length = (number.bit_length() + 7) // 8 + len(value) - len(value.lstrip("1"))
    require(length == 32, "Chain identifier is not 32 bytes")
    return value


def header(result):
    require(isinstance(result, dict) and isinstance(result.get("header"), dict), "Missing block header")
    h = result["header"]
    for key in ("hash", "prev_hash", "epoch_id", "next_epoch_id"):
        chain_id(h.get(key))
    capture.integer(h.get("height"), "height")
    capture.integer(h.get("prev_height"), "prev_height")
    require(h["prev_height"] < h["height"], "Nondecreasing predecessor height")
    timestamp = h.get("timestamp_nanosec")
    require(isinstance(timestamp, str) and timestamp.isascii() and timestamp.isdigit(), "Missing exact timestamp")
    require(type(h.get("timestamp")) is int and h["timestamp"] == int(timestamp), "Timestamp fields disagree")
    capture.money(h.get("total_supply"), "total_supply")
    return h


def validator_info(result):
    require(isinstance(result, dict), "Missing validator metadata")
    for key in ("epoch_height", "epoch_start_height"):
        capture.integer(result.get(key), key)
        require(result[key] > 0, "Unavailable/genesis epoch metadata")
    require(isinstance(result.get("current_validators"), list) and result["current_validators"], "Missing historical validators")
    ids = []
    for row in result["current_validators"]:
        require(isinstance(row, dict), "Malformed validator record")
        ids.append(capture.account_id(row.get("account_id")))
    require(len(ids) == len(set(ids)), "Duplicate historical validator IDs")
    rewards = result.get("validator_reward_paid_prev_epoch")
    require(isinstance(rewards, dict) and rewards, "Missing/empty reward map; not zero issuance")
    for account, amount in rewards.items():
        capture.account_id(account)
        capture.money(amount, "reward amount")
    require(sum(int(v) for v in rewards.values()) < 2**128, "Reward sum overflows Balance")
    return result


def semantic_key(method, params):
    return method + ":" + capture.json_bytes(params).decode()


class Resolver:
    """Verified local cache; network is reachable only when explicitly live."""

    def __init__(self, directories, live=False, destination=None, transport=None, pause=None):
        self.cache, self.used = {}, []
        self.live, self.destination = live, destination
        self.transport, self.pause = transport, pause
        self.new_requests = 0
        for directory in directories:
            for path in sorted(directory.glob("*.request.json")):
                payload = capture.decode(path.read_bytes())
                if payload.get("method") not in {"block", "validators", "EXPERIMENTAL_protocol_config"}:
                    continue
                result = capture.recorded(directory, payload)
                self.register(directory, payload, result)

    def register(self, directory, payload, result):
        method, params = payload["method"], payload["params"]
        keys = [semantic_key(method, params)]
        if method == "block":
            h = header(result)
            block_id = params.get("block_id")
            require((type(block_id) is int and block_id == h["height"])
                    or (isinstance(block_id, str) and block_id == h["hash"]), "Cached block request/result disagreement")
            keys += [semantic_key(method, {"block_id": h[k]}) for k in ("hash", "height")]
        record = (directory, payload, result)
        for key in keys:
            if key in self.cache:
                require(self.cache[key][2] == result, "Conflicting saved responses for one request identity")
            else:
                self.cache[key] = record

    def has(self, method, params):
        return semantic_key(method, params) in self.cache

    def get(self, method, params):
        key = semantic_key(method, params)
        if key not in self.cache:
            require(self.live, "Missing saved response; offline validation makes no requests")
            require(self.new_requests < MAX_REQUESTS, "Request cap reached; discovery incomplete")
            self.new_requests += 1
            payload = {"jsonrpc": "2.0", "id": f"epoch-{self.new_requests:03d}-{method}", "method": method, "params": params}
            result = capture.capture(self.destination, payload, self.transport, self.pause)
            self.register(self.destination, payload, result)
        directory, payload, result = self.cache[key]
        self.used.append({"method": method, "requested_params": params,
                          "saved_request": str((directory / (payload["id"] + ".request.json")).resolve().relative_to(ROOT))
                          if directory.resolve().is_relative_to(ROOT) else str(directory / (payload["id"] + ".request.json"))})
        return result


def inputs():
    w = weekly.validate_week(WEEK_CAPTURE)
    require(capture.json_bytes(w) == (WEEK_CAPTURE / "validation.json").read_bytes(), "Weekly validation report differs")
    p = pilot.validate(PILOT_CAPTURE)
    require(p["status"] == "EXACT_HEADER_IDENTITY_MATCH"
            and capture.json_bytes(p) == (PILOT_CAPTURE / "validation.json").read_bytes(), "Epoch pilot does not reproduce")
    paths = [Path(__file__), ROOT / "analysis/25_supply_source_inventory.py", ROOT / "analysis/24_supply_epoch_pilot.py",
             ROOT / "analysis/11_collect_canonical_validator_evidence.py", ROOT / "analysis/13_consolidate_supply_evidence.py"]
    for directory in CACHE_DIRS:
        paths += [f for f in directory.iterdir() if f.is_file() and not f.name.startswith(".")]
    return w, p, pilot.fingerprint(paths)


def plan():
    w, p, hashes = inputs()
    opening, closing = w["endpoints"]
    return {"status": "OFFLINE_DISCOVERY_PREPARATION", "endpoint": capture.ENDPOINT,
            "week_start": "2026-09-21T00:00:00Z", "week_end_exclusive": "2026-09-28T00:00:00Z",
            "opening": opening, "closing": closing, "max_application_epochs": MAX_EPOCHS,
            "max_new_requests": MAX_REQUESTS, "sequence_bound": "3*K+1 before saved-response reuse; K <= 32",
            "known_mandatory_reuses": ["A boundary block", "A parent block", "B boundary block", "validators(B epoch)"],
            "successful_complete_walk_new_request_bound": "3*K-3 (at most 93), after the four known mandatory reuses",
            "first_request": {"jsonrpc": "2.0", "id": "epoch-001-validators", "method": "validators", "params": {"epoch_id": closing["epoch_id"]}},
            "last_epoch_reward_response_epoch": closing["next_epoch_id"],
            "opening_epoch_stop_id": opening["epoch_id"], "spacing_seconds": capture.SPACING_SECONDS,
            "connect_timeout_seconds": capture.CONNECT_TIMEOUT, "request_timeout_seconds": capture.REQUEST_TIMEOUT,
            "automatic_retries": 0, "fallback_endpoints": [], "saved_inputs": hashes,
            "known_pilot_mint_yocto": p["epoch_reward_mint_yocto"],
            "protocol_scope": "Per-epoch configs are reused for A/B only; other protocol coverage remains unverified, without additional automatic requests",
            "historical_source_commit": pilot.COMMIT,
            "historical_source_git_blobs": {
                "core/primitives/src/types.rs": "5a8b018fab65d2fa1e59803da47806864727d611",
                "core/primitives/src/views.rs": "a66080fa5753aff77bf44e414642535c3111345d",
                "chain/epoch-manager/src/lib.rs": "b02a0f7e3a575c89e80ade99c9a01452afbb74be",
                "chain/jsonrpc/src/lib.rs": "53f701281374685f7a71ac8fff4b6e730e0cf55b",
                "chain/client-primitives/src/debug.rs": "6d7c22511e09d9e76c9fa9a48b4cdc667f8a6d4c",
                "chain/epoch-manager/src/reward_calculator.rs": "3923545f29ead72b6a0018e2d54c71a397382204"},
            "historical_sources": {
                "epoch_identifier": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/core/primitives/src/types.rs#L534",
                "public_method_and_debug_gate": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/chain/jsonrpc/src/lib.rs#L2992",
                "boundary_storage_and_response": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/chain/epoch-manager/src/lib.rs#L1314",
                "reward_offset": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/core/primitives/src/views.rs#L2594",
                "epoch_info_debug_shape": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/chain/client-primitives/src/debug.rs#L28",
                "reward_sum": f"https://github.com/near/nearcore/blob/{pilot.COMMIT}/chain/epoch-manager/src/reward_calculator.rs#L48"},
            "documentation": ["https://docs.near.org/api-reference/post-validators", "https://docs.near.org/api/rpc/block-chunk", "https://docs.near.org/api/rpc/providers"],
            "independent_weekly_issuance_yocto": None, "independent_weekly_net_debit_yocto": None,
            "gross_burn_yocto": None, "subsidies_yocto": None,
            "manual_command": ".venv/bin/python analysis/26_supply_epoch_discovery.py collect",
            "output_root": str(OUTPUT.relative_to(ROOT)) if OUTPUT.is_relative_to(ROOT) else str(OUTPUT)}


def discover(resolver, opening, closing, controls=None):
    controls = {} if controls is None else controls
    o, cursor = header(opening), header(closing)
    require(int(o["timestamp_nanosec"]) < START_NS <= int(cursor["timestamp_nanosec"]) < END_NS,
            "Saved endpoints do not bracket the selected week")
    closing_header = cursor
    visited, rows, previous = set(), [], None
    while cursor["epoch_id"] != o["epoch_id"]:
        require(len(rows) < MAX_EPOCHS, "Epoch cap reached before opening epoch; discovery incomplete")
        epoch_id, next_epoch_id = cursor["epoch_id"], cursor["next_epoch_id"]
        require(epoch_id not in visited, "Repeated epoch/cycle")
        visited.add(epoch_id)
        info = validator_info(resolver.get("validators", {"epoch_id": epoch_id}))
        require(info["epoch_start_height"] <= cursor["height"], "Start height exceeds epoch anchor")
        if previous:
            require(info["epoch_height"] + 1 == previous["epoch_height"]
                    and info["epoch_start_height"] < previous["height"], "Nonconsecutive/decreasing epoch metadata")
        block = resolver.get("block", {"block_id": info["epoch_start_height"]})
        h = header(block)
        require(h["epoch_id"] == epoch_id and h["next_epoch_id"] == next_epoch_id
                and h["height"] == info["epoch_start_height"], "Boundary epoch/start identity mismatch")
        require(o["height"] < h["height"] <= closing_header["height"]
                and START_NS <= int(h["timestamp_nanosec"]) <= int(cursor["timestamp_nanosec"]) < END_NS,
                "Boundary application time/height outside selected interval")
        parent = header(resolver.get("block", {"block_id": h["prev_hash"]}))
        require(parent["hash"] == h["prev_hash"] == next_epoch_id and parent["height"] == h["prev_height"]
                and parent["epoch_id"] != epoch_id and parent["next_epoch_id"] == epoch_id
                and int(parent["timestamp_nanosec"]) < int(h["timestamp_nanosec"]), "Parent does not establish adjacent epoch transition")
        require(parent["height"] >= o["height"] and int(parent["timestamp_nanosec"]) >= int(o["timestamp_nanosec"]),
                "Walk crossed opening endpoint without its epoch sentinel")
        if parent["height"] == o["height"]:
            require(parent["hash"] == o["hash"], "Opening endpoint hash disagreement")
        reward = validator_info(resolver.get("validators", {"epoch_id": next_epoch_id}))
        require(reward["epoch_height"] == info["epoch_height"] + 1
                and reward["epoch_start_height"] > cursor["height"], "Reward response has wrong successor offset")
        if previous:
            require(reward["epoch_start_height"] == previous["height"], "Successor start does not match prior boundary")
        rewards = reward["validator_reward_paid_prev_epoch"]
        protocol_verified, treasury, mint = False, None, None
        params = {"block_id": h["hash"]}
        if resolver.has("EXPERIMENTAL_protocol_config", params):
            config = resolver.get("EXPERIMENTAL_protocol_config", params)
            chunks = block.get("chunks")
            require(isinstance(chunks, list) and chunks, "Missing saved manifest")
            shards = {capture.integer(c.get("shard_id"), "shard_id") for c in chunks}
            require(len(shards) == len(chunks), "Duplicate boundary shard")
            capture.validate_protocol(config, shards)
            treasury = capture.account_id(config.get("protocol_treasury_account"))
            require(treasury in rewards and any(int(v) > 0 for a, v in rewards.items() if a != treasury),
                    "Treasury missing or degenerate reward branch")
            protocol_verified, mint = True, str(sum(int(v) for v in rewards.values()))
        if h["height"] in controls:
            control = controls[h["height"]]
            require(h["hash"] == control["hash"] and h["timestamp_nanosec"] == control["timestamp_nanosec"], "Saved A/B boundary disagreement")
            if "reward_map" in control:
                require(rewards == control["reward_map"], "Saved A reward map disagreement")
        rows.append({"epoch_id": epoch_id, "epoch_height": info["epoch_height"], "height": h["height"],
                     "hash": h["hash"], "timestamp_nanosec": h["timestamp_nanosec"],
                     "parent_height": parent["height"], "parent_hash": parent["hash"], "parent_epoch_id": parent["epoch_id"],
                     "reward_response_epoch_id": next_epoch_id, "reward_response_epoch_height": reward["epoch_height"],
                     "reward_response_epoch_start_height": reward["epoch_start_height"],
                     "rewards_earned_epoch_height": info["epoch_height"] - 1,
                     "full_reward_map_yocto": rewards, "reward_payees": len(rewards),
                     "recorded_reward_map_sum_yocto": str(sum(int(v) for v in rewards.values())),
                     "historical_protocol_verified": protocol_verified, "treasury_account": treasury,
                     "independently_identified_epoch_reward_mint_yocto": mint})
        previous, cursor = rows[-1], parent
    require(cursor["height"] >= o["height"] and cursor["next_epoch_id"] == o["next_epoch_id"], "Invalid opening-epoch stop")
    require(set(controls) <= {r["height"] for r in rows}, "Complete walk omitted saved A/B controls")
    total = sum(int(r["recorded_reward_map_sum_yocto"]) for r in rows)
    covered = all(r["historical_protocol_verified"] for r in rows)
    net = int(closing_header["total_supply"]) - int(o["total_supply"])
    return {"status": "COMPLETE_OBSERVED_EPOCH_WALK_NOT_WEEKLY_RECONCILIATION", "application_epochs": len(rows),
            "boundaries_descending": rows, "opening_epoch_stop_id": cursor["epoch_id"],
            "all_saved_boundary_controls_observed": True, "recorded_reward_maps_sum_yocto": str(total),
            "epochs_without_protocol_verification": sum(not r["historical_protocol_verified"] for r in rows),
            "independently_identified_weekly_epoch_reward_mint_yocto": str(total) if covered else None,
            "exact_endpoint_supply_movement_yocto": str(net),
            "implied_net_debit_yocto": str(total - net) if covered else None,
            "implied_net_debit_scope": "Issuance minus endpoint supply change; not independently measured debit or gross burn",
            "independently_measured_weekly_net_debit_yocto": None, "gross_actual_burn_yocto": None,
            "subsidies_yocto": None, "gross_issuance_including_subsidies_yocto": None,
            "coverage_scope": "Adjacent observed epoch transitions and endpoint anchors; no independent chain proof or intervening inclusion-debit census"}


def run_discovery(resolver):
    w, p, _ = inputs()
    targets = weekly.plan()["targets"]
    blocks = [resolver.get("block", {"block_id": t["hash"]}) for t in targets]
    saved_blocks, _, _, _ = pilot.saved_inputs()
    controls = {b["header"]["height"]: {k: b["header"][k] for k in ("hash", "timestamp_nanosec")} for b in saved_blocks.values()}
    controls[capture.TARGETS["A"]["height"]]["reward_map"] = p["reward_audit"]["full_reward_map_yocto"]
    return discover(resolver, *blocks, controls)


def validate(directory):
    require(capture.decode((directory / "run.json").read_bytes()) == plan(), "Run/input provenance differs")
    require(len(list(directory.glob("*.metadata.json"))) <= MAX_REQUESTS, "Too many collected requests")
    resolver = Resolver((*CACHE_DIRS, directory))
    report = run_discovery(resolver)
    report["new_request_count"] = len(list(directory.glob("*.metadata.json")))
    report["used_responses"] = resolver.used
    paths = [directory / "run.json"]
    for use in resolver.used:
        request_path = ROOT / use["saved_request"]
        stem = request_path.name.removesuffix(".request.json")
        paths += [request_path.parent / (stem + "." + suffix) for suffix in ("request.json", "metadata.json", "response.body")]
    report["capture_inputs"] = pilot.fingerprint(paths)
    return report


def collect(transport=None, pause=None):
    proposal = plan()
    resolver = Resolver(CACHE_DIRS, live=True, transport=transport, pause=pause)
    require(not OUTPUT.exists() or not any(OUTPUT.iterdir()), "Prior discovery attempt exists; validate it offline before preparing any further collection")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    directory = OUTPUT / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    resolver.destination = directory
    capture.write_new(directory / "run.json", capture.json_bytes(proposal))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    try:
        run_discovery(resolver)
        report = validate(directory)
        capture.write_new(directory / "validation.json", capture.json_bytes(report))
        print(f"Complete observed walk: {report['application_epochs']} application epochs; {report['new_request_count']} new requests.")
    except (Exception, KeyboardInterrupt) as exc:
        capture.write_new(directory / "stopped.json", capture.json_bytes({
            "status": "INCOMPLETE_STOPPED_NOT_ZERO", "error": f"{type(exc).__name__}: {exc}",
            "new_requests_attempted": resolver.new_requests, "used_responses": resolver.used,
            "weekly_issuance_yocto": None, "independent_weekly_debit_yocto": None}))
        raise
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "collect", "validate"))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            require(args.run_dir is None and args.output is None, "Collection requires a fresh directory")
            collect()
            return 0
        require((args.command == "validate") == (args.run_dir is not None), "validate requires --run-dir only")
        result = validate(args.run_dir) if args.command == "validate" else plan()
        raw = capture.json_bytes(result)
        if args.output:
            capture.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}. No retries, resume or endpoint fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
