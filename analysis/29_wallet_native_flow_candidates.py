"""Offline validation/decoding of SQL 45; no network or SQL execution.

Successful local receipt actions remain economically unclassified. Native action
amounts exclude tokens, internal Verifier balances and other balance adjustments.
"""

import argparse
import base64
import importlib.util
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("native_decoder", ROOT / "analysis/14_decode_frontend_native_transfers.py")
prior = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(prior)
require, decode = prior.require, prior.decode
SQL = ROOT / "sql/45_three_wallet_native_flow_candidates.sql"
SOURCE = ROOT / "results/74_three_wallet_native_flow_candidates_2026-08-24_to_2026-10-18.json"
WALLETS = ("fefundsadmin.sputnik-dao.near", "1csfundsadmin.sputnik-dao.near", "buybacks.multisignature.near")
START, END = date(2026, 8, 24), date(2026, 10, 18)
LOOKUP_START, LOOKUP_END = date(2026, 8, 23), date(2026, 10, 24)


def number(v):
    require(type(v) is int or (isinstance(v, str) and v.isascii() and v.isdigit()), "Invalid integer diagnostic")
    result = int(v)
    require(result >= 0, "Negative integer diagnostic")
    return result


def stamp(v):
    require(isinstance(v, str), "Missing timestamp")
    result = datetime.fromisoformat(v.replace(" UTC", "+00:00").replace("Z", "+00:00"))
    require(result.utcoffset() == timedelta(0), "Timestamp is not UTC")
    return result


def exact_deposit(action):
    """Observed TRANSFER shape; FC reference shape must match actual saved args.

    Return null plus a diagnostic for unsupported/invalid encodings. Duplicate
    JSON keys, unquoted numbers and u128 overflow are never accepted as amounts.
    """
    try:
        source = decode(action["source_row_json"])
        require(source.get("args") == action["raw_args_scalar_text"], "Source args disagree")
        outer = decode(action["raw_args_json"])
        require(isinstance(outer, str) and outer == source["args"], "Unestablished args outer encoding")
        args = decode(outer)
        require(isinstance(args, dict), "Args are not an object")
        kind = action["action_kind"]
        if kind == "TRANSFER":
            require(set(args) == {"deposit"}, "Transfer args shape changed")
            basis = "OBSERVED_TRANSFER_NESTED_JSON_STRING"
        elif kind == "FUNCTION_CALL":
            require(set(args) == {"deposit", "gas", "method_name", "args_base64"}, "Unverified function-call args shape")
            require(isinstance(args["gas"], str) and args["gas"].isascii() and args["gas"].isdigit()
                    and int(args["gas"]) < 2**64, "Invalid function-call gas")
            require(isinstance(args["method_name"], str) and args["method_name"]
                    and isinstance(args["args_base64"], str), "Invalid function-call fields")
            base64.b64decode(args["args_base64"], validate=True)
            basis = "REFERENCE_FUNCTION_CALL_SHAPE_CONFIRMED_IN_EXPORTED_ROW"
        else:
            return None, "OTHER_ACTION_NOT_A_DECODED_NATIVE_PAYMENT"
        text = args["deposit"]
        require(isinstance(text, str) and text.isascii() and text.isdigit()
                and 1 <= len(text) <= 39 and int(text) < 2**128, "Deposit is not an exact u128 string")
        return text, basis
    except (ValueError, TypeError, KeyError) as exc:
        return None, f"UNAVAILABLE_INVALID_OR_UNVERIFIED_ENCODING: {exc}"


def validate(raw):
    rows = decode(raw)
    require(isinstance(rows, list), "Expected JSON row array")
    grouped = defaultdict(list)
    for row in rows:
        require(isinstance(row, dict) and set(row) == {"row_kind", "record_json"}
                and row["row_kind"] in {"SUMMARY", "DAILY_CONTROL", "WALLET_CONTROL", "ACTION"}
                and isinstance(row["record_json"], str), "Unexpected outer schema")
        value = decode(row["record_json"])
        require(isinstance(value, dict), "Unexpected nested record")
        grouped[row["row_kind"]].append(value)
    require(len(grouped["SUMMARY"]) == 1, "Expected one summary")
    s = grouped["SUMMARY"][0]
    require(number(s["expected_export_rows"]) == len(rows) == len(grouped["ACTION"])+67
            and number(s["output_action_rows"]) == len(grouped["ACTION"]), "Incomplete export/count discrepancy")
    require((s["target_start"], s["target_end"], s["lookup_start"], s["lookup_end"])
            == (str(START), str(END), str(LOOKUP_START), str(LOOKUP_END)), "Unexpected date scope")
    require(s["scope"] == "NATIVE_ACTION_CANDIDATES_NOT_COMPLETE_BALANCE_OR_MULTI_ASSET_LEDGER"
            and s["coverage_basis"] == "OBSERVED_RECORDS_NOT_INDEPENDENT_COMPLETENESS", "Unexpected economic/coverage scope")
    days = {str(LOOKUP_START+timedelta(days=i)) for i in range(63)}
    daily = {r["day"]: r for r in grouped["DAILY_CONTROL"]}
    require(len(grouped["DAILY_CONTROL"]) == len(daily) == number(s["expected_lookup_days"]) == 63
            and set(daily) == days, "Missing/duplicate daily controls")
    require(number(s["observed_action_days"]) == sum(number(r["observed_action_rows"])>0 for r in daily.values())
            and number(s["unavailable_selector_rows"]) == sum(number(r["unavailable_selector_rows"]) for r in daily.values()), "Daily coverage controls disagree")
    wallet_controls = {r["account_id"]: r for r in grouped["WALLET_CONTROL"]}
    require(len(grouped["WALLET_CONTROL"]) == len(wallet_controls) == 3 and set(wallet_controls) == set(WALLETS), "Missing/duplicate wallet controls")
    action_keys = Counter((r["source_action"]["receipt_id"], r["source_action"]["action_index"]) for r in grouped["ACTION"])
    controls = Counter()
    ledger, day_counts, wallet_counts = [], Counter(), defaultdict(Counter)
    unknown = number(s["observed_action_days"]) != 63 or number(s["unavailable_selector_rows"]) > 0
    for row in grouped["ACTION"]:
        a = row["source_action"]
        require(a["predecessor"] in WALLETS or a["receiver"] in WALLETS, "Unselected wallet action")
        source = decode(a["source_row_json"])
        require(a["block_date"] == source["block_date"], "Source partition disagreement")
        for k, source_key in (("receipt_id", "receipt_id"), ("action_kind", "action_kind"),
                              ("predecessor", "receipt_predecessor_account_id"), ("receiver", "receipt_receiver_account_id"),
                              ("source_block_hash", "block_hash"), ("source_chunk_hash", "chunk_hash")):
            require(a[k] == source[source_key], "Source action identity disagreement")
        require(a["block_date"] in days, "Source date outside lookup bounds")
        day_counts[a["block_date"]] += 1
        key = (a["receipt_id"], a["action_index"])
        count = number(row["action_key_rows"]) if row["action_key_rows"] is not None else 0
        if a["receipt_id"] and a["action_index"] is not None:
            require(count >= action_keys[key], "Duplicate action diagnostic understates selected observations")
        if count != 1:
            require(row["action_check"] != "UNIQUE_OBSERVED_ACTION", "Duplicate action accepted")
        outcome = row["outcome_audit"]
        observations = [] if outcome is None else outcome["observations"]
        source_blocks = row["source_block_audit"]
        if source_blocks is not None:
            require(len(source_blocks["observations"]) == number(source_blocks["block_rows"]), "Truncated source block array")
        if outcome is not None:
            require(outcome["receipt_id"] == a["receipt_id"] and len(observations) == number(outcome["outcome_rows"]), "Truncated outcome array")
        for observed in observations:
            require(len(observed["execution_block_observations"] or []) ==
                    (number(observed["execution_block_rows"]) if observed["execution_block_rows"] is not None else 0), "Truncated execution block array")
        if outcome is None:
            expected_check = "UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN"
        elif len(observations) != 1:
            expected_check = "DUPLICATE_OUTCOMES_EXCLUDED"
        else:
            o = observations[0]
            if o["executor_account_id"] is None or o["executor_account_id"] != a["receiver"] or o["outcome_record_timestamp_utc"] is None or stamp(o["outcome_record_timestamp_utc"]).date().isoformat() != o["outcome_record_date"]:
                expected_check = "INVALID_OUTCOME_IDENTITY_OR_TIME"
            elif o["execution_block_rows"] is None or number(o["execution_block_rows"]) != 1 or number(o["execution_block_invalid_rows"]) != 0:
                expected_check = "EXECUTION_BLOCK_UNRESOLVED"
            elif o["status"] in {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID"}:
                expected_check = "SUCCESS_LOCAL_RECEIPT"
            elif o["status"] == "FAILURE":
                expected_check = "FAILED_LOCAL_RECEIPT"
            else:
                expected_check = "UNRECOGNIZED_STATUS"
        require(row["outcome_check"] == expected_check, "Missing/duplicate outcome or status assessment disagrees")
        outcome_ok = row["outcome_check"] == "SUCCESS_LOCAL_RECEIPT"
        execution_day = None
        if len(observations) == 1:
            o = observations[0]
            blocks = o["execution_block_observations"] or []
            require(len(blocks) == (number(o["execution_block_rows"]) if o["execution_block_rows"] is not None else 0), "Truncated block array")
            if outcome_ok:
                original = decode(o["source_outcome_row_json"])
                require(o["status"] in {"SUCCESS_VALUE", "SUCCESS_RECEIPT_ID"}
                        and o["executor_account_id"] == a["receiver"] and len(blocks) == 1
                        and number(o["execution_block_invalid_rows"]) == 0, "Invalid success/execution assessment")
                require(original["receipt_id"] == a["receipt_id"] and original["status"] == o["status"]
                        and original["executor_account_id"] == a["receiver"]
                        and original["executed_in_block_hash"] == o["executed_in_block_hash"] == blocks[0]["block_hash"], "Outcome source/identity disagreement")
                require(stamp(o["outcome_record_timestamp_utc"]).date().isoformat() == o["outcome_record_date"], "Outcome record date disagreement")
                require(stamp(row["execution_timestamp_utc"]) == stamp(blocks[0]["block_timestamp_utc"]), "Execution time disagreement")
                execution_day = stamp(row["execution_timestamp_utc"]).date()
        elif outcome_ok:
            raise ValueError("Missing/duplicate outcome accepted as successful")
        if row["execution_timestamp_utc"] is not None:
            execution_day = stamp(row["execution_timestamp_utc"]).date()
        expected_window = "UNRESOLVED_EXECUTION_DATE" if execution_day is None else ("IN_TARGET_WINDOW" if START <= execution_day <= END else "OUTSIDE_TARGET_WINDOW")
        require(row["execution_window"] == expected_window, "Execution window disagreement")
        movement = "SELF_MOVEMENT" if a["predecessor"] == a["receiver"] else ("BETWEEN_SELECTED_WALLETS" if a["predecessor"] in WALLETS and a["receiver"] in WALLETS else "EXTERNAL_COUNTERPARTY")
        require(row["movement_scope"] == movement, "Wallet movement classification disagreement")
        require(row["economic_classification"] == ("UNCLASSIFIED_TRANSFER" if a["action_kind"] == "TRANSFER" else "UNCLASSIFIED_ACTION_CANDIDATE"), "Unsupported economic attribution")
        eligible = row["action_check"] == "UNIQUE_OBSERVED_ACTION" and outcome_ok and expected_window == "IN_TARGET_WINDOW"
        if row["action_check"] == "UNIQUE_OBSERVED_ACTION":
            require(count == 1 and a["action_index"] is not None and number(a["action_index"]) == number(source["index_in_action_receipt"]), "Invalid accepted action key")
            b = row["source_block_audit"]
            require(b is not None and number(b["block_rows"]) == len(b["observations"]) == 1
                    and number(b["invalid_block_rows"]) == 0, "Invalid source block assessment")
            require(b["observations"][0]["block_hash"] == a["source_block_hash"]
                    and number(b["observations"][0]["block_height"]) == number(a["source_block_height"])
                    and stamp(b["observations"][0]["block_timestamp_utc"]) == stamp(a["source_timestamp_utc"]), "Source block/time disagreement")
        amount, amount_basis = exact_deposit(a)
        accepted = eligible and amount is not None
        relevant = expected_window != "OUTSIDE_TARGET_WINDOW"
        if relevant and (row["action_check"] != "UNIQUE_OBSERVED_ACTION"
                         or row["outcome_check"] not in {"SUCCESS_LOCAL_RECEIPT", "FAILED_LOCAL_RECEIPT"}
                         or expected_window == "UNRESOLVED_EXECUTION_DATE"
                         or (outcome_ok and a["action_kind"] in {"DELEGATE_ACTION", "DELETE_ACCOUNT", "UNKNOWN"})
                         or (outcome_ok and a["action_kind"] in {"TRANSFER", "FUNCTION_CALL"} and amount is None)):
            unknown = True
        controls["transfer_action_rows"] += a["action_kind"] == "TRANSFER"
        controls["function_call_rows"] += a["action_kind"] == "FUNCTION_CALL"
        controls["excluded_action_rows"] += row["action_check"] != "UNIQUE_OBSERVED_ACTION"
        controls["duplicate_outcome_action_rows"] += row["outcome_check"] == "DUPLICATE_OUTCOMES_EXCLUDED"
        controls["unmatched_outcome_action_rows"] += row["outcome_check"] == "UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN"
        controls["failed_action_rows"] += row["outcome_check"] == "FAILED_LOCAL_RECEIPT"
        controls["successful_local_action_candidates"] += eligible
        controls["internal_movement_rows"] += movement == "BETWEEN_SELECTED_WALLETS"
        controls["unresolved_execution_date_rows"] += expected_window == "UNRESOLVED_EXECUTION_DATE"
        controls["outside_execution_window_rows"] += expected_window == "OUTSIDE_TARGET_WINDOW"
        for wallet in WALLETS:
            if wallet in {a["predecessor"], a["receiver"]}:
                w = wallet_counts[wallet]
                w["selected_rows"] += 1
                w["successful_local_action_candidates"] += eligible
                w["internal_movement_rows"] += movement == "BETWEEN_SELECTED_WALLETS"
                if accepted:
                    w["inflow_yocto"] += int(amount) if a["receiver"] == wallet else 0
                    w["outflow_yocto"] += int(amount) if a["predecessor"] == wallet else 0
        ledger.append({"receipt_id": a["receipt_id"], "action_index": a["action_index"], "action_kind": a["action_kind"],
                       "predecessor": a["predecessor"], "receiver": a["receiver"], "execution_timestamp_utc": row["execution_timestamp_utc"],
                       "source_block_hash": a["source_block_hash"], "source_block_height": a["source_block_height"],
                       "source_timestamp_utc": a["source_timestamp_utc"], "source_chunk_hash": a["source_chunk_hash"],
                       "source_shard_id": source.get("shard_id"), "signer_account_id": source.get("signer_account_id"),
                       "delegation_flag": source.get("is_delegate_action"), "raw_args_json": a["raw_args_json"],
                       "execution_block_hash": observations[0]["executed_in_block_hash"] if len(observations) == 1 else None,
                       "execution_block_height": observations[0]["execution_block_observations"][0]["block_height"]
                       if len(observations) == 1 and len(observations[0]["execution_block_observations"] or []) == 1 else None,
                       "origin_transaction_hash": None,
                       "execution_check": row["outcome_check"], "execution_window": expected_window,
                       "amount_yocto": amount, "amount_near": prior.near(int(amount)) if amount is not None else None,
                       "amount_basis": amount_basis, "accepted_local_native_amount": accepted, "movement_scope": movement,
                       "economic_classification": "UNCLASSIFIED_TRANSFER" if a["action_kind"] == "TRANSFER" else "UNCLASSIFIED_ACTION_CANDIDATE"})
    for key in ("transfer_action_rows", "function_call_rows", "excluded_action_rows", "duplicate_outcome_action_rows",
                "unmatched_outcome_action_rows", "failed_action_rows", "successful_local_action_candidates",
                "internal_movement_rows", "unresolved_execution_date_rows", "outside_execution_window_rows"):
        require(number(s[key]) == controls[key], f"Summary diagnostic disagrees: {key}")
    require(sum(number(r["selected_action_rows"]) for r in daily.values()) == len(ledger)
            and all(number(daily[k]["selected_action_rows"]) == day_counts[k] for k in daily), "Daily action counts disagree")
    for wallet in WALLETS:
        for key in ("selected_rows", "successful_local_action_candidates", "internal_movement_rows"):
            require(number(wallet_controls[wallet][key]) == wallet_counts[wallet][key], "Wallet counts disagree")
    wallets = []
    for wallet in WALLETS:
        c = wallet_counts[wallet]
        wallets.append({"account_id": wallet, "valid_inflow_subtotal_yocto": str(c["inflow_yocto"]),
                        "valid_outflow_subtotal_yocto": str(c["outflow_yocto"]),
                        "observed_action_layer_net_yocto": str(c["inflow_yocto"]-c["outflow_yocto"]) if not unknown else None,
                        "complete_native_balance_net_yocto": None})
    accepted = [r for r in ledger if r["accepted_local_native_amount"]]
    external_in = sum(int(r["amount_yocto"]) for r in accepted if r["movement_scope"] == "EXTERNAL_COUNTERPARTY" and r["receiver"] in WALLETS)
    external_out = sum(int(r["amount_yocto"]) for r in accepted if r["movement_scope"] == "EXTERNAL_COUNTERPARTY" and r["predecessor"] in WALLETS)
    internal = [r for r in accepted if r["movement_scope"] == "BETWEEN_SELECTED_WALLETS"]
    return {"status": "OBSERVED_NATIVE_ACTION_LAYER_VALIDATED_NOT_REVENUE_OR_BALANCE_RECONCILIATION",
            "export_rows": len(rows), "source_summary": s, "action_layer_coverage_unresolved": unknown,
            "wallets": wallets, "actions": ledger,
            "group_valid_external_inflow_subtotal_yocto": str(external_in),
            "group_valid_external_outflow_subtotal_yocto": str(external_out),
            "group_observed_external_net_yocto": str(external_in-external_out) if not unknown else None,
            "accepted_between_wallet_action_count": len(internal),
            "between_wallet_amount_subtotal_counted_once_yocto": str(sum(int(r["amount_yocto"]) for r in internal)),
            "verified_revenue_yocto": None, "verified_purchase_yocto": None, "verified_buyback_yocto": None,
            "verified_customer_principal_yocto": None, "verified_solver_settlement_yocto": None, "verified_refund_yocto": None,
            "limitations": ["Bounded source lookback/tail; no independent ingestion completeness",
                            "Function-call deposits decoded only when the full reference shape is observed",
                            "Delegate envelopes remain unexpanded; receipt funding/escrow timing is not account-debit timing",
                            "Between-wallet/self movements are not added twice to group external flows",
                            "Local receipt success is not complete-chain settlement",
                            "Native actions exclude FT/MT assets and other account balance adjustments"]}


def saved_transfer_control(report):
    """Compare the same-day native receipt/action evidence, without new tracing."""
    reference = prior.report()
    saved_path = ROOT / "results/48_frontend_wallet_native_transfers_decoded_2026-09-23.json"
    require(prior.json_bytes(reference) == saved_path.read_bytes(), "Saved result 48 no longer reproduces")
    expected = {(r["receipt_id"], r["action_index"]): r for r in reference["transfers"]}
    actual = defaultdict(list)
    for row in report["actions"]:
        if row["action_kind"] == "TRANSFER" and row["receiver"] == prior.ACCOUNT and row["execution_timestamp_utc"] is not None and stamp(row["execution_timestamp_utc"]).date().isoformat() == prior.DATE:
            actual[(row["receipt_id"], row["action_index"])].append(row)
    mismatches = [list(key) for key, old in expected.items() if key in actual and
                  (len(actual[key]) != 1 or not actual[key][0]["accepted_local_native_amount"]
                   or actual[key][0]["amount_yocto"] is None or int(actual[key][0]["amount_yocto"]) != int(old["amount_yoctonear"])
                   or actual[key][0]["predecessor"] != old["predecessor_account_id"]
                   or actual[key][0]["receiver"] != old["receiver_account_id"]
                   or actual[key][0]["execution_block_hash"] != old["block_hash"])]
    missing = [list(k) for k in expected if k not in actual]
    extra = [list(k) for k in actual if k not in expected]
    return {"status": "MATCHED_SAVED_22_TRANSFER_CONTROL" if not (missing or extra or mismatches) else "SAVED_CONTROL_DIFFERENCE_REQUIRES_REVIEW",
            "expected_actions": len(expected), "missing_keys": missing, "additional_keys": extra,
            "amount_identity_or_assessment_mismatches": mismatches, "source": prior.fingerprint(saved_path)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate(args.source.read_bytes())
        report["saved_sep23_control"] = saved_transfer_control(report)
        report["saved_control_matches"] = report["saved_sep23_control"]["status"] == "MATCHED_SAVED_22_TRANSFER_CONTROL"
        if not report["saved_control_matches"]:
            report["action_layer_coverage_unresolved"] = True
            report["group_observed_external_net_yocto"] = None
            for wallet in report["wallets"]:
                wallet["observed_action_layer_net_yocto"] = None
        report["source"] = prior.fingerprint(args.source)
        report["derivation"] = {str(p.relative_to(ROOT)): prior.fingerprint(p) for p in (SQL, Path(__file__), Path(prior.__file__))}
        raw = prior.json_bytes(report)
        if args.output:
            with args.output.open("xb") as handle:
                handle.write(raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Stopped: {exc}. No source requests made.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
