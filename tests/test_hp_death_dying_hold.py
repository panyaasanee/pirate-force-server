"""DYING-HOLD-001 (HYP-PF-022, second profile) -- the 20-second dying hold.

``tests/test_hp_death_encoder.py`` proves the ``death_sweep`` profile: arm the
death timer, zero current HP, then put the HP value back, so an attended tester
is never left staring at a dead character.  That profile is a DIAGNOSTIC, and
its 60.0 s timer was a margin taken when nobody knew what the client's
``DURATION_DYING`` actually was.

Round 83's static pass answered that question at the byte level: the value
compiled into the image is 20 (the int global ``0x102249C``, bound by name at
``0x483476``, with a single reader at ``0x44A572`` that opens L"Main_Dead"
``0xF0D738`` iff ``DURATION_DYING - 0.5 <= timer``).  Which makes a second
question askable for the first time, and it is not one the diagnostic can ask:

    WHAT HAPPENS WHEN THE COUNTDOWN RUNS OUT?

That is what the ``dying_hold`` profile exists for, and it is the whole reason
it has no restoring step.  Three things an attended tester is asked to look at,
in this order:

  1. does the countdown on screen actually move?
  2. when it reaches zero, does the client cross from "dying" (``0x454AC0``:
     HP == 0 and timer > 0) into "timer elapsed" (``0x454A70``: HP == 0 and
     timer <= 0)?
  3. and does the SECOND window -- L"Common_Death" at ``0xF0D860``, opened out
     of ``CMyActor``'s own update, NOT L"Main_Dead" -- appear?

What this file proves, all of it offline and none of it about a screen:

  * the ``death_sweep`` profile did not move one byte across the refactor: same
    step order, same 60.0 s timer, same twelve sha256 pins;
  * ``dying_hold`` is the three-step plan it claims to be, at 20.0 s, with one
    lethal step, ending on the kill;
  * the two profiles' BASELINE frames are byte-identical, and their TIMER_ARMED
    frames differ only inside the four f32 bytes of the timer value;
  * the step-plan validator RAISES on four separately broken profiles -- a
    verifier that cannot fail is not a verifier;
  * the lane is still fail-closed: no unlock token, no bytes;
  * and the scenario file on disk agrees with the encoder on every hash and
    every size, read back off the disk rather than trusted.

NOT proven here, and this is the load-bearing limit: that any client has ever
rendered any of it.  No client in this project has been shown one byte of this
profile, and L"Common_Death" has never been observed by this project at all.
"""
from __future__ import annotations

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
SWEEP_SCENARIO_PATH = (
    ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
)
HOLD_SCENARIO_PATH = ROOT / "scenarios" / "hp_death_hypothesis_dying_hold.json"
BASIC_MASK_OFFSET = 12

# The death_sweep pins, transcribed here ONCE and independently of the module,
# so that "the refactor did not move a byte" is checked against a written-down
# expectation rather than against the module checking itself.
FROZEN_DEATH_SWEEP_ATTR_BODY_SHA256 = {
    "BASELINE":
        "479ED77DFA554F89AAB02E884608EC53BAEC9E213F85548AF9CCD291BCC896C4",
    "TIMER_ARMED":
        "903F2D45EAB009DD2D1AD9C14A00D0027F428BB98076560E5C5F22534B53A8FA",
    "HP_ZERO":
        "C718DFC077AEC9C93432F26C81A6AA08D2BD8616F5C4424D1DC2DAC668576469",
    "HP_RESTORED":
        "903F2D45EAB009DD2D1AD9C14A00D0027F428BB98076560E5C5F22534B53A8FA",
}
FROZEN_DEATH_SWEEP_PC_SHA256 = {
    "BASELINE":
        "DB3CE0B5D14196181EF9EA26A0D435E0489212634334CB562F840E368B5F0049",
    "TIMER_ARMED":
        "B7BE99B81FDBBC88D08599C6504328B99E55F40B3877856FC6D7BA0F7047E97F",
    "HP_ZERO":
        "A1990A937B4A1A8FFAB2D1D8F29004489C260A7829051F14CADDB0D619A16717",
    "HP_RESTORED":
        "B7BE99B81FDBBC88D08599C6504328B99E55F40B3877856FC6D7BA0F7047E97F",
}
FROZEN_DEATH_SWEEP_FRAME_SHA256 = {
    "BASELINE":
        "04E2B40152B633A48C84713B1C24A2910B7AB84E178E268094C0D10B179D9FBC",
    "TIMER_ARMED":
        "FF43A6FC590A88CCC9B548AE694FA9EDAFE25051FB3AB9E61041BA4142276B04",
    "HP_ZERO":
        "F6DB8ACA8C80DBFCED2FBF12BC8532C0A0865818D88D7AF4B4CAD06931C58A35",
    "HP_RESTORED":
        "FF43A6FC590A88CCC9B548AE694FA9EDAFE25051FB3AB9E61041BA4142276B04",
}


def _armed_body(bodies):
    return bodies["TIMER_ARMED"]


class _Base(unittest.TestCase):
    def setUp(self):
        self.legacy = load_legacy(LEGACY_PATH)
        self.actor = sp.HP_DEATH_PROBE_ACTOR
        self.sweep_scenario = sp.load_hp_death_hypothesis_scenario(
            SWEEP_SCENARIO_PATH,
        )
        self.hold_scenario = sp.load_hp_death_hypothesis_scenario(
            HOLD_SCENARIO_PATH,
        )
        self.unlock = sp.hp_death_lethal_unlock(self.sweep_scenario)

    def _bodies(self, profile):
        out = {}
        for index, label in enumerate(profile.step_order):
            pc, frame = sp.make_hp_death_step_response(
                self.legacy, self.actor, index, self.unlock, profile,
            )
            out[label] = (sp.hp_death_attr_body(pc), pc, frame)
        return out


class DeathSweepDidNotMoveTests(_Base):
    """Regression: the refactor must not have shifted the original profile."""

    def test_the_module_symbols_still_name_the_death_sweep_profile(self):
        profile = sp.HP_DEATH_PROFILE_DEATH_SWEEP
        self.assertEqual(sp.HP_DEATH_STEP_ORDER, profile.step_order)
        self.assertEqual(sp.HP_DEATH_STEP_FIELDS, profile.step_fields)
        self.assertEqual(sp.HP_DEATH_LETHAL_STEP_LABELS,
                         profile.lethal_step_labels)
        self.assertEqual(sp.HP_DEATH_TIMER_SECONDS, profile.timer_seconds)
        self.assertEqual(sp.HP_DEATH_SCENARIO_ID, profile.scenario_id)
        self.assertEqual(sp.HP_DEATH_SPACING_SECONDS, profile.spacing_seconds)
        self.assertEqual(sp.HP_DEATH_FIRST_DELAY_SECONDS,
                         profile.first_delay_seconds)
        self.assertEqual(sp.HP_DEATH_ACTION_LABEL_PREFIX,
                         profile.action_label_prefix)
        self.assertIs(profile.ends_dead, False)

    def test_the_death_sweep_plan_and_timer_are_unchanged(self):
        self.assertEqual(
            sp.HP_DEATH_STEP_ORDER,
            ("BASELINE", "TIMER_ARMED", "HP_ZERO", "HP_RESTORED"),
        )
        self.assertEqual(sp.HP_DEATH_TIMER_SECONDS, 60.0)
        self.assertEqual(sp.HP_DEATH_LETHAL_STEP_LABELS, ("HP_ZERO",))
        self.assertEqual(sp.HP_DEATH_TIMER_WIRE_BYTES,
                         bytes.fromhex("2a00007042"))
        self.assertEqual(self.sweep_scenario.death_timer_seconds, 60.0)
        self.assertIs(self.sweep_scenario.ends_dead, False)

    def test_every_death_sweep_hash_is_exactly_what_it_always_was(self):
        self.assertEqual(
            sp.HP_DEATH_PROBE_ATTR_BODY_SHA256,
            FROZEN_DEATH_SWEEP_ATTR_BODY_SHA256,
        )
        self.assertEqual(
            sp.HP_DEATH_PROBE_PC_SHA256, FROZEN_DEATH_SWEEP_PC_SHA256,
        )
        self.assertEqual(
            sp.HP_DEATH_PROBE_FRAME_SHA256, FROZEN_DEATH_SWEEP_FRAME_SHA256,
        )

    def test_the_death_sweep_bytes_still_hash_to_those_pins(self):
        for label, (body, pc, frame) in self._bodies(
            sp.HP_DEATH_PROFILE_DEATH_SWEEP
        ).items():
            self.assertEqual(
                hashlib.sha256(body).hexdigest().upper(),
                FROZEN_DEATH_SWEEP_ATTR_BODY_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(),
                FROZEN_DEATH_SWEEP_PC_SHA256[label], label,
            )
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(),
                FROZEN_DEATH_SWEEP_FRAME_SHA256[label], label,
            )

    def test_the_default_profile_is_still_death_sweep(self):
        # Every pre-existing caller passes no profile at all.
        without = sp.hp_death_step_fields(self.legacy, self.actor, 1)
        withit = sp.hp_death_step_fields(
            self.legacy, self.actor, 1, sp.HP_DEATH_PROFILE_DEATH_SWEEP,
        )
        self.assertEqual(without, withit)
        self.assertEqual(without["hp_death_timer"], 60.0)


class DyingHoldPlanTests(_Base):
    def test_the_plan_is_three_steps_that_end_on_the_kill(self):
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        self.assertEqual(
            profile.step_order, ("BASELINE", "TIMER_ARMED", "HP_ZERO"),
        )
        self.assertEqual(profile.step_order[-1], "HP_ZERO")
        self.assertNotIn("HP_RESTORED", profile.step_order)
        self.assertIs(profile.ends_dead, True)
        self.assertEqual(profile.lethal_step_labels, ("HP_ZERO",))

    def test_the_timer_is_the_value_compiled_into_the_client_image(self):
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        self.assertEqual(profile.timer_seconds, 20.0)
        self.assertEqual(sp.HP_DEATH_DYING_HOLD_TIMER_SECONDS, 20.0)
        self.assertEqual(
            profile.timer_seconds, float(sp.DURATION_DYING_IMAGE_DEFAULT),
        )
        # 20.0 >= 19.5: it clears the window gate exactly, with nothing spare.
        self.assertGreaterEqual(
            profile.timer_seconds,
            sp.DURATION_DYING_IMAGE_DEFAULT - sp.DURATION_DYING_WINDOW_MARGIN,
        )
        self.assertEqual(sp.DURATION_DYING_GLOBAL_VA, 0x102249C)
        self.assertEqual(sp.COMMON_DEATH_LITERAL_VA, 0xF0D860)
        self.assertEqual(sp.IS_DYING_PLAYER_VA, 0x454AC0)
        self.assertEqual(sp.IS_DEAD_ELAPSED_PLAYER_VA, 0x454A70)

    def test_exactly_one_step_is_lethal_and_it_is_the_last_one(self):
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        lethal = [
            label for index, label in enumerate(profile.step_order)
            if sp.hp_death_step_is_lethal(index, profile)
        ]
        self.assertEqual(lethal, ["HP_ZERO"])
        self.assertEqual(lethal, list(profile.lethal_step_labels))
        self.assertEqual(profile.step_order[-1], lethal[-1])

    def test_the_last_frame_leaves_the_character_dead_on_the_wire(self):
        bodies = self._bodies(sp.HP_DEATH_PROFILE_DYING_HOLD)
        body = bodies["HP_ZERO"][0]
        _lo, _hi, fields = sp.decode_actor_attr(body, self.unlock)
        self.assertEqual(fields["hp_current"], 0)
        self.assertEqual(fields["hp_death_timer"], 20.0)

    def test_the_armed_frame_carries_the_bit_without_the_kill(self):
        fields = sp.hp_death_step_fields(
            self.legacy, self.actor, 1, sp.HP_DEATH_PROFILE_DYING_HOLD,
        )
        self.assertEqual(fields["hp_death_timer"], 20.0)
        self.assertEqual(fields["hp_current"], 100)

    def test_a_step_index_outside_the_shorter_plan_is_refused(self):
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        for index in (-1, 3, 4, True, 1.0, "0"):
            with self.assertRaises(ValueError):
                sp.hp_death_step_fields(
                    self.legacy, self.actor, index, profile,
                )

    def test_an_unregistered_profile_object_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            sp.hp_death_step_fields(self.legacy, self.actor, 0, object())
        self.assertIn("unknown_step_profile", str(caught.exception))


class TwoProfilesDifferOnlyByTheTimerTests(_Base):
    def test_the_two_baselines_are_byte_identical(self):
        sweep = self._bodies(sp.HP_DEATH_PROFILE_DEATH_SWEEP)
        hold = self._bodies(sp.HP_DEATH_PROFILE_DYING_HOLD)
        self.assertEqual(sweep["BASELINE"][0], hold["BASELINE"][0])
        self.assertEqual(sweep["BASELINE"][1], hold["BASELINE"][1])
        self.assertEqual(sweep["BASELINE"][2], hold["BASELINE"][2])
        # ... and both are still the projection a real client has accepted
        # since NAME-002, which is what makes the DIFFERENCE the only thing
        # under test in either profile.
        self.assertEqual(
            hold["BASELINE"][0],
            make_actor_attr_with_name(
                self.legacy, self.actor.identity_lo, self.actor.identity_hi,
                self.actor.scene_id, self.actor.scene_sequence,
                self.actor.character_name,
            ),
        )

    def test_the_two_armed_frames_differ_only_inside_the_f32(self):
        sweep = _armed_body(self._bodies(sp.HP_DEATH_PROFILE_DEATH_SWEEP))[0]
        hold = _armed_body(self._bodies(sp.HP_DEATH_PROFILE_DYING_HOLD))[0]
        self.assertNotEqual(sweep, hold)
        self.assertEqual(len(sweep), len(hold))
        at = sweep.index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 1
        differing = [
            index for index, (left, right) in enumerate(zip(sweep, hold))
            if left != right
        ]
        self.assertTrue(differing)
        # 60.0f is 00 00 70 42 and 20.0f is 00 00 A0 41, so two of the four
        # value bytes coincide.  The load-bearing claim is that NOTHING outside
        # the f32 moved: not the tag, not the mask, not one other field, not
        # the envelope.
        self.assertLessEqual(set(differing), set(range(at, at + 4)))
        self.assertEqual(sweep[at - 1], sp.HP_DEATH_TIMER_TAG)
        self.assertEqual(hold[at - 1], sp.HP_DEATH_TIMER_TAG)
        self.assertEqual(struct.unpack("<f", sweep[at:at + 4])[0], 60.0)
        self.assertEqual(struct.unpack("<f", hold[at:at + 4])[0], 20.0)
        self.assertEqual(
            hold[at - 1:at + 4], sp.HP_DEATH_DYING_HOLD_TIMER_WIRE_BYTES,
        )

    def test_the_two_armed_frames_carry_the_same_basic_mask(self):
        sweep = _armed_body(self._bodies(sp.HP_DEATH_PROFILE_DEATH_SWEEP))[0]
        hold = _armed_body(self._bodies(sp.HP_DEATH_PROFILE_DYING_HOLD))[0]
        for body in (sweep, hold):
            self.assertEqual(
                int.from_bytes(
                    body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
                ),
                0x038C,
            )


class StepPlanValidatorTrapTests(_Base):
    """A verifier that cannot fail is not a verifier.

    Each mutant below breaks exactly one clause of the profile contract, and
    every one of them must be REFUSED -- both by the validator directly and by
    the composer, which will not compose against an unregistered profile at all.
    """

    ARMED_20 = {sp.HP_DEATH_TIMER_NAME: 20.0}
    ARMED_19 = {sp.HP_DEATH_TIMER_NAME: 19.0}
    KILL = {"hp_current": 0}
    RESTORE = {"hp_current": 100}

    def _mutant(self, name, steps, ends_dead, timer,
                lethal=("HP_ZERO",)):
        base = sp.HP_DEATH_PROFILE_DYING_HOLD
        return sp.HpDeathStepProfile(
            name, base.scenario_id, timer, steps, lethal, ends_dead,
            base.spacing_seconds, base.first_delay_seconds,
            base.action_label_prefix, base.response_policy,
            base.capabilities, base.nonclaims,
            base.probe_attr_body_sha256, base.probe_pc_sha256,
            base.probe_frame_sha256, base.probe_attr_body_size,
            base.probe_pc_size, base.probe_frame_size,
            base.probe_basic_mask, base.timer_wire_bytes,
        )

    def _refused(self, mutant):
        with self.assertRaises(RuntimeError):
            sp._require_hp_death_step_plan(mutant)
        with self.assertRaises(ValueError) as caught:
            sp.make_hp_death_step_response(
                self.legacy, self.actor, 1, self.unlock, mutant,
            )
        self.assertIn("unknown_step_profile", str(caught.exception))

    def test_trap_a_an_ends_dead_plan_that_still_restores_hp(self):
        self._refused(self._mutant("trap_a", (
            ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
            ("HP_ZERO", self.KILL), ("HP_RESTORED", self.RESTORE),
        ), True, 20.0))

    def test_trap_b_an_ends_dead_plan_below_the_window_gate(self):
        self._refused(self._mutant("trap_b", (
            ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_19),
            ("HP_ZERO", self.KILL),
        ), True, 19.0))

    def test_trap_c_an_ends_alive_plan_that_stops_on_the_kill(self):
        self._refused(self._mutant("trap_c", (
            ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
            ("HP_ZERO", self.KILL),
        ), False, 20.0))

    def test_trap_d_a_plan_that_kills_before_it_arms(self):
        self._refused(self._mutant("trap_d", (
            ("BASELINE", {}), ("HP_ZERO", self.KILL),
            ("TIMER_ARMED", self.ARMED_20), ("HP_RESTORED", self.RESTORE),
        ), False, 20.0))

    def test_further_traps_the_contract_also_has_to_catch(self):
        for label, mutant in (
            ("no baseline", self._mutant("trap_e", (
                ("TIMER_ARMED", self.ARMED_20), ("HP_ZERO", self.KILL),
            ), True, 20.0)),
            ("a baseline that already carries a field", self._mutant(
                "trap_f", (
                    ("BASELINE", self.ARMED_20),
                    ("TIMER_ARMED", self.ARMED_20), ("HP_ZERO", self.KILL),
                ), True, 20.0)),
            ("a step that changes two fields at once", self._mutant(
                "trap_g", (
                    ("BASELINE", {}),
                    ("TIMER_ARMED", dict(self.ARMED_20, hp_max=1)),
                    ("HP_ZERO", self.KILL),
                ), True, 20.0)),
            ("a kill step that does not zero hp", self._mutant("trap_h", (
                ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
                ("HP_ZERO", {"hp_current": 1}),
            ), True, 20.0)),
            ("more than one lethal label", self._mutant("trap_i", (
                ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
                ("HP_ZERO", self.KILL),
            ), True, 20.0, ("HP_ZERO", "TIMER_ARMED"))),
            ("an armed step that disagrees with the declared timer",
             self._mutant("trap_j", (
                 ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_19),
                 ("HP_ZERO", self.KILL),
             ), True, 20.0)),
            ("a step naming a field the lethal table does not know",
             self._mutant("trap_k", (
                 ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
                 ("HP_ZERO", self.KILL), ("HP_RESTORED", {"nope": 1}),
             ), False, 20.0)),
            ("an ends-alive plan whose restore leaves hp at zero",
             self._mutant("trap_l", (
                 ("BASELINE", {}), ("TIMER_ARMED", self.ARMED_20),
                 ("HP_ZERO", self.KILL), ("HP_RESTORED", {"hp_current": 0}),
             ), False, 20.0)),
        ):
            with self.subTest(trap=label):
                with self.assertRaises(RuntimeError):
                    sp._require_hp_death_step_plan(mutant)

    def test_the_two_shipped_profiles_pass_the_same_validator(self):
        for profile in (
            sp.HP_DEATH_PROFILE_DEATH_SWEEP, sp.HP_DEATH_PROFILE_DYING_HOLD,
        ):
            self.assertIsNone(sp._require_hp_death_step_plan(profile))
        self.assertIsNone(sp._require_hp_death_step_plan())

    def test_a_non_profile_is_not_a_step_plan(self):
        for candidate in (object(), "dying_hold", 1, True, {}):
            with self.assertRaises(RuntimeError):
                sp._require_hp_death_step_plan(candidate)


class DyingHoldFailsClosedTests(_Base):
    def test_without_the_token_the_profile_composes_nothing(self):
        for candidate in (
            None, object(), True, 1, "unlock",
            sp.HpDeathLethalUnlock(
                sp.HP_DEATH_DYING_HOLD_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
            ),
            sp.HpDeathLethalUnlock(
                sp.HP_DEATH_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
            ),
        ):
            with self.assertRaises(ValueError) as caught:
                sp.make_hp_death_step_response(
                    self.legacy, self.actor, 2, candidate,
                    sp.HP_DEATH_PROFILE_DYING_HOLD,
                )
            self.assertIn("lethal_lane_locked", str(caught.exception))

    def test_the_second_profile_did_not_add_a_second_key(self):
        self.assertIs(
            sp.hp_death_lethal_unlock(self.hold_scenario),
            sp.hp_death_lethal_unlock(self.sweep_scenario),
        )
        self.assertIs(
            sp.hp_death_lethal_unlock(self.hold_scenario), sp._HP_DEATH_UNLOCK,
        )

    def test_the_scenario_is_test_only_and_never_production(self):
        raw = json.loads(HOLD_SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertIs(raw["test_only"], True)
        self.assertIs(raw["production_allowed"], False)
        self.assertIs(raw["lethal"], True)
        self.assertEqual(raw["hypothesis_id"], "HYP-PF-022")
        self.assertEqual(raw["persisted_post_state"]["database_write"], "none")
        self.assertEqual(raw["dispatch"]["socket_action"], "none")

    def test_the_scenario_states_the_four_things_nobody_may_claim(self):
        raw = json.loads(HOLD_SCENARIO_PATH.read_text(encoding="utf-8"))
        for nonclaim in (
            "no_client_has_ever_been_shown_one_byte_of_this_profile",
            "the_common_death_window_has_never_been_observed_by_this_project",
            "no_persistence_hp_has_no_write_path_and_this_lane_opens_none",
            "not_a_rule_of_the_original_server_which_this_project_cannot_read",
        ):
            self.assertIn(nonclaim, raw["nonclaims"])

    def test_a_scenario_outside_the_exact_allowlist_is_refused(self):
        import tempfile

        raw = json.loads(HOLD_SCENARIO_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for mutation in (
                {"production_allowed": True},
                {"id": "hp_death_hypothesis_something_else"},
                {"lethal": False},
            ):
                broken = dict(raw)
                broken.update(mutation)
                path.write_text(json.dumps(broken), encoding="utf-8")
                with self.assertRaises(ValueError):
                    sp.load_hp_death_hypothesis_scenario(path)
            # A restoring step smuggled into the dispatch block is also outside
            # the allowlist: the file is compared to the profile, exactly.
            broken = json.loads(json.dumps(raw))
            broken["dispatch"]["step_order"].append("HP_RESTORED")
            path.write_text(json.dumps(broken), encoding="utf-8")
            with self.assertRaises(ValueError):
                sp.load_hp_death_hypothesis_scenario(path)

    def test_the_death_sweep_file_still_loads_to_its_own_profile(self):
        self.assertIs(
            sp.hp_death_profile_for_scenario(self.sweep_scenario),
            sp.HP_DEATH_PROFILE_DEATH_SWEEP,
        )
        self.assertIs(
            sp.hp_death_profile_for_scenario(self.hold_scenario),
            sp.HP_DEATH_PROFILE_DYING_HOLD,
        )


class ScenarioFileMatchesTheEncoderTests(_Base):
    """The file on disk is compared to bytes, not to the module's own opinion."""

    def test_every_hash_and_size_in_the_file_is_what_the_encoder_produced(self):
        raw = json.loads(HOLD_SCENARIO_PATH.read_text(encoding="utf-8"))
        per_step = raw["probe"]["per_step"]
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        self.assertEqual(sorted(per_step), sorted(profile.step_order))
        for index, label in enumerate(profile.step_order):
            pc, frame = sp.make_hp_death_step_response(
                self.legacy, self.actor, index, self.unlock, profile,
            )
            body = sp.hp_death_attr_body(pc)
            with self.subTest(step=label):
                self.assertEqual(
                    per_step[label]["attr_body_sha256"],
                    hashlib.sha256(body).hexdigest().upper(),
                )
                self.assertEqual(
                    per_step[label]["pc_sha256"],
                    hashlib.sha256(pc).hexdigest().upper(),
                )
                self.assertEqual(
                    per_step[label]["frame_sha256"],
                    hashlib.sha256(frame).hexdigest().upper(),
                )
                self.assertEqual(per_step[label]["attr_body_size"], len(body))
                self.assertEqual(per_step[label]["pc_size"], len(pc))
                self.assertEqual(per_step[label]["frame_size"], len(frame))
                self.assertEqual(
                    per_step[label]["lethal"],
                    label in profile.lethal_step_labels,
                )

    def test_the_file_agrees_with_the_probe_and_the_plan(self):
        raw = json.loads(HOLD_SCENARIO_PATH.read_text(encoding="utf-8"))
        profile = sp.HP_DEATH_PROFILE_DYING_HOLD
        self.assertEqual(raw["id"], "hp_death_hypothesis_dying_hold")
        self.assertEqual(raw["dispatch"]["step_order"],
                         list(profile.step_order))
        self.assertEqual(raw["dispatch"]["frames_per_accepted_request"], 3)
        self.assertEqual(raw["dispatch"]["lethal_steps"], ["HP_ZERO"])
        self.assertNotIn("HP_RESTORED", raw["dispatch"]["step_fields"])
        self.assertNotIn("HP_RESTORED", raw["dispatch"]["step_order"])
        self.assertNotIn(
            "HYP_PF_022_DYING_HOLD_HP_RESTORED", raw["dispatch"]["action_labels"],
        )
        self.assertEqual(
            raw["wire"]["death_field"]["value_seconds"], 20.0,
        )
        self.assertEqual(
            raw["wire"]["death_window_gate"]["duration_dying_image_default"],
            20,
        )
        self.assertEqual(
            raw["wire"]["death_window_gate"]["duration_dying_global"],
            0x102249C,
        )
        self.assertEqual(raw["probe"]["identity_lo"], sp.STATS_PROBE_IDENTITY_LO)
        self.assertEqual(raw["probe"]["character_name"], "test01")

    def test_the_death_sweep_file_on_disk_was_not_touched(self):
        raw = json.loads(SWEEP_SCENARIO_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            raw["dispatch"]["step_order"],
            ["BASELINE", "TIMER_ARMED", "HP_ZERO", "HP_RESTORED"],
        )
        self.assertEqual(raw["wire"]["death_field"]["value_seconds"], 60.0)
        for label, expected in FROZEN_DEATH_SWEEP_PC_SHA256.items():
            self.assertEqual(
                raw["probe"]["per_step"][label]["pc_sha256"], expected, label,
            )


if __name__ == "__main__":
    unittest.main()
