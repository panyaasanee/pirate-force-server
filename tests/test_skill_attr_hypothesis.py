"""SKILL-ATTR-001 (HYP-PF-035) -- the 0x1661 skill-attr block encoder lane
and its dispatch hookup.

Pure offline pytest: no network, no GameClient, no UI; the dispatch half runs
the REAL ``make_state_class`` path against a throwaway temp database.

What these tests are actually proving
-------------------------------------
RE-061 pinned, byte-exactly from the read-only client image, the wire shape
of the attr block the Skill window's controller init gate 0x761ED0 depends
on (letter pf_bridge/notes_to_chief/20260824_1437_RE-061-RESULT-SKILLATTR-
GATE-PINNED.md; body serializer [0x007520B0,0x00752281) sha256 9227cc60..;
apply 0x751C70 sha256 1e8d5b2e..; carrier handler 0x5F2400 sha256
65a7095c..):

    UpdateAttrVital 0x309A attr collection: u16 tag 0x12 attr_count, then
    per element u16 tag 0x12 attr_class_id (0x1661) / u32 tag 0x14 body_len
    / body; body = u8 tag 0x0B db_mask (+ u64 tag 0x32 identity if bit 0x01),
    u16 tag 0x12 record_count, then per record u16 tag 0x12 key / u16 tag
    0x12 opaque_u16 / u32 tag 0x14 opaque_u32.

This file proves the server-side encoder emits exactly that order and nothing
else -- tag bytes asserted literally at their byte positions, GOLDEN full-hex
pins for both sweep variants (pc and frame), round-trip through the module's
own strict decoder, the frozen v141 ``make_runtime_vitals`` envelope
byte-for-byte, all per-step hash pins in module and scenario file, and the
dispatch path: two frames per accepted trigger from the pinned probe
identity only, database byte-identical, every refusal family silent with a
named event, and containment with no scenario.

NOT tested here, because it is not claimed: that one packet is sufficient to
open the skill window (RE-061's own nonclaim -- the init gate has other
checks and the runtime null-ness of the actor slot was never observed); any
MEANING for the two opaque record fields or any key value; anything about
the original server, which is unrecoverable; and whether any client accepts
or shows anything for one of these frames -- that is an attended GT ticket,
queued and not run.
"""
from __future__ import annotations

import dataclasses
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_PAYLOADS,
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.skill_attr_hypothesis import (  # noqa: E402
    SKILL_ATTR_ACTION_LABEL_PREFIX,
    SKILL_ATTR_BODY_BASE_SIZE,
    SKILL_ATTR_COLLECTION_HEADER_SIZE,
    SKILL_ATTR_COUNT_TAG,
    SKILL_ATTR_DB_IDENTITY_TAG,
    SKILL_ATTR_DB_MASK_TAG,
    SKILL_ATTR_DB_MASK_VALUE,
    SKILL_ATTR_FIRST_DELAY_SECONDS,
    SKILL_ATTR_HYPOTHESIS_ID,
    SKILL_ATTR_ID,
    SKILL_ATTR_PC_OVERHEAD,
    SKILL_ATTR_PC_PAYLOAD_OFFSET,
    SKILL_ATTR_PC_VITAL_ID_SLICE,
    SKILL_ATTR_PROBE_BODY_SHA256,
    SKILL_ATTR_PROBE_BODY_SIZE,
    SKILL_ATTR_PROBE_FRAME_SHA256,
    SKILL_ATTR_PROBE_FRAME_SIZE,
    SKILL_ATTR_PROBE_IDENTITY_HI,
    SKILL_ATTR_PROBE_IDENTITY_LO,
    SKILL_ATTR_PROBE_PAYLOAD_SHA256,
    SKILL_ATTR_PROBE_PAYLOAD_SIZE,
    SKILL_ATTR_PROBE_PC_SHA256,
    SKILL_ATTR_PROBE_PC_SIZE,
    SKILL_ATTR_RECORD_KEY_TAG,
    SKILL_ATTR_RECORD_OPAQUE_U16_TAG,
    SKILL_ATTR_RECORD_OPAQUE_U32_TAG,
    SKILL_ATTR_RECORD_WIRE_SIZE,
    SKILL_ATTR_REJECTIONS,
    SKILL_ATTR_SCENARIO_ID,
    SKILL_ATTR_SPACING_SECONDS,
    SKILL_ATTR_STEP_ORDER,
    SKILL_ATTR_STEP_RECORDS,
    UPDATE_ATTR_VITAL_ID,
    UPDATE_ATTR_VITAL_VERSION,
    SkillAttrRecord,
    decode_skill_attr,
    encode_skill_attr,
    load_skill_attr_hypothesis_scenario,
    make_skill_attr_payload,
    make_skill_attr_response,
    make_skill_attr_step_response,
    require_skill_attr_hypothesis_scenario,
    unwrap_skill_attr_payload,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "skill_attr_hypothesis_attr_sweep.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
SWEEP_EVENT = "skill_attr_hypothesis_attr_sweep_sent"
IDENTITY_EVENT = "skill_attr_hypothesis_identity_not_pinned_no_reply"

# GOLDEN byte-exact pins for the two sweep variants, computed by running the
# encoder over the pinned probe identity and frozen here as full hex.  Every
# byte is accounted for by the RE-061 wire order plus the frozen v141
# envelope; a change to ANY byte of either frame must fail this file.
GOLDEN_PC_HEX = {
    "COUNT0_EMPTY": (
        "129D6E140000000008040B02120100129A300B00120100126116140E0000000B"
        "013201000110000000001200000B00"
    ),
    "COUNT1_KEY1": (
        "129D6E140000000008040B02120100129A300B0012010012611614190000000B"
        "0132010001100000000012010012010012000014000000000B00"
    ),
}
GOLDEN_FRAME_HEX = {
    "COUNT0_EMPTY": (
        "AC3E255F310000002FB8129D6E140000000008040B02120100129A300B001201"
        "00126116140E0000000B013201000110000000001200000B00"
    ),
    "COUNT1_KEY1": (
        "AC3E255F3C0000003AE4129D6E140000000008040B02120100129A300B001201"
        "0012611614190000000B01320100011000000000120100120100120000140000"
        "00000B00"
    ),
}


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)


def _record_bytes(record: SkillAttrRecord) -> bytes:
    """The RE-061 record layout, assembled independently of the encoder."""
    return (
        bytes([SKILL_ATTR_RECORD_KEY_TAG])
        + record.key.to_bytes(2, "little")
        + bytes([SKILL_ATTR_RECORD_OPAQUE_U16_TAG])
        + record.opaque_u16.to_bytes(2, "little")
        + bytes([SKILL_ATTR_RECORD_OPAQUE_U32_TAG])
        + record.opaque_u32.to_bytes(4, "little")
    )


def _body_bytes(identity_lo, identity_hi, records) -> bytes:
    return (
        bytes([SKILL_ATTR_DB_MASK_TAG, SKILL_ATTR_DB_MASK_VALUE])
        + bytes([SKILL_ATTR_DB_IDENTITY_TAG])
        + ((identity_hi << 32) | identity_lo).to_bytes(8, "little")
        + bytes([SKILL_ATTR_COUNT_TAG])
        + len(records).to_bytes(2, "little")
        + b"".join(_record_bytes(record) for record in records)
    )


def _payload_bytes(body: bytes) -> bytes:
    return (
        b"\x12\x01\x00"
        + b"\x12" + SKILL_ATTR_ID.to_bytes(2, "little")
        + b"\x14" + len(body).to_bytes(4, "little")
        + body
    )


class _DriftedLegacy:
    """A shim whose UpdateAttrVital id disagrees with the pinned constant."""

    def __init__(self, legacy, vital_id):
        self._legacy = legacy
        self.UPDATE_ATTR_VITAL = vital_id

    def __getattr__(self, name):
        return getattr(self._legacy, name)


class WireShapeTests(_LegacyCase):
    """The proven tag bytes, at their exact byte positions, literally."""

    def test_count_zero_body_is_the_fourteen_proven_bytes(self):
        body = encode_skill_attr(self.legacy, 0x10010001, 0, ())
        self.assertEqual(
            body,
            b"\x0b\x01"                            # u8 tag 0x0B db_mask 0x01
            + b"\x32\x01\x00\x01\x10\x00\x00\x00\x00"  # u64 tag 0x32 identity
            + b"\x12\x00\x00",                     # u16 tag 0x12 record_count
        )
        self.assertEqual(len(body), SKILL_ATTR_BODY_BASE_SIZE)

    def test_count_one_body_is_the_proven_tag_order(self):
        record = SkillAttrRecord(0x0201, 0x0403, 0x08070605)
        body = encode_skill_attr(self.legacy, 1, 0, (record,))
        self.assertEqual(
            body,
            b"\x0b\x01"
            + b"\x32\x01\x00\x00\x00\x00\x00\x00\x00"
            + b"\x12\x01\x00"                      # u16 tag 0x12 count
            + b"\x12\x01\x02"                      # u16 tag 0x12 key
            + b"\x12\x03\x04"                      # u16 tag 0x12 opaque_u16
            + b"\x14\x05\x06\x07\x08",             # u32 tag 0x14 opaque_u32
        )

    def test_the_tag_constants_are_the_re061_bytes(self):
        self.assertEqual(SKILL_ATTR_DB_MASK_TAG, 0x0B)
        self.assertEqual(SKILL_ATTR_DB_IDENTITY_TAG, 0x32)
        self.assertEqual(SKILL_ATTR_COUNT_TAG, 0x12)
        self.assertEqual(SKILL_ATTR_RECORD_KEY_TAG, 0x12)
        self.assertEqual(SKILL_ATTR_RECORD_OPAQUE_U16_TAG, 0x12)
        self.assertEqual(SKILL_ATTR_RECORD_OPAQUE_U32_TAG, 0x14)
        self.assertEqual(SKILL_ATTR_ID, 0x1661)
        self.assertEqual(UPDATE_ATTR_VITAL_ID, 0x309A)
        self.assertEqual(SKILL_ATTR_RECORD_WIRE_SIZE, 11)
        self.assertEqual(SKILL_ATTR_DB_MASK_VALUE, 0x01)

    def test_body_size_is_fourteen_plus_eleven_per_record(self):
        for count in (0, 1, 2, 3, 7):
            records = tuple(
                SkillAttrRecord(index, index, index) for index in range(count)
            )
            body = encode_skill_attr(self.legacy, 5, 6, records)
            self.assertEqual(len(body), 14 + 11 * count, count)

    def test_the_encoder_matches_an_independent_assembly(self):
        # The expected bytes here are assembled by this test's own helper,
        # not by the module, so a tag or width slip in either one shows up.
        records = (
            SkillAttrRecord(0, 0, 0),
            SkillAttrRecord(0xFFFF, 0xFFFF, 0xFFFFFFFF),
            SkillAttrRecord(0x1234, 0x4321, 0x60606060),
        )
        for lo, hi in ((0, 0), (0x10010001, 0), (0xFFFFFFFF, 0xFFFFFFFF)):
            self.assertEqual(
                encode_skill_attr(self.legacy, lo, hi, records),
                _body_bytes(lo, hi, records),
            )

    def test_record_member_order_is_not_interchangeable(self):
        self.assertNotEqual(
            encode_skill_attr(self.legacy, 1, 0, (SkillAttrRecord(1, 2, 3),)),
            encode_skill_attr(self.legacy, 1, 0, (SkillAttrRecord(2, 1, 3),)),
        )

    def test_the_payload_wrap_is_the_attr_collection_layout(self):
        body = encode_skill_attr(self.legacy, 0x10010001, 0, ())
        payload = make_skill_attr_payload(self.legacy, body)
        self.assertEqual(payload, _payload_bytes(body))
        self.assertEqual(payload[:3], b"\x12\x01\x00")
        self.assertEqual(payload[3:6], b"\x12\x61\x16")
        self.assertEqual(payload[6:11], b"\x14" + (14).to_bytes(4, "little"))
        self.assertEqual(
            len(payload), SKILL_ATTR_COLLECTION_HEADER_SIZE + len(body),
        )
        self.assertEqual(unwrap_skill_attr_payload(payload), body)

    def test_composition_is_deterministic_and_repeatable(self):
        records = (SkillAttrRecord(9, 8, 7),)
        first = encode_skill_attr(self.legacy, 3, 4, records)
        second = encode_skill_attr(self.legacy, 3, 4, records)
        self.assertEqual(first, second)


class RoundTripTests(_LegacyCase):
    def test_encode_then_decode_is_identity(self):
        for lo, hi, records in (
            (0, 0, ()),
            (0x10010001, 0, ()),
            (1, 2, (SkillAttrRecord(1, 2, 3),)),
            (0xFFFFFFFF, 0xFFFFFFFF,
             (SkillAttrRecord(0, 0, 0),
              SkillAttrRecord(0xFFFF, 0xFFFF, 0xFFFFFFFF))),
            (7, 0, tuple(
                SkillAttrRecord(i * 3, i * 2, i) for i in range(9)
            )),
        ):
            body = encode_skill_attr(self.legacy, lo, hi, records)
            self.assertEqual(decode_skill_attr(body), (lo, hi, records))

    def test_width_boundaries_are_carried_exactly(self):
        record = SkillAttrRecord(0xFFFF, 0, 0xFFFFFFFF)
        body = encode_skill_attr(self.legacy, 0xFFFFFFFF, 0, (record,))
        lo, hi, records = decode_skill_attr(body)
        self.assertEqual(lo, 0xFFFFFFFF)
        self.assertEqual(hi, 0)
        self.assertEqual(records[0].key, 0xFFFF)
        self.assertEqual(records[0].opaque_u16, 0)
        self.assertEqual(records[0].opaque_u32, 0xFFFFFFFF)

    def test_decode_accepts_bytearray_input(self):
        body = bytearray(encode_skill_attr(self.legacy, 1, 0, ()))
        self.assertEqual(decode_skill_attr(body), (1, 0, ()))

    def test_payload_wrap_round_trips_through_the_strict_unwrap(self):
        for records in ((), (SkillAttrRecord(1, 0, 0),)):
            body = encode_skill_attr(self.legacy, 0x10010001, 0, records)
            self.assertEqual(
                decode_skill_attr(unwrap_skill_attr_payload(
                    make_skill_attr_payload(self.legacy, body)
                )),
                (0x10010001, 0, records),
            )


class FailClosedTests(_LegacyCase):
    """Every rejection means: no bytes, no reply, no partial result."""

    def assert_encode_refuses(self, lo, hi, records, reason):
        with self.assertRaises(ValueError) as raised:
            encode_skill_attr(self.legacy, lo, hi, records)
        self.assertIn(reason, str(raised.exception))
        self.assertIn(reason, SKILL_ATTR_REJECTIONS)

    def test_non_tuple_record_containers_are_refused(self):
        for records in (
            None, [], [SkillAttrRecord(1, 2, 3)], "records", 3,
            (SkillAttrRecord(1, 2, 3), (4, 5, 6)),
            ((1, 2, 3),),
        ):
            self.assert_encode_refuses(
                1, 0, records, "records_not_a_tuple_of_records",
            )

    def test_non_integer_record_members_are_refused(self):
        for record in (
            SkillAttrRecord(True, 2, 3),
            SkillAttrRecord(1, True, 3),
            SkillAttrRecord(1, 2, True),
            SkillAttrRecord(1.0, 2, 3),
            SkillAttrRecord(1, "2", 3),
            SkillAttrRecord(1, 2, None),
        ):
            self.assert_encode_refuses(
                1, 0, (record,), "record_value_type_not_integer",
            )

    def test_out_of_width_record_members_are_refused(self):
        for record in (
            SkillAttrRecord(-1, 0, 0),
            SkillAttrRecord(1 << 16, 0, 0),
            SkillAttrRecord(0, -1, 0),
            SkillAttrRecord(0, 1 << 16, 0),
            SkillAttrRecord(0, 0, -1),
            SkillAttrRecord(0, 0, 1 << 32),
        ):
            self.assert_encode_refuses(
                1, 0, (record,), "record_value_outside_field_width",
            )

    def test_bad_identity_halves_are_refused(self):
        for lo, hi, reason in (
            (True, 0, "identity_type_not_integer"),
            (None, 0, "identity_type_not_integer"),
            (1.0, 0, "identity_type_not_integer"),
            ("1", 0, "identity_type_not_integer"),
            (0, True, "identity_type_not_integer"),
            (-1, 0, "identity_outside_u32_half"),
            (1 << 32, 0, "identity_outside_u32_half"),
            (0, -1, "identity_outside_u32_half"),
            (0, 1 << 32, "identity_outside_u32_half"),
        ):
            self.assert_encode_refuses(lo, hi, (), reason)

    def test_a_record_count_outside_u16_is_refused(self):
        records = tuple(SkillAttrRecord(0, 0, 0) for _ in range(0x10000))
        self.assert_encode_refuses(1, 0, records, "record_count_outside_u16")
        # ...and the largest admissible count still composes.
        body = encode_skill_attr(self.legacy, 1, 0, records[:-1])
        self.assertEqual(len(body), 14 + 11 * 0xFFFF)

    def assert_decode_refuses(self, body, reason):
        with self.assertRaises(ValueError) as raised:
            decode_skill_attr(body)
        self.assertIn(reason, str(raised.exception))
        self.assertIn(reason, SKILL_ATTR_REJECTIONS)

    def test_non_bytes_bodies_are_refused(self):
        for body in (None, "0b01", 5, [0x0B]):
            self.assert_decode_refuses(body, "truncated_body")

    def test_truncations_are_refused_at_every_boundary(self):
        good = _body_bytes(
            0x10010001, 0,
            (SkillAttrRecord(1, 2, 3), SkillAttrRecord(4, 5, 6)),
        )
        # The decoder checks remaining length before it checks a tag, so
        # every proper prefix refuses as a truncation, never as a wrong tag.
        for cut in range(len(good)):
            self.assert_decode_refuses(good[:cut], "truncated_body")

    def test_a_wrong_tag_at_any_position_is_refused_by_name(self):
        good = _body_bytes(1, 0, (SkillAttrRecord(1, 2, 3),))
        for index, reason in (
            (0, "wrong_db_mask_tag"),
            (2, "wrong_identity_tag"),
            (11, "wrong_count_tag"),
            (14, "wrong_record_key_tag"),
            (17, "wrong_record_opaque_u16_tag"),
            (20, "wrong_record_opaque_u32_tag"),
        ):
            bad = bytearray(good)
            bad[index] ^= 0xFF
            self.assert_decode_refuses(bytes(bad), reason)

    def test_unimplemented_db_mask_bits_are_refused(self):
        good = _body_bytes(1, 0, ())
        for mask in (0x00, 0x02, 0x03, 0x80, 0x81, 0xFF):
            bad = bytearray(good)
            bad[1] = mask
            self.assert_decode_refuses(bytes(bad), "unimplemented_db_mask")

    def test_trailing_bytes_after_the_records_are_refused(self):
        good = _body_bytes(1, 0, ())
        for extra in (b"\x00", b"\x12\x00\x00", b"\x14\x00\x00\x00\x00"):
            self.assert_decode_refuses(
                good + extra, "trailing_bytes_after_records",
            )

    def test_a_count_larger_than_the_body_is_refused(self):
        # Declared count 2, one record present.
        body = (
            _body_bytes(1, 0, ())[:11]
            + b"\x12\x02\x00"
            + _record_bytes(SkillAttrRecord(1, 2, 3))
        )
        self.assert_decode_refuses(body, "truncated_body")

    def assert_unwrap_refuses(self, payload, reason):
        with self.assertRaises(ValueError) as raised:
            unwrap_skill_attr_payload(payload)
        self.assertIn(reason, str(raised.exception))
        self.assertIn(reason, SKILL_ATTR_REJECTIONS)

    def test_malformed_payload_wraps_are_refused_by_name(self):
        body = encode_skill_attr(self.legacy, 1, 0, ())
        good = _payload_bytes(body)
        cases = []
        bad = bytearray(good)
        bad[0] ^= 0xFF
        cases.append((bytes(bad), "wrong_collection_count_tag"))
        bad = bytearray(good)
        bad[1] = 2
        cases.append((bytes(bad), "unimplemented_attr_count"))
        bad = bytearray(good)
        bad[3] ^= 0xFF
        cases.append((bytes(bad), "wrong_attr_class_tag"))
        bad = bytearray(good)
        bad[4] ^= 0xFF
        cases.append((bytes(bad), "wrong_attr_class_id"))
        bad = bytearray(good)
        bad[6] ^= 0xFF
        cases.append((bytes(bad), "wrong_body_length_tag"))
        bad = bytearray(good)
        bad[7] ^= 0x01
        cases.append((bytes(bad), "body_length_mismatch"))
        cases.append((good[:10], "truncated_payload"))
        cases.append((good + b"\x00", "body_length_mismatch"))
        cases.append((None, "truncated_payload"))
        for payload, reason in cases:
            self.assert_unwrap_refuses(payload, reason)

    def test_the_outer_id_drift_check_trips_when_ids_differ(self):
        # The frozen module is the authority on the carrier id; a legacy
        # whose constant disagrees with the pinned 0x309A must refuse before
        # one byte is composed.
        body = encode_skill_attr(self.legacy, 1, 0, ())
        for drifted_id in (0x309B, 0x6E9D, 0):
            drifted = _DriftedLegacy(self.legacy, drifted_id)
            with self.assertRaises(RuntimeError) as raised:
                make_skill_attr_payload(drifted, body)
            self.assertIn("drift", str(raised.exception))
        # ...and the undrifted module still composes.
        self.assertEqual(
            make_skill_attr_payload(
                _DriftedLegacy(self.legacy, self.legacy.UPDATE_ATTR_VITAL),
                body,
            ),
            _payload_bytes(body),
        )

    def test_composition_refuses_every_rejected_input(self):
        for lo, hi, records in (
            (1, 0, None),
            (1, 0, ((1, 2, 3),)),
            (1, 0, (SkillAttrRecord(-1, 0, 0),)),
            (-1, 0, ()),
            (True, 0, ()),
        ):
            with self.assertRaises(ValueError):
                make_skill_attr_response(self.legacy, lo, hi, records)

    def test_an_unknown_step_index_is_refused(self):
        for index in (-1, 2, 99, True, None, "0", 1.0):
            with self.assertRaises(ValueError) as raised:
                make_skill_attr_step_response(self.legacy, index)
            self.assertIn("unknown_step_label", str(raised.exception))


class ComposedResponseTests(_LegacyCase):
    """The envelope is the reused v141 helper; every sweep frame is pinned."""

    def test_the_envelope_is_the_reused_v141_helper_not_a_new_one(self):
        records = (SkillAttrRecord(1, 2, 3),)
        body = encode_skill_attr(self.legacy, 7, 0, records)
        payload = make_skill_attr_payload(self.legacy, body)
        self.assertEqual(
            make_skill_attr_response(self.legacy, 7, 0, records),
            self.legacy.make_runtime_vitals([
                (UPDATE_ATTR_VITAL_ID, UPDATE_ATTR_VITAL_VERSION, payload),
            ]),
        )

    def test_the_pc_carries_the_vital_id_and_the_payload_at_fixed_offset(self):
        records = (SkillAttrRecord(7, 8, 9),)
        body = encode_skill_attr(self.legacy, 5, 0, records)
        payload = make_skill_attr_payload(self.legacy, body)
        pc, _frame = make_skill_attr_response(self.legacy, 5, 0, records)
        self.assertEqual(len(pc), len(payload) + SKILL_ATTR_PC_OVERHEAD)
        self.assertEqual(
            pc[SKILL_ATTR_PC_VITAL_ID_SLICE],
            (0x309A).to_bytes(2, "little"),
        )
        offset = SKILL_ATTR_PC_PAYLOAD_OFFSET
        self.assertEqual(pc[offset:offset + len(payload)], payload)
        # The version byte our design sends sits right before the payload.
        self.assertEqual(
            pc[18:20],
            self.legacy.u8tag(0x0B, UPDATE_ATTR_VITAL_VERSION),
        )

    def test_both_steps_match_the_golden_full_hex_pins(self):
        # THE headless byte-exact proof: the two variants, every byte.
        for index, label in enumerate(SKILL_ATTR_STEP_ORDER):
            pc, frame = make_skill_attr_step_response(self.legacy, index)
            self.assertEqual(pc.hex().upper(), GOLDEN_PC_HEX[label], label)
            self.assertEqual(
                frame.hex().upper(), GOLDEN_FRAME_HEX[label], label,
            )
            # ...and the frame is the pc behind the outer header, so the
            # golden pins agree with each other too.
            self.assertTrue(
                frame.hex().upper().endswith(GOLDEN_PC_HEX[label]), label,
            )

    def test_every_step_matches_the_module_pins(self):
        for index, label in enumerate(SKILL_ATTR_STEP_ORDER):
            pc, frame = make_skill_attr_step_response(self.legacy, index)
            self.assertEqual(len(pc), SKILL_ATTR_PROBE_PC_SIZE[label], label)
            self.assertEqual(
                len(frame), SKILL_ATTR_PROBE_FRAME_SIZE[label], label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                SKILL_ATTR_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                SKILL_ATTR_PROBE_FRAME_SHA256[label], label,
            )
            payload = pc[SKILL_ATTR_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                len(payload), SKILL_ATTR_PROBE_PAYLOAD_SIZE[label], label,
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                SKILL_ATTR_PROBE_PAYLOAD_SHA256[label], label,
            )
            body = payload[SKILL_ATTR_COLLECTION_HEADER_SIZE:]
            self.assertEqual(
                len(body), SKILL_ATTR_PROBE_BODY_SIZE[label], label,
            )
            self.assertEqual(
                hashlib.sha256(body).hexdigest().upper(),
                SKILL_ATTR_PROBE_BODY_SHA256[label], label,
            )

    def test_every_step_re_decodes_to_its_declared_plan_row(self):
        for index, label in enumerate(SKILL_ATTR_STEP_ORDER):
            pc, _frame = make_skill_attr_step_response(self.legacy, index)
            payload = pc[SKILL_ATTR_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                decode_skill_attr(unwrap_skill_attr_payload(payload)),
                (
                    SKILL_ATTR_PROBE_IDENTITY_LO,
                    SKILL_ATTR_PROBE_IDENTITY_HI,
                    SKILL_ATTR_STEP_RECORDS[label],
                ),
                label,
            )

    def test_the_sweep_plan_keeps_its_designed_edges(self):
        self.assertEqual(
            [len(SKILL_ATTR_STEP_RECORDS[label])
             for label in SKILL_ATTR_STEP_ORDER],
            [0, 1],
        )
        self.assertEqual(
            SKILL_ATTR_STEP_RECORDS["COUNT1_KEY1"],
            (SkillAttrRecord(1, 0, 0),),
        )


class ScenarioGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_scenario_loads_and_is_opt_in_test_only(self):
        scenario = load_skill_attr_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(scenario.hypothesis_id, SKILL_ATTR_HYPOTHESIS_ID)
        self.assertEqual(scenario.scenario_id, SKILL_ATTR_SCENARIO_ID)
        self.assertEqual(scenario.step_order, SKILL_ATTR_STEP_ORDER)
        self.assertEqual(
            scenario.spacing_seconds, SKILL_ATTR_SPACING_SECONDS,
        )
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(data["test_only"], True)
        self.assertIs(data["production_allowed"], False)
        self.assertEqual(data["persisted_post_state"]["database_write"], "none")
        self.assertEqual(data["wire"]["carrier_vital_id"], 0x309A)
        self.assertEqual(data["wire"]["attr_class_id"], 0x1661)
        self.assertEqual(
            data["wire"]["vital_version_provenance"],
            "our_design_no_capture_or_static_pin_fixes_it",
        )
        self.assertIn(
            "one_packet_sufficient_to_open_the_skill_window",
            data["nonclaims"],
        )
        self.assertIn(
            "any_meaning_for_the_two_opaque_record_fields",
            data["nonclaims"],
        )
        self.assertIn(
            "original_server_skill_attr_behavior_which_is_unrecoverable",
            data["nonclaims"],
        )

    def test_the_scenario_carries_the_re061_provenance_pins(self):
        provenance = json.loads(
            SCENARIO_PATH.read_text(encoding="utf-8")
        )["wire"]["provenance"]
        self.assertEqual(provenance["ticket"], "RE-061")
        self.assertEqual(
            provenance["serializer_sha256"],
            "9227cc6009fff2f20c79a3b19c395f9623d87f68a4ee3462e541aed62aa7e906",
        )
        self.assertEqual(
            provenance["apply_sha256"],
            "1e8d5b2e6a7814bc88cec812188d05a8673aa5d3c69e9ba9c963a2d0cd98738e",
        )
        self.assertEqual(
            provenance["handler_sha256"],
            "65a7095cc493e33988f816efcd63d48220ee9cf39437e543389d54e3718acfaf",
        )
        self.assertEqual(provenance["serializer_va"], "0x007520B0")
        self.assertEqual(provenance["apply_va"], "0x00751C70")
        self.assertEqual(provenance["handler_va"], "0x005F2400")
        self.assertEqual(provenance["window_gate_init_va"], "0x00761ED0")
        self.assertEqual(provenance["actor_slot_offset"], "0x3E8")
        self.assertEqual(provenance["serializer_len"], 465)
        self.assertEqual(provenance["apply_len"], 72)
        self.assertEqual(provenance["handler_len"], 538)

    def test_the_scenario_pins_agree_with_the_module_pins(self):
        per_step = json.loads(
            SCENARIO_PATH.read_text(encoding="utf-8")
        )["probe"]["per_step"]
        for label in SKILL_ATTR_STEP_ORDER:
            self.assertEqual(
                per_step[label]["pc_sha256"],
                SKILL_ATTR_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                per_step[label]["frame_sha256"],
                SKILL_ATTR_PROBE_FRAME_SHA256[label], label,
            )
            self.assertEqual(
                per_step[label]["body_sha256"],
                SKILL_ATTR_PROBE_BODY_SHA256[label], label,
            )
            self.assertEqual(
                per_step[label]["payload_sha256"],
                SKILL_ATTR_PROBE_PAYLOAD_SHA256[label], label,
            )

    def test_the_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-020"),
            lambda d: d.__setitem__("id", "skill_attr_hypothesis_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["dispatch"].__setitem__("spacing_seconds", 0.0),
            lambda d: d["dispatch"]["step_order"].reverse(),
            lambda d: d["dispatch"]["step_order"].pop(),
            lambda d: d["dispatch"]["step_records"]["COUNT1_KEY1"][0]
            .__setitem__("key", 999),
            lambda d: d["dispatch"].__setitem__("probe_identity_lo", 2),
            lambda d: d["wire"].__setitem__("attr_class_id", 0x12AD),
            lambda d: d["wire"].__setitem__("carrier_vital_id", 0x6E9D),
            lambda d: d["wire"].__setitem__("vital_version", 1),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "skills",
            ),
            lambda d: d["probe"]["per_step"]["COUNT1_KEY1"].__setitem__(
                "pc_sha256", "00" * 32,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_skill_attr_hypothesis_scenario(tampered)

    def test_unrelated_scenario_files_never_load_through_this_gate(self):
        for name in (
            "stats_progression_hypothesis_xp_sweep.json",
            "learn_skill_result_hypothesis_learn_sweep.json",
            "channel_message_hypothesis_channel_sweep.json",
        ):
            with self.assertRaises(ValueError):
                load_skill_attr_hypothesis_scenario(
                    ROOT / "scenarios" / name,
                )
        missing = Path(self.tmp.name) / "nope.json"
        with self.assertRaises(ValueError):
            load_skill_attr_hypothesis_scenario(missing)

    def test_a_lookalike_scenario_object_is_refused(self):
        scenario = load_skill_attr_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(),
            None,
            replace(scenario, spacing_seconds=0.25),
            replace(scenario, step_order=SKILL_ATTR_STEP_ORDER[:1]),
            replace(scenario, hypothesis_id="HYP-PF-020"),
            replace(scenario, scenario_id="skill_attr_other"),
        ):
            with self.assertRaises(ValueError):
                require_skill_attr_hypothesis_scenario(bad)

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        # The two importers are named and the list is exact, so a third one
        # shows up here as a failure -- the CHAT-CHANNEL-003 containment
        # shape.  connection.py, scenario.py and the frozen v141 module know
        # nothing about any of it.
        module = "skill_attr_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name,
            )
        legacy_source = LEGACY_PATH.read_text(encoding="utf-8")
        self.assertNotIn(module, legacy_source)
        self.assertNotIn("0x1661", legacy_source)
        self.assertNotIn("0X1661", legacy_source.upper())

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if skill_attr_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "skill_attr_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID",
            source,
        )
        # The composer is reached from exactly one call site (the import
        # line is the other mention).
        self.assertEqual(source.count("make_skill_attr_step_response"), 2)
        self.assertEqual(source.count("make_skill_attr_step_response("), 1)
        self.assertEqual(source.count("_dispatch_skill_attr_hypothesis"), 2)
        # ...and the dispatcher reads both identity halves.
        self.assertIn("identity_lo != SKILL_ATTR_PROBE_IDENTITY_LO", source)
        self.assertIn("identity_hi != SKILL_ATTR_PROBE_IDENTITY_HI", source)

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--skill-attr-hypothesis-scenario", source)
        self.assertIn(
            "'--skill-attr-hypothesis-scenario requires an explicit '\n"
            "            'existing --db'",
            source,
        )

    def test_the_lane_is_registered_in_the_hypothesis_ledger(self):
        raw = json.loads(
            (ROOT / "docs" / "HYPOTHESIS_LEDGER.json").read_text(
                encoding="utf-8",
            )
        )
        for entry in raw["entries"]:
            if entry["id"] != SKILL_ATTR_HYPOTHESIS_ID:
                continue
            self.assertEqual(entry["status"], "active")
            self.assertIs(entry["production_allowed"], False)
            self.assertEqual(
                entry["introduced_checkpoint"], "SKILL-ATTR-001",
            )
            self.assertIn("RE-061", entry["provenance"])
            self.assertIn("9227cc60", entry["provenance"])
            return
        self.fail(
            "HYP-PF-035 is not registered in docs/HYPOTHESIS_LEDGER.json"
        )

    def test_the_coverage_row_stays_in_progress_not_runtime_pass(self):
        raw = json.loads(
            (ROOT / "docs" / "FUNCTIONAL_COVERAGE.json").read_text(
                encoding="utf-8",
            )
        )
        for domain in raw["domains"]:
            for cap in domain["capabilities"]:
                if cap["id"] != "skill_use":
                    continue
                self.assertEqual(cap["status"], "in_progress")
                self.assertIn(
                    "tests/test_skill_attr_hypothesis.py", cap["test_refs"],
                )
                self.assertIn(
                    "scenarios/skill_attr_hypothesis_attr_sweep.json",
                    cap["evidence_refs"],
                )
                return
        self.fail("combat/skill_use row is missing from the coverage matrix")


class DispatchTests(unittest.TestCase):
    """The runtime wire hookup, on the REAL make_state_class path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.scenario = load_skill_attr_hypothesis_scenario(SCENARIO_PATH)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            skill_attr_hypothesis_scenario=(
                self.scenario if sweep else None
            ),
        )

    def _state(self, login, *, sweep=True, ready=True):
        state = self._state_type(sweep=sweep)(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        characters = self.store.list_characters(state.foundation.account_id)
        self.assertEqual(len(characters), 1)
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _unpin_identity(self, state, *, lo=None, hi=None):
        """Swap the selected character for one whose identity is NOT the
        pinned probe.  The harness cannot create a second character (the V25
        create wire always commits the same canonical smoke character), so
        the frozen Character record is re-stamped instead -- the dispatcher
        reads only identity_lo/identity_hi off it."""
        selected = state.foundation.selected
        self.assertIsNotNone(selected)
        replaced = dataclasses.replace(
            selected,
            identity_lo=selected.identity_lo if lo is None else lo,
            identity_hi=selected.identity_hi if hi is None else hi,
        )
        state.foundation.selected = replaced
        return selected, replaced

    def _trigger_pc(self, payload, *, outer_id=None, outer_version=0,
                    nested_version=0):
        legacy = self.legacy
        outer = legacy.GSCN_RUNTIME_PROTOCOL_REQ if outer_id is None else outer_id
        return bytes(
            legacy.u16tag(0x12, outer)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, outer_version)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
            + legacy.u8tag(0x0B, nested_version)
            + payload
        )

    def _trigger(self, probe="probe1"):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

    def _session_closed_at(self, session_id):
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (session_id,),
            ).fetchone()
        self.assertIsNotNone(row)
        return row["closed_at"]

    # ----- happy path ------------------------------------------------------

    def test_the_created_smoke_character_is_the_pinned_probe_identity(self):
        state = self._state("skillattr-id")
        selected = state.foundation.selected
        self.assertEqual(selected.identity_lo, SKILL_ATTR_PROBE_IDENTITY_LO)
        self.assertEqual(selected.identity_hi, SKILL_ATTR_PROBE_IDENTITY_HI)

    def test_one_request_sweeps_the_two_steps_in_the_pinned_order(self):
        state = self._state("skillattr01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 2)
        self.assertEqual(
            [action[0] for action in actions],
            [
                SKILL_ATTR_ACTION_LABEL_PREFIX + label
                for label in SKILL_ATTR_STEP_ORDER
            ],
        )
        self.assertEqual(
            [action[0] for action in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "HYP_PF_035_SKILL_ATTR_COUNT0_EMPTY",
                "HYP_PF_035_SKILL_ATTR_COUNT1_KEY1",
            ],
        )
        self.assertEqual(state.skill_attr_sweep_count, 1)
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_every_dispatched_frame_is_a_0x309A_vital(self):
        state = self._state("skillattr-ids")
        actions = state.dispatch(self._trigger())
        for label, action in zip(SKILL_ATTR_STEP_ORDER, actions):
            pc = action[1]
            self.assertEqual(
                pc[SKILL_ATTR_PC_VITAL_ID_SLICE],
                UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"), label,
            )
        self.assertEqual(
            self.pinned["wire"]["carrier_vital_id"], UPDATE_ATTR_VITAL_ID,
        )

    def test_the_dispatched_bodies_decode_to_the_declared_plan(self):
        # THE claim of this milestone, checked on dispatched bytes: the
        # RE-061 body shape leaves the server with the declared identity
        # and records, at both count edges.
        state = self._state("skillattr-decode")
        actions = state.dispatch(self._trigger())
        for label, action in zip(SKILL_ATTR_STEP_ORDER, actions):
            payload = action[1][SKILL_ATTR_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                decode_skill_attr(unwrap_skill_attr_payload(payload)),
                (
                    SKILL_ATTR_PROBE_IDENTITY_LO,
                    SKILL_ATTR_PROBE_IDENTITY_HI,
                    SKILL_ATTR_STEP_RECORDS[label],
                ),
                label,
            )

    def test_every_dispatched_frame_matches_its_golden_hex(self):
        state = self._state("skillattr-golden")
        actions = state.dispatch(self._trigger())
        for label, action in zip(SKILL_ATTR_STEP_ORDER, actions):
            _name, pc, frame, _delay = action
            self.assertEqual(pc.hex().upper(), GOLDEN_PC_HEX[label], label)
            self.assertEqual(
                frame.hex().upper(), GOLDEN_FRAME_HEX[label], label,
            )

    def test_every_dispatched_frame_matches_its_scenario_pin(self):
        state = self._state("skillattr-pins")
        actions = state.dispatch(self._trigger())
        per_step = self.pinned["probe"]["per_step"]
        for label, action in zip(SKILL_ATTR_STEP_ORDER, actions):
            _name, pc, frame, _delay = action
            self.assertEqual(len(pc), per_step[label]["pc_size"], label)
            self.assertEqual(len(frame), per_step[label]["frame_size"], label)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                per_step[label]["pc_sha256"], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                per_step[label]["frame_sha256"], label,
            )
            payload = pc[SKILL_ATTR_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                len(payload), per_step[label]["payload_size"], label,
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                per_step[label]["payload_sha256"], label,
            )
            # ...and the same pins the module carries, independently.
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                SKILL_ATTR_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                SKILL_ATTR_PROBE_FRAME_SHA256[label], label,
            )

    def test_the_dispatched_frames_are_the_documented_composer_output(self):
        state = self._state("skillattr-composer")
        actions = state.dispatch(self._trigger("probe2"))
        for index, action in enumerate(actions):
            expected = make_skill_attr_step_response(self.legacy, index)
            self.assertEqual((action[1], action[2]), expected, index)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("skillattr-spacing")
        actions = state.dispatch(self._trigger())
        delays = [action[3] for action in actions]
        self.assertEqual(
            delays,
            [SKILL_ATTR_FIRST_DELAY_SECONDS, SKILL_ATTR_SPACING_SECONDS],
        )
        self.assertEqual(
            delays[0], self.pinned["dispatch"]["first_frame_delay_seconds"],
        )
        self.assertEqual(
            delays[1], self.pinned["dispatch"]["spacing_seconds"],
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two different accepted chat payloads must produce byte-identical
        # sweeps: nothing from the request reaches the wire.
        state = self._state("skillattr-trigger")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe2"))
        self.assertEqual(first, second)
        self.assertEqual(state.skill_attr_sweep_count, 2)

    # ----- repeatability ---------------------------------------------------

    def test_two_requests_give_four_frames_with_no_accumulated_state(self):
        state = self._state("skillattr-repeat")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe1"))
        self.assertEqual([len(first), len(second)], [2, 2])
        self.assertEqual(first, second)
        self.assertEqual(state.skill_attr_sweep_count, 2)
        self.assertEqual(state.events.count(SWEEP_EVENT), 2)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("skillattr-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._trigger("probe1"))
        state.dispatch(self._trigger("probe2"))
        state.dispatch(self._trigger("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.skill_attr_sweep_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("skillattr-nowrite-refused")
        before = self.db_path.read_bytes()
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], bytes([base[0] ^ 0x01]) + base[1:]):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertEqual(state.skill_attr_sweep_count, 0)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.skill_attr_sweep_count, 0)

    def test_wrong_length_fails_closed(self):
        state = self._state("skillattr-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00", b"", base[:5]):
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "skill_attr_hypothesis_wrong_length_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "skill_attr_hypothesis_wrong_length_no_reply"
            ),
            4,
        )

    def test_wrong_prefix_fails_closed(self):
        state = self._state("skillattr-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        self._assert_silent(
            state, self.legacy.parse_outer(self._trigger_pc(tampered)),
            "skill_attr_hypothesis_wrong_prefix_no_reply",
        )

    def test_wrong_envelope_fails_closed(self):
        state = self._state("skillattr-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._trigger_pc(payload, nested_version=1),
            self._trigger_pc(payload, outer_version=1),
            self._trigger_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self._assert_silent(
                state, self.legacy.parse_outer(pc),
                "skill_attr_hypothesis_wrong_envelope_no_reply",
            )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("skillattr-seq", ready=False)
        self._assert_silent(
            state, self._trigger(),
            "skill_attr_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("skillattr-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self._assert_silent(
            state, self._trigger(),
            "skill_attr_hypothesis_no_selected_no_reply",
        )

    def test_a_non_probe_identity_low_half_fails_closed(self):
        state = self._state("skillattr-unpin-lo")
        _original, replaced = self._unpin_identity(
            state, lo=SKILL_ATTR_PROBE_IDENTITY_LO + 1,
        )
        self.assertNotEqual(replaced.identity_lo, SKILL_ATTR_PROBE_IDENTITY_LO)
        self._assert_silent(state, self._trigger(), IDENTITY_EVENT)

    def test_a_nonzero_identity_hi_is_not_the_pinned_probe_either(self):
        state = self._state("skillattr-unpin-hi")
        self._unpin_identity(state, hi=1)
        self._assert_silent(state, self._trigger(), IDENTITY_EVENT)

    def test_the_identity_refusal_does_not_stop_a_later_pinned_sweep(self):
        state = self._state("skillattr-repin")
        original, _replaced = self._unpin_identity(
            state, lo=SKILL_ATTR_PROBE_IDENTITY_LO ^ 0x00ABCDEF,
        )
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertEqual(state.events.count(IDENTITY_EVENT), 1)
        self.assertEqual(state.skill_attr_sweep_count, 0)
        state.foundation.selected = original
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 2)
        self.assertEqual(state.skill_attr_sweep_count, 1)
        self.assertEqual(state.events.count(SWEEP_EVENT), 1)

    def test_no_refusal_path_ever_emits_a_sweep_event(self):
        state = self._state("skillattr-refusals")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:-2],
            bytes([base[0] ^ 0x01]) + base[1:],
            base[:10] + b"\x1f" + base[11:],
        ):
            self.assertEqual(
                state.dispatch(
                    self.legacy.parse_outer(self._trigger_pc(payload))
                ),
                [],
            )
        self.assertEqual(state.events.count(SWEEP_EVENT), 0)
        for event in state.events:
            self.assertNotIn("sweep", event)

    # ----- containment -----------------------------------------------------

    def test_without_a_scenario_the_baseline_does_not_move(self):
        state = self._state("skillattr-off", sweep=False)
        rx_before = state.rx_frames
        events_before = list(state.events)
        before = self.db_path.read_bytes()
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_035")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.skill_attr_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(
            [e for e in state.events[len(events_before):]
             if "skill_attr" in e],
            [],
        )
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        from pirateforce_foundation.chat_input_hypothesis import (
            load_chat_input_hypothesis_scenario,
        )
        from pirateforce_foundation.learn_skill_result_hypothesis import (
            load_learn_skill_result_hypothesis_scenario,
        )
        from pirateforce_foundation.stats_progression_hypothesis import (
            load_stats_progression_hypothesis_scenario,
        )
        others = {
            "chat_input_hypothesis_scenario": load_chat_input_hypothesis_scenario(
                ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
            ),
            "learn_skill_result_hypothesis_scenario": (
                load_learn_skill_result_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "learn_skill_result_hypothesis_learn_sweep.json"
                )
            ),
            "stats_progression_hypothesis_scenario": (
                load_stats_progression_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "stats_progression_hypothesis_xp_sweep.json"
                )
            ),
        }
        for name, other in others.items():
            with self.subTest(mode=name):
                with self.assertRaises(ValueError) as raised:
                    make_state_class(
                        self.legacy, self.lifecycle, self.projector,
                        skill_attr_hypothesis_scenario=self.scenario,
                        **{name: other},
                    )
                self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for bad in (
            object(),
            replace(self.scenario, spacing_seconds=0.25),
            replace(self.scenario, step_order=SKILL_ATTR_STEP_ORDER[:1]),
            replace(self.scenario, hypothesis_id="HYP-PF-033"),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    skill_attr_hypothesis_scenario=bad,
                )


if __name__ == "__main__":
    unittest.main()
