"""HP-DEATH-002 (HYP-PF-022) -- the lethal encoder, offline.

HP-DEATH-001 settled the evidence half of `combat / hp_death_and_respawn`
statically: the client derives death entirely by itself, out of two values the
server projects.  ``IsDead`` at ``CNetActor``/``CMyActor`` vtable +0x40
(``0x454AC0``) requires the ``f32`` at ``BasicAttr +0x58`` to be greater than
the ``0.0f`` at ``0xF0989C`` and then returns ``u32[BasicAttr +0x44] == 0``.
Those are mask bits ``0x0080`` and ``0x0004`` of the block this server has been
emitting since NAME-002 -- and bit ``0x0080`` had never been emitted by
anything in this repository.

This file tests the encoder that emits it.  What it checks:

  * the death field is the report's field -- mask bit 0x0080, object offset
    +0x58, wire tag 0x2A, four bytes, gate pin 0x4657AE -- and the widened
    table's gate pins still ascend with the mask bits, which is the entire
    basis for "emission order == ascending mask bit";
  * the lane is LOCKED by default: without the unlock token the encoder cannot
    name the field, the decoder refuses a body that carries the bit, and the
    23-field progression table is untouched, so bit 0x0080 stays exactly as
    unimplemented for HYP-PF-020 as it was before;
  * the four sweep frames carry the pinned masks and values -- BASELINE is
    byte-identical to the projection a real client has accepted since NAME-002,
    TIMER_ARMED adds the bit WITHOUT the kill, HP_ZERO completes the predicate,
    and HP_RESTORED undoes it -- and every one of them re-decodes to what was asked;
  * every rejection family produces no bytes: a non-float timer, an int or bool
    timer, a non-finite timer, a zero or negative timer, a timer that is not
    exactly representable in 32 bits, a timer below the death-window gate, a
    timer sent without a current-HP field, a forged unlock token, and a step
    index outside the plan.

NOT proven here, and this is the load-bearing limit: that any client renders
death from these bytes.  That is GT-019, attended, not run.  Nothing in this
project has ever seen BasicAttr bit 0x0080 on a wire in either direction.
"""
from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_name,
)
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
# The BasicAttr change mask sits at a fixed place in every body this lane
# composes: u8tag DBAttribute mask (2) + qwordtag identity (9) + the u16 tag.
BASIC_MASK_OFFSET = 12


class HpDeathFieldTableTests(unittest.TestCase):
    def test_the_death_field_is_the_reports_field(self):
        field = sp.HP_DEATH_TIMER_FIELD
        self.assertEqual(field.name, "hp_death_timer")
        self.assertEqual(field.block, "basic")
        self.assertEqual(field.mask_bit, 0x0080)
        self.assertEqual(field.offset, 0x58)
        self.assertEqual(field.tag, 0x2A)
        self.assertEqual(field.kind, "f32")
        self.assertEqual(sp.FIELD_KIND_WIDTH["f32"], 4)
        self.assertEqual(sp.HP_DEATH_TIMER_GATE_PIN, 0x4657AE)

    def test_the_lethal_table_is_the_progression_table_plus_one_bit(self):
        self.assertEqual(
            set(sp.LETHAL_FIELDS),
            set(sp.PROGRESSION_FIELDS) | {"hp_death_timer"},
        )
        self.assertEqual(
            len(sp.LETHAL_BASIC_ATTR_FIELDS), len(sp.BASIC_ATTR_FIELDS) + 1,
        )

    def test_the_death_bit_never_enters_the_progression_table(self):
        self.assertNotIn("hp_death_timer", sp.PROGRESSION_FIELDS)
        self.assertNotIn(
            0x0080, {field.mask_bit for field in sp.BASIC_ATTR_FIELDS},
        )
        self.assertIn(0x0080, sp.NOT_IMPLEMENTED_BASIC_ATTR_BITS)

    def test_the_widened_gate_pins_still_ascend_with_the_mask_bits(self):
        pins = [
            sp.LETHAL_BASIC_ATTR_GATE_PINS[field.mask_bit]
            for field in sp.LETHAL_BASIC_ATTR_FIELDS
            if field.mask_bit in sp.LETHAL_BASIC_ATTR_GATE_PINS
        ]
        self.assertEqual(pins, sorted(pins))
        self.assertEqual(len(set(pins)), len(pins))

    def test_the_death_field_is_emitted_between_hp_max_and_scene_id(self):
        order = [field.name for field in sp.LETHAL_BASIC_ATTR_FIELDS]
        self.assertEqual(
            order.index("hp_death_timer") - 1, order.index("mp_max"),
        )
        self.assertEqual(
            order.index("hp_death_timer") + 1, order.index("scene_id"),
        )

    def test_the_static_pins_this_lane_carries_match_hp_death_001(self):
        # Documentation-grade constants; a drift here means the module and the
        # milestone report have parted company.
        self.assertEqual(sp.IS_DEAD_PLAYER_VA, 0x454AC0)
        self.assertEqual(sp.IS_DEAD_NPC_VA, 0x43BDA0)
        self.assertEqual(sp.ZERO_FLOAT_CONSTANT_VA, 0xF0989C)
        self.assertEqual(sp.MAIN_DEAD_GATE_VA, 0x44A540)
        self.assertEqual(sp.MY_ACTOR_UPDATE_VA, 0x44E4E0)
        self.assertEqual(sp.PROGRESSION_FIELDS["hp_current"].mask_bit, 0x0004)
        self.assertEqual(sp.PROGRESSION_FIELDS["hp_current"].offset, 0x44)


class HpDeathLockTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.actor = sp.HP_DEATH_PROBE_ACTOR
        self.unlock = sp.hp_death_lethal_unlock(
            sp.load_hp_death_hypothesis_scenario(SCENARIO_PATH)
        )

    def _encode(self, fields, lethal=None):
        return sp.encode_actor_attr(
            self.legacy, self.actor.identity_lo, self.actor.identity_hi,
            fields, lethal,
        )

    def test_without_the_token_the_field_name_does_not_exist(self):
        with self.assertRaises(ValueError) as caught:
            self._encode({"hp_current": 0, "hp_death_timer": 60.0})
        self.assertIn("unknown_field", str(caught.exception))

    def test_without_the_token_a_lethal_body_cannot_be_decoded(self):
        body = self._encode(
            {"hp_current": 0, "hp_death_timer": 60.0}, self.unlock,
        )
        with self.assertRaises(ValueError) as caught:
            sp.decode_actor_attr(body)
        self.assertIn("unimplemented_mask_bit", str(caught.exception))
        self.assertEqual(
            sp.decode_actor_attr(body, self.unlock)[2]["hp_death_timer"], 60.0,
        )

    def test_a_forged_token_does_not_unlock_the_lane(self):
        forged = sp.HpDeathLethalUnlock(
            sp.HP_DEATH_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
        )
        self.assertEqual(forged, sp._HP_DEATH_UNLOCK)  # equal by value
        for candidate in (forged, True, 1, "unlock", object()):
            with self.assertRaises(ValueError) as caught:
                self._encode(
                    {"hp_current": 0, "hp_death_timer": 60.0}, candidate,
                )
            self.assertIn("lethal_lane_locked", str(caught.exception))

    def test_the_token_only_comes_from_the_allowlisted_scenario(self):
        with self.assertRaises(ValueError):
            sp.hp_death_lethal_unlock(None)
        with self.assertRaises(ValueError):
            sp.hp_death_lethal_unlock(
                sp.HpDeathHypothesisScenario(
                    sp.HP_DEATH_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
                    sp.HP_DEATH_STEP_ORDER, 6.0, 60.0,
                )
            )

    def test_the_progression_baseline_is_byte_identical_with_and_without(self):
        fields = sp.stats_progression_baseline_fields(self.legacy, self.actor)
        self.assertEqual(self._encode(fields), self._encode(fields, self.unlock))
        self.assertEqual(
            self._encode(fields),
            make_actor_attr_with_name(
                self.legacy, self.actor.identity_lo, self.actor.identity_hi,
                self.actor.scene_id, self.actor.scene_sequence,
                self.actor.character_name,
            ),
        )


class HpDeathEncoderTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.actor = sp.HP_DEATH_PROBE_ACTOR
        self.unlock = sp.hp_death_lethal_unlock(
            sp.load_hp_death_hypothesis_scenario(SCENARIO_PATH)
        )

    def _encode(self, fields):
        return sp.encode_actor_attr(
            self.legacy, self.actor.identity_lo, self.actor.identity_hi,
            fields, self.unlock,
        )

    def test_the_timer_is_tag_0x2a_and_a_little_endian_float(self):
        body = self._encode({"hp_current": 0, "hp_death_timer": 60.0})
        self.assertIn(sp.HP_DEATH_TIMER_WIRE_BYTES, body)
        index = body.index(sp.HP_DEATH_TIMER_WIRE_BYTES)
        self.assertEqual(body[index], 0x2A)
        self.assertEqual(struct.unpack("<f", body[index + 1:index + 5])[0], 60.0)

    def test_setting_the_bit_sets_exactly_that_bit(self):
        without = self._encode({"hp_current": 0})
        with_timer = self._encode({"hp_current": 0, "hp_death_timer": 60.0})
        self.assertEqual(
            int.from_bytes(
                with_timer[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
            )
            ^ int.from_bytes(
                without[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
            ),
            0x0080,
        )
        self.assertEqual(len(with_timer) - len(without), 5)

    def test_every_composed_body_round_trips(self):
        for hp, timer in ((0, 60.0), (1, 100.0), (100, 19.5), (65535, 20.0)):
            body = self._encode({"hp_current": hp, "hp_death_timer": timer})
            self.assertEqual(
                sp.decode_actor_attr(body, self.unlock),
                (
                    self.actor.identity_lo, self.actor.identity_hi,
                    {"hp_current": hp, "hp_death_timer": timer},
                ),
            )

    # ----- fail closed -----------------------------------------------------

    def _refused(self, fields, reason):
        with self.assertRaises(ValueError) as caught:
            self._encode(fields)
        self.assertIn(reason, str(caught.exception))

    def test_an_integer_or_bool_timer_is_refused(self):
        for value in (60, 0, True, False):
            self._refused(
                {"hp_current": 0, "hp_death_timer": value},
                "death_timer_not_float",
            )

    def test_a_non_finite_timer_is_refused(self):
        for value in (float("inf"), float("-inf"), float("nan")):
            self._refused(
                {"hp_current": 0, "hp_death_timer": value},
                "death_timer_not_",
            )

    def test_a_non_positive_timer_is_refused(self):
        for value in (0.0, -0.0, -1.0, -60.0):
            self._refused(
                {"hp_current": 0, "hp_death_timer": value},
                "death_timer_not_positive",
            )

    def test_a_timer_below_the_death_window_gate_is_refused(self):
        # IsDead itself only needs "> 0.0f", but the local player's Main_Dead
        # window is behind `DURATION_DYING - 0.5 <= timer` at 0x44A572, and the
        # value compiled into the image is 20.  A timer the window would not
        # honour is a frame that produces an unobservable result, so it is
        # refused rather than sent.
        for value in (0.5, 1.0, 19.0, 19.25):
            self._refused(
                {"hp_current": 0, "hp_death_timer": value},
                "death_timer_below_the_death_window_gate",
            )
        self.assertEqual(sp.DURATION_DYING_IMAGE_DEFAULT, 20)
        self.assertEqual(sp.DURATION_DYING_WINDOW_MARGIN, 0.5)

    def test_a_timer_that_is_not_exactly_representable_is_refused(self):
        self._refused(
            {"hp_current": 0, "hp_death_timer": 20.123456789},
            "death_timer_not_exactly_representable",
        )

    def test_a_timer_without_a_current_hp_field_is_refused(self):
        self._refused(
            {"hp_max": 100, "hp_death_timer": 60.0},
            "death_timer_without_hp_current",
        )

    def test_no_refusal_ever_returns_bytes(self):
        for fields in (
            {"hp_current": 0, "hp_death_timer": 1},
            {"hp_current": 0, "hp_death_timer": -1.0},
            {"hp_death_timer": 60.0},
            {"hp_current": 0, "hp_death_timer": 60.0, "nope": 1},
        ):
            with self.assertRaises(ValueError):
                self._encode(fields)


class HpDeathSweepTests(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.actor = sp.HP_DEATH_PROBE_ACTOR
        self.scenario = sp.load_hp_death_hypothesis_scenario(SCENARIO_PATH)
        self.unlock = sp.hp_death_lethal_unlock(self.scenario)
        self.pinned = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))

    def test_the_plan_arms_then_kills_then_revives(self):
        self.assertEqual(
            sp.HP_DEATH_STEP_ORDER,
            ("BASELINE", "TIMER_ARMED", "HP_ZERO", "HP_RESTORED"),
        )
        self.assertEqual(sp.HP_DEATH_LETHAL_STEP_LABELS, ("HP_ZERO",))
        self.assertFalse(sp.hp_death_step_is_lethal(0))
        self.assertFalse(sp.hp_death_step_is_lethal(1))
        self.assertTrue(sp.hp_death_step_is_lethal(2))
        self.assertFalse(sp.hp_death_step_is_lethal(3))

    def test_the_armed_frame_carries_the_bit_but_does_not_kill(self):
        fields = sp.hp_death_step_fields(self.legacy, self.actor, 1)
        self.assertEqual(fields["hp_death_timer"], 60.0)
        self.assertEqual(fields["hp_current"], 100)

    def test_the_lethal_frame_carries_both_halves_of_the_predicate(self):
        fields = sp.hp_death_step_fields(self.legacy, self.actor, 2)
        self.assertEqual(fields["hp_current"], 0)
        self.assertGreater(fields["hp_death_timer"], 0.0)

    def test_the_sweep_ends_with_the_character_alive(self):
        fields = sp.hp_death_step_fields(
            self.legacy, self.actor, len(sp.HP_DEATH_STEP_ORDER) - 1,
        )
        self.assertEqual(fields["hp_current"], 100)
        self.assertEqual(fields["hp_max"], 100)

    def test_the_baseline_frame_is_the_untouched_proven_projection(self):
        pc, _frame = sp.make_hp_death_step_response(
            self.legacy, self.actor, 0, self.unlock,
        )
        body = sp.hp_death_attr_body(pc)
        self.assertEqual(
            body,
            make_actor_attr_with_name(
                self.legacy, self.actor.identity_lo, self.actor.identity_hi,
                self.actor.scene_id, self.actor.scene_sequence,
                self.actor.character_name,
            ),
        )
        self.assertEqual(
            hashlib.sha256(body).hexdigest().upper(),
            sp.STATS_PROBE_ATTR_BODY_SHA256["BASELINE"],
        )

    def test_every_frame_matches_its_module_and_scenario_pin(self):
        per_step = self.pinned["probe"]["per_step"]
        for index, label in enumerate(sp.HP_DEATH_STEP_ORDER):
            pc, frame = sp.make_hp_death_step_response(
                self.legacy, self.actor, index, self.unlock,
            )
            body = sp.hp_death_attr_body(pc)
            self.assertEqual(
                hashlib.sha256(body).hexdigest().upper(),
                sp.HP_DEATH_PROBE_ATTR_BODY_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                sp.HP_DEATH_PROBE_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                sp.HP_DEATH_PROBE_FRAME_SHA256[label], label,
            )
            self.assertEqual(len(body), sp.HP_DEATH_PROBE_ATTR_BODY_SIZE[label])
            self.assertEqual(len(pc), sp.HP_DEATH_PROBE_PC_SIZE[label])
            self.assertEqual(len(frame), sp.HP_DEATH_PROBE_FRAME_SIZE[label])
            self.assertEqual(
                per_step[label]["attr_body_sha256"],
                sp.HP_DEATH_PROBE_ATTR_BODY_SHA256[label],
            )
            self.assertEqual(
                per_step[label]["pc_sha256"], sp.HP_DEATH_PROBE_PC_SHA256[label],
            )
            self.assertEqual(
                per_step[label]["frame_sha256"],
                sp.HP_DEATH_PROBE_FRAME_SHA256[label],
            )
            self.assertEqual(
                per_step[label]["lethal"],
                label in sp.HP_DEATH_LETHAL_STEP_LABELS,
            )

    def test_every_frame_carries_the_pinned_mask_and_the_right_vital(self):
        for index, label in enumerate(sp.HP_DEATH_STEP_ORDER):
            pc, _frame = sp.make_hp_death_step_response(
                self.legacy, self.actor, index, self.unlock,
            )
            body = sp.hp_death_attr_body(pc)
            self.assertEqual(
                int.from_bytes(
                    body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
                ),
                sp.HP_DEATH_PROBE_BASIC_MASK[label], label,
            )
            self.assertEqual(
                pc[16:18], sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"),
            )
            self.assertEqual(
                pc[sp.STATS_PC_ATTR_BODY_OFFSET:
                   sp.STATS_PC_ATTR_BODY_OFFSET + len(body)], body,
            )

    def test_every_frame_redecodes_to_its_declared_field_set(self):
        for index, label in enumerate(sp.HP_DEATH_STEP_ORDER):
            expected = sp.hp_death_step_fields(self.legacy, self.actor, index)
            pc, _frame = sp.make_hp_death_step_response(
                self.legacy, self.actor, index, self.unlock,
            )
            self.assertEqual(
                sp.decode_actor_attr(sp.hp_death_attr_body(pc), self.unlock),
                (self.actor.identity_lo, self.actor.identity_hi, expected),
                label,
            )

    def test_a_step_index_outside_the_plan_is_refused(self):
        for index in (-1, len(sp.HP_DEATH_STEP_ORDER), True, 1.0, "0"):
            with self.assertRaises(ValueError):
                sp.hp_death_step_fields(self.legacy, self.actor, index)

    def test_composing_without_the_token_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            sp.make_hp_death_step_response(self.legacy, self.actor, 2, None)
        self.assertIn("lethal_lane_locked", str(caught.exception))

    def test_the_scenario_stays_test_only_lethal_and_write_free(self):
        self.assertIs(self.pinned["test_only"], True)
        self.assertIs(self.pinned["production_allowed"], False)
        self.assertIs(self.pinned["lethal"], True)
        self.assertEqual(
            self.pinned["persisted_post_state"]["database_write"], "none",
        )
        self.assertEqual(self.pinned["hypothesis_id"], "HYP-PF-022")

    def test_the_scenario_records_the_transport_it_cannot_reach(self):
        # The one correction this lane makes to HP-DEATH-001's open debt B1:
        # UpdateAttrVital does NOT reach 0x4446F0, so it cannot reach the
        # dead-state sync 0x4437C0.  The scenario says so rather than letting a
        # later reader assume the animation is coming.
        chain = self.pinned["wire"]["apply_chain"]
        self.assertIs(chain["reaches_dead_state_sync"], False)
        self.assertIs(chain["copy_is_mask_gated"], False)
        self.assertEqual(chain["dead_state_sync"], 0x4437C0)
        self.assertEqual(chain["actor_attr_copy"], 0x464F30)
        self.assertEqual(chain["basic_attr_copy"], 0x464B40)

    def test_a_scenario_outside_the_exact_allowlist_is_refused(self):
        import tempfile

        broken = dict(self.pinned)
        broken["production_allowed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ValueError):
                sp.load_hp_death_hypothesis_scenario(path)
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(ValueError):
                sp.load_hp_death_hypothesis_scenario(path)

    def test_a_non_probe_actor_still_composes_and_redecodes(self):
        other = replace(
            self.actor, identity_lo=0x10020003, scene_id=5,
            character_name="dieth",
        )
        pc, _frame = sp.make_hp_death_step_response(
            self.legacy, other, 2, self.unlock,
        )
        _lo, _hi, fields = sp.decode_actor_attr(
            sp.hp_death_attr_body(pc), self.unlock,
        )
        self.assertEqual(fields["hp_current"], 0)
        self.assertEqual(fields["hp_death_timer"], 60.0)
        self.assertEqual(fields["character_name"], "dieth")


class HpDeathContainmentTests(unittest.TestCase):
    def test_the_lane_names_none_of_the_relive_verbs(self):
        source = (
            ROOT / "src" / "pirateforce_foundation"
            / "stats_progression_hypothesis.py"
        ).read_text(encoding="utf-8")
        for verb in ("make_relive", "encode_relive", "ReliveMarker"):
            self.assertNotIn(verb, source)

    def test_the_module_carries_exactly_one_ledger_marker_per_entry(self):
        source = (
            ROOT / "src" / "pirateforce_foundation"
            / "stats_progression_hypothesis.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-020 active"), 1,
        )
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-022 active"), 1,
        )

    def test_the_lane_opens_no_database_path(self):
        source = (
            ROOT / "src" / "pirateforce_foundation"
            / "stats_progression_hypothesis.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "sqlite3", "SQLiteStore", "self.store", "commit(", "INSERT INTO",
            "UPDATE ", "import store", "from .store",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
