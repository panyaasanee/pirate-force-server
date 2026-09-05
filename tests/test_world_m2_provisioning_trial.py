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
from pirateforce_foundation import (  # noqa: E402
    world_m2_sailing_result_key as sailing_result,
)


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

    def test_the_0x14_field_carries_column_discriminating_sailing_result_keys(self):
        # RE-265 + COO-DECISION 20260905_1947 item 2: a bare 0 at +0x14 is
        # the null-lookup gate RE-265 measured exits BEFORE the distance
        # test -- this field must no longer be that value.  COO-DECISION
        # 20260905_2349 item 1 (GT-233 v3, option (ข)): the two records must
        # each test a DIFFERENT COLUMN hypothesis (n_ID vs n_AREA), not two
        # rows of the same column -- see
        # world_m2_sailing_result_key.column_discriminating_keys.
        records = {r.trigger_id: r for r in trial.trial_survey_records()}
        expected = sailing_result.column_discriminating_keys(len(records))
        self.assertEqual(
            tuple(records[t].fields.unmeasured_0x14 for t in (153, 154)),
            expected,
        )
        # dock 153 (Prison Exile) tests "key is n_ID"; dock 154 (Spice
        # Paradise) tests "key is n_AREA" -- fixed assignment, load-bearing
        # for reading GT-233's result (see trial_survey_records docstring).
        self.assertEqual(
            records[153].fields.unmeasured_0x14,
            sailing_result.provisional_area_126_key(),
        )
        self.assertEqual(
            records[154].fields.unmeasured_0x14, sailing_result.n_area_key()
        )
        keys = [r.fields.unmeasured_0x14 for r in records.values()]
        self.assertEqual(len(set(keys)), len(keys))
        for value in keys:
            self.assertNotEqual(value, 0)
        # D8: neither candidate may collide with either dock's own `+0x12`
        # (survey_id 2/3) -- see column_discriminating_keys' own test for
        # the full reasoning.
        for value in keys:
            self.assertNotIn(value, (2, 3))

    def test_the_remaining_unmeasured_fields_still_default_to_zero(self):
        for record in trial.trial_survey_records():
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


class TrialSceneRefusalReasonTests(unittest.TestCase):
    """`trial_scene_refusal_reason`, closed round `m1wqqy` for
    `ADVERSARY_PENDING` item 3 (round `16uvmp`): `encode_trial_records`
    itself stays `()` on a scene refusal -- its one caller (`runtime.py`)
    only ever checked truthiness -- but the WHY is no longer unreachable."""

    def test_the_sea_scene_has_no_refusal(self):
        self.assertIsNone(trial.trial_scene_refusal_reason(SEA_SCENE))

    def test_a_different_scene_names_the_wrong_scene_reason(self):
        self.assertEqual(
            trial.trial_scene_refusal_reason(17),
            plan.PLAN_SCENE_REFUSED_WRONG_SCENE,
        )

    def test_it_is_the_same_reason_the_plans_own_guard_gives(self):
        for scene_id in (SEA_SCENE, 17, "126", None, 126.0):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    trial.trial_scene_refusal_reason(scene_id),
                    plan.scene_guard_reason(scene_id),
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
                # `encode_trial_records` now defaults `outer_leading_byte`
                # to `survey.OUTER_PRESENCE_PRESENT` (RE-256, round
                # `vwekfq`), so the byte-for-byte comparison must ask the
                # same question of the encoder to stay meaningful.
                outer_leading_byte=survey.OUTER_PRESENCE_PRESENT,
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
            # WIDENED round `vwekfq` (LANE-A), same reason and same shape as
            # this file's own name joining `test_navigationex_survey_
            # record.py`'s exclusion set: condition (d) of COO-DECISION
            # `20260905_0848_...` requires a byte-pin proving scene 17's new
            # roster does not perturb GT-233's own records, and the only
            # faithful way to do that is to call `encode_trial_records`
            # directly and hash its output against a value captured before
            # this round's changes.  Read-only, no socket, no `sendall`.
            "tests/test_lane_a_scene17_roster_does_not_touch_gt233.py",
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



class OuterLeadingByteIsForwardedTests(unittest.TestCase):
    """pf-adversary pass 2, round `f03s5f`; re-baselined round `vwekfq`
    (LANE-A) once RE-256 measured the byte.

    The composer grew `outer_leading_byte` and this function -- the only
    path between it and the wire -- could not pass it.  An attended round
    would have armed the trial, sent byte-identical bytes, seen the same
    dialog and reported that the byte did not help, without ever having
    sent it.

    RE-256 (`pf_bridge/notes_to_chief/
    20260905_1007_RE-256-RESULT-PRESENCE-ONE-SINGLE-RECORD-VERSION-ZERO.md`)
    has since measured this class's own presence byte directly: `1` for one
    record present, `0` for none, never a record count.  This function's
    default therefore moved from `None` (R313's original, byte-missing
    frame) to `survey.OUTER_PRESENCE_PRESENT` -- this is the caller RE-256's
    BUILD_IMPACT line means, and moving the default here (instead of
    editing `runtime.py`, which does not pass this argument at all) is how
    the fix reaches the one real call site with no edit to a chief-owned
    file.  `None` remains a valid EXPLICIT choice -- e.g. to reproduce
    R313's original capture on purpose -- it is simply no longer what a
    real send falls back to.
    """

    _SCENE = plan.XYZ_FRAME_SCENE_ID

    def test_the_default_now_carries_the_re256_measured_presence_byte(self):
        default = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
        )
        explicit_one = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
            outer_leading_byte=survey.OUTER_PRESENCE_PRESENT,
        )
        self.assertEqual(default, explicit_one)
        self.assertTrue(default)
        for _trigger, pc, _frame in default:
            self.assertEqual(pc[20:22], bytes([0x0B, 1]))

    def test_explicit_none_still_reproduces_r313s_original_missing_byte_shape(self):
        # `None` is kept as a valid override -- never as what a real send
        # falls back to any more (module docstring, this round).
        explicit_none = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
            outer_leading_byte=None,
        )
        default = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
        )
        self.assertEqual(len(explicit_none), len(default))
        for (_t1, pc_none, _f1), (_t2, pc_def, _f2) in zip(
            explicit_none, default,
        ):
            self.assertEqual(len(pc_def), len(pc_none) + 2)

    def test_a_value_reaches_every_record_this_function_composes(self):
        bare = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
            outer_leading_byte=None,
        )
        withbyte = trial.encode_trial_records(
            legacy, msg_id=0xC4AF, vital_version=0, player_scene_id=self._SCENE,
            outer_leading_byte=survey.OUTER_PRESENCE_PRESENT,
        )
        self.assertEqual(len(withbyte), len(bare))
        for (trigger_a, pc_a, _), (trigger_b, pc_b, _) in zip(bare, withbyte):
            self.assertEqual(trigger_a, trigger_b)
            self.assertEqual(len(pc_b), len(pc_a) + 2)
            self.assertEqual(pc_b[20:22], bytes([0x0B, 1]))
            self.assertEqual(pc_b[:20], pc_a[:20])
            self.assertEqual(pc_b[22:], pc_a[20:])


if __name__ == "__main__":
    unittest.main()
