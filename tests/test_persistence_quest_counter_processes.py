"""LANE-DB: `increment_quest_counter` under REAL concurrent processes.

WHY THIS FILE EXISTS.  pf-adversary's `D1` against round `6vv9mi` measured
that the door's central promise -- "two kills landing at the same moment
must not both read 3 and both write 4" -- had NO test at all: moving the
`SELECT` out of the immediate transaction left all 47 tests of
`tests/test_persistence_quest_state.py` green.  The same debt has been
declared and deferred by this lane for three rounds (`kh0ukv`, `fw2hs6`,
`6vv9mi`), and `tests/test_store_spend_typed_attribute.py` carries the same
hole with a written-down reason: a `subprocess` control was built there and
PULLED before push because it was FLAKY, and a flaky control teaches the
next round to re-run instead of to read.

SO THE CONTENTION HERE IS ARRANGED, NOT HOPED FOR.  Children rendezvous
through files in a directory the parent owns: nobody proceeds until every
child has arrived.  The lost-update control goes further and rendezvouses
BETWEEN the read and the write, which makes its loss a certainty rather
than a probability -- every child reads the same number and every child
writes that number plus one, so a table that should hold 3 holds 1 on every
machine, every time, at any speed.

WHAT THE PAIR PROVES TOGETHER.  The honest door and the read-outside-the-
transaction shape are driven through the SAME harness, the same database
and the same rendezvous.  The mutant losing increments is what gives the
honest test its teeth: without it, "the total was right" could equally mean
the children never overlapped.

TWO LAYERS, KEPT APART.  Children write through the door; the parent reads
the result with a `sqlite3` connection of its own.  No claim is made about
a player: nothing calls this door in `runtime.py` yet (that is not this
lane's zone), so no quest counter on the owner's machine has ever survived
two processes.  This is the wire/DB layer only.
"""
from __future__ import annotations

import subprocess
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position     # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: Seconds the parent waits for a child.  Generous on purpose: this number
#: exists to turn a hang into a legible failure, never to decide a race.
CHILD_TIMEOUT = 120.0

CHILD_SOURCE = '''
"""Child of tests/test_persistence_quest_counter_processes.py."""
import sqlite3
import sys
import time
from pathlib import Path

SRC, DB, MIGRATIONS, MODE, TAG, PEERS, ITERATIONS, GATE = sys.argv[1:9]
sys.path.insert(0, SRC)
PEERS = int(PEERS)
ITERATIONS = int(ITERATIONS)
GATE = Path(GATE)
CHARACTER_ID = int(sys.argv[9])
QUEST_ID = int(sys.argv[10])
NAME = sys.argv[11]


def arrive(step):
    """Block until every child has reached `step`."""
    (GATE / (step + "." + TAG)).write_text("here", encoding="ascii")
    deadline = time.time() + 90.0
    while time.time() < deadline:
        if len(list(GATE.glob(step + ".*"))) >= PEERS:
            return
        time.sleep(0.01)
    raise AssertionError("peers never arrived at " + step)


def honest():
    from pirateforce_foundation.store import SQLiteStore
    store = SQLiteStore(Path(DB), Path(MIGRATIONS))
    arrive("start")
    for _ in range(ITERATIONS):
        store.increment_quest_counter(CHARACTER_ID, QUEST_ID, NAME, 1)


def read_outside_the_transaction():
    """The mutant `D1` named: the SELECT moved out of the transaction."""
    db = sqlite3.connect(DB, timeout=30.0)
    try:
        arrive("start")
        row = db.execute(
            "SELECT counter_value FROM character_quest_counter "
            "WHERE character_id=? AND quest_id=? AND counter_name=?",
            (CHARACTER_ID, QUEST_ID, NAME),
        ).fetchone()
        current = 0 if row is None else row[0]
        arrive("read")
        db.execute("BEGIN IMMEDIATE")
        db.execute(
            "INSERT INTO character_quest_counter"
            "(character_id,quest_id,counter_name,counter_value,updated_at)"
            " VALUES (?,?,?,?,?) "
            "ON CONFLICT(character_id,quest_id,counter_name) DO UPDATE SET "
            "counter_value=excluded.counter_value",
            (CHARACTER_ID, QUEST_ID, NAME, current + 1, "2026-09-08T00:00:00"),
        )
        db.commit()
    finally:
        db.close()


try:
    if MODE == "honest":
        honest()
    else:
        read_outside_the_transaction()
except BaseException as error:            # reported, never swallowed
    (GATE / ("done." + TAG)).write_text(
        "FAILED %s: %s" % (type(error).__name__, error), encoding="ascii",
    )
    raise
(GATE / ("done." + TAG)).write_text("OK", encoding="ascii")
'''


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _ProcessHarness(unittest.TestCase):
    """One database, N children, one rendezvous directory."""

    PEERS = 3
    QUEST_ID = 4207
    NAME = "mob:900"

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name)
        self.path = self.workspace / "quest_counter_races.sqlite3"
        self.gate = self.workspace / "gate"
        self.gate.mkdir()
        self.child = self.workspace / "quest_counter_child.py"
        self.child.write_text(CHILD_SOURCE, encoding="ascii")
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account = store.ensure_account("quest-counter-race-tests")
        self.character_id = store.create_character(
            account, "QRace", "qrace", "fingerprint-qrace", _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        ).id

    def _run(self, mode, iterations):
        """Start every child, then wait for all of them."""
        children = []
        for index in range(self.PEERS):
            children.append((str(index), subprocess.Popen(
                [
                    sys.executable, str(self.child), str(ROOT / "src"),
                    str(self.path), str(MIGRATIONS), mode, str(index),
                    str(self.PEERS), str(iterations), str(self.gate),
                    str(self.character_id), str(self.QUEST_ID), self.NAME,
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )))
        report = []
        for tag, child in children:
            try:
                _, stderr = child.communicate(timeout=CHILD_TIMEOUT)
            except subprocess.TimeoutExpired:
                child.kill()
                _, stderr = child.communicate()
                report.append("child %s timed out" % tag)
                continue
            done = self.gate / ("done." + tag)
            said = done.read_text(encoding="ascii") if done.exists() else "-"
            if child.returncode != 0 or said != "OK":
                report.append("child %s rc=%s said=%r stderr=%s" % (
                    tag, child.returncode, said,
                    stderr.decode("utf-8", "replace")[-800:],
                ))
        self.assertEqual(report, [], "\n".join(report))

    def _stored(self):
        """The number as a connection of the parent's own reads it."""
        db = sqlite3.connect(str(self.path))
        try:
            row = db.execute(
                "SELECT counter_value FROM character_quest_counter "
                "WHERE character_id=? AND quest_id=? AND counter_name=?",
                (self.character_id, self.QUEST_ID, self.NAME),
            ).fetchone()
        finally:
            db.close()
        return None if row is None else row[0]


class IncrementUnderRealProcessesTests(_ProcessHarness):
    """The door's own promise, measured across process boundaries."""

    ITERATIONS = 20

    def test_three_processes_lose_no_increment(self):
        """`3 x 20` increments must leave exactly 60 in the row.

        `2212` and the door's docstring both promise the read and the write
        sit inside ONE immediate transaction so a second caller queues
        behind the first.  Threads cannot measure that promise -- a
        `threading.Lock` would pass the same test -- which is exactly how
        `tests/test_store_spend_typed_attribute.py` lost four spends to
        four processes while every thread test there stayed green.
        """
        self._run("honest", self.ITERATIONS)
        self.assertEqual(self._stored(), self.PEERS * self.ITERATIONS)

    def test_the_row_is_created_by_the_first_writer_not_by_the_test(self):
        """The starting fact is `0 + delta` written by whichever child got
        the lock first -- no fixture pre-creates the row, so the race
        includes the INSERT half, not only the UPDATE half."""
        self.assertIsNone(self._stored())
        self._run("honest", 1)
        self.assertEqual(self._stored(), self.PEERS)


class TheHarnessCatchesTheMutantD1NamedTests(_ProcessHarness):
    """The teeth of the test above: the same children, the same database,
    the same rendezvous -- and a read that sits outside the transaction."""

    def test_a_read_outside_the_transaction_loses_two_of_three_increments(
        self,
    ):
        """Every child reads 0, every child writes 1: the row holds 1 where
        three increments were asked for.

        This is not a timing observation.  The children rendezvous BETWEEN
        the read and the write, so the interleaving that loses the updates
        is forced on every machine at every speed.  `D1`'s claim was that
        the honest test above would stay green under this shape; the number
        below is the measurement that says it would not.
        """
        self._run("mutant", 1)
        self.assertEqual(self._stored(), 1)

    def test_the_honest_door_survives_the_interleaving_that_breaks_it(self):
        """Same three processes, same rendezvous -- through the real door.

        Run on a fresh database of its own (each test gets its own
        `setUp`), it is the A/B half of the test above: 3 where the mutant
        leaves 1, from one harness driving one row two ways.

        NONCLAIM, measured rather than assumed: with ONE increment per
        child this test is not the deterministic half.  Mutating the real
        door (SELECT moved above `_quest_begin`) was run before this file
        was pushed -- it left this test at `2 != 3` and turned
        `test_three_processes_lose_no_increment` red in the same run (that
        one's own number was not read off the run, so none is quoted), but
        the single-increment shape can also come out right by luck.  The
        deterministic pins are the mutant child above (always exactly 1)
        and the 20-increment test, where 60 tiny transactions across three
        processes do not all miss each other.
        """
        self._run("honest", 1)
        self.assertEqual(self._stored(), self.PEERS)


if __name__ == "__main__":       # pragma: no cover - parity with the file's
    unittest.main()              # neighbours in tests/
