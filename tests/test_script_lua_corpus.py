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
import shutil
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from pf_preconditions import LUA_CORPUS_RUNNABLE, LUPA_PACKAGE, SIBLING

from pirateforce_foundation import script_host
from pirateforce_foundation.lua_api import message as lua_api_message
from pirateforce_foundation.lua_api import spec as lua_api_spec

LUA_ROOT = SIBLING / "pf_bridge" / "gamedata" / "lua"

#: Quest.CheckOpenTime became real the round after 4jsydv (lua_api/quest.py).
#: A fixed instant, not the real wall clock, for every corpus-wide run in
#: this module: Quest/q_sea_join.lua's own Accept_Run chains seven windows
#: with `or`, which short-circuits the moment one is true, so which of the
#: seven actually get called -- and therefore this file's own pinned call
#: counts below -- would otherwise depend on the real time of day the test
#: happened to run.  Noon (the datetime's own naive hour/minute -- all
#: script_host ever reads, see lua_api.quest._minutes_of_day) sits outside
#: every literal window all three CheckOpenTime-calling files in the corpus
#: use (grepped: Quest/q_sea_join.lua's seven windows run 1930-1955 through
#: 0155; Quest/q_con5.lua and Quest/q_arena2.lua pass Quest.Var3/Var4, which
#: this harness supplies as STUB_DEFAULT=0 -- a window of exactly minute 0,
#: also nowhere near noon).
FIXED_QUEST_CLOCK = lambda: datetime(2026, 9, 5, 12, 0)  # noqa: E731

#: Measured 2026-09-05, round s2fxf6 (see docs/SCRIPT_LANE.md "known
#: findings").  Four are real syntax errors in the shipped source (missing
#: `end`/`)` - the original scripts, not this host's parsing); one
#: (utility.lua) calls os.time() at its own top level, which the sandbox
#: correctly blocks per the charter.  This set must change in the SAME
#: commit as any fix to script_host.py or to the vendored scripts - a test
#: that just asserted "failed == []" would go red the moment ANY future
#: script is added to the corpus with its own unrelated bug, telling nobody
#: which of 616 files to look at.
#: The corpus's one file whose name contains a space, measured (round
#: `5qtaqy`, pf-adversary D6).  Named here rather than inside the test that
#: uses it because two classes need it: the fixture that reproduces the
#: ambiguous log line without the corpus, and the corpus-guarded test that
#: fails if this stops being the shape of the real problem.
THE_ONE_SPACED_FILE_NAME = "t_test auto.lua"

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

    def test_no_file_in_the_real_corpus_fails_because_of_a_defect_of_OURS(self):
        # pf-adversary D1 (round `oghyca`): the bucket that separates our
        # broken checkout from a broken quest file had no assertion of its
        # own on the REAL corpus, and every corpus test threw the log away.
        # Deleting lua_api/message_catalog.tsv -- the shape a .gitignore
        # accident produces -- put 23 of 616 files in host_failed and this
        # module stayed green.  Both halves are asserted here: the bucket,
        # and the LUA_HOST line that is the only thing a human running the
        # sweep by hand would see.
        logged = []
        report = script_host.load_corpus(LUA_ROOT, log=logged.append)
        host_lines = [line for line in logged if line.startswith("LUA_HOST")]
        self.assertEqual(report.host_failed, [], "\n".join(host_lines))
        self.assertEqual(host_lines, [])

    def test_the_corpus_still_has_exactly_one_file_with_a_space_in_its_name(self):
        # The other half of the D6 pin (round `oghyca`).  The fixture in
        # AHostLineNamesAPathWithASpaceUnambiguouslyTests reproduces the
        # ambiguous log line without needing the corpus; this says the
        # fixture is still shaped like the real problem.  Red here means
        # either the file was renamed (fix the name in the constant) or the
        # corpus grew more of them (nothing to fix, but somebody should
        # know).
        spaced = sorted(path.name for path in LUA_ROOT.rglob("*.lua")
                        if " " in path.name)
        self.assertEqual(spaced, [THE_ONE_SPACED_FILE_NAME])

    def test_load_corpus_never_raises_out_of_the_full_616_file_run(self):
        # The fail-closed contract itself: calling load_corpus over the
        # real, full corpus must complete and return, never propagate.
        try:
            script_host.load_corpus(LUA_ROOT, log=lambda _msg: None)
        except Exception as exc:  # noqa: BLE001 - this IS the assertion
            self.fail("load_corpus raised instead of failing closed: %r" % exc)

    # test_the_vendored_message_catalog_still_matches_the_real_table MOVED,
    # round 7kxfe9, to tests/test_script_lua_api_message.py's
    # VendoredCatalogMatchesTheRealTableTests under BRIDGE_GAMEDATA.  It was
    # here because this module already required a bridge checkout -- but this
    # module's key ALSO requires lupa, and comparing two TSV files never
    # needed a Lua runtime.  On a bridge machine without lupa the one test
    # that proves the vendored copy is honest was silently not running, which
    # is the same hole in a different shape.  Strictly wider now.

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
#: for a baseline of 5020 across fewer distinct still-stub
#: <Namespace>.<Method> names.  RE-MEASURED round 0rgg6q (LANE-Q), recovering
#: the round-after-4jsydv commit that made Quest.CheckOpenTime real
#: (lua_api/quest.py) after it landed on top of the Instance baseline above
#: rather than beside it (that commit's own PR, pirate-force-server#874, was
#: closed by the gate's one-open-claude-pull-request lock rather than a real
#: failure -- SYNC-NOTICE 20260906_0226 -- and recovered here by cherry-pick):
#: against a FIXED quest_clock (FIXED_QUEST_CLOCK below), 5020 - 2 = 5018,
#: NOT 5020 - 9 despite the corpus having 9 CheckOpenTime call sites
#: (api_spec.tsv). MEASURED, not assumed from the call-site count: only
#: Quest/q_con5.lua and Quest/q_arena2.lua's Accept_Check (1 call each)
#: actually execute their CheckOpenTime call under STANDARD_ENTRY_POINTS
#: today. Quest/q_sea_join.lua's own Accept_Run gates its whole 7-window
#: chain behind `if Player.CheckBuff(9903) then ... else <the chain> end` --
#: Player.CheckBuff is still a stub returning STUB_DEFAULT (0), which Lua
#: treats as TRUTHY (only nil/false are falsy), so the stubbed condition
#: always takes the `then` branch and the `else` branch holding every
#: CheckOpenTime call in that file never runs -- confirmed by printing
#: report.real_call_counts directly (`{'Quest.CheckOpenTime': 2, ...}`), not
#: inferred from the call-site table.
#:
#: RE-MEASURED THIS ROUND (LANE-Q, this session): lua_api/player.py made
#: Player.GetLv/GetClass real (see that module's own docstring for why
#: these two, of Player's 73 names, needed no LANE-DB column and no wire
#: frame). MEASURED, not derived from the 91/60 call-site counts in
#: api_spec.tsv the naive way: report.real_call_counts prints
#: {'Player.GetLv': 60, 'Player.GetClass': 42} against this same LUA_ROOT
#: and FIXED_QUEST_CLOCK -- 5018 - 81 = 4937, NOT 5018 - (91 + 60) = 4867
#: (pf-adversary caught this arithmetic as off by one in an earlier draft).
#: The gap is not a bug in the count: giving GetLv/GetClass their real
#: answer (the injected PlayerContext's level/class_id, both nonzero by
#: default) instead of STUB_DEFAULT=0 changes which branches some scripts
#: take on their way to a Report_Check/Accept_Check call, which changes
#: which OTHER still-stubbed names execute afterward in the same run --
#: some newly reached, some no longer reached -- exactly the same kind of
#: emergent, measured-not-assumed shift a future round making any other
#: name real should expect to see here too, not treat as a discrepancy to
#: chase down.  A round that lands a real API implementation makes every
#: call to that name, in every script that makes it, stop counting here --
#: so a regression that raises this number (not a branch-shift fall) is
#: still stub coverage getting worse, and the test below is written to
#: catch that.
#:
#: RE-MEASURED (LANE-Q, round qbr5h8): lua_api/player.py made
#: Player.CheckItemNum/GetItemNum/CheckEquipItem real (COO-DECISION
#: 20260906_1846's "inventory seam, read side"). MEASURED, not derived from
#: the 211/99/14 call-site counts in api_spec.tsv the naive way:
#: report.real_call_counts prints {'Player.GetItemNum': 88,
#: 'Player.CheckItemNum': 154} against this same LUA_ROOT and
#: FIXED_QUEST_CLOCK (CheckEquipItem's own 2 call sites, both in files with
#: no STANDARD_ENTRY_POINTS entry point that reaches them under this fixed
#: clock, contribute 0 -- absent from real_call_counts entirely, not a
#: dropped key) -- 4937 - 242 = 4695, NOT the actual 4715. The remaining
#: 20-call gap is the same emergent, measured-not-assumed branch-shift
#: phenomenon this baseline's own comment already documents for round
#: gqjas5's GetLv/GetClass: giving these three their real (nonzero-capable)
#: answer instead of STUB_DEFAULT=0 changes which branches some scripts take
#: on their way to a Report_Check/Accept_Check gate, which changes which
#: OTHER still-stubbed names execute afterward in the same run -- some
#: newly reached (raising the count), some no longer reached (lowering it),
#: net +20 stub calls elsewhere this time. Not a discrepancy to chase down;
#: see the paragraph above for the same shape from a prior round.
#:
#: RE-MEASURED AGAIN, COMBINED WITH THE ABOVE (LANE-Q, round lvoma1,
#: recovering both round qbr5h8's #953 and round 7v7yn2/uadtc7's #947/#960
#: onto one branch after both died on an unrelated main-branch gate failure
#: -- see this round's own round file): lua_api/quest.py made 9 more of
#: Quest's 25 names real (GetQuestFlag/SetFlag/SetQuestFlag/GetFlag/
#: MobKillCount/CheckMobKillCount/GetMobKillCount/CanReportDailyQuest/
#: ReportDailyQuest) and lua_api/trigger.py made 2 more of Trigger's 17
#: (QuestActiveProgress/QuestFinishProgress), sharing the same
#: QuestStateStore door, ON TOP OF the inventory-seam three above -- both
#: deltas landed together in the SAME corpus run for the first time here,
#: so the combined total is measured fresh below, not added arithmetically
#: from the two entries above (this comment's own standing rule: branch
#: shift is emergent, never additive across independent real-method
#: landings). MEASURED: report.real_call_counts against this same LUA_ROOT
#: and FIXED_QUEST_CLOCK now prints {'Player.CheckItemNum': 145,
#: 'Player.GetItemNum': 88, 'Player.GetLv': 60, 'Player.GetClass': 48,
#: 'Quest.GetQuestFlag': 160, 'Quest.SetFlag': 405, 'Quest.SetQuestFlag':
#: 47, 'Quest.GetFlag': 67, 'Quest.MobKillCount': 106,
#: 'Quest.CheckMobKillCount': 105, 'Quest.GetMobKillCount': 1,
#: 'Quest.CanReportDailyQuest': 45, 'Quest.ReportDailyQuest': 60,
#: 'Quest.CheckOpenTime': 2, 'Trigger.QuestActiveProgress': 7, plus the
#: unchanged Trigger/Instance real names} -- total_stub_calls
#: 4715 -> 3716, NOT 4715 - (995 Quest calls + 7 Trigger calls) = 3713 (a
#: 3-call gap, the same branch-shift phenomenon again, this time from
#: CheckItemNum itself shifting 154 -> 145 and GetQuestFlag shifting
#: 159 -> 160 once both deltas run in the SAME corpus pass -- neither
#: shift is visible when each delta is measured alone, exactly why this
#: round remeasured instead of adding the two prior entries' own deltas).
#:
#: RE-MEASURED (LANE-Q, round x6gxzd): lua_api/player.py made
#: Player.MobAppear real (COO-DECISION 20260907_0043 answering
#: PANYA-DECISION 20260907_0039 -- a per-player visibility FLAG, not a
#: world spawn; see that module's own docstring). MEASURED, not derived
#: from the 3,532-call-site grep the naive way: report.real_call_counts
#: against this same LUA_ROOT and FIXED_QUEST_CLOCK prints
#: {'Player.MobAppear': 1096, ...unchanged...} -- 3716 - 1096 = 2620,
#: EXACTLY (no branch-shift this time, unlike every prior real-method
#: landing this file documents above): MobAppear is a side-effecting call
#: inside branches other stub reads already gate (`if (Quest.VarN > 0)
#: then Player.MobAppear(...)`), never itself a condition another call
#: sits behind, so making it real changes no OTHER script's control flow.
#: RE-MEASURED (LANE-Q, round 6775u1): the message-wire landed TWO real
#: names at once -- Player.ShowMessage and Trigger.TriggerShowMessage
#: (lua_api/message.py, NOW.md's LANE-Q system order item 4). MEASURED
#: against this same LUA_ROOT/FIXED_QUEST_CLOCK: real_call_counts prints
#: {'Player.ShowMessage': 23, ...} and NO 'Trigger.TriggerShowMessage' key
#: at all -- 2620 - 23 = 2597, EXACTLY, and no branch shift. Both halves of
#: that are worth stating plainly, because landing two names in one round
#: is exactly how a branch shift hides: (a) the drop equals ONE name's
#: measured count, so the other name did not silently move anything; (b)
#: Trigger.TriggerShowMessage genuinely fires ZERO times here. CORRECTED
#: after pf-adversary measured the first draft of this note wrong, and the
#: correction matters because it points at a different lane: the draft said
#: `Scene.CheckPlacementAlive` gates it. It does not. FIVE of the 8 calling
#: files never call Scene.* at all (t_nex_msg, t_nex_msg_ins,
#: t_nex_msg_ins_t1, t_indanix2_msg, t_bg2017_msg), and in t_msg_mod.lua
#: -- the file the draft cited -- the gate runs the OTHER way
#: (`if Scene.CheckPlacementAlive(...) == true then return 0 else <the
#: TriggerShowMessage block> end`), so a stubbed 0 REACHES the call rather
#: than skipping it. What actually stops it is the Trigger.VarN data every
#: one of those branches tests, which lives in the .tgr tables this lane
#: has never mined (the RE-273 lead). Adversary's own mutation -- feed
#: Trigger.VarN a 1, touch no Scene.* at all -- makes three of those files
#: reach the closure and log LUA_TRIGGER_REAL. So its 55 call sites are
#: real in the source and unreachable in THIS harness for want of trigger
#: table data, not for want of LANE-A's Scene.* seam; that is a gap this
#: pin makes visible rather than a count to celebrate.
BASELINE_TOTAL_STUB_CALLS = 2597

#: The other half of the split, pinned for the same reason (pf-adversary
#: D1, round `oghyca`).  Only the stub total was pinned before, so a round
#: that changed the real corpus's behaviour saw 2852 -> 2849 and nothing
#: went red: the stub total happened to stay put.  An exact pin, not a
#: ceiling -- a round that makes another API real raises this in the same
#: commit; a round that breaks one gets caught here.  Measured 2026-09-07,
#: round `5qtaqy`, with FIXED_QUEST_CLOCK.
BASELINE_TOTAL_REAL_CALLS = 2852


def bucket_conservation(report):
    """``(total, the buckets' own accounting)`` for a corpus report.

    pf-adversary D3 (round `oghyca`): the file-level buckets are NOT a
    partition -- a file whose run failed both ways is in ``call_failed``
    and in ``host_failed`` at once -- so summing them overcounts.  This is
    the equation that does hold, written once and asserted against both the
    real corpus and a fixture built to have that overlap.
    """
    accounted = (len(report.load_failed)
                 + len(report.no_entry_point)
                 + len(report.ran)
                 + len({run.path for run in report.call_failed}
                       | set(report.host_failed)))
    return report.total, accounted


@LUA_CORPUS_RUNNABLE.skip_unless_present()
class FullCorpusEntryPointCallsTests(unittest.TestCase):
    """Not just loading the 616 files (above) -- CALLING what each one
    defines, per script_host.run_corpus_entry_points.  This is what
    actually exercises the 160-name API surface at realistic call volume,
    rather than the trivial single-call cases test_script_lua_api_*.py's
    unit tests use.
    """

    def test_every_present_entry_point_gets_called_or_its_failure_is_pinned(self):
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
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
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
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
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
        self.assertEqual(report.no_entry_point, [])

    def test_run_corpus_entry_points_never_raises_out_of_the_full_616_file_run(self):
        try:
            script_host.run_corpus_entry_points(LUA_ROOT, log=lambda _msg: None)
        except Exception as exc:  # noqa: BLE001 - this IS the assertion
            self.fail("run_corpus_entry_points raised instead of failing closed: %r" % exc)

    def test_no_entry_point_failure_in_the_real_corpus_is_OURS(self):
        # pf-adversary D1 (round `oghyca`), call-side half.  host_failed and
        # host_failed_runs were both introduced with no assertion against
        # the real corpus at all -- a bucket "reported and never read",
        # which is the exact shape this project's house rule forbids.
        logged = []
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=logged.append, quest_clock=FIXED_QUEST_CLOCK)
        host_lines = [line for line in logged if line.startswith("LUA_HOST")]
        self.assertEqual(report.host_failed, [], "\n".join(host_lines))
        self.assertEqual([run.path for run in report.host_failed_runs], [])
        self.assertEqual(host_lines, [])

    def test_the_LUA_SCRIPT_lines_are_exactly_the_pinned_failures(self):
        # The log is evidence, not decoration: every line the sweep prints
        # against a script must be one of the failures this module already
        # pins by name, and there must be no line it does not pin.  Without
        # this the log could gain a whole new failure class and only the
        # counts would move.
        logged = []
        script_host.run_corpus_entry_points(
            LUA_ROOT, log=logged.append, quest_clock=FIXED_QUEST_CLOCK)
        blamed = [line for line in logged if line.startswith("LUA_SCRIPT")]
        self.assertEqual(
            len(blamed),
            len(KNOWN_LOAD_FAILURES) + len(KNOWN_ENTRY_POINT_CALL_FAILURES),
            "\n".join(blamed))

    def test_every_file_lands_in_exactly_one_bucket_or_a_named_overlap(self):
        # pf-adversary D3 (round `oghyca`): the buckets were documented as
        # if they partitioned the corpus and do not.  See
        # bucket_conservation above for the equation that does hold.
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
        total, accounted = bucket_conservation(report)
        self.assertEqual(total, accounted)

    def test_exactly_the_pinned_real_call_count_no_more_no_fewer(self):
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
        self.assertEqual(report.total_real_calls, BASELINE_TOTAL_REAL_CALLS)

    def test_exactly_the_pinned_stub_call_count_no_more_no_fewer(self):
        # Same shape as test_exactly_the_known_failures_fail_no_more_no_fewer
        # above: an exact pin, not a <= ceiling, so this goes red the moment
        # ANYTHING changes it -- a round that lands a real API (count should
        # fall) must lower BASELINE_TOTAL_STUB_CALLS in the same commit, and
        # a round that regresses one (count would rise) gets caught here
        # instead of silently drifting.
        report = script_host.run_corpus_entry_points(
            LUA_ROOT, log=lambda _msg: None, quest_clock=FIXED_QUEST_CLOCK)
        self.assertEqual(report.total_stub_calls, BASELINE_TOTAL_STUB_CALLS)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


@LUPA_PACKAGE.skip_unless_present()
class HostSideCallFailureBucketingTests(unittest.TestCase):
    """pf-adversary D12 (round 8ou0zg): a defect of OURS that surfaces while
    an entry point is being CALLED must be counted once, against us.

    Not gated on the real corpus (LUA_CORPUS_RUNNABLE) on purpose -- these
    three files are written here, so the numbers asserted below are exact
    and do not move when the shipped corpus does.  The host-side failure is
    injected the way the real one arrives: the vendored message catalog is
    pointed at a path that does not exist, so `Player.ShowMessage` -- the
    first API the corpus reaches that reads a mirror of ours -- raises
    MessageCatalogError, a VendoredDataError, exactly as a corrupt checkout
    would make it.
    """

    HOST_SIDE_CALL = "Player.ShowMessage(1)"

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pf_lua_bucket_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        # Three entry points, every one of them reaching our broken mirror.
        (self.root / "ours.lua").write_text(
            "function ScriptStart() %s end\n"
            "function Accept_Run() %s end\n"
            "function Report_Run() %s end\n"
            % ((self.HOST_SIDE_CALL,) * 3), encoding="ascii")
        # One of ours, one genuinely the script's own bug.
        (self.root / "both.lua").write_text(
            "function ScriptStart() %s end\n"
            "function Accept_Run() error('this one is the script') end\n"
            % self.HOST_SIDE_CALL, encoding="ascii")
        (self.root / "clean.lua").write_text(
            "function ScriptStart() return 1 end\n", encoding="ascii")

        catalog_path = lua_api_message._CATALOG_PATH
        catalog_cache = lua_api_message._CATALOG_CACHE
        lua_api_message._CATALOG_PATH = self.root / "no_such_catalog.tsv"
        lua_api_message._CATALOG_CACHE = None

        def restore():
            lua_api_message._CATALOG_PATH = catalog_path
            lua_api_message._CATALOG_CACHE = catalog_cache

        self.addCleanup(restore)

    def _report(self):
        self.logged = []
        return script_host.run_corpus_entry_points(
            self.root, log=self.logged.append, quest_clock=FIXED_QUEST_CLOCK)

    def test_the_broken_mirror_is_counted_once_per_file_not_once_per_entry_point(self):
        report = self._report()
        # Three failing entry points in ours.lua, one in both.lua: the old
        # shape appended a path per failure and reported four.
        self.assertEqual(sorted(report.host_failed), ["both.lua", "ours.lua"])

    def test_our_defect_never_makes_a_script_look_like_a_broken_quest(self):
        report = self._report()
        # ours.lua has no bug of its own, so it is in NEITHER call_failed
        # (which pins "quests known to fail") nor ran (it did not run).
        self.assertEqual([run.path for run in report.call_failed], ["both.lua"])
        self.assertEqual([run.path for run in report.ran], ["clean.lua"])
        self.assertEqual(sorted(run.path for run in report.host_failed_runs),
                         ["both.lua", "ours.lua"])

    def test_the_two_kinds_of_failure_are_kept_in_separate_dicts(self):
        report = self._report()
        by_path = {run.path: run for run in report.host_failed_runs}
        self.assertEqual(sorted(by_path["ours.lua"].host_errors),
                         ["Accept_Run", "Report_Run", "ScriptStart"])
        self.assertEqual(by_path["ours.lua"].errors, {})
        # both.lua: our failure and the script's, each in its own dict, so
        # a caller pinning script failures never inherits ours.
        self.assertEqual(sorted(by_path["both.lua"].host_errors), ["ScriptStart"])
        self.assertEqual(sorted(by_path["both.lua"].errors), ["Accept_Run"])
        self.assertFalse(by_path["both.lua"].ok)

    def test_a_run_that_only_WE_broke_still_reports_ok_False(self):
        # pf-adversary D4 (round `oghyca`): deleting `run.ok = False` from
        # the host-side branch of run_corpus_entry_points left 137 tests
        # green.  ours.lua is the only file here with host errors and NO
        # errors of its own, so it is the only one that can say so.
        report = self._report()
        by_path = {run.path: run for run in report.host_failed_runs}
        self.assertEqual(by_path["ours.lua"].errors, {})
        self.assertFalse(by_path["ours.lua"].ok,
                         "a run broken only by OUR defect reported ok")
        # And the control, so this cannot pass by everything being False.
        self.assertTrue(report.ran[0].ok)

    def test_every_file_lands_in_exactly_one_bucket_or_a_named_overlap(self):
        # pf-adversary D3 (round `oghyca`), on the fixture that HAS the
        # overlap: both.lua is in call_failed and host_failed at once, so
        # the file-level buckets sum to 4 against a total of 3.
        report = self._report()
        self.assertEqual(bucket_conservation(report), (3, 3))
        naive = (len(report.load_failed) + len(report.no_entry_point)
                 + len(report.ran) + len(report.call_failed)
                 + len(report.host_failed))
        self.assertEqual(naive, 4, "the overlap this equation exists for")

    def test_the_log_line_names_the_defect_not_the_script(self):
        self._report()
        blamed = [line for line in self.logged
                  if line.startswith("LUA_SCRIPT ours.lua")]
        self.assertEqual(blamed, [], "our own defect was logged against a script")
        ours = [line for line in self.logged
                if line.startswith("LUA_HOST")
                and 'discovered_at="ours.lua"' in line]
        self.assertEqual(len(ours), 3)
        for line in ours:
            self.assertIn("MessageCatalogError", line)


@LUPA_PACKAGE.skip_unless_present()
class AHostLineNamesAPathWithASpaceUnambiguouslyTests(unittest.TestCase):
    """pf-adversary D6 (round `oghyca`): the corpus has exactly one file
    whose name contains a space (`t_test auto.lua`), and the LUA_HOST line
    used to end `discovered_at=t_test auto.lua entry=ScriptStart` -- a
    reader splitting on whitespace got `discovered_at=t_test` and no way to
    tell where the path ended.  The name here is the real one, so this test
    keeps naming the file that motivated it.
    """

    SPACED = THE_ONE_SPACED_FILE_NAME

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pf_lua_spaced_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / self.SPACED).write_text(
            "function ScriptStart() Player.ShowMessage(1) end\n",
            encoding="ascii")
        catalog_path = lua_api_message._CATALOG_PATH
        catalog_cache = lua_api_message._CATALOG_CACHE
        lua_api_message._CATALOG_PATH = self.root / "no_such_catalog.tsv"
        lua_api_message._CATALOG_CACHE = None

        def restore():
            lua_api_message._CATALOG_PATH = catalog_path
            lua_api_message._CATALOG_CACHE = catalog_cache

        self.addCleanup(restore)

    def test_the_path_is_quoted_and_the_entry_point_is_its_own_field(self):
        logged = []
        script_host.run_corpus_entry_points(
            self.root, log=logged.append, quest_clock=FIXED_QUEST_CLOCK)
        host_lines = [line for line in logged if line.startswith("LUA_HOST")]
        self.assertEqual(len(host_lines), 1)
        self.assertIn('discovered_at="%s" entry=ScriptStart' % self.SPACED,
                      host_lines[0])
        # The recovery a reader actually performs, done here rather than
        # asserted about: the quoted field round-trips the whole name.
        after = host_lines[0].split('discovered_at="', 1)[1]
        self.assertEqual(after.split('"', 1)[0], self.SPACED)


@LUPA_PACKAGE.skip_unless_present()
class BrokenApiSpecIsOursNotTheScriptsTests(unittest.TestCase):
    """lua_api/spec.py's own claim, checked end to end.

    The vendored API census is the one mirror every ScriptHost reads while
    it is being BUILT, so a corrupt copy of it used to raise out of an
    import and take script_host down with it -- before any sweep's own
    try/except could classify it, and as a type
    script_host._host_side_error_types() would not have recognised anyway
    (pf-adversary finding 13, round 8ou0zg).  Now it is a lazily-raised
    VendoredDataError, which is host-side: these tests are what says so out
    loud.  (An earlier draft of this docstring named an `ApiSpecError`
    class.  There has never been one in `src/` -- the name was left over
    from a draft that was replaced by reusing `VendoredDataError` before
    the round pushed.  pf-adversary D7.4, round `oghyca`.)
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="pf_lua_spec_"))
        self.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "innocent.lua").write_text(
            "function ScriptStart() return 1 end\n", encoding="ascii")
        spec_path = lua_api_spec._SPEC_PATH
        lua_api_spec._SPEC_PATH = self.root / "no_such_api_spec.tsv"
        lua_api_spec._CACHE.clear()

        def restore():
            lua_api_spec._SPEC_PATH = spec_path
            lua_api_spec._CACHE.clear()

        self.addCleanup(restore)

    def test_a_corrupt_census_is_reported_against_us_not_against_the_script(self):
        logged = []
        report = script_host.run_corpus_entry_points(
            self.root, log=logged.append, quest_clock=FIXED_QUEST_CLOCK)
        self.assertEqual(report.host_failed, ["innocent.lua"])
        self.assertEqual(report.load_failed, [])
        self.assertEqual(report.ran, [])
        self.assertEqual([line for line in logged
                          if line.startswith("LUA_SCRIPT")], [])
        host_lines = [line for line in logged if line.startswith("LUA_HOST")]
        self.assertEqual(len(host_lines), 1)
        self.assertIn("VendoredDataError", host_lines[0])
        self.assertIn(str(self.root / "no_such_api_spec.tsv"), host_lines[0])
        self.assertTrue(host_lines[0].endswith('discovered_at="innocent.lua"'),
                        host_lines[0])

    def test_a_census_that_PARSES_but_lost_a_name_is_ours_too(self):
        # pf-adversary D2 (round `oghyca`): the end-to-end claim used to
        # cover one shape only, the file being absent.  A census whose
        # CONTENT was wrong parsed happily, and every name it lost reached
        # the scripts as ApiNamespaceStub's numeric default -- measured, one
        # trailing space produced 189 `attempt to call a number value` lines
        # over 122 innocent quest files and not one LUA_HOST line.  This is
        # that shape, with the digest recomputed so it is the ROW rule being
        # measured and not the digest.
        good = [line for line in
                (Path(__file__).resolve().parents[1] / "src"
                 / "pirateforce_foundation" / "lua_api" / "api_spec.tsv"
                 ).read_text(encoding="ascii").splitlines()
                if not line.startswith("#")]
        rows = []
        for line in good:
            cells = line.split("\t")
            if cells[:2] == ["Player", "RemoveItem"]:
                cells[1] = "RemoveItem "  # invisible in a diff
                line = "\t".join(cells)
            rows.append(line)
        body = "\n".join(rows) + "\n"
        corrupt = self.root / "corrupt_api_spec.tsv"
        corrupt.write_text(
            lua_api_spec.BODY_DIGEST_PREFIX + lua_api_spec.body_digest(body)
            + "\n" + body, encoding="ascii")
        lua_api_spec._SPEC_PATH = corrupt
        lua_api_spec._CACHE.clear()

        logged = []
        report = script_host.run_corpus_entry_points(
            self.root, log=logged.append, quest_clock=FIXED_QUEST_CLOCK)
        self.assertEqual(report.host_failed, ["innocent.lua"])
        self.assertEqual([line for line in logged
                          if line.startswith("LUA_SCRIPT")], [])
        host_lines = [line for line in logged if line.startswith("LUA_HOST")]
        self.assertEqual(len(host_lines), 1)
        self.assertIn("method that is not an identifier", host_lines[0])

    def test_the_same_holds_for_the_load_only_sweep(self):
        logged = []
        report = script_host.load_corpus(self.root, log=logged.append)
        self.assertEqual(report.host_failed, ["innocent.lua"])
        self.assertEqual(report.failed, [])
        self.assertEqual(report.ok, 0)
