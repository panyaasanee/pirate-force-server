import copy,hashlib,importlib.util,json,math,struct,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("pf_action_consumer_probe",ROOT/"tools/pf_action_consumer_probe.py")
P=importlib.util.module_from_spec(SPEC);sys.modules[SPEC.name]=P;SPEC.loader.exec_module(P)

class ConsumerProbeTests(unittest.TestCase):
 def config(self,name="pf_action_consumer_probe_config.json"):return P.load_config(ROOT/"tools"/name)
 def synthetic(self,root,config):
  raw_size=0x400000;raw=bytearray(0x200+raw_size);raw[:2]=b"MZ";struct.pack_into("<I",raw,0x3c,0x80);raw[0x80:0x84]=b"PE\0\0";struct.pack_into("<HH",raw,0x84,0x14c,1);struct.pack_into("<H",raw,0x94,0xe0);opt=0x98;struct.pack_into("<H",raw,opt,0x10b);struct.pack_into("<I",raw,opt+28,0x400000);struct.pack_into("<I",raw,opt+56,0x700000);sec=opt+0xe0;struct.pack_into("<IIII",raw,sec+8,raw_size,0x40000,raw_size,0x200)
  for h in P._hooks(config):
   off=0x200+h["va"]-0x440000;raw[off:off+len(bytes.fromhex(h["code"]))]=bytes.fromhex(h["code"])
  path=root/"GameClient.bin";path.write_bytes(raw);config["binary"].update(size=len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),size_of_image=0x700000);return path
 def test_profiles_hooks_and_observe_only_source(self):
  a=self.config();b=self.config("pf_action_consumer_probe_local_config.json")
  self.assertEqual(a["hooks"],b["hooks"]);self.assertNotEqual(a["binary"]["sha256"],b["binary"]["sha256"])
  self.assertEqual(P.DEFAULT_CLIENT.name,"GameClient.local.bin");self.assertEqual(P.DEFAULT_CAPTURE_ROOT.name,"capture_action_consumer")
  source=P.make_agent_source(b)
  for forbidden in ("Memory.write","writeU","writeFloat","NativeFunction","Interceptor.replace"):self.assertNotIn(forbidden,source)
  self.assertEqual(source.count("Interceptor.attach"),7);self.assertIn("timeout_ms",source);self.assertIn("max_events",source);self.assertNotIn("cross-thread action update",source)
  self.assertIn("const o=this.context.ecx,key=o.toString(),s=owners.get(key)",source)
  self.assertIn("const o=this.context.esi,key=o.toString(),s=owners.get(key)",source)
  self.assertIn("action object ownership ambiguity or reuse",source);self.assertIn("nonterminal action at common return",source)
  self.assertEqual(b["hooks"]["update_before"]["code"][:4],"8bf1")
  self.assertIn("function step(tid,want,stage,object){const s=state(tid);if(!s)return null",source)
  self.assertIn("const key=args[0].toString(),owned=owners.get(key);if(owned===undefined)return",source)
  self.assertIn("stage='+stage+' thread='+tid+' expected='+want+' actual='+actual+' object=",source)
  self.assertNotIn("sequence or thread correlation failure",source)
  self.assertIn("diagnostic('update_before',this.threadId,'queued',s.step,key)",source)
  self.assertIn("expected='step=updating owner_thread='+s.updateThread,actual='step='+s.step+' current_thread='+this.threadId",source)
  self.assertIn("diagnostic('update_after',this.threadId,expected,actual,key)",source)
  self.assertNotIn("post-queue object ambiguity or order failure",source)
  self.assertNotIn("update completion ambiguity or thread mismatch",source)
  self.assertIn("Number.isFinite",source)
 def test_exact_real_binary_guards_both_profiles(self):
  P.guard_binary(ROOT.parent/"GameClient/GameClient.bin",self.config())
  P.guard_binary(ROOT.parent/"GameClient/GameClient.local.bin",self.config("pf_action_consumer_probe_local_config.json"))
 def test_config_and_binary_guards(self):
  c=copy.deepcopy(self.config());c["correlation"]["timeout_ms"]=2001
  with tempfile.TemporaryDirectory() as td:
   bad=Path(td)/"bad.json";bad.write_text(json.dumps(c));
   with self.assertRaisesRegex(ValueError,"correlation"):P.load_config(bad)
  with tempfile.TemporaryDirectory() as td:
   c=copy.deepcopy(self.config());path=self.synthetic(Path(td),c);P.guard_binary(path,c);raw=bytearray(path.read_bytes());raw[-1]^=1;path.write_bytes(raw)
   with self.assertRaisesRegex(ValueError,"SHA-256"):P.guard_binary(path,c)
 def test_safe_output_and_runtime_options(self):
  for values in ((0,0),(1,-1),(1,math.inf),(1,math.nan)):
   with self.assertRaises(ValueError):P.validate_runtime_options(*values)
  P.validate_runtime_options(1,0)
  client=ROOT.parent/"GameClient/GameClient.bin";config=ROOT/"tools/pf_action_consumer_probe_config.json"
  with tempfile.TemporaryDirectory() as td:
   safe=Path(td).resolve();good=(safe/"run/events.jsonl").resolve();self.assertEqual(P.validate_output_path(good,client,config,safe),good)
   with self.assertRaisesRegex(ValueError,"absolute"):P.validate_output_path(Path("x"),client,config,safe)
   with self.assertRaisesRegex(ValueError,"capture directory"):P.validate_output_path((safe.parent/"escape.jsonl").resolve(),client,config,safe)
  with self.assertRaisesRegex(ValueError,"aliases"):P.validate_output_path(client.resolve(),client,config,client.parent)
  with self.assertRaisesRegex(ValueError,"aliases"):P.validate_output_path(Path(P.__file__).resolve(),client,config,Path(P.__file__).resolve().parent)
 def events(self,update_thread=2):
  return [
   {"schema":1,"event":"handler","timestamp":"x","thread_id":1,"sequence":1,"address":"0x7516e5","request":"0x1","performer":"0x10","target":"0x203d","action":0xea7d},
   {"schema":1,"event":"constructor_return","timestamp":"x","thread_id":1,"sequence":2,"address":"0x75180e","object":"0x2","action":0xea7d,"implementation":"0x0","flags":8},
   {"schema":1,"event":"attach_call","timestamp":"x","thread_id":1,"sequence":3,"address":"0x7519a1","actor":"0x3","object":"0x2"},
   {"schema":1,"event":"actor_attach","timestamp":"x","thread_id":1,"sequence":4,"address":"0x4843f0","actor":"0x3","object":"0x2","flags":8,"expected_queue":"0x23"},
   {"schema":1,"event":"queue_add","timestamp":"x","thread_id":1,"sequence":5,"address":"0x4a0c90","queue":"0x23","object":"0x2"},
   {"schema":1,"event":"update_before","timestamp":"x","thread_id":update_thread,"sequence":6,"address":"0x47af1b","object":"0x2","implementation":"0x0","flags":8},
   {"schema":1,"event":"update_after","timestamp":"x","thread_id":update_thread,"sequence":7,"address":"0x47b295","object":"0x2","flags_before":8,"flags_after":8},
  ]
 def test_event_schema_full_order_and_safe_cross_thread_handoff(self):
  events=self.events()
  for event in events:self.assertIs(P.validate_event(event),event)
  s=P.CaptureState();s.accept({"event":"probe_ready"})
  for event in events:s.accept(event)
  s.ensure_success();self.assertEqual(s.pre_thread,1);self.assertEqual(s.update_thread,2)
 def test_event_schema_and_late_failure(self):
  handler=self.events()[0]
  self.assertIs(P.validate_event(handler),handler)
  with self.assertRaises(ValueError):P.validate_event(dict(handler,target="0x203e"))
  constructor=self.events()[1]
  self.assertIs(P.validate_event(constructor),constructor)
  with self.assertRaisesRegex(ValueError,"fields"):P.validate_event(dict(constructor,semantic="animation"))
  s=P.CaptureState();s.accept({"event":"probe_ready"})
  s.accept({"event":"update_after"})
  with self.assertRaisesRegex(RuntimeError,"out of order"):s.ensure_success()
  s=P.CaptureState();s.accept({"event":"probe_ready"})
  for event in self.events():s.accept(event)
  s.accept({"event":"probe_error","reason":"late"})
  with self.assertRaisesRegex(RuntimeError,"late"):s.ensure_success()
 def test_ambiguity_nonterminal_timeout_and_event_bound_fail_closed(self):
  s=P.CaptureState();s.accept({"event":"probe_ready"});s.accept(self.events()[0]);s.accept(self.events()[1]);s.accept(self.events()[1])
  with self.assertRaisesRegex(RuntimeError,"out of order|ambiguity"):s.ensure_success()
  for event in (dict(self.events()[5],flags=0),dict(self.events()[6],flags_after=0)):
   with self.assertRaisesRegex(ValueError,"terminal|nonterminal"):P.validate_event(event)
  for reason in ("correlation timeout","event bound exceeded"):
   s=P.CaptureState();s.accept({"event":"probe_ready"});s.accept({"event":"probe_error","reason":reason})
   with self.assertRaisesRegex(RuntimeError,reason):s.ensure_success()
 def completed_state(self):
  s=P.CaptureState();s.accept({"event":"probe_ready"})
  for event in self.events():s.accept(event)
  return s
 def test_cleanup_uses_single_bounded_session_detach(self):
  calls=[]
  class Script:
   def unload(self):calls.append("unload")
  class Session:
   def detach(self):calls.append("detach")
  P.cleanup_frida(Script(),Session(),0.25,lambda call,timeout:(self.assertEqual(timeout,0.25),call()))
  self.assertEqual(calls,["detach"])
  calls.clear()
  def timeout_runner(call,_timeout):
   calls.append(call.__name__);raise TimeoutError("bounded")
  with self.assertRaisesRegex(TimeoutError,"bounded"):
   P.cleanup_frida(Script(),Session(),0.25,timeout_runner)
  self.assertEqual(calls,["detach"])
 def test_finalize_preserves_completed_result_but_fails_late_error(self):
  class Script:
   def unload(self):pass
  class Session:
   def detach(self):pass
  P.finalize_capture(self.completed_state(),Script(),Session(),runner=lambda call,_timeout:call())
  P.finalize_capture(self.completed_state(),Script(),Session(),runner=lambda _call,_timeout:(_ for _ in ()).throw(TimeoutError("bounded detach")))
  state=self.completed_state()
  def late_runner(call,_timeout):
   call()
   if call.__name__=="detach":state.accept({"event":"probe_error","reason":"late during cleanup"})
  with self.assertRaisesRegex(RuntimeError,"late during cleanup"):
   P.finalize_capture(state,Script(),Session(),runner=late_runner)
 def test_malformed_pe(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/"GameClient.bin";p.write_bytes(b"bad")
   with self.assertRaises(ValueError):P._base.read_pe(p)

if __name__=="__main__":unittest.main()
