"""LANE-A: the per-scene world registry, and the relogin it is meant to fix.

The scenario every test here is a piece of: R309 measured a monster standing
back up at full health after a relogin on a server that never restarted.
``mob_death_persistence`` answers the half where the monster had DIED.  This
file's subject is the half where it had not: a monster left at a third of its
health is healed by the next login, because the only place that number lived
was the ledger of the session that ended.
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout

from src.pirateforce_foundation import mob_combat
from src.pirateforce_foundation import mob_death
from src.pirateforce_foundation import mob_death_persistence
from src.pirateforce_foundation import world_scene_registry


SCENE = "bg0002"
SOLDIER = 0x203D
SECOND = 0x203E
CEILING = 3138


def _ledger(*balances, scene=SCENE):
    """A fresh session ledger the way ``_sync_combat_scene_state`` opens one:

    every monster on the roster at its table's full health.
    """
    rows = balances or (mob_combat.MobBalance(SOLDIER, CEILING, CEILING),)
    return mob_combat.CombatLedger(tuple(rows), 0, scene)


class TheDefectThisFileExistsFor(unittest.TestCase):
    """One scenario, end to end, in the shape the player experiences it."""

    def test_a_wounded_monster_is_still_wounded_for_the_next_session(self):
        registry = world_scene_registry.WorldSceneRegistry()
        # Session one hits it three times and walks away.
        outcome = registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        self.assertTrue(outcome.noted, outcome.reason)

        # Session two opens its own fresh ledger, the way an arrival does:
        # every roster row at the table's full health.
        fresh = _ledger()
        self.assertEqual(fresh.balance_of(SOLDIER).current_hp, CEILING)

        seeded = world_scene_registry.seed_the_session_ledger(
            fresh, SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 900)
        self.assertEqual(seeded.balance_of(SOLDIER).max_hp, CEILING)
        # The caller's own value is untouched: a ledger is a VALUE, and the
        # seed returns a new one rather than mutating the old.
        self.assertEqual(fresh.balance_of(SOLDIER).current_hp, CEILING)

    def test_two_sessions_in_one_scene_read_the_same_health(self):
        """The shared-world criterion, as a comparison of two readings."""
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 512, CEILING)
        first = world_scene_registry.seed_the_session_ledger(
            _ledger(), SCENE, registry=registry, announce=False)
        second = world_scene_registry.seed_the_session_ledger(
            _ledger(), SCENE, registry=registry, announce=False)
        self.assertEqual(first.balance_of(SOLDIER).current_hp,
                         second.balance_of(SOLDIER).current_hp)
        self.assertEqual(first.balance_of(SOLDIER).current_hp, 512)

    def test_without_the_registry_the_monster_heals(self):
        """The baseline, pinned: an empty book changes nothing at all.

        This is also the state of production until the seed and the write
        halves are wired, and it must be a no-op rather than a surprise.
        """
        registry = world_scene_registry.WorldSceneRegistry()
        fresh = _ledger()
        seeded = world_scene_registry.seed_the_session_ledger(
            fresh, SCENE, registry=registry, announce=False)
        self.assertIs(seeded, fresh)


class TheGraveDoor(unittest.TestCase):
    """A dead monster is the OTHER book's row, and this one refuses it."""

    def test_zero_health_is_refused_by_name_at_the_write_door(self):
        registry = world_scene_registry.WorldSceneRegistry()
        outcome = registry.note_balance(SCENE, SOLDIER, 0, CEILING)
        self.assertFalse(outcome.noted)
        self.assertEqual(outcome.reason,
                         world_scene_registry.REFUSE_A_GRAVE_IS_NOT_A_VITAL)
        self.assertEqual(registry.remembered(SCENE), ())

    def test_the_row_type_refuses_a_grave_too(self):
        """No path -- a test, a replay, a future caller -- can build one."""
        with self.assertRaises(ValueError):
            world_scene_registry.MobVital(
                SOLDIER, mob_death.HP_WHEN_DEAD, CEILING)

    def test_a_buried_identity_is_never_stood_back_up(self):
        """The crash this skip prevents is named in mob_death itself.

        ``repopulation_entries`` refuses a ledger that disagrees with its
        register, and the arrival census reaches that refusal from an
        ``else:`` its own ``try`` does not cover.  So a health remembered
        before the kill must not be seeded over a grave, in EITHER call
        order -- which is why the grave book is re-read here rather than
        trusted from the order of two statements in runtime.py.
        """
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)

        deaths = mob_death_persistence.WorldDeaths()

        class _Buried:
            @staticmethod
            def is_buried(scene, identity):
                return identity == SOLDIER

        # The ledger arm the grave seed would already have zeroed.
        dead_in_ledger = _ledger(
            mob_combat.MobBalance(SOLDIER, CEILING, mob_death.HP_WHEN_DEAD))
        seeded = world_scene_registry.seed_the_session_ledger(
            dead_in_ledger, SCENE, registry=registry, deaths=deaths,
            announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp,
                         mob_death.HP_WHEN_DEAD)

        # And the arm where the ledger has NOT been zeroed yet but the world
        # knows the grave: the world's answer still wins.
        not_yet_zeroed = _ledger()
        seeded = world_scene_registry.seed_the_session_ledger(
            not_yet_zeroed, SCENE, registry=registry, deaths=_Buried,
            announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, CEILING)


class WhatTheSeedSkips(unittest.TestCase):

    def test_an_identity_the_ledger_does_not_carry(self):
        """A ledger still open on the scene being LEFT holds no destination row."""
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SECOND, 100, CEILING)
        elsewhere = _ledger()          # carries SOLDIER only
        seeded = world_scene_registry.seed_the_session_ledger(
            elsewhere, SCENE, registry=registry, announce=False)
        self.assertIs(seeded, elsewhere)
        self.assertNotIn(SECOND, seeded.identities())

    def test_a_health_above_the_ledgers_own_ceiling_is_skipped_not_clamped(self):
        """The roster table changed under the world's memory.

        Lowering the number to a ceiling this module guessed at would be an
        invented value on the wire; refusing the row leaves the table's own
        answer standing, which is the honest one.
        """
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 9000, 9000)
        smaller = _ledger(mob_combat.MobBalance(SOLDIER, 100, 100))
        seeded = world_scene_registry.seed_the_session_ledger(
            smaller, SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 100)

    def test_a_row_that_only_remembers_a_position(self):
        registry = world_scene_registry.WorldSceneRegistry()
        self.assertTrue(
            registry.note_position(SCENE, SOLDIER, (1.0, 2.0, 3.0)).noted)
        fresh = _ledger()
        seeded = world_scene_registry.seed_the_session_ledger(
            fresh, SCENE, registry=registry, announce=False)
        self.assertIs(seeded, fresh)

    def test_a_health_that_already_matches_writes_nothing(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, CEILING, CEILING)
        fresh = _ledger()
        seeded = world_scene_registry.seed_the_session_ledger(
            fresh, SCENE, registry=registry, announce=False)
        self.assertIs(seeded, fresh)
        self.assertEqual(seeded.generation, fresh.generation)


class TheDoorsNeverRaise(unittest.TestCase):
    """This book sits on the arrival path; an exception here is a dropped thread."""

    def test_every_write_refusal_is_named(self):
        registry = world_scene_registry.WorldSceneRegistry()
        cases = (
            (registry.note_balance(None, SOLDIER, 1, 2),
             world_scene_registry.REFUSE_BAD_SCENE),
            (registry.note_balance(SCENE, 0, 1, 2),
             world_scene_registry.REFUSE_BAD_IDENTITY),
            (registry.note_balance(SCENE, True, 1, 2),
             world_scene_registry.REFUSE_BAD_IDENTITY),
            (registry.note_balance(SCENE, SOLDIER, "40", 100),
             world_scene_registry.REFUSE_BAD_HP),
            (registry.note_balance(SCENE, SOLDIER, 200, 100),
             world_scene_registry.REFUSE_BAD_HP),
            (registry.note_position(SCENE, SOLDIER, (1.0, 2.0)),
             world_scene_registry.REFUSE_BAD_POSITION),
            (registry.note_position(SCENE, SOLDIER, (float("inf"), 0.0, 0.0)),
             world_scene_registry.REFUSE_BAD_POSITION),
            (registry.note_position(SCENE, SOLDIER, (float("nan"), 0.0, 0.0)),
             world_scene_registry.REFUSE_BAD_POSITION),
            (registry.note_position(SCENE, SOLDIER, "here"),
             world_scene_registry.REFUSE_BAD_POSITION),
        )
        for outcome, expected in cases:
            with self.subTest(reason=expected):
                self.assertFalse(outcome.noted)
                self.assertEqual(outcome.reason, expected)
        self.assertEqual(registry.remembered(SCENE), ())

    def test_the_seed_hands_back_the_callers_own_object(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        not_a_ledger = object()
        self.assertIs(
            world_scene_registry.seed_the_session_ledger(
                not_a_ledger, SCENE, registry=registry, announce=False),
            not_a_ledger)
        fresh = _ledger()
        self.assertIs(
            world_scene_registry.seed_the_session_ledger(
                fresh, None, registry=registry, announce=False),
            fresh)

    def test_a_book_that_raises_costs_the_caller_nothing(self):
        class _Hostile:
            @staticmethod
            def remembered(scene):
                raise RuntimeError("the book is on fire")

        fresh = _ledger()
        self.assertIs(
            world_scene_registry.seed_the_session_ledger(
                fresh, SCENE, registry=_Hostile, announce=False),
            fresh)

    def test_a_grave_book_that_raises_costs_the_caller_nothing(self):
        class _Hostile:
            @staticmethod
            def is_buried(scene, identity):
                raise RuntimeError("no")

        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        fresh = _ledger()
        seeded = world_scene_registry.seed_the_session_ledger(
            fresh, SCENE, registry=registry, deaths=_Hostile, announce=False)
        # ALL OR NOTHING: the caller's own ledger, not a half-seeded one.
        self.assertIs(seeded, fresh)

    def test_the_view_survives_three_broken_books(self):
        class _Hostile:
            @staticmethod
            def remembered(scene):
                raise RuntimeError("no")

            @staticmethod
            def buried_in(scene):
                raise RuntimeError("no")

            @staticmethod
            def standing(scene):
                raise RuntimeError("no")

        scene_view = world_scene_registry.view(
            SCENE, registry=_Hostile, deaths=_Hostile, ground=_Hostile)
        self.assertTrue(scene_view.is_empty)
        self.assertEqual(scene_view.scene, SCENE)
        self.assertEqual(
            world_scene_registry.view(None, registry=_Hostile).scene, "")


class TheBookItself(unittest.TestCase):

    def test_one_scene_two_spellings(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance("Bg0002", SOLDIER, 900, CEILING)
        self.assertEqual(len(registry.remembered("bg0002")), 1)
        self.assertEqual(registry.scenes(), ("bg0002",))

    def test_health_and_position_are_written_independently(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        registry.note_position(SCENE, SOLDIER, (10.0, 20.0, 30.0))
        row = registry.remembered_one(SCENE, SOLDIER)
        self.assertEqual(row.current_hp, 900)
        self.assertEqual(row.position, (10.0, 20.0, 30.0))
        registry.note_balance(SCENE, SOLDIER, 400, CEILING)
        row = registry.remembered_one(SCENE, SOLDIER)
        self.assertEqual(row.current_hp, 400)
        self.assertEqual(row.position, (10.0, 20.0, 30.0))

    def test_forget_is_the_respawn_door(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        self.assertTrue(registry.forget(SCENE, SOLDIER))
        self.assertFalse(registry.forget(SCENE, SOLDIER))
        self.assertEqual(registry.remembered(SCENE), ())
        self.assertEqual(registry.scenes(), ())
        self.assertFalse(registry.forget(None, SOLDIER))

    def test_the_cap_refuses_by_name_and_keeps_what_it_has(self):
        registry = world_scene_registry.WorldSceneRegistry(vitals_per_scene=1)
        self.assertTrue(registry.note_balance(SCENE, SOLDIER, 900, CEILING).noted)
        refused = registry.note_balance(SCENE, SECOND, 900, CEILING)
        self.assertEqual(refused.reason,
                         world_scene_registry.REFUSE_SCENE_IS_FULL)
        self.assertEqual(len(registry.remembered(SCENE)), 1)
        # A row already held is still writable when the scene is full: the
        # cap bounds how many monsters are remembered, not how often one
        # takes a hit.
        self.assertTrue(registry.note_balance(SCENE, SOLDIER, 800, CEILING).noted)
        self.assertEqual(registry.remembered_one(SCENE, SOLDIER).current_hp, 800)

    def test_a_bad_cap_is_refused_at_construction(self):
        for bad in (0, -1, True, 1.5, "many"):
            with self.subTest(cap=bad):
                with self.assertRaises(ValueError):
                    world_scene_registry.WorldSceneRegistry(vitals_per_scene=bad)

    def test_rows_come_back_sorted_and_immutable(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SECOND, 10, CEILING)
        registry.note_balance(SCENE, SOLDIER, 20, CEILING)
        rows = registry.remembered(SCENE)
        self.assertEqual([row.actor_identity for row in rows],
                         [SOLDIER, SECOND])
        with self.assertRaises(Exception):
            rows[0].current_hp = 1

    def test_the_process_registry_is_built_once_and_only_takes_a_registry(self):
        first = world_scene_registry.world_scene_registry()
        self.assertIs(first, world_scene_registry.world_scene_registry())
        with self.assertRaises(ValueError):
            world_scene_registry.install_world_scene_registry(object())
        self.assertIs(world_scene_registry.world_scene_registry(), first)


class TheConsoleLines(unittest.TestCase):
    """The bridge console is cp874: every line is ASCII by construction."""

    def test_every_line_is_ascii_and_names_its_subject(self):
        registry = world_scene_registry.WorldSceneRegistry()
        lines = [
            world_scene_registry.describe_noted(
                registry.note_balance(SCENE, SOLDIER, 900, CEILING)),
            world_scene_registry.describe_noted(
                registry.note_balance(SCENE, SOLDIER, 0, CEILING)),
            world_scene_registry.describe_noted(
                registry.note_balance(None, SOLDIER, 1, 2)),
            world_scene_registry.describe_seeded(
                world_scene_registry.SeedOutcome(SCENE, None, (SOLDIER,), 2)),
            world_scene_registry.describe_seeded(
                world_scene_registry.SeedOutcome(
                    SCENE, None, (), 0,
                    world_scene_registry.REFUSE_NOT_A_LEDGER)),
            world_scene_registry.describe_view(
                world_scene_registry.view(SCENE, registry=registry)),
        ]
        for line in lines:
            with self.subTest(line=line[:40]):
                line.encode("ascii")
                self.assertTrue(line.startswith("WORLD_REGISTRY_"), line)
        self.assertIn("hp=900/3138", lines[0])
        self.assertIn("reason=a_grave_is_not_a_vital", lines[1])
        self.assertIn("monsters=1 skipped=2", lines[3])
        self.assertIn("monsters=1 graves=0 ground=0", lines[5])

    def test_no_describe_can_raise_on_a_shape_it_did_not_expect(self):
        for describe in (world_scene_registry.describe_noted,
                         world_scene_registry.describe_seeded,
                         world_scene_registry.describe_view):
            with self.subTest(describe=describe.__name__):
                line = describe(object())
                line.encode("ascii")
                self.assertTrue(line.startswith("WORLD_REGISTRY_"), line)

    def test_the_seed_is_silent_when_the_scene_is_untouched(self):
        registry = world_scene_registry.WorldSceneRegistry()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            world_scene_registry.seed_the_session_ledger(
                _ledger(), SCENE, registry=registry)
        self.assertEqual(buffer.getvalue(), "")

    def test_the_seed_speaks_when_it_did_something(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            world_scene_registry.seed_the_session_ledger(
                _ledger(), SCENE, registry=registry)
        self.assertIn("WORLD_REGISTRY_SEEDED scene=bg0002 monsters=1",
                      buffer.getvalue())


class TheWiringAsk(unittest.TestCase):

    def test_the_pasteable_call_site_names_the_function_it_asks_for(self):
        text = world_scene_registry.WORLD_REGISTRY_SEED_WIRING
        self.assertIn("seed_the_session_ledger", text)
        self.assertIn("self.mob_combat_ledger", text)
        self.assertIn("from . import world_scene_registry", text)
        text.encode("ascii")


if __name__ == "__main__":
    unittest.main()
