"""The 14.13 (d) check for ``AvatarAttr``, run against real client bytes
and against the corpus rows that name the fields.

Sources, and which is which:

* ``current/pf_login_game_server_v141.py:2224`` (frozen, chief's zone) --
  the walk the running server uses to slice the body out of the actor.
* ``pf_bridge/.../reference_codex_attr/PF_ATTR_FIELD_SEMANTICS.tsv``, class
  ``AvatarAttr`` orders 5..25 -- offsets, tags, widths, ``mask_bit`` and
  names.  Transcribed into ``world_avatar_attr.FIELDS``.
* ``get_preset_actor_wire()`` -> the v25 create submit captured from the
  real client.  The only real body in evidence.

WHAT THE FIRST DRAFT OF THIS FILE COULD NOT TEST, AND THIS ONE DOES.  The
captured body ships ``mask = 0xFFFFFFFF``.  With every bit set the byte
stream is identical under ANY permutation of the bit->field assignment, so
no round trip over that body can observe which bit carries which field --
pf-adversary proved it by reversing the frozen walker's twelve u32 branches
and watching the whole suite stay green.  The sparse-mask tests below are
the fix: a body carrying only one bit has a length and a tag that depend on
which field that bit is, so a permuted assignment goes red.
"""

import ast
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pf_preconditions import BRIDGE_ATTR_CORPUS

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.world_avatar_attr import (
    AVATAR_ATTR_ID,
    COMMON_FLAGS_IDENTITY_BIT,
    FIELDS,
    FROZEN_WALK,
    GENDER_FEMALE,
    LAST_DEFINED_MASK_BIT,
    MASK_OFFSET,
    TAG_ASTR,
    TAG_MASK_U32,
    TAG_S8,
    TAG_U32,
    TAG_U8,
    AvatarAttrDrift,
    build_body,
    check_frozen_walk_against_the_transcribed_rows,
    decode_avatar_attr,
    describe_avatar_body,
    encode_avatar_attr,
    field_for_bit,
    field_for_name,
    wire_order_matches_offset_order,
    with_named_fields,
)

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The bridge checkout, when this clone has one beside it.  Used to re-derive
# FIELDS from the corpus file itself rather than trusting the transcription.
# Taken FROM the precondition rather than spelled again here, so the path the
# guard tests and the path the test opens cannot drift apart.
#
# ONE CONSEQUENCE WORTH KNOWING (pf-adversary, round a2nvx9): because this
# assignment names BRIDGE_ATTR_CORPUS, the census's _guard_aliases() promotes
# CORPUS_TSV to an alias of the precondition, so a skip mentioning CORPUS_TSV
# would be COUNTED as a guarded use.  Both misuse directions were probed and
# both fail safe (an untokenised skip goes red at runtime while the static
# count goes red too) - but do not write a skip against CORPUS_TSV expecting
# it to be invisible.
CORPUS_TSV = BRIDGE_ATTR_CORPUS.paths[0]

CAPTURED_BODY_LENGTH = 103
CAPTURED_MASK = 0xFFFFFFFF
CAPTURED_BASE_FLAGS = 0xFF


#: The 21 rows, typed here a SECOND time, independently of the module's own
#: table.  This is the answer to the hole pf-adversary measured in round
#: a2nvx9: the only test that opens the corpus file needs the bridge sibling,
#: so on the Windows gate - the machine that decides "green" - nothing graded
#: the bit->name assignment at all.  Swapping n_SLOT_RHAND and n_SLOT_LHAND in
#: the module (both u32, both 0x002191C2 in the capture) left the whole
#: gate-shaped run byte-identical: 6174 passed, 72 skipped, exit 0.
#:
#: WHAT THIS PIN IS, AND WHAT IT IS NOT.  It is a second transcription, so it
#: cannot prove the corpus says this - only the guarded test above can, and
#: only where the corpus is present.  What it does is make an edit to the
#: module's table a TWO-file edit, on every machine, gate included.  A silent
#: permutation of the names is what it stops.
PINNED_ROWS = (
    # order, bit, offset, tag, width, structural_type, semantic_name
    (5, 0, 0x2C, TAG_U32, 4, "uint32", "n_DRESS_HAT"),
    (6, 1, 0x30, TAG_U32, 4, "uint32", "n_HRID"),
    (7, 2, 0x34, TAG_U32, 4, "uint32", "n_HDID"),
    (8, 3, 0x38, TAG_U32, 4, "uint32", "n_FCID"),
    (9, 4, 0x3C, TAG_U32, 4, "uint32", "n_ETID"),
    (10, 5, 0x40, TAG_U32, 4, "uint32", "n_DRESS_CHEST"),
    (11, 6, 0x44, TAG_U32, 4, "uint32", "n_DRESS_LEGGINGS"),
    (12, 7, 0x48, TAG_U32, 4, "uint32", "equip_projection_slot_0x000800"),
    (13, 8, 0x4C, TAG_U32, 4, "uint32", "equip_projection_slot_0x001000"),
    (14, 9, 0x50, TAG_U32, 4, "uint32", "equip_projection_slot_0x002000"),
    (15, 10, 0x54, TAG_U32, 4, "uint32", "n_SLOT_RHAND"),
    (16, 11, 0x58, TAG_U32, 4, "uint32", "n_SLOT_LHAND"),
    (17, 12, 0x5C, TAG_U8, 1, "uint8_enum", "n_GENDER_1_female_other_male"),
    (18, 13, 0x5D, TAG_S8, 1, "int8", "s_BODYRATIO_component_0_height"),
    (19, 14, 0x5E, TAG_S8, 1, "int8", "s_BODYRATIO_component_1_width"),
    (20, 15, 0x64, TAG_ASTR, None, "byte_string",
     "item_definition_key_to_packed_color_low24_pair_map_text"),
    (21, 16, 0x60, TAG_U8, 1, "uint8_flags",
     "avatar_presentation_behavior_flags__0x1_pair_map_application_gate__"
     "0x4_0x8_effect_suppress__0x10_scale_1_3"),
    (22, 17, 0x80, TAG_U32, 4, "uint32", "opaque_u32_delta_member"),
    (23, 18, 0x5F, TAG_U8, 1, "uint8_enum", "avatar_render_record_lookup_key"),
    (24, 19, 0x84, TAG_U8, 1, "uint8", "n_SKIN"),
    (25, 20, 0x88, TAG_U32, 4, "uint32", "equip_projection_slot_0x200000"),
)


class FieldTableIsPinnedOnEveryMachineTests(unittest.TestCase):
    """No precondition ON PURPOSE - this class runs on the gate.

    Everything here is graded on a single-repository checkout with no
    ``pf_bridge`` beside it, which is the machine that decides whether a pull
    request merges.
    """

    def test_the_module_table_matches_the_pinned_rows_slot_for_slot(self):
        self.assertEqual(len(FIELDS), len(PINNED_ROWS))
        for field, row in zip(FIELDS, PINNED_ROWS):
            with self.subTest(order=field.order):
                self.assertEqual(
                    (field.order, field.bit, field.offset, field.tag,
                     field.width, field.structural_type, field.name),
                    row,
                )

    def test_the_pin_is_not_vacuous(self):
        """The control for the test above: permute two names and it goes red.

        This is the exact mutation that stayed green before this class
        existed - two u32 slots carrying the same value in the only captured
        body, so no assertion over that body can separate them."""
        import pirateforce_foundation.world_avatar_attr as module

        original = module.FIELDS
        try:
            rows = list(original)
            right, left = rows[10], rows[11]
            rows[10] = type(right)(right.order, right.bit, right.offset,
                                   right.tag, right.width,
                                   right.structural_type, left.name)
            rows[11] = type(left)(left.order, left.bit, left.offset, left.tag,
                                  left.width, left.structural_type, right.name)
            module.FIELDS = tuple(rows)
            self.assertNotEqual(
                [f.name for f in module.FIELDS],
                [row[6] for row in PINNED_ROWS],
                "the permuted table must differ from the pin",
            )
        finally:
            module.FIELDS = original

    def test_every_pinned_name_is_unique(self):
        names = [row[6] for row in PINNED_ROWS]
        self.assertEqual(len(names), len(set(names)))

    def test_every_pinned_bit_is_used_once_and_the_run_has_no_gaps(self):
        bits = sorted(row[1] for row in PINNED_ROWS)
        self.assertEqual(bits, list(range(len(PINNED_ROWS))))


def _sample_value(field):
    """A distinct, in-range value for one field, for the sparse bodies."""
    if field.width is None:
        return b"pf" * (field.bit % 3)
    if field.width == 1:
        return (field.bit * 7 + 3) & 0xFF
    return 0x01000000 + field.bit


class AvatarAttrCheckTest(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.actor = self.legacy.get_preset_actor_wire()
        self.body = self.legacy.extract_avatar_attr_wire_from_actor(self.actor)

    # -- the check itself ---------------------------------------------------

    def test_the_frozen_walk_and_the_corpus_agree_slot_for_slot(self):
        ordered = check_frozen_walk_against_the_transcribed_rows()
        self.assertEqual(len(ordered), 21)
        self.assertEqual([f.bit for f in ordered], list(range(21)))
        self.assertEqual([f.order for f in ordered], list(range(5, 26)))

    def test_the_check_goes_red_when_the_frozen_walk_disagrees(self):
        """A tautological check would stay green.  Swap two slots of
        DIFFERENT width in the transcribed frozen walk and it must raise."""
        import pirateforce_foundation.world_avatar_attr as module

        original = module.FROZEN_WALK
        try:
            mutated = list(original)
            mutated[19], mutated[20] = mutated[20], mutated[19]  # u8 <-> u32
            module.FROZEN_WALK = tuple(mutated)
            with self.assertRaises(AvatarAttrDrift):
                check_frozen_walk_against_the_transcribed_rows()
        finally:
            module.FROZEN_WALK = original

    def test_the_check_goes_red_when_a_corpus_row_is_wrong(self):
        import pirateforce_foundation.world_avatar_attr as module

        original = module.FIELDS
        try:
            mutated = list(original)
            broken = mutated[19]
            mutated[19] = type(broken)(
                broken.order, broken.bit, broken.offset, TAG_U32, 4,
                "uint32", broken.name,
            )
            module.FIELDS = tuple(mutated)
            with self.assertRaises(AvatarAttrDrift):
                check_frozen_walk_against_the_transcribed_rows()
        finally:
            module.FIELDS = original

    def test_n_skin_is_bit_19_and_not_bit_20(self):
        """The defect the first draft shipped, pinned so it cannot return.

        ``n_SKIN`` is +0x84, u8, mask_bit 0x00080000 = bit 19.  Bit 20 is
        ``equip_projection_slot_0x200000`` at +0x88, a u32.  Reading skin off
        bit 20 hands back an equipment id."""
        skin = field_for_name("n_SKIN")
        self.assertEqual(skin.bit, 19)
        self.assertEqual(skin.offset, 0x84)
        self.assertEqual(skin.width, 1)
        self.assertEqual(field_for_bit(20).name, "equip_projection_slot_0x200000")
        self.assertEqual(field_for_bit(20).offset, 0x88)
        self.assertEqual(field_for_bit(20).width, 4)

    def test_the_wire_order_is_not_the_offset_order(self):
        """The assumption the first draft ran on, stated as a value.

        Orders 20/21 are +0x64 then +0x60, and 23/24/25 are +0x5F, +0x84,
        +0x88 -- so a derivation that laid the wire slots down as ascending
        dense offsets from +0x2C was wrong from order 20 onward."""
        self.assertFalse(wire_order_matches_offset_order())
        self.assertEqual(field_for_bit(15).offset, 0x64)
        self.assertEqual(field_for_bit(16).offset, 0x60)

    def test_the_transcription_matches_the_corpus_file_when_it_is_here(self):
        """Re-derive FIELDS from the TSV instead of trusting the copy."""
        BRIDGE_ATTR_CORPUS.require(self)
        rows = {}
        with CORPUS_TSV.open(encoding="utf-8", errors="replace") as handle:
            header = handle.readline().rstrip("\n").split("\t")
            index = {name: position for position, name in enumerate(header)}
            for line in handle:
                cells = line.rstrip("\n").split("\t")
                if len(cells) != len(header):
                    continue
                if cells[index["class"]] != "AvatarAttr":
                    continue
                order = cells[index["order"]]
                if not order.isdigit() or int(order) < 5:
                    continue
                rows[int(order)] = (
                    int(cells[index["offset"]], 16),
                    int(cells[index["tag"]], 16),
                    cells[index["storage_width"]],
                    int(cells[index["mask_bit"]], 16),
                    cells[index["structural_type"]],
                    cells[index["semantic_name"]],
                )
        self.assertEqual(len(rows), len(FIELDS))
        for field in FIELDS:
            with self.subTest(order=field.order):
                offset, tag, width, mask_bit, structural, name = rows[field.order]
                self.assertEqual(field.offset, offset)
                self.assertEqual(field.tag, tag)
                self.assertEqual(mask_bit, 1 << field.bit)
                self.assertEqual(field.structural_type, structural)
                self.assertEqual(field.name, name)
                if field.width is None:
                    self.assertEqual(width, "5+N_bytes")
                else:
                    self.assertEqual(int(width), field.width)

    # -- the bit identities, which only a sparse mask can pin ---------------

    def test_the_frozen_walker_slices_every_single_bit_body_exactly(self):
        """The test the first draft was missing.

        For each of the 21 bits, build a body carrying ONLY that bit, embed
        it in a synthetic actor object, and require the FROZEN walker to
        hand back exactly those bytes.  Under a permuted bit->field
        assignment the lengths stop matching, so this goes red where the
        all-ones capture cannot."""
        for field in FIELDS:
            with self.subTest(bit=field.bit, name=field.name):
                body = build_body((field.bit,), {field.bit: _sample_value(field)})
                actor = self._actor_around(body)
                self.assertEqual(
                    self.legacy.extract_avatar_attr_wire_from_actor(actor), body
                )
                self.assertEqual(encode_avatar_attr(decode_avatar_attr(body)), body)

    def test_the_frozen_walker_slices_mixed_sparse_bodies_exactly(self):
        for bits in ((0, 12, 20), (12, 13, 14), (15, 16), (19, 20), (1, 15, 19)):
            with self.subTest(bits=bits):
                values = {bit: _sample_value(field_for_bit(bit)) for bit in bits}
                body = build_body(bits, values)
                actor = self._actor_around(body)
                self.assertEqual(
                    self.legacy.extract_avatar_attr_wire_from_actor(actor), body
                )
                decoded = decode_avatar_attr(body)
                for bit in bits:
                    self.assertEqual(decoded.values[bit], values[bit])

    def test_a_single_bit_body_has_the_length_its_own_field_implies(self):
        """Length is the property that makes the sparse bodies bite."""
        prefix = 2 + 9 + 5  # flags, identity, mask
        for field in FIELDS:
            with self.subTest(bit=field.bit):
                value = _sample_value(field)
                body = build_body((field.bit,), {field.bit: value})
                if field.width is None:
                    expected = prefix + 1 + 4 + len(value)
                else:
                    expected = prefix + 1 + field.width
                self.assertEqual(len(body), expected)

    def test_the_wire_pins_each_bits_shape_and_not_its_identity(self):
        """The exact reach of the sparse-mask evidence, measured.

        Two bits whose slots have the same (tag, width) produce identical
        bytes when either one alone is set, so NO test over the wire can
        tell them apart -- swapping their names is invisible here.  Measured
        by pf-adversary reversing the frozen walker's twelve u32 branches:
        the suite stayed green, because that loop consumes one u32 per set
        bit regardless of which.  So the identity of the fourteen u32 slots
        rests entirely on the corpus ``mask_bit`` column (an IMAGE fact),
        never on this repository's bytes.  Pinned as a class table so the
        claim cannot quietly grow."""
        classes: dict[tuple[int, int | None], list[int]] = {}
        for field in FIELDS:
            classes.setdefault((field.tag, field.width), []).append(field.bit)
        self.assertEqual(
            {shape: sorted(bits) for shape, bits in classes.items()},
            {
                (TAG_U32, 4): [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 17, 20],
                (TAG_U8, 1): [12, 16, 18, 19],
                (TAG_S8, 1): [13, 14],
                (TAG_ASTR, None): [15],
            },
        )
        # And the demonstration: same shape -> identical single-bit bodies.
        for left, right in ((0, 17), (12, 19), (13, 14)):
            with self.subTest(pair=(left, right)):
                a = build_body((left,), {left: _sample_value(field_for_bit(left))})
                b = build_body((right,), {right: _sample_value(field_for_bit(left))})
                self.assertEqual(len(a), len(b))
                self.assertEqual(a[:2] + a[11:12], b[:2] + b[11:12])
        # Different shape -> the frozen walker cannot confuse them.  This is
        # the class the n_SKIN defect fell into, which is why it was findable.
        u8_body = build_body((19,), {19: 1})
        u32_body = build_body((20,), {20: 1})
        self.assertNotEqual(len(u8_body), len(u32_body))

    def _actor_around(self, avatar_body: bytes) -> bytes:
        """Build the exact CreateActorDataEx prefix the frozen walker reads.

        Transcribed from ``extract_avatar_attr_wire_from_actor`` itself:
        identity, selector, name, two u8, u32, two u16, an ascii string and a
        wide string -- then the AvatarAttr body."""
        v = self.legacy
        out = bytearray()
        out.append(0x32)
        out.extend(b"\x00" * 8)
        out.extend(v.u8tag(0x0B, 0))
        out.extend(v.wstrtag("A") if hasattr(v, "wstrtag") else _wstr("A"))
        out.extend(v.u8tag(0x0B, 0))
        out.extend(v.u8tag(0x0B, 0))
        out.extend(v.u32tag(0x19, 0))
        out.extend(v.u16tag(0x12, 0))
        out.extend(v.u16tag(0x12, 0))
        out.extend(_astr(b""))
        out.extend(_wstr(""))
        out.extend(avatar_body)
        return bytes(out)

    # -- the real capture ---------------------------------------------------

    def test_the_capture_is_the_body_the_running_code_slices(self):
        self.assertEqual(len(self.body), CAPTURED_BODY_LENGTH)
        self.assertEqual(self.actor.count(self.body), 1)

    def test_the_round_trip_is_byte_exact_on_the_capture(self):
        decoded = decode_avatar_attr(self.body)
        self.assertEqual(encode_avatar_attr(decoded), self.body)

    def test_the_captured_character_reads_back_as_a_named_avatar(self):
        decoded = decode_avatar_attr(self.body)
        self.assertEqual(decoded.base_flags, CAPTURED_BASE_FLAGS)
        self.assertEqual(decoded.mask, CAPTURED_MASK)
        self.assertIsNotNone(decoded.identity)
        self.assertEqual(decoded.gender, GENDER_FEMALE)
        self.assertEqual(decoded.body_ratio, (30, 30))
        self.assertEqual(decoded.skin, 1)
        self.assertEqual(decoded.colour_map_text, b"")
        self.assertEqual(decoded.named("n_DRESS_HAT"), 0)
        self.assertEqual(decoded.named("n_HRID"), 0x00114009)
        self.assertEqual(decoded.named("n_HDID"), 0x0010EFF0)
        self.assertEqual(decoded.named("n_FCID"), 0x0010F01A)
        self.assertEqual(decoded.named("n_ETID"), 0)
        self.assertEqual(decoded.named("n_DRESS_CHEST"), 0x0023187A)
        self.assertEqual(decoded.named("n_DRESS_LEGGINGS"), 0x0023187B)
        self.assertEqual(decoded.named("n_SLOT_RHAND"), 0x002191C2)
        self.assertEqual(decoded.named("n_SLOT_LHAND"), 0x002191C2)
        self.assertEqual(decoded.named("equip_projection_slot_0x200000"), 0)

    def test_the_capture_reports_both_kinds_of_undefined_set_bit(self):
        decoded = decode_avatar_attr(self.body)
        self.assertEqual(decoded.undefined_mask_bits, tuple(range(21, 32)))
        self.assertEqual(decoded.undefined_flag_bits, tuple(range(1, 8)))
        self.assertEqual(LAST_DEFINED_MASK_BIT, 20)

    def test_every_named_reading_is_backed_by_the_bytes_at_that_position(self):
        decoded = decode_avatar_attr(self.body)
        cursor = 2 + 9
        self.assertEqual(self.body[cursor], TAG_MASK_U32)
        cursor += 5
        for bit in range(12):
            self.assertEqual(self.body[cursor], TAG_U32)
            raw = struct.unpack_from("<I", self.body, cursor + 1)[0]
            self.assertEqual(decoded.values[bit], raw)
            cursor += 5
        self.assertEqual(self.body[cursor], TAG_U8)
        self.assertEqual(decoded.gender, self.body[cursor + 1])
        cursor += 2
        self.assertEqual(self.body[cursor], TAG_S8)
        cursor += 2
        self.assertEqual(self.body[cursor], TAG_S8)
        cursor += 2
        self.assertEqual(self.body[cursor], TAG_ASTR)

    def test_a_mutated_value_byte_changes_exactly_that_named_reading(self):
        decoded = decode_avatar_attr(self.body)
        offset = self.body.find(struct.pack("<I", 0x00114009))
        self.assertGreater(offset, 0)
        mutated = bytearray(self.body)
        struct.pack_into("<I", mutated, offset, 0x00DEAD01)
        after = decode_avatar_attr(bytes(mutated))
        self.assertEqual(after.named("n_HRID"), 0x00DEAD01)
        for field in FIELDS:
            if field.name == "n_HRID" or field.width is None:
                continue
            with self.subTest(name=field.name):
                self.assertEqual(after.named(field.name), decoded.named(field.name))

    def test_the_signed_rows_are_read_signed_because_the_corpus_says_int8(self):
        negative = with_named_fields(
            self.body, s_BODYRATIO_component_0_height=-7
        )
        decoded = decode_avatar_attr(negative)
        self.assertEqual(decoded.body_ratio[0], -7)
        self.assertEqual(decoded.raw("s_BODYRATIO_component_0_height"), 0xF9)
        self.assertEqual(decoded.body_ratio[1], 30)

    # -- refusals ----------------------------------------------------------

    def test_it_refuses_one_extra_byte_the_frozen_slice_would_not_notice(self):
        with self.assertRaises(AvatarAttrDrift):
            decode_avatar_attr(self.body + b"\x00")

    def test_it_refuses_a_truncated_body(self):
        for cut in (1, 2, 11, 16, 50, len(self.body) - 1):
            with self.subTest(cut=cut):
                with self.assertRaises(AvatarAttrDrift):
                    decode_avatar_attr(self.body[:cut])

    def test_it_refuses_a_tag_that_drifted(self):
        for position in (0, 11, 16):
            with self.subTest(position=position):
                broken = bytearray(self.body)
                broken[position] ^= 0xFF
                with self.assertRaises(AvatarAttrDrift):
                    decode_avatar_attr(bytes(broken))

    def test_it_refuses_a_mask_bit_set_with_no_value_behind_it(self):
        decoded = decode_avatar_attr(self.body)
        values = dict(decoded.values)
        del values[0]
        with self.assertRaises(AvatarAttrDrift):
            encode_avatar_attr(
                type(decoded)(
                    base_flags=decoded.base_flags,
                    identity=decoded.identity,
                    mask=decoded.mask,
                    values=values,
                    undefined_mask_bits=(),
                    undefined_flag_bits=(),
                )
            )

    def test_it_refuses_a_value_whose_mask_bit_is_clear(self):
        decoded = decode_avatar_attr(self.body)
        with self.assertRaises(AvatarAttrDrift):
            encode_avatar_attr(
                type(decoded)(
                    base_flags=decoded.base_flags,
                    identity=decoded.identity,
                    mask=decoded.mask & ~1,
                    values=dict(decoded.values),
                    undefined_mask_bits=(),
                    undefined_flag_bits=(),
                )
            )

    def test_it_refuses_to_add_a_field_the_body_does_not_carry(self):
        without_gender = build_body((0,), {0: 5})
        with self.assertRaises(AvatarAttrDrift):
            with_named_fields(without_gender, n_GENDER_1_female_other_male=0)

    def test_an_unknown_name_is_a_key_error_not_a_silent_no_op(self):
        with self.assertRaises(KeyError):
            field_for_name("n_NOT_A_FIELD")

    def test_a_body_with_no_identity_bit_round_trips_too(self):
        body = build_body((0,), {0: 9}, base_flags=0, identity=b"")
        decoded = decode_avatar_attr(body)
        self.assertIsNone(decoded.identity)
        self.assertEqual(encode_avatar_attr(decoded), body)

    # -- what a change would look like, without making one -----------------

    def test_changing_one_named_field_keeps_every_other_byte(self):
        new_value = 0xAABBCCDD
        changed = with_named_fields(self.body, n_DRESS_HAT=new_value)
        self.assertEqual(len(changed), len(self.body))
        differing = [
            index
            for index, (a, b) in enumerate(zip(self.body, changed))
            if a != b
        ]
        self.assertEqual(differing, list(range(differing[0], differing[0] + 4)))
        self.assertEqual(decode_avatar_attr(changed).named("n_DRESS_HAT"), new_value)

    def test_a_no_op_change_is_byte_identical(self):
        decoded = decode_avatar_attr(self.body)
        same = with_named_fields(
            self.body, n_GENDER_1_female_other_male=decoded.gender
        )
        self.assertEqual(same, self.body)

    # -- the GT-203 console line -------------------------------------------

    def test_the_gt203_console_line_is_ascii_and_names_every_field(self):
        line = describe_avatar_body(self.body)
        line.encode("ascii")
        line.encode("cp874")
        for field in FIELDS:
            self.assertIn(f"{field.name}=", line)
        self.assertIn("mask=0xFFFFFFFF", line)
        self.assertIn(f"len={CAPTURED_BODY_LENGTH}", line)
        self.assertIn("n_SKIN=1", line)

    def test_the_console_line_changes_when_the_bytes_change(self):
        changed = with_named_fields(self.body, n_DRESS_HAT=0xAABBCCDD)
        self.assertNotEqual(
            describe_avatar_body(changed), describe_avatar_body(self.body)
        )

    def test_the_attr_id_is_the_one_start_game_res_actually_tags(self):
        """Not "0x16A0 appears somewhere": the exact composition line."""
        source = (
            ROOT / "src" / "pirateforce_foundation" / "legacy_bridge.py"
        ).read_text(encoding="utf-8")
        self.assertIn(f"u16tag(0x12,0x{AVATAR_ATTR_ID:04X})+avatar", source)

    # -- rule 14.13 (d): one named caller, and nothing else -----------------
    #
    # THIS GUARD WAS "NOTHING MAY CALL IT" UNTIL 2026-09-04.  `COO-DECISION
    # 20260904_0446` points 1-2 lifted it for EXACTLY ONE caller -- the
    # character-creation path in `src/pirateforce_foundation/lifecycle.py`,
    # which decodes the body it just stored and hands the three starting-gear
    # slots to `persistence_class_id.resolve_class_id` so the class the player
    # picked stops being dropped (CORE-REQUEST of `pf_bridge/notes_to_chief/
    # 20260904_0423`, ordered by `PANYA-DECISION 20260904_0328` piece 1).
    #
    # The rest of Rule 14.13(d) stands unchanged and is what these two tests
    # measure: a SECOND file mentioning this module is still red, and the one
    # allowed file having quietly stopped calling it is red too, so the
    # exemption cannot rot into a hole nobody notices.
    THE_ONE_ALLOWED_CALLER = (
        Path("src") / "pirateforce_foundation" / "lifecycle.py"
    )

    def test_no_module_outside_this_file_mentions_this_module(self):
        """Two mechanisms, because pf-adversary broke the first one twice.

        The AST walk missed ``from . import world_avatar_attr`` (whose
        ``node.module`` is None, so only ``node.names`` carries the name) and
        ``importlib.import_module(...)`` (a Call, which it never looked at).
        A plain text scan catches both, and is the primary check here; the
        AST walk stays as a second opinion for the aliased-import shapes.
        The scan covers the frozen server and the tool directories too, not
        just the package.

        The single allowed caller is compared as a RESOLVED path, not as a
        name or a suffix: a second `lifecycle.py` anywhere else under these
        roots is an offender like any other file."""
        roots = [
            ROOT / "src" / "pirateforce_foundation",
            ROOT / "current",
            ROOT / "tools",
            ROOT / "migrations",
            ROOT / "scenarios",
        ]
        mine = {
            (ROOT / "src" / "pirateforce_foundation" / "world_avatar_attr.py"),
            Path(__file__).resolve(),
            (ROOT / self.THE_ONE_ALLOWED_CALLER).resolve(),
        }
        offenders = []
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.resolve() in mine:
                    continue
                if path.suffix not in {".py", ".json", ".sql"}:
                    continue
                text = path.read_text(encoding="utf-8", errors="replace")
                if "world_avatar_attr" in text:
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_the_one_allowed_caller_really_is_a_caller(self):
        """The exemption must not outlive the wiring it was granted for.

        If `lifecycle.py` stops calling this module -- the wiring reverted,
        the call moved to a third file, the decode replaced by a copy of the
        walk -- then the guard above is silently one file weaker than Rule
        14.13(d) says it is, with every test green.  This is the test that
        goes red instead, and it asks for the CALL, not merely for the name
        in a comment."""
        text = (ROOT / self.THE_ONE_ALLOWED_CALLER).read_text(encoding="utf-8")
        self.assertIn("world_avatar_attr", text)
        self.assertIn("world_avatar_attr.decode_avatar_attr(", text)

    def test_the_ast_second_opinion_sees_both_import_shapes(self):
        """Prove the AST helper bites before relying on it.

        ``from . import world_avatar_attr`` and ``import x as y`` are the two
        shapes the first version of this guard let through."""
        for snippet in (
            "from . import world_avatar_attr",
            "from .world_avatar_attr import with_named_fields",
            "import pirateforce_foundation.world_avatar_attr as w",
            "from pirateforce_foundation import world_avatar_attr",
        ):
            with self.subTest(snippet=snippet):
                self.assertTrue(_ast_mentions(ast.parse(snippet)))
        self.assertFalse(_ast_mentions(ast.parse("from . import store")))

    def test_no_module_in_the_package_imports_this_one_by_ast(self):
        """The second opinion, exempting the same single caller by PATH.

        `path.name == ...` is how the module itself is skipped above and it
        would be the wrong test for the exemption: a second `lifecycle.py`
        added under a subpackage would inherit the exemption by name alone.
        The allowed caller is compared as a resolved path for that reason.
        """
        package = ROOT / "src" / "pirateforce_foundation"
        allowed = (ROOT / self.THE_ONE_ALLOWED_CALLER).resolve()
        offenders = []
        for path in sorted(package.rglob("*.py")):
            if path.name == "world_avatar_attr.py":
                continue
            if path.resolve() == allowed:
                continue
            if _ast_mentions(ast.parse(path.read_text(encoding="utf-8"))):
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [])

    def test_the_one_allowed_caller_is_seen_by_the_ast_walk_too(self):
        """Both guards must agree on who the one caller is.

        If the exemption stayed in the text scan while `lifecycle.py` stopped
        importing the module, this asserts the disagreement instead of
        letting the two guards drift into disagreeing in silence.
        """
        tree = ast.parse(
            (ROOT / self.THE_ONE_ALLOWED_CALLER).read_text(encoding="utf-8")
        )
        self.assertTrue(_ast_mentions(tree))

    def test_the_slot_tables_stay_the_same_length(self):
        self.assertEqual(len(FIELDS), 21)
        self.assertEqual(len(FROZEN_WALK), 21)
        self.assertEqual(MASK_OFFSET, 0x28)
        self.assertEqual(COMMON_FLAGS_IDENTITY_BIT, 0x01)


def _ast_mentions(tree) -> bool:
    """True when the parsed module names ``world_avatar_attr`` in an import."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [alias.name for alias in node.names]
        else:
            continue
        if any("world_avatar_attr" in name for name in names):
            return True
    return False


def _astr(payload: bytes) -> bytes:
    return bytes([TAG_ASTR]) + struct.pack("<I", len(payload)) + payload


def _wstr(text: str) -> bytes:
    encoded = text.encode("utf-16le")
    return bytes([0x48]) + struct.pack("<I", len(encoded)) + encoded


if __name__ == "__main__":
    unittest.main()
