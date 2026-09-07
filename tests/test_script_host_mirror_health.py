"""A broken mirror of ours must be READABLE, not only loggable.

COO-DECISION `pf_bridge/notes_to_chief/20260907_1441_COO-DECISION-q1344-
fail-soft-with-a-counter-LANE-Q.md`, answering this lane's own
`20260907_1344_LANE-Q-ASK-COO-who-reads-host-failed-at-boot.md`:

* fail-soft is the right posture -- the server must come up even when
  quests are dead, because "nobody can log in" is worse damage than "no
  quests" (item 1);
* but the `LUA_HOST` line round `oghyca` added is a log NOBODY READS
  (measured in that letter: `load_corpus`/`run_corpus_entry_points` have
  zero call sites outside `tests/`), so the host must also keep the count,
  the last error and a stamp in state a reader can get at without opening
  a log file (item 3);
* and this lane must NOT invent a health-check endpoint to display it
  (item 4).  There is none in `src/` to plug into -- measured, this round:
  `grep -rn "def .*health\\|/health" --include=*.py src/` finds no
  endpoint -- so the state stops at `script_host.MIRROR_HEALTH`.

Everything here except the two `ScriptHost` classes at the bottom runs
without `lupa`, on purpose: the counter is the part the decision asked
for, and it must be pinned on the cloud runner (no `lupa` wheel there)
as well as on the bridge.
"""
import contextlib
import shutil
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from pathlib import Path

from pf_preconditions import LUPA_PACKAGE

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import spec
from pirateforce_foundation.lua_api.vendored import VendoredDataError


@contextlib.contextmanager
def broken_census():
    """Point the census at a file that is not there, then put it back.

    The same two lines `tests/test_script_lua_api_spec.py` uses in its own
    child interpreter (`_SPEC_PATH` + `_CACHE.clear()`), in-process here
    because what is under test is a Python object's state rather than an
    import.  The `finally` clears the cache a SECOND time so the next
    reader in this process re-parses the real file rather than inheriting
    whatever this block left behind.
    """
    original = spec._SPEC_PATH
    spec._SPEC_PATH = Path("no_such_api_spec_for_this_test.tsv")
    spec._CACHE.clear()
    try:
        yield
    finally:
        spec._SPEC_PATH = original
        spec._CACHE.clear()


def _fixed_clock(stamp="2026-09-07T10:11:12Z"):
    moment = datetime(2026, 9, 7, 10, 11, 12, tzinfo=timezone.utc)
    return (lambda: moment), stamp


class TheTallyMovesWhenAMirrorIsBrokenTests(unittest.TestCase):
    """COO-DECISION item 3: a broken file must move a counter."""

    def test_a_healthy_build_returns_its_value_and_counts_nothing(self):
        health = script_host.MirrorHealth()
        lines = []
        self.assertEqual(
            script_host.guard_mirrors(lambda: {"Quest": frozenset()},
                                      lines.append, health),
            ({"Quest": frozenset()}, None))
        self.assertEqual(health.tally().failures, 0)
        self.assertIsNone(health.tally().last_error)
        self.assertIsNone(health.tally().last_failed_at)
        self.assertEqual(lines, [])

    def test_a_broken_census_moves_the_counter_and_names_the_file(self):
        clock, stamp = _fixed_clock()
        health = script_host.MirrorHealth(clock=clock)
        lines = []
        with broken_census():
            built, failure = script_host.guard_mirrors(
                lambda: spec.NAMESPACE_METHODS, lines.append, health)
        self.assertIsNone(built, "a degraded build hands back None")
        self.assertIsNotNone(failure, "and the failure it hit, for the caller "
                                      "to quote instead of a shared counter")
        tally = health.tally()
        self.assertEqual(tally.failures, 1)
        self.assertEqual(tally.last_failed_at, stamp)
        self.assertIn("VendoredDataError", tally.last_error)
        self.assertIn("no_such_api_spec_for_this_test.tsv", tally.last_error)

    def test_the_second_failure_moves_the_counter_again(self):
        # The letter's whole complaint was a state nobody could see; a
        # counter that latched at 1 would hide "and it is still broken".
        health = script_host.MirrorHealth()
        with broken_census():
            for _ in range(2):
                script_host.guard_mirrors(
                    lambda: spec.NAMESPACE_METHODS, lambda _line: None, health)
        self.assertEqual(health.tally().failures, 2)

    def test_it_writes_one_line_and_that_line_is_not_a_LUA_HOST_line(self):
        """pf-adversary D1, this round -- the finding that made the gate red.

        `tests/test_script_lua_corpus.py` pins that one broken mirror of
        ours produces exactly ONE line starting `LUA_HOST` per script it
        stopped, ending in that script's name. The first draft of this
        module wrote two more per host construction, both starting with
        that prefix (`LUA_HOST ...` and `LUA_HOST_DEGRADED ...`): 3 where
        1 was pinned, and over the real 616-file corpus 1848 lines where
        main writes 616. The machine-readable line now has a prefix of its
        own, and the `LUA_HOST` line stays the sweep's to write.
        """
        clock, stamp = _fixed_clock()
        health = script_host.MirrorHealth(clock=clock)
        lines = []
        with broken_census():
            script_host.guard_mirrors(
                lambda: spec.NAMESPACE_METHODS, lines.append, health)
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("LUA_MIRROR_DEGRADED "), lines[0])
        self.assertEqual([line for line in lines
                          if line.startswith("LUA_HOST")], [])
        self.assertIn("mirror_failures=1", lines[0])
        self.assertIn('last_failed_at="%s"' % stamp, lines[0])
        self.assertIn('discovered_at="ScriptHost construction"', lines[0])

    def test_every_line_it_writes_is_console_safe(self):
        # AGENTS.md section 7: the bridge console is cp874.
        health = script_host.MirrorHealth()
        lines = []
        with broken_census():
            script_host.guard_mirrors(
                lambda: spec.NAMESPACE_METHODS, lines.append, health)
        for line in lines:
            line.encode("ascii")

    def test_a_non_ascii_error_message_is_still_recorded_ascii(self):
        health = script_host.MirrorHealth()
        # Written as escapes so this FILE stays ASCII (AGENTS.md section 7)
        # while the value it records is not.
        health.record(VendoredDataError("api_spec.tsv \u0e1e\u0e31\u0e07"))
        health.tally().last_error.encode("ascii")
        health.tally().log_fields().encode("ascii")

    def test_an_error_that_is_not_ours_is_not_swallowed_and_not_counted(self):
        # The guard classifies, it does not catch everything: a bug in this
        # lane's own Python must still blow up where it happened rather
        # than being filed as "the mirror is broken".
        health = script_host.MirrorHealth()

        def build():
            raise ZeroDivisionError("a defect in this lane, not in a file")

        with self.assertRaises(ZeroDivisionError):
            script_host.guard_mirrors(build, lambda _line: None, health)
        self.assertEqual(health.tally().failures, 0)

    def test_sixteen_threads_recording_lose_no_count(self):
        health = script_host.MirrorHealth()
        error = VendoredDataError("api_spec.tsv is empty")
        threads = [threading.Thread(target=health.record, args=(error,))
                   for _ in range(16)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(health.tally().failures, 16)

    def test_a_class_name_outside_ascii_is_escaped_too(self):
        # pf-adversary D10, this round: only the message used to be
        # escaped, so a subclass whose NAME carried such a character
        # reached `print` and killed the sweep on a cp874 console.
        health = script_host.MirrorHealth()

        error_type = type("\u9328Error", (VendoredDataError,), {})
        health.record(error_type("boom"))
        health.tally().log_fields().encode("cp874")

    def test_the_process_wide_tally_exists_and_starts_at_zero_shape(self):
        # Not asserting it is 0 -- another test in this process may have
        # recorded into it -- only that the module publishes ONE readable
        # object of the right type, which is what a health check would read.
        self.assertIsInstance(script_host.MIRROR_HEALTH,
                              script_host.MirrorHealth)
        tally = script_host.MIRROR_HEALTH.tally()
        self.assertIsInstance(tally.failures, int)
        self.assertIn("mirror_failures=", tally.log_fields())

    def test_a_degraded_host_refusal_is_classified_as_ours_not_a_script_s(self):
        # pf-adversary D11 (round 7kxfe9) in one line: the refusal a
        # degraded host raises must land in the LUA_HOST bucket, never be
        # logged against whichever quest file happened to be loading.
        self.assertTrue(issubclass(script_host.MirrorUnavailable,
                                   VendoredDataError))
        self.assertTrue(issubclass(script_host.MirrorUnavailable,
                                   script_host._host_side_error_types()))


@LUPA_PACKAGE.skip_unless_present()
class ADegradedHostIsStillBuiltAndStillASandboxTests(unittest.TestCase):
    """COO-DECISION item 3's other half: `ScriptHost` must still build."""

    def test_the_host_is_built_degraded_with_no_namespaces(self):
        health = script_host.MirrorHealth()
        lines = []
        with broken_census():
            host = script_host.ScriptHost(log=lines.append, mirror_health=health)
        self.assertTrue(host.degraded)
        self.assertEqual(host.namespaces, {})
        self.assertEqual(health.tally().failures, 1)

    def test_a_degraded_host_still_blocks_every_sandbox_door(self):
        # A mirror failure is not an excuse to hand a script io/os/require.
        with broken_census():
            host = script_host.ScriptHost(log=lambda _line: None,
                                          mirror_health=script_host.MirrorHealth())
        globals_ = host.runtime.globals()
        for name in script_host.BLOCKED_GLOBALS:
            with self.subTest(name=name):
                self.assertIsNone(globals_[name])

    def test_a_degraded_host_refuses_to_load_or_call_naming_the_tally(self):
        with broken_census():
            host = script_host.ScriptHost(log=lambda _line: None,
                                          mirror_health=script_host.MirrorHealth())
        with self.assertRaises(script_host.MirrorUnavailable) as caught:
            host.load("function ScriptStart() return 1 end")
        # THIS host's own cause, not a shared counter's latest
        # (pf-adversary D7): the sweep logs this text against the script it
        # stopped, so it has to name the file that actually broke it.
        self.assertIn("VendoredDataError", str(caught.exception))
        self.assertIn("no_such_api_spec_for_this_test.tsv", str(caught.exception))
        with self.assertRaises(script_host.MirrorUnavailable):
            host.call("ScriptStart")
        with self.assertRaises(script_host.MirrorUnavailable):
            host.has_function("ScriptStart")

    def test_a_healthy_host_is_not_degraded_and_counts_nothing(self):
        health = script_host.MirrorHealth()
        host = script_host.ScriptHost(log=lambda _line: None, mirror_health=health)
        self.assertFalse(host.degraded)
        self.assertEqual(len(host.namespaces), 8)
        self.assertEqual(health.tally().failures, 0)


@LUPA_PACKAGE.skip_unless_present()
class ASweepOverABrokenMirrorBlamesUsNotTheScriptsTests(unittest.TestCase):
    """The end-to-end shape of D11, now that the host survives the failure."""

    def setUp(self):
        # pf-adversary D8, this round: `load_corpus` builds its hosts with
        # no `mirror_health`, so without this the module under test leaves
        # the process-wide object holding a failure that names a file which
        # has never existed. Swapped for the duration, restored after.
        original = script_host.MIRROR_HEALTH
        script_host.MIRROR_HEALTH = script_host.MirrorHealth()
        self.isolated = script_host.MIRROR_HEALTH
        self.addCleanup(setattr, script_host, "MIRROR_HEALTH", original)
        self.tmp = tempfile.mkdtemp(prefix="pf_lua_degraded_")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        (Path(self.tmp) / "q_innocent.lua").write_text(
            "function Accept_Run()\n  return 1\nend\n", encoding="ascii")

    def test_the_innocent_script_lands_in_host_failed_not_failed(self):
        lines = []
        with broken_census():
            report = script_host.load_corpus(self.tmp, log=lines.append)
        self.assertEqual(report.total, 1)
        self.assertEqual(report.ok, 0)
        self.assertEqual(report.failed, [])
        self.assertEqual(report.host_failed, ["q_innocent.lua"])
        self.assertEqual([line for line in lines
                          if line.startswith("LUA_SCRIPT ")], [])
        self.assertTrue([line for line in lines
                         if line.startswith("LUA_HOST ")], lines)
        # Exactly one, and it names the script it stopped: the contract
        # tests/test_script_lua_corpus.py pins (pf-adversary D1).
        host_lines = [line for line in lines if line.startswith("LUA_HOST")]
        self.assertEqual(len(host_lines), 1, lines)
        self.assertTrue(host_lines[0].endswith('discovered_at="q_innocent.lua"'),
                        host_lines[0])
        self.assertIn("VendoredDataError", host_lines[0])

    def test_a_host_built_with_no_health_records_into_the_published_one(self):
        # pf-adversary D5, this round: every other test injects its own
        # MirrorHealth, so `MIRROR_HEALTH` -- the ONE object a future health
        # check would read, and the reason this round exists -- had no pin
        # at all. Replacing the default with a fresh MirrorHealth() left
        # every test green.
        self.assertEqual(self.isolated.tally().failures, 0)
        with broken_census():
            script_host.load_corpus(self.tmp, log=lambda _line: None)
        self.assertEqual(self.isolated.tally().failures, 1)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
