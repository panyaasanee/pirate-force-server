"""LANE-DB / M4: the typed attribute columns exist, hold only encodable
values, and an unset one is ABSENT rather than zero.

WHAT THIS FILE IS THE EVIDENCE FOR.  Until this round the twenty-two
server-owned attribute fields had exactly one column between them
(``characters.name``); ``persistence_attr_compose.unlock_report()`` reported
twenty-one of them as ``server_owned_column_not_built``, which is why
``/speed`` had nowhere to remember a speed.
``migrations/006_character_typed_attribute_columns.sql`` builds those
twenty-one columns and this file proves three things about them, in order of
how much they matter:

1. **The migration cannot have destroyed anything.**  It is parsed statement
   by statement (nothing but ``ALTER TABLE ... ADD COLUMN``), and then run for
   real against a database that already holds a character, a position and a
   backpack -- every pre-existing value is compared byte for byte afterwards.
   This matters because no boot path calls ``SQLiteStore.migrate_with_backup``
   yet (``CORE-REQUEST-DB-001``, open), so on the owner's canonical database
   this file's migration runs unprotected.  "It only adds columns" is the
   whole safety argument, so it is the thing measured hardest here.
2. **An unset column is absent, not zero.**  The owner's rule
   (``COO-DECISION 20260901_1059``) is that a guessed zero must never reach a
   block.  A read that turned NULL into ``0`` would defeat
   ``persistence_attr_compose`` one layer below it, silently.
3. **A value that could not survive the wire encoder cannot be stored.**
   Twice: refused in python by ``persistence_typed_attrs.validate`` before any
   SQL runs, and refused again by the column's own SQL CHECK for a writer that
   does not come through this API.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable.  No frame
is composed, nothing is sent, and no call site anywhere calls either new store
method -- ``/speed`` still cannot be typed into the game.  Nothing seeds these
columns either: after 006 every one of them is NULL on every existing
character, which is deliberate (seeding is a write on live rows and waits for
the backup-on-boot wiring), so a full attribute block still cannot compose.
The last test in this file asserts that refusal rather than hiding it.
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

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation.gm.attr_wire import BY_X  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MIGRATION_006 = MIGRATIONS / typed.MIGRATION_FILE

#: Columns `characters` had before 006, from 004's rebuild of the table.
COLUMNS_BEFORE_006 = (
    "id", "account_id", "selector", "name", "actor_wire", "avatar_wire",
    "avatar_typed_json", "identity_lo", "identity_hi", "created_at",
    "updated_at", "deleted_at", "name_key", "create_fingerprint",
)


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


def _statements(sql: str) -> list[str]:
    """The migration's real statements, with `--` comment lines removed."""
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


class MigrationShapeTests(unittest.TestCase):
    """The migration adds columns and does nothing else -- parsed, not assumed."""

    def setUp(self):
        self.sql = MIGRATION_006.read_text(encoding="utf-8")
        self.statements = _statements(self.sql)

    def test_every_statement_is_an_add_column_on_characters(self):
        self.assertEqual(len(self.statements), len(typed.TYPED_COLUMNS))
        for statement in self.statements:
            with self.subTest(statement=statement[:60]):
                self.assertRegex(
                    statement, r"^ALTER TABLE characters ADD COLUMN [a-z][a-z0-9_]*\b"
                )

    def test_the_migration_contains_no_row_touching_verb(self):
        """The owner's rule 1112 point 3 in one assertion.

        A backfill, an UPDATE or a table rebuild in this file would need the
        pre-apply snapshot that no boot path takes yet.  Checked over the
        statements rather than the raw text so the explanatory comment above
        (which names UPDATE and DROP in prose) cannot make this test pass or
        fail for the wrong reason.
        """
        for verb in ("UPDATE", "DELETE", "INSERT", "DROP", "CREATE", "REPLACE",
                     "RENAME", "PRAGMA", "COMMIT", "BEGIN"):
            for statement in self.statements:
                with self.subTest(verb=verb):
                    self.assertNotRegex(statement, rf"\b{verb}\b")

    def test_the_columns_the_migration_declares_are_exactly_the_module_s(self):
        declared = [
            re.match(r"^ALTER TABLE characters ADD COLUMN ([a-z][a-z0-9_]*)", s).group(1)
            for s in self.statements
        ]
        self.assertEqual(declared, list(typed.TYPED_COLUMNS))

    def test_each_column_declares_the_sql_type_and_range_of_its_wire_kind(self):
        for statement in self.statements:
            column = re.match(
                r"^ALTER TABLE characters ADD COLUMN ([a-z][a-z0-9_]*) (INTEGER|REAL)",
                statement,
            )
            self.assertIsNotNone(statement)
            name, sql_type = column.group(1), column.group(2)
            spec = typed.TYPED_COLUMNS[name]
            with self.subTest(column=name):
                self.assertEqual(sql_type, spec.sql_type)
                self.assertIn(f"{name} IS NULL", statement)
                self.assertIn(f"typeof({name})=", statement)
                # python renders a float exponent as `e+38`, SQL as `e38`
                for bound in (spec.minimum, spec.maximum):
                    self.assertIn(str(bound).replace("e+", "e"), statement)

    def test_no_column_is_declared_not_null_or_with_a_default(self):
        # A NOT NULL column needs a constant default, and on a live character
        # that constant is a server invention that reads back exactly like a
        # measured value.  NULL cannot be mistaken for one.
        for statement in self.statements:
            with self.subTest(statement=statement[:60]):
                self.assertNotRegex(statement, r"\bNOT NULL\b")
                self.assertNotRegex(statement, r"\bDEFAULT\b")


class TypedColumnTableTests(unittest.TestCase):
    def test_every_column_serves_the_wire_kind_its_field_declares(self):
        for column, spec in typed.TYPED_COLUMNS.items():
            with self.subTest(column=column):
                self.assertEqual(spec.kind, BY_X[spec.x][5])
                self.assertEqual(
                    (spec.sql_type, spec.minimum, spec.maximum),
                    typed.KIND_STORAGE[spec.kind],
                )

    def test_the_table_is_the_server_owned_set_minus_the_name(self):
        self.assertEqual(
            set(typed.COLUMN_FOR_X) | typed.NOT_A_TYPED_ATTRIBUTE_COLUMN,
            set(compose.SERVER_OWNED_FIELDS),
        )
        self.assertEqual(len(typed.TYPED_COLUMNS), 21)
        for x, column in typed.COLUMN_FOR_X.items():
            self.assertEqual(compose.SERVER_OWNED_FIELDS[x].column, column)

    def test_the_name_column_is_not_reachable_through_this_api(self):
        # x=1 is server-owned, but a rename carries uniqueness rules that
        # `create_character` owns; a field poke must not be able to do it.
        self.assertEqual(compose.SERVER_OWNED_FIELDS[1].column, "name")
        self.assertNotIn("name", typed.TYPED_COLUMNS)
        with self.assertRaises(typed.TypedAttrError):
            typed.column_for(1)

    def test_the_u64_narrowing_is_stated_not_silent(self):
        # SQLite's INTEGER is signed 64-bit: the top half of a u64 has nowhere
        # to go.  Pinned so it cannot become a silent truncation later.
        self.assertEqual(typed.KIND_STORAGE["u64"][2], 2**63 - 1)
        for column in ("experience", "cash"):
            self.assertEqual(typed.TYPED_COLUMNS[column].kind, "u64")
            self.assertEqual(typed.TYPED_COLUMNS[column].maximum, 2**63 - 1)


class ValidationTests(unittest.TestCase):
    def test_a_value_in_range_comes_back_as_it_will_be_stored(self):
        self.assertEqual(typed.validate("level", 40), 40)
        self.assertEqual(typed.validate("speed_walk", 400.0), 400.0)
        self.assertIsInstance(typed.validate("speed_walk", 400), float)

    def test_an_unknown_column_is_refused_by_name(self):
        for bad in ("deleted_at", "name", "id", "speed", "level; DROP TABLE"):
            with self.subTest(column=bad):
                with self.assertRaises(typed.TypedAttrError):
                    typed.validate(bad, 1)

    def test_none_is_refused_rather_than_written_as_null(self):
        with self.assertRaises(typed.TypedAttrError):
            typed.validate("level", None)

    def test_a_bool_is_refused_because_python_would_store_it_as_a_number(self):
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaises(typed.TypedAttrError):
                    typed.validate("level", value)

    def test_a_float_is_refused_for_an_integer_field(self):
        with self.assertRaises(typed.TypedAttrError):
            typed.validate("level", 40.0)

    def test_a_string_is_refused_everywhere(self):
        for column in ("level", "speed_walk"):
            with self.subTest(column=column):
                with self.assertRaises(typed.TypedAttrError):
                    typed.validate(column, "40")

    def test_a_non_finite_speed_is_refused(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(typed.TypedAttrError):
                    typed.validate("speed_walk", value)

    def test_every_column_refuses_just_outside_its_wire_range(self):
        for column, spec in typed.TYPED_COLUMNS.items():
            with self.subTest(column=column):
                if spec.sql_type == "INTEGER":
                    self.assertEqual(typed.validate(column, spec.maximum), spec.maximum)
                    for bad in (spec.minimum - 1, spec.maximum + 1):
                        with self.assertRaises(typed.TypedAttrError):
                            typed.validate(column, bad)
                else:
                    self.assertEqual(typed.validate(column, spec.maximum), spec.maximum)
                    for bad in (spec.minimum * 1.0001, spec.maximum * 1.0001):
                        with self.assertRaises(typed.TypedAttrError):
                            typed.validate(column, bad)

    def test_an_empty_write_is_refused_rather_than_reported_as_done(self):
        with self.assertRaises(typed.TypedAttrError):
            typed.validate_all({})


class MigrationIsNonDestructiveTests(unittest.TestCase):
    """Run 001..005, put real rows in, THEN run 006, and compare everything."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_005"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if path.name != MIGRATION_006.name:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state.sqlite3"

    def _dump(self, table):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()

    def test_existing_rows_survive_006_unchanged_and_the_new_columns_are_null(self):
        old_store = SQLiteStore(self.path, self.older)
        old_store.migrate()
        account_id = old_store.ensure_account("typed-attr-006")
        home = Position(3, 0, 11.0, 22.0, 33.0, heading=1.5)
        old_store.create_character(
            account_id, "TypedAttrOne", "typedattrone",
            "fingerprint-typed-attr-006", _build_wire, home,
        )
        before = {t: self._dump(t) for t in
                  ("characters", "character_positions", "character_backpacks")}
        self.assertEqual(len(before["characters"]), 1)
        for column in COLUMNS_BEFORE_006:
            self.assertIn(column, before["characters"][0])

        SQLiteStore(self.path, MIGRATIONS).migrate()

        after = {t: self._dump(t) for t in before}
        for table in ("character_positions", "character_backpacks"):
            self.assertEqual(after[table], before[table], table)
        self.assertEqual(len(after["characters"]), 1)
        row = after["characters"][0]
        for column in COLUMNS_BEFORE_006:
            self.assertEqual(row[column], before["characters"][0][column], column)
        for column in typed.TYPED_COLUMNS:
            self.assertIsNone(row[column], f"006 seeded {column}; it must not")

    def test_006_is_recorded_in_the_ledger_and_re_running_is_a_no_op(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        db = sqlite3.connect(self.path)
        try:
            applied = {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()
        self.assertIn(6, applied)
        SQLiteStore(self.path, MIGRATIONS).migrate()  # checksum ledger, not a re-apply
        columns = self._character_columns()
        self.assertEqual(
            sum(1 for c in typed.TYPED_COLUMNS if c in columns),
            len(typed.TYPED_COLUMNS),
        )

    def _character_columns(self):
        db = sqlite3.connect(self.path)
        try:
            return {r[1] for r in db.execute("PRAGMA table_info(characters)")}
        finally:
            db.close()


class StoreRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("typed-attr-store")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "TypedAttrStore", "typedattrstore",
            "fingerprint-typed-attr-store", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    def test_a_fresh_character_has_no_typed_values_at_all(self):
        # NOT `{column: 0 for ...}`: the whole rule in one assertion.
        self.assertEqual(self.store.read_typed_attributes(self.character.id), {})

    def test_a_written_value_survives_a_reopen_of_the_database(self):
        self.store.write_typed_attributes(self.character.id, {"speed_walk": 800.0})
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.read_typed_attributes(self.character.id), {"speed_walk": 800.0}
        )

    def test_writing_one_column_leaves_the_others_absent_not_zero(self):
        self.store.write_typed_attributes(self.character.id, {"level": 12})
        state = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(state, {"level": 12})
        self.assertNotIn("hp_current", state)

    def test_a_second_write_updates_rather_than_duplicates(self):
        self.store.write_typed_attributes(self.character.id, {"speed_walk": 400.0})
        after = self.store.write_typed_attributes(
            self.character.id, {"speed_walk": 250.0, "level": 3}
        )
        self.assertEqual(after, {"level": 3, "speed_walk": 250.0})

    def test_the_write_returns_the_whole_state_not_only_what_it_wrote(self):
        self.store.write_typed_attributes(self.character.id, {"level": 5})
        after = self.store.write_typed_attributes(self.character.id, {"cash": 900})
        self.assertEqual(after, {"level": 5, "cash": 900})

    def test_a_refused_value_writes_nothing_at_all(self):
        self.store.write_typed_attributes(self.character.id, {"level": 7})
        with self.assertRaises(typed.TypedAttrError):
            self.store.write_typed_attributes(
                self.character.id, {"speed_walk": 500.0, "level": 999999}
            )
        # the good half of the refused batch must not have landed either
        self.assertEqual(self.store.read_typed_attributes(self.character.id), {"level": 7})

    def test_an_unknown_character_is_a_key_error_on_both_sides(self):
        with self.assertRaises(KeyError):
            self.store.read_typed_attributes(999999)
        with self.assertRaises(KeyError):
            self.store.write_typed_attributes(999999, {"level": 1})

    def test_a_soft_deleted_character_is_invisible_to_both_sides(self):
        second = self.store.create_character(
            self.account_id, "TypedAttrTwo", "typedattrtwo",
            "fingerprint-typed-attr-store-2", _build_wire, self.home,
        )
        self.store.write_typed_attributes(second.id, {"level": 9})
        self.store.soft_delete_character(self.sid, second.selector)
        with self.assertRaises(KeyError):
            self.store.read_typed_attributes(second.id)
        with self.assertRaises(KeyError):
            self.store.write_typed_attributes(second.id, {"level": 10})

    def test_the_write_moves_updated_at(self):
        before = self._raw_value("updated_at")
        self.store.write_typed_attributes(self.character.id, {"level": 2})
        self.assertNotEqual(self._raw_value("updated_at"), before)

    def test_the_character_row_reads_back_the_same_after_006(self):
        # `list_characters`/`get_character` select `c.*`; adding columns must
        # not change the Character they build.
        self.assertEqual(self.store.get_character(self.character.id), self.character)
        self.store.write_typed_attributes(self.character.id, {"level": 2})
        self.assertEqual(self.store.get_character(self.character.id), self.character)

    def _raw_value(self, column):
        db = sqlite3.connect(self.path)
        try:
            return db.execute(
                f"SELECT {column} FROM characters WHERE id=?", (self.character.id,)
            ).fetchone()[0]
        finally:
            db.close()

    def test_the_sql_check_refuses_a_writer_that_bypasses_this_api(self):
        """The second line of defence, measured.

        `validate` protects callers who come through the store.  A migration,
        a repair script or another lane's code writing the column directly
        meets the CHECK instead -- so the CHECK is exercised here rather than
        assumed to be decorative.
        """
        cases = [
            ("level", 70000), ("level", -1), ("hp_current", 2**32),
            ("experience", -5), ("speed_walk", 1e39), ("level", "forty"),
        ]
        for column, value in cases:
            with self.subTest(column=column, value=value):
                db = sqlite3.connect(self.path)
                try:
                    with self.assertRaises(sqlite3.IntegrityError):
                        db.execute(
                            f"UPDATE characters SET {column}=? WHERE id=?",
                            (value, self.character.id),
                        )
                        db.commit()
                finally:
                    db.rollback()
                    db.close()
        self.assertEqual(self.store.read_typed_attributes(self.character.id), {})


class TheGateStillRefusesTests(unittest.TestCase):
    """Built columns are not composed blocks, and this file says so."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.account_id = self.store.ensure_account("typed-attr-gate")
        self.character = self.store.create_character(
            self.account_id, "TypedAttrGate", "typedattrgate",
            "fingerprint-typed-attr-gate", _build_wire,
            Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )

    def _typed_values(self):
        """What the database really knows, in the gate's `{x: value}` shape."""
        stored = self.store.read_typed_attributes(self.character.id)
        return {typed.TYPED_COLUMNS[c].x: v for c, v in stored.items()}

    def test_an_unwritten_column_reaches_the_gate_as_absent_not_as_zero(self):
        values = self._typed_values()
        self.assertEqual(values, {})
        gaps = {g.x: g for g in compose.block_gaps(values)}
        self.assertEqual(gaps[7].reason, compose.REASON_NO_TYPED_VALUE)

    def test_writing_speed_closes_that_field_s_gap_and_no_other(self):
        self.store.write_typed_attributes(self.character.id, {"speed_walk": 620.0})
        values = self._typed_values()
        self.assertEqual(values, {7: 620.0})
        gaps = {g.x: g for g in compose.block_gaps(values)}
        self.assertNotIn(7, gaps)
        self.assertIn(2, gaps)  # level, still unwritten
        self.assertEqual(len(gaps), 54)

    def test_a_full_block_still_cannot_be_composed_after_this_round(self):
        self.store.write_typed_attributes(
            self.character.id,
            {c: (400.0 if c == "speed_walk" else 1) for c in typed.TYPED_COLUMNS},
        )
        values = self._typed_values()
        self.assertEqual(len(values), 21)
        with self.assertRaises(compose.AttrComposeError):
            compose.compose_full_block(values)
        # 34 open: x=1 (`characters.name`, server-owned and deliberately not
        # reachable through this API), the 7 unsourced, the sensitive one, and
        # the 25 unadjudicated client defaults.  Writing every typed column
        # this lane built moved the count from 55 to 34 and no further.
        gaps = compose.block_gaps(values)
        self.assertEqual(len(gaps), 34)
        self.assertEqual(
            [g.x for g in gaps if g.reason == compose.REASON_NO_TYPED_VALUE], [1]
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
