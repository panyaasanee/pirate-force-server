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
import contextlib
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
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

import pf_birth_state as birth_state  # noqa: E402

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


@contextlib.contextmanager
def raw_rows(path):
    """A raw sqlite connection that is committed AND CLOSED.

    `with sqlite3.connect(...)` commits on exit and does NOT close, which
    costs nothing on Linux and fails the whole suite on Windows with
    `WinError 32` out of `TemporaryDirectory` cleanup.  Same helper, same
    reason, as `raw()` in `tests/test_persistence_vitals.py`.
    """
    db = sqlite3.connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


def _statements(sql: str) -> list[str]:
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [" ".join(s.split()) for s in body.split(";") if s.strip()]


def _build_wire_offset(base):
    """A wire builder whose identity cannot collide with `_build_wire`'s.

    `004_character_soft_delete_reuse.sql` puts a partial UNIQUE index on
    `(identity_lo, identity_hi)`, and a second account's selectors also start
    at zero.
    """
    def build(selector):
        return b"wire", b"avatar", base + selector, 0
    return build


def _columns_written_by_migrations_after_007() -> dict[str, float]:
    """Typed columns a migration file numbered ABOVE 007 writes, AND the exact
    value each of them writes.

    Derived from the files themselves, never listed here.  `_apply_007` runs
    the WHOLE directory on purpose -- that is the boot a server really
    performs, and running a hand-built prefix instead would stop measuring
    what the owner's database meets.  The cost is that "every other column is
    still NULL after this file" stops being true the moment a LATER migration
    adjudicates one, which `migrations/008_character_speed_walk_seed.sql` did
    for `speed_walk`.  So the two pins below say what they always meant --
    007 wrote its three and nothing of ITS OWN leaked -- and the columns a
    later file owns are checked to hold THAT FILE'S OWN VALUE rather than
    waved past.

    *** THE VALUE IS PART OF THE RETURN ON PURPOSE.  A `pf-adversary` pass
    pointed out that an exclusion derived from the migration directory
    EXCUSES ITSELF: a future 009 seeding, say, `cash = 0` -- a guessed zero,
    the exact thing `COO-DECISION 20260901_1059` forbids -- would be silently
    excused by these two pins, and a guard of `assertIsNotNone` would not
    notice because zero is not None.  Excusing a column now costs naming the
    number it is excused FOR, so a wrong number is red here even though the
    column is not 007's.
    """
    written = {}
    for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
        if int(path.name[:3]) <= 7:
            continue
        for statement in _statements(path.read_text(encoding="utf-8")):
            if " SET " not in statement:
                continue
            assignments = statement.split(" SET ", 1)[1].split(" WHERE ", 1)[0]
            for part in assignments.split(","):
                column, _, value = part.partition("=")
                column = column.strip()
                if column not in typed.TYPED_COLUMNS:
                    continue
                written[column] = float(value.strip())
    return written


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
        self.births = []

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
        """Create characters on the pre-007 schema, in the pre-007 VITALS
        STATE, and return their ids.

        The second half of that sentence used to be inherited rather than
        built: `create_character` left the three columns NULL, so every test
        below got the row state it wanted for free.  That is a fact about
        today, not about 007 -- `COO-DECISION 20260902_0444` has chief seeding
        the three at creation, and round `cby3pd` measured ten tests in this
        file going red on it, none of them because 007 had changed.  What this
        file is ABOUT is what the migration does to a row in a given state, so
        the fixture now states the state instead of hoping for it.

        The birth state is measured before it is cleared, and
        `pf_birth_state.measure_birth_typed_state` refuses any state other
        than the two this lane accepts -- so clearing cannot hide an insertion
        point that seeds the wrong numbers, a fourth column, or a `level` of
        zero.  It reads the FIRST character, before any `_set` call has run.
        """
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
            # EVERY character, not only the first, and each one before the
            # next is created: a plug that is correct for an account's first
            # character and wrong for the rest was green when this measured
            # `ids[0]` alone.  See `tests/pf_birth_state.py`.
            self.births.append(birth_state.measure_birth_typed_state(
                store, character.id))
            ids.append(character.id)
        # ... and again at the end, because creating character N+1 is exactly
        # when a plug with a missing `WHERE id` rewrites character N.
        self.assertEqual(birth_state.measure_every_birth(store, ids),
                         self.births,
                         "creating a character changed an earlier "
                         "character's birth state")
        self.birth = self.births[0]
        birth_state.clear_vitals_to_pre_seed(self.path, ids)
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
        later = _columns_written_by_migrations_after_007()
        for column in before:
            if column not in SEEDED and column not in later:
                self.assertEqual(after[column], before[column], column)
        for column, value in later.items():
            self.assertEqual(
                after[column], value,
                "%s is excused here as a later migration's column, but the row "
                "does not hold that migration's own value (%r) -- the "
                "exclusion is covering something it was not opened for"
                % (column, value))

    def test_every_other_typed_column_is_still_null(self):
        self._make(["SeedTwo"])
        self._apply_007()
        row = self._rows()[0]
        later = _columns_written_by_migrations_after_007()
        self.assertEqual(set(later) & set(SEEDED), set(),
                         "a later migration re-writes one of 007's three")
        for column in typed.TYPED_COLUMNS:
            if column in SEEDED:
                continue
            if column in later:
                self.assertEqual(row[column], later[column], column)
                continue
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
        # NAMED `from_player_wire` AND NOW ACTUALLY FROM `player_wire`.  The
        # HP pair here was two hand-typed `100`s under that name, which was
        # already a fourth spelling of the number and became a false one the
        # moment the login-vitals seam turned the composer's literals into
        # parameters (`pf-adversary` defect D5, round `mgyoob`).
        from_player_wire = (
            self.legacy.u16tag(0x12, player_wire.PLAYER_LOGIN_LEVEL)
            + self.legacy.u32tag(0x14, player_wire.PLAYER_LOGIN_HP_CURRENT)
            + self.legacy.u32tag(0x14, player_wire.PLAYER_LOGIN_HP_MAX)
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
        # !! THE HP PAIR IS NO LONGER WRITTEN DOWN IN THAT BODY, AND READING
        # IT AS A LITERAL WAS THE TRAP THIS FILE HAD LEFT FOR ITS OWN LANE.
        # `COO-DECISION 20260903_0647` landed the login-vitals seam, which
        # turned the two inline `u32tag(0x14, 100)` calls into two keyword
        # PARAMETERS -- exactly the change this lane's own CORE-REQUEST asked
        # for -- so a `body.count(...) == 2` would have failed the round that
        # did what it asked.  What the migration's provenance claim actually
        # needs is that the composer still EMITS the seeded numbers when
        # nobody hands it others, and that is now read off the signature's
        # defaults (derived, never copied: a default that drifts moves this
        # assertion with it) and by the emission naming those parameters.
        # 🔴 NO FRAME IS COMPOSED HERE, and an earlier draft of this comment
        # said one was (`pf-adversary` defect D5).  The neighbour at
        # `test_those_bytes_really_are_the_ones_the_login_frame_carries` does
        # compose one -- with the DEFAULTS, so its two HP tags are identical
        # and it cannot tell the pair apart either.  Which of the two
        # `u32tag(0x14, ...)` is `hp_current` is not settled by anything in
        # this file, and round `mgyoob` raised it as an open question rather
        # than letting two wire-layer assertions agreeing pass for proof.
        import inspect
        defaults = inspect.signature(
            player_wire._make_actor_attr_with_name_and_class).parameters
        self.assertEqual(defaults["hp_current"].default, SEEDED["hp_current"])
        self.assertEqual(defaults["hp_max"].default, SEEDED["hp_max"])
        self.assertIn("legacy.u32tag(0x14, hp_current)", body)
        self.assertIn("legacy.u32tag(0x14, hp_max)", body)
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

    HOW THESE TESTS BEHAVE WHEN IT IS CLOSED, because it changed this round
    and the change is a real weakening if read carelessly.  The first version
    asserted flatly that a character born after 007 has NULL vitals.  That was
    true when it was written and it is a LANDMINE: `COO-DECISION 20260902_0443`
    point 1 ordered the write at creation, the plug is three columns in
    `SQLiteStore.create_character` and belongs to chief -- so the day chief
    lands the thing COO ordered, a test in THIS lane's file goes red inside
    HIS pull request, over a file he may not edit.  A lane does not get to
    leave that in another lane's path.

    So these MEASURE which of two adjudicated states the repository is in
    instead of asserting one of them, and both branches assert something that
    can fail:

    * not plugged -- all three columns absent, `require()` refuses, and the
      fresh-install census reads zero.  Exactly the old claim.
    * plugged -- all three present and EQUAL to
      `persistence_vitals.new_character_vitals()`, `require()` succeeds, and
      no other typed column came with them.

    A partial seed, a different number, or a value this lane's own front door
    refuses fails in BOTH branches, which is the property that matters: the
    only thing that stopped being graded is WHICH of the two, and that is
    reported by `test_which_state_this_repository_is_in_is_reported`.
    """

    def _newborn(self, tag="after-007"):
        """A character created on the FULL migration set, and what it holds."""
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account(tag)
        character = store.create_character(
            account_id, "Newborn", "newborn", "fingerprint-newborn",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        return store, character.id, store.read_typed_attributes(character.id)

    def test_a_character_created_after_007_holds_nothing_or_the_birth_values(self):
        store, character_id, stored = self._newborn()
        present = [column for column in SEEDED if column in stored]
        if not present:
            # 007 seeded a cohort and this character was not in it.
            with self.assertRaises(vitals.VitalsError):
                store.read_character_vitals(character_id).require()
            return
        # chief's plug (COO-DECISION 20260902_0443 point 1) has landed.
        self.assertEqual(sorted(present), sorted(SEEDED),
                         "a PARTIAL birth seed: %r" % (stored,))
        birth = vitals.new_character_vitals()
        self.assertEqual({c: stored[c] for c in SEEDED}, birth)
        state = store.read_character_vitals(character_id).require()
        self.assertEqual(
            (state.level, state.hp_current, state.hp_max),
            (birth["level"], birth["hp_current"], birth["hp_max"]))

    def _second_birth(self, first_vitals=None):
        """Create TWO characters on one account and return both rows.

        The hole a `pf-adversary` pass drove through the first version of this
        class: every test created exactly ONE character and never looked at
        another row, so a plug whose UPDATE was missing its `WHERE id=?` --
        or carried `WHERE account_id=?`, or fired only for `selector == 0` --
        passed all seven tests.  Measured, with the `account_id` variant
        actually installed: a veteran at `level 9, hp 480/500` came out of the
        NEXT character's creation at `1, 100/100`.  A silent reset of a real
        player's character, green.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("two-births")
        first = store.create_character(
            account_id, "Veteran", "veteran", "fingerprint-veteran",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        if first_vitals is not None:
            store.write_typed_attributes(first.id, dict(first_vitals))
        before = store.read_typed_attributes(first.id)
        second = store.create_character(
            account_id, "Rookie", "rookie", "fingerprint-rookie",
            _build_wire, Position(3, 0, 4.0, 5.0, 6.0, heading=0.0))
        return (store, before,
                store.read_typed_attributes(first.id),
                store.read_typed_attributes(second.id))

    def _retried_birth(self, first_vitals):
        """Create ONE character, level it up, then create it AGAIN with the
        SAME fingerprint -- the retransmitted-create-packet path.

        *** THE SECOND DOOR INTO THE SAME ROOM.  `_second_birth` above closed
        the door where creating character N+1 damages character N, and its
        docstring names the damage exactly: "a veteran at `level 9, hp
        480/500` came out of the NEXT character's creation at `1, 100/100`".
        `SQLiteStore.create_character` has a SECOND way to reach an existing
        character -- the `create_fingerprint` retry branch, which returns the
        character that already exists instead of making a second one, and
        which exists for a retransmitted create packet from a lagging or
        reconnecting client.  Nothing in this file looked at it.

        Measured, on `main` at `064d9e37`, with a plug that is correct in
        every way `_second_birth` checks (right values, right function, right
        `WHERE id`) and that ALSO seeds on the retry branch:

            veteran before duplicate create: level 9, hp 480/500
            veteran AFTER  duplicate create: level 1, hp 100/100

        `pytest` over this lane's four files: **230 passed, 0 failed**.  A
        real player's character silently reset to a newborn by a repeated
        packet, and the whole lane green.  Found by a `pf-adversary` pass on
        LANE-DB round `5w9ly0`.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        account_id = store.ensure_account("retried-birth")
        home = Position(3, 0, 1.0, 2.0, 3.0, heading=0.0)
        first = store.create_character(
            account_id, "Veteran", "veteran", "fingerprint-veteran",
            _build_wire, home)
        store.write_typed_attributes(first.id, dict(first_vitals))
        before = store.read_typed_attributes(first.id)
        again = store.create_character(
            account_id, "Veteran", "veteran", "fingerprint-veteran",
            _build_wire, home)
        return store, first, again, before, store.read_typed_attributes(first.id)

    def test_a_repeated_create_returns_the_same_row_and_changes_nothing(self):
        """The retry door, closed.

        Two assertions, and both are needed: that the repeat did not make a
        second character -- the store's existing promise, without which the
        second half would be vacuous -- and that it did not rewrite the
        vitals of the character it returned.  The count is taken by raw SQL
        rather than through the store, so the reader being graded is not the
        reader supplying the evidence.
        """
        veteran = {"level": 9, "hp_current": 480, "hp_max": 500}
        _store, first, again, before, after = self._retried_birth(veteran)
        self.assertEqual(again.id, first.id)
        with raw_rows(self.path) as db:
            live = db.execute(
                "SELECT COUNT(*) FROM characters WHERE deleted_at IS NULL"
            ).fetchone()[0]
        self.assertEqual(live, 1)
        for column, value in veteran.items():
            self.assertEqual(before.get(column), value, column)
            self.assertEqual(
                after.get(column), value,
                "a repeated create with the same fingerprint rewrote %s of an "
                "EXISTING character from %r to %r.  The retry branch of "
                "create_character returns a character that already exists; it "
                "must not seed it as if it were being born."
                % (column, value, after.get(column)),
            )

    def test_a_repeated_create_changes_no_row_in_any_table(self):
        """*** THE PROPERTY THE RETRY DOOR ACTUALLY NEEDS, and the one the
        test above walks past on every column it does not name.

        `test_a_repeated_create_returns_the_same_row_and_changes_nothing`
        grades ONE row, THREE columns, inside ONE account.  A `pf-adversary`
        pass measured what that leaves open on the retry branch, with the
        plugs installed rather than imagined, and every one of these was
        GREEN at `7243 passed, 323 skipped` -- the identical figure the round
        that added the narrow test offered as its evidence of a clean tree:

        * a retry plug that also resets every OTHER account's veteran to
          `1, 100/100` and moves every character 1000 units in `z`
        * a retry plug that also stamps `speed_walk`, `cash` and `experience`
          -- the first of which is the very column
          `COO-DECISION 20260902_1043` ruled must NOT be written at birth
        * a retry plug using `COALESCE(col, ?)`, the defensible "only fill
          what is NULL" shape, which turns a raw `level 9, hp_max 500,
          hp_current NULL` row into `hp 100/500` -- exactly the outcome
          `MigrationIsNarrowTests` forbids for 007 itself

        So the rule is stated the only way that covers them, and on this door
        it is both STRONGER and SIMPLER than the birth-door version: a
        repeated create returns a character that already exists, so it adds
        no rows either.  The whole database must come back BYTE-FOR-BYTE
        identical -- not "no row was lost", but "nothing changed at all".

        The world is built to have something to lose, and deliberately
        outside the retried account: a second account's veteran, a
        soft-deleted row, positions and backpacks for everyone, a
        `speed_walk` no store method would rewrite, and one half-filled HP
        pair set by raw SQL so the COALESCE shape has a NULL to find.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        mine = store.ensure_account("retry-mine")
        theirs = store.ensure_account("retry-theirs")

        # EVERY CREATION FIRST, EVERY DISTINGUISHING VALUE AFTERWARDS -- the
        # same interval bug the birth-door test above documents: a plug whose
        # damage lands before the `before` dump is taken looks like a no-op.
        retried = store.create_character(
            mine, "Retried", "retried", "fingerprint-retry-subject",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        neighbour = store.create_character(
            theirs, "Neighbour", "neighbour", "fingerprint-retry-neighbour",
            _build_wire_offset(0x60000001),
            Position(3, 0, 4.0, 5.0, 6.0, heading=0.0))
        doomed = store.create_character(
            mine, "Doomed", "doomed", "fingerprint-retry-doomed",
            _build_wire_offset(0x70000001),
            Position(3, 0, 7.0, 8.0, 9.0, heading=0.0))
        sid = store.open_session(mine)
        store.soft_delete_character(sid, doomed.selector)

        store.write_typed_attributes(
            retried.id, {"level": 9, "hp_current": 480, "hp_max": 500,
                         "speed_walk": 620.5, "experience": 123456,
                         "cash": 99999})
        store.write_typed_attributes(
            neighbour.id, {"level": 7, "hp_current": 210, "hp_max": 300,
                           "speed_walk": 380.25})
        self._set(doomed.id, level=4, hp_current=40, hp_max=60)
        self._set(retried.id, avatar_typed_json='{"lane":"db"}')
        # a HALF-FILLED pair, written by raw SQL because no store method will
        # leave one: this is the NULL a `COALESCE` retry plug fills in.
        self._set(neighbour.id, hp_current=None)

        before = self._dump_every_table()
        self.assertTrue(any(before[t] for t in
                            ("characters", "character_positions",
                             "character_backpacks")),
                        "the world this test is about was never built")

        again = store.create_character(
            mine, "Retried", "retried", "fingerprint-retry-subject",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        # load-bearing: without this the equality below could hold because
        # the retry branch was never taken at all.
        self.assertEqual(again.id, retried.id)

        after = self._dump_every_table()
        self.assertEqual(sorted(after), sorted(before),
                         "a table appeared or vanished")
        for table in sorted(before):
            self.assertEqual(
                before[table], after[table],
                "a repeated create with the same fingerprint CHANGED table "
                "`%s`.  The retry branch returns a character that already "
                "exists: it adds nothing and it may not rewrite a single row "
                "in any table, including rows of accounts and characters "
                "nobody was creating.  before=%r after=%r"
                % (table, before[table], after[table]),
            )

    def test_creating_a_character_does_not_touch_any_other_row(self):
        """The veteran-reset defect, as the test that fails on it.

        This is the one that matters for the owner's data: whatever the birth
        write turns out to be, creating character N+1 may not change the
        vitals of character N.  Graded on a row that HOLDS values, because a
        row holding NULL cannot show a reset.
        """
        veteran = {"level": 9, "hp_current": 480, "hp_max": 500}
        _store, before, after, _newborn = self._second_birth(veteran)
        for column, value in veteran.items():
            self.assertEqual(before.get(column), value, column)
            self.assertEqual(
                after.get(column), value,
                "creating another character changed an EXISTING character's "
                "%s from %r to %r -- a birth write reached a row that is not "
                "the newborn's" % (column, value, after.get(column)),
            )

    def test_every_character_is_born_the_same_way_not_only_the_first(self):
        """The same hole from the other side: a plug that fires only for an
        account's FIRST character (`selector == 0`) leaves every later
        character unseeded forever, and a class that creates one character per
        test never sees it."""
        _store, first_at_birth, _after, second_at_birth = self._second_birth()
        self.assertEqual(
            sorted(column for column in SEEDED if column in first_at_birth),
            sorted(column for column in SEEDED if column in second_at_birth),
            "an account's second character is born in a DIFFERENT state from "
            "its first (first=%r, second=%r)"
            % (first_at_birth, second_at_birth),
        )

    def _dump_every_table(self):
        """Every row of every table, as comparable tuples."""
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            names = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            return {
                name: sorted(
                    tuple((k, r[k]) for k in r.keys())
                    for r in db.execute("SELECT * FROM %s" % name)
                )
                for name in names
            }
        finally:
            db.close()

    def test_creating_a_character_changes_no_row_that_already_existed(self):
        """*** THE PROPERTY THE OWNER'S DATA ACTUALLY NEEDS, and the one four
        separate wrong plugs walked past.

        `test_creating_a_character_does_not_touch_any_other_row` above checks
        the three VITALS of one live veteran.  A `pf-adversary` pass measured
        what that leaves open, with the plugs installed rather than imagined:

        * a plug that also runs `UPDATE character_positions SET z = z + 1000`
        * a plug that also blanks every OTHER character's `avatar_typed_json`
        * a plug that also re-seeds every SOFT-DELETED row in the database
        * a plug that also stamps every other character's backpack rows

        All four were green.  None of them is exotic; each is one stray
        statement in the same commit, and each rewrites rows belonging to
        characters nobody was creating.

        So the rule is stated the only way that covers them: creating a
        character may ADD rows, and may not change or remove a single row that
        already existed, in ANY table.  The world here is built to have
        something to lose -- a second account, a veteran holding real vitals,
        a soft-deleted character, positions and backpacks for all of them.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        first = store.ensure_account("world-first")
        second = store.ensure_account("world-second")

        # *** EVERY CREATION FIRST, EVERY DISTINGUISHING VALUE AFTERWARDS.  The
        # first draft of this test interleaved them and two destructive plugs
        # stayed GREEN because of it: a plug that re-seeds soft-deleted rows,
        # and one that blanks other characters' `avatar_typed_json`, had
        # already done their damage BEFORE the `before` dump was taken, so the
        # newborn's creation repeated a write that changed nothing and the
        # subset held.  A test that lets the mutation run before it starts
        # looking is measuring the wrong interval.
        veteran = store.create_character(
            first, "Veteran", "veteran", "fingerprint-world-veteran",
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        doomed = store.create_character(
            first, "Doomed", "doomed", "fingerprint-world-doomed",
            _build_wire, Position(3, 0, 4.0, 5.0, 6.0, heading=0.0))
        stranger = store.create_character(
            second, "Stranger", "stranger", "fingerprint-world-stranger",
            _build_wire_offset(0x40000001),
            Position(3, 0, 7.0, 8.0, 9.0, heading=0.0))
        sid = store.open_session(first)
        store.soft_delete_character(sid, doomed.selector)

        store.write_typed_attributes(
            veteran.id, {"level": 9, "hp_current": 480, "hp_max": 500,
                         "speed_walk": 620.5})
        store.write_typed_attributes(stranger.id, {"level": 2, "cash": 77})
        # the soft-deleted row holds a COMPLETE and distinctive set, so a plug
        # that "helpfully" re-seeds deleted rows changes it visibly
        self._set(doomed.id, level=4, hp_current=40, hp_max=60)
        # a column no store method writes, given a value so that blanking it
        # is a change rather than a no-op
        self._set(veteran.id, avatar_typed_json='{"lane":"db"}')

        before = self._dump_every_table()
        self.assertTrue(any(before[t] for t in
                            ("characters", "character_positions",
                             "character_backpacks")),
                        "the world this test is about was never built")

        store.create_character(
            first, "Newborn", "newborn", "fingerprint-world-newborn",
            _build_wire_offset(0x50000001),
            Position(3, 0, 10.0, 11.0, 12.0, heading=0.0))

        after = self._dump_every_table()
        self.assertEqual(sorted(after), sorted(before), "a table appeared or "
                                                        "vanished")
        for table, rows in before.items():
            missing = [row for row in rows if row not in after[table]]
            self.assertEqual(
                [], missing,
                "creating a character CHANGED OR REMOVED %d row(s) that "
                "already existed in `%s`.  A birth write may add rows; it may "
                "not touch a row belonging to a character nobody was "
                "creating.  First one: %r" % (len(missing), table,
                                              missing[0] if missing else None),
            )

    def test_a_newborn_is_not_stamped_as_having_been_modified(self):
        """The fifth plug that walked past everything else: correct values,
        plus `updated_at` set to something that is not the creation time.

        A character that has only ever been created has not been changed, and
        `migrations/007`'s header states the same rule for a backfill.  An
        operator reading `updated_at` must not see a character that nobody has
        touched claiming otherwise.
        """
        store, character_id, _stored = self._newborn("stamp")
        del store
        db = sqlite3.connect(self.path)
        try:
            created, updated = db.execute(
                "SELECT created_at, updated_at FROM characters WHERE id=?",
                (character_id,)).fetchone()
        finally:
            db.close()
        self.assertEqual(updated, created)

    def test_the_numbers_on_a_newborn_row_came_from_the_call_itself(self):
        """`COO-DECISION 20260902_0443` point 1 is about a MECHANISM, not only
        about three numbers: "ผ่านฟังก์ชันเดียว `new_character_vitals()`" --
        one function, so that the day an RE answers, the value changes in one
        edit in one file.  This is the only test in the repository that
        actually measures it.

        WHAT IT REPLACED, AND WHY.  Two weaker questions were being asked in
        its place, and they are independently satisfiable:

        * "does the row hold 1/100/100" -- `_newborn` and the class around it.
        * "does the source of `store.py` contain a CALL to that name" -- an
          AST predicate this lane added mid-round and a `pf-adversary` pass
          then drove straight through: a `CREATE TRIGGER` installed by a
          migration file, seeding at the schema level (the mechanism point 2
          explicitly forbids), plus NINE LINES OF DEAD CODE in `store.py` that
          call the function and throw the result away, was green across the
          whole 7000-test suite.  The same pass drove a plug that CALLS the
          function, discards its return, and writes `(1, 100, 100)` literals.
          Both hold the right numbers and both name the function; neither
          takes its numbers from it.

        So the question is asked the one way that binds the two: make the
        function return numbers nobody could have typed by accident, and look
        for THOSE on the row.  A trigger returns 1/100/100 and is red here.
        A literal returns 1/100/100 and is red here.

        The patch is applied to the DEFINING module and to every name in
        `store.py`'s globals whose function is CALLED `new_character_vitals`,
        so `import ... as _birth` and `persistence_vitals.
        new_character_vitals()` are both caught, and so is the state left
        behind by a sibling test's `importlib.reload`.  Matching by name
        rather than by identity is not fussiness: both the source-scan
        spelling this replaced AND the first draft of this test produced a
        FALSE RED on a CORRECT plug, which is the landmine this round exists
        to remove rather than re-lay.

        WHAT IT CANNOT SEE, stated rather than left to be found: a plug that
        reaches the function through something whose `__name__` is different
        (a `functools.partial`, a lambda wrapper).  No patch would land, the
        row would hold the real numbers, and this test would accuse a correct
        plug.  That spelling is not a plausible reading of
        `COO-DECISION 20260902_0443` point 1 -- but if it ever appears, the
        failure message is wrong and this docstring is where to look.
        """
        sentinel = {"level": 7, "hp_current": 33, "hp_max": 77}
        self.assertNotEqual(sentinel, vitals.new_character_vitals())

        import pirateforce_foundation.store as store_module

        # *** BY NAME, NOT BY IDENTITY, and the difference is a false red this
        # test produced on the CORRECT plug before it was found.  A sibling
        # test in `tests/test_persistence_vitals.py` calls
        # `importlib.reload(persistence_vitals)`; after that reload
        # `vitals.new_character_vitals` is a NEW function object while
        # `store.py`'s module global still holds the OLD one, so an
        # identity match (`value is real`) finds nothing, the patch reaches
        # nothing, and a perfectly correct plug is accused of taking its
        # numbers from a literal.  It passed alone and failed in the file --
        # exactly the shape of test that lands red inside someone else's
        # pull request.  `__name__` survives a reload and survives
        # `import ... as _birth`, which is the other spelling that has to work.
        def _fake():
            return dict(sentinel)

        aliases = [name for name, value in vars(store_module).items()
                   if callable(value)
                   and getattr(value, "__name__", "") == "new_character_vitals"]
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(
                vitals, "new_character_vitals", _fake))
            for name in aliases:
                stack.enter_context(
                    mock.patch.object(store_module, name, _fake))
            # the patch really took, on every route a plug could use
            self.assertEqual(vitals.new_character_vitals(), sentinel)
            for name in aliases:
                self.assertEqual(getattr(store_module, name)(), sentinel, name)
            _store, _character_id, stored = self._newborn("mechanism")

        if not any(column in stored for column in SEEDED):
            # The plug is not in and the database is below 009; there is no
            # birth write to trace.
            return
        self.assertEqual(
            {column: stored[column] for column in SEEDED}, sentinel,
            "a newborn holds birth vitals, but NOT the ones "
            "new_character_vitals() returned while it was being created -- so "
            "the numbers came from somewhere else (an inline literal, a schema "
            "DEFAULT, or a trigger).  COO-DECISION 20260902_0443 points 1 and "
            "2 rule out all three.  Measured at runtime, not read off source.",
        )

    # WHY THIS IS STILL ONE EQUALITY AFTER `migrations/009`.  An earlier draft
    # of this round widened it into a two-branch acceptance -- sentinel OR the
    # schema defaults -- on the reasoning that `COO-DECISION 20260902_1607`
    # made a DEFAULT a legitimate second source.  A `pf-adversary` pass
    # measured what that cost: it patched `create_character` to write the
    # literals `1, 100, 100` -- the exact third source both decisions forbid --
    # and the widened test PASSED while its own docstring above still said
    # "a literal returns 1/100/100 and is red here".  The widening was
    # unnecessary as well as wrong: chief's insertion point landed on `main`
    # in the same hour (commit `b9e11059`), so `create_character` NAMES the
    # three columns and their values really do come from the call.  The
    # DEFAULT for those three is a backstop no creation path reaches, and the
    # one column 009 alone supplies -- `speed_walk` -- is not in `SEEDED` and
    # is graded next door in `test_persistence_birth_defaults_009.py`.

    def test_a_birth_seed_may_not_carry_any_other_typed_column(self):
        """The seventeen columns with no adjudicated value hold nothing.

        This used to be eighteen: `COO-DECISION 20260901_1447` point 2 kept
        `speed_walk` out of a birth as well, until `RE-194` settled the number
        and `COO-DECISION 20260902_1607` made it one of the four
        `migrations/009_character_birth_defaults.sql` supplies.  The rule the
        test enforces is unchanged and is the owner's own (`COO-DECISION
        20260901_1059`): a column whose value nobody has measured is never
        guessed -- it stays NULL and reaches the compose gate as absent.
        """
        _store, _character_id, stored = self._newborn("no-extras")
        unadjudicated = [column for column in typed.TYPED_COLUMNS
                         if column not in birth_state.BIRTH_COLUMNS]
        self.assertEqual(len(unadjudicated), 17)
        for column in unadjudicated:
            self.assertNotIn(column, stored, column)

    def test_the_birth_values_are_the_same_three_007_wrote(self):
        """Whatever the plug's state, the two seeds may not disagree: a
        character born tomorrow and one 007 wrote today have to be the same
        kind of character.  Derived from 007's SQL text, not from a constant
        this test also uses for the other side."""
        sql = MIGRATION_007.read_text(encoding="utf-8")
        from_007 = {}
        for statement in _statements(sql):
            for column, value in re.findall(
                    r"\b(level|hp_current|hp_max)\s*=\s*(\d+)", statement):
                if "SET" in statement.split(column)[0].upper():
                    from_007[column] = int(value)
        self.assertEqual(from_007, SEEDED, from_007)
        self.assertEqual(vitals.new_character_vitals(), from_007)

    def test_the_birth_label_is_the_same_string_007_carries(self):
        """`COO-DECISION 20260902_0443` point 1 requires the SAME label as
        007.  Graded against 007's own bytes so the two cannot drift."""
        self.assertIn(
            vitals.NEW_CHARACTER_VITALS_LABEL,
            MIGRATION_007.read_text(encoding="utf-8"),
        )
        self.assertEqual(vitals.NEW_CHARACTER_VITALS_LABEL,
                         REQUIRED_HEADER_TAG)

    def test_on_a_fresh_install_the_census_counts_only_what_is_written(self):
        """The sentence a round file must never write about a fresh install:
        "007 applied, every character seeded".  007 runs against an empty
        table there and seeds nothing at all; the only vitals a fresh install
        can hold are the ones a birth write puts there."""
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertIsNone(store.migrate_with_backup(
            backups_root=self.root / "backups"))
        account_id = store.ensure_account("fresh")
        character = store.create_character(
            account_id, "Fresh", "fresh", "fingerprint-fresh", _build_wire,
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        del character
        census = store.vitals_seeding_census()
        self.assertEqual(census["characters_any"], 1)
        # Graded against RAW SQL, not against `read_typed_attributes`.  The
        # first version derived what to expect by reading back the same row
        # the census had just counted, which a `pf-adversary` pass called
        # correctly: once a plug lands that can only ever prove the census and
        # the read path agree with each other, never that either is right.
        # `sqlite3` on the file is an oracle neither of them can influence.
        with raw_rows(self.path) as db:
            for column in SEEDED:
                expected = db.execute(
                    "SELECT COUNT(*) FROM characters WHERE %s IS NOT NULL"
                    % column).fetchone()[0]
                self.assertEqual(
                    census["%s_seeded_any" % column], expected, column)

    def test_the_census_counts_a_zero_level_as_seeded_though_it_is_unusable(self):
        """A caveat a round file must not lose, found by a `pf-adversary`
        pass: from `COO-DECISION 20260902_0443` point 4, "seeded" and "usable"
        are two different numbers, and only the first one is in the census.

        `vitals_seeding_census` counts NOT NULL, so a row at `level = 0`
        counts as seeded while `resolve(...).require()` refuses it.  That is
        the right behaviour for a census -- it reports what is on disk -- but
        a round file quoting `level_seeded_any` as "characters M4 can use" is
        quoting the wrong number.
        """
        ids = self._make(["ZeroLevel"])
        self._set(ids[0], level=0, hp_current=100, hp_max=100)
        store = SQLiteStore(self.path, self.older)
        census = store.vitals_seeding_census()
        self.assertEqual(census["level_seeded_any"], 1)
        with self.assertRaises(vitals.VitalsError):
            store.read_character_vitals(ids[0]).require()

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
