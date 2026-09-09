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
    seed 2.  WHAT CHANGED ON 2026-09-08 AT 14:41: the COLUMN is still
    LANE-DB's (``prompts/LANE-CS.md``: rows in the DB are not this lane's
    write zone) but the NUMBER is now this lane's, by
    ``COO-DECISION 20260908_1441`` point 3 on LANE-DB's own proposal --
    see ``BIRTH_SKILL_POINTS`` below, which is where that order landed.

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

THE ONE NUMBER THIS MODULE DOES NAME, AND WHY IT IS NOT A THIRD READING.
``BIRTH_SKILL_POINTS`` is 0, and it is an ASSUMPTION, not a measurement.
``COO-DECISION 20260908_1441`` point 3 ordered it here for a reason that is
worth keeping in front of the number: ``migrations/017`` gives
``characters.skill_points`` a ``DEFAULT 0``, and ``tests/pf_birth_state.py``
pins the birth row -- but that pin OMITS ``skill_points`` ON PURPOSE, and
says so in its own words: "a column no module owns a number for is absent
here, and absence means this file has nothing to say about the value".  It
reads ``experience`` through the module that owns THAT number and leaves this
one ungraded, because there was nobody to ask.  This constant is the answer
to that sentence and nothing more: it gives the pin somebody to ask, the way
the vitals module is who that pin asks about the three vitals.

    THE VITALS DOOR IS NOT SPELLED HERE, AND THAT IS THE FOURTH TIME.  The
    function that answers "what are the three vitals at birth" carries a
    sole-call-site pin that scans every file under ``src/`` for its own name
    as a SUBSTRING, so writing it in this sentence -- as an ANALOGY, calling
    nothing -- turned that pin red on the full suite of this very round.  The
    comment over ``SOURCE_SHA256`` predicted this and said the fourth time
    would be somebody else; it was not.  The rule for this file is now
    simple: describe another lane's door, never name it.

  * It is NOT read off a shipped table.  Measured this round rather than
    asserted: of the 188 committed client tables, the ones that could
    plausibly carry a birth balance carry no such column -- all four
    ``CONSTDATA_TH__CHARCREATE_*`` tables were dumped header-first (CLASS 5
    rows / 38 columns, PACKAGE 30/14, LOOK 218/12, SKIN 20/10) and none has a
    skill-point column of any spelling, and a header scan across every
    ``gamedata/tables/*.tsv`` for ``SP``/``SKILL_POINT`` returns only
    per-level, per-mob, per-quest, guild and PVP columns -- ``n_SP`` (this
    table and ``STANDARD_MOB``), ``n_QUEST_SP``, ``n_PVP_SP``, ``f_SP``,
    ``f_REWARD_SP``, ``f_RATIO_SP`` and the ten ``GUILD_MEMBER`` rows.  None
    of them is "what a character is born holding".  So the label is
    ``ASSUMPTION`` and it says so in the constant, not only here.

  * ONE THING DOES SUPPORT IT, AND IT IS AN ARGUMENT, NOT A DECLARATION --
    which is why the label stays ``ASSUMPTION``.  The client's own scripting
    surface has no verb that SETS this balance: ``gamedata/PF_LUA_API_SPEC
    .md`` lists ``AddSkillPoint``, ``Quest.AddCriteriaSkillPoint`` and
    ``AddLvCriteriaSkillPoint``, all of them ADD, and ``SetSkillPoint``
    appears nowhere under ``gamedata/`` at all (grepped this round; the two
    ``AddSkillPoint`` call sites are ``gamedata/lua/t_getm_rat_exp&sp.lua``
    and ``gamedata/lua/t_inskyev_getm_rat_exp&sp.lua``).  A quantity that is
    only ever added to starts SOMEWHERE, and 0 is the natural somewhere --
    which is exactly the argument ``migrations/017`` uses to call the 0 on
    ``experience`` MEASURED.  It is weaker here: there the argument rides on
    a shipped table that carries ``n_EXP_CURRENTLV = 0`` at level 1, and no
    table carries the equivalent row for this column.  An absent setter is
    consistent with 0; it does not state it.

  * It is NOT derived from either reading of this table, and the coincidence
    has to be stated or somebody will mistake it for support: under reading
    (b) a level-1 character holds 0, which is the same 0.  That is a
    COINCIDENCE AND NOT EVIDENCE.  The 0 here comes from
    ``PANYA-DECISION 20260908_1218`` point 3 -- the owner ordered the column
    default by name -- and it would still be 0 if this table said something
    else entirely, because nothing in this file was consulted to pick it.
    ``migrations/017``'s own header says the same thing in the other
    direction ("the 0 on THIS column is hers, not a measurement").

  * The guard is that the label and the value cannot drift apart.
    :func:`birth_skill_points` refuses a value that is labelled
    ``ASSUMPTION`` and is not the number the owner ordered, and refuses a
    value labelled ``MEASURED`` that names no source -- so the day an RE
    answers this, the round that changes the number is FORCED to change the
    label and name the table in the same edit.  What the guard does not do,
    said plainly: it cannot stop a caller reading ``BIRTH_SKILL_POINTS``
    directly and bypassing the check, exactly as ``sp_at_level`` can be
    spent by a caller who ignores the two readings.  It raises the cost of
    the wrong edit; it is not a mechanism.

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

#: The two provenance labels a number in this module may carry.  ``MEASURED``
#: means a committed, shipped table says it; ``ASSUMPTION`` means somebody
#: decided it and no shipped byte does.  Kept as data rather than as prose in
#: a comment so :func:`birth_skill_points` can refuse a label it does not
#: recognise instead of trusting a free-text string.
PROVENANCE_MEASURED = "MEASURED"
PROVENANCE_ASSUMPTION = "ASSUMPTION"
PROVENANCE_LABELS = (PROVENANCE_MEASURED, PROVENANCE_ASSUMPTION)

#: The number the owner ordered for ``characters.skill_points`` at birth.
#: Separate from ``BIRTH_SKILL_POINTS`` on purpose: this one records WHAT WAS
#: ORDERED and only the owner moves it, while the one below records what this
#: module currently publishes.  A round that wants a different number without
#: an RE behind it has to edit this line, where the decision reference is, and
#: not just the export.
#:
#: READ THIS FIRST -- pf-adversary D5, round `30piru`, PAID in round `ixbs2f` and worth
#: reading before trusting the gate below.  Its question was exact: "what in
#: this repo goes red if a round changes BOTH integers to 5 in one commit and
#: fixes up the two test literals?"  The honest answer at the time was
#: NOTHING -- comparing two globals in one file proves ``X == X``, and a
#: mutant that aliased one to the other left 39 tests green.  The number now
#: has an anchor OUTSIDE this module: ``_BIRTH_SKILL_POINTS_SCHEMA_ANCHOR``
#: below names the committed migration that materialises the same order as a
#: column default, and :func:`schema_birth_skill_points` parses it out.  Both
#: integers moved to 5 now needs the migration moved with them -- and moving
#: a migration that has already run on the owner's database is a thing this
#: project does not do quietly.
OWNER_ORDERED_BIRTH_SKILL_POINTS = 0

#: The committed file that carries the same order as SCHEMA, outside this
#: module and outside this lane's write zone.  ``migrations/017`` rebuilt
#: ``characters`` with ``skill_points INTEGER DEFAULT 0``; that default is
#: what every character born on a migrated database actually gets, whatever
#: this module says.
_BIRTH_SKILL_POINTS_SCHEMA_ANCHOR = (
    "migrations/017_character_experience_skill_points_birth_defaults.sql"
)

#: The column the anchor is read out of.  Spelled once so the parser and the
#: refusal message cannot drift apart.
_BIRTH_SKILL_POINTS_SCHEMA_COLUMN = "skill_points"

#: The skill points a character is born holding.  See the module header
#: section "THE ONE NUMBER THIS MODULE DOES NAME".
BIRTH_SKILL_POINTS = 0

#: ASSUMPTION, not MEASURED: no committed client table declares a birth
#: skill-point balance (header scan of every ``gamedata/tables/*.tsv``, and
#: all four ``CHARCREATE`` tables dumped column by column -- see the module
#: header).  The value is the owner's order, ``PANYA-DECISION 20260908_1218``
#: point 3, the same order ``migrations/017`` carries as ``DEFAULT 0``.
#: RE-316: the client's own CharCreate request carries no ``ActorAttr`` at
#: all, so whatever the original server gave a character at birth is not
#: measurable from this client -- closed as a bounded negative
#: (``COO-DECISION 20260908_2141``, "re316-is-a-bounded-negative-the-
#: number-stays-yours"), not evidence that zero is the measured answer.
BIRTH_SKILL_POINTS_PROVENANCE = PROVENANCE_ASSUMPTION

#: The shipped table a ``MEASURED`` number was read off.  Empty exactly while
#: the label is ``ASSUMPTION``, and :func:`birth_skill_points` grades that
#: pairing in both directions, so "MEASURED" can never be claimed without a
#: named source and a source can never be named for a number nobody measured.
BIRTH_SKILL_POINTS_SOURCE = ""

TABLE_FIRST_LEVEL = 1
TABLE_LAST_LEVEL = 120

REFUSE_LEVEL_NOT_AN_INT = "level_is_not_an_int"
REFUSE_LEVEL_OFF_TABLE = "level_is_outside_the_committed_table"
REFUSE_TABLE_DRIFTED = "committed_copy_no_longer_matches_source_sha256"
REFUSE_TABLE_MALFORMED = "committed_copy_is_not_the_two_column_level_table"
REFUSE_BIRTH_PROVENANCE_UNKNOWN = "birth_provenance_is_not_a_known_label"
REFUSE_BIRTH_ASSUMPTION_NOT_AS_ORDERED = (
    "birth_value_is_an_assumption_but_not_the_number_the_owner_ordered"
)
REFUSE_BIRTH_MEASURED_WITHOUT_SOURCE = (
    "birth_value_claims_measured_but_names_no_shipped_table"
)
REFUSE_BIRTH_ASSUMPTION_WITH_SOURCE = (
    "birth_value_names_a_shipped_table_but_is_labelled_an_assumption"
)
#: pf-adversary D5, paid in round `ixbs2f`: the owner-ordered number no
#: longer stands alone in this file.  Raised when the committed migration
#: that materialises the same order as a column default says something else.
REFUSE_BIRTH_ORDER_NOT_IN_THE_SCHEMA = (
    "owner_ordered_birth_value_disagrees_with_the_committed_migration"
)
#: Raised when the anchor file cannot be read or does not carry the column
#: default at all.  Separate from the disagreement above on purpose: "the
#: schema says 5" and "there is no schema to ask" are different bug reports
#: and a single reason would have them arrive as the same one.
REFUSE_BIRTH_SCHEMA_ANCHOR_UNREADABLE = (
    "the_committed_migration_named_as_the_anchor_could_not_be_read"
)


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


def schema_birth_skill_points() -> int:
    """The ``skill_points`` column default, READ OUT of the committed migration.

    pf-adversary D5 (round `30piru`) asked one question and it is the only
    reason this function exists: what in this repository goes red if a round
    changes both ``OWNER_ORDERED_BIRTH_SKILL_POINTS`` and
    ``BIRTH_SKILL_POINTS`` to 5 in a single commit and fixes up the two test
    literals?  The answer was NOTHING -- the gate compared two globals in one
    file, which proves ``X == X``, and a mutant aliasing one to the other left
    the whole file green.  This is the anchor that was missing: a number in
    another file, in another lane's write zone, that a round moving the
    constant would also have to move.

    WHAT IT PARSES.  ``_BIRTH_SKILL_POINTS_SCHEMA_ANCHOR``'s
    ``CREATE TABLE ... skill_points INTEGER DEFAULT <n>``.  Not the whole SQL
    -- the column line, found by name, and the integer after its ``DEFAULT``.

    WHY THE FILE AND NOT A LIVE DATABASE.  A database is a thing on the
    machine running the suite, and a machine that happens to have a database
    with the wrong default would turn this into a fact about that machine
    (this lane already lost eight tests to exactly that shape once, in the GM
    login-scene config).  The migration file is committed, is the same on
    every checkout, and IS what a fresh database gets built from.

    WHAT IT IS NOT.  It is not a claim that 0 is the original game's number
    -- the migration's own header says ``skill_points -- NOT MEASURED, AND
    ORDERED ANYWAY``.  Both files record the same ORDER; agreeing about an
    order is all this proves, and that is exactly the thing D5 showed was
    unproven.  ``BIRTH_SKILL_POINTS_PROVENANCE`` stays ``ASSUMPTION``.
    """
    import re
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[2] / _BIRTH_SKILL_POINTS_SCHEMA_ANCHOR
    )
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SkillPointCurveError(
            REFUSE_BIRTH_SCHEMA_ANCHOR_UNREADABLE,
            "cannot read %s, named as the schema anchor for the birth "
            "skill-point order: %s" % (_BIRTH_SKILL_POINTS_SCHEMA_ANCHOR, error),
        ) from error
    # Comment lines dropped first: this migration's header discusses its own
    # DDL at length, including the string `skill_points INTEGER DEFAULT 0` in
    # prose, and a scan that reads prose would pass while the DDL said 5.
    body = "\n".join(
        line for line in text.splitlines()
        if not line.lstrip().startswith("--")
    )
    found = re.findall(
        r"\b%s\s+INTEGER\s+DEFAULT\s+(-?\d+)"
        % re.escape(_BIRTH_SKILL_POINTS_SCHEMA_COLUMN),
        body,
    )
    if not found:
        raise SkillPointCurveError(
            REFUSE_BIRTH_SCHEMA_ANCHOR_UNREADABLE,
            "%s carries no `%s INTEGER DEFAULT <n>` outside its comments"
            % (
                _BIRTH_SKILL_POINTS_SCHEMA_ANCHOR,
                _BIRTH_SKILL_POINTS_SCHEMA_COLUMN,
            ),
        )
    if len(set(found)) != 1:
        raise SkillPointCurveError(
            REFUSE_BIRTH_SCHEMA_ANCHOR_UNREADABLE,
            "%s declares %s with more than one default (%r); this function "
            "will not pick one"
            % (
                _BIRTH_SKILL_POINTS_SCHEMA_ANCHOR,
                _BIRTH_SKILL_POINTS_SCHEMA_COLUMN,
                sorted(set(found)),
            ),
        )
    return int(found[0])


def birth_skill_points() -> int:
    """The skill points a character is born holding, re-graded on every call.

    WHY A FUNCTION AND NOT JUST THE CONSTANT.  The same reason the vitals
    module re-validates its three birth numbers before handing them back
    (named nowhere in this file on purpose -- see the header):
    a birth value that contradicts this module's own rules is a
    character the server would compose wrongly on its first login, and the
    failure would surface far from the edit that caused it.  Three checks,
    run every call, are cheaper than finding that out from a database.

    WHAT IT REFUSES, and each one is a real edit somebody could make:

      * a provenance label this module does not know (``"probably"``);
      * ``ASSUMPTION`` paired with any number other than the one the owner
        ordered -- this is the guessed-number door
        ``COO-DECISION 20260908_1441`` point 3 closes by name;
      * ``MEASURED`` with no named source, which is the shape of a round
        upgrading the label without doing the reading; and its mirror,
        a named source under an ``ASSUMPTION`` label.

    WHAT IT DOES NOT DO.  It is not a write, it touches no database, and it
    is not a claim that 0 is the original game's number -- see
    ``BIRTH_SKILL_POINTS_PROVENANCE``.  A caller may also read
    ``BIRTH_SKILL_POINTS`` directly and skip all of this; the constant is
    exported because a pin has to be able to name it.
    """
    if BIRTH_SKILL_POINTS_PROVENANCE not in PROVENANCE_LABELS:
        raise SkillPointCurveError(
            REFUSE_BIRTH_PROVENANCE_UNKNOWN,
            "provenance must be one of %r, got %r"
            % (PROVENANCE_LABELS, BIRTH_SKILL_POINTS_PROVENANCE),
        )
    # pf-adversary D5: the ORDER is graded against the committed migration
    # before the published value is graded against the order.  Unconditional,
    # under either label -- a MEASURED number that contradicts the schema
    # every character is actually born under is a worse bug than an
    # unmeasured one, not a better one.
    schema_ordered = schema_birth_skill_points()
    if schema_ordered != OWNER_ORDERED_BIRTH_SKILL_POINTS:
        raise SkillPointCurveError(
            REFUSE_BIRTH_ORDER_NOT_IN_THE_SCHEMA,
            "this module records the owner's order as %d, and %s builds "
            "`characters` with `%s ... DEFAULT %d`; one of the two moved "
            "without the other"
            % (
                OWNER_ORDERED_BIRTH_SKILL_POINTS,
                _BIRTH_SKILL_POINTS_SCHEMA_ANCHOR,
                _BIRTH_SKILL_POINTS_SCHEMA_COLUMN,
                schema_ordered,
            ),
        )
    if BIRTH_SKILL_POINTS_PROVENANCE == PROVENANCE_ASSUMPTION:
        if BIRTH_SKILL_POINTS != OWNER_ORDERED_BIRTH_SKILL_POINTS:
            raise SkillPointCurveError(
                REFUSE_BIRTH_ASSUMPTION_NOT_AS_ORDERED,
                "an unmeasured birth value may only be the %d the owner "
                "ordered (PANYA-DECISION 20260908_1218 point 3), got %r"
                % (OWNER_ORDERED_BIRTH_SKILL_POINTS, BIRTH_SKILL_POINTS),
            )
        if BIRTH_SKILL_POINTS_SOURCE:
            raise SkillPointCurveError(
                REFUSE_BIRTH_ASSUMPTION_WITH_SOURCE,
                "a value that names the shipped table %r is not an "
                "assumption -- relabel it %s"
                % (BIRTH_SKILL_POINTS_SOURCE, PROVENANCE_MEASURED),
            )
    elif not BIRTH_SKILL_POINTS_SOURCE:
        raise SkillPointCurveError(
            REFUSE_BIRTH_MEASURED_WITHOUT_SOURCE,
            "a %s birth value must name the shipped table it was read off"
            % (PROVENANCE_MEASURED,),
        )
    return BIRTH_SKILL_POINTS


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
        "strictly_increasing=%s readings_undecided=%d birth_sp=%d "
        "birth_sp_provenance=%s source_sha256=%s"
        % (
            len(_ROWS),
            TABLE_FIRST_LEVEL,
            TABLE_LAST_LEVEL,
            _ROWS[TABLE_FIRST_LEVEL].sp,
            _ROWS[TABLE_LAST_LEVEL].sp,
            "yes" if is_strictly_increasing() else "no",
            len(UNDECIDED_READINGS),
            birth_skill_points(),
            BIRTH_SKILL_POINTS_PROVENANCE,
            SOURCE_SHA256[:16],
        )
    )


if __name__ == "__main__":  # pragma: no cover - console entry point
    print(headless_summary())
