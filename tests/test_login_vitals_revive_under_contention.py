"""Two logins of the same DEAD character, overlapping, on a real database.

WHY THIS FILE EXISTS.  `persistence_login_vitals._revive_on_login` is the one
write this lane's login path makes, and its whole design is "the ROW decides,
not the write door" -- the write is attempted, the row is read back, and the
answer comes from the read-back.  Every branch of that shape is a CONCURRENCY
branch: the loser of a `BEGIN IMMEDIATE` race finds nothing to write, or finds
its write raised after another connection already committed the same repair.

`_what_the_write_reported`'s own docstring says so in words -- "a concurrent
login of the same character wins the `BEGIN IMMEDIATE` race, and the loser's
write is a no-op reporting `was_already_full`" -- and until this file NOTHING
MEASURED IT.  The `pf-adversary` pass of round `mgyoob` declared it unmeasured
in as many words ("what the reviewer did not measure, and I do not claim: two
concurrent logins writing the revive of the same dead character"), and the
round file carried that sentence forward as an open item.  A sentence in a
docstring that no test can kill is a prediction, not a measurement.

WHAT IS PINNED HERE, AND WHAT IS DELIBERATELY NOT
-------------------------------------------------
Three of the four classes below are DETERMINISTIC and use no threads at all:
they build the interleaving by hand, through a store proxy that runs the other
login (or the other writer) at the exact statement where a real race would
land.  A test that pins a message and an outcome may not depend on the
scheduler, and this repository has no sleep-and-hope tests.

The fourth class DOES start real threads, and it therefore asserts only what
cannot flake: no exception escapes any login, the row ends ALIVE at its own
maximum, and no login invents a third answer -- every returned triple is
either the row's numbers or the caller's literals, never a mixture and never
`hp_current=0`.  The "all three or none" rule (`PANYA-DECISION 20260901_1059`,
never send a block whose fields were guessed) is exactly the property a race
could break silently, so it is the one the threaded test states.

WHAT THIS FILE DOES NOT CLAIM
-----------------------------
* NOTHING CLIENT-OBSERVABLE.  No player logs in twice at once here; this is
  the wire/DB layer and no byte reaches a screen.
* It does not claim two REAL logins can overlap on this server today -- that
  is a question about `runtime.py`'s session handling and this lane does not
  own it.  What it claims is narrower and is the part that is ours: IF two
  calls overlap, the row stays consistent and neither login is failed.
* It does not test the seam (`session.py`).  This file drives
  `resolve_for_character` directly, the way `tests/test_persistence_login_
  vitals.py::AgainstARealDatabaseTests` does.

THE FALLBACK LITERALS HERE ARE THIS FILE'S OWN, AND ON PURPOSE.  The sibling
file derives them from `player_wire`'s composer so it can state a nonclaim
about a fresh install.  This file states no such nonclaim: it needs three
numbers that are UNMISTAKABLY not the row's, so that "sent the literals" and
"sent the row" can never be confused for one another, and deriving them from a
composer whose shape is currently moving would import that file's fragility
for no benefit.
"""
from __future__ import annotations

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
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
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
    """Everything the real store does, with one method replaced.

    Written as a proxy rather than a stub because the point of every test
    below is that the OTHER writer is real: it opens its own connection, takes
    its own `BEGIN IMMEDIATE`, and commits.  A stub store cannot lose a race
    it does not run.
    """

    def __init__(self, store):
        self._store = store

    def __getattr__(self, name):
        return getattr(self._store, name)


class _WhileTheWriteIsInFlight(_Proxy):
    """Run `during()` at the moment the revive's write is about to happen.

    This is the interleaving a real race produces, made deterministic: the
    other login's whole `resolve_for_character` -- read, revive, read back,
    commit -- happens BEFORE this one's write reaches SQLite, which is exactly
    what "the other connection won `BEGIN IMMEDIATE`" leaves behind.
    """

    def __init__(self, store, during):
        super().__init__(store)
        self._during = during
        self.calls = 0

    def restore_hp_to_full(self, character_id):
        self.calls += 1
        self._during()
        return self._store.restore_hp_to_full(character_id)


class _WhoseWriteRaisesAfterItLanded(_Proxy):
    """The write commits and THEN the door raises.

    A losing connection can raise `sqlite3.OperationalError` after another one
    has already committed the identical repair, and the property under test is
    that this login reports what the ROW says rather than what the door did.
    The exception is raised after delegating, so the row really is repaired
    when the read-back happens.
    """

    def __init__(self, store, exc):
        super().__init__(store)
        self._exc = exc

    def restore_hp_to_full(self, character_id):
        self._store.restore_hp_to_full(character_id)
        raise self._exc


class _ThatMovesTheRowBeforeTheReadBack(_Proxy):
    """Let something else damage the row between the write and the read-back.

    `_revive_on_login` reads the row back through
    `store.read_character_vitals`, so the second call to that method IS the
    read-back.  Damage applied there is damage applied inside the window the
    module's own comment names ("something else moved the row between the
    write and the read-back").
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
        """A character the store itself beat to zero -- not a hand-written row.

        `apply_hp_damage` is the only mover of `hp_current` this repository
        has, so a row it produced is a row production could produce.
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


class TheSecondLoginOfADeadCharacterTests(_OnARealDatabase):
    """The race itself, deterministic: the other login finishes first."""

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
            "the login that LOST the race reported something other than a "
            "revive, so a player logging in twice at once is told the repair "
            "failed on a row that is repaired: " + mine.detail)
        self.assertEqual(self._triple(mine), self._row_triple())
        self.assertEqual(self._triple(winner), self._row_triple())
        self.assertNotEqual(self._triple(mine), LITERALS)

    def test_the_loser_writes_nothing_and_says_so_in_its_own_line(self):
        """The property `_what_the_write_reported` predicts in words.

        The loser's `restore_hp_to_full` finds the row already at its maximum,
        so it writes NOTHING and reports `was_already_full=True`.  Both halves
        are asserted: the console fragment (which is what an operator reads)
        and the row's `updated_at` (which is what the database records), so a
        change that keeps the wording and starts writing is still caught.
        """
        character_id = self._dead_character("rc3")
        stamps: list = []

        def the_other_login():
            login_vitals.resolve_for_character(
                self.store, character_id, **FALLBACKS)
            stamps.append(self._updated_at(character_id))

        proxy = _WhileTheWriteIsInFlight(self.store, the_other_login)
        mine = login_vitals.resolve_for_character(
            proxy, character_id, **FALLBACKS)

        self.assertIn("was_already_full=True", mine.detail)
        self.assertEqual(
            self._updated_at(character_id), stamps[0],
            "the losing login moved the row after the winner had repaired it")

    def _updated_at(self, character_id):
        with self.store.connect() as db:
            return db.execute(
                "SELECT updated_at FROM characters WHERE id=?",
                (character_id,),
            ).fetchone()["updated_at"]

    def test_a_third_login_after_both_is_an_ordinary_from_row_login(self):
        """The state the race leaves behind is not a special state.

        Two overlapping revives must not leave a row that only a revive can
        read: the next login is `FROM_ROW`, with no write at all.
        """
        character_id = self._dead_character("rc4")

        def the_other_login():
            login_vitals.resolve_for_character(
                self.store, character_id, **FALLBACKS)

        login_vitals.resolve_for_character(
            _WhileTheWriteIsInFlight(self.store, the_other_login),
            character_id, **FALLBACKS)

        before = self._updated_at(character_id)
        third = login_vitals.resolve_for_character(
            self.store, character_id, **FALLBACKS)
        self.assertEqual(third.reason, login_vitals.FROM_ROW)
        self.assertEqual(self._triple(third), self._row_triple())
        self.assertEqual(self._updated_at(character_id), before)


class TheWriteDoorDoesNotGetTheLastWordTests(_OnARealDatabase):
    """`REVIVE_WRITE_FAILED` is decided by the row, and here the door lies."""

    def test_a_write_that_raises_after_it_landed_is_still_a_revive(self):
        import sqlite3

        character_id = self._dead_character("rc5")
        proxy = _WhoseWriteRaisesAfterItLanded(
            self.store, sqlite3.OperationalError("database is locked"))

        resolved = login_vitals.resolve_for_character(
            proxy, character_id, **FALLBACKS)

        self.assertEqual(
            resolved.reason,
            login_vitals.ROW_HP_NOT_POSITIVE_REVIVED_ON_LOGIN,
            "the door's exception outranked the row, which is the exact "
            "defect the second adversary pass of round `zt40am` removed: "
            + resolved.detail)
        self.assertIn("the write raised", resolved.detail)
        self.assertEqual(self._triple(resolved), self._row_triple())
        self.assertNotEqual(self._triple(resolved), LITERALS)

    def test_a_write_that_raises_and_did_not_land_reports_the_failure(self):
        """The other direction, so the test above cannot pass by being blind.

        Here the door raises WITHOUT delegating, so the row is still dead when
        it is read back -- and the login must say the revive did not take and
        send the literals.
        """
        import sqlite3

        character_id = self._dead_character("rc6")

        class _RaisesWithoutWriting(_Proxy):
            def restore_hp_to_full(self, character_id):
                raise sqlite3.OperationalError("database is locked")

        resolved = login_vitals.resolve_for_character(
            _RaisesWithoutWriting(self.store), character_id, **FALLBACKS)

        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(self._triple(resolved), LITERALS)
        self.assertEqual(
            self._row()[vitals.HP_CURRENT_COLUMN], 0,
            "nothing should have repaired the row on this branch")


class SomethingElseMovesTheRowMidReviveTests(_OnARealDatabase):
    """The window between the write and the read-back, on a real database."""

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
        self.assertIn("something ", resolved.detail)
        self.assertIn("moved the row", resolved.detail)

    def test_a_row_damaged_back_to_zero_before_the_read_back_is_a_failure(self):
        """The same window, taken to the end: re-killed before the read-back.

        A login that reported a revive here would be reporting a repair that
        the database does not hold.
        """
        character_id = self._dead_character("rc8")

        resolved = login_vitals.resolve_for_character(
            _ThatMovesTheRowBeforeTheReadBack(self.store, 10_000),
            character_id, **FALLBACKS)

        self.assertEqual(resolved.reason, login_vitals.REVIVE_WRITE_FAILED)
        self.assertEqual(self._triple(resolved), LITERALS)


class RealThreadsTests(_OnARealDatabase):
    """Actual concurrency, asserting only what a scheduler cannot change.

    !! THIS CLASS DELIBERATELY PINS NO MESSAGE AND NO REASON.  Which login
    wins is the operating system's business, and a test that asserts an
    ordering here would be a test that fails on a busy Windows runner.  What
    it asserts instead is the invariant a race could break: the row is alive
    at its own maximum afterwards, no login raised, and no login answered with
    a triple that is neither the row's nor the literals.
    """

    THREADS = 4

    def test_four_overlapping_logins_leave_one_consistent_row(self):
        character_id = self._dead_character("rc9")
        start = threading.Barrier(self.THREADS)
        answers: list = []
        failures: list = []
        lock = threading.Lock()

        def one_login():
            try:
                start.wait(timeout=30)
                resolved = login_vitals.resolve_for_character(
                    self.store, character_id, **FALLBACKS)
            except BaseException as exc:      # noqa: BLE001 -- reported below
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
            thread.join(timeout=60)
            self.assertFalse(thread.is_alive(), "a login thread did not finish")

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

        row_triple = self._row_triple()
        for resolved in answers:
            self.assertIn(
                self._triple(resolved), (row_triple, LITERALS),
                "a login answered with a triple that is neither the row's nor "
                "the caller's literals -- the mixed block "
                "`PANYA-DECISION 20260901_1059` bans: " + resolved.detail)
            self.assertNotEqual(
                resolved.hp_current, 0,
                "a login sent hp_current=0 on the wire: " + resolved.detail)


if __name__ == "__main__":       # pragma: no cover
    unittest.main()
