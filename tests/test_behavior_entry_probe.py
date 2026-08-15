import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pf_behavior_entry_probe", ROOT / "tools/pf_behavior_entry_probe.py")
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class BehaviorEntryProbeTests(unittest.TestCase):
    def config(self, name="pf_behavior_entry_probe_config.json"):
        return P.load_config(ROOT / "tools" / name)

    def event(self, **changes):
        event = {
            "schema": 1, "event": "behavior_entry_result", "timestamp": "t",
            "thread_id": 4, "sequence": 1, "address": "0x702a10",
            "caller": "0x75082f", "manager": "0x18edad8", "key": 7101, "entry": "0x123400",
            "n_id": 7101, "n_amount_target": 1, "n_range": 0,
            "n_damage_area": 0, "n_profit": 0, "n_thendo": 0, "n_class": 0,
            "hit_vector_object": "0x1234e4", "hit_vector_begin": "0x200000",
            "hit_vector_end": "0x200038", "hit_vector_count": 1,
        }
        event.update(changes)
        return event

    def test_exact_profiles_disk_guards_and_hook_provenance(self):
        original = self.config()
        local = self.config("pf_behavior_entry_probe_local_config.json")
        self.assertEqual(original["hooks"], local["hooks"])
        self.assertEqual(original["limits"], local["limits"])
        P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", original)
        P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", local)
        with self.assertRaises(ValueError):
            P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", original)
        with self.assertRaises(ValueError):
            P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", local)
        hook = P.EXACT_HOOKS["numeric_lookup"]
        code = bytes.fromhex(hook["code"])
        decoded = list(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(code, hook["va"]))
        self.assertEqual(sum(item.size for item in decoded), len(code))
        self.assertEqual(decoded[-1].mnemonic, "ret")
        for filename in ("GameClient.bin", "GameClient.local.bin"):
            pe = pefile.PE(str(ROOT.parent / "GameClient" / filename), fast_load=False)
            relocated = {
                pe.OPTIONAL_HEADER.ImageBase + entry.rva
                for block in getattr(pe, "DIRECTORY_ENTRY_BASERELOC", [])
                for entry in block.entries
                if entry.type == pefile.RELOCATION_TYPE["IMAGE_REL_BASED_HIGHLOW"]
            }
            self.assertFalse(relocated.intersection(range(hook["va"], hook["va"] + len(code))))

    def test_config_rejects_malformed_and_drift(self):
        data = json.loads((ROOT / "tools/pf_behavior_entry_probe_config.json").read_text())
        for mutate in (
            lambda d: d["limits"].__setitem__("record_stride", 32),
            lambda d: d["hooks"]["numeric_lookup"].__setitem__("va", 1),
            lambda d: d.__setitem__("extra", 1),
        ):
            changed = json.loads(json.dumps(data))
            mutate(changed)
            with tempfile.TemporaryDirectory() as td:
                path = Path(td) / "bad.json"
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    P.load_config(path)

    def test_exact_event_schema_and_field_bounds(self):
        self.assertEqual(P.validate_event(self.event())["event"], "behavior_entry_result")
        for broken in (
            self.event(n_id=7102), self.event(hit_vector_count=33),
            self.event(sequence=0), self.event(n_range=-1),
            self.event(entry="0x-no"), self.event(extra=1),
            self.event(entry="0x123401"), self.event(hit_vector_object="0x1234e8"),
            self.event(hit_vector_begin="0x0"), self.event(hit_vector_end="0x200070"),
            self.event(hit_vector_count=0),
        ):
            with self.assertRaises(ValueError):
                P.validate_event(broken)

    def test_require_entry_sequence_and_late_failure(self):
        state = P.CaptureState(require_entry=True)
        state.accept({"event": "probe_ready", "address": "0xcc0000"})
        with self.assertRaisesRegex(RuntimeError, "not observed"):
            state.ensure_success()
        state.accept(P.validate_event(self.event(sequence=2)))
        state.ensure_success()
        state.accept(P.validate_event(self.event(sequence=2)))
        with self.assertRaisesRegex(RuntimeError, "strictly increasing"):
            state.ensure_success()
        late = P.CaptureState()
        late.accept({"event": "probe_ready", "address": "0xcc0000"})
        late.accept({"event": "probe_error", "reason": "late"})
        with self.assertRaisesRegex(RuntimeError, "late"):
            late.ensure_success()
        wrong_manager = P.CaptureState(require_entry=True)
        wrong_manager.accept({"event": "probe_ready", "address": "0xcc0000"})
        wrong_manager.accept(P.validate_event(self.event(manager="0x10cdae0")))
        with self.assertRaisesRegex(RuntimeError, "manager"):
            wrong_manager.ensure_success()
        early = P.CaptureState(require_entry=True)
        early.accept(P.validate_event(self.event()))
        with self.assertRaisesRegex(RuntimeError, "before probe_ready"):
            early.ensure_success()

    def test_source_is_observe_only_bounded_and_named_only(self):
        source = P.make_agent_source(self.config("pf_behavior_entry_probe_local_config.json"))
        for required in (
            "onLeave(retval)", "n_amount_target", "n_range", "n_damage_area",
            "n_profit", "n_thendo", "n_class", "retval.add(0xe4)",
            "retval.add(0xf0).readPointer()", "retval.add(0xf4).readPointer()",
            "record_stride", "max_vector_records", "lookup key and n_ID differ",
            "this.context.ecx.equals(behaviorManager)", "manager:this.manager",
        ):
            self.assertIn(required, source)
        for forbidden in (
            "Memory.write", "writeU", "writeS", "writePointer", "NativeFunction",
            "Interceptor.replace", "sendInput", "readUtf", "readCString",
        ):
            self.assertNotIn(forbidden, source)
        launcher = Path(P.__file__).read_text(encoding="utf-8")
        self.assertIn("_consumer.finalize_capture(state, script, session)", launcher)
        self.assertNotIn("session.detach()", launcher)

    def test_output_is_confined_and_guarded(self):
        client = ROOT.parent / "GameClient/GameClient.local.bin"
        config = ROOT / "tools/pf_behavior_entry_probe_local_config.json"
        safe = P.DEFAULT_CAPTURE_ROOT / "capture.jsonl"
        self.assertEqual(P.DEFAULT_CAPTURE_ROOT.name, "capture_behavior_entry")
        self.assertEqual(P.validate_output_path(safe, client, config), safe.resolve())
        with self.assertRaises(ValueError):
            P.validate_output_path(ROOT / "outside.jsonl", client, config)
        with self.assertRaises(ValueError):
            P.validate_output_path(config, client, config)


if __name__ == "__main__":
    unittest.main()
