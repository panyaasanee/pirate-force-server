"""LANE-DB: the experience a character earns turns into a LEVEL.

WHAT A PLAYER GETS BECAUSE OF THIS FILE, FIRST AND WITHOUT DECORATION.
Today a payout that reaches ``characters.experience`` (LANE-Q's
``Player.AddExp``, through ``store.add_typed_attribute``) makes the number
in that column bigger and nothing else ever happens: the character stays at
the level it was created with forever, because no code in this repository
turns experience into a level.  With this module and its store door, the
same payout can raise ``characters.level`` -- and because both columns are
in ``characters``, the new level is still there after a relog.

THE RULE IS NOT THIS LANE'S INVENTION, AND THAT IS THE WHOLE POINT.
``persistence_standard_status`` already carries the client's own per-level
table, pinned by sha256, and names the ONE independently proven consumer of
its ``n_EXP_CURRENTLV`` column: the client's XP bar (``0x519299``) divides
displayed experience by ``STANDARD_STATUS[level + 1].n_EXP_CURRENTLV``.
That is a denominator, and a denominator is a threshold: the bar is full
exactly when the character's experience reaches the row for the NEXT level.
So :func:`threshold_for_next_level` reads that row and nothing else, and
:func:`plan_experience_gain` levels up exactly when the bar the player is
looking at would be full.  No constant is invented here, no curve is
fitted, and no column outside the two named ones is touched
(``COO-DECISION 20260901_1059``: a field with no source is never guessed).

WHAT LAYER THE PROVEN FACT LIVES ON.  It is a STATIC DISASSEMBLY reading
(``STATS-PROG-001`` in ``docs/FUNCTIONAL_COVERAGE.json``: the divide at
``0x519299``, and the same record's scaling by 100 to a percentage).  That
record also says, in as many words, that nothing in this project has ever
observed a progression field on a wire in either direction, and queues the
runtime check as ``GT-017``.  So "the bar the player is looking at" is
shorthand for an instruction read out of the client image, not for
something anybody has watched happen -- pf-adversary (round ``6n7pam``,
``D10``) was right that the first draft of this docstring wrote the
present tense without saying which layer it came from.

WHAT IS DERIVED RATHER THAN MEASURED, AND WHY THE FIRST ARGUMENT FOR IT WAS
WRONG.  The proven fact is the DIVISION.  That the remainder carries
forward -- a character crossing the line keeps ``experience - threshold``
rather than dropping to zero or keeping a running total -- is this module's
reading, not a measurement.  The reason first written here ("a cumulative
numerator makes the division exceed 1.0") is FALSE and is struck: under a
self-consistent cumulative reading a character at level L holds ``row(L) <=
experience < row(L + 1)``, so that quotient stays below 1.0 at every level
(pf-adversary ``D3`` measured the error).  The argument that does hold is
about where the bar STARTS: under the cumulative reading a fresh level
begins at ``row(L) / row(L + 1)``, which is 99.4% at level 254 -- a bar
that is nearly full the moment you level and crawls to full over the whole
level.  Under the per-level reading it starts empty and fills once.  Only
the second is a bar anybody would ship.
``standard_status_row(1).exp_currentlv == 0`` is NOT evidence either way
(it is what both readings look like at the first level) and this module
does not use it as any; :func:`threshold_for_next_level` refuses a
non-positive threshold outright.
The carry rule is pinned by :func:`plan_experience_gain`'s tests, and
``test_dropping_the_remainder_is_a_different_rule_and_the_tests_see_it``
is the one that actually separates it from the alternative -- the
"numerator stays inside the bar" test does not, because that is the loop's
own exit condition restated (``D3`` again).

NONCLAIMS.
* Nothing here sends a frame.  A client that is already logged in does not
  learn about a level change from this module; the new level reaches a
  screen through the attribute block composed at the next login
  (``persistence_attr_compose``), which is where every other typed column
  reaches it too.
* Nothing here grants anything for the level: ``n_POINT_ABILITY`` in the
  same table is the unproven guess ``persistence_standard_status``'s own
  docstring labels as such, and this module does not build on it -- no
  ability point, no stat, no HP, no skill point moves because a level did.
  A level number is the entire claim.
* The table stops at level 255 (``STANDARD_STATUS_MAX_LEVEL``).  At that
  level there is no next row, so there is no threshold and no level-up;
  experience keeps accumulating in its own column and this module says so
  with :attr:`ExperienceGain.at_table_ceiling` rather than inventing a cap
  or silently swallowing the payout.
"""
from __future__ import annotations

from dataclasses import dataclass

from .persistence_standard_status import (
    STANDARD_STATUS_MAX_LEVEL,
    STANDARD_STATUS_MIN_LEVEL,
    standard_status_row,
)

#: The two ``characters`` columns this module reasons about, by name, so a
#: caller and a test name them from here rather than typing the strings.
LEVEL_COLUMN = "level"
EXPERIENCE_COLUMN = "experience"


class ExperienceError(ValueError):
    """A grant that cannot be planned: a bad amount, or a character whose
    level/experience pair is outside what the committed table can answer.
    Never a plan with a guessed value substituted for the bad one."""


class InconsistentLevelExperienceError(ExperienceError):
    """The character's stored pair is ALREADY past the line before the
    grant: ``experience >= threshold_for_next_level(level)``.

    THE HOLE THIS CLOSES, MEASURED BY pf-adversary (round ``6n7pam``,
    ``D5``) BEFORE IT COULD SHIP.  ``characters.experience`` has other
    doors -- ``store.add_typed_attribute`` adds to it without consulting
    the level, ``store.spend_typed_attribute`` subtracts from it, and the
    GM's ``/lv`` writes ``characters.level`` on its own.  Without this
    refusal, experience banked through one of those doors is harvested by
    the NEXT grant through this one, whatever its size: a payout of ZERO
    awarded two levels in the adversary's run, and a character whose level
    a GM had set to 50 was re-derived to 123.  A level nobody granted, on a
    payout nobody made, is worse than a refusal.

    So the pair is not adjudicated here.  This door raises, names both
    values, and leaves the row untouched: deciding what a level should be
    when another door moved the column underneath it is a rule this project
    has not made, and inventing one inside a grant would be exactly the
    guess ``COO-DECISION 20260901_1059`` forbids this lane.  The way out is
    for a payout to use ONE door -- this one -- which is what the letter to
    LANE-Q asks for.
    """


@dataclass(frozen=True)
class ExperienceGain:
    """What one grant does to the level/experience pair, before any write.

    ``levels_gained`` is ``level_after - level_before`` and is carried
    explicitly so a caller does not have to subtract to find out whether
    anything visible happened.  ``at_table_ceiling`` is True when the
    character sits at ``STANDARD_STATUS_MAX_LEVEL`` AFTER the grant, which
    is the one state in which further experience buys no level.
    """

    level_before: int
    level_after: int
    experience_before: int
    experience_after: int
    amount: int
    levels_gained: int
    at_table_ceiling: bool


def threshold_for_next_level(level: int) -> int | None:
    """Experience needed to leave ``level``, or ``None`` at the ceiling.

    The value is ``standard_status_row(level + 1).exp_currentlv`` -- the
    denominator the client's own XP bar divides by while the character is
    at ``level``.  ``None`` means the committed table has no row for
    ``level + 1``, which is a real answer ("there is no next level"), not a
    missing one.

    Raises :class:`ExperienceError` for a level the table cannot describe at
    all (a non-int, or outside its ``1..255``), because a threshold read for
    such a level would be a guess either way.
    """
    if type(level) is not int:
        raise ExperienceError("level must be an int, got %r" % (level,))
    if not STANDARD_STATUS_MIN_LEVEL <= level <= STANDARD_STATUS_MAX_LEVEL:
        raise ExperienceError(
            "level %d is outside the committed table's %d..%d range"
            % (level, STANDARD_STATUS_MIN_LEVEL, STANDARD_STATUS_MAX_LEVEL)
        )
    if level == STANDARD_STATUS_MAX_LEVEL:
        return None
    threshold = standard_status_row(level + 1).exp_currentlv
    if threshold <= 0:
        # Not reachable on the committed table (every row from 2 up is
        # positive and increasing) and deliberately not trusted anyway: a
        # zero threshold would let the loop in `plan_experience_gain` raise
        # a level for free, forever.  Refusing names the row instead.
        raise ExperienceError(
            "standard status row %d has a non-positive n_EXP_CURRENTLV "
            "(%d); refusing to treat it as a level-up threshold"
            % (level + 1, threshold)
        )
    return threshold


def plan_experience_gain(
    level: int, experience: int, amount: int
) -> ExperienceGain:
    """Add ``amount`` to ``experience`` and spend it on levels.

    Pure arithmetic: it reads the committed table and touches no database,
    so a caller can compute the plan inside its own transaction (which is
    what ``store.grant_experience`` does) and a test can check the rule
    without a store at all.

    ``amount`` must be an ``int`` at or above zero.  This is a GRANT door;
    taking experience away is a different rule (what happens to the level
    when experience falls below the threshold it bought is a question
    nobody in this project has answered, and answering it by accident here
    would be exactly the guess the owner's ``1059`` rule forbids).

    Multiple levels in one grant are supported and expected: a quest that
    pays more than the next threshold raises the level as many times as the
    table allows, stopping at ``STANDARD_STATUS_MAX_LEVEL`` with the
    leftover experience intact in ``experience_after``.
    """
    if type(amount) is not int:
        raise ExperienceError("amount must be an int, got %r" % (amount,))
    if amount < 0:
        raise ExperienceError(
            "amount must be >= 0, got %d -- this door only grants "
            "experience; removing it is a rule this project has not "
            "adjudicated" % amount
        )
    if type(experience) is not int:
        raise ExperienceError(
            "experience must be an int, got %r" % (experience,)
        )
    if experience < 0:
        raise ExperienceError(
            "experience must be >= 0, got %d" % experience
        )
    # `threshold_for_next_level` is the level validator too: it refuses a
    # level the committed table cannot describe, before anything is added.
    threshold = threshold_for_next_level(level)
    if threshold is not None and experience >= threshold:
        raise InconsistentLevelExperienceError(
            "character is stored at level %d with %d experience, which is "
            "already at or past the %d this table wants for the next level "
            "-- another door moved a column under this one; refusing to "
            "turn somebody else's write into levels" % (
                level, experience, threshold)
        )

    new_level = level
    total = experience + amount
    while threshold is not None and total >= threshold:
        total -= threshold
        new_level += 1
        threshold = threshold_for_next_level(new_level)

    return ExperienceGain(
        level_before=level,
        level_after=new_level,
        experience_before=experience,
        experience_after=total,
        amount=amount,
        levels_gained=new_level - level,
        at_table_ceiling=new_level == STANDARD_STATUS_MAX_LEVEL,
    )
