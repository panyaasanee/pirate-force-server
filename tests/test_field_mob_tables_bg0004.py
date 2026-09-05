"""LANE-B: scene 4 (bg0004, Slave Market Island) is a REGISTERED combat
scene, and the FIRST this lane has armed through all three doors in the round
that mined it.

ROUND r6isy5, on COO-DECISION 2026-09-05T05:46+07:00 ("roster of scene 4 +
the kill letter of scene 4, in the shape of scenes 3/5"), which is also the
letter that closed 1450 item 3 and put this scene back in the queue.

WHAT THIS COMMIT CHANGES.  ~~Seven monsters in the Slave Market appear as
red-named, clickable, killable targets that drop loot on the ground.~~
STRUCK IN THE SAME ROUND, pf-adversary D5, and it is worth saying why
rather than just softening it: every clause of that sentence was a
CLIENT-OBSERVABLE claim, and this project has already MEASURED two of them
negative.

* "red-named" -- ``pf_bridge/NOW.md`` P-2 records R306 on screen: monster
  names render PINK, still wrong.  Worse, ``RE-222`` SHA-pins that the "in
  combat" and "dead" name styles are reachable only for actors the client
  builds as ``CNetNPC``, and monsters delivered through the ``field_mobs``
  census (``0x2000 + placement + 1``) are a different kind -- so that style
  is not merely unwatched here, it is what RE-222 says this delivery path
  cannot reach.  And under P-2's own spec red means IN COMBAT; an idle
  monster would be orange anyway.
* "drop loot on the ground" -- ``scene_door_walk``'s own NONCLAIM says the
  drop door places rows and composes nothing, and GT-045 measured a name
  label, brown dust and no model.

WHAT IS TRUE, at the layer this file actually measures: seven monsters in
scene 4 are ANNOUNCED to a client, are admitted by the targeting gate, take
damage through ``mob_combat.strike``, die through ``mob_death.kill`` under a
letter, and their kills place loot rows through ``mob_loot``.  Lane A opened
this map's arrival census AND its ``login_entry_allowed`` door back in round
bq4mst -- scene 4 was the FIRST of the ten doors that opened -- so a player
has been able to stand here for days with nothing in the map to swing at,
because ``field_mobs.scene_for_scene_id(4)`` returned ``None``.  NOW.md
still forbids an on-screen monster-hit GT for scenes 3/4/5/14 until P-2
closes, so nobody has WATCHED any of it, and a struck sentence at the top of
a file is not undone by a disclaimer three paragraphs down -- which is why
the sentence itself is struck rather than annotated.

THE THREE THINGS THAT MAKE THIS SCENE DIFFERENT FROM 3, 5 AND 14, each
measured below rather than asserted in a PR body:

* THE FOUR HOSTILITY PREDICATES DISAGREE: ai_combat 9, rank 7,
  drops_normal 7, rank_and_ai_combat 7.  ~~for the first time in any scene
  this lane ships~~ STRUCK, pf-adversary D3: bg0001 (9/0/0/0) and Bg0015
  (12/12/11/12) already disagree, so this is the THIRD, not the first -- the
  sibling modules' own ``PREDICATE_CENSUS`` was one import away and was not
  opened.  What stands is the obligation: the generator's docstring says a
  scene where they disagree "must be read before its roster is shipped", the
  reading is in ``field_mobs.BG0004_SCENE``, and the two extra rows are
  pinned by name here.
* IT IS THE FIRST SCENE TO CARRY A ``n_DROPS_SPECIALLY`` SET THAT
  ``field_drop_tables`` HAD NEVER MINED.  (Not the first to carry one at
  all -- pf-adversary D4 counted 26 shipped rows across four scenes that
  already name one.)  Templates 94 and 97 name sets 2802253 and 2802236, and
  the drop door was MEASURED shut on them before the miner was widened --
  ``target=7 kill=7 drop=3``, four rows refusing ``drop:unknown_drop_set``.
  Widened, it walks 7/7/7 -- though see
  ``test_the_two_specially_sets_this_scene_brought_are_mined`` for what
  those two sets actually contribute, which is nothing.
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

import dataclasses
import hashlib
import importlib.util
from pathlib import Path
import random
import struct
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
from pirateforce_foundation import field_mob_ai_tables  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0004  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_combat_membership  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_ledger_admission  # noqa: E402
from pirateforce_foundation import mob_loot  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import scene_door_walk  # noqa: E402
from pirateforce_foundation import world_bg0004_identity  # noqa: E402
from pirateforce_foundation import world_population_bg0004  # noqa: E402
from pirateforce_foundation import world_population_bg0005  # noqa: E402
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

# The two DROPS_SPECIALLY sets this scene brought.  ~~which no earlier
# scene's roster named~~ STRUCK, pf-adversary D4: 26 shipped rows across
# Bg0002/Bg0003/Bg0015/bg0005 already name a specially set (2802234, 2802264,
# 2802219, 2802215, 2802208, 2802250, 2802205, 2802214, 2802211, 2802235),
# and origin/main's own REFERENCED_BY table listed six of them.  The true and
# narrow claim is the one this constant is named for: these two are the first
# specially-set ids ``field_drop_tables`` had never MINED, which is why the
# drop door was measured SHUT on the four rows carrying them.
FIRST_SPECIALLY_SETS = (2802236, 2802253)

# pf-adversary D7: the whole shipped table, digested, so no column can move
# on a clone with no bridge beside it (where the byte-for-byte regenerate
# test is skipped by design).  Recompute with:
#   hashlib.sha256(repr(field_mob_tables_bg0004.SHIPPED_PLACEMENTS)
#                  .encode("ascii")).hexdigest()
SHIPPED_ROWS_SHA256 = (
    "5c3dd0b6168af916d41852bfb0ec85bf00c384fd3fe5761936a016aa2d4b6cac"
)
EXPECTED_UNRESOLVED = 51
EXPECTED_WITHDRAWN = 16
#: 65 unambiguous + 51 unresolved, which is every row of
#: gamedata/scene/bg0004/bg0004.placements.tsv.
PLACEMENTS_IN_THE_SCENE_FILE = 116
MOBS_SHA256 = (
    "3c0d33d68f832eefda56c845495008338dcef56f4277584b9ca479b7e1b3916b"
)
EXPECTED_CONTROL_FINDINGS = {
    "prison_exile_identity": "35/35",
    "town_target_916_hp": "198125",
}

# Measured immediately before field_mob_tables_bg0004.py was added, on the
# same discipline as the bg0003/bg0005/bg0015 cards: never updated to make a
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


#: The frozen serializer every door-walking test in this project drives, so
#: a kill here composes the same bytes production would.
V141 = ROOT / "current" / "pf_login_game_server_v141.py"
_LEGACY = None


def _legacy():
    """The project's own loader, not a hand-rolled one.

    ``legacy_bridge.load_legacy`` is what every other card that drives the
    frozen serializer uses; loading v141 under an ad-hoc module name instead
    leaves its classes with a ``__module__`` that is not in ``sys.modules``,
    which breaks ``dataclasses`` on anything that touches them.
    """
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy(V141)
    return _LEGACY


def _outcome_for(mob):
    """A real killing blow on ``mob``, composed by production code.

    Not a hand-built ``HitOutcome``: the point of the tests that use this is
    that a kill would otherwise SUCCEED, so the blow has to be one
    ``mob_death.kill`` would accept if the ruling let it through.
    """
    step = mob_combat.strike(
        _legacy(), None, mob_combat.open_ledger((mob,)), None, mob,
        scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
    return step.outcome


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
        by name; both are rank 0 with no drop table at level 105, ~~more
        than twice this scene's own 47-58~~ (pf-adversary D12: 2 x 58 = 116,
        so that is false for placements 69, 83 and 42) -- far outside this
        scene's own 47-58 band.  This lane is not deciding WHAT they are --
        that is a content question -- only that a monster with no ruling and
        no drop table is not a monster it ships.

        THE 3 IN EACH TUPLE IS THEIR ``n_AI_COMBAT``, and it is NOT one of
        this scene's own combat AI ids (pf-adversary D13, correcting a
        sentence in ``mob_death`` that called it "this scene's combat AI"):
        the shipped rows point at 214/250/300/332, and AI row 3 is not in
        the mined ``field_mob_ai_tables`` union at all.  Asserted below, so
        the two facts cannot drift back together.
        """
        self.assertEqual(
            tuple(tuple(row) for row in
                  field_mob_tables_bg0004.COMBAT_AI_AT_RANK_ZERO),
            EXPECTED_RANK_ZERO_COMBAT,
        )
        shipped = {row[1] for row in field_mob_tables_bg0004.SHIPPED_PLACEMENTS}
        for _placement, template, name, ai_combat in EXPECTED_RANK_ZERO_COMBAT:
            with self.subTest(template=template, name=name):
                self.assertNotIn(template, shipped)
                self.assertNotIn(template, EXPECTED_RULING_TEMPLATES)
                self.assertNotIn(ai_combat, EXPECTED_AI_COMBAT_IDS)

    def test_every_column_of_every_shipped_row_is_pinned_without_a_bridge(
            self) -> None:
        """~~EXPECTED_ROWS' four columns~~ ALL SIXTEEN, pf-adversary D7.

        ``Bg0004RegenerateTests`` re-derives this module byte-for-byte, but
        it needs the bridge clone and ``docs/PYTEST_SKIP_PINS.json`` declares
        it a design skip on a fresh checkout -- which is the configuration
        the Windows gate runs.  In that configuration pf-adversary landed
        EIGHT hand-edits on the generated module and the suite stayed green:
        ``speed_walk`` 100 -> 250, ``drops_equipment`` 5400002 -> 5400003,
        ``drops_normal`` 2701003 -> 2701002, ``drops_specially`` 2802253 ->
        0, a deleted ``UNRESOLVED_PLACEMENTS`` row, a deleted
        ``WITHDRAWN_UNDER_THIS_RULE`` row, an all-zero ``SOURCE_DIGESTS``
        entry, and a corrupted ``CONTROL_FINDINGS`` value.  Two of those
        reach a player directly (``max_hp`` and the drop-set ids), and the
        ``drops_specially`` one slipped past this card's own specially-set
        test because that test is a set comprehension with a truthiness
        filter -- zeroing one of three rows changes nothing it looks at.

        A digest, not a re-typed table: sixteen columns times seven rows is
        a wall nobody re-reads, and the row-by-row identity check is already
        ``EXPECTED_ROWS`` above.  What this adds is that NOTHING in a row can
        move silently.  Regenerate and paste the new digest only after
        reading why it moved.
        """
        digest = hashlib.sha256(
            repr(field_mob_tables_bg0004.SHIPPED_PLACEMENTS).encode("ascii")
        ).hexdigest()
        self.assertEqual(digest, SHIPPED_ROWS_SHA256)
        # The two lists the module's own header arithmetic depends on
        # ("unambiguous + unresolved = the scene's whole placement count"),
        # which a deleted row silently falsifies.
        self.assertEqual(
            len(field_mob_tables_bg0004.UNRESOLVED_PLACEMENTS),
            EXPECTED_UNRESOLVED)
        self.assertEqual(
            len(field_mob_tables_bg0004.WITHDRAWN_UNDER_THIS_RULE),
            EXPECTED_WITHDRAWN)
        self.assertEqual(
            EXPECTED_UNAMBIGUOUS + EXPECTED_UNRESOLVED,
            PLACEMENTS_IN_THE_SCENE_FILE)
        # The provenance the module claims for itself.  A zeroed digest is
        # how a hand-edited "generated" module stops being traceable to the
        # data it claims to come from.
        self.assertEqual(
            field_mob_tables_bg0004.SOURCE_DIGESTS["mobs"], MOBS_SHA256)
        self.assertEqual(
            field_mob_tables_bg0004.CONTROL_FINDINGS, EXPECTED_CONTROL_FINDINGS)

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

    def test_the_letter_is_tied_to_this_scene_in_the_registry_itself(
            self) -> None:
        """~~implied by the loop below~~ ASSERTED DIRECTLY, ROUND r6isy5.

        pf-adversary D1: deleting this scene's entry from
        ``WIDENING_RULING_SCENES`` left the ENTIRE suite green -- 10749
        passed, byte-identical to baseline -- because the loop below walks
        the LIVE rosters of scenes 1/2/3/5/14 and not one live row carries
        a template in {94, 97, 103, 246, 519}.  The loop body was vacuously
        true whether or not the tie existed.  The sibling cards each do one
        of the two things that would have caught it (bg0005 asserts the
        mapping, Bg0003 relabels a row and drives the refusal); this scene
        now does BOTH, because it is the scene with the overlapping
        template and the one where an untied letter costs something.
        """
        self.assertEqual(
            mob_death.WIDENING_RULING_SCENES[RULING_0546], EXPECTED_SCENE)
        # Every registered ruling is tied, not just this one -- an untied
        # entry is the shape that goes green while reaching every scene.
        for name in mob_death.WIDENING_RULINGS:
            with self.subTest(ruling=name):
                self.assertIn(name, mob_death.WIDENING_RULING_SCENES)

    def test_a_scene_four_row_wearing_another_scenes_name_is_refused(
            self) -> None:
        """The tie driven, on the row where the overlap is real.

        pf-adversary D1 drove the deletion mutant to completion: with the
        tie gone, Bg0002 placement 92 (template 103, 0x205D, "Orc Chief")
        is KILLED under the Slave Market letter -- 167 bytes on the wire,
        register says dead.  Those five Bg0002 rows are held out of its
        live roster by the owner's own n_id 101-104 refusal today, so this
        relabels a real bg0004 row instead of resurrecting a refused one:
        same question, no dependency on a refusal staying in place.
        """
        orc = [mob for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
               if mob.template_id == 103]
        self.assertEqual(len(orc), 1)
        self.assertEqual(mob_death.ruling_for(orc[0]), RULING_0546)
        for other_scene in ("Bg0002", "Bg0003", "bg0005", "Bg0015", "bg0001"):
            relabelled = dataclasses.replace(orc[0], scene=other_scene)
            with self.subTest(scene=other_scene):
                self.assertNotIn(
                    RULING_0546, mob_death.rulings_covering(relabelled))
                with self.assertRaises(mob_death.MobDeathContractError) as box:
                    mob_death.kill(
                        _legacy(), relabelled, _outcome_for(relabelled),
                        widened=RULING_0546)
                self.assertIn(
                    "target_outside_the_sanctioned_scope", str(box.exception))

    def test_the_0546_letter_does_not_reach_any_other_scene(self) -> None:
        """Measured from the tie's own side, on the scene where it bites.

        Template 103 ("Orc Chief") is in Bg0002's ruling set too -- the
        first overlap between two rulings in this dict since the pair the
        scene axis was built for.  ~~Without the tie, this scene's letter
        would kill Prison Exile's Fighting Fish soldiers~~ STRUCK, same
        round, pf-adversary D2: the overlap is template 103 ALONE, and 103
        in Bg0002 is the ORC CHIEF at placements 92-96 -- template 34, the
        Fighting Fish soldier, is not in this letter and never was.  The
        sentence named a monster nobody looked up.

        THIS TEST ALONE CANNOT CATCH AN UNTIED LETTER (D1): no live row of
        any other scene carries one of these five templates, so the loop is
        vacuously true.  It is kept for what it does measure -- that the
        five ids do not silently spread as rosters grow -- and the tie
        itself is driven in the two tests above.
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

        ~~Templates 94 and 97 are the first shipped rows in this project to
        name an ``n_DROPS_SPECIALLY`` set -- the THIRD drop column, which no
        earlier scene's roster exercised at all.~~  STRUCK, pf-adversary D4:
        26 shipped rows across Bg0002, Bg0003, Bg0015 and bg0005 already
        name a specially set, and ``field_drop_tables``' own ``REFERENCED_BY``
        table listed six of those ids on origin/main.  The true claim is the
        narrow one: these are the first specially-set ids the DROP TABLE had
        never mined, which is what shut the door.  Before
        ``tools/pf_mine_scene_drop_tables.py`` was widened to this scene,
        ``scene_door_walk`` reported ``drop=3`` for these seven rows with
        placements 30/31/32/42 refusing by that name.

        AND WHAT THE TWO SETS CONTRIBUTE IS NOTHING, asserted below rather
        than left for a reader to infer from ``drop=7`` (pf-adversary D9,
        who rolled all seven rows over 5000 seeds each and never saw either
        item).  Both rows carry a leading percent of 0.0, so items 2414053
        ("Craig Firebird") and 2414036 ("Forest Green Eagle") can never be
        placed.  The widening's real and only effect was to stop the
        ``unknown_drop_set`` refusal; the seven-of-seven drop verdict is
        produced entirely by ``drops_normal``/``drops_equipment``, the same
        two columns every earlier scene used.  A reader who takes
        ``every_door=yes`` to mean "the third column now pays out" has been
        told something untrue, so this test says it out loud.
        """
        self.assertIn(
            EXPECTED_SCENE.lower(),
            {scene.lower() for scene in field_drop_tables.SCENES},
        )
        for set_id in FIRST_SPECIALLY_SETS:
            with self.subTest(set_id=set_id):
                self.assertIn(set_id, field_drop_tables.DROPS_SPECIALLY)
                # The zero that makes this column inert.  Pinned, so the day
                # the data says otherwise this test says so rather than the
                # docstring above quietly going stale.
                leading_percent = field_drop_tables.DROPS_SPECIALLY[set_id][0]
                self.assertEqual(leading_percent, 0.0)
        # ~~a set comprehension with a truthiness filter~~ -- pf-adversary
        # D7 zeroed placement 30's ``drops_specially`` and this assertion did
        # not move, because two other rows carry the same id.  Compared per
        # row now, against the pinned table.
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertEqual(
            {mob.placement_index: mob.drops_specially for mob in rows},
            {30: 2802253, 31: 2802253, 32: 2802253, 42: 2802236,
             69: 0, 82: 0, 83: 0},
        )
        # And no seed places either item, over the same search width the
        # drop-door test uses -- the measurement behind the docstring.
        for mob in rows:
            if not mob.drops_specially:
                continue
            for seed in range(200):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                for item in roll.items:
                    self.assertNotIn(
                        getattr(item, "item_id", None), (2414053, 2414036))

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

    def test_the_composer_body_actually_runs_and_composes_this_scene(
            self) -> None:
        """~~registration is the whole card~~ NOT ENOUGH, pf-adversary D6.

        Two mutants of ``_build_bg0004`` survived the entire suite: a body
        that raises on entry, and a body that calls scene 3's builder while
        leaving ``serves_scene_id`` correct so
        ``assert_every_non_delegated_kind_has_a_builder`` stayed satisfied.
        The second is the one that costs something -- driven by hand it
        gives ``state=refused_Bg0003CensusError ... the Bg0003 roster is
        only valid in scene 3, not scene 4``, and since that state is not in
        ``COMPOSING_STATES`` the runtime call site takes its one-entry
        fallback: the replace-by-omission shape RE-092 named, on EVERY hit
        and EVERY kill in scene 4.

        A registration table proves the wiring is COMPLETE.  Only running
        the body proves it is RIGHT.  The per-scene control pf-adversary ran
        is worth recording: mutating ``_build_bg0002`` fails 23 tests,
        ``_build_bg0015`` 3, ``_build_bg0005`` 1, and ``_build_bg0003``
        ZERO -- scene 3 has this same hole, and closing it there is not this
        card's to do.  This closes it here.
        """
        anchor = mob_scene_recompose.census_anchor(
            EXPECTED_SCENE_ID, (0.0, 0.0, 0.0),
            world_population_bg0004.DEFAULT_ACTOR_COUNT,
        )
        record = mob_scene_recompose.recompose_frames(
            _legacy(), anchor, mob_death.DeathRegister(),
            ledger=mob_combat.open_ledger_for_scene_id(EXPECTED_SCENE_ID),
        )
        self.assertEqual(record.state, mob_scene_recompose.STATE_COMPOSED)
        self.assertIn(record.state, mob_scene_recompose.COMPOSING_STATES)
        # Non-empty bytes, and the scene's own census rather than a
        # neighbour's: the wrong-builder mutant refuses before this point,
        # and a builder that composed some OTHER scene would not carry this
        # scene's seven roster identities.
        self.assertTrue(record.pc)
        self.assertTrue(record.frame)
        # ~~"a builder that composed some OTHER scene would not carry this
        # scene's seven roster identities"~~ IS STRUCK, and the correction is
        # this round's (`ti9gxr`, pf-adversary on the merged `#814`): that
        # sentence is FALSE and was measured false.  Every scene assigns
        # identities from the same low range (``0x2000 + placement + 1``), so
        # a two-byte pattern in a 16-19 KB blob costs almost nothing to hit --
        # Bg0002's and bg0005's own composed frames each carry **7 of 7** of
        # scene 4's identities, and Bg0003's carry 5 of 7.  The whole
        # wrong-builder mutant was being killed by ``record.state`` above,
        # while the docstring credited the byte check.
        #
        # That matters beyond this card: COO-DECISION 20260905_1246 item 1
        # makes exactly this pair ("state in COMPOSING_STATES + the bytes
        # carry the roster's own identities") the GENERIC per-scene contract
        # every future scene must pass, starting with LANE-A's scene 17.  A
        # vacuous half was one round away from being generalised to the whole
        # project.
        #
        # COORDINATES are what actually discriminate, because they come from
        # this scene's own placement rows and no other scene's.  Measured on
        # the same three controls: 7/7 present in scene 4's frame, **0/7** in
        # scene 3's and 0/7 in scene 5's.
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            with self.subTest(identity=hex(mob.actor_identity)):
                self.assertIn(
                    mob.actor_identity.to_bytes(2, "little"), record.frame,
                    "necessary but NOT sufficient -- see the comment above; "
                    "the coordinate check below is the discriminating one")
                for axis, value in (("x", mob.x), ("y", mob.y), ("z", mob.z)):
                    with self.subTest(axis=axis):
                        self.assertIn(
                            struct.pack("<f", value), record.frame,
                            "scene %s's composed frame does not carry this "
                            "roster row's own %s -- the body ran, but it "
                            "composed some other scene's census"
                            % (EXPECTED_SCENE_ID, axis))

    def test_the_coordinate_check_above_is_not_vacuous(self) -> None:
        """The control that makes the assertion above worth making.

        pf-adversary's D2 this round was not "the test is wrong", it was "the
        test passes for the wrong reason and nobody would notice".  A fix that
        swaps one weak substring check for another weak substring check earns
        nothing, so the discrimination is measured here rather than asserted
        in a comment: a NEIGHBOURING scene's composed frame must NOT carry
        scene 4's roster coordinates.

        bg0005 is the control because it is one of the two scenes whose frames
        were measured carrying 7/7 of scene 4's identity bytes -- i.e. the
        exact frame that would have slipped past the old assertion.
        """
        anchor = mob_scene_recompose.census_anchor(
            world_population_bg0005.SCENE_N_ID, (0.0, 0.0, 0.0),
            world_population_bg0005.DEFAULT_ACTOR_COUNT,
        )
        neighbour = mob_scene_recompose.recompose_frames(
            _legacy(), anchor, mob_death.DeathRegister(),
            ledger=mob_combat.open_ledger_for_scene_id(
                world_population_bg0005.SCENE_N_ID),
        )
        self.assertEqual(neighbour.state, mob_scene_recompose.STATE_COMPOSED)
        carried_identities = 0
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            if mob.actor_identity.to_bytes(2, "little") in neighbour.frame:
                carried_identities += 1
            for value in (mob.x, mob.y, mob.z):
                self.assertNotIn(
                    struct.pack("<f", value), neighbour.frame,
                    "a neighbouring scene's frame carries one of scene %s's "
                    "own coordinates -- the check above is not discriminating "
                    "after all and this card must be re-thought, not patched"
                    % EXPECTED_SCENE_ID)
        # And the measurement that motivated the change, pinned so it cannot
        # quietly stop being true: the identity bytes really are shared.
        self.assertGreater(
            carried_identities, 0,
            "if a neighbour's frame stopped carrying ANY of this scene's "
            "identity bytes, the old assertion would have become meaningful "
            "again and this comment would be misleading")

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


class GeneratedSiblingTablesAreProtectedOffBridgeTests(unittest.TestCase):
    """pf-adversary D1 of round `ti9gxr`, on this PR's own merged work.

    The round that shipped scene 4 widened THREE generated modules and gave
    only one of them the digest pin D7 had asked for.  Measured on a clone
    with no `pf_bridge` sibling -- which is the configuration the Windows
    merge gate runs, `actions/checkout@v4` with no sibling and these skips
    pinned in `docs/PYTEST_SKIP_PINS.json` -- every one of these hand-edits
    left a 2138-test drop/loot/pickup selection GREEN:

      * `DROPS_NORMAL[2701003]` entry rate 10.0 -> 0.0 (Blood Cubic Crystal
        stops dropping in six scenes, including all seven scene-4 rows)
      * that entry's item id 2400046 -> 2400047
      * `DROPS_EQUIPMENT[5400003]` entry-1 item id, and its rate 50.0 -> 5.0
      * `ITEMS[2414053]` display name

    The only guard was `@BRIDGE_GAMEDATA.skip_unless_present()` on the
    byte-for-byte regenerate tests, which the gate never runs.  These two
    digests are the non-bridge-gated half, in the shape D7 already
    established next door: the whole shipped table digested, so no column can
    move on a clone with no bridge beside it.

    THEY ARE NOT A DRIFT CHECK against the client tables -- a self-hash
    "keeps matching itself forever regardless of what pf_bridge does"
    (pf-adversary, round iazmrv).  The regenerate tests remain the upstream
    check.  This pair closes the OTHER hole: a hand-edit that never touches
    the bridge at all.

    Recompute with:
      hashlib.sha256("".join(repr(getattr(field_drop_tables, name))
                             for name in DROP_TABLE_NAMES)
                     .encode("ascii")).hexdigest()
    """

    # REFERENCED_BY and SCENES are in the digest because the completeness
    # test below caught them missing on the first cut -- and REFERENCED_BY is
    # not incidental: D1 measured that reverting `REFERENCED_BY[2701003]`
    # (which is how a scene stops being listed as using a drop set) was one
    # of the edits that stayed green off-bridge.
    DROP_TABLE_NAMES = (
        "DROPS_NORMAL", "DROPS_EQUIPMENT", "DROPS_SPECIALLY", "ITEMS",
        "REFERENCED_BY", "SCENES")
    DROP_TABLES_SHA256 = (
        "ddca33f5abbd10a9959d9ce02476316a55bbcd397c8827b8c32b415858004727")

    AI_TABLE_NAMES = (
        "AI_COMBAT_ROWS", "AI_COMBAT_PARALLEL", "AI_WANDER_ROWS",
        "PLACEMENT_AI_LINKS")
    # ROUND 4m2kx7: recomputed, and the rows that moved are named here rather
    # than left for a reader to diff.  tools/pf_mine_mob_ai_rows.py's union
    # gained field_mob_tables_bg0008, so the regenerated tables carry FOUR new
    # rows and nine new links and NOTHING ELSE changed: AI_COMBAT 162, 200 and
    # 471 and AI_WANDER 2, which scene 8's nine placements point at, plus their
    # PLACEMENT_AI_LINKS entries.  Every row that was here before is byte-for-
    # byte what it was.
    AI_TABLES_SHA256 = (
        "a83c4d9b9ae24cf1a243f7d2c24e28b2337b2eb43f9ad5189e4dde1ff573895f")

    @staticmethod
    def _digest(module, names):
        return hashlib.sha256(
            "".join(repr(getattr(module, name)) for name in names)
            .encode("ascii")).hexdigest()

    def test_no_drop_table_row_can_move_without_this_going_red(self):
        self.assertEqual(
            self._digest(field_drop_tables, self.DROP_TABLE_NAMES),
            self.DROP_TABLES_SHA256,
            "a row of field_drop_tables.py moved.  If you regenerated it with "
            "tools/pf_mine_scene_drop_tables.py, recompute this digest in the "
            "same commit and say in the PR which rows changed; if you did "
            "not, something hand-edited what a player picks up")

    def test_no_ai_table_row_can_move_without_this_going_red(self):
        # D9 in the same pass: replacing AI_COMBAT_ROWS[300]'s whole mined
        # script with two tokens left the AI test set green, because the only
        # content assertion is `conditions.endswith("GO(0)")`.  Nothing parses
        # these scripts yet, which is why D9 is LOW -- and why a digest is the
        # proportionate guard rather than a parser this lane does not need.
        self.assertEqual(
            self._digest(field_mob_ai_tables, self.AI_TABLE_NAMES),
            self.AI_TABLES_SHA256,
            "a row of field_mob_ai_tables.py moved -- regenerate with "
            "tools/pf_mine_mob_ai_rows.py and recompute this digest in the "
            "same commit")

    def test_the_digests_cover_every_table_each_module_ships(self):
        """A digest that silently stops covering a table is worse than none.

        Both modules' table names are enumerated by hand above, so a NEW
        table added by a widening would be outside the pin and nobody would
        notice.  This asserts the enumeration is complete instead.
        """
        for module, covered in (
            (field_drop_tables, self.DROP_TABLE_NAMES),
            (field_mob_ai_tables, self.AI_TABLE_NAMES),
        ):
            shipped = {
                name for name in dir(module)
                if name.isupper() and isinstance(
                    getattr(module, name), (dict, tuple, list, frozenset))
                and name not in ("SOURCE_DIGESTS",)
            }
            with self.subTest(module=module.__name__):
                self.assertEqual(
                    shipped - set(covered), set(),
                    "this module ships a table the digest above does not "
                    "cover; add it to the name tuple and recompute")


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
