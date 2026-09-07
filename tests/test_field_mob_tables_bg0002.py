"""LANE-B: Bg0002's hostile roster, mined AND wired (unlike Bg0015's).

PANYA-DECISION 2026-08-27T20:10+07:00 ("M1-P" item 3, notes_to_chief/
20260827_2010_PANYA-DECISION-pause-M2-M1-identity-first-Prison-Exile-
Bg0002-MOBSET-equals-nID.md) gave lane B one instruction: mon 27-35 in
Bg0002's census, faction pair (1, 6) unchanged, widen death scope to cover
Bg0002 -- and to expand field_mobs.assert_single_scene_tables rather than
disable it. Unlike field_mob_tables_bg0015.py (COO-DECISION 2026-08-26
12:46, deliberately kept unwired pending a second travel gate), this
module IS imported under src/pirateforce_foundation/ this round: by
field_mobs.py (field_mobs.load_roster(scene=field_mobs.BG0002_SCENE)) and
by mob_death.py (WIDENING_RULING_SCENES).  So this file's own tests are
shaped around "wired for real and behaving correctly", not around "stayed
inert" -- there is no test_nothing_under_src_imports_this_module guard
here, on purpose, because the opposite is true and is meant to be true.

The three tests that matter most, mirroring test_field_mob_tables_bg0015.py's
own three:

``test_regenerating_reproduces_the_committed_module_byte_for_byte`` is the
same discipline every GENERATED module in this tree is held to: it is only
trustworthy if the generator that wrote it can reproduce it right now, from
the same committed game data.

``test_pinned_scene_and_hostile_count`` pins the concrete numbers this round
measured: 17 hostile placements, 4 distinct templates (31 Tornado Eagle, 34
Fighting Fish soldier, 35 Fighting Fish Sergeant, 103 Orc Chief) -- NOT the
27-35 range the decision letter names, because templates 27, 28, 29, 30, 32
and 33 all carry a multi-variant CONSTDATA_TH__MOBS.s_OUTFIT and fail the
mining tool's own "single unambiguous basename" selection rule.

``test_field_mob_tables_bg0001_is_untouched_by_this_round`` pins the fact
that the live/default roster (bg0001, Port Royal) was not touched while
mining Bg0002: its sha256 must equal the value test_field_mob_tables_
bg0015.py already measured and pins for the same reason.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0002.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

# Measured 2026-08-26 by test_field_mob_tables_bg0015.py, re-quoted here
# rather than re-measured, so both files pin the SAME frozen value for the
# SAME reason -- if bg0001's roster ever changes for a real reason this
# constant moves in that same commit, in both files, and says why.
# ~~"158704080cc23180d0829d81848119327f335461519a848a1cab599aefaabb9e", 3978
# bytes~~ -- moved in round szdkgs, which is the "real reason" the comment
# above says this constant may move for: bg0001's roster was re-mined through
# the RE-128 crosswalk (four placements are now n_ID 916 Training Iron Man;
# the other nine are labelled as the legacy set-number reading pending
# migration).  The old digest is kept, not deleted, so the change is auditable
# from either side.
# ROUND 8ftmbx: moved again, and again by bg0001's OWN lane, not by this
# round -- COO-DECISION 2026-08-29T00:41+07:00 withdrew the nine set-number
# rows.  The previous digest is kept, not deleted:
# ~~b9c142ba8e1b4702cfad2b9cbbe5bd40a910be56120fffb5ace28681c9910fee~~
# ROUND hor2lh: re-pinned, and by a change that touched ALL SIX generated
# tables on purpose -- pf-adversary D14 of round r6isy5b found the
# generator stamping every scene with a control sentence that is true only
# for bg0001, so the corrected comment was regenerated into each module.
# Only the comment block moved; every row, digest and census value in
# bg0001 is byte-identical (verified by regenerating and diffing).  The
# previous digest is kept, not deleted:
# ~~574fdca1391eb0aa4bc4a5a2b46b50c090839a86baf94426573312afff2866a5~~
BG0001_UNTOUCHED_SHA256 = (
    "c1a341c9d7721db45b07e2e7df2840719da5fcbcf5521d7f31eabd4a1ce26934"
)
# ROUND 8ftmbx: ~~10570~~ -> 9704.  bg0001's own module shrank when
# COO-DECISION 2026-08-29T00:41+07:00 withdrew its nine set-number rows;
# this constant exists to prove THIS round did not touch that file, so it
# tracks that file's size and is re-pinned whenever bg0001's own lane
# changes it on purpose.
# ROUND hor2lh: ~~9708~~ -> 12316, the comment correction described
# above.  This constant still means "this round did not touch that
# file"; it is re-pinned when a round changes bg0001 on purpose.
BG0001_UNTOUCHED_SIZE = 12316

EXPECTED_SCENE = "Bg0002"
# ROUND najn72: the scene was re-mined under the CROSSWALK identity rule and
# the owner's outfit rule (NOW.md `1313` "an enemy is n_RANK + n_AI_COMBAT,
# s_OUTFIT decides nothing"; owner tick 20260908_0025 item 1, "do them
# together"), regenerated with
#   tools/pf_mine_scene_mob_roster.py --gamedata <bridge>/gamedata
#     --scene Bg0002 --identity-rule cline --outfit-rule any
# ~~17 rows / 4 templates {31, 34, 35, 103} / 49 unambiguous~~ ->
# 52 rows / 9 templates {27..35} / 104 unambiguous.  The templates are the
# whole 27-35 census block the PANYA-DECISION ADDENDUM named, and
# mob_death's Bg0002 widening ruling moved to exactly that set in the same
# commit -- which is the point of the owner's "together": neither the roster
# nor the ruling is allowed to be ahead of the other.
EXPECTED_HOSTILE_COUNT = 52
EXPECTED_TEMPLATE_COUNT = 9
EXPECTED_TEMPLATES = set(range(27, 36))
EXPECTED_UNAMBIGUOUS = 104
EXPECTED_IDENTITY_RULE = "cline"
EXPECTED_OUTFIT_RULE = "any"


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_generated_module():
    spec = importlib.util.spec_from_file_location(
        "field_mob_tables_bg0002_check", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0002ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present: shape, ASCII, wiring."""

    def test_module_file_exists(self) -> None:
        self.assertTrue(MODULE_PATH.is_file())

    def test_module_is_pure_ascii(self) -> None:
        raw = MODULE_PATH.read_bytes()
        non_ascii = [b for b in raw if b >= 0x80]
        self.assertEqual(non_ascii, [])

    def test_module_carries_the_generated_header(self) -> None:
        text = MODULE_PATH.read_text(encoding="ascii")
        self.assertTrue(text.startswith('"""GENERATED - do not hand-edit.'))

    def test_pinned_scene_and_hostile_count(self) -> None:
        module = _load_generated_module()
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        self.assertEqual(len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        distinct_templates = {row[1] for row in module.HOSTILE_PLACEMENTS}
        self.assertEqual(len(distinct_templates), EXPECTED_TEMPLATE_COUNT)
        self.assertEqual(distinct_templates, EXPECTED_TEMPLATES)
        self.assertEqual(
            module.PREDICATE_CENSUS["unambiguous"], EXPECTED_UNAMBIGUOUS
        )
        self.assertEqual(
            module.PREDICATE_CENSUS["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT
        )

    def test_the_whole_27_35_monster_block_is_in_this_roster(self) -> None:
        # ROUND najn72.  ~~test_template_27_mountain_deer_is_not_in_this_
        # roster~~ INVERTED, and the old reason is kept because it is what
        # changed: templates 27-30, 32 and 33 used to be absent because
        # CONSTDATA_TH__MOBS.tsv gives them a ";"-joined multi-variant
        # s_OUTFIT, which failed the mining tool's single-unambiguous-
        # basename rule.  The owner WITHDREW that rule (COO-DECISION
        # 20260907_1346, NOW.md `1313`: s_OUTFIT has no effect on who is an
        # enemy), so their absence WAS the oversight and this table is now
        # the whole 27-35 monster block of the decision letter's own
        # numbering (1-26 are single-instance NPCs).
        # Template 27 (Mountain Deer) is now in TWO places on purpose: here
        # as a real Bg0002 placement, and in mob_diag_multi_object.py as the
        # hand-mined DIAG-001 body standing at the bg0001 test point.  The
        # two are separated by SCENE, not by template -- mob_death's
        # WIDENING_RULING_SCENES ties each ruling to one scene and kill()
        # checks mob.scene, which tests/test_mob_death.py drives across the
        # crossing rather than asserting here.
        module = _load_generated_module()
        templates = {row[1] for row in module.HOSTILE_PLACEMENTS}
        self.assertEqual(templates, EXPECTED_TEMPLATES)
        for expected in (27, 28, 29, 30, 32, 33):
            self.assertIn(expected, templates)
        # And the rule labels say so per row, so nothing infers the rule
        # from the counts above.
        self.assertEqual(module.IDENTITY_RULE, EXPECTED_IDENTITY_RULE)
        self.assertEqual(
            set(module.IDENTITY_RULE_PER_PLACEMENT.values()),
            {EXPECTED_IDENTITY_RULE})

    def test_field_mob_tables_bg0001_is_untouched_by_this_round(self) -> None:
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(len(raw), BG0001_UNTOUCHED_SIZE)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), BG0001_UNTOUCHED_SHA256)

    def test_bg0001_scene_constant_is_still_the_live_default(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "field_mob_tables_bg0001_check", BG0001_PATH
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.SCENE, "bg0001")

    def test_this_module_IS_imported_under_src_unlike_bg0015s(self) -> None:
        """The opposite of test_field_mob_tables_bg0015.py's own guard.

        Walks the same AST-plus-string-sweep shape that file's
        test_only_the_approved_hostile_composer_imports_the_bg0015_module
        (renamed this round; was test_nothing_under_src_imports_the_bg0015_
        module before COO-DECISION 2026-08-31T16:48+07:00 unlocked one
        approved importer) uses, but asserts
        the module name IS referenced somewhere under src/ -- pf-adversary
        precedent (that file, this same round) says a vacuous scan (an
        empty rglob) makes either direction of this kind of check pass for
        the wrong reason, so the file-count floor is repeated here too.
        """
        py_files = sorted(SRC.rglob("*.py"))
        self.assertGreater(
            len(py_files), 30,
            "src/**/*.py scan returned suspiciously few files (%d) -- "
            "the check below would be vacuous" % len(py_files),
        )
        offenders = []
        for path in py_files:
            if path == MODULE_PATH:
                continue
            text = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError:
                self.fail("could not parse %s" % path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "field_mob_tables_bg0002" in alias.name:
                            offenders.append(str(path))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "field_mob_tables_bg0002" in node.module:
                        offenders.append(str(path))
                    for alias in node.names:
                        if "field_mob_tables_bg0002" in alias.name:
                            offenders.append(str(path))
        # AT LEAST these two real IMPORT statements (a stricter, positive
        # version of test_field_mob_tables_bg0015.py's negative guard) --
        # a comment/docstring MENTION elsewhere (mob_diag_multi_object.py's
        # own provenance note cites this module by name without importing
        # it) is not what this test is about, so it checks actual import
        # statements via AST, not a text sweep.
        self.assertIn(
            str(SRC / "pirateforce_foundation" / "field_mobs.py"), offenders)
        self.assertIn(
            str(SRC / "pirateforce_foundation" / "mob_death.py"), offenders)


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0002RegenerateAndDiffTest(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_regenerating_reproduces_the_committed_module_byte_for_byte(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        # ROUND najn72: ~~check_controls~~ -> check_crosswalk_controls.  The
        # tool picks the control by rule (see its main()), and this scene is
        # on the crosswalk now: the set-number control re-derives an identity
        # scheme this scene no longer uses, and its findings are not what the
        # module carries.  Taken from the tool's own branch rather than
        # hand-copied so a control change lands here too.
        controls = tool.check_crosswalk_controls(sources)
        census = tool.predicate_census(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        roster = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        # ROUND najn72: "a future round that re-mines this scene through the
        # crosswalk has to come here and say so" -- this is that round, and
        # this is it saying so.  ~~IDENTITY_RULE_SETNUM + the tool's default
        # outfit rule~~ -> the crosswalk and the owner's outfit rule, both
        # named explicitly for the same reason the old pair was: the tool's
        # DEFAULTS must not be able to move this scene silently, in either
        # direction.  NOW.md `1313` rules bg0002 onto `cline` and takes
        # s_OUTFIT out of the hostility decision; the owner's tick
        # 20260908_0025 item 1 orders it in one commit with mob_death's
        # widening ruling.
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census,
            rule=tool.IDENTITY_RULE_CLINE, cline_type=sources.cline_type,
            controls=controls,
            withdrawn=tool.withdrawn_under_rule(
                sources, tool.IDENTITY_RULE_CLINE,
                outfit_rule=tool.OUTFIT_RULE_ANY),
            unresolved=tool.unresolved_placements(
                sources, tool.IDENTITY_RULE_CLINE,
                outfit_rule=tool.OUTFIT_RULE_ANY),
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(
                    sources, tool.IDENTITY_RULE_CLINE,
                    outfit_rule=tool.OUTFIT_RULE_ANY)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
            outfit_rule=tool.OUTFIT_RULE_ANY,
        )
        committed = MODULE_PATH.read_text(encoding="ascii")
        self.assertEqual(
            regenerated, committed,
            "src/pirateforce_foundation/field_mob_tables_bg0002.py is stale "
            "- regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0002 --out <this file>",
        )

    def test_the_predicate_census_matches_the_recorded_finding(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        census = tool.predicate_census(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["drops_normal"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)

    def test_hostile_roster_count_is_fifty_two_from_live_gamedata(self) -> None:
        # ROUND najn72: ~~..._is_seventeen_...~~ -> fifty-two, and the rules
        # are named at the call rather than inherited from the tool's
        # defaults (see the byte-for-byte control above for why).
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        tool.check_controls(sources)
        roster = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        self.assertEqual(len(roster), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row["template_id"] for row in roster}), EXPECTED_TEMPLATE_COUNT
        )
        self.assertEqual(
            {row["template_id"] for row in roster}, EXPECTED_TEMPLATES
        )

    def test_template_27_was_excluded_by_the_outfit_half_alone(self) -> None:
        # Confirms, against LIVE gamedata rather than a hand-typed claim,
        # that template 27 (Mountain Deer) really does pass the
        # RANK+AI_COMBAT hostility predicate and really was excluded solely
        # by the outfit-unambiguous half of the selection rule.
        # ROUND najn72: the claim is now provable IN BOTH DIRECTIONS on the
        # same sources, which is strictly stronger than the one-sided
        # absence it used to assert -- flip only the outfit rule, with the
        # identity rule held at the crosswalk, and template 27 appears.  That
        # is the whole content of "the outfit half alone", and it is why the
        # owner withdrawing that half (COO-DECISION 20260907_1346, NOW.md
        # `1313`) put the 27-35 block into this scene's roster.
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        mob27 = sources.mobs.get("27")
        self.assertIsNotNone(mob27)
        self.assertTrue(tool._nonzero(mob27, "n_RANK"))
        self.assertTrue(tool._nonzero(mob27, "n_AI_COMBAT"))
        outfit = (mob27.get("s_OUTFIT") or "").strip()
        self.assertIn(";", outfit)
        withdrawn_rule = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_UNAMBIGUOUS)
        self.assertNotIn(27, {row["template_id"] for row in withdrawn_rule})
        owners_rule = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        self.assertIn(27, {row["template_id"] for row in owners_rule})

    #: R322B, attended 2026-09-07: the console this scene printed on the
    #: owner's machine was ``MOB_CENSUS_HOSTILITY scene_id=2 roster=12
    #: backed=12 refused=8``, and on screen a Desert Eagle stood with a GREEN
    #: name beside a PINK Fighting Fish.  The owner's question was "why is
    #: only the fish attackable".  This is the answer, as data: six Mob-Sets
    #: whose leader passes the rank+combat-AI half of the selection rule and
    #: is refused by the outfit half alone.  Mob-Set number -> (placements in
    #: this scene, resolved n_ID, displayed name).  Every value re-derived
    #: from live gamedata by the test below; the table is here so a reader
    #: sees the size of the gap without running anything.
    OUTFIT_AMBIGUOUS_HOSTILE_SETS = {
        27: (4, 27, "Mountain Deer"),
        28: (6, 28, "Drunk wolf pirates"),
        29: (7, 29, "Lion pirates"),
        30: (11, 30, "Desert Eagle"),
        32: (3, 32, "Rock turtle"),
        33: (9, 33, "Sediment Wolf"),
    }

    def test_the_r322b_gap_is_the_outfit_half_and_nothing_else(self) -> None:
        """WHAT THE OWNER SAW, stated as an executable number.

        Forty placements in this scene carry a leader whose MOBS row has BOTH
        a rank and a combat AI -- the whole hostility predicate -- and every
        one of them is refused because that row's ``s_OUTFIT`` is a ``;``
        list.  Twelve placements pass both halves, and twelve is exactly what
        the server's own census printed on the owner's machine.

        This test exists because the instruction this gap generated ("17 rows
        vs a 12-mob roster, regenerate from the real roster") describes a
        DIFFERENT defect: the 17-vs-12 difference is five Orc Chief rows that
        only the setnum reading produces, and deleting them would not make
        one Desert Eagle attackable.  Whoever acts on either number should
        have both in front of them, re-derived rather than quoted.
        """
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        # Counted here, from the same placements file the generator reads,
        # rather than through a private helper that may be renamed.
        counts = {}
        for item in sources.placements:
            raw = (item.get("name") or "").split()
            if not raw or not raw[0].startswith("MOBSET_"):
                continue
            counts[int(raw[0].split("_")[1])] = counts.get(
                int(raw[0].split("_")[1]), 0) + 1

        refused_placements = 0
        for set_number, (expected_n, expected_id, expected_name) in sorted(
                self.OUTFIT_AMBIGUOUS_HOSTILE_SETS.items()):
            with self.subTest(mob_set=set_number):
                resolved = sources.resolve(
                    set_number, tool.IDENTITY_RULE_CLINE)
                self.assertEqual(resolved, expected_id)
                mob = sources.mobs.get(str(expected_id))
                self.assertIsNotNone(mob)
                # Passes the hostility predicate outright.
                self.assertTrue(tool._nonzero(mob, "n_RANK"))
                self.assertTrue(tool._nonzero(mob, "n_AI_COMBAT"))
                # And is refused by the OTHER half, alone.
                self.assertIn(";", (mob.get("s_OUTFIT") or "").strip())
                self.assertEqual(counts.get(set_number), expected_n)
                refused_placements += expected_n
        self.assertEqual(
            refused_placements, 40,
            "the outfit-ambiguity gap in this scene changed size; re-read it "
            "before changing any number that quotes it",
        )
        # ROUND najn72: THE GAP IS CLOSED, and this is where that is
        # measured rather than announced.  The 40 placements counted above
        # are exactly what the outfit half was refusing; with the owner's
        # rule in force the same sources ship 52 rows -- 12 under the old
        # reading (the number R322B's console printed) plus those 40.  The
        # owner's screen question ("why is only the fish attackable") has a
        # data answer AND a fix in the same file now.
        old_reading = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_UNAMBIGUOUS)
        roster = tool.hostile_roster(
            sources, rule=tool.IDENTITY_RULE_CLINE,
            outfit_rule=tool.OUTFIT_RULE_ANY)
        self.assertEqual(len(roster), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len(roster) - len(old_reading), refused_placements,
            "the rows the owner's outfit rule readmits are no longer the "
            "rows the outfit half was refusing -- re-read both before "
            "changing either number")


if __name__ == "__main__":
    unittest.main()
