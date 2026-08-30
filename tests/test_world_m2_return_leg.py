"""LANE-A M2: the way back, captured at the moment of departure.

The load-bearing tests here are the two that keep an ABSENCE from reading as a
MEASUREMENT: a crossing dispatched without the character's departure row must
say so in its own field, and a report that measured nothing must not be able to
produce ``drift=0.0``, which is a real answer meaning "the fallback is exactly
right for this character".
"""

import math
from pathlib import Path
import sys
import unittest
import unittest.mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch
from pirateforce_foundation import world_m2_return_leg
from pirateforce_foundation import world_scene_entry
from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.model import Position
from pirateforce_foundation import world_population
from pirateforce_foundation.world_m2_return_leg import (
    NO_DEPARTURE_ROW,
    SOURCE_DEPARTED_ROW,
    SOURCE_NONE_OWED,
    SOURCE_NOT_NAMED,
    SOURCE_PINNED_HOME_ENTRY,
    DepartureRowRefused,
    drift_from_pinned_home,
    remember_departure,
    return_leg,
    return_leg_console_line,
    return_population_console_line,
    return_population_owed,
)


class DepartureRowTests(unittest.TestCase):
    def test_a_departure_row_must_be_a_home_scene_position(self) -> None:
        home = world_scene_travel.home_return_position()
        self.assertIs(remember_departure(home), home)
        for refused in (
            None,
            "1,0,0,0",
            (1, 0, 0.0, 0.0, 0.0, 0.0),
            # A row already naming the sea is not a departure FROM home, and
            # accepting it would mint a ticket back into the scene the player
            # is trying to leave.
            Position(17, 0, 0.0, 0.0, 0.0, 0.0),
            Position(278, 0, 1.0, 2.0, 3.0, 0.0),
            Position(1, 0, float("nan"), 0.0, 0.0, 0.0),
            Position(1, 0, 0.0, float("inf"), 0.0, 0.0),
        ):
            with self.assertRaises(DepartureRowRefused):
                remember_departure(refused)

    def test_drift_is_zero_only_for_a_character_on_the_pinned_entry(
        self,
    ) -> None:
        home = world_scene_travel.home_return_position()
        self.assertEqual(drift_from_pinned_home(home), 0.0)
        moved = Position(1, 0, home.x + 300.0, home.y - 400.0, home.z, 0.0)
        self.assertAlmostEqual(drift_from_pinned_home(moved), 500.0, places=3)

    def test_drift_counts_height_as_well_as_ground_distance(self) -> None:
        # A character handed back 900 units above where they left is not back,
        # so z is in the measurement rather than dropped for convenience.
        home = world_scene_travel.home_return_position()
        above = Position(1, 0, home.x, home.y, home.z + 900.0, 0.0)
        self.assertAlmostEqual(drift_from_pinned_home(above), 900.0, places=3)


class ReturnLegReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)
        cls.home_entry = world_scene_travel.home_return_position()

    def test_the_sea_crossing_owes_a_ticket_and_the_registry_says_so(
        self,
    ) -> None:
        # Not this module's opinion: world_scene_entry decides, and scene 17
        # is a non-home destination.
        self.assertTrue(self.entry.return_ticket_required)
        report = return_leg(self.entry)
        self.assertTrue(report["owed"])

    def test_without_a_departure_row_the_source_and_the_reason_are_named(
        self,
    ) -> None:
        report = return_leg(self.entry)
        self.assertEqual(report["source"], SOURCE_PINNED_HOME_ENTRY)
        self.assertEqual(report["reason"], NO_DEPARTURE_ROW)
        # The ticket still exists - it is the generic one - and the drift is
        # unmeasurable rather than zero.
        self.assertEqual(report["position"], self.home_entry)
        self.assertIsNone(report["drift"])

    def test_with_a_departure_row_the_ticket_is_that_row(self) -> None:
        departed = Position(
            1, 0, self.home_entry.x + 100.0, self.home_entry.y,
            self.home_entry.z, 1.25,
        )
        report = return_leg(self.entry, departed=departed)
        self.assertEqual(report["source"], SOURCE_DEPARTED_ROW)
        self.assertIsNone(report["reason"])
        self.assertEqual(report["position"], departed)
        # The heading the character was facing survives, which the fallback
        # row does not carry.
        self.assertEqual(report["position"].heading, 1.25)
        self.assertAlmostEqual(report["drift"], 100.0, places=3)

    def test_a_home_destination_owes_nothing_and_says_that_too(self) -> None:
        home_entry = world_scene_entry.resolve_entry(
            world_scene_travel.home_return_position(),
            emit=lambda line: None,
        )
        report = return_leg(home_entry)
        self.assertFalse(report["owed"])
        self.assertEqual(report["source"], SOURCE_NONE_OWED)
        self.assertIsNone(report["position"])
        self.assertIsNone(report["drift"])
        self.assertIn(
            "owed=NO", return_leg_console_line(home_entry))


class ReturnLegConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)

    def test_the_line_reaches_a_cp874_console_in_every_state(self) -> None:
        home = world_scene_travel.home_return_position()
        for line in (
            return_leg_console_line(self.entry),
            return_leg_console_line(self.entry, departed=home),
            return_leg_console_line(self.entry, departed="not a row"),
            return_leg_console_line("not an entry"),
            return_leg_console_line(None, departed=None),
        ):
            self.assertTrue(line.startswith("WORLD_M2_RETURN_LEG "))
            self.assertNotIn("\n", line)
            line.encode("ascii")
            line.encode("cp874")

    def test_nothing_a_caller_can_hand_this_makes_it_raise(self) -> None:
        # It runs inside the dispatch that sends a player to sea; a report
        # that can throw turns a reporting gap into a lost crossing.
        class Exploding:
            @property
            def return_ticket_required(self):
                raise RuntimeError("boom")

        for bad_entry in (None, 0, [], Exploding(), object()):
            for bad_row in (None, "x", 3, Position(17, 0, 0.0, 0.0, 0.0, 0.0)):
                line = return_leg_console_line(bad_entry, departed=bad_row)
                self.assertTrue(line.startswith("WORLD_M2_RETURN_LEG "))
                line.encode("cp874")

    def test_the_unmeasured_line_is_not_the_measured_line_with_a_zero(
        self,
    ) -> None:
        unmeasured = return_leg_console_line(self.entry)
        measured = return_leg_console_line(
            self.entry, departed=world_scene_travel.home_return_position())
        self.assertIn("source=" + SOURCE_PINNED_HOME_ENTRY, unmeasured)
        self.assertIn("drift=unmeasured:" + NO_DEPARTURE_ROW, unmeasured)
        self.assertNotIn("drift=0.0", unmeasured)
        # And the measured line for a character who really is standing on the
        # pinned entry DOES say 0.0 - the two states are distinguishable in
        # both directions, which is the whole point of the pair.
        self.assertIn("source=" + SOURCE_DEPARTED_ROW, measured)
        self.assertIn("drift=0.0", measured)


class ReturnPopulationOwedTests(unittest.TestCase):
    """The other half of the return trip: who would be there, not sent."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)

    def test_a_home_destination_owes_no_population_either(self) -> None:
        home_entry = world_scene_entry.resolve_entry(
            world_scene_travel.home_return_position(),
            emit=lambda line: None,
        )
        report = return_population_owed(home_entry)
        self.assertFalse(report["owed"])
        self.assertIsNone(report["source"])
        self.assertIsNone(report["count"])
        self.assertIsNone(report["count_source"])

    def test_the_sea_crossing_owes_the_home_census_by_name(self) -> None:
        # Reuses the exact selectors the real login/crossing path reads
        # rather than re-deriving them, so this cannot disagree with the
        # composer that would actually build the roster.
        report = return_population_owed(self.entry)
        self.assertTrue(report["owed"])
        self.assertEqual(report["source"], world_scene_travel.CENSUS_SOURCE)
        expected_count, expected_source = (
            world_population.census_count_for_dispatch()
        )
        self.assertEqual(report["count"], expected_count)
        self.assertEqual(report["count_source"], expected_source)

    def test_a_non_census_source_is_named_but_not_counted(self) -> None:
        # Not reachable from the shipped registry today (the only return
        # target is HOME_SCENE_ID, and it always names CENSUS_SOURCE) - forced
        # here with a patch so this branch has real coverage rather than only
        # the constant-value check below.  A mutant that always takes the
        # census branch would pass every OTHER test in this class but fails
        # this one, because it would report a count where none is owed.
        with unittest.mock.patch.object(
            world_scene_travel, "population_source",
            lambda n_id: "some_other_roster",
        ):
            report = return_population_owed(self.entry)
        self.assertTrue(report["owed"])
        self.assertEqual(report["source"], "some_other_roster")
        self.assertIsNone(report["count"])
        self.assertIsNone(report["count_source"])

    def test_no_named_source_reports_the_named_absence(self) -> None:
        with unittest.mock.patch.object(
            world_scene_travel, "population_source", lambda n_id: None,
        ):
            report = return_population_owed(self.entry)
        self.assertTrue(report["owed"])
        self.assertEqual(report["source"], SOURCE_NOT_NAMED)
        self.assertIsNone(report["count"])
        line = return_population_console_line(self.entry)
        # The console wrapper is not patched here, so this call takes the
        # real (census) path - proving the two tests exercise genuinely
        # different code, not the same line read twice.
        self.assertIn("kind=census", line)

    def test_owed_is_shared_with_return_leg_not_re_derived(self) -> None:
        # A departure row already in the sea scene makes ``return_leg`` raise
        # (``world_scene_entry.return_ticket``'s own scene guard, a plain
        # ``ValueError``); this function must see the SAME failure, not
        # silently answer "not owed" by catching it locally.
        broken = Position(17, 0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            return_population_owed(self.entry, departed=broken)

    def test_this_function_never_builds_the_actual_roster(self) -> None:
        # The whole point of reading only the selectors: this must not touch
        # the module that actually composes wire bytes for a scene.  Call
        # syntax, not bare words: the module docstring names
        # ``world_population_handoff`` in prose to explain why it is NOT
        # called, so a bare-word check would fail on the explanation itself.
        source = (
            ROOT / "src/pirateforce_foundation/world_m2_return_leg.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "world_population_handoff.handoff_on_crossing(", source)
        self.assertNotIn(
            "world_population_handoff.handoff_for_arrival(", source)
        self.assertNotIn("import world_population_handoff", source)


class ReturnPopulationConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.entry = columbus_quest_dispatch.resolve_columbus_arrival(
            emit=lambda line: None)

    def test_the_line_reaches_a_cp874_console_in_every_state(self) -> None:
        home = world_scene_travel.home_return_position()
        for line in (
            return_population_console_line(self.entry),
            return_population_console_line(self.entry, departed=home),
            return_population_console_line(self.entry, departed="not a row"),
            return_population_console_line("not an entry"),
            return_population_console_line(None, departed=None),
        ):
            self.assertTrue(line.startswith("WORLD_M2_RETURN_POPULATION "))
            self.assertNotIn("\n", line)
            line.encode("ascii")
            line.encode("cp874")

    def test_nothing_a_caller_can_hand_this_makes_it_raise(self) -> None:
        class Exploding:
            @property
            def return_ticket_required(self):
                raise RuntimeError("boom")

        for bad_entry in (None, 0, [], Exploding(), object()):
            for bad_row in (None, "x", 3, Position(17, 0, 0.0, 0.0, 0.0, 0.0)):
                line = return_population_console_line(
                    bad_entry, departed=bad_row)
                self.assertTrue(
                    line.startswith("WORLD_M2_RETURN_POPULATION "))
                line.encode("cp874")

    def test_the_measured_line_names_source_kind_and_count(self) -> None:
        line = return_population_console_line(self.entry)
        self.assertIn("owed=YES", line)
        self.assertIn("source=" + world_scene_travel.CENSUS_SOURCE, line)
        self.assertIn("kind=census", line)
        self.assertIn("composed=NO", line)
        count, count_source = world_population.census_count_for_dispatch()
        self.assertIn("count={0}".format(count), line)
        self.assertIn("count_source=" + count_source, line)

    def test_a_home_destination_says_owed_no(self) -> None:
        home_entry = world_scene_entry.resolve_entry(
            world_scene_travel.home_return_position(),
            emit=lambda line: None,
        )
        self.assertIn(
            "owed=NO", return_population_console_line(home_entry))

    def test_source_not_named_is_a_real_reachable_string(self) -> None:
        # Not reachable from the shipped registry today (the only return
        # target names CENSUS_SOURCE), so this exercises the constant
        # directly rather than leaving it untested dead code.
        self.assertEqual(SOURCE_NOT_NAMED, "no_named_population_source")


class CrossingPrintsTheWayBackTests(unittest.TestCase):
    """The wiring: every boarding prints this, on the flagless path."""

    def test_the_columbus_dispatch_prints_the_return_leg_every_time(
        self,
    ) -> None:
        lines = []
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append)
        matching = [
            line for line in lines if line.startswith("WORLD_M2_RETURN_LEG ")
        ]
        self.assertEqual(len(matching), 1, lines)
        # Today the call site passes no departure row, and the line says which
        # of the two tickets this crossing got rather than going quiet.
        self.assertIn("source=" + SOURCE_PINNED_HOME_ENTRY, matching[0])
        self.assertIn(NO_DEPARTURE_ROW, matching[0])
        self.assertEqual(entry.destination.n_id, 17)

    def test_the_line_carries_the_departure_row_once_the_call_site_has_one(
        self,
    ) -> None:
        home = world_scene_travel.home_return_position()
        departed = Position(1, 0, home.x - 731.0, home.y, home.z, 2.0)
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, departed_from=departed)
        matching = [
            line for line in lines if line.startswith("WORLD_M2_RETURN_LEG ")
        ]
        self.assertEqual(len(matching), 1, lines)
        self.assertIn("source=" + SOURCE_DEPARTED_ROW, matching[0])
        self.assertIn("drift=731.0", matching[0])
        self.assertIn("heading=2.000", matching[0])

    def test_a_broken_departure_row_does_not_cost_the_crossing(self) -> None:
        # The teleport is what the player came for; a report that refuses its
        # own input must not take the trip down with it.
        lines = []
        entry = columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, departed_from=Position(17, 0, 0., 0., 0., 0.))
        self.assertEqual(entry.destination.n_id, 17)
        self.assertTrue(
            any(line.startswith("WORLD_M2_RETURN_LEG unmeasured")
                for line in lines),
            lines,
        )
        # And the teleport fields the runtime hands to make_login_teleport are
        # untouched by any of this.
        self.assertEqual(len(tuple(entry.teleport_fields)), 5)

    def test_the_report_module_sends_nothing_and_writes_nothing(self) -> None:
        source = (
            ROOT / "src/pirateforce_foundation/world_m2_return_leg.py"
        ).read_text(encoding="utf-8")
        # Call syntax, not bare words: "store" appears inside "docstring" and
        # a substring test that matches prose proves nothing about behaviour.
        for forbidden in (
            "make_login_teleport(", "update_position(", "store.",
            "sqlite3", "make_runtime", "sendall(", "import socket",
        ):
            self.assertNotIn(forbidden, source)
        # And the whole of what it may reach: readers only.  A new one here
        # is a review conversation, not a diff nobody notices.
        #
        # ROUND 4lrspn ADDS ONE: ``world_population``,
        # for ``census_count_for_dispatch`` - a count, not a wire (see the
        # module docstring for why this module still never calls
        # ``world_population_handoff``, the module that actually builds one).
        imports = sorted(
            line.strip() for line in source.splitlines()
            if line.startswith(("import ", "from "))
        )
        self.assertEqual(imports, [
            "from . import world_population",
            "from . import world_scene_entry",
            "from . import world_scene_travel",
            "from .model import Position",
            "from .world_scene_travel import HOME_SCENE_ID",
            "from __future__ import annotations",
            "import math",
        ])

    def test_the_module_is_ascii_because_the_bridge_console_is_cp874(
        self,
    ) -> None:
        source = (
            ROOT / "src/pirateforce_foundation/world_m2_return_leg.py"
        ).read_text(encoding="utf-8")
        source.encode("ascii")


if __name__ == "__main__":
    unittest.main()
