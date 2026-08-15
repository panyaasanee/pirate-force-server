import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "pf_action_producer_probe", ROOT / "tools" / "pf_action_producer_probe.py"
)
PROBE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = PROBE
SPEC.loader.exec_module(PROBE)


class ActionProducerProbeTests(unittest.TestCase):
    def config(self):
        return PROBE.load_config(ROOT / "tools/pf_action_producer_probe_config.json")

    def synthetic_pe(self, root: Path, config: dict) -> Path:
        raw_size = 0x220000
        raw = bytearray(0x200 + raw_size)
        raw[:2] = b"MZ"
        struct.pack_into("<I", raw, 0x3C, 0x80)
        raw[0x80:0x84] = b"PE\0\0"
        struct.pack_into("<HH", raw, 0x84, 0x14C, 1)
        struct.pack_into("<H", raw, 0x84 + 16, 0xE0)
        optional = 0x98
        struct.pack_into("<H", raw, optional, 0x10B)
        struct.pack_into("<I", raw, optional + 28, 0x400000)
        struct.pack_into("<I", raw, optional + 56, 0x700000)
        section = optional + 0xE0
        raw[section:section + 8] = b".text\0\0\0"
        struct.pack_into("<IIII", raw, section + 8, raw_size, 0x40000, raw_size, 0x200)
        for hook in PROBE._all_hooks(config):
            signature = bytes.fromhex(hook["code"])
            offset = 0x200 + hook["va"] - 0x440000
            raw[offset:offset + len(signature)] = signature
        path = root / "GameClient.bin"
        path.write_bytes(raw)
        config["binary"].update({
            "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest().upper(),
            "size_of_image": 0x700000,
        })
        return path

    def test_checked_in_provenance_and_observe_only_agent(self):
        config = self.config()
        self.assertEqual(config["binary"]["filename"], "GameClient.bin")
        self.assertEqual(config["hooks"]["action_producer"]["va"], 0x44D260)
        self.assertEqual(
            [(item["candidate"], item["va"], item["queue_call"]["va"]) for item in config["hooks"]["candidate_branches"]],
            [
                ("branch_ea72_or_ea74", 0x450D79, 0x450E1E),
                ("branch_ea75", 0x450F6E, 0x450FE2),
            ],
        )
        self.assertEqual(config["hooks"]["action_queue"]["va"], 0x5DD800)
        source = PROBE.make_agent_source(config)
        self.assertNotIn("Memory.write", source)
        self.assertNotIn("writeU", source)
        self.assertNotIn("writeFloat", source)
        self.assertNotIn("NativeFunction", source)
        self.assertNotIn("Interceptor.replace", source)
        self.assertEqual(source.count("Interceptor.attach"), 4)
        self.assertIn("count > 256", source)
        self.assertIn("Number.isFinite", source)
        self.assertIn("producerStack.get(this.threadId)", source)
        self.assertNotIn("observedActions", source)
        self.assertIn("this.context.esp.readPointer()", source)

    def test_binary_guard_accepts_exact_synthetic_pe_and_rejects_changes(self):
        with tempfile.TemporaryDirectory() as raw_root:
            config = copy.deepcopy(self.config())
            path = self.synthetic_pe(Path(raw_root), config)
            PROBE.guard_binary(path, config)
            changed = bytearray(path.read_bytes())
            changed[-1] ^= 1
            path.write_bytes(changed)
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                PROBE.guard_binary(path, config)

    def test_config_rejects_unknown_or_changed_provenance(self):
        config = copy.deepcopy(self.config())
        config["hooks"]["candidate_branches"][0]["candidate"] = "hotkey5"
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "bad.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "candidate provenance"):
                PROBE.load_config(path)
        config = copy.deepcopy(self.config())
        config["unknown"] = True
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "bad.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "config root"):
                PROBE.load_config(path)

    def test_runtime_options_and_output_path_are_strict(self):
        for pid, duration in ((0, 0.0), (-1, 1.0), (1, -1.0), (1, math.inf), (1, math.nan)):
            with self.assertRaises(ValueError):
                PROBE.validate_runtime_options(pid, duration)
        PROBE.validate_runtime_options(1, 0.0)
        config_path = ROOT / "tools/pf_action_producer_probe_config.json"
        client = ROOT.parent / "GameClient/GameClient.bin"
        with tempfile.TemporaryDirectory() as raw_root:
            safe_root = Path(raw_root).resolve()
            good = (safe_root / "run/events.jsonl").resolve()
            self.assertEqual(PROBE.validate_output_path(good, client, config_path, safe_root), good)
            with self.assertRaisesRegex(ValueError, "absolute"):
                PROBE.validate_output_path(Path("events.jsonl"), client, config_path, safe_root)
            with self.assertRaisesRegex(ValueError, "capture directory"):
                PROBE.validate_output_path((safe_root.parent / "escape.jsonl").resolve(), client, config_path, safe_root)
        with self.assertRaisesRegex(ValueError, "aliases"):
            PROBE.validate_output_path(client.resolve(), client, config_path, client.parent.resolve())
        with self.assertRaisesRegex(ValueError, "aliases"):
            PROBE.validate_output_path(config_path.resolve(), client, config_path, config_path.parent.resolve())

    def test_capture_state_requires_ready_and_propagates_late_error(self):
        state = PROBE.CaptureState()
        with self.assertRaisesRegex(RuntimeError, "probe_ready"):
            state.ensure_success()
        state.accept({"event": "probe_ready"})
        state.ensure_success()
        state.accept({"event": "probe_error", "reason": "late guard failure"})
        with self.assertRaisesRegex(RuntimeError, "late guard failure"):
            state.ensure_success()

    def test_malformed_pe_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw_root:
            path = Path(raw_root) / "GameClient.bin"
            path.write_bytes(b"not-a-pe")
            with self.assertRaisesRegex(ValueError, "MZ|truncated"):
                PROBE.read_pe(path)

    def test_event_schema_is_exact_and_rejects_nonfinite_or_bad_bounds(self):
        producer = {
            "schema": 1, "event": "action_producer", "timestamp": "2026-08-15T00:00:00Z",
            "thread_id": 1, "address": "0x44d260", "sequence": 2,
            "caller": "0x450ea6", "controller": "0x1032ec4", "action": 0xEA80,
            "has_position": False, "position": None,
        }
        self.assertIs(PROBE.validate_event(producer), producer)
        with self.assertRaisesRegex(ValueError, "position presence"):
            PROBE.validate_event(dict(producer, has_position=True))
        queued = {
            "schema": 1, "event": "action_queue", "timestamp": "2026-08-15T00:00:01Z",
            "thread_id": 1, "address": "0x5dd800", "sequence": 3,
            "caller": "0x44d42c", "object": "0x12340000", "action": 0xEA80,
            "heading": 0.0, "xyz": [1.0, 2.0, 3.0], "target_kind": 0,
            "scene": 1, "opaque_target_dwords": [0, 0, 0, 0x2001],
        }
        self.assertIs(PROBE.validate_event(queued), queued)
        candidate = dict(queued)
        candidate.pop("caller")
        candidate.update(event="candidate_queue", candidate="branch_ea75")
        self.assertIs(PROBE.validate_event(candidate), candidate)
        with self.assertRaisesRegex(ValueError, "heading"):
            PROBE.validate_event(dict(queued, heading=math.nan))
        with self.assertRaisesRegex(ValueError, "opaque target"):
            PROBE.validate_event(dict(queued, opaque_target_dwords=[0, 0, 0, 0x100000000]))
        with self.assertRaisesRegex(ValueError, "fields"):
            PROBE.validate_event(dict(queued, semantic="attack"))


if __name__ == "__main__":
    unittest.main()
