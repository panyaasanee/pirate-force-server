"""LANE-B: tests for src/pirateforce_foundation/mob_combat_bg0015_gates.py.

REWRITTEN IN ROUND 6cm6ry after pf-adversary broke the first draft's tests
as well as its claims.  What each test here exists to stop:

``test_a_real_swing_in_scene_14_answers_not_a_field_mob`` drives the REAL
wired path (login -> StartGame -> scene 14 -> ActionVital on each of the 12
splice identities) and asserts the event the runtime actually appends.  The
first draft asserted ``target_not_in_ledger``, a refusal that call site
cannot emit, and "measured" it by calling ``balance_of`` on an empty ledger
-- which answers the same way for ``0xDEADBEEF``, so it carried no
information about Bg0015 at all.

``test_splice_identities_are_all_backed_by_lane_As_own_census`` cross-checks
lane B's splice dict against lane A's independently built 81-actor
generation.  The first draft compared ``scene14_hostile_roster()`` with
itself; shifting eleven of the twelve placement indices by +100 left it
green with eleven fabricated identities.
``test_fabricated_placements_are_caught_by_the_independent_check`` is that
exact mutation, run as a test, so the check cannot rot back into a
tautology.

``test_there_are_no_live_cross_scene_collisions_today`` pins the fact the
first draft got backwards from a historical docstring: HEAD has NONE, so
registering Bg0015 would create the first one rather than joining an
accepted class.

The gate tests pin all four gates measured shut, so the day any one opens
this file goes red and the module's own docstring has to be rewritten.
"""
from __future__ import annotations

import contextlib
import dataclasses
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mob_hostile_bg0015 as hostile_bg0015
from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_combat_bg0015_gates as gates
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_scene_recompose
from pirateforce_foundation import world_population_bg0015
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.runtime import make_state_class
from pirateforce_foundation.store import SQLiteStore

MODULE_PATH = SRC / "pirateforce_foundation" / "mob_combat_bg0015_gates.py"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# The twelve numbers LANE-A's design letter (20260831_2007) measured
# independently of this lane, already cross-checked in
# tests/test_field_mob_hostile_bg0015.py. Repeated here as literals on
# purpose: a check that reads both sides out of the same table cannot
# notice the table itself being wrong.
LANE_A_MEASURED_IDENTITIES = (
    0x2017, 0x2019, 0x201C, 0x201E, 0x2020, 0x202D,
    0x202E, 0x202F, 0x2030, 0x2034, 0x2047, 0x2058,
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class Bg0015GateMeasurementTests(unittest.TestCase):
    """The cheap half: measurements that need no session."""

    def setUp(self) -> None:
        self.legacy = _legacy()

    def test_all_four_gates_are_shut_today(self) -> None:
        self.assertFalse(gates.roster_gate_open())
        self.assertFalse(gates.death_ruling_gate_open())
        self.assertFalse(gates.recompose_gate_open())
        self.assertEqual(gates.scene14_roster_size_today(), 0)
        self.assertEqual(
            gates.closed_gates(),
            (gates.GATE_ROSTER_REGISTRATION, gates.GATE_APPROVED_IMPORTER,
             gates.GATE_DEATH_RULING, gates.GATE_SCENE_RECOMPOSE),
        )
        # Every gate names an owner: a gate with no owner is a gate nobody
        # moves, which is how this round's first draft nearly shipped a
        # three-owner problem described as one lane's edit.
        for gate in gates.closed_gates():
            self.assertIn(gate, gates.GATE_OWNERS)

    def test_gate_three_is_measured_against_the_real_death_predicate(
            self) -> None:
        refused = gates.templates_without_a_death_ruling()
        self.assertEqual(refused, (343, 345, 348, 350, 353, 355, 924))
        # Not a hand-typed list: every row really does raise today.
        for mob in hostile_bg0015.scene14_hostile_roster():
            with self.assertRaises(mob_death.MobDeathContractError) as ctx:
                mob_death.ruling_for(mob)
            self.assertEqual(
                ctx.exception.reason, "target_outside_the_sanctioned_scope")

    def test_gate_four_is_measured_against_the_real_composer_table(
            self) -> None:
        self.assertEqual(mob_scene_recompose.composer_scene_ids(), (1, 2))
        self.assertNotIn(
            gates.SCENE14_SCENE_ID, mob_scene_recompose.composer_scene_ids())

    def test_splice_identities_come_from_the_visual_path(self) -> None:
        spliced = gates.splice_identities(self.legacy)
        self.assertEqual(spliced, LANE_A_MEASURED_IDENTITIES)
        # ...and they are the keys of the real override dict, not a reread
        # of the roster: same call chief's future branch will make.
        self.assertEqual(
            set(spliced),
            set(hostile_bg0015.scene14_hostile_overrides(self.legacy)),
        )

    def test_splice_identities_are_all_backed_by_lane_As_own_census(
            self) -> None:
        generation = world_population_bg0015.build_bg0015_population(
            self.legacy, (0.0, 0.0, 0.0),
            world_population_bg0015.ROSTER_COUNT, scene_id=14,
            count_source=world_population_bg0015.COUNT_SOURCE_FULL_ROSTER,
        )
        # The premise this round had to correct: scene 14 is not empty and
        # not waiting on the splice to have bodies in it. Lane A ships this
        # whole census to a real client today.
        self.assertEqual(generation.actor_count, 81)
        self.assertEqual(len(generation.actor_identities), 81)
        missing = gates.splice_identities_missing_from(
            generation.actor_identities, self.legacy)
        self.assertEqual(
            missing, (),
            "a spliced identity lane A never ships would decorate a body "
            "the client was never sent")

    def test_fabricated_placements_are_caught_by_the_independent_check(
            self) -> None:
        # pf-adversary's own mutation, kept as a test: shift eleven of the
        # twelve identities out of lane A's census and the check must go
        # red. The first draft's roster-vs-roster comparison stayed green
        # through exactly this.
        real = gates.splice_identities(self.legacy)
        fabricated = set(real[:1]) | {identity + 0x100 for identity in real[1:]}
        generation_identities = world_population_bg0015.\
            build_bg0015_population(
                self.legacy, (0.0, 0.0, 0.0),
                world_population_bg0015.ROSTER_COUNT, scene_id=14,
                count_source=world_population_bg0015.COUNT_SOURCE_FULL_ROSTER,
            ).actor_identities
        still_backed = [i for i in fabricated if i in set(generation_identities)]
        self.assertEqual(
            len(still_backed), 1,
            "eleven fabricated identities must fall outside lane A's census")

    def test_an_empty_external_set_is_refused_rather_than_reported(
            self) -> None:
        with self.assertRaises(gates.MobCombatBg0015GateError):
            gates.splice_identities_missing_from((), self.legacy)

    def test_there_are_no_live_cross_scene_collisions_today(self) -> None:
        # The fact the first draft of this module got backwards. Two other
        # tests already assert this emptiness
        # (tests/test_field_mobs.py::test_default_set_is_the_two_live_known_
        # scenes_only and tests/test_mob_death.py's own stand-in note); it is
        # repeated here because THIS module's framing depends on it.
        self.assertEqual(gates.live_cross_scene_collisions_today(), ())

    def test_the_one_collision_registration_would_create(self) -> None:
        # Not novel as a fact: tests/test_field_mobs.py::test_all_three_
        # known_tables_together_find_one_pairwise_collision (round ua236k)
        # already pins placement 87 / templates 34 vs 924 / exactly one.
        # What this adds is the LIVE, owner-filtered reading of the Bg0002
        # side, which the raw-table test does not use.
        self.assertEqual(gates.bg0002_bg0015_identity_collisions(), (0x2058,))
        bg0015_row = next(
            mob for mob in hostile_bg0015.scene14_hostile_roster()
            if mob.actor_identity == 0x2058)
        bg0002_row = next(
            mob for mob in field_mobs.roster_for_scene_id(
                gates.BG0002_SCENE_ID)
            if mob.actor_identity == 0x2058)
        self.assertEqual(
            (bg0015_row.placement_index, bg0002_row.placement_index), (87, 87))
        self.assertEqual(
            (bg0002_row.template_id, bg0015_row.template_id), (34, 924))

    def test_the_owner_refusal_divergence_is_named_not_assumed(self) -> None:
        # load_roster filters OWNER_REFUSED_PLACEMENTS; the splice roster
        # does not. They agree for Bg0015 only because Bg0015 has no
        # refusals today -- true by data, not by construction.
        self.assertEqual(gates.owner_refused_placements_for_scene14(), ())
        self.assertEqual(
            field_mobs.OWNER_REFUSED_PLACEMENTS.get("Bg0002"),
            (89, 90, 92, 93, 94, 95, 96, 97),
            "Bg0002 is the worked example that this filter really removes "
            "rows -- if this changes, the Bg0015 agreement above needs "
            "re-measuring rather than re-asserting")

    def test_this_module_does_not_import_the_raw_table_module(self) -> None:
        text = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("field_mob_tables_bg0015", text)

    def test_importing_this_module_registers_nothing(self) -> None:
        before = field_mobs.live_scenes()
        import importlib
        importlib.reload(gates)
        self.assertEqual(field_mobs.live_scenes(), before)
        self.assertEqual(set(before), {"bg0001", "Bg0002"})


class Bg0015WiredAnswerTests(unittest.TestCase):
    """The expensive half: what the REAL dispatch answers in scene 14.

    Same harness shape tests/test_scene_scoped_combat_wiring.py uses (login
    -> create -> StartGame -> scene surgery -> ActionVital), because what is
    under test is the dispatch's answer, not any travel lane.
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(1, 0, self.legacy.V135_PLAYER_X,
                     self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _state_in_scene_14(self, token):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector)
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        with contextlib.redirect_stdout(io.StringIO()):
            state.dispatch(self.legacy.parse_outer(
                self.legacy._synthetic_start_game_pc(character.selector)))
        state.teleport_sent = True
        state.runtime_ack_sent = True
        state.welcome_message_sent = True
        state.current_scene_music_sent = True
        selected = state.foundation.selected
        state.foundation.selected = dataclasses.replace(
            selected,
            position=dataclasses.replace(selected.position, scene_id=14),
        )
        return state

    def _action_vital_pc(self, target_identity):
        legacy = self.legacy
        body = (
            legacy.qwordtag(0x32, 0)
            + legacy.qwordtag(0x32, target_identity)
            + legacy.qwordtag(0x32, 0)
            + legacy.u32tag(0x14, 0)
            + legacy.u32tag(0x19, 0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.f32tag(0.0) + legacy.f32tag(0.0)
            + legacy.u8tag(0x0B, 0)
            + legacy.u16tag(0x12, 0)
            + legacy.u8tag(0x0B, 0)
        )
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.ACTION_VITAL)
            + legacy.u8tag(0x0B, 0)
            + body
        )

    def _attack(self, state, target_identity):
        with contextlib.redirect_stdout(io.StringIO()):
            return state.dispatch(self.legacy.parse_outer(
                self._action_vital_pc(target_identity)))

    def test_a_real_swing_in_scene_14_answers_not_a_field_mob(self) -> None:
        state = self._state_in_scene_14("bg0015_gates_wired")
        spliced = gates.splice_identities(self.legacy)
        self.assertEqual(len(spliced), 12)
        for identity in spliced:
            self._attack(state, identity)
        answers = [
            event for event in state.events
            if event.startswith("mob_combat_")
        ]
        self.assertEqual(
            answers.count(gates.WIRED_ANSWER_FOR_A_TABLELESS_SCENE), 12,
            "every swing at a scene-14 actor must answer with the "
            "not-a-field-mob silence: %r" % (answers,))
        # The refusal the first draft of this module named must NOT appear:
        # attack_from_observed_action walks the roster first, so a target
        # that is in the roster and missing from the ledger is
        # unconstructable at this call site.
        self.assertNotIn(
            "mob_combat_refused_%s_no_reply"
            % mob_combat.REFUSE_TARGET_NOT_IN_LEDGER,
            state.events)
        for event in state.events:
            self.assertNotIn(mob_combat.REFUSE_TARGET_NOT_IN_LEDGER, event)
        # And the cause is the ROSTER, not the ledger: both are empty here
        # because both came from the same load_roster call.
        self.assertEqual(state.mob_combat_ledger.identities(), ())
        self.assertEqual(gates.scene14_roster_size_today(), 0)
        # Prove the session really is in scene 14 rather than answering
        # from somewhere else: the sync records the folder it opened on,
        # and bg0001 (the boot scene) would have four ledger rows, not zero.
        self.assertEqual(state.mob_combat_scene_folder, gates.BG0015_FOLDER)
        self.assertEqual(len(field_mobs.load_roster()), 4)


if __name__ == "__main__":
    unittest.main()
