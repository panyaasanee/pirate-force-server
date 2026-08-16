import importlib.util,json,struct,tempfile,unittest
from pathlib import Path
import capstone,pefile
ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location("pf_knockdown_consumer_probe",ROOT/"tools/pf_knockdown_consumer_probe.py");P=importlib.util.module_from_spec(S);S.loader.exec_module(P)
class KnockdownProbeTests(unittest.TestCase):
 def cfg(self,n="pf_knockdown_consumer_probe_config.json"):return P.load_config(ROOT/"tools"/n)
 def ev(self,k,s,**kw):
  a={"codec_enter":"0x100ebf0","codec_complete":"0x100ebf0","consumer_enter":"0x1010700","manager_return":"0xd3cad0","actor40_dispatch":"0xd443f0","queue_enter":"0xd60c90","consumer_complete":"0x1010700"};c={"thread_id":7,"sequence":s,"invocation":1,"address":a[k],"object":"0x2000","caller":"0x3000","raw_qword_18":"0x10010001","raw_u32_20":278,"raw_u32_24":4,"raw_f32_28":1.0,"raw_f32_2c":2.0,"raw_f32_30":3.0,"raw_f32_34":4.0};extra={"codec_enter":{"direction":"read"},"codec_complete":{"direction":"read"},"consumer_enter":{},"manager_return":{"receiver":"0x4000","wrapper":"0x5000","manager_caller":"0x1010761"},"actor40_dispatch":{"receiver":"0x4000","wrapper":"0x5000","dispatch_caller":"0x1010769","wrapper_vtable":"0x17cf7dc","wrapper_flags":0x40000005},"queue_enter":{"receiver":"0x4000","wrapper":"0x5000","queue_caller":"0xd4440c","queue_argument":1},"consumer_complete":{"result_bool":1,"completion_path":"queued"}}[k];return {"schema":1,"event":k,"timestamp":"t",**c,**extra,**kw}
 def test_profiles_actual_binaries_boundaries_relocations_cross_pair(self):
  a=self.cfg();b=self.cfg("pf_knockdown_consumer_probe_local_config.json");self.assertEqual(a["hooks"],b["hooks"]);P.guard_binary(ROOT.parent/"GameClient/GameClient.bin",a);P.guard_binary(ROOT.parent/"GameClient/GameClient.local.bin",b)
  with self.assertRaises(ValueError):P.guard_binary(ROOT.parent/"GameClient/GameClient.local.bin",a)
  with self.assertRaises(ValueError):P.guard_binary(ROOT.parent/"GameClient/GameClient.bin",b)
  for fn in ("GameClient.bin","GameClient.local.bin"):
   pe=pefile.PE(str(ROOT.parent/"GameClient"/fn));rel={pe.OPTIONAL_HEADER.ImageBase+e.rva for z in pe.DIRECTORY_ENTRY_BASERELOC for e in z.entries if e.type==3}
   for h in a["hooks"].values():
    code=bytes.fromhex(h["code"]);ins=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32).disasm(code,h["va"]));self.assertEqual(sum(x.size for x in ins),len(code));self.assertEqual(rel&set(range(h["va"],h["va"]+len(code))),{h["va"]+r["offset"] for r in h["runtime_relocations"]})
    slid=bytearray(code)
    for r in h["runtime_relocations"]:struct.pack_into("<I",slid,r["offset"],(struct.unpack_from("<I",code,r["offset"])[0]+0x8c0000)&0xffffffff)
    for r in h["runtime_relocations"]:self.assertEqual(struct.unpack_from("<I",slid,r["offset"])[0],(struct.unpack_from("<I",code,r["offset"])[0]+0x8c0000)&0xffffffff)
 def test_config_malformed_and_drift(self):
  d=json.loads((ROOT/"tools/pf_knockdown_consumer_probe_config.json").read_text());d["hooks"]["codec"]["va"]+=1
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"x";p.write_text(json.dumps(d));
   with self.assertRaisesRegex(ValueError,"provenance"):P.load_config(p)
 def test_schema_bounds_nonfinite_and_exact(self):
  for i,k in enumerate(("codec_enter","codec_complete","consumer_enter","manager_return","actor40_dispatch","queue_enter","consumer_complete"),1):P.validate_event(self.ev(k,i))
  for x in (self.ev("consumer_enter",1,raw_f32_28=float("nan")),self.ev("queue_enter",1,queue_argument=0),self.ev("actor40_dispatch",1,wrapper_flags=1),self.ev("consumer_complete",1,result_bool=0),self.ev("consumer_enter",1,address="bad"),self.ev("consumer_enter",1,extra=1)):
   with self.assertRaises(ValueError):P.validate_event(x)
 def test_full_order_require_wrong_address_and_late(self):
  s=P.CaptureState(True);s.accept({"event":"probe_ready","address":"0xcc0000"})
  for i,k in enumerate(("consumer_enter","manager_return","actor40_dispatch","queue_enter","consumer_complete"),1):s.accept(P.validate_event(self.ev(k,i)))
  s.ensure_success();x=P.CaptureState(True);x.accept({"event":"probe_ready","address":"0xcc0000"});
  with self.assertRaisesRegex(RuntimeError,"completed consumer"):x.ensure_success()
  y=P.CaptureState();y.accept({"event":"probe_ready","address":"0xcc0000"});y.accept(P.validate_event(self.ev("consumer_enter",1,address="0x1010701")))
  with self.assertRaisesRegex(RuntimeError,"wrong exact"):y.ensure_success()
  z=P.CaptureState();z.accept({"event":"probe_ready","address":"0xcc0000"});z.accept({"event":"probe_error","reason":"late"})
  with self.assertRaisesRegex(RuntimeError,"late"):z.ensure_success()
 def test_null_order_and_incomplete_fail(self):
  n=P.CaptureState(True);n.accept({"event":"probe_ready","address":"0xcc0000"});n.accept(P.validate_event(self.ev("consumer_enter",1)));n.accept(P.validate_event(self.ev("manager_return",2,wrapper="0x0")));n.accept(P.validate_event(self.ev("consumer_complete",3,completion_path="null_wrapper")));n.ensure_success()
  x=P.CaptureState();x.accept({"event":"probe_ready","address":"0xcc0000"});x.accept(P.validate_event(self.ev("consumer_enter",1)));x.accept(P.validate_event(self.ev("manager_return",2,wrapper="0x0")));x.accept(P.validate_event(self.ev("consumer_complete",3)))
  with self.assertRaises(RuntimeError):x.ensure_success()
  y=P.CaptureState();y.accept({"event":"probe_ready","address":"0xcc0000"});y.accept(P.validate_event(self.ev("consumer_enter",2)));y.accept(P.validate_event(self.ev("manager_return",1)))
  with self.assertRaisesRegex(RuntimeError,"strictly increasing"):y.ensure_success()
 def test_host_rejects_callers_wrapper_receiver_raw_order_timeout_and_bound(self):
  def failed(events,text):
   s=P.CaptureState();s.accept({"event":"probe_ready","address":"0xcc0000"})
   for e in events:s.accept(P.validate_event(e))
   with self.assertRaisesRegex(RuntimeError,text):s.ensure_success()
  enter=self.ev("consumer_enter",1);manager=self.ev("manager_return",2)
  failed([enter,self.ev("manager_return",2,manager_caller="0x1010762")],"manager caller")
  failed([enter,manager,self.ev("actor40_dispatch",3,dispatch_caller="0x1010768")],"dispatch caller")
  failed([enter,manager,self.ev("actor40_dispatch",3,receiver="0x4004")],"wrapper/receiver")
  failed([enter,manager,self.ev("actor40_dispatch",3,wrapper_vtable="0x17cf7d8")],"provenance")
  failed([enter,manager,self.ev("actor40_dispatch",3),self.ev("queue_enter",4,queue_caller="0xd4440d")],"queue caller")
  failed([enter,manager,self.ev("queue_enter",3)],"order")
  failed([enter,self.ev("manager_return",2,raw_u32_20=279)],"raw snapshot")
  for reason in ("codec timeout","consumer timeout","event bound exceeded"):
   q=P.CaptureState();q.accept({"event":"probe_ready","address":"0xcc0000"});q.accept({"event":"probe_error","reason":reason})
   with self.assertRaisesRegex(RuntimeError,reason):q.ensure_success()
 def test_output_alias_and_safe_root(self):
  c=ROOT.parent/"GameClient/GameClient.local.bin";g=ROOT/"tools/pf_knockdown_consumer_probe_local_config.json";p=P.DEFAULT_CAPTURE_ROOT/"x.jsonl";self.assertEqual(P.validate_output_path(p,c,g),p.resolve())
  with self.assertRaises(ValueError):P.validate_output_path(ROOT/"x",c,g)
  with self.assertRaises(ValueError):P.validate_output_path(g,c,g)
 def test_observe_only_filters_bounds_cleanup(self):
  s=P.make_agent_source(self.cfg("pf_knockdown_consumer_probe_local_config.json"))
  for x in ("guarded(h,m)","at.manager","at.dispatch","at.queue","at.consumer.add(0x61)","at.consumer.add(0x69)","at.dispatch.add(0x1c)","if(s.wrapper.isNull())return","args[1].toUInt32()!==1","stopped=true","codec timeout","consumer timeout","event bound exceeded"):self.assertIn(x,s)
  for x in ("Memory.write","writeU","writeS","writePointer","NativeFunction","Interceptor.replace","sendInput"):self.assertNotIn(x,s)
  q=Path(P.__file__).read_text();self.assertIn("_consumer.finalize_capture(state,script,session)",q);self.assertNotIn("session.detach()",q)
if __name__=="__main__":unittest.main()
