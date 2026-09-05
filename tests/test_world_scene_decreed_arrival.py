"""The owner-decreed arrival point, and the four things that hold it honest.

LANE-A, round ihjytc, 2026-09-05.  PANYA-DECISION 20260905_1329 made
``/warp 126`` a LIVE warp like ``/warp 2`` and pinned scene 126's arrival at
``(3050, 232, 90)`` permanently, naming ``CONSTDATA_TH__MARKER.tsv`` row
``n_ID 17`` as where that coordinate comes from.  COO-DECISION 20260905_1346
item 3 routed the fix into the registry - NOT into the ``n_MARKER`` gate -
with one instruction repeated twice: do not weaken the marker test for any
other scene, and keep GT-141's pinned answer for scene 278 exactly as it is.

WHAT THIS FILE PINS
1. The decree reaches the one gate it was meant to reach: GM-A's bare
   ``/warp 126`` now resolves a live target instead of ``None``.
2. It reaches NOTHING ELSE: 17, 278 and 997 - the other three markerless
   scenes - still answer ``None``, and scene 278's report keys are unmoved.
3. The coordinate is not a number this lane typed twice.  The row pinned in
   ``world_scene_marker.DECREED_ARRIVAL_ROWS`` is cross-examined here against
   the committed crosswalk copy, which is a projection of the client's own
   table.  THIS CHECK LIVES IN A TEST ON PURPOSE: no module in the package may
   import ``world_marker_copy`` (the copy does not ship in the release
   archive, and ``tests/test_world_marker_copy.py`` pins that), so the
   production path carries a transcription and the gate re-derives it.
4. The loader refuses every shape of a bad decree, one refusal per defect: a
   decree on a scene rule 1 already answers, a marker row pointing at another
   scene, a spawn that does not stand on the decreed point, a heading that
   disagrees with the row, a tier without a block, a block without the tier.

WHAT IT DOES NOT CLAIM.  Nothing here says a client moved.  The screen layer
is the GT ticket drafted in this round's round file, and LANE-GM's own ticket
(COO-DECISION 20260905_1347) is what confirms the live teleport and the
persisted row on the wire.  The heading (6) is RECORDED AND NOT WIRED: which
heading the client's teleport handler applies is unmeasured, and COO-DECISION
20260905_1346 item 3 says in as many words not to guess it.
"""

from __future__ import annotations

import copy as copy_module
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    world_marker_copy,
    world_scene_marker,
    world_scene_travel,
)
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    warp_no_coords_live_target,
)

DECREED_SCENE = 126
DECREED_MARKER = 17
DECREED_POINT = (3050.0, 232.0, 90.0)
DECREED_HEADING = 6
# The scenes that carry `n_MARKER == 0` and NO decree.  GT-182 nonclaim 4 was
# written about FOUR such scenes (17, 126, 278, 997) - both in-repo citations
# of it say four (`gm/warp_executor.py`, `docs/GM_LANE.md`) and this round
# does not get to re-read it down to three by quoting itself.  What happened
# is narrower and is the whole claim: the owner ruled on ONE of the four by
# name (`PANYA-DECISION 20260905_1329`), so nonclaim 4 still governs the
# other three and this test is what proves the ruling did not leak to them.
STILL_STAGE_ONLY = (17, 278, 997)


def _raw_registry() -> dict:
    return json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="utf-8"))


def _registry_with(mutate) -> None:
    """Load a registry from a mutated copy of the pinned file, in a temp path.

    Returns nothing; raises whatever the loader raises.  Written as a helper
    because every refusal test below is the same three lines with one edit.
    """
    import tempfile

    document = _raw_registry()
    rows = {row["n_id"]: row for row in document["destinations"]}
    mutate(document, rows)
    with tempfile.TemporaryDirectory() as workspace:
        path = Path(workspace) / "world_scene_registry_001.json"
        path.write_text(json.dumps(document), encoding="utf-8")
        world_scene_travel.load_scene_registry(path)


class TheDecreeReachesItsOneGate(unittest.TestCase):
    """PANYA-DECISION 20260905_1329's own sentence, as an assertion."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()

    def test_a_bare_warp_126_now_resolves_a_live_target(self):
        # THE ONE THAT MATTERS.  Before this round this call answered None and
        # `/warp 126` staged the next login instead of moving anybody.
        target = warp_no_coords_live_target(DECREED_SCENE)
        self.assertIsNotNone(target)
        self.assertEqual(target.n_id, DECREED_SCENE)
        self.assertEqual(target.spawn, DECREED_POINT)
        self.assertEqual(
            world_scene_travel.spawn_position(target), DECREED_POINT)

    def test_the_scene_carries_the_decree_and_still_carries_no_table_marker(self):
        row = self.registry[DECREED_SCENE]
        self.assertTrue(row.has_decreed_arrival)
        self.assertTrue(row.has_authored_entry)
        # Rule 1 is untouched: the client's own column still says nothing.
        self.assertFalse(row.has_table_authored_entry)
        self.assertEqual(row.entry_marker, 0)
        self.assertEqual(row.decreed_arrival_marker, DECREED_MARKER)
        self.assertEqual(row.decreed_arrival_heading, DECREED_HEADING)
        self.assertIn("PANYA-DECISION 20260905_1329", row.decreed_arrival_authority)

    def test_the_console_line_says_both_halves_out_loud(self):
        line = world_scene_travel.entry_console_line(
            self.registry[DECREED_SCENE])
        self.assertIn("marker=0", line)
        self.assertIn("decreed_arrival=17", line)
        # cp874 console: the line stays 7-bit ASCII like every other one.
        line.encode("ascii")

    def test_the_login_door_is_not_what_this_round_opened(self):
        # COO-DECISION 20260829_1444 needs an attended var2 test before the
        # ordinary login path may resolve into 126.  A live warp is a
        # different door, and this round did not touch that one.
        self.assertFalse(self.registry[DECREED_SCENE].login_entry_allowed)


class TheDecreeReachesNothingElse(unittest.TestCase):
    """COO-DECISION 20260905_1346 item 3: do not soften the gate elsewhere."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()

    def test_the_other_markerless_scenes_still_stage(self):
        for scene_id in STILL_STAGE_ONLY:
            with self.subTest(scene_id=scene_id):
                row = self.registry[scene_id]
                self.assertEqual(row.entry_marker, 0)
                self.assertFalse(row.has_decreed_arrival)
                self.assertFalse(row.has_authored_entry)
                self.assertIsNone(warp_no_coords_live_target(scene_id))

    def test_the_registry_carries_exactly_the_known_decreed_scenes(self):
        # ~~exactly one scene ... (DECREED_SCENE,)~~ WIDENED round n4vqxc:
        # COO-DECISION 20260905_1748 pinned 304 and 305 by the same
        # mechanism, tagged `decreed_provisional` -- see
        # `world_sea_edge_crossing.py` and its own test file. This still
        # pins a CLOSED set: a decree appearing on any OTHER scene without a
        # round updating this line is exactly the leak this test exists to
        # catch.
        decreed = tuple(
            row.n_id for row in self.registry.destinations
            if row.has_decreed_arrival
        )
        self.assertEqual(decreed, (DECREED_SCENE, 304, 305))

    def test_the_marker_backed_scenes_are_unchanged(self):
        # The scenes rule 1 always reached must still reach it BY RULE 1,
        # not by having quietly acquired a decree.
        for scene_id in (1, 2, 3, 4, 5, 14, 130):
            with self.subTest(scene_id=scene_id):
                row = self.registry[scene_id]
                self.assertTrue(row.has_table_authored_entry)
                self.assertFalse(row.has_decreed_arrival)
                self.assertTrue(row.has_authored_entry)


class TheDecreeDoesNotJoinTheOwnersAttendedChain(unittest.TestCase):
    """pf-adversary D2, caught before merge and pinned so it cannot return.

    `gm/warp_chain_preflight.reachable_scene_ids` DERIVES the attended GT-192
    warp chain from the live-warp gate rather than listing it, which is right
    - a new marker-backed scene should join without an edit.  But a decree is
    a per-scene owner decision about `/warp`, and joining a closed attended
    chain (`COO-DECISION 2026-09-02T05:44`, thirteen scenes) is a different
    decision nobody made.  Left underived, this round would have handed an
    attended tester a fourteenth row telling them to warp into Atlantis - a
    scene whose own registry row says it owes a return ticket.
    """

    def test_the_chain_is_still_the_owners_thirteen(self):
        from pirateforce_foundation.gm import warp_chain_preflight

        reachable = warp_chain_preflight.reachable_scene_ids()
        self.assertNotIn(DECREED_SCENE, reachable)
        self.assertEqual(reachable, (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130))

    def test_the_gate_itself_still_answers_for_the_decreed_scene(self):
        # The exclusion is the CHAIN's, not the gate's: `/warp 126` must
        # still work.  Asserted here so a later round cannot "fix" the chain
        # by closing the gate and call it the same thing.
        self.assertIsNotNone(warp_no_coords_live_target(DECREED_SCENE))


class TheDurableHalfIsRefusedAndSaysSo(unittest.TestCase):
    """pf-adversary D3: the one thing this round does NOT deliver, pinned.

    `PANYA-DECISION 20260904_1430` says a live `/warp <n>` must leave the
    destination scene in `character_positions` at send time.  For scene 126
    it cannot: `gm/warp_scene_persist.login_would_accept` mirrors
    `world_scene_entry.resolve_entry`'s login refusals, and 126's
    `login_entry_allowed` is False (`COO-DECISION 20260829_1444` requires an
    attended var2 test before that flips, and this round did not do one).  So
    the write is refused, by design, and a GM who warps here and relogs is
    back in Port Royal.

    THIS IS PINNED RATHER THAN FIXED because fixing it means opening 126's
    login door, which is a COO/owner decision this lane may not take.  The
    test exists so the gap is a KNOWN, NAMED state with a console line
    (`GM_WARP_SCENE_PERSIST_FAILED scene=126 reason=login_would_refuse`)
    instead of a silent surprise for whoever runs `GT-266`.  Letter:
    `pf_bridge/notes_to_chief/20260905_17xx_LANE-A-ASK-COO-warp-126-live-but-
    not-persisted.md`.  When the door opens, this test flips and that is the
    signal the round is finally complete.
    """

    def test_the_decreed_scenes_are_the_only_live_targets_whose_write_is_refused(self):
        # ~~test_the_decreed_scene_is_the_one_live_target_whose_write_is_
        # refused~~, singular, RENAMED round n4vqxc: 304 and 305 carry the
        # same `login_entry_allowed=False` shape as 126 (measured, not
        # assumed -- neither has an attended login test either), so both
        # join this refused list too.  Still a CLOSED set: any OTHER live
        # target's write going unexpectedly refused is exactly the leak
        # this test exists to catch.
        from pirateforce_foundation.gm import warp_scene_persist

        registry = world_scene_travel.load_scene_registry()
        live = [
            row.n_id for row in registry.destinations
            if warp_no_coords_live_target(row.n_id) is not None
        ]
        refused = [
            scene_id for scene_id in live
            if not warp_scene_persist.login_would_accept(scene_id)
        ]
        self.assertEqual(refused, [DECREED_SCENE, 304, 305], live)

    def test_the_registry_row_still_says_why(self):
        registry = world_scene_travel.load_scene_registry()
        row = registry[DECREED_SCENE]
        self.assertFalse(row.login_entry_allowed)
        # And it still owes a return ticket, which is the same fact wearing
        # the console's clothes.
        self.assertTrue(
            world_scene_travel.entry_report(row)["needs_return_ticket"])


class TheCoordinateIsCrossExamined(unittest.TestCase):
    """The transcription in the package, against the copy of the client's table.

    ``world_scene_marker.DECREED_ARRIVAL_ROWS`` is hand-transcribed, the same
    way ``_ROWS`` above it is, because the production path may not read the
    committed copy.  This is the gate that re-derives it.
    """

    def test_the_pinned_decree_row_is_the_clients_own_row(self):
        for marker_id, scene, x, y, z, direction in (
            world_scene_marker.DECREED_ARRIVAL_ROWS
        ):
            with self.subTest(marker_id=marker_id):
                from_copy = world_marker_copy.verbatim_marker_row(marker_id)
                self.assertIsNotNone(
                    from_copy,
                    "a decree row must be one the committed copy carries "
                    "verbatim, or nothing can check it")
                self.assertEqual(from_copy, (scene, x, y, z, direction))

    def test_the_pair_must_match_or_nothing_comes_back(self):
        # The relation that makes this a crosswalk read and not rule 2's
        # forbidden shortcut: the caller names BOTH ids and the lookup only
        # answers when one pinned row carries both.
        self.assertEqual(
            world_scene_marker.decreed_arrival_row(DECREED_SCENE, DECREED_MARKER),
            (3050, 232, 90, DECREED_HEADING),
        )
        # Right marker, wrong scene.  Nothing.
        self.assertIsNone(
            world_scene_marker.decreed_arrival_row(17, DECREED_MARKER))
        # Right scene, wrong marker.  Nothing.
        self.assertIsNone(
            world_scene_marker.decreed_arrival_row(DECREED_SCENE, 126))

    def test_the_integer_17_cannot_pull_scene_126s_coordinate_out(self):
        """The trap this module names as its own worst case (pf-adversary D4).

        17 is BOTH a real scene id in the registry AND the marker id scene
        126's decree names, and `SHORTCUT_AT_SCENE_17` exists in
        `world_scene_marker` precisely to say what goes wrong when the two
        are confused.  The first version of `decreed_arrival_row` took a
        marker id alone, so `decreed_arrival_row(17)` handed back scene 126's
        point for the integer 17 while `arrival_point(17)` correctly said
        None - two public functions of one module disagreeing about 17, with
        the wrong one dispensing coordinates.  Both spellings a caller
        holding the scene id 17 could reach are None now.
        """
        self.assertIsNone(world_scene_marker.arrival_point(17))
        self.assertIsNone(world_scene_marker.decreed_arrival_row(17, 17))
        self.assertIsNone(
            world_scene_marker.decreed_arrival_row(17, DECREED_MARKER))
        # And the registry agrees: scene 17 has no arrival point of any kind.
        registry = world_scene_travel.load_scene_registry()
        self.assertFalse(registry[17].has_authored_entry)
        self.assertEqual(
            world_scene_marker.SHORTCUT_AT_SCENE_17, (126, 3050, 232, 90))

    def test_the_degenerate_row_for_scene_126_is_not_the_decree(self):
        # MARKER[126] exists and points back at scene 126, but it is the
        # degenerate (0, 0, 90) origin.  The decree names 17, and asking for
        # the pair (126, 126) must answer nothing.
        self.assertIsNone(
            world_scene_marker.decreed_arrival_row(DECREED_SCENE, 126))
        self.assertEqual(
            world_marker_copy.verbatim_marker_row(126)[1:4], (0, 0, 90))

    def test_a_non_int_id_is_refused_rather_than_coerced(self):
        for bad in ("17", 17.0, None, True):
            with self.subTest(repr(bad)):
                with self.assertRaises(world_scene_marker.SceneMarkerError):
                    world_scene_marker.decreed_arrival_row(bad, DECREED_MARKER)
                with self.assertRaises(world_scene_marker.SceneMarkerError):
                    world_scene_marker.decreed_arrival_row(DECREED_SCENE, bad)


class TheLoaderRefusesEveryBadDecree(unittest.TestCase):
    """One refusal per way a decree could become a self-report.

    Every case below is a MUTATION of the pinned file, loaded from a temp
    path: the shipped registry is never written to.
    """

    def test_the_pinned_file_still_loads_unmutated(self):
        # The control.  Without it a helper bug would make every refusal
        # below pass for the wrong reason.
        _registry_with(lambda document, rows: None)

    def test_a_decree_on_a_scene_rule_1_already_answers(self):
        def mutate(document, rows):
            rows[2]["decreed_arrival"] = copy_module.deepcopy(
                rows[DECREED_SCENE]["decreed_arrival"])
            rows[2]["coordinate_provenance"]["evidence_tier"] = (
                "decreed_permanent")
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("rule 1 answers for this scene", str(caught.exception))

    def test_a_marker_row_that_points_at_another_scene(self):
        def mutate(document, rows):
            # Marker 1 is scene 1's row; pointing scene 126 at it is exactly
            # the "borrow somebody else's arrival point" failure.
            rows[DECREED_SCENE]["decreed_arrival"]["marker_n_id"] = 1
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("not a (scene, marker) pair", str(caught.exception))

    def test_a_spawn_that_does_not_stand_on_the_decreed_point(self):
        def mutate(document, rows):
            rows[DECREED_SCENE]["spawn"]["x"] = 3051.0
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("does not stand on that marker's point",
                      str(caught.exception))

    def test_a_heading_that_disagrees_with_the_client_row(self):
        def mutate(document, rows):
            rows[DECREED_SCENE]["decreed_arrival"]["heading"] = 0
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("n_DIRTECTION", str(caught.exception))

    def test_the_tier_without_the_block(self):
        def mutate(document, rows):
            del rows[DECREED_SCENE]["decreed_arrival"]
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("without a decreed_arrival block", str(caught.exception))

    def test_the_block_with_a_tier_neither_decree_may_wear(self):
        # ~~test_the_block_without_the_tier~~, tier "decreed_provisional",
        # RENAMED round n4vqxc: COO-DECISION 20260905_1748 made
        # "decreed_provisional" a SECOND tier a `decreed_arrival` block may
        # legitimately carry (scenes 304/305, own test file), so setting
        # scene 126's tier to it is no longer a defect to refuse -- it is
        # exactly the shape this round shipped elsewhere. The refusal this
        # test exists to pin still holds for a tier that is neither of the
        # two: a block naming a marker row with no corroborating decree
        # strength at all.
        def mutate(document, rows):
            rows[DECREED_SCENE]["coordinate_provenance"]["evidence_tier"] = (
                "chosen_no_evidence")
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("neither 'decreed_permanent' nor 'decreed_provisional'",
                      str(caught.exception))

    def test_a_provisional_decree_is_now_accepted(self):
        # THE WIDENING ITSELF, PINNED POSITIVELY.  Flipping scene 126's own
        # tier to "decreed_provisional" while keeping its (valid) block must
        # now LOAD, not raise -- proven on the scene this file already
        # controls rather than only on 304/305, so a future round cannot
        # "fix" this back to permanent-only without a test in THIS file
        # going red.
        def mutate(document, rows):
            rows[DECREED_SCENE]["coordinate_provenance"]["evidence_tier"] = (
                "decreed_provisional")
        _registry_with(mutate)  # must not raise

    def test_a_half_written_block(self):
        def mutate(document, rows):
            del rows[DECREED_SCENE]["decreed_arrival"]["reverse_lookup"]
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("decreed_arrival is incomplete", str(caught.exception))

    def test_an_unrecognised_evidence_tier_is_still_refused(self):
        def mutate(document, rows):
            rows[DECREED_SCENE]["coordinate_provenance"]["evidence_tier"] = (
                "decreed_permanent_ish")
        with self.assertRaises(ValueError) as caught:
            _registry_with(mutate)
        self.assertIn("is not one this project recognises",
                      str(caught.exception))


if __name__ == "__main__":
    unittest.main()
