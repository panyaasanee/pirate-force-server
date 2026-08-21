import copy
import importlib.util
import json
import math
import sys
import tempfile
import unittest
import pefile
from pathlib import Path

# The proprietary client binaries in ../GameClient can never be in a fresh
# clone; only the tests that read them are guarded.  See tests/pf_preconditions.py.
from pf_preconditions import CLIENT_IMAGE, GAME_INSTALL_TREE

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("pf_hit_result_probe", ROOT / "tools/pf_hit_result_probe.py")
P = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = P
SPEC.loader.exec_module(P)


class HitResultProbeTests(unittest.TestCase):
    def config(self, name="pf_hit_result_probe_config.json"):
        return P.load_config(ROOT / "tools" / name)

    def test_profiles_guards_and_observe_only_source(self):
        original = self.config()
        local = self.config("pf_hit_result_probe_local_config.json")
        self.assertEqual(original["hooks"], local["hooks"])
        self.assertNotEqual(original["binary"]["sha256"], local["binary"]["sha256"])
        self.assertEqual(P.DEFAULT_CLIENT.name, "GameClient.local.bin")
        self.assertEqual(P.DEFAULT_CAPTURE_ROOT.name, "capture_hit_result")
        source = P.make_agent_source(local)
        for forbidden in ("Memory.write", "writeU", "writeFloat", "NativeFunction", "Interceptor.replace"):
            self.assertNotIn(forbidden, source)
        self.assertEqual(source.count("Interceptor.attach"), len(P.EXACT_HOOKS))
        self.assertIn("(flags&1)===0||(flags&8)===0||(flags&16)!==0", source)
        self.assertIn("queue_lane:'target+0x40_prepared'", source)
        self.assertIn("target_vfunc_prepared", source)
        self.assertIn("presentation_prepared", source)
        self.assertIn("target_queue_prepared", source)
        self.assertNotIn("emit('target_vfunc'", source)
        self.assertNotIn("emit('presentation'", source)
        self.assertNotIn("emit('target_queue'", source)
        self.assertIn("Number.isFinite", source)
        self.assertEqual(local["hooks"]["presentation_call"]["va"], 0x750D90)
        self.assertEqual(local["hooks"]["target_vfunc_bit0"]["va"], 0x7508E3)
        self.assertEqual(local["hooks"]["target_vfunc_bits5_6"]["va"], 0x750903)
        self.assertNotIn("target_queue", local["hooks"])

    # Hashes GameClient.bin from the proprietary install tree AND the patched
    # local image; the local image lives inside that tree, so client_image is
    # the stricter single key.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_real_binary_guards_both_profiles(self):
        P.guard_binary(ROOT.parent / "GameClient/GameClient.bin", self.config())
        P.guard_binary(ROOT.parent / "GameClient/GameClient.local.bin", self.config("pf_hit_result_probe_local_config.json"))

    # Parses relocations out of both proprietary client binaries; the local
    # image lives inside the install tree, so client_image is the stricter
    # single key.  See tests/pf_preconditions.py.
    @CLIENT_IMAGE.skip_unless_present()
    def test_hook_spans_do_not_overlap_pe_relocations(self):
        for filename in ("GameClient.bin", "GameClient.local.bin"):
            image = ROOT.parent / "GameClient" / filename
            pe = pefile.PE(str(image), fast_load=False)
            relocated = {
                pe.OPTIONAL_HEADER.ImageBase + entry.rva
                for block in getattr(pe, "DIRECTORY_ENTRY_BASERELOC", [])
                for entry in block.entries
                if entry.type == pefile.RELOCATION_TYPE["IMAGE_REL_BASED_HIGHLOW"]
            }
            for name, hook in P.EXACT_HOOKS.items():
                span = range(hook["va"], hook["va"] + len(bytes.fromhex(hook["code"])))
                self.assertFalse(relocated.intersection(span), name)

    def test_config_is_exact(self):
        config = copy.deepcopy(self.config())
        config["limits"]["max_records"] = 33
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "limits"):
                P.load_config(path)

    def test_ready_only_and_require_hit(self):
        ready = {"schema": 1, "event": "probe_ready", "timestamp": "x", "address": "0x400000"}
        self.assertIs(P.validate_event(ready), ready)
        state = P.CaptureState()
        state.accept(ready)
        state.ensure_success()
        strict = P.CaptureState(require_hit=True)
        strict.accept(ready)
        with self.assertRaisesRegex(RuntimeError, "not observed"):
            strict.ensure_success()
        hit = {"schema": 1, "event": "hit_result", "timestamp": "x", "thread_id": 1, "sequence": 1, "address": "0x7507a5", "object": "0x1", "vital_id": 0x16F7, "performer": "0x2", "field_20": 0, "action": 0xEA7D, "field_24": 0, "field_28": 0, "records": []}
        P.validate_event(hit)
        strict.accept(hit)
        with self.assertRaisesRegex(RuntimeError, "did not complete"):
            strict.ensure_success()
        complete = {"schema": 1, "event": "hit_complete", "timestamp": "x", "thread_id": 1, "sequence": 2, "address": "0x750e95", "object": "0x1"}
        P.validate_event(complete)
        strict.accept(complete)
        strict.ensure_success()
        with self.assertRaisesRegex(ValueError, "fields"):
            P.validate_event(dict(hit, damage=1))
        with self.assertRaisesRegex(ValueError, "performer"):
            P.validate_event(dict(hit, performer="0xnothex"))

    def test_host_state_correlates_thread_object_and_sequence(self):
        ready = {"event": "probe_ready"}
        hit = {"event": "hit_result", "thread_id": 7, "object": "0xa", "sequence": 1}
        middle = {"event": "target_resolved", "thread_id": 7, "object": "0xa", "sequence": 2}
        complete = {"event": "hit_complete", "thread_id": 7, "object": "0xa", "sequence": 3}
        state = P.CaptureState(require_hit=True)
        for event in (ready, hit, middle, complete):
            state.accept(event)
        state.ensure_success()
        cases = (
            (hit, dict(complete, thread_id=8), "matching active"),
            (hit, dict(complete, object="0xb"), "matching active"),
            (hit, dict(middle, sequence=1), "strictly increasing"),
            (hit, dict(hit, sequence=2), "duplicate active"),
            (dict(middle, sequence=1), None, "matching active"),
        )
        for first, second, message in cases:
            state = P.CaptureState(require_hit=True)
            state.accept(ready)
            state.accept(first)
            if second is not None:
                state.accept(second)
            with self.assertRaisesRegex(RuntimeError, message):
                state.ensure_success()

    def test_correlation_source_is_fail_closed(self):
        source = P.make_agent_source(self.config("pf_hit_result_probe_local_config.json"))
        self.assertIn("active.delete(tid);fail('record correlation mismatch');return null", source)
        self.assertIn("record pointer is outside captured vector", source)
        self.assertIn("target object correlation mismatch", source)

    def test_late_error_and_bounded_cleanup_contract(self):
        state = P.CaptureState()
        state.accept({"event": "probe_ready"})
        state.accept({"event": "probe_error", "reason": "late"})
        with self.assertRaisesRegex(RuntimeError, "late"):
            state.ensure_success()
        source = Path(P.__file__).read_text(encoding="utf-8")
        self.assertIn("_consumer.finalize_capture(state, script, session)", source)
        self.assertNotIn("session.detach()", source)

    # validate_output_path resolves the client with strict=True, so it needs
    # GameClient.bin from the proprietary install tree.  See tests/pf_preconditions.py.
    @GAME_INSTALL_TREE.skip_unless_present()
    def test_safe_output(self):
        client = ROOT.parent / "GameClient/GameClient.bin"
        config = ROOT / "tools/pf_hit_result_probe_config.json"
        with tempfile.TemporaryDirectory() as td:
            safe = Path(td).resolve()
            good = (safe / "run/events.jsonl").resolve()
            self.assertEqual(P.validate_output_path(good, client, config, safe), good)
            with self.assertRaisesRegex(ValueError, "absolute"):
                P.validate_output_path(Path("relative.jsonl"), client, config, safe)
            with self.assertRaisesRegex(ValueError, "capture directory"):
                P.validate_output_path((safe.parent / "escape.jsonl").resolve(), client, config, safe)
        with self.assertRaisesRegex(ValueError, "aliases"):
            P.validate_output_path(client.resolve(), client, config, client.parent)


if __name__ == "__main__":
    unittest.main()
