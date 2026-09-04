"""gm/speed_wire.py: the sparse (x=7-only) `/speed` composer.

NONCLAIM (read before extending this file): nothing here sends a byte to a
real client.  `attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is no longer
unconditionally `None` -- `ScopeTests` pins the scoped exception
(`COO-DECISION 20260901_1847`) that flipped it to `0` for this door only --
but this module still never reads that value to decide whether to compose
(module docstring point 1); the gate lives at `chat_command_action.
_speed_action`, the one call site allowed to reach a real socket. These
tests exercise byte construction only, and confirm the composer touches
field x=7 and NOTHING else -- see speed_wire.py's module docstring for the
full scope statement.
"""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm import attr_wire
from pirateforce_foundation.gm.speed_wire import (
    SPEED_FIELD_NAME,
    SPEED_FIELD_X,
    SpeedWireError,
    compose_sparse_speed_update,
    parse_speed_value,
    shared_vital_version_confirmed,
)


class ScopeTests(unittest.TestCase):
    """The identity claims this module's docstring makes about x=7."""

    def test_speed_field_x_is_seven(self):
        self.assertEqual(SPEED_FIELD_X, 7)

    def test_speed_field_name_reads_through_attr_wire_by_x(self):
        self.assertEqual(SPEED_FIELD_NAME, attr_wire.BY_X[7][6])

    def test_field_seven_is_still_known_false_in_attr_wire(self):
        # This module must NEVER be the thing that quietly widens
        # attr_wire's own gate -- x=7 stays known=False there regardless of
        # what this sparse door does.
        self.assertFalse(attr_wire.BY_X[7][7])

    def test_attr_wire_build_named_field_update_still_refuses_x7(self):
        cache = attr_wire.RawBlockCache()
        cache.capture_initial({})
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        with self.assertRaises(attr_wire.AttrWireError):
            attr_wire.build_named_field_update(
                legacy, cache, 1, 0, 7, 5.0, character_id=7,
            )

    def test_shared_vital_version_confirmed_reads_attr_wire_live(self):
        self.assertIs(
            shared_vital_version_confirmed(),
            attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED,
        )

    def test_shared_vital_version_confirmed_is_zero_by_scoped_exception(self):
        # `COO-DECISION 2026-09-01T18:47+07:00` (pf_bridge/notes_to_chief/
        # 20260901_1847_COO-DECISION-gm049-vital-version-gate-scoped-
        # exception-c.md) flipped `attr_wire.UPDATE_ATTR_VITAL_VERSION_
        # CONFIRMED` None -> 0, SCOPED to exactly this door -- see that
        # constant's own comment in attr_wire.py for the reasoning (a
        # convergence across two independently-measured RE-105/RE-129
        # vitals, not a byte lifted from either). This module still never
        # gates ITSELF on the value (module docstring point 1) -- the gate
        # lives at the one call site allowed to reach a real socket
        # (`chat_command_action._speed_action`).
        self.assertEqual(shared_vital_version_confirmed(), 0)


class ParseSpeedValueTests(unittest.TestCase):
    def test_parses_ordinary_finite_value(self):
        self.assertEqual(parse_speed_value("5.0"), 5.0)

    def test_parses_integer_looking_text(self):
        self.assertEqual(parse_speed_value("400"), 400.0)

    def test_rejects_non_numeric_text(self):
        with self.assertRaises(SpeedWireError):
            parse_speed_value("fast")

    def test_rejects_nan(self):
        with self.assertRaises(SpeedWireError):
            parse_speed_value("nan")

    def test_rejects_infinite(self):
        for bad in ("inf", "-inf", "1e400"):
            with self.assertRaises(SpeedWireError):
                parse_speed_value(bad)

    def test_rejects_non_str_input(self):
        with self.assertRaises(SpeedWireError):
            parse_speed_value(5.0)  # type: ignore[arg-type]


class ComposeSparseSpeedUpdateTests(unittest.TestCase):
    """THIS DOOR IS CLOSED (`COO-DECISION 20260904_0345` item 2).

    ~~(b'') does not change this function's own composition~~ -- struck, not
    deleted.  That was true for exactly one round and COO withdrew it: the
    2026-09-03 06:46 approval of the `PF_SPEED_TRIAL` escape hatch predates
    `RE-222` (21:49), and `RE-222` Q0 says the client's apply is a
    full-object copy whose constructor zeroes every field first -- so the
    damage never depended on the number in x=7, only on the 54 rows this
    shape omits.  There is no safe value on a half block, so the function
    refuses instead of choosing one.

    WHAT THESE TESTS PIN NOW: the refusal is unconditional, it is a NAMED
    `SpeedWireError` (so `chat_command_action._speed_action`'s existing
    compose-refused branch routes it to a console line rather than a
    silent drop), and the value checks still run FIRST so a caller passing
    rubbish is told it passed rubbish.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_a_valid_value_no_longer_composes_anything(self):
        with self.assertRaises(SpeedWireError) as caught:
            compose_sparse_speed_update(self.legacy, 1, 0, 500.0)
        self.assertIn("20260904_0345", str(caught.exception))

    def test_the_refusal_covers_every_shape_that_used_to_send(self):
        for value in (500.0, 400, 1.0, 12.5, 0.0, -3.5):
            with self.subTest(value=value):
                with self.assertRaises(SpeedWireError):
                    compose_sparse_speed_update(self.legacy, 1, 0, value)

    def test_the_identity_no_longer_matters_because_no_frame_is_built(self):
        with self.assertRaises(SpeedWireError):
            compose_sparse_speed_update(self.legacy, 0xAABBCCDD, 0x11223344, 1.0)

    def test_the_frame_exit_would_refuse_this_shape_anyway(self):
        # DEFENCE IN DEPTH, MEASURED RATHER THAN ASSERTED IN A COMMENT: even
        # with this function's own refusal deleted, the shape it used to
        # build cannot become a frame -- `COO-DECISION 20260904_0345` item 1
        # put the wall at `make_update_attr_frame`.  A round that reopens
        # this door by accident still cannot ship the GT-218 shape.
        with self.assertRaises(attr_wire.AttrWireError):
            attr_wire.make_update_attr_frame(
                self.legacy, 1, 0, {SPEED_FIELD_X: 500.0}
            )

    def test_the_body_this_shape_used_to_carry_is_still_composable(self):
        # `encode_block` stays sparse-capable on purpose (item 1): the shape
        # is still MEASURABLE, which is how `test_gm_speed_shape_hold.py`
        # keeps GT-193's byte-level history.  Only the header is refused.
        body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 1, 0, {SPEED_FIELD_X: 500.0}
        )
        self.assertTrue(body)
        self.assertEqual(basic_mask, attr_wire.BY_X[SPEED_FIELD_X][2])
        self.assertEqual(actor_mask, 0)

    def test_rejects_nan(self):
        with self.assertRaises(SpeedWireError):
            compose_sparse_speed_update(self.legacy, 1, 0, float("nan"))

    def test_rejects_infinite(self):
        with self.assertRaises(SpeedWireError):
            compose_sparse_speed_update(self.legacy, 1, 0, float("inf"))

    def test_rejects_bool_even_though_it_is_an_int_subclass(self):
        with self.assertRaises(SpeedWireError):
            compose_sparse_speed_update(self.legacy, 1, 0, True)  # type: ignore[arg-type]

    def test_rejects_non_numeric_value(self):
        with self.assertRaises(SpeedWireError):
            compose_sparse_speed_update(self.legacy, 1, 0, "5.0")  # type: ignore[arg-type]

    def test_a_bad_value_is_told_it_is_a_bad_value_not_that_the_door_is_shut(self):
        # The two facts send an operator to two different places, so they
        # keep two different words (the same split `live_named_values` keeps
        # between `absent` and `unsendable`).
        with self.assertRaises(SpeedWireError) as caught:
            compose_sparse_speed_update(self.legacy, 1, 0, "5.0")  # type: ignore[arg-type]
        self.assertNotIn("20260904_0345", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
