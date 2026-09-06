"""LANE-DB: the read-only, two-group count promised as backlog item 2 of
this lane's own round `64da3x`
(`pf_bridge/rounds/DB_20260905_1739_64da3x_skill_points_store_doors.md`):
how many rows hold NULL in `skill_points` (which has real store doors and
CS-side consumers as of that round) versus `unspent_points` (schema only,
no caller anywhere), reported as two separate groups rather than folded into
`persistence_null_audit`'s existing list -- which is scoped to columns with
an adjudicated birth `DEFAULT`, and neither of these two has one.

WHAT THIS FILE PROVES (wire/DB layer only):

1. **The two constants really name the group `persistence_attr_compose`
   agrees they belong to** -- `SERVER_OWNED_FIELDS[16].column` for wired,
   `SERVER_OWNED_FIELDS[17].column` for unwired -- not two hand-typed
   strings that could drift from that table.
2. **The grouping matches what is actually in `src/` today**: `skill_points`
   has a consumer beyond the wire table and the compose gate;
   `unspent_points` does not.  Grepped at test time, not asserted in prose.
3. **The two counts are not folded into one number.**
4. **Soft-deleted rows are counted separately, not dropped.**
5. **It writes nothing.**
6. **The store door is exercised**, not only the raw SQL underneath it.
7. **A count that could not be taken says so** (`None`/`not-counted`, not
   `0`).

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable.  Nothing
here says either column should get a birth default, and nothing here has
run against the owner's canonical database.
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

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402,E501
from pirateforce_foundation import persistence_skill_points_null_audit as audit_module  # noqa: E402,E501
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
SRC = ROOT / "src" / "pirateforce_foundation"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _Workspace(unittest.TestCase):
    """A store migrated to HEAD.  Matches
    `tests/test_persistence_hp_pair_audit.py`'s `_Workspace`: every raw
    `sqlite3` connection is closed in a `finally`, and the temp directory is
    a `with tempfile.TemporaryDirectory()` inside each test."""

    def _make_character(self, store, account_id, name, key):
        return store.create_character(
            account_id, name, key, "fingerprint-" + key, _build_wire,
            Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        )

    def _set(self, store, character_id, **columns):
        store.write_typed_attributes(character_id, columns)


class TheGroupingAgreesWithTheComposeGateTests(unittest.TestCase):
    def test_wired_column_is_x16_per_the_compose_gate(self):
        self.assertEqual(
            audit_module.WIRED_COLUMN,
            compose.SERVER_OWNED_FIELDS[audit_module.SKILL_POINTS_X].column,
        )

    def test_unwired_column_is_x17_per_the_compose_gate(self):
        self.assertEqual(
            audit_module.UNWIRED_COLUMN,
            compose.SERVER_OWNED_FIELDS[audit_module.UNSPENT_POINTS_X].column,
        )

    def test_the_two_columns_are_not_the_same(self):
        self.assertNotEqual(audit_module.WIRED_COLUMN,
                             audit_module.UNWIRED_COLUMN)


class TheGroupingMatchesLiveCodeTests(unittest.TestCase):
    """Measured, not asserted: `skill_points` has a consumer beyond the wire
    table and this compose gate; `unspent_points` does not.  If a later
    round wires a caller for `unspent_points`, this test goes red until the
    column is moved from `UNWIRED_COLUMNS` to `WIRED_COLUMNS` -- the module
    header's own instruction."""

    #: Files that spell a column's name WITHOUT being a consumer of it: the
    #: wire field table, the compose gate's own partition, the store door
    #: itself, and this module.  `stats_progression_hypothesis.py` belongs
    #: here for the same reason `gm/attr_wire.py` does and was missing until
    #: pf-adversary (round `auo3bj`, D2) measured that its single match is
    #: one `AttrField("skill_points", ...)` row -- a wire-layer table, not a
    #: caller.  Spelled with forward slashes; `_files_naming` normalises.
    _CONSUMER_ALLOWED_FILES = {
        "gm/attr_wire.py",
        "persistence_attr_compose.py",
        "persistence_skill_points_null_audit.py",
        "stats_progression_hypothesis.py",
        "store.py",
    }

    #: The two store doors that actually read or spend the balance.  The
    #: WIRED claim is asserted against a CALL to one of these, never against
    #: the substring `skill_points` -- pf-adversary (round `auo3bj`, D2)
    #: measured that the substring form stayed green with every real
    #: consumer deleted, because a wire-field-table row satisfied it.
    _STORE_DOORS = ("get_skill_points(", "spend_skill_points(")

    def _files_naming(self, needle):
        hits = []
        for path in SRC.rglob("*.py"):
            # `.as_posix()`, never `str()`: `str(WindowsPath("gm/attr_wire
            # .py"))` is `'gm\\attr_wire.py'` on the gate runner, which
            # would never match the forward-slash literals above -- the
            # exact separator bug that already cost this diff one closure
            # (`#949`) in a different helper, measured again here by
            # pf-adversary (round `auo3bj`, D1) before it could cost a
            # fourth.  Four sibling LANE-DB guards normalise the same way
            # (`test_persistence_vitals.py:915`, `:1552`,
            # `test_persistence_vitals_heal.py:1199`,
            # `test_persistence_speed_walk_seed_008.py:713`).
            rel = path.relative_to(SRC).as_posix()
            if needle in path.read_text(encoding="utf-8"):
                hits.append(rel)
        return hits

    def _files_calling_a_store_door(self):
        """Files holding a real CALL to one of `_STORE_DOORS`, excluding the
        door's own definition in `store.py`.

        A line carrying a backtick is prose, not code: the house convention
        spells code references inside backticks in docstrings, so
        `skill_learn_wiring.py`'s two narrative mentions (lines 50 and 73)
        are excluded while its two real call sites (lines 85 and 96) are
        not.  Measured on this tree, not assumed.
        """
        hits = []
        for path in SRC.rglob("*.py"):
            rel = path.relative_to(SRC).as_posix()
            if rel == "store.py":
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                if "`" in line or line.lstrip().startswith("#"):
                    continue
                if any(door in line for door in self._STORE_DOORS):
                    hits.append(rel)
                    break
        return hits

    def test_skill_points_has_a_consumer_beyond_the_wire_table_and_the_gate(
            self):
        callers = self._files_calling_a_store_door()
        self.assertTrue(
            callers,
            "skill_points is grouped WIRED, but no file under src/ actually "
            "CALLS store.get_skill_points()/spend_skill_points() -- if the "
            "last caller has gone, move the column to UNWIRED_COLUMNS "
            "rather than deleting this test. Files merely naming the "
            "column: %r" % (self._files_naming("skill_points"),))

    def test_unspent_points_has_no_consumer_beyond_the_wire_table_and_the_gate(
            self):
        hits = self._files_naming("unspent_points")
        extra = [f for f in hits if f not in self._CONSUMER_ALLOWED_FILES]
        self.assertFalse(
            extra,
            "unspent_points has grown a consumer -- move it to "
            "WIRED_COLUMNS: %r" % extra)


class NothingInTheModuleCanWriteTests(unittest.TestCase):
    def test_only_select_statements_appear(self):
        source = (SRC / "persistence_skill_points_null_audit.py").read_text(
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


class TheTwoCountsAreNotFoldedIntoOneNumberTests(_Workspace):
    def test_a_row_null_in_one_and_set_in_the_other_counts_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("split")
            character = self._make_character(store, account_id, "A", "a")
            self._set(store, character.id, skill_points=3)
            audit = store.skill_points_null_audit()
        self.assertEqual(audit[audit_module.WIRED_COLUMN + "_null_any"], 0)
        self.assertEqual(audit[audit_module.UNWIRED_COLUMN + "_null_any"], 1)


class SoftDeletedRowsAreCountedSeparatelyTests(_Workspace):
    def test_a_deleted_null_row_leaves_live_at_zero_and_any_at_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            account_id = store.ensure_account("deleted")
            character = self._make_character(store, account_id, "B", "b")
            sid = store.open_session(account_id)
            store.soft_delete_character(sid, character.selector)
            audit = store.skill_points_null_audit()
        self.assertEqual(audit[audit_module.WIRED_COLUMN + "_null_any"], 1)
        self.assertEqual(audit[audit_module.WIRED_COLUMN + "_null_live"], 0)


class TheStoreDoorIsTheOneThatGetsRunTests(_Workspace):
    """A `pf-adversary` pass against `persistence_null_audit` measured what
    happens when nothing calls the store method: mutants that answer zero
    for every column, or the wrong query, survived.  These tests call
    `store.skill_points_null_audit()` itself rather than only the raw SQL."""

    def _built(self, tmp):
        path = Path(tmp) / "state.sqlite3"
        store = SQLiteStore(path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("door")
        set_one = self._make_character(store, account_id, "Set", "set")
        self._set(store, set_one.id, skill_points=5, unspent_points=2)
        null_one = self._make_character(store, account_id, "Null", "null")
        doomed = self._make_character(store, account_id, "Doomed", "doomed")
        sid = store.open_session(account_id)
        store.soft_delete_character(sid, doomed.selector)
        return store, path, set_one, null_one

    def test_the_door_answers_the_numbers_the_query_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _, _ = self._built(tmp)
            audit = store.skill_points_null_audit()
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
        # set_one has both columns set; null_one and doomed hold NULL in
        # both -> two `_any`, one still live (null_one).
        self.assertEqual(audit[audit_module.WIRED_COLUMN + "_null_any"], 2)
        self.assertEqual(audit[audit_module.WIRED_COLUMN + "_null_live"], 1)
        self.assertEqual(audit[audit_module.UNWIRED_COLUMN + "_null_any"], 2)
        self.assertEqual(audit[audit_module.UNWIRED_COLUMN + "_null_live"], 1)

    def test_the_door_names_the_file_it_counted_resolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _, _ = self._built(tmp)
            audit = store.skill_points_null_audit()
        self.assertEqual(audit["database"], str(path.resolve()))

    def test_the_door_moves_no_byte_of_the_file(self):
        """Same claim, same shape of proof, as
        `test_persistence_hp_pair_audit.py`'s
        `TheStoreDoorIsTheOneThatGetsRunTests.
        test_the_door_moves_no_byte_of_the_file`."""
        with tempfile.TemporaryDirectory() as tmp:
            store, path, _, _ = self._built(tmp)
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
            store.skill_points_null_audit()
            store.skill_points_null_audit()
            after = signature()
        self.assertEqual(
            before, after,
            "skill_points_null_audit moved the file it was counting")

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
                store.skill_points_null_audit()


class AnUncountedZeroIsNotACountedZeroTests(_Workspace):
    def test_an_empty_table_reports_not_counted_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.sqlite3"
            store = SQLiteStore(path, MIGRATIONS)
            store.migrate()
            audit = store.skill_points_null_audit()
        self.assertEqual(audit["characters_any"], 0)
        for column in audit_module.ALL_COLUMNS:
            self.assertIsNone(audit["%s_null_any" % column], column)
            self.assertIsNone(audit["%s_null_live" % column], column)
        text = audit_module.format_report(audit)
        self.assertIn(audit_module.NOT_COUNTED, text)
        self.assertNotIn("null_any=0", text)

    def test_a_counted_zero_still_prints_as_zero(self):
        text = audit_module.format_report({
            "database": "/x", "characters_any": 1, "characters_live": 1,
            "skill_points_null_any": 0, "skill_points_null_live": 0,
        })
        self.assertIn(
            "SKILL_POINTS_AUDIT wired skill_points null_live=0 null_any=0",
            text)


class TheReportSaysWhichDatabaseAndGroupTests(unittest.TestCase):
    def test_the_path_is_the_first_line(self):
        text = audit_module.format_report({"database": "/tmp/x.sqlite3"})
        self.assertTrue(text.splitlines()[0].endswith("/tmp/x.sqlite3"), text)

    def test_the_wired_column_line_says_wired(self):
        text = audit_module.format_report({})
        self.assertIn(
            "SKILL_POINTS_AUDIT wired %s null_live=" %
            audit_module.WIRED_COLUMN, text)

    def test_the_unwired_column_line_says_unwired(self):
        text = audit_module.format_report({})
        self.assertIn(
            "SKILL_POINTS_AUDIT unwired %s null_live=" %
            audit_module.UNWIRED_COLUMN, text)


if __name__ == "__main__":
    unittest.main()
