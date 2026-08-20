"""NPC-HP-LINK-001 (HYP-PF-029) -- the target sweep, proven offline.

WHAT THIS FILE PROVES
---------------------
That the lane composes ONE eight-frame ``GSCN_RunTimeProtocolRes`` (id 0x6E9D
version 4) sweep that alternates the two client-proven carriers against ONE
frozen Port Royal placement identity (0x2001), and that it moves a TARGET's
hit points -- which nothing else in this tree has ever done:

  * the three ``CHitResult`` 0x16F7 v0 frames ride the VitalData collection
    (BASE mask 0x02 at object +0x18, trailing DERIVED mask 0x00), performer =
    the player, target = 0x2001;
  * the five actor-entry frames ride the actor-entry collection (INHERITED
    mask 0x00, DERIVED mask 0x02 at object +0x1C, ``actor_type`` 4 CNetNPC)
    carrying an ``NPCAttr`` whose BasicAttr ``hp_current`` is a server-held
    balance and whose bit 0x0080 f32 at +0x58 arms and then elapses the dying
    window.

Same bit NUMBER, different mask BYTE, different reader.  Several tests below
exist only to keep those two collections told apart.

WHOSE ARITHMETIC THIS IS
------------------------
**Ours.**  The original server is closed, was never published and cannot be
recovered.  NO CAPTURE IN ANY CORPUS shows a target's hit points moving in
response to damage in either direction, and round 83 proved the client
computes nothing and never subtracts -- which is exactly why the server has to
say both halves itself.  On 2026-08-20 an attended test (GT-027 rerun, on
video) delivered 63 + 379 + 63 = 505 damage to a selected NPC and the target's
HP bar did not move by a single unit.

NOT proven here, and this is the load-bearing limit: **whether the client
renders the intermediate value 37 on the target's HP bar is UNDECIDABLE from
static analysis and is the queued attended test.**  The only thing proven so
far is that negative.  No client has ever been shown one byte of this profile.

DISCIPLINE.  This suite opens no database at all -- the lane writes nothing --
and the canonical database is only ``stat``-ed, once at import and once at the
end, so a regression that reached for it would be reported rather than
silently tolerated.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import npc_hp_link_hypothesis as nh  # noqa: E402
# The two PARENT lanes, imported here as BYTE ORACLES.  The module itself
# imports neither: every constant it shares with them is COPIED, and these
# tests are the drift guard that makes copying safe.
from pirateforce_foundation import damage_model_hypothesis as dm  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rd  # noqa: E402
from pirateforce_foundation import damage_hp_link_hypothesis as hpl  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = ROOT / "scenarios" / "npc_hp_link_hypothesis_target_sweep.json"
DAMAGE_NPC_SCENARIO = (
    ROOT / "scenarios" / "damage_model_hypothesis_npc_sweep.json"
)
DEATH_SCENARIO = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
)
MODULE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "npc_hp_link_hypothesis.py"
)

# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")

EXPECTED_STEP_ORDER = (
    "TARGET_SPAWN", "HIT_WEAK", "TARGET_HP_AFTER_WEAK", "MISS",
    "TARGET_HP_AFTER_MISS", "HIT_STRONG", "TARGET_HP_ZERO_DYING",
    "TARGET_DYING_ELAPSED",
)
EXPECTED_KINDS = ("actor", "hit", "actor", "hit", "actor", "hit", "actor",
                  "actor")
EXPECTED_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
EXPECTED_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
EXPECTED_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}
EXPECTED_TIMERS = {"TARGET_HP_ZERO_DYING": 20.0, "TARGET_DYING_ELAPSED": 0.0}
EXPECTED_DELAYS = tuple([0.0] + [6.0] * 7)
TARGET_IDENTITY = 0x2001
PERFORMER_LO = 0x10010001
PERFORMER_HI = 0
PARENT_ORACLE = {
    "TARGET_SPAWN": ("death", "SPAWN"),
    "TARGET_HP_ZERO_DYING": ("death", "DYING_LATCH"),
    "TARGET_DYING_ELAPSED": ("death", "DEATH_TASK"),
    "HIT_WEAK": ("damage", "HIT_WEAK"),
    "MISS": ("damage", "MISS"),
    "HIT_STRONG": ("damage", "HIT_STRONG"),
}


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


class NpcHpLinkBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.scenario = nh.load_npc_hp_link_hypothesis_scenario(SCENARIO_PATH)
        cls.unlock = nh.npc_hp_link_wire_unlock(cls.scenario)
        cls.target = nh.resolve_npc_hp_link_target(cls.legacy)
        cls.actions = nh.build_npc_hp_link_sweep(
            cls.legacy, cls.target, PERFORMER_LO, PERFORMER_HI,
            cls.unlock, cls.scenario,
        )
        cls.by_step = {
            action[0].replace(nh.NPC_HP_LINK_ACTION_LABEL_PREFIX, ""): action
            for action in cls.actions
        }
        cls.file_tree = json.loads(
            SCENARIO_PATH.read_text(encoding="utf-8"))


class PlanTests(NpcHpLinkBase):
    def test_the_plan_is_the_eight_pinned_steps_in_order(self):
        self.assertEqual(nh.NPC_HP_LINK_STEP_ORDER, EXPECTED_STEP_ORDER)
        self.assertEqual(
            tuple(row[1] for row in nh.NPC_HP_LINK_STEPS), EXPECTED_KINDS)

    def test_the_lane_identifies_itself_as_hyp_pf_029_npc_hp_link_001(self):
        self.assertEqual(nh.NPC_HP_LINK_HYPOTHESIS_ID, "HYP-PF-029")
        self.assertEqual(nh.NPC_HP_LINK_CHECKPOINT, "NPC-HP-LINK-001")
        self.assertEqual(
            nh.NPC_HP_LINK_SCENARIO_ID, "npc_hp_link_hypothesis_target_sweep")
        self.assertEqual(
            nh.NPC_HP_LINK_DISPATCH_KWARG, "npc_hp_link_hypothesis_scenario")
        self.assertEqual(
            nh.NPC_HP_LINK_EVENT_NAME,
            "npc_hp_link_hypothesis_target_sweep_sent")
        self.assertEqual(
            nh.NPC_HP_LINK_WIRING_OWNER, "npc_hp_link_002_round_111")
        self.assertEqual(
            nh.NPC_HP_LINK_ACTION_LABEL_PREFIX, "HYP_PF_029_NPC_HP_LINK_")

    def test_the_lane_is_not_production_allowed(self):
        self.assertIs(nh.production_allowed, False)
        self.assertIs(self.file_tree["production_allowed"], False)
        self.assertIs(self.file_tree["test_only"], True)

    def test_the_spacing_is_six_seconds_not_the_fifteen_second_profile(self):
        """Panya, 2026-08-20: stretching frame spacing for the human tester is
        wasted effort because the event itself is short; the correct fix is
        recording video.  The reason is data, not folklore."""
        self.assertEqual(nh.NPC_HP_LINK_SPACING_SECONDS, 6.0)
        self.assertEqual(nh.NPC_HP_LINK_FIRST_DELAY_SECONDS, 0.0)
        self.assertNotEqual(
            nh.NPC_HP_LINK_SPACING_SECONDS, dm.DAMAGE_MODEL_NPC_SPACING_SECONDS)
        self.assertIn("recording_video", nh.NPC_HP_LINK_SPACING_DECISION)
        self.assertIn("wasted_effort", nh.NPC_HP_LINK_SPACING_DECISION)
        self.assertIn(
            "recording_video", self.file_tree["spacing_decision_comment"])
        header = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("recording video", header)

    def test_the_module_header_carries_the_nonclaim(self):
        header = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS", header)
        self.assertIn("505", header)
        self.assertIn("UNDECIDABLE from static analysis", header)
        self.assertIn("# PF-HYPOTHESIS-LEDGER: HYP-PF-029 active", header)
        self.assertIn("production_allowed = False", header)

    def test_the_nonclaims_name_the_undecidable_question_and_the_negative(self):
        joined = " ".join(nh.NPC_HP_LINK_NONCLAIMS)
        self.assertIn(
            "this_is_our_design_not_the_original_servers_which_is_"
            "unrecoverable", joined)
        self.assertIn("undecidable_from_static_analysis", joined)
        self.assertIn("505_damage_and_the_bar_did_not_move", joined)
        self.assertIn(
            "no_capture_shows_a_targets_hit_points_moving_in_response_to_"
            "damage_in_either_direction", joined)
        self.assertEqual(
            list(nh.NPC_HP_LINK_NONCLAIMS), self.file_tree["nonclaims"])

    def test_the_step_plan_validator_accepts_the_shipped_plan(self):
        nh._require_step_plan()

    def test_the_first_step_is_a_live_placed_spawn(self):
        label, kind, spec, _flags = nh.NPC_HP_LINK_STEPS[0]
        self.assertEqual((label, kind), ("TARGET_SPAWN", "actor"))
        self.assertEqual(spec, (100, None, True))

    def test_every_hit_step_is_followed_by_the_actor_frame_that_applies_it(self):
        for index, (_label, kind, _spec, _flags) in enumerate(
            nh.NPC_HP_LINK_STEPS
        ):
            if kind == "hit":
                self.assertEqual(nh.NPC_HP_LINK_STEPS[index + 1][1], "actor")


class ArithmeticTests(NpcHpLinkBase):
    def test_the_ladder_is_re_derived_not_declared(self):
        self.assertEqual(
            nh.replay_npc_hp_link_balance_ladder(), EXPECTED_LADDER)
        self.assertEqual(
            nh.require_npc_hp_link_balance_ladder(), EXPECTED_LADDER)
        self.assertEqual(nh.NPC_HP_LINK_BALANCE_LADDER, EXPECTED_LADDER)

    def test_the_damage_numbers_are_derived_from_the_formula(self):
        self.assertEqual(nh.compute_npc_hp_link_damage_wire("MOB_WEAK"), -63)
        self.assertEqual(
            nh.compute_npc_hp_link_damage_wire("MOB_STRONG"), -379)
        # The formula, re-run by hand here, with no help from the module.
        attack_weak = 100 + 7 * 3 + 3 * 1
        attack_strong = 100 + 7 * 40 + 3 * 20
        defense = 10 + 2 * 22 + 1 * 7
        self.assertEqual(-(attack_weak - defense), -63)
        self.assertEqual(-(attack_strong - defense), -379)

    def test_the_ladder_is_arithmetic_all_the_way_down(self):
        self.assertEqual(100 + (-63), EXPECTED_LADDER[2])
        self.assertEqual(EXPECTED_LADDER[2] + 0, EXPECTED_LADDER[4])
        self.assertEqual(max(0, EXPECTED_LADDER[4] + (-379)),
                         EXPECTED_LADDER[6])

    def test_the_clamp_happens_on_exactly_one_step(self):
        self.assertEqual(nh.NPC_HP_LINK_CLAMP_STEP_LABEL,
                         "TARGET_HP_ZERO_DYING")
        self.assertIn(nh.NPC_HP_LINK_CLAMP_STEP_LABEL,
                      nh.NPC_HP_LINK_LETHAL_STEP_LABELS)
        self.assertGreater(EXPECTED_LADDER[4] + (-379) * -1, 0)
        self.assertLess(EXPECTED_LADDER[4] + (-379), 0)

    def test_apply_hit_to_balance_refuses_every_named_way_to_be_wrong(self):
        for balance, damage, flags, reason in (
            (100.0, -63, 0x0001, "hp_balance_not_integer"),
            (True, -63, 0x0001, "hp_balance_not_integer"),
            (101, -63, 0x0001, "hp_balance_outside_the_declared_band"),
            (-1, -63, 0x0001, "hp_balance_outside_the_declared_band"),
            (100, 1, 0x0001, "damage_positive_heal_semantics_unknown"),
            (100, -63, 0x0009, "flags_outside_value_allowlist"),
            (100, 0, 0x0001, "damage_zero_with_apply_flag"),
            (100, -63, 0x0000, "damage_nonzero_without_apply_flag"),
        ):
            with self.subTest(reason=reason):
                with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
                    nh.apply_hit_to_balance(balance, damage, flags)
                self.assertTrue(str(ctx.exception).startswith(reason))

    def test_a_miss_moves_the_balance_by_exactly_zero(self):
        self.assertEqual(nh.apply_hit_to_balance(37, 0, 0x0000), 37)


class CompositionTests(NpcHpLinkBase):
    def test_the_sweep_is_eight_actions_with_the_pinned_labels_and_delays(self):
        self.assertEqual(len(self.actions), 8)
        self.assertEqual(
            tuple(action[0] for action in self.actions),
            tuple("HYP_PF_029_NPC_HP_LINK_" + step
                  for step in EXPECTED_STEP_ORDER),
        )
        self.assertEqual(
            tuple(action[3] for action in self.actions), EXPECTED_DELAYS)

    def test_every_composed_frame_reproduces_its_module_pin(self):
        for step in EXPECTED_STEP_ORDER:
            _label, pc, frame, _delay = self.by_step[step]
            pin = nh.NPC_HP_LINK_PINS[step]
            with self.subTest(step=step):
                self.assertEqual(len(pc), pin["pc_size"])
                self.assertEqual(len(frame), pin["frame_size"])
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest().upper(), pin["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest().upper(),
                    pin["frame_sha256"])

    def test_the_scenario_file_declares_the_same_eight_pins(self):
        for step in EXPECTED_STEP_ORDER:
            with self.subTest(step=step):
                self.assertEqual(
                    self.file_tree["probe"]["per_step"][step],
                    {
                        "pc_size": nh.NPC_HP_LINK_PINS[step]["pc_size"],
                        "pc_sha256": nh.NPC_HP_LINK_PINS[step]["pc_sha256"],
                        "frame_size": nh.NPC_HP_LINK_PINS[step]["frame_size"],
                        "frame_sha256":
                            nh.NPC_HP_LINK_PINS[step]["frame_sha256"],
                    },
                )

    def test_the_two_post_hit_hp_frames_are_byte_identical(self):
        """A miss moves nothing, and identical bytes are the strongest way to
        say so."""
        self.assertEqual(
            self.by_step["TARGET_HP_AFTER_WEAK"][1:3],
            self.by_step["TARGET_HP_AFTER_MISS"][1:3],
        )

    def test_the_two_lethal_frames_differ_because_the_polarity_flips(self):
        self.assertNotEqual(
            self.by_step["TARGET_HP_ZERO_DYING"][1],
            self.by_step["TARGET_DYING_ELAPSED"][1],
        )

    def test_the_frame_is_the_frozen_framer_applied_to_the_pc(self):
        for step in EXPECTED_STEP_ORDER:
            _label, pc, frame, _delay = self.by_step[step]
            with self.subTest(step=step):
                self.assertEqual(frame, self.legacy.frame_pc(pc))
                self.assertEqual(nh.decode_npc_hp_link_transport(frame), pc)

    def test_the_actor_frames_do_not_depend_on_the_performer_at_all(self):
        """Only the three hit frames vary with who is swinging; the five
        actor-entry frames are the same bytes for every session."""
        other = nh.build_npc_hp_link_sweep(
            self.legacy, self.target, 0x10010002, 0, self.unlock,
            self.scenario)
        other_by = {
            action[0].replace(nh.NPC_HP_LINK_ACTION_LABEL_PREFIX, ""): action
            for action in other
        }
        for step, kind in zip(EXPECTED_STEP_ORDER, EXPECTED_KINDS):
            with self.subTest(step=step):
                if kind == "actor":
                    self.assertEqual(
                        other_by[step][1:3], self.by_step[step][1:3])
                else:
                    self.assertNotEqual(
                        other_by[step][1], self.by_step[step][1])


class DecodeTests(NpcHpLinkBase):
    def test_the_hit_frames_ride_the_vitaldata_collection(self):
        for step in ("HIT_WEAK", "MISS", "HIT_STRONG"):
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["kind"], "hit")
                self.assertEqual(decoded["base_change_mask"], 0x02)
                self.assertEqual(decoded["derived_change_mask"], 0x00)
                self.assertEqual(decoded["vital_id"], 0x16F7)
                self.assertEqual(decoded["vital_version"], 0)

    def test_the_actor_frames_ride_the_actor_entry_collection(self):
        for step in ("TARGET_SPAWN", "TARGET_HP_AFTER_WEAK",
                     "TARGET_HP_AFTER_MISS", "TARGET_HP_ZERO_DYING",
                     "TARGET_DYING_ELAPSED"):
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["kind"], "actor")
                self.assertEqual(decoded["base_change_mask"], 0x00)
                self.assertEqual(decoded["derived_change_mask"], 0x02)
                self.assertEqual(decoded["actor_type"], 4)

    def test_the_two_collections_are_not_the_same_object(self):
        self.assertEqual(nh.HIT_BASE_OBJECT_OFFSET, 0x18)
        self.assertEqual(nh.ACTOR_DERIVED_OBJECT_OFFSET, 0x1C)
        self.assertNotEqual(
            nh.HIT_BASE_OBJECT_OFFSET, nh.ACTOR_DERIVED_OBJECT_OFFSET)

    def test_the_hit_frames_carry_the_pinned_damage_and_flag_pairs(self):
        for step, damage in EXPECTED_DAMAGE.items():
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["damage_wire"], damage)
                self.assertEqual(decoded["flags"], EXPECTED_FLAGS[step])
                self.assertEqual(decoded["yaw"], 0.0)

    def test_the_damage_field_is_the_signed_reading_of_a_u32_tag(self):
        decoded = nh.decode_npc_hp_link_frame(self.by_step["HIT_WEAK"][1])
        raw = struct.pack("<i", decoded["damage_wire"])
        self.assertEqual(struct.unpack("<I", raw)[0], (-63) & 0xFFFFFFFF)
        self.assertLess(decoded["damage_wire"], 0)

    def test_every_frame_of_the_sweep_names_the_same_target(self):
        seen = set()
        for step in EXPECTED_STEP_ORDER:
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            seen.add(decoded["target_identity"])
        self.assertEqual(seen, {TARGET_IDENTITY})

    def test_the_performer_is_the_player_and_never_the_target(self):
        for step in ("HIT_WEAK", "MISS", "HIT_STRONG"):
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["performer_identity"], PERFORMER_LO)
                self.assertNotEqual(
                    decoded["performer_identity"], decoded["target_identity"])

    def test_the_actor_frames_carry_the_server_held_target_ladder(self):
        for index, step in enumerate(EXPECTED_STEP_ORDER):
            if EXPECTED_KINDS[index] != "actor":
                continue
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            fields = decoded["attrs"][nh.NPC_ATTR_ID]["fields"]
            with self.subTest(step=step):
                self.assertEqual(
                    fields[nh.BASIC_BIT_CURRENT_HP], EXPECTED_LADDER[index])
                self.assertEqual(fields[nh.BASIC_BIT_MAX_HP], 100)
                self.assertEqual(
                    fields.get(nh.BASIC_BIT_DEATH_TIMER),
                    EXPECTED_TIMERS.get(step))

    def test_the_spawn_is_alive_placed_and_timerless(self):
        decoded = nh.decode_npc_hp_link_frame(self.by_step["TARGET_SPAWN"][1])
        fields = decoded["attrs"][nh.NPC_ATTR_ID]["fields"]
        self.assertEqual(fields[nh.BASIC_BIT_CURRENT_HP], 100)
        self.assertNotIn(nh.BASIC_BIT_DEATH_TIMER, fields)
        self.assertIn(nh.MOVEMENT_ATTR_ID, decoded["attrs"])

    def test_only_the_spawn_carries_a_movement_attr(self):
        for step in ("TARGET_HP_AFTER_WEAK", "TARGET_HP_AFTER_MISS",
                     "TARGET_HP_ZERO_DYING", "TARGET_DYING_ELAPSED"):
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertNotIn(nh.MOVEMENT_ATTR_ID, decoded["attrs"])

    def test_the_polarity_is_latch_first_then_task(self):
        dying = nh.decode_npc_hp_link_frame(
            self.by_step["TARGET_HP_ZERO_DYING"][1]
        )["attrs"][nh.NPC_ATTR_ID]["fields"]
        elapsed = nh.decode_npc_hp_link_frame(
            self.by_step["TARGET_DYING_ELAPSED"][1]
        )["attrs"][nh.NPC_ATTR_ID]["fields"]
        self.assertEqual(dying[nh.BASIC_BIT_CURRENT_HP], 0)
        self.assertGreater(dying[nh.BASIC_BIT_DEATH_TIMER], 0.0)
        self.assertEqual(elapsed[nh.BASIC_BIT_CURRENT_HP], 0)
        self.assertLessEqual(elapsed[nh.BASIC_BIT_DEATH_TIMER], 0.0)
        self.assertLess(
            EXPECTED_STEP_ORDER.index("TARGET_HP_ZERO_DYING"),
            EXPECTED_STEP_ORDER.index("TARGET_DYING_ELAPSED"),
        )

    def test_the_elapsed_timer_packs_to_the_pinned_five_bytes(self):
        self.assertEqual(
            bytes([nh.DEATH_TIMER_TAG]) + struct.pack("<f", 0.0),
            nh.NPC_HP_LINK_TIMER_ELAPSED_WIRE_BYTES,
        )

    def test_the_validator_returns_one_row_per_step(self):
        rows = nh.validate_npc_hp_link_sweep(list(self.actions))
        self.assertEqual([row["label"] for row in rows],
                         list(EXPECTED_STEP_ORDER))
        self.assertEqual([row["kind"] for row in rows], list(EXPECTED_KINDS))


class RefusalTests(NpcHpLinkBase):
    def test_the_encoder_refuses_to_emit_without_the_unlock(self):
        with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
            nh.encode_npc_hp_link_hit_entry(
                self.legacy, TARGET_IDENTITY, -63, (0.0, 0.0, 0.0), 0.0,
                0x0001, None)
        self.assertTrue(
            str(ctx.exception).startswith("missing_or_forged_wire_unlock"))

    def test_a_value_equal_unlock_is_refused_by_identity(self):
        forged = nh.NpcHpLinkWireUnlock(
            nh.NPC_HP_LINK_SCENARIO_ID, nh.NPC_HP_LINK_HYPOTHESIS_ID)
        self.assertEqual(forged, self.unlock)
        self.assertIsNot(forged, self.unlock)
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.require_npc_hp_link_wire_unlock(forged)

    def test_a_value_equal_scenario_object_mints_nothing(self):
        lookalike = nh.NpcHpLinkHypothesisScenario(
            nh.NPC_HP_LINK_SCENARIO_ID, nh.NPC_HP_LINK_HYPOTHESIS_ID,
            nh.NPC_HP_LINK_STEP_ORDER, 6.0, 0.0,
            nh.NPC_HP_LINK_ACTION_LABEL_PREFIX)
        self.assertEqual(lookalike, nh._PROFILE)
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.npc_hp_link_wire_unlock(lookalike)

    def test_the_hit_entry_refuses_any_target_but_the_pinned_one(self):
        with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
            nh.encode_npc_hp_link_hit_entry(
                self.legacy, 0x2002, -63,
                (float(self.legacy.V135_PLAYER_X),
                 float(self.legacy.V135_PLAYER_Y),
                 float(self.legacy.V135_PLAYER_Z)), 0.0, 0x0001, self.unlock)
        self.assertTrue(
            str(ctx.exception).startswith("npc_target_identity_not_pinned"))

    def test_the_npc_may_not_be_its_own_performer(self):
        with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
            nh.encode_npc_hp_link_chit_result(
                self.legacy, TARGET_IDENTITY, [b"\x00" * 37], self.unlock)
        self.assertTrue(str(ctx.exception).startswith(
            "npc_performer_must_not_be_the_npc_target"))

    def test_the_lethal_fields_may_only_ride_the_two_lethal_steps(self):
        for step, hp, timer in (
            ("TARGET_HP_AFTER_WEAK", 37, 20.0),
            ("TARGET_HP_AFTER_WEAK", 0, None),
            ("TARGET_SPAWN", 0, None),
            ("TARGET_HP_ZERO_DYING", 0, None),
            ("TARGET_HP_ZERO_DYING", 37, 20.0),
        ):
            with self.subTest(step=step, hp=hp, timer=timer):
                with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
                    nh.encode_npc_hp_link_npc_attr(
                        self.legacy, self.target, step, hp, timer, self.unlock)
                self.assertTrue(str(ctx.exception).startswith(
                    "lethal_field_outside_the_pinned_step"))

    def test_the_death_timer_refuses_every_unpinned_shape(self):
        for step, value, reason in (
            ("TARGET_HP_ZERO_DYING", 19.0,
             "death_timer_outside_the_pinned_plan"),
            ("TARGET_HP_ZERO_DYING", 20, "death_timer_not_float"),
            ("TARGET_DYING_ELAPSED", -0.0,
             "death_timer_elapsed_is_not_the_pinned_zero"),
            ("TARGET_DYING_ELAPSED", float("nan"), "death_timer_not_finite"),
        ):
            with self.subTest(step=step, value=value):
                with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
                    nh.encode_npc_hp_link_npc_attr(
                        self.legacy, self.target, step, 0, value, self.unlock)
                self.assertTrue(str(ctx.exception).startswith(reason))

    def test_the_flag_word_allowlist_excludes_the_reaction_word(self):
        self.assertEqual(
            tuple(nh.NPC_HP_LINK_FLAGS_VALUE_ALLOWLIST), (0x0000, 0x0001))
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.require_npc_hp_link_flags_value(0x0009)

    def test_healing_is_refused_by_name(self):
        with self.assertRaises(nh.NpcHpLinkValidationError) as ctx:
            nh.require_npc_hp_link_damage_wire_value(1)
        self.assertTrue(str(ctx.exception).startswith(
            "damage_positive_heal_semantics_unknown"))

    def test_the_validator_refuses_a_tampered_sweep(self):
        bad = list(self.actions)
        pc = bytearray(bad[2][1])
        pc[40] ^= 0x01
        raw = bytes(pc)
        bad[2] = (bad[2][0], raw, self.legacy.frame_pc(raw), bad[2][3])
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.validate_npc_hp_link_sweep(bad)

    def test_the_validator_refuses_the_sweep_reversed(self):
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.validate_npc_hp_link_sweep(list(reversed(self.actions)))

    def test_the_validator_refuses_a_short_sweep(self):
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.validate_npc_hp_link_sweep(list(self.actions)[:7])

    def test_the_validator_refuses_a_wrong_delay(self):
        bad = list(self.actions)
        bad[1] = (bad[1][0], bad[1][1], bad[1][2], 15.0)
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.validate_npc_hp_link_sweep(bad)

    def test_the_decoder_refuses_a_frame_from_neither_carrier(self):
        pc = bytearray(self.by_step["TARGET_SPAWN"][1])
        pc[11] = 0x04
        with self.assertRaises(nh.NpcHpLinkValidationError):
            nh.decode_npc_hp_link_frame(bytes(pc))


class ScenarioFileTests(NpcHpLinkBase):
    def test_the_file_loads_to_the_modules_own_profile_object(self):
        self.assertIs(self.scenario, nh._PROFILE)

    def test_one_extra_key_anywhere_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = json.loads(json.dumps(self.file_tree))
            tree["unexpected"] = 1
            path = Path(tmp) / "extra.json"
            path.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaises(nh.NpcHpLinkValidationError):
                nh.load_npc_hp_link_hypothesis_scenario(path)

    def test_one_missing_key_anywhere_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = json.loads(json.dumps(self.file_tree))
            del tree["dispatch"]["one_shot"]
            path = Path(tmp) / "missing.json"
            path.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaises(nh.NpcHpLinkValidationError):
                nh.load_npc_hp_link_hypothesis_scenario(path)

    def test_one_changed_value_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = json.loads(json.dumps(self.file_tree))
            tree["dispatch"]["spacing_seconds"] = 15.0
            path = Path(tmp) / "changed.json"
            path.write_text(json.dumps(tree), encoding="utf-8")
            with self.assertRaises(nh.NpcHpLinkValidationError):
                nh.load_npc_hp_link_hypothesis_scenario(path)

    def test_a_neighbouring_lanes_scenario_is_refused(self):
        for other in (DAMAGE_NPC_SCENARIO, DEATH_SCENARIO,
                      ROOT / "scenarios"
                      / "damage_hp_link_hypothesis_link_sweep.json"):
            with self.subTest(other=other.name):
                with self.assertRaises(nh.NpcHpLinkValidationError):
                    nh.load_npc_hp_link_hypothesis_scenario(other)

    def test_the_file_declares_one_shot_no_socket_and_no_database_write(self):
        self.assertIs(self.file_tree["dispatch"]["one_shot"], True)
        self.assertEqual(self.file_tree["dispatch"]["socket_action"], "none")
        self.assertEqual(
            self.file_tree["persisted_post_state"]["database_write"], "none")

    def test_the_file_states_the_undecidable_question(self):
        self.assertIn(
            "undecidable", json.dumps(self.file_tree))
        self.assertIn("37", self.file_tree["undecidable_from_static_analysis"])
        self.assertIn(
            "505", self.file_tree["undecidable_from_static_analysis"])

    def test_the_file_declares_the_ladder_as_the_targets(self):
        self.assertEqual(
            self.file_tree["wire"]["hp_ladder"]["owner"],
            "the_target_not_the_player")
        self.assertEqual(
            self.file_tree["wire"]["hp_ladder"]["ladder"],
            list(EXPECTED_LADDER))

    def test_the_file_names_the_wiring_owner_and_the_real_dispatch(self):
        self.assertEqual(
            self.file_tree["dispatch"]["wiring_owner"],
            "npc_hp_link_002_round_111")
        self.assertIs(self.file_tree["dispatch"]["wired"], True)
        self.assertEqual(
            self.file_tree["dispatch"]["runtime_dispatch_branch"],
            "runtime_py_dispatch_npc_hp_link_hypothesis_reached_from_the_app_"
            "flag_through_make_state_class")


class CrossLaneByteEqualityTests(NpcHpLinkBase):
    """The strongest drift guard this lane can have.

    Every constant this module shares with a parent is COPIED, never imported.
    These tests are what makes copying safe, and the honest statement of how is
    NOT "two verifiers red at once" -- an adversarial review mutated this
    lane's actor_type and found all three parent tools still green.  A drift in
    a PARENT turns that parent's verifier red and turns these tests red too,
    because they recompose the parent's own bytes.  A drift in THIS lane turns
    only this lane's tests and verifier red.  The guard lives here.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dm_profile = dm.load_damage_model_hypothesis_scenario(
            DAMAGE_NPC_SCENARIO)
        dm_unlock = dm.damage_model_wire_unlock(dm_profile)
        dm_probe = dm.damage_probe_actor(cls.legacy)
        cls.damage_by = {
            label: dm.make_damage_model_step_response(
                cls.legacy, dm_probe, index, dm_unlock, dm_profile)
            for index, label in enumerate(dm_profile.step_order)
        }
        rd_profile = rd.load_runtimeres_death_hypothesis_scenario(
            DEATH_SCENARIO)
        rd_unlock = rd.runtimeres_death_lethal_unlock(rd_profile)
        cls.rd_probe = rd.resolve_probe(cls.legacy)
        cls.death_by = {
            label: rd.make_runtimeres_death_step_response(
                cls.legacy, cls.rd_probe, index, rd_unlock, rd_profile)
            for index, label in enumerate(rd_profile.step_order)
        }
        cls.oracle = {"damage": cls.damage_by, "death": cls.death_by}

    def test_six_of_the_eight_frames_are_a_parents_bytes_exactly(self):
        for step, (lane, parent_step) in PARENT_ORACLE.items():
            parent_pc, parent_frame = self.oracle[lane][parent_step]
            _label, pc, frame, _delay = self.by_step[step]
            with self.subTest(step=step, parent=parent_step):
                self.assertEqual(pc, parent_pc)
                self.assertEqual(frame, parent_frame)

    def test_the_two_intermediate_frames_use_the_parents_own_body_oracle(self):
        """TARGET_HP_AFTER_WEAK / _MISS have no counterpart STEP in the death
        lane, so the oracle is the frozen projection that lane uses as its own
        baseline."""
        baseline = self.legacy.make_npc_attr(
            self.target.template_id, self.target.actor_identity,
            self.target.scene_id, self.target.scene_sequence,
            self.target.visual_preset, 37, 100)
        mine = nh.encode_npc_hp_link_npc_attr(
            self.legacy, self.target, "TARGET_HP_AFTER_WEAK", 37, None,
            self.unlock)
        theirs = rd.encode_death_capable_npc_attr(
            self.legacy, self.rd_probe, current_hp=37, max_hp=100)
        self.assertEqual(mine, baseline)
        self.assertEqual(mine, theirs)

    def test_the_copied_pins_agree_with_the_parents_live_tables(self):
        for step, (lane, parent_step) in PARENT_ORACLE.items():
            table = (rd.RUNTIMERES_DEATH_PINS if lane == "death"
                     else dm.DAMAGE_MODEL_PINS_NPC)
            with self.subTest(step=step):
                self.assertEqual(
                    nh.NPC_HP_LINK_PINS[step]["pc_sha256"],
                    table[parent_step]["pc_sha256"])
                self.assertEqual(
                    nh.NPC_HP_LINK_PINS[step]["frame_sha256"],
                    table[parent_step]["frame_sha256"])
                self.assertEqual(
                    nh.NPC_HP_LINK_PINS[step]["pc_size"],
                    table[parent_step]["pc_size"])
                self.assertEqual(
                    nh.NPC_HP_LINK_PINS[step]["frame_size"],
                    table[parent_step]["frame_size"])

    def test_the_reverse_direction_the_parents_pins_are_still_this_lanes(self):
        """The guard has to bite BOTH ways, or a parent could drift while this
        lane sat still."""
        for step, (lane, parent_step) in PARENT_ORACLE.items():
            table = (rd.RUNTIMERES_DEATH_PINS if lane == "death"
                     else dm.DAMAGE_MODEL_PINS_NPC)
            parent_pc, parent_frame = self.oracle[lane][parent_step]
            with self.subTest(step=step):
                self.assertEqual(
                    hashlib.sha256(parent_pc).hexdigest().upper(),
                    nh.NPC_HP_LINK_PINS[step]["pc_sha256"])
                self.assertEqual(
                    hashlib.sha256(parent_frame).hexdigest().upper(),
                    table[parent_step]["frame_sha256"])

    def test_the_formula_constants_did_not_drift_from_either_parent(self):
        self.assertEqual(
            (nh.ATK_BASE, nh.K_ATK_STR, nh.K_ATK_LV, nh.DEF_BASE,
             nh.K_DEF_CON, nh.K_DEF_LV, nh.MIN_HIT),
            (dm.ATK_BASE, dm.K_ATK_STR, dm.K_ATK_LV, dm.DEF_BASE,
             dm.K_DEF_CON, dm.K_DEF_LV, dm.MIN_HIT),
        )
        self.assertEqual(
            (nh.ATK_BASE, nh.K_ATK_STR, nh.K_ATK_LV, nh.DEF_BASE,
             nh.K_DEF_CON, nh.K_DEF_LV, nh.MIN_HIT),
            (hpl.ATK_BASE, hpl.K_ATK_STR, hpl.K_ATK_LV, hpl.DEF_BASE,
             hpl.K_DEF_CON, hpl.K_DEF_LV, hpl.MIN_HIT),
        )
        self.assertEqual(
            (nh.DEFENDER_LEVEL, nh.DEFENDER_ABILITY_CON),
            (dm.DEFENDER_LEVEL, dm.DEFENDER_ABILITY_CON))
        self.assertEqual(
            dict(nh.NPC_HP_LINK_ATTACKER_PROFILES),
            dict(hpl.HP_LINK_ATTACKER_PROFILES))
        self.assertEqual(
            dict(nh.NPC_HP_LINK_DAMAGE_PINNED),
            dict(hpl.HP_LINK_DAMAGE_PINNED))

    def test_the_formula_reproduces_the_damage_lanes_own_numbers(self):
        self.assertEqual(
            nh.compute_npc_hp_link_damage_wire("MOB_WEAK"),
            dm.compute_damage(dm.ATTACKER_MOB_WEAK,
                              dm.DEFENDER_PLAYER_BASELINE))
        self.assertEqual(
            nh.compute_npc_hp_link_damage_wire("MOB_STRONG"),
            dm.compute_damage(dm.ATTACKER_MOB_STRONG,
                              dm.DEFENDER_PLAYER_BASELINE))

    def test_the_wire_constants_did_not_drift_from_either_parent(self):
        self.assertEqual(nh.CHIT_RESULT_VITAL_ID, dm.CHIT_RESULT_VITAL_ID)
        self.assertEqual(
            nh.CHIT_RESULT_VITAL_VERSION, dm.CHIT_RESULT_VITAL_VERSION)
        self.assertEqual(
            nh.CHIT_RESULT_HEADER_WIRE_SIZE, dm.CHIT_RESULT_HEADER_WIRE_SIZE)
        self.assertEqual(nh.HIT_ELEMENT_WIRE_SIZE, dm.HIT_ELEMENT_WIRE_SIZE)
        self.assertEqual(nh.FLAGS_FORBIDDEN_MASK, dm.FLAGS_FORBIDDEN_MASK)
        self.assertEqual(
            nh.BASIC_BIT_DEATH_TIMER, rd.BASIC_BIT_DEATH_TIMER)
        self.assertEqual(nh.DEATH_TIMER_OFFSET, rd.DEATH_TIMER_OFFSET)
        self.assertEqual(nh.DEATH_TIMER_TAG, rd.DEATH_TIMER_TAG)
        self.assertEqual(
            nh.DYING_LATCH_TIMER_SECONDS, rd.DYING_LATCH_TIMER_SECONDS)
        self.assertEqual(
            nh.DEATH_TASK_TIMER_SECONDS, rd.DEATH_TASK_TIMER_SECONDS)
        self.assertEqual(
            nh.DYING_LATCH_PREDICATE_VA, rd.DYING_LATCH_PREDICATE_VA)
        self.assertEqual(
            nh.DEATH_TASK_PREDICATE_VA, rd.DEATH_TASK_PREDICATE_VA)
        self.assertEqual(
            nh.ACTOR_DERIVED_CHANGE_MASK,
            rd.DERIVED_CHANGE_MASK_ACTOR_ENTRIES)

    def test_the_target_identity_is_the_one_both_parents_already_drive(self):
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_IDENTITY_LO, dm.DAMAGE_NPC_TARGET_IDENTITY_LO)
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_IDENTITY_HI, dm.DAMAGE_NPC_TARGET_IDENTITY_HI)
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_IDENTITY_LO,
            rd.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_PLACEMENT_INDEX,
            rd.RUNTIMERES_DEATH_PROBE_PLACEMENT_INDEX)
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_VISUAL_PRESET,
            rd.RUNTIMERES_DEATH_PROBE_VISUAL_PRESET)
        self.assertEqual(
            nh.NPC_HP_LINK_TARGET_SOURCE_NAME,
            rd.RUNTIMERES_DEATH_PROBE_SOURCE_NAME)
        self.assertEqual(self.target.actor_identity, self.rd_probe.actor_identity)

    def test_this_lane_moves_a_target_where_hyp_pf_026_moved_the_player(self):
        """The gap this checkpoint closes, stated as a test.

        HYP-PF-026 links damage to hit points on the PLAYER's own actor, on
        the base VitalData carrier, with no actor-entry collection at all.
        """
        self.assertEqual(hpl.HP_LINK_DERIVED_CHANGE_MASK, 0x00)
        self.assertEqual(nh.ACTOR_DERIVED_CHANGE_MASK, 0x02)
        self.assertEqual(
            nh.NPC_HP_LINK_BALANCE_LADDER, hpl.HP_LINK_BALANCE_LADDER)
        actor_frames = [
            step for step, kind in zip(EXPECTED_STEP_ORDER, EXPECTED_KINDS)
            if kind == "actor"
        ]
        self.assertEqual(len(actor_frames), 5)
        for step in actor_frames:
            decoded = nh.decode_npc_hp_link_frame(self.by_step[step][1])
            with self.subTest(step=step):
                self.assertEqual(decoded["target_identity"], TARGET_IDENTITY)
                self.assertNotEqual(decoded["target_identity"], PERFORMER_LO)


class ContainmentTests(NpcHpLinkBase):
    def test_no_path_in_this_suite_names_the_canonical_database(self):
        text = Path(__file__).read_text(encoding="utf-8")
        self.assertNotIn("pirateforce" + ".sqlite3", text)

    def test_the_canonical_database_has_not_moved_since_this_module_loaded(self):
        self.assertEqual(_canonical_stat(), _CANONICAL_AT_IMPORT)

    def test_the_module_source_is_pure_ascii(self):
        self.assertTrue(
            all(byte < 0x80 for byte in MODULE_PATH.read_bytes()))

    def test_the_scenario_file_is_pure_ascii(self):
        self.assertTrue(
            all(byte < 0x80 for byte in SCENARIO_PATH.read_bytes()))

    def test_the_module_imports_neither_parent_lane(self):
        """Copied, never imported.  The cross-lane tests above are what makes
        that safe; an import here would widen both parents' blast radius."""
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("from .damage_model_hypothesis", text)
        self.assertNotIn("from .runtimeres_death_hypothesis", text)
        self.assertNotIn("from .damage_hp_link_hypothesis", text)
        self.assertNotIn("import damage_model_hypothesis", text)
        self.assertNotIn("import runtimeres_death_hypothesis", text)


if __name__ == "__main__":
    unittest.main()
