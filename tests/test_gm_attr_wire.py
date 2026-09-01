"""gm/attr_wire.py: field table integrity, byte-level composer correctness,
and the RawBlockCache fail-closed/lossless-preserve properties.

NONCLAIM (read before extending this file): nothing here sends a byte to a
real client.  `UPDATE_ATTR_VITAL_VERSION_CONFIRMED` is no longer
unconditionally `None` -- `VersionGateTests` pins the SCOPED exception
(`COO-DECISION 20260901_1847`, `/speed` sparse x=7 only) that flipped it to
`0` -- but that flip is not this module's own three-point unlock answering
itself: the full-block door (`build_named_field_update`) is not gated on
this constant at all (see `make_update_attr_frame`'s own docstring) and
condition (b) below is still open.  These tests exercise byte construction
only -- see attr_wire.py's module docstring "STATUS THIS ROUND" for the
full picture, including the still-open raw-block-source question this
module does not claim to have answered.
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.gm.attr_wire import (
    AC_ATTR_ID,
    BY_NAME,
    BY_X,
    DB_ATTRIBUTE_IDENTITY_BIT,
    FIELDS,
    SENSITIVE_FIELDS,
    UPDATE_ATTR_VITAL_ID,
    UPDATE_ATTR_VITAL_VERSION_CONFIRMED,
    AttrWireError,
    RawBlockCache,
    build_named_field_update,
    encode_block,
    encode_field,
    make_update_attr_frame,
    parse_value,
)

_KIND_WIDTH = {"u8": 1, "u16": 2, "u32": 4, "i32": 4, "f32": 4, "u64": 8}


class FieldTableShapeTests(unittest.TestCase):
    def test_55_fields_matching_the_proven_probe_table(self):
        self.assertEqual(len(FIELDS), 55)

    def test_x_values_are_1_through_55_contiguous_and_unique(self):
        xs = [f[0] for f in FIELDS]
        self.assertEqual(xs, list(range(1, 56)))

    def test_every_row_has_9_elements_in_the_documented_shape(self):
        for f in FIELDS:
            self.assertEqual(len(f), 9, msg=f"row x={f[0]} has {len(f)} elements")
            x, block, bit, offset, tag, kind, name, known, note = f
            self.assertIsInstance(x, int)
            self.assertIn(block, ("basic", "actor"))
            self.assertIsInstance(bit, int)
            self.assertGreater(bit, 0)
            self.assertIsInstance(offset, int)
            self.assertIsInstance(tag, int)
            self.assertIn(kind, ("u8", "u16", "u32", "i32", "f32", "u64", "wstr", "blob"))
            self.assertIsInstance(name, str)
            self.assertTrue(name)
            self.assertIsInstance(known, bool)
            self.assertIsInstance(note, str)

    def test_by_x_and_by_name_index_every_row_exactly_once(self):
        self.assertEqual(len(BY_X), 55)
        self.assertEqual(len(BY_NAME), 55)
        for f in FIELDS:
            self.assertIs(BY_X[f[0]], f)
            self.assertIs(BY_NAME[f[6]], f)

    def test_basic_mask_bits_are_a_power_of_two_and_unique_per_block(self):
        seen = {}
        for f in FIELDS:
            if f[1] != "basic":
                continue
            self.assertEqual(f[2] & (f[2] - 1), 0, msg=f"x={f[0]} bit not a power of two")
            self.assertNotIn(f[2], seen, msg=f"basic mask bit {f[2]:#x} reused by x={f[0]} and x={seen.get(f[2])}")
            seen[f[2]] = f[0]

    def test_actor_mask_bits_unique_except_the_two_documented_pairs(self):
        by_bit = {}
        for f in FIELDS:
            if f[1] != "actor":
                continue
            by_bit.setdefault(f[2], []).append(f[0])
        pairs = {frozenset(v) for v in by_bit.values() if len(v) == 2}
        singles = [v for v in by_bit.values() if len(v) == 1]
        collisions = [v for v in by_bit.values() if len(v) > 2]
        self.assertEqual(collisions, [])
        self.assertEqual(pairs, {frozenset({39, 40}), frozenset({41, 42})})
        # every non-paired x appears exactly once
        seen_singles = {v[0] for v in singles}
        self.assertEqual(len(seen_singles), len(singles))

    def test_sensitive_field_30_is_never_marked_known(self):
        self.assertIn(30, SENSITIVE_FIELDS)
        self.assertFalse(BY_X[30][7], "x=30 must stay known=False regardless of SENSITIVE_FIELDS")

    def test_sensitive_fields_is_a_subset_of_real_field_ids(self):
        for x in SENSITIVE_FIELDS:
            self.assertIn(x, BY_X)


class ParseValueTests(unittest.TestCase):
    def test_u16_in_range(self):
        self.assertEqual(parse_value("u16", "65535"), 65535)

    def test_u16_out_of_range_rejected(self):
        with self.assertRaises(AttrWireError):
            parse_value("u16", "65536")

    def test_u8_negative_rejected(self):
        with self.assertRaises(AttrWireError):
            parse_value("u8", "-1")

    def test_i32_negative_ok(self):
        self.assertEqual(parse_value("i32", "-5"), -5)

    def test_wstr_passthrough(self):
        self.assertEqual(parse_value("wstr", "hello"), "hello")

    def test_blob_hex(self):
        self.assertEqual(parse_value("blob", "0a0b"), b"\x0a\x0b")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(AttrWireError):
            parse_value("nope", "1")


class EncodeFieldByteExactTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_u16_field_matches_legacy_u16tag_directly(self):
        field = BY_NAME["level"]
        self.assertEqual(
            encode_field(self.legacy, field, 7),
            self.legacy.u16tag(field[4], 7),
        )

    def test_u32_field_matches_legacy_u32tag_directly(self):
        field = BY_NAME["hp_current"]
        self.assertEqual(
            encode_field(self.legacy, field, 100),
            self.legacy.u32tag(field[4], 100),
        )

    def test_u64_field_matches_legacy_qwordtag_directly(self):
        field = BY_NAME["cash"]
        self.assertEqual(
            encode_field(self.legacy, field, 10000),
            self.legacy.qwordtag(field[4], 10000),
        )

    def test_wstr_field_carries_tag_then_u32_byte_length_then_utf16le(self):
        field = BY_NAME["name"]
        out = encode_field(self.legacy, field, "Ann")
        expected_body = "Ann".encode("utf-16le")
        self.assertEqual(out, bytes([field[4]]) + struct.pack("<I", len(expected_body)) + expected_body)

    def test_f32_field_round_trips_via_struct(self):
        field = BY_NAME["death_timer"]
        out = encode_field(self.legacy, field, 2.5)
        self.assertEqual(out[0], field[4])
        self.assertEqual(struct.unpack("<f", out[1:])[0], 2.5)

    def test_blob_field_carries_raw_bytes_with_u32_length_header(self):
        field = BY_X[30]  # sensitive field, still byte-encodable at this layer
        out = encode_field(self.legacy, field, b"\x01\x02\x03")
        self.assertEqual(out, bytes([field[4]]) + struct.pack("<I", 3) + b"\x01\x02\x03")

    def test_out_of_range_u32_is_refused(self):
        field = BY_NAME["hp_current"]
        with self.assertRaises(AttrWireError):
            encode_field(self.legacy, field, 1 << 32)


class EncodeBlockTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_empty_values_still_carries_identity_and_zero_masks(self):
        body, basic_mask, actor_mask = encode_block(self.legacy, 0x11, 0x22, {})
        self.assertEqual(basic_mask, 0)
        self.assertEqual(actor_mask, 0)
        expected = (
            self.legacy.u8tag(0x0B, DB_ATTRIBUTE_IDENTITY_BIT)
            + bytes([0x32])
            + struct.pack("<II", 0x11, 0x22)
            + self.legacy.u16tag(0x12, 0)
            + self.legacy.qwordtag(0x32, 0)
            + self.legacy.u8tag(0x05, 1)
        )
        self.assertEqual(body, expected)

    def test_one_basic_field_sets_only_its_own_mask_bit(self):
        level_field = BY_NAME["level"]
        _body, basic_mask, actor_mask = encode_block(self.legacy, 1, 0, {level_field[0]: 5})
        self.assertEqual(basic_mask, level_field[2])
        self.assertEqual(actor_mask, 0)

    def test_one_actor_field_sets_only_its_own_mask_bit(self):
        str_field = BY_NAME["str"]
        _body, basic_mask, actor_mask = encode_block(self.legacy, 1, 0, {str_field[0]: 4})
        self.assertEqual(basic_mask, 0)
        self.assertEqual(actor_mask, str_field[2])

    def test_fields_are_emitted_in_ascending_x_order_within_each_block(self):
        level_x = BY_NAME["level"][0]
        hp_x = BY_NAME["hp_current"][0]
        self.assertLess(level_x, hp_x)
        body, _bm, _am = encode_block(
            self.legacy, 1, 0, {hp_x: 50, level_x: 3},
        )
        level_bytes = encode_field(self.legacy, BY_X[level_x], 3)
        hp_bytes = encode_field(self.legacy, BY_X[hp_x], 50)
        self.assertLess(body.find(level_bytes), body.find(hp_bytes))

    def test_paired_bit_39_without_40_is_refused(self):
        with self.assertRaises(AttrWireError):
            encode_block(self.legacy, 1, 0, {39: 0})

    def test_paired_bit_41_without_42_is_refused(self):
        with self.assertRaises(AttrWireError):
            encode_block(self.legacy, 1, 0, {42: 0})

    def test_paired_bits_together_both_encode(self):
        body, _bm, actor_mask = encode_block(self.legacy, 1, 0, {39: 1, 40: 2})
        self.assertEqual(actor_mask, BY_X[39][2])
        self.assertIn(encode_field(self.legacy, BY_X[39], 1), body)
        self.assertIn(encode_field(self.legacy, BY_X[40], 2), body)


class MakeUpdateAttrFrameTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_frame_wraps_body_in_ac_attr_wrapper_and_runtime_vitals_envelope(self):
        level_x = BY_NAME["level"][0]
        pc, frame = make_update_attr_frame(self.legacy, 1, 0, {level_x: 9})
        body, _bm, _am = encode_block(self.legacy, 1, 0, {level_x: 9})
        expected_payload = (
            self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, AC_ATTR_ID)
            + self.legacy.u32tag(0x14, len(body))
            + body
        )
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(UPDATE_ATTR_VITAL_ID, 0, expected_payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)

    def test_pc_carries_the_update_attr_vital_id(self):
        pc, _frame = make_update_attr_frame(self.legacy, 1, 0, {})
        self.assertIn(struct.pack("<H", UPDATE_ATTR_VITAL_ID), pc)


class RawBlockCacheTests(unittest.TestCase):
    def test_fresh_cache_is_not_captured(self):
        self.assertFalse(RawBlockCache().is_captured())

    def test_merged_with_before_capture_raises(self):
        with self.assertRaises(AttrWireError):
            RawBlockCache().merged_with({1: "x"})

    def test_capture_initial_marks_captured_and_stores_values(self):
        cache = RawBlockCache()
        cache.capture_initial({2: 5, 3: 100})
        self.assertTrue(cache.is_captured())
        self.assertEqual(cache.current_values(), {2: 5, 3: 100})

    def test_capture_initial_is_idempotent_latest_wins(self):
        cache = RawBlockCache()
        cache.capture_initial({2: 5})
        cache.capture_initial({2: 9, 3: 1})
        self.assertEqual(cache.current_values(), {2: 9, 3: 1})

    def test_merged_with_overlays_without_mutating_stored_values(self):
        cache = RawBlockCache()
        cache.capture_initial({2: 5, 3: 100})
        merged = cache.merged_with({2: 6})
        self.assertEqual(merged, {2: 6, 3: 100})
        self.assertEqual(cache.current_values(), {2: 5, 3: 100})  # unchanged

    def test_record_sent_replaces_the_cache_wholesale(self):
        cache = RawBlockCache()
        cache.capture_initial({2: 5})
        cache.record_sent({2: 5, 3: 200})
        self.assertEqual(cache.current_values(), {2: 5, 3: 200})

    def test_a_second_named_field_command_preserves_the_first_ones_value(self):
        """The lossless-preserve property this module CAN guarantee on its
        own: once this module has sent field A, sending field B later must
        not silently drop A back to nothing."""
        cache = RawBlockCache()
        level_x, hp_x = BY_NAME["level"][0], BY_NAME["hp_current"][0]
        cache.capture_initial({})
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        build_named_field_update(legacy, cache, 1, 0, level_x, 5)
        self.assertEqual(cache.current_values().get(level_x), 5)
        build_named_field_update(legacy, cache, 1, 0, hp_x, 80)
        # level must still be 5, not dropped, after the hp-only command
        self.assertEqual(cache.current_values().get(level_x), 5)
        self.assertEqual(cache.current_values().get(hp_x), 80)


class BuildNamedFieldUpdateTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_refuses_when_cache_never_captured(self):
        cache = RawBlockCache()
        level_x = BY_NAME["level"][0]
        with self.assertRaises(AttrWireError):
            build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)

    def test_refuses_unknown_x(self):
        cache = RawBlockCache()
        cache.capture_initial({})
        with self.assertRaises(AttrWireError):
            build_named_field_update(self.legacy, cache, 1, 0, 9999, 1)

    def test_refuses_sensitive_field_even_when_captured(self):
        cache = RawBlockCache()
        cache.capture_initial({})
        with self.assertRaises(AttrWireError):
            build_named_field_update(self.legacy, cache, 1, 0, 30, b"\x00")

    def test_refuses_every_field_marked_known_false(self):
        cache = RawBlockCache()
        cache.capture_initial({})
        unknown_xs = [f[0] for f in FIELDS if not f[7] and f[0] not in SENSITIVE_FIELDS]
        self.assertTrue(unknown_xs, "expected at least one known=False, non-sensitive field")
        for x in unknown_xs:
            field = BY_X[x]
            with self.assertRaises(AttrWireError, msg=f"x={x} ({field[6]}) should be refused"):
                build_named_field_update(self.legacy, cache, 1, 0, x, 0)

    def test_succeeds_for_a_known_field_and_returns_pc_and_frame(self):
        cache = RawBlockCache()
        cache.capture_initial({})
        level_x = BY_NAME["level"][0]
        pc, frame = build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)
        self.assertIsInstance(pc, bytes)
        self.assertIsInstance(frame, bytes)
        self.assertGreater(len(pc), 0)
        self.assertGreater(len(frame), 0)

    def test_success_updates_the_cache_via_record_sent(self):
        cache = RawBlockCache()
        cache.capture_initial({})
        level_x = BY_NAME["level"][0]
        build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)
        self.assertEqual(cache.current_values(), {level_x: 5})

    def test_every_known_non_sensitive_field_is_individually_composable(self):
        """Every field this round claims to support actually round-trips
        through the real composer with a real legacy module -- not just
        the one 'level' field the other tests happen to use."""
        known_xs = [f[0] for f in FIELDS if f[7] and f[0] not in SENSITIVE_FIELDS]
        self.assertGreater(len(known_xs), 20)
        for x in known_xs:
            field = BY_X[x]
            cache = RawBlockCache()
            cache.capture_initial({})
            sample = {
                "u8": 1, "u16": 2, "u32": 3, "i32": -1, "f32": 1.5,
                "u64": 4, "wstr": "x", "blob": b"\x00",
            }[field[5]]
            pc, frame = build_named_field_update(self.legacy, cache, 1, 0, x, sample)
            self.assertGreater(len(pc), 0, msg=f"x={x} ({field[6]})")
            self.assertGreater(len(frame), 0, msg=f"x={x} ({field[6]})")


class VersionGateTests(unittest.TestCase):
    def test_the_shipped_constant_is_zero_by_a_scoped_speed_exception(self):
        # Flipped None -> 0 by `COO-DECISION 2026-09-01T18:47+07:00`
        # (pf_bridge/notes_to_chief/20260901_1847_COO-DECISION-gm049-vital-
        # version-gate-scoped-exception-c.md), SCOPED to the `/speed` sparse
        # x=7 send site only -- see this constant's own comment in
        # attr_wire.py for the full reasoning (a convergence across two
        # independently-measured RE-105/RE-129 vitals, not a copy of
        # either). If this fails without that letter's reasoning landing in
        # attr_wire.py's own comment, someone flipped the general gate
        # instead of the scoped one -- read the comment before touching this
        # assertion.
        self.assertEqual(UPDATE_ATTR_VITAL_VERSION_CONFIRMED, 0)

    def test_the_full_block_door_does_not_read_this_constant_at_all(self):
        # The flip above does NOT by itself open `build_named_field_update`
        # (the full-block door `attr_wire.py`'s own "STATUS THIS ROUND"
        # three-point unlock still gates): `make_update_attr_frame`'s own
        # docstring says it is "not gated on
        # UPDATE_ATTR_VITAL_VERSION_CONFIRMED", and this constant becoming
        # non-None changes nothing about condition (b) (lossless
        # unnamed-field preservation), which is still open.  A composer that
        # started reading this constant to decide whether to compose would
        # make the scoped exception a silent general one.
        cache = RawBlockCache()
        cache.capture_initial({})
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        level_x = BY_NAME["level"][0]
        # Still composes freely regardless of the gate value -- this door was
        # never gated on it, and still is not.
        pc, frame = build_named_field_update(legacy, cache, 1, 0, level_x, 5)
        self.assertGreater(len(pc), 0)
        self.assertGreater(len(frame), 0)


if __name__ == "__main__":
    unittest.main()
