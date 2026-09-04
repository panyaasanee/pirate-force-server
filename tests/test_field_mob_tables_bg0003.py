"""LANE-B: scene 3 (Bg0003) is a REGISTERED combat scene -- and still not
a scene anybody can fight in.

ROUND am1fw8.  Same shape as scene 5's card (round jqeo2m) and registered in
the same commit that mines it, for the same reason: lane A opened scene 3's
arrival census AND its ``login_entry_allowed`` door rounds ago, so a player
can stand in this map today; what they could not do until this commit is
swing at anything in it, because ``field_mobs.scene_for_scene_id(3)``
returned ``None``.

WHAT THIS ROUND DOES NOT CLAIM, said here rather than in a PR body nobody
re-reads.  A player STILL cannot damage a monster in scene 3, and this file
measures both halves of why:

* ``test_the_lane_composed_membership_seam_is_still_shut_for_this_scene``
  -- scene 3 arrives through ``runtime.py``'s lane-composed census branch,
  which stamps an EMPTY announced membership on purpose, and the RE-157 gate
  refuses every unannounced target.  Opening that seam is CORE-REQUEST
  ``20260904_1134``, addressed to chief, still open at this commit; scene 3
  is now the THIRD scene armed behind it (``tests/
  test_field_mob_tables_bg0005.py``'s ``LaneComposedScenesAreNotFightableYet
  Test`` carries the set, and this round moved it from ``(5, 14)`` to
  ``(3, 5, 14)`` rather than quietly widening it).
* ``test_no_scene_three_row_has_a_death_ruling_yet_and_that_refuses`` -- no
  COO letter sanctions killing anything in this scene, so even past an open
  seam every scene-3 target refuses with
  ``target_outside_the_sanctioned_scope``.  The letter asking for one goes
  out this round (``20260904_1345_LANE-B-ASK-COO-...``); this card is what
  turns red when it is granted, which is how the grant cannot land without
  the roster it names being checked against the rows actually shipped.

THE COLLISION MEASUREMENT.  Scene 3's twelve placements bring FOUR new
cross-scene ``actor_identity`` collisions at once (0x201C and 0x201E against
Bg0015, 0x203B against Bg0002, 0x2046 against bg0005) -- more than doubling
the three this project had.  ``tests/test_field_mobs.py``'s collision card
demands a fresh walk of strike/ledger/rehydration/death/loot whenever one
appears; the walk's reading half is recorded there, and its MEASUREMENT half
is ``test_scene_fives_kill_permission_does_not_reach_scene_threes_0x2046``
here: two real monsters, two scenes, one wire identity, and the ruling that
covers one of them refusing the other.
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

from pirateforce_foundation import field_mob_tables_bg0003  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0005  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_bg0003_identity  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0003.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "Bg0003"
EXPECTED_SCENE_ID = 3
EXPECTED_HOSTILE_COUNT = 12
EXPECTED_TEMPLATE_COUNT = 7
EXPECTED_UNAMBIGUOUS = 37
# All four hostility readings agree at 12 on this scene, the same MEASURED
# (not lawful) agreement scene 5 had at 6 -- the generator's own docstring
# says a scene where they disagree must be read before its roster ships, so
# each is pinned separately and a future divergence is a named failure
# rather than a silently different roster.
EXPECTED_DROPS_NORMAL = 12

# The whole shipped roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_ROWS = (
    (27, 61, 0x201C, "Toxic Vine"),
    (28, 61, 0x201D, "Toxic Vine"),
    (29, 62, 0x201E, "Ancient Civilization Alert Weapon"),
    (33, 65, 0x2022, "Ward Apes"),
    (34, 62, 0x2023, "Ancient Civilization Alert Weapon"),
    (35, 60, 0x2024, "Jungle Big Tiger"),
    (39, 194, 0x2028, "Jet cat thieves No.2"),
    (40, 515, 0x2029, "Jet cat thieves No.1"),
    (41, 62, 0x202A, "Ancient Civilization Alert Weapon"),
    (42, 62, 0x202B, "Ancient Civilization Alert Weapon"),
    (58, 907, 0x203B, "Sediment Wolf"),
    (69, 907, 0x2046, "Sediment Wolf"),
)

# The AI foreign keys this scene's rows point at, named so a regeneration of
# ``field_mob_ai_tables`` from a narrower union is a failure here with the
# ids in the message rather than an ``ai_row_missing`` in front of a player.
EXPECTED_AI_COMBAT_IDS = frozenset({100, 123, 133, 140, 240, 250})
EXPECTED_AI_WANDER_IDS = frozenset({11, 16})

# Measured immediately before field_mob_tables_bg0003.py was added, on the
# same discipline as the bg0005 and bg0015 cards: never updated to make a
# future edit of field_mob_tables.py pass silently.
BG0001_UNTOUCHED_SHA256 = (
    "574fdca1391eb0aa4bc4a5a2b46b50c090839a86baf94426573312afff2866a5"
)
BG0001_UNTOUCHED_SIZE = 9708


def _load_tool():
    spec = importlib.util.spec_from_file_location(
        "pf_mine_scene_mob_roster", TOOL_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Bg0003ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(
            self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0003
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        # The project's ONE identity rule (COO-DECISION 2026-08-29T03:45),
        # named here rather than inherited from the tool's default.
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 3)
        self.assertEqual(
            len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in module.HOSTILE_PLACEMENTS}),
            EXPECTED_TEMPLATE_COUNT,
        )
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["drops_normal"], EXPECTED_DROPS_NORMAL)
        self.assertEqual(census["town_target"], 0)
        # Nothing under the retired set-number reading, nothing off the
        # town-target allowlist: asserted rather than assumed, so a future
        # regeneration that starts shipping either is a failure.
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
            EXPECTED_ROWS,
        )
        # Every row stamped with THIS scene: a roster that reached a strike
        # under another scene's name is what ``assert_single_scene_tables``
        # exists to stop, one layer down.
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """The trap that unwinds the listener thread on the FIRST swing.

        Reproduced on scene 3 this round BEFORE ``tools/pf_mine_mob_ai_rows
        .py``'s union was widened, exactly as round jqeo2m reproduced it on
        scene 5 rather than predicting it: ``MobAiControlError:
        ai_row_missing: placement 27 points at AI_COMBAT 140, which is not
        in the mined rows``.  ``runtime.py``'s ``_sync_combat_scene_state``
        sits ABOVE every ``except`` in ``_dispatch_mob_combat``, so that
        refusal empties a walking player's world.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_the_ai_ids_this_scene_depends_on_are_named_not_just_resolved(
            self) -> None:
        """``open_register`` passing says the union is wide enough TODAY.

        This says WHICH ids it has to stay wide enough for, so a regenerated
        AI table that drops one names the id instead of failing as a bare
        ``ai_row_missing`` in the test above.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            {mob.ai_combat for mob in rows}, EXPECTED_AI_COMBAT_IDS)
        self.assertEqual(
            {mob.ai_wander for mob in rows}, EXPECTED_AI_WANDER_IDS)

    def test_registering_scene_three_left_the_other_four_scenes_alone(
            self) -> None:
        """A fifth scene must not move the four already on the wire."""
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(5)), 6)
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 12)
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         BG0001_UNTOUCHED_SHA256)
        self.assertEqual(len(raw), BG0001_UNTOUCHED_SIZE)

    def test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk(
            self) -> None:
        """The control measured ON the scene being mined.

        Lane A resolved this scene's CLINE type 3 block with its own miner
        for its own arrival census (``world_bg0003_identity.IDENTITIES``);
        this lane's generator resolved it again for the combat roster.  Two
        lanes, two tools, one answer per row -- or this names the row that
        disagrees.  The failure it exists to catch is GT-078's: a map
        wearing another map's names.
        """
        sets = field_mob_tables_bg0003.SET_NUMBER_FOR_PLACEMENT
        disagreements = []
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            set_number = sets[mob.placement_index]
            theirs = world_bg0003_identity.IDENTITIES.get(set_number)
            if theirs is None:
                disagreements.append(
                    "placement %d (Mob-Set %d) resolves to %d here and is "
                    "UNRESOLVED in lane A's table"
                    % (mob.placement_index, set_number, mob.template_id))
                continue
            if (theirs.mobs_n_id, theirs.name) != (
                    mob.template_id, mob.display_name):
                disagreements.append(
                    "placement %d (Mob-Set %d): lane B says %d %r, lane A "
                    "says %d %r" % (
                        mob.placement_index, set_number, mob.template_id,
                        mob.display_name, theirs.mobs_n_id, theirs.name))
        self.assertEqual(
            disagreements, [],
            "the two independently mined readings of CLINE type 3 disagree; "
            "GT-078 is what shipping the wrong one costs, so stop and find "
            "out which miner is wrong before regenerating either table",
        )


class Bg0003CannotBeKilledYetTests(unittest.TestCase):
    """No COO letter sanctions a death in this scene.  Measured, not read."""

    def test_no_scene_three_row_has_a_death_ruling_yet_and_that_refuses(
            self) -> None:
        refusals = []
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            with self.assertRaises(mob_death.MobDeathContractError) as caught:
                mob_death.ruling_for(mob)
            refusals.append(str(caught.exception))
        self.assertEqual(len(refusals), EXPECTED_HOSTILE_COUNT)
        for reason in refusals:
            self.assertIn("target_outside_the_sanctioned_scope", reason)

    def test_scene_fives_kill_permission_does_not_reach_scene_threes_0x2046(
            self) -> None:
        """The collision walk's measurement half, on REAL rows of both
        scenes rather than a hand-built pair.

        Placement 69 exists in both scenes, so both monsters compute the
        same wire ``actor_identity`` 0x2046 -- and scene 5's placement 69
        (``Ned apes``, template 150) is covered by ``COO-DECISION
        2026-09-04T11:48+07:00`` while scene 3's (``Sediment Wolf``,
        template 907) is covered by nothing.  If a ruling were keyed by
        anything the two share, this would pass the wrong one through.
        """
        three = {
            mob.placement_index: mob
            for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        }[69]
        five = {
            mob.placement_index: mob
            for mob in field_mobs.roster_for_scene_id(5)
        }[69]
        self.assertEqual(three.actor_identity, five.actor_identity)
        self.assertEqual(three.actor_identity, 0x2046)
        self.assertNotEqual(three.template_id, five.template_id)
        self.assertNotEqual(three.scene, five.scene)
        # The sanctioned side really is sanctioned -- otherwise this test
        # would pass just as well on a project where nothing can die.
        self.assertIn("widen-death-scope-bg0005", mob_death.ruling_for(five))
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(three)
        self.assertIn("target_outside_the_sanctioned_scope",
                      str(caught.exception))

    def test_the_other_three_new_collisions_are_different_monsters(
            self) -> None:
        """0x201C / 0x201E against Bg0015 and 0x203B against Bg0002.

        Not a proof of scope on its own -- it is the cheaper half: no pair
        is two spellings of ONE monster, so a scope defect would have to
        carry a visibly wrong name and template, not merely a wrong scene.
        """
        three = {
            mob.placement_index: mob
            for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        }
        others = {
            14: {
                mob.placement_index: mob
                for mob in field_mobs.load_roster(field_mobs.BG0015_SCENE)
            },
            2: {
                mob.placement_index: mob
                for mob in field_mobs.load_roster(field_mobs.BG0002_SCENE)
            },
        }
        for placement, other_scene_id in ((27, 14), (29, 14), (58, 2)):
            mine = three[placement]
            theirs = others[other_scene_id][placement]
            with self.subTest(placement=placement):
                self.assertEqual(mine.actor_identity, theirs.actor_identity)
                self.assertNotEqual(mine.template_id, theirs.template_id)
                self.assertNotEqual(mine.display_name, theirs.display_name)
                self.assertNotEqual(mine.scene, theirs.scene)


class Bg0003RecomposeRegistrationTests(unittest.TestCase):
    """Scene 3 moved from "acknowledged without a composer" to composed."""

    def test_scene_three_is_no_longer_acknowledged_without_a_composer(
            self) -> None:
        self.assertNotIn(
            EXPECTED_SCENE_ID,
            mob_scene_recompose.declared_without_composer(),
            "scene 3 has a composer now; an entry in the acknowledgement "
            "dict as well would be this lane saying both things at once",
        )
        self.assertIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.composer_scene_ids())
        self.assertTrue(
            mob_scene_recompose.scene_is_accounted_for(EXPECTED_SCENE_ID))

    def test_the_new_composer_kind_is_non_delegated_and_has_a_builder(
            self) -> None:
        composer = mob_scene_recompose.composer_for_scene_id(
            EXPECTED_SCENE_ID)
        self.assertEqual(composer.kind, mob_scene_recompose.COMPOSER_BG0003)
        self.assertEqual(composer.scene, EXPECTED_SCENE)
        self.assertIn(
            composer.kind, mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS)
        # The import-time assertion round jqeo2m added is what makes "the
        # tuple and the builder table agree" checkable rather than a
        # property of how they happen to be typed today.  Called here on the
        # real pair, so scene 3's entry is covered by it and not merely
        # beside it.
        mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder()
        builder = mob_scene_recompose._POPULATION_BUILDERS[composer.kind]
        self.assertEqual(builder.serves_scene_id, EXPECTED_SCENE_ID)


class Bg0003NotFightableYetTests(unittest.TestCase):
    """The two shut doors between this roster and a player hitting it."""

    def test_the_lane_composed_membership_seam_is_still_shut_for_this_scene(
            self) -> None:
        """Scene 3 is armed BEHIND the seam, not past it.

        The runtime sentence this pins is the same one scene 5's card pins;
        it is re-asserted here so scene 3's own file fails on the day the
        seam opens, rather than leaving the whole finding hanging off
        another scene's test file.
        """
        raw = (SRC / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8")
        runtime_src = " ".join(raw.replace("#", " ").split())
        self.assertIn(
            "no lane scene a player can stand in and fight in exists yet",
            runtime_src,
            "the lane-composed arrival branch's own justification has "
            "changed.  If the seam was opened, scene 3 is one of the "
            "scenes that just became fightable -- say so with a "
            "measurement, and update this card and scene 5's together",
        )
        self.assertIn(
            EXPECTED_SCENE_ID,
            tuple(
                scene_id
                for scene_id in sorted(
                    mob_scene_recompose.composer_scene_ids())
                if scene_id not in (1, 2)
            ),
        )


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0003RegenerateTests(unittest.TestCase):
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
            "src/pirateforce_foundation/field_mob_tables_bg0003.py is stale "
            "- regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene Bg0003 --identity-rule cline --out "
            "<this file>",
        )

    def test_the_placement_path_resolves_a_scene_whose_two_halves_disagree(
            self) -> None:
        """Why this scene needed a generator fix before it could be mined.

        The bridge clone spells scene 3 ``scene/Bg0003/bg0003.placements
        .tsv`` -- capitalised directory, lowercase file.  Scene 1 is
        lower/lower and scene 2 is upper/upper, so until this round the
        generator's ``<S>/<S>.placements.tsv`` was right about every scene
        it had ever mined, and on Linux BOTH spellings of scene 3's own name
        refused with "missing source table".  Windows could not see it.
        """
        tool = _load_tool()
        resolved = tool.resolve_placement_path(GAMEDATA, EXPECTED_SCENE)
        self.assertTrue(resolved.is_file())
        self.assertEqual(resolved.name, "bg0003.placements.tsv")
        self.assertEqual(resolved.parent.name, "Bg0003")
        # The other spelling of the same scene finds the same file, and the
        # scenes whose halves DO agree are unaffected.
        self.assertEqual(
            tool.resolve_placement_path(GAMEDATA, "bg0003"), resolved)
        self.assertEqual(
            tool.resolve_placement_path(GAMEDATA, "bg0005").name,
            "bg0005.placements.tsv")
        self.assertEqual(
            tool.resolve_placement_path(GAMEDATA, "Bg0002").name,
            "Bg0002.placements.tsv")

    def test_the_resolver_refuses_a_scene_that_is_not_there(self) -> None:
        """It resolves case, it does not invent a scene."""
        tool = _load_tool()
        with self.assertRaises(tool.MineError) as caught:
            tool.resolve_placement_path(GAMEDATA, "Bg9999")
        self.assertIn("missing source table", str(caught.exception))

    def test_the_resolver_refuses_rather_than_picking_between_two(
            self) -> None:
        """Two directories differing only in case is a coin flip, and this
        tool does not flip coins -- checked on a temporary tree, because the
        real clone (rightly) has no such pair to point it at."""
        import tempfile

        tool = _load_tool()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ("Bg0099", "bg0099"):
                directory = root / "scene" / name
                directory.mkdir(parents=True)
                (directory / ("%s.placements.tsv" % name)).write_text(
                    "n_ID\n1\n", encoding="ascii")
            with self.assertRaises(tool.MineError) as caught:
                tool.resolve_placement_path(root, "BG0099")
        self.assertIn("refusing", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
