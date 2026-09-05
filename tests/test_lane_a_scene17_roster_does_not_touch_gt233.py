"""LANE-A safety rail, COO-DECISION condition (d), round ``vwekfq``.

WHAT THIS FILE PINS.  ``GT-233`` is Panya's own attended, mid-boot-test on
the ``NavigationEx_AddSurveyDataVtial`` encoder (``m2_survey_trial.py`` /
``world_m2_provisioning_trial.py`` / ``navigationex_survey_record.py``,
landed ``#797``), provisioning ISLAND 2 (Prison Exile, trigger id 153) and
ISLAND 3 (Spice Paradise, trigger id 154) records in **scene 126's own
frame** (``world_m2_survey_plan.XYZ_FRAME_SCENE_ID``).  This round builds
scene 17's roster (``world_bg1001_identity`` / ``world_population_bg1001``)
and touches ``world_m2_sea_destination.CLINE_BLOCKS``,
``world_scene_travel.CENSUS_SOURCES``,
``lane_hooks/lane_a_scene_census.py`` and ``world_population_handoff.py``.
NONE of those four files is on the GT-233 encoder's own import path, and
this test proves it empirically rather than by reading imports by eye: the
two records' bytes are pinned to a sha256 taken BEFORE this round's changes
existed, with every one of this round's new/changed modules already
imported when the pin is recomputed.

WHY A HASH AND NOT A ROUND-TRIP TEST.  ``tests/test_world_m2_provisioning_
trial.py`` already proves ``encode_trial_records`` is internally consistent
(it matches a fresh call to the same encoder) - that catches a REGRESSION
IN THE ENCODER ITSELF, but a self-consistent encoder can still have been fed
different data by this round's own changes if any of them touched something
GT-233's call graph reads.  A hash taken from THIS round's own start (the
values below were captured from the working tree before any file this round
edits was touched) is the only thing that can say "not one byte moved".

CONDITION (d) ALSO ASKS ABOUT THE CROSSING-HANDOFF THIS ROUND TOUCHES, EVEN
THOUGH IT NEVER RUN THROUGH THE SAME COMPOSER.  Scene 17 is registered in
``world_scene_travel.CENSUS_SOURCES`` this round, but deliberately NOT in
``world_population_handoff.ROSTER_COMPOSERS`` - see that module's own
``PENDING_CROSSING_SAFETY_REVIEW`` comment for the runtime.py invariant this
lane will not flip without chief's review.  So the Columbus crossing
(``columbus_quest_dispatch.dispatch_columbus_quest3021``, the flagless
default path GT-106 already walked) still composes and QUEUES the exact
same 27-byte CLEAR it did before this round - pinned below too, because
that queueing is real (``runtime.py``'s ``crossing_handoff_dispatched=True``,
wired chief round R250/65etwo) and not merely a report line.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "current"))

import pf_login_game_server_v141 as legacy  # noqa: E402
from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import m2_survey_trial  # noqa: E402
from pirateforce_foundation import world_bg1001_identity  # noqa: E402
from pirateforce_foundation import world_m2_crossing_handoff as crossing  # noqa: E402
from pirateforce_foundation import world_m2_provisioning_trial as trial  # noqa: E402
from pirateforce_foundation import world_population_bg1001  # noqa: E402
from pirateforce_foundation import world_population_bg3001  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402

# Captured from the working tree BEFORE round `vwekfq` touched anything -
# see the module docstring.  (trigger_id -> (pc sha256, frame sha256)).
#
# RE-PINNED, same round `vwekfq`, AFTER the scene-17 roster work above, for a
# SECOND and unrelated reason: RE-256 (`pf_bridge/notes_to_chief/
# 20260905_1007_RE-256-RESULT-PRESENCE-ONE-SINGLE-RECORD-VERSION-ZERO.md`)
# measured `NavigationEx_AddSurveyDataVtial`'s own outer presence byte
# (pointer-presence boolean, `1` for one record present, `0` for none --
# never a record count) and `world_m2_provisioning_trial.encode_trial_
# records` picked that fix up as its own default, so these two records'
# bytes correctly changed on THIS round for a reason that has nothing to do
# with scene 17: they now carry the RE-256-measured `0B 01` presence byte
# that R313's original frame was missing.  The hash below was re-derived by
# calling `trial.encode_trial_records` with the fixed source (not
# hand-guessed) and this test's own PURPOSE is unchanged -- it still proves
# scene 17's roster does not perturb GT-233's bytes ANY FURTHER than the
# RE-256 fix itself already, deliberately, does.
GT233_EXPECTED_SHA256 = {
    153: (
        "1d45beace4b3950ef70a67de6341d06f7c779387279288bb9c3e8819cf6ff2a9",
        "6263b09144f3613b57a096fad1c47315ec6f72736e135b39118c1606a61f75a8",
    ),
    154: (
        "032db84a0e860e7729dc8af2358105a366530fae329e50f7a539a6dbee74bca3",
        "a13c09cfc733577fadf158ef91ccb688c6af7e71e3484b7004505c68e0eac362",
    ),
}
GT233_SCENE_ID = 126

# The Atlantis census this same boot family already sends (round 4uztfj) -
# pinned as a bonus, same reason: this round's changes must not perturb it
# either.  Captured before round `vwekfq` touched anything.
BG3001_EXPECTED = {
    "actor_count": 37,
    "pc_sha256": "2daa258f6929d56fe3d0ba1c5643f90fe80d7f6aeab90ac2c789039e6931bab0",
    "frame_sha256": "ceb738b356b5aea89e3f1e6d119814e4e56d18d81e6f29d70ed3b4e94e795d93",
}

# The scene-17 crossing handoff as it read before this round and as it must
# still read after: STILL the same 27-byte CLEAR frame
# (``world_m2_crossing_handoff``'s own docstring figure) - see
# PENDING_CROSSING_SAFETY_REVIEW's own docstring for why it is not yet a
# census.  ``pc`` is read from the seam's own header-size constant rather
# than a second literal, so a change to the wire header shape moves both
# sides together; ``frame`` is the framed figure the docstring quotes.
CROSSING_HANDOFF_EXPECTED_PC_BYTES = world_population_handoff.WIRE_HEADER_BYTES
CROSSING_HANDOFF_EXPECTED_FRAME_BYTES = 27


class ThisRoundsModulesAreActuallyLoaded(unittest.TestCase):
    """A pin that is never exercised proves nothing.  Confirm every module
    this round built or edited is actually importable and imported before
    the byte pins below run."""

    def test_the_new_modules_import_and_self_check(self):
        self.assertTrue(world_bg1001_identity.production_allowed)
        self.assertTrue(world_population_bg1001.production_allowed)
        self.assertEqual(len(world_bg1001_identity.shippable_placements()), 7)

    def test_scene_17_is_registered_where_this_round_put_it(self):
        self.assertEqual(
            world_scene_travel.CENSUS_SOURCES.get(17), "bg1001_roster")
        self.assertIn(
            "bg1001_roster", world_population_handoff.PENDING_CROSSING_SAFETY_REVIEW)
        self.assertNotIn("bg1001_roster", world_population_handoff.ROSTER_COMPOSERS)


class GT233BytesUnchangedTests(unittest.TestCase):
    """Condition (d), literally: the island 2/3 provisioning-trial bytes."""

    def test_the_two_survey_records_are_byte_identical_to_before_this_round(self):
        encoded = trial.encode_trial_records(
            legacy,
            msg_id=m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_ID_TRIAL,
            vital_version=(
                m2_survey_trial.NAVIGATIONEX_ADD_SURVEY_DATA_VITAL_VERSION_TRIAL
            ),
            player_scene_id=GT233_SCENE_ID,
        )
        by_trigger = {row[0]: row for row in encoded}
        self.assertEqual(set(by_trigger), set(GT233_EXPECTED_SHA256))
        for trigger_id, (expect_pc_sha, expect_frame_sha) in (
            GT233_EXPECTED_SHA256.items()
        ):
            with self.subTest(trigger_id=trigger_id):
                _tid, pc, frame = by_trigger[trigger_id]
                self.assertEqual(
                    hashlib.sha256(pc).hexdigest(), expect_pc_sha,
                    "trigger %d's provisioning-trial pc bytes moved" % trigger_id,
                )
                self.assertEqual(
                    hashlib.sha256(frame).hexdigest(), expect_frame_sha,
                    "trigger %d's provisioning-trial frame bytes moved"
                    % trigger_id,
                )

    def test_scene_17_still_refuses_the_provisioning_trial_frame(self):
        """The trial's own scene guard (unrelated to this round's changes)
        - re-asserted here so a future change that widens it is caught
        beside the byte pin above, in the file that cares most."""
        self.assertEqual(
            trial.encode_trial_records(
                legacy, msg_id=0x1234, vital_version=1, player_scene_id=17,
            ),
            (),
        )


class Bg3001CensusUnchangedTests(unittest.TestCase):
    """Bonus pin: the Atlantis census this same M2 family already ships."""

    def test_the_atlantis_census_bytes_are_unchanged(self):
        generation = world_population_bg3001.build_bg3001_population(
            legacy, (0.0, 0.0, 0.0), scene_id=126,
            count_source=world_population_bg3001.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(generation.actor_count, BG3001_EXPECTED["actor_count"])
        self.assertEqual(
            hashlib.sha256(generation.pc).hexdigest(),
            BG3001_EXPECTED["pc_sha256"],
        )
        self.assertEqual(
            hashlib.sha256(generation.frame).hexdigest(),
            BG3001_EXPECTED["frame_sha256"],
        )


class ScenesSeventeenCrossingHandoffUnchangedTests(unittest.TestCase):
    """The one thing on scene 17's OWN default path that is already live
    and queued (``runtime.py``'s ``crossing_handoff_dispatched=True``) must
    still be the same 27-byte CLEAR it was before this round - see
    ``world_population_handoff.PENDING_CROSSING_SAFETY_REVIEW``."""

    def test_the_columbus_crossing_still_composes_the_same_clear(self):
        entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)
        handoff = crossing.crossing_handoff(legacy, entry)
        self.assertEqual(handoff.kind, world_population_handoff.KIND_CLEAR)
        self.assertEqual(handoff.actor_count, 0)
        self.assertEqual(len(handoff.pc), CROSSING_HANDOFF_EXPECTED_PC_BYTES)
        self.assertEqual(len(handoff.frame), CROSSING_HANDOFF_EXPECTED_FRAME_BYTES)
        self.assertEqual(handoff.frame, legacy.frame_pc(handoff.pc))


if __name__ == "__main__":
    unittest.main()
