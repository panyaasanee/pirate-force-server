"""The birth plug has a pin, and the pin has no branches.

WHY THIS FILE EXISTS.  `COO-DECISION 20260902_0443` point 1 ordered the three
vitals written at character creation, and chief landed that in
`SQLiteStore.create_character` in round R308.  A `pf-adversary` pass then
measured the state the repository was left in and it was not the state the
round thought it was: with the plug **fully reverted** -- the twelve-column
INSERT back, the numbers back to a literal -- the suite came out
`7686 passed, 387 skipped, 15425 subtests passed`, identical to the digit.
Nothing in the tree noticed.

Three guards look like they cover it and each one fails open:

* `tests/pf_birth_state.py` accepts BOTH the seeded and the unseeded birth by
  construction (`UNSEEDED_BIRTH = {}` next to `seeded_birth()`).
* `SeedsACohortNotADatabaseTests::test_a_character_created_after_007_holds_
  nothing_or_the_birth_values` branches on `if not present: ... return`.
* `test_the_numbers_on_a_newborn_row_came_from_the_call_itself` -- the real
  mechanism guard -- ends in `if not any(column in stored ...): return`.

Every one of those was RIGHT while the plug was chief's to write: a lane does
not leave a red test in another lane's corridor for work that has not landed.
`tests/test_persistence_birth_hole_pin.py` was the one file that said which of
the two states the repository was in, and it retired itself the moment the
plug landed, exactly as it was written to.  It shipped with no replacement.

This is the replacement, and it is chief's file rather than LANE-DB's for the
reason the corridor rule gives: the thing it grades is now LANDED code in
`src/pirateforce_foundation/store.py`, which is chief's to keep working.

WHAT IT DELIBERATELY DOES NOT DO.  It never says "or the plug is not in yet".
There is no such state any more.  A revert of the birth INSERT must cost a
named red test, and that is the whole job here.

WHAT IT READS, AND WHY THAT SPELLING.  It grades the COLUMNS, through raw
SQL and `write_typed_attributes`, and names none of the three vitals store
methods `NothingIsWiredTests` scans for -- so it stays outside that allowlist
by not needing to be in it.  A pin on a written row should read the row, not
the door in front of it: a door that starts answering from a cache would
otherwise turn this file green on an empty column.

It does name `new_character_vitals`, and that one it cannot avoid: the value
test compares the row against what the function adjudicates, and the
mechanism test patches the function to make it return numbers nobody could
type by accident.  So this file is listed in
`NewCharacterVitalsTests.test_only_the_ordered_call_site_may_call_it`'s
allowlist, in LANE-DB's file, as an exercise rather than a second source of
birth values -- it produces no birth numbers of its own anywhere.
"""

import ast
import contextlib
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: The three columns the birth INSERT owns, and the only three it may own.
BIRTH_COLUMNS = ("level", "hp_current", "hp_max")

#: A veteran's state: nothing a birth value could be mistaken for.
VETERAN = {"level": 9, "hp_current": 480, "hp_max": 500}

#: Numbers nobody could type by accident, for the mechanism test.
SENTINEL = {"level": 7, "hp_current": 33, "hp_max": 77}

#: A speed no DEFAULT could have supplied.  Not 400.0 (the value `008` seeds
#: the existing cohort with, and the DEFAULT `migrations/009` gives the
#: column), not 0.0, and exact in float32 so the REAL column returns the same
#: bits it was handed.  See `TheFourthBirthValueTests` for what it is for.
VETERAN_SPEED = 313.5

#: The store method the birth lives in, and the two lifecycle events that
#: must not grow a write to a typed column.  `open_session` is named because
#: LANE-DB's letter `20260902_2030` and this file's own docstring both list
#: it as a candidate seed site, and nothing was scanning it.
BIRTH_METHODS = ("create_character", "select_character", "open_session")

#: The column `COO-DECISION 20260902_2046` is about.  It is deliberately NOT
#: in `BIRTH_COLUMNS`: those three are the columns the birth INSERT OWNS,
#: this is the one it must not acquire.
FOURTH_COLUMN = "speed_walk"

#: Reads as SQL that WRITES, rather than merely mentioning a column name.  A
#: docstring naming the column is not a write, and the first version of the
#: scanner in `tests/test_persistence_speed_walk_seed_008.py` was beaten by
#: exactly that -- its comment at lines 549-568 records the five evasions.
_SQL_WRITE = re.compile(r"\b(insert\s+into|update)\b", re.IGNORECASE)


def _build_wire(selector):
    return b"wire", b"avatar", 0x20000001 + selector, 0


def _position():
    return Position(3, 0, 1.0, 2.0, 3.0, heading=0.0)


@contextlib.contextmanager
def _raw(path):
    """A raw connection that is committed AND CLOSED.

    `with sqlite3.connect(...)` commits on exit and does not close, which is
    free on Linux and fails the Windows gate inside `TemporaryDirectory`
    cleanup with `WinError 32`.  Same helper, same reason, as `raw_rows` in
    `tests/test_persistence_vitals_seed_007.py`.
    """
    db = sqlite3.connect(path)
    try:
        yield db
        db.commit()
    finally:
        db.close()


class _FreshInstall(unittest.TestCase):
    """One empty database with the FULL migration set applied.

    A fresh install is the case the old hole bit hardest: `007` runs against
    an empty `characters` table, seeds nobody, and can never run again.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = str(Path(self._tmp.name) / "pf.sqlite3")

    def _store(self):
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        return store

    def _born(self, store, tag):
        # A per-character identity base, because `004`'s partial UNIQUE index
        # covers (identity_lo, identity_hi) across ACCOUNTS: two accounts'
        # first characters both take selector 0, and one `_build_wire` keyed
        # on the selector alone would collide on the second birth -- which is
        # the exact call these tests are here to make.
        self._identity_base = getattr(self, "_identity_base", 0) + 0x1000

        base = self._identity_base

        def build_wire(selector):
            return b"wire", b"avatar", 0x20000001 + base + selector, 0

        account_id = store.ensure_account(tag)
        return store.create_character(
            account_id, "Born%s" % tag, "born%s" % tag, "fingerprint-%s" % tag,
            build_wire, _position())

    def _columns_of(self, character_id):
        with _raw(self.path) as db:
            row = db.execute(
                "SELECT level, hp_current, hp_max FROM characters WHERE id=?",
                (character_id,)).fetchone()
        return dict(zip(BIRTH_COLUMNS, row))

    def _speed_of(self, character_id):
        """`speed_walk` off the row.  `_columns_of` reads the three columns
        the birth owns and deliberately not this one."""
        with _raw(self.path) as db:
            row = db.execute(
                "SELECT %s FROM characters WHERE id=?" % (FOURTH_COLUMN,),
                (character_id,)).fetchone()
        return row[0]

    def _column_default(self, column):
        """The column's own DEFAULT as `PRAGMA table_info` reports it.

        Read from the SAME database the test just migrated, so this file
        never becomes a second place the number is written down -- the rule
        `COO-DECISION 20260902_0443` point 1 sets.  `None` for a column that
        has no DEFAULT, which is what `main` has today.
        """
        with _raw(self.path) as db:
            for row in db.execute("PRAGMA table_info(characters)"):
                if row[1] == column:
                    return row[4]
        raise AssertionError("characters has no column %r" % (column,))


class TheBirthPlugIsPinnedTests(_FreshInstall):
    """No branches.  A revert costs a red test, by name."""

    def test_a_newborn_holds_the_three_birth_values_and_none_is_null(self):
        store = self._store()
        character = self._born(store, "one")
        held = self._columns_of(character.id)
        for column in BIRTH_COLUMNS:
            self.assertIsNotNone(
                held[column],
                "%s is NULL on a character born on a fresh install -- the "
                "birth INSERT in SQLiteStore.create_character no longer "
                "writes it, and COO-DECISION 20260902_0443 point 1 is undone "
                "(migrations/007 seeds a COHORT and cannot reach this row)"
                % column)
        self.assertEqual(
            held, dict(vitals.new_character_vitals()),
            "a newborn holds birth vitals that are not the ones "
            "persistence_vitals.new_character_vitals() adjudicates")

    def test_the_numbers_come_from_the_call_and_not_from_a_literal(self):
        """The MECHANISM, which is half of what point 1 ordered: one function,
        so the day an RE answers what the original game's birth values were,
        the value changes in one edit in one file.

        Asked the one way that binds it: make the function return numbers
        nobody could type by accident and look for THOSE on the row.  A
        literal `(1, 100, 100)` in the INSERT, a schema DEFAULT and a
        `CREATE TRIGGER` all hold the right numbers and all are red here.

        Patched BY NAME, not by identity, on the defining module and on every
        `store.py` global whose function is called `new_character_vitals` --
        `import ... as _birth` and `persistence_vitals.new_character_vitals()`
        are both caught, and so is the object identity left behind by a
        sibling file's `importlib.reload(persistence_vitals)`, which produced
        a FALSE RED on a CORRECT plug in the test this one is modelled on.
        """
        self.assertNotEqual(SENTINEL, dict(vitals.new_character_vitals()))

        import pirateforce_foundation.store as store_module

        def _fake():
            return dict(SENTINEL)

        aliases = [name for name, value in vars(store_module).items()
                   if callable(value)
                   and getattr(value, "__name__", "") == "new_character_vitals"]
        with contextlib.ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(vitals, "new_character_vitals", _fake))
            for name in aliases:
                stack.enter_context(
                    mock.patch.object(store_module, name, _fake))
            store = self._store()
            character = self._born(store, "mech")
            held = self._columns_of(character.id)

        self.assertEqual(
            held, SENTINEL,
            "a newborn holds birth vitals, but NOT the ones "
            "new_character_vitals() returned while it was being created -- so "
            "the numbers came from somewhere else (an inline literal, a schema "
            "DEFAULT, or a trigger).  COO-DECISION 20260902_0443 points 1 and "
            "2 rule out all three.  Measured at runtime, not read off source.")

    def test_a_positional_swap_of_hp_current_and_hp_max_is_caught(self):
        """The INSERT names fifteen columns and passes fifteen values, and the
        two HP values are both 100 in the shipped constant -- so a swap of the
        last two is invisible to any test that only checks the numbers.  The
        sentinel above is asymmetric on purpose (33 vs 77); this states that
        that is WHY, so a later round does not "tidy" it to 100/100.
        """
        self.assertNotEqual(SENTINEL["hp_current"], SENTINEL["hp_max"])

    def test_a_birth_writes_no_typed_column_beyond_the_three(self):
        """`COO-DECISION 20260901_1447` point 2: no fourth column at birth.
        `speed_walk` is the live candidate, and it is NO LONGER NULL at
        birth: `COO-DECISION 20260902_0742` then `20260902_1607` (the one
        Panya ruled live) replaced `20260902_1043`, and migration `009`
        gives the column a schema DEFAULT of 400.0.  At HEAD
        `create_character` names only the three vitals, so the 400.0 below
        is the DEFAULT's -- but the assertion MEASURES THE VALUE, NOT ITS
        PROVENANCE, and `COO-DECISION 20260902_2046` point 3 gives the
        provenance guard to this file's owner, not to LANE-DB.
        """
        store = self._store()
        character = self._born(store, "four")
        with _raw(self.path) as db:
            columns = [row[1] for row in
                       db.execute("PRAGMA table_info(characters)")]
            self.assertIn("speed_walk", columns,
                          "migration 008 is missing; this test grades nothing")
            value = db.execute(
                "SELECT speed_walk FROM characters WHERE id=?",
                (character.id,)).fetchone()[0]
        self.assertEqual(
            value, 400.0,
            "a newborn's speed_walk is not the 400.0 that "
            "migrations/009_character_birth_defaults.sql declares as the "
            "column DEFAULT.  The value is owed to the SCHEMA: "
            "COO-DECISION 20260902_0742 then 20260902_1607 (Panya ruled "
            "live) replaced 20260902_1043, which is what the old NULL "
            "expectation cited.  THIS CARD CANNOT TELL WHERE THE 400.0 "
            "CAME FROM -- measured by pf-adversary on 2026-09-02: a "
            "create_character that appends speed_walk=400.0 to the birth "
            "INSERT costs ZERO red tests in this file, and a tree with the "
            "DEFAULT removed and the value written at birth instead leaves "
            "all seven green.  Read a green here as 'the row holds 400.0', "
            "never as 'no fourth column was written at birth'; "
            "COO-DECISION 20260902_2046 point 3 gives that guard to chief")


class TheBirthTouchesNothingElseTests(_FreshInstall):
    """The other half: what a birth must NOT do."""

    def test_a_second_birth_leaves_a_veteran_untouched(self):
        """The failure this shape is written for: a plug spelled as an UPDATE
        with no `WHERE`, or `WHERE account_id=?`, resets a real player's
        character on the NEXT create.  Measured on the first draft of the
        pin this file replaces: a veteran at `level 9, hp 480/500` came out
        of the next creation at `1, 100/100`, green across seven tests that
        each looked at only one row.
        """
        store = self._store()
        veteran = self._born(store, "vet")
        store.write_typed_attributes(veteran.id, dict(VETERAN))
        self.assertEqual(self._columns_of(veteran.id), VETERAN)

        self._born(store, "next")

        self.assertEqual(
            self._columns_of(veteran.id), VETERAN,
            "creating a character rewrote ANOTHER character's vitals -- the "
            "birth write is reaching rows it does not own")

    def test_selecting_a_character_writes_no_vitals(self):
        """Which LIFECYCLE EVENT holds the seed, which is the discrimination
        the retired pin made and nothing else does.

        A seed installed in `select_character` (or in `open_session`) would
        satisfy every "a newborn holds 1/100/100" test in the repository
        while silently rewriting a veteran's HP on every login.  This is the
        only test that can tell the two apart: it puts a NON-birth state on
        the row and then logs in.
        """
        store = self._store()
        veteran = self._born(store, "login")
        store.write_typed_attributes(veteran.id, dict(VETERAN))

        session = store.open_session(store.ensure_account("login"))
        store.select_character(session, veteran.selector)

        self.assertEqual(
            self._columns_of(veteran.id), VETERAN,
            "logging in changed a character's vitals -- the birth values are "
            "being written by a login-path event rather than by "
            "SQLiteStore.create_character, so every login resets HP")

    def test_a_repeated_create_with_the_same_fingerprint_writes_nothing_new(self):
        """The retry branch returns the existing character before the INSERT.
        A birth write placed above that early return would fire twice.
        """
        store = self._store()
        account_id = store.ensure_account("retry")
        first = store.create_character(
            account_id, "Retry", "retry", "fingerprint-retry",
            _build_wire, _position())
        store.write_typed_attributes(first.id, dict(VETERAN))

        again = store.create_character(
            account_id, "Retry", "retry", "fingerprint-retry",
            _build_wire, _position())

        self.assertEqual(again.id, first.id)
        self.assertEqual(
            self._columns_of(first.id), VETERAN,
            "a repeated create re-ran the birth write and reset the row")


class TheFourthBirthValueTests(_FreshInstall):
    """The guard that survives `speed_walk` getting a column DEFAULT.

    `COO-DECISION 20260902_2046`.  `test_a_birth_writes_no_typed_column_
    beyond_the_three` asserts a newborn's `speed_walk` is NULL, which is true
    and green on `main` today.  It stops being either the moment
    `migrations/009_character_birth_defaults.sql` lands, because that gives
    the column `DEFAULT 400.0` on the owner's own ruling (`COO-DECISION
    20260902_1607`) -- and from then on a row-level read cannot tell "the
    birth path WROTE a fourth value" from "the schema's DEFAULT supplied
    one".  The sensor goes blind while staying green, which is the shape that
    let `109` be green on a broken build.

    !! THE COO OFFERED TWO SHAPES AND SAID TO PICK ONE.  BOTH ARE HERE, AND
    THE REASON IS A MEASUREMENT, NOT AN APPETITE FOR TESTS.  Three one-line
    mutations were written into scratch copies of `store.py` and run:

      M1  a `speed_walk` UPDATE added to `select_character`   (b) RED  (a) RED
      M2  `speed_walk` added to the birth INSERT itself       (b) GREEN (a) RED
      M3  an unqualified `UPDATE characters SET speed_walk=`  (b) RED  (a) RED

    M2 IS THE ORIGINAL INTENT -- the fourth value written on the newborn's
    OWN row -- and the behavioural shape (b) passes it, because (b) can only
    ever inspect a DIFFERENT row than the one just born.  With a column
    DEFAULT present no row-level or trigger-level probe can separate the two:
    a SQLite `AFTER INSERT` trigger sees `NEW.speed_walk = 400.0` identically
    whether the INSERT named the column or the DEFAULT filled it, and the
    authorizer callback carries no column name for `SQLITE_INSERT`.  Only the
    statement text can tell them apart.  So (a) is the one that preserves the
    retired pin's meaning, and (b) is the one that catches the seed migrating
    into a login-path event.  They cover disjoint failures; either alone
    leaves a door open.

    Both are green on `main` today AND green with `009` grafted on, so this
    file does not have to wait for LANE-DB's migration to land.
    """

    def _source_of(self, method):
        """The `ast` node for one method of `SQLiteStore`."""
        source = (ROOT / "src" / "pirateforce_foundation" / "store.py")
        tree = ast.parse(source.read_text(encoding="utf-8"), str(source))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name == method:
                return node
        raise AssertionError(
            "SQLiteStore has no method %r -- this scan is grading nothing"
            % (method,))

    def _sql_writes_in(self, node):
        """Every string literal under `node` that reads as SQL that writes.

        Both plain constants and the literal halves of an f-string, because
        `store.py` already builds one statement with an f-string and a
        computed `{assignments}` -- a scan that only read `ast.Constant`
        would be blind to the day the birth path grows one.
        """
        found = []
        for child in ast.walk(node):
            texts = []
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                texts.append(child.value)
            elif isinstance(child, ast.JoinedStr):
                texts.append("".join(
                    part.value for part in child.values
                    if isinstance(part, ast.Constant)
                    and isinstance(part.value, str)))
            for text in texts:
                if _SQL_WRITE.search(text) and FOURTH_COLUMN in text:
                    found.append(text)
        return found

    # ---- shape (a): measured at the statement -------------------------

    def test_no_lifecycle_method_writes_the_fourth_column(self):
        """`COO-DECISION 20260902_2046` shape (a), and the ONLY shape that
        still measures the retired pin's meaning once the column has a
        DEFAULT: the birth path must contain no INSERT or UPDATE naming
        `speed_walk` at all.

        Scanned methods are `BIRTH_METHODS`.  A docstring that merely
        mentions the column is not a write and does not fire this -- the
        evasion that beat the first version of the sibling scanner in
        `tests/test_persistence_speed_walk_seed_008.py`.
        """
        for method in BIRTH_METHODS:
            with self.subTest(method=method):
                writes = self._sql_writes_in(self._source_of(method))
                self.assertEqual(
                    writes, [],
                    "SQLiteStore.%s writes %s: that is the fourth birth "
                    "value nobody adjudicated, and once migrations/009 gives "
                    "the column a DEFAULT no row-level test can see it "
                    "(COO-DECISION 20260902_2046)"
                    % (method, FOURTH_COLUMN))

    def test_the_statement_scan_fires_on_a_write_it_is_meant_to_catch(self):
        """Prove the scan can go red, so it is not a guard on prose.

        This repo's own answer to the vacuous-source-scan problem
        (`tests/test_persistence_speed_walk_seed_008.py` ships the same
        self-test).  Each string below is a shape the birth path could
        plausibly grow; each must be seen.
        """
        caught = (
            "INSERT INTO characters (speed_walk) VALUES (400.0)",
            "UPDATE characters SET speed_walk=? WHERE id=?",
            "update characters set speed_walk = 400.0",
        )
        ignored = (
            "SELECT speed_walk FROM characters WHERE id=?",
            "the birth INSERT does not touch speed_walk",
            "UPDATE characters SET level=? WHERE id=?",
        )
        for text in caught:
            with self.subTest(caught=text):
                node = ast.parse("def f():\n    x = %r\n" % (text,))
                self.assertTrue(self._sql_writes_in(node))
        for text in ignored:
            with self.subTest(ignored=text):
                node = ast.parse("def f():\n    x = %r\n" % (text,))
                self.assertFalse(self._sql_writes_in(node))

    def test_the_scan_reads_f_strings_and_not_only_plain_literals(self):
        """`store.py` already composes one UPDATE with an f-string and a
        computed `{assignments}`; a scan blind to `JoinedStr` would be
        defeated by the birth path growing the same idiom.
        """
        node = ast.parse(
            'def f():\n'
            '    cols = "x"\n'
            '    q = f"UPDATE characters SET speed_walk=?, {cols} WHERE id=?"\n'
        )
        self.assertTrue(self._sql_writes_in(node))

    # ---- shape (b): measured at behaviour ------------------------------

    def test_a_speed_on_a_row_survives_a_login_and_a_later_birth(self):
        """`COO-DECISION 20260902_2046` shape (b): put a value on the row
        that no DEFAULT could have supplied, then run the login path and a
        later birth, and require it back byte-exact.

        This catches what shape (a) cannot see from source alone -- a seed
        that reaches the row through a helper rather than through a literal
        in one of the scanned methods -- and it is the ONLY test here that
        would notice a login-path write reaching a veteran's row.  What it
        does NOT cover is measured and written down in this class's
        docstring: a birth INSERT naming the column on its OWN row (M2) is
        green here.
        """
        store = self._store()
        default = self._column_default(FOURTH_COLUMN)
        if default is not None:
            self.assertNotEqual(
                float(default), VETERAN_SPEED,
                "VETERAN_SPEED was set to the column's own DEFAULT, so this "
                "test can no longer tell a write from a default")

        veteran = self._born(store, "speed")
        store.write_typed_attributes(veteran.id, {FOURTH_COLUMN: VETERAN_SPEED})
        self.assertEqual(self._speed_of(veteran.id), VETERAN_SPEED)

        session = store.open_session(store.ensure_account("speed"))
        store.select_character(session, veteran.selector)
        self.assertEqual(
            self._speed_of(veteran.id), VETERAN_SPEED,
            "logging in overwrote speed_walk, so every login resets a "
            "player's speed")

        self._born(store, "speednext")
        self.assertEqual(
            self._speed_of(veteran.id), VETERAN_SPEED,
            "creating a character overwrote ANOTHER character's speed_walk "
            "-- the birth write is reaching rows it does not own")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
