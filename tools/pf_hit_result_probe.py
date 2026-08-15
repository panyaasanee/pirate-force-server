#!/usr/bin/env python3
"""Checksum-guarded, observe-only SCENE-009 CHitResult consumer probe."""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
import time
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "pf_action_probe_base", Path(__file__).with_name("pf_action_producer_probe.py")
)
_base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _base
_spec.loader.exec_module(_base)
_consumer_spec = importlib.util.spec_from_file_location(
    "pf_action_consumer_probe_base", Path(__file__).with_name("pf_action_consumer_probe.py")
)
_consumer = importlib.util.module_from_spec(_consumer_spec)
sys.modules[_consumer_spec.name] = _consumer
_consumer_spec.loader.exec_module(_consumer)

DEFAULT_CONFIG = Path(__file__).with_name("pf_hit_result_probe_local_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_hit_result"
EXACT_BINARIES = _base.EXACT_BINARIES
EXACT_HOOKS = {
    "handler": {"va": 0x7507A5, "code": "8be98b451c8b4d185051e86c22cbff8b", "runtime_relocations": []},
    "target_resolved": {"va": 0x7508A9, "code": "8bf085f60f84a4030000f74610000001", "runtime_relocations": []},
    "target_vfunc_bit0": {"va": 0x7508F7, "code": "ffd2eb1e8b01eb8ca8607416", "runtime_relocations": []},
    "target_vfunc_bits5_6": {"va": 0x750917, "code": "ffd0837b08000f8db3000000", "runtime_relocations": []},
    "presentation_call": {"va": 0x750DAA, "code": "e831f0ceff85db7531", "runtime_relocations": []},
    "implementation_return": {"va": 0x750A5E, "code": "8bf885ff741c6a018d530c528bcee8ff", "runtime_relocations": []},
    "implementation_mark": {"va": 0x750A78, "code": "578bcee87039d3ff8b7c2414f6431c", "runtime_relocations": []},
    "target_queue": {"va": 0x750A7B, "code": "e87039d3ff8b7c2414f6431c", "runtime_relocations": []},
    "handler_return": {"va": 0x750E95, "code": "b0018b8c248800000064890d00000000", "runtime_relocations": []},
}
EXACT_LIMITS = {"vital_id": 0x16F7, "timeout_ms": 2000, "max_events": 256, "max_records": 32}
EVENTS = {"probe_ready", "hit_result", "target_resolved", "target_vfunc", "presentation", "implementation_return", "implementation_mark", "target_queue", "hit_complete", "probe_error"}
POINTER = re.compile(r"^0x[0-9a-f]+$")


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks", "limits"} or data["schema"] != 1:
        raise ValueError("invalid hit-result probe config root")
    if type(data["binary"]) is not dict or data["binary"] != EXACT_BINARIES.get(data["binary"].get("filename")):
        raise ValueError("binary profile differs from exact allowlist")
    if data["hooks"] != EXACT_HOOKS:
        raise ValueError("hit-result hook provenance differs from exact allowlist")
    if data["limits"] != EXACT_LIMITS:
        raise ValueError("hit-result limits differ from exact allowlist")
    return data


def guard_binary(path: Path, config: dict[str, Any]):
    hooks = list(config["hooks"].values())
    pe = _base.guard_binary(path, {"binary": config["binary"], "hooks": {"action_producer": hooks[0], "candidate_branches": [], "action_queue": hooks[1]}})
    raw = path.read_bytes()
    for hook in hooks:
        sig = bytes.fromhex(hook["code"])
        off = pe.rva_to_offset(hook["va"] - pe.image_base)
        if raw[off : off + len(sig)] != sig:
            raise ValueError(f"client code guard mismatch at VA 0x{hook['va']:X}")
    return pe


def validate_output_path(output: Path, client: Path, config: Path, capture_root: Path = DEFAULT_CAPTURE_ROOT) -> Path:
    resolved = _base.validate_output_path(output, client, config, capture_root)
    guarded = [Path(__file__).resolve(), Path(__file__).with_name("pf_hit_result_probe_config.json").resolve(), Path(__file__).with_name("pf_hit_result_probe_local_config.json").resolve()]
    for item in guarded:
        if resolved == item or (resolved.exists() and resolved.samefile(item)):
            raise ValueError("output aliases a guarded input")
    return resolved


class CaptureState:
    def __init__(self, require_hit: bool = False):
        self.require_hit = require_hit
        self.ready = False
        self.open_hits: set[tuple[int, str]] = set()
        self.completed_hits = 0
        self.last_sequence = 0
        self.failures: list[str] = []

    def accept(self, event: dict[str, Any]) -> None:
        if event["event"] == "probe_ready":
            self.ready = True
        elif event["event"] == "probe_error":
            self.failures.append(event["reason"])
        else:
            sequence = event.get("sequence")
            if type(sequence) is not int or isinstance(sequence, bool) or sequence <= self.last_sequence:
                self.failures.append("lifecycle sequence is not positive and strictly increasing")
                return
            self.last_sequence = sequence
            key = (event.get("thread_id"), event.get("object"))
            if event["event"] == "hit_result":
                if key in self.open_hits:
                    self.failures.append("duplicate active CHitResult handler")
                else:
                    self.open_hits.add(key)
            elif key not in self.open_hits:
                self.failures.append("lifecycle event has no matching active handler")
            elif event["event"] == "hit_complete":
                self.open_hits.remove(key)
                self.completed_hits += 1

    def ensure_success(self) -> None:
        if self.failures:
            raise RuntimeError(self.failures[0])
        if not self.ready:
            raise RuntimeError("probe_ready was not observed")
        if self.open_hits:
            raise RuntimeError("CHitResult handler did not complete")
        if self.require_hit and not self.completed_hits:
            raise RuntimeError("complete CHitResult was not observed")


def validate_event(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value.get("schema") != 1 or value.get("event") not in EVENTS:
        raise ValueError("invalid hit-result event")
    if type(value.get("timestamp")) is not str or not value["timestamp"]:
        raise ValueError("invalid hit-result timestamp")
    fields = {
        "probe_ready": {"address"}, "probe_error": {"reason"},
        "hit_result": {"thread_id", "sequence", "address", "object", "vital_id", "performer", "field_20", "action", "field_24", "field_28", "records"},
        "target_resolved": {"thread_id", "sequence", "address", "object", "record_index", "record", "target_object"},
        "target_vfunc": {"thread_id", "sequence", "address", "object", "record_index", "record", "target_object", "lane"},
        "presentation": {"thread_id", "sequence", "address", "object", "record_index", "record", "presentation_value", "flags"},
        "implementation_return": {"thread_id", "sequence", "address", "object", "record_index", "record", "implementation", "flags"},
        "implementation_mark": {"thread_id", "sequence", "address", "object", "record_index", "implementation", "flags_after"},
        "target_queue": {"thread_id", "sequence", "address", "object", "record_index", "target_actor", "implementation", "queue_lane"},
        "hit_complete": {"thread_id", "sequence", "address", "object"},
    }[value["event"]]
    if set(value) != {"schema", "event", "timestamp"} | fields:
        raise ValueError("hit-result event fields do not exactly match kind")
    if value["event"] == "probe_error" and (type(value["reason"]) is not str or not value["reason"]):
        raise ValueError("invalid probe error")
    for key in ("thread_id", "sequence", "vital_id", "field_20", "action", "field_24", "field_28", "record_index", "presentation_value", "flags", "flags_after"):
        if key in value and (type(value[key]) is not int or isinstance(value[key], bool)):
            raise ValueError(f"invalid {key}")
        if key in value and key != "presentation_value" and not 0 <= value[key] <= 0xFFFFFFFF:
            raise ValueError(f"invalid {key}")
        if key == "presentation_value" and key in value and not -(1 << 31) <= value[key] < (1 << 31):
            raise ValueError(f"invalid {key}")
    for key in ("address", "object", "performer", "record", "target_object", "implementation", "target_actor"):
        if key in value and (type(value[key]) is not str or not POINTER.fullmatch(value[key])):
            raise ValueError(f"invalid {key}")
    if value["event"] == "hit_result":
        if value["vital_id"] != 0x16F7 or type(value["records"]) is not list or len(value["records"]) > 32:
            raise ValueError("invalid CHitResult summary")
        for record in value["records"]:
            if type(record) is not dict or set(record) != {"index", "target", "presentation_value", "vector_raw", "scalar_raw", "flags"}:
                raise ValueError("invalid CHitResult record event")
            if type(record["index"]) is not int or isinstance(record["index"], bool) or not 0 <= record["index"] < 32:
                raise ValueError("invalid CHitResult record index")
            if type(record["target"]) is not str or not POINTER.fullmatch(record["target"]):
                raise ValueError("invalid CHitResult record target")
            if type(record["presentation_value"]) is not int or isinstance(record["presentation_value"], bool) or not -(1 << 31) <= record["presentation_value"] < (1 << 31):
                raise ValueError("invalid CHitResult presentation value")
            if type(record["flags"]) is not int or isinstance(record["flags"], bool) or not 0 <= record["flags"] <= 0xFFFF:
                raise ValueError("invalid CHitResult record flags")
            if type(record["vector_raw"]) is not list or len(record["vector_raw"]) != 3 or not all(type(x) in (int, float) and math.isfinite(x) for x in record["vector_raw"] + [record["scalar_raw"]]):
                raise ValueError("invalid CHitResult record scalars")
    if value.get("queue_lane") not in (None, "target+0x40") or value.get("lane") not in (None, "bit0_without_bit1", "bits5_or_6"):
        raise ValueError("invalid exact lane")
    return value


def make_agent_source(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, separators=(",", ":"))
    return """'use strict';
const config=__CONFIG__;let seq=0,eventCount=0;const active=new Map();
function now(){return new Date().toISOString();}
function emit(event,fields){eventCount++;if(eventCount>config.limits.max_events){send({schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'});return;}send(Object.assign({schema:1,event,timestamp:now()},fields));}
function readable(p,n){if(p.isNull()||n<0||n>2048)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}
function hex(p,n){if(!readable(p,n))throw new Error('unreadable code guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}
function qword(p){if(!readable(p,8))throw new Error('unreadable qword');return '0x'+p.add(4).readU32().toString(16).padStart(8,'0')+p.readU32().toString(16).padStart(8,'0');}
function fail(reason){emit('probe_error',{reason});}
function owner(tid,record){const s=active.get(tid);if(!s){return null;}if(Date.now()-s.started>config.limits.timeout_ms){active.delete(tid);fail('handler correlation timeout');return null;}if(record&&s.record!==null&&s.record!==record.toString()){active.delete(tid);fail('record correlation mismatch');return null;}return s;}
function recordIndex(s,p){const delta=p.sub(s.begin).toInt32();if(delta<0||(delta%0x20)!==0||delta/0x20>=s.records.length||p.toString()!==s.begin.add(delta).toString())return -1;return delta/0x20;}
function install(){const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const at=h=>m.base.add(h.va-config.binary.image_base);for(const name of Object.keys(config.hooks)){const h=config.hooks[name];if(hex(at(h),h.code.length/2)!==h.code)throw new Error('runtime code guard mismatch '+name);}
Interceptor.attach(at(config.hooks.handler),{onEnter(){const o=this.context.ecx;if(!readable(o,0x40)){fail('unreadable CHitResult object');return;}const begin=o.add(0x38).readPointer(),end=o.add(0x3c).readPointer();if(end.compare(begin)<0){fail('reversed CHitResult vector');return;}const extent=end.sub(begin).toUInt32();if((extent%0x20)!==0||extent/0x20>config.limits.max_records||(!begin.isNull()&&!readable(begin,extent))){fail('invalid CHitResult vector extent');return;}const records=[];for(let i=0;i<extent/0x20;i++){const r=begin.add(i*0x20),v=[r.add(0xc).readFloat(),r.add(0x10).readFloat(),r.add(0x14).readFloat()],scalar=r.add(0x18).readFloat();if(!v.every(Number.isFinite)||!Number.isFinite(scalar)){fail('nonfinite CHitResult scalar');return;}records.push({index:i,target:qword(r),presentation_value:r.add(8).readS32(),vector_raw:v,scalar_raw:scalar,flags:r.add(0x1c).readU16()});}
const tid=this.threadId;if(active.has(tid)){fail('overlapping CHitResult handler');return;}const s={started:Date.now(),object:o.toString(),begin,records,index:-1,record:null,target:null,implementation:null};active.set(tid,s);setTimeout(()=>{if(active.get(tid)===s){active.delete(tid);fail('handler correlation timeout');}},config.limits.timeout_ms);emit('hit_result',{thread_id:tid,sequence:++seq,address:this.context.pc.toString(),object:s.object,vital_id:config.limits.vital_id,performer:qword(o.add(0x18)),field_20:o.add(0x20).readU16(),action:o.add(0x22).readU16(),field_24:o.add(0x24).readU32(),field_28:o.add(0x28).readU8(),records});}});
Interceptor.attach(at(config.hooks.target_resolved),{onEnter(){const s=owner(this.threadId,null);if(!s)return;const index=recordIndex(s,this.context.ebx);if(index<0){active.delete(this.threadId);fail('record pointer is outside captured vector');return;}s.record=this.context.ebx.toString();s.index=index;s.target=this.context.eax.toString();emit('target_resolved',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:s.index,record:s.record,target_object:s.target});}});
function vfunc(lane){return {onEnter(){const s=owner(this.threadId,this.context.ebx);if(!s)return;if(this.context.esi.toString()!==s.target){active.delete(this.threadId);fail('target object correlation mismatch');return;}emit('target_vfunc',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:s.index,record:s.record,target_object:s.target,lane});}};}
Interceptor.attach(at(config.hooks.target_vfunc_bit0),vfunc('bit0_without_bit1'));Interceptor.attach(at(config.hooks.target_vfunc_bits5_6),vfunc('bits5_or_6'));
Interceptor.attach(at(config.hooks.implementation_return),{onEnter(){const s=owner(this.threadId,this.context.ebx);if(!s)return;const flags=this.context.ebx.add(0x1c).readU16();if((flags&1)===0||(flags&8)===0||(flags&16)!==0){fail('implementation gate mismatch');return;}s.implementation=this.context.eax.toString();emit('implementation_return',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:s.index,record:s.record,implementation:s.implementation,flags});}});
Interceptor.attach(at(config.hooks.implementation_mark),{onEnter(){const s=owner(this.threadId,this.context.ebx);if(!s||!s.implementation||this.context.edi.toString()!==s.implementation){fail('implementation mark correlation mismatch');return;}const flags=this.context.edi.add(0x10).readU32();if((flags&0x40000000)===0){fail('implementation mark was not observed');return;}emit('implementation_mark',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:s.index,implementation:s.implementation,flags_after:flags});}});
Interceptor.attach(at(config.hooks.target_queue),{onEnter(){const s=owner(this.threadId,this.context.ebx);if(!s||this.context.edi.toString()!==s.implementation){fail('target queue correlation mismatch');return;}emit('target_queue',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:s.index,target_actor:this.context.ecx.toString(),implementation:s.implementation,queue_lane:'target+0x40'});}});
Interceptor.attach(at(config.hooks.presentation_call),{onEnter(){const s=owner(this.threadId,null);if(!s)return;const index=recordIndex(s,this.context.esi);if(index<0){active.delete(this.threadId);fail('presentation record is outside captured vector');return;}emit('presentation',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object,record_index:index,record:this.context.esi.toString(),presentation_value:this.context.esi.add(8).readS32(),flags:this.context.esi.add(0x1c).readU16()});}});
Interceptor.attach(at(config.hooks.handler_return),{onEnter(){const s=active.get(this.threadId);if(!s)return;active.delete(this.threadId);emit('hit_complete',{thread_id:this.threadId,sequence:++seq,address:this.context.pc.toString(),object:s.object});}});
emit('probe_ready',{address:m.base.toString()});}
try{install();}catch(e){send({schema:1,event:'probe_error',timestamp:now(),reason:String(e)});throw e;}
""".replace("__CONFIG__", encoded)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--require-hit", action="store_true")
    args = parser.parse_args()
    _base.validate_runtime_options(args.pid, args.duration)
    config_path = args.config.resolve(strict=True)
    config = load_config(config_path)
    client = args.client.resolve(strict=True)
    output = validate_output_path(args.output, client, config_path)
    guard_binary(client, config)
    live = _base.process_image_path(args.pid).resolve(strict=True)
    if not live.samefile(client):
        raise ValueError("PID executable path differs from guarded client")
    guard_binary(live, config)
    import frida
    output.parent.mkdir(parents=True, exist_ok=True)
    state = CaptureState(args.require_hit)
    with output.open("a", encoding="utf-8", buffering=1) as stream:
        session = frida.attach(args.pid)
        script = session.create_script(make_agent_source(config))
        def message(item, _data):
            try:
                if item.get("type") != "send":
                    raise ValueError(item.get("description", "Frida script error"))
                event = validate_event(item.get("payload"))
                stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                state.accept(event)
            except Exception as exc:
                state.failures.append(str(exc))
        script.on("message", message)
        script.load()
        deadline = None if args.duration == 0 else time.monotonic() + args.duration
        try:
            while deadline is None or time.monotonic() < deadline:
                if state.failures:
                    raise RuntimeError(state.failures[0])
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            time.sleep(0.05)
            try:
                _consumer.finalize_capture(state, script, session)
            finally:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
