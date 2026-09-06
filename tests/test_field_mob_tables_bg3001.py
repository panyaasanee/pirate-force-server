"""LANE-B round mf71tm: scene 126's roster, and the reading that produced it.

WHY THIS FILE IS NOT A COPY OF ITS ELEVEN SIBLINGS.  Every other
``test_field_mob_tables_bg*.py`` pins a roster mined under the TOWN hostility
reading (``n_RANK != 0 AND n_AI_COMBAT != 0``).  Bg3001 is the first scene
this lane has shipped under the OCEAN reading (``n_RANK != 0`` alone), so the
thing most worth pinning here is not the two rows - it is the measurement that
says the two readings are not interchangeable at sea, re-derived from the
committed tables on every run rather than quoted from a round note:

    the town reading selects ZERO placements in this scene, and
    the ocean reading's rows and the combat-AI rows do not overlap at all.

If a future round "fixes" the generator by making ocean a superset of town, or
by folding the two readings back into one, the first two tests below fail
rather than the roster quietly growing ships and weather markers.

WHAT THIS FILE DOES NOT CLAIM.  That the ocean reading is RIGHT - that is
LANE-B's reading of the client's own tables put to COO in
``notes_to_chief/20260906_1643_LANE-B-ASK-COO-*`` and not answered when this
file was written.  That these two rows can be KILLED - they are in no
``mob_death.WIDENING_RULINGS`` set, which the last test here pins on purpose.
That anybody has SEEN them: scene 126's door is LANE-A's and is shut.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import field_mob_tables_bg3001 as table  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402

GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"
TOOL = ROOT / "tools" / "pf_mine_scene_mob_roster.py"

EXPECTED_SCENE = "Bg3001"
EXPECTED_SCENE_N_ID = 126


def _load_tool():
    spec = importlib.util.spec_from_file_location("_mine_tool", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg3001HostilityReadingTests(unittest.TestCase):
    """The two readings, measured on this scene, not quoted."""

    def test_the_town_reading_selects_nothing_in_this_scene(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        town = tool.hostile_roster(
            sources, tool.IDENTITY_RULE_CLINE, tool.HOSTILITY_RULE_TOWN)
        self.assertEqual(
            town, [],
            "the town reading now selects rows in an ocean panel: either the "
            "tables changed or the reading did - re-read the scene before "
            "shipping anything under either",
        )

    def test_the_ocean_reading_and_the_combat_ai_rows_do_not_overlap(
            self) -> None:
        """Rank rows are creatures; combat-AI rows are hulls and weather."""
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        ocean = {row["placement_index"] for row in tool.hostile_roster(
            sources, tool.IDENTITY_RULE_CLINE, tool.HOSTILITY_RULE_OCEAN)}
        combat = set()
        for item in tool.unambiguous_placements(
                sources, tool.IDENTITY_RULE_CLINE):
            if tool._nonzero(item[6], "n_AI_COMBAT"):
                combat.add(item[0])
        self.assertTrue(ocean, "this scene ships no ocean-reading rows at all")
        self.assertTrue(combat, "this scene has no combat-AI rows at all")
        self.assertEqual(
            ocean & combat, set(),
            "a placement is now BOTH a rank row and a combat-AI row in an "
            "ocean panel; the two families separated cleanly when this "
            "roster was mined, and the roster's justification rests on that",
        )

    def test_regenerating_reproduces_the_committed_module(self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        rule = tool.IDENTITY_RULE_CLINE
        hostility = tool.HOSTILITY_RULE_OCEAN
        regenerated = tool.render_module(
            EXPECTED_SCENE,
            tool.hostile_roster(sources, rule, hostility),
            sources.digests(), tool.predicate_census(sources, rule),
            rule=rule, hostility=hostility, cline_type=sources.cline_type,
            town=tool.town_target_roster(sources, rule),
            withdrawn=tool.withdrawn_under_rule(sources, rule),
            controls=tool.check_crosswalk_controls(sources),
            rank_zero_combat=[
                tool._roster_row(sources, item)
                for item in tool.unambiguous_placements(sources, rule)
                if tool._nonzero(item[6], "n_AI_COMBAT")
                and not tool._nonzero(item[6], "n_RANK")
            ],
            unresolved=tool.unresolved_placements(sources, rule),
        )
        committed = (
            ROOT / "src/pirateforce_foundation/field_mob_tables_bg3001.py"
        ).read_text(encoding="ascii")
        self.assertEqual(
            regenerated, committed,
            "field_mob_tables_bg3001.py is stale - regenerate with "
            "tools/pf_mine_scene_mob_roster.py --gamedata <bridge>/gamedata "
            "--scene Bg3001 --hostility-rule ocean --out <this file>",
        )


class Bg3001RosterTests(unittest.TestCase):
    """What the roster is, read through the loader every scene shares."""

    def test_the_module_records_which_reading_shipped_it(self) -> None:
        self.assertEqual(table.SCENE, EXPECTED_SCENE)
        self.assertEqual(table.IDENTITY_RULE, "cline")
        self.assertEqual(table.HOSTILITY_RULE, "rank")

    def test_the_loader_serves_two_level_60_creatures(self) -> None:
        roster = field_mobs.load_roster(scene=field_mobs.BG3001_SCENE)
        self.assertEqual(len(roster), 2)
        self.assertEqual(
            [mob.placement_index for mob in roster], [29, 37])
        self.assertEqual(
            sorted({mob.template_id for mob in roster}), [8041, 8180])
        for mob in roster:
            with self.subTest(placement=mob.placement_index):
                self.assertEqual(mob.scene, EXPECTED_SCENE)
                self.assertEqual(mob.level, 60)
                # HP is the derived column and it is derived the same way for
                # every scene: STANDARD_MOB[n_LEVEL_MIN].n_HPMAX, sent as
                # current == max.  Both rows are level 60, so both are the
                # level-60 row's HP; a hand-composed number would not be.
                self.assertEqual(mob.max_hp, 43275)
                self.assertGreater(mob.rank, 0)
                self.assertEqual(mob.ai_combat, 0)

    def test_the_shipped_rows_are_creature_models_not_hulls(self) -> None:
        """The visual preset is what separates a monster from the scenery."""
        roster = field_mobs.load_roster(scene=field_mobs.BG3001_SCENE)
        for mob in roster:
            with self.subTest(placement=mob.placement_index):
                self.assertTrue(
                    mob.visual_preset.startswith("M0"),
                    "%r is not a creature model; SP_* is a hull and "
                    "INVISIBLE is a weather marker, and neither belongs in a "
                    "hostile roster" % (mob.visual_preset,),
                )

    def test_this_scene_is_registered_exactly_once(self) -> None:
        self.assertEqual(field_mobs.BG3001_SCENE, EXPECTED_SCENE)
        self.assertIn(EXPECTED_SCENE, field_mobs._SCENE_TABLE_MODULES)
        self.assertIs(
            field_mobs._SCENE_TABLE_MODULES[EXPECTED_SCENE], table)


class Bg3001IsNotKillableYetTests(unittest.TestCase):
    """The registration ships a roster and NOT a permission to kill it.

    This is the test that would catch the mistake worth catching: a later
    round adding these templates to a ruling set that was signed for a
    different scene, or this round having quietly done so.  When COO answers
    the letter, this test is the one that changes, and it has to be changed
    deliberately.
    """

    def test_neither_template_is_inside_any_widening_ruling(self) -> None:
        shipped = {row[1] for row in table.HOSTILE_PLACEMENTS}
        self.assertEqual(shipped, {8041, 8180})
        for key, templates in mob_death.WIDENING_RULINGS.items():
            with self.subTest(ruling=key[:60]):
                self.assertEqual(
                    shipped & set(templates), set(),
                    "a ruling signed before scene 126 had a roster now "
                    "covers one of its templates",
                )

    def test_no_ruling_names_this_scene(self) -> None:
        for key, scene in mob_death.WIDENING_RULING_SCENES.items():
            with self.subTest(ruling=key[:60]):
                self.assertNotEqual(scene, EXPECTED_SCENE)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
