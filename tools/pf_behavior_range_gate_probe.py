#!/usr/bin/env python3
"""Guarded observe-only EA7D geometric-threshold gate probe."""
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
_base = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _base
_spec.loader.exec_module(_base)
_consumer_spec = importlib.util.spec_from_file_location("pf_action_consumer_probe_base", Path(__file__).with_name("pf_action_consumer_probe.py"))
_consumer = importlib.util.module_from_spec(_consumer_spec)
sys.modules[_consumer_spec.name] = _consumer
_consumer_spec.loader.exec_module(_consumer)

DEFAULT_CONFIG = Path(__file__).with_name("pf_behavior_range_gate_probe_local_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_behavior_range_gate"
EXACT_BINARIES = _base.EXACT_BINARIES
EXACT_HOOKS = {
    "gate_call": {"va": 0x44EB1D, "code": "e8ae6d0200", "runtime_relocations": []},
    "gate_result": {"va": 0x44EB22, "code": "83c41084c07427", "runtime_relocations": []},
    "range_function": {"va": 0x755540, "code": "518b4424085350e824c7d4ff", "runtime_relocations": []},
    "range_empty": {"va": 0x755558, "code": "5b59c20800", "runtime_relocations": []},
    "range_selected": {"va": 0x755604, "code": "8b5030c64424180189542410", "runtime_relocations": []},
    "range_post_x87_dead": {"va": 0x475A9C, "code": "f30f104424188b4514", "runtime_relocations": []},
}
EXACT_LIMITS = {"max_events": 256, "max_active": 32, "max_selections": 32, "timeout_ms": 2000}
EVENTS = {"probe_ready", "gate_enter", "range_enter", "range_empty", "range_selected", "range_complete", "gate_result", "probe_error"}
POINTER = re.compile(r"^0x[0-9a-f]+$")


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks", "limits"} or data["schema"] != 1:
        raise ValueError("invalid range gate probe config root")
    if type(data["binary"]) is not dict or data["binary"] != EXACT_BINARIES.get(data["binary"].get("filename")):
        raise ValueError("binary profile differs from exact allowlist")
    if data["hooks"] != EXACT_HOOKS or data["limits"] != EXACT_LIMITS:
        raise ValueError("range gate provenance differs from exact allowlist")
    return data


def guard_binary(path: Path, config: dict[str, Any]):
    first = config["hooks"]["gate_call"]
    pe = _base.guard_binary(path, {"binary": config["binary"], "hooks": {"action_producer": first, "candidate_branches": [], "action_queue": first}})
    raw = path.read_bytes()
    for name, hook in config["hooks"].items():
        sig = bytes.fromhex(hook["code"])
        off = pe.rva_to_offset(hook["va"] - pe.image_base)
        if raw[off : off + len(sig)] != sig:
            raise ValueError(f"client code guard mismatch at {name}")
    return pe


def validate_output_path(output: Path, client: Path, config: Path, capture_root: Path = DEFAULT_CAPTURE_ROOT) -> Path:
    resolved = _base.validate_output_path(output, client, config, capture_root)
    guarded = [Path(__file__).resolve(), Path(__file__).with_name("pf_behavior_range_gate_probe_config.json").resolve(), Path(__file__).with_name("pf_behavior_range_gate_probe_local_config.json").resolve()]
    for item in guarded:
        if resolved == item or (resolved.exists() and resolved.samefile(item)):
            raise ValueError("output aliases a guarded input")
    return resolved


class CaptureState:
    def __init__(self, require_gate: bool = False, require_complete: bool = False):
        self.require_gate = require_gate
        self.require_complete = require_complete
        self.ready = False
        self.runtime_base: int | None = None
        self.last_sequence = 0
        self.gates: dict[tuple[int, int], dict[str, Any]] = {}
        self.active_threads: set[int] = set()
        self.results = 0
        self.complete_results = 0
        self.failures: list[str] = []

    def accept(self, event: dict[str, Any]) -> None:
        kind = event["event"]
        if kind == "probe_ready":
            if self.ready:
                self.failures.append("duplicate probe_ready")
            self.ready = True
            self.runtime_base = int(event["address"], 16)
            return
        if kind == "probe_error":
            self.failures.append(event["reason"])
            return
        if not self.ready:
            self.failures.append("gate event arrived before probe_ready")
            return
        sequence = event["sequence"]
        if sequence <= self.last_sequence:
            self.failures.append("gate sequence is not strictly increasing")
            return
        self.last_sequence = sequence
        key = (event["thread_id"], event["invocation"])
        if kind == "gate_enter":
            expected_caller = (self.runtime_base + 0x44EB22 - 0x400000) & 0xFFFFFFFF
            if int(event["caller"], 16) != expected_caller:
                self.failures.append("gate caller is not exact 0x44EB1D path")
                return
            if key in self.gates or event["thread_id"] in self.active_threads:
                self.failures.append("duplicate or nested gate invocation")
                return
            self.gates[key] = {"range": False, "ranges": 0, "selections": 0}
            self.active_threads.add(event["thread_id"])
            return
        state = self.gates.get(key)
        if state is None:
            self.failures.append("event has no matching gate invocation")
            return
        if kind == "range_enter":
            if state["range"] or state["ranges"] != 0:
                self.failures.append("invalid range-enter order")
            else:
                state["range"] = True
            return
        if kind == "range_selected":
            if not state["range"]:
                self.failures.append("selection outside range invocation")
            else:
                state["selections"] += 1
                if state["selections"] > EXACT_LIMITS["max_selections"]:
                    self.failures.append("selection bound exceeded")
            return
        if kind == "range_empty":
            if not state["range"]:
                self.failures.append("empty range result without invocation")
            else:
                state["range"] = False
            return
        if kind == "range_complete":
            if not state["range"]:
                self.failures.append("range completion without entry")
            else:
                state["range"] = False
                state["ranges"] = 1
            return
        if kind == "gate_result":
            if state["range"] or event["range_count"] != state["ranges"]:
                self.failures.append("gate result has incomplete or mismatched range count")
                return
            self.results += 1
            if state["ranges"] == 1:
                self.complete_results += 1
            del self.gates[key]
            self.active_threads.remove(event["thread_id"])

    def ensure_success(self) -> None:
        if self.failures:
            raise RuntimeError(self.failures[0])
        if not self.ready:
            raise RuntimeError("probe_ready was not observed")
        if self.gates:
            raise RuntimeError("capture ended with incomplete gate invocation")
        if self.require_gate and not self.results:
            raise RuntimeError("EA7D gate result was not observed")
        if self.require_complete and not self.complete_results:
            raise RuntimeError("EA7D gate with completed range selection was not observed")


def _uint(value: Any, name: str, upper: int = 0xFFFFFFFF) -> None:
    if type(value) is not int or isinstance(value, bool) or not 0 <= value <= upper:
        raise ValueError(f"invalid {name}")


def validate_event(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value.get("schema") != 1 or value.get("event") not in EVENTS:
        raise ValueError("invalid range gate event")
    if type(value.get("timestamp")) is not str or not value["timestamp"]:
        raise ValueError("invalid event timestamp")
    fields = {
        "probe_ready": {"address"}, "probe_error": {"reason"},
        "gate_enter": {"thread_id", "sequence", "invocation", "address", "caller", "action"},
        "range_enter": {"thread_id", "sequence", "invocation", "address", "source_key", "mode"},
        "range_empty": {"thread_id", "sequence", "invocation", "address"},
        "range_selected": {"thread_id", "sequence", "invocation", "address", "entry", "n_id", "n_range"},
        "range_complete": {"thread_id", "sequence", "invocation", "address", "raw_selected"},
        "gate_result": {"thread_id", "sequence", "invocation", "address", "result_bool", "range_count"},
    }[value["event"]]
    if set(value) != {"schema", "event", "timestamp"} | fields:
        raise ValueError("event fields do not exactly match kind")
    if value["event"] == "probe_error":
        if type(value["reason"]) is not str or not value["reason"]:
            raise ValueError("invalid probe error")
        return value
    for name in ("address", "caller", "entry"):
        if name in value and (type(value[name]) is not str or not POINTER.fullmatch(value[name])):
            raise ValueError(f"invalid {name}")
    if value["event"] != "probe_ready":
        for name in ("thread_id", "sequence", "invocation"):
            _uint(value[name], name)
            if value[name] == 0:
                raise ValueError(f"invalid positive {name}")
    for name in ("action", "source_key", "mode", "n_id"):
        if name in value:
            _uint(value[name], name)
    if "n_range" in value and (type(value["n_range"]) is not int or isinstance(value["n_range"], bool) or not -0x80000000 <= value["n_range"] <= 0x7FFFFFFF):
        raise ValueError("invalid n_range")
    if "raw_selected" in value and (type(value["raw_selected"]) is not int or isinstance(value["raw_selected"], bool) or not -0x80000000 <= value["raw_selected"] <= 0x7FFFFFFF):
        raise ValueError("invalid raw_selected")
    if value["event"] == "gate_enter" and value["action"] != 0xEA7D:
        raise ValueError("gate action is not exact EA7D")
    if value["event"] == "gate_result":
        _uint(value["result_bool"], "result_bool", 1)
        _uint(value["range_count"], "range_count", 1)
    return value


def make_agent_source(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, separators=(",", ":"))
    return """'use strict';
const config=__CONFIG__;let sequence=0,nextInvocation=0,eventCount=0,activeCount=0;const gates=new Map();
function now(){return new Date().toISOString();}
function emit(event,fields){eventCount++;if(eventCount>config.limits.max_events){send({schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'});return;}send(Object.assign({schema:1,event,timestamp:now()},fields));}
function fail(reason){emit('probe_error',{reason});}
function readable(p,n){if(p.isNull()||n<0||n>256)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}
function hex(p,n){if(!readable(p,n))throw new Error('unreadable code guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}
function guardedHex(p,h,m){const bytes=h.code.match(/../g).map(x=>parseInt(x,16));const slide=m.base.toUInt32()-config.binary.image_base;for(const r of h.runtime_relocations){if(r.size!==4)throw new Error('unsupported runtime relocation');const staticValue=parseInt(h.code.slice(r.offset*2,r.offset*2+8).match(/../g).reverse().join(''),16)>>>0;const runtimeValue=(staticValue+slide)>>>0;for(let i=0;i<4;i++)bytes[r.offset+i]=(runtimeValue>>>(i*8))&255;}return bytes.map(b=>b.toString(16).padStart(2,'0')).join('');}
function owner(tid){const s=gates.get(tid);if(!s)return null;if(Date.now()-s.started>config.limits.timeout_ms){fail('gate correlation timeout');gates.delete(tid);activeCount--;return null;}return s;}
function completeRange(tid,address){const s=owner(tid);if(!s||s.range===null)return;const raw=s.range.selected===null?10:s.range.selected;emit('range_complete',{thread_id:tid,sequence:++sequence,invocation:s.id,address,raw_selected:raw});s.range=null;s.ranges=1;}
function install(){const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const at={};for(const [name,h] of Object.entries(config.hooks)){at[name]=m.base.add(h.va-config.binary.image_base);if(hex(at[name],h.code.length/2)!==guardedHex(at[name],h,m))throw new Error('runtime code guard mismatch '+name);}const exactCaller=at.gate_result;
Interceptor.attach(at.gate_call,{onEnter(){if(this.context.ebx.toUInt32()!==0xea7d)return;const tid=this.threadId;if(gates.has(tid)){const existing=gates.get(tid);clearTimeout(existing.timer);gates.delete(tid);activeCount--;fail('duplicate gate invocation');return;}if(activeCount>=config.limits.max_active){fail('active gate bound exceeded');return;}const s={id:++nextInvocation,started:Date.now(),range:null,ranges:0};gates.set(tid,s);activeCount++;emit('gate_enter',{thread_id:tid,sequence:++sequence,invocation:s.id,address:this.context.pc.toString(),caller:exactCaller.toString(),action:0xea7d});const id=s.id;s.timer=setTimeout(()=>{const current=gates.get(tid);if(current&&current.id===id){fail('gate correlation timeout');gates.delete(tid);activeCount--; }},config.limits.timeout_ms);}});
Interceptor.attach(at.gate_result,{onEnter(){const tid=this.threadId,s=gates.get(tid);if(!s)return;if(s.range!==null){fail('gate returned with active range');return;}const result=this.context.eax.toUInt32()&0xff;if(result>1){fail('gate returned non-boolean AL');return;}emit('gate_result',{thread_id:tid,sequence:++sequence,invocation:s.id,address:this.context.pc.toString(),result_bool:result,range_count:s.ranges});clearTimeout(s.timer);gates.delete(tid);activeCount--;}});
Interceptor.attach(at.range_function,{onEnter(args){const s=owner(this.threadId);if(!s)return;if(s.range!==null||s.ranges!==0){fail('range invocation order failure');return;}s.range={sourceKey:args[0].toUInt32(),mode:args[1].toUInt32(),selections:0,selected:null};emit('range_enter',{thread_id:this.threadId,sequence:++sequence,invocation:s.id,address:this.context.pc.toString(),source_key:s.range.sourceKey,mode:s.range.mode});}});
Interceptor.attach(at.range_empty,{onEnter(){const s=owner(this.threadId);if(!s)return;if(s.range===null){fail('empty result without range invocation');return;}emit('range_empty',{thread_id:this.threadId,sequence:++sequence,invocation:s.id,address:this.context.pc.toString()});s.range=null;}});
Interceptor.attach(at.range_selected,{onEnter(){const s=owner(this.threadId);if(!s)return;if(s.range===null){fail('selection without range invocation');return;}if(++s.range.selections>config.limits.max_selections){fail('selection bound exceeded');return;}const entry=this.context.eax;if(!readable(entry,0x34)){fail('unreadable selected BEHAVIOR entry');return;}const selected=entry.add(0x30).readS32();s.range.selected=selected;emit('range_selected',{thread_id:this.threadId,sequence:++sequence,invocation:s.id,address:this.context.pc.toString(),entry:entry.toString(),n_id:entry.add(4).readU32(),n_range:selected});}});
Interceptor.attach(at.range_post_x87_dead,{onEnter(){completeRange(this.threadId,this.context.pc.toString());}});
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
    parser.add_argument("--require-gate", action="store_true")
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    _base.validate_runtime_options(args.pid, args.duration)
    config_path = args.config.resolve(strict=True); config = load_config(config_path)
    client = args.client.resolve(strict=True); output = validate_output_path(args.output, client, config_path)
    guard_binary(client, config)
    live = _base.process_image_path(args.pid).resolve(strict=True)
    if not live.samefile(client): raise ValueError("PID executable path differs from guarded client")
    guard_binary(live, config)
    import frida
    output.parent.mkdir(parents=True, exist_ok=True)
    state = CaptureState(args.require_gate, args.require_complete)
    with output.open("a", encoding="utf-8", buffering=1) as stream:
        session = frida.attach(args.pid); script = session.create_script(make_agent_source(config))
        def message(item, _data):
            try:
                if item.get("type") != "send": raise ValueError(item.get("description", "Frida script error"))
                event = validate_event(item.get("payload")); stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"); state.accept(event)
            except Exception as exc: state.failures.append(str(exc))
        script.on("message", message); script.load()
        deadline = None if args.duration == 0 else time.monotonic() + args.duration
        try:
            while deadline is None or time.monotonic() < deadline:
                if state.failures: raise RuntimeError(state.failures[0])
                time.sleep(0.1)
        except KeyboardInterrupt: pass
        finally:
            time.sleep(0.05); _consumer.finalize_capture(state, script, session)
    return 0


if __name__ == "__main__": raise SystemExit(main())
