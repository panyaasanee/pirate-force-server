"""LANE-DB: the rebuild guard, and the proof that it sees what a row-count
guard could not.

`pf_bridge/rounds/DB_20260908_1316_nivlwg_round.md` records pf-adversary
finding D2 against migration `017`: its seven guards count child rows and
never look at their CONTENT, so an `UPDATE ... SET scene_id=99` slipped in
before the `DROP` passes green.  `017` is applied and frozen and cannot be
repaired; the repair named in that round's own "next round" list is a
helper every later rebuild borrows, and the first migration to carry it.

This file proves three separate things, and the third is the one that
matters:

  1. `persistence_rebuild_guard` builds the SQL it claims to build and
     refuses a name it cannot safely concatenate;
  2. `migrations/018_character_skills_gm_grant_source.sql` carries that
     helper's output VERBATIM, against the complete column list read out of
     `PRAGMA table_info` on a database migrated to `017` -- not a column
     list typed a second time in the migration and hoped to be complete;
  3. against the same corrupted rebuild, the OLD count-only guard passes
     and the NEW content guard aborts the migration.  Point 3 is what makes
     this a guard rather than a decoration, and it is measured here on a
     real database, not argued.

NONCLAIM ADDED AFTER ADVERSARY FINDING D4 (round `fw2hs6`).  Point 3 is
carried by exactly TWO of the mutants below -- `test_the_old_count_only_
guard_passes_the_corrupted_rebuild` paired with `test_the_content_guard_
aborts_the_same_corrupted_rebuild`, and `test_a_dropped_column_filled_by_a_
default_is_caught`.  `test_a_lost_row_is_caught_too` is caught by the row
COUNT as well and separates nothing; it is here because losing a row is a
failure worth pinning, not as evidence for point 3.

WHAT THIS FILE STILL DOES NOT WATCH.  The SCHEMA.  A rebuild that quietly
drops a foreign key passes every test here (adversary finding D1) -- that
half lives in `tests/test_persistence_rebuild_guard_schema_half.py`, on
`schema_snapshot_sql`/`schema_verify_sql`, which `018` predates and cannot
carry.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_rebuild_guard as guard  # noqa: E402
from pirateforce_foundation.model import Position                     # noqa: E402
from pirateforce_foundation.store import SQLiteStore                  # noqa: E402

MIGRATIONS = ROOT / "migrations"
EIGHTEEN = MIGRATIONS / "018_character_skills_gm_grant_source.sql"

TABLE = "character_skills"
TAG = "_pf_mig018"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
_next_identity = iter(range(0x20009000, 0x2000A000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


def _migrations_upto(root: Path, highest: int) -> Path:
    """A migrations directory holding every file up to and including
    `highest` -- the same shape `test_persistence_character_skills_
    learned_014.py` uses to reach a pre-rebuild database."""
    subset = root / f"migrations_{highest:03d}"
    subset.mkdir()
    for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
        if int(path.name[:3]) <= highest:
            shutil.copy(path, subset / path.name)
    return subset


def _rows(path: Path):
    db = sqlite3.connect(str(path))
    try:
        return [
            tuple(row)
            for row in db.execute(
                "SELECT id,character_id,skill_id,source,granted_at "
                f"FROM {TABLE} ORDER BY id"
            )
        ]
    finally:
        db.close()


class TheHelperBuildsWhatItSaysTests(unittest.TestCase):
    def test_the_snapshot_is_a_plain_data_copy(self):
        self.assertEqual(
            guard.snapshot_sql("t", "_x"),
            "CREATE TABLE _x_before AS SELECT * FROM t;",
        )

    def test_the_verify_block_asks_both_directions_and_the_count(self):
        sql = guard.verify_sql("t", ("a", "b"), "_x")
        self.assertIn("CREATE TABLE _x_guard(ok INTEGER NOT NULL CHECK(ok=1));", sql)
        self.assertIn("SELECT COUNT(*) FROM t)=(SELECT COUNT(*) FROM _x_before)", sql)
        self.assertIn("SELECT a,b FROM t EXCEPT SELECT a,b FROM _x_before", sql)
        self.assertIn("SELECT a,b FROM _x_before EXCEPT SELECT a,b FROM t", sql)
        self.assertIn("pragma_foreign_key_check()", sql)
        # Four guard rows, one question each.
        self.assertEqual(sql.count("INSERT INTO _x_guard(ok)"), 4)

    def test_the_drop_removes_both_scaffold_tables(self):
        self.assertEqual(
            guard.drop_sql("_x"),
            "DROP TABLE _x_guard;\nDROP TABLE _x_before;",
        )

    def test_a_name_that_is_not_an_identifier_is_refused(self):
        for bad in ("t;DROP", "t t", "", "t'", '"t"', "9t"):
            with self.assertRaises(guard.RebuildGuardError):
                guard.snapshot_sql(bad, "_x")
            with self.assertRaises(guard.RebuildGuardError):
                guard.drop_sql(bad)

    def test_a_column_list_that_cannot_guard_anything_is_refused(self):
        with self.assertRaises(guard.RebuildGuardError):
            guard.verify_sql("t", (), "_x")
        with self.assertRaises(guard.RebuildGuardError):
            guard.verify_sql("t", "ab", "_x")
        with self.assertRaises(guard.RebuildGuardError):
            guard.verify_sql("t", ("a", "a"), "_x")
        with self.assertRaises(guard.RebuildGuardError):
            guard.verify_sql("t", ("a", "b;--"), "_x")

    def test_the_helper_runs_nothing(self):
        """Every public name here returns text.  A helper that executed
        would put logic inside the migration checksum's blind spot.

        Measured off the parsed module, not off its prose: the docstring
        names `executescript` while explaining why it is not called here.
        """
        import ast

        tree = ast.parse(
            (
                ROOT
                / "src"
                / "pirateforce_foundation"
                / "persistence_rebuild_guard.py"
            ).read_text(encoding="utf-8")
        )
        imported = set()
        called = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module or "")
            elif isinstance(node, ast.Call) and isinstance(
                node.func, ast.Attribute
            ):
                called.add(node.func.attr)
        self.assertEqual(imported, {"__future__"}, sorted(imported))
        self.assertEqual(
            called & {"execute", "executescript", "executemany", "connect"},
            set(),
            sorted(called),
        )


class MigrationEighteenCarriesTheHelpersOutputTests(unittest.TestCase):
    """The pin: `018`'s guard text is regenerated here from the helper and
    from the table's PRE-migration column list, read off a database at
    `017`.  A column added to the table without being added to `018`'s
    guard list, or a hand edit of `018`'s guard statements, fails here."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _columns_at_017(self):
        path = self.root / "at017.sqlite3"
        SQLiteStore(path, _migrations_upto(self.root, 17)).migrate()
        db = sqlite3.connect(str(path))
        try:
            return tuple(
                str(row[1])
                for row in db.execute(
                    f"SELECT cid,name FROM pragma_table_info('{TABLE}') "
                    "ORDER BY cid"
                )
            )
        finally:
            db.close()

    def test_the_guard_statements_are_the_helpers_output_verbatim(self):
        columns = self._columns_at_017()
        text = EIGHTEEN.read_text(encoding="utf-8")
        self.assertIn(guard.snapshot_sql(TABLE, TAG), text)
        self.assertIn(guard.verify_sql(TABLE, columns, TAG), text)
        self.assertIn(guard.drop_sql(TAG), text)

    def test_the_guarded_column_list_is_the_whole_table(self):
        """Not a subset that happens to pass: every column the table had
        before `018` must appear in the guard's SELECT lists."""
        columns = self._columns_at_017()
        text = EIGHTEEN.read_text(encoding="utf-8")
        self.assertEqual(
            set(columns),
            {"id", "character_id", "skill_id", "source", "granted_at"},
        )
        self.assertIn("SELECT " + ",".join(columns) + f" FROM {TABLE}", text)

    def test_the_snapshot_is_taken_before_the_table_is_dropped(self):
        text = EIGHTEEN.read_text(encoding="utf-8")
        self.assertLess(
            text.index(guard.snapshot_sql(TABLE, TAG)),
            text.index(f"DROP TABLE {TABLE};"),
        )
        self.assertLess(
            text.index(f"ALTER TABLE {TABLE}_rebuild RENAME TO {TABLE};"),
            text.index(guard.verify_sql(TABLE, self._columns_at_017(), TAG)),
        )

    def test_no_scaffold_table_survives_the_migration(self):
        path = self.root / "clean.sqlite3"
        SQLiteStore(path, MIGRATIONS).migrate()
        db = sqlite3.connect(str(path))
        try:
            leftovers = [
                str(r[0])
                for r in db.execute(
                    "SELECT name FROM sqlite_master WHERE name LIKE '_pf_%'"
                )
            ]
        finally:
            db.close()
        self.assertEqual(leftovers, [])


class TheGuardCatchesWhatTheCountMissedTests(unittest.TestCase):
    """Point 3, measured: one corrupted rebuild, two guards, two answers.

    The corruption is the exact shape pf-adversary used against `017` --
    a row rewritten in place before the `DROP`, leaving the row COUNT
    untouched.
    """

    #: `017`'s guard shape: a count and nothing else.
    COUNT_ONLY = "\n".join(
        (
            f"CREATE TABLE {TAG}_guard(ok INTEGER NOT NULL CHECK(ok=1));",
            f"INSERT INTO {TAG}_guard(ok) SELECT CASE WHEN"
            f" (SELECT COUNT(*) FROM {TABLE})"
            f"=(SELECT COUNT(*) FROM {TAG}_before) THEN 1 ELSE 0 END;",
        )
    )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upto_017 = _migrations_upto(self.root, 17)
        self.eighteen = EIGHTEEN.read_text(encoding="utf-8")

    def _database_at_017_with_two_skill_rows(self, name):
        path = self.root / name
        store = SQLiteStore(path, self.upto_017)
        store.migrate()
        account_id = store.ensure_account("guard" + name[:4])
        character = store.create_character(
            account_id, "Guard" + name[:4], "guard" + name[:4],
            "fp-" + name, _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99, 210))
        return path, character.id

    def _run_eighteen(self, path, sql_018, name):
        """Apply a (possibly corrupted) `018` to a database already at
        `017`, through the real runner."""
        directory = self.root / ("mig_" + name)
        shutil.copytree(self.upto_017, directory)
        (directory / EIGHTEEN.name).write_text(sql_018, encoding="utf-8")
        SQLiteStore(path, directory).migrate()

    def _corrupt(self, text):
        """The D2 mutant: rewrite every row in place, right before the
        `DROP`, exactly as an accidental stray statement would.

        `+1000` rather than D2's literal `=99` because this table carries
        `UNIQUE(character_id, skill_id)` -- collapsing two rows onto one
        value would be caught by the constraint rather than by any guard,
        which would prove nothing about either guard.  An offset keeps the
        row count and the uniqueness intact and changes only the content,
        which is precisely the blind spot under test.
        """
        marker = f"DROP TABLE {TABLE};"
        self.assertIn(marker, text)
        return text.replace(
            marker,
            f"UPDATE {TABLE}_rebuild SET skill_id=skill_id+1000;\n" + marker,
            1,
        )

    def test_the_old_count_only_guard_passes_the_corrupted_rebuild(self):
        path, character_id = self._database_at_017_with_two_skill_rows(
            "countonly.sqlite3"
        )
        columns = ("id", "character_id", "skill_id", "source", "granted_at")
        weakened = self.eighteen.replace(
            guard.verify_sql(TABLE, columns, TAG), self.COUNT_ONLY, 1
        )
        # The prose above the SQL discusses `EXCEPT`; only the statements
        # matter, so measure the body, which starts at the runner handshake.
        body = weakened[weakened.index("COMMIT;\nPRAGMA foreign_keys=OFF;") :]
        self.assertNotIn("EXCEPT", body)
        self._run_eighteen(path, self._corrupt(weakened), "weak")
        # It passed -- and every skill id in the owner's database is now
        # a different number than the one that went in.  This is the
        # finding, reproduced against a real database.
        self.assertEqual({row[2] for row in _rows(path)}, {1099, 1210})

    def test_the_content_guard_aborts_the_same_corrupted_rebuild(self):
        path, character_id = self._database_at_017_with_two_skill_rows(
            "content.sqlite3"
        )
        before = _rows(path)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run_eighteen(path, self._corrupt(self.eighteen), "strong")
        # Aborted AND rolled back: the rows are the ones that went in, and
        # `018` is not in the ledger.
        self.assertEqual(_rows(path), before)
        db = sqlite3.connect(str(path))
        try:
            versions = {
                int(r[0])
                for r in db.execute("SELECT version FROM schema_migrations")
            }
        finally:
            db.close()
        self.assertNotIn(18, versions)

    def test_a_dropped_column_filled_by_a_default_is_caught(self):
        path, _ = self._database_at_017_with_two_skill_rows("col.sqlite3")
        before = _rows(path)
        mutant = self.eighteen.replace(
            "SELECT id,character_id,skill_id,source,granted_at "
            f"FROM {TABLE};",
            "SELECT id,character_id,skill_id,'starting_kit',granted_at "
            f"FROM {TABLE};",
            1,
        )
        # Only meaningful if the substitution actually landed AND the rows
        # really do carry a non-'starting_kit' source to lose.
        self.assertNotEqual(mutant, self.eighteen)
        db = sqlite3.connect(str(path))
        try:
            db.execute(
                f"UPDATE {TABLE} SET source='learned' WHERE skill_id=210"
            )
            db.commit()
        finally:
            db.close()
        before = _rows(path)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run_eighteen(path, mutant, "col")
        self.assertEqual(_rows(path), before)

    def test_a_lost_row_is_caught_too(self):
        """A row that the REBUILD drops on the way across.

        PAYS ADVERSARY FINDING D4 (round `fw2hs6`).  This test used to
        mutate the first `FROM character_skills;` in the file, which is the
        SNAPSHOT statement on line 102, not the copy on line 113 -- so the
        rebuilt table lost nothing and the SNAPSHOT was the short one.  It
        went red for the wrong reason and measured the mirror image of its
        own name.  The mutant now names the copy statement in full, the
        same way `test_a_dropped_column_filled_by_a_default_is_caught`
        beside it already does, and the test asserts the snapshot line is
        untouched so this cannot silently drift back.

        NONCLAIM: unlike the two tests above, this mutant is caught by the
        row-count guard as well -- a lost row changes the count.  It does
        not separate the new guard from the old one and is not offered as
        evidence that it does; it is here because "the rebuild loses a row"
        is a failure the guard must catch on the way in, not because it is
        a failure only the new guard can see.
        """
        path, _ = self._database_at_017_with_two_skill_rows("lost.sqlite3")
        before = _rows(path)
        copy_statement = (
            "SELECT id,character_id,skill_id,source,granted_at "
            f"FROM {TABLE};"
        )
        mutant = self.eighteen.replace(
            copy_statement,
            "SELECT id,character_id,skill_id,source,granted_at "
            f"FROM {TABLE} WHERE skill_id<>210;",
            1,
        )
        self.assertNotEqual(mutant, self.eighteen)
        self.assertIn(guard.snapshot_sql(TABLE, TAG), mutant)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run_eighteen(path, mutant, "lost")
        self.assertEqual(_rows(path), before)

    def test_an_honest_rebuild_still_passes(self):
        """The guard's other half: it must not refuse the real file."""
        path, character_id = self._database_at_017_with_two_skill_rows(
            "honest.sqlite3"
        )
        before = _rows(path)
        self._run_eighteen(path, self.eighteen, "honest")
        self.assertEqual(_rows(path), before)
        db = sqlite3.connect(str(path))
        try:
            versions = {
                int(r[0])
                for r in db.execute("SELECT version FROM schema_migrations")
            }
        finally:
            db.close()
        self.assertIn(18, versions)


if __name__ == "__main__":
    unittest.main()
