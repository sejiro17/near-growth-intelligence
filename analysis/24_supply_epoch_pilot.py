"""Offline preparation and manually invoked collection for one epoch boundary.

plan and validate never request source data. collect makes at most two sequential
requests, retaining the existing collector's bytes, metadata and stop behaviour.
This tests epoch reward minting and the header's NET debit, not gross supply burn.
"""

import argparse
import importlib.util
import json
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


evidence = module("epoch_supply_evidence", "13_consolidate_supply_evidence.py")
capture = evidence.capture
require = capture.require
SAVED = ROOT / "results/canonical_rpc_2026-09-23/20261106T133436Z_2e1218e30fbc/stage1"
WITNESS = ROOT / "results/45_bitwise_validator_update_witness_2026-09-23.json"
OUTPUT = ROOT / "results/supply_epoch_pilot_2026-09-23"
COMMIT = "5af9ca74631e6cf0dae33e77d1a632e94d2952ce"
ACCOUNT = "bitwise_1.poolv1.near"
NEXT_EPOCH = "FVHyDPzSZRgtcicYP665D2gBhapxALLYQktzu6S3P9n2"
SOURCES = {
    "reward_response_semantics": ("core/primitives/src/views.rs", "a66080fa5753aff77bf44e414642535c3111345d", 2612),
    "reward_response_population": ("chain/epoch-manager/src/lib.rs", "b02a0f7e3a575c89e80ade99c9a01452afbb74be", 1553),
    "reward_map_and_minted_amount": ("chain/epoch-manager/src/reward_calculator.rs", "3923545f29ead72b6a0018e2d54c71a397382204", 48),
    "epoch_start_mint_selection": ("chain/client/src/client.rs", "11d87ecff93ed2cae1e833bd0d729c6d7d79fac1", 1113),
    "new_chunk_supply_identity": ("core/primitives/src/block.rs", "0adf83574179e3b203d2e5411b0c948b5e00068c", 145),
    "net_debit_after_subsidy": ("chain/chain/src/runtime/mod.rs", "9db1b922d5194664f1fce5394ec52a675f2d4633", 387),
    "gross_burn_and_subsidy_fields": ("core/primitives/src/chunk_apply_stats.rs", "8a654755efced518d03503956efeda65509a9ec1", 243),
    "historical_stats_storage": ("core/store/src/adapter/chunk_store.rs", "27ead2a44b2004ab569f5d5ed585c9088b467bdc", None),
}


def yocto(value, label):
    capture.money(value, label)
    return int(value)


def near(value):
    return evidence.near_integer(value)


def fingerprint(paths):
    def name(path):
        path = path.resolve()
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    return {name(path): {"sha256": capture.sha256(path.read_bytes()), "bytes": path.stat().st_size}
            for path in sorted(set(paths))}


def requests():
    return [
        {"jsonrpc": "2.0", "id": "A-next-epoch-rewards", "method": "validators",
         "params": {"epoch_id": NEXT_EPOCH}},
        {"jsonrpc": "2.0", "id": "A-parent-block", "method": "block",
         "params": {"block_id": capture.TARGETS["A"]["parent"]}},
    ]


def chunk_debit(block, protocol):
    """Use inclusion height, not creation height or the presence of a chunk."""
    shards = capture.validate_block(block, capture.TARGETS["A"])
    capture.validate_protocol(protocol, shards)
    require(protocol.get("runtime_config", {}).get("wasm_config", {}).get("one_yocto_on_promise") is True,
            "Unreviewed subsidy configuration; stop")
    header = block["header"]
    require(header.get("next_epoch_id") == NEXT_EPOCH, "Wrong A next epoch")
    require(isinstance(header.get("chunk_mask"), list), "Missing chunk mask")
    seen = set()
    rows = []
    for index, chunk in enumerate(block["chunks"]):
        key = chunk["chunk_hash"]
        require(key not in seen, "Duplicate chunk hash")
        seen.add(key)
        included = chunk["height_included"] == header["height"]
        require(isinstance(chunk.get("prev_block_hash"), str) and chunk["prev_block_hash"],
                "Missing chunk predecessor")
        if included:
            require(chunk["prev_block_hash"] == header["prev_hash"], "New chunk predecessor mismatch")
        value = yocto(chunk.get("balance_burnt"), "chunk balance_burnt")
        rows.append({"array_index": index, "shard_id": chunk["shard_id"], "chunk_hash": key,
                     "prev_block_hash": chunk["prev_block_hash"], "height_created": chunk["height_created"],
                     "height_included": chunk["height_included"], "newly_included": included,
                     "balance_burnt_yocto": str(value)})
    included = [x for x in rows if x["newly_included"]]
    excluded = [x for x in rows if not x["newly_included"]]
    total = sum(int(x["balance_burnt_yocto"]) for x in included)
    return {"chunk_headers": rows, "observed_shards": len(rows),
            "configured_shards_match": True, "newly_included_chunks": len(included),
            "carried_forward_chunks_excluded": len(excluded),
            "net_header_debit_yocto": str(total), "net_header_debit_near": near(total),
            "excluded_carried_forward_debit_yocto": str(sum(int(x["balance_burnt_yocto"]) for x in excluded)),
            "gross_actual_burn_yocto": None, "subsidized_amount_yocto": None}


def saved_inputs():
    witness = capture.decode(WITNESS.read_bytes())
    evidence.verify_inputs(witness["source_hashes"])
    require(witness.get("account_id") == ACCOUNT, "Wrong witness account")
    before, after = witness["parent"], witness["post"]
    require(before["block_hash"] == capture.TARGETS["A"]["parent"]
            and after["block_hash"] == capture.TARGETS["A"]["hash"]
            and before["block_height"] + 1 == after["block_height"], "Witness block identity mismatch")
    delta = sum(yocto(after[k], k) - yocto(before[k], k) for k in ("amount_yocto", "locked_yocto"))
    require(str(delta) == witness["change"]["combined_yocto"] and delta > 0,
            "Witness exact arithmetic mismatch")
    blocks, configs = {}, {}
    paths = [WITNESS, Path(__file__), ROOT / "analysis/13_consolidate_supply_evidence.py",
             ROOT / "analysis/11_collect_canonical_validator_evidence.py"]
    for label in "AB":
        blocks[label] = capture.recorded(SAVED, capture.request(label, "block"))
        configs[label] = capture.recorded(SAVED, capture.request(label, "protocol"))
        shards = capture.validate_block(blocks[label], capture.TARGETS[label])
        capture.validate_protocol(configs[label], shards)
        for kind in ("block", "protocol"):
            paths.extend(SAVED / f"{label}-{kind}.{suffix}" for suffix in
                         ("request.json", "response.body", "metadata.json"))
    require(blocks["A"]["header"]["next_epoch_id"] == blocks["B"]["header"]["epoch_id"] == NEXT_EPOCH,
            "Saved next-epoch anchor mismatch")
    return blocks, configs, witness, fingerprint(paths)


def reward_mint(result, treasury, witness):
    capture.integer(result.get("epoch_start_height"), "reward epoch start height")
    require(result.get("epoch_start_height") == capture.TARGETS["B"]["height"],
            "Reward response has wrong epoch-start anchor")
    capture.integer(result.get("epoch_height"), "reward epoch height")
    require(isinstance(result.get("current_validators"), list) and result["current_validators"],
            "Unavailable validator epoch history")
    rewards = result.get("validator_reward_paid_prev_epoch")
    require(isinstance(rewards, dict) and rewards, "Missing/empty reward map; not zero minting")
    capture.account_id(treasury)
    require(treasury in rewards, "Missing treasury in full reward map")
    for account, amount in rewards.items():
        capture.account_id(account)
        yocto(amount, "validator/treasury reward")
    require(any(int(v) > 0 for a, v in rewards.items() if a != treasury),
            "Degenerate reward branch; cannot equate reward map with minted amount")
    require(rewards.get(ACCOUNT) == witness["change"]["combined_yocto"],
            "Reward map does not match saved witness; epoch/timing unresolved")
    total = sum(int(v) for v in rewards.values())
    require(total < 2**128, "Reward total overflows Balance")
    return {"response_epoch_start_height": result["epoch_start_height"],
            "response_epoch_height": result["epoch_height"], "requested_epoch_id": NEXT_EPOCH,
            "reward_payees": len(rewards), "treasury_account": treasury,
            "treasury_reward_yocto": rewards[treasury], "full_reward_map_yocto": rewards,
            "epoch_reward_mint_yocto": str(total), "epoch_reward_mint_near": near(total),
            "witness_reward_yocto": rewards[ACCOUNT], "witness_crosscheck": "MATCH",
            "map_scope": "All returned payees including treasury; no selected-account filter"}


def compare(parent, block, reward, debit):
    h, p = block["header"], parent.get("header", {})
    capture.integer(p.get("height"), "parent height")
    require(p.get("hash") == h["prev_hash"] == capture.TARGETS["A"]["parent"]
            and p.get("height") == h["height"] - 1, "Wrong exact parent identity")
    require(isinstance(p.get("epoch_id"), str) and p["epoch_id"] != h["epoch_id"]
            and p.get("next_epoch_id") == h["epoch_id"], "Parent does not establish epoch transition")
    def timestamp(header):
        value = header.get("timestamp_nanosec", header.get("timestamp"))
        require(type(value) in (int, str) and str(value).isdigit(), "Missing exact timestamp")
        return int(value)
    require(timestamp(p) < timestamp(h), "Parent timestamp does not precede A")
    opening = yocto(p.get("total_supply"), "parent supply")
    closing = yocto(h.get("total_supply"), "A supply")
    mint = yocto(reward["epoch_reward_mint_yocto"], "epoch mint")
    net_debit = yocto(debit["net_header_debit_yocto"], "net debit")
    difference = closing - opening - mint + net_debit
    return {"status": "EXACT_HEADER_IDENTITY_MATCH" if difference == 0 else "HEADER_IDENTITY_MISMATCH",
            "parent_block_hash": p["hash"], "parent_block_height": p["height"],
            "block_hash": h["hash"], "block_height": h["height"],
            "opening_supply_yocto": str(opening), "closing_supply_yocto": str(closing),
            "net_supply_change_yocto": str(closing - opening),
            "epoch_reward_mint_yocto": str(mint), "net_header_debit_yocto": str(net_debit),
            "arithmetic_discrepancy_yocto": str(difference), "tolerance_yocto": "0",
            "gross_actual_burn_yocto": None, "subsidized_amount_yocto": None,
            "gross_issuance_including_subsidy_yocto": None,
            "scope": "One canonical epoch-start header; not daily or weekly gross reconciliation",
            "chunk_audit": debit, "reward_audit": reward}


def plan():
    blocks, configs, witness, hashes = saved_inputs()
    return {"status": "OFFLINE_PREPARATION_ONLY", "endpoint": capture.ENDPOINT,
            "max_requests": 2, "requests_in_order": requests(),
            "stop_after_first_if_invalid": True, "retries": 0, "fallback_endpoints": [],
            "spacing_seconds": capture.SPACING_SECONDS,
            "connect_timeout_seconds": capture.CONNECT_TIMEOUT,
            "request_timeout_seconds": capture.REQUEST_TIMEOUT,
            "saved_inputs": hashes, "protocol_version": configs["A"]["protocol_version"],
            "one_yocto_on_promise": True, "saved_block_header": blocks["A"]["header"],
            "saved_next_epoch_start": {k: blocks["B"]["header"][k] for k in ("height", "hash", "epoch_id")},
            "saved_chunk_audit": chunk_debit(blocks["A"], configs["A"]),
            "witness_crosscheck_yocto": witness["change"]["combined_yocto"],
            "epoch_reward_mint_yocto": None, "parent_exact_supply_yocto": None,
            "gross_actual_burn_yocto": None, "subsidized_amount_yocto": None,
            "identities": {"header": "S_A = S_parent + M_epoch - D_included",
                           "runtime": "D = tx_burnt_amount + other_burnt_amount + slashed_burnt_amount - subsidized_amount",
                           "gross_accounting": "S_A = S_parent + M_epoch - B_gross + U_subsidy"},
            "historical_implementation": {"nearcore_release": "2.13.3", "commit": COMMIT,
                "release_date": "2026-08-04", "source_scope": "Protocol 86 non-Spice path; saved configuration matches",
                "sources": {name: {"path": path, "git_blob_sha1": sha,
                    "url": f"https://github.com/near/nearcore/blob/{COMMIT}/{path}" + (f"#L{line}" if line else "")}
                    for name, (path, sha, line) in SOURCES.items()}},
            "documentation": ["https://docs.near.org/api-reference/post-validators",
                              "https://docs.near.org/api/rpc/providers"],
            "gross_accounting_blocker": "Exact historical ChunkApplyStats balance breakdown, keyed by execution block hash and shard ID and linked to each included prev_balance_burnt/ChunkExtra, is not saved or established as publicly available. Net header debits cannot separate gross burn from subsidy.",
            "precision": "Integer yoctoNEAR, exact zero arithmetic tolerance. Existing FLOAT-derived comparisons retain their separate source-precision limits.",
            "manual_command": "python3 -B analysis/24_supply_epoch_pilot.py collect",
            "output_pattern": "results/supply_epoch_pilot_2026-09-23/<UTC>_<unique-id>/validation.json"}


def validate(directory):
    blocks, configs, witness, hashes = saved_inputs()
    run = capture.decode((directory / "run.json").read_bytes())
    require(run.get("saved_inputs") == hashes and run.get("endpoint") == capture.ENDPOINT
            and run.get("requests_in_order") == requests(), "Capture input/endpoint/request provenance mismatch")
    require(len(list(directory.glob("*.metadata.json"))) == 2, "Expected exactly two completed captures")
    rewards = reward_mint(capture.recorded(directory, requests()[0]),
                          configs["A"]["protocol_treasury_account"], witness)
    report = compare(capture.recorded(directory, requests()[1]), blocks["A"], rewards,
                     chunk_debit(blocks["A"], configs["A"]))
    report["saved_inputs"] = hashes
    report["capture_inputs"] = fingerprint(sorted(directory.glob("*.request.json"))
                                           + sorted(directory.glob("*.response.body"))
                                           + sorted(directory.glob("*.metadata.json"))
                                           + [directory / "run.json"])
    return report


def collect(output_root=OUTPUT, transport=None, pause=None):
    prepared = plan()  # Validate all saved inputs before any request.
    blocks, configs, witness, _ = saved_inputs()
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    capture.write_new(directory / "run.json", capture.json_bytes(prepared))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    result = capture.capture(directory, requests()[0], transport, pause)
    reward_mint(result, configs["A"]["protocol_treasury_account"], witness)
    capture.capture(directory, requests()[1], transport, pause)
    report = validate(directory)
    capture.write_new(directory / "validation.json", capture.json_bytes(report))
    require(report["status"] == "EXACT_HEADER_IDENTITY_MATCH",
            "Header arithmetic mismatch; raw evidence and report retained; stop")
    print("Exact header identity matched. Gross burn and subsidy remain unavailable.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan", help="Offline saved-input audit; stdout by default")
    p.add_argument("--output", type=Path, help="New file only; existing files are never replaced")
    sub.add_parser("collect", help="LIVE: manually invoke at most two archival requests")
    p = sub.add_parser("validate", help="Offline checksum, epoch and exact arithmetic validation")
    p.add_argument("capture_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            collect()
        else:
            value = plan() if args.command == "plan" else validate(args.capture_directory)
            raw = capture.json_bytes(value)
            if getattr(args, "output", None):
                capture.write_new(args.output, raw)
            else:
                sys.stdout.write(raw.decode())
            if value.get("status") == "HEADER_IDENTITY_MISMATCH":
                return 1
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
