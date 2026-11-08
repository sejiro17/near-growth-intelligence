"""Offline stopped-run audit and explicitly manual two-stage epoch recovery.

Keep analysis 26 and its pinned manifest unchanged. Reuse only validated
responses; retain the failed capture and count every attempt against old caps.
Only recover-failed and continue perform requests, when invoked manually.
"""

import argparse
import importlib.util
import shlex
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("recovery_discovery", ROOT / "analysis/26_supply_epoch_discovery.py")
d = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(d)
capture, require = d.capture, d.require


class MissingEvidence(Exception):
    def __init__(self, method, params):
        self.method, self.params = method, params
        super().__init__(f"Missing saved response: {method} {params}")


class ReuseResolver(d.Resolver):
    def get(self, method, params):
        if not self.live and not self.has(method, params):
            raise MissingEvidence(method, params)
        return super().get(method, params)


def relative(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def integrity(directory, payload):
    """Check bytes and provenance even when no successful envelope exists."""
    stem = payload["id"]
    request = (directory / f"{stem}.request.json").read_bytes()
    response = (directory / f"{stem}.response.body").read_bytes()
    meta = capture.decode((directory / f"{stem}.metadata.json").read_bytes())
    require(capture.decode(request) == payload and meta.get("endpoint") == capture.ENDPOINT
            and meta.get("request_http_method") == "POST" and meta.get("request_path") == "/", "Capture request/endpoint mismatch")
    require(meta.get("request_sha256") == capture.sha256(request)
            and meta.get("response_sha256") == capture.sha256(response)
            and meta.get("request_bytes") == len(request)
            and meta.get("response_bytes") == len(response), "Capture checksum/length mismatch")
    started, finished = (datetime.fromisoformat(meta.get(k, "")) for k in ("started_at", "finished_at"))
    require(started.utcoffset() == timezone.utc.utcoffset(started)
            and finished.utcoffset() == timezone.utc.utcoffset(finished)
            and started <= finished, "Invalid capture UTC timestamps")
    return meta


def prefix(resolver):
    """Replay the original validator first, then describe only its valid prefix.

    Reconstruction reports rows only after all four inputs are available. The
    original walk has already checked those rows, including offset/protocol and
    saved A/B controls. Any other error propagates; it is not a partial success.
    """
    try:
        complete = d.run_discovery(resolver)
    except MissingEvidence as exc:
        missing = {"method": exc.method, "params": exc.params}
        original_usage = list(resolver.used)
    else:
        return complete, None, list(resolver.used)
    opening, closing = d.weekly.plan()["targets"]
    cursor = d.header(resolver.get("block", {"block_id": closing["hash"]}))
    opening_epoch = d.weekly.validate_week(d.WEEK_CAPTURE)["endpoints"][0]["epoch_id"]
    rows, pending = [], {}
    while cursor["epoch_id"] != opening_epoch:
        phase = "validators"
        pending = {"epoch_id": cursor["epoch_id"]}
        try:
            info = d.validator_info(resolver.get("validators", {"epoch_id": cursor["epoch_id"]}))
            pending.update(epoch_height=info["epoch_height"], boundary_height=info["epoch_start_height"])
            phase = "boundary_block"
            boundary = d.header(resolver.get("block", {"block_id": info["epoch_start_height"]}))
            phase = "parent_block"
            parent = d.header(resolver.get("block", {"block_id": boundary["prev_hash"]}))
            phase = "offset_reward_response"
            reward = d.validator_info(resolver.get("validators", {"epoch_id": cursor["next_epoch_id"]}))
        except MissingEvidence as exc:
            require(missing == {"method": exc.method, "params": exc.params}, "Prefix reconstruction disagrees with original replay")
            pending["missing_phase"] = phase
            break
        rows.append({"epoch_id": cursor["epoch_id"], "epoch_height": info["epoch_height"],
                     "boundary_height": boundary["height"], "boundary_hash": boundary["hash"],
                     "application_timestamp_nanosec": boundary["timestamp_nanosec"],
                     "parent_height": parent["height"], "parent_hash": parent["hash"],
                     "reward_response_epoch_id": cursor["next_epoch_id"],
                     "reward_response_epoch_height": reward["epoch_height"],
                     "reward_map_payees": len(reward["validator_reward_paid_prev_epoch"]),
                     "recorded_reward_map_sum_yocto": str(sum(int(v) for v in reward["validator_reward_paid_prev_epoch"].values()))})
        cursor = parent
    require(len(rows) <= d.MAX_EPOCHS, "Prefix exceeds original epoch cap")
    resolver.used = original_usage
    return {"status": "INCOMPLETE_VALIDATED_PREFIX_NOT_WEEKLY_ISSUANCE", "validated_application_boundaries": len(rows),
            "boundaries_descending": rows, "pending_epoch": pending,
            "opening_epoch_reached": False,
            "saved_AB_controls_observed": sorted(set(d.capture.TARGETS[k]["height"] for k in "AB") & {r["boundary_height"] for r in rows}),
            "weekly_issuance_yocto": None, "independent_weekly_net_debit_yocto": None,
            "gross_actual_burn_yocto": None, "subsidies_yocto": None}, missing, original_usage


def audit(directory):
    directory = directory.resolve()
    manifest = capture.decode((directory / "run.json").read_bytes())
    require(manifest == d.plan(), "Original collector/manifest/input provenance changed")
    stopped = capture.decode((directory / "stopped.json").read_bytes())
    require(stopped.get("status") == "INCOMPLETE_STOPPED_NOT_ZERO"
            and stopped.get("weekly_issuance_yocto") is None and stopped.get("independent_weekly_debit_yocto") is None,
            "Unexpected stopped-run scope")
    paths = sorted(directory.glob("*.request.json"))
    attempts = stopped.get("new_requests_attempted")
    require(type(attempts) is int and 0 < attempts <= d.MAX_REQUESTS and len(paths) == attempts,
            "Request count disagrees with stopped manifest/cap")
    require(len(list(directory.glob("*.metadata.json"))) == attempts
            and len(list(directory.glob("*.response.body"))) == attempts, "Missing/extra capture components")
    resolver = ReuseResolver(d.CACHE_DIRS)
    failed, counts, prior_finished, gaps = None, {}, None, []
    for ordinal, path in enumerate(paths, 1):
        payload = capture.decode(path.read_bytes())
        require(isinstance(payload, dict) and payload.get("jsonrpc") == "2.0"
                and payload.get("method") in {"block", "validators"}
                and payload.get("id") == f"epoch-{ordinal:03d}-{payload['method']}"
                and path.name == payload["id"] + ".request.json", "Nonconsecutive/unexpected original request identity")
        meta = integrity(directory, payload)
        started = datetime.fromisoformat(meta["started_at"])
        if prior_finished:
            gap = started - prior_finished
            microseconds = (gap.days*86400 + gap.seconds)*10**6 + gap.microseconds
            gaps.append({"request_id": payload["id"], "wall_clock_gap_microseconds": microseconds})
        prior_finished = datetime.fromisoformat(meta["finished_at"])
        try:
            value = capture.recorded(directory, payload)
        except ValueError as exc:
            require(ordinal == attempts and failed is None, "Nonterminal failed capture; manual review required")
            # Integrity errors were rejected above, not silently treated as retries.
            failed = {"request": payload, "request_path": relative(path), "metadata": meta,
                      "saved_validation_error": str(exc)}
        else:
            if payload["method"] == "validators":
                d.validator_info(value)
            resolver.register(directory, payload, value)
            counts[payload["method"]] = counts.get(payload["method"], 0) + 1
    require(failed is not None and failed["request"]["id"] in stopped.get("error", ""), "Stopped error does not identify terminal failed request")
    report, missing, usage = prefix(resolver)
    require(missing is not None and missing == {"method": failed["request"]["method"], "params": failed["request"]["params"]},
            "Failed request does not match first missing scope evidence")
    require(usage == stopped.get("used_responses"), "Original stopped transcript does not reproduce")
    used_paths = {(ROOT / u["saved_request"]).resolve() for u in usage}
    require(all(p.resolve() in used_paths for p in paths[:-1]), "Unused/off-scope completed original capture")
    report.update(original_run_directory=relative(directory), original_attempts=attempts,
                  validated_completed_responses=sum(counts.values()), completed_response_types=counts,
                  stopped_transcript_reproduces=True, failed_capture=failed,
                  remaining_attempt_budget=d.MAX_REQUESTS-attempts,
                  original_max_requests=d.MAX_REQUESTS, original_max_application_epochs=d.MAX_EPOCHS)
    report["pacing_diagnostic"] = {
        "minimum_wall_clock_gap_microseconds": min(g["wall_clock_gap_microseconds"] for g in gaps) if gaps else None,
        "gaps_below_configured_spacing": [g for g in gaps if g["wall_clock_gap_microseconds"] < d.capture.SPACING_SECONDS*10**6],
        "scope": "UTC wall-clock differences only; monotonic sleep duration was not recorded. Recovery keeps the original 65-second sleep."}
    report["source_hashes"] = d.pilot.fingerprint([p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".")]
                                                + [Path(__file__), ROOT / "analysis/26_supply_epoch_discovery.py"])
    return report, resolver


def recovery_plan(original):
    report, _ = audit(original)
    require(report["remaining_attempt_budget"] > 0, "Original request cap exhausted")
    suggested = ROOT / "results/supply_epoch_discovery_recovery_2026-09-21_to_2026-09-27" / (original.name + "_recovery_01")
    command = [".venv/bin/python", "analysis/27_recover_supply_epoch_discovery.py"]
    return {"status": "MANUAL_RECOVERY_PREPARATION_ONLY", "original_run_directory": relative(original),
            "endpoint": capture.ENDPOINT, "original_attempts": report["original_attempts"],
            "max_cumulative_attempts": d.MAX_REQUESTS, "max_application_epochs": d.MAX_EPOCHS,
            "failed_request": report["failed_capture"]["request"],
            "failed_request_recovery_attempts": 1,
            "remaining_stage_attempt_limit": d.MAX_REQUESTS-report["original_attempts"]-1,
            "spacing_seconds": capture.SPACING_SECONDS, "connect_timeout_seconds": capture.CONNECT_TIMEOUT,
            "request_timeout_seconds": capture.REQUEST_TIMEOUT, "automatic_retries": 0, "fallback_endpoints": [],
            "original_audit": report, "recovery_code_sha256": capture.sha256(Path(__file__).read_bytes()),
            "suggested_recovery_directory": relative(suggested),
            "manual_commands": {
                "recover_failed": shlex.join(command+["recover-failed", "--run-dir", relative(original), "--recovery-dir", relative(suggested)]),
                "validate_failed_offline": shlex.join(command+["validate-failed", "--recovery-dir", relative(suggested)]),
                "continue_remaining": shlex.join(command+["continue", "--recovery-dir", relative(suggested)])},
            "expected_outputs": ["run.json", "failed/<original-request-id>.request.json", "failed/<original-request-id>.response.body",
                                 "failed/<original-request-id>.metadata.json", "failed_validation.json", "remaining/epoch-055-<method>.*", "validation.json"],
            "scope": "Same UTC week, opening epoch sentinel, offset maps, and existing A/B controls; unsuccessful original attempt consumes budget"}


def seed_recovery(directory):
    run = capture.decode((directory / "run.json").read_bytes())
    original = ROOT / run["original_run_directory"]
    require(run == recovery_plan(original), "Recovery provenance/input mismatch")
    _, resolver = audit(original)
    payload = run["failed_request"]
    integrity(directory / "failed", payload)
    result = capture.recorded(directory / "failed", payload)
    resolver.register(directory / "failed", payload, result)
    resolver.used = []
    return run, resolver


def validate_failed(directory):
    run, resolver = seed_recovery(directory)
    report, missing, _ = prefix(resolver)
    payload = run["failed_request"]
    require(missing != {"method": payload["method"], "params": payload["params"]}, "Failed request remains unresolved")
    result = capture.recorded(directory / "failed", payload)
    h = d.header(result) if payload["method"] == "block" else None
    return {"status": "RECOVERED_RESPONSE_VALIDATED_NOT_COMPLETE_WEEK", "recovered_request": payload,
            "returned_header": {k: h[k] for k in ("height", "hash", "epoch_id", "prev_hash", "next_epoch_id", "timestamp_nanosec")} if h else None,
            "cumulative_attempts": run["original_attempts"]+1, "remaining_attempt_budget": run["remaining_stage_attempt_limit"],
            "validated_prefix": report, "next_missing_request": missing,
            "capture_inputs": d.pilot.fingerprint(sorted((directory / "failed").iterdir())+[directory / "run.json"])}


def recover_failed(original, directory, transport=None, pause=None):
    prepared = recovery_plan(original)
    original_raw = (ROOT / prepared["original_audit"]["failed_capture"]["request_path"]).read_bytes()
    require(capture.json_bytes(prepared["failed_request"]) == original_raw, "Original request encoding needs explicit review")
    directory.mkdir(parents=True, exist_ok=False)
    capture.write_new(directory / "run.json", capture.json_bytes(prepared))
    target = directory / "failed"
    target.mkdir()
    print(f"Recovery evidence directory: {directory.resolve()}", flush=True)
    try:
        capture.capture(target, prepared["failed_request"], transport=transport, pause=pause)
        capture.write_new(directory / "failed_validation.json", capture.json_bytes(validate_failed(directory)))
    except (Exception, KeyboardInterrupt) as exc:
        capture.write_new(directory / "failed_stopped.json", capture.json_bytes({"status": "RECOVERY_STOPPED_NOT_ZERO",
            "error": f"{type(exc).__name__}: {exc}", "cumulative_attempts": prepared["original_attempts"]+1,
            "weekly_issuance_yocto": None, "independent_weekly_net_debit_yocto": None}))
        raise
    print("One response recovered. Review failed_validation.json offline before the separate continue command.")
    return directory


def validate_remaining(directory):
    failed_report = validate_failed(directory)
    require(capture.json_bytes(failed_report) == (directory / "failed_validation.json").read_bytes(), "Stage-one validation changed")
    run, resolver = seed_recovery(directory)
    remainder = directory / "remaining"
    paths = sorted(remainder.glob("*.request.json"))
    require(len(paths) <= run["remaining_stage_attempt_limit"], "Cumulative request cap exceeded")
    require(len(list(remainder.glob("*.metadata.json"))) == len(paths)
            and len(list(remainder.glob("*.response.body"))) == len(paths), "Incomplete remaining capture components")
    for index, path in enumerate(paths, run["original_attempts"]+2):
        payload = capture.decode(path.read_bytes())
        require(payload.get("method") in {"block", "validators"}
                and payload.get("id") == f"epoch-{index:03d}-{payload['method']}", "Recovery request numbering/scope mismatch")
        integrity(remainder, payload)
        require(not resolver.has(payload["method"], payload["params"]), "Recovery repeated a successful request")
        result = capture.recorded(remainder, payload)
        if payload["method"] == "validators":
            d.validator_info(result)
        resolver.register(remainder, payload, result)
    report = d.run_discovery(resolver)
    used_paths = {(ROOT / u["saved_request"]).resolve() for u in resolver.used}
    require(all(p.resolve() in used_paths for p in paths), "Unused/off-scope recovery capture")
    report.update(original_attempts=run["original_attempts"], failed_recovery_attempts=1,
                  remaining_collection_attempts=len(paths), cumulative_attempts=run["original_attempts"]+1+len(paths),
                  used_responses=resolver.used)
    sources = [p for p in directory.rglob("*") if p.is_file()
               and p.name not in {"validation.json", "stopped.json"} and not p.name.startswith(".")]
    report["capture_inputs"] = d.pilot.fingerprint(sources)
    return report


def continue_collection(directory, transport=None, pause=None):
    require(capture.json_bytes(validate_failed(directory)) == (directory / "failed_validation.json").read_bytes(),
            "Stage-one validation changed")
    run, resolver = seed_recovery(directory)
    remainder = directory / "remaining"
    remainder.mkdir()  # Refuse resuming/replacing any previous remaining attempt.
    resolver.live, resolver.destination = True, remainder
    resolver.transport, resolver.pause = transport, pause
    resolver.new_requests = run["original_attempts"]+1  # Failed attempts consume the original cap.
    try:
        d.run_discovery(resolver)
        report = validate_remaining(directory)
        capture.write_new(directory / "validation.json", capture.json_bytes(report))
    except (Exception, KeyboardInterrupt) as exc:
        capture.write_new(directory / "stopped.json", capture.json_bytes({"status": "INCOMPLETE_RECOVERY_NOT_ZERO",
            "error": f"{type(exc).__name__}: {exc}", "cumulative_attempts": resolver.new_requests,
            "used_responses": resolver.used, "weekly_issuance_yocto": None, "independent_weekly_net_debit_yocto": None}))
        raise
    print(f"Complete observed walk; {report['cumulative_attempts']} cumulative attempts. Independent weekly debit remains unavailable.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("inspect", "plan", "recover-failed", "validate-failed", "continue", "validate"))
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--recovery-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command in {"inspect", "plan", "recover-failed"}:
            require(args.run_dir is not None, "--run-dir required")
        else:
            require(args.run_dir is None, "--run-dir applies to original-run commands only")
        if args.command in {"recover-failed", "validate-failed", "continue", "validate"}:
            require(args.recovery_dir is not None, "--recovery-dir required")
        else:
            require(args.recovery_dir is None, "--recovery-dir applies to recovery stages only")
        if args.command in {"recover-failed", "continue"}:
            require(args.output is None, "Live stages retain evidence in exclusive directories")
            if args.command == "recover-failed":
                recover_failed(args.run_dir, args.recovery_dir)
            else:
                continue_collection(args.recovery_dir)
            return 0
        result = {"inspect": lambda: audit(args.run_dir)[0], "plan": lambda: recovery_plan(args.run_dir),
                  "validate-failed": lambda: validate_failed(args.recovery_dir), "validate": lambda: validate_remaining(args.recovery_dir)}[args.command]()
        raw = capture.json_bytes(result)
        if args.output:
            capture.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, MissingEvidence) as exc:
        print(f"Stopped: {exc}. No automatic retry or fallback.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
