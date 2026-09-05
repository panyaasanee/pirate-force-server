"""LANE-B: scene 3 (Bg0003) is a REGISTERED combat scene -- and still not
a scene anybody can fight in.

ROUND am1fw8.  Same shape as scene 5's card (round jqeo2m) and registered in
the same commit that mines it, for the same reason: lane A opened scene 3's
arrival census AND its ``login_entry_allowed`` door rounds ago, so a player
can stand in this map today; what they could not do until this commit is
swing at anything in it, because ``field_mobs.scene_for_scene_id(3)``
returned ``None``.

WHAT A PLAYER SEES, AND WHAT THEY STILL DO NOT.  Twelve monsters in scene 3
become TARGETABLE with this commit, and that is not a claim about a roster
existing -- it is a consequence of chief's round `9vec2s` (PR #734), which
landed while this round was running and answered CORE-REQUEST
``20260904_1134``: a lane-composed arrival now announces
``SceneCensusResult.actor_identities``, and lane A fills that field from
``field_mobs.roster_for_scene_id``, the reader this commit changes the answer
of.  ``Bg0003IsTargetableButNotKillableTests`` measures it end to end
through lane A's own composer helper and the real membership builder.

WHAT IS STILL SHUT, measured here rather than left to a PR body nobody
re-reads:

* ~~``test_no_scene_three_row_has_a_death_ruling_yet_and_that_refuses`` -- no
  COO letter sanctions killing anything in this scene, so all twelve refuse
  with ``target_outside_the_sanctioned_scope``.  A player can now swing and
  see nothing die.  The letter asking for the ruling goes out this round.~~
  STRUCK, round 59iqwi: the letter went out (``notes_to_chief/20260904_1432``)
  and ``COO-DECISION 2026-09-04T14:50+07:00`` answered it, approving the seven
  templates behind all twelve placements.  What replaces it is
  ``test_every_scene_three_row_is_covered_by_the_1450_letter_and_no_other``,
  which measures the same two things from the other side: every real row
  names THAT letter, and no row reaches a ruling written for another scene.
* ~~``test_loot_is_the_third_shut_door_and_it_refuses_by_name`` -- scene 3's
  ``DROPS_NORMAL`` set 2701002 was never mined into ``field_drop_tables``,
  so even past a ruling, a kill here drops nothing.~~ STRUCK, round (next
  after 59iqwi): the drop-table miner widened to the union of scenes 3, 5
  and 14 (this lane's own reserve item), and scene 3's DROPS_NORMAL set
  2701002 is now mined.  What replaces it is
  ``test_loot_is_no_longer_the_third_shut_door``, proving a kill here rolls
  real items instead of refusing ``unknown_drop_set``.

THE COLLISION MEASUREMENT.  Scene 3's twelve placements bring FOUR new
cross-scene ``actor_identity`` collisions at once (0x201C and 0x201E against
Bg0015, 0x203B against Bg0002, 0x2046 against bg0005) -- more than doubling
the three this project had.  ``tests/test_field_mobs.py``'s collision card
demands a fresh walk of strike/ledger/rehydration/death/loot whenever one
appears; the walk was redone this round and MEASURED here rather than
inherited -- death in ``Bg0003CannotBeKilledYetTests`` (scene 5's kill
permission refusing scene 3's identical 0x2046), ledger and loot in
``Bg0003CollisionWalkTests`` (a foreign ledger that really does cover one of
the twelve is still refused; a scene-3 kill cannot reach the loot leg at
all).  The strike leg is the one the open seam makes reachable, and it is
scene-scoped at the membership itself: the same membership refuses 0x2046
under scene 5's id, measured in
``test_the_lane_composed_arrival_now_announces_all_twelve``.
"""

from __future__ import annotations

import dataclasses
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
from pirateforce_foundation import field_drop_tables  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_ledger_admission  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation.lane_hooks import lane_a_scene_census  # noqa: E402
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
# ROUND hor2lh: re-pinned, and by a change that touched ALL SIX generated
# tables on purpose -- pf-adversary D14 of round r6isy5b found the
# generator stamping every scene with a control sentence that is true only
# for bg0001, so the corrected comment was regenerated into each module.
# Only the comment block moved; every row, digest and census value in
# bg0001 is byte-identical (verified by regenerating and diffing).  The
# previous digest is kept, not deleted:
# ~~574fdca1391eb0aa4bc4a5a2b46b50c090839a86baf94426573312afff2866a5~~
BG0001_UNTOUCHED_SHA256 = (
    "c1a341c9d7721db45b07e2e7df2840719da5fcbcf5521d7f31eabd4a1ce26934"
)
# ROUND hor2lh: ~~9708~~ -> 12316, the comment correction described
# above.  This constant still means "this round did not touch that
# file"; it is re-pinned when a round changes bg0001 on purpose.
BG0001_UNTOUCHED_SIZE = 12316


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
        # ~~12~~ -> 11 for scene 14, round j5v7mu: COO-DECISION
        # 20260905_0545 withheld placement 87 (Carlos) from what this lane
        # ships.  Asserted as a live count minus the withheld list rather
        # than as a bare 11, so this line keeps meaning "nothing else
        # moved" if the ruling is lifted.
        self.assertEqual(
            len(field_mobs.roster_for_scene_id(14)),
            12 - len(field_mobs.lane_withheld_placements("Bg0015")))
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 11)
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
        theirs_by_placement = {
            placement.placement_index: placement
            for placement in world_bg0003_identity.shippable_placements()
        }
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
            placement = theirs_by_placement.get(mob.placement_index)
            if placement is None:
                disagreements.append(
                    "placement %d is shipped here and is not a shippable "
                    "placement in lane A's table at all"
                    % (mob.placement_index,))
                continue
            # EVERY COLUMN BOTH TABLES CARRY, not just the identity pair.
            # ROUND am1fw8, closing what pf-adversary measured this round:
            # with only (n_id, name) compared, mutating ``max_hp`` or an
            # ``x`` in the generated module SURVIVED the whole suite,
            # because the one check that would catch it -- the byte-for-byte
            # regeneration -- needs the bridge clone and is SKIPPED on the
            # gate.  Both values reach a player (``mob_death`` writes
            # ``max_hp`` into the actor entry and ``x``/``y``/``z`` into the
            # recompose frame), so they are compared here, where no bridge
            # is needed.  ``speed_walk`` and the three drop-set columns are
            # NOT compared: lane A's table does not carry them, so this
            # round leaves them named as bridge-only rather than pretending
            # a second source exists.
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
            "the two independently mined readings of CLINE type 3 disagree; "
            "GT-078 is what shipping the wrong one costs, so stop and find "
            "out which miner is wrong before regenerating either table",
        )


class Bg0003CannotBeKilledYetTests(unittest.TestCase):
    """~~No COO letter sanctions a death in this scene~~ -- ONE DOES NOW.

    STRUCK AND REPLACED, round 59iqwi, `COO-DECISION 2026-09-04T14:50+07:00`
    item 2, which asked for this flip in the same round the ruling is
    registered and asked for it to be checked against THE ROWS THAT SHIP
    rather than against a hand-typed list.  The class name is kept so a
    reader who greps the old name lands on why it moved.
    """

    def test_every_scene_three_row_is_covered_by_the_1450_letter_and_no_other(
            self) -> None:
        """All twelve, by the letter's own name, re-derived from the roster.

        Both halves matter.  That every row is covered is what makes a swing
        in scene 3 able to kill; that the covering ruling is THIS letter is
        what stops scene 5's letter (or bg0001's, or Bg0015's) reaching a
        scene it never mentioned -- the 0x2046 collision two tests below is
        the measured case where that is not hypothetical.
        """
        rows = tuple(field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID))
        self.assertEqual(len(rows), EXPECTED_HOSTILE_COUNT)
        for mob in rows:
            ruling = mob_death.ruling_for(mob)
            self.assertIn("widen-death-scope-bg0003-seven-templates", ruling,
                          mob.display_name)
            self.assertIn("2026-09-04T14:50+07:00", ruling, mob.display_name)
        # The seven the letter names, and no eighth: re-derived from the
        # rows that ship, so a placement added to this scene tomorrow shows
        # up here as an uncovered row rather than as a silent kill.
        self.assertEqual(
            {mob.template_id for mob in rows},
            {60, 61, 62, 65, 194, 515, 907})

    def test_a_scene_three_template_id_in_another_scene_is_still_refused(
            self) -> None:
        """The ruling is tied to Bg0003, measured from the tie's own side.

        Template 907 is covered by the 1450 letter, and the SAME template id
        carried by a row of any other scene must still refuse: the letter
        approves seven templates IN ONE SCENE, and a ruling that had been
        registered without its `WIDENING_RULING_SCENES` entry would pass this
        row through with nothing raised anywhere.
        """
        three = {
            mob.placement_index: mob
            for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        }[58]
        self.assertEqual(three.template_id, 907)
        elsewhere = dataclasses.replace(three, scene="Bg0002")
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(elsewhere)
        self.assertIn("target_outside_the_sanctioned_scope",
                      str(caught.exception))

    def test_scene_fives_kill_permission_does_not_reach_scene_threes_0x2046(
            self) -> None:
        """The collision walk's measurement half, on REAL rows of both
        scenes rather than a hand-built pair.

        Placement 69 exists in both scenes, so both monsters compute the
        same wire ``actor_identity`` 0x2046 -- and scene 5's placement 69
        (``Ned apes``, template 150) is covered by ``COO-DECISION
        2026-09-04T11:48+07:00`` while scene 3's (``Sediment Wolf``,
        template 907) is covered by ~~nothing~~ ``COO-DECISION
        2026-09-04T14:50+07:00``, round 59iqwi.  The test gets HARDER rather
        than weaker for it: while scene 3 could not be killed at all, a
        ruling keyed by something the two share would have shown up as a kill
        where none was allowed.  Now both sides are allowed and what has to
        hold is that each carries its OWN letter -- a mix-up that a refusal
        can no longer catch, and that this assertion can.
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
        # Each side really is sanctioned -- otherwise this test would pass
        # just as well on a project where nothing can die.
        five_ruling = mob_death.ruling_for(five)
        three_ruling = mob_death.ruling_for(three)
        self.assertIn("widen-death-scope-bg0005", five_ruling)
        self.assertIn("widen-death-scope-bg0003", three_ruling)
        # And neither letter reaches the other's monster: the identity they
        # share is not what either ruling is keyed by.
        self.assertNotIn("bg0003", five_ruling)
        self.assertNotIn("bg0005", three_ruling)

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


class Bg0003CollisionWalkTests(unittest.TestCase):
    """The rest of the walk ``tests/test_field_mobs.py``'s collision card
    demands whenever a new pair appears -- ledger and loot, measured here
    rather than read.  (Death is the class above; the strike leg cannot be
    reached at all while the membership seam is shut, which is its own
    measurement and is in ``Bg0003NotFightableYetTests``.)
    """

    def test_a_scene_five_ledger_is_refused_for_scene_three_despite_0x2046(
            self) -> None:
        """The collision buys ONE covered identity, and that is not enough.

        This is the sharpest thing the four new pairs made testable: scene
        5's ledger really does answer for one of scene 3's twelve
        identities, because 0x2046 is both scenes' placement 69.  If
        admission were coverage-counting without a scene term, a partially
        covering foreign ledger is exactly the shape that would slip
        through.  It does not: the record says ``other_scene``, coverage
        1/12, ``admitted`` False, and the ledger handed back is ``None``
        (compose without consulting HP), never scene 5's balances.
        """
        roster_three = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        foreign = mob_combat.open_ledger(field_mobs.roster_for_scene_id(5))
        record = mob_ledger_admission.admit_ledger(
            EXPECTED_SCENE_ID, foreign, roster=roster_three)
        self.assertEqual(record["scene"], EXPECTED_SCENE)
        self.assertEqual(record["ledger_scene"], "bg0005")
        self.assertEqual(record["roster_count"], EXPECTED_HOSTILE_COUNT)
        self.assertEqual(record["covered_count"], 1)
        self.assertIn(0x2046, {mob.actor_identity for mob in roster_three})
        self.assertEqual(record["state"], "other_scene")
        self.assertFalse(record["admitted"])
        self.assertIsNone(record["ledger"])
        # And this scene's OWN ledger is admitted, so the refusal above is
        # about the scene tag and not about scene 3 being unusable.
        own = mob_combat.open_ledger(roster_three)
        self.assertEqual(own.scene, EXPECTED_SCENE)
        self.assertIs(
            mob_ledger_admission.ledger_for_scene(
                EXPECTED_SCENE_ID, own, roster=roster_three),
            own,
        )

    def test_loot_is_no_longer_the_third_shut_door(self) -> None:
        """~~test_loot_is_the_third_shut_door_and_it_refuses_by_name~~ STRUCK.

        Scene 3's drop sets were never mined; that was true when this test
        was named for it and it is FALSE now, MEASURED rather than assumed:
        round (next after 59iqwi) widened ``tools/pf_mine_scene_drop_tables.
        py`` to the union of every scene this lane ships a roster for, which
        includes Bg0003 (this scene), Bg0005 and Bg0015, answering exactly
        the reserve item this lane's own round file named ("drop of scene
        3/5/14 ... DROPS_NORMAL 2701002 never dug into field_drop_tables").
        This is the flip side of that struck test: every scene-3 row's
        ``DROPS_NORMAL`` set (2701002) is now IN ``field_drop_tables``, so a
        kill here no longer refuses with ``unknown_drop_set`` before a key
        is issued -- the loot leg of the collision walk is reachable now.
        The collision walk itself (a scene-3 drop cannot land in scene 5's
        cell) is still true and still asserted below, by the same scene-key
        argument the struck test made -- it no longer needs an unreachable
        door to be true, because ``DropLedgerCell`` scopes by scene key on
        its own.
        """
        import random

        self.assertIn(
            EXPECTED_SCENE.lower(),
            {scene.lower() for scene in field_drop_tables.SCENES},
        )
        # A roll that drops nothing is not a bug (mob_drop_presence's own
        # fixtures note it is roughly one kill in three), so this searches
        # seeds rather than trusting a single one -- the same shape
        # tests/test_mob_drop_presence.py's PresenceTestBase uses, for the
        # same reason: a hard-coded seed that happens to roll nothing is a
        # test that goes red the day a drop table is edited, not a proof.
        rolled_any_item = False
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                self.assertNotIn("unknown_drop_set", roll.refusals)
                if roll.items:
                    rolled_any_item = True
                    break
        self.assertTrue(
            rolled_any_item,
            "twelve scene-3 mobs, 60 seeds each, rolled nothing placeable "
            "at all -- either the table mining regressed or the odds need "
            "a wider search, and either way this is worth failing loudly on")
        # The scene key a drop is filed under is this scene's own, so the
        # collision cannot put a scene-3 drop in scene 5's list even though
        # both scenes' loot is now reachable.
        self.assertNotEqual(
            mob_loot.scene_key(EXPECTED_SCENE), mob_loot.scene_key("bg0005"))


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


class Bg0003IsTargetableButNotKillableTests(unittest.TestCase):
    """~~Bg0003NotFightableYetTests: the two shut doors between this roster
    and a player hitting it.~~

    REWRITTEN MID-ROUND am1fw8, on a measurement, because one of the two
    doors opened while this round was running.  Chief's round `9vec2s`
    (PR #734) answered CORE-REQUEST ``20260904_1134``: the lane-composed
    arrival branch in ``runtime.py`` no longer stamps an empty announced
    membership -- it reads ``SceneCensusResult.actor_identities``, which
    ``lane_a_scene_census`` fills from ``field_mobs.roster_for_scene_id``.
    That reader is scene-agnostic, so registering scene 3's roster in this
    commit is also what makes scene 3's twelve monsters ANNOUNCED, and the
    RE-157 gate that refuses unannounced targets now admits every one of
    them.

    The card is kept and re-pointed rather than deleted: what it exists to
    hold is the honest distance between "a roster exists" and "a player can
    fight here", and that distance is still real -- it is now ONE door, not
    two.  Nothing in scene 3 can die (no COO letter sanctions it) and
    nothing can drop (its drop sets are unmined), both measured above.
    """

    def test_the_lane_composed_arrival_now_announces_all_twelve(
            self) -> None:
        """The whole reason this round changes anything for a player.

        Driven through lane A's own composer helper and the real membership
        builder, so this is the identity list an arrival in scene 3 would
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
        # An identity this scene does not ship is still refused, so the
        # announcement is a roster and not an open door.
        self.assertFalse(mob_combat_membership.admits(
            membership, scene_id=EXPECTED_SCENE_ID,
            actor_identity=0x2099, generation=1))
        # And the announcement is scene-scoped: the same membership does not
        # admit its own identities under another scene's id, which is what
        # keeps the four new cross-scene collisions harmless here too.
        self.assertFalse(mob_combat_membership.admits(
            membership, scene_id=5,
            actor_identity=0x2046, generation=1))

    def test_the_runtime_branch_still_says_it_announces_a_real_roster(
            self) -> None:
        """Scene 3's own file fails if that call site reverts.

        The same sentence scene 5's card pins, re-asserted here: the seam
        this scene's monsters became targetable through is one call site,
        and a revert of it would silently make all twelve unhittable again.
        """
        raw = (SRC / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8")
        runtime_src = " ".join(raw.replace("#", " ").split())
        self.assertIn(
            "SO A LANE-COMPOSED ARRIVAL CAN NOW ANNOUNCE A REAL ROSTER",
            runtime_src,
            "the lane-composed arrival branch no longer says it announces "
            "a real roster.  If it reverted to an empty membership, scene "
            "3's twelve monsters are unhittable again and this round's "
            "only player-visible change is gone",
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
