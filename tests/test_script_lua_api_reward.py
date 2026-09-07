"""LANE-Q round `8ou0zg`: the write half of the quest reward seam.

WHAT THESE TESTS ARE FOR.  `lua_api.reward` is the one place a resolved
quest reward can reach a character row, and today it REFUSES on the real
store.  A refusal is only worth anything if it is the refusal we meant, so
these tests pin the shape of the refusal, not just its existence: which
column would have been written, what number was not paid, and -- the one
that matters most -- that nothing on the way there ever reads a balance.

`pf-adversary` D14 (round `wn088m`) is the finding this module was written
against: a read-modify-write across two connections silently eats the other
writer, and `store.read_typed_attributes` drops NULL columns so the "read"
half of it would be guessing zero anyway.  `RmwTripwireStore` below is how
that is held shut BEHAVIOURALLY: it answers `add_typed_attribute` and
EXPLODES on any read accessor.  A future edit that reintroduces the read
does not fail a string count, it fails a call.
"""
from __future__ import annotations

import unittest

from pirateforce_foundation import persistence_typed_attrs
from pirateforce_foundation.lua_api import quest as lua_api_quest
from pirateforce_foundation.lua_api import quest_criteria, reward


class RmwTripwireStore:
    """Answers the atomic delta; explodes on anything that smells like a read.

    Deliberately NOT a `unittest.mock` autospec: the point is to fail loudly
    on an attribute this lane is not allowed to touch, including one nobody
    has thought of yet, which a mock would happily invent instead.
    """

    def __init__(self, start: int = 0, answer=None):
        self.balances: dict = {}
        self.calls: list = []
        self._start = start
        self._answer = answer

    def add_typed_attribute(self, character_id: int, column: str, delta: int):
        self.calls.append((character_id, column, delta))
        if self._answer is not None:
            return self._answer
        key = (character_id, column)
        self.balances[key] = self.balances.get(key, self._start) + delta
        return self.balances[key]

    def __getattr__(self, name):  # pragma: no cover - only fires on a defect
        raise AssertionError(
            "lua_api.reward touched %r on the store: the payout seam is "
            "only allowed to call add_typed_attribute (pf-adversary D14)"
            % (name,))


class ExplodingStore:
    def add_typed_attribute(self, character_id, column, delta):
        raise RuntimeError("database is locked")


#: A quest whose `AddCriteriaExp` resolves without needing a player level.
#: Chosen from the mirror at test time, never hard-coded, so a re-vendor
#: that renumbers the rows makes this test move rather than lie.
def _a_resolvable_quest() -> int:
    for quest_id in sorted(quest_criteria.load_reward_rows()):
        amount, reason = quest_criteria.resolve_for_api(
            "AddCriteriaExp", quest_id)
        if amount is not None and amount.amount > 0:
            return quest_id
    raise AssertionError("no quest in the mirror resolves a positive Exp "
                         "criteria: the mirror or the resolver is broken")


class ColumnMapTests(unittest.TestCase):
    def test_every_reward_kind_has_a_column(self):
        self.assertEqual(set(reward.KIND_COLUMN), set(quest_criteria.KINDS))

    def test_every_column_is_a_real_typed_column(self):
        for kind, column in sorted(reward.KIND_COLUMN.items()):
            with self.subTest(kind=kind):
                self.assertIn(column, persistence_typed_attrs.TYPED_COLUMNS)

    def test_columns_are_distinct(self):
        columns = list(reward.KIND_COLUMN.values())
        self.assertEqual(len(columns), len(set(columns)))


class PayoutTests(unittest.TestCase):
    def setUp(self):
        self.quest_id = _a_resolvable_quest()
        self.expected, reason = quest_criteria.resolve_for_api(
            "AddCriteriaExp", self.quest_id)
        self.assertIsNone(reason)

    def test_pays_the_resolved_amount_into_the_mapped_column(self):
        store = RmwTripwireStore(start=1000)
        lines: list = []
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=store, log=lines.append)
        self.assertIsNone(reason)
        self.assertIsNotNone(payout)
        self.assertEqual(store.calls,
                         [(7, "experience", self.expected.amount)])
        self.assertEqual(payout.balance_after, 1000 + self.expected.amount)
        self.assertEqual(payout.column, "experience")

    def test_never_reads_a_balance(self):
        """The D14 tripwire, fired through the whole call path."""
        store = RmwTripwireStore(start=1000)
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=store)
        self.assertIsNone(reason)
        self.assertEqual(len(store.calls), 1,
                         "exactly one store call: a second one is a "
                         "read-modify-write in disguise")

    def test_each_kind_lands_in_its_own_column(self):
        seen = {}
        for api_name in sorted(quest_criteria.LEVEL_SOURCE):
            if quest_criteria.LEVEL_SOURCE[api_name] != \
                    quest_criteria.LEVEL_SOURCE_QUEST:
                continue
            for quest_id in sorted(quest_criteria.load_reward_rows()):
                amount, reason = quest_criteria.resolve_for_api(
                    api_name, quest_id)
                if amount is None or amount.amount <= 0:
                    continue
                store = RmwTripwireStore()
                payout, reason = reward.pay(api_name, 7, quest_id,
                                            store=store)
                self.assertIsNone(reason, api_name)
                seen[amount.kind] = payout.column
                break
        self.assertEqual(seen, reward.KIND_COLUMN,
                         "every reward kind reachable from the mirror must "
                         "reach its own mapped column")

    def test_no_store_refuses_and_says_what_it_would_have_paid(self):
        lines: list = []
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    log=lines.append)
        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_NO_STORE)
        self.assertEqual(len(lines), 1)
        self.assertIn("unpaid=%d" % self.expected.amount, lines[0])

    def test_a_store_without_the_atomic_add_is_refused_not_worked_around(self):
        class NoAdd:
            def read_typed_attributes(self, character_id):
                return {"experience": 5}

            def write_typed_attributes(self, character_id, values):
                raise AssertionError("reward.pay must not fall back to RMW")

        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=NoAdd())
        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_STORE_NOT_ATOMIC)

    def test_the_real_store_class_is_refused_today(self):
        """The measured fact this round reports, not an opinion about it.

        If LANE-DB lands `add_typed_attribute` on `store.Store`, THIS test
        goes red -- which is the point: the round that gets the method is
        the round that must delete this test and prove a payout instead.
        """
        from pirateforce_foundation import store as store_module

        self.assertTrue(hasattr(store_module, "SQLiteStore"),
                        "store.py's character store was renamed: this test "
                        "is asking about the wrong class")
        self.assertFalse(
            hasattr(store_module.SQLiteStore, "add_typed_attribute"),
            "store.SQLiteStore grew add_typed_attribute: wire lua_api.reward "
            "to it and replace this test with one that pays a real row")

    def test_the_real_store_would_be_refused_by_pay_not_worked_around(self):
        """Not just "the method is absent" -- what `pay` DOES about it.

        The absence above is a fact about LANE-DB's file; this is the fact
        about ours, and it is the one that matters: handed the real store
        class's surface, `pay` refuses rather than reaching for
        `read_typed_attributes` + `write_typed_attributes`, both of which
        that class does have.
        """
        from pirateforce_foundation import store as store_module

        surface = store_module.SQLiteStore
        self.assertTrue(hasattr(surface, "read_typed_attributes"))
        self.assertTrue(hasattr(surface, "write_typed_attributes"))

        class RealStoreSurface:
            read_typed_attributes = surface.read_typed_attributes
            write_typed_attributes = surface.write_typed_attributes

        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=RealStoreSurface())
        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_STORE_NOT_ATOMIC)

    def test_character_zero_is_refused(self):
        """`quest.DEFAULT_CONTEXT`'s character id must never be paid."""
        self.assertEqual(lua_api_quest.DEFAULT_CONTEXT.character_id, 0)
        store = RmwTripwireStore()
        payout, reason = reward.pay("AddCriteriaExp", 0, self.quest_id,
                                    store=store)
        self.assertEqual(reason, reward.REFUSE_NO_CHARACTER)
        self.assertEqual(store.calls, [])

    def test_a_bool_character_id_is_refused(self):
        store = RmwTripwireStore()
        payout, reason = reward.pay("AddCriteriaExp", True, self.quest_id,
                                    store=store)
        self.assertEqual(reason, reward.REFUSE_NO_CHARACTER)
        self.assertEqual(store.calls, [])

    def test_a_resolution_refusal_never_reaches_the_store(self):
        store = RmwTripwireStore()
        payout, reason = reward.pay("AddLvCriteriaExp", 7, self.quest_id,
                                    store=store)
        self.assertEqual(reason, quest_criteria.REFUSE_NO_PLAYER_LEVEL)
        self.assertEqual(store.calls, [])

    def test_a_store_that_raises_is_a_refusal_not_a_crash(self):
        lines: list = []
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=ExplodingStore(), log=lines.append)
        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_STORE_ERROR)
        self.assertIn("RuntimeError", lines[0])

    def test_a_store_that_answers_with_a_non_integer_is_refused(self):
        store = RmwTripwireStore(answer="lots")
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=store)
        self.assertIsNone(payout)
        self.assertEqual(reason, reward.REFUSE_STORE_ERROR)

    def test_a_store_that_answers_with_a_bool_is_refused(self):
        store = RmwTripwireStore(answer=True)
        payout, reason = reward.pay("AddCriteriaExp", 7, self.quest_id,
                                    store=store)
        self.assertEqual(reason, reward.REFUSE_STORE_ERROR)

    def test_every_reason_comes_from_a_closed_set(self):
        allowed = reward.REFUSALS | {
            quest_criteria.REFUSE_UNKNOWN_API,
            quest_criteria.REFUSE_NO_QUEST_ROW,
            quest_criteria.REFUSE_NO_PLAYER_LEVEL,
            quest_criteria.REFUSE_BAD_PLAYER_LEVEL,
            quest_criteria.REFUSE_LEVEL_OUT_OF_RANGE,
        }
        seen = set()
        for api_name in ("AddCriteriaExp", "AddLvCriteriaExp", "NotAnApi"):
            for character_id in (0, 7):
                for store in (None, RmwTripwireStore(), ExplodingStore()):
                    _payout, reason = reward.pay(api_name, character_id,
                                                 self.quest_id, store=store)
                    if reason is not None:
                        seen.add(reason)
        self.assertTrue(seen)
        self.assertTrue(seen <= allowed, seen - allowed)


class NamespaceWiringTests(unittest.TestCase):
    """`Quest.AddCriteriaExp()` from a script, all the way to the store.

    This is the D10 answer for the reward path: a caller inside the server
    now exists.  It is still not a quest system -- the caller has to be
    handed a context and a store by whatever dispatches the script.
    """

    def setUp(self):
        self.quest_id = _a_resolvable_quest()
        self.expected, _ = quest_criteria.resolve_for_api(
            "AddCriteriaExp", self.quest_id)

    def _namespace(self, log, **kwargs):
        context = lua_api_quest.QuestContext(character_id=7,
                                             quest_id=self.quest_id)
        return lua_api_quest.build_namespace(
            frozenset(lua_api_quest.CRITERIA_METHODS), log,
            context=context, **kwargs)

    def test_a_script_call_moves_a_row_when_a_store_is_bound(self):
        store = RmwTripwireStore(start=0)
        lines: list = []
        namespace = self._namespace(lines.append, reward_store=store)
        namespace["AddCriteriaExp"]()
        self.assertEqual(store.calls,
                         [(7, "experience", self.expected.amount)])

    def test_the_default_namespace_pays_nothing_and_says_so(self):
        lines: list = []
        namespace = self._namespace(lines.append)
        namespace["AddCriteriaExp"]()
        payout = [line for line in lines if "LUA_QUEST_PAYOUT" in line]
        self.assertEqual(len(payout), 1)
        self.assertIn("refused=%s" % reward.REFUSE_NO_STORE, payout[0])

    def test_criteria_and_payout_are_two_separate_lines(self):
        store = RmwTripwireStore()
        lines: list = []
        namespace = self._namespace(lines.append, reward_store=store)
        namespace["AddCriteriaExp"]()
        self.assertEqual(
            len([line for line in lines if "LUA_QUEST_CRITERIA" in line]), 1)
        self.assertEqual(
            len([line for line in lines if "LUA_QUEST_PAYOUT" in line]), 1)

    def test_a_resolve_refusal_is_logged_once_not_twice(self):
        """No `LUA_QUEST_PAYOUT` echo of a refusal the resolver already made."""
        lines: list = []
        namespace = self._namespace(lines.append,
                                    reward_store=RmwTripwireStore())
        namespace["AddLvCriteriaExp"]()
        self.assertEqual(
            len([line for line in lines if "LUA_QUEST_CRITERIA" in line]), 1)
        self.assertEqual(
            [line for line in lines if "LUA_QUEST_PAYOUT" in line], [])

    def test_the_stub_still_returns_the_stub_default(self):
        """Paying a reward must not change what the script gets back.

        The six names stay stubbed on the RETURN value until someone can say
        what the game's own engine returns from them; a payout is a side
        effect, and quietly changing the return value would be this lane
        guessing an API contract it has not measured.
        """
        store = RmwTripwireStore()
        namespace = self._namespace(lambda _line: None, reward_store=store)
        self.assertEqual(namespace["AddCriteriaExp"](),
                         lua_api_quest.STUB_DEFAULT)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
