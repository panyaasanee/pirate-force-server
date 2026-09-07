"""The game's own ``utility.lua`` prelude, and the one-key ``os`` it needs.

TWO LAYERS, KEPT SEPARATE ON PURPOSE (house rule: one layer may never be
the evidence for the other).

  * SANDBOX layer -- what a script can reach after the prelude has run.
    Asserted against a runtime this file builds, with preludes this file
    writes, including hostile ones the shipped file is not.
  * CORPUS layer -- what the 17 shipped files that call ``rate(...)``
    actually do.  Asserted by DIFFERENCE against the real corpus: the same
    files, the same fixed clock, prelude off then on.  13 of the 17 are the
    ones the prelude repairs; the other four never reach ``rate`` at all
    (see ``lua_api/prelude.py`` for which and why), which is precisely why
    the assertions below are SET RELATIONS rather than "all 17".

WHY THE CORPUS LAYER PINS NO NEW ABSOLUTE NUMBER.  The container this was
written in has no ``lupa`` and COO-DECISION ``20260907_1941`` forbids
installing one mid-round, so the new census totals could not be measured
here.  A difference needs no such measurement: "the set of files that fail
with `global 'rate'` is non-empty without the prelude and EMPTY with it" is
exact, and it goes red for a regression in either direction.  The absolute
census pins in ``test_script_lua_corpus.py`` are untouched because the
prelude seam is off by default -- see ``lua_api/prelude.py``'s docstring.

THE NUMBERS NOW EXIST, AND ARE NOT PINNED HERE ON PURPOSE.  pf-adversary
measured them this round on real lupa (2606 stub / 2865 real with the
prelude on, against the same fixed clock, reproducing 2597/2852 with it
off).  They are recorded in this round's file and its letter to COO, not
turned into constants here: this lane could not reproduce them in this
container, and a pin whose owner cannot re-measure it is the shape that
sends the NEXT round hunting a red it has no instrument for.  Pinning them
is the first task of the round that can run lupa itself.
"""
import unittest
from datetime import datetime
from pathlib import Path

from pf_preconditions import LUA_CORPUS_RUNNABLE, LUPA_PACKAGE, SIBLING

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import prelude as lua_api_prelude

LUA_ROOT = SIBLING / "pf_bridge" / "gamedata" / "lua"

FIXED_QUEST_CLOCK = lambda: datetime(2026, 9, 5, 12, 0)  # noqa: E731

#: A fixed seed, so every test in this file gets the same RNG stream out of
#: the shipped ``math.randomseed(os.time())`` line.  The value is arbitrary;
#: what matters is that it does not change between two runs of the same
#: test, which is the property `rate` needs to be assertable at all.
FIXED_SEED_CLOCK = lambda: 1757000000  # noqa: E731

#: The shipped files that CALL `rate(...)`.  Measured, not guessed:
#:
#:   grep -rlE '(^|[^A-Za-z_])rate[[:space:]]*\(' --include=*.lua gamedata/lua
#:
#: 18 files, 34 call sites (2026-09-07, round `q6nytd`).  17 are listed
#: here; the 18th is `utility.lua` itself, which DEFINES rate rather than
#: calling it, and is the prelude.  Listed by name rather than re-grepped
#: at test time so that a corpus which GAINS or LOSES one of them turns
#: this file red instead of silently changing what it measures.
#:
#: NOT every one of the 17 is claimed to reach `rate` from `ScriptStart`:
#: a file can die earlier for its own reasons, and this container had no
#: lupa to find out which (COO-DECISION 20260907_1941 forbids installing
#: one mid-round).  So the assertions below are written as a set
#: difference, which is exact no matter how that split falls.
RATE_CALLERS: tuple = (
    "t_escaphk_sp.lua",
    "t_ge2tm_rat.lua",
    "t_getm&cat_himd_q1_rat.lua",
    "t_getm_rat_exp&sp.lua",
    "t_getmorpopmo_q1.lua",
    "t_indani_l_cat_pt_rat.lua",
    "t_ins_ratx3_lv.lua",
    "t_ins_ratx4_lv.lua",
    "t_ins_ratx5_lv.lua",
    "t_ins_ratx6_lv.lua",
    "t_inskyev_danifx_rat.lua",
    "t_inskyev_getm_rat_exp&sp.lua",
    "t_inskyev_himdlfx_rat.lua",
    "t_inskyev_rat.lua",
    "t_opnplc_rat_lv&buf.lua",
    "t_opnplc_rat_lv.lua",
    "t_opnplc_rat_setoth.lua",
)

#: The Lua error a script gets today, verbatim enough to match on.
NIL_RATE = "global 'rate'"


def _sink():
    """A log that keeps its lines, so an assertion can read them."""
    lines: list = []
    return lines, lines.append


@LUPA_PACKAGE.skip_unless_present()
class OsShimIsGoneBeforeAnyScriptRunsTests(unittest.TestCase):
    """The sandbox invariant, asserted from the script's side of the wall."""

    #: Appended to every hand-written prelude in this class that is not
    #: itself about the helper check: `run_prelude` now answers False
    #: unless the chunk installed `rate` (pf-adversary D6), so a probe
    #: prelude has to install it too or every `prelude_ok` assertion below
    #: would be measuring the helper check instead of what it says.
    HELPER = "\nfunction rate(d) return d end\n"

    def _host(self, source, log=None, seed=1757000000, with_helper=True):
        preloaded = lua_api_prelude.Prelude(
            source=source + (self.HELPER if with_helper else ""),
            origin="<test>", seed=seed)
        return script_host.ScriptHost(log=log or (lambda _m: None),
                                      prelude=preloaded)

    def test_the_shipped_prelude_shape_defines_rate_and_rate_is_callable(self):
        host = self._host("function rate(d) return d end", with_helper=False)
        self.assertTrue(host.prelude_ok)
        self.assertEqual(host.runtime.eval("rate(7)"), 7)

    def test_os_is_nil_again_the_moment_the_prelude_chunk_is_done(self):
        host = self._host("local t = os.time()")
        self.assertTrue(host.prelude_ok)
        self.assertIsNone(host.runtime.globals()["os"])

    def test_os_is_nil_even_when_the_prelude_raised_halfway_through(self):
        # The `finally`, not the happy path.  A prelude that dies AFTER
        # touching the shim must not leave it installed.
        lines, log = _sink()
        host = self._host("local t = os.time() error('boom')", log=log)
        self.assertFalse(host.prelude_ok)
        self.assertIsNone(host.runtime.globals()["os"])
        self.assertTrue([l for l in lines if l.startswith("LUA_PRELUDE ERR")],
                        "\n".join(lines))

    def test_a_prelude_that_smuggles_the_shim_into_a_global_gets_a_dead_clock(self):
        # The shipped utility.lua does not do this.  A future one, or an
        # edited one, could -- and re-nilling `os` alone would not stop it,
        # because the smuggled reference is a DIFFERENT global name.
        lines, log = _sink()
        host = self._host("smuggled = os", log=log)
        self.assertTrue(host.prelude_ok)
        self.assertIsNone(host.runtime.globals()["os"])
        self.assertEqual(host.runtime.eval("smuggled.time()"),
                         lua_api_prelude.DISARMED_TIME)
        self.assertIn("LUA_PRELUDE_OS_DISARMED time", lines)

    def test_the_shim_carries_time_and_nothing_else_of_the_os_library(self):
        # BOTH probes run INSIDE the prelude chunk, which is the only place
        # `os` exists at all.  The first draft of the second one ran
        # `host.runtime.eval("os.execute")` AFTER construction, where the
        # `finally` has already nilled `os` -- indexing nil is a Lua error,
        # not None, so it raised (`attempt to index a nil value (global
        # 'os')`) and the test was RED.  pf-adversary D1 caught it by
        # running this file against real lupa; it would have gone red on
        # the Windows gate, which does have lupa==2.8.  A probe that has
        # never executed is not evidence.
        names = ("execute", "remove", "rename", "exit", "getenv", "clock")
        probe = "shim_keys = {} for k in pairs(os) do shim_keys[#shim_keys+1] = k end\n"
        probe += "\n".join("saw_%s = (os.%s ~= nil)" % (n, n) for n in names)
        host = self._host(probe)
        self.assertTrue(host.prelude_ok)
        keys = host.runtime.eval("shim_keys")
        self.assertEqual(sorted(keys.values()), sorted(lua_api_prelude.OS_SHIM_KEYS))
        # Name by name, not by counting keys: a count passes if the ONE key
        # present is the wrong one.
        for name in names:
            self.assertFalse(host.runtime.globals()["saw_%s" % name],
                             "os.%s reached the prelude" % name)

    def test_every_other_blocked_global_is_still_nil_during_the_prelude(self):
        # Widening the sandbox for `os` must not have widened it for the
        # rest.  Asserted DURING the chunk, not after, because after is
        # where the `finally` would hide a mistake.
        probe = "\n".join(
            "seen_%s = (%s ~= nil)" % (name, name)
            for name in script_host.BLOCKED_GLOBALS if name != "os")
        host = self._host(probe)
        self.assertTrue(host.prelude_ok)
        for name in script_host.BLOCKED_GLOBALS:
            if name == "os":
                continue
            self.assertFalse(host.runtime.globals()["seen_%s" % name],
                             "%s was reachable from the prelude" % name)

    def test_a_host_given_no_prelude_is_exactly_the_host_of_yesterday(self):
        host = script_host.ScriptHost(log=lambda _m: None)
        self.assertIsNone(host.prelude_ok)
        self.assertIsNone(host.runtime.globals()["os"])
        self.assertIsNone(host.runtime.globals()["rate"])

    def test_a_prelude_that_runs_clean_but_installs_nothing_is_not_OK(self):
        # pf-adversary D6.  An empty, comment-only, truncated or renamed
        # prelude used to log LUA_PRELUDE OK with `rate` still nil, after
        # which 13 scripts died on a nil `rate` and were billed as broken
        # quest files.  The token now stands on the target, not on "did
        # not raise".
        # No empty string in this list on purpose: an empty chunk is a
        # question about lupa's parser, not about this check.
        for source in ("-- nothing at all\n", "local unused = 1\n",
                       "function rat(d) return d end"):
            lines, log = _sink()
            host = self._host(source, log=log, with_helper=False)
            self.assertFalse(host.prelude_ok, source)
            self.assertIsNone(host.runtime.globals()["rate"], source)
            self.assertTrue(
                [l for l in lines if "reason=no_helpers" in l], "\n".join(lines))

    def test_the_seed_clock_answers_the_injected_value_while_armed(self):
        clock = lua_api_prelude.SeedClock(4242, lambda _m: None)
        self.assertEqual(clock(), 4242)
        self.assertEqual(clock({"year": 2026}), 4242,
                         "os.time(table) is legal Lua and must not raise")
        clock.disarm()
        self.assertEqual(clock(), lua_api_prelude.DISARMED_TIME)


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class TheShippedPreludeItselfTests(unittest.TestCase):
    """The real ``utility.lua``, read off the shipped corpus."""

    def test_read_prelude_finds_the_file_the_engine_names(self):
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        self.assertIsNotNone(found)
        self.assertTrue(found.origin.endswith(lua_api_prelude.PRELUDE_FILENAME))
        self.assertEqual(found.seed, FIXED_SEED_CLOCK())

    def test_the_shipped_bytes_are_the_ones_this_lane_measured(self):
        import hashlib
        raw = (Path(LUA_ROOT) / lua_api_prelude.PRELUDE_FILENAME).read_bytes()
        self.assertEqual(len(raw), lua_api_prelude.EXTRACTED_PRELUDE_BYTES)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         lua_api_prelude.EXTRACTED_PRELUDE_SHA256)

    def test_read_prelude_returns_None_for_a_root_that_ships_none_and_says_so(self):
        # pf-adversary D7: a silent None is indistinguishable from "the
        # caller asked for no prelude" and reverts a deployment to
        # yesterday's behaviour with nothing in the log to find.
        lines, log = _sink()
        self.assertIsNone(
            lua_api_prelude.read_prelude(Path(__file__).parent, log=log))
        self.assertTrue([l for l in lines if l.startswith("LUA_PRELUDE ABSENT")],
                        "\n".join(lines))

    def test_read_prelude_refuses_bytes_it_does_not_recognise_and_says_so(self):
        # pf-adversary D2: a prelude's global writes are restored from a
        # Python `finally`, outside any protected Lua call, so an EDITED
        # utility.lua can take the process down with a C-level PANIC no
        # `except` can see.  The digest was in the module already; this is
        # it being used rather than merely reported.
        import tempfile
        lines, log = _sink()
        with tempfile.TemporaryDirectory() as tmp:
            planted = Path(tmp) / lua_api_prelude.PRELUDE_FILENAME
            planted.write_bytes(b"function rate(d) return true end\n")
            self.assertIsNone(lua_api_prelude.read_prelude(tmp, log=log))
            self.assertTrue(
                [l for l in lines if l.startswith("LUA_PRELUDE REFUSED")],
                "\n".join(lines))
            # ...and the escape hatch is a real one, so the refusal above
            # is the digest talking and not the file being unreadable.
            allowed = lua_api_prelude.read_prelude(tmp, expect_digest=None)
            self.assertIsNotNone(allowed)

    def test_the_shipped_prelude_defines_rate_inside_the_sandbox(self):
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        lines, log = _sink()
        host = script_host.ScriptHost(log=log, prelude=found)
        self.assertTrue(host.prelude_ok, "\n".join(lines))
        self.assertIsNone(host.runtime.globals()["os"])
        # rate(100): r is math.random(0,1000000)/10000, i.e. 0..100, so a
        # 100% roll is true for every possible draw.  rate(-1) is false for
        # every possible draw.  Neither assertion depends on the seed, the
        # platform's RNG, or how many draws happen first -- which is what
        # makes them assertions rather than a coin flip in a test suite.
        for _ in range(200):
            self.assertTrue(host.runtime.eval("rate(100)"))
            self.assertFalse(host.runtime.eval("rate(-1)"))

    def _roll(self, prelude, draws=40):
        host = script_host.ScriptHost(log=lambda _m: None, prelude=prelude)
        return list(host.runtime.execute(
            "local out = {} for i = 1, %d do out[i] = rate(50) end return out"
            % draws).values())

    def test_one_prelude_seeds_every_host_it_is_given_to_identically(self):
        # THIS IS A DEFECT, PINNED AS THE FACT IT IS (pf-adversary D5).
        # The previous version of this class asserted that two hand-built
        # Preludes with hand-different seeds roll differently -- true, and
        # beside the point: it never asked whether the SWEEP or
        # `read_prelude` give different hosts different seeds.  They do
        # not.  `load_corpus`/`run_corpus_entry_points` take ONE Prelude
        # for all 616 hosts, so every player at every rate-gated trigger
        # would get the same roll for the life of the process.  The
        # replacement policy is a design decision with owners, asked of COO
        # by letter this round, and until it is answered the seam stays off
        # by default -- so this test exists to make the next round's fix
        # go red here rather than to bless the behaviour.
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        self.assertEqual(self._roll(found), self._roll(found),
                         "the shared-seed defect this pins has changed shape; "
                         "read lua_api/prelude.py:Prelude before editing this")

    def test_a_different_seed_really_does_change_the_stream(self):
        # The control for the test above: identical rolls there are the
        # SEED being identical, not `rate` ignoring its seed entirely.
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        other = lua_api_prelude.Prelude(
            source=found.source, origin=found.origin, seed=found.seed + 99991)
        self.assertNotEqual(self._roll(found), self._roll(other))


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class RateGatedCorpusFilesTests(unittest.TestCase):
    """The 18 files, before and after, on the real corpus."""

    def _run_one(self, name, prelude):
        lines, log = _sink()
        host = script_host.load_script_file(
            Path(LUA_ROOT) / name, log=log,
            quest_clock=FIXED_QUEST_CLOCK, prelude=prelude)
        if not host.has_function("ScriptStart"):
            return None, lines
        try:
            host.call("ScriptStart")
        except Exception as exc:  # noqa: BLE001 - the failure IS the reading
            return str(exc), lines
        return None, lines

    def test_the_pinned_rate_calling_files_all_exist_in_the_shipped_corpus(self):
        missing = [name for name in RATE_CALLERS
                   if not (Path(LUA_ROOT) / name).is_file()]
        self.assertEqual(missing, [])

    def _nil_rate_failures(self, prelude):
        failed = set()
        for name in RATE_CALLERS:
            error, _lines = self._run_one(name, prelude)
            if error is not None and NIL_RATE in error:
                failed.add(name)
        return failed

    def test_the_premise_still_holds_some_of_them_die_on_a_nil_rate_today(self):
        # If this ever goes red, the corpus or the host changed under this
        # file and every other assertion here is measuring nothing.
        self.assertNotEqual(self._nil_rate_failures(None), set())

    def test_the_prelude_removes_every_nil_rate_failure_and_adds_none(self):
        before = self._nil_rate_failures(None)
        after = self._nil_rate_failures(
            lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK))
        self.assertEqual(after, set())
        self.assertNotEqual(before, set())

    def test_the_whole_corpus_sweep_blames_nobody_for_a_nil_rate_with_it(self):
        # Wider than the 17 pinned names on purpose: a file this lane never
        # grepped for is exactly the one a per-name list would miss.
        lines, log = _sink()
        script_host.run_corpus_entry_points(
            LUA_ROOT, log=log, quest_clock=FIXED_QUEST_CLOCK,
            prelude=lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK))
        blamed = [line for line in lines if NIL_RATE in line]
        self.assertEqual(blamed, [])

    def test_the_prelude_strictly_adds_api_calls_it_never_removes_them(self):
        # The census question, asked as a difference so it needs no new
        # absolute pin (see this module's docstring).  Scripts that ran
        # zero API calls now run some; nothing that ran before stops.
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        # `prelude=None` EXPLICITLY, not by omission (round `e5epdj`).  The
        # sweeps' default is now script_host.SHIPPED_PRELUDE, so an omitted
        # argument here would compare the prelude against ITSELF and this
        # test would assert nothing while still passing -- it failed loudly
        # the moment the default flipped, which is the only reason the
        # regression was visible at all.
        before = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _m: None, quest_clock=FIXED_QUEST_CLOCK,
            prelude=None)
        after = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _m: None, quest_clock=FIXED_QUEST_CLOCK,
            prelude=found)
        # PATHS, NOT COUNTS (pf-adversary D9).  `assertLessEqual` on a
        # count passes for a change that repairs 13 files and breaks 13
        # different ones -- which is exactly the drift the exact pins in
        # test_script_lua_corpus.py were written to catch.  A subset
        # relation on the file names cannot.
        before_failed = {run.path for run in before.call_failed}
        after_failed = {run.path for run in after.call_failed}
        self.assertTrue(after_failed <= before_failed,
                        "new call failures with the prelude: %s"
                        % sorted(after_failed - before_failed))
        self.assertTrue(before_failed - after_failed,
                        "the prelude repaired nothing")
        self.assertGreater(after.total_stub_calls + after.total_real_calls,
                           before.total_stub_calls + before.total_real_calls)
        self.assertEqual(after.total, before.total)
        self.assertEqual(after.load_failed, before.load_failed)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
