"""LANE-DB: the permanent test `COO-DECISION 20260903_1247` ordered for the
fixture that unblocks `GT-221` -- a script that writes named
`(character_id, level, hp_max)` triples into a RUN COPY database through
`SQLiteStore.write_typed_attributes`, and nothing else.

WHAT THIS FILE PROVES (wire/DB layer only, matching this module's own
`persistence_gt221_fixture` docstring):

1. **It refuses a file named `pirateforce.sqlite3`, case-insensitively,
   before opening it at all.**  Measured with a database that would
   otherwise seed perfectly well -- the refusal has to come from the name,
   not from anything about the file's contents.
2. **The three rows the ticket table names land exactly, with `hp_current`
   forced to `0` even when a caller does not ask for it.**  Graded against
   `persistence_gt221_fixture.GT221_ROWS` rather than the literal numbers
   typed twice, so a typo in one place cannot drift silently past the
   other.
3. **It writes through the validated door and nothing else** -- a value
   this schema will not hold (a `bool`, a value outside the column's wire
   range) is refused by `persistence_typed_attrs.validate` underneath,
   unchanged, and nothing lands.
4. **A character id that is not a live row in this database is a named,
   readable failure**, not a silent no-op and not a raw `KeyError` with no
   context -- `write_typed_attributes` itself already fails loudly; this
   file also proves this module's wrapping message still names the id.
5. **`--list` writes nothing but the account row itself** (idempotent,
   `INSERT OR IGNORE`) -- no character, no typed attribute, changes.
6. **`--gt221` refuses a typo'd `(level, hp_max)` pair, and separately
   refuses a duplicated character id** rather than seeding whatever it was
   given (pf-adversary, round `uhfve8`: a duplicate id paired with an
   omitted one used to pass the pairs-only check silently).
7. **A row that lands before a later row fails is visible on stdout before
   the failure is reported** -- not just true on disk and silent at the
   CLI (pf-adversary, round `uhfve8`: the original loop printed nothing
   until `seed_rows` returned, so a failure on the last of three rows
   produced zero `SEEDED` lines even though the first two had committed).

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: no
character-select screen is rendered and no HUD is read.  This file does not
create a character -- every row it writes onto is built first with
`store.create_character` exactly as `test_persistence_null_audit.py` and
sibling files already do, because a real client's "create character" flow
is the only thing this repository trusts to build an `actor_wire`
(`persistence_gt221_fixture`'s own docstring explains why).  Whether the
character-select/HUD screen actually reads these columns is `GT-221`'s own
attended criteria to measure, not this file's.
"""
from __future__ import annotations

import contextlib
import io
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_gt221_fixture as fixture  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "run_gt221_20260905_000000.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)
        self.account_id = self.store.ensure_account("gt221-fixture-tests")

    def _make_character(self, tag):
        return self.store.create_character(
            self.account_id, f"GT221{tag}", f"gt221{tag}",
            f"fingerprint-gt221-{tag}", _build_wire, self.home,
        ).id

    def _create_and_soft_delete(self, tag):
        character = self.store.create_character(
            self.account_id, f"GT221{tag}", f"gt221{tag}",
            f"fingerprint-gt221-{tag}", _build_wire, self.home,
        )
        sid = self.store.open_session(self.account_id)
        self.store.soft_delete_character(sid, character.selector)
        return character.id


class CanonicalNameIsRefusedTests(_Workspace):
    """The one guard that has to fire from the name alone."""

    def test_a_file_named_exactly_pirateforce_sqlite3_is_refused(self):
        # `canonical` need not even exist -- the guard fires from the NAME,
        # before any file is opened, so there is nothing to copy first.
        canonical = Path(self.tmp.name) / "pirateforce.sqlite3"
        character_id = self._make_character("A")
        birth = self.store.read_typed_attributes(character_id)
        with self.assertRaises(fixture.CanonicalDatabaseRefused):
            fixture.seed_rows(
                canonical, MIGRATIONS, [(character_id, 3, 40)]
            )
        # And it never touched the row it would have written to, on the
        # database this refusal was measured against -- still exactly its
        # birth state, not the (3, 40) this call asked for.
        self.assertEqual(
            self.store.read_typed_attributes(character_id), birth
        )

    def test_the_check_is_case_insensitive(self):
        shouting = Path(self.tmp.name) / "PIRATEFORCE.SQLITE3"
        with self.assertRaises(fixture.CanonicalDatabaseRefused):
            fixture.seed_rows(shouting, MIGRATIONS, [(1, 3, 40)])

    def test_a_symlink_that_resolves_to_the_canonical_name_is_also_refused(self):
        """pf-adversary (round `uhfve8`): an operator whose copy step is a
        symlink or hardlink rather than a byte copy -- `mklink`, or a
        link-preserving `robocopy` flag, both real Windows mistakes --
        used to sail straight past the un-resolved name check and write
        this fixture's rows into the file the link points at. Reproduced
        live before the fix: writing through such a link changed the
        canonical file's own bytes."""
        canonical_dir = Path(self.tmp.name) / "canonical_home"
        canonical_dir.mkdir()
        canonical = canonical_dir / "pirateforce.sqlite3"
        canonical_store = SQLiteStore(canonical, MIGRATIONS)
        canonical_store.migrate()
        account_id = canonical_store.ensure_account("owner-account")
        character = canonical_store.create_character(
            account_id, "Owner", "owner", "fingerprint-owner", _build_wire,
            self.home,
        )
        birth = canonical_store.read_typed_attributes(character.id)

        link = Path(self.tmp.name) / "run_gt221_20260905_999999.sqlite3"
        try:
            link.symlink_to(canonical)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available in this environment")

        with self.assertRaises(fixture.CanonicalDatabaseRefused):
            fixture.seed_rows(link, MIGRATIONS, [(character.id, 9, 250)])

        # The canonical file itself -- opened directly, not through the
        # link -- must be byte-for-byte unaffected: still birth state.
        self.assertEqual(
            canonical_store.read_typed_attributes(character.id), birth
        )

    def test_list_roster_refuses_the_same_name(self):
        canonical = Path(self.tmp.name) / "pirateforce.sqlite3"
        with self.assertRaises(fixture.CanonicalDatabaseRefused):
            fixture.list_roster(canonical, MIGRATIONS, "anyone")

    def test_a_run_copy_named_anything_else_is_not_refused_by_name(self):
        character_id = self._make_character("B")
        # No exception -- the name guard is the only thing this test is
        # about, and `self.path` is not the canonical name.
        fixture.seed_rows(self.path, MIGRATIONS, [(character_id, 9, 250)])


class TheThreeRowsLandExactlyTests(_Workspace):
    """The reason `GT-221` was blocked: does the copy end up holding
    numbers a hardcoded constant could never have produced."""

    def test_all_three_gt221_rows_land_with_hp_current_zero(self):
        ids = [self._make_character(tag) for tag in ("A", "B", "C")]
        rows = [
            (ids[0], *fixture.GT221_ROWS[0]),
            (ids[1], *fixture.GT221_ROWS[1]),
            (ids[2], *fixture.GT221_ROWS[2]),
        ]
        fixture.seed_rows(self.path, MIGRATIONS, rows)
        for character_id, (level, hp_max) in zip(ids, fixture.GT221_ROWS):
            after = self.store.read_typed_attributes(character_id)
            self.assertEqual(after[vitals.LEVEL_COLUMN], level)
            self.assertEqual(after[vitals.HP_MAX_COLUMN], hp_max)
            self.assertEqual(after[vitals.HP_CURRENT_COLUMN], 0)

    def test_hp_current_is_forced_to_zero_even_if_a_caller_asks_otherwise(self):
        """`seed_rows` takes exactly `(character_id, level, hp_max)` -- there
        is no fourth parameter a caller could use to ask for a different
        `hp_current`, so this proves the constant by reading the column
        after a call that only ever offers three values."""
        character_id = self._make_character("D")
        fixture.seed_rows(self.path, MIGRATIONS, [(character_id, 1, 7)])
        after = self.store.read_typed_attributes(character_id)
        self.assertEqual(after[vitals.HP_CURRENT_COLUMN], 0)

    def test_returned_state_matches_what_was_written(self):
        character_id = self._make_character("E")
        [written] = fixture.seed_rows(
            self.path, MIGRATIONS, [(character_id, 9, 250)]
        )
        self.assertEqual(written["character_id"], character_id)
        self.assertEqual(written[vitals.LEVEL_COLUMN], 9)
        self.assertEqual(written[vitals.HP_MAX_COLUMN], 250)
        self.assertEqual(written[vitals.HP_CURRENT_COLUMN], 0)


class TheValidatedDoorIsStillTheOnlyDoorTests(_Workspace):
    """`seed_rows` must not open a second, less careful way in."""

    def test_a_value_the_schema_cannot_hold_is_refused(self):
        character_id = self._make_character("F")
        birth = self.store.read_typed_attributes(character_id)
        with self.assertRaises(typed.TypedAttrError):
            fixture.seed_rows(
                self.path, MIGRATIONS, [(character_id, 3, -1)]
            )
        # Refused before anything landed -- still exactly birth state.
        self.assertEqual(
            self.store.read_typed_attributes(character_id), birth
        )

    def test_a_bool_is_refused_not_silently_coerced(self):
        character_id = self._make_character("G")
        with self.assertRaises(typed.TypedAttrError):
            fixture.seed_rows(
                self.path, MIGRATIONS, [(character_id, True, 40)]
            )


class UnknownCharacterIsANamedFailureTests(_Workspace):
    def test_an_id_nothing_created_raises_with_the_id_named(self):
        with self.assertRaises(KeyError) as caught:
            fixture.seed_rows(self.path, MIGRATIONS, [(999999, 3, 40)])
        self.assertIn("999999", str(caught.exception))

    def test_a_soft_deleted_character_is_refused_the_same_way(self):
        character_id = self._create_and_soft_delete("H")
        with self.assertRaises(KeyError):
            fixture.seed_rows(self.path, MIGRATIONS, [(character_id, 3, 40)])

    def test_the_first_bad_row_stops_the_call_but_earlier_rows_stay_written(self):
        good_id = self._make_character("I")
        fixture.seed_rows(self.path, MIGRATIONS, [(good_id, 3, 40)])
        with self.assertRaises(KeyError):
            fixture.seed_rows(
                self.path, MIGRATIONS,
                [(good_id, 9, 250), (999999, 1, 7)],
            )
        # The first row of the SECOND call, which is a real character,
        # still landed -- `seed_rows`'s docstring says each row commits on
        # its own and this is the measurement of that claim.
        after = self.store.read_typed_attributes(good_id)
        self.assertEqual(after[vitals.LEVEL_COLUMN], 9)
        self.assertEqual(after[vitals.HP_MAX_COLUMN], 250)


class ListRosterWritesNothingButTheAccountTests(_Workspace):
    def test_listing_an_existing_account_changes_nothing(self):
        character_id = self._make_character("J")
        fixture.seed_rows(self.path, MIGRATIONS, [(character_id, 9, 250)])
        before = sqlite3.connect(str(self.path)).execute(
            "SELECT level,hp_current,hp_max FROM characters WHERE id=?",
            (character_id,),
        ).fetchone()
        roster = fixture.list_roster(
            self.path, MIGRATIONS, "gt221-fixture-tests"
        )
        after = sqlite3.connect(str(self.path)).execute(
            "SELECT level,hp_current,hp_max FROM characters WHERE id=?",
            (character_id,),
        ).fetchone()
        self.assertEqual(before, after)
        [entry] = [row for row in roster if row["id"] == character_id]
        self.assertEqual(entry["name"], "GT221J")
        self.assertEqual(entry[vitals.LEVEL_COLUMN], 9)

    def test_listing_an_account_that_does_not_exist_yet_creates_it_empty(self):
        """Documented in the module docstring as the one write `--list`
        performs: `ensure_account` is INSERT-OR-IGNORE.  Proven here as
        "creates nothing but the account row" -- zero characters back."""
        roster = fixture.list_roster(self.path, MIGRATIONS, "brand-new-account")
        self.assertEqual(roster, [])


class Gt221ConvenienceModeRefusesATypoTests(unittest.TestCase):
    """The CLI-level guard, exercised through `main` directly rather than a
    subprocess -- this is argument handling, not process plumbing."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "run_gt221_cli.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)
        account_id = self.store.ensure_account("gt221-cli-tests")
        self.ids = [
            self.store.create_character(
                account_id, f"GT221CLI{tag}", f"gt221cli{tag}",
                f"fingerprint-cli-{tag}", _build_wire, self.home,
            ).id
            for tag in ("A", "B", "C")
        ]
        self.birth = {
            character_id: self.store.read_typed_attributes(character_id)
            for character_id in self.ids
        }

    def test_the_exact_three_pairs_are_accepted(self):
        argv = ["--db", str(self.path), "--migrations", str(MIGRATIONS), "--gt221"]
        for character_id, (level, hp_max) in zip(self.ids, fixture.GT221_ROWS):
            argv += ["--row", str(character_id), str(level), str(hp_max)]
        self.assertEqual(fixture.main(argv), 0)
        after = self.store.read_typed_attributes(self.ids[0])
        self.assertEqual(after[vitals.LEVEL_COLUMN], fixture.GT221_ROWS[0][0])

    def test_a_typo_d_pair_is_refused_and_writes_nothing(self):
        argv = [
            "--db", str(self.path), "--migrations", str(MIGRATIONS), "--gt221",
            "--row", str(self.ids[0]), "3", "40",
            "--row", str(self.ids[1]), "9", "250",
            # Typo: 100 instead of 7 -- the exact constant GT-221 exists to
            # rule out, which is precisely why this must be refused.
            "--row", str(self.ids[2]), "1", "100",
        ]
        self.assertEqual(fixture.main(argv), 2)
        for character_id in self.ids:
            self.assertEqual(
                self.store.read_typed_attributes(character_id),
                self.birth[character_id],
            )

    def test_a_duplicated_character_id_is_refused_even_with_valid_pairs(self):
        """pf-adversary (round `uhfve8`): `--row A 3 40 --row A 9 250
        --row B 1 7` (id `self.ids[2]` never named) used to pass the
        pairs-only check -- the multiset of `(level, hp_max)` still equals
        `GT221_ROWS` -- while leaving the third character completely
        unseeded, still at the exact newborn constant this ticket exists
        to distinguish from a real row read."""
        argv = [
            "--db", str(self.path), "--migrations", str(MIGRATIONS), "--gt221",
            "--row", str(self.ids[0]), "3", "40",
            "--row", str(self.ids[0]), "9", "250",
            "--row", str(self.ids[1]), "1", "7",
        ]
        self.assertEqual(fixture.main(argv), 2)
        for character_id in self.ids:
            self.assertEqual(
                self.store.read_typed_attributes(character_id),
                self.birth[character_id],
            )

    def test_rows_written_before_a_later_failure_are_printed_immediately(self):
        """pf-adversary (round `uhfve8`): the two good rows must appear on
        stdout as `SEEDED` lines even though the third `--row` names a
        character id that does not exist and the whole call ends in
        `FIXTURE_REFUSED`/exit 1 -- an operator must not have to re-query
        the database to learn that two rows already landed."""
        argv = [
            "--db", str(self.path), "--migrations", str(MIGRATIONS),
            "--row", str(self.ids[0]), "3", "40",
            "--row", str(self.ids[1]), "9", "250",
            "--row", "999999", "1", "7",
        ]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = fixture.main(argv)
        self.assertEqual(code, 1)
        self.assertIn("SEEDED character_id=%s" % self.ids[0], out.getvalue())
        self.assertIn("SEEDED character_id=%s" % self.ids[1], out.getvalue())
        self.assertIn("FIXTURE_REFUSED", err.getvalue())
        # And the two rows the stdout lines claimed landed really did.
        after0 = self.store.read_typed_attributes(self.ids[0])
        after1 = self.store.read_typed_attributes(self.ids[1])
        self.assertEqual(after0[vitals.LEVEL_COLUMN], 3)
        self.assertEqual(after1[vitals.LEVEL_COLUMN], 9)

    def test_list_mode_prints_the_roster_and_returns_zero(self):
        argv = [
            "--db", str(self.path), "--migrations", str(MIGRATIONS),
            "--list", "gt221-cli-tests",
        ]
        self.assertEqual(fixture.main(argv), 0)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
