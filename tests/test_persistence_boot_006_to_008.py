"""LANE-DB / M4: the upgrade the OWNER's machine actually performs -- one
boot that applies ``006`` -> ``007`` -> ``008`` to a database that already
holds real characters -- and the first direct tests of this lane's own test
gate, ``tests/pf_birth_state.py``.

WHY THIS FILE EXISTS.  ``COO-DECISION 20260902_1144`` point 2 approves two
things this lane measured as missing from ``main``:

* **(b) a single-boot ``006`` -> ``008`` test on rows that hold data.**  The
  owner's canonical database was built before ``006`` existed and has
  characters in it; the next server boot hands ``migrate()`` a directory with
  THREE unapplied files and applies all three inside one call, against rows
  that are not fixtures.  ``COO-DECISION 20260901_1112`` makes that path the
  whole point of this lane -- the canonical database becomes the standard one
  *through these migration files*.

  STATED AS NARROWLY AS IT WAS MEASURED, because the first draft of this
  paragraph said "nothing in this repository ran that path" and a
  ``pf-adversary`` pass refuted it by instrumenting ``migrate()``:
  ``tests/test_persistence_typed_attr_columns.py::BootSnapshotProtects006Tests``
  does run a three-file boot over a pre-006 row (and the full suite even
  records a seven-file one).  What no test asserted is **what those
  pre-existing rows HOLD once the three files have run** -- their subject is
  the snapshot, and they never read the rows back.  That, and not the boot
  itself, is the gap this file closes.  Every other test of these migrations
  stages the world so that exactly one file is pending
  (``001..005`` then ``006``; ``001..006`` then ``007``; ``001..007`` then
  ``008``), which is the right shape for "what does THIS file do" and cannot
  answer "what do the three together leave behind".

* **(c) direct tests of the test gate itself.**  ``tests/pf_birth_state.py``
  is what stops this lane's other five test files from taking "a newly
  created character holds nothing" as a fact about the world, and its
  ``measure_birth_typed_state`` REFUSES any third state -- a fourth column, a
  level of zero, a ``speed_walk`` seeded at birth.  Round ``cby3pd`` built
  that refusal after a ``pf-adversary`` pass drove four wrong insertion points
  green through a weaker shape.  Measured on ``main`` before this file:
  five test files import the gate and every one of them calls it as a
  HELPER; not one asserts that it refuses anything.  A gate whose refusal is
  never exercised is a gate that can be deleted by accident and leave 7000
  green tests behind it -- and chief's ``COO-DECISION 20260902_0444`` plug is
  the change it exists to catch.

WHAT THIS FILE DOES NOT DO.  It adds no migration, edits no migration, and
touches no ``.db`` file anywhere; every database here is built inside a
``TemporaryDirectory``.  It changes no behaviour at all -- nothing here is
client-observable, no frame is composed and nothing is sent.  It does not
claim to have run against the owner's canonical database; it claims to run
the same SEQUENCE of files against a database in the same schema state.
"""
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402
from test_persistence_typed_attr_columns import (  # noqa: E402
    _insert_character_at_005,
)

MIGRATIONS = ROOT / "migrations"

#: The last version the owner's database can have been built at before this
#: lane existed: `005` is the newest file that is not one of this lane's.
LAST_PRE_LANE_VERSION = 5

def _lane_migration_versions() -> tuple[int, ...]:
    """Every migration this lane has added on top of the pre-lane world.

    DERIVED from the directory rather than typed out as ``(6, 7, 8)``.  A
    `pf-adversary` pass measured what typing it costs: adding `009` -- a file
    this lane is chartered to add -- turned three tests here red for a reason
    that has nothing to do with what they measure.  The same correction is
    already written down three lines above the equivalent assertion in
    `tests/test_persistence_typed_attr_columns.py`: "the list is derived
    rather than typed so that the next one does not turn this pin red for the
    wrong reason".
    """
    return tuple(sorted(
        int(path.name[:3])
        for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        if int(path.name[:3]) > LAST_PRE_LANE_VERSION
    ))


#: The versions one boot must apply together on the owner's machine.
UPGRADE_VERSIONS = _lane_migration_versions()


def _typed_columns_seeded_by_lane_migrations() -> set[str]:
    """Typed columns any lane migration ASSIGNS a value to.

    `006` only adds columns (no assignment), so it contributes nothing; `007`
    assigns the three vitals and `008` assigns `speed_walk`.  Derived so that
    a future migration seeding a FIFTH column fails `_expected` with an
    instruction rather than failing three tests with a puzzle.
    """
    seeded = set()
    for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"):
        if int(path.name[:3]) <= LAST_PRE_LANE_VERSION:
            continue
        body = "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("--"))
        for column in typed.TYPED_COLUMNS:
            if re.search(r"\b%s\s*=" % re.escape(column), body):
                seeded.add(column)
    return seeded


def _speed_walk_seeded_by_008() -> float:
    """The value `008` really writes, read out of the migration file.

    Not written out here as a literal: this file must fail if `008` and this
    expectation ever disagree, and a second copy of the number cannot do that.
    """
    sql = (MIGRATIONS / "008_character_speed_walk_seed.sql").read_text(
        encoding="utf-8")
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--"))
    found = re.findall(r"speed_walk\s*=\s*([0-9]+\.[0-9]+)", body)
    if len(found) != 1:
        raise AssertionError(
            "expected exactly one `speed_walk = <float>` assignment in 008, "
            "found %r -- this helper, not 008, is what needs rereading"
            % (found,))
    return float(found[0])


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _PreLaneWorkspace(unittest.TestCase):
    """A database at `005` with real characters in it -- the owner's state.

    THE ROWS ARE BUILT WITH RAW SQL, THROUGH THE HELPER THIS LANE ALREADY
    NAMED ONCE, AND THE FIRST DRAFT OF THIS CLASS GOT IT WRONG.  It used
    `SQLiteStore.create_character`, and a `pf-adversary` pass measured the
    cost by simulating the very change this file says it exists to protect:
    with `COO-DECISION 20260902_0444`'s plug in `create_character`, **17 of
    31 tests here died** on `sqlite3.OperationalError: table characters has
    no column named level` -- inside chief's pull request, in this lane's
    fixture, not in his line.  The same 33-mine clearing round `cby3pd`
    already wrote the answer down in
    `tests/test_persistence_typed_attr_columns.py::_insert_character_at_005`:
    "a test whose whole subject is a PRE-006 database cannot use a creator
    that requires 006 ... this is that same insert, named once."  So this
    imports that one, rather than becoming a second copy of it or re-laying
    the mine that round was spent clearing.

    That helper writes `characters` AND `character_positions` AND the
    backpack rows -- which matters here, because
    `TheBootChangesNothingElseTests` compares those tables across the boot
    and would otherwise be comparing `[] == []`.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_005"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= LAST_PRE_LANE_VERSION:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state.sqlite3"

    def _make_pre_lane_rows(self, names=("Veteran", "Second", "Third")):
        """Characters that exist before `006` does, each with its own data."""
        store = SQLiteStore(self.path, self.older)
        store.migrate()
        self.assertNotIn(
            "level", self._character_columns(),
            "the pre-006 fixture already has typed columns; the migrations "
            "copied into it are not the pre-lane set this file needs")
        self.logins = []
        self.selectors = []
        ids = []
        for offset, name in enumerate(names):
            login = "boot-006-to-008-%s" % name.lower()
            home = Position(3 + offset, offset, 11.0 + offset, 22.0, 33.0,
                            heading=1.5)
            ids.append(_insert_character_at_005(
                self.path, login, name, selector=offset,
                position=home, store=store))
            self.logins.append(login)
            self.selectors.append(offset)
        return ids

    def _character_columns(self):
        db = sqlite3.connect(self.path)
        try:
            return [str(row[1])
                    for row in db.execute("PRAGMA table_info(characters)")]
        finally:
            db.close()

    def _rows(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute("SELECT * FROM characters ORDER BY id").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()

    def _dump_other_tables(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            names = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {
                name: [{k: r[k] for k in r.keys()}
                       for r in db.execute(
                           "SELECT * FROM %s ORDER BY rowid" % name)]
                for name in names
                if name not in ("characters", "schema_migrations")
            }
        finally:
            db.close()

    def _ledger(self):
        """`{version: applied_at}` -- the whole row, not only its key."""
        db = sqlite3.connect(self.path)
        try:
            return {int(r[0]): r[1] for r in db.execute(
                "SELECT version,applied_at FROM schema_migrations")}
        finally:
            db.close()

    def _applied_versions(self):
        db = sqlite3.connect(self.path)
        try:
            return sorted(int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations"))
        finally:
            db.close()

    def _boot(self):
        """The one call the owner's server makes on its next start."""
        SQLiteStore(self.path, MIGRATIONS).migrate()


class OneBootAppliesAllThreeTests(_PreLaneWorkspace):
    """The sequencing itself: three unapplied files, one `migrate()`."""

    def test_all_three_are_pending_before_the_boot_and_none_after(self):
        from pirateforce_foundation import persistence_backup

        self._make_pre_lane_rows()
        self.assertEqual(
            list(UPGRADE_VERSIONS),
            persistence_backup.pending_versions(self.path, MIGRATIONS),
            "the fixture is not in the state this file is about")
        self._boot()
        self.assertEqual(
            [], persistence_backup.pending_versions(self.path, MIGRATIONS))
        self.assertEqual(
            sorted(persistence_backup.migration_versions(MIGRATIONS)),
            self._applied_versions())

    def test_the_three_versions_are_recorded_with_a_real_applied_at(self):
        """`assertTrue(stamp)` is not a check -- the column is already
        `TEXT NOT NULL`, so a `pf-adversary` pass replaced the timestamp with
        `"-"` and the first draft stayed green.  This parses it.
        """
        import datetime

        self._make_pre_lane_rows()
        self._boot()
        stamped = self._ledger()
        for version in UPGRADE_VERSIONS:
            self.assertIn(version, stamped)
            text = str(stamped[version])
            datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))

    def test_a_second_boot_does_not_restamp_a_line_it_already_wrote(self):
        """The sibling below compares only the version NUMBERS, and a mutant
        that re-runs `UPDATE schema_migrations SET applied_at=?` on every
        boot left it green.  The ledger row for an applied file is history;
        rewriting it on every start makes the owner's audit trail say the
        migration ran today."""
        self._make_pre_lane_rows()
        self._boot()
        first = self._ledger()
        self._boot()
        self.assertEqual(first, self._ledger())

    def test_a_second_boot_moves_no_row_and_writes_no_ledger_line(self):
        self._make_pre_lane_rows()
        self._boot()
        after_first = self._rows()
        ledger_after_first = self._applied_versions()
        self._boot()
        self.assertEqual(after_first, self._rows())
        self.assertEqual(ledger_after_first, self._applied_versions())


class EveryPreLaneRowComesOutSeededTests(_PreLaneWorkspace):
    """What the owner's existing characters hold once the boot is over."""

    def _expected(self):
        """The four values one boot must leave behind.

        Derived through `pf_birth_state.seeded_birth()` rather than by
        calling `persistence_vitals.new_character_vitals()` here.  Both
        answer with the same numbers, but `NothingIsWiredTests.
        test_only_the_ordered_call_site_may_call_it` keeps the birth values
        to one call site plus a short allowlist, and this file joining that
        allowlist would make it the second SOURCE of birth values the rule
        exists to prevent.  `speed_walk` is not a birth value at all
        (`COO-DECISION 20260901_1447` point 2 forbids it at birth); it is
        read out of `008` itself.
        """
        expected = dict(birth_state.seeded_birth())
        expected["speed_walk"] = _speed_walk_seeded_by_008()
        return expected

    def test_every_character_holds_exactly_the_four_seeded_values(self):
        """Read by raw SQL on purpose.

        A `pf-adversary`-style mutant that answers `read_typed_attributes`
        from `persistence_vitals` instead of from the row leaves the shipped
        reader supplying the evidence for its own grade; it is caught here
        because this row comes out of `SELECT * FROM characters`.
        """
        ids = self._make_pre_lane_rows()
        self._boot()
        expected = self._expected()
        rows = {row["id"]: row for row in self._rows()}
        self.assertEqual(sorted(ids), sorted(rows))
        for character_id in ids:
            row = rows[character_id]
            for column, value in expected.items():
                self.assertEqual(value, row[column],
                                 "%s of character %d" % (column, character_id))

    def test_the_shipped_reader_agrees_with_the_row_it_reads(self):
        ids = self._make_pre_lane_rows()
        self._boot()
        store = SQLiteStore(self.path, MIGRATIONS)
        rows = {row["id"]: row for row in self._rows()}
        for character_id in ids:
            row = rows[character_id]
            self.assertEqual(
                {column: row[column] for column in typed.TYPED_COLUMNS
                 if row[column] is not None},
                dict(store.read_typed_attributes(character_id)),
                "character %d" % character_id)

    def test_no_typed_column_outside_those_four_is_written(self):
        ids = self._make_pre_lane_rows()
        self._boot()
        untouched = set(typed.TYPED_COLUMNS) - set(self._expected())
        self.assertTrue(untouched, "006 built no column beyond the seeded four")
        for row in self._rows():
            for column in untouched:
                self.assertIsNone(row[column],
                                  "%s of character %d" % (column, row["id"]))
        self.assertEqual(len(ids), len(self._rows()))

    def test_each_seeded_row_resolves_complete_with_no_gap(self):
        ids = self._make_pre_lane_rows()
        self._boot()
        store = SQLiteStore(self.path, MIGRATIONS)
        for character_id in ids:
            resolution = store.read_character_vitals(character_id)
            self.assertEqual((), tuple(resolution.gaps),
                             "character %d" % character_id)
            answer = store.read_character_vitals_or_none(character_id)
            self.assertIsNotNone(answer)
            seeded = birth_state.seeded_birth()
            self.assertEqual(
                (seeded["level"], seeded["hp_current"], seeded["hp_max"]),
                (answer.level, answer.hp_current, answer.hp_max))

    def test_a_row_that_already_held_a_level_keeps_it_through_the_boot(self):
        """`007` must decline a row that already holds a level even when it
        is not the only file the boot has left to apply.

        Stated as narrowly as it is built: a database cannot hold a level
        before `006` runs, because the column does not exist, so the only
        honest fixture stages `006`, writes the level, and lets the rest of
        the upgrade (`007` and `008`) run in one call.  It is a two-file
        boot, not the three-file one above, and the difference is why this
        docstring says so instead of borrowing that class's sentence."""
        ids = self._make_pre_lane_rows()
        # Reach the row the only way a pre-006 database allows: 006 first,
        # then a value, then the rest of the boot.  This is not a hand-edit
        # of a canonical file -- it is a temporary fixture standing in for a
        # database that already held a level when 007 arrived.
        self._apply_only(6)
        self._set(ids[0], level=9, hp_current=480, hp_max=500)
        self._boot()
        store = SQLiteStore(self.path, MIGRATIONS)
        veteran = store.read_typed_attributes(ids[0])
        self.assertEqual(9, veteran["level"])
        self.assertEqual(480, veteran["hp_current"])
        self.assertEqual(500, veteran["hp_max"])
        self.assertEqual(_speed_walk_seeded_by_008(), veteran["speed_walk"])
        self.assertEqual(self._expected(),
                         dict(store.read_typed_attributes(ids[1])),
                         "the row beside it stopped being seeded")

    def _apply_only(self, version):
        staged = self.root / ("migrations_upto_%03d" % version)
        staged.mkdir(exist_ok=True)
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) <= version:
                shutil.copy2(path, staged / path.name)
        SQLiteStore(self.path, staged).migrate()

    def _set(self, character_id, **columns):
        db = sqlite3.connect(self.path)
        try:
            for column, value in columns.items():
                db.execute("UPDATE characters SET %s=? WHERE id=?" % column,
                           (value, character_id))
            db.commit()
        finally:
            db.close()


class TheBootChangesNothingElseTests(_PreLaneWorkspace):
    """What the three files leave standing, compared before and after the one
    boot rather than reasoned about from their SQL.

    The soft-delete test at the end is the odd one out and is here on
    purpose: it is about a row the files ARE required to touch, and it sits
    beside the "nothing else moved" comparisons because it is the same
    before/after measurement over the same fixture."""

    def test_no_non_typed_column_of_any_character_moves(self):
        self._make_pre_lane_rows()
        before = {row["id"]: row for row in self._rows()}
        self._boot()
        after = {row["id"]: row for row in self._rows()}
        self.assertEqual(sorted(before), sorted(after))
        for character_id, old in before.items():
            new = after[character_id]
            for column, value in old.items():
                self.assertEqual(
                    value, new[column],
                    "%s of character %d changed across the boot"
                    % (column, character_id))

    def test_every_other_table_is_row_identical_across_the_boot(self):
        self._make_pre_lane_rows()
        before = self._dump_other_tables()
        self.assertIn("accounts", before,
                      "the fixture built no other table to compare")
        self._boot()
        after = self._dump_other_tables()
        self.assertEqual(
            before, {name: rows for name, rows in after.items()
                     if name in before},
            "a table that existed before the boot changed across it")

    def test_a_soft_deleted_character_is_seeded_like_any_other(self):
        """The owner's database has them, and a row the migrations skipped
        would resolve `None` forever if it were ever restored."""
        ids = self._make_pre_lane_rows()
        store = SQLiteStore(self.path, self.older)
        session = store.open_session(store.ensure_account(self.logins[0]))
        store.soft_delete_character(session, self.selectors[0])
        self._boot()
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute("SELECT * FROM characters WHERE id=?",
                             (ids[0],)).fetchone()
        finally:
            db.close()
        self.assertIsNotNone(row["deleted_at"],
                             "the fixture did not actually soft-delete it")
        expected = dict(birth_state.seeded_birth())
        expected["speed_walk"] = _speed_walk_seeded_by_008()
        for column, value in expected.items():
            self.assertEqual(value, row[column], column)


class TheOwnerKeepsACopyOfThePreUpgradeWorldTests(_PreLaneWorkspace):
    """`COO-DECISION 20260901_1112` point 3 over the REAL upgrade.

    `006`, `007` and `008` each have a snapshot test of their own, and each
    asks the question with one file pending.  The owner's boot has three
    pending at once, and the copy she can fall back to has to be of the
    database as it was BEFORE the first of them, not between two of them.
    """

    def test_one_snapshot_is_taken_and_it_predates_all_three_files(self):
        ids = self._make_pre_lane_rows()
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=self.root / "backups")
        self.assertIsNotNone(snapshot)
        restored = self.root / "restored.sqlite3"
        shutil.copy2(Path(snapshot), restored)
        db = sqlite3.connect(restored)
        db.row_factory = sqlite3.Row
        try:
            columns = [str(r[1])
                       for r in db.execute("PRAGMA table_info(characters)")]
            versions = sorted(int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations"))
            names = [r["name"] for r in db.execute(
                "SELECT name FROM characters ORDER BY id")]
        finally:
            db.close()
        for version in UPGRADE_VERSIONS:
            self.assertNotIn(version, versions)
        for column in typed.TYPED_COLUMNS:
            self.assertNotIn(column, columns,
                             "the copy was taken after 006 had already run")
        self.assertEqual(len(ids), len(names),
                         "the copy lost the characters it exists to protect")

    def test_a_snapshot_that_cannot_be_taken_stops_the_whole_upgrade(self):
        from unittest import mock

        from pirateforce_foundation import persistence_backup

        self._make_pre_lane_rows()
        with mock.patch.object(
                persistence_backup, "_sha256_file",
                side_effect=OSError("disk went away mid-snapshot")):
            with self.assertRaises(persistence_backup.BackupError):
                SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                    backups_root=self.root / "backups")
        self.assertEqual([], [v for v in self._applied_versions()
                              if v in UPGRADE_VERSIONS])
        self.assertNotIn("level", self._character_columns())


class WhatAHalfDoneUpgradeLeavesBehindTests(_PreLaneWorkspace):
    """The one property a THREE-file boot has that a one-file boot does not,
    and the answer to the question a `pf-adversary` pass ended on: is the
    owner's upgrade safe because the three files are narrow, or because the
    boot is atomic?

    MEASURED: it is not atomic.  `SQLiteStore.migrate` wraps each file in its
    OWN `BEGIN IMMEDIATE ... COMMIT`, so a failure in the third file leaves
    the first two committed and the rows already rewritten.  That is not a
    defect being reported here -- it is the behaviour, and this class pins it
    so that the safety claim rests where it really rests: on the snapshot
    `migrate_with_backup` takes BEFORE the first file, which is the only
    thing that can put a half-upgraded canonical database back.
    `test_a_snapshot_that_cannot_be_taken_stops_the_whole_upgrade` above
    covers a failure BEFORE any file runs; this covers one in the middle.
    """

    def _directory_whose_last_file_fails(self):
        """The real lane migrations, with the last one replaced by a file
        that raises -- a temporary directory, never `migrations/`."""
        staged = self.root / "migrations_with_a_bad_tail"
        staged.mkdir()
        last = max(UPGRADE_VERSIONS)
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) < last:
                shutil.copy2(path, staged / path.name)
        (staged / ("%03d_deliberately_broken.sql" % last)).write_text(
            "UPDATE characters SET no_such_column = 1;\n", encoding="utf-8")
        return staged, last

    def test_a_failure_in_the_last_file_leaves_the_earlier_ones_committed(self):
        ids = self._make_pre_lane_rows()
        staged, last = self._directory_whose_last_file_fails()
        with self.assertRaises(sqlite3.OperationalError):
            SQLiteStore(self.path, staged).migrate()
        applied = self._applied_versions()
        for version in UPGRADE_VERSIONS:
            if version < last:
                self.assertIn(version, applied)
        self.assertNotIn(last, applied)
        # and the rows are already rewritten by the files that did commit
        row = {r["id"]: r for r in self._rows()}[ids[0]]
        seeded = birth_state.seeded_birth()
        for column, value in seeded.items():
            self.assertEqual(value, row[column], column)

    def test_the_snapshot_taken_first_still_holds_the_whole_pre_upgrade_world(self):
        """Which is why the copy has to predate file ONE, not file three."""
        ids = self._make_pre_lane_rows()
        staged, _ = self._directory_whose_last_file_fails()
        backups = self.root / "backups"
        with self.assertRaises(sqlite3.OperationalError):
            SQLiteStore(self.path, staged).migrate_with_backup(
                backups_root=backups)
        copies = [path for path in backups.rglob("*")
                  if path.is_file() and path.name == self.path.name]
        self.assertEqual(1, len(copies), [str(c) for c in copies])
        restored = self.root / "restored_after_failure.sqlite3"
        shutil.copy2(copies[0], restored)
        db = sqlite3.connect(restored)
        db.row_factory = sqlite3.Row
        try:
            columns = [str(r[1])
                       for r in db.execute("PRAGMA table_info(characters)")]
            names = [r["name"] for r in db.execute(
                "SELECT name FROM characters ORDER BY id")]
        finally:
            db.close()
        for column in typed.TYPED_COLUMNS:
            self.assertNotIn(column, columns)
        self.assertEqual(len(ids), len(names))


class _FakeStore:
    """Answers `read_typed_attributes` from a dict, and nothing else.

    The gate takes a store only to call that one method; giving it a real
    `SQLiteStore` here would mean building a row in a state the schema's own
    CHECK constraints refuse, which is the wrong thing to measure.
    """

    def __init__(self, states):
        self._states = states

    def read_typed_attributes(self, character_id):
        return dict(self._states[character_id])


class TheBirthGateRefusesTests(unittest.TestCase):
    """`tests/pf_birth_state.py` measured as a subject, not used as a helper.

    Every assertion here is about the REFUSAL.  Five test files on `main`
    depend on it and none of them would go red if it were reduced to
    `return dict(store.read_typed_attributes(character_id))` (measured:
    254 passed with that mutation in place and this file absent).

    THE GATE HAS ONE RULE, NOT THREE.  `measure_birth_typed_state` is a
    single `if state in (unseeded, seeded)`; the three test names below --
    a fourth column, a level of zero, `hp_current` over `hp_max` -- are three
    STATES that one rule refuses, not three defences.  A `pf-adversary` pass
    read the names as implying three, and it is worth one sentence here
    rather than three misleading names, because the day someone adds a
    second rule these tests will not tell them which one they broke.
    """

    def _seeded(self):
        return birth_state.seeded_birth()

    def test_it_accepts_the_states_it_names_and_they_all_differ(self):
        """Every accepted state is accepted, and no two of them are the same.

        Written over the whole tuple rather than over two names: `009` added
        a third (`COO-DECISION 20260902_1607`) and a fourth would otherwise
        arrive unmeasured.  The pairwise inequality is what stops the tuple
        being padded with a duplicate to make this test pass.
        """
        states = birth_state.accepted_birth_states()
        self.assertEqual({}, states[0])
        self.assertGreaterEqual(len(states), 3)
        for index, state in enumerate(states):
            for other in states[index + 1:]:
                self.assertNotEqual(state, other)
            store = _FakeStore({1: state})
            self.assertEqual(state,
                             birth_state.measure_birth_typed_state(store, 1))

    def test_the_defaulted_state_is_derived_and_is_not_a_second_copy(self):
        """`defaulted_birth` must DERIVE its numbers, exactly as
        `seeded_birth` does, and for the same reason: `COO-DECISION
        20260902_1607` fixes them and forbids changing them, so a literal
        `400.0` or `100` written here would be a second place they live.

        Scanned on the parsed statements with the docstring stripped -- the
        shape a `pf-adversary` pass drove a literal through when this file
        scanned prose (see the sibling test above).
        """
        import ast

        source = (ROOT / "tests" / "pf_birth_state.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "defaulted_birth")
        body = list(function.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        statements = "\n".join(ast.dump(node) for node in body)
        self.assertIn("seeded_birth", statements,
                      "defaulted_birth() no longer builds on seeded_birth()")
        self.assertIn("CLIENT_CONSTRUCTION_DEFAULTS", statements,
                      "the walk speed is no longer taken from the module "
                      "that measured it")
        for number in ("400.0", "100", "1"):
            self.assertNotIn(
                "value=%s" % number, statements,
                "a number COO-DECISION 20260902_1607 fixed is written out "
                "here as well as in the module that owns it")
        # and the state it produces really is the seeded one plus the speed
        seeded = birth_state.seeded_birth()
        defaulted = birth_state.defaulted_birth()
        self.assertEqual({c: defaulted[c] for c in seeded}, seeded)
        self.assertEqual(sorted(set(defaulted) - set(seeded)), ["speed_walk"])

    def test_the_seeded_state_is_derived_and_is_not_a_second_copy(self):
        """`seeded_birth` must DERIVE the numbers, not restate them.

        Pinned at the SOURCE rather than by calling the ordered function
        here, for the reason `_PreLaneWorkspace._expected` gives: a second
        caller of `new_character_vitals` is the second source of birth
        values `COO-DECISION 20260902_0443` point 1 forbids, and this file
        will not become one in order to check that another file is not.

        THE DOCSTRING IS STRIPPED BEFORE THE SCAN, AND THE FIRST DRAFT DID
        NOT DO THAT.  A `pf-adversary` pass replaced the body with
        `return dict(level=1, hp_current=100, hp_max=100)` and left the
        docstring alone; the old `assertIn("new_character_vitals()")` passed
        **on the docstring's own prose**, `re.search(r"return\\s*\\{")` missed
        `return dict(...)`, and the second source of birth values landed
        green -- then hp 100->200 in `persistence_vitals` drifted the two
        apart with this file still passing.  Prose read as evidence about
        code.  The scan below runs on the function's real statements, taken
        from the parsed tree, and refuses any literal container.
        """
        import ast

        source = (ROOT / "tests" / "pf_birth_state.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        function = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "seeded_birth")
        body = list(function.body)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            body = body[1:]
        statements = "\n".join(ast.dump(node) for node in body)
        self.assertIn("new_character_vitals", statements,
                      "seeded_birth() no longer calls the ordered function; "
                      "the birth values now live in two places")
        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            self.assertNotIsInstance(
                node, (ast.Dict, ast.DictComp),
                "seeded_birth() builds a literal mapping; the numbers can "
                "now disagree with persistence_vitals and nothing would say so")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                self.assertNotEqual(
                    "dict", node.func.id,
                    "seeded_birth() builds a dict from keywords; same defect "
                    "as a literal, spelled differently")

    def test_the_seeded_state_holds_the_vital_columns_and_only_those(self):
        self.assertEqual(sorted(vitals.VITAL_COLUMNS),
                         sorted(birth_state.seeded_birth()))

    def test_a_caller_cannot_mutate_the_seeded_state_for_the_next_caller(self):
        first = birth_state.seeded_birth()
        first["level"] = 999
        self.assertNotEqual(first, birth_state.seeded_birth())

    def test_it_refuses_a_column_no_accepted_state_carries(self):
        """The refusal, on a column that is genuinely outside every state.

        This was `test_it_refuses_a_fourth_column` and it used `speed_walk`,
        which `migrations/009_character_birth_defaults.sql` then made a legal
        FOURTH column (`COO-DECISION 20260902_1607`).  Asking
        `pf_birth_state` which columns no accepted state carries keeps the
        refusal measured instead of turning this test into a defence of a
        superseded decision.
        """
        column = birth_state.a_column_no_birth_carries()
        for base in birth_state.accepted_birth_states():
            state = dict(base)
            state[column] = 3
            store = _FakeStore({1: state})
            with self.assertRaises(AssertionError) as caught:
                birth_state.measure_birth_typed_state(store, 1)
            self.assertIn(column, str(caught.exception))

    def test_it_refuses_a_level_of_zero(self):
        state = dict(self._seeded())
        state["level"] = 0
        store = _FakeStore({1: state})
        with self.assertRaises(AssertionError):
            birth_state.measure_birth_typed_state(store, 1)

    def test_it_refuses_hp_current_above_hp_max(self):
        state = dict(self._seeded())
        state["hp_current"] = state["hp_max"] + 1
        store = _FakeStore({1: state})
        with self.assertRaises(AssertionError):
            birth_state.measure_birth_typed_state(store, 1)

    def test_it_refuses_a_half_written_birth(self):
        state = {"level": self._seeded()["level"]}
        store = _FakeStore({1: state})
        with self.assertRaises(AssertionError):
            birth_state.measure_birth_typed_state(store, 1)

    def test_the_refusal_names_both_accepted_states_and_the_decision(self):
        store = _FakeStore({1: {"level": 4}})
        with self.assertRaises(AssertionError) as caught:
            birth_state.measure_birth_typed_state(store, 1)
        message = str(caught.exception)
        self.assertIn("20260902_0444", message)
        self.assertIn(repr(birth_state.seeded_birth()), message)

    def test_measure_every_birth_refuses_a_bad_SECOND_character(self):
        """The exact regression `measure_every_birth` was written for: a plug
        that seeds character one correctly and every later character wrong."""
        bad = dict(self._seeded())
        bad["level"] = 0
        store = _FakeStore({1: self._seeded(), 2: bad})
        with self.assertRaises(AssertionError):
            birth_state.measure_every_birth(store, [1, 2])

    def test_measure_every_birth_returns_one_state_per_id_in_order(self):
        """Three DISTINGUISHABLE states, because the first draft used a
        palindrome (`[{}, seeded, {}]`) and a `pf-adversary` pass reversed
        the iteration inside the helper with this file -- and all five other
        lane files -- still green.  The order is load-bearing:
        `tests/test_persistence_vitals_or_none.py` unpacks
        `self.birth, self.second_birth = measure_every_birth(...)`, so a
        reversal silently grades the wrong row.
        """
        unseeded, seeded = birth_state.accepted_birth_states()[:2]
        store = _FakeStore({1: unseeded, 2: seeded, 3: unseeded})
        self.assertEqual(
            [unseeded, seeded, unseeded],
            birth_state.measure_every_birth(store, [1, 2, 3]))
        self.assertEqual(
            [seeded, unseeded],
            birth_state.measure_every_birth(store, [2, 3]),
            "the helper does not follow the order of the ids it was given")
        self.assertEqual(
            [unseeded, seeded],
            birth_state.measure_every_birth(store, [3, 2]))

    def test_with_birth_lets_what_the_test_wrote_win(self):
        birth = self._seeded()
        self.assertEqual(
            12, birth_state.with_birth(birth, level=12)["level"])
        self.assertEqual(self._seeded(), birth,
                         "with_birth mutated the birth state it was given")

    def test_birth_by_x_uses_the_typed_column_table_for_its_keys(self):
        birth = self._seeded()
        by_x = birth_state.birth_by_x(birth)
        # Written out from the vitals module's own x constants rather than
        # recomputed with the implementation's expression, which is what the
        # first draft did and which grades nothing.
        self.assertEqual(
            {vitals.LEVEL_X: birth["level"],
             vitals.HP_CURRENT_X: birth["hp_current"],
             vitals.HP_MAX_X: birth["hp_max"]},
            by_x)


class TheClearingHelperIsTestedTests(_PreLaneWorkspace):
    """`clear_vitals_to_pre_seed` -- the other half of the gate, and the one
    that writes.  It is raw SQL on a temporary file by design; what has never
    been measured is that it clears the rows it was ASKED for and no others,
    and that it fails loudly rather than reporting a clean pre-seed state it
    did not build."""

    def test_it_clears_only_the_ids_it_was_given(self):
        """EVERY other row is inspected, not just the next one.

        The first draft looked at `ids[0]` and `ids[1]` and left the third
        row unread; a `pf-adversary` pass appended the table's highest id to
        the caller's list inside the helper and this file stayed green,
        while `tests/test_persistence_vitals_or_none.py` keeps a deliberately
        SEEDED second row as its control and would have had it wiped.
        """
        ids = self._make_pre_lane_rows()
        self._boot()
        self.assertGreaterEqual(len(ids), 3, "fixture too small to see this")
        self.assertEqual(0, birth_state.clear_vitals_to_pre_seed(
            self.path, [ids[0]]))
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual({}, {k: v for k, v in
                              store.read_typed_attributes(ids[0]).items()
                              if k in vitals.VITAL_COLUMNS})
        for untouched in ids[1:]:
            self.assertEqual(
                dict(birth_state.seeded_birth()),
                {k: v for k, v in
                 store.read_typed_attributes(untouched).items()
                 if k in vitals.VITAL_COLUMNS},
                "character %d was cleared and nobody asked for it" % untouched)

    def test_it_leaves_speed_walk_alone_because_it_is_not_a_vital(self):
        ids = self._make_pre_lane_rows()
        self._boot()
        birth_state.clear_vitals_to_pre_seed(self.path, [ids[0]])
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(_speed_walk_seeded_by_008(),
                         store.read_typed_attributes(ids[0])["speed_walk"])

    def test_clearing_every_row_leaves_the_whole_table_pre_seed(self):
        ids = self._make_pre_lane_rows()
        self._boot()
        self.assertEqual(0, birth_state.clear_vitals_to_pre_seed(self.path))
        store = SQLiteStore(self.path, MIGRATIONS)
        for character_id in ids:
            self.assertIsNone(
                store.read_character_vitals_or_none(character_id))

    def test_a_database_without_the_table_raises_rather_than_reporting_zero(self):
        empty = self.root / "not-a-world.sqlite3"
        sqlite3.connect(str(empty)).close()
        with self.assertRaises(sqlite3.OperationalError):
            birth_state.clear_vitals_to_pre_seed(empty)

    def test_it_holds_no_handle_on_the_database_after_it_returns(self):
        """A LEAKED HANDLE, not merely a held write lock.

        The first draft asserted `BEGIN IMMEDIATE` / `ROLLBACK` succeeds,
        and a `pf-adversary` pass showed that is a different property: a
        committed-but-unclosed connection holds no lock, so a helper that
        never calls `close()` left this green.  `SQLiteStore.connect` sets
        `journal_mode=WAL`, and switching a WAL database to `DELETE` is
        refused while ANY other connection is open -- which is the shape
        that matters, because the gate runs on `windows-latest` where a live
        handle under a `TemporaryDirectory` is what breaks the cleanup.
        Both arms were measured: leaked -> `database is locked`; shipped
        helper -> the pragma returns `delete`.
        """
        ids = self._make_pre_lane_rows()
        self._boot()
        birth_state.clear_vitals_to_pre_seed(self.path, [ids[0]])
        db = sqlite3.connect(str(self.path))
        try:
            mode = db.execute("PRAGMA journal_mode=DELETE").fetchone()[0]
        finally:
            db.close()
        self.assertEqual("delete", str(mode).lower())


class TheSecondAllowlistCannotRotTests(unittest.TestCase):
    """`NewCharacterVitalsTests.test_only_the_ordered_call_site_may_call_it`
    carries a LOCAL `allowed` set, and unlike
    `NothingIsWiredTests.ALLOWED_TO_NAME_THEM` -- which
    `test_every_allowed_file_exists_and_really_names_them` guards -- nothing
    checked that its entries still name real files.

    A `pf-adversary` pass raised it against this round, which adds an entry
    to it: rename or delete the file the entry names and the exemption
    survives forever, silently, as a hole the next round can drop a real
    second source of birth values into.  The guard lives here rather than
    in that file because the entry this round added is the one that made
    the hole worth closing.
    """

    def test_every_entry_in_it_is_a_file_that_still_names_the_function(self):
        import ast

        source = (ROOT / "tests" / "test_persistence_vitals.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        entries = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "test_only_the_ordered_call_site_may_call_it"):
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Set):
                        entries = [element.value for element in inner.elts
                                   if isinstance(element, ast.Constant)]
        self.assertIsNotNone(
            entries,
            "the allowlist this test guards is no longer a set literal in "
            "that test; the guard cannot see it and must be rewritten")
        self.assertTrue(entries)
        for relative in entries:
            self.assertTrue(
                (ROOT / relative).is_file(),
                "%s is exempt from the birth-value scan and does not exist; "
                "the exemption outlived the file it was written for"
                % relative)

    def test_it_is_not_also_required_to_name_the_function_and_why(self):
        """The sibling guard on `ALLOWED_TO_NAME_THEM` additionally requires
        each entry to MENTION the methods, and this one deliberately does
        not.  `src/pirateforce_foundation/store.py` is on this list as the
        call site `COO-DECISION 20260902_0443` point 1 ORDERS and chief has
        not written yet -- measured today: it names the function zero times.
        Requiring the mention here would make the entry that exists for a
        future line into a red test until that line lands, which is the
        landmine-in-another-lane's-corridor shape this lane keeps paying for.
        Pinned so a later round does not "tighten" this guard into one.
        """
        store_source = (ROOT / "src" / "pirateforce_foundation"
                        / "store.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "new_character_vitals", store_source,
            "the ordered call site has landed; this test's premise is out "
            "of date and the round that sees it should say so rather than "
            "delete it")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
