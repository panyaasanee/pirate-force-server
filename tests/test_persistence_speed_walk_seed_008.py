"""LANE-DB / M4: ``migrations/008_character_speed_walk_seed.sql`` -- the one
column ``COO-DECISION 20260901_1447`` point 2 held back, and the four things
``COO-DECISION 20260902_0742`` attached to letting it go.

The held-back column was ``speed_walk``.  Point 2 refused BOTH candidates --
150.0 (`tests/test_npc_gait_wire.py`'s `PROVEN_WALK_SPEED`) and 400.0 (the
client construction default) -- on the ground that "both numbers are equally a
guess without" an RE answer.  RE-194 (`pf_bridge/notes_to_chief/
20260902_0501_RE-194-RESULT-PLAYER-FRESH-DEFAULT-400-NPC150-IS-WIRE.md`)
answered it, and `COO-DECISION 20260902_0742` lifted the hold for the STORE
and for nothing else.  What is measured here, condition by condition:

1. ``MigrationShapeTests`` -- 007's shape exactly (point 1): one statement,
   ``WHERE speed_walk IS NULL``, no other column named, no row that already
   holds a value touched.  Read off the file's real statements.
2. ``HeaderTagTests`` -- the header carries the decision's label VERBATIM,
   including the second half (point 2), which is the half that says the number
   is not cleared for the wire.
3. ``MigrationIsNarrowTests`` -- real rows, the real migration, compared field
   by field: an existing value survives, every other typed column stays NULL,
   and no other table moves a byte.
4. ``NothingSendsItTests`` -- point 4: no code reads this column off a row to
   put it on the wire on the strength of this file.  Scanned, not promised.
5. ``BootSnapshotProtects008Tests`` -- ``COO-DECISION 20260901_1112`` point 3
   for a SECOND row-touching file: the real ``migrate_with_backup`` over the
   real directory, and the pre-008 database restored out of what it leaves.

And one property that is neither a condition nor visible from the SQL:
``Float32Tests`` -- 400.0 survives the round trip through a SQLite REAL and
through ``as_f32`` unchanged, so the column and the wire cannot disagree about
the number the header claims was measured.
"""
import ast
import re
import shutil
import sqlite3
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_attr_compose as compose  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MIGRATION_008 = MIGRATIONS / "008_character_speed_walk_seed.sql"

#: The one column and the one value.  Derived nowhere else in this file.
SEEDED_COLUMN = "speed_walk"
SEEDED_VALUE = 400.0

#: `COO-DECISION 20260902_0743` point 3, verbatim.  007's header may never be
#: edited (`COO-DECISION 20260902_0250` point 3) and the decision chose THIS
#: file over a file of its own, so if it is not here it is nowhere -- and 008
#: may not be edited afterwards either.  A `pf-adversary` pass found it
#: missing: the round had read the decision that granted permission and not
#: the one that imposed a chore, because the mailbox grep matched
#: `ADDRESSEE: LANE-DB` and `0743` is addressed to chief with LANE-DB in cc.
REQUIRED_007_ERRATA = (
    "007 header: SeedsACohortNotADatabaseTests now accepts both pre/post "
    "create-plug states; the 'seeds a cohort, not a database' sentence "
    "remains true of 007's own effect"
)

#: `COO-DECISION 20260902_0742` point 2, verbatim.  Both halves: the second is
#: the one that keeps a reader from taking the first as a licence to send it.
REQUIRED_HEADER_TAG = (
    "MEASURED from client BasicAttr constructor (RE-194) -- "
    "VA 0x00464AF2 -- STORE ONLY, not a send value"
)


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


def _build_wire_for(base):
    """A wire builder whose identity does not collide with `_build_wire`'s.

    `004_character_soft_delete_reuse.sql` puts a partial UNIQUE index on
    `(identity_lo, identity_hi)`, so a second ACCOUNT whose selectors also
    start at zero would hand out an identity the first account already holds.
    """
    def build(selector):
        return b"wire", b"avatar", base + selector, 0
    return build


def _statements(sql: str) -> list[str]:
    """The migration's real statements, with `--` comment lines removed."""
    body = "\n".join(
        line for line in sql.splitlines() if not line.lstrip().startswith("--")
    )
    return [s.strip() for s in body.split(";") if s.strip()]


class HeaderTagTests(unittest.TestCase):
    def setUp(self):
        self.sql = MIGRATION_008.read_text(encoding="utf-8")

    def test_the_header_carries_the_decision_s_label_verbatim(self):
        self.assertIn(REQUIRED_HEADER_TAG, self.sql)

    def test_the_label_names_the_measured_address_and_the_re(self):
        self.assertIn("0x00464AF2", self.sql)
        self.assertIn("RE-194", self.sql)

    def test_the_second_half_of_the_label_is_not_droppable(self):
        """`COO-DECISION 20260902_0742` point 2: "บรรทัดหลังต้องอยู่".  A header
        that kept only "MEASURED from client BasicAttr constructor" would read
        as a clearance to send 400.0, which RE-194's own BUILD_IMPACT
        explicitly refuses."""
        self.assertIn("STORE ONLY, not a send value", self.sql)

    def test_the_007_errata_line_is_carried_verbatim(self):
        """`COO-DECISION 20260902_0743` point 3."""
        self.assertIn(REQUIRED_007_ERRATA, self.sql)

    def test_the_errata_is_on_one_line_the_way_the_decision_wrote_it(self):
        """A line broken across two `--` comments would satisfy `assertIn`
        only by accident of whitespace; it does not here, and a reader
        grepping 007's class name must land on one readable sentence."""
        carriers = [line for line in self.sql.splitlines()
                    if REQUIRED_007_ERRATA in line]
        self.assertEqual(len(carriers), 1, carriers)
        self.assertTrue(carriers[0].lstrip().startswith("--"), carriers[0])

    def test_the_file_is_ascii_and_cp874_safe(self):
        """`gate-windows.yml`'s tripwire does not scan `migrations/`; what
        reads this file under a Thai-locale console is a person and a boot's
        traceback, so the house rule is enforced here instead."""
        self.sql.encode("ascii")
        self.sql.encode("cp874")


class MigrationShapeTests(unittest.TestCase):
    """Condition 1: 007's shape, read off the statements SQLite would run."""

    def setUp(self):
        self.statements = _statements(
            MIGRATION_008.read_text(encoding="utf-8"))

    def test_it_is_one_update_and_nothing_else(self):
        self.assertEqual(len(self.statements), 1, self.statements)
        self.assertTrue(self.statements[0].upper().startswith("UPDATE "))

    def test_it_never_inserts_deletes_drops_or_alters(self):
        for verb in ("INSERT", "DELETE", "DROP", "ALTER", "CREATE"):
            for statement in self.statements:
                self.assertNotIn(verb, statement.upper(), statement)

    def test_it_touches_only_rows_that_hold_nothing(self):
        where = self.statements[0].upper().split(" WHERE ", 1)[1]
        self.assertEqual(where.strip().rstrip(";"), "SPEED_WALK IS NULL")

    def test_the_only_column_written_is_speed_walk(self):
        assignments = (self.statements[0].split(" SET ", 1)[1]
                       .split(" WHERE ", 1)[0])
        written = {part.split("=")[0].strip()
                   for part in assignments.split(",")}
        self.assertEqual(written, {SEEDED_COLUMN})

    def test_no_other_typed_column_is_named_by_the_statement(self):
        for column in typed.TYPED_COLUMNS:
            if column == SEEDED_COLUMN:
                continue
            self.assertNotIn(column, self.statements[0], column)

    def test_the_value_written_is_the_measured_one(self):
        self.assertIn("400.0", self.statements[0])

    def test_it_does_not_stamp_updated_at(self):
        self.assertNotIn("updated_at", self.statements[0])

    def test_the_column_it_writes_is_one_006_really_built(self):
        """Not a name this file invented: 006's own text has to carry it."""
        six = (MIGRATIONS / typed.MIGRATION_FILE).read_text(encoding="utf-8")
        self.assertIn(SEEDED_COLUMN, six)
        self.assertIn(SEEDED_COLUMN, typed.TYPED_COLUMNS)


class _MigratedWorkspace(unittest.TestCase):
    """Run 001..007, put real rows in, THEN run the full directory."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.older = self.root / "migrations_upto_007"
        self.older.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if int(path.name[:3]) < 8:
                shutil.copy2(path, self.older / path.name)
        self.path = self.root / "state.sqlite3"
        self.births = []

    def _make(self, names):
        """Characters on the pre-008 schema, with `speed_walk` unset.

        The birth state is MEASURED (and refused unless it is one this lane
        accepts) before anything is cleared -- see `tests/pf_birth_state.py`
        for why every fixture in this lane does that rather than assuming a
        newly created character holds nothing.  `speed_walk` is never part of
        a birth state, so nothing is cleared for it; the vitals are, so that
        these rows are the same pre-seed rows 007's file works on.
        """
        store = SQLiteStore(self.path, self.older)
        store.migrate()
        account_id = store.ensure_account("speed-walk-008")
        home = Position(3, 0, 11.0, 22.0, 33.0, heading=1.5)
        ids = []
        for name in names:
            character = store.create_character(
                account_id, name, name.lower(),
                "fingerprint-008-%s" % name.lower(), _build_wire, home,
            )
            # EVERY character, not only the first -- see the same correction
            # in `tests/test_persistence_vitals_seed_007.py::_make` and the
            # measurement behind it in `tests/pf_birth_state.py`.
            birth = birth_state.measure_birth_typed_state(store, character.id)
            self.assertNotIn(
                SEEDED_COLUMN, birth,
                "a birth state carrying speed_walk would mean 008 has "
                "nothing left to seed AND that COO-DECISION 20260901_1447 "
                "point 2 was overtaken somewhere this file cannot see")
            self.births.append(birth)
            ids.append(character.id)
        self.assertEqual(birth_state.measure_every_birth(store, ids),
                         self.births,
                         "creating a character changed an earlier "
                         "character's birth state")
        self.birth = self.births[0]
        return ids

    def _rows(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            rows = db.execute(
                "SELECT * FROM characters ORDER BY id").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()

    def _apply_008(self):
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

    def _dump_tables(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        try:
            names = [r[0] for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            dump = {}
            for name in names:
                if name in ("characters", "schema_migrations"):
                    continue
                dump[name] = [
                    {k: r[k] for k in r.keys()}
                    for r in db.execute(
                        "SELECT * FROM %s ORDER BY rowid" % name)
                ]
            return dump
        finally:
            db.close()


class MigrationIsNarrowTests(_MigratedWorkspace):
    """Condition 3: real rows, real migration, compared field by field."""

    def test_a_row_holding_no_speed_gets_exactly_the_one_value(self):
        self._make(["SeedOne"])
        before = self._rows()[0]
        self.assertIsNone(before[SEEDED_COLUMN])
        self._apply_008()
        after = self._rows()[0]
        self.assertEqual(after[SEEDED_COLUMN], SEEDED_VALUE)
        for column in before:
            if column != SEEDED_COLUMN:
                self.assertEqual(after[column], before[column], column)

    def test_a_row_that_already_holds_a_speed_keeps_its_exact_bytes(self):
        """The point of `WHERE speed_walk IS NULL`.  `620.5` is chosen because
        it is exactly representable in f32, so a change would be a real change
        and not a rounding artefact."""
        ids = self._make(["Sprinter"])
        self._set(ids[0], speed_walk=620.5)
        self._apply_008()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], 620.5)

    def test_a_row_holding_zero_speed_is_not_overwritten(self):
        """Zero is a value, not an absence.  A predicate written
        `WHERE speed_walk IS NULL OR speed_walk = 0` -- or one relying on
        falsiness anywhere above SQL -- would silently adjudicate it, and the
        owner's rule is about exactly that kind of silent zero."""
        ids = self._make(["Rooted"])
        self._set(ids[0], speed_walk=0.0)
        self._apply_008()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], 0.0)

    def test_the_seeded_and_the_untouched_row_sit_side_by_side(self):
        ids = self._make(["Fresh", "Sprinter"])
        self._set(ids[1], speed_walk=620.5)
        self._apply_008()
        rows = self._rows()
        self.assertEqual(rows[0][SEEDED_COLUMN], SEEDED_VALUE)
        self.assertEqual(rows[1][SEEDED_COLUMN], 620.5)

    def test_every_other_typed_column_is_untouched_by_008(self):
        """Compared against the row as it stood BEFORE 008, not against NULL:
        007 runs in the same `migrate()` call and seeds three columns, so a
        test that demanded NULL everywhere would be measuring 007."""
        self._make(["Others"])
        before = self._rows()[0]
        self._apply_008()
        after = self._rows()[0]
        for column in typed.TYPED_COLUMNS:
            if column == SEEDED_COLUMN:
                continue
            if column in vitals.VITAL_COLUMNS:
                continue  # 007's three, seeded by the same migrate() call
            self.assertEqual(after[column], before[column], column)
            self.assertIsNone(after[column], column)

    def test_a_soft_deleted_row_is_seeded_like_any_other(self):
        ids = self._make(["Gone"])
        db = sqlite3.connect(self.path)
        try:
            db.execute("UPDATE characters SET deleted_at='x' WHERE id=?",
                       (ids[0],))
            db.commit()
        finally:
            db.close()
        self._apply_008()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], SEEDED_VALUE)

    def test_other_tables_are_byte_identical_across_the_migration(self):
        self._make(["Untouched"])
        before = self._dump_tables()
        self._apply_008()
        after = self._dump_tables()
        self.assertTrue(before, "no other tables were compared at all")
        for table in before:
            self.assertEqual(after[table], before[table], table)

    def test_008_is_recorded_in_the_ledger_and_re_running_is_a_no_op(self):
        ids = self._make(["Ledger"])
        self._apply_008()
        self.assertIn(8, self._applied_versions())
        self._set(ids[0], speed_walk=None)
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertIsNone(
            self._rows()[0][SEEDED_COLUMN],
            "008 ran a second time: the checksum ledger did not stop it",
        )

    def test_it_seeds_a_cohort_and_not_the_database(self):
        """The limitation the header states, kept as a measurement so the
        sentence in the round file cannot drift from the code.

        A character created AFTER 008 has run holds no speed, and
        `create_character` cannot give it one:
        `persistence_vitals.new_character_vitals()` is forbidden from carrying
        a fourth column, so the insertion point of `COO-DECISION 20260902_0444`
        closes the cohort gap for the three vitals and not for this column.
        """
        self._make(["Before"])
        self._apply_008()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], SEEDED_VALUE)
        store = SQLiteStore(self.path, MIGRATIONS)
        later = store.create_character(
            store.ensure_account("after-008"), "After", "after",
            "fingerprint-after-008", _build_wire_for(0x30000001),
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        self.assertNotIn(
            SEEDED_COLUMN, store.read_typed_attributes(later.id))
        self.assertNotIn(SEEDED_COLUMN, vitals.new_character_vitals())


class Float32Tests(_MigratedWorkspace):
    """The number in the column is the number the header measured."""

    def test_the_seeded_value_survives_the_column_and_as_f32(self):
        ids = self._make(["Precision"])
        self._apply_008()
        store = SQLiteStore(self.path, MIGRATIONS)
        stored = store.read_typed_attributes(ids[0])[SEEDED_COLUMN]
        self.assertEqual(stored, SEEDED_VALUE)
        self.assertEqual(typed.as_f32(stored), SEEDED_VALUE)

    def test_the_seeded_value_is_the_f32_re_194_read_out_of_the_image(self):
        """RE-194 quotes the literal's four bytes: `00 00 C8 43`.  Decoded
        here rather than trusted, so "400.0" in the header and the bytes in
        the client image are the same number."""
        import struct
        self.assertEqual(
            struct.unpack("<f", bytes([0x00, 0x00, 0xC8, 0x43]))[0],
            SEEDED_VALUE,
        )

    def test_the_seeded_value_is_one_the_column_would_accept_anyway(self):
        """008 must not put a value into the row that this lane's own
        validator would refuse on the way back out."""
        self.assertEqual(typed.validate(SEEDED_COLUMN, SEEDED_VALUE),
                         SEEDED_VALUE)

    def test_the_stored_speed_closes_exactly_the_x_7_gap(self):
        ids = self._make(["Gap"])
        store_before = SQLiteStore(self.path, self.older)
        values_before = {typed.TYPED_COLUMNS[c].x: v for c, v in
                         store_before.read_typed_attributes(ids[0]).items()}
        gaps_before = {g.x for g in compose.block_gaps(values_before)}
        self.assertIn(7, gaps_before)

        self._apply_008()
        store = SQLiteStore(self.path, MIGRATIONS)
        values = {typed.TYPED_COLUMNS[c].x: v for c, v in
                  store.read_typed_attributes(ids[0]).items()}
        self.assertEqual(values[7], SEEDED_VALUE)
        gaps_after = {g.x for g in compose.block_gaps(values)}
        self.assertNotIn(7, gaps_after)
        self.assertEqual(gaps_after - gaps_before, set(),
                         "008 OPENED a gap")


class NothingSendsItTests(unittest.TestCase):
    """Condition 4 of `COO-DECISION 20260902_0742`: this file is a STORE.

    Scanned rather than promised.  *** THE FIRST VERSION OF THIS CLASS WAS
    DEFEATED FIVE WAYS by a `pf-adversary` pass and every one of them is
    closed below, named so a reader can check rather than trust:

    A. Raw SQL -- `SELECT speed_walk FROM characters` plus `encode_block()` --
       was skipped before parsing, because the scan first grepped for
       `read_typed_attributes`.  **That is the shape a real implementation
       would take.**  There is no pre-filter now, and a raw read of the column
       counts as a read.
    B. Read in one function, encode in its caller.  The unit was a function;
       it is a FILE now.
    C. Name the offending function `write_typed_attributes_and_compose_sparse`
       anywhere in the tree and be exempted by name.  There is NO exemption
       now, by name or by path: `store.py` was the only candidate and it turns
       out not to need one -- it composes what its caller wrote and never
       reads a row to do it, so it passes the scan on its merits.
    D. `getattr(store, "read_typed_attributes")(cid)` -- the name lived in a
       string, not in `Call.func`.  Strings count now.
    E. The send at module scope, outside any `def`.  Module level is walked.

    F. `SELECT *` plus a row read by key (`row["speed_walk"]`) -- the marker
       wanted the column name and the word SELECT in the SAME string literal,
       and `SELECT *` puts them in different ones.  This is the LIKELIER of
       the two raw spellings, since reading by key is what `SELECT *` is for.
    G. The column name assembled as `"speed_" + "walk"`.  Constant string
       concatenation is folded now.

    *** WHAT IT STILL IS, AND WHY THAT CANNOT BE FIXED BY ADDING A NINTH ROW
    TO THAT LIST.  This is a SOURCE scan, and every strengthening it has had
    came from an adversary naming one more spelling.  A property policed by a
    growing list of defeated spellings HAS NO CLOSURE CONDITION: F and G were
    found the same way A through E were, and nothing here says the list is
    finished, because nothing can.  It cannot see a send assembled at runtime
    out of pieces no single file names.

    So read its zero for exactly what it is: evidence that nobody has written
    the obvious thing, not proof that the column cannot reach a client.  The
    day `speed_walk` legitimately has to reach one -- under its own owner/COO
    decision, which `COO-DECISION 20260902_0742` point 4 reserves -- this
    class must be REWRITTEN, not widened: the property then belongs at the
    send site, as a check that the value on the wire is the value on the row,
    and this scan should be deleted rather than given an exemption.
    """

    #: A call to any of these is "putting a typed value on the wire".
    ENCODERS = ("encode_block", "encode_field", "compose_full_block",
                "compose_sparse_block")
    #: Names, and strings, that mean "read a typed value off a character row".
    READERS = ("read_typed_attributes", "read_character_vitals")
    #: The one file this lane expected to need an exemption.  It gets NONE:
    #: measured, `store.py` composes but never READS a row to do it, so it
    #: passes the scan on its merits.  Kept as a named constant only so the
    #: structural test below can point at it.
    COMPOSING_STORE = "src/pirateforce_foundation/store.py"

    @classmethod
    def _names_and_strings(cls, source):
        """Every identifier, attribute and string constant in the file."""
        try:
            with warnings.catch_warnings():
                # `ast.parse` re-raises other files' invalid-escape warnings;
                # they belong to those files, not to this scan.
                warnings.simplefilter("ignore", DeprecationWarning)
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source)
        except SyntaxError:
            return None
        seen = set()
        strings = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                seen.add(node.id)
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                seen.add(node.value)
                strings.append(node.value)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                # `"speed_" + "walk"` is the column name, spelled to slip past
                # a scan that only looks at whole literals.  Folded here.
                left, right = node.left, node.right
                if (isinstance(left, ast.Constant)
                        and isinstance(left.value, str)
                        and isinstance(right, ast.Constant)
                        and isinstance(right.value, str)):
                    joined = left.value + right.value
                    seen.add(joined)
                    strings.append(joined)
        blob = " ".join(strings).lower()
        # A RAW read of the column, in either of the two spellings that reach
        # it.  The first version of this marker required the column name and
        # the word SELECT in the SAME string literal, which `SELECT *` splits
        # apart -- the likelier spelling of the two, since a row read by key
        # (`row["speed_walk"]`) is what a `SELECT *` is FOR.
        if "select" in blob and "characters" in blob and "speed_walk" in blob:
            seen.add("__raw_speed_walk_select__")
        return seen

    @classmethod
    def _reads_and_encodes(cls, source):
        seen = cls._names_and_strings(source)
        if seen is None:
            return False
        reads = bool(seen & set(cls.READERS)) or (
            "__raw_speed_walk_select__" in seen)
        return reads and bool(seen & set(cls.ENCODERS))

    def test_the_predicate_catches_every_evasion_found_so_far(self):
        """The scan below is only worth running if it can fire.  Each string
        here is one shape the earlier version let through."""
        cases = {
            "raw_sql": ("def send(c):\n"
                        "    row = db.execute('SELECT speed_walk FROM "
                        "characters WHERE id=?', (c,)).fetchone()\n"
                        "    return encode_block({7: row[0]})\n"),
            "split_functions": ("def load(c):\n"
                                "    return store.read_typed_attributes(c)\n"
                                "def send(c):\n"
                                "    return encode_block(load(c))\n"),
            "getattr_string": ("def send(c):\n"
                               "    r = getattr(store, 'read_typed_attributes')"
                               "(c)\n"
                               "    return encode_field(7, r['speed_walk'])\n"),
            "module_scope": ("VALUES = store.read_typed_attributes(1)\n"
                             "BLOCK = encode_block(VALUES)\n"),
            "select_star_row_key": (
                "def send(c):\n"
                "    row = db.execute('SELECT * FROM characters WHERE id=?', "
                "(c,)).fetchone()\n"
                "    return encode_block({7: row['speed_walk']})\n"),
            "concatenated_column_name": (
                "_COL = 'speed_' + 'walk'\n"
                "def send(c):\n"
                "    row = db.execute('SELECT %s FROM characters WHERE id=?' "
                "% _COL, (c,)).fetchone()\n"
                "    return encode_field(7, row[0])\n"),
        }
        for label, source in cases.items():
            with self.subTest(evasion=label):
                self.assertTrue(self._reads_and_encodes(source))
        # and a mention must still NOT count
        self.assertFalse(self._reads_and_encodes(
            "def send(c):\n"
            '    """hands the result to encode_block"""\n'
            "    return store.read_typed_attributes(c)\n"))

    def test_no_file_reads_a_typed_value_off_a_row_and_encodes_it(self):
        offenders = []
        for tree in (ROOT / "src", ROOT / "tools", ROOT / "scenarios",
                     ROOT / "current"):
            if not tree.exists():
                continue
            for path in tree.rglob("*.py"):
                relative = str(path.relative_to(ROOT)).replace("\\", "/")
                text = path.read_text(encoding="utf-8", errors="replace")
                if self._reads_and_encodes(text):
                    offenders.append(relative)
        self.assertEqual(
            [], sorted(offenders),
            "%r reads a typed value off a character row and calls the "
            "attribute encoder.  COO-DECISION 20260902_0742 point 4 forbids "
            "any code sending speed_walk on the strength of migration 008; if "
            "this is a deliberate send under its own decision, this test's "
            "claim -- and 008's header -- are out of date and must be "
            "rewritten, not widened." % (sorted(offenders),),
        )

    def test_the_composing_store_needs_no_exemption_to_pass(self):
        """The claim that makes "no exemptions" true rather than convenient.
        If this goes red, `store.py` has started reading a row and encoding
        it, and the scan above will already have said so."""
        path = ROOT / self.COMPOSING_STORE
        self.assertTrue(path.is_file(), self.COMPOSING_STORE)
        self.assertFalse(
            self._reads_and_encodes(path.read_text(encoding="utf-8")))

    def test_the_one_composing_store_method_is_write_first_and_caller_driven(self):
        """Why `store.py`'s exemption is not a licence: its composer composes
        only the columns its CALLER just wrote, never the whole row.  Read off
        the parse tree, not off its prose."""
        source = (ROOT / self.COMPOSING_STORE).read_text(encoding="utf-8")
        tree = ast.parse(source)
        target = None
        for node in ast.walk(tree):
            if (isinstance(node, ast.FunctionDef)
                    and node.name == "write_typed_attributes_and_compose_sparse"):
                target = node
        self.assertIsNotNone(target, "the composing method is gone; re-read "
                                     "this test's claim before deleting it")
        body = ast.get_source_segment(source, target) or ""
        self.assertNotIn("read_typed_attributes", body)


class BootSnapshotProtects008Tests(_MigratedWorkspace):
    """`COO-DECISION 20260901_1112` point 3 for a SECOND row-touching file.

    007's own class proves the mechanism fires for 007.  That is not the same
    sentence as "it fires for 008": `should_snapshot` is keyed on pending
    migration files, and a regression that narrowed it to a version range
    would leave this file applying to the owner's only database with no copy
    behind it.
    """

    def test_a_snapshot_is_due_while_008_is_the_pending_file(self):
        from pirateforce_foundation import persistence_backup

        self._make(["Snapshot"])
        take, reason = persistence_backup.should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take, reason)
        self.assertIn("008", reason)
        self.assertEqual([8],
                         persistence_backup.pending_versions(self.path,
                                                             MIGRATIONS))

    def test_a_snapshot_that_dies_in_its_prologue_still_aborts_the_boot(self):
        from unittest import mock

        from pirateforce_foundation import persistence_backup

        self._make(["Prologue"])
        with mock.patch.object(
                persistence_backup, "_sha256_file",
                side_effect=OSError("disk went away mid-snapshot")):
            with self.assertRaises(persistence_backup.BackupError) as caught:
                SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                    backups_root=self.root / "backups")
        self.assertIn("disk went away mid-snapshot", str(caught.exception))
        self.assertIsNone(self._rows()[0][SEEDED_COLUMN])
        self.assertNotIn(8, self._applied_versions())

    def test_the_snapshot_taken_at_boot_restores_the_pre_008_database(self):
        ids = self._make(["Restore"])
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=self.root / "backups")
        self.assertIsNotNone(snapshot)
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], SEEDED_VALUE)

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
        self.assertNotIn(8, versions)
        self.assertIsNone(row[SEEDED_COLUMN])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
