"""LANE-Q: the 10 ``Quest.*`` names real today -- ``CheckOpenTime`` (round
4jsydv/s2fxf6 lineage) plus the 9 flag/counter/daily-stamp names
COO-DECISION ``20260906_1846`` ("flag-quest-state") added this round -- and
why each needed no wire frame and, per the module docstring, no LANE-DB
column YET (a CORE-REQUEST asks for one; :class:`quest.InMemoryQuestStateStore`
is the inert stand-in until it lands).

Same three-level shape as ``tests/test_script_lua_api_trigger.py``: the pure
function alone (no lupa dependency, runs on every machine), the namespace
object's ``__getitem__`` contract (still no Lua), and real scripts running
against it through a live ``ScriptHost`` (guarded by ``LUPA_PACKAGE``) or the
actual shipped corpus file (guarded by the composite ``LUA_CORPUS_RUNNABLE``).
"""
import unittest
from datetime import datetime

from pf_preconditions import LUA_CORPUS_RUNNABLE, LUPA_PACKAGE, SIBLING

from pirateforce_foundation.lua_api import quest


def _clock_at(hour, minute, day=6):
    fixed = datetime(2026, 9, day, hour, minute)
    return lambda: fixed


class RealQuestNamespaceTests(unittest.TestCase):
    """The ``__getitem__``/``__setitem__`` contract, without a Lua state."""

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Quest"]
        calls = []
        ns = quest.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_current_time_inside_a_same_day_window_is_true(self):
        ns, calls = self._namespace(clock=_clock_at(9, 30))
        self.assertTrue(ns["CheckOpenTime"](900, 1000))
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].startswith("LUA_QUEST_REAL Quest.CheckOpenTime "))

    def test_current_time_outside_a_same_day_window_is_false(self):
        ns, _calls = self._namespace(clock=_clock_at(11, 0))
        self.assertFalse(ns["CheckOpenTime"](900, 1000))

    def test_window_boundaries_are_inclusive_at_both_ends(self):
        at_start, _ = self._namespace(clock=_clock_at(9, 0))
        self.assertTrue(at_start["CheckOpenTime"](900, 1000))
        at_end, _ = self._namespace(clock=_clock_at(10, 0))
        self.assertTrue(at_end["CheckOpenTime"](900, 1000))
        one_minute_early, _ = self._namespace(clock=_clock_at(8, 59))
        self.assertFalse(one_minute_early["CheckOpenTime"](900, 1000))
        one_minute_late, _ = self._namespace(clock=_clock_at(10, 1))
        self.assertFalse(one_minute_late["CheckOpenTime"](900, 1000))

    def test_a_window_that_crosses_midnight_wraps(self):
        # A SYNTHETIC single-call combination -- not itself a call site in
        # the corpus (see lua_api/quest.py's _in_window docstring: every
        # real q_sea_join.lua window is its own same-day call, the chain as
        # a whole crosses midnight but no single call's two arguments do).
        # Built from q_sea_join.lua's own literal values (2330, and 0030's
        # Lua-truncated decimal 30) to exercise the wrap branch the
        # structural completeness choice added, against real numbers from
        # the corpus rather than invented ones.
        after_midnight, _ = self._namespace(clock=_clock_at(0, 45))
        self.assertTrue(after_midnight["CheckOpenTime"](2330, 55))
        before_midnight, _ = self._namespace(clock=_clock_at(23, 40))
        self.assertTrue(before_midnight["CheckOpenTime"](2330, 55))
        outside, _ = self._namespace(clock=_clock_at(12, 0))
        self.assertFalse(outside["CheckOpenTime"](2330, 55))

    def test_wrong_arity_degrades_safely_instead_of_raising(self):
        # Every one of the 9 real call sites in the corpus uses exactly 2
        # args (grepped, api_spec.tsv's own arity_min=arity_max=2) -- this
        # is the same "untrusted input must never crash the host" guard
        # lua_api/trigger.py's real closures already carry.
        ns, calls = self._namespace(clock=_clock_at(9, 30))
        for args in ((), (900,), (900, 1000, 1)):
            with self.subTest(argc=len(args)):
                calls.clear()
                result = ns["CheckOpenTime"](*args)
                self.assertEqual(result, quest.STUB_DEFAULT)
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0].startswith(
                    "LUA_QUEST_BAD_ARITY Quest.CheckOpenTime "), calls)

    def test_bad_input_values_are_refused_not_guessed(self):
        ns, _calls = self._namespace(clock=_clock_at(9, 30))
        cases = (
            ("nine", 1000),      # not a number at all
            (900, "ten"),
            (True, 1000),        # bool is an int in Python; refused anyway
            (900, True),
            (float("nan"), 1000),
            (900, float("inf")),
            (900.5, 1000),       # fractional float: no real call site has one
            (2500, 1000),        # hour 25 does not exist
            (900, 9999),         # minute 99 does not exist
            (-5, 1000),
        )
        for bad_start, bad_end in cases:
            with self.subTest(start=bad_start, end=bad_end):
                self.assertFalse(ns["CheckOpenTime"](bad_start, bad_end))

    def test_a_lua_style_whole_number_float_is_accepted(self):
        # lupa hands every Lua number back as a float; 900.0/1000.0 is what
        # CheckOpenTime(900,1000) actually receives at a real call site.
        ns, _calls = self._namespace(clock=_clock_at(9, 30))
        self.assertTrue(ns["CheckOpenTime"](900.0, 1000.0))

    def test_a_still_stubbed_method_logs_lua_api_stub_exactly_like_before(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["GetWeekDay"](), quest.STUB_DEFAULT)
        self.assertEqual(calls, ["LUA_API_STUB Quest.GetWeekDay"])

    def test_every_still_stubbed_name_is_reachable_and_logs_its_own_line(self):
        for name in quest.STILL_STUBBED:
            with self.subTest(method=name):
                ns, calls = self._namespace()
                ns[name]()
                self.assertEqual(calls, ["LUA_API_STUB Quest.%s" % name])

    def test_still_stubbed_plus_real_accounts_for_all_25_names(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Quest"]
        self.assertEqual(len(methods), 25)
        self.assertEqual(set(quest.STILL_STUBBED) | quest.REAL_METHODS, set(methods))
        self.assertEqual(set(quest.STILL_STUBBED) & quest.REAL_METHODS, set())

    def test_a_non_api_key_returns_the_stub_default_silently(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["Var1"], quest.STUB_DEFAULT)
        self.assertEqual(calls, [])

    def test_writing_into_the_namespace_is_accepted_and_discarded(self):
        ns, _calls = self._namespace()
        self.assertIsNone(ns.__setitem__("Var1", 42))

    def test_default_clock_reads_the_bangkok_timezone(self):
        # Not a value assertion (today's actual minute would make this test
        # flaky by construction) -- just that the default clock this
        # namespace falls back to when nothing is injected is genuinely
        # wired to a timezone, and to the one this project's other
        # timestamps already use, not silently naive or UTC.
        now = quest._server_clock()
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset().total_seconds(), 7 * 3600)

    @staticmethod
    def _always_zoneinfo_not_found(key):
        raise quest.ZoneInfoNotFoundError(key)

    def test_default_clock_falls_back_to_a_fixed_offset_without_tzdata(self):
        # Reproduces pirate-force-server#900's own gate failure (run
        # 34003119697): on an interpreter/platform whose zoneinfo has no
        # IANA database for "Asia/Bangkok" (Windows without the `tzdata`
        # PyPI package -- this repo pins none), ZoneInfo(...) raises
        # ZoneInfoNotFoundError. Simulated on any platform by monkeypatching
        # the module's own ZoneInfo lookup itself (SERVER_TIMEZONE_NAME
        # stays "Asia/Bangkok" -- the fallback below is keyed to that exact
        # name, see test_unresolvable_non_bangkok_zone_fails_loud_instead_of_guessing).
        original = quest.ZoneInfo
        quest.ZoneInfo = self._always_zoneinfo_not_found
        try:
            now = quest._server_clock()
        finally:
            quest.ZoneInfo = original
        self.assertIsNotNone(now.tzinfo)
        self.assertEqual(now.utcoffset().total_seconds(), 7 * 3600)

    def test_unresolvable_non_bangkok_zone_fails_loud_instead_of_guessing(self):
        # pf-adversary (round ksp5d3): catching ZoneInfoNotFoundError
        # unconditionally would silently substitute Bangkok's UTC+7 for ANY
        # zone name that later replaced SERVER_TIMEZONE_NAME and also failed
        # to resolve -- e.g. a future move to "Asia/Tokyo" (UTC+9) deployed
        # to the same tzdata-less platform would then read 2 hours wrong
        # with no error. _server_clock must re-raise rather than reuse
        # Bangkok's offset for a zone it has no verified fixed-offset
        # equivalent for.
        original_zoneinfo = quest.ZoneInfo
        original_name = quest.SERVER_TIMEZONE_NAME
        quest.ZoneInfo = self._always_zoneinfo_not_found
        quest.SERVER_TIMEZONE_NAME = "Asia/Tokyo"
        try:
            with self.assertRaises(quest.ZoneInfoNotFoundError):
                quest._server_clock()
        finally:
            quest.ZoneInfo = original_zoneinfo
            quest.SERVER_TIMEZONE_NAME = original_name


class QuestFlagAndCounterTests(unittest.TestCase):
    """The 9 flag/counter/daily-stamp names, no lupa dependency.

    Uses ``quest.InMemoryQuestStateStore`` directly (the default
    ``build_namespace`` falls back to) rather than a fake -- it IS the
    seam :class:`quest.QuestStateStore` names, just not the production
    persistent implementation; see its own docstring.
    """

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Quest"]
        calls = []
        ns = quest.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_quest_status_constants_are_distinct_small_ints(self):
        # The module docstring's own two-script derivation: None=0 (an
        # unset flag reads back as None), Active=1 (t_opnq_t1.lua/t_clsq.lua
        # cross-script correlation), Finish=2 (free choice, only required
        # to be distinct).
        ns, _calls = self._namespace()
        self.assertEqual(ns["None"], 0)
        self.assertEqual(ns["Active"], 1)
        self.assertEqual(ns["Finish"], 2)
        self.assertEqual(len({ns["None"], ns["Active"], ns["Finish"]}), 3)

    def test_a_never_set_flag_reads_back_as_none_not_a_kind_of_missing(self):
        ns, _calls = self._namespace(context=quest.QuestContext(1, 100))
        self.assertEqual(ns["GetQuestFlag"](999), quest.QUEST_NONE)
        self.assertEqual(ns["GetFlag"](), quest.QUEST_NONE)

    def test_set_flag_writes_the_current_quest_get_flag_reads_it_back(self):
        ns, calls = self._namespace(context=quest.QuestContext(1, 100))
        self.assertEqual(ns["SetFlag"](quest.QUEST_ACTIVE), quest.QUEST_ACTIVE)
        self.assertEqual(ns["GetFlag"](), quest.QUEST_ACTIVE)
        self.assertTrue(any(c.startswith("LUA_QUEST_REAL Quest.SetFlag ") for c in calls))
        # SetFlag never takes a quest id -- it can only ever affect the
        # CURRENT quest, unlike SetQuestFlag below.
        other, _ = self._namespace(context=quest.QuestContext(1, 200))
        self.assertEqual(other["GetFlag"](), quest.QUEST_NONE)

    def test_set_quest_flag_writes_an_arbitrary_quest_get_quest_flag_reads_it(self):
        # The one name in this group callable from a Trigger script, not
        # bound to "the current quest" -- t_exch&setq_q1.lua's own call
        # shape: Quest.SetQuestFlag(Trigger.Var7, Trigger.Var8).
        ns, _calls = self._namespace(context=quest.QuestContext(1, 100))
        self.assertEqual(ns["SetQuestFlag"](555, quest.QUEST_FINISH), quest.QUEST_FINISH)
        self.assertEqual(ns["GetQuestFlag"](555), quest.QUEST_FINISH)
        # The CURRENT quest (100) is untouched by a SetQuestFlag on quest 555.
        self.assertEqual(ns["GetFlag"](), quest.QUEST_NONE)

    def test_two_characters_never_see_each_others_flags(self):
        store = quest.InMemoryQuestStateStore()
        alice, _ = self._namespace(context=quest.QuestContext(1, 100), store=store)
        bob, _ = self._namespace(context=quest.QuestContext(2, 100), store=store)
        alice["SetFlag"](quest.QUEST_ACTIVE)
        self.assertEqual(alice["GetFlag"](), quest.QUEST_ACTIVE)
        self.assertEqual(bob["GetFlag"](), quest.QUEST_NONE)

    def test_flag_wrong_arity_degrades_safely(self):
        ns, calls = self._namespace()
        for name, args in (("GetQuestFlag", ()), ("SetFlag", ()),
                           ("SetQuestFlag", (1,)), ("GetFlag", (1,))):
            with self.subTest(method=name):
                calls.clear()
                self.assertEqual(ns[name](*args), quest.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith("LUA_QUEST_BAD_ARITY Quest.%s " % name))

    def test_mob_kill_count_registers_progress_at_zero(self):
        ns, calls = self._namespace(context=quest.QuestContext(1, 100))
        ns["MobKillCount"](42, 5)
        self.assertEqual(ns["GetMobKillCount"](42), 0)
        self.assertFalse(ns["CheckMobKillCount"](42, 5))
        self.assertTrue(any(c.startswith("LUA_QUEST_REAL Quest.MobKillCount ") for c in calls))

    def test_check_mob_kill_count_compares_the_stored_progress_to_the_argument(self):
        # MobKillCount does not persist the target (module docstring) -- the
        # script re-supplies it to CheckMobKillCount every time, exactly
        # like every measured corpus call site does.
        store = quest.InMemoryQuestStateStore()
        ns, _ = self._namespace(context=quest.QuestContext(1, 100), store=store)
        ns["MobKillCount"](42, 5)
        store.set_quest_counter(1, 100, "42", 5)  # simulate a future kill hook
        self.assertTrue(ns["CheckMobKillCount"](42, 5))
        self.assertFalse(ns["CheckMobKillCount"](42, 6))

    def test_get_mob_kill_count_of_an_unregistered_mob_is_the_stub_default(self):
        ns, _calls = self._namespace(context=quest.QuestContext(1, 100))
        self.assertEqual(ns["GetMobKillCount"](999), quest.STUB_DEFAULT)

    def test_two_mobs_in_the_same_quest_track_independently(self):
        # q_kill5.lua's own Accept_Run: two MobKillCount calls for two
        # different mobs in the same quest instance, module docstring.
        store = quest.InMemoryQuestStateStore()
        ns, _ = self._namespace(context=quest.QuestContext(1, 100), store=store)
        ns["MobKillCount"](1, 3)
        ns["MobKillCount"](2, 5)
        store.set_quest_counter(1, 100, "1", 3)
        self.assertTrue(ns["CheckMobKillCount"](1, 3))
        self.assertFalse(ns["CheckMobKillCount"](2, 5))

    def test_mob_kill_count_bad_args_refuse_not_guess(self):
        ns, calls = self._namespace()
        for name, args in (("MobKillCount", (1,)), ("CheckMobKillCount", ()),
                           ("GetMobKillCount", ())):
            with self.subTest(method=name):
                calls.clear()
                self.assertEqual(ns[name](*args), quest.STUB_DEFAULT)
        self.assertEqual(ns["MobKillCount"]("nope", 5), quest.STUB_DEFAULT)
        self.assertFalse(ns["CheckMobKillCount"]("nope", 5))

    def test_can_report_daily_quest_is_true_until_reported_then_false_same_day(self):
        ns, _calls = self._namespace(
            context=quest.QuestContext(1, 100), clock=_clock_at(10, 0))
        self.assertTrue(ns["CanReportDailyQuest"]())
        ns["ReportDailyQuest"]()
        self.assertFalse(ns["CanReportDailyQuest"]())

    def test_can_report_daily_quest_is_true_again_the_next_day(self):
        store = quest.InMemoryQuestStateStore()
        day1, _ = self._namespace(
            context=quest.QuestContext(1, 100), store=store, clock=_clock_at(23, 0, day=6))
        day1["ReportDailyQuest"]()
        day2, _ = self._namespace(
            context=quest.QuestContext(1, 100), store=store, clock=_clock_at(0, 5, day=7))
        self.assertTrue(day2["CanReportDailyQuest"]())

    def test_daily_report_is_per_quest_not_shared_across_quests(self):
        store = quest.InMemoryQuestStateStore()
        quest_a, _ = self._namespace(
            context=quest.QuestContext(1, 100), store=store, clock=_clock_at(10, 0))
        quest_b, _ = self._namespace(
            context=quest.QuestContext(1, 200), store=store, clock=_clock_at(10, 0))
        quest_a["ReportDailyQuest"]()
        self.assertFalse(quest_a["CanReportDailyQuest"]())
        self.assertTrue(quest_b["CanReportDailyQuest"]())


@LUPA_PACKAGE.skip_unless_present()
class RealQuestLuaIntegrationTests(unittest.TestCase):
    """The same clock check, driven from real Lua through a ScriptHost."""

    def _host(self, clock):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(log=calls.append, quest_clock=clock)
        return host, calls

    def test_check_open_time_from_lua_reads_the_injected_clock(self):
        host, calls = self._host(_clock_at(9, 30))
        host.load("function Probe() return Quest.CheckOpenTime(900, 1000) end")
        self.assertTrue(host.call("Probe"))
        self.assertTrue(any(c.startswith("LUA_QUEST_REAL ") for c in calls))

    def test_the_real_q_sea_join_accept_run_window_chain_is_real_now(self):
        # gamedata/lua/Quest/q_sea_join.lua's own Accept_Run: seven chained
        # Quest.CheckOpenTime windows, or'd together, gating
        # Player.BookBattleField vs. Player.ShowMessage(890).  Reproduced
        # inline at the exact literal windows the shipped script uses
        # (grepped, not invented) rather than vendoring a third fixture
        # file -- same choice round 456vso made for its own six-gate proof
        # of Trigger.NextStatus/GetTriggerStatus.
        source = """
        function Probe()
          if Quest.CheckOpenTime(1930,1955) or
          Quest.CheckOpenTime(2030,2055) or
          Quest.CheckOpenTime(2130,2155) or
          Quest.CheckOpenTime(2230,2255) or
          Quest.CheckOpenTime(2330,2355) or
          Quest.CheckOpenTime(0030,0055) or
          Quest.CheckOpenTime(0130,0155) then
            return 1
          else
            return 0
          end
        end
        """
        inside, _calls_inside = self._host(_clock_at(0, 45))
        inside.load(source)
        self.assertEqual(inside.call("Probe"), 1)

        outside, calls_outside = self._host(_clock_at(12, 0))
        outside.load(source)
        self.assertEqual(outside.call("Probe"), 0)
        # None of the seven windows contains noon, so the `or` chain cannot
        # short-circuit early -- proves every one is genuinely evaluated
        # against the injected clock, not silently skipped.
        real_lines = [c for c in calls_outside if c.startswith("LUA_QUEST_REAL ")]
        self.assertEqual(len(real_lines), 7)


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class RealQuestAgainstTheShippedFileTests(unittest.TestCase):
    """The actual gamedata/lua/Quest/q_con5.lua file, not a copy.

    NOT q_sea_join.lua, MEASURED WHY NOT.  A first draft of this test used
    q_sea_join.lua's Accept_Run (the seven-window chain the module
    docstring describes) and got 0 real calls: that function's OWN first
    line is ``if Player.CheckBuff(9903) then ... else <the chain> end``,
    and ``Player.CheckBuff`` is still a stub returning
    ``script_host.STUB_DEFAULT`` (0) -- which is TRUTHY in Lua (only
    ``nil``/``false`` are falsy), so the stubbed condition always takes the
    ``then`` branch and the ``else`` branch holding every ``CheckOpenTime``
    call never runs.  This is a real, reproducible property of running a
    real script against today's stub coverage, not a bug in this test or in
    ``CheckOpenTime`` -- q_con5.lua's ``Accept_Check`` reaches its own
    ``CheckOpenTime`` call with no such gate in front of it, so it is used
    here instead.
    """

    def test_the_shipped_file_s_accept_check_calls_check_open_time_for_real(self):
        from pirateforce_foundation import script_host

        path = SIBLING / "pf_bridge" / "gamedata" / "lua" / "Quest" / "q_con5.lua"
        calls = []
        host = script_host.load_script_file(
            path, log=calls.append, quest_clock=_clock_at(0, 45))
        # Accept_Check's own gate: `Quest.Var1 == 0` reads STUB_DEFAULT (0)
        # and is true, so Lua's `or` short-circuits before GetQuestFlag is
        # ever reached; `Quest.CheckOpenTime(Quest.Var3, Quest.Var4)` --
        # also STUB_DEFAULT, decoding to the single-minute window
        # [00:00,00:00] -- is what this call actually exercises.
        result = host.call("Accept_Check")
        self.assertEqual(calls, [
            "LUA_QUEST_REAL Quest.CheckOpenTime start=0 end=0 now_minutes=45 result=False"
        ])
        # at 00:45 the window [00:00,00:00] does not contain the clock, so
        # CheckOpenTime is False, `False == false` is true in Lua, and the
        # REAL source's own branch returns 1 -- not a hardcoded result.
        self.assertEqual(result, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
