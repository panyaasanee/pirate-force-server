"""LANE-CS: every skill row the client's own table declares, not just 8.

WHERE THE PROJECT STOPS WITHOUT THIS MODULE.  ``skill_catalog.py`` carries
the 8 starting-kit skill ids and is right to: it exists to answer "what does
a freshly created character of class N hold", and that question has a
committed answer.  But ``skill_learn_validator.can_afford_to_learn`` reads
its cost through that same 8-id catalog, so on a real learn request for any
other id -- and the client's own table declares 2165 of them -- the server
answered ``KeyError``, which a caller cannot tell apart from a broken
lookup.  A player clicking a skill her own client drew could not be told
"you cannot learn that yet" or "that costs 4 points"; nothing in src/ knew
the row existed.  This module is that census, and only that.

WHAT IT IS.  A verbatim copy of
``pf_bridge/gamedata/tables/CONSTDATA_TH__SKILL_CONTEXT.tsv`` (all 20
columns, all 2165 rows, the client's own order), sha256-pinned at import,
plus readers for the three columns a learn rule needs.  The copy is written
by ``tools/pf_skill_context_census_extract.py``; drift against the bridge is
caught by the ``BRIDGE_GAMEDATA``-guarded test in
``tests/test_skill_context_census.py`` that re-runs the extractor and diffs.

THE KIT COPY IS A ROW SUBSET OF THIS ONE, BYTE FOR BYTE, and that is
asserted at import (``_cross_check_starting_kit``), not merely hoped for.
Two files carrying the same rows is how two answers drift apart; the check
turns that into an import-time failure with the offending id named.

WHAT THIS MODULE REFUSES TO SAY, measured rather than assumed
------------------------------------------------------------
  * ``n_LEVELS`` IS NOT A RANK COUNT THIS MODULE WILL DO ARITHMETIC ON.
    Its values across the 2165 rows are 1 (1982 rows), 120 (14 rows) and
    4294967295 (169 rows).  4294967295 is 0xFFFFFFFF -- an unsigned
    sentinel, not a number of ranks -- so "cost of rank 2 = f_SP_LEVEL2PLUS
    times something" would be arithmetic on a sentinel for 169 skills.
    :func:`declared_rank_count` returns the raw value and
    :func:`rank_count_is_a_real_count` says which rows can carry a rank
    question at all.  No rank-2 cost is computed anywhere in this file.
  * ``n_PASSIVE`` IS NOT A BOOLEAN.  Six distinct values (0,1,2,3,4,5) with
    1016 rows at 2 and 910 at 3; nothing committed states what any of them
    mean, so the column is carried under its own name and never read as
    "is this a passive skill".  Same for ``n_TARGET`` (0,1,2,4,5), which is
    the column an AOE question would eventually be asked of.
  * WHO MAY LEARN WHAT IS NOT IN HERE.  pf-adversary (round ``iazmrv``)
    measured that no committed table maps a class to its full skill list --
    see ``tools/pf_class_skill_starting_kit_extract.py`` for the four
    reasons.  A census of rows is not a curriculum, and this module makes no
    class claim of any kind.
  * NOTHING HERE HAS BEEN SEEN ON A CLIENT.  The numbers below are what the
    shipped table says; that a client enforces any of them is unmeasured.
"""
from __future__ import annotations

from pathlib import Path
import csv
import hashlib

from . import skill_catalog

_ALL_CONTEXT_PATH = Path(__file__).parent / "data" / "skill_context_all.tsv"

ALL_CONTEXT_SOURCE_SHA256 = (
    "41d642c535bfefd9a560cb8fc92a530a51bd3ca55168eddae93cfd64dca7c4f4"
)

#: 0xFFFFFFFF.  What ``n_LEVELS`` carries for 169 of the 2165 rows: an
#: unsigned sentinel standing in for "not set", not a count of ranks.  Named
#: here so no caller has to recognise the bare number.
RANK_COUNT_SENTINEL = 4294967295

#: The census as measured on the pinned copy, pinned so a table swap that
#: changes the shape of the answer cannot pass quietly.
DECLARED_SKILL_ROWS = 2165


class SkillContextCensusError(RuntimeError):
    """Raised when the pinned copy drifted, or a lookup cannot be answered."""


def _load_rows() -> list[dict]:
    raw = _ALL_CONTEXT_PATH.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != ALL_CONTEXT_SOURCE_SHA256:
        raise SkillContextCensusError(
            "%s sha256 mismatch: expected %s, got %s -- the census drifted "
            "from the pinned client source, re-derive with "
            "tools/pf_skill_context_census_extract.py before trusting it"
            % (_ALL_CONTEXT_PATH.name, ALL_CONTEXT_SOURCE_SHA256, actual)
        )
    with _ALL_CONTEXT_PATH.open("r", encoding="ascii", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


_ROWS = _load_rows()

SKILL_ID_TO_RAW_CONTEXT: dict[int, dict[str, str]] = {
    int(row["n_ID"]): dict(row) for row in _ROWS
}

DECLARED_SKILL_IDS: tuple[int, ...] = tuple(sorted(SKILL_ID_TO_RAW_CONTEXT))


def _cross_check_starting_kit() -> None:
    """The 8 kit rows must be THIS file's rows, column for column.

    ``skill_catalog`` carries a narrower column projection of the same
    source, so the comparison is over the columns the kit copy kept.  A
    mismatch means one of the two copies was re-derived and the other was
    not, which is exactly the state that makes a server answer two different
    costs for one skill id depending on which module a caller reached first.
    """
    for skill_id, kit_row in skill_catalog.SKILL_ID_TO_RAW_CONTEXT.items():
        mine = SKILL_ID_TO_RAW_CONTEXT.get(skill_id)
        if mine is None:
            raise SkillContextCensusError(
                "starting-kit skill id %d is missing from the census copy"
                % (skill_id,)
            )
        for column, value in kit_row.items():
            if mine.get(column) != value:
                raise SkillContextCensusError(
                    "skill id %d column %s disagrees: kit copy %r, census "
                    "copy %r -- re-derive both with their extractors"
                    % (skill_id, column, value, mine.get(column))
                )


_cross_check_starting_kit()


def _row(skill_id: int) -> dict:
    if isinstance(skill_id, bool) or not isinstance(skill_id, int):
        raise TypeError(
            "skill_id must be an int, got %s" % type(skill_id).__name__
        )
    try:
        return SKILL_ID_TO_RAW_CONTEXT[skill_id]
    except KeyError:
        raise SkillContextCensusError(
            "skill id %d is not one of the %d rows the client's own "
            "SKILL_CONTEXT table declares -- refusing rather than inventing "
            "a default row for it" % (skill_id, DECLARED_SKILL_ROWS)
        ) from None


def is_declared(skill_id: int) -> bool:
    """`True` when the client's own table carries a row for this id."""
    return (
        not isinstance(skill_id, bool)
        and isinstance(skill_id, int)
        and skill_id in SKILL_ID_TO_RAW_CONTEXT
    )


def raw_context(skill_id: int) -> dict:
    """This skill's row, columns under their own client-given names."""
    return dict(_row(skill_id))


def level_to_learn(skill_id: int) -> int:
    """``n_LEVEL_LEARN``: the character level the table puts on this skill.

    Raw, unmodified.  Across the census it takes 21 distinct values, a
    ladder from 1 to 120 (1991 rows sit at 1).  What the client does with
    it is not claimed here -- see :func:`meets_level_requirement` for the
    one rule this lane builds on it and for who ordered that rule.
    """
    return int(_row(skill_id)["n_LEVEL_LEARN"])


def meets_level_requirement(character_level: int, skill_id: int) -> bool:
    """`True` when `character_level` reaches this skill's ``n_LEVEL_LEARN``.

    WHY THIS RULE EXISTS AND WHO ORDERED IT.  ``PANYA 20260908_1455`` spells
    the GM practice sandbox as ``/skill all`` plus ``/job``, explicitly
    "ignoring ``n_LEVEL_LEARN``".  A bypass names the thing it bypasses: the
    ordinary path is the one that honours the column, and this is that
    check.  It is deliberately a plain comparison against the table value --
    no scaling, no per-class adjustment, no rounding -- because the table
    states one number and nothing committed states a transform of it.

    ``Lv`` COMPARISON IS ``>=`` AND THAT IS NOT A COIN FLIP: the column is
    named LEVEL_LEARN and 1991 rows carry 1, the level every character
    starts at; reading it as "strictly greater" would make those 1991 rows
    unlearnable at level 1, which no client behaviour supports.

    Refuses a level that is not a plain non-negative ``int`` rather than
    comparing a ``bool`` as 1/0.
    """
    if isinstance(character_level, bool) or not isinstance(
        character_level, int
    ):
        raise TypeError(
            "character_level must be an int, got %s"
            % type(character_level).__name__
        )
    if character_level < 0:
        raise SkillContextCensusError(
            "character_level must be >= 0, got %r" % (character_level,)
        )
    return character_level >= level_to_learn(skill_id)


def declared_rank_count(skill_id: int) -> int:
    """``n_LEVELS`` raw, sentinel included -- see the module docstring."""
    return int(_row(skill_id)["n_LEVELS"])


def rank_count_is_a_real_count(skill_id: int) -> bool:
    """`False` when ``n_LEVELS`` is the 0xFFFFFFFF sentinel or is 0.

    The one guard between this lane and a rank cost computed by multiplying
    a sentinel.  169 of the 2165 rows answer `False` here.
    """
    value = declared_rank_count(skill_id)
    return 0 < value < RANK_COUNT_SENTINEL


def rank_one_point_cost(skill_id: int) -> float:
    """``f_SP_LEVE1`` raw: what the table charges for this skill's first rank.

    Raw and unrounded, including the fractional values the table really
    carries (the census holds 0.0, 0.2, 0.4, 1.0, 4.0 and 8.0, and 1767 of
    the 2165 rows carry 0.0).  A caller deciding affordability must decide
    what a 0.0 means for itself -- ``skill_learn_validator`` refuses it by
    name rather than reporting the skill free, and this reader does not make
    that decision on the caller's behalf.
    """
    return float(_row(skill_id)["f_SP_LEVE1"])
