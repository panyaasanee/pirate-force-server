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
        # And a directory that stops at 008, so this file's subject stays 008.
        # `_apply_008` used to run the WHOLE directory, which was the same
        # thing until `migrations/009_character_birth_defaults.sql` existed;
        # after it, running the whole directory would silently make every test
        # below a test of 008 AND 009 together.
        self.upto_008 = self.root / "migrations_upto_008"
        self.upto_008.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(path.name[:3])
            if version < 8:
                shutil.copy2(path, self.older / path.name)
            if version <= 8:
                shutil.copy2(path, self.upto_008 / path.name)
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
        """Exactly 001..008 -- see the note in `setUp`."""
        SQLiteStore(self.path, self.upto_008).migrate()

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

        A character created after 008 and BEFORE 009 holds no speed: 008
        writes the rows that exist when it runs and the ledger stops it ever
        running again, and the insertion point of `COO-DECISION 20260902_0444`
        is for the three vitals and not for this column.  That gap is what
        `migrations/009_character_birth_defaults.sql` closed, at the schema
        rather than at the insertion point (`COO-DECISION 20260902_1607`), so
        the two halves are measured separately here: 008 alone leaves the
        newborn empty, and 009 is what fills it.
        """
        self._make(["Before"])
        self._apply_008()
        self.assertEqual(self._rows()[0][SEEDED_COLUMN], SEEDED_VALUE)
        store_at_008 = SQLiteStore(self.path, self.upto_008)
        during_the_gap = store_at_008.create_character(
            store_at_008.ensure_account("after-008"), "After", "after",
            "fingerprint-after-008", _build_wire_for(0x30000001),
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        self.assertNotIn(
            SEEDED_COLUMN,
            store_at_008.read_typed_attributes(during_the_gap.id))

        # 009, and only 009, is what gives the NEXT one a speed -- and it does
        # not reach backwards for the one born during the gap.
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        later = store.create_character(
            store.ensure_account("after-009"), "Later", "later",
            "fingerprint-after-009", _build_wire_for(0x30000009),
            Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        self.assertEqual(
            store.read_typed_attributes(later.id)[SEEDED_COLUMN], SEEDED_VALUE)
        self.assertNotIn(
            SEEDED_COLUMN, store.read_typed_attributes(during_the_gap.id))
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

    WHAT IT STILL IS, said plainly rather than left to be discovered: a
    SOURCE scan.  It cannot see a send assembled at runtime out of pieces no
    single file names, and a determined author can still get past it.  Its
    zero is evidence that nobody has written the obvious thing, not proof that
    the column cannot reach a client.
    """

    #: A call to any of these is "putting a typed value on the wire".
    ENCODERS = ("encode_block", "encode_field", "compose_full_block",
                "compose_sparse_block")
    #: Names, and strings, that mean "read a value off a character row THAT
    #: COULD BE `speed_walk`".  The tuple is CHOSEN, and each membership
    #: decision is checked against the code by
    #: `test_the_reader_list_is_derived_from_what_can_carry_the_column`
    #: below: `read_typed_attributes` can hand `speed_walk` to a caller and
    #: `read_character_vitals` cannot, because everything it returns has been
    #: through `persistence_vitals.resolve()`, which keeps only the three
    #: vital columns and drops the rest.  (An earlier draft of this comment
    #: said "derived, not chosen"; a `pf-adversary` pass pointed out that
    #: nothing derives WHICH methods can carry the column, and the sentence
    #: was doing work the code does not do.)
    #:
    #: *** KNOWN GAP, measured by that same pass and REPORTED rather than
    #: quietly closed, because closing it needs a decision this lane does not
    #: own: `write_typed_attributes` is missing from this tuple and it hands
    #: back THE WHOLE POST-WRITE ROW, so
    #: `store.write_typed_attributes(cid, {"level": 1})["speed_walk"]`
    #: reaches the column through a WRITE, with no reader named and no raw
    #: SQL involved.  It is pre-existing (this scan has never counted it) and
    #: adding it would turn `store.py` itself red, since its own
    #: `write_typed_attributes_and_compose_sparse` is exactly that shape --
    #: escaping only by projecting the caller's own keys, which is pinned by
    #: `test_the_one_composing_store_method_is_write_first_and_caller_driven`
    #: below.  Naming it here beats a green test that means less than it
    #: looks like it means.
    #:
    #: LANE-DB round h5csld removed `read_character_vitals` from this tuple,
    #: and the reason is written here rather than in a commit message because
    #: a narrowed scan that nobody can audit is worse than no scan.  The claim
    #: this class exists for is point 4 of `COO-DECISION 20260902_0742`:
    #: nothing may read `speed_walk` off a row and send it.  A call that
    #: structurally cannot produce `speed_walk` is not that shape, and
    #: counting it made the scan fire on `store.py` the moment this lane added
    #: `read_character_vitals_or_none` -- a method that reads three vitals,
    #: encodes nothing, and cannot reach x=7 at all.  Widening the exemptions
    #: or making the unit a function again would have re-opened evasions A-E;
    #: narrowing WHAT COUNTS AS A READ, on a property derived from the code,
    #: does not.  Whether anything is wired to the VITALS is a different claim
    #: with its own home: `NothingIsWiredTests` in
    #: `tests/test_persistence_vitals.py`.
    READERS = ("read_typed_attributes",)
    #: The one file this lane expected to need an exemption.  It gets NONE:
    #: measured, `store.py` composes but never READS a row to do it, so it
    #: passes the scan on its merits.  Kept as a named constant only so the
    #: structural test below can point at it.
    COMPOSING_STORE = "src/pirateforce_foundation/store.py"

    #: "This string is a SELECT statement", not "this string says select".
    _SQL_SELECT_FROM = re.compile(r"\bselect\b[\s\S]*\bfrom\b")

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
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                seen.add(node.id)
            elif isinstance(node, ast.Attribute):
                seen.add(node.attr)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                seen.add(node.value)
                # A raw SQL read of the column itself, not only the API.
                #
                # The shape is required to look like SQL, and that is a
                # correction rather than a softening (LANE-DB round h5csld):
                # the first version fired on `"speed_walk" in s and "select"
                # in s`, and the string that caught it out was a DOCSTRING --
                # one naming the column and containing the word "selected".
                # Prose is not a read.  `\bselect\b` does not match
                # "selected", and a real `SELECT ... FROM characters` still
                # matches both halves, so every evasion below stays closed.
                lowered = node.value.lower()
                if ("speed_walk" in lowered
                        and cls._SQL_SELECT_FROM.search(lowered)):
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

    def test_the_predicate_catches_all_five_evasions_that_beat_the_first_one(self):
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
        }
        for label, source in cases.items():
            with self.subTest(evasion=label):
                self.assertTrue(self._reads_and_encodes(source))
        # and a mention must still NOT count
        self.assertFalse(self._reads_and_encodes(
            "def send(c):\n"
            '    """hands the result to encode_block"""\n'
            "    return store.read_typed_attributes(c)\n"))
        # nor may PROSE count, which is what the first version of the raw-SQL
        # half did: this docstring names the column and contains the word
        # "selected", and it reads nothing at all.
        self.assertFalse(self._reads_and_encodes(
            "def compose(c):\n"
            '    """speed_walk is stored; a character it has just selected\n'
            '    is not read here."""\n'
            "    return encode_block({})\n"))
        # while the real statement still counts, spelled either way round
        self.assertTrue(self._reads_and_encodes(
            "def send(c):\n"
            "    row = db.execute('select speed_walk from characters')\n"
            "    return encode_block({7: row[0]})\n"))

    def test_the_reader_list_is_derived_from_what_can_carry_the_column(self):
        """`READERS` is a claim about the CODE, so it is measured against the
        code rather than declared.  Two halves, and both must hold:

        1. `read_typed_attributes` really can hand `speed_walk` to a caller --
           if it could not, this scan would be watching nothing.
        2. `read_character_vitals` really cannot -- everything it returns has
           been through `persistence_vitals.resolve()`, and the day that stops
           being true this test goes red and the tuple must grow again.
        """
        self.assertIn("read_typed_attributes", self.READERS)
        self.assertNotIn("read_character_vitals", self.READERS)

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "readers.sqlite3"
        store = SQLiteStore(path, MIGRATIONS)
        store.migrate()
        account = store.ensure_account("readers")
        character = store.create_character(
            account, "ReaderChar", "readerchar", "fingerprint-readers",
            _build_wire, Position(1, 0, 1.0, 2.0, 3.0, heading=0.0),
        )
        store.write_typed_attributes(
            character.id,
            {"speed_walk": SEEDED_VALUE, "level": 4,
             "hp_current": 20, "hp_max": 40},
        )

        # 1. the reader that IS on the list hands the column over.
        self.assertEqual(
            store.read_typed_attributes(character.id)["speed_walk"],
            SEEDED_VALUE)

        # 2. the reader that is NOT on the list cannot, on a row that holds
        #    the column, through the public method and through `resolve()`
        #    directly -- the second is what makes it structural rather than a
        #    happy accident of this row.
        resolution = store.read_character_vitals(character.id)
        self.assertNotIn("speed_walk", resolution.present)
        self.assertEqual(
            sorted(resolution.present), sorted(vitals.VITAL_COLUMNS))
        self.assertNotIn("speed_walk", vitals.VITAL_COLUMNS)
        direct = vitals.resolve(
            {"speed_walk": SEEDED_VALUE, "level": 4,
             "hp_current": 20, "hp_max": 40})
        self.assertNotIn("speed_walk", direct.present)
        # and what `require()` hands out has no room for it either
        self.assertEqual(
            sorted(vars(direct.require())),
            sorted(vitals.VITAL_COLUMNS))

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
        # 009, round `5d02mu`'s 010 (`010_ground_drops.sql`), round
        # `6796cv`'s 011 (`011_character_skills.sql`), round `p6x3ee`'s
        # 012 (`012_ground_drops_taken_marker.sql`), and round `j9wwc4`'s
        # 013 (`013_character_home_marker.sql`) all joined the directory
        # after this test was written, so a database that stopped at 007
        # now has all six pending.  Still an exact list and not an
        # `assertIn`: the point of the pin is that the snapshot is due for a
        # KNOWN set of pending files, and a membership test would keep
        # passing while a fourteenth file nobody looked at joined them.
        self.assertEqual([8, 9, 10, 11, 12, 13],
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
