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

import io
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
    LIVE_VALUE_READ_POINT,
    LOGIN_BYTES_READ_POINT,
    SEED_CAPTURED_CONSOLE_TOKEN,
    SEED_REFUSED_CONSOLE_TOKEN,
    SENSITIVE_FIELDS,
    UPDATE_ATTR_VITAL_ID,
    UPDATE_ATTR_VITAL_VERSION_CONFIRMED,
    AttrWireError,
    RawBlockCache,
    all_field_x,
    build_named_field_update,
    encode_block,
    encode_field,
    live_full_block_values,
    live_login_bytes,
    live_named_values,
    make_update_attr_frame,
    named_field_x,
    parse_value,
    seed_cache_from_live_values,
    unnamed_field_x,
    validate_field_value,
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
    """`encode_block` stays a general-purpose composer that accepts a
    partial `values` -- (b'')'s completeness guarantee is enforced at
    `build_named_field_update` instead (see `BuildNamedFieldUpdateCompleteness
    Tests` below and `encode_block`'s own docstring for why)."""

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

    def test_a_complete_block_also_still_composes(self):
        # (b'') callers DO pass a full block through this same function --
        # this pins that the general-purpose composer handles that shape
        # too, not only the sparse ones above.
        body, basic_mask, actor_mask = encode_block(self.legacy, 0x11, 0x22, _full_values())
        expected_basic_mask = 0
        expected_actor_mask = 0
        for field in FIELDS:
            if field[1] == "basic":
                expected_basic_mask |= field[2]
            else:
                expected_actor_mask |= field[2]
        self.assertEqual(basic_mask, expected_basic_mask)
        self.assertEqual(actor_mask, expected_actor_mask)
        self.assertTrue(body.startswith(self.legacy.u8tag(0x0B, DB_ATTRIBUTE_IDENTITY_BIT)))


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


class BuildNamedFieldUpdateCompletenessTests(unittest.TestCase):
    """(b'') (`COO-DECISION 20260904_0215`): the door THIS lane's named-field
    API opens must never compose a partial 0x309A block -- enforced at
    `build_named_field_update`'s cache check (widened this round from
    `named_field_x()` to `all_field_x()`), not inside `encode_block` (see
    that function's own docstring for why not).
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_mutant_a_cache_missing_exactly_one_row_is_refused(self):
        # THE MUTATION TEST `COO-DECISION 20260904_0215` ORDERED BY NAME,
        # aimed at this door: a cache missing exactly one FIELDS row must
        # refuse a compose, for every row in the table.
        level_x = BY_NAME["level"][0]
        for field in FIELDS:
            values = _full_values()
            del values[field[0]]
            cache = RawBlockCache()
            cache.capture_initial(values)
            with self.assertRaises(
                AttrWireError, msg=f"x={field[0]} ({field[6]}) missing alone should refuse"
            ):
                build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)

    def test_a_fully_seeded_cache_composes(self):
        cache = RawBlockCache()
        cache.capture_initial(_full_values())
        level_x = BY_NAME["level"][0]
        pc, frame = build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)
        self.assertGreater(len(pc), 0)
        self.assertGreater(len(frame), 0)


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
        # SEEDED IN FULL, not empty (pf-adversary `3qh50k` D10, widened by
        # `COO-DECISION 20260904_0215` from named-only to every FIELDS
        # row): the door refuses a cache that does not hold every row,
        # because composing any-but-all ZEROES the rest on the client.
        # This test's own subject -- A survives a later send of B -- is
        # unchanged by the completeness requirement.
        cache.capture_initial(_full_values())
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
        cache.capture_initial(_full_values())
        level_x = BY_NAME["level"][0]
        pc, frame = build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)
        self.assertIsInstance(pc, bytes)
        self.assertIsInstance(frame, bytes)
        self.assertGreater(len(pc), 0)
        self.assertGreater(len(frame), 0)

    def test_success_updates_the_cache_via_record_sent(self):
        cache = RawBlockCache()
        seeded = _full_values()
        cache.capture_initial(seeded)
        level_x = BY_NAME["level"][0]
        build_named_field_update(self.legacy, cache, 1, 0, level_x, 5)
        # The merged block is the seed with ONE row overridden -- the whole
        # point of (b''): a send carries every FIELDS row, not just the
        # typed one, so nothing the client reads gets zeroed by omission.
        self.assertEqual(cache.current_values(), {**seeded, level_x: 5})

    def test_every_known_non_sensitive_field_is_individually_composable(self):
        """Every field this round claims to support actually round-trips
        through the real composer with a real legacy module -- not just
        the one 'level' field the other tests happen to use."""
        known_xs = [f[0] for f in FIELDS if f[7] and f[0] not in SENSITIVE_FIELDS]
        self.assertGreater(len(known_xs), 20)
        for x in known_xs:
            field = BY_X[x]
            cache = RawBlockCache()
            cache.capture_initial(_full_values())
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
        cache.capture_initial(_full_values())
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        level_x = BY_NAME["level"][0]
        # Still composes freely regardless of the gate value -- this door was
        # never gated on it, and still is not.  (The cache is seeded in full
        # because of (b''), which is a different gate; see D10.)
        pc, frame = build_named_field_update(legacy, cache, 1, 0, level_x, 5)
        self.assertGreater(len(pc), 0)
        self.assertGreater(len(frame), 0)


class _Hooks:
    """A stand-in for the `lane_hooks` package, with or without either read
    point (b'') needs: `COO-DECISION 20260904_0047`'s named-value point and
    `COO-DECISION 20260904_0216`'s login-byte point."""

    def __init__(self, values=None, raises=None, login_values=None, login_raises=None):
        self._values = values
        self._raises = raises
        self._login_values = login_values
        # Defaults to `raises` so a caller testing "the whole world is
        # broken" does not have to say so twice.
        self._login_raises = raises if login_raises is None else login_raises

    def current_named_attr_values(self, character_id):
        if self._raises is not None:
            raise self._raises
        return self._values

    def current_login_attr_bytes(self, character_id):
        if self._login_raises is not None:
            raise self._login_raises
        return self._login_values


class _NoReadPointHooks:
    """The SHIPPED world: a `lane_hooks` package with no read point on it."""


def _complete_values():
    """A full, encodable value for every NAMED row (b'') requires a real
    value for -- `named_field_x()`, unchanged in shape by (b''), now
    includes x=9."""
    values = {}
    for x in named_field_x():
        kind = BY_X[x][5]
        if kind == "wstr":
            values[x] = "x"
        elif kind == "f32":
            values[x] = 1.5
        elif kind == "blob":
            values[x] = b"\x00"
        else:
            values[x] = 1
    return values


def _login_values():
    """A full, encodable value for every UNNAMED row (b'') requires a login
    byte for -- `unnamed_field_x()`, includes `SENSITIVE_FIELDS` (x=30)."""
    values = {}
    for x in unnamed_field_x():
        kind = BY_X[x][5]
        if kind == "wstr":
            values[x] = "y"
        elif kind == "f32":
            values[x] = 2.5
        elif kind == "blob":
            values[x] = b"\x01"
        else:
            values[x] = 2
    return values


def _full_values():
    """Every `FIELDS` row, named and unnamed together -- what (b'') asks a
    seeded `RawBlockCache`/`encode_block` call to hold in full."""
    return {**_complete_values(), **_login_values()}


class UnlockBPrimeSeedingTests(unittest.TestCase):
    """(b') of the unlock -- `COO-DECISION 20260904_0046` item 3.

    Every named row must carry a REAL value at send time; a row missing from
    the read point's answer is not "unchanged", it is ZERO on the client
    (full-object-copy apply, `RE-222` Q0), which is the `GT-218` crash in one
    frame.  So every test below is about one question: can a partial or
    unreadable answer reach the cache?
    """

    def capture(self, **kwargs):
        """Run the seeder with stderr captured; returns (ok, lines)."""
        stream = io.StringIO()
        ok = seed_cache_from_live_values(stream=stream, **kwargs)
        return ok, stream.getvalue()

    def test_the_shipped_world_refuses_because_chiefs_read_point_is_absent(self):
        # THE PATH THAT RUNS TODAY.  `lane_hooks.current_named_attr_values`
        # was ordered on 2026-09-04 and does not exist; every send must die
        # here, out loud, with no bytes and no cache.
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache, character_id=7, hooks=_NoReadPointHooks()
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())
        self.assertIn(SEED_REFUSED_CONSOLE_TOKEN, said)
        self.assertIn("no_read_point", said)

    def test_the_real_lane_hooks_package_still_has_no_read_point(self):
        # The same claim against the REAL package rather than a fake, so the
        # day chief lands it this test goes red and this lane finds out from
        # its own suite instead of from a letter.  When it does: delete this
        # test, keep the rest.
        from pirateforce_foundation import lane_hooks

        self.assertFalse(
            hasattr(lane_hooks, LIVE_VALUE_READ_POINT),
            "chief's read point landed -- (b') can now be satisfied; see"
            " attr_wire's module docstring",
        )

    def test_one_missing_named_row_refuses_the_whole_seed(self):
        # THE HEART OF (b').  A dict missing `cash` does not send "cash
        # unchanged" -- `encode_block` sets a bit only for keys present, and
        # an unset bit is a zero on the client.  Partial must cost a refusal.
        values = _complete_values()
        cash_x = BY_NAME["cash"][0]
        del values[cash_x]
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache, character_id=7, hooks=_Hooks(values)
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())
        self.assertIn("missing_named_rows", said)
        self.assertIn(str(cash_x), said)

    def test_a_present_but_unsendable_row_is_as_fatal_as_a_missing_one(self):
        # A read point that answers `None` for HP has not answered.  If this
        # passed validation the refusal would move to compose time, leaving a
        # cache holding a baseline no send can use.
        values = _complete_values()
        hp_x = BY_NAME["hp_current"][0]
        values[hp_x] = None
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache, character_id=7, hooks=_Hooks(values)
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())
        self.assertIn(str(hp_x), said)

    def test_a_raising_read_point_never_escapes_and_never_seeds(self):
        # This runs on the listener thread's dispatch path. v141's game
        # listener has no `except` around `state.dispatch`, so an escape here
        # takes the connection down, not just the command.
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache,
            character_id=7,
            hooks=_Hooks(raises=RuntimeError("boom")),
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())
        self.assertIn("read_point_raised_RuntimeError", said)
        self.assertNotIn("boom", said)

    def test_a_read_point_that_answers_with_the_wrong_type_refuses(self):
        for answer in (None, [], "1,2,3", 7):
            with self.subTest(answer=answer):
                cache = RawBlockCache()
                ok, said = self.capture(
                    cache=cache, character_id=7, hooks=_Hooks(answer)
                )
                self.assertFalse(ok)
                self.assertFalse(cache.is_captured())
                self.assertIn("not_a_mapping", said)

    def test_a_named_only_answer_still_refuses_because_the_login_point_is_missing(self):
        # (b'') needs BOTH sources; a `_Hooks` with only the named point
        # answered is still the shipped world for the second one.
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache, character_id=7, hooks=_Hooks(_complete_values())
        )
        self.assertFalse(ok, said)
        self.assertFalse(cache.is_captured())
        self.assertIn("not_a_mapping", said)

    def test_a_complete_answer_from_both_sources_seeds_every_field_row(self):
        cache = RawBlockCache()
        ok, said = self.capture(
            cache=cache,
            character_id=7,
            hooks=_Hooks(_complete_values(), login_values=_login_values()),
        )
        self.assertTrue(ok, said)
        self.assertTrue(cache.is_captured())
        self.assertEqual(sorted(cache.current_values()), sorted(all_field_x()))
        self.assertIn(SEED_CAPTURED_CONSOLE_TOKEN, said)

    def test_extra_keys_from_the_read_point_can_never_set_an_unknown_bit(self):
        # A read point that over-answers must not widen what this module
        # sends.  An unknown row's bit carries a value nobody has confirmed
        # the meaning of; x=30 is SENSITIVE_FIELDS outright.
        values = _complete_values()
        unknown_x = next(f[0] for f in FIELDS if not f[7] and f[0] not in SENSITIVE_FIELDS)
        values[unknown_x] = 1
        for sensitive_x in SENSITIVE_FIELDS:
            values[sensitive_x] = b"\x00"
        seeded = live_named_values(7, hooks=_Hooks(values))
        self.assertNotIn(unknown_x, seeded)
        for sensitive_x in SENSITIVE_FIELDS:
            self.assertNotIn(sensitive_x, seeded)
        self.assertEqual(sorted(seeded), sorted(named_field_x()))

    def test_no_sensitive_row_is_ever_required_by_b_prime(self):
        # Today the two sets do not overlap because x=30 is `known=False`.
        # The subtraction in `named_field_x` is what keeps that true if an RE
        # result ever renames it: x=30's own row comment says it must never
        # be settable "even once this field is renamed True".
        for sensitive_x in SENSITIVE_FIELDS:
            self.assertNotIn(sensitive_x, named_field_x())

    def test_the_console_lines_are_ascii(self):
        # The bridge console is cp874; a non-ASCII byte in a token an
        # attended round greps is a line that lane cannot read back.
        cache = RawBlockCache()
        _, said = self.capture(
            cache=cache, character_id="GMก", hooks=_NoReadPointHooks()
        )
        self.assertEqual(said, said.encode("ascii").decode())

    def test_seeding_sends_nothing_and_leaves_both_gates_where_they_were(self):
        # NONCLAIM IN TEST FORM: this round prepares a consumer; it does not
        # open a door.  The full-block door still refuses an unknown row, and
        # still refuses an unseeded cache.
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        unknown_x = next(f[0] for f in FIELDS if not f[7] and f[0] not in SENSITIVE_FIELDS)
        cache = RawBlockCache()
        seed_cache_from_live_values(
            cache, 7, hooks=_Hooks(_complete_values()), stream=io.StringIO()
        )
        with self.assertRaises(AttrWireError):
            build_named_field_update(legacy, cache, 1, 0, unknown_x, 1)
        with self.assertRaises(AttrWireError):
            build_named_field_update(
                legacy, RawBlockCache(), 1, 0, BY_NAME["level"][0], 5
            )


class LiveLoginBytesTests(unittest.TestCase):
    """`live_login_bytes` -- the SECOND half of (b'') (`COO-DECISION
    20260904_0215` item 1, `20260904_0216`): every `known=False` row's
    login byte, or a named refusal.  Mirrors `UnlockBPrimeSeedingTests`'
    shape for `live_named_values`, against the not-yet-built second point.
    """

    def test_the_shipped_world_refuses_because_the_login_point_is_absent(self):
        with self.assertRaises(AttrWireError) as caught:
            live_login_bytes(7, hooks=_NoReadPointHooks())
        self.assertIn("no_login_byte_read_point", str(caught.exception))

    def test_the_real_lane_hooks_package_still_has_no_login_read_point(self):
        # Same shape as `live_named_values`'s own canary test: the day
        # chief lands this one (under this name or another -- see
        # `LOGIN_BYTES_READ_POINT`'s own comment), this test goes red and
        # this lane finds out from its own suite.
        from pirateforce_foundation import lane_hooks

        self.assertFalse(hasattr(lane_hooks, LOGIN_BYTES_READ_POINT))

    def test_one_missing_unnamed_row_refuses_the_whole_answer(self):
        values = _login_values()
        wstr_b0_x = BY_NAME["wstr_B0"][0]
        del values[wstr_b0_x]
        with self.assertRaises(AttrWireError) as caught:
            live_login_bytes(7, hooks=_Hooks(login_values=values))
        self.assertIn("missing_login_rows", str(caught.exception))
        self.assertIn(str(wstr_b0_x), str(caught.exception))

    def test_a_present_but_unsendable_row_is_as_fatal_as_a_missing_one(self):
        values = _login_values()
        values[BY_NAME["wstr_B0"][0]] = 12345  # wstr row given a non-str
        with self.assertRaises(AttrWireError) as caught:
            live_login_bytes(7, hooks=_Hooks(login_values=values))
        self.assertIn("unsendable", str(caught.exception))

    def test_a_read_point_that_answers_with_the_wrong_type_refuses(self):
        with self.assertRaises(AttrWireError) as caught:
            live_login_bytes(7, hooks=_Hooks(login_values="not a dict"))
        self.assertIn("not_a_mapping", str(caught.exception))

    def test_sensitive_field_30_is_covered_by_the_login_point_not_refused(self):
        # x=30 is `SENSITIVE_FIELDS` -- this lane may never let a caller
        # CHOOSE its value, but (b'') still needs SOME byte for it in every
        # send, and the login byte is that byte.  `unnamed_field_x()`
        # includes it on purpose (see that function's own docstring).
        self.assertIn(30, unnamed_field_x())
        seeded = live_login_bytes(7, hooks=_Hooks(login_values=_login_values()))
        self.assertIn(30, seeded)

    def test_a_complete_answer_seeds_exactly_the_unnamed_rows_and_no_others(self):
        seeded = live_login_bytes(7, hooks=_Hooks(login_values=_login_values()))
        self.assertEqual(sorted(seeded), sorted(unnamed_field_x()))

    def test_extra_keys_are_dropped_not_refused(self):
        values = _login_values()
        values[BY_NAME["level"][0]] = 99  # a NAMED row has no business here
        seeded = live_login_bytes(7, hooks=_Hooks(login_values=values))
        self.assertNotIn(BY_NAME["level"][0], seeded)


class LiveFullBlockValuesTests(unittest.TestCase):
    """`live_full_block_values` -- (b'') combined: both sources must
    answer, or the whole block refuses (`COO-DECISION 20260904_0215` item
    1: "no byte source for any row = the door refuses the whole thing")."""

    def test_named_point_missing_refuses_before_the_login_point_is_even_asked(self):
        with self.assertRaises(AttrWireError) as caught:
            live_full_block_values(7, hooks=_NoReadPointHooks())
        # `no_read_point` is `live_named_values`'s own reason string; if
        # this ever said `no_login_byte_read_point` instead, the two
        # sources are being queried in the wrong order.
        self.assertIn("no_read_point", str(caught.exception))

    def test_named_point_answers_but_login_point_is_absent_refuses(self):
        with self.assertRaises(AttrWireError) as caught:
            live_full_block_values(7, hooks=_Hooks(_complete_values()))
        self.assertIn("not_a_mapping", str(caught.exception))

    def test_both_sources_answering_yields_exactly_all_field_x(self):
        combined = live_full_block_values(
            7, hooks=_Hooks(_complete_values(), login_values=_login_values())
        )
        self.assertEqual(sorted(combined), sorted(all_field_x()))

    def test_named_and_unnamed_rows_never_collide(self):
        # If this ever failed, `named_field_x()`/`unnamed_field_x()` would
        # no longer partition `FIELDS`, and `live_full_block_values`'s own
        # internal assertion would already have caught it -- this test
        # names the property in one place a reader does not have to derive.
        self.assertEqual(set(named_field_x()) & set(unnamed_field_x()), set())
        self.assertEqual(set(named_field_x()) | set(unnamed_field_x()), set(all_field_x()))


class AdversaryFindingsRound3qh50kTests(unittest.TestCase):
    """The four defects pf-adversary MEASURED in this round's first draft.

    Each test fails if its fix is reverted. They are grouped so a future
    round reading a regression here can find the finding that bought it.
    """

    def setUp(self):
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def test_d8_a_float_the_encoder_cannot_pack_is_never_blessed(self):
        # MEASURED: x=8 `death_timer` is the only known=True f32 row, so it
        # is a REQUIRED row. `validate_field_value` blessed 1e40 and
        # `struct.pack` then raised OverflowError mid-compose -- verbatim
        # the outcome the validator's docstring promises is impossible, and
        # OverflowError is not caught by `except AttrWireError`.
        field = BY_NAME["death_timer"]
        with self.assertRaises(AttrWireError):
            validate_field_value(field, 1e40)
        with self.assertRaises(AttrWireError):
            encode_field(self.legacy, field, 1e40)
        values = _complete_values()
        values[field[0]] = 1e40
        cache = RawBlockCache()
        ok = seed_cache_from_live_values(
            cache, 7, hooks=_Hooks(values), stream=io.StringIO()
        )
        self.assertFalse(ok)
        self.assertFalse(cache.is_captured())

    def test_d8_an_unbounded_string_is_never_blessed(self):
        field = BY_NAME["name"]
        with self.assertRaises(AttrWireError):
            validate_field_value(field, "A" * 100000)
        with self.assertRaises(AttrWireError):
            encode_field(self.legacy, field, "A" * 100000)

    def test_d9_the_read_back_checks_the_content_not_the_flag(self):
        # MEASURED: a cache whose `capture_initial` stored ONE row got
        # `seed_...` returning True and a console line saying
        # `rows=26` -- both compared against the function's own input
        # instead of against what the cache actually holds.
        class LyingCache(RawBlockCache):
            def capture_initial(self, values):
                super().capture_initial({2: 5})

        cache = LyingCache()
        stream = io.StringIO()
        ok = seed_cache_from_live_values(
            cache,
            "char",
            hooks=_Hooks(_complete_values(), login_values=_login_values()),
            stream=stream,
        )
        said = stream.getvalue()
        self.assertFalse(ok)
        self.assertIn(SEED_REFUSED_CONSOLE_TOKEN, said)
        self.assertIn("capture_did_not_hold", said)
        self.assertNotIn(SEED_CAPTURED_CONSOLE_TOKEN, said)

    def test_d10_the_door_itself_refuses_a_cache_that_does_not_satisfy_b_double_prime(self):
        # THE FINDING THAT CHANGED THIS ROUND'S SHAPE, WIDENED BY (b'')
        # (`COO-DECISION 20260904_0215`). `capture_initial` is public and
        # unvalidated, and `COO-DECISION 20260904_0046` item 2 names LANE-B's
        # Door B as a second consumer of chief's read point -- ordered to
        # call the function the seeding helper does not gate. A peer lane
        # doing exactly what it was told, with a hook that omits `cash` for
        # a NULL-cash row, would compose an incomplete block and the
        # client's full-object copy would zero the missing one. So the
        # completeness question is asked at the door, where every consumer
        # must pass -- now against every FIELDS row, not only named ones.
        values = _full_values()
        del values[BY_NAME["cash"][0]]
        cache = RawBlockCache()
        cache.capture_initial(values)
        self.assertTrue(cache.is_captured())
        with self.assertRaises(AttrWireError) as caught:
            build_named_field_update(
                self.legacy, cache, 1, 0, BY_NAME["hp_current"][0], 80
            )
        self.assertIn("(b''", str(caught.exception))
        self.assertIn(str(BY_NAME["cash"][0]), str(caught.exception))

    def test_d10_an_over_seeded_cache_is_refused_too(self):
        # The other direction: a cache carrying a row (b'') does not name
        # would set a mask bit for a field nobody has confirmed the meaning
        # of. `!=` rather than `issubset` is what refuses both.
        values = _complete_values()
        values[next(f[0] for f in FIELDS if not f[7] and f[0] not in SENSITIVE_FIELDS)] = 1
        cache = RawBlockCache()
        cache.capture_initial(values)
        with self.assertRaises(AttrWireError):
            build_named_field_update(
                self.legacy, cache, 1, 0, BY_NAME["level"][0], 5
            )

    def test_d13_absent_and_unsendable_rows_are_reported_apart(self):
        values = _complete_values()
        absent_x = BY_NAME["cash"][0]
        unsendable_x = BY_NAME["hp_current"][0]
        del values[absent_x]
        values[unsendable_x] = None
        stream = io.StringIO()
        seed_cache_from_live_values(
            RawBlockCache(), 7, hooks=_Hooks(values), stream=stream
        )
        said = stream.getvalue()
        self.assertIn(f"absent={absent_x}", said)
        self.assertIn(f"unsendable={unsendable_x}", said)


class ValidatorIsOneAnswerTests(unittest.TestCase):
    """`validate_field_value` split out of `encode_field`, which now calls it.

    Two copies of these bounds would be two answers to keep in agreement, and
    the failure mode is a value the seeder blessed and the encoder refused
    mid-compose.
    """

    def test_the_encoder_and_the_seeder_agree_on_every_kind(self):
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        bad = {
            "u8": 0x100, "u16": 0x10000, "u32": 0x100000000,
            "u64": 1 << 64, "i32": 1 << 31, "f32": "nope",
            "wstr": 7, "blob": "nope",
        }
        for field in FIELDS:
            kind = field[5]
            with self.subTest(x=field[0], kind=kind):
                value = bad[kind]
                with self.assertRaises(AttrWireError):
                    validate_field_value(field, value)
                with self.assertRaises(AttrWireError):
                    encode_field(legacy, field, value)

    def test_a_bad_f32_or_blob_is_an_attrwireerror_not_a_bare_typeerror(self):
        # Both used to escape as `TypeError` from `float()`/`bytes()` -- the
        # one exception class this module's callers do not catch by name.
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        f32_field = next(f for f in FIELDS if f[5] == "f32")
        blob_field = next(f for f in FIELDS if f[5] == "blob")
        with self.assertRaises(AttrWireError):
            encode_field(legacy, f32_field, object())
        with self.assertRaises(AttrWireError):
            encode_field(legacy, blob_field, object())

    def test_a_bool_is_not_an_integer_value_for_the_wire(self):
        # `True` is an `int` subclass and would encode as 1 for a level or an
        # HP -- a read point returning a flag where a number belongs must be
        # refused, not silently sent.
        level_field = BY_NAME["level"]
        with self.assertRaises(AttrWireError):
            validate_field_value(level_field, True)


if __name__ == "__main__":
    unittest.main()
