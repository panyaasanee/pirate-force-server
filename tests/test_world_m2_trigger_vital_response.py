"""LANE-A / M2: the TriggerVital 2/3 answer slot is a no-op today, refuses at
a NAMED tier rather than by accident, and would answer exactly what was
registered -- unchanged -- the day all three tiers pass.

COO-DECISION `pf_bridge/notes_to_chief/20260906_1955_COO-DECISION-panya1910-
m2-path-A-server-answers-0x1FB2-LANE-A.md` item 4(b) bans sending anything
here until LANE-UI cites a real candidate frame, so this module's own
production registry must start (and, this round, stay) empty for both ids
2 and 3.

RE-234 item (3) (`pf_bridge/CLIENT_RE_QUEUE.md`, CLOSED by LANE-A) adds the
second half: `GT-228` saw wire trigger id 3 BOTH at island contact AND while
sailing open water, so the wire id ALONE is an unsafe classifier. The tier
tests below are the pin on that -- a filled slot must NOT be enough to make
this module answer, while `ISLAND_CONTACT_DISCRIMINATOR` is `None`.
"""
from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    world_m2_trigger_vital_response as trigger_response,
)

SEA = trigger_response.M2_ISLAND_CONTACT_SCENE_ID

# Captured at IMPORT time, before any test class has had a chance to run, so
# the "production registry untouched" assertion below is anchored to the
# module's own import-time state rather than to whatever the previously
# executed test happened to leave behind.
REGISTRY_AT_IMPORT = dict(trigger_response._CANDIDATES)


class M2RegistryIsolation(unittest.TestCase):
    """Base class: every test in this file asserts, in its OWN tearDown, that
    it left `_CANDIDATES` exactly as it found it, and restores it if not.

    pf-adversary measured that the previous single "was the real registry
    touched" test was ORDER-BLIND: appending one class that writes
    `_CANDIDATES[2]` left all 16 tests green, because nothing checked after
    it ran. Checking in tearDown makes the check order-independent AND makes
    the failing test name the class that did the writing, instead of some
    unrelated test later in the file.
    """

    def setUp(self):
        self._registry_before = dict(trigger_response._CANDIDATES)
        self._discriminator_before = trigger_response.ISLAND_CONTACT_DISCRIMINATOR

    def tearDown(self):
        after = dict(trigger_response._CANDIDATES)
        trigger_response._CANDIDATES.clear()
        trigger_response._CANDIDATES.update(self._registry_before)
        trigger_response.ISLAND_CONTACT_DISCRIMINATOR = self._discriminator_before
        self.assertEqual(
            after,
            self._registry_before,
            "this test mutated the module's production registry",
        )

    def measured_discriminator(self, name="TEST_ONLY_PRETEND_MEASURED"):
        """Pretend, for one test only, that somebody measured the thing tier
        3 is waiting for. Restored by tearDown above.

        This is the ONLY way a test may make tier 3 pass. Setting
        `ISLAND_CONTACT_DISCRIMINATOR` in the module to satisfy a test would
        be a claim that the fact was measured, which it was not.
        """
        trigger_response.ISLAND_CONTACT_DISCRIMINATOR = name


def _fake(va="sub_DEADBEEF", vital_id=0xC723, frame=b"\x12\x34\x56"):
    return trigger_response.CandidateFrame(va=va, vital_id=vital_id, frame=frame)


class RegistryStartsEmptyTests(M2RegistryIsolation):
    """Nothing changes for a live client yet -- both trigger ids are still
    unanswered, which is the entire deliverable of this round."""

    def test_both_m2_trigger_ids_are_still_unregistered(self):
        for wire_trigger_id in (2, 3):
            with self.subTest(wire_trigger_id=wire_trigger_id):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(SEA, wire_trigger_id)
                )

    def test_candidate_trigger_ids_names_exactly_two_and_three(self):
        self.assertEqual(trigger_response.CANDIDATE_TRIGGER_IDS, (2, 3))

    def test_registered_count_is_zero_on_the_real_registry(self):
        self.assertEqual(trigger_response.registered_count(), 0)

    def test_the_production_registry_is_still_its_import_time_self(self):
        # Order-independent: REGISTRY_AT_IMPORT was captured at module import,
        # and every class restores in tearDown, so this holds wherever the
        # runner schedules it.
        self.assertEqual(trigger_response._CANDIDATES, REGISTRY_AT_IMPORT)
        self.assertEqual(REGISTRY_AT_IMPORT, {2: None, 3: None})

    def test_the_discriminator_is_unmeasured_on_the_shipped_module(self):
        # If this ever fails, somebody claimed a measurement. That claim needs
        # a ticket behind it, not a green test.
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)


class ThreeTierGuardTests(M2RegistryIsolation):
    """RE-234 item (3): the wire id alone cannot decide the world. All three
    tiers must pass, in order, and each refusal is NAMED."""

    def test_tier1_a_session_outside_the_sea_scene_is_refused_by_name(self):
        for scene_id in (0, 1, 125, 127, 304, 305, -1, 2 ** 62):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    trigger_response.answer_guard_reason(scene_id, 3),
                    trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
                )

    def test_tier1_refuses_a_non_int_or_bool_scene_id(self):
        for scene_id in ("126", None, 126.0, True, False, [], object()):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    trigger_response.scene_guard_reason(scene_id),
                    trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
                )

    def test_tier1_passes_only_scene_126(self):
        self.assertIsNone(trigger_response.scene_guard_reason(SEA))
        self.assertEqual(SEA, 126)

    def test_tier2_runs_after_tier1_not_before(self):
        # A non-M2 id in the WRONG scene must report the SCENE reason: the
        # tiers are ordered, and reporting the id reason there would leak
        # that this module cares about ids outside its own scene.
        self.assertEqual(
            trigger_response.answer_guard_reason(1, 7),
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 7),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )

    def test_tier3_refuses_the_one_input_that_reaches_it(self):
        for wire_trigger_id in (2, 3):
            with self.subTest(wire_trigger_id=wire_trigger_id):
                self.assertEqual(
                    trigger_response.answer_guard_reason(SEA, wire_trigger_id),
                    trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
                )

    def test_a_filled_slot_is_still_not_answered_while_tier3_refuses(self):
        # THE finding this round exists to pay: on the shipped module, filling
        # a candidate slot must not be sufficient. A player sailing open water
        # in scene 126 fires id 3, and this lookup still says None.
        synthetic_registry = {2: _fake(), 3: _fake()}
        for wire_trigger_id in (2, 3):
            with self.subTest(wire_trigger_id=wire_trigger_id):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(
                        SEA, wire_trigger_id, registry=synthetic_registry
                    )
                )
        # ...and the count still reports the slots as filled, because that is
        # a different question from whether they may be answered.
        self.assertEqual(
            trigger_response.registered_count(registry=synthetic_registry), 2
        )

    def test_all_three_tiers_pass_only_together(self):
        self.measured_discriminator()
        self.assertIsNone(trigger_response.answer_guard_reason(SEA, 3))
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA - 1, 3),
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 4),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )


class LookupIsAPassThroughTests(M2RegistryIsolation):
    """A synthetic registration only -- never written into the module's own
    ``_CANDIDATES`` -- proves the lookup hands back exactly what it was
    given, unedited, once all three tiers pass."""

    def test_a_registered_candidate_comes_back_unchanged(self):
        self.measured_discriminator()
        fake = _fake()
        synthetic_registry = {2: fake, 3: None}

        result = trigger_response.candidate_for_trigger_id(
            SEA, 2, registry=synthetic_registry
        )

        self.assertIs(result, fake)
        self.assertEqual(result.va, "sub_DEADBEEF")
        self.assertEqual(result.vital_id, 0xC723)
        self.assertEqual(result.frame, b"\x12\x34\x56")

    def test_the_other_id_in_the_same_synthetic_registry_stays_none(self):
        self.measured_discriminator()
        synthetic_registry = {2: _fake(), 3: None}

        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 3, registry=synthetic_registry
            )
        )

    def test_registered_count_reads_the_registry_it_is_given(self):
        synthetic_registry = {2: _fake(), 3: None}

        self.assertEqual(
            trigger_response.registered_count(registry=synthetic_registry), 1
        )

    def test_registered_count_is_scoped_to_candidate_trigger_ids(self):
        # Mutant killer: `sum(... for trigger_id in table)` reads identically
        # and is wrong -- an entry for an id this slot is not for must count
        # for nothing, the same way the lookup refuses it.
        off_slot_only = {7: _fake(va="sub_NOT_M2")}
        self.assertEqual(trigger_response.registered_count(registry=off_slot_only), 0)

        mixed = {7: _fake(va="sub_NOT_M2"), 3: _fake()}
        self.assertEqual(trigger_response.registered_count(registry=mixed), 1)


class RegistryTypeDisagreementTests(M2RegistryIsolation):
    """The three plausible "is this a registry" predicates agree on every easy
    input and disagree on exactly two. Both are pinned, so `isinstance(...,
    Mapping)` cannot silently become `dict` or `hasattr(..., "get")`."""

    def test_a_read_only_mapping_that_is_not_a_dict_is_accepted(self):
        self.measured_discriminator()
        fake = _fake()
        proxy = types.MappingProxyType({2: fake, 3: None})

        self.assertIs(
            trigger_response.candidate_for_trigger_id(SEA, 2, registry=proxy), fake
        )
        self.assertEqual(trigger_response.registered_count(registry=proxy), 1)

    def test_an_object_that_merely_owns_a_get_is_refused_by_name(self):
        self.measured_discriminator()

        class NotAMappingButHasGet:
            def get(self, key, default=None):  # pragma: no cover - never called
                return "wrong"

        for callable_under_test in (
            lambda r: trigger_response.candidate_for_trigger_id(SEA, 2, registry=r),
            lambda r: trigger_response.registered_count(registry=r),
        ):
            with self.subTest(callable_under_test=callable_under_test):
                with self.assertRaises(TypeError) as raised:
                    callable_under_test(NotAMappingButHasGet())
                self.assertEqual(
                    str(raised.exception),
                    trigger_response.REGISTRY_REFUSED_NOT_A_MAPPING,
                )


class NonM2TriggerIdGuardTests(M2RegistryIsolation):
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
        # non-M2 id must not be answered -- this slot is only ever for 2/3 --
        # and that holds even with tier 3 satisfied.
        self.measured_discriminator()
        poisoned_registry = {7: _fake(va="sub_NOT_M2", vital_id=1, frame=b"\x00")}
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 7, registry=poisoned_registry
            )
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


class TheTwoArgumentsGetOppositePosturesTests(M2RegistryIsolation):
    """`current_scene_id` and `wire_trigger_id` come off a live session and
    are answered, never raised on; `registry` can only come from a test in
    this repo and is refused LOUDLY, by name.

    pf-adversary's finding 1 against `pirate-force-server#951` was that the
    docstring promised "Never raises" while `registry=[]` raised a bare
    `AttributeError` from `.get`. These tests pin both halves of the fixed
    promise so the docstring cannot drift back into being false.
    """

    HOSTILE = (
        -1, 0, 1, 7, 126, 153, 154, 2 ** 62, True, False, 2.0, "2", b"\x02",
        None, [], {}, object(),
    )

    def test_no_wire_trigger_id_of_any_type_raises(self):
        # The whole point of the fail-closed guard: a session must never die
        # on a surprising trigger id, whatever the client put on the wire.
        for hostile in self.HOSTILE:
            with self.subTest(wire_trigger_id=hostile):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(SEA, hostile)
                )

    def test_no_scene_id_of_any_type_raises(self):
        for hostile in self.HOSTILE:
            with self.subTest(current_scene_id=hostile):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(hostile, 3)
                )

    def test_a_registry_that_is_not_a_mapping_is_refused_by_name(self):
        self.measured_discriminator()
        for not_a_mapping in ([], "x", 7, object()):
            with self.subTest(registry=not_a_mapping):
                with self.assertRaises(TypeError) as raised:
                    trigger_response.candidate_for_trigger_id(
                        SEA, 2, registry=not_a_mapping
                    )
                self.assertEqual(
                    str(raised.exception),
                    trigger_response.REGISTRY_REFUSED_NOT_A_MAPPING,
                )

    def test_registered_count_refuses_the_same_way(self):
        with self.assertRaises(TypeError) as raised:
            trigger_response.registered_count(registry=[])
        self.assertEqual(
            str(raised.exception),
            trigger_response.REGISTRY_REFUSED_NOT_A_MAPPING,
        )

    def test_a_refused_wire_id_is_answered_before_a_bad_registry_is_seen(self):
        # Guard order matters: the three tiers are checked FIRST, so a non-M2
        # id is still answered None rather than being turned into a raise by
        # a malformed test registry sitting behind it.
        self.measured_discriminator()
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(SEA, 7, registry=[])
        )

    def test_a_refused_scene_is_answered_before_a_bad_registry_is_seen(self):
        self.measured_discriminator()
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(1, 3, registry=[])
        )

    def test_tier3_refuses_before_a_bad_registry_is_seen(self):
        # On the SHIPPED module (no measured discriminator) nothing reaches
        # the registry at all, so even a garbage registry cannot raise.
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(SEA, 2, registry=[])
        )


if __name__ == "__main__":
    unittest.main()
