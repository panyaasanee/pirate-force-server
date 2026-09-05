"""LANE-CS: `skill_learn_wiring.learn_skill_spend` -- the caller that joins
`skill_learn_validator` (pure balance check) to `store.SQLiteStore`'s
`get_skill_points`/`spend_skill_points` (`pf_bridge/notes_to_chief/
20260905_1844_COO-DECISION-cs1814-received-db1739-already-answered-store-
hookup-consume-it-825-fix-pr-gate-verified-by-2036-LANE-CS.md`).

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: there is
still no request handler (`runtime.py`) calling `learn_skill_spend` from a
real client frame, same zero-production-caller posture `skill_learn_
validator.py` and `store.py`'s own skill-points tests both state.
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
from pirateforce_foundation.skill_learn_validator import (  # noqa: E402
    SkillLearnValidatorError,
)
from pirateforce_foundation.skill_learn_wiring import (  # noqa: E402
    learn_skill_spend,
)
from pirateforce_foundation.store import (  # noqa: E402
    InsufficientSkillPointsError,
    SQLiteStore,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

#: Bumped per character so two rows never collide on
#: `UNIQUE(identity_lo, identity_hi)`, same idiom `test_store_skill_points.py`
#: uses.
_next_identity = iter(range(0x30002000, 0x30003000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


#: Skill 99 ("Normal Attack") costs exactly 1.0 skill point
#: (`skill_catalog.skill_point_cost_to_learn(99) == 1.0`,
#: `tests/test_skill_learn_validator.py`).
_WHOLE_COST_SKILL_ID = 99

#: Skill 111 ("VIP Strive Jump") costs a fractional amount
#: (`< 1.0`, `COO-DECISION 20260905_1245`'s `math.ceil` house rule spends 1
#: point for it -- `tests/test_skill_learn_validator.py`).
_FRACTIONAL_COST_SKILL_ID = 111


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _make_character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )


class LearnSkillSpendTests(_StoreFixture):
    def test_spends_a_whole_cost_skill_and_returns_new_balance(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        remaining = learn_skill_spend(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(remaining, 4)
        self.assertEqual(self.store.get_skill_points(character.id), 4)

    def test_fractional_cost_spends_the_ceiling_not_the_raw_float(self):
        # id 111 costs < 1.0 -- COO-DECISION 20260905_1245 rounds the spend
        # up to 1, never floors to 0 and never leaves a fractional balance.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 3})
        remaining = learn_skill_spend(
            self.store, character.id, _FRACTIONAL_COST_SKILL_ID
        )
        self.assertEqual(remaining, 2)
        self.assertIsInstance(remaining, int)

    def test_unmeasured_balance_refuses_before_any_write(self):
        character = self._make_character()
        with self.assertRaises(SkillLearnValidatorError):
            learn_skill_spend(self.store, character.id, _WHOLE_COST_SKILL_ID)
        # Refusing must not have written anything -- still NULL, not 0.
        self.assertIsNone(self.store.get_skill_points(character.id))

    def test_insufficient_balance_refuses_before_any_write(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        with self.assertRaises(SkillLearnValidatorError):
            learn_skill_spend(self.store, character.id, _WHOLE_COST_SKILL_ID)
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def test_unknown_skill_id_raises_key_error_not_reported_unaffordable(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 99})
        with self.assertRaises(KeyError):
            learn_skill_spend(self.store, character.id, 424242)
        # A refused, unknown skill must not have spent anything.
        self.assertEqual(self.store.get_skill_points(character.id), 99)

    def test_unknown_character_raises_key_error(self):
        with self.assertRaises(KeyError):
            learn_skill_spend(self.store, 999999, _WHOLE_COST_SKILL_ID)

    def test_a_second_spend_after_the_first_reads_the_updated_balance(self):
        # Not a concurrency test (see the module docstring's TOCTOU
        # nonclaim) -- just confirms two sequential calls compose correctly
        # through the same store.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 10})
        first = learn_skill_spend(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        second = learn_skill_spend(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(first, 9)
        self.assertEqual(second, 8)

    def test_spending_exactly_the_last_point_reaches_zero(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 1})
        remaining = learn_skill_spend(
            self.store, character.id, _WHOLE_COST_SKILL_ID
        )
        self.assertEqual(remaining, 0)

    def test_insufficient_error_type_is_the_store_one_not_the_validator_one(self):
        # A balance too low to afford EITHER cost check
        # (can_afford_to_learn) refuses with SkillLearnValidatorError before
        # store.spend_skill_points is ever called -- InsufficientSkillPoints
        # Error is store.py's own, reachable only if a caller bypassed the
        # validator (not exercised by this wiring function, documented so a
        # caller of learn_skill_spend does not need to catch it).
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        try:
            learn_skill_spend(self.store, character.id, _WHOLE_COST_SKILL_ID)
        except InsufficientSkillPointsError:
            self.fail(
                "learn_skill_spend must refuse via SkillLearnValidatorError "
                "before store.spend_skill_points ever runs"
            )
        except SkillLearnValidatorError:
            pass

    def test_toctou_concurrent_spend_between_read_and_write_is_caught(self):
        # [pf-adversary, this round] verified this race live with real
        # threads and flagged that this file did not itself exercise it --
        # this closes that gap.  A concurrent spend drains the balance to 0
        # in the gap between learn_skill_spend's own read
        # (get_skill_points) and its write (spend_skill_points); the
        # affordability check above that gap cannot see it, so the refusal
        # must come from spend_skill_points's own re-read inside its
        # `BEGIN IMMEDIATE` transaction, as InsufficientSkillPointsError --
        # not a crash, not a silent bad write, not
        # SkillLearnValidatorError (this function does not catch or
        # translate it).
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
                learn_skill_spend(
                    self.store, character.id, _WHOLE_COST_SKILL_ID
                )
        # The concurrent drain is the only spend that took effect.
        self.assertEqual(self.store.get_skill_points(character.id), 0)


if __name__ == "__main__":
    unittest.main()
