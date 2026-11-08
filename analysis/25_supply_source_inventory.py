"""Validate SQL 44 offline; prepare or manually collect two weekly endpoints.

inventory and plan make no source requests. collect-week is LIVE: exactly two
sequential block requests through the existing credential-free archival collector.
These endpoints measure weekly supply movement, not weekly issuance or burn.
"""

import argparse
import csv
import importlib.util
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inventory_capture", ROOT / "analysis/11_collect_canonical_validator_evidence.py")
capture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capture)
require = capture.require
SOURCE = ROOT / "results/64_supply_source_schema_inventory.json"
SQL = ROOT / "sql/44_supply_source_schema_inventory.sql"
BASELINE = ROOT / "results/28_daily_supply_checks_2026-08-23_to_2026-10-18.csv"
OUTPUT = ROOT / "results/supply_weekly_header_pilot_2026-09-21_to_2026-09-27"
PINNED_SOURCE = "8540fdb621046c37cd8343640f194634603ca5a0d3230937b096ae6778c29e38"
FIELDS = set("row_kind table_name column_name field_path data_type is_nullable is_partitioning_column description metadata_summary".split())


def identity(path):
    raw = path.read_bytes()
    return {"bytes": len(raw), "sha256": capture.sha256(raw)}


def count(value):
    require(isinstance(value, (str, int)) and not isinstance(value, bool)
            and str(value).isdigit(), "Invalid metadata count")
    return int(value)


def validate(raw):
    rows = capture.decode(raw)
    require(isinstance(rows, list) and rows, "Missing metadata export")
    require(all(isinstance(r, dict) and set(r) == FIELDS for r in rows), "Unexpected export schema")
    kinds = Counter(r["row_kind"] for r in rows)
    require(kinds["SUMMARY"] == 1 and set(kinds) <= {"SUMMARY", "COLUMN", "NESTED"}, "Invalid row kinds/summary count")
    summary_row = next(r for r in rows if r["row_kind"] == "SUMMARY")
    require(all(summary_row[k] is None for k in FIELDS - {"row_kind", "metadata_summary"}), "Unexpected summary fields")
    require(isinstance(summary_row["metadata_summary"], str), "Missing nested summary")
    summary = capture.decode(summary_row["metadata_summary"])
    require(isinstance(summary, dict) and set(summary) == set("metadata_time_utc source_dataset expected_export_rows top_level_rows nested_rows visible_tables inspected_tables".split()), "Unexpected summary schema")
    require(summary["source_dataset"] == "bigquery-public-data.crypto_near_mainnet_us", "Wrong source dataset")
    stamp = datetime.fromisoformat(summary["metadata_time_utc"].replace("Z", "+00:00"))
    require(stamp.utcoffset() == timezone.utc.utcoffset(stamp), "Metadata time must be UTC")
    require(count(summary["expected_export_rows"]) == len(rows)
            and count(summary["top_level_rows"]) == kinds["COLUMN"]
            and count(summary["nested_rows"]) == kinds["NESTED"], "Incomplete export/count discrepancy")
    for key in ("visible_tables", "inspected_tables"):
        names = summary[key]
        require(isinstance(names, list) and all(isinstance(n, str) and n for n in names)
                and names == sorted(set(names)), "Invalid/duplicate table names")
    require(set(summary["inspected_tables"]) <= set(summary["visible_tables"]), "Inspected table not visible")
    expected_tables = {n for n in summary["visible_tables"] if any(
        word in n.lower() for word in ("block", "chunk", "epoch", "validator", "reward", "mint", "raw", "bronze"))}
    require(set(summary["inspected_tables"]) == expected_tables, "Candidate selection differs from SQL 44")
    seen, tables = set(), {}
    for row in rows:
        kind = row["row_kind"]
        if kind == "SUMMARY":
            continue
        require(row["metadata_summary"] is None, "Unexpected nested summary on field")
        table, column, field = (row[k] for k in ("table_name", "column_name", "field_path"))
        require(table in expected_tables and all(isinstance(v, str) and v for v in (column, field, row["data_type"])), "Invalid field identity/type")
        key = (table, field)
        require(key not in seen, "Duplicate metadata field")
        seen.add(key)
        if kind == "COLUMN":
            require(column == field and row["description"] is None
                    and row["is_nullable"] in {"YES", "NO"}
                    and row["is_partitioning_column"] in {"YES", "NO"}, "Invalid top-level metadata")
        else:
            require(field.startswith(column + ".") and row["is_nullable"] is None
                    and row["is_partitioning_column"] is None, "Invalid nested metadata")
        tables.setdefault(table, {})[field] = {k: row[k] for k in (
            "data_type", "is_nullable", "is_partitioning_column")}
    require(set(tables) == expected_tables, "Inspected table missing its fields")
    for row in rows:
        if row["row_kind"] == "NESTED":
            require(row["column_name"] in tables[row["table_name"]], "Nested field missing top-level column")
    return {"status": "METADATA_EXPORT_COMPLETE_OBSERVED_SCHEMA_ONLY", "export_rows": len(rows),
            "row_counts": dict(sorted(kinds.items())), "metadata_summary": summary, "fields": tables,
            "historical_population_established": False, "independent_epoch_mint_yocto": None,
            "independent_weekly_net_header_debit_yocto": None,
            "gross_actual_burn_yocto": None, "subsidies_yocto": None}


def inventory():
    result = validate(SOURCE.read_bytes())
    result["source_hashes"] = {str(p.relative_to(ROOT)): identity(p) for p in (
        SOURCE, SQL, Path(__file__), ROOT / "analysis/11_collect_canonical_validator_evidence.py",
        ROOT / "results/59_persistent_activity_initial_receipt_validation.json")}
    original = ROOT / "sql/43_persistent_activity_shared_week_initial_receipts.sql"
    duplicate = ROOT / "sql/43_persistent_activity_shared_week_initial_receipts 2.sql"
    result["sql43_comparison"] = {
        "authoritative_path": str(original.relative_to(ROOT)),
        "authority": "Tracked file referenced by analysis 21/22 and results 59/61",
        "duplicate_path": str(duplicate.relative_to(ROOT)),
        "byte_identical": original.read_bytes() == duplicate.read_bytes(),
        "files": {str(p.relative_to(ROOT)): identity(p) for p in (original, duplicate)},
        "cleanup_performed": False}
    prior = capture.decode((ROOT / "results/59_persistent_activity_initial_receipt_validation.json").read_bytes())
    recorded = prior["source_hashes"][str(original.relative_to(ROOT))]
    current = original.read_bytes()
    candidate = current[:-2] + current[-1:]
    require(current.endswith(b"; \n") and len(candidate) == recorded["bytes"]
            and capture.sha256(candidate) == recorded["sha256"], "Unverified historical SQL 43 difference")
    result["sql43_comparison"].update({
        "result59_recorded_sql": recorded,
        "historical_difference": "Current file has one extra space after its final semicolon, before LF; removing only that byte in memory reproduces result 59's fingerprint",
        "references": ["analysis/21_validate_initial_receipt_pilot.py: EXTENSION",
                       "analysis/22_validate_shared_week_receipts.py: SQL and preflight",
                       "tests/test_shared_week_receipts.py: validator report/preflight",
                       "results/59_persistent_activity_initial_receipt_validation.json: source_hashes",
                       "results/61_persistent_activity_shared_week_validation.json: source_hashes and prior_validation_provenance"]})
    result["measurement_limits"] = {
        "epoch_boundary_fields": "No epoch_id/next_epoch_id or nested header is exposed in blocks/chunks",
        "predecessors": "blocks.prev_block_hash exists; field availability does not establish historical canonical completeness",
        "chunk_inclusion_and_debit": "No height_created/height_included/balance_burnt; flat chunk block identity does not establish supply-inclusion timing",
        "precision": "total_supply and gas_price are FLOAT64; chunks.gas_used/gas_limit are FLOAT64, not monetary burn fields. Casting cannot recover lost digits",
        "scope": "Current visible dataset metadata only; other datasets/providers and historical field population remain unestablished"}
    return result


def plan():
    require(identity(SOURCE)["sha256"] == PINNED_SOURCE, "Schema input changed; review before collection")
    inventory()
    with BASELINE.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    targets = []
    for label, day, height, block_hash in (
        ("week-opening", "2026-09-20", 216553375, "5sUCEyrF5p3RZvx5DzE6zD4gtknwHf8kMmHnH7ViGPWk"),
        ("week-closing", "2026-09-27", 217555961, "5VLWBqYvC98Q5qUzbQ8nHN1wcGZ9CnLxShZgojz4ohUa")):
        found = [r for r in rows if r["block_date"] == day]
        require(len(found) == 1, "Missing/duplicate saved endpoint date")
        row = found[0]
        require(row["closing_block_hash"] == block_hash and row["closing_block_height"] == str(height), "Saved endpoint identity changed")
        targets.append({"id": label, "date": day, "height": height, "hash": block_hash,
                        "saved_timestamp_utc": row["closing_block_timestamp_utc"],
                        "request": {"jsonrpc": "2.0", "id": label, "method": "block", "params": {"block_id": block_hash}}})
    return {"network": "mainnet", "endpoint": capture.ENDPOINT, "request_count": 2,
            "week_start": "2026-09-21", "week_end": "2026-09-27", "targets": targets,
            "spacing_seconds": capture.SPACING_SECONDS, "automatic_retries": 0, "fallback_endpoints": [],
            "output_root": str(OUTPUT.relative_to(ROOT)) if OUTPUT.is_relative_to(ROOT) else str(OUTPUT),
            "source_hashes": {str(p.relative_to(ROOT)): identity(p) for p in (
                SOURCE, SQL, BASELINE, Path(__file__), ROOT / "analysis/11_collect_canonical_validator_evidence.py")},
            "supports": "Exact supplies at two saved observed weekly endpoints, plus epoch-ID seeds and ordered chunk manifests",
            "does_not_establish": "Last canonical block of each UTC day, intervening predecessor/epoch coverage, weekly independent issuance/debit, gross burn or subsidies"}


def validate_endpoint(result, target):
    h = result.get("header", {})
    require(h.get("hash") == target["hash"] and type(h.get("height")) is int
            and h["height"] == target["height"], "Wrong endpoint block identity")
    capture.money(h.get("total_supply"), "total_supply")
    timestamp = h.get("timestamp_nanosec")
    require(isinstance(timestamp, str) and timestamp.isdigit(), "Missing exact nanosecond timestamp")
    saved = datetime.strptime(target["saved_timestamp_utc"], "%Y-%m-%d %H:%M:%S.%f UTC").replace(tzinfo=timezone.utc)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    delta = saved - epoch
    require(int(timestamp) // 1000 == (delta.days * 86400 + delta.seconds) * 10**6 + delta.microseconds,
            "Saved endpoint timestamp disagreement")
    for key in ("prev_hash", "epoch_id", "next_epoch_id"):
        require(isinstance(h.get(key), str) and h[key], "Missing predecessor/epoch identity")
    chunks, mask = result.get("chunks"), h.get("chunk_mask")
    require(isinstance(chunks, list) and chunks and isinstance(mask, list)
            and len(mask) == len(chunks), "Missing/partial chunk manifest or mask")
    shards, hashes = set(), set()
    delayed = 0
    for index, chunk in enumerate(chunks):
        shard = capture.integer(chunk.get("shard_id"), "shard_id")
        chunk_hash = chunk.get("chunk_hash")
        require(shard not in shards and isinstance(chunk_hash, str) and chunk_hash
                and chunk_hash not in hashes, "Duplicate/invalid observed chunk identity")
        shards.add(shard)
        hashes.add(chunk_hash)
        created, included = (capture.integer(chunk.get(k), k) for k in ("height_created", "height_included"))
        require(created <= included <= h["height"] and type(mask[index]) is bool
                and mask[index] == (included == h["height"]), "Chunk inclusion/mask discrepancy")
        capture.money(chunk.get("balance_burnt"), "balance_burnt")
        require(isinstance(chunk.get("prev_block_hash"), str) and chunk["prev_block_hash"], "Missing chunk predecessor")
        if included == h["height"]:
            if created == included:
                require(chunk["prev_block_hash"] == h["prev_hash"], "New chunk predecessor discrepancy")
            else:
                # A delayed chunk refers to its creation predecessor. That block
                # is not necessarily the inclusion block's immediate parent.
                delayed += 1
    return {"height": h["height"], "hash": h["hash"], "prev_hash": h["prev_hash"],
            "timestamp_nanosec": timestamp, "epoch_id": h["epoch_id"], "next_epoch_id": h["next_epoch_id"],
            "total_supply_yocto": h["total_supply"], "observed_chunk_headers": len(chunks),
            "new_headers_with_earlier_creation_predecessor_unchecked": delayed,
            "expected_protocol_shard_coverage_verified": False}


def validate_week(directory):
    proposal = plan()
    require(capture.decode((directory / "run.json").read_bytes()) == proposal, "Run provenance changed")
    require(len(list(directory.glob("*.metadata.json"))) == 2, "Incomplete two-request capture")
    endpoints = [validate_endpoint(capture.recorded(directory, t["request"]), t) for t in proposal["targets"]]
    difference = int(endpoints[1]["total_supply_yocto"]) - int(endpoints[0]["total_supply_yocto"])
    return {"status": "OBSERVED_ENDPOINTS_CONSISTENT_NOT_WEEKLY_RECONCILIATION", "endpoints": endpoints,
            "net_supply_movement_yocto": str(difference), "independent_weekly_mint_yocto": None,
            "independent_weekly_net_header_debit_yocto": None, "gross_actual_burn_yocto": None, "subsidies_yocto": None}


def collect_week():
    proposal = plan()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    directory = OUTPUT / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:12])
    directory.mkdir()
    capture.write_new(directory / "run.json", capture.json_bytes(proposal))
    print(f"Evidence directory: {directory.resolve()}", flush=True)
    for target in proposal["targets"]:
        validate_endpoint(capture.capture(directory, target["request"]), target)
    capture.write_new(directory / "validation.json", capture.json_bytes(validate_week(directory)))
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inventory", "plan", "collect-week", "validate-week"))
    parser.add_argument("--output", type=Path, help="Exclusive new file; default stdout")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect-week":
            require(args.output is None and args.run_dir is None, "Collection uses a fresh evidence directory")
            collect_week()
            return 0
        if args.command == "validate-week":
            require(args.run_dir is not None, "--run-dir required")
            result = validate_week(args.run_dir)
        else:
            require(args.run_dir is None, "--run-dir applies only to validate-week")
            result = inventory() if args.command == "inventory" else plan()
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
