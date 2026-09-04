"""LANE-A / M2: the arrival half's INPUTS are well-formed, and every claim
this module makes about that is pinned by something that fails when it stops
being true.

Two halves need proving and they fail in opposite directions:

* the ORDER is fail-closed on the handle -- with `MEASURED_XYZ` empty every
  possible u16 refuses -- and an "everything refuses" module that would still
  refuse after GT-228 lands is worthless, so every refusal assertion here has
  a sibling that injects a measurement and proves the same call then answers
  with a complete order;
* the READINESS must not report 2/2 out of a constant, and must not report it
  out of a check that stopped checking.  Each thing it folds together has a
  test that breaks that one thing and watches the count fall.

MOST OF THIS FILE EXISTS BECAUSE A MUTATION SURVIVED.  pf-adversary ran the
module against 20-odd mutations; the ones that lived are listed against the
tests that now kill them:

    `_SYNTHETIC_HEADING`/`_SYNTHETIC_SEQ` changed   -> TheSyntheticRow
    `persist_allowed` replaced by a constant True   -> ...persist_allowed_is_read
    the door consulted despite a disagreement       -> ...the_door_is_not_asked
    `console_report` dropping `refusal=`            -> TheConsoleSurfaces
    `door_refusal()` made the identity function     -> ...tagged_with_its_owner
    `TOKEN` set to the hook's own token             -> ...token_is_distinct
    the second resolve ignoring the registry        -> ...one_resolution_not_two
    `except SceneEntryRefused` widened to Exception -> ...a_broken_pin_propagates
    the no-registry-row branch claiming names       -> ...an_absence_is_not_a_
"""
from __future__ import annotations

import dataclasses
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_island_dock_table as islands  # noqa: E402
from pirateforce_foundation import world_m2_arrival as arrival  # noqa: E402
from pirateforce_foundation import world_m2_survey_plan as plan  # noqa: E402
from pirateforce_foundation import world_scene_entry as entry_door  # noqa: E402
from pirateforce_foundation import world_scene_travel as travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_enter_instance_log as hooklog,
)


PRISON_EXILE_TRIGGER = 153
SPICE_PARADISE_TRIGGER = 154
PORT_ROYAL_TRIGGER = 152          # home: the door keeps the row it is given
HELL_VOLCANIC_TRIGGER = 161       # the one measured name disagreement


class _WithMeasuredXYZ:
    """The plan's own test idiom: real coordinates in, restored on the way
    out.  Injecting a measurement is the only way to reach the branches that
    matter once GT-228 reports, and nothing else in this repository may leave
    `MEASURED_XYZ` non-empty."""

    def __init__(self, rows):
        self._rows = rows
        self._saved = {}

    def __enter__(self):
        self._saved = dict(plan.MEASURED_XYZ)
        plan.MEASURED_XYZ.update(self._rows)
        return plan

    def __exit__(self, *_exc):
        plan.MEASURED_XYZ.clear()
        plan.MEASURED_XYZ.update(self._saved)
        return False


class _WithOnlyMeasuredXYZ(_WithMeasuredXYZ):
    """Like `_WithMeasuredXYZ`, but empties the dict first.  Needed for the
    one test below that must see the pre-GT-228 all-refuse state, now that
    GT-228 has left both real M2 targets measured by default."""

    def __enter__(self):
        self._saved = dict(plan.MEASURED_XYZ)
        plan.MEASURED_XYZ.clear()
        plan.MEASURED_XYZ.update(self._rows)
        return plan


class _WithPlannedIds:
    """`PLANNED_TRIGGER_IDS` swapped and restored."""

    def __init__(self, ids):
        self._ids = tuple(ids)
        self._saved = ()

    def __enter__(self):
        self._saved = plan.PLANNED_TRIGGER_IDS
        plan.PLANNED_TRIGGER_IDS = self._ids
        return plan

    def __exit__(self, *_exc):
        plan.PLANNED_TRIGGER_IDS = self._saved
        return False


def _xyz_for(trigger_ids):
    """Plausible coordinates for the injection above, derived rather than
    typed: the HUD-to-record conversion COO 1147 sanctioned.  Their VALUES do
    not matter to any assertion here -- only that the plan issues handles."""
    return {
        trigger_id: plan.record_xyz_from_hud(3050.0 + index, 232.0 + index)
        for index, trigger_id in enumerate(trigger_ids)
    }


def _registry_with(**changes):
    """The real registry with one destination row edited.

    Built from the loaded registry rather than from a hand-made stub, so a
    test that breaks one assumption still exercises every other field exactly
    as the shipped JSON carries it.
    """
    n_id = changes.pop("n_id")
    loaded = travel.load_scene_registry()
    rows = tuple(
        dataclasses.replace(row, **changes) if row.n_id == n_id else row
        for row in loaded.destinations
    )
    return travel.SceneRegistry(destinations=rows)


def _registry_without(n_id):
    loaded = travel.load_scene_registry()
    return travel.SceneRegistry(
        destinations=tuple(r for r in loaded.destinations if r.n_id != n_id)
    )


class TheCrosswalkIsCheckedNotAssumed(unittest.TestCase):
    def test_both_m2_destinations_agree_on_name_and_model(self):
        rows = {row.trigger_id: row for row in arrival.crosswalk_rows()}
        self.assertEqual(
            set(rows), {PRISON_EXILE_TRIGGER, SPICE_PARADISE_TRIGGER}
        )
        for row in rows.values():
            self.assertIs(row.names_agree, True, row)
            self.assertIs(row.models_agree, True, row)

    def test_the_agreement_is_read_off_both_sources_not_off_one(self):
        registry = travel.load_scene_registry()
        for trigger_id in (PRISON_EXILE_TRIGGER, SPICE_PARADISE_TRIGGER):
            dock = islands.destination_for_trigger_id(trigger_id)
            row = arrival.crosswalk_row(trigger_id)
            target = registry[dock.scene_name_tip_id]
            self.assertEqual(row.dock_name, dock.name)
            self.assertEqual(row.registry_name, target.scene_name_ascii)
            self.assertEqual(row.registry_model_id, target.model_id)
            self.assertEqual(row.dock_scene_model, dock.scene_model)

    def test_a_name_and_a_model_disagreement_are_reported_apart(self):
        # A name difference between two renderings of one Chinese name is not
        # the same event as a model-id mismatch, and an attended tester must
        # not be told the id crosswalk is broken when it is a translation.
        by_name = arrival.crosswalk_row(
            SPICE_PARADISE_TRIGGER,
            _registry_with(n_id=3, scene_name_ascii="Somewhere Else"),
        )
        self.assertIs(by_name.names_agree, False)
        self.assertEqual(
            by_name.refusal, arrival.ARRIVAL_REFUSED_NAME_DISAGREEMENT
        )
        by_model = arrival.crosswalk_row(
            PRISON_EXILE_TRIGGER, _registry_with(n_id=2, model_id="BG9999")
        )
        self.assertIs(by_model.models_agree, False)
        self.assertEqual(
            by_model.refusal, arrival.ARRIVAL_REFUSED_MODEL_DISAGREEMENT
        )
        self.assertNotEqual(by_name.refusal, by_model.refusal)

    def test_the_measured_translation_mismatch_is_still_refused(self):
        # Trigger 161: "Hell Volcanic Island" (Trigger_TIP) against the
        # registry's "Hell Volcano Island".  Fail-closed is the right answer
        # -- this lane does not fuzzy-match names to widen a plan -- but it
        # must be refused as a NAME difference, and the docstring says so.
        row = arrival.crosswalk_row(HELL_VOLCANIC_TRIGGER)
        self.assertIs(row.names_agree, False)
        self.assertEqual(
            row.refusal, arrival.ARRIVAL_REFUSED_NAME_DISAGREEMENT
        )
        self.assertIs(row.models_agree, True)

    def test_the_door_is_not_asked_when_the_identity_is_in_doubt(self):
        # Documented behaviour, and a surviving mutation before this test:
        # "can we compose an arrival for scene 3" is meaningless while it is
        # unsettled that scene 3 is the destination.
        row = arrival.crosswalk_row(
            SPICE_PARADISE_TRIGGER,
            _registry_with(n_id=3, scene_name_ascii="Somewhere Else"),
        )
        self.assertFalse(row.door_was_asked)
        self.assertIsNone(row.entry)

    def test_an_absent_model_column_is_not_a_disagreement(self):
        dock = islands.destination_for_trigger_id(PRISON_EXILE_TRIGGER)
        without_model = dock._replace(scene_model=None)
        saved = islands.destination_for_trigger_id
        try:
            islands.destination_for_trigger_id = (
                lambda t: without_model if t == PRISON_EXILE_TRIGGER else saved(t)
            )
            row = arrival.crosswalk_row(PRISON_EXILE_TRIGGER)
        finally:
            islands.destination_for_trigger_id = saved
        self.assertIs(row.models_agree, True)
        self.assertIsNone(row.refusal)

    def test_an_absence_is_not_a_disagreement_when_there_is_no_row_at_all(self):
        # The mirror of the test above, and the one pf-adversary measured
        # missing: with no registry row NOTHING was compared, so the two
        # columns must be None, not False, and the console must not print
        # "names_agree=no" about a comparison that never happened.
        row = arrival.crosswalk_row(
            SPICE_PARADISE_TRIGGER, _registry_without(3)
        )
        self.assertEqual(row.refusal, arrival.ARRIVAL_REFUSED_NO_REGISTRY_ROW)
        self.assertIsNone(row.names_agree)
        self.assertIsNone(row.models_agree)
        self.assertIsNone(row.registry_name)
        self.assertIsNone(row.registry_model_id)
        self.assertIsNone(row.door_open_at_login)
        self.assertIsNone(row.confirmed_by_a_client)
        self.assertFalse(row.door_was_asked)
        report = arrival.console_report(_registry_without(3))
        self.assertIn("names_agree=n_a", report)
        self.assertIn("models_agree=n_a", report)
        self.assertIn("client_confirmed=n_a", report)

    def test_a_door_that_said_yes_is_told_apart_from_one_never_asked(self):
        asked = arrival.crosswalk_row(PRISON_EXILE_TRIGGER)
        self.assertTrue(asked.door_was_asked)
        self.assertIsNone(asked.door_refusal_reason)
        never = arrival.crosswalk_row(HELL_VOLCANIC_TRIGGER)
        self.assertFalse(never.door_was_asked)
        self.assertIsNone(never.door_refusal_reason)

    def test_a_trigger_id_that_is_not_a_destination_is_none_not_a_refusal(self):
        self.assertIsNone(arrival.crosswalk_row(40))


class TheRegistryKillSwitchIsReadHere(unittest.TestCase):
    """`via_login=False` stops the DOOR reading `login_entry_allowed`, so
    this module reads it.  An earlier draft of this round pinned the bypass
    instead; these tests exist so that cannot come back quietly."""

    def test_a_shut_door_refuses_and_drops_the_count(self):
        registry = _registry_with(n_id=3, login_entry_allowed=False)
        row = arrival.crosswalk_row(SPICE_PARADISE_TRIGGER, registry)
        self.assertEqual(row.refusal, arrival.ARRIVAL_REFUSED_DOOR_SHUT)
        self.assertIs(row.door_open_at_login, False)
        self.assertEqual(arrival.arrival_readiness(registry), (1, 2))

    def test_a_shut_door_is_not_even_asked_to_compose(self):
        registry = _registry_with(n_id=2, login_entry_allowed=False)
        row = arrival.crosswalk_row(PRISON_EXILE_TRIGGER, registry)
        self.assertFalse(row.door_was_asked)
        self.assertIsNone(row.entry)

    def test_an_issued_handle_into_a_shut_door_still_refuses(self):
        registry = _registry_with(n_id=2, login_entry_allowed=False)
        with _WithMeasuredXYZ(_xyz_for((PRISON_EXILE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER), registry
            )
        self.assertEqual(order.refusal, arrival.ARRIVAL_REFUSED_DOOR_SHUT)
        self.assertIsNone(order.teleport_fields)
        self.assertIsNone(order.position)
        # The fields that WERE established survive the refusal.
        self.assertEqual(order.trigger_id, PRISON_EXILE_TRIGGER)
        self.assertEqual(order.wire_scene_id, 2)

    def test_both_doors_shut_is_zero_of_two_not_two_of_two(self):
        registry = travel.load_scene_registry()
        rows = tuple(
            dataclasses.replace(row, login_entry_allowed=False)
            if row.n_id in (2, 3) else row
            for row in registry.destinations
        )
        shut = travel.SceneRegistry(destinations=rows)
        self.assertEqual(arrival.arrival_readiness(shut), (0, 2))
        self.assertEqual(arrival.console_annotation(shut), "arrival_plan=0/2")


class TheSyntheticRow(unittest.TestCase):
    def test_every_field_of_it_is_pinned(self):
        # Heading and seq both flow into the persisted Position, and both
        # were unpinned mutations before this test.
        row = arrival.synthetic_row(3)
        self.assertEqual(row.scene_id, 3)
        self.assertEqual(row.scene_seq, 0)
        self.assertEqual((row.x, row.y, row.z), (0.0, 0.0, 0.0))
        self.assertEqual(row.heading, 0.0)

    def test_a_door_that_hands_the_row_straight_back_is_refused(self):
        # Trigger 152 (Port Royal) is a real dock row one plan-widening line
        # away, and `resolve_entry`'s home branch keeps the row it is given.
        # Fed our fabricated zeroes that produced a "deliverable" order whose
        # persisted Position was the scene origin, thousands of units from
        # the real spawn -- the GT-106 shape.  It must refuse instead.
        with _WithPlannedIds((PORT_ROYAL_TRIGGER,)):
            row = arrival.crosswalk_row(PORT_ROYAL_TRIGGER)
            self.assertEqual(
                row.refusal,
                arrival.ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW,
            )
            self.assertEqual(arrival.arrival_readiness(), (0, 1))
            with _WithMeasuredXYZ(_xyz_for((PORT_ROYAL_TRIGGER,))):
                order = arrival.arrival_order(
                    plan.handle_for_trigger_id(PORT_ROYAL_TRIGGER)
                )
        self.assertEqual(
            order.refusal, arrival.ARRIVAL_REFUSED_DOOR_KEPT_THE_SYNTHETIC_ROW
        )
        self.assertIsNone(order.position)

    def test_the_real_targets_do_not_come_back_as_the_synthetic_row(self):
        for trigger_id, wire_scene_id in (
            (PRISON_EXILE_TRIGGER, 2), (SPICE_PARADISE_TRIGGER, 3)
        ):
            row = arrival.crosswalk_row(trigger_id)
            self.assertNotEqual(
                row.entry.position, arrival.synthetic_row(wire_scene_id)
            )


class TheReadinessCountIsDerived(unittest.TestCase):
    def test_todays_answer_is_two_of_two(self):
        self.assertEqual(arrival.arrival_readiness(), (2, 2))

    def test_the_denominator_follows_the_survey_plan_not_a_literal(self):
        with _WithPlannedIds((PRISON_EXILE_TRIGGER,)):
            self.assertEqual(arrival.arrival_readiness(), (1, 1))
        self.assertEqual(arrival.arrival_readiness(), (2, 2))

    def test_a_planned_id_with_no_destination_row_still_counts_as_planned(self):
        with _WithPlannedIds((PRISON_EXILE_TRIGGER, 40)):
            self.assertEqual(arrival.arrival_readiness(), (1, 2))

    def test_a_door_refusal_drops_the_count_and_keeps_the_doors_own_word(self):
        registry = _registry_with(n_id=2, spawn=None, spawn_provenance=None)
        self.assertEqual(arrival.arrival_readiness(registry), (1, 2))
        row = arrival.crosswalk_row(PRISON_EXILE_TRIGGER, registry)
        self.assertEqual(
            row.door_refusal_reason, entry_door.REFUSED_NO_PINNED_SPAWN
        )
        self.assertTrue(row.door_was_asked)

    def test_a_missing_registry_row_drops_the_count(self):
        self.assertEqual(arrival.arrival_readiness(_registry_without(3)), (1, 2))


class TheOrderIsFailClosedOnTheHandle(unittest.TestCase):
    def test_an_empty_plan_refuses_every_handle(self):
        # The pre-GT-228 shape, reproduced by forcing the dict empty: GT-228
        # (R308, PASS) has since left both real targets measured by default,
        # which is exactly what `test_the_module_is_not_merely_always_
        # refusing` below and `test_todays_default_plan_delivers_for_both_
        # m2_targets` prove.
        with _WithOnlyMeasuredXYZ({}):
            for handle in (0x0000, 0x1234, 0xFFFF,
                           plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER),
                           plan.handle_for_trigger_id(SPICE_PARADISE_TRIGGER)):
                order = arrival.arrival_order(handle)
                self.assertEqual(
                    order.refusal, arrival.ARRIVAL_REFUSED_HANDLE_NOT_ISSUED
                )
                self.assertFalse(order.deliverable)

    def test_todays_default_plan_delivers_for_both_m2_targets(self):
        # GT-228 landed as data-only, so this is the DEFAULT state now --
        # no injection, unlike every other test in this class.
        for trigger_id in (PRISON_EXILE_TRIGGER, SPICE_PARADISE_TRIGGER):
            order = arrival.arrival_order(plan.handle_for_trigger_id(trigger_id))
            self.assertIsNone(order.refusal, order)
            self.assertTrue(order.deliverable)
            self.assertEqual(order.trigger_id, trigger_id)

    def test_todays_default_plan_also_delivers_for_the_value_the_trial_sends(self):
        # Round `16uvmp`: the confirm frame of the FIRST provisioning trial
        # carries the record's own u16, which that trial sets to the
        # destination number (2/3), not to this plan's 0xA0xx handle.  Before
        # this, every one of those confirms refused -- so a perfect attended
        # run of GT-233 would have put the player nowhere and been graded as
        # a failure of the hypothesis it was testing.
        for trigger_id, wire_scene_id in (
            (PRISON_EXILE_TRIGGER, 2), (SPICE_PARADISE_TRIGGER, 3),
        ):
            record = {r.trigger_id: r for r in plan.planned_records()}[trigger_id]
            order = arrival.arrival_order(plan.trial_survey_id(record))
            with self.subTest(trigger_id=trigger_id):
                self.assertIsNone(order.refusal, order)
                self.assertTrue(order.deliverable)
                self.assertEqual(order.trigger_id, trigger_id)
                self.assertEqual(order.wire_scene_id, wire_scene_id)
                # The two readings of the same confirm land in the same
                # place; only the console's confidence fragment differs.
                by_handle = arrival.arrival_order(
                    plan.handle_for_trigger_id(trigger_id)
                )
                self.assertEqual(order.position, by_handle.position)
                self.assertEqual(order.teleport_fields, by_handle.teleport_fields)

    def test_the_trial_value_still_refuses_when_the_plan_cannot_provision(self):
        with _WithOnlyMeasuredXYZ({}):
            for value in (2, 3):
                order = arrival.arrival_order(value)
                with self.subTest(value=value):
                    self.assertEqual(
                        order.refusal, arrival.ARRIVAL_REFUSED_HANDLE_NOT_ISSUED
                    )
                    self.assertFalse(order.deliverable)

    def test_a_refusal_carries_none_where_a_zero_would_be_read_as_an_answer(self):
        order = arrival.arrival_order(0x1234)
        for field in (
            order.wire_scene_id, order.teleport_fields, order.position,
            order.min_level, order.persist_allowed, order.population_source,
            order.return_ticket_required, order.relocation_is_an_artefact,
        ):
            self.assertIsNone(field)
        self.assertEqual(order.handle, 0x1234)

    def test_the_module_is_not_merely_always_refusing(self):
        targets = (PRISON_EXILE_TRIGGER, SPICE_PARADISE_TRIGGER)
        with _WithMeasuredXYZ(_xyz_for(targets)):
            for trigger_id in targets:
                order = arrival.arrival_order(
                    plan.handle_for_trigger_id(trigger_id)
                )
                self.assertIsNone(order.refusal, order)
                self.assertTrue(order.deliverable)
                self.assertEqual(order.trigger_id, trigger_id)

    def test_a_complete_order_is_the_entry_doors_own_answer_not_a_copy(self):
        with _WithMeasuredXYZ(_xyz_for((SPICE_PARADISE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(SPICE_PARADISE_TRIGGER)
            )
        expected = entry_door.resolve_entry(
            arrival.synthetic_row(3), emit=lambda _line: None, via_login=False
        )
        self.assertEqual(order.teleport_fields, expected.teleport_fields)
        self.assertEqual(order.position, expected.position)
        self.assertEqual(order.population_source, expected.population_source)
        self.assertEqual(
            order.return_ticket_required, expected.return_ticket_required
        )
        self.assertEqual(order.wire_scene_id, 3)
        self.assertEqual(order.destination_name, "Spice Paradise Island")
        self.assertEqual(order.min_level, 25)

    def test_the_teleport_tuple_still_matches_the_travel_modules_own(self):
        registry = travel.load_scene_registry()
        with _WithMeasuredXYZ(_xyz_for((PRISON_EXILE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER)
            )
        self.assertEqual(
            order.teleport_fields, travel.login_teleport_fields(registry[2])
        )

    def test_persist_allowed_is_read_from_the_row_not_assumed(self):
        # `assertTrue(order.persist_allowed)` matched a constant True before
        # this test; drive the field from both sides.
        registry = _registry_with(n_id=3, persist_position_allowed=False)
        with _WithMeasuredXYZ(_xyz_for((SPICE_PARADISE_TRIGGER,))):
            handle = plan.handle_for_trigger_id(SPICE_PARADISE_TRIGGER)
            self.assertIs(
                arrival.arrival_order(handle, registry).persist_allowed, False
            )
            self.assertIs(arrival.arrival_order(handle).persist_allowed, True)

    def test_the_relocation_report_is_flagged_as_an_artefact(self):
        # True by construction on this path -- the synthetic row is (0,0,0)
        # and no M2 destination has pinned ground -- so it must never be read
        # as a fact about a player's stored position.
        with _WithMeasuredXYZ(_xyz_for((PRISON_EXILE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER)
            )
        self.assertIs(order.relocation_is_an_artefact, True)

    def test_the_order_does_not_carry_the_doors_console_lines(self):
        # They name a scene and an island beside a frame with bytes_out=0.
        self.assertNotIn("console_lines", arrival.ArrivalOrder._fields)
        self.assertNotIn("entry", arrival.ArrivalOrder._fields)

    def test_the_door_lines_are_swallowed_not_printed(self):
        # The paragraph justifying the swallow was defended by no test at
        # all: `emit=print` left the whole suite green.
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            arrival.arrival_readiness()
            arrival.arrival_order(0xA099)
        self.assertEqual(buffer.getvalue(), "")

    def test_one_resolution_not_two_and_it_honours_the_caller_registry(self):
        # The order must reuse the crosswalk's resolution: a second call
        # ignoring the caller's registry was a surviving mutation, and it is
        # also what put a second full resolution on the per-frame path.
        calls = []
        real = entry_door.resolve_entry

        def counting(stored, **kwargs):
            calls.append(kwargs.get("registry"))
            return real(stored, **kwargs)

        registry = _registry_with(n_id=2, persist_position_allowed=False)
        entry_door.resolve_entry = counting
        try:
            with _WithMeasuredXYZ(_xyz_for((PRISON_EXILE_TRIGGER,))):
                order = arrival.arrival_order(
                    plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER), registry
                )
        finally:
            entry_door.resolve_entry = real
        self.assertEqual(len(calls), 1)
        self.assertIs(calls[0], registry)
        self.assertIs(order.persist_allowed, False)

    def test_a_broken_pin_propagates_rather_than_becoming_a_quiet_refusal(self):
        # Deliberate, and unpinned in BOTH directions before this test: a
        # later round could have turned a malformed pin into arrival_plan=1/2.
        real = travel.load_scene_registry

        def broken(*_a, **_k):
            raise ValueError("scene registry root is incomplete")

        arrival.forget_cached_registry()
        travel.load_scene_registry = broken
        try:
            with self.assertRaises(ValueError):
                arrival.arrival_readiness()
            # An unissued handle never reaches the pin -- it refuses first --
            # so the order side has to be driven with an issued one.
            with _WithMeasuredXYZ(_xyz_for((PRISON_EXILE_TRIGGER,))):
                with self.assertRaises(ValueError):
                    arrival.arrival_order(
                        plan.handle_for_trigger_id(PRISON_EXILE_TRIGGER)
                    )
        finally:
            travel.load_scene_registry = real
            arrival.forget_cached_registry()
        self.assertEqual(arrival.arrival_readiness(), (2, 2))

    def test_only_the_doors_own_refusal_is_caught_not_every_exception(self):
        # Widening `except SceneEntryRefused` to `except Exception` survived
        # the suite: it would turn a real defect inside the door into a quiet
        # `arrival_plan=1/2` that reads like a data gap.  The narrow catch is
        # deliberate and is pinned here in the direction nothing covered.
        real = entry_door.resolve_entry

        def exploding(*_a, **_k):
            raise RuntimeError("a defect inside the door, not a refusal")

        entry_door.resolve_entry = exploding
        try:
            with self.assertRaises(RuntimeError):
                arrival.crosswalk_row(PRISON_EXILE_TRIGGER)
            with self.assertRaises(RuntimeError):
                arrival.arrival_readiness()
        finally:
            entry_door.resolve_entry = real
        self.assertEqual(arrival.arrival_readiness(), (2, 2))

    def test_the_cached_load_is_the_none_path_only_and_can_be_dropped(self):
        arrival.forget_cached_registry()
        # Built BEFORE the counter goes in: the helper loads the pin itself.
        explicit = _registry_without(3)
        calls = []
        real = travel.load_scene_registry

        def counting(*a, **k):
            calls.append(1)
            return real(*a, **k)

        travel.load_scene_registry = counting
        try:
            arrival.arrival_readiness()
            arrival.arrival_readiness()
            arrival.arrival_readiness(explicit)
        finally:
            travel.load_scene_registry = real
        self.assertEqual(len(calls), 1)

    def test_it_never_raises_whatever_it_is_handed(self):
        for handle in (-1, 0, 2 ** 32, 0xA099):
            self.assertIsInstance(
                arrival.arrival_order(handle), arrival.ArrivalOrder
            )

    def test_every_row_readiness_counted_yields_a_deliverable_order(self):
        ready_ids = [
            row.trigger_id for row in arrival.crosswalk_rows() if row.ready
        ]
        self.assertTrue(ready_ids)
        with _WithMeasuredXYZ(_xyz_for(tuple(ready_ids))):
            for trigger_id in ready_ids:
                order = arrival.arrival_order(
                    plan.handle_for_trigger_id(trigger_id)
                )
                self.assertTrue(order.deliverable, order)
                self.assertIsNotNone(order.teleport_fields)

    def test_a_row_readiness_refused_refuses_the_order_for_the_same_reason(self):
        registry = _registry_with(n_id=3, spawn=None, spawn_provenance=None)
        row = arrival.crosswalk_row(SPICE_PARADISE_TRIGGER, registry)
        with _WithMeasuredXYZ(_xyz_for((SPICE_PARADISE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(SPICE_PARADISE_TRIGGER), registry
            )
        self.assertEqual(order.refusal, row.refusal)


class TheLevelGateIsOfferedNotApplied(unittest.TestCase):
    def test_a_below_level_character_still_gets_a_complete_order(self):
        with _WithMeasuredXYZ(_xyz_for((SPICE_PARADISE_TRIGGER,))):
            order = arrival.arrival_order(
                plan.handle_for_trigger_id(SPICE_PARADISE_TRIGGER)
            )
        self.assertIsNone(order.refusal)
        self.assertEqual(
            arrival.level_refusal(order, 1),
            arrival.ARRIVAL_REFUSED_BELOW_MIN_LEVEL,
        )
        self.assertIsNone(arrival.level_refusal(order, 25))

    def test_a_refused_order_has_no_level_opinion(self):
        self.assertIsNone(
            arrival.level_refusal(arrival.arrival_order(0x1234), 1)
        )


class TheConsoleSurfaces(unittest.TestCase):
    def test_the_fragment_says_plan_and_stays_inside_the_nonclaim(self):
        line = arrival.console_annotation()
        line.encode("ascii")
        self.assertEqual(line, "arrival_plan=2/2")
        for forbidden in ("island", "scene", "trigger"):
            self.assertNotIn(forbidden, line.lower())

    def test_the_fragment_tracks_the_registry_rather_than_being_a_constant(self):
        registry = _registry_with(n_id=3, spawn=None, spawn_provenance=None)
        self.assertEqual(
            arrival.console_annotation(registry), "arrival_plan=1/2"
        )

    def test_the_token_is_distinct_from_the_hooks_own(self):
        # Asserted as a literal and against the hook: `assertIn(TOKEN, report)`
        # let TOKEN be set to the hook's token with the suite green, which
        # would make a grader's grep of an attended log match report lines no
        # client produced.
        self.assertEqual(arrival.TOKEN, "LANE_A_M2_ARRIVAL")
        self.assertNotEqual(arrival.TOKEN, hooklog.TOKEN)
        self.assertNotIn("WORLD_SCENE", arrival.TOKEN)

    def test_a_door_refusal_is_tagged_with_its_owner(self):
        # `door_refusal` as the identity function survived: the console then
        # printed the door's reason with no owner tag.  Assert the literal.
        self.assertEqual(
            arrival.door_refusal(entry_door.REFUSED_NO_PINNED_SPAWN),
            "ARRIVAL_REFUSED_BY_DOOR:scene_has_no_pinned_spawn",
        )
        registry = _registry_with(n_id=2, spawn=None, spawn_provenance=None)
        row = arrival.crosswalk_row(PRISON_EXILE_TRIGGER, registry)
        self.assertTrue(
            row.refusal.startswith(arrival.ARRIVAL_REFUSED_BY_DOOR)
        )

    def test_the_report_names_both_destinations_and_stays_ascii(self):
        report = arrival.console_report()
        report.encode("ascii")
        self.assertIn(arrival.TOKEN, report)
        self.assertIn("Prison_Exile_Island", report)
        self.assertIn("Spice_Paradise_Island", report)
        # The status the bridge's RE queue owns is REPORTED, never rewritten.
        self.assertIn("status=PROVEN", report)
        self.assertIn("status=CANDIDATE", report)
        self.assertIn("client_confirmed=yes", report)
        self.assertIn("client_confirmed=no", report)

    def test_the_report_carries_the_refusal_field_it_exists_to_surface(self):
        # Dropping `refusal=` from the report survived the whole suite.
        self.assertIn("refusal=none", arrival.console_report())
        registry = _registry_with(n_id=3, login_entry_allowed=False)
        self.assertIn(
            f"refusal={arrival.ARRIVAL_REFUSED_DOOR_SHUT}",
            arrival.console_report(registry),
        )

    def test_the_report_has_one_line_per_row_plus_its_header(self):
        self.assertEqual(len(arrival.console_report().splitlines()), 3)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
