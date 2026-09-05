"""LANE-CS: the skill-learn spend caller -- joins the pure balance check
(`skill_learn_validator`) to the persisted balance
(`store.SQLiteStore.get_skill_points`/`spend_skill_points`).

Where the project stops without this module
---------------------------------------------
`skill_learn_validator.py`'s own docstring names its posture explicitly: it
"does not WRITE anything" and "has no database connection, no store, no
wire, no socket" -- writing the deduction is a caller's job.  LANE-DB's
`store.py` (`pf_bridge/notes_to_chief/20260905_1739_LANE-DB-REPLY-skill-
points-store-doors-built-get-and-spend.md`) built that caller's read and
write half, `get_skill_points`/`spend_skill_points`, and named its own
nonclaim just as explicitly: "zero production caller ... `store.py` does not
know about `skill_catalog`/fractional cost at all" -- the two modules agree
on a boundary neither one crosses.  This module is the caller both sides
named as pending: it reads a character's persisted balance, asks
`skill_learn_validator` whether `skill_id` is affordable and what rounded
`cost` (`COO-DECISION 20260905_1245`'s `math.ceil` house rule) that costs,
then spends exactly that amount through `store.spend_skill_points`.

WHAT THIS MODULE DOES NOT DO.  It does not decide WHEN a player learns a
skill -- there is still no request handler (`runtime.py`, chief's write
zone) that calls this from a real client frame; `learn_skill_request_
hypothesis.py` proves a request WIRE SHAPE a real client could send but
does not call this function, and 0x36AA's own direction is unproven (see
that module's nonclaims).  It does not grant the skill itself (writing a
`character_skills` row) -- that is a separate write this module does not
attempt; spending points and granting a skill are two different
persisted facts, and conflating them here would silently assume an
answer neither `store.py` nor this round settles.  It does not retry or
re-check anything `spend_skill_points` itself already guards (schema
drift, SQLite integer range, the write-lock timeout) -- those errors
propagate unchanged.

ZERO PRODUCTION CALLER, same posture as everything it joins: nothing in
`runtime.py`/`session.py` calls this yet.
"""
from __future__ import annotations

from . import skill_learn_validator
from .store import SQLiteStore


def learn_skill_spend(
    store: SQLiteStore, character_id: int, skill_id: int
) -> int:
    """Spend `character_id`'s skill points to learn `skill_id`, returning
    the balance remaining after the deduction.

    Reads `store.get_skill_points(character_id)` for the current balance.
    Raises `KeyError` if the character does not exist or is soft-deleted --
    whatever `get_skill_points` itself raises for that, unchanged.

    Raises `skill_learn_validator.SkillLearnValidatorError` if the balance
    is `None` (unmeasured -- `COO-DECISION 20260901_1059` forbids guessing
    a NULL balance as `0` or unlimited, the same rule `store.
    spend_skill_points` enforces on its own NULL read one step later; this
    function refuses at the same point rather than letting an unmeasured
    balance reach `skill_learn_validator.can_afford_to_learn`, which
    requires a plain non-negative `int` and would raise `TypeError` on
    `None` instead of naming the real cause).

    Once a balance is in hand, computes the rounded amount to spend by
    calling `skill_learn_validator.skill_points_after_learning(current,
    skill_id)` and taking `current - after` -- rather than re-deriving
    `skill_catalog.skill_point_cost_to_learn` and its `math.ceil` rounding
    rule a second time in this module.  This inherits every refusal
    `skill_points_after_learning` already makes on the same inputs:
    `SkillLearnValidatorError` for a non-affordable balance or for a
    `skill_id` whose cost is `<= 0`, and `KeyError` for a `skill_id` outside
    the catalog.  Nothing is spent when any of those refuse.

    Finally calls `store.spend_skill_points(character_id, cost)` -- the
    only write in this function.  NOT ATOMIC ACROSS THE READ AND THE SPEND:
    `get_skill_points` and `spend_skill_points` are two separate
    connections, so a concurrent spend on the SAME character between this
    function's read and its call to `spend_skill_points` cannot corrupt
    data (`spend_skill_points`'s own `BEGIN IMMEDIATE` re-reads the balance
    inside its transaction) but CAN mean this function's own affordability
    check passes here and `spend_skill_points` still raises
    `InsufficientSkillPointsError` moments later -- a caller must catch
    that too, not treat a successful check from this function as a
    guarantee the spend below it will succeed.
    """
    current = store.get_skill_points(character_id)
    if current is None:
        raise skill_learn_validator.SkillLearnValidatorError(
            "character %r has no skill_points value yet (NULL) -- cannot "
            "learn a skill against an unmeasured balance "
            "(COO-DECISION 20260901_1059)" % (character_id,)
        )
    after = skill_learn_validator.skill_points_after_learning(
        current, skill_id
    )
    cost = current - after
    return store.spend_skill_points(character_id, cost)
