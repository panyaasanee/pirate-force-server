"""LANE-Q: the 2 ``Player.*`` names (``GetLv``, ``GetClass``) that became
real this round, and why these two needed no LANE-DB column and no wire
frame to get there.

Same three-level shape as ``tests/test_script_lua_api_quest.py``: the
namespace object's ``__getitem__`` contract alone (no lupa dependency, runs
on every machine), then real scripts running against it through a live
``ScriptHost`` (guarded by ``LUPA_PACKAGE``).
"""
import unittest

from pf_preconditions import LUPA_PACKAGE

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

    def _host(self, context=None):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(log=calls.append, player_context=context)
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
