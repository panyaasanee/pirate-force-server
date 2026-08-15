#!/usr/bin/env python3
"""Read-only Frida probe for the client FACTION relation lookup matrix."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

try:
    from .pf_relation_probe import (
        DEFAULT_CLIENT,
        DEFAULT_CONFIG,
        guard_binary,
        load_config,
        process_image_path,
    )
except ImportError:  # Direct script execution places tools/ on sys.path.
    from pf_relation_probe import (
        DEFAULT_CLIENT,
        DEFAULT_CONFIG,
        guard_binary,
        load_config,
        process_image_path,
    )


LOOKUP_VA = 0x4A1D50
LOOKUP_CODE = "83ec08535556578d71248d44241c508d"
ACCESSOR_VA = 0x40B560
ACCESSOR_CODE = "6aff681e40b80064a10000000050a1bc"


def validate_event(payload: object, maximum: int) -> dict:
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError("invalid matrix probe event")
    event = payload.get("event")
    fields = {
        "probe_ready": {"schema", "event", "timestamp", "module_base"},
        "observed_lookup": {
            "schema", "event", "timestamp", "first", "second", "result_u8",
        },
        "matrix": {
            "schema", "event", "timestamp", "relation_system", "target", "rows",
        },
        "probe_error": {"schema", "event", "timestamp", "reason"},
    }
    if event not in fields or set(payload) != fields[event]:
        raise ValueError("matrix probe event shape mismatch")
    if not isinstance(payload["timestamp"], str) or not payload["timestamp"]:
        raise ValueError("invalid matrix probe timestamp")
    if event == "observed_lookup":
        if any(type(payload[key]) is not int or not 0 <= payload[key] <= 0xFFFFFFFF
               for key in ("first", "second")) or payload["result_u8"] not in (0, 1):
            raise ValueError("invalid observed relation lookup")
    elif event == "matrix":
        rows = payload["rows"]
        if (
            type(payload["target"]) is not int
            or not isinstance(payload["relation_system"], str)
            or not payload["relation_system"].startswith("0x")
            or not isinstance(rows, list)
            or len(rows) != maximum + 1
        ):
            raise ValueError("invalid relation matrix envelope")
        for candidate, row in enumerate(rows):
            if row != {
                "candidate": candidate,
                "candidate_then_target": row.get("candidate_then_target") if isinstance(row, dict) else None,
                "target_then_candidate": row.get("target_then_candidate") if isinstance(row, dict) else None,
            } or row["candidate_then_target"] not in (0, 1) or row["target_then_candidate"] not in (0, 1):
                raise ValueError("invalid relation matrix row")
    elif event == "probe_error" and (
        not isinstance(payload["reason"], str) or not payload["reason"]
    ):
        raise ValueError("invalid matrix probe error")
    return payload


def make_agent_source(config: dict, target: int, maximum: int) -> str:
    compact = json.dumps(config, separators=(",", ":"))
    return f"""
'use strict';
const config = {compact};
const target = {target};
const maximum = {maximum};
function emit(event, fields) {{
  send(Object.assign({{schema: 1, event, timestamp: new Date().toISOString()}}, fields));
}}
function hex(address, count) {{
  const bytes = new Uint8Array(address.readByteArray(count));
  return Array.from(bytes, b => b.toString(16).padStart(2, '0')).join('');
}}
function relocatedAccessorCode(slide) {{
  const bytes = Array.from('{ACCESSOR_CODE}'.match(/../g), pair => parseInt(pair, 16));
  const original = (bytes[3] | (bytes[4] << 8) | (bytes[5] << 16) |
    (bytes[6] << 24)) >>> 0;
  const value = (original + slide) >>> 0;
  bytes[3] = value & 0xff;
  bytes[4] = (value >>> 8) & 0xff;
  bytes[5] = (value >>> 16) & 0xff;
  bytes[6] = (value >>> 24) & 0xff;
  return bytes.map(b => b.toString(16).padStart(2, '0')).join('');
}}
function install() {{
  const module = Process.enumerateModules().find(
    m => m.name.toLowerCase() === config.binary.filename.toLowerCase());
  if (!module || module.size !== config.binary.size_of_image)
    throw new Error('runtime module guard mismatch');
  const lookupAt = module.base.add(0x{LOOKUP_VA - 0x400000:X});
  const accessorAt = module.base.add(0x{ACCESSOR_VA - 0x400000:X});
  const slide = module.base.sub(config.binary.image_base).toUInt32();
  if (hex(lookupAt, {len(bytes.fromhex(LOOKUP_CODE))}) !== '{LOOKUP_CODE}' ||
      hex(accessorAt, {len(bytes.fromhex(ACCESSOR_CODE))}) !== relocatedAccessorCode(slide))
    throw new Error('runtime relation function guard mismatch');

  Interceptor.attach(lookupAt, {{
    onEnter() {{
      this.first = this.context.esp.add(4).readU32();
      this.second = this.context.esp.add(8).readU32();
    }},
    onLeave(retval) {{
      emit('observed_lookup', {{first: this.first, second: this.second,
        result_u8: retval.toUInt32() & 0xff}});
    }}
  }});

  setTimeout(function () {{
    try {{
      const getRelationSystem = new NativeFunction(accessorAt, 'pointer', []);
      const lookup = new NativeFunction(
        lookupAt, 'uint8', ['pointer', 'uint32', 'uint32'], 'thiscall');
      const relationSystem = getRelationSystem();
      if (relationSystem.isNull()) throw new Error('relation singleton is null');
      const rows = [];
      for (let candidate = 0; candidate <= maximum; candidate++) {{
        rows.push({{candidate,
          candidate_then_target: lookup(relationSystem, candidate, target),
          target_then_candidate: lookup(relationSystem, target, candidate)}});
      }}
      emit('matrix', {{relation_system: relationSystem.toString(), target, rows}});
    }} catch (error) {{
      emit('probe_error', {{reason: String(error)}});
    }}
  }}, 1000);
  emit('probe_ready', {{module_base: module.base.toString()}});
}}
try {{ install(); }} catch (error) {{
  emit('probe_error', {{reason: String(error)}});
  throw error;
}}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pid", type=int, required=True)
    parser.add_argument("--client", type=Path, default=DEFAULT_CLIENT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target", type=int, default=6)
    parser.add_argument("--maximum", type=int, default=31)
    parser.add_argument("--duration", type=float, default=5.0)
    args = parser.parse_args()
    if not 0 <= args.target <= args.maximum <= 255:
        raise ValueError("require 0 <= target <= maximum <= 255")

    config = load_config(args.config.resolve())
    client = args.client.resolve(strict=True)
    guard_binary(client, config)
    live_image = process_image_path(args.pid).resolve(strict=True)
    if not live_image.samefile(client):
        raise ValueError("PID executable path differs from guarded client")
    guard_binary(live_image, config)

    import frida

    messages: list[dict] = []
    failures: list[str] = []
    session = frida.attach(args.pid)
    script = session.create_script(make_agent_source(config, args.target, args.maximum))

    def on_message(message, _data):
        if message.get("type") != "send":
            failures.append(message.get("description", "Frida script error"))
            return
        try:
            payload = validate_event(message.get("payload"), args.maximum)
        except ValueError as exc:
            failures.append(str(exc))
            return
        messages.append(payload)
        if payload.get("event") == "probe_error":
            failures.append(str(payload.get("reason")))

    script.on("message", on_message)
    script.load()
    deadline = time.monotonic() + args.duration
    try:
        while time.monotonic() < deadline and not failures:
            if any(item.get("event") == "matrix" for item in messages):
                break
            time.sleep(0.1)
    finally:
        script.unload()
        session.detach()
    if failures:
        raise RuntimeError(failures[0])
    if not any(item.get("event") == "matrix" for item in messages):
        raise RuntimeError("matrix event not received before deadline")
    args.output.write_text(
        "\n".join(json.dumps(item, sort_keys=True, separators=(",", ":"))
                  for item in messages) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
