"""LANE-DB: how many rows on THIS database hold NULL in `skill_points` and
`unspent_points`, reported as TWO SEPARATE GROUPS rather than one list --
the backlog item this lane's own round `64da3x` named as ready to start
(`pf_bridge/rounds/DB_20260905_1739_64da3x_skill_points_store_doors.md`,
"## งานสำรอง" item 2): "ขยาย typed_column_null_audit ให้รายงาน
skill_points/unspent_points แยกกลุ่ม (คอลัมน์ที่มี CORE-REQUEST เขียนใช้แล้ว
vs ยังไม่มีใครแตะ)".

WHY A NEW MODULE AND NOT A ROW ADDED TO `persistence_null_audit.NULL_AUDIT_
COLUMNS`.  That list is explicitly scoped, in its own header, to columns
SOMEBODY HAS ADJUDICATED A BIRTH VALUE FOR and that carry a schema `DEFAULT`
since `migrations/009_character_birth_defaults.sql` (`level`, `hp_current`,
`hp_max`, `speed_walk`).  Neither `skill_points` nor `unspent_points` has an
adjudicated birth default or a `DEFAULT` clause -- `009`'s own `CREATE TABLE
characters_rebuild` leaves both bare (checked at
`migrations/009_character_birth_defaults.sql`, the `skill_points INTEGER`
and `unspent_points INTEGER` lines carry no `DEFAULT`).  Adding them to that
list would misreport them as adjudicated when they are not: a row holding
NULL in `skill_points` is not a gap in a birth default that should have run,
it is simply a column nobody has written yet.  `persistence_hp_pair_audit`
set the precedent this module follows instead -- a new, small, single-
purpose module per new question, not a growing list bent to fit a header
that no longer describes what it counts.

WHY THESE TWO COLUMNS AND WHY GROUPED THE WAY THEY ARE.  Both are `x=16`/
`x=17` in `persistence_attr_compose.SERVER_OWNED_FIELDS`, both got their
column in the same migration (`006_character_typed_attribute_columns.sql`),
and neither has a production caller that WRITES a value at birth -- but as
of round `64da3x` they no longer have the same amount of code around them:

* `skill_points` (`WIRED_COLUMN`) has real store doors, on `main`, that read
  and spend it (`store.get_skill_points`, `store.spend_skill_points`,
  `pf_bridge/notes_to_chief/20260905_1510_LANE-CS-CORE-REQUEST-store-py-
  skill-points-hookup-to-lane-db-rerouted-from-chief.md`), and CS-side
  consumers built against it (`skill_learn_validator.py`,
  `skill_learn_wiring.py`, `skill_grant_wiring.py`,
  `stats_progression_hypothesis.py` -- `grep -rl skill_points src/` at HEAD
  lists all four beside `store.py` and this compose gate).  A row holding
  NULL there is invisible to code that already exists and could run against
  it the moment a caller supplies a number.
* `unspent_points` (`UNWIRED_COLUMN`) has neither: the same `grep` for
  `unspent_points` across `src/` returns only `gm/attr_wire.py` (the wire
  field table) and `persistence_attr_compose.py` (the compose gate's own
  partition) -- no store door, no consumer, zero round has touched it since
  `006` built the column.  A row holding NULL there is a column nobody has
  had a reason to look at yet, a different kind of gap from the first one.

Folding the two into one number the way `persistence_null_audit` folds its
four would erase exactly the distinction the backlog item asked for.

WHAT THIS IS NOT.
* Not a backfill and not a birth-default proposal.  Every statement below is
  a `SELECT`, same discipline `persistence_null_audit`/
  `persistence_hp_pair_audit` state for their own counts.
* Not proof that either column SHOULD default at birth -- that is
  `COO-DECISION 20260902_1043`'s kind of ruling (which left `speed_walk`
  unseeded at birth on purpose) and this module answers "how many", never
  "and therefore", for the same reason those two modules do.
* Not a claim that `WIRED`/`UNWIRED` is permanent.  The moment a round wires
  a caller for `unspent_points`, the correct fix is moving its name from one
  constant to the other in the same diff that wires it -- not adding a third
  group -- and `tests/test_persistence_skill_points_null_audit.py`'s own
  `TheGroupingMatchesLiveCodeTests` greps `src/` at test time so a rename
  that is not also made here turns red instead of drifting silently.
"""
from __future__ import annotations

from . import persistence_attr_compose as compose
from . import persistence_typed_attrs as typed_attrs

#: `x=16`/`x=17` in `persistence_attr_compose.SERVER_OWNED_FIELDS` -- spelled
#: as the field index and resolved through `persistence_typed_attrs.
#: column_for`, not retyped as the strings `"skill_points"`/
#: `"unspent_points"`, so a rename of either column (the way `speed_walk`'s
#: own header warns is still open for that column) moves this module with it
#: instead of leaving a stale predicate behind.
SKILL_POINTS_X = 16
UNSPENT_POINTS_X = 17

#: Has a real `store.py` door and at least one production-code consumer
#: beyond the wire-field table and the compose gate itself, as of this
#: round -- see the module header for the `grep` this claim is measured
#: against.
WIRED_COLUMN = typed_attrs.column_for(SKILL_POINTS_X)

#: Has neither -- schema only, since `006`, with no caller anywhere.
UNWIRED_COLUMN = typed_attrs.column_for(UNSPENT_POINTS_X)

WIRED_COLUMNS: tuple[str, ...] = (WIRED_COLUMN,)
UNWIRED_COLUMNS: tuple[str, ...] = (UNWIRED_COLUMN,)

#: Both groups, in report order: wired first (the column code can already
#: act on today), unwired second.
ALL_COLUMNS: tuple[str, ...] = WIRED_COLUMNS + UNWIRED_COLUMNS


def _verify_grouping() -> None:
    """Both columns are real, server-owned, distinct, and belong to exactly
    one group -- checked at import time so a future edit that types the same
    column into both constants, or a column the compose gate does not know,
    fails loud here rather than producing a report with a duplicated or
    silently wrong line."""
    if WIRED_COLUMN == UNWIRED_COLUMN:
        raise ValueError(
            "WIRED_COLUMN and UNWIRED_COLUMN name the same column: "
            f"{WIRED_COLUMN!r}"
        )
    for x, column in ((SKILL_POINTS_X, WIRED_COLUMN),
                      (UNSPENT_POINTS_X, UNWIRED_COLUMN)):
        if x not in compose.SERVER_OWNED_FIELDS:
            raise ValueError(
                f"x={x} ({column!r}) is not in "
                "persistence_attr_compose.SERVER_OWNED_FIELDS"
            )
        if compose.SERVER_OWNED_FIELDS[x].column != column:
            raise ValueError(
                f"x={x}: persistence_typed_attrs names column {column!r}, "
                f"persistence_attr_compose names "
                f"{compose.SERVER_OWNED_FIELDS[x].column!r}"
            )


_verify_grouping()


def audit_sql() -> str:
    """One query answering, per column in `ALL_COLUMNS`, how many rows hold
    NULL -- both counts side by side, live and on disk, for the reason
    `persistence_null_audit`/`persistence_hp_pair_audit` both learned and
    wrote down: a report that skips soft-deleted rows gives a permanently
    reassuring wrong answer, because
    `004_character_soft_delete_reuse.sql` keeps those rows on disk forever.
    """
    parts = ["COUNT(*) AS characters_any",
             "SUM(deleted_at IS NULL) AS characters_live"]
    for column in ALL_COLUMNS:
        parts.append(f"SUM({column} IS NULL) AS {column}_null_any")
        parts.append(
            f"SUM({column} IS NULL AND deleted_at IS NULL) "
            f"AS {column}_null_live"
        )
    return "SELECT " + ",".join(parts) + " FROM characters"


#: What a count that COULD NOT BE TAKEN prints as.  NOT `0` -- `SUM()` over
#: zero rows is SQL NULL, so a database with no characters would otherwise
#: print a report line identical to a fully seeded one.  Same rule
#: `persistence_null_audit.NOT_COUNTED`/`persistence_hp_pair_audit.
#: NOT_COUNTED` state, kept as a separate constant here rather than
#: imported, for the same reason those two keep separate constants from each
#: other: the three modules count different things.
NOT_COUNTED = "not-counted"


def _count(value):
    return NOT_COUNTED if value is None else value


def format_report(audit: dict) -> str:
    """The audit as the lines that go into a letter, one column per line,
    grouped and labelled `wired`/`unwired` so a reader does not have to
    cross-reference this module's source to know which is which.

    The path is the first line and is not optional -- the same rule
    `persistence_null_audit.format_report`/`persistence_hp_pair_audit.
    format_report` both state, for the same reason: a number quoted into a
    letter without the database it was counted from is worth nothing.
    """
    lines = [
        "SKILL_POINTS_AUDIT database=%s" % (audit.get("database"),),
        "SKILL_POINTS_AUDIT characters live=%s any=%s" % (
            _count(audit.get("characters_live")),
            _count(audit.get("characters_any"))),
    ]
    for group, columns in (("wired", WIRED_COLUMNS),
                            ("unwired", UNWIRED_COLUMNS)):
        for column in columns:
            lines.append(
                "SKILL_POINTS_AUDIT %s %s null_live=%s null_any=%s" % (
                    group, column,
                    _count(audit.get("%s_null_live" % column)),
                    _count(audit.get("%s_null_any" % column)),
                ))
    return "\n".join(lines)
