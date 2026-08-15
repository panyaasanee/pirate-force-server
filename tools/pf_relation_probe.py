#!/usr/bin/env python3
"""Capture-only Frida probe for proven Pirate Force relation-comparator reads."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import ctypes
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
from typing import Any, BinaryIO


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = Path(__file__).with_name("pf_relation_probe_config.json")
DEFAULT_CLIENT = ROOT.parent / "GameClient" / "GameClient.local.bin"
EVENT_KINDS = {
    "probe_ready", "start_game_observation", "relation_entry",
    "relation_basic_attr_read", "probe_error",
}
EXACT_HOOKS = {
    "start_game_observation": {
        "va": 0x5DDC57, "code": "e8343d0000", "runtime_relocations": [],
    },
    "relation_entry": {
        "va": 0x43C380, "code": "6aff68186db800",
        "runtime_relocations": [{"offset": 3, "size": 4}],
    },
}
EXACT_READS = (
    {"va": 0x43C5CD, "code": "8b4068", "runtime_relocations": [], "register": "eax", "offset": 0x68, "operand": "first"},
    {"va": 0x43C5D4, "code": "8b4968", "runtime_relocations": [], "register": "ecx", "offset": 0x68, "operand": "second"},
)


@dataclass(frozen=True)
class PEInfo:
    machine: int
    optional_magic: int
    image_base: int
    size_of_image: int
    sections: tuple[tuple[int, int, int, int], ...]

    def rva_to_offset(self, rva: int) -> int:
        for virtual_address, virtual_size, raw_offset, raw_size in self.sections:
            if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
                delta = rva - virtual_address
                if delta >= raw_size:
                    raise ValueError("hook RVA has no file-backed bytes")
                return raw_offset + delta
        raise ValueError("hook RVA is outside file-backed PE sections")


def _read_exact(stream: BinaryIO, offset: int, size: int) -> bytes:
    stream.seek(offset)
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("truncated PE structure")
    return data


def read_pe(path: Path) -> PEInfo:
    with path.open("rb") as stream:
        if _read_exact(stream, 0, 2) != b"MZ":
            raise ValueError("binary is not an MZ image")
        pe_offset = struct.unpack("<I", _read_exact(stream, 0x3C, 4))[0]
        if _read_exact(stream, pe_offset, 4) != b"PE\0\0":
            raise ValueError("binary has no PE signature")
        coff = _read_exact(stream, pe_offset + 4, 20)
        machine, section_count = struct.unpack_from("<HH", coff)
        optional_size = struct.unpack_from("<H", coff, 16)[0]
        optional = _read_exact(stream, pe_offset + 24, optional_size)
        if len(optional) < 60:
            raise ValueError("PE optional header is too short")
        optional_magic = struct.unpack_from("<H", optional)[0]
        image_base = struct.unpack_from("<I", optional, 28)[0]
        size_of_image = struct.unpack_from("<I", optional, 56)[0]
        sections = []
        section_offset = pe_offset + 24 + optional_size
        for index in range(section_count):
            section = _read_exact(stream, section_offset + index * 40, 40)
            virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
                "<IIII", section, 8
            )
            sections.append((virtual_address, virtual_size, raw_offset, raw_size))
    return PEInfo(machine, optional_magic, image_base, size_of_image, tuple(sections))


def load_config(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if type(data) is not dict or set(data) != {"schema", "binary", "hooks"}:
        raise ValueError("probe config root is incomplete or has unknown fields")
    if data["schema"] != 1 or type(data["schema"]) is not int:
        raise ValueError("unsupported probe config schema")
    binary = data["binary"]
    expected_binary = {
        "filename", "size", "sha256", "machine", "optional_magic",
        "image_base", "size_of_image",
    }
    if type(binary) is not dict or set(binary) != expected_binary:
        raise ValueError("probe binary guard is incomplete or has unknown fields")
    if (
        type(binary["filename"]) is not str
        or type(binary["sha256"]) is not str
        or len(binary["sha256"]) != 64
        or binary["sha256"] != binary["sha256"].upper()
        or any(type(binary[key]) is not int or binary[key] < 0 for key in (
            "size", "machine", "optional_magic", "image_base", "size_of_image"
        ))
        or binary["machine"] != 0x14C
        or binary["optional_magic"] != 0x10B
    ):
        raise ValueError("probe binary guard values are invalid")
    hooks = data["hooks"]
    if type(hooks) is not dict or set(hooks) != {
        "start_game_observation", "relation_entry", "relation_reads"
    }:
        raise ValueError("probe hook config is incomplete or has unknown fields")
    singleton_fields = {"va", "code", "runtime_relocations"}
    for key in ("start_game_observation", "relation_entry"):
        hook = hooks[key]
        if type(hook) is not dict or set(hook) != singleton_fields:
            raise ValueError(f"invalid {key} hook")
    reads = hooks["relation_reads"]
    if type(reads) is not list or len(reads) != 2:
        raise ValueError("exactly two relation reads are required")
    for read in reads:
        if type(read) is not dict or set(read) != {
            "va", "code", "runtime_relocations", "register", "offset", "operand"
        }:
            raise ValueError("invalid relation-read hook")
    if any(hooks[key] != value for key, value in EXACT_HOOKS.items()):
        raise ValueError("hook provenance differs from the exact guarded addresses")
    if tuple(reads) != EXACT_READS:
        raise ValueError("relation-read provenance differs from the exact proven pair")
    for hook in (hooks["start_game_observation"], hooks["relation_entry"], *reads):
        if (
            type(hook["va"]) is not int
            or type(hook["code"]) is not str
            or not hook["code"]
            or len(hook["code"]) % 2
        ):
            raise ValueError("invalid hook VA or code guard")
        bytes.fromhex(hook["code"])
    return data


def relocated_runtime_code(hook: dict[str, Any], runtime_base: int, image_base: int) -> bytes:
    """Apply only explicitly allowlisted PE base relocations to disk code bytes."""
    code = bytearray.fromhex(hook["code"])
    slide = (runtime_base - image_base) & 0xFFFFFFFF
    for relocation in hook["runtime_relocations"]:
        if relocation != {"offset": 3, "size": 4}:
            raise ValueError("unsupported runtime relocation descriptor")
        offset = relocation["offset"]
        if offset + 4 > len(code):
            raise ValueError("runtime relocation exceeds code guard")
        original = struct.unpack_from("<I", code, offset)[0]
        struct.pack_into("<I", code, offset, (original + slide) & 0xFFFFFFFF)
    return bytes(code)


def guard_binary(path: Path, config: dict[str, Any]) -> PEInfo:
    expected = config["binary"]
    stat = path.stat()
    if path.name != expected["filename"]:
        raise ValueError("client filename mismatch")
    if stat.st_size != expected["size"]:
        raise ValueError("client size mismatch")
    digest = hashlib.sha256(path.read_bytes()).hexdigest().upper()
    if digest != expected["sha256"]:
        raise ValueError("client SHA-256 mismatch")
    pe = read_pe(path)
    for field in ("machine", "optional_magic", "image_base", "size_of_image"):
        if getattr(pe, field) != expected[field]:
            raise ValueError(f"client PE {field} mismatch")
    raw = path.read_bytes()
    hooks = config["hooks"]
    for hook in (
        hooks["start_game_observation"], hooks["relation_entry"],
        *hooks["relation_reads"],
    ):
        signature = bytes.fromhex(hook["code"])
        offset = pe.rva_to_offset(hook["va"] - pe.image_base)
        if raw[offset:offset + len(signature)] != signature:
            raise ValueError(f"client code guard mismatch at VA 0x{hook['va']:X}")
    return pe


def validate_event(payload: Any) -> dict[str, Any]:
    if type(payload) is not dict:
        raise ValueError("probe event has invalid shape")
    if (
        type(payload.get("schema")) is not int
        or payload.get("schema") != 1
        or payload.get("event") not in EVENT_KINDS
    ):
        raise ValueError("probe event schema or kind is invalid")
    event_fields = {
        "probe_ready": {"timestamp", "address"},
        "start_game_observation": {"timestamp", "thread_id", "address"},
        "relation_entry": {
            "timestamp", "thread_id", "address", "sequence",
            "this_object", "argument_object",
        },
        "relation_basic_attr_read": {
            "timestamp", "thread_id", "address", "sequence", "operand",
            "basic_attr", "field_address", "raw_u32",
        },
        "probe_error": {"timestamp", "reason"},
    }[payload["event"]]
    if set(payload) != {"schema", "event"} | event_fields:
        raise ValueError("probe event fields do not exactly match its kind")
    if payload.get("operand") not in (None, "first", "second"):
        raise ValueError("probe event operand is invalid")
    if type(payload["timestamp"]) is not str or not payload["timestamp"]:
        raise ValueError("probe event timestamp is invalid")
    for key in ("thread_id", "sequence"):
        if key in payload and (type(payload[key]) is not int or payload[key] < 0):
            raise ValueError(f"probe event {key} is invalid")
    for key in ("address", "this_object", "argument_object", "basic_attr", "field_address"):
        if key in payload and payload[key] is not None and type(payload[key]) is not str:
            raise ValueError(f"probe event {key} is invalid")
    if "raw_u32" in payload and (
        type(payload["raw_u32"]) is not int or not 0 <= payload["raw_u32"] <= 0xFFFFFFFF
    ):
        raise ValueError("probe event raw_u32 is invalid")
    if "reason" in payload and (type(payload["reason"]) is not str or not payload["reason"]):
        raise ValueError("probe event reason is invalid")
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
function now() {{ return new Date().toISOString(); }}
function emit(event, fields) {{ send(Object.assign({{schema: 1, event, timestamp: now()}}, fields)); }}
function hex(address, count) {{
  const bytes = new Uint8Array(address.readByteArray(count));
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}}
function readable(address, count) {{
  if (address.isNull()) return false;
  const range = Process.findRangeByAddress(address);
  if (range === null || range.protection.indexOf('r') < 0) return false;
  return address.compare(range.base) >= 0 && address.add(count).compare(range.base.add(range.size)) <= 0;
}}
function safePointer(address) {{ return readable(address, Process.pointerSize) ? address.readPointer().toString() : null; }}
function runtimeCode(hook, slide) {{
  const bytes = Array.from(hook.code.match(/../g), pair => parseInt(pair, 16));
  for (const relocation of hook.runtime_relocations) {{
    if (relocation.offset !== 3 || relocation.size !== 4 || relocation.offset + 4 > bytes.length)
      throw new Error('unsupported runtime relocation descriptor');
    const i = relocation.offset;
    const original = (bytes[i] | (bytes[i + 1] << 8) | (bytes[i + 2] << 16) | (bytes[i + 3] << 24)) >>> 0;
    const value = (original + slide) >>> 0;
    bytes[i] = value & 0xff; bytes[i + 1] = (value >>> 8) & 0xff;
    bytes[i + 2] = (value >>> 16) & 0xff; bytes[i + 3] = (value >>> 24) & 0xff;
  }}
  return bytes.map(b => b.toString(16).padStart(2, '0')).join('');
}}
function install() {{
  const wanted = config.binary.filename.toLowerCase();
  const module = Process.enumerateModules().find(m => m.name.toLowerCase() === wanted);
  if (!module || module.size !== config.binary.size_of_image) throw new Error('runtime module guard mismatch');
  const base = module.base;
  const slide = base.sub(config.binary.image_base).toUInt32();
  function addressOf(hook) {{ return base.add(hook.va - config.binary.image_base); }}
  for (const hook of [config.hooks.start_game_observation, config.hooks.relation_entry, ...config.hooks.relation_reads]) {{
    const at = addressOf(hook);
    if (hex(at, hook.code.length / 2) !== runtimeCode(hook, slide)) throw new Error('runtime code guard mismatch at ' + at);
  }}
  const relationSequence = new Map();
  Interceptor.attach(addressOf(config.hooks.start_game_observation), {{
    onEnter() {{ emit('start_game_observation', {{thread_id: this.threadId, address: this.context.pc.toString()}}); }}
  }});
  Interceptor.attach(addressOf(config.hooks.relation_entry), {{
    onEnter() {{
      const current = ++sequence;
      relationSequence.set(this.threadId, current);
      emit('relation_entry', {{
        thread_id: this.threadId, address: this.context.pc.toString(), sequence: current,
        this_object: this.context.ecx.toString(), argument_object: safePointer(this.context.esp.add(4))
      }});
    }},
    onLeave() {{ relationSequence.delete(this.threadId); }}
  }});
  for (const hook of config.hooks.relation_reads) {{
    Interceptor.attach(addressOf(hook), {{
      onEnter() {{
        const baseAttr = this.context[hook.register];
        const field = baseAttr.add(hook.offset);
        if (!readable(field, 4)) {{
          emit('probe_error', {{timestamp: now(), reason: 'unreadable relation operand ' + hook.operand}});
          return;
        }}
        emit('relation_basic_attr_read', {{
          thread_id: this.threadId, address: this.context.pc.toString(),
          sequence: relationSequence.get(this.threadId) || 0, operand: hook.operand,
          basic_attr: baseAttr.toString(), field_address: field.toString(),
          raw_u32: field.readU32()
        }});
      }}
    }});
  }}
  emit('probe_ready', {{address: base.toString()}});
}}
try {{ install(); }} catch (error) {{ emit('probe_error', {{reason: String(error)}}); throw error; }}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=0.0,
                        help="seconds to capture; zero waits until Ctrl+C")
    args = parser.parse_args()
    config = load_config(args.config.resolve())
    client = args.client.resolve(strict=True)
    guard_binary(client, config)
    live_image = process_image_path(args.pid).resolve(strict=True)
    if not live_image.samefile(client):
        raise ValueError("PID executable path differs from guarded client")
    guard_binary(live_image, config)

    import frida  # imported only after every on-disk guard passes

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("a", encoding="utf-8", buffering=1) as output:
        session = frida.attach(args.pid)
        script = session.create_script(make_agent_source(config))
        failed = []

        def on_message(message, _data):
            try:
                if message.get("type") != "send":
                    raise ValueError(message.get("description", "Frida script error"))
                event = validate_event(message.get("payload"))
                output.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
                output.flush()
                if event["event"] == "probe_error":
                    failed.append(event["reason"])
            except Exception as exc:
                failed.append(str(exc))

        script.on("message", on_message)
        script.load()
        deadline = None if args.duration == 0 else time.monotonic() + args.duration
        try:
            while deadline is None or time.monotonic() < deadline:
                if failed:
                    raise RuntimeError(failed[0])
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            script.unload()
            session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
