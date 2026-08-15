import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import capstone
import pefile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pf_behavior_range_gate_probe", ROOT / "tools/pf_behavior_range_gate_probe.py")
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


class BehaviorRangeGateProbeTests(unittest.TestCase):
    def config(self, name="pf_behavior_range_gate_probe_config.json"):
        return P.load_config(ROOT / "tools" / name)

    def event(self, kind, sequence, **fields):
        base = {"schema": 1, "event": kind, "timestamp": "t"}
        common = {"thread_id": 7, "sequence": sequence, "invocation": 1}
        shapes = {
            "gate_enter": {**common, "address": "0xd358d0", "caller": "0xd0eb22", "action": 0xEA7D},
            "range_enter": {**common, "address": "0x1015540", "source_key": 123, "mode": 0},
            "range_empty": {**common, "address": "0x1015558"},
            "range_selected": {**common, "address": "0x1015604", "entry": "0x220000", "n_id": 278, "n_range": 75},
            "range_complete": {**common, "address": "0x101562c", "raw_selected": 75},
            "gate_result": {**common, "address": "0xd0eb22", "result_bool": 1, "range_count": 1},
        }
        base.update(shapes[kind]); base.update(fields); return base

    def test_profiles_guards_instructions_and_relocations(self):
        original = self.config(); local = self.config("pf_behavior_range_gate_probe_local_config.json")
        self.assertEqual(original["hooks"], local["hooks"])
        P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", original)
        P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", local)
        with self.assertRaises(ValueError): P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", original)
        with self.assertRaises(ValueError): P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", local)
        for filename in ("GameClient.bin", "GameClient.local.bin"):
            pe = pefile.PE(str(ROOT.parent / "GameClient" / filename), fast_load=False)
            relocated = {pe.OPTIONAL_HEADER.ImageBase + e.rva for b in getattr(pe, "DIRECTORY_ENTRY_BASERELOC", []) for e in b.entries if e.type == pefile.RELOCATION_TYPE["IMAGE_REL_BASED_HIGHLOW"]}
            for hook in original["hooks"].values():
                code = bytes.fromhex(hook["code"])
                decoded = list(capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(code, hook["va"]))
                self.assertEqual(sum(i.size for i in decoded), len(code))
                overlap = relocated.intersection(range(hook["va"], hook["va"] + len(code)))
                declared = {hook["va"] + r["offset"] for r in hook["runtime_relocations"]}
                self.assertEqual(overlap, declared)
        source = P.make_agent_source(local)
        self.assertIn("staticValue+slide", source)
        self.assertIn("bytes=h.code.match", source)
        self.assertIn("unsupported runtime relocation", source)

    def test_config_rejects_drift(self):
        data = json.loads((ROOT / "tools/pf_behavior_range_gate_probe_config.json").read_text())
        data["limits"]["timeout_ms"] += 1
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"; path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "provenance"): P.load_config(path)

    def test_exact_schema_and_bounds(self):
        for seq, kind in enumerate(("gate_enter", "range_enter", "range_empty", "range_selected", "range_complete", "gate_result"), 1):
            P.validate_event(self.event(kind, seq))
        for broken in (
            self.event("gate_enter", 1, action=0xEA7E), self.event("gate_result", 2, result_bool=2),
            self.event("range_selected", 2, n_range=0x80000000), self.event("range_complete", 2, raw_selected=-0x80000001),
            self.event("range_selected", 2, entry="0x-no"), self.event("range_empty", 2, extra=1),
        ):
            with self.assertRaises(ValueError): P.validate_event(broken)

    def test_full_order_empty_and_fail_closed_paths(self):
        state = P.CaptureState(require_gate=True, require_complete=True)
        state.accept({"event": "probe_ready", "address": "0xcc0000"})
        for event in (self.event("gate_enter", 1), self.event("range_enter", 2), self.event("range_selected", 3), self.event("range_complete", 4), self.event("gate_result", 5)):
            state.accept(P.validate_event(event))
        state.ensure_success()
        empty = P.CaptureState(require_gate=True)
        empty.accept({"event": "probe_ready", "address": "0xcc0000"})
        for event in (self.event("gate_enter", 1), self.event("range_enter", 2), self.event("range_empty", 3), self.event("gate_result", 4, range_count=0)):
            empty.accept(P.validate_event(event))
        empty.ensure_success()
        strict = P.CaptureState(require_complete=True)
        strict.accept({"event": "probe_ready", "address": "0xcc0000"})
        for event in (self.event("gate_enter", 1), self.event("range_enter", 2), self.event("range_empty", 3), self.event("gate_result", 4, range_count=0)):
            strict.accept(P.validate_event(event))
        with self.assertRaisesRegex(RuntimeError, "completed range"): strict.ensure_success()

    def test_wrong_caller_order_timeout_late_and_incomplete_fail(self):
        wrong = P.CaptureState()
        wrong.accept({"event": "probe_ready", "address": "0xcc0000"})
        wrong.accept(P.validate_event(self.event("gate_enter", 1, caller="0xd0eb24")))
        with self.assertRaisesRegex(RuntimeError, "caller"): wrong.ensure_success()
        incomplete = P.CaptureState()
        incomplete.accept({"event": "probe_ready", "address": "0xcc0000"})
        incomplete.accept(P.validate_event(self.event("gate_enter", 1)))
        with self.assertRaisesRegex(RuntimeError, "incomplete"): incomplete.ensure_success()
        reordered = P.CaptureState()
        reordered.accept({"event": "probe_ready", "address": "0xcc0000"})
        reordered.accept(P.validate_event(self.event("gate_enter", 2)))
        reordered.accept(P.validate_event(self.event("range_enter", 1)))
        with self.assertRaisesRegex(RuntimeError, "strictly increasing"): reordered.ensure_success()
        late = P.CaptureState(); late.accept({"event": "probe_ready", "address": "0xcc0000"}); late.accept({"event": "probe_error", "reason": "gate correlation timeout"})
        with self.assertRaisesRegex(RuntimeError, "timeout"): late.ensure_success()

    def test_agent_is_observe_only_scoped_and_bounded(self):
        source = P.make_agent_source(self.config("pf_behavior_range_gate_probe_local_config.json"))
        for required in ("args[3].toUInt32()===0xea7d", "this.returnAddress.equals(exactCaller)", "entry.add(0x30).readS32()", "esp.add(0x10)", "readS32()", "gate correlation timeout", "range_empty"):
            self.assertIn(required, source)
        for forbidden in ("Memory.write", "writeU", "writeS", "writePointer", "NativeFunction", "Interceptor.replace", "sendInput"):
            self.assertNotIn(forbidden, source)
        launcher = Path(P.__file__).read_text(encoding="utf-8")
        self.assertIn("_consumer.finalize_capture(state, script, session)", launcher)
        self.assertNotIn("session.detach()", launcher)

    def test_output_confined(self):
        client = ROOT.parent / "GameClient/GameClient.local.bin"; config = ROOT / "tools/pf_behavior_range_gate_probe_local_config.json"
        safe = P.DEFAULT_CAPTURE_ROOT / "capture.jsonl"
        self.assertEqual(P.validate_output_path(safe, client, config), safe.resolve())
        with self.assertRaises(ValueError): P.validate_output_path(ROOT / "outside.jsonl", client, config)
        with self.assertRaises(ValueError): P.validate_output_path(config, client, config)


if __name__ == "__main__": unittest.main()
