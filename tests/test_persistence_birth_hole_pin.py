"""LANE-DB: the pin `COO-DECISION 20260902_1546` ordered over the birth hole.

WHAT THE HOLE IS.  `SQLiteStore.create_character` names its INSERT columns
explicitly (`store.py:229`) and `level`, `hp_current`, `hp_max` are not among
them; `006_character_typed_attribute_columns.sql` added the three with no
DEFAULT; `007_character_vitals_seed.sql` seeds the rows that EXIST when it
runs and the ledger stops it ever running again.  So on a FRESH INSTALL --
where 007 runs against an empty table -- every character born afterwards holds
NULL in all three, forever.  A character with no HP cannot be damaged, cannot
be healed, and composes with a named gap instead of a number.

WHAT THIS FILE IS AND IS NOT.  It is not a second copy of the state grading
already done by `SeedsACohortNotADatabaseTests` in
`tests/test_persistence_vitals_seed_007.py`: that class deliberately accepts
EITHER adjudicated state, so that the day chief lands the insertion point
`COO-DECISION 20260902_0444` ordered, nothing in this lane's files goes red
inside his pull request.  The cost of that choice is exactly what COO named
in `1546`: WHICH of the two states the repository is in stopped being said
out loud anywhere, and the class docstring even points at a
`test_which_state_this_repository_is_in_is_reported` that was never written.
This file is that missing report -- "a pin, not silence" in COO's words.

WHAT IT COSTS THE PLUG'S OWN PULL REQUEST, said here rather than discovered
by the person who lands it.  This pin goes RED the day the hole is closed.
That is the landmine `SeedsACohortNotADatabaseTests` was rewritten to avoid,
and it is deliberate here for one reason: COO ordered a pin, and a pin that is
green in both states is silence.  What this file owes in exchange is that the
red is CHEAP -- one named failure whose whole message is the instruction to
delete one file that nothing imports, plus written permission to do it
(LANE-DB round `dgx8e5`, letter to chief the same round).

THE SHAPE THAT WAS TRIED FIRST AND MEASURED WRONG.  The first draft skipped
instead of failing on the plugged branch, on the theory that a skip is visible
under `pytest -rs` and never red.  It is red, just somewhere worse:
`.github/workflows/gate-windows.yml:454` runs
`tools/pf_pytest_precondition_census.py`, which exits 1 on "a skip whose
reason carries no `[precondition:<key>]` token and is not in the design_skips
pin" (`tools/pf_pytest_precondition_census.py:17-19`), and the pin file it
reads is `docs/PYTEST_SKIP_PINS.json` -- chief's zone, which this lane may not
edit to declare the skip in advance, and which could not hold it anyway
because the same tool exits 1 on "a pinned skip that did not happen".  So the
skip would have turned the gate red for chief with an opaque census exit code
instead of a test failure carrying its own instructions.  A worse red, bought
by pretending there was none.

A THIRD STATE IS STILL A FAILURE.  The measurement goes through
`pf_birth_state.measure_birth_typed_state`, which refuses anything that is
neither "no typed column" nor exactly `persistence_vitals.new_character_
vitals()` -- a partial seed, a level of zero, a `speed_walk` seeded at birth.
The pin therefore grades a wrong plug in both of its branches, which is the
property that makes it worth its line count.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

import pf_birth_state as birth_state  # noqa: E402

MIGRATIONS = ROOT / "migrations"

#: The instruction that travels WITH the plug, so the person who lands it does
#: not have to find this file's owner to know what to do about it.
DELETE_ME_WHEN_THE_PLUG_LANDS = (
    "THIS IS NOT A DEFECT IN YOUR CHANGE -- IT IS THIS PIN RETIRING.  A "
    "character born on a fresh install now holds exactly the birth vitals, "
    "so the birth hole COO-DECISION 20260902_1546 told LANE-DB to pin is "
    "CLOSED and the pin is finished.  Do this and nothing else: delete "
    "tests/test_persistence_birth_hole_pin.py, the whole file.  Nothing "
    "imports it and no other test reads any name in it; LANE-DB gives "
    "written permission to remove it in round dgx8e5 and in the letter to "
    "chief of the same round, so the write-zone rule is not in your way.  "
    "The plugged state stays graded, in a file you do not have to touch, by "
    "SeedsACohortNotADatabaseTests in "
    "tests/test_persistence_vitals_seed_007.py -- which accepts EITHER "
    "adjudicated state and grades the values either way, so deleting this "
    "file loses no coverage of your plug."
)


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class TheBirthHoleHasAPinTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = str(Path(self.tmp.name) / "fresh_install.sqlite3")

    def _fresh_install(self):
        """A server booting on a machine that has never held a character.

        The real migration directory against a real empty file: a fresh
        install is the ONLY shape in which this hole bites, so building the
        schema by hand here would measure something else.
        """
        store = SQLiteStore(self.path, MIGRATIONS)
        store.migrate()
        return store

    def _newborn(self, store, tag="pin"):
        account_id = store.ensure_account(tag)
        character = store.create_character(
            account_id, "Newborn", "newborn", "fingerprint-%s" % tag,
            _build_wire, Position(3, 0, 1.0, 2.0, 3.0, heading=0.0))
        return character.id

    def test_a_character_born_on_a_fresh_install_still_holds_no_vital(self):
        """THE PIN.  Green today over the open hole; ONE named failure, whose
        message is the whole instruction, once the hole is closed."""
        store = self._fresh_install()
        character_id = self._newborn(store)
        state = birth_state.measure_birth_typed_state(store, character_id)

        if state == birth_state.seeded_birth():
            self.fail(DELETE_ME_WHEN_THE_PLUG_LANDS)

        # The hole is open.  Everything below is what that costs, measured
        # rather than described, so that a plug which lands HALF of it (or
        # lands it somewhere this branch cannot see) is red here.
        self.assertEqual(
            state, {},
            "create_character left a typed value behind but not the birth "
            "vitals: %r" % (state,))
        for column in vitals.VITAL_COLUMNS:
            with self.subTest(column=column):
                self.assertNotIn(column, state)

        resolution = store.read_character_vitals(character_id)
        self.assertFalse(resolution.complete)
        self.assertEqual(
            sorted(gap.column for gap in resolution.gaps),
            sorted(vitals.VITAL_COLUMNS))
        self.assertEqual(
            {gap.reason for gap in resolution.gaps},
            {vitals.REASON_NOT_SEEDED},
            "an unseeded column must be reported as not seeded and never as "
            "a zero (COO-DECISION 20260901_1059)")
        with self.assertRaises(vitals.VitalsError) as caught:
            resolution.require()
        self.assertIn(vitals.REASON_NOT_SEEDED, str(caught.exception))

        census = store.vitals_seeding_census()
        self.assertEqual(census["characters_any"], 1)
        for column in vitals.VITAL_COLUMNS:
            with self.subTest(column=column):
                self.assertEqual(census["%s_seeded_any" % column], 0)
                self.assertEqual(census["%s_seeded_live" % column], 0)

    def test_the_pin_ran_the_whole_migration_directory_it_claims_to(self):
        """The pin's guard against being vacuously green.

        A fixture that quietly stopped before `006` would report "no vital on
        a newborn" for the wrong reason -- there would be no columns to hold
        one -- and the pin would keep passing after the hole was closed.  So
        the ledger is compared against the directory on disk, and the three
        columns are proved to EXIST on the table the newborn was written to.
        """
        store = self._fresh_install()
        character_id = self._newborn(store)
        on_disk = sorted(
            int(path.name[:3])
            for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
        self.assertIn(6, on_disk, "006 is what adds the columns at all")
        db = sqlite3.connect(self.path)
        try:
            applied = sorted(
                int(row[0])
                for row in db.execute("SELECT version FROM schema_migrations"))
            columns = {str(row[1])
                       for row in db.execute("PRAGMA table_info(characters)")}
            row = db.execute(
                "SELECT COUNT(*) FROM characters WHERE id=?",
                (character_id,)).fetchone()
        finally:
            db.close()
        self.assertEqual(applied, on_disk)
        for column in vitals.VITAL_COLUMNS:
            with self.subTest(column=column):
                self.assertIn(column, columns)
                self.assertIn(column, typed.TYPED_COLUMNS)
        self.assertEqual(int(row[0]), 1, "the newborn was never written")


if __name__ == "__main__":
    unittest.main()
