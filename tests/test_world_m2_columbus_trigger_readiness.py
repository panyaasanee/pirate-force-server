"""Tests for ``world_m2_columbus_trigger_readiness``.

The module ships no wire bytes, so what is worth testing is what it can get
wrong: reading the wrong column off a scene's own resolved placements (its
first draft matched ``template_id`` instead of ``identity.mobs_n_id`` and got
every non-Port-Royal island wrong), claiming an island's Columbus is placed
when it is not, and going quiet instead of reporting UNMEASURED when a caller
withholds ``legacy``.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import columbus_quest_dispatch  # noqa: E402
from pirateforce_foundation import world_m2_columbus_trigger_readiness as trig  # noqa: E402
from pirateforce_foundation import world_m2_sea_destination  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class TriggerStateForTests(unittest.TestCase):
    def test_rejects_non_int_arguments(self):
        with self.assertRaises(trig.TriggerReadinessError):
            trig.trigger_state_for("156", 1)
        with self.assertRaises(trig.TriggerReadinessError):
            trig.trigger_state_for(156, "1")

    def test_rejects_a_home_scene_columbus_routes_does_not_name(self):
        with self.assertRaises(trig.TriggerReadinessError):
            trig.trigger_state_for(1, 99)

    def test_port_royal_is_unmeasured_with_no_legacy(self):
        self.assertEqual(
            trig.trigger_state_for(156, 1), trig.STATE_UNMEASURED,
        )

    def test_port_royal_is_placed_with_the_real_legacy_module(self):
        # columbus_actor_identity resolving without raising is exactly the
        # check the shipped, GT-148-confirmed dispatch itself relies on.
        self.assertEqual(
            trig.trigger_state_for(156, 1, legacy=_legacy()),
            trig.STATE_PLACED,
        )

    def test_every_non_port_royal_route_matches_columbus_routes_exactly(self):
        """Ground truth, re-derived directly against each scene's own
        shipped identity module rather than trusted from this module's own
        docstring - a passing test here is what caught the ``template_id``
        vs ``identity.mobs_n_id`` mistake before it shipped."""
        for mobs_n_id, home_scene, _row, _target, _ocean in (
            world_m2_sea_destination.COLUMBUS_ROUTES
        ):
            if home_scene == 1:
                continue
            with self.subTest(home_scene=home_scene, mobs_n_id=mobs_n_id):
                state = trig.trigger_state_for(mobs_n_id, home_scene)
                if home_scene == 2:
                    # THE DISCREPANCY THIS ROUND FOUND AND DID NOT PAPER
                    # OVER: Prison Exile's own table places MOBS n_id 36
                    # (Spice Paradise's Columbus) under its "Columbus" row,
                    # not 360 - see the module docstring for the full
                    # citation trail (both 36 and 360 are real
                    # CONSTDATA_TH__MOBS.tsv rows).
                    self.assertEqual(state, trig.STATE_NOT_PLACED)
                else:
                    self.assertEqual(state, trig.STATE_PLACED)

    def test_home_scene_2_columbus_is_present_under_the_OTHER_id(self):
        """Pins the actual finding, not just its absence: 36 - not 360 - is
        what Prison Exile's own table carries for its Columbus row, so a
        reader can tell "wrong id" from "no Columbus placed at all"."""
        ids = trig._bg0002_mobs_n_ids()
        self.assertIn(36, ids)
        self.assertNotIn(360, ids)


class TriggerReadinessRowsTests(unittest.TestCase):
    def test_widens_across_all_eight_columbus_routes_rows(self):
        rows = trig.trigger_readiness_rows(legacy=_legacy())
        self.assertEqual(len(rows), len(world_m2_sea_destination.COLUMBUS_ROUTES))
        by_home = {home: state for _mobs, home, state in rows}
        self.assertEqual(by_home[1], trig.STATE_PLACED)
        self.assertEqual(by_home[2], trig.STATE_NOT_PLACED)
        for home in (3, 4, 5, 6, 7, 8):
            self.assertEqual(by_home[home], trig.STATE_PLACED)

    def test_without_legacy_only_home_scene_1_goes_unmeasured(self):
        rows = trig.trigger_readiness_rows()
        by_home = {home: state for _mobs, home, state in rows}
        self.assertEqual(by_home[1], trig.STATE_UNMEASURED)
        for home in (3, 4, 5, 6, 7, 8):
            self.assertEqual(by_home[home], trig.STATE_PLACED)
        self.assertEqual(by_home[2], trig.STATE_NOT_PLACED)


class ConsoleLineTests(unittest.TestCase):
    def test_the_line_reports_the_true_counts(self):
        line = trig.trigger_readiness_console_line(legacy=_legacy())
        self.assertTrue(line.startswith(trig.CONSOLE_TAG + " "))
        self.assertIn("islands=8", line)
        self.assertIn("placed=7", line)
        self.assertIn("not_placed=1", line)
        self.assertIn("unmeasured=0", line)
        self.assertIn("1:PLACED", line)
        self.assertIn("2:NOT_PLACED", line)

    def test_never_raises_and_reports_unmeasured_with_no_legacy(self):
        line = trig.trigger_readiness_console_line()
        self.assertTrue(line.startswith(trig.CONSOLE_TAG + " "))
        self.assertIn("unmeasured=1", line)
        self.assertIn("1:UNMEASURED", line)

    def test_the_line_is_cp874_encodable(self):
        line = trig.trigger_readiness_console_line(legacy=_legacy())
        line.encode("cp874")
        self.assertTrue(all(0x20 <= ord(ch) < 0x7F for ch in line))


class DispatchWiringTests(unittest.TestCase):
    """The default path prints it.  No flag, no scenario, no argument."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()

    def test_a_columbus_crossing_prints_the_trigger_readiness_line_last(self):
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append, legacy=self.legacy, held_indices=(),
        )
        self.assertTrue(
            lines[-1].startswith(trig.CONSOLE_TAG + " "), lines)
        self.assertIn("placed=7", lines[-1])
        self.assertIn("not_placed=1", lines[-1])

    def test_the_line_still_prints_when_the_call_site_has_no_legacy(self):
        lines = []
        columbus_quest_dispatch.dispatch_columbus_quest3021(
            emit=lines.append,
        )
        matching = [
            line for line in lines
            if line.startswith(trig.CONSOLE_TAG + " ")
        ]
        self.assertEqual(len(matching), 1, lines)
        self.assertIn("unmeasured=1", matching[0])


if __name__ == "__main__":
    unittest.main()
