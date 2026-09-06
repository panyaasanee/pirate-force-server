"""LANE-A / M2: the TriggerVital 2/3 answer slot is a no-op today, and would
answer exactly what was registered -- unchanged -- the day it is not.

COO-DECISION `pf_bridge/notes_to_chief/20260906_1955_COO-DECISION-panya1910-
m2-path-A-server-answers-0x1FB2-LANE-A.md` item 4(b) bans sending anything
here until LANE-UI cites a real candidate frame, so this module's own
production registry must start (and, this round, stay) empty for both ids
2 and 3 -- the first test below is that promise. The second proves the
lookup is a pure pass-through, not a re-encoder, using a SYNTHETIC
registration only (never written into the module's own ``_CANDIDATES``).
The third proves the guard refuses every wire id this M2 slot is not for.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    world_m2_trigger_vital_response as trigger_response,
)


class RegistryStartsEmptyTests(unittest.TestCase):
    """Nothing changes for a live client yet -- both trigger ids are still
    unanswered, which is the entire deliverable of this round."""

    def test_both_m2_trigger_ids_are_still_unregistered(self):
        for wire_trigger_id in (2, 3):
            with self.subTest(wire_trigger_id=wire_trigger_id):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(wire_trigger_id)
                )

    def test_candidate_trigger_ids_names_exactly_two_and_three(self):
        self.assertEqual(trigger_response.CANDIDATE_TRIGGER_IDS, (2, 3))

    def test_registered_count_is_zero_on_the_real_registry(self):
        self.assertEqual(trigger_response.registered_count(), 0)


class LookupIsAPassThroughTests(unittest.TestCase):
    """A synthetic registration only -- never written into the module's own
    ``_CANDIDATES`` -- proves the lookup hands back exactly what it was
    given, unedited, once something IS registered."""

    def test_a_registered_candidate_comes_back_unchanged(self):
        fake = trigger_response.CandidateFrame(
            va="sub_DEADBEEF", vital_id=0xC723, frame=b"\x12\x34\x56"
        )
        synthetic_registry = {2: fake, 3: None}

        result = trigger_response.candidate_for_trigger_id(
            2, registry=synthetic_registry
        )

        self.assertIs(result, fake)
        self.assertEqual(result.va, "sub_DEADBEEF")
        self.assertEqual(result.vital_id, 0xC723)
        self.assertEqual(result.frame, b"\x12\x34\x56")

    def test_the_other_id_in_the_same_synthetic_registry_stays_none(self):
        fake = trigger_response.CandidateFrame(
            va="sub_DEADBEEF", vital_id=0xC723, frame=b"\x12\x34\x56"
        )
        synthetic_registry = {2: fake, 3: None}

        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(3, registry=synthetic_registry)
        )

    def test_registered_count_reads_the_registry_it_is_given(self):
        fake = trigger_response.CandidateFrame(
            va="sub_DEADBEEF", vital_id=0xC723, frame=b"\x12\x34\x56"
        )
        synthetic_registry = {2: fake, 3: None}

        self.assertEqual(
            trigger_response.registered_count(registry=synthetic_registry), 1
        )

    def test_the_real_module_registry_was_never_touched(self):
        # Guards against a test above accidentally mutating shared state:
        # the real registry must still answer None for both ids after the
        # synthetic-registration tests above ran.
        self.assertIsNone(trigger_response.candidate_for_trigger_id(2))
        self.assertIsNone(trigger_response.candidate_for_trigger_id(3))


class NonM2TriggerIdGuardTests(unittest.TestCase):
    """The guard refuses every id that is not one of this M2 slot's two,
    fail-closed style, matching `world_island_dock_table.destination_for_
    trigger_id` and `world_m2_survey_plan.scene_guard_reason`."""

    def test_a_non_m2_trigger_id_is_named_refused(self):
        self.assertEqual(
            trigger_response.trigger_id_guard_reason(7),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )

    def test_a_non_m2_trigger_id_returns_no_candidate_even_if_registered(self):
        # Even a poisoned synthetic registry that DOES carry an entry for a
        # non-M2 id must not be answered -- this slot is only ever for 2/3.
        poisoned_registry = {7: trigger_response.CandidateFrame(
            va="sub_NOT_M2", vital_id=1, frame=b"\x00"
        )}
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(7, registry=poisoned_registry)
        )

    def test_a_non_int_trigger_id_is_named_refused(self):
        self.assertEqual(
            trigger_response.trigger_id_guard_reason("2"),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )

    def test_a_bool_trigger_id_is_named_refused(self):
        # bool subclasses int in Python; True == 1 must not pass as trigger
        # id 1 (which is not one of CANDIDATE_TRIGGER_IDS anyway, but the
        # refusal must be the TYPE reason, not the membership reason).
        self.assertEqual(
            trigger_response.trigger_id_guard_reason(True),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )

    def test_is_candidate_trigger_id_agrees_with_the_guard(self):
        self.assertTrue(trigger_response.is_candidate_trigger_id(2))
        self.assertTrue(trigger_response.is_candidate_trigger_id(3))
        self.assertFalse(trigger_response.is_candidate_trigger_id(7))
        self.assertFalse(trigger_response.is_candidate_trigger_id("2"))


if __name__ == "__main__":
    unittest.main()
