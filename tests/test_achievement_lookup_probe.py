import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pf_action_data_binding_probe", ROOT / "tools/pf_action_data_binding_probe.py")
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class ActionDataBindingProbeTests(unittest.TestCase):
    def config(self, name="pf_action_data_binding_probe_config.json"):
        return P.load_config(ROOT / "tools" / name)

    def test_exact_profiles_and_disk_guards(self):
        original = self.config()
        local = self.config("pf_action_data_binding_probe_local_config.json")
        self.assertEqual(original["hooks"], local["hooks"])
        P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", original)
        P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", local)
        with self.assertRaises(ValueError):
            P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", original)
        with self.assertRaises(ValueError):
            P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", local)

    def test_hook_is_instruction_aligned_and_has_no_relocations(self):
        hook = P.EXACT_HOOKS["numeric_lookup"]
        code = bytes.fromhex(hook["code"])
        decoded = list(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(code, hook["va"]))
        self.assertEqual(decoded[0].address, hook["va"])
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

    def test_config_rejects_drift(self):
        data = json.loads((ROOT / "tools/pf_action_data_binding_probe_config.json").read_text())
        data["hooks"]["numeric_lookup"]["va"] += 1
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "provenance"):
                P.load_config(path)

    def test_event_schema_and_state(self):
        ready = {"schema": 1, "event": "probe_ready", "timestamp": "t", "address": "0x1000"}
        lookup = {"schema": 1, "event": "numeric_lookup_result", "timestamp": "t", "thread_id": 4, "sequence": 1, "address": "0x702a10", "caller": "0x75082f", "key": 0xEA7D, "entry": "0x1234"}
        state = P.CaptureState(require_lookup=True)
        for event in (ready, lookup):
            state.accept(P.validate_event(event))
        state.ensure_success()
        broken = dict(lookup, entry="0x-no")
        with self.assertRaisesRegex(ValueError, "entry"):
            P.validate_event(broken)

    def test_require_lookup_and_sequence_are_fail_closed(self):
        state = P.CaptureState(require_lookup=True)
        state.accept({"event": "probe_ready"})
        with self.assertRaisesRegex(RuntimeError, "not observed"):
            state.ensure_success()
        state = P.CaptureState()
        state.accept({"event": "probe_ready"})
        state.accept({"event": "numeric_lookup_result", "sequence": 2})
        state.accept({"event": "numeric_lookup_result", "sequence": 2})
        with self.assertRaisesRegex(RuntimeError, "strictly increasing"):
            state.ensure_success()
        late = P.CaptureState()
        late.accept({"event": "probe_ready"})
        late.accept({"event": "probe_error", "reason": "late during cleanup"})
        with self.assertRaisesRegex(RuntimeError, "late during cleanup"):
            late.ensure_success()
        launcher = Path(P.__file__).read_text(encoding="utf-8")
        self.assertIn("_consumer.finalize_capture(state, script, session)", launcher)
        self.assertNotIn("session.detach()", launcher)

    def test_agent_is_observe_only_and_claims_return(self):
        source = P.make_agent_source(self.config("pf_action_data_binding_probe_local_config.json"))
        self.assertIn("onLeave(retval)", source)
        self.assertIn("numeric_lookup_result", source)
        self.assertIn("this.key=args[0].toUInt32()", source)
        self.assertIn("this.caller=this.returnAddress.toString()", source)
        for forbidden in ("Memory.write", "writeU", "writeS", "writePointer", "NativeFunction", "Interceptor.replace", "sendInput"):
            self.assertNotIn(forbidden, source)

    def test_output_is_confined_and_rejects_guard_alias(self):
        client = ROOT.parent / "GameClient/GameClient.local.bin"
        config = ROOT / "tools/pf_action_data_binding_probe_local_config.json"
        safe = P.DEFAULT_CAPTURE_ROOT / "capture.jsonl"
        self.assertEqual(P.validate_output_path(safe, client, config), safe.resolve())
        with self.assertRaises(ValueError):
            P.validate_output_path(ROOT / "outside.jsonl", client, config)
        with self.assertRaises(ValueError):
            P.validate_output_path(config, client, config)


if __name__ == "__main__":
    unittest.main()
