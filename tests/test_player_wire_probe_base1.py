"""CORE-REQUEST-023 "probe base 1" widening: movement speed now rides on the
player login ``ActorAttr``, on top of the class+level CORE-REQUEST-023 already
wired.

This file drives the real ``player_wire`` functions (no reimplementation of
the codec) and asserts:

  * the frozen, class-less projections (``make_actor_attr_with_name`` /
    ``make_actor_attr_with_basic_faction``) are byte-for-byte unchanged --
    the other lanes that crosscheck their own pinned bytes against them
    still see exactly what NAME-002 / GT-032 proved;
  * the class+level-carrying projections
    (``make_actor_attr_with_name_and_class`` /
    ``make_actor_attr_with_name_class_and_faction``) now additionally carry
    movement speed, at the exact offset/tag/mask bit report
    PF_STATS_PROG001 section 4 pins (same bit mob_death.py already wires for
    field mobs), in strict ascending mask-bit order;
  * the faction-carrying variant's length delta against the plain variant
    stays exactly 5 bytes (one ``u32tag`` faction field) -- the invariant
    ``runtime.py``'s ``NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA`` guard relies
    on -- proving the new field was added symmetrically to both branches;
  * MP current/max and STR/CON/DEX/INT/PER are deliberately NOT emitted --
    this repo has no committed source for a level-1 Gladiator's actual MP or
    ability values (see player_wire.py's module docstring), and the wire
    POSITIONS for those fields (also proven, just not wired to any value)
    match the independent field table this repo already ships
    (stats_progression_hypothesis.PROGRESSION_FIELDS).
"""
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.npc_hostile_hypothesis import (
    NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA,
)
from pirateforce_foundation.player_wire import (
    PLAYER_LOGIN_CLASS_ID,
    PLAYER_LOGIN_LEVEL,
    PLAYER_LOGIN_MOVEMENT_SPEED,
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
    make_actor_attr_with_name_and_class,
    make_actor_attr_with_name_class_and_faction,
)
from pirateforce_foundation.stats_progression_hypothesis import PROGRESSION_FIELDS

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

IDENTITY_LO = 0x10010001
IDENTITY_HI = 0
SCENE_ID = 1
SCENE_SEQ = 0
NAME = "test01"


class _LegacyCase(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)


class FrozenBaselineUnchangedTests(_LegacyCase):
    """The two class-less projections are untouched by this widening."""

    def test_make_actor_attr_with_name_is_byte_for_byte_unchanged(self):
        actor = make_actor_attr_with_name(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        identity = bytes([0x32]) + struct.pack("<II", IDENTITY_LO, IDENTITY_HI)
        expected = (
            self.legacy.u8tag(0x0B, 1)
            + identity
            + self.legacy.u16tag(0x12, 0x030C)  # 0x000C | 0x0100 | 0x0200
            + self.legacy.u32tag(0x14, 100)
            + self.legacy.u32tag(0x14, 100)
            + self.legacy.u16tag(0x12, SCENE_ID)
            + bytes([0x32]) + struct.pack("<Q", SCENE_SEQ)
            + bytes([0x32]) + struct.pack("<II", 0x01000800, 0)
            + self.legacy.u8tag(0x05, 1)
            + bytes([0x32]) + struct.pack("<Q", self.legacy.V116_INITIAL_CASH)
            + self.legacy.wstr_tag(NAME)
        )
        self.assertEqual(actor, expected)
        self.assertEqual(len(actor), 73)  # pinned by PF_STATS_PROG002 s4/s5

    def test_make_actor_attr_with_basic_faction_is_byte_for_byte_unchanged(self):
        actor = make_actor_attr_with_basic_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME, 1,
        )
        baseline = make_actor_attr_with_name(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        faction_at = 14 + 10 + 3 + 9
        expected = (
            baseline[:11]
            + self.legacy.u16tag(0x12, 0x070C)
            + baseline[14:faction_at]
            + self.legacy.u32tag(0x14, 1)
            + baseline[faction_at:]
        )
        self.assertEqual(actor, expected)
        self.assertEqual(len(actor), len(baseline) + 5)

    def test_basic_faction_guard_is_unchanged(self):
        with self.assertRaises(ValueError):
            make_actor_attr_with_basic_faction(
                self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME, 2,
            )


class ProbeBase1LoginAttrTests(_LegacyCase):
    """The real login projection now carries class+level+speed."""

    def _expected(self, faction_wire: bytes = b"") -> bytes:
        legacy = self.legacy
        basic_mask = 0x0001 | 0x0002 | 0x000C | 0x0040 | 0x0100 | 0x0200
        if faction_wire:
            basic_mask |= 0x0400
        identity = bytes([0x32]) + struct.pack("<II", IDENTITY_LO, IDENTITY_HI)
        return (
            legacy.u8tag(0x0B, 1)
            + identity
            + legacy.u16tag(0x12, basic_mask)
            + legacy.wstr_tag(NAME)
            + legacy.u16tag(0x12, PLAYER_LOGIN_LEVEL)
            + legacy.u32tag(0x14, 100)
            + legacy.u32tag(0x14, 100)
            + legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED)
            + legacy.u16tag(0x12, SCENE_ID)
            + bytes([0x32]) + struct.pack("<Q", SCENE_SEQ)
            + faction_wire
            + bytes([0x32]) + struct.pack("<II", 0x00000801, 0)
            + legacy.u8tag(0x05, 1)
            + legacy.u32tag(0x19, PLAYER_LOGIN_CLASS_ID)
            + bytes([0x32]) + struct.pack("<Q", legacy.V116_INITIAL_CASH)
        )

    def test_class_and_level_variant_matches_the_full_hand_derived_layout(self):
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        self.assertEqual(actor, self._expected())

    def test_class_level_and_faction_variant_matches_the_full_layout(self):
        actor = make_actor_attr_with_name_class_and_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME, 1,
        )
        faction_wire = self.legacy.u32tag(0x14, 1)
        self.assertEqual(actor, self._expected(faction_wire))

    def test_basic_mask_bits_are_within_the_u16_field_and_ascend(self):
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        # byte 11 is the tag (0x12), bytes 12-13 the little-endian u16 mask.
        self.assertEqual(actor[11], 0x12)
        basic_mask = int.from_bytes(actor[12:14], "little")
        self.assertEqual(basic_mask, 0x0001 | 0x0002 | 0x000C | 0x0040 | 0x0100 | 0x0200)
        bits = [1 << i for i in range(16) if basic_mask & (1 << i)]
        self.assertEqual(bits, sorted(bits))

    def test_movement_speed_is_f32_tag_0x2a_immediately_after_hp(self):
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        hp_max = self.legacy.u32tag(0x14, 100)
        speed = self.legacy.f32tag(PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertEqual(speed[0], 0x2A)
        self.assertEqual(struct.unpack("<f", speed[1:])[0], PLAYER_LOGIN_MOVEMENT_SPEED)
        self.assertIn(hp_max + speed, actor)

    def test_mp_and_ability_fields_are_not_emitted(self):
        """No committed source names a level-1/class-1 MP or ability value
        (see player_wire.py's module docstring) -- must not fabricate one."""
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        basic_mask = int.from_bytes(actor[12:14], "little")
        self.assertEqual(basic_mask & 0x0030, 0)  # MP current/max bits unset
        name_wire_len = len(self.legacy.wstr_tag(NAME))
        actor_mask_at = 2 + 9 + 3 + name_wire_len + 3 + 5 + 5 + 5 + 3 + 9
        self.assertEqual(actor[actor_mask_at], 0x32)
        low, high = struct.unpack("<II", actor[actor_mask_at + 1:actor_mask_at + 9])
        self.assertEqual(high, 0)
        self.assertEqual(low & 0x000003E0, 0)  # STR/CON/DEX/INT/PER bits unset
        self.assertEqual(low & 0x01000000, 0)  # guild-name bit unset (PANYA-DECISION 0125: not the char name)
        self.assertEqual(low, 0x00000801)

    def test_wire_positions_for_the_not_yet_wired_fields_match_the_committed_field_table(self):
        """Cross-check: the report-derived field table this repo already
        ships (stats_progression_hypothesis.PROGRESSION_FIELDS) agrees with
        the positions cited in player_wire.py's module docstring, so wiring
        MP/abilities in later is a one-line value change, not a new RE hunt."""
        mp_current = PROGRESSION_FIELDS["mp_current"]
        mp_max = PROGRESSION_FIELDS["mp_max"]
        self.assertEqual((mp_current.mask_bit, mp_current.offset, mp_current.tag), (0x0010, 0x4C, 0x14))
        self.assertEqual((mp_max.mask_bit, mp_max.offset, mp_max.tag), (0x0020, 0x50, 0x14))
        for name, bit, offset in (
            ("ability_str", 0x00000020, 0x82),
            ("ability_con", 0x00000040, 0x84),
            ("ability_dex", 0x00000080, 0x86),
            ("ability_int", 0x00000100, 0x88),
            ("ability_per", 0x00000200, 0x8A),
        ):
            field = PROGRESSION_FIELDS[name]
            self.assertEqual((field.mask_bit, field.offset, field.tag), (bit, offset, 0x12))

    def test_length_delta_between_plain_and_faction_variant_stays_five_bytes(self):
        plain = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        )
        faction = make_actor_attr_with_name_class_and_faction(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME, 1,
        )
        self.assertEqual(len(faction), len(plain) + NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA)

    def test_faction_guard_unchanged_on_the_widened_variant(self):
        with self.assertRaises(ValueError):
            make_actor_attr_with_name_class_and_faction(
                self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME, 2,
            )
        # Scene 130 (Navy Training Camp), not admitted -- MOVED this round
        # (68mm02) from scene 11 (Deep Sea Temple floor 2), which
        # world_faction_admission now admits since its registry row opened
        # this round.
        with self.assertRaises(ValueError):
            make_actor_attr_with_name_class_and_faction(
                self.legacy, IDENTITY_LO, IDENTITY_HI, 130, SCENE_SEQ, NAME, 1,
            )

    def test_class_and_level_arguments_still_thread_through(self):
        actor = make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
            class_id=4, level=12,
        )
        self.assertIn(self.legacy.u16tag(0x12, 12), actor)
        self.assertIn(self.legacy.u32tag(0x19, 4), actor)


if __name__ == "__main__":
    unittest.main()
