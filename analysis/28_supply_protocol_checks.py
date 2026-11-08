"""Offline weekly supply status and manual, capped historical config checks.

plan/status/validate never request data. collect fetches only the 21 missing
application-epoch configurations; it does not repeat headers or reward maps.
"""

import argparse
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("protocol_recovery", ROOT / "analysis/27_recover_supply_epoch_discovery.py")
recovery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(recovery)
d, capture, require = recovery.d, recovery.capture, recovery.require
WALK = ROOT / "results/supply_epoch_discovery_recovery_2026-09-21_to_2026-09-27/20261107T094028Z_f5df2c194ab4_recovery_01"
OUTPUT = ROOT / "results/supply_protocol_checks_2026-09-21_to_2026-09-27"
MAX_REQUESTS = 21
METHOD = "EXPERIMENTAL_protocol_config"
REVIEW_KEYS = ("chain_id", "protocol_version", "protocol_treasury_account", "max_inflation_rate",
               "protocol_reward_rate", "num_blocks_per_year", "runtime_config")


def near(value):
    sign = "-" if value < 0 else ""
    whole, fraction = divmod(abs(value), 10**24)
    return f"{sign}{whole}.{fraction:024d}"


def configuration_bytes(value):
    """Deterministic JSON for diagnostic hashes, retaining exact Decimal numbers.

    Raw response bytes remain the provenance source and are never rewritten.
    Configs contain fractional non-monetary settings; no float conversion is used.
    """
    def encode(item):
        if isinstance(item, Decimal):
            require(item.is_finite(), "Nonfinite configuration number")
            return str(item)
        if isinstance(item, dict):
            require(all(isinstance(k, str) for k in item), "Non-string configuration key")
            return "{" + ",".join(json.dumps(k)+":"+encode(item[k]) for k in sorted(item)) + "}"
        if isinstance(item, list):
            return "[" + ",".join(encode(v) for v in item) + "]"
        require(item is None or type(item) in (str, bool, int), "Unsupported/float configuration scalar")
        return json.dumps(item)
    return encode(value).encode()


def saved():
    report = recovery.validate_remaining(WALK)
    require(capture.json_bytes(report) == (WALK / "validation.json").read_bytes(), "Completed epoch report differs")
    _, resolver = recovery.seed_recovery(WALK)
    for path in sorted((WALK / "remaining").glob("*.request.json")):
        payload = capture.decode(path.read_bytes())
        resolver.register(path.parent, payload, capture.recorded(path.parent, payload))
    require(report["application_epochs"] == 23 and report["epochs_without_protocol_verification"] == 21,
            "Unexpected baseline protocol coverage")
    return report, resolver


def source_hashes(report):
    paths = [Path(__file__), WALK / "validation.json"]
    for use in report["used_responses"]:
        p = ROOT / use["saved_request"]
        stem = p.name.removesuffix(".request.json")
        paths += [p.parent / (stem + "." + suffix) for suffix in ("request.json", "response.body", "metadata.json")]
    return d.pilot.fingerprint(paths)


def request(row):
    return {"jsonrpc": "2.0", "id": f"protocol-epoch-{row['epoch_height']}", "method": METHOD,
            "params": {"block_id": row["hash"]}}


def plan():
    report, _ = saved()
    targets = [{k: row[k] for k in ("epoch_id", "epoch_height", "height", "hash", "timestamp_nanosec")}
               for row in reversed(report["boundaries_descending"]) if not row["historical_protocol_verified"]]
    require(len(targets) == MAX_REQUESTS and len({r["hash"] for r in targets}) == MAX_REQUESTS, "Missing/duplicate config targets")
    for row in targets:
        row["request"] = request(row)
    return {"status": "MANUAL_PROTOCOL_CHECK_PREPARATION", "network": "mainnet", "endpoint": capture.ENDPOINT,
            "week": "2026-09-21/2026-09-27", "requests": targets, "max_requests": MAX_REQUESTS,
            "reused_protocol_epochs": [4793, 4794], "spacing_seconds": capture.SPACING_SECONDS,
            "connect_timeout_seconds": capture.CONNECT_TIMEOUT, "request_timeout_seconds": capture.REQUEST_TIMEOUT,
            "automatic_retries": 0, "fallback_endpoints": [], "source_hashes": source_hashes(report),
            "historical_commit": d.pilot.COMMIT,
            "activation_scope": "No complete historical activation/configuration census is saved. No interpolation from announcements, equal endpoint versions or advertised latest_protocol_version.",
            "authoritative_sources": {
                "active_epoch_selection": f"https://github.com/near/nearcore/blob/{d.pilot.COMMIT}/chain/client/src/view_client_actor.rs#L1629",
                "active_configuration": f"https://github.com/near/nearcore/blob/{d.pilot.COMMIT}/chain/chain/src/runtime/mod.rs#L1583",
                "voting": f"https://github.com/near/nearcore/blob/{d.pilot.COMMIT}/chain/epoch-manager/src/lib.rs#L544",
                "public_method": "https://docs.near.org/api/rpc/protocol"},
            "manual_command": ".venv/bin/python analysis/28_supply_protocol_checks.py collect",
            "output_root": str(OUTPUT.relative_to(ROOT)) if OUTPUT.is_relative_to(ROOT) else str(OUTPUT)}


def net_header_debit(block):
    h = d.header(block)
    chunks, mask = block.get("chunks"), h.get("chunk_mask")
    require(isinstance(chunks, list) and chunks and isinstance(mask, list) and len(mask) == len(chunks), "Missing chunk manifest/mask")
    require(len({c.get("shard_id") for c in chunks}) == len(chunks)
            and len({c.get("chunk_hash") for c in chunks}) == len(chunks), "Duplicate chunk/shard identity")
    require(all(type(value) is bool for value in mask)
            and mask == [c.get("height_included") == h["height"] for c in chunks]
            and type(h.get("chunks_included")) is int and h["chunks_included"] == sum(mask), "Inclusion diagnostics disagree")
    total = 0
    for c in chunks:
        capture.integer(c.get("shard_id"), "shard")
        d.chain_id(c.get("chunk_hash"))
        d.chain_id(c.get("prev_block_hash"))
        created = capture.integer(c.get("height_created"), "created")
        included = capture.integer(c.get("height_included"), "included")
        require(created <= included <= h["height"], "Invalid chunk timing")
        capture.money(c.get("balance_burnt"), "net header debit")
        if included == h["height"]:
            total += int(c["balance_burnt"])
    return total


def validate_configuration(config, block, reference):
    require(type(config.get("protocol_version")) is int, "Invalid active protocol version type")
    chunks = block.get("chunks")
    require(isinstance(chunks, list) and chunks, "Missing boundary chunk manifest")
    shards = {capture.integer(c.get("shard_id"), "shard") for c in chunks}
    require(len(shards) == len(chunks), "Duplicate header shards")
    capture.validate_protocol(config, shards)  # Reviewed protocol 86; stop on other versions.
    require(all(k in config and k in reference and config[k] == reference[k] for k in REVIEW_KEYS),
            "Unreviewed economic/runtime configuration change; retain response and stop")
    capture.account_id(config["protocol_treasury_account"])
    require(config["runtime_config"]["wasm_config"].get("one_yocto_on_promise") is True, "Unreviewed subsidy flag")
    return {"active_protocol_version": config["protocol_version"], "reviewed_runtime_and_economic_fields_match_AB": True,
            "configured_shards_match_observed_header": True,
            "configuration_semantic_sha256": capture.sha256(configuration_bytes(config))}


def status(report=None, resolver=None):
    if report is None:
        report, resolver = saved()
    rows, verified_mint = [], 0
    for row in report["boundaries_descending"]:
        block = resolver.get("block", {"block_id": row["hash"]})
        parent = resolver.get("block", {"block_id": row["parent_hash"]})
        debit = net_header_debit(block)
        reward = sum(int(v) for v in row["full_reward_map_yocto"].values())
        movement = int(block["header"]["total_supply"]) - int(parent["header"]["total_supply"])
        require(movement - reward + debit == 0, "Boundary monetary identity mismatch")
        if row["historical_protocol_verified"]:
            require(int(row["independently_identified_epoch_reward_mint_yocto"]) == reward, "Verified mint differs from map")
            verified_mint += reward
        rows.append({"epoch_height": row["epoch_height"], "height": row["height"], "hash": row["hash"],
                     "recorded_reward_map_yocto": str(reward), "observed_boundary_net_header_debit_yocto": str(debit),
                     "boundary_supply_movement_yocto": str(movement), "arithmetic_discrepancy_yocto": "0",
                     "protocol_verified": row["historical_protocol_verified"]})
    opening = int(resolver.get("block", {"block_id": d.weekly.plan()["targets"][0]["hash"]})["header"]["total_supply"])
    net = int(report["exact_endpoint_supply_movement_yocto"])
    rewards, debits = sum(int(r["recorded_reward_map_yocto"]) for r in rows), sum(int(r["observed_boundary_net_header_debit_yocto"]) for r in rows)
    missing = sum(not r["protocol_verified"] for r in rows)
    with localcontext() as context:
        context.prec = 80
        supply_growth_pct = str(Decimal(net)*100/Decimal(opening))
    return {"week": "2026-09-21/2026-09-27", "application_epochs": len(rows), "protocol_checks_missing": missing,
            "opening_supply_yocto": str(opening), "exact_supply_movement_yocto": str(net), "exact_supply_movement_near": near(net),
            "recorded_reward_maps_yocto": str(rewards), "recorded_reward_maps_near": near(rewards),
            "protocol_validated_mint_subtotal_yocto": str(verified_mint), "protocol_validated_mint_subtotal_near": near(verified_mint),
            "protocol_validated_weekly_epoch_reward_mint_yocto": str(rewards) if missing == 0 else None,
            "observed_boundary_header_debits_yocto": str(debits), "observed_boundary_header_debits_near": near(debits),
            "boundary_debit_scope": "23 application blocks only; not all weekly inclusion blocks or gross burn",
            "conditional_reward_map_implied_weekly_net_debit_yocto": str(rewards-net),
            "conditional_reward_map_implied_weekly_net_debit_near": near(rewards-net),
            "implied_debit_scope": "Recorded reward maps minus exact supply movement; conditional until protocol checks complete; never independent debit or burn",
            "independently_measured_weekly_net_debit_yocto": None, "gross_actual_burn_yocto": None, "subsidies_yocto": None,
            "gross_issuance_including_subsidies_yocto": None, "boundaries": rows,
            "observed_endpoint_total_supply_growth_pct": supply_growth_pct,
            "investment_scope": "Observed net supply growth and conditional scenarios; no staking APR, revenue yield, actual burn, net purchases or holder return established",
            "source_hashes": source_hashes(report)}


def validate(directory):
    proposal = plan()
    require(capture.decode((directory / "run.json").read_bytes()) == proposal, "Protocol run/input provenance differs")
    require(len(list(directory.glob("*.metadata.json"))) == MAX_REQUESTS
            and len(list(directory.glob("*.request.json"))) == MAX_REQUESTS
            and len(list(directory.glob("*.response.body"))) == MAX_REQUESTS, "Incomplete/excess configuration capture")
    report, resolver = saved()
    reference = resolver.get(METHOD, {"block_id": capture.TARGETS["A"]["hash"]})
    audits = []
    for row in proposal["requests"]:
        block = resolver.get("block", {"block_id": row["hash"]})
        config = capture.recorded(directory, row["request"])
        checks = validate_configuration(config, block, reference)
        resolver.register(directory, row["request"], config)
        audits.append({"epoch_id": row["epoch_id"], "height": row["height"], "hash": row["hash"], **checks})
    updated = d.run_discovery(resolver)
    require(updated["epochs_without_protocol_verification"] == 0, "Protocol coverage incomplete")
    updated["used_responses"] = list(resolver.used)
    result = status(updated, resolver)
    result.update(status="ALL_23_APPLICATION_CONFIGURATIONS_VALIDATED_NOT_WEEKLY_DEBIT_RECONCILIATION", configuration_audits=audits)
    result["configuration_capture_inputs"] = d.pilot.fingerprint(
        [directory / "run.json"] + sorted(directory.glob("*.request.json"))
        + sorted(directory.glob("*.response.body")) + sorted(directory.glob("*.metadata.json")))
    return result


def collect(transport=None, pause=None):
    proposal = plan()
    _, resolver = saved()
    reference = resolver.get(METHOD, {"block_id": capture.TARGETS["A"]["hash"]})
    require(not OUTPUT.exists() or not any(OUTPUT.iterdir()), "Prior protocol attempt exists; inspect offline before further collection")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    directory = OUTPUT / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    capture.write_new(directory / "run.json", capture.json_bytes(proposal))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    attempted = 0
    try:
        for row in proposal["requests"]:
            require(not resolver.has(METHOD, row["request"]["params"]), "Configuration already saved; no duplicate request")
            attempted += 1
            require(attempted <= MAX_REQUESTS, "Protocol request cap reached")
            config = capture.capture(directory, row["request"], transport=transport, pause=pause)
            validate_configuration(config, resolver.get("block", {"block_id": row["hash"]}), reference)
        result = validate(directory)
        capture.write_new(directory / "validation.json", capture.json_bytes(result))
    except (Exception, KeyboardInterrupt) as exc:
        capture.write_new(directory / "stopped.json", capture.json_bytes({"status": "INCOMPLETE_PROTOCOL_CHECKS_NOT_ZERO",
            "requests_attempted": attempted, "error": f"{type(exc).__name__}: {exc}",
            "validated_weekly_epoch_reward_mint_yocto": None, "independent_weekly_net_debit_yocto": None}))
        raise
    print("All 23 application configurations checked. Independent weekly net debit, gross burn and subsidies remain unavailable.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "status", "collect", "validate"))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        require((args.command == "validate") == (args.run_dir is not None), "Only validate requires --run-dir")
        if args.command == "collect":
            require(args.output is None, "Collection uses an exclusive evidence directory")
            collect()
            return 0
        result = validate(args.run_dir) if args.command == "validate" else (plan() if args.command == "plan" else status())
        raw = capture.json_bytes(result)
        if args.output:
            capture.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Stopped: {exc}. No automatic retry or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
