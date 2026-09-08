"""LANE-B round vavm4h: the generator and the server are bound WITHOUT the
bridge clone standing beside this checkout.

WHY THIS FILE EXISTS -- pf-adversary D6, round db4o73, quoted:

    "the generator and the server cannot diverge" is true only on a machine
    with the bridge clone beside it -- the regenerate test is
    ``skip_unless_present``.  Adversary measured: reverting ``visual_preset``
    back to the raw cell is COMPLETELY GREEN when ``../pf_bridge/gamedata``
    is absent.

That finding is about coverage, not about a wrong byte: the byte-for-byte
regenerate test is a real check and it stays.  What it is not is a check that
RUNS.  On the cloud clones every lane works from, and in the gate, there is
no ``gamedata`` beside the checkout, so the one test that bound the wire rule
to the shipped column skipped, and the claim in the module docstring stood on
a test nobody in that environment executed.

WHAT THIS FILE ADDS, and why each half catches a mutant the other does not:

* :class:`TheRowBuilderShipsABasenameTests` runs the generator's OWN row
  builder on a synthetic placement.  No table, no ``gamedata``, no bridge
  clone -- a hand-made ``mob`` dict and a stub source.  Reverting
  ``visual_preset`` to the raw cell in ``tools/pf_mine_scene_mob_roster.py``
  turns this red on any machine.  That is the exact mutant D6 measured
  walking free.
* :class:`TheShippedColumnAgreesWithTheRuleTests` re-derives the shipped
  column from the raw cells the generated modules carry, under the SERVER's
  function.  It catches the other half of the divergence: a generator that
  was changed and a module that was never regenerated (or the reverse).

NON-CLAIMS.  Neither half re-derives the table from ``gamedata``: they cannot,
and they do not pretend to.  A row that is wrong in the source table is wrong
here too and both halves will agree with it.  What is checked is that the two
ends of ONE rule say the same thing -- the failure D6 showed could happen in
silence.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_avatar_basename  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"

#: The index of the shipped avatar column inside a generated placement row.
#: Named rather than spelled ``[5]`` at four call sites, because a column
#: reorder that this file failed to notice is exactly the drift it is here
#: to catch.
VISUAL_PRESET_COLUMN = 5


def _load_tool():
    spec = importlib.util.spec_from_file_location("pf_miner_vavm4h", TOOL_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _StubSources:
    """The two lookups ``_roster_row`` makes, and nothing else.

    Deliberately NOT a ``Sources``: building a real one needs the gamedata
    tables this file exists to do without.  If ``_roster_row`` ever grows a
    third call into its sources, this stub raises ``AttributeError`` and the
    test says so out loud rather than skipping.
    """

    def __init__(self, name: str = "Test monster", hp: int = 100) -> None:
        self._name = name
        self._hp = hp

    def display_name(self, template_id: int) -> str:
        return self._name

    def hp_for_level(self, level: int, where: str) -> int:
        return self._hp


def _mob_row() -> dict:
    """A MOBS row with every numeric column ``_roster_row`` reads."""
    return {
        "n_LEVEL_MIN": "16",
        "n_LEVEL_MAX": "16",
        "n_RANK": "1",
        "n_AI_WANDER": "16",
        "n_AI_COMBAT": "110",
        "n_SPEED_WALK": "100",
        "n_SPEED_RUN": "1054",
        "n_DROPS_NORMAL": "2701001",
        "n_DROPS_EQUIPMENT": "5400001",
        "n_DROPS_SPECIALLY": "0",
    }


class TheRowBuilderShipsABasenameTests(unittest.TestCase):
    """D6's mutant, caught with nothing beside the checkout."""

    def setUp(self) -> None:
        self.tool = _load_tool()

    def _row(self, cell: str) -> dict:
        item = (31, 28, 1.0, 2.0, 3.0, cell, _mob_row(), 7)
        return self.tool._roster_row(_StubSources(), item)

    def test_a_list_cell_is_shipped_as_its_first_token(self) -> None:
        row = self._row("M001_000_000_N;M001_000_000_SP1")
        self.assertEqual(row["visual_preset"], "M001_000_000_N")

    def test_the_raw_cell_is_kept_in_its_own_column(self) -> None:
        row = self._row("M001_000_000_N;M001_000_000_SP1")
        self.assertEqual(
            row["outfit_cell"], "M001_000_000_N;M001_000_000_SP1")
        self.assertNotEqual(row["visual_preset"], row["outfit_cell"])

    def test_the_shipped_column_never_carries_a_separator(self) -> None:
        for cell in ("M001_000_000_N;M001_000_000_SP1",
                     "M005_000_000_SP1",
                     "M002_000_000_N;M002_000_000_SP1;M002_000_000_SP2"):
            with self.subTest(cell=cell):
                row = self._row(cell)
                self.assertFalse(
                    mob_avatar_basename.has_separator(row["visual_preset"]),
                    "the generator would put a list cell on the wire",
                )

    def test_the_builder_uses_the_servers_own_function(self) -> None:
        # Not "the same string": the same answer on an input whose reading is
        # a CHOICE of this lane's (the wide separator set), so a generator
        # that quietly kept its own narrow copy of the rule differs here.
        row = self._row("A B;C")
        self.assertEqual(
            row["visual_preset"],
            mob_avatar_basename.avatar_basename("A B;C"),
        )

    def test_a_cell_with_no_first_token_is_refused_not_shipped_empty(
            self) -> None:
        # pf-adversary D10: the generator used to write the empty string into
        # a module whose own boot path refuses an empty preset.
        with self.assertRaises(self.tool.MineError) as caught:
            self._row(";M001_000_000_N")
        self.assertIn("visual_preset", str(caught.exception))


class TheShippedColumnAgreesWithTheRuleTests(unittest.TestCase):
    """Every raw cell a module carries still resolves to what it ships."""

    def test_every_recorded_cell_resolves_to_the_shipped_basename(
            self) -> None:
        checked = 0
        for scene in field_mobs.live_scenes():
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            cells = getattr(module, "OUTFIT_CELL_FOR_PLACEMENT", {})
            if not cells:
                continue
            shipped = {
                row[0]: row[VISUAL_PRESET_COLUMN]
                for row in module.SHIPPED_PLACEMENTS
            }
            for index, cell in cells.items():
                with self.subTest(scene=scene, placement=index):
                    self.assertIn(index, shipped)
                    self.assertEqual(
                        mob_avatar_basename.avatar_basename(cell),
                        shipped[index],
                        "the module's raw cell and its shipped basename "
                        "disagree under the server's own rule: the "
                        "generator changed and this table was never "
                        "regenerated, or the reverse",
                    )
                    checked += 1
        self.assertGreater(
            checked, 0,
            "no scene module carries a raw cell any more; this test has "
            "stopped measuring anything and the reason must be written down",
        )

    def test_a_module_that_records_no_cell_ships_no_list(self) -> None:
        # pf-adversary D11: the ABSENCE of OUTFIT_CELL_FOR_PLACEMENT had two
        # meanings (mined under ``any`` with no cell differing, vs mined
        # under ``unambiguous`` so the list rows were dropped at source), and
        # the only thing separating them was the absence of ANOTHER symbol.
        # An emptiness is not a disambiguator, so the meaning both readings
        # share is turned into a check instead: whatever the reason a module
        # carries no cell column, nothing it ships may be a list.  A module
        # that grows one fails here with its own name.
        for scene in field_mobs.live_scenes():
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            if getattr(module, "OUTFIT_CELL_FOR_PLACEMENT", {}):
                continue
            for row in module.SHIPPED_PLACEMENTS:
                with self.subTest(scene=scene, placement=row[0]):
                    self.assertFalse(
                        mob_avatar_basename.has_separator(
                            row[VISUAL_PRESET_COLUMN]),
                        "a module with no recorded cell shipped a list cell",
                    )

    def test_a_module_mined_under_any_says_so_and_carries_its_cells(
            self) -> None:
        # The other half of D11, stated as the invariant the two meanings
        # actually differ by: ``OUTFIT_RULE == 'any'`` is the ONLY way a list
        # cell can reach a module at all, so a module carrying cells must
        # declare that rule.  The reverse is not asserted -- a scene mined
        # under ``any`` whose every cell happens to be its own basename is a
        # legitimate module with no cells to record.
        for scene in field_mobs.live_scenes():
            module = field_mobs._SCENE_TABLE_MODULES[scene]
            if not getattr(module, "OUTFIT_CELL_FOR_PLACEMENT", {}):
                continue
            with self.subTest(scene=scene):
                self.assertEqual(
                    getattr(module, "OUTFIT_RULE", None), "any",
                    "a module carries raw cells but does not declare the "
                    "rule that is the only way they could have been mined",
                )


class TheToolStillPrintsItsUsageTests(unittest.TestCase):
    """pf-adversary D5: ``--help`` must not need the wire rule file."""

    def test_help_does_not_load_the_wire_rule(self) -> None:
        tool = _load_tool()
        # The rule is loaded on first use, not at import.  Importing the tool
        # is what ``--help`` does before it parses; if that alone had already
        # loaded the rule, a checkout without the rule file could not print
        # usage -- which is the state D5 measured.
        self.assertIsNone(
            tool._AVATAR_RULE,
            "the wire rule was loaded at import time again; --help on a "
            "checkout without src/ beside it dies with FileNotFoundError",
        )

    def test_a_missing_rule_file_says_what_is_missing(self) -> None:
        tool = _load_tool()
        tool._AVATAR_RULE_PATH = ROOT / "tools" / "no_such_wire_rule.py"
        with self.assertRaises(tool.WireRuleUnavailableError) as caught:
            tool._load_avatar_rule()
        message = str(caught.exception)
        self.assertIn("no_such_wire_rule.py", message)
        self.assertIn("wire rule", message)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
