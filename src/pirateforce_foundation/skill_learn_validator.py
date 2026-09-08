"""LANE-CS: skill-point learn-request validator.

`PANYA-DECISION 20260904_0328` piece 5 / `COO-DECISION 20260905_0155`
direction "ระบบเรียนสกิล/skill point" (the skill-learn / skill-point
system): before a character's skill window grants a new skill, something
has to check she can afford it.  This module is that check, and nothing
more.

WHAT THIS MODULE ANSWERS.  Given a character's current skill-point balance
and a target `skill_id`, can she afford `skill_catalog.
skill_point_cost_to_learn(skill_id)`?  It reads `skill_catalog` (LANE-CS's
own table-pinned accessor for `SKILL_CONTEXT.f_SP_LEVE1`) and nothing else.

WHAT THIS MODULE DOES NOT DO.

* It does not read a character's skill-point balance.  `current_skill_points`
  is a plain `int` the caller supplies.  The wire field that would carry
  this value on the wire (`attr_wire.py`'s `skill_points` / `"SP"`, actor
  offset `0x7C`) and the row that would persist it are LANE-GM's and
  LANE-DB's write zones respectively -- this module has no database
  connection, no store, no wire, no socket, same posture as
  `persistence_starting_skills.py`'s own "what this module does not do".
* It does not WRITE anything.  `skill_points_after_learning` (below) computes
  the balance a caller WOULD deduct, but neither function touches a
  database, a store or a wire -- writing the granted skill id and the new
  balance is a caller's job (a future learn-request hookup chief would
  grant, the same shape `persistence_starting_skills` already documents as
  pending for piece 5's other half).
* It does not guess a skill's cost.  An unknown `skill_id` propagates
  whatever `skill_catalog.skill_raw_context` raises (`KeyError`) rather
  than defaulting to "free" or "unaffordable" -- silently guessing either
  one would be worse than refusing (`COO-DECISION 20260901_1059`).
* It does not handle multi-rank costs.  `skill_catalog.
  skill_point_cost_to_learn` only reads `f_SP_LEVE1` (rank 1); every one of
  the 8 starting-kit ids has `n_LEVELS == 1` (see `skill_catalog.
  max_skill_level`), so a rank-2+ cost (`f_SP_LEVEL2PLUS`) is out of scope
  here for the same reason `skill_catalog.py` itself does not name an
  accessor for that column yet.

ZERO PRODUCTION CALLERS, same posture as `skill_catalog`'s own accessors
and `persistence_starting_skills.resolve_starting_skill_ids`: this is a
read/compare, not a gate, until a learn-request hookup calls it.

[UPDATE, this round]: `skill_points_after_learning` is the "spend" half
`can_afford_to_learn`'s own docstring named as a caller's job -- pure
arithmetic (`current_skill_points - cost`), same zero-DB posture.
`skill_catalog.skill_point_cost_to_learn` returns the client's own
`f_SP_LEVE1` column unmodified, and it is not always a whole number (id 111
"VIP Strive Jump" costs 0.20000000298023224 -- see
`tests/test_skill_catalog.py`).  The `skill_points` column this project's
own schema commits to (`migrations/006_character_typed_attribute_columns
.sql`) is `INTEGER`-typed and CHECKed as such.

[UPDATE, `COO-DECISION 20260905_1245`]: a fractional cost now spends
`math.ceil(cost)` points -- a house rule for *any* `skill_id` whose cost is
not a whole number, not a special case for id 111.  `id 111` costs `1`
skill point under this rule.  Reasoning owned by the decision, not this
docstring: the `skill_points` column and the wire field that feeds it
(`attr_wire.py`'s `"SP"`, actor offset `0x7C`) are both whole-number typed,
so the table's intent ("this skill has a cost") survives as "round up",
never "free" (floor to `0`) and never "impossible to ever learn" (the old
refusal).  A cost that is `<= 0` is unaffected by this decision and still
refuses -- this project's tables have never carried one (all 8
starting-kit ids cost `1.0` or `0.20000000298023224`), so a non-positive
cost stays a defect to refuse loudly rather than a value to round to zero
or spend as a negative number.  All 7 of the other 8 starting-kit ids cost
exactly `1.0` and are unaffected by the rounding rule.

[UPDATE, this round]: the `cost <= 0` refusal above moved from
`skill_points_after_learning` to `can_afford_to_learn`.  Before this round
`can_afford_to_learn(current_skill_points, skill_id)` had no such guard --
for a hypothetical zero-or-negative-cost `skill_id` it returned `True`
(reported the skill affordable) for any non-negative balance, while
`skill_points_after_learning` on the exact same inputs raised.  Two
functions on the same module disagreeing about whether the identical
`(current_skill_points, skill_id)` pair is refusable is the kind of drift
this project's docstrings exist to catch; pf-adversary flagged it in round
`7fqb46` (`pirate-force-server#825`'s own description) as real but out of
scope for that round, since no committed `skill_id` costs `<= 0` today and
nothing calls either function in production yet.  `can_afford_to_learn` is
now the single place that decides refusable-vs-affordable, and
`skill_points_after_learning` no longer repeats the check -- it inherits
the refusal by calling `can_afford_to_learn` first, same as it already did
for the negative-balance and bad-type guards.
"""
from __future__ import annotations

import math

from . import skill_catalog
from . import skill_context_census


class SkillLearnValidatorError(RuntimeError):
    """Raised when `current_skill_points` is not a valid non-negative count."""


def can_afford_to_learn(current_skill_points: int, skill_id: int) -> bool:
    """`True` if `current_skill_points` covers
    `skill_catalog.skill_point_cost_to_learn(skill_id)`, else `False`.

    Raises `TypeError` for a `current_skill_points` that is not a plain
    `int` (a `bool` included -- `True`/`False` are `int` in Python and
    would silently compare as 1/0, the same refusal
    `persistence_starting_skills.resolve_starting_skill_ids` makes for
    `class_id`).  Raises `SkillLearnValidatorError` for a negative balance
    -- not a state this project's own wire/store ever names, so refusing it
    beats guessing what a negative balance should mean.  Raises the same
    error for a `skill_id` whose cost is `<= 0` -- a value this project's
    tables have never carried (see the module docstring's
    `COO-DECISION 20260905_1245` paragraph) -- rather than reporting it
    "affordable" for free, which is what the bare `current_skill_points >=
    cost` compare below would otherwise do for any non-negative balance
    (pf-adversary, round `jbe8rr`/`7fqb46`: flagged as a real asymmetry with
    `skill_points_after_learning`'s own refusal of the identical cost,
    fixed here instead of left latent).  Raises whatever
    `skill_catalog.skill_point_cost_to_learn` raises (`KeyError`) for a
    `skill_id` outside the 8-id starting-kit catalog -- this module does not
    catch that and turn it into `False`, because "unaffordable" and
    "unknown skill" are different failures a caller must not conflate.
    """
    if isinstance(current_skill_points, bool) or not isinstance(
        current_skill_points, int
    ):
        raise TypeError(
            "current_skill_points must be an int, got %s"
            % type(current_skill_points).__name__
        )
    if current_skill_points < 0:
        raise SkillLearnValidatorError(
            "current_skill_points must be >= 0, got %r" % (current_skill_points,)
        )
    cost = skill_catalog.skill_point_cost_to_learn(skill_id)
    if cost <= 0:
        raise SkillLearnValidatorError(
            "skill_id %r costs %r skill points -- a non-positive cost is "
            "not a value this project's tables are expected to carry; "
            "refusing rather than reporting it affordable for free "
            "(COO-DECISION 20260905_1245)" % (skill_id, cost)
        )
    return current_skill_points >= cost


def skill_points_after_learning(current_skill_points: int, skill_id: int) -> int:
    """The skill-point balance remaining after spending
    `skill_catalog.skill_point_cost_to_learn(skill_id)` from
    `current_skill_points` -- pure arithmetic, no database read, no
    database write, no grant.

    Raises the same errors `can_afford_to_learn` raises, for the same
    reasons, on the same inputs (`TypeError` for a non-`int`/`bool`
    balance, `SkillLearnValidatorError` for a negative balance, for a
    `skill_id` whose cost is `<= 0`, and `KeyError` for an unknown
    `skill_id`) -- this function does not repeat any of those checks
    itself, it calls `can_afford_to_learn` first and lets its refusal
    propagate, so the two functions cannot drift apart on what counts as a
    refusable cost (`[UPDATE, this round]` below is the fix for the one
    place they had).  Additionally raises `SkillLearnValidatorError` when
    `can_afford_to_learn(current_skill_points, skill_id)` returns `False`
    -- spending more than the balance holds is a caller bug this function
    refuses rather than returning a negative result.

    A fractional cost (not a whole number) spends `math.ceil(cost)` points
    -- `COO-DECISION 20260905_1245`'s house rule for any such `skill_id`,
    id 111 ("VIP Strive Jump", cost `0.20000000298023224`) included.  This
    never returns a negative balance: `can_afford_to_learn` above already
    required `current_skill_points >= cost` with the raw (unrounded) cost,
    and an `int` balance that is `>=` a non-integer real number is
    necessarily `>=` that number's ceiling too.
    """
    if not can_afford_to_learn(current_skill_points, skill_id):
        raise SkillLearnValidatorError(
            "cannot spend: current_skill_points %r does not cover "
            "skill_catalog.skill_point_cost_to_learn(%r) -- call "
            "can_afford_to_learn first" % (current_skill_points, skill_id)
        )
    cost = skill_catalog.skill_point_cost_to_learn(skill_id)
    spend = cost if cost.is_integer() else math.ceil(cost)
    return current_skill_points - int(spend)


#: The named refusals :func:`refusal_to_learn` can return.  Strings, not an
#: enum, because they travel to a console line and into a test's assertion
#: unchanged, and because every other refusal in this lane is already a
#: named string a caller can match on (the login-frame module's
#: `record_count_is_above_any_observed_acceptance` is the shape; its name is
#: deliberately not spelled here -- that module's `callers_in_src` token
#: counts every sibling that mentions it, and a prose mention would make an
#: operator's console line report a caller this file is not).
REFUSED_SKILL_NOT_DECLARED = "skill_id_not_in_skill_context"
REFUSED_LEVEL_TOO_LOW = "character_level_below_n_level_learn"
REFUSED_COST_NOT_POSITIVE = "f_sp_leve1_is_not_positive"
REFUSED_NOT_ENOUGH_POINTS = "skill_points_below_f_sp_leve1"


def refusal_to_learn(
    current_skill_points: int, character_level: int, skill_id: int
) -> "str | None":
    """The reason this character cannot learn this skill, or `None`.

    WHY THIS FUNCTION EXISTS, AND WHAT CHANGED.  `can_afford_to_learn` above
    answers ONE of the two questions the client's own table asks -- can she
    pay -- and only for the 8 starting-kit ids `skill_catalog` carries; for
    every other id it raises `KeyError`, which is indistinguishable from a
    broken lookup.  The client's table declares 2165 skills.  This function
    answers for all of them, through `skill_context_census`, and adds the
    second question the table states: has she reached the skill's own
    `n_LEVEL_LEARN` (see `skill_context_census.meets_level_requirement` for
    who ordered that rule and why the comparison is `>=`).

    ORDER OF THE CHECKS IS PART OF THE ANSWER.  Declared, then level, then
    cost: an undeclared id has no level to check, and a player who is too
    low to learn a skill should be told THAT and not "you are 3 points
    short", which is a different thing to go and fix.

    RETURNS `None` FOR "NOTHING REFUSES", not `True` for "allowed".  There is
    no grant here and no permission being given: this module has no store,
    no wire and no socket (see the module docstring), and a caller that
    writes a skill row is doing so on its own authority.  A named string is
    also what a console line and a test can carry unchanged, which a bool
    cannot.

    RAISES rather than refusing for inputs that are not answerable at all:
    `TypeError` for a non-`int` (or `bool`) balance, level or skill id, and
    `SkillLearnValidatorError` for a negative balance -- same posture, same
    reasons, as `can_afford_to_learn`.

    WHAT IT STILL DOES NOT ASK.  Whether this character's CLASS may learn
    this skill (no committed table maps a class to its full skill list --
    `skill_context_census`'s docstring carries the measurement), whether she
    already knows it (that is a store read, and the store is not this
    module's), whether a rank beyond the first costs anything (`n_LEVELS` is
    a sentinel for 169 rows -- the census refuses that arithmetic by name),
    and whether any client enforces any of this (unmeasured).
    """
    if isinstance(current_skill_points, bool) or not isinstance(
        current_skill_points, int
    ):
        raise TypeError(
            "current_skill_points must be an int, got %s"
            % type(current_skill_points).__name__
        )
    if current_skill_points < 0:
        raise SkillLearnValidatorError(
            "current_skill_points must be >= 0, got %r"
            % (current_skill_points,)
        )
    if isinstance(character_level, bool) or not isinstance(
        character_level, int
    ):
        raise TypeError(
            "character_level must be an int, got %s"
            % type(character_level).__name__
        )
    if isinstance(skill_id, bool) or not isinstance(skill_id, int):
        raise TypeError(
            "skill_id must be an int, got %s" % type(skill_id).__name__
        )

    if not skill_context_census.is_declared(skill_id):
        return REFUSED_SKILL_NOT_DECLARED
    if not skill_context_census.meets_level_requirement(
        character_level, skill_id
    ):
        return REFUSED_LEVEL_TOO_LOW
    cost = skill_context_census.rank_one_point_cost(skill_id)
    if cost <= 0:
        # 1767 of the 2165 rows carry 0.0 here.  Reporting those learnable
        # for free is the failure `can_afford_to_learn` was already fixed
        # for once (pf-adversary, round `jbe8rr`/`7fqb46`); this is the same
        # refusal, kept identical on purpose.
        return REFUSED_COST_NOT_POSITIVE
    if current_skill_points < cost:
        return REFUSED_NOT_ENOUGH_POINTS
    return None


def skill_points_after_learning_declared(
    current_skill_points: int, character_level: int, skill_id: int
) -> int:
    """`skill_points_after_learning`, widened to every declared skill id.

    Same arithmetic, same `math.ceil` house rule (`COO-DECISION
    20260905_1245`), same refusal posture -- but the cost comes from
    `skill_context_census` (2165 rows) instead of `skill_catalog` (8), and
    the character's level is checked first through :func:`refusal_to_learn`.

    ONE DOOR, NOT TWO.  The census copy and the starting-kit copy are the
    same client table, and `skill_context_census` asserts at import that the
    kit rows are byte-identical in both; on top of that,
    `tests/test_skill_learn_validator.py` pins that this function returns
    exactly what `skill_points_after_learning` returns for every one of the
    8 kit ids at a level that clears their `n_LEVEL_LEARN`.  The older
    function is not deleted and not re-routed: callers that have no level to
    offer keep it, and it keeps refusing unknown ids with `KeyError`.

    Raises `SkillLearnValidatorError` naming the refusal (one of the four
    `REFUSED_*` strings) when :func:`refusal_to_learn` refuses -- including
    "not enough points", which this function cannot answer with a number.
    """
    refusal = refusal_to_learn(current_skill_points, character_level, skill_id)
    if refusal is not None:
        raise SkillLearnValidatorError(
            "cannot learn skill %r at level %r with %r skill points: %s"
            % (skill_id, character_level, current_skill_points, refusal)
        )
    cost = skill_context_census.rank_one_point_cost(skill_id)
    spend = cost if cost.is_integer() else math.ceil(cost)
    return current_skill_points - int(spend)
