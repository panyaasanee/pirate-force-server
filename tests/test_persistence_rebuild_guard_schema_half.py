"""LANE-DB: the SECOND half of the rebuild guard -- the one that watches
the schema, and the linter that bounds the window the first half protects.

WHAT THIS FILE PAYS.  Two findings pf-adversary returned against round
`fw2hs6` after that round's lock was released (`pf_bridge/rounds/
DB_20260908_1602_fw2hs6_addendum_pf-adversary-not-clean.md`):

  D1 [CRITICAL].  A one-token mutant deleting `REFERENCES characters(id)`
  from `migrations/018` passed the ENTIRE suite with identical numbers, and
  the test named `test_foreign_key_integrity_holds_after_the_rebuild`
  passed BECAUSE the foreign key was gone -- `pragma_foreign_key_check` has
  nothing to check on a table that carries no constraints.  The guard
  compares ROWS and a rebuild exists to change the SCHEMA, so it looked
  away by construction.  `persistence_rebuild_guard.schema_snapshot_sql` /
  `schema_verify_sql` are the half that looks.

  D2 [HIGH].  The row corruption the guard was built to stop moved UP one
  line, above the snapshot, and passed green -- the window the guard
  protects begins AT the snapshot and nothing proved the snapshot was the
  first statement in the transaction.  No SQL emitted from inside that
  window can bound it; `window_violations` bounds it from outside, by
  reading the file, which is what the tests that pin a migration are for.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim `migrations/018` is
repaired -- `018` is applied and frozen, its text pinned by the ledger's
checksum, and it carries neither new builder.  It claims the tools the NEXT
rebuild carries exist and are measured, and that `018` as shipped is clean
under the linter.  Nothing here is client-observable.
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
_HOME = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _migrations_upto(root, last):
    """A migrations directory holding `001`..`<last>` only."""
    directory = root / f"upto_{last:03d}"
    directory.mkdir()
    for path in sorted(MIGRATIONS.glob("*.sql")):
        if path.name[:3].isdigit() and int(path.name[:3]) <= last:
            shutil.copy(path, directory / path.name)
    return directory


class TheSchemaHalfSeesWhatTheRowGuardCannotTests(unittest.TestCase):
    """A synthetic rebuild of a child table, run three ways.

    Synthetic rather than against `018` itself because `018` is frozen: the
    point is what the NEXT rebuild gets, and a two-table fixture makes the
    single changed token visible without 120 lines of unrelated prose in
    the way.  The `018`-shaped measurement is the class below.
    """

    SEED = """
    CREATE TABLE parent(id INTEGER PRIMARY KEY);
    CREATE TABLE kid(
        id INTEGER PRIMARY KEY,
        pid INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE,
        n INTEGER NOT NULL
    );
    CREATE INDEX kid_pid ON kid(pid);
    INSERT INTO parent(id) VALUES (1),(2);
    INSERT INTO kid(id,pid,n) VALUES (1,1,10),(2,2,20);
    """

    #: The honest rebuild: same columns, same constraints, one CHECK added.
    REBUILD = """
    CREATE TABLE kid_rebuild(
        id INTEGER PRIMARY KEY,
        pid INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE,
        n INTEGER NOT NULL CHECK(n>=0)
    );
    INSERT INTO kid_rebuild(id,pid,n) SELECT id,pid,n FROM kid;
    DROP TABLE kid;
    ALTER TABLE kid_rebuild RENAME TO kid;
    CREATE INDEX kid_pid ON kid(pid);
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "schema_half.sqlite3"

    def _script(self, rebuild):
        return "\n".join(
            (
                "BEGIN;",
                guard.snapshot_sql("kid", "_pf_t"),
                guard.schema_snapshot_sql("kid", "_pf_t"),
                rebuild,
                guard.verify_sql("kid", ("id", "pid", "n"), "_pf_t"),
                guard.schema_verify_sql("kid", "_pf_t"),
                guard.schema_drop_sql("_pf_t"),
                guard.drop_sql("_pf_t"),
                "COMMIT;",
            )
        )

    def _run(self, rebuild):
        db = sqlite3.connect(str(self.path))
        try:
            db.executescript(self.SEED)
            db.commit()
            db.executescript(self._script(rebuild))
        finally:
            db.close()

    def _rows(self):
        db = sqlite3.connect(str(self.path))
        try:
            return [tuple(r) for r in db.execute(
                "SELECT id,pid,n FROM kid ORDER BY id")]
        finally:
            db.close()

    def test_an_honest_rebuild_passes_and_keeps_its_rows(self):
        self._run(self.REBUILD)
        self.assertEqual(self._rows(), [(1, 1, 10), (2, 2, 20)])

    def test_a_dropped_foreign_key_is_caught(self):
        """D1, reproduced and then closed: the single token the whole
        14,7xx-test suite could not see."""
        mutant = self.REBUILD.replace(
            "pid INTEGER NOT NULL REFERENCES parent(id) ON DELETE CASCADE,",
            "pid INTEGER NOT NULL,",
            1,
        )
        self.assertNotEqual(mutant, self.REBUILD)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(mutant)

    def test_a_weakened_on_delete_action_is_caught(self):
        """`CASCADE` turned into the default `NO ACTION` keeps the foreign
        key -- so `pragma_foreign_key_list` being non-empty proves nothing,
        and the guard has to compare the ROW it returns."""
        mutant = self.REBUILD.replace(
            "REFERENCES parent(id) ON DELETE CASCADE",
            "REFERENCES parent(id)",
            1,
        )
        self.assertNotEqual(mutant, self.REBUILD)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(mutant)

    def test_a_foreign_key_pointed_at_the_wrong_column_is_caught(self):
        db = sqlite3.connect(str(self.path))
        try:
            db.executescript(self.SEED)
            db.execute("CREATE TABLE other(id INTEGER PRIMARY KEY)")
            db.commit()
        finally:
            db.close()
        mutant = self.REBUILD.replace(
            "REFERENCES parent(id) ON DELETE CASCADE",
            "REFERENCES other(id) ON DELETE CASCADE",
            1,
        )
        db = sqlite3.connect(str(self.path))
        try:
            with self.assertRaises(sqlite3.IntegrityError):
                db.executescript(self._script(mutant))
        finally:
            db.close()

    def test_a_lost_index_is_caught(self):
        mutant = self.REBUILD.replace(
            "CREATE INDEX kid_pid ON kid(pid);", "", 1
        )
        self.assertNotEqual(mutant, self.REBUILD)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(mutant)

    def test_an_index_that_quietly_became_unique_is_caught(self):
        mutant = self.REBUILD.replace(
            "CREATE INDEX kid_pid ON kid(pid);",
            "CREATE UNIQUE INDEX kid_pid ON kid(pid);",
            1,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(mutant)

    def test_an_added_index_is_caught_too(self):
        """Both directions: a rebuild that mints an index nobody asked for
        is as much of a silent schema change as one that loses one."""
        mutant = self.REBUILD + "\nCREATE INDEX kid_n ON kid(n);"
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(mutant)

    def test_the_scaffold_tables_do_not_survive_an_honest_run(self):
        self._run(self.REBUILD)
        db = sqlite3.connect(str(self.path))
        try:
            leftovers = [str(r[0]) for r in db.execute(
                "SELECT name FROM sqlite_master WHERE name LIKE '_pf_%'")]
        finally:
            db.close()
        self.assertEqual(leftovers, [])

    def test_the_row_guard_alone_lets_every_one_of_these_through(self):
        """The measurement that makes this half worth carrying: the SAME
        mutants, with only `verify_sql`'s rows watching, all pass green."""
        for mutant in (
            self.REBUILD.replace(
                "pid INTEGER NOT NULL REFERENCES parent(id) "
                "ON DELETE CASCADE,",
                "pid INTEGER NOT NULL,",
                1,
            ),
            self.REBUILD.replace(
                "CREATE INDEX kid_pid ON kid(pid);", "", 1
            ),
        ):
            path = Path(self.tmp.name) / ("rowonly%d.sqlite3" % id(mutant))
            db = sqlite3.connect(str(path))
            try:
                db.executescript(self.SEED)
                db.commit()
                db.executescript(
                    "\n".join(
                        (
                            "BEGIN;",
                            guard.snapshot_sql("kid", "_pf_t"),
                            mutant,
                            guard.verify_sql(
                                "kid", ("id", "pid", "n"), "_pf_t"),
                            guard.drop_sql("_pf_t"),
                            "COMMIT;",
                        )
                    )
                )
                self.assertEqual(
                    [tuple(r) for r in db.execute(
                        "SELECT id,pid,n FROM kid ORDER BY id")],
                    [(1, 1, 10), (2, 2, 20)],
                )
            finally:
                db.close()


class TheSchemaHalfOnAnEighteenShapedRebuildTests(unittest.TestCase):
    """The same measurement against the real `018` file and the real
    migration runner, so the helper is not proved only on a fixture."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upto_017 = _migrations_upto(self.root, 17)
        self.eighteen = EIGHTEEN.read_text(encoding="utf-8")

    def _with_schema_half(self, text):
        """`018`, plus the half it was written before."""
        text = text.replace(
            guard.snapshot_sql(TABLE, TAG),
            guard.snapshot_sql(TABLE, TAG) + "\n"
            + guard.schema_snapshot_sql(TABLE, TAG),
            1,
        )
        return text.replace(
            guard.drop_sql(TAG),
            guard.schema_verify_sql(TABLE, TAG) + "\n"
            + guard.schema_drop_sql(TAG) + "\n" + guard.drop_sql(TAG),
            1,
        )

    def _database_at_017(self, name):
        path = self.root / name
        store = SQLiteStore(path, self.upto_017)
        store.migrate()
        account_id = store.ensure_account("sch" + name[:4])
        character = store.create_character(
            account_id, "Sch" + name[:4], "sch" + name[:4],
            "fp-" + name, _build_wire, _HOME,
        )
        store.grant_starting_skills(character.id, (99, 210))
        return path

    def _run(self, path, sql, name):
        directory = self.root / ("mig_" + name)
        shutil.copytree(self.upto_017, directory)
        (directory / EIGHTEEN.name).write_text(sql, encoding="utf-8")
        SQLiteStore(path, directory).migrate()

    def test_the_real_file_plus_the_schema_half_still_applies_cleanly(self):
        path = self._database_at_017("honest.sqlite3")
        armed = self._with_schema_half(self.eighteen)
        self.assertNotEqual(armed, self.eighteen)
        self._run(path, armed, "honest")
        db = sqlite3.connect(str(path))
        try:
            self.assertEqual(
                [tuple(r) for r in db.execute(
                    "SELECT skill_id FROM character_skills ORDER BY id")],
                [(99,), (210,)],
            )
            self.assertIn(
                (18,),
                [tuple(r) for r in db.execute(
                    "SELECT version FROM schema_migrations")],
            )
        finally:
            db.close()

    def test_the_d1_mutant_that_beat_the_whole_suite_now_goes_red(self):
        """The exact token adversary deleted, on the exact file."""
        path = self._database_at_017("fk.sqlite3")
        armed = self._with_schema_half(self.eighteen)
        mutant = armed.replace(
            "character_id INTEGER NOT NULL REFERENCES characters(id),",
            "character_id INTEGER NOT NULL,",
            1,
        )
        self.assertNotEqual(mutant, armed)
        with self.assertRaises(sqlite3.IntegrityError):
            self._run(path, mutant, "fk")
        db = sqlite3.connect(str(path))
        try:
            self.assertNotIn(
                (18,),
                [tuple(r) for r in db.execute(
                    "SELECT version FROM schema_migrations")],
            )
        finally:
            db.close()

    def test_the_same_mutant_without_the_schema_half_still_passes(self):
        """Not a decoration: this is `018` exactly as it shipped, and the
        mutant sails through -- which is the finding, reproduced."""
        path = self._database_at_017("fkweak.sqlite3")
        mutant = self.eighteen.replace(
            "character_id INTEGER NOT NULL REFERENCES characters(id),",
            "character_id INTEGER NOT NULL,",
            1,
        )
        self._run(path, mutant, "fkweak")
        db = sqlite3.connect(str(path))
        try:
            db.execute("PRAGMA foreign_keys=ON")
            db.execute(
                "INSERT INTO character_skills"
                "(character_id,skill_id,source,granted_at) "
                "VALUES (424242,7,'gm_grant','t')"
            )
            db.commit()
            self.assertEqual(
                [tuple(r) for r in db.execute(
                    "SELECT COUNT(*) FROM character_skills "
                    "WHERE character_id=424242")],
                [(1,)],
            )
        finally:
            db.close()


class TheWindowLinterTests(unittest.TestCase):
    """D2: what bounds the window the row guard protects."""

    def setUp(self):
        self.eighteen = EIGHTEEN.read_text(encoding="utf-8")

    def test_the_shipped_018_is_clean(self):
        self.assertEqual(
            guard.window_violations(self.eighteen, TABLE, TAG), ()
        )

    def test_the_d2_corruption_above_the_snapshot_is_reported(self):
        """The mutant that passed the guard green -- one statement, moved
        one line up, out of the window."""
        mutant = self.eighteen.replace(
            guard.snapshot_sql(TABLE, TAG),
            f"UPDATE {TABLE} SET skill_id=skill_id+1000;\n"
            + guard.snapshot_sql(TABLE, TAG),
            1,
        )
        problems = guard.window_violations(mutant, TABLE, TAG)
        self.assertEqual(len(problems), 1)
        self.assertIn("before the snapshot", problems[0])

    def test_the_d2_corruption_appended_after_the_guard_is_reported(self):
        mutant = self.eighteen + (
            f"\nUPDATE {TABLE} SET skill_id=skill_id+1000;\n"
        )
        problems = guard.window_violations(mutant, TABLE, TAG)
        self.assertEqual(len(problems), 1)
        self.assertIn("after the last guard row", problems[0])

    def test_a_file_with_no_snapshot_at_all_is_reported(self):
        problems = guard.window_violations(
            "BEGIN;\nDROP TABLE character_skills;\nCOMMIT;", TABLE, TAG
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("not in this file", problems[0])

    def test_a_scaffold_left_behind_is_reported(self):
        mutant = self.eighteen.replace(f"DROP TABLE {TAG}_before;", "", 1)
        problems = guard.window_violations(mutant, TABLE, TAG)
        self.assertIn(
            f"{TAG}_before is created but never dropped", problems
        )

    def test_a_comment_mentioning_the_table_is_not_a_violation(self):
        """Every migration in this repository explains itself above the
        SQL, and `018`'s prose names `character_skills` dozens of times --
        a linter that counted those would be turned off within a day."""
        mutant = self.eighteen.replace(
            "CREATE TABLE " + TAG + "_before",
            f"-- UPDATE {TABLE} SET skill_id=0;\nCREATE TABLE "
            + TAG + "_before",
            1,
        )
        self.assertEqual(guard.window_violations(mutant, TABLE, TAG), ())

    def test_a_table_whose_name_is_a_prefix_of_another_is_not_confused(self):
        """`character_skills` must not match `character_skills_rebuild`,
        which `018` creates and drops entirely inside the window."""
        self.assertIn("character_skills_rebuild", self.eighteen)
        self.assertEqual(
            guard.window_violations(self.eighteen, TABLE, TAG), ()
        )

    def test_the_linter_refuses_an_identifier_it_could_not_emit(self):
        with self.assertRaises(guard.RebuildGuardError):
            guard.window_violations(self.eighteen, "character_skills; --", TAG)


if __name__ == "__main__":
    unittest.main()
