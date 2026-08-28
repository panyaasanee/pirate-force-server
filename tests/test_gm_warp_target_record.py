"""LANE-GM: where a `/warp` sent someone, kept for exactly one position read.

Chief's `GM_WARP_POSITION_CONFIRMED` token (PR #212, merged) proves that the
first position report after a GM warp caused a real durable write.  His own
reply filed what it cannot prove -- that the row written is the point the GM
asked for -- and asked this lane to expose the destination
(`notes_to_chief/20260828_2301_CHIEF-REPLY-LANE-GM-030-wired-029-deferred.md`,
appendix item 5).  This file proves the exposed half is worth reading:

1. THE TARGET IS THE FRAME.  The recorded coordinates are the binary32
   values the ForcePos payload carries, not the float64 the GM typed, and the
   frame bytes are byte-identical to the ones the existing composer builds.
   A target that disagrees with the bytes would make the client look wrong
   for this lane's rounding.
2. IT CANNOT OUTLIVE ITS FRAME.  Taken once, then gone; replaced by a second
   warp; refused for a different character; never parked at all when the warp
   was refused.  A stale target measures a position row against a warp that
   never happened, which is the same class of lie chief's arming flag had to
   be narrowed to one frame to avoid.
3. NOT-COMPARABLE IS NOT A MATCH.  A row in another scene, a missing
   coordinate, a NaN -- every one of them is `None`/False, never a distance
   that reads as "close".

nonclaim: nothing here is evidence that any client moved.  RE-129 measured
the ForcePos handler as `mov al,1; ret 4`, so today the expected live result
is a MISMATCH with a large distance, and this file's job is to make that
number honest rather than to make it small.
"""
from __future__ import annotations

import math
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.gm.commands import parse_gm_command  # noqa: E402
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    WarpExecutorError,
    WarpTarget,
    make_warp_force_pos_frame,
    make_warp_force_pos_frame_with_target,
)
from pirateforce_foundation.gm.warp_target_record import (  # noqa: E402
    REASON_CHARACTER_MISMATCH,
    REASON_CHARACTER_UNREADABLE,
    REASON_FOREIGN_VALUE,
    REASON_NOT_CLEARED,
    REASON_NOTHING_PARKED,
    REASON_OK,
    SESSION_ATTRIBUTE,
    UNREADABLE_CHARACTER_ID,
    WARP_TARGET_MATCH_TOLERANCE,
    WarpTargetRecord,
    clear_warp_target,
    current_character_id,
    distance_to_target,
    position_matches_target,
    record_warp_target,
    take_warp_target,
    take_warp_target_with_reason,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

UNPROVEN_TEST_VERSION = 7


def f32(value: float) -> float:
    """What `legacy.f32tag` will store, computed independently of it."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


class FakePosition:
    def __init__(self, scene_id=2, x=0.0, y=0.0, z=0.0):
        self.scene_id = scene_id
        self.x = x
        self.y = y
        self.z = z


class FakeSelected:
    def __init__(self, identifier=41, position=None):
        self.id = identifier
        self.position = position


class FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class FakeSession:
    def __init__(self, character_id=41):
        self.foundation = FakeFoundation(FakeSelected(character_id))


class TargetIsTheFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_the_bytes_are_the_same_as_the_targetless_composer(self):
        command = parse_gm_command("warp 2 11865 6147")
        pc, frame, _target = make_warp_force_pos_frame_with_target(
            self.legacy, UNPROVEN_TEST_VERSION, command, 2, -3.5
        )
        expected_pc, expected_frame = make_warp_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, command, 2, -3.5
        )
        self.assertEqual(bytes(pc), bytes(expected_pc))
        self.assertEqual(bytes(frame), bytes(expected_frame))

    def test_the_target_is_the_wire_value_not_the_typed_value(self):
        # 11865.7 is not representable in binary32; the client will receive
        # 11865.6997... and a comparison against 11865.7 would charge that
        # gap to the client every time.
        command = parse_gm_command("warp 2 11865.7 6147.3")
        _pc, _frame, target = make_warp_force_pos_frame_with_target(
            self.legacy, UNPROVEN_TEST_VERSION, command, 2, -3.5
        )
        self.assertNotEqual(target.x, 11865.7)
        self.assertEqual(target.x, f32(11865.7))
        self.assertEqual(target.y, f32(6147.3))
        self.assertEqual(target.z, f32(-3.5))

    def test_the_target_carries_the_scene_the_frame_is_valid_in(self):
        command = parse_gm_command("warp 17 1 2")
        _pc, _frame, target = make_warp_force_pos_frame_with_target(
            self.legacy, UNPROVEN_TEST_VERSION, command, 17, 0.0
        )
        self.assertEqual(target.scene_id, 17)

    def test_the_decoded_payload_agrees_with_the_target(self):
        # The one property the whole comparison rests on: the numbers handed
        # to the reader are the numbers on the socket.
        command = parse_gm_command("warp 2 100.5 200.25")
        _pc, _frame, target = make_warp_force_pos_frame_with_target(
            self.legacy, UNPROVEN_TEST_VERSION, command, 2, 7.0
        )
        body = teleport_wire.decode_force_pos(
            teleport_wire.make_force_pos_payload(self.legacy, 100.5, 200.25, 7.0)
        )
        self.assertEqual((target.x, target.y, target.z), (body.x, body.y, body.z))

    def test_a_refused_warp_yields_no_target_because_it_yields_no_bytes(self):
        command = parse_gm_command("warp 3 100 200")
        with self.assertRaises(WarpExecutorError):
            make_warp_force_pos_frame_with_target(
                self.legacy, UNPROVEN_TEST_VERSION, command, 2, 0.0
            )

    def test_a_command_whose_coordinates_change_per_read_cannot_split(self):
        # The threat warp_executor's docstring already names: a hand-built
        # GmCommand accepted "regardless of source".  One validation pass
        # means the wire and the target read the SAME conversion, so a
        # coordinate that returns a new number on every __float__ cannot put
        # one value on the socket and another in the record.
        class Drifting:
            def __init__(self):
                self.reads = 0

            def __float__(self):
                self.reads += 1
                return 100.0 + self.reads

        class HandBuilt:
            name = "warp"

        drifting = Drifting()
        command = HandBuilt()
        command.args = (2, drifting, 200)
        _pc, frame, target = make_warp_force_pos_frame_with_target(
            self.legacy, UNPROVEN_TEST_VERSION, command, 2, 0.0
        )
        self.assertEqual(drifting.reads, 1)
        _expected_pc, expected_frame = teleport_wire.make_force_pos_frame(
            self.legacy, UNPROVEN_TEST_VERSION, target.x, target.y, target.z
        )
        self.assertEqual(bytes(frame), bytes(expected_frame))


class RecordLifetimeTests(unittest.TestCase):
    def setUp(self):
        self.target = WarpTarget(2, 100.0, 200.0, 30.0)
        self.session = FakeSession(character_id=41)

    def test_a_parked_target_comes_back_once_and_only_once(self):
        self.assertTrue(record_warp_target(self.session, self.target, 41))
        record = take_warp_target(self.session, 41)
        self.assertIsInstance(record, WarpTargetRecord)
        self.assertEqual(record.target, self.target)
        self.assertIsNone(take_warp_target(self.session, 41))

    def test_a_second_warp_replaces_the_first(self):
        second = WarpTarget(2, 300.0, 400.0, 30.0)
        record_warp_target(self.session, self.target, 41)
        record_warp_target(self.session, second, 41)
        record = take_warp_target(self.session, 41)
        self.assertEqual(record.target, second)

    def test_a_different_character_gets_nothing_and_the_record_is_dropped(self):
        # Warp, re-select, then walk: the second character's position must
        # not be measured against the first character's destination.
        record_warp_target(self.session, self.target, 41)
        self.assertIsNone(take_warp_target(self.session, 42))
        self.assertIsNone(take_warp_target(self.session, 41))

    def test_a_connection_with_no_character_is_matched_as_none(self):
        record_warp_target(self.session, self.target, None)
        self.assertIsNotNone(take_warp_target(self.session, None))

    def test_nothing_parked_is_none_not_a_crash(self):
        self.assertIsNone(take_warp_target(FakeSession(), 41))

    def test_a_foreign_value_in_the_attribute_is_refused_and_cleared(self):
        setattr(self.session, SESSION_ATTRIBUTE, ("warp", 1, 2))
        self.assertIsNone(take_warp_target(self.session, 41))
        self.assertIsNone(getattr(self.session, SESSION_ATTRIBUTE))

    def test_only_a_warp_target_can_be_parked(self):
        self.assertFalse(record_warp_target(self.session, (2, 1.0, 2.0, 3.0), 41))
        self.assertIsNone(take_warp_target(self.session, 41))

    def test_a_session_that_refuses_attributes_costs_a_record_not_a_crash(self):
        class Sealed:
            __slots__ = ()

        sealed = Sealed()
        self.assertFalse(record_warp_target(sealed, self.target, 41))
        self.assertIsNone(take_warp_target(sealed, 41))
        clear_warp_target(sealed)  # must not raise either

    def test_clear_is_safe_on_a_session_that_never_had_one(self):
        clear_warp_target(self.session)
        self.assertIsNone(take_warp_target(self.session, 41))

    def test_the_character_id_is_read_from_one_place(self):
        self.assertEqual(current_character_id(self.session), 41)
        self.assertIsNone(current_character_id(object()))

    def test_an_unreadable_id_is_not_the_same_answer_as_no_character(self):
        # pf-adversary: with both spelled `None`, two connections that each
        # fail to read an id compare EQUAL, and one GM's destination is handed
        # to another character -- the leak this module exists to prevent.
        self.assertIs(
            current_character_id(FakeSession(character_id="41")),
            UNREADABLE_CHARACTER_ID,
        )
        no_character = FakeSession()
        no_character.foundation.selected = None
        self.assertIsNone(current_character_id(no_character))

    def test_two_unreadable_ids_do_not_match_each_other(self):
        record_warp_target(self.session, self.target, UNREADABLE_CHARACTER_ID)
        record, reason = take_warp_target_with_reason(
            self.session, UNREADABLE_CHARACTER_ID
        )
        self.assertIsNone(record)
        self.assertEqual(reason, REASON_CHARACTER_UNREADABLE)

    def test_an_id_that_raises_when_read_costs_the_record_not_the_thread(self):
        class Exploding:
            position = None

            @property
            def id(self):
                raise RuntimeError("boom")

        session = FakeSession()
        session.foundation.selected = Exploding()
        self.assertIs(current_character_id(session), UNREADABLE_CHARACTER_ID)

    def test_a_session_that_swallows_the_write_is_reported_as_not_recorded(self):
        # Silently dropping the attribute raises nothing, so "the call did not
        # raise" is not evidence that anything was parked.
        class Swallowing:
            def __setattr__(self, name, value):
                pass

        session = Swallowing()
        self.assertFalse(record_warp_target(session, self.target, 41))

    def test_a_record_that_cannot_be_cleared_is_never_handed_out(self):
        # Consume-once has to hold even when the clear fails, or the same
        # record answers for a second frame.
        class RefusesClear:
            def __init__(self):
                object.__setattr__(self, "stored", None)

            def __setattr__(self, name, value):
                if value is None:
                    return
                object.__setattr__(self, "stored", value)

            def __getattr__(self, name):
                if name == SESSION_ATTRIBUTE:
                    return object.__getattribute__(self, "stored")
                raise AttributeError(name)

        session = RefusesClear()
        self.assertTrue(record_warp_target(session, self.target, 41))
        record, reason = take_warp_target_with_reason(session, 41)
        self.assertIsNone(record)
        self.assertEqual(reason, REASON_NOT_CLEARED)

    def test_every_not_comparable_state_says_which_one_it_was(self):
        # The reasons are the answer to "a permanent disagreement between the
        # two belts must not look like a GM who never typed /warp".
        empty = FakeSession()
        self.assertEqual(
            take_warp_target_with_reason(empty, 41)[1], REASON_NOTHING_PARKED
        )
        setattr(empty, SESSION_ATTRIBUTE, ("warp", 1, 2))
        self.assertEqual(
            take_warp_target_with_reason(empty, 41)[1], REASON_FOREIGN_VALUE
        )
        record_warp_target(self.session, self.target, 41)
        self.assertEqual(
            take_warp_target_with_reason(self.session, 42)[1],
            REASON_CHARACTER_MISMATCH,
        )
        record_warp_target(self.session, self.target, 41)
        self.assertEqual(
            take_warp_target_with_reason(self.session, 41)[1], REASON_OK
        )


class DistanceTests(unittest.TestCase):
    def setUp(self):
        self.target = WarpTarget(2, 100.0, 200.0, 30.0)

    def test_the_exact_point_is_distance_zero_and_a_match(self):
        position = FakePosition(2, 100.0, 200.0, 30.0)
        self.assertEqual(distance_to_target(self.target, position), 0.0)
        self.assertTrue(position_matches_target(self.target, position))

    def test_a_row_in_another_scene_is_not_comparable(self):
        # ForcePos carries no scene id, so a row in scene 3 cannot be the
        # result of a frame that was only valid in scene 2.
        position = FakePosition(3, 100.0, 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))
        self.assertFalse(position_matches_target(self.target, position))

    def test_a_z_only_difference_is_still_a_difference(self):
        position = FakePosition(2, 100.0, 200.0, 130.0)
        self.assertEqual(distance_to_target(self.target, position), 100.0)
        self.assertFalse(position_matches_target(self.target, position))

    def test_the_tolerance_is_a_boundary_not_a_suggestion(self):
        inside = FakePosition(2, 100.0 + WARP_TARGET_MATCH_TOLERANCE, 200.0, 30.0)
        outside = FakePosition(
            2, 100.0 + WARP_TARGET_MATCH_TOLERANCE * 2, 200.0, 30.0
        )
        self.assertTrue(position_matches_target(self.target, inside))
        self.assertFalse(position_matches_target(self.target, outside))
        self.assertTrue(
            position_matches_target(
                self.target, outside, tolerance=WARP_TARGET_MATCH_TOLERANCE * 3
            )
        )

    def test_binary32_rounding_can_never_be_what_fails_a_comparison(self):
        # The gap the tolerance has to swallow, at the owner's own test
        # coordinates, is about a thousandth of a unit.
        self.assertLess(abs(f32(11865.7) - 11865.7), WARP_TARGET_MATCH_TOLERANCE)
        target = WarpTarget(2, f32(11865.7), f32(6147.3), f32(-3.5))
        self.assertTrue(
            position_matches_target(target, FakePosition(2, 11865.7, 6147.3, -3.5))
        )

    def test_a_walking_gm_leaves_the_tolerance_immediately(self):
        # move_authority_hypothesis records 400-500 units between reports on
        # a continuous run, so a GM who walked cannot read as "still on the
        # point" for the one frame this record lives.
        position = FakePosition(2, 100.0 + 400.0, 200.0, 30.0)
        self.assertFalse(position_matches_target(self.target, position))

    def test_a_missing_coordinate_is_not_comparable(self):
        class Partial:
            scene_id = 2
            x = 100.0
            y = 200.0

        self.assertIsNone(distance_to_target(self.target, Partial()))
        self.assertFalse(position_matches_target(self.target, Partial()))

    def test_a_nan_coordinate_is_not_a_match(self):
        position = FakePosition(2, float("nan"), 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))
        self.assertFalse(position_matches_target(self.target, position))

    def test_an_infinite_coordinate_is_not_a_match(self):
        position = FakePosition(2, float("inf"), 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))
        self.assertFalse(position_matches_target(self.target, position))

    def test_a_squared_overflow_reads_as_not_comparable_not_as_close(self):
        position = FakePosition(2, 1e200, 1e200, 1e200)
        self.assertIsNone(distance_to_target(self.target, position))
        self.assertFalse(position_matches_target(self.target, position))

    def test_an_int_too_large_for_a_float_does_not_raise(self):
        # `isinstance(x, int)` admits arbitrary precision, and `float(10**400)`
        # raises OverflowError -- which pf-adversary reproduced escaping onto
        # the dispatch path from the line right above the guard that already
        # caught the same exception one operation later.
        position = FakePosition(2, 10 ** 400, 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))
        self.assertFalse(position_matches_target(self.target, position))

    def test_a_coordinate_that_raises_when_read_does_not_raise_here(self):
        class Exploding:
            scene_id = 2
            x = 100.0
            y = 200.0

            @property
            def z(self):
                raise RuntimeError("boom")

        self.assertIsNone(distance_to_target(self.target, Exploding()))

    def test_an_infinite_tolerance_does_not_turn_the_check_into_true(self):
        # A caller can widen the tolerance -- that is the point of the
        # keyword -- but not to the value that matches every comparable
        # position while still reading as a measurement.
        far = FakePosition(2, 1e6, 200.0, 30.0)
        self.assertFalse(
            position_matches_target(self.target, far, tolerance=float("inf"))
        )
        self.assertFalse(
            position_matches_target(self.target, far, tolerance=float("nan"))
        )
        self.assertFalse(
            position_matches_target(self.target, far, tolerance=-1.0)
        )
        self.assertFalse(
            position_matches_target(self.target, far, tolerance="1e9")
        )

    def test_a_boolean_is_not_a_coordinate(self):
        # True == 1.0 in Python arithmetic; a position field that is a bool
        # is a malformed row, not a point one unit from the origin.
        position = FakePosition(2, True, 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))

    def test_a_scene_id_that_is_not_an_int_is_not_comparable(self):
        position = FakePosition("2", 100.0, 200.0, 30.0)
        self.assertIsNone(distance_to_target(self.target, position))

    def test_a_non_target_is_refused_rather_than_measured(self):
        self.assertIsNone(
            distance_to_target((2, 100.0, 200.0, 30.0), FakePosition(2))
        )
        self.assertFalse(
            position_matches_target((2, 100.0, 200.0, 30.0), FakePosition(2))
        )

    def test_the_distance_is_euclidean_in_three_axes(self):
        position = FakePosition(2, 103.0, 204.0, 30.0)
        self.assertTrue(
            math.isclose(distance_to_target(self.target, position), 5.0)
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
