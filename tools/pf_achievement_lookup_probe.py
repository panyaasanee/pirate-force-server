#!/usr/bin/env python3
"""Checksum-guarded observe-only ACHIEVEMENT-registry lookup probe."""
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

DEFAULT_CONFIG = Path(__file__).with_name("pf_achievement_lookup_probe_local_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_achievement_lookup"
EXACT_BINARIES = _base.EXACT_BINARIES
EXACT_HOOKS = {
    "numeric_lookup": {
        "va": 0x702A10,
        "code": "83ec08837c240c00750833c083c408c20400",
        "runtime_relocations": [],
    }
}
EXACT_LIMITS = {"max_events": 256, "max_active": 64}
EVENTS = {"probe_ready", "numeric_lookup_result", "probe_error"}
POINTER = re.compile(r"^0x[0-9a-f]+$")


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks", "limits"} or data["schema"] != 1:
        raise ValueError("invalid achievement lookup probe config root")
    if type(data["binary"]) is not dict or data["binary"] != EXACT_BINARIES.get(data["binary"].get("filename")):
        raise ValueError("binary profile differs from exact allowlist")
    if data["hooks"] != EXACT_HOOKS or data["limits"] != EXACT_LIMITS:
        raise ValueError("achievement lookup provenance differs from exact allowlist")
    return data


def guard_binary(path: Path, config: dict[str, Any]):
    hook = config["hooks"]["numeric_lookup"]
    pe = _base.guard_binary(path, {"binary": config["binary"], "hooks": {"action_producer": hook, "candidate_branches": [], "action_queue": hook}})
    raw = path.read_bytes()
    sig = bytes.fromhex(hook["code"])
    off = pe.rva_to_offset(hook["va"] - pe.image_base)
    if raw[off : off + len(sig)] != sig:
        raise ValueError("client code guard mismatch at numeric ACHIEVEMENT lookup")
    return pe


def validate_output_path(output: Path, client: Path, config: Path, capture_root: Path = DEFAULT_CAPTURE_ROOT) -> Path:
    resolved = _base.validate_output_path(output, client, config, capture_root)
    guarded = [Path(__file__).resolve(), Path(__file__).with_name("pf_achievement_lookup_probe_config.json").resolve(), Path(__file__).with_name("pf_achievement_lookup_probe_local_config.json").resolve()]
    for item in guarded:
        if resolved == item or (resolved.exists() and resolved.samefile(item)):
            raise ValueError("output aliases a guarded input")
    return resolved


class CaptureState:
    def __init__(self, require_lookup: bool = False):
        self.require_lookup = require_lookup
        self.ready = False
        self.lookups = 0
        self.last_sequence = 0
        self.failures: list[str] = []

    def accept(self, event: dict[str, Any]) -> None:
        if event["event"] == "probe_ready":
            self.ready = True
        elif event["event"] == "probe_error":
            self.failures.append(event["reason"])
        else:
            sequence = event["sequence"]
            if sequence <= self.last_sequence:
                self.failures.append("lookup sequence is not strictly increasing")
                return
            self.last_sequence = sequence
            self.lookups += 1

    def ensure_success(self) -> None:
        if self.failures:
            raise RuntimeError(self.failures[0])
        if not self.ready:
            raise RuntimeError("probe_ready was not observed")
        if self.require_lookup and not self.lookups:
            raise RuntimeError("numeric achievement lookup was not observed")


def validate_event(value: Any) -> dict[str, Any]:
    if type(value) is not dict or value.get("schema") != 1 or value.get("event") not in EVENTS:
        raise ValueError("invalid achievement lookup event")
    if type(value.get("timestamp")) is not str or not value["timestamp"]:
        raise ValueError("invalid event timestamp")
    fields = {
        "probe_ready": {"address"},
        "probe_error": {"reason"},
        "numeric_lookup_result": {"thread_id", "sequence", "address", "caller", "key", "entry"},
    }[value["event"]]
    if set(value) != {"schema", "event", "timestamp"} | fields:
        raise ValueError("event fields do not exactly match kind")
    if value["event"] == "probe_error":
        if type(value["reason"]) is not str or not value["reason"]:
            raise ValueError("invalid probe error")
        return value
    for key in ("address", "caller", "entry"):
        if key in value and (type(value[key]) is not str or not POINTER.fullmatch(value[key])):
            raise ValueError(f"invalid {key}")
    if value["event"] == "numeric_lookup_result":
        for key in ("thread_id", "sequence", "key"):
            if type(value[key]) is not int or isinstance(value[key], bool) or not 0 <= value[key] <= 0xFFFFFFFF:
                raise ValueError(f"invalid {key}")
        if value["sequence"] == 0:
            raise ValueError("invalid sequence")
    return value


def make_agent_source(config: dict[str, Any]) -> str:
    encoded = json.dumps(config, separators=(",", ":"))
    return """'use strict';
const config=__CONFIG__;let sequence=0,eventCount=0,active=0;
function now(){return new Date().toISOString();}
function emit(event,fields){eventCount++;if(eventCount>config.limits.max_events){send({schema:1,event:'probe_error',timestamp:now(),reason:'event bound exceeded'});return;}send(Object.assign({schema:1,event,timestamp:now()},fields));}
function readable(p,n){if(p.isNull()||n<0||n>256)return false;const r=Process.findRangeByAddress(p);return r!==null&&r.protection.indexOf('r')>=0&&p.add(n).compare(r.base.add(r.size))<=0;}
function hex(p,n){if(!readable(p,n))throw new Error('unreadable code guard');return Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');}
function install(){const m=Process.enumerateModules().find(x=>x.name.toLowerCase()===config.binary.filename.toLowerCase());if(!m||m.size!==config.binary.size_of_image)throw new Error('runtime module guard mismatch');const h=config.hooks.numeric_lookup,at=m.base.add(h.va-config.binary.image_base);if(hex(at,h.code.length/2)!==h.code)throw new Error('runtime code guard mismatch numeric_lookup');
Interceptor.attach(at,{onEnter(args){if(active>=config.limits.max_active){emit('probe_error',{reason:'active lookup bound exceeded'});this.valid=false;return;}active++;this.valid=true;this.key=args[0].toUInt32();this.address=this.context.pc.toString();this.caller=this.returnAddress.toString();},onLeave(retval){if(!this.valid)return;active--;emit('numeric_lookup_result',{thread_id:this.threadId,sequence:++sequence,address:this.address,caller:this.caller,key:this.key,entry:retval.toString()});}});
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
    parser.add_argument("--require-lookup", action="store_true")
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
    state = CaptureState(args.require_lookup)
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
