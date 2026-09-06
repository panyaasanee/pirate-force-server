"""LANE-B: scene 10 (Bg0010) is a REGISTERED scene whose mobs CANNOT be killed.

Round 30ja9z.  Every sibling scene module this lane has shipped so far landed
its roster and its ``mob_death`` widening ruling in the same commit, under a
COO-DECISION that names the scene.  THIS ONE DOES NOT, and the split is the
point of this file:

* The SPAWN half (M3, "the field has monsters") ships here.  Seventeen
  placements over six distinct templates, mined by
  ``tools/pf_mine_scene_mob_roster.py`` under the project's one identity rule
  (``cline``), registered in ``field_mobs._SCENE_TABLE_MODULES``.
* The KILL half (M4) does NOT.  No letter widens the death scope to Bg0010,
  so ``mob_death.WIDENING_RULINGS`` carries no Bg0010 key and
  ``mob_death.ruling_for`` refuses all seventeen bodies.  That refusal is
  PINNED below as the intended behaviour of this round, not tolerated as an
  accident: a later round that adds the ruling has to come back here and say
  so, instead of silently flipping seventeen monsters from decorative to
  killable.

WHY THE ROSTER SHIPS AT ALL WHILE ONE ROW IS UNREADABLE.  Bg0010's raw
placement 50 names ``Mob_Set_99``, which the scene's own file never defines;
the generator reports it and keeps going (COO-DECISION 2026-09-06T07:48+07:00
item 3 approved exactly that shape), and it is absent from
``HOSTILE_PLACEMENTS`` and named in the module's ``UNRESOLVED_PLACEMENTS``.
The STATIC ticket that asks what that row is (pf_bridge
notes_to_chief/20260906_0903 plus its 1046 addendum) has no number and no
answer.  Registering the sixteen-plus-one READABLE rows meanwhile is this
lane's own call under item 4 of the same letter ("silent more than 1 hour,
keep going, no need to ask") and is tagged as an assumption in
``field_mobs``' own BG0010_SCENE comment.  Nothing here decides what
placement 50 is.
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

from pirateforce_foundation import field_mob_tables_bg0010  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0010.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "Bg0010"
EXPECTED_SCENE_ID = 10
EXPECTED_HOSTILE_COUNT = 17
EXPECTED_TEMPLATE_COUNT = 6
EXPECTED_TEMPLATES = frozenset({660, 661, 662, 668, 671, 673})
EXPECTED_UNAMBIGUOUS = 35
EXPECTED_CENSUS_RANK = 17
EXPECTED_CENSUS_AI_COMBAT = 17
EXPECTED_CENSUS_RANK_AND_AI_COMBAT = 17
EXPECTED_CENSUS_DROPS_NORMAL = 17

# The raw row the crosswalk cannot resolve AT ALL -- the STATIC ticket's whole
# subject.  ``UNRESOLVED_PLACEMENTS`` is a longer list than this one row: the
# generator files every placement it declined to ship there WITH ITS REASON,
# and most of Bg0010's entries carry the ordinary reason
# ``n_id_<n>_avatar_is_a_variant_list``.  Placement 50 is the different one --
# its template id is not a number at all, because the scene names
# ``Mob_Set_99`` and its own file never defines it.  Pinned so a future
# generator change that starts SHIPPING it, or that stops naming it, fails
# here rather than silently answering a question chief has not answered.
EXPECTED_UNRESOLVED_ROW = (50, 0, "template_id_is_not_a_number_UNRESOLVED")

# The whole SHIPPED roster, spelled out rather than counted.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_SHIPPED_ROWS = (
    (24, 662, 0x2019, "Abyss Demon Wolf"),
    (31, 660, 0x2020, "Skeleton Commander Lebiya"),
    (32, 661, 0x2021, "Exotic Demon Wolf"),
    (39, 668, 0x2028, "Navy Two Tripods"),
    (46, 673, 0x202F, "Seabed Wanderer"),
    (47, 671, 0x2030, "Crusty Bone Fish"),
    (48, 671, 0x2031, "Crusty Bone Fish"),
    (90, 661, 0x205B, "Exotic Demon Wolf"),
    (91, 661, 0x205C, "Exotic Demon Wolf"),
    (92, 661, 0x205D, "Exotic Demon Wolf"),
    (93, 661, 0x205E, "Exotic Demon Wolf"),
    (94, 661, 0x205F, "Exotic Demon Wolf"),
    (95, 661, 0x2060, "Exotic Demon Wolf"),
    (96, 662, 0x2061, "Abyss Demon Wolf"),
    (97, 662, 0x2062, "Abyss Demon Wolf"),
    (98, 662, 0x2063, "Abyss Demon Wolf"),
    (99, 662, 0x2064, "Abyss Demon Wolf"),
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0010ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0010
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 10)
        self.assertEqual(len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            {row[1] for row in module.HOSTILE_PLACEMENTS}, EXPECTED_TEMPLATES)
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank"], EXPECTED_CENSUS_RANK)
        self.assertEqual(census["ai_combat"], EXPECTED_CENSUS_AI_COMBAT)
        self.assertEqual(
            census["rank_and_ai_combat"], EXPECTED_CENSUS_RANK_AND_AI_COMBAT)
        self.assertEqual(census["drops_normal"], EXPECTED_CENSUS_DROPS_NORMAL)
        self.assertEqual(census["town_target"], 0)
        self.assertEqual(module.TOWN_TARGET_PLACEMENTS, [])
        self.assertEqual(module.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION, [])

    def test_the_unresolved_raw_row_is_named_and_never_shipped(self) -> None:
        module = field_mob_tables_bg0010
        unresolved = tuple(tuple(row) for row in module.UNRESOLVED_PLACEMENTS)
        self.assertIn(EXPECTED_UNRESOLVED_ROW, unresolved)
        # Exactly one row carries the "not a number" reason.  The rest are the
        # ordinary variant-list declines and are not this ticket's subject.
        self.assertEqual(
            [row for row in unresolved if not isinstance(row[1], int) or row[1] == 0],
            [EXPECTED_UNRESOLVED_ROW],
        )
        # Nothing unresolved is shipped, by index, under any reason.
        shipped_indices = {row[0] for row in module.SHIPPED_PLACEMENTS}
        for row in unresolved:
            self.assertNotIn(row[0], shipped_indices)
        # And placement 50 is absent from what the loader hands downstream.
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertNotIn(
            EXPECTED_UNRESOLVED_ROW[0],
            {mob.placement_index for mob in rows},
        )

    def test_no_shipped_row_is_a_player_model_body(self) -> None:
        """The Nina/Carlos withhold shape, checked rather than assumed.

        That rule (COO-DECISION 2026-09-06T07:48+07:00 item 2) withholds a row
        only when BOTH halves hold: a ``P_`` player avatar AND a 0/0/0 drop
        row.  Every Bg0010 row carries an ``M`` monster body, so no row is
        withheld and ``lane_withheld_placements`` is empty for this scene.
        """
        for row in field_mob_tables_bg0010.HOSTILE_PLACEMENTS:
            visual_preset = row[5]
            self.assertFalse(
                visual_preset.startswith("P_"),
                "placement %d ships a player-model body %r" % (
                    row[0], visual_preset),
            )
            self.assertTrue(visual_preset.startswith("M"))
        self.assertEqual(field_mobs.lane_withheld_placements(EXPECTED_SCENE), ())

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
        self.assertEqual({mob.template_id for mob in rows}, EXPECTED_TEMPLATES)
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_every_shipped_row_refuses_a_kill_because_no_letter_covers_it(
            self) -> None:
        """M4 is deliberately withheld from this scene.  Pin it, do not assume.

        A ruling arriving later is fine and expected -- but it has to edit this
        test to arrive, which is the whole point: seventeen monsters must not
        become killable as a side effect of somebody else's round.
        """
        for name, scene in mob_death.WIDENING_RULING_SCENES.items():
            self.assertNotEqual(
                scene, EXPECTED_SCENE,
                "a ruling (%r) now ties the death scope to %s; the roster "
                "shipped WITHOUT one on purpose, so update this test and "
                "field_mobs' BG0010_SCENE comment together" % (
                    name, EXPECTED_SCENE),
            )
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        for mob in rows:
            with self.assertRaises(mob_death.MobDeathContractError):
                mob_death.ruling_for(mob)

    def test_registering_scene_ten_left_the_other_scenes_alone(self) -> None:
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(3)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(4)), 7)
        self.assertEqual(len(field_mobs.roster_for_scene_id(5)), 6)
        self.assertEqual(len(field_mobs.roster_for_scene_id(6)), 2)
        self.assertEqual(len(field_mobs.roster_for_scene_id(7)), 9)
        self.assertEqual(len(field_mobs.roster_for_scene_id(8)), 8)
        self.assertEqual(len(field_mobs.roster_for_scene_id(9)), 5)
        self.assertEqual(len(field_mobs.roster_for_scene_id(11)), 10)
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 11)

    def test_the_shipped_templates_do_not_ride_another_scenes_ruling(
            self) -> None:
        """Template ids are shared across scenes; the scene tie is what saves us.

        660/661/662/668/671/673 must not be reachable through any OTHER
        scene's ruling for a Bg0010 body.  ``ruling_for`` already refuses
        above; this asserts the reason -- no ruling set contains one of these
        templates under a scene tie that is not Bg0010's.
        """
        for name, templates in mob_death.WIDENING_RULINGS.items():
            overlap = EXPECTED_TEMPLATES & set(templates)
            if not overlap:
                continue
            self.assertNotEqual(
                mob_death.WIDENING_RULING_SCENES.get(name), EXPECTED_SCENE,
                "ruling %r would authorise Bg0010 templates %r" % (
                    name, sorted(overlap)),
            )


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0010RegenerateTests(unittest.TestCase):
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
            "src/pirateforce_foundation/field_mob_tables_bg0010.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0010 --identity-rule cline --out "
            "<this file>",
        )


if __name__ == "__main__":
    unittest.main()
