"""DAMAGE-HP-LINK-001 / HYP-PF-026: pin the hit -> bleed -> die link sweep.

The lane's claim is that EIGHT composed ``GSCN_RunTimeProtocolRes`` frames --
three ``CHitResult`` 0x16F7 version 0 hit frames interleaved with five
``UpdateAttrVital`` 0x309A / ``ActorAttr`` 0x12AD hp frames -- can say both
halves of one sentence the client cannot compute for itself: the floating
damage number AND the shrinking HP bar, linked by a SERVER-HELD balance whose
whole ladder (100, 100, 37, 37, 37, 37, 0, 0) is re-derived by the module's
own arithmetic engine on every composition.  Every part of that claim is a
statement about bytes, so these tests assert bytes: the complete hex of all
eight PCs of the pinned probe identity 0x10010001, the two change masks, the
basic-attr masks 0x030C and 0x038C, the exact five bytes of -63 / 0 / -379,
the exact five bytes of the 20.0 s dying timer and the pinned elapsed zero.

COPIED, NOT IMPORTED -- AND THIS FILE IS THE DRIFT CHECK
--------------------------------------------------------
The module deliberately imports neither neighbouring lane: the containment
tests below require that exactly two foundation modules (app.py and
runtime.py) mention it at all, and the same discipline holds for its
neighbours.  Every constant it copied -- the damage formula, the CHitResult
layout, the ActorAttr field registry, the dying-hold timer pair, the probe
identity, the baseline cash -- is therefore re-compared HERE against the lane
it came from, where an import costs nothing.  And the copies are held to more
than equality: the three hit frames must be BYTE-IDENTICAL to what the
damage-model lane's own composer emits for the same probe, and the three
pinned hp frames BYTE-IDENTICAL to the stats lane's own baseline and
dying-hold compositions, each through that lane's own unlock.

TRAP TESTS
----------
A validator that cannot be made to fail is not a validator, and a check that
has never been seen red is not a check.  Every trap below fires into the SAME
code path the real guard runs -- a tampered pin dict goes through the real
build, a forged unlock through the real identity comparison, a mutated sweep
through the real byte walker -- and every refused call must hand back NOTHING,
which assertNoBytes enforces.

No socket, no server, no GameClient, no canonical database, no write of any
kind.  The only subprocess is the lane's own verifier, and that test skips
itself if the verifier has not been written yet.

ASCII ONLY.  Everything this file can print has to survive a cp874 Windows
console, so the source itself is asserted to be pure ASCII below.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import damage_hp_link_hypothesis as hpl  # noqa: E402
from pirateforce_foundation import damage_model_hypothesis as dmh  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402

SCENARIO = ROOT / "scenarios" / "damage_hp_link_hypothesis_link_sweep.json"
DAMAGE_SCENARIO = ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
DYING_HOLD_SCENARIO = ROOT / "scenarios" / "hp_death_hypothesis_dying_hold.json"
TOOL = ROOT / "tools" / "verify_damage_hp_link_encoder.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
LEDGER = ROOT / "docs" / "HYPOTHESIS_LEDGER.json"
MODULE_SOURCE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "damage_hp_link_hypothesis.py"
)
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
REPORT_PATH = "reports/PF_DAMAGE_HP_LINK001_HIT_BLEED_DIE_LINK_20260820.md"
REPLAY_TOOL_PATH = "tools/pf_damage_hp_link_headless_replay.py"
VERIFIER_PATH = "tools/verify_damage_hp_link_encoder.py"

# The complete PC of every frame of the PINNED PROBE identity (0x10010001),
# byte for byte.  A live sweep carries the session's own identity -- except on
# THIS lane it cannot: the dispatcher refuses any identity that is not the
# probe, so the bytes below are the only bytes this lane can ever emit.  If
# any of these strings has to change, the change is a WIRE CHANGE and belongs
# in a report before it belongs in this file.
EXPECT_PC_HEX = {
    "HP_BASELINE": (
        "129d6e140000000008040b02120100129a300b0012010012ad1214490000"
        "000b01320100011000000000120c03146400000014640000001201003200"
        "000000000000003200080001000000000501321027000000000000480c00"
        "00007400650073007400300031000b00"
    ),
    "HIT_WEAK": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b0012010032010001100000000014c1ffffff2a"
        "d45f10c62ab9e030c52ac74a5f432a000000001201000b00"
    ),
    "HP_AFTER_WEAK": (
        "129d6e140000000008040b02120100129a300b0012010012ad1214490000"
        "000b01320100011000000000120c03142500000014640000001201003200"
        "000000000000003200080001000000000501321027000000000000480c00"
        "00007400650073007400300031000b00"
    ),
    "MISS": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b0012010032010001100000000014000000002a"
        "d45f10c62ab9e030c52ac74a5f432a000000001200000b00"
    ),
    "HP_AFTER_MISS": (
        "129d6e140000000008040b02120100129a300b0012010012ad1214490000"
        "000b01320100011000000000120c03142500000014640000001201003200"
        "000000000000003200080001000000000501321027000000000000480c00"
        "00007400650073007400300031000b00"
    ),
    "HIT_STRONG": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b001201003201000110000000001485feffff2a"
        "d45f10c62ab9e030c52ac74a5f432a000000001201000b00"
    ),
    "HP_ZERO_DYING": (
        "129d6e140000000008040b02120100129a300b0012010012ad12144e0000"
        "000b01320100011000000000128c03140000000014640000002a0000a041"
        "120100320000000000000000320008000100000000050132102700000000"
        "0000480c0000007400650073007400300031000b00"
    ),
    "DYING_ELAPSED": (
        "129d6e140000000008040b02120100129a300b0012010012ad12144e0000"
        "000b01320100011000000000128c03140000000014640000002a00000000"
        "120100320000000000000000320008000100000000050132102700000000"
        "0000480c0000007400650073007400300031000b00"
    ),
}

# The five bytes at hit-entry +0x08, per hit step: tag 0x14 then the
# little-endian two's complement.  -63 is 0xFFFFFFC1 -> c1 ff ff ff.
EXPECT_DAMAGE_BYTES = {
    "HIT_WEAK": "14c1ffffff",
    "MISS": "1400000000",
    "HIT_STRONG": "1485feffff",
}
EXPECT_DAMAGE_SIGNED = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
EXPECT_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}

# The five bytes of hp_current per hp step, and of the death timer where the
# step carries one: tag then the little-endian value.
EXPECT_HP_CURRENT_BYTES = {
    "HP_BASELINE": "1464000000",
    "HP_AFTER_WEAK": "1425000000",
    "HP_AFTER_MISS": "1425000000",
    "HP_ZERO_DYING": "1400000000",
    "DYING_ELAPSED": "1400000000",
}
EXPECT_TIMER_BYTES = {
    "HP_ZERO_DYING": "2a0000a041",   # 20.0f
    "DYING_ELAPSED": "2a00000000",   # 0.0f, the pinned elapsed frame
}
EXPECT_BASIC_MASK = {
    "HP_BASELINE": 0x030C,
    "HP_AFTER_WEAK": 0x030C,
    "HP_AFTER_MISS": 0x030C,
    "HP_ZERO_DYING": 0x038C,
    "DYING_ELAPSED": 0x038C,
}

EXPECT_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
EXPECT_DELAYS = [0.0] + [15.0] * 7

# Byte positions inside the composed PCs, walked out by hand once from the
# pinned hex and asserted below.  These are positions of VALUES; each is
# preceded by its tag.  The envelope prefix is shared by both carriers:
#
#   0  12 ....  envelope id      (tag 0x12, u16)      value at 1
#   3  14 ....  envelope error   (tag 0x14, u32)      value at 4
#   8  08 ..    envelope version (tag 0x08, u8)       value at 9
#  10  0b ..    base change mask (tag 0x0B, u8)       value at 11
#  12  12 ....  vital count      (tag 0x12, u16)      value at 13
#  15  12 ....  vital id         (tag 0x12, u16)      value at 16
#  18  0b ..    vital version    (tag 0x0B, u8)       value at 19
#  20  ......   the carrier body starts here
ENVELOPE_ID_VALUE_AT = 1
ENVELOPE_VERSION_VALUE_AT = 9
BASE_CHANGE_MASK_VALUE_AT = 11
VITAL_COUNT_VALUE_AT = 13
VITAL_ID_VALUE_AT = 16
VITAL_VERSION_VALUE_AT = 19

# Hit-frame positions (84-byte PC), identical to the damage lane's because the
# bytes are identical to the damage lane's:
HIT_ENTRY_AT = 45
DAMAGE_TAG_AT = 54
POSITION_TAG_AT = 59
YAW_TAG_AT = 74
FLAGS_TAG_AT = 79
HIT_DERIVED_CHANGE_MASK_VALUE_AT = 83
EXPECT_HIT_PC_SIZE = 84
EXPECT_HIT_FRAME_SIZE = 95

# Hp-frame positions.  The Attr collection header sits at 20 (count), 23 (attr
# id) and 26 (body length); the body starts at 31.  On the two lethal frames
# the timer field inserts five bytes after hp_max, shifting everything behind
# it; the offsets below stop before that point on purpose.
ATTR_COUNT_VALUE_AT = 21
ATTR_ID_VALUE_AT = 24
ATTR_BODY_LENGTH_VALUE_AT = 27
DB_MASK_VALUE_AT = 32
IDENTITY_QWORD_VALUE_AT = 34
BASIC_MASK_VALUE_AT = 43
HP_CURRENT_TAG_AT = 45
HP_MAX_TAG_AT = 50
LETHAL_TIMER_TAG_AT = 55
EXPECT_HP_PC_SIZE = 106
EXPECT_HP_FRAME_SIZE = 117
EXPECT_LETHAL_PC_SIZE = 111
EXPECT_LETHAL_FRAME_SIZE = 122

HP_STEP_LABELS = (
    "HP_BASELINE", "HP_AFTER_WEAK", "HP_AFTER_MISS",
    "HP_ZERO_DYING", "DYING_ELAPSED",
)
HIT_STEP_LABELS = ("HIT_WEAK", "MISS", "HIT_STRONG")
LETHAL_STEP_LABELS = ("HP_ZERO_DYING", "DYING_ELAPSED")

GUARD_SUMMARY_RE = re.compile(r"^guards run:\s*(\d+)", re.MULTILINE)

_LEGACY = None
_SWEEP = None


def legacy():
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy(LEGACY_PATH)
    return _LEGACY


def sweep():
    """Compose the real probe sweep once.

    Returns ``(scenario, unlock, actions)``.  ``build_damage_hp_link_sweep``
    already refuses to return anything that is not the pin, so simply getting
    here is itself a guard.
    """
    global _SWEEP
    if _SWEEP is None:
        scenario = hpl.load_damage_hp_link_hypothesis_scenario(SCENARIO)
        unlock = hpl.damage_hp_link_wire_unlock(scenario)
        _SWEEP = (
            scenario, unlock,
            hpl.build_damage_hp_link_sweep(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, scenario,
            ),
        )
    return _SWEEP


def step_index(label):
    return hpl.DAMAGE_HP_LINK_STEP_ORDER.index(label)


def mutated(mutate):
    """A copy of the real sweep with one deliberate defect.

    ``mutate`` receives a list of mutable rows.  Whenever it edits a PC it
    must call :func:`repack`, otherwise the transport check fires first and
    the trap proves nothing about the guard it claims to test.
    """
    _scenario, _unlock, actions = sweep()
    rows = [list(a) for a in actions]
    mutate(rows)
    return [tuple(r) for r in rows]


def repack(rows, index, pc):
    """Store a mutated PC together with the frame that really wraps it."""
    rows[index][1] = bytes(pc)
    rows[index][2] = legacy().frame_pc(bytes(pc))


def patch_u16(pc, at, value):
    out = bytearray(pc)
    out[at:at + 2] = struct.pack("<H", value)
    return out


def patch_i32(pc, at, value):
    out = bytearray(pc)
    out[at:at + 4] = struct.pack("<i", value)
    return out


def patch_u32(pc, at, value):
    out = bytearray(pc)
    out[at:at + 4] = struct.pack("<I", value)
    return out


def patch_f32(pc, at, value):
    out = bytearray(pc)
    out[at:at + 4] = struct.pack("<f", value)
    return out


def baseline_fields():
    return hpl.damage_hp_link_baseline_fields(legacy())


class NoBytesMixin:
    """Every refusal in this lane has to fail closed with nothing in hand."""

    def assertNoBytes(self, thunk, because):
        """Call ``thunk``; require the named refusal AND zero output.

        ``produced`` stays empty only if ``thunk`` never returned.  If a
        future edit ever makes a guard log-and-continue, the frame it handed
        back lands in ``produced`` and this fails -- which is the point.
        """
        produced = []
        with self.assertRaises(hpl.DamageHpLinkValidationError) as ctx:
            produced.append(thunk())
        self.assertIn(because, str(ctx.exception))
        self.assertEqual(
            produced, [],
            "the refused call still handed back %d byte-carrying result(s)"
            % len(produced),
        )

    def assertSweepRejected(self, mutate, because):
        bad = mutated(mutate)
        self.assertNoBytes(
            lambda: hpl.validate_damage_hp_link_sweep(bad), because,
        )


# ===========================================================================
# 1.  THE BYTES THEMSELVES
# ===========================================================================
class PinnedByteTests(unittest.TestCase):
    def test_every_probe_frame_is_byte_for_byte_the_expected_pc(self):
        _scenario, _unlock, actions = sweep()
        for index, label in enumerate(hpl.DAMAGE_HP_LINK_STEP_ORDER):
            with self.subTest(step=label):
                self.assertEqual(actions[index][1].hex(), EXPECT_PC_HEX[label])

    def test_the_pinned_hex_is_the_pinned_sha256_and_size(self):
        for label, hexed in EXPECT_PC_HEX.items():
            pin = hpl.DAMAGE_HP_LINK_PINS[label]
            pc = bytes.fromhex(hexed)
            with self.subTest(step=label):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])

    def test_every_composed_frame_matches_its_pin_in_size_and_hash(self):
        _scenario, _unlock, actions = sweep()
        for index, label in enumerate(hpl.DAMAGE_HP_LINK_STEP_ORDER):
            pin = hpl.DAMAGE_HP_LINK_PINS[label]
            _label, pc, frame, _delay = actions[index]
            with self.subTest(step=label):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(len(frame), pin["frame_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"])

    def test_the_scenario_file_carries_the_same_pins_as_the_module(self):
        """Two copies of the pin, on disk and in code, must not drift apart."""
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        per_step = on_disk["probe"]["per_step"]
        self.assertEqual(set(per_step), set(hpl.DAMAGE_HP_LINK_STEP_ORDER))
        for label in hpl.DAMAGE_HP_LINK_STEP_ORDER:
            pin = hpl.DAMAGE_HP_LINK_PINS[label]
            with self.subTest(step=label):
                for key in ("pc_size", "pc_sha256", "frame_size",
                            "frame_sha256"):
                    self.assertEqual(per_step[label][key], pin[key])

    def test_the_pins_belong_to_the_pinned_probe_identity(self):
        """Hit frames carry the qword twice (performer and target); hp frames
        carry it once, inside the DBAttribute identity field."""
        _scenario, _unlock, actions = sweep()
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_LO, 0x10010001)
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_HI, 0)
        qword = struct.pack("<Q", hpl.HP_LINK_PROBE_IDENTITY_LO)
        for index, label in enumerate(hpl.DAMAGE_HP_LINK_STEP_ORDER):
            pc = actions[index][1]
            expected = 2 if label in HIT_STEP_LABELS else 1
            with self.subTest(step=label):
                self.assertEqual(pc.count(qword), expected)

    def test_the_shipped_scenario_file_loads_and_is_the_pinned_plan(self):
        scenario = hpl.load_damage_hp_link_hypothesis_scenario(SCENARIO)
        self.assertEqual(scenario.scenario_id, hpl.DAMAGE_HP_LINK_SCENARIO_ID)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-026")
        self.assertEqual(
            scenario.step_order,
            ("HP_BASELINE", "HIT_WEAK", "HP_AFTER_WEAK", "MISS",
             "HP_AFTER_MISS", "HIT_STRONG", "HP_ZERO_DYING", "DYING_ELAPSED"))
        self.assertEqual(scenario.step_order, hpl.DAMAGE_HP_LINK_STEP_ORDER)
        self.assertIs(hpl.production_allowed, False)

    def test_the_sweep_is_eight_labelled_frames_on_the_pinned_cadence(self):
        _scenario, _unlock, actions = sweep()
        self.assertEqual([a[0] for a in actions],
                         list(hpl.DAMAGE_HP_LINK_ACTION_LABELS))
        self.assertEqual([a[3] for a in actions], EXPECT_DELAYS)
        self.assertEqual(hpl.DAMAGE_HP_LINK_SPACING_SECONDS, 15.0)
        self.assertEqual(hpl.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS, 0.0)

    def test_the_two_post_miss_hp_frames_are_byte_identical(self):
        """A miss moves nothing, and identical bytes are the strongest way to
        say so: HP_AFTER_WEAK and HP_AFTER_MISS must not differ by one bit."""
        _scenario, _unlock, actions = sweep()
        after_weak = actions[step_index("HP_AFTER_WEAK")]
        after_miss = actions[step_index("HP_AFTER_MISS")]
        self.assertEqual(after_weak[1], after_miss[1])
        self.assertEqual(after_weak[2], after_miss[2])
        self.assertEqual(
            hpl.DAMAGE_HP_LINK_PINS["HP_AFTER_WEAK"]["pc_sha256"],
            hpl.DAMAGE_HP_LINK_PINS["HP_AFTER_MISS"]["pc_sha256"])


# ===========================================================================
# 2.  CROSS-LANE BYTE EQUALITY: the copies are the originals, byte for byte
# ===========================================================================
class CrossLaneByteEqualityTests(unittest.TestCase):
    """The strongest drift check there is: recompose every borrowed frame
    through the lane it was borrowed from, with that lane's own unlock, and
    compare with ``==`` on the bytes."""

    def test_the_hit_frames_are_the_damage_lanes_bytes_recomposed(self):
        _scenario, _unlock, actions = sweep()
        damage_scenario = dmh.load_damage_model_hypothesis_scenario(
            DAMAGE_SCENARIO)
        damage_unlock = dmh.damage_model_wire_unlock(damage_scenario)
        probe = dmh.damage_probe_actor(legacy())
        self.assertEqual(probe.identity_lo, hpl.HP_LINK_PROBE_IDENTITY_LO)
        self.assertEqual(probe.identity_hi, hpl.HP_LINK_PROBE_IDENTITY_HI)
        for link_label, damage_label in (
            ("HIT_WEAK", "HIT_WEAK"),
            ("MISS", "MISS"),
            ("HIT_STRONG", "HIT_STRONG"),
        ):
            damage_index = dmh.DAMAGE_MODEL_STEP_ORDER.index(damage_label)
            pc, frame = dmh.make_damage_model_step_response(
                legacy(), probe, damage_index, damage_unlock, damage_scenario)
            link = actions[step_index(link_label)]
            with self.subTest(step=link_label):
                self.assertEqual(link[1], pc)
                self.assertEqual(link[2], frame)

    def test_the_hit_pins_equal_the_damage_lane_pins(self):
        for label in HIT_STEP_LABELS:
            with self.subTest(step=label):
                self.assertEqual(
                    hpl.DAMAGE_HP_LINK_PINS[label]["pc_sha256"],
                    dmh.DAMAGE_MODEL_PINS[label]["pc_sha256"])
                self.assertEqual(
                    hpl.DAMAGE_HP_LINK_PINS[label]["frame_sha256"],
                    dmh.DAMAGE_MODEL_PINS[label]["frame_sha256"])
                self.assertEqual(
                    hpl.DAMAGE_HP_LINK_PINS[label]["pc_size"],
                    dmh.DAMAGE_MODEL_PINS[label]["pc_size"])

    def test_the_hp_baseline_is_the_stats_lanes_baseline_recomposed(self):
        """The stats lane's OWN composer, no unlock needed for its baseline."""
        _scenario, _unlock, actions = sweep()
        pc, frame = sp.make_stats_progression_step_response(
            legacy(), sp.STATS_PROBE_ACTOR, 0)
        self.assertEqual(actions[step_index("HP_BASELINE")][1], pc)
        self.assertEqual(actions[step_index("HP_BASELINE")][2], frame)

    def test_the_lethal_frames_are_the_dying_hold_lanes_bytes_recomposed(self):
        """The dying-hold profile's OWN path, through its OWN lethal unlock."""
        _scenario, _unlock, actions = sweep()
        dying_scenario = sp.load_hp_death_hypothesis_scenario(
            DYING_HOLD_SCENARIO)
        lethal = sp.hp_death_lethal_unlock(dying_scenario)
        profile = sp.hp_death_profile_for_scenario(dying_scenario)
        self.assertEqual(
            profile.step_order,
            ("BASELINE", "TIMER_ARMED", "HP_ZERO", "TIMER_ELAPSED"))
        for link_label, dying_label in (
            ("HP_BASELINE", "BASELINE"),
            ("HP_ZERO_DYING", "HP_ZERO"),
            ("DYING_ELAPSED", "TIMER_ELAPSED"),
        ):
            dying_index = profile.step_order.index(dying_label)
            pc, frame = sp.make_hp_death_step_response(
                legacy(), sp.STATS_PROBE_ACTOR, dying_index, lethal, profile)
            link = actions[step_index(link_label)]
            with self.subTest(step=link_label):
                self.assertEqual(link[1], pc)
                self.assertEqual(link[2], frame)

    def test_the_modules_own_pins_reproduce_on_recomposition(self):
        """Not just the sweep builder: every step recomposed one at a time."""
        _scenario, unlock, _actions = sweep()
        for index, label in enumerate(hpl.DAMAGE_HP_LINK_STEP_ORDER):
            pc, frame = hpl.make_damage_hp_link_step_response(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, index, unlock)
            pin = hpl.DAMAGE_HP_LINK_PINS[label]
            with self.subTest(step=label):
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"])


# ===========================================================================
# 3.  DRIFT TESTS: every copied constant against the lane it came from
# ===========================================================================
class CopiedConstantDriftTests(unittest.TestCase):
    """The module copies, never imports; this file imports, and compares."""

    def test_the_formula_constants_equal_the_damage_lanes(self):
        self.assertEqual(hpl.ATK_BASE, dmh.ATK_BASE)
        self.assertEqual(hpl.K_ATK_STR, dmh.K_ATK_STR)
        self.assertEqual(hpl.K_ATK_LV, dmh.K_ATK_LV)
        self.assertEqual(hpl.DEF_BASE, dmh.DEF_BASE)
        self.assertEqual(hpl.K_DEF_CON, dmh.K_DEF_CON)
        self.assertEqual(hpl.K_DEF_LV, dmh.K_DEF_LV)
        self.assertEqual(hpl.MIN_HIT, dmh.MIN_HIT)

    def test_the_attacker_and_defender_ints_equal_the_source_lanes(self):
        self.assertEqual(hpl.ATTACKER_MOB_WEAK_LEVEL,
                         dmh.ATTACKER_MOB_WEAK.level)
        self.assertEqual(hpl.ATTACKER_MOB_WEAK_ABILITY_STR,
                         dmh.ATTACKER_MOB_WEAK.ability_str)
        self.assertEqual(hpl.ATTACKER_MOB_STRONG_LEVEL,
                         dmh.ATTACKER_MOB_STRONG.level)
        self.assertEqual(hpl.ATTACKER_MOB_STRONG_ABILITY_STR,
                         dmh.ATTACKER_MOB_STRONG.ability_str)
        self.assertEqual(hpl.DEFENDER_LEVEL, dmh.DEFENDER_LEVEL)
        self.assertEqual(hpl.DEFENDER_ABILITY_CON, dmh.DEFENDER_ABILITY_CON)
        # and one lane further back: the defender is the progression lane's
        # on-screen character, in all three modules
        self.assertEqual(hpl.DEFENDER_LEVEL, sp.STATS_PROGRESSION_LEVEL)
        self.assertEqual(hpl.DEFENDER_ABILITY_CON,
                         sp.STATS_PROGRESSION_ABILITY_CON)

    def test_the_recomputed_wire_values_agree_across_the_two_lanes(self):
        self.assertEqual(hpl.compute_hp_link_damage_wire("MOB_WEAK"), -63)
        self.assertEqual(hpl.compute_hp_link_damage_wire("MOB_STRONG"), -379)
        self.assertEqual(
            hpl.compute_hp_link_damage_wire("MOB_WEAK"),
            dmh.compute_damage(dmh.ATTACKER_MOB_WEAK,
                               dmh.DEFENDER_PLAYER_BASELINE))
        self.assertEqual(
            hpl.compute_hp_link_damage_wire("MOB_STRONG"),
            dmh.compute_damage(dmh.ATTACKER_MOB_STRONG,
                               dmh.DEFENDER_PLAYER_BASELINE))

    def test_the_chit_result_layout_constants_equal_the_damage_lanes(self):
        pairs = (
            ("CHIT_RESULT_VITAL_ID", "CHIT_RESULT_VITAL_ID"),
            ("CHIT_RESULT_VITAL_VERSION", "CHIT_RESULT_VITAL_VERSION"),
            ("CHIT_RESULT_HEADER_WIRE_SIZE", "CHIT_RESULT_HEADER_WIRE_SIZE"),
            ("HIT_COUNT_WIRE_SIZE", "HIT_COUNT_WIRE_SIZE"),
            ("HIT_ELEMENT_WIRE_SIZE", "HIT_ELEMENT_WIRE_SIZE"),
            ("HIT_ENTRY_TARGET_OFFSET", "HIT_ENTRY_TARGET_OFFSET"),
            ("HIT_ENTRY_DAMAGE_OFFSET", "HIT_ENTRY_DAMAGE_OFFSET"),
            ("HIT_ENTRY_POSITION_OFFSET", "HIT_ENTRY_POSITION_OFFSET"),
            ("HIT_ENTRY_YAW_OFFSET", "HIT_ENTRY_YAW_OFFSET"),
            ("HIT_ENTRY_FLAGS_OFFSET", "HIT_ENTRY_FLAGS_OFFSET"),
            ("HEADER_RESERVED_VALUE", "HEADER_RESERVED_VALUE"),
            ("HIT_ENTRY_COUNT_PINNED", "HIT_ENTRY_COUNT_PINNED"),
            ("CHIT_RESULT_PAYLOAD_WIRE_SIZE", "CHIT_RESULT_PAYLOAD_WIRE_SIZE"),
        )
        for link_name, damage_name in pairs:
            with self.subTest(constant=link_name):
                self.assertEqual(getattr(hpl, link_name),
                                 getattr(dmh, damage_name))

    def test_the_flag_and_band_constants_equal_the_damage_lanes(self):
        self.assertEqual(hpl.FLAGS_MISS, dmh.FLAGS_MISS)
        self.assertEqual(hpl.FLAGS_HIT, dmh.FLAGS_HIT)
        self.assertEqual(hpl.FLAGS_FORBIDDEN_MASK, dmh.FLAGS_FORBIDDEN_MASK)
        self.assertEqual(hpl.DAMAGE_WIRE_MAX, dmh.DAMAGE_WIRE_MAX)
        self.assertEqual(hpl.DAMAGE_WIRE_MIN, dmh.DAMAGE_WIRE_MIN)
        self.assertEqual(hpl.INT32_MIN, dmh.INT32_MIN)
        self.assertEqual(hpl.YAW_PINNED, dmh.YAW_PINNED)
        # this lane deliberately ships only the two plain flag words; the
        # reaction word 0x0009 stays with the damage lane
        self.assertEqual(hpl.HP_LINK_FLAGS_VALUE_ALLOWLIST, (0x0000, 0x0001))
        self.assertNotIn(dmh.FLAGS_HIT_REACTION,
                         hpl.HP_LINK_FLAGS_VALUE_ALLOWLIST)

    def test_the_envelope_constants_equal_the_neighbours(self):
        self.assertEqual(hpl.RUNTIME_PROTOCOL_RES_VERSION,
                         dmh.RUNTIME_PROTOCOL_RES_VERSION)
        self.assertEqual(hpl.RUNTIME_PROTOCOL_RES_VERSION, 4)
        self.assertEqual(hpl.HP_LINK_BASE_CHANGE_MASK,
                         dmh.BASE_CHANGE_MASK_VITAL_COLLECTION)
        self.assertEqual(hpl.HP_LINK_DERIVED_CHANGE_MASK,
                         dmh.DERIVED_CHANGE_MASK_ABSENT)
        self.assertEqual(hpl.HP_LINK_UPDATE_ATTR_VITAL_ID,
                         sp.UPDATE_ATTR_VITAL_ID)
        self.assertEqual(hpl.HP_LINK_UPDATE_ATTR_VITAL_VERSION,
                         sp.UPDATE_ATTR_VITAL_VERSION)
        self.assertEqual(hpl.HP_LINK_ACTOR_ATTR_ID, sp.ACTOR_ATTR_ID)
        self.assertEqual(hpl.HP_LINK_DB_ATTRIBUTE_MASK_TAG,
                         sp.DB_ATTRIBUTE_MASK_TAG)
        self.assertEqual(hpl.HP_LINK_DB_ATTRIBUTE_IDENTITY_BIT,
                         sp.DB_ATTRIBUTE_IDENTITY_BIT)
        self.assertEqual(hpl.HP_LINK_DB_ATTRIBUTE_IDENTITY_TAG,
                         sp.DB_ATTRIBUTE_IDENTITY_TAG)
        self.assertEqual(hpl.HP_LINK_BASIC_MASK_TAG, sp.BASIC_ATTR_MASK_TAG)
        self.assertEqual(hpl.HP_LINK_ACTOR_MASK_TAG, sp.ACTOR_ATTR_MASK_TAG)
        self.assertEqual(hpl.HP_LINK_EXTRA_GROUP_TAG,
                         sp.ACTOR_ATTR_EXTRA_GROUP_TAG)
        self.assertEqual(hpl.HP_LINK_EXTRA_GROUP_VALUE,
                         sp.ACTOR_ATTR_EXTRA_GROUP_VALUE)

    def test_the_actor_attr_field_table_rows_equal_the_stats_registry(self):
        """bit / offset / tag / width for every field this lane may emit."""
        source_rows = {
            "hp_current": sp.PROGRESSION_FIELDS["hp_current"],
            "hp_max": sp.PROGRESSION_FIELDS["hp_max"],
            "scene_id": sp.PROGRESSION_FIELDS["scene_id"],
            "scene_sequence": sp.PROGRESSION_FIELDS["scene_sequence"],
            "cash": sp.PROGRESSION_FIELDS["cash"],
            "character_name": sp.PROGRESSION_FIELDS["character_name"],
            "hp_death_timer": sp.HP_DEATH_TIMER_FIELD,
        }
        self.assertEqual(set(hpl.HP_LINK_FIELD_TABLE), set(source_rows))
        for name, source in source_rows.items():
            link = hpl.HP_LINK_FIELD_TABLE[name]
            with self.subTest(field=name):
                self.assertEqual(link.block, source.block)
                self.assertEqual(link.mask_bit, source.mask_bit)
                self.assertEqual(link.offset, source.offset)
                self.assertEqual(link.tag, source.tag)
                self.assertEqual(link.kind, source.kind)
        # the timer field is also the lethal table's row, same registry twice
        self.assertEqual(
            hpl.HP_LINK_FIELD_TABLE["hp_death_timer"].mask_bit,
            sp.LETHAL_FIELDS[sp.HP_DEATH_TIMER_NAME].mask_bit)
        self.assertEqual(hpl.HP_LINK_DEATH_TIMER_NAME, sp.HP_DEATH_TIMER_NAME)

    def test_the_probe_identity_equals_the_damage_lanes(self):
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_LO,
                         dmh.DAMAGE_PROBE_IDENTITY_LO)
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_HI,
                         dmh.DAMAGE_PROBE_IDENTITY_HI)
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_LO,
                         sp.STATS_PROBE_IDENTITY_LO)
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_HI,
                         sp.STATS_PROBE_IDENTITY_HI)
        self.assertEqual(hpl.HP_LINK_PROBE_IDENTITY_LO, 0x10010001)

    def test_the_dying_timer_pair_equals_the_stats_lanes_dying_hold(self):
        self.assertEqual(hpl.HP_LINK_DYING_TIMER_SECONDS, 20.0)
        self.assertEqual(hpl.HP_LINK_DYING_TIMER_SECONDS,
                         sp.HP_DEATH_DYING_HOLD_TIMER_SECONDS)
        self.assertEqual(hpl.HP_LINK_TIMER_ELAPSED_SECONDS,
                         sp.HP_DEATH_TIMER_ELAPSED_SECONDS)
        self.assertEqual(hpl.HP_LINK_TIMER_ELAPSED_WIRE_BYTES,
                         sp.HP_DEATH_TIMER_ELAPSED_WIRE_BYTES)
        self.assertEqual(hpl.HP_LINK_DURATION_DYING_IMAGE_DEFAULT,
                         sp.DURATION_DYING_IMAGE_DEFAULT)
        self.assertEqual(hpl.HP_LINK_DYING_WINDOW_MARGIN,
                         sp.DURATION_DYING_WINDOW_MARGIN)

    def test_the_baseline_pins_equal_the_stats_lanes_probe_projection(self):
        self.assertEqual(hpl.HP_LINK_BASELINE_CASH, legacy().V116_INITIAL_CASH)
        self.assertEqual(hpl.HP_LINK_BASELINE_CASH, sp.STATS_PROBE_CASH)
        self.assertEqual(hpl.HP_LINK_HP_START, sp.STATS_BASELINE_HP_CURRENT)
        self.assertEqual(hpl.HP_LINK_HP_MAX, sp.STATS_BASELINE_HP_MAX)
        self.assertEqual(hpl.HP_LINK_BASELINE_SCENE_ID, sp.STATS_PROBE_SCENE_ID)
        self.assertEqual(hpl.HP_LINK_BASELINE_SCENE_SEQUENCE,
                         sp.STATS_PROBE_SCENE_SEQUENCE)
        self.assertEqual(hpl.HP_LINK_BASELINE_CHARACTER_NAME,
                         sp.STATS_PROBE_CHARACTER_NAME)


# ===========================================================================
# 4.  THE WIRE SHAPE
# ===========================================================================
class WireShapeTests(unittest.TestCase):
    def test_every_frame_is_the_0x6e9d_version_4_envelope(self):
        _scenario, _unlock, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[0], hpl.TAG_U16)
                self.assertEqual(
                    struct.unpack_from("<H", pc, ENVELOPE_ID_VALUE_AT)[0],
                    0x6E9D)
                self.assertEqual(pc[ENVELOPE_VERSION_VALUE_AT],
                                 hpl.RUNTIME_PROTOCOL_RES_VERSION)
                self.assertEqual(pc[ENVELOPE_VERSION_VALUE_AT], 4)

    def test_the_base_mask_selects_the_vitaldata_collection_and_no_other(self):
        """base mask 0x02 (this+0x18), derived mask 0, on BOTH carriers."""
        _scenario, _unlock, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[BASE_CHANGE_MASK_VALUE_AT], 0x02)
                self.assertEqual(pc[len(pc) - 2], hpl.TAG_U8)
                self.assertEqual(pc[len(pc) - 1], 0x00)

    def test_the_hit_frames_are_chitresult_0x16f7_version_byte_zero(self):
        _scenario, _unlock, actions = sweep()
        for label in HIT_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(
                    struct.unpack_from("<H", pc, VITAL_COUNT_VALUE_AT)[0], 1)
                self.assertEqual(
                    struct.unpack_from("<H", pc, VITAL_ID_VALUE_AT)[0], 0x16F7)
                self.assertEqual(pc[VITAL_VERSION_VALUE_AT], 0)
                self.assertEqual(len(pc), EXPECT_HIT_PC_SIZE)
                self.assertEqual(pc[HIT_ENTRY_AT], hpl.TAG_QWORD)
                self.assertEqual(pc[DAMAGE_TAG_AT], hpl.TAG_U32)
                self.assertEqual(pc[YAW_TAG_AT], hpl.TAG_F32)
                self.assertEqual(pc[FLAGS_TAG_AT], hpl.TAG_U16)

    def test_the_hp_frames_are_updateattrvital_0x309a_actorattr_0x12ad(self):
        _scenario, _unlock, actions = sweep()
        for label in HP_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(
                    struct.unpack_from("<H", pc, VITAL_ID_VALUE_AT)[0], 0x309A)
                self.assertEqual(pc[VITAL_VERSION_VALUE_AT], 0)
                self.assertEqual(
                    struct.unpack_from("<H", pc, ATTR_COUNT_VALUE_AT)[0], 1)
                self.assertEqual(
                    struct.unpack_from("<H", pc, ATTR_ID_VALUE_AT)[0], 0x12AD)
                body_length = struct.unpack_from(
                    "<I", pc, ATTR_BODY_LENGTH_VALUE_AT)[0]
                # body + 20-byte envelope prefix + 11-byte collection header
                # + 2-byte derived mask tail
                self.assertEqual(len(pc), 20 + 11 + body_length + 2)
                self.assertEqual(pc[DB_MASK_VALUE_AT], 0x01)
                self.assertEqual(
                    struct.unpack_from("<Q", pc, IDENTITY_QWORD_VALUE_AT)[0],
                    hpl.HP_LINK_PROBE_IDENTITY_LO)

    def test_the_basic_attr_masks_are_030c_without_and_038c_with_the_timer(self):
        _scenario, _unlock, actions = sweep()
        for label in HP_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(
                    struct.unpack_from("<H", pc, BASIC_MASK_VALUE_AT)[0],
                    EXPECT_BASIC_MASK[label])
        self.assertEqual(EXPECT_BASIC_MASK["HP_ZERO_DYING"] ^ (
            EXPECT_BASIC_MASK["HP_BASELINE"]
        ), hpl.HP_LINK_FIELD_TABLE["hp_death_timer"].mask_bit)

    def test_the_hp_current_bytes_are_the_ladders_bytes(self):
        _scenario, _unlock, actions = sweep()
        for label in HP_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(
                    pc[HP_CURRENT_TAG_AT:HP_CURRENT_TAG_AT + 5].hex(),
                    EXPECT_HP_CURRENT_BYTES[label])
                self.assertEqual(pc[HP_MAX_TAG_AT:HP_MAX_TAG_AT + 5].hex(),
                                 "1464000000")

    def test_the_timer_bytes_are_the_pinned_20s_and_the_pinned_zero(self):
        _scenario, _unlock, actions = sweep()
        for label in LETHAL_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(
                    pc[LETHAL_TIMER_TAG_AT:LETHAL_TIMER_TAG_AT + 5].hex(),
                    EXPECT_TIMER_BYTES[label])
                self.assertEqual(len(pc), EXPECT_LETHAL_PC_SIZE)
        # spelled out once, so neither float is taken on trust
        self.assertEqual(bytes.fromhex("2a0000a041"),
                         bytes([0x2A]) + struct.pack("<f", 20.0))
        self.assertEqual(bytes.fromhex("2a00000000"),
                         bytes([0x2A]) + struct.pack("<f", 0.0))
        self.assertEqual(hpl.HP_LINK_TIMER_ELAPSED_WIRE_BYTES,
                         bytes.fromhex("2a00000000"))

    def test_every_frame_is_frame_pc_of_its_own_pc(self):
        _scenario, _unlock, actions = sweep()
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(frame, legacy().frame_pc(pc))
                self.assertEqual(
                    struct.unpack_from("<I", frame, 0)[0],
                    hpl.HP_LINK_FRAME_MAGIC)

    def test_the_independent_transport_walker_reproduces_every_pc(self):
        _scenario, _unlock, actions = sweep()
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(hpl.decode_hp_link_transport(frame), pc)

    def test_the_decoder_reads_back_what_the_encoder_wrote(self):
        _scenario, _unlock, actions = sweep()
        ladder = hpl.require_hp_link_balance_ladder()
        for index, (label, kind, _spec, _flags) in enumerate(
            hpl.DAMAGE_HP_LINK_STEPS
        ):
            decoded = hpl.decode_damage_hp_link_frame(actions[index][1])
            with self.subTest(step=label):
                self.assertEqual(decoded["envelope_id"], 0x6E9D)
                self.assertEqual(decoded["envelope_version"], 4)
                self.assertEqual(decoded["base_change_mask"], 2)
                self.assertEqual(decoded["derived_change_mask"], 0)
                self.assertEqual(decoded["kind"], kind)
                self.assertEqual(decoded["performer_identity"],
                                 hpl.HP_LINK_PROBE_IDENTITY_LO)
                if kind == hpl.HP_LINK_STEP_KIND_HIT:
                    self.assertEqual(decoded["damage_wire"],
                                     EXPECT_DAMAGE_SIGNED[label])
                    self.assertEqual(decoded["flags"], EXPECT_FLAGS[label])
                    self.assertEqual(decoded["target_identity"],
                                     decoded["performer_identity"])
                else:
                    fields = decoded["fields"]
                    self.assertEqual(fields["hp_current"], ladder[index])
                    self.assertEqual(fields["hp_max"], 100)
                    self.assertEqual(fields["cash"], 10000)
                    self.assertEqual(fields["character_name"], "test01")
                    self.assertEqual(
                        fields.get(hpl.HP_LINK_DEATH_TIMER_NAME),
                        hpl.DAMAGE_HP_LINK_TIMER_BY_STEP.get(label))

    def test_the_position_is_the_frozen_v135_player_spawn_on_hit_frames(self):
        _scenario, _unlock, actions = sweep()
        pinned = (
            float(legacy().V135_PLAYER_X),
            float(legacy().V135_PLAYER_Y),
            float(legacy().V135_PLAYER_Z),
        )
        positions = set()
        for label in HIT_STEP_LABELS:
            decoded = hpl.decode_damage_hp_link_frame(
                actions[step_index(label)][1])
            with self.subTest(step=label):
                for got, want in zip(decoded["position"], pinned):
                    self.assertEqual(struct.pack("<f", got),
                                     struct.pack("<f", want))
                self.assertEqual(decoded["yaw"], hpl.YAW_PINNED)
                self.assertEqual(hpl.YAW_PINNED, 0.0)
            positions.add(decoded["position"])
        self.assertEqual(len(positions), 1)

    def test_the_hp_frame_name_is_utf16le_two_bytes_per_code_unit(self):
        _scenario, _unlock, actions = sweep()
        pc = actions[step_index("HP_BASELINE")][1]
        raw = "test01".encode("utf-16le")
        self.assertEqual(len(raw), 12)
        self.assertIn(bytes([hpl.TAG_WSTRING]) + struct.pack("<I", 12) + raw,
                      pc)


# ===========================================================================
# 5.  THE SIGN IS THE MEANING
# ===========================================================================
class SignIsTheMeaningTests(unittest.TestCase):
    def test_plus_0x08_reads_back_signed_as_minus_63_0_minus_379(self):
        _scenario, _unlock, actions = sweep()
        read = [
            hpl.decode_damage_hp_link_frame(
                actions[step_index(label)][1])["damage_wire"]
            for label in HIT_STEP_LABELS
        ]
        self.assertEqual(read, [-63, 0, -379])

    def test_the_literal_bytes_of_each_hit_are_tag_0x14_then_twos_complement(self):
        _scenario, _unlock, actions = sweep()
        for label in HIT_STEP_LABELS:
            pc = actions[step_index(label)][1]
            with self.subTest(step=label):
                self.assertEqual(pc[DAMAGE_TAG_AT:DAMAGE_TAG_AT + 5].hex(),
                                 EXPECT_DAMAGE_BYTES[label])
        # spelled out once, so the two's complement is not taken on trust
        self.assertEqual(bytes.fromhex("14c1ffffff"),
                         bytes([0x14]) + struct.pack("<i", -63))
        self.assertEqual(bytes.fromhex("1485feffff"),
                         bytes([0x14]) + struct.pack("<i", -379))
        self.assertEqual(bytes.fromhex("1400000000"),
                         bytes([0x14]) + struct.pack("<i", 0))

    def test_the_unsigned_reading_of_the_same_bytes_is_not_the_meaning(self):
        _scenario, _unlock, actions = sweep()
        raw = actions[step_index("HIT_WEAK")][1][
            DAMAGE_TAG_AT + 1:DAMAGE_TAG_AT + 5]
        self.assertEqual(struct.unpack("<I", raw)[0], 0xFFFFFFC1)
        self.assertEqual(struct.unpack("<i", raw)[0], -63)

    def test_a_negative_wire_value_is_a_positive_number_on_screen(self):
        """The display path calls abs(); the wire carries the negative."""
        for label, value in EXPECT_DAMAGE_SIGNED.items():
            with self.subTest(step=label):
                self.assertLessEqual(value, hpl.DAMAGE_WIRE_MAX)
                self.assertEqual(hpl.DAMAGE_WIRE_MAX, 0)
                self.assertIn(abs(value), (0, 63, 379))


# ===========================================================================
# 6.  OUR FORMULA
# ===========================================================================
class FormulaTests(NoBytesMixin, unittest.TestCase):
    def test_the_arithmetic_is_the_one_a_tester_can_check_by_hand(self):
        self.assertEqual(hpl.compute_hp_link_attack(1, 3), 124)
        self.assertEqual(hpl.compute_hp_link_attack(20, 40), 440)
        self.assertEqual(hpl.compute_hp_link_defense(7, 22), 61)
        self.assertEqual(124 - 61, 63)
        self.assertEqual(440 - 61, 379)

    def test_the_two_pinned_profiles_produce_minus_63_and_minus_379(self):
        self.assertEqual(hpl.compute_hp_link_damage_wire("MOB_WEAK"), -63)
        self.assertEqual(hpl.compute_hp_link_damage_wire("MOB_STRONG"), -379)
        self.assertEqual(hpl.HP_LINK_DAMAGE_PINNED,
                         {"MOB_WEAK": -63, "MOB_STRONG": -379})

    def test_an_unknown_attacker_name_is_refused(self):
        for bad in ("MOB_MEDIUM", "", None, 0, object()):
            with self.subTest(attacker=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.compute_hp_link_damage_wire(b),
                    "unknown_step_label")

    def test_the_formula_is_deterministic_over_a_hundred_calls(self):
        values = {
            hpl.compute_hp_link_damage_wire("MOB_STRONG") for _ in range(100)
        }
        self.assertEqual(values, {-379})

    def test_the_module_source_contains_no_randomness_at_all(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        for banned in ("import random", "random.", "secrets", "urandom",
                       "SystemRandom", "time.time("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)

    def test_the_formula_constants_agree_with_the_scenario_file(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        formula = on_disk["wire"]["formula"]
        self.assertIs(formula["deterministic"], True)
        self.assertIs(formula["uses_random"], False)
        self.assertEqual(formula["atk_base"], hpl.ATK_BASE)
        self.assertEqual(formula["k_atk_str"], hpl.K_ATK_STR)
        self.assertEqual(formula["k_atk_lv"], hpl.K_ATK_LV)
        self.assertEqual(formula["def_base"], hpl.DEF_BASE)
        self.assertEqual(formula["k_def_con"], hpl.K_DEF_CON)
        self.assertEqual(formula["k_def_lv"], hpl.K_DEF_LV)
        self.assertEqual(formula["min_hit"], hpl.MIN_HIT)
        self.assertEqual(formula["defender"]["level"], hpl.DEFENDER_LEVEL)
        self.assertEqual(formula["defender"]["ability_con"],
                         hpl.DEFENDER_ABILITY_CON)
        self.assertEqual(formula["attackers"]["MOB_WEAK"]["level"],
                         hpl.ATTACKER_MOB_WEAK_LEVEL)
        self.assertEqual(formula["attackers"]["MOB_STRONG"]["ability_str"],
                         hpl.ATTACKER_MOB_STRONG_ABILITY_STR)

    def test_the_step_plan_reproduces_the_pinned_numbers(self):
        for label in HIT_STEP_LABELS:
            with self.subTest(step=label):
                self.assertEqual(hpl.step_damage_wire(step_index(label)),
                                 EXPECT_DAMAGE_SIGNED[label])

    def test_the_hp_steps_have_no_damage_number_at_all(self):
        for label in HP_STEP_LABELS:
            with self.subTest(step=label):
                self.assertNoBytes(
                    lambda i=step_index(label): hpl.step_damage_wire(i),
                    "unknown_step_label")

    def test_trap_a_drifted_formula_constant_cannot_ship_a_frame(self):
        """The recomputation guard, seen red through the REAL code path."""
        _scenario, unlock, _actions = sweep()
        with mock.patch.object(hpl, "ATK_BASE", 101):
            self.assertNoBytes(
                lambda: hpl.compute_hp_link_damage_wire("MOB_WEAK"),
                "formula_output_not_reproducible")
            self.assertNoBytes(
                lambda: hpl.build_damage_hp_link_sweep(
                    legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                    hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, sweep()[0]),
                "formula_output_not_reproducible")
        self.assertEqual(hpl.ATK_BASE, 100)

    def test_every_refusal_of_the_damage_wire_value_is_named(self):
        self.assertNoBytes(lambda: hpl.require_hp_link_damage_wire_value(1),
                           "damage_positive_heal_semantics_unknown")
        self.assertNoBytes(
            lambda: hpl.require_hp_link_damage_wire_value(hpl.INT32_MIN),
            "damage_is_int32_min")
        self.assertNoBytes(
            lambda: hpl.require_hp_link_damage_wire_value(-2_000_000),
            "damage_below_safe_band")
        for bad in (-63.0, True, False, "-63", None, complex(-63)):
            with self.subTest(damage=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.require_hp_link_damage_wire_value(b),
                    "damage_not_integer")

    def test_every_refusal_of_the_flag_word_is_named(self):
        for bad in (-1, 0x10000, True, 1.0, "1", None):
            with self.subTest(flags=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.require_hp_link_flags_value(b),
                    "flags_not_u16")
        self.assertNoBytes(lambda: hpl.require_hp_link_flags_value(0x0080),
                           "flags_forbidden_bit")
        self.assertNoBytes(lambda: hpl.require_hp_link_flags_value(0x0008),
                           "flags_outside_value_allowlist")
        # the damage lane's reaction word 0x0009 is NOT this lane's to send
        self.assertNoBytes(lambda: hpl.require_hp_link_flags_value(0x0009),
                           "flags_outside_value_allowlist")

    def test_the_number_and_the_flag_word_must_tell_the_same_story(self):
        self.assertNoBytes(
            lambda: hpl.require_hp_link_damage_and_flags_agree(0, 1),
            "damage_zero_with_apply_flag")
        self.assertNoBytes(
            lambda: hpl.require_hp_link_damage_and_flags_agree(-1, 0),
            "damage_nonzero_without_apply_flag")


# ===========================================================================
# 7.  THE LADDER: a server-held balance, moved only by the engine
# ===========================================================================
class LadderTests(NoBytesMixin, unittest.TestCase):
    def test_the_replayed_ladder_equals_the_pinned_tuple(self):
        self.assertEqual(hpl.replay_hp_link_balance_ladder(), EXPECT_LADDER)
        self.assertEqual(hpl.HP_LINK_BALANCE_LADDER, EXPECT_LADDER)
        self.assertEqual(hpl.require_hp_link_balance_ladder(), EXPECT_LADDER)

    def test_the_ladder_is_the_arithmetic_a_tester_can_check_by_hand(self):
        self.assertEqual(100 - 63, 37)
        self.assertEqual(hpl.apply_hit_to_balance(100, -63, hpl.FLAGS_HIT), 37)
        self.assertEqual(hpl.apply_hit_to_balance(37, 0, hpl.FLAGS_MISS), 37)
        self.assertEqual(hpl.apply_hit_to_balance(37, -379, hpl.FLAGS_HIT), 0)
        self.assertEqual(max(37 - 379, 0), 0)

    def test_the_declared_hp_specs_are_the_derived_balances(self):
        ladder = hpl.require_hp_link_balance_ladder()
        for index, (label, kind, spec, _flags) in enumerate(
            hpl.DAMAGE_HP_LINK_STEPS
        ):
            if kind != hpl.HP_LINK_STEP_KIND_HP or not spec:
                continue
            declared = spec.get("hp_current")
            if declared is None:
                continue
            with self.subTest(step=label):
                self.assertEqual(declared, ladder[index])

    def test_a_positive_damage_cannot_move_the_balance(self):
        self.assertNoBytes(
            lambda: hpl.apply_hit_to_balance(100, 63, hpl.FLAGS_HIT),
            "damage_positive_heal_semantics_unknown")

    def test_a_zero_damage_with_the_apply_flag_cannot_move_the_balance(self):
        self.assertNoBytes(
            lambda: hpl.apply_hit_to_balance(100, 0, hpl.FLAGS_HIT),
            "damage_zero_with_apply_flag")

    def test_a_nonzero_damage_without_the_apply_flag_cannot_move_it(self):
        self.assertNoBytes(
            lambda: hpl.apply_hit_to_balance(100, -63, hpl.FLAGS_MISS),
            "damage_nonzero_without_apply_flag")

    def test_a_non_integer_balance_or_damage_is_refused(self):
        for bad in (100.0, True, False, "100", None):
            with self.subTest(balance=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.apply_hit_to_balance(
                        b, -63, hpl.FLAGS_HIT),
                    "hp_balance_not_integer")
        self.assertNoBytes(
            lambda: hpl.apply_hit_to_balance(100, -63.0, hpl.FLAGS_HIT),
            "damage_not_integer")

    def test_a_balance_outside_the_declared_band_is_refused(self):
        for bad in (101, -1, 1 << 32):
            with self.subTest(balance=bad):
                self.assertNoBytes(
                    lambda b=bad: hpl.apply_hit_to_balance(
                        b, -63, hpl.FLAGS_HIT),
                    "hp_balance_outside_the_declared_band")

    def test_trap_a_clamp_anywhere_but_the_pinned_step_is_refused(self):
        """Make the WEAK hit lethal: the clamp would land on HP_AFTER_WEAK."""
        steps = list(hpl.DAMAGE_HP_LINK_STEPS)
        steps[step_index("HIT_WEAK")] = (
            "HIT_WEAK", hpl.HP_LINK_STEP_KIND_HIT, "MOB_STRONG", hpl.FLAGS_HIT)
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_STEPS", tuple(steps)):
            self.assertNoBytes(
                lambda: hpl.replay_hp_link_balance_ladder(),
                "hp_clamp_outside_the_pinned_step")

    def test_trap_a_pinned_clamp_step_that_does_not_clamp_is_refused(self):
        """Silence the strong hit: HP_ZERO_DYING would stop clamping."""
        steps = list(hpl.DAMAGE_HP_LINK_STEPS)
        steps[step_index("HIT_STRONG")] = (
            "HIT_STRONG", hpl.HP_LINK_STEP_KIND_HIT, None, hpl.FLAGS_MISS)
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_STEPS", tuple(steps)):
            self.assertNoBytes(
                lambda: hpl.replay_hp_link_balance_ladder(),
                "the pinned clamp step did not clamp")

    def test_trap_two_hit_frames_in_a_row_are_refused(self):
        """A number nothing applied is a lie waiting to happen."""
        steps = list(hpl.DAMAGE_HP_LINK_STEPS)
        steps[step_index("HP_AFTER_WEAK")] = (
            "HP_AFTER_WEAK", hpl.HP_LINK_STEP_KIND_HIT, "MOB_WEAK",
            hpl.FLAGS_HIT)
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_STEPS", tuple(steps)):
            self.assertNoBytes(
                lambda: hpl.replay_hp_link_balance_ladder(),
                "two hit frames in a row")

    def test_trap_a_tampered_ladder_constant_is_refused_on_every_build(self):
        _scenario, unlock, _actions = sweep()
        with mock.patch.object(hpl, "HP_LINK_BALANCE_LADDER",
                               (100, 100, 38, 37, 37, 37, 0, 0)):
            self.assertNoBytes(
                lambda: hpl.require_hp_link_balance_ladder(),
                "hp_arithmetic_not_reproducible")
            self.assertNoBytes(
                lambda: hpl.build_damage_hp_link_sweep(
                    legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                    hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, sweep()[0]),
                "hp_arithmetic_not_reproducible")
        self.assertEqual(hpl.HP_LINK_BALANCE_LADDER, EXPECT_LADDER)

    def test_the_lethal_fields_refuse_to_exist_outside_the_pinned_steps(self):
        _scenario, unlock, _actions = sweep()
        with_timer = dict(baseline_fields())
        with_timer[hpl.HP_LINK_DEATH_TIMER_NAME] = 20.0
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, with_timer, "HP_BASELINE",
                unlock),
            "lethal_field_outside_the_pinned_step")
        at_floor = dict(baseline_fields())
        at_floor["hp_current"] = 0
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, at_floor, "HP_AFTER_WEAK",
                unlock),
            "lethal_field_outside_the_pinned_step")

    def test_a_lethal_step_must_carry_both_halves_of_the_dying_window(self):
        _scenario, unlock, _actions = sweep()
        no_timer = hpl.damage_hp_link_step_fields(
            legacy(), step_index("HP_ZERO_DYING"))
        del no_timer[hpl.HP_LINK_DEATH_TIMER_NAME]
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, no_timer, "HP_ZERO_DYING",
                unlock),
            "lethal_field_outside_the_pinned_step")
        off_floor = hpl.damage_hp_link_step_fields(
            legacy(), step_index("HP_ZERO_DYING"))
        off_floor["hp_current"] = 1
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, off_floor, "HP_ZERO_DYING",
                unlock),
            "lethal_field_outside_the_pinned_step")

    def test_every_refusal_of_the_timer_value_is_named(self):
        _scenario, unlock, _actions = sweep()
        lethal_fields = hpl.damage_hp_link_step_fields(
            legacy(), step_index("HP_ZERO_DYING"))

        def encode(value, label="HP_ZERO_DYING"):
            fields = dict(lethal_fields)
            fields[hpl.HP_LINK_DEATH_TIMER_NAME] = value
            return hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, fields, label, unlock)

        self.assertNoBytes(lambda: encode(20), "death_timer_not_float")
        self.assertNoBytes(lambda: encode(True), "death_timer_not_float")
        self.assertNoBytes(lambda: encode(float("nan")),
                           "death_timer_not_finite")
        self.assertNoBytes(lambda: encode(float("inf")),
                           "death_timer_not_finite")
        self.assertNoBytes(lambda: encode(19.0),
                           "death_timer_outside_the_pinned_plan")
        self.assertNoBytes(lambda: encode(60.0),
                           "death_timer_outside_the_pinned_plan")

    def test_a_negative_zero_elapsed_timer_is_not_the_pinned_zero(self):
        """-0.0 == 0.0 in arithmetic but packs to different bytes; the wire
        check must catch what the equality check cannot."""
        _scenario, unlock, _actions = sweep()
        fields = hpl.damage_hp_link_step_fields(
            legacy(), step_index("DYING_ELAPSED"))
        fields[hpl.HP_LINK_DEATH_TIMER_NAME] = -0.0
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, fields, "DYING_ELAPSED",
                unlock),
            "death_timer_elapsed_is_not_the_pinned_zero")

    def test_the_step_field_projection_is_cumulative_and_hp_only(self):
        for label in HP_STEP_LABELS:
            fields = hpl.damage_hp_link_step_fields(
                legacy(), step_index(label))
            with self.subTest(step=label):
                self.assertEqual(
                    fields["hp_current"],
                    EXPECT_LADDER[step_index(label)])
                self.assertEqual(fields["hp_max"], 100)
        for label in HIT_STEP_LABELS:
            with self.subTest(step=label):
                self.assertNoBytes(
                    lambda i=step_index(label):
                    hpl.damage_hp_link_step_fields(legacy(), i),
                    "unknown_step_label")


# ===========================================================================
# 8.  TRAP TESTS
# ===========================================================================
class TrapTests(NoBytesMixin, unittest.TestCase):
    """A validator that cannot be made to fail is not a validator, and every
    trap here fires into the same code path the real check runs."""

    def test_positive_control_the_untouched_sweep_validates(self):
        _scenario, _unlock, actions = sweep()
        rows = hpl.validate_damage_hp_link_sweep(list(actions))
        self.assertEqual(len(rows), 8)
        self.assertEqual([r["label"] for r in rows],
                         list(hpl.DAMAGE_HP_LINK_STEP_ORDER))
        self.assertEqual([r.get("hp_current") for r in rows],
                         [100, None, 37, None, 37, None, 0, 0])
        self.assertEqual([r.get("damage_wire") for r in rows],
                         [None, -63, None, 0, None, -379, None, None])

    # ---- TRAP 1: a tampered pin dict ---------------------------------------
    def test_trap_a_tampered_pin_dict_makes_the_real_build_refuse(self):
        """The pins are load-bearing: edit one hash and the composer itself
        must refuse -- through build_damage_hp_link_sweep, not a copy."""
        scenario, unlock, _actions = sweep()
        tampered = json.loads(json.dumps(hpl.DAMAGE_HP_LINK_PINS))
        tampered["HIT_WEAK"]["pc_sha256"] = "0" * 64
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_PINS", tampered):
            self.assertNoBytes(
                lambda: hpl.build_damage_hp_link_sweep(
                    legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                    hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, scenario),
                "composed_bytes_do_not_match_the_pin")
        # and the real pins are untouched afterwards
        self.assertNotEqual(
            hpl.DAMAGE_HP_LINK_PINS["HIT_WEAK"]["pc_sha256"], "0" * 64)

    def test_trap_a_tampered_frame_size_pin_refuses_for_any_identity(self):
        scenario, unlock, _actions = sweep()
        tampered = json.loads(json.dumps(hpl.DAMAGE_HP_LINK_PINS))
        tampered["HP_BASELINE"]["pc_size"] = 1
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_PINS", tampered):
            self.assertNoBytes(
                lambda: hpl.make_damage_hp_link_step_response(
                    legacy(), 0x20010001, 0, 0, unlock),
                "composed_bytes_do_not_match_the_pin")
            _ = scenario  # the scenario object itself is untouched

    # ---- TRAP 2: a forged unlock that compares EQUAL -----------------------
    def test_trap_a_forged_unlock_that_compares_equal_to_the_real_one(self):
        """Proves the gate is `is`, not `==`."""
        scenario, unlock, _actions = sweep()
        forged = hpl.DamageHpLinkWireUnlock(
            hpl.DAMAGE_HP_LINK_SCENARIO_ID, hpl.DAMAGE_HP_LINK_HYPOTHESIS_ID)
        self.assertEqual(forged, unlock)      # equal ...
        self.assertIsNot(forged, unlock)      # ... and still not the key
        self.assertNoBytes(
            lambda: hpl.build_damage_hp_link_sweep(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, forged, scenario),
            "missing_or_forged_wire_unlock")
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_hit_entry(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, -63,
                (float(legacy().V135_PLAYER_X), float(legacy().V135_PLAYER_Y),
                 float(legacy().V135_PLAYER_Z)),
                hpl.YAW_PINNED, hpl.FLAGS_HIT, forged),
            "missing_or_forged_wire_unlock")
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, baseline_fields(),
                "HP_BASELINE", forged),
            "missing_or_forged_wire_unlock")

    # ---- TRAP 3: a scenario tree one key away from the allowlist -----------
    def test_trap_a_scenario_file_with_one_key_added_or_removed(self):
        base = json.loads(SCENARIO.read_text(encoding="utf-8"))
        variants = {
            "extra top level key": lambda d: d.update(extra=1),
            "missing top level key": lambda d: d.pop("test_only"),
            "extra nested key": lambda d: d["wire"].update(sneaky=1),
            "missing nested key": lambda d: d["wire"]["formula"].pop(
                "uses_random"),
            "extra per step key": lambda d: d["probe"]["per_step"]
            ["MISS"].update(note="hello"),
            "missing per step key": lambda d: d["probe"]["per_step"]
            ["HIT_WEAK"].pop("frame_sha256"),
            "production allowed": lambda d: d.update(production_allowed=True),
            "not test only": lambda d: d.update(test_only=False),
            "edited pin": lambda d: d["probe"]["per_step"]["HIT_WEAK"].update(
                pc_size=1),
            "edited formula constant": lambda d: d["wire"]["formula"].update(
                atk_base=101),
            "edited ladder": lambda d: d["wire"]["hp_ladder"].update(
                ladder=[100, 100, 38, 37, 37, 37, 0, 0]),
            "edited clamp step": lambda d: d["wire"]["hp_ladder"].update(
                clamp_step="DYING_ELAPSED"),
            "edited spacing": lambda d: d["dispatch"].update(
                spacing_seconds=6.0),
            "edited timer": lambda d: d["wire"]["timer"].update(
                dying_seconds=60.0),
            "not one shot": lambda d: d["dispatch"].update(one_shot=False),
            "reordered steps": lambda d: d["dispatch"].update(
                step_order=list(reversed(d["dispatch"]["step_order"]))),
        }
        for label, mutate in variants.items():
            with self.subTest(variant=label):
                data = json.loads(json.dumps(base))
                mutate(data)
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "scenario.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.assertNoBytes(
                        lambda p=path:
                        hpl.load_damage_hp_link_hypothesis_scenario(p),
                        "scenario_file_exceeds_allowlist")

    def test_trap_a_scenario_path_that_is_not_json_or_not_there_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "scenario.json"
            broken.write_text("not json at all", encoding="utf-8")
            self.assertNoBytes(
                lambda: hpl.load_damage_hp_link_hypothesis_scenario(broken),
                "scenario_file_exceeds_allowlist")
            self.assertNoBytes(
                lambda: hpl.load_damage_hp_link_hypothesis_scenario(
                    Path(tmp) / "nothing_here.json"),
                "scenario_file_exceeds_allowlist")
        self.assertNoBytes(
            lambda: hpl.load_damage_hp_link_hypothesis_scenario(None),
            "scenario_file_exceeds_allowlist")

    def test_trap_a_scenario_object_that_is_not_the_pinned_plan(self):
        lookalike = hpl.DamageHpLinkHypothesisScenario(
            hpl.DAMAGE_HP_LINK_SCENARIO_ID, hpl.DAMAGE_HP_LINK_HYPOTHESIS_ID,
            tuple(reversed(hpl.DAMAGE_HP_LINK_STEP_ORDER)),
            hpl.DAMAGE_HP_LINK_SPACING_SECONDS,
            hpl.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
            hpl.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX,
        )
        for impostor in (lookalike, object(), None, "scenario"):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor:
                    hpl.require_damage_hp_link_hypothesis_scenario(i),
                    "scenario_object_exceeds_allowlist")
                self.assertNoBytes(
                    lambda i=impostor: hpl.damage_hp_link_wire_unlock(i),
                    "scenario_object_exceeds_allowlist")

    def test_trap_an_equal_scenario_object_still_mints_no_unlock(self):
        """Identity, not equality, is the minter's gate."""
        equal_twin = hpl.DamageHpLinkHypothesisScenario(
            hpl.DAMAGE_HP_LINK_SCENARIO_ID, hpl.DAMAGE_HP_LINK_HYPOTHESIS_ID,
            hpl.DAMAGE_HP_LINK_STEP_ORDER,
            hpl.DAMAGE_HP_LINK_SPACING_SECONDS,
            hpl.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
            hpl.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX,
        )
        scenario, _unlock, _actions = sweep()
        self.assertEqual(equal_twin, scenario)
        self.assertIsNot(equal_twin, scenario)
        self.assertNoBytes(
            lambda: hpl.damage_hp_link_wire_unlock(equal_twin),
            "scenario_object_exceeds_allowlist")

    # ---- TRAP 4: the step list itself --------------------------------------
    def test_trap_a_reordered_step_list_refuses_through_the_real_build(self):
        scenario, unlock, _actions = sweep()
        reordered = (
            hpl.DAMAGE_HP_LINK_STEPS[1], hpl.DAMAGE_HP_LINK_STEPS[0],
        ) + hpl.DAMAGE_HP_LINK_STEPS[2:]
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_STEPS", reordered):
            self.assertNoBytes(
                lambda: hpl.build_damage_hp_link_sweep(
                    legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                    hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, scenario),
                "unknown_step_label")
        self.assertEqual(hpl.DAMAGE_HP_LINK_STEPS[0][0], "HP_BASELINE")

    def test_trap_a_sweep_that_never_shows_the_miss_control(self):
        """The MISS pair is the experiment's control, not filler."""
        scenario, unlock, _actions = sweep()
        steps = list(hpl.DAMAGE_HP_LINK_STEPS)
        steps[step_index("MISS")] = (
            "MISS", hpl.HP_LINK_STEP_KIND_HIT, "MOB_WEAK", hpl.FLAGS_HIT)
        with mock.patch.object(hpl, "DAMAGE_HP_LINK_STEPS", tuple(steps)):
            self.assertNoBytes(
                lambda: hpl.build_damage_hp_link_sweep(
                    legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                    hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, scenario),
                "sweep_does_not_contain_a_miss_frame")
        self.assertIsNone(hpl.DAMAGE_HP_LINK_STEPS[step_index("MISS")][2])

    # ---- TRAP 5: step indices that are not steps ----------------------------
    def test_trap_step_index_true_minus_one_and_len(self):
        _scenario, unlock, _actions = sweep()
        for index in (True, False, -1, len(hpl.DAMAGE_HP_LINK_STEP_ORDER),
                      99, 1.0, "0", None):
            with self.subTest(index=repr(index)):
                self.assertNoBytes(
                    lambda i=index: hpl.step_plan(i), "unknown_step_label")
                self.assertNoBytes(
                    lambda i=index: hpl.make_damage_hp_link_step_response(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                        hpl.HP_LINK_PROBE_IDENTITY_HI, i, unlock),
                    "unknown_step_label")

    # ---- mutated-sweep traps, through the real validator --------------------
    def test_trap_a_positive_damage_edited_onto_the_wire(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_i32(rows[index][1], DAMAGE_TAG_AT + 1, 63))
        self.assertSweepRejected(
            mutate, "damage_positive_heal_semantics_unknown")

    def test_trap_int32_min_edited_onto_the_wire(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_i32(rows[index][1], DAMAGE_TAG_AT + 1, hpl.INT32_MIN))
        self.assertSweepRejected(mutate, "damage_is_int32_min")

    def test_trap_a_forbidden_flag_bit_edited_onto_the_wire(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_u16(rows[index][1], FLAGS_TAG_AT + 1, 0x0080))
        self.assertSweepRejected(mutate, "flags_forbidden_bit")

    def test_trap_a_flag_word_outside_the_value_allowlist(self):
        self.assertFalse(0x0008 & hpl.FLAGS_FORBIDDEN_MASK)

        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_u16(rows[index][1], FLAGS_TAG_AT + 1, 0x0008))
        self.assertSweepRejected(mutate, "flags_outside_value_allowlist")

    def test_trap_damage_zero_carrying_the_apply_flag(self):
        def mutate(rows):
            index = step_index("MISS")
            repack(rows, index,
                   patch_u16(rows[index][1], FLAGS_TAG_AT + 1, 0x0001))
        self.assertSweepRejected(mutate, "damage_zero_with_apply_flag")

    def test_trap_a_nonzero_damage_without_the_apply_flag(self):
        def mutate(rows):
            index = step_index("HIT_STRONG")
            repack(rows, index,
                   patch_u16(rows[index][1], FLAGS_TAG_AT + 1, 0x0000))
        self.assertSweepRejected(mutate, "damage_nonzero_without_apply_flag")

    def test_trap_a_number_the_arithmetic_did_not_produce(self):
        """The hit announced -63 but the bar shows 36: the link is the lie."""
        def mutate(rows):
            index = step_index("HP_AFTER_WEAK")
            repack(rows, index,
                   patch_u32(rows[index][1], HP_CURRENT_TAG_AT + 1, 36))
        self.assertSweepRejected(mutate, "hp_arithmetic_not_reproducible")

    def test_trap_an_edited_hp_max(self):
        def mutate(rows):
            index = step_index("HP_BASELINE")
            repack(rows, index,
                   patch_u32(rows[index][1], HP_MAX_TAG_AT + 1, 99))
        self.assertSweepRejected(mutate, "composed_bytes_do_not_match_the_pin")

    def test_trap_an_edited_dying_timer(self):
        def mutate(rows):
            index = step_index("HP_ZERO_DYING")
            repack(rows, index,
                   patch_f32(rows[index][1], LETHAL_TIMER_TAG_AT + 1, 19.0))
        self.assertSweepRejected(mutate, "death_timer_outside_the_pinned_plan")

    def test_trap_an_elapsed_timer_that_is_not_zero(self):
        def mutate(rows):
            index = step_index("DYING_ELAPSED")
            repack(rows, index,
                   patch_f32(rows[index][1], LETHAL_TIMER_TAG_AT + 1, 20.0))
        self.assertSweepRejected(mutate, "death_timer_outside_the_pinned_plan")

    def test_trap_the_base_change_mask_cleared(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[BASE_CHANGE_MASK_VALUE_AT] = 0x00
            repack(rows, 0, pc)
        self.assertSweepRejected(
            mutate, "base change mask does not select the VitalData collection")

    def test_trap_a_derived_change_mask_that_should_not_be_there(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[len(pc) - 1] = 0x02
            repack(rows, 0, pc)
        self.assertSweepRejected(
            mutate, "derived change mask must be absent on this lane")

    def test_trap_the_wrong_envelope_id(self):
        def mutate(rows):
            repack(rows, 0,
                   patch_u16(rows[0][1], ENVELOPE_ID_VALUE_AT, 0x16F7))
        self.assertSweepRejected(mutate, "envelope id is not 0x6E9D")

    def test_trap_the_wrong_envelope_version(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[ENVELOPE_VERSION_VALUE_AT] = 3
            repack(rows, 0, pc)
        self.assertSweepRejected(mutate, "envelope is not version 4")

    def test_trap_a_nonzero_vital_version_byte(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[VITAL_VERSION_VALUE_AT] = 1
            repack(rows, 0, pc)
        self.assertSweepRejected(mutate, "vital_version_not_pinned")

    def test_trap_a_swapped_carrier_kind(self):
        """The baseline slot carrying a hit frame is not the plan."""
        def mutate(rows):
            hit = rows[step_index("HIT_WEAK")]
            rows[0][1] = hit[1]
            rows[0][2] = hit[2]
        self.assertSweepRejected(
            mutate, "composed_bytes_do_not_match_the_pin")

    def test_trap_a_nonzero_reserved_header_field(self):
        for at in (30, 33, 36, 41):
            with self.subTest(at=at):
                def mutate(rows, at=at):
                    index = step_index("HIT_WEAK")
                    pc = bytearray(rows[index][1])
                    pc[at] = 1
                    repack(rows, index, pc)
                self.assertSweepRejected(
                    mutate, "header_reserved_field_nonzero")

    def test_trap_a_target_that_is_not_the_performer(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            pc = bytearray(rows[index][1])
            pc[HIT_ENTRY_AT + 1:HIT_ENTRY_AT + 9] = struct.pack("<Q", 7)
            repack(rows, index, pc)
        self.assertSweepRejected(
            mutate, "performer_identity_not_the_selected_actor")

    def test_trap_a_frame_whose_performer_differs_from_the_rest(self):
        scenario, unlock, actions = sweep()
        other = hpl.build_damage_hp_link_sweep(
            legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO + 1,
            hpl.HP_LINK_PROBE_IDENTITY_HI, unlock, scenario)

        def mutate(rows):
            index = step_index("HIT_WEAK")
            rows[index][1] = other[index][1]
            rows[index][2] = other[index][2]
        self.assertSweepRejected(
            mutate, "performer_identity_not_the_selected_actor")
        _ = actions

    def test_trap_a_position_edited_to_a_non_finite_value(self):
        """A FINITE position edit on the probe identity trips the byte pin
        first (asserted separately below); the position guard's own name is
        reachable on the wire through the one value the pin cannot outrank,
        a NaN component, and at the encoder for every malformed shape."""
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_f32(rows[index][1], POSITION_TAG_AT + 1,
                             float("nan")))
        self.assertSweepRejected(mutate, "position_not_from_the_pinned_source")

    def test_trap_a_finite_position_edit_still_cannot_ship_past_the_pin(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_f32(rows[index][1], POSITION_TAG_AT + 1, 1.0))
        self.assertSweepRejected(mutate, "composed_bytes_do_not_match_the_pin")

    def test_trap_a_malformed_position_straight_at_the_encoder(self):
        _scenario, unlock, _actions = sweep()
        x = float(legacy().V135_PLAYER_X)
        y = float(legacy().V135_PLAYER_Y)
        z = float(legacy().V135_PLAYER_Z)
        for bad in ((x, y), (x, y, z, 0.0), [x, y, z], None, "xyz",
                    (float("nan"), y, z), (float("inf"), y, z),
                    (1, y, z), (True, y, z)):
            with self.subTest(position=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.encode_hp_link_hit_entry(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, -63, b,
                        hpl.YAW_PINNED, hpl.FLAGS_HIT, unlock),
                    "position_not_from_the_pinned_source")

    def test_trap_a_yaw_edited_after_composition(self):
        def mutate(rows):
            index = step_index("HIT_WEAK")
            repack(rows, index,
                   patch_f32(rows[index][1], YAW_TAG_AT + 1, 1.5))
        self.assertSweepRejected(mutate, "yaw_outside_pinned_value")

    def test_trap_a_truncated_frame(self):
        def mutate(rows):
            repack(rows, 0, bytearray(rows[0][1][:-4]))
        self.assertSweepRejected(mutate, "truncated")

    def test_trap_a_frame_that_is_not_the_transport_of_its_pc(self):
        def mutate(rows):
            rows[0][2] = b"\x00" * len(rows[0][2])
        self.assertSweepRejected(
            mutate, "transport_frame_does_not_reproduce_the_pc")

    def test_trap_a_delay_that_is_not_the_plan(self):
        def mutate(rows):
            rows[0][3] = 15.0
        self.assertSweepRejected(mutate, "sweep delay is not the plan")

    def test_trap_a_relabelled_step_in_a_composed_sweep(self):
        def mutate(rows):
            rows[4][0] = "HYP_PF_026_HP_LINK_SOMETHING_ELSE"
        self.assertSweepRejected(mutate, "unknown_step_label")

    def test_trap_a_sweep_of_the_wrong_length(self):
        _scenario, _unlock, actions = sweep()
        for bad in (list(actions[:7]), list(actions) + list(actions[:1]), []):
            with self.subTest(length=len(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.validate_damage_hp_link_sweep(b),
                    "sweep length is not the pinned plan")

    def test_trap_an_identity_outside_the_qword_range(self):
        _scenario, unlock, _actions = sweep()
        position = (
            float(legacy().V135_PLAYER_X), float(legacy().V135_PLAYER_Y),
            float(legacy().V135_PLAYER_Z),
        )
        for bad in (-1, 1 << 64, True, "0", None, 1.0):
            with self.subTest(identity=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.encode_hp_link_hit_entry(
                        legacy(), b, -63, position, hpl.YAW_PINNED,
                        hpl.FLAGS_HIT, unlock),
                    "target_identity_outside_qword")
        for bad in (-1, 1 << 32, True, None):
            with self.subTest(identity_pair=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.encode_hp_link_actor_attr(
                        legacy(), b, 0, baseline_fields(), "HP_BASELINE",
                        unlock),
                    "target_identity_outside_qword")

    def test_trap_an_entry_count_that_is_not_one(self):
        _scenario, unlock, _actions = sweep()
        position = (
            float(legacy().V135_PLAYER_X), float(legacy().V135_PLAYER_Y),
            float(legacy().V135_PLAYER_Z),
        )
        entry = hpl.encode_hp_link_hit_entry(
            legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, -63, position,
            hpl.YAW_PINNED, hpl.FLAGS_HIT, unlock)
        for bad in ([], [entry, entry], tuple([entry])):
            with self.subTest(count=len(bad)):
                self.assertNoBytes(
                    lambda b=bad: hpl.encode_hp_link_chit_result(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, b, unlock),
                    "entry_count_not_pinned")

    def test_trap_a_field_outside_the_pinned_table(self):
        _scenario, unlock, _actions = sweep()
        fields = dict(baseline_fields())
        fields["mp_current"] = 50
        self.assertNoBytes(
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI, fields, "HP_BASELINE", unlock),
            "hp_field_outside_the_pinned_table")

    def test_trap_a_sparse_delta_missing_a_baseline_field(self):
        """A dropped field is an overwritten field on the client; refused."""
        _scenario, unlock, _actions = sweep()
        for missing in ("hp_current", "hp_max", "cash", "character_name",
                        "scene_id", "scene_sequence"):
            fields = dict(baseline_fields())
            del fields[missing]
            with self.subTest(missing=missing):
                self.assertNoBytes(
                    lambda f=fields: hpl.encode_hp_link_actor_attr(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                        hpl.HP_LINK_PROBE_IDENTITY_HI, f, "HP_BASELINE",
                        unlock),
                    "hp_frame_missing_baseline_field")


# ===========================================================================
# 9.  NO LEAK WITHOUT THE SCENARIO
# ===========================================================================
class FailClosedWithoutTheScenarioTests(NoBytesMixin, unittest.TestCase):
    """A process that never opted in cannot compose either carrier at all."""

    def test_the_hit_entry_encoder_refuses_every_impostor_unlock(self):
        position = (
            float(legacy().V135_PLAYER_X), float(legacy().V135_PLAYER_Y),
            float(legacy().V135_PLAYER_Z),
        )
        for impostor in (None, object(), "unlock", 0, False,
                         hpl.DamageHpLinkWireUnlock("", "")):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: hpl.encode_hp_link_hit_entry(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, -63,
                        position, hpl.YAW_PINNED, hpl.FLAGS_HIT, i),
                    "missing_or_forged_wire_unlock")

    def test_the_actor_attr_encoder_refuses_every_impostor_unlock(self):
        for impostor in (None, object(), "unlock", 0, False):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: hpl.encode_hp_link_actor_attr(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                        hpl.HP_LINK_PROBE_IDENTITY_HI, baseline_fields(),
                        "HP_BASELINE", i),
                    "missing_or_forged_wire_unlock")

    def test_the_step_encoder_and_the_sweep_builder_refuse_without_it(self):
        scenario, _unlock, _actions = sweep()
        for impostor in (None, object(), "unlock"):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: hpl.make_damage_hp_link_step_response(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                        hpl.HP_LINK_PROBE_IDENTITY_HI, 0, i),
                    "missing_or_forged_wire_unlock")
                self.assertNoBytes(
                    lambda i=impostor: hpl.build_damage_hp_link_sweep(
                        legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                        hpl.HP_LINK_PROBE_IDENTITY_HI, i, scenario),
                    "missing_or_forged_wire_unlock")

    def test_the_unlock_cannot_be_minted_from_anything_but_the_scenario(self):
        for impostor in (None, object(),
                         "damage_hp_link_hypothesis_link_sweep",
                         {"id": hpl.DAMAGE_HP_LINK_SCENARIO_ID}):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: hpl.damage_hp_link_wire_unlock(i),
                    "scenario_object_exceeds_allowlist")

    def test_the_only_unlock_that_works_comes_from_the_shipped_file(self):
        scenario = hpl.load_damage_hp_link_hypothesis_scenario(SCENARIO)
        unlock = hpl.damage_hp_link_wire_unlock(scenario)
        self.assertIs(unlock, hpl.require_damage_hp_link_wire_unlock(unlock))
        entry = hpl.encode_hp_link_hit_entry(
            legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO, -63,
            (float(legacy().V135_PLAYER_X), float(legacy().V135_PLAYER_Y),
             float(legacy().V135_PLAYER_Z)),
            hpl.YAW_PINNED, hpl.FLAGS_HIT, unlock)
        self.assertEqual(len(entry), hpl.HIT_ELEMENT_WIRE_SIZE)

    def test_the_lane_never_claims_production(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(on_disk["production_allowed"], False)
        self.assertIs(on_disk["test_only"], True)
        self.assertEqual(on_disk["persisted_post_state"]["database_write"],
                         "none")
        self.assertEqual(on_disk["dispatch"]["socket_action"], "none")
        self.assertIs(hpl.production_allowed, False)


# ===========================================================================
# 10. CONTAINMENT: copied, not imported, and nobody else touches the lane
# ===========================================================================
class ContainmentTests(unittest.TestCase):
    def test_the_module_never_names_either_neighbour_lane(self):
        """The copies must stay copies: a substring match would widen the
        neighbours' containment tests, so even a comment may not say the
        names.  The drift checks live in THIS file instead."""
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("stats_progression_hypothesis", source)
        self.assertNotIn("damage_model_hypothesis", source)
        self.assertNotIn("make_remote_actor_entry", source)

    def test_the_module_touches_the_shared_envelope_helper_exactly_once(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("make_runtime_vitals("), 1)

    def test_the_modules_import_lines_import_no_neighbour(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        import_lines = [
            line for line in source.splitlines()
            if line.startswith(("import ", "from "))
        ]
        self.assertTrue(import_lines)
        for line in import_lines:
            with self.subTest(line=line):
                for banned in ("stats_progression", "damage_model",
                               "remote_player", "runtimeres_death",
                               "chat_input", "channel_message"):
                    self.assertNotIn(banned, line)
        self.assertIn("from .population import RUNTIME_PROTOCOL_RES_ID",
                      import_lines)

    def test_exactly_two_foundation_modules_mention_the_lane(self):
        module = "damage_hp_link_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py", "session.py",
                     "store.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name)

    def test_the_module_opens_no_database_and_no_socket(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        for banned in ("sqlite3", "SQLiteStore", "INSERT ", "DELETE FROM",
                       "import socket", "socket.socket", "connect("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)


# ===========================================================================
# 11. THE REAL VERIFIER
# ===========================================================================
class VerifierTests(unittest.TestCase):
    """Run the lane's own verifier as a real subprocess, exactly as the gate
    does."""

    @unittest.skipUnless(
        TOOL.exists(),
        "tools/verify_damage_hp_link_encoder.py is not written yet")
    def test_the_verifier_exits_zero_and_reports_more_than_zero_guards(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL)],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, output[-4000:])
        match = GUARD_SUMMARY_RE.search(output)
        self.assertIsNotNone(
            match, "no 'guards run: N' summary line:\n" + output[-4000:])
        self.assertGreater(int(match.group(1)), 0, output[-4000:])
        self.assertIn("RESULT: PASS", output)

    @unittest.skipUnless(
        TOOL.exists(),
        "tools/verify_damage_hp_link_encoder.py is not written yet")
    def test_the_verifier_prints_nothing_a_cp874_console_cannot_show(self):
        proc = subprocess.run(
            [sys.executable, str(TOOL)],
            cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=600,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.assertTrue(
            output.isascii(),
            "the verifier printed non-ASCII, which dies on a cp874 console")

    @unittest.skipUnless(
        TOOL.exists(),
        "tools/verify_damage_hp_link_encoder.py is not written yet")
    def test_the_verifier_needs_no_third_party_package(self):
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests"):
            with self.subTest(package=banned):
                self.assertNotIn("import " + banned, source)


# ===========================================================================
# 12. LEDGER BINDING
# ===========================================================================
class LedgerBindingTests(unittest.TestCase):
    """HYP-PF-026 must be registered, active, bounded, and bound both ways.

    Everything here is READ from the ledger, never copied: a marker added to
    the ledger and forgotten in the source must turn this red without anyone
    remembering to edit a test.
    """

    def entry(self):
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        for entry in ledger["entries"]:
            if entry["id"] == hpl.DAMAGE_HP_LINK_HYPOTHESIS_ID:
                return entry
        self.fail("HYP-PF-026 is not registered in docs/HYPOTHESIS_LEDGER.json")

    def test_the_hypothesis_is_registered_active_and_bounded(self):
        entry = self.entry()
        self.assertEqual(entry["id"], "HYP-PF-026")
        self.assertEqual(entry["introduced_checkpoint"], "DAMAGE-HP-LINK-001")
        self.assertEqual(entry["status"], "active")
        self.assertIs(entry["production_allowed"], False)
        self.assertEqual(entry["max_versions"], 3)
        # tracked_versions lives INSIDE expiry -- the ledger verifier is
        # field-exact at the top level and would reject it anywhere else.
        self.assertEqual(
            entry["expiry"]["tracked_versions"], ["DAMAGE-HP-LINK-001"])

    def test_the_scenario_file_and_the_ledger_agree_on_the_registration(self):
        entry = self.entry()
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(
            on_disk["hypothesis_id_is_registered_in_the_ledger"], True)
        self.assertEqual(on_disk["hypothesis_id"], entry["id"])

    def test_the_evidence_refs_name_every_artifact_of_this_lane(self):
        refs = self.entry()["evidence_refs"]
        for required in (
            "scenarios/damage_hp_link_hypothesis_link_sweep.json",
            REPORT_PATH,
            VERIFIER_PATH,
            REPLAY_TOOL_PATH,
            "tests/test_damage_hp_link_hypothesis.py",
            "tests/test_damage_hp_link_dispatch.py",
        ):
            with self.subTest(ref=required):
                self.assertIn(required, refs)

    def test_every_source_ref_marker_the_ledger_claims_is_really_there(self):
        entry = self.entry()
        refs = entry["source_refs"]
        self.assertTrue(refs, "HYP-PF-026 carries no source_refs")
        checked = 0
        for ref in refs:
            path = ROOT / ref["path"]
            with self.subTest(path=ref["path"]):
                self.assertTrue(path.is_file(),
                                "%s does not exist" % ref["path"])
                source = path.read_text(encoding="utf-8")
                markers = ref["required_markers"]
                self.assertTrue(markers, "%s claims no markers" % ref["path"])
                for marker in markers:
                    with self.subTest(marker=marker):
                        self.assertIn(marker, source)
                    checked += 1
        self.assertGreater(checked, 0)

    def test_the_module_and_the_scenario_are_both_bound(self):
        paths = {ref["path"] for ref in self.entry()["source_refs"]}
        self.assertIn(
            "src/pirateforce_foundation/damage_hp_link_hypothesis.py", paths)
        self.assertIn(
            "scenarios/damage_hp_link_hypothesis_link_sweep.json", paths)

    def test_the_active_claim_annotation_is_in_the_module(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("PF-HYPOTHESIS-LEDGER: HYP-PF-026 active", source)
        self.assertEqual(
            source.count("PF-HYPOTHESIS-LEDGER: HYP-PF-026 active"), 1)


# ===========================================================================
# 13. THE SCENARIO FILE ITSELF
# ===========================================================================
class ScenarioFileTests(unittest.TestCase):
    def data(self):
        return json.loads(SCENARIO.read_text(encoding="utf-8"))

    def test_the_nonclaims_on_disk_are_the_modules_nonclaims(self):
        self.assertEqual(self.data()["nonclaims"],
                         list(hpl.DAMAGE_HP_LINK_NONCLAIMS))
        self.assertIn("no_database_write_no_hp_column_exists_and_none_is_added",
                      hpl.DAMAGE_HP_LINK_NONCLAIMS)
        self.assertIn("one_shot_per_process", hpl.DAMAGE_HP_LINK_NONCLAIMS)
        self.assertIn("no_claim_about_any_death_window_exit_path",
                      hpl.DAMAGE_HP_LINK_NONCLAIMS)

    def test_the_capabilities_on_disk_are_the_modules_capabilities(self):
        self.assertEqual(self.data()["capabilities"],
                         list(hpl.DAMAGE_HP_LINK_CAPABILITIES))

    def test_the_dispatch_section_is_the_pinned_plan(self):
        dispatch = self.data()["dispatch"]
        self.assertEqual(dispatch["step_order"],
                         list(hpl.DAMAGE_HP_LINK_STEP_ORDER))
        self.assertEqual(dispatch["action_labels"],
                         list(hpl.DAMAGE_HP_LINK_ACTION_LABELS))
        self.assertEqual(dispatch["spacing_seconds"], 15.0)
        self.assertEqual(dispatch["first_frame_delay_seconds"], 0.0)
        self.assertEqual(dispatch["frames_per_accepted_request"], 8)
        self.assertIs(dispatch["one_shot"], True)
        self.assertIs(dispatch["wired"], True)

    def test_the_ladder_and_timer_sections_are_the_modules_numbers(self):
        wire = self.data()["wire"]
        self.assertEqual(wire["hp_ladder"]["ladder"], list(EXPECT_LADDER))
        self.assertEqual(wire["hp_ladder"]["start"], 100)
        self.assertEqual(wire["hp_ladder"]["max"], 100)
        self.assertEqual(wire["hp_ladder"]["floor"], 0)
        self.assertEqual(wire["hp_ladder"]["clamp_step"], "HP_ZERO_DYING")
        self.assertEqual(wire["timer"]["dying_seconds"], 20.0)
        self.assertEqual(wire["timer"]["elapsed_seconds"], 0.0)
        self.assertEqual(wire["timer"]["duration_dying_image_default"], 20)
        self.assertEqual(wire["timer"]["window_margin_seconds"], 0.5)
        self.assertEqual(wire["timer"]["elapsed_wire_bytes"], "2a00000000")

    def test_every_number_on_disk_is_decimal_no_hex_string_anywhere(self):
        raw = SCENARIO.read_text(encoding="utf-8")
        self.assertNotIn("0x", raw)
        self.assertNotIn("0X", raw)
        probe = self.data()["probe"]
        self.assertEqual(probe["identity_lo"], 268500993)  # 0x10010001
        self.assertEqual(probe["identity_lo"],
                         hpl.HP_LINK_PROBE_IDENTITY_LO)
        self.assertEqual(probe["identity_hi"], 0)

    def test_the_file_byte_round_trips_through_json(self):
        raw = SCENARIO.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertEqual(json.dumps(data, indent=2) + "\n", raw)


# ===========================================================================
# 14. THE cp874 LESSON
# ===========================================================================
class AsciiOnlyTests(unittest.TestCase):
    def test_this_test_file_is_pure_ascii(self):
        """Anything this file can print has to survive a cp874 console."""
        source = Path(__file__).read_text(encoding="utf-8")
        self.assertTrue(source.isascii())

    def test_the_module_and_the_scenario_are_pure_ascii_too(self):
        for path in (MODULE_SOURCE_PATH, SCENARIO):
            with self.subTest(path=path.name):
                self.assertTrue(
                    path.read_text(encoding="utf-8").isascii())

    def test_the_sibling_dispatch_test_file_is_pure_ascii_too(self):
        sibling = Path(__file__).resolve().parent / (
            "test_damage_hp_link_dispatch.py"
        )
        self.assertTrue(sibling.is_file())
        self.assertTrue(sibling.read_text(encoding="utf-8").isascii())

    def test_every_rejection_message_this_lane_can_raise_is_ascii(self):
        scenario, unlock, actions = sweep()
        raised = []
        probes = (
            lambda: hpl.require_hp_link_damage_wire_value(1),
            lambda: hpl.require_hp_link_damage_wire_value(hpl.INT32_MIN),
            lambda: hpl.require_hp_link_flags_value(0x0080),
            lambda: hpl.require_hp_link_flags_value(0x0008),
            lambda: hpl.require_hp_link_damage_and_flags_agree(0, 1),
            lambda: hpl.require_hp_link_damage_and_flags_agree(-1, 0),
            lambda: hpl.step_plan(-1),
            lambda: hpl.apply_hit_to_balance(101, -63, hpl.FLAGS_HIT),
            lambda: hpl.damage_hp_link_wire_unlock(object()),
            lambda: hpl.require_damage_hp_link_wire_unlock(object()),
            lambda: hpl.load_damage_hp_link_hypothesis_scenario(None),
            lambda: hpl.decode_hp_link_transport(b"short"),
            lambda: hpl.validate_damage_hp_link_sweep(list(actions[:1])),
            lambda: hpl.encode_hp_link_actor_attr(
                legacy(), hpl.HP_LINK_PROBE_IDENTITY_LO,
                hpl.HP_LINK_PROBE_IDENTITY_HI,
                {"mp_current": 1, **baseline_fields()}, "HP_BASELINE", unlock),
        )
        for thunk in probes:
            try:
                thunk()
            except hpl.DamageHpLinkValidationError as exc:
                raised.append(str(exc))
        self.assertEqual(len(raised), len(probes))
        for message in raised:
            with self.subTest(message=message):
                self.assertTrue(message.isascii())
        _ = scenario


if __name__ == "__main__":
    unittest.main()
