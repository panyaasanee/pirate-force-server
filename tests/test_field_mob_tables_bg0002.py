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
BG0001_UNTOUCHED_SHA256 = (
    "c25f0d15e93db6d6700a22f6ebb142885d3c000d592caa47d745a45129115a61"
)
BG0001_UNTOUCHED_SIZE = 9636

EXPECTED_SCENE = "Bg0002"
EXPECTED_HOSTILE_COUNT = 17
EXPECTED_TEMPLATE_COUNT = 4
EXPECTED_TEMPLATES = {31, 34, 35, 103}
EXPECTED_UNAMBIGUOUS = 49


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

    def test_template_27_mountain_deer_is_not_in_this_roster(self) -> None:
        # The decision letter's own block is templates 1-41; 1-26 are
        # single-instance NPCs and 27-35 are the monster block. This pins
        # the concrete reason template 27 (Mountain Deer, the DIAG-001
        # body) is absent from THIS table specifically, so a future reader
        # does not mistake the absence for an oversight: CONSTDATA_TH__
        # MOBS.tsv row 27's s_OUTFIT is a ";"-joined two-variant list, which
        # fails the mining tool's own single-unambiguous-basename rule --
        # see mob_diag_multi_object.py for where template 27's row actually
        # lives (hand-mined, not generated).
        module = _load_generated_module()
        templates = {row[1] for row in module.HOSTILE_PLACEMENTS}
        self.assertNotIn(27, templates)
        for excluded in (27, 28, 29, 30, 32, 33):
            self.assertNotIn(excluded, templates)

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
        test_nothing_under_src_imports_the_bg0015_module uses, but asserts
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
        tool.check_controls(sources)
        census = tool.predicate_census(sources)
        roster = tool.hostile_roster(sources)
        # Round szdkgs: the generator grew an identity rule and this scene is
        # still mined under the legacy set-number one, on purpose -- see
        # LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION in bg0001's module and
        # this lane's round note.  The call below names that rule explicitly
        # rather than inheriting the tool's new default, so a future round
        # that re-mines this scene through the crosswalk has to come here and
        # say so.
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census,
            rule=tool.IDENTITY_RULE_SETNUM, cline_type=sources.cline_type,
            controls={"legacy_setnum_controls": "re-derived"},
            withdrawn=tool.withdrawn_under_rule(
                sources, tool.IDENTITY_RULE_SETNUM),
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(
                    sources, tool.IDENTITY_RULE_SETNUM)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
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
        census = tool.predicate_census(sources)
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["drops_normal"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)

    def test_hostile_roster_count_is_seventeen_from_live_gamedata(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        tool.check_controls(sources)
        roster = tool.hostile_roster(sources)
        self.assertEqual(len(roster), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row["template_id"] for row in roster}), EXPECTED_TEMPLATE_COUNT
        )
        self.assertEqual(
            {row["template_id"] for row in roster}, EXPECTED_TEMPLATES
        )

    def test_template_27_fails_only_the_outfit_ambiguity_half_of_selection(
            self) -> None:
        # Confirms, against LIVE gamedata rather than a hand-typed claim,
        # that template 27 (Mountain Deer) really does pass the
        # RANK+AI_COMBAT hostility predicate and really is excluded solely
        # by the outfit-unambiguous half of the selection rule -- the exact
        # distinction mob_diag_multi_object.py's own provenance comment and
        # mob_death.py's WIDENING_RULINGS comment both depend on.
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        mob27 = sources.mobs.get("27")
        self.assertIsNotNone(mob27)
        self.assertTrue(tool._nonzero(mob27, "n_RANK"))
        self.assertTrue(tool._nonzero(mob27, "n_AI_COMBAT"))
        outfit = (mob27.get("s_OUTFIT") or "").strip()
        self.assertIn(";", outfit)
        roster = tool.hostile_roster(sources)
        self.assertNotIn(27, {row["template_id"] for row in roster})


if __name__ == "__main__":
    unittest.main()
