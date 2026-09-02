"""LANE-DB: the pin `COO-DECISION 20260902_1546` ordered over the birth hole.

WHAT THE HOLE IS.  `SQLiteStore.create_character` names its INSERT columns
explicitly and `level`, `hp_current`, `hp_max` are not among them (named by
symbol, not by line: a `pf-adversary` pass has already caught this lane
citing a line number that an unrelated edit had moved);
`006_character_typed_attribute_columns.sql` added the three with no DEFAULT;
`007_character_vitals_seed.sql` seeds the rows that EXIST when it runs and the
ledger stops it ever running again.  So on a FRESH INSTALL -- where 007 runs
against an empty table -- every character born afterwards holds NULL in all
three, forever.  A character with no HP cannot be damaged, cannot be healed,
and composes with a named gap instead of a number.

WHAT THIS FILE IS.  `SeedsACohortNotADatabaseTests` in
`tests/test_persistence_vitals_seed_007.py` deliberately accepts EITHER
adjudicated state, so that the day chief lands the insertion point
`COO-DECISION 20260902_0444` ordered, nothing in this lane's files goes red
inside his pull request.  The cost of that choice is what COO named in
`1546`: WHICH of the two states the repository is in stopped being said out
loud anywhere, and that class's docstring even points at a
`test_which_state_this_repository_is_in_is_reported` that was never written.
This file is that missing report -- "a pin, not silence" in COO's words.

WHAT IT DOES *NOT* CLAIM TO BE THE ONLY COPY OF.  The `require()` and census
assertions below overlap `ItSaysNoneAndNeverANumberTests` and
`CensusAfterMigrationTests` on purpose; they are here so that "the hole is
open" costs something a reader can see rather than being an empty dict.  The
census is graded against RAW SQL over the same file, never against a
hardcoded zero, because a hardcoded zero can only be right in one of the two
states this file claims to grade -- a `pf-adversary` pass refused an earlier
version of the neighbouring test for exactly that.  The genuinely new
sentence here is the branchless one: TODAY, the state is UNSEEDED.

WHAT IT COSTS THE PLUG'S OWN PULL REQUEST, said here rather than discovered
by the person who lands it.  This pin goes RED the day the hole is closed.
That is deliberate: COO ordered a pin, and a pin that is green in both states
is silence.  What this file owes in exchange is that the red is CHEAP and
HONEST -- a failure whose whole message is the two edits that retire it, and
which is only raised once the plug has been shown to be RIGHT (see below).

THE SHAPE THAT WAS TRIED FIRST AND MEASURED WRONG.  The first draft skipped
instead of failing on the plugged branch, on the theory that a skip is
visible under `pytest -rs` and never red.  It is red, just somewhere worse:
`.github/workflows/gate-windows.yml:454` runs
`tools/pf_pytest_precondition_census.py`, which emits UNDECLARED SKIP -- and
`gate-windows.yml` exits 1 on it -- for any skip whose reason carries no
`[precondition:<key>]` token and is not in the `design_skips` pin.  That pin
lives in `docs/PYTEST_SKIP_PINS.json`, chief's zone, which this lane may not
edit to declare the skip in advance and which could not hold it anyway
because the same tool exits 1 on "a pinned skip that did not happen".  So the
skip would have turned the gate red for chief with an opaque census exit code
instead of a test failure carrying its own instructions.  A worse red, bought
by pretending there was none.

*** WHY THIS TEST BUILDS FOUR CHARACTERS AND A SESSION, AND NOT ONE.  A
`pf-adversary` pass drove SEVEN wrong plugs through the one-character version
of this file and every single one produced the retirement message -- whose
first words are "THIS IS NOT A DEFECT IN YOUR CHANGE" -- including an UPDATE
with no WHERE clause at all, which resets every character in the database to
`1, 100/100`.  It also found THREE wrong plugs that left it fully GREEN,
publishing "the hole is still open" while a birth write had landed.  One
character on a new account at selector 0 on the non-retry branch is the
exact fixture shape this lane's OWN file
(`test_persistence_vitals_seed_007.py`, `_second_birth`) documents as already
refuted, and `tests/pf_birth_state.py` ships `measure_every_birth` for
precisely this reason.  The first draft imported that module and did not call
that function.  So the population below is chosen so that each refuted shape
separates:

  * a VETERAN whose vitals are written before anything else is created --
    a plug with no WHERE, or `WHERE account_id=?`, or `WHERE id=(SELECT
    MIN(id)...)`, stomps it, and the retirement branch is never reached;
  * a SECOND character on the same account at selector 1 -- a plug that fires
    only for the account's first character, or only for `selector == 0`, or
    only from the second character onward, leaves the population in a
    PARTIAL state, which is its own named failure and not the all-clear;
  * a RETRY create with the second character's own fingerprint -- the
    retransmitted-create-packet branch, the one shape a `pf-adversary` pass
    measured turning a veteran at `level 9, hp 480/500` into `1, 100/100`,
    and the one the one-character version never executed at all;
  * a THIRD character at selector 0 of a SECOND account -- so "first
    character" and "selector 0" cannot be confused with "every character";
  * a LOGIN (`open_session` + `select_character`) after all of it -- a plug
    written into the select path instead of the create path is a plug in the
    wrong lifecycle event, and without this the pin cannot tell it from no
    plug at all.

WHAT IT STILL DOES NOT COVER, so the next reader does not have to find out
the hard way: it does not check that other TABLES (positions, backpacks) or
non-vital columns survived a creation, and it does not reach a plug installed
somewhere neither `create_character` nor `select_character` runs.  Those are
`SeedsACohortNotADatabaseTests`' and a later round's, not this file's.

WHICH DECISION THE ACCEPTED STATES ARE PINNED TO.  `pf_birth_state.
measure_birth_typed_state` accepts exactly two states, and the seeded one is
`COO-DECISION 20260902_0444` (three vitals, nothing else).  A birth that also
carries `speed_walk = 400.0` is refused by that module under `COO-DECISION
20260901_1447` point 2.  `migrations/008_character_speed_walk_seed.sql`
reports the resulting asymmetry to COO as an OPEN question, so if COO later
closes it by seeding speed at birth, this pin goes red saying "defect in the
insertion point" over a change that is correct.  That would be a pin held
against a superseded decision, not a defect in the plug: the fix then is to
retire this file and let `pf_birth_state` be amended, not to argue with it
here.
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

#: What a veteran holds before any of the newborns exist.  A plug that reaches
#: an existing row turns these into the birth values, which is the damage the
#: retry-branch scenario in `test_persistence_vitals_seed_007.py` measured.
VETERAN = {"level": 9, "hp_current": 480, "hp_max": 500}

#: BOTH edits, because a `pf-adversary` pass executed the one-edit version of
#: this instruction and it left the suite red in a second LANE-DB file.
DELETE_ME_WHEN_THE_PLUG_LANDS = (
    "THIS IS NOT A DEFECT IN YOUR CHANGE -- IT IS THIS PIN RETIRING.  Every "
    "character born on a fresh install now holds exactly the birth vitals, "
    "no existing character was touched, the retry branch changed nothing, "
    "and logging in changed nothing -- so the birth hole COO-DECISION "
    "20260902_1546 told LANE-DB to pin is CLOSED and the pin is finished.  "
    "TWO edits retire it, and it must be BOTH or the suite stays red: "
    "(1) delete tests/test_persistence_birth_hole_pin.py, the whole file; "
    "(2) delete the 'tests/test_persistence_birth_hole_pin.py' entry, and "
    "its comment, from ALLOWED_TO_NAME_THEM in "
    "tests/test_persistence_vitals.py -- "
    "NothingIsWiredTests.test_every_allowed_file_exists_and_really_names_them "
    "asserts every entry still resolves to a file, so deleting only (1) "
    "trades this failure for that one.  LANE-DB gives written permission for "
    "both in round dgx8e5 and in the letter to chief of the same round, so "
    "the write-zone rule is not in your way.  Your plug stays graded, in "
    "files you do not have to touch, by SeedsACohortNotADatabaseTests in "
    "tests/test_persistence_vitals_seed_007.py."
)

PARTIAL = (
    "A PARTIAL BIRTH SEED, AND THIS IS A DEFECT IN THE INSERTION POINT.  "
    "Some characters born on this fresh install hold the birth vitals and "
    "others hold nothing, so the database now contains two kinds of "
    "character.  The shapes that do this, all of them measured green against "
    "an earlier version of this file: seeding only the account's FIRST "
    "character, seeding only when selector == 0, and seeding from the SECOND "
    "character onward.  Per-character state, in creation order "
    "(account A selector 0, account A selector 1, account B selector 0): %r"
)


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _build_wire_second_account(selector):
    """A second account's selectors also start at zero, and
    `004_character_soft_delete_reuse.sql` puts a partial UNIQUE index on
    `(identity_lo, identity_hi)`."""
    return b"wire", b"avatar", 0x40000001 + selector, 0


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

    def _create(self, store, account_id, name, tag, build, x):
        return store.create_character(
            account_id, name, name.casefold(), "fingerprint-%s" % tag,
            build, Position(3, 0, x, 2.0, 3.0, heading=0.0))

    def _raw_census(self):
        """The census numbers, counted with raw SQL over the same file.

        The reader under test must not also be the source of its own
        expectation -- a `pf-adversary` pass refused the neighbouring test for
        deriving one from the other, and a hardcoded zero here would be a
        harder version of the same mistake, since zero can only be correct in
        one of the two states this file exists to tell apart.
        """
        columns = list(vitals.VITAL_COLUMNS)
        parts = ["COUNT(*)", "SUM(deleted_at IS NULL)"]
        for column in columns:
            parts.append("SUM(%s IS NOT NULL)" % column)
            parts.append(
                "SUM(%s IS NOT NULL AND deleted_at IS NULL)" % column)
        db = sqlite3.connect(self.path)
        try:
            row = db.execute(
                "SELECT %s FROM characters" % ",".join(parts)).fetchone()
        finally:
            db.close()
        counted = {"characters_any": row[0],
                   "characters_live": row[1]}
        for index, column in enumerate(columns):
            counted["%s_seeded_any" % column] = row[2 + index * 2]
            counted["%s_seeded_live" % column] = row[3 + index * 2]
        return {key: (0 if value is None else int(value))
                for key, value in counted.items()}

    def test_a_character_born_on_a_fresh_install_still_holds_no_vital(self):
        """THE PIN.  Green today over the open hole; one named failure, whose
        message is the whole instruction, once the hole is really closed."""
        store = self._fresh_install()

        # The guard against a vacuously green pin, IN THE SAME DATABASE the
        # rest of this test measures.  A fixture that stopped before `006`
        # would report "no vital on a newborn" because there is nowhere to
        # put one, and would keep passing after the hole was closed.  (The
        # earlier version asserted `ledger == directory`, which `migrate()`
        # makes true by construction and which therefore could never fire --
        # and it asserted it in a DIFFERENT temporary database from the one
        # holding the row it graded.)
        on_disk = sorted(int(path.name[:3])
                         for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"))
        self.assertIn(6, on_disk, "006 is what adds the columns at all")
        db = sqlite3.connect(self.path)
        try:
            columns = {str(row[1])
                       for row in db.execute("PRAGMA table_info(characters)")}
        finally:
            db.close()
        for column in vitals.VITAL_COLUMNS:
            with self.subTest(column=column):
                self.assertIn(column, columns, "the column is not even there")
                self.assertIn(column, typed.TYPED_COLUMNS)

        # -- the population, in the order the docstring explains --
        account_a = store.ensure_account("account-a")
        veteran = self._create(store, account_a, "Veteran", "veteran",
                               _build_wire, 1.0)
        first_birth = birth_state.measure_birth_typed_state(store, veteran.id)
        store.write_typed_attributes(veteran.id, dict(VETERAN))
        self.assertEqual(store.read_typed_attributes(veteran.id), VETERAN)

        second = self._create(store, account_a, "Rookie", "rookie",
                              _build_wire, 4.0)
        again = self._create(store, account_a, "Rookie", "rookie",
                             _build_wire, 4.0)
        self.assertEqual(
            again.id, second.id,
            "the retry branch made a second row instead of returning the "
            "existing one; this test's retry coverage is not measuring what "
            "it claims to")

        account_b = store.ensure_account("account-b")
        third = self._create(store, account_b, "Stranger", "stranger",
                             _build_wire_second_account, 7.0)

        # -- what no plug may do, whatever else it does --
        self.assertEqual(
            store.read_typed_attributes(veteran.id), VETERAN,
            "creating characters changed an EXISTING character's vitals.  "
            "That is an UPDATE with no WHERE, or WHERE account_id=?, or "
            "WHERE id=(SELECT MIN(id)...), and it silently resets real "
            "players.  Not a pin retirement -- a defect.")

        # `measure_every_birth` over the two characters that have not been
        # written to.  The veteran is deliberately NOT in that list: it holds
        # `VETERAN` by now, which is not a birth state and which the helper
        # would refuse -- its birth was measured, by the same helper, before
        # anything wrote to it (`first_birth` above).  Grading it again here
        # would turn "the veteran survived" into a crash instead of the named
        # failure two lines up.
        births = [first_birth] + birth_state.measure_every_birth(
            store, [second.id, third.id])

        seeded = birth_state.seeded_birth()
        present = [state == seeded for state in births]

        if all(present):
            # A plug is in, it reached every character, it left the veteran
            # alone, the retry changed nothing, and login changed nothing.
            session = store.open_session(account_b)
            store.select_character(session, third.selector)
            self.assertEqual(
                store.read_typed_attributes(third.id), seeded,
                "logging in changed a character's vitals")
            self.fail(DELETE_ME_WHEN_THE_PLUG_LANDS)
        if any(present):
            self.fail(PARTIAL % (births,))

        # -- the hole is open.  Everything below is what that costs --
        for index, state in enumerate(births):
            with self.subTest(character=index):
                self.assertEqual(state, {})

        # A plug written into the LOGIN path rather than the creation path is
        # a plug in the wrong lifecycle event; without this the pin cannot
        # tell it from no plug at all, and would publish "hole open" over a
        # database whose characters get vitals the moment anyone plays them.
        session = store.open_session(account_b)
        store.select_character(session, third.selector)
        self.assertEqual(
            store.read_typed_attributes(third.id), {},
            "selecting a character wrote vitals: the birth seed landed in "
            "select_character rather than create_character")

        resolution = store.read_character_vitals(third.id)
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

        # The census, graded against raw SQL over the same file rather than
        # against a number typed here.
        counted = self._raw_census()
        census = store.vitals_seeding_census()
        self.assertEqual(
            {key: census[key] for key in counted}, counted,
            "vitals_seeding_census disagrees with the rows on disk")
        self.assertEqual(counted["characters_any"], 3)
        for column in vitals.VITAL_COLUMNS:
            with self.subTest(column=column):
                # exactly the veteran, which this test wrote itself
                self.assertEqual(counted["%s_seeded_any" % column], 1)


if __name__ == "__main__":
    unittest.main()
