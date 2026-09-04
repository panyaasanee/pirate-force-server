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

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_island_dock_table as islands  # noqa: E402
from pirateforce_foundation.lane_hooks import lane_a_island_trigger_log as hooklog  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


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
    247: _hex("0F 24 00 0B 04 2A 7A C7 85 C5 2A 56 D1 91 C3 2A 00 00 3A 43"),
}

# The xyz triple each frame carries, decoded from the floats above.  These
# exist to make the fixture self-checking: pf-adversary (D2) caught frame
# #247's second float copied from #229, and NOTHING in the suite could have
# seen it, because `first_tag_value` returns after offset 3 and no test read a
# byte past it.  A wrong float now moves a coordinate and goes red.  Values
# re-derived from the letter's own hex, one frame at a time.
EXPECTED_XYZ = {
    114: (6077.9, 1012.4, 186.0),
    203: (6614.3, -4823.8, 186.0),
    217: (-1079.4, -5965.9, 186.0),
    229: (-4418.0, -6261.2, 186.0),
    247: (-4280.9, -291.6, 186.0),
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
        # Frame 217 (id=3, "Seafood Cargo") is excluded from the blanket PROP
        # assertion below on purpose -- see the class right after this one.
        # GT-228 (R308, PASS) made id=3 the OBSERVED wire id for Spice
        # Paradise Island contact, and the hook now reports it as ISLAND
        # even though this specific captured frame really is R307's ordinary
        # Seafood Cargo prop hit; COO-DECISION 20260904_1345 item 3(a)
        # accepts that collision as a known risk of the id-2/3 hypothesis.
        for frame, (trigger_id, name) in EXPECTED_NAMES.items():
            if frame == 217:
                continue
            line = hooklog.console_line(NESTED_PAYLOADS[frame])
            with self.subTest(frame=frame):
                self.assertIn(f"id={trigger_id} ", line)
                self.assertIn(f"name={name} ", line)
                self.assertIn(" PROP", line)
                self.assertNotIn("ISLAND", line)
                self.assertNotIn("UNPARSED", line)

    def test_frame_217_is_the_known_id3_collision_gt228_now_calls_island(self):
        # Real R307 bytes, real "Seafood Cargo" name from the client's own
        # table -- and, since GT-228, ALSO the id the wire uses for Spice
        # Paradise Island contact.  This test pins the collision so the next
        # round that touches this hook sees it as a documented, accepted
        # trade-off rather than rediscovering it as a regression.
        line = hooklog.console_line(NESTED_PAYLOADS[217])
        self.assertIn("id=3 name=Spice Paradise Island ISLAND", line)
        self.assertIn("wire=OBSERVED_GT228_R308", line)
        self.assertNotIn("Seafood Cargo", line)

    def test_the_five_lines_are_five_distinct_lines(self):
        lines = {hooklog.console_line(p) for p in NESTED_PAYLOADS.values()}
        self.assertEqual(len(lines), 5)

    def test_every_byte_of_every_fixture_is_read_by_something(self):
        # The fixture-rot guard (pf-adversary D2).  Each payload is
        # `0F <id> 0B 04 2A x 2A y 2A z` and this walks ALL of it: the tag
        # bytes, the widths, and the three floats.  A byte copied from the
        # wrong frame moves a coordinate and fails here.
        import struct

        for frame, payload in NESTED_PAYLOADS.items():
            with self.subTest(frame=frame):
                self.assertEqual(len(payload), 20)
                self.assertEqual(payload[0], 0x0F)
                self.assertEqual(payload[3:5], b"\x0b\x04")
                self.assertEqual(payload[5], 0x2A)
                self.assertEqual(payload[10], 0x2A)
                self.assertEqual(payload[15], 0x2A)
                xyz = tuple(
                    round(struct.unpack("<f", payload[off:off + 4])[0], 1)
                    for off in (6, 11, 16)
                )
                self.assertEqual(xyz, EXPECTED_XYZ[frame])

    def test_the_five_capture_positions_are_five_different_places(self):
        # The specific thing D2 broke: two frames sharing a coordinate.
        self.assertEqual(len(set(EXPECTED_XYZ.values())), 5)
        self.assertEqual(len({xy[:2] for xy in EXPECTED_XYZ.values()}), 5)

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


# R308's own captured nested payloads (KA1A-R308-RESULTS, 20260904_1331):
# rx130/rx152/rx248 at Prison Exile Island (id=2), rx433/rx491 at Spice
# Paradise Island (id=3).  Trimmed to the tag-walker's own shape
# (`0F <id> 00 0B 04 2A x 2A y 2A z`), same convention `NESTED_PAYLOADS`
# above uses for the R307 fixtures.
R308_NESTED_PAYLOADS = {
    "rx130": _hex(
        "0F 02 00 0B 04 2A 78 1C 8B C5 2A AB 98 8D 45 2A 00 00 3A 43"
    ),
    "rx152": _hex(
        "0F 02 00 0B 04 2A 54 6E AF C5 2A 51 14 82 45 2A 00 00 3A 43"
    ),
    "rx433": _hex(
        "0F 03 00 0B 04 2A 31 6F C3 C4 2A 04 D9 A4 C5 2A 00 00 3A 43"
    ),
    "rx491": _hex(
        "0F 03 00 0B 04 2A 03 0C D7 C4 2A E4 1C A4 C5 2A 00 00 3A 43"
    ),
}


class TheGT228ObservedOverrideTests(unittest.TestCase):
    """id 2/3 on REAL R308 wire bytes -- not the 153/154 fabricated payloads
    `AnIslandIdWouldAnnounceItselfTests` above uses, which have never once
    been observed.  COO-DECISION 20260904_1345 item 3(a)."""

    def test_every_r308_island_contact_frame_says_island(self):
        expect = {
            "rx130": (2, "Prison Exile Island"),
            "rx152": (2, "Prison Exile Island"),
            "rx433": (3, "Spice Paradise Island"),
            "rx491": (3, "Spice Paradise Island"),
        }
        for label, (wire_id, name) in expect.items():
            line = hooklog.console_line(R308_NESTED_PAYLOADS[label])
            with self.subTest(label=label):
                self.assertIn(f"id={wire_id} name={name} ISLAND", line)
                self.assertIn("wire=OBSERVED_GT228_R308", line)
                self.assertIn("no_responder bytes_out=0", line)

    def test_the_override_table_is_exactly_the_two_observed_ids(self):
        self.assertEqual(
            hooklog.M2_OBSERVED_ISLAND_TRIGGER_IDS, {2: 153, 3: 154}
        )

    def test_an_id_outside_the_override_still_uses_the_dock_table(self):
        # id=40 (Black Braid Landmine, R307 frame 114) is untouched by the
        # override -- still PROP, still the client's own name.
        line = hooklog.console_line(NESTED_PAYLOADS[114])
        self.assertIn("id=40 name=Black Braid Landmine PROP", line)
        self.assertNotIn("OBSERVED_GT228_R308", line)


class TheHookNeverSendsAndNeverRaisesTests(unittest.TestCase):
    def test_it_is_registered_declares_production_allowed_and_survives_discovery(self):
        points = lane_hooks.registered_points()
        self.assertIn(hooklog.POINT, points)
        self.assertGreaterEqual(points[hooklog.POINT], 1)
        self.assertIs(hooklog.production_allowed, True)
        self.assertIs(lane_hooks.module_production_allowed(hooklog.__name__), True)

    def test_the_declaration_and_the_call_site_stay_in_step_through_the_handover(self):
        # WRITTEN TO SURVIVE CHIEF'S ONE-LINE CORE-REQUEST, not to block it
        # (pf-adversary D3).  The first draft asserted two separate absolute
        # facts -- "runtime.py does not name this point" and "the module
        # declares it never-fired" -- and measured consequence was that chief
        # landing the fire() call the PR body asks for turns THIS file red in
        # two or three places whatever he does, including when he follows the
        # deletion instruction exactly.  That would have cost the attended
        # capture round the whole ticket exists for.
        #
        # So this asserts the RELATION instead: the module declares the point
        # never-fired if and only if nothing fires it.  Both states are green,
        # the illegal in-between states are red, and the handover is one
        # edit -- delete `registered_but_not_fired` in the same commit that
        # adds the call site, exactly as the module's own comment says.
        runtime_source = (ROOT / "src" / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8"
        )
        fired_by_runtime = hooklog.POINT in runtime_source
        declared = hooklog.POINT in getattr(hooklog, "registered_but_not_fired", ())
        self.assertEqual(
            declared,
            not fired_by_runtime,
            "declare the point never-fired exactly while nothing fires it: "
            f"runtime.py names it = {fired_by_runtime}, declared = {declared}",
        )

    def test_the_hook_is_registered_on_the_point_whichever_state_we_are_in(self):
        # The half of the old pair that is true in BOTH worlds, kept as its
        # own test so the relation above cannot be satisfied by a module that
        # has quietly stopped registering anything.
        self.assertIn(hooklog.POINT, lane_hooks.registered_points())

    def test_every_tag_width_in_the_walkers_table_is_actually_pinned(self):
        # pf-adversary D5 measured that five of the seven widths and one of
        # the two length-prefixed tags could be mutated with the whole suite
        # still green: the step-over branch had only ever run for 0x2A and
        # 0x44, because in every real payload the trigger id comes first.
        # This drives the step-over for EVERY tag the table claims to know:
        # a wrong width desynchronises the walk and the trailing 0x0F is no
        # longer found, or is found at the wrong offset.
        for tag, width in hooklog._TAG_WIDTHS.items():
            if tag == hooklog.TRIGGER_ID_TAG:
                continue
            payload = bytes([tag]) + b"\x0f" * width + b"\x0f\x99\x00"
            with self.subTest(tag=hex(tag), width=width):
                self.assertEqual(hooklog.first_tag_value(payload, 0x0F), 153)
        for tag in hooklog._TAG_LENGTH_PREFIXED:
            payload = (
                bytes([tag]) + (3).to_bytes(4, "little") + b"\x0f\x0f\x0f"
                + b"\x0f\x99\x00"
            )
            with self.subTest(length_prefixed=hex(tag)):
                self.assertEqual(hooklog.first_tag_value(payload, 0x0F), 153)

    def test_the_trigger_id_tag_width_matches_the_proven_serializer_row(self):
        # PF_SERIALIZER_FIELDS.tsv: TriggerVital W/R order 1 is tag 0x0F,
        # 2 bytes, ALWAYS, and it is the first field.  Both facts are what
        # the walker depends on, so both are pinned here.
        self.assertEqual(hooklog.TRIGGER_ID_TAG, 0x0F)
        self.assertEqual(hooklog._TAG_WIDTHS[0x0F], 2)
        self.assertEqual(NESTED_PAYLOADS[114][0], hooklog.TRIGGER_ID_TAG)

    def test_the_hook_returns_none_for_every_payload_shape(self):
        # NAME SAYS WHAT IT MEASURES (pf-adversary D10): the return-value
        # half only.  The "no byte leaves" half is
        # test_the_module_composes_no_frame_at_all below, which greps the
        # source -- a function returning None proves nothing about sending.
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


class TheCapturedFrameWalksTheWholeDispatcherTests(unittest.TestCase):
    """COO-DECISION 20260904_0642 item 3, on the capture's own bytes.

    Two proofs already exist and neither is this one.
    `TheFiveCapturedFramesEachProduceOneCorrectLineTests` above drives the
    REAL R307 bytes but stops at `console_line()` -- no dispatcher, no
    session.  `tests/test_lane_a_trigger_vital_dispatch_wiring.py` (LANE-E
    R333, the round that landed the call site) drives the REAL dispatcher
    but hands it a hand-built three-byte payload `0F <id> 00` inside a
    hand-built envelope.

    The frame this class drives is neither: its outer header says
    `vital_count = 2`, and `parse_outer` hands the hook a `nested_payload`
    that RUNS PAST the end of the TriggerVital and into the position vital
    behind it (measured: 40 bytes handed over for a 20-byte trigger vital).
    That overrun is the whole reason the walker in the module refuses to
    step over tag 0x12, and until this class nothing drove that refusal
    through the real dispatch path.

    SIZE, SAID ONCE AND CORRECTLY (pf-adversary D1).  The frame on the wire
    was 69 bytes; `FRAME_114` is the 60 bytes the R307 letter quotes before
    its quote is cut, as the fixture's own comment says.  The first draft of
    this class called the fixture 69 bytes in four places -- reading a number
    out of an evidence file without reading that file's own conclusion.  The
    nine unseen tail bytes matter to exactly one test below and it says so.

    `GT-228` grades a console line during an attended run on the owner's
    machine.  A `LANE_A_TRIGGER_VITAL ... ISLAND` line printed for the wrong
    reason would send the milestone down a wrong road for a day, so these
    tests are as interested in the lines that must NOT appear as in the one
    that must.
    """

    ISLAND_ID = 153  # Prison Exile Island = M2 target 1.

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = load_legacy(ROOT / "current" / "pf_login_game_server_v141.py")
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _logged_in_session(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def _dispatch(self, state, frame):
        """Feed one whole captured PC frame in and collect the console."""
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = state.dispatch(self.legacy.parse_outer(frame))
        return actions, stderr.getvalue()

    @staticmethod
    def _lane_a_lines(console):
        return [
            line for line in console.splitlines()
            if line.startswith(hooklog.TOKEN)
        ]

    # The trigger-id field of FRAME_114, located rather than hardcoded: the
    # nested payload starts right after `12 B2 1F 0B 01`, and its first tag
    # is the 0x0F the serializer row pins as field order 1.
    _ID_AT = 21

    def test_the_field_this_class_edits_is_where_it_thinks_it_is(self):
        self.assertEqual(FRAME_114[self._ID_AT - 1], hooklog.TRIGGER_ID_TAG)
        self.assertEqual(
            int.from_bytes(FRAME_114[self._ID_AT:self._ID_AT + 2], "little"),
            EXPECTED_NAMES[114][0],
        )

    def test_the_fixture_is_the_quoted_60_bytes_not_the_69_on_the_wire(self):
        # pf-adversary D1: the letter says the frames were 69 bytes ON THE
        # WIRE and quotes 60 of them.  Nothing in the suite pinned that, so
        # "69" travelled into four documents as if it described the fixture.
        # Pinned here so the next person to "fix the fixture to match the
        # letter" has to read this line first: the 9 missing bytes have never
        # been seen by anyone, and one test below depends on not pretending
        # otherwise.
        self.assertEqual(len(FRAME_114), 60)
        self.assertEqual(len(NESTED_PAYLOADS[114]), 20)

    def _with_trigger_id(self, trigger_id):
        return (
            FRAME_114[:self._ID_AT]
            + trigger_id.to_bytes(2, "little")
            + FRAME_114[self._ID_AT + 2:]
        )

    def test_the_captured_frame_prints_its_prop_line_and_answers_nothing(self):
        state = self._logged_in_session("capfr114")
        rx_before = state.rx_frames
        actions, console = self._dispatch(state, FRAME_114)
        lines = self._lane_a_lines(console)
        self.assertEqual(actions, [], "0x1FB2 is log-only: no bytes go out")
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(len(lines), 1, console)
        self.assertIn("id=40 name=Black Braid Landmine PROP", lines[0])
        self.assertIn("no_responder bytes_out=0", lines[0])

    def test_an_island_id_in_the_captured_frame_shape_says_island(self):
        # The proof COO-DECISION 0642 item 3 asks for, standing on main: a
        # captured TriggerVital whose ONLY edit is the two id bytes (0x28 ->
        # 0x99) reaches the hook through runtime.py's dispatcher and names
        # the island, still sending nothing.  This is the exact byte string
        # `GT-228`'s search criterion (ข) tells the tester to grep the
        # capture for: `0F 99 00 0B 04`.
        state = self._logged_in_session("capisl2")
        frame = self._with_trigger_id(self.ISLAND_ID)
        self.assertIn(b"\x0f\x99\x00\x0b\x04", frame)
        actions, console = self._dispatch(state, frame)
        lines = self._lane_a_lines(console)
        self.assertEqual(actions, [])
        self.assertEqual(len(lines), 1, console)
        # The WHOLE line, evidence label included (pf-adversary D5): `wire=`
        # is the grade of the scene number sitting next to it, and a test
        # that pins `scene=2` while letting PROVEN drift to CANDIDATE pins
        # the number without its warranty.
        self.assertIn(
            "id=153 name=Prison Exile Island ISLAND scene=2 min_level=0",
            lines[0],
        )
        self.assertIn("wire=PROVEN", lines[0])
        self.assertIn("no_responder bytes_out=0", lines[0])

    def test_the_other_target_island_says_candidate_where_this_one_says_proven(self):
        # NOT "reads the same way" (pf-adversary D5): island 3's line differs
        # from island 2's in the two places that carry the most weight, and
        # the attended grader is the person most likely to read one and
        # assume the other.  Both differences are pinned here.
        state = self._logged_in_session("capisl3")
        actions, console = self._dispatch(state, self._with_trigger_id(154))
        lines = self._lane_a_lines(console)
        self.assertEqual(actions, [])
        self.assertEqual(len(lines), 1, console)
        self.assertIn(
            "id=154 name=Spice Paradise Island ISLAND scene=3 min_level=25",
            lines[0],
        )
        self.assertIn("wire=CANDIDATE", lines[0])
        self.assertNotIn("wire=PROVEN", lines[0])

    def test_the_payload_handed_over_runs_past_the_trigger_vital(self):
        # Measured, not assumed -- this is the fact the next two tests
        # depend on, and if `parse_outer` ever stops overrunning, they stop
        # proving anything and this one says so.
        parsed = self.legacy.parse_outer(FRAME_114)
        self.assertEqual(len(NESTED_PAYLOADS[114]), 20)
        self.assertGreater(len(bytes(parsed.nested_payload)), 20)
        self.assertTrue(bytes(parsed.nested_payload).startswith(NESTED_PAYLOADS[114]))

    # `12 90 2A 0B 00` -- the header of the position vital riding behind the
    # TriggerVital in FRAME_114, lifted so the frame below is built out of
    # named parts rather than offsets.
    _SECOND_VITAL_HEADER = bytes.fromhex("12902a0b00")

    def _frame_whose_island_bytes_sit_behind_a_0x12(self):
        """A TriggerVital with NO 0x0F, and `0F 99 00` inside the vital behind it.

        Built explicitly (pf-adversary D10: the first draft sliced at offset
        40 and re-joined, which reassembles the same bytes for ANY offset --
        it read like a pinned vital boundary and pinned nothing).  Here the
        trigger vital keeps its `0B 04` + three floats and loses only the
        three id bytes, and the island bytes are placed where a walker that
        stepped over 0x12 lands on them deterministically -- not where the
        end of a truncated fixture happens to put them (pf-adversary D2).
        """
        trigger_body = FRAME_114[self._ID_AT + 2:40]  # 0B 04 + 2A x 2A y 2A z
        second_vital = self._SECOND_VITAL_HEADER + b"\x0f\x99\x00"
        return FRAME_114[:20] + trigger_body + second_vital

    def test_a_second_vital_cannot_donate_a_trigger_id_to_the_first(self):
        # The false-ISLAND guard, driven end to end.  A walker that stepped
        # over 0x12 would read 153 out of the neighbouring vital and print
        # the very line `GT-228` would grade as "the island fired".  It must
        # print UNPARSED with the hex instead, and no island name.
        #
        # NOT a shape the client can produce today (pf-adversary D11): the
        # pinned serializer row makes tag 0x0F field order 1 of every
        # TriggerVital, so on the wire the id always precedes any 0x12.
        # This is a regression guard on the walker, not a live risk.
        frame = self._frame_whose_island_bytes_sit_behind_a_0x12()
        self.assertNotIn(b"\x0f\x28\x00", frame)
        self.assertIn(b"\x0f\x99\x00", frame)
        state = self._logged_in_session("capfalse")
        actions, console = self._dispatch(state, frame)
        lines = self._lane_a_lines(console)
        self.assertEqual(actions, [])
        self.assertEqual(len(lines), 1, console)
        self.assertIn("UNPARSED", lines[0])
        self.assertNotIn("ISLAND", lines[0])
        self.assertNotIn("Prison Exile", lines[0])

    def test_the_island_bytes_in_that_frame_are_reachable_if_you_step_over_0x12(self):
        # The positive control the guard above needs (pf-adversary D2).
        # Without it, UNPARSED proves only "the walk did not get there" --
        # which a truncated fixture, a mistyped tail, or a lucky byte can
        # produce while the walker happily steps over 0x12.  Walking the
        # same frame from just past the 0x12 field MUST find 153: so when
        # the walker returns None for the whole frame, the only remaining
        # explanation is that it refused the 0x12, which is the behaviour
        # under test.
        frame = self._frame_whose_island_bytes_sit_behind_a_0x12()
        at = frame.index(self._SECOND_VITAL_HEADER) + 3  # past `12 90 2A`
        self.assertEqual(hooklog.first_tag_value(frame[at:], 0x0F), 153)
        payload = bytes(self.legacy.parse_outer(frame).nested_payload)
        self.assertIsNone(hooklog.first_tag_value(payload, 0x0F))

    def test_a_trigger_vital_riding_second_never_reaches_the_hook_at_all(self):
        # MEASURED, and it is a finding, not a feature (pf-adversary D13):
        # `parse_outer` reads the FIRST nested vital only -- its own comment
        # says boundaries for the rest need every vital's schema.  Put the
        # TriggerVital second and `nested_id` is the position vital's
        # 0x2A90, the dispatch branch is never chosen, and the console says
        # NOTHING.  R307's five frames happened to carry the TriggerVital
        # first; nobody has established that the island-contact frame will.
        # If `GT-228` comes back with a silent console, this is the first
        # thing to rule out -- not "the build has no call site".
        frame = FRAME_114[:15] + FRAME_114[40:] + FRAME_114[15:40]
        parsed = self.legacy.parse_outer(frame)
        self.assertNotEqual(parsed.nested_id, self.legacy.TRIGGER_VITAL)
        self.assertEqual(parsed.nested_id, 0x2A90)
        state = self._logged_in_session("capsecond")
        _actions, console = self._dispatch(state, frame)
        self.assertEqual(self._lane_a_lines(console), [], console)

    def test_one_captured_frame_replayed_with_five_ids_sends_nothing(self):
        # NAMED FOR WHAT IT DRIVES (pf-adversary D4): one captured frame,
        # five ids -- the other four frames' bytes (their own floats) reach
        # only `console_line()`, in the offline class above.  What this adds
        # is the session-level half of R307's measurement: five frames in,
        # zero answers out.  A hook that answered every fifth frame would
        # still pass the single-frame test above.
        state = self._logged_in_session("capfive")
        rx_before = state.rx_frames
        console = ""
        for frame_no, (trigger_id, _name) in EXPECTED_NAMES.items():
            actions, out = self._dispatch(state, self._with_trigger_id(trigger_id))
            with self.subTest(frame=frame_no):
                self.assertEqual(actions, [])
            console += out
        lines = self._lane_a_lines(console)
        self.assertEqual(len(lines), 5, console)
        self.assertEqual(state.rx_frames, rx_before + 5)
        for _frame_no, (trigger_id, name) in EXPECTED_NAMES.items():
            if _frame_no == 217:
                # id=3 -- the known GT-228 override collision, see
                # `TheFiveCapturedFramesEachProduceOneCorrectLineTests
                # .test_frame_217_is_the_known_id3_collision_gt228_now_calls_island`.
                self.assertTrue(
                    any(
                        "id=3 name=Spice Paradise Island ISLAND" in line
                        for line in lines
                    ),
                    lines,
                )
                continue
            self.assertTrue(
                any(f"id={trigger_id} name={name} " in line for line in lines),
                f"no line for id={trigger_id}: {lines}",
            )

    def test_the_console_lines_the_attended_grader_reads_are_ascii(self):
        state = self._logged_in_session("capascii")
        for trigger_id in (self.ISLAND_ID, 154, 40):
            _actions, console = self._dispatch(
                state, self._with_trigger_id(trigger_id),
            )
            lines = self._lane_a_lines(console)
            with self.subTest(trigger_id=trigger_id):
                # Assert a line EXISTS before asserting it encodes
                # (pf-adversary D3): "".encode("cp874") succeeds, so without
                # this the test stayed green with the call site deleted --
                # answering "is the console safe" with a console that has
                # nothing in it, for a ticket that lives on that console.
                self.assertEqual(len(lines), 1, console)
                lines[0].encode("ascii")
                lines[0].encode("cp874")


if __name__ == "__main__":
    unittest.main()
