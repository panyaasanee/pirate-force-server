"""LANE-A / M2: the survey plan is fail-closed on measured XYZ, its handles
are the server's own, and its geometry can never take a hook down with it.

The plan module exists to be EMPTY today and correct the day GT-228 reports.
Both halves need a test: an empty plan that would stay empty after the
measurement lands would be worthless, so every "nothing is provisionable"
assertion here has a sibling that injects a measurement and proves the same
function then answers differently.

Several tests below exist because pf-adversary measured the mutation they
now catch: a handle formula nothing pinned, a radius compared only against
itself, constants no test read, and an import-time raise that deleted the
hook's evidence line rather than the annotation.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_bg3001_identity as bg3001  # noqa: E402
from pirateforce_foundation import world_island_dock_table as islands  # noqa: E402
from pirateforce_foundation import world_m2_survey_plan as plan  # noqa: E402


class _WithMeasuredXYZ:
    """Context manager putting real coordinates into `MEASURED_XYZ`.

    The plan reads the module-level dict on every call rather than caching a
    snapshot at import, which is what makes "GT-228 lands as a data-only
    change" true.  Every test that injects restores the dict afterwards.
    """

    def __init__(self, rows: dict[int, tuple[float, float, float]]):
        self._rows = rows
        self._saved: dict[int, tuple[float, float, float]] = {}

    def __enter__(self):
        self._saved = dict(plan.MEASURED_XYZ)
        plan.MEASURED_XYZ.update(self._rows)
        return plan

    def __exit__(self, *_exc):
        plan.MEASURED_XYZ.clear()
        plan.MEASURED_XYZ.update(self._saved)
        return False


class _WithOnlyMeasuredXYZ(_WithMeasuredXYZ):
    """Like `_WithMeasuredXYZ`, but empties the dict first instead of adding
    to it.  Needed for tests that must see a single row (or none at all) in
    isolation now that GT-228 has left both real M2 targets measured by
    default -- `_WithMeasuredXYZ` alone can no longer produce that."""

    def __enter__(self):
        self._saved = dict(plan.MEASURED_XYZ)
        plan.MEASURED_XYZ.clear()
        plan.MEASURED_XYZ.update(self._rows)
        return plan


class _WithAnchors:
    """Context manager replacing the identity module's island rows.

    Clears the plan's anchor cache on the way in AND on the way out, so a
    test that shifts the plane cannot leave a shifted one behind.
    """

    def __init__(self, rows):
        self._rows = rows
        self._saved = None

    def __enter__(self):
        self._saved = bg3001.shippable_placements
        bg3001.shippable_placements = lambda: self._rows
        plan._ANCHORS = None
        return plan

    def __exit__(self, *_exc):
        bg3001.shippable_placements = self._saved
        plan._ANCHORS = None
        return False


def _island_rows(z_shift: float = 0.0):
    import dataclasses

    rows = []
    for placement in bg3001.shippable_placements():
        if getattr(placement.identity, "outfit", None) == "MAP_ISLAND_01":
            placement = dataclasses.replace(placement, z=placement.z + z_shift)
        rows.append(placement)
    return tuple(rows)


class TheConstantsOtherThingsRestOnTests(unittest.TestCase):
    """Every one of these was a surviving mutation before it was written."""

    def test_the_contact_radius_is_re_227s_number(self):
        # Not "whatever the module says": 500 is the wire fact the whole
        # third-component argument is built on.
        self.assertEqual(plan.CLIENT_CONTACT_RADIUS, 500)

    def test_the_blocking_reason_names_the_ticket_that_lifts_it(self):
        self.assertEqual(plan.XYZ_SOURCE_TICKET, "GT-228")
        self.assertEqual(plan.BLOCKED_XYZ_UNMEASURED, "XYZ_UNMEASURED_PENDING_GT-228")
        self.assertIn(plan.XYZ_SOURCE_TICKET, plan.BLOCKED_XYZ_UNMEASURED)

    def test_the_coordinate_frame_is_the_scene_the_ticket_is_run_in(self):
        self.assertEqual(plan.XYZ_FRAME_SCENE_ID, 126)
        self.assertTrue(plan.plan_is_for_scene(126))
        # Columbus's destination is scene 17, and a record in this frame is
        # meaningless to a player standing there.
        self.assertFalse(plan.plan_is_for_scene(17))


class SceneGuardNamesItsRefusalTests(unittest.TestCase):
    """`scene_guard_reason`, closed round `m1wqqy` for `ADVERSARY_PENDING`
    item 3 (round `16uvmp`): the guard used to return a bare `False` for
    both a caller in the wrong scene and a caller passing something that
    was never a scene id -- silent where this file otherwise names its
    refusals (`BLOCKED_XYZ_UNMEASURED` above)."""

    def test_the_frame_scene_itself_is_not_refused(self):
        self.assertIsNone(plan.scene_guard_reason(126))

    def test_a_different_int_scene_is_the_wrong_scene_reason(self):
        self.assertEqual(
            plan.scene_guard_reason(17), plan.PLAN_SCENE_REFUSED_WRONG_SCENE
        )

    def test_a_float_that_equals_126_is_still_refused_by_type(self):
        # `126 == 126.0` is True in Python -- the old bare `==` guard let
        # this through silently.  A scene id has never been a float in this
        # codebase, so this is refused, and named for exactly what it is:
        # not the wrong scene, the wrong TYPE.
        self.assertEqual(
            plan.scene_guard_reason(126.0), plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )

    def test_a_string_scene_id_is_refused_by_type_not_by_value(self):
        self.assertEqual(
            plan.scene_guard_reason("126"), plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )

    def test_none_is_refused_by_type(self):
        self.assertEqual(
            plan.scene_guard_reason(None), plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )

    def test_a_bool_is_refused_by_type_even_though_it_subclasses_int(self):
        self.assertEqual(
            plan.scene_guard_reason(True), plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )
        self.assertEqual(
            plan.scene_guard_reason(False), plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )

    def test_the_two_reasons_are_distinct_strings(self):
        self.assertNotEqual(
            plan.PLAN_SCENE_REFUSED_WRONG_SCENE, plan.PLAN_SCENE_REFUSED_NOT_AN_INT
        )

    def test_plan_is_for_scene_stays_a_thin_boolean_view(self):
        for scene_id in (126, 17, "126", None, 126.0, True):
            with self.subTest(scene_id=scene_id):
                self.assertEqual(
                    plan.plan_is_for_scene(scene_id),
                    plan.scene_guard_reason(scene_id) is None,
                )

    def test_never_raises(self):
        for scene_id in (object(), [], {}, 126.0, "126", None, True, -1):
            with self.subTest(scene_id=scene_id):
                plan.scene_guard_reason(scene_id)  # must not raise


class FailClosedOnMeasurementTests(unittest.TestCase):
    # `test_no_xyz_is_measured_yet` lived here until GT-228 (R308, PASS,
    # 2026-09-04) reported and this file's own docstring did exactly what it
    # promised: "the fix is to delete it and keep the ones below."

    def test_gt_228_measured_both_targets_and_nothing_is_blocked_any_more(self):
        records = {r.trigger_id: r for r in plan.planned_records()}
        self.assertEqual(set(records), {153, 154})
        self.assertEqual(
            (records[153].x, records[153].y, records[153].z),
            plan.MEASURED_XYZ[153],
        )
        self.assertEqual(
            (records[154].x, records[154].y, records[154].z),
            plan.MEASURED_XYZ[154],
        )
        self.assertEqual(plan.provisionable_count(), 2)
        self.assertEqual(plan.blocked_rows(), ())

    def test_gt_228_primary_and_backup_values_match_the_coo_letter_not_just_each_other(self):
        # `test_gt_228_measured_both_targets_and_nothing_is_blocked_any_more`
        # above only checks that `planned_records()` copies `MEASURED_XYZ`
        # faithfully -- it is silent if the dict itself holds a transcribed
        # wrong number, and pf-adversary (round `tpuvll`) mutation-tested
        # that gap directly: swapping primary/backup, swapping x/y, and
        # corrupting a digit all left the rest of this file's suite green.
        # These four literals are copied from the two source letters, not
        # from `plan.py`, so a future transcription slip here fails:
        #   notes_to_chief/20260904_1345_COO-DECISION-lane-a-gt228-pass-*
        #   (COO's PRIMARY pick, item 2: rx152 for 153, rx433 for 154)
        #   notes_to_chief/20260904_1331_KA1A-R308-RESULTS-* (all four
        #   raw HUD readings: rx130/rx152 for 153, rx433/rx491 for 154)
        self.assertEqual(plan.MEASURED_XYZ[153], (-5613.8, 4162.5, 186.0))  # rx152, PRIMARY
        self.assertEqual(plan.MEASURED_XYZ[154], (-1563.5, -5275.1, 186.0))  # rx433, PRIMARY
        self.assertEqual(plan.MEASURED_XYZ_BACKUP[153], (-4451.6, 4531.1, 186.0))  # rx130
        self.assertEqual(plan.MEASURED_XYZ_BACKUP[154], (-1720.4, -5251.6, 186.0))  # rx491
        # The two dicts must not share a value between islands or between
        # primary/backup -- that shape would hide exactly the swap mutation
        # pf-adversary tried.
        all_values = [
            plan.MEASURED_XYZ[153],
            plan.MEASURED_XYZ[154],
            plan.MEASURED_XYZ_BACKUP[153],
            plan.MEASURED_XYZ_BACKUP[154],
        ]
        self.assertEqual(len(set(all_values)), 4)

    def test_the_accessor_answers_from_the_table_not_from_none(self):
        # 155 (Slave Market Island) is a real dock row GT-228 did not
        # measure -- only M2's own two targets, 153/154, are in
        # `MEASURED_XYZ` by default.
        self.assertIsNone(plan.xyz_for_trigger_id(155))
        with _WithOnlyMeasuredXYZ({155: (1.5, -2.5, 3.5)}):
            self.assertEqual(plan.xyz_for_trigger_id(155), (1.5, -2.5, 3.5))
            self.assertIsNone(plan.xyz_for_trigger_id(153))

    def test_planned_and_blocked_partition_the_planned_ids(self):
        # Not a restatement of the two above: this is the invariant that
        # holds AFTER the measurement lands too, so a later round cannot
        # produce a destination that is neither planned nor explained.
        for injected in ({}, {153: (1.0, 2.0, 3.0)}):
            with self.subTest(injected=sorted(injected)):
                with _WithMeasuredXYZ(injected):
                    planned = {r.trigger_id for r in plan.planned_records()}
                    blocked = {t for t, _reason in plan.blocked_rows()}
                    self.assertEqual(planned | blocked, set(plan.PLANNED_TRIGGER_IDS))
                    self.assertEqual(planned & blocked, set())

    def test_one_measured_row_turns_the_plan_on_by_data_alone(self):
        with _WithOnlyMeasuredXYZ({153: (100.5, -20.25, 3.0)}):
            records = plan.planned_records()
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.trigger_id, 153)
            self.assertEqual((record.x, record.y, record.z), (100.5, -20.25, 3.0))
            self.assertEqual(record.frame_scene_id, plan.XYZ_FRAME_SCENE_ID)
            self.assertEqual(plan.provisionable_count(), 1)
        # ...and back to GT-228's own two real records once the injection is
        # gone, i.e. the plan reads the dict rather than a snapshot taken at
        # import time.
        self.assertEqual(plan.provisionable_count(), 2)

    def test_a_measured_row_carries_the_dock_tables_own_status_not_a_guess(self):
        with _WithMeasuredXYZ({153: (0.0, 0.0, 0.0), 154: (1.0, 1.0, 1.0)}):
            by_id = {r.trigger_id: r for r in plan.planned_records()}
            row_153 = islands.destination_for_trigger_id(153)
            row_154 = islands.destination_for_trigger_id(154)
            self.assertEqual(by_id[153].wire_scene_id_status, row_153.wire_scene_id_status)
            self.assertEqual(by_id[154].wire_scene_id_status, row_154.wire_scene_id_status)
            self.assertEqual(by_id[153].scene_name_tip_id, row_153.scene_name_tip_id)
            self.assertEqual(by_id[154].scene_name_tip_id, row_154.scene_name_tip_id)
            self.assertEqual(by_id[154].min_level, row_154.min_level)
            # The one that matters: M2's second island is NOT a proven wire
            # scene id, and a round wiring the confirm must see that.
            self.assertEqual(by_id[154].wire_scene_id_status, "CANDIDATE")

    def test_the_plan_covers_m2s_two_targets_and_takes_them_from_the_dock_table(self):
        self.assertEqual(plan.PLANNED_TRIGGER_IDS, islands.M2_TARGET_TRIGGER_IDS)
        self.assertEqual(sorted(plan.PLANNED_TRIGGER_IDS), [153, 154])


class HandleAllocationTests(unittest.TestCase):
    def test_the_handles_of_m2s_two_targets_are_these_exact_numbers(self):
        # Pins the VALUE, not just the round trip: a mutated formula that is
        # still injective (base + ordinal*7 + 3, say) passes every other test
        # in this class and fails this one.
        self.assertEqual(plan.handle_for_trigger_id(153), 0xA099)
        self.assertEqual(plan.handle_for_trigger_id(154), 0xA09A)
        self.assertEqual(plan.trigger_id_for_handle(0xA099), 153)
        self.assertEqual(plan.trigger_id_for_handle(0xA09A), 154)

    def test_every_destination_gets_a_distinct_handle_inside_u16(self):
        handles = [
            plan.handle_for_trigger_id(row.trigger_id)
            for row in islands.DESTINATION_ROWS
        ]
        self.assertNotIn(None, handles)
        self.assertEqual(len(set(handles)), len(handles))
        for handle in handles:
            self.assertGreaterEqual(handle, 0)
            self.assertLessEqual(handle, 0xFFFF)

    def test_a_handle_does_not_move_when_the_dock_table_is_reordered(self):
        # pf-adversary measured an ordinal-based allocation silently
        # renumbering every handle when a row moved, with the whole suite
        # green.  The handle is a function of the destination, so:
        saved = islands.DESTINATION_ROWS
        before = plan.handle_for_trigger_id(153)
        try:
            islands.DESTINATION_ROWS = tuple(reversed(saved))
            self.assertEqual(plan.handle_for_trigger_id(153), before)
            self.assertEqual(plan.trigger_id_for_handle(before), 153)
        finally:
            islands.DESTINATION_ROWS = saved

    def test_ids_that_are_not_destinations_have_no_handle(self):
        # 40 is a sea prop (Black Braid Landmine), 165 is an ocean-travel row
        # with no scene match, 9999 is nothing at all.
        for trigger_id in (40, 165, 9999):
            with self.subTest(trigger_id=trigger_id):
                self.assertIsNone(plan.handle_for_trigger_id(trigger_id))

    def test_the_handle_range_matches_whichever_base_is_configured(self):
        # Both configurations the docstring names, so the documented rollback
        # (base = 0, handle = trigger id) does not walk into a red suite.
        handles = {
            plan.handle_for_trigger_id(row.trigger_id)
            for row in islands.DESTINATION_ROWS
        }
        trigger_ids = set(islands.TRIGGER_NAMES)
        if plan.SURVEY_HANDLE_BASE:
            # The distinctive range: no handle may be confusable with a
            # trigger id, a scene id or a placement index.
            self.assertEqual(handles & (trigger_ids | set(range(0, 512))), set())
        else:
            # The rollback: the handle IS the trigger id, deliberately.
            self.assertEqual(
                handles,
                {row.trigger_id for row in islands.DESTINATION_ROWS},
            )

    def test_an_unknown_handle_resolves_to_nothing(self):
        self.assertIsNone(plan.trigger_id_for_handle(0x0000))
        self.assertIsNone(plan.trigger_id_for_handle(0xFFFF))


class ConfirmResolutionTests(unittest.TestCase):
    def test_no_value_is_issued_by_a_build_that_can_provision_nothing(self):
        # Forced empty: GT-228 has since left 153/154 measured by default,
        # so this reproduces the pre-GT-228 all-refuse shape deliberately
        # rather than by accident of import order.
        with _WithOnlyMeasuredXYZ({}):
            for handle in (0x0000, 153, plan.handle_for_trigger_id(153), 0xFFFF):
                with self.subTest(handle=handle):
                    resolution = plan.confirm_resolution(handle)
                    self.assertFalse(resolution.issued)
                    self.assertIsNone(resolution.trigger_id)
                    self.assertIsNone(resolution.scene_name_tip_id)
                    self.assertIsNone(resolution.wire_scene_id_status)

    def test_allocation_is_not_issuance(self):
        # The distinction the module is built around: a handle can be
        # allocated to a destination and still not be one we ever issued.
        # 155 (Slave Market Island) is a real dock row and gets a real
        # handle, but GT-228 did not measure it -- only M2's own two
        # targets, 153/154, are in `MEASURED_XYZ` by default.
        handle = plan.handle_for_trigger_id(155)
        self.assertEqual(plan.trigger_id_for_handle(handle), 155)
        self.assertFalse(plan.confirm_resolution(handle).issued)

    def test_a_provisioned_handle_resolves_and_its_neighbour_does_not(self):
        with _WithOnlyMeasuredXYZ({153: (0.0, 0.0, 0.0)}):
            mine = plan.handle_for_trigger_id(153)
            resolution = plan.confirm_resolution(mine)
            self.assertTrue(resolution.issued)
            self.assertEqual(resolution.trigger_id, 153)
            self.assertEqual(resolution.wire_scene_id_status, "PROVEN")
            # 154 is allocated but unmeasured in this injection, so its
            # handle is still not ours.
            self.assertFalse(
                plan.confirm_resolution(plan.handle_for_trigger_id(154)).issued
            )

    def test_todays_default_build_issues_both_real_handles(self):
        # GT-228 landed as data-only, so this is the DEFAULT state now --
        # no injection, unlike every other test in this class.
        for trigger_id in (153, 154):
            resolution = plan.confirm_resolution(plan.handle_for_trigger_id(trigger_id))
            self.assertTrue(resolution.issued, trigger_id)
            self.assertEqual(resolution.trigger_id, trigger_id)


class TrialSurveyIdResolutionTests(unittest.TestCase):
    """Round `16uvmp`: the value the first provisioning trial actually writes
    into a record resolves too, and says how strongly."""

    def test_a_trial_value_resolves_to_its_destination_at_low_confidence(self):
        for trigger_id, expected in ((153, 2), (154, 3)):
            with self.subTest(trigger_id=trigger_id):
                record = {r.trigger_id: r for r in plan.planned_records()}[trigger_id]
                value = plan.trial_survey_id(record)
                self.assertEqual(value, expected)
                resolution = plan.confirm_resolution(value)
                self.assertTrue(resolution.issued)
                self.assertEqual(resolution.trigger_id, trigger_id)
                self.assertEqual(resolution.matched_as, "trial")
                self.assertEqual(resolution.confidence, "low")

    def test_a_handle_still_resolves_at_high_confidence(self):
        for trigger_id in (153, 154):
            resolution = plan.confirm_resolution(plan.handle_for_trigger_id(trigger_id))
            with self.subTest(trigger_id=trigger_id):
                self.assertEqual(resolution.matched_as, "handle")
                self.assertEqual(resolution.confidence, "high")

    def test_a_value_that_is_neither_carries_no_match_and_no_confidence(self):
        resolution = plan.confirm_resolution(0x1234)
        self.assertFalse(resolution.issued)
        self.assertIsNone(resolution.matched_as)
        self.assertIsNone(resolution.confidence)

    def test_a_trial_value_of_an_unmeasured_destination_is_not_issued(self):
        # Fail-closed on DATA, same as the handle half: 155 (Slave Market)
        # is a real dock row with a real tip id, and GT-228 measured no XYZ
        # for it, so neither of its two values is ours.
        with _WithOnlyMeasuredXYZ({153: (0.0, 0.0, 0.0)}):
            row = islands.destination_for_trigger_id(155)
            self.assertFalse(plan.confirm_resolution(row.scene_name_tip_id).issued)
            self.assertFalse(
                plan.confirm_resolution(plan.handle_for_trigger_id(155)).issued
            )

    def test_the_handle_reading_wins_when_a_value_could_be_read_either_way(self):
        # Today nothing is ambiguous (handles are 0xA0xx, trial values are
        # single digits), so the precedence is pinned against a SYNTHETIC
        # collision rather than left to be discovered if the plan widens or
        # the documented `SURVEY_HANDLE_BASE = 0` rollback is taken.
        records = plan.planned_records()
        collision = records[1].handle
        forced = [
            records[0]._replace(scene_name_tip_id=collision),
            records[1],
        ]
        with mock.patch.object(plan, "planned_records", lambda: tuple(forced)):
            resolution = plan.confirm_resolution(collision)
            self.assertTrue(resolution.issued)
            self.assertEqual(resolution.matched_as, "handle")
            self.assertEqual(resolution.trigger_id, records[1].trigger_id)

    def test_the_low_range_guard_covers_only_half_the_accepted_set_and_says_so(self):
        # pf-adversary, round `16uvmp`: `HandleAllocationTests` asserts that no
        # HANDLE may be confusable with a trigger id or a low id -- "which is
        # what makes 'did this echo come from us?' a real question" -- and it
        # inspects `handle` only.  The trial values this round started
        # accepting are 2 and 3: both inside that forbidden low range, and
        # both real `Trigger_TIP` rows (Edmund Hidden Treasure / Seafood
        # Cargo).  That is not a bug to fix here -- COO-DECISION 20260904_1345
        # item 1 chose the value and rules the Trigger_TIP names a different
        # namespace until proven otherwise -- but it must be VISIBLE, because
        # it is precisely why the trial reading carries `confidence=low`.
        # BRANCHED ON THE BASE, like the older guard it is about: the
        # docstring's rollback (`SURVEY_HANDLE_BASE = 0`) puts the handles IN
        # the low range on purpose, and a test written to make a gap visible
        # must not be the thing that forbids the documented repair
        # (pf-adversary, second pass this round -- it measured this test going
        # red under the rollback).
        for record in plan.planned_records():
            with self.subTest(trigger_id=record.trigger_id):
                if plan.SURVEY_HANDLE_BASE:
                    self.assertNotIn(record.handle, range(0, 512))
                self.assertIn(plan.trial_survey_id(record), range(0, 512))
                self.assertEqual(
                    plan.confirm_resolution(plan.trial_survey_id(record)).confidence,
                    "low",
                    "a value inside the range the handle guard forbids must "
                    "never be reported as a strong match",
                )

    def test_no_two_destinations_can_claim_the_same_value(self):
        # The property that makes a resolution safe to teleport on: every
        # u16 this build can issue maps to exactly ONE destination.  A
        # widening of the plan that broke it would send a confirming player
        # to the wrong island, so it fails here first.
        issued: dict[int, int] = {}
        for record in plan.planned_records():
            for value in (record.handle, plan.trial_survey_id(record)):
                self.assertNotIn(
                    value, issued,
                    f"u16 {value} is claimed by both trigger {issued.get(value)} "
                    f"and trigger {record.trigger_id}",
                )
                issued[value] = record.trigger_id


class ConsoleAnnotationTests(unittest.TestCase):
    def test_todays_annotation_reflects_gt_228s_two_real_records(self):
        # 0x1234 is not a handle either destination was ever given, so it
        # stays "no" even though the build now provisions 2 records by
        # default (GT-228, R308, PASS).
        self.assertEqual(plan.console_annotation(0x1234), "issued=no provisioned=2")

    def test_the_annotation_never_names_what_the_value_means_to_the_client(self):
        # RE-227 nonclaim 3 and chief 09:10, enforced where the string is
        # BUILT as well as where it is printed -- the hook's own guard test
        # only sees the assembled line.
        with _WithMeasuredXYZ({153: (0.0, 0.0, 0.0), 154: (1.0, 1.0, 1.0)}):
            for handle in (0x1234, plan.handle_for_trigger_id(153)):
                text = plan.console_annotation(handle).lower()
                with self.subTest(handle=handle):
                    self.assertNotIn("island", text)
                    self.assertNotIn("scene", text)
                    self.assertNotIn("trigger", text)
                    self.assertNotIn("prison", text)
                    self.assertNotIn("spice", text)

    def test_the_annotation_moves_when_the_plan_does(self):
        with _WithOnlyMeasuredXYZ({153: (0.0, 0.0, 0.0)}):
            self.assertEqual(
                plan.console_annotation(plan.handle_for_trigger_id(153)),
                "issued=yes provisioned=1",
            )
            self.assertEqual(
                plan.console_annotation(0x1234), "issued=no provisioned=1"
            )

    def test_a_trial_value_annotates_itself_as_the_weak_match_it_is(self):
        # The fragment an attended grader reads.  `confidence=low` is the
        # whole point: without it, `issued=yes` on a single digit reads as
        # proof the record came from us.
        self.assertEqual(
            plan.console_annotation(2),
            "issued=yes match=trial confidence=low provisioned=2",
        )
        # A handle match adds nothing, so the string other tests pin is
        # unchanged by this round.
        self.assertEqual(
            plan.console_annotation(plan.handle_for_trigger_id(153)),
            "issued=yes provisioned=2",
        )

    def test_the_trial_fragment_still_names_nothing_the_client_believes(self):
        # RE-227 nonclaim 3 applies to the new fragment exactly as it does
        # to the old one -- `match=trial` says where the value came from on
        # OUR side and nothing about what it means to the client.
        text = plan.console_annotation(2).lower()
        for forbidden in ("island", "scene", "trigger", "prison", "spice"):
            self.assertNotIn(forbidden, text)
        text.encode("ascii")
        self.assertNotIn("+", text)

    def test_the_annotation_is_ascii_and_carries_no_truncation_marker(self):
        # `+` is how the sibling line marks truncated hex; an annotation that
        # smuggled one in would make that test's `assertNotIn("+", line)`
        # read the wrong thing.
        text = plan.console_annotation(0x1234)
        text.encode("ascii")
        self.assertNotIn("+", text)


class TheThirdComponentTests(unittest.TestCase):
    """The HUD shows two numbers; a record needs three.

    These tests hold the argument that the missing one is a bounded cost --
    and hold each number to what it is actually a measurement OF, because the
    first draft called a four-row spread a whole-scene range and pf-adversary
    measured that as wrong by a factor of 4500.
    """

    def test_the_anchors_are_the_identity_modules_own_island_rows(self):
        expected = sorted(
            (p.identity.name, p.x, p.y, p.z)
            for p in bg3001.shippable_placements()
            if getattr(p.identity, "outfit", None) == "MAP_ISLAND_01"
        )
        self.assertEqual(list(plan.calibration_anchors()), expected)
        self.assertEqual(len(plan.calibration_anchors()), 4)

    def test_those_four_rows_agree_on_a_plane_the_scene_itself_does_not(self):
        self.assertLess(plan.island_plane_z_spread(), 0.1)
        for _name, _x, _y, z in plan.calibration_anchors():
            self.assertAlmostEqual(z, plan.island_plane_z(), delta=0.1)
        # ...and the scene is NOT flat: its shippable placements span far
        # more than that, which is why the spread may never be described as
        # a property of the scene.
        scene_z = [p.z for p in bg3001.shippable_placements()]
        self.assertGreater(max(scene_z) - min(scene_z), 300.0)

    def test_the_plane_moves_when_the_identity_modules_rows_move(self):
        # The mutation that separates a derivation from a literal.
        before = plan.island_plane_z()
        with _WithAnchors(_island_rows(z_shift=10.0)):
            self.assertAlmostEqual(plan.island_plane_z(), before + 10.0, places=6)
            self.assertAlmostEqual(plan.island_plane_z_spread(), 0.068, delta=0.01)
        self.assertAlmostEqual(plan.island_plane_z(), before, places=6)

    def test_no_island_row_at_all_is_a_refusal_not_an_average_over_nothing(self):
        with _WithAnchors(()):
            with self.assertRaises(RuntimeError):
                plan.calibration_anchors()
            with self.assertRaises(RuntimeError):
                plan.island_plane_z()

    def test_a_wrong_third_component_costs_bounded_reach_not_the_contact(self):
        radius = float(plan.CLIENT_CONTACT_RADIUS)
        # Each error named for what it measures, with the cost it actually
        # carries -- no proxy standing in for a range it is not.
        self.assertAlmostEqual(
            plan.horizontal_reach_for_z_error(plan.island_plane_z_spread()),
            radius,
            places=4,
        )
        # island-actor plane (123.6) against the marker table's player plane
        # (90) -- the error that actually applies.
        self.assertGreater(plan.horizontal_reach_for_z_error(33.6), 498.0)
        # the full z range of scene 126's placements: still reaches, but this
        # is 79% of the radius, not 98%.
        worst = plan.horizontal_reach_for_z_error(307.7)
        self.assertGreater(worst, 0.78 * radius)
        self.assertLess(worst, 0.80 * radius)
        # Monotone, and zero once the error alone exceeds the radius.
        self.assertGreater(
            plan.horizontal_reach_for_z_error(10.0),
            plan.horizontal_reach_for_z_error(200.0),
        )
        self.assertEqual(plan.horizontal_reach_for_z_error(radius), 0.0)
        self.assertEqual(plan.horizontal_reach_for_z_error(radius * 2), 0.0)

    def test_a_hud_pair_becomes_a_triple_on_the_island_plane(self):
        triple = plan.record_xyz_from_hud(3050, 232)
        self.assertEqual(triple[0], 3050.0)
        self.assertEqual(triple[1], 232.0)
        self.assertEqual(triple[2], plan.island_plane_z())
        for value in triple:
            self.assertIsInstance(value, float)


class NotASendPathTests(unittest.TestCase):
    def test_the_plan_returns_no_bytes_from_any_public_function(self):
        with _WithMeasuredXYZ({153: (1.0, 2.0, 3.0)}):
            for value in (
                plan.planned_records(),
                plan.blocked_rows(),
                plan.confirm_resolution(plan.handle_for_trigger_id(153)),
                plan.console_annotation(1),
                plan.xyz_for_trigger_id(153),
                plan.provisionable_count(),
            ):
                self.assertNotIsInstance(value, (bytes, bytearray))

    def test_the_plan_does_not_reach_the_record_encoder(self):
        # That module's own grep guard forbids any other file in this
        # repository from even naming it; this asserts the same boundary from
        # the other side, so a later round wiring the send path has to touch
        # both guards deliberately.
        source = (
            ROOT / "src" / "pirateforce_foundation" / "world_m2_survey_plan.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("survey_record", source)
        self.assertNotIn("make_runtime_vital", source)


if __name__ == "__main__":
    unittest.main()
