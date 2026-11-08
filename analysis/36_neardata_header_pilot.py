"""Resumable, manually invoked 100-height Neardata header pilot; no full scan.

Raw attempts live outside the checkout. plan/validate never request source data.
Nulls need successor predecessor evidence; missing data is never assumed skipped.
"""

import argparse
import fcntl
import importlib.util
import os
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("header_redirect_control", ROOT / "analysis/35_recover_neardata_archive_redirect.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)
b, c, require = r.b, r.c, r.require
START, FULL_END = 216877934, 216921133
END = START+99
SPACING = 1
MAX_ATTEMPTS = 2                 # one attempt per height per manual invocation
MAX_SESSION_REQUESTS = 198       # 99 uncached heights, at most two hops each
TOTAL_BODY_CAP = 64*1024*1024     # includes failed and null attempts, across resumes
STORE = ROOT.parent/"near-growth-intelligence-evidence/neardata_headers_216877934_216921133/pilot_216877934_216878033"
PLAN = ROOT/"results/84_neardata_contiguous_header_pilot_plan.json"
RECOVERY = ROOT/"results/neardata_supply_block_pilot_recovery_2026-09-23/20261107T154218Z_8ca556d6bf23_recovery_01"
POINT = ROOT/"results/83_neardata_canonical_block_A_comparison_2026-09-23.json"
WEEK = ROOT/"results/72_supply_protocol_validated_week_2026-09-21_to_2026-09-27.json"
HOSTS = ("mainnet.neardata.xyz", "a3.mainnet.neardata.xyz")
SOURCE = "https://github.com/fastnear/neardata-server/blob/7324d9131e7e8285306606ba05822b007e44c53a/"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
CHUNK_KEYS = ("shard_id", "chunk_hash", "prev_block_hash", "height_created", "height_included", "balance_burnt")
HEADER_KEYS = ("height", "hash", "prev_hash", "prev_height", "epoch_id", "next_epoch_id", "timestamp_nanosec", "total_supply", "chunk_mask", "chunks_included")
CAPTURE_FILES = {"request.http", "request.json", "response.body", "metadata.json"}


def write_new(path, raw):
    """Atomic exclusive publication; interrupted drafts remain as evidence."""
    if path.exists():
        raise FileExistsError(path)
    draft = path.with_name(path.name+".writing-"+uuid.uuid4().hex[:12])
    with draft.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(draft, path)  # atomic, and refuses an existing destination
    draft.unlink()       # same bytes now retained at the final name


def chain_id(value):
    require(isinstance(value, str) and value and all(x in ALPHABET for x in value), "Invalid chain identifier")
    number = 0
    for char in value:
        number = number*58+ALPHABET.index(char)
    require((number.bit_length()+7)//8+len(value)-len(value.lstrip("1")) == 32, "Identifier is not 32 bytes")
    return value


def normalize(block, height, control, check_epoch=True):
    require(isinstance(block, dict) and isinstance(block.get("header"), dict), "Missing header envelope")
    h = block["header"]
    require(all(k in h for k in HEADER_KEYS), "Missing required lossless header field")
    for k in ("height", "prev_height", "chunks_included"):
        c.integer(h[k], k)
    require(h["height"] == height and h["prev_height"] < height, "Requested height/predecessor mismatch")
    for k in ("hash", "prev_hash", "epoch_id", "next_epoch_id"):
        chain_id(h[k])
    require(isinstance(h["timestamp_nanosec"], str) and h["timestamp_nanosec"].isascii()
            and h["timestamp_nanosec"].isdigit() and type(h.get("timestamp")) is int
            and h["timestamp"] == int(h["timestamp_nanosec"]), "Invalid exact timestamp fields")
    b.money(h["total_supply"])
    if check_epoch:
        require(h["epoch_id"] == control["header"]["epoch_id"] and h["next_epoch_id"] == control["header"]["next_epoch_id"], "Unreviewed epoch/configuration transition")
    chunks, mask = block.get("chunks"), h["chunk_mask"]
    require(isinstance(chunks, list) and len(chunks) == len(control["chunks"])
            and isinstance(mask, list) and len(mask) == len(chunks) and all(type(x) is bool for x in mask), "Partial manifest or invalid chunk mask")
    seen, result = set(), []
    for index, (chunk, reference) in enumerate(zip(chunks, control["chunks"])):
        require(isinstance(chunk, dict) and all(k in chunk for k in CHUNK_KEYS), "Missing required chunk field")
        require(type(chunk["shard_id"]) is int and chunk["shard_id"] == reference["shard_id"], "Shard order/configuration mismatch")
        chain_id(chunk["chunk_hash"])
        chain_id(chunk["prev_block_hash"])
        require(chunk["chunk_hash"] not in seen, "Duplicate chunk hash")
        seen.add(chunk["chunk_hash"])
        created, included = (c.integer(chunk[k], k) for k in ("height_created", "height_included"))
        require(created <= included <= height and mask[index] == (included == height), "Invalid chunk inclusion/mask")
        b.money(chunk["balance_burnt"])
        result.append({k: chunk[k] for k in CHUNK_KEYS})
    require(h["chunks_included"] == sum(mask), "Included chunk count mismatch")
    return {"header": {k: h[k] for k in HEADER_KEYS}, "chunks": result}


def seeds():
    require(c.json_bytes(r.validate(RECOVERY)) == POINT.read_bytes(), "Validated result 83 no longer reproduces")
    control = b.controls()[0]
    observations, excluded = {}, []
    def add(block, sources):
        height = block["header"]["height"]
        norm = normalize(block, height, control, check_epoch=height >= START)
        if height in observations:
            require(observations[height]["block"] == norm, "Conflicting saved block identities/monetary fields")
            observations[height]["sources"].extend(sources)
        else:
            observations[height] = {"kind": "BLOCK", "block": norm, "sources": sources}
    document = c.decode((RECOVERY/"hop-01-archive/block-A.response.body").read_bytes())
    add(document["block"], [b.fingerprint(POINT)])
    for request_path in sorted((ROOT/"results").rglob("*.request.json")):
        payload = c.decode(request_path.read_bytes())
        if not isinstance(payload, dict) or payload.get("method") != "block":
            continue
        block_id = payload.get("params", {}).get("block_id")
        if type(block_id) is int and not START-1 <= block_id <= END:
            continue
        stem = request_path.name[:-len(".request.json")]
        body_path = request_path.with_name(stem+".response.body")
        try:
            peek = c.decode(body_path.read_bytes())
            block = peek.get("result", {})
            height = block.get("header", {}).get("height")
            if type(height) is not int or not START-1 <= height <= END:
                continue
            verified = c.recorded(request_path.parent, payload)
            require(block_id in (height, verified["header"]["hash"]), "Saved RPC requested identity mismatch")
        except (OSError, ValueError, KeyError, TypeError) as exc:
            excluded.append({"path": str(request_path.relative_to(ROOT)), "reason": str(exc)})
            continue
        add(verified, [b.fingerprint(request_path.with_name(stem+"."+suffix)) for suffix in ("request.json", "response.body", "metadata.json")])
    require(START in observations and START-1 in observations, "Missing exact A/opening-parent controls")
    require(observations[START]["block"]["header"]["prev_hash"] == observations[START-1]["block"]["header"]["hash"], "Saved A parent mismatch")
    return observations, excluded


def plan():
    require(START <= END <= FULL_END and END-START+1 <= 100, "Only the at-most-100-height pilot is enabled")
    cached, excluded = seeds()
    return {"scope": "100_HEIGHT_PILOT_ONLY_FULL_INTERVAL_DISABLED", "network": "mainnet",
            "full_interval": [START, FULL_END], "pilot_interval": [START, END], "maximum_pilot_heights": 100,
            "full_interval_last_hash_control": {"height": FULL_END, "hash": c.TARGETS["B"]["parent"]},
            "following_boundary_B": {"height": c.TARGETS["B"]["height"], "hash": c.TARGETS["B"]["hash"]},
            "cached_pilot_heights": sorted(h for h in cached if h >= START),
            "seeds": {str(h): row for h, row in cached.items()}, "excluded_unusable_saved_captures": excluded,
            "request_path": "/v0/block/{height}/headers", "allowed_hosts": list(HOSTS),
            "routing": "Official base then at most one HTTPS redirect to the previously verified a3 host, identical height and /headers path",
            "documented_limit_requests_per_minute_per_ip": 180, "pacing_seconds_after_each_response": SPACING,
            "maximum_session_http_requests": MAX_SESSION_REQUESTS, "maximum_attempts_per_height": MAX_ATTEMPTS,
            "maximum_lifetime_http_requests": MAX_SESSION_REQUESTS*MAX_ATTEMPTS,
            "automatic_retries": 0, "connect_timeout_seconds": c.CONNECT_TIMEOUT, "request_timeout_seconds": c.REQUEST_TIMEOUT,
            "per_response_body_cap_bytes": b.MAX_BODY, "lifetime_downloaded_body_cap_bytes": TOTAL_BODY_CAP,
            "null_policy": "One bounded successor probe inside the pilot only; null is skipped only with matching predecessor height/hash bypass; two consecutive or trailing nulls stop",
            "monetary_scope": "Newly included headers only; opening predecessor excluded. Pilot overlaps already measured A and is not added to earlier boundary totals",
            "raw_store": str(STORE), "large_raw_files_belong_in_git": False,
            "actual_pilot_download_bytes_before_manual_run": None,
            "actual_pilot_throughput_before_manual_run": None, "full_interval_collection_proposal": None,
            "credentials": "NONE; no Authorization, cookies, query keys or environment credentials",
            "references": [SOURCE+"README.md", SOURCE+"src/api.rs"],
            "historical_supply_constructor": "https://github.com/near/nearcore/blob/5af9ca74631e6cf0dae33e77d1a632e94d2952ce/core/primitives/src/block.rs",
            "source_files": [b.fingerprint(p) for p in (Path(__file__), Path(r.__file__), Path(b.__file__), Path(c.__file__), POINT, WEEK)]}


def endpoint(host, height):
    require(host in HOSTS and type(height) is int and START <= height <= END, "Unverified host or height outside pilot")
    return f"https://{host}/v0/block/{height}/headers"


def redirect(headers, height):
    values = [v for k, v in headers if k.lower() == "location"]
    require(len(values) == 1 and values[0] == endpoint(HOSTS[1], height), "Unverified/duplicate redirect or changed block path")
    return values[0]


def transport_for(url, remaining):
    parsed = urlsplit(url)
    height = int(parsed.path.split("/")[-2])
    require(url == endpoint(parsed.hostname, height), "Unverified request URL")
    require(remaining > 0, "Pilot lifetime download cap reached")
    module = r.load_base("bounded_header_transport")
    module.HOST, module.PATH, module.URL = parsed.hostname, parsed.path, url
    module.HEADERS = [[k, module.HOST if k.lower() == "host" else v] for k, v in b.HEADERS]
    module.MAX_BODY = min(b.MAX_BODY, remaining)
    return module


def read_hop(directory, url, height):
    module = transport_for(url, TOTAL_BODY_CAP)
    expected = {"request.http", "request.json", "response.body", "metadata.json"}
    if not expected <= {p.name for p in directory.iterdir()}:
        return {"kind": "INTERRUPTED", "directory": str(directory)}
    raw, desc, body = [(directory/name).read_bytes() for name in ("request.http", "request.json", "response.body")]
    meta = c.decode((directory/"metadata.json").read_bytes())
    require(raw == module.request_bytes() and desc == c.json_bytes(module.description()), "Changed saved request")
    require(meta.get("request_sha256") == c.sha256(raw) and meta.get("request_bytes") == len(raw)
            and meta.get("request_description_sha256") == c.sha256(desc)
            and meta.get("response_sha256") == c.sha256(body) and meta.get("response_bytes") == len(body), "Saved capture checksum/length mismatch")
    require(meta.get("endpoint") == url and meta.get("request_http_method") == "GET"
            and meta.get("request_path") == module.PATH, "Saved endpoint identity changed")
    r.timestamp_order(meta)
    c.integer(meta.get("transport_elapsed_ns"), "transport_elapsed_ns")
    sources = [b.fingerprint(directory/name) for name in sorted(expected)]
    if meta.get("body_complete") is not True or meta.get("transport_error") or len(body) > b.MAX_BODY:
        return {"kind": "ERROR", "metadata": meta, "sources": sources}
    if meta["http_status"] == 302:
        return {"kind": "REDIRECT", "url": redirect(meta["response_headers"], height), "metadata": meta, "sources": sources}
    if meta["http_status"] != 200:
        return {"kind": "ERROR", "metadata": meta, "sources": sources}
    value = c.decode(body)
    return {"kind": "NULL" if value is None else "BLOCK", "value": value, "metadata": meta,
            "sources": sources}


def read_attempt(directory, height, control):
    first = directory/"hop-00"
    if not first.exists():
        return {"kind": "INTERRUPTED"}
    result = read_hop(first, endpoint(HOSTS[0], height), height)
    if result["kind"] == "REDIRECT":
        original_sources = result["sources"]
        second = directory/"hop-01"
        if not second.exists():
            return {"kind": "INTERRUPTED"}
        result = read_hop(second, endpoint(HOSTS[1], height), height)
        require(result["kind"] != "REDIRECT", "Second redirect; stop without following")
        result["sources"] = original_sources+result.get("sources", [])
    if result["kind"] == "BLOCK":
        result["block"] = normalize(result.pop("value"), height, control)
    elif result["kind"] == "NULL":
        result.pop("value")
    return result


def scan(store, prepared):
    cache = {int(h): row for h, row in prepared["seeds"].items()}
    control = cache[START]["block"]
    attempts = store/"attempts"
    if not attempts.exists():
        return cache
    for height_dir in sorted(attempts.iterdir()):
        require(height_dir.is_dir() and height_dir.name.isdigit() and START <= int(height_dir.name) <= END, "Unexpected cached height")
        height = int(height_dir.name)
        require(len(list(height_dir.iterdir())) <= MAX_ATTEMPTS, "Cached manual attempt cap exceeded")
        for attempt in sorted(height_dir.iterdir()):
            require(attempt.is_dir() and attempt.name in {"01", "02"}, "Unexpected attempt file")
            result = read_attempt(attempt, height, control)
            if result["kind"] not in {"BLOCK", "NULL"}:
                continue
            if height in cache:
                if cache[height]["kind"] == result["kind"] == "BLOCK":
                    require(cache[height]["block"] == result["block"], "Conflicting cached height/hash/monetary fields")
                elif cache[height]["kind"] == "NULL" and result["kind"] == "BLOCK":
                    cache[height] = result  # null never asserted that a block was absent
            else:
                cache[height] = result
    return cache


def walk(cache, prepared):
    prev = cache[START-1]["block"]
    known = {prev["header"]["hash"]: prev["header"]["height"]}
    known_chunks = {x["chunk_hash"]: x for x in prev["chunks"]}
    pending, rows, net, outside = [], [], 0, []
    for height in range(START, END+1):
        if height not in cache:
            return {"complete": False, "next_height": height, "rows": rows, "pending_null_heights": pending,
                    "observed_prefix_net_debit_yocto": str(net), "outside_scope_creation_predecessors": outside}
        row = cache[height]
        if row["kind"] == "NULL":
            pending.append(height)
            require(len(pending) <= 1, "Unexplained consecutive nulls; positive chain evidence required before continuing")
            continue
        block, h, p = row["block"], row["block"]["header"], prev["header"]
        require(h["hash"] not in known, "Conflicting repeated block hash at another height")
        require(h["prev_height"] == p["height"] and h["prev_hash"] == p["hash"]
                and int(h["timestamp_nanosec"]) > int(p["timestamp_nanosec"]), "Conflicting predecessor continuity or time")
        require(list(range(p["height"]+1, height)) == pending, "Unexplained gap without retained null and predecessor evidence")
        for gap in pending:
            rows.append({"height": gap, "status": "SKIP_SUPPORTED_BY_SUCCESSOR_PREDECESSOR",
                         "successor_height": height, "successor_hash": h["hash"], "prev_height": p["height"],
                         "prev_hash": p["hash"], "null_response_sources": cache[gap]["sources"], "net_debit_yocto": None})
        pending = []
        debit = 0
        for index, chunk in enumerate(block["chunks"]):
            old = prev["chunks"][index]
            if chunk["chunk_hash"] in known_chunks:
                require(chunk == known_chunks[chunk["chunk_hash"]], "Conflicting chunk hash/fields across observations")
            known_chunks[chunk["chunk_hash"]] = chunk
            if chunk["height_included"] != height:
                require(chunk == old, "Carried-forward header changed or unexplained inclusion gap")
                continue
            require(chunk["chunk_hash"] != old["chunk_hash"], "Previously included chunk relabelled as new")
            if chunk["height_created"] == height:
                require(chunk["prev_block_hash"] == p["hash"], "Fresh chunk predecessor mismatch")
            elif chunk["prev_block_hash"] not in known:
                require(chunk["height_created"] < START, "Unexplained in-scope delayed chunk predecessor")
                outside.append({"height": height, "shard_id": chunk["shard_id"], "prev_block_hash": chunk["prev_block_hash"]})
            else:
                require(known[chunk["prev_block_hash"]] < chunk["height_created"], "Delayed chunk predecessor ordering mismatch")
            debit += int(chunk["balance_burnt"])
        if height > START:
            # Historical same-epoch constructor has no epoch reward mint input.
            require(int(h["total_supply"]) == int(p["total_supply"])-debit, "Same-epoch supply/net-header identity discrepancy")
        net += debit
        known[h["hash"]] = height
        rows.append({"height": height, "status": "PRODUCED", "hash": h["hash"], "prev_hash": h["prev_hash"],
                     "net_debit_yocto": str(debit), "header": h, "chunks": block["chunks"], "sources": row["sources"]})
        prev = block
    return {"complete": not pending, "next_height": None, "rows": rows, "pending_null_heights": pending,
            "observed_prefix_net_debit_yocto": str(net), "outside_scope_creation_predecessors": outside,
            "last_produced_height": prev["header"]["height"], "closing_supply_yocto": prev["header"]["total_supply"]}


def body_bytes(store):
    return sum(p.stat().st_size for p in (store/"attempts").rglob("response.body*")) if (store/"attempts").exists() else 0


def ratio(numerator, denominator):
    if not denominator:
        return None
    with localcontext() as ctx:
        ctx.prec = 40
        return str(Decimal(numerator)/Decimal(denominator))


def metrics(store):
    paths = list((store/"attempts").rglob("metadata.json")) if (store/"attempts").exists() else []
    metas = [c.decode(p.read_bytes()) for p in paths]
    elapsed = sum(x["transport_elapsed_ns"] for x in metas)
    downloaded = sum(x["response_bytes"] for x in metas)
    sizes = sorted(x["response_bytes"] for p, x in zip(paths, metas) if x["http_status"] == 200 and x.get("body_complete")
                   and p.with_name("response.body").read_bytes().strip() != b"null")
    sessions = []
    if (store/"sessions").exists():
        for directory in sorted((store/"sessions").iterdir()):
            found = False
            for name in ("stopped.json", "finished.json"):
                if (directory/name).exists():
                    sessions.append(c.decode((directory/name).read_bytes()))
                    found = True
                    break
            if not found:
                sessions.append({"session_directory": str(directory), "status": "INTERRUPTED_OR_RUNNING", "wall_elapsed_ns": None})
    return {"new_http_responses_recorded": len(metas), "downloaded_body_bytes_all_attempts": downloaded,
            "summed_transport_elapsed_ns": elapsed, "observed_body_bytes_per_transport_second": ratio(downloaded*10**9, elapsed),
            "observed_http_status_counts": dict(Counter(str(x["http_status"]) for x in metas)),
            "retained_unpublished_body_draft_bytes": sum(p.stat().st_size for p in (store/"attempts").rglob("response.body.writing-*")) if (store/"attempts").exists() else 0,
            "http200_body_size_min": min(sizes) if sizes else None, "http200_body_size_max": max(sizes) if sizes else None,
            "http200_body_size_p95": sizes[(95*len(sizes)+99)//100-1] if sizes else None,
            "raw_store_logical_bytes_excluding_validation_reports": sum(p.stat().st_size for p in store.rglob("*") if p.is_file() and p.name != "validation.json"),
            "reused_seed_download_bytes": 0, "full_interval_volume_or_throughput_projection": None,
            "session_records": sessions}


def validate(store, prepared=None):
    prepared = plan() if prepared is None else prepared
    manifest = c.decode((store/"manifest.json").read_bytes())
    require(manifest["plan"] == prepared, "Store plan/inputs/code changed")
    cache = scan(store, prepared)
    result = walk(cache, prepared)
    opening = cache[START-1]["block"]["header"]
    produced = [row for row in result["rows"] if row["status"] == "PRODUCED"]
    last = produced[-1]["header"] if produced else None
    result["opening_parent"] = {k: opening[k] for k in ("height", "hash", "timestamp_nanosec", "total_supply")}
    result["observed_prefix_closing_header"] = last
    result["pilot_net_supply_movement_yocto"] = str(int(last["total_supply"])-int(opening["total_supply"])) if result["complete"] and last else None
    result["unresolved_null_observations"] = [{"height": h, "sources": row["sources"]} for h, row in cache.items()
                                             if row["kind"] == "NULL" and h in result["pending_null_heights"]]
    week = c.decode(WEEK.read_bytes())
    mint = next(x for x in week["boundaries"] if x["height"] == START)
    require(mint["hash"] == cache[START]["block"]["header"]["hash"] and mint["protocol_verified"] is True, "Mint application control mismatch")
    result.update(scope="CONTIGUOUS_PILOT_NOT_FULL_INTERVAL", pilot_interval=[START, END],
                  independently_recorded_A_reward_mint_yocto=mint["recorded_reward_map_yocto"],
                  net_debit_complete_yocto=result["observed_prefix_net_debit_yocto"] if result["complete"] else None,
                  gross_actual_burn_yocto=None, subsidies_yocto=None, independent_weekly_net_debit_yocto=None,
                  coverage="Observed predecessor chain from saved canonical A; pilot tail lacks a separate canonical tip control",
                  performance=metrics(store), raw_store=str(store.resolve()),
                  source_manifest=b.fingerprint(store/"manifest.json"))
    if result["complete"]:
        expected = int(cache[START-1]["block"]["header"]["total_supply"])+int(mint["recorded_reward_map_yocto"])-int(result["observed_prefix_net_debit_yocto"])
        result["pilot_supply_identity_discrepancy_yocto"] = str(int(result["closing_supply_yocto"])-expected)
        require(result["pilot_supply_identity_discrepancy_yocto"] == "0", "Pilot mint/supply/net-header identity discrepancy")
    return result


def capture_hop(store, directory, host, height, session, transport, pause):
    require(session["new_http_requests"] < MAX_SESSION_REQUESTS, "Session request cap reached")
    remaining = TOTAL_BODY_CAP-body_bytes(store)
    url = endpoint(host, height)
    module = transport_for(url, remaining)
    directory.mkdir()
    raw, desc = module.request_bytes(), c.json_bytes(module.description())
    write_new(directory/"request.http", raw)
    write_new(directory/"request.json", desc)
    print(f"Waiting {SPACING}s before {host} height {height}; one attempt, no retry.", flush=True)
    pause(SPACING)
    started, monotonic = c.utc_now(), time.monotonic_ns()
    session["new_http_requests"] += 1
    meta, response = transport(url, raw) if transport else module.fetch(raw)
    duration = time.monotonic_ns()-monotonic
    meta.update(endpoint=url, started_at=started, finished_at=c.utc_now(), transport_elapsed_ns=duration,
                request_http_method="GET", request_path=module.PATH, request_sha256=c.sha256(raw), request_bytes=len(raw),
                request_description_sha256=c.sha256(desc), response_sha256=c.sha256(response), response_bytes=len(response))
    write_new(directory/"response.body", response)
    write_new(directory/"metadata.json", c.json_bytes(meta))
    require(len(response) <= remaining, "Lifetime pilot body cap exceeded; evidence retained")
    return read_hop(directory, url, height)


def collect(store=STORE, transport=None, pause=None):
    store = store.resolve()
    require(not store.is_relative_to(ROOT) and not ROOT.is_relative_to(store), "Raw evidence must live outside the checkout")
    prepared = plan()
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Frozen plan 84 differs; review offline")
    store.mkdir(parents=True, exist_ok=True)
    with (store/".collector.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if not (store/"manifest.json").exists():
            write_new(store/"manifest.json", c.json_bytes({"created_at": c.utc_now(), "plan": prepared}))
        require(c.decode((store/"manifest.json").read_bytes())["plan"] == prepared, "Changed resumable store plan")
        sessions = store/"sessions"
        sessions.mkdir(exist_ok=True)
        directory = sessions/f"{len(list(sessions.iterdir()))+1:04d}"
        directory.mkdir()
        session = {"started_at": c.utc_now(), "new_http_requests": 0}
        write_new(directory/"started.json", c.json_bytes(session))
        began, before_bytes = time.monotonic_ns(), body_bytes(store)
        pause = time.sleep if pause is None else pause
        print(f"Evidence store: {store}", flush=True)
        try:
            cache = scan(store, prepared)
            while True:
                progress = walk(cache, prepared)
                if progress["next_height"] is None:
                    require(progress["complete"], "Trailing null lacks a successor witness inside the 100-height cap")
                    break
                height = progress["next_height"]
                attempts = store/"attempts"/str(height)
                attempts.mkdir(parents=True, exist_ok=True)
                require(len(list(attempts.iterdir())) < MAX_ATTEMPTS, "Manual per-height attempt cap reached")
                attempt = attempts/f"{len(list(attempts.iterdir()))+1:02d}"
                attempt.mkdir()
                first = capture_hop(store, attempt/"hop-00", HOSTS[0], height, session, transport, pause)
                if first["kind"] == "REDIRECT":
                    second = capture_hop(store, attempt/"hop-01", HOSTS[1], height, session, transport, pause)
                    require(second["kind"] != "REDIRECT", "Second redirect; no additional follow")
                result = read_attempt(attempt, height, cache[START]["block"])
                require(result["kind"] in {"BLOCK", "NULL"}, "HTTP/transport unavailable; explicit manual resume only")
                cache[height] = result
            report = validate(store, prepared)
            session.update(finished_at=c.utc_now(), wall_elapsed_ns=time.monotonic_ns()-began, status="COMPLETE")
            session["new_http_requests_per_wall_second"] = ratio(session["new_http_requests"]*10**9, session["wall_elapsed_ns"])
            session["downloaded_body_bytes"] = body_bytes(store)-before_bytes
            session["downloaded_body_bytes_per_wall_second"] = ratio(session["downloaded_body_bytes"]*10**9, session["wall_elapsed_ns"])
            write_new(directory/"finished.json", c.json_bytes(session))
            report["performance"] = metrics(store)
            write_new(directory/"validation.json", c.json_bytes(report))
            print(f"Pilot complete; {session['new_http_requests']} new HTTP requests. Review {directory/'validation.json'} before proposing the full interval.")
            return report
        except (Exception, KeyboardInterrupt) as exc:
            session.update(finished_at=c.utc_now(), wall_elapsed_ns=time.monotonic_ns()-began,
                           error=f"{type(exc).__name__}: {exc}", automatic_retry=False, status="STOPPED")
            session["downloaded_body_bytes"] = body_bytes(store)-before_bytes
            session["downloaded_body_bytes_per_wall_second"] = ratio(session["downloaded_body_bytes"]*10**9, session["wall_elapsed_ns"])
            write_new(directory/"stopped.json", c.json_bytes(session))
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("plan", help="OFFLINE: print fixed pilot and cached controls")
    p.add_argument("--output", type=Path)
    for command in ("collect", "validate"):
        p = subs.add_parser(command, help="Manual pilot/resume" if command == "collect" else "OFFLINE: validate saved pilot")
        p.add_argument("--store", type=Path, default=STORE)
        if command == "validate":
            p.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "collect":
            collect(args.store)
            return 0
        report = plan() if args.command == "plan" else validate(args.store)
        raw = c.json_bytes(report)
        if args.output:
            write_new(args.output, raw)
        else:
            sys.stdout.write(raw.decode())
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(f"Stopped: {exc}. No automatic retry or scope expansion.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
