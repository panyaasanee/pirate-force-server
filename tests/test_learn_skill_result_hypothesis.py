"""LEARN-SKILL-RESULT-001 (HYP-PF-033) -- the CLearnSkillResultVital 0x673C
encoder lane and its dispatch hookup.

Pure offline pytest: no network, no GameClient, no UI; the dispatch half runs
the REAL ``make_state_class`` path against a throwaway temp database.

What these tests are actually proving
-------------------------------------
GT-050 closed the 0x673C body shape byte-exactly from the read-only client
image (top serializer [0x00756100,0x00756156) sha256 c6a66b70..; nested WRITE
loop [0x00755D30,0x00755E1E) sha256 35eaeb47..; nested READ loop
[0x00756070,0x007560FB) sha256 0c78744e..; W and R agree):

    u16 tag 0x12 count, then count records of
    (u32 tag 0x14, u16 tag 0x12, u32 tag 0x14), then u8 tag 0x0B.

This file proves the server-side encoder emits exactly that order and nothing
else -- tag bytes asserted literally at their byte positions, count edges 0/1/3,
round-trip through the module's own strict decoder, the frozen v141
``make_runtime_vitals`` envelope byte-for-byte, all fifteen per-step hash pins
in module and scenario file, and the dispatch path: five frames per accepted
trigger, database byte-identical, every refusal family silent with a named
event, and containment with no scenario.

NOT tested here, because it is not claimed: any MEANING for the three record
members (they are opaque declared triples named by wire position only) or the
trailing u8; the inbound CLearnSkillVital 0x36AA direction, which has no
handler and no learn rule anywhere in this tree; anything about the original
server; and whether any client accepts or shows anything for one of these
frames -- that is an attended GT ticket, queued and not run.
"""
from __future__ import annotations

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
from pirateforce_foundation.learn_skill_result_hypothesis import (  # noqa: E402
    LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX,
    LEARN_SKILL_RESULT_COUNT_TAG,
    LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS,
    LEARN_SKILL_RESULT_HYPOTHESIS_ID,
    LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE,
    LEARN_SKILL_RESULT_PC_OVERHEAD,
    LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET,
    LEARN_SKILL_RESULT_PC_VITAL_ID_SLICE,
    LEARN_SKILL_RESULT_PROBE_FRAME_SHA256,
    LEARN_SKILL_RESULT_PROBE_FRAME_SIZE,
    LEARN_SKILL_RESULT_PROBE_PAYLOAD_SHA256,
    LEARN_SKILL_RESULT_PROBE_PAYLOAD_SIZE,
    LEARN_SKILL_RESULT_PROBE_PC_SHA256,
    LEARN_SKILL_RESULT_PROBE_PC_SIZE,
    LEARN_SKILL_RESULT_RECORD_U16_TAG,
    LEARN_SKILL_RESULT_RECORD_U32_TAG,
    LEARN_SKILL_RESULT_RECORD_WIRE_SIZE,
    LEARN_SKILL_RESULT_REJECTIONS,
    LEARN_SKILL_RESULT_SCENARIO_ID,
    LEARN_SKILL_RESULT_SPACING_SECONDS,
    LEARN_SKILL_RESULT_STEP_ORDER,
    LEARN_SKILL_RESULT_STEP_RECORDS,
    LEARN_SKILL_RESULT_STEP_TRAILING,
    LEARN_SKILL_RESULT_TRAILING_TAG,
    LEARN_SKILL_RESULT_VITAL_ID,
    LEARN_SKILL_RESULT_VITAL_VERSION,
    LearnSkillResultRecord,
    decode_learn_skill_result_payload,
    encode_learn_skill_result_payload,
    load_learn_skill_result_hypothesis_scenario,
    make_learn_skill_result_response,
    make_learn_skill_result_step_response,
    require_learn_skill_result_hypothesis_scenario,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "learn_skill_result_hypothesis_learn_sweep.json"
)
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
SWEEP_EVENT = "learn_skill_result_hypothesis_learn_sweep_sent"


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Source import only: no server is started, no socket is opened, no
        # database is touched.
        cls.legacy = load_legacy(LEGACY_PATH)


def _record_bytes(record: LearnSkillResultRecord) -> bytes:
    """The GT-050 record layout, assembled independently of the encoder."""
    return (
        bytes([LEARN_SKILL_RESULT_RECORD_U32_TAG])
        + record.record_u32_0.to_bytes(4, "little")
        + bytes([LEARN_SKILL_RESULT_RECORD_U16_TAG])
        + record.record_u16_4.to_bytes(2, "little")
        + bytes([LEARN_SKILL_RESULT_RECORD_U32_TAG])
        + record.record_u32_8.to_bytes(4, "little")
    )


def _payload_bytes(records, trailing) -> bytes:
    return (
        bytes([LEARN_SKILL_RESULT_COUNT_TAG])
        + len(records).to_bytes(2, "little")
        + b"".join(_record_bytes(record) for record in records)
        + bytes([LEARN_SKILL_RESULT_TRAILING_TAG, trailing])
    )


class WireShapeTests(_LegacyCase):
    """The proven tag bytes, at their exact byte positions, literally."""

    def test_count_zero_payload_is_the_five_proven_bytes(self):
        payload = encode_learn_skill_result_payload(self.legacy, (), 0)
        self.assertEqual(payload, b"\x12\x00\x00\x0b\x00")
        self.assertEqual(len(payload), LEARN_SKILL_RESULT_PAYLOAD_BASE_SIZE)

    def test_count_one_payload_is_the_proven_tag_order(self):
        record = LearnSkillResultRecord(0x04030201, 0x0605, 0x0A090807)
        payload = encode_learn_skill_result_payload(self.legacy, (record,), 1)
        self.assertEqual(
            payload,
            b"\x12\x01\x00"                    # u16 tag 0x12 count
            + b"\x14\x01\x02\x03\x04"          # u32 tag 0x14 record+0
            + b"\x12\x05\x06"                  # u16 tag 0x12 record+4
            + b"\x14\x07\x08\x09\x0a"          # u32 tag 0x14 record+8
            + b"\x0b\x01",                     # u8 tag 0x0B object+0x2C
        )

    def test_the_tag_constants_are_the_gt050_bytes(self):
        self.assertEqual(LEARN_SKILL_RESULT_COUNT_TAG, 0x12)
        self.assertEqual(LEARN_SKILL_RESULT_RECORD_U32_TAG, 0x14)
        self.assertEqual(LEARN_SKILL_RESULT_RECORD_U16_TAG, 0x12)
        self.assertEqual(LEARN_SKILL_RESULT_TRAILING_TAG, 0x0B)
        self.assertEqual(LEARN_SKILL_RESULT_VITAL_ID, 0x673C)
        self.assertEqual(LEARN_SKILL_RESULT_RECORD_WIRE_SIZE, 13)

    def test_payload_size_is_five_plus_thirteen_per_record(self):
        for count in (0, 1, 2, 3, 7):
            records = tuple(
                LearnSkillResultRecord(index, index, index)
                for index in range(count)
            )
            payload = encode_learn_skill_result_payload(
                self.legacy, records, 0,
            )
            self.assertEqual(len(payload), 5 + 13 * count, count)

    def test_the_encoder_matches_an_independent_assembly(self):
        # The expected bytes here are assembled by this test's own helper,
        # not by the module, so a tag or width slip in either one shows up.
        records = (
            LearnSkillResultRecord(0, 0, 0),
            LearnSkillResultRecord(0xFFFFFFFF, 0xFFFF, 0xFFFFFFFF),
            LearnSkillResultRecord(0x12345678, 0x1234, 0x60606060),
        )
        for trailing in (0, 1, 255):
            self.assertEqual(
                encode_learn_skill_result_payload(
                    self.legacy, records, trailing,
                ),
                _payload_bytes(records, trailing),
            )

    def test_record_member_order_is_not_interchangeable(self):
        self.assertNotEqual(
            encode_learn_skill_result_payload(
                self.legacy, (LearnSkillResultRecord(1, 2, 3),), 0,
            ),
            encode_learn_skill_result_payload(
                self.legacy, (LearnSkillResultRecord(3, 2, 1),), 0,
            ),
        )

    def test_composition_is_deterministic_and_repeatable(self):
        records = (LearnSkillResultRecord(9, 8, 7),)
        first = encode_learn_skill_result_payload(self.legacy, records, 1)
        second = encode_learn_skill_result_payload(self.legacy, records, 1)
        self.assertEqual(first, second)


class RoundTripTests(_LegacyCase):
    def test_encode_then_decode_is_identity(self):
        for records, trailing in (
            ((), 0),
            ((), 255),
            ((LearnSkillResultRecord(1, 2, 3),), 0),
            ((LearnSkillResultRecord(0, 0, 0),
              LearnSkillResultRecord(0xFFFFFFFF, 0xFFFF, 0xFFFFFFFF)), 1),
            (tuple(
                LearnSkillResultRecord(i * 3, i * 2, i) for i in range(9)
            ), 7),
        ):
            payload = encode_learn_skill_result_payload(
                self.legacy, records, trailing,
            )
            self.assertEqual(
                decode_learn_skill_result_payload(payload),
                (records, trailing),
            )

    def test_width_boundaries_are_carried_exactly(self):
        record = LearnSkillResultRecord(0xFFFFFFFF, 0xFFFF, 0)
        payload = encode_learn_skill_result_payload(
            self.legacy, (record,), 255,
        )
        decoded_records, decoded_trailing = (
            decode_learn_skill_result_payload(payload)
        )
        self.assertEqual(decoded_records[0].record_u32_0, 0xFFFFFFFF)
        self.assertEqual(decoded_records[0].record_u16_4, 0xFFFF)
        self.assertEqual(decoded_records[0].record_u32_8, 0)
        self.assertEqual(decoded_trailing, 255)

    def test_decode_accepts_bytearray_input(self):
        payload = bytearray(
            encode_learn_skill_result_payload(self.legacy, (), 1)
        )
        self.assertEqual(
            decode_learn_skill_result_payload(payload), ((), 1),
        )


class FailClosedTests(_LegacyCase):
    """Every rejection means: no bytes, no reply, no partial result."""

    def assert_encode_refuses(self, records, trailing, reason):
        with self.assertRaises(ValueError) as raised:
            encode_learn_skill_result_payload(self.legacy, records, trailing)
        self.assertIn(reason, str(raised.exception))
        self.assertIn(reason, LEARN_SKILL_RESULT_REJECTIONS)

    def test_non_tuple_record_containers_are_refused(self):
        for records in (
            None, [], [LearnSkillResultRecord(1, 2, 3)], "records", 3,
            (LearnSkillResultRecord(1, 2, 3), (4, 5, 6)),
            ((1, 2, 3),),
        ):
            self.assert_encode_refuses(
                records, 0, "records_not_a_tuple_of_records",
            )

    def test_non_integer_record_members_are_refused(self):
        for record in (
            LearnSkillResultRecord(True, 2, 3),
            LearnSkillResultRecord(1, True, 3),
            LearnSkillResultRecord(1, 2, True),
            LearnSkillResultRecord(1.0, 2, 3),
            LearnSkillResultRecord(1, "2", 3),
            LearnSkillResultRecord(1, 2, None),
        ):
            self.assert_encode_refuses(
                (record,), 0, "record_value_type_not_integer",
            )

    def test_out_of_width_record_members_are_refused(self):
        for record in (
            LearnSkillResultRecord(-1, 0, 0),
            LearnSkillResultRecord(1 << 32, 0, 0),
            LearnSkillResultRecord(0, -1, 0),
            LearnSkillResultRecord(0, 1 << 16, 0),
            LearnSkillResultRecord(0, 0, -1),
            LearnSkillResultRecord(0, 0, 1 << 32),
        ):
            self.assert_encode_refuses(
                (record,), 0, "record_value_outside_field_width",
            )

    def test_a_record_count_outside_u16_is_refused(self):
        records = tuple(
            LearnSkillResultRecord(0, 0, 0) for _ in range(0x10000)
        )
        self.assert_encode_refuses(records, 0, "record_count_outside_u16")
        # ...and the largest admissible count still composes.
        payload = encode_learn_skill_result_payload(
            self.legacy, records[:-1], 0,
        )
        self.assertEqual(len(payload), 5 + 13 * 0xFFFF)

    def test_bad_trailing_bytes_are_refused(self):
        for trailing, reason in (
            (True, "trailing_byte_type_not_integer"),
            (None, "trailing_byte_type_not_integer"),
            (1.0, "trailing_byte_type_not_integer"),
            ("1", "trailing_byte_type_not_integer"),
            (-1, "trailing_byte_outside_u8"),
            (256, "trailing_byte_outside_u8"),
        ):
            self.assert_encode_refuses((), trailing, reason)

    def assert_decode_refuses(self, payload, reason):
        with self.assertRaises(ValueError) as raised:
            decode_learn_skill_result_payload(payload)
        self.assertIn(reason, str(raised.exception))
        self.assertIn(reason, LEARN_SKILL_RESULT_REJECTIONS)

    def test_non_bytes_payloads_are_refused(self):
        for payload in (None, "1200000b00", 5, [0x12]):
            self.assert_decode_refuses(payload, "truncated_payload")

    def test_truncations_are_refused_at_every_boundary(self):
        good = _payload_bytes(
            (LearnSkillResultRecord(1, 2, 3),
             LearnSkillResultRecord(4, 5, 6)), 1,
        )
        # The decoder checks remaining length before it checks a tag, so
        # every proper prefix refuses as a truncation, never as a wrong tag.
        for cut in range(len(good)):
            self.assert_decode_refuses(good[:cut], "truncated_payload")

    def test_a_wrong_tag_at_any_position_is_refused_by_name(self):
        good = _payload_bytes((LearnSkillResultRecord(1, 2, 3),), 1)
        for index, reason in (
            (0, "wrong_count_tag"),
            (3, "wrong_record_u32_tag"),
            (8, "wrong_record_u16_tag"),
            (11, "wrong_record_u32_tag"),
            (16, "wrong_trailing_tag"),
        ):
            bad = bytearray(good)
            bad[index] ^= 0xFF
            self.assert_decode_refuses(bytes(bad), reason)

    def test_trailing_bytes_after_the_object_are_refused(self):
        good = _payload_bytes((), 0)
        for extra in (b"\x00", b"\x0b\x00", b"\x14\x00\x00\x00\x00"):
            self.assert_decode_refuses(
                good + extra, "trailing_bytes_after_object",
            )

    def test_a_count_larger_than_the_body_is_refused(self):
        # Declared count 2, one record present.
        payload = (
            b"\x12\x02\x00"
            + _record_bytes(LearnSkillResultRecord(1, 2, 3))
            + b"\x0b\x00"
        )
        self.assert_decode_refuses(payload, "truncated_payload")

    def test_no_rejection_path_ever_returns_a_partial_result(self):
        samples = (
            b"", b"\x12", b"\x12\x01\x00", b"\x0b\x00",
            _payload_bytes((), 0) + b"\x00",
        )
        for payload in samples:
            with self.assertRaises(ValueError) as raised:
                decode_learn_skill_result_payload(payload)
            reason = str(raised.exception).split(": ")[-1]
            self.assertIn(reason, LEARN_SKILL_RESULT_REJECTIONS)

    def test_composition_refuses_every_rejected_input(self):
        for records, trailing in (
            (None, 0),
            (((1, 2, 3),), 0),
            ((LearnSkillResultRecord(-1, 0, 0),), 0),
            ((), 256),
            ((), True),
        ):
            with self.assertRaises(ValueError):
                make_learn_skill_result_response(
                    self.legacy, records, trailing,
                )

    def test_an_unknown_step_index_is_refused(self):
        for index in (-1, 5, 99, True, None, "0", 1.0):
            with self.assertRaises(ValueError) as raised:
                make_learn_skill_result_step_response(self.legacy, index)
            self.assertIn("unknown_step_label", str(raised.exception))


class ComposedResponseTests(_LegacyCase):
    """The envelope is the reused v141 helper; every sweep frame is pinned."""

    def test_the_envelope_is_the_reused_v141_helper_not_a_new_one(self):
        records = (LearnSkillResultRecord(1, 2, 3),)
        payload = encode_learn_skill_result_payload(self.legacy, records, 1)
        self.assertEqual(
            make_learn_skill_result_response(self.legacy, records, 1),
            self.legacy.make_runtime_vitals([
                (LEARN_SKILL_RESULT_VITAL_ID,
                 LEARN_SKILL_RESULT_VITAL_VERSION, payload),
            ]),
        )

    def test_the_pc_carries_the_vital_id_and_the_payload_at_fixed_offset(self):
        records = (LearnSkillResultRecord(7, 8, 9),)
        payload = encode_learn_skill_result_payload(self.legacy, records, 0)
        pc, _frame = make_learn_skill_result_response(
            self.legacy, records, 0,
        )
        self.assertEqual(len(pc), len(payload) + LEARN_SKILL_RESULT_PC_OVERHEAD)
        self.assertEqual(
            pc[LEARN_SKILL_RESULT_PC_VITAL_ID_SLICE],
            (0x673C).to_bytes(2, "little"),
        )
        offset = LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET
        self.assertEqual(pc[offset:offset + len(payload)], payload)
        # The version byte our design sends sits right before the payload.
        self.assertEqual(
            pc[18:20],
            self.legacy.u8tag(0x0B, LEARN_SKILL_RESULT_VITAL_VERSION),
        )

    def test_every_step_matches_the_module_pins(self):
        for index, label in enumerate(LEARN_SKILL_RESULT_STEP_ORDER):
            pc, frame = make_learn_skill_result_step_response(
                self.legacy, index,
            )
            self.assertEqual(
                len(pc), LEARN_SKILL_RESULT_PROBE_PC_SIZE[label], label,
            )
            self.assertEqual(
                len(frame), LEARN_SKILL_RESULT_PROBE_FRAME_SIZE[label], label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                LEARN_SKILL_RESULT_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[label], label,
            )
            payload = pc[LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                len(payload),
                LEARN_SKILL_RESULT_PROBE_PAYLOAD_SIZE[label], label,
            )
            self.assertEqual(
                hashlib.sha256(payload).hexdigest().upper(),
                LEARN_SKILL_RESULT_PROBE_PAYLOAD_SHA256[label], label,
            )

    def test_every_step_re_decodes_to_its_declared_plan_row(self):
        for index, label in enumerate(LEARN_SKILL_RESULT_STEP_ORDER):
            pc, _frame = make_learn_skill_result_step_response(
                self.legacy, index,
            )
            payload = pc[LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                decode_learn_skill_result_payload(payload),
                (
                    LEARN_SKILL_RESULT_STEP_RECORDS[label],
                    LEARN_SKILL_RESULT_STEP_TRAILING[label],
                ),
                label,
            )

    def test_the_trailing_byte_pair_differs_in_exactly_one_byte(self):
        # COUNT1_TRAIL0 and COUNT1_TRAIL1 isolate the one unexplained byte:
        # their PCs must be the same length and differ in exactly one byte,
        # the trailing u8 payload byte.
        pc0, _f0 = make_learn_skill_result_step_response(self.legacy, 1)
        pc1, _f1 = make_learn_skill_result_step_response(self.legacy, 2)
        self.assertEqual(len(pc0), len(pc1))
        differing = [
            index for index, (a, b) in enumerate(zip(pc0, pc1)) if a != b
        ]
        self.assertEqual(len(differing), 1)
        # ...and it is the byte after the trailing tag 0x0B of the body.
        self.assertEqual(pc0[differing[0] - 1], 0x0B)
        self.assertEqual(pc0[differing[0]], 0)
        self.assertEqual(pc1[differing[0]], 1)

    def test_the_sweep_plan_keeps_its_designed_edges(self):
        self.assertEqual(
            [len(LEARN_SKILL_RESULT_STEP_RECORDS[label])
             for label in LEARN_SKILL_RESULT_STEP_ORDER],
            [0, 1, 1, 3, 3],
        )
        self.assertEqual(
            [LEARN_SKILL_RESULT_STEP_TRAILING[label]
             for label in LEARN_SKILL_RESULT_STEP_ORDER],
            [0, 0, 1, 0, 1],
        )
        multi = LEARN_SKILL_RESULT_STEP_RECORDS["COUNT3_TRAIL0"]
        self.assertIn(LearnSkillResultRecord(0, 0, 0), multi)
        self.assertIn(
            LearnSkillResultRecord(0xFFFFFFFF, 0xFFFF, 0xFFFFFFFF), multi,
        )


class ScenarioGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_scenario_loads_and_is_opt_in_test_only(self):
        scenario = load_learn_skill_result_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(
            scenario.hypothesis_id, LEARN_SKILL_RESULT_HYPOTHESIS_ID,
        )
        self.assertEqual(
            scenario.scenario_id, LEARN_SKILL_RESULT_SCENARIO_ID,
        )
        self.assertEqual(scenario.step_order, LEARN_SKILL_RESULT_STEP_ORDER)
        self.assertEqual(
            scenario.spacing_seconds, LEARN_SKILL_RESULT_SPACING_SECONDS,
        )
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(data["test_only"], True)
        self.assertIs(data["production_allowed"], False)
        self.assertEqual(data["persisted_post_state"]["database_write"], "none")
        self.assertEqual(data["wire"]["vital_id"], 0x673C)
        self.assertEqual(
            data["wire"]["vital_version_provenance"],
            "our_design_no_capture_or_static_pin_fixes_it",
        )
        self.assertIn(
            "any_meaning_for_the_three_record_members", data["nonclaims"],
        )
        self.assertIn(
            "any_meaning_for_the_trailing_u8", data["nonclaims"],
        )
        self.assertIn(
            "the_inbound_clearn_skill_request_0x36AA_or_any_learn_rule",
            data["nonclaims"],
        )
        self.assertIn(
            "original_server_learn_skill_behavior", data["nonclaims"],
        )

    def test_the_scenario_carries_the_gt050_provenance_pins(self):
        provenance = json.loads(
            SCENARIO_PATH.read_text(encoding="utf-8")
        )["wire"]["provenance"]
        self.assertEqual(provenance["ticket"], "GT-050")
        self.assertEqual(
            provenance["top_serializer_sha256"],
            "c6a66b70cc80a48b84ecc433f10aa7696eb8c2a261affd677692a6ab9c90fe94",
        )
        self.assertEqual(
            provenance["write_loop_sha256"],
            "35eaeb4718fc91dcc4b22ab13a0b1d9557834f83c735befb01cfe01bc6654944",
        )
        self.assertEqual(
            provenance["read_loop_sha256"],
            "0c78744ea4659a8a0d36a8a4015a4a9ce5904f15ccea7e8b14ccdcfbad70f3b3",
        )
        self.assertEqual(provenance["top_serializer_len"], 86)
        self.assertEqual(provenance["write_loop_len"], 238)
        self.assertEqual(provenance["read_loop_len"], 139)

    def test_the_scenario_allowlist_is_exact(self):
        data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-020"),
            lambda d: d.__setitem__("id", "learn_skill_result_hypothesis_v2"),
            lambda d: d.__setitem__("extra_field", 1),
            lambda d: d.pop("nonclaims"),
            lambda d: d["dispatch"].__setitem__("spacing_seconds", 0.0),
            lambda d: d["dispatch"]["step_order"].reverse(),
            lambda d: d["dispatch"]["step_order"].pop(),
            lambda d: d["dispatch"]["step_records"]["COUNT1_TRAIL0"][0]
            .__setitem__("record_u32_0", 999),
            lambda d: d["dispatch"]["step_trailing_u8"]
            .__setitem__("COUNT0_TRAIL0", 1),
            lambda d: d["wire"].__setitem__("vital_id", 0x36AA),
            lambda d: d["wire"].__setitem__("vital_version", 1),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "skills",
            ),
            lambda d: d["probe"]["per_step"]["COUNT3_TRAIL1"].__setitem__(
                "pc_sha256", "00" * 32,
            ),
        ):
            tampered_data = json.loads(json.dumps(data))
            mutate(tampered_data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_learn_skill_result_hypothesis_scenario(tampered)

    def test_unrelated_scenario_files_never_load_through_this_gate(self):
        for name in (
            "stats_progression_hypothesis_xp_sweep.json",
            "channel_message_hypothesis_channel_sweep.json",
            "ground_loot_hypothesis_bit08_render.json",
        ):
            with self.assertRaises(ValueError):
                load_learn_skill_result_hypothesis_scenario(
                    ROOT / "scenarios" / name,
                )
        missing = Path(self.tmp.name) / "nope.json"
        with self.assertRaises(ValueError):
            load_learn_skill_result_hypothesis_scenario(missing)

    def test_a_lookalike_scenario_object_is_refused(self):
        scenario = load_learn_skill_result_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(),
            None,
            replace(scenario, spacing_seconds=0.25),
            replace(scenario, step_order=LEARN_SKILL_RESULT_STEP_ORDER[:2]),
            replace(scenario, hypothesis_id="HYP-PF-020"),
            replace(scenario, scenario_id="learn_skill_result_other"),
        ):
            with self.assertRaises(ValueError):
                require_learn_skill_result_hypothesis_scenario(bad)

    def test_this_lane_is_reachable_only_through_the_opt_in_scenario(self):
        # The two importers are named and the list is exact, so a third one
        # shows up here as a failure -- the CHAT-CHANNEL-003 containment
        # shape.  connection.py, scenario.py and the frozen v141 module know
        # nothing about any of it.
        module = "learn_skill_result_hypothesis"
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
        self.assertNotIn("0x673C", legacy_source)
        self.assertNotIn("0x673c", legacy_source)

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if learn_skill_result_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "learn_skill_result_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID",
            source,
        )
        # The composer is reached from exactly one call site (the import
        # line is the other mention).
        self.assertEqual(
            source.count("make_learn_skill_result_step_response"), 2,
        )
        self.assertEqual(
            source.count("make_learn_skill_result_step_response("), 1,
        )
        self.assertEqual(
            source.count("_dispatch_learn_skill_result_hypothesis"), 2,
        )

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--learn-skill-result-hypothesis-scenario", source)
        self.assertIn(
            "'--learn-skill-result-hypothesis-scenario requires an explicit '\n"
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
            if entry["id"] != LEARN_SKILL_RESULT_HYPOTHESIS_ID:
                continue
            self.assertEqual(entry["status"], "active")
            self.assertIs(entry["production_allowed"], False)
            self.assertEqual(
                entry["introduced_checkpoint"], "LEARN-SKILL-RESULT-001",
            )
            self.assertIn("GT-050", entry["provenance"])
            self.assertIn("c6a66b70", entry["provenance"])
            return
        self.fail(
            "HYP-PF-033 is not registered in docs/HYPOTHESIS_LEDGER.json"
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
                    "tests/test_learn_skill_result_hypothesis.py",
                    cap["test_refs"],
                )
                self.assertIn(
                    "scenarios/learn_skill_result_hypothesis_learn_sweep.json",
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
        self.scenario = load_learn_skill_result_hypothesis_scenario(
            SCENARIO_PATH
        )
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def _state_type(self, *, sweep=True):
        return make_state_class(
            self.legacy, self.lifecycle, self.projector,
            learn_skill_result_hypothesis_scenario=(
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

    def test_one_request_sweeps_the_five_steps_in_the_pinned_order(self):
        state = self._state("learn01")
        session_id = state.foundation.session_id
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 5)
        self.assertEqual(
            [action[0] for action in actions],
            [
                LEARN_SKILL_RESULT_ACTION_LABEL_PREFIX + label
                for label in LEARN_SKILL_RESULT_STEP_ORDER
            ],
        )
        self.assertEqual(
            [action[0] for action in actions],
            self.pinned["dispatch"]["action_labels"],
        )
        self.assertEqual(
            [action[0] for action in actions],
            [
                "HYP_PF_033_LEARN_SKILL_RESULT_COUNT0_TRAIL0",
                "HYP_PF_033_LEARN_SKILL_RESULT_COUNT1_TRAIL0",
                "HYP_PF_033_LEARN_SKILL_RESULT_COUNT1_TRAIL1",
                "HYP_PF_033_LEARN_SKILL_RESULT_COUNT3_TRAIL0",
                "HYP_PF_033_LEARN_SKILL_RESULT_COUNT3_TRAIL1",
            ],
        )
        self.assertEqual(state.learn_skill_result_sweep_count, 1)
        self.assertIn(SWEEP_EVENT, state.events)
        self.assertIsNone(self._session_closed_at(session_id))

    def test_every_dispatched_frame_is_a_0x673C_vital(self):
        state = self._state("learn-ids")
        actions = state.dispatch(self._trigger())
        for label, action in zip(LEARN_SKILL_RESULT_STEP_ORDER, actions):
            pc = action[1]
            self.assertEqual(
                pc[LEARN_SKILL_RESULT_PC_VITAL_ID_SLICE],
                LEARN_SKILL_RESULT_VITAL_ID.to_bytes(2, "little"), label,
            )
        self.assertEqual(
            self.pinned["wire"]["vital_id"], LEARN_SKILL_RESULT_VITAL_ID,
        )

    def test_the_dispatched_bodies_decode_to_the_declared_plan(self):
        # THE claim of this milestone, checked on dispatched bytes: the
        # GT-050 body shape leaves the server with the declared opaque
        # triples and trailing byte, at every count edge.
        state = self._state("learn-decode")
        actions = state.dispatch(self._trigger())
        for label, action in zip(LEARN_SKILL_RESULT_STEP_ORDER, actions):
            payload = action[1][LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET:-2]
            self.assertEqual(
                decode_learn_skill_result_payload(payload),
                (
                    LEARN_SKILL_RESULT_STEP_RECORDS[label],
                    LEARN_SKILL_RESULT_STEP_TRAILING[label],
                ),
                label,
            )

    def test_every_dispatched_frame_matches_its_scenario_pin(self):
        state = self._state("learn-pins")
        actions = state.dispatch(self._trigger())
        per_step = self.pinned["probe"]["per_step"]
        for label, action in zip(LEARN_SKILL_RESULT_STEP_ORDER, actions):
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
            payload = pc[LEARN_SKILL_RESULT_PC_PAYLOAD_OFFSET:-2]
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
                LEARN_SKILL_RESULT_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                LEARN_SKILL_RESULT_PROBE_FRAME_SHA256[label], label,
            )

    def test_the_dispatched_frames_are_the_documented_composer_output(self):
        state = self._state("learn-composer")
        actions = state.dispatch(self._trigger("probe2"))
        for index, action in enumerate(actions):
            expected = make_learn_skill_result_step_response(
                self.legacy, index,
            )
            self.assertEqual((action[1], action[2]), expected, index)

    def test_the_spacing_matches_the_scenario(self):
        state = self._state("learn-spacing")
        actions = state.dispatch(self._trigger())
        delays = [action[3] for action in actions]
        self.assertEqual(
            delays,
            [LEARN_SKILL_RESULT_FIRST_DELAY_SECONDS]
            + [LEARN_SKILL_RESULT_SPACING_SECONDS] * 4,
        )
        self.assertEqual(
            delays[0], self.pinned["dispatch"]["first_frame_delay_seconds"],
        )
        self.assertEqual(
            set(delays[1:]), {self.pinned["dispatch"]["spacing_seconds"]},
        )

    def test_the_request_payload_is_a_trigger_not_an_input(self):
        # Two different accepted chat payloads must produce byte-identical
        # sweeps: nothing from the request reaches the wire.
        state = self._state("learn-trigger")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe2"))
        self.assertEqual(first, second)
        self.assertEqual(state.learn_skill_result_sweep_count, 2)

    # ----- repeatability ---------------------------------------------------

    def test_two_requests_give_ten_frames_with_no_accumulated_state(self):
        state = self._state("learn-repeat")
        first = state.dispatch(self._trigger("probe1"))
        second = state.dispatch(self._trigger("probe1"))
        self.assertEqual([len(first), len(second)], [5, 5])
        self.assertEqual(first, second)
        self.assertEqual(state.learn_skill_result_sweep_count, 2)
        self.assertEqual(state.events.count(SWEEP_EVENT), 2)

    def test_the_sweep_writes_nothing_to_the_database(self):
        state = self._state("learn-nowrite")
        session_id = state.foundation.session_id
        before = self.db_path.read_bytes()
        state.dispatch(self._trigger("probe1"))
        state.dispatch(self._trigger("probe2"))
        state.dispatch(self._trigger("probe1"))
        self.assertEqual(self.db_path.read_bytes(), before)
        self.assertIsNone(self._session_closed_at(session_id))
        self.assertEqual(state.learn_skill_result_sweep_count, 3)

    def test_a_refused_frame_also_writes_nothing(self):
        state = self._state("learn-nowrite-refused")
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
        self.assertEqual(state.learn_skill_result_sweep_count, 0)

    # ----- fail closed -----------------------------------------------------

    def _assert_silent(self, state, parsed, event):
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn(event, state.events)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(state.learn_skill_result_sweep_count, 0)

    def test_wrong_length_fails_closed(self):
        state = self._state("learn-length")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (base[:-2], base + b"A\x00", b"", base[:5]):
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "learn_skill_result_hypothesis_wrong_length_no_reply",
            )
        self.assertEqual(
            state.events.count(
                "learn_skill_result_hypothesis_wrong_length_no_reply"
            ),
            4,
        )

    def test_wrong_prefix_fails_closed(self):
        state = self._state("learn-prefix")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        tampered = bytes([base[0] ^ 0x01]) + base[1:]
        self.assertEqual(len(tampered), 34)
        self._assert_silent(
            state, self.legacy.parse_outer(self._trigger_pc(tampered)),
            "learn_skill_result_hypothesis_wrong_prefix_no_reply",
        )

    def test_wrong_text_bytes_fail_closed(self):
        state = self._state("learn-text")
        base = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for payload in (
            base[:11] + b"\x01" + base[12:],
            base[:10] + b"\x1f" + base[11:],
            base[:10] + b"\x7f" + base[11:],
        ):
            self.assertEqual(len(payload), 34)
            self._assert_silent(
                state, self.legacy.parse_outer(self._trigger_pc(payload)),
                "learn_skill_result_hypothesis_wrong_text_no_reply",
            )

    def test_wrong_envelope_fails_closed(self):
        state = self._state("learn-envelope")
        payload = CHAT_INPUT_PROBE_PAYLOADS["probe1"]
        for pc in (
            self._trigger_pc(payload, nested_version=1),
            self._trigger_pc(payload, outer_version=1),
            self._trigger_pc(payload, outer_id=self.legacy.GSCN_LOGIN_PROTOCOL),
        ):
            self._assert_silent(
                state, self.legacy.parse_outer(pc),
                "learn_skill_result_hypothesis_wrong_envelope_no_reply",
            )

    def test_not_yet_runtime_ready_fails_closed(self):
        state = self._state("learn-seq", ready=False)
        self._assert_silent(
            state, self._trigger(),
            "learn_skill_result_hypothesis_wrong_sequence_no_reply",
        )

    def test_no_selected_character_fails_closed(self):
        state = self._state_type()("learn-noselect")
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()
        ))
        self.assertIsNone(state.foundation.selected)
        self._assert_silent(
            state, self._trigger(),
            "learn_skill_result_hypothesis_no_selected_no_reply",
        )

    def test_no_refusal_path_ever_emits_a_sweep_event(self):
        state = self._state("learn-refusals")
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
        state = self._state("learn-off", sweep=False)
        rx_before = state.rx_frames
        events_before = list(state.events)
        before = self.db_path.read_bytes()
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [a for a in actions if a[0].startswith("HYP_PF_033")], [],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(state.learn_skill_result_sweep_count, 0)
        self.assertNotIn(SWEEP_EVENT, state.events)
        self.assertEqual(
            [e for e in state.events[len(events_before):]
             if "learn_skill_result" in e],
            [],
        )
        self.assertEqual(self.db_path.read_bytes(), before)

    def test_the_lane_is_mutually_exclusive_with_every_other_mode(self):
        from pirateforce_foundation.channel_message_hypothesis import (
            load_channel_message_hypothesis_scenario,
        )
        from pirateforce_foundation.chat_input_hypothesis import (
            load_chat_input_hypothesis_scenario,
        )
        from pirateforce_foundation.stats_progression_hypothesis import (
            load_stats_progression_hypothesis_scenario,
        )
        others = {
            "chat_input_hypothesis_scenario": load_chat_input_hypothesis_scenario(
                ROOT / "scenarios" / "chat_input_hypothesis_echo.json"
            ),
            "channel_message_hypothesis_scenario": (
                load_channel_message_hypothesis_scenario(
                    ROOT / "scenarios"
                    / "channel_message_hypothesis_channel_sweep.json"
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
                        learn_skill_result_hypothesis_scenario=self.scenario,
                        **{name: other},
                    )
                self.assertIn("mutually exclusive", str(raised.exception))

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        for bad in (
            object(),
            replace(self.scenario, spacing_seconds=0.25),
            replace(
                self.scenario,
                step_order=LEARN_SKILL_RESULT_STEP_ORDER[:1],
            ),
            replace(self.scenario, hypothesis_id="HYP-PF-032"),
        ):
            with self.assertRaises(ValueError):
                make_state_class(
                    self.legacy, self.lifecycle, self.projector,
                    learn_skill_result_hypothesis_scenario=bad,
                )


if __name__ == "__main__":
    unittest.main()
