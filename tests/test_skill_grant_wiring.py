"""LANE-CS: `skill_grant_wiring.learn_and_grant_skill` -- the spend-then-
grant composer that closes the gap `skill_learn_wiring.learn_skill_spend`'s
own docstring names ("granting the skill itself ... is a separate write
this module does not attempt").

WHAT THIS FILE DOES NOT PROVE.  `grant_learned_skill` does not exist on
the real `store.SQLiteStore` yet (this round's CORE-REQUEST proposes it to
LANE-DB) -- every test here exercises the composer against `_FakeGrantStore`
below, a thin wrapper that delegates the real spend-side calls
(`get_skill_points`/`spend_skill_points`) to a real `store.SQLiteStore`
(migrated, same as `test_skill_learn_wiring.py`'s own fixture) and fakes
only the not-yet-real grant call. Nothing here is client-observable: same
zero-production-caller posture as `skill_learn_wiring.py` and
`skill_grant_wiring.py` themselves.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.skill_grant_wiring import (  # noqa: E402
    learn_and_grant_skill,
)
from pirateforce_foundation.skill_learn_validator import (  # noqa: E402
    SkillLearnValidatorError,
)
from pirateforce_foundation.store import (  # noqa: E402
    InsufficientSkillPointsError,
    SQLiteStore,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

#: Bumped per character so two rows never collide on
#: `UNIQUE(identity_lo, identity_hi)`, same idiom `test_skill_learn_wiring.py`
#: and `test_store_skill_points.py` use.
_next_identity = iter(range(0x30003000, 0x30004000))

#: Skill 99 ("Normal Attack") costs exactly 1.0 skill point
#: (`skill_catalog.skill_point_cost_to_learn(99) == 1.0`,
#: `tests/test_skill_learn_validator.py`).
_WHOLE_COST_SKILL_ID = 99

_GRANTED_AT = "2026-09-05T21:17:00+07:00"


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _FakeGrantStore:
    """Delegates the real spend-side calls to a real, migrated
    `store.SQLiteStore` unchanged; fakes only `grant_learned_skill`, the
    one call `SkillGrantStore` (`skill_grant_wiring.py`) names as not-yet-
    real. The fake dedups per `(character_id, skill_id)` the same way
    `migrations/011_character_skills.sql`'s `UNIQUE(character_id,
    skill_id)` + `INSERT OR IGNORE` does for the real (starting-kit-only,
    today) table -- this is the idempotency shape this round proposed
    LANE-DB build for a learned grant too.
    """

    def __init__(self, store: SQLiteStore):
        self._store = store
        self._granted: "dict[int, list[int]]" = {}
        self.grant_calls: "list[tuple[int, int, str]]" = []
        self._raise_on_grant: "Exception | None" = None

    def fail_next_grant(self, exc: Exception) -> None:
        self._raise_on_grant = exc

    def get_skill_points(self, character_id):
        return self._store.get_skill_points(character_id)

    def spend_skill_points(self, character_id, cost):
        return self._store.spend_skill_points(character_id, cost)

    def grant_learned_skill(self, character_id, skill_id, granted_at):
        self.grant_calls.append((character_id, skill_id, granted_at))
        if self._raise_on_grant is not None:
            exc, self._raise_on_grant = self._raise_on_grant, None
            raise exc
        existing = self._granted.setdefault(character_id, [])
        if skill_id not in existing:
            existing.append(skill_id)
        return tuple(existing)


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.fake = _FakeGrantStore(self.store)

    def _make_character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )


class LearnAndGrantSkillTests(_StoreFixture):
    def test_happy_path_spends_then_grants_and_returns_both(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        points_remaining, skills_after_grant = learn_and_grant_skill(
            self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
        )
        self.assertEqual(points_remaining, 4)
        self.assertEqual(skills_after_grant, (_WHOLE_COST_SKILL_ID,))
        self.assertEqual(self.store.get_skill_points(character.id), 4)
        self.assertEqual(
            self.fake.grant_calls,
            [(character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT)],
        )

    def test_insufficient_points_never_attempts_the_grant(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        with self.assertRaises(SkillLearnValidatorError):
            learn_and_grant_skill(
                self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
            )
        self.assertEqual(self.fake.grant_calls, [])
        # Refusing must not have spent anything either.
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def test_unknown_skill_id_raises_key_error_and_never_grants(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 99})
        with self.assertRaises(KeyError):
            learn_and_grant_skill(self.fake, character.id, 424242, _GRANTED_AT)
        self.assertEqual(self.fake.grant_calls, [])
        self.assertEqual(self.store.get_skill_points(character.id), 99)

    def test_toctou_insufficient_from_the_store_also_never_grants(self):
        # Same race learn_skill_spend's own test suite documents: a
        # concurrent drain between the read and the spend surfaces as
        # InsufficientSkillPointsError, not SkillLearnValidatorError --
        # the grant must still never run.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 1})
        real_get_skill_points = self.store.get_skill_points

        def draining_get_skill_points(character_id):
            balance = real_get_skill_points(character_id)
            self.store.spend_skill_points(character_id, balance)
            return balance

        with mock.patch.object(
            self.store,
            "get_skill_points",
            side_effect=draining_get_skill_points,
        ):
            with self.assertRaises(InsufficientSkillPointsError):
                learn_and_grant_skill(
                    self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
                )
        self.assertEqual(self.fake.grant_calls, [])
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def test_regranting_the_same_skill_dedups_on_the_grant_side_only(self):
        # Idempotency lives in grant_learned_skill's own contract (mirrors
        # migrations/011_character_skills.sql's UNIQUE(character_id,
        # skill_id) + INSERT OR IGNORE), NOT in learn_and_grant_skill --
        # this composer has no memory of what was already granted, so a
        # second full call still spends a second time even though the
        # grant itself dedups. This is intentional: whether "already
        # learned" should block a second SPEND is a design question for
        # whatever caller/handler decides when a learn request fires, not
        # something this composer silently assumes.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        first_points, first_skills = learn_and_grant_skill(
            self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
        )
        second_points, second_skills = learn_and_grant_skill(
            self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
        )
        self.assertEqual(first_points, 4)
        self.assertEqual(second_points, 3)  # spent again -- not deduped
        self.assertEqual(first_skills, (_WHOLE_COST_SKILL_ID,))
        self.assertEqual(second_skills, (_WHOLE_COST_SKILL_ID,))  # deduped
        self.assertEqual(len(self.fake.grant_calls), 2)

    def test_spend_succeeded_but_grant_raised_propagates_not_swallowed(self):
        # The documented non-atomicity gap: the spend already committed by
        # the time grant_learned_skill raises, and this function does not
        # catch, translate, or refund it -- the caller sees the real
        # exception and must handle the inconsistent state itself.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        self.fake.fail_next_grant(RuntimeError("grant_learned_skill boom"))
        with self.assertRaises(RuntimeError):
            learn_and_grant_skill(
                self.fake, character.id, _WHOLE_COST_SKILL_ID, _GRANTED_AT
            )
        # The spend is NOT rolled back -- this is the gap, not a bug in
        # this test's expectation.
        self.assertEqual(self.store.get_skill_points(character.id), 4)
        self.assertEqual(len(self.fake.grant_calls), 1)


if __name__ == "__main__":
    unittest.main()
