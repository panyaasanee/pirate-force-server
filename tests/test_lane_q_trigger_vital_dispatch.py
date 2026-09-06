"""LANE-Q: the first live wire connection into ``TriggerStatusRegistry``.

Covers ``lane_hooks/lane_q_trigger_vital_dispatch.py`` at two levels: the
pure ``dispatch_line`` function (no ``lupa``, no ``ScriptHost`` -- these run
on every machine, same posture as ``test_script_lua_api_trigger.py``'s own
registry tests), and the registered ``@hook`` entry point through
``lane_hooks.fire()`` itself, to prove the module is actually reachable the
way ``runtime.py`` would reach it -- not just correct in isolation.

Every payload used here is one of the five real R307 capture frames'
nested-payload tail, reused verbatim from
``tests/test_lane_a_island_trigger_log.py`` (same source letter,
``pf_bridge/notes_to_chief/20260903_1901_KA1A-R307-RESULTS-*.md``) rather
than invented bytes, so a shape mismatch between the two hooks' parsing
would show up here too.
"""
from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_scene_folder  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_q_trigger_vital_dispatch as dispatch_mod,
)
from pirateforce_foundation.lua_api import trigger as lua_api_trigger  # noqa: E402


def _hex(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


# The five R307 nested payloads, verbatim from
# tests/test_lane_a_island_trigger_log.py's own NESTED_PAYLOADS.
NESTED_PAYLOADS = {
    114: _hex("0F 28 00 0B 04 2A 83 EF BD 45 2A 9A 1A 7D 44 2A 00 00 3A 43"),
    203: _hex("0F 33 00 0B 04 2A 62 B2 CE 45 2A B1 BE 96 C5 2A 00 00 3A 43"),
    217: _hex("0F 03 00 0B 04 2A DE EB 86 C4 2A 79 6F BA C5 2A 00 00 3A 43"),
}


def _session(scene_id):
    """The one attribute chain this module reads, built as a bare double --
    proving the hook needs nothing else from a real state object."""
    return SimpleNamespace(
        foundation=SimpleNamespace(
            selected=SimpleNamespace(position=SimpleNamespace(scene_id=scene_id))
        )
    )


class DispatchLineTests(unittest.TestCase):
    """No lupa, no ScriptHost, no lane_hooks.fire() -- the pure function."""

    def setUp(self):
        # A fresh, private registry for every test, same seam
        # test_script_lua_api_trigger.py itself relies on
        # (install_trigger_status_registry is "A TEST SEAM, named as one").
        self.registry = lua_api_trigger.TriggerStatusRegistry()
        lua_api_trigger.install_trigger_status_registry(self.registry)

    def test_a_real_r307_frame_advances_the_production_registry(self):
        line = dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[114])
        self.assertEqual(
            line,
            "LANE_Q_TRIGGER_VITAL_DISPATCH scene=Bg0002 wire_trigger_id=40"
            " status=1 key=WIRE_NATIVE_ID_UNPROVEN_VS_TGR_ORDINAL",
        )
        # The SAME book Trigger.GetTriggerStatus/NextStatus would read --
        # not a side channel, not a private copy.
        self.assertEqual(
            lua_api_trigger.trigger_status_registry().get_status("bg0002", 40), 1
        )

    def test_two_frames_same_scene_same_id_advance_by_one_each_time(self):
        dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[114])
        line2 = dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[114])
        self.assertIn("status=2", line2)

    def test_two_different_wire_ids_do_not_collide(self):
        # tag 0x0F values: frame 114 = 0x0028 = 40, frame 203 = 0x0033 = 51.
        dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[114])
        dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[203])
        reg = lua_api_trigger.trigger_status_registry()
        self.assertEqual(reg.get_status("bg0002", 40), 1)
        self.assertEqual(reg.get_status("bg0002", 51), 1)

    def test_two_different_scenes_same_wire_id_do_not_collide(self):
        dispatch_mod.dispatch_line(_session(2), NESTED_PAYLOADS[114])
        dispatch_mod.dispatch_line(_session(3), NESTED_PAYLOADS[114])
        reg = lua_api_trigger.trigger_status_registry()
        self.assertEqual(reg.get_status("bg0002", 40), 1)
        self.assertEqual(reg.get_status("bg0003", 40), 1)

    def test_no_trigger_id_tag_is_unresolved(self):
        line = dispatch_mod.dispatch_line(_session(2), b"\x0b\x01")
        self.assertEqual(
            line, "LANE_Q_TRIGGER_VITAL_DISPATCH UNRESOLVED reason=no_trigger_id_tag"
        )

    def test_session_missing_the_attribute_chain_is_unresolved_not_a_crash(self):
        line = dispatch_mod.dispatch_line(SimpleNamespace(), NESTED_PAYLOADS[114])
        self.assertEqual(
            line,
            "LANE_Q_TRIGGER_VITAL_DISPATCH UNRESOLVED reason=no_scene_id"
            " wire_trigger_id=40",
        )

    def test_none_session_is_unresolved_not_a_crash(self):
        line = dispatch_mod.dispatch_line(None, NESTED_PAYLOADS[114])
        self.assertEqual(
            line,
            "LANE_Q_TRIGGER_VITAL_DISPATCH UNRESOLVED reason=no_scene_id"
            " wire_trigger_id=40",
        )

    def test_a_bool_scene_id_is_rejected_the_same_as_world_scene_folder_rejects_it(self):
        # world_scene_folder.scene_folder_for_scene_id raises ValueError on a
        # non-int (bool is an int subclass in Python and is refused by name
        # in every _coerce_int door this codebase has -- same posture here).
        line = dispatch_mod.dispatch_line(_session(True), NESTED_PAYLOADS[114])
        self.assertEqual(
            line,
            "LANE_Q_TRIGGER_VITAL_DISPATCH UNRESOLVED reason=no_scene_id"
            " wire_trigger_id=40",
        )

    def test_an_unaddressed_scene_id_is_unresolved_not_a_write_to_a_guessed_folder(self):
        self.assertIsNone(world_scene_folder.scene_folder_for_scene_id(999999))
        line = dispatch_mod.dispatch_line(_session(999999), NESTED_PAYLOADS[114])
        self.assertEqual(
            line,
            "LANE_Q_TRIGGER_VITAL_DISPATCH UNRESOLVED reason=unaddressed_scene"
            " scene_id=999999 wire_trigger_id=40",
        )


class HookEntryPointTests(unittest.TestCase):
    """Through ``lane_hooks.fire()`` itself -- proves the module is actually
    registered on the point ``runtime.py`` fires, not just correct as a bare
    function."""

    def setUp(self):
        self.registry = lua_api_trigger.TriggerStatusRegistry()
        lua_api_trigger.install_trigger_status_registry(self.registry)

    def test_fire_reaches_this_module_and_writes_the_registry(self):
        capture = io.StringIO()
        real_stderr = sys.stderr
        sys.stderr = capture
        try:
            lane_hooks.fire(
                "vital_inbound_trigger_vital",
                session=_session(2),
                payload=NESTED_PAYLOADS[114],
            )
        finally:
            sys.stderr = real_stderr
        printed = capture.getvalue()
        self.assertIn("LANE_Q_TRIGGER_VITAL_DISPATCH scene=Bg0002", printed)
        self.assertEqual(
            lua_api_trigger.trigger_status_registry().get_status("bg0002", 40), 1
        )

    def test_a_non_bytes_payload_does_not_raise_out_of_fire(self):
        capture = io.StringIO()
        real_stderr = sys.stderr
        sys.stderr = capture
        try:
            lane_hooks.fire(
                "vital_inbound_trigger_vital", session=_session(2), payload="not bytes"
            )
        finally:
            sys.stderr = real_stderr
        self.assertIn("bad_payload_type=str", capture.getvalue())
        self.assertNotIn("LANE_HOOK ", capture.getvalue())  # no exception path taken

    def test_lane_a_hook_still_fires_alongside_this_one(self):
        # Registration order in _HOOKS is filename-sort order
        # (lane_hooks/__init__.py's own _discover() contract); this test
        # only needs BOTH to run, not which runs first.
        capture = io.StringIO()
        real_stderr = sys.stderr
        sys.stderr = capture
        try:
            lane_hooks.fire(
                "vital_inbound_trigger_vital",
                session=_session(2),
                payload=NESTED_PAYLOADS[114],
            )
        finally:
            sys.stderr = real_stderr
        printed = capture.getvalue()
        self.assertIn("LANE_A_TRIGGER_VITAL", printed)
        self.assertIn("LANE_Q_TRIGGER_VITAL_DISPATCH", printed)


if __name__ == "__main__":
    unittest.main()
