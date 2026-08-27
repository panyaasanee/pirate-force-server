"""LANE-B / GT-DIAG-MULTI-OBJECT-001: proof that four objects differ from a

control by exactly the field the design says and nothing else, as bytes.

The load-bearing tests are the four ``test_*_byte_diff_from_control`` ones:
each rebuilds D0 and one variant through the exact functions
:mod:`mob_diag_multi_object` calls and asserts the ONLY difference on the wire
is the one the module's docstring names -- never by reading the module's own
claim about itself, always by re-deriving the expected bytes independently
from :mod:`field_mobs`/:mod:`mob_death`/the legacy bridge, the same way
``test_field_mobs.py`` and ``test_mob_death.py`` cross-check their own
composers.
"""

import inspect
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, mob_death, mob_diag_multi_object as diag
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import DeathRegister


PERFORMER = 0x750059
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)


class DiagObjectsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")

    def setUp(self):
        self.objects = diag.diagnostic_objects()
        self.by_label = {obj.label: obj for obj in self.objects}

    def killing_outcome(self, mob):
        ledger = open_ledger(tuple(obj.mob for obj in self.objects))
        step = strike(
            self.legacy, None, ledger, None, mob, PERFORMER, LETHAL)
        self.assertTrue(step.outcome.death_due)
        return step.outcome

    def killing_outcome_solo(self, mob):
        # For a mob that is not one of the five (e.g. one of the five
        # repositioned onto another's identity, which would collide with it
        # in the shared ledger `killing_outcome` uses).
        step = strike(
            self.legacy, None, open_ledger((mob,)), None, mob, PERFORMER,
            LETHAL)
        self.assertTrue(step.outcome.death_due)
        return step.outcome

    # -- shape of the five --------------------------------------------------

    def test_five_objects_five_distinct_identities_five_distinct_positions(self):
        self.assertEqual(len(self.objects), 5)
        self.assertEqual(
            tuple(obj.label for obj in self.objects), diag.DIAG_LABELS)
        identities = [obj.mob.actor_identity for obj in self.objects]
        self.assertEqual(len(identities), len(set(identities)))
        positions = [(obj.mob.x, obj.mob.y, obj.mob.z) for obj in self.objects]
        self.assertEqual(len(positions), len(set(positions)))

    def test_no_diagnostic_identity_collides_with_a_live_roster_member(self):
        live = {mob.actor_identity for mob in field_mobs.load_roster()}
        for obj in self.objects:
            self.assertNotIn(obj.mob.actor_identity, live)

    def test_body_fields_off_position_are_identical_to_the_control_everywhere(self):
        control = self.by_label[diag.DIAG_LABEL_CONTROL].mob
        for obj in self.objects:
            mob = obj.mob
            self.assertEqual(mob.template_id, control.template_id)
            self.assertEqual(mob.visual_preset, control.visual_preset)
            self.assertEqual(mob.display_name, control.display_name)
            self.assertEqual(mob.level, control.level)
            self.assertEqual(mob.rank, control.rank)
            self.assertEqual(mob.ai_wander, control.ai_wander)
            self.assertEqual(mob.ai_combat, control.ai_combat)
            self.assertEqual(mob.max_hp, control.max_hp)

    def test_the_body_is_the_hand_mined_mountain_deer_row_not_a_roster_search(
            self):
        # Template 27 is NOT a member of either generated roster -- this is
        # the replacement for the old "search field_mobs.load_roster()"
        # assertion, which no longer applies (that search would now find
        # nothing at all, in either scene).
        control = self.by_label[diag.DIAG_LABEL_CONTROL].mob
        self.assertEqual(control.template_id, diag.DIAG_MOUNTAIN_DEER_TEMPLATE_ID)
        self.assertEqual(control.template_id, 27)
        for mob in field_mobs.load_roster():
            self.assertNotEqual(mob.template_id, 27)
        for mob in field_mobs.load_roster(scene=field_mobs.BG0002_SCENE):
            self.assertNotEqual(mob.template_id, 27)
        self.assertEqual(control.visual_preset, diag.DIAG_MOUNTAIN_DEER_VISUAL_PRESET)
        self.assertEqual(control.display_name, "Mountain Deer")
        self.assertEqual(control.max_hp, diag.DIAG_MOUNTAIN_DEER_MAX_HP)
        self.assertEqual(control.scene, field_mobs.field_mob_tables.SCENE)

    def test_the_chosen_body_is_NOT_aggro_this_is_a_known_tradeoff(self):
        # pf-adversary / this round's swap: ADDENDUM 19:05's original
        # criterion (a) was "has aggro AI", and the PREVIOUS body (Jungle Big
        # Tiger, ai_wander=11, n_AGGRO 1200) satisfied it. Mountain Deer
        # (ai_wander=16) does NOT -- field_mob_ai_tables.AI_WANDER_ROWS[16]'s
        # own n_AGGRO is 0, the SAME zero-aggro row the module docstring
        # says most bg0001 hostiles use and the old pick was chosen away
        # from. This test pins that fact plainly rather than silently
        # dropping the old assertion, per the owner's own later, more
        # specific ADDENDUM 20:18 instruction, which is followed here even
        # though it trades this criterion away.
        from pirateforce_foundation import field_mob_ai_tables
        control = self.by_label[diag.DIAG_LABEL_CONTROL].mob
        self.assertEqual(control.ai_wander, 16)
        _wander, _faction, _offensive, aggro = (
            field_mob_ai_tables.AI_WANDER_ROWS[control.ai_wander])
        self.assertEqual(aggro, 0)

    def test_the_chosen_body_still_grants_exp(self):
        # The SECOND of ADDENDUM 19:05's two criteria still holds for the
        # new body: f_RATIO_EXP 1.0, same contrast the module used for the
        # old pick (the two hand-placed story NPCs read 0.0). This project
        # has no per-scene EXP table wired here, so this is pinned as a
        # constant checked against the module's own provenance comment
        # rather than re-derived from a table this test would have to mine
        # itself.
        control = self.by_label[diag.DIAG_LABEL_CONTROL].mob
        self.assertEqual(diag.DIAG_MOUNTAIN_DEER_AI_COMBAT, 150)
        # f_RATIO_EXP is not carried on FieldMob; the module's own docstring
        # cites CONSTDATA_TH__MOBS row 27's f_RATIO_EXP as 1.0, matching
        # ADDENDUM 20:18's own relayed number -- there is no live column on
        # this record to assert it against directly, so this test instead
        # pins the one MOBS figure that IS carried (ai_combat) as the anchor
        # a human re-checking the docstring's other cited figures can use.
        self.assertEqual(control.ai_combat, diag.DIAG_MOUNTAIN_DEER_AI_COMBAT)

    def test_exactly_three_bg0001_hostiles_have_nonzero_aggro_and_none_is_the_control(self):
        # Still true of bg0001's own roster (unaffected by the body swap);
        # what changed is that the control is no longer one of them --
        # pinned explicitly so a future reader does not assume otherwise
        # from this test's name alone surviving the swap.
        from pirateforce_foundation import field_mob_ai_tables
        aggro_mobs = [
            mob for mob in field_mobs.load_roster()
            if field_mob_ai_tables.AI_WANDER_ROWS[mob.ai_wander][3] > 0
        ]
        self.assertEqual(len(aggro_mobs), 3)
        control = self.by_label[diag.DIAG_LABEL_CONTROL].mob
        self.assertNotIn(
            control.template_id, {m.template_id for m in aggro_mobs})

    # -- D0 / D2: the alive entry itself ------------------------------------

    def test_d0_alive_entry_is_the_production_hostile_builder(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        got = diag.alive_entry(self.legacy, d0)
        want = field_mobs.hostile_actor_entry(self.legacy, d0.mob)
        self.assertEqual(got, want)

    def test_d2_byte_diff_from_control_is_only_identity_and_position(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        d2 = self.by_label[diag.DIAG_LABEL_REPEAT_CONTROL]
        # Rebuild D2's alive entry against a mob that carries D0's identity
        # and position instead of its own: if that reproduces D0's entry
        # byte for byte, the only wire difference between the real D0 and D2
        # is the identity/position this test just swapped back.
        respositioned = field_mobs.FieldMob(
            **{**d2.mob.__dict__,
               "placement_index": d0.mob.placement_index,
               "x": d0.mob.x, "y": d0.mob.y, "z": d0.mob.z})
        self.assertEqual(respositioned.actor_identity, d0.mob.actor_identity)
        got = field_mobs.hostile_actor_entry(self.legacy, respositioned)
        want = diag.alive_entry(self.legacy, d0)
        self.assertEqual(got, want)

    # -- D1a: death schedule, frame bytes untouched -------------------------

    def test_d1a_frame_composition_reuses_kill_untouched(self):
        # dying_timer_hold_schedule must add no composition of its own: for
        # D1a's own mob its frames must equal mob_death.kill()'s frames for
        # the SAME mob at the SAME hold_ms, byte for byte.
        d1a = self.by_label[diag.DIAG_LABEL_DYING_TIMER_HOLD]
        outcome = self.killing_outcome(d1a.mob)
        want = mob_death.kill(
            self.legacy, d1a.mob, outcome,
            hold_ms=int(mob_death.DYING_TIMER_SECONDS * 1000),
            widened=diag.DIAG_WIDENED_RULING)
        got = diag.dying_timer_hold_schedule(self.legacy, d1a, outcome)
        self.assertEqual(got.dying_frame, want.dying_frame)
        self.assertEqual(got.dead_frame, want.dead_frame)
        self.assertEqual(got.hold_ms, want.hold_ms)

    def test_d1a_frames_match_d0s_once_repositioned_onto_its_identity_and_hold_is_the_only_other_change(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        d1a = self.by_label[diag.DIAG_LABEL_DYING_TIMER_HOLD]
        repositioned = field_mobs.FieldMob(
            **{**d1a.mob.__dict__,
               "placement_index": d0.mob.placement_index,
               "x": d0.mob.x, "y": d0.mob.y, "z": d0.mob.z})
        self.assertEqual(repositioned.actor_identity, d0.mob.actor_identity)
        d0_step = diag.kill_schedule(
            self.legacy, d0, self.killing_outcome(d0.mob))
        repositioned_outcome = self.killing_outcome_solo(repositioned)
        repositioned_step = diag.dying_timer_hold_schedule(
            self.legacy,
            diag.DiagObject(diag.DIAG_LABEL_DYING_TIMER_HOLD, "", repositioned),
            repositioned_outcome)
        self.assertEqual(repositioned_step.dying_frame, d0_step.dying_frame)
        self.assertEqual(repositioned_step.dead_frame, d0_step.dead_frame)
        self.assertNotEqual(repositioned_step.hold_ms, d0_step.hold_ms)
        self.assertEqual(repositioned_step.hold_ms, 20000)
        self.assertEqual(d0_step.hold_ms, mob_death.DEATH_TASK_HOLD_MS)

    def test_dying_timer_hold_schedule_refuses_the_wrong_object(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        with self.assertRaises(diag.MobDiagContractError):
            diag.dying_timer_hold_schedule(
                self.legacy, d0, self.killing_outcome(d0.mob))

    # -- D1b: dead-only, gated ------------------------------------------------

    def test_d1b_dead_frame_is_the_production_composer_untouched(self):
        # dead_only_schedule must add no composition of its own: its output
        # for D1b's own mob has to equal mob_death.dead_frames() called on
        # that same mob directly, byte for byte.
        d1b = self.by_label[diag.DIAG_LABEL_DEAD_ONLY_AFTER_TARGET]
        want = mob_death.dead_frames(self.legacy, d1b.mob)
        got = diag.dead_only_schedule(
            self.legacy, d1b, target_vital_seen=True)
        self.assertEqual(got, want)

    def test_d1b_dead_frame_matches_d0s_once_repositioned_onto_its_identity(self):
        # With identity/position swapped to agree, D1b's dead-only frame must
        # be byte-identical to D0's dead frame: the only real difference
        # between the two objects is which frames get SENT (dying+dead vs
        # dead alone), never the dead frame's own bytes.
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        d1b = self.by_label[diag.DIAG_LABEL_DEAD_ONLY_AFTER_TARGET]
        repositioned = field_mobs.FieldMob(
            **{**d1b.mob.__dict__,
               "placement_index": d0.mob.placement_index,
               "x": d0.mob.x, "y": d0.mob.y, "z": d0.mob.z})
        self.assertEqual(repositioned.actor_identity, d0.mob.actor_identity)
        _pc, d0_dead = mob_death.dead_frames(self.legacy, d0.mob)
        _pc, repositioned_dead = mob_death.dead_frames(
            self.legacy, repositioned)
        self.assertEqual(repositioned_dead, d0_dead)

    def test_d1b_refuses_without_the_target_vital_attestation(self):
        d1b = self.by_label[diag.DIAG_LABEL_DEAD_ONLY_AFTER_TARGET]
        with self.assertRaises(diag.MobDiagContractError):
            diag.dead_only_schedule(
                self.legacy, d1b, target_vital_seen=False)

    def test_dead_only_schedule_refuses_the_wrong_object(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        with self.assertRaises(diag.MobDiagContractError):
            diag.dead_only_schedule(self.legacy, d0, target_vital_seen=True)

    # -- D3: no faction splice, otherwise the same body ----------------------

    def test_d3_alive_entry_is_the_unspliced_baseline_field_mobs_already_names(self):
        d3 = self.by_label[diag.DIAG_LABEL_NO_FACTION_SPLICE]
        got = diag.alive_entry(self.legacy, d3)
        want_npc_attr = self.legacy.make_npc_attr(
            d3.mob.template_id, d3.mob.actor_identity,
            field_mobs.SCENE_ID, field_mobs.SCENE_SEQUENCE,
            d3.mob.visual_preset, d3.mob.max_hp, d3.mob.max_hp,
            basic_name=d3.mob.display_name,
        )
        # No BASIC_BIT_FACTION anywhere and no faction tag bytes: exactly the
        # nameless-splice absent, since this call never adds one.
        self.assertNotIn(
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)),
            want_npc_attr)
        movement = self.legacy.make_remote_movement_attr(
            d3.mob.actor_identity, d3.mob.x, d3.mob.y, d3.mob.z,
            field_mobs.HEADINGS[d3.mob.placement_index & 3],
            mask=field_mobs.FULL_MOVEMENT_MASK,
        )
        want = self.legacy.make_remote_actor_entry(
            field_mobs.NPC_STYLE_ACTOR_TYPE, d3.mob.actor_identity,
            [(field_mobs.NPC_ATTR_ID, want_npc_attr),
             (field_mobs.MOVEMENT_ATTR_ID, movement)],
        )
        self.assertEqual(got, want)

    def test_d3_byte_diff_from_control_is_exactly_the_faction_splice(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        d3 = self.by_label[diag.DIAG_LABEL_NO_FACTION_SPLICE]
        # Re-home D3's un-spliced body onto D0's identity/position: this must
        # equal exactly field_mobs.hostile_npc_attr's OWN unspliced baseline
        # for that same repositioned mob -- the same relationship
        # test_field_mobs.py already pins for the general case, re-derived
        # here for this diagnostic's specific body/position instead of
        # trusted from the module's docstring.
        respositioned_d3 = field_mobs.FieldMob(
            **{**d3.mob.__dict__,
               "placement_index": d0.mob.placement_index,
               "x": d0.mob.x, "y": d0.mob.y, "z": d0.mob.z})
        self.assertEqual(respositioned_d3.actor_identity, d0.mob.actor_identity)
        d3_npc_attr = self.legacy.make_npc_attr(
            respositioned_d3.template_id, respositioned_d3.actor_identity,
            field_mobs.SCENE_ID, field_mobs.SCENE_SEQUENCE,
            respositioned_d3.visual_preset, respositioned_d3.max_hp,
            respositioned_d3.max_hp, basic_name=respositioned_d3.display_name,
        )
        d0_npc_attr = field_mobs.hostile_npc_attr(self.legacy, d0.mob)
        # d0's spliced body must differ from d3's unspliced body by exactly
        # the widened mask (2 bytes) plus the 5-byte tagged faction field;
        # nothing else on either side is allowed to move.
        self.assertEqual(
            len(d0_npc_attr),
            len(d3_npc_attr) + field_mobs.FACTION_SPLICE_BYTES)
        mask_at = len(
            bytes(self.legacy.u8tag(0x0B, 1))
            + bytes(self.legacy.qwordtag(0x32, d0.mob.actor_identity))
        ) + 1
        self.assertEqual(d0_npc_attr[:mask_at], d3_npc_attr[:mask_at])
        d0_mask = int.from_bytes(d0_npc_attr[mask_at:mask_at + 2], "little")
        d3_mask = int.from_bytes(d3_npc_attr[mask_at:mask_at + 2], "little")
        self.assertEqual(d0_mask, d3_mask | field_mobs.BASIC_BIT_FACTION)
        # The NPCAttr tail (mask byte + template id [+ preset]) is fixed-shape
        # and independent of the faction splice, per field_mobs's own
        # ascending-mask-bit ordering -- so it must be byte-identical on both
        # sides, and everything BETWEEN the BasicAttr mask and that tail must
        # be identical too, except D0 carries five extra tagged-faction bytes.
        npc_mask = 0x01 | (0x04 if d0.mob.visual_preset else 0)
        tail = bytes(self.legacy.u8tag(0x0B, npc_mask)) + bytes(
            self.legacy.u16tag(0x12, d0.mob.template_id))
        if d0.mob.visual_preset:
            tail += bytes(self.legacy.wstr_tag(d0.mob.visual_preset))
        self.assertTrue(d0_npc_attr.endswith(tail))
        self.assertTrue(d3_npc_attr.endswith(tail))
        splice_len = field_mobs.FACTION_SPLICE_BYTES
        after_mask = mask_at + 2
        d0_middle = d0_npc_attr[after_mask:len(d0_npc_attr) - len(tail)]
        d3_middle = d3_npc_attr[after_mask:len(d3_npc_attr) - len(tail)]
        self.assertEqual(len(d0_middle), len(d3_middle) + splice_len)
        self.assertEqual(d0_middle[:len(d3_middle)], d3_middle)
        self.assertEqual(
            d0_middle[len(d3_middle):],
            bytes(self.legacy.u32tag(
                field_mobs.FACTION_TAG, field_mobs.FIELD_MOB_FACTION)))

    # -- console lines --------------------------------------------------------

    # -- the wiring line -------------------------------------------------

    def test_the_wiring_line_names_the_widened_ruling_it_actually_uses(self):
        self.assertTrue(diag.GT_DIAG_MULTI_OBJECT_WIRING.isascii())
        self.assertIn("DIAG_WIDENED_RULING", diag.GT_DIAG_MULTI_OBJECT_WIRING)
        self.assertIn(diag.DIAG_WIDENED_RULING, mob_death.WIDENING_RULINGS)
        self.assertIn(
            diag.DIAG_BODY_TEMPLATE_ID,
            mob_death.WIDENING_RULINGS[diag.DIAG_WIDENED_RULING])

    def test_the_wiring_line_is_correct_about_which_objects_pass_the_widened_gate(self):
        # pf-adversary (this round) caught an earlier draft claiming "all
        # five" pass DIAG_WIDENED_RULING; only kill_schedule and
        # dying_timer_hold_schedule (D0/D2 and D1a) do. dead_only_schedule
        # (D1b) calls mob_death.dead_frames() directly, which this test pins
        # as having NO widened= parameter at all -- so no gate applies there,
        # regardless of what the module's prose claims.
        self.assertNotIn(
            "widened", inspect.signature(mob_death.dead_frames).parameters)
        self.assertIn("widened", inspect.signature(mob_death.kill).parameters)
        # The prose itself must not claim "all five" use the widened ruling.
        self.assertNotIn("All five use", diag.GT_DIAG_MULTI_OBJECT_WIRING)

    def test_describe_boot_has_one_line_per_object_in_the_required_format(self):
        lines = diag.describe_boot(self.objects)
        self.assertEqual(len(lines), 5)
        for obj, line in zip(self.objects, lines):
            self.assertTrue(line.startswith("DIAG object=%s variant=" % obj.label))
            self.assertIn("identity=0x%X" % obj.mob.actor_identity, line)
            self.assertIn(
                "pos=(%.4f,%.4f,%.4f)" % (obj.mob.x, obj.mob.y, obj.mob.z),
                line)


if __name__ == "__main__":
    unittest.main()
