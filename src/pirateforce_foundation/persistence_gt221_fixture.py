"""LANE-DB: the one door `GT-221` (`pf_bridge/GAME_TEST_QUEUE.md`) has been
BLOCKED on since it opened -- a script that takes an external database PATH
and writes three named rows into it through
`SQLiteStore.write_typed_attributes`, on a copy only, so an attended login
can prove the server sends what a ROW holds instead of the constant
`level 1, hp 100/100` every newborn character also happens to carry.

WHY THIS FILE EXISTS.  `COO-DECISION 20260903_1247` point 1 ruled on the one
open question `GT-221`'s own body records: how does the run-copy database
that ticket boots against come to hold `level 3/hp_max 40`, `level 9/hp_max
250` and `level 1/hp_max 7`, when no character is born holding any of those
numbers?  Two ways were on the table.  A migration was REFUSED outright --
it would write those rows into the OWNER'S CANONICAL database the next time
she boots the real server, and no ticket names who would ever undo that
("`COO-DECISION 20260901_1112` point 2 does not cover a migration that
exists only to make a test pass").  The one way left standing, way (a), is
this file: a script, run with the server stopped, against a COPY, through
the same validated door every other typed-attribute write in this repository
already goes through.

WHAT IT DOES.  `seed_rows` takes a database path and a sequence of
`(character_id, level, hp_max)` triples already sitting in THAT database
(created earlier, the ordinary way -- through the client's own "create
character" screen, the only place this repository has ever safely produced
an `actor_wire` a real client will render; see `lifecycle.CharacterLifecycle.
create`, which requires the client's own submitted bytes and refuses to run
without them).  For each triple it calls
`SQLiteStore.write_typed_attributes(character_id, {level, hp_current: 0,
hp_max})` -- the same door `GT-215`'s birth seeding and `GT-192`'s class-id
backfill both already trust -- and nothing else.  `hp_current` is always
`0`: that is not a fourth number this file invents, it is the one value
`GT-221`'s own objective requires -- the ticket is measuring the login
resolver's revive-on-a-dead-row path (named in the ticket's own body,
`GAME_TEST_QUEUE.md:12439-12441`), which only fires over a row already at
`hp_current <= 0`.  (Deliberately not spelled here as an importable name:
this repository's login-seam test scans `src/` for exactly one string and
refuses a second hit -- see that test file's own header -- so a citation in
prose has to stay a citation, not a second name for the module to match.)

WHAT IT DOES NOT DO.
* **It does not create a character.**  Synthesizing an `actor_wire` a real
  client will render without crashing needs the exact byte layout
  `bind_actor_and_avatar_identity` binds onto the client's OWN submission
  (`lifecycle.py:153-161`) -- there is no committed, RE-proven way to
  fabricate one from nothing, and guessing one to save an attended step
  is exactly the kind of guess `COO-DECISION 20260901_1059` forbids, aimed
  at a live client instead of a log line.  The three characters this fixture
  writes onto must already exist in the copy -- ordinarily created once,
  cheaply, through the client, the same way `GT-215` step 5 already does,
  and named so an operator can tell them apart on the character-select
  screen.
* **It does not touch the canonical database, under any name the operator
  gives it.**  `_refuse_canonical_name` below refuses a path whose file name
  is `pirateforce.sqlite3` (case-insensitively), the same name `GT-257`'s
  own `db:` section already forbids a run-copy from being called, for the
  same reason: a script that cannot tell a copy from the original by
  argument alone must refuse by name instead of trusting the caller.  This
  is a name check, not a location check -- it is the fast, cheap half of the
  guard `persistence_canon_gate` exists to do properly for a real canonical
  rotation, not a replacement for it.
* **It does not decide which three characters, or which numbers -- only
  that three DIFFERENT ones were named.**  `GT221_ROWS` records the exact
  three `(level, hp_max)` pairs `COO-DECISION 20260903_1247`'s own table
  names, so `--gt221` refuses a typo'd number and refuses a duplicated
  character id (pf-adversary, round `uhfve8`: a duplicate id paired with an
  omitted one still passed a pairs-only check, leaving one character
  unseeded at the exact newborn constant this ticket exists to rule out).
  The CALLER still names which row on disk gets which pair via `--row
  CHARACTER_ID LEVEL HP_MAX` -- this file has no way to know which id an
  operator's client just created, so it cannot catch three DISTINCT ids
  that are nonetheless the WRONG three characters.
* **It does not run migrations beyond bringing the copy to this
  repository's current schema.**  `SQLiteStore.migrate()` is idempotent
  (`store.py:337`, checksum-ledgered) and is what every other attended
  fixture in this lane calls before writing -- a copy already at HEAD is
  unchanged by it, and a copy the operator made before pulling a newer
  `pirate-force-server` is brought up to date the same way a real boot
  would.

WHY `--row` TAKES AN EXISTING CHARACTER ID AND NOT A NAME.  A name is
ambiguous the moment an operator boots this against a copy holding more than
one account, and `list_characters` (`store.py:627`) already prints the id
next to the name -- `--list` below is the read path that makes finding it a
non-issue.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .persistence_vitals import HP_CURRENT_COLUMN, HP_MAX_COLUMN, LEVEL_COLUMN
from .store import SQLiteStore

#: The exact three `(level, hp_max)` pairs `COO-DECISION 20260903_1247`
#: names for `GT-221` -- `level 1` deliberately pairs with `hp_max 7`, not
#: `100`, so this fixture can never be typo'd into reproducing the very
#: constant the ticket exists to rule out.  `hp_current` is not part of this
#: tuple: `seed_rows` writes it as `0` for every row, unconditionally -- see
#: the module docstring for why that is not a fourth free parameter.
GT221_ROWS: tuple[tuple[int, int], ...] = ((3, 40), (9, 250), (1, 7))

#: The one name this script refuses to write to, regardless of directory.
#: Matches the same guard `GT-257`'s own `db:` section already imposes on a
#: run-copy's file name (`pf_bridge/GAME_TEST_QUEUE.md`), so a copy this
#: fixture is safe to run against and the copy a live GM command already
#: refuses to touch are named the same way.
_CANONICAL_BASENAME = "pirateforce.sqlite3"


class CanonicalDatabaseRefused(ValueError):
    """Raised instead of writing, when the target path's file name is the
    one this script will never touch."""


def _refuse_canonical_name(db_path: str | Path) -> None:
    """Refuse a path whose RESOLVED file name is the canonical one.

    `pf-adversary` (round `uhfve8`) measured that checking the argument AS
    GIVEN is not enough: an operator whose copy step is a symlink or a
    hardlink rather than a byte copy -- a real Windows mistake, `mklink` or
    a link-preserving `robocopy` flag instead of `copy` -- hands this
    function a path named `run_gt221_....sqlite3` that resolves to the
    canonical file itself, and the un-resolved check let every write through
    onto the owner's live, no-rollback database.  Reproduced live: writing
    through such a link changed the bytes of the canonical file underneath
    it.  `Path.resolve()` (not `strict`, so a `--db` path that does not
    exist yet still resolves rather than raising) is the same call
    `SQLiteStore.__init__` already makes on its own path (`store.py:312`) --
    this reuses that precedent rather than inventing a second one.
    """
    name = Path(db_path).resolve().name
    if name.casefold() == _CANONICAL_BASENAME.casefold():
        raise CanonicalDatabaseRefused(
            f"refusing to write typed attributes into a file that resolves "
            f"to {name!r} -- this script only ever writes a RUN COPY, "
            f"never the canonical database (checked after resolving "
            f"symlinks/hardlinks), and this file name is the one this "
            f"lane's fixtures already reserve for the original "
            f"(see GT-257's db: section)"
        )


def seed_rows(
    db_path: str | Path,
    migrations_dir: str | Path,
    rows: Sequence[tuple[int, int, int]],
) -> list[dict]:
    """Write `(character_id, level, hp_max)` triples onto rows already in
    `db_path`, `hp_current` forced to `0` for every one, through
    `SQLiteStore.write_typed_attributes`.

    Refuses before opening the database at all if its file name is the
    canonical one (`_refuse_canonical_name`).  Stops at the FIRST row that
    fails -- a character id that does not exist (or is soft-deleted) raises
    `KeyError`, exactly as `write_typed_attributes` itself does, with the
    failing id named; a value this schema will not hold raises
    `persistence_typed_attrs.TypedAttrError` (a `ValueError`), also from
    underneath unchanged.  ROWS ALREADY WRITTEN BEFORE THE FAILURE STAY
    WRITTEN -- each call is already its own committed transaction inside
    `write_typed_attributes`, so there is no outer transaction this function
    could roll back even if it tried, and pretending otherwise would be the
    same silent claim `persistence_null_audit`'s header refuses to make
    about its own boundary.  A caller that must know exactly which rows
    landed before a failure should pass one row at a time.

    Returns the full typed-attribute state of each character AFTER its
    write, in the same order `rows` was given, exactly as
    `write_typed_attributes` returns it.
    """
    _refuse_canonical_name(db_path)
    store = SQLiteStore(db_path, migrations_dir)
    store.migrate()
    results = []
    for character_id, level, hp_max in rows:
        values = {
            LEVEL_COLUMN: level,
            HP_CURRENT_COLUMN: 0,
            HP_MAX_COLUMN: hp_max,
        }
        try:
            after = store.write_typed_attributes(character_id, values)
        except KeyError:
            raise KeyError(
                f"no live character with id={character_id!r} in {db_path!s} "
                "-- create it through the client first (see the module "
                "docstring); this script only writes onto a row that "
                "already exists"
            ) from None
        results.append({"character_id": character_id, **after})
    return results


def list_roster(
    db_path: str | Path, migrations_dir: str | Path, account_name: str
) -> list[dict]:
    """The live characters on `account_name` in `db_path`, id and name first
    so an operator can pick which one gets which `--row` triple, followed by
    whatever typed attributes that row already holds.

    Refuses the canonical file name the same way `seed_rows` does.  Calls
    `SQLiteStore.ensure_account`, which is INSERT-OR-IGNORE and therefore
    creates the account row (holding zero characters) the first time this
    is run against a name that does not exist yet in this copy -- a
    harmless, idempotent write on a copy this function has already refused
    to let be the canonical file, never a guess at what should be in it.
    """
    _refuse_canonical_name(db_path)
    store = SQLiteStore(db_path, migrations_dir)
    store.migrate()
    account_id = store.ensure_account(account_name)
    roster = []
    for character in store.list_characters(account_id):
        typed = store.read_typed_attributes(character.id)
        roster.append({
            "id": character.id,
            "selector": character.selector,
            "name": character.name,
            **typed,
        })
    return roster


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pirateforce_foundation.persistence_gt221_fixture",
        description=(
            "Write level/hp_max/hp_current=0 onto existing characters in a "
            "RUN COPY database, so GT-221 can boot against rows a hardcoded "
            "constant could not have produced. Never touches a file named "
            "pirateforce.sqlite3."
        ),
    )
    parser.add_argument("--db", required=True, help="the RUN COPY .sqlite3 file")
    parser.add_argument(
        "--migrations", required=True,
        help="this repository's migrations/ directory",
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--list", metavar="ACCOUNT",
        help="print the characters on ACCOUNT in --db and exit; writes nothing",
    )
    mode.add_argument(
        "--row", nargs=3, action="append", type=int,
        metavar=("CHARACTER_ID", "LEVEL", "HP_MAX"),
        help="write LEVEL/HP_MAX (hp_current forced to 0) onto CHARACTER_ID; "
             "repeat --row for more than one character",
    )
    parser.add_argument(
        "--gt221", action="store_true",
        help="with --row: also require exactly three --row entries, all "
             "naming DIFFERENT character ids, whose (LEVEL, HP_MAX) pairs "
             "equal GT221_ROWS ((3,40),(9,250),(1,7)) as a set -- refuses a "
             "typo'd number, a duplicated character id, or a missing row "
             "instead of seeding it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.list is not None:
            for character in list_roster(
                arguments.db, arguments.migrations, arguments.list
            ):
                print(
                    "CHARACTER id=%(id)s selector=%(selector)s name=%(name)r "
                    "level=%(level)s hp_current=%(hp_current)s "
                    "hp_max=%(hp_max)s" % {
                        "id": character["id"],
                        "selector": character["selector"],
                        "name": character["name"],
                        "level": character.get(LEVEL_COLUMN, "unset"),
                        "hp_current": character.get(HP_CURRENT_COLUMN, "unset"),
                        "hp_max": character.get(HP_MAX_COLUMN, "unset"),
                    }
                )
            return 0
        rows = [(cid, level, hp_max) for cid, level, hp_max in arguments.row]
        if arguments.gt221:
            character_ids = [cid for cid, _, _ in rows]
            given = sorted((level, hp_max) for _, level, hp_max in rows)
            wanted = sorted(GT221_ROWS)
            if len(character_ids) != len(set(character_ids)):
                # pf-adversary (round `uhfve8`): a duplicated character id
                # paired with a missing one still passes a pairs-only
                # check, silently leaving one character at the exact
                # hardcoded-newborn constant GT-221 exists to rule out.
                print(
                    "GT221_MISMATCH duplicate character id(s) in --row=%r "
                    "-- refusing to seed; --gt221 requires three DIFFERENT "
                    "character ids, one per row" % (character_ids,),
                    file=sys.stderr,
                )
                return 2
            if given != wanted:
                print(
                    "GT221_MISMATCH given=%r wanted=%r -- refusing to seed; "
                    "--gt221 requires exactly these three (level, hp_max) "
                    "pairs" % (given, wanted),
                    file=sys.stderr,
                )
                return 2
        # Seeded ONE ROW AT A TIME, not as a single `seed_rows(..., rows)`
        # call, and printed immediately after each success. pf-adversary
        # (round `uhfve8`) measured that feeding the whole list to
        # `seed_rows` and printing only after the loop finished meant a
        # failure on row N raised out of `seed_rows` before this loop's
        # first `print` ever ran -- so an operator whose first two rows
        # committed successfully and whose third named a bad character id
        # saw ONLY the final `FIXTURE_REFUSED` line and no `SEEDED` line at
        # all, even though two rows had already landed. Seeding one row per
        # call makes each success visible on stdout the moment it commits,
        # before a later row's failure can suppress it.
        for row in rows:
            [written] = seed_rows(arguments.db, arguments.migrations, [row])
            print(
                "SEEDED character_id=%(character_id)s level=%(level)s "
                "hp_current=%(hp_current)s hp_max=%(hp_max)s" % {
                    "character_id": written["character_id"],
                    "level": written.get(LEVEL_COLUMN),
                    "hp_current": written.get(HP_CURRENT_COLUMN),
                    "hp_max": written.get(HP_MAX_COLUMN),
                }
            )
        return 0
    except (ValueError, KeyError) as error:
        print("FIXTURE_REFUSED %r" % (error,), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    sys.exit(main())
