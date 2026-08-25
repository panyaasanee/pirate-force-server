"""HOSTILE-HP-LINK-001 (HYP-PF-038) -- a REAL hostile's bar, proven offline.

WHAT THIS FILE PROVES
---------------------
That the lane composes ONE seven-frame ``GSCN_RunTimeProtocolRes`` (id 0x6E9D
version 4) sweep that alternates the two client-proven carriers against the
frozen Port Royal placement 30 identity ``0x201F`` ("Tornado Eagle"), that the
bar it moves starts at the CLIENT's own 3857 baseline, that the target is
placed PLAYER-RELATIVE rather than at the frozen world row, and that the sweep
ENDS ALIVE -- no floor balance, no death timer, no dying latch anywhere.

WHY EACH OF THOSE IS A TEST RATHER THAN A COMMENT
-------------------------------------------------
* the world row for placement 30 is roughly twelve thousand units from the
  player spawn, so a lane that shipped it would put a dot on a minimap and
  nothing on a screen -- the exact outcome an attended round already measured
  on a neighbouring lane.  Several tests below exist only to keep that from
  coming back.
* the death half belongs to GT-036 and a later version of this slot.  One
  ticket, one claim: the guards that refuse it are tested from both sides.

WHOSE ARITHMETIC THIS IS
------------------------
**Ours.**  The original server is closed, was never published and cannot be
recovered.  No capture in any corpus shows a target's hit points moving in
response to damage, and round 83 proved the client computes nothing and never
subtracts -- which is why the server has to say both halves itself.

NOT proven here, and these are the load-bearing limits: whether the client
renders 2893 on a real hostile's bar is UNDECIDABLE from static analysis and
is the queued attended test, and nobody has ever confirmed with their own eyes
that a model at this distance is inside the client's draw distance.

DISCIPLINE.  Every database below is a fresh ``tempfile`` one that is deleted
on exit.  The repository's canonical database is never opened -- it is only
``stat``-ed, once at import and once at the end.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import hostile_hp_link_hypothesis as hh  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
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


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "hostile_hp_link_hypothesis_p30_sweep.json"
)
OTHER_SCENARIO_PATH = (
    ROOT / "scenarios" / "npc_hp_link_hypothesis_target_sweep.json"
)
MODULE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "hostile_hp_link_hypothesis.py"
)
APP_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "app.py"
RUNTIME_SOURCE_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
REPLAY_TOOL = ROOT / "tools" / "pf_hostile_hp_link_headless_replay.py"

# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")

FLAG = "--hostile-hp-link-hypothesis-scenario"

EXPECTED_STEP_ORDER = (
    "TARGET_SPAWN", "HIT_WEAK", "TARGET_HP_AFTER_WEAK", "MISS",
    "TARGET_HP_AFTER_MISS", "HIT_STRONG", "TARGET_HP_AFTER_STRONG",
)
EXPECTED_KINDS = ("actor", "hit", "actor", "hit", "actor", "hit", "actor")
EXPECTED_LADDER = (3857, 3857, 2893, 2893, 2893, 2893, 771)
EXPECTED_DAMAGE = {"HIT_WEAK": -964, "MISS": 0, "HIT_STRONG": -2122}
EXPECTED_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}
EXPECTED_DELAYS = tuple([0.0] + [6.0] * 6)
TARGET_IDENTITY = 0x201F
PERFORMER_LO = 0x10010001
PERFORMER_HI = 0
WORLD_ROW = (1747.5244140625, -7837.69775390625, 931.0413208007812)
SWEEP_EVENT = "hostile_hp_link_hypothesis_target_sweep_sent"
EVENT_PREFIX = "hostile_hp_link_hypothesis_"


def _canonical_stat():
    """Size and mtime of the canonical database, WITHOUT opening it."""
    if not CANONICAL_DB.exists():
        return None
    info = CANONICAL_DB.stat()
    return (info.st_size, info.st_mtime_ns)


_CANONICAL_AT_IMPORT = _canonical_stat()


def tearDownModule():
    """Round 41's lesson, enforced: pytest may not move the canonical file."""
    if _canonical_stat() != _CANONICAL_AT_IMPORT:
        raise AssertionError(
            "this test module changed the canonical database's size or mtime; "
            "this lane writes nothing and this suite opens no database at all"
        )


def _run_app(args, timeout=180):
    """Run the REAL app.py entry point, in a subprocess, and report."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get(
        "PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "pirateforce_foundation.app", *args],
        cwd=str(ROOT), env=env, capture_output=True, text=True,
        timeout=timeout,
    )


class HostileHpLinkBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.scenario = hh.load_hostile_hp_link_hypothesis_scenario(
            SCENARIO_PATH)
        cls.unlock = hh.hostile_hp_link_wire_unlock(cls.scenario)
        cls.probe_position = hh.hostile_hp_link_probe_player_position(
            cls.legacy)
        cls.target = hh.resolve_hostile_hp_link_target(
            cls.legacy, cls.probe_position, cls.scenario)
        cls.actions = hh.build_hostile_hp_link_sweep(
            cls.legacy, cls.target, PERFORMER_LO, PERFORMER_HI,
            cls.unlock, cls.scenario,
        )
        cls.rows = hh.validate_hostile_hp_link_sweep(cls.actions)
        cls.by_step = {
            action[0].replace(hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX, ""):
                action
            for action in cls.actions
        }
        cls.file_tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))


class PlanTests(HostileHpLinkBase):
    def test_the_plan_is_seven_steps_in_the_pinned_order(self):
        self.assertEqual(hh.HOSTILE_HP_LINK_STEP_ORDER, EXPECTED_STEP_ORDER)
        self.assertEqual(
            tuple(row[1] for row in hh.HOSTILE_HP_LINK_STEPS), EXPECTED_KINDS)

    def test_the_lane_declares_its_identity_and_refuses_production(self):
        self.assertEqual(hh.HOSTILE_HP_LINK_HYPOTHESIS_ID, "HYP-PF-038")
        self.assertEqual(hh.HOSTILE_HP_LINK_CHECKPOINT, "HOSTILE-HP-LINK-001")
        self.assertIs(hh.production_allowed, False)
        self.assertIs(self.file_tree["production_allowed"], False)
        self.assertIs(self.file_tree["test_only"], True)

    def test_the_target_is_the_real_hostile_not_the_sibling_lanes_probe(self):
        self.assertEqual(hh.HOSTILE_HP_LINK_TARGET_IDENTITY_LO, 0x201F)
        self.assertEqual(hh.HOSTILE_HP_LINK_TARGET_PLACEMENT_INDEX, 30)
        self.assertEqual(hh.HOSTILE_HP_LINK_TARGET_TEMPLATE_ID, 31)
        self.assertEqual(
            hh.HOSTILE_HP_LINK_TARGET_SOURCE_NAME, "Tornado Eagle")
        self.assertEqual(
            hh.HOSTILE_HP_LINK_TARGET_VISUAL_PRESET, "M011_000_000_SP3")
        self.assertEqual(hh.HOSTILE_HP_LINK_HP_BASELINE, 3857)

    def test_the_identity_is_the_frozen_formula_not_a_typed_constant(self):
        self.assertEqual(
            0x2000 + hh.HOSTILE_HP_LINK_TARGET_PLACEMENT_INDEX + 1,
            hh.HOSTILE_HP_LINK_TARGET_IDENTITY_LO,
        )
        self.assertEqual(
            self.legacy.V112_MONSTER_ACTOR_ID,
            hh.HOSTILE_HP_LINK_TARGET_IDENTITY_LO,
        )
        self.assertEqual(
            self.legacy.V117_P30_EXACT_HP, hh.HOSTILE_HP_LINK_HP_BASELINE)
        self.assertEqual(
            self.legacy.V119_P30_TARGET_NAME,
            hh.HOSTILE_HP_LINK_TARGET_SOURCE_NAME,
        )

    def test_no_step_is_lethal_and_the_two_lethal_registers_are_empty(self):
        self.assertEqual(hh.HOSTILE_HP_LINK_LETHAL_STEP_LABELS, ())
        self.assertEqual(hh.HOSTILE_HP_LINK_TIMER_BY_STEP, {})
        for _label, kind, spec, _flags in hh.HOSTILE_HP_LINK_STEPS:
            if kind != hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                continue
            self.assertIsNone(spec[1])
            self.assertGreater(spec[0], hh.HOSTILE_HP_LINK_HP_FLOOR)

    def test_the_spacing_is_the_short_profile_and_the_first_delay_is_zero(self):
        self.assertEqual(hh.HOSTILE_HP_LINK_SPACING_SECONDS, 6.0)
        self.assertEqual(hh.HOSTILE_HP_LINK_FIRST_DELAY_SECONDS, 0.0)
        self.assertNotEqual(hh.HOSTILE_HP_LINK_SPACING_SECONDS, 15.0)

    def test_the_label_prefix_names_this_slot_not_the_sibling(self):
        self.assertEqual(
            hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX,
            "HYP_PF_038_HOSTILE_HP_LINK_",
        )
        self.assertNotIn("029", hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX)


class ArithmeticTests(HostileHpLinkBase):
    def test_the_ladder_is_derived_by_the_engine_not_declared(self):
        self.assertEqual(
            hh.replay_hostile_hp_link_balance_ladder(), EXPECTED_LADDER)
        self.assertEqual(hh.HOSTILE_HP_LINK_BALANCE_LADDER, EXPECTED_LADDER)

    def test_the_damage_numbers_come_out_of_the_formula(self):
        defence = hh.compute_hostile_hp_link_defense(
            hh.DEFENDER_LEVEL, hh.DEFENDER_ABILITY_CON)
        for name, expected in (("MOB_WEAK", -964), ("MOB_STRONG", -2122)):
            level, ability = hh.HOSTILE_HP_LINK_ATTACKER_PROFILES[name]
            attack = hh.compute_hostile_hp_link_attack(level, ability)
            self.assertEqual(-(attack - defence), expected)
            self.assertEqual(
                hh.compute_hostile_hp_link_damage_wire(name), expected)

    def test_the_movement_is_visible_on_a_3857_bar(self):
        """The whole reason the profiles differ from the sibling lane's."""
        baseline = hh.HOSTILE_HP_LINK_HP_BASELINE
        after_weak = EXPECTED_LADDER[2] / baseline
        after_strong = EXPECTED_LADDER[6] / baseline
        self.assertAlmostEqual(after_weak, 0.75, places=3)
        self.assertAlmostEqual(after_strong, 0.20, places=3)
        # The sibling lane's own number, for contrast: 1.6 percent of the bar.
        self.assertLess(63 / baseline, 0.02)

    def test_a_move_that_would_reach_the_floor_is_refused_not_clamped(self):
        with self.assertRaises(hh.HostileHpLinkValidationError) as caught:
            hh.apply_hit_to_balance(100, -100, 0x0001)
        self.assertIn("hp_clamp_is_forbidden_in_this_lane", str(caught.exception))
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.apply_hit_to_balance(100, -1000, 0x0001)

    def test_a_miss_moves_nothing(self):
        self.assertEqual(hh.apply_hit_to_balance(3857, 0, 0x0000), 3857)

    def test_the_engine_refuses_every_disagreeing_pair(self):
        for balance, damage, flags in (
            (3857, 0, 0x0001),          # zero damage with the apply bit
            (3857, -964, 0x0000),       # damage without the apply bit
            (3857, 964, 0x0001),        # a positive number: heal semantics
            (3857, -964, 0x0009),       # a flag outside the allowlist
            (-1, -964, 0x0001),         # a balance outside the band
        ):
            with self.assertRaises(hh.HostileHpLinkValidationError):
                hh.apply_hit_to_balance(balance, damage, flags)


class GeometryTests(HostileHpLinkBase):
    """The half of this lane an attended round lives or dies on."""

    def test_the_composed_position_is_the_player_plus_the_offsets(self):
        px, py, pz = self.probe_position
        self.assertEqual(self.target.x, px + hh.HOSTILE_HP_LINK_TARGET_DX)
        self.assertEqual(self.target.y, py + hh.HOSTILE_HP_LINK_TARGET_DY)
        self.assertEqual(self.target.z, pz + hh.HOSTILE_HP_LINK_TARGET_DZ)

    def test_the_frozen_world_row_is_carried_but_never_composed(self):
        self.assertEqual(
            (self.target.world_x, self.target.world_y, self.target.world_z),
            WORLD_ROW,
        )
        self.assertNotEqual(
            (self.target.x, self.target.y, self.target.z), WORLD_ROW)
        spawn_pc = self.by_step["TARGET_SPAWN"][1]
        for value in WORLD_ROW:
            self.assertNotIn(struct.pack("<f", value), spawn_pc)

    def test_the_offsets_are_the_arena_lanes_and_ride_the_scenario(self):
        arena = json.loads(
            (ROOT / "scenarios" / "arena_v1.json").read_text(encoding="utf-8"))
        position = arena["target"]["position"]
        self.assertEqual(position["mode"], hh.HOSTILE_HP_LINK_POSITION_MODE)
        self.assertEqual(float(position["dx"]), hh.HOSTILE_HP_LINK_TARGET_DX)
        self.assertEqual(float(position["dy"]), hh.HOSTILE_HP_LINK_TARGET_DY)
        self.assertEqual(float(position["dz"]), hh.HOSTILE_HP_LINK_TARGET_DZ)
        self.assertEqual(
            self.file_tree["probe"]["position_mode"], "player_relative")

    def test_the_scenario_file_never_names_the_world_row(self):
        raw = SCENARIO_PATH.read_text(encoding="utf-8")
        module = MODULE_PATH.read_text(encoding="utf-8")
        # The module pins the row so it can REFUSE it; the scenario file is
        # what the attended ticket greps, and it must be clean.
        self.assertNotIn("1747.5", raw)
        self.assertNotIn("-7837.6", raw)
        self.assertIn("player_relative", raw)
        self.assertIn("1747.5244140625", module)

    def test_a_target_placed_at_the_world_row_is_refused_by_name(self):
        offsets = (
            hh.HOSTILE_HP_LINK_TARGET_DX,
            hh.HOSTILE_HP_LINK_TARGET_DY,
            hh.HOSTILE_HP_LINK_TARGET_DZ,
        )
        standing = tuple(
            row - offset for row, offset in zip(WORLD_ROW, offsets))
        with self.assertRaises(hh.HostileHpLinkValidationError) as caught:
            hh.resolve_hostile_hp_link_target(
                self.legacy, standing, self.scenario)
        self.assertIn("not_player_relative", str(caught.exception))

    def test_a_live_position_composes_and_keeps_the_size_pins(self):
        live = hh.resolve_hostile_hp_link_target(
            self.legacy, (-8553.947, -2579.689, 186.0, 0.0, 0, 0),
            self.scenario,
        )
        self.assertFalse(live.probe_geometry)
        actions = hh.build_hostile_hp_link_sweep(
            self.legacy, live, 0x10010002, 0, self.unlock, self.scenario)
        for (label, pc, frame, _delay), (_l, ppc, pframe, _d) in zip(
            actions, self.actions,
        ):
            step = label.replace(hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX, "")
            self.assertEqual(len(pc), hh.HOSTILE_HP_LINK_PINS[step]["pc_size"])
            self.assertEqual(len(pc), len(ppc))
            self.assertEqual(len(frame), len(pframe))
        # ... and the bytes are NOT the pinned ones, which is the point.
        self.assertNotEqual(actions[0][1], self.actions[0][1])

    def test_the_position_argument_is_refused_when_it_is_not_a_position(self):
        for value in (None, "here", (1.0, 2.0), (1.0, 2.0, "z"),
                      (1.0, 2.0, float("nan")), [1.0, 2.0, 3.0]):
            with self.assertRaises(hh.HostileHpLinkValidationError):
                hh.resolve_hostile_hp_link_target(
                    self.legacy, value, self.scenario)


class CompositionTests(HostileHpLinkBase):
    def test_seven_actions_with_the_pinned_labels_and_delays(self):
        self.assertEqual(len(self.actions), 7)
        self.assertEqual(
            tuple(action[0] for action in self.actions),
            tuple(hh.HOSTILE_HP_LINK_ACTION_LABELS),
        )
        self.assertEqual(
            tuple(action[3] for action in self.actions), EXPECTED_DELAYS)

    def test_every_frame_matches_the_module_and_the_file_pins(self):
        for step, (_label, pc, frame, _delay) in self.by_step.items():
            pin = hh.HOSTILE_HP_LINK_PINS[step]
            file_pin = self.file_tree["probe"]["per_step"][step]
            self.assertEqual(len(pc), pin["pc_size"])
            self.assertEqual(len(frame), pin["frame_size"])
            self.assertEqual(
                hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
            self.assertEqual(
                hashlib.sha256(frame).hexdigest().upper(), pin["frame_sha256"])
            self.assertEqual(pin, file_pin)

    def test_the_transport_frame_is_the_frozen_projection_of_the_pc(self):
        for _step, (_label, pc, frame, _delay) in self.by_step.items():
            self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_two_post_hit_frames_around_the_miss_are_byte_identical(self):
        self.assertEqual(
            self.by_step["TARGET_HP_AFTER_WEAK"][1],
            self.by_step["TARGET_HP_AFTER_MISS"][1],
        )

    def test_only_the_spawn_frame_places_the_actor(self):
        for step, (_label, pc, _frame, _delay) in self.by_step.items():
            decoded = hh.decode_hostile_hp_link_frame(pc)
            if decoded["kind"] != hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                continue
            has_movement = hh.MOVEMENT_ATTR_ID in decoded["attrs"]
            self.assertEqual(has_movement, step == "TARGET_SPAWN")


class DecodeTests(HostileHpLinkBase):
    def test_the_carriers_alternate_and_never_share_a_frame(self):
        for index, row in enumerate(self.rows):
            self.assertEqual(row["kind"], EXPECTED_KINDS[index])

    def test_every_frame_is_about_the_same_hostile(self):
        self.assertEqual(
            {row["target_identity"] for row in self.rows}, {TARGET_IDENTITY})

    def test_the_hit_frames_carry_our_numbers_and_our_flags(self):
        for row in self.rows:
            if row["kind"] != hh.HOSTILE_HP_LINK_STEP_KIND_HIT:
                continue
            self.assertEqual(row["damage_wire"], EXPECTED_DAMAGE[row["label"]])
            self.assertEqual(row["flags"], EXPECTED_FLAGS[row["label"]])
            self.assertNotEqual(row["performer_identity"], TARGET_IDENTITY)

    def test_the_ladder_is_in_the_bytes(self):
        walked = [
            row.get("hp_current") for row in self.rows
            if row["kind"] == hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR
        ]
        self.assertEqual(walked, [3857, 2893, 2893, 771])
        for row in self.rows:
            if row["kind"] != hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                continue
            self.assertIsNone(row["hp_death_timer"])

    def test_the_name_and_the_preset_are_on_the_wire(self):
        spawn_pc = self.by_step["TARGET_SPAWN"][1]
        self.assertIn("Tornado Eagle".encode("utf-16-le"), spawn_pc)
        self.assertIn("M011_000_000_SP3".encode("utf-16-le"), spawn_pc)
        decoded = hh.decode_hostile_hp_link_frame(spawn_pc)
        self.assertEqual(
            decoded["attrs"][hh.NPC_ATTR_ID]["visual_preset"],
            "M011_000_000_SP3",
        )

    def test_the_client_baseline_is_the_max_hp_of_every_actor_frame(self):
        for _step, (_label, pc, _frame, _delay) in self.by_step.items():
            decoded = hh.decode_hostile_hp_link_frame(pc)
            if decoded["kind"] != hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                continue
            fields = decoded["attrs"][hh.NPC_ATTR_ID]["fields"]
            self.assertEqual(fields[hh.BASIC_BIT_MAX_HP], 3857)

    def test_no_frame_carries_the_death_timer_bit(self):
        for _step, (_label, pc, _frame, _delay) in self.by_step.items():
            decoded = hh.decode_hostile_hp_link_frame(pc)
            if decoded["kind"] != hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                continue
            mask = decoded["attrs"][hh.NPC_ATTR_ID]["basic_mask"]
            self.assertFalse(mask & hh.BASIC_BIT_DEATH_TIMER)
            self.assertTrue(mask & hh.BASIC_BIT_NAME)

    def test_the_sibling_lanes_identity_appears_nowhere(self):
        forged = struct.pack("<Q", 0x2001)
        for _step, (_label, pc, _frame, _delay) in self.by_step.items():
            self.assertNotIn(forged, pc)


class RefusalTests(HostileHpLinkBase):
    def test_the_encoders_refuse_without_the_unlock(self):
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.encode_hostile_hp_link_hit_entry(
                self.legacy, TARGET_IDENTITY, -964,
                (0.0, 0.0, 0.0), 0.0, 0x0001, None,
            )
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.encode_hostile_hp_link_npc_attr(
                self.legacy, self.target, "TARGET_SPAWN", 3857, None, None)

    def test_a_value_equal_forgery_mints_nothing(self):
        forged = hh.HostileHpLinkHypothesisScenario(
            hh.HOSTILE_HP_LINK_SCENARIO_ID,
            hh.HOSTILE_HP_LINK_HYPOTHESIS_ID,
            hh.HOSTILE_HP_LINK_STEP_ORDER,
            hh.HOSTILE_HP_LINK_SPACING_SECONDS,
            hh.HOSTILE_HP_LINK_FIRST_DELAY_SECONDS,
            hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX,
            hh.HOSTILE_HP_LINK_POSITION_MODE,
            hh.HOSTILE_HP_LINK_TARGET_DX,
            hh.HOSTILE_HP_LINK_TARGET_DY,
            hh.HOSTILE_HP_LINK_TARGET_DZ,
        )
        self.assertEqual(forged, self.scenario)
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.hostile_hp_link_wire_unlock(forged)

    def test_a_death_timer_is_refused_by_name_on_every_step(self):
        for label in hh.HOSTILE_HP_LINK_STEP_ORDER:
            with self.assertRaises(hh.HostileHpLinkValidationError) as caught:
                hh.encode_hostile_hp_link_npc_attr(
                    self.legacy, self.target, label, 3857, 20.0, self.unlock)
            self.assertIn(
                "lethal_field_is_not_available_in_this_lane",
                str(caught.exception),
            )

    def test_a_floor_balance_is_refused_by_name(self):
        with self.assertRaises(hh.HostileHpLinkValidationError) as caught:
            hh.encode_hostile_hp_link_npc_attr(
                self.legacy, self.target, "TARGET_SPAWN", 0, None,
                self.unlock,
            )
        self.assertIn(
            "lethal_field_is_not_available_in_this_lane", str(caught.exception))

    def test_the_hit_entry_refuses_any_other_target(self):
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.encode_hostile_hp_link_hit_entry(
                self.legacy, 0x2001, -964,
                (self.target.x, self.target.y, self.target.z), 0.0, 0x0001,
                self.unlock,
            )

    def test_the_performer_may_not_be_the_target(self):
        entry = hh.encode_hostile_hp_link_hit_entry(
            self.legacy, TARGET_IDENTITY, -964,
            (self.target.x, self.target.y, self.target.z), 0.0, 0x0001,
            self.unlock,
        )
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.encode_hostile_hp_link_chit_result(
                self.legacy, TARGET_IDENTITY, [entry], self.unlock)

    def test_the_validator_refuses_a_reordered_or_shortened_sweep(self):
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.validate_hostile_hp_link_sweep(list(self.actions)[:-1])
        reversed_actions = list(self.actions)
        reversed_actions[1], reversed_actions[2] = (
            reversed_actions[2], reversed_actions[1])
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.validate_hostile_hp_link_sweep(reversed_actions)

    def test_the_validator_refuses_a_drifted_delay(self):
        drifted = list(self.actions)
        label, pc, frame, _delay = drifted[3]
        drifted[3] = (label, pc, frame, 15.0)
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.validate_hostile_hp_link_sweep(drifted)


class ScenarioFileTests(HostileHpLinkBase):
    def test_the_file_loads_to_the_module_profile(self):
        self.assertIs(self.scenario, hh._PROFILE)

    def test_one_changed_key_anywhere_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            for mutate in (
                lambda tree: tree.__setitem__("schema", 2),
                lambda tree: tree.__setitem__("extra_key", True),
                lambda tree: tree.pop("checkpoint"),
                lambda tree: tree["wire"]["hp_ladder"].__setitem__(
                    "floor", 1),
                lambda tree: tree["probe"].__setitem__(
                    "position_mode", "world"),
            ):
                tree = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
                mutate(tree)
                path = Path(tmp) / "mutated.json"
                path.write_text(json.dumps(tree), encoding="utf-8")
                with self.assertRaises(hh.HostileHpLinkValidationError):
                    hh.load_hostile_hp_link_hypothesis_scenario(path)

    def test_a_neighbouring_lanes_scenario_is_refused(self):
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.load_hostile_hp_link_hypothesis_scenario(OTHER_SCENARIO_PATH)

    def test_a_missing_file_is_refused_rather_than_defaulted(self):
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.load_hostile_hp_link_hypothesis_scenario(None)
        with self.assertRaises(hh.HostileHpLinkValidationError):
            hh.load_hostile_hp_link_hypothesis_scenario(
                ROOT / "scenarios" / "does_not_exist.json")

    def test_the_file_declares_the_house_disciplines(self):
        self.assertIs(self.file_tree["dispatch"]["one_shot"], True)
        self.assertEqual(self.file_tree["dispatch"]["socket_action"], "none")
        self.assertEqual(
            self.file_tree["persisted_post_state"]["database_write"], "none")
        self.assertEqual(self.file_tree["dispatch"]["lethal_steps"], [])
        self.assertIs(
            self.file_tree["wire"]["target_carrier"]["lethal_half"][
                "composed_by_this_lane"],
            False,
        )
        self.assertIn(
            "nobody_has_ever_confirmed_with_their_own_eyes_that_a_model_at_"
            "this_distance_is_inside_the_clients_draw_distance",
            self.file_tree["nonclaims"],
        )


class WiringTests(unittest.TestCase):
    def test_the_flag_is_declared_once_and_reaches_the_runtime(self):
        source = APP_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(source.count("'%s'" % FLAG), 1)
        self.assertIn(
            "hostile_hp_link_hypothesis_scenario=hostile_hp_link_hypothesis",
            source,
        )
        self.assertIn(
            "--hostile-hp-link-hypothesis-scenario requires an explicit ",
            source,
        )
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-038 active"), 1)

    def test_the_runtime_carries_the_branch_and_the_named_refusals(self):
        source = RUNTIME_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertEqual(
            source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-038 active"), 1)
        for marker in (
            "def _dispatch_hostile_hp_link_hypothesis(",
            "hostile_hp_link_hypothesis_scenario=None,",
            "hostile_hp_link_unlock = hostile_hp_link_wire_unlock(",
            "self.hostile_hp_link_sweep_count = 0",
            "hostile_hp_link_hypothesis_no_selected_no_reply",
            "hostile_hp_link_hypothesis_wrong_sequence_no_reply",
            "hostile_hp_link_hypothesis_wrong_scene_no_reply",
            "hostile_hp_link_hypothesis_already_sent_no_reply",
            "hostile_hp_link_hypothesis_target_sweep_sent",
            "HYP-PF-038 sweep event name drift",
        ):
            self.assertIn(marker, source)

    def test_the_sources_are_ascii(self):
        for path in (MODULE_PATH, SCENARIO_PATH, Path(__file__)):
            self.assertTrue(
                path.read_text(encoding="utf-8").isascii(),
                "%s must stay ASCII: the bridge console is cp874" % path.name,
            )

    def test_the_flag_is_refused_alongside_another_mode(self):
        result = _run_app([
            "--db", str(ROOT / "state" / "does_not_matter.sqlite3"),
            FLAG, str(SCENARIO_PATH),
            "--npc-hp-link-hypothesis-scenario", str(OTHER_SCENARIO_PATH),
        ])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mutually exclusive", result.stderr)

    def test_the_flag_demands_an_explicit_db(self):
        result = _run_app([FLAG, str(SCENARIO_PATH)])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "--hostile-hp-link-hypothesis-scenario requires an explicit",
            result.stderr,
        )


class ToolTests(unittest.TestCase):
    """The headless replay the attended ticket's layer (1) leans on."""

    def _run_tool(self, *extra):
        env = dict(os.environ)
        return subprocess.run(
            [sys.executable, str(REPLAY_TOOL), *extra],
            cwd=str(ROOT), env=env, capture_output=True, text=True,
            timeout=180,
        )

    def test_the_replay_runs_green_and_needs_no_database(self):
        result = self._run_tool("--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertEqual(verdict["result"], "PASS")
        self.assertEqual(verdict["hypothesis_id"], "HYP-PF-038")
        self.assertEqual(len(verdict["frames"]), 7)
        self.assertTrue(all(verdict["checks"].values()))

    def test_the_replay_reports_the_placement_for_a_live_position(self):
        result = self._run_tool(
            "--json", "--player-position=-8553.947,-2579.689,186.0")
        self.assertEqual(result.returncode, 0, result.stderr)
        verdict = json.loads(result.stdout)
        self.assertFalse(verdict["probe_geometry"])
        self.assertTrue(verdict["checks"]["the_placement_is_player_relative"])
        placed = [
            frame["actor_placed_at"] for frame in verdict["frames"]
            if "actor_placed_at" in frame
        ]
        self.assertEqual(len(placed), 1)
        self.assertAlmostEqual(placed[0][0], -8453.947, places=2)

    def test_the_replay_names_every_refusal_it_drives(self):
        result = self._run_tool("--json")
        verdict = json.loads(result.stdout)
        for refusal in verdict["refusals"]:
            self.assertIsNotNone(
                refusal["raised"],
                "%s did not refuse at all" % refusal["expected"],
            )
            self.assertTrue(refusal["raised"].startswith(refusal["expected"]))
        self.assertIn(
            "lethal_field_is_not_available_in_this_lane",
            [refusal["expected"] for refusal in verdict["refusals"]],
        )

    def test_the_tool_is_ascii_and_takes_no_db_argument(self):
        source = REPLAY_TOOL.read_text(encoding="utf-8")
        self.assertTrue(source.isascii())
        self.assertNotIn("--db", source)
        result = self._run_tool("--db", "anything")
        self.assertNotEqual(result.returncode, 0)


class DispatchTests(unittest.TestCase):
    """The lane driven through make_state_class on a throwaway database."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)
        self.db_path = self.tmp_dir / "state.sqlite3"
        self.assertIn(
            Path(tempfile.gettempdir()).resolve(),
            self.db_path.resolve().parents,
        )
        self.assertNotIn(ROOT.resolve(), self.db_path.resolve().parents)
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
        self.scenario = hh.load_hostile_hp_link_hypothesis_scenario(
            SCENARIO_PATH)
        self.unlock = hh.hostile_hp_link_wire_unlock(self.scenario)

    def tearDown(self):
        self.tmp.cleanup()

    def _state(self, login, *, sweep=True, ready=True, select=True):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            hostile_hp_link_hypothesis_scenario=(
                self.scenario if sweep else None),
        )
        state = state_type(login)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc()))
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._V25_REAL_CREATE_PC))
        self.assertEqual(actions[0][0], "FOUNDATION_CREATE_COMMITTED")
        if select:
            characters = self.store.list_characters(state.foundation.account_id)
            actions = state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(characters[-1].selector)))
            self.assertEqual(actions[0][0], "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = ready
        return state

    def _trigger(self):
        return self.legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])

    def test_one_accepted_trigger_composes_the_whole_sweep(self):
        state = self._state("hhl01")
        actions = state.dispatch(self._trigger())
        self.assertEqual(len(actions), 7)
        self.assertEqual(
            [action[0] for action in actions],
            list(hh.HOSTILE_HP_LINK_ACTION_LABELS),
        )
        self.assertIn(SWEEP_EVENT, state.events)
        rows = hh.validate_hostile_hp_link_sweep(actions)
        self.assertEqual(
            [row.get("hp_current") for row in rows if row["kind"] == "actor"],
            [3857, 2893, 2893, 771],
        )

    def test_the_target_is_placed_against_the_players_own_row(self):
        state = self._state("hhl02")
        actions = state.dispatch(self._trigger())
        position = state.foundation.selected.position
        expected = (
            float(position.x) + hh.HOSTILE_HP_LINK_TARGET_DX,
            float(position.y) + hh.HOSTILE_HP_LINK_TARGET_DY,
            float(position.z) + hh.HOSTILE_HP_LINK_TARGET_DZ,
        )
        # The hit frames carry the position the number floats at, and the
        # decoder reads it back from byte 0 -- so this is the composed
        # geometry as the client would see it, not as the composer meant it.
        hit = hh.decode_hostile_hp_link_frame(actions[1][1])
        for composed, wanted in zip(hit["position"], expected):
            self.assertAlmostEqual(composed, wanted, places=3)
        # ... and the spawn frame places the actor at the same three floats.
        spawn_pc = actions[0][1]
        for value in expected:
            self.assertIn(struct.pack("<f", value), spawn_pc)
        # The frozen world row is nowhere in the sweep.
        for value in WORLD_ROW:
            self.assertNotIn(struct.pack("<f", value), spawn_pc)

    def test_the_sweep_is_one_shot_per_connection_not_per_process(self):
        state = self._state("hhl03")
        self.assertEqual(len(state.dispatch(self._trigger())), 7)
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_already_sent_no_reply", state.events)
        # A SECOND CONNECTION for the same account gets its own sweep: the
        # counter lives on the connection, not on the process.  The lane's
        # nonclaims used to say "one_shot_per_process", copied in from a
        # neighbour; an adversarial review of R162 caught that this test
        # falsifies it, and the nonclaim was corrected rather than the test.
        other = self._state("hhl03")
        self.assertEqual(len(other.dispatch(self._trigger())), 7)

    def test_every_refusal_is_named_and_emits_no_frame(self):
        no_selection = self._state("hhl05", select=False)
        self.assertEqual(no_selection.dispatch(self._trigger()), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_no_selected_no_reply",
            no_selection.events,
        )
        not_ready = self._state("hhl05", ready=False)
        self.assertEqual(not_ready.dispatch(self._trigger()), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_wrong_sequence_no_reply",
            not_ready.events,
        )
        # A refusal must not burn the one shot.
        not_ready.runtime_ack_sent = True
        self.assertEqual(len(not_ready.dispatch(self._trigger())), 7)

    def test_with_the_scenario_absent_the_lane_does_not_exist(self):
        state = self._state("hhl07", sweep=False)
        actions = state.dispatch(self._trigger())
        self.assertEqual(
            [label for label, *_rest in actions
             if label.startswith("HYP_PF_038")],
            [],
        )
        self.assertEqual(
            [event for event in state.events
             if event.startswith(EVENT_PREFIX)],
            [],
        )

    def test_the_lane_writes_nothing_to_the_database(self):
        state = self._state("hhl08")
        before = sorted(
            (name, (self.tmp_dir / name).stat().st_size)
            for name in os.listdir(self.tmp_dir)
        )
        state.dispatch(self._trigger())
        after = sorted(
            (name, (self.tmp_dir / name).stat().st_size)
            for name in os.listdir(self.tmp_dir)
        )
        self.assertEqual(before, after)

    def test_an_unpinned_performer_gets_no_bytes(self):
        """The promise the attended ticket makes about picking the wrong row.

        A second account's character is a different identity, and this lane
        composes for one pinned identity only -- so the tester who selects
        the wrong row sees the same thing they see when anything else is
        wrong: nothing at all, and a named event nobody at the client can
        read.  Both halves of that are the point.
        """
        self._state("hhl10")            # burns the pinned identity
        other_account = self._state("hhl11")
        self.assertEqual(other_account.dispatch(self._trigger()), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_identity_not_pinned_no_reply",
            other_account.events,
        )

    def test_a_trigger_that_is_not_ascii12_is_refused_by_classification(self):
        """A Thai keyboard, or any high byte, lands here -- not in the sweep."""
        state = self._state("hhl12")
        pc = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        pc[-1] ^= 0xFF
        self.assertEqual(
            state.dispatch(self.legacy.parse_outer(bytes(pc))), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_wrong_text_no_reply", state.events)
        # ... and the refusal did not burn the one shot.
        self.assertEqual(len(state.dispatch(self._trigger())), 7)

    def test_a_player_in_another_scene_is_refused_by_name(self):
        state = self._state("hhl13")
        position = state.foundation.selected.position
        state.foundation.checkpoint(
            Position(
                position.scene_id + 1, position.scene_seq,
                position.x, position.y, position.z, position.heading,
            )
        )
        self.assertEqual(state.dispatch(self._trigger()), [])
        self.assertIn(
            "hostile_hp_link_hypothesis_wrong_scene_no_reply", state.events)

    def test_the_dispatcher_bytes_are_the_composers_bytes(self):
        state = self._state("hhl09")
        actions = state.dispatch(self._trigger())
        selected = state.foundation.selected
        position = selected.position
        target = hh.resolve_hostile_hp_link_target(
            self.legacy,
            (float(position.x), float(position.y), float(position.z)),
            self.scenario,
        )
        expected = hh.build_hostile_hp_link_sweep(
            self.legacy, target, selected.identity_lo, selected.identity_hi,
            self.unlock, self.scenario,
        )
        self.assertEqual(actions, expected)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
