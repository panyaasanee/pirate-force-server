import importlib.util, json, tempfile, unittest
from pathlib import Path
import capstone, pefile

ROOT=Path(__file__).resolve().parents[1]
S=importlib.util.spec_from_file_location("pf_skill_trigger_probe",ROOT/"tools/pf_skill_trigger_probe.py");P=importlib.util.module_from_spec(S);S.loader.exec_module(P)

# Two tests below read the proprietary client binaries in ../GameClient,
# which are never committed.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE

class SkillTriggerProbeTests(unittest.TestCase):
    def config(self,name="pf_skill_trigger_probe_config.json"):return P.load_config(ROOT/"tools"/name)
    def event(self,kind,seq,**kw):
        addresses={"codec_enter":"0xec0a60","codec_complete":"0xec0a60","consumer_enter":"0xec1810","consumer_submission":"0xd09110","consumer_complete":"0xec1810"}
        common={"thread_id":7,"sequence":seq,"invocation":1,"address":addresses[kind],"object":"0x1000","caller":"0x2000","raw_u16_14":3,"raw_u8_16":4,"raw_u32_18":5}
        shape={"codec_enter":{**common,"direction":"read"},"codec_complete":{**common,"direction":"read"},"consumer_enter":common,"consumer_submission":{**common,"submitted_object":"0x3000","submission_caller":"0xec1885"},"consumer_complete":{**common,"result_bool":1}}[kind]
        return {"schema":1,"event":kind,"timestamp":"t",**shape,**kw}
    def test_profiles_guards_boundaries_and_relocations(self):
        # Reads both proprietary binaries under ../GameClient; the local image
        # lives inside that tree, so client_image is the stricter single key.
        # See tests/pf_preconditions.py.
        CLIENT_IMAGE.require(self)
        a=self.config();b=self.config("pf_skill_trigger_probe_local_config.json");self.assertEqual(a["hooks"],b["hooks"])
        P.guard_binary(ROOT.parent/"GameClient/GameClient.bin",a);P.guard_binary(ROOT.parent/"GameClient/GameClient.local.bin",b)
        with self.assertRaises(ValueError):P.guard_binary(ROOT.parent/"GameClient/GameClient.local.bin",a)
        with self.assertRaises(ValueError):P.guard_binary(ROOT.parent/"GameClient/GameClient.bin",b)
        for fn in ("GameClient.bin","GameClient.local.bin"):
            pe=pefile.PE(str(ROOT.parent/"GameClient"/fn));rel={pe.OPTIONAL_HEADER.ImageBase+e.rva for block in pe.DIRECTORY_ENTRY_BASERELOC for e in block.entries if e.type==3}
            for h in a["hooks"].values():
                code=bytes.fromhex(h["code"]);ins=list(capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32).disasm(code,h["va"]));self.assertEqual(sum(x.size for x in ins),len(code))
                self.assertEqual(rel&set(range(h["va"],h["va"]+len(code))),{h["va"]+r["offset"] for r in h["runtime_relocations"]})
    def test_config_drift_rejected(self):
        d=json.loads((ROOT/"tools/pf_skill_trigger_probe_config.json").read_text());d["limits"]["timeout_ms"]+=1
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.json";p.write_text(json.dumps(d));
            with self.assertRaisesRegex(ValueError,"provenance"):P.load_config(p)
    def test_schema_exact_and_bounds(self):
        for i,k in enumerate(("codec_enter","codec_complete","consumer_enter","consumer_submission","consumer_complete"),1):P.validate_event(self.event(k,i))
        bad=(self.event("codec_enter",1,direction="cast"),self.event("codec_enter",1,raw_u16_14=65536),self.event("consumer_complete",1,result_bool=2),self.event("consumer_enter",1,object="no"),self.event("consumer_enter",1,extra=1))
        for x in bad:
            with self.assertRaises(ValueError):P.validate_event(x)
    def test_state_complete_and_requirements(self):
        s=P.CaptureState(True,True);s.accept({"event":"probe_ready","address":"0xcc0000"})
        for i,k in enumerate(("codec_enter","codec_complete","consumer_enter","consumer_submission","consumer_complete"),1):s.accept(P.validate_event(self.event(k,i)))
        s.ensure_success()
        for req in ((True,False),(False,True)):
            x=P.CaptureState(*req);x.accept({"event":"probe_ready","address":"0xcc0000"})
            with self.assertRaises(RuntimeError):x.ensure_success()
    def test_state_fail_closed_correlation_order_and_late_error(self):
        x=P.CaptureState();x.accept({"event":"probe_ready","address":"0xcc0000"});x.accept(P.validate_event(self.event("codec_enter",2)));x.accept(P.validate_event(self.event("codec_complete",1)))
        with self.assertRaisesRegex(RuntimeError,"strictly increasing"):x.ensure_success()
        y=P.CaptureState();y.accept({"event":"probe_ready","address":"0xcc0000"});y.accept(P.validate_event(self.event("consumer_enter",1)));y.accept(P.validate_event(self.event("consumer_complete",2)))
        with self.assertRaisesRegex(RuntimeError,"without submission"):y.ensure_success()
        q=P.CaptureState();q.accept({"event":"probe_ready","address":"0xcc0000"});q.accept(P.validate_event(self.event("consumer_enter",1)));q.accept(P.validate_event(self.event("consumer_submission",2,submission_caller="0xd01886")))
        with self.assertRaisesRegex(RuntimeError,"exact 0x601885"):q.ensure_success()
        w=P.CaptureState();w.accept({"event":"probe_ready","address":"0xcc0000"});w.accept(P.validate_event(self.event("codec_enter",1,address="0xec0a61")))
        with self.assertRaisesRegex(RuntimeError,"exact guarded hook"):w.ensure_success()
        z=P.CaptureState();z.accept({"event":"probe_ready","address":"0xcc0000"});z.accept({"event":"probe_error","reason":"late"})
        with self.assertRaisesRegex(RuntimeError,"late"):z.ensure_success()
    def test_agent_scope_observe_only_and_cleanup(self):
        src=P.make_agent_source(self.config("pf_skill_trigger_probe_local_config.json"))
        for s in ("at.codec","at.consumer","at.submission","this.returnAddress.equals(exactSubmissionCaller)","submission_caller","stopped=true","raw_u16_14","raw_u8_16","raw_u32_18","codec correlation timeout","consumer correlation timeout"):self.assertIn(s,src)
        for s in ("Memory.write","writeU","writeS","writePointer","NativeFunction","Interceptor.replace","sendInput"):self.assertNotIn(s,src)
        launcher=Path(P.__file__).read_text();self.assertIn("_consumer.finalize_capture(state,script,session)",launcher);self.assertNotIn("session.detach()",launcher)
    def test_output_confined_and_aliases(self):
        # validate_output_path resolves the proprietary client image strictly,
        # and a clone cannot carry it.  See tests/pf_preconditions.py.
        CLIENT_IMAGE.require(self)
        client=ROOT.parent/"GameClient/GameClient.local.bin";cfg=ROOT/"tools/pf_skill_trigger_probe_local_config.json";safe=P.DEFAULT_CAPTURE_ROOT/"x.jsonl"
        self.assertEqual(P.validate_output_path(safe,client,cfg),safe.resolve())
        with self.assertRaises(ValueError):P.validate_output_path(ROOT/"x.jsonl",client,cfg)
        with self.assertRaises(ValueError):P.validate_output_path(cfg,client,cfg)

if __name__=="__main__":unittest.main()
