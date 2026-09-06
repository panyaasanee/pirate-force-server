"""LANE-Q: the 5 ``Trigger.*`` names that became real this round.

Covers ``lua_api/trigger.py`` at three levels: the registry alone (no Lua,
no lupa dependency -- these tests run on every machine), the namespace
object's ``__getitem__`` contract (still no Lua), and a real script running
against it through a live ``ScriptHost`` (guarded by ``LUPA_PACKAGE``,
same as the rest of ``tests/test_script_*``).
"""
import threading
import unittest
import unittest.mock

from pf_preconditions import LUPA_PACKAGE

from pirateforce_foundation.lua_api import trigger


class TriggerStatusRegistryTests(unittest.TestCase):
    """No lupa needed: this is plain Python state, like world_scene_registry."""

    def test_unknown_trigger_reads_as_the_stub_default(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.get_status("bg0001", 42), trigger.STUB_DEFAULT)

    def test_set_then_get_round_trips(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, 7), 7)
        self.assertEqual(reg.get_status("bg0001", 1), 7)

    def test_next_status_advances_by_exactly_one_from_the_default(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.next_status("bg0001", 1), 1)
        self.assertEqual(reg.next_status("bg0001", 1), 2)
        self.assertEqual(reg.next_status("bg0001", 1), 3)

    def test_two_scenes_never_share_one_trigger_id(self):
        reg = trigger.TriggerStatusRegistry()
        reg.set_status("bg0001", 1, 9)
        self.assertEqual(reg.get_status("bg0002", 1), trigger.STUB_DEFAULT)

    def test_scene_name_is_case_folded_like_every_other_book_in_this_project(self):
        reg = trigger.TriggerStatusRegistry()
        reg.set_status("Bg0002", 5, 3)
        self.assertEqual(reg.get_status("bg0002", 5), 3)

    def test_a_bad_scene_refuses_the_write_and_reads_back_the_stub_default(self):
        reg = trigger.TriggerStatusRegistry()
        # "" is refused by mob_loot._require_scene (REFUSE_SCENE_NOT_A_SCENE)
        # -- the exact landmine DEFAULT_CONTEXT's own docstring warns about.
        self.assertEqual(reg.set_status("", 1, 5), trigger.STUB_DEFAULT)
        self.assertEqual(reg.get_status("", 1), trigger.STUB_DEFAULT)

    def test_a_non_int_status_is_refused_not_coerced(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, "seven"), trigger.STUB_DEFAULT)
        self.assertEqual(reg.get_status("bg0001", 1), trigger.STUB_DEFAULT)

    def test_a_bool_status_is_refused_not_treated_as_zero_or_one(self):
        # True is an int in Python; a registry that accepted it would let a
        # script mistake a truthy Lua value for a real status literal.
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, True), trigger.STUB_DEFAULT)

    def test_a_lua_style_float_that_is_a_whole_number_is_accepted(self):
        # lupa hands every Lua number back as a Python float; 3.0 is what
        # SetStatus(3) actually receives at the real call site.
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, 3.0), 3)
        self.assertEqual(reg.get_status("bg0001", 1.0), 3)

    def test_a_fractional_float_status_is_refused(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, 3.5), trigger.STUB_DEFAULT)

    def test_nan_and_infinite_status_are_refused(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, float("nan")), trigger.STUB_DEFAULT)
        self.assertEqual(reg.set_status("bg0001", 1, float("inf")), trigger.STUB_DEFAULT)

    def test_a_negative_status_is_refused(self):
        reg = trigger.TriggerStatusRegistry()
        self.assertEqual(reg.set_status("bg0001", 1, -1), trigger.STUB_DEFAULT)

    def test_per_scene_cap_refuses_a_new_trigger_but_keeps_existing_ones_working(self):
        reg = trigger.TriggerStatusRegistry(triggers_per_scene=2)
        reg.set_status("bg0001", 1, 1)
        reg.set_status("bg0001", 2, 1)
        self.assertEqual(reg.set_status("bg0001", 3, 1), trigger.STUB_DEFAULT)
        self.assertEqual(reg.get_status("bg0001", 3), trigger.STUB_DEFAULT)
        # existing rows are untouched by the refusal
        self.assertEqual(reg.get_status("bg0001", 1), 1)
        self.assertEqual(reg.set_status("bg0001", 1, 5), 5)

    def test_total_scenes_cap_refuses_a_new_scene_but_keeps_existing_ones_working(self):
        reg = trigger.TriggerStatusRegistry(scenes=1)
        reg.set_status("bg0001", 1, 1)
        self.assertEqual(reg.set_status("bg0002", 1, 1), trigger.STUB_DEFAULT)
        self.assertEqual(reg.get_status("bg0001", 1), 1)

    def test_concurrent_next_status_on_one_trigger_never_loses_a_step(self):
        # A statistical sanity check, not the proof -- see the deterministic
        # test right below.  pf-adversary (this round) measured that THIS
        # test alone gives zero actual protection: removing next_status's
        # outer lock (reading and writing under two separate acquisitions
        # instead of one) still passes it every time under CPython's normal
        # scheduler, because each get_status/set_status call is too fast
        # for the interpreter to switch threads inside the gap.  Kept as a
        # real-world sanity check (it DOES pass on correct code, at real
        # thread counts, with no mocking), not as the regression guard.
        reg = trigger.TriggerStatusRegistry()
        iterations = 200

        def bump():
            for _ in range(iterations):
                reg.next_status("bg0001", 1)

        threads = [threading.Thread(target=bump) for _ in range(4)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        self.assertEqual(reg.get_status("bg0001", 1), iterations * len(threads))

    def test_next_status_holds_the_lock_for_its_whole_read_modify_write(self):
        # THE deterministic regression guard for the mutant named above,
        # timing-independent: pause a next_status call (in a background
        # thread) right after its internal read, then, from THIS thread,
        # try to acquire the registry's own lock with a short timeout.  If
        # next_status wraps its read and write in one lock acquisition (an
        # RLock, exclusive across threads), that acquire attempt MUST fail
        # -- the lock is still held.  If a future edit split next_status
        # into two separate lock acquisitions (get_status's own, then
        # set_status's own, with a gap between), this thread's acquire
        # would succeed while the background thread is paused mid-gap, and
        # the assertion below catches that directly rather than hoping a
        # race manifests statistically.
        reg = trigger.TriggerStatusRegistry()
        reg.set_status("bg0001", 1, 10)
        original_get_status = trigger.TriggerStatusRegistry.get_status
        paused_after_read = threading.Event()
        release_reader = threading.Event()

        def paused_get_status(self, scene, trigger_id):
            value = original_get_status(self, scene, trigger_id)
            paused_after_read.set()
            release_reader.wait(timeout=5)
            return value

        with unittest.mock.patch.object(
                trigger.TriggerStatusRegistry, "get_status", paused_get_status):
            worker = threading.Thread(
                target=reg.next_status, args=("bg0001", 1))
            worker.start()
            self.assertTrue(
                paused_after_read.wait(timeout=5),
                "next_status never reached its paused read")
            lock_was_free = reg._lock.acquire(timeout=0.2)
            if lock_was_free:
                reg._lock.release()
            release_reader.set()
            worker.join(timeout=5)

        self.assertFalse(
            lock_was_free,
            "the registry's lock was free between next_status's read and "
            "write -- a second caller could interleave here and lose a step")
        self.assertEqual(reg.get_status("bg0001", 1), 11)

    def test_a_non_positive_triggers_per_scene_cap_is_refused_at_construction(self):
        # The one door on this class that IS allowed to raise -- a caller
        # (test/production code) programming error, never reachable from a
        # script.  Named explicitly because an earlier draft's class
        # docstring claimed "never raises" without this carve-out
        # (pf-adversary, this round).
        with self.assertRaises(ValueError):
            trigger.TriggerStatusRegistry(triggers_per_scene=0)
        with self.assertRaises(ValueError):
            trigger.TriggerStatusRegistry(triggers_per_scene=-1)

    def test_a_non_positive_scenes_cap_is_refused_at_construction(self):
        with self.assertRaises(ValueError):
            trigger.TriggerStatusRegistry(scenes=0)
        with self.assertRaises(ValueError):
            trigger.TriggerStatusRegistry(scenes=True)  # bool is an int; refused anyway

    def test_install_and_accessor_hand_back_the_same_process_singleton(self):
        first = trigger.trigger_status_registry()
        second = trigger.trigger_status_registry()
        self.assertIs(first, second)
        fresh = trigger.TriggerStatusRegistry()
        self.assertIs(trigger.install_trigger_status_registry(fresh), fresh)
        self.assertIs(trigger.trigger_status_registry(), fresh)
        # restore, so no other test in this process sees a stub registry
        # installed as "the world" by this one.
        trigger.install_trigger_status_registry(trigger.TriggerStatusRegistry())

    def test_install_refuses_anything_that_is_not_a_registry(self):
        with self.assertRaises(ValueError):
            trigger.install_trigger_status_registry("not a registry")


class RealTriggerNamespaceTests(unittest.TestCase):
    """The ``__getitem__``/``__setitem__`` contract, without a Lua state."""

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Trigger"]
        calls = []
        ns = trigger.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_get_trigger_status_and_its_typo_alias_read_the_same_registry(self):
        reg = trigger.TriggerStatusRegistry()
        reg.set_status("bg0001", 3, 4)
        ns, _log_lines = self._namespace(
            context=trigger.TriggerContext("bg0001", 99), registry=reg)
        self.assertEqual(ns["GetTriggerStatus"](3), 4)
        self.assertEqual(ns["GetTeiggerStatus"](3), 4)
        # ns.calls is the bare dynamic-dispatch record (COO-DECISION
        # 20260905_0947's "wired means observed"); the log lines above are
        # the human-readable console trace and use a different format.
        self.assertIn("Trigger.GetTriggerStatus", ns.calls)
        self.assertIn("Trigger.GetTeiggerStatus", ns.calls)

    def test_set_status_and_next_status_write_the_context_s_own_trigger(self):
        reg = trigger.TriggerStatusRegistry()
        ns, _calls = self._namespace(
            context=trigger.TriggerContext("bg0001", 55), registry=reg)
        self.assertEqual(ns["SetStatus"](2), 2)
        self.assertEqual(reg.get_status("bg0001", 55), 2)
        self.assertEqual(ns["NextStatus"](), 3)
        self.assertEqual(reg.get_status("bg0001", 55), 3)

    def test_set_trigger_status_writes_a_different_trigger_not_the_context_s_own(self):
        reg = trigger.TriggerStatusRegistry()
        ns, _calls = self._namespace(
            context=trigger.TriggerContext("bg0001", 55), registry=reg)
        ns["SetTriggerStatus"](77, 9)
        self.assertEqual(reg.get_status("bg0001", 77), 9)
        # the context's OWN trigger (55) is untouched
        self.assertEqual(reg.get_status("bg0001", 55), trigger.STUB_DEFAULT)

    def test_quest_active_progress_and_finish_progress_write_the_shared_quest_store(self):
        # The t_opnq_t1.lua/t_clsq.lua pair this round's module docstring
        # derives Quest.Active/Finish's numeric values from: open sets 1,
        # close (only reachable once the flag reads 1) sets 2.
        from pirateforce_foundation.lua_api import quest as lua_api_quest

        store = lua_api_quest.InMemoryQuestStateStore()
        ns, calls = self._namespace(
            quest_context=lua_api_quest.QuestContext(character_id=7, quest_id=0),
            quest_store=store)
        self.assertEqual(ns["QuestActiveProgress"](42), lua_api_quest.QUEST_ACTIVE)
        self.assertEqual(store.get_quest_flag(7, 42), lua_api_quest.QUEST_ACTIVE)
        self.assertEqual(ns["QuestFinishProgress"](42), lua_api_quest.QUEST_FINISH)
        self.assertEqual(store.get_quest_flag(7, 42), lua_api_quest.QUEST_FINISH)
        self.assertTrue(any(
            c.startswith("LUA_TRIGGER_REAL Trigger.QuestActiveProgress ") for c in calls))
        self.assertTrue(any(
            c.startswith("LUA_TRIGGER_REAL Trigger.QuestFinishProgress ") for c in calls))

    def test_quest_progress_functions_share_the_store_with_the_quest_namespace(self):
        # The exact cross-namespace requirement build_namespace's own
        # docstring names: Trigger.QuestActiveProgress and Quest.GetQuestFlag
        # must see each other's writes when given the SAME store, the way
        # script_host.ScriptHost wires them for one real script run.
        from pirateforce_foundation.lua_api import quest as lua_api_quest
        from pirateforce_foundation.lua_api import spec as api_spec

        store = lua_api_quest.InMemoryQuestStateStore()
        qcontext = lua_api_quest.QuestContext(character_id=3, quest_id=0)
        trigger_ns, _ = self._namespace(quest_context=qcontext, quest_store=store)
        quest_ns = lua_api_quest.build_namespace(
            api_spec.NAMESPACE_METHODS["Quest"], lambda _msg: None,
            context=qcontext, store=store)
        trigger_ns["QuestActiveProgress"](900)
        self.assertEqual(quest_ns["GetQuestFlag"](900), lua_api_quest.QUEST_ACTIVE)

    def test_quest_progress_functions_bad_value_logs_a_line(self):
        # pf-adversary (this round): same fix as lua_api.quest's own
        # QuestFlagAndCounterTests::test_bad_value_same_arity_calls_log_a_line_not_silently.
        ns, calls = self._namespace()
        for name in ("QuestActiveProgress", "QuestFinishProgress"):
            with self.subTest(method=name):
                calls.clear()
                ns[name](float("nan"))
                self.assertTrue(
                    any(c.startswith("LUA_TRIGGER_BAD_VALUE Trigger.%s " % name) for c in calls),
                    calls,
                )

    def test_quest_progress_functions_wrong_arity_degrades_safely(self):
        ns, calls = self._namespace()
        for name, args in (("QuestActiveProgress", ()), ("QuestFinishProgress", (1, 2))):
            with self.subTest(method=name):
                calls.clear()
                self.assertEqual(ns[name](*args), trigger.STUB_DEFAULT)
                self.assertTrue(calls[0].startswith(
                    "LUA_TRIGGER_BAD_ARITY Trigger.%s " % name), calls)

    def test_wrong_arity_real_calls_degrade_safely_instead_of_raising(self):
        # CRITICAL, pf-adversary (this round): the first draft's real
        # closures had fixed positional parameters, so a wrong-arity call
        # (impossible from the shipped corpus today -- every real call site
        # is grepped at the exact arity below -- but not impossible from a
        # future or corrupted script, and this Lua host's whole charter is
        # "untrusted input must never crash the host") raised a raw Python
        # TypeError straight out of ScriptHost.call, breaking the one
        # invariant every OTHER name in this file still has via `*args`.
        ns, calls = self._namespace(
            context=trigger.TriggerContext("bg0001", 1),
            registry=trigger.TriggerStatusRegistry())
        cases = [
            ("GetTriggerStatus", ()),
            ("GetTriggerStatus", (1, 2)),
            ("SetStatus", ()),
            ("SetStatus", (1, 2, 3)),
            ("NextStatus", (1,)),
            ("SetTriggerStatus", (1,)),
            ("SetTriggerStatus", ()),
        ]
        for name, args in cases:
            with self.subTest(method=name, argc=len(args)):
                calls.clear()
                result = ns[name](*args)  # must not raise
                self.assertEqual(result, trigger.STUB_DEFAULT)
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0].startswith(
                    "LUA_TRIGGER_BAD_ARITY Trigger.%s " % name), calls)

    def test_correct_arity_real_calls_are_unaffected_by_the_arity_guard(self):
        # The guard must not turn into a second stub for well-formed calls
        # -- every real call site the corpus actually has.
        reg = trigger.TriggerStatusRegistry()
        ns, _calls = self._namespace(
            context=trigger.TriggerContext("bg0001", 1), registry=reg)
        self.assertEqual(ns["SetStatus"](5), 5)
        self.assertEqual(ns["NextStatus"](), 6)
        self.assertEqual(ns["GetTriggerStatus"](1), 6)
        self.assertEqual(ns["SetTriggerStatus"](2, 9), 9)
        self.assertEqual(reg.get_status("bg0001", 2), 9)

    def test_a_still_stubbed_method_logs_lua_api_stub_exactly_like_before(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["PlayFx"]("BgFx0005_002.fxs"), trigger.STUB_DEFAULT)
        self.assertEqual(calls, ["LUA_API_STUB Trigger.PlayFx"])

    def test_every_still_stubbed_name_is_reachable_and_logs_its_own_line(self):
        for name in trigger.STILL_STUBBED:
            with self.subTest(method=name):
                ns, calls = self._namespace()
                ns[name]()
                self.assertEqual(calls, ["LUA_API_STUB Trigger.%s" % name])

    def test_still_stubbed_plus_real_accounts_for_all_17_names(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Trigger"]
        self.assertEqual(len(methods), 17)
        self.assertEqual(
            set(trigger.STILL_STUBBED) | trigger.REAL_METHODS, set(methods))
        self.assertEqual(
            set(trigger.STILL_STUBBED) & trigger.REAL_METHODS, set())

    def test_a_non_api_key_returns_the_stub_default_silently(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["Var1"], trigger.STUB_DEFAULT)
        self.assertEqual(calls, [])

    def test_writing_into_the_namespace_is_accepted_and_discarded(self):
        ns, _calls = self._namespace()
        self.assertIsNone(ns.__setitem__("Var1", 42))

    def test_default_context_and_registry_are_supplied_when_omitted(self):
        ns, _calls = self._namespace()
        # Round trips against the private default registry this namespace
        # was built with -- the point being it does NOT raise, and it is
        # NOT the same object as a second call's default (no shared state
        # between two callers who both said nothing).
        self.assertEqual(ns["SetStatus"](1), 1)
        other_ns, _ = self._namespace()
        self.assertEqual(other_ns["GetTriggerStatus"](
            trigger.DEFAULT_CONTEXT.trigger_id), trigger.STUB_DEFAULT)


@LUPA_PACKAGE.skip_unless_present()
class RealTriggerLuaIntegrationTests(unittest.TestCase):
    """The same state machine, driven from real Lua through a ScriptHost."""

    def _host(self, context=None, registry=None):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(
            log=calls.append, trigger_context=context, trigger_registry=registry)
        return host, calls

    def test_set_status_from_lua_actually_changes_the_registry(self):
        reg = trigger.TriggerStatusRegistry()
        ctx = trigger.TriggerContext("bg0001", 12)
        host, calls = self._host(ctx, reg)
        host.load("function Probe() Trigger.SetStatus(3) end")
        host.call("Probe")
        self.assertEqual(reg.get_status("bg0001", 12), 3)
        self.assertIn(
            "LUA_TRIGGER_REAL Trigger.SetStatus scene='bg0001' trigger=12 from=0 to=3",
            calls)

    def test_a_six_gate_trigger_only_advances_when_every_prerequisite_is_ready(self):
        # The real shape of gamedata/lua/t_nex_t6.lua's ScriptStart, driven
        # against REAL, DISTINCT prerequisite triggers this time (round
        # s2fxf6's own test only proved the trivial Var-stub case, where
        # every Var collapsed to the same value by coincidence).
        source = """
        function ScriptStart()
          local S1 = Trigger.GetTriggerStatus(1)
          local S2 = Trigger.GetTriggerStatus(2)
          local S3 = Trigger.GetTriggerStatus(3)
          local S4 = Trigger.GetTriggerStatus(4)
          local S5 = Trigger.GetTriggerStatus(5)
          local S6 = Trigger.GetTriggerStatus(6)
          local TARGET = 5
          if ((S1 ~= TARGET) or (S2 ~= TARGET) or (S3 ~= TARGET)
              or (S4 ~= TARGET) or (S5 ~= TARGET) or (S6 ~= TARGET)) then
            return 0
          else
            Trigger.NextStatus()
            return 1
          end
        end
        """
        reg = trigger.TriggerStatusRegistry()
        ctx = trigger.TriggerContext("bg0001", 200)
        for pre in (1, 2, 3, 4, 5, 6):
            reg.set_status("bg0001", pre, 0)
        host, _calls = self._host(ctx, reg)
        host.load(source)

        self.assertEqual(host.call("ScriptStart"), 0)
        self.assertEqual(reg.get_status("bg0001", 200), trigger.STUB_DEFAULT)

        for pre in (1, 2, 3, 4, 5, 6):
            reg.set_status("bg0001", pre, 5)
        self.assertEqual(host.call("ScriptStart"), 1)
        self.assertEqual(reg.get_status("bg0001", 200), 1)

        # And it does NOT re-advance a second time by itself: a caller who
        # runs ScriptStart again with the gate already open is a script
        # authoring question (not this test's), but the registry itself
        # only moves when NextStatus is actually called again.
        self.assertEqual(host.call("ScriptStart"), 1)
        self.assertEqual(reg.get_status("bg0001", 200), 2)

    def test_two_hosts_sharing_one_registry_see_each_other_s_writes(self):
        # THE shared-world property this book exists for (PANYA-DECISION
        # 20260905_1057): two "sessions" (here: two ScriptHost instances,
        # standing in for two scripts/two players) reading and writing the
        # SAME process memory, not two private copies.
        reg = trigger.TriggerStatusRegistry()
        writer, _ = self._host(trigger.TriggerContext("bg0001", 1), reg)
        reader, _ = self._host(trigger.TriggerContext("bg0001", 2), reg)
        writer.load("function Bump() Trigger.SetStatus(7) end")
        reader.load("function Read() return Trigger.GetTriggerStatus(1) end")
        writer.call("Bump")
        self.assertEqual(reader.call("Read"), 7)

    def test_two_hosts_with_no_registry_given_do_not_leak_into_each_other(self):
        # The opposite property, equally load-bearing: the DEFAULT (no
        # explicit registry) must NOT be a second spelling of the world
        # singleton, or every corpus/spike test in this file would silently
        # share state with each other in test run order.
        host_a, _ = self._host()
        host_b, _ = self._host()
        host_a.load("function Bump() Trigger.SetStatus(9) end")
        host_b.load("function Read() return Trigger.GetTriggerStatus(%d) end"
                    % trigger.DEFAULT_CONTEXT.trigger_id)
        host_a.call("Bump")
        self.assertEqual(host_b.call("Read"), trigger.STUB_DEFAULT)

    def test_t_nex_t6_fixture_still_runs_to_completion_with_the_real_namespace(self):
        # round s2fxf6's own scenario (all Var* stubbed to 0, so the gate is
        # trivially satisfied) still holds under the real implementation --
        # this is the regression companion to test_script_host_spike.py's
        # updated version of the same fixture.
        from pathlib import Path

        from pirateforce_foundation import script_host

        fixtures = Path(__file__).parent / "fixtures" / "lua_spike"
        calls = []
        host = script_host.load_script_file(
            fixtures / "t_nex_t6.lua", log=calls.append,
            trigger_context=trigger.TriggerContext("bg0001", 300))
        self.assertEqual(host.call("ScriptStart"), 1)
        real_lines = [c for c in calls if c.startswith("LUA_TRIGGER_REAL ")]
        self.assertEqual(len(real_lines), 7)  # 6 GetTriggerStatus + 1 NextStatus


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
