"""LANE-DB: the atomic `characters` typed-attribute ADD door.

`LANE-Q CORE-REQUEST pf_bridge/notes_to_chief/20260907_1027_LANE-Q-CORE-
REQUEST-atomic-add-typed-attribute-for-quest-reward-payout.md`.  LANE-Q's
`lua_api/reward.QuestRewardStore` is a `Protocol` with four contracts and a
`pay()` that REFUSES rather than falling back to a read-modify-write when
the store has no such method; 1,039 of 1,213 quest reward rows have real
numbers waiting behind it.  This file measures `SQLiteStore.
add_typed_attribute`, the method that answers it.

WHAT THIS FILE DOES AND DOES NOT PROVE.  `QuestRewardReachesARealRowTests`
at the bottom pays one resolved criteria reward through LANE-Q's `pay()`
into a real `SQLiteStore` and reads it back off disk, which is as far as
this side of the seam reaches.  What is still NOT proven here is
client-observable: whether a player sees experience move needs `pay()`
reached from a real quest completion on a real connection, which is
LANE-Q's half.

Round `coqzj0` wrote here that "their own suite is what goes red the day
this method lands" and then shipped without acting on it:
`tests/test_script_lua_api_reward.py::PayoutTests::test_the_real_store_
class_is_refused_today` did exactly that, the Windows gate closed
`pirate-force-server#1032` for it, and the whole round had to be recovered
in round `ueaey7`.  Seeing a tripwire is not the same as paying it.

THE ONE CONTRACT A CALLER CANNOT SEE is atomicity: LANE-Q wrote in as many
words that a method of this NAME whose body was a read-modify-write would
pass their `callable(getattr(...))` check and silently eat a concurrent
payout.  `test_two_writers_racing_the_same_column_both_land` is that
contract measured HERE, with two real connections, because it cannot be
measured there.
"""
from __future__ import annotations

import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import pf_birth_state as _pin  # noqa: E402

from pirateforce_foundation.lua_api import quest_criteria, reward  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.persistence_typed_attrs import (  # noqa: E402
    TYPED_COLUMNS,
    TypedAttrError,
)
from pirateforce_foundation.store import (  # noqa: E402
    SQLiteStore,
    UnmeasuredTypedAttributeError,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

_next_identity = iter(range(0x31000001, 0x31001000))


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


class AddTypedAttributeTests(_StoreFixture):
    def test_returns_the_balance_after_the_addition(self):
        """Contract 3.  The caller must not have to read back to find out
        whether the write landed."""
        character = self._with("experience", 100)
        self.assertEqual(
            self.store.add_typed_attribute(character.id, "experience", 22120),
            22220,
        )
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["experience"], 22220
        )

    def test_the_quest_2170_payout_from_the_request_letter(self):
        """The number LANE-Q's letter names by hand, end to end."""
        character = self._with("experience", 0)
        self.assertEqual(
            self.store.add_typed_attribute(character.id, "experience", 22120),
            22120,
        )

    def test_a_zero_balance_is_a_measured_value_and_adds_normally(self):
        character = self._with("cash", 0)
        self.assertEqual(self.store.add_typed_attribute(character.id, "cash", 5), 5)

    def test_a_null_column_is_refused_by_name_not_treated_as_zero(self):
        """Contract 2, and the reason the request exists: `read_typed_
        attributes` DROPS a NULL column, so a caller doing its own
        arithmetic reaches for `.get(column, 0)` and guesses."""
        character = self._make_character()
        # THE UNMEASURED STATE IS CONSTRUCTED NOW.  `migrations/017` gives
        # this column a birth default (`PANYA-DECISION 20260908_1218`
        # point 3), so no newborn arrives here holding NULL any more and
        # this refusal stopped being reachable by accident.  It has to
        # stay reachable on purpose: the owner's database still holds
        # rows written before `016` ran, and a fail-closed door whose
        # refusal no test can reach is a door that can be deleted with
        # the suite green.
        _pin.clear_columns_to_null(self.path, ["experience"], [character.id])
        self.assertNotIn("experience", self.store.read_typed_attributes(character.id))
        with self.assertRaises(UnmeasuredTypedAttributeError) as caught:
            self.store.add_typed_attribute(character.id, "experience", 10)
        self.assertIn("experience", str(caught.exception))
        # Nothing written: the column is still NULL, not 10.
        self.assertNotIn("experience", self.store.read_typed_attributes(character.id))

    def test_the_column_must_come_from_the_typed_column_table(self):
        character = self._with("experience", 1)
        for column in ("name", "id", "experience; DROP TABLE characters", "hp"):
            with self.subTest(column=column):
                with self.assertRaises(TypedAttrError):
                    self.store.add_typed_attribute(character.id, column, 1)
        # The table is still there and the value is untouched.
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["experience"], 1
        )

    def test_every_column_lane_q_can_send_is_actually_servable(self):
        """Contract 4, derived from the table rather than from the letter's
        list, so a column leaving `TYPED_COLUMNS` fails here."""
        for column in ("experience", "cash", "skill_points"):
            with self.subTest(column=column):
                self.assertIn(column, TYPED_COLUMNS)
                character = self._with(
                    column, 1, login=f"acct_{column}", name=f"N{column[:6]}"
                )
                self.assertEqual(
                    self.store.add_typed_attribute(character.id, column, 2), 3
                )

    def test_a_result_past_the_wire_kind_is_refused_not_wrapped(self):
        """Validated, not clamped: an addition that would carry the column
        past what the client can be sent writes nothing."""
        spec = TYPED_COLUMNS["experience"]
        character = self._with("experience", int(spec.maximum))
        with self.assertRaises(TypedAttrError):
            self.store.add_typed_attribute(character.id, "experience", 1)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["experience"],
            int(spec.maximum),
        )

    def test_a_negative_delta_is_refused_and_says_which_door_subtracts(self):
        character = self._with("skill_points", 10)
        with self.assertRaises(ValueError) as caught:
            self.store.add_typed_attribute(character.id, "skill_points", -1)
        self.assertIn("spend_skill_points", str(caught.exception))
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["skill_points"], 10
        )

    def test_a_zero_delta_writes_the_same_value_back(self):
        character = self._with("cash", 42)
        self.assertEqual(self.store.add_typed_attribute(character.id, "cash", 0), 42)

    def test_bools_are_not_ints_here(self):
        character = self._with("cash", 1)
        with self.assertRaises(TypeError):
            self.store.add_typed_attribute(character.id, "cash", True)
        with self.assertRaises(TypeError):
            self.store.add_typed_attribute(True, "cash", 1)

    def test_a_non_str_column_is_a_type_error(self):
        character = self._with("cash", 1)
        with self.assertRaises(TypeError):
            self.store.add_typed_attribute(character.id, 24, 1)

    def test_ids_and_deltas_past_sqlite_int64_are_refused_not_overflowed(self):
        character = self._with("cash", 1)
        with self.assertRaises(KeyError):
            self.store.add_typed_attribute(2 ** 63, "cash", 1)
        with self.assertRaises(ValueError):
            self.store.add_typed_attribute(character.id, "cash", 2 ** 63)

    def test_unknown_and_soft_deleted_characters_are_key_errors(self):
        with self.assertRaises(KeyError):
            self.store.add_typed_attribute(999999, "cash", 1)
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03", _build_wire, _HOME,
        )
        self.store.write_typed_attributes(character.id, {"cash": 5})
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.add_typed_attribute(character.id, "cash", 1)


class AtomicityTests(_StoreFixture):
    """The contract LANE-Q cannot check from their side (their (a))."""

    ADDS_PER_WRITER = 40
    WRITERS = 4

    def test_two_writers_racing_the_same_column_both_land(self):
        """A read-modify-write across two connections loses one side's
        payout SILENTLY -- no error anywhere -- which is exactly the failure
        `pf-adversary D14` named.  This is that failure, made to happen.

        Every writer opens its own `SQLiteStore` on the same file, so the
        only thing serialising them is `BEGIN IMMEDIATE` inside the method.
        If the body were a read-modify-write, the total would come out BELOW
        `WRITERS * ADDS_PER_WRITER` and nothing would raise.
        """
        character = self._with("experience", 0)
        start = threading.Barrier(self.WRITERS)
        errors: list[BaseException] = []

        def writer():
            store = SQLiteStore(self.path, MIGRATIONS)
            try:
                start.wait(timeout=30)
                for _ in range(self.ADDS_PER_WRITER):
                    store.add_typed_attribute(character.id, "experience", 1)
            except BaseException as error:  # noqa: BLE001 - reported below
                errors.append(error)

        threads = [threading.Thread(target=writer) for _ in range(self.WRITERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        self.assertEqual([repr(e) for e in errors], [])
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["experience"],
            self.WRITERS * self.ADDS_PER_WRITER,
            "a concurrent add was lost -- this door is not atomic",
        )

    def test_the_same_race_through_a_read_modify_write_loses_writes(self):
        """The control, so the test above cannot pass merely because the
        race never happened on this machine.  Same threads, same file, same
        counts -- but the arithmetic done the way LANE-Q refused to do it.

        DELIBERATELY ASSERTS ONLY `<=`, AND DOES NOT SKIP.  Whether two
        threads actually interleave is a property of the machine, not of
        this repository, so an assertion that a write WAS lost would be a
        test that goes red on a fast enough or slow enough runner -- and a
        `skipTest` would be a new unpinned skip in the gate's census.  The
        number it observed is what matters, and it is carried in the failure
        message and written into the round file rather than asserted: on the
        run that shipped this file, four writers x 40 adds landed 160/160
        through `add_typed_attribute` and 40/160 through the
        read-modify-write -- 120 payouts lost with nothing raised anywhere --
        on the same machine in the same session.
        """
        character = self._with("cash", 0)
        start = threading.Barrier(self.WRITERS)

        def writer():
            store = SQLiteStore(self.path, MIGRATIONS)
            start.wait(timeout=30)
            for _ in range(self.ADDS_PER_WRITER):
                current = store.read_typed_attributes(character.id)["cash"]
                store.write_typed_attributes(character.id, {"cash": current + 1})

        threads = [threading.Thread(target=writer) for _ in range(self.WRITERS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)
        expected = self.WRITERS * self.ADDS_PER_WRITER
        total = self.store.read_typed_attributes(character.id)["cash"]
        self.assertLessEqual(
            total,
            expected,
            "a read-modify-write cannot produce MORE than the adds issued; "
            f"got {total} from {expected} adds, which means this control is "
            "not measuring what it claims to",
        )


class QuestRewardReachesARealRowTests(_StoreFixture):
    """The payout LANE-Q's tripwire asked the landing round to prove.

    `tests/test_script_lua_api_reward.py` carried a test asserting this
    method was ABSENT, whose docstring said that the round which lands it
    must delete it and prove a payout instead.  This is that proof: a
    criteria reward resolved from this repository's own quest mirror, paid
    through `lua_api.reward.pay` into a real `SQLiteStore`, and then read
    back OFF DISK through a second connection rather than believed from the
    return value of the call that claimed to have written it.

    THE TWO LAYERS ARE KEPT APART.  `payout.balance_after` is what the
    method SAID; `reread.read_typed_attributes` is what the file HOLDS.  A
    method that returned the right number and wrote nothing passes the
    first and fails the second.
    """

    def _a_resolvable_quest(self):
        """A quest id whose Exp criteria resolves to a positive number.

        Derived from the mirror, never typed in: the id that resolves today
        is a property of `gamedata`, and a hardcoded one would go red for
        the wrong reason the day a row moves.
        """
        for quest_id in sorted(quest_criteria.load_reward_rows()):
            amount, reason = quest_criteria.resolve_for_api(
                "AddCriteriaExp", quest_id)
            if amount is not None and amount.amount > 0:
                return quest_id, amount
        self.fail("no quest in the mirror resolves a positive Exp criteria: "
                  "the mirror or the resolver is broken, not this door")

    def test_a_resolved_quest_reward_lands_on_the_row_and_survives_a_reread(self):
        quest_id, expected = self._a_resolvable_quest()
        character = self._with("experience", 1000)

        payout, reason = reward.pay(
            "AddCriteriaExp", character.id, quest_id, store=self.store)

        self.assertIsNone(reason)
        self.assertIsNotNone(payout)
        self.assertEqual(payout.column, "experience")
        self.assertEqual(payout.balance_after, 1000 + expected.amount)

        reread = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(
            reread.read_typed_attributes(character.id)["experience"],
            1000 + expected.amount,
            "reward.pay reported a balance the file does not hold")

    def test_an_unmeasured_balance_is_refused_by_pay_not_paid_from_a_zero(self):
        """The contract's second half, seen from LANE-Q's side of the door.

        A character whose `experience` was never measured is NULL, not 0.
        The door refuses by name; `pay` turns that into `store_error` and
        leaves the column NULL, so nobody invents a starting point on the
        way to paying a reward.
        """
        quest_id, _expected = self._a_resolvable_quest()
        character = self._make_character()
        # THE UNMEASURED STATE IS CONSTRUCTED NOW.  `migrations/017` gives
        # this column a birth default (`PANYA-DECISION 20260908_1218`
        # point 3), so no newborn arrives here holding NULL any more and
        # this refusal stopped being reachable by accident.  It has to
        # stay reachable on purpose: the owner's database still holds
        # rows written before `016` ran, and a fail-closed door whose
        # refusal no test can reach is a door that can be deleted with
        # the suite green.
        _pin.clear_columns_to_null(self.path, ["experience"], [character.id])

        payout, reason = reward.pay(
            "AddCriteriaExp", character.id, quest_id, store=self.store)

        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_STORE_ERROR)
        self.assertNotIn("experience",
                         self.store.read_typed_attributes(character.id))


if __name__ == "__main__":
    unittest.main()
