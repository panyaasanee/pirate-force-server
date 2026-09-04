"""LANE-B: scene 5 (bg0005, Evil Port) is a REGISTERED combat scene.

ROUND jqeo2m.  Unlike Bg0015's own file, which spent five rounds asserting
that its table stayed inert, this one asserts the opposite from its first
commit: ``field_mob_tables_bg0005`` is registered in
``field_mobs._SCENE_TABLE_MODULES`` in the same commit that adds it, because
the gate Bg0015 was waiting on does not exist here.  Lane A opened scene 5's
arrival census AND its ``login_entry_allowed`` door in round l03cgh; a player
can stand in this map today.  What they could not do until this commit is
swing at anything in it: ``field_mobs.scene_for_scene_id(5)`` returned
``None``, so ``roster_for_scene_id(5)`` was the empty tuple, so every strike
was refused with ``target_not_in_ledger``.

THE THREE TESTS THAT MATTER MOST, of the ones in this file:

``test_the_ai_register_opens_for_every_shipped_row`` is the one that would
have cost a player the most.  ``mob_ai_control.open_register`` raises
``MobAiControlError: ai_row_missing`` for a roster row whose ``AI_COMBAT`` id
is not in the mined AI table, and ``runtime.py``'s
``_sync_combat_scene_state`` call sits ABOVE every ``except`` in
``_dispatch_mob_combat`` -- so the FIRST swing in a scene whose AI rows were
not mined unwinds the listener thread and empties the player's world.  That
is measured, not theoretical: ``mob_combat_bg0015_gates.py`` measured it end
to end for scene 14, and this round reproduced it for scene 5 (placement 59
-> AI_COMBAT 201) before widening ``tools/pf_mine_mob_ai_rows.py``'s union.

``test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk``
is the control ``scene_identity_rule.py`` says this lane did not have:
"NONE of the three [generator controls] touches type 14, yet the generated
module records the type-2 and bg0001 findings under a heading that reads
'what the crosswalk controls found at mining time'".  Scene 5 is the first
scene where a control measured ON THE SCENE BEING MINED is available without
writing a new one: lane A mined this scene's CLINE type 5 crosswalk
independently, for its own arrival census, into
``world_bg0005_identity.IDENTITIES``.  Two lanes, two tools, two tables, one
answer per row -- or this test says which row disagrees.  It is a control,
not a coincidence: the failure it exists to catch is GT-078's, a map wearing
another map's names, and a single shared bug would have to occur in two
independently written miners to slip past it.

``test_scene_five_is_no_longer_acknowledged_without_a_composer`` holds the
promise ``mob_scene_recompose``'s acknowledgement block makes in its own
words -- "this lane WILL compose it; what it cannot do is compose a map with
no monsters in it" -- to the commit that puts the monsters in the map.
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

from pirateforce_foundation import field_mob_tables_bg0005  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import world_bg0005_identity  # noqa: E402

TOOL_PATH = ROOT / "tools" / "pf_mine_scene_mob_roster.py"
MODULE_PATH = SRC / "pirateforce_foundation" / "field_mob_tables_bg0005.py"
BG0001_PATH = SRC / "pirateforce_foundation" / "field_mob_tables.py"
GAMEDATA = ROOT.parent / "pf_bridge" / "gamedata"

EXPECTED_SCENE = "bg0005"
EXPECTED_SCENE_ID = 5
EXPECTED_HOSTILE_COUNT = 6
EXPECTED_TEMPLATE_COUNT = 6
EXPECTED_UNAMBIGUOUS = 49
# Equal to the hostile count for this scene, and that equality is a MEASURED
# property of bg0005 rather than a law -- the generator's own docstring says
# a scene where the four readings disagree must be read before its roster
# ships.  Here all four agree at 6; pinned separately so a future divergence
# is a failure with a name instead of a silently different roster.
EXPECTED_DROPS_NORMAL = 6

# The whole shipped roster, spelled out rather than counted: a count cannot
# tell a re-mine that swapped two monsters from one that changed nothing.
# (placement index, MOBS n_ID, wire actor identity, MOBS_TIP name)
EXPECTED_ROWS = (
    (59, 148, 0x203C, "Red Devil"),
    (69, 150, 0x2046, "Ned apes"),
    (70, 144, 0x2047, "Hard Blade Eagle"),
    (74, 146, 0x204B, "Black Jack"),
    (84, 523, 0x2055, "Jet cat thieves No.5"),
    (85, 525, 0x2056, "Jet cat thieves No.6"),
)

# Measured immediately before field_mob_tables_bg0005.py was added, and never
# to be updated to make a future edit of field_mob_tables.py pass silently --
# if bg0001's roster changes for a real reason this constant moves in that
# same commit and says why.  Same discipline, same value, as the pin
# tests/test_field_mob_tables_bg0015.py already carries.
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


class Bg0005ShapeTests(unittest.TestCase):
    """Checks that hold with no bridge clone present."""

    def test_module_is_pure_ascii_and_carries_the_generated_header(self) -> None:
        raw = MODULE_PATH.read_bytes()
        self.assertEqual([b for b in raw if b >= 0x80], [])
        self.assertTrue(
            raw.decode("ascii").startswith('"""GENERATED - do not hand-edit.')
        )

    def test_pinned_scene_rule_and_census(self) -> None:
        module = field_mob_tables_bg0005
        self.assertEqual(module.SCENE, EXPECTED_SCENE)
        # The project's ONE identity rule (COO-DECISION 2026-08-29T03:45).
        # Named here rather than inherited from the tool's default, so a
        # change of default cannot silently change what this scene ships.
        self.assertEqual(module.IDENTITY_RULE, "cline")
        self.assertEqual(module.SCENE_CLINE_TYPE, 5)
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
            EXPECTED_ROWS,
        )
        # Every row is stamped with THIS scene: the one thing
        # ``assert_single_scene_tables`` exists to stop is two scenes' rows
        # merged into one roster, and a roster that reached a strike under
        # another scene's name is the same defect one layer down.
        self.assertEqual({mob.scene for mob in rows}, {EXPECTED_SCENE})

    def test_the_ai_register_opens_for_every_shipped_row(self) -> None:
        """The trap that unwinds the listener thread on the FIRST swing.

        Reproduced on scene 5 this round before ``tools/pf_mine_mob_ai_rows
        .py``'s union was widened: ``ai_row_missing: placement 59 points at
        AI_COMBAT 201, which is not in the mined rows``.  A future round that
        adds a roster row citing an unmined AI id, or regenerates the AI
        table from a narrower union, fails here instead of in front of a
        player.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        self.assertTrue(rows)
        mob_ai_control.open_register(rows)  # must not raise
        for mob in rows:
            mob_ai_control.profile_of(mob)  # must not raise

    def test_registering_scene_five_left_the_other_three_scenes_alone(
            self) -> None:
        """A fourth scene must not move the three already on the wire."""
        self.assertEqual(len(field_mobs.roster_for_scene_id(1)), 4)
        self.assertEqual(len(field_mobs.roster_for_scene_id(2)), 12)
        self.assertEqual(len(field_mobs.roster_for_scene_id(14)), 12)
        raw = BG0001_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         BG0001_UNTOUCHED_SHA256)
        self.assertEqual(len(raw), BG0001_UNTOUCHED_SIZE)

    def test_every_shipped_row_agrees_with_lane_as_independently_mined_crosswalk(
            self) -> None:
        """The control measured ON the scene being mined -- see the module
        docstring.  Lane A's ``world_bg0005_identity`` resolved this scene's
        CLINE type 5 block with its own miner for its own arrival census;
        this lane's generator resolved it again for the combat roster.  Every
        shipped row must land on the same ``MOBS.n_ID`` AND the same name in
        both, keyed by the scene file's own Mob-Set number.
        """
        sets = field_mob_tables_bg0005.SET_NUMBER_FOR_PLACEMENT
        disagreements = []
        for mob in field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID):
            set_number = sets[mob.placement_index]
            theirs = world_bg0005_identity.IDENTITIES.get(set_number)
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
            "the two independently mined readings of CLINE type 5 disagree; "
            "GT-078 is what shipping the wrong one costs, so stop and find "
            "out which miner is wrong before regenerating either table",
        )

    def test_no_shipped_template_has_a_death_ruling_yet_and_that_refuses(
            self) -> None:
        """WHAT THIS SCENE STILL CANNOT DO, pinned rather than left implicit.

        None of the six templates is covered by a registered owner letter, so
        a kill in scene 5 refuses.  That refusal is honest degradation and
        NOT a crash: ``runtime.py:5239`` evaluates ``widened=mob_death
        .ruling_for(mob)`` inside the ``try`` whose ``except mob_death
        .MobDeathContractError`` appends ``mob_death_refused_..._no_death_
        frames`` and breaks.  This test pins BOTH halves -- that the rulings
        are missing, and that what they raise is the class that call site
        catches -- so the day an owner letter lands, this test is the one
        that says the scene changed.
        """
        rows = field_mobs.roster_for_scene_id(EXPECTED_SCENE_ID)
        for mob in rows:
            with self.assertRaises(mob_death.MobDeathContractError):
                mob_death.ruling_for(mob)


class Bg0005RecomposeRegistrationTests(unittest.TestCase):
    """The promise ``mob_scene_recompose``'s acknowledgement block made."""

    def test_scene_five_is_no_longer_acknowledged_without_a_composer(
            self) -> None:
        self.assertNotIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.ACKNOWLEDGED_WITHOUT_COMPOSER)
        self.assertTrue(
            mob_scene_recompose.scene_is_accounted_for(EXPECTED_SCENE_ID))
        self.assertIn(
            EXPECTED_SCENE_ID, mob_scene_recompose.composer_scene_ids())
        composer = mob_scene_recompose.composer_for_scene_id(EXPECTED_SCENE_ID)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.kind, mob_scene_recompose.COMPOSER_BG0005)
        self.assertEqual(composer.scene, EXPECTED_SCENE)

    def test_the_new_composer_kind_is_non_delegated_and_has_a_builder(
            self) -> None:
        """The pair round n4pv7k found out of step when scene 14 was added.

        A kind that is admitted by :func:`_compose`'s guard but absent from
        the builder table reaches a ``KeyError`` in the listener thread; a
        kind in the table that is not admitted is a scene someone believes is
        composable and is not.  Both halves are one tuple now, and the
        assertion that keeps them one runs at import time.
        """
        self.assertIn(
            mob_scene_recompose.COMPOSER_BG0005,
            mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS,
        )
        self.assertEqual(
            frozenset(mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS),
            frozenset(mob_scene_recompose._POPULATION_BUILDERS),
        )
        for composer in mob_scene_recompose._COMPOSERS.values():
            if composer.kind == mob_scene_recompose.COMPOSER_DELEGATED:
                continue
            self.assertIn(
                composer.kind,
                mob_scene_recompose.NON_DELEGATED_COMPOSER_KINDS,
                "a registered composer whose kind is neither delegated nor "
                "admitted cannot compose at all",
            )

    def test_the_import_time_assertion_actually_refuses_a_broken_pair(
            self) -> None:
        """Mutation guard: the assertion above is only worth having if it
        fails on the mismatch it exists for.  Handed a broken pair rather
        than breaking the real one."""
        with self.assertRaises(mob_scene_recompose.SceneRecomposeError):
            mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
                kinds=("a_kind_with_no_builder",), builders={},
            )
        with self.assertRaises(mob_scene_recompose.SceneRecomposeError):
            mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
                kinds=(), builders={"a_builder_nothing_admits": None},
            )
        # And passes on a matching pair, so the test above is not green
        # merely because this function raises on everything.
        mob_scene_recompose.assert_every_non_delegated_kind_has_a_builder(
            kinds=("k",), builders={"k": None},
        )


@BRIDGE_GAMEDATA.skip_unless_present()
class Bg0005RegenerateTests(unittest.TestCase):
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
            "src/pirateforce_foundation/field_mob_tables_bg0005.py is stale - "
            "regenerate with tools/pf_mine_scene_mob_roster.py --gamedata "
            "<bridge>/gamedata --scene bg0005 --identity-rule cline --out "
            "<this file>",
        )

    def test_verify_frozen_runs_at_all_and_reproduces_bg0001(self) -> None:
        """``--verify-frozen`` is the generator's ONE checkable control, and
        it had been RAISING rather than verifying since
        ``unambiguous_placements`` grew an eighth tuple element: every call
        died on ``ValueError: too many values to unpack (expected 7)``, so
        the two scenes mined between that change and this round were mined
        with the control off.  Nothing caught it because nothing called this
        function -- so this test calls it.
        """
        tool = _load_tool()
        legacy = ROOT / "current" / "pf_login_game_server_v141.py"
        compared, mismatches = tool.verify_frozen(GAMEDATA, legacy)
        self.assertEqual(compared, tool.CONTROL_UNAMBIGUOUS_COUNT)
        self.assertEqual(mismatches, 0)


if __name__ == "__main__":
    unittest.main()
