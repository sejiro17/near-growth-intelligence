"""Audit a stopped six-state run offline; manually recover only missing states.

The original collector, frozen plan and capture directory are never modified.
An explicitly invoked recover command uses the same transport and validation.
"""

import argparse
import importlib.util
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("balance_recovery_base", ROOT / "analysis/31_wallet_historical_balances.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)
c, require = b.c, b.require
PLAN = ROOT / "results/79_three_wallet_balance_recovery_plan.json"
OUTPUT = ROOT / "results/three_wallet_native_balance_recovery_2026-08-24_to_2026-10-18"
SUFFIXES = ("request.json", "response.body", "metadata.json")


def path_text(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def evidence_integrity(directory, item):
    """Check saved bytes even when transport failed and the body is not JSON."""
    stem = item["request"]["id"]
    request = (directory / f"{stem}.request.json").read_bytes()
    response = (directory / f"{stem}.response.body").read_bytes()
    meta = c.decode((directory / f"{stem}.metadata.json").read_bytes())
    require(request == c.json_bytes(item["request"]), "Changed original request bytes")
    require(meta.get("endpoint") == c.ENDPOINT and meta.get("request_http_method") == "POST"
            and meta.get("request_path") == "/", "Changed original endpoint/method")
    require(meta.get("request_sha256") == c.sha256(request) and meta.get("response_sha256") == c.sha256(response)
            and meta.get("request_bytes") == len(request) and meta.get("response_bytes") == len(response), "Original capture checksum/length mismatch")
    require(b.m.stamp(meta["finished_at"]) >= b.m.stamp(meta["started_at"]), "Invalid original retrieval timestamps")
    return meta


def audit(original):
    """Require a verified successful prefix followed by exactly one failure."""
    original = original.resolve()
    prepared = b.plan()
    require(b.PLAN.read_bytes() == c.json_bytes(prepared), "Original frozen plan changed")
    manifest = c.decode((original / "run.json").read_bytes())
    require(manifest.get("plan") == prepared, "Original run plan/input provenance differs")
    b.m.stamp(manifest["created_at"])
    stopped = c.decode((original / "stopped.json").read_bytes())
    attempts = stopped.get("attempts")
    require(type(attempts) is int and 1 <= attempts <= prepared["request_count"]
            and stopped.get("automatic_retry") is False, "Invalid stopped-run attempt count")
    attempted = prepared["requests"][:attempts]
    require(stopped.get("request_id") == attempted[-1]["request"]["id"], "Stopped request identity differs")
    files = {"run.json", "stopped.json"} | {f'{item["request"]["id"]}.{suffix}' for item in attempted for suffix in SUFFIXES}
    require({p.name for p in original.iterdir()} == files, "Missing/unexpected original capture files")
    states = []
    failed = None
    for index, item in enumerate(attempted):
        meta = evidence_integrity(original, item)
        try:
            state = b.saved_state(original, item)
        except (ValueError, KeyError, TypeError, IndexError) as exc:
            require(index == len(attempted)-1, "Earlier original response failed validation; cannot reuse prefix")
            require(stopped.get("error") == f"{type(exc).__name__}: {exc}", "Stopped reason disagrees with observed failure")
            failed = {"item": item, "validation_error": f"{type(exc).__name__}: {exc}",
                      "transport": meta,
                      "captures": [b.m.prior.fingerprint(original / f'{item["request"]["id"]}.{s}') for s in SUFFIXES]}
        else:
            require(index < len(attempted)-1, "Stopped request now validates; manual review required")
            states.append(state)
    require(failed is not None, "No verified failed capture")
    pending = prepared["requests"][len(states):]
    return {"status": "PARTIAL_RUN_VALIDATED_RECOVERY_PREPARED_NOT_COLLECTED",
            "original_run_dir": path_text(original), "original_plan": prepared,
            "validated_request_ids": [item["request"]["id"] for item in attempted[:-1]],
            "validated_states": states, "failed_capture": failed,
            "pending_requests": pending, "recovery_request_count": len(pending),
            "original_attempts": attempts, "maximum_combined_attempts": attempts+len(pending),
            "unique_account_boundary_pairs": prepared["request_count"],
            "recovery_directory": path_text(OUTPUT / (original.name+"_recovery_01")),
            "automatic_retries": 0, "fallback_endpoints": [],
            "source_files": [b.m.prior.fingerprint(p) for p in (Path(__file__), Path(b.__file__), b.PLAN)],
            "original_file_hashes": {name: b.m.prior.fingerprint(original / name) for name in sorted(files)},
            "complete_stock_flow_comparison": None}


def validate(directory):
    directory = directory.resolve()
    manifest = c.decode((directory / "run.json").read_bytes())
    frozen = manifest["recovery_plan"]
    original = Path(frozen["original_run_dir"])
    original = original if original.is_absolute() else ROOT / original
    current = audit(original)
    require(frozen == current, "Original evidence or recovery plan changed")
    b.m.stamp(manifest["created_at"])
    pending = current["pending_requests"]
    expected = {f'{item["request"]["id"]}.{suffix}' for item in pending for suffix in SUFFIXES}
    actual = {p.name for suffix in SUFFIXES for p in directory.glob(f"*.{suffix}")}
    require(actual == expected, "Incomplete/unexpected recovery captures")
    require(not (directory / "stopped.json").exists(), "Recovery stopped; no complete comparison")
    states = current["validated_states"] + [b.saved_state(directory, item) for item in pending]
    report = b.compare(states, c.decode(b.sidecar.DECODED.read_bytes()))
    report.update(status="SIX_BOUNDARY_RESPONSES_VALIDATED_ACROSS_ORIGINAL_AND_RECOVERY",
                  reused_request_ids=current["validated_request_ids"],
                  recovered_request_ids=[item["request"]["id"] for item in pending],
                  original_failed_capture=current["failed_capture"],
                  boundaries=current["original_plan"]["boundaries"],
                  boundary_status=current["original_plan"]["boundary_status"],
                  boundary_precision=current["original_plan"]["boundary_precision"],
                  source_hashes=current["original_plan"]["source_hashes"],
                  recovery_sources=current["source_files"], original_file_hashes=current["original_file_hashes"],
                  recovery_manifest=b.m.prior.fingerprint(directory / "run.json"), references=b.SOURCES)
    return report


def recover(original, output_root=OUTPUT, transport=None, pause=None):
    prepared = audit(original)
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Saved recovery plan differs; review offline")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root / (original.resolve().name+"_recovery_01")
    directory.mkdir()  # Refuse a second invocation against the same attempt.
    c.write_new(directory / "run.json", c.json_bytes({"created_at": c.utc_now(), "recovery_plan": prepared}))
    print(f"Recovery evidence directory: {directory.resolve()}", flush=True)
    transport = c.fetch if transport is None else transport
    pause = time.sleep if pause is None else pause
    for attempt, item in enumerate(prepared["pending_requests"], 1):
        stem = item["request"]["id"]
        try:
            raw = c.json_bytes(item["request"])
            c.write_new(directory / f"{stem}.request.json", raw)
            print(f"Waiting {c.SPACING_SECONDS}s before {stem}; one attempt, no retries.", flush=True)
            pause(c.SPACING_SECONDS)
            started = c.utc_now()
            meta, response = transport(raw)
            meta.update(endpoint=c.ENDPOINT, started_at=started, finished_at=c.utc_now(),
                        request_http_method="POST", request_path="/", request_sha256=c.sha256(raw),
                        response_sha256=c.sha256(response), request_bytes=len(raw), response_bytes=len(response))
            c.write_new(directory / f"{stem}.response.body", response)
            c.write_new(directory / f"{stem}.metadata.json", c.json_bytes(meta))
            b.saved_state(directory, item)
        except (Exception, KeyboardInterrupt) as exc:
            c.write_new(directory / "stopped.json", c.json_bytes({"request_id": stem, "recovery_attempts": attempt,
                         "error": f"{type(exc).__name__}: {exc}", "automatic_retry": False}))
            raise
    report = validate(directory)
    c.write_new(directory / "validation.json", c.json_bytes(report))
    print("Six states validated across original and recovery; unexplained differences are not fees or revenue.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("plan", help="OFFLINE: audit the stopped run and prepare only missing requests")
    p.add_argument("--original-run-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p = subs.add_parser("recover", help="LIVE/manual: one attempt per missing state; no automatic retries")
    p.add_argument("--original-run-dir", type=Path, required=True)
    p = subs.add_parser("validate", help="OFFLINE: validate combined original/recovery evidence")
    p.add_argument("--recovery-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "recover":
            recover(args.original_run_dir)
            return 0
        report = audit(args.original_run_dir) if args.command == "plan" else validate(args.recovery_dir)
        raw = c.json_bytes(report)
        if args.output:
            c.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No automatic retry or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
