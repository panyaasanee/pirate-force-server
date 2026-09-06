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
        ns, calls = self._namespace()
        self.assertEqual(ns["AddItem"](1, 2), player.STUB_DEFAULT)
        self.assertEqual(calls, ["LUA_API_STUB Player.AddItem"])

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


@LUPA_PACKAGE.skip_unless_present()
class RealPlayerLuaIntegrationTests(unittest.TestCase):
    """The same context checks, driven from real Lua through a ScriptHost."""

    def _host(self, context=None, store=None):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(
            log=calls.append, player_context=context, player_store=store)
        return host, calls

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
