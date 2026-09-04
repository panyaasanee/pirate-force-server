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
call site only chief may add (`mob_death_persistence.seed_the_session_register`
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

from pirateforce_foundation import mob_death                          # noqa: E402
from pirateforce_foundation import mob_death_persistence as graves    # noqa: E402
from pirateforce_foundation import field_mobs                         # noqa: E402

#: The scene tags are the folder registry's own spelling, which is what
#: `world_scene_folder.scene_folder_for_scene_id` hands the call site and what
#: every mined table's `SCENE` constant carries.  Scene 2 is capitalised and
#: scene 1 is not -- that asymmetry is real and it is why this file tests the
#: fold.
BG1 = "bg0001"
BG2 = "Bg0002"

#: The monster R309 actually killed, and the ceiling it actually stood at.
SOLDIER = 0x203D
SOLDIER_MAX_HP = 3138
KILLER = 0x750059


def a_record(identity=SOLDIER, scene=BG2, killer=KILLER,
             max_hp=SOLDIER_MAX_HP):
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
            self.world.bury(a_record(max_hp=1, killer=0x999)), (False, ""))
        held = self.world.buried_in(BG2)[0]
        self.assertEqual((held.max_hp, held.killer_identity),
                         (SOLDIER_MAX_HP, KILLER))

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
        self.assertEqual(small.bury(a_record(identity=0x2001)), (True, ""))
        self.assertEqual(small.bury(a_record(identity=0x2002)), (True, ""))
        self.assertEqual(small.bury(a_record(identity=0x2003)),
                         (False, graves.REFUSE_SCENE_IS_FULL))
        # The failure this cap must NOT have: an older corpse standing back
        # up because a newer one needed the room.
        self.assertTrue(small.is_buried(BG2, 0x2001))
        self.assertTrue(small.is_buried(BG2, 0x2002))
        self.assertFalse(small.is_buried(BG2, 0x2003))

    def test_forget_is_the_respawn_door_and_removes_only_one_grave(self):
        self.world.bury(a_record(identity=0x2001))
        self.world.bury(a_record(identity=0x2002))
        self.assertTrue(self.world.forget(BG2, 0x2001))
        self.assertFalse(self.world.forget(BG2, 0x2001))
        self.assertEqual(
            tuple(r.actor_identity for r in self.world.buried_in(BG2)),
            (0x2002,))

    def test_clear_empties_every_scene(self):
        self.world.bury(a_record(scene=BG1))
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
        for identity in (0x2001, 0x2002, 0x2003):
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
        graves.remember_death(
            a_record(identity=SOLDIER, scene=BG2),
            world=self.world, announce=False)
        graves.remember_death(
            a_record(identity=SOLDIER, scene=BG1),
            world=self.world, announce=False)
        seeded = graves.seed_register(
            self.empty, BG2, world=self.world).register
        self.assertTrue(seeded.is_dead(SOLDIER, BG2))
        self.assertFalse(seeded.is_dead(SOLDIER, BG1))
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
        self.assertEqual(
            seeded.record_of(SOLDIER, BG2).max_hp, SOLDIER_MAX_HP)

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
            a_record(identity=0x2001), world=self.world, announce=False)
        seeded = graves.seed_register(
            mob_death.DeathRegister(), BG2, world=self.world).register
        self.assertEqual(seeded.generation, 1)
        record = a_record(identity=SOLDIER)
        step = a_step(record, seeded, base_generation=seeded.generation)
        with contextlib.redirect_stdout(io.StringIO()):
            after = mob_death.commit_death(seeded, step)
        self.assertTrue(after.is_dead(0x2001, BG2))
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
            "seed_the_session_register", graves.DEATH_SEED_WIRING)
        self.assertIn("_sync_combat_scene_state", graves.DEATH_SEED_WIRING)
        self.assertIn("mob_death_persistence", graves.DEATH_SEED_WIRING)
        graves.DEATH_SEED_WIRING.encode("ascii")
        self.assertTrue(hasattr(graves, "seed_the_session_register"))


class TheLaneGateTests(unittest.TestCase):

    def test_this_module_ships_without_a_scenario_flag(self):
        self.assertIs(graves.production_allowed, True)


if __name__ == "__main__":
    unittest.main()
