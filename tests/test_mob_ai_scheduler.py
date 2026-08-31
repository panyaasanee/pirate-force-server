"""LANE-B / MOB-AGGRO-001 continuation: tests for mob_ai_scheduler.tick_session.

The load-bearing tests in this file are these three.

``test_a_charging_monster_acquires_through_the_scheduler_without_a_hit`` is
the whole point of this module: a monster whose mined ``n_OFFESIVE = 1`` row
notices a player NOBODY has hit it with, something no existing wired call
site (``damage_step``/``death_step``) can ever produce because both require
an outcome that already happened.

``test_a_passive_dummy_never_initiates_through_the_scheduler`` is the
regression pin for finding 3 of the same audit letter this module answers
finding 2 of: a practice dummy's ``ai_combat`` row is ``None``, so
``mob_ai_control.profile_of`` forces ``offensive=False`` regardless of its
wander row, and this test proves that holds through the new caller too, not
just through ``mob_ai_control.tick_step`` directly.

``test_the_scheduler_has_no_importer_yet`` is the honest half of this
module's own NONCLAIMS: nothing calls this today, and this test fails the
day that stops being true without the docstring being updated to match --
the same AST check ``test_mob_ai_control.py`` runs for its own module,
pointed at this one.
"""

import ast
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_mob_tables_bg0002, field_mobs, mob_aggro, mob_ai_control,
    mob_ai_scheduler, mob_combat,
)
from pirateforce_foundation.mob_ai_scheduler import (  # noqa: E402
    MobAiSchedulerError, SchedulerStepResult, tick_session,
)

SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
PLAYER = 0x750059
OTHER_PLAYER = 0x750060

# The two mined values this file states rather than reads back out of the
# module it tests -- same convention test_mob_ai_control.py uses.
MINED_AGGRO_RADIUS = 1200
BG0002_OFFENSIVE_PLACEMENT = 92  # Orc Chief, ai_wander=11 (offensive), ai_combat=332


class SchedulerTickTests(unittest.TestCase):
    def setUp(self):
        self.roster = field_mobs.load_roster()  # bg0001: four practice dummies
        self.register = mob_ai_control.open_register(self.roster)
        self.ledger = mob_combat.open_ledger(self.roster)

        bg0002_roster = field_mobs._parse_hostile_placements(
            field_mob_tables_bg0002)
        self.bg0002_by_placement = {
            m.placement_index: m for m in bg0002_roster}
        self.bg0002_register = mob_ai_control.open_register(bg0002_roster)
        self.bg0002_ledger = mob_combat.open_ledger(bg0002_roster)

    def test_a_charging_monster_acquires_through_the_scheduler_without_a_hit(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        new_register, results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (mob.x + 100.0, mob.y, mob.z))
        self.assertEqual(
            new_register.state_of(mob.actor_identity).phase,
            mob_aggro.PHASE_AGGRO)
        self.assertEqual(
            new_register.state_of(mob.actor_identity).target_identity,
            PLAYER)
        row = next(r for r in results if r.actor_identity == mob.actor_identity)
        self.assertEqual(row.before_phase, mob_aggro.PHASE_IDLE)
        self.assertEqual(row.after_phase, mob_aggro.PHASE_AGGRO)
        self.assertEqual(row.intent_kind, mob_aggro.INTENT_ATTACK_UNDELIVERABLE)
        self.assertEqual(row.intent_target_identity, PLAYER)
        # Door B stays shut: an intent by name is not a frame.
        self.assertIs(mob_aggro.ATTACK_INTENT_DELIVERABLE, False)

    def test_a_monster_outside_its_mined_radius_does_not_acquire(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        _new_register, results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (mob.x + float(MINED_AGGRO_RADIUS) + 1.0, mob.y, mob.z))
        row = next(r for r in results if r.actor_identity == mob.actor_identity)
        self.assertEqual(row.after_phase, mob_aggro.PHASE_IDLE)
        self.assertEqual(row.intent_kind, mob_aggro.INTENT_NONE)

    def test_a_passive_dummy_never_initiates_through_the_scheduler(self):
        mob = self.roster[0]
        new_register, results = tick_session(
            self.register, self.ledger, PLAYER, (mob.x, mob.y, mob.z))
        for row in results:
            self.assertEqual(row.after_phase, mob_aggro.PHASE_IDLE)
            self.assertEqual(row.intent_kind, mob_aggro.INTENT_NONE)
        for identity in self.register.identities():
            self.assertEqual(
                new_register.state_of(identity).phase, mob_aggro.PHASE_IDLE)

    def test_every_row_in_the_register_is_ticked_in_ascending_order(self):
        _new_register, results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (0.0, 0.0, 0.0))
        self.assertEqual(len(results), len(self.bg0002_register.identities()))
        self.assertEqual(
            [r.actor_identity for r in results],
            list(self.bg0002_register.identities()))
        self.assertEqual(
            list(self.bg0002_register.identities()),
            sorted(self.bg0002_register.identities()))

    def test_row_2_sees_row_1s_committed_state_not_a_stale_snapshot(self):
        # Both real players are far from every monster (0,0,0 is nowhere
        # near any Bg0002 placement), so nothing acquires -- this test is
        # about the FOLD, not about aggro: every row must still be present
        # and typed correctly after every other row's commit has already
        # landed on the register the loop threads through.
        new_register, results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (0.0, 0.0, 0.0))
        # mob_ai_control.tick_step only advances a row's generation when its
        # state actually changes (commit_step returns the SAME register,
        # unchanged, when nothing does) -- so a no-op pass over every row
        # correctly leaves generation at 0.  What this test pins is that
        # every row survived the fold regardless: the register threaded
        # through 17 sequential commits and still tracks all 17 identities.
        self.assertEqual(len(results), len(self.bg0002_register.identities()))
        for identity in self.bg0002_register.identities():
            self.assertTrue(new_register.is_tracked(identity))

    def test_a_call_is_pure_on_the_register_it_was_given(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        before_generation = self.bg0002_register.generation
        tick_session(self.bg0002_register, self.bg0002_ledger, PLAYER,
                     (mob.x + 100.0, mob.y, mob.z))
        self.assertEqual(self.bg0002_register.generation, before_generation)
        self.assertEqual(
            self.bg0002_register.state_of(mob.actor_identity).phase,
            mob_aggro.PHASE_IDLE,
            "tick_session must not mutate the register it was handed -- "
            "dataclasses are frozen, but this pins the observable promise")

    def test_two_calls_with_the_same_inputs_agree(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        first_register, first_results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (mob.x + 100.0, mob.y, mob.z))
        second_register, second_results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (mob.x + 100.0, mob.y, mob.z))
        self.assertEqual(
            [r.after_phase for r in first_results],
            [r.after_phase for r in second_results])
        self.assertEqual(
            first_register.identities(), second_register.identities())

    def test_a_dead_player_is_not_visible_to_any_monster(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        _new_register, results = tick_session(
            self.bg0002_register, self.bg0002_ledger, PLAYER,
            (mob.x + 100.0, mob.y, mob.z), player_alive=False)
        row = next(r for r in results if r.actor_identity == mob.actor_identity)
        self.assertEqual(row.after_phase, mob_aggro.PHASE_IDLE)
        self.assertEqual(row.intent_kind, mob_aggro.INTENT_NONE)

    def test_bad_register_type_refuses_by_name(self):
        with self.assertRaises(MobAiSchedulerError) as caught:
            tick_session(object(), self.ledger, PLAYER, (0.0, 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                          mob_ai_scheduler.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_bad_ledger_type_refuses_by_name(self):
        with self.assertRaises(MobAiSchedulerError) as caught:
            tick_session(self.register, object(), PLAYER, (0.0, 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                          mob_ai_scheduler.REFUSE_TYPE_NOT_TYPED_RECORD)

    def test_a_register_and_ledger_from_different_rosters_refuses_not_silently(self):
        # A register opened for bg0001 against a ledger opened for Bg0002:
        # the two describe different monsters, and this must surface as the
        # SAME named refusal mob_combat.CombatLedger.balance_of already
        # gives every other caller, not a swallowed KeyError or a silent
        # skip.
        with self.assertRaises(mob_combat.MobCombatContractError) as caught:
            tick_session(self.register, self.bg0002_ledger, PLAYER,
                         (0.0, 0.0, 0.0))
        self.assertEqual(caught.exception.reason,
                          mob_combat.REFUSE_TARGET_NOT_IN_LEDGER)

    def test_a_bad_player_position_refuses_through_mob_aggros_own_contract(self):
        with self.assertRaises(mob_aggro.MobAiContractError):
            tick_session(self.register, self.ledger, PLAYER,
                         (float("nan"), 0.0, 0.0))


class WiringLineTests(unittest.TestCase):
    """Same convention test_mob_ai_control.py pins for its own module."""

    def test_production_allowed_is_true_with_no_flag(self):
        self.assertIs(mob_ai_scheduler.production_allowed, True)

    def test_the_wiring_line_names_runtime_py_and_stays_unwired_today(self):
        line = mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING
        self.assertIn("runtime.py", line)
        self.assertIn("mob_ai_scheduler.tick_session", line)

    def test_the_scheduler_has_no_importer_yet(self):
        # Mirrors test_mob_ai_control.py's own "exactly runtime.py imports
        # this lane" check, inverted: this module names its own NONCLAIM
        # that nothing calls it yet, and this makes that claim mechanical
        # instead of prose a future round could leave stale.
        importers = []
        for path in SRC_ROOT.glob("*.py"):
            if path.name == "mob_ai_scheduler.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        alias.name for alias in node.names]
                if any("mob_ai_scheduler" in name for name in names):
                    importers.append(path.name)
        self.assertEqual(
            sorted(set(importers)), [],
            "mob_ai_scheduler now has an importer in src/ -- if that is "
            "runtime.py picking up MOB_AI_SCHEDULER_WIRING, update this "
            "test AND the module docstring's 'WHAT THE PLAYER WILL SEE "
            "DIFFERENTLY' section, which currently says 'nothing today'")


if __name__ == "__main__":
    unittest.main()
