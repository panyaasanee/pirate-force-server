"""LANE-DB: the count `COO-DECISION 20260903_1047` point 2 ordered, and the
cards that keep it from lying in the reassuring direction.

WHAT THIS FILE PROVES (wire/DB layer only):

1. **The audited list is the four adjudicated columns, and it is checked
   against the SCHEMA rather than against itself.**  A fifth column gaining a
   `DEFAULT` turns this file red instead of slipping past the count.
2. **The window is real and this file walks through it.**  A character born
   on a database at `008` and carried forward to `009` really does end up
   with `speed_walk` NULL, and the audit really does count it.  That is not
   a mock -- the migrations directory is assembled file by file, the store
   boots on it, and `009` is added afterwards exactly as the owner's database
   will meet it.
3. **Soft-deleted rows are counted separately, not dropped.**  The mistake
   `persistence_vitals.census_sql` was caught making, pinned here for the
   count that would decide a backfill.
4. **It writes nothing** -- asserted on the file's own sha256, mtime and
   `data_version`, over a database deliberately put back into ROLLBACK
   JOURNAL mode, which is where the first draft failed this: it went through
   `SQLiteStore.connect()`, whose `PRAGMA journal_mode=WAL` moved the file's
   bytes while the docstring said it wrote nothing.
5. **The write path is untouched.**  `persistence_vitals.VITAL_COLUMNS` still
   holds exactly three names, which is what that decision forbade changing.
6. **THE STORE DOOR ITSELF IS EXERCISED**, not only the raw SQL underneath
   it.  The first draft tested `audit_sql()` through `sqlite3.connect` and
   never called `SQLiteStore.typed_column_null_audit` once: a `pf-adversary`
   pass deleted the whole method and the suite was byte-identical, and three
   mutants inside it -- answering with the census query, dropping the schema
   check, and returning zero for every column on every database -- all
   survived.  A door nothing opens is not a delivered door.
7. **A count that could not be taken says so.**  An empty table makes every
   `SUM()` NULL, and the report may not print that as `0`.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no frame
is composed and no player can see a difference.  Every database here is built
in a `TemporaryDirectory` -- **this file has never run against the owner's
canonical database, and the number COO asked for is a number only that
database can answer.**  Nothing here backfills anything, and nothing here
says a NULL `speed_walk` is a defect: `COO-DECISION 20260902_1043` chose to
leave that column unseeded at birth.
"""
import ast
import hashlib
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

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402,E501
from pirateforce_foundation import persistence_null_audit as audit_module  # noqa: E402,E501
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class TheAuditedListIsDerivedNotTypedTests(unittest.TestCase):
    """The list cannot rot into a stale set of strings, and it cannot
    silently miss a column somebody adjudicates next month."""

    def test_it_is_the_three_vitals_plus_the_column_x7_serves(self):
        self.assertEqual(
            audit_module.NULL_AUDIT_COLUMNS,
            tuple(vitals.VITAL_COLUMNS) + (typed.column_for(7),),
        )

    def test_x7_is_the_speed_column_according_to_another_module(self):
        """Graded against `persistence_attr_compose`'s own field table rather
        than against the string `"speed_walk"` typed here -- the house rule
        that a card may not retype a list it is checking."""
        rows = {x: name for x, name, *_ in compose._SERVER_OWNED_ROWS}
        self.assertEqual(rows[audit_module.SPEED_WALK_X], typed.column_for(7))

    def test_x7_is_the_same_field_the_store_names(self):
        """The second copy, graded instead of removed.  `store.py` holds
        `SPEED_WALK_FIELD_X = 7` and this module holds its own `7`; the
        import that would remove the duplication is a cycle, since `store`
        imports this module.  So the two are compared here and a change to
        either goes red."""
        self.assertEqual(audit_module.SPEED_WALK_X,
                         store_module.SPEED_WALK_FIELD_X)

    def test_the_write_path_constant_was_not_touched(self):
        """`COO-DECISION 20260903_1047` point 2, the forbidden half: adding a
        fourth name to `VITAL_COLUMNS` changes how a character is born
        (`store.py`'s birth guard reads it) and is not a count."""
        self.assertEqual(len(vitals.VITAL_COLUMNS), 3)
        self.assertNotIn(typed.column_for(7), vitals.VITAL_COLUMNS)

    def test_nothing_in_the_module_can_write(self):
        """Read-only is the whole licence this module has
        (`COO-DECISION 20260903_1047` point 2 forbids the backfill), so it is
        asserted rather than promised.

        DOCSTRINGS ARE STRIPPED FIRST, and the first draft did not strip
        them: it scanned the raw source, and quoting `008`'s own
        `UPDATE characters SET speed_walk = ...` in the header -- which is
        the evidence for the window this module counts -- turned it red.
        Prose read as evidence about code is the trap this lane keeps being
        caught by; it cuts both ways, and this is the side where it refuses
        an honest citation.
        """
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "persistence_null_audit.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(
                    node.value, ast.Constant) and isinstance(
                        node.value.value, str):
                node.value.value = ""
        executable = ast.dump(tree).upper()
        for verb in ("UPDATE ", "INSERT ", "DELETE ", "ALTER ", "DROP ",
                     "REPLACE INTO", "CREATE TABLE"):
            self.assertNotIn(verb, executable, verb)
        # And the control: the one verb it DOES contain, so a mangled parse
        # cannot make this vacuous.
        self.assertIn("SELECT ", executable)


class TheListMatchesTheSchemaAtHeadTests(unittest.TestCase):
    """THE DRIFT CARD.  On a database migrated to HEAD, the typed columns
    carrying a schema `DEFAULT` are exactly the audited four.

    A fifth adjudicated column arrives as a `DEFAULT` in a new migration --
    that is the shape `009` established -- and it would otherwise be missed
    by a count nobody re-derived.  This is deliberately NOT how the module
    builds its list: a database still at `008` carries no typed `DEFAULT` at
    all, so a list derived this way would audit nothing over exactly the rows
    the module exists to find.  The derivation belongs in code; the agreement
    belongs here.
    """

    #: A statement that gives a typed column a value.  TWO SHAPES, because
    #: this repository has used both and the first draft of this card modelled
    #: only the minority one: `009` added `DEFAULT`s (caught by
    #: `PRAGMA table_info` below), while `007` and `008` -- the majority --
    #: wrote `UPDATE characters SET <col> = ... WHERE <col> IS NULL` and left
    #: no DEFAULT behind at all.  A `pf-adversary` pass wrote a
    #: `migrations/010` in `007`/`008`'s shape seeding `mp_current`/`mp_max`
    #: and this card stayed GREEN over two freshly adjudicated columns
    #: holding NULL on disk.
    SET_CLAUSE = re.compile(r"\bSET\s+(.*?)(?:;|\bWHERE\b)", re.S | re.I)
    ASSIGNED = re.compile(r"\b([a-z_]+)\s*=")

    def _columns_a_migration_assigns(self):
        assigned = set()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            # `--` comments stripped: 006's header discusses these columns in
            # prose and a scan that read prose would name all twenty-one.
            body = "\n".join(
                line.split("--")[0]
                for line in path.read_text(encoding="utf-8").splitlines())
            for clause in self.SET_CLAUSE.finditer(body):
                for name in self.ASSIGNED.finditer(clause.group(1)):
                    if name.group(1) in typed.TYPED_COLUMNS:
                        assigned.add(name.group(1))
        return assigned

    def test_a_migration_that_seeds_by_update_is_caught_too(self):
        """The half the first draft did not have.  Any typed column a
        migration ASSIGNS has been adjudicated by somebody, whether or not it
        also got a DEFAULT, and it belongs in the audit."""
        assigned = self._columns_a_migration_assigns()
        self.assertTrue(assigned, "the scan found nothing, so a green result "
                                  "here means the scan is broken")
        self.assertLessEqual(
            assigned, set(audit_module.NULL_AUDIT_COLUMNS),
            "a migration assigns a typed column that NULL_AUDIT_COLUMNS does "
            "not audit (%r).  Somebody adjudicated a value for it, so rows "
            "that predate that migration can hold NULL in it and this count "
            "would not see them."
            % (sorted(assigned - set(audit_module.NULL_AUDIT_COLUMNS)),))

    def test_the_two_arms_together_cover_the_audited_list(self):
        """Neither shape alone is the answer, and the union is: every audited
        column is adjudicated by at least one of them, and nothing they name
        is left out."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            SQLiteStore(path, MIGRATIONS).migrate()
            db = sqlite3.connect(path)
            try:
                defaulted = {
                    str(row[1]) for row in
                    db.execute("PRAGMA table_info(characters)")
                    if row[4] is not None and str(row[1]) in typed.TYPED_COLUMNS
                }
            finally:
                db.close()
        self.assertEqual(
            defaulted | self._columns_a_migration_assigns(),
            set(audit_module.NULL_AUDIT_COLUMNS))

    def test_the_defaulted_typed_columns_are_the_audited_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            SQLiteStore(path, MIGRATIONS).migrate()
            db = sqlite3.connect(path)
            try:
                defaulted = {
                    str(row[1]) for row in
                    db.execute("PRAGMA table_info(characters)")
                    if row[4] is not None and str(row[1]) in typed.TYPED_COLUMNS
                }
            finally:
                db.close()
        self.assertEqual(defaulted, set(audit_module.NULL_AUDIT_COLUMNS))


class _UpgradeWorkspace(unittest.TestCase):
    """A store booted on a PREFIX of the migrations directory, so a row can
    be born under the schema an older database really had.

    ON THE WINDOWS HANDLE TRAP, because every test in this file opens raw
    `sqlite3` connections on a file under a temporary directory -- the exact
    shape that closed `#495` and `#610` with
    `PermissionError [WinError 32]`.  Two things are done about it and
    neither is a promise: every raw connection is closed in a `finally`, and
    the directory is a `with tempfile.TemporaryDirectory() as tmp:` INSIDE
    each test rather than an `addCleanup`, so the unlink happens while the
    test is still the thing being graded.  A leaked handle therefore fails
    the test that leaked it, by the operating system's own refusal, rather
    than surfacing as a teardown error somewhere else.  This lane's
    `NoHandleOutlivesItsTempDirMixin` is deliberately NOT used here: it
    guards a directory torn down in cleanup, which is a shape this file
    does not have.
    """

    def _migrations_up_to(self, tmp, last):
        directory = Path(tmp) / ("m%03d" % last)
        directory.mkdir()
        for source in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(source.name[:3]) <= last:
                shutil.copy2(source, directory / source.name)
        return directory

    def _add_migration(self, directory, version):
        for source in sorted(MIGRATIONS.glob("%03d_*.sql" % version)):
            shutil.copy2(source, directory / source.name)

    def _make_character(self, store, account_id, name, key):
        return store.create_character(
            account_id, name, key, "fingerprint-" + key, _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )


class TheWindowIsRealAndTheAuditSeesItTests(_UpgradeWorkspace):
    """The whole reason the count was ordered."""

    def test_a_character_born_at_008_still_holds_a_null_after_009(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = self._migrations_up_to(tmp, 8)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            account_id = store.ensure_account("audit-window")
            before = self._make_character(store, account_id, "Older", "older")

            # The upgrade the owner's database will take.
            self._add_migration(directory, 9)
            SQLiteStore(path, directory).migrate()
            after = self._make_character(store, account_id, "Newer", "newer")

            db = sqlite3.connect(path)
            try:
                rows = {
                    int(r[0]): r[1] for r in db.execute(
                        "SELECT id, speed_walk FROM characters")
                }
                report = db.execute(audit_module.audit_sql()).fetchone()
                columns = [d[0] for d in db.execute(
                    audit_module.audit_sql()).description]
            finally:
                db.close()

        result = dict(zip(columns, report))
        # The window, stated as the two rows that make it:
        self.assertIsNone(rows[before.id],
                          "the pre-009 row was seeded by something; the "
                          "window this audit counts does not exist as "
                          "described and this file must be rewritten")
        self.assertIsNotNone(rows[after.id],
                             "a character born after 009 did not pick up the "
                             "DEFAULT")
        self.assertEqual(result["speed_walk_null_any"], 1)
        self.assertEqual(result["speed_walk_null_live"], 1)
        self.assertEqual(result["characters_any"], 2)
        # The three vitals are written by `create_character` itself, so they
        # are NOT in the window -- asserted rather than assumed, because if
        # that ever changes the count above is answering a bigger question
        # than this file claims.
        for column in vitals.VITAL_COLUMNS:
            self.assertEqual(result["%s_null_any" % column], 0, column)


class SoftDeletedRowsAreCountedSeparatelyTests(_UpgradeWorkspace):
    """`persistence_vitals.census_sql`'s measured lesson, applied to the
    count that would decide a backfill: a backfill has to touch every row on
    disk, so a decision taken from the live-only number is taken from the
    wrong number."""

    def test_a_deleted_null_row_leaves_live_at_zero_and_any_at_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = self._migrations_up_to(tmp, 8)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            account_id = store.ensure_account("audit-deleted")
            character = self._make_character(
                store, account_id, "Doomed", "doomed")
            self._add_migration(directory, 9)
            SQLiteStore(path, directory).migrate()
            sid = store.open_session(account_id)
            store.soft_delete_character(sid, character.selector)

            db = sqlite3.connect(path)
            try:
                report = db.execute(audit_module.audit_sql()).fetchone()
                columns = [d[0] for d in db.execute(
                    audit_module.audit_sql()).description]
                still_there = db.execute(
                    "SELECT COUNT(*) FROM characters WHERE id=?",
                    (character.id,)).fetchone()[0]
            finally:
                db.close()

        result = dict(zip(columns, report))
        self.assertEqual(still_there, 1, "004 no longer keeps deleted rows; "
                                         "this test's premise is gone")
        self.assertEqual(result["speed_walk_null_any"], 1)
        self.assertEqual(result["speed_walk_null_live"], 0)
        self.assertEqual(result["characters_any"], 1)
        self.assertEqual(result["characters_live"], 0)


class TheReportSaysWhichDatabaseTests(unittest.TestCase):
    def test_the_path_is_the_first_line(self):
        text = audit_module.format_report({"database": "/tmp/x.sqlite3"})
        self.assertTrue(text.splitlines()[0].endswith("/tmp/x.sqlite3"), text)

    def test_every_audited_column_gets_a_line(self):
        text = audit_module.format_report({})
        for column in audit_module.NULL_AUDIT_COLUMNS:
            self.assertIn("NULL_AUDIT %s null_live=" % column, text)


class TheStoreDoorIsTheOneThatGetsRunTests(_UpgradeWorkspace):
    """THE DOOR ITSELF, because nothing else in this file opened it.

    A `pf-adversary` pass deleted `SQLiteStore.typed_column_null_audit`
    entirely and the full suite came back byte-identical -- 8,540 passed,
    same as with it present -- because every other test here drives
    `audit_sql()` through a raw `sqlite3` connection.  Three mutants inside
    the method survived all nine: answering with the vitals census query
    instead, dropping the schema check, and returning zero for every column
    on every database.  That last one is the one that matters: it prints a
    clean sheet on the owner's canonical database, COO reads "no backfill
    needed", and the gate is green.

    So these tests call the method.
    """

    def _built(self, tmp):
        """A database with one pre-009 row, one post-009 row, and one of
        each soft-deleted, so every number in the report is distinct and a
        mutant cannot satisfy them all with one constant."""
        directory = self._migrations_up_to(tmp, 8)
        path = Path(tmp) / "state.sqlite3"
        store = SQLiteStore(path, directory)
        store.migrate()
        account_id = store.ensure_account("audit-door")
        old = self._make_character(store, account_id, "Old", "old")
        doomed = self._make_character(store, account_id, "Doomed", "doomed")
        self._add_migration(directory, 9)
        SQLiteStore(path, directory).migrate()
        self._make_character(store, account_id, "New", "new")
        sid = store.open_session(account_id)
        store.soft_delete_character(sid, doomed.selector)
        return store, path, old

    def test_the_door_answers_the_numbers_the_query_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _ = self._built(tmp)
            audit = store.typed_column_null_audit()
            db = sqlite3.connect(path)
            try:
                raw = db.execute(audit_module.audit_sql()).fetchone()
                keys = [d[0] for d in
                        db.execute(audit_module.audit_sql()).description]
            finally:
                db.close()
        expected = dict(zip(keys, raw))
        for key, value in expected.items():
            self.assertEqual(audit[key], value, key)
        # And the numbers are not all the same, so a constant cannot pass:
        self.assertEqual(audit["characters_any"], 3)
        self.assertEqual(audit["characters_live"], 2)
        self.assertEqual(audit["speed_walk_null_any"], 2)
        self.assertEqual(audit["speed_walk_null_live"], 1)
        self.assertEqual(audit["level_null_any"], 0)

    def test_the_door_names_the_file_it_counted_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _ = self._built(tmp)
            audit = store.typed_column_null_audit()
        self.assertEqual(audit["database"], str(path.resolve()))

    def test_the_door_moves_no_byte_of_the_file(self):
        """The claim this file's header makes, on the shape that breaks it.

        The database is deliberately put back into ROLLBACK JOURNAL mode
        first, because that is where the defect lived: `SQLiteStore.connect`
        runs `PRAGMA journal_mode=WAL` and commits, so the first draft of the
        door -- which used it -- rewrote the header of any non-WAL file it
        counted.  A snapshot kept to prove which file a number came from is
        exactly such a file, and `AGENTS.md` requires its hash not to move.
        """
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _ = self._built(tmp)
            db = sqlite3.connect(path)
            try:
                db.execute("PRAGMA journal_mode=DELETE")
            finally:
                db.close()

            def signature():
                data = path.read_bytes()
                probe = sqlite3.connect(path)
                try:
                    version = probe.execute(
                        "PRAGMA data_version").fetchone()[0]
                finally:
                    probe.close()
                return (hashlib.sha256(data).hexdigest(),
                        data[16:24], path.stat().st_mtime_ns, version)

            before = signature()
            store.typed_column_null_audit()
            store.typed_column_null_audit()
            after = signature()
        self.assertEqual(before, after,
                         "typed_column_null_audit moved the file it was "
                         "counting")

    def test_the_door_refuses_a_database_whose_columns_are_not_there(self):
        """The schema check is not decoration: on a database at `006` the
        four columns exist but `007`/`008`/`009` have not run, and on one
        older still they do not exist at all.  A count over a table that
        cannot answer must say so rather than return zeros."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = self._migrations_up_to(tmp, 5)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            with self.assertRaises(vitals.VitalsError):
                store.typed_column_null_audit()


class AnUncountedZeroIsNotACountedZeroTests(unittest.TestCase):
    """`COO-DECISION 20260901_1059` at the reporting layer.

    `SUM()` over zero rows is SQL NULL.  The first draft of the store door
    coerced every value to an int, which made a database holding NO
    CHARACTERS AT ALL print a report line for line identical to a fully
    seeded one -- the banned guessed zero, in the one method whose output
    goes into a letter to COO.
    """

    def test_an_empty_table_reports_not_counted_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            audit = store.typed_column_null_audit()
        self.assertEqual(audit["characters_any"], 0)
        for column in audit_module.NULL_AUDIT_COLUMNS:
            self.assertIsNone(audit["%s_null_any" % column], column)
            self.assertIsNone(audit["%s_null_live" % column], column)
        text = audit_module.format_report(audit)
        self.assertIn(audit_module.NOT_COUNTED, text)
        self.assertNotIn("null_any=0", text)

    def test_a_counted_zero_still_prints_as_zero(self):
        """The control: `not-counted` may not swallow a real zero."""
        text = audit_module.format_report({
            "database": "/x", "characters_any": 1, "characters_live": 1,
            "level_null_any": 0, "level_null_live": 0,
        })
        self.assertIn("NULL_AUDIT level null_live=0 null_any=0", text)


class ZeroCanMeanTheWindowNeverOpenedTests(_UpgradeWorkspace):
    """!! THE ANSWER IS `0` BY CONSTRUCTION ON THE LIKELIER UPGRADE ORDER,
    and a reader who does not know that reads a clean sheet as evidence.

    A database that meets `008` and `009` in the SAME boot cannot have a row
    in the window at all: no character can be created between two files
    applied by one `migrate()`.  Only a database that ran a live server while
    sitting at `008` can answer anything else.  Both are measured here so the
    distinction is a test rather than a sentence in a docstring.
    """

    def test_both_migrations_in_one_boot_answer_zero_having_had_no_chance(
            self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = self._migrations_up_to(tmp, 7)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            account_id = store.ensure_account("audit-oneboot")
            self._make_character(store, account_id, "Before", "before")
            # 008 and 009 arrive together, which is what a database two
            # migrations behind does on its next boot.
            self._add_migration(directory, 8)
            self._add_migration(directory, 9)
            SQLiteStore(path, directory).migrate()
            audit = store.typed_column_null_audit()
        self.assertEqual(audit["characters_any"], 1)
        self.assertEqual(audit["speed_walk_null_any"], 0)

    def test_a_server_that_ran_at_008_answers_more_than_zero(self):
        """The other order, and the one that makes the count worth taking."""
        with tempfile.TemporaryDirectory() as tmp:
            directory = self._migrations_up_to(tmp, 8)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            account_id = store.ensure_account("audit-lived")
            self._make_character(store, account_id, "During", "during")
            self._add_migration(directory, 9)
            SQLiteStore(path, directory).migrate()
            audit = store.typed_column_null_audit()
        self.assertEqual(audit["speed_walk_null_any"], 1)

if __name__ == "__main__":
    unittest.main()
