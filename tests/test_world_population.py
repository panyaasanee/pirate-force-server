"""LANE-A BUILD-001: the bg0001 census staircase.

The load-bearing test in this file is the first one.  Rung 3 must be BYTE-
IDENTICAL to what the runtime already sends today; if it is not, then a failing
higher rung could be blamed on the encoder instead of on the actor count, and
the whole staircase stops measuring anything.

The second load-bearing test is ``test_the_census_is_thin_everywhere``.  It
pins the measured fact that this table is map-wide and sparse, which is the
reason this module refuses to promise a crowded screen.  If the table ever
becomes dense, that promise can change - loudly, here, not quietly in prose.
"""

import dataclasses
import json
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_population
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.population import (
    AUTHORITATIVE_COUNT,
    build_port_royal_initial_population,
)
from pirateforce_foundation.world_population import (
    CENSUS_COUNT,
    WorldPopulationGeneration,
    census_console_line,
    census_shortfall_reason,
    dispatch_report,
    DEFAULT_ACTOR_COUNT,
    INITIAL_REAPPLY_MS,
    SHIPPED_ISOLATED_INDICES,
    STAIRCASE_RUNGS,
    build_staircase,
    build_world_population,
    census_order,
    effective_actor_count,
    nesting_break,
    production_allowed,
    staircase_report,
    test_only,
)


class WorldPopulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.anchor = (
            cls.legacy.V134_PLAYER_X,
            cls.legacy.V134_PLAYER_Y,
            cls.legacy.V134_PLAYER_Z,
        )
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )
        cls.far = (
            cls.legacy.V112_PLAYER_X,
            cls.legacy.V112_PLAYER_Y,
            cls.legacy.V112_PLAYER_Z,
        )

    # --- the control -----------------------------------------------------

    def test_rung_three_differs_from_the_shipped_default_by_exactly_the_two_added_names(
        self,
    ) -> None:
        """Was byte-identical; GT-078 OWNER-REJECTED ended that on purpose.

        ``make_v112_monster_shop_population_state()`` is the frozen diagnostic
        isolation lane other hypotheses measure against, and this project does
        not edit it: it still sends P0 and P91 nameless, by design, forever.
        This module no longer matches it byte-for-byte, because ``_entry()``
        now puts every placement's own ``source_name`` on the wire (P30's
        pinned V119 override is unchanged and unaffected).  The invariant that
        survives is narrower than byte-identity: the ONLY bytes rung 3 adds,
        anywhere, are the two UTF-16LE name tags for P0 and P91 - P30's name
        tag was already present in both frames via the pinned monster override,
        so it contributes nothing to the delta.
        """
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import SHIPPED_MONSTER_INDEX

        shipped_pc, shipped_frame, shipped_rows = (
            self.legacy.make_v112_monster_shop_population_state()
        )
        rung = build_world_population(self.legacy, self.anchor, 3, scene_id=1)
        self.assertEqual(rung.indices, tuple(row[0] for row in shipped_rows))
        self.assertEqual(rung.indices, SHIPPED_ISOLATED_INDICES)

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        added_name_tags = [
            self.legacy.wstr_tag(placements[index].source_name)
            for index in SHIPPED_ISOLATED_INDICES
            if index != SHIPPED_MONSTER_INDEX
        ]
        added_bytes = sum(len(tag) for tag in added_name_tags)
        self.assertEqual(len(rung.pc) - len(shipped_pc), added_bytes)
        self.assertEqual(len(rung.frame) - len(shipped_frame), added_bytes)
        for tag in added_name_tags:
            self.assertNotIn(tag, shipped_pc)
            self.assertIn(tag, rung.pc)

        # Pinned so a future encoder change is caught here too, not only in
        # scenarios/world_population_full_001.json.
        self.assertEqual((rung.pc_bytes, rung.frame_bytes), (564, 577))

    def test_the_control_rung_is_anchor_invariant(self) -> None:
        """Which is what makes it a control - and also its only limitation."""
        first = build_world_population(self.legacy, self.anchor, 3, scene_id=1)
        for other in (self.spawn, self.far, (0.0, 0.0, 0.0)):
            self.assertEqual(build_world_population(self.legacy, other, 3, scene_id=1).pc, first.pc)

    # --- the honesty pin -------------------------------------------------

    def test_the_census_is_thin_everywhere(self) -> None:
        """Sending 115 does not crowd a view; this is why the module says so."""
        placements = census_order(self.legacy, self.spawn)
        x, y, z = self.spawn
        distances = sorted(
            ((item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2) ** 0.5
            for item in placements
        )
        self.assertLessEqual(sum(1 for d in distances if d < 2000.0), 2)
        self.assertGreater(distances[AUTHORITATIVE_COUNT - 1], 10000.0)
        self.assertGreater(distances[-1], 35000.0)

    # --- the staircase ---------------------------------------------------

    def test_every_rung_is_a_prefix_of_the_next(self) -> None:
        built = build_staircase(self.legacy, self.anchor)
        self.assertEqual(tuple(item.actor_count for item in built), STAIRCASE_RUNGS)
        for lower, higher in zip(built, built[1:]):
            self.assertEqual(higher.indices[: lower.actor_count], lower.indices)
            self.assertGreater(higher.frame_bytes, lower.frame_bytes)
        self.assertIsNone(nesting_break(built))

    def test_nesting_break_catches_rungs_built_at_different_anchors(self) -> None:
        """The real threat: one boot per rung means one anchor per rung."""
        low = build_world_population(self.legacy, self.anchor, 20, scene_id=1)
        high_same = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        self.assertIsNone(nesting_break((low, high_same)))

        # An anchor on the far side of the table: at ~30,000 units away its
        # nearest-60 no longer contains the first anchor's nearest-20.
        elsewhere = (21694.0703125, -5071.00048828125, 0.0)
        high_elsewhere = build_world_population(self.legacy, elsewhere, 60, scene_id=1)
        dropped = nesting_break((low, high_elsewhere))
        self.assertIsNotNone(dropped)
        self.assertTrue(set(dropped) <= set(low.indices))
        self.assertTrue(set(dropped).isdisjoint(set(high_elsewhere.indices)))

    def test_nesting_break_refuses_input_it_cannot_read(self) -> None:
        low = build_world_population(self.legacy, self.anchor, 20, scene_id=1)
        high = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        for bad in ((), [low, high], None):
            with self.assertRaises(ValueError):
                nesting_break(bad)
        with self.assertRaises(ValueError):
            nesting_break((high, low))

    def test_top_rung_is_the_whole_census_without_repeats(self) -> None:
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(top.actor_count, CENSUS_COUNT)
        self.assertEqual(len(set(top.indices)), CENSUS_COUNT)

    def test_top_rung_differs_from_the_frozen_golden_115_by_every_members_own_name(
        self,
    ) -> None:
        """v141:1441 already builds a 115-member snapshot; this one is that one.

        Was "by P30 alone", when P30's BasicAttr name was the only name this
        module put on the wire.  GT-078 OWNER-REJECTED ended that: ``_entry()``
        now puts every placement's own frozen ``source_name`` on the wire, and
        ``make_v62_port_royal_population_snapshot`` never sets a name for
        ANYONE (it calls ``make_npc_attr`` with no ``basic_name`` argument at
        all, not even for P30).  So the true invariant is no longer "P30's tag
        alone" - it is the sum of every top-rung member's own name-tag length,
        computed from the encoder's own ``wstr_tag`` rather than hand-counted,
        so a change to any placement's name text is still caught here.
        """
        from pirateforce_foundation.population import load_port_royal_placements

        _label, golden_pc, _frame, chosen = (
            self.legacy.make_v62_port_royal_population_snapshot(*self.anchor)
        )
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(set(top.indices), {row[0] for row in chosen})

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        name_tags = [
            self.legacy.wstr_tag(placements[index].source_name)
            for index in top.indices
        ]
        expected_delta = sum(len(tag) for tag in name_tags)
        self.assertEqual(top.pc_bytes - len(golden_pc), expected_delta)
        for tag in name_tags:
            self.assertNotIn(tag, golden_pc)

    def test_every_member_is_now_absent_from_the_golden_115_because_every_member_is_named(
        self,
    ) -> None:
        """Was "every member but P30 appears verbatim"; GT-078's fix widened this to all 115.

        Stronger than the frame-size delta above, and it can fail alone: a
        total-size comparison passes if two members drift in offsetting
        directions, so this looks for each census entry's exact bytes INSIDE
        the payload the frozen V62 builder produced.  Before the GT-078 name
        fix only P30 carried a name, so only P30's entry was absent from the
        nameless golden snapshot.  Now ``_entry()`` puts every placement's own
        ``source_name`` on the wire, and V62 never names anyone (not even
        P30), so EVERY entry this module builds now differs from its golden
        counterpart - "some absent" was the half-fixed world; "all absent" is
        the one after this fix.

        The comparison deliberately calls ``make_v62_port_royal_population_
        snapshot`` and searches its real output.  An earlier version of this
        test rebuilt a "golden" entry here using ``HEADINGS`` imported from the
        module under test, which made it agree with itself: zeroing HEADINGS
        changed 86 of 115 actors on the wire and the test still passed.

        NONCLAIM: a substring miss proves each entry's bytes are absent, not
        that the collection orders them the way V62 orders them.  Ordering is
        not compared here, and no other test compares it either.
        """
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import _entry

        _label, golden_pc, _frame, _chosen = (
            self.legacy.make_v62_port_royal_population_snapshot(*self.anchor)
        )
        placements = load_port_royal_placements(self.legacy)
        absent = [
            placement.placement_index
            for placement in placements
            if _entry(self.legacy, placement) not in golden_pc
        ]
        self.assertEqual(absent, [placement.placement_index for placement in placements])
        self.assertEqual(len(absent), CENSUS_COUNT)

    def test_every_members_own_name_reaches_the_wire_as_a_utf16_basic_name_tag(
        self,
    ) -> None:
        """GT-078 OWNER-REJECTED, direct: no client screenshot ever showed a
        name line under any NPC in town, only a title line.  This is the test
        that would have caught it - there was none before this lane's fix
        (a static-RE grep of tests/test_population.py and
        tests/test_world_population.py for "basic_name"/"source_name" found
        no coverage of this path at all).

        Reuses the codebase's own frozen tag helper (``legacy.wstr_tag``)
        rather than hand-rolling UTF-16LE, the same way
        tests/test_field_mobs.py checks ``mob.display_name`` reaches the
        wire.  Checked for three specific, distinct placements: the pinned
        control's two non-monster members (P0, P91) plus one ordinary
        mid-table member (P35, "Columbus") that carries no special-case
        handling at all - so this is not merely re-proving the control rung.
        """
        from pirateforce_foundation.population import load_port_royal_placements
        from pirateforce_foundation.world_population import _entry

        placements = {
            placement.placement_index: placement
            for placement in load_port_royal_placements(self.legacy)
        }
        for index in (0, 91, 35):
            placement = placements[index]
            self.assertTrue(placement.source_name)
            entry = _entry(self.legacy, placement)
            name_tag = self.legacy.wstr_tag(placement.source_name)
            self.assertIn(name_tag, entry)

    def test_identities_follow_the_frozen_actor_identity_rule(self) -> None:
        top = build_world_population(self.legacy, self.anchor, CENSUS_COUNT, scene_id=1)
        self.assertEqual(
            top.actor_identities,
            tuple(0x2000 + index + 1 for index in top.indices),
        )

    def test_build_is_deterministic(self) -> None:
        first = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        second = build_world_population(self.legacy, self.anchor, 60, scene_id=1)
        self.assertEqual(first.pc, second.pc)
        self.assertEqual(first.indices, second.indices)

    def test_order_is_pinned_first_then_nearest_first(self) -> None:
        placements = census_order(self.legacy, self.anchor)
        self.assertEqual(
            tuple(item.placement_index for item in placements[:3]),
            SHIPPED_ISOLATED_INDICES,
        )
        x, y, z = self.anchor
        distances = [
            (item.x - x) ** 2 + (item.y - y) ** 2 + (item.z - z) ** 2
            for item in placements[3:]
        ]
        self.assertEqual(distances, sorted(distances))

    def test_rung_twenty_membership_coincides_with_v94_at_this_anchor(self) -> None:
        """A weak coincidence, recorded as one - not a second control.

        At the V134 anchor the pinned three happen to fall inside V94's
        nearest-20, so the SETS match.  The frames do not, the orders do not,
        and at other anchors the sets do not either.  No client has accepted
        this frame.
        """
        v94 = build_port_royal_initial_population(self.legacy, self.anchor)
        rung = build_world_population(self.legacy, self.anchor, AUTHORITATIVE_COUNT, scene_id=1)
        self.assertEqual(set(rung.indices), set(v94.current_indices))
        self.assertNotEqual(rung.pc, v94.pc)
        self.assertNotEqual(rung.indices, v94.current_indices)

    # --- the default this lane exists to ship ----------------------------

    def test_module_declares_itself_a_shipping_lane(self) -> None:
        self.assertTrue(production_allowed)
        self.assertFalse(test_only)
        self.assertEqual(DEFAULT_ACTOR_COUNT, CENSUS_COUNT)

    def test_recording_a_measured_ceiling_actually_changes_what_callers_send(
        self,
    ) -> None:
        """The whole point of the constant: editing it must change behaviour."""
        original = world_population.MEASURED_CLIENT_ACTOR_CEILING
        try:
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = 20
            self.assertEqual(effective_actor_count(), 20)
            world_population.MEASURED_CLIENT_ACTOR_CEILING = CENSUS_COUNT
            self.assertEqual(effective_actor_count(), CENSUS_COUNT)
        finally:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = original
        self.assertEqual(effective_actor_count(), CENSUS_COUNT)

    def test_effective_count_validates_an_explicit_ceiling(self) -> None:
        self.assertEqual(effective_actor_count(None), CENSUS_COUNT)
        self.assertEqual(effective_actor_count(60), 60)
        for bad in (0, -1, CENSUS_COUNT + 1, "60", 60.0, True):
            with self.assertRaises(ValueError):
                effective_actor_count(bad)

    def test_report_pins_sizes_and_membership(self) -> None:
        report = staircase_report(self.legacy, self.anchor)
        self.assertEqual(report["census_count"], CENSUS_COUNT)
        self.assertEqual(report["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        counts = [rung["actor_count"] for rung in report["rungs"]]
        self.assertEqual(counts, list(STAIRCASE_RUNGS))
        for rung in report["rungs"]:
            self.assertEqual(len(rung["indices"]), rung["actor_count"])
        sizes = [rung["frame_bytes"] for rung in report["rungs"]]
        self.assertEqual(sizes, sorted(sizes))

    def test_pin_file_still_describes_what_the_module_builds(self) -> None:
        """The scenario file is a PIN, not a switch: no flag reads it.

        Both anchors are pinned on purpose - the documented V134 anchor and the
        anchor a new character actually spawns at - so a tester comparing an
        observed frame to the pin is comparing against a position that exists.
        """
        pinned = json.loads(
            (ROOT / "scenarios" / "world_population_full_001.json")
            .read_text(encoding="ascii")
        )
        self.assertTrue(pinned["production_allowed"])
        self.assertFalse(pinned["test_only"])
        population = pinned["population"]
        self.assertEqual(population["default_actor_count"], CENSUS_COUNT)
        self.assertEqual(population["source_count"], CENSUS_COUNT)
        self.assertEqual(population["initial_reapply_ms"], INITIAL_REAPPLY_MS)
        self.assertEqual(
            population["control_rung_indices"], list(SHIPPED_ISOLATED_INDICES)
        )
        from pirateforce_foundation.population import PORT_ROYAL_SOURCE_SHA256

        self.assertEqual(population["source_sha256"], PORT_ROYAL_SOURCE_SHA256)

        anchors = pinned["staircase"]["reference_anchors"]
        self.assertEqual(len(anchors), 2)
        expected_anchors = {
            "v141_V134_PLAYER_XYZ": self.anchor,
            "v141_V135_PLAYER_XYZ_new_character_spawn": self.spawn,
        }
        for block in anchors:
            xyz = expected_anchors[block["label"]]
            self.assertEqual((block["x"], block["y"], block["z"]), xyz)
            report = staircase_report(self.legacy, xyz)
            self.assertEqual(
                [
                    {
                        "actor_count": rung["actor_count"],
                        "pc_bytes": rung["pc_bytes"],
                        "frame_bytes": rung["frame_bytes"],
                        "indices": rung["indices"],
                    }
                    for rung in report["rungs"]
                ],
                block["rungs"],
            )

    def test_pin_file_cannot_be_loaded_as_a_population_scenario(self) -> None:
        """It declares production_allowed; the loader only accepts test_only."""
        from pirateforce_foundation.population_scenario import (
            load_population_scenario,
        )

        with self.assertRaises(ValueError):
            load_population_scenario(
                ROOT / "scenarios" / "world_population_full_001.json"
            )

    # --- refusals --------------------------------------------------------

    def test_actor_count_is_bounded_by_the_census(self) -> None:
        for bad in (0, -1, CENSUS_COUNT + 1, 3.0, "3", None, True):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, self.anchor, bad, scene_id=1)

    def test_anchor_must_be_an_exact_finite_triple(self) -> None:
        for bad in (
            None, (), (0.0, 0.0), (0.0, 0.0, 0.0, 0.0), [0.0, 0.0, 0.0],
            (0.0, 0.0, float("nan")), (0.0, 0.0, float("inf")),
            (0.0, 0.0, "0"), (0.0, 0.0, 1e39),
        ):
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, bad, 3, scene_id=1)

    def test_rungs_must_be_a_strictly_increasing_tuple_of_counts(self) -> None:
        for bad in (
            (), [3, 20], (20, 3), (3, 3), (3, 20, 20),
            (3, "20"), (3, None), (3, 3.0), (0, 20), (3, CENSUS_COUNT + 1),
        ):
            with self.assertRaises(ValueError):
                build_staircase(self.legacy, self.anchor, bad)

    def test_control_rung_refuses_to_measure_a_drifted_default(self) -> None:
        """If the shipped isolated set changes, rung 3 stops being the control."""
        drifted = types.SimpleNamespace(
            **{
                name: getattr(self.legacy, name)
                for name in (
                    "NPC_ATTR", "MOVEMENT_ATTR", "GSCN_RUNTIME_PROTOCOL_RES",
                    "V94_LOCAL_LIMIT", "V94_REFRESH_DISTANCE",
                    "PORT_ROYAL_UNAMBIGUOUS_PLACEMENTS",
                    "make_npc_attr", "make_remote_movement_attr",
                    "make_remote_actor_entry", "make_runtime_remote_actors",
                    "V112_MONSTER_INDEX", "V117_P30_EXACT_HP",
                    "V119_P30_TARGET_NAME",
                )
            }
        )
        drifted.V112_TEST_INDICES = (0, 30, 92)
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)
        drifted.V112_TEST_INDICES = self.legacy.V112_TEST_INDICES
        drifted.V112_MONSTER_INDEX = 31
        with self.assertRaises(ValueError):
            census_order(drifted, self.anchor)


class CensusDispatchCountTests(unittest.TestCase):
    """CHARTER-02 replaced the staircase with a pre-send count.

    The ruling has a hard half: the number that goes out must never quietly
    become something other than the whole census.  "Quietly" includes a frame
    that SAYS 115 while carrying fewer bodies, which is why these tests care
    about the wire header and the body bytes and not only about the list this
    module built.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.spawn = (
            cls.legacy.V135_PLAYER_X,
            cls.legacy.V135_PLAYER_Y,
            cls.legacy.V135_PLAYER_Z,
        )

    def test_the_full_census_reports_no_shortfall(self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn,
            scene_id=1, count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )
        report = dispatch_report(generation)
        self.assertEqual(report["assembled_count"], CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], CENSUS_COUNT)
        self.assertTrue(report["counts_agree"])
        self.assertTrue(report["bodies_intact"])
        self.assertIsNone(report["shortfall_reason"])
        self.assertEqual(report["initial_reapply_ms"], INITIAL_REAPPLY_MS)

    def test_the_wire_count_is_read_back_out_of_the_bytes(self) -> None:
        """Not copied from the request - decoded from the header the client reads."""
        for count in (1, 3, 20, CENSUS_COUNT):
            generation = build_world_population(
                self.legacy, self.spawn, count, scene_id=1)
            self.assertEqual(
                world_population.wire_actor_count(generation), count)
        # and it refuses bytes that are not that header rather than guessing
        broken = build_world_population(self.legacy, self.spawn, 3, scene_id=1)
        with self.assertRaises(ValueError):
            world_population.wire_actor_count(
                dataclasses.replace(broken, pc=b"\x00" * 8))

    def test_a_frame_that_lost_a_body_cannot_print_a_clean_line(self) -> None:
        """The defect this report exists to catch, reproduced end to end.

        A dropped actor body leaves the collection header saying N while N-1
        bodies follow - a RuntimeRes stream-tail misalignment, which is what
        ErrorData=28317 answers.  A report that counted only its own input
        would print 115/115 over exactly this frame.
        """
        honest = build_world_population(self.legacy, self.spawn, scene_id=1)
        last = honest.entry_bytes[-1]
        maimed = dataclasses.replace(honest, pc=honest.pc[:-last])
        report = dispatch_report(maimed)
        self.assertEqual(report["assembled_count"], CENSUS_COUNT)
        self.assertEqual(report["wire_actor_count"], CENSUS_COUNT)
        self.assertFalse(report["bodies_intact"])
        self.assertEqual(
            report["body_bytes"], report["entry_bytes_total"] - last)
        self.assertIn("bodies=SHORT", census_console_line(maimed))
        self.assertIn("bodies=ok", census_console_line(honest))

    def test_an_actor_that_encodes_to_nothing_is_refused_at_build(self) -> None:
        """The same defect one step earlier, where it can still be prevented."""
        original = world_population._entry
        calls = []

        def drop_one(legacy, placement):
            calls.append(placement.placement_index)
            if len(calls) == 2:
                return b""
            return original(legacy, placement)

        world_population._entry = drop_one
        try:
            with self.assertRaises(ValueError):
                build_world_population(self.legacy, self.spawn, 3, scene_id=1)
        finally:
            world_population._entry = original

    def test_the_census_refuses_to_be_built_for_another_scene(self) -> None:
        """The acting half of the cross-build-order guard.

        world_scene_travel.population_source() reports which scene the census
        is true in; this refuses to build it anywhere else, so a caller that
        never asks still cannot deliver bg0001 dock NPCs into another map.
        """
        for scene in (2, 278, 0, None, "1"):
            with self.assertRaises(ValueError):
                build_world_population(
                    self.legacy, self.spawn, 3, scene_id=scene)
        with self.assertRaises(TypeError):
            build_world_population(self.legacy, self.spawn, 3)

    def test_the_reason_for_a_short_send_is_recorded_not_inferred(self) -> None:
        """One number, two meanings - so the caller states which one it meant."""
        deliberate = build_world_population(
            self.legacy, self.spawn, 20, scene_id=1,
            count_source=world_population.COUNT_SOURCE_CALLER,
        )
        self.assertEqual(
            dispatch_report(deliberate)["shortfall_reason"],
            "caller_requested=20",
        )
        capped = build_world_population(
            self.legacy, self.spawn, 20, scene_id=1,
            count_source=world_population.COUNT_SOURCE_MEASURED_CEILING,
        )
        self.assertEqual(
            dispatch_report(capped)["shortfall_reason"],
            "measured_client_ceiling=20",
        )
        self.assertIsNone(census_shortfall_reason(CENSUS_COUNT))
        with self.assertRaises(ValueError):
            census_shortfall_reason(20, "because_i_said_so")

    def test_the_dispatch_count_names_its_own_source(self) -> None:
        self.assertEqual(
            world_population.census_count_for_dispatch(),
            (CENSUS_COUNT, world_population.COUNT_SOURCE_FULL_CENSUS),
        )
        original = world_population.MEASURED_CLIENT_ACTOR_CEILING
        try:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = 60
            self.assertEqual(
                world_population.census_count_for_dispatch(),
                (60, world_population.COUNT_SOURCE_MEASURED_CEILING),
            )
        finally:
            world_population.MEASURED_CLIENT_ACTOR_CEILING = original

    def test_the_console_line_is_one_ascii_line_carrying_the_count(self) -> None:
        generation = build_world_population(
            self.legacy, self.spawn,
            scene_id=1, count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )
        line = census_console_line(generation)
        line.encode("ascii")
        self.assertNotIn("\n", line)
        self.assertIn("assembled=115/115", line)
        self.assertIn("wire=115", line)
        self.assertIn("shortfall=none", line)
        self.assertIn("source=full_census", line)
        self.assertIn(f"reapply_ms={INITIAL_REAPPLY_MS}", line)
        short = census_console_line(
            build_world_population(self.legacy, self.spawn, 3, scene_id=1))
        self.assertIn("assembled=3/115", short)
        self.assertIn("shortfall=caller_requested=3", short)

    def test_the_report_refuses_anything_that_is_not_a_generation(self) -> None:
        for bad in (None, 115, {"actor_count": 115}, [1, 2, 3]):
            with self.assertRaises(ValueError):
                dispatch_report(bad)


if __name__ == "__main__":
    unittest.main()
