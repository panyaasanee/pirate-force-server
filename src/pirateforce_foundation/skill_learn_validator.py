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
"""
from __future__ import annotations

import math

from . import skill_catalog


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
    beats guessing what a negative balance should mean.  Raises whatever
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
    return current_skill_points >= cost


def skill_points_after_learning(current_skill_points: int, skill_id: int) -> int:
    """The skill-point balance remaining after spending
    `skill_catalog.skill_point_cost_to_learn(skill_id)` from
    `current_skill_points` -- pure arithmetic, no database read, no
    database write, no grant.

    Raises the same errors `can_afford_to_learn` raises, for the same
    reasons, on the same inputs (`TypeError` for a non-`int`/`bool`
    balance, `SkillLearnValidatorError` for a negative balance, `KeyError`
    for an unknown `skill_id`).  Additionally raises
    `SkillLearnValidatorError` when `can_afford_to_learn(current_skill_points,
    skill_id)` would be `False` -- spending more than the balance holds is
    a caller bug this function refuses rather than returning a negative
    result -- and when `skill_id`'s cost is `<= 0` (a value this project's
    own tables have never carried; see the module docstring's
    `COO-DECISION 20260905_1245` paragraph).

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
    if cost <= 0:
        raise SkillLearnValidatorError(
            "skill_id %r costs %r skill points -- a non-positive cost is "
            "not a value this project's tables are expected to carry; "
            "refusing rather than granting it for free or spending a "
            "negative amount (COO-DECISION 20260905_1245)" % (skill_id, cost)
        )
    spend = cost if cost.is_integer() else math.ceil(cost)
    return current_skill_points - int(spend)
