"""LANE-A: scene 305's census hook - the cast the third arm was waiting for.

WHY THIS IS ITS OWN FILE, AND WHY IT IS SHORTER THAN ITS SIBLING.  The THIRD
ADMISSION ARM itself is graded by ``tests/test_lane_a_scene_census_bg3007.py``
and is not re-graded here: that file owns the arm's mechanics, its
stand-aside for the GM lane's sanction table, and the whole-registry fence
that pins the arm's reach at exactly {304, 305}.  Scene 305 was already
INSIDE that reach before this round - round ``dyi95m`` put it in
``ARM_THREE_ELIGIBLE_SCENE_IDS`` - and what it did not have was a composer,
so a GM standing there was admitted by the arm and then sent nothing.

WHAT IS PINNED HERE, AND WHY EACH ONE:

* the scene is registered in BOTH tables (the seam's ``CENSUS_SOURCES`` and
  this lane's own console-reader table) - a scene in one and not the other
  prints ``LANE_A_CENSUS_SKIPPED`` at import and composes nothing;
* the arm admits it through the THIRD arm and not by accident through the
  first two - a test that only asserted ``scene_may_be_populated`` would
  stay green if someone flipped ``login_entry_allowed``, which is the one
  thing this round must NOT do;
* the composer really composes 59 actors on the repository's REAL registry,
  and the bytes the hook returns are the generation whose numbers its own
  console line quotes - not a second build;
* the login door is still shut for 305 - the sentence "this opens no door"
  is checked, not repeated.

What this file cannot prove, and does not: that a client draws any of it.
Nobody has stood in scene 305 in this project's history.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_population_bg3008  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_scene_census as lane_a,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.world_scene_entry import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
PALE_SILVER_SEA = 305
ROSTER_COUNT = 59


class TheSceneIsRegisteredInBothTables(unittest.TestCase):
    def test_the_seam_table_names_this_lanes_composer(self) -> None:
        self.assertEqual(
            world_scene_travel.CENSUS_SOURCES[PALE_SILVER_SEA],
            "bg3008_roster")
        self.assertEqual(
            world_scene_travel.PALE_SILVER_SEA_SCENE_ID, PALE_SILVER_SEA)

    def test_the_named_constant_is_what_the_allowlist_reads(self) -> None:
        """Until this round the allowlist carried the bare literal 305 with
        a comment saying the scene had no named seam constant.  It has one
        now, and the allowlist reads THAT - so a future edit cannot move the
        seam's idea of this scene without moving the arm's."""
        self.assertIn(
            world_scene_travel.PALE_SILVER_SEA_SCENE_ID,
            lane_a.ARM_THREE_ELIGIBLE_SCENE_IDS)

    def test_the_lane_registered_a_composer_for_scene_305(self) -> None:
        composer = lane_hooks.scene_census_composer(PALE_SILVER_SEA)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)
        self.assertTrue(lane_hooks.module_production_allowed(composer.module))

    def test_the_scene_is_not_in_the_skipped_list(self) -> None:
        """A scene in one table and not the other prints
        ``LANE_A_CENSUS_SKIPPED`` at import.  305 must be in both."""
        skipped = {scene_id for scene_id, _source, _why
                   in lane_a.skipped_scenes()}
        self.assertNotIn(PALE_SILVER_SEA, skipped)
        self.assertIn(PALE_SILVER_SEA, lane_a.scenes_this_lane_composes_for())

    def test_the_console_reader_is_this_scenes_own(self) -> None:
        self.assertIn("bg3008_roster", lane_a._CONSOLE_LINES_OF)


class ItIsTheThirdArmThatAdmitsIt(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()

    def test_the_real_registry_admits_scene_305(self) -> None:
        self.assertTrue(
            lane_a.scene_may_be_populated(PALE_SILVER_SEA, self.registry))

    def test_the_first_two_arms_still_refuse_it(self) -> None:
        """Which arm matters.  If the first one ever answers True for this
        scene, its login door has been opened and that is a different
        decision than the one this round made."""
        self.assertFalse(
            lane_a.scene_is_open_to_players(PALE_SILVER_SEA, self.registry))
        self.assertFalse(
            lane_a.scene_is_sanctioned_for_a_gm_entry(
                PALE_SILVER_SEA, self.registry))
        self.assertTrue(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                PALE_SILVER_SEA, self.registry))

    def test_it_opens_no_login_door(self) -> None:
        """The sentence the arm's docstring makes, checked for THIS scene.
        A character whose stored row names scene 305 is still refused at
        login."""
        destination = world_scene_travel.destination(
            PALE_SILVER_SEA, self.registry)
        self.assertFalse(destination.login_entry_allowed)
        with self.assertRaises(
            world_scene_entry.SceneEntryRefused
        ) as refusal:
            world_scene_entry.resolve_entry(
                Position(PALE_SILVER_SEA, 0, 0.0, 0.0, 0.0, 0),
                registry=self.registry,
                emit=lambda line: None,
                via_login=True,
            )
        self.assertIn(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
            str(refusal.exception))
        # And the non-login route resolves it, which is what makes the
        # refusal above a decision about LOGIN rather than about the scene
        # being unknown.
        entry = world_scene_entry.resolve_entry(
            Position(PALE_SILVER_SEA, 0, 0.0, 0.0, 0.0, 0),
            registry=self.registry,
            emit=lambda line: None,
            via_login=False,
        )
        self.assertEqual(entry.position.scene_id, PALE_SILVER_SEA)


class TheComposerActuallyComposesForAGmStandingThere(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.registry = world_scene_travel.load_scene_registry()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(PALE_SILVER_SEA))

    def _compose(self, scene_id=PALE_SILVER_SEA, registry=None):
        return lane_a._compose_for_scene(scene_id)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=scene_id,
            scene_entry_registry=self.registry if registry is None
            else registry,
        )

    def test_the_arrival_path_gets_fifty_nine_actors_on_the_real_registry(
        self,
    ) -> None:
        result = self._compose()
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, ROSTER_COUNT)
        self.assertTrue(result.pc)
        self.assertTrue(result.frame)

    def test_the_console_lines_carry_this_scenes_own_evidence(self) -> None:
        result = self._compose()
        joined = "\n".join(result.console_lines)
        self.assertIn("WORLD_CENSUS_BG3008 assembled=59/59", joined)
        # And NOT the sibling's, which is what a copied console reader would
        # print while every count in this file stayed green.
        self.assertNotIn("WORLD_CENSUS_BG3007", joined)
        self.assertNotIn("BG3008_UNSHIPPED", joined)
        for line in result.console_lines:
            with self.subTest(line=line[:40]):
                self.assertTrue(line.isascii())

    def test_it_declines_the_moment_the_arm_says_no(self) -> None:
        """The arm is the whole gate: with it patched to False the composer
        declines and sends nothing, which is byte-identical to what this
        scene did before this round."""
        original = lane_a.scene_arrival_was_decreed_and_is_gm_reachable
        lane_a.scene_arrival_was_decreed_and_is_gm_reachable = (
            lambda scene_id, registry=None: False)
        try:
            self.assertIsNone(self._compose())
        finally:
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable = original
        self.assertIsNotNone(self._compose())

    def test_the_bytes_are_the_composers_own_and_not_a_second_build(
        self,
    ) -> None:
        """The seam and this lane must not compose the roster twice: the
        frame the hook returns is the generation whose numbers the console
        line quotes."""
        result = self._compose()
        generation = world_population_bg3008.build_bg3008_population(
            self.legacy, self.anchor, scene_id=PALE_SILVER_SEA,
            count_source=world_population_bg3008.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(result.pc, generation.pc)
        self.assertEqual(result.frame, generation.frame)
        self.assertIn(
            "pc=%dB" % len(generation.pc),
            "\n".join(result.console_lines))

    def test_the_two_seas_do_not_compose_each_others_casts(self) -> None:
        """Both scenes reach the same arm through the same hook.  A composer
        keyed on the arm rather than on the scene would hand a GM standing
        in 305 the Dark Fog Sea's ships, and every count in this file would
        still agree with itself."""
        theirs = lane_a._compose_for_scene(304)(
            legacy=self.legacy,
            anchor=world_scene_travel.spawn_position(
                world_scene_travel.destination(304)),
            scene_id=304,
            scene_entry_registry=self.registry,
        )
        self.assertIsNotNone(theirs)
        self.assertNotEqual(theirs.actor_count, ROSTER_COUNT)
        self.assertNotEqual(theirs.pc, self._compose().pc)


if __name__ == "__main__":
    unittest.main()
