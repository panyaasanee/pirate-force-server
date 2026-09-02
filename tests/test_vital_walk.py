"""VITAL-WALK-001 -- every nested vital of a frame, or none of them.

WHAT THESE TESTS ARE FOR.  ``current/pf_login_game_server_v141.py`` reads the
FIRST nested vital of an inbound frame and treats the whole remaining tail as
that vital's body.  Attended round R303 measured ``vital_count = 5`` on live
traffic, and two things the owner watched fail followed from it: 42 of 46
pickup clicks were thrown away before the body was decoded, and the position
the server believed froze, so it refused a player standing 173 units from a
drop on the grounds that she was 9250 units away.

Four questions decide whether the walker is worth landing, and this file is
organised as those four:

  1. Does it reproduce the frame that was actually measured?  The R303 dump
     of frame #714 is 156 bytes with a stated layout; this file rebuilds it
     from the length table and asserts BOTH the byte count and the decoded
     coordinates, so the table cannot drift away from the capture without
     turning red.
  2. Is it fail-closed where it says it is?  One unknown id, one missing
     byte, one byte too many, one lying envelope -- each has to refuse the
     WHOLE frame by name, with no vitals handed back.
  3. Does the defect actually close?  The isolated pickup vital has to be
     ACCEPTED by the lane that refused it, driven through that lane's own
     public entry point rather than by inspecting fields here.
  4. Does the wiring RUN?  A real session, logged in and started headless,
     has to learn a position out of a batched frame that main's parser
     cannot see -- and the same session must not have its single-vital
     behaviour changed at all.

Question 4 is the one a described paragraph cannot answer, and it is why
this file boots ``make_state_class`` instead of asserting on source text.
"""
from __future__ import annotations

import ast
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_pickup_request, vital_walk  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import login_scene_override  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector,
    load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


# ---------------------------------------------------------------------------
# The frame builders.  Each one composes a vital the way the R303 dump shows
# it, from the tag helpers the legacy module exports -- never from a hand
# typed byte string, so a change to the codec convention turns this file red
# rather than leaving it agreeing with a fossil.
# ---------------------------------------------------------------------------

def _on_land_vital(legacy, x=1.0, y=2.0, z=3.0, heading=4.0, tail=1):
    """``12 B4 1E 0B 00 <4 floats> 0F 01 00`` -- 23 body bytes."""
    body = b"".join(legacy.f32tag(value)
                    for value in (x, y, z, heading))
    body += legacy.u16tag(0x0F, tail)
    return legacy.u16tag(0x12, legacy.ON_LAND_VITAL) + legacy.u8tag(0x0B, 0) + body


def _target_pos_vital(legacy, x, y, z, heading=0.0, moving=1, tail=0):
    """``12 90 2A 0B 00 <4 floats> 0B 01 0B 00`` -- 24 body bytes."""
    body = b"".join(legacy.f32tag(value)
                    for value in (x, y, z, heading))
    body += legacy.u8tag(0x0B, moving) + legacy.u8tag(0x0B, tail)
    return (legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0) + body)


def _pickup_vital(legacy, object_ref=0x11223344, opaque=0):
    """The seven-byte pickup body inside its own vital header."""
    body = legacy.u32tag(0x14, object_ref) + legacy.u8tag(0x08, opaque)
    return (legacy.u16tag(0x12, mob_pickup_request.PICKUP_REQUEST_VITAL_ID)
            + legacy.u8tag(0x0B, 0) + body)


def _unknown_vital(legacy, vital_id=0x7777, body=b"\x2a\x00\x00\x00\x00"):
    return legacy.u16tag(0x12, vital_id) + legacy.u8tag(0x0B, 0) + body


def _frame(legacy, vitals, *, outer_id=None, outer_version=0, outer_mask=2,
           vital_count=None):
    """One PC around a list of already-composed vitals.

    ``vital_count`` defaults to the truth and is a parameter so a frame can
    be made to LIE about how many vitals it carries, which is the only way
    to reach the envelope-disagreement refusal.
    """
    if outer_id is None:
        outer_id = legacy.GSCN_RUNTIME_PROTOCOL_REQ
    if vital_count is None:
        vital_count = len(vitals)
    return bytes(
        legacy.u16tag(0x12, outer_id)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, outer_version)
        + legacy.u8tag(0x0B, outer_mask)
        + legacy.u16tag(0x12, vital_count)
        + b"".join(vitals)
    )


# ---------------------------------------------------------------------------
# 1. The frame that was actually measured.
# ---------------------------------------------------------------------------

class R303FrameTests(unittest.TestCase):
    """The capture is the fixture, and its byte count is an assertion."""

    def setUp(self):
        self.legacy = _legacy()

    def test_the_r303_frame_714_is_156_bytes_and_v141_sees_one_fifth_of_it(self):
        # ka1-A, pf_bridge notes_to_chief/20260902_1800: frame #714, 156
        # bytes, vital_count = 5, four COnLandVital then one TargetPosVital,
        # and the TargetPos reported (21482.5, 9433.3, 498.0).
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])
        # THE ARITHMETIC OF THE LENGTH TABLE, EXECUTED -- and computed from
        # the SHIPPED table, not from this file's builders.  An earlier
        # draft asserted only ``len(pc) == 156``, whose two sides were both
        # built here, so mutating ON_LAND_VITAL's row from 23 to 22 left it
        # green (pf-adversary D10).  Reading the table is what makes this
        # the assertion its docstring claims it is.
        table = vital_walk.body_length_table(self.legacy)
        header_len, vital_header_len = 15, 5
        predicted = header_len + sum(
            vital_header_len + table[vital_id] for vital_id in
            [self.legacy.ON_LAND_VITAL] * 4 + [self.legacy.TARGET_POS_VITAL])
        self.assertEqual(predicted, 156)
        self.assertEqual(len(pc), predicted)

        parsed = self.legacy.parse_outer(pc)
        # This is the defect, stated as an assertion rather than as prose:
        # the frozen parser reports five vitals and hands over ONE id, and
        # the body it hands over is the whole 141-byte tail.
        self.assertEqual(parsed.vital_count, 5)
        self.assertEqual(parsed.nested_id, self.legacy.ON_LAND_VITAL)
        # 15 outer bytes and the FIRST vital's own five-byte header are
        # consumed; everything else -- 136 bytes carrying four whole vitals
        # -- is handed over as if it were one vital's body.
        self.assertEqual(len(parsed.nested_payload), 156 - 15 - 5)

    def test_the_walk_returns_all_five_vitals_in_wire_order(self):
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])
        walk = vital_walk.walk_nested_vitals(
            self.legacy, self.legacy.parse_outer(pc))
        self.assertTrue(walk.walked)
        self.assertEqual(walk.reason, vital_walk.WALKED)
        self.assertEqual(
            [v.nested_id for v in walk.vitals],
            [self.legacy.ON_LAND_VITAL] * 4 + [self.legacy.TARGET_POS_VITAL],
        )

    def test_the_dropped_target_pos_decodes_to_the_measured_coordinates(self):
        """The whole point of the walk, read back through v141's OWN decoder.

        Not this file's arithmetic: the isolated parse is handed to
        ``parse_target_pos_vital`` unchanged, which is the contract the
        runtime call site depends on.
        """
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])
        isolated = vital_walk.isolate_vital(
            self.legacy, self.legacy.parse_outer(pc),
            self.legacy.TARGET_POS_VITAL,
        )
        self.assertIsNotNone(isolated)
        pos = self.legacy.parse_target_pos_vital(isolated)
        self.assertIsNotNone(pos)
        self.assertAlmostEqual(pos[0], 21482.5, places=1)
        self.assertAlmostEqual(pos[1], 9433.3, places=1)
        self.assertAlmostEqual(pos[2], 498.0, places=1)

    def test_a_walked_frame_reconstructs_the_original_bytes_exactly(self):
        """THE STRONGEST ASSERTION IN THIS FILE, and the cheapest.

        If the header plus every vital's own bytes, concatenated in order,
        is the frame that went in, then the walk lost nothing, invented
        nothing, and put every boundary exactly where the wire put it.  A
        wrong body length cannot survive this: it either eats into the next
        vital's header (and the walk refuses) or leaves bytes over (and the
        walk refuses), and any length that did neither would have to be the
        right one.

        Driven here over the four shapes; a mutation sweep of 30,000 frames
        (single-byte corruption, truncation and extension) held the same
        invariant with zero byte loss and zero crashes, which is what
        promoted it from a check into a test.
        """
        header_len = 15
        for vitals in (
            [_on_land_vital(self.legacy)],
            [_pickup_vital(self.legacy)],
            [_on_land_vital(self.legacy)] * 4
            + [_target_pos_vital(self.legacy, 1.0, 2.0, 3.0)],
            [_target_pos_vital(self.legacy, 4.0, 5.0, 6.0),
             _pickup_vital(self.legacy, 0x01020304, 9),
             _on_land_vital(self.legacy)],
        ):
            pc = _frame(self.legacy, vitals)
            with self.subTest(count=len(vitals)):
                walk = vital_walk.walk_nested_vitals(
                    self.legacy, self.legacy.parse_outer(pc))
                self.assertTrue(walk.walked)
                self.assertEqual(
                    pc[:header_len]
                    + b"".join(v.raw_pc for v in walk.vitals),
                    pc,
                )

    def test_an_isolated_parse_keeps_v141s_own_offset_invariant(self):
        """``nested_payload == raw_pc[nested_offset + 5:]``, as v141 builds it.

        v141 points ``nested_offset`` at the nested HEADER (id + version,
        five bytes) and starts ``nested_payload`` after it.  A consumer that
        re-slices an isolated parse on that invariant has to get the body.
        """
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _pickup_vital(self.legacy, 0x0BADF00D, 3),
        ])
        walk = vital_walk.walk_nested_vitals(
            self.legacy, self.legacy.parse_outer(pc))
        self.assertTrue(walk.walked)
        for vital in walk.vitals:
            self.assertEqual(
                vital.nested_payload,
                vital.raw_pc[vital.nested_offset + 5:],
            )
            self.assertEqual(vital.vital_count, 1)


# ---------------------------------------------------------------------------
# 2. Fail-closed.  Every one of these must refuse the WHOLE frame.
# ---------------------------------------------------------------------------

class FailClosedTests(unittest.TestCase):
    """A guessed body length is a stranger's bytes read as the player's."""

    def setUp(self):
        self.legacy = _legacy()

    def _refusal(self, pc, *, vital_count=None):
        parsed = self.legacy.parse_outer(pc)
        if vital_count is not None:
            parsed = self.legacy.ParsedOuter(
                parsed.outer_id, parsed.outer_version, parsed.outer_mask,
                vital_count, parsed.nested_id, parsed.nested_version,
                parsed.nested_payload, parsed.nested_offset, parsed.raw_pc,
            )
        walk = vital_walk.walk_nested_vitals(self.legacy, parsed)
        self.assertFalse(walk.walked)
        self.assertEqual(walk.vitals, ())
        self.assertIn(walk.reason, vital_walk.VITAL_WALK_REFUSAL_REASONS)
        return walk.reason

    def test_one_unknown_id_stops_the_walk_and_the_known_vitals_go_too(self):
        # The unknown id sits LAST, behind two vitals that read perfectly.
        # Handing those two back would be a partial answer about a frame
        # whose end was never established.
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
            _unknown_vital(self.legacy),
        ])
        self.assertEqual(self._refusal(pc), "unknown_vital_id")

    def test_an_unknown_id_in_front_refuses_the_readable_tail_behind_it(self):
        pc = _frame(self.legacy, [
            _unknown_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
        ])
        self.assertEqual(self._refusal(pc), "unknown_vital_id")

    def test_one_byte_too_many_refuses_the_whole_frame(self):
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
        ]) + b"\x00"
        self.assertEqual(
            self._refusal(pc), "trailing_bytes_after_last_vital")

    def test_one_byte_missing_refuses_the_whole_frame(self):
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
        ])[:-1]
        self.assertEqual(self._refusal(pc), "truncated_vital")

    def test_a_frame_claiming_more_vitals_than_it_carries_refuses(self):
        pc = _frame(self.legacy, [_on_land_vital(self.legacy)], vital_count=4)
        self.assertEqual(self._refusal(pc), "truncated_vital")

    def test_a_parse_object_that_lies_about_the_count_refuses_by_name(self):
        # The re-read of the raw bytes disagrees with the fields handed in.
        # Walking from a position one of the two readers did not mean is
        # exactly the mistake this module exists to avoid.
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
        ])
        self.assertEqual(
            self._refusal(pc, vital_count=2 + 1), "envelope_reread_disagrees")

    def test_a_frame_that_is_not_a_runtime_protocol_req_refuses(self):
        pc = _frame(self.legacy, [_on_land_vital(self.legacy)],
                    outer_id=self.legacy.GSCN_RUNTIME_PROTOCOL_REQ ^ 0x0101)
        self.assertEqual(self._refusal(pc), "not_a_runtime_protocol_req")

    def test_a_frame_with_no_vital_collection_bit_refuses(self):
        pc = _frame(self.legacy, [_on_land_vital(self.legacy)], outer_mask=0)
        parsed = self.legacy.parse_outer(pc)
        walk = vital_walk.walk_nested_vitals(self.legacy, parsed)
        self.assertFalse(walk.walked)
        self.assertEqual(walk.reason, "not_a_vital_collection")

    def test_a_count_over_the_cap_refuses_before_any_body_is_read(self):
        pc = _frame(self.legacy, [_on_land_vital(self.legacy)],
                    vital_count=vital_walk.MAX_VITALS_PER_FRAME + 1)
        self.assertEqual(self._refusal(pc), "vital_count_too_large")

    def test_a_parse_object_that_raises_while_read_is_named_not_propagated(self):
        class Hostile:
            outer_id = 0
            outer_version = 0
            outer_mask = 2
            vital_count = 1
            nested_id = 0
            nested_version = 0
            nested_payload = b""

            @property
            def raw_pc(self):
                raise KeyError("a parse object that answers with an exception")

        walk = vital_walk.walk_nested_vitals(self.legacy, Hostile())
        self.assertFalse(walk.walked)
        self.assertIn(walk.reason, vital_walk.VITAL_WALK_REFUSAL_REASONS)

    def test_a_non_bytes_raw_pc_refuses_by_name(self):
        parsed = self.legacy.ParsedOuter(
            self.legacy.GSCN_RUNTIME_PROTOCOL_REQ, 0, 2, 1,
            self.legacy.ON_LAND_VITAL, 0, b"", 0, "not bytes",
        )
        walk = vital_walk.walk_nested_vitals(self.legacy, parsed)
        self.assertFalse(walk.walked)
        self.assertEqual(walk.reason, "raw_pc_not_bytes")

    def test_a_legacy_module_missing_its_names_refuses_by_name(self):
        class Bare:
            pass

        walk = vital_walk.walk_nested_vitals(Bare(), object())
        self.assertFalse(walk.walked)
        self.assertEqual(walk.reason, "legacy_module_missing_fields")

    def test_isolate_returns_none_rather_than_a_half_read_frame(self):
        pc = _frame(self.legacy, [
            _pickup_vital(self.legacy),
            _unknown_vital(self.legacy),
        ])
        self.assertIsNone(vital_walk.isolate_vital(
            self.legacy, self.legacy.parse_outer(pc),
            mob_pickup_request.PICKUP_REQUEST_VITAL_ID,
        ))


# ---------------------------------------------------------------------------
# 3. Does the defect close?  Driven through the refusing lane's own entry.
# ---------------------------------------------------------------------------

class PickupDefectTests(unittest.TestCase):
    """42 of 46 clicks, and the two readings of where the vital sat."""

    def setUp(self):
        self.legacy = _legacy()

    def test_the_batched_pickup_leading_the_frame_is_no_longer_refused(self):
        """~~The defect, executed~~ -- HALF of it closed in round t8z97r.

        THE STRIKE, AND WHY THE TEST IS NOT SIMPLY DELETED.  This test used
        to assert ``vital_count_not_one``: it recorded what ``main``
        answered a real click on the day the walker was written, and 42 of
        the owner's 46 clicks in R303 got exactly that answer.  LANE-B's
        round ``t8z97r`` (re-landed in ``di7ers`` after the reaper closed
        ``#603`` on a red gate) turned the equality gate on the outer vital
        count into an "at least one" gate, so the shape below -- OUR vital
        first, somebody else's behind it -- is now read as the click it is.
        The name ``vital_count_not_one`` is retired rather than deleted; it
        still stands in ``MOB_PICKUP_REQUEST_RETIRED_REASONS`` so R303's
        console stays readable.

        WHAT THIS DOES NOT SAY.  It does not say the walker is redundant.
        The two lanes close different halves and the next test is the other
        half: when the pickup vital is NOT first, this lane never sees the
        click at all, and no gate inside it can help.  That half is the
        walker's, and only the walker's.
        """
        pc = _frame(self.legacy, [
            _pickup_vital(self.legacy),
            _on_land_vital(self.legacy),
        ])
        self.assertEqual(
            mob_pickup_request.classify_pickup_request(
                self.legacy, self.legacy.parse_outer(pc)),
            "exact_pickup_request",
        )
        self.assertIn(
            "vital_count_not_one",
            mob_pickup_request.MOB_PICKUP_REQUEST_RETIRED_REASONS,
        )

    def test_a_frame_this_module_refuses_is_refused_by_the_pickup_lane_too(
            self):
        """WHEN THE TWO READERS DISAGREE ABOUT ONE FRAME, THE REFUSAL WINS.

        ~~"a frame whose pickup vital sits behind a movement vital does not
        reach the pickup lane at all"~~ IS STRUCK before it ever shipped: a
        pf-adversary pass measured it false on this very tree -- ``R309``
        made ``runtime.py`` isolate on ``leads_with_pickup or selected is
        not None``, and ``DispatchWiringTests`` below drives exactly that
        frame and watches the lane answer it.  A test whose docstring is
        refuted by the file it ships in is worth less than no test.

        What is worth pinning is the seam the merge actually created.  This
        module refuses a frame by name; the pickup lane's relaxed tail rule
        checks two bytes and passes over the rest; before round ``di7ers``
        the second granted what the first refused -- ``[pickup][12 AA BB 0B
        FF FF FF]`` decoded a click out of seven bytes of noise.  Now the
        walker's refusal IS the lane's refusal, and this test fails the day
        anyone unhooks that.
        """
        noise = bytes([0x12, 0xAA, 0xBB, 0x0B, 0xFF, 0xFF, 0xFF])
        pc = _frame(self.legacy, [_pickup_vital(self.legacy)],
                    vital_count=2) + noise
        parsed = self.legacy.parse_outer(pc)

        walk = vital_walk.walk_nested_vitals(self.legacy, parsed)
        self.assertFalse(walk.walked, "this frame was supposed to refuse")
        self.assertEqual(walk.reason, "unknown_vital_id")

        self.assertEqual(
            mob_pickup_request.classify_pickup_request(self.legacy, parsed),
            "tail_refused_by_vital_walk",
        )

    def test_the_isolated_pickup_vital_is_accepted_leading_the_frame(self):
        # READING A: the pickup vital is FIRST and the movement vitals
        # follow.  This is the reading the 42 counted refusal tokens
        # support, since the runtime branch keys on parsed.nested_id.
        pc = _frame(self.legacy, [
            _pickup_vital(self.legacy, 0x0BADF00D, 7),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
        ])
        isolated = vital_walk.isolate_vital(
            self.legacy, self.legacy.parse_outer(pc),
            mob_pickup_request.PICKUP_REQUEST_VITAL_ID,
        )
        read = mob_pickup_request.read_inbound_pickup_request(
            self.legacy, isolated, echo=False)
        self.assertTrue(read.accepted)
        self.assertEqual(read.fields.object_ref_u32, 0x0BADF00D)
        self.assertEqual(read.fields.opaque_u8, 7)

    def test_the_isolated_pickup_vital_is_accepted_trailing_the_frame(self):
        # READING B: ka1-A's prose says the request "usually arrives as
        # vital 2..5".  The two readings disagree and the walker settles
        # neither -- it handles both, and this test is the second half of
        # that promise.
        pc = _frame(self.legacy, [
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _pickup_vital(self.legacy, 0x00C0FFEE, 1),
        ])
        parsed = self.legacy.parse_outer(pc)
        # Main cannot even see it: the id it reports is somebody else's.
        self.assertEqual(parsed.nested_id, self.legacy.ON_LAND_VITAL)
        isolated = vital_walk.isolate_vital(
            self.legacy, parsed, mob_pickup_request.PICKUP_REQUEST_VITAL_ID)
        read = mob_pickup_request.read_inbound_pickup_request(
            self.legacy, isolated, echo=False)
        self.assertTrue(read.accepted)
        self.assertEqual(read.fields.object_ref_u32, 0x00C0FFEE)

    def test_the_single_vital_fast_path_hands_back_the_same_object(self):
        """Identity, not equality: a frame that works today is untouched.

        The runtime call site distinguishes "this frame needed the walk"
        from "this frame is main's" with ``is not``, so the fast path
        returning a rebuilt copy would make every ordinary click print the
        promotion line.
        """
        pc = _frame(self.legacy, [_pickup_vital(self.legacy)])
        parsed = self.legacy.parse_outer(pc)
        self.assertIs(
            vital_walk.isolate_vital(
                self.legacy, parsed,
                mob_pickup_request.PICKUP_REQUEST_VITAL_ID),
            parsed,
        )


# ---------------------------------------------------------------------------
# 4. Does the wiring RUN?  A real session, headless, no flag, no scenario.
# ---------------------------------------------------------------------------

class DispatchWiringTests(unittest.TestCase):
    """The frozen parser cannot see this position; the session must."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        pin.start()
        self.addCleanup(pin.stop)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, self.legacy.V135_PLAYER_X,
                     self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()

    def _started_session(self, token="vital_walk"):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)))
        # THE SINGLETON FIRST, exactly as a real client sends it: the walk
        # is deliberately gated until the login sequence is over, and
        # npc_spawn_sent is what ends it.  Reaching that state through the
        # dispatcher rather than by setting the flag is the difference
        # between testing the wiring and testing a mock.
        state.dispatch(self.legacy.parse_outer(_frame(
            self.legacy, [_target_pos_vital(self.legacy, 100.0, 200.0, 300.0)])))
        return state

    def test_a_batched_frame_moves_the_position_main_would_have_frozen(self):
        state = self._started_session("vital_walk_batched")
        self.assertTrue(getattr(state, "npc_spawn_sent", False))
        before = state.last_target_pos
        self.assertIsNotNone(before)

        # Frame #714's shape, with the coordinates R303 measured being
        # dropped on the floor.
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])))
        self.assertNotEqual(state.last_target_pos, before)
        x, y, z, _heading = state.last_target_pos
        self.assertAlmostEqual(x, 21482.5, places=1)
        self.assertAlmostEqual(y, 9433.3, places=1)
        self.assertAlmostEqual(z, 498.0, places=1)
        self.assertTrue(any(
            event.startswith("vital_walk_target_pos_21482")
            for event in state.events))

    def test_a_batched_frame_with_an_unknown_vital_changes_nothing(self):
        """Fail-closed at the call site, not only in the module."""
        state = self._started_session("vital_walk_unknown")
        before = state.last_target_pos
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _unknown_vital(self.legacy),
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
        ])))
        self.assertEqual(state.last_target_pos, before)

    def test_a_singleton_target_pos_is_still_v141s_to_read(self):
        """No second author of one field on one frame.

        The promotion stands down on a frame the frozen branch reads
        itself, so the value the session ends up with is v141's, and the
        walk's own event name must not appear for it.
        """
        state = self._started_session("vital_walk_singleton")
        state.dispatch(self.legacy.parse_outer(_frame(
            self.legacy,
            [_target_pos_vital(self.legacy, 777.0, 888.0, 999.0)])))
        x, y, z, _heading = state.last_target_pos
        self.assertAlmostEqual(x, 777.0, places=1)
        self.assertFalse(any(
            event.startswith("vital_walk_target_pos_777")
            for event in state.events))

    def test_a_connection_with_no_character_selected_learns_no_position(self):
        """The gate that actually bites on the production boot.

        Measured, and it corrected this round's first draft: on the census
        boot ``npc_spawn_sent`` is already True at construction
        (runtime.py:1378, which disarms v141's frozen population branch), so
        the login-order conjunct is open before the first frame arrives.
        What is left to guard -- and what every neighbouring inbound lane in
        the method guards -- is a connection that has nobody to be standing
        anywhere yet.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type("vital_walk_login_gate")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc("vital_walk_login_gate")))
        self.assertIsNone(state.foundation.selected)
        before = state.last_target_pos
        self.assertEqual(
            state._vital_walk_promote_target_pos(self.legacy.parse_outer(
                _frame(self.legacy, [
                    _on_land_vital(self.legacy),
                    _target_pos_vital(self.legacy, 1.0, 2.0, 3.0),
                ]))),
            "no_character_selected",
        )
        self.assertEqual(state.last_target_pos, before)

    def test_a_leading_target_pos_that_carries_a_click_still_moves_the_player(self):
        """THE REGRESSION TEST FOR D1, and it is the most important one here.

        The pickup branch claims the frame and returns ~1370 lines above the
        only ``super().dispatch(parsed)``.  So on a frame that LEADS with
        TargetPos and also carries a pickup click, v141 never runs -- and a
        promotion that stood down "because v141 reads this one" would leave
        the position written by nobody.  That is the R303 freeze put back on
        the one frame that most needs the position, and an adversarial pass
        measured it on the real dispatcher before it shipped.

        This exact frame MOVES THE PLAYER ON MAIN, so anything less than a
        move here is a regression, not a missed improvement.
        """
        state = self._started_session("vital_walk_lead_tpos_click")
        before = state.last_target_pos
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
            _on_land_vital(self.legacy),
            _pickup_vital(self.legacy, 0x0BADF00D),
        ])))
        self.assertNotEqual(state.last_target_pos, before)
        x, y, z, _heading = state.last_target_pos
        self.assertAlmostEqual(x, 21482.5, places=1)
        self.assertAlmostEqual(y, 9433.3, places=1)
        self.assertAlmostEqual(z, 498.0, places=1)
        # ...and the click reached the lane on the same frame.
        self.assertIn("vital_walk_pickup_promoted", state.events)

    def test_a_batched_click_reaches_the_pickup_lane_through_dispatch(self):
        """The round's headline claim, driven through the DISPATCHER.

        Two mutations of the call site survived this file's first draft --
        deleting the whole pickup-side change, and forcing the promotion
        flag to False -- because every pickup test drove the module rather
        than the branch.  Two layers agreeing about a decoder is not
        evidence that the dispatcher reaches it.
        """
        state = self._started_session("vital_walk_batched_click")
        before = [e for e in state.events if e.startswith("mob_pickup_request_")]
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _on_land_vital(self.legacy),
            _on_land_vital(self.legacy),
            _pickup_vital(self.legacy, 0x00C0FFEE),
        ])))
        after = [e for e in state.events if e.startswith("mob_pickup_request_")]
        self.assertGreater(
            len(after), len(before),
            "a batched click produced no verdict from the pickup lane: on "
            "main this frame never entered the branch at all, so an empty "
            "result here means the walked path is not wired",
        )
        self.assertIn("vital_walk_pickup_promoted", state.events)

    def test_a_click_the_walker_refuses_is_not_granted_by_the_fallback(self):
        """THE FAIL-OPEN THE MERGE CREATED, CLOSED AT THE DISPATCHER.

        ``runtime.py``'s leading-pickup fallback exists so that "a walk this
        module refuses still prints its named refusal instead of turning a
        loud line into silence".  LANE-B's relaxed tail rule, landing in the
        same week, turned that preserved REFUSAL into a GRANT: a
        pf-adversary pass on the merge dispatched ``[pickup][12 AA BB 0B FF
        FF FF]`` through a real session and read
        ``MOB_PICKUP_REQUEST_DECODED object_ref=0x00C0FFEE`` off the
        console, for a tail this module names ``unknown_vital_id``.

        Seven bytes of noise are not a vital, and a click carried by a frame
        that is not vitals is not a click.  The walk gate in the pickup lane
        refuses it now, and this test drives the whole path -- session,
        dispatcher, fallback, lane -- because both lanes' module tests were
        green while the pair was open.
        """
        state = self._started_session("vital_walk_noise_tail")
        noise = bytes([0x12, 0xAA, 0xBB, 0x0B, 0xFF, 0xFF, 0xFF])
        pc = _frame(self.legacy, [
            _pickup_vital(self.legacy, 0x00C0FFEE),
        ], vital_count=2) + noise

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            state.dispatch(self.legacy.parse_outer(pc))
        console = buffer.getvalue()

        self.assertNotIn(
            mob_pickup_request.MOB_PICKUP_REQUEST_DECODED_TOKEN, console,
            "a noise tail still bought a decoded click")
        self.assertIn(
            mob_pickup_request.MOB_PICKUP_REQUEST_TAIL_REFUSED_TOKEN,
            console,
            "the refusal is silent, which is what the fallback exists to "
            "prevent")
        self.assertFalse(any(
            event == "mob_pickup_request_" + mob_pickup_request.ACCEPTED
            for event in state.events))

    def test_a_not_yet_selected_connection_gains_no_new_reach(self):
        """D7.  Main's channel stays exactly as wide as it was.

        On main only a frame whose FIRST vital was the pickup id could
        reach this branch.  Keying on walked content would let a connection
        that has only logged in spend console lines and unbounded events
        per frame with any leading vital.
        """
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type("vital_walk_unauth")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc("vital_walk_unauth")))
        self.assertIsNone(state.foundation.selected)
        before = len(state.events)
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _on_land_vital(self.legacy),
            _pickup_vital(self.legacy, 0x41414141),
        ])))
        self.assertNotIn("vital_walk_pickup_promoted", state.events)
        self.assertFalse([
            e for e in state.events[before:]
            if e.startswith("mob_pickup_request_")])

    def test_the_later_of_two_positions_in_one_frame_is_the_one_recorded(self):
        """D8.  Recording the older one then range-checking against it IS
        the defect this round exists to remove.

        SCOPED TO THE FRAMES THIS LANE OWNS, and the boundary is worth
        stating.  When the frame LEADS with a TargetPos and nothing claims
        it, v141 reads it in its own branch and takes the FIRST of two --
        that is v141's behaviour, unchanged by this round and not this
        round's to override without becoming a second author of the field.
        The frames this walk owns are the ones v141 cannot see at all, and
        on those the last position wins.
        """
        state = self._started_session("vital_walk_two_positions")
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 1.0, 1.0, 1.0),
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, 9999.0, 8888.0, 7777.0),
        ])))
        x, y, z, _heading = state.last_target_pos
        self.assertAlmostEqual(x, 9999.0, places=1)
        self.assertAlmostEqual(y, 8888.0, places=1)
        self.assertAlmostEqual(z, 7777.0, places=1)

    def test_a_refused_walk_is_loud_on_the_console_and_in_the_events(self):
        """D3.  Absence must have ONE cause, or the round cannot be read.

        If a refusal is silent, an attended round that sees no
        VITAL_WALK_PROMOTED cannot tell "the player never clicked" from
        "every live frame carries a vital this table has never heard of".
        """
        state = self._started_session("vital_walk_loud_refusal")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
                _on_land_vital(self.legacy),
                _unknown_vital(self.legacy),
                _target_pos_vital(self.legacy, 21482.5, 9433.3, 498.0),
            ])))
        self.assertIn(
            "vital_walk_refused_unknown_vital_id", state.events)
        self.assertIn(vital_walk.VITAL_WALK_REFUSED_TOKEN, stderr.getvalue())
        self.assertIn("unknown_vital_id", stderr.getvalue())

    def test_the_refusal_line_is_said_once_per_reason_not_once_per_frame(self):
        """A client that batches an untabled vital does it on EVERY frame."""
        state = self._started_session("vital_walk_refusal_once")
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            for _ in range(5):
                state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
                    _on_land_vital(self.legacy),
                    _unknown_vital(self.legacy),
                ])))
        self.assertEqual(
            stderr.getvalue().count(vital_walk.VITAL_WALK_REFUSED_TOKEN), 1)
        # ...but every occurrence is still countable in the events trail.
        self.assertEqual(len([
            e for e in state.events
            if e == "vital_walk_refused_unknown_vital_id"]), 5)

    def test_a_closed_console_loses_a_line_and_not_the_session(self):
        """D4.  stderr into a pipe whose reader exited raises BrokenPipeError
        out of the listener thread, one connection killed per print."""
        state = self._started_session("vital_walk_closed_console")
        broken = io.StringIO()
        broken.close()
        with redirect_stderr(broken):
            state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
                _on_land_vital(self.legacy),
                _target_pos_vital(self.legacy, 555.0, 666.0, 777.0),
            ])))
        x, _y, _z, _heading = state.last_target_pos
        self.assertAlmostEqual(x, 555.0, places=1)

    def test_a_nonfinite_coordinate_is_rejected_the_way_v141_rejects_it(self):
        state = self._started_session("vital_walk_nonfinite")
        before = state.last_target_pos
        nan = struct.unpack("<f", b"\x00\x00\xc0\x7f")[0]
        state.dispatch(self.legacy.parse_outer(_frame(self.legacy, [
            _on_land_vital(self.legacy),
            _target_pos_vital(self.legacy, nan, 9433.3, 498.0),
        ])))
        self.assertEqual(state.last_target_pos, before)
        self.assertIn("vital_walk_target_pos_nonfinite_rejected", state.events)


# ---------------------------------------------------------------------------
# 5. The rebinding is safe because the branch claims the frame -- pinned,
#    not promised.
# ---------------------------------------------------------------------------

def _always_leaves(body) -> bool:
    """True when control cannot fall off the end of this statement list.

    Conservative on purpose: anything this function does not recognise as a
    terminator counts as "falls through", so an unrecognised shape turns the
    pin RED rather than quietly passing it.
    """
    if not body:
        return False
    last = body[-1]
    if isinstance(last, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
        return True
    if isinstance(last, ast.If):
        return (_always_leaves(last.body)
                and bool(last.orelse) and _always_leaves(last.orelse))
    if isinstance(last, ast.Try):
        if last.finalbody and _always_leaves(last.finalbody):
            return True
        return (_always_leaves(last.body)
                and bool(last.handlers)
                and all(_always_leaves(h.body) for h in last.handlers)
                and (not last.orelse or _always_leaves(last.orelse)))
    if isinstance(last, (ast.With, ast.AsyncWith)):
        return _always_leaves(last.body)
    if isinstance(last, ast.Match):
        return bool(last.cases) and all(
            _always_leaves(case.body) for case in last.cases)
    return False


class PickupBranchClaimsTheFrameTests(unittest.TestCase):
    """``parsed`` is rebound inside the pickup branch; nothing may see it.

    WHY THIS IS A TEST AND NOT A COMMENT.  The branch passes the isolated
    vital to LANE-B's published call by REBINDING ``parsed``, so that the
    call site still matches ``MOB_PICKUP_REQUEST_HEADLINE_CALL`` argument
    for argument -- that pin is what catches a swapped bag_cell /
    drop_ledger_cell pair, which refuses every pickup for good and
    silently, and it is not this lane's to weaken.  The rebinding is
    correct only while the branch returns on every path.  A later edit that
    adds one fall-through path would hand every lane BELOW this branch a
    one-vital parse wearing the frame's name, and no other test in this
    repository would see it.
    """

    def test_every_path_out_of_the_pickup_branch_returns(self):
        source = (ROOT / "src/pirateforce_foundation/runtime.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        branches = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            calls = [
                inner for inner in ast.walk(node)
                if isinstance(inner, ast.Call)
                and isinstance(inner.func, ast.Attribute)
                and inner.func.attr == "dispatch_inbound_pickup_request"
            ]
            if calls:
                branches.append(node)
        self.assertTrue(branches, "the pickup branch vanished from the AST")
        # The innermost `if` carrying the call is the branch itself; the
        # outer ones are the method and class bodies around it.
        branch = max(branches, key=lambda node: node.lineno)
        # THE VALUE MATTERS, NOT JUST THE NAME.  An earlier draft accepted
        # any assignment to `parsed`, so the no-op `parsed = parsed` passed
        # it (pf-adversary D11).  The rebinding is only meaningful if what
        # lands in `parsed` is the walked vital.
        self.assertTrue(
            any(isinstance(stmt, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == "parsed"
                        for t in stmt.targets)
                and isinstance(stmt.value, ast.Name)
                and stmt.value.id == "pickup_parsed"
                for stmt in branch.body),
            "the pickup branch no longer rebinds `parsed` to the walked "
            "vital; if the call site was changed to take another name "
            "instead, LANE-B's published call pin is the thing to check "
            "first -- it is not this lane's to weaken",
        )
        self.assertTrue(
            _always_leaves(branch.body),
            "runtime.py:%d -- the pickup branch rebinds `parsed` and can "
            "now fall through instead of returning, so every lane after it "
            "would read a one-vital parse as if it were the frame."
            % branch.lineno,
        )


if __name__ == "__main__":
    unittest.main()
