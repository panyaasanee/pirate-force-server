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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
