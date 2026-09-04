"""LANE-B: a grave survives the session that dug it.

WHAT THIS FILE IS THE EVIDENCE FOR.  ka1-A's R309 (`pf_bridge/notes_to_chief/
20260904_1430`) killed the Fighting Fish soldier `0x203D` in scene 2, closed
the client, logged back in on a server that never restarted, and photographed
that monster STANDING AT 3138/3138 (`141440.png`).  Nothing had respawned it:
the deaths lived in the ended session's `mob_death.DeathRegister`, and
`runtime.py` builds a fresh empty one per session.

The wire layer of that half is here -- the world's grave book, the write seam
inside `commit_death`, and the read seam a new session's register is built
through.  The client-observable layer is `GT-223` re-run, which needs the one
call site only chief may add (`mob_death_persistence.seed_the_session_state`
in `_sync_combat_scene_state`) and is therefore NOT claimed by this file.
What IS claimed: after a committed kill, a register built from nothing and
seeded from the world says that identity is dead, `live_roster` leaves it out,
and a kill computed against the seeded register still commits.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_combat                         # noqa: E402
from pirateforce_foundation import mob_death                          # noqa: E402
from pirateforce_foundation import mob_death_persistence as graves    # noqa: E402
from pirateforce_foundation import field_mobs                         # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy          # noqa: E402

#: The scene tags are the folder registry's own spelling, which is what
#: `world_scene_folder.scene_folder_for_scene_id` hands the call site and what
#: every mined table's `SCENE` constant carries.  Scene 2 is capitalised and
#: scene 1 is not -- that asymmetry is real and it is why this file tests the
#: fold.
BG1 = "bg0001"
BG2 = "Bg0002"

#: The monster R309 actually killed, and the ceiling it actually stood at.
#: A REAL ROW of Bg0002's mined roster, and every identity in this file is
#: one: `roster_key_of` refuses anything else, and a test that reached for a
#: made-up number would be testing a path production cannot take.
SOLDIER = 0x203D
SOLDIER_MAX_HP = 3138
KILLER = 0x750059

#: Three more real Bg0002 rows, for the tests that need a handful.
BG2_ROWS = (0x2033, 0x203B, 0x203C)
#: A real bg0001 row (a Training Iron Man).
IRON_MAN = 0x2068
#: A LIVE cross-scene identity collision, straight out of the mined tables:
#: 0x203C is a row of Bg0002 AND a row of bg0005.  Two graves, not one.
COLLIDING = 0x203C
BG5 = "bg0005"

#: Identities the world's books must refuse.  0x4329 is a diag multi-object
#: (`mob_diag_multi_object` stamps it with bg0001's own scene tag); 0x201F is
#: the sanctioned first target, WITHDRAWN from the bg0001 roster by
#: COO-DECISION 2026-08-29T00:41.  pf-adversary measured both of these ending
#: up in the book and then refusing bg0001's arrival census for the life of
#: the process.
DIAG_OBJECT = 0x4329
WITHDRAWN = 0x201F


def roster_ceiling(identity, scene):
    """The ceiling that scene's mined table actually gives this identity.

    Every record in this file carries it, because the roster gate refuses a
    row whose ceiling disagrees with the roster's -- `repopulation_entries`
    refuses on that field too, so a test that made one up would be testing a
    row production cannot produce.
    """
    for mob in field_mobs.load_roster(scene):
        if mob.actor_identity == identity:
            return mob.max_hp
    raise AssertionError(
        "0x%X is not a row of %s" % (identity, scene))


def a_record(identity=SOLDIER, scene=BG2, killer=KILLER, max_hp=None):
    if max_hp is None:
        try:
            max_hp = roster_ceiling(identity, scene)
        except (AssertionError, Exception):             # noqa: BLE001
            max_hp = SOLDIER_MAX_HP
    return mob_death.DeathRecord(identity, killer, max_hp, scene)


def a_step(record, register, base_generation=0):
    """A committable step.  The frames are opaque bytes to `commit_death`."""
    return mob_death.DeathStep(
        record=record,
        dying_pc=b"\x01", dying_frame=b"\x02",
        dead_pc=b"\x03", dead_frame=b"\x04",
        register=register.with_death(record),
        base_generation=base_generation,
    )


def quiet(fn, *args, **kwargs):
    """Run something that prints a console line and hand back the line."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = fn(*args, **kwargs)
    return result, buffer.getvalue()


class TheGraveBookTests(unittest.TestCase):
    """`WorldDeaths` -- the process's own books.  NEVER RAISES OUTWARD."""

    def setUp(self) -> None:
        self.world = graves.WorldDeaths()

    def test_burying_one_death_makes_it_readable_in_that_scene(self):
        self.assertEqual(self.world.bury(a_record()), (True, ""))
        self.assertTrue(self.world.is_buried(BG2, SOLDIER))
        self.assertEqual(
            tuple(r.actor_identity for r in self.world.buried_in(BG2)),
            (SOLDIER,))

    def test_a_second_burial_of_one_identity_is_already_not_an_overwrite(self):
        self.world.bury(a_record())
        self.assertEqual(
            self.world.bury(a_record(killer=0x999)), (False, ""))
        held = self.world.buried_in(BG2)[0]
        self.assertEqual(held.killer_identity, KILLER)

    def test_a_scene_only_answers_for_its_own_graves(self):
        self.world.bury(a_record(scene=BG2))
        self.assertFalse(self.world.is_buried(BG1, SOLDIER))
        self.assertEqual(self.world.buried_in(BG1), ())

    def test_the_key_folds_case_because_the_registry_spells_both_ways(self):
        self.world.bury(a_record(scene=BG2))
        self.assertTrue(self.world.is_buried("bg0002", SOLDIER))
        self.assertEqual(len(self.world.buried_in("BG0002")), 1)

    def test_a_row_that_is_not_a_death_record_is_refused_by_name(self):
        self.assertEqual(
            self.world.bury(object()), (False, graves.REFUSE_NOT_A_RECORD))
        self.assertEqual(self.world.buried_in(BG2), ())

    def test_an_unreadable_scene_is_refused_by_name_and_never_raises(self):
        self.assertEqual(self.world.buried_in(None), ())
        self.assertFalse(self.world.is_buried(None, SOLDIER))
        self.assertFalse(self.world.forget(None, SOLDIER))

    def test_the_cap_refuses_the_newest_and_keeps_every_older_grave(self):
        small = graves.WorldDeaths(graves_per_scene=2)
        first, second, third = BG2_ROWS
        self.assertEqual(small.bury(a_record(identity=first)), (True, ""))
        self.assertEqual(small.bury(a_record(identity=second)), (True, ""))
        self.assertEqual(small.bury(a_record(identity=third)),
                         (False, graves.REFUSE_SCENE_IS_FULL))
        # Which corpse the cap sacrifices, stated as measured rather than as
        # the docstring first argued it: the OLDER graves survive and the
        # NEWEST one -- the corpse the player is looking at -- is the one
        # that will stand back up.  The roster gate is what puts this out of
        # production's reach, not this policy.
        self.assertTrue(small.is_buried(BG2, first))
        self.assertTrue(small.is_buried(BG2, second))
        self.assertFalse(small.is_buried(BG2, third))

    def test_forget_is_the_respawn_door_and_removes_only_one_grave(self):
        first, second, _third = BG2_ROWS
        self.world.bury(a_record(identity=first))
        self.world.bury(a_record(identity=second))
        self.assertTrue(self.world.forget(BG2, first))
        self.assertFalse(self.world.forget(BG2, first))
        self.assertEqual(
            tuple(r.actor_identity for r in self.world.buried_in(BG2)),
            (second,))

    def test_clear_empties_every_scene(self):
        self.world.bury(a_record(identity=IRON_MAN, scene=BG1))
        self.world.bury(a_record(scene=BG2))
        self.world.clear()
        self.assertEqual(self.world.buried_in(BG1), ())
        self.assertEqual(self.world.buried_in(BG2), ())

    def test_a_cap_that_is_not_a_positive_int_is_refused_at_construction(self):
        for bad in (0, -1, 1.5, "4", True):
            with self.assertRaises(ValueError):
                graves.WorldDeaths(graves_per_scene=bad)


class RememberingADeathTests(unittest.TestCase):
    """`remember_death` -- the write seam.  NEVER RAISES, ALWAYS SAYS."""

    def setUp(self) -> None:
        self.world = graves.WorldDeaths()

    def test_a_death_is_remembered_and_one_bounded_line_says_so(self):
        outcome, line = quiet(
            graves.remember_death, a_record(), world=self.world)
        self.assertTrue(outcome.buried)
        self.assertFalse(outcome.already_buried)
        self.assertIn(graves.WORLD_REMEMBERED_TOKEN, line)
        self.assertIn("identity=0x203D", line)
        self.assertIn("already=no", line)
        self.assertEqual(len(line.splitlines()), 1)

    def test_a_repeat_says_already_yes_and_still_reports_it_is_on_the_books(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        outcome, line = quiet(
            graves.remember_death, a_record(), world=self.world)
        self.assertTrue(outcome.buried)
        self.assertTrue(outcome.already_buried)
        self.assertIn("already=yes", line)

    def test_junk_is_refused_by_name_and_nothing_raises(self):
        outcome, line = quiet(
            graves.remember_death, object(), world=self.world)
        self.assertFalse(outcome.buried)
        self.assertEqual(outcome.reason, graves.REFUSE_NOT_A_RECORD)
        self.assertIn(graves.WORLD_REMEMBER_REFUSED_TOKEN, line)

    def test_a_world_that_raises_is_a_named_refusal_not_an_escape(self):
        class Angry:
            def bury(self, record):
                raise RuntimeError("no")

        outcome, line = quiet(
            graves.remember_death, a_record(),
            world=graves.install_world_deaths(graves.WorldDeaths()))
        self.assertTrue(outcome.buried)
        # And now the real one: an installed world whose bury() explodes.
        graves._WORLD = Angry()                         # noqa: SLF001
        try:
            outcome, line = quiet(graves.remember_death, a_record())
        finally:
            graves.install_world_deaths(graves.WorldDeaths())
        self.assertFalse(outcome.buried)
        self.assertIn(graves.REFUSE_WORLD_RAISED, outcome.reason)
        self.assertIn(graves.WORLD_REMEMBER_REFUSED_TOKEN, line)

    def test_every_console_line_this_module_writes_is_ascii(self):
        # The bridge console is cp874: a non-ASCII byte in a token is a
        # crash on the operator's machine, not a cosmetic problem.
        lines = [
            graves.describe_remembered(
                graves.remember_death(
                    a_record(), world=self.world, announce=False)),
            graves.describe_remembered(
                graves.GraveOutcome("x", reason="boom")),
            graves.describe_seeded(
                graves.seed_register(mob_death.DeathRegister(), BG2,
                                     world=self.world)),
            graves.describe_seeded(
                graves.SeedOutcome("x", mob_death.DeathRegister(),
                                   reason="boom")),
        ]
        for line in lines:
            line.encode("ascii")
            self.assertLess(len(line), 300)


class SeedingASessionRegisterTests(unittest.TestCase):
    """`seed_register` -- what a relogin walks into.  NEVER RAISES."""

    def setUp(self) -> None:
        self.world = graves.WorldDeaths()
        self.empty = mob_death.DeathRegister()
        # pf-adversary: without this, `test_an_empty_scene_still_prints...`
        # passed only because its name sorts before its siblings'.  A
        # process-global latch needs clearing in EVERY class that reads it,
        # not only in the one written for it.
        graves.forget_announced_scenes()

    def tearDown(self) -> None:
        graves.forget_announced_scenes()

    def test_an_empty_world_hands_the_caller_its_own_register_back(self):
        outcome = graves.seed_register(self.empty, BG2, world=self.world)
        self.assertTrue(outcome.seeded)
        self.assertIs(outcome.register, self.empty)
        self.assertEqual(outcome.admitted, ())

    def test_a_grave_dug_in_one_session_is_dead_in_the_next_ones_register(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        outcome = graves.seed_register(self.empty, BG2, world=self.world)
        self.assertTrue(outcome.seeded)
        self.assertTrue(outcome.register.is_dead(SOLDIER, BG2))
        self.assertEqual(len(outcome.admitted), 1)
        # The register the caller handed in is a value and is untouched.
        self.assertEqual(self.empty.records, ())

    def test_the_seeded_register_keeps_generation_equal_to_its_length(self):
        for identity in BG2_ROWS:
            graves.remember_death(
                a_record(identity=identity), world=self.world, announce=False)
        seeded = graves.seed_register(
            self.empty, BG2, world=self.world).register
        self.assertEqual(len(seeded.records), 3)
        self.assertEqual(seeded.generation, len(seeded.records))

    def test_seeding_twice_admits_nothing_the_second_time(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        once = graves.seed_register(self.empty, BG2, world=self.world).register
        twice = graves.seed_register(once, BG2, world=self.world)
        self.assertEqual(twice.admitted, ())
        self.assertIs(twice.register, once)

    def test_only_the_named_scenes_graves_cross_over(self):
        # 0x203C is genuinely a row of BOTH Bg0002 and bg0005: the live
        # collision the register's (scene, identity) key exists for.
        graves.remember_death(
            a_record(identity=COLLIDING, scene=BG2),
            world=self.world, announce=False)
        graves.remember_death(
            a_record(identity=COLLIDING, scene=BG5),
            world=self.world, announce=False)
        seeded = graves.seed_register(
            self.empty, BG2, world=self.world).register
        self.assertTrue(seeded.is_dead(COLLIDING, BG2))
        self.assertFalse(seeded.is_dead(COLLIDING, BG5))
        self.assertEqual(len(seeded.records), 1)

    def test_a_seeded_row_keeps_its_own_scene_spelling_not_the_callers(self):
        # The rehydrate loop at the call site compares `record.scene ==
        # folder` with `==`, so a row that came back spelled by the fold
        # would be skipped there and the ledger would stay at full HP while
        # the register said dead.
        graves.remember_death(a_record(scene=BG2), world=self.world,
                              announce=False)
        seeded = graves.seed_register(
            self.empty, "bg0002", world=self.world).register
        self.assertEqual(seeded.records[0].scene, BG2)

    def test_the_grave_carries_the_ceiling_the_monster_actually_stood_at(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        seeded = graves.seed_register(
            self.empty, BG2, world=self.world).register
        self.assertEqual(seeded.record_of(SOLDIER, BG2).max_hp,
                         roster_ceiling(SOLDIER, BG2))

    def test_something_that_is_not_a_register_is_refused_and_handed_back(self):
        outcome = graves.seed_register(object(), BG2, world=self.world)
        self.assertFalse(outcome.seeded)
        self.assertEqual(outcome.reason, graves.REFUSE_NOT_A_REGISTER)

    def test_an_unreadable_scene_is_refused_and_the_register_survives(self):
        outcome = graves.seed_register(self.empty, None, world=self.world)
        self.assertFalse(outcome.seeded)
        self.assertEqual(outcome.reason, graves.REFUSE_SCENE_IS_UNREADABLE)
        self.assertIs(outcome.register, self.empty)

    def test_a_world_that_raises_costs_the_seed_and_not_the_register(self):
        class Angry:
            def buried_in(self, scene):
                raise RuntimeError("no")

        outcome = graves.seed_register(self.empty, BG2, world=graves.world_deaths())
        self.assertTrue(outcome.seeded)
        graves._WORLD = Angry()                         # noqa: SLF001
        try:
            outcome = graves.seed_register(self.empty, BG2)
        finally:
            graves.install_world_deaths(graves.WorldDeaths())
        self.assertFalse(outcome.seeded)
        self.assertIn(graves.REFUSE_WORLD_RAISED, outcome.reason)
        self.assertIs(outcome.register, self.empty)

    def test_the_one_line_call_site_returns_a_register_and_says_so(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        seeded, line = quiet(
            graves.seed_the_session_register, self.empty, BG2,
            world=self.world)
        self.assertIsInstance(seeded, mob_death.DeathRegister)
        self.assertTrue(seeded.is_dead(SOLDIER, BG2))
        self.assertIn(graves.WORLD_SEEDED_TOKEN, line)
        self.assertIn("admitted=1", line)

    def test_the_one_line_call_site_hands_back_the_register_on_a_refusal(self):
        seeded, line = quiet(
            graves.seed_the_session_register, self.empty, None,
            world=self.world)
        self.assertIs(seeded, self.empty)
        self.assertIn(graves.WORLD_SEED_REFUSED_TOKEN, line)

    def test_an_empty_scene_still_prints_a_line_because_silence_is_ambiguous(self):
        _seeded, line = quiet(
            graves.seed_the_session_register, self.empty, BG2,
            world=self.world)
        self.assertIn(graves.WORLD_SEEDED_TOKEN, line)
        self.assertIn("admitted=0", line)
        self.assertIn("identities=none", line)


class TheKillPathWritesToTheWorldTests(unittest.TestCase):
    """`commit_death` is the only writer, and only past its own refusals."""

    def setUp(self) -> None:
        self.world = graves.install_world_deaths(graves.WorldDeaths())

    def tearDown(self) -> None:
        graves.install_world_deaths(graves.WorldDeaths())

    def test_an_accepted_kill_is_on_the_worlds_books(self):
        record = a_record()
        register = mob_death.DeathRegister()
        with contextlib.redirect_stdout(io.StringIO()):
            after = mob_death.commit_death(register, a_step(record, register))
        self.assertTrue(after.is_dead(SOLDIER, BG2))
        self.assertTrue(self.world.is_buried(BG2, SOLDIER))

    def test_a_refused_kill_digs_no_grave(self):
        record = a_record()
        register = mob_death.DeathRegister()
        stale = a_step(record, register, base_generation=7)
        with self.assertRaises(mob_death.MobDeathContractError):
            with contextlib.redirect_stdout(io.StringIO()):
                mob_death.commit_death(register, stale)
        self.assertFalse(self.world.is_buried(BG2, SOLDIER))

    def test_a_kill_computed_after_a_seed_still_commits(self):
        # The compare-and-swap reads `current.generation`; a seeded register
        # carries a HIGHER one than the empty register a session starts on,
        # so this is the check that the seam does not wedge the next kill.
        graves.remember_death(
            a_record(identity=BG2_ROWS[0]), world=self.world, announce=False)
        seeded = graves.seed_register(
            mob_death.DeathRegister(), BG2, world=self.world).register
        self.assertEqual(seeded.generation, 1)
        record = a_record(identity=SOLDIER)
        step = a_step(record, seeded, base_generation=seeded.generation)
        with contextlib.redirect_stdout(io.StringIO()):
            after = mob_death.commit_death(seeded, step)
        self.assertTrue(after.is_dead(BG2_ROWS[0], BG2))
        self.assertTrue(after.is_dead(SOLDIER, BG2))
        self.assertEqual(after.generation, len(after.records))


class WhatARelogNowSeesTests(unittest.TestCase):
    """The R309 sequence, at the layer this file can measure."""

    def setUp(self) -> None:
        self.world = graves.install_world_deaths(graves.WorldDeaths())

    def tearDown(self) -> None:
        graves.install_world_deaths(graves.WorldDeaths())

    def test_the_monster_the_first_session_killed_is_not_in_the_second_ones_live_roster(self):
        roster = field_mobs.load_roster(BG2)
        self.assertTrue(roster, "scene 2 must have a mined roster")
        victim = roster[0]
        # Session one: kill it.
        first = mob_death.DeathRegister()
        record = mob_death.DeathRecord(
            victim.actor_identity, KILLER, victim.max_hp, victim.scene)
        with contextlib.redirect_stdout(io.StringIO()):
            first = mob_death.commit_death(first, a_step(record, first))
        self.assertNotIn(
            victim.actor_identity,
            tuple(m.actor_identity
                  for m in mob_death.live_roster(roster, first)))
        # Session two: a brand new, empty register -- yesterday's bug.
        second = mob_death.DeathRegister()
        self.assertIn(
            victim.actor_identity,
            tuple(m.actor_identity
                  for m in mob_death.live_roster(roster, second)))
        # ...and the same register once the seam has run.
        seeded = graves.seed_register(
            second, victim.scene, world=self.world).register
        self.assertNotIn(
            victim.actor_identity,
            tuple(m.actor_identity
                  for m in mob_death.live_roster(roster, seeded)))

    def test_the_wiring_note_names_the_function_and_the_file_it_belongs_in(self):
        # The letter to chief quotes this constant; a rename that did not
        # update it would send chief a call site that does not exist.
        self.assertIn(
            "seed_the_session_state", graves.DEATH_SEED_WIRING)
        self.assertIn("mob_combat_ledger", graves.DEATH_SEED_WIRING)
        self.assertIn("_sync_combat_scene_state", graves.DEATH_SEED_WIRING)
        self.assertIn("mob_death_persistence", graves.DEATH_SEED_WIRING)
        graves.DEATH_SEED_WIRING.encode("ascii")
        self.assertTrue(hasattr(graves, "seed_the_session_state"))


class TheRosterGateTests(unittest.TestCase):
    """The refusals pf-adversary (round amz1w5) measured the need for.

    THE FAILURE THESE PIN, in the adversary's own measurement: one diag
    multi-object kill puts `0x4329` in the world's books tagged `bg0001`;
    every LATER login into bg0001 is seeded with it; `repopulation_entries`
    refuses a register row that is not a roster key; the arrival census
    raises inside its own fail-closed catch and ships NO frame; and the
    player logs into an empty town for the life of the PROCESS, not the
    session.  A grave is only ever dug for a row of the scene's mined table.
    """

    def setUp(self) -> None:
        self.world = graves.WorldDeaths()

    def test_a_diag_multi_object_identity_never_gets_a_grave(self):
        self.assertEqual(
            self.world.bury(a_record(identity=DIAG_OBJECT, scene=BG1)),
            (False, graves.REFUSE_IDENTITY_NOT_IN_THE_ROSTER))
        self.assertEqual(self.world.buried_in(BG1), ())

    def test_an_identity_withdrawn_from_a_roster_never_gets_a_grave(self):
        self.assertEqual(
            self.world.bury(a_record(identity=WITHDRAWN, scene=BG1)),
            (False, graves.REFUSE_IDENTITY_NOT_IN_THE_ROSTER))

    def test_a_scene_with_no_mined_table_is_refused_by_its_own_name(self):
        self.assertEqual(
            self.world.bury(a_record(scene="Bg0004")),
            (False, graves.REFUSE_SCENE_HAS_NO_MINED_ROSTER))

    def test_the_rosters_own_spelling_is_required_not_merely_folded(self):
        # The book folds case for its KEY, but every consumer downstream
        # compares `record.scene` with `==`: runtime's rehydrate guard,
        # `live_roster`, `repopulation_entries`.  A row spelled the other
        # way would be seeded and then silently skipped by all three, with a
        # green console line over a monster still standing at full HP.
        self.assertEqual(
            self.world.bury(a_record(scene="bg0002")),
            (False, graves.REFUSE_SCENE_SPELLING_IS_NOT_THE_ROSTERS))
        self.assertEqual(self.world.bury(a_record(scene=BG2)), (True, ""))

    def test_a_row_that_got_into_the_book_anyway_is_skipped_at_the_seed(self):
        # Second line of defence, and it is not decorative: `bury` is not the
        # only way rows could ever reach these dicts (a shrunken table in a
        # later build would do it), and ONE bad row costs a scene its whole
        # census for every session in the process.
        rogue = a_record(identity=DIAG_OBJECT, scene=BG1)
        self.world._graves.setdefault(          # noqa: SLF001
            BG1, __import__("collections").OrderedDict())[DIAG_OBJECT] = rogue
        outcome = graves.seed_register(
            mob_death.DeathRegister(), BG1, world=self.world)
        self.assertEqual(outcome.admitted, ())
        self.assertEqual(outcome.skipped, 1)
        self.assertIn("skipped=1", graves.describe_seeded(outcome))

    def test_the_arrival_census_still_composes_after_a_kill_and_a_seed(self):
        # THE WHOLE POINT, at the layer this file can measure: a fresh
        # session's register, seeded from the world, must not make
        # `repopulation_entries` refuse.  The adversary's control was the
        # same call raising `register_row_disagrees_with_roster`.
        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        roster = field_mobs.load_roster(BG2)
        victim = roster[0]
        register = mob_death.DeathRegister()
        record = mob_death.DeathRecord(
            victim.actor_identity, KILLER, victim.max_hp, victim.scene)
        with contextlib.redirect_stdout(io.StringIO()):
            mob_death.commit_death(
                register, a_step(record, register), world=self.world)
        # `ledger=` on purpose: every production call site passes one, and
        # the REFUSE_LEDGER_DISAGREES_WITH_REGISTER arm -- the one that
        # actually fires after a seed -- is unreachable without it.
        ledger = mob_combat.open_ledger(roster, scene=BG2)
        with contextlib.redirect_stdout(io.StringIO()):
            seeded, ledger = graves.seed_the_session_state(
                mob_death.DeathRegister(), ledger, BG2, world=self.world)
        entries = mob_death.repopulation_entries(
            legacy, roster, seeded, ledger=ledger)
        self.assertEqual(len(entries), len(roster))


class TheWriteSeamHasAnOptOutTests(unittest.TestCase):
    """`commit_death` must not force every caller to touch process state."""

    def setUp(self) -> None:
        self.world = graves.install_world_deaths(graves.WorldDeaths())

    def tearDown(self) -> None:
        graves.install_world_deaths(graves.WorldDeaths())

    def test_a_caller_may_name_its_own_book_and_leave_the_process_alone(self):
        mine = graves.WorldDeaths()
        register = mob_death.DeathRegister()
        record = a_record()
        mob_death.commit_death(
            register, a_step(record, register), world=mine, announce=False)
        self.assertTrue(mine.is_buried(BG2, SOLDIER))
        self.assertFalse(self.world.is_buried(BG2, SOLDIER))

    def test_announce_false_reaches_all_the_way_down_from_commit_death(self):
        register = mob_death.DeathRegister()
        record = a_record()
        _after, line = quiet(
            mob_death.commit_death, register, a_step(record, register),
            world=graves.WorldDeaths(), announce=False)
        self.assertEqual(line, "")

    def test_by_default_a_kill_still_says_so_on_the_console(self):
        register = mob_death.DeathRegister()
        record = a_record()
        _after, line = quiet(
            mob_death.commit_death, register, a_step(record, register))
        self.assertIn(graves.WORLD_REMEMBERED_TOKEN, line)


class TheConsoleDoesNotRepeatItselfTests(unittest.TestCase):
    """The seed runs on every dispatch, so a no-op must be silent."""

    def setUp(self) -> None:
        self.world = graves.WorldDeaths()
        graves.forget_announced_scenes()

    def tearDown(self) -> None:
        graves.forget_announced_scenes()

    def test_an_empty_scene_says_so_once_and_then_stops(self):
        _r, first = quiet(graves.seed_the_session_register,
                          mob_death.DeathRegister(), BG2, world=self.world)
        _r, second = quiet(graves.seed_the_session_register,
                           mob_death.DeathRegister(), BG2, world=self.world)
        self.assertIn(graves.WORLD_SEEDED_TOKEN, first)
        self.assertEqual(second, "")

    def test_a_scene_whose_graves_are_already_held_is_silent(self):
        graves.remember_death(a_record(), world=self.world, announce=False)
        register, first = quiet(
            graves.seed_the_session_register, mob_death.DeathRegister(), BG2,
            world=self.world)
        _again, second = quiet(
            graves.seed_the_session_register, register, BG2, world=self.world)
        self.assertIn("admitted=1", first)
        self.assertEqual(second, "")

    def test_a_refusal_is_never_swallowed_by_the_quiet_rule(self):
        _r, line = quiet(graves.seed_the_session_register,
                         object(), BG2, world=self.world)
        self.assertIn(graves.WORLD_SEED_REFUSED_TOKEN, line)


class TheLedgerMovesWithTheRegisterTests(unittest.TestCase):
    """`seed_the_session_state` -- and the crash it exists to prevent.

    pf-adversary MEASURED this round's own first answer taking the listener
    thread down.  Seeding the register OUTSIDE the scene-change branch put
    graves in the register while the boot ledger -- whose only rehydrate loop
    lives INSIDE that branch -- stayed at full HP.  `repopulation_entries`
    refuses when the two disagree, and the arrival census reaches that
    refusal from an `else:` clause its own `try` does not cover.
    """

    def setUp(self) -> None:
        self.world = graves.install_world_deaths(graves.WorldDeaths())
        graves.forget_announced_scenes()
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.roster = field_mobs.load_roster(BG1)
        self.victim = self.roster[0]

    def tearDown(self) -> None:
        graves.install_world_deaths(graves.WorldDeaths())
        graves.forget_announced_scenes()

    def _kill_in_a_first_session(self):
        register = mob_death.DeathRegister()
        record = mob_death.DeathRecord(
            self.victim.actor_identity, KILLER, self.victim.max_hp,
            self.victim.scene)
        with contextlib.redirect_stdout(io.StringIO()):
            mob_death.commit_death(register, a_step(record, register))

    def test_the_boot_scene_census_composes_after_a_relogin(self):
        # THE MEASURED CRASH, pinned.  bg0001 is the scene the process boots
        # on, so the branch that would re-open its roster never runs: this is
        # the exact path where a register-only seed raised.
        self._kill_in_a_first_session()
        ledger = mob_combat.open_ledger(self.roster, scene=BG1)
        register = mob_death.DeathRegister()
        with contextlib.redirect_stdout(io.StringIO()):
            register, ledger = graves.seed_the_session_state(
                register, ledger, BG1)
        self.assertTrue(register.is_dead(self.victim.actor_identity, BG1))
        self.assertEqual(
            ledger.balance_of(self.victim.actor_identity).current_hp, 0)
        # The call that raised before this function existed.
        entries = mob_death.repopulation_entries(
            self.legacy, self.roster, register, ledger=ledger)
        self.assertEqual(len(entries), len(self.roster))

    def test_the_ledger_keeps_the_ceiling_and_only_the_dead_row_moves(self):
        self._kill_in_a_first_session()
        ledger = mob_combat.open_ledger(self.roster, scene=BG1)
        with contextlib.redirect_stdout(io.StringIO()):
            _register, seeded = graves.seed_the_session_state(
                mob_death.DeathRegister(), ledger, BG1)
        self.assertEqual(
            seeded.balance_of(self.victim.actor_identity).max_hp,
            self.victim.max_hp)
        for other in self.roster[1:]:
            self.assertEqual(
                seeded.balance_of(other.actor_identity).current_hp,
                other.max_hp)

    def test_a_ledger_open_on_another_scene_comes_back_untouched(self):
        # The scene-change order: the branch re-opens the ledger a moment
        # later and rehydrates it from the register this call just seeded.
        self._kill_in_a_first_session()
        elsewhere = mob_combat.open_ledger(
            field_mobs.load_roster(BG2), scene=BG2)
        with contextlib.redirect_stdout(io.StringIO()):
            register, ledger = graves.seed_the_session_state(
                mob_death.DeathRegister(), elsewhere, BG1)
        self.assertIs(ledger, elsewhere)
        self.assertTrue(register.is_dead(self.victim.actor_identity, BG1))

    def test_no_ledger_means_no_seed_either_because_it_is_both_or_neither(self):
        self._kill_in_a_first_session()
        before = mob_death.DeathRegister()
        (register, ledger), line = quiet(
            graves.seed_the_session_state, before, None, BG1)
        self.assertIsNone(ledger)
        self.assertIs(register, before)
        self.assertIn(graves.REFUSE_NOT_A_LEDGER, line)

    def test_a_ledger_that_refuses_costs_the_register_its_seed_too(self):
        # BOTH HALVES OR NEITHER: a register holding graves the ledger does
        # not is the crash, so the safe degradation is yesterday's behaviour.
        class Angry(mob_combat.CombatLedger):
            def identities(self):
                raise RuntimeError("no")

        self._kill_in_a_first_session()
        before = mob_death.DeathRegister()
        angry = Angry(
            mob_combat.open_ledger(self.roster, scene=BG1).balances)
        (register, ledger), line = quiet(
            graves.seed_the_session_state, before, angry, BG1)
        self.assertIs(register, before)
        self.assertIs(ledger, angry)
        self.assertIn(graves.WORLD_SEED_REFUSED_TOKEN, line)
        self.assertIn(graves.REFUSE_LEDGER_REFUSED_THE_ROW, line)

    def test_a_second_admitted_grave_that_fails_still_costs_the_ledger_nothing(self):
        # pf-adversary, this round (re-review of the second pass): the loop
        # below used to reassign the `ledger` PARAMETER on every successful
        # `with_balance`, so a failure on the SECOND OR LATER row returned a
        # ledger already carrying the first row's mutation -- "the caller
        # gets back exactly what it handed in" was false whenever more than
        # one grave was admitted. `test_a_ledger_that_refuses_costs_the_
        # register_its_seed_too` above can't catch this: its `Angry` ledger
        # raises out of `identities()`, before the loop's first iteration,
        # so the reassignment never had a chance to run.
        register = mob_death.DeathRegister()
        first, second = self.roster[0], self.roster[1]
        for victim in (first, second):
            record = mob_death.DeathRecord(
                victim.actor_identity, KILLER, victim.max_hp, victim.scene)
            step = a_step(record, register, base_generation=register.generation)
            with contextlib.redirect_stdout(io.StringIO()):
                register = mob_death.commit_death(register, step)
        before = mob_death.DeathRegister()
        real = mob_combat.open_ledger(self.roster, scene=BG1)

        class RaisesOnTheSecondRow(mob_combat.CombatLedger):
            # `CombatLedger.with_balance` returns a bare `CombatLedger(...)`,
            # not `type(self)(...)` -- so delegating to `super().with_balance`
            # on a success would hand the loop a plain `CombatLedger` for its
            # NEXT iteration and this override would never see row two. Build
            # the replacement the same way the base method does, but keep it
            # this subclass, so the raise-on-the-second-call still applies to
            # the object the loop is actually holding by then.
            def with_balance(self, balance):
                calls.append(balance.actor_identity)
                if len(calls) == 2:
                    raise RuntimeError("no")
                self.balance_of(balance.actor_identity)
                return RaisesOnTheSecondRow(
                    tuple(
                        balance if row.actor_identity == balance.actor_identity
                        else row
                        for row in self.balances),
                    self.generation + 1,
                    self.scene,
                )

        calls: list = []
        angry = RaisesOnTheSecondRow(real.balances)
        (result_register, result_ledger), line = quiet(
            graves.seed_the_session_state, before, angry, BG1)
        self.assertEqual(len(calls), 2)
        self.assertIs(result_register, before)
        self.assertIs(result_ledger, angry)
        self.assertEqual(
            result_ledger.balance_of(first.actor_identity).current_hp,
            first.max_hp)
        self.assertEqual(
            result_ledger.balance_of(second.actor_identity).current_hp,
            second.max_hp)
        self.assertIn(graves.WORLD_SEED_REFUSED_TOKEN, line)
        self.assertIn(graves.REFUSE_LEDGER_REFUSED_THE_ROW, line)
        # `repopulation_entries` requires an exact `mob_combat.CombatLedger`
        # (the mock subclass above is not one); rebuild a plain ledger from
        # what this call actually returned to prove it is really the
        # untouched, fully-alive ledger the real call site would have kept.
        plain = mob_combat.CombatLedger(
            result_ledger.balances, result_ledger.generation,
            result_ledger.scene)
        entries = mob_death.repopulation_entries(
            self.legacy, self.roster, result_register, ledger=plain)
        self.assertEqual(len(entries), len(self.roster))

    def test_a_repeat_changes_nothing_and_says_nothing(self):
        self._kill_in_a_first_session()
        ledger = mob_combat.open_ledger(self.roster, scene=BG1)
        with contextlib.redirect_stdout(io.StringIO()):
            register, ledger = graves.seed_the_session_state(
                mob_death.DeathRegister(), ledger, BG1)
        (again, ledger_again), line = quiet(
            graves.seed_the_session_state, register, ledger, BG1)
        self.assertIs(again, register)
        self.assertIs(ledger_again, ledger)
        self.assertEqual(line, "")

    def test_the_console_says_how_many_ledger_rows_it_zeroed(self):
        self._kill_in_a_first_session()
        ledger = mob_combat.open_ledger(self.roster, scene=BG1)
        _pair, line = quiet(
            graves.seed_the_session_state, mob_death.DeathRegister(), ledger,
            BG1)
        self.assertIn(graves.WORLD_SEEDED_TOKEN, line)
        self.assertIn("ledger_zeroed=1", line)


class TheDoorsThatMustNotFailOpenTests(unittest.TestCase):
    """pf-adversary, second pass: refusals that were silent fallbacks."""

    def setUp(self) -> None:
        self.world = graves.install_world_deaths(graves.WorldDeaths())
        graves.forget_roster_cache()

    def tearDown(self) -> None:
        graves.install_world_deaths(graves.WorldDeaths())
        graves.forget_roster_cache()

    def test_a_world_that_is_not_a_grave_book_is_refused_not_ignored(self):
        # The worst shape a door can have: a caller asking for isolation,
        # mistyping the argument, and silently getting the process-global
        # book it was opting out of, under a line that says it worked.
        outcome, line = quiet(
            graves.remember_death, a_record(), world=object())
        self.assertFalse(outcome.buried)
        self.assertEqual(outcome.reason, graves.REFUSE_NOT_A_GRAVE_BOOK)
        self.assertIn(graves.WORLD_REMEMBER_REFUSED_TOKEN, line)
        self.assertFalse(self.world.is_buried(BG2, SOLDIER))

    def test_a_seed_with_a_bogus_world_is_refused_not_ignored(self):
        outcome = graves.seed_register(
            mob_death.DeathRegister(), BG2, world=object())
        self.assertEqual(outcome.reason, graves.REFUSE_NOT_A_GRAVE_BOOK)

    def test_a_ceiling_the_roster_does_not_carry_is_refused_by_name(self):
        # `repopulation_entries` refuses on the ceiling as well as on the
        # identity, so a gate that checked only the identity could still
        # empty a town for the life of the process.
        real = roster_ceiling(SOLDIER, BG2)
        self.assertEqual(
            self.world.bury(a_record(max_hp=real + 1)),
            (False, graves.REFUSE_CEILING_IS_NOT_THE_ROSTERS))
        self.assertEqual(self.world.bury(a_record(max_hp=real)), (True, ""))

    def test_a_roster_that_raises_once_is_not_refused_forever(self):
        real = field_mobs.load_roster
        calls = []

        def angry(scene, *args, **kwargs):
            calls.append(scene)
            if len(calls) == 1:
                raise RuntimeError("transient")
            return real(scene, *args, **kwargs)

        # Built BEFORE the patch: `a_record` reads the roster for its own
        # ceiling, and it would otherwise eat the one transient raise.
        record = a_record()
        field_mobs.load_roster = angry
        try:
            first = self.world.bury(record)
            second = self.world.bury(record)
        finally:
            field_mobs.load_roster = real
        self.assertEqual(first, (False, graves.REFUSE_SCENE_HAS_NO_MINED_ROSTER))
        self.assertEqual(second, (True, ""))

    def test_the_roster_cache_has_a_clearing_seam(self):
        self.world.bury(a_record())
        graves.forget_roster_cache()
        self.assertEqual(self.world.bury(a_record(identity=BG2_ROWS[0])),
                         (True, ""))

    def test_installing_something_that_is_not_a_book_raises(self):
        with self.assertRaises(TypeError):
            graves.install_world_deaths(object())

    def test_a_broken_persistence_door_is_named_on_the_console(self):
        # "the module is broken" and "chief has not wired the seam yet" must
        # not have the same signature, because that signature is silence and
        # the write half's whole evidence is a console line.
        register = mob_death.DeathRegister()
        record = a_record()
        step = a_step(record, register)
        real = graves.remember_death

        def broken(*args, **kwargs):
            raise RuntimeError("the door is gone")

        graves.remember_death = broken
        try:
            after, line = quiet(mob_death.commit_death, register, step)
        finally:
            graves.remember_death = real
        self.assertTrue(after.is_dead(SOLDIER, BG2))
        self.assertIn("MOB_DEATH_WORLD_REMEMBER_REFUSED", line)
        self.assertIn("persistence_door_raised", line)


class TheLaneGateTests(unittest.TestCase):

    def test_this_module_ships_without_a_scenario_flag(self):
        self.assertIs(graves.production_allowed, True)


if __name__ == "__main__":
    unittest.main()
