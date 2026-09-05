"""LANE-Q: the 7 ``Instance.*`` names that became real this round.

Covers ``lua_api/instance.py`` at three levels: the registry alone (no Lua,
no lupa dependency -- these tests run on every machine), the namespace
object's ``__getitem__`` contract (still no Lua), and a real script running
against it through a live ``ScriptHost`` (guarded by ``LUPA_PACKAGE``, same
as the rest of ``tests/test_script_*``). Mirrors
``tests/test_script_lua_api_trigger.py``'s own shape.
"""
import unittest

from pf_preconditions import LUPA_PACKAGE, LUA_CORPUS_RUNNABLE, SIBLING

from pirateforce_foundation.lua_api import instance
from pirateforce_foundation.lua_api import trigger as lua_trigger


class InstanceRegistryTests(unittest.TestCase):
    """No lupa needed: this is plain Python state, like TriggerStatusRegistry."""

    def test_unknown_instance_reads_lasting_time_as_the_stub_default(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.get_lasting_time(42), instance.STUB_DEFAULT)

    def test_set_then_get_lasting_time_round_trips(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, 300), 300)
        self.assertEqual(reg.get_lasting_time(1), 300)

    def test_two_instances_never_share_one_lasting_time(self):
        reg = instance.InstanceRegistry()
        reg.set_lasting_time(1, 300)
        self.assertEqual(reg.get_lasting_time(2), instance.STUB_DEFAULT)

    def test_a_non_int_lasting_time_is_refused_not_coerced(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, "seven"), instance.STUB_DEFAULT)
        self.assertEqual(reg.get_lasting_time(1), instance.STUB_DEFAULT)

    def test_a_bool_lasting_time_is_refused_not_treated_as_zero_or_one(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, True), instance.STUB_DEFAULT)

    def test_a_lua_style_float_that_is_a_whole_number_is_accepted(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, 300.0), 300)
        self.assertEqual(reg.get_lasting_time(1.0), 300)

    def test_a_fractional_float_lasting_time_is_refused(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, 300.5), instance.STUB_DEFAULT)

    def test_nan_and_infinite_lasting_time_are_refused(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, float("nan")), instance.STUB_DEFAULT)
        self.assertEqual(reg.set_lasting_time(1, float("inf")), instance.STUB_DEFAULT)

    def test_a_negative_lasting_time_is_refused(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.set_lasting_time(1, -1), instance.STUB_DEFAULT)

    def test_key_events_add_and_remove_change_the_count(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.add_key_event(1, 5), 1)
        self.assertEqual(reg.add_key_event(1, 6), 2)
        # adding the same id twice does not grow the set again
        self.assertEqual(reg.add_key_event(1, 5), 2)
        self.assertEqual(reg.remove_key_event(1, 5), 1)
        self.assertEqual(reg.remove_key_event(1, 5), 1)  # already gone, no error

    def test_key_events_are_scoped_per_instance(self):
        reg = instance.InstanceRegistry()
        reg.add_key_event(1, 5)
        self.assertEqual(reg.remove_key_event(2, 5), instance.STUB_DEFAULT)

    def test_a_bad_event_id_is_refused(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.add_key_event(1, -1), instance.STUB_DEFAULT)
        self.assertEqual(reg.add_key_event(1, "five"), instance.STUB_DEFAULT)

    def test_key_events_per_instance_cap_refuses_a_new_event_but_keeps_existing_ones(self):
        reg = instance.InstanceRegistry(key_events_per_instance=2)
        reg.add_key_event(1, 1)
        reg.add_key_event(1, 2)
        self.assertEqual(reg.add_key_event(1, 3), 2)
        self.assertEqual(reg.remove_key_event(1, 1), 1)

    def test_instances_cap_refuses_a_new_instance_but_keeps_existing_ones_working(self):
        reg = instance.InstanceRegistry(instances=1)
        reg.set_lasting_time(1, 10)
        self.assertEqual(reg.set_lasting_time(2, 10), instance.STUB_DEFAULT)
        self.assertEqual(reg.get_lasting_time(1), 10)

    def test_call_score_count_tallies_per_instance_and_starts_at_one(self):
        reg = instance.InstanceRegistry()
        self.assertEqual(reg.call_score_count(1), 1)
        self.assertEqual(reg.call_score_count(1), 2)
        self.assertEqual(reg.call_score_count(1), 3)
        self.assertEqual(reg.call_score_count(2), 1)

    def test_a_non_positive_instances_cap_is_refused_at_construction(self):
        with self.assertRaises(ValueError):
            instance.InstanceRegistry(instances=0)
        with self.assertRaises(ValueError):
            instance.InstanceRegistry(instances=-1)

    def test_a_non_positive_key_events_cap_is_refused_at_construction(self):
        with self.assertRaises(ValueError):
            instance.InstanceRegistry(key_events_per_instance=0)
        with self.assertRaises(ValueError):
            instance.InstanceRegistry(key_events_per_instance=True)  # bool is an int; refused anyway

    def test_install_and_accessor_hand_back_the_same_process_singleton(self):
        first = instance.instance_registry()
        second = instance.instance_registry()
        self.assertIs(first, second)
        fresh = instance.InstanceRegistry()
        self.assertIs(instance.install_instance_registry(fresh), fresh)
        self.assertIs(instance.instance_registry(), fresh)
        # restore, so no other test in this process sees a stub registry
        # installed as "the world" by this one.
        instance.install_instance_registry(instance.InstanceRegistry())

    def test_install_refuses_anything_that_is_not_a_registry(self):
        with self.assertRaises(ValueError):
            instance.install_instance_registry("not a registry")


class RealInstanceNamespaceTests(unittest.TestCase):
    """The ``__getitem__``/``__setitem__`` contract, without a Lua state."""

    def _namespace(self, **kwargs):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Instance"]
        calls = []
        ns = instance.build_namespace(methods, calls.append, **kwargs)
        return ns, calls

    def test_get_instance_id_and_its_alias_read_the_same_context(self):
        ns, _log_lines = self._namespace(
            context=instance.InstanceContext(instance_id=1005))
        self.assertEqual(ns["GetInstanceID"](), 1005)
        self.assertEqual(ns["GetInstanceId"](), 1005)
        # ns.calls is the bare dynamic-dispatch record (COO-DECISION
        # 20260905_0947's "wired means observed"); the log lines above are
        # the human-readable console trace and use a different format.
        self.assertIn("Instance.GetInstanceID", ns.calls)
        self.assertIn("Instance.GetInstanceId", ns.calls)

    def test_set_lasting_time_and_get_lasting_time_round_trip_the_context_s_own_instance(self):
        reg = instance.InstanceRegistry()
        ns, _calls = self._namespace(
            context=instance.InstanceContext(instance_id=7), registry=reg)
        self.assertEqual(ns["SetLastingTime"](120), 120)
        self.assertEqual(ns["GetLastingTime"](), 120)
        self.assertEqual(reg.get_lasting_time(7), 120)

    def test_add_and_remove_key_event_write_the_context_s_own_instance(self):
        reg = instance.InstanceRegistry()
        ns, _calls = self._namespace(
            context=instance.InstanceContext(instance_id=7), registry=reg)
        self.assertEqual(ns["AddKeyEvent"](3), 1)
        self.assertEqual(reg.remove_key_event(7, 3), 0)

    def test_call_score_count_advances_the_context_s_own_instance(self):
        reg = instance.InstanceRegistry()
        ns, _calls = self._namespace(
            context=instance.InstanceContext(instance_id=7), registry=reg)
        self.assertEqual(ns["CallScoreCount"](), 1)
        self.assertEqual(ns["CallScoreCount"](), 2)
        self.assertEqual(reg.call_score_count(7), 3)

    def test_wrong_arity_real_calls_degrade_safely_instead_of_raising(self):
        # Same invariant round 456vso proved for Trigger.*: untrusted input
        # must never crash the host, even at an arity no shipped script
        # actually uses today.
        ns, calls = self._namespace(
            context=instance.InstanceContext(instance_id=1),
            registry=instance.InstanceRegistry())
        cases = [
            ("GetInstanceID", (1,)),
            ("GetInstanceId", (1,)),
            ("GetLastingTime", (1,)),
            ("SetLastingTime", ()),
            ("SetLastingTime", (1, 2)),
            ("AddKeyEvent", ()),
            ("AddKeyEvent", (1, 2)),
            ("RemoveKeyEvent", ()),
            ("CallScoreCount", (1,)),
        ]
        for name, args in cases:
            with self.subTest(method=name, argc=len(args)):
                calls.clear()
                result = ns[name](*args)  # must not raise
                self.assertEqual(result, instance.STUB_DEFAULT)
                self.assertEqual(len(calls), 1)
                self.assertTrue(calls[0].startswith(
                    "LUA_INSTANCE_BAD_ARITY Instance.%s " % name), calls)

    def test_correct_arity_real_calls_are_unaffected_by_the_arity_guard(self):
        reg = instance.InstanceRegistry()
        ns, _calls = self._namespace(
            context=instance.InstanceContext(instance_id=1), registry=reg)
        self.assertEqual(ns["SetLastingTime"](60), 60)
        self.assertEqual(ns["GetLastingTime"](), 60)
        self.assertEqual(ns["AddKeyEvent"](9), 1)
        self.assertEqual(ns["RemoveKeyEvent"](9), 0)
        self.assertEqual(ns["CallScoreCount"](), 1)

    def test_a_still_stubbed_method_logs_lua_api_stub_exactly_like_before(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["AddBonusPoint"](), instance.STUB_DEFAULT)
        self.assertEqual(calls, ["LUA_API_STUB Instance.AddBonusPoint"])

    def test_every_still_stubbed_name_is_reachable_and_logs_its_own_line(self):
        for name in instance.STILL_STUBBED:
            with self.subTest(method=name):
                ns, calls = self._namespace()
                ns[name]()
                self.assertEqual(calls, ["LUA_API_STUB Instance.%s" % name])

    def test_still_stubbed_plus_real_accounts_for_all_9_names(self):
        from pirateforce_foundation.lua_api import spec as api_spec
        methods = api_spec.NAMESPACE_METHODS["Instance"]
        self.assertEqual(len(methods), 9)
        self.assertEqual(
            set(instance.STILL_STUBBED) | instance.REAL_METHODS, set(methods))
        self.assertEqual(
            set(instance.STILL_STUBBED) & instance.REAL_METHODS, set())

    def test_a_non_api_key_returns_the_stub_default_silently(self):
        ns, calls = self._namespace()
        self.assertEqual(ns["Var1"], instance.STUB_DEFAULT)
        self.assertEqual(calls, [])

    def test_writing_into_the_namespace_is_accepted_and_discarded(self):
        ns, _calls = self._namespace()
        self.assertIsNone(ns.__setitem__("Var1", 42))

    def test_default_context_and_registry_are_supplied_when_omitted(self):
        ns, _calls = self._namespace()
        self.assertEqual(ns["SetLastingTime"](1), 1)
        other_ns, _ = self._namespace()
        self.assertEqual(other_ns["GetLastingTime"](), instance.STUB_DEFAULT)


class RealInstanceLuaIntegrationTests(unittest.TestCase):
    """The same state machine, driven from real Lua through a ScriptHost.

    Decorated per-method, not once on the class (round PIN-DRIFT-FIX, LANE-Q).
    A class-level ``skip_unless_present()`` sets ``__unittest_skip_why__`` on
    the CLASS, and ``TestCase.run()`` uses the class's own reason for every
    method in it whenever the class is skipped -- a method's own additional
    decorator never gets to raise its own reason on a machine where the
    class-level condition is already false, because ``run()`` never calls the
    wrapped method at all. Three of the four tests here need only
    ``LUPA_PACKAGE`` and are decorated with it directly; the fourth also reads
    the bridge's own script corpus and is decorated with
    ``LUA_CORPUS_RUNNABLE`` (the same composite key
    ``tests/test_script_lua_corpus.py`` uses, per
    ``pf_preconditions.AllOfThese``'s own docstring) instead of stacking
    ``BRIDGE_LUA_SCRIPTS`` under this class's old ``LUPA_PACKAGE`` guard --
    that stack was exactly the shape ``AllOfThese`` exists to replace, and the
    stacked form is what a real gate without lupa measured as
    ``PIN DRIFT: tests/test_script_lua_api_instance.py / precondition
    'bridge_lua_scripts': pinned 1, observed 0`` -- the method's own reason
    never fired because the class already skipped it under a different key.
    """

    def _host(self, context=None, registry=None):
        from pirateforce_foundation import script_host
        calls = []
        host = script_host.ScriptHost(
            log=calls.append, instance_context=context, instance_registry=registry)
        return host, calls

    @LUPA_PACKAGE.skip_unless_present()
    def test_set_lasting_time_from_lua_actually_changes_the_registry(self):
        reg = instance.InstanceRegistry()
        ctx = instance.InstanceContext(instance_id=12)
        host, calls = self._host(ctx, reg)
        host.load("function Probe() Instance.SetLastingTime(45) end")
        host.call("Probe")
        self.assertEqual(reg.get_lasting_time(12), 45)
        self.assertIn(
            "LUA_INSTANCE_REAL Instance.SetLastingTime instance=12 time=45",
            calls)

    @LUPA_PACKAGE.skip_unless_present()
    def test_two_hosts_sharing_one_registry_see_each_other_s_writes(self):
        # THE shared-world property this book exists for (PANYA-DECISION
        # 20260905_1057), same as lua_api.trigger's own proof: two
        # ScriptHost instances standing in for two scripts/two players,
        # reading and writing the SAME process memory, not two private
        # copies.
        reg = instance.InstanceRegistry()
        writer, _ = self._host(instance.InstanceContext(instance_id=1), reg)
        reader, _ = self._host(instance.InstanceContext(instance_id=2), reg)
        writer.load("function Bump() Instance.AddKeyEvent(7) end")
        reader.load("function Read() return Instance.GetLastingTime() end")
        writer.call("Bump")
        reg.set_lasting_time(2, 99)
        self.assertEqual(reader.call("Read"), 99)
        self.assertEqual(reg.remove_key_event(1, 7), 0)

    @LUPA_PACKAGE.skip_unless_present()
    def test_two_hosts_with_no_registry_given_do_not_leak_into_each_other(self):
        host_a, _ = self._host()
        host_b, _ = self._host()
        host_a.load("function Bump() Instance.SetLastingTime(30) end")
        host_b.load("function Read() return Instance.GetLastingTime() end")
        host_a.call("Bump")
        self.assertEqual(host_b.call("Read"), instance.STUB_DEFAULT)

    @LUA_CORPUS_RUNNABLE.skip_unless_present()
    def test_t_inscnt_fixture_from_the_real_corpus_calls_both_real_apis(self):
        # gamedata/lua/t_inscnt.lua's ScriptStart: `Instance.CallScoreCount()`
        # then `Trigger.NextStatus()` -- both real now, a worked example
        # proving this is real gating logic against the actual shipped
        # script, not just a synthetic fixture. Needs BOTH lupa (to drive a
        # live ScriptHost) and the bridge's own script corpus (the actual
        # .lua file on disk) at once, so it is guarded by the ONE composite
        # key that owns that conjunction (see the class docstring above and
        # pf_preconditions.AllOfThese's own docstring) rather than stacking
        # this method's own precondition under a class-level LUPA_PACKAGE
        # guard the other three methods use -- that stack is what produced
        # the pin drift this test's decorator now avoids.
        from pirateforce_foundation import script_host

        path = SIBLING / "pf_bridge" / "gamedata" / "lua" / "t_inscnt.lua"
        inst_reg = instance.InstanceRegistry()
        trig_reg = lua_trigger.TriggerStatusRegistry()
        calls = []
        host = script_host.load_script_file(
            path, log=calls.append,
            instance_context=instance.InstanceContext(instance_id=42),
            instance_registry=inst_reg,
            trigger_context=lua_trigger.TriggerContext("bg0001", 300),
            trigger_registry=trig_reg,
        )
        self.assertEqual(host.call("ScriptStart"), 1)
        self.assertEqual(inst_reg.call_score_count(42), 2)  # 1 from the script + this probe
        self.assertEqual(trig_reg.get_status("bg0001", 300), 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
