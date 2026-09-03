"""A login that revives a dead row while ANOTHER login is doing the same.

WHAT THIS FILE ADDS, STATED NARROWLY BECAUSE AN ADVERSARY PASS CUT THE FIRST
DRAFT'S CLAIM IN HALF.  `tests/test_persistence_login_vitals.py` already grades
every branch of `persistence_login_vitals._revive_on_login` against store
STUBS, and `tests/test_persistence_vitals_heal.py` already grades the write
lock itself (`_begin_immediate_under_contention` and the four `HEAL_LOCK_*`
knobs `COO-DECISION 20260902_1646` protects).  Neither of those is this file's
job and this file does not pretend to do either.

What is here and nowhere else:

* A login whose FIRST READ of the row is already stale -- it read a dead row,
  and by the time its write reaches the store another login has repaired the
  same row.  The sibling's second-login test reads an ALREADY-repaired row, so
  it never walks the revive path with a stale start.
* `store.apply_hp_damage` -- the real damage door, on a real database, on real
  `migrations/` -- landing INSIDE the window between the revive's write and
  its read-back.  The sibling measures that window with a stub.
* Four real threads, whose contract is stated in `RealThreadsTests`.

!! THE THREE DETERMINISTIC CLASSES DO NOT MEASURE THE WRITE LOCK, AND MUST NOT
BE READ AS DOING SO.  Measured, not assumed: with `_begin_immediate_under_
contention` replaced by a deferred `BEGIN`, and again with the transaction
removed altogether, all five of their tests stay GREEN while
`tests/test_persistence_vitals_heal.py` goes red on six.  The proxies below
impose an ORDER by hand; they do not create a race, and a test that pins a
message may not depend on a scheduler.  What they measure is the RESOLVER's
behaviour when the order a race can produce has already happened.

`RealThreadsTests` DOES sometimes catch those two, and "sometimes" is the
whole of the claim: with the write barrier below forcing four real writers to
arrive together, the deferred-`BEGIN` mutant was caught 9 times in 10 and the
no-transaction mutant 3 times in 10 (this round, on this box; a Windows runner
will not reproduce those ratios).  A test that catches a defect 3 times in 10
IS NOT A GUARD FOR IT, and this file does not stand in for
`tests/test_persistence_vitals_heal.py`, which kills both every time.  It is
written down because a later round measuring the same thing should not read
the paragraph above and conclude the threaded class is blind.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
* NOTHING CLIENT-OBSERVABLE.  No player logs in twice at once here; this is
  the wire/DB layer and no byte reaches a screen.
* It does not claim two real logins can overlap on this server today -- that
  is a question about `runtime.py`'s session handling and this lane does not
  own it.  The claim is narrower: IF two calls overlap, the row stays
  consistent and neither login is failed.
* It does not drive the seam (`session.py`).  It calls
  `resolve_for_character` directly, as
  `tests/test_persistence_login_vitals.py::AgainstARealDatabaseTests` does.
* THE ROW THESE TESTS START FROM IS NOT ONE PRODUCTION CAN PRODUCE TODAY.  The
  fixture kills the character through the store's damage door, and that door
  has no caller in `src/` at all (measured this round; the round file carries
  the grep).  So "a dead row logs in" is a state only a test or a future
  combat path can reach, and this file says so rather than calling its fixture
  production-shaped.

THE ROUND'S CITATION, LABELLED.  The adversary pass that declared the
concurrent revive unmeasured is recorded in `pf_bridge/rounds/DB_20260903_
0703_mgyoob_*.md` -- IN THE OTHER REPOSITORY, AND UNOPENABLE FROM THIS ONE.
It is named that way because `persistence_login_vitals.py` (lines 6-10) makes
labelling an unopenable citation this lane's house rule.  What was already
measured in THIS repository, and what an earlier draft of this docstring
wrongly claimed nobody had measured, is the stub-level case:
`tests/test_persistence_login_vitals.py::test_a_write_that_healed_nothing_
does_not_claim_it_healed`.

THE FALLBACK LITERALS HERE ARE THIS FILE'S OWN, AND ON PURPOSE.  The sibling
derives them from `player_wire`'s composer so it can state a nonclaim about a
fresh install.  This file states no such nonclaim: it needs three numbers that
are UNMISTAKABLY not the row's, and importing a derivation from a composer
whose shape is currently moving would buy that file's fragility for nothing.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_login_vitals as login_vitals  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import (  # noqa: E402
    HEAL_LOCK_TOTAL_WAIT_S,
    SQLiteStore,
)
from test_persistence_typed_attr_columns import (  # noqa: E402
    NoHandleOutlivesItsTempDirMixin,
)

MIGRATIONS = ROOT / "migrations"

#: Three numbers no row in this file ever holds.  A resolution carrying them
#: is a resolution that fell back, and one carrying the row's is not.
FALLBACK_LEVEL = 61
FALLBACK_HP_CURRENT = 101
FALLBACK_HP_MAX = 103
FALLBACKS = dict(
    fallback_level=FALLBACK_LEVEL,
    fallback_hp_current=FALLBACK_HP_CURRENT,
    fallback_hp_max=FALLBACK_HP_MAX,
)
LITERALS = (FALLBACK_LEVEL, FALLBACK_HP_CURRENT, FALLBACK_HP_MAX)


def _build_wire(selector):
    return b"wire-%d" % selector, b"avatar", 0x30000001 + selector, 0


class _Proxy:
    """Everything the real store does, with one method wrapped.

    A WRAPPER, NOT A STUB, AND THE DIFFERENCE IS THE POINT: every proxy below
    delegates to the real `SQLiteStore`, so the write under test is the
    production write on a real database and the read-back reads what SQLite
    actually holds.  The sibling file grades the same branches against stubs;
    substituting a stub here would measure this file's own arithmetic.
    """

    def __init__(self, store):
        self._store = store

    def __getattr__(self, name):
        return getattr(self._store, name)


class _WhileTheWriteIsInFlight(_Proxy):
    """Run `during()` between this login's READ and its WRITE.

    !! THIS IS AN ORDER, NOT A RACE, AND THE MODULE DOCSTRING SAYS WHY THE
    DIFFERENCE MATTERS.  What it reproduces is the state a losing login is
    left holding: a resolution built from a row that said DEAD, arriving at a
    store where the row is already repaired.  `during()` runs before this
    login's own connection is opened, so nothing here can lose a lock -- and
    nothing here can see whether the lock exists.
    """

    def __init__(self, store, during):
        super().__init__(store)
        self._during = during
        self.calls = 0

    def restore_hp_to_full(self, character_id):
        self.calls += 1
        self._during()
        return self._store.restore_hp_to_full(character_id)


class _AllOfThemWriteAtOnce(_Proxy):
    """Hold every thread's revive write until all of them have READ.

    !! WITHOUT THIS THE THREADED TEST IS MOSTLY VACUOUS, AND THAT WAS
    MEASURED, NOT FEARED.  With the threads free-running, the winner often
    commits before the other three have even read the row, so those three
    resolve `FROM_ROW` on a live row and never enter the revive at all: a
    mutant that makes every losing revive report `REVIVE_WRITE_FAILED` was
    caught 8 times in 9 rather than 9 in 9.  A test whose coverage depends on
    the scheduler is a test that reports a green it did not earn.

    The barrier is in this harness and not in the store: every thread's read
    happens before any thread's write, so all four hold a resolution built
    from a DEAD row, and then all four arrive at `restore_hp_to_full`
    together.  One heals; the rest are real losers of the real write lock.

    A broken barrier does not hang the suite -- it is recorded and the write
    goes through anyway, so the test fails on its own report rather than on a
    join deadline.
    """

    def __init__(self, store, parties):
        super().__init__(store)
        self.gate = threading.Barrier(parties)
        self.broken: list = []
        self._lock = threading.Lock()

    def restore_hp_to_full(self, character_id):
        try:
            self.gate.wait(timeout=30)
        except threading.BrokenBarrierError as exc:
            with self._lock:
                self.broken.append(repr(exc))
        return self._store.restore_hp_to_full(character_id)


class _ThatMovesTheRowBeforeTheReadBack(_Proxy):
    """Let the real damage door move the row between the write and read-back.

    `_revive_on_login` reads the row back through
    `store.read_character_vitals`, so the SECOND call to that method is the
    read-back.  Damage applied there lands inside the window the module's own
    comment names ("something else moved the row between the write and the
    read-back").  The sibling measures this window with a stub resolution;
    here the mover is `store.apply_hp_damage` against real `migrations/`.
    """

    def __init__(self, store, amount):
        super().__init__(store)
        self._amount = amount
        self.reads = 0

    def read_character_vitals(self, character_id):
        self.reads += 1
        if self.reads == 2:
            self._store.apply_hp_damage(character_id, self._amount)
        return self._store.read_character_vitals(character_id)


class _OnARealDatabase(NoHandleOutlivesItsTempDirMixin, unittest.TestCase):
    """The fixture the whole file shares: real `migrations/`, real store."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.guard_the_temp_dir(self.tmp)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("revive-contention")
        self.home = Position(1, 0, 1.0, 2.0, 3.0, heading=0.0)

    def _dead_character(self, tag="rc1"):
        """A character the store's own damage door beat to zero.

        NOT A ROW PRODUCTION CAN REACH TODAY, and the docstring at the top of
        this file says so: nothing in `src/` calls that door.  The reason to
        build the row THROUGH it rather than with an `UPDATE` of this file's
        own is narrower and still worth it -- every rule in
        `persistence_vitals` runs on the way in, so the fixture cannot invent
        a row the lane's own gate would refuse.
        """
        character = self.store.create_character(
            self.account_id, "Revive" + tag, tag, "fingerprint-" + tag,
            _build_wire, self.home)
        self.store.apply_hp_damage(character.id, 10_000)
        self._character_id = character.id
        self.assertEqual(
            self._row()[vitals.HP_CURRENT_COLUMN], 0,
            "this fixture needs a row that really says the character is dead",
        )
        return character.id

    def _row(self, character_id=None):
        """The three columns AS THE DATABASE HOLDS THEM, through the store's
        own gap-carrying door -- never this file's copy of them."""
        if character_id is None:
            character_id = getattr(self, "_character_id", None)
        return dict(self.store.read_character_vitals(character_id).present)

    def _row_triple(self, character_id=None):
        row = self._row(character_id)
        return (
            row[vitals.LEVEL_COLUMN],
            row[vitals.HP_CURRENT_COLUMN],
            row[vitals.HP_MAX_COLUMN],
        )

    @staticmethod
    def _triple(resolved):
        return (resolved.level, resolved.hp_current, resolved.hp_max)


class _WriteProbe:
    """Did ANOTHER connection commit a change to this file, yes or no.

    `PRAGMA data_version` on a connection that holds the file open is bumped
    by SQLite itself whenever a different connection commits, and is untouched
    by a transaction that wrote nothing.  It replaces the `updated_at`
    comparison a first draft used here, and the reason is measured rather than
    stylistic: `store._now()` is `datetime.now(...)`, whose resolution on the
    Windows runner this suite is gated on is the ~15.6 ms system tick, while
    this whole file runs in under a second.  An adversary pass emulated that
    clock and the `updated_at` form caught a "the loser writes anyway" mutant
    2 times in 10, against 10 in 10 for this one.  A guard that is 80% blind
    on the platform it runs on is a comment.
    """

    def __init__(self, path):
        self._db = sqlite3.connect(path)

    def version(self) -> int:
        return self._db.execute("PRAGMA data_version").fetchone()[0]

    def close(self) -> None:
        self._db.close()


class TheSecondLoginOfADeadCharacterTests(_OnARealDatabase):
    """A login holding a stale dead-row read, arriving at a repaired row."""

    def test_both_logins_send_the_row_and_neither_sends_the_literals(self):
        character_id = self._dead_character("rc2")
        other: list = []

        def the_other_login():
            other.append(login_vitals.resolve_for_character(
                self.store, character_id, **FALLBACKS))

        proxy = _WhileTheWriteIsInFlight(self.store, the_other_login)
        mine = login_vitals.resolve_for_character(
            proxy, character_id, **FALLBACKS)

        self.assertEqual(proxy.calls, 1, "the fixture did not interleave")
        self.assertEqual(len(other), 1)
        winner, = other
        self.assertEqual(
            winner.reason, login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            mine.reason, login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
            "the login that arrived second reported something other than a "
            "revive, so a player logging in twice at once is told the repair "
            "failed on a row that is repaired: " + mine.detail)
        # `_row_triple` is an independent read through the store's own door,
        # so this is the row grading the answer and not the answer grading
        # itself.  `LITERALS` is not asserted against separately: no row in
        # this file holds level 61, so equality with the row already excludes
        # it, and a second assertion that cannot fire is a comment.
        self.assertEqual(self._triple(mine), self._row_triple())
        self.assertEqual(self._triple(winner), self._row_triple())

    def test_the_second_login_writes_nothing_and_says_so_in_its_own_line(self):
        """The property `_what_the_write_reported`'s docstring predicts.

        Its write finds the row already at its maximum, so it writes NOTHING
        and reports `was_already_full=True`.  Both halves are asserted -- the
        fragment that reaches `resolved.detail` (which is what
        `console_line()` puts in front of an operator) and SQLite's own answer
        to "did another connection commit anything", read through
        `_WriteProbe` at the two statements that bracket the write.
        """
        character_id = self._dead_character("rc3")
        probe = _WriteProbe(self.path)
        self.addCleanup(probe.close)
        seen: list = []

        def the_other_login():
            login_vitals.resolve_for_character(
                self.store, character_id, **FALLBACKS)
            seen.append(probe.version())

        proxy = _WhileTheWriteIsInFlight(self.store, the_other_login)
        mine = login_vitals.resolve_for_character(
            proxy, character_id, **FALLBACKS)

        self.assertIn("was_already_full=True", mine.detail)
        self.assertEqual(
            probe.version(), seen[0],
            "the second login committed something after the first had "
            "already repaired the row")

    def test_a_third_login_after_both_is_an_ordinary_from_row_login(self):
        """The state the pair leaves behind is not a special state.

        Two revives over one row must not leave something only a revive can
        read: the next login is `FROM_ROW`, and it writes nothing.
        """
        character_id = self._dead_character("rc4")

        def the_other_login():
            login_vitals.resolve_for_character(
                self.store, character_id, **FALLBACKS)

        login_vitals.resolve_for_character(
            _WhileTheWriteIsInFlight(self.store, the_other_login),
            character_id, **FALLBACKS)

        probe = _WriteProbe(self.path)
        self.addCleanup(probe.close)
        before = probe.version()
        third = login_vitals.resolve_for_character(
            self.store, character_id, **FALLBACKS)
        self.assertEqual(third.reason, login_vitals.FROM_ROW)
        self.assertEqual(self._triple(third), self._row_triple())
        self.assertEqual(probe.version(), before)


class SomethingElseMovesTheRowMidReviveTests(_OnARealDatabase):
    """The window between the write and the read-back, with a real mover."""

    def test_a_row_damaged_before_the_read_back_is_reported_as_moved(self):
        character_id = self._dead_character("rc7")
        proxy = _ThatMovesTheRowBeforeTheReadBack(self.store, 63)

        resolved = login_vitals.resolve_for_character(
            proxy, character_id, **FALLBACKS)

        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN)
        self.assertEqual(
            self._triple(resolved), self._row_triple(),
            "the login sent a number nobody read back")
        self.assertLess(resolved.hp_current, resolved.hp_max)
        self.assertIn("moved the row", resolved.detail)

    def test_a_row_damaged_back_to_zero_before_the_read_back_is_a_failure(self):
        """The same window, taken to the end: re-killed before the read-back.

        A login reporting a revive here would be reporting a repair the
        database does not hold.
        """
        character_id = self._dead_character("rc8")

        resolved = login_vitals.resolve_for_character(
            _ThatMovesTheRowBeforeTheReadBack(self.store, 10_000),
            character_id, **FALLBACKS)

        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(self._triple(resolved), LITERALS)


class RealThreadsTests(_OnARealDatabase):
    """Actual concurrency, against a contract stated here in full.

    THE CONTRACT, BECAUSE AN ADVERSARY PASS ASKED FOR IT IN WORDS AND THE
    FIRST DRAFT DID NOT HAVE ONE.  Overlapping logins of one dead character
    must leave ONE consistent row, and:

    * NO login may report `REVIVE_WRITE_FAILED`.  The row IS repaired by the
      time any of them reads it back, and that token means "read back, and
      still dead".  A losing login answering it is the defect this class
      exists to catch -- measured: a mutant that turns every
      `was_already_full` write into `REVIVE_WRITE_FAILED` + the literals is
      exactly "three of four players are told the repair failed on a repaired
      row", and the first draft of this class accepted it.
    * A login may answer with the caller's literals ONLY under
      `REVIVE_NOT_CONFIRMED` or `ROW_COULD_NOT_BE_READ`.  Those two are the
      honest contention outcomes and they are reachable here: `connect()` sets
      `busy_timeout=5000`, so a read-back that loses five seconds of lock
      really cannot confirm the row, and the module's whole design is that a
      login is never FAILED for it.  Every other reason must carry the row's
      three numbers.

    WHAT IS DELIBERATELY NOT PINNED: which login wins.  That is the operating
    system's business, and a test asserting an ordering here would be a test
    that fails on a loaded Windows runner.
    """

    THREADS = 4

    #: Longer than `store.HEAL_LOCK_TOTAL_WAIT_S`, on purpose.  A
    #: thread still inside the heal lock's own documented budget is a CORRECT
    #: store, and failing it on a shorter clock is the "losing on TIME, not on
    #: logic" defect `COO-DECISION 20260902_1646` was written to end.
    #: IMPORTED from `store.py` rather than typed, so raising that budget
    #: cannot leave this number behind.  A first draft reached for it as an
    #: attribute of `SQLiteStore`, where it is not, and `getattr`'s default
    #: would have hidden the miss for good.
    JOIN_TIMEOUT_S = HEAL_LOCK_TOTAL_WAIT_S + 60.0

    def test_four_overlapping_logins_leave_one_consistent_row(self):
        character_id = self._dead_character("rc9")
        start = threading.Barrier(self.THREADS)
        # Every thread reads before any thread writes -- see
        # `_AllOfThemWriteAtOnce` for the measurement that made this
        # necessary.  The store underneath is the real one.
        store = _AllOfThemWriteAtOnce(self.store, self.THREADS)
        answers: list = []
        barrier_failures: list = []
        failures: list = []
        lock = threading.Lock()

        def one_login():
            # The barrier wait is OUTSIDE the try below and reports through
            # its own list: a `BrokenBarrierError` is a thread-start problem,
            # and the first draft filed it under "a login raised", which would
            # have sent a reader to `persistence_login_vitals.py` for a defect
            # that is in this file's own harness.
            try:
                start.wait(timeout=30)
            except threading.BrokenBarrierError as exc:
                with lock:
                    barrier_failures.append(repr(exc))
                return
            try:
                resolved = login_vitals.resolve_for_character(
                    store, character_id, **FALLBACKS)
            except Exception as exc:      # noqa: BLE001 -- reported below
                # `Exception`, not `BaseException`: `apply_to_character` in
                # the module under test writes down why this lane does not
                # swallow a `KeyboardInterrupt`, and a test harness that does
                # would contradict it.
                with lock:
                    failures.append(repr(exc))
            else:
                with lock:
                    answers.append(resolved)

        threads = [threading.Thread(target=one_login, name="login-%d" % n)
                   for n in range(self.THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=self.JOIN_TIMEOUT_S)
            self.assertFalse(
                thread.is_alive(),
                "a login thread outlived the store's own lock budget")

        self.assertEqual(barrier_failures, [], "the threads never lined up")
        self.assertEqual(store.broken, [], "the write barrier broke")
        self.assertEqual(
            failures, [],
            "a login raised, and this module exists so that a login cannot")
        self.assertEqual(len(answers), self.THREADS)

        row = self._row()
        self.assertGreater(
            row[vitals.HP_CURRENT_COLUMN], 0,
            "overlapping revives left the character dead on disk")
        self.assertEqual(
            row[vitals.HP_CURRENT_COLUMN], row[vitals.HP_MAX_COLUMN],
            "overlapping revives left the row at something that is not its "
            "own maximum")

        # THE TEST GRADES ITS OWN COVERAGE FIRST.  At least one login must
        # have reached the revive holding a stale dead-row read and found the
        # repair already done, or the assertions below are being made about a
        # path nothing walked this run.
        # Either fragment proves a loser really walked the revive: it found
        # the row already at its maximum, or its own write lost the lock and
        # raised.  Both are the losing side; only "no loser at all" is a run
        # that measured nothing.
        self.assertTrue(
            any("was_already_full=True" in resolved.detail
                or "the write raised" in resolved.detail
                for resolved in answers),
            "no login lost the write race, so this run measured nothing: "
            + repr([resolved.detail for resolved in answers]))

        row_triple = self._row_triple()
        may_fall_back = (
            login_vitals.REVIVE_NOT_CONFIRMED,
            login_vitals.ROW_COULD_NOT_BE_READ,
        )
        for resolved in answers:
            self.assertNotEqual(
                resolved.reason, login_vitals.REVIVE_WRITE_FAILED,
                "a login was told the revive did not take, on a row that is "
                "repaired: " + resolved.detail)
            if resolved.reason in may_fall_back:
                self.assertEqual(
                    self._triple(resolved), LITERALS,
                    "a login that could not confirm the row sent something "
                    "other than the caller's literals: " + resolved.detail)
            else:
                self.assertEqual(
                    self._triple(resolved), row_triple,
                    "a login answered with a triple that is neither the "
                    "row's nor a declared fallback -- the mixed block "
                    "`PANYA-DECISION 20260901_1059` bans: " + resolved.detail)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
