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
import pathlib
import threading
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


class TheLedgerMustBelongToThisScene(unittest.TestCase):
    """D1, pf-adversary round `tz2rgc`: the identity check is NOT enough.

    ``field_mobs`` identities are ``0x2000 + placement + 1`` with no scene
    term, so two different monsters in two different scenes really do carry
    the same wire identity -- measured at this round's HEAD: eight of this
    game's fifteen live-scene pairs share at least one.  Seeding on identity alone wrote
    one scene's remaining health under another scene's ceiling and printed a
    green line over it.
    """

    def test_a_ledger_open_on_another_scene_is_refused_whole(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance("bg0004", SOLDIER, 12, 38728)
        elsewhere = _ledger(scene="Bg0003")
        seeded = world_scene_registry.seed_the_session_ledger(
            elsewhere, "bg0004", registry=registry, announce=False)
        self.assertIs(seeded, elsewhere)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, CEILING)

    def test_the_refusal_is_named_on_the_console(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance("bg0004", SOLDIER, 12, 38728)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            world_scene_registry.seed_the_session_ledger(
                _ledger(scene="Bg0003"), "bg0004", registry=registry)
        self.assertIn("reason=another_scenes_ledger", buffer.getvalue())

    def test_a_ledger_with_no_scene_on_it_is_refused_too(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        # ``None`` is the only untagged ledger this project can build --
        # ``CombatLedger`` itself refuses "" and a non-str at construction,
        # which is checked here so that a future widening of that rule
        # cannot quietly widen what this seed accepts either.
        for tag in ("", 17):
            with self.subTest(refused_at_construction=tag):
                with self.assertRaises(mob_combat.MobCombatContractError):
                    mob_combat.CombatLedger(
                        (mob_combat.MobBalance(SOLDIER, CEILING, CEILING),),
                        0, tag)
        nameless = mob_combat.CombatLedger(
            (mob_combat.MobBalance(SOLDIER, CEILING, CEILING),), 0, None)
        seeded = world_scene_registry.seed_the_session_ledger(
            nameless, SCENE, registry=registry, announce=False)
        self.assertIs(seeded, nameless)

    def test_the_same_scene_spelled_differently_still_seeds(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance("bg0002", SOLDIER, 900, CEILING)
        seeded = world_scene_registry.seed_the_session_ledger(
            _ledger(scene="Bg0002"), "BG0002", registry=registry,
            announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 900)


class WhatTheSeedSkips(unittest.TestCase):
    """Each skip must leave the REST of the scene seeded.

    Every test here carries a second, good row and asserts it landed.  That
    is not decoration: pf-adversary (round `tz2rgc`, D4) measured the first
    draft of these three tests passing unchanged when the skip they name was
    DELETED -- because deleting it made the whole seed collapse into the
    `except` arm, which returns the caller's own ledger, which was the only
    thing they asserted.  "The bad row was skipped" and "every row was
    abandoned" have to be told apart, so the good row is the witness.
    """

    def _registry_with_a_good_row(self):
        registry = world_scene_registry.WorldSceneRegistry()
        self.assertTrue(registry.note_balance(SCENE, SOLDIER, 900, CEILING).noted)
        return registry

    def _ledger_of_two(self):
        return _ledger(
            mob_combat.MobBalance(SOLDIER, CEILING, CEILING),
            mob_combat.MobBalance(SECOND, CEILING, CEILING))

    def test_an_identity_the_ledger_does_not_carry(self):
        """A roster that shrank under the world's memory."""
        registry = self._registry_with_a_good_row()
        registry.note_balance(SCENE, 0x20FF, 100, CEILING)
        seeded = world_scene_registry.seed_the_session_ledger(
            self._ledger_of_two(), SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 900)
        self.assertNotIn(0x20FF, seeded.identities())

    def test_a_health_above_the_ledgers_own_ceiling_is_skipped_not_clamped(self):
        """The roster table changed under the world's memory.

        Lowering the number to a ceiling this module guessed at would be an
        invented value on the wire; refusing the row leaves the table's own
        answer standing, which is the honest one -- and the OTHER monster in
        the same scene is still seeded.
        """
        registry = self._registry_with_a_good_row()
        registry.note_balance(SCENE, SECOND, 9000, 9000)
        seeded = world_scene_registry.seed_the_session_ledger(
            self._ledger_of_two(), SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SECOND).current_hp, CEILING)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 900)

    def test_a_row_that_only_remembers_a_position(self):
        registry = self._registry_with_a_good_row()
        self.assertTrue(
            registry.note_position(SCENE, SECOND, (1.0, 2.0, 3.0)).noted)
        seeded = world_scene_registry.seed_the_session_ledger(
            self._ledger_of_two(), SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SECOND).current_hp, CEILING)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, 900)

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


class TheLockIsLoadBearing(unittest.TestCase):
    """A book whose whole premise is one process, many sessions, must be safe
    for many threads.  pf-adversary (round `tz2rgc`, D4) measured the
    unlocked version losing 69,227 updates in one run of this shape; with the
    lock it loses none.  A merge of two independent fields (health, position)
    is exactly where a read-modify-write would drop one.
    """

    def test_two_writers_and_a_reader_never_see_a_field_go_backwards(self):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 1, 200000)
        registry.note_position(SCENE, SOLDIER, (0.0, 0.0, 0.0))
        done = threading.Event()
        reversals = []

        def health():
            for hp in range(1, 20000):
                registry.note_balance(SCENE, SOLDIER, hp, 200000)
            done.set()

        def position():
            step = 0
            while not done.is_set():
                registry.note_position(SCENE, SOLDIER, (float(step), 0.0, 0.0))
                step += 1

        def reader():
            highest = 0
            while not done.is_set():
                row = registry.remembered_one(SCENE, SOLDIER)
                if row is not None and row.current_hp is not None:
                    if row.current_hp < highest:
                        reversals.append(row.current_hp)
                    highest = max(highest, row.current_hp)

        threads = [threading.Thread(target=f)
                   for f in (health, position, reader)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual(reversals, [])
        row = registry.remembered_one(SCENE, SOLDIER)
        self.assertEqual(row.current_hp, 19999)
        self.assertIsNotNone(row.position)
        # And no scene key is left behind holding nothing.
        self.assertEqual(registry.scenes(), (SCENE,))


class TheBoundsOnTheBook(unittest.TestCase):

    def test_a_new_scene_is_refused_when_the_book_is_full(self):
        """The per-scene cap is not a bound on the BOOK.

        pf-adversary (round `tz2rgc`, D8) measured the first draft holding
        20,000 fabricated scene keys with no refusal, under a comment that
        claimed the opposite.
        """
        registry = world_scene_registry.WorldSceneRegistry(scenes=2)
        self.assertTrue(registry.note_balance("bg0002", SOLDIER, 9, 10).noted)
        self.assertTrue(registry.note_balance("bg0003", SOLDIER, 9, 10).noted)
        refused = registry.note_balance("bg0004", SOLDIER, 9, 10)
        self.assertEqual(refused.reason,
                         world_scene_registry.REFUSE_TOO_MANY_SCENES)
        self.assertEqual(registry.scenes(), ("bg0002", "bg0003"))
        # A scene already in the book keeps working when the book is full.
        self.assertTrue(registry.note_balance("bg0002", SECOND, 9, 10).noted)
        # And nothing was left behind for the refused scene.
        self.assertEqual(registry.remembered("bg0004"), ())

    def test_a_bad_scene_cap_is_refused_at_construction(self):
        for bad in (0, -1, True, 1.5, "many"):
            with self.subTest(cap=bad):
                with self.assertRaises(ValueError):
                    world_scene_registry.WorldSceneRegistry(scenes=bad)

    def test_a_vital_needs_its_ceiling(self):
        with self.assertRaises(ValueError):
            world_scene_registry.MobVital(SOLDIER, 900, None)
        with self.assertRaises(ValueError):
            world_scene_registry.MobVital(SOLDIER, None, CEILING)
        with self.assertRaises(ValueError):
            world_scene_registry.MobVital(SOLDIER, CEILING + 1, CEILING)
        with self.assertRaises(ValueError):
            world_scene_registry.MobVital(SOLDIER, position=("a", "b", "c"))


class TheFailureIsReportedUnderItsOwnName(unittest.TestCase):
    """D5: three different faults were printed under one borrowed name."""

    def _seed_with(self, book):
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            returned = world_scene_registry.seed_the_session_ledger(
                _ledger(), SCENE, registry=registry, deaths=book)
        return returned, buffer.getvalue()

    def test_a_raising_grave_book_is_not_reported_as_a_ceiling_problem(self):
        class _Hostile:
            @staticmethod
            def is_buried(scene, identity):
                raise RuntimeError("the grave book is on fire")

        returned, printed = self._seed_with(_Hostile)
        self.assertEqual(returned.balance_of(SOLDIER).current_hp, CEILING)
        self.assertIn("reason=ledger_refused_the_row", printed)
        self.assertIn("on fire", printed)
        self.assertNotIn("above_the_ledger_ceiling", printed)
        printed.encode("ascii")

    def test_the_install_seam_actually_installs(self):
        mine = world_scene_registry.WorldSceneRegistry()
        previous = world_scene_registry.world_scene_registry()
        try:
            self.assertIs(
                world_scene_registry.install_world_scene_registry(mine), mine)
            self.assertIs(world_scene_registry.world_scene_registry(), mine)
        finally:
            world_scene_registry.install_world_scene_registry(previous)


class TheConstantsAreTheOnesTheDocstringsJustify(unittest.TestCase):
    """N4: a bound nothing pins can silently return to unbounded.

    Mutating `SCENES_CAP` to a billion left both test files green, which is
    the same hole D8 was opened for -- one level up.
    """

    def test_the_production_bounds_are_pinned(self):
        self.assertEqual(world_scene_registry.VITALS_PER_SCENE_CAP, 4096)
        self.assertEqual(world_scene_registry.SCENES_CAP, 128)
        self.assertEqual(world_scene_registry._MAX_COORDINATE, 1.0e7)
        # And the defaults are really what a bare registry gets.
        bare = world_scene_registry.WorldSceneRegistry()
        self.assertEqual(bare.vitals_per_scene,
                         world_scene_registry.VITALS_PER_SCENE_CAP)

    def test_a_health_exactly_at_the_ceiling_is_applied_not_skipped(self):
        """N8: the boundary.  A row remembered at full health IS a row --
        it is what a respawn or a full heal leaves behind, and skipping it
        would silently drop the one value that says "this monster is whole".
        """
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, CEILING, CEILING)
        wounded = _ledger(mob_combat.MobBalance(SOLDIER, CEILING, 900))
        seeded = world_scene_registry.seed_the_session_ledger(
            wounded, SCENE, registry=registry, announce=False)
        self.assertEqual(seeded.balance_of(SOLDIER).current_hp, CEILING)

    def test_a_thing_that_is_not_a_ledger_is_named_as_that(self):
        """N7: the scene check must not swallow `not_a_ledger`.

        Deleting the isinstance check made a non-ledger come back as
        `another_scenes_ledger` -- one fault reported under another's name,
        which is the disease D5 was opened for.
        """
        registry = world_scene_registry.WorldSceneRegistry()
        registry.note_balance(SCENE, SOLDIER, 900, CEILING)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            world_scene_registry.seed_the_session_ledger(
                object(), SCENE, registry=registry)
        self.assertIn("reason=not_a_ledger", buffer.getvalue())
        self.assertNotIn("another_scenes_ledger", buffer.getvalue())

    def test_a_hostile_exception_cannot_break_the_console_line(self):
        """N2: the reason that carries an error is clamped, ASCII and bounded."""

        class _Raising:
            @staticmethod
            def is_buried(scene, identity):
                raise RuntimeError("\u0e44\u0e17\u0e22 \u20ac " + "A" * 5000)

        class _Unreprable(Exception):
            def __repr__(self):
                raise ValueError("no repr for you")

        class _Worse:
            @staticmethod
            def is_buried(scene, identity):
                raise _Unreprable()

        for book in (_Raising, _Worse):
            with self.subTest(book=book.__name__):
                registry = world_scene_registry.WorldSceneRegistry()
                registry.note_balance(SCENE, SOLDIER, 900, CEILING)
                buffer = io.StringIO()
                with redirect_stdout(buffer):
                    returned = world_scene_registry.seed_the_session_ledger(
                        _ledger(), SCENE, registry=registry, deaths=book)
                line = buffer.getvalue().strip()
                self.assertEqual(returned.balance_of(SOLDIER).current_hp,
                                 CEILING)
                self.assertIn("reason=ledger_refused_the_row", line)
                line.encode("ascii")
                line.encode("cp874")
                self.assertLess(len(line), 300, len(line))
                self.assertNotIn("\n", line)


class TheWiringAsk(unittest.TestCase):

    def test_the_pasteable_call_site_names_the_function_it_asks_for(self):
        text = world_scene_registry.WORLD_REGISTRY_SEED_WIRING
        self.assertIn("seed_the_session_ledger", text)
        self.assertIn("self.mob_combat_ledger", text)
        self.assertIn("from . import world_scene_registry", text)
        text.encode("ascii")

    def test_every_runtime_anchor_the_ask_names_is_really_in_runtime_today(self):
        """D2: the first draft told chief to paste after a line that does not exist.

        A letter is a claim about another file, and a substring check of the
        letter against itself would pass on a letter naming an imaginary
        anchor.  So the anchors are checked against runtime.py itself.
        """
        runtime = (pathlib.Path(__file__).resolve().parents[1]
                   / "src" / "pirateforce_foundation" / "runtime.py").read_text(
                       encoding="utf-8")
        for anchor in (
                "def _sync_combat_scene_state",
                "if folder != self.mob_combat_scene_folder:",
                "for record in self.mob_death_register.records:",
                "register = mob_ai_control.open_register(roster, epoch=0)",
        ):
            with self.subTest(anchor=anchor[:40]):
                self.assertIn(anchor, runtime)
        self.assertIn(
            "self.mob_combat_ledger = mob_combat.open_ledger(_boot_roster)",
            runtime)
        # NOT pinned here: the ABSENCE of mob_death_persistence's own queued
        # statement.  A first draft asserted `assertNotIn(
        # "seed_the_session_state", runtime)`, and pf-adversary (round
        # tz2rgc, N3) measured what that costs: the moment chief does what
        # the OTHER module's wiring ask says, THIS lane's suite goes red
        # under a test named "anchor is really in runtime today".  A lane
        # may pin what its own ask needs to exist; pinning that another
        # lane's ask has not been granted yet is a tripwire under a
        # colleague.


if __name__ == "__main__":
    unittest.main()
