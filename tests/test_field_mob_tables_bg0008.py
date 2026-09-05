"""LANE-B: scene 8 (Bg0008, Silver Harbour) is mined but DELIBERATELY UNSHIPPED.

ROUND 4m2kx7.  This file is the opposite of ``test_field_mob_tables_bg0005``'s
first commit and the same shape as ``Bg0015``'s: the roster module it pins is
NOT registered in ``field_mobs._SCENE_TABLE_MODULES``, and the tests below say
WHY in a form that fails when the reason stops being true, instead of leaving a
comment for a later round to read and disbelieve.

WHAT A PLAYER GETS FROM THIS COMMIT: nothing yet, and that is stated plainly
rather than dressed up.  What the NEXT commit gets is a one-line registration,
because this one closes the half of the blocker that was nobody else's to
close.

THE TWO GATES BETWEEN SILVER HARBOUR AND NINE NAMED MONSTERS, MEASURED THIS
ROUND RATHER THAN ASSUMED:

  1. NO DEATH RULING COVERS THIS SCENE.  ``mob_death.ruling_for`` raises
     ``target_outside_the_sanctioned_scope`` for all nine shipped rows -- no
     entry in ``WIDENING_RULINGS`` names templates 274, 277, 280, 281, 527,
     529 or 544.  This gate is NOT this lane's to open: every scene shipped so
     far entered through an owner or COO letter (bg0002's PANYA-DECISION
     2026-08-27T20:10, bg0003's COO 2026-09-04T14:50, bg0005's COO
     2026-09-04T11:48, bg0004's COO 2026-09-05T05:46).  A letter is asked for
     this round; until it exists, registering this scene would put nine
     monsters in a map that a player can strike to 0 HP and then be answered
     with silence for ever -- exactly the outcome ``COO-DECISION
     2026-09-05T05:45+07:00`` refused for Bg0015's Carlos, in that decision's
     own words: one NPC missing from the field is better than one zombie
     standing in it.
  2. THE AI ROWS WERE NOT MINED.  ``mob_ai_control.open_register`` refused
     three of this scene's six combat AI ids (162, 200, 471) and its wander id
     2.  That is the gate that costs a player the most -- the sibling file for
     scene 5 records why: ``runtime.py``'s ``_sync_combat_scene_state`` sits
     above every ``except`` in ``_dispatch_mob_combat``, so the FIRST swing in
     a scene with an unmined AI row unwinds the listener thread and empties
     the world.  THIS GATE IS CLOSED BY THIS COMMIT: the union in
     ``tools/pf_mine_mob_ai_rows.py`` now carries this module and
     ``field_mob_ai_tables`` was regenerated from it (+4 rows, no existing row
     changed).  ``test_the_ai_register_opens_for_every_shipped_row`` is what
     holds it closed.

The refusal in gate 2 was reproduced BEFORE the union line was written, not
predicted from it, exactly as rounds jqeo2m / am1fw8 / r6isy5 did for their
scenes.

WHY REGISTERING WITH EVERY ROW WITHHELD IS NOT THE ANSWER, since it is the
first thing a reader will reach for given Carlos is handled that way.  It was
tried this round and ``field_mobs.load_roster`` refuses it by design:

    the refusal list for scene 'Bg0008' removes every row this lane ships
    (owner: [], lane-withheld: [21, 23, 26, 27, 51, 52, 66, 67, 69]); an
    empty roster must come from an empty table, not from a filter

``LANE_WITHHELD_PLACEMENTS`` is for a row inside a shipped scene, not for a
whole scene that has not been authorised, and the loader says so.  Non-
registration is therefore the only correct state for scene 8 today, and
``test_scene_eight_stays_unregistered_while_no_letter_covers_it`` pins the two
halves TOGETHER so neither can move without the other.

THE PREDICATE READING THE GENERATOR DEMANDS.  Its docstring requires that a
scene whose four hostility readings disagree be READ before its roster ships.
Scene 8 disagrees: ai_combat 9, rank 10, drops_normal 8, rank_and_ai_combat 9.

  * rank 10 vs rank_and_ai_combat 9: one placement carries a rank with no
    combat AI.  It is not shipped, and that is the same treatment every
    sibling scene gives such a row.
  * drops_normal 8 vs 9 shipped: placement 69, "Nina", MOBS 529, is the one
    shipped row with no drop table of any kind.  She is the SECOND row of that
    exact shape this lane has mined -- Bg0015 placement 87 "Carlos" (MOBS 924,
    outfit ``P_MALE_033_000_CARLOS``) is the first -- and both wear a PLAYER
    avatar preset rather than a monster one.  Carlos is withheld today under
    the COO decision named above, pending the content question "what is
    template 924".  ``test_the_second_player_avatar_row_is_named`` exists so
    that Nina cannot reach a player's screen without somebody having answered
    the same question about template 529 first; the ASK-COO letter this round
    writes puts it to the COO with Carlos beside it.

(English only in this file on purpose: the bridge console is cp874.)
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import field_mob_ai_tables  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0008  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import world_bg0008_identity  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0008.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "Bg0008"
EXPECTED_SCENE_ID = 8
EXPECTED_CLINE_TYPE = 8
EXPECTED_HOSTILE_COUNT = 9
EXPECTED_TEMPLATE_COUNT = 7

# The four hostility readings, pinned separately from the roster so a future
# divergence is a failure with a name rather than a quietly different scene.
EXPECTED_PREDICATE_CENSUS = {
    "ai_combat": 9,
    "drops_normal": 8,
    "rank": 10,
    "rank_and_ai_combat": 9,
    "town_target": 0,
    "unambiguous": 33,
}

# The whole shipped roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, MOBS_TIP name, level)
EXPECTED_ROWS = (
    (21, 274, "Polar head", 87),
    (23, 277, "Polar Giant Turtle", 87),
    (26, 280, "Walrus general", 87),
    (27, 281, "Ice Carle Commander", 87),
    (51, 280, "Walrus general", 87),
    (52, 280, "Walrus general", 87),
    (66, 544, "Jet cat thieves No.9", 87),
    (67, 527, "Jet cat thieves No.10", 87),
    (69, 529, "Nina", 90),
)

# The one shipped row with no drop table of any kind, and the sibling row of
# the same shape that is already on main and already withheld.
NINA_PLACEMENT = 69
NINA_TEMPLATE = 529
NINA_OUTFIT = "P_FEMALE_003_002_NENA"
CARLOS_SCENE = "Bg0015"
CARLOS_PLACEMENT = 87

EXPECTED_COMBAT_AI_IDS = (134, 162, 200, 201, 250, 471)
EXPECTED_WANDER_AI_IDS = (2, 11, 16)


def _roster() -> tuple:
    """The scene's rows WITHOUT going through ``field_mobs.load_roster``.

    ``load_roster`` reads ``_SCENE_TABLE_MODULES``, and the whole point of
    this file is that scene 8 is not in it.  ``_parse_hostile_placements`` is
    the same parser ``load_roster`` uses on the module it finds, so these are
    the objects the registration would produce, one lookup earlier.
    """
    return tuple(field_mobs._parse_hostile_placements(field_mob_tables_bg0008))


class Bg0008RosterTests(unittest.TestCase):

    def test_the_module_identifies_its_own_scene(self) -> None:
        self.assertEqual(field_mob_tables_bg0008.SCENE, EXPECTED_SCENE)
        self.assertEqual(
            field_mob_tables_bg0008.SCENE_CLINE_TYPE, EXPECTED_CLINE_TYPE)
        self.assertEqual(field_mob_tables_bg0008.IDENTITY_RULE, "cline")

    def test_the_shipped_roster_is_exactly_these_nine_rows(self) -> None:
        got = tuple(
            (m.placement_index, m.template_id, m.display_name, m.level)
            for m in _roster())
        self.assertEqual(got, EXPECTED_ROWS)
        self.assertEqual(len(got), EXPECTED_HOSTILE_COUNT)
        self.assertEqual(
            len({row[1] for row in got}), EXPECTED_TEMPLATE_COUNT)

    def test_the_predicate_reading_is_pinned(self) -> None:
        """The generator refuses to let a disagreeing scene ship unread; this
        pins the reading that was made, so a re-mine that changes the split
        fails here instead of changing the roster in silence.
        """
        self.assertEqual(
            dict(field_mob_tables_bg0008.PREDICATE_CENSUS),
            EXPECTED_PREDICATE_CENSUS)
        census = field_mob_tables_bg0008.PREDICATE_CENSUS
        self.assertEqual(census["rank_and_ai_combat"], EXPECTED_HOSTILE_COUNT)
        # The two disagreements this scene actually has, asserted as the
        # arithmetic that produced the reading in the module docstring.
        self.assertEqual(census["rank"] - census["rank_and_ai_combat"], 1)
        self.assertEqual(census["rank_and_ai_combat"] - census["drops_normal"], 1)

    def test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk(
            self) -> None:
        """The control measured ON the scene being mined.  Lane A resolved
        this scene's CLINE type 8 block with its own miner for its own arrival
        census (``world_bg0008_identity``); this lane's generator resolved it
        again for the combat roster.  Every shipped row must land on the same
        ``MOBS.n_ID`` AND the same name in both, keyed by the scene file's own
        Mob-Set number.  The failure it exists to catch is GT-078's: a map
        wearing another map's names.
        """
        sets = field_mob_tables_bg0008.SET_NUMBER_FOR_PLACEMENT
        disagreements = []
        for mob in _roster():
            set_number = sets[mob.placement_index]
            theirs = world_bg0008_identity.IDENTITIES.get(set_number)
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
        self.assertEqual(disagreements, [])

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """Gate 2 of the module docstring, held closed.

        Before this round's union widening this call raised
        ``MobAiControlError: ai_row_missing``.  It is the failure that unwinds
        the listener thread on a player's FIRST swing, so it is asserted on
        the register the registration would build, not on the table's keys.
        """
        register = mob_ai_control.open_register(_roster())
        self.assertEqual(len(register.rows), EXPECTED_HOSTILE_COUNT)

    def test_the_ai_table_carries_every_id_this_scene_points_at(self) -> None:
        roster = _roster()
        self.assertEqual(
            tuple(sorted({m.ai_combat for m in roster})),
            EXPECTED_COMBAT_AI_IDS)
        self.assertEqual(
            tuple(sorted({m.ai_wander for m in roster})),
            EXPECTED_WANDER_AI_IDS)
        missing_combat = [
            i for i in EXPECTED_COMBAT_AI_IDS
            if i not in field_mob_ai_tables.AI_COMBAT_ROWS]
        missing_wander = [
            i for i in EXPECTED_WANDER_AI_IDS
            if i not in field_mob_ai_tables.AI_WANDER_ROWS]
        self.assertEqual((missing_combat, missing_wander), ([], []))

    def test_scene_eight_stays_unregistered_while_no_letter_covers_it(
            self) -> None:
        """Gate 1, pinned as ONE fact rather than two.

        The two halves move together or this fails: while no ruling covers a
        shipped template, the scene must be absent from the registry; once a
        letter covers every shipped template, this test tells the round that
        registers the scene that it may.  It does NOT assert "unregistered
        for ever" -- that would have to be deleted to ship the scene, and a
        test that must be deleted to make progress teaches a round to delete
        tests.
        """
        uncovered = []
        for mob in _roster():
            try:
                mob_death.ruling_for(mob)
            except Exception as exc:  # the module's own scope error
                uncovered.append((mob.placement_index, mob.template_id,
                                  type(exc).__name__))
        registered = EXPECTED_SCENE in field_mobs._SCENE_TABLE_MODULES
        if uncovered:
            self.assertFalse(
                registered,
                "scene 8 is registered in _SCENE_TABLE_MODULES while %d of "
                "its %d rows have no death ruling (%r) -- a player could "
                "strike these to 0 HP and be answered with silence for ever, "
                "which COO-DECISION 2026-09-05T05:45+07:00 refused"
                % (len(uncovered), EXPECTED_HOSTILE_COUNT, uncovered))
        else:
            self.assertTrue(
                registered,
                "every shipped row of scene 8 now has a death ruling, so the "
                "only reason this scene was held back is gone: register "
                "field_mob_tables_bg0008 in field_mobs._SCENE_TABLE_MODULES")

    def test_a_full_withhold_is_not_an_alternative_to_non_registration(
            self) -> None:
        """The shape a reader reaches for first, and the loader's own refusal.

        Asserted rather than described, because the module docstring makes a
        claim about ``load_roster``'s behaviour and a claim about behaviour
        that nothing executes is a claim that rots.  The registry is restored
        in ``finally`` so this test cannot leak a registration into a sibling.
        """
        scene = EXPECTED_SCENE
        self.assertNotIn(scene, field_mobs._SCENE_TABLE_MODULES)
        indices = tuple(m.placement_index for m in _roster())
        field_mobs._SCENE_TABLE_MODULES[scene] = field_mob_tables_bg0008
        field_mobs.LANE_WITHHELD_PLACEMENTS[scene] = indices
        field_mobs.LANE_WITHHELD_REASON[scene] = "probe_only_never_shipped"
        try:
            with self.assertRaises(field_mobs.FieldMobContractError) as caught:
                field_mobs.load_roster(scene)
            self.assertIn("must come from an empty table", str(caught.exception))
        finally:
            del field_mobs._SCENE_TABLE_MODULES[scene]
            del field_mobs.LANE_WITHHELD_PLACEMENTS[scene]
            del field_mobs.LANE_WITHHELD_REASON[scene]
        self.assertNotIn(scene, field_mobs._SCENE_TABLE_MODULES)

    def test_the_second_player_avatar_row_is_named(self) -> None:
        """Nina, and the row already on main that she is the second of.

        Not a style check: both rows carry a rank and a combat AI and NO drop
        table of any kind, and both wear a player avatar rather than a monster
        one.  The first such row was withheld by the COO pending a content
        question; this pins the facts that make the same question apply here,
        so the answer cannot be skipped by a round that never noticed the
        resemblance.
        """
        nina = [m for m in _roster() if m.placement_index == NINA_PLACEMENT]
        self.assertEqual(len(nina), 1)
        nina = nina[0]
        self.assertEqual(nina.template_id, NINA_TEMPLATE)
        self.assertEqual(nina.visual_preset, NINA_OUTFIT)
        self.assertTrue(nina.visual_preset.startswith("P_"))
        self.assertEqual(
            (nina.drops_normal, nina.drops_equipment, nina.drops_specially),
            (0, 0, 0))
        no_drops = [
            m for m in _roster()
            if (m.drops_normal, m.drops_equipment, m.drops_specially)
            == (0, 0, 0)]
        self.assertEqual([m.placement_index for m in no_drops],
                         [NINA_PLACEMENT])
        # The sibling row is still on main and still withheld; if that stops
        # being true the precedent this round leans on has moved.
        self.assertIn(
            CARLOS_PLACEMENT,
            field_mobs.lane_withheld_placements(CARLOS_SCENE))

    def test_the_module_is_ascii_only(self) -> None:
        MODULE_PATH.read_text(encoding="ascii")


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0008RegenerateTests(unittest.TestCase):
    """The upstream drift control: the only thing that re-derives these values
    from the client's own tables.  Gated on the bridge clone, so it does not
    run on the Windows merge gate.
    """

    def test_regenerating_reproduces_the_committed_module_byte_for_byte(
            self) -> None:
        # ``--out`` rather than stdout on purpose: the generator prints its
        # withdrawn-placement report to stdout alongside the module, so a
        # stdout comparison would be comparing a report as well as a module.
        with tempfile.TemporaryDirectory() as work:
            out = Path(work) / "regenerated.py"
            subprocess.run(
                [sys.executable, "-B", str(TOOL_PATH),
                 "--gamedata", str(GAMEDATA),
                 "--scene", EXPECTED_SCENE,
                 "--out", str(out)],
                capture_output=True, text=True, check=True)
            regenerated = out.read_text(encoding="ascii")
        on_disk = MODULE_PATH.read_text(encoding="ascii")
        self.assertEqual(
            hashlib.sha256(regenerated.encode("ascii")).hexdigest(),
            hashlib.sha256(on_disk.encode("ascii")).hexdigest(),
            "field_mob_tables_bg0008.py is not what the generator writes "
            "today -- regenerate it rather than hand-editing it")


if __name__ == "__main__":
    unittest.main()
