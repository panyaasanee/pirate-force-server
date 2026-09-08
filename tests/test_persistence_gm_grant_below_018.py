"""LANE-DB: `grant_gm_skills` on a database that has not applied `018`.

WHAT THIS FILE PAYS.  pf-adversary finding D3 against round `fw2hs6`
(`pf_bridge/rounds/DB_20260908_1602_fw2hs6_addendum_pf-adversary-not-
clean.md`), measured on a real database:

    ledger max version: 17
    grant_gm_skills(cid, tuple(range(1000,1300)))  ->  returned normally
    rows in character_skills after a 300-skill /skill all: 1

`INSERT OR IGNORE` swallows a CHECK violation exactly as quietly as it
swallows the UNIQUE conflict it is there for, and `'gm_grant'` only becomes
a legal `source` in `migrations/018_character_skills_gm_grant_source.sql`.
So on any database still at `017` the operator saw `/skill all` succeed and
got nothing -- the exact opposite of the door's own docstring sentence
("Nothing is written when anything is refused"), and a false success is
worse than a refusal because nobody goes looking.

WHY THE FIX IS A READ-BACK AND NOT A LEDGER LOOKUP.  The door already reads
the row back (that is its return value), so the proof is free and, more to
the point, it measures the OUTCOME rather than a proxy for it: a database
whose `source` CHECK was widened by hand, or narrowed again by a later
migration, is answered correctly by "did the rows arrive", and not by "what
number is in `schema_migrations`".

WHAT THIS FILE DOES NOT CLAIM.  It does not claim the owner's canonical
database was ever in this state -- `SQLiteStore.migrate()` runs every
pending file at boot, so a server that boots normally is at the newest
migration before any door opens.  It claims the door no longer reports a
success it did not have.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position       # noqa: E402
from pirateforce_foundation.store import SQLiteStore    # noqa: E402

MIGRATIONS = ROOT / "migrations"
_HOME = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class GrantGmSkillsBelow018Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upto_017 = self.root / "upto_017"
        self.upto_017.mkdir()
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name[:3].isdigit() and int(path.name[:3]) <= 17:
                shutil.copy(path, self.upto_017 / path.name)
        self.path = self.root / "below018.sqlite3"
        self.store = SQLiteStore(self.path, self.upto_017)
        self.store.migrate()
        account_id = self.store.ensure_account("below-018")
        self.character_id = self.store.create_character(
            account_id, "Below", "below", "fp-below", _build_wire, _HOME,
        ).id

    def _rows(self):
        db = sqlite3.connect(str(self.path))
        try:
            return [tuple(r) for r in db.execute(
                "SELECT skill_id,source FROM character_skills ORDER BY id")]
        finally:
            db.close()

    def test_the_ledger_really_stops_at_017(self):
        """The fixture is only worth anything if it is the state the
        finding was measured in."""
        db = sqlite3.connect(str(self.path))
        try:
            versions = [int(r[0]) for r in db.execute(
                "SELECT version FROM schema_migrations")]
        finally:
            db.close()
        self.assertEqual(max(versions), 17)

    def test_a_three_hundred_id_grant_raises_instead_of_lying(self):
        with self.assertRaises(RuntimeError) as caught:
            self.store.grant_gm_skills(
                self.character_id, tuple(range(1000, 1300))
            )
        self.assertIn("018", str(caught.exception))

    def test_and_writes_nothing_at_all(self):
        with self.assertRaises(RuntimeError):
            self.store.grant_gm_skills(
                self.character_id, tuple(range(1000, 1300))
            )
        self.assertEqual(self._rows(), [])

    def test_the_rollback_leaves_no_open_transaction_behind(self):
        """A door that raises inside `BEGIN IMMEDIATE` must not leave the
        write lock held, or the next caller times out for a reason that
        has nothing to do with itself."""
        with self.assertRaises(RuntimeError):
            self.store.grant_gm_skills(self.character_id, (1000,))
        self.store.grant_starting_skills(self.character_id, (99, 210))
        self.assertEqual(
            self._rows(), [(99, "starting_kit"), (210, "starting_kit")]
        )

    def test_a_mixed_call_reports_the_number_it_actually_counted(self):
        """PAYS pf-adversary D5 (round `6vv9mi`): the first version of the
        message said "wrote none of N ids ... every INSERT OR IGNORE was
        swallowed" no matter what it had counted.  On a call where three of
        four ids were already on the row, only the fourth was swallowed and
        the sentence was false."""
        self.store.grant_starting_skills(self.character_id, (7, 8, 9))
        with self.assertRaises(RuntimeError) as caught:
            self.store.grant_gm_skills(self.character_id, (7, 8, 9, 4242))
        self.assertIn("1 of 4 id(s)", str(caught.exception))
        self.assertIn("4242", str(caught.exception))

    def test_a_call_whose_ids_are_all_already_held_does_not_raise(self):
        """And it must not: at `018` the same call also writes zero rows,
        because `OR IGNORE` skips every id the row already carries.  The
        check asks "did every id arrive", not "did this call mint a
        gm_grant row" -- a door that raised here would refuse the one case
        where 017 and 018 behave identically.  NONCLAIM, named rather than
        hidden: that is exactly the case this guard cannot see, and it is
        also the case where there is nothing to see."""
        self.store.grant_starting_skills(self.character_id, (7, 8, 9))
        self.assertEqual(
            self.store.grant_gm_skills(self.character_id, (7, 8, 9)),
            (7, 8, 9),
        )
        self.assertEqual(
            self._rows(),
            [(7, "starting_kit"), (8, "starting_kit"), (9, "starting_kit")],
        )

    def test_the_sibling_doors_are_unaffected_at_017(self):
        """`'starting_kit'` and `'learned'` were legal in the migration
        that created the table and in `014`; neither sibling needs the
        check and neither may have gained a new refusal."""
        self.store.grant_starting_skills(self.character_id, (99, 210))
        self.store.grant_learned_skill(self.character_id, 511)
        self.assertEqual(
            self._rows(),
            [(99, "starting_kit"), (210, "starting_kit"), (511, "learned")],
        )


class GrantGmSkillsAt018IsUnchangedTests(unittest.TestCase):
    """The other half of the fix: every path that already worked still
    does.  Measured on the full migrations directory, so `019` is applied
    too -- a new migration must not disturb a door built on `018`."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "at018.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        account_id = self.store.ensure_account("at-018")
        self.character_id = self.store.create_character(
            account_id, "At18", "at18", "fp-at18", _build_wire, _HOME,
        ).id

    def test_a_grant_lands_every_id(self):
        granted = self.store.grant_gm_skills(
            self.character_id, tuple(range(1000, 1300))
        )
        self.assertEqual(len(granted), 300)

    def test_running_it_twice_is_a_no_op_not_a_raise(self):
        """The idempotence the door exists for must not be turned into a
        failure by a check that cannot tell "already there" from "never
        arrived"."""
        first = self.store.grant_gm_skills(self.character_id, (7, 8, 9))
        second = self.store.grant_gm_skills(self.character_id, (7, 8, 9))
        self.assertEqual(first, second)

    def test_an_id_already_held_as_starting_kit_keeps_its_provenance(self):
        self.store.grant_starting_skills(self.character_id, (99, 210))
        self.store.grant_gm_skills(self.character_id, (99, 7))
        db = sqlite3.connect(str(self.path))
        try:
            rows = dict(db.execute(
                "SELECT skill_id,source FROM character_skills"))
        finally:
            db.close()
        self.assertEqual(rows[99], "starting_kit")
        self.assertEqual(rows[7], "gm_grant")

    def test_duplicates_inside_one_call_are_still_folded(self):
        self.assertEqual(
            self.store.grant_gm_skills(self.character_id, (7, 7, 8)), (7, 8)
        )

    def test_an_empty_sequence_is_still_a_value_error(self):
        with self.assertRaises(ValueError):
            self.store.grant_gm_skills(self.character_id, ())


if __name__ == "__main__":
    unittest.main()
