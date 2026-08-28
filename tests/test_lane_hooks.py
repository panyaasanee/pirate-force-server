"""lane_hooks package: discovery, fail-closed dispatch, stdout/stderr split.

v6.3 lane_hooks architecture (see lane_hooks/__init__.py's own docstring).
This file proves the package's own contract in isolation -- the regression
proof for the one real hook it discovers today (LANE-GM's inbound
GM_RunGMCommandVital move) is tests/test_gm_run_command_dispatch_wiring.py,
unchanged by this PR.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402


class LaneHooksDiscoveryTests(unittest.TestCase):
    def test_the_real_gm_run_command_hook_is_discovered_and_registered(self):
        points = lane_hooks.registered_points()
        self.assertIn("vital_inbound_gm_run_command", points)
        self.assertGreaterEqual(points["vital_inbound_gm_run_command"], 1)

    def test_the_real_hook_module_declares_production_allowed(self):
        # pf-adversary finding: the lane_hooks approval (PANYA-ORDER
        # 20260827_1230, COO-DECISION 20260827_1241) names production_allowed
        # as a required gate, same as every other shippable lane module.
        # A module missing it is silently withdrawn (see the withdrawal
        # test below) -- this test catches the real hook regressing to
        # "silently stops firing" if the flag is ever deleted by accident.
        from pirateforce_foundation.lane_hooks import lane_gm_run_command

        self.assertIs(lane_gm_run_command.production_allowed, True)

    def test_a_broken_hook_module_is_caught_at_import_time_not_propagated(self):
        # pf-adversary HIGH finding: an import-time bug in a future
        # lane_hooks/lane_*.py file must not crash the whole process --
        # _discover() used to let importlib.import_module's exception
        # propagate straight through runtime.py's `from . import
        # lane_hooks` and kill boot for every lane, not just the broken
        # one. _import_module_safely is the fix, tested directly here
        # since the real _discover() only ever runs once per process.
        result = lane_hooks._import_module_safely(
            "pirateforce_foundation.lane_hooks.lane_this_module_does_not_exist"
        )
        self.assertIsNone(result)

    def test_a_module_without_production_allowed_has_its_hooks_withdrawn(self):
        # Simulates what _discover() does to a real on-disk module that
        # imports fine but never sets production_allowed = True: register
        # a hook under a fake module name, then run the same withdrawal
        # _discover() would run for a module whose production_allowed is
        # missing/False.
        fake_module_name = "pirateforce_foundation.lane_hooks._test_fake_not_allowed"
        lane_hooks._HOOKS.setdefault(self.POINT, []).append(
            (fake_module_name, lambda **kw: None)
        )
        self.addCleanup(lane_hooks._withdraw, fake_module_name)
        self.assertEqual(
            [m for m, _ in lane_hooks._HOOKS[self.POINT]], [fake_module_name]
        )
        lane_hooks._withdraw(fake_module_name)
        self.assertEqual(lane_hooks._HOOKS.get(self.POINT, []), [])

    POINT = "test_only_lane_hooks_discovery_point_never_used_in_production"

    def setUp(self):
        lane_hooks._HOOKS.pop(self.POINT, None)
        self.addCleanup(lane_hooks._HOOKS.pop, self.POINT, None)


class ModuleProductionAllowedTests(unittest.TestCase):
    """The gate as a DIRECT call site sees it (COO-DECISION 20260829_0041).

    Withdrawal is only half a gate: it can silence a module's hooks, and
    that is all it can do.  The 0xAC52 chat route reaches LANE-GM's code
    without registering anything, so runtime.py has to read the flag for
    itself before it calls -- these tests pin the answers it gets.
    """

    ALLOWED = "lane_gm_chat_command"

    def test_the_gated_chat_module_reports_allowed_by_its_bare_name(self):
        self.assertIs(lane_hooks.module_production_allowed(self.ALLOWED), True)

    def test_the_qualified_name_answers_the_same_as_the_bare_one(self):
        self.assertIs(
            lane_hooks.module_production_allowed(
                f"pirateforce_foundation.lane_hooks.{self.ALLOWED}"
            ),
            True,
        )

    def test_a_module_that_never_imported_is_closed_not_open(self):
        # The name of a file that does not exist, which is also the shape a
        # typo at a call site takes: closed, never "unknown so probably
        # fine".
        self.assertIs(
            lane_hooks.module_production_allowed("lane_no_such_module"),
            False,
        )

    def test_flipping_the_flag_to_false_closes_the_module(self):
        # The switch itself, exercised the way the owner would use it: with
        # production_allowed = False on disk, discovery records False and
        # every direct call site reading this function stands down.
        qualified = f"pirateforce_foundation.lane_hooks.{self.ALLOWED}"
        previous = lane_hooks._PRODUCTION_ALLOWED[qualified]
        lane_hooks._PRODUCTION_ALLOWED[qualified] = False
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__, qualified, previous
        )
        self.assertIs(lane_hooks.module_production_allowed(self.ALLOWED), False)

    def test_discovery_records_an_answer_for_every_lane_file_on_disk(self):
        # Re-derived from the directory, not from _HOOKS: the whole point of
        # this function is call sites reached WITHOUT a hook, so a module
        # that registers nothing must still be recorded. Deriving the
        # expectation from _HOOKS (the first version of this test) would
        # have gone blind the day the dead `vital_inbound_chat_local_talk`
        # registration is cleaned up -- which this package's own docstring
        # invites -- and stayed green while covering nothing.
        # [pf-adversary, round wi1m62]
        package_dir = Path(lane_hooks.__file__).parent
        on_disk = {
            f"pirateforce_foundation.lane_hooks.{path.stem}"
            for path in package_dir.glob("lane_*.py")
        }
        self.assertIn(
            "pirateforce_foundation.lane_hooks.lane_gm_chat_command", on_disk
        )
        self.assertEqual(
            on_disk - set(lane_hooks._PRODUCTION_ALLOWED),
            set(),
            "a lane file on disk that discovery recorded no answer for is a "
            "door that closes silently: module_production_allowed() reports "
            "False for it and nothing says why",
        )


class GateModuleTests(unittest.TestCase):
    """The arrow that had no test: flag on the module -> recorded -> answer.

    pf-adversary (round wi1m62) measured the hole this class fills. With the
    flag read written inline in `_discover()`, replacing it with a constant
    `True` -- which disables the hook withdrawal AND the record, i.e. the
    entire kill switch PANYA-ORDER 20260827_1230 approved -- left all 4,000
    tests green. Every gate test wrote `_PRODUCTION_ALLOWED` by hand, and
    the only lane module on disk sets the flag to `True`, so the False path
    of the read had never executed in a test at all.

    `_gate_module` is that read, on its own, callable with a module object
    whose flag says whatever a test needs it to say.

    WHAT IS STILL NOT TESTED, NAMED RATHER THAN PAPERED OVER: the step from
    a `production_allowed = False` line in a FILE ON DISK to that module
    object. `_discover()` runs once per process, at import, before any test
    exists, and this suite must not write files into the package directory
    to re-run it. The seam is `getattr(module, "production_allowed", False)`
    on a real imported module, which the tests below drive directly.
    """

    NAME = "pirateforce_foundation.lane_hooks._test_only_gate_module"

    def setUp(self):
        self.addCleanup(lane_hooks._PRODUCTION_ALLOWED.pop, self.NAME, None)

    def _module(self, **attrs):
        return types.SimpleNamespace(**attrs)

    def test_a_true_flag_is_recorded_and_returned(self):
        allowed = lane_hooks._gate_module(self.NAME, self._module(production_allowed=True))
        self.assertIs(allowed, True)
        self.assertIs(lane_hooks._PRODUCTION_ALLOWED[self.NAME], True)

    def test_a_false_flag_is_recorded_as_false_not_dropped(self):
        # Dropped instead of recorded would still answer False today (the
        # .get default), but it would erase the difference between "the
        # lane said no" and "no such file", which is the difference the
        # console tokens are supposed to explain.
        allowed = lane_hooks._gate_module(self.NAME, self._module(production_allowed=False))
        self.assertIs(allowed, False)
        self.assertIn(self.NAME, lane_hooks._PRODUCTION_ALLOWED)
        self.assertIs(lane_hooks._PRODUCTION_ALLOWED[self.NAME], False)

    def test_a_module_with_no_flag_at_all_is_closed(self):
        allowed = lane_hooks._gate_module(self.NAME, self._module())
        self.assertIs(allowed, False)

    def test_the_recorded_value_is_a_real_bool_not_whatever_the_module_set(self):
        # `production_allowed = 1` opens the gate (documented), but what is
        # recorded and returned must still be a bool, or a caller that
        # compares with `is True` gets a wrong answer from a right flag.
        allowed = lane_hooks._gate_module(self.NAME, self._module(production_allowed=1))
        self.assertIs(allowed, True)
        self.assertIs(lane_hooks._PRODUCTION_ALLOWED[self.NAME], True)

    def test_the_gate_answer_is_what_module_production_allowed_reports(self):
        # The arrow's last hop, end to end through the public function.
        lane_hooks._gate_module(self.NAME, self._module(production_allowed=False))
        self.assertIs(lane_hooks.module_production_allowed(self.NAME), False)
        lane_hooks._gate_module(self.NAME, self._module(production_allowed=True))
        self.assertIs(lane_hooks.module_production_allowed(self.NAME), True)


class LaneHooksFireTests(unittest.TestCase):
    """Uses a private, test-only point name so it can never collide with
    or perturb a real lane's registered hooks."""

    POINT = "test_only_lane_hooks_fire_point_never_used_in_production"

    def setUp(self):
        # _HOOKS is module-global by design (see lane_hooks/__init__.py) --
        # each test clears only its own private point name before and
        # after, never touching any other point a real lane registered.
        lane_hooks._HOOKS.pop(self.POINT, None)
        self.addCleanup(lane_hooks._HOOKS.pop, self.POINT, None)

    def test_fire_calls_every_registered_hook_for_the_point(self):
        calls = []

        @lane_hooks.hook(self.POINT)
        def _first(value):
            calls.append(("first", value))

        @lane_hooks.hook(self.POINT)
        def _second(value):
            calls.append(("second", value))

        lane_hooks.fire(self.POINT, value=42)
        self.assertEqual(calls, [("first", 42), ("second", 42)])

    def test_fire_on_an_unregistered_point_is_a_silent_no_op(self):
        # Must not raise -- a lane's hook file is optional, not a
        # precondition for the point to exist.
        lane_hooks.fire("no_such_point_was_ever_registered")

    def test_a_raising_hook_is_caught_and_never_reaches_the_caller(self):
        calls = []

        @lane_hooks.hook(self.POINT)
        def _broken(value):
            raise RuntimeError("this lane's hook is buggy")

        @lane_hooks.hook(self.POINT)
        def _still_runs(value):
            calls.append(value)

        # Must not raise -- fail-closed is not optional (see fire()'s own
        # docstring): one lane's bug can never take down the caller, and a
        # LATER hook for the same point must still run.
        lane_hooks.fire(self.POINT, value="ok")
        self.assertEqual(calls, ["ok"])

    def test_registration_prints_to_stderr_not_stdout(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout

        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):

            @lane_hooks.hook(self.POINT)
            def _noop(value):
                pass

        self.assertEqual(out.getvalue(), "")
        self.assertIn("LANE_HOOK_REGISTERED", err.getvalue())
        self.assertIn(self.POINT, err.getvalue())

    def test_a_hook_raising_non_ascii_text_does_not_crash_the_error_print(self):
        # pf-adversary finding: fire()'s except-handler print used to be a
        # raw f-string with no console-encoding guard -- fine for this
        # round's one hook (raises only fixed ASCII messages) but a
        # landmine for the very next hook whose exception embeds
        # client-supplied text on a cp874 console (this project's own
        # scar tissue, cited twice in the chief prompt). Proves the
        # guard holds even when a hook's exception message is non-ASCII.
        @lane_hooks.hook(self.POINT)
        def _raises_non_ascii(value):
            raise RuntimeError("bad name: การทดสอบ")

        # Must not raise UnicodeEncodeError or anything else.
        lane_hooks.fire(self.POINT, value=1)

    def test_a_real_fire_prints_the_fired_token_to_stderr_not_stdout(self):
        """stderr since round lo7e03 -- see the `hook` decorator's comment.

        A tool's --json contract is "pure JSON on stdout"; the 0xAC52 point
        fires on a vital every client sends, so this token on stdout landed
        inside one replay tool's JSON artifact.  The token still reaches
        the console, which is what the WIRED v2 grader greps.
        """
        import io
        from contextlib import redirect_stderr, redirect_stdout

        @lane_hooks.hook(self.POINT)
        def _noop(value):
            pass

        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            lane_hooks.fire(self.POINT, value=1)
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertIn(self.POINT, err.getvalue())
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
