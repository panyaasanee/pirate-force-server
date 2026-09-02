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

import contextlib
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
