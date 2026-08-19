"""DAMAGE-ENCODER-001 / HYP-PF-024: pin the CHitResult hit sweep to its bytes.

The lane's claim is that four composed ``GSCN_RunTimeProtocolRes`` frames, each
carrying ONE ``CHitResult`` (wire id ``0x16F7``, **version byte 0**) as the
single element of the VitalData collection, can put a number of OUR OWN
choosing on a client's screen -- and, once, deliberately put NO number there.
Every part of that claim is a statement about bytes, so these tests assert
bytes: the complete hex of all four PCs of the pinned probe identity, the two
change masks, the four reserved header fields, the 22/3/37 payload widths, and
the exact five bytes that carry ``-63``.

WHOSE NUMBERS THESE ARE
-----------------------
The formula is this project's, not the original server's -- round 83 proved the
client computes nothing and there is therefore nothing in the image to recover
a formula from.  So the formula tests here are not "does it match the server",
they are "is it OURS, is it reproducible, and does it stay inside the band we
declared": 63 and 379 from the pinned profiles, ``-1`` at the floor, the same
answer 100 times running, and no ``random`` anywhere in the module source.

THE SIGN IS THE MEANING
-----------------------
``+0x08`` is read SIGNED.  A negative value is the took-damage side and the
player still sees a positive figure because the display path calls ``abs()``.
That is the single easiest thing in this lane to get backwards, so it is pinned
twice: once as the decoded integer (``-63 / -379 / 0 / -63``) and once as the
literal bytes ``14 c1 ff ff ff`` -- tag ``0x14`` followed by the little-endian
two's complement of 63.

TRAP TESTS
----------
A validator that cannot be made to fail is not a validator, it is a printout.
:class:`TrapTests` builds deliberately malformed sweeps and entries and
requires the guard to reject each one, BY NAME, and -- this is the part that
matters -- requires that **no bytes are returned at all**.  An exception that
still hands back a frame is a leak, so every trap runs through
``assertNoBytes``, which fails if the refused call produced any value:

  1. a sweep with no MISS frame ......... sweep_does_not_contain_a_miss_frame
  2. a positive damage .................. damage_positive_heal_semantics_unknown
  3. INT32_MIN .......................... damage_is_int32_min
  4. flag bit 7 (0x0080) ................ flags_forbidden_bit
  5. flag bit 4 (0x0010), the bit that makes the client play _F_KNOCKED_002
     INSTEAD of drawing the figure ...... flags_bit_outside_allowed_mask
  6. damage 0 with the apply bit, and damage != 0 without it -- two separate
     traps, because they are two separate lies
  7. a forged unlock that compares EQUAL to the real one but is a different
     object ............................. missing_or_forged_wire_unlock
  8. a scenario file with one key added, and one with a key removed
     ................................... scenario_file_exceeds_allowlist
  9. step index ``True`` / ``-1`` / ``len()`` ....... unknown_step_label
 10. a position that is not the frozen source ...................
     position_not_from_the_pinned_source
 11. yaw ``nan``/``inf`` (yaw_not_finite_float32) and a yaw that is not 0.0
     (yaw_outside_pinned_value) -- again two separate traps

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
from pirateforce_foundation import damage_model_hypothesis as dmh  # noqa: E402

SCENARIO = ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
TOOL = ROOT / "tools" / "verify_damage_model_encoder.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
LEDGER = ROOT / "docs" / "HYPOTHESIS_LEDGER.json"
MODULE_SOURCE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "damage_model_hypothesis.py"
)

# The complete PC of every frame of the PINNED PROBE identity (0x10010001),
# byte for byte.  A live sweep carries the session's own identity and so cannot
# be hashed to a constant; the probe can, and the encoder re-composes it on
# every build.  If any of these four strings has to change, the change is a
# WIRE CHANGE and belongs in a report before it belongs in this file.
EXPECT_PC_HEX = {
    "HIT_WEAK": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b0012010032010001100000000014c1ffffff2a"
        "d45f10c62ab9e030c52ac74a5f432a000000001201000b00"
    ),
    "HIT_STRONG": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b001201003201000110000000001485feffff2a"
        "d45f10c62ab9e030c52ac74a5f432a000000001201000b00"
    ),
    "MISS": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b0012010032010001100000000014000000002a"
        "d45f10c62ab9e030c52ac74a5f432a000000001200000b00"
    ),
    "HIT_REACTION": (
        "129d6e140000000008040b0212010012f7160b0032010001100000000012"
        "000012000014000000000b0012010032010001100000000014c1ffffff2a"
        "d45f10c62ab9e030c52ac74a5f432a000000001209000b00"
    ),
}

# The five bytes at hit-entry +0x08, per step: tag 0x14 then the little-endian
# two's complement.  -63 is 0xFFFFFFC1 -> c1 ff ff ff.
EXPECT_DAMAGE_BYTES = {
    "HIT_WEAK": "14c1ffffff",
    "HIT_STRONG": "1485feffff",
    "MISS": "1400000000",
    "HIT_REACTION": "14c1ffffff",
}
EXPECT_DAMAGE_SIGNED = {
    "HIT_WEAK": -63,
    "HIT_STRONG": -379,
    "MISS": 0,
    "HIT_REACTION": -63,
}

# Byte positions inside the 84-byte PC, walked out by hand once and asserted
# below.  These are the positions of the VALUES; each is preceded by its tag.
#
#   0  12 ....  envelope id      (tag 0x12, u16)      value at 1
#   3  14 ....  envelope error   (tag 0x14, u32)      value at 4
#   8  08 ..    envelope version (tag 0x08, u8)       value at 9
#  10  0b ..    base change mask (tag 0x0B, u8)       value at 11
#  12  12 ....  vital count      (tag 0x12, u16)      value at 13
#  15  12 ....  vital id         (tag 0x12, u16)      value at 16
#  18  0b ..    vital version    (tag 0x0B, u8)       value at 19
#  20  ......   CHitResult body starts here
#  82  0b ..    derived mask     (tag 0x0B, u8)       value at 83
#
# NOTE FOR THE REPORT, not for an assertion: the module's own BASE_CHANGE_MASK_
# OFFSET .. CHIT_RESULT_PAYLOAD_OFFSET block is dead documentation (nothing
# reads it) and is off by one from offset 11 onward -- it assumes the change
# mask rides without a tag byte.  This file pins the positions the encoder and
# the decoder actually agree on, and the constants are reported upstream rather
# than edited here.
ENVELOPE_ID_VALUE_AT = 1
ENVELOPE_VERSION_VALUE_AT = 9
BASE_CHANGE_MASK_VALUE_AT = 11
VITAL_COUNT_VALUE_AT = 13
VITAL_ID_VALUE_AT = 16
VITAL_VERSION_VALUE_AT = 19
CHIT_RESULT_BODY_AT = 20
HEADER_FIELD2_VALUE_AT = 30
HEADER_FIELD3_VALUE_AT = 33
HEADER_FIELD4_VALUE_AT = 36
HEADER_FIELD5_VALUE_AT = 41
HIT_COUNT_VALUE_AT = 43
HIT_ENTRY_AT = 45
DAMAGE_TAG_AT = 54
YAW_TAG_AT = 74
FLAGS_TAG_AT = 79
DERIVED_CHANGE_MASK_VALUE_AT = 83

EXPECT_PC_SIZE = 84
EXPECT_FRAME_SIZE = 95

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

    Returns ``(scenario, unlock, probe, actions)``.  ``build_damage_model_
    sweep`` already refuses to return anything that is not the pin, so simply
    getting here is itself a guard.
    """
    global _SWEEP
    if _SWEEP is None:
        scenario = dmh.load_damage_model_hypothesis_scenario(SCENARIO)
        unlock = dmh.damage_model_wire_unlock(scenario)
        probe = dmh.damage_probe_actor(legacy())
        _SWEEP = (
            scenario, unlock, probe,
            dmh.build_damage_model_sweep(legacy(), probe, unlock, scenario),
        )
    return _SWEEP


def mutated(mutate):
    """A copy of the real sweep with one deliberate defect.

    ``mutate`` receives a list of mutable rows.  Whenever it edits a PC it must
    call :func:`repack`, otherwise the frame check fires first and the trap
    proves nothing about the guard it claims to test.
    """
    _scenario, _unlock, _probe, actions = sweep()
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


def patch_f32(pc, at, value):
    out = bytearray(pc)
    out[at:at + 4] = struct.pack("<f", value)
    return out


class NoBytesMixin:
    """Every refusal in this lane has to fail closed with nothing in hand."""

    def assertNoBytes(self, thunk, because):
        """Call ``thunk``; require the named refusal AND zero output.

        ``produced`` stays empty only if ``thunk`` never returned.  If a future
        edit ever makes a guard log-and-continue, the frame it handed back
        lands in ``produced`` and this fails -- which is the whole point.
        """
        produced = []
        with self.assertRaises(dmh.DamageModelValidationError) as ctx:
            produced.append(thunk())
        self.assertIn(because, str(ctx.exception))
        self.assertEqual(
            produced, [],
            "the refused call still handed back %d byte-carrying result(s)"
            % len(produced),
        )

    def assertSweepRejected(self, mutate, because):
        scenario, _unlock, _probe, _actions = sweep()
        bad = mutated(mutate)
        self.assertNoBytes(
            lambda: dmh.validate_damage_model_sweep(legacy(), bad, scenario),
            because,
        )


# ===========================================================================
# 1.  THE BYTES THEMSELVES
# ===========================================================================
class PinnedByteTests(unittest.TestCase):
    def test_every_probe_frame_is_byte_for_byte_the_expected_pc(self):
        _scenario, _unlock, _probe, actions = sweep()
        for index, label in enumerate(dmh.DAMAGE_MODEL_STEP_ORDER):
            with self.subTest(step=label):
                self.assertEqual(actions[index][1].hex(), EXPECT_PC_HEX[label])

    def test_the_pinned_hex_is_the_pinned_sha256_and_size(self):
        for label, hexed in EXPECT_PC_HEX.items():
            pin = dmh.DAMAGE_MODEL_PINS[label]
            pc = bytes.fromhex(hexed)
            with self.subTest(step=label):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])

    def test_every_composed_frame_matches_its_pin_in_size_and_hash(self):
        _scenario, _unlock, _probe, actions = sweep()
        for index, label in enumerate(dmh.DAMAGE_MODEL_STEP_ORDER):
            pin = dmh.DAMAGE_MODEL_PINS[label]
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
        per_step = on_disk["target"]["per_step"]
        self.assertEqual(
            set(per_step), set(dmh.DAMAGE_MODEL_STEP_ORDER))
        for label in dmh.DAMAGE_MODEL_STEP_ORDER:
            pin = dmh.DAMAGE_MODEL_PINS[label]
            with self.subTest(step=label):
                for key in ("damage_wire", "flags", "pc_size", "pc_sha256",
                            "frame_size", "frame_sha256"):
                    self.assertEqual(per_step[label][key], pin[key])

    def test_the_pins_belong_to_the_pinned_probe_identity(self):
        _scenario, _unlock, probe, actions = sweep()
        self.assertEqual(probe.identity_lo, dmh.DAMAGE_PROBE_IDENTITY_LO)
        self.assertEqual(probe.identity_hi, dmh.DAMAGE_PROBE_IDENTITY_HI)
        self.assertEqual(dmh.DAMAGE_PROBE_IDENTITY_LO, 0x10010001)
        qword = struct.pack("<Q", dmh.actor_identity(probe))
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                # once as the performer, once as the target
                self.assertEqual(pc.count(qword), 2)

    def test_the_shipped_scenario_file_loads_and_is_the_pinned_plan(self):
        scenario = dmh.load_damage_model_hypothesis_scenario(SCENARIO)
        self.assertEqual(scenario.scenario_id, dmh.DAMAGE_MODEL_SCENARIO_ID)
        self.assertEqual(scenario.hypothesis_id, "HYP-PF-024")
        self.assertEqual(
            scenario.step_order,
            ("HIT_WEAK", "HIT_STRONG", "MISS", "HIT_REACTION"))
        self.assertEqual(scenario.step_order, dmh.DAMAGE_MODEL_STEP_ORDER)
        self.assertIs(dmh.production_allowed, False)

    def test_the_sweep_is_four_labelled_frames_on_the_pinned_cadence(self):
        _scenario, _unlock, _probe, actions = sweep()
        self.assertEqual([a[0] for a in actions],
                         list(dmh.DAMAGE_MODEL_ACTION_LABELS))
        self.assertEqual([a[3] for a in actions], [0.0, 6.0, 6.0, 6.0])


# ===========================================================================
# 2.  THE WIRE SHAPE
# ===========================================================================
class WireShapeTests(unittest.TestCase):
    def test_every_frame_is_the_0x6e9d_version_4_envelope(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[0], dmh.TAG_U16)
                self.assertEqual(
                    struct.unpack_from("<H", pc, ENVELOPE_ID_VALUE_AT)[0],
                    0x6E9D)
                self.assertEqual(
                    struct.unpack_from("<H", pc, ENVELOPE_ID_VALUE_AT)[0],
                    dmh.RUNTIME_PROTOCOL_RES_ID)
                self.assertEqual(pc[ENVELOPE_VERSION_VALUE_AT],
                                 dmh.RUNTIME_PROTOCOL_RES_VERSION)
                self.assertEqual(dmh.RUNTIME_PROTOCOL_RES_VERSION, 4)

    def test_the_base_mask_selects_the_vitaldata_collection_and_no_other(self):
        """base mask 0x02 (this+0x18), derived mask 0 -- NOT HYP-PF-023's +0x1C."""
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[BASE_CHANGE_MASK_VALUE_AT],
                                 dmh.BASE_CHANGE_MASK_VITAL_COLLECTION)
                self.assertEqual(dmh.BASE_CHANGE_MASK_VITAL_COLLECTION, 2)
                self.assertEqual(pc[DERIVED_CHANGE_MASK_VALUE_AT],
                                 dmh.DERIVED_CHANGE_MASK_ABSENT)
                self.assertEqual(dmh.DERIVED_CHANGE_MASK_ABSENT, 0)

    def test_the_single_vital_is_chitresult_0x16f7_version_byte_zero(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(
                    struct.unpack_from("<H", pc, VITAL_COUNT_VALUE_AT)[0], 1)
                self.assertEqual(
                    struct.unpack_from("<H", pc, VITAL_ID_VALUE_AT)[0],
                    0x16F7)
                self.assertEqual(dmh.CHIT_RESULT_VITAL_ID, 0x16F7)
                self.assertEqual(pc[VITAL_VERSION_VALUE_AT], 0)
                self.assertEqual(dmh.CHIT_RESULT_VITAL_VERSION, 0)

    def test_the_decoder_reads_back_the_header_the_encoder_wrote(self):
        _scenario, _unlock, probe, actions = sweep()
        identity = dmh.actor_identity(probe)
        for label, pc, _frame, _delay in actions:
            read = dmh.decode_chit_result_frame(pc)
            body = read["vitals"][0]
            with self.subTest(step=label):
                self.assertEqual(read["envelope_id"], 0x6E9D)
                self.assertEqual(read["envelope_version"], 4)
                self.assertEqual(read["base_change_mask"], 2)
                self.assertEqual(read["derived_change_mask"], 0)
                self.assertEqual(read["vital_count"], 1)
                self.assertEqual(body["vital_id"], 0x16F7)
                self.assertEqual(body["vital_version"], 0)
                self.assertEqual(body["header_wire_size"], 22)
                self.assertEqual(dmh.CHIT_RESULT_HEADER_WIRE_SIZE, 22)
                self.assertEqual(body["performer_identity"], identity)
                self.assertEqual(body["entry_count"], 1)
                self.assertEqual(dmh.HIT_ENTRY_COUNT_PINNED, 1)
                self.assertEqual(body["entries"][0]["wire_size"], 37)
                self.assertEqual(dmh.HIT_ELEMENT_WIRE_SIZE, 37)
                self.assertEqual(body["entries"][0]["target_identity"],
                                 identity)

    def test_the_four_reserved_header_fields_are_all_zero(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            read = dmh.decode_chit_result_frame(pc)
            body = read["vitals"][0]
            with self.subTest(step=label):
                for key in ("header_field2", "header_field3",
                            "header_field4", "header_field5"):
                    self.assertEqual(body[key], dmh.HEADER_RESERVED_VALUE)
                    self.assertEqual(body[key], 0)
                # and in the raw bytes, at the positions and tags they ride
                self.assertEqual(pc[HEADER_FIELD2_VALUE_AT - 1], dmh.TAG_U16)
                self.assertEqual(pc[HEADER_FIELD3_VALUE_AT - 1], dmh.TAG_U16)
                self.assertEqual(pc[HEADER_FIELD4_VALUE_AT - 1], dmh.TAG_U32)
                self.assertEqual(pc[HEADER_FIELD5_VALUE_AT - 1], dmh.TAG_U8)
                self.assertEqual(pc[HEADER_FIELD2_VALUE_AT:
                                    HEADER_FIELD2_VALUE_AT + 2], b"\x00\x00")
                self.assertEqual(pc[HEADER_FIELD3_VALUE_AT:
                                    HEADER_FIELD3_VALUE_AT + 2], b"\x00\x00")
                self.assertEqual(pc[HEADER_FIELD4_VALUE_AT:
                                    HEADER_FIELD4_VALUE_AT + 4], b"\x00" * 4)
                self.assertEqual(pc[HEADER_FIELD5_VALUE_AT], 0)

    def test_the_widths_add_up_to_84_and_95(self):
        _scenario, _unlock, _probe, actions = sweep()
        self.assertEqual(
            dmh.CHIT_RESULT_PAYLOAD_WIRE_SIZE,
            dmh.CHIT_RESULT_HEADER_WIRE_SIZE
            + dmh.HIT_COUNT_WIRE_SIZE
            + dmh.HIT_ELEMENT_WIRE_SIZE,
        )
        self.assertEqual(dmh.CHIT_RESULT_PAYLOAD_WIRE_SIZE, 62)
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(len(pc), EXPECT_PC_SIZE)
                self.assertEqual(len(frame), EXPECT_FRAME_SIZE)
                self.assertEqual(
                    len(pc) - CHIT_RESULT_BODY_AT - 2,
                    dmh.CHIT_RESULT_PAYLOAD_WIRE_SIZE)

    def test_every_frame_is_frame_pc_of_its_own_pc(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(frame, legacy().frame_pc(pc))

    def test_the_hit_entry_rides_the_tags_the_serializer_writes(self):
        _scenario, _unlock, _probe, actions = sweep()
        for label, pc, _frame, _delay in actions:
            with self.subTest(step=label):
                self.assertEqual(pc[HIT_COUNT_VALUE_AT - 1], dmh.TAG_U16)
                self.assertEqual(
                    struct.unpack_from("<H", pc, HIT_COUNT_VALUE_AT)[0], 1)
                self.assertEqual(pc[HIT_ENTRY_AT], dmh.TAG_QWORD)
                self.assertEqual(pc[DAMAGE_TAG_AT], dmh.TAG_U32)
                self.assertEqual(pc[YAW_TAG_AT], dmh.TAG_F32)
                self.assertEqual(pc[FLAGS_TAG_AT], dmh.TAG_U16)

    def test_the_position_is_the_frozen_v135_player_spawn(self):
        _scenario, _unlock, _probe, actions = sweep()
        pinned = (
            float(legacy().V135_PLAYER_X),
            float(legacy().V135_PLAYER_Y),
            float(legacy().V135_PLAYER_Z),
        )
        for label, pc, _frame, _delay in actions:
            read = dmh.decode_chit_result_frame(pc)
            entry = read["vitals"][0]["entries"][0]
            with self.subTest(step=label):
                for got, want in zip(entry["position"], pinned):
                    self.assertEqual(struct.pack("<f", got),
                                     struct.pack("<f", want))
                self.assertEqual(entry["yaw"], dmh.YAW_PINNED)
                self.assertEqual(dmh.YAW_PINNED, 0.0)


# ===========================================================================
# 3.  THE SIGN IS THE MEANING
# ===========================================================================
class SignIsTheMeaningTests(unittest.TestCase):
    def test_plus_0x08_reads_back_signed_as_minus_63_379_0_63(self):
        _scenario, _unlock, _probe, actions = sweep()
        read = [
            dmh.decode_chit_result_frame(a[1])["vitals"][0]["entries"][0]
            for a in actions
        ]
        self.assertEqual([e["damage_wire"] for e in read],
                         [-63, -379, 0, -63])
        for index, label in enumerate(dmh.DAMAGE_MODEL_STEP_ORDER):
            with self.subTest(step=label):
                self.assertEqual(read[index]["damage_wire"],
                                 EXPECT_DAMAGE_SIGNED[label])

    def test_the_literal_bytes_of_minus_63_are_tag_0x14_then_c1_ff_ff_ff(self):
        _scenario, _unlock, _probe, actions = sweep()
        for index, label in enumerate(dmh.DAMAGE_MODEL_STEP_ORDER):
            pc = actions[index][1]
            with self.subTest(step=label):
                self.assertEqual(
                    pc[DAMAGE_TAG_AT:DAMAGE_TAG_AT + 5].hex(),
                    EXPECT_DAMAGE_BYTES[label])
        # spelled out once, so the two's complement is not taken on trust
        self.assertEqual(bytes.fromhex("14c1ffffff"),
                         bytes([0x14]) + struct.pack("<i", -63))
        self.assertEqual(bytes.fromhex("1485feffff"),
                         bytes([0x14]) + struct.pack("<i", -379))
        self.assertEqual(bytes.fromhex("1400000000"),
                         bytes([0x14]) + struct.pack("<i", 0))

    def test_a_negative_wire_value_is_a_positive_number_on_screen(self):
        """The display path calls abs(); the wire carries the negative."""
        for label, value in EXPECT_DAMAGE_SIGNED.items():
            with self.subTest(step=label):
                self.assertLessEqual(value, dmh.DAMAGE_WIRE_MAX)
                self.assertEqual(dmh.DAMAGE_WIRE_MAX, 0)
                self.assertIn(abs(value), (0, 63, 379))

    def test_the_unsigned_reading_of_the_same_bytes_is_not_the_meaning(self):
        """Read the damage field as u32 and it is a huge positive number.

        That is exactly the mistake this lane exists to make impossible, so it
        is written down rather than left implicit.
        """
        _scenario, _unlock, _probe, actions = sweep()
        raw = actions[0][1][DAMAGE_TAG_AT + 1:DAMAGE_TAG_AT + 5]
        self.assertEqual(struct.unpack("<I", raw)[0], 0xFFFFFFC1)
        self.assertEqual(struct.unpack("<i", raw)[0], -63)


# ===========================================================================
# 4.  OUR FORMULA
# ===========================================================================
class DefenderProvenanceTests(unittest.TestCase):
    """The two defender numbers are copied from HYP-PF-020, not imported.

    The encoder deliberately does not import that lane: a containment test in
    tests/test_stats_progression_hypothesis.py requires that exactly two
    foundation modules (app.py and runtime.py) import it, and an encoder is
    not one of them.  The drift check belongs here instead, where an import
    costs nothing.
    """

    def test_the_defender_numbers_still_match_the_lane_they_came_from(self):
        from pirateforce_foundation import stats_progression_hypothesis as spx

        self.assertEqual(dmh.DEFENDER_LEVEL, spx.STATS_PROGRESSION_LEVEL)
        self.assertEqual(
            dmh.DEFENDER_ABILITY_CON, spx.STATS_PROGRESSION_ABILITY_CON
        )
        self.assertEqual(
            dmh.DEFENDER_PLAYER_BASELINE.level, spx.STATS_PROGRESSION_LEVEL
        )
        self.assertEqual(
            dmh.DEFENDER_PLAYER_BASELINE.ability_con,
            spx.STATS_PROGRESSION_ABILITY_CON,
        )

    def test_the_encoder_does_not_import_the_progression_lane(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from .stats_progression_hypothesis", source)
        self.assertNotIn("import stats_progression_hypothesis", source)


class FormulaTests(unittest.TestCase):
    def test_the_two_pinned_profiles_produce_63_and_379(self):
        weak = dmh.compute_damage(
            dmh.ATTACKER_MOB_WEAK, dmh.DEFENDER_PLAYER_BASELINE)
        strong = dmh.compute_damage(
            dmh.ATTACKER_MOB_STRONG, dmh.DEFENDER_PLAYER_BASELINE)
        self.assertEqual(weak, -63)
        self.assertEqual(strong, -379)
        self.assertEqual(abs(weak), 63)
        self.assertEqual(abs(strong), 379)

    def test_the_arithmetic_is_the_one_a_tester_can_check_by_hand(self):
        self.assertEqual(dmh.compute_attack(dmh.ATTACKER_MOB_WEAK), 124)
        self.assertEqual(dmh.compute_attack(dmh.ATTACKER_MOB_STRONG), 440)
        self.assertEqual(
            dmh.compute_defense(dmh.DEFENDER_PLAYER_BASELINE), 61)
        self.assertEqual(124 - 61, 63)
        self.assertEqual(440 - 61, 379)

    def test_the_floor_case_is_minus_one_and_never_a_positive_number(self):
        """A defender nothing can dent still takes the floor, not a heal."""
        wall = dmh.DamageProfile("WALL", 7, 0, 0, 0xFFFF, 0)
        value = dmh.compute_damage(dmh.ATTACKER_MOB_WEAK, wall)
        self.assertEqual(value, -1)
        self.assertEqual(value, -dmh.MIN_HIT)
        self.assertLess(value, 0)
        self.assertNotEqual(value, 1)

    def test_the_formula_is_deterministic_over_a_hundred_calls(self):
        first = dmh.compute_damage(
            dmh.ATTACKER_MOB_STRONG, dmh.DEFENDER_PLAYER_BASELINE)
        values = {
            dmh.compute_damage(
                dmh.ATTACKER_MOB_STRONG, dmh.DEFENDER_PLAYER_BASELINE)
            for _ in range(100)
        }
        self.assertEqual(values, {first})
        self.assertEqual(values, {-379})

    def test_the_module_source_contains_no_randomness_at_all(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        for banned in ("import random", "random.", "secrets", "urandom",
                       "SystemRandom", "time.time("):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, source)
        self.assertEqual(dmh.JITTER_PCT_MAX, 0)

    def test_the_formula_constants_agree_with_the_scenario_file(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))["formula"]
        self.assertIs(on_disk["deterministic"], True)
        self.assertIs(on_disk["uses_random"], False)
        self.assertEqual(on_disk["atk_base"], dmh.ATK_BASE)
        self.assertEqual(on_disk["k_atk_str"], dmh.K_ATK_STR)
        self.assertEqual(on_disk["k_atk_lv"], dmh.K_ATK_LV)
        self.assertEqual(on_disk["def_base"], dmh.DEF_BASE)
        self.assertEqual(on_disk["k_def_con"], dmh.K_DEF_CON)
        self.assertEqual(on_disk["k_def_lv"], dmh.K_DEF_LV)
        self.assertEqual(on_disk["min_hit"], dmh.MIN_HIT)
        self.assertEqual(on_disk["jitter_pct_max"], dmh.JITTER_PCT_MAX)

    def test_the_step_plan_reproduces_the_pinned_numbers(self):
        for index, label in enumerate(dmh.DAMAGE_MODEL_STEP_ORDER):
            with self.subTest(step=label):
                self.assertEqual(dmh.step_damage_wire(index),
                                 EXPECT_DAMAGE_SIGNED[label])
                self.assertEqual(dmh.step_damage_wire(index),
                                 dmh.DAMAGE_MODEL_PINS[label]["damage_wire"])


# ===========================================================================
# 5.  TRAP TESTS
# ===========================================================================
class TrapTests(NoBytesMixin, unittest.TestCase):
    """A validator that cannot be made to fail is not a validator."""

    def test_positive_control_the_untouched_sweep_validates(self):
        scenario, _unlock, _probe, actions = sweep()
        rows = dmh.validate_damage_model_sweep(
            legacy(), list(actions), scenario)
        self.assertEqual(len(rows), 4)
        self.assertEqual([r["label"] for r in rows],
                         list(dmh.DAMAGE_MODEL_STEP_ORDER))

    # ---- TRAP 1: a sweep with no MISS frame -------------------------------
    def test_trap_a_sweep_that_never_shows_the_control_frame(self):
        """The MISS frame is the experiment's control, not filler.

        Without it, a tester cannot tell whether the client is reading OUR
        bytes or drawing something of its own, so the step plan is patched to
        make every frame a hit and the whole build must come back empty.
        """
        scenario, unlock, probe, _actions = sweep()
        all_hits = tuple(
            (label, "MOB_WEAK", dmh.FLAGS_HIT) if label == "MISS" else row
            for row, label in zip(dmh.DAMAGE_MODEL_STEPS,
                                  dmh.DAMAGE_MODEL_STEP_ORDER)
        )
        with mock.patch.object(dmh, "DAMAGE_MODEL_STEPS", all_hits):
            self.assertNoBytes(
                lambda: dmh.build_damage_model_sweep(
                    legacy(), probe, unlock, scenario),
                "sweep_does_not_contain_a_miss_frame",
            )
        # and the real plan is untouched afterwards
        self.assertEqual(dmh.DAMAGE_MODEL_STEPS[2][1], None)

    # ---- TRAP 2: a positive damage ----------------------------------------
    def test_trap_a_positive_damage_value(self):
        """Heal / absorb / no-op: the meaning is UNKNOWN, so it is refused."""
        def mutate(rows):
            repack(rows, 0, patch_i32(rows[0][1], DAMAGE_TAG_AT + 1, 63))
        self.assertSweepRejected(
            mutate, "damage_positive_heal_semantics_unknown")

    def test_trap_a_positive_damage_straight_at_the_encoder(self):
        _scenario, unlock, probe, _actions = sweep()
        self.assertNoBytes(
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), 63,
                (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
                dmh.FLAGS_HIT, unlock),
            "damage_positive_heal_semantics_unknown",
        )

    # ---- TRAP 3: INT32_MIN ------------------------------------------------
    def test_trap_int32_min(self):
        """abs(0x80000000) is 0x80000000, so "%d" would print a minus sign."""
        def mutate(rows):
            repack(rows, 0,
                   patch_i32(rows[0][1], DAMAGE_TAG_AT + 1, dmh.INT32_MIN))
        self.assertSweepRejected(mutate, "damage_is_int32_min")

    def test_trap_int32_min_straight_at_the_encoder(self):
        _scenario, unlock, probe, _actions = sweep()
        self.assertEqual(dmh.INT32_MIN, -2147483648)
        self.assertNoBytes(
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), dmh.INT32_MIN,
                (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
                dmh.FLAGS_HIT, unlock),
            "damage_is_int32_min",
        )

    def test_trap_a_damage_below_the_safe_band(self):
        def mutate(rows):
            repack(rows, 0,
                   patch_i32(rows[0][1], DAMAGE_TAG_AT + 1, -2_000_000))
        self.assertSweepRejected(mutate, "damage_below_safe_band")

    def test_trap_a_damage_outside_the_four_digit_scenario_band(self):
        def mutate(rows):
            repack(rows, 0, patch_i32(rows[0][1], DAMAGE_TAG_AT + 1, -50_000))
        self.assertSweepRejected(mutate, "damage_outside_scenario_band")

    # ---- TRAP 4: flag bit 7 -----------------------------------------------
    def test_trap_flag_bit_7_the_tested_but_unexplained_bit(self):
        """0x750A84 tests bit 7, so it does something, and we cannot say what."""
        self.assertTrue(0x0080 & dmh.FLAGS_FORBIDDEN_MASK)

        def mutate(rows):
            repack(rows, 0, patch_u16(rows[0][1], FLAGS_TAG_AT + 1, 0x0080))
        self.assertSweepRejected(mutate, "flags_forbidden_bit")

    def test_trap_flag_bit_7_straight_at_the_encoder(self):
        _scenario, unlock, probe, _actions = sweep()
        self.assertNoBytes(
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), -63,
                (probe.x, probe.y, probe.z), dmh.YAW_PINNED, 0x0080, unlock),
            "flags_forbidden_bit",
        )

    # ---- TRAP 5: flag bit 4, the bit that hides the number ----------------
    def test_trap_flag_bit_4_which_plays_an_animation_instead_of_the_number(self):
        """bit 4 makes the client play _F_KNOCKED_002 INSTEAD of the figure.

        A frame whose entire purpose is a legible number may never carry it.
        """
        self.assertEqual(dmh.FLAGS_BIT_SUPPRESSES_THE_NUMBER, 0x0010)

        def mutate(rows):
            repack(rows, 0, patch_u16(rows[0][1], FLAGS_TAG_AT + 1, 0x0010))
        self.assertSweepRejected(mutate, "flags_bit_outside_allowed_mask")

    def test_trap_flag_bit_4_riding_alongside_a_legal_bit(self):
        """0x0011 is bit 0 plus the suppressor: still refused, twice over."""
        _scenario, unlock, probe, _actions = sweep()
        self.assertNoBytes(
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), -63,
                (probe.x, probe.y, probe.z), dmh.YAW_PINNED, 0x0011, unlock),
            "flags_bit_outside_allowed_mask",
        )
        self.assertNoBytes(
            lambda: dmh.require_damage_and_flags_agree(-63, 0x0011),
            "flags_knockback_bit_suppresses_the_number",
        )

    def test_trap_a_flag_word_outside_the_value_allowlist(self):
        """0x0008 is inside the allowed MASK but is not a whole value we ship."""
        self.assertFalse(0x0008 & dmh.FLAGS_FORBIDDEN_MASK)
        self.assertFalse(0x0008 & ~dmh.FLAGS_ALLOWED_MASK_PHASE1)
        self.assertNotIn(0x0008, dmh.FLAGS_VALUE_ALLOWLIST_PHASE1)

        def mutate(rows):
            repack(rows, 0, patch_u16(rows[0][1], FLAGS_TAG_AT + 1, 0x0008))
        self.assertSweepRejected(mutate, "flags_outside_value_allowlist")

    # ---- TRAP 6: the two fields telling different stories -----------------
    def test_trap_damage_zero_carrying_the_apply_flag(self):
        """A miss that asks the client to react to nothing."""
        def mutate(rows):
            repack(rows, 2, patch_u16(rows[2][1], FLAGS_TAG_AT + 1, 0x0001))
        self.assertSweepRejected(mutate, "damage_zero_with_apply_flag")

    def test_trap_a_nonzero_damage_without_the_apply_flag(self):
        """A figure with no reaction behind it."""
        def mutate(rows):
            repack(rows, 0, patch_u16(rows[0][1], FLAGS_TAG_AT + 1, 0x0000))
        self.assertSweepRejected(mutate, "damage_nonzero_without_apply_flag")

    # ---- TRAP 7: a forged unlock that compares EQUAL ----------------------
    def test_trap_a_forged_unlock_that_compares_equal_to_the_real_one(self):
        """Proves the gate is `is`, not `==`."""
        _scenario, unlock, probe, _actions = sweep()
        forged = dmh.DamageModelWireUnlock(
            dmh.DAMAGE_MODEL_SCENARIO_ID, dmh.DAMAGE_MODEL_HYPOTHESIS_ID)
        self.assertEqual(forged, unlock)      # equal ...
        self.assertIsNot(forged, unlock)      # ... and still not the key
        self.assertNoBytes(
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), -63,
                (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
                dmh.FLAGS_HIT, forged),
            "missing_or_forged_wire_unlock",
        )
        self.assertNoBytes(
            lambda: dmh.encode_chit_result(
                legacy(), dmh.actor_identity(probe), [b"x" * 37], forged),
            "missing_or_forged_wire_unlock",
        )

    def test_trap_a_forged_unlock_through_the_whole_sweep_builder(self):
        scenario, _unlock, probe, _actions = sweep()
        forged = dmh.DamageModelWireUnlock(
            dmh.DAMAGE_MODEL_SCENARIO_ID, dmh.DAMAGE_MODEL_HYPOTHESIS_ID)
        self.assertNoBytes(
            lambda: dmh.build_damage_model_sweep(
                legacy(), probe, forged, scenario),
            "missing_or_forged_wire_unlock",
        )

    # ---- TRAP 8: a scenario file one key away from the allowlist ----------
    def test_trap_a_scenario_file_with_one_key_added_or_removed(self):
        base = json.loads(SCENARIO.read_text(encoding="utf-8"))
        variants = {
            "extra top level key": lambda d: d.update(extra=1),
            "missing top level key": lambda d: d.pop("test_only"),
            "extra nested key": lambda d: d["wire"].update(sneaky=1),
            "missing nested key": lambda d: d["formula"].pop("uses_random"),
            "extra per step key": lambda d: d["target"]["per_step"]
            ["MISS"].update(note="hello"),
            "missing per step key": lambda d: d["target"]["per_step"]
            ["HIT_WEAK"].pop("frame_sha256"),
            "production allowed": lambda d: d.update(production_allowed=True),
            "not test only": lambda d: d.update(test_only=False),
            "edited pin": lambda d: d["target"]["per_step"]["HIT_WEAK"].update(
                pc_size=1),
            "edited formula constant": lambda d: d["formula"].update(
                atk_base=101),
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
                        dmh.load_damage_model_hypothesis_scenario(p),
                        "scenario_file_exceeds_allowlist",
                    )

    def test_trap_a_scenario_path_that_is_not_json_or_not_there_at_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            broken = Path(tmp) / "scenario.json"
            broken.write_text("not json at all", encoding="utf-8")
            self.assertNoBytes(
                lambda: dmh.load_damage_model_hypothesis_scenario(broken),
                "scenario_file_exceeds_allowlist")
            self.assertNoBytes(
                lambda: dmh.load_damage_model_hypothesis_scenario(
                    Path(tmp) / "nothing_here.json"),
                "scenario_file_exceeds_allowlist")
        self.assertNoBytes(
            lambda: dmh.load_damage_model_hypothesis_scenario(None),
            "scenario_file_exceeds_allowlist")

    def test_trap_a_scenario_object_that_is_not_the_pinned_plan(self):
        lookalike = dmh.DamageModelHypothesisScenario(
            dmh.DAMAGE_MODEL_SCENARIO_ID, dmh.DAMAGE_MODEL_HYPOTHESIS_ID,
            ("HIT_WEAK", "HIT_STRONG", "HIT_REACTION"),
            dmh.DAMAGE_MODEL_SPACING_SECONDS,
            dmh.DAMAGE_MODEL_FIRST_DELAY_SECONDS,
            dmh.DAMAGE_MODEL_ACTION_LABEL_PREFIX,
        )
        for impostor in (lookalike, object(), None, "scenario"):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor:
                    dmh.require_damage_model_hypothesis_scenario(i),
                    "scenario_object_exceeds_allowlist")
                self.assertNoBytes(
                    lambda i=impostor: dmh.damage_model_wire_unlock(i),
                    "scenario_object_exceeds_allowlist")

    # ---- TRAP 9: step indices that are not steps --------------------------
    def test_trap_step_index_true_minus_one_and_len(self):
        scenario, unlock, probe, _actions = sweep()
        for index in (True, False, -1, len(dmh.DAMAGE_MODEL_STEP_ORDER),
                      99, 1.0, "0", None):
            with self.subTest(index=repr(index)):
                self.assertNoBytes(
                    lambda i=index: dmh.step_plan(i), "unknown_step_label")
                self.assertNoBytes(
                    lambda i=index: dmh.make_damage_model_step_response(
                        legacy(), probe, i, unlock, scenario),
                    "unknown_step_label")

    def test_trap_a_relabelled_step_in_a_composed_sweep(self):
        def mutate(rows):
            rows[3][0] = "HYP_PF_024_DAMAGE_MODEL_SOMETHING_ELSE"
        self.assertSweepRejected(mutate, "unknown_step_label")

    # ---- TRAP 10: a position that is not the pinned source ----------------
    def test_trap_a_position_that_is_not_the_frozen_spawn(self):
        scenario, unlock, probe, _actions = sweep()
        drifted = dmh.DamageModelActor(
            probe.identity_lo, probe.identity_hi,
            probe.x + 1.0, probe.y, probe.z)
        self.assertNoBytes(
            lambda: dmh.make_damage_model_step_response(
                legacy(), drifted, 0, unlock, scenario),
            "position_not_from_the_pinned_source",
        )

    def test_trap_a_position_edited_after_composition(self):
        def mutate(rows):
            repack(rows, 0, patch_f32(rows[0][1], 60, 1.0))
        self.assertSweepRejected(mutate, "position_not_from_the_pinned_source")

    def test_trap_a_non_finite_position_at_the_encoder(self):
        _scenario, unlock, probe, _actions = sweep()
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(component=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_hit_entry(
                        legacy(), dmh.actor_identity(probe), -63,
                        (b, probe.y, probe.z), dmh.YAW_PINNED,
                        dmh.FLAGS_HIT, unlock),
                    "position_not_from_the_pinned_source",
                )

    # ---- TRAP 11: the yaw, which is an angle and not a magnitude ----------
    def test_trap_a_yaw_that_is_nan_or_inf(self):
        _scenario, unlock, probe, _actions = sweep()
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(yaw=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_hit_entry(
                        legacy(), dmh.actor_identity(probe), -63,
                        (probe.x, probe.y, probe.z), b,
                        dmh.FLAGS_HIT, unlock),
                    "yaw_not_finite_float32",
                )

    def test_trap_a_yaw_that_is_simply_not_zero(self):
        """Every value here IS exactly representable as a float32.

        That matters: a value that is not, such as 3.14159, is refused one step
        earlier by the float32 round-trip check and would prove the wrong
        guard.  Those are covered separately below.
        """
        _scenario, unlock, probe, _actions = sweep()
        for bad in (1.5, -0.5, 90.0, 360.0):
            self.assertEqual(
                struct.unpack("<f", struct.pack("<f", bad))[0], bad)
            with self.subTest(yaw=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_hit_entry(
                        legacy(), dmh.actor_identity(probe), -63,
                        (probe.x, probe.y, probe.z), b,
                        dmh.FLAGS_HIT, unlock),
                    "yaw_outside_pinned_value",
                )

    def test_trap_a_yaw_that_does_not_survive_a_float32_round_trip(self):
        """3.14159 is not a float32, so it never reaches the wire either.

        NOTE, for the report and not for a fix here: the rejection is named
        ``yaw_not_finite_float32`` even though the value is perfectly finite.
        The refusal is right; only the name is narrower than the check.
        """
        _scenario, unlock, probe, _actions = sweep()
        for bad in (3.14159, 0.1, 1e-40):
            self.assertNotEqual(
                struct.unpack("<f", struct.pack("<f", bad))[0], bad)
            with self.subTest(yaw=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_hit_entry(
                        legacy(), dmh.actor_identity(probe), -63,
                        (probe.x, probe.y, probe.z), b,
                        dmh.FLAGS_HIT, unlock),
                    "yaw_not_finite_float32",
                )

    def test_trap_a_yaw_edited_after_composition(self):
        def mutate(rows):
            repack(rows, 0, patch_f32(rows[0][1], YAW_TAG_AT + 1, 1.5))
        self.assertSweepRejected(mutate, "yaw_outside_pinned_value")

    # ---- structural traps -------------------------------------------------
    def test_trap_the_base_change_mask_cleared(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[BASE_CHANGE_MASK_VALUE_AT] = 0x00
            repack(rows, 0, pc)
        self.assertSweepRejected(
            mutate, "base change mask does not select the VitalData collection")

    def test_trap_a_derived_change_mask_that_should_not_be_there(self):
        """0x02 in the DERIVED mask is HYP-PF-023's +0x1C collection, not ours."""
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[DERIVED_CHANGE_MASK_VALUE_AT] = 0x02
            repack(rows, 0, pc)
        self.assertSweepRejected(
            mutate, "derived change mask must be absent on this lane")

    def test_trap_a_nonzero_version_byte(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[VITAL_VERSION_VALUE_AT] = 1
            repack(rows, 0, pc)
        self.assertSweepRejected(mutate, "vital_version_not_pinned")

    def test_trap_the_wrong_envelope_id(self):
        def mutate(rows):
            repack(rows, 0,
                   patch_u16(rows[0][1], ENVELOPE_ID_VALUE_AT, 0x309A))
        self.assertSweepRejected(mutate, "envelope id is not 0x6E9D")

    def test_trap_the_wrong_envelope_version(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[ENVELOPE_VERSION_VALUE_AT] = 3
            repack(rows, 0, pc)
        self.assertSweepRejected(mutate, "envelope is not version 4")

    def test_trap_a_nonzero_reserved_header_field(self):
        for at in (HEADER_FIELD2_VALUE_AT, HEADER_FIELD3_VALUE_AT,
                   HEADER_FIELD4_VALUE_AT, HEADER_FIELD5_VALUE_AT):
            with self.subTest(at=at):
                def mutate(rows, at=at):
                    pc = bytearray(rows[0][1])
                    pc[at] = 1
                    repack(rows, 0, pc)
                self.assertSweepRejected(mutate, "header_reserved_field_nonzero")

    def test_trap_a_target_that_is_not_the_performer(self):
        def mutate(rows):
            pc = bytearray(rows[0][1])
            pc[HIT_ENTRY_AT + 1:HIT_ENTRY_AT + 9] = struct.pack("<Q", 7)
            repack(rows, 0, pc)
        self.assertSweepRejected(
            mutate, "performer_identity_not_the_selected_actor")

    def test_trap_a_truncated_frame(self):
        def mutate(rows):
            repack(rows, 0, bytearray(rows[0][1][:-4]))
        self.assertSweepRejected(mutate, "truncated")

    def test_trap_a_frame_that_is_not_frame_pc_of_its_pc(self):
        def mutate(rows):
            rows[0][2] = b"\x00" * EXPECT_FRAME_SIZE
        self.assertSweepRejected(mutate, "HYP-PF-024 frame drift")

    def test_trap_a_delay_that_is_not_the_plan(self):
        def mutate(rows):
            rows[0][3] = 6.0
        self.assertSweepRejected(mutate, "sweep delay is not the plan")

    def test_trap_a_sweep_of_the_wrong_length(self):
        scenario, _unlock, _probe, actions = sweep()
        for bad in (list(actions[:3]), list(actions) + list(actions[:1]), []):
            with self.subTest(length=len(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.validate_damage_model_sweep(
                        legacy(), b, scenario),
                    "sweep length is not the pinned plan")

    def test_trap_an_identity_outside_the_qword_range(self):
        _scenario, unlock, probe, _actions = sweep()
        for bad in (-1, 1 << 64, True, "0", None, 1.0):
            with self.subTest(identity=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_hit_entry(
                        legacy(), b, -63, (probe.x, probe.y, probe.z),
                        dmh.YAW_PINNED, dmh.FLAGS_HIT, unlock),
                    "target_identity_outside_qword")

    def test_trap_an_entry_count_that_is_not_one(self):
        _scenario, unlock, probe, _actions = sweep()
        entry = dmh.encode_hit_entry(
            legacy(), dmh.actor_identity(probe), -63,
            (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
            dmh.FLAGS_HIT, unlock)
        for bad in ([], [entry, entry], tuple([entry])):
            with self.subTest(count=len(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.encode_chit_result(
                        legacy(), dmh.actor_identity(probe), b, unlock),
                    "entry_count_not_pinned")

    def test_trap_a_formula_input_outside_the_declared_u16_domain(self):
        for bad in (-1, 0x10000, True, 1.0, "7", None):
            with self.subTest(level=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.compute_damage(
                        dmh.DamageProfile("BAD", b, 0, 0, 0, 0),
                        dmh.DEFENDER_PLAYER_BASELINE),
                    "formula_input_outside_declared_domain")

    def test_trap_a_damage_that_is_not_an_integer_at_all(self):
        for bad in (-63.0, True, False, "-63", None, complex(-63)):
            with self.subTest(damage=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.require_damage_wire_value(b),
                    "damage_not_integer")

    def test_trap_a_flag_word_that_is_not_a_u16(self):
        for bad in (-1, 0x10000, True, 1.0, "1", None):
            with self.subTest(flags=repr(bad)):
                self.assertNoBytes(
                    lambda b=bad: dmh.require_flags_value(b), "flags_not_u16")


# ===========================================================================
# 6.  NO LEAK WITHOUT THE SCENARIO
# ===========================================================================
class FailClosedWithoutTheScenarioTests(NoBytesMixin, unittest.TestCase):
    """A process that never opted in cannot compose a CHitResult at all."""

    def test_the_hit_entry_encoder_refuses_every_impostor_unlock(self):
        _scenario, _unlock, probe, _actions = sweep()
        for impostor in (None, object(), "unlock", 0, False,
                         dmh.DamageModelWireUnlock("", "")):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: dmh.encode_hit_entry(
                        legacy(), dmh.actor_identity(probe), -63,
                        (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
                        dmh.FLAGS_HIT, i),
                    "missing_or_forged_wire_unlock")

    def test_the_payload_encoder_refuses_every_impostor_unlock(self):
        _scenario, _unlock, probe, _actions = sweep()
        for impostor in (None, object(), "unlock", 0, False):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: dmh.encode_chit_result(
                        legacy(), dmh.actor_identity(probe), [b"x" * 37], i),
                    "missing_or_forged_wire_unlock")

    def test_the_step_encoder_and_the_sweep_builder_refuse_without_it(self):
        scenario, _unlock, probe, _actions = sweep()
        for impostor in (None, object(), "unlock"):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: dmh.make_damage_model_step_response(
                        legacy(), probe, 0, i, scenario),
                    "missing_or_forged_wire_unlock")
                self.assertNoBytes(
                    lambda i=impostor: dmh.build_damage_model_sweep(
                        legacy(), probe, i, scenario),
                    "missing_or_forged_wire_unlock")

    def test_the_unlock_cannot_be_minted_from_anything_but_the_scenario(self):
        for impostor in (None, object(), "damage_model_hypothesis_hit_sweep",
                         {"id": dmh.DAMAGE_MODEL_SCENARIO_ID}):
            with self.subTest(impostor=type(impostor).__name__):
                self.assertNoBytes(
                    lambda i=impostor: dmh.damage_model_wire_unlock(i),
                    "scenario_object_exceeds_allowlist")

    def test_the_only_unlock_that_works_comes_from_the_shipped_file(self):
        scenario = dmh.load_damage_model_hypothesis_scenario(SCENARIO)
        unlock = dmh.damage_model_wire_unlock(scenario)
        self.assertIs(unlock, dmh.require_damage_model_wire_unlock(unlock))
        probe = dmh.damage_probe_actor(legacy())
        entry = dmh.encode_hit_entry(
            legacy(), dmh.actor_identity(probe), -63,
            (probe.x, probe.y, probe.z), dmh.YAW_PINNED,
            dmh.FLAGS_HIT, unlock)
        self.assertEqual(len(entry), dmh.HIT_ELEMENT_WIRE_SIZE)

    def test_the_lane_never_claims_production(self):
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(on_disk["production_allowed"], False)
        self.assertIs(on_disk["test_only"], True)
        self.assertIs(on_disk["our_own_formula_not_the_original_servers"], True)
        self.assertEqual(on_disk["persisted_post_state"]["database_write"],
                         "none")
        self.assertEqual(on_disk["dispatch"]["socket_action"], "none")
        self.assertIs(dmh.production_allowed, False)


# ===========================================================================
# 7.  THE REAL VERIFIER
# ===========================================================================
class VerifierTests(unittest.TestCase):
    """Run the lane's own verifier as a real subprocess, exactly as the gate does."""

    @unittest.skipUnless(
        TOOL.exists(), "tools/verify_damage_model_encoder.py is not written yet")
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
        TOOL.exists(), "tools/verify_damage_model_encoder.py is not written yet")
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
        TOOL.exists(), "tools/verify_damage_model_encoder.py is not written yet")
    def test_the_verifier_needs_no_third_party_package(self):
        source = TOOL.read_text(encoding="utf-8")
        for banned in ("capstone", "pefile", "numpy", "yaml", "requests"):
            with self.subTest(package=banned):
                self.assertNotIn("import " + banned, source)


# ===========================================================================
# 8.  LEDGER BINDING
# ===========================================================================
class LedgerBindingTests(unittest.TestCase):
    """Every marker HYP-PF-024 claims in source_refs has to actually be there.

    The list is READ from the ledger, never copied here: a marker added to the
    ledger and forgotten in the source must turn this red without anyone
    remembering to edit a test.
    """

    def entry(self):
        ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        for entry in ledger["entries"]:
            if entry["id"] == dmh.DAMAGE_MODEL_HYPOTHESIS_ID:
                return entry
        self.fail("HYP-PF-024 is not registered in docs/HYPOTHESIS_LEDGER.json")

    def test_the_hypothesis_is_registered_at_all(self):
        entry = self.entry()
        self.assertEqual(entry["id"], "HYP-PF-024")
        self.assertEqual(entry["introduced_checkpoint"], "DAMAGE-ENCODER-001")
        on_disk = json.loads(SCENARIO.read_text(encoding="utf-8"))
        self.assertIs(
            on_disk["hypothesis_id_is_registered_in_the_ledger"], True)
        self.assertEqual(on_disk["hypothesis_id"], entry["id"])

    def test_every_source_ref_marker_the_ledger_claims_is_really_there(self):
        entry = self.entry()
        refs = entry["source_refs"]
        self.assertTrue(refs, "HYP-PF-024 carries no source_refs")
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
            "src/pirateforce_foundation/damage_model_hypothesis.py", paths)
        self.assertIn(
            "scenarios/damage_model_hypothesis_hit_sweep.json", paths)

    def test_the_active_claim_annotation_is_in_the_module(self):
        source = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("PF-HYPOTHESIS-LEDGER: HYP-PF-024 active", source)


# ===========================================================================
# 9.  THE cp874 LESSON
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

    def test_every_rejection_message_this_lane_can_raise_is_ascii(self):
        scenario, unlock, probe, actions = sweep()
        raised = []
        probes = (
            lambda: dmh.require_damage_wire_value(1),
            lambda: dmh.require_damage_wire_value(dmh.INT32_MIN),
            lambda: dmh.require_flags_value(0x0080),
            lambda: dmh.require_flags_value(0x0010),
            lambda: dmh.require_damage_and_flags_agree(0, 1),
            lambda: dmh.require_damage_and_flags_agree(-1, 0),
            lambda: dmh.step_plan(-1),
            lambda: dmh.damage_model_wire_unlock(object()),
            lambda: dmh.require_damage_model_wire_unlock(object()),
            lambda: dmh.load_damage_model_hypothesis_scenario(None),
            lambda: dmh.encode_hit_entry(
                legacy(), dmh.actor_identity(probe), -63,
                (probe.x, probe.y, probe.z), 1.5, dmh.FLAGS_HIT, unlock),
            lambda: dmh.validate_damage_model_sweep(
                legacy(), list(actions[:1]), scenario),
        )
        for thunk in probes:
            try:
                thunk()
            except dmh.DamageModelValidationError as exc:
                raised.append(str(exc))
        self.assertEqual(len(raised), len(probes))
        for message in raised:
            with self.subTest(message=message):
                self.assertTrue(message.isascii())


if __name__ == "__main__":
    unittest.main()
