"""The first provisioning trial's two records: composed from
`world_m2_survey_plan` + `navigationex_survey_record`, encoded byte-for-byte,
and reachable from no send path.

LANE-A, COO-DECISION 20260904_1345 item 3(b).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "current"))

import pf_login_game_server_v141 as legacy  # noqa: E402
from pirateforce_foundation import world_m2_survey_plan as plan  # noqa: E402
from pirateforce_foundation import (  # noqa: E402
    world_m2_provisioning_trial as trial,
)
from pirateforce_foundation import navigationex_survey_record as survey  # noqa: E402


class TrialSurveyRecordsTests(unittest.TestCase):
    def test_todays_default_plan_yields_both_islands_survey_id_is_the_scene_number(self):
        records = {r.trigger_id: r for r in trial.trial_survey_records()}
        self.assertEqual(set(records), {153, 154})
        # scene_name_tip_id, i.e. the OBSERVED wire trigger id (GT-228), not
        # the internal confirm-tracking handle.
        self.assertEqual(records[153].fields.survey_id, 2)
        self.assertEqual(records[154].fields.survey_id, 3)
        self.assertNotEqual(
            records[153].fields.survey_id, plan.handle_for_trigger_id(153)
        )

    def test_the_xyz_matches_the_plans_own_measured_primary_reading(self):
        records = {r.trigger_id: r for r in trial.trial_survey_records()}
        for planned in plan.planned_records():
            with self.subTest(trigger_id=planned.trigger_id):
                fields = records[planned.trigger_id].fields
                self.assertEqual(fields.x, planned.x)
                self.assertEqual(fields.y, planned.y)
                self.assertEqual(fields.z, planned.z)

    def test_unmeasured_fields_default_to_zero_not_a_guess(self):
        for record in trial.trial_survey_records():
            self.assertEqual(record.fields.unmeasured_0x14, 0)
            self.assertEqual(record.fields.unmeasured_0x16, 0)
            self.assertEqual(record.fields.unmeasured_0x28, 0)
            self.assertEqual(record.fields.unmeasured_0x30, 0)

    def test_an_empty_plan_yields_no_trial_records(self):
        saved = dict(plan.MEASURED_XYZ)
        try:
            plan.MEASURED_XYZ.clear()
            self.assertEqual(trial.trial_survey_records(), ())
        finally:
            plan.MEASURED_XYZ.clear()
            plan.MEASURED_XYZ.update(saved)


SEA_SCENE = 126


class TheCoordinateFrameIsCheckedNotAssumed(unittest.TestCase):
    """pf-adversary, round `16uvmp`: `plan_is_for_scene` had no caller, and
    the call site being waited for is described as "when the player enters the
    sea scene".  Provisioning scene-126 triples to a player standing in scene
    17 -- where row 3021 actually teleports -- can pop a captain report whose
    confirm now composes a real teleport."""

    def test_records_are_encoded_for_the_scene_the_coordinates_belong_to(self):
        encoded = trial.encode_trial_records(
            legacy, msg_id=0x1234, vital_version=1, player_scene_id=SEA_SCENE,
        )
        self.assertEqual({row[0] for row in encoded}, {153, 154})
        self.assertTrue(plan.plan_is_for_scene(SEA_SCENE))

    def test_no_record_is_encoded_for_a_player_in_any_other_scene(self):
        # 17 is the scene the one crossing a player can make today lands in;
        # 1/2/3 are scenes a player is routinely standing in.
        for scene_id in (1, 2, 3, 17, 0, -1):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    trial.encode_trial_records(
                        legacy, msg_id=0x1234, vital_version=1,
                        player_scene_id=scene_id,
                    ),
                    (),
                )

    def test_the_scene_argument_has_no_default(self):
        import inspect

        sig = inspect.signature(trial.encode_trial_records)
        self.assertIs(
            sig.parameters["player_scene_id"].default, inspect.Parameter.empty
        )


class EncodeTrialRecordsTests(unittest.TestCase):
    def test_each_record_matches_the_encoders_own_byte_output(self):
        encoded = trial.encode_trial_records(
            legacy, msg_id=0x1234, vital_version=1, player_scene_id=SEA_SCENE,
        )
        by_trigger = {row[0]: row for row in encoded}
        self.assertEqual(set(by_trigger), {153, 154})
        for record in trial.trial_survey_records():
            trigger_id, pc, frame = by_trigger[record.trigger_id]
            expect_pc, expect_frame = survey.encode_add_survey_data_outer(
                legacy, 0x1234, 1, record.fields,
            )
            with self.subTest(trigger_id=trigger_id):
                self.assertEqual(pc, expect_pc)
                self.assertEqual(frame, expect_frame)

    def test_msg_id_has_no_default(self):
        import inspect

        sig = inspect.signature(trial.encode_trial_records)
        self.assertIs(sig.parameters["msg_id"].default, inspect.Parameter.empty)

    def test_the_two_encoded_frames_are_not_identical(self):
        encoded = trial.encode_trial_records(
            legacy, msg_id=1, vital_version=1, player_scene_id=SEA_SCENE,
        )
        frames = {frame for _tid, _pc, frame in encoded}
        self.assertEqual(len(frames), 2)


class WhatWeSendIsWhatWeCanRecogniseTests(unittest.TestCase):
    """The end-to-end pin round `16uvmp` added, and the defect it caught.

    RE-227 item 3: the client copies the record's opaque u16 back unchanged
    into the confirm frame.  So every u16 this trial WRITES has to be a u16
    `world_m2_survey_plan.confirm_resolution` RECOGNISES -- otherwise the one
    attended run of GT-233 echoes a value we sent ourselves, the plan answers
    "not issued", `world_m2_arrival` refuses the arrival, and the console
    prints the line that reads as a REFUTATION of the provisioning
    hypothesis.  That is exactly the state this repository was in until this
    test existed: the trial wrote 2/3, the plan knew only 0xA099/0xA09A, and
    every test on both sides was green.
    """

    def test_every_survey_id_this_trial_sends_resolves_to_its_own_destination(self):
        records = trial.trial_survey_records()
        self.assertTrue(records)
        for record in records:
            with self.subTest(trigger_id=record.trigger_id):
                resolution = plan.confirm_resolution(record.fields.survey_id)
                self.assertTrue(
                    resolution.issued,
                    "a value this build puts on the wire must resolve as issued",
                )
                self.assertEqual(resolution.trigger_id, record.trigger_id)

    def test_the_trial_reads_the_plans_decision_instead_of_making_its_own(self):
        for planned in plan.planned_records():
            with self.subTest(trigger_id=planned.trigger_id):
                sent = {
                    r.trigger_id: r.fields.survey_id
                    for r in trial.trial_survey_records()
                }
                self.assertEqual(
                    sent[planned.trigger_id], plan.trial_survey_id(planned)
                )

    def test_an_echo_of_a_trial_value_is_reported_as_the_low_confidence_match(self):
        # It resolves, and the resolution says out loud that a single digit
        # coming back is not evidence the record was ours.
        for record in trial.trial_survey_records():
            resolution = plan.confirm_resolution(record.fields.survey_id)
            with self.subTest(trigger_id=record.trigger_id):
                self.assertEqual(resolution.matched_as, "trial")
                self.assertEqual(resolution.confidence, "low")

    def test_a_value_this_trial_never_sends_still_refuses(self):
        sent = {r.fields.survey_id for r in trial.trial_survey_records()}
        for value in (0, 1, 4, 0x1234, 0xFFFF):
            if value in sent:      # pragma: no cover - today's plan sends 2/3
                continue
            with self.subTest(value=value):
                self.assertFalse(plan.confirm_resolution(value).issued)


class NotWiredToAnySendPathTests(unittest.TestCase):
    def test_no_python_file_anywhere_in_this_repository_imports_this_module(self):
        # Same discipline as navigationex_survey_record's own guard: this
        # module composes and encodes but opens no socket and calls no
        # `sendall` itself, and CORE-REQUEST is still open for the runtime.py
        # call site (see this module's own docstring) -- so nothing else in
        # the repository may reach it yet either.
        # Excluded by RELATIVE PATH, not basename -- same fix, same reason,
        # as the sibling guard in test_navigationex_survey_record.py
        # (pf-adversary, this round: a basename-only exclusion is evaded by
        # any same-named file anywhere else in the tree).
        # WIDENED ONCE, ON THE RECORD, round `t7bsfx`/R342 (chief/LANE-E):
        # COO-DECISION 20260904_1845 item 1 ordered the runtime.py call site
        # built, answering the CORE-REQUEST this guard's own message calls
        # "still open".  So runtime.py may now name this module -- and ONLY
        # behind the attended-only flag: `tests/test_m2_survey_trial.py`
        # (`RuntimeCallSiteTests`) parses runtime.py and fails if the call to
        # `encode_trial_records` is not in the same function as the
        # `m2_survey_trial.trial_opening()` that admits it, or if it appears
        # more than once.  The guard below did not become weaker by two
        # paths; it moved next door, from "nobody may call this" to "one
        # named caller, gated".
        excluded = {
            "src/pirateforce_foundation/world_m2_provisioning_trial.py",
            "tests/test_world_m2_provisioning_trial.py",
            # Names this module in its own exclusion-widening comment,
            # not an import -- see that guard's docstring note.
            "tests/test_navigationex_survey_record.py",
            # The one send path, gated -- see the note above.
            "src/pirateforce_foundation/runtime.py",
            "tests/test_m2_survey_trial.py",
        }
        hits = []
        for path in ROOT.rglob("*.py"):
            if ".git" in path.parts:
                continue
            rel = str(path.relative_to(ROOT))
            if rel.replace("\\", "/") in excluded:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "world_m2_provisioning_trial" in text:
                hits.append(rel)
        self.assertEqual(
            hits, [],
            f"world_m2_provisioning_trial must not be imported yet; found: {hits}",
        )

    def test_this_module_opens_no_socket_and_sends_nothing_itself(self):
        source = (
            ROOT / "src" / "pirateforce_foundation"
            / "world_m2_provisioning_trial.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("socket.socket", source)
        self.assertNotIn("sendall", source)
        self.assertNotIn(".send(", source)


if __name__ == "__main__":
    unittest.main()
