"""Offline synthetic tests; source requests are forbidden."""

import copy
import hashlib
import importlib.util
import io
import tempfile
import threading
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("optimized",ROOT/"analysis/37_neardata_optimized_segment.py")
m=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def identifier(label):
    raw=hashlib.sha256(label.encode()).digest()
    n,result=int.from_bytes(raw,"big"),""
    while n:
        n,d=divmod(n,58);result=m.p.ALPHABET[d]+result
    return "1"*(len(raw)-len(raw.lstrip(b"\0")))+result


class Clock:
    def __init__(self):self.ns=time.monotonic_ns()
    def now(self):return self.ns
    def sleep(self,seconds):self.ns+=round(seconds*10**9)


class OptimizedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch("socket.socket",side_effect=AssertionError("Networking forbidden")):
            cls.base=m.plan()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.store=self.root/"raw"
        self.prepared=copy.deepcopy(self.base)
        for target in ("socket.socket","socket.create_connection"):
            g=patch(target,side_effect=AssertionError("Networking forbidden"));g.start();self.addCleanup(g.stop)
        self.end=m.START+7
        g=patch.object(m,"END",self.end);g.start();self.addCleanup(g.stop)
        planfile=self.root/"plan.json";planfile.write_bytes(m.c.json_bytes(self.prepared))
        g=patch.object(m,"PLAN",planfile);g.start();self.addCleanup(g.stop)
        self.clock=Clock()
        g=patch.object(m.time,"monotonic_ns",self.clock.now);g.start();self.addCleanup(g.stop)
        self.limiter=m.Limiter(clock=self.clock.now,sleep=self.clock.sleep)
        self.calls=[];self.lock=threading.Lock()
        self.make_blocks()

    def make_blocks(self,nulls=(),carried=False,delayed=False):
        self.blocks={};prev=copy.deepcopy(self.prepared["seeds"][str(m.START-1)]["block"])
        for height in range(m.START,m.END+1):
            if height in nulls:self.blocks[height]=None;continue
            block=copy.deepcopy(prev);h,ph=block["header"],prev["header"]
            stamp=int(ph["timestamp_nanosec"])+10**9
            h.update(height=height,hash=identifier(f"block-{height}"),prev_height=ph["height"],prev_hash=ph["hash"],timestamp=stamp,timestamp_nanosec=str(stamp))
            mask=[];debit=0
            for i,chunk in enumerate(block["chunks"]):
                if carried and i==0:mask.append(False);continue
                chunk.update(chunk_hash=identifier(f"chunk-{height}-{i}"),height_created=height,height_included=height,
                             prev_block_hash=ph["hash"],balance_burnt=str(10**17+i))
                if delayed and height==m.START+1 and i==1:
                    chunk.update(height_created=height-1,prev_block_hash=self.prepared["seeds"][str(m.START-1)]["block"]["header"]["hash"])
                mask.append(True);debit+=int(chunk["balance_burnt"])
            h.update(total_supply=str(int(ph["total_supply"])-debit),chunk_mask=mask,chunks_included=sum(mask))
            self.blocks[height]=block;prev=block

    def transport(self,height,raw):
        with self.lock:self.calls.append(height)
        self.assertEqual(raw,m.request_parts(height)[0])
        return {"http_status":200,"response_headers":[],"body_complete":True,"transport_error":None,"connection_reused":True},m.c.json_bytes(self.blocks[height])

    def collect(self,transport=None):
        with redirect_stdout(io.StringIO()):
            return m.collect(self.store,prepared=self.prepared,transport=transport or self.transport,limiter=self.limiter)

    def test_shared_rolling_limiter_spacing_and_resume_history(self):
        clock=Clock();gate=m.Limiter(clock=clock.now,sleep=clock.sleep);stop=threading.Event()
        stamps=[gate.acquire(stop) for _ in range(400)]
        self.assertTrue(all(b-a>=500_000_000 for a,b in zip(stamps,stamps[1:])))
        self.assertTrue(all(stamps[i]-stamps[i-120]>=60*10**9 for i in range(120,len(stamps))))
        again=m.Limiter(recent=stamps[-120:],clock=clock.now,sleep=clock.sleep)
        self.assertGreaterEqual(again.acquire(stop)-stamps[-1],500_000_000)
        stop.set()
        with self.assertRaisesRegex(ValueError,"Scheduling stopped"):gate.acquire(stop)

    def test_complete_segment_integer_identity_and_immutable_no_request_resume(self):
        r=self.collect()
        self.assertTrue(r["complete"]);self.assertEqual(len(self.calls),8)
        self.assertEqual(r["segment_supply_identity_discrepancy_yocto"],"0")
        self.assertEqual(r["cumulative_supply_identity_discrepancy_yocto"],"0")
        self.assertIsNone(r["gross_actual_burn_yocto"]);self.assertIsNone(r["independent_full_epoch_net_debit_yocto"])
        self.assertEqual(r,m.validate(self.store,self.prepared))
        before={str(x):x.read_bytes() for x in (self.store/"attempts").rglob("*") if x.is_file()}
        self.collect();self.assertEqual(len(self.calls),8)
        self.assertEqual(before,{str(x):x.read_bytes() for x in (self.store/"attempts").rglob("*") if x.is_file()})

    def test_four_workers_are_bounded_and_out_of_order_completion_is_accepted(self):
        active=maximum=0
        def transport(h,raw):
            nonlocal active,maximum
            with self.lock:active+=1;maximum=max(maximum,active)
            time.sleep(0.02 if h%2==0 else 0.001)
            out=self.transport(h,raw)
            with self.lock:active-=1
            return out
        r=self.collect(transport)
        self.assertTrue(r["complete"]);self.assertGreater(maximum,1);self.assertLessEqual(maximum,4)
        self.assertEqual(sorted(self.calls),list(range(m.START,m.END+1)))

    def test_failed_capture_retained_no_auto_retry_and_manual_resume_reuses_success(self):
        failed=m.START+2
        def transport(h,raw):
            meta,body=self.transport(h,raw)
            if h==failed:meta.update(http_status=503,body_complete=False,transport_error="synthetic incomplete transport")
            return meta,body
        with self.assertRaisesRegex(ValueError,"Collection stopped"):self.collect(transport)
        self.assertEqual(self.calls.count(failed),1)
        bad=self.store/f"attempts/{failed}/01/response.body";old=bad.read_bytes()
        successful=set(self.calls)-{failed};self.calls.clear()
        r=self.collect()
        self.assertTrue(r["complete"]);self.assertEqual(bad.read_bytes(),old)
        self.assertTrue(successful.isdisjoint(self.calls))
        self.assertEqual(self.calls.count(failed),1)

    def test_429_and_redirect_stop_without_following(self):
        for status in (429,302):
            self.store=self.root/f"store-{status}";self.calls.clear()
            def transport(h,raw):
                meta,body=self.transport(h,raw);meta.update(http_status=status,response_headers=[["Location","https://unverified.test/"]]);return meta,body
            with self.assertRaisesRegex(ValueError,"Collection stopped"):self.collect(transport)
            self.assertLessEqual(len(self.calls),4)
            self.assertTrue((self.store/"sessions/0001/stopped.json").exists())

    def test_supported_skip_is_not_zero_and_consecutive_nulls_stop(self):
        self.make_blocks(nulls={m.START})
        r=self.collect();self.assertTrue(r["complete"])
        self.assertIsNone(r["supported_skips"][0]["net_debit_yocto"])
        self.store=self.root/"consecutive";self.make_blocks(nulls={m.START,m.START+1})
        with self.assertRaisesRegex(ValueError,"Consecutive nulls"):self.collect()
        self.assertTrue((self.store/"sessions/0001/stopped.json").exists())

    def test_trailing_null_keeps_complete_amount_unavailable(self):
        self.make_blocks(nulls={m.END})
        with self.assertRaisesRegex(ValueError,"Collection stopped"):self.collect()
        r=m.validate(self.store,self.prepared)
        self.assertFalse(r["complete"]);self.assertIsNone(r["independent_complete_segment_net_debit_yocto"])

    def test_carried_delayed_chunks_and_broken_supply_identity(self):
        self.make_blocks(carried=True,delayed=True)
        r=self.collect();self.assertEqual(r["segment_supply_identity_discrepancy_yocto"],"0")
        self.store=self.root/"bad-identity";self.make_blocks();self.blocks[m.START]["header"]["total_supply"]="1"
        with self.assertRaisesRegex(ValueError,"supply/net-debit"):self.collect()

    def test_schema_protocol_conflict_and_checksum_tampering(self):
        self.blocks[m.START]["header"]["epoch_id"]=identifier("unreviewed")
        with self.assertRaisesRegex(ValueError,"transition"):self.collect()
        calls=len(self.calls)
        with self.assertRaisesRegex(ValueError,"transition"):self.collect()
        self.assertEqual(len(self.calls),calls)
        self.store=self.root/"tampered";self.make_blocks();self.collect()
        path=self.store/f"attempts/{m.START}/01/response.body";path.write_bytes(path.read_bytes()+b" ")
        with self.assertRaisesRegex(ValueError,"checksum"):m.validate(self.store,self.prepared)

    def test_concurrent_body_and_store_reservations_are_enforced(self):
        self.store.mkdir();budget=m.Budget(self.store)
        with patch.object(m,"BODY_CAP",2*m.RESPONSE_CAP):
            budget.reserve();budget.reserve()
            with self.assertRaisesRegex(ValueError,"body cap"):budget.reserve()
        budget=m.Budget(self.store)
        with patch.object(m,"STORE_CAP",2*m.RESPONSE_CAP+m.META_RESERVE-1):
            with self.assertRaisesRegex(ValueError,"total-store cap"):budget.reserve()

    def test_attempt_cap_and_repository_storage_guard(self):
        def bad(h,raw):
            meta,body=self.transport(h,raw);meta["http_status"]=500;return meta,body
        for _ in range(2):
            with self.assertRaises(ValueError):self.collect(bad)
        calls=len(self.calls)
        with self.assertRaisesRegex(ValueError,"Collection stopped"):self.collect(bad)
        self.assertEqual(len(self.calls),calls)
        with self.assertRaisesRegex(ValueError,"outside repository"):
            m.collect(ROOT/"results/forbidden",prepared=self.prepared,transport=bad)

    def test_full_1000_height_scope_and_request_limit(self):
        with patch.object(m,"END",m.START+999):
            self.make_blocks()
            r=self.collect()
            self.assertTrue(r["complete"]);self.assertEqual(len(self.calls),1000)
            self.assertEqual(max(self.calls),216879033);self.assertEqual(min(self.calls),216878034)
            self.assertEqual(r["segment_supply_identity_discrepancy_yocto"],"0")
            self.assertEqual(r["sample_extrapolations"]["remaining_epoch_after_segment"]["height_slots_to_model"],42099)
            self.assertEqual(r["sample_extrapolations"]["whole_week_all_slots_before_reuse"]["height_slots_to_model"],1002586)
            with self.assertRaisesRegex(ValueError,"outside enabled"):m.request_parts(m.END+1)

    def test_http_transport_reuses_connections_and_does_not_follow_redirects(self):
        class Sock:
            def settimeout(self,value):pass
        class Response:
            version=11;reason="OK";length=2;status=200
            def __init__(self):self.closed=False
            def getheaders(self):return []
            def getheader(self,key):return None
            def isclosed(self):return self.closed
            def read1(self,size):self.closed=True;self.length=0;return b"{}"
            def close(self):self.closed=True
        class Connection:
            def __init__(self,*args,**kwargs):self.sock=None;self.paths=[];self.headers=[];self.status=200
            def connect(self):self.sock=Sock()
            def putrequest(self,method,path,**kwargs):self.paths.append(path)
            def putheader(self,key,value):self.headers.append((key,value))
            def endheaders(self):pass
            def getresponse(self):r=Response();r.status=self.status;return r
            def close(self):self.sock=None
        conn=Connection()
        with patch.object(m.http.client,"HTTPSConnection",return_value=conn) as factory:
            transport=m.Transport();raw=m.request_parts(m.START)[0]
            one,body=transport(m.START,raw);two,_=transport(m.START+1,m.request_parts(m.START+1)[0])
            self.assertFalse(one["connection_reused"]);self.assertTrue(two["connection_reused"])
            self.assertEqual(factory.call_count,1);self.assertEqual(body,b"{}")
            conn.status=302;meta,_=transport(m.START+2,m.request_parts(m.START+2)[0])
            self.assertEqual(meta["http_status"],302);self.assertEqual(len(conn.paths),3)
            self.assertTrue(all(k.lower() not in {"authorization","cookie","referer"} for k,v in conn.headers))
            transport.close()

    def test_recent_request_history_restored_and_response_cap_guard(self):
        mono=10**15;utc=1700000000*10**9
        metas=[{"started_at":"2023-11-14T22:13:19+00:00"}]
        self.assertEqual(m.recent_starts(metas,mono=lambda:mono,utc=lambda:utc),[mono-10**9])
        with patch.object(m,"RESPONSE_CAP",10):
            def oversized(h,raw):return {},b"x"*11
            with self.assertRaises(ValueError):self.collect(oversized)
            self.assertLessEqual(len(self.calls),4)


if __name__=="__main__":unittest.main()
