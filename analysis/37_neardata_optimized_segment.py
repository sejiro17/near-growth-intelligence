"""Bounded four-worker Neardata header segment. plan/validate are offline.

Only the next 1,000 height slots are enabled. Full-interval collection is disabled.
"""

import argparse
import fcntl
import http.client
import importlib.util
import shutil
import ssl
import sys
import threading
import time
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("original_header_pilot", ROOT/"analysis/36_neardata_header_pilot.py")
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
c, require, write_new = p.c, p.require, p.write_new
START, END = 216878034, 216879033
FULL_START, FULL_END = p.START, p.FULL_END
HOST = "a3.mainnet.neardata.xyz"
STORE = p.STORE.parent/"optimized_216878034_216879033"
PLAN = ROOT/"results/87_neardata_optimized_segment_plan.json"
PREVIOUS = ROOT/"results/85_neardata_header_pilot_validation_216877934_to_216878033.json"
PROPOSAL = ROOT/"results/86_neardata_full_interval_collection_proposal.json"
WEEK_PLAN = ROOT/"results/66_supply_weekly_header_pilot_plan.json"
WORKERS, AHEAD, RPM, SPACING_NS = 4, 16, 120, 500_000_000
BODY_CAP, STORE_CAP, RESPONSE_CAP = 2*1024**3, 8*1024**3, 32*1024**2
FREE_START, FREE_STOP = 10*1024**3, 2*1024**3
SESSION_CAP, LIFETIME_CAP, ATTEMPTS = 4096, 86198, 2
# http.client permits at most 100 header lines of 65,536 bytes each. Reserve
# their worst-case JSON encoding plus request files before allowing a request.
META_RESERVE = 64*1024**2
FILES = ("request.http", "request.json", "response.body", "metadata.json")


def fingerprint(path):
    return p.b.fingerprint(path)


def plan():
    require(START == 216878034 and END == 216879033 and END-START+1 == 1000,
            "Only the authorized 1,000-height segment is enabled")
    previous = p.validate(p.STORE)
    require(c.json_bytes(previous) == PREVIOUS.read_bytes() and previous["complete"], "Result 85 no longer reproduces")
    proposal = c.decode(PROPOSAL.read_bytes())
    closing_sources = proposal["closing_control_sources"]
    for source in closing_sources:
        require(fingerprint(Path(source["path"])) == source, "Changed closing control input")
    request = next(Path(x["path"]) for x in closing_sources if x["path"].endswith(".request.json"))
    closing = c.recorded(request.parent, c.decode(request.read_bytes()))
    seeds = {str(FULL_START-1): p.plan()["seeds"][str(FULL_START-1)]}
    for row in previous["rows"]:
        require(row["status"] == "PRODUCED", "Review seed skips before extending")
        seeds[str(row["height"])] = {"kind": "BLOCK", "block": {"header": row["header"], "chunks": row["chunks"]}, "sources": row["sources"]}
    control = seeds[str(FULL_START)]["block"]
    closing = p.normalize(closing, FULL_END, control)
    require(closing["header"]["hash"] == p.c.TARGETS["B"]["parent"], "Wrong canonical closing control")
    return {"status": "1000_HEIGHT_SEGMENT_ONLY_FULL_COLLECTION_DISABLED", "network": "mainnet",
            "segment": [START, END], "full_interval": [FULL_START, FULL_END], "endpoint_host": HOST,
            "raw_store": str(STORE), "workers": WORKERS, "maximum_ahead": AHEAD,
            "global_rolling_60_second_request_starts": RPM, "minimum_start_spacing_ns": SPACING_NS,
            "response_body_cap": RESPONSE_CAP, "lifetime_response_body_cap": BODY_CAP,
            "lifetime_store_cap": STORE_CAP, "session_request_cap": SESSION_CAP,
            "lifetime_request_cap": LIFETIME_CAP, "maximum_attempts_per_height": ATTEMPTS,
            "automatic_retries": 0, "automatic_redirects": False, "connect_timeout_seconds": 15,
            "request_timeout_seconds": 60, "free_start_bytes": FREE_START, "free_stop_bytes": FREE_STOP,
            "seeds": seeds, "canonical_closing_control": {"block": closing, "sources": closing_sources},
            "reward_mint_yocto": previous["independently_recorded_A_reward_mint_yocto"],
            "inputs": [fingerprint(x) for x in (PREVIOUS, PROPOSAL, WEEK_PLAN, p.PLAN, p.WEEK, Path(__file__), Path(p.__file__), Path(p.r.__file__), Path(p.b.__file__), Path(c.__file__))]}


def request_parts(height):
    require(type(height) is int and START <= height <= END, "Height outside enabled segment")
    path = f"/v0/block/{height}/headers"
    headers = [["Host", HOST], ["Accept", "application/json"], ["Accept-Encoding", "identity"],
               ["Connection", "keep-alive"], ["User-Agent", "near-growth-intelligence-bounded-headers/1"]]
    raw = ("GET "+path+" HTTP/1.1\r\n"+"".join(k+": "+v+"\r\n" for k,v in headers)+"\r\n").encode("ascii")
    desc = {"method": "GET", "url": "https://"+HOST+path, "path": path, "headers": headers, "body_bytes": 0}
    return raw, desc


class Limiter:
    """One process-wide start gate; restore recent starts on explicit resume."""
    def __init__(self, recent=(), clock=time.monotonic_ns, sleep=time.sleep):
        self.clock, self.sleep, self.lock = clock, sleep, threading.Lock()
        self.starts = deque(sorted(recent))
        self.last = self.starts[-1] if self.starts else None

    def acquire(self, stop):
        with self.lock:
            while True:
                require(not stop.is_set(), "Scheduling stopped before request start")
                now = self.clock()
                while self.starts and now-self.starts[0] >= 60*10**9:
                    self.starts.popleft()
                due = now if self.last is None else max(now, self.last+SPACING_NS)
                if len(self.starts) >= RPM:
                    due = max(due, self.starts[0]+60*10**9)
                if due <= now:
                    self.starts.append(now)
                    self.last = now
                    return now
                self.sleep(min((due-now)/10**9, 0.5))


def sizes(store):
    files = [x for x in store.rglob("*") if x.is_file()]
    return (sum(x.stat().st_size for x in files if x.name.startswith("response.body")),
            sum(x.stat().st_size for x in files))


class Budget:
    def __init__(self, store):
        self.store, self.lock = store, threading.Lock()
        self.body, self.total = sizes(store)
        self.reserved_body = self.reserved_store = 0

    def reserve(self):
        with self.lock:
            require(shutil.disk_usage(self.store).free >= FREE_STOP, "Free-space stop threshold")
            require(self.body+self.reserved_body+RESPONSE_CAP <= BODY_CAP, "Lifetime response-body cap")
            # Temporary and final hard-link names may coexist while publishing.
            require(self.total+self.reserved_store+2*RESPONSE_CAP+META_RESERVE <= STORE_CAP, "Lifetime total-store cap")
            self.reserved_body += RESPONSE_CAP
            self.reserved_store += 2*RESPONSE_CAP+META_RESERVE

    def finish(self, directory):
        with self.lock:
            body, total = sizes(directory)
            self.reserved_body -= RESPONSE_CAP
            self.reserved_store -= 2*RESPONSE_CAP+META_RESERVE
            self.body += body
            self.total += total
            require(self.body <= BODY_CAP and self.total <= STORE_CAP, "Stored evidence cap exceeded")

    def publish(self, path, value):
        raw = c.json_bytes(value)
        with self.lock:
            require(self.total+self.reserved_store+2*len(raw) <= STORE_CAP, "Report/checkpoint store cap")
            write_new(path, raw)
            self.total += len(raw)


class Transport:
    """Per-worker TLS connection reuse; never retries or follows redirects."""
    def __init__(self):
        self.local = threading.local()
        self.connections, self.lock = [], threading.Lock()

    def __call__(self, height, raw):
        expected, desc = request_parts(height)
        require(raw == expected, "Unexpected HTTP request")
        conn = getattr(self.local, "connection", None)
        reused = conn is not None and conn.sock is not None
        if not reused:
            conn = http.client.HTTPSConnection(HOST, timeout=15, context=ssl.create_default_context())
            self.local.connection = conn
            with self.lock:
                self.connections.append(conn)
        body, response = bytearray(), None
        meta = {"http_status": None, "response_headers": [], "body_complete": False, "transport_error": None,
                "connection_reused": reused}
        deadline = time.monotonic()+60
        try:
            if not reused:
                conn.connect()
            sock = conn.sock
            require(sock is not None, "Missing TLS connection")
            sock.settimeout(max(0.001, deadline-time.monotonic()))
            conn.putrequest("GET", desc["path"], skip_host=True, skip_accept_encoding=True)
            for key,value in desc["headers"]:
                conn.putheader(key, value)
            conn.endheaders()
            response = conn.getresponse()
            meta.update(http_status=response.status, response_headers=response.getheaders(),
                        http_version=response.version, http_reason=response.reason)
            require(not response.getheader("Content-Encoding") or response.getheader("Content-Encoding") == "identity", "Unexpected content encoding")
            require(response.length is None or response.length <= RESPONSE_CAP, "Declared response exceeds body cap")
            while not response.isclosed():
                require(len(body) < RESPONSE_CAP, "Body cap reached before confirmed completion")
                remaining = deadline-time.monotonic()
                require(remaining > 0, "Request deadline exceeded")
                sock.settimeout(remaining)
                body.extend(response.read1(min(65536, RESPONSE_CAP-len(body))))
            require(response.length in (None, 0), "Truncated Content-Length response")
            meta["body_complete"] = True
        except Exception as exc:
            if isinstance(exc, http.client.IncompleteRead):
                body.extend(exc.partial[:max(0, RESPONSE_CAP-len(body))])
            meta["transport_error"] = f"{type(exc).__name__}: {exc}"
            conn.close()
        finally:
            if response is not None:
                response.close()
        return meta, bytes(body)

    def close(self):
        for conn in self.connections:
            conn.close()


def read_attempt(directory, height, control):
    if not all((directory/name).exists() for name in FILES):
        return {"kind": "INTERRUPTED"}
    raw, desc = request_parts(height)
    body = (directory/"response.body").read_bytes()
    meta = c.decode((directory/"metadata.json").read_bytes())
    require((directory/"request.http").read_bytes() == raw and (directory/"request.json").read_bytes() == c.json_bytes(desc), "Saved request changed")
    require(meta.get("endpoint") == desc["url"] and meta.get("request_path") == desc["path"] and meta.get("request_http_method") == "GET", "Saved endpoint changed")
    require(meta.get("request_sha256") == c.sha256(raw) and meta.get("request_bytes") == len(raw)
            and meta.get("request_description_sha256") == c.sha256(c.json_bytes(desc))
            and meta.get("response_sha256") == c.sha256(body) and meta.get("response_bytes") == len(body), "Saved checksum/length mismatch")
    p.r.timestamp_order(meta)
    c.integer(meta.get("transport_elapsed_ns"), "transport_elapsed_ns")
    c.integer(meta.get("request_started_monotonic_ns"), "request_started_monotonic_ns")
    require(len(body) <= RESPONSE_CAP, "Oversize retained response")
    sources = [fingerprint(directory/name) for name in FILES]
    if not meta.get("body_complete") or meta.get("transport_error") or meta.get("http_status") != 200:
        return {"kind": "ERROR", "metadata": meta, "sources": sources}
    value = c.decode(body)
    return {"kind": "NULL" if value is None else "BLOCK", "block": None if value is None else p.normalize(value,height,control),
            "metadata": meta, "sources": sources}


def scan(store, prepared):
    cache = {int(k):v for k,v in prepared["seeds"].items()}
    metas, attempts = [], 0
    root = store/"attempts"
    if root.exists():
        for hd in sorted(root.iterdir()):
            require(hd.is_dir() and hd.name.isdigit() and START <= int(hd.name) <= END, "Unexpected saved height")
            height = int(hd.name)
            dirs = sorted(hd.iterdir())
            require(len(dirs) <= ATTEMPTS, "Lifetime per-height attempt cap")
            for directory in dirs:
                require(directory.is_dir() and directory.name in {"01","02"}, "Unexpected attempt directory")
                attempts += 1
                row = read_attempt(directory,height,cache[FULL_START]["block"])
                if "metadata" in row:
                    metas.append(row["metadata"])
                if row["kind"] in {"BLOCK","NULL"}:
                    require(height not in cache or (cache[height]["kind"] == row["kind"] and cache[height].get("block") == row.get("block")), "Conflicting saved identities")
                    cache[height] = row
    require(attempts <= LIFETIME_CAP, "Lifetime request cap")
    return cache, metas, attempts


class Chain:
    def __init__(self, prepared):
        self.prepared = prepared
        self.previous = prepared["seeds"][str(FULL_START-1)]["block"]
        self.known = {self.previous["header"]["hash"]: FULL_START-1}
        self.chunks = {x["chunk_hash"]: x for x in self.previous["chunks"]}
        self.pending, self.skips, self.outside = [], [], []
        self.net = self.segment_net = self.produced = self.segment_produced = self.included = self.carried = 0
        self.next = FULL_START

    def push(self, height, row):
        require(height == self.next, "Out-of-order chain acceptance")
        self.next += 1
        if row["kind"] == "NULL":
            self.pending.append(height)
            require(len(self.pending) <= 1, "Consecutive nulls lack a bounded successor witness")
            return
        require(row["kind"] == "BLOCK", "Unavailable chain comparison")
        block = row["block"]
        h, prev = block["header"], self.previous["header"]
        require(h["hash"] not in self.known and h["prev_height"] == prev["height"] and h["prev_hash"] == prev["hash"]
                and int(h["timestamp_nanosec"]) > int(prev["timestamp_nanosec"]), "Predecessor/hash/time conflict")
        require(list(range(prev["height"]+1,height)) == self.pending, "Unexplained missing heights")
        self.skips.extend({"height":x,"successor_height":height,"successor_hash":h["hash"],"prev_height":prev["height"],"prev_hash":prev["hash"],"net_debit_yocto":None} for x in self.pending)
        self.pending = []
        debit = 0
        for index,chunk in enumerate(block["chunks"]):
            old = self.previous["chunks"][index]
            if chunk["chunk_hash"] in self.chunks:
                require(chunk == self.chunks[chunk["chunk_hash"]], "Conflicting repeated chunk fields")
            self.chunks[chunk["chunk_hash"]] = chunk
            if chunk["height_included"] != height:
                require(chunk == old, "Carried header changed")
                self.carried += 1
                continue
            require(chunk["chunk_hash"] != old["chunk_hash"], "Old chunk relabelled as new")
            if chunk["height_created"] == height:
                require(chunk["prev_block_hash"] == prev["hash"], "Fresh chunk predecessor conflict")
            elif chunk["prev_block_hash"] not in self.known:
                require(chunk["height_created"] < FULL_START, "Unknown in-scope creation predecessor")
                self.outside.append({"height":height,"shard_id":chunk["shard_id"],"prev_block_hash":chunk["prev_block_hash"]})
            else:
                require(self.known[chunk["prev_block_hash"]] < chunk["height_created"], "Delayed chunk ordering conflict")
            debit += int(chunk["balance_burnt"])
            self.included += 1
        mint = int(self.prepared["reward_mint_yocto"]) if height == FULL_START else 0
        require(int(h["total_supply"]) == int(prev["total_supply"])+mint-debit, "Integer supply/net-debit identity discrepancy")
        self.net += debit
        self.produced += 1
        if height >= START:
            self.segment_net += debit
            self.segment_produced += 1
        self.known[h["hash"]] = height
        self.previous = block


def chain_from(cache, prepared):
    chain = Chain(prepared)
    while chain.next <= END and chain.next in cache:
        chain.push(chain.next,cache[chain.next])
    return chain


def summary(chain, prepared):
    complete = chain.next == END+1 and not chain.pending
    opening = prepared["seeds"][str(START-1)]["block"]["header"]
    ending = chain.previous["header"]
    movement = int(ending["total_supply"])-int(opening["total_supply"]) if ending["height"] >= START else None
    return {"scope":"1000_HEIGHT_OPTIMIZED_SEGMENT_NOT_FULL_EPOCH", "complete":complete,
            "segment":[START,END], "last_validated_height":ending["height"], "next_unvalidated_height":chain.next,
            "segment_produced_blocks":chain.segment_produced, "cumulative_produced_blocks_including_pilot":chain.produced,
            "opening_header":opening, "closing_observed_header":ending, "supported_skips":chain.skips,
            "unresolved_null_heights":chain.pending, "outside_scope_creation_predecessors":chain.outside,
            "cumulative_new_inclusions":chain.included, "cumulative_carried_headers_excluded":chain.carried,
            "observed_segment_prefix_net_debit_yocto":str(chain.segment_net),
            "independent_complete_segment_net_debit_yocto":str(chain.segment_net) if complete else None,
            "segment_supply_movement_yocto":str(movement) if complete else None,
            "segment_supply_identity_discrepancy_yocto":str(movement+chain.segment_net) if complete else None,
            "cumulative_net_debit_including_pilot_yocto":str(chain.net),
            "protocol_validated_mint_at_A_yocto":prepared["reward_mint_yocto"],
            "cumulative_supply_identity_discrepancy_yocto":str(int(ending["total_supply"])-int(prepared["seeds"][str(FULL_START-1)]["block"]["header"]["total_supply"])-int(prepared["reward_mint_yocto"])+chain.net),
            "full_interval_closing_control_reached":False, "independent_full_epoch_net_debit_yocto":None,
            "independent_weekly_net_debit_yocto":None,"gross_actual_burn_yocto":None,"subsidies_yocto":None,
            "coverage":"Observed chain anchored at saved canonical A; segment tail has no separate canonical tip control"}


def capture(height, directory, limiter, stop, transport, budget):
    raw, desc = request_parts(height)
    try:
        write_new(directory/"request.http",raw)
        write_new(directory/"request.json",c.json_bytes(desc))
        started_mono = limiter.acquire(stop)
        started = c.utc_now()
        meta, body = transport(height,raw)
        require(len(body) <= RESPONSE_CAP, "Transport returned an oversized body")
        meta.update(endpoint=desc["url"],started_at=started,finished_at=c.utc_now(),
                    request_started_monotonic_ns=started_mono,transport_elapsed_ns=time.monotonic_ns()-started_mono,
                    request_http_method="GET",request_path=desc["path"],request_sha256=c.sha256(raw),request_bytes=len(raw),
                    request_description_sha256=c.sha256(c.json_bytes(desc)),response_sha256=c.sha256(body),response_bytes=len(body))
        write_new(directory/"response.body",body)
        require(len(c.json_bytes(meta)) < META_RESERVE//2, "Oversized HTTP metadata")
        write_new(directory/"metadata.json",c.json_bytes(meta))
        return directory
    finally:
        budget.finish(directory)


def recent_starts(metas, mono=time.monotonic_ns, utc=time.time_ns):
    now, wall = mono(),utc()
    recent = []
    for meta in metas:
        stamp = datetime.fromisoformat(meta["started_at"])
        epoch_delta = stamp-datetime(1970,1,1,tzinfo=timezone.utc)
        stamp_ns = (epoch_delta.days*86400+epoch_delta.seconds)*10**9+epoch_delta.microseconds*1000
        delta = wall-stamp_ns
        require(delta >= -10**9, "Future request timestamp; inspect system clock")
        if delta < 60*10**9:
            recent.append(now-max(0,delta))
    return recent


def rate_audit(metas):
    groups = {}
    for meta in metas:
        groups.setdefault(meta["session_id"],[]).append(meta["request_started_monotonic_ns"])
    gaps, maximum = [], 0
    for values in groups.values():
        values.sort()
        gaps.extend(b-a for a,b in zip(values,values[1:]))
        recent = deque()
        for stamp in values:
            while recent and stamp-recent[0] >= 60*10**9:
                recent.popleft()
            recent.append(stamp)
            maximum=max(maximum,len(recent))
    require(not gaps or min(gaps) >= SPACING_NS, "Shared request-spacing violation")
    require(maximum <= RPM, "Rolling request-rate violation")
    return {"maximum_starts_in_any_session_rolling_60_seconds":maximum,"minimum_start_gap_ns":min(gaps) if gaps else None,
            "cross_session_recent_starts_restored_on_resume":True}


def validate(store=STORE, prepared=None):
    prepared = plan() if prepared is None else prepared
    require(c.decode((store/"manifest.json").read_bytes())["plan"] == prepared, "Changed frozen plan/inputs")
    cache, metas, attempts = scan(store,prepared)
    result = summary(chain_from(cache,prepared),prepared)
    body,total = sizes(store)
    require(body <= BODY_CAP and total <= STORE_CAP, "Saved storage cap violation")
    sessions=[]
    if (store/"sessions").exists():
        for sd in sorted((store/"sessions").iterdir()):
            terminal = next((sd/x for x in ("finished.json","stopped.json") if (sd/x).exists()),None)
            sessions.append(c.decode(terminal.read_bytes()) if terminal else {"status":"INTERRUPTED_OR_RUNNING","session":str(sd)})
    result.update(raw_store=str(store.resolve()),manifest=fingerprint(store/"manifest.json"),
                  attempted_height_requests=attempts,http_responses=len(metas),
                  http_status_counts=dict(Counter(str(x["http_status"]) for x in metas)),
                  transport_or_http_errors=sum(not x.get("body_complete") or bool(x.get("transport_error")) or x.get("http_status")!=200 for x in metas),
                  response_body_bytes=sum(x["response_bytes"] for x in metas),retained_body_bytes_including_drafts=body,
                  response_body_min_bytes=min((x["response_bytes"] for x in metas),default=None),
                  response_body_max_bytes=max((x["response_bytes"] for x in metas),default=None),
                  reused_connections=sum(x.get("connection_reused") is True for x in metas),
                  rate_audit=rate_audit(metas),sessions=sessions,
                  capture_index=[{"height":h,"kind":row["kind"],"sources":row["sources"]} for h,row in sorted(cache.items()) if START <= h <= END])
    # Exclude derived reports to make reproducing this report stable.
    result["raw_file_logical_bytes_excluding_session_reports"] = sum(x.stat().st_size for x in (store/"attempts").rglob("*") if x.is_file()) if (store/"attempts").exists() else 0
    result["raw_file_allocated_bytes_excluding_session_reports"] = sum(x.stat().st_blocks*512 for x in (store/"attempts").rglob("*") if x.is_file()) if (store/"attempts").exists() else 0
    result["sample_extrapolations"] = estimates(result)
    return result


def estimates(report):
    """Scenarios from measured wall time; neither response-size nor time bounds."""
    if not report["complete"] or not report["http_responses"] or any(x["status"] != "COMPLETE" for x in report["sessions"]):
        return None
    count=report["http_responses"]
    elapsed=sum(x["wall_elapsed_ns"] for x in report["sessions"])
    week=c.decode(WEEK_PLAN.read_bytes())
    targets={x["id"]:x["height"] for x in week["targets"]}
    slots=targets["week-closing"]-targets["week-opening"]
    remaining_epoch=FULL_END-END-1  # canonical closing header is already saved
    # Conservative request-slot estimate; additional saved RPC headers reduce it.
    known_slots=END-FULL_START+1+1  # prior pilot + segment + canonical epoch closing
    with localcontext() as context:
        context.prec=50
        mean=Decimal(report["response_body_bytes"])/count
        seconds=Decimal(elapsed)/10**9/count
        def scenario(n):
            return {"height_slots_to_model":n,"hours_at_measured_wall_time_per_request":str(Decimal(n)*seconds/3600),
                    "body_bytes_at_sample_mean":str(Decimal(n)*mean),
                    "body_bytes_at_twice_sample_mean":str(Decimal(n)*mean*2),
                    "body_bytes_at_four_times_sample_mean":str(Decimal(n)*mean*4),
                    "raw_logical_bytes_at_sample_file_proportions":str(Decimal(n)*report["raw_file_logical_bytes_excluding_session_reports"]/count),
                    "allocated_file_bytes_on_sample_filesystem":str(Decimal(n)*report["raw_file_allocated_bytes_excluding_session_reports"]/count)}
        return {"status":"SCENARIOS_NOT_BOUNDS_OR_ACQUIRED_COVERAGE", "sample_wall_seconds":str(Decimal(elapsed)/10**9),
                "sample_requests":count,"sample_requests_per_second":str(Decimal(count)*10**9/elapsed),
                "sample_body_bytes_per_request":str(mean),
                "remaining_epoch_after_segment":scenario(remaining_epoch),
                "whole_week_all_slots_before_reuse":scenario(slots),
                "remaining_week_slots_after_known_prefix_and_epoch_closing_before_other_saved_reuse":scenario(slots-known_slots),
                "weekly_height_boundaries":[targets["week-opening"],targets["week-closing"]],
                "week_not_authorized_or_supported_by_current_epoch_only_collector":True,
                "weekly_acquisition_exceeds_current_body_cap_at_sample_mean":Decimal(slots-known_slots)*mean>BODY_CAP,
                "limitations":"This narrow same-epoch sample does not bound other response sizes, layouts, archive routing, skipped slots, latency or filesystem overhead. Other saved RPC headers reduce weekly requests; complete weekly canonical census is not yet acquired. No automatic limit increase."}


def collect(store=STORE, prepared=None, transport=None, limiter=None):
    store = store.resolve()
    require(not store.is_relative_to(ROOT) and not ROOT.is_relative_to(store), "Raw evidence must live outside repository")
    prepared = plan() if prepared is None else prepared
    require(PLAN.read_bytes() == c.json_bytes(prepared), "Plan 87 differs; review offline")
    store.mkdir(parents=True,exist_ok=True)
    require(shutil.disk_usage(store).free >= FREE_START, "Require 10 GiB free before start")
    with (store/".collector.lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if not (store/"manifest.json").exists():
            require(len(c.json_bytes(prepared))*2 < STORE_CAP, "Manifest store cap")
            write_new(store/"manifest.json",c.json_bytes({"created_at":c.utc_now(),"plan":prepared}))
        require(c.decode((store/"manifest.json").read_bytes())["plan"] == prepared,"Changed resumable plan")
        cache, metas, lifetime = scan(store,prepared)
        chain = chain_from(cache,prepared)
        sessions=store/"sessions";sessions.mkdir(exist_ok=True)
        sd=sessions/f"{len(list(sessions.iterdir()))+1:04d}";sd.mkdir()
        session={"session_id":sd.name,"started_at":c.utc_now(),"new_requests":0}
        write_new(sd/"started.json",c.json_bytes(session))
        budget=Budget(store)
        limiter=Limiter(recent_starts(metas)) if limiter is None else limiter
        transport=Transport() if transport is None else transport
        stop=threading.Event(); futures={}; issued=set(); errors=[]
        began=time.monotonic_ns(); body_before=budget.body
        print(f"Evidence store: {store}; authorized segment {START}–{END}; four workers, shared {RPM}/minute.",flush=True)
        try:
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                while True:
                    while chain.next <= END and chain.next in cache:
                        try:
                            chain.push(chain.next,cache[chain.next])
                        except Exception:
                            stop.set()
                            raise
                        if (chain.next-START)%100 == 0 and chain.next > START:
                            print(f"Validated through {chain.next-1}; {session['new_requests']} requests scheduled; no scope expansion.",flush=True)
                    if chain.next > END:
                        require(not chain.pending,"Trailing null lacks an in-scope successor")
                        break
                    limit=min(END,chain.next+AHEAD-1)
                    if chain.pending:
                        limit=min(limit,chain.pending[-1]+1)
                    for height in range(max(START,chain.next),limit+1):
                        if stop.is_set() or len(futures) >= WORKERS:
                            break
                        if height in cache or height in issued:
                            continue
                        require(session["new_requests"] < min(SESSION_CAP,END-START+1),"Session request cap")
                        require(lifetime < LIFETIME_CAP,"Lifetime request cap")
                        hd=store/"attempts"/str(height);hd.mkdir(parents=True,exist_ok=True)
                        count=len(list(hd.iterdir()));require(count < ATTEMPTS,"Manual per-height attempt cap")
                        budget.reserve()
                        directory=hd/f"{count+1:02d}";directory.mkdir()
                        issued.add(height);lifetime+=1;session["new_requests"]+=1
                        futures[pool.submit(capture_with_session,height,directory,limiter,stop,transport,budget,sd.name)] = height
                    require(futures,"No requests can advance bounded prefix")
                    done,_=wait(futures,return_when=FIRST_COMPLETED)
                    for future in done:
                        height=futures.pop(future)
                        try:
                            row=read_attempt(future.result(),height,cache[FULL_START]["block"])
                            require(row["kind"] in {"BLOCK","NULL"},"HTTP/transport/routing unavailable; no automatic retry")
                            cache[height]=row
                        except Exception as exc:
                            stop.set();errors.append(f"height {height}: {type(exc).__name__}: {exc}")
                    if errors:
                        raise ValueError("; ".join(errors))
                budget.publish(sd/"checkpoint.json",summary(chain,prepared))
            status="COMPLETE"
        except (Exception,KeyboardInterrupt) as exc:
            stop.set()
            errors.append(f"{type(exc).__name__}: {exc}")
            status="STOPPED"
        finally:
            stop.set()
            if hasattr(transport,"close"):
                transport.close()
        session.update(status=status,finished_at=c.utc_now(),wall_elapsed_ns=time.monotonic_ns()-began,
                       response_body_bytes=budget.body-body_before,errors=errors,automatic_retries=0)
        budget.publish(sd/("finished.json" if status=="COMPLETE" else "stopped.json"),session)
        report=validate(store,prepared)
        budget.publish(sd/"validation.json",report)
        require(status=="COMPLETE",f"Collection stopped; inspect {sd/'stopped.json'}")
        print(f"Segment complete; {session['new_requests']} new requests; remaining interval NOT started.",flush=True)
        return report


def capture_with_session(height,directory,limiter,stop,transport,budget,session_id):
    def wrapped(h,raw):
        meta,body=transport(h,raw)
        meta["session_id"]=session_id
        return meta,body
    return capture(height,directory,limiter,stop,wrapped,budget)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="command",required=True)
    for command in ("plan","collect","validate"):
        q=sub.add_parser(command)
        if command != "plan":q.add_argument("--store",type=Path,default=STORE)
        if command != "collect":q.add_argument("--output",type=Path)
    args=parser.parse_args(argv)
    try:
        if args.command=="collect":collect(args.store);return 0
        result=plan() if args.command=="plan" else validate(args.store)
        if args.output:write_new(args.output,c.json_bytes(result))
        else:sys.stdout.write(c.json_bytes(result).decode())
    except (OSError,ValueError,KeyError,TypeError,IndexError) as exc:
        print(f"Stopped: {exc}. No retry or scope expansion.",file=sys.stderr);return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
