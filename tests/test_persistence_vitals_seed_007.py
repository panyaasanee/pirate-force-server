"""LANE-DB / M4: ``migrations/007_character_vitals_seed.sql`` -- the first
migration of this lane that writes EXISTING ROWS, and the three conditions
``COO-DECISION 20260902_0250`` attached to letting it.

The decision approved seeding ``level=1, hp_current=100, hp_max=100`` into
rows that hold none, on the ground that those three numbers are a
TRANSCRIPTION of what ``src/pirateforce_foundation/player_wire.py:203-205``
already sends to every client at every login rather than a new value this
lane picked.  It attached three conditions, and this file is where each one
is measured rather than promised:

1. ``WireEqualityTests`` -- the bytes encoded from what the migration leaves
   in the DATABASE equal, byte for byte, the bytes ``player_wire`` builds
   today.  Not a re-implementation of either side: the real migration runs
   against a real SQLite file, the values come back through
   ``SQLiteStore.read_typed_attributes``, and the comparison is against the
   real ``player_wire`` projection driven with the real v141 tag helpers.
2. ``CensusAfterMigrationTests`` -- the number quoted in the round file comes
   from ``SQLiteStore.vitals_seeding_census``, which COUNTS ROWS in the
   database it is holding.  The test proves the census actually moves with
   the migration, so a round file quoting zero-seeded after 007 would be
   caught here rather than believed.
3. ``HeaderTagTests`` -- the header carries the decision's label, so a reader
   who opens the file in a year sees that the original game's default is OPEN
   and that a future RE answer means a NEW file, not an edit to this one.

Two more properties are proved here because they are what makes a
row-touching migration survivable at all, and neither is visible from the SQL:

* ``MigrationIsNarrowTests`` -- it touches exactly three columns of exactly
  the rows that hold nothing, and a row that already holds a value comes out
  the other side with its exact bytes.  Including the case that made the HP
  pair atomic: ``hp_max=50`` with ``hp_current`` NULL must NOT come out at
  ``hp_current=100``.
* ``BootSnapshotProtects007Tests`` -- the pre-apply copy really is taken for
  THIS file by the real ``migrate_with_backup``, and the pre-007 database
  really can be restored out of it.  ``COO-DECISION 20260901_1112`` point 3
  is a rule about the owner's only copy of the world; a test that asserted
  the mechanism exists somewhere would not be about that.
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

from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.gm.attr_wire import BY_X, encode_field  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation import player_wire  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MIGRATION_007 = MIGRATIONS / "007_character_vitals_seed.sql"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: The label ``COO-DECISION 20260902_0250`` point 3 requires in the header,
#: in the ASCII spelling the file uses (the decision wrote an em dash; every
#: line this repository ships is read under a cp874 console).
REQUIRED_HEADER_TAG = (
    "TRANSCRIBED from player_wire hardcode -- original game default OPEN"
)

#: What 007 seeds, and the ONLY thing it may seed.
SEEDED = {"level": 1, "hp_current": 100, "hp_max": 100}


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


def _statements(sql: str) -> list[str]:
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [" ".join(s.split()) for s in body.split(";") if s.strip()]


class _MigratedWorkspace(unittest.TestCase):
    """Run 001..006, put real rows in, THEN run the full directory.

    The pre-007 half is a REAL migration run over a copy of the real files,
    not a hand-built schema: a seed migration that works against a schema this
    test invented would prove nothing about the owner's database.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_006"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) < 7:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state.sqlite3"

    def _rows(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                "SELECT * FROM characters ORDER BY id").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()

    def _make(self, names):
        """Create characters on the pre-007 schema; return their ids."""
        store = SQLiteStore(self.path, self.older)
        store.migrate()
        account_id = store.ensure_account("vitals-seed-007")
        home = Position(3, 0, 11.0, 22.0, 33.0, heading=1.5)
        ids = []
        for name in names:
            character = store.create_character(
                account_id, name, name.lower(),
                "fingerprint-007-%s" % name.lower(), _build_wire, home,
            )
            ids.append(character.id)
        return ids

    def _apply_007(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()

    def _applied_versions(self):
        db = sqlite3.connect(self.path)
        try:
            return {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()

    def _set(self, character_id, **columns):
        db = sqlite3.connect(self.path)
        try:
            for column, value in columns.items():
                db.execute(
                    "UPDATE characters SET %s=? WHERE id=?" % column,
                    (value, character_id),
                )
            db.commit()
        finally:
            db.close()


class HeaderTagTests(unittest.TestCase):
    """Condition 3 of COO-DECISION 20260902_0250."""

    def setUp(self):
        self.sql = MIGRATION_007.read_text(encoding="utf-8")

    def test_the_header_carries_the_decision_s_label(self):
        self.assertIn(REQUIRED_HEADER_TAG, self.sql)

    def test_the_label_is_in_the_header_not_buried_after_a_statement(self):
        """A label a reader has to scroll past the SQL to find is not a
        header.  Measured position: before the first statement.

        "The first statement" is the first line that STARTS with `UPDATE`, not
        the first occurrence of the word: the header quotes `002`'s own
        `UPDATE` when it explains why "first row-touching migration" needs the
        lane qualifier, and matching that turned this test red for a comment.
        """
        lines = self.sql.splitlines(keepends=True)
        offset, first_statement = 0, None
        for line in lines:
            if line.upper().startswith("UPDATE"):
                first_statement = offset
                break
            offset += len(line)
        self.assertIsNotNone(first_statement, "the migration has no statement")
        self.assertLess(self.sql.index(REQUIRED_HEADER_TAG), first_statement)

    def test_the_file_is_ascii(self):
        """Every line this repository ships is read under a cp874 console at
        least once (`gate-windows.yml`), and a migration is read by the boot
        that applies it, not only by a reader."""
        MIGRATION_007.read_bytes().decode("ascii")

    def test_the_header_names_what_the_numbers_were_transcribed_from(self):
        """By SYMBOL and by emitting expression, not by line number.

        The first version of this test asserted the strings
        `"player_wire.py:203"`/`":204"`/`":205"` -- the file compared against a
        constant.  A `pf-adversary` pass moved those three fields to 206-208
        by inserting comments elsewhere in `player_wire.py` and every test in
        this file stayed green.  Since `COO-DECISION 20260902_0250` point 3
        forbids editing 007 afterwards, a line number in this header would
        have become permanently wrong and uncorrectable.
        """
        self.assertIn("PLAYER_LOGIN_LEVEL", self.sql)
        self.assertIn("_make_actor_attr_with_name_and_class", self.sql)
        self.assertIn("legacy.u16tag(0x12, level)", self.sql)
        self.assertIn("legacy.u32tag(0x14, 100)", self.sql)
        self.assertIn("player_wire.py", self.sql)


class MigrationShapeTests(unittest.TestCase):
    """Parsed, not assumed: what the file is allowed to contain."""

    def setUp(self):
        self.statements = _statements(
            MIGRATION_007.read_text(encoding="utf-8"))

    def test_every_statement_is_an_update_on_characters(self):
        self.assertTrue(self.statements)
        for statement in self.statements:
            self.assertTrue(
                statement.upper().startswith("UPDATE CHARACTERS SET"),
                statement,
            )

    def test_no_statement_can_destroy_or_create_anything(self):
        """The verbs this file must never contain.  `UPDATE` is the one thing
        it may do and the reason it needed a decision to exist at all.

        Matched on WORD BOUNDARIES, not as substrings.  A `pf-adversary` pass
        showed what the substring spelling costs the next author: adding the
        safest possible narrowing to a future migration, `AND deleted_at IS
        NULL`, turned this test red on `DELETE` -- a red whose message accuses
        them of destroying something, for writing a guard.
        """
        for verb in ("DELETE", "DROP", "INSERT", "REPLACE", "ALTER",
                     "CREATE", "PRAGMA", "ATTACH", "VACUUM", "BEGIN",
                     "COMMIT", "ROLLBACK"):
            for statement in self.statements:
                self.assertIsNone(
                    re.search(r"\b%s\b" % verb, statement.upper()),
                    "%s in %s" % (verb, statement),
                )

    def test_the_verb_scan_does_not_fire_on_a_column_name(self):
        """The control for the boundary rule above -- without it this test
        file cannot tell a forbidden verb from a column that contains one."""
        harmless = "UPDATE CHARACTERS SET LEVEL = 1 WHERE DELETED_AT IS NULL"
        self.assertIn("DELETE", harmless)
        self.assertIsNone(re.search(r"\bDELETE\b", harmless))

    def test_every_column_written_is_guarded_by_its_own_is_null(self):
        """The whole safety property: a row that already holds one of these
        values is not in the WHERE clause of the statement that writes it.

        Checked per COLUMN rather than by "the WHERE contains IS NULL
        somewhere", which a statement writing two columns and guarding one
        would pass.
        """
        for statement in self.statements:
            upper = statement.upper()
            self.assertIn(" WHERE ", upper, statement)
            where = upper.split(" WHERE ", 1)[1]
            assignments = upper.split(" SET ", 1)[1].split(" WHERE ", 1)[0]
            for part in assignments.split(","):
                column = part.split("=")[0].strip()
                self.assertIn("%s IS NULL" % column, where, statement)

    def test_no_top_level_or_can_widen_a_where_clause(self):
        """An `OR` beside the guards would let a row that holds a value back
        in.  The one `OR` this file contains is INSIDE parentheses -- the
        `level` guard on the HP pair -- so the check strips parenthesised
        groups and requires the remaining, top-level condition to be a pure
        AND-chain.
        """
        for statement in self.statements:
            where = statement.upper().split(" WHERE ", 1)[1]
            stripped, depth = [], 0
            for character in where:
                if character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                elif depth == 0:
                    stripped.append(character)
            self.assertGreaterEqual(depth, 0, statement)
            self.assertEqual(depth, 0, statement)
            self.assertNotIn(" OR ", "".join(stripped), statement)

    def test_the_columns_written_are_exactly_the_three_vitals(self):
        written = set()
        for statement in self.statements:
            assignments = statement.split(" SET ", 1)[1].split(" WHERE ", 1)[0]
            for part in assignments.split(","):
                written.add(part.split("=")[0].strip())
        self.assertEqual(written, set(SEEDED))
        self.assertEqual(written, set(vitals.VITAL_COLUMNS))

    def test_the_hp_pair_is_written_by_one_statement_over_both_nulls(self):
        """The defect that made the pair atomic: seeding `hp_current` on its
        own condition would put 100 into a row whose `hp_max` is 50."""
        hp = [s for s in self.statements if "hp_current" in s]
        self.assertEqual(len(hp), 1, self.statements)
        self.assertIn("hp_max", hp[0])
        where = hp[0].upper().split(" WHERE ", 1)[1]
        self.assertIn("HP_CURRENT IS NULL AND HP_MAX IS NULL", where)

    def test_no_other_typed_column_is_named_by_any_statement(self):
        """Eighteen columns stay NULL, and `speed_walk` is named here so that
        the one column with two candidate values (COO-DECISION 20260901_1447
        point 2) is proved absent rather than assumed absent."""
        for column in typed.TYPED_COLUMNS:
            if column in SEEDED:
                continue
            for statement in self.statements:
                self.assertNotIn(column, statement, column)


class MigrationIsNarrowTests(_MigratedWorkspace):
    """Real rows, real migration, compared field by field."""

    def test_a_row_holding_nothing_gets_exactly_the_three_values(self):
        self._make(["SeedOne"])
        before = self._rows()[0]
        self._apply_007()
        after = self._rows()[0]
        for column, value in SEEDED.items():
            self.assertIsNone(before[column], column)
            self.assertEqual(after[column], value, column)
        for column in before:
            if column not in SEEDED:
                self.assertEqual(after[column], before[column], column)

    def test_every_other_typed_column_is_still_null(self):
        self._make(["SeedTwo"])
        self._apply_007()
        row = self._rows()[0]
        for column in typed.TYPED_COLUMNS:
            if column not in SEEDED:
                self.assertIsNone(row[column], column)

    def test_a_row_that_already_holds_a_level_keeps_it(self):
        ids = self._make(["Veteran"])
        self._set(ids[0], level=42)
        self._apply_007()
        row = self._rows()[0]
        self.assertEqual(row["level"], 42)
        self.assertEqual(row["hp_current"], 100)
        self.assertEqual(row["hp_max"], 100)

    def test_a_half_written_hp_pair_is_left_alone_entirely(self):
        """THE reason the pair is one statement.  Per-column seeding would
        leave `hp_current=100 > hp_max=50`, a state `persistence_vitals`
        refuses to resolve -- so the migration would have manufactured a
        character the server cannot compose for."""
        ids = self._make(["Wounded"])
        self._set(ids[0], hp_max=50)
        self._apply_007()
        row = self._rows()[0]
        self.assertEqual(row["hp_max"], 50)
        self.assertIsNone(row["hp_current"])
        self.assertEqual(row["level"], 1)

    def test_the_other_half_written_pair_is_left_alone_too(self):
        ids = self._make(["Bleeding"])
        self._set(ids[0], hp_current=7)
        self._apply_007()
        row = self._rows()[0]
        self.assertEqual(row["hp_current"], 7)
        self.assertIsNone(row["hp_max"])

    def test_a_soft_deleted_row_is_seeded_like_any_other(self):
        """`004_character_soft_delete_reuse.sql` keeps the row.  Leaving it
        NULL would make an undelete produce a character the compose gate
        refuses, which is a worse outcome than seeding it."""
        ids = self._make(["Gone"])
        db = sqlite3.connect(self.path)
        try:
            db.execute("UPDATE characters SET deleted_at='x' WHERE id=?",
                       (ids[0],))
            db.commit()
        finally:
            db.close()
        self._apply_007()
        row = self._rows()[0]
        self.assertEqual(row["level"], 1)
        self.assertEqual(row["hp_current"], 100)

    def test_a_level_zero_row_is_not_completed_into_an_accepted_state(self):
        """The defect a `pf-adversary` pass measured, kept as a test.

        A row at `level = 0` with both HP ends NULL is REFUSED today, because
        its HP is unseeded.  Seeding the pair into it would make it COMPLETE
        -- `require()` accepts it, `apply_hp_damage` runs on it -- around a
        level of zero nobody adjudicated, which is this migration turning a
        fail-closed row into an accepted one.  `persistence_vitals` refuses
        `hp_max = 0` and has no rule at all about `level = 0`, so nothing
        downstream would catch it either.
        """
        ids = self._make(["Levelless"])
        self._set(ids[0], level=0)
        before = SQLiteStore(self.path, self.older).read_character_vitals(ids[0])
        with self.assertRaises(vitals.VitalsError):
            before.require()

        self._apply_007()

        row = self._rows()[0]
        self.assertEqual(row["level"], 0)
        self.assertIsNone(row["hp_current"])
        self.assertIsNone(row["hp_max"])
        after = SQLiteStore(self.path, MIGRATIONS).read_character_vitals(ids[0])
        with self.assertRaises(vitals.VitalsError):
            after.require()

    def test_a_level_one_row_beside_it_is_still_seeded(self):
        """The control for the test above: the level guard refuses exactly the
        zero, not every row that happens to hold a level."""
        ids = self._make(["Levelless", "Levelled"])
        self._set(ids[0], level=0)
        self._set(ids[1], level=3)
        self._apply_007()
        rows = self._rows()
        self.assertIsNone(rows[0]["hp_current"])
        self.assertEqual(rows[1]["level"], 3)
        self.assertEqual(rows[1]["hp_current"], 100)
        self.assertEqual(rows[1]["hp_max"], 100)

    def test_other_tables_are_byte_identical_across_the_migration(self):
        self._make(["Untouched"])
        before = self._dump_tables()
        self._apply_007()
        after = self._dump_tables()
        for table in before:
            self.assertEqual(after[table], before[table], table)

    def test_007_is_recorded_in_the_ledger_and_re_running_is_a_no_op(self):
        self._make(["Ledger"])
        self._apply_007()
        first = self._rows()[0]
        self.assertIn(7, self._applied_versions())
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self._rows()[0], first)

    def test_a_value_written_after_the_migration_is_not_re_seeded(self):
        """The ledger is what stops a second apply, but the statements are
        idempotent anyway; this is the property a reader assumes and nothing
        else here checks."""
        ids = self._make(["Later"])
        self._apply_007()
        self._set(ids[0], level=9, hp_current=3)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        row = self._rows()[0]
        self.assertEqual(row["level"], 9)
        self.assertEqual(row["hp_current"], 3)

    def _dump_tables(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            names = [str(r[0]) for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name<>'characters' "
                "AND name<>'schema_migrations' ORDER BY name")]
            return {
                name: [dict(r) for r in db.execute(
                    "SELECT * FROM %s ORDER BY rowid" % name)]
                for name in names
            }
        finally:
            db.close()



class WireEqualityTests(_MigratedWorkspace):
    """Condition 1 of COO-DECISION 20260902_0250, measured on both sides.

    The DATABASE side reads back through the shipped read path
    (``read_typed_attributes`` -> ``typed_values_for_compose`` ->
    ``gm.attr_wire.encode_field``); nothing here re-implements a codec.

    THE SHIPPED SEND PATH IS NOT USED HERE, AND THE FIRST DRAFT OF THIS
    DOCSTRING LIED ABOUT WHY.  It said the bytes were "the same either way,
    because ``compose_sparse_block``'s own last step is this
    ``encode_field``".  A ``pf-adversary`` pass measured that sentence and it
    is false twice over: ``compose_sparse_block`` returns NUMBERS, not bytes
    (its last step is ``validate(column_for(x), value)``), and it REFUSES
    x=2/3/4 outright -- ``field_not_approved_for_the_sparse_path``, since
    ``COO-ORDER 20260901_1640`` approves x=7 alone.  ``encode_field`` is
    reached from ``encode_block``, one layer further out.

    So what is true, stated as narrowly as it deserves: these tests prove that
    the values 007 stores encode to the bytes the login frame carries today.
    They do NOT prove anything about the approved sparse path, because that
    path cannot carry these three fields at all until a COO order widens it.
    Widening it is not a test's decision, and inventing a per-field
    concatenation here does not make one; the second test below is what keeps
    this honest, by requiring the bytes to appear in the REAL login frame
    rather than only in a concatenation this file assembled.
    """

    def setUp(self):
        super().setUp()
        self.legacy = load_legacy(LEGACY_PATH)

    def test_the_three_fields_encoded_from_the_database_are_the_wire_bytes(self):
        ids = self._make(["WireOne"])
        self._apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        stored = store.read_typed_attributes(ids[0])
        for column in SEEDED:
            self.assertIn(column, stored, column)
        composed = typed.typed_values_for_compose(
            {c: v for c, v in stored.items() if c in SEEDED})
        from_database = b"".join(
            encode_field(self.legacy, BY_X[x], composed[x])
            for x in (vitals.LEVEL_X, vitals.HP_CURRENT_X, vitals.HP_MAX_X)
        )
        from_player_wire = (
            self.legacy.u16tag(0x12, player_wire.PLAYER_LOGIN_LEVEL)
            + self.legacy.u32tag(0x14, 100)
            + self.legacy.u32tag(0x14, 100)
        )
        self.assertEqual(from_database, from_player_wire)

    def test_those_bytes_really_are_the_ones_the_login_frame_carries(self):
        """The line above pins the three tags; this pins that the same three
        tags appear, in that order, INSIDE the frame `player_wire` builds --
        so a future edit that reorders or drops them cannot leave the first
        test green and the login frame changed."""
        ids = self._make(["WireTwo"])
        self._apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        stored = store.read_typed_attributes(ids[0])
        composed = typed.typed_values_for_compose(
            {c: v for c, v in stored.items() if c in SEEDED})
        from_database = b"".join(
            encode_field(self.legacy, BY_X[x], composed[x])
            for x in (vitals.LEVEL_X, vitals.HP_CURRENT_X, vitals.HP_MAX_X)
        )
        frame = player_wire.make_actor_attr_with_name_and_class(
            self.legacy, 0x10010001, 0, 1, 0, "test01",
        )
        self.assertEqual(frame.count(from_database), 1, from_database.hex())

    def test_the_transcribed_values_are_still_what_player_wire_emits(self):
        """The migration's provenance claim, re-derived from the SOURCE.

        The first version of this file asserted only that the strings
        ``"player_wire.py:203"``/``":204"``/``":205"`` appeared in the
        migration text -- the file compared against a constant, never opening
        ``player_wire.py``.  A ``pf-adversary`` pass inserted three comment
        lines earlier in that module; the three fields moved to 206-208 and
        all 28 tests stayed green.

        That pin cannot be repaired the usual way, because
        ``COO-DECISION 20260902_0250`` point 3 forbids editing 007 after the
        fact: a line number in the header would be permanently wrong on the
        first unrelated edit above it.  So the header cites SYMBOLS, and what
        is graded here is the substance -- that ``player_wire`` still emits
        level 1 and hp 100/100, from the function the header names.
        """
        source = Path(player_wire.__file__).read_text(encoding="utf-8")
        start = source.index("def _make_actor_attr_with_name_and_class")
        body = source[start:source.index("\ndef ", start + 1)]
        self.assertIn("legacy.u16tag(0x12, level)", body)
        self.assertEqual(body.count("legacy.u32tag(0x14, 100)"), 2, body)
        self.assertEqual(player_wire.PLAYER_LOGIN_LEVEL, SEEDED["level"])
        self.assertEqual(SEEDED["hp_current"], 100)
        self.assertEqual(SEEDED["hp_max"], 100)

    def test_the_stored_values_resolve_as_a_complete_vitals_state(self):
        """A seed that the lane's own decision layer refuses would be a seed
        that cannot be used, whatever the bytes say."""
        ids = self._make(["WireThree"])
        self._apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        resolution = store.read_character_vitals(ids[0])
        self.assertEqual(resolution.require().level, 1)
        self.assertEqual(resolution.require().hp_current, 100)
        self.assertEqual(resolution.require().hp_max, 100)

    def test_before_the_migration_the_same_read_reports_a_named_gap(self):
        """The control for the test above: the seed is what moved it, not the
        read path being permissive."""
        ids = self._make(["WireFour"])
        store = SQLiteStore(self.path, self.older)
        resolution = store.read_character_vitals(ids[0])
        with self.assertRaises(vitals.VitalsError):
            resolution.require()


class CensusAfterMigrationTests(_MigratedWorkspace):
    """Condition 2 of COO-DECISION 20260902_0250: the number in the round file
    is counted in the database, and it moves when the migration runs."""

    def test_the_census_counts_zero_before_and_every_row_after(self):
        self._make(["CensusOne", "CensusTwo"])
        before = SQLiteStore(self.path, self.older).vitals_seeding_census()
        self.assertEqual(before["characters_any"], 2)
        for column in SEEDED:
            self.assertEqual(before["%s_seeded_any" % column], 0, column)
        self._apply_007()
        after = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        self.assertEqual(after["characters_any"], 2)
        for column in SEEDED:
            self.assertEqual(after["%s_seeded_any" % column], 2, column)
            self.assertEqual(after["%s_seeded_live" % column], 2, column)

    def test_the_census_counts_the_rows_007_declined_to_complete(self):
        """A skipped row is not a seeded row, and 007 runs ONCE.

        A row 007 declines -- a half-written HP pair, a `level = 0` -- keeps
        its incomplete vitals forever: the ledger stops 007 from running
        again and the decision forbids editing it.  Nothing would ever
        complete it, and `require()`/`apply_hp_damage` refuse it for good.
        That is the right call for a migration, and it is only survivable if
        the leftovers are COUNTABLE rather than silent, so this pins that the
        census can name them: seeded < characters is the whole signal.
        """
        ids = self._make(["Whole", "HalfPair", "ZeroLevel"])
        self._set(ids[1], hp_max=50)
        self._set(ids[2], level=0)
        self._apply_007()
        census = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        self.assertEqual(census["characters_any"], 3)
        self.assertEqual(census["level_seeded_any"], 3)
        self.assertEqual(census["hp_current_seeded_any"], 1)
        self.assertEqual(census["hp_max_seeded_any"], 2)
        declined = census["characters_any"] - census["hp_current_seeded_any"]
        self.assertEqual(declined, 2)

    def test_the_census_names_the_database_it_actually_counted(self):
        """`census["database"]` must identify the file the COUNTS came from.

        The first version of this test asserted only
        `census["database"] == self.path` against `store.py`'s literal
        `census["database"] = self.path`: a store echoing its own constructor
        argument, which cannot fail and proves nothing.  A `pf-adversary` pass
        measured that.  Two databases with DIFFERENT row counts are censused
        here, so the label and the numbers have to move together.
        """
        self._make(["CensusThree"])
        self._apply_007()
        other = self.root / "other.sqlite3"
        other_store = SQLiteStore(other, MIGRATIONS)
        other_store.migrate()
        account_id = other_store.ensure_account("census-other")
        home = Position(3, 0, 1.0, 2.0, 3.0, heading=0.0)
        for name in ("OtherOne", "OtherTwo"):
            other_store.create_character(
                account_id, name, name.lower(),
                "fingerprint-other-%s" % name.lower(), _build_wire, home)

        mine = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        theirs = other_store.vitals_seeding_census()
        self.assertEqual(str(mine["database"]), str(self.path))
        self.assertEqual(str(theirs["database"]), str(other))
        self.assertEqual(mine["characters_any"], 1)
        self.assertEqual(theirs["characters_any"], 2)
        self.assertNotEqual(mine["characters_any"], theirs["characters_any"])

    def test_an_empty_database_reports_zero_rather_than_none(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        census = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        self.assertEqual(census["characters_any"], 0)
        for column in SEEDED:
            self.assertEqual(census["%s_seeded_any" % column], 0, column)


class SeedsACohortNotADatabaseTests(_MigratedWorkspace):
    """007 seeds the characters that EXIST when it runs, and no others.

    A `pf-adversary` pass measured the consequence and it is the largest
    limitation of this file, so it is pinned here rather than left for a
    later round to discover: `SQLiteStore.create_character` names its INSERT
    columns explicitly and none of the three is among them, `006` added them
    with no DEFAULT, and the ledger stops 007 from ever running again.  So a
    character created after the migration has NULL vitals forever, exactly as
    before, and on a FRESH INSTALL -- where 007 runs against an empty table --
    the census reads 0/0/0 for all three columns while reporting success.

    Nothing in this lane can close that: `create_character` is an existing
    method and the charter (`COO-DECISION 20260901_1100`) forbids changing
    one.  Closing it needs either a `DEFAULT` on the three columns (a table
    rebuild, since SQLite cannot add a default to an existing column) or a
    write at character creation -- both of them decisions, not edits.  Raised
    to COO the same round this landed.

    These tests exist so that the day it IS closed, they go red and say so.
    """

    def test_a_character_created_after_007_has_no_vitals_at_all(self):
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("after-007")
        character = store.create_character(
            account_id, "Newborn", "newborn", "fingerprint-newborn",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        stored = store.read_typed_attributes(character.id)
        for column in SEEDED:
            self.assertNotIn(column, stored, column)
        with self.assertRaises(vitals.VitalsError):
            store.read_character_vitals(character.id).require()

    def test_on_a_fresh_install_the_census_reads_zero_after_a_successful_007(self):
        """The sentence a round file must never write about a fresh install:
        "007 applied, every character seeded"."""
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertIsNone(store.migrate_with_backup(
            backups_root=self.root / "backups"))
        account_id = store.ensure_account("fresh")
        store.create_character(
            account_id, "Fresh", "fresh", "fingerprint-fresh", _build_wire,
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        census = store.vitals_seeding_census()
        self.assertEqual(census["characters_any"], 1)
        for column in SEEDED:
            self.assertEqual(census["%s_seeded_any" % column], 0, column)

    def test_the_migration_header_states_this_limitation(self):
        """A limitation a reader has to run a test to discover is not stated.

        The header is what a boot's operator and the next lane read; this
        pins that the sentence is in it and did not get edited out.
        """
        sql = MIGRATION_007.read_text(encoding="utf-8")
        self.assertIn("created after it", sql)
        self.assertIn("create_character", sql)


class BootSnapshotProtects007Tests(_MigratedWorkspace):
    """The owner's rule for a row-touching migration (COO-DECISION
    20260901_1112 point 3), measured against THIS file rather than against a
    synthetic probe migration."""

    def test_a_snapshot_is_due_while_007_is_the_pending_file(self):
        from pirateforce_foundation import persistence_backup

        self._make(["Snapshot"])
        take, reason = persistence_backup.should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take, reason)
        self.assertIn("007", reason)

    def test_a_snapshot_that_dies_in_its_prologue_still_aborts_the_boot(self):
        """`app.py` catches `BackupError` and nothing else, so a failure this
        module lets out raw becomes a traceback and exit 1 instead of exit 13
        and "your database has NOT been changed".

        A `pf-adversary` pass measured the hole: `source_fingerprint` hashes
        the live database before the copy loop's `try`, so an `OSError` there
        -- a Windows antivirus or backup agent holding the file -- escaped.
        The database was never at risk; the message the owner needs was.
        """
        from pirateforce_foundation import persistence_backup
        from unittest import mock

        self._make(["Prologue"])
        with mock.patch.object(
                persistence_backup, "_sha256_file",
                side_effect=OSError("disk went away mid-snapshot")):
            with self.assertRaises(persistence_backup.BackupError) as caught:
                SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                    backups_root=self.root / "backups")
        self.assertIn("disk went away mid-snapshot", str(caught.exception))
        # ... and the migration did NOT run behind the failed snapshot.
        row = self._rows()[0]
        for column in SEEDED:
            self.assertIsNone(row[column], column)
        self.assertNotIn(7, self._applied_versions())

    def test_the_snapshot_taken_at_boot_restores_the_pre_007_database(self):
        ids = self._make(["Restore"])
        backups = self.root / "backups"
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=backups)
        self.assertIsNotNone(snapshot)
        seeded = self._rows()[0]
        self.assertEqual(seeded["level"], 1)

        # `snapshot_database` returns the copied DATABASE FILE inside the
        # snapshot directory, not the directory (persistence_backup.py:685).
        copy = Path(snapshot)
        self.assertEqual(copy.name, self.path.name)
        restored = self.root / "restored.sqlite3"
        shutil.copy2(copy, restored)
        db = sqlite3.connect(restored)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT * FROM characters WHERE id=?", (ids[0],)).fetchone()
            versions = {int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")}
        finally:
            db.close()
        self.assertNotIn(7, versions)
        for column in SEEDED:
            self.assertIsNone(row[column], column)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
