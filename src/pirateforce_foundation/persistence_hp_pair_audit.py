"""LANE-DB: how many rows on THIS database sit in one of the three broken
HP-pair conditions LANE-GM measured while wiring `/lv`
(`pf_bridge/notes_to_chief/20260906_0436_LANE-GM-TO-LANE-DB-slash-lv-blocked-
by-broken-hp-pair-rows.md`) -- conditions that make the login vitals
resolver's gate refuse to send the row's real numbers and fall back to the
composer's literals (that resolver is described and not spelled here: this
lane's own test for it forbids naming it from a second place under `src/`,
and a mention in prose is indistinguishable from a call to it): `hp_max IS
NULL`,
`hp_current > hp_max`, `hp_max = 0`.  GM already guards its own write (`/lv`
reads the login door back after writing and reverts rather than leave a row
the login and the database would disagree about); these three conditions
predate that command and this module only counts how many rows already hold
one of them.

READ-ONLY, REPORTING ONLY -- the backlog item LANE-DB's reply promised
(`pf_bridge/notes_to_chief/20260906_0536_LANE-DB-REPLY-gm0436-hp-pair-rows-
not-a-blocker-for-0156-logged-as-backlog.md`): no migration, no `UPDATE`, no
new write door.  This answers "how many", never "and therefore" -- the same
restraint `persistence_null_audit` states for its own count, and for the
same reason: nobody has adjudicated what a backfill for a broken HP pair
should write, and this module does not decide that by existing.

WHY THESE THREE AND NOT THE WHOLE LOGIN GATE.  `persistence_vitals.resolve()`
refuses more than this: an unseeded column (`REASON_NOT_SEEDED`) and a stored
`level = 0` (`REASON_LEVEL_ZERO`) also make a login fall back to the
composer's literals.  Those two are the unseeded-at-birth / adjudicated-zero
shape this repository already has evidence and tests for
(`persistence_null_audit`, `persistence_vitals`'s own suite).  This module
counts only the three conditions GM's letter measured as ACTUALLY OCCURRING
on a real run, because that is the number the letter asked for.

WHAT THIS IS NOT.
* Not a backfill.  Every statement below is a `SELECT`.
* Not `persistence_vitals._consistency_gaps`, which walks one character's
  already-read columns at a time from inside the login path.  This is a
  single aggregate query over every row in the table, the shape
  `persistence_null_audit.audit_sql` uses and for the same reason: COO
  cannot rule on a fix without the number, and reading one row at a time
  through the login gate does not produce one.
* Not proof that these are the only three ways a row ends up refused by the
  login gate -- see above.
* Not proof the three counts are disjoint.  A row can satisfy more than one
  condition at once (a stray `hp_current` written above a `hp_max` that is
  itself `0`, for instance), so they are reported side by side rather than
  summed into one number.
"""
from __future__ import annotations

from . import persistence_vitals as vitals

HP_CURRENT_COLUMN = vitals.HP_CURRENT_COLUMN
HP_MAX_COLUMN = vitals.HP_MAX_COLUMN

#: The three conditions GM's letter measured, in the order the letter named
#: them.
HP_MAX_NULL = "hp_max_is_null"
HP_CURRENT_ABOVE_MAX = "hp_current_above_hp_max"
HP_MAX_ZERO = "hp_max_is_zero"

CONDITIONS: tuple[str, ...] = (HP_MAX_NULL, HP_CURRENT_ABOVE_MAX, HP_MAX_ZERO)

#: One SQL predicate per condition, built from the same column names
#: `persistence_vitals` resolves the login gate against -- not retyped as
#: the strings `"hp_current"`/`"hp_max"`, so a rename of either column moves
#: this module with it instead of leaving a stale predicate behind.
#:
#: Every predicate that can see a NULL operand is guarded with an explicit
#: `IS NOT NULL` (pf-adversary, PR #896 follow-up): SQL three-valued logic
#: makes `hp_max = 0` evaluate to NULL, not FALSE, when `hp_max IS NULL`, so
#: `SUM()` over an all-NULL-`hp_max` table returned SQL NULL for the
#: `hp_max_is_zero` condition -- rendered as `not-counted` even though the
#: true count for that condition is a well-defined `0`.
_PREDICATE: dict[str, str] = {
    HP_MAX_NULL: f"{HP_MAX_COLUMN} IS NULL",
    HP_CURRENT_ABOVE_MAX: (
        f"{HP_CURRENT_COLUMN} IS NOT NULL AND {HP_MAX_COLUMN} IS NOT NULL "
        f"AND {HP_CURRENT_COLUMN} > {HP_MAX_COLUMN}"
    ),
    HP_MAX_ZERO: f"{HP_MAX_COLUMN} IS NOT NULL AND {HP_MAX_COLUMN} = 0",
}


def audit_sql() -> str:
    """One query answering, per condition, how many rows match it.

    BOTH COUNTS, side by side, for the reason `persistence_null_audit`
    learned the hard way and wrote down: a report that skips soft-deleted
    rows gives a permanently reassuring wrong answer, because
    `004_character_soft_delete_reuse.sql` keeps those rows on disk forever.
    `*_any` is what is actually in the file; `*_live` is what a read would
    see.
    """
    parts = ["COUNT(*) AS characters_any",
             "SUM(deleted_at IS NULL) AS characters_live"]
    for name in CONDITIONS:
        predicate = _PREDICATE[name]
        parts.append(f"SUM({predicate}) AS {name}_any")
        parts.append(
            f"SUM(({predicate}) AND deleted_at IS NULL) AS {name}_live"
        )
    return "SELECT " + ",".join(parts) + " FROM characters"


#: What a count that COULD NOT BE TAKEN prints as.  NOT `0` -- `SUM()` over
#: zero rows is SQL NULL, so a database with no characters would otherwise
#: print a report line for line identical to a fully clean one.  Same rule
#: `persistence_null_audit.NOT_COUNTED` states, kept as a separate constant
#: here rather than imported: the two modules count different things and a
#: shared import would suggest one depends on the other's shape.
NOT_COUNTED = "not-counted"


def _count(value):
    return NOT_COUNTED if value is None else value


def format_report(audit: dict) -> str:
    """The audit as the lines that go into a letter, one condition per line.

    A number quoted into a letter without the database it was counted from
    is worth nothing -- `persistence_null_audit.format_report` says the same
    about its own result and for the same reason -- so the path is the first
    line and it is not optional.
    """
    lines = [
        "HP_PAIR_AUDIT database=%s" % (audit.get("database"),),
        "HP_PAIR_AUDIT characters live=%s any=%s" % (
            _count(audit.get("characters_live")),
            _count(audit.get("characters_any"))),
    ]
    for name in CONDITIONS:
        lines.append("HP_PAIR_AUDIT %s live=%s any=%s" % (
            name,
            _count(audit.get("%s_live" % name)),
            _count(audit.get("%s_any" % name)),
        ))
    return "\n".join(lines)
