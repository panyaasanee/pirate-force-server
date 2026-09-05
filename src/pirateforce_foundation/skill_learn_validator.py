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
* It does not spend or grant anything.  A `True` return means "the balance
  covers the cost", not "the skill was learned" -- deducting the cost and
  writing the granted skill id is a caller's job (a future learn-request
  hookup chief would grant, the same shape `persistence_starting_skills`
  already documents as pending for piece 5's other half).
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
"""
from __future__ import annotations

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
