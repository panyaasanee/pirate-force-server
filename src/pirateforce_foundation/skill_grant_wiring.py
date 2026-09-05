"""LANE-CS: the spend-then-grant composer for a LEARNED skill -- joins
`skill_learn_wiring.learn_skill_spend` (real, on `main`, spends skill
points) to a store method this module does NOT assume exists yet.

WHY THIS MODULE EXISTS.  `skill_learn_wiring.py`'s own docstring names its
boundary explicitly: "It does not grant the skill itself (writing a
`character_skills` row) -- that is a separate write this module does not
attempt; spending points and granting a skill are two different persisted
facts, and conflating them here would silently assume an answer neither
`store.py` nor this round settles."  `migrations/011_character_skills.sql`
backs that up on the schema side: `source TEXT NOT NULL CHECK(source IN
('starting_kit'))` -- the CHECK list has exactly one value today, and a
LEARNED grant needs a second one LANE-DB has not added yet (see this
round's CORE-REQUEST to LANE-DB, `pf_bridge/notes_to_chief/`, proposing a
`'learned'` value and a `grant_learned_skill` store method). `store.py`
and `migrations/` are LANE-DB's exclusive write zone (`AGENTS.md` section 7 /
`prompts/LANE-CS.md`); this lane proposes, LANE-DB decides and builds.

HOW THIS MODULE STAYS TESTABLE BEFORE THAT METHOD EXISTS.  `SkillGrantStore`
below is a minimal `typing.Protocol` naming only the one not-yet-real call
this module needs (`grant_learned_skill`) plus the two calls
`skill_learn_wiring.learn_skill_spend` already requires
(`get_skill_points`/`spend_skill_points`, inherited from `store.
SQLiteStore` via duck typing -- this module does not re-declare them).  A
fake implementing `SkillGrantStore` exercises every branch below today
(`tests/test_skill_grant_wiring.py`); the real `store.SQLiteStore` already
satisfies the two spend-side methods, so the only thing standing between
this module and a real caller is LANE-DB shipping the third method with a
matching name and signature -- no import of `store.SQLiteStore` needed
here beyond what `skill_learn_wiring` itself already imports.

WHAT THIS MODULE DOES NOT DO.

* It does not decide WHEN a player learns a skill.  Same zero-caller
  posture as `skill_learn_wiring.learn_skill_spend` itself: there is no
  request handler (`runtime.py`, chief's write zone) calling this from a
  real client frame.  `runtime.py` is explicitly OUT OF SCOPE for this
  module and this round (`COO-DECISION 20260905_2053` item 3: the
  `learn_skill_spend` -> `runtime.py` hookup is its own CORE-REQUEST,
  deferred to a future round).
* It is NOT ATOMIC ACROSS THE SPEND AND THE GRANT.  `learn_skill_spend`
  and `grant_learned_skill` are two separate store calls (two separate
  SQLite transactions, same as `skill_learn_wiring.learn_skill_spend`'s
  own read-then-spend is two separate connections/transactions).  If the
  grant call raises AFTER the spend already committed, the caller has
  spent a skill point with nothing to show for it -- this module does
  NOT catch that and roll the spend back (there is nothing to roll back
  to without a compensating store call this module also does not have),
  and does NOT swallow the grant's exception -- it propagates unchanged,
  so a caller sees the inconsistent state rather than a false success.
  Closing this gap for real needs either a single cross-table transaction
  in `store.py` (LANE-DB's design, not proposed here) or an explicit
  compensating "refund" call this round does not build. This is a real,
  documented gap, not a paper-over.
* It does not validate or re-derive anything `learn_skill_spend` or
  `skill_learn_validator` already validate -- every refusal those two
  raise (`KeyError` for an unknown character or skill id,
  `skill_learn_validator.SkillLearnValidatorError` for an unmeasured or
  insufficient balance, `store.InsufficientSkillPointsError` for the
  TOCTOU race `learn_skill_spend`'s own docstring names) propagates
  unchanged, and in every one of those cases `grant_learned_skill` is
  never called -- the grant only runs after the spend has actually
  returned a balance.
* It does not decide the `source` column's value or the store method's
  final name/signature -- `_GRANT_SOURCE` documents what this round
  proposed to LANE-DB; the real value ships in whatever migration and
  store method LANE-DB actually builds, which may differ from the
  proposal.

ZERO PRODUCTION CALLER, same posture as everything it composes.
"""
from __future__ import annotations

from typing import Protocol

from . import skill_learn_wiring


class SkillGrantStore(Protocol):
    """The one not-yet-real store call this module needs, named as a
    `Protocol` rather than imported from `store.py` so this module can be
    fully exercised by a fake today.  `skill_learn_wiring.learn_skill_spend`
    already requires `get_skill_points`/`spend_skill_points` on whatever
    object is passed as `store` -- those are not re-declared here, this
    Protocol only adds the third call `learn_and_grant_skill` below needs.

    Shape LANE-DB decided (`pf_bridge/notes_to_chief/
    20260905_2228_LANE-DB-REPLY-grant_learned_skill-shape-decided-no-
    granted_at-param.md`, replying to this round's CORE-REQUEST `2119`):
    same `INSERT OR IGNORE` idempotency shape as `store.
    SQLiteStore.grant_starting_skills`, scoped to a single skill id and a
    `source` value other than `'starting_kit'` -- with ONE difference from
    what this lane proposed: `granted_at` is NOT a parameter.  The real
    method computes it itself with `_now()` inside its own transaction
    (identical to `grant_starting_skills`), because a caller-supplied
    timestamp can be stale or wrong and the method's own transaction is the
    only place that actually knows when the `INSERT` happened.
    """

    def grant_learned_skill(
        self, character_id: int, skill_id: int
    ) -> "tuple[int, ...]":
        ...


#: What this round proposed to LANE-DB as the new `character_skills.source`
#: CHECK value for a learned (non-starting-kit) grant. Documentation only --
#: this module never writes to `character_skills` itself, `grant_learned_
#: skill` does, so the real value is whatever LANE-DB's migration commits.
_GRANT_SOURCE = "learned"


def learn_and_grant_skill(
    store: SkillGrantStore, character_id: int, skill_id: int
) -> "tuple[int, tuple[int, ...]]":
    """Spend `character_id`'s skill points to learn `skill_id`, then grant
    it, returning `(points_remaining, skills_after_grant)`.

    Two sequential store calls, in this order:

    1. `skill_learn_wiring.learn_skill_spend(store, character_id, skill_id)`
       -- reads the current balance, validates affordability (rounding a
       fractional cost up per `COO-DECISION 20260905_1245`), and spends it.
       Every refusal this raises (`KeyError` for an unknown character or
       skill id, `skill_learn_validator.SkillLearnValidatorError` for an
       unmeasured/insufficient balance, `store.
       InsufficientSkillPointsError` for a concurrent-drain TOCTOU) is
       raised BEFORE this function reaches step 2 -- `grant_learned_skill`
       is never called when the spend itself refuses.

    2. `store.grant_learned_skill(character_id, skill_id)` -- the write
       this module exists to add on top of `learn_skill_spend`. No
       `granted_at` argument: LANE-DB's reply (see `SkillGrantStore`)
       decided the real method computes its own timestamp internally, so
       this composer does not accept or forward one either. Whatever this
       raises (schema error, anything else) propagates UNCHANGED and
       UNCAUGHT -- see the module docstring's non-atomicity nonclaim: the
       points spent in step 1 are NOT refunded when step 2 raises. A
       caller observing this function raise after a prior successful call
       must treat the character's skill-point balance as already
       decremented even though the grant did not land.

    Returns `(points_remaining, skills_after_grant)`:
    `points_remaining` is step 1's return value (the balance right after
    the spend); `skills_after_grant` is step 2's return value (every
    distinct skill id now on the character's row, per `grant_learned_
    skill`'s own idempotency contract -- see `SkillGrantStore`).
    """
    points_remaining = skill_learn_wiring.learn_skill_spend(
        store, character_id, skill_id
    )
    skills_after_grant = store.grant_learned_skill(character_id, skill_id)
    return points_remaining, skills_after_grant
