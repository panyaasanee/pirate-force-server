"""LANE-B: Bg0015's hostile roster is mined and PREPARED, not wired in.

COO-DECISION 2026-08-26 12:46 (pf_bridge, notes_to_chief) confirmed ``Bg0015``
(Hell Volcanic Island) as the real ``M3`` monster map and gave lane B one
instruction: prepare ``field_mob_tables`` regenerated pointed at Bg0015, but do
NOT wire it in for real until lane A confirms its second travel gate and the
geometry/reachability check passes.  bg0001 (Port Royal) stays the live/default
roster this round; ``field_mob_tables_bg0015.py`` sits beside it, generated the
same way, imported by nothing.

The three tests that matter most, of the ten in this file, are these:

``test_nothing_under_src_imports_the_bg0015_module`` is the one that matters
most: it is the guard that this round did not accidentally wire BUILD-004's
prep work into a live path ahead of lane A's gate.  A grep for the literal
module name would be fooled by a comment; this walks the AST of every module
under ``src/pirateforce_foundation/`` and checks actual import statements.

``test_regenerating_reproduces_the_committed_module_byte_for_byte`` is the
same discipline ``field_mob_tables.py`` and ``field_drop_tables.py`` are
already held to: a GENERATED module is only trustworthy if the generator that
wrote it can reproduce it right now, from the same committed game data.

``test_field_mob_tables_bg0001_is_untouched_by_this_round`` pins the fact that
the live/default roster (bg0001, Port Royal) was not touched while preparing
Bg0015: its sha256 must equal the value measured immediately before this
round's file was added.
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
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0015.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

# Measured 2026-08-26, immediately before field_mob_tables_bg0015.py was added
# to this repository, and never to be updated to make a future edit of
# field_mob_tables.py pass silently -- if bg0001's roster changes for a real
# reason this constant moves in that same commit and says why.
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
BG0001_UNTOUCHED_SHA256 = (
    "574fdca1391eb0aa4bc4a5a2b46b50c090839a86baf94426573312afff2866a5"
)
# ROUND 8ftmbx: ~~10570~~ -> 9704.  bg0001's own module shrank when
# COO-DECISION 2026-08-29T00:41+07:00 withdrew its nine set-number rows;
# this constant exists to prove THIS round did not touch that file, so it
# tracks that file's size and is re-pinned whenever bg0001's own lane
# changes it on purpose.
BG0001_UNTOUCHED_SIZE = 9708

EXPECTED_SCENE = "Bg0015"
# ROUND ua236k: this scene is now mined under ``cline``, by
# COO-DECISION 20260829_0345 ("cline เป็นกฎอ่านตัวตนของทุกฉาก ตั้งแต่วันนี้").
# The previous numbers are kept, not deleted, so the size of the change is
# auditable from either side: ~~17 hostiles, 4 templates, 76 unambiguous~~
# under the set-number reading.
#
# WHAT MOVED AND WHY IT IS NOT A REGRESSION.  CLINE type 14 -- this scene's
# own type -- agrees with the set-number reading on ZERO of its 51 rows
# (pinned in tests/test_scene_identity_rule.py), so every identity in this
# table changed.  The set-number reading had Hell Volcanic Island populated
# by Port Royal's level-25 Fighting Fish soldiers and Tornado Eagles; the
# crosswalk gives level-105 Glaucoma, Lava shakers and Horror butcher Lasa.
# That is the GT-078 failure mode -- a whole map wearing another map's names
# -- caught before anything was wired to it rather than after.
EXPECTED_HOSTILE_COUNT = 12
EXPECTED_TEMPLATE_COUNT = 7
EXPECTED_UNAMBIGUOUS = 36
# NOT equal to EXPECTED_HOSTILE_COUNT any more, and the inequality is the
# finding rather than a rounding error: placement 87 resolves to MOBS 924
# (Carlos, level 115), which has rank and combat AI but n_DROP_NORMAL 0.  The
# old test asserted one constant for both and would have hidden this.
EXPECTED_DROPS_NORMAL = 11


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_generated_module():
    spec = importlib.util.spec_from_file_location(
        "field_mob_tables_bg0015", MODULE_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0015PrepShapeTests(unittest.TestCase):
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
        self.assertEqual(
            module.PREDICATE_CENSUS["unambiguous"], EXPECTED_UNAMBIGUOUS
        )
        self.assertEqual(
            module.PREDICATE_CENSUS["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT
        )

    def test_nothing_under_src_imports_the_bg0015_module(self) -> None:
        """This round's prep must stay exactly as inert as bg0001's own pin.

        Walks the AST of every .py file under src/ rather than grepping text,
        so a docstring or comment that merely mentions the module name cannot
        be mistaken for an import.  Both ``import`` forms are checked, and
        ``ImportFrom`` checks its ALIASES as well as its ``module`` -- the
        exact style this codebase actually uses is
        ``from pirateforce_foundation import field_mob_tables, field_mobs``
        (see tests/test_field_mobs.py), where the target name lives in
        ``node.names``, not ``node.module``; the first draft of this guard
        checked only ``node.module`` and would have missed exactly that
        style of wiring (self-caught adversarial pass on this same test).

        A second, string-literal-based sweep runs alongside the AST one, as
        a catch for a dynamic ``importlib.import_module("...")`` wiring that
        an AST Import/ImportFrom check cannot see at all.  Both must scan a
        non-trivial number of files: an empty ``rglob`` would make either
        check vacuously green, which is exactly the "green because it never
        got there" shape this project has already shipped once.
        """
        py_files = sorted(SRC.rglob("*.py"))
        # A hard floor well under the real count (66 measured 2026-08-26),
        # so a path typo that returns zero or a near-empty tree is a loud
        # failure here rather than a silent, vacuous pass below.
        self.assertGreater(
            len(py_files), 30,
            "src/**/*.py scan returned suspiciously few files (%d) -- "
            "the import guard below would be vacuous" % len(py_files),
        )

        offenders = []
        for path in py_files:
            if path == MODULE_PATH:
                continue
            text = path.read_text(encoding="utf-8")

            # Layer 1: AST-based, catches every real import statement.
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError:
                self.fail("could not parse %s" % path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if "field_mob_tables_bg0015" in alias.name:
                            offenders.append(str(path))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and "field_mob_tables_bg0015" in node.module:
                        offenders.append(str(path))
                    for alias in node.names:
                        if "field_mob_tables_bg0015" in alias.name:
                            offenders.append(str(path))

            # Layer 2: literal-string sweep, catches importlib.import_module
            # and any other reference an AST Import/ImportFrom check cannot
            # see (this is deliberately broader than "an import" -- ANY
            # mention outside this test file and the module itself is
            # suspicious enough to fail loudly and be looked at by a human,
            # not silently ignored).
            if "field_mob_tables_bg0015" in text:
                offenders.append(str(path))

        offenders = sorted(set(offenders))
        self.assertEqual(
            offenders, [],
            "field_mob_tables_bg0015 must stay unwired until lane A's second "
            "gate + geometry check passes (COO-DECISION 2026-08-26 12:46); "
            "found a reference in: %s" % offenders,
        )

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


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0015RegenerateAndDiffTest(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_regenerating_reproduces_the_committed_module_byte_for_byte(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        rule = tool.IDENTITY_RULE_CLINE
        controls = tool.check_crosswalk_controls(sources)
        census = tool.predicate_census(sources, rule)
        roster = tool.hostile_roster(sources, rule)
        # ~~Round szdkgs: the generator grew an identity rule and this scene
        # is still mined under the legacy set-number one, on purpose.~~
        # ROUND ua236k: re-mined through the crosswalk, which is what that
        # comment said a future round would have to come here and say.  The
        # rule is still named explicitly rather than inherited from the
        # tool's default, for the same reason: a change of default must not
        # silently change what this scene ships.
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census,
            rule=rule, cline_type=sources.cline_type,
            controls=controls,
            withdrawn=tool.withdrawn_under_rule(sources, rule),
            unresolved=tool.unresolved_placements(sources, rule),
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(sources, rule)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
        )
        committed = MODULE_PATH.read_text(encoding="ascii")
        self.assertEqual(
            regenerated, committed,
            "src/pirateforce_foundation/field_mob_tables_bg0015.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0015 --out <this file>",
        )

    def test_the_predicate_census_matches_the_recorded_finding(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        census = tool.predicate_census(sources, tool.IDENTITY_RULE_CLINE)
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            census["drops_normal"], EXPECTED_DROPS_NORMAL,
            "one hostile here has no normal drop table (MOBS 924, Carlos).  "
            "If this equals the hostile count again, either the roster or "
            "the drop tables moved -- find out which before re-pinning."
        )

    def test_hostile_roster_count_is_twelve_from_live_gamedata(self) -> None:
        """~~seventeen~~ twelve, under the crosswalk (round ua236k).

        Renamed rather than left saying "seventeen" with a 12 inside it; the
        pin in docs/PYTEST_SKIP_PINS.json moves in this same commit.
        """
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        roster = tool.hostile_roster(sources, tool.IDENTITY_RULE_CLINE)
        self.assertEqual(len(roster), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row["template_id"] for row in roster}), EXPECTED_TEMPLATE_COUNT
        )

    def test_this_scene_agrees_with_the_legacy_rule_on_nothing(self) -> None:
        """The reason the whole table changed, as a number rather than prose.

        If this ever returns a non-zero agreement, the two readings have
        started to overlap for this scene and the "every identity changed"
        sentence in this file's constants block is no longer true.
        """
        sys.path.insert(0, str(SRC))
        from pirateforce_foundation import scene_identity_rule as sir

        cline_type = _load_generated_module().SCENE_CLINE_TYPE
        self.assertEqual(cline_type, sir.SCENE_CLINE_TYPE[EXPECTED_SCENE])
        agreeing, total = sir.agreement(cline_type)
        self.assertEqual((agreeing, total), (0, 51))


if __name__ == "__main__":
    unittest.main()
