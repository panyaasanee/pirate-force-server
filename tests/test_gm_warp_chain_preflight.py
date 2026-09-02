"""The GT-192 preflight, and the one mistake it exists to not make.

``gm/warp_chain_preflight.py`` predicts, before an attended round is booked,
what the server will compose for every map ``/warp`` can reach.  The value of
such a tool is entirely in being right about the maps that are DIFFERENT, so
most of this file is about those:

* scene 2, whose roster ships from the runtime's own bg0002 arm.  The
  everyday arrival seam -- the one every other scene answers through --
  reports ``clear``/0 for it.  A preflight that trusted that seam would print
  ``0`` for the FIRST map on the owner's list and send a tester hunting a bug
  that is not there.  ``TheSceneTwoTrapTests`` measures both halves: that the
  seam really does say clear/0, and that the tool does not repeat it;
* scene 1, empty on arrival BY DESIGN and full one step later.  The tool must
  say ``empty_by_design``, not ``0``, or the tester grades the design as a
  FAIL;
* every other scene, whose count must come off the seam rather than off a
  label a lane handed over.

And one guard that is not about a scene at all: the runtime's bg0002 call
site is READ FROM SOURCE here, because this tool's scene-2 number is only
true while the tool calls that arm the way the runtime does.  If chief
changes those arguments, this file goes red rather than the tool quietly
lying to a tester.
"""

import ast
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    lane_hooks,
    world_population,
    world_population_bg0002,
    world_population_handoff,
    world_scene_travel,
)
from pirateforce_foundation.gm import warp_chain_preflight as preflight  # noqa: E402
from pirateforce_foundation.gm.warp_executor import (  # noqa: E402
    warp_no_coords_live_target,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
RUNTIME_PATH = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
MODULE_PATH = (
    ROOT / "src" / "pirateforce_foundation" / "gm" / "warp_chain_preflight.py"
)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _Raises:
    """A legacy object every attribute access on explodes.

    Not ``None``: ``None`` might be handled by an ``is None`` branch
    somewhere and prove nothing about the failure path this tool promises.
    """

    def __getattr__(self, name):
        raise RuntimeError("legacy unavailable: " + name)


class TheChainIsTheOwnersOwnListTests(unittest.TestCase):
    """COO-DECISION 20260902_0544: scenes 2-11, 14, 130, closing with 1."""

    def test_the_reachable_set_is_the_thirteen_scenes_the_tester_types(self):
        self.assertEqual(
            preflight.reachable_scene_ids(),
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130),
        )

    def test_the_gate_this_module_asks_is_the_production_gate(self):
        """Not a list in the module.  The day LANE-A opens a scene, this
        covers it without an edit -- and the day one closes, no row here
        describes a map nobody can reach."""
        self.assertEqual(
            preflight.reachable_scene_ids(),
            tuple(
                scene_id
                for scene_id in preflight.scene_catalog.SCENE_ID_TO_GM_NAME
                if warp_no_coords_live_target(scene_id) is not None
            ),
        )

    def test_scene_one_is_last_because_a_session_boots_there(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        self.assertEqual([r.scene_id for r in rows][-1], world_population.SCENE_ID)
        self.assertEqual(
            [r.scene_id for r in rows],
            [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130, 1],
        )


class TheSceneTwoTrapTests(unittest.TestCase):
    """The mistake this module was built around, pinned from both sides."""

    def test_the_everyday_seam_really_does_report_clear_zero_for_scene_two(self):
        """The premise.  If this ever stops being true the module's special
        case is dead weight and should be deleted, not left asserting."""
        scene_id = world_population_bg0002.SCENE2_N_ID
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        handoff = world_population_handoff.handoff_for_arrival(
            _legacy(), scene_id, anchor,
        )
        self.assertEqual(handoff.kind, world_population_handoff.KIND_CLEAR)
        self.assertEqual(int(handoff.actor_count), 0)
        self.assertIsNone(lane_hooks.scene_census_composer(scene_id))

    def test_the_preflight_does_not_repeat_the_seams_answer(self):
        row = preflight.preflight_for(
            world_population_bg0002.SCENE2_N_ID, legacy=_legacy()
        )
        self.assertEqual(row.source, preflight.SOURCE_RUNTIME_BG0002_ARM)
        self.assertTrue(row.on_arrival)
        self.assertIsNotNone(row.actor_count)
        self.assertGreater(row.actor_count, 0)

    def test_the_number_is_the_bg0002_arms_own_wire_count(self):
        scene_id = world_population_bg0002.SCENE2_N_ID
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        generation = world_population_bg0002.build_bg0002_population(
            _legacy(), anchor, scene_id=scene_id,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        self.assertEqual(
            preflight.preflight_for(scene_id, legacy=_legacy()).actor_count,
            world_population_bg0002.wire_actor_count(generation),
        )

    def test_the_runtimes_own_call_site_still_passes_these_arguments(self):
        """READ FROM SOURCE, not imported.

        This tool's scene-2 number is only true while it calls the arm the
        way ``runtime.py`` does.  ``runtime.py`` is chief's file; this lane
        cannot stop it changing, but it can stop the change being silent.
        """
        tree = ast.parse(RUNTIME_PATH.read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "build_bg0002_population"
        ]
        self.assertEqual(
            len(calls), 1,
            "runtime.py no longer has exactly one bg0002 build call; this "
            "tool's scene-2 prediction is derived from that one call site",
        )
        keywords = {kw.arg for kw in calls[0].keywords}
        self.assertIn("scene_id", keywords)
        self.assertIn("count_source", keywords)
        source = ast.unparse(calls[0])
        self.assertIn("COUNT_SOURCE_FULL_ROSTER", source, source)
        self.assertNotIn(
            "actor_count", keywords,
            "the runtime now passes an explicit actor_count; this tool "
            "predicts the default and would now be wrong",
        )


class TheOneMapThatIsEmptyOnPurposeTests(unittest.TestCase):
    """Scene 1.  ``empty_by_design`` and ``0`` are not the same sentence."""

    def test_scene_one_is_named_as_held_not_as_missing(self):
        row = preflight.preflight_for(world_population.SCENE_ID, legacy=_legacy())
        self.assertEqual(row.source, preflight.SOURCE_HELD_UNTIL_THE_PLAYER_MOVES)
        self.assertFalse(row.on_arrival)
        self.assertIn("ONE STEP", row.note.upper())

    def test_it_still_says_what_she_gets_after_the_step(self):
        """A tester who takes the step needs a number to compare against."""
        row = preflight.preflight_for(world_population.SCENE_ID, legacy=_legacy())
        self.assertIsNotNone(row.actor_count)
        self.assertGreater(row.actor_count, 0)

    def test_the_summary_separates_by_design_from_unexplained(self):
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        summary = [line for line in lines if " chain=" in line]
        self.assertEqual(len(summary), 1, lines)
        self.assertIn("empty_by_design=1", summary[0])
        self.assertIn("empty_unexplained=none", summary[0])


class TheCountsComeOffTheSeamTests(unittest.TestCase):
    def test_every_lane_composed_row_matches_an_independent_seam_read(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        composed = [r for r in rows if r.source == preflight.SOURCE_LANE_COMPOSER]
        self.assertGreaterEqual(
            len(composed), 8,
            "a chain this short is not the world GM-A was rejected over",
        )
        for row in composed:
            with self.subTest(scene=row.scene_id):
                anchor = world_scene_travel.spawn_position(
                    world_scene_travel.destination(row.scene_id)
                )
                handoff = world_population_handoff.handoff_for_arrival(
                    _legacy(), row.scene_id, anchor,
                )
                self.assertEqual(
                    handoff.kind, world_population_handoff.KIND_CENSUS
                )
                self.assertEqual(row.actor_count, int(handoff.actor_count))
                self.assertTrue(row.on_arrival)


class ItFailsClosedAndNamedTests(unittest.TestCase):
    def test_a_scene_warp_refuses_is_not_reported_as_an_empty_map(self):
        """``/warp 278`` is REFUSED BY NAME.  Confusing that with an empty
        map is how a tester reports a bug against a command that never ran."""
        self.assertIsNone(warp_no_coords_live_target(278))
        row = preflight.preflight_for(278, legacy=_legacy())
        self.assertEqual(row.source, preflight.SOURCE_NOTHING)
        self.assertIsNone(row.actor_count)
        self.assertIn("refuses", row.note)

    def test_a_broken_legacy_leaves_every_row_named_and_countless(self):
        rows = preflight.preflight_chain(legacy=_Raises())
        self.assertEqual(len(rows), 13)
        for row in rows:
            with self.subTest(scene=row.scene_id):
                self.assertIsNone(
                    row.actor_count,
                    "a count survived a legacy that cannot answer -- it was "
                    "not read from the seam",
                )
                self.assertFalse(row.on_arrival)

    def test_a_non_census_handoff_is_absence_not_a_count_of_zero(self):
        """``_lane_count``'s own guard, driven with a REAL non-census scene.

        No reachable scene reaches this branch through ``preflight_for``
        today -- scene 2 is special-cased above it and every other scene
        answers ``census`` -- so it is prospective, and a prospective branch
        with no test that kills it is not a branch.  Measured here against
        the one scene whose seam really does answer ``clear``: the guard must
        say "no number", never ``0``.  ``0`` would render as an empty map and
        a tester would grade a scene nobody had measured as a FAIL.
        """
        scene_id = world_population_bg0002.SCENE2_N_ID
        anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(scene_id)
        )
        self.assertEqual(
            world_population_handoff.handoff_for_arrival(
                _legacy(), scene_id, anchor,
            ).kind,
            world_population_handoff.KIND_CLEAR,
        )
        self.assertIsNone(
            preflight._lane_count(scene_id, anchor, legacy=_legacy()),
            "a clear handoff produced a number; every caller of this helper "
            "turns a number into 'the tester will see actors here'",
        )

    def test_no_row_ever_reports_zero_in_place_of_unknown(self):
        for legacy in (_legacy(), _Raises()):
            for row in preflight.preflight_chain(legacy=legacy):
                with self.subTest(scene=row.scene_id):
                    self.assertNotEqual(
                        row.actor_count, 0,
                        "0 and 'do not know' must never be the same value",
                    )


class TheOutputAnOwnerCanPasteBackTests(unittest.TestCase):
    def test_every_line_is_ascii_and_carries_the_token(self):
        """The bridge console is cp874 (GT-145); scene 10 and 11's GM names
        are Thai, so this is not a hypothetical."""
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        for line in lines:
            with self.subTest(line=line):
                line.encode("ascii")
                self.assertTrue(line.startswith(preflight.CONSOLE_TOKEN))

    def test_the_nonclaim_rides_the_output_not_only_the_docstring(self):
        """A tester reads the console, not this repository."""
        lines = preflight.render(preflight.preflight_chain(legacy=_legacy()))
        joined = " ".join(lines)
        self.assertIn("never what the client draws", joined)

    def test_one_line_per_scene_plus_summary_plus_note(self):
        rows = preflight.preflight_chain(legacy=_legacy())
        self.assertEqual(len(preflight.render(rows)), len(rows) + 2)


class ItGrantsNobodyAnythingTests(unittest.TestCase):
    """Lane rule 1: nothing here may hand out GM, and nothing here sends."""

    def test_the_module_opens_no_socket_and_reads_no_account_list(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imported.add(alias.name)
                imported.add(node.module or "")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
        for forbidden in ("socket", "accounts", "gm_accounts"):
            self.assertNotIn(forbidden, imported, forbidden)
        for forbidden in ("def send", "sendall", "production_allowed = True"):
            self.assertNotIn(forbidden, source, forbidden)


if __name__ == "__main__":
    unittest.main()
