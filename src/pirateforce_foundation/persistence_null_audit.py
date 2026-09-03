"""LANE-DB: how many rows on THIS database still hold NULL in a column
somebody has adjudicated a value for.

WHY IT EXISTS.  `COO-DECISION 20260903_1047` point 2.  Four typed columns
have an adjudicated birth value and carry it as a schema DEFAULT since
`migrations/009_character_birth_defaults.sql`: `level`, `hp_current`,
`hp_max`, `speed_walk`.  A DEFAULT reaches rows INSERTed after `009` ran; it
does not reach a row that already existed holding NULL, and `009` backfills
nothing.  `007` and `008` seeded the cohort that existed when THEY ran
(`008`'s whole body is
`UPDATE characters SET speed_walk = 400.0 WHERE speed_walk IS NULL;`), so
the window is the gap BETWEEN the two migrations, stated exactly: a
character created after `008` ran and before `009` ran can still hold NULL
in a column the schema now says has a value.  A row older than `008` is not
in it, and a row younger than `009` is not in it either.

!! THAT IS ONE WINDOW OF THE TWO, and it is the only one measured.  The
three vitals have a window of their own -- between `007` and the round that
made `SQLiteStore.create_character` write them into the INSERT -- and this
module audits them without rehearsing it: the tests build the `speed_walk`
window and then assert the three vitals come back `0` in it.  So for three
of the four audited columns this module counts something it has not
demonstrated can be nonzero on a real upgrade path.  That is a gap in the
EVIDENCE, not in the query, and it is written here rather than left for a
reader of a clean sheet to assume the other way.

!! A ZERO FROM THIS MODULE IS THEREFORE TWO DIFFERENT ANSWERS, and a reader
who cannot tell them apart will read the wrong one.  A database that met
`008` and `009` IN THE SAME BOOT has a window of zero WIDTH -- no row can be
created between two files applied by one `migrate()` -- so it answers `0` BY
CONSTRUCTION, having had no opportunity, not by having been checked and
found clean.  Only a database that ran a live server while sitting at `008`
can answer anything else.  Measured both ways in
`tests/test_persistence_null_audit.py`.  Nothing in this repository records
which of the two the owner's database is; that is a question for whoever
runs this, and it is why the module reports the file it counted.

Nobody in this repository knows how wide that window is on the owner's
canonical database, and COO cannot rule on a backfill without the number.
This module is how the number is produced.

WHAT IT IS NOT.
* **It is not a backfill and it writes nothing.**  `COO-DECISION 20260903_1047`
  point 2 forbids the backfill until the number is seen.  Every statement in
  here is a `SELECT`.
* **It does not touch `persistence_vitals.VITAL_COLUMNS`.**  Six places in
  `src/` read that tuple; the two that make adding a name to it a change to
  BEHAVIOUR rather than to a report are `store.py`'s birth guard
  (`set(birth) != set(vitals.VITAL_COLUMNS)`, which refuses an INSERT whose
  keys are not exactly those three) and `persistence_vitals`'s extra-key
  guard on the birth mapping.  The other four -- the resolver's missing-column
  list, the census query, the schema check, and the login resolver's
  every-column-unseeded classification (that module is described and not
  spelled: its own test file scans `src/` for the spelling to prove the login
  has exactly one seam, and a mention in prose is indistinguishable from an
  import to a regex) -- read it rather than write through it, and an earlier
  draft of this paragraph said "two places" as if it had counted them.  It
  had not.  `NULL_AUDIT_COLUMNS` below is a separate constant that only the
  reporting path reads, exactly as that decision ordered.
* **It does not say what SHOULD be done about a nonzero count.**  A row that
  is NULL in `speed_walk` is not thereby broken: `COO-DECISION 20260902_1043`
  chose to leave `speed_walk` unseeded at birth, and the login resolvers are
  built to report a gap rather than guess a zero
  (`COO-DECISION 20260901_1059`).  This answers "how many", never "and
  therefore".
* **"HOLDS NULL" IS NARROWER THAN "HAS NO ADJUDICATED VALUE", and a reader
  of a zero here has to know it.**  Measured: `/speed 0` through this lane's
  own shipped door stores `0.0`; `008` declines to overwrite a stored zero
  (pinned in `tests/test_persistence_speed_walk_seed_008.py`) and `009`'s
  DEFAULT never reaches an existing row, so that row is permanently
  un-adjudicated and permanently invisible to this count.  The same holds for
  a row at `level 0`, which `persistence_vitals` refuses to resolve
  (`level_zero_is_not_an_adjudicated_level`) while every column of it is
  NOT NULL.  This counts NULLs.  It does not count rows the server would
  refuse.

WHY THE COLUMN LIST IS BUILT AND NOT TYPED OUT.  The house rule from
`NOW.md` -- a card that has to retype a list in a second file is forbidden,
derive it from the source instead.  `NULL_AUDIT_COLUMNS` is
`persistence_vitals.VITAL_COLUMNS` plus the column
`persistence_typed_attrs` maps wire field `x=7` to, so a rename of any of
the four moves this list with it and cannot leave a stale string behind.

WHY IT IS NOT DERIVED FROM THE DATABASE'S OWN `DEFAULT`s, which was the
first draft and is wrong in the dangerous direction.  Reading
`PRAGMA table_info(characters)` and auditing whatever carries a DEFAULT
looks stronger -- it cannot drift.  But on a database still at `008` NO
typed column carries a DEFAULT, so that version would audit nothing and
report a clean sheet over exactly the rows this module was written to count.
The list is therefore static, and `tests/test_persistence_null_audit.py`
grades it against the live schema of a database migrated to HEAD, so a fifth
adjudicated column turns that test red instead of being silently missed.
"""
from __future__ import annotations

from . import persistence_typed_attrs as typed_attrs
from . import persistence_vitals as vitals

#: The wire field `speed_walk` serves.  Spelled as the NUMBER and resolved to
#: a column through `persistence_typed_attrs`, rather than spelled as the
#: string `"speed_walk"`: `persistence_vitals`'s own header says a rename of
#: that column is the one rename this schema still expects, and a hand-typed
#: string is what would survive it while meaning nothing.
#:
#: !! IT IS THE SAME NUMBER AS `store.SPEED_WALK_FIELD_X`, and that is a
#: second copy in a second file, which this module's own header calls
#: forbidden.  It is not imported because `store` imports THIS module (from
#: inside the audit method) and the reverse import at module scope would be a
#: cycle.  The house rule is honoured the other way instead:
#: `tests/test_persistence_null_audit.py::
#: TheAuditedListIsDerivedNotTypedTests::test_x7_is_the_same_field_the_store_
#: names` grades the two against each other, so a change to either goes red.
SPEED_WALK_X = 7

#: The four columns somebody has adjudicated a birth value for, in the order
#: `009` writes them.  READ-ONLY, REPORTING ONLY -- see the module header for
#: why this is not `persistence_vitals.VITAL_COLUMNS` with a name appended.
NULL_AUDIT_COLUMNS: tuple[str, ...] = tuple(vitals.VITAL_COLUMNS) + (
    typed_attrs.column_for(SPEED_WALK_X),
)


def audit_sql() -> str:
    """One query answering, per column, how many rows hold NULL.

    BOTH COUNTS, side by side, for the reason
    the vitals census query learned the hard way and wrote down: a
    report that skips soft-deleted rows gives a permanently reassuring wrong
    answer, because `004_character_soft_delete_reuse.sql` keeps those rows on
    disk forever.  `*_null_live` is what a read would see; `*_null_any` is
    what is actually in the file.  A backfill would have to touch both, so a
    decision about one taken from the other would be taken on the wrong
    number.

    NULL IS COUNTED, not "not seeded": these are different questions from the
    census's.  `persistence_vitals.census_sql` counts values PRESENT in the
    three vitals; this counts values ABSENT in four columns, and the fourth
    is the whole reason it exists.  Neither is derivable from the other on a database where rows
    have been deleted.
    """
    parts = ["COUNT(*) AS characters_any",
             "SUM(deleted_at IS NULL) AS characters_live"]
    for column in NULL_AUDIT_COLUMNS:
        parts.append(f"SUM({column} IS NULL) AS {column}_null_any")
        parts.append(
            f"SUM({column} IS NULL AND deleted_at IS NULL) "
            f"AS {column}_null_live"
        )
    return "SELECT " + ",".join(parts) + " FROM characters"


def format_report(audit: dict) -> str:
    """The audit as the lines that go into a letter, one column per line.

    A number quoted into a letter without the database it was counted from is
    worth nothing -- the store's vitals seeding census says the same about
    its own result and for the same reason (the method is described and not
    spelled here on purpose: `tests/test_persistence_vitals.py::
    NothingIsWiredTests` scans `src/` for that spelling to prove nothing has
    wired it, and a mention in prose is indistinguishable from a call to a
    regex) -- so the path is the first line and it is not optional.
    """
    lines = [
        "NULL_AUDIT database=%s" % (audit.get("database"),),
        # `characters_any` is `COUNT(*)` and is a real number even at zero;
        # `characters_live` is a `SUM()` and is NULL over an empty table, so
        # it goes through the same guard as the columns.
        "NULL_AUDIT characters live=%s any=%s" % (
            _count(audit.get("characters_live")),
            audit.get("characters_any")),
    ]
    for column in NULL_AUDIT_COLUMNS:
        lines.append("NULL_AUDIT %s null_live=%s null_any=%s" % (
            column,
            _count(audit.get("%s_null_live" % column)),
            _count(audit.get("%s_null_any" % column)),
        ))
    return "\n".join(lines)


#: What a count that COULD NOT BE TAKEN prints as.  NOT `0`.
#: `SUM()` over zero rows is SQL NULL, so on a database with no characters
#: every per-column number here is NULL rather than a counted zero -- and an
#: earlier draft of the store door coerced that to `0`, which made an empty
#: database print a report line for line identical to a fully seeded one.
#: That is `COO-DECISION 20260901_1059`'s banned guessed zero, arriving at
#: the layer whose output goes into a letter: this lane refuses to send an
#: unknown field as `0` on the wire and must not print one either.
NOT_COUNTED = "not-counted"


def _count(value):
    return NOT_COUNTED if value is None else value
