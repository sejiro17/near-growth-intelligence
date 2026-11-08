"""Bounded selection, identity gates and stop behavior; no live network."""

import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("jars", ROOT/"analysis/49_trace_sweat_jars.py")
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class JarsTraceTests(unittest.TestCase):
    def candidate(self):
        old = m.c.decode((ROOT/"results/96_sweat_relayer_attribution_trace_2026-09-23.json").read_bytes())
        header = m.c.decode((ROOT/"results/97_priority4_attribution_coverage.json").read_bytes())["case_study"]["submission_block"]
        return {"transaction_hash": old["transaction_hash"], "account_id": m.RECEIVER,
                "is_receiver": True, "tx_block_height": header["height"], "tx_index": 0,
                "tx_block_timestamp": header["timestamp_nanosec"]}

    def test_receiver_day_cap_and_no_pagination(self):
        row = self.candidate()
        self.assertEqual(m.history_identity({"account_txs": [row]})[0], row)
        payload = m.history_request()
        self.assertEqual(payload["limit"], 5)
        self.assertNotIn("resume_token", payload)
        self.assertTrue(payload["is_receiver"])
        for rows in [[], [row]*6, [row, row]]:
            with self.assertRaises(ValueError):
                m.history_identity({"account_txs": rows})
        for key, value in [("account_id", "wrong.near"), ("is_receiver", False),
                           ("tx_block_timestamp", "0"), ("tx_block_height", m.w.day_bounds()[1])]:
            bad = {**row, key: value}
            with self.assertRaises(ValueError):
                m.history_identity({"account_txs": [bad]})

    def test_selection_requires_both_roles_and_complete_batch(self):
        row = self.candidate()
        tx = {"hash": row["transaction_hash"], "signer_id": m.SIGNER, "receiver_id": m.RECEIVER,
              "actions": [{"FunctionCall": {"method_name": "test"}}]}
        result = {"transactions": [{"transaction": tx}]}
        self.assertEqual(m.select(result, [row])[0], row)
        for key in ["signer_id", "receiver_id"]:
            bad = copy.deepcopy(result)
            bad["transactions"][0]["transaction"][key] = "other.near"
            with self.assertRaisesRegex(ValueError, "No Sweat-to-jars"):
                m.select(bad, [row])
        with self.assertRaises(ValueError):
            m.select({"transactions": []}, [row])

    def test_canonical_identity_and_failure_is_not_filtered_out(self):
        row = self.candidate()
        tx = {"hash": row["transaction_hash"], "signer_id": m.SIGNER, "receiver_id": m.RECEIVER, "actions": ["Transfer"]}
        rid = m.c.TARGETS["A"]["hash"]
        result = {"final_execution_status": "FINAL", "transaction": tx,
                  "transaction_outcome": {"id": tx["hash"], "block_hash": m.c.TARGETS["B"]["hash"],
                    "outcome": {"executor_id": m.SIGNER, "status": {"SuccessReceiptId": rid}, "receipt_ids": [rid]}},
                  "receipts_outcome": [{"id": rid, "outcome": {"executor_id": m.RECEIVER, "status": {"Failure": {"error": "test"}}}}],
                  "receipts": [{"receipt_id": rid, "receiver_id": m.RECEIVER}]}
        self.assertIn("Failure", m.status_gate(result, row, tx)["initial_outcome_status"])
        bad = copy.deepcopy(result)
        bad["transaction"]["receiver_id"] = "other.near"
        with self.assertRaises(ValueError):
            m.status_gate(bad, row, tx)
        bad = copy.deepcopy(result)
        bad["receipts_outcome"] *= 2
        with self.assertRaises(ValueError):
            m.status_gate(bad, row, tx)

    def test_error_stops_collect_without_next_stage(self):
        with patch.object(m, "stage_inputs", return_value=(m.w.HISTORY_ENDPOINT, {}, lambda _: None)), \
             patch.object(m, "reuse_existing", return_value=None), \
             patch.object(m.w, "capture", side_effect=ValueError("HTTP error")) as capture, \
             patch.object(m, "OUTPUT", ROOT/"results/__unused_jars_test"), \
             patch.object(Path, "mkdir"), patch.object(m.c, "write_new"):
            with self.assertRaisesRegex(ValueError, "HTTP error"):
                m.collect()
            self.assertEqual(capture.call_count, 1)

    def test_four_slots_and_successful_slots_are_reused(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp, patch.object(m, "OUTPUT", Path(temp)), \
             patch.object(m, "stage_inputs", return_value=(m.w.HISTORY_ENDPOINT, {}, lambda _: None)), \
             patch.object(m, "reuse_existing", return_value=None), patch.object(m, "load", return_value={}), \
             patch.object(m.w, "capture") as capture:
            def save_marker(stage, *_args, **_kwargs):
                m.c.write_new(Path(temp)/(stage+".attempt.json"), b'{}')
            capture.side_effect = save_marker
            m.collect()
            m.collect()
            self.assertEqual(capture.call_count, 4)
            self.assertEqual([c.args[0] for c in capture.call_args_list], list(m.STAGES))

    def test_raw_argument_precision_and_explicit_delegate_context(self):
        import base64
        raw = b'{"amount":"123456789012345678901234567890","fraction":0.123456789012345678901}'
        call = {"FunctionCall": {"method_name": "example", "args": base64.b64encode(raw).decode(), "deposit": "1", "gas": 100}}
        result = {"transaction": {"signer_id": m.SIGNER, "receiver_id": m.RECEIVER,
                   "actions": [{"Delegate": {"delegate_action": {"sender_id": "actor.near", "receiver_id": "target.near", "actions": [call]}}}]}, "receipts": []}
        decoded, = m.decoded_calls(result)
        self.assertEqual(decoded["receiver"], "target.near")
        self.assertEqual(decoded["predecessor"], "actor.near")
        self.assertEqual(decoded["args_utf8"], raw.decode())
        self.assertEqual(decoded["decoded_args"]["fraction"], "0.123456789012345678901")
        self.assertEqual(decoded["decoded_args"]["amount"], "123456789012345678901234567890")

    def test_saved_case_graph_charges_and_application_rejection(self):
        with patch("socket.socket.connect", side_effect=AssertionError("No source request")):
            report = m.report()
        self.assertEqual(m.c.json_bytes(report), m.ARTIFACT.read_bytes())
        self.assertEqual(report["collection"]["new_requests"], 4)
        self.assertEqual(report["collection"]["maximum_candidates"], 5)
        self.assertEqual(report["population_coverage"]["saved_destination_bucket_transactions"], 3039759)
        graph = report["returned_graph"]
        self.assertEqual(graph["network_signer"], m.SIGNER)
        self.assertEqual(graph["declared_delegate_sender_ids"], [m.RECEIVER])
        self.assertEqual(graph["coverage"]["returned_receipt_outcomes"], 8)
        self.assertTrue(graph["coverage"]["observed_graph_consistent_and_covered"])
        self.assertTrue(graph["coverage"]["all_observed_receipt_outcomes_successful"])
        self.assertEqual(sum(int(r["recorded_execution_charge_yocto"]) for r in [graph["transaction_outcome"]]+graph["receipt_outcomes"]), int(graph["recorded_transaction_and_receipt_execution_charge_yocto"]))
        behavior = report["observed_behavior"]
        self.assertFalse(behavior["booster_applied"])
        self.assertEqual(behavior["amount_base_units"], "3000000000000000000")
        self.assertEqual(behavior["callback_returns"]["ft_on_transfer"], "0")
        self.assertIsNone(behavior["verified_revenue_or_purchase"])
        self.assertIsNone(behavior["token_decimals"])


if __name__ == "__main__":
    unittest.main()
