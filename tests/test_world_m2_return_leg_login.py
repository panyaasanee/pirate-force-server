"""The way out of a one-way scene - LANE-A round `umv5w2`, COO-DECISION
20260908_1943 Q2.

WHAT THIS FILE IS ABOUT.  PANYA-DECISION 20260908_1218 made the durable row
follow a character everywhere, sea included, and nothing in this tree can
dispatch a character back out of the sea scene.  A login that puts the row
back where it was is therefore a character that never plays again.  The
decision above says 1218 never meant that and hands the way out to this lane.

WHAT IT DOES NOT PIN.  Nothing here says a player has seen this: no login on a
running server reaches `login_entry` yet (the call site is `runtime.py`, the
chief's file).  These cases pin the DECISION - which scene the ticket fires
for, which it does not, and that it never overrides a refusal.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import pf_bent_scene_registry  # noqa: E402
from pirateforce_foundation import world_m2_sea_destination  # noqa: E402
from pirateforce_foundation import world_m2_return_leg  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

HOME = world_scene_travel.HOME_SCENE_ID
SEA = world_m2_sea_destination.DESTINATION_SCENE_N_ID


def _sea_row() -> Position:
    """The row PANYA-DECISION 1218 headlines, measured inside 17's box."""
    return Position(SEA, 0, -149.0, -1250.3, 745.0)


class OneWaySceneIdsAreDerived(unittest.TestCase):

    def test_the_set_is_the_crossing_a_player_can_actually_make(self):
        self.assertEqual(
            frozenset({SEA}), world_scene_entry.one_way_scene_ids(),
            "the only in-game crossing this tree dispatches is Columbus "
            "quest 3021 into the sea scene",
        )

    def test_a_scene_with_a_way_out_leaves_the_set(self):
        """The exit half is a table, not a literal, and this proves it.

        The day any lane builds a dispatch site that sends a character out of
        the sea, its scene id goes in `_SCENES_WITH_A_MEASURED_WAY_OUT` and
        the ticket stops firing with no other edit.  Patched rather than
        waited for.
        """
        real = world_scene_entry._SCENES_WITH_A_MEASURED_WAY_OUT
        world_scene_entry._SCENES_WITH_A_MEASURED_WAY_OUT = frozenset({SEA})
        self.addCleanup(
            setattr, world_scene_entry, "_SCENES_WITH_A_MEASURED_WAY_OUT",
            real,
        )
        self.assertEqual(frozenset(), world_scene_entry.one_way_scene_ids())


class TheTicketFiresForTheSeaAndNothingElse(unittest.TestCase):

    def setUp(self):
        self.registry = world_scene_travel.load_scene_registry()

    def _login(self, row):
        lines = []
        entry, ticketed = world_m2_return_leg.login_entry(
            row, registry=self.registry, emit=lines.append)
        return entry, ticketed, lines

    def test_a_login_at_sea_lands_at_home_and_says_so(self):
        entry, ticketed, lines = self._login(_sea_row())
        self.assertEqual(HOME, entry.destination.n_id)
        self.assertEqual(SEA, ticketed.scene_id)
        ticket = [l for l in lines if l.startswith("WORLD_SCENE_RETURN_TICKET")]
        self.assertEqual(1, len(ticket), lines)
        self.assertIn(
            world_scene_entry.RELOCATED_ONE_WAY_SCENE_RETURN_TICKET, ticket[0])
        # The row it came FROM is on the line, not only the row it goes to:
        # a console reader has to be able to tell which character moved.
        self.assertIn("stored=(-149.000,-1250.300,745.000)", ticket[0])
        # And the ticket line is printed BEFORE the arrival line, so a reader
        # sees the reason above the destination it explains.
        self.assertLess(
            lines.index(ticket[0]),
            [i for i, l in enumerate(lines)
             if l.startswith("WORLD_SCENE ")][0],
        )

    def test_a_login_anywhere_else_is_1218_untouched(self):
        """Every populated scene but the sea keeps the row, byte for byte."""
        for scene_id in sorted(world_scene_travel.CENSUS_SOURCES):
            if scene_id == SEA:
                continue
            with self.subTest(scene=scene_id):
                destination = self.registry[scene_id]
                if destination.spawn is None:
                    continue
                row = Position(scene_id, 0, *destination.spawn)
                entry, ticketed, lines = self._login(row)
                self.assertIsNone(ticketed)
                self.assertEqual(scene_id, entry.destination.n_id)
                self.assertEqual(
                    [], [l for l in lines
                         if l.startswith("WORLD_SCENE_RETURN_TICKET")])

    def test_a_shut_door_still_refuses_rather_than_handing_out_a_ticket(self):
        """The sanction wins over the ticket, and this is the case that says so.

        Without this the ticket would answer a refusal the registry asked for:
        a scene LANE-GM or an operator pinned shut would quietly start walking
        characters home instead of refusing them, and the refusal IS the
        sanction.  Driven through a bent reading of the real registry rather
        than a scene that happens to be shut, because 1218 left none shut.
        """
        bent = pf_bent_scene_registry.shut_at_login(SEA)
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_m2_return_leg.login_entry(
                _sea_row(), registry=bent, emit=lambda line: None)
        self.assertEqual(
            world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN,
            caught.exception.reason,
        )

    def test_a_scene_id_the_registry_does_not_carry_is_still_refused(self):
        with self.assertRaises(world_scene_entry.SceneEntryRefused):
            world_m2_return_leg.login_entry(
                Position(9999, 0, 0.0, 0.0, 0.0), registry=self.registry,
                emit=lambda line: None)


if __name__ == "__main__":
    unittest.main()
