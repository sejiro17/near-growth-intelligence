import csv
import json
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PERIOD = "2026-08-24_to_2026-10-18"

SOURCE = RESULTS / f"25_growth_account_failure_sample_{PERIOD}.csv"
OUTPUT = RESULTS / f"26_growth_account_failure_details_{PERIOD}.json"

ENDPOINT = "https://archival-rpc.mainnet.fastnear.com"
METHOD = "EXPERIMENTAL_tx_status"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def extract_execution_errors(value):
    errors = []

    if isinstance(value, dict):
        for key, item in value.items():
            if key == "ExecutionError" and isinstance(item, str):
                errors.append(item)
            else:
                errors.extend(extract_execution_errors(item))
    elif isinstance(value, list):
        for item in value:
            errors.extend(extract_execution_errors(item))

    return errors


def validate_response(data, sample):
    if not isinstance(data, dict) or "error" in data:
        raise ValueError("Response contains an RPC error or invalid data.")

    result = data.get("result")
    if not isinstance(result, dict):
        raise ValueError("Missing transaction result.")

    transaction = result.get("transaction", {})
    if (
        transaction.get("hash") != sample["transaction_hash"]
        or transaction.get("signer_id") != sample["signer_account_id"]
    ):
        raise ValueError("Returned transaction identity does not match.")

    matches = [
        item
        for item in result.get("receipts_outcome", [])
        if item.get("id") == sample["receipt_id"]
    ]

    if len(matches) != 1:
        raise ValueError(
            f"Expected one matching receipt; found {len(matches)}."
        )

    receipt = matches[0]
    outcome = receipt.get("outcome", {})

    if outcome.get("executor_id") != sample["executor_account_id"]:
        raise ValueError("Returned executor does not match the sample.")

    status = outcome.get("status")
    if not isinstance(status, dict) or "Failure" not in status:
        raise ValueError("Returned receipt does not have Failure status.")

    return {
        "receipt_id": receipt["id"],
        "block_hash": receipt.get("block_hash"),
        "executor_id": outcome.get("executor_id"),
        "status": status,
        "logs": outcome.get("logs"),
        "execution_errors": extract_execution_errors(status),
    }


def fetch_details(sample):
    payload = {
        "jsonrpc": "2.0",
        "id": sample["receipt_id"],
        "method": METHOD,
        "params": [
            sample["transaction_hash"],
            sample["signer_account_id"],
        ],
    }

    record = {
        "sample": sample,
        "rpc_endpoint": ENDPOINT,
        "requested_at_utc": utc_now(),
        "request": payload,
        "retrieval_status": "UNRESOLVED",
    }

    try:
        response = subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--fail-with-body",
                "--max-time",
                "30",
                ENDPOINT,
                "-H",
                "Content-Type: application/json",
                "--data-binary",
                "@-",
            ],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=35,
        )

        record["response_received_at_utc"] = utc_now()

        if response.returncode != 0:
            record["retrieval_status"] = "HTTP_OR_TRANSPORT_ERROR"
            record["error"] = response.stderr.strip()
            record["response_body"] = response.stdout
            return record

        data = json.loads(response.stdout)
        record["rpc_response"] = data

        if isinstance(data, dict) and "error" in data:
            record["retrieval_status"] = "RPC_ERROR"
            return record

        record["matched_receipt"] = validate_response(data, sample)
        record["retrieval_status"] = "VALIDATED_FAILURE"

    except (
        OSError,
        subprocess.TimeoutExpired,
        ValueError,
        TypeError,
        AttributeError,
    ) as error:
        record["retrieval_status"] = "RETRIEVAL_OR_VALIDATION_ERROR"
        record["error"] = str(error)

    return record


def save_results(document):
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(OUTPUT)


def print_summary(document):
    summary = Counter(
        record["retrieval_status"]
        for record in document["records"]
    )

    print("\nRetrieval summary:")
    for status, count in summary.items():
        print(f"  {status}: {count}")

    print(f"\nResults file: {OUTPUT}")


def main():
    with SOURCE.open(newline="", encoding="utf-8-sig") as handle:
        samples = list(csv.DictReader(handle))

    if len(samples) != 18:
        raise ValueError(f"Expected 18 sample rows; found {len(samples)}.")

    samples_by_id = {row["receipt_id"]: row for row in samples}
    if len(samples_by_id) != len(samples):
        raise ValueError("Duplicate sampled receipt identifiers.")

    if any(
        row["status"] != "FAILURE"
        or row["matching_outcome_rows"] != "1"
        for row in samples
    ):
        raise ValueError("Unexpected sample status or matching count.")

    if OUTPUT.exists():
        document = json.loads(OUTPUT.read_text(encoding="utf-8"))

        if (
            document.get("source_file") != SOURCE.name
            or document.get("sample_size") != len(samples)
            or not isinstance(document.get("records"), list)
        ):
            raise ValueError("Saved results do not match the source sample.")
    else:
        document = {
            "source_file": SOURCE.name,
            "rpc_endpoint": ENDPOINT,
            "rpc_method": METHOD,
            "started_at_utc": utc_now(),
            "sample_size": len(samples),
            "scope": (
                "Diagnostic sample of failed initial receipts. "
                "Results do not estimate population error frequencies."
            ),
            "records": [],
        }

    records_by_id = {}

    for record in document["records"]:
        sample = record.get("sample", {})
        receipt_id = sample.get("receipt_id")

        if receipt_id not in samples_by_id:
            raise ValueError("Saved record is absent from the source sample.")

        if receipt_id in records_by_id:
            raise ValueError("Duplicate receipt in saved results.")

        if sample != samples_by_id[receipt_id]:
            raise ValueError(f"Saved sample differs for {receipt_id}.")

        if record.get("retrieval_status") == "VALIDATED_FAILURE":
            checked = validate_response(record.get("rpc_response"), sample)

            if checked != record.get("matched_receipt"):
                raise ValueError(
                    f"Saved receipt summary differs from its response: "
                    f"{receipt_id}."
                )

        records_by_id[receipt_id] = record

    pending = [
        sample
        for sample in samples
        if records_by_id.get(sample["receipt_id"], {}).get(
            "retrieval_status"
        ) != "VALIDATED_FAILURE"
    ]

    skipped = len(samples) - len(pending)
    print(f"Validated saved responses: {skipped}/{len(samples)}.")

    if not pending:
        print("All 18 records are complete. No RPC requests made.")
        print("Saved results were left unchanged.")
        print_summary(document)
        return

    document["last_run_started_at_utc"] = utc_now()
    document["last_run_rpc_endpoint"] = ENDPOINT

    for number, sample in enumerate(pending, start=1):
        receipt_id = sample["receipt_id"]
        previous = records_by_id.get(receipt_id)
        updated = fetch_details(sample)

        if previous is not None:
            old_attempt = {
                key: value
                for key, value in previous.items()
                if key != "previous_attempts"
            }
            old_attempt.setdefault(
                "rpc_endpoint",
                document.get("rpc_endpoint"),
            )
            updated["previous_attempts"] = (
                previous.get("previous_attempts", []) + [old_attempt]
            )

        records_by_id[receipt_id] = updated
        document["records"] = [
            records_by_id[row["receipt_id"]]
            for row in samples
            if row["receipt_id"] in records_by_id
        ]
        document["retrieval_summary"] = dict(
            Counter(
                record["retrieval_status"]
                for record in document["records"]
            )
        )
        save_results(document)

        print(
            f"{number}/{len(pending)} "
            f"{receipt_id}: {updated['retrieval_status']}",
            flush=True,
        )

        for error in updated.get("matched_receipt", {}).get(
            "execution_errors", []
        ):
            print(f"  {error}", flush=True)

        if updated["retrieval_status"] != "VALIDATED_FAILURE":
            print("Stopping after an unsuccessful lookup; progress is saved.")
            break

        if number < len(pending):
            time.sleep(3)

    document["last_run_finished_at_utc"] = utc_now()

    if (
        len(document["records"]) == len(samples)
        and all(
            record["retrieval_status"] == "VALIDATED_FAILURE"
            for record in document["records"]
        )
    ):
        document.setdefault("completed_at_utc", utc_now())

    save_results(document)
    print_summary(document)


if __name__ == "__main__":
    main()