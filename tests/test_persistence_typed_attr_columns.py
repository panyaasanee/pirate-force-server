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
import struct
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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
        """The bounds are PARSED and compared as numbers, not searched for.

        The first version of this test did `assertIn(str(bound), statement)`.
        An adversary pass broke two CHECKs and the whole suite stayed green:
        `"0"` is a substring of `"-1000"`, so `BETWEEN -1000 AND 65535` passed
        a u16 column, and `"65535"` is a substring of `"655350"`, so a bound
        ten times too large passed as well.  A repair script writing
        `stat_str = -7` would then have been admitted by the CHECK and blown
        up in `gm/attr_wire.encode_field` at emit time on a live client.
        """
        for statement in self.statements:
            declaration = re.match(
                r"^ALTER TABLE characters ADD COLUMN ([a-z][a-z0-9_]*) (INTEGER|REAL)",
                statement,
            )
            self.assertIsNotNone(declaration, statement)
            name, sql_type = declaration.group(1), declaration.group(2)
            spec = typed.TYPED_COLUMNS[name]
            with self.subTest(column=name):
                self.assertEqual(sql_type, spec.sql_type)
                self.assertIn(f"{name} IS NULL", statement)
                self.assertIn(f"typeof({name})=", statement)
                bounds = re.search(
                    rf"{name} BETWEEN (-?[0-9.eE+-]+) AND (-?[0-9.eE+-]+)\)",
                    statement,
                )
                self.assertIsNotNone(bounds, statement)
                low, high = (float(bounds.group(1)), float(bounds.group(2)))
                self.assertEqual(low, float(spec.minimum))
                self.assertEqual(high, float(spec.maximum))

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

    def test_a_float_is_stored_as_the_float32_the_wire_will_carry(self):
        """The database and the client must hold the SAME number.

        `gm/attr_wire.py` emits an f32 as `struct.pack("<f", value)` while the
        column is an 8-byte REAL, so without rounding here the row says
        `400.1` and the client is sent `400.1000061035156` -- two numbers, one
        character, nothing measuring the difference.
        """
        self.assertEqual(typed.validate("speed_walk", 400.1), 400.1000061035156)
        stored = typed.validate("speed_walk", 400.1)
        self.assertEqual(struct.unpack("<f", struct.pack("<f", stored))[0], stored)

    def test_a_speed_that_underflows_to_zero_on_the_wire_is_refused(self):
        """The owner's banned zero, arriving by arithmetic instead of `.get`.

        An adversary pass measured it: `1e-300` validates, stores, reads back
        as `1e-300`, and reaches the client as an EXACT `0.0`.  And on this
        wire a zero is a value rather than an absence -- see
        `tests/test_npc_gait_wire.py`,
        `test_zero_speed_is_still_serialized_because_only_none_means_absent`.
        """
        for value in (1e-300, 5e-324, -1e-300):
            with self.subTest(value=value):
                with self.assertRaises(typed.TypedAttrError):
                    typed.validate("speed_walk", value)
        # a real zero, asked for on purpose, is still storable
        self.assertEqual(typed.validate("speed_walk", 0.0), 0.0)

    def test_the_compose_conversion_revalidates_instead_of_trusting_presence(self):
        """`block_gaps` keys on `x in typed_values`, never on the value.

        So a caller building `{x: row[x]}` straight off a SELECT walks a
        `None` past the gate and into the encoder.  This conversion is the one
        that refuses it.
        """
        self.assertEqual(
            typed.typed_values_for_compose({"speed_walk": 400.0, "level": 3}),
            {7: 400.0, 2: 3},
        )
        for bad in ({"level": None}, {"level": 99999}, {"deleted_at": 1},
                    {"speed_walk": "fast"}):
            with self.subTest(bad=bad):
                with self.assertRaises(typed.TypedAttrError):
                    typed.typed_values_for_compose(bad)
        gaps = {g.x: g for g in compose.block_gaps({7: None})}
        self.assertNotIn(7, gaps, "the gate itself cannot see a None; this is why")


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
        """And the refused write really did not land.

        The earlier version of this test asserted only the `KeyError`.  An
        adversary pass deleted the whole existence guard from
        `write_typed_attributes` and this test stayed green -- the trailing
        read raised `KeyError` by itself while the UPDATE had already written
        `level=10` onto the soft-deleted row.  So the row is read raw here.
        """
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
        db = sqlite3.connect(self.path)
        try:
            row = db.execute(
                "SELECT level FROM characters WHERE id=?", (second.id,)
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(row[0], 9, "the refused write landed on a deleted row")

    def test_the_state_returned_is_read_under_the_write_s_own_lock(self):
        """D3/D4: commit-then-read let another writer into the window.

        Measured by an adversary pass on the earlier shape, which returned
        `self.read_typed_attributes(...)` on a NEW connection after the
        transaction had already committed: a concurrent soft-delete in that
        window made this method commit the write AND raise `KeyError` (a
        caller catching `KeyError` would report "no such character" while the
        row on disk had changed), and a concurrent write made it return a
        value it never wrote.  The read-back is now inside the same
        transaction, and this test pins that by making the second-connection
        path explode if it is ever taken again.
        """
        def forbidden(*args, **kwargs):
            raise AssertionError(
                "write_typed_attributes read its result on a second "
                "connection, outside its own transaction"
            )

        with mock.patch.object(SQLiteStore, "read_typed_attributes", forbidden):
            after = self.store.write_typed_attributes(self.character.id, {"level": 4})
        self.assertEqual(after, {"level": 4})

    def test_the_update_itself_refuses_a_soft_deleted_row(self):
        # Belt and braces, measured separately from the guard above it: the
        # UPDATE carries `deleted_at IS NULL` too, so neither one alone can be
        # removed and still let a write land where the API says it cannot.
        sql = Path(
            ROOT / "src" / "pirateforce_foundation" / "store.py"
        ).read_text(encoding="utf-8")
        body = sql[sql.index("def write_typed_attributes"):]
        body = body[:body.index("def _character")]
        self.assertIn("WHERE id=? AND deleted_at IS NULL", body)
        self.assertIn("rowcount", body)

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
