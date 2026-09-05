"""LANE-B: the respawn door, and the end-to-end proof that a scene refills.

WHAT THIS FILE MEASURES, AND WHY IT IS NOT A UNIT-TEST FILE WITH ONE
END-TO-END TEST BOLTED ON.  The claim of round ``qamp70`` is a claim about
what a player sees, so the last class here (:class:`SceneOpenProofTests`)
replays ``runtime.py``'s OWN scene-open block -- ``mob_combat.open_ledger``
at the table's ceiling, then one zero-balance per row in the session death
register -- against a real bg0001 roster and a real kill, twice: with the
sweep and without it.  Without it the monster is at 0 of its ceiling forever;
with it, and only after the delay has passed, the same block leaves it at the
ceiling.  That is the whole feature, measured where it happens rather than
asserted about.

NO BRIDGE CLONE REQUIRED.  Nothing here is
``@BRIDGE_GAMEDATA.skip_unless_present()``: the Windows gate runs with no
``pf_bridge`` beside it (``NOW.md``), and a respawn test that skips there is
a respawn test that never ran.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs
from pirateforce_foundation import mob_combat
from pirateforce_foundation import mob_death
from pirateforce_foundation import mob_respawn
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import (
    DeathRecord,
    DeathRegister,
    MobDeathContractError,
)

PERFORMER = 0x750059
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)
RUNTIME = ROOT / "src" / "pirateforce_foundation" / "runtime.py"


def grave(identity: int, *, scene: str = mob_death.DEFAULT_SCENE,
          buried_at=None) -> DeathRecord:
    """One record, with the clock as the caller wants it."""
    return DeathRecord(identity, PERFORMER, 100, scene, buried_at)


class ClockOnTheRecordTests(unittest.TestCase):
    """``buried_at`` is metadata about a grave, not part of which grave."""

    def test_a_record_defaults_to_no_clock(self):
        # The default is what every caller in this tree built before this
        # round, and it must keep meaning "never respawns".
        self.assertIsNone(grave(0x2011).buried_at)

    def test_two_records_are_equal_whatever_their_clocks_say(self):
        # The register's own header promises that two registers built from
        # the same kills compare equal IN ANY PROCESS.  A monotonic reading
        # is different in every process, so it must not reach __eq__.
        early = grave(0x2011, buried_at=1.0)
        late = grave(0x2011, buried_at=999_999.0)
        self.assertEqual(early, late)
        self.assertEqual(hash(early), hash(late))
        self.assertEqual(early, grave(0x2011))

    def test_the_clock_stays_out_of_the_repr(self):
        # Same reason as __eq__: a repr that changes run to run breaks every
        # golden-line comparison in this tree, silently.
        self.assertNotIn("buried_at", repr(grave(0x2011, buried_at=5.0)))

    def test_a_negative_reading_is_refused_by_name(self):
        with self.assertRaises(MobDeathContractError) as caught:
            grave(0x2011, buried_at=-1.0)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_CLOCK_NOT_A_READING)

    def test_a_bool_is_refused_by_name(self):
        # isinstance(True, int) is True in this language: buried_at=True
        # would be a grave one second old on every clock in the process.
        with self.assertRaises(MobDeathContractError) as caught:
            grave(0x2011, buried_at=True)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_CLOCK_NOT_A_READING)

    def test_a_non_number_is_refused_by_name(self):
        with self.assertRaises(MobDeathContractError) as caught:
            grave(0x2011, buried_at="now")
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_CLOCK_NOT_A_READING)


class KillLeavesTheGraveUndatedTests(unittest.TestCase):
    """``mob_death`` stays clockless, and this is where that is written down.

    Not an accident to be tidied up by a later round: ``mob_death.py``'s own
    test refuses ``time`` in that file's imports beside ``socket`` and
    ``random``.  So the grave leaves ``kill()`` undated and this lane's sweep
    dates it -- the consequence for what the delay is measured FROM is stated
    in ``mob_respawn``'s docstring and in this round's letter.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [
            m for m in cls.roster
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]

    def test_a_real_kill_leaves_the_grave_undated(self):
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER,
            LETHAL)
        death = mob_death.kill(
            self.legacy, self.mob, step.outcome, DeathRegister(),
            widened=mob_death.ruling_for(self.mob))
        self.assertIsNone(death.record.buried_at)

    def test_mob_death_still_imports_no_clock(self):
        # The pin this design bends to.  Stated here as well as in
        # tests/test_mob_death.py so that a future round reading THIS file
        # learns why the dating lives where it does.
        #
        # OVER THE AST, not over the text (pf-adversary D10): a substring
        # check for "\nimport time" is passed by `from time import
        # monotonic`, by `import time, math`, and by two spaces after the
        # keyword -- three spellings that would each put a clock back into
        # that module while this test stayed green and claimed to be the
        # same pin tests/test_mob_death.py holds.
        import ast

        tree = ast.parse(
            (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
                encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        self.assertNotIn("time", imported)


class SweepTests(unittest.TestCase):
    """The door itself."""

    def test_a_grave_past_the_delay_is_opened(self):
        register = DeathRegister((grave(0x2011, buried_at=10.0),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertTrue(outcome.swept)
        self.assertEqual(outcome.opened,
                         ((mob_death.DEFAULT_SCENE, 0x2011),))
        self.assertEqual(swept.records, ())
        self.assertFalse(swept.is_dead(0x2011))

    def test_the_generation_moves_only_when_a_grave_opens(self):
        # A register that lost a row is a different reading, and a kill
        # computed against the old one must retry rather than commit on top.
        register = DeathRegister((grave(0x2011, buried_at=10.0),), 7)
        swept, _ = mob_respawn.sweep_the_session_register(
            register, now=10.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(swept.generation, 8)

    def test_a_sweep_that_opens_nothing_hands_back_the_same_object(self):
        # Not an equal copy: a caller that stores what it is handed must not
        # invalidate an in-flight commit_death for nothing.
        register = DeathRegister((grave(0x2011, buried_at=10.0),), 7)
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertIs(swept, register)
        self.assertEqual(outcome.kept_too_young, 1)
        self.assertEqual(outcome.opened, ())

    def test_one_second_short_of_the_delay_stays_buried(self):
        register = DeathRegister((grave(0x2011, buried_at=10.0),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=9.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertIs(swept, register)
        self.assertEqual(outcome.kept_too_young, 1)

    def test_exactly_the_delay_opens_the_grave(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(len(outcome.opened), 1)

    def test_an_undated_grave_is_dated_and_kept_by_the_same_sweep(self):
        # Never opened in the breath that dated it: "I do not know how old
        # this is" must not read as "it is old enough".
        register = DeathRegister((grave(0x2011),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0 ** 9, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.opened, ())
        self.assertEqual(outcome.dated, 1)
        self.assertIsNot(swept, register)
        self.assertEqual(
            swept.record_of(0x2011).buried_at, 10.0 ** 9)

    def test_dating_does_not_move_the_generation(self):
        # `buried_at` is compare=False, so the two registers are the same
        # VALUE; bumping the counter would lose a racing kill for nothing.
        register = DeathRegister((grave(0x2011),), 7)
        swept, _ = mob_respawn.sweep_the_session_register(register, now=1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(swept.generation, 7)
        self.assertEqual(swept, register)

    def test_the_sweep_after_the_dating_one_opens_the_grave(self):
        # The whole two-scene-change shape, end to end on the door itself.
        register = DeathRegister((grave(0x2011),))
        once, first = mob_respawn.sweep_the_session_register(
            register, now=100.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(first.dated, 1)
        twice, second = mob_respawn.sweep_the_session_register(
            once, now=100.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(second.opened,
                         ((mob_death.DEFAULT_SCENE, 0x2011),))
        self.assertEqual(twice.records, ())

    def test_a_dated_grave_is_not_redated_by_a_later_sweep(self):
        # If it were, no grave would ever age: every scene change would
        # restart the clock and the monster would never come back.
        register = DeathRegister((grave(0x2011),))
        once, _ = mob_respawn.sweep_the_session_register(register, now=100.0, world=mob_respawn.NO_WORLD_BOOK)
        twice, outcome = mob_respawn.sweep_the_session_register(
            once, now=101.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.dated, 0)
        self.assertEqual(outcome.kept_too_young, 1)
        self.assertIs(twice, once)
        self.assertEqual(twice.record_of(0x2011).buried_at, 100.0)

    def test_a_reading_older_than_the_grave_opens_nothing(self):
        register = DeathRegister((grave(0x2011, buried_at=100.0),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertIs(swept, register)
        self.assertEqual(outcome.kept_clock_went_backwards, 1)

    def test_only_the_old_graves_leave_and_the_rest_keep_their_order(self):
        register = DeathRegister((
            grave(0x2011, buried_at=0.0),
            grave(0x2012, buried_at=10_000.0),
            grave(0x2013, buried_at=0.0),
        ))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(
            outcome.opened,
            ((mob_death.DEFAULT_SCENE, 0x2011),
             (mob_death.DEFAULT_SCENE, 0x2013)))
        self.assertEqual(swept.identities(), (0x2012,))
        self.assertEqual(outcome.kept_too_young, 1)

    def test_two_scenes_are_two_graves(self):
        # The register is keyed by (scene, identity) and the sweep must not
        # collapse that: opening a grave in one scene may not empty another.
        register = DeathRegister(tuple(sorted((
            grave(0x2011, scene="bg0001", buried_at=0.0),
            grave(0x2011, scene="Bg0002", buried_at=10_000.0),
        ), key=lambda row: (row.scene, row.actor_identity))))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.opened, (("bg0001", 0x2011),))
        self.assertTrue(swept.is_dead(0x2011, "Bg0002"))
        self.assertFalse(swept.is_dead(0x2011, "bg0001"))

    def test_a_backwards_row_survives_a_sweep_that_rebuilds_the_register(
            self):
        # THE MUTANT THAT SURVIVED (pf-adversary D6/M6): dropping the
        # `keep.append(record)` from the clock-went-backwards branch passed
        # all 44 tests, because no test ever put a backwards row in the same
        # register as a dated or opened one -- and `keep` is only consulted
        # when something moved.  The mutant silently resurrects a monster
        # that is NOT in `opened`, is not counted, and does not bump the
        # generation, so nothing anywhere says it happened.
        register = DeathRegister((
            grave(0x2011, buried_at=100.0),   # reading is older: backwards
            grave(0x2012),                    # undated: dated this sweep
        ))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.kept_clock_went_backwards, 1)
        self.assertEqual(outcome.dated, 1)
        self.assertEqual(swept.identities(), (0x2011, 0x2012))
        self.assertEqual(swept.record_of(0x2011).buried_at, 100.0)

    def test_a_too_young_row_survives_a_sweep_that_opens_another(self):
        # The same shape for the other keep branch: a register where one row
        # ages out and another does not must not lose the second.
        register = DeathRegister((
            grave(0x2011, buried_at=0.0),
            grave(0x2012, buried_at=10_000.0),
        ))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.kept_too_young, 1)
        self.assertEqual(swept.identities(), (0x2012,))

    def test_a_custom_delay_is_honoured(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=5.0, delay=5.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(len(outcome.opened), 1)


class SweepRefusalTests(unittest.TestCase):
    """Every failure is a named value, never an exception into the caller."""

    def test_a_foreign_register_is_refused_by_name(self):
        swept, outcome = mob_respawn.sweep_the_session_register(object(), world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.refusal, mob_respawn.REFUSE_NOT_A_REGISTER)
        self.assertFalse(outcome.swept)
        self.assertIsInstance(swept, object)

    def test_a_delay_past_the_ceiling_is_refused_by_name(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0 ** 9,
            delay=mob_respawn.MAX_RESPAWN_DELAY_SECONDS + 1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(
            outcome.refusal, mob_respawn.REFUSE_DELAY_NOT_A_DURATION)
        self.assertIs(swept, register)

    def test_a_negative_delay_is_refused_by_name(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1.0, delay=-1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(
            outcome.refusal, mob_respawn.REFUSE_DELAY_NOT_A_DURATION)

    def test_a_bool_delay_is_refused_by_name(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1.0, delay=True, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(
            outcome.refusal, mob_respawn.REFUSE_DELAY_NOT_A_DURATION)

    def test_a_negative_now_is_refused_by_name(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=-1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.refusal, mob_respawn.REFUSE_NOW_NOT_A_READING)

    def test_a_non_numeric_now_is_refused_by_name(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now="later", world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.refusal, mob_respawn.REFUSE_NOW_NOT_A_READING)

    def test_the_real_clock_is_used_when_now_is_omitted(self):
        # runtime.py passes no `now`, so the omitted path is the production
        # path and it must actually read a clock rather than refuse.
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(register, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.refusal, "")


class WorldBookTests(unittest.TestCase):
    """The shared half: one door opens both books."""

    def test_the_world_book_is_told_about_every_grave_opened(self):
        # A REAL roster row: WorldDeaths.bury refuses an identity the mined
        # roster does not carry (identity_not_in_the_mined_roster), which is
        # its own gate and not this module's to weaken.
        from pirateforce_foundation import mob_death_persistence

        mob = [
            m for m in field_mobs.load_roster()
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]
        world = mob_death_persistence.WorldDeaths()
        record = DeathRecord(
            mob.actor_identity, PERFORMER, mob.max_hp, mob.scene, 0.0)
        buried, reason = world.bury(record)
        self.assertTrue(buried, reason)
        register = DeathRegister((record,))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=world)
        self.assertEqual(outcome.world_forgot, 1)
        self.assertFalse(world.is_buried(mob.scene, mob.actor_identity))

    def test_the_default_reaches_the_book_every_production_kill_is_in(self):
        # THE FINDING THAT MADE THIS THE DEFAULT (pf-adversary D2): a draft
        # of this module claimed the world grave book had no production
        # writer.  It has had one all along -- mob_death.commit_death calls
        # remember_death(step.record, world=world) on every accepted kill and
        # remember_death resolves world=None to world_deaths().  A sweep that
        # moved only the session register would leave the two books
        # disagreeing about one monster, which is the failure this whole area
        # exists to avoid.
        from pirateforce_foundation import mob_death_persistence

        mob = [
            m for m in field_mobs.load_roster()
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]
        book = mob_death_persistence.world_deaths()
        record = DeathRecord(
            mob.actor_identity, PERFORMER, mob.max_hp, mob.scene, 0.0)
        book.forget(mob.scene, mob.actor_identity)
        buried, reason = book.bury(record)
        self.assertTrue(buried, reason)
        try:
            # NO world= argument at all: exactly what the published order
            # tells the chief to paste.
            _swept, outcome = mob_respawn.sweep_the_session_register(
                DeathRegister((record,)), now=10_000.0)
            self.assertEqual(outcome.world_forgot, 1)
            self.assertFalse(book.is_buried(mob.scene, mob.actor_identity))
        finally:
            book.forget(mob.scene, mob.actor_identity)

    def test_a_burial_really_does_reach_the_process_book_through_a_kill(self):
        # The other half of D2, measured through the production door rather
        # than asserted about: commit_death with no world= buries into the
        # singleton.  If this ever stops being true, the default above is
        # sweeping a book nothing writes and this file must be re-argued.
        from pirateforce_foundation import mob_death_persistence

        legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        roster = field_mobs.load_roster()
        mob = [
            m for m in roster
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]
        book = mob_death_persistence.world_deaths()
        book.forget(mob.scene, mob.actor_identity)
        try:
            step = strike(
                legacy, None, open_ledger(), None, mob, PERFORMER, LETHAL)
            death = mob_death.kill(
                legacy, mob, step.outcome, DeathRegister(),
                widened=mob_death.ruling_for(mob))
            mob_death.commit_death(DeathRegister(), death, announce=False)
            self.assertTrue(book.is_buried(mob.scene, mob.actor_identity))
        finally:
            book.forget(mob.scene, mob.actor_identity)

    def test_a_world_that_raises_is_counted_not_thrown_and_not_a_refusal(self):
        class Angry:
            def forget(self, scene, actor_identity):
                raise RuntimeError("books on fire")

        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=Angry())
        # NOT a refusal: this sweep ran and the session register really did
        # lose the row.  Calling it a refusal made `swept` read False for a
        # sweep that had changed the register -- pf-adversary D4.
        self.assertEqual(outcome.refusal, "")
        self.assertTrue(outcome.swept)
        self.assertEqual(outcome.world_failed, 1)
        self.assertIn(mob_respawn.WORLD_RAISED, outcome.world_detail)
        self.assertEqual(swept.records, ())

    def test_a_book_that_raises_on_one_grave_is_still_asked_about_the_rest(
            self):
        # THE MUTANT THAT SURVIVED (pf-adversary D6/M7): with `break` instead
        # of `continue`, one transient failure on the second of three graves
        # orphaned the third on the process book for ever -- and an orphan
        # there is a row a future DEATH_SEED_WIRING re-admits UNDATED, so it
        # would never age out again either.
        class AngryAboutOne:
            def __init__(self):
                self.asked = []

            def forget(self, scene, actor_identity):
                self.asked.append(actor_identity)
                if actor_identity == 0x2012:
                    raise RuntimeError("books on fire")
                return True

        world = AngryAboutOne()
        register = DeathRegister((
            grave(0x2011, buried_at=0.0),
            grave(0x2012, buried_at=0.0),
            grave(0x2013, buried_at=0.0),
        ))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=world)
        self.assertEqual(world.asked, [0x2011, 0x2012, 0x2013])
        self.assertEqual(outcome.world_forgot, 2)
        self.assertEqual(outcome.world_failed, 1)

    def test_no_world_book_is_a_counted_state_not_a_failure(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertTrue(outcome.swept)
        self.assertEqual(outcome.world_forgot, 0)
        self.assertEqual(outcome.world_failed, 0)
        self.assertIn("NO_WORLD_BOOK", outcome.world_detail)


class ConsoleTests(unittest.TestCase):

    def test_a_sweep_that_moved_nothing_says_nothing(self):
        register = DeathRegister((grave(0x2011, buried_at=10.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(mob_respawn.describe_sweep(outcome), ())

    def test_a_dating_only_sweep_still_says_so(self):
        # pf-adversary D8: a silent dating sweep is indistinguishable from
        # the statement never being pasted, or from a paste that raised
        # inside a caught branch -- for the first two minutes of every wipe,
        # which is the whole window somebody would be checking in.
        register = DeathRegister((grave(0x2011),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10.0, world=mob_respawn.NO_WORLD_BOOK)
        lines = mob_respawn.describe_sweep(outcome)
        self.assertTrue(lines)
        self.assertTrue(any("dated=1" in line for line in lines), lines)

    def test_every_opened_grave_gets_a_greppable_line(self):
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        lines = mob_respawn.describe_sweep(outcome)
        self.assertTrue(
            any(line.startswith(mob_respawn.RESPAWN_TOKEN + " scene=")
                and "0x2011" in line for line in lines), lines)

    def test_the_per_grave_line_claims_a_removal_not_a_resurrection(self):
        # pf-adversary D7: this function has not seen the ledger, does not
        # know which scene is being opened, and composes no frame -- so
        # "alive_again" would be a bookkeeping delta wearing the goal's name,
        # and a sweep fired while walking into a DIFFERENT scene would grep
        # as the feature working.
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        lines = mob_respawn.describe_sweep(outcome)
        self.assertTrue(
            any("removed_from_the_death_register" in line for line in lines),
            lines)
        for line in lines:
            self.assertNotIn("alive_again", line)

    def test_a_world_failure_prints_its_own_line_beside_the_removals(self):
        class Angry:
            def forget(self, scene, actor_identity):
                raise RuntimeError("books on fire")

        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=Angry())
        lines = mob_respawn.describe_sweep(outcome)
        self.assertTrue(
            any(line.startswith(mob_respawn.RESPAWN_REFUSED_TOKEN)
                and mob_respawn.WORLD_RAISED in line for line in lines),
            lines)

    def test_a_wrongly_typed_argument_is_named_not_silent(self):
        # pf-adversary D11: describe_sweep(register) is one transposition
        # away from describe_sweep(outcome), and answering it with () looks
        # exactly like the quiet case.
        lines = mob_respawn.describe_sweep(DeathRegister())
        self.assertTrue(lines)
        self.assertIn(mob_respawn.REFUSE_NOT_AN_OUTCOME, lines[0])

    def test_a_refusal_uses_its_own_token(self):
        _swept, outcome = mob_respawn.sweep_the_session_register(object(), world=mob_respawn.NO_WORLD_BOOK)
        lines = mob_respawn.describe_sweep(outcome)
        self.assertTrue(lines)
        self.assertTrue(lines[0].startswith(mob_respawn.RESPAWN_REFUSED_TOKEN))

    def test_every_console_line_is_ascii(self):
        # The bridge console is cp874: a non-ASCII byte here is a crash on
        # the machine that reads these lines.
        register = DeathRegister((grave(0x2011, buried_at=0.0),))
        _swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=10_000.0, world=mob_respawn.NO_WORLD_BOOK)
        for line in mob_respawn.describe_sweep(outcome):
            line.encode("ascii")


class SceneOpenProofTests(unittest.TestCase):
    """Replay runtime.py's own scene-open block, with and without the sweep.

    This is the round's player-visible claim, headless.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [
            m for m in cls.roster
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]

    def a_real_kill(self):
        """One real strike-to-zero and its commit, exactly as runtime does."""
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER,
            LETHAL)
        death = mob_death.kill(
            self.legacy, self.mob, step.outcome, DeathRegister(),
            widened=mob_death.ruling_for(self.mob))
        return mob_death.commit_death(DeathRegister(), death)

    def a_real_kill_dated_at(self, when):
        """...and the first scene change after it, which starts its clock."""
        dated, outcome = mob_respawn.sweep_the_session_register(
            self.a_real_kill(), now=when, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.dated, 1)
        return dated

    def open_the_scene(self, register):
        """runtime.py:_sync_combat_scene_state's ledger block, verbatim shape.

        Kept deliberately close to the original so that a reader can compare
        the two: open at the table's ceiling, then zero one balance per row
        the register still calls dead.
        """
        folder = self.mob.scene
        ledger = mob_combat.open_ledger(self.roster, scene=folder)
        ledger_identities = ledger.identities()
        for record in register.records:
            if (record.scene == folder
                    and record.actor_identity in ledger_identities):
                ledger = ledger.with_balance(mob_combat.MobBalance(
                    record.actor_identity,
                    ledger.balance_of(record.actor_identity).max_hp,
                    0,
                ))
        return ledger

    def test_without_the_sweep_the_monster_is_a_corpse_for_ever(self):
        # This is main's behaviour today, pinned here so the round after this
        # one cannot mistake the fix for something that was always true.
        register = self.a_real_kill()
        ledger = self.open_the_scene(register)
        balance = ledger.balance_of(self.mob.actor_identity)
        self.assertEqual(balance.current_hp, 0)

    def test_before_the_delay_the_scene_still_opens_on_a_corpse(self):
        register = self.a_real_kill_dated_at(1000.0)
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1000.0 + mob_respawn.RESPAWN_DELAY_SECONDS - 1.0, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(outcome.opened, ())
        ledger = self.open_the_scene(swept)
        self.assertEqual(
            ledger.balance_of(self.mob.actor_identity).current_hp, 0)

    def test_after_the_delay_the_scene_opens_with_the_monster_standing(self):
        register = self.a_real_kill_dated_at(1000.0)
        swept, outcome = mob_respawn.sweep_the_session_register(
            register, now=1000.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        self.assertEqual(len(outcome.opened), 1)
        ledger = self.open_the_scene(swept)
        balance = ledger.balance_of(self.mob.actor_identity)
        self.assertEqual(balance.current_hp, balance.max_hp)
        self.assertEqual(balance.max_hp, self.mob.max_hp)

    def test_the_respawned_row_agrees_with_the_register(self):
        # The failure this whole shape exists to avoid: a ledger and a
        # register that disagree, which repopulation_entries refuses at a
        # call site whose refusal unwinds the listener thread.
        register = self.a_real_kill_dated_at(1000.0)
        swept, _ = mob_respawn.sweep_the_session_register(
            register, now=1000.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        ledger = self.open_the_scene(swept)
        # `is not None` was the assertion here and it could not fail
        # (pf-adversary D10): repopulation_entries returns a list on every
        # non-raising path, so the test would have passed on a composer that
        # shipped no actor at all.  What is actually being measured is that
        # the pair does not raise ledger_disagrees_with_register AND that the
        # respawned monster is in the result at its ceiling.
        entries = mob_death.repopulation_entries(
            self.legacy, self.roster, swept, ledger=ledger)
        # The strongest thing that can be said about a list of composed
        # bytes: after the respawn, this scene is composed BYTE FOR BYTE the
        # way a session that never killed anything composes it.
        virgin = mob_death.repopulation_entries(
            self.legacy, self.roster, DeathRegister(),
            ledger=mob_combat.open_ledger(self.roster, scene=self.mob.scene))
        self.assertTrue(entries)
        self.assertEqual(entries, virgin)
        self.assertEqual(
            ledger.balance_of(self.mob.actor_identity).current_hp,
            self.mob.max_hp)

    def test_the_corpse_case_composes_differently_from_the_respawned_one(self):
        # The control for the byte comparison above: if a grave changed
        # nothing about the composed entries, that assertion would be
        # measuring nothing at all.
        register = self.a_real_kill()
        ledger = self.open_the_scene(register)
        buried = mob_death.repopulation_entries(
            self.legacy, self.roster, register, ledger=ledger)
        virgin = mob_death.repopulation_entries(
            self.legacy, self.roster, DeathRegister(),
            ledger=mob_combat.open_ledger(self.roster, scene=self.mob.scene))
        self.assertNotEqual(buried, virgin)

    def test_a_register_still_holding_the_grave_disagrees_with_a_full_ledger(
            self):
        # The negative control for the test above: the refusal it is meant to
        # be avoiding must be reachable, or "it did not raise" says nothing.
        register = self.a_real_kill()
        full = mob_combat.open_ledger(self.roster, scene=self.mob.scene)
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.repopulation_entries(
                self.legacy, self.roster, register, ledger=full)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_LEDGER_DISAGREES_WITH_REGISTER)

    def test_the_other_monsters_are_untouched_by_a_respawn(self):
        register = self.a_real_kill_dated_at(1000.0)
        swept, _ = mob_respawn.sweep_the_session_register(
            register, now=1000.0 + mob_respawn.RESPAWN_DELAY_SECONDS, world=mob_respawn.NO_WORLD_BOOK)
        ledger = self.open_the_scene(swept)
        for mob in self.roster:
            balance = ledger.balance_of(mob.actor_identity)
            self.assertEqual(balance.current_hp, balance.max_hp)


class WiringLineTests(unittest.TestCase):
    """The order this module publishes must name lines runtime.py really has.

    A wiring string that names an anchor no longer in the file is how round
    ``a7k5gy`` shipped a gate argument that was False on every frame for
    three days.  This file reads runtime.py rather than trusting the prose.
    """

    @classmethod
    def setUpClass(cls):
        cls.runtime_source = RUNTIME.read_text(encoding="utf-8")

    def test_nothing_in_runtime_py_calls_the_sweep_yet(self):
        # THE PINNED NEGATIVE.  The day chief pastes MOB_RESPAWN_WIRING this
        # test is FLIPPED, in this lane's own file, not deleted.
        self.assertNotIn("mob_respawn", self.runtime_source)

    def test_the_order_names_an_anchor_that_exists(self):
        self.assertIn(
            "for record in self.mob_death_register.records:",
            self.runtime_source)
        self.assertIn("ledger_identities = ledger.identities()",
                      self.runtime_source)
        for anchor in ("for record in self.mob_death_register.records:",
                       "ledger_identities = ledger.identities()"):
            self.assertIn(anchor, mob_respawn.MOB_RESPAWN_WIRING)

    def test_each_anchor_appears_exactly_once_in_runtime_py(self):
        # An order that names an anchor appearing twice is an order that can
        # be pasted into the wrong block and still look obeyed.  Round
        # a7k5gy is what that costs: three days of a gate that was False on
        # every frame, with nothing red anywhere.
        for anchor in ("for record in self.mob_death_register.records:",
                       "ledger_identities = ledger.identities()"):
            self.assertEqual(
                self.runtime_source.count(anchor), 1, anchor)

    def test_the_order_names_the_function_it_asks_to_be_called(self):
        self.assertIn("sweep_the_session_register",
                      mob_respawn.MOB_RESPAWN_WIRING)
        self.assertTrue(hasattr(mob_respawn, "sweep_the_session_register"))

    def test_every_runtime_name_the_order_uses_exists_in_runtime_py(self):
        # pf-adversary D5: a draft told the chief to paste
        # `print(console_safe(line))`.  There is no bare `console_safe` in
        # runtime.py -- both real uses are `lane_hooks.console_safe(...)` --
        # so the paste would have been a NameError on the scene-open path,
        # inside a branch `_sync_combat_scene_at_edge` catches, i.e. no
        # crash, no respawn, and a refusal line nobody was looking for.
        self.assertIn("lane_hooks.console_safe",
                      mob_respawn.MOB_RESPAWN_WIRING)
        self.assertNotIn("print(console_safe",
                         mob_respawn.MOB_RESPAWN_WIRING)
        self.assertIn("lane_hooks.console_safe", self.runtime_source)

    def test_the_order_keeps_the_death_register_inside_the_atomic_block(self):
        # pf-adversary D3: the three field assignments at the bottom of that
        # branch are atomic ON PURPOSE (runtime.py says so in its own
        # comment, from round pk14rf), because mob_ai_control.open_register
        # between them and the loop can raise by design.  An order that
        # assigns self.mob_death_register ABOVE that raise point tears the
        # session's combat state across two scenes.
        self.assertIn("mob_ai_control.open_register", self.runtime_source)
        self.assertIn("respawned, respawn_outcome = ",
                      mob_respawn.MOB_RESPAWN_WIRING)
        self.assertIn("self.mob_death_register = respawned",
                      mob_respawn.MOB_RESPAWN_WIRING)
        self.assertNotIn(
            "self.mob_death_register, _respawn",
            mob_respawn.MOB_RESPAWN_WIRING)

    def test_the_order_does_not_ask_for_a_world_argument(self):
        # The default already reaches the process book every production kill
        # is buried in; naming one at the call site is how the two books
        # start disagreeing again (pf-adversary D2).
        self.assertNotIn("world=mob_death_persistence.world_deaths()",
                         mob_respawn.MOB_RESPAWN_WIRING)

    def test_the_module_ships_without_a_flag(self):
        self.assertTrue(mob_respawn.production_allowed)


if __name__ == "__main__":
    unittest.main()
