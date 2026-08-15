#!/usr/bin/env python3
"""Guarded observe-only TriggerCastSkillVital codec/consumer probe."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("pf_action_probe_base", Path(__file__).with_name("pf_action_producer_probe.py"))
_base = importlib.util.module_from_spec(_spec); sys.modules[_spec.name] = _base; _spec.loader.exec_module(_base)
_cspec = importlib.util.spec_from_file_location("pf_action_consumer_probe_base", Path(__file__).with_name("pf_action_consumer_probe.py"))
_consumer = importlib.util.module_from_spec(_cspec); sys.modules[_cspec.name] = _consumer; _cspec.loader.exec_module(_consumer)

DEFAULT_CONFIG = Path(__file__).with_name("pf_skill_trigger_probe_local_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_skill_trigger"
EXACT_BINARIES = _base.EXACT_BINARIES
EXACT_HOOKS = {
    "codec": {"va": 0x600A60, "code": "807c24080056578b7c240c", "runtime_relocations": []},
    "consumer": {"va": 0x601810, "code": "6aff683b1cbb00", "runtime_relocations": [{"offset": 3, "size": 4}]},
    "submission": {"va": 0x449110, "code": "568bf18b8edc03000085c974208b01", "runtime_relocations": []},
    "submission_return": {"va": 0x601885, "code": "b0018b4c240c", "runtime_relocations": []},
}
EXACT_LIMITS = {"max_events": 256, "max_active": 32, "timeout_ms": 2000}
EVENTS = {"probe_ready", "codec_enter", "codec_complete", "consumer_enter", "consumer_submission", "consumer_complete", "probe_error"}
POINTER = re.compile(r"^0x[0-9a-f]+$")


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks", "limits"} or data["schema"] != 1:
        raise ValueError("invalid skill trigger probe config root")
    if type(data["binary"]) is not dict or data["binary"] != EXACT_BINARIES.get(data["binary"].get("filename")):
        raise ValueError("binary profile differs from exact allowlist")
    if data["hooks"] != EXACT_HOOKS or data["limits"] != EXACT_LIMITS:
        raise ValueError("skill trigger provenance differs from exact allowlist")
    return data


def guard_binary(path: Path, config: dict[str, Any]):
    first = config["hooks"]["codec"]
    pe = _base.guard_binary(path, {"binary": config["binary"], "hooks": {"action_producer": first, "candidate_branches": [], "action_queue": first}})
    raw = path.read_bytes()
    for name, hook in config["hooks"].items():
        sig = bytes.fromhex(hook["code"]); off = pe.rva_to_offset(hook["va"] - pe.image_base)
        if raw[off:off + len(sig)] != sig: raise ValueError(f"client code guard mismatch at {name}")
    return pe


def validate_output_path(output: Path, client: Path, config: Path, capture_root: Path = DEFAULT_CAPTURE_ROOT) -> Path:
    resolved = _base.validate_output_path(output, client, config, capture_root)
    guarded = [Path(__file__).resolve(), Path(__file__).with_name("pf_skill_trigger_probe_config.json").resolve(), Path(__file__).with_name("pf_skill_trigger_probe_local_config.json").resolve()]
    if any(resolved == item or (resolved.exists() and resolved.samefile(item)) for item in guarded):
        raise ValueError("output aliases a guarded input")
    return resolved


def _uint(v: Any, name: str, upper: int = 0xFFFFFFFF) -> None:
    if type(v) is not int or isinstance(v, bool) or not 0 <= v <= upper: raise ValueError(f"invalid {name}")


def validate_event(v: Any) -> dict[str, Any]:
    if type(v) is not dict or v.get("schema") != 1 or v.get("event") not in EVENTS: raise ValueError("invalid skill trigger event")
    if type(v.get("timestamp")) is not str or not v["timestamp"]: raise ValueError("invalid timestamp")
    raw = {"thread_id", "sequence", "invocation", "address", "object", "caller", "raw_u16_14", "raw_u8_16", "raw_u32_18"}
    fields = {
        "probe_ready": {"address"}, "probe_error": {"reason"},
        "codec_enter": raw | {"direction"}, "codec_complete": raw | {"direction"},
        "consumer_enter": raw, "consumer_submission": raw | {"submitted_object", "submission_caller"},
        "consumer_complete": raw | {"result_bool"},
    }[v["event"]]
    if set(v) != {"schema", "event", "timestamp"} | fields: raise ValueError("event fields do not exactly match kind")
    if v["event"] == "probe_error":
        if type(v["reason"]) is not str or not v["reason"]: raise ValueError("invalid probe error")
        return v
    for name in ("address", "object", "caller", "submitted_object", "submission_caller"):
        if name in v and (type(v[name]) is not str or not POINTER.fullmatch(v[name])): raise ValueError(f"invalid {name}")
    if v["event"] == "probe_ready": return v
    for name in ("thread_id", "sequence", "invocation"):
        _uint(v[name], name)
        if v[name] == 0: raise ValueError(f"invalid positive {name}")
    _uint(v["raw_u16_14"], "raw_u16_14", 0xFFFF); _uint(v["raw_u8_16"], "raw_u8_16", 0xFF); _uint(v["raw_u32_18"], "raw_u32_18")
    if "direction" in v and v["direction"] not in ("read", "write"): raise ValueError("invalid codec direction")
    if "result_bool" in v: _uint(v["result_bool"], "result_bool", 1)
    return v


class CaptureState:
    def __init__(self, require_codec: bool = False, require_consumer: bool = False):
        self.require_codec=require_codec; self.require_consumer=require_consumer; self.ready=False; self.runtime_base: int|None=None; self.last_sequence=0
        self.codec: dict[tuple[int,int,str], int]={}; self.consumer: dict[tuple[int,int], dict[str,Any]]={}; self.codec_done=0; self.consumer_done=0; self.failures:list[str]=[]
    def accept(self, e: dict[str,Any]) -> None:
        k=e["event"]
        if k=="probe_ready":
            if self.ready:self.failures.append("duplicate probe_ready")
            self.ready=True; self.runtime_base=int(e["address"],16); return
        if k=="probe_error": self.failures.append(e["reason"]); return
        if not self.ready:self.failures.append("event arrived before probe_ready"); return
        if e["sequence"]<=self.last_sequence:self.failures.append("sequence is not strictly increasing"); return
        self.last_sequence=e["sequence"]
        expected_va={"codec_enter":0x600A60,"codec_complete":0x600A60,"consumer_enter":0x601810,"consumer_submission":0x449110,"consumer_complete":0x601810}[k]
        expected=(self.runtime_base + expected_va - 0x400000) & 0xFFFFFFFF
        if int(e["address"],16)!=expected:self.failures.append(f"{k} address is not exact guarded hook"); return
        if k.startswith("codec_"):
            key=(e["thread_id"],int(e["object"],16),e["direction"])
            if k=="codec_enter":
                if key in self.codec:self.failures.append("duplicate codec invocation"); return
                self.codec[key]=e["invocation"]
            elif self.codec.pop(key,None)!=e["invocation"]:self.failures.append("codec completion correlation failure")
            else:self.codec_done+=1
            return
        key=(e["thread_id"],e["invocation"])
        if k=="consumer_enter":
            if key in self.consumer or any(t==e["thread_id"] for t,_ in self.consumer):self.failures.append("duplicate consumer invocation"); return
            self.consumer[key]={"object":e["object"],"submitted":False}; return
        s=self.consumer.get(key)
        if s is None or s["object"]!=e["object"]:self.failures.append("consumer correlation failure"); return
        if k=="consumer_submission":
            expected=(self.runtime_base + 0x601885 - 0x400000) & 0xFFFFFFFF
            if int(e["submission_caller"],16)!=expected:self.failures.append("submission caller is not exact 0x601885 edge"); return
            if s["submitted"]:self.failures.append("duplicate consumer submission")
            s["submitted"]=True
        elif k=="consumer_complete":
            if not s["submitted"]:self.failures.append("consumer completed without submission"); return
            del self.consumer[key]; self.consumer_done+=1
    def ensure_success(self)->None:
        if self.failures:raise RuntimeError(self.failures[0])
        if not self.ready:raise RuntimeError("probe_ready was not observed")
        if self.codec or self.consumer:raise RuntimeError("capture ended with incomplete correlation")
        if self.require_codec and not self.codec_done:raise RuntimeError("completed codec was not observed")
        if self.require_consumer and not self.consumer_done:raise RuntimeError("completed consumer was not observed")


def make_agent_source(config: dict[str,Any])->str:
    encoded=json.dumps(config,separators=(",",":"))
    return r"""'use strict';
const config=__CONFIG__;let sequence=0,nextInvocation=0,eventCount=0,activeCount=0,stopped=false;const codecs=new Map(),consumers=new Map();
function now(){return new Date().toISOString();}function emit(event,fields){if(stopped)return;if(eventCount>=config.limits.max_events){stopped=true;send({schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'});return;}eventCount++;send(Object.assign({schema:1,event,timestamp:now()},fields));}function fail(r){emit('probe_error',{reason:r});}
function readable(p,n){if(p.isNull()||n<0||n>64)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}function hex(p,n){if(!readable(p,n))throw new Error('unreadable guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}
function guardedHex(h,m){const b=h.code.match(/../g).map(x=>parseInt(x,16)),slide=m.base.toUInt32()-config.binary.image_base;for(const r of h.runtime_relocations){if(r.size!==4)throw new Error('unsupported relocation');const sv=parseInt(h.code.slice(r.offset*2,r.offset*2+8).match(/../g).reverse().join(''),16)>>>0,rv=(sv+slide)>>>0;for(let i=0;i<4;i++)b[r.offset+i]=(rv>>>(i*8))&255;}return b.map(x=>x.toString(16).padStart(2,'0')).join('');}
function raw(o){if(!readable(o,0x1c))throw new Error('unreadable TriggerCastSkillVital object');return {object:o.toString(),raw_u16_14:o.add(0x14).readU16(),raw_u8_16:o.add(0x16).readU8(),raw_u32_18:o.add(0x18).readU32()};}
function install(){const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const at={};for(const [n,h] of Object.entries(config.hooks)){at[n]=m.base.add(h.va-config.binary.image_base);if(hex(at[n],h.code.length/2)!==guardedHex(h,m))throw new Error('runtime code guard mismatch '+n);}
Interceptor.attach(at.codec,{onEnter(args){const tid=this.threadId,o=this.context.ecx,dir=args[1].toUInt32();if(dir>1){fail('invalid codec direction byte');return;}const key=tid+':'+o+':'+dir;if(codecs.has(key)||activeCount>=config.limits.max_active){fail('codec active bound/correlation failure');return;}const s={id:++nextInvocation,tid,o,dir,caller:this.returnAddress};codecs.set(key,s);activeCount++;Object.assign(s,raw(o));emit('codec_enter',Object.assign({thread_id:tid,sequence:++sequence,invocation:s.id,address:at.codec.toString(),caller:s.caller.toString(),direction:dir?'write':'read'},raw(o)));s.timer=setTimeout(()=>{if(codecs.get(key)===s){codecs.delete(key);activeCount--;fail('codec correlation timeout');}},config.limits.timeout_ms);this.key=key;},onLeave(){const s=codecs.get(this.key);if(!s)return;emit('codec_complete',Object.assign({thread_id:s.tid,sequence:++sequence,invocation:s.id,address:at.codec.toString(),caller:s.caller.toString(),direction:s.dir?'write':'read'},raw(s.o)));clearTimeout(s.timer);codecs.delete(this.key);activeCount--;}});
Interceptor.attach(at.consumer,{onEnter(){const tid=this.threadId,o=this.context.ecx;if(consumers.has(tid)||activeCount>=config.limits.max_active){fail('consumer active bound/correlation failure');return;}const s={id:++nextInvocation,tid,o,caller:this.returnAddress};consumers.set(tid,s);activeCount++;emit('consumer_enter',Object.assign({thread_id:tid,sequence:++sequence,invocation:s.id,address:at.consumer.toString(),caller:s.caller.toString()},raw(o)));s.timer=setTimeout(()=>{if(consumers.get(tid)===s){consumers.delete(tid);activeCount--;fail('consumer correlation timeout');}},config.limits.timeout_ms);this.owned=s;},onLeave(ret){const s=this.owned;if(!s||consumers.get(s.tid)!==s)return;const result=ret.toUInt32()&255;if(result>1){fail('consumer returned non-boolean AL');return;}emit('consumer_complete',Object.assign({thread_id:s.tid,sequence:++sequence,invocation:s.id,address:at.consumer.toString(),caller:s.caller.toString(),result_bool:result},raw(s.o)));clearTimeout(s.timer);consumers.delete(s.tid);activeCount--;}});
const exactSubmissionCaller=at.submission_return;
Interceptor.attach(at.submission,{onEnter(args){const s=consumers.get(this.threadId);if(!s||!this.returnAddress.equals(exactSubmissionCaller))return;if(s.submitted){fail('duplicate consumer submission');return;}s.submitted=true;emit('consumer_submission',Object.assign({thread_id:s.tid,sequence:++sequence,invocation:s.id,address:at.submission.toString(),caller:s.caller.toString(),submission_caller:this.returnAddress.toString(),submitted_object:args[0].toString()},raw(s.o)));}});
emit('probe_ready',{address:m.base.toString()});}
try{install();}catch(e){send({schema:1,event:'probe_error',timestamp:now(),reason:String(e)});throw e;}
""".replace("__CONFIG__",encoded)


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument("--pid",type=int,required=True); ap.add_argument("--client",type=Path,default=DEFAULT_CLIENT); ap.add_argument("--config",type=Path,default=DEFAULT_CONFIG); ap.add_argument("--output",type=Path,required=True); ap.add_argument("--duration",type=float,default=0.0); ap.add_argument("--require-codec",action="store_true"); ap.add_argument("--require-consumer",action="store_true"); a=ap.parse_args()
    _base.validate_runtime_options(a.pid,a.duration); cp=a.config.resolve(strict=True); cfg=load_config(cp); client=a.client.resolve(strict=True); out=validate_output_path(a.output,client,cp); guard_binary(client,cfg)
    live=_base.process_image_path(a.pid).resolve(strict=True)
    if not live.samefile(client):raise ValueError("PID executable path differs from guarded client")
    guard_binary(live,cfg); import frida; out.parent.mkdir(parents=True,exist_ok=True); state=CaptureState(a.require_codec,a.require_consumer)
    with out.open("a",encoding="utf-8",buffering=1) as stream:
        session=frida.attach(a.pid); script=session.create_script(make_agent_source(cfg))
        def message(item,_data):
            try:
                if item.get("type")!="send":raise ValueError(item.get("description","Frida script error"))
                e=validate_event(item.get("payload"));stream.write(json.dumps(e,sort_keys=True,separators=(",",":"))+"\n");state.accept(e)
            except Exception as exc:state.failures.append(str(exc))
        script.on("message",message);script.load();deadline=None if a.duration==0 else time.monotonic()+a.duration
        try:
            while deadline is None or time.monotonic()<deadline:
                if state.failures:raise RuntimeError(state.failures[0])
                time.sleep(.1)
        except KeyboardInterrupt:pass
        finally:time.sleep(.05);_consumer.finalize_capture(state,script,session)
    return 0

if __name__=="__main__":raise SystemExit(main())
