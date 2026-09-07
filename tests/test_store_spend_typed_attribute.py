"""LANE-DB: the atomic `characters` typed-attribute SPEND door.

`LANE-Q pf_bridge/notes_to_chief/20260907_1942_LANE-Q-TO-DB-add-typed-
attribute-needs-a-spend-door.md`.  Round `i7ihga` shipped the ADD door and
LANE-Q wired `Player.AddExp`/`Player.AddSkillPoint` to it; they left
`Player.AddCash` STUBBED on purpose, because two shipped quest scripts pay
money OUT -- `gamedata/lua/Quest/q_ship.lua:50` (`Player.AddCash(
-Quest.Var3)`) and `q_boat_health.lua:21` (`Player.AddCash(Quest.Var2 *
-1)`) -- and opening only the adding half would hand the player a free
ship.  This file measures `SQLiteStore.spend_typed_attribute`, the method
that answers that letter, contract for contract.

WHAT THIS FILE DOES AND DOES NOT PROVE.  It proves the row on disk moves
DOWN by exactly the magnitude asked for, that an overdraft is refused with
a type nobody else raises, and that two connections spending the same
column cannot lose a spend.  It does NOT prove anything client-observable:
no frame goes out because of this method, and a player will not see cash
move until LANE-Q's `lua_api/reward.pay()` calls it from a real quest
completion -- their half, named as theirs in their own letter.

THE CONTRACT A CALLER CANNOT SEE is atomicity, exactly as for the ADD
door: a body that read the balance on one connection and wrote it back on
another would satisfy every `callable(getattr(...))` check LANE-Q can
make, and silently lose a concurrent spend.
`test_two_spenders_racing_the_same_column_both_land` is that contract
measured HERE, with two real connections, because it cannot be measured
there.

THE CONTRACT A CALLER CAN SEE BUT MUST NOT CONFUSE is the refusal type.
LANE-Q asked for a name different from the ADD door's, so that catching
the wrong one cannot read "not paid" as "paid";
`test_an_overdraft_is_not_the_skill_points_refusal` is that, measured
against `spend_skill_points`' own type rather than asserted in prose.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.persistence_typed_attrs import (  # noqa: E402
    TYPED_COLUMNS,
    TypedAttrError,
)
from pirateforce_foundation.store import (  # noqa: E402
    InsufficientSkillPointsError,
    InsufficientTypedAttributeError,
    SQLiteStore,
    UnmeasuredTypedAttributeError,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

_next_identity = iter(range(0x33000001, 0x33001000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


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

    def _with(self, column, value, login="acct01", name="Test01"):
        character = self._make_character(login, name)
        self.store.write_typed_attributes(character.id, {column: value})
        return character


class SpendTypedAttributeTests(_StoreFixture):
    def test_returns_the_balance_after_the_subtraction(self):
        """Contract 4.  The number returned is read back inside the same
        transaction, so it is the row's value and not the method's own
        arithmetic."""
        character = self._with("cash", 5000)
        self.assertEqual(
            self.store.spend_typed_attribute(character.id, "cash", 1200), 3800
        )
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"], 3800
        )

    def test_the_whole_balance_can_be_spent_down_to_zero(self):
        """The floor is a floor, not a fence one short of it: a quest that
        costs exactly what the player has is payable."""
        character = self._with("cash", 750)
        self.assertEqual(
            self.store.spend_typed_attribute(character.id, "cash", 750), 0
        )

    def test_an_overdraft_is_refused_and_the_row_does_not_move(self):
        """Contract 3.  Not clamped to zero, not stored negative: the
        balance is exactly what it was before the call."""
        character = self._with("cash", 100)
        with self.assertRaises(InsufficientTypedAttributeError) as caught:
            self.store.spend_typed_attribute(character.id, "cash", 101)
        message = str(caught.exception)
        self.assertIn("cash", message)
        self.assertIn("100", message)
        self.assertIn("101", message)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"], 100
        )

    def test_an_overdraft_is_not_the_skill_points_refusal(self):
        """The separation LANE-Q asked for by name.  A caller that catches
        `InsufficientSkillPointsError` around this door must NOT swallow an
        overdraft, or it decides an unpaid quest was paid."""
        self.assertFalse(
            issubclass(
                InsufficientTypedAttributeError, InsufficientSkillPointsError
            )
        )
        self.assertFalse(
            issubclass(
                InsufficientSkillPointsError, InsufficientTypedAttributeError
            )
        )
        character = self._with("cash", 1)
        with self.assertRaises(InsufficientTypedAttributeError):
            try:
                self.store.spend_typed_attribute(character.id, "cash", 2)
            except InsufficientSkillPointsError as wrong:  # pragma: no cover
                raise AssertionError(
                    "the spend door raised the skill-points refusal: "
                    f"{wrong!r}"
                ) from wrong

    def test_a_null_column_is_refused_by_name_not_treated_as_zero(self):
        """Contract 2.  `read_typed_attributes` DROPS a NULL column, so a
        caller doing its own arithmetic would spend against a balance
        nobody ever measured (`COO-DECISION 20260901_1059`)."""
        character = self._make_character()
        self.assertNotIn("cash", self.store.read_typed_attributes(character.id))
        with self.assertRaises(UnmeasuredTypedAttributeError) as caught:
            self.store.spend_typed_attribute(character.id, "cash", 1)
        self.assertIn("cash", str(caught.exception))

    def test_a_null_column_is_not_reported_as_an_overdraft(self):
        """The two refusals answer different questions -- "nobody measured
        this" versus "you cannot afford this" -- and a caller that cannot
        tell them apart cannot tell a broken row from a poor player."""
        character = self._make_character()
        with self.assertRaises(UnmeasuredTypedAttributeError):
            self.store.spend_typed_attribute(character.id, "cash", 1)
        self.assertNotIsInstance(
            UnmeasuredTypedAttributeError("x"), InsufficientTypedAttributeError
        )

    def test_a_zero_amount_writes_the_same_value_back(self):
        character = self._with("cash", 42)
        self.assertEqual(
            self.store.spend_typed_attribute(character.id, "cash", 0), 42
        )

    def test_a_zero_balance_is_a_measured_value_and_refuses_a_real_spend(self):
        """A measured 0 is not a NULL: it reaches the floor rule, not the
        unmeasured rule."""
        character = self._with("cash", 0)
        self.assertEqual(
            self.store.spend_typed_attribute(character.id, "cash", 0), 0
        )
        with self.assertRaises(InsufficientTypedAttributeError):
            self.store.spend_typed_attribute(character.id, "cash", 1)

    def test_a_negative_amount_is_refused_the_sign_is_in_the_name(self):
        """A caller that flips a sign by accident must get a `ValueError`,
        not a silent addition through the subtracting door."""
        character = self._with("cash", 10)
        with self.assertRaises(ValueError) as caught:
            self.store.spend_typed_attribute(character.id, "cash", -5)
        self.assertIn("magnitude", str(caught.exception))
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"], 10
        )

    def test_the_column_must_come_from_the_typed_column_table(self):
        character = self._with("cash", 10)
        for column in ("id", "name", "cash; DROP TABLE characters", "deleted_at"):
            with self.subTest(column=column):
                with self.assertRaises(TypedAttrError):
                    self.store.spend_typed_attribute(character.id, column, 1)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"], 10
        )

    def test_every_column_lane_q_can_send_is_actually_spendable(self):
        """Derived from `reward.KIND_COLUMN` rather than a hand-typed list,
        so a fourth reward kind upstream cannot quietly arrive unspendable.
        """
        from pirateforce_foundation.lua_api import reward

        for column in sorted(set(reward.KIND_COLUMN.values())):
            with self.subTest(column=column):
                self.assertIn(column, TYPED_COLUMNS)
                character = self._with(
                    column, 10, login="acct-" + column, name="C" + column[:6]
                )
                self.assertEqual(
                    self.store.spend_typed_attribute(character.id, column, 4),
                    6,
                )

    def test_bools_are_not_ints_here(self):
        character = self._with("cash", 10)
        with self.assertRaises(TypeError):
            self.store.spend_typed_attribute(True, "cash", 1)
        with self.assertRaises(TypeError):
            self.store.spend_typed_attribute(character.id, "cash", True)

    def test_a_non_str_column_is_a_type_error(self):
        character = self._with("cash", 10)
        with self.assertRaises(TypeError):
            self.store.spend_typed_attribute(character.id, 3, 1)

    def test_ids_and_amounts_past_sqlite_int64_are_refused(self):
        character = self._with("cash", 10)
        with self.assertRaises(ValueError):
            self.store.spend_typed_attribute(character.id, "cash", 2 ** 63)
        with self.assertRaises(KeyError):
            self.store.spend_typed_attribute(2 ** 63, "cash", 1)

    def test_unknown_and_soft_deleted_characters_are_key_errors(self):
        with self.assertRaises(KeyError):
            self.store.spend_typed_attribute(999999, "cash", 1)
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03", _build_wire, _HOME,
        )
        self.store.write_typed_attributes(character.id, {"cash": 5})
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.spend_typed_attribute(character.id, "cash", 1)


class SpendAtomicityTests(_StoreFixture):
    """The one contract LANE-Q cannot check from their side."""

    SPENDERS = 4
    SPENDS_PER_SPENDER = 40

    def test_two_spenders_racing_the_same_column_both_land(self):
        """Every spender opens its own `SQLiteStore` on the same file, so
        the only thing serialising them is `BEGIN IMMEDIATE` inside the
        method.  A read-modify-write body would leave the balance ABOVE the
        expected floor with nothing raised anywhere.
        """
        total = self.SPENDERS * self.SPENDS_PER_SPENDER
        character = self._with("cash", total)
        start = threading.Barrier(self.SPENDERS)
        errors: list[BaseException] = []

        def spender():
            store = SQLiteStore(self.path, MIGRATIONS)
            try:
                start.wait(timeout=30)
                for _ in range(self.SPENDS_PER_SPENDER):
                    store.spend_typed_attribute(character.id, "cash", 1)
            except BaseException as error:  # noqa: BLE001 - reported below
                errors.append(error)

        threads = [threading.Thread(target=spender) for _ in range(self.SPENDERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual([repr(e) for e in errors], [])
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"],
            0,
            "a concurrent spend was lost -- this door is not atomic",
        )

    def test_the_floor_holds_under_the_same_race(self):
        """The overdraft rule is not a check the race can step around: with
        one unit LESS in the row than the spenders together ask for,
        EXACTLY one spend must be refused and the balance must land on 0,
        never on -1.
        """
        total = self.SPENDERS * self.SPENDS_PER_SPENDER
        character = self._with("cash", total - 1)
        start = threading.Barrier(self.SPENDERS)
        refused: list[BaseException] = []
        other: list[BaseException] = []

        def spender():
            store = SQLiteStore(self.path, MIGRATIONS)
            try:
                start.wait(timeout=30)
                for _ in range(self.SPENDS_PER_SPENDER):
                    try:
                        store.spend_typed_attribute(character.id, "cash", 1)
                    except InsufficientTypedAttributeError as refusal:
                        refused.append(refusal)
            except BaseException as error:  # noqa: BLE001 - reported below
                other.append(error)

        threads = [threading.Thread(target=spender) for _ in range(self.SPENDERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual([repr(e) for e in other], [])
        self.assertEqual(len(refused), 1)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["cash"], 0
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
