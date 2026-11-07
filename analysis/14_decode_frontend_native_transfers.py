"""Validate result 47 and derive exact native-transfer amounts entirely offline.

Supports the observed dotted-column export and nested-JSON deposit strings only.
Default output is stdout; --output creates a new file exclusively. No network IO.
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/47_frontend_wallet_native_transfer_diagnostic_2026-09-23.json"
OUTPUT = ROOT / "results/48_frontend_wallet_native_transfers_decoded_2026-09-23.json"
DATE = "2026-09-23"
ACCOUNT = "fefundsadmin.sputnik-dao.near"
A = "transfer_record.source_action."
O = "transfer_record.outcome_audit."
E = O + "observations."
T = "transfer_record.initial_origin_audit."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, f"Duplicate JSON key: {key}")
            value[key] = item
        return value

    def invalid(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")

    return json.loads(raw, object_pairs_hook=unique, parse_float=Decimal,
                      parse_constant=invalid)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def fingerprint(path):
    raw = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def count(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9]+", value),
            "Missing or invalid exported integer diagnostic")
    return int(value)


def near(value):
    whole, fraction = divmod(value, 10**24)
    return f"{whole}.{fraction:024d}"


def timestamp(value):
    require(isinstance(value, str), "Missing timestamp")
    result = datetime.fromisoformat(value.replace(" UTC", "+00:00").replace("Z", "+00:00"))
    require(result.utcoffset() is not None and result.utcoffset().total_seconds() == 0
            and result.date().isoformat() == DATE, "Wrong UTC observation date")
    return result


def deposit(row, source):
    """Two JSON parses, with agreement against both retained representations."""
    outer = decode(row[A + "raw_args_json"])
    require(isinstance(outer, str) and outer == row[A + "raw_args_scalar_text"]
            == source["args"], "Raw args representations disagree or encoding changed")
    args = decode(outer)
    require(isinstance(args, dict) and set(args) == {"deposit"},
            "Expected a deposit-only JSON object")
    text = args["deposit"]
    require(isinstance(text, str) and re.fullmatch(r"[0-9]{1,39}", text),
            "Deposit must be an exact unsigned decimal string")
    require(int(text) < 2**128, "Deposit exceeds u128")
    return text


def validate_rows(rows):
    require(isinstance(rows, list) and rows, "Expected nonempty result-row array")
    summaries = [r for r in rows if r.get("row_kind") == "SUMMARY"]
    transfers = [r for r in rows if r.get("row_kind") == "TRANSFER"]
    require(len(summaries) == 1 and len(rows) == 1 + len(transfers),
            "Expected one SUMMARY and only TRANSFER detail rows")
    summary = summaries[0]
    for row in rows:
        require(row["observation_date"] == DATE and row["target_account_id"] == ACCOUNT
                and row["asset_scope"] == "NATIVE_ONLY_EXCLUDES_TOKENS_AND_INTERNAL_VERIFIER_BALANCES",
                "Unexpected observation identity or asset scope")
        null_prefix = "transfer_record." if row["row_kind"] == "SUMMARY" else "summary_record."
        require(all(v is None for k, v in row.items() if k.startswith(null_prefix)),
                "Unexpected nonnull fields on the other row kind")
    require(count(summary["summary_record.output_transfer_rows"]) == len(transfers),
            "Output transfer count mismatch")
    decoded, keys, observed = [], set(), Counter()
    for index, row in enumerate(rows):
        if row["row_kind"] != "TRANSFER":
            continue
        source = decode(row[A + "source_row_json"])
        outcome = decode(row[E + "source_outcome_row_json"])
        for field in ("block_height", "shard_id", "index_in_action_receipt"):
            require(type(source[field]) is int and source[field] >= 0,
                    f"Invalid source integer: {field}")
        require(isinstance(source["block_timestamp"], str)
                and re.fullmatch(r"[0-9]+", source["block_timestamp"]),
                "Missing exact nanosecond timestamp")
        key = (row[A + "receipt_id"], count(row[A + "action_index"]))
        require(key not in keys, "Duplicate action identity")
        keys.add(key)
        for derived, original in (
            ("receipt_id", "receipt_id"), ("action_kind", "action_kind"),
            ("receiver", "receipt_receiver_account_id"),
            ("predecessor", "receipt_predecessor_account_id"),
            ("action_index", "index_in_action_receipt"),
            ("source_action_index_text", "index_in_action_receipt"),
            ("source_block_hash", "block_hash"), ("source_block_height", "block_height"),
            ("source_chunk_hash", "chunk_hash"), ("source_shard_id_text", "shard_id"),
            ("source_signer_account_id", "signer_account_id"),
            ("source_signer_public_key", "signer_public_key"),
        ):
            require(row[A + derived] == str(source[original]), f"Source identity mismatch: {derived}")
        require(source["action_kind"] == "TRANSFER"
                and source["receipt_receiver_account_id"] == ACCOUNT
                and source["block_date"] == row[A + "block_date"] == DATE,
                "Wrong action or source date")
        require(type(source["is_delegate_action"]) is bool
                and str(source["is_delegate_action"]).lower() == row[A + "source_delegation_text"],
                "Delegation fields disagree")
        require(timestamp(source["block_timestamp_utc"]) == timestamp(row[A + "source_timestamp_utc"])
                == timestamp(row[A + "source_timestamp_text"]), "Source timestamps disagree")
        ns_seconds, ns_fraction = divmod(int(source["block_timestamp"]), 10**9)
        utc = datetime.fromtimestamp(ns_seconds, tz=timestamp(source["block_timestamp_utc"]).tzinfo)
        require(timestamp(source["block_timestamp_utc"]) == utc.replace(microsecond=ns_fraction // 1000),
                "Nanosecond and microsecond timestamps disagree")
        require(row["transfer_record.economic_classification"] == "UNCLASSIFIED_TRANSFER",
                "Unexpected economic classification")
        require(row["transfer_record.action_check"] == "OBSERVED_ACTION_KEY_AND_TIMESTAMP_CONSISTENT"
                and count(row[A + "same_day_action_key_rows"]) == 1,
                "Invalid or duplicate source action")
        # This export has one outcome and one block observation per action. Reject
        # multi-match display exports instead of guessing flattened array alignment.
        require(count(row[O + "outcome_rows"]) == 1
                and count(row[E + "execution_block_match_rows"]) == 1,
                "Missing/duplicate outcome or block observations")
        for field in ("missing_status_rows", "invalid_outcome_timestamp_rows", "executor_mismatch_rows",
                      "unavailable_execution_hash_rows", "unresolved_execution_block_rows"):
            require(count(row[O + field]) == 0, f"Invalid outcome diagnostic: {field}")
        require(count(row[E + "execution_block_invalid_rows"]) == 0, "Invalid execution block")
        require(row[O + "receipt_id"] == source["receipt_id"] == outcome["receipt_id"]
                and outcome["executor_account_id"] == row[E + "executor_account_id"] == ACCOUNT,
                "Outcome receipt/executor mismatch")
        for derived, original in (
            ("outcome_record_block_hash", "block_hash"),
            ("outcome_record_block_height_text", "block_height"),
            ("outcome_record_chunk_hash", "chunk_hash"),
            ("outcome_record_shard_id_text", "shard_id"),
            ("executed_in_block_hash", "executed_in_block_hash"), ("status", "status"),
        ):
            require(row[E + derived] == str(outcome[original]), "Outcome observation mismatch")
        require(outcome["block_date"] == row[E + "outcome_partition_date"] == DATE,
                "Wrong outcome date")
        require(outcome["block_hash"] == outcome["executed_in_block_hash"]
                == row[E + "execution_block_observations.block_hash"] == source["block_hash"]
                and str(outcome["block_height"]) == row[E + "execution_block_observations.block_height"]
                and outcome["block_height"] == source["block_height"]
                and outcome["chunk_hash"] == source["chunk_hash"]
                and outcome["shard_id"] == source["shard_id"], "Block/chunk identity mismatch")
        require(timestamp(outcome["block_timestamp_utc"])
                == timestamp(row[E + "execution_block_observations.block_timestamp_utc"])
                == timestamp(row[E + "outcome_record_timestamp_utc"]), "Outcome timestamps disagree")
        require(all(v is None for k, v in row.items() if k.startswith(T)),
                "Unexpected origin evidence; decoder supports this export's unresolved origins only")
        require(row["transfer_record.initial_origin_check"]
                == "NO_INITIAL_TX_MATCH_DESCENDANT_OR_BOUNDARY_OR_COVERAGE_UNRESOLVED",
                "Unexpected origin check")
        require(row["transfer_record.outcome_check"]
                == "UNIQUE_SAME_DAY_OUTCOME_OBSERVATION_STATUS_RETAINED",
                "Unexpected outcome check")
        require(row["transfer_record.transfer_amount_yoctonear"] is None
                and row["transfer_record.transfer_amount_near"] is None,
                "Expected the original export's unavailable decoded amounts")
        require(row["transfer_record.observed_args_json_type"] == "string", "Args encoding changed")
        amount = deposit(row, source)
        observed["selected_action_rows"] += 1
        observed["missing_same_day_initial_tx_matches"] += 1
        decoded.append({
            "source_export_row_index": index, "economic_classification": "UNCLASSIFIED_TRANSFER",
            "observation_date": DATE, "receipt_id": key[0], "action_index": key[1],
            "block_height": source["block_height"], "block_hash": source["block_hash"],
            "block_timestamp_nanoseconds": source["block_timestamp"],
            "block_timestamp_utc": source["block_timestamp_utc"],
            "chunk_hash": source["chunk_hash"], "shard_id": source["shard_id"],
            "predecessor_account_id": source["receipt_predecessor_account_id"],
            "receiver_account_id": ACCOUNT, "receipt_signer_account_id": source["signer_account_id"],
            "receipt_signer_public_key": source["signer_public_key"],
            "is_delegate_action": source["is_delegate_action"],
            "raw_args_json": row[A + "raw_args_json"], "raw_args_scalar_text": source["args"],
            "amount_yoctonear": amount, "amount_near": near(int(amount)),
            "amount_validation": "OBSERVED_NESTED_JSON_EXACT_DECIMAL_STRING_U128",
            "execution_status": outcome["status"],
            "child_receipt_ids": [x["element"] for x in outcome["outcome_receipt_ids"]["list"]],
            "logs": outcome["logs"], "originating_transaction": None,
            "initial_origin_check": row["transfer_record.initial_origin_check"],
        })
    observed["distinct_selected_receipt_ids"] = len({r["receipt_id"] for r in decoded})
    for field in ("selected_action_rows", "distinct_selected_receipt_ids", "unavailable_or_invalid_action_rows",
                  "missing_same_day_outcome_matches", "actions_with_duplicate_outcome_matches",
                  "missing_same_day_initial_tx_matches", "actions_with_duplicate_initial_tx_matches",
                  "unavailable_raw_args_rows"):
        require(count(summary["summary_record.c." + field]) == observed[field],
                f"Summary/detail diagnostic mismatch: {field}")
    require(count(summary["summary_record.s.unavailable_selector_rows"]) == 0,
            "Selection is partial or unavailable")
    require(count(summary["summary_record.unavailable_transfer_amount_rows"]) == len(decoded)
            and summary["summary_record.total_transfer_amount_yoctonear"] is None
            and summary["summary_record.total_transfer_amount_near"] is None,
            "Original amount-availability diagnostics disagree")
    require(count(summary["summary_record.s.observed_action_partition_rows"])
            >= count(summary["summary_record.s.observed_partition_transfer_rows"]) >= len(decoded),
            "Partition diagnostics disagree")
    for field in ("observed_outcome_partition_rows", "observed_transaction_partition_rows", "observed_block_partition_rows"):
        require(count(summary["summary_record." + field]) > 0, "Unavailable lookup partition")
    return decoded


def report(source=SOURCE):
    source = source.resolve()
    raw = source.read_bytes()
    rows = validate_rows(decode(raw))
    total = sum(int(r["amount_yoctonear"]) for r in rows)
    return {
        "source": {**fingerprint(source), "sha256": hashlib.sha256(raw).hexdigest()},
        "derivation": {"script": fingerprint(Path(__file__).resolve()),
                       "method": "Parse dotted result rows and both JSON argument layers; require agreement with source-row JSON; validate decimal strings as u128; sum integers and format with 24 decimals."},
        "summary": {"transfer_rows": len(rows), "amount_yoctonear": str(total), "amount_near": near(total)},
        "limitations": ["UNCLASSIFIED_TRANSFER throughout; receipt signer is not necessarily the originating transaction signer.",
                        "Amounts are saved TRANSFER deposits, not independently reconciled net wallet balance changes.",
                        "Observed-record consistency does not establish independent historical completeness.",
                        "Native-only; excludes tokens and internal Verifier balances.",
                        "No fee, principal, refund or internal-movement attribution is established."],
        "transfers": rows,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = json_bytes(report(args.source))
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"Validation stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
