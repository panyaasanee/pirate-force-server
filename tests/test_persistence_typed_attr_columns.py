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
   A boot now snapshots first (``app.py:784``/``:787`` call
   ``SQLiteStore.migrate_with_backup``; ``CORE-REQUEST-DB-001`` answered), so
   this is no longer the LAST line of defence it was when first written -- but
   a snapshot is a way to undo damage, not a reason to do it, and "it only
   adds columns" is still the whole safety argument of this file, so it is
   still the thing measured hardest here.
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
character, which is deliberate (seeding is a write on live rows, and what it
waits for is now a value nobody has adjudicated -- ``COO-DECISION 20260901_
1447`` point 2 -- not the backup-on-boot wiring, which landed), so a full
attribute block still cannot compose.  ``TheGateStillRefusesTests`` asserts
that refusal rather than hiding it, and ``BootSnapshotProtects006Tests``
asserts the protection that arriving wiring is supposed to give this file.
"""
import json
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

        A backfill, an UPDATE or a table rebuild in this file would need a
        value nobody has adjudicated (``COO-DECISION 20260901_1447`` point 2);
        the pre-apply snapshot such a file ALSO needs now exists on the boot
        path, which is asserted separately below.  Checked over the
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


class BootSnapshotProtects006Tests(unittest.TestCase):
    """006 is irreversible, so the thing that makes it survivable is the copy a
    boot takes before applying it.  That copy is taken by code in a file this
    lane may not write (`app.py`, chief's), which is exactly why it is pinned
    here: if a later edit puts the plain `migrate()` back at a boot call site,
    the owner's canonical database meets an irreversible migration with no way
    back, and nothing in this repository would have said so.

    `tests/test_persistence_premigration_backup.py` already proves the backup
    MECHANISM against a synthetic probe migration.  What is proved here is the
    other half: that the mechanism fires for THIS file, on the real
    `migrations/` directory, and that what it leaves behind restores a
    character committed into a HOT write-ahead log -- the state a boot really
    finds, and the one a plain file copy loses.

    WHAT THESE THREE DO NOT PROVE, so nobody reads more into them: that a
    snapshot exists before the pin below ever goes red.  006 is checksum
    -locked once applied, so if `app.py` regressed on a boot BEFORE anyone ran
    this suite, the copy for that boot was never taken and no test here can
    make it exist afterwards.  The pin shortens that window; it does not close
    it.  Raised to COO in `20260901_1520_LANE-DB-REPORT-coo-...md`.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_005"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if path.name != MIGRATION_006.name:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state" / "pirateforce.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _at_005_with_a_character(self, keep_wal_hot=False):
        """A database at schema 005 with one real character in it.

        With `keep_wal_hot`, the character is committed through a connection
        that is left OPEN and returned to the caller, so SQLite cannot
        checkpoint the row out of `-wal` into the database file.  That is the
        state a snapshot has to survive, and the state a naive file copy
        loses; without it a copy that drops the WAL still looks correct.
        """
        store = SQLiteStore(self.path, self.older)
        store.migrate()
        if not keep_wal_hot:
            account_id = store.ensure_account("boot-snapshot-006")
            store.create_character(
                account_id, "SnapshotOne", "snapshotone",
                "fingerprint-boot-snapshot-006", _build_wire,
                Position(3, 0, 44.0, 55.0, 66.0, heading=0.25),
            )
            return store

        holder = sqlite3.connect(str(self.path))
        holder.execute("PRAGMA journal_mode=WAL")
        holder.execute("PRAGMA foreign_keys=ON")
        holder.execute(
            "INSERT INTO accounts(login_name,created_at) VALUES (?,?)",
            ("boot-snapshot-006", "2026-09-01T15:00:00Z"),
        )
        account_id = int(holder.execute(
            "SELECT id FROM accounts WHERE login_name=?",
            ("boot-snapshot-006",),
        ).fetchone()[0])
        actor, avatar, identity, _ = _build_wire(1)
        holder.execute(
            "INSERT INTO characters(account_id,selector,name,actor_wire,"
            "avatar_wire,identity_lo,identity_hi,created_at,updated_at,"
            "name_key,create_fingerprint) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (account_id, 1, "SnapshotOne", actor, avatar, identity, 0,
             "2026-09-01T15:00:00Z", "2026-09-01T15:00:00Z", "snapshotone",
             "fingerprint-boot-snapshot-006"),
        )
        holder.commit()
        return store, holder

    @staticmethod
    def _columns(path, table="characters"):
        db = sqlite3.connect(str(path))
        try:
            return {r[1] for r in db.execute(f"PRAGMA table_info({table})")}
        finally:
            db.close()

    @staticmethod
    def _versions(path):
        db = sqlite3.connect(str(path))
        try:
            return {int(r[0]) for r in db.execute("SELECT version FROM schema_migrations")}
        finally:
            db.close()

    def test_a_005_database_meeting_006_is_copied_first_and_the_copy_predates_it(self):
        """The owner's rule 1112 point 3, measured on this lane's own file
        rather than on a probe: the database that exists today (005, with a
        character in it) meets 006 and is copied before a column is added."""
        from pirateforce_foundation import persistence_backup

        self._at_005_with_a_character()
        take, reason = persistence_backup.should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take, reason)
        self.assertEqual([6], persistence_backup.pending_versions(self.path, MIGRATIONS))
        self.assertIn("006", reason)

        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=self.root / "backups"
        )
        self.assertIsNotNone(snapshot, "006 was applied with no snapshot taken")
        self.assertTrue(Path(snapshot).exists())

        # The live database moved to 006 ...
        self.assertIn(6, self._versions(self.path))
        self.assertTrue(set(typed.TYPED_COLUMNS) <= self._columns(self.path))
        # ... and the copy is the state from BEFORE it, character and all.
        self.assertNotIn(6, self._versions(snapshot))
        self.assertEqual(set(), set(typed.TYPED_COLUMNS) & self._columns(snapshot))
        db = sqlite3.connect(str(snapshot))
        try:
            names = [r[0] for r in db.execute(
                "SELECT name FROM characters WHERE deleted_at IS NULL")]
        finally:
            db.close()
        self.assertEqual(["SnapshotOne"], names)

    def test_restoring_the_snapshot_puts_the_database_back_before_006(self):
        """A copy nobody can boot from is not a backup.

        The character is committed through a connection that is STILL OPEN
        when the snapshot is taken, so the row lives in a hot `-wal` rather
        than in the database file.  That is the state a boot actually finds
        (a stopped or killed server leaves one), and it is what separates a
        real backup from `shutil.copyfile`: an adversary pass replaced
        `persistence_backup._copy_consistent`'s online-backup call with a
        plain file copy and the first version of this test -- which let every
        connection close and checkpoint first -- stayed green through it.

        The restore follows the manifest's own `restore_hint` (move the live
        sidecars ASIDE, do not delete them; the snapshot file is
        self-contained) rather than a procedure invented here, and reads the
        hint out of `MANIFEST.json` to check the two steps it still describes.
        """
        store, holder = self._at_005_with_a_character(keep_wal_hot=True)
        try:
            self.assertTrue(
                self.path.with_name(self.path.name + "-wal").exists(),
                "this test is only worth anything with a hot -wal; there is none",
            )
            snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                backups_root=self.root / "backups"
            )
        finally:
            holder.close()

        manifest = json.loads(
            (Path(snapshot).parent / "MANIFEST.json").read_text(encoding="utf-8")
        )
        hint = manifest["restore_hint"]
        self.assertIn("renaming", hint)
        self.assertIn("do not delete them", hint)

        # A server built before 006 refuses the migrated database on purpose.
        with self.assertRaises(Exception) as refused:
            SQLiteStore(self.path, self.older).migrate()
        self.assertIn("newer than this server", str(refused.exception))

        # Step (1) of the hint: move the live sidecars aside, do NOT delete.
        for suffix in ("-wal", "-shm"):
            sidecar = self.path.with_name(self.path.name + suffix)
            if sidecar.exists():
                sidecar.rename(sidecar.with_name(sidecar.name + ".movedaside"))
        # Step (2): the snapshot FILE alone goes over the live database.
        shutil.copy2(snapshot, self.path)

        # ... and now the older server boots, with the character still there.
        restored = SQLiteStore(self.path, self.older)
        restored.migrate()
        self.assertNotIn(6, self._versions(self.path))
        with restored.connect() as db:
            names = [r[0] for r in db.execute(
                "SELECT name FROM characters WHERE deleted_at IS NULL")]
        self.assertEqual(
            ["SnapshotOne"], names,
            "the snapshot lost a transaction that was committed into the "
            "write-ahead log -- a file copy, not a consistent backup",
        )

    def test_every_boot_call_site_in_app_py_still_takes_the_snapshot(self):
        """The pin.  `app.py` is chief's file and this lane cannot write it, so
        the only thing this lane can do about a regression there is see it.

        Scanned over the WHOLE MODULE, not just `main()`.  The first version
        of this test walked `main()` only, and an adversary pass measured the
        hole: move the plain branch's call (`app.py:787` -- the owner's own
        canonical boot, the one with no hypothesis flags) into a module-level
        `def _boot_migrate(store): store.migrate()`, and the pin stayed green
        because `migrate_with_backup` was still visible at `:784` in the
        hypothesis-only branch.  A pin that a one-line extraction walks around
        protects nothing.  Module scope has no such hole: wherever in this
        file the bare `migrate()` ends up, it is seen.

        Parsed with `ast`, not grepped, so a mention of `migrate()` in a
        comment or a docstring can neither create nor hide a failure.

        WHAT THIS DOES NOT PIN, said out loud: that every boot SHAPE takes a
        snapshot.  `app.py` has a third path -- `scene_load` set with no
        hypothesis -- that migrates not at all, which is chief's deliberate
        design (`tests/test_startup_stale_lease_recovery.py::
        test_the_scene_load_branch_is_the_one_deliberate_exception`), not a
        regression, and not this lane's to change.

        🔴 If this test goes red, do NOT edit `app.py` from this lane: write
        the chief a letter (`charter COO-DECISION 20260901_1100` gives him
        `app.py`; this lane's standing request is
        `pf_bridge/notes_to_chief/20260901_1515_LANE-DB-REQUEST-chief-staged-
        canon-gate-spec-and-backuperror-wrapper.md`).  The one thing that
        could change that instruction is an explicit COO order handing this
        lane the file; `COO-DECISION 20260901_1447` point 6 reads like one
        ("LANE-DB เป็นผู้ทำ (ไฟล์ของสายตัวเอง)") but names a file the charter
        assigns to chief, so this lane treated it as a mistake and asked
        rather than edited.  If COO confirms the override, change this
        instruction in the same commit that first edits `app.py`.
        """
        import ast

        app_py = ROOT / "src" / "pirateforce_foundation" / "app.py"
        tree = ast.parse(app_py.read_text(encoding="utf-8"))
        called = [
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("migrate", "migrate_with_backup")
        ]
        self.assertEqual(
            [], [name for name in called if name == "migrate"],
            "app.py calls the unprotected migrate(): an irreversible "
            "migration would apply to the owner's canonical database with no "
            "pre-apply snapshot (owner's rule, COO-DECISION 20260901_1112 "
            "point 3).  Write chief a letter; do not edit app.py from here.",
        )
        self.assertGreaterEqual(
            called.count("migrate_with_backup"), 2,
            "app.py used to call migrate_with_backup at BOTH boot call sites "
            "(:784 hypothesis-enabled, :787 plain -- the owner's canonical "
            "boot is the plain one).  Fewer than two means a call site was "
            "removed or moved; this pin has to move with it, not be dropped.",
        )


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
        """The UPDATE carries `deleted_at IS NULL` of its own, so removing the
        SELECT guard alone cannot land a write where the API says it cannot.

        Read off the statements SQLite ACTUALLY EXECUTED, via a trace
        callback, not off `store.py`'s source.  The first version of this test
        did `assertIn("WHERE id=? AND deleted_at IS NULL", body)` over the
        method's source text -- and an adversary pass measured that the exact
        same string is supplied by the SELECT guard eleven lines above, so
        deleting the predicate from the UPDATE ONLY left the whole suite green
        (6285 passed).  A token that fires on a line other than the one it
        claims to guard is not a test.  This version cannot: the SELECT and
        the UPDATE arrive as separate strings and each is checked on its own.
        """
        statements = []
        real_connect = sqlite3.connect

        def tracing_connect(*args, **kwargs):
            db = real_connect(*args, **kwargs)
            db.set_trace_callback(statements.append)
            return db

        with mock.patch("pirateforce_foundation.store.sqlite3.connect",
                        tracing_connect):
            self.store.write_typed_attributes(self.character.id, {"level": 9})

        updates = [s for s in statements if s.lstrip().startswith("UPDATE characters SET")]
        self.assertEqual(1, len(updates), statements)
        self.assertIn("deleted_at IS NULL", updates[0])
        selects = [s for s in statements
                   if s.lstrip().startswith("SELECT id FROM characters")]
        self.assertEqual(1, len(selects), statements)
        self.assertIn("deleted_at IS NULL", selects[0])

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
