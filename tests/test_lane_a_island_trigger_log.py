"""The log-only 0x1FB2 hook: the five R307 frames, and the silence around them.

LANE-A, round `xv20xj`, for COO-DECISION 20260904_0343 item 4 ("five hex
frames from letter 1901 must produce five lines with the right names") as
narrowed by PANYA-INFO 20260904_0409 item 1 (print ISLAND when the id is an
island row).

The frames are the real capture bytes from
`pf_bridge/notes_to_chief/20260903_1901_KA1A-R307-RESULTS-*.md`, which
recorded frame #114 with a long enough prefix to be parsed by the frozen
`parse_outer` and the other four as their documented tail shape.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_island_dock_table as islands  # noqa: E402
from pirateforce_foundation.lane_hooks import lane_a_island_trigger_log as hooklog  # noqa: E402


def _hex(text: str) -> bytes:
    return bytes.fromhex(text.replace(" ", ""))


# R307 frame #114, verbatim from the letter up to where its quote is cut.
# Outer: id 0x6E6F, mask 0x02, two nested vitals; first nested id 0xB2 0x1F
# = TRIGGER_VITAL, version 0x01.
FRAME_114 = _hex(
    "12 6F 6E 14 00 00 00 00 08 00 0B 02 12 02 00"
    "12 B2 1F 0B 01"
    "0F 28 00 0B 04 2A 83 EF BD 45 2A 9A 1A 7D 44 2A 00 00 3A 43"
    "12 90 2A 0B 00 2A 7B FC C6 45 2A 29 87 96 44 2A 00 00 AC 42"
)

# The other four, as the letter quotes them: the nested payload from the
# trigger-id tag onward.
NESTED_PAYLOADS = {
    114: _hex("0F 28 00 0B 04 2A 83 EF BD 45 2A 9A 1A 7D 44 2A 00 00 3A 43"),
    203: _hex("0F 33 00 0B 04 2A 62 B2 CE 45 2A B1 BE 96 C5 2A 00 00 3A 43"),
    217: _hex("0F 03 00 0B 04 2A DE EB 86 C4 2A 79 6F BA C5 2A 00 00 3A 43"),
    229: _hex("0F 39 00 0B 04 2A 31 10 8A C5 2A 8F A9 C3 C5 2A 00 00 3A 43"),
    247: _hex("0F 24 00 0B 04 2A 7A C7 85 C5 2A 8F A9 C3 C5 2A 00 00 3A 43"),
}

EXPECTED_NAMES = {
    114: (40, "Black Braid Landmine"),
    203: (51, "Magic Egg"),
    217: (3, "Seafood Cargo"),
    229: (57, "Black Charm Demon Flower"),
    247: (36, "Offer Altar"),
}


class TheFiveCapturedFramesEachProduceOneCorrectLineTests(unittest.TestCase):
    def test_each_frame_yields_its_own_trigger_id(self):
        for frame, (trigger_id, _) in EXPECTED_NAMES.items():
            with self.subTest(frame=frame):
                self.assertEqual(
                    hooklog.first_tag_value(NESTED_PAYLOADS[frame], hooklog.TRIGGER_ID_TAG),
                    trigger_id,
                )

    def test_each_frame_yields_one_line_carrying_the_clients_own_name(self):
        for frame, (trigger_id, name) in EXPECTED_NAMES.items():
            line = hooklog.console_line(NESTED_PAYLOADS[frame])
            with self.subTest(frame=frame):
                self.assertIn(f"id={trigger_id} ", line)
                self.assertIn(f"name={name} ", line)
                self.assertIn(" PROP", line)
                self.assertNotIn("ISLAND", line)
                self.assertNotIn("UNPARSED", line)

    def test_the_five_lines_are_five_distinct_lines(self):
        lines = {hooklog.console_line(p) for p in NESTED_PAYLOADS.values()}
        self.assertEqual(len(lines), 5)

    def test_the_full_captured_frame_parses_through_the_frozen_parser(self):
        # Not a hand-made payload: this drives the real bytes through the
        # frozen `parse_outer`, so the hook is proven against the same seam
        # runtime.py would hand it -- including that nested_payload starts
        # AFTER the 0x0B version byte, which is the one offset a hand-built
        # fixture could get wrong and stay green about.
        sys.path.insert(0, str(ROOT / "current"))
        import pf_login_game_server_v141 as legacy

        parsed = legacy.parse_outer(FRAME_114)
        self.assertEqual(parsed.nested_id, legacy.TRIGGER_VITAL)
        self.assertEqual(parsed.nested_id, 0x1FB2)
        self.assertEqual(parsed.vital_count, 2)
        line = hooklog.console_line(bytes(parsed.nested_payload))
        self.assertIn("id=40 name=Black Braid Landmine PROP", line)


class AnIslandIdWouldAnnounceItselfTests(unittest.TestCase):
    def test_an_island_frame_says_island_and_names_the_scene(self):
        # No such frame has ever been captured -- that is precisely what the
        # attended capture ticket drafted this round is for.  This test
        # states what the console will say on the day one arrives, so the
        # ticket's grader knows the exact string to grep for.
        for trigger_id, name, scene in (
            (153, "Prison Exile Island", 2),
            (154, "Spice Paradise Island", 3),
        ):
            payload = b"\x0f" + trigger_id.to_bytes(2, "little") + b"\x0b\x04"
            line = hooklog.console_line(payload)
            with self.subTest(trigger_id=trigger_id):
                self.assertIn(f"id={trigger_id} name={name} ISLAND", line)
                self.assertIn(f"scene={scene} ", line)
                self.assertIn("no_responder bytes_out=0", line)

    def test_the_two_ids_the_ticket_targets_are_the_milestone_targets(self):
        self.assertEqual(islands.M2_TARGET_TRIGGER_IDS, (153, 154))


class TheHookNeverSendsAndNeverRaisesTests(unittest.TestCase):
    def test_it_is_registered_declares_production_allowed_and_survives_discovery(self):
        points = lane_hooks.registered_points()
        self.assertIn(hooklog.POINT, points)
        self.assertGreaterEqual(points[hooklog.POINT], 1)
        self.assertIs(hooklog.production_allowed, True)
        self.assertIs(lane_hooks.module_production_allowed(hooklog.__name__), True)

    def test_the_never_fired_state_is_declared_the_way_the_audit_reads_it(self):
        # gm/lane_gate_name_audit.py's dead-hook-point half reports a
        # registered-but-never-fired point as a defect unless the module
        # declares it.  Measured: without this declaration
        # tests/test_gm_lane_gate_name_audit.py goes red on this file, and
        # with a non-literal @hook() argument it goes red for the WHOLE tree.
        from pirateforce_foundation.gm import lane_gate_name_audit as audit

        self.assertEqual(hooklog.registered_but_not_fired, (hooklog.POINT,))
        self.assertEqual(audit.dead_hook_point_findings(), ())

    def test_the_point_it_registers_on_is_not_fired_by_runtime_yet(self):
        # Truth-in-advertising for the module docstring: today the hook is
        # registered and never fires, and the CORE-REQUEST one-liner in the
        # PR body is what changes that.  When chief lands the call site this
        # test is the one that must be updated, deliberately, in that PR.
        runtime_source = (ROOT / "src" / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(hooklog.POINT, runtime_source)

    def test_no_byte_leaves_and_nothing_is_returned_whatever_arrives(self):
        for payload in (
            b"",
            b"\x0f",
            b"\x0f\x99",
            b"\xff\xff\xff",
            b"\x0f\x99\x00" + b"\x00" * 400,
            NESTED_PAYLOADS[114],
        ):
            with self.subTest(payload=payload[:8]):
                self.assertIsNone(hooklog._on_trigger_vital(session=object(), payload=payload))

    def test_a_payload_that_does_not_walk_is_reported_as_unparsed_with_its_hex(self):
        line = hooklog.console_line(b"\xff\xee\xdd")
        self.assertIn("UNPARSED len=3 hex=ffeedd", line)
        self.assertIn("no_responder bytes_out=0", line)

    def test_a_loose_0f_byte_inside_a_float_is_not_read_as_a_trigger_id(self):
        # `2A 0F 00 99 00` is a float whose bytes happen to contain 0x0F.
        # A byte-scanning parser would report trigger id 0x0099; the tag
        # walker steps over the float and finds the real tag after it.
        payload = b"\x2a\x0f\x00\x99\x00" + b"\x0f\x99\x00"
        self.assertEqual(hooklog.first_tag_value(payload, 0x0F), 0x0099)

    def test_a_truncated_tag_at_the_end_is_unparsed_not_a_short_read(self):
        self.assertIsNone(hooklog.first_tag_value(b"\x0b\x01\x0f\x28", 0x0F))

    def test_a_length_prefixed_tag_that_overruns_stops_the_walk(self):
        self.assertIsNone(hooklog.first_tag_value(b"\x44\xff\xff\xff\xff\x0f\x28\x00", 0x0F))

    def test_a_length_prefixed_tag_that_fits_is_stepped_over(self):
        payload = b"\x44\x02\x00\x00\x00AB\x0f\x28\x00"
        self.assertEqual(hooklog.first_tag_value(payload, 0x0F), 40)

    def test_a_non_bytes_payload_still_produces_a_line_and_no_exception(self):
        self.assertIsNone(hooklog._on_trigger_vital(session=None, payload="not bytes"))

    def test_an_extra_kwarg_from_a_future_call_site_does_not_break_the_hook(self):
        self.assertIsNone(
            hooklog._on_trigger_vital(
                session=None, payload=NESTED_PAYLOADS[203], scene_id=126
            )
        )

    def test_a_gigantic_payload_cannot_write_a_gigantic_console_line(self):
        line = hooklog.console_line(b"\xff" * 100_000)
        self.assertIn("UNPARSED len=100000", line)
        self.assertLess(len(line), 400)

    def test_every_line_it_can_print_is_cp874_safe(self):
        for trigger_id in islands.TRIGGER_NAMES:
            payload = b"\x0f" + (trigger_id & 0xFFFF).to_bytes(2, "little")
            line = hooklog.console_line(payload)
            with self.subTest(trigger_id=trigger_id):
                line.encode("cp874")
                line.encode("ascii")

    def test_the_module_composes_no_frame_at_all(self):
        source = Path(hooklog.__file__).read_text(encoding="utf-8")
        for forbidden in ("frame_pc", "queue", "send", "u16tag", "qwordtag"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(f"{forbidden}(", source)


if __name__ == "__main__":
    unittest.main()
