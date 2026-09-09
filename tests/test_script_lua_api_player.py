"""LANE-Q: the ``Player.*`` names real so far -- ``GetLv``/``GetClass``
(round ``gqjas5``) plus this round's ``CheckItemNum``/``GetItemNum``/
``CheckEquipItem``, the inventory seam's read side
(``COO-DECISION 20260906_1846``).

Same three-level shape as ``tests/test_script_lua_api_quest.py``: the
namespace object's ``__getitem__`` contract alone (no lupa dependency, runs
on every machine), then real scripts running against it through a live
``ScriptHost`` (guarded by ``LUPA_PACKAGE``).
"""
import unittest

from pf_preconditions import LUPA_PACKAGE

from pirateforce_foundation.inventory import BackpackState, ItemAttrState
from pirateforce_foundation.lua_api import player


#: A minimal stand-in for the one store method this seam is allowed to
#: call.  Deliberately not a mock: an attribute nobody has thought of yet
#: would be invented by a mock and explode here instead, the same posture
#: ``tests/test_script_lua_api_reward.py``'s own tripwire store takes.
class _RecordingPayoutStore:
    """Both directions, and it records the SIGN it was asked for.

    ``calls`` holds a positive delta for an add and a NEGATIVE one for a
    spend, so a test can assert which door the namespace picked without
    reading the log: a closure that sent a charge down the adding path
    would record ``+n`` where the test wants ``-n``, and no amount of
    correct-looking arithmetic hides that.
    """

    def __init__(self, start: int = 0, balances=None):
        self.calls: list = []
        self._balances: dict = dict(balances or {})
        self._start = start

    def add_typed_attribute(self, character_id: int, column: str, delta: int):
        self.calls.append((character_id, column, delta))
        key = (character_id, column)
        self._balances[key] = self._balances.get(key, self._start) + delta
        return self._balances[key]

    def spend_typed_attribute(self, character_id: int, column: str,
                              amount: int):
        from pirateforce_foundation import store as store_module

        if column in store_module.COLUMNS_WITH_THEIR_OWN_SPEND_DOOR:
            raise ValueError("%s has its own spend door" % (column,))
        return self._spend(character_id, column, amount)

    def spend_skill_points(self, character_id: int, cost: int):
        return self._spend(character_id, "skill_points", cost)

    def _spend(self, character_id: int, column: str, amount: int):
        from pirateforce_foundation import store as store_module

        self.calls.append((character_id, column, -amount))
        key = (character_id, column)
        current = self._balances.get(key, self._start)
        if current < amount:
            raise store_module.InsufficientTypedAttributeError(
                "character %d has %s=%d, which does not cover %d"
                % (character_id, column, current, amount))
        self._balances[key] = current - amount
        return self._balances[key]


def _grant_home():
    """The home position ``create_character`` needs.

    Irrelevant to a stat grant -- only its type is -- so it is built from
    the real ``model.Position`` rather than a tuple that happens to work
    today, the same value shape ``tests/test_store_add_typed_attribute.py``
    uses.
    """
    from pirateforce_foundation.model import Position

    return Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)


class RealPlayerNamespaceTests(unittest.TestCase):
    """The ``__getitem__``/``__setitem__`` contract, without a Lua state."""

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Player"]
        calls = []
        ns = player.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_get_lv_reads_the_default_context(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["GetLv"](), player.DEFAULT_CONTEXT.level)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.GetLv "))

    def test_get_class_reads_the_default_context(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["GetClass"](), player.DEFAULT_CONTEXT.class_id)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.GetClass "))

    def test_get_lv_reads_an_injected_context(self):
        ns, _calls = self._namespace(context=player.PlayerContext(level=42, class_id=3))
        self.assertEqual(ns["GetLv"](), 42)

    def test_get_class_reads_an_injected_context(self):
        ns, _calls = self._namespace(context=player.PlayerContext(level=42, class_id=3))
        self.assertEqual(ns["GetClass"](), 3)

    def test_get_lv_wrong_arity_degrades_safely_instead_of_raising(self):
        # Every one of the 91 real call sites in the corpus uses exactly 0
        # args (grepped, api_spec.tsv's own arity_min=arity_max=0) -- same
        # "untrusted input must never crash the host" guard
        # lua_api/trigger.py's/lua_api/quest.py's real closures already carry.
        ns, calls = self._namespace()
        for args in ((1,), (1, 2)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["GetLv"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.GetLv "), calls)

    def test_get_class_wrong_arity_degrades_safely_instead_of_raising(self):
        ns, calls = self._namespace()
        for args in ((1,), (1, 2)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["GetClass"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.GetClass "), calls)

    def _backpack(self, *rows):
        # rows: (identity, template_id, quantity, slot)
        return BackpackState(0xFF, 0, 1, tuple(
            ItemAttrState(identity, template_id, quantity, slot)
            for identity, template_id, quantity, slot in rows
        ))

    def test_get_item_num_reads_the_default_context_as_zero(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["GetItemNum"](2600001), 0)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.GetItemNum "))

    def test_get_item_num_sums_quantity_across_matching_rows_only(self):
        backpack = self._backpack(
            (1, 2600001, 3, 0), (2, 2400901, 1, 1), (3, 2600001, 2, 2),
        )
        ns, _calls = self._namespace(context=player.PlayerContext(backpack=backpack))
        self.assertEqual(ns["GetItemNum"](2600001), 5)
        self.assertEqual(ns["GetItemNum"](2400901), 1)
        self.assertEqual(ns["GetItemNum"](9999999), 0)

    def test_get_item_num_wrong_arity_degrades_safely_instead_of_raising(self):
        ns, calls = self._namespace()
        for args in ((), (1, 2)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["GetItemNum"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.GetItemNum "), calls)

    def test_get_item_num_never_raises_on_a_malformed_context_backpack(self):
        # pf-adversary, round qbr5h8: PlayerContext(backpack=None) raised a
        # raw AttributeError straight out of _item_count before this fix.
        # No dispatcher builds a PlayerContext from live data yet, but the
        # day one does (a store.get_backpack decode failure, say), this
        # must degrade like every other real closure in this file, not
        # crash the whole script call.
        ns, _calls = self._namespace(context=player.PlayerContext(backpack=None))
        self.assertEqual(ns["GetItemNum"](2600001), 0)
        self.assertIs(ns["CheckItemNum"](2600001, 1), False)

    def test_get_item_num_never_raises_on_a_row_with_a_non_numeric_quantity(self):
        # pf-adversary, round qbr5h8: a row whose quantity is None raised
        # TypeError from `sum(...)` before this fix.
        backpack = BackpackState(0xFF, 0, 1, (ItemAttrState(1, 2600001, None, 0),))
        ns, _calls = self._namespace(context=player.PlayerContext(backpack=backpack))
        self.assertEqual(ns["GetItemNum"](2600001), 0)

    def test_check_equip_item_never_raises_on_malformed_equipped_ids(self):
        # pf-adversary, round qbr5h8: equipped_template_ids=None raised
        # TypeError ("argument of type 'NoneType' is not iterable") before
        # this fix.
        ns, _calls = self._namespace(
            context=player.PlayerContext(equipped_template_ids=None))
        self.assertIs(ns["CheckEquipItem"](2200225), False)

    def test_get_item_num_bad_argument_type_counts_as_zero_not_a_crash(self):
        ns, _calls = self._namespace()
        self.assertEqual(ns["GetItemNum"]("not-a-template-id"), 0)
        self.assertEqual(ns["GetItemNum"](True), 0)  # bool rejected, same as trigger._coerce_int

    def test_check_item_num_true_when_held_at_least_required(self):
        backpack = self._backpack((1, 2600001, 3, 0))
        ns, calls = self._namespace(context=player.PlayerContext(backpack=backpack))
        self.assertIs(ns["CheckItemNum"](2600001, 3), True)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.CheckItemNum "))

    def test_check_item_num_false_when_held_less_than_required(self):
        backpack = self._backpack((1, 2600001, 2, 0))
        ns, _calls = self._namespace(context=player.PlayerContext(backpack=backpack))
        self.assertIs(ns["CheckItemNum"](2600001, 3), False)

    def test_check_item_num_false_when_item_never_held(self):
        ns, _calls = self._namespace()
        self.assertIs(ns["CheckItemNum"](2600001, 1), False)

    def test_check_item_num_wrong_arity_degrades_safely_instead_of_raising(self):
        ns, calls = self._namespace()
        for args in ((), (1,), (1, 2, 3)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["CheckItemNum"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.CheckItemNum "), calls)

    def test_check_item_num_bad_argument_type_refuses_rather_than_guesses(self):
        ns, calls = self._namespace()
        self.assertIs(ns["CheckItemNum"]("bad", 1), False)
        self.assertIs(ns["CheckItemNum"](1, "bad"), False)
        self.assertTrue(all(
            c.startswith("LUA_PLAYER_REAL Player.CheckItemNum ") for c in calls))

    def test_check_equip_item_true_when_template_is_equipped(self):
        ns, calls = self._namespace(
            context=player.PlayerContext(equipped_template_ids=frozenset({2200225})))
        self.assertIs(ns["CheckEquipItem"](2200225), True)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.CheckEquipItem "))

    def test_check_equip_item_false_when_not_equipped(self):
        ns, _calls = self._namespace()
        self.assertIs(ns["CheckEquipItem"](2200225), False)

    def test_check_equip_item_wrong_arity_degrades_safely_instead_of_raising(self):
        ns, calls = self._namespace()
        for args in ((), (1, 2)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["CheckEquipItem"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.CheckEquipItem "), calls)

    def test_mob_appear_true_sets_the_flag_and_returns_it(self):
        ns, calls = self._namespace(context=player.PlayerContext(character_id=1))
        self.assertIs(ns["MobAppear"](500, True), True)
        self.assertTrue(calls[0].startswith("LUA_PLAYER_REAL Player.MobAppear "))

    def test_mob_appear_false_clears_the_flag_and_returns_it(self):
        ns, _calls = self._namespace(context=player.PlayerContext(character_id=1))
        ns["MobAppear"](500, True)
        self.assertIs(ns["MobAppear"](500, False), False)

    def test_mob_appear_is_keyed_per_character_not_shared(self):
        store = player.InMemoryPlayerMobAppearStore()
        char_a, _ = self._namespace(
            context=player.PlayerContext(character_id=1), store=store)
        char_b, _ = self._namespace(
            context=player.PlayerContext(character_id=2), store=store)
        char_a["MobAppear"](500, True)
        self.assertEqual(store.get_mob_appear_flag(1, 500), True)
        self.assertIsNone(store.get_mob_appear_flag(2, 500))
        # char_b writes its OWN flag on the same shared store -- must not
        # disturb char_a's own already-set flag for the same mob id.
        self.assertIs(char_b["MobAppear"](500, False), False)
        self.assertEqual(store.get_mob_appear_flag(1, 500), True)
        self.assertEqual(store.get_mob_appear_flag(2, 500), False)

    def test_mob_appear_does_not_touch_a_second_injected_store(self):
        # A regression guard for the exact shape lua_api.quest's own
        # OneScriptHostSharesOneQuestStateStoreTests exists to catch:
        # two DIFFERENT store instances must never be confused with a
        # shared one just because both start empty.
        store_a = player.InMemoryPlayerMobAppearStore()
        store_b = player.InMemoryPlayerMobAppearStore()
        ns_a, _ = self._namespace(
            context=player.PlayerContext(character_id=1), store=store_a)
        ns_a["MobAppear"](500, True)
        self.assertIsNone(store_b.get_mob_appear_flag(1, 500))

    def test_mob_appear_wrong_arity_degrades_safely_instead_of_raising(self):
        ns, calls = self._namespace()
        for args in ((), (1,), (1, True, 2)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["MobAppear"](*args)
                self.assertEqual(result, player.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith(
                    "LUA_PLAYER_BAD_ARITY Player.MobAppear "), calls)

    def test_mob_appear_bad_argument_type_refuses_rather_than_guesses(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["MobAppear"]("bad", True), player.STUB_DEFAULT)
        self.assertEqual(ns["MobAppear"](500, "not-a-bool"), player.STUB_DEFAULT)
        # A Lua/Python int (0/1) is never accepted as the visibility flag --
        # only an actual bool -- same "booleans/ints are not interchangeable
        # with each other's meaning" posture _coerce_int already takes in
        # the other direction (a bool is refused as an int).
        self.assertEqual(ns["MobAppear"](500, 1), player.STUB_DEFAULT)
        self.assertTrue(all(
            c.startswith("LUA_PLAYER_BAD_VALUE Player.MobAppear ") for c in calls))

    def test_mob_appear_never_raises_on_a_malformed_store(self):
        class _BrokenStore:
            def set_mob_appear_flag(self, *_a, **_k):
                raise RuntimeError("boom")

        ns, _calls = self._namespace(store=_BrokenStore())
        with self.assertRaises(RuntimeError):
            # Documented, not silently swallowed: unlike the inventory
            # closures above (which validate a caller-supplied CONTEXT
            # field), MobAppear's store is an injected COLLABORATOR, not
            # untrusted script input -- a broken store is this namespace's
            # own caller-programming error, not a script's fault, so it
            # propagates rather than degrading to a fake success.
            ns["MobAppear"](500, True)

    def test_a_still_stubbed_method_logs_lua_api_stub_exactly_like_before(self):
        # RemoveItem, not AddItem: AddItem moved to REAL_METHODS this
        # round (store.mint_backpack_item landed) -- see
        # AddItemClosureTests for its own coverage.
        ns, calls = self._namespace()
        self.assertEqual(ns["RemoveItem"](1, 2), player.STUB_DEFAULT)
        self.assertEqual(calls, ["LUA_API_STUB Player.RemoveItem"])

    def test_every_still_stubbed_name_is_reachable_and_logs_its_own_line(self):
        for name in player.STILL_STUBBED:
            with self.subTest(method=name):
                ns, calls = self._namespace()
                ns[name]()
                self.assertEqual(calls, ["LUA_API_STUB Player.%s" % name])

    def test_still_stubbed_plus_real_accounts_for_all_73_names(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Player"]
        self.assertEqual(len(methods), 73)
        self.assertEqual(set(player.STILL_STUBBED) | player.REAL_METHODS, set(methods))
        self.assertEqual(set(player.STILL_STUBBED) & player.REAL_METHODS, set())

    def test_a_non_api_key_returns_the_stub_default_silently(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["Var1"], player.STUB_DEFAULT)
        self.assertEqual(calls, [])

    def test_writing_into_the_namespace_is_accepted_and_discarded(self):
        ns, _calls = self._namespace()
        self.assertIsNone(ns.__setitem__("Var1", 42))

    def test_default_context_matches_the_fresh_login_constants(self):
        # Not an independent value -- explicitly the same constants
        # player_wire.PLAYER_LOGIN_LEVEL/PLAYER_LOGIN_CLASS_ID already send
        # on a fresh login, per this module's own docstring.
        from pirateforce_foundation import player_wire

        self.assertEqual(player.DEFAULT_CONTEXT.level, player_wire.PLAYER_LOGIN_LEVEL)
        self.assertEqual(player.DEFAULT_CONTEXT.class_id, player_wire.PLAYER_LOGIN_CLASS_ID)


class StatGrantTests(unittest.TestCase):
    """``Player.AddExp``/``Player.AddSkillPoint`` -- the first two Player.*
    names that WRITE.

    The amount is the script's own (``Player.AddExp(Player.GetLv()*
    Trigger.Var5)`` in ``gamedata/lua/t_getm_rat_exp&sp.lua``), so what is
    pinned here is the door: which arguments get through, which column the
    kind maps to, and that a namespace with no store refuses OUT LOUD
    instead of pretending.  The store contract itself is
    ``lua_api.reward``'s and is pinned in that lane's own test file.
    """

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Player"]
        calls = []
        ns = player.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_add_exp_moves_the_experience_column(self):
        store = _RecordingPayoutStore()
        ns, calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        ns["AddExp"](250)
        self.assertEqual(store.calls, [(9, "experience", 250)])
        self.assertTrue(any("LUA_PLAYER_GRANT Player.AddExp" in line
                            for line in calls), calls)

    def test_add_skill_point_moves_the_skill_point_column(self):
        store = _RecordingPayoutStore()
        ns, _calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        ns["AddSkillPoint"](3)
        self.assertEqual(store.calls, [(9, "skill_points", 3)])

    def test_a_paid_grant_still_returns_the_stub_default(self):
        """A payout is a SIDE EFFECT.

        Nobody has measured what the game's own engine returns from these
        two names, and both corpus call sites use them as statements, so
        handing back a column balance would be inventing an API contract.
        Same rule the six ``Quest.Add*Criteria*`` names already live under.
        """
        store = _RecordingPayoutStore()
        ns, _calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        self.assertEqual(ns["AddExp"](250), player.STUB_DEFAULT)

    def test_without_a_store_nothing_is_written_and_the_log_says_so(self):
        ns, calls = self._namespace(
            context=player.PlayerContext(character_id=9))
        self.assertEqual(ns["AddExp"](250), player.STUB_DEFAULT)
        refusals = [line for line in calls if "refused=" in line]
        self.assertEqual(len(refusals), 1, calls)
        self.assertIn("no_reward_store", refusals[0])
        self.assertIn("unpaid=250", refusals[0])

    def test_a_negative_or_unusable_amount_never_reaches_the_store(self):
        """The store call is what is asserted, not just the return value.

        ``store.add_typed_attribute`` takes ``delta >= 0``; a negative that
        got this far would be refused by SOMEBODY, but it must be refused
        HERE, where the log names the script's own number.
        """
        store = _RecordingPayoutStore()
        ns, calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        for amount in (-1, 12.5, float("nan"), float("inf"), True, "250"):
            with self.subTest(amount=amount):
                self.assertEqual(ns["AddExp"](amount), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertEqual(len([c for c in calls if "LUA_API_BAD_VALUE" in c
                              or "bad_value" in c.lower()]), 6, calls)

    def test_the_wrong_arity_is_refused_before_the_store(self):
        store = _RecordingPayoutStore()
        ns, _calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        self.assertEqual(ns["AddExp"](), player.STUB_DEFAULT)
        self.assertEqual(ns["AddExp"](1, 2), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])

    def test_the_default_context_character_is_refused_not_paid(self):
        """``character_id`` 0 is the inert bucket, not a player."""
        store = _RecordingPayoutStore()
        ns, calls = self._namespace(payout_store=store)
        ns["AddExp"](250)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=no_character" in line for line in calls),
                        calls)

    def test_add_cash_is_no_longer_a_stub(self):
        """It was stubbed for one reason, and that reason is gone.

        The corpus CHARGES with this name (``q_ship.lua:50``), so paying
        its positive call sites while dropping its negative ones would let
        a player buy a ship for free.  LANE-DB's
        ``store.spend_typed_attribute`` (round ``dcz2sv``) is the floor
        answer that was missing; both halves exist now, so the name opens.
        """
        self.assertNotIn("AddCash", player.STILL_STUBBED)
        self.assertIn("AddCash", player.REAL_METHODS)
        store = _RecordingPayoutStore()
        ns, calls = self._namespace(
            context=player.PlayerContext(character_id=9), payout_store=store)
        self.assertEqual(ns["AddCash"](500), player.STUB_DEFAULT)
        self.assertNotIn("LUA_API_STUB Player.AddCash", calls)
        self.assertEqual(store.calls, [(9, "cash", 500)])

    def test_the_grant_map_is_exactly_these_two_names(self):
        """GRANT_KINDS pinned BY VALUE, not merely iterated.

        pf-adversary D11 (round yfeauz): the loop below passes on an empty
        map and on a third entry, so it could not catch a name being added
        to the paying set without anyone reading the corpus for its sign --
        which is the whole reason AddCash is not in it.
        """
        from pirateforce_foundation.lua_api import quest_criteria

        self.assertEqual(player.GRANT_KINDS, {
            "AddExp": quest_criteria.KIND_EXP,
            "AddSkillPoint": quest_criteria.KIND_SKILL_POINT,
        })

    def test_the_signed_map_is_exactly_add_cash(self):
        """Pinned BY VALUE for the same reason ``GRANT_KINDS`` is.

        A name in here gets a door that can take a player's money on a
        NEGATIVE argument.  Adding one without reading the corpus for what
        that name's negative call sites mean is precisely the mistake this
        assertion exists to make loud.
        """
        from pirateforce_foundation.lua_api import quest_criteria, reward

        self.assertEqual(player.SIGNED_STAT_KINDS, {
            "AddCash": quest_criteria.KIND_CASH,
        })
        self.assertEqual(
            set(player.SIGNED_STAT_KINDS) & set(player.GRANT_KINDS), set())
        for name, kind in player.SIGNED_STAT_KINDS.items():
            with self.subTest(name=name):
                self.assertIn(name, player.REAL_METHODS)
                self.assertNotIn(name, player.STILL_STUBBED)
                self.assertIn(kind, reward.KIND_COLUMN)
                self.assertIn(kind, reward.SPEND_DOOR)

    def test_every_grant_kind_maps_to_a_column_this_lane_can_pay(self):
        from pirateforce_foundation.lua_api import reward
        for name, kind in player.GRANT_KINDS.items():
            with self.subTest(name=name):
                self.assertIn(name, player.REAL_METHODS)
                self.assertNotIn(name, player.STILL_STUBBED)
                self.assertIn(kind, reward.KIND_COLUMN)


class StatGrantReachesARealRowTests(unittest.TestCase):
    """The same two names against a real ``SQLiteStore`` on disk.

    The layer above pins the door with a recording double; this one pins
    that the door opens onto an actual ``characters`` row -- read back off
    the store after the call, never from the number the namespace returned.
    """

    def setUp(self):
        import tempfile
        from pathlib import Path

        from pirateforce_foundation.store import SQLiteStore

        migrations = Path(__file__).resolve().parents[1] / "migrations"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = SQLiteStore(Path(tmp.name) / "state.sqlite3", migrations)
        self.store.migrate()
        account_id = self.store.ensure_account("acct-grant")
        self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "Grant01", "grant01", "fp-grant",
            lambda selector: (b"wire", b"avatar", 4242, 0),
            _grant_home(),
        )
        # A measured starting balance: `add_typed_attribute` refuses a NULL
        # column rather than guessing zero, so a row nobody has ever
        # measured is not a row this seam may add to.
        self.store.write_typed_attributes(
            self.character.id, {"experience": 100, "skill_points": 2})

    def _namespace(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        calls = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=self.character.id),
            payout_store=self.store)
        return ns, calls

    def test_add_exp_adds_to_the_row_on_disk(self):
        ns, calls = self._namespace()
        ns["AddExp"](250)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(stored["experience"], 350)
        self.assertTrue(any("balance_after=350" in line for line in calls),
                        calls)

    def test_add_skill_point_adds_to_the_row_on_disk(self):
        ns, _calls = self._namespace()
        ns["AddSkillPoint"](3)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(stored["skill_points"], 5)

    def test_an_unmeasured_column_refuses_rather_than_starting_at_zero(self):
        """COO-DECISION 20260901_1059, end to end.

        A character nobody has ever granted cash to has a NULL column; the
        store refuses, and this seam reports it as a refusal rather than
        inventing a starting balance.  Uses ``reward.grant`` directly for
        cash because ``Player.AddCash`` is deliberately still a stub.
        """
        from pirateforce_foundation.lua_api import quest_criteria, reward
        lines: list = []
        granted, reason = reward.grant(
            "Player.AddCash", quest_criteria.KIND_CASH, self.character.id,
            500, store=self.store, log=lines.append)
        self.assertIsNone(granted)
        self.assertEqual(reason, reward.REFUSE_STORE_ERROR)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertNotIn("cash", stored)


@LUPA_PACKAGE.skip_unless_present()
class RealPlayerLuaIntegrationTests(unittest.TestCase):
    """The same context checks, driven from real Lua through a ScriptHost."""

    def _host(self, context=None, store=None, payout_store=None):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(
            log=calls.append, player_context=context, player_store=store,
            payout_store=payout_store)
        return host, calls

    def test_add_exp_from_real_lua_reaches_the_hosts_payout_store(self):
        """``ScriptHost``'s new pass-through, exercised through a Lua state.

        The namespace-level tests above prove the closure; this proves the
        WIRING -- that a store handed to the host arrives at the Player
        namespace and not at some private default.  Written at the shape
        of the corpus's own only call site
        (``gamedata/lua/t_getm_rat_exp&sp.lua:19``:
        ``Player.AddExp(Player.GetLv()*Trigger.Var5)``), with
        ``Trigger.Var5`` reading STUB_DEFAULT=0 through the host's own
        contract -- so the product is 0 and REFUSED, which is why the
        amount is written as a literal in the paying half below.
        """
        store = _RecordingPayoutStore()
        host, calls = self._host(
            context=player.PlayerContext(level=7, character_id=9),
            payout_store=store)
        host.load("function Probe() Player.AddExp(Player.GetLv()*50) end")
        host.call("Probe")
        self.assertEqual(store.calls, [(9, "experience", 350)])
        self.assertTrue(any("LUA_PLAYER_GRANT Player.AddExp" in line
                            for line in calls), calls)

    def test_the_affordability_guard_can_finally_be_true(self):
        """`q_class.lua:47` in miniature, both ways.

        With `Player.GetCash` stubbed this branch was false for every
        player forever; the two halves here are the same script text
        against the same store with two different balances.
        """
        Reading = GetCashReadsTheColumnAddCashWritesTests._ReadingStore
        text = ("function Probe()\n"
                "  if( Player.GetCash() >= 15000 ) then\n"
                "    return 1\n"
                "  else\n"
                "    return 0\n"
                "  end\n"
                "end")
        for balance, expected in ((15000, 1), (14999, 0)):
            host, _calls = self._host(
                player.PlayerContext(character_id=9),
                payout_store=Reading(balances={(9, "cash"): balance}))
            host.load(text)
            self.assertEqual(host.call("Probe"), expected, balance)

    def test_an_unmeasured_purse_leaves_the_guard_false_from_lua(self):
        Reading = GetCashReadsTheColumnAddCashWritesTests._ReadingStore
        host, calls = self._host(player.PlayerContext(character_id=9),
                                 payout_store=Reading())
        host.load("function Probe() return Player.GetCash() end")
        self.assertEqual(host.call("Probe"), player.STUB_DEFAULT)
        self.assertTrue(any("refused=balance_was_never_measured" in line
                            for line in calls), calls)

    def test_a_host_with_no_payout_store_refuses_out_loud(self):
        host, calls = self._host(
            context=player.PlayerContext(level=7, character_id=9))
        host.load("function Probe() Player.AddSkillPoint(3) end")
        host.call("Probe")
        refusals = [line for line in calls if "refused=no_reward_store" in line]
        self.assertEqual(len(refusals), 1, calls)

    def test_get_lv_from_lua_reads_the_injected_context(self):
        host, calls = self._host(player.PlayerContext(level=17, class_id=2))
        host.load("function Probe() return Player.GetLv() end")
        self.assertEqual(host.call("Probe"), 17)
        self.assertTrue(any(c.startswith("LUA_PLAYER_REAL ") for c in calls))

    def test_get_class_from_lua_reads_the_injected_context(self):
        host, _calls = self._host(player.PlayerContext(level=17, class_id=2))
        host.load("function Probe() return Player.GetClass() end")
        self.assertEqual(host.call("Probe"), 2)

    def test_the_real_q_day_watch_accept_check_gate_is_real_now(self):
        # gamedata/lua/Quest/q_day_watch.lua's own Accept_Check (grepped,
        # line 13, inside the Accept_Check() function that starts line 9 --
        # NOT Report_Check(), a different function at line 37 gating on
        # Player.CheckMoralized instead; pf-adversary caught this file
        # citing the wrong function name for the right line number):
        # `Player.GetLv() <= (Quest.Var4) or (Quest.Var4) == 0`.
        # Reproduced inline at the real gate shape rather than vendoring a
        # fixture file -- same choice round vqng2z made for
        # Quest.CheckOpenTime's own q_sea_join.lua reproduction.
        source = """
        function Probe()
          if ( Player.GetLv() <= (Quest.Var4) or (Quest.Var4) == 0 ) then
            return 1
          else
            return 0
          end
        end
        """
        under_cap, _calls = self._host(player.PlayerContext(level=5, class_id=1))
        under_cap.load(source)
        # Quest.Var4 is STUB_DEFAULT (0) until per-instance Quest.Var* data
        # is wired (a different, still-blocked gap) -- so the `== 0` half
        # of the `or` always holds today regardless of level, exactly as
        # lua_api/quest.py's own module docstring already documents for
        # Quest.Var1-backed gates elsewhere in the corpus.
        self.assertEqual(under_cap.call("Probe"), 1)

    def test_get_item_num_from_lua_reads_the_injected_backpack(self):
        # gamedata/lua/Quest/q_gather_new.lua:205 -- `Player.GetItemNum(Quest.Var5)`.
        backpack = BackpackState(0xFF, 0, 1, (ItemAttrState(1, 2600001, 3, 0),))
        host, _calls = self._host(player.PlayerContext(backpack=backpack))
        host.load("function Probe() return Player.GetItemNum(2600001) end")
        self.assertEqual(host.call("Probe"), 3)

    def test_check_item_num_from_lua_matches_the_real_q_guildgather1_gate_shape(self):
        # gamedata/lua/Quest/q_guildgather1.lua:41 --
        # `Player.CheckItemNum(Quest.Var2,Quest.Var3)`.
        backpack = BackpackState(0xFF, 0, 1, (ItemAttrState(1, 5000, 4, 0),))
        host, _calls = self._host(player.PlayerContext(backpack=backpack))
        host.load("function Probe() return Player.CheckItemNum(5000, 4) end")
        self.assertTrue(host.call("Probe"))

    def test_check_equip_item_from_lua_matches_the_real_q_kill1_2_call_shape(self):
        # gamedata/lua/Quest/q_kill1_2.lua:14 -- `Player.CheckEquipItem(2200225)`.
        host, _calls = self._host(
            player.PlayerContext(equipped_template_ids=frozenset({2200225})))
        host.load("function Probe() return Player.CheckEquipItem(2200225) end")
        self.assertTrue(host.call("Probe"))

    def test_mob_appear_from_lua_matches_the_real_q_kill5_delete_run_call_shape(self):
        # tests/fixtures/lua_spike/q_kill5.lua's Delete_Run -- the 4 calls
        # in this fixture NOT gated behind an `if (Quest.VarN > 0)` guard
        # (grepped; see tests/test_script_lua_corpus.py's own
        # BASELINE_TOTAL_STUB_CALLS note for the 12 that ARE gated and
        # never fire under STUB_DEFAULT=0 this round):
        # `Player.MobAppear(Quest.Var13, true)`.
        store = player.InMemoryPlayerMobAppearStore()
        host, calls = self._host(
            player.PlayerContext(character_id=7), store=store)
        host.load("function Probe() return Player.MobAppear(0, true) end")
        self.assertIs(host.call("Probe"), True)
        self.assertEqual(store.get_mob_appear_flag(7, 0), True)
        self.assertTrue(any(
            c.startswith("LUA_PLAYER_REAL Player.MobAppear ") for c in calls))


class SignedStatClosureTests(unittest.TestCase):
    """``Player.AddCash`` -- the first name that can move a row EITHER way.

    Every assertion here is about which DOOR the closure picked, because
    that is the only thing the closure decides: the arithmetic belongs to
    ``lua_api.reward`` and the row belongs to ``store``.  A charge sent
    down the adding door is a free ship, and a payment sent down the
    subtracting door takes money from a player who was owed it, so both
    directions are pinned, not just the new one.
    """

    def _namespace(self, character_id=9, payout_store=None):
        from pirateforce_foundation.lua_api import spec as api_spec

        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=character_id),
            payout_store=payout_store)
        return ns, calls

    def test_a_positive_amount_goes_down_the_adding_door(self):
        """``q_guildgather1.lua:60`` -- ``Player.AddCash(Quest.Var8)``."""
        store = _RecordingPayoutStore(start=100)
        ns, calls = self._namespace(payout_store=store)
        self.assertEqual(ns["AddCash"](500), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [(9, "cash", 500)])
        self.assertTrue(any("LUA_PLAYER_GRANT Player.AddCash" in line
                            and "paid=500" in line for line in calls), calls)

    def test_a_negative_amount_goes_down_the_subtracting_door(self):
        """``q_ship.lua:50`` -- ``Player.AddCash(-Quest.Var3)``.

        THE ROUND'S POINT, in one assertion: before this change the
        argument was refused by ``_coerce_int``'s floor and the player kept
        the money AND got the ship.
        """
        store = _RecordingPayoutStore(balances={(9, "cash"): 1000})
        ns, calls = self._namespace(payout_store=store)
        self.assertEqual(ns["AddCash"](-250), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [(9, "cash", -250)])
        self.assertTrue(any("LUA_PLAYER_CHARGE Player.AddCash" in line
                            and "charged=250 balance_after=750" in line
                            for line in calls), calls)

    def test_a_lua_float_charge_is_the_same_charge(self):
        """Lua has ONE number type: ``-250`` arrives as ``-250.0``."""
        store = _RecordingPayoutStore(balances={(9, "cash"): 1000})
        ns, _calls = self._namespace(payout_store=store)
        ns["AddCash"](-250.0)
        self.assertEqual(store.calls, [(9, "cash", -250)])

    def test_a_charge_the_player_cannot_afford_moves_nothing(self):
        store = _RecordingPayoutStore(balances={(9, "cash"): 100})
        ns, calls = self._namespace(payout_store=store)
        self.assertEqual(ns["AddCash"](-250), player.STUB_DEFAULT)
        self.assertTrue(any("refused=balance_does_not_cover_it" in line
                            for line in calls), calls)

    def test_the_script_cannot_tell_a_refused_charge_from_a_paid_one(self):
        """Said out loud rather than left for someone to discover.

        Both return ``STUB_DEFAULT``, because nobody has measured what the
        game's engine returns from this name and all six corpus call sites
        use it as a statement.  ``q_ship.lua`` therefore hands over the ship
        whether or not the charge landed; closing that needs
        ``Player.GetCash`` (still stubbed) so the script's own guard works,
        the way ``q_boat_health.lua:19`` already guards with it.
        """
        rich = _RecordingPayoutStore(balances={(9, "cash"): 1000})
        poor = _RecordingPayoutStore(balances={(9, "cash"): 1})
        for store in (rich, poor):
            ns, _calls = self._namespace(payout_store=store)
            self.assertEqual(ns["AddCash"](-250), player.STUB_DEFAULT)
        self.assertEqual(rich.calls, [(9, "cash", -250)])
        self.assertEqual(poor.calls, [(9, "cash", -250)])
        self.assertEqual(poor._balances[(9, "cash")], 1)

    def test_zero_moves_nothing_and_uses_one_token_not_two(self):
        store = _RecordingPayoutStore(start=100)
        ns, calls = self._namespace(payout_store=store)
        for zero in (0, 0.0, -0.0):
            with self.subTest(zero=zero):
                ns["AddCash"](zero)
        self.assertEqual(store.calls, [])
        self.assertEqual(
            sum("refused=amount_is_zero" in line for line in calls), 3, calls)

    def test_garbage_is_a_bad_value_and_never_a_charge(self):
        store = _RecordingPayoutStore(balances={(9, "cash"): 1000})
        ns, calls = self._namespace(payout_store=store)
        for bad in (float("nan"), float("inf"), float("-inf"), -2.5, "500",
                    True, False, None, -(0x1_0000_0000)):
            with self.subTest(bad=bad):
                self.assertEqual(ns["AddCash"](bad), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertEqual(store._balances[(9, "cash")], 1000)
        self.assertTrue(any("LUA_PLAYER_BAD_VALUE" in line for line in calls),
                        calls)

    def test_wrong_arity_is_refused_before_any_door(self):
        store = _RecordingPayoutStore(balances={(9, "cash"): 1000})
        ns, _calls = self._namespace(payout_store=store)
        self.assertEqual(ns["AddCash"](), player.STUB_DEFAULT)
        self.assertEqual(ns["AddCash"](-1, -2), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])

    def test_without_a_payout_store_it_refuses_rather_than_pretending(self):
        ns, calls = self._namespace(payout_store=None)
        self.assertEqual(ns["AddCash"](-250), player.STUB_DEFAULT)
        self.assertTrue(any("refused=no_reward_store" in line
                            for line in calls), calls)

    def test_character_zero_is_the_inert_bucket_not_a_purse(self):
        store = _RecordingPayoutStore(balances={(0, "cash"): 1000})
        ns, calls = self._namespace(character_id=0, payout_store=store)
        ns["AddCash"](-250)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=no_character" in line for line in calls),
                        calls)

    def test_the_adding_names_keep_their_floor(self):
        """The asymmetry, pinned so it cannot be "tidied up" into symmetry.

        ``AddExp``/``AddSkillPoint`` have no subtracting route in
        ``SIGNED_STAT_KINDS``, so a negative reaching one of them is a
        decode fault and must stay a BAD VALUE -- never a charge nobody
        asked for.
        """
        store = _RecordingPayoutStore(balances={(9, "experience"): 1000,
                                                (9, "skill_points"): 10})
        ns, calls = self._namespace(payout_store=store)
        for name in ("AddExp", "AddSkillPoint"):
            with self.subTest(name=name):
                self.assertEqual(ns[name](-5), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertEqual(
            sum("LUA_PLAYER_BAD_VALUE" in line for line in calls), 2, calls)


class _RecordingMintStore:
    """Records ``mint_backpack_item`` calls -- the (i) half of the two-way
    test ``COO-DECISION 20260909_1312`` asked for, at the ``Player.AddItem``
    call site rather than at ``reward.mint`` directly."""

    def __init__(self):
        self.calls: list = []

    def mint_backpack_item(self, sid, character_id, item_id, quantity,
                           category):
        self.calls.append((sid, character_id, item_id, quantity, category))
        return object()


class AddItemClosureTests(unittest.TestCase):
    """``Player.AddItem`` -- the first ITEM name to leave ``STILL_STUBBED``.

    ``store.mint_backpack_item`` landed this round (LANE-DB, answering
    ``COO-DECISION 20260908_2055``), which is what makes this closure real
    rather than the ``_ITEM_STATE`` stub every other item name still is.
    The closure itself decides almost nothing (arity, coercion, which
    context field to read) -- the mint/refuse logic is
    ``lua_api.reward.mint``'s, pinned on its own in
    ``test_script_lua_api_reward.py::MintTests``.  What is pinned HERE is
    that the closure is WIRED to it with the right arguments, including the
    one this namespace adds this round: ``context.sid``.
    """

    def _namespace(self, character_id=9, sid="sess-1", store=None):
        from pirateforce_foundation.lua_api import spec as api_spec

        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=character_id, sid=sid),
            payout_store=store)
        return ns, calls

    def test_add_item_is_no_longer_a_stub(self):
        self.assertNotIn("AddItem", player.STILL_STUBBED)
        self.assertIn("AddItem", player.REAL_METHODS)

    def test_a_known_unambiguous_item_reaches_the_minter(self):
        store = _RecordingMintStore()
        ns, calls = self._namespace(store=store)
        self.assertEqual(ns["AddItem"](11, 3), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [("sess-1", 9, 11, 3, "quest")])
        self.assertTrue(any("LUA_PLAYER_MINT Player.AddItem" in line
                            for line in calls), calls)
        self.assertNotIn("LUA_API_STUB Player.AddItem", calls)

    def test_a_lua_float_pair_is_the_same_mint(self):
        store = _RecordingMintStore()
        ns, _calls = self._namespace(store=store)
        ns["AddItem"](11.0, 3.0)
        self.assertEqual(store.calls, [("sess-1", 9, 11, 3, "quest")])

    def test_without_a_payout_store_it_refuses_rather_than_pretending(self):
        ns, calls = self._namespace(store=None)
        self.assertEqual(ns["AddItem"](11, 3), player.STUB_DEFAULT)
        self.assertTrue(any("refused=no_reward_store" in line
                            for line in calls), calls)

    def test_a_store_without_the_minter_refuses_by_exact_name(self):
        class NoMinter:
            pass

        ns, calls = self._namespace(store=NoMinter())
        self.assertEqual(ns["AddItem"](11, 3), player.STUB_DEFAULT)
        self.assertTrue(any("refused=no-item-minter" in line
                            for line in calls), calls)

    def test_wrong_arity_never_reaches_the_store(self):
        store = _RecordingMintStore()
        ns, _calls = self._namespace(store=store)
        self.assertEqual(ns["AddItem"](), player.STUB_DEFAULT)
        self.assertEqual(ns["AddItem"](11), player.STUB_DEFAULT)
        self.assertEqual(ns["AddItem"](11, 3, 5), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])

    def test_garbage_arguments_never_reach_the_store(self):
        store = _RecordingMintStore()
        ns, calls = self._namespace(store=store)
        for bad_item, bad_qty in ((True, 3), ("11", 3), (11, "3"),
                                  (float("nan"), 3), (-1, 3), (11, -1)):
            with self.subTest(item=bad_item, qty=bad_qty):
                self.assertEqual(ns["AddItem"](bad_item, bad_qty),
                                 player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("LUA_PLAYER_BAD_VALUE Player.AddItem" in line
                            for line in calls), calls)

    def test_no_session_on_the_context_refuses_before_the_store(self):
        store = _RecordingMintStore()
        ns, calls = self._namespace(sid="", store=store)
        self.assertEqual(ns["AddItem"](11, 3), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=no_session" in line for line in calls),
                        calls)

    def test_character_zero_is_the_inert_bucket_not_a_player(self):
        store = _RecordingMintStore()
        ns, calls = self._namespace(character_id=0, store=store)
        ns["AddItem"](11, 3)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=no_character" in line for line in calls),
                        calls)


class SignedStatReachesARealRowTests(unittest.TestCase):
    """``AddCash`` against a real ``SQLiteStore`` on disk, both directions.

    The layer above pins which door the closure picked with a double; this
    one pins that the money actually leaves the ``characters`` row -- read
    back off the store, never from what the namespace returned.
    """

    def setUp(self):
        import tempfile
        from pathlib import Path

        from pirateforce_foundation.store import SQLiteStore

        migrations = Path(__file__).resolve().parents[1] / "migrations"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = SQLiteStore(Path(tmp.name) / "state.sqlite3", migrations)
        self.store.migrate()
        account_id = self.store.ensure_account("acct-charge")
        self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "Charge01", "charge01", "fp-charge",
            lambda selector: (b"wire", b"avatar", 4242, 0),
            _grant_home(),
        )
        self.store.write_typed_attributes(self.character.id, {"cash": 1000})

    def _namespace(self):
        from pirateforce_foundation.lua_api import spec as api_spec

        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=self.character.id),
            payout_store=self.store)
        return ns, calls

    def test_the_ship_is_paid_for_out_of_the_row(self):
        ns, calls = self._namespace()
        ns["AddCash"](-250)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(stored["cash"], 750)
        self.assertTrue(any("charged=250 balance_after=750" in line
                            for line in calls), calls)

    def test_the_reward_still_adds_to_the_same_row(self):
        ns, _calls = self._namespace()
        ns["AddCash"](500)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(stored["cash"], 1500)

    def test_a_player_who_cannot_afford_it_keeps_every_coin(self):
        ns, calls = self._namespace()
        ns["AddCash"](-4000)
        stored = self.store.read_typed_attributes(self.character.id)
        self.assertEqual(stored["cash"], 1000)
        self.assertTrue(any("refused=balance_does_not_cover_it" in line
                            for line in calls), calls)

    def test_an_unmeasured_purse_refuses_rather_than_starting_at_zero(self):
        """COO-DECISION 20260901_1059, on the subtracting side.

        A character whose ``cash`` was never written has a NULL column, and
        NULL is "nobody measured this", not "no money" -- so the charge is
        refused under its own token rather than reported as being short.
        """
        account_id = self.store.ensure_account("acct-charge-null")
        self.store.open_session(account_id)
        fresh = self.store.create_character(
            account_id, "Charge02", "charge02", "fp-charge2",
            lambda selector: (b"wire", b"avatar", 4243, 0),
            _grant_home(),
        )
        from pirateforce_foundation.lua_api import spec as api_spec

        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=fresh.id),
            payout_store=self.store)
        ns["AddCash"](-250)
        self.assertTrue(any("refused=balance_was_never_measured" in line
                            for line in calls), calls)


class SignedStatWrappedNegativeTests(unittest.TestCase):
    """pf-adversary `D1`, round `2euu94`: the sign is not always in the sign.

    ``gamedata/tables/QUESTDATA_TH__QUEST.tsv`` stores a negative ``n_VARI``
    as unsigned 32-bit two's complement.  A ``u32`` magnitude ceiling let
    those cells through as huge POSITIVE ints, so the door that exists to
    charge the player would have CREDITED 4,294,952,296 to the class-change
    quest instead of debiting 15,000.

    The cells are written out here rather than read from the bridge repo,
    because these tests must pass with no ``pf_bridge`` beside the
    checkout.  What is asserted is the RELATIONSHIP, not the constant: each
    cell is checked to be exactly ``2**32`` minus its own script's gate
    value, which is what makes it a wrapped negative rather than a number
    someone copied down.
    """

    #: (quest rows, script gate cell, the AddCash cell) from the shipped
    #: table.  Q_CLASS 3200-3204 gate on n_VARI_3 (q_class.lua:47) and pay
    #: n_VARI_4 (q_class.lua:60); Q_GUILD_BOSS2 8061-8065 gate on n_VARI_5
    #: (q_guild_boss2.lua:41) and pay n_VARI_8 (q_guild_boss2.lua:59).
    WRAPPED = [
        ("Q_CLASS 3200-3204", 15000, 4294952296),
        ("Q_GUILD_BOSS2 8061", 10000, 4294957296),
        ("Q_GUILD_BOSS2 8062", 40000, 4294927296),
        ("Q_GUILD_BOSS2 8063-8065", 50000, 4294917296),
    ]

    def test_each_cell_really_is_its_gate_wrapped(self):
        """The provenance, not just the number: 2**32 - gate == cell."""
        for label, gate, cell in self.WRAPPED:
            with self.subTest(row=label):
                self.assertEqual(cell, 2 ** 32 - gate)

    def test_a_wrapped_negative_is_refused_and_pays_nobody(self):
        store = _RecordingPayoutStore(balances={(9, "cash"): 20000})
        from pirateforce_foundation.lua_api import spec as api_spec

        for label, _gate, cell in self.WRAPPED:
            calls: list = []
            ns = player.build_namespace(
                api_spec.NAMESPACE_METHODS["Player"], calls.append,
                context=player.PlayerContext(character_id=9),
                payout_store=store)
            for value in (cell, float(cell)):
                with self.subTest(row=label, value=value):
                    self.assertEqual(ns["AddCash"](value),
                                     player.STUB_DEFAULT)
            self.assertTrue(any("LUA_PLAYER_BAD_VALUE" in line
                                for line in calls), calls)
        self.assertEqual(store.calls, [])
        self.assertEqual(store._balances[(9, "cash")], 20000)

    def test_the_ceiling_is_i32_not_u32_and_that_is_the_whole_fix(self):
        """Pinned so a later "tidy up" cannot restore the shared constant.

        ``AddExp``/``AddSkillPoint`` keep ``_MAX_GRANT_AMOUNT``: they have
        no subtracting route, so a wrapped cell reaching one of them is
        already refused by ``_coerce_int``'s floor... only if it decodes
        NEGATIVE, which it does not.  That is a real remaining gap and it
        is named in the round file, not papered over here.
        """
        self.assertEqual(player._MAX_SIGNED_STAT_MAGNITUDE, 0x7FFFFFFF)
        self.assertLess(player._MAX_SIGNED_STAT_MAGNITUDE,
                        player._MAX_GRANT_AMOUNT)
        for _label, _gate, cell in self.WRAPPED:
            self.assertGreater(cell, player._MAX_SIGNED_STAT_MAGNITUDE)

    def test_every_real_reward_magnitude_in_the_table_still_fits(self):
        """The largest cash magnitude anywhere in the table is 50,000."""
        for _label, gate, _cell in self.WRAPPED:
            self.assertLess(gate, player._MAX_SIGNED_STAT_MAGNITUDE)


class SignedStatNeedsBothDoorsTests(unittest.TestCase):
    """pf-adversary `D5`: the free ship, reached through the store's shape.

    A store with ``add_typed_attribute`` and no spend door pays this name's
    rewards and refuses its charges -- the exact outcome the round exists
    to prevent, arriving through an injected object instead of through a
    sign.  So a name that can charge refuses to pay through such a store.
    """

    class _AddOnlyStore:
        def __init__(self):
            self.calls: list = []

        def add_typed_attribute(self, character_id, column, delta):
            self.calls.append((character_id, column, delta))
            return 20000 + delta

    def _namespace(self, store):
        from pirateforce_foundation.lua_api import spec as api_spec

        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=9), payout_store=store)
        return ns, calls

    def test_an_add_only_store_pays_nothing_for_a_name_that_can_charge(self):
        store = self._AddOnlyStore()
        ns, calls = self._namespace(store)
        self.assertEqual(ns["AddCash"](5000), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=store_has_no_atomic_spend" in line
                            for line in calls), calls)

    def test_the_charge_direction_refuses_under_the_same_token(self):
        store = self._AddOnlyStore()
        ns, calls = self._namespace(store)
        self.assertEqual(ns["AddCash"](-5000), player.STUB_DEFAULT)
        self.assertEqual(store.calls, [])
        self.assertTrue(any("refused=store_has_no_atomic_spend" in line
                            for line in calls), calls)

    def test_the_add_only_names_still_pay_through_it(self):
        """The rule is per NAME, not a blanket ban on add-only stores.

        ``AddExp`` has no charging half, so an add-only store is a
        perfectly good store for it -- narrowing that too would break a
        seam round ``yfeauz`` shipped for no gain.
        """
        store = self._AddOnlyStore()
        ns, _calls = self._namespace(store)
        ns["AddExp"](250)
        self.assertEqual(store.calls, [(9, "experience", 250)])


class GetCashReadsTheColumnAddCashWritesTests(unittest.TestCase):
    """``Player.GetCash`` -- the purse READ four spending quests gate on.

    The point of the name is not the number.  It is that
    ``gamedata/lua/Quest/q_class.lua:47``
    (``if( Player.GetCash() >= (Quest.Var3) )``) was a guard that could
    never be true while the name answered ``STUB_DEFAULT``, so the shipped
    quest's own affordability check had never run once -- and
    ``lua_api.reward.charge``'s docstring names the cost of that from the
    other side: ``q_ship.lua`` charges and hands the ship over with no
    check of its own, so the SCRIPT's guard is the only thing between a
    broke player and a free ship.
    """

    def _namespace(self, store=None, character_id=9):
        from pirateforce_foundation.lua_api import spec as api_spec
        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=character_id),
            payout_store=store)
        return ns, calls

    class _ReadingStore(_RecordingPayoutStore):
        """The recording double, plus the one READ method this seam uses.

        Deliberately backed by the SAME ``_balances`` dict the writing
        doors move, so a test can charge and then read and see the two
        halves agree -- which is the whole claim: one column, two doors.
        """

        def read_typed_attributes(self, character_id: int):
            return {column: value
                    for (cid, column), value in self._balances.items()
                    if cid == character_id}

    def test_get_cash_is_no_longer_a_stub(self):
        self.assertNotIn("GetCash", player.STILL_STUBBED)
        self.assertIn("GetCash", player.REAL_METHODS)
        ns, calls = self._namespace(self._ReadingStore(balances={
            (9, "cash"): 4200}))
        self.assertEqual(ns["GetCash"](), 4200)
        self.assertFalse(any("LUA_API_STUB Player.GetCash" in line
                             for line in calls), calls)

    def test_the_read_map_is_exactly_get_cash(self):
        """Closed and one entry, the same pin ``SIGNED_STAT_KINDS`` has.

        A second name arriving here silently would be a column this lane
        reads without having said which store door writes it.
        """
        from pirateforce_foundation.lua_api import quest_criteria
        self.assertEqual(player.STAT_READ_KINDS,
                         {"GetCash": quest_criteria.KIND_CASH})

    def test_what_add_cash_wrote_is_what_get_cash_reads(self):
        """One column, two doors -- the claim in a single test.

        Not two assertions about two numbers: the balance is never
        written by the test, it is put there by ``Player.AddCash`` going
        through ``reward.grant`` and taken away by the same name going
        through ``reward.charge``.
        """
        store = self._ReadingStore(balances={(9, "cash"): 1000})
        ns, _calls = self._namespace(store)
        ns["AddCash"](500)
        self.assertEqual(ns["GetCash"](), 1500)
        ns["AddCash"](-200)
        self.assertEqual(ns["GetCash"](), 1300)

    def test_an_unmeasured_purse_stubs_out_and_says_so(self):
        """The refusal that must not look like an answer.

        ``STUB_DEFAULT`` is what the Lua comparison gets, but the log
        carries ``refused=balance_was_never_measured`` -- so a census can
        tell "this player has no money" from "nobody has ever measured
        this player's money", which ``COO-DECISION 20260901_1059``
        forbids collapsing.
        """
        from pirateforce_foundation.lua_api import reward
        store = self._ReadingStore()
        ns, calls = self._namespace(store)
        self.assertEqual(ns["GetCash"](), player.STUB_DEFAULT)
        self.assertTrue(any("refused=%s" % reward.REFUSE_UNMEASURED in line
                            for line in calls), calls)

    def test_no_payout_store_refuses_rather_than_inventing_a_purse(self):
        from pirateforce_foundation.lua_api import reward
        ns, calls = self._namespace(store=None)
        self.assertEqual(ns["GetCash"](), player.STUB_DEFAULT)
        self.assertTrue(any("refused=%s" % reward.REFUSE_NO_STORE in line
                            for line in calls), calls)

    def test_an_argument_is_a_bad_arity_not_a_read(self):
        """All seven corpus call sites are ``Player.GetCash()``, arity 0."""
        store = self._ReadingStore(balances={(9, "cash"): 4200})
        ns, calls = self._namespace(store)
        self.assertEqual(ns["GetCash"](1), player.STUB_DEFAULT)
        self.assertTrue(any("LUA_PLAYER_BAD_ARITY Player.GetCash got=1 want=0"
                            in line for line in calls), calls)

    def test_the_call_is_counted_under_its_qualified_name(self):
        calls: list = []
        from pirateforce_foundation.lua_api import spec as api_spec
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=9),
            payout_store=self._ReadingStore(balances={(9, "cash"): 1}))
        ns["GetCash"]()
        self.assertIn("Player.GetCash", ns.calls)


class GetCashReachesARealRowTests(unittest.TestCase):
    """The same name against a real ``SQLiteStore`` on disk."""

    def setUp(self):
        import tempfile
        from pathlib import Path

        from pirateforce_foundation.store import SQLiteStore

        migrations = Path(__file__).resolve().parents[1] / "migrations"
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.store = SQLiteStore(Path(tmp.name) / "state.sqlite3", migrations)
        self.store.migrate()
        account_id = self.store.ensure_account("acct-purse")
        self.store.open_session(account_id)
        self.character = self.store.create_character(
            account_id, "Purse01", "purse01", "fp-purse",
            lambda selector: (b"wire", b"avatar", 4242, 0),
            _grant_home(),
        )

    def _namespace(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        calls: list = []
        ns = player.build_namespace(
            api_spec.NAMESPACE_METHODS["Player"], calls.append,
            context=player.PlayerContext(character_id=self.character.id),
            payout_store=self.store)
        return ns, calls

    def test_a_freshly_created_character_has_no_measured_cash(self):
        """MEASURED, not assumed, and it is the reason the refusal exists.

        ``create_character`` leaves ``cash`` NULL, so the very first
        player to walk up to a class-change NPC is the unmeasured case,
        not an exotic one.
        """
        from pirateforce_foundation.lua_api import reward
        self.assertNotIn(
            "cash", self.store.read_typed_attributes(self.character.id))
        ns, calls = self._namespace()
        self.assertEqual(ns["GetCash"](), player.STUB_DEFAULT)
        self.assertTrue(any("refused=%s" % reward.REFUSE_UNMEASURED in line
                            for line in calls), calls)

    def test_the_row_on_disk_is_what_the_name_answers(self):
        self.store.write_typed_attributes(self.character.id, {"cash": 15000})
        ns, calls = self._namespace()
        self.assertEqual(ns["GetCash"](), 15000)
        self.assertTrue(any("balance=15000" in line for line in calls), calls)

    def test_a_charge_moves_the_row_and_the_next_read_sees_it(self):
        """``q_class.lua``'s two lines, end to end on a real row.

        Line 47 asks whether the purse covers 15,000; line 60 debits it
        (``n_VARI_4`` = 4294952296 = -15000, resolved to a charge by the
        signed door).  Both halves now go through the same column.
        """
        self.store.write_typed_attributes(self.character.id, {"cash": 20000})
        ns, _calls = self._namespace()
        self.assertGreaterEqual(ns["GetCash"](), 15000)
        ns["AddCash"](-15000)
        self.assertEqual(ns["GetCash"](), 5000)
        self.assertEqual(
            self.store.read_typed_attributes(self.character.id)["cash"], 5000)
