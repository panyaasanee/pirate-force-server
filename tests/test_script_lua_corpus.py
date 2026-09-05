"""LANE-Q spike: the loader loads all 616 real shipped scripts headless.

Guarded by LUA_CORPUS_RUNNABLE, the one key composing the two things this
module needs at once: the real corpus in the sibling bridge checkout (this
repository vendors only two named fixture files, see
test_script_host_spike.py) and the lupa package in this interpreter.  On a
machine missing either, these tests skip with a declared, pinned reason
(docs/PYTEST_SKIP_PINS.json) naming which piece is missing, rather than
failing or silently vanishing; on the bridge, and on any cloud round
paired with a pf_bridge checkout, they run against the real files.
"""
import unittest
from pathlib import Path

from pf_preconditions import LUA_CORPUS_RUNNABLE, SIBLING

from pirateforce_foundation import script_host

LUA_ROOT = SIBLING / "pf_bridge" / "gamedata" / "lua"

#: Measured 2026-09-05, round s2fxf6 (see docs/SCRIPT_LANE.md "known
#: findings").  Four are real syntax errors in the shipped source (missing
#: `end`/`)` - the original scripts, not this host's parsing); one
#: (utility.lua) calls os.time() at its own top level, which the sandbox
#: correctly blocks per the charter.  This set must change in the SAME
#: commit as any fix to script_host.py or to the vendored scripts - a test
#: that just asserted "failed == []" would go red the moment ANY future
#: script is added to the corpus with its own unrelated bug, telling nobody
#: which of 616 files to look at.
KNOWN_LOAD_FAILURES = frozenset({
    "Quest/q_day_send_new.lua",
    "Quest/q_repeat_send_new.lua",
    "Quest/q_send_new.lua",
    "Quest/q_set_new.lua",
    "utility.lua",
})


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class FullCorpusLoadsHeadlessTests(unittest.TestCase):
    def test_loader_visits_every_lua_file_on_disk(self):
        on_disk = {p.relative_to(LUA_ROOT).as_posix() for p in LUA_ROOT.rglob("*.lua")}
        report = script_host.load_corpus(LUA_ROOT, log=lambda _msg: None)
        self.assertEqual(report.total, len(on_disk))
        visited = {r.path for r in report.failed} | (on_disk - set(report.failed_paths))
        self.assertEqual(visited, on_disk)

    def test_exactly_the_known_failures_fail_no_more_no_fewer(self):
        report = script_host.load_corpus(LUA_ROOT, log=lambda _msg: None)
        self.assertEqual(set(report.failed_paths), KNOWN_LOAD_FAILURES)
        self.assertEqual(report.ok, report.total - len(KNOWN_LOAD_FAILURES))

    def test_load_corpus_never_raises_out_of_the_full_616_file_run(self):
        # The fail-closed contract itself: calling load_corpus over the
        # real, full corpus must complete and return, never propagate.
        try:
            script_host.load_corpus(LUA_ROOT, log=lambda _msg: None)
        except Exception as exc:  # noqa: BLE001 - this IS the assertion
            self.fail("load_corpus raised instead of failing closed: %r" % exc)

    def test_the_two_named_charter_fixtures_are_identical_to_the_real_files(self):
        # docs/SCRIPT_LANE.md/test_script_host_spike.py vendor byte-for-byte
        # copies of these two named files so that module needs no sibling
        # checkout - this test is what proves that copy has not drifted.
        fixtures = Path(__file__).parent / "fixtures" / "lua_spike"
        for name, real_relpath in (
            ("t_nex_t6.lua", "t_nex_t6.lua"),
            ("q_kill5.lua", "Quest/q_kill5.lua"),
        ):
            with self.subTest(name=name):
                vendored = (fixtures / name).read_bytes()
                real = (LUA_ROOT / real_relpath).read_bytes()
                self.assertEqual(vendored, real)


#: Measured 2026-09-05, round 4jsydv, calling every present
#: script_host.STANDARD_ENTRY_POINTS function across the real corpus.  Both
#: causes are bugs/gaps in the SHIPPED scripts, not this host, and this set
#: must change in the SAME commit as any fix to script_host.py, per the
#: same reasoning as KNOWN_LOAD_FAILURES above:
#:
#: - the four q_*_anticlass.lua / q_repeat_*_new.lua files declare
#:   `local check_N` INSIDE nested if/then blocks in Report_Check, then
#:   read `check_N` again after those blocks close -- by then the local has
#:   gone out of scope, so standard Lua lexical scoping resolves the name to
#:   an ever-nil global.  Verified in the source itself (grep
#:   "local check_1" gamedata/lua/Quest/q_gather_anticlass.lua): the
#:   declarations sit inside `if`/`else` bodies, the read sits after them.
#: - the twelve t_*rat*.lua files call a bare global `rate(dicevalue)`
#:   that is defined in gamedata/lua/utility.lua, not in the calling file.
#:   This host gives every script its OWN Lua state (module docstring:
#:   "ONE LUA STATE PER SCRIPT", deliberate, to stop 616 files sharing one
#:   global namespace from silently overwriting each other's same-named
#:   entry points) so a name defined in one file is never visible from
#:   another -- and utility.lua itself is in KNOWN_LOAD_FAILURES (it calls
#:   os.time() at its own top level, which the sandbox blocks), so even a
#:   shared-preload design would not yet make `rate` real here.  Nonclaim:
#:   this does NOT show the original client-side engine hits the same
#:   error -- it plausibly loads utility.lua once into a shared global
#:   environment before running any trigger/quest script, which this
#:   isolated-per-script host does not attempt (out of scope this round).
KNOWN_ENTRY_POINT_CALL_FAILURES = frozenset({
    ("Quest/q_gather_anticlass.lua", "Report_Check"),
    ("Quest/q_kill_anticlass.lua", "Report_Check"),
    ("Quest/q_repeat_gather_new.lua", "Report_Check"),
    ("Quest/q_repeat_kill_new.lua", "Report_Check"),
    ("t_ge2tm_rat.lua", "ScriptStart"),
    ("t_getm_rat_exp&sp.lua", "ScriptStart"),
    ("t_indani_l_cat_pt_rat.lua", "ScriptStart"),
    ("t_ins_ratx3_lv.lua", "ScriptStart"),
    ("t_ins_ratx4_lv.lua", "ScriptStart"),
    ("t_ins_ratx5_lv.lua", "ScriptStart"),
    ("t_ins_ratx6_lv.lua", "ScriptStart"),
    ("t_inskyev_danifx_rat.lua", "ScriptStart"),
    ("t_inskyev_getm_rat_exp&sp.lua", "ScriptStart"),
    ("t_inskyev_himdlfx_rat.lua", "ScriptStart"),
    ("t_inskyev_rat.lua", "ScriptStart"),
    ("t_opnplc_rat_lv.lua", "ScriptStart"),
    ("t_opnplc_rat_setoth.lua", "ScriptStart"),
})

#: Measured 2026-09-05, round 4jsydv, on the real 616-file corpus: calling
#: every STANDARD_ENTRY_POINTS function present in each file, with every
#: Quest/Trigger/Instance instance field (Var*/RewardItem*/StringVar*/...)
#: reading STUB_DEFAULT=0 per script_host's own contract, originally
#: produced 5057 total LUA_API_STUB emissions (STUB calls ONLY -- calls to
#: any REAL method are counted separately in report.total_real_calls, never
#: folded in here; see script_host.REAL_QUALIFIED_NAMES and
#: CorpusEntryPointReport's own docstring for why that split needed its own
#: test after a first draft got this wrong).  A later round made 7 of
#: Instance's 9 names real (lua_api/instance.py), which moved 37 calls --
#: 12 CallScoreCount, 9 AddKeyEvent, 7 GetLastingTime, 5 GetInstanceID,
#: 2 RemoveKeyEvent, 1 GetInstanceId, 1 SetLastingTime -- out of this count
#: and into report.total_real_calls (alongside Trigger's own 346: 201
#: NextStatus/121 GetTriggerStatus/23 SetTriggerStatus/1 GetTeiggerStatus),
#: for a new baseline of 5020 across fewer distinct still-stub
#: <Namespace>.<Method> names.  A round that lands a real API implementation
#: makes every call to that name, in every script that makes it, stop
#: counting here -- so this number may only fall or hold; a round that
#: raises it has made stub coverage worse, not a rounding artifact, and the
#: test below is written to catch that.
BASELINE_TOTAL_STUB_CALLS = 5020


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class FullCorpusEntryPointCallsTests(unittest.TestCase):
    """Not just loading the 616 files (above) -- CALLING what each one
    defines, per script_host.run_corpus_entry_points.  This is what
    actually exercises the 160-name API surface at realistic call volume,
    rather than the trivial single-call cases test_script_lua_api_*.py's
    unit tests use.
    """

    def test_every_present_entry_point_gets_called_or_its_failure_is_pinned(self):
        report = script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        self.assertEqual(set(report.load_failed), KNOWN_LOAD_FAILURES)
        # Structural lookup (run.errors is keyed by entry-point name), not a
        # substring search over a concatenated message -- a name that
        # happened to be a substring of another entry point's error text
        # would silently misattribute the failure under a string search.
        actual_failures = {
            (run.path, name)
            for run in report.call_failed
            for name in run.errors
        }
        self.assertEqual(actual_failures, KNOWN_ENTRY_POINT_CALL_FAILURES)

    def test_stub_vs_real_call_split_is_not_conflated(self):
        # Regression test for the exact bug this round's own draft made and
        # caught before push (see CorpusEntryPointReport's docstring):
        # Trigger's real methods share one RealTriggerNamespace.calls list
        # with its 12 still-stub methods, so a naive "sum every namespace's
        # .calls" silently double-books real calls as stub calls.
        report = script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        stub_names = set(report.stub_call_counts)
        real_names = set(report.real_call_counts)
        self.assertEqual(stub_names & real_names, set())
        self.assertTrue(real_names.issubset(script_host.REAL_QUALIFIED_NAMES))
        self.assertEqual(report.total_real_calls, sum(report.real_call_counts.values()))
        self.assertEqual(report.total_stub_calls, sum(report.stub_call_counts.values()))

    def test_no_script_defines_zero_standard_entry_points(self):
        # Measured 2026-09-05: every one of the 611 loadable files defines
        # at least one of STANDARD_ENTRY_POINTS.  A file with none would be
        # silent dead weight this report's totals would never explain --
        # this test is the tripwire if the corpus ever grows one.
        report = script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        self.assertEqual(report.no_entry_point, [])

    def test_run_corpus_entry_points_never_raises_out_of_the_full_616_file_run(self):
        try:
            script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        except Exception as exc:  # noqa: BLE001 - this IS the assertion
            self.fail("run_corpus_entry_points raised instead of failing closed: %r" % exc)

    def test_exactly_the_pinned_stub_call_count_no_more_no_fewer(self):
        # Same shape as test_exactly_the_known_failures_fail_no_more_no_fewer
        # above: an exact pin, not a <= ceiling, so this goes red the moment
        # ANYTHING changes it -- a round that lands a real API (count should
        # fall) must lower BASELINE_TOTAL_STUB_CALLS in the same commit, and
        # a round that regresses one (count would rise) gets caught here
        # instead of silently drifting.
        report = script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        self.assertEqual(report.total_stub_calls, BASELINE_TOTAL_STUB_CALLS)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
