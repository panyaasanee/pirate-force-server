"""LANE-A: scene 304's census hook, and THE THIRD ADMISSION ARM it needs.

WHY THIS IS ITS OWN FILE.  ``tests/test_lane_a_scene_census.py`` grades the
composer machinery every scene shares; this file grades the ONE decision
round ``yob0a2`` made on top of it - that a scene whose arrival point the
OWNER decreed, and which a live GM ``/warp`` can land a session on, is shown
its own cast instead of an empty ocean.  That decision is this lane's
reading of two rulings rather than a ruling of its own (see
``scene_arrival_was_decreed_and_is_gm_reachable``'s own
``[ASSUMPTION OF LANE A - AWAITING COO CONFIRMATION]``), so the tests that
would go red if the COO says no are kept together and named.

WHAT IS PINNED HERE, AND WHY EACH ONE:

* the arm ADMITS scene 304 on the repository's real registry - the round is
  a no-op otherwise, and "registered but never fired" is what four earlier
  scenes shipped as;
* the arm admits it through the THIRD arm and not by accident through the
  first two - a test that only asserted ``scene_may_be_populated`` would
  stay green if someone flipped ``login_entry_allowed``, which is the one
  thing this round must NOT do;
* the arm's whole reach is exactly {304, 305} at HEAD, ENUMERATED over the
  registry rather than asserted - a wider arm would populate scenes other
  rounds deliberately left inert, and an arm that did not stand aside for
  scene 126 would take the GM lane's own revocation lever away (measured by
  pf-adversary this round, and pinned below);
* the login door is still shut for 304 - the sentence "this opens no door"
  is checked, not repeated.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_population_bg3007  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import warp_executor  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_scene_census as lane_a,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.world_scene_entry import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DARK_FOG_SEA = 304
PALE_SILVER_SEA = 305
ATLANTIS = 126
ROSTER_COUNT = 50


class TheSceneIsRegisteredInBothTables(unittest.TestCase):
    def test_the_seam_table_names_this_lanes_composer(self) -> None:
        self.assertEqual(
            world_scene_travel.CENSUS_SOURCES[DARK_FOG_SEA], "bg3007_roster")
        self.assertEqual(
            world_scene_travel.DARK_FOG_SEA_SCENE_ID, DARK_FOG_SEA)

    def test_the_lane_registered_a_composer_for_scene_304(self) -> None:
        composer = lane_hooks.scene_census_composer(DARK_FOG_SEA)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)
        self.assertTrue(lane_hooks.module_production_allowed(composer.module))

    def test_the_scene_is_not_in_the_skipped_list(self) -> None:
        """A scene in one table and not the other prints
        ``LANE_A_CENSUS_SKIPPED`` at import.  304 must be in both."""
        skipped = {scene_id for scene_id, _source, _why
                   in lane_a.skipped_scenes()}
        self.assertNotIn(DARK_FOG_SEA, skipped)

    def test_the_console_reader_is_this_scenes_own(self) -> None:
        self.assertIn("bg3007_roster", lane_a._CONSOLE_LINES_OF)


class TheThirdAdmissionArm(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()

    def test_the_real_registry_admits_scene_304_and_that_is_the_round(
        self,
    ) -> None:
        self.assertTrue(
            lane_a.scene_may_be_populated(DARK_FOG_SEA, self.registry))

    def test_it_is_the_third_arm_that_admits_it(self) -> None:
        """Which arm matters.  If the first one ever answers True for this
        scene, its login door has been opened and that is a different
        decision than the one this round made."""
        self.assertFalse(
            lane_a.scene_is_open_to_players(DARK_FOG_SEA, self.registry))
        self.assertFalse(
            lane_a.scene_is_sanctioned_for_a_gm_entry(
                DARK_FOG_SEA, self.registry))
        self.assertTrue(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                DARK_FOG_SEA, self.registry))

    def test_both_halves_of_the_arm_are_load_bearing(self) -> None:
        """Neither half alone admits this scene: a decree with no live warp,
        and a live warp with no decree, both answer False.  Scene 17 is the
        second shape on the real registry (no decree, no live warp); scene 1
        is a live warp with no decree."""
        self.assertFalse(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                17, self.registry))
        self.assertFalse(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                1, self.registry))
        self.assertIsNone(warp_executor.warp_no_coords_live_target(17))
        self.assertIsNotNone(warp_executor.warp_no_coords_live_target(1))
        self.assertFalse(
            world_scene_travel.destination(1, self.registry)
            .has_decreed_arrival)

    def test_the_arms_whole_reach_at_head_is_the_two_ungoverned_seas(
        self,
    ) -> None:
        """ENUMERATED, not asserted.  Every scene in the registry is asked,
        so a row someone pins a decree on later shows up here as a red test
        rather than as a scene quietly becoming populatable.

        THREE scenes carry a decree and a live warp; only TWO reach this
        arm, because scene 126 is governed by the GM lane's sanction table
        and this arm stands aside for it (see the next test).
        """
        admitted = sorted(
            scene_id
            for scene_id in self.registry.ids
            if lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                scene_id, self.registry)
        )
        self.assertEqual(admitted, [DARK_FOG_SEA, PALE_SILVER_SEA])

    def test_it_stands_aside_for_a_scene_the_gm_lane_governs(self) -> None:
        """The lever pf-adversary measured this round, pinned.

        A first draft of this arm answered True for scene 126 as well, which
        made the GM lane's own revocation switch for that scene a no-op: with
        ``single_use_entry_is_admissible`` saying no, the scene was still
        populated.  A lane may not take another lane's lever away, so the
        arm asks FIRST whether the GM lane governs the scene and declines if
        it does.  Driven by revoking the sanction, not by reading the source.
        """
        from pirateforce_foundation.gm import login_scene_admission
        self.assertIn(
            ATLANTIS, login_scene_admission.SANCTIONED_BARRED_SCENES)
        # Both halves of this arm's own test match scene 126 ...
        self.assertTrue(
            world_scene_travel.destination(ATLANTIS, self.registry)
            .has_decreed_arrival)
        self.assertIsNotNone(
            warp_executor.warp_no_coords_live_target(ATLANTIS))
        # ... and it declines anyway, because that scene is arm 2's.
        self.assertFalse(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                ATLANTIS, self.registry))
        # And the lever really is the GM lane's again: revoke it and the
        # whole admission closes for scene 126.
        original = login_scene_admission.single_use_entry_is_admissible
        login_scene_admission.single_use_entry_is_admissible = (
            lambda *a, **k: False)
        try:
            self.assertFalse(
                lane_a.scene_may_be_populated(ATLANTIS, self.registry))
        finally:
            login_scene_admission.single_use_entry_is_admissible = original
        self.assertTrue(lane_a.scene_may_be_populated(ATLANTIS, self.registry))

    def test_a_scene_the_gm_lane_governs_cannot_be_claimed_by_this_arm(
        self,
    ) -> None:
        """The standing-aside is driven by the GM lane's own table, not by a
        hardcoded 126: put scene 304 in that table and this arm gives it up
        too, which is what makes the rule a rule."""
        from pirateforce_foundation.gm import login_scene_admission
        original = login_scene_admission.is_sanctioned_barred_scene
        login_scene_admission.is_sanctioned_barred_scene = (
            lambda scene_id: scene_id in (ATLANTIS, DARK_FOG_SEA))
        try:
            self.assertFalse(
                lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                    DARK_FOG_SEA, self.registry))
        finally:
            login_scene_admission.is_sanctioned_barred_scene = original
        self.assertTrue(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                DARK_FOG_SEA, self.registry))

    def test_the_arm_changes_no_answer_for_a_scene_the_first_arm_admits(
        self,
    ) -> None:
        """The cost check.  Every OTHER scene a live warp reaches is already
        open, so this arm can never be the reason one of them is populated -
        the first arm answers first and this arm is not even called."""
        for scene_id in self.registry.ids:
            if scene_id in (ATLANTIS, DARK_FOG_SEA, PALE_SILVER_SEA):
                continue
            with self.subTest(scene_id=scene_id):
                self.assertFalse(
                    lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                        scene_id, self.registry))

    def test_it_is_fail_closed_in_every_direction(self) -> None:
        for scene_id in (None, "304", -1, 0, 99999, 1.5):
            with self.subTest(scene_id=scene_id):
                self.assertFalse(
                    lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                        scene_id, self.registry))
        # A registry object that raises on every question is not a licence
        # to populate.

        class Exploding:
            def __getattr__(self, name):
                raise RuntimeError("no registry today")

        self.assertFalse(
            lane_a.scene_arrival_was_decreed_and_is_gm_reachable(
                DARK_FOG_SEA, Exploding()))
        self.assertFalse(
            lane_a.scene_may_be_populated(DARK_FOG_SEA, Exploding()))

    def test_it_opens_no_login_door(self) -> None:
        """The sentence the arm's docstring makes, checked.  A character
        whose stored row names scene 304 is still refused at login."""
        destination = world_scene_travel.destination(
            DARK_FOG_SEA, self.registry)
        self.assertFalse(destination.login_entry_allowed)
        with self.assertRaises(
            world_scene_entry.SceneEntryRefused
        ) as refusal:
            world_scene_entry.resolve_entry(
                Position(DARK_FOG_SEA, 0, 0.0, 0.0, 0.0, 0),
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
            Position(DARK_FOG_SEA, 0, 0.0, 0.0, 0.0, 0),
            registry=self.registry,
            emit=lambda line: None,
            via_login=False,
        )
        self.assertEqual(entry.position.scene_id, DARK_FOG_SEA)


class TheComposerActuallyComposesForAGmStandingThere(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.registry = world_scene_travel.load_scene_registry()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(DARK_FOG_SEA))

    def _compose(self, scene_id=DARK_FOG_SEA, registry=None):
        return lane_a._compose_for_scene(scene_id)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=scene_id,
            scene_entry_registry=self.registry if registry is None
            else registry,
        )

    def test_the_arrival_path_gets_fifty_actors_on_the_real_registry(
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
        self.assertIn("WORLD_CENSUS_BG3007 assembled=50/66", joined)
        self.assertIn("BG3007_UNSHIPPED", joined)
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
        generation = world_population_bg3007.build_bg3007_population(
            self.legacy, self.anchor, scene_id=DARK_FOG_SEA,
            count_source=world_population_bg3007.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(result.pc, generation.pc)
        self.assertEqual(result.frame, generation.frame)
        self.assertIn(
            "pc=%dB" % len(generation.pc),
            "\n".join(result.console_lines))


if __name__ == "__main__":
    unittest.main()
