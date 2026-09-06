"""LANE-Q spike: the sandboxed Lua host runs the game's own scripts headless.

Covers the charter's round-1 deliverable (prompts/LANE-Q.md item 1) at the
two named files: load ``t_nex_t6.lua`` and ``Quest/q_kill5.lua`` with all
160 API names stubbed, run their entry points headless to completion with
no error, and prove the sandbox actually blocks io/os/require/load rather
than merely not calling them.  Fixtures are byte-for-byte copies of the two
named files from ../pf_bridge/gamedata/lua/ (verified with ``cmp`` when
vendored - see docs/SCRIPT_LANE.md) so this module needs no sibling
checkout: it is guarded only by LUPA_PACKAGE, not BRIDGE_LUA_SCRIPTS.
"""
import unittest
from pathlib import Path

from pf_preconditions import LUPA_PACKAGE

from pirateforce_foundation import script_host

FIXTURES = Path(__file__).parent / "fixtures" / "lua_spike"


@LUPA_PACKAGE.skip_unless_present()
class TwoNamedSpikeScriptsRunHeadlessTests(unittest.TestCase):
    """prompts/LANE-Q.md item 1: t_nex_t6.lua and Quest/q_kill5.lua."""

    def test_t_nex_t6_script_start_runs_to_completion(self):
        # UPDATED after Trigger.GetTriggerStatus/NextStatus became REAL
        # (lua_api/trigger.py, the round after s2fxf6): these two no longer
        # log LUA_API_STUB.  The result is unchanged and for the reason the
        # old comment already gave -- Trigger.Var1..Var7 are not API names,
        # so they still all read as STUB_DEFAULT (0) from the namespace's
        # non-API fallback, which means all six GetTriggerStatus calls ask
        # the SAME real registry about the SAME trigger id (0) and get back
        # the SAME real default (0), 0 == Var7's 0, every "~=" is false, and
        # the script takes its NextStatus branch.  This is the trivial case;
        # tests/test_script_lua_api_trigger.py proves the real gating logic
        # against six DISTINCT prerequisite triggers that are NOT all equal.
        calls = []
        host = script_host.load_script_file(FIXTURES / "t_nex_t6.lua", log=calls.append)
        result = host.call("ScriptStart")
        self.assertEqual(result, 1)
        real_lines = [c for c in calls if c.startswith("LUA_TRIGGER_REAL ")]
        self.assertEqual(len(real_lines), 7)  # 6 reads + 1 write
        self.assertEqual(calls, [c for c in calls if not c.startswith("LUA_API_STUB ")])

    def test_q_kill5_full_quest_lifecycle_runs_to_completion(self):
        calls = []
        host = script_host.load_script_file(FIXTURES / "q_kill5.lua", log=calls.append)
        for entry_point in (
            "OpenAcceptUI_Run", "OpenReportUI_Run",
            "Accept_Check", "Accept_Run",
            "Report_Check", "Report_Run",
            "Delete_Run",
        ):
            with self.subTest(entry_point=entry_point):
                self.assertTrue(host.has_function(entry_point))
                result = host.call(entry_point)
                # The four Check_/Run_ style functions explicitly `return
                # 1`; OpenAcceptUI_Run/OpenReportUI_Run have no return
                # statement at all in the source (they only call
                # Mob.ShowAnimation for a side effect) so Lua's nil comes
                # back as None - never raise either way.
                self.assertIn(result, (0, 1, None))
        called = {c.split(" ", 1)[1] for c in calls if c.startswith("LUA_API_STUB ")}
        # A genuine dynamic-dispatch check, not just "it did not crash":
        # every API name this specific script's source calls by name must
        # actually have fired through the stub, in namespaces that are not
        # each other (COO-DECISION 20260905_0947: "wired" means observed).
        self.assertEqual(called, {
            "Mob.ShowAnimation",
            "Quest.MobKillCount",
            "Quest.SetFlag",
            "Quest.CountDownTime",
            "Quest.CheckMobKillCount",
            "Quest.AddCriteriaExp",
            "Quest.AddCriteriaSkillPoint",
            "Quest.AddCriteriaCash",
            "Player.MobAppear",
        })


@LUPA_PACKAGE.skip_unless_present()
class SandboxActuallyBlocksTheBannedGlobalsTests(unittest.TestCase):
    """The charter's sandbox line, verified from inside a running script."""

    def _host(self):
        return script_host.ScriptHost(log=lambda _msg: None)

    def test_banned_globals_are_nil_not_merely_unused(self):
        host = self._host()
        host.load("function Probe() return io, os, require, load end")
        self.assertEqual(host.call("Probe"), (None, None, None, None))

    def test_every_name_on_the_blocklist_is_nil_not_just_the_famous_four(self):
        # Derived from BLOCKED_GLOBALS itself rather than a second hand-typed
        # list: pf-adversary measured that a mutant dropping loadstring,
        # loadfile, dofile, package, debug and collectgarbage from the tuple
        # left the whole module green.  debug.getregistry/setmetatable and
        # package.loadlib are escape vectors in their own right, so a
        # regression that re-exposes one must not be silent.
        host = self._host()
        for name in script_host.BLOCKED_GLOBALS:
            with self.subTest(blocked=name):
                host.load("function Probe() return %s end" % name)
                self.assertIsNone(
                    host.call("Probe"),
                    "%r is on BLOCKED_GLOBALS but a script can still see it" % name,
                )

    def test_a_returned_api_closure_cannot_be_walked_back_to_builtins(self):
        # THE escape of this round, measured by pf-adversary against the
        # commit whose whole purpose was to close the previous one:
        #   Quest.GetQuestFlag.__globals__["__builtins__"]["__import__"]("os")
        # reached __import__ and ran os.system as the server process (uid=0),
        # through a path touching neither the python table nor any blocked
        # global.  __getitem__ intercepts attribute-looking keys on the
        # NAMESPACE, so probing Quest.__class__ says nothing about the
        # CLOSURE a namespace hands back - which is a plain Python function
        # and was fully getattr-able.  This probes the closure.
        host = self._host()
        host.load(
            "function Probe()\n"
            "  local ok, err = pcall(function()\n"
            "    return Quest.GetQuestFlag.__globals__\n"
            "  end)\n"
            "  return ok, tostring(err)\n"
            "end"
        )
        ok, err = host.call("Probe")
        self.assertFalse(ok, "a script read __globals__ off an API closure")
        self.assertIn("may not read or write Python attributes", err)

    def test_the_full_import_chain_dies_at_its_first_step(self):
        host = self._host()
        host.load(
            "function Probe()\n"
            "  local ok, err = pcall(function()\n"
            "    return Quest.GetQuestFlag.__globals__['__builtins__']"
            "['__import__']('os')\n"
            "  end)\n"
            "  return ok, tostring(err)\n"
            "end"
        )
        ok, _err = host.call("Probe")
        self.assertFalse(ok, "a script imported a module from inside the sandbox")

    def test_setting_a_python_attribute_is_denied_too(self):
        # The filter is asked about writes as well as reads; a script that
        # cannot read __globals__ but could REPLACE a bound attribute would
        # still be a foothold.
        host = self._host()
        host.load(
            "function Probe()\n"
            "  local ok = pcall(function() Quest.GetQuestFlag.x = 1 end)\n"
            "  return ok\n"
            "end"
        )
        self.assertFalse(host.call("Probe"))

    def test_reaching_into_os_raises_a_lua_error_the_caller_can_catch(self):
        host = self._host()
        host.load("function Probe() return os.time() end")
        with self.assertRaises(Exception):
            host.call("Probe")

    def test_lupas_own_python_bridge_is_not_reachable_from_a_script(self):
        # The escape this sandbox nearly shipped with: lupa injects a
        # `python` table into every Lua state, and with its default
        # constructor flags that table carries eval and builtins outright.
        host = self._host()
        host.load("function Probe() return python end")
        self.assertIsNone(host.call("Probe"))

    def test_as_attrgetter_cannot_walk_out_through_a_namespace_object(self):
        # The API namespaces are live Python objects inside an untrusted
        # Lua state.  python.as_attrgetter survives register_eval=False
        # and register_builtins=False, and it flips indexing from
        # __getitem__ to getattr - which is step one of the ordinary
        # __class__/__bases__/__subclasses__ walk to the interpreter.
        # Blanking the python table is what stops it; this asserts the
        # walk actually dies rather than that the flags were passed.
        host = self._host()
        host.load(
            "function Probe()\n"
            "  local ok, err = pcall(function()\n"
            "    return python.as_attrgetter(Quest).__class__\n"
            "  end)\n"
            "  return ok, tostring(err)\n"
            "end"
        )
        ok, err = host.call("Probe")
        self.assertFalse(ok)
        self.assertIn("python", err)

    def test_indexing_a_namespace_never_yields_a_python_attribute(self):
        # Even without the python table, plain Lua indexing must not reach
        # a dunder or an internal of the stub object itself: every key that
        # is not one of that namespace's API names answers STUB_DEFAULT.
        host = self._host()
        host.load(
            "function Probe() return Quest.__class__, Quest.__dict__, "
            "Quest._methods, Quest.namespace end"
        )
        self.assertEqual(host.call("Probe"), (0, 0, 0, 0))

    def test_math_and_string_libraries_remain_available(self):
        # The sandbox blocks the specific dangerous globals, not all of Lua's
        # standard library - the scripts use math.random/string.find freely.
        host = self._host()
        host.load("function Probe() return math.floor(3.7), string.len('abc') end")
        self.assertEqual(host.call("Probe"), (3, 3))


@LUPA_PACKAGE.skip_unless_present()
class ApiNamespaceStubBehaviourTests(unittest.TestCase):
    def test_unknown_property_style_key_returns_the_safe_default_silently(self):
        calls = []
        host = script_host.ScriptHost(log=calls.append)
        host.load("function Probe() return Quest.Var1, Quest.StringVar1, Quest.Active end")
        result = host.call("Probe")
        self.assertEqual(result, (0, 0, 0))
        self.assertEqual(calls, [])  # not API surface - no LUA_API_STUB line

    def test_known_api_name_logs_exactly_once_per_call_and_returns_default(self):
        calls = []
        host = script_host.ScriptHost(log=calls.append)
        host.load("function Probe() return Quest.GetQuestFlag(5) end")
        self.assertEqual(host.call("Probe"), 0)
        self.assertEqual(calls, ["LUA_API_STUB Quest.GetQuestFlag"])

    def test_every_still_stubbed_name_is_reachable_from_every_namespace_table(self):
        # Not a sample: every qualified name the census found THAT IS STILL
        # A STUB, called for real through a live ScriptHost, must log its
        # own stub line.  The 5 Trigger.* names that became real (round
        # after s2fxf6), the 7 Instance.* names that became real (a later
        # round) and the 1 Quest.* name that became real (round after
        # 4jsydv, CheckOpenTime) are excluded here -- calling any of them
        # with a bare `()` is not a stub-reachability probe for them, it is
        # a wrong-arity call for the ones that take arguments (e.g.
        # GetTriggerStatus/SetTriggerStatus/SetLastingTime/AddKeyEvent) --
        # and their own reachability is proven exhaustively, at their real
        # arity, by tests/test_script_lua_api_trigger.py,
        # tests/test_script_lua_api_instance.py and
        # tests/test_script_lua_api_quest.py respectively.
        from pirateforce_foundation.lua_api import quest as lua_api_quest
        from pirateforce_foundation.lua_api import spec as api_spec
        from pirateforce_foundation.lua_api import trigger as lua_api_trigger
        from pirateforce_foundation.lua_api import instance as lua_api_instance

        for fn in api_spec.API_FUNCTIONS:
            if fn.namespace == "Trigger" and fn.method in lua_api_trigger.REAL_METHODS:
                continue
            if fn.namespace == "Instance" and fn.method in lua_api_instance.REAL_METHODS:
                continue
            if fn.namespace == "Quest" and fn.method in lua_api_quest.REAL_METHODS:
                continue
            with self.subTest(qualified=fn.qualified_name):
                calls = []
                host = script_host.ScriptHost(log=calls.append)
                host.load(
                    "function Probe() return %s.%s() end"
                    % (fn.namespace, fn.method)
                )
                host.call("Probe")
                self.assertEqual(calls, ["LUA_API_STUB %s" % fn.qualified_name])

    def test_the_5_real_trigger_names_are_excluded_above_not_forgotten(self):
        # A regression guard on the exclusion itself: if REAL_METHODS ever
        # grew or shrank without the corpus's own 17-name Trigger table
        # changing, this fails loudly instead of the test above silently
        # covering fewer names than it used to.
        from pirateforce_foundation.lua_api import trigger as lua_api_trigger

        self.assertEqual(lua_api_trigger.REAL_METHODS, frozenset({
            "GetTriggerStatus", "GetTeiggerStatus", "SetStatus",
            "NextStatus", "SetTriggerStatus",
        }))

    def test_the_9_real_instance_names_are_excluded_above_not_forgotten(self):
        # Same regression guard as above, for Instance.*'s own real set.
        # Instance.* reached 9/9 real in round vmm7vf (AddBonusPoint/
        # AddBonusReward joined as pure invocation counters) -- this guard
        # was not updated in that round, which is exactly the silent-drift
        # failure mode it exists to catch turned on its own author.
        from pirateforce_foundation.lua_api import instance as lua_api_instance

        self.assertEqual(lua_api_instance.REAL_METHODS, frozenset({
            "GetInstanceID", "GetInstanceId", "GetLastingTime",
            "SetLastingTime", "AddKeyEvent", "RemoveKeyEvent",
            "CallScoreCount", "AddBonusPoint", "AddBonusReward",
        }))

    def test_the_1_real_quest_name_is_excluded_above_not_forgotten(self):
        # Same regression shape as the Trigger guard above, for Quest's own
        # single real name.
        from pirateforce_foundation.lua_api import quest as lua_api_quest

        self.assertEqual(lua_api_quest.REAL_METHODS, frozenset({"CheckOpenTime"}))

    def test_writing_into_a_namespace_table_is_discarded_not_a_crash(self):
        host = script_host.ScriptHost(log=lambda _msg: None)
        host.load("function Probe() Quest.Var1 = 42; return Quest.Var1 end")
        # The write is accepted and silently discarded (see ApiNamespaceStub
        # docstring): a stub-stage read-back still answers STUB_DEFAULT, not
        # the value the script just "set".
        self.assertEqual(host.call("Probe"), 0)


@LUPA_PACKAGE.skip_unless_present()
class FailClosedLoadingTests(unittest.TestCase):
    """One bad script must never take a boot, or the loader loop, down."""

    def test_a_syntax_error_is_caught_not_raised(self):
        with self.assertRaises(Exception):
            # Loading directly (not through load_corpus) DOES raise - the
            # fail-closed catch lives in load_corpus, exercised below, so a
            # caller who wants the low-level behaviour still gets a real
            # exception instead of a silently swallowed one.
            script_host.ScriptHost(log=lambda _m: None).load("function( -- broken")

    def test_load_corpus_catches_a_broken_script_and_keeps_going(self, tmp_dir=None):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good_one.lua").write_text("function ScriptStart() return 1 end")
            (root / "broken_one.lua").write_text("function( -- syntax error, no end")
            (root / "good_two.lua").write_text("function ScriptStart() return 1 end")
            log_lines = []
            report = script_host.load_corpus(root, log=log_lines.append)
            self.assertEqual(report.total, 3)
            self.assertEqual(report.ok, 2)
            self.assertEqual(report.failed_paths, ["broken_one.lua"])
            self.assertTrue(
                any(line.startswith("LUA_SCRIPT broken_one.lua ERR ") for line in log_lines),
                log_lines,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
