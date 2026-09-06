"""LANE-B: scene 8 (Bg0008, Silver Harbour) is a REGISTERED combat scene.

COO-DECISION widen-death-scope-bg0008-six-templates 2026-09-06T05:48+07:00
(notes_to_chief/20260906_0548_COO-DECISION-b0441-widen-death-scope-bg0008-
six-templates-nina-withheld-with-carlos-one-letter-for-five-scenes-next-
LANE-B.md), answering this lane's own ASK-COO 2026-09-06T04:41+07:00
(notes_to_chief/20260906_0441_LANE-B-ASK-COO-widen-death-scope-bg0008-
silver-harbour-seven-templates.md).  ``field_mob_tables_bg0008`` is
registered in ``field_mobs._SCENE_TABLE_MODULES`` in the same commit that
adds it, the same shape bg0003/bg0004/bg0005 already ship: no staged gate
like Bg0015's own history had.

WHAT IS DIFFERENT ABOUT THIS SCENE, AND WHY THIS FILE IS NOT A STRAIGHT COPY
OF bg0005'S OWN TEST MODULE.  The mining tool's hostility predicate finds
NINE placements over SEVEN distinct templates here -- but only SIX of the
seven are what this lane SHIPS.  Placement 69 (MOBS 529, "Nina") resolves to
avatar ``P_FEMALE_003_002_NENA`` (a PLAYER model, not a monster one) and
carries ZERO in every one of ``n_DROPS_NORMAL``/``n_DROPS_EQUIPMENT``/
``n_DROPS_SPECIALLY`` -- the same content-unknown shape Bg0015's Carlos
already has a ruling for -- so the 0548 letter's item 2 withholds her the
same way Carlos is withheld: ``field_mobs.LANE_WITHHELD_PLACEMENTS['Bg0008']
= (69,)``.  She is MINED (the raw ``HOSTILE_PLACEMENTS`` below has all nine
rows, the same generator behaviour Carlos's own row already established) and
NOT SHIPPED (``field_mobs.roster_for_scene_id(8)`` and
``mob_death.WIDENING_RULINGS``' new entry both cover only the other six).

THE THREE-AND-A-HALF THINGS THIS FILE MEASURES, of the ones that matter most:

``test_regenerating_reproduces_the_committed_module_byte_for_byte`` (gated on
the bridge clone) is the upstream drift control: nothing else re-derives
these rows from the client's own tables.

``test_the_ai_register_opens_for_every_shipped_row`` is the trap
``field_mob_ai_tables.py``'s own history already cost a round on scene 5, and
reproduced again here before this round widened
``tools/pf_mine_mob_ai_rows.py``'s union: ``mob_ai_control.open_register``
raised ``ai_row_missing: placement 23 points at AI_COMBAT 162`` on the
shipped eight-row roster.

``test_the_shipped_templates_have_a_death_ruling_a_stray_row_and_nina_still_
refuse`` is this scene's version of the ruling test every sibling scene
carries, widened by one clause: Nina's own placement, hand-built the same
shape a shipped row is, must refuse under ``mob_death.ruling_for`` exactly
like the stray-template test does, because ``field_mobs.load_roster``
dropping her placement index is a SEPARATE fact from ``mob_death`` having no
letter that names template 529 -- both must independently refuse, or a
future caller that reaches ``mob_death`` directly (bypassing the roster
filter) could still kill her.

THE "HALF": ``test_nina_is_withheld_not_merely_unmined`` is the same shape
``tests/test_field_mobs_scene_binding.py`` already holds Carlos to -- named
here too because a reader of THIS scene's own test module should not have to
go find Carlos's file to see the withholding contract this scene now shares.
"""

from __future__ import annotations

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

from pirateforce_foundation import field_mob_tables_bg0008  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0008.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "Bg0008"
EXPECTED_SCENE_ID = 8
# MINED, not shipped: the raw generated table's own HOSTILE_PLACEMENTS,
# Nina (placement 69, template 529) included -- the same list the AI-row
# miner and the cross-scene collision report both read directly.
EXPECTED_MINED_HOSTILE_COUNT = 9
EXPECTED_MINED_TEMPLATE_COUNT = 7
# SHIPPED: what field_mobs.load_roster / roster_for_scene_id actually
# return, after this lane's own withholding filter drops placement 69.
# EIGHT rows (280 "Walrus general" repeats at placements 26/51/52), over SIX
# distinct templates.
EXPECTED_SHIPPED_HOSTILE_COUNT = 8
EXPECTED_SHIPPED_TEMPLATE_COUNT = 6
EXPECTED_WITHHELD_PLACEMENTS = (69,)
EXPECTED_UNAMBIGUOUS = 33
# MEASURED, not required to agree with the hostile count: this scene's own
# four hostility readings do NOT all agree (rank=10, ai_combat=9,
# rank_and_ai_combat=9, drops_normal=8) -- one placement outside
# HOSTILE_PLACEMENTS has a rank with no combat AI, and Nina's own row is the
# one HOSTILE_PLACEMENTS member with a rank and a combat AI but zero in
# every drop column (the same fact the withholding ruling cites).
EXPECTED_CENSUS_RANK = 10
EXPECTED_CENSUS_AI_COMBAT = 9
EXPECTED_CENSUS_RANK_AND_AI_COMBAT = 9
EXPECTED_CENSUS_DROPS_NORMAL = 8

RULING_NAME = (
    "COO-DECISION widen-death-scope-bg0008-six-templates "
    "2026-09-06T05:48+07:00"
)

# The whole SHIPPED roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_SHIPPED_ROWS = (
    (21, 274, 0x2016, "Polar head"),
    (23, 277, 0x2018, "Polar Giant Turtle"),
    (26, 280, 0x201B, "Walrus general"),
    (27, 281, 0x201C, "Ice Carle Commander"),
    (51, 280, 0x2034, "Walrus general"),
    (52, 280, 0x2035, "Walrus general"),
    (66, 544, 0x2043, "Jet cat thieves No.9"),
    (67, 527, 0x2044, "Jet cat thieves No.10"),
)


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0008ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0008
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        # The project's ONE identity rule (COO-DECISION 2026-08-29T03:45).
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 8)
        self.assertEqual(
            len(module.HOSTILE_PLACEMENTS), EXPECTED_MINED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in module.HOSTILE_PLACEMENTS}),
            EXPECTED_MINED_TEMPLATE_COUNT,
        )
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank"], EXPECTED_CENSUS_RANK)
        self.assertEqual(census["ai_combat"], EXPECTED_CENSUS_AI_COMBAT)
        self.assertEqual(
            census["rank_and_ai_combat"], EXPECTED_CENSUS_RANK_AND_AI_COMBAT)
        self.assertEqual(census["drops_normal"], EXPECTED_CENSUS_DROPS_NORMAL)
        # This scene ships nothing under the retired set-number reading and
        # nothing off the town-target allowlist; asserted rather than assumed
        # so a future regeneration that starts shipping either is a failure.
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
        self.assertEqual(len(rows), EXPECTED_SHIPPED_HOSTILE_COUNT)
        self.assertEqual(
            len({mob.template_id for mob in rows}),
            EXPECTED_SHIPPED_TEMPLATE_COUNT)
        # Every row is stamped with THIS scene: the one thing
        # ``assert_single_scene_tables`` exists to stop is two scenes' rows
        # merged into one roster.
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_nina_is_withheld_not_merely_unmined(self) -> None:
        """Same contract Carlos already has, named for this scene's own row.

        Mirrors ``tests/test_field_mobs_scene_binding.py``'s own Bg0015
        withholding checks: the row IS mined (present in the generated
        table's own ``HOSTILE_PLACEMENTS``) and is NOT shipped (absent from
        ``load_roster`` / ``roster_for_scene_id``), and the two facts are
        checked separately so a future regeneration that stops mining her at
        all cannot be mistaken for this lane's own ruling still applying.
        """
        self.assertEqual(
            field_mobs.lane_withheld_placements(EXPECTED_SCENE),
            EXPECTED_WITHHELD_PLACEMENTS)
        mined_placements = {
            row[0]: row[1] for row in field_mob_tables_bg0008.HOSTILE_PLACEMENTS
        }
        self.assertEqual(mined_placements[69], 529)
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertNotIn(69, {mob.placement_index for mob in rows})
        self.assertNotIn(529, {mob.template_id for mob in rows})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """The trap that unwinds the listener thread on the FIRST swing.

        Reproduced on scene 8 this round before
        ``tools/pf_mine_mob_ai_rows.py``'s union was widened:
        ``MobAiControlError: ai_row_missing: placement 23 points at
        AI_COMBAT 162, which is not in the mined rows``.  A future round
        that adds a roster row citing an unmined AI id fails here instead of
        in front of a player.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_registering_scene_eight_left_the_other_scenes_alone(
            self) -> None:
        """A sixth scene must not move the five already on the wire."""
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(5)), 6)
        self.assertEqual(
            len(field_mobs.roster_for_scene_id(14)),
            12 - len(field_mobs.lane_withheld_placements("Bg0015")))
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 11)
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "c1a341c9d7721db45b07e2e7df2840719da5fcbcf5521d7f31eabd4a1ce26934")
        self.assertEqual(len(raw), 12316)

    def test_the_shipped_templates_have_a_death_ruling_a_stray_row_and_nina_still_refuse(
            self) -> None:
        """WHAT CHANGED THIS ROUND, pinned rather than left implicit.

        The 0548 letter approves exactly the SIX shipped templates, under
        the exact ruling name pinned below -- re-derived from the shipped
        roster rather than hand-copied, the same discipline
        ``mob_death.py``'s own comments hold every other ruling to.

        THE STRAY ROW is the same technique every sibling scene's own test
        uses: a hand-built FieldMob stamped ``scene="Bg0008"`` carrying a
        template no ruling here names (916, the Training Iron Man dummy,
        ruled ONLY for bg0001) must still refuse.

        NINA, HAND-BUILT THE SAME SHAPE, must ALSO refuse -- and for a
        DIFFERENT reason than the stray row: the stray row's template has
        never been mined for this scene at all, while Nina's template (529)
        really is one of this scene's own mined rows and simply has no
        letter naming it.  Both paths through ``mob_death.ruling_for`` must
        independently refuse, because ``field_mobs.load_roster`` dropping
        her placement index is a roster-shape fact, not a ``mob_death``
        one -- a caller that reaches ``mob_death.kill`` directly, bypassing
        the roster filter (as the diagnostic call site does for OTHER
        monsters), must still be refused by the ruling itself.
        """
        self.assertIn(RULING_NAME, mob_death.WIDENING_RULINGS)
        self.assertEqual(
            mob_death.WIDENING_RULINGS[RULING_NAME],
            frozenset(
                row[1] for row in field_mob_tables_bg0008.HOSTILE_PLACEMENTS
                if row[0] != 69),
        )
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[RULING_NAME],
            field_mob_tables_bg0008.SCENE,
        )
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(len(rows), EXPECTED_SHIPPED_HOSTILE_COUNT)
        seen_templates = set()
        for mob in rows:
            self.assertEqual(mob_death.ruling_for(mob), RULING_NAME)
            seen_templates.add(mob.template_id)
        self.assertEqual(
            seen_templates,
            frozenset(
                row[1] for row in field_mob_tables_bg0008.HOSTILE_PLACEMENTS
                if row[0] != 69),
        )
        self.assertNotIn(529, mob_death.WIDENING_RULINGS[RULING_NAME])

        # The stray row: same scene, a template this ruling never named.
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

        # Nina, hand-built the same shape a shipped row is (this scene's own
        # mined values for placement 69, not invented ones) -- refused for a
        # DIFFERENT reason than the stray row above, and that reason is
        # checked by name.
        nina_row = next(
            row for row in field_mob_tables_bg0008.HOSTILE_PLACEMENTS
            if row[0] == 69)
        (_placement, template_id, x, y, z, visual_preset, display_name,
         level, rank, ai_wander, ai_combat, speed_walk, max_hp, drops_normal,
         drops_equipment, drops_specially) = nina_row
        nina = field_mobs.FieldMob(
            placement_index=69, template_id=template_id, x=x, y=y, z=z,
            visual_preset=visual_preset, display_name=display_name,
            level=level, rank=rank, ai_wander=ai_wander, ai_combat=ai_combat,
            speed_walk=speed_walk, max_hp=max_hp, drops_normal=drops_normal,
            drops_equipment=drops_equipment,
            drops_specially=drops_specially, scene=EXPECTED_SCENE,
        )
        self.assertEqual(nina.template_id, 529)
        self.assertEqual(mob_death.rulings_covering(nina), ())
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(nina)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0008RegenerateTests(unittest.TestCase):
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
            "src/pirateforce_foundation/field_mob_tables_bg0008.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0008 --identity-rule cline --out "
            "<this file>",
        )


if __name__ == "__main__":
    unittest.main()
