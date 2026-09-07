"""The game's own ``utility.lua`` prelude, and the one-key ``os`` it needs.

TWO LAYERS, KEPT SEPARATE ON PURPOSE (house rule: one layer may never be
the evidence for the other).

  * SANDBOX layer -- what a script can reach after the prelude has run.
    Asserted against a runtime this file builds, with preludes this file
    writes, including hostile ones the shipped file is not.
  * CORPUS layer -- what the 17 shipped files that call ``rate(...)``
    actually do.  Asserted by DIFFERENCE against the
    real corpus: the same files, the same fixed clock, prelude off then on.

WHY THE CORPUS LAYER PINS NO NEW ABSOLUTE NUMBER.  The container this was
written in has no ``lupa`` and COO-DECISION ``20260907_1941`` forbids
installing one mid-round, so the new census totals could not be measured
here.  A difference needs no such measurement: "the set of files that fail
with `global 'rate'` is non-empty without the prelude and EMPTY with it" is
exact, and it goes red for a regression in either direction.  The absolute
census pins in ``test_script_lua_corpus.py`` are untouched because the
prelude seam is off by default -- see ``lua_api/prelude.py``'s docstring.
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

    def _host(self, source, log=None, seed=1757000000):
        preloaded = lua_api_prelude.Prelude(
            source=source, origin="<test>", seed=seed)
        return script_host.ScriptHost(log=log or (lambda _m: None),
                                      prelude=preloaded)

    def test_the_shipped_prelude_shape_defines_rate_and_rate_is_callable(self):
        host = self._host("function rate(d) return d end")
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
        host = self._host(
            "shim_keys = {} for k in pairs(os) do shim_keys[#shim_keys+1] = k end")
        keys = host.runtime.eval("shim_keys")
        self.assertEqual(sorted(keys.values()), sorted(lua_api_prelude.OS_SHIM_KEYS))
        # The names a real os library would carry, checked one by one rather
        # than by counting keys: a count passes if the ONE key is the wrong
        # one.
        for absent in ("execute", "remove", "rename", "exit", "getenv", "clock"):
            self.assertIsNone(host.runtime.eval("os.%s" % absent),
                              "os.%s reached the prelude" % absent)

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

    def test_read_prelude_returns_None_for_a_root_that_ships_none(self):
        self.assertIsNone(lua_api_prelude.read_prelude(Path(__file__).parent))

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

    def test_two_hosts_seeded_alike_roll_alike_and_differently_seeded_do_not(self):
        # Determinism is the property a test needs; INDEPENDENCE is the
        # property gameplay needs.  Both are asserted here because the same
        # seam gives both, and a future round that seeds every host from a
        # constant would break the second while keeping the first.
        found = lua_api_prelude.read_prelude(LUA_ROOT, clock=FIXED_SEED_CLOCK)
        draws = "local out = {} for i = 1, 40 do out[i] = rate(50) end return out"

        def roll(prelude):
            host = script_host.ScriptHost(log=lambda _m: None, prelude=prelude)
            return list(host.runtime.execute(draws).values())

        self.assertEqual(roll(found), roll(found))
        other = lua_api_prelude.Prelude(
            source=found.source, origin=found.origin, seed=found.seed + 99991)
        self.assertNotEqual(roll(found), roll(other),
                            "two differently seeded hosts rolled identically")


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
        before = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _m: None, quest_clock=FIXED_QUEST_CLOCK)
        after = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _m: None, quest_clock=FIXED_QUEST_CLOCK,
            prelude=found)
        self.assertGreater(after.total_stub_calls + after.total_real_calls,
                           before.total_stub_calls + before.total_real_calls)
        self.assertLessEqual(len(after.call_failed), len(before.call_failed))
        self.assertEqual(after.total, before.total)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
