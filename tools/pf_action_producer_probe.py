#!/usr/bin/env python3
"""Observe-only Frida probe for the guarded Pirate Force ActionVital producer."""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys
import time
from typing import Any, BinaryIO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("pf_action_producer_probe_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.bin"
DEFAULT_CAPTURE_ROOT = ROOT.parent / "GameClient" / "capture_action_probe"
POINTER = re.compile(r"^0x[0-9a-f]+$")
EVENT_KINDS = {
    "probe_ready", "candidate_branch", "action_producer", "action_queue", "candidate_queue",
    "probe_error",
}
EXACT_HOOKS = {
    "action_producer": {
        "va": 0x44D260,
        "code": "6aff68377eb80064a1000000005083ec0c53555657a1bcb4020133c4508d4424",
    },
    "candidate_branches": (
        {"va": 0x450D79, "code": "e882a1ffff", "candidate": "branch_ea72_or_ea74", "queue_call": {"va": 0x450E1E, "code": "e8ddc91800"}},
        {"va": 0x450F6E, "code": "e88d9fffff", "candidate": "branch_ea75", "queue_call": {"va": 0x450FE2, "code": "e819c81800"}},
    ),
    "action_queue": {"va": 0x5DD800, "code": "538b5c2408568bf185db747680bed000"},
}


@dataclass(frozen=True)
class PEInfo:
    machine: int
    optional_magic: int
    image_base: int
    size_of_image: int
    sections: tuple[tuple[int, int, int, int], ...]

    def rva_to_offset(self, rva: int) -> int:
        for va, virtual_size, raw_offset, raw_size in self.sections:
            if va <= rva < va + max(virtual_size, raw_size):
                delta = rva - va
                if delta >= raw_size:
                    raise ValueError("hook RVA has no file-backed bytes")
                return raw_offset + delta
        raise ValueError("hook RVA is outside file-backed PE sections")


def _read_exact(stream: BinaryIO, offset: int, size: int) -> bytes:
    stream.seek(offset)
    result = stream.read(size)
    if len(result) != size:
        raise ValueError("truncated PE structure")
    return result


def read_pe(path: Path) -> PEInfo:
    with path.open("rb") as stream:
        if _read_exact(stream, 0, 2) != b"MZ":
            raise ValueError("binary is not an MZ image")
        pe_offset = struct.unpack("<I", _read_exact(stream, 0x3C, 4))[0]
        if _read_exact(stream, pe_offset, 4) != b"PE\0\0":
            raise ValueError("binary has no PE signature")
        coff = _read_exact(stream, pe_offset + 4, 20)
        machine, count = struct.unpack_from("<HH", coff)
        optional_size = struct.unpack_from("<H", coff, 16)[0]
        optional = _read_exact(stream, pe_offset + 24, optional_size)
        if len(optional) < 60:
            raise ValueError("PE optional header is too short")
        sections = []
        section_offset = pe_offset + 24 + optional_size
        for index in range(count):
            section = _read_exact(stream, section_offset + index * 40, 40)
            virtual_size, va, raw_size, raw_offset = struct.unpack_from("<IIII", section, 8)
            sections.append((va, virtual_size, raw_offset, raw_size))
        return PEInfo(
            machine, struct.unpack_from("<H", optional)[0],
            struct.unpack_from("<I", optional, 28)[0],
            struct.unpack_from("<I", optional, 56)[0], tuple(sections),
        )


def _all_hooks(config: dict[str, Any]):
    hooks = config["hooks"]
    candidates = hooks["candidate_branches"]
    return (
        hooks["action_producer"], *candidates,
        *(item["queue_call"] for item in candidates), hooks["action_queue"],
    )


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks"} or data["schema"] != 1:
        raise ValueError("invalid probe config root")
    binary = data["binary"]
    binary_fields = {"filename", "size", "sha256", "machine", "optional_magic", "image_base", "size_of_image"}
    if type(binary) is not dict or set(binary) != binary_fields:
        raise ValueError("invalid binary guard")
    if (
        binary["filename"] != "GameClient.bin"
        or type(binary["sha256"]) is not str
        or not re.fullmatch(r"[0-9A-F]{64}", binary["sha256"])
        or any(type(binary[key]) is not int or binary[key] < 0 for key in binary_fields - {"filename", "sha256"})
        or binary["machine"] != 0x14C or binary["optional_magic"] != 0x10B
    ):
        raise ValueError("invalid binary guard values")
    hooks = data["hooks"]
    if type(hooks) is not dict or set(hooks) != {"action_producer", "candidate_branches", "action_queue"}:
        raise ValueError("invalid hook config")
    if hooks["action_producer"] != EXACT_HOOKS["action_producer"] or hooks["action_queue"] != EXACT_HOOKS["action_queue"]:
        raise ValueError("hook provenance differs from exact addresses")
    if tuple(hooks["candidate_branches"]) != EXACT_HOOKS["candidate_branches"]:
        raise ValueError("candidate provenance differs from exact addresses")
    for hook in _all_hooks(data):
        if type(hook["va"]) is not int or not hook["code"] or len(hook["code"]) % 2:
            raise ValueError("invalid hook address or code")
        bytes.fromhex(hook["code"])
    return data


def validate_runtime_options(pid: int, duration: float) -> None:
    if type(pid) is not int or isinstance(pid, bool) or pid <= 0:
        raise ValueError("PID must be a positive integer")
    if type(duration) not in (int, float) or isinstance(duration, bool) or not math.isfinite(duration) or duration < 0:
        raise ValueError("duration must be finite and nonnegative")


def validate_output_path(
    output: Path, client: Path, config_path: Path,
    capture_root: Path = DEFAULT_CAPTURE_ROOT,
) -> Path:
    if not output.is_absolute():
        raise ValueError("output path must be absolute")
    resolved = output.resolve(strict=False)
    safe_root = capture_root.resolve(strict=False)
    try:
        resolved.relative_to(safe_root)
    except ValueError as exc:
        raise ValueError("output must be inside the action-probe capture directory") from exc
    guarded = (client.resolve(strict=True), config_path.resolve(strict=True), Path(__file__).resolve())
    if resolved in guarded:
        raise ValueError("output aliases a guarded input")
    if resolved.exists() and any(resolved.samefile(path) for path in guarded):
        raise ValueError("output aliases a guarded input")
    if resolved.exists() and resolved.is_dir():
        raise ValueError("output path is a directory")
    return resolved


class CaptureState:
    def __init__(self) -> None:
        self.ready = False
        self.failures: list[str] = []

    def accept(self, event: dict[str, Any]) -> None:
        if event["event"] == "probe_ready":
            self.ready = True
        elif event["event"] == "probe_error":
            self.failures.append(event["reason"])

    def ensure_success(self) -> None:
        if self.failures:
            raise RuntimeError(self.failures[0])
        if not self.ready:
            raise RuntimeError("probe_ready was not observed")


def guard_binary(path: Path, config: dict[str, Any]) -> PEInfo:
    expected = config["binary"]
    if path.name != expected["filename"] or path.stat().st_size != expected["size"]:
        raise ValueError("client filename or size mismatch")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != expected["sha256"]:
        raise ValueError("client SHA-256 mismatch")
    pe = read_pe(path)
    for field in ("machine", "optional_magic", "image_base", "size_of_image"):
        if getattr(pe, field) != expected[field]:
            raise ValueError(f"client PE {field} mismatch")
    for hook in _all_hooks(config):
        signature = bytes.fromhex(hook["code"])
        offset = pe.rva_to_offset(hook["va"] - pe.image_base)
        if raw[offset:offset + len(signature)] != signature:
            raise ValueError(f"client code guard mismatch at VA 0x{hook['va']:X}")
    return pe


def _finite_vector(value: Any, length: int) -> bool:
    return (
        type(value) is list and len(value) == length
        and all(type(item) in (int, float) and not isinstance(item, bool) and math.isfinite(item) for item in value)
    )


def validate_event(payload: Any) -> dict[str, Any]:
    if type(payload) is not dict or payload.get("schema") != 1 or type(payload.get("schema")) is not int:
        raise ValueError("probe event schema is invalid")
    kind = payload.get("event")
    if kind not in EVENT_KINDS:
        raise ValueError("probe event kind is invalid")
    fields = {
        "probe_ready": {"timestamp", "address"},
        "candidate_branch": {"timestamp", "thread_id", "address", "sequence", "candidate"},
        "action_producer": {"timestamp", "thread_id", "address", "sequence", "caller", "controller", "action", "has_position", "position"},
        "action_queue": {"timestamp", "thread_id", "address", "sequence", "caller", "object", "action", "heading", "xyz", "target_kind", "scene", "opaque_target_dwords"},
        "candidate_queue": {"timestamp", "thread_id", "address", "sequence", "candidate", "object", "action", "heading", "xyz", "target_kind", "scene", "opaque_target_dwords"},
        "probe_error": {"timestamp", "reason"},
    }[kind]
    if set(payload) != {"schema", "event"} | fields:
        raise ValueError("probe event fields do not exactly match its kind")
    if type(payload["timestamp"]) is not str or not payload["timestamp"]:
        raise ValueError("invalid timestamp")
    for key in ("thread_id", "sequence", "action", "target_kind", "scene"):
        if key in payload and (type(payload[key]) is not int or payload[key] < 0 or payload[key] > 0xFFFFFFFF):
            raise ValueError(f"invalid {key}")
    for key in ("address", "caller", "controller", "object"):
        if key in payload and (type(payload[key]) is not str or POINTER.fullmatch(payload[key]) is None):
            raise ValueError(f"invalid {key}")
    if "candidate" in payload and payload["candidate"] not in {item["candidate"] for item in EXACT_HOOKS["candidate_branches"]}:
        raise ValueError("invalid candidate")
    if "has_position" in payload and type(payload["has_position"]) is not bool:
        raise ValueError("invalid has_position")
    if "position" in payload:
        if payload["position"] is not None and not _finite_vector(payload["position"], 3):
            raise ValueError("invalid position")
        if payload["has_position"] != (payload["position"] is not None):
            raise ValueError("position presence mismatch")
    if "heading" in payload and (type(payload["heading"]) not in (int, float) or isinstance(payload["heading"], bool) or not math.isfinite(payload["heading"])):
        raise ValueError("invalid heading")
    for key, length in (("xyz", 3), ("opaque_target_dwords", 4)):
        if key in payload and not _finite_vector(payload[key], length):
            raise ValueError(f"invalid {key}")
    if "opaque_target_dwords" in payload and any(type(item) is not int or not 0 <= item <= 0xFFFFFFFF for item in payload["opaque_target_dwords"]):
        raise ValueError("invalid opaque target data")
    if "reason" in payload and (type(payload["reason"]) is not str or not payload["reason"]):
        raise ValueError("invalid reason")
    return payload


def process_image_path(pid: int) -> Path:
    if sys.platform != "win32":
        raise RuntimeError("live probe supports Windows only")
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = (ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong)
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.QueryFullProcessImageNameW.argtypes = (
        ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
        ctypes.POINTER(ctypes.c_ulong),
    )
    kernel32.QueryFullProcessImageNameW.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = (ctypes.c_void_p,)
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x1000, False, pid)
    if not handle:
        raise OSError(ctypes.get_last_error(), "OpenProcess failed")
    try:
        size = ctypes.c_ulong(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            raise OSError(ctypes.get_last_error(), "QueryFullProcessImageNameW failed")
        return Path(buffer.value)
    finally:
        kernel32.CloseHandle(handle)


def make_agent_source(config: dict[str, Any]) -> str:
    compact = json.dumps(config, separators=(",", ":"))
    return f"""
'use strict';
const config = {compact};
let sequence = 0;
const producerStack = new Map();
function now() {{ return new Date().toISOString(); }}
function emit(event, fields) {{ send(Object.assign({{schema:1,event,timestamp:now()}}, fields)); }}
function readable(address, count) {{
  if (address.isNull() || count < 0 || count > 256) return false;
  const range = Process.findRangeByAddress(address);
  return range !== null && range.protection.indexOf('r') >= 0 && address.add(count).compare(range.base.add(range.size)) <= 0;
}}
function codeHex(address, count) {{
  if (!readable(address, count)) throw new Error('unreadable code guard');
  return Array.from(new Uint8Array(address.readByteArray(count)), b => b.toString(16).padStart(2,'0')).join('');
}}
function finite3(pointer) {{
  if (!readable(pointer, 12)) return null;
  const value = [pointer.readFloat(), pointer.add(4).readFloat(), pointer.add(8).readFloat()];
  return value.every(Number.isFinite) ? value : null;
}}
function install() {{
  const module = Process.enumerateModules().find(m => m.name.toLowerCase() === config.binary.filename.toLowerCase());
  if (!module || module.size !== config.binary.size_of_image) throw new Error('runtime module guard mismatch');
  const addressOf = hook => module.base.add(hook.va - config.binary.image_base);
  const hooks = [config.hooks.action_producer, ...config.hooks.candidate_branches, ...config.hooks.candidate_branches.map(h => h.queue_call), config.hooks.action_queue];
  for (const hook of hooks) if (codeHex(addressOf(hook), hook.code.length / 2) !== hook.code)
    throw new Error('runtime code guard mismatch at ' + addressOf(hook));
  function decodeObject(object) {{
    if (!readable(object, 0x4c)) return null;
    const heading = object.add(0x38).readFloat(); const xyz = finite3(object.add(0x3c));
    if (!Number.isFinite(heading) || xyz === null) return null;
    return {{object:object.toString(),action:object.add(0x30).readU32(),heading,xyz,target_kind:object.add(0x48).readU8(),scene:object.add(0x4a).readU16(),opaque_target_dwords:[object.add(0x20).readU32(),object.add(0x24).readU32(),object.add(0x28).readU32(),object.add(0x2c).readU32()]}};
  }}
  for (const hook of config.hooks.candidate_branches) {{
    Interceptor.attach(addressOf(hook), {{onEnter() {{
      emit('candidate_branch', {{thread_id:this.threadId,address:this.context.pc.toString(),sequence:++sequence,candidate:hook.candidate}});
    }}}});
    Interceptor.attach(addressOf(hook.queue_call), {{onEnter() {{
      if (!readable(this.context.esp, Process.pointerSize)) {{ emit('probe_error', {{reason:'unreadable candidate queue stack'}}); return; }}
      const decoded = decodeObject(this.context.esp.readPointer());
      if (decoded === null) {{ emit('probe_error', {{reason:'unreadable or nonfinite candidate ActionVital'}}); return; }}
      emit('candidate_queue', Object.assign({{thread_id:this.threadId,address:this.context.pc.toString(),sequence:++sequence,candidate:hook.candidate}}, decoded));
    }}}});
  }}
  Interceptor.attach(addressOf(config.hooks.action_producer), {{onEnter(args) {{
    const action = args[0].toUInt32(); const pointer = args[1]; const position = pointer.isNull() ? null : finite3(pointer);
    if (!pointer.isNull() && position === null) {{ emit('probe_error', {{reason:'unreadable or nonfinite position'}}); return; }}
    const stack = producerStack.get(this.threadId) || []; stack.push(action); producerStack.set(this.threadId, stack);
    emit('action_producer', {{thread_id:this.threadId,address:this.context.pc.toString(),sequence:++sequence,caller:this.returnAddress.toString(),controller:this.context.ecx.toString(),action,has_position:position!==null,position}});
  }}, onLeave() {{ const stack=producerStack.get(this.threadId)||[]; stack.pop(); if(stack.length===0) producerStack.delete(this.threadId); }} }});
  Interceptor.attach(addressOf(config.hooks.action_queue), {{onEnter(args) {{
    const stack=producerStack.get(this.threadId)||[]; if(stack.length===0) return;
    const decoded=decodeObject(args[0]);
    if(decoded===null || decoded.action!==stack[stack.length-1]) {{ emit('probe_error', {{reason:'generic producer queue correlation failed'}}); return; }}
    emit('action_queue', Object.assign({{thread_id:this.threadId,address:this.context.pc.toString(),sequence:++sequence,caller:this.returnAddress.toString()}}, decoded));
  }}}});
  emit('probe_ready', {{address:module.base.toString()}});
}}
try {{ install(); }} catch (error) {{ emit('probe_error', {{reason:String(error)}}); throw error; }}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=0.0)
    args = parser.parse_args()
    validate_runtime_options(args.pid, args.duration)
    config = load_config(args.config.resolve())
    client = args.client.resolve(strict=True)
    output_path = validate_output_path(args.output, client, args.config)
    guard_binary(client, config)
    live_image = process_image_path(args.pid).resolve(strict=True)
    if not live_image.samefile(client):
        raise ValueError("PID executable path differs from guarded client")
    guard_binary(live_image, config)
    import frida
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8", buffering=1) as output:
        session = frida.attach(args.pid)
        script = session.create_script(make_agent_source(config))
        state = CaptureState()
        def on_message(message, _data):
            try:
                if message.get("type") != "send":
                    raise ValueError(message.get("description", "Frida script error"))
                event = validate_event(message.get("payload"))
                output.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                state.accept(event)
            except Exception as exc: state.failures.append(str(exc))
        script.on("message", on_message); script.load()
        deadline = None if args.duration == 0 else time.monotonic() + args.duration
        try:
            while deadline is None or time.monotonic() < deadline:
                if state.failures: raise RuntimeError(state.failures[0])
                time.sleep(0.1)
        except KeyboardInterrupt: pass
        finally:
            time.sleep(0.05)
            try: state.ensure_success()
            finally: script.unload(); session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
