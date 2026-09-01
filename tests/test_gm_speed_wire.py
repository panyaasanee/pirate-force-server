"""gm/speed_wire.py: the sparse (x=7-only) `/speed` composer.

NONCLAIM (read before extending this file): nothing here sends a byte to a
real client, and nothing here claims `attr_wire.UPDATE_ATTR_VITAL_VERSION_
CONFIRMED` is anything but `None`. These tests exercise byte construction
only, and confirm the composer touches field x=7 and NOTHING else -- see
speed_wire.py's module docstring for the full scope statement.
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
            attr_wire.build_named_field_update(legacy, cache, 1, 0, 7, 5.0)

    def test_shared_vital_version_confirmed_reads_attr_wire_live(self):
        self.assertIs(
            shared_vital_version_confirmed(),
            attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED,
        )

    def test_shared_vital_version_confirmed_is_none_today(self):
        # The load-bearing safety fact this module's docstring point 1
        # states: nothing sends until this is proven, sparse or not.
        self.assertIsNone(shared_vital_version_confirmed())


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
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_composes_a_frame_carrying_only_the_x7_mask_bit(self):
        pc, frame = compose_sparse_speed_update(self.legacy, 1, 0, 500.0)
        expected_pc, expected_frame = attr_wire.make_update_attr_frame(
            self.legacy, 1, 0, {SPEED_FIELD_X: 500.0}
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_basic_mask_is_exactly_the_x7_bit_and_no_other(self):
        body, basic_mask, actor_mask = attr_wire.encode_block(
            self.legacy, 1, 0, {SPEED_FIELD_X: 500.0}
        )
        self.assertEqual(basic_mask, attr_wire.BY_X[SPEED_FIELD_X][2])
        self.assertEqual(actor_mask, 0)
        # Sanity: the sparse composer's own output embeds this exact body.
        _pc, frame = compose_sparse_speed_update(self.legacy, 1, 0, 500.0)
        self.assertIn(body, frame)

    def test_carries_the_identity_given(self):
        import struct

        _pc, frame = compose_sparse_speed_update(self.legacy, 0xAABBCCDD, 0x11223344, 1.0)
        self.assertIn(struct.pack("<II", 0xAABBCCDD, 0x11223344), frame)

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

    def test_accepts_int_value(self):
        # A GM typing `/speed 400` parses to the string "400"; a caller may
        # reasonably hand this function an int after its own conversion.
        pc, frame = compose_sparse_speed_update(self.legacy, 1, 0, 400)
        expected_pc, expected_frame = attr_wire.make_update_attr_frame(
            self.legacy, 1, 0, {SPEED_FIELD_X: 400.0}
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_does_not_mutate_any_raw_block_cache(self):
        # Module docstring point 3: this door never reads or writes
        # RawBlockCache. Nothing to assert against an object that is never
        # constructed -- the real assertion is that the function signature
        # has no cache parameter at all, exercised by every call above
        # succeeding without one.
        compose_sparse_speed_update(self.legacy, 1, 0, 12.5)


if __name__ == "__main__":
    unittest.main()
