"""LANE-CS: `skill_grant_wiring.learn_and_grant_skill` -- the spend-then-
grant composer that closes the gap `skill_learn_wiring.learn_skill_spend`'s
own docstring names ("granting the skill itself ... is a separate write
this module does not attempt").

`store.SQLiteStore.grant_learned_skill` is now real, landed on `main` in
`pirate-force-server#863` -- `LearnAndGrantSkillTests` below still runs
the composer against `_FakeGrantStore` (useful for exercising a mid-grant
failure without needing the real method to cooperate), and
`LearnAndGrantSkillAgainstRealStoreTests` runs the identical scenarios
straight against `store.SQLiteStore` with zero code changes to
`skill_grant_wiring.py` -- the module's `SkillGrantStore` Protocol already
matched the real method's arity (fixed in `pirate-force-server#866`),
proving the composer and the concrete store door actually fit together,
not just that a fake shaped like one does. Nothing here is
client-observable: same zero-production-caller posture as
`skill_learn_wiring.py` and `skill_grant_wiring.py` themselves -- there is
still no `runtime.py` request handler calling this from a real client
frame.
"""
from __future__ import annotations

import sqlite3
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


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _FakeGrantStore:
    """Delegates the real spend-side calls to a real, migrated
    `store.SQLiteStore` unchanged; fakes only `grant_learned_skill` -- kept
    even though the real method now exists on `main`, so tests that need
    to inject a mid-grant failure
    (`test_spend_succeeded_but_grant_raised_propagates_not_swallowed`)
    still can without depending on the real method cooperating. The fake
    dedups per `(character_id, skill_id)` the same way
    `migrations/014_character_skills_learned_source.sql`'s shared
    `UNIQUE(character_id, skill_id)` + `INSERT OR IGNORE` does for the
    real table -- the same idempotency shape the real
    `grant_learned_skill` actually ships, verified directly in
    `LearnAndGrantSkillAgainstRealStoreTests` below.
    """

    def __init__(self, store: SQLiteStore):
        self._store = store
        self._granted: "dict[int, list[int]]" = {}
        self.grant_calls: "list[tuple[int, int]]" = []
        self._raise_on_grant: "Exception | None" = None

    def fail_next_grant(self, exc: Exception) -> None:
        self._raise_on_grant = exc

    def get_skill_points(self, character_id):
        return self._store.get_skill_points(character_id)

    def spend_skill_points(self, character_id, cost):
        return self._store.spend_skill_points(character_id, cost)

    def grant_learned_skill(self, character_id, skill_id):
        self.grant_calls.append((character_id, skill_id))
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
            self.fake, character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(points_remaining, 4)
        self.assertEqual(skills_after_grant, (_WHOLE_COST_SKILL_ID,))
        self.assertEqual(self.store.get_skill_points(character.id), 4)
        self.assertEqual(
            self.fake.grant_calls,
            [(character.id, _WHOLE_COST_SKILL_ID)],
        )

    def test_insufficient_points_never_attempts_the_grant(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        with self.assertRaises(SkillLearnValidatorError):
            learn_and_grant_skill(
                self.fake, character.id, _WHOLE_COST_SKILL_ID
            )
        self.assertEqual(self.fake.grant_calls, [])
        # Refusing must not have spent anything either.
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def test_unknown_skill_id_raises_key_error_and_never_grants(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 99})
        with self.assertRaises(KeyError):
            learn_and_grant_skill(self.fake, character.id, 424242)
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
                    self.fake, character.id, _WHOLE_COST_SKILL_ID
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
            self.fake, character.id, _WHOLE_COST_SKILL_ID
        )
        second_points, second_skills = learn_and_grant_skill(
            self.fake, character.id, _WHOLE_COST_SKILL_ID
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
                self.fake, character.id, _WHOLE_COST_SKILL_ID
            )
        # The spend is NOT rolled back -- this is the gap, not a bug in
        # this test's expectation.
        self.assertEqual(self.store.get_skill_points(character.id), 4)
        self.assertEqual(len(self.fake.grant_calls), 1)


class LearnAndGrantSkillAgainstRealStoreTests(_StoreFixture):
    """Same composer, same scenarios as `LearnAndGrantSkillTests`, but
    `store=self.store` throughout -- the real `store.SQLiteStore`, no
    `_FakeGrantStore` involved anywhere. This is the check that actually
    matters now that `grant_learned_skill` is real: `SkillGrantStore`
    (a `typing.Protocol`) type-checks structurally, so nothing before this
    file ever confirmed the real method's arity and return shape truly
    line up with what `learn_and_grant_skill` calls -- only that a fake
    written to the Protocol's declared shape does.
    """

    def _source_of(self, character_id, skill_id):
        # Reads the persisted `character_skills.source` value directly
        # with a second connection to the same on-disk file `self.store`
        # already migrated -- independent of anything `store.py` computes
        # in memory, the same second-connection-reads-the-file discipline
        # `test_skill_learn_wiring.py` and `test_store_skill_points.py`
        # both use to cross-check a write door's claim.
        conn = sqlite3.connect(self.path)
        try:
            row = conn.execute(
                "SELECT source FROM character_skills"
                " WHERE character_id = ? AND skill_id = ?",
                (character_id, skill_id),
            ).fetchone()
        finally:
            conn.close()
        return row[0] if row is not None else None

    def test_happy_path_against_real_store_grants_source_learned(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        points_remaining, skills_after_grant = learn_and_grant_skill(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(points_remaining, 4)
        self.assertEqual(skills_after_grant, (_WHOLE_COST_SKILL_ID,))
        self.assertEqual(self.store.get_skill_points(character.id), 4)
        self.assertEqual(
            self._source_of(character.id, _WHOLE_COST_SKILL_ID), "learned"
        )

    def test_grant_survives_a_reopened_store_real_persistence(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        learn_and_grant_skill(self.store, character.id, _WHOLE_COST_SKILL_ID)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reopened.get_skill_points(character.id), 4
        )
        self.assertEqual(
            self._source_of(character.id, _WHOLE_COST_SKILL_ID), "learned"
        )

    def test_insufficient_points_never_attempts_the_grant_real_store(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        with self.assertRaises(SkillLearnValidatorError):
            learn_and_grant_skill(
                self.store, character.id, _WHOLE_COST_SKILL_ID
            )
        self.assertIsNone(
            self._source_of(character.id, _WHOLE_COST_SKILL_ID)
        )
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def _row_identity_of(self, character_id, skill_id):
        # (id, granted_at) of the one row for this (character_id, skill_id)
        # pair -- used to prove a repeat grant is a true no-op (`INSERT OR
        # IGNORE`) and not a delete-and-reinsert (`INSERT OR REPLACE`),
        # which would change both. `grant_starting_skills`'s own docstring
        # (store.py) names row-identity/timestamp corruption on a
        # reordered regrant as the specific failure mode a shared
        # UNIQUE(character_id, skill_id) door must not produce, and
        # `tests/test_persistence_character_skills_011.py` has a
        # dedicated regression test for that door -- this is the same
        # check for `grant_learned_skill`.
        conn = sqlite3.connect(self.path)
        try:
            return conn.execute(
                "SELECT id, granted_at FROM character_skills"
                " WHERE character_id = ? AND skill_id = ?",
                (character_id, skill_id),
            ).fetchone()
        finally:
            conn.close()

    def test_regranting_dedups_on_the_real_grant_door_only(self):
        # Same non-dedup-on-spend behavior as the fake-backed test above,
        # but this time `grant_learned_skill`'s own `INSERT OR IGNORE`
        # (not the fake's dict) is what has to actually dedup.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        first_points, first_skills = learn_and_grant_skill(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        row_after_first = self._row_identity_of(
            character.id, _WHOLE_COST_SKILL_ID
        )
        second_points, second_skills = learn_and_grant_skill(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        row_after_second = self._row_identity_of(
            character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(first_points, 4)
        self.assertEqual(second_points, 3)  # spent again -- not deduped
        self.assertEqual(first_skills, (_WHOLE_COST_SKILL_ID,))
        self.assertEqual(second_skills, (_WHOLE_COST_SKILL_ID,))  # deduped
        # Row identity AND its granted_at timestamp must survive the
        # repeat grant untouched -- an `INSERT OR REPLACE` regression
        # would still pass a row-count-only check (still one row) while
        # silently changing both of these.
        self.assertEqual(
            row_after_first, row_after_second,
            "a repeat grant must be a true no-op (same id, same "
            "granted_at), not a delete-and-reinsert",
        )
        conn = sqlite3.connect(self.path)
        try:
            (row_count,) = conn.execute(
                "SELECT COUNT(*) FROM character_skills"
                " WHERE character_id = ? AND skill_id = ?",
                (character.id, _WHOLE_COST_SKILL_ID),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row_count, 1)  # one row, not two

    def test_unknown_skill_id_raises_key_error_real_store(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 99})
        with self.assertRaises(KeyError):
            learn_and_grant_skill(self.store, character.id, 424242)
        self.assertIsNone(self._source_of(character.id, 424242))
        self.assertEqual(self.store.get_skill_points(character.id), 99)


if __name__ == "__main__":
    unittest.main()
