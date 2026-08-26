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
BG0001_UNTOUCHED_SHA256 = (
    "158704080cc23180d0829d81848119327f335461519a848a1cab599aefaabb9e"
)
BG0001_UNTOUCHED_SIZE = 3978

EXPECTED_SCENE = "Bg0015"
EXPECTED_HOSTILE_COUNT = 17
EXPECTED_TEMPLATE_COUNT = 4
EXPECTED_UNAMBIGUOUS = 76


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
        tool.check_controls(sources)
        census = tool.predicate_census(sources)
        roster = tool.hostile_roster(sources)
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census
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


if __name__ == "__main__":
    unittest.main()
