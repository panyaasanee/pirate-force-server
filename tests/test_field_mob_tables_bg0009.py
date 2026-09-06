"""LANE-B: scene 9 (Bg0009) is a REGISTERED combat scene.

COO-DECISION widen-death-scope-bg0006-bg0007-bg0009-bg0011-four-scenes
2026-09-06T11:50+07:00 (notes_to_chief/20260906_1150_COO-DECISION-b1122-
widen-death-scope-bg0006-bg0007-bg0009-bg0011-four-scenes-ratified-repoint-
four-strings-to-1150-coo-greps-ruling-keys-every-exec-round-LANE-B.md), the
ratifying letter this module's ``RULING_NAME`` now cites.  Round 4tnhzw
(this lane) first registered this scene citing notes_to_chief/20260906_0748_
COO-DECISION-b0659-send-four-clean-scenes-now-bg0010-unresolved-is-a-static-
ticket-body-to-chief-bg0009-zero-drop-m-avatars-are-ordinary-mobs-LANE-B.md,
which only ASKED for a ruling (its own item 1 says "send a request"); COO
1150 ratifies the same scene/templates (not reversed) and repoints the
citation to itself.  That letter answers LANE-B-ASK-COO 2026-09-06T06:59+07:00
(notes_to_chief/20260906_0659_LANE-B-ASK-COO-five-scene-recon-bg0010-mining-
crash-bg0009-two-ambiguous-rows.md).  ``field_mob_tables_bg0009`` is
registered in
``field_mobs._SCENE_TABLE_MODULES`` in the same commit that adds it.

THE TWO ROWS THIS FILE NAMES BY HAND.  Placements 56 (MOBS 546, "Black braid
Edward") and 57 (MOBS 549, "Bermuda Banshee") mine zero in every one of
``n_DROPS_NORMAL``/``n_DROPS_EQUIPMENT``/``n_DROPS_SPECIALLY`` -- the same
HALF of the Carlos/Nina withhold condition Bg0008's Nina carries.  The other
half does NOT hold here: both rows' ``s_OUTFIT`` starts ``M0`` (an ordinary
monster body), not ``P_`` (a player model), and the 0748 letter's item 2 is
explicit that BOTH halves are required before a row is withheld.  So this
lane ships both normally and flags them ``DROPS_UNMINED`` in
``field_mobs.DROPS_UNMINED_PLACEMENTS`` instead -- documentary only, and
NOT a filter: ``test_the_drops_unmined_rows_still_ship`` is the check that
the flag never quietly becomes a second withhold list.
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

from pirateforce_foundation import field_mob_tables_bg0009  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0009.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "Bg0009"
EXPECTED_SCENE_ID = 9
EXPECTED_HOSTILE_COUNT = 5
EXPECTED_TEMPLATE_COUNT = 5
EXPECTED_UNAMBIGUOUS = 27
EXPECTED_CENSUS_RANK = 5
EXPECTED_CENSUS_AI_COMBAT = 5
EXPECTED_CENSUS_RANK_AND_AI_COMBAT = 5
EXPECTED_CENSUS_DROPS_NORMAL = 3
EXPECTED_DROPS_UNMINED_PLACEMENTS = (56, 57)

RULING_NAME = (
    "COO-DECISION widen-death-scope-bg0009-five-templates "
    "2026-09-06T11:50+07:00"
)

# The whole SHIPPED roster, spelled out rather than counted.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_SHIPPED_ROWS = (
    (42, 314, 0x202B, "Captain Golem Rabia"),
    (49, 317, 0x2032, "Destroy Magic Flower"),
    (54, 320, 0x2037, "Skeleton Commander Corella"),
    (56, 546, 0x2039, "Black braid Edward"),
    (57, 549, 0x203A, "Bermuda Banshee"),
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0009ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0009
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 9)
        self.assertEqual(len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in module.HOSTILE_PLACEMENTS}),
            EXPECTED_TEMPLATE_COUNT,
        )
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank"], EXPECTED_CENSUS_RANK)
        self.assertEqual(census["ai_combat"], EXPECTED_CENSUS_AI_COMBAT)
        self.assertEqual(
            census["rank_and_ai_combat"], EXPECTED_CENSUS_RANK_AND_AI_COMBAT)
        self.assertEqual(census["drops_normal"], EXPECTED_CENSUS_DROPS_NORMAL)
        self.assertEqual(module.TOWN_TARGET_PLACEMENTS, [])
        self.assertEqual(module.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION, [])

    def test_the_scene_is_registered_and_reachable_through_its_scene_id(
            self) -> None:
        self.assertEqual(
            field_mobs.scene_for_scene_id(EXPECTED_SCENE_ID), EXPECTED_SCENE)
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            tuple(
                (mob.placement_index, mob.template_id, mob.actor_identity,
                 mob.display_name)
                for mob in rows
            ),
            EXPECTED_SHIPPED_ROWS,
        )
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({mob.template_id for mob in rows}), EXPECTED_TEMPLATE_COUNT)
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_drops_unmined_rows_still_ship(self) -> None:
        """546/549 have no drop table yet, and are NOT withheld for it.

        COO-DECISION 2026-09-06T07:48+07:00 item 2: the withhold test needs
        BOTH a player-model avatar AND zero drops; these two rows carry only
        the second half (avatar starts ``M0``, an ordinary monster body), so
        the letter ships them normally and this lane records the missing
        drop table as a flag, not a filter.
        """
        self.assertEqual(
            field_mobs.DROPS_UNMINED_PLACEMENTS.get(EXPECTED_SCENE),
            EXPECTED_DROPS_UNMINED_PLACEMENTS,
        )
        self.assertEqual(field_mobs.lane_withheld_placements(EXPECTED_SCENE), ())
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        shipped_placements = {mob.placement_index for mob in rows}
        for placement_index in EXPECTED_DROPS_UNMINED_PLACEMENTS:
            self.assertIn(placement_index, shipped_placements)
        mined = {
            row[0]: row for row in field_mob_tables_bg0009.HOSTILE_PLACEMENTS
        }
        for placement_index in EXPECTED_DROPS_UNMINED_PLACEMENTS:
            row = mined[placement_index]
            # (placement_index, template_id, x, y, z, visual_preset, ...,
            #  drops_normal, drops_equipment, drops_specially) -- the last
            # three columns are indices 13, 14, 15.
            self.assertTrue(row[5].startswith("M0"), row[5])
            self.assertEqual(row[13:16], (0, 0, 0))

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_registering_scene_nine_left_the_other_scenes_alone(self) -> None:
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(3)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(4)), 7)
        self.assertEqual(len(field_mobs.roster_for_scene_id(5)), 6)
        self.assertEqual(len(field_mobs.roster_for_scene_id(6)), 2)
        self.assertEqual(len(field_mobs.roster_for_scene_id(7)), 9)
        self.assertEqual(len(field_mobs.roster_for_scene_id(8)), 8)
        self.assertEqual(
            len(field_mobs.roster_for_scene_id(14)),
            12 - len(field_mobs.lane_withheld_placements("Bg0015")))
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 11)

    def test_the_shipped_templates_have_a_death_ruling_and_a_stray_row_still_refuses(
            self) -> None:
        self.assertIn(RULING_NAME, mob_death.WIDENING_RULINGS)
        self.assertEqual(
            mob_death.WIDENING_RULINGS[RULING_NAME],
            frozenset(
                row[1] for row in field_mob_tables_bg0009.HOSTILE_PLACEMENTS),
        )
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[RULING_NAME],
            field_mob_tables_bg0009.SCENE,
        )
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        seen_templates = set()
        for mob in rows:
            self.assertEqual(mob_death.ruling_for(mob), RULING_NAME)
            seen_templates.add(mob.template_id)
        self.assertEqual(
            seen_templates,
            frozenset(
                row[1] for row in field_mob_tables_bg0009.HOSTILE_PLACEMENTS),
        )

        a_shipped_row = rows[0]
        stray = field_mobs.FieldMob(
            placement_index=a_shipped_row.placement_index,
            template_id=916,
            x=a_shipped_row.x, y=a_shipped_row.y, z=a_shipped_row.z,
            visual_preset=a_shipped_row.visual_preset,
            display_name="stray-not-a-real-shipped-row",
            level=a_shipped_row.level,
            rank=a_shipped_row.rank,
            ai_wander=a_shipped_row.ai_wander,
            ai_combat=a_shipped_row.ai_combat,
            speed_walk=a_shipped_row.speed_walk,
            max_hp=a_shipped_row.max_hp,
            drops_normal=a_shipped_row.drops_normal,
            drops_equipment=a_shipped_row.drops_equipment,
            drops_specially=a_shipped_row.drops_specially,
            scene=EXPECTED_SCENE,
        )
        with self.assertRaises(mob_death.MobDeathContractError):
            mob_death.ruling_for(stray)


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0009RegenerateTests(unittest.TestCase):
    """Checks that need the bridge clone's gamedata beside this repo."""

    def test_regenerating_reproduces_the_committed_module_byte_for_byte(
            self) -> None:
        tool = _load_tool()
        sources = tool.Sources(GAMEDATA, EXPECTED_SCENE)
        rule = tool.IDENTITY_RULE_CLINE
        controls = tool.check_crosswalk_controls(sources)
        census = tool.predicate_census(sources, rule)
        roster = tool.hostile_roster(sources, rule)
        regenerated = tool.render_module(
            EXPECTED_SCENE, roster, sources.digests(), census,
            rule=rule, cline_type=sources.cline_type,
            town=tool.town_target_roster(sources, rule),
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
        self.assertEqual(
            regenerated, MODULE_PATH.read_text(encoding="ascii"),
            "src/pirateforce_foundation/field_mob_tables_bg0009.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0009 --identity-rule cline --out "
            "<this file>",
        )


if __name__ == "__main__":
    unittest.main()
