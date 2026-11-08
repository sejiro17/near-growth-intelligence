"""Offline SQL-45 decoding and count/overlap safeguards; no source requests."""
import copy
import importlib.util
import re
import unittest
from collections import Counter
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("wallets", ROOT / "analysis/29_wallet_native_flow_candidates.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class WalletNativeFlowTests(unittest.TestCase):
    def action(self):
        old = next(r for r in m.decode(m.prior.SOURCE.read_bytes()) if r.get("row_kind") == "TRANSFER")
        source = m.decode(old[m.prior.A+"source_row_json"])
        outcome = m.decode(old[m.prior.E+"source_outcome_row_json"])
        block = {"block_hash": source["block_hash"], "block_height": source["block_height"],
                 "block_timestamp_utc": source["block_timestamp_utc"], "block_timestamp_nanosec": source["block_timestamp"]}
        a = {"block_date": source["block_date"], "receipt_id": source["receipt_id"], "action_kind": "TRANSFER",
             "predecessor": source["receipt_predecessor_account_id"], "receiver": source["receipt_receiver_account_id"],
             "source_row_json": old[m.prior.A+"source_row_json"], "action_index": source["index_in_action_receipt"],
             "source_block_hash": source["block_hash"], "source_block_height": source["block_height"],
             "source_chunk_hash": source["chunk_hash"], "source_timestamp_utc": source["block_timestamp_utc"],
             "raw_args_json": old[m.prior.A+"raw_args_json"], "raw_args_scalar_text": source["args"]}
        return {"source_action": a, "action_key_rows": 1,
                "source_block_audit": {"block_rows": 1, "invalid_block_rows": 0, "observations": [block]},
                "outcome_audit": {"receipt_id": a["receipt_id"], "outcome_rows": 1, "observations": [{
                    "outcome_record_date": source["block_date"], "status": "SUCCESS_VALUE", "executor_account_id": a["receiver"],
                    "outcome_record_timestamp_utc": source["block_timestamp_utc"], "executed_in_block_hash": source["block_hash"],
                    "source_outcome_row_json": old[m.prior.E+"source_outcome_row_json"], "execution_block_rows": 1,
                    "execution_block_invalid_rows": 0, "execution_block_observations": [block]}]},
                "action_check": "UNIQUE_OBSERVED_ACTION", "outcome_check": "SUCCESS_LOCAL_RECEIPT",
                "execution_timestamp_utc": source["block_timestamp_utc"], "execution_window": "IN_TARGET_WINDOW",
                "movement_scope": "EXTERNAL_COUNTERPARTY", "economic_classification": "UNCLASSIFIED_TRANSFER"}

    def export(self, actions):
        kinds = Counter(a["source_action"]["action_kind"] for a in actions)
        eligible = lambda a: a["action_check"] == "UNIQUE_OBSERVED_ACTION" and a["outcome_check"] == "SUCCESS_LOCAL_RECEIPT" and a["execution_window"] == "IN_TARGET_WINDOW"
        summary = {"target_start": str(m.START), "target_end": str(m.END), "lookup_start": str(m.LOOKUP_START), "lookup_end": str(m.LOOKUP_END),
                   "scope": "NATIVE_ACTION_CANDIDATES_NOT_COMPLETE_BALANCE_OR_MULTI_ASSET_LEDGER", "coverage_basis": "OBSERVED_RECORDS_NOT_INDEPENDENT_COMPLETENESS",
                   "expected_export_rows": len(actions)+67, "output_action_rows": len(actions), "expected_lookup_days": 63,
                   "observed_action_days": 63, "unavailable_selector_rows": 0, "transfer_action_rows": kinds["TRANSFER"],
                   "function_call_rows": kinds["FUNCTION_CALL"], "excluded_action_rows": sum(a["action_check"] != "UNIQUE_OBSERVED_ACTION" for a in actions),
                   "duplicate_outcome_action_rows": sum(a["outcome_check"] == "DUPLICATE_OUTCOMES_EXCLUDED" for a in actions),
                   "unmatched_outcome_action_rows": sum(a["outcome_check"] == "UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN" for a in actions),
                   "failed_action_rows": sum(a["outcome_check"] == "FAILED_LOCAL_RECEIPT" for a in actions),
                   "successful_local_action_candidates": sum(map(eligible,actions)),
                   "internal_movement_rows": sum(a["movement_scope"] == "BETWEEN_SELECTED_WALLETS" for a in actions),
                   "unresolved_execution_date_rows": sum(a["execution_window"] == "UNRESOLVED_EXECUTION_DATE" for a in actions),
                   "outside_execution_window_rows": sum(a["execution_window"] == "OUTSIDE_TARGET_WINDOW" for a in actions)}
        rows = [("SUMMARY",summary)]
        for i in range(63):
            day=str(m.LOOKUP_START+timedelta(days=i));rows.append(("DAILY_CONTROL",{"day":day,"observed_action_rows":1,"unavailable_selector_rows":0,
                "selected_action_rows":sum(a["source_action"]["block_date"]==day for a in actions)}))
        for w in m.WALLETS:
            selected=[a for a in actions if w in {a["source_action"]["predecessor"],a["source_action"]["receiver"]}]
            rows.append(("WALLET_CONTROL",{"account_id":w,"selected_rows":len(selected),"successful_local_action_candidates":sum(map(eligible,selected)),
                "internal_movement_rows":sum(a["movement_scope"]=="BETWEEN_SELECTED_WALLETS" for a in selected)}))
        rows += [("ACTION",a) for a in actions]
        return m.prior.json_bytes([{"row_kind":kind,"record_json":m.prior.json_bytes(r).decode()} for kind,r in rows])

    def test_observed_transfer_encoding_exact_and_empty_export(self):
        a=self.action();value,basis=m.exact_deposit(a["source_action"])
        self.assertEqual(value,m.decode(a["source_action"]["raw_args_scalar_text"])["deposit"])
        r=m.validate(self.export([a]));self.assertTrue(r["actions"][0]["accepted_local_native_amount"])
        self.assertIsNone(r["verified_revenue_yocto"])
        self.assertIsNone(r["wallets"][0]["complete_native_balance_net_yocto"])
        self.assertEqual(m.validate(self.export([]))["actions"],[])
        comparison=m.saved_transfer_control(r)
        self.assertEqual(comparison["expected_actions"],22)
        self.assertEqual(len(comparison["missing_keys"]),21)

    def test_duplicate_keys_unquoted_values_overflow_and_function_call_reference(self):
        a=self.action()["source_action"]
        for args in ('{"deposit":"1","deposit":"2"}','{"deposit":1}','{"deposit":"NaN"}', '{"deposit":"'+str(2**128)+'"}'):
            bad=copy.deepcopy(a);s=m.decode(bad["source_row_json"]);s["args"]=args
            bad.update(raw_args_scalar_text=args,raw_args_json=m.prior.json_bytes(args).decode(),source_row_json=m.prior.json_bytes(s).decode())
            self.assertIsNone(m.exact_deposit(bad)[0])
        args=m.prior.json_bytes({"deposit":"1000000000000000000000001","gas":"1000","method_name":"method","args_base64":"e30="}).decode()
        s=m.decode(a["source_row_json"]);s.update(args=args,action_kind="FUNCTION_CALL")
        a.update(action_kind="FUNCTION_CALL",raw_args_scalar_text=args,raw_args_json=m.prior.json_bytes(args).decode(),source_row_json=m.prior.json_bytes(s).decode())
        self.assertEqual(m.exact_deposit(a)[0],"1000000000000000000000001")

    def test_missing_duplicate_dates_and_export_truncation(self):
        rows=m.decode(self.export([self.action()]))
        with self.assertRaisesRegex(ValueError,"Incomplete"):m.validate(m.prior.json_bytes(rows[:-1]))
        daily=[r for r in rows if r["row_kind"]=="DAILY_CONTROL"];daily[1]["record_json"]=daily[0]["record_json"]
        with self.assertRaisesRegex(ValueError,"daily"):m.validate(m.prior.json_bytes(rows))

    def test_duplicate_outcomes_or_actions_never_enter_amount_totals(self):
        a=self.action();a["outcome_audit"]["observations"]*=2;a["outcome_audit"]["outcome_rows"]=2
        with self.assertRaisesRegex(ValueError,"duplicate outcome"):m.validate(self.export([a]))
        a["outcome_check"]="DUPLICATE_OUTCOMES_EXCLUDED"
        r=m.validate(self.export([a]));self.assertFalse(r["actions"][0]["accepted_local_native_amount"]);self.assertTrue(r["action_layer_coverage_unresolved"])
        a=self.action()
        with self.assertRaisesRegex(ValueError,"Duplicate action"):m.validate(self.export([a,copy.deepcopy(a)]))

    def test_missing_evidence_stays_null_and_internal_wallet_legs_cancel(self):
        a=self.action();a.update(outcome_audit=None,outcome_check="UNMATCHED_OUTCOME_BOUNDARY_OR_COVERAGE_UNKNOWN",execution_timestamp_utc=None,execution_window="UNRESOLVED_EXECUTION_DATE")
        r=m.validate(self.export([a]));self.assertIsNone(r["wallets"][0]["observed_action_layer_net_yocto"])
        a=self.action();a["source_action"]["predecessor"]=m.WALLETS[1]
        s=m.decode(a["source_action"]["source_row_json"]);s["receipt_predecessor_account_id"]=m.WALLETS[1];a["source_action"]["source_row_json"]=m.prior.json_bytes(s).decode()
        a["movement_scope"]="BETWEEN_SELECTED_WALLETS"
        r=m.validate(self.export([a]));self.assertEqual(sum(int(w["observed_action_layer_net_yocto"]) for w in r["wallets"]),0)

    def test_static_sql_direct_partitions_and_no_origin_substitute_or_monetary_cast(self):
        sql=re.sub(r'/\*.*?\*/','',m.SQL.read_text(),flags=re.S)
        reads=re.findall(r'FROM `bigquery-public-data.crypto_near_mainnet_us\.(\w+)`([^;]*?)(?=\n\),)',sql,re.S)
        self.assertEqual([r[0] for r in reads],["receipt_actions","receipt_actions","execution_outcomes","blocks"])
        for _,segment in reads:self.assertRegex(segment,r"WHERE (?:\w+\.)?block_date BETWEEN DATE '2026-08-23' AND DATE '2026-10-24'")
        self.assertNotIn('converted_into_receipt_id',sql);self.assertNotIn('LIMIT ',sql.upper())
        self.assertNotRegex(sql.upper(),r'\b(CREATE|INSERT|UPDATE|DELETE|MERGE|EXPORT)\b')


if __name__=="__main__":unittest.main()
