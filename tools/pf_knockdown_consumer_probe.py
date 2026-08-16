#!/usr/bin/env python3
"""Guarded observe-only CKnockdownVital codec and consumer-chain probe."""
from __future__ import annotations

import argparse, importlib.util, json, math, re, sys, time
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
def _load(name:str,file:str):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
_base=_load("pf_knock_base","pf_action_producer_probe.py");_consumer=_load("pf_knock_cleanup","pf_action_consumer_probe.py")
DEFAULT_CONFIG=Path(__file__).with_name("pf_knockdown_consumer_probe_local_config.json")
DEFAULT_CLIENT=ROOT.parent/"GameClient"/"GameClient.local.bin"
DEFAULT_CAPTURE_ROOT=ROOT.parent/"GameClient"/"capture_knockdown_consumer"
EXACT_BINARIES=_base.EXACT_BINARIES
EXACT_HOOKS={
 "codec":{"va":0x74EBF0,"code":"807c24080056578b7c240c","runtime_relocations":[]},
 "consumer":{"va":0x750700,"code":"568bf18b461c8b4e18575051","runtime_relocations":[]},
 "manager":{"va":0x47CAD0,"code":"6aff685dabb80064a1000000005053555657a1bcb4020133c4508d44241464a300000000","runtime_relocations":[{"offset":3,"size":4},{"offset":19,"size":4}]},
 "dispatch":{"va":0x4843F0,"code":"8b44240485c0741ff7401000000040","runtime_relocations":[]},
 "queue":{"va":0x4A0C90,"code":"568bf1807e1e0074198b4c240885c9","runtime_relocations":[]}}
EXACT_LIMITS={"max_events":256,"max_active":32,"timeout_ms":2000}
POINTER=re.compile(r"^0x[0-9a-f]+$")
RAW={"thread_id","sequence","invocation","address","object","caller","raw_qword_18","raw_u32_20","raw_u32_24","raw_f32_28","raw_f32_2c","raw_f32_30","raw_f32_34"}
EVENT_FIELDS={
 "probe_ready":{"address"},"probe_error":{"reason"},
 "codec_enter":RAW|{"direction"},"codec_complete":RAW|{"direction"},
 "consumer_enter":RAW,"manager_return":RAW|{"receiver","wrapper","manager_caller"},
 "actor40_dispatch":RAW|{"receiver","wrapper","dispatch_caller","wrapper_vtable","wrapper_flags"},
 "queue_enter":RAW|{"receiver","wrapper","queue_caller","queue_argument"},
 "consumer_complete":RAW|{"result_bool","completion_path"}}

def load_config(path:Path)->dict[str,Any]:
    d=json.loads(path.read_text(encoding="utf-8"))
    if type(d) is not dict or set(d)!={"schema","binary","hooks","limits"} or d["schema"]!=1:raise ValueError("invalid knockdown config root")
    if type(d["binary"]) is not dict or d["binary"]!=EXACT_BINARIES.get(d["binary"].get("filename")):raise ValueError("binary profile differs from exact allowlist")
    if d["hooks"]!=EXACT_HOOKS or d["limits"]!=EXACT_LIMITS:raise ValueError("knockdown provenance differs from exact allowlist")
    return d

def guard_binary(path:Path,cfg:dict[str,Any]):
    first=cfg["hooks"]["codec"];pe=_base.guard_binary(path,{"binary":cfg["binary"],"hooks":{"action_producer":first,"candidate_branches":[],"action_queue":first}});raw=path.read_bytes()
    for n,h in cfg["hooks"].items():
        sig=bytes.fromhex(h["code"]);off=pe.rva_to_offset(h["va"]-pe.image_base)
        if raw[off:off+len(sig)]!=sig:raise ValueError(f"client code guard mismatch at {n}")
    return pe

def validate_output_path(output:Path,client:Path,config:Path,capture_root:Path=DEFAULT_CAPTURE_ROOT)->Path:
    p=_base.validate_output_path(output,client,config,capture_root)
    guarded=[Path(__file__).resolve(),Path(__file__).with_name("pf_knockdown_consumer_probe_config.json").resolve(),Path(__file__).with_name("pf_knockdown_consumer_probe_local_config.json").resolve()]
    if any(p==x or (p.exists() and p.samefile(x)) for x in guarded):raise ValueError("output aliases a guarded input")
    return p

def _u(v:Any,n:str,top:int=0xffffffff):
    if type(v) is not int or isinstance(v,bool) or not 0<=v<=top:raise ValueError(f"invalid {n}")
def validate_event(v:Any)->dict[str,Any]:
    if type(v) is not dict or v.get("schema")!=1 or v.get("event") not in EVENT_FIELDS:raise ValueError("invalid knockdown event")
    if type(v.get("timestamp")) is not str or not v["timestamp"]:raise ValueError("invalid timestamp")
    if set(v)!={"schema","event","timestamp"}|EVENT_FIELDS[v["event"]]:raise ValueError("event fields do not exactly match kind")
    if v["event"]=="probe_error":
        if type(v["reason"]) is not str or not v["reason"]:raise ValueError("invalid probe error")
        return v
    for n in ("address","object","caller","receiver","wrapper","manager_caller","dispatch_caller","queue_caller","wrapper_vtable"):
        if n in v and (type(v[n]) is not str or not POINTER.fullmatch(v[n])):raise ValueError(f"invalid {n}")
    if v["event"]=="probe_ready":return v
    for n in ("thread_id","sequence","invocation"):_u(v[n],n); 
    if min(v["thread_id"],v["sequence"],v["invocation"])<=0:raise ValueError("lifecycle integers must be positive")
    if type(v["raw_qword_18"]) is not str or not POINTER.fullmatch(v["raw_qword_18"]):raise ValueError("invalid raw_qword_18")
    _u(v["raw_u32_20"],"raw_u32_20");_u(v["raw_u32_24"],"raw_u32_24")
    for n in ("raw_f32_28","raw_f32_2c","raw_f32_30","raw_f32_34"):
        if type(v[n]) not in (int,float) or isinstance(v[n],bool) or not math.isfinite(v[n]):raise ValueError(f"invalid {n}")
    if "direction" in v and v["direction"] not in ("read","write"):raise ValueError("invalid direction")
    if "result_bool" in v and v["result_bool"]!=1:raise ValueError("consumer result is not exact true")
    if "completion_path" in v and v["completion_path"] not in ("null_wrapper","queued"):raise ValueError("invalid completion_path")
    if "queue_argument" in v and v["queue_argument"]!=1:raise ValueError("queue argument is not exact 1")
    if "wrapper_flags" in v and v["wrapper_flags"]!=0x40000005:raise ValueError("wrapper flags mismatch")
    return v

class CaptureState:
    def __init__(self,require_consumer:bool=False):self.require_consumer=require_consumer;self.ready=False;self.base=None;self.last=0;self.codec={};self.active={};self.done=0;self.failures=[]
    def accept(self,e:dict[str,Any]):
        k=e["event"]
        if k=="probe_ready":
            if self.ready:self.failures.append("duplicate probe_ready")
            self.ready=True;self.base=int(e["address"],16);return
        if k=="probe_error":self.failures.append(e["reason"]);return
        if not self.ready:self.failures.append("event before probe_ready");return
        if e["sequence"]<=self.last:self.failures.append("sequence not strictly increasing");return
        self.last=e["sequence"];vas={"codec_enter":0x74ebf0,"codec_complete":0x74ebf0,"consumer_enter":0x750700,"manager_return":0x47cad0,"actor40_dispatch":0x4843f0,"queue_enter":0x4a0c90,"consumer_complete":0x750700}
        if int(e["address"],16)!=(self.base+vas[k]-0x400000)&0xffffffff:self.failures.append("wrong exact hook address");return
        if k.startswith("codec_"):
            q=(e["thread_id"],e["object"],e["direction"])
            if k=="codec_enter":
                if q in self.codec:self.failures.append("duplicate codec")
                else:self.codec[q]=e["invocation"]
            elif self.codec.pop(q,None)!=e["invocation"]:self.failures.append("codec correlation failure")
            return
        q=(e["thread_id"],e["invocation"])
        snap={name:e[name] for name in ("raw_qword_18","raw_u32_20","raw_u32_24","raw_f32_28","raw_f32_2c","raw_f32_30","raw_f32_34")}
        if k=="consumer_enter":
            if q in self.active or any(t==e["thread_id"] for t,_ in self.active):self.failures.append("duplicate consumer")
            else:self.active[q]={"object":e["object"],"raw":snap,"step":"enter","wrapper":None,"receiver":None}
            return
        s=self.active.get(q)
        if not s or s["object"]!=e["object"]:self.failures.append("consumer correlation failure");return
        if s["raw"]!=snap:self.failures.append("consumer raw snapshot mutation");return
        expected={"manager_return":"enter","actor40_dispatch":"manager","queue_enter":"dispatch"}.get(k)
        if expected is not None and s["step"]!=expected:self.failures.append("consumer event order failure");return
        if k=="manager_return":
            if int(e["manager_caller"],16)!=(self.base+0x750761-0x400000)&0xffffffff:self.failures.append("manager caller mismatch");return
            s.update(step="manager",wrapper=e["wrapper"],receiver=e["receiver"])
        elif k in ("actor40_dispatch","queue_enter"):
            if e["wrapper"]!=s["wrapper"] or e["receiver"]!=s["receiver"]:self.failures.append("wrapper/receiver correlation failure");return
            if k=="actor40_dispatch":
                if int(e["dispatch_caller"],16)!=(self.base+0x750769-0x400000)&0xffffffff:self.failures.append("dispatch caller mismatch");return
                if e["wrapper"]=="0x0" or int(e["wrapper_vtable"],16)!=(self.base+0xf0f7dc-0x400000)&0xffffffff:self.failures.append("successful wrapper provenance failure");return
                s["step"]="dispatch"
            else:
                if int(e["queue_caller"],16)!=(self.base+0x48440c-0x400000)&0xffffffff:self.failures.append("queue caller mismatch");return
                s["step"]="queue"
        else:
            if e["completion_path"]=="null_wrapper":
                if s["step"]!="manager" or s["wrapper"]!="0x0":self.failures.append("invalid null-wrapper completion");return
            elif s["step"]!="queue" or not s["wrapper"] or s["wrapper"]=="0x0":self.failures.append("invalid queued completion");return
            del self.active[q];self.done+=1
    def ensure_success(self):
        if self.failures:raise RuntimeError(self.failures[0])
        if not self.ready:raise RuntimeError("probe_ready not observed")
        if self.codec or self.active:raise RuntimeError("incomplete correlation")
        if self.require_consumer and not self.done:raise RuntimeError("completed consumer not observed")

def make_agent_source(cfg:dict[str,Any])->str:
    return r'''"use strict";const c=__C__;let seq=0,nxt=0,count=0,active=0,stopped=false;const codecs=new Map(),cs=new Map();
function now(){return new Date().toISOString()}function emit(event,x){if(stopped)return;if(count>=c.limits.max_events){stopped=true;send({schema:1,event:"probe_error",timestamp:now(),reason:"event bound exceeded"});return}count++;send(Object.assign({schema:1,event:event,timestamp:now()},x))}function fail(x){emit("probe_error",{reason:x})}
function readable(p,n){if(p.isNull()||n<0||n>0x100)return false;let r=Process.findRangeByAddress(p);return r&&r.protection.indexOf("r")>=0&&p.add(n).compare(r.base.add(r.size))<=0}function hx(p,n){if(!readable(p,n))throw Error("unreadable");return Array.from(new Uint8Array(p.readByteArray(n)),x=>x.toString(16).padStart(2,"0")).join("")}function guarded(h,m){let b=h.code.match(/../g).map(x=>parseInt(x,16)),slide=m.base.toUInt32()-c.binary.image_base;for(let r of h.runtime_relocations){if(r.size!==4)throw Error("relocation size");let z=parseInt(h.code.slice(r.offset*2,r.offset*2+8).match(/../g).reverse().join(""),16)>>>0,v=(z+slide)>>>0;for(let i=0;i<4;i++)b[r.offset+i]=(v>>>(8*i))&255}return b.map(x=>x.toString(16).padStart(2,"0")).join("")}
function raw(o){if(!readable(o,0x38))throw Error("unreadable vital");let q=o.add(0x18).readU64();let x={object:o.toString(),raw_qword_18:"0x"+q.toString(16),raw_u32_20:o.add(0x20).readU32(),raw_u32_24:o.add(0x24).readU32(),raw_f32_28:o.add(0x28).readFloat(),raw_f32_2c:o.add(0x2c).readFloat(),raw_f32_30:o.add(0x30).readFloat(),raw_f32_34:o.add(0x34).readFloat()};for(let k of ["raw_f32_28","raw_f32_2c","raw_f32_30","raw_f32_34"])if(!Number.isFinite(x[k]))throw Error("nonfinite vital");return x}
function base(s,a){return Object.assign({thread_id:s.tid,sequence:++seq,invocation:s.id,address:a.toString(),caller:s.caller.toString()},raw(s.o))}
try{let m=Process.enumerateModules().find(x=>x.name.toLowerCase()===c.binary.filename.toLowerCase());if(!m||m.size!==c.binary.size_of_image)throw Error("module mismatch");let at={};for(let [k,h] of Object.entries(c.hooks)){at[k]=m.base.add(h.va-c.binary.image_base);if(hx(at[k],h.code.length/2)!==guarded(h,m))throw Error("code guard "+k)}
Interceptor.attach(at.codec,{onEnter(args){let d=args[1].toUInt32();if(d>1){fail("direction");return}let o=this.context.ecx,k=this.threadId+":"+o+":"+d;if(codecs.has(k)||active>=c.limits.max_active){fail("codec bound");return}let s={id:++nxt,tid:this.threadId,o:o,d:d,caller:this.returnAddress};codecs.set(k,s);active++;emit("codec_enter",Object.assign(base(s,at.codec),{direction:d?"write":"read"}));s.timer=setTimeout(()=>{if(codecs.get(k)===s){codecs.delete(k);active--;fail("codec timeout")}},c.limits.timeout_ms);this.k=k},onLeave(){let s=codecs.get(this.k);if(!s)return;emit("codec_complete",Object.assign(base(s,at.codec),{direction:s.d?"write":"read"}));clearTimeout(s.timer);codecs.delete(this.k);active--}});
Interceptor.attach(at.consumer,{onEnter(){let tid=this.threadId,o=this.context.ecx;if(cs.has(tid)||active>=c.limits.max_active){fail("consumer bound");return}let s={id:++nxt,tid:tid,o:o,caller:this.returnAddress,step:"enter"};cs.set(tid,s);active++;emit("consumer_enter",base(s,at.consumer));this.s=s;s.timer=setTimeout(()=>{if(cs.get(tid)===s){cs.delete(tid);active--;fail("consumer timeout")}},c.limits.timeout_ms)},onLeave(r){let s=this.s;if(!s||cs.get(s.tid)!==s)return;let b=r.toUInt32()&255;if(b!==1){fail("consumer result is not exact true");return}let path=s.step==="queue"?"queued":(s.step==="manager"&&s.wrapper.isNull()?"null_wrapper":null);if(path===null){fail("consumer incomplete chain");return}emit("consumer_complete",Object.assign(base(s,at.consumer),{result_bool:b,completion_path:path}));clearTimeout(s.timer);cs.delete(s.tid);active--}});
Interceptor.attach(at.manager,{onEnter(){let s=cs.get(this.threadId);if(!s||!this.returnAddress.equals(at.consumer.add(0x61)))return;if(s.step!=="enter"){fail("manager order");return}this.s=s;this.receiver=this.context.edi;this.managerCaller=this.returnAddress},onLeave(r){let s=this.s;if(!s)return;s.wrapper=r;s.receiver=this.receiver;s.step="manager";emit("manager_return",Object.assign(base(s,at.manager),{receiver:this.receiver.toString(),wrapper:r.toString(),manager_caller:this.managerCaller.toString()}))}});
Interceptor.attach(at.dispatch,{onEnter(args){let s=cs.get(this.threadId);if(!s||!this.returnAddress.equals(at.consumer.add(0x69)))return;if(s.step!=="manager"||!args[0].equals(s.wrapper)||!this.context.ecx.equals(s.receiver)){fail("dispatch correlation");return}if(s.wrapper.isNull())return;if(!readable(s.wrapper,0x14)){fail("wrapper unreadable");return}let vt=s.wrapper.readPointer(),fl=s.wrapper.add(0x10).readU32(),expectedVtable=m.base.add(0xf0f7dc-c.binary.image_base);if(!vt.equals(expectedVtable)||fl!==0x40000005){fail("wrapper provenance");return}s.step="dispatch";emit("actor40_dispatch",Object.assign(base(s,at.dispatch),{receiver:s.receiver.toString(),wrapper:s.wrapper.toString(),dispatch_caller:this.returnAddress.toString(),wrapper_vtable:vt.toString(),wrapper_flags:fl}))}});
Interceptor.attach(at.queue,{onEnter(args){let s=cs.get(this.threadId);if(!s||!this.returnAddress.equals(at.dispatch.add(0x1c)))return;if(s.step!=="dispatch"||!args[0].equals(s.wrapper)||args[1].toUInt32()!==1||!this.context.ecx.equals(s.receiver.add(0x40))){fail("queue correlation");return}s.step="queue";emit("queue_enter",Object.assign(base(s,at.queue),{receiver:s.receiver.toString(),wrapper:s.wrapper.toString(),queue_caller:this.returnAddress.toString(),queue_argument:1}))}});emit("probe_ready",{address:m.base.toString()})}catch(e){send({schema:1,event:"probe_error",timestamp:now(),reason:String(e)});throw e}'''.replace("__C__",json.dumps(cfg,separators=(",",":")))

def main()->int:
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--pid",type=int,required=True);p.add_argument("--client",type=Path,default=DEFAULT_CLIENT);p.add_argument("--config",type=Path,default=DEFAULT_CONFIG);p.add_argument("--output",type=Path,required=True);p.add_argument("--duration",type=float,default=0);p.add_argument("--require-consumer",action="store_true");a=p.parse_args();_base.validate_runtime_options(a.pid,a.duration)
    cp=a.config.resolve(strict=True);cfg=load_config(cp);client=a.client.resolve(strict=True);out=validate_output_path(a.output,client,cp);guard_binary(client,cfg);live=_base.process_image_path(a.pid).resolve(strict=True)
    if not live.samefile(client):raise ValueError("PID executable differs from client")
    guard_binary(live,cfg);import frida;out.parent.mkdir(parents=True,exist_ok=True);state=CaptureState(a.require_consumer)
    with out.open("a",encoding="utf-8",buffering=1) as f:
        session=frida.attach(a.pid);script=session.create_script(make_agent_source(cfg))
        def msg(item,_):
            try:
                if item.get("type")!="send":raise ValueError(item.get("description","Frida error"))
                e=validate_event(item.get("payload"));f.write(json.dumps(e,sort_keys=True,separators=(",",":"))+"\n");state.accept(e)
            except Exception as x:state.failures.append(str(x))
        script.on("message",msg);script.load();deadline=None if a.duration==0 else time.monotonic()+a.duration
        try:
            while deadline is None or time.monotonic()<deadline:
                if state.failures:raise RuntimeError(state.failures[0])
                time.sleep(.1)
        except KeyboardInterrupt:pass
        finally:time.sleep(.05);_consumer.finalize_capture(state,script,session)
    return 0
if __name__=="__main__":raise SystemExit(main())
