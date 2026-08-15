#!/usr/bin/env python3
"""Guarded observe-only probe for the SCENE-008 EA7D consumer lifecycle."""
from __future__ import annotations
import argparse, importlib.util, json, math, re, sys, time
from pathlib import Path
from typing import Any

ROOT=Path(__file__).resolve().parents[1]
_spec=importlib.util.spec_from_file_location("pf_action_probe_base",Path(__file__).with_name("pf_action_producer_probe.py"))
_base=importlib.util.module_from_spec(_spec); sys.modules[_spec.name]=_base; _spec.loader.exec_module(_base)
DEFAULT_CONFIG=Path(__file__).with_name("pf_action_consumer_probe_local_config.json")
DEFAULT_CLIENT=ROOT.parent/"GameClient"/"GameClient.local.bin"
DEFAULT_CAPTURE_ROOT=ROOT.parent/"GameClient"/"capture_action_consumer"
EXACT_BINARIES=_base.EXACT_BINARIES
EXACT_HOOKS={
 "handler":{"va":0x7516E5,"code":"8bf18b461c8b4e185051e82c13cbff8b","runtime_relocations":[]},
 "constructor_return":{"va":0x75180E,"code":"8bd8e90d0100008b46","runtime_relocations":[]},
 "attach_call":{"va":0x7519A1,"code":"538bcfe8472ad3ff","runtime_relocations":[]},
 "actor_attach":{"va":0x4843F0,"code":"8b44240485c0741ff74010000000406a","runtime_relocations":[]},
 "queue_add":{"va":0x4A0C90,"code":"568bf1807e1e0074198b4c240885c90f","runtime_relocations":[]},
 "update_before":{"va":0x47AF1B,"code":"8bf1f64610080f856e030000","runtime_relocations":[]},
 "update_after":{"va":0x47B295,"code":"b0018b8c242801000064890d00000000","runtime_relocations":[]},
}
KINDS={"probe_ready","handler","constructor_return","attach_call","actor_attach","queue_add","update_before","update_after","probe_error"}
POINTER=re.compile(r"^0x[0-9a-f]+$")

def _hooks(config): return tuple(config["hooks"][name] for name in EXACT_HOOKS)

def load_config(path:Path)->dict[str,Any]:
 data=json.loads(path.read_text(encoding="utf-8"))
 if type(data) is not dict or set(data)!={"schema","binary","hooks","correlation"} or data["schema"]!=1: raise ValueError("invalid consumer probe config root")
 if type(data["binary"]) is not dict or data["binary"]!=EXACT_BINARIES.get(data["binary"].get("filename")): raise ValueError("binary profile differs from exact allowlist")
 if data["hooks"]!=EXACT_HOOKS: raise ValueError("consumer hook provenance differs from exact allowlist")
 if data["correlation"]!={"action":0xEA7D,"target":0x203D,"timeout_ms":2000,"max_events":256}: raise ValueError("correlation policy differs from exact allowlist")
 return data

def guard_binary(path:Path,config):
 pe=_base.guard_binary(path,{"binary":config["binary"],"hooks":{"action_producer":config["hooks"]["handler"],"candidate_branches":[],"action_queue":config["hooks"]["constructor_return"]}})
 raw=path.read_bytes()
 for hook in _hooks(config):
  sig=bytes.fromhex(hook["code"]); off=pe.rva_to_offset(hook["va"]-pe.image_base)
  if raw[off:off+len(sig)]!=sig: raise ValueError(f"client code guard mismatch at VA 0x{hook['va']:X}")
 return pe

def validate_output_path(output:Path,client:Path,config_path:Path,capture_root:Path=DEFAULT_CAPTURE_ROOT)->Path:
 resolved=_base.validate_output_path(output,client,config_path,capture_root)
 probe=Path(__file__).resolve()
 if resolved==probe or (resolved.exists() and resolved.samefile(probe)):
  raise ValueError("output aliases a guarded input")
 return resolved

def validate_runtime_options(pid:int,duration:float)->None: _base.validate_runtime_options(pid,duration)

class CaptureState(_base.CaptureState):
 ORDER=("handler","constructor_return","attach_call","actor_attach","queue_add","update_before","update_after")
 def __init__(self):
  super().__init__();self.index=0;self.pre_thread=None;self.update_thread=None;self.object=None;self.actor=None;self.queue=None;self.before=None
 def accept(self,event):
  super().accept(event)
  kind=event["event"]
  if kind in ("probe_ready","probe_error"):return
  if self.index>=len(self.ORDER) or kind!=self.ORDER[self.index]:
   self.failures.append("consumer events are incomplete or out of order");return
  if kind=="handler":self.pre_thread=event["thread_id"]
  elif kind=="constructor_return":
   if event["thread_id"]!=self.pre_thread or self.object is not None:self.failures.append("constructor ownership ambiguity or thread mismatch")
   self.object=event["object"]
  elif kind=="attach_call":
   if event["thread_id"]!=self.pre_thread or event["object"]!=self.object:self.failures.append("attach call correlation mismatch")
   self.actor=event["actor"]
  elif kind=="actor_attach":
   if event["thread_id"]!=self.pre_thread or event["object"]!=self.object or event["actor"]!=self.actor:self.failures.append("actor attach correlation mismatch")
   self.queue=event["expected_queue"]
  elif kind=="queue_add":
   if event["thread_id"]!=self.pre_thread or event["object"]!=self.object or event["queue"]!=self.queue:self.failures.append("queue correlation mismatch")
  elif kind=="update_before":
   if event["object"]!=self.object:self.failures.append("update object mismatch")
   self.update_thread=event["thread_id"];self.before=event["flags"]
  elif kind=="update_after":
   if event["thread_id"]!=self.update_thread or event["object"]!=self.object or event["flags_before"]!=self.before:self.failures.append("update completion correlation mismatch")
  self.index+=1
 def ensure_success(self):
  super().ensure_success()
  if self.index!=len(self.ORDER):raise RuntimeError("complete ordered consumer correlation was not observed")

def validate_event(p:Any)->dict[str,Any]:
 if type(p) is not dict or p.get("schema")!=1 or type(p.get("schema")) is not int or p.get("event") not in KINDS: raise ValueError("consumer event schema is invalid")
 kind=p["event"]
 fields={
  "probe_ready":{"timestamp","address"}, "probe_error":{"timestamp","reason"},
  "handler":{"timestamp","thread_id","sequence","address","request","performer","target","action"},
  "constructor_return":{"timestamp","thread_id","sequence","address","object","action","implementation","flags"},
  "attach_call":{"timestamp","thread_id","sequence","address","actor","object"},
  "actor_attach":{"timestamp","thread_id","sequence","address","actor","object","flags","expected_queue"},
  "queue_add":{"timestamp","thread_id","sequence","address","queue","object"},
  "update_before":{"timestamp","thread_id","sequence","address","object","implementation","flags"},
  "update_after":{"timestamp","thread_id","sequence","address","object","flags_before","flags_after"},
 }[kind]
 if set(p)!={"schema","event"}|fields: raise ValueError("consumer event fields do not exactly match kind")
 if type(p["timestamp"]) is not str or not p["timestamp"]: raise ValueError("invalid timestamp")
 for key in ("thread_id","sequence","action","flags","flags_before","flags_after"):
  if key in p and (type(p[key]) is not int or isinstance(p[key],bool) or not 0<=p[key]<=0xFFFFFFFF): raise ValueError(f"invalid {key}")
 for key in ("address","request","performer","target","object","implementation","actor","expected_queue","queue"):
  if key in p and (type(p[key]) is not str or not POINTER.fullmatch(p[key])): raise ValueError(f"invalid {key}")
 if kind=="handler" and (p["action"]!=0xEA7D or p["target"]!="0x203d" or p["performer"]=="0x0"): raise ValueError("handler tuple is outside SCENE-008")
 if kind=="constructor_return" and p["action"]!=0xEA7D: raise ValueError("constructed action is outside SCENE-008")
 if kind=="update_before" and (p["implementation"]!="0x0" or not p["flags"]&8): raise ValueError("update entry is not the proven terminal no-implementation lane")
 if kind=="update_after" and (not p["flags_before"]&8 or not p["flags_after"]&8): raise ValueError("update return is nonterminal")
 if kind=="probe_error" and (type(p["reason"]) is not str or not p["reason"]): raise ValueError("invalid error reason")
 return p

def make_agent_source(config)->str:
 c=json.dumps(config,separators=(",",":"))
 return f"""'use strict';
const config={c}; let sequence=0,eventCount=0; const active=new Map(); const owners=new Map();
function now(){{return new Date().toISOString();}} function emit(event,fields){{eventCount++;if(!Number.isFinite(eventCount)||eventCount>config.correlation.max_events){{send({{schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'}});return;}}send(Object.assign({{schema:1,event,timestamp:now()}},fields));}}
function readable(p,n){{if(p.isNull()||n<0||n>256)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}}
function hex(p,n){{if(!readable(p,n))throw new Error('unreadable code guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}}
function ptr64(p){{if(!readable(p,8))throw new Error('unreadable qword');const lo=p.readU32().toString(16).padStart(8,'0'),hi=p.add(4).readU32().toString(16).padStart(8,'0');return '0x'+hi+lo;}}
function state(tid){{const s=active.get(tid);if(s&&Date.now()-s.started>config.correlation.timeout_ms){{active.delete(tid);owners.delete(s.object||'');emit('probe_error',{{reason:'correlation timeout'}});return null;}}return s||null;}}
function diagnostic(stage,tid,want,actual,object){{return 'stage='+stage+' thread='+tid+' expected='+want+' actual='+actual+' object='+(object||'0x0');}}
function step(tid,want,stage,object){{const s=state(tid);if(!s)return null;if(s.step!==want){{emit('probe_error',{{reason:diagnostic(stage,tid,want,s.step,object||s.object)}});return null;}}return s;}}
function install(){{const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const at=h=>m.base.add(h.va-config.binary.image_base);
for(const name of Object.keys(config.hooks)){{const h=config.hooks[name];if(hex(at(h),h.code.length/2)!==h.code)throw new Error('runtime code guard mismatch '+name);}}
Interceptor.attach(at(config.hooks.handler),{{onEnter(){{const q=this.context.ecx;if(!readable(q,0x50)){{emit('probe_error',{{reason:'unreadable ActionVital handler object'}});return;}}const action=q.add(0x30).readU32(),target=ptr64(q.add(0x20));if(action!==config.correlation.action||target!=='0x000000000000203d')return;const performer=ptr64(q.add(0x18));if(performer==='0x0000000000000000'){{emit('probe_error',{{reason:'zero performer in SCENE-008 handler'}});return;}}if(active.has(this.threadId)){{emit('probe_error',{{reason:'overlapping thread correlation'}});return;}}const started=Date.now(),tid=this.threadId,s={{step:'handler',started,request:q.toString(),object:null,actor:null}};active.set(tid,s);setTimeout(()=>{{const pre=active.get(tid),owned=s.object?owners.get(s.object):null;if((pre&&pre.started===started)||(owned&&owned.started===started)){{active.delete(tid);if(s.object)owners.delete(s.object);emit('probe_error',{{reason:'correlation timeout'}});}}}},config.correlation.timeout_ms);emit('handler',{{thread_id:tid,sequence:++sequence,address:this.context.pc.toString(),request:q.toString(),performer, target:'0x203d',action}});}}}});
Interceptor.attach(at(config.hooks.constructor_return),{{onEnter(){{const o=this.context.eax,s=step(this.threadId,'handler','constructor_return',o.toString());if(!s)return;if(!readable(o,0x50)){{emit('probe_error',{{reason:'unreadable constructed action'}});return;}}if(o.add(0x20).readU32()!==config.correlation.action){{emit('probe_error',{{reason:'constructed action mismatch'}});return;}}s.object=o.toString();if(owners.has(s.object)){{emit('probe_error',{{reason:'action object ownership ambiguity or reuse'}});return;}}s.step='constructed';owners.set(s.object,s);emit('constructor_return',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),object:s.object,action:o.add(0x20).readU32(),implementation:o.add(0x4c).readPointer().toString(),flags:o.add(0x10).readU32()}});}}}});
Interceptor.attach(at(config.hooks.attach_call),{{onEnter(){{const o=this.context.ebx,s=step(this.threadId,'constructed','attach_call',o.toString());if(!s)return;const a=this.context.edi;if(o.toString()!==s.object){{emit('probe_error',{{reason:diagnostic('attach_call',this.threadId,'object='+s.object,'object='+o.toString(),o.toString())}});return;}}s.actor=a.toString();s.step='attach_call';emit('attach_call',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),actor:s.actor,object:s.object}});}}}});
Interceptor.attach(at(config.hooks.actor_attach),{{onEnter(args){{const key=args[0].toString(),owned=owners.get(key);if(owned===undefined)return;const current=active.get(this.threadId);if(current!==owned){{emit('probe_error',{{reason:diagnostic('actor_attach',this.threadId,'owning prequeue thread','different or absent thread state',key)}});return;}}const s=step(this.threadId,'attach_call','actor_attach',key);if(!s)return;if(this.context.ecx.toString()!==s.actor){{emit('probe_error',{{reason:diagnostic('actor_attach',this.threadId,'actor='+s.actor,'actor='+this.context.ecx.toString(),key)}});return;}}const flags=args[0].add(0x10).readU32();if((flags&0x40000000)!==0){{emit('probe_error',{{reason:'unexpected actor queue lane'}});return;}}s.queue=this.context.ecx.add(0x20).toString();s.step='actor_attach';emit('actor_attach',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),actor:s.actor,object:s.object,flags,expected_queue:s.queue}});}}}});
Interceptor.attach(at(config.hooks.queue_add),{{onEnter(args){{const key=args[0].toString(),owned=owners.get(key);if(owned===undefined)return;const current=active.get(this.threadId);if(current!==owned){{emit('probe_error',{{reason:diagnostic('queue_add',this.threadId,'owning prequeue thread','different or absent thread state',key)}});return;}}const s=step(this.threadId,'actor_attach','queue_add',key);if(!s)return;if(this.context.ecx.toString()!==s.queue){{emit('probe_error',{{reason:diagnostic('queue_add',this.threadId,'queue='+s.queue,'queue='+this.context.ecx.toString(),key)}});return;}}s.step='queued';active.delete(this.threadId);emit('queue_add',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),queue:s.queue,object:s.object}});}}}});
Interceptor.attach(at(config.hooks.update_before),{{onEnter(){{const o=this.context.ecx,key=o.toString(),s=owners.get(key);if(s===undefined)return;if(s.step!=='queued'){{emit('probe_error',{{reason:diagnostic('update_before',this.threadId,'queued',s.step,key)}});return;}}if(!readable(o,0x50)){{emit('probe_error',{{reason:'unreadable action at update entry'}});return;}}const implementation=o.add(0x4c).readPointer().toString(),flags=o.add(0x10).readU32();if(implementation!=='0x0'||(flags&8)===0){{emit('probe_error',{{reason:'nonterminal action at update entry'}});owners.delete(key);return;}}s.before=flags;s.updateThread=this.threadId;s.step='updating';emit('update_before',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),object:key,implementation,flags}});}}}});
Interceptor.attach(at(config.hooks.update_after),{{onEnter(){{const o=this.context.esi,key=o.toString(),s=owners.get(key);if(s===undefined)return;if(s.step!=='updating'||s.updateThread!==this.threadId){{const expected='step=updating owner_thread='+s.updateThread,actual='step='+s.step+' current_thread='+this.threadId;emit('probe_error',{{reason:diagnostic('update_after',this.threadId,expected,actual,key)}});return;}}const after=o.add(0x10).readU32();if((s.before&8)===0||(after&8)===0){{emit('probe_error',{{reason:'nonterminal action at common return'}});owners.delete(key);return;}}emit('update_after',{{thread_id:this.threadId,sequence:++sequence,address:this.context.pc.toString(),object:key,flags_before:s.before,flags_after:after}});owners.delete(key);}}}});
emit('probe_ready',{{address:m.base.toString()}});}}
try{{install();}}catch(e){{send({{schema:1,event:'probe_error',timestamp:now(),reason:String(e)}});throw e;}}"""

def main()->int:
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--pid",type=int,required=True);ap.add_argument("--client",type=Path,default=DEFAULT_CLIENT);ap.add_argument("--config",type=Path,default=DEFAULT_CONFIG);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--duration",type=float,default=0.0);a=ap.parse_args()
 validate_runtime_options(a.pid,a.duration);config=load_config(a.config.resolve());client=a.client.resolve(strict=True);out=validate_output_path(a.output,client,a.config);guard_binary(client,config)
 live=_base.process_image_path(a.pid).resolve(strict=True)
 if not live.samefile(client):raise ValueError("PID executable path differs from guarded client")
 guard_binary(live,config);import frida;out.parent.mkdir(parents=True,exist_ok=True);state=CaptureState()
 with out.open("a",encoding="utf-8",buffering=1) as stream:
  session=frida.attach(a.pid);script=session.create_script(make_agent_source(config))
  def message(m,_d):
   try:
    if m.get("type")!="send":raise ValueError(m.get("description","Frida script error"))
    e=validate_event(m.get("payload"));stream.write(json.dumps(e,sort_keys=True,separators=(",",":"))+"\n");state.accept(e)
   except Exception as exc:state.failures.append(str(exc))
  script.on("message",message);script.load();deadline=None if a.duration==0 else time.monotonic()+a.duration
  try:
   while deadline is None or time.monotonic()<deadline:
    if state.failures:raise RuntimeError(state.failures[0])
    time.sleep(.1)
  except KeyboardInterrupt:pass
  finally:
   time.sleep(.05)
   try:state.ensure_success()
   finally:script.unload();session.detach()
 return 0
if __name__=="__main__":raise SystemExit(main())
