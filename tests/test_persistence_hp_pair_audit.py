"""LANE-DB: the read-only count promised in
`pf_bridge/notes_to_chief/20260906_0536_LANE-DB-REPLY-gm0436-hp-pair-rows-
not-a-blocker-for-0156-logged-as-backlog.md`, answering `LANE-GM`'s letter
(`pf_bridge/notes_to_chief/20260906_0436_LANE-GM-TO-LANE-DB-slash-lv-blocked-
by-broken-hp-pair-rows.md`): how many rows hold one of the three HP-pair
conditions GM measured `persistence_login_vitals.resolve()` refusing --
`hp_max IS NULL`, `hp_current > hp_max`, `hp_max = 0`.

WHAT THIS FILE PROVES (wire/DB layer only):

1. **Each of the three conditions is really reachable on this schema.**
   `migrations/006`'s own `CHECK` constraints allow `hp_max = 0` and put no
   cross-column rule between `hp_current` and `hp_max` at all -- so a caller
   that writes one column without reading the other, exactly the shape GM's
   letter warns about, is not stopped by SQLite either.
2. **The three counts are not folded into one number**, because a row can
   satisfy more than one condition at once.
3. **Soft-deleted rows are counted separately, not dropped** -- the mistake
   `persistence_null_audit`'s own header names.
4. **It writes nothing.**
5. **The store door is exercised**, not only the raw SQL underneath it.
6. **A count that could not be taken says so** (`None`, not `0`).

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable.  Nothing
here says what should be done about a nonzero count, and nothing here has
run against the owner's canonical database -- that number is COO's to ask
for and this lane's to produce when asked.
"""
import ast
import hashlib
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_hp_pair_audit as audit_module  # noqa: E402,E501
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _Workspace(unittest.TestCase):
    """A store migrated to HEAD, with a helper that makes a character and
    then forces its HP pair into a named broken shape through the same door
    (`write_typed_attributes`) a real caller who ignores the other half of
    the pair would use -- not raw SQL, so this file measures the same gap
    the letter measured rather than a hand-built row nothing in this server
    could produce.

    ON THE WINDOWS HANDLE TRAP: every raw `sqlite3` connection this file
    opens is closed in a `finally`, and the temp directory is a
    `with tempfile.TemporaryDirectory()` inside each test rather than
    `addCleanup`, matching `tests/test_persistence_null_audit.py`.
    """

    def _make_character(self, store, account_id, name, key):
        return store.create_character(
            account_id, name, key, "fingerprint-" + key, _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )

    def _break(self, store, character_id, **columns):
        store.write_typed_attributes(character_id, columns)


class EachConditionIsReallyReachableTests(_Workspace):
    """The premise the module's header states: nothing in this schema stops
    any of the three shapes."""

    def test_hp_max_null_survives_the_column_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("reach-null")
            character = self._make_character(store, account_id, "A", "a")
            db = sqlite3.connect(path)
            try:
                db.execute(
                    "UPDATE characters SET hp_max = NULL WHERE id = ?",
                    (character.id,))
                db.commit()
            finally:
                db.close()
        # No exception raised: the CHECK on hp_max explicitly allows NULL.

    def test_hp_current_above_hp_max_survives_write_typed_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("reach-above")
            character = self._make_character(store, account_id, "B", "b")
            self._break(store, character.id, hp_current=999, hp_max=50)
            row = store.read_typed_attributes(character.id)
        self.assertEqual(row["hp_current"], 999)
        self.assertEqual(row["hp_max"], 50)

    def test_hp_max_zero_survives_write_typed_attributes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("reach-zero")
            character = self._make_character(store, account_id, "C", "c")
            self._break(store, character.id, hp_max=0)
            row = store.read_typed_attributes(character.id)
        self.assertEqual(row["hp_max"], 0)


class TheLoginGateReallyRefusesAllThreeTests(_Workspace):
    """The reason the count matters, tied to the module this audit is about
    rather than asserted in prose: each of the three broken shapes really
    does turn `persistence_vitals.resolve()` into a gap the login gate
    reports, matching what GM's letter and `persistence_login_vitals`'s own
    header describe."""

    def test_hp_max_null_is_a_gap(self):
        resolution = vitals.resolve({"level": 5, "hp_current": 10})
        self.assertTrue(resolution.gaps)

    def test_hp_current_above_hp_max_is_a_gap(self):
        resolution = vitals.resolve(
            {"level": 5, "hp_current": 999, "hp_max": 50})
        self.assertTrue(any(
            g.reason == vitals.REASON_HP_ABOVE_MAX for g in resolution.gaps))

    def test_hp_max_zero_is_a_gap(self):
        resolution = vitals.resolve(
            {"level": 5, "hp_current": 0, "hp_max": 0})
        self.assertTrue(any(
            g.reason == vitals.REASON_HP_MAX_ZERO for g in resolution.gaps))


class NothingInTheModuleCanWriteTests(unittest.TestCase):
    def test_only_select_statements_appear(self):
        source = (ROOT / "src" / "pirateforce_foundation"
                  / "persistence_hp_pair_audit.py").read_text(
                      encoding="utf-8")
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
        self.assertIn("SELECT ", executable)


class TheThreeCountsAreNotFoldedIntoOneNumberTests(_Workspace):
    """A row can satisfy more than one condition; the module reports them
    side by side rather than deduplicating."""

    def test_a_row_that_is_both_zero_max_and_above_max_counts_in_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("double")
            character = self._make_character(store, account_id, "D", "d")
            # hp_max = 0 AND hp_current (1) above it: both conditions at once.
            self._break(store, character.id, hp_current=1, hp_max=0)
            audit = store.hp_pair_audit()
        self.assertEqual(audit[audit_module.HP_MAX_ZERO + "_any"], 1)
        self.assertEqual(audit[audit_module.HP_CURRENT_ABOVE_MAX + "_any"], 1)


class SoftDeletedRowsAreCountedSeparatelyTests(_Workspace):
    def test_a_deleted_broken_row_leaves_live_at_zero_and_any_at_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("deleted")
            character = self._make_character(store, account_id, "E", "e")
            self._break(store, character.id, hp_max=0)
            sid = store.open_session(account_id)
            store.soft_delete_character(sid, character.selector)
            audit = store.hp_pair_audit()
        self.assertEqual(audit[audit_module.HP_MAX_ZERO + "_any"], 1)
        self.assertEqual(audit[audit_module.HP_MAX_ZERO + "_live"], 0)


class TheStoreDoorIsTheOneThatGetsRunTests(_Workspace):
    """A `pf-adversary` pass against `persistence_null_audit` measured what
    happens when nothing calls the store method: mutants that answer zero
    for every column, or the wrong query, survived. These tests call
    `store.hp_pair_audit()` itself rather than only the raw SQL."""

    def _built(self, tmp):
        """`broken` is left `hp_max = 0` and its BIRTH `hp_current` (100) is
        also above that zero, so it counts under both `HP_MAX_ZERO` and
        `HP_CURRENT_ABOVE_MAX` -- consistent with
        `TheThreeCountsAreNotFoldedIntoOneNumberTests`, not a second
        coincidence."""
        path = Path(tmp) / "state.sqlite3"
        store = SQLiteStore(path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("door")
        clean = self._make_character(store, account_id, "Clean", "clean")
        broken = self._make_character(store, account_id, "Broken", "broken")
        self._break(store, broken.id, hp_max=0)
        doomed = self._make_character(store, account_id, "Doomed", "doomed")
        self._break(store, doomed.id, hp_current=500, hp_max=10)
        sid = store.open_session(account_id)
        store.soft_delete_character(sid, doomed.selector)
        return store, path, clean

    def test_the_door_answers_the_numbers_the_query_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _ = self._built(tmp)
            audit = store.hp_pair_audit()
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
        self.assertEqual(audit["characters_any"], 3)
        self.assertEqual(audit["characters_live"], 2)
        self.assertEqual(audit[audit_module.HP_MAX_ZERO + "_any"], 1)
        self.assertEqual(audit[audit_module.HP_MAX_ZERO + "_live"], 1)
        # `broken` (live, hp_current=100 > hp_max=0) and `doomed` (deleted,
        # 500 > 10): two rows `_any`, one of them still live.
        self.assertEqual(
            audit[audit_module.HP_CURRENT_ABOVE_MAX + "_any"], 2)
        self.assertEqual(
            audit[audit_module.HP_CURRENT_ABOVE_MAX + "_live"], 1)
        self.assertEqual(audit[audit_module.HP_MAX_NULL + "_any"], 0)

    def test_the_door_names_the_file_it_counted_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _ = self._built(tmp)
            audit = store.hp_pair_audit()
        self.assertEqual(audit["database"], str(path.resolve()))

    def test_the_door_moves_no_byte_of_the_file(self):
        """Same claim, same shape of proof, as
        `test_persistence_null_audit.py`'s
        `TheStoreDoorIsTheOneThatGetsRunTests.
        test_the_door_moves_no_byte_of_the_file`: the database is put back
        into ROLLBACK JOURNAL mode first, because `connect()`'s
        `PRAGMA journal_mode=WAL` is what moved bytes in the first draft of
        that door."""
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
            store.hp_pair_audit()
            store.hp_pair_audit()
            after = signature()
        self.assertEqual(before, after,
                         "hp_pair_audit moved the file it was counting")

    def test_the_door_refuses_a_database_whose_columns_are_not_there(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "old-schema"
            directory.mkdir()
            import shutil
            for source in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
                if int(source.name[:3]) <= 5:
                    shutil.copy2(source, directory / source.name)
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, directory)
            store.migrate()
            with self.assertRaises(vitals.VitalsError):
                store.hp_pair_audit()


class AnUncountedZeroIsNotACountedZeroTests(_Workspace):
    def test_an_empty_table_reports_not_counted_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            audit = store.hp_pair_audit()
        self.assertEqual(audit["characters_any"], 0)
        for name in audit_module.CONDITIONS:
            self.assertIsNone(audit["%s_any" % name], name)
            self.assertIsNone(audit["%s_live" % name], name)
        text = audit_module.format_report(audit)
        self.assertIn(audit_module.NOT_COUNTED, text)
        self.assertNotIn("_any=0", text)

    def test_a_counted_zero_still_prints_as_zero(self):
        text = audit_module.format_report({
            "database": "/x", "characters_any": 1, "characters_live": 1,
            "hp_max_is_zero_any": 0, "hp_max_is_zero_live": 0,
        })
        self.assertIn("HP_PAIR_AUDIT hp_max_is_zero live=0 any=0", text)


class TheReportSaysWhichDatabaseTests(unittest.TestCase):
    def test_the_path_is_the_first_line(self):
        text = audit_module.format_report({"database": "/tmp/x.sqlite3"})
        self.assertTrue(text.splitlines()[0].endswith("/tmp/x.sqlite3"), text)

    def test_every_condition_gets_a_line(self):
        text = audit_module.format_report({})
        for name in audit_module.CONDITIONS:
            self.assertIn("HP_PAIR_AUDIT %s live=" % name, text)


if __name__ == "__main__":
    unittest.main()
