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
import enum
import importlib
import unittest
from collections.abc import Hashable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    world_m2_trigger_vital_response as trigger_response,
    world_sea_edge_crossing,
)
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_island_trigger_log as island_trigger_log,
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
        self._boxes_before = dict(trigger_response.ISLAND_EXTENT_BOXES)

    def tearDown(self):
        after = dict(trigger_response._CANDIDATES)
        trigger_response._CANDIDATES.clear()
        trigger_response._CANDIDATES.update(self._registry_before)
        trigger_response.ISLAND_CONTACT_DISCRIMINATOR = self._discriminator_before
        trigger_response.ISLAND_EXTENT_BOXES.clear()
        trigger_response.ISLAND_EXTENT_BOXES.update(self._boxes_before)
        self.assertEqual(
            after,
            self._registry_before,
            "this test mutated the module's production registry",
        )

    def measured_discriminator(self, name="TEST_ONLY_PRETEND_MEASURED"):
        """Pretend, for one test only, that somebody measured the thing tier
        3 is waiting for, AND return the one reading that matches it.
        Restored by tearDown above.

        This is the ONLY way a test may make tier 3 pass. Setting
        `ISLAND_CONTACT_DISCRIMINATOR` in the module to satisfy a test would
        be a claim that the fact was measured, which it was not.

        THE RETURN VALUE IS THE HALF THIS ROUND ADDED. Before this round,
        setting the name WAS passing tier 3 -- which is exactly the defect
        `IslandContactEvidence` exists to close, and the reason a test that
        wants through tier 3 now has to hold a reading in its hand and pass
        it. A test that only calls this and passes nothing is measuring the
        refusal, which is a legitimate thing to measure and is now visibly
        different from measuring the pass.
        """
        trigger_response.ISLAND_CONTACT_DISCRIMINATOR = name
        trigger_response.ISLAND_EXTENT_BOXES[3] = TEST_ONLY_BOX
        return trigger_response.IslandContactEvidence(
            discriminator=name, x=10.0, y=10.0, z=10.0, source="TEST_ONLY"
        )

    def open_water_reading(self, name="TEST_ONLY_PRETEND_MEASURED"):
        """A reading from the same measurement, taken OUTSIDE every box."""
        return trigger_response.IslandContactEvidence(
            discriminator=name, x=9999.0, y=9999.0, z=9999.0, source="TEST_ONLY"
        )


TEST_ONLY_BOX = (0.0, 0.0, 0.0, 100.0, 100.0, 100.0)


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

    def test_tier1_refuses_a_non_int_or_bool_scene_id_by_its_own_name(self):
        # pf-adversary: collapsing "wrong type" into "wrong scene" sends a
        # caller holding "126" off a TEXT column to look at the player's
        # position. The two reasons are now separate constants.
        for scene_id in ("126", None, 126.0, True, False, [], object()):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    trigger_response.scene_guard_reason(scene_id),
                    trigger_response.SCENE_REFUSED_NOT_AN_INT,
                )

    def test_the_two_tier1_refusals_are_different_strings(self):
        # The mutant this kills: re-pointing SCENE_REFUSED_NOT_AN_INT at the
        # other constant reads as a tidy-up and undoes the split.
        self.assertNotEqual(
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )
        self.assertEqual(
            trigger_response.scene_guard_reason("126"),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.scene_guard_reason(125),
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )

    def test_tier1_passes_only_scene_126(self):
        self.assertIsNone(trigger_response.scene_guard_reason(SEA))
        self.assertEqual(SEA, 126)

    def test_the_sea_scene_id_equals_the_siblings_constant(self):
        self.assertEqual(
            trigger_response.M2_ISLAND_CONTACT_SCENE_ID,
            world_sea_edge_crossing.SEA_EDGE_SOURCE_SCENE_ID,
        )

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
        evidence = self.measured_discriminator()
        self.assertIsNone(trigger_response.answer_guard_reason(SEA, 3, evidence))
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA - 1, 3),
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 4),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )


class OneSpellingOfIsThisAnIntTests(M2RegistryIsolation):
    """pf-adversary A8: four spellings of "is this an int" lived in this one
    file, no test separated them, and the file contradicted ITSELF -- an
    `IntEnum` valued 126 was refused as a scene id and accepted as a trigger
    id. There is one spelling now, and these tests are what hold it.
    """

    class Scene(enum.IntEnum):
        ATLANTIS = 126

    class Trigger(enum.IntEnum):
        SPICE_PARADISE = 3

    class Counted(int):
        """A plain `int` subclass -- not an enum -- so the pin is on the
        SUBCLASS rule, not on anything `enum` does."""

    class EqRaises(int):
        """An `int` subclass whose comparison RAISES. Nothing about it is
        exotic -- `__eq__` is ordinary Python and anything reaching this
        module comes off a live session."""

        def __eq__(self, other):  # noqa: D105
            raise ValueError("wire said no")

        def __ne__(self, other):  # noqa: D105
            raise ValueError("wire said no")

        def __hash__(self):  # noqa: D105
            return 0

    class EqAlwaysTrue(int):
        """An `int` subclass that claims to equal everything, including the
        one scene id tier 1 exists to check for."""

        def __eq__(self, other):  # noqa: D105
            return True

        def __ne__(self, other):  # noqa: D105
            return False

        def __hash__(self):  # noqa: D105
            return hash(3)

    def test_an_int_subclass_is_refused_the_same_way_by_both_guards(self):
        # THE mutant this kills: `type(x) is int` -> `isinstance(x, int) and
        # not isinstance(x, bool)`, which is the spelling `#993` SHIPPED and
        # this round takes back out. The previous version of this test
        # asserted the opposite and is the reason the regression went green.
        self.assertEqual(
            trigger_response.scene_guard_reason(self.Scene.ATLANTIS),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.trigger_id_guard_reason(self.Trigger.SPICE_PARADISE),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.scene_guard_reason(self.Counted(126)),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.trigger_id_guard_reason(self.Counted(3)),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )
        # And the plain int still passes, so the pin is on SUBCLASSES, not
        # on having broken the guard for everybody.
        self.assertIsNone(trigger_response.scene_guard_reason(126))
        self.assertIsNone(trigger_response.trigger_id_guard_reason(3))

    def test_an_int_subclass_whose_eq_raises_is_answered_not_raised(self):
        # D1(a): the CONSEQUENCE, not the spelling. `type(x) is not int`
        # short-circuits before `__eq__` runs; `isinstance` does not, so on
        # `#993`'s head this call came back `ValueError` and broke
        # `candidate_for_trigger_id`'s own "never raises" promise.
        boom = self.EqRaises(126)
        self.assertEqual(
            trigger_response.scene_guard_reason(boom),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertIsNone(trigger_response.candidate_for_trigger_id(boom, 3))
        self.assertIsNone(trigger_response.candidate_for_trigger_id(126, boom))
        # The sibling that is actually on this call path answers the same
        # way, which is the agreement `#993` broke.
        self.assertIsNone(world_sea_edge_crossing.crossing_target(boom, 3))

    def test_an_int_subclass_that_equals_everything_cannot_pass_tier1(self):
        # D1(b): with a discriminator measured AND a matching reading in
        # hand, `#993` handed back a live CandidateFrame FOR SCENE 999.
        evidence = self.measured_discriminator()
        sneaky = self.EqAlwaysTrue(999)
        self.assertEqual(
            trigger_response.answer_guard_reason(sneaky, sneaky, evidence),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                sneaky,
                sneaky,
                registry={3: _fake(va="sub_X", vital_id=1, frame=b"\xff")},
                island_contact=evidence,
            )
        )

    def test_the_two_guards_never_disagree_about_a_type(self):
        # The property the file broke, stated directly: whatever the type
        # rule is, both guards apply the SAME one.
        for value in (
            126, self.Scene.ATLANTIS, self.Counted(126), 126.0, "126", True,
            False, None, [], object(), b"\x7e",
        ):
            with self.subTest(value=value):
                scene_reason = trigger_response.scene_guard_reason(value)
                self.assertEqual(
                    scene_reason == trigger_response.SCENE_REFUSED_NOT_AN_INT,
                    trigger_response.trigger_id_guard_reason(value)
                    == trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
                )

    def test_a_float_that_equals_the_scene_is_still_refused(self):
        # The reason the docstring gives for being strict, kept honest:
        # `126.0 == 126` is True in Python.
        self.assertEqual(126.0, trigger_response.M2_ISLAND_CONTACT_SCENE_ID)
        self.assertEqual(
            trigger_response.scene_guard_reason(126.0),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )

    def test_bool_is_refused_by_both_even_though_it_subclasses_int(self):
        self.assertEqual(
            trigger_response.trigger_id_guard_reason(True),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.scene_guard_reason(True),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )

    def test_the_candidate_ids_are_sorted_and_that_is_load_bearing(self):
        # LOW, from the same run: `sorted()` could be deleted from
        # CANDIDATE_TRIGGER_IDS and no test noticed. The order is what makes
        # this tuple reproducible across runs, since it is built from a
        # SET in the hook module.
        self.assertEqual(
            trigger_response.CANDIDATE_TRIGGER_IDS,
            tuple(sorted(trigger_response.CANDIDATE_TRIGGER_IDS)),
        )
        self.assertEqual(trigger_response.CANDIDATE_TRIGGER_IDS, (2, 3))


class TwoSpellingsNoValueTestCanSeparateTests(M2RegistryIsolation):
    """Two of this file's claims are about HOW something is written, and no
    assertion on today's VALUES can tell the two spellings apart:

      * `M2_ISLAND_CONTACT_SCENE_ID = SEA_EDGE_SOURCE_SCENE_ID` vs `= 126`.
        Both give 126, and `assertIs` passes for both because CPython
        interns small ints.
      * `tuple(sorted(hook_dict))` vs `tuple(hook_dict)`. The hook's dict is
        written `{2: ..., 3: ...}`, so insertion order ALREADY matches
        sorted order and the two agree on today's data.

    Both were measured surviving as mutants this round. The house rule is
    to grep the MECHANISM, not the spelling, so neither is pinned by
    matching source text: each is pinned by moving the thing it depends on
    and reimporting, which is the only way the difference becomes a value.
    """

    def reimported_with(self, module, attribute, value):
        """This module, reimported while `module.attribute` is `value`.
        Both modules are restored before returning, so nothing leaks into
        the rest of the file even when an assertion fails.
        """
        original = getattr(module, attribute)
        setattr(module, attribute, value)
        try:
            importlib.reload(trigger_response)
            return {
                "scene": trigger_response.M2_ISLAND_CONTACT_SCENE_ID,
                "ids": trigger_response.CANDIDATE_TRIGGER_IDS,
                "registry_keys": tuple(sorted(trigger_response._CANDIDATES)),
            }
        finally:
            setattr(module, attribute, original)
            importlib.reload(trigger_response)

    def test_moving_the_siblings_scene_id_moves_this_modules(self):
        # Kills the mutant `M2_ISLAND_CONTACT_SCENE_ID = 126`.
        seen = self.reimported_with(
            world_sea_edge_crossing, "SEA_EDGE_SOURCE_SCENE_ID", 777
        )
        self.assertEqual(seen["scene"], 777)
        self.assertEqual(trigger_response.M2_ISLAND_CONTACT_SCENE_ID, SEA)

    def test_the_registry_keys_follow_the_candidate_ids_not_a_literal(self):
        # pf-adversary D6: `_CANDIDATES = {trigger_id: None for trigger_id in
        # CANDIDATE_TRIGGER_IDS}` could be mutated to the literal
        # `{2: None, 3: None}` and nothing noticed -- the same
        # duplicated-literal shape A9 paid for one screen higher up. Same
        # mechanism kills it: move what it depends on, reimport, and the
        # literal stops tracking.
        original = trigger_response.ISLAND_CONTACT_DISCRIMINATOR
        try:
            seen = self.reimported_with(
                island_trigger_log,
                "M2_OBSERVED_ISLAND_TRIGGER_IDS",
                {8: 800, 9: 900},
            )
            self.assertEqual(seen["ids"], (8, 9))
            self.assertEqual(seen["registry_keys"], (8, 9))
        finally:
            trigger_response.ISLAND_CONTACT_DISCRIMINATOR = original
        self.assertEqual(sorted(trigger_response._CANDIDATES), [2, 3])

    def test_the_candidate_ids_are_sorted_not_merely_copied(self):
        # Kills the mutant `tuple(M2_OBSERVED_ISLAND_TRIGGER_IDS)`: with the
        # hook's dict written the other way round, a copy would give (3, 2).
        seen = self.reimported_with(
            island_trigger_log,
            "M2_OBSERVED_ISLAND_TRIGGER_IDS",
            {3: 154, 2: 153},
        )
        self.assertEqual(seen["ids"], (2, 3))
        self.assertEqual(trigger_response.CANDIDATE_TRIGGER_IDS, (2, 3))


class Tier3IsACheckNotANameTests(M2RegistryIsolation):
    """pf-adversary D2, against `#993` and against `550a36d` alike: tier 3
    used to be, in full, `if ISLAND_CONTACT_DISCRIMINATOR is None`. Setting
    the module constant to the EMPTY STRING -- a value whose plain meaning is
    "nothing was measured" -- unlocked all three tiers and produced a live
    frame. And `answer_guard_reason(current_scene_id, wire_trigger_id)` had
    NOWHERE to put the fact `RE-289` will measure, so the first round to
    receive a discriminator could have closed M2 with a one-line assignment
    that passed every test in this file.

    These tests are the reason that one line is not enough any more.

    [assumption of LANE-A - pending COO confirmation] -- the shape change is asked in
    `20260907_0722_LANE-A-ASK-COO-tier3-signature-must-grow-...`.
    """

    def test_a_blank_discriminator_is_not_a_measurement(self):
        # THE defect, stated as a value. On both shipped trees this returned
        # None and handed back a frame.
        for blank in ("", "   ", "\t", 0, object()):
            with self.subTest(discriminator=blank):
                trigger_response.ISLAND_CONTACT_DISCRIMINATOR = blank
                self.assertEqual(
                    trigger_response.answer_guard_reason(SEA, 3),
                    trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
                )
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(
                        SEA, 3, registry={3: _fake()}
                    )
                )

    def test_naming_the_discriminator_is_not_enough_on_its_own(self):
        # The one-line M2 close, refused: the name is set and a candidate is
        # registered, and the answer is still None because no session
        # reading was handed in.
        self.measured_discriminator()
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(SEA, 3, registry={3: _fake()})
        )

    def test_a_bare_truthy_value_is_not_evidence(self):
        # What a caller reaches for when it wants the guard to go away.
        self.measured_discriminator()
        for pretend in (True, 1, "yes", ("TEST_ONLY_PRETEND_MEASURED", True, "x")):
            with self.subTest(island_contact=pretend):
                self.assertEqual(
                    trigger_response.answer_guard_reason(SEA, 3, pretend),
                    trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
                )

    def test_a_reading_from_another_discriminator_is_refused_by_name(self):
        # Evidence gathered under an older measurement cannot be replayed
        # against a newer one.
        self.measured_discriminator("RE-289-ORDINAL-V2")
        stale = trigger_response.IslandContactEvidence(
            discriminator="RE-289-ORDINAL-V1", x=10.0, y=10.0, z=10.0, source="RE-289"
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, stale),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )

    def test_open_water_is_refused_by_its_own_name(self):
        # `RE-234` item (3)'s finding, as a named refusal: the id alone
        # cannot tell an island from open water, so the reading has to.
        evidence = self.measured_discriminator()
        open_water = self.open_water_reading()
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, open_water),
            trigger_response.CONTACT_REFUSED_OPEN_WATER,
        )
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 3, registry={3: _fake()}, island_contact=open_water
            )
        )

    def test_a_coordinate_that_is_not_a_number_is_refused_as_no_evidence(self):
        # pf-adversary, against this round's FIRST draft: that draft carried
        # `in_contact: bool`, so the CALLER decided the thing tier 3 exists
        # to decide and the module could only check the spelling. A session
        # in open water that handed in `in_contact=True` was accepted. The
        # reading now carries coordinates the server owns, and a coordinate
        # that is not exactly a number is not a position.
        evidence = self.measured_discriminator()
        for junk in ("10.0", None, True, [10.0]):
            with self.subTest(x=junk):
                self.assertEqual(
                    trigger_response.answer_guard_reason(
                        SEA, 3, evidence._replace(x=junk)
                    ),
                    trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
                )

    def test_a_str_subclass_discriminator_cannot_make_tier3_raise(self):
        # THE regression this round nearly shipped, measured by pf-adversary
        # against its own draft: the first `_tier3_contact_reason` compared
        # with `!=` after only an `isinstance` check, so a `str` subclass
        # whose `__ne__` raises made the guard RAISE -- D1's bug reappearing
        # one round later inside the code written to fix it.
        class BoomStr(str):
            def __eq__(self, other):  # noqa: D105
                raise ValueError("boom")

            def __ne__(self, other):  # noqa: D105
                raise ValueError("boom")

            def __hash__(self):  # noqa: D105
                return 0

        evidence = self.measured_discriminator()
        forged = evidence._replace(discriminator=BoomStr(evidence.discriminator))
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, forged),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )

    def test_an_evidence_subclass_cannot_walk_through_tier3(self):
        # Also pf-adversary against the draft: with `isinstance`, a subclass
        # overriding the fields with properties passed every check. Same
        # spelling question this file spends sixty lines on in
        # `_is_a_wire_int`, and the draft answered it the loose way.
        evidence = self.measured_discriminator()
        name = evidence.discriminator

        class Forged(trigger_response.IslandContactEvidence):
            @property
            def discriminator(self):  # noqa: D102
                return name

        self.assertEqual(
            trigger_response.answer_guard_reason(
                SEA, 3, Forged("WRONG", 10.0, 10.0, 10.0, "")
            ),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )

    def test_a_name_without_a_committed_extent_table_decides_nothing(self):
        # The refusal that stops "assign the name" from being enough even
        # with a well-formed reading in hand: RE-289 is open, so there is no
        # box to be inside of.
        evidence = self.measured_discriminator()
        trigger_response.ISLAND_EXTENT_BOXES.clear()
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, evidence),
            trigger_response.CONTACT_REFUSED_NO_EXTENT_TABLE,
        )

    def test_the_shipped_extent_table_is_empty(self):
        # If this fails somebody committed an extent. That needs RE-289's
        # result behind it, not a green test.
        self.assertEqual(trigger_response.ISLAND_EXTENT_BOXES, {})

    def test_a_reading_wrong_in_two_ways_reports_the_earlier_one(self):
        # pf-adversary: swapping checks 3 and 4 inside `_tier3_contact_reason`
        # SURVIVED, because no test ever handed in a reading that was wrong
        # in two ways at once. A stale reading taken in open water must
        # report the STALE half -- the reading cannot be judged for position
        # at all until it is established which measurement it belongs to.
        self.measured_discriminator("RE-289-V2")
        stale_and_adrift = trigger_response.IslandContactEvidence(
            discriminator="RE-289-V1", x=9999.0, y=9999.0, z=9999.0, source="RE-289"
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, stale_and_adrift),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )
        # And with the table emptied as well, the discriminator still wins:
        # three things wrong, one answer, and it is the earliest.
        trigger_response.ISLAND_EXTENT_BOXES.clear()
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, stale_and_adrift),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )

    def test_the_five_tier3_refusals_are_five_different_strings(self):
        reasons = (
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
            trigger_response.CONTACT_REFUSED_NO_EXTENT_TABLE,
            trigger_response.CONTACT_REFUSED_OPEN_WATER,
        )
        self.assertEqual(len(set(reasons)), 5)
        for reason in reasons:
            with self.subTest(reason=reason):
                self.assertTrue(reason.startswith("CONTACT_REFUSED_"))

    def test_tier3_runs_after_tier1_and_tier2_not_before(self):
        # Order pin in the new direction: a wrong scene with GOOD evidence
        # still reports the scene, not the contact.
        evidence = self.measured_discriminator()
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA - 1, 3, evidence),
            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 4, evidence),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )

    def test_tier3_never_raises_on_any_reading(self):
        # Same posture as the other two session-sourced arguments.
        self.measured_discriminator()
        for hostile in (None, object(), [], b"\x01", 2.0, {"x": 1.0}):
            with self.subTest(island_contact=hostile):
                self.assertEqual(
                    trigger_response.answer_guard_reason(SEA, 3, hostile),
                    trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
                )

    def test_nothing_in_src_constructs_an_evidence_reading_yet(self):
        # The honest state of the door frame this round widened: it is a
        # door frame, not a door. If this ever fails, somebody wired tier 3
        # to a live session and that needs a ticket, not a green test.
        import subprocess

        src = Path(__file__).resolve().parents[1] / "src"
        found = subprocess.run(
            ["grep", "-rl", "--include=*.py", "IslandContactEvidence", str(src)],
            capture_output=True,
            text=True,
        ).stdout.split()
        self.assertEqual(
            sorted(Path(hit).name for hit in found),
            ["world_m2_trigger_vital_response.py"],
        )


class FieldOrderIsTheContractTests(M2RegistryIsolation):
    """pf-adversary D3: `CandidateFrame`'s field ORDER was unpinned --
    swapping `va` and `vital_id` in the NamedTuple left 42 tests passing,
    because every test in this file builds it with keywords. The module's one
    job is to carry three values from a LANE-UI letter UNCHANGED, and the
    obvious way a letter gets typed in is POSITIONALLY."""

    def test_the_two_optional_arguments_are_keyword_only(self):
        # pf-adversary, measured against this round's draft: with `registry`
        # third and positional, a caller MEANING to pass evidence
        # (`candidate_for_trigger_id(126, 3, evidence)`) had it land in
        # `registry`, and got a silent `None` with no error, no warning and
        # no way to notice. A `*` turns that into a TypeError at the call.
        # Nothing in the repo imports this module, so this costs no caller.
        evidence = self.measured_discriminator()
        with self.assertRaises(TypeError):
            trigger_response.candidate_for_trigger_id(SEA, 3, evidence)
        # The keyword spelling is the one that works.
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 3, island_contact=evidence
            )
        )

    def test_candidate_frame_field_order_is_pinned(self):
        self.assertEqual(
            trigger_response.CandidateFrame._fields, ("va", "vital_id", "frame")
        )

    def test_a_positionally_built_candidate_frame_lands_where_it_reads(self):
        # The failure this prevents, spelled out: someone transcribing a
        # letter writes the three values in the order the letter gives them.
        frame = trigger_response.CandidateFrame("sub_C0FFEE", 0x1FB2, b"\x01\x02")
        self.assertEqual(frame.va, "sub_C0FFEE")
        self.assertEqual(frame.vital_id, 0x1FB2)
        self.assertEqual(frame.frame, b"\x01\x02")

    def test_island_contact_evidence_field_order_is_pinned(self):
        # Same reasoning, applied to the type this round adds before anyone
        # can build one positionally against the wrong order.
        self.assertEqual(
            trigger_response.IslandContactEvidence._fields,
            ("discriminator", "x", "y", "z", "source"),
        )
        reading = trigger_response.IslandContactEvidence(
            "RE-289", 1.0, 2.0, 3.0, "vital 154"
        )
        self.assertEqual(reading.discriminator, "RE-289")
        self.assertEqual((reading.x, reading.y, reading.z), (1.0, 2.0, 3.0))
        self.assertEqual(reading.source, "vital 154")


class LookupIsAPassThroughTests(M2RegistryIsolation):
    """A synthetic registration only -- never written into the module's own
    ``_CANDIDATES`` -- proves the lookup hands back exactly what it was
    given, unedited, once all three tiers pass."""

    def test_a_registered_candidate_comes_back_unchanged(self):
        evidence = self.measured_discriminator()
        fake = _fake()
        synthetic_registry = {2: fake, 3: None}

        result = trigger_response.candidate_for_trigger_id(
            SEA, 2, registry=synthetic_registry, island_contact=evidence
        )

        self.assertIs(result, fake)
        self.assertEqual(result.va, "sub_DEADBEEF")
        self.assertEqual(result.vital_id, 0xC723)
        self.assertEqual(result.frame, b"\x12\x34\x56")

    def test_the_other_id_in_the_same_synthetic_registry_stays_none(self):
        evidence = self.measured_discriminator()
        synthetic_registry = {2: _fake(), 3: None}

        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 3, registry=synthetic_registry, island_contact=evidence
            )
        )

    def test_registered_count_reads_the_registry_it_is_given(self):
        synthetic_registry = {2: _fake(), 3: None}

        self.assertEqual(
            trigger_response.registered_count(registry=synthetic_registry), 1
        )

    def test_registered_count_reads_an_empty_registry_as_empty(self):
        # pf-adversary D6, second survivor: `_table_for(registry)` mutated to
        # `_table_for(registry) or _CANDIDATES` survived, because no test
        # ever handed in a FALSY mapping. An empty dict is a legitimate
        # registry that says "nothing registered" -- it must not silently
        # fall back to the module's own table.
        self.assertEqual(trigger_response.registered_count(registry={}), 0)
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(SEA, 2, registry={})
        )
        # And with the production table actually carrying something, so the
        # mutant would have a different answer to give.
        trigger_response._CANDIDATES[2] = _fake()
        try:
            self.assertEqual(trigger_response.registered_count(registry={}), 0)
            self.assertEqual(trigger_response.registered_count(), 1)
        finally:
            trigger_response._CANDIDATES[2] = None

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
        evidence = self.measured_discriminator()
        fake = _fake()
        proxy = types.MappingProxyType({2: fake, 3: None})

        self.assertIs(
            trigger_response.candidate_for_trigger_id(
                SEA, 2, registry=proxy, island_contact=evidence
            ),
            fake,
        )
        self.assertEqual(trigger_response.registered_count(registry=proxy), 1)

    def test_an_object_that_merely_owns_a_get_is_refused_by_name(self):
        evidence = self.measured_discriminator()

        class NotAMappingButHasGet:
            def get(self, key, default=None):  # pragma: no cover - never called
                return "wrong"

        for callable_under_test in (
            lambda r: trigger_response.candidate_for_trigger_id(
                SEA, 2, registry=r, island_contact=evidence
            ),
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
        evidence = self.measured_discriminator()
        poisoned_registry = {7: _fake(va="sub_NOT_M2", vital_id=1, frame=b"\x00")}
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 7, registry=poisoned_registry, island_contact=evidence
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

    def test_tier2_id_is_a_candidate_agrees_with_the_guard(self):
        self.assertTrue(trigger_response._tier2_id_is_a_candidate(2))
        self.assertTrue(trigger_response._tier2_id_is_a_candidate(3))
        self.assertFalse(trigger_response._tier2_id_is_a_candidate(7))
        self.assertFalse(trigger_response._tier2_id_is_a_candidate("2"))

    def test_no_public_name_answers_candidacy_from_the_wire_id_alone(self):
        """`COO-DECISION 20260907_0405` item 1: no overload that takes the
        trigger id by itself.

        pf-adversary, run against the round that shipped the three tiers,
        found the file breaking that rule while claiming to keep it: a public
        ``is_candidate_trigger_id(wire_trigger_id)`` sat one import line away
        from the guard, its own docstring offering itself to "a caller that
        only ever needed yes/no", and a test pinned its ``True``.  Renaming it
        fixes today; this test is what stops it coming back under a new name.

        The rule pinned here is narrow and mechanical, so it cannot rot into
        a slogan: a PUBLIC callable defined in this module whose parameters
        mention the wire trigger id must also take ``current_scene_id``.
        ``trigger_id_guard_reason`` is the deliberate exception and is named
        here, once, so that adding a second exception is an edit to this list
        rather than a silent pass.
        """
        import inspect

        allowed_id_only = {"trigger_id_guard_reason"}
        offenders = []
        for name, obj in vars(trigger_response).items():
            if name.startswith("_") or not inspect.isfunction(obj):
                continue
            if obj.__module__ != trigger_response.__name__:
                continue
            params = list(inspect.signature(obj).parameters)
            if "wire_trigger_id" not in params:
                continue
            if name in allowed_id_only:
                continue
            if "current_scene_id" not in params:
                offenders.append(name)
        self.assertEqual(offenders, [])

    def test_the_guard_takes_the_scene_id_first(self):
        """Argument ORDER, not just presence -- a caller that gets it
        backwards must not be able to compile a working call by accident.
        Same order as this lane's sibling
        ``world_sea_edge_crossing.crossing_target``.
        """
        import inspect

        self.assertEqual(
            list(
                inspect.signature(
                    trigger_response.candidate_for_trigger_id
                ).parameters
            )[:2],
            ["current_scene_id", "wire_trigger_id"],
        )


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
        #
        # WITH THE DISCRIMINATOR MEASURED, on purpose. pf-adversary measured
        # that the shipped-module version of these two tests passed because
        # TIER 3 refuses everything, so gutting tiers 1 and 2 to `return
        # None` left them green -- they were named for a guard they never
        # reached. Overriding tier 3 puts the named guard back in the path,
        # and the day a real discriminator lands they keep measuring the
        # same thing instead of turning red for an unrelated reason.
        evidence = self.measured_discriminator()
        # D7: `assertIsNone(candidate_for_trigger_id(...))` was satisfied by
        # the EMPTY production registry no matter what the guard did -- all
        # the killing power sat in the `assertIn` below. A registry POISONED
        # with a frame for every hostile row gives the first assertion teeth:
        # it can only stay None because the guard refused, not because there
        # was nothing to hand back.
        poisoned = {
            hostile: _fake(va="sub_POISON", vital_id=1, frame=b"\xde\xad")
            for hostile in self.HOSTILE
            if isinstance(hostile, Hashable)
        }
        for hostile in self.HOSTILE:
            with self.subTest(wire_trigger_id=hostile):
                self.assertIsNone(
                    trigger_response.candidate_for_trigger_id(
                        SEA, hostile, registry=poisoned, island_contact=evidence
                    )
                )
                # pf-adversary: `2.0 in (2, 3)` is True, so THE ONE ROW in
                # this sweep that is a float equal to a real id used to skip
                # its reason assertion in silence -- the single most
                # interesting row, unasserted and uncounted. The type test
                # is what the guard actually asks, so it is what this asks.
                if type(hostile) is not int or (
                    hostile not in trigger_response.CANDIDATE_TRIGGER_IDS
                ):
                    self.assertIn(
                        trigger_response.answer_guard_reason(SEA, hostile),
                        (
                            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
                            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
                        ),
                    )

    def test_no_scene_id_of_any_type_raises(self):
        evidence = self.measured_discriminator()
        # Same D7 poisoning on the scene sweep: id 3 IS registered here, so
        # every None below is the SCENE guard refusing and nothing else.
        poisoned = {3: _fake(va="sub_POISON", vital_id=1, frame=b"\xde\xad")}
        for hostile in self.HOSTILE:
            with self.subTest(current_scene_id=hostile):
                # No value of any type raises -- that is this test's name.
                answered = trigger_response.candidate_for_trigger_id(
                    hostile, 3, registry=poisoned, island_contact=evidence
                )
                if type(hostile) is int and hostile == SEA:
                    # The ONE legitimate row: it gets the poisoned frame,
                    # which is what proves the None on every other row came
                    # from the scene guard and not from an empty registry.
                    self.assertEqual(answered.va, "sub_POISON")
                else:
                    self.assertIsNone(answered)
                if hostile != trigger_response.M2_ISLAND_CONTACT_SCENE_ID or (
                    isinstance(hostile, bool)
                ):
                    self.assertIn(
                        trigger_response.answer_guard_reason(hostile, 3),
                        (
                            trigger_response.SCENE_REFUSED_NOT_AN_INT,
                            trigger_response.SCENE_REFUSED_NOT_THE_SEA_SCENE,
                        ),
                    )

    def test_the_hostile_sweep_reaches_the_named_tiers_not_just_tier3(self):
        # The control for the two tests above: with tier 3 overridden, the
        # one hostile row that is a legitimate (scene, id) pair gets THROUGH
        # the guard. If that stops being true, the sweep above has gone back
        # to being answered by something other than tiers 1 and 2.
        evidence = self.measured_discriminator()
        self.assertIsNone(trigger_response.answer_guard_reason(SEA, 2, evidence))
        self.assertIn(126, self.HOSTILE)
        self.assertIsNone(trigger_response.answer_guard_reason(126, 3, evidence))

    def test_a_registry_that_is_not_a_mapping_is_refused_by_name(self):
        evidence = self.measured_discriminator()
        for not_a_mapping in ([], "x", 7, object()):
            with self.subTest(registry=not_a_mapping):
                with self.assertRaises(TypeError) as raised:
                    trigger_response.candidate_for_trigger_id(
                        SEA, 2, registry=not_a_mapping, island_contact=evidence
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
        evidence = self.measured_discriminator()
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 7, registry=[], island_contact=evidence
            )
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
