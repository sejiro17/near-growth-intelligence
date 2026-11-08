"""Offline redirect audit; one manually invoked, exact-allowlisted archive GET.

Reuse the saved mainnet 302 rather than requesting it again. Preserve both hops
and the original collector/plan. Any additional redirect stops, without follow.
"""

import argparse
import importlib.util
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BASE_FILE = ROOT / "analysis/34_neardata_single_block_pilot.py"


def load_base(name):
    spec = importlib.util.spec_from_file_location(name, BASE_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b = load_base("redirect_original_pilot")
c, require = b.c, b.require
DESTINATION = "https://a3.mainnet.neardata.xyz/v0/block/216877934"
PLAN = ROOT / "results/82_neardata_archive_redirect_recovery_plan.json"
OUTPUT = ROOT / "results/neardata_supply_block_pilot_recovery_2026-09-23"
COMMIT = "7324d9131e7e8285306606ba05822b007e44c53a"
SOURCE_BASE = "https://github.com/fastnear/neardata-server/blob/"+COMMIT+"/"
ORIGINAL_FILES = ("run.json", "stopped.json", "block-A.request.http", "block-A.request.json", "block-A.response.body", "block-A.metadata.json")
HOP_FILES = ORIGINAL_FILES[2:]


def path_text(path):
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def verified_url(value):
    require(isinstance(value, str) and value.isascii(), "Non-ASCII/missing redirect destination")
    parsed = urlsplit(value)
    require(value == DESTINATION and parsed.scheme == "https" and parsed.hostname == "a3.mainnet.neardata.xyz"
            and parsed.netloc == "a3.mainnet.neardata.xyz" and parsed.port is None
            and parsed.username is None and parsed.password is None
            and parsed.path == b.PATH and not parsed.query and not parsed.fragment,
            "Unverified destination, credentials or changed block path; do not follow")
    return value


def location(headers):
    require(isinstance(headers, list) and all(isinstance(h, list) and len(h) == 2
            and all(isinstance(x, str) for x in h) for h in headers), "Invalid response-header list")
    values = [v for k, v in headers if k.lower() == "location"]
    require(len(values) == 1, "Missing/duplicate Location headers; do not follow")
    return verified_url(values[0])


def timestamp_order(meta):
    stamps = [b.datetime.fromisoformat(meta[k]) for k in ("started_at", "finished_at")]
    require(all(s.utcoffset() == b.timedelta(0) for s in stamps) and stamps[1] >= stamps[0], "Invalid UTC retrieval times")


def integrity(directory, expected_http, expected_description, endpoint):
    raw = (directory / "block-A.request.http").read_bytes()
    desc = (directory / "block-A.request.json").read_bytes()
    body = (directory / "block-A.response.body").read_bytes()
    meta = c.decode((directory / "block-A.metadata.json").read_bytes())
    require(raw == expected_http and desc == c.json_bytes(expected_description), "Saved request bytes changed")
    require(meta.get("endpoint") == endpoint and meta.get("request_http_method") == "GET"
            and meta.get("request_path") == b.PATH, "Saved request endpoint/method/path changed")
    require(meta.get("request_sha256") == c.sha256(raw) and meta.get("request_bytes") == len(raw)
            and meta.get("request_description_sha256") == c.sha256(desc)
            and meta.get("response_sha256") == c.sha256(body) and meta.get("response_bytes") == len(body), "Capture checksum/length mismatch")
    require(meta.get("body_complete") is True and not meta.get("transport_error")
            and len(body) <= b.MAX_BODY, "Incomplete/oversize transport; evidence retained")
    timestamp_order(meta)
    return meta, body


def archive_transport():
    """Private instance of the original transport; change only the verified host."""
    verified_url(DESTINATION)
    module = load_base("redirect_archive_transport")
    module.HOST = urlsplit(DESTINATION).hostname
    module.URL = DESTINATION
    module.HEADERS = [[k, module.HOST if k.lower() == "host" else v] for k, v in b.HEADERS]
    require(module.PATH == b.PATH and module.MAX_BODY == b.MAX_BODY
            and module.c.CONNECT_TIMEOUT == b.c.CONNECT_TIMEOUT
            and module.c.REQUEST_TIMEOUT == b.c.REQUEST_TIMEOUT, "Original transport limits changed")
    require({k.lower() for k, _ in module.HEADERS} == {"host", "accept", "accept-encoding", "connection", "user-agent"}, "Unexpected credential-bearing request headers")
    return module


def plan(original):
    original = original.resolve()
    prepared = b.plan()
    require(b.PLAN.read_bytes() == c.json_bytes(prepared), "Original plan 81 changed")
    require({p.name for p in original.iterdir()} == set(ORIGINAL_FILES), "Unexpected/missing original files")
    manifest = c.decode((original / "run.json").read_bytes())
    require(manifest.get("plan") == prepared, "Original run/input provenance changed")
    meta, body = integrity(original, b.request_bytes(), b.description(), b.URL)
    require(meta.get("http_status") == 302, "Original response is not the reviewed archive-routing 302")
    verified = location(meta["response_headers"])
    stopped = c.decode((original / "stopped.json").read_bytes())
    require(type(stopped.get("attempts")) is int and stopped["attempts"] == 1 and stopped.get("automatic_retry") is False
            and stopped.get("error") == "ValueError: Failed/incomplete HTTP transport/status: 302; evidence retained", "Original stopped reason differs")
    transport = archive_transport()
    return {"status": "ORIGINAL_302_VALIDATED_DOCUMENTED_ARCHIVE_ROUTE_PREPARED",
            "original_run_dir": path_text(original), "original_http_status": 302,
            "original_response_bytes": len(body), "original_location": verified,
            "original_response_headers": meta["response_headers"],
            "original_file_hashes": {name: b.fingerprint(original/name) for name in ORIGINAL_FILES},
            "original_plan": prepared, "allowed_destinations": [DESTINATION],
            "request": transport.description(), "additional_request_count": 1, "maximum_response_hops_including_original": 2,
            "further_redirects": "STOP_AND_PRESERVE_WITHOUT_FOLLOWING", "automatic_retries": 0,
            "credentials": "NONE; no Authorization, Proxy-Authorization, Cookie, Referer, query keys or environment credentials",
            "fallback_endpoints": [], "spacing_seconds": b.c.SPACING_SECONDS,
            "connect_timeout_seconds": b.c.CONNECT_TIMEOUT, "request_timeout_seconds": b.c.REQUEST_TIMEOUT,
            "response_body_cap_bytes": b.MAX_BODY, "combined_hop_body_cap_bytes": b.MAX_BODY,
            "official_source_review": {
                "repository": "fastnear/neardata-server", "commit": COMMIT,
                "api": {"url": SOURCE_BASE+"src/api.rs", "git_blob_sha": "16fdd9ce6e866395e96245016731eb1a2524ed6f",
                        "mechanism": "check_archive_redirects selects archive index by height and returns Found with https://a{index}.{domain_name}/v0/block/{height}"},
                "readme": {"url": SOURCE_BASE+"README.md", "git_blob_sha": "4e3540252225ac19e48c95fdfdad2ccbdda984c1",
                           "mechanism": "Finalized block route may redirect to the host owning its canonical archive range; mainnet base and credential-free access documented"},
                "verification_basis": "Saved complete HTTPS response from official mainnet base, exact unchanged path, and matching pinned source routing pattern",
                "limits": "Production range boundaries, exact deployed binary and destination availability are not independently established; TLS hostname verification stays enabled"},
            "recovery_directory": path_text(OUTPUT/(original.name+"_recovery_01")),
            "source_files": [b.fingerprint(p) for p in (Path(__file__), BASE_FILE, b.PLAN)]}


def validate(directory):
    directory = directory.resolve()
    manifest = c.decode((directory/"run.json").read_bytes())
    frozen = manifest["recovery_plan"]
    original = Path(frozen["original_run_dir"])
    original = original if original.is_absolute() else ROOT/original
    prepared = plan(original)
    require(frozen == prepared, "Recovery plan/original evidence changed")
    copy_dir = directory/"hop-00-original"
    require({p.name for p in copy_dir.iterdir()} == set(ORIGINAL_FILES), "Original hop copy is incomplete")
    for name in ORIGINAL_FILES:
        require((copy_dir/name).read_bytes() == (original/name).read_bytes(), "Original-hop copied bytes changed")
    hop = directory/"hop-01-archive"
    require({p.name for p in hop.iterdir()} == set(HOP_FILES), "Archive hop contains missing/extra files")
    transport = archive_transport()
    meta, body = integrity(hop, transport.request_bytes(), transport.description(), DESTINATION)
    require(meta.get("http_status") == 200, f"Archive HTTP {meta.get('http_status')}; stop, no further redirect or retry")
    require(len(body)+prepared["original_response_bytes"] <= b.MAX_BODY, "Combined hop body cap exceeded")
    require(not (directory/"stopped.json").exists(), "Recovery stopped; no successful validation")
    report = b.compare(body, b.controls()[0])
    report.update(redirect_recovery={"original": prepared, "archive_http_status": meta["http_status"],
                  "recovery_manifest": b.fingerprint(directory/"run.json"),
                  "archive_capture": [b.fingerprint(hop/name) for name in HOP_FILES]})
    return report


def recover(original, output_root=OUTPUT, transport=None, pause=None):
    prepared = plan(original)
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Saved recovery plan differs; review offline")
    output_root.mkdir(parents=True, exist_ok=True)
    directory = output_root/(original.resolve().name+"_recovery_01")
    directory.mkdir()  # Prevent a repeated invocation from making another request.
    c.write_new(directory/"run.json", c.json_bytes({"created_at": c.utc_now(), "recovery_plan": prepared}))
    copied, hop = directory/"hop-00-original", directory/"hop-01-archive"
    copied.mkdir()
    hop.mkdir()
    for name in ORIGINAL_FILES:
        c.write_new(copied/name, (original/name).read_bytes())
    archive = archive_transport()
    raw, desc = archive.request_bytes(), c.json_bytes(archive.description())
    c.write_new(hop/"block-A.request.http", raw)
    c.write_new(hop/"block-A.request.json", desc)
    print(f"Recovery evidence directory: {directory.resolve()}", flush=True)
    pause = time.sleep if pause is None else pause
    transport = archive.fetch if transport is None else transport
    try:
        print(f"Waiting {b.c.SPACING_SECONDS}s before verified archive hop; one GET, no retries.", flush=True)
        pause(b.c.SPACING_SECONDS)
        started = c.utc_now()
        meta, response = transport(raw)
        meta.update(endpoint=DESTINATION, started_at=started, finished_at=c.utc_now(), request_http_method="GET", request_path=b.PATH,
                    request_sha256=c.sha256(raw), request_bytes=len(raw), request_description_sha256=c.sha256(desc),
                    response_sha256=c.sha256(response), response_bytes=len(response))
        c.write_new(hop/"block-A.response.body", response)
        c.write_new(hop/"block-A.metadata.json", c.json_bytes(meta))
        report = validate(directory)
        c.write_new(directory/"validation.json", c.json_bytes(report))
    except (Exception, KeyboardInterrupt) as exc:
        c.write_new(directory/"stopped.json", c.json_bytes({"attempts": 1, "automatic_retry": False,
                     "error": f"{type(exc).__name__}: {exc}"}))
        raise
    print("Archive hop compared with canonical A; no bulk coverage, gross burn or weekly reconciliation established.")
    return directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("plan", help="OFFLINE: validate original 302 and print exact archive-hop plan")
    p.add_argument("--original-run-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    p = subs.add_parser("recover", help="LIVE/manual: follow only the reviewed saved Location once")
    p.add_argument("--original-run-dir", type=Path, required=True)
    p = subs.add_parser("validate", help="OFFLINE: validate saved original/archive hops")
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "recover":
            recover(args.original_run_dir)
            return 0
        report = plan(args.original_run_dir) if args.command == "plan" else validate(args.run_dir)
        raw = c.json_bytes(report)
        if args.output:
            c.write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No automatic retry or unverified redirect.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
