"""LANE-CS: a typed reader for ``CONSTDATA_TH__LEVEL_SP.tsv``, the client's
one level-indexed ``SP`` curve -- and an explicit record of what the shipped
bytes do and do NOT say that curve means.

WHY THIS FILE EXISTS.  Three lanes argued about one number this week and none
of them had opened the table.  LANE-CS claimed (letter ``20260908_0458``) that
``LEVEL_SP`` "must be an experience curve, because it is the only table
indexed by level"; LANE-DB answered (letter ``20260908_0633``) that the
experience curve is ``STANDARD_STATUS.n_EXP_CURRENTLV`` and is already read on
main, so that argument is dead, and closed with the sentence this module is
the answer to: "what LEVEL_SP is, NOBODY HAS MEASURED".  This module is the
measurement, committed as code rather than as prose, so the next round reads
a table instead of re-running the argument.

WHAT THE BYTES SAY (measured on the committed copy, not asserted).
  * 120 rows.  ``n_ID`` is 1..120 with no gap, and is the level.
  * ``n_SP`` is strictly increasing over all 120 rows.
  * ``n_SP`` at level 1 is 2.  ``n_SP`` at level 120 is 13,645,740.
  * ``n_SP`` equals ``STANDARD_STATUS.n_EXP_CURRENTLV`` at ZERO of 120 levels,
    equals ``n_PVP_SP`` at zero, equals ``n_PVP_EXP`` at zero, and equals the
    per-level experience delta at zero.  It is a curve of its own.
  * It TRACKS the experience curve without being a multiple of it.  The ratio
    ``n_SP / n_EXP_CURRENTLV`` is UNDEFINED at level 1 (``n_EXP_CURRENTLV``
    is 0 there while ``n_SP`` is 2 -- on its own enough to refute any
    multiplier), and over the 119 levels where it is defined it spans 0.0506
    (level 2) to 0.1786 (level 61): between 0.05942 and 0.05952 for levels
    13..40, and between 0.0626 (level 41) and 0.1786 for levels 41..120.  So no
    single multiplier reproduces this curve from the experience curve.  Note
    what that does NOT say: individual rows are of course reproducible by
    SOME multiplier (1/17 hits levels 4, 7 and 10 exactly).  The refutation
    is the spread, not a per-row miss.  Both bounds are recomputed from the
    two committed tables by ``tests/test_skill_point_curve.py``; they are not
    recomputable from inside this module, because naming the reader of the
    other table here would enrol this file in that reader's sole-caller pin
    (which is exactly what this round did once already).
  * ``STANDARD_STATUS`` runs to level 255; this table stops at 120.  The two
    are not two views of one object.

WHAT THE BYTES DO NOT SAY, AND WHY THIS MODULE REFUSES TO GUESS.  A column
named ``n_SP`` on a table named ``LEVEL_SP`` admits at least two readings that
the shipped data cannot separate:

    (a) a HOLDING -- the SP a character has accumulated on reaching that
        level, in which case a fresh level-1 character holds ``2``; or
    (b) a THRESHOLD -- the SP needed to leave that level, in which case a
        fresh level-1 character holds ``0`` and owes ``2``.

Both readings fit every byte in the file, and no code in either repo READS
the table before this module.  The one place that names it is a COMMENT:
``migrations/016_character_experience_skill_points_backfill.sql`` quotes four
of its rows while arguing about ``skill_points``.  A comment is not a
consumer, and that migration reaches its own conclusion without ever opening
the file -- which is exactly how three lanes ended up arguing from four rows.

    A MEASUREMENT THIS MODULE MADE AND THEN THREW AWAY, recorded so nobody
    re-runs it thinking it means something.  ``LEVEL_SP`` appears in zero of
    the 616 committed lua scripts.  That number is real and it is EVIDENCE OF
    NOTHING: run the same grep for all 188 client table names and only two
    appear, both false positives on ordinary words, and ``STANDARD_STATUS`` --
    a table the client unquestionably consumes -- scores zero exactly like
    this one.  Lua scripts in this corpus do not name data tables, so the
    grep cannot separate "consumed" from "not consumed".  An earlier draft of
    this docstring offered it as support for "no consumer decides it"
    (pf-adversary D5); it is kept here as a retired measurement, not as
    support for anything.

WHAT THE COMMITTED CODE ALREADY ASSUMES, WHICH CUTS AGAINST READING (a).
This lane's own modules on ``main`` already treat skill points as a small
SPENDABLE BALANCE: ``skill_learn_validator.can_afford_to_learn`` /
``skill_points_after_learning`` subtract ``skill_catalog.
skill_point_cost_to_learn``, which reads the client's ``f_SP_LEVE1``.
Measured on the curriculum copy this package vendors: a first rank costs
0.2 to 8.0 points, a rank-up 0.0 to 1.0, and maxing every one of the 38 rows
with a usable ``n_LEVELS`` totals 178.6.  Under reading (a) a level-120
character would hold 13,645,740 points to spend on a tree that costs three
figures -- five orders of magnitude apart.  That does not prove reading (b);
a currency can be inflated, and 99 of the 137 rows carry an unusable
``n_LEVELS`` so the tree total is a floor, not a ceiling.  But it means
reading (a) is the LESS comfortable of the two against code this repo has
already shipped, and any round quoting the "2" below has to carry this
paragraph with it.  LANE-DB's letter ``20260908_0633`` raised this in its own
fairness note and an earlier draft of this module dropped it (pf-adversary
D2).  So this module
publishes the number and the two readings, and NAMES NOTHING after a reading.
Be precise about how weak that guard is: ``sp_at_level(1)`` returns 2 to
anybody who asks, and it must -- that IS the table.  What the guard buys is
only that no NAME in this module says the 2 is a birth value, so a caller who
wants to treat it as one has to write that sentence at its own call site
where a reviewer can see it.  It is a naming convention with a test behind
it, not a mechanism, and pf-adversary D7 is right that a caller can spend the
number anyway.

    THE DECISION THIS FEEDS, STATED SO IT CANNOT BE OVERSTATED.  The open
    item is PANYA's to tick, not COO's to decide: ``NOW.md``'s section is
    ``rows waiting for Panya to tick``, its item 1 asks whether a character
    born after migration ``016`` holds ``experience``/``skill_points`` of 0,
    it pairs that with migration ``017``'s DEFAULT rather than ``016``, and
    COO has ALREADY recommended yes.  An earlier draft of this paragraph said
    COO was being asked and named the wrong migration (pf-adversary D10).
    What this module adds is exactly one thing: under reading (a) the shipped
    answer is 2, not 0, so "0" is a CHOICE and not a value read off the
    client's own table -- carried together with the paragraph above, which
    says reading (a) is the weaker of the two.  It is NOT a recommendation to
    seed 2, and this lane is not the owner of that column -- ``skill_points``
    is LANE-DB's (``prompts/LANE-CS.md``: rows in the DB are not this lane's
    write zone).

    THIS LANE'S OWN EARLIER CLAIM IS WITHDRAWN HERE, in the file rather than
    only in a letter.  Letter ``20260908_0458`` argued "thirteen million
    cannot be skill points".  LANE-DB refuted it from a table already in this
    repo (``lua_api/quest_criteria_curve.tsv`` pays a level-255 quest
    14,252,800 SkillPoint), and the refutation stands: 13,645,740 is BELOW a
    reward this project already ships.  The magnitude argument is dead and
    must not be revived by a later round quoting the old letter.

WHAT THE HASH PIN DOES AND DOES NOT CATCH (pf-adversary D3, stated because
the earlier wording oversold it).  Both sides of the check live in this
module, so it catches an edit to the ``.tsv`` alone and an edit to
``SOURCE_SHA256`` alone -- but NOT a coordinated edit that changes a row and
recomputes the digest.  The value pins in ``tests/test_skill_point_curve.py``
are what raise the cost of that: they name rows across the span, so a
coordinated edit has to move those too.  114 of the 120 rows are still
covered by the digest alone.  A second, independently owned signature over
this table (the shape ``docs/WORLD_SOURCE_TABLE_COUNTERSIGN.json`` exists
for) is what would actually close it, and this round did not open that file.
Related: ``_load_rows`` raising at import means a drifted byte fails
COLLECTION for every test module that imports this one, so the failure names
the import rather than the row.

WHAT THIS MODULE IS NOT.  It is not a progression system, it grants nothing,
it touches no database, and it has no caller in ``src/`` on the round that
added it.  It is the data door that this lane's queue item 5 (learn-skill /
skill-point system) has to have before any of that can be written against
something other than a guess.
"""

from __future__ import annotations

from dataclasses import dataclass
import csv
import hashlib
from pathlib import Path


_DATA_PATH = Path(__file__).parent / "data" / "level_sp.tsv"

# sha256 of the byte-for-byte copy of pf_bridge/gamedata/tables/
# CONSTDATA_TH__LEVEL_SP.tsv committed next to this module, checked at import
# time so a hand-edit fails loudly instead of drifting from the client's
# table.  Deliberately the same shape as the other vendored-table readers in
# this package, which each pin their own copy's digest the same way.
#
# THE MODULE NAMES ARE NOT SPELLED HERE ON PURPOSE.  The reader for the
# STANDARD_STATUS table carries a sole-production-caller pin that scans every
# file under src/, tools/, migrations/ and scenarios/ for its own name as a
# SUBSTRING, so a comment naming it -- even one saying only "we copied its
# pattern" -- registers this file as a caller and turns that pin red.  The
# first draft of this comment did exactly that and the full suite caught it
# (2 red).  This lane has now been bitten by the mentions-are-uses shape
# three rounds running; the note stays so the fourth time is somebody else.
SOURCE_SHA256 = (
    "0cf63d83e2901d729605d9d65204ee81d7998f75668e4a56e3a3dc20201c2293"
)

#: The two readings of ``n_SP`` the shipped bytes cannot separate.  Exported
#: as data so a caller has to name which one it is assuming at its own call
#: site, instead of quietly inheriting one from this module.
READING_HOLDING = "sp_already_held_on_reaching_this_level"
READING_THRESHOLD = "sp_still_owed_to_leave_this_level"
UNDECIDED_READINGS = (READING_HOLDING, READING_THRESHOLD)

TABLE_FIRST_LEVEL = 1
TABLE_LAST_LEVEL = 120

REFUSE_LEVEL_NOT_AN_INT = "level_is_not_an_int"
REFUSE_LEVEL_OFF_TABLE = "level_is_outside_the_committed_table"
REFUSE_TABLE_DRIFTED = "committed_copy_no_longer_matches_source_sha256"
REFUSE_TABLE_MALFORMED = "committed_copy_is_not_the_two_column_level_table"


class SkillPointCurveError(KeyError):
    """The committed table could not answer: wrong type, a level outside
    1..120, or a committed copy that no longer hashes to ``SOURCE_SHA256``.
    Never a guessed, interpolated or extrapolated row."""


@dataclass(frozen=True)
class SkillPointRow:
    """One row of ``CONSTDATA_TH__LEVEL_SP.tsv``, typed, unmodified.

    ``sp`` is named for the column (``n_SP``) and not for either reading,
    because naming it ``points_held`` would decide reading (a) in the type
    system, which is precisely what this module refuses to do.
    """

    level: int
    sp: int


def _load_rows() -> dict[int, SkillPointRow]:
    """Read, hash-check and parse the committed table.

    A plain function called once at import rather than a lazy cache: a table
    that fails its hash must fail the import of anything that reads it, not
    the first lookup at some later, quieter moment.
    """
    raw = _DATA_PATH.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SOURCE_SHA256:
        raise SkillPointCurveError(
            REFUSE_TABLE_DRIFTED,
            "committed copy of the level SP table hashes to %s, not the "
            "pinned %s" % (digest, SOURCE_SHA256),
        )
    reader = csv.DictReader(
        raw.decode("ascii").splitlines(), delimiter="\t"
    )
    if reader.fieldnames != ["n_ID", "n_SP"]:
        raise SkillPointCurveError(
            REFUSE_TABLE_MALFORMED,
            "expected columns ['n_ID', 'n_SP'], found %r"
            % (reader.fieldnames,),
        )
    rows: dict[int, SkillPointRow] = {}
    for record in reader:
        level = int(record["n_ID"])
        rows[level] = SkillPointRow(level=level, sp=int(record["n_SP"]))
    expected = list(range(TABLE_FIRST_LEVEL, TABLE_LAST_LEVEL + 1))
    if sorted(rows) != expected:
        raise SkillPointCurveError(
            REFUSE_TABLE_MALFORMED,
            "expected levels %d..%d with no gap, found %d rows"
            % (TABLE_FIRST_LEVEL, TABLE_LAST_LEVEL, len(rows)),
        )
    return rows


_ROWS = _load_rows()


def _require_level(value: object) -> int:
    if type(value) is not int or type(value) is bool:
        raise SkillPointCurveError(
            REFUSE_LEVEL_NOT_AN_INT,
            "level must be a plain int, got %r" % (value,),
        )
    if not TABLE_FIRST_LEVEL <= value <= TABLE_LAST_LEVEL:
        raise SkillPointCurveError(
            REFUSE_LEVEL_OFF_TABLE,
            "level %d is outside the committed table, %d..%d -- this table "
            "stops at 120 while STANDARD_STATUS runs to 255, so a level in "
            "121..255 is a real level with no row here, not a bad argument"
            % (value, TABLE_FIRST_LEVEL, TABLE_LAST_LEVEL),
        )
    return value


def row_for_level(level: int) -> SkillPointRow:
    """The committed row for ``level``, or a named refusal."""
    return _ROWS[_require_level(level)]


def sp_at_level(level: int) -> int:
    """The ``n_SP`` the client's table carries at ``level``.

    Named for the column rather than for a meaning.  A caller that wants "how
    many points does this character have" must first decide which of
    :data:`UNDECIDED_READINGS` it is assuming, and say so at its own call
    site -- this function will not decide it for them.
    """
    return row_for_level(level).sp


def levels() -> tuple[int, ...]:
    """Every level the table carries, ascending."""
    return tuple(range(TABLE_FIRST_LEVEL, TABLE_LAST_LEVEL + 1))


def is_strictly_increasing() -> bool:
    """Whether ``n_SP`` rises at every step of the committed table.

    Exposed as a function over the loaded rows rather than asserted in the
    docstring, so the claim in this module's header is something a caller can
    re-run rather than something a reader has to trust.
    """
    values = [_ROWS[level].sp for level in levels()]
    return all(values[i] < values[i + 1] for i in range(len(values) - 1))


def headless_summary() -> str:
    """One ASCII line for a cp874 console.  No characters above 0x7F."""
    return (
        "SKILL_POINT_CURVE rows=%d levels=%d..%d sp_first=%d sp_last=%d "
        "strictly_increasing=%s readings_undecided=%d source_sha256=%s"
        % (
            len(_ROWS),
            TABLE_FIRST_LEVEL,
            TABLE_LAST_LEVEL,
            _ROWS[TABLE_FIRST_LEVEL].sp,
            _ROWS[TABLE_LAST_LEVEL].sp,
            "yes" if is_strictly_increasing() else "no",
            len(UNDECIDED_READINGS),
            SOURCE_SHA256[:16],
        )
    )


if __name__ == "__main__":  # pragma: no cover - console entry point
    print(headless_summary())
