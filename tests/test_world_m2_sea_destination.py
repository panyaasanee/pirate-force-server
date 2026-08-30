"""Tests for ``world_m2_sea_destination``.

The module ships no wire bytes, so what is worth testing is what it can get
wrong: naming the wrong scene as the destination (which its own first draft
did), drifting from the module that actually sends the option, keying the
CLINE table the way the shipped scene-14 module keys it, and claiming a door
is open when nothing behind it is pinned.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch
from pirateforce_foundation import world_bg0015_identity
from pirateforce_foundation import world_m2_sea_destination as sea
from pirateforce_foundation import world_scene_travel


class DestinationTests(unittest.TestCase):
    def test_the_target_is_the_ship_scene_the_row_itself_names(self):
        self.assertEqual(sea.DESTINATION_SCENE_N_ID, 17)
        self.assertEqual(sea.DESTINATION_SCENE_MODEL_ID, "Bg1001")
        self.assertEqual(
            sea.OPTION_TARGET_SCENE_N_ID[sea.DESTINATION_QUEST_ID], 17,
        )

    def test_it_does_not_drift_from_the_module_that_sends_the_option(self):
        # The defect this test exists for: two modules in src/ asserting
        # different destinations for the same option, with nothing failing.
        self.assertEqual(
            sea.DESTINATION_QUEST_ID, columbus_quest_dispatch.COLUMBUS_QUEST_ID,
        )
        self.assertEqual(
            sea.DESTINATION_SCENE_N_ID,
            columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID,
            "the dispatch lane and this pin must name ONE destination for "
            "this option; if they differ the tree contradicts itself in a "
            "console line an operator has to choose between",
        )

    def test_the_advertised_ocean_is_not_the_destination(self):
        self.assertEqual(sea.ADVERTISED_OCEAN_SCENE_N_ID, 126)
        self.assertNotEqual(
            sea.ADVERTISED_OCEAN_SCENE_N_ID, sea.DESTINATION_SCENE_N_ID,
            "reading the advertised name as a route is the error this "
            "module was rewritten to record, not to repeat",
        )

    def test_three_islands_advertise_one_ocean_and_go_three_ways(self):
        # The asymmetry that refutes "126 is the destination": if it were,
        # 3021/3022/3023 would be indistinguishable.
        rising_sun = [r for r in sea.COLUMBUS_ROUTES if r[4] == 126]
        self.assertEqual(len(rising_sun), 3)
        self.assertEqual(len({r[3] for r in rising_sun}), 3)
        self.assertEqual(len({r[2] for r in rising_sun}), 3)

    def test_port_royals_columbus_routes_the_way_the_dispatch_lane_sends(self):
        home, row, target, ocean = sea.route_for(156)
        self.assertEqual(home, 1)
        self.assertEqual(row, columbus_quest_dispatch.COLUMBUS_QUEST_ID)
        self.assertEqual(target, columbus_quest_dispatch.COLUMBUS_DEST_SCENE_ID)
        self.assertEqual(ocean, 126)

    def test_an_unknown_columbus_is_refused_not_guessed(self):
        self.assertIsNone(sea.route_for(999999))

    def test_the_console_line_is_ascii_and_names_both_scenes(self):
        line = sea.console_line(world_scene_travel.load_scene_registry())
        line.encode("ascii")   # raises if a non-ASCII character creeps in
        line.encode("cp874")   # the bridge console's own encoding
        self.assertIn("target_scene=17", line)
        self.assertIn("advertises_ocean=126", line)
        self.assertIn("state=READY_DECREED", line)
        self.assertIn("var2_reading=CONTESTED", line)
        self.assertIn("arrival=0.000,0.000,0.000", line)
        self.assertIn("evidence=GT-106", line)

    def test_console_line_safe_agrees_with_console_line_when_nothing_fails(
        self,
    ):
        registry = world_scene_travel.load_scene_registry()
        self.assertEqual(
            sea.console_line_safe(registry), sea.console_line(registry),
        )

    def test_console_line_safe_never_raises_on_a_registry_missing_the_attr(
        self,
    ):
        line = sea.console_line_safe("not a registry")
        line.encode("ascii")
        line.encode("cp874")
        self.assertTrue(line.startswith("M2_SEA_DESTINATION unmeasured "))
        self.assertIn("reason=refused:SeaDestinationError", line)

    def test_console_line_safe_names_a_none_registry_rather_than_guessing(
        self,
    ):
        """``None`` is the shape ``dispatch_columbus_quest3021`` actually
        defaults to (its own ``registry=None``) -- a NAMED absence, not the
        generic ``SeaDestinationError`` catch-all below it."""
        line = sea.console_line_safe(None)
        self.assertEqual(
            line,
            "M2_SEA_DESTINATION unmeasured "
            "reason=call_site_passed_no_registry",
        )


class ArrivalPointTests(unittest.TestCase):
    """The half of this module that was stale on main until round drrnpu.

    It answered "no arrival point, and nobody has read the path that would
    carry one" while the registry had carried one for two days and
    ``runtime.py`` was dispatching on it with no flag.  These tests exist so
    that pair can never disagree silently again.
    """

    def setUp(self):
        self.registry = world_scene_travel.load_scene_registry()

    def test_the_arrival_point_is_the_registrys_and_not_a_second_copy(self):
        # The D8 shape: a module holding its own answer next to the owner's.
        target = world_scene_travel.destination(
            sea.DESTINATION_SCENE_N_ID, self.registry,
        )
        self.assertEqual(
            sea.arrival_position(self.registry),
            world_scene_travel.spawn_position(target),
        )
        self.assertEqual(
            sea.arrival_provenance(self.registry), target.spawn_provenance,
        )
        self.assertFalse(
            hasattr(sea, "ARRIVAL_POSITION"),
            "the struck constant must stay struck - a module-level copy of "
            "this point is the defect this class was written for",
        )
        self.assertIn("world_scene_registry_001.json", sea.ARRIVAL_POSITION_OWNER)

    def test_moving_the_registrys_point_moves_this_modules_answer(self):
        """The control the first draft of this class did NOT have.

        pf-adversary (round drrnpu, D4) drove two fakes past all 21 tests:
        one that answered from its own module-level copy of (0,0,0), and one
        that ignored the caller's registry and read the file from disk.  Both
        passed because every assertion compared two things that were both
        (0,0,0), and because the anti-copy check was a check on a NAME.  This
        one moves the registry's point somewhere no default could produce.
        """
        loaded = world_scene_travel.load_scene_registry()
        moved = replace(
            loaded[sea.DESTINATION_SCENE_N_ID], spawn=(111.0, 222.0, 333.0),
        )
        registry = replace(loaded, destinations=tuple(
            moved if row.n_id == sea.DESTINATION_SCENE_N_ID else row
            for row in loaded.destinations
        ))
        self.assertEqual(sea.arrival_position(registry), (111.0, 222.0, 333.0))
        self.assertIn(
            "arrival=111.000,222.000,333.000", sea.console_line(registry),
        )

    def test_the_var2_reading_is_carried_as_contested_not_as_measured(self):
        """Item 0 of the module docstring, as data a machine can check.

        The refutation must survive a later round that reads only the code:
        Var2 is a valid MARKER id in all 41 rows and is not a scene id in
        five of them, and the console line has to say the reading is
        contested rather than print a destination as settled.
        """
        self.assertEqual(sea.TELEPORT_ROWS_TOTAL, 41)
        self.assertEqual(len(sea.VAR2_VALUES_THAT_ARE_NOT_SCENE_IDS), 5)
        self.assertIn(
            (3037, sea.SCENE_130_DECLARES_MARKER),
            sea.VAR2_VALUES_THAT_ARE_NOT_SCENE_IDS,
        )
        self.assertEqual(sea.MARKER_AT_VAR2[0], sea.ADVERTISED_OCEAN_SCENE_N_ID)
        self.assertIn(
            "var2_reading=CONTESTED",
            sea.console_line(world_scene_travel.load_scene_registry()),
        )

    def test_the_marker_reading_reproduces_this_files_own_ocean_column(self):
        """8 of 8, from the copy this repository commits - no bridge needed.

        This is the measurement that refuted the round: MARKER[Var2].n_SCENE
        gives, in one lookup, the same eight oceans this file derives through
        a three-hop chain.  If a later round wants to keep the scene reading
        it has to explain this agreement away.
        """
        crosswalk = json.loads(
            (ROOT / "src/pirateforce_foundation/world_data"
             / "world_marker_crosswalk.json").read_text()
        )
        marker_scene = {row[0]: row[1] for row in crosswalk["marker_scene_index"]}
        checked = 0
        for _mobs, _home, _row_id, target, ocean in sea.COLUMBUS_ROUTES:
            # COLUMBUS_ROUTES' fourth field IS the row's Var2, read as a
            # scene id by this file and as a marker id by the refutation.
            var2 = target
            self.assertIn(var2, marker_scene, "Var2 must be a valid marker id")
            self.assertEqual(
                marker_scene[var2], ocean,
                "MARKER[Var2].n_SCENE must reproduce the advertised ocean - "
                "that agreement is the refutation, and losing it silently is "
                "how this round's error would come back",
            )
            checked += 1
        self.assertEqual(checked, 8)

    def test_the_door_has_a_landing_spot_and_the_state_says_who_authored_it(self):
        self.assertTrue(sea.destination_ready(self.registry))
        self.assertEqual(sea.refusal_reason(self.registry), "")
        # Pinned, but still on the owner's decree: "ready" must never be
        # allowed to read as "measured" while that prefix is what holds it.
        self.assertTrue(sea.arrival_is_decreed(self.registry))
        self.assertEqual(
            sea.destination_state(self.registry), sea.STATE_READY_DECREED,
        )

    def test_a_registry_without_this_scene_refuses_instead_of_raising(self):
        class NoSuchScene:
            destinations = {}

        empty = NoSuchScene()
        self.assertIsNone(sea.arrival_position(empty))
        self.assertFalse(sea.destination_ready(empty))
        self.assertEqual(sea.destination_state(empty), sea.STATE_REFUSED)
        self.assertFalse(sea.arrival_is_decreed(empty))
        with self.assertRaises(sea.SeaDestinationError):
            sea.arrival_position(None)   # never silently reads the file
        for not_a_registry in ("world_scene_registry_001.json", [1, 2], 17):
            # A wrong argument must not come back as a confident REFUSED
            # about a registry that was never one.
            with self.assertRaises(sea.SeaDestinationError):
                sea.arrival_position(not_a_registry)
        reason = sea.refusal_reason(empty)
        self.assertIn("n_MARKER is 0", reason)
        self.assertIn("MARKER[17] does exist", reason)
        self.assertNotIn(
            "nothing here has read that path", reason,
            "that path IS read - q_teleport1.lua, one argument, no "
            "coordinate; saying otherwise is what kept RE-103 open",
        )

    def test_the_state_follows_the_provenance_rather_than_a_literal(self):
        # Negative control: hand it a registry whose scene 17 spawn is NOT
        # decreed and the state has to move on its own.
        loaded = world_scene_travel.load_scene_registry()
        measured = replace(
            loaded[sea.DESTINATION_SCENE_N_ID],
            spawn_provenance="GT-106 attended arrival, 2026-08-27",
        )
        registry = replace(loaded, destinations=tuple(
            measured if row.n_id == sea.DESTINATION_SCENE_N_ID else row
            for row in loaded.destinations
        ))
        self.assertFalse(sea.arrival_is_decreed(registry))
        self.assertEqual(
            sea.destination_state(registry), sea.STATE_READY_NOT_DECREED,
        )
        self.assertIn("state=READY_NOT_DECREED", sea.console_line(registry))

    def _registry_with(self, provenance, z):
        """A copy of the real registry file with scene 17's spawn edited."""
        data = json.loads(
            (ROOT / "scenarios/world_scene_registry_001.json").read_text()
        )
        for row in data["destinations"]:
            if row["n_id"] == sea.DESTINATION_SCENE_N_ID:
                row["spawn"]["provenance"] = provenance
                row["spawn"]["z"] = z
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "registry.json"
            path.write_text(json.dumps(data))
            return world_scene_travel.load_scene_registry(path)

    def test_retiring_the_decree_today_would_stop_the_registry_loading(self):
        """Why this round reported the decree instead of retiring it.

        The PROVISIONAL-OWNER-DECREE prefix is what exempts scene 17's spawn
        from the ground check, and that check tests z: the pinned band comes
        from the scene's native placements (746.04 .. 1272.74), so with the
        prefix gone the registry REFUSES TO LOAD and every login dies at
        boot.  Driven here rather than argued, because the ASK-COO letter
        this round sends is only worth reading if these three lines are real.
        """
        measured = "GT-106 attended arrival 2026-08-27, client-observed"
        for z in (0.0, sea.ARRIVAL_RUN_DB_WALKED_Z):
            with self.assertRaises(ValueError) as caught:
                self._registry_with(measured, z)
            self.assertIn("spawn z is outside", str(caught.exception))
        # Even the z a human actually stood at is refused, one unit under the
        # lowest placement - the band is not a floor measurement, which is
        # what the registry's own ground block says about it.
        loads = self._registry_with(measured, sea.LOWEST_NATIVE_PLACEMENT_Z)
        self.assertEqual(
            world_scene_travel.spawn_position(
                loads[sea.DESTINATION_SCENE_N_ID],
            )[2],
            sea.LOWEST_NATIVE_PLACEMENT_Z,
        )
        # And the shipped pairing loads, which is the state on main today.
        today = self._registry_with(
            "PROVISIONAL-OWNER-DECREE-20260827-1445 (owner decree)", 0.0,
        )
        self.assertEqual(
            world_scene_travel.spawn_position(
                today[sea.DESTINATION_SCENE_N_ID],
            ),
            (0.0, 0.0, 0.0),
        )

    def test_the_teleport_path_reading_is_the_one_that_closes_re_103(self):
        # Not prose: the two values the answer rests on, plus the file to
        # re-read if anybody doubts them.
        self.assertEqual(sea.TELEPORT_CALL_ARGUMENT_COUNT, 1)
        self.assertFalse(sea.TELEPORT_CALL_CARRIES_A_POSITION)
        self.assertTrue(sea.TELEPORT_SCRIPT.endswith("q_teleport1.lua"))
        self.assertEqual(sea.SCENE_NAME_MARKER_COLUMN_FOR_THE_SEA_FAMILY, 0)
        self.assertIn(sea.DESTINATION_SCENE_N_ID, sea.SEA_FAMILY_SCENE_IDS)
        self.assertIn(
            sea.DESTINATION_QUEST_ID, sea.TELEPORT_ACCEPT_PRECONDITION_ROWS,
        )

    def test_the_two_z_numbers_are_kept_apart_and_neither_is_the_spawn(self):
        # The reading NOT to take from GT-106: that 745 is an arrival z.  It
        # is a walked position in the same scene, and the spawn is still 0.
        self.assertAlmostEqual(
            sea.LOWEST_NATIVE_PLACEMENT_Z - sea.ARRIVAL_RUN_DB_WALKED_Z,
            1.0424194335938, places=6,
        )
        _x, _y, z = sea.arrival_position(self.registry)
        self.assertEqual(z, 0.0)
        self.assertNotEqual(z, sea.ARRIVAL_RUN_DB_WALKED_Z)
        self.assertEqual(sea.ARRIVAL_OBSERVED_HUD_XY, (0.0, 0.0))


class CrosswalkKeyRuleTests(unittest.TestCase):
    def test_the_key_is_a_column_not_a_row_id_or_a_position(self):
        self.assertEqual(
            sea.cline_key(14, 111),
            (("n_CLINE_TYPE", 14), ("n_CREATURE_TYPE", 111)),
        )

    def test_the_rule_covers_every_set_number_scene_14_actually_ships(self):
        # The test that caught the ordinal misreading: scene 14 ships Mob-Set
        # 111 out of a block of 51 rows, so a rule that treats the set number
        # as a position into the block refuses a placement on the wire today.
        for placement in world_bg0015_identity.shippable_placements():
            sea.cline_key(14, placement.template_id)

    def test_scene_14_really_does_ship_a_set_past_its_block_length(self):
        highest = max(
            p.template_id
            for p in world_bg0015_identity.shippable_placements()
        )
        _base, count, _lowest, _highest = sea.CLINE_BLOCKS[14]
        self.assertGreater(
            highest, count,
            "if scene 14 ever stops shipping a set number past its block "
            "length, this module's warning has lost its only witness",
        )

    def test_a_set_number_outside_the_measured_key_range_is_refused(self):
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(14, 116)   # keys measured 1..115
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(3001, 57)  # keys measured 1..56
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(14, 0)

    def test_an_unmeasured_cline_type_is_refused(self):
        with self.assertRaises(sea.SeaDestinationError):
            sea.cline_key(3002, 1)


class FeasibilityCountTests(unittest.TestCase):
    def test_the_two_variant_rows_are_resolving_rows_not_a_drop(self):
        # The corrected count.  An earlier draft reported 31 of 38 by
        # treating these six as unresolvable; both of their legs resolve.
        self.assertEqual(sea.RESOLVING_PLACEMENT_COUNT, 37)
        self.assertLessEqual(
            sea.TWO_VARIANT_PLACEMENT_COUNT, sea.RESOLVING_PLACEMENT_COUNT,
        )
        self.assertEqual(
            sea.RESOLVING_PLACEMENT_COUNT + sea.EMPTY_LEADER_PLACEMENT_COUNT,
            sea.PLACEMENT_COUNT,
        )

    def test_the_two_variant_shape_is_not_claimed_to_be_rare(self):
        placements, scenes = sea.TWO_VARIANT_SHAPE_TREE_WIDE
        self.assertGreater(placements, sea.PLACEMENT_COUNT)
        self.assertGreater(scenes, 1)


class SeaMapTests(unittest.TestCase):
    """``sea_map_console_line`` widens the single-door registry question
    (``console_line``, scene 17 only) to all eight ``COLUMBUS_ROUTES``
    islands, by reusing the same registry-reading helpers rather than
    re-deriving a second set - these tests hold that generalization to the
    same discipline ``ArrivalPointTests`` holds the scene-17-only path to.
    """

    def setUp(self):
        self.registry = world_scene_travel.load_scene_registry()

    def test_the_model_id_table_names_exactly_the_eight_route_targets(self):
        targets = {row[3] for row in sea.COLUMBUS_ROUTES}
        self.assertEqual(set(sea.COLUMBUS_ROUTE_SCENE_MODEL_ID), targets)
        self.assertEqual(set(sea.COLUMBUS_ROUTE_SCENE_NAME_MARKER), targets)
        self.assertEqual(
            sea.COLUMBUS_ROUTE_SCENE_MODEL_ID[sea.DESTINATION_SCENE_N_ID],
            sea.DESTINATION_SCENE_MODEL_ID,
        )
        # Measured, not derived by the Bg100<n> arithmetic that happens to
        # hold for scenes 17-21 and breaks for 39/40/41 (Bg1023/24/25).
        self.assertEqual(sea.COLUMBUS_ROUTE_SCENE_MODEL_ID[39], "Bg1023")
        self.assertEqual(sea.COLUMBUS_ROUTE_SCENE_MODEL_ID[41], "Bg1025")

    def test_generalized_helpers_agree_with_the_scene_17_only_originals(self):
        self.assertEqual(
            sea._target_for(self.registry, sea.DESTINATION_SCENE_N_ID),
            sea._target(self.registry),
        )
        self.assertEqual(
            sea.arrival_position_for(self.registry, sea.DESTINATION_SCENE_N_ID),
            sea.arrival_position(self.registry),
        )
        self.assertEqual(
            sea.arrival_is_decreed_for(self.registry, sea.DESTINATION_SCENE_N_ID),
            sea.arrival_is_decreed(self.registry),
        )
        self.assertEqual(
            sea.destination_state_for(self.registry, sea.DESTINATION_SCENE_N_ID),
            sea.destination_state(self.registry),
        )

    def test_a_scene_absent_from_the_registry_refuses_not_raises(self):
        # None of the sea family beyond scene 17 has a registry row today.
        self.assertIsNone(sea.arrival_position_for(self.registry, 18))
        self.assertEqual(
            sea.destination_state_for(self.registry, 18), sea.STATE_REFUSED,
        )

    def test_sea_map_lines_names_all_eight_in_columbus_routes_order(self):
        rows = sea.sea_map_lines(self.registry)
        self.assertEqual(len(rows), 8)
        self.assertEqual(
            tuple(scene for scene, _model, _state in rows),
            tuple(row[3] for row in sea.COLUMBUS_ROUTES),
        )
        self.assertEqual(rows[0], (17, "Bg1001", sea.STATE_READY_DECREED))
        for scene, model, state in rows[1:]:
            self.assertEqual(state, sea.STATE_REFUSED)
            self.assertEqual(model, sea.COLUMBUS_ROUTE_SCENE_MODEL_ID[scene])

    def test_sea_map_lines_requires_a_real_registry_never_reads_the_file(self):
        with self.assertRaises(sea.SeaDestinationError):
            sea.sea_map_lines(None)
        with self.assertRaises(sea.SeaDestinationError):
            sea.sea_map_lines([1, 2, 3])

    def test_console_line_counts_and_is_ascii(self):
        line = sea.sea_map_console_line(self.registry)
        line.encode("ascii")
        self.assertTrue(line.startswith(sea.SEA_MAP_CONSOLE_TAG + " "))
        self.assertIn("islands=8", line)
        self.assertIn("ready_decreed=1", line)
        self.assertIn("ready_not_decreed=0", line)
        self.assertIn("refused=7", line)
        self.assertIn("17:READY_DECREED", line)

    def test_console_line_safe_names_a_none_registry_rather_than_guessing(self):
        self.assertEqual(
            sea.sea_map_console_line_safe(None),
            sea.SEA_MAP_CONSOLE_TAG + " unmeasured "
            "reason=call_site_passed_no_registry",
        )

    def test_console_line_safe_never_raises_on_a_registry_missing_the_attr(
        self,
    ):
        line = sea.sea_map_console_line_safe(object())
        self.assertTrue(
            line.startswith(sea.SEA_MAP_CONSOLE_TAG + " unmeasured "), line,
        )
        self.assertIn("reason=refused:", line)


if __name__ == "__main__":
    unittest.main()
