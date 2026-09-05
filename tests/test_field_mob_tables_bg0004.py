"""LANE-B: scene 4 (bg0004, Slave Market Island) is a REGISTERED combat
scene, and the FIRST this lane has armed through all three doors in the round
that mined it.

ROUND r6isy5, on COO-DECISION 2026-09-05T05:46+07:00 ("roster of scene 4 +
the kill letter of scene 4, in the shape of scenes 3/5"), which is also the
letter that closed 1450 item 3 and put this scene back in the queue.

WHAT A PLAYER SEES THAT THEY DID NOT YESTERDAY.  Seven monsters in the Slave
Market appear as red-named, clickable, killable targets that drop loot on the
ground.  Lane A opened this map's arrival census AND its
``login_entry_allowed`` door back in round bq4mst -- scene 4 was the FIRST of
the ten doors that opened -- so a player has been able to stand here for days
with nothing in the map to swing at, because
``field_mobs.scene_for_scene_id(4)`` returned ``None``.  That is what this
commit changes.  What it does NOT change is the attended half: NOW.md still
forbids an on-screen monster-hit GT for scenes 3/4/5/14 until P-2 (monster
name colour) closes, so nobody has WATCHED any of this yet, and this card
does not claim they have.

THE THREE THINGS THAT MAKE THIS SCENE DIFFERENT FROM 3, 5 AND 14, each
measured below rather than asserted in a PR body:

* THE FOUR HOSTILITY PREDICATES DISAGREE, for the first time in any scene
  this lane ships: ai_combat 9, rank 7, drops_normal 7,
  rank_and_ai_combat 7.  The generator's own docstring says a scene where
  they disagree "must be read before its roster is shipped"; the reading is
  in ``field_mobs.BG0004_SCENE``'s comment and the two extra rows are pinned
  by name here (``test_the_two_rank_zero_combat_rows_are_named_and_not_
  shipped``).
* IT IS THE FIRST SCENE TO CARRY AN UNMINED ``n_DROPS_SPECIALLY`` SET.
  Templates 94 and 97 name sets 2802253 and 2802236, which
  ``field_drop_tables`` had never seen, and the drop door was MEASURED shut
  on them before the miner was widened -- ``target=7 kill=7 drop=3`` with
  four rows refusing ``drop:unknown_drop_set``.  Widened, it walks 7/7/7.
* 0x2046 IS NOW A THREE-WAY IDENTITY COLLISION (scenes 3, 4 and 5 all have a
  placement 69), and scene 3's ledger covers TWO of this scene's seven
  identities -- the widest partial overlap this project has had, and exactly
  the shape a coverage-counting admission would let through.  It does not:
  see ``Bg0004CollisionWalkTests``.

WHAT IS THIS LANE'S ASSUMPTION AND NOT THE LETTER'S.  0546 ordered a kill
letter for this scene but could not name its template ids, because nobody had
mined the scene when it was written.  The five ids are this lane's answer,
tagged in ``mob_death.WIDENING_RULINGS`` and asked in
``notes_to_chief/20260905_1031_LANE-B-ASK-COO-scene-4-five-templates-need-a-
death-ruling.md``.  If the COO refuses one, the ruling entry loses that id
and these tests go red naming it -- which is the point of pinning the five
rather than counting them.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import field_drop_tables  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0004  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_ledger_admission  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_bg0004_identity  # noqa: E402
from pirateforce_foundation.lane_hooks import lane_a_scene_census  # noqa: E402


TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0004.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "bg0004"
EXPECTED_SCENE_ID = 4
EXPECTED_HOSTILE_COUNT = 7
EXPECTED_TEMPLATE_COUNT = 5
EXPECTED_UNAMBIGUOUS = 65

# THE FOUR READINGS DO NOT AGREE ON THIS SCENE, unlike scenes 3 (12/12/12/12)
# and 5 (6/6/6/6).  Each is pinned separately -- that is what the separate
# constants are FOR, and this is the first scene that spends them.
EXPECTED_AI_COMBAT_CENSUS = 9
EXPECTED_RANK_CENSUS = 7
EXPECTED_DROPS_NORMAL = 7

# The two placements with a combat AI at rank 0.  Not shipped, and named
# here so that a re-mine which starts shipping them is a failure with their
# ids in the message rather than two new monsters nobody decided on.
EXPECTED_RANK_ZERO_COMBAT = (
    (75, 640, "Crazy Rose Regina", 3),
    (76, 641, "Blood dragon Norman", 3),
)

# The whole shipped roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_ROWS = (
    (30, 94, 0x201F, "An Gebo Little Firebird"),
    (31, 94, 0x2020, "An Gebo Little Firebird"),
    (32, 94, 0x2021, "An Gebo Little Firebird"),
    (42, 97, 0x202B, "Mutant Green Eagle"),
    (69, 103, 0x2046, "Orc Chief"),
    (82, 519, 0x2053, "Jet cat thieves No.3"),
    (83, 246, 0x2054, "Jet cat thieves No.4"),
)

# The five ids the 0546 ruling covers, in the ruling's own order of magnitude
# rather than the roster's, so a reader comparing the two reads them as the
# same set and not as a second list.
EXPECTED_RULING_TEMPLATES = frozenset({94, 97, 103, 246, 519})
RULING_0546 = (
    "COO-DECISION 2026-09-05T05:46+07:00 "
    "widen-death-scope-bg0004-five-templates"
)

# The AI foreign keys this scene's rows point at, named so a regeneration of
# ``field_mob_ai_tables`` from a narrower union is a failure here with the
# ids in the message rather than an ``ai_row_missing`` in front of a player.
EXPECTED_AI_COMBAT_IDS = frozenset({214, 250, 300, 332})
EXPECTED_AI_WANDER_IDS = frozenset({11, 16})

# The two DROPS_SPECIALLY sets this scene brought, which no earlier scene's
# roster named.  Pinned because the drop door was measured SHUT on them.
FIRST_SPECIALLY_SETS = (2802236, 2802253)

# Measured immediately before field_mob_tables_bg0004.py was added, on the
# same discipline as the bg0003/bg0005/bg0015 cards: never updated to make a
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


class Bg0004ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(
            self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_the_census_that_does_not_agree(
            self) -> None:
        """The first scene whose four readings split, pinned one by one.

        Scene 3's card can compare three of the four to one constant because
        they agree; this one cannot, and writing them as separate numbers is
        the difference between "the predicates agree here" and "seven of the
        nine combat-AI rows have a rank".
        """
        module = field_mob_tables_bg0004
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        # The project's ONE identity rule (COO-DECISION 2026-08-29T03:45),
        # named here rather than inherited from the tool's default.
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 4)
        self.assertEqual(
            len(module.HOSTILE_PLACEMENTS), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in module.HOSTILE_PLACEMENTS}),
            EXPECTED_TEMPLATE_COUNT,
        )
        census = module.PREDICATE_CENSUS
        self.assertEqual(census["unambiguous"], EXPECTED_UNAMBIGUOUS)
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(census["rank"], EXPECTED_RANK_CENSUS)
        self.assertEqual(census["drops_normal"], EXPECTED_DROPS_NORMAL)
        self.assertEqual(census["town_target"], 0)
        # THE DISAGREEMENT ITSELF, asserted rather than left implicit in two
        # numbers that happen to differ: a re-mine in which ai_combat falls
        # to 7 has changed what this scene IS, and the reading recorded in
        # ``field_mobs.BG0004_SCENE`` would silently stop describing it.
        self.assertEqual(census["ai_combat"], EXPECTED_AI_COMBAT_CENSUS)
        self.assertGreater(census["ai_combat"], census["rank"])
        # Nothing under the retired set-number reading, nothing off the
        # town-target allowlist.
        self.assertEqual(module.TOWN_TARGET_PLACEMENTS, [])
        self.assertEqual(module.LEGACY_SETNUM_PLACEMENTS_PENDING_MIGRATION, [])

    def test_the_two_rank_zero_combat_rows_are_named_and_not_shipped(
            self) -> None:
        """Who the two extra ai_combat rows are, and that they stay out.

        640 wears a PLAYER model (``P_FEMALE_003_000_ARENAFIGHTER``), which
        the three-step methodology every scene before this one used refuses
        by name; both are rank 0 with no drop table at level 105, more than
        twice this scene's own 47-58.  This lane is not deciding WHAT they
        are -- that is a content question -- only that a monster with no
        ruling and no drop table is not a monster it ships.
        """
        self.assertEqual(
            tuple(tuple(row) for row in
                  field_mob_tables_bg0004.COMBAT_AI_AT_RANK_ZERO),
            EXPECTED_RANK_ZERO_COMBAT,
        )
        shipped = {row[1] for row in field_mob_tables_bg0004.SHIPPED_PLACEMENTS}
        for _placement, template, name, _ai in EXPECTED_RANK_ZERO_COMBAT:
            with self.subTest(template=template, name=name):
                self.assertNotIn(template, shipped)
                self.assertNotIn(template, EXPECTED_RULING_TEMPLATES)

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
        # under another scene's name is the hazard the scene field exists
        # for, and this scene is the one where it would bite (template 103
        # is in Bg0002's own ruling set).
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """``ai_row_missing`` here is a refusal in front of a player.

        Reproduced before the union was widened rather than predicted from
        it: with this roster registered and
        ``tools/pf_mine_mob_ai_rows.py`` unwidened, this call raised
        ``MobAiControlError: ai_row_missing: placement 30 points at
        AI_COMBAT 300``.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        register = mob_ai_control.open_register(rows)
        self.assertIsNotNone(register)

    def test_the_ai_ids_this_scene_depends_on_are_named_not_just_resolved(
            self) -> None:
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            {mob.ai_combat for mob in rows}, EXPECTED_AI_COMBAT_IDS)
        self.assertEqual(
            {mob.ai_wander for mob in rows}, EXPECTED_AI_WANDER_IDS)

    def test_registering_scene_four_left_the_other_five_scenes_alone(
            self) -> None:
        """A sixth scene must not move the five already on the wire."""
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(3)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(5)), 6)
        # Written as the live count minus the withheld list rather than as a
        # bare 11, so this line keeps meaning "nothing else moved" if
        # COO-DECISION 20260905_0545's withhold of Carlos is ever lifted.
        self.assertEqual(
            len(field_mobs.roster_for_scene_id(14)),
            12 - len(field_mobs.lane_withheld_placements("Bg0015")))
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         BG0001_UNTOUCHED_SHA256)
        self.assertEqual(len(raw), BG0001_UNTOUCHED_SIZE)

    def test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk(
            self) -> None:
        """The control measured ON the scene being mined.

        Lane A resolved this scene's CLINE type 4 block with its own miner
        for its own arrival census (``world_bg0004_identity.IDENTITIES``);
        this lane's generator resolved it again for the combat roster.  Two
        lanes, two tools, one answer per row -- or this names the row that
        disagrees.  The failure it exists to catch is GT-078's: a map
        wearing another map's names.
        """
        sets = field_mob_tables_bg0004.SET_NUMBER_FOR_PLACEMENT
        theirs_by_placement = {
            placement.placement_index: placement
            for placement in world_bg0004_identity.shippable_placements()
        }
        disagreements = []
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            set_number = sets[mob.placement_index]
            theirs = world_bg0004_identity.IDENTITIES.get(set_number)
            if theirs is None:
                disagreements.append(
                    "placement %d (Mob-Set %d) resolves to %d here and is "
                    "UNRESOLVED in lane A's table"
                    % (mob.placement_index, set_number, mob.template_id))
                continue
            placement = theirs_by_placement.get(mob.placement_index)
            if placement is None:
                disagreements.append(
                    "placement %d is shipped here and is not a shippable "
                    "placement in lane A's table at all"
                    % (mob.placement_index,))
                continue
            mine_row = (
                mob.template_id, mob.display_name, mob.visual_preset,
                mob.level, mob.rank, mob.max_hp, mob.x, mob.y, mob.z,
            )
            their_row = (
                theirs.mobs_n_id, theirs.name, theirs.outfit,
                theirs.level, theirs.rank, theirs.max_hp,
                placement.x, placement.y, placement.z,
            )
            if mine_row != their_row:
                disagreements.append(
                    "placement %d (Mob-Set %d): lane B says %r, lane A says "
                    "%r" % (mob.placement_index, set_number, mine_row,
                            their_row))
        self.assertEqual(
            disagreements, [],
            "the two independently mined readings of CLINE type 4 disagree; "
            "GT-078 is what shipping the wrong one costs, so stop and find "
            "out which miner is wrong before regenerating either table",
        )


class Bg0004DeathRulingTests(unittest.TestCase):
    """The 0546 letter, from both sides of its scene tie."""

    def test_every_scene_four_row_is_covered_by_the_0546_letter_and_no_other(
            self) -> None:
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        for mob in rows:
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertEqual(
                    mob_death.rulings_covering(mob), (RULING_0546,))
                self.assertEqual(mob_death.ruling_for(mob), RULING_0546)
        # The ruling's set is the roster's distinct templates and nothing
        # else -- re-derived here rather than hand-copied a second time.
        self.assertEqual(
            {mob.template_id for mob in rows}, EXPECTED_RULING_TEMPLATES)
        self.assertEqual(
            mob_death.WIDENING_RULINGS[RULING_0546], EXPECTED_RULING_TEMPLATES)

    def test_the_0546_letter_does_not_reach_any_other_scene(self) -> None:
        """Measured from the tie's own side, on the scene where it bites.

        Template 103 ("Orc Chief") is in Bg0002's ruling set too -- the
        first overlap between two rulings in this dict since the pair the
        scene axis was built for.  Without the tie, this scene's letter
        would kill Prison Exile's Fighting Fish soldiers and Prison Exile's
        letter would kill the Slave Market's Orc Chief.
        """
        for scene_id in (1, 2, 3, 5, 14):
            for mob in field_mobs.roster_for_scene_id(scene_id):
                with self.subTest(scene=scene_id,
                                  identity=hex(mob.actor_identity)):
                    self.assertNotIn(
                        RULING_0546, mob_death.rulings_covering(mob))
        # And the reverse direction, which is the half a one-sided check
        # misses: Bg0002's letter covers template 103 and must not reach
        # THIS scene's Orc Chief.
        orc = [mob for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
               if mob.template_id == 103]
        self.assertEqual(len(orc), 1)
        bg0002_letters = [
            name for name, templates in mob_death.WIDENING_RULINGS.items()
            if 103 in templates and name != RULING_0546
        ]
        self.assertTrue(bg0002_letters)
        for name in bg0002_letters:
            with self.subTest(letter=name):
                self.assertNotIn(name, mob_death.rulings_covering(orc[0]))


class Bg0004CollisionWalkTests(unittest.TestCase):
    """The walk ``tests/test_field_mobs.py``'s collision card demands
    whenever a new pair appears -- four appeared this round, one of them
    turning 0x2046 into the first THREE-way collision this lane ships.
    Measured, not read.
    """

    def test_a_scene_three_ledger_covering_two_of_seven_is_still_refused(
            self) -> None:
        """The widest partial overlap this project has had.

        Scene 3's ledger really does answer for TWO of this scene's seven
        identities (0x202B and 0x2046 are both scenes' placements 42 and
        69).  A coverage-counting admission with no scene term is exactly
        what a two-of-seven foreign ledger would slip through.  It does not:
        ``other_scene``, ``admitted`` False, and the ledger handed back is
        ``None`` -- never scene 3's balances.
        """
        roster_four = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        foreign = mob_combat.open_ledger(field_mobs.roster_for_scene_id(3))
        record = mob_ledger_admission.admit_ledger(
            EXPECTED_SCENE_ID, foreign, roster=roster_four)
        self.assertEqual(record["scene"], EXPECTED_SCENE)
        self.assertEqual(record["ledger_scene"], "Bg0003")
        self.assertEqual(record["roster_count"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(record["covered_count"], 2)
        self.assertEqual(record["state"], "other_scene")
        self.assertFalse(record["admitted"])
        self.assertIsNone(record["ledger"])
        # Scene 5's and scene 14's ledgers each cover one, and are refused
        # the same way -- so the refusal is about the scene tag and not
        # about the size of the overlap.
        for other_scene_id, covered in ((5, 1), (14, 1)):
            with self.subTest(ledger_of=other_scene_id):
                other = mob_ledger_admission.admit_ledger(
                    EXPECTED_SCENE_ID,
                    mob_combat.open_ledger(
                        field_mobs.roster_for_scene_id(other_scene_id)),
                    roster=roster_four)
                self.assertEqual(other["covered_count"], covered)
                self.assertEqual(other["state"], "other_scene")
                self.assertFalse(other["admitted"])
        # This scene's OWN ledger is admitted, all seven.
        own = mob_combat.open_ledger(roster_four)
        self.assertEqual(own.scene, EXPECTED_SCENE)
        self.assertIs(
            mob_ledger_admission.ledger_for_scene(
                EXPECTED_SCENE_ID, own, roster=roster_four),
            own,
        )

    def test_0x2046_is_three_different_monsters_in_three_scenes(self) -> None:
        """A collision is a coincidence of index, never of monster."""
        by_scene = {
            scene_id: {
                mob.actor_identity: mob
                for mob in field_mobs.roster_for_scene_id(scene_id)
            }
            for scene_id in (3, 4, 5)
        }
        rows = [by_scene[scene_id][0x2046] for scene_id in (3, 4, 5)]
        self.assertEqual([mob.template_id for mob in rows], [907, 103, 150])
        self.assertEqual(len({mob.display_name for mob in rows}), 3)
        self.assertEqual(len({mob.scene for mob in rows}), 3)

    def test_the_other_three_new_collisions_are_different_monsters(
            self) -> None:
        others = {
            3: {mob.placement_index: mob
                for mob in field_mobs.roster_for_scene_id(3)},
            5: {mob.placement_index: mob
                for mob in field_mobs.roster_for_scene_id(5)},
            14: {mob.placement_index: mob
                 for mob in field_mobs.roster_for_scene_id(14)},
        }
        mine = {mob.placement_index: mob
                for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)}
        for placement, other_scene_id in ((31, 14), (42, 3), (69, 5)):
            ours = mine[placement]
            theirs = others[other_scene_id][placement]
            with self.subTest(placement=placement):
                self.assertEqual(ours.actor_identity, theirs.actor_identity)
                self.assertNotEqual(ours.template_id, theirs.template_id)
                self.assertNotEqual(ours.display_name, theirs.display_name)
                self.assertNotEqual(ours.scene, theirs.scene)

    def test_the_announcement_is_scene_scoped_at_the_membership_itself(
            self) -> None:
        """The strike leg of the walk, on the roster a real arrival sends.

        Driven through lane A's own composer helper and the real membership
        builder, so this is the identity list an arrival in scene 4 would
        actually announce -- not a re-derivation of the roster under another
        name.
        """
        identities, note = lane_a_scene_census._field_mob_identities(
            EXPECTED_SCENE_ID)
        roster = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            tuple(sorted(identities)),
            tuple(sorted(mob.actor_identity for mob in roster)),
        )
        self.assertEqual(len(identities), EXPECTED_HOSTILE_COUNT)
        self.assertIsNone(note)
        membership = mob_combat_membership.build_membership(
            EXPECTED_SCENE_ID, identities, 1)
        for mob in roster:
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertTrue(mob_combat_membership.admits(
                    membership, scene_id=EXPECTED_SCENE_ID,
                    actor_identity=mob.actor_identity, generation=1))
        # An identity this scene does not ship is refused, so the
        # announcement is a roster and not an open door.
        self.assertFalse(mob_combat_membership.admits(
            membership, scene_id=EXPECTED_SCENE_ID,
            actor_identity=0x2099, generation=1))
        # And the three-way collision is harmless here for the same reason
        # it is harmless in scene 3's card: the membership carries the scene.
        for other_scene_id in (3, 5):
            with self.subTest(scene=other_scene_id):
                self.assertFalse(mob_combat_membership.admits(
                    membership, scene_id=other_scene_id,
                    actor_identity=0x2046, generation=1))


class Bg0004LootTests(unittest.TestCase):
    """The door this scene found shut and this round opened."""

    def test_the_two_specially_sets_this_scene_brought_are_mined(
            self) -> None:
        """Measured shut first: four rows refused ``unknown_drop_set``.

        Templates 94 and 97 are the first shipped rows in this project to
        name an ``n_DROPS_SPECIALLY`` set -- the THIRD drop column, which no
        earlier scene's roster exercised at all.  Before
        ``tools/pf_mine_scene_drop_tables.py`` was widened to this scene,
        ``scene_door_walk`` reported ``drop=3`` for these seven rows with
        placements 30/31/32/42 refusing by that name.
        """
        self.assertIn(
            EXPECTED_SCENE.lower(),
            {scene.lower() for scene in field_drop_tables.SCENES},
        )
        for set_id in FIRST_SPECIALLY_SETS:
            with self.subTest(set_id=set_id):
                self.assertIn(set_id, field_drop_tables.DROPS_SPECIALLY)
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            {mob.drops_specially for mob in rows if mob.drops_specially},
            set(FIRST_SPECIALLY_SETS),
        )

    def test_every_row_rolls_something_placeable_and_none_refuses(
            self) -> None:
        """A roll that drops nothing is not a bug, so seeds are searched.

        Same shape ``tests/test_mob_drop_presence.py``'s ``PresenceTestBase``
        uses and for the same reason: a hard-coded seed that happens to roll
        nothing is a test that goes red the day a drop table is edited, not
        a proof.
        """
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            rolled = False
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                self.assertNotIn("unknown_drop_set", roll.refusals)
                if roll.items:
                    rolled = True
                    break
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertTrue(
                    rolled,
                    "placement %d rolled nothing placeable in 60 seeds -- "
                    "either the table mining regressed or the odds need a "
                    "wider search, and either way this is worth failing "
                    "loudly on" % mob.placement_index)
        # The scene key a drop is filed under is this scene's own, so the
        # three-way collision cannot put a scene-4 drop in scene 3's or
        # scene 5's list.
        self.assertNotEqual(
            mob_loot.scene_key(EXPECTED_SCENE), mob_loot.scene_key("Bg0003"))
        self.assertNotEqual(
            mob_loot.scene_key(EXPECTED_SCENE), mob_loot.scene_key("bg0005"))


class Bg0004RecomposeRegistrationTests(unittest.TestCase):
    """The composer half, which lands in the same commit as the roster."""

    def test_scene_four_is_no_longer_acknowledged_without_a_composer(
            self) -> None:
        self.assertNotIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER)
        self.assertIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.composer_scene_ids())

    def test_the_new_composer_kind_is_non_delegated_and_has_a_builder(
            self) -> None:
        self.assertIn(
            mob_scene_recompose.COMPOSER_BG0004,
            mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS,
        )
        # The tuple-and-table pair round jqeo2m named once so a new scene
        # cannot be added to one and left out of the other.
        mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder()


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0004RegenerateTests(unittest.TestCase):
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
            "src/pirateforce_foundation/field_mob_tables_bg0004.py is stale "
            "- regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene bg0004 --identity-rule cline --out "
            "<this file>",
        )


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
