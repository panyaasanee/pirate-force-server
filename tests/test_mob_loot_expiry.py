"""LANE-B round 0n9inw: the ledger ceiling the COO ruled, pinned.

COO-DECISION 2026-08-29T12:41+07:00 answered what replaces the ledger ceiling
when ``runtime.py`` stops taking every key of the kill it just sent: a PER-DROP
EXPIRY, evaluated lazily at insert and dispatch, explicitly not a background
timer, "because it is deterministic, testable headless, and adds no thread".

Every test here is that determinism cashed in.  The clock is a list of numbers,
so nothing in this file sleeps, nothing races and nothing is timing-dependent:
the boundary tests below would be untestable against a real clock and are the
whole reason the ruling named the lazy shape.

WHAT THIS FILE DOES NOT PROVE, said here because a test file is where the claim
is easiest to overread: no client has expired anything.  This is the SERVER's
cell keeping itself bounded.  The client-observable half is a player clicking
an object after the deadline and being told the right thing, and that needs the
pickup opcode GT-146 was opened to capture.
"""

from pathlib import Path
import random
import sys
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import field_mobs, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_loot import (
    DROP_LIFETIME_SECONDS,
    EXPIRED_KEY_MEMORY,
    MAX_DROP_LIFETIME_SECONDS,
    REFUSE_CLOCK_IS_NOT_A_CLOCK,
    REFUSE_CLOCK_WENT_BACKWARDS,
    REFUSE_DROP_EXPIRED,
    REFUSE_DROP_NOT_IN_LEDGER,
    REFUSE_LIFETIME_OUT_OF_RANGE,
    DropLedgerCell,
    MobLootContractError,
    roll_drops,
)

KILLER = 0x750059


class _Clock:
    """A clock that only moves when a test says so."""

    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class LedgerExpiryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster = load_roster(scene=field_mobs.BG0002_SCENE)
        cls.mob = cls.roster[0]

    def setUp(self):
        self.clock = _Clock()
        self.record = DeathRecord(
            self.mob.actor_identity, KILLER, self.mob.max_hp)

    def _cell(self, lifetime=60.0, ledger=None):
        return DropLedgerCell(
            ledger, lifetime_seconds=lifetime, clock=self.clock)

    def _kill(self, cell, token, seed=3):
        """One kill that dropped something, or the test is not testing this."""
        drops = cell.loot_a_kill(
            self.mob, self.record, roll_drops(self.mob, random.Random(seed)),
            kill_token=token)
        self.assertTrue(
            drops, "this test needs a kill with rows; seed %r dropped none"
            % (seed,))
        return drops

    # -- the ruling, in one test -------------------------------------------
    def test_a_cell_nobody_touches_correctly_stops_bounding_itself(self):
        """The honest shape of "lazy", stated as a test rather than hidden.

        The ruling chose lazy evaluation over a background timer.  The cost of
        that choice, which no docstring should be allowed to blur: a cell that
        nobody touches does not shrink.  Rows sit past their deadline until
        somebody reads, kills or picks up -- and then they are gone in the same
        call, before the caller can see one.

        The memory is bounded by the KILL RATE, not by the clock, and that is
        acceptable for the reason the ruling gives: no thread.  It is written
        down here so nobody reads "expiry" as "a cell empties itself".
        """
        cell = self._cell(lifetime=10.0)
        self._kill(cell, token=1)
        self.clock.advance(10_000.0)
        # Nothing has touched the cell: the rows are still in the object.
        self.assertTrue(cell._ledger.drops)      # deliberately the raw value
        # The first touch of any kind collects them.
        self.assertEqual(cell.ledger.drops, ())

    def test_the_deadline_is_the_first_instant_the_row_is_gone(self):
        """The boundary, which is only pinnable because the clock is injected."""
        cell = self._cell(lifetime=60.0)
        drops = self._kill(cell, token=1)
        key = drops[0].drop_key
        self.clock.advance(59.999)
        self.assertIn(
            key, [row.drop_key for row in cell.ledger.drops],
            "a row must live for the whole lifetime it was given")
        self.clock.advance(0.001)
        self.assertEqual(
            cell.ledger.drops, (),
            "at the deadline exactly, the row is gone: >= not >")

    def test_expiry_is_evaluated_at_insert(self):
        """Insert is one of the two points the ruling names."""
        cell = self._cell(lifetime=60.0)
        first = self._kill(cell, token=1, seed=3)
        self.clock.advance(61.0)
        second = self._kill(cell, token=2, seed=4)
        live = [row.drop_key for row in cell._ledger.drops]
        for row in first:
            self.assertNotIn(
                row.drop_key, live, "the kill itself should have swept it")
        for row in second:
            self.assertIn(row.drop_key, live)

    def test_a_new_kill_is_not_born_expired(self):
        """The reason the sweep and the placement share ONE clock reading.

        If the sweep took its own reading and the deadline took another, a
        cell built with a short lifetime could place rows against a "now" that
        was already behind, and the drop would be gone before the frame
        carrying it was composed.  One reading per call makes that unreachable
        rather than unlikely.
        """
        cell = self._cell(lifetime=0.001)
        drops = self._kill(cell, token=1)
        self.assertEqual(
            len(cell._ledger.drops), len(drops),
            "the rows a call places must survive that same call")

    def test_expiry_is_evaluated_at_dispatch_and_refuses_by_its_own_name(self):
        """The distinction round uq2lxw2 wrote down as owed.

        Before this round a pickup call site could not tell "your object timed
        out" from "somebody else took it": both arrived as the same refusal.
        Those are different sentences to put on a player's screen.
        """
        cell = self._cell(lifetime=30.0)
        drops = self._kill(cell, token=1)
        key = drops[0].drop_key
        self.clock.advance(30.0)
        with self.assertRaises(MobLootContractError) as caught:
            cell.take(key)
        self.assertEqual(caught.exception.args[0], REFUSE_DROP_EXPIRED)
        self.assertIn("not taken by anyone", str(caught.exception.args[1]))

    def test_a_row_taken_by_a_pickup_does_not_report_as_expired(self):
        """The other half of the same distinction, and the one that can lie.

        A row that a player successfully picked up must never come back as
        ``drop_expired`` -- that would tell the second player the object timed
        out when in truth the first player has it.
        """
        cell = self._cell(lifetime=600.0)
        drops = self._kill(cell, token=1)
        key = drops[0].drop_key
        cell.take(key)
        with self.assertRaises(MobLootContractError) as caught:
            cell.take(key)
        self.assertEqual(caught.exception.args[0], REFUSE_DROP_NOT_IN_LEDGER)

    def test_a_pruned_row_does_not_later_report_as_expired(self):
        """A deadline outliving its row is not harmless.

        ``prune_previous_kills`` removes rows the cell still holds deadlines
        for.  If those deadlines survived, the next sweep would "expire" a key
        that a PRUNE removed, and a pickup call site would be told the row
        timed out.  The prune's own reason -- RE-130's narrow generation --
        would be reported to the player as the clock's.
        """
        cell = self._cell(lifetime=60.0)
        first = self._kill(cell, token=1, seed=3)
        self._kill(cell, token=2, seed=4)
        removed = cell.prune_previous_kills()
        self.assertTrue(removed)
        self.clock.advance(120.0)
        cell.ledger                               # force a sweep
        for row in first:
            with self.assertRaises(MobLootContractError) as caught:
                cell.take(row.drop_key)
            self.assertEqual(
                caught.exception.args[0], REFUSE_DROP_NOT_IN_LEDGER,
                "a pruned row must not be reported as expired")

    def test_a_deadline_never_outlives_the_row_it_belongs_to(self):
        """THE INVARIANT, and the reason this test exists is a real defect.

        Round 0n9inw's own adversarial pass mutated the deadline cleanup out of
        BOTH ``take`` and ``prune_issued_before``, and every test in the first
        draft of this file still passed -- so the mutant in
        ``prune_issued_before`` was committed and pushed before anyone noticed.
        The two per-method tests below pin the CONSEQUENCE a caller can see (a
        pruned row is not later called expired), and that consequence survives
        the mutation, because ``_sweep_locked`` only remembers a key as expired
        when it actually removed a row.

        What does not survive is the invariant itself: the cell's deadline map
        must hold exactly the keys that are on the ground.  Every way a row can
        leave -- pickup, prune, expiry -- is checked here in one place, so the
        cleanup cannot be deleted from any of them silently.
        """
        cell = self._cell(lifetime=60.0)

        def deadlines_match_the_ground(where):
            live = {row.drop_key for row in cell._ledger.drops}
            held = set(cell._deadlines)
            self.assertEqual(
                held, live,
                "after %s the cell holds deadlines %r for rows on the ground "
                "%r" % (where, sorted(held), sorted(live)))

        first = self._kill(cell, token=1, seed=3)
        deadlines_match_the_ground("a kill")
        # The prune must have something of the FIRST kill left to remove, so
        # this row is deliberately NOT picked up.  The first draft of this test
        # took it here, which left the prune with nothing to do -- and a prune
        # that removes no row never reaches the cleanup being pinned, so the
        # mutant walked through this test too.
        second = self._kill(cell, token=2, seed=4)
        deadlines_match_the_ground("a second kill")
        removed = cell.prune_previous_kills()
        self.assertTrue(
            removed, "this test is only meaningful if the prune removed a row")
        self.assertIn(first[0].drop_key, [row.drop_key for row in removed])
        deadlines_match_the_ground("a prune")
        cell.take(second[0].drop_key)
        deadlines_match_the_ground("a pickup")
        self.clock.advance(120.0)
        cell.sweep_expired()
        deadlines_match_the_ground("an expiry")
        self.assertEqual(cell._deadlines, {}, "everything left the ground")

    def test_the_expired_memory_is_bounded(self):
        """The structure that explains a refusal must not become the leak.

        Past ``EXPIRED_KEY_MEMORY`` the answer falls back to
        ``drop_not_in_ledger`` -- still true, just less useful -- which is the
        trade this bound buys.  A test that only checked the useful case would
        pass while the memory grew forever.
        """
        cell = self._cell(lifetime=1.0)
        oldest = None
        for token in range(1, EXPIRED_KEY_MEMORY + 12):
            drops = cell.loot_a_kill(
                self.mob, self.record,
                roll_drops(self.mob, random.Random(token)), kill_token=token)
            if drops and oldest is None:
                oldest = drops[0].drop_key
            self.clock.advance(2.0)
        cell.ledger
        self.assertLessEqual(len(cell._expired), EXPIRED_KEY_MEMORY)
        self.assertIsNotNone(oldest)
        with self.assertRaises(MobLootContractError) as caught:
            cell.take(oldest)
        self.assertEqual(
            caught.exception.args[0], REFUSE_DROP_NOT_IN_LEDGER,
            "beyond the bound the honest answer is the less useful one")

    def test_the_memory_is_deep_enough_to_be_worth_having(self):
        """A bound of one would satisfy "bounded" and be useless.

        The adversarial pass set EXPIRED_KEY_MEMORY to 1 and every test still
        passed, because they all measured the memory against ITSELF.  The
        memory exists so a player whose object timed out a few kills ago is
        told that, rather than "no such object" -- so what has to be pinned is
        that several recent expiries are still nameable, not merely that the
        deque has a maxlen.
        """
        self.assertGreaterEqual(EXPIRED_KEY_MEMORY, 16)
        cell = self._cell(lifetime=1.0)
        keys = []
        for token in range(1, 9):
            drops = cell.loot_a_kill(
                self.mob, self.record,
                roll_drops(self.mob, random.Random(token)), kill_token=token)
            keys.extend(row.drop_key for row in drops)
            self.clock.advance(2.0)
        cell.ledger
        self.assertGreaterEqual(
            len(keys), 4, "this test needs several kills that dropped rows")
        for key in keys:
            with self.assertRaises(MobLootContractError) as caught:
                cell.take(key)
            self.assertEqual(
                caught.exception.args[0], REFUSE_DROP_EXPIRED,
                "a click on key 0x%X, expired a few kills ago, must still be "
                "told it expired" % key)

    def test_rows_handed_in_at_construction_get_a_deadline(self):
        """A row that entered before the cell existed must not live forever."""
        seed_cell = self._cell(lifetime=600.0)
        self._kill(seed_cell, token=1)
        carried = seed_cell.ledger
        self.assertTrue(carried.drops)
        cell = self._cell(lifetime=60.0, ledger=carried)
        self.clock.advance(61.0)
        self.assertEqual(cell.ledger.drops, ())

    def test_sweep_expired_returns_the_rows_so_a_caller_can_log_them(self):
        cell = self._cell(lifetime=30.0)
        drops = self._kill(cell, token=1)
        self.clock.advance(31.0)
        removed = cell.sweep_expired()
        self.assertEqual(
            sorted(row.drop_key for row in removed),
            sorted(row.drop_key for row in drops))
        self.assertEqual(cell.sweep_expired(), (), "a second sweep is a no-op")

    def test_expires_at_names_a_live_row_and_refuses_a_dead_one(self):
        cell = self._cell(lifetime=45.0)
        drops = self._kill(cell, token=1)
        key = drops[0].drop_key
        self.assertEqual(cell.expires_at(key), self.clock.now + 45.0)
        self.clock.advance(45.0)
        with self.assertRaises(MobLootContractError) as caught:
            cell.expires_at(key)
        self.assertEqual(caught.exception.args[0], REFUSE_DROP_NOT_IN_LEDGER)

    # -- the clock ---------------------------------------------------------
    def test_a_backwards_clock_is_refused_by_name(self):
        """Reachable, and reached here, which is why the name is not a lie.

        A clock that goes back freezes every deadline in the future: nothing
        expires again, the ledger grows without bound, and NOTHING IS RAISED.
        That is the silent version of the exact defect this mechanism exists
        to close, so it is loud instead.
        """
        cell = self._cell(lifetime=60.0)
        self._kill(cell, token=1)
        self.clock.advance(-1.0)
        with self.assertRaises(MobLootContractError) as caught:
            cell.ledger
        self.assertEqual(caught.exception.args[0], REFUSE_CLOCK_WENT_BACKWARDS)

    def test_the_default_clock_is_monotonic_not_wall_time(self):
        """Which is why the refusal above is unreachable in production.

        ``time.time`` steps backwards over an NTP correction; this lane would
        then refuse a real player's pickup for a reason that is the operating
        system's, not the game's.
        """
        import time

        cell = DropLedgerCell()
        self.assertIs(cell._clock, time.monotonic)

    def test_a_clock_that_is_not_a_clock_is_refused_when_the_cell_is_built(self):
        for bad in (object(), "now", 5):
            with self.assertRaises(MobLootContractError) as caught:
                DropLedgerCell(clock=bad)
            self.assertEqual(
                caught.exception.args[0], REFUSE_CLOCK_IS_NOT_A_CLOCK)
        with self.assertRaises(MobLootContractError) as caught:
            DropLedgerCell(clock=lambda: "soon")
        self.assertEqual(caught.exception.args[0], REFUSE_CLOCK_IS_NOT_A_CLOCK)

    # -- the number --------------------------------------------------------
    def test_the_lifetime_bounds_are_refusals_not_clamps(self):
        for bad in (0, -1.0, float("inf"), float("nan"), "60", None, True):
            with self.assertRaises(MobLootContractError) as caught:
                DropLedgerCell(lifetime_seconds=bad)
            self.assertEqual(
                caught.exception.args[0], REFUSE_LIFETIME_OUT_OF_RANGE,
                "lifetime %r must be refused, not silently repaired" % (bad,))
        with self.assertRaises(MobLootContractError):
            DropLedgerCell(lifetime_seconds=MAX_DROP_LIFETIME_SECONDS + 1.0)

    def test_the_default_lifetime_is_not_the_labels_lifetime(self):
        """The mistake this constant is one keystroke away from.

        The label a client draws lives 0.2-0.4 s (GT-045).  The ROW is what
        makes a click succeed, and RE-130 is why a player clicks where nothing
        is drawn.  A default taken from the label would delete every drop
        before a player could walk to it -- and it would look like a loot bug,
        not like a number somebody chose.

        THE BOUNDS BELOW ARE ABSOLUTE, and the first draft's were not: it
        asserted only ``> max(label) * 100``, which its own adversarial pass
        walked straight through with 41.0 s.  A relation to a number that
        small is not a floor -- it just looks like one.  These say what the
        figure has to be for the reason it exists: long enough that a player
        who has to WALK to the object still finds it (30 s is already tight),
        short enough that a cell is genuinely bounded (10 min).

        WHAT THIS TEST DELIBERATELY DOES NOT DO is pin 120.0 itself.  The
        figure is labelled [ASSUMPTION OF LANE B - AWAITING COO] and the letter
        asking for it promises the rollback is one line with no call-site
        change; a test that pinned the exact number would make that false.  So
        a mutation to any other defensible figure -- 41.0, say -- passes here
        ON PURPOSE.  That is the difference between pinning a decision and
        pinning a reason, and only the reason is this lane's to keep.
        """
        self.assertGreaterEqual(DROP_LIFETIME_SECONDS, 30.0)
        self.assertLessEqual(DROP_LIFETIME_SECONDS, 600.0)
        self.assertGreater(
            DROP_LIFETIME_SECONDS,
            max(mob_loot.GROUND_LABEL_OBSERVED_LIFETIME_SECONDS) * 100)
        self.assertLess(DROP_LIFETIME_SECONDS, MAX_DROP_LIFETIME_SECONDS)

    def test_the_lifetime_tripwire_is_a_real_ceiling_not_a_formality(self):
        """An absolute bound, because a relative one pins nothing.

        The adversarial pass set this tripwire to 1e12 and every test still
        passed, since they all compared the lifetime against the tripwire
        rather than against reality.  A tripwire of 1e12 s admits a lifetime of
        thirty thousand years, which is the same as having no ceiling at all --
        precisely the defect the expiry was ruled in to close.
        """
        self.assertGreater(
            MAX_DROP_LIFETIME_SECONDS, DROP_LIFETIME_SECONDS,
            "the tripwire must admit the default")
        self.assertLessEqual(
            MAX_DROP_LIFETIME_SECONDS, 24 * 3600.0,
            "a lifetime measured in days is not a ceiling")

    def test_the_assumption_tag_is_on_the_number_and_not_on_the_mechanism(self):
        """The mechanism is ruled; only the figure is this lane's guess.

        Round uq2lxw2 shipped an [ASSUMPTION OF LANE B] on the whole approach.
        The ruling landed, so that tag would now be false -- and a stale
        "awaiting COO" is worse than none: it invites the next round to
        re-litigate something already decided.
        """
        source = (
            ROOT / "src/pirateforce_foundation/mob_loot.py"
        ).read_text(encoding="utf-8")
        head, _, tail = source.partition("DROP_LIFETIME_SECONDS = ")
        self.assertIn("[ASSUMPTION OF LANE B - AWAITING COO]", head[-2000:])
        self.assertIn("only this figure is", head[-2000:])
        wiring = mob_loot.MOB_LOOT_WIRING
        self.assertIn("COO-DECISION 2026-08-29T12:41+07:00", wiring)
        # The house rule is STRIKE, NEVER DELETE, so the answered question is
        # still in the text -- and a test that simply forbade the words would
        # be asking this lane to break that rule.  What must be true is
        # narrower: every occurrence is inside a strike-through.  That is the
        # difference between a note that records what it used to say and a
        # note that still ASKS a question the COO has answered.
        stale = "[ASSUMPTION OF LANE B - AWAITING COO] chief asked the COO"
        found = 0
        start = 0
        while True:
            at = wiring.find(stale, start)
            if at < 0:
                break
            found += 1
            self.assertEqual(
                wiring[at - 3:at], "~~'",
                "occurrence %d of the answered question is live text, not a "
                "strike-through" % found)
            self.assertIn("IS STRUCK", wiring[at:at + 500])
            start = at + 1
        self.assertEqual(found, 1, "expected exactly one struck occurrence")

    # -- the lock ----------------------------------------------------------
    def test_the_sweep_happens_under_the_same_lock_as_everything_else(self):
        """Two threads killing and reading must not tear the ledger.

        The cell's whole reason to exist is that a ledger is a value nobody
        owns.  An expiry that swept outside the lock would reintroduce exactly
        the race the cell was built to remove.
        """
        cell = self._cell(lifetime=5.0)
        errors = []

        def kill(token):
            try:
                for step in range(20):
                    cell.loot_a_kill(
                        self.mob, self.record,
                        roll_drops(self.mob, random.Random(step)),
                        kill_token=token * 100 + step)
                    self.clock.advance(0.6)
            except MobLootContractError as exc:      # a named refusal is fine
                if exc.args[0] not in ("mob_already_looted", "ledger_stale"):
                    errors.append(exc)
            except Exception as exc:                 # anything else is not
                errors.append(exc)

        def read():
            try:
                for _ in range(200):
                    cell.ledger
                    cell.sweep_expired()
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=kill, args=(n,)) for n in (1, 2)]
        threads.append(threading.Thread(target=read))
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        # and the value is still internally consistent
        ledger = cell.ledger
        keys = [row.drop_key for row in ledger.drops]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(keys, sorted(keys))


if __name__ == "__main__":                           # pragma: no cover
    unittest.main()
