"""STATS-PROG-002 (HYP-PF-020) -- the UpdateAttrVital 0x309A progression encoder.

STATS-PROG-001 characterised the client's progression surface byte-exactly and
measured the server gap: of the nineteen named progression fields the whole
repository emitted two (the HP pair), and level, experience and the five
ability values had never been on any wire this project produced.  This module
tests the encoder that closes the field half of that gap, offline:

  * the field tables are the report's tables -- mask bit, object offset, wire
    tag and width for every implemented field -- and the emission order is
    ascending mask bit, which the gate-pin addresses recorded in the report
    independently confirm (ascending address == ascending emission order in a
    linear serializer, and the pins ascend with the bits in both blocks);
  * the encoder is generic and mask-driven, and for the baseline field set it
    reproduces ``player_wire.make_actor_attr_with_name`` BYTE FOR BYTE -- a
    hand-written, field-by-field projection that has been in front of a real
    client since NAME-002.  Two independent code paths agreeing on 73 bytes is
    the evidence that the tags, widths, block boundaries and field order are
    right; a single wrong nibble cannot survive it;
  * every composed body re-decodes to exactly the requested ``(identity,
    fields)``, and every rejection family produces no bytes at all;
  * the composed frames ride the frozen v141 ``make_runtime_vitals`` envelope
    with the Attr body at a fixed offset, and the nine pinned probe frames are
    hash-pinned in the module AND in the scenario file, from the same live
    computation;
  * containment: exactly ``app.py`` and ``runtime.py`` import the lane, every
    runtime mention sits inside the scenario gate, and the frozen v141 module
    knows nothing about any of it.

NOT proven here, and this is the load-bearing limit: that any client renders
any of it.  That is GT-017, attended, not run.  Nothing in this project has
ever seen a progression field on a wire in either direction.
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

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_name,
)
from pirateforce_foundation.stats_progression_hypothesis import (  # noqa: E402
    ACTOR_ATTR_EXTRA_GROUP_TAG,
    ACTOR_ATTR_EXTRA_GROUP_VALUE,
    ACTOR_ATTR_FIELDS,
    ACTOR_ATTR_GATE_PINS,
    ACTOR_ATTR_ID,
    ACTOR_ATTR_MASK_LOW_HALF_LIMIT,
    BASIC_ATTR_FIELDS,
    BASIC_ATTR_GATE_PINS,
    DB_ATTRIBUTE_IDENTITY_BIT,
    DB_ATTRIBUTE_MASK_TAG,
    NOT_IMPLEMENTED_BASIC_ATTR_BITS,
    PROGRESSION_FIELDS,
    STATS_PC_ATTR_BODY_OFFSET,
    STATS_PC_OVERHEAD,
    STATS_PC_PAYLOAD_OFFSET,
    STATS_PROBE_ACTOR,
    STATS_PROBE_ATTR_BODY_SHA256,
    STATS_PROBE_ATTR_BODY_SIZE,
    STATS_PROBE_CASH,
    STATS_PROBE_FRAME_SHA256,
    STATS_PROBE_FRAME_SIZE,
    STATS_PROBE_PC_SHA256,
    STATS_PROBE_PC_SIZE,
    STATS_PROGRESSION_ACTION_LABEL_PREFIX,
    STATS_PROGRESSION_EXPERIENCE_1,
    STATS_PROGRESSION_EXPERIENCE_2,
    STATS_PROGRESSION_HYPOTHESIS_ID,
    STATS_PROGRESSION_LEVEL,
    STATS_PROGRESSION_SCENARIO_ID,
    STATS_PROGRESSION_SPACING_SECONDS,
    STATS_PROGRESSION_STEP_FIELDS,
    STATS_PROGRESSION_STEP_ORDER,
    StatsProgressionActor,
    UPDATE_ATTR_VITAL_ID,
    decode_actor_attr,
    encode_actor_attr,
    load_stats_progression_hypothesis_scenario,
    make_stats_progression_response,
    make_stats_progression_step_response,
    require_stats_progression_hypothesis_scenario,
    stats_progression_baseline_fields,
    stats_progression_step_fields,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "stats_progression_hypothesis_xp_sweep.json"
)
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"


class _LegacyCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)


class SchemaTests(_LegacyCase):
    """The field tables are STATS-PROG-001's tables, not a re-derivation."""

    def test_the_named_progression_fields_carry_the_reports_offsets(self):
        expected = {
            # BasicAttr, report section 4.
            "level": (0x0002, 0x5E, 0x12, "u16"),
            "hp_current": (0x0004, 0x44, 0x14, "u32"),
            "hp_max": (0x0008, 0x48, 0x14, "u32"),
            "mp_current": (0x0010, 0x4C, 0x14, "u32"),
            "mp_max": (0x0020, 0x50, 0x14, "u32"),
            "scene_id": (0x0100, 0x5C, 0x12, "u16"),
            "scene_sequence": (0x0200, 0x60, 0x32, "qword"),
            # ActorAttr, report section 5.
            "class_id": (0x00000001, 0x8C, 0x19, "u32"),
            "skill_points": (0x00000008, 0x7C, 0x19, "u32"),
            "unspent_ability_points": (0x00000010, 0x80, 0x12, "u16"),
            "ability_str": (0x00000020, 0x82, 0x12, "u16"),
            "ability_con": (0x00000040, 0x84, 0x12, "u16"),
            "ability_dex": (0x00000080, 0x86, 0x12, "u16"),
            "ability_int": (0x00000100, 0x88, 0x12, "u16"),
            "ability_per": (0x00000200, 0x8A, 0x12, "u16"),
            "experience": (0x00000400, 0xA0, 0x32, "qword"),
            "cash": (0x00000800, 0xA8, 0x32, "qword"),
            "ability_bonus_str": (0x00040000, 0x182, 0x12, "u16"),
            "ability_bonus_con": (0x00080000, 0x184, 0x12, "u16"),
            "ability_bonus_dex": (0x00100000, 0x186, 0x12, "u16"),
            "ability_bonus_int": (0x00200000, 0x188, 0x12, "u16"),
            "ability_bonus_per": (0x00400000, 0x18A, 0x12, "u16"),
            "character_name": (0x01000000, 0x164, 0x48, "wstring"),
        }
        self.assertEqual(set(PROGRESSION_FIELDS), set(expected))
        for name, (bit, offset, tag, kind) in expected.items():
            field = PROGRESSION_FIELDS[name]
            self.assertEqual(
                (field.mask_bit, field.offset, field.tag, field.kind),
                (bit, offset, tag, kind), name,
            )

    def test_emission_order_is_ascending_mask_bit_in_both_blocks(self):
        for fields in (BASIC_ATTR_FIELDS, ACTOR_ATTR_FIELDS):
            bits = [field.mask_bit for field in fields]
            self.assertEqual(bits, sorted(bits))
            self.assertEqual(len(set(bits)), len(bits))

    def test_the_reports_gate_pins_ascend_with_the_mask_bits(self):
        # This is the whole argument for the field order: a linear serializer
        # emits in code order, so if the gate addresses did NOT ascend with the
        # bits the ordering rule would be wrong.  They do, in both tables.
        for fields, pins in (
            (BASIC_ATTR_FIELDS, BASIC_ATTR_GATE_PINS),
            (ACTOR_ATTR_FIELDS, ACTOR_ATTR_GATE_PINS),
        ):
            addresses = [
                pins[field.mask_bit]
                for field in fields if field.mask_bit in pins
            ]
            self.assertEqual(addresses, sorted(addresses))
            self.assertEqual(len(set(addresses)), len(addresses))

    def test_the_one_unpinned_bit_is_declared_as_a_derivation(self):
        # Every implemented field but the ActorAttr name has a gate pin in the
        # report; the name's bit is derived from the mask player_wire has had
        # on the wire since NAME-002 and says so in its own evidence string.
        unpinned = [
            field for field in ACTOR_ATTR_FIELDS
            if field.mask_bit not in ACTOR_ATTR_GATE_PINS
        ]
        self.assertEqual([field.name for field in unpinned], ["character_name"])
        self.assertIn("derived", unpinned[0].evidence)
        self.assertEqual(
            unpinned[0].mask_bit | PROGRESSION_FIELDS["cash"].mask_bit,
            0x01000800,
        )

    def test_the_unimplemented_bits_are_declared_not_silently_missing(self):
        implemented = {field.mask_bit for field in BASIC_ATTR_FIELDS}
        for bit in NOT_IMPLEMENTED_BASIC_ATTR_BITS:
            self.assertNotIn(bit, implemented)
        # Nothing in the low-half table strays into the high half of the
        # 64-bit ActorAttr mask, which this lane refuses by construction.
        for field in ACTOR_ATTR_FIELDS:
            self.assertLess(field.mask_bit, ACTOR_ATTR_MASK_LOW_HALF_LIMIT)


class EncoderTests(_LegacyCase):
    """The encoder against the one projection a real client has accepted."""

    def test_the_baseline_reproduces_player_wire_byte_for_byte(self):
        actor = STATS_PROBE_ACTOR
        composed = encode_actor_attr(
            self.legacy, actor.identity_lo, actor.identity_hi,
            stats_progression_baseline_fields(self.legacy, actor),
        )
        proven = make_actor_attr_with_name(
            self.legacy, actor.identity_lo, actor.identity_hi,
            actor.scene_id, actor.scene_sequence, actor.character_name,
        )
        self.assertEqual(composed, proven)
        self.assertEqual(len(composed), 73)

    def test_the_crosscheck_holds_for_other_identities_and_scenes(self):
        for actor in (
            StatsProgressionActor(0x10020007, 0, 2, 0, "test01"),
            StatsProgressionActor(1, 0, 1, 9, "A"),
            StatsProgressionActor(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 5, "abcdef"),
        ):
            composed = encode_actor_attr(
                self.legacy, actor.identity_lo, actor.identity_hi,
                stats_progression_baseline_fields(self.legacy, actor),
            )
            proven = make_actor_attr_with_name(
                self.legacy, actor.identity_lo, actor.identity_hi,
                actor.scene_id, actor.scene_sequence, actor.character_name,
            )
            self.assertEqual(composed, proven, actor)

    def test_the_baseline_cash_constant_matches_the_frozen_module(self):
        self.assertEqual(self.legacy.V116_INITIAL_CASH, STATS_PROBE_CASH)

    def test_the_ids_match_the_frozen_module(self):
        self.assertEqual(self.legacy.UPDATE_ATTR_VITAL, UPDATE_ATTR_VITAL_ID)
        self.assertEqual(self.legacy.ACTOR_ATTR, ACTOR_ATTR_ID)

    def test_a_sparse_body_carries_only_the_requested_fields(self):
        body = encode_actor_attr(
            self.legacy, 1, 0, {"experience": 5, "level": 2},
        )
        self.assertEqual(decode_actor_attr(body), (1, 0, {"experience": 5, "level": 2}))
        # DBAttribute mask + identity, BasicAttr mask + one u16, ActorAttr
        # 64-bit mask + flag + one qword.
        self.assertEqual(body[0], DB_ATTRIBUTE_MASK_TAG)
        self.assertEqual(body[1], DB_ATTRIBUTE_IDENTITY_BIT)
        self.assertEqual(len(body), 2 + 9 + 3 + 3 + 9 + 2 + 9)

    def test_the_extra_group_flag_is_the_value_v141_has_always_sent(self):
        body = encode_actor_attr(self.legacy, 1, 0, {"cash": 0})
        index = body.index(bytes([ACTOR_ATTR_EXTRA_GROUP_TAG,
                                 ACTOR_ATTR_EXTRA_GROUP_VALUE]))
        self.assertGreater(index, 0)
        proven = make_actor_attr_with_name(self.legacy, 1, 0, 1, 0, "x")
        self.assertIn(
            bytes([ACTOR_ATTR_EXTRA_GROUP_TAG, ACTOR_ATTR_EXTRA_GROUP_VALUE]),
            proven,
        )

    def test_every_field_round_trips_on_its_own(self):
        samples = {
            "level": 250, "hp_current": 7, "hp_max": 9, "mp_current": 11,
            "mp_max": 13, "scene_id": 3, "scene_sequence": 2 ** 40,
            "class_id": 4, "skill_points": 6, "unspent_ability_points": 8,
            "ability_str": 1, "ability_con": 2, "ability_dex": 3,
            "ability_int": 4, "ability_per": 5, "experience": 2 ** 33,
            "cash": 12345, "ability_bonus_str": 6, "ability_bonus_con": 7,
            "ability_bonus_dex": 8, "ability_bonus_int": 9,
            "ability_bonus_per": 10, "character_name": "test01",
        }
        self.assertEqual(set(samples), set(PROGRESSION_FIELDS))
        for name, value in samples.items():
            body = encode_actor_attr(self.legacy, 0x11, 0x22, {name: value})
            self.assertEqual(
                decode_actor_attr(body), (0x11, 0x22, {name: value}), name,
            )
        every = encode_actor_attr(self.legacy, 0x11, 0x22, dict(samples))
        self.assertEqual(decode_actor_attr(every), (0x11, 0x22, samples))

    def test_the_body_bytes_do_not_depend_on_the_order_the_caller_asked(self):
        forward = encode_actor_attr(
            self.legacy, 1, 0, {"level": 2, "experience": 3, "cash": 4},
        )
        backward = encode_actor_attr(
            self.legacy, 1, 0, {"cash": 4, "experience": 3, "level": 2},
        )
        self.assertEqual(forward, backward)


class FailClosedTests(_LegacyCase):
    """Every refusal family produces no bytes at all."""

    def _refused(self, **kwargs):
        with self.assertRaises(ValueError):
            encode_actor_attr(self.legacy, 1, 0, kwargs)

    def test_unknown_field_names_are_refused(self):
        for name in ("exp", "Level", "ability_luk", "", "hp"):
            self._refused(**{name: 1})

    def test_wrong_value_types_are_refused(self):
        for value in (True, 1.0, "5", None, b"5"):
            self._refused(experience=value)

    def test_out_of_range_values_are_refused(self):
        self._refused(level=0x10000)
        self._refused(level=-1)
        self._refused(class_id=1 << 32)
        self._refused(experience=1 << 64)
        self._refused(ability_str=-1)

    def test_unencodable_or_empty_names_are_refused(self):
        self._refused(character_name="")
        self._refused(character_name=5)
        # A valid surrogate pair decodes fine but is four wire bytes for one
        # character, which breaks the two-bytes-per-code-unit invariant.
        self._refused(character_name="a\U0001F600b")

    def test_bad_identities_are_refused(self):
        for lo, hi in ((-1, 0), (0, -1), (1 << 32, 0), (0, 1 << 32),
                       (True, 0), ("1", 0)):
            with self.assertRaises(ValueError):
                encode_actor_attr(self.legacy, lo, hi, {"cash": 0})

    def test_a_non_dictionary_field_set_is_refused(self):
        for bad in ([("cash", 0)], "cash", None, 5):
            with self.assertRaises(ValueError):
                encode_actor_attr(self.legacy, 1, 0, bad)

    def test_the_decoder_refuses_damaged_bodies(self):
        good = encode_actor_attr(self.legacy, 1, 0, {"level": 2, "cash": 3})
        for damaged in (
            good[:-1],
            good + b"\x00",
            bytes([good[0] ^ 0x01]) + good[1:],
            good[:1] + bytes([0x03]) + good[2:],
            b"",
            b"\x0b\x01",
        ):
            with self.assertRaises(ValueError):
                decode_actor_attr(damaged)

    def test_the_decoder_refuses_a_mask_bit_this_lane_does_not_implement(self):
        good = encode_actor_attr(self.legacy, 1, 0, {"cash": 3})
        # BasicAttr mask sits at offset 11..13; set bit 0x0001 (the BasicAttr
        # name field, deliberately unimplemented) without supplying bytes.
        tampered = good[:12] + bytes([good[12] | 0x01]) + good[13:]
        with self.assertRaises(ValueError):
            decode_actor_attr(tampered)

    def test_a_step_index_outside_the_plan_is_refused(self):
        for index in (-1, len(STATS_PROGRESSION_STEP_ORDER), True, 1.0, "0"):
            with self.assertRaises(ValueError):
                stats_progression_step_fields(
                    self.legacy, STATS_PROBE_ACTOR, index,
                )


class CompositionTests(_LegacyCase):
    """The frames ride the frozen envelope and match the pins."""

    def test_the_envelope_geometry_is_the_frozen_one_vital_collection(self):
        pc, frame = make_stats_progression_step_response(
            self.legacy, STATS_PROBE_ACTOR, 0,
        )
        body = encode_actor_attr(
            self.legacy, STATS_PROBE_ACTOR.identity_lo,
            STATS_PROBE_ACTOR.identity_hi,
            stats_progression_baseline_fields(self.legacy, STATS_PROBE_ACTOR),
        )
        self.assertEqual(len(pc), len(body) + 11 + STATS_PC_OVERHEAD)
        self.assertEqual(
            pc[STATS_PC_ATTR_BODY_OFFSET:STATS_PC_ATTR_BODY_OFFSET + len(body)],
            body,
        )
        self.assertEqual(
            pc[STATS_PC_PAYLOAD_OFFSET:STATS_PC_PAYLOAD_OFFSET + 2],
            self.legacy.u16tag(0x12, 1)[:2],
        )
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_vital_id_on_the_wire_is_the_delta_pipe(self):
        pc, _frame = make_stats_progression_step_response(
            self.legacy, STATS_PROBE_ACTOR, 0,
        )
        self.assertEqual(
            pc[16:18], UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"),
        )
        self.assertIn(
            self.legacy.u16tag(0x12, ACTOR_ATTR_ID),
            pc[STATS_PC_PAYLOAD_OFFSET:],
        )

    def test_every_pinned_step_reproduces_its_hashes(self):
        for index, label in enumerate(STATS_PROGRESSION_STEP_ORDER):
            fields = stats_progression_step_fields(
                self.legacy, STATS_PROBE_ACTOR, index,
            )
            body = encode_actor_attr(
                self.legacy, STATS_PROBE_ACTOR.identity_lo,
                STATS_PROBE_ACTOR.identity_hi, fields,
            )
            pc, frame = make_stats_progression_step_response(
                self.legacy, STATS_PROBE_ACTOR, index,
            )
            self.assertEqual(
                hashlib.sha256(body).hexdigest().upper(),
                STATS_PROBE_ATTR_BODY_SHA256[label], label,
            )
            self.assertEqual(len(body), STATS_PROBE_ATTR_BODY_SIZE[label], label)
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                STATS_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(len(pc), STATS_PROBE_PC_SIZE[label], label)
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                STATS_PROBE_FRAME_SHA256[label], label,
            )
            self.assertEqual(len(frame), STATS_PROBE_FRAME_SIZE[label], label)

    def test_the_plan_is_cumulative_and_changes_one_thing_per_frame(self):
        previous = stats_progression_baseline_fields(
            self.legacy, STATS_PROBE_ACTOR,
        )
        for index, label in enumerate(STATS_PROGRESSION_STEP_ORDER):
            fields = stats_progression_step_fields(
                self.legacy, STATS_PROBE_ACTOR, index,
            )
            added = STATS_PROGRESSION_STEP_FIELDS[label]
            self.assertLessEqual(set(previous), set(fields), label)
            for name, value in previous.items():
                if name in added:
                    continue
                self.assertEqual(fields[name], value, (label, name))
            for name, value in added.items():
                self.assertEqual(fields[name], value, (label, name))
            previous = fields
        # By the last frame every progression value of the plan is present.
        self.assertEqual(previous["experience"], STATS_PROGRESSION_EXPERIENCE_2)
        self.assertEqual(previous["level"], STATS_PROGRESSION_LEVEL)
        self.assertEqual(
            [previous[name] for name in (
                "ability_str", "ability_con", "ability_dex", "ability_int",
                "ability_per",
            )],
            [11, 22, 33, 44, 55],
        )

    def test_the_two_experience_frames_really_differ(self):
        self.assertNotEqual(
            STATS_PROGRESSION_EXPERIENCE_1, STATS_PROGRESSION_EXPERIENCE_2,
        )
        first = make_stats_progression_step_response(
            self.legacy, STATS_PROBE_ACTOR, 1,
        )
        second = make_stats_progression_step_response(
            self.legacy, STATS_PROBE_ACTOR, 2,
        )
        self.assertNotEqual(first, second)
        self.assertEqual(len(first[0]), len(second[0]))
        differing = [
            index for index, (a, b) in enumerate(zip(first[0], second[0]))
            if a != b
        ]
        # One qword field changed and nothing else.
        self.assertLessEqual(len(differing), 8)

    def test_composition_is_deterministic(self):
        for index in range(len(STATS_PROGRESSION_STEP_ORDER)):
            self.assertEqual(
                make_stats_progression_step_response(
                    self.legacy, STATS_PROBE_ACTOR, index,
                ),
                make_stats_progression_step_response(
                    self.legacy, STATS_PROBE_ACTOR, index,
                ),
            )

    def test_a_bad_actor_object_is_refused(self):
        for bad in (object(), None, ("a", "b")):
            with self.assertRaises(ValueError):
                make_stats_progression_response(self.legacy, bad, {})


class ScenarioGateTests(_LegacyCase):
    """The scenario loads through an exact allowlist and pins the same bytes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_scenario_loads_and_carries_the_dispatch_policy(self):
        scenario = load_stats_progression_hypothesis_scenario(SCENARIO_PATH)
        self.assertEqual(scenario.scenario_id, STATS_PROGRESSION_SCENARIO_ID)
        self.assertEqual(scenario.hypothesis_id, STATS_PROGRESSION_HYPOTHESIS_ID)
        self.assertEqual(scenario.step_order, STATS_PROGRESSION_STEP_ORDER)
        self.assertEqual(
            scenario.spacing_seconds, STATS_PROGRESSION_SPACING_SECONDS,
        )

    def test_the_profile_stays_test_only_with_no_database_write(self):
        self.assertIs(self.data["test_only"], True)
        self.assertIs(self.data["production_allowed"], False)
        self.assertEqual(
            self.data["persisted_post_state"]["database_write"], "none",
        )
        self.assertEqual(
            self.data["hypothesis_id"], STATS_PROGRESSION_HYPOTHESIS_ID,
        )

    def test_the_scenario_pins_the_same_hashes_the_module_carries(self):
        per_step = self.data["probe"]["per_step"]
        self.assertEqual(
            list(per_step), list(STATS_PROGRESSION_STEP_ORDER),
        )
        for label in STATS_PROGRESSION_STEP_ORDER:
            row = per_step[label]
            self.assertEqual(row["pc_sha256"], STATS_PROBE_PC_SHA256[label])
            self.assertEqual(
                row["frame_sha256"], STATS_PROBE_FRAME_SHA256[label],
            )
            self.assertEqual(
                row["attr_body_sha256"], STATS_PROBE_ATTR_BODY_SHA256[label],
            )
            self.assertEqual(row["pc_size"], STATS_PROBE_PC_SIZE[label])
            self.assertEqual(row["frame_size"], STATS_PROBE_FRAME_SIZE[label])

    def test_the_scenarios_field_schema_is_the_modules_field_table(self):
        declared = dict(self.data["wire"]["basic_attr_fields"])
        declared.update(self.data["wire"]["actor_attr_fields"])
        self.assertEqual(set(declared), set(PROGRESSION_FIELDS))
        for name, row in declared.items():
            field = PROGRESSION_FIELDS[name]
            self.assertEqual(row["mask_bit"], field.mask_bit, name)
            self.assertEqual(row["object_offset"], field.offset, name)
            self.assertEqual(row["wire_tag"], field.tag, name)
            self.assertEqual(row["width"], field.kind, name)
        self.assertEqual(self.data["wire"]["vital_id"], UPDATE_ATTR_VITAL_ID)
        self.assertEqual(self.data["wire"]["attr_id"], ACTOR_ATTR_ID)

    def test_a_one_field_tampered_scenario_file_never_loads(self):
        for mutate in (
            lambda d: d.__setitem__("production_allowed", True),
            lambda d: d.__setitem__("test_only", False),
            lambda d: d.__setitem__("schema", 2),
            lambda d: d.__setitem__("hypothesis_id", "HYP-PF-019"),
            lambda d: d["entry"].__setitem__(
                "required_sequence", "selected_only",
            ),
            lambda d: d["dispatch"].__setitem__("spacing_seconds", 0.0),
            lambda d: d["dispatch"].__setitem__("one_shot", True),
            lambda d: d["dispatch"].__setitem__("cumulative", False),
            lambda d: d["dispatch"]["step_order"].__setitem__(0, "LEVEL"),
            lambda d: d["dispatch"]["step_fields"]["LEVEL"].__setitem__(
                "level", 8,
            ),
            lambda d: d["dispatch"]["action_labels"].__setitem__(
                0, "HYP_PF_020_STATS_PROG_NOPE",
            ),
            lambda d: d["wire"]["actor_attr_fields"]["experience"].__setitem__(
                "object_offset", 0xA8,
            ),
            lambda d: d["wire"]["basic_attr_fields"]["level"].__setitem__(
                "mask_bit", 4,
            ),
            lambda d: d["probe"]["per_step"]["ABILITY_PER"].__setitem__(
                "pc_sha256", "00" * 32,
            ),
            lambda d: d["probe"].__setitem__("cash", 1),
            lambda d: d["persisted_post_state"].__setitem__(
                "database_write", "characters",
            ),
            lambda d: d["nonclaims"].pop(),
        ):
            tampered_data = json.loads(json.dumps(self.data))
            mutate(tampered_data)
            self.assertNotEqual(tampered_data, self.data)
            tampered = Path(self.tmp.name) / "tampered.json"
            tampered.write_text(json.dumps(tampered_data), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_stats_progression_hypothesis_scenario(tampered)

    def test_a_scenario_object_outside_the_allowlist_is_refused(self):
        scenario = load_stats_progression_hypothesis_scenario(SCENARIO_PATH)
        for bad in (
            object(), None,
            replace(scenario, spacing_seconds=0.25),
            replace(scenario, step_order=STATS_PROGRESSION_STEP_ORDER[:2]),
            replace(scenario, hypothesis_id="HYP-PF-019"),
            replace(scenario, scenario_id="other"),
        ):
            with self.assertRaises(ValueError):
                require_stats_progression_hypothesis_scenario(bad)

    def test_a_missing_or_broken_file_is_refused(self):
        broken = Path(self.tmp.name) / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        for path in (broken, Path(self.tmp.name) / "absent.json"):
            with self.assertRaises(ValueError):
                load_stats_progression_hypothesis_scenario(path)


class ContainmentTests(_LegacyCase):
    """The lane is reachable only through its explicit opt-in scenario."""

    def test_exactly_two_foundation_modules_import_the_lane(self):
        module = "stats_progression_hypothesis"
        importers = sorted(
            path.name for path in SRC_ROOT.glob("*.py")
            if module in path.read_text(encoding="utf-8")
            and path.name != f"{module}.py"
        )
        self.assertEqual(importers, ["app.py", "runtime.py"])
        for name in ("connection.py", "scenario.py", "session.py", "store.py"):
            self.assertNotIn(
                module, (SRC_ROOT / name).read_text(encoding="utf-8"), name,
            )

    def test_every_runtime_mention_sits_behind_the_opt_in_gate(self):
        source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
        self.assertIn(
            "if stats_progression_hypothesis_scenario is not None:", source,
        )
        self.assertIn(
            "stats_progression_hypothesis_scenario is not None\n"
            "                and nested_id == CHAT_INPUT_VITAL_ID",
            source,
        )
        self.assertEqual(
            source.count("make_stats_progression_step_response"), 2,
        )
        self.assertEqual(
            source.count("make_stats_progression_step_response("), 1,
        )
        self.assertEqual(
            source.count("_dispatch_stats_progression_hypothesis"), 2,
        )

    def test_the_cli_flag_requires_an_explicit_database(self):
        source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn("--stats-progression-hypothesis-scenario", source)
        self.assertIn(
            "'--stats-progression-hypothesis-scenario requires an explicit "
            "existing --db'",
            source,
        )

    def test_the_frozen_module_knows_nothing_about_this_lane(self):
        legacy_source = LEGACY_PATH.read_text(encoding="utf-8")
        self.assertNotIn("stats_progression_hypothesis", legacy_source)
        self.assertNotIn("ability_str", legacy_source)
        self.assertNotIn("STATS_PROGRESSION", legacy_source)

    def test_the_lane_owns_no_progression_verb_encoder(self):
        # STATS-PROG-001 measured "5 progression verbs, 0 encoders" for both
        # v141 and src/.  This milestone moves the DELTA PIPE only, so that
        # statement must stay literally true after it lands.
        module_source = (
            SRC_ROOT / "stats_progression_hypothesis.py"
        ).read_text(encoding="utf-8")
        for verb in ("AbilityDepoly", "CLearnSkillVital",
                     "CLearnSkillResultVital", "CRevertSkilltVital",
                     "CSkillAttr"):
            self.assertNotIn(verb, module_source, verb)

    def test_the_action_labels_are_namespaced_to_this_hypothesis(self):
        self.assertTrue(
            STATS_PROGRESSION_ACTION_LABEL_PREFIX.startswith("HYP_PF_020_")
        )
        labels = {
            STATS_PROGRESSION_ACTION_LABEL_PREFIX + label
            for label in STATS_PROGRESSION_STEP_ORDER
        }
        self.assertEqual(len(labels), len(STATS_PROGRESSION_STEP_ORDER))


if __name__ == "__main__":
    unittest.main()
