import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pf_relation_probe", ROOT / "tools" / "pf_relation_probe.py"
)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class RelationProbeTests(unittest.TestCase):
    def config(self):
        return PROBE.load_config(ROOT / "tools/pf_relation_probe_config.json")

    def synthetic_pe(self, root: Path, config: dict) -> Path:
        raw_size = 0x1B0000
        raw = bytearray(0x200 + raw_size)
        raw[:2] = b"MZ"
        struct.pack_into("<I", raw, 0x3C, 0x80)
        raw[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HH", raw, 0x84, 0x14C, 1)
        struct.pack_into("<H", raw, 0x84 + 16, 0xE0)
        optional = 0x98
        struct.pack_into("<H", raw, optional, 0x10B)
        struct.pack_into("<I", raw, optional + 28, 0x400000)
        struct.pack_into("<I", raw, optional + 56, 0x1E0000)
        section = optional + 0xE0
        raw[section:section + 8] = b".text\0\0\0"
        struct.pack_into("<IIII", raw, section + 8, raw_size, 0x30000, raw_size, 0x200)
        hooks = config["hooks"]
        for hook in (
            hooks["start_game_observation"], hooks["relation_entry"],
            *hooks["relation_reads"],
        ):
            signature = bytes.fromhex(hook["code"])
            offset = 0x200 + (hook["va"] - 0x400000 - 0x30000)
            raw[offset:offset + len(signature)] = signature
        path = root / "GameClient.local.bin"
        path.write_bytes(raw)
        binary = config["binary"]
        binary.update({
            "size": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
            "machine": 0x14C,
            "optional_magic": 0x10B,
            "image_base": 0x400000,
            "size_of_image": 0x1E0000,
        })
        return path

    def test_checked_in_config_is_exact_and_agent_is_capture_only(self):
        config = self.config()
        self.assertEqual(config["hooks"]["start_game_observation"]["va"], 0x5DDC57)
        self.assertEqual(config["hooks"]["relation_entry"]["va"], 0x43C380)
        self.assertEqual(
            [item["va"] for item in config["hooks"]["relation_reads"]],
            [0x43C5CD, 0x43C5D4],
        )
        source = PROBE.make_agent_source(config)
        self.assertNotIn("Memory.write", source)
        self.assertNotIn("NativeFunction", source)
        self.assertEqual(source.count("Interceptor.attach"), 3)

    def test_binary_guard_accepts_exact_pe_and_refuses_mismatch(self):
        with tempfile.TemporaryDirectory() as raw_root:
            config = copy.deepcopy(self.config())
            path = self.synthetic_pe(Path(raw_root), config)
            pe = PROBE.guard_binary(path, config)
            self.assertEqual((pe.machine, pe.optional_magic), (0x14C, 0x10B))
            changed = bytearray(path.read_bytes())
            changed[-1] ^= 1
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                PROBE.guard_binary(path, config)

    def test_config_and_event_schema_are_strict(self):
        config = copy.deepcopy(self.config())
        config["hooks"]["relation_reads"][0]["offset"] = 0x6C
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "bad.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaises(ValueError):
                PROBE.load_config(path)
        event = {
            "schema": 1, "event": "relation_basic_attr_read",
            "timestamp": "2026-08-15T00:00:00.000Z", "thread_id": 7,
            "address": "0x43c5cd", "sequence": 1, "operand": "first",
            "basic_attr": "0x1000", "field_address": "0x1068", "raw_u32": 6,
        }
        self.assertIs(PROBE.validate_event(event), event)
        bad = dict(event, semantic="enemy")
        with self.assertRaises(ValueError):
            PROBE.validate_event(bad)
        schema_bool = dict(event, schema=True)
        with self.assertRaises(ValueError):
            PROBE.validate_event(schema_bool)
        cross_kind = {
            "schema": 1, "event": "probe_ready",
            "timestamp": "2026-08-15T00:00:00.000Z",
            "address": "0x400000", "raw_u32": 6,
        }
        with self.assertRaises(ValueError):
            PROBE.validate_event(cross_kind)


if __name__ == "__main__":
    unittest.main()
