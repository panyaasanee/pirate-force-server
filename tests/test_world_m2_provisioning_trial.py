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


class EncodeTrialRecordsTests(unittest.TestCase):
    def test_each_record_matches_the_encoders_own_byte_output(self):
        encoded = trial.encode_trial_records(legacy, msg_id=0x1234, vital_version=1)
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
        encoded = trial.encode_trial_records(legacy, msg_id=1, vital_version=1)
        frames = {frame for _tid, _pc, frame in encoded}
        self.assertEqual(len(frames), 2)


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
