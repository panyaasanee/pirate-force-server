#!/usr/bin/env python3
"""Checksum-guarded observe-only BEHAVIOR entry-field probe."""
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

DEFAULT_CONFIG = Path(__file__).with_name("pf_behavior_entry_probe_local_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_behavior_entry"
EXACT_BINARIES = _base.EXACT_BINARIES
EXACT_HOOKS = {
    "numeric_lookup": {
        "va": 0x702A10,
        "code": "83ec08837c240c00750833c083c408c20400",
        "runtime_relocations": [],
    }
}
EXACT_LIMITS = {"max_events": 256, "max_active": 64, "max_vector_records": 32, "record_stride": 0x38}
EVENTS = {"probe_ready", "behavior_entry_result", "probe_error"}
POINTER = re.compile(r"^0x[0-9a-f]+$")
ENTRY_FIELDS = {
    "thread_id", "sequence", "address", "caller", "manager", "key", "entry", "n_id",
    "n_amount_target", "n_range", "n_damage_area", "n_profit", "n_thendo",
    "n_class", "hit_vector_object", "hit_vector_begin", "hit_vector_end",
    "hit_vector_count",
}


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "behavior_manager_va", "hooks", "limits"} or data["schema"] != 1:
        raise ValueError("invalid behavior entry probe config root")
    if type(data["binary"]) is not dict or data["binary"] != EXACT_BINARIES.get(data["binary"].get("filename")):
        raise ValueError("binary profile differs from exact allowlist")
    if data["behavior_manager_va"] != 0x102DAD8 or data["hooks"] != EXACT_HOOKS or data["limits"] != EXACT_LIMITS:
        raise ValueError("behavior entry provenance differs from exact allowlist")
    return data


def guard_binary(path: Path, config: dict[str, Any]):
    hook = config["hooks"]["numeric_lookup"]
    pe = _base.guard_binary(path, {"binary": config["binary"], "hooks": {"action_producer": hook, "candidate_branches": [], "action_queue": hook}})
    raw = path.read_bytes()
    sig = bytes.fromhex(hook["code"])
    off = pe.rva_to_offset(hook["va"] - pe.image_base)
    if raw[off : off + len(sig)] != sig:
        raise ValueError("client code guard mismatch at numeric BEHAVIOR lookup")
    return pe


def validate_output_path(output: Path, client: Path, config: Path, capture_root: Path = DEFAULT_CAPTURE_ROOT) -> Path:
    resolved = _base.validate_output_path(output, client, config, capture_root)
    guarded = [
        Path(__file__).resolve(),
        Path(__file__).with_name("pf_behavior_entry_probe_config.json").resolve(),
        Path(__file__).with_name("pf_behavior_entry_probe_local_config.json").resolve(),
    ]
    for item in guarded:
        if resolved == item or (resolved.exists() and resolved.samefile(item)):
            raise ValueError("output aliases a guarded input")
    return resolved


class CaptureState:
    def __init__(self, require_entry: bool = False):
        self.require_entry = require_entry
        self.ready = False
        self.runtime_base: int | None = None
        self.entries = 0
        self.last_sequence = 0
        self.failures: list[str] = []

    def accept(self, event: dict[str, Any]) -> None:
        if event["event"] == "probe_ready":
            if self.ready:
                self.failures.append("duplicate probe_ready")
                return
            self.ready = True
            self.runtime_base = int(event["address"], 16)
        elif event["event"] == "probe_error":
            self.failures.append(event["reason"])
        else:
            if not self.ready or self.runtime_base is None:
                self.failures.append("entry arrived before probe_ready")
                return
            expected_manager = (self.runtime_base + 0x102DAD8 - 0x400000) & 0xFFFFFFFF
            if int(event["manager"], 16) != expected_manager:
                self.failures.append("BEHAVIOR manager does not match runtime base")
                return
            sequence = event["sequence"]
            if sequence <= self.last_sequence:
                self.failures.append("entry sequence is not strictly increasing")
                return
            self.last_sequence = sequence
            self.entries += 1

    def ensure_success(self) -> None:
        if self.failures:
            raise RuntimeError(self.failures[0])
        if not self.ready:
            raise RuntimeError("probe_ready was not observed")
        if self.require_entry and not self.entries:
            raise RuntimeError("natural non-null BEHAVIOR entry was not observed")


def validate_event(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value.get("schema") != 1 or value.get("event") not in EVENTS:
        raise ValueError("invalid behavior entry event")
    if type(value.get("timestamp")) is not str or not value["timestamp"]:
        raise ValueError("invalid event timestamp")
    fields = {
        "probe_ready": {"address"},
        "probe_error": {"reason"},
        "behavior_entry_result": ENTRY_FIELDS,
    }[value["event"]]
    if set(value) != {"schema", "event", "timestamp"} | fields:
        raise ValueError("event fields do not exactly match kind")
    if value["event"] == "probe_error":
        if type(value["reason"]) is not str or not value["reason"]:
            raise ValueError("invalid probe error")
        return value
    for key in ("address", "caller", "manager", "entry", "hit_vector_object", "hit_vector_begin", "hit_vector_end"):
        if key in value and (type(value[key]) is not str or not POINTER.fullmatch(value[key])):
            raise ValueError(f"invalid {key}")
    if value["event"] == "behavior_entry_result":
        integer_fields = ENTRY_FIELDS - {"address", "caller", "manager", "entry", "hit_vector_object", "hit_vector_begin", "hit_vector_end"}
        for key in integer_fields:
            if type(value[key]) is not int or isinstance(value[key], bool) or not 0 <= value[key] <= 0xFFFFFFFF:
                raise ValueError(f"invalid {key}")
        if value["thread_id"] == 0 or value["sequence"] == 0:
            raise ValueError("invalid positive identity or sequence")
        if value["n_id"] != value["key"]:
            raise ValueError("lookup key and n_ID differ")
        if value["hit_vector_count"] > EXACT_LIMITS["max_vector_records"]:
            raise ValueError("invalid hit vector count")
        pointers = {key: int(value[key], 16) for key in ("manager", "entry", "hit_vector_object", "hit_vector_begin", "hit_vector_end")}
        if pointers["manager"] == 0 or pointers["entry"] == 0 or any(pointer & 3 for pointer in pointers.values()):
            raise ValueError("unaligned or null entry provenance pointer")
        if pointers["hit_vector_object"] != pointers["entry"] + 0xE4:
            raise ValueError("hit vector object does not equal entry+0xE4")
        begin, end = pointers["hit_vector_begin"], pointers["hit_vector_end"]
        if (begin == 0) != (end == 0):
            raise ValueError("inconsistent null hit vector bounds")
        if end < begin or end - begin != value["hit_vector_count"] * EXACT_LIMITS["record_stride"]:
            raise ValueError("hit vector extent differs from count and stride")
    return value


def make_agent_source(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, separators=(",", ":"))
    return """'use strict';
const config=__CONFIG__;let sequence=0,eventCount=0,active=0;
function now(){return new Date().toISOString();}
function emit(event,fields){eventCount++;if(eventCount>config.limits.max_events){send({schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'});return;}send(Object.assign({schema:1,event,timestamp:now()},fields));}
function readable(p,n,max){if(p.isNull()||n<0||n>max)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}
function hex(p,n){if(!readable(p,n,256))throw new Error('unreadable code guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}
function aligned4(p){return p.and(3).isNull();}
function install(){const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const h=config.hooks.numeric_lookup,at=m.base.add(h.va-config.binary.image_base);if(hex(at,h.code.length/2)!==h.code)throw new Error('runtime code guard mismatch numeric_lookup');
const behaviorManager=m.base.add(config.behavior_manager_va-config.binary.image_base);
Interceptor.attach(at,{onEnter(args){this.valid=this.context.ecx.equals(behaviorManager);if(!this.valid)return;if(active>=config.limits.max_active){emit('probe_error',{reason:'active lookup bound exceeded'});this.valid=false;return;}active++;this.key=args[0].toUInt32();this.address=this.context.pc.toString();this.caller=this.returnAddress.toString();this.manager=this.context.ecx.toString();},onLeave(retval){if(!this.valid)return;active--;if(retval.isNull())return;try{if(!aligned4(retval)||!readable(retval,0xf8,0xf8))throw new Error('invalid or unreadable BEHAVIOR entry');const nId=retval.add(4).readU32();if(nId!==this.key)throw new Error('lookup key and n_ID differ');const vectorObject=retval.add(0xe4),begin=retval.add(0xf0).readPointer(),end=retval.add(0xf4).readPointer();if(!aligned4(begin)||!aligned4(end))throw new Error('unaligned hit vector bounds');let count=0;if(begin.isNull()!==end.isNull())throw new Error('inconsistent hit vector bounds');if(!begin.isNull()){if(end.compare(begin)<0)throw new Error('reversed hit vector bounds');const delta=end.sub(begin).toUInt32();if(delta%config.limits.record_stride!==0)throw new Error('misaligned hit vector extent');count=delta/config.limits.record_stride;if(count>config.limits.max_vector_records)throw new Error('hit vector count bound exceeded');if(delta>0&&!readable(begin,delta,config.limits.max_vector_records*config.limits.record_stride))throw new Error('unreadable hit vector extent');}
emit('behavior_entry_result',{thread_id:this.threadId,sequence:++sequence,address:this.address,caller:this.caller,manager:this.manager,key:this.key,entry:retval.toString(),n_id:nId,n_amount_target:retval.add(0x2c).readU32(),n_range:retval.add(0x30).readU32(),n_damage_area:retval.add(0x34).readU32(),n_profit:retval.add(0x38).readU32(),n_thendo:retval.add(0x3c).readU32(),n_class:retval.add(0x7c).readU32(),hit_vector_object:vectorObject.toString(),hit_vector_begin:begin.toString(),hit_vector_end:end.toString(),hit_vector_count:count});}catch(e){emit('probe_error',{reason:String(e)});}}});
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
    parser.add_argument("--require-entry", action="store_true")
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
    state = CaptureState(args.require_entry)
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
            _consumer.finalize_capture(state, script, session)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
