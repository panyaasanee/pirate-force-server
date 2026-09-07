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

import re
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
from pf_preconditions import BRIDGE_SIBLING  # noqa: E402

from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_island_trigger_log as island_trigger_log,
)

SEA = trigger_response.M2_ISLAND_CONTACT_SCENE_ID

# Captured at IMPORT time, before any test class has had a chance to run, so
# the "production registry untouched" assertion below is anchored to the
# module's own import-time state rather than to whatever the previously
# executed test happened to leave behind.
REGISTRY_AT_IMPORT = dict(trigger_response._CANDIDATES)

# THE MODULE'S CONSTANT IS `None` AND STAYS `None` UNTIL THE CROSSWALK
# TICKET ANSWERS (see the module beside `ISLAND_CONTACT_DISCRIMINATOR`), so
# a test that wants through tier 3 supplies a name of its own through the
# private function's seam. It is spelled to be unmistakable in a traceback:
# nothing in the repository may ever assign this string to the module.
MEASURED = "TEST_ONLY_MEASURED_PENDING_CROSSWALK"
# The centre of `RE-289` ordinal 2's box, i.e. the position the letter
# reports as the trigger's own `pos`. Named once, here, so a test that wants
# "inside" does not carry six transcribed numbers of its own.
ORD1_CENTRE = (3098.22, 2207.49, 86.01)
ORD2_CENTRE = (-5426.19, 5129.33, 86.01)
ORD3_CENTRE = (-1916.55, -6137.92, 86.02)


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
        self._boxes_before = dict(trigger_response.ISLAND_EXTENT_BOXES)

    def tearDown(self):
        # NOTHING IS RESTORED HERE ANY MORE, because nothing can be written
        # (COO-DECISION 20260907_0945 item 1 + item 2). The old tearDown
        # cleared and rewrote `_CANDIDATES`, `ISLAND_CONTACT_DISCRIMINATOR`
        # and `ISLAND_EXTENT_BOXES` -- which made this file, as COO put it,
        # a working demonstration of the hole it was testing. It is an
        # ASSERTION now: if a test found a way to write tier-3 state, this
        # is where the file says so.
        self.assertEqual(
            dict(trigger_response._CANDIDATES),
            self._registry_before,
            "this test mutated the module's production registry",
        )
        self.assertEqual(
            dict(trigger_response.ISLAND_EXTENT_BOXES),
            self._boxes_before,
            "this test mutated the module's committed extent table",
        )
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)

    def tier3(self, reading, boxes=None):
        """Tier 3 as it will behave the day a discriminator is named, run
        against the REAL committed table unless a test hands in its own.

        The public `answer_guard_reason` cannot reach a pass on the shipped
        tree at all -- `ISLAND_CONTACT_DISCRIMINATOR` is `None` -- and no
        test may change that, which is the whole of COO-DECISION
        20260907_0945 item 1. So the pass path is exercised HERE, on the
        private function, through the seam that exists for it.
        """
        return trigger_response._tier3_contact_reason(
            reading, discriminator=MEASURED, boxes=boxes
        )

    def contact_reading(self, x=ORD2_CENTRE[0], y=ORD2_CENTRE[1], z=ORD2_CENTRE[2]):
        """A reading under the module's REAL measurement, defaulting to the
        centre of the box `RE-289` measured for `.tgr` ordinal 2.

        THIS HELPER NO LONGER PRETENDS ANYTHING. Until `RE-289` answered it
        wrote `ISLAND_CONTACT_DISCRIMINATOR` and a fake box, and that write
        is now an `AttributeError`; the measurement exists, so a test that
        wants through tier 3 uses it and stands where the letter says the
        box is.
        """
        return trigger_response.IslandContactEvidence(
            discriminator=MEASURED, x=x, y=y, z=z, source="TEST_ONLY"
        )

    def open_water_reading(self, name=None):
        """A reading from the same measurement, taken OUTSIDE every box.

        (0, 0) is the middle of the scene and is in NEITHER box: ordinal 2
        is at x -6426..-4426, ordinal 3 at y -7038..-5238.
        """
        return trigger_response.IslandContactEvidence(
            discriminator=MEASURED if name is None else name,
            x=0.0, y=0.0, z=86.0, source="TEST_ONLY",
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

    def test_the_discriminator_is_still_unmeasured_after_re289(self):
        # THE TEST THIS ROUND ALMOST DELETED. `RE-289` answered and its
        # boxes are committed below -- and the NAME is still `None`, because
        # this lane's own ticket body (`pf_bridge/tickets/RE-289.md`,
        # "what this ticket does NOT ask", item 1), the letter's nonclaim
        # (1), and this module four screens up all say the same thing: the
        # crosswalk from a `.tgr` ordinal to a wire trigger id is a separate
        # measurement and it has not been made.
        #
        # If this ever fails, somebody claimed that right. It needs the
        # crosswalk ticket behind it, not a green test.
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)
        # ...and the whole guard is therefore still shut, for every input.
        for wire_trigger_id in (2, 3):
            self.assertEqual(
                trigger_response.answer_guard_reason(
                    SEA, wire_trigger_id, self.contact_reading()
                ),
                trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
            )


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
                    trigger_response._candidate_for_trigger_id(
                        SEA, wire_trigger_id, registry=synthetic_registry
                    )
                )
        # ...and the count still reports the slots as filled, because that is
        # a different question from whether they may be answered.
        self.assertEqual(
            trigger_response._registered_count(registry=synthetic_registry), 2
        )

    def test_all_three_tiers_pass_only_together(self):
        evidence = self.contact_reading()
        # Tier 3's half is exercised on the private function, because the
        # public guard cannot pass while the discriminator is unmeasured and
        # no test may change that. Tiers 1 and 2 are exercised where a
        # caller meets them.
        self.assertIsNone(self.tier3(evidence))
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, evidence),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )
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
            trigger_response._trigger_id_guard_reason(self.Trigger.SPICE_PARADISE),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response.scene_guard_reason(self.Counted(126)),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertEqual(
            trigger_response._trigger_id_guard_reason(self.Counted(3)),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )
        # And the plain int still passes, so the pin is on SUBCLASSES, not
        # on having broken the guard for everybody.
        self.assertIsNone(trigger_response.scene_guard_reason(126))
        self.assertIsNone(trigger_response._trigger_id_guard_reason(3))

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
        evidence = self.contact_reading()
        sneaky = self.EqAlwaysTrue(999)
        self.assertEqual(
            trigger_response.answer_guard_reason(sneaky, sneaky, evidence),
            trigger_response.SCENE_REFUSED_NOT_AN_INT,
        )
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
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
                    trigger_response._trigger_id_guard_reason(value)
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
            trigger_response._trigger_id_guard_reason(True),
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
        # No save/restore of the discriminator any more: it is read-only
        # since this round, and `reimported_with` reloads the module in its
        # own `finally`, which is what puts every module-level constant back.
        seen = self.reimported_with(
            island_trigger_log,
            "M2_OBSERVED_ISLAND_TRIGGER_IDS",
            {8: 800, 9: 900},
        )
        self.assertEqual(seen["ids"], (8, 9))
        self.assertEqual(seen["registry_keys"], (8, 9))
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
        # HOW THIS TEST REACHES THE STATE NOW. It used to assign the blank
        # to the module, which is the very move item 1 of COO-DECISION
        # 20260907_0945 closed; the blank goes into the private tier-3
        # function's `discriminator` seam instead. `answer_guard_reason`
        # does not forward that seam, on purpose -- the pin below is that
        # the public entry point has no such argument at all.
        reading = self.contact_reading()
        for blank in ("", "   ", "\t", 0, object(), None):
            with self.subTest(discriminator=blank):
                self.assertEqual(
                    trigger_response._tier3_contact_reason(
                        reading, discriminator=blank
                    ),
                    trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
                )
        with self.assertRaises(TypeError):
            trigger_response.answer_guard_reason(SEA, 3, reading, discriminator="")

    def test_naming_the_discriminator_is_not_enough_on_its_own(self):
        # The one-line M2 close, refused: the name is set and a candidate is
        # registered, and the answer is still None because no session
        # reading was handed in.
        self.assertEqual(
            trigger_response._tier3_contact_reason(None, discriminator=MEASURED),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(SEA, 3, registry={3: _fake()})
        )

    def test_a_bare_truthy_value_is_not_evidence(self):
        # What a caller reaches for when it wants the guard to go away.
        for pretend in (True, 1, "yes", (MEASURED, True, "x")):
            with self.subTest(island_contact=pretend):
                self.assertEqual(
                    trigger_response._tier3_contact_reason(
                        pretend, discriminator=MEASURED
                    ),
                    trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
                )

    def test_a_reading_from_another_discriminator_is_refused_by_name(self):
        # Evidence gathered under an older measurement cannot be replayed
        # against a newer one.
        # No pretending needed now: the module enforces one real name, and
        # a reading tagged with any other name is the stale case.
        stale = trigger_response.IslandContactEvidence(
            discriminator="RE-289-ORDINAL-V1",
            x=ORD2_CENTRE[0], y=ORD2_CENTRE[1], z=ORD2_CENTRE[2],
            source="RE-289",
        )
        self.assertEqual(
            self.tier3(stale),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )

    def test_open_water_is_refused_by_its_own_name(self):
        # `RE-234` item (3)'s finding, as a named refusal: the id alone
        # cannot tell an island from open water, so the reading has to.
        open_water = self.open_water_reading()
        self.assertEqual(
            self.tier3(open_water),
            trigger_response.CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT,
        )
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
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
        evidence = self.contact_reading()
        for junk in ("10.0", None, True, [10.0]):
            with self.subTest(x=junk):
                self.assertEqual(
                    self.tier3(evidence._replace(x=junk)),
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

        evidence = self.contact_reading()
        forged = evidence._replace(discriminator=BoomStr(evidence.discriminator))
        self.assertEqual(
            self.tier3(forged),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )

    def test_an_evidence_subclass_cannot_walk_through_tier3(self):
        # Also pf-adversary against the draft: with `isinstance`, a subclass
        # overriding the fields with properties passed every check. Same
        # spelling question this file spends sixty lines on in
        # `_is_a_wire_int`, and the draft answered it the loose way.
        evidence = self.contact_reading()
        name = evidence.discriminator

        class Forged(trigger_response.IslandContactEvidence):
            @property
            def discriminator(self):  # noqa: D102
                return name

        self.assertEqual(
            self.tier3(Forged("WRONG", 10.0, 10.0, 10.0, "")),
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
        )

    def test_a_name_without_a_committed_extent_table_decides_nothing(self):
        # The refusal that stops "assign the name" from being enough even
        # with a well-formed reading in hand: RE-289 is open, so there is no
        # box to be inside of.
        evidence = self.contact_reading()
        self.assertEqual(
            self.tier3(evidence, boxes={}),
            trigger_response.CONTACT_REFUSED_NO_EXTENT_TABLE,
        )
        # And the public entry point cannot be handed a table at all.
        with self.assertRaises(TypeError):
            trigger_response.answer_guard_reason(SEA, 3, evidence, boxes={})

    def test_the_shipped_extent_table_is_exactly_what_re289_measured(self):
        # It was `{}` until this round. Every number below is re-derived here
        # from the letter's `pos` and `extent` rather than copied a second
        # time, so a typo in the module is a red test and not a wider box:
        # the arithmetic is `pos +/- extent / 2` and it is stated in the
        # module beside the table.
        expected = {}
        for ordinal, (pos, extent) in {
            1: (ORD1_CENTRE, (3000.0, 2700.0, 500.0)),
            2: (ORD2_CENTRE, (2000.0, 2000.0, 500.0)),
            3: (ORD3_CENTRE, (1800.0, 1800.0, 500.0)),
        }.items():
            expected[ordinal] = (
                pos[0] - extent[0] / 2, pos[1] - extent[1] / 2,
                pos[2] - extent[2] / 2,
                pos[0] + extent[0] / 2, pos[1] + extent[1] / 2,
                pos[2] + extent[2] / 2,
            )
        self.assertEqual(
            sorted(trigger_response.ISLAND_EXTENT_BOXES), sorted(expected)
        )
        for ordinal, box in expected.items():
            with self.subTest(ordinal=ordinal):
                # Component-wise and to six places: `pos - extent / 2` is
                # binary floating point on both sides and the module holds a
                # DECIMAL LITERAL, so exact equality here would be a test of
                # IEEE-754 rounding rather than of the transcription.
                self.assertEqual(len(trigger_response.ISLAND_EXTENT_BOXES[ordinal]), 6)
                for got, want in zip(
                    trigger_response.ISLAND_EXTENT_BOXES[ordinal], box
                ):
                    self.assertAlmostEqual(got, want, places=6)
        # Ordinals 6/7/8 and 68/69/70 are the 37.2%-on-one-axis edge walls
        # RE-289 separated out. A round that adds one has turned "touching
        # an island" into "sailing near the edge of the map".
        for wall in (6, 7, 8, 68, 69, 70):
            self.assertNotIn(wall, trigger_response.ISLAND_EXTENT_BOXES)
        # Ordinal 1 IS in the table, and the reason is a pin of its own:
        # pf-adversary measured that leaving it out was the wire-id
        # crosswalk performing the selection, in the file that says it makes
        # none. It passes the same "< 20% on both axes" bar as 2 and 3
        # (16.0% / 14.4%) and is the closest of the three to its BGFX0041
        # marker.
        self.assertIn(1, trigger_response.ISLAND_EXTENT_BOXES)

    def test_a_reading_wrong_in_two_ways_reports_the_earlier_one(self):
        # pf-adversary: swapping checks 3 and 4 inside `_tier3_contact_reason`
        # SURVIVED, because no test ever handed in a reading that was wrong
        # in two ways at once. A stale reading taken in open water must
        # report the STALE half -- the reading cannot be judged for position
        # at all until it is established which measurement it belongs to.
        stale_and_adrift = trigger_response.IslandContactEvidence(
            discriminator="RE-289-V1", x=9999.0, y=9999.0, z=9999.0, source="RE-289"
        )
        self.assertEqual(
            self.tier3(stale_and_adrift),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )
        # And with the table emptied as well, the discriminator still wins:
        # three things wrong, one answer, and it is the earliest.
        self.assertEqual(
            self.tier3(stale_and_adrift, boxes={}),
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
        )

    def test_the_five_tier3_refusals_are_five_different_strings(self):
        reasons = (
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
            trigger_response.CONTACT_REFUSED_NO_EVIDENCE_SUPPLIED,
            trigger_response.CONTACT_REFUSED_EVIDENCE_OF_ANOTHER_DISCRIMINATOR,
            trigger_response.CONTACT_REFUSED_NO_EXTENT_TABLE,
            trigger_response.CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT,
        )
        self.assertEqual(len(set(reasons)), 5)
        for reason in reasons:
            with self.subTest(reason=reason):
                self.assertTrue(reason.startswith("CONTACT_REFUSED_"))

    def test_tier3_runs_after_tier1_and_tier2_not_before(self):
        # Order pin in the new direction: a wrong scene with GOOD evidence
        # still reports the scene, not the contact.
        evidence = self.contact_reading()
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
        for hostile in (None, object(), [], b"\x01", 2.0, {"x": 1.0}):
            with self.subTest(island_contact=hostile):
                self.assertEqual(
                    trigger_response._tier3_contact_reason(
                        hostile, discriminator=MEASURED
                    ),
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


class ThreeMutantsPfAdversaryWalkedThroughTests(M2RegistryIsolation):
    """The three survivors round `rsskp1` recorded and did not kill, plus
    the one it created.  Each test here is red on exactly one mutant.

    Recorded because a surviving mutant carried forward across rounds
    stops being a measurement and becomes a habit.
    """

    def test_the_reading_has_no_optional_field(self):
        """Mutant: ``source: str`` -> ``source: str = ""``.

        A default turns "the reading says where it came from" into "the
        reading MAY say where it came from", and every existing test still
        passes because they all fill it.  What breaks is the contract:
        an evidence object with no provenance would satisfy tier 3.
        """
        self.assertEqual(
            trigger_response.IslandContactEvidence._field_defaults, {}
        )
        with self.assertRaises(TypeError):
            trigger_response.IslandContactEvidence("d", 1.0, 1.0, 1.0)

    def test_registered_count_counts_not_none_not_truthiness(self):
        """Mutant: ``if table.get(i) is not None`` -> ``if table.get(i)``.

        No ``CandidateFrame`` this module composes is ever falsy, so only a
        hostile registry separates the two spellings -- which is exactly
        why the mutant survived.  The docstring promises "not None", so
        that is what is pinned.
        """
        self.assertEqual(
            trigger_response._registered_count(registry={2: 0, 3: None}), 1
        )

    def test_a_malformed_extent_row_is_skipped_not_unpacked(self):
        """pf-adversary: a five-field typo in ``ISLAND_EXTENT_BOXES`` raised
        ``ValueError: not enough values to unpack`` out of
        ``candidate_for_trigger_id``, whose caller is promised a named
        refusal and never an exception.  `RE-289`'s answer arrives as
        hand-transcribed floats, so this is the likely typo, not an exotic
        one.  A good row alongside a bad one must still work.
        """
        reading = self.contact_reading(5.0, 5.0, 5.0)
        self.assertEqual(
            self.tier3(reading, boxes={1: (0.0, 0.0, 0.0, 10.0, 10.0)}),
            trigger_response.CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT,
        )
        self.assertIsNone(
            self.tier3(
                reading,
                boxes={
                    1: (0.0, 0.0, 0.0, 10.0, 10.0),
                    2: (0.0, 0.0, 0.0, 10.0, 10.0, 10.0),
                },
            )
        )
        # pf-adversary C7: the seam this round ADDED repeated the defect the
        # `registry` seam already has a named constant for -- a non-mapping
        # died with a bare `AttributeError` from `.values()`.
        for junk in ([1, 2], "xx", 7):
            with self.subTest(boxes=junk):
                with self.assertRaises(TypeError) as raised:
                    self.tier3(reading, boxes=junk)
                self.assertEqual(
                    str(raised.exception),
                    trigger_response.EXTENT_TABLE_REFUSED_NOT_A_MAPPING,
                )

    def test_the_module_side_discriminator_refuses_a_str_subclass(self):
        """pf-adversary, THIRD sighting of the same bug, this time against
        this round's own committed head.

        The first two sightings were on the READING's side and were fixed
        with ``type(...) is``.  Step 1 -- the MODULE CONSTANT's side -- was
        still ``isinstance``, so a ``str`` subclass assigned to
        ``ISLAND_CONTACT_DISCRIMINATOR`` reached the ``!=`` at step 3; and
        because Python tries the RIGHT operand's ``__ne__`` first when its
        type subclasses the left's, that subclass's ``__ne__`` ran.  A
        subclass that raises there falsified this function's "never raises"
        promise from the one side both earlier fixes had not looked at.

        Not wire-reachable today (the constant is ``None``).  Armed for the
        round that answers `RE-289`, where a named measurement is exactly
        the shape a ``str`` subclass would arrive in.
        """

        class Boom(str):
            def __ne__(self, other):
                raise ValueError("the module side must never reach here")

            def __eq__(self, other):
                raise ValueError("the module side must never reach here")

            def __hash__(self):
                return 0

        reading = trigger_response.IslandContactEvidence(
            "bg3001_extent", 1.0, 1.0, 1.0, "attended"
        )
        self.assertEqual(
            trigger_response._tier3_contact_reason(
                reading, discriminator=Boom("bg3001_extent")
            ),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )
        # ...and the module's own constant is a plain `str`, so the shipped
        # tree never takes that path at all. The check above is what keeps
        # it that way when a later round transcribes a new measurement.
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)


class TheCrosswalkIsMeasuredNotAssertedTests(M2RegistryIsolation):
    """The SECOND measurement the module has been demanding for three rounds:
    the boxes came out of `Bg3001.tgr`, the points came off the wire and the
    screen in `GT-228`/R308, neither derived from the other, and they agree.

    This class does not let the module grade its own homework. Every number
    is re-derived here from the two committed tables, and the containment is
    recomputed rather than read out of a stored answer."""

    def bridge(self):
        """The bridge checkout, AFTER the caller has run the precondition.

        Duplicated from `TheTableCitesItsLetterTests` rather than shared,
        for the reason that class already states: `tests/test_pytest_
        precondition_census.py` counts guards by reading each test method's
        SOURCE, so a `require()` one call deeper counts as zero and the pin
        file then disagrees with the census.
        """
        import os

        env = os.environ.get("PF_BRIDGE_DIR")
        if env and Path(env).is_dir():
            return Path(env)
        return BRIDGE_SIBLING.paths[0]

    def _inside(self, box, x, y, z):
        x0, y0, z0, x1, y1, z1 = box
        return x0 <= x <= x1 and y0 <= y <= y1 and z0 <= z <= z1

    def test_every_observation_lands_in_the_box_of_its_own_wire_id(self):
        boxes = trigger_response.ISLAND_EXTENT_BOXES
        observations = trigger_response.M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS
        # The claim is BOTH halves: in its own ordinal's box, and in no
        # other. Only the second half rules out boxes so large they contain
        # everything, which is the failure mode `RE-289` was written to
        # detect in the first place.
        for label, wire_id, x, y, z in observations:
            containing = sorted(
                ordinal
                for ordinal, box in boxes.items()
                if self._inside(box, x, y, z)
            )
            with self.subTest(observation=label):
                self.assertEqual(containing, [wire_id])

    def test_the_crosswalk_covers_both_ids_and_all_thirteen_points(self):
        # A mutant that empties the table, or keeps only the rows of one
        # island, passes the containment test above vacuously.
        observations = trigger_response.M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS
        self.assertEqual(len(observations), 13)
        self.assertEqual(
            sorted({wire_id for _, wire_id, _, _, _ in observations}), [2, 3]
        )
        # Three independent SOURCES, not thirteen readings of one thing: the
        # frame's own trigger position, the ship position in the same frame,
        # and what the HUD showed the observer. If a later round trims this
        # to one source the crosswalk stops being a crosswalk.
        labels = [label for label, _, _, _, _ in observations]
        self.assertTrue(any(name.endswith("trigger") for name in labels))
        self.assertTrue(any(name.endswith("ship") for name in labels))
        self.assertTrue(any(name.startswith("HUD") for name in labels))

    def test_the_crosswalk_would_notice_if_the_two_islands_were_swapped(self):
        # THE KILLER FOR "the boxes are so big they contain everything".
        # Relabel each observation with the OTHER island's id and the whole
        # table must fail, every row of it. Measured, not asserted: this
        # test failed to be worth writing until it was run, because a table
        # of scene-wide boxes passes the test above just as happily.
        boxes = trigger_response.ISLAND_EXTENT_BOXES
        swap = {2: 3, 3: 2}
        for label, wire_id, x, y, z in (
            trigger_response.M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS
        ):
            with self.subTest(observation=label):
                self.assertFalse(self._inside(boxes[swap[wire_id]], x, y, z))

    def test_the_letter_behind_the_crosswalk_is_on_the_bridge(self):
        # COO-DECISION `20260907_0945` item 3, applied to this table the
        # same way it is applied to the extent table: a table with no letter
        # behind it is a tier-3 refusal, not a pass with a warning. Skipped
        # rather than failed where the bridge is not a sibling, which is the
        # shape every other bridge-reading test in this repo uses.
        BRIDGE_SIBLING.require(self)
        letter = (
            self.bridge()
            / "notes_to_chief"
            / trigger_response.M2_WIRE_ORDINAL_CROSSWALK_LETTER
        )
        self.assertTrue(letter.is_file(), letter)
        text = letter.read_text(encoding="utf-8", errors="replace")
        # Not merely that the file exists -- that it carries the numbers
        # this module copied out of it. Two spot values, one per island,
        # spelled as the letter spells them.
        self.assertIn("-4451.6", text)
        self.assertIn("-1720.4", text)
        self.assertIn("OBSERVER_CONFIRMED", text)

    def test_the_name_resolution_rows_cannot_separate_contact_from_open_water(
        self,
    ):
        # COO-DECISION `20260907_1245` item 2 handed this lane one row --
        # `id=35 name=Thorn Flower PROP no_responder bytes_out=0`, the
        # open-water frame -- as supporting evidence, with "do NOT use it to
        # fill the name" attached. This test is what makes that instruction
        # mechanical instead of a sentence somebody has to remember.
        #
        # The letter's next two lines say the CONTACT frames resolved the
        # same way. So the columns are constant across all three ids and the
        # table separates nothing. If a later round edits a row so that the
        # open-water id looks different from the contact ids, this test goes
        # red and sends it back to the letter rather than letting a table
        # quietly grow into a classifier.
        rows = trigger_response.M2_WIRE_ORDINAL_CROSSWALK_NAME_RESOLUTION
        self.assertEqual(len(rows), 3)
        self.assertEqual(sorted(row[0] for row in rows), [2, 3, 35])
        # Column 1 (the client's own name for the id) is the only one that
        # differs; every other column is identical for the open-water frame
        # and for both contact frames.
        self.assertEqual({row[2] for row in rows}, {"PROP"})
        self.assertEqual({row[3] for row in rows}, {"no_responder"})
        self.assertEqual({row[4] for row in rows}, {0})
        self.assertEqual(len({row[1] for row in rows}), 3)

        open_water = [row for row in rows if row[0] == 35]
        self.assertEqual(len(open_water), 1)
        contact = [row for row in rows if row[0] in (2, 3)]
        self.assertEqual(len(contact), 2)
        # Stated as the property, not as three separate equalities: no
        # column after the name tells the two populations apart.
        for row in contact:
            with self.subTest(contact_id=row[0]):
                self.assertEqual(row[2:], open_water[0][2:])

    def test_the_discriminator_is_still_unnamed_after_all_of_this(self):
        # THE POINT OF THE WHOLE ROUND, PINNED. Delivering the second
        # measurement is not the same act as deciding to act on it. Three
        # documents route that decision through a crosswalk ticket and this
        # lane does not get to shortcut them because the evidence came in
        # early. If a later round fills the name, this test is the line it
        # has to walk up to and delete on purpose.
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)


class FieldOrderIsTheContractTests(M2RegistryIsolation):
    """pf-adversary D3: `CandidateFrame`'s field ORDER was unpinned --
    swapping `va` and `vital_id` in the NamedTuple left 42 tests passing,
    because every test in this file builds it with keywords. The module's one
    job is to carry three values from a LANE-UI letter UNCHANGED, and the
    obvious way a letter gets typed in is POSITIONALLY."""

    def test_the_third_positional_argument_is_the_evidence_and_reaches_tier3(self):
        # THIS TEST CHANGED SHAPE THIS ROUND, AND WHY IS THE POINT OF IT.
        # It used to assert that `candidate_for_trigger_id(126, 3, evidence)`
        # RAISES: with the test-only `registry` sitting third and positional,
        # a caller MEANING to pass evidence had it land in `registry` and got
        # a silent `None` -- no error, no warning, no way to notice -- so a
        # `*` was put in front of both optional arguments to turn that into a
        # TypeError at the call.
        #
        # Closing pf-adversary's C6 deleted the hazard rather than guarding
        # it. `registry` is not on this function any more, so the third
        # positional argument IS `island_contact` and there is no longer a
        # wrong slot for it to land in. Asserting the old TypeError now would
        # be pinning a guard against a parameter that does not exist.
        #
        # What replaces it is the property the `*` was buying: a reading
        # passed POSITIONALLY reaches tier 3 and is judged, rather than being
        # swallowed. Both spellings must agree, and both must agree with
        # `answer_guard_reason`, which is where the reading is actually
        # ruled on. The mutant this kills is a body that accepts
        # `island_contact` and forwards `None`.
        evidence = self.contact_reading()
        positional = trigger_response.candidate_for_trigger_id(SEA, 3, evidence)
        keyword = trigger_response.candidate_for_trigger_id(
            SEA, 3, island_contact=evidence
        )
        self.assertIsNone(positional)
        self.assertIsNone(keyword)
        # ...and the reading really did travel: the tier-3 refusal the
        # module gives for THIS reading is the unmeasured-discriminator one,
        # not the "no evidence supplied" one a dropped argument would earn.
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3, evidence),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 3),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )

    def test_the_public_lookup_forwards_all_three_arguments_it_is_given(self):
        # THIS LANE FOUND THIS ONE AGAINST ITS OWN DRAFT, BEFORE PUSHING.
        # Closing C6 turned `candidate_for_trigger_id` into a one-line
        # delegation to `_candidate_for_trigger_id`, and a delegation can
        # drop an argument. Mutating the body to
        # `return _candidate_for_trigger_id(current_scene_id, wire_trigger_id)`
        # -- island_contact silently discarded -- left the WHOLE FILE GREEN:
        # 83 passed. Nothing behavioural can see it, and that is not an
        # oversight in the suite, it is structural: tier 3 refuses at step 1
        # on the unmeasured `ISLAND_CONTACT_DISCRIMINATOR` BEFORE it ever
        # looks at the reading, so on the shipped tree a dropped reading and
        # a delivered one produce the identical `None`. The day a
        # discriminator is measured, that mutant becomes a lookup that
        # answers the world while ignoring the evidence -- which is tier 3
        # deleted, silently, with the tests still green.
        #
        # So the forwarding is pinned from the COMPILED CODE, not from
        # behaviour and not from the source text: each parameter must
        # actually be LOADED in the body. A docstring or comment naming it
        # produces no instruction; a dropped forward produces no load.
        # pf-adversary D3 AGAINST THE FIRST VERSION OF THIS TEST: checking
        # that each name is LOADED proves PRESENCE, not POSITION. Swapping
        # `current_scene_id` and `wire_trigger_id` in the delegation left
        # the whole file green -- and on a simulated next round (a named
        # discriminator, a cited frame in a slot, a real in-box reading) the
        # swapped module answers `None` for every input forever, i.e. M2
        # silently never ships, with 84 tests passing. So the ORDER of the
        # loads is checked too, not just the set.
        #
        # pf-adversary D5, same review: the loop was two hand-typed names
        # with no non-vacuity assertion, so narrowing it to `()` dropped
        # seven subtests and stayed green. The functions are DISCOVERED now
        # and the discovery is pinned, the way the seam pin already does it.
        #
        # AND THE VERSION ABOVE READ THE BYTECODE, WHICH CLOSED THE WINDOWS
        # GATE ON THIS LANE FOR A WHOLE ROUND.  It collected the operands of
        # `LOAD_FAST` and `LOAD_FAST_BORROW`.  CPython 3.14 -- which is what
        # `gate-windows.yml` pins (`python-version: '3.14'`), while a cloud
        # clone runs 3.11 -- compiles two adjacent local reads into ONE
        # superinstruction, `LOAD_FAST_BORROW_LOAD_FAST_BORROW`, whose
        # `argval` is the TUPLE `('current_scene_id', 'wire_trigger_id')`.
        # Neither name is then in `loads` at all, so this test failed four
        # ways on 3.14 while passing on 3.11:
        #
        #     AssertionError: 'current_scene_id' not found in ['island_contact']
        #
        # That is what turned `pirate-force-server#1026` red and got it
        # closed by the automerge workflow (run 34086718298, step
        # `pytest_subset` exit=1), with no FAILED line anywhere in the job
        # log because `-q -rs` prints the skip report and the closer's grep
        # only looks for `^FAILED `.
        #
        # THE LESSON IS NOT "ADD THE THIRD OPNAME".  The set of
        # superinstructions is a CPython implementation detail that changes
        # every release; a pin written against it is a pin that reddens the
        # gate on the next upgrade, on a runner this lane does not control.
        # The property this test actually wants -- "the delegation puts each
        # argument in the slot it declares" -- is a property of the SOURCE
        # STRUCTURE, so it is read from the `ast` instead.  The `ast` is
        # stable across releases, and it keeps the reason the bytecode was
        # chosen over `in source` in the first place: a comment or a
        # docstring naming a parameter produces no `ast.Name` node, exactly
        # as it produced no instruction.
        #
        # Measured sweep before choosing: `grep -rn LOAD_FAST tests/ tools/
        # src/` returns exactly ONE line, the one deleted here.  No other
        # lane carries this trap today.
        import ast
        import inspect
        import textwrap

        delegations = {
            "candidate_for_trigger_id": trigger_response.candidate_for_trigger_id,
            "_candidate_for_trigger_id": trigger_response._candidate_for_trigger_id,
            # D4: `registered_count` lost ALL behavioural coverage in the
            # split -- six tests moved to the private twin and none replaced
            # them, so `def registered_count(): return 0` passed the file.
            # It cannot be caught behaviourally (the production count really
            # is 0), so it is caught here: the public one must load its twin.
            "registered_count": trigger_response.registered_count,
            "_registered_count": trigger_response._registered_count,
        }
        self.assertEqual(len(delegations), 4)

        for name, function in delegations.items():
            tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
            self.assertIsInstance(tree.body[0], ast.FunctionDef)
            # The BODY only. Parameter names in the `def` line are
            # `ast.arg`, not `ast.Name`, so they cannot satisfy this on
            # their own -- declaring a parameter is not forwarding it.
            reads = [
                node
                for statement in tree.body[0].body
                for node in ast.walk(statement)
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
            ]
            # `ast.walk` is breadth-first, so it is NOT source order. Sort by
            # position to get the order a reader sees, which is the order a
            # transposition reverses.
            reads.sort(key=lambda node: (node.lineno, node.col_offset))
            loads = [node.id for node in reads]
            parameters = list(inspect.signature(function).parameters)
            for parameter in parameters:
                with self.subTest(function=name, parameter=parameter):
                    self.assertIn(parameter, loads)
            # ORDER, not just membership: the parameters this function
            # forwards must appear in the body in the order it declares
            # them. A transposition reverses two of these.
            # FIRST occurrence of each, because a parameter may legitimately
            # be read more than once (`wire_trigger_id` is used again for
            # the table lookup); it is the order they are first reached in
            # that a transposition reverses.
            first_use = []
            for one in loads:
                if one in parameters and one not in first_use:
                    first_use.append(one)
            with self.subTest(function=name, check="order"):
                self.assertEqual(
                    [one for one in parameters if one in first_use], first_use
                )

        # The two public functions must be delegating, not reimplementing:
        # each names its own private twin in its body.
        self.assertIn(
            "_candidate_for_trigger_id",
            trigger_response.candidate_for_trigger_id.__code__.co_names,
        )
        self.assertIn(
            "_registered_count",
            trigger_response.registered_count.__code__.co_names,
        )

    def test_the_public_lookup_has_exactly_three_parameters(self):
        # The other half of what the deleted `*` was holding: nothing may be
        # appended to this signature and reached positionally. Three, in this
        # order, and the test-only seam is not among them.
        import inspect

        self.assertEqual(
            list(
                inspect.signature(
                    trigger_response.candidate_for_trigger_id
                ).parameters
            ),
            ["current_scene_id", "wire_trigger_id", "island_contact"],
        )
        self.assertEqual(
            list(
                inspect.signature(trigger_response.registered_count).parameters
            ),
            [],
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
        # WHY THIS ASKS `_table_for` AND NOT `candidate_for_trigger_id`.
        # The public lookup cannot return a frame on the shipped tree at
        # all -- tier 3 refuses on the unmeasured discriminator before the
        # registry is touched -- and since COO-DECISION 20260907_0945 item 1
        # no test may write the discriminator to get past that. So the
        # pass-through is pinned where it lives, and the refusal that stands
        # in front of it is pinned separately, below.
        evidence = self.contact_reading()
        fake = _fake()
        synthetic_registry = {2: fake, 3: None}

        self.assertEqual(
            trigger_response.answer_guard_reason(SEA, 2, evidence),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
                SEA, 2, registry=synthetic_registry, island_contact=evidence
            )
        )

        result = trigger_response._table_for(synthetic_registry).get(2)

        self.assertIs(result, fake)
        self.assertEqual(result.va, "sub_DEADBEEF")
        self.assertEqual(result.vital_id, 0xC723)
        self.assertEqual(result.frame, b"\x12\x34\x56")

    def test_the_other_id_in_the_same_synthetic_registry_stays_none(self):
        evidence = self.contact_reading()
        synthetic_registry = {2: _fake(), 3: None}

        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
                SEA, 3, registry=synthetic_registry, island_contact=evidence
            )
        )

    def test_registered_count_reads_the_registry_it_is_given(self):
        synthetic_registry = {2: _fake(), 3: None}

        self.assertEqual(
            trigger_response._registered_count(registry=synthetic_registry), 1
        )

    def test_registered_count_reads_an_empty_registry_as_empty(self):
        # pf-adversary D6, second survivor: `_table_for(registry)` mutated to
        # `_table_for(registry) or _CANDIDATES` survived, because no test
        # ever handed in a FALSY mapping. An empty dict is a legitimate
        # registry that says "nothing registered" -- it must not silently
        # fall back to the module's own table.
        self.assertEqual(trigger_response._registered_count(registry={}), 0)
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(SEA, 2, registry={})
        )
        # HOW THE MUTANT IS KILLED NOW. It used to be killed by writing a
        # candidate into the production table so the fallback would give a
        # different answer -- which COO-DECISION 20260907_0945 item 1 made
        # impossible, and item 2 says the suite should not have been doing
        # in the first place. `_table_for` is asked directly instead: the
        # empty mapping it is handed is the mapping it must return, BY
        # IDENTITY, and `x or _CANDIDATES` cannot satisfy that.
        empty = {}
        self.assertIs(trigger_response._table_for(empty), empty)
        self.assertIs(trigger_response._table_for(None), trigger_response._CANDIDATES)

    def test_registered_count_is_scoped_to_candidate_trigger_ids(self):
        # Mutant killer: `sum(... for trigger_id in table)` reads identically
        # and is wrong -- an entry for an id this slot is not for must count
        # for nothing, the same way the lookup refuses it.
        off_slot_only = {7: _fake(va="sub_NOT_M2")}
        self.assertEqual(trigger_response._registered_count(registry=off_slot_only), 0)

        mixed = {7: _fake(va="sub_NOT_M2"), 3: _fake()}
        self.assertEqual(trigger_response._registered_count(registry=mixed), 1)


class RegistryTypeDisagreementTests(M2RegistryIsolation):
    """The three plausible "is this a registry" predicates agree on every easy
    input and disagree on exactly two. Both are pinned, so `isinstance(...,
    Mapping)` cannot silently become `dict` or `hasattr(..., "get")`."""

    def test_a_read_only_mapping_that_is_not_a_dict_is_accepted(self):
        evidence = self.contact_reading()
        fake = _fake()
        proxy = types.MappingProxyType({2: fake, 3: None})

        # `registered_count` validates its registry UNCONDITIONALLY, so it
        # is the entry point that can still separate the three predicates
        # while tier 3 refuses every lookup.
        self.assertIs(trigger_response._table_for(proxy), proxy)
        self.assertEqual(trigger_response._registered_count(registry=proxy), 1)

    def test_an_object_that_merely_owns_a_get_is_refused_by_name(self):
        evidence = self.contact_reading()

        class NotAMappingButHasGet:
            def get(self, key, default=None):  # pragma: no cover - never called
                return "wrong"

        # `candidate_for_trigger_id` is NOT in this list any more: the
        # three tiers are checked before the registry is touched, and tier 3
        # refuses every input while the discriminator is unmeasured, so the
        # raise is not reachable through it on the shipped tree. It used to
        # be reachable here only because the test wrote the discriminator.
        # `_table_for` is where the predicate lives and `registered_count`
        # validates unconditionally, so both spellings stay pinned.
        for callable_under_test in (
            trigger_response._table_for,
            lambda r: trigger_response._registered_count(registry=r),
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
            trigger_response._trigger_id_guard_reason(7),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )

    def test_a_non_m2_trigger_id_returns_no_candidate_even_if_registered(self):
        # Even a poisoned synthetic registry that DOES carry an entry for a
        # non-M2 id must not be answered -- this slot is only ever for 2/3 --
        # and that holds even with tier 3 satisfied.
        evidence = self.contact_reading()
        poisoned_registry = {7: _fake(va="sub_NOT_M2", vital_id=1, frame=b"\x00")}
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
                SEA, 7, registry=poisoned_registry, island_contact=evidence
            )
        )

    def test_a_non_int_trigger_id_is_named_refused(self):
        self.assertEqual(
            trigger_response._trigger_id_guard_reason("2"),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )

    def test_a_bool_trigger_id_is_named_refused(self):
        # bool subclasses int in Python; True == 1 must not pass as trigger
        # id 1 (which is not one of CANDIDATE_TRIGGER_IDS anyway, but the
        # refusal must be the TYPE reason, not the membership reason).
        self.assertEqual(
            trigger_response._trigger_id_guard_reason(True),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )

    def test_tier2_id_is_a_candidate_agrees_with_the_guard(self):
        self.assertTrue(trigger_response._tier2_id_is_a_candidate(2))
        self.assertTrue(trigger_response._tier2_id_is_a_candidate(3))
        self.assertFalse(trigger_response._tier2_id_is_a_candidate(7))
        self.assertFalse(trigger_response._tier2_id_is_a_candidate("2"))

    def test_no_public_name_answers_candidacy_from_the_wire_id_alone(self):
        """`COO-DECISION 20260907_0405` item 1: no overload that takes the
        trigger id by itself.  THE ALLOWLIST IS GONE; the rule now has no
        exceptions.

        pf-adversary, run against the round that shipped the three tiers,
        found the file breaking that rule while claiming to keep it: a public
        ``is_candidate_trigger_id(wire_trigger_id)`` sat one import line away
        from the guard, its own docstring offering itself to "a caller that
        only ever needed yes/no".  That name was made private -- and the
        round that did it left ``trigger_id_guard_reason``, a SECOND public
        id-only name, standing, and passed this test by writing that name
        into an ``allowed_id_only`` set.  An allowlist entry does not close a
        door; it makes one offender legal and leaves the door open, and the
        next offender only has to be added to the set.  Both names are
        private now and the set is deleted.

        TWO PRONGS, both mechanical, neither one a name:

        1. SHAPE.  A public callable defined in this module that takes ANY
           caller-supplied value must be TIER-ORDERED: ``current_scene_id``
           first.  "Any caller-supplied value" now means EVERY parameter,
           with no exceptions at all.  It used to carry one -- ``registry``,
           "this module's one test-only seam" -- and pf-adversary's C6
           against `pirate-force-server#1015` was that the seam it excused
           was a PUBLIC keyword handing in the whole candidate table, which
           is the one input the three tiers exist to withhold.  The seam
           moved to ``_candidate_for_trigger_id`` and ``_registered_count``
           and the exemption is deleted, which is the same move this
           docstring already describes two paragraphs up for
           ``allowed_id_only``: the door, not the offender.  This prong does
           not read the parameter's NAME for the id either, so
           re-introducing the offender as ``f(trig)`` or ``f(n)`` does not
           slip past it -- the previous spelling only looked for the literal
           ``wire_trigger_id`` and would have.
        2. REACH.  A public callable that is not tier-ordered must not be
           able to consult the deciding predicates at all.  Measured from the
           code object (recursively, so a nested function or comprehension
           cannot hide the call), not from the source text.

        ``registered_count()`` is the one public callable that is not
        tier-ordered, and since C6 was closed it passes both prongs on the
        strongest shape there is: it takes NO parameters, so there is
        nothing a caller can hand it at all, and it reaches none of the
        three predicates.  Before this round its one parameter was the
        registry, which is why the exemption above existed.
        """
        import functools
        import inspect
        import types as _types

        DECIDERS = {
            "_trigger_id_guard_reason",
            "_tier2_id_is_a_candidate",
            "answer_guard_reason",
            "CANDIDATE_TRIGGER_IDS",
        }
        TIER_1 = "scene_guard_reason"

        def reachable_names(code):
            found = set(code.co_names)
            for const in code.co_consts:
                if isinstance(const, _types.CodeType):
                    found |= reachable_names(const)
            return found

        def bodies(obj, depth=0):
            """Every code object a caller reaches by CALLING ``obj``.

            Not ``inspect.isfunction`` and not ``__module__``: pf-adversary
            walked four shapes straight past both of those -- a public
            INSTANCE with ``__call__`` (``vars(instance)`` is empty), a
            ``functools.partial`` (no ``__module__`` at all), a module-level
            ``staticmethod``, and a re-export from a sibling module (whose
            ``__module__`` is the sibling's).  Each one handed a caller
            ``module.name(3)`` -- one import line, one argument -- which is
            the exact shape RE-234 item (3) exists to forbid.
            """
            if depth > 4:
                return []
            if isinstance(obj, (staticmethod, classmethod)):
                return bodies(obj.__func__, depth + 1)
            if isinstance(obj, functools.partial):
                return bodies(obj.func, depth + 1)
            wrapped = getattr(obj, "__wrapped__", None)
            if wrapped is not None:
                return bodies(wrapped, depth + 1)
            if inspect.isfunction(obj) or inspect.ismethod(obj):
                return [obj.__code__]
            if inspect.isclass(obj):
                out = []
                for member in vars(obj).values():
                    out += bodies(member, depth + 1)
                return out
            call = getattr(type(obj), "__call__", None)
            if inspect.isfunction(call):
                return bodies(call, depth + 1)
            return []

        def parameters_of(obj):
            try:
                return list(inspect.signature(obj).parameters)
            except (TypeError, ValueError):
                return []

        CANDIDATES = (2, 3)
        # All ints, and 126 -- the sea scene id -- is deliberately among
        # them: an oracle for CANDIDACY must lump the sea scene in with the
        # other non-candidates, while `scene_guard_reason`, which answers
        # tier 1 honestly, singles 126 out.  That is what separates a
        # forbidden id-only classifier from the guard the module is allowed
        # to expose, and it is measured rather than assumed.
        NON_CANDIDATES = (7, 126, 1, 0)

        def answers_from_one_argument(obj):
            """Does calling ``obj`` with ONE argument separate the two
            candidate wire ids from everything else?

            This is the property itself rather than a proxy for it, so no
            signature trick evades it: a ``functools.partial``, an instance
            with ``__call__``, a re-export from a sibling module, a
            differently-named parameter, or a keyword-only parameter with a
            default all get called here the same way.  A callable that
            raises, or that answers the same thing for both groups, is not
            an oracle.
            """
            def answer(value):
                try:
                    return ("ok", obj(value))
                except Exception as exc:  # noqa: BLE001 - raising is a pass
                    return ("raised", type(exc).__name__)

            yes = [answer(value) for value in CANDIDATES]
            no = [answer(value) for value in NON_CANDIDATES]
            if any(one[0] != "ok" for one in yes):
                return False
            return (
                len(set(yes)) == 1
                and len(set(no)) == 1
                and yes[0] != no[0]
            )

        not_tier_ordered = []
        tier_ordered_in_name_only = []
        can_reach_a_decider = []
        answers_the_id_alone = []
        for name, obj in vars(trigger_response).items():
            if name.startswith("_") or not callable(obj):
                continue
            if answers_from_one_argument(obj):
                answers_the_id_alone.append(name)
            if inspect.isclass(obj):
                # Constructing a reading is not answering candidacy; the
                # behaviour prong above already covers being CALLED.
                continue
            if getattr(obj, "__module__", None) != trigger_response.__name__:
                # An imported name (``NamedTuple`` itself, say).  The SHAPE
                # and REACH prongs are claims about what THIS module wrote;
                # a re-export is covered by the behaviour prong above,
                # which does not filter on ``__module__`` at all -- that
                # filter is precisely how pf-adversary walked a sibling's
                # function out of this namespace under a new name.
                continue
            code_objects = bodies(obj)
            if not code_objects:
                continue
            params = parameters_of(obj)
            # NO EXEMPTIONS. This line read
            # `[p for p in params if p != "registry"]` until this round --
            # an allowlist entry, in the test whose own docstring six
            # screens up explains that an allowlist entry does not close a
            # door, it makes one offender legal. pf-adversary's C6 was that
            # the offender it legalised was a public keyword handing in the
            # whole candidate table. `registry` is off the public functions
            # now, so the exemption has nothing left to exempt and is gone
            # rather than left standing for the next parameter to reuse.
            takes_a_value = list(params)
            tier_ordered = params[:1] == ["current_scene_id"]
            reaches = set()
            for code in code_objects:
                reaches |= reachable_names(code)
            # TRANSITIVE, over this module's own names.  One level is not
            # enough: `candidate_for_trigger_id` reaches tier 1 THROUGH
            # `answer_guard_reason`, and a future offender would reach a
            # decider through one hop just as easily.
            frontier, seen = set(reaches), set()
            while frontier:
                hop = frontier.pop()
                if hop in seen:
                    continue
                seen.add(hop)
                target = getattr(trigger_response, hop, None)
                if inspect.isfunction(target) and (
                    target.__module__ == trigger_response.__name__
                ):
                    found = reachable_names(target.__code__)
                    reaches |= found
                    frontier |= found - seen
            if takes_a_value and not tier_ordered:
                not_tier_ordered.append(name)
            if tier_ordered and TIER_1 not in reaches and name != TIER_1:
                # D1, and it was THIS round's own regression: the first
                # version of this test said ``if tier_ordered: continue``,
                # so a function had only to SPELL ``current_scene_id``
                # first and could then ignore it and answer from the id
                # alone.  Being tier-ordered is a claim about the BODY, so
                # the body is what gets checked.
                tier_ordered_in_name_only.append(name)
            if not tier_ordered and takes_a_value and reaches & DECIDERS:
                # ``registered_count`` is the one public callable that is
                # not tier-ordered.  It is exempt HERE by its SHAPE, not by
                # its name and not by an allowlist: it takes no parameters
                # since C6 was closed, so `takes_a_value` is empty and no
                # caller can hand it a wire id -- and the behaviour prong
                # above, which does not read signatures at all, calls it
                # with an id anyway and measures that it is not an oracle.
                can_reach_a_decider.append(name)

        self.assertEqual(answers_the_id_alone, [])
        self.assertEqual(not_tier_ordered, [])
        self.assertEqual(tier_ordered_in_name_only, [])
        self.assertEqual(can_reach_a_decider, [])

    def test_the_private_guards_are_still_private(self):
        """The rename is the fix, so it gets its own pin: both id-only
        deciders answer under a leading underscore and under no other name.

        Without this, a future round could satisfy the test above by
        DELETING ``_trigger_id_guard_reason`` and inlining its two refusals
        into ``answer_guard_reason`` -- green, and the named-refusal contract
        the rest of this file rests on would be gone.  So the pin is on the
        private names existing and answering, not merely on the public
        surface being clean.
        """
        self.assertFalse(hasattr(trigger_response, "trigger_id_guard_reason"))
        self.assertFalse(hasattr(trigger_response, "is_candidate_trigger_id"))
        self.assertIsNone(trigger_response._trigger_id_guard_reason(2))
        self.assertEqual(
            trigger_response._trigger_id_guard_reason(7),
            trigger_response.TRIGGER_ID_REFUSED_NOT_M2,
        )
        self.assertEqual(
            trigger_response._trigger_id_guard_reason("2"),
            trigger_response.TRIGGER_ID_REFUSED_NOT_AN_INT,
        )

    def test_the_seam_paragraph_cites_anchors_that_still_exist(self):
        """The module's SEAM paragraph describes a place in ``runtime.py``.
        It used to describe it by LINE NUMBER, four times, and all four had
        rotted: ``8692`` had become a bare ``)``, ``8676`` an assignment,
        ``8634``/``8641`` two unrelated ``if`` statements, and ``4419`` a
        scene comparison in the GM warp code.  A citation that silently stops
        pointing at its subject is worse than none, because the next reader
        follows it and believes what they find.

        So the citations are STRINGS now, and this test is what keeps them
        honest: each anchor must still appear in ``runtime.py``, and this
        module must carry no ``runtime.py:<number>`` pin at all, so the
        rotting form cannot come back.  ``runtime.py`` is chief's file and is
        only READ here -- it lives in this same repository, so there is no
        bridge sibling to guard on and this runs everywhere the suite runs.
        """
        import re

        runtime_text = (ROOT / "src" / "pirateforce_foundation" / "runtime.py").read_text(
            encoding="utf-8"
        )
        module_text = (
            ROOT
            / "src"
            / "pirateforce_foundation"
            / "world_m2_trigger_vital_response.py"
        ).read_text(encoding="utf-8")

        # (what runtime.py must still contain, how this module spells it)
        for in_runtime, in_module in (
            (
                '"vital_inbound_trigger_vital"',
                'lane_hooks.fire("vital_inbound_trigger_vital", ...)',
            ),
            (
                'return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]',
                'return [("FOUNDATION_CREATE_COMMITTED", pc, frame, 0.10)]',
            ),
            (
                "def _gm_warp_target_unknown_reason",
                "_gm_warp_target_unknown_reason",
            ),
        ):
            with self.subTest(anchor=in_runtime):
                self.assertIn(in_runtime, runtime_text)
                self.assertIn(in_module, module_text)

        self.assertEqual(re.findall(r"runtime\.py:\d+", module_text), [])
        self.assertEqual(re.findall(r"runtime\.py.{0,4}?line \d+", module_text), [])

        # ADJACENCY, not mere presence.  pf-adversary walked three mutants
        # past the presence check above, all three green: (A1) the branch
        # body replaced with a return of a GUESSED frame while the hook
        # call stayed put -- which is item 4(b)'s exact prohibition, live
        # in runtime.py, with this test silent; (A2) the whole branch body
        # deleted and both anchor strings left behind as comments; (A3) the
        # GM branch's own hook point renamed to this one's, so the hook
        # fires from the wrong branch.  A string existing in a file is not
        # the claim the seam paragraph makes.  The claim is about this
        # branch's BODY, so the body is what is read.
        body = module_text  # placeholder rebound below; keeps the name local
        head = "if nested_id == legacy.TRIGGER_VITAL:"
        self.assertIn(head, runtime_text)
        after = runtime_text.split(head, 1)[1]
        # Up to the next branch at the same indentation.
        body = after.split("\n            if ", 1)[0]
        self.assertIn("self.rx_frames += 1", body)
        self.assertIn('lane_hooks.fire(', body)
        self.assertIn('"vital_inbound_trigger_vital"', body)
        self.assertIn("return []", body)
        self.assertEqual(
            re.findall(r"^\s+return .*$", body, re.M),
            ["                return []"],
            "the TRIGGER_VITAL branch has grown a second return: this "
            "module's seam paragraph, and COO-DECISION 20260906_1955 item "
            "4(b), both say it answers nothing",
        )
        self.assertEqual(runtime_text.count('"vital_inbound_trigger_vital"'), 1)

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
        evidence = self.contact_reading()
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
                    trigger_response._candidate_for_trigger_id(
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
        evidence = self.contact_reading()
        # Same D7 poisoning on the scene sweep: id 3 IS registered here, so
        # every None below is the SCENE guard refusing and nothing else.
        poisoned = {3: _fake(va="sub_POISON", vital_id=1, frame=b"\xde\xad")}
        for hostile in self.HOSTILE:
            with self.subTest(current_scene_id=hostile):
                # No value of any type raises -- that is this test's name.
                answered = trigger_response._candidate_for_trigger_id(
                    hostile, 3, registry=poisoned, island_contact=evidence
                )
                # EVERY row answers None on the shipped tree, including the
                # legitimate one, because tier 3 refuses on the unmeasured
                # discriminator. The poisoned registry still earns its keep:
                # the row below re-asks the SCENE guard by name, so a None
                # that came from the wrong tier is still visible.
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
        # The control for the two tests above: the one hostile row that is a
        # legitimate (scene, id) pair must get past tiers 1 and 2 and be
        # refused by TIER 3, not by a scene or id reason. If that stops
        # being true, the sweep above has gone back to being answered by
        # something other than tiers 1 and 2.
        evidence = self.contact_reading()
        self.assertIn(126, self.HOSTILE)
        for scene_id, wire_trigger_id in ((SEA, 2), (126, 3)):
            with self.subTest(scene=scene_id, wire_id=wire_trigger_id):
                self.assertEqual(
                    trigger_response.answer_guard_reason(
                        scene_id, wire_trigger_id, evidence
                    ),
                    trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
                )
        # ...and the tier-3 half of that pair passes when a measurement is
        # supplied, so the refusal above is the discriminator and not the
        # reading.
        self.assertIsNone(self.tier3(evidence))

    def test_a_registry_that_is_not_a_mapping_is_refused_by_name(self):
        evidence = self.contact_reading()
        for not_a_mapping in ([], "x", 7, object()):
            with self.subTest(registry=not_a_mapping):
                # Through the guard the answer is a REFUSAL, not a raise:
                # tier 3 is checked before the registry is looked at, which
                # is the ordering the module promises so that a malformed
                # test registry cannot turn a refusal into a traceback.
                self.assertIsNone(
                    trigger_response._candidate_for_trigger_id(
                        SEA, 2, registry=not_a_mapping, island_contact=evidence
                    )
                )
                with self.assertRaises(TypeError) as raised:
                    trigger_response._table_for(not_a_mapping)
                self.assertEqual(
                    str(raised.exception),
                    trigger_response.REGISTRY_REFUSED_NOT_A_MAPPING,
                )

    def test_registered_count_refuses_the_same_way(self):
        with self.assertRaises(TypeError) as raised:
            trigger_response._registered_count(registry=[])
        self.assertEqual(
            str(raised.exception),
            trigger_response.REGISTRY_REFUSED_NOT_A_MAPPING,
        )

    def test_a_refused_wire_id_is_answered_before_a_bad_registry_is_seen(self):
        # Guard order matters: the three tiers are checked FIRST, so a non-M2
        # id is still answered None rather than being turned into a raise by
        # a malformed test registry sitting behind it.
        evidence = self.contact_reading()
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
                SEA, 7, registry=[], island_contact=evidence
            )
        )

    def test_a_refused_scene_is_answered_before_a_bad_registry_is_seen(self):
        self.contact_reading()
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(1, 3, registry=[])
        )

    def test_tier3_refuses_before_a_bad_registry_is_seen(self):
        # On the SHIPPED module (no measured discriminator) nothing reaches
        # the registry at all, so even a garbage registry cannot raise.
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(SEA, 2, registry=[])
        )




class Tier3StateIsReadOnlyToImportersTests(M2RegistryIsolation):
    """COO-DECISION `20260907_0945` item 1, as tests.

    pf-adversary's repro for the tier-3 hole had three legs -- the
    discriminator, the extent table and the candidate registry -- and every
    one of them was an ordinary attribute an importer could assign. The
    round that answers `RE-289` is precisely the round in which those three
    stop being placeholders and start being the thing that decides whether
    the server tells a player they are touching an island, so this is the
    round the writes have to stop.
    """

    def test_the_three_tier3_names_cannot_be_reassigned_by_an_importer(self):
        for name, value in (
            ("ISLAND_CONTACT_DISCRIMINATOR", "anything at all"),
            ("ISLAND_EXTENT_BOXES", {1: (0.0, 0.0, 0.0, 1e9, 1e9, 1e9)}),
            ("_CANDIDATES", {2: _fake(), 3: _fake()}),
        ):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError) as raised:
                    setattr(trigger_response, name, value)
                self.assertIn("read-only to importers", str(raised.exception))
                with self.assertRaises(AttributeError):
                    delattr(trigger_response, name)

    def test_the_two_tables_cannot_be_mutated_in_place(self):
        # The other half: a proxy that could be `.update()`d would make the
        # freeze above cosmetic.
        for table in (
            trigger_response.ISLAND_EXTENT_BOXES,
            trigger_response._CANDIDATES,
        ):
            with self.subTest(table=type(table).__name__):
                self.assertIsInstance(table, types.MappingProxyType)
                with self.assertRaises(TypeError):
                    table[99] = None
                for method in ("clear", "update", "pop", "popitem"):
                    self.assertFalse(hasattr(table, method))

    def test_an_unfrozen_name_is_still_writable(self):
        # The freeze is a NAMED SET, not a blanket ban: a module that refuses
        # every write cannot be reloaded or patched by any tool in the repo,
        # and the tests above would pass just as well on a module that had
        # been made uselessly rigid. This is the control that says which.
        original = trigger_response.CANDIDATE_TRIGGER_IDS
        try:
            trigger_response.CANDIDATE_TRIGGER_IDS = (2, 3)
            self.assertEqual(trigger_response.CANDIDATE_TRIGGER_IDS, (2, 3))
        finally:
            trigger_response.CANDIDATE_TRIGGER_IDS = original

    def test_no_public_callable_carries_any_of_the_three_seams(self):
        """The seams live on PRIVATE functions. If any of them ever appears
        on a PUBLIC one, a wire caller supplies the very table it is judged
        against and the freeze above has bought nothing.

        `registry` joined `discriminator` and `boxes` this round --
        pf-adversary's C6 against `pirate-force-server#1015`. It is the same
        defect as `boxes` one layer out: a caller who hands in the candidate
        table is answering itself, and every tier in front of it is
        decoration. It was public until this round and survived only because
        tier 3 refuses every input on an unmeasured discriminator -- which is
        the fact the NEXT round exists to change, so the door had to be shut
        before that round, not by it.

        THE LIST OF FUNCTIONS IS DISCOVERED, NOT TYPED. This test named
        three functions by hand until this lane mutated its own draft:
        appending `lookup_with_registry = _candidate_for_trigger_id` to the
        module -- one line, a public name, the full seam behind it -- left
        the entire file green, 84 passed. A hand-typed list of entry points
        is an allowlist wearing a different hat, which is the lesson
        `allowed_id_only` already cost this file once. Every public callable
        in the module namespace is checked now, so a re-export is a red
        test rather than a new door.

        CLASSES ARE EXCLUDED, and by shape rather than by name: constructing
        an `IslandContactEvidence` is not answering the world with one, and
        its first FIELD is legitimately called `discriminator`. The public
        surface test one class down makes the same carve-out for the same
        reason, and the behaviour prong there is what covers a class being
        CALLED."""
        import inspect

        checked = []
        for name, obj in vars(trigger_response).items():
            if name.startswith("_") or not callable(obj):
                continue
            if inspect.isclass(obj):
                continue
            try:
                parameters = inspect.signature(obj).parameters
            except (TypeError, ValueError):  # pragma: no cover - defensive
                continue
            checked.append(name)
            with self.subTest(callable=name):
                self.assertNotIn("discriminator", parameters)
                self.assertNotIn("boxes", parameters)
                self.assertNotIn("registry", parameters)

        # The discovery itself is pinned: a mutant that narrows the loop to
        # nothing would pass every subTest above vacuously.
        self.assertIn("candidate_for_trigger_id", checked)
        self.assertIn("registered_count", checked)
        self.assertIn("answer_guard_reason", checked)
        self.assertIn("scene_guard_reason", checked)

    def test_the_freeze_covers_every_function_this_module_defines(self):
        """pf-adversary D1, CRITICAL, against this round's own fix, and D6,
        which is why D1 could be written at all.

        Closing C6 minted `_candidate_for_trigger_id` and `_registered_count`
        and left both OUT of `__FROZEN`, while the frozen public pair do
        nothing but delegate to them. One assignment --
        `module._candidate_for_trigger_id = lambda *a, **k: forged` -- then
        made the frozen public function hand a forged frame to a caller with
        no scene, no reading and no measured discriminator. Strictly worse
        than the C6 this round was sent to close.

        It was invisible because `__FROZEN` was pinned by three hand-typed
        names and nothing else: removing `_table_for` from the set, removing
        `candidate_for_trigger_id`, and ADDING the two twins (that is, the
        fix itself) were all green. A hand-typed pin cannot notice a name
        that was never typed.

        So the set is DERIVED here. Every function this module defines must
        be frozen. The next twin is covered before anyone remembers to
        think about it."""
        import types

        defined = {
            name
            for name, value in vars(trigger_response).items()
            if isinstance(value, types.FunctionType)
            and value.__module__ == trigger_response.__name__
        }
        # Non-vacuity: the derivation itself is pinned, or a mutant that
        # narrows it to nothing passes.
        self.assertIn("answer_guard_reason", defined)
        self.assertIn("_candidate_for_trigger_id", defined)
        self.assertIn("_registered_count", defined)
        self.assertGreaterEqual(len(defined), 10)

        frozen = set(type(trigger_response)._FrozenTier3Module__FROZEN)
        self.assertEqual(sorted(defined - frozen), [])

    def test_the_new_crosswalk_table_is_frozen_like_every_other_tier3_table(self):
        # Same round, same lesson one layer over: the crosswalk table is
        # data a discriminator would be judged against tomorrow, which is
        # the argument that froze `_ISLAND_EXTENT_BOXES`.
        for name in (
            "M2_WIRE_ORDINAL_CROSSWALK_LETTER",
            "M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS",
            "M2_WIRE_ORDINAL_CROSSWALK_UNDECODED_FRAMES",
            "M2_WIRE_ORDINAL_CROSSWALK_NAME_RESOLUTION",
        ):
            with self.subTest(name=name):
                with self.assertRaises(AttributeError):
                    setattr(trigger_response, name, "anything at all")

    def test_the_reload_hole_is_named_and_not_pretended_away(self):
        # `importlib.reload` re-executes the module body, which writes the
        # module dict directly and cannot be intercepted. The module says so
        # in `_FrozenTier3Module`'s docstring rather than claiming a lock it
        # does not have; this test is what keeps that sentence honest, and
        # it is also the pin that a reload RESTORES the shipped values
        # rather than leaving a test's leftovers behind.
        importlib.reload(trigger_response)
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)
        self.assertEqual(sorted(trigger_response.ISLAND_EXTENT_BOXES), [1, 2, 3])
        self.assertIn("bypass", trigger_response._FrozenTier3Module.__doc__)


class EveryBoxCitesTheLetterItCameFromTests(M2RegistryIsolation):
    """COO-DECISION `20260907_0945` item 3: "the right to say an extent was
    measured comes from an RE result letter, not from a round that commits
    numbers -- a table with no letter behind it is a tier-3 refusal, not a
    pass with a warning".

    WHY THIS IS NOT THE GATE COO NAMED, STATED PLAINLY.  The decision
    said to reuse `tests/test_mob_death_widening_schema_gate._letter_exists_
    for` and to write no second oracle.  That function is imported below and
    IS the house gate -- but it requires the filename to contain both
    "COO-DECISION" and "widen", so it can certify a death-widening ruling
    and cannot certify an RE result letter, and `tests/test_mob_death_
    widening_schema_gate.py` is LANE-B's file, outside this lane's write
    zone.  So this class checks the letter by the SHA256 OF ITS CONTENT,
    which answers a strictly narrower question than the house gate ("this
    exact letter is on the bridge") and makes no claim at all about who
    wrote it -- the handwriting question that COO's "no second oracle" rule
    is about.  The ask to make the house gate take its name tokens as a
    parameter is `notes_to_chief/20260907_1022_LANE-A-ASK-COO-the-house-
    letter-gate-cannot-certify-an-RE-letter.md`.
    [assumption of LANE-A - pending COO confirmation]
    """

    def bridge(self):
        """The bridge checkout, AFTER the caller has run the precondition.

        `BRIDGE_SIBLING.require(self)` is spelled out in each guarded test
        rather than hidden in here, because `tests/test_pytest_precondition_
        census.py` counts guards by reading the source of each test method:
        a require() one call deeper counts as zero, the pin file then
        disagrees with the census, and the gate goes red on the file that
        was trying to be tidy.
        """
        import os

        env = os.environ.get("PF_BRIDGE_DIR")
        if env and Path(env).is_dir():
            return Path(env)
        return BRIDGE_SIBLING.paths[0]

    def test_every_committed_box_carries_a_citation_naming_re289(self):
        boxes = trigger_response.ISLAND_EXTENT_BOXES
        citations = trigger_response.ISLAND_EXTENT_BOX_CITATIONS
        self.assertEqual(sorted(boxes), sorted(citations))
        self.assertEqual(
            sorted(boxes), sorted(trigger_response.ISLAND_EXTENT_BOX_ORDINALS)
        )
        for ordinal in boxes:
            with self.subTest(ordinal=ordinal):
                citation = citations[ordinal]
                self.assertIn("RE-289", citation)
                self.assertIn(trigger_response.RE289_RESULT_LETTER_SHA256, citation)
                # The citation has to carry the RAW measurement, not just a
                # ticket number: a reader must be able to redo `pos +/-
                # extent / 2` without opening the letter.
                self.assertIn("pos ", citation)
                self.assertIn("extent ", citation)

    def test_the_cited_letter_is_on_the_bridge_with_the_cited_hash(self):
        import hashlib
        import os

        if not (os.environ.get("PF_BRIDGE_DIR")
                and Path(os.environ["PF_BRIDGE_DIR"]).is_dir()):
            # "not found = skip with a reason, never silently pass".
            BRIDGE_SIBLING.require(self)
        bridge = self.bridge()
        # BOTH roots, and recursively, for the reason LANE-B's gate gives:
        # LANE-K sweeps letters into `pf_bridge/archive/<dated folder>/` on
        # age, and a letter that has been filed is still a letter. A gate
        # that only looked in the mailbox would go red weeks from now with
        # nobody having touched this table.
        roots = [bridge / "notes_to_chief", bridge / "archive"]
        wanted = trigger_response.RE289_RESULT_LETTER_SHA256
        found = []
        for root in roots:
            if not root.is_dir():
                continue
            for entry in root.rglob("*.md"):
                # `rglob(NAME)` treats NAME as a PATTERN -- pf-adversary:
                # set the constant to "*.md" and the gate would hash any one
                # of 6,184 files and pass. The name is compared literally.
                if entry.name == trigger_response.RE289_RESULT_LETTER:
                    if entry.is_file():
                        found.append(entry)
        self.assertTrue(
            found,
            "the extent table cites %s and no such file exists under %s or "
            "%s -- COO-DECISION 20260907_0945 item 3: a table with no letter "
            "behind it is a refusal, not a pass with a warning"
            % (trigger_response.RE289_RESULT_LETTER, roots[0], roots[1]),
        )
        digests = {
            hashlib.sha256(entry.read_bytes()).hexdigest() for entry in found
        }
        self.assertIn(
            wanted,
            digests,
            "a letter with the cited NAME is on the bridge but its content "
            "hashes to %s, not the %s this table was copied from -- the "
            "numbers in the module and the numbers in the letter are no "
            "longer known to agree" % (sorted(digests), wanted),
        )

    def test_each_box_is_re_derived_from_its_own_citation_string(self):
        """pf-adversary D1, MEASURED against this round's first draft: a
        single transposed digit typed into BOTH the box and the test's own
        centre constant left all 81 tests green, while the citation twenty
        lines away still carried the right number. Double entry that shares
        a source is single entry.

        So the citation is the source now: its `pos` and `extent` are parsed
        back out and the box is re-derived from them. A typo in the box is
        red, a typo in the citation is red, and only a typo made IDENTICALLY
        in both survives -- which is a different act from a slip.
        """
        pattern = re.compile(
            r"pos (-?[\d.]+),(-?[\d.]+),(-?[\d.]+) "
            r"extent (-?[\d.]+)x(-?[\d.]+)x(-?[\d.]+)"
        )
        for ordinal, box in trigger_response.ISLAND_EXTENT_BOXES.items():
            with self.subTest(ordinal=ordinal):
                citation = trigger_response.ISLAND_EXTENT_BOX_CITATIONS[ordinal]
                match = pattern.search(citation)
                self.assertIsNotNone(
                    match, "citation %r carries no machine-readable "
                    "pos/extent" % (citation,)
                )
                numbers = [float(group) for group in match.groups()]
                pos, extent = numbers[:3], numbers[3:]
                for axis in range(3):
                    self.assertAlmostEqual(
                        box[axis], pos[axis] - extent[axis] / 2, places=6
                    )
                    self.assertAlmostEqual(
                        box[axis + 3], pos[axis] + extent[axis] / 2, places=6
                    )

    def test_the_letter_itself_carries_the_numbers_the_citations_quote(self):
        # The half that makes the sha pin mean "these numbers came from this
        # letter" instead of "a file with this hash exists". Bytes, never
        # text: the letter is UTF-8 with ~3,000 Thai characters and would
        # raise UnicodeDecodeError under the bridge console's cp874.
        import os

        if not (os.environ.get("PF_BRIDGE_DIR")
                and Path(os.environ["PF_BRIDGE_DIR"]).is_dir()):
            BRIDGE_SIBLING.require(self)
        bridge = self.bridge()
        # BOTH roots, like the test above and for the same reason: a letter
        # LANE-K has swept into `archive/` is still a letter. Reading only
        # the mailbox would have needed a `skipTest` for the swept case,
        # which is an UNPINNED SKIP and is what closed PR #503 -- caught by
        # pf_gate_preflight before this branch was pushed.
        # BOTH `RE-289` ARTIFACTS COUNT, and the second one arrived this
        # round. The prose letter rounded ordinal 1 to (3098.2, 2207.5,
        # 86.0) while printing ordinals 2 and 3 exact; the verbatim dump
        # prints all three at full precision, and the table now carries the
        # dump's digits. Requiring the prose letter alone would force the
        # table to stay rounded in one row and exact in the other two --
        # which is the state that made the table uncheckable in the first
        # place. A number must appear in ONE of the two, and both are named
        # constants with pinned shas, so this is not a widened net.
        blobs = {}
        wanted = {
            trigger_response.RE289_RESULT_LETTER,
            trigger_response.RE289_TGR_DUMP_LETTER,
        }
        for root in (bridge / "notes_to_chief", bridge / "archive"):
            if not root.is_dir():
                continue
            for entry in root.rglob("*.md"):
                if entry.name in wanted and entry.is_file():
                    blobs.setdefault(entry.name, entry.read_bytes())
        self.assertIn(
            trigger_response.RE289_RESULT_LETTER, blobs,
            "the cited letter %s is not under notes_to_chief/ or archive/ "
            "on the bridge" % (trigger_response.RE289_RESULT_LETTER,),
        )
        self.assertIn(
            trigger_response.RE289_TGR_DUMP_LETTER, blobs,
            "the cited dump %s is not under notes_to_chief/ or archive/ "
            "on the bridge" % (trigger_response.RE289_TGR_DUMP_LETTER,),
        )
        for ordinal, citation in trigger_response.ISLAND_EXTENT_BOX_CITATIONS.items():
            with self.subTest(ordinal=ordinal):
                for number in re.findall(r"-?\d+\.\d+", citation.split("pos ")[1]):
                    self.assertTrue(
                        any(
                            number.encode("ascii") in blob
                            for blob in blobs.values()
                        ),
                        "the citation for ordinal %s quotes %s and neither "
                        "RE-289 artifact contains it" % (ordinal, number),
                    )

    def test_the_keys_of_the_extent_table_are_never_used_as_wire_ids(self):
        # RE-289 nonclaim (1): nothing has shown the .tgr ordinal equals the
        # wire trigger id. They are equal today by coincidence of numbering.
        # The pin is behavioural, not a grep: move the table's keys off the
        # wire ids entirely and a reading inside ordinal 2's box must STILL
        # pass, because containment reads values and never indexes by id.
        reading = self.contact_reading()
        relabelled = {
            777: trigger_response.ISLAND_EXTENT_BOXES[2],
            888: trigger_response.ISLAND_EXTENT_BOXES[3],
        }
        self.assertIsNone(self.tier3(reading, boxes=relabelled))
        # ...and a table keyed by the wire ids but holding the WRONG boxes
        # must refuse, which a lookup by id would not do.
        swapped = {2: trigger_response.ISLAND_EXTENT_BOXES[3]}
        self.assertEqual(
            self.tier3(reading, boxes=swapped),
            trigger_response.CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT,
        )

    def test_a_reading_at_each_measured_centre_passes_and_the_edges_hold(self):
        # The measurement, exercised end to end through the public guard.
        for centre in (ORD1_CENTRE, ORD2_CENTRE, ORD3_CENTRE):
            with self.subTest(centre=centre):
                self.assertIsNone(self.tier3(self.contact_reading(*centre)))
        # One metre outside ordinal 2's x half-width, at its own centre in y
        # and z: this is the boundary the "extent is FULL width" reading
        # puts there, and the fail-closed direction is that it refuses.
        just_outside = (ORD2_CENTRE[0] - 1000.01, ORD2_CENTRE[1], ORD2_CENTRE[2])
        self.assertEqual(
            self.tier3(self.contact_reading(*just_outside)),
            trigger_response.CONTACT_REFUSED_OUTSIDE_EVERY_COMMITTED_EXTENT,
        )
        # And on the SHIPPED module none of that is reachable at all: the
        # public guard refuses on the unmeasured discriminator first, and
        # both candidate slots are empty besides.
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 3, island_contact=self.contact_reading(*ORD3_CENTRE)
            )
        )


class ThePassPathHasActuallyBeenRunTests(M2RegistryIsolation):
    """pf-adversary F5 against `pirate-force-server#1033`, and it was the
    bluntest finding this module has had: the lane's one function that hands
    a frame to a caller had NEVER been executed past its guard.

    The measurement was a surviving mutant. Change the last line of
    `_candidate_for_trigger_id` from ``table.get(wire_trigger_id)`` to
    ``table.get(current_scene_id)`` and the whole file stays green, because
    `ISLAND_CONTACT_DISCRIMINATOR` is `None` on the shipped tree, so every
    call in every test is refused at tier 3 and the lookup underneath is
    dead code under test. `_tier3_contact_reason` had seams for exactly this
    reason; nothing carried them the two frames up to the lookup. Since this
    round `_answer_guard_reason` does, and these tests are what that is for.

    THE PUBLIC FUNCTION STILL FORWARDS NOTHING -- pinned by
    `test_no_public_callable_carries_any_of_the_three_seams` and by the last
    test here, which walks the same input through the public door and gets
    the shipped refusal.
    """

    MEASURED = "a discriminator this test measured, not the module"

    def reading(self, centre):
        return trigger_response.IslandContactEvidence(
            discriminator=self.MEASURED,
            x=centre[0],
            y=centre[1],
            z=centre[2],
            source="ThePassPathHasActuallyBeenRunTests",
        )

    def passing(self, wire_trigger_id, registry, centre=ORD2_CENTRE):
        return trigger_response._candidate_for_trigger_id(
            SEA,
            wire_trigger_id,
            self.reading(centre),
            discriminator=self.MEASURED,
            boxes=trigger_response.ISLAND_EXTENT_BOXES,
            registry=registry,
        )

    def test_a_passing_call_returns_the_frame_registered_for_the_WIRE_ID(self):
        # The registry deliberately holds an entry under the SCENE id too,
        # and a different one. `table.get(current_scene_id)` would return
        # `scene_frame` here, and `table.get(2)` returns `wire_frame`; a
        # lookup keyed on the wrong argument now fails loudly instead of
        # being invisible. This is the mutant F5 named.
        wire_frame = _fake(vital_id=2)
        scene_frame = _fake(vital_id=SEA)
        got = self.passing(2, {2: wire_frame, SEA: scene_frame})
        self.assertIs(got, wire_frame)
        self.assertIsNot(got, scene_frame)

    def test_the_frame_comes_back_UNCHANGED(self):
        # The module's oldest promise, and until this round no test could
        # reach the line that keeps it: what is registered is what is
        # returned, not a copy and not a re-encoding.
        registered = _fake(vital_id=3)
        got = self.passing(3, {3: registered})
        self.assertIs(got, registered)

    def test_a_passing_call_with_an_EMPTY_slot_is_still_None(self):
        # All three tiers pass and nothing is registered: `None`, and NOT
        # because a tier refused. The distinction is the reason
        # `answer_guard_reason` exists next to this function.
        self.assertIsNone(self.passing(2, {2: None, 3: None}))
        self.assertIsNone(
            trigger_response._answer_guard_reason(
                SEA,
                2,
                self.reading(ORD2_CENTRE),
                discriminator=self.MEASURED,
                boxes=trigger_response.ISLAND_EXTENT_BOXES,
            )
        )

    def test_each_tier_still_refuses_with_the_seams_supplied(self):
        # A seam that opened the tiers instead of only the third one would
        # be worse than the dead code it replaced.
        registry = {2: _fake(vital_id=2), 3: _fake(vital_id=3)}
        for scene, wire, centre, why in (
            (SEA + 1, 2, ORD2_CENTRE, "wrong scene"),
            (SEA, 4, ORD2_CENTRE, "wrong wire id"),
            (SEA, 2, (0.0, 0.0, 86.0), "open water"),
        ):
            with self.subTest(why=why):
                self.assertIsNone(
                    trigger_response._candidate_for_trigger_id(
                        scene,
                        wire,
                        self.reading(centre),
                        discriminator=self.MEASURED,
                        boxes=trigger_response.ISLAND_EXTENT_BOXES,
                        registry=registry,
                    )
                )

    def test_a_reading_naming_ANOTHER_discriminator_is_still_refused(self):
        # The seam supplies what the module has not measured; it does not
        # switch off the comparison against it.
        other = trigger_response.IslandContactEvidence(
            discriminator=self.MEASURED + " (a different one)",
            x=ORD2_CENTRE[0],
            y=ORD2_CENTRE[1],
            z=ORD2_CENTRE[2],
            source="ThePassPathHasActuallyBeenRunTests",
        )
        self.assertIsNone(
            trigger_response._candidate_for_trigger_id(
                SEA,
                2,
                other,
                discriminator=self.MEASURED,
                boxes=trigger_response.ISLAND_EXTENT_BOXES,
                registry={2: _fake(vital_id=2)},
            )
        )

    def test_the_SHIPPED_public_door_refuses_the_very_same_input(self):
        # The control. Everything above runs through a private twin with
        # seams; the public function has none, reads the module's own
        # unmeasured `ISLAND_CONTACT_DISCRIMINATOR`, and answers `None` for
        # the identical reading -- which is what a live session gets today.
        self.assertIsNone(trigger_response.ISLAND_CONTACT_DISCRIMINATOR)
        self.assertIsNone(
            trigger_response.candidate_for_trigger_id(
                SEA, 2, self.reading(ORD2_CENTRE)
            )
        )
        self.assertEqual(
            trigger_response.answer_guard_reason(
                SEA, 2, self.reading(ORD2_CENTRE)
            ),
            trigger_response.CONTACT_REFUSED_ISLAND_VS_OPEN_WATER_UNMEASURED,
        )


class TheFreezeIsCensusedNotJustDerivedTests(M2RegistryIsolation):
    """pf-adversary F4, CRITICAL: `__FROZEN` could be SHRUNK.

    The previous round bought a derived test that requires every module-level
    FUNCTION to be in the set, so a new private twin cannot be forgotten.
    The other half of the set -- the data -- was still typed by hand and
    checked by nothing, so deleting a line from it left the file green.
    Eight of the thirteen non-function entries survived deletion; the worst
    was `"__class__"`, whose removal restores `module.__class__ =
    types.ModuleType` -- the un-freeze that is the FIRST bypass the class's
    own comment lists.

    A test that iterates `__FROZEN` cannot catch that: shrink the set and
    the loop just runs fewer times. So this class carries an INDEPENDENT
    census of the data half and requires the set to equal
    (module functions) | (this census) exactly. Adding a frozen name without
    naming it here is red; removing one from the set is red.
    """

    #: The non-function names `__FROZEN` must hold, and WHY each is tier-3
    #: state. Sourced from pf-adversary's F4 census plus this round's
    #: additions -- deliberately NOT read out of `__FROZEN`.
    DATA_NAMES = {
        "__class__": "un-freeze the module, then write anything",
        "ISLAND_CONTACT_DISCRIMINATOR": "the name tier 3 compares against",
        "ISLAND_EXTENT_BOXES": "the boxes tier 3 decides in",
        "_ISLAND_EXTENT_BOXES": "the dict behind that proxy",
        "ISLAND_EXTENT_BOX_CITATIONS": "what the citation gate reads",
        "ISLAND_EXTENT_BOX_ORDINALS": "which rows claim to be islands",
        "ISLAND_EXTENT_BOX_INTERPRETATION": "how the two vectors are read",
        "ISLAND_EXTENT_BOX_INTERPRETATIONS_REFUTED": "what RE-297 ruled out",
        "ISLAND_EXTENT_BOX_EDGE_WALL_ORDINALS": "rows that must stay out",
        "ISLAND_EXTENT_EDGE_WALL_RECORDS": "the evidence for the reading",
        "ISLAND_EXTENT_EDGE_WALL_SPACINGS": "the second entry for it",
        "RE289_RESULT_LETTER": "the letter the boxes came from",
        "RE289_RESULT_LETTER_SHA256": "that letter's identity",
        "RE297_RESULT_LETTER": "the letter the reading came from",
        "RE297_RESULT_LETTER_SHA256": "that letter's identity",
        "RE289_TGR_DUMP_LETTER": "the dump that makes both re-checkable",
        "RE289_TGR_DUMP_LETTER_SHA256": "that dump's identity",
        "_CANDIDATES": "the frames this module would answer with",
        "__CANDIDATES": "the dict behind that proxy",
        "TIER3_STATE_IS_READ_ONLY": "the refusal message itself",
        "M2_WIRE_ORDINAL_CROSSWALK_LETTER": "the crosswalk's source",
        "M2_WIRE_ORDINAL_CROSSWALK_OBSERVATIONS": "the crosswalk itself",
        "M2_WIRE_ORDINAL_CROSSWALK_UNDECODED_FRAMES": "its negative half",
        "M2_WIRE_ORDINAL_CROSSWALK_NAME_RESOLUTION": "the rows GT-228 read",
    }

    def frozen(self):
        return getattr(
            trigger_response._FrozenTier3Module, "_FrozenTier3Module__FROZEN"
        )

    def module_function_names(self):
        return {
            name
            for name, value in vars(trigger_response).items()
            if isinstance(value, types.FunctionType)
            and getattr(value, "__module__", None) == trigger_response.__name__
        }

    def test_the_frozen_set_is_exactly_the_functions_plus_this_census(self):
        expected = self.module_function_names() | set(self.DATA_NAMES)
        self.assertEqual(self.frozen(), expected)

    def test_every_name_in_the_census_refuses_both_write_and_delete(self):
        # Membership in a set is not a guard; this runs the guard. The
        # sentinel is deliberately NOT a freeze class, so `__class__` takes
        # the same path as every other name.
        sentinel = object()
        for name, why in sorted(self.DATA_NAMES.items()):
            with self.subTest(name=name, why=why):
                with self.assertRaises(AttributeError) as raised:
                    setattr(trigger_response, name, sentinel)
                self.assertIn("read-only to importers", str(raised.exception))
                with self.assertRaises(AttributeError):
                    delattr(trigger_response, name)

    def test_the_un_freeze_door_is_shut_by_name(self):
        # F4's headline, as a behaviour rather than a list membership: this
        # is the assignment that made every other entry in the set moot.
        with self.assertRaises(AttributeError):
            trigger_response.__class__ = types.ModuleType
        # And the module is still the frozen class afterwards.
        self.assertIsNotNone(
            getattr(
                type(trigger_response), "_FrozenTier3Module__FROZEN", None
            )
        )

    def test_a_reload_may_still_reinstall_its_own_freeze(self):
        # The control for the test above: `importlib.reload` re-executes the
        # module body, which ends by assigning `__class__` with a NEW class
        # carrying the same freeze. Refusing that would make the module
        # unreloadable, so the exemption is deliberate and pinned here.
        reloaded = importlib.reload(trigger_response)
        self.assertIsNotNone(
            getattr(type(reloaded), "_FrozenTier3Module__FROZEN", None)
        )


class TheEdgeWallsAreEvidenceNotIslandsTests(M2RegistryIsolation):
    """`RE-297`, consumed. Two things follow from it and both are pinned.

    ONE: ordinals 6/7/8 and 68/69/70 are the MAP-EDGE WALLS. They are the
    records that decided how to read `pos` and `extent`, and they are the
    rows that would turn "touching an island" into "sailing near the edge of
    the map" -- `RE-234` item (3)'s confusion, rebuilt -- if a later round
    widened the selection rule and swept them in.

    TWO: the reading itself. `pos` is the box CENTRE and `extent` its FULL
    WIDTH, and the arithmetic below is `RE-297`'s discriminator re-derived
    from the six records this file pins, not a restatement of its verdict.
    """

    def test_no_edge_wall_ordinal_is_in_the_island_table(self):
        walls = set(trigger_response.ISLAND_EXTENT_BOX_EDGE_WALL_ORDINALS)
        self.assertEqual(walls, set(trigger_response.ISLAND_EXTENT_EDGE_WALL_RECORDS))
        self.assertFalse(
            walls & set(trigger_response.ISLAND_EXTENT_BOX_ORDINALS)
        )
        self.assertFalse(walls & set(trigger_response.ISLAND_EXTENT_BOXES))
        self.assertFalse(walls & set(trigger_response.ISLAND_EXTENT_BOX_CITATIONS))

    def test_the_edge_walls_tile_only_under_centre_plus_full_width(self):
        # Each wall is three records laid along one axis. Under the reading
        # this module uses, consecutive boxes OVERLAP (spacing < extent), so
        # the wall has no gap. Under MIN CORNER the same three leave a gap
        # the size of a box at one end; under HALF WIDTH they overlap by
        # more than half, so laying three of them is pointless.
        records = trigger_response.ISLAND_EXTENT_EDGE_WALL_RECORDS
        walls = {
            # (ordinals, index of the axis they are laid along)
            "west": ((6, 7, 8), 1),
            "south": ((68, 69, 70), 0),
        }
        for side, (ordinals, axis) in walls.items():
            positions = sorted(records[one][axis] for one in ordinals)
            extents = {records[one][2 + axis] for one in ordinals}
            with self.subTest(side=side):
                self.assertEqual(extents, {7000.0})
                extent = extents.pop()
                gaps = [
                    round(high - low, 2)
                    for low, high in zip(positions, positions[1:])
                ]
                self.assertEqual(len(gaps), 2)
                # SECOND ENTRY. Without this a transposed digit in a
                # record survives the whole file: the bounds below are
                # loose by hundreds of units, and a wall coordinate is
                # hand-transcribed. Measured: ordinal 7 moved from
                # -325.84 to -352.84 passed 106 tests before this line.
                measured = trigger_response.ISLAND_EXTENT_EDGE_WALL_SPACINGS
                for gap in gaps:
                    self.assertIn(gap, measured)
                for gap in gaps:
                    # CENTRE + FULL WIDTH: they overlap, so no gap.
                    self.assertLess(gap, extent)
                    # ... and by only a little, which is what makes three
                    # records a wall and not three stacked boxes. HALF WIDTH
                    # would put the true extent at 14000, i.e. gap < half.
                    self.assertGreater(gap, extent / 2.0)
                # MIN CORNER: the low box starts at its own `pos`, so the
                # wall stops short of the scene edge by a whole box that the
                # centre reading covers. Named as a number so the refuted
                # reading is auditable and not merely asserted.
                shortfall = round(extent / 2.0, 2)
                self.assertGreater(shortfall, 0.0)
        self.assertEqual(
            trigger_response.ISLAND_EXTENT_BOX_INTERPRETATION,
            "CENTRE_PLUS_FULL_WIDTH",
        )
        self.assertNotIn(
            trigger_response.ISLAND_EXTENT_BOX_INTERPRETATION,
            trigger_response.ISLAND_EXTENT_BOX_INTERPRETATIONS_REFUTED,
        )

    def test_the_four_measured_spacings_are_exactly_what_the_records_give(self):
        # The other direction: the spacing table may not carry a number no
        # pair of records produces, or the "second entry" is decoration.
        records = trigger_response.ISLAND_EXTENT_EDGE_WALL_RECORDS
        produced = set()
        for ordinals, axis in (((6, 7, 8), 1), ((68, 69, 70), 0)):
            positions = sorted(records[one][axis] for one in ordinals)
            produced.update(
                round(high - low, 2)
                for low, high in zip(positions, positions[1:])
            )
        self.assertEqual(
            produced, set(trigger_response.ISLAND_EXTENT_EDGE_WALL_SPACINGS)
        )
        self.assertEqual(len(trigger_response.ISLAND_EXTENT_EDGE_WALL_SPACINGS), 4)

    def test_every_island_box_matches_the_named_interpretation(self):
        # The interpretation constant is not decoration: each committed row
        # must be `pos +/- extent/2` of the numbers in its own citation, so
        # changing the constant without changing the table -- or the other
        # way round -- is red.
        self.assertEqual(
            trigger_response.ISLAND_EXTENT_BOX_INTERPRETATION,
            "CENTRE_PLUS_FULL_WIDTH",
        )
        pattern = re.compile(
            r"pos (-?[\d.]+),(-?[\d.]+),(-?[\d.]+) "
            r"extent ([\d.]+)x([\d.]+)x([\d.]+)"
        )
        for ordinal, citation in trigger_response.ISLAND_EXTENT_BOX_CITATIONS.items():
            with self.subTest(ordinal=ordinal):
                found = pattern.search(citation)
                self.assertIsNotNone(found, citation)
                numbers = [float(one) for one in found.groups()]
                centre, extent = numbers[:3], numbers[3:]
                expected = tuple(
                    round(one, 6)
                    for one in (
                        [c - e / 2.0 for c, e in zip(centre, extent)]
                        + [c + e / 2.0 for c, e in zip(centre, extent)]
                    )
                )
                got = tuple(
                    round(one, 6)
                    for one in trigger_response._ISLAND_EXTENT_BOXES[ordinal]
                )
                self.assertEqual(got, expected)

    def test_z_is_an_ordinary_coordinate_and_the_floor_anchor_is_refuted(self):
        # `RE-297` item 3: 32 of the 52 records sit above the scene floor,
        # so `pos.z` is not an anchor. The consequence this module lives
        # with is that its bands dip under the water surface, which is what
        # the committed rows do -- and a round that "fixed" that by moving
        # the band up would be re-adopting the refuted reading.
        for ordinal, box in trigger_response._ISLAND_EXTENT_BOXES.items():
            with self.subTest(ordinal=ordinal):
                self.assertLess(box[2], 86.0)
                self.assertGreater(box[5], 86.0)


if __name__ == "__main__":
    unittest.main()
