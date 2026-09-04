"""LANE-A / M2: the survey plan is fail-closed on measured XYZ, and its
handles are the server's own.

The plan module exists to be EMPTY today and correct the day GT-228 reports.
Both halves need a test: an empty plan that would stay empty after the
measurement lands would be worthless, so every "nothing is provisionable"
assertion here has a sibling that injects a measurement and proves the same
function then answers differently.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

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


class FailClosedOnMeasurementTests(unittest.TestCase):
    def test_no_xyz_is_measured_yet(self):
        # The state of M2 in one assertion.  When GT-228 lands and this test
        # fails, the fix is to delete it and keep the two below.
        self.assertEqual(plan.MEASURED_XYZ, {})

    def test_nothing_is_provisionable_and_every_target_says_why(self):
        self.assertEqual(plan.planned_records(), ())
        self.assertEqual(plan.provisionable_count(), 0)
        self.assertEqual(
            plan.blocked_rows(),
            tuple(
                (trigger_id, plan.BLOCKED_XYZ_UNMEASURED)
                for trigger_id in plan.PLANNED_TRIGGER_IDS
            ),
        )

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
        with _WithMeasuredXYZ({153: (100.5, -20.25, 3.0)}):
            records = plan.planned_records()
            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record.trigger_id, 153)
            self.assertEqual((record.x, record.y, record.z), (100.5, -20.25, 3.0))
            self.assertEqual(plan.provisionable_count(), 1)
        # ...and off again once the injection is gone, i.e. the plan reads
        # the dict rather than a snapshot taken at import time.
        self.assertEqual(plan.provisionable_count(), 0)

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

    def test_a_handle_round_trips_back_to_its_destination(self):
        for row in islands.DESTINATION_ROWS:
            with self.subTest(trigger_id=row.trigger_id):
                handle = plan.handle_for_trigger_id(row.trigger_id)
                self.assertEqual(plan.trigger_id_for_handle(handle), row.trigger_id)

    def test_ids_that_are_not_destinations_have_no_handle(self):
        # 40 is a sea prop (Black Braid Landmine), 165 is an ocean-travel row
        # with no scene match, 9999 is nothing at all.
        for trigger_id in (40, 165, 9999):
            with self.subTest(trigger_id=trigger_id):
                self.assertIsNone(plan.handle_for_trigger_id(trigger_id))

    def test_the_handle_range_does_not_collide_with_the_ids_it_must_be_told_apart_from(self):
        # The whole reason the base is 0xA000 and not 152: a handle must not
        # be confusable with a trigger id, a scene id or a placement index,
        # or "did this echo come from us" has no answer.
        handles = {
            plan.handle_for_trigger_id(row.trigger_id)
            for row in islands.DESTINATION_ROWS
        }
        collidable = set(islands.TRIGGER_NAMES) | set(range(0, 512))
        self.assertEqual(handles & collidable, set())

    def test_an_unknown_handle_resolves_to_nothing(self):
        self.assertIsNone(plan.trigger_id_for_handle(0x0000))
        self.assertIsNone(plan.trigger_id_for_handle(0xFFFF))


class ConfirmResolutionTests(unittest.TestCase):
    def test_no_value_is_issued_by_a_build_that_can_provision_nothing(self):
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
        handle = plan.handle_for_trigger_id(153)
        self.assertEqual(plan.trigger_id_for_handle(handle), 153)
        self.assertFalse(plan.confirm_resolution(handle).issued)

    def test_a_provisioned_handle_resolves_and_its_neighbour_does_not(self):
        with _WithMeasuredXYZ({153: (0.0, 0.0, 0.0)}):
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


class ConsoleAnnotationTests(unittest.TestCase):
    def test_todays_annotation_is_the_negative_result_spelled_out(self):
        self.assertEqual(plan.console_annotation(0x1234), "issued=no provisioned=0")

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
        with _WithMeasuredXYZ({153: (0.0, 0.0, 0.0)}):
            self.assertEqual(
                plan.console_annotation(plan.handle_for_trigger_id(153)),
                "issued=yes provisioned=1",
            )
            self.assertEqual(
                plan.console_annotation(0x1234), "issued=no provisioned=1"
            )

    def test_the_annotation_is_ascii_and_carries_no_truncation_marker(self):
        # `+` is how the sibling line marks truncated hex; an annotation that
        # smuggled one in would make that test's `assertNotIn("+", line)`
        # read the wrong thing.
        text = plan.console_annotation(0x1234)
        text.encode("ascii")
        self.assertNotIn("+", text)


class TheThirdComponentTests(unittest.TestCase):
    """GT-228's HUD shows two numbers; the record needs three.

    These tests hold the argument that the missing one is a bounded cost
    rather than a blocker -- and hold it to the identity module's own rows,
    so a plane averaged from somewhere else cannot creep in.
    """

    def test_the_anchors_are_the_identity_modules_own_island_rows(self):
        expected = sorted(
            (p.identity.name, p.x, p.y, p.z)
            for p in bg3001.shippable_placements()
            if getattr(p.identity, "outfit", None) == "MAP_ISLAND_01"
        )
        self.assertEqual(list(plan.CALIBRATION_ANCHORS), expected)
        self.assertEqual(len(plan.CALIBRATION_ANCHORS), 4)

    def test_every_island_in_the_sailing_scene_sits_on_one_plane(self):
        # The measurement the third component rests on: 0.068 units across
        # the whole scene.  A tenth of a unit is the generous bound.
        self.assertLess(plan.ISLAND_PLANE_Z_SPREAD, 0.1)
        for _name, _x, _y, z in plan.CALIBRATION_ANCHORS:
            self.assertAlmostEqual(z, plan.ISLAND_PLANE_Z, delta=0.1)

    def test_no_island_row_at_all_is_a_refusal_not_an_average_over_nothing(self):
        saved = bg3001.shippable_placements
        try:
            bg3001.shippable_placements = lambda: ()
            with self.assertRaises(RuntimeError):
                plan._island_plane_or_raise()
        finally:
            bg3001.shippable_placements = saved

    def test_the_plane_moves_when_the_identity_modules_rows_move(self):
        # The mutation that separates a derivation from a literal: shift the
        # identity module's island rows by a known amount, re-import, and the
        # plane must shift with them.  A hardcoded 123.6 passes every other
        # test in this class and fails this one.
        import dataclasses
        import importlib

        saved = bg3001.shippable_placements
        shift = 10.0

        def shifted():
            rows = []
            for placement in saved():
                if getattr(placement.identity, "outfit", None) == "MAP_ISLAND_01":
                    placement = dataclasses.replace(placement, z=placement.z + shift)
                rows.append(placement)
            return tuple(rows)

        try:
            before = plan.ISLAND_PLANE_Z
            bg3001.shippable_placements = shifted
            importlib.reload(plan)
            self.assertAlmostEqual(plan.ISLAND_PLANE_Z, before + shift, places=6)
            self.assertAlmostEqual(plan.ISLAND_PLANE_Z_SPREAD, 0.068, delta=0.01)
        finally:
            bg3001.shippable_placements = saved
            importlib.reload(plan)
        self.assertAlmostEqual(plan.ISLAND_PLANE_Z, before, places=6)
        self.assertEqual(plan.MEASURED_XYZ, {})

    def test_a_wrong_third_component_costs_bounded_reach_not_the_contact(self):
        radius = float(plan.CLIENT_CONTACT_RADIUS)
        # The spread we actually measured: indistinguishable from perfect.
        self.assertAlmostEqual(
            plan.horizontal_reach_for_z_error(plan.ISLAND_PLANE_Z_SPREAD),
            radius,
            places=4,
        )
        # An error the size of this scene's whole prop height range.
        self.assertGreater(plan.horizontal_reach_for_z_error(100.0), 0.97 * radius)
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
        self.assertEqual(triple[2], plan.ISLAND_PLANE_Z)
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
