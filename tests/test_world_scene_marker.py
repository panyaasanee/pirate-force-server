"""LANE-A M2: the MARKER crosswalk, and scene 14's arrival point.

The load-bearing tests here are the ones that would go red if the crosswalk
were quietly replaced by the shortcut that looks identical on the 12 scenes
where it happens to agree:

* ``test_the_marker_id_is_not_the_scene_id`` - scene 130 names marker 1000.
  A round that indexes MARKER by scene id passes every other test in this file
  and puts one map's arrival point in another map.
* ``test_a_scene_with_no_marker_answers_none_rather_than_guessing`` - 258 of
  the client's 271 scenes have no authored arrival point, scene 17 among them,
  and None is the table's answer rather than a hole in the reader.
* ``test_the_door_is_closed_and_this_is_the_load_bearing_test`` - scene 14 is
  pinned as data with its login refused, and the docstring carries the three
  measured defects that shut it.  A round that flips the key re-opens all
  three, and this is where it finds that out.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pf_preconditions import BRIDGE_GAMEDATA  # noqa: E402

from pirateforce_foundation import world_scene_entry
from pirateforce_foundation import world_scene_marker
from pirateforce_foundation import world_scene_travel
from pirateforce_foundation.model import Position
from pirateforce_foundation.world_scene_marker import (
    MarkerArrival,
    SceneMarkerError,
    arrival_point,
    console_line,
    scenes_with_an_arrival_point,
)

VOLCANO_SCENE_ID = 14
SEA_SCENE_ID = 17
# The scene-1 row of the same table, kept as a value rather than a lookup so a
# test that reads the module under test cannot agree with itself.
PORT_ROYAL_MARKER = (-10322, -755, 671)
# What this runtime actually stands a fresh character on at home - NOT the
# marker, and the gap is the module's own stated non-corroboration.
V135_HOME_SPAWN = (-9239.95703125, -2830.045166015625, 223.29209899902344)


class MarkerTableTests(unittest.TestCase):

    def test_the_marker_id_is_not_the_scene_id(self):
        scene_130 = arrival_point(130)
        self.assertIsNotNone(scene_130)
        self.assertEqual(scene_130.marker_n_id, 1000)
        self.assertNotEqual(scene_130.marker_n_id, scene_130.scene_n_id)

    def test_every_pinned_marker_points_back_at_the_scene_that_names_it(self):
        for scene_id in scenes_with_an_arrival_point():
            arrival = arrival_point(scene_id)
            self.assertEqual(arrival.marker_row_scene, arrival.scene_n_id)

    def test_no_two_scenes_share_one_marker_row(self):
        marker_ids = [
            arrival_point(scene_id).marker_n_id
            for scene_id in scenes_with_an_arrival_point()
        ]
        self.assertEqual(len(marker_ids), len(set(marker_ids)))

    def test_the_thirteen_scenes_are_the_measured_thirteen(self):
        self.assertEqual(
            scenes_with_an_arrival_point(),
            (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 130),
        )
        self.assertEqual(
            len(scenes_with_an_arrival_point()),
            world_scene_marker.SCENES_WITH_A_MARKER,
        )

    def test_a_scene_with_no_marker_answers_none_rather_than_guessing(self):
        self.assertIsNone(arrival_point(SEA_SCENE_ID))
        self.assertIsNone(arrival_point(278))
        self.assertIsNone(arrival_point(126))

    def test_a_scene_id_that_is_not_an_int_is_refused_not_answered(self):
        for bad in ("14", 14.0, None, True):
            with self.assertRaises(SceneMarkerError):
                arrival_point(bad)

    def test_the_coordinates_are_read_as_signed(self):
        # Read unsigned, scene 1's n_X is 4294956974.  Any future round that
        # drops the two's-complement step gets a point 4.29 billion units out,
        # and this is the row that catches it first.
        self.assertEqual(
            (arrival_point(1).x, arrival_point(1).y, arrival_point(1).z),
            PORT_ROYAL_MARKER,
        )

    def test_home_is_the_non_corroboration_the_module_admits_to(self):
        # If these two ever coincide, the module's docstring is wrong and the
        # claim "one scene agrees exactly and one differs" has to be rewritten
        # rather than quietly kept.
        marker = arrival_point(1)
        self.assertNotEqual(
            (float(marker.x), float(marker.y), float(marker.z)),
            V135_HOME_SPAWN,
        )

    def test_the_console_line_is_ascii_and_names_its_source(self):
        line = console_line(arrival_point(VOLCANO_SCENE_ID))
        self.assertTrue(line.isascii())
        self.assertIn("SCENE_MARKER scene=14 marker=14", line)
        self.assertIn("source=CLIENT_MARKER_TABLE", line)

    def test_the_console_line_refuses_anything_but_an_arrival(self):
        with self.assertRaises(SceneMarkerError):
            console_line((14, 14, 0, 0, 0, 0))

    def test_every_pinned_row_is_pinned_by_value(self):
        # pf-adversary, round vyi2ud, D6: eleven of the thirteen rows had no
        # value coverage at all - x, y, z and direction could be mutated to
        # anything and 124 tests stayed green - and n_DIRTECTION had none.
        # This is the whole table, transcribed a second time, by hand, from
        # the same source.  A one-character slip in either copy goes red.
        self.assertEqual(
            tuple(
                (a.scene_n_id, a.marker_n_id, a.marker_row_scene,
                 a.x, a.y, a.z, a.direction)
                for a in (
                    arrival_point(scene)
                    for scene in scenes_with_an_arrival_point()
                )
            ),
            (
                (1, 1, 1, -10322, -755, 671, 3),
                (2, 2, 2, 26905, 21185, 1680, 8),
                (3, 3, 3, -21215, 16907, -830, 3),
                (4, 4, 4, -19076, 17634, 1440, 6),
                (5, 5, 5, 13025, 23379, -740, 6),
                (6, 6, 6, -9848, 24151, 375, 6),
                (7, 7, 7, -23266, 7709, 5220, 3),
                (8, 8, 8, 19440, 23997, 560, 6),
                (9, 9, 9, 2129, 20907, 240, 6),
                (10, 10, 10, 15740, 25461, 465, 6),
                (11, 11, 11, 15179, 22807, 380, 6),
                (14, 14, 14, -17513, 18989, 1894, 6),
                (130, 1000, 130, -24482, 13364, -990, 1),
            ),
        )

    def test_the_reverification_script_is_ascii_and_self_contained(self):
        script = world_scene_marker.reverification_script()
        self.assertTrue(script.isascii())
        self.assertIn("SCENE_ROWS = 271", script)
        self.assertIn("MARKER_ROWS = 390", script)
        self.assertIn("ID_EQUALS_SCENE = 19", script)

    def test_the_reverification_script_is_not_a_posix_only_command(self):
        # The bridge is a Windows host driven through py -3; the first
        # version of this returned a `python - <<'EOF'` heredoc, which
        # PowerShell cannot run at all (D9).
        script = world_scene_marker.reverification_script()
        # A .py file, not a shell line: no heredoc, no interpreter prefix.
        # ("<<" on its own would match the shift operators the script uses.)
        self.assertNotIn("<<'EOF'", script)
        self.assertNotIn('<<"EOF"', script)
        self.assertFalse(script.lstrip().startswith("python"))
        self.assertIn("assert tuple(derived) == EXPECTED", script)


class TheRulingIsPinnedNotJustWrittenTest(unittest.TestCase):
    """COO-DECISION 20260829_0542, rules 2 and 3, as tests.

    The ruling's own words are that rule 2 is a prohibition rather than a
    preference.  A prohibition that lives only in a docstring is a comment,
    so each of these fails if a later round softens the rule in the module or
    in the registry.
    """

    def test_the_evidence_tier_of_a_marker_point_is_authored_not_observed(self):
        # Rule 3.  If this constant ever reads client-observed, a marker
        # point has been promoted without the attended round that alone
        # grants it (COO-DECISION 20260828_2250, left standing by 0542).
        self.assertEqual(world_scene_marker.EVIDENCE_TIER, "authored")

    def test_the_console_line_carries_the_evidence_tier(self):
        # So a point that reaches an operator's screen is labelled where it
        # is read, not only where it is defined.
        self.assertIn(
            "evidence=authored", console_line(arrival_point(VOLCANO_SCENE_ID))
        )

    def test_the_shortcut_lies_for_scene_130_and_the_module_says_which(self):
        lying = world_scene_marker.forbidden_direct_index_scenes()
        self.assertEqual(sorted(lying), [130])
        self.assertIn("1000", lying[130])

    def test_the_shortcut_invents_a_point_for_257_of_the_258_marker_less_scenes(self):
        # THE size of rule 2's hazard, and the number an earlier draft of
        # this round got wrong by a factor of 36 (pf-adversary, round
        # 8ubiku, D1).  258 scenes have no authored arrival point; 257 of
        # them have a MARKER row sitting at their own scene-id index, so the
        # shortcut answers for almost every scene that must have no answer.
        # Re-derived on the bridge by reverification_script(), not just
        # pinned here.
        self.assertEqual(
            world_scene_marker.SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR,
            257,
        )
        self.assertEqual(world_scene_marker.MARKER_LESS_SCENES, 258)

    def test_three_of_those_survive_this_modules_only_structural_defence(self):
        # Scenes 126, 127 and 128 have n_MARKER = 0 and a same-numbered
        # MARKER row that points back at them, so the back-pointer relation
        # - the one check this module has - does not reject them.  All three
        # are the degenerate origin, which is the tell.
        self.assertEqual(
            world_scene_marker.SHORTCUT_SURVIVES_THE_BACK_POINTER_CHECK,
            (126, 127, 128),
        )

    def test_the_sea_is_the_worked_example_of_why_rule_2_is_a_prohibition(self):
        # Scene 17 has no marker; RE-103 closed bounded-negative on it and an
        # owner decree had to answer it.  The shortcut would have "answered"
        # all along, with scene 126's row.
        self.assertEqual(world_scene_marker.SHORTCUT_AT_SCENE_17,
                         (126, 3050, 232, 90))
        self.assertIsNone(arrival_point(SEA_SCENE_ID))

    def test_the_shortcut_hands_scene_130_prison_exile_islands_row(self):
        # Not merely "another map's row" - MARKER[130] carries n_SCENE 2.
        self.assertEqual(
            world_scene_marker.MARKER_ROW_AT_SCENE_130_BELONGS_TO, 2)
        self.assertIn(130, world_scene_marker.forbidden_direct_index_scenes())

    def test_the_19_minus_12_subtraction_is_kept_as_row_arithmetic_only(self):
        # It is true (7 rows carry n_ID == n_SCENE without being the row
        # their scene named) and it is NOT the hazard: four of those seven
        # row ids are not scene ids at all.  Kept separate so the two can
        # never be quoted as each other again.
        self.assertEqual(
            world_scene_marker.rows_that_look_self_consistent_and_name_nobody(),
            7,
        )
        self.assertNotEqual(
            world_scene_marker.rows_that_look_self_consistent_and_name_nobody(),
            world_scene_marker.SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR,
        )

    def test_the_shortcut_agrees_often_enough_to_look_right(self):
        # ~~Compared two fields of the same pinned tuple, which the loader
        # already guarantees.~~ REWRITTEN after pf-adversary (round 8ubiku,
        # D8) showed it could not go red without a neighbour going red
        # first.  The claim being pinned is a RATIO between two independently
        # sourced numbers: 12 of the 13 marker scenes survive the shortcut,
        # while 257 marker-less scenes do not - which is why the shortcut
        # looks right to whoever introduces it and is wrong for whoever
        # inherits it.  Both sides are re-derived on the bridge.
        agreeing = [
            scene for scene in scenes_with_an_arrival_point()
            if arrival_point(scene).marker_n_id == scene
        ]
        self.assertEqual(len(agreeing), 12)
        self.assertEqual(len(scenes_with_an_arrival_point()), 13)
        self.assertGreater(
            world_scene_marker.SCENES_THE_SHORTCUT_WOULD_INVENT_A_POINT_FOR,
            20 * len(agreeing),
            "the shortcut's damage must stay an order of magnitude larger "
            "than the agreement that makes it tempting; if these ever "
            "converge, rule 2's justification has changed and the text "
            "above it needs rewriting rather than this number relaxing",
        )

    def test_no_public_api_takes_a_marker_id(self):
        # ~~Grepped public callables for the substrings "marker_id" and
        # "by_marker".~~ REWRITTEN: pf-adversary (round 8ubiku, D7) added
        # the exact forbidden read as `marker_row()` / `direct_index()` and
        # the suite stayed green, so the docstring's claim that the read
        # "cannot be spelled through this module at all" was false.  A name
        # filter cannot express a prohibition; an exact surface can.  Adding
        # a public callable here is now a deliberate act that fails this
        # test until someone widens the list on purpose.
        public = sorted(
            name for name in dir(world_scene_marker)
            if not name.startswith("_")
            and callable(getattr(world_scene_marker, name))
        )
        self.assertEqual(public, [
            "Any",
            "MarkerArrival",
            "SceneMarkerError",
            "arrival_point",
            "console_line",
            "dataclass",
            "forbidden_direct_index_scenes",
            "reverification_script",
            "rows_that_look_self_consistent_and_name_nobody",
            "scenes_with_an_arrival_point",
        ])

    def test_the_registry_records_where_every_row_s_coordinate_came_from(self):
        # Rule 3's registry half: every destination says which marker it came
        # from, or says explicitly that it came from something else.  A new
        # destination added without provenance fails here.
        registry = json.loads(
            (ROOT / "scenarios" / "world_scene_registry_001.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertIn("arrival_point_rule", registry)
        for destination in registry["destinations"]:
            with self.subTest(scene=destination["n_id"]):
                provenance = destination["coordinate_provenance"]
                self.assertIn("from_marker", provenance)
                if provenance["from_marker"]:
                    self.assertIsNotNone(provenance["marker_n_id"])
                    pinned = arrival_point(destination["n_id"])
                    self.assertEqual(
                        provenance["marker_n_id"], pinned.marker_n_id
                    )
                else:
                    self.assertIsNone(provenance["marker_n_id"])

    def test_no_marker_sourced_row_claims_to_be_confirmed(self):
        # Rule 3 is a ceiling, enforced across the file boundary.
        # ~~Scene 2 is the deliberate exception and is named rather than
        # excluded silently.~~ It WAS excluded silently: the first version
        # hard-coded `n_id == 2` out of its own loop, so the ceiling test
        # covered exactly one row while the rule text claimed a marker point
        # is never client-observed - false of scene 2 in the same file
        # (pf-adversary, round 8ubiku, D6).  The rule now states its
        # exception, and this test checks the exception is EARNED rather
        # than asserted: the only tier above "authored" is one a client was
        # actually stood on, and the row has to say where that is recorded.
        registry = json.loads(
            (ROOT / "scenarios" / "world_scene_registry_001.json").read_text(
                encoding="utf-8"
            )
        )
        raised = []
        for destination in registry["destinations"]:
            provenance = destination["coordinate_provenance"]
            if not provenance["from_marker"]:
                continue
            with self.subTest(scene=destination["n_id"]):
                self.assertNotIn("confirmed", destination["status"])
                if provenance["evidence_tier"] == "authored":
                    continue
                # Anything above "authored" must cite the pass that earned
                # it, in the row itself.
                self.assertEqual(
                    provenance["evidence_tier"], "client-observed")
                self.assertIn("EXPERIMENT_LEDGER", provenance["note"])
                raised.append(destination["n_id"])
        # Exactly one row has cleared that bar so far, and it is scene 2.
        # A second one appearing without an attended round is the thing this
        # is here to notice.
        self.assertEqual(raised, [2])

    def test_the_rule_text_does_not_contradict_the_rows_beneath_it(self):
        # The specific failure D6 named: prose at the top of the file that a
        # row further down refutes.  If scene 2 is client-observed, the rule
        # may not say a marker point is never client-observed.
        registry = json.loads(
            (ROOT / "scenarios" / "world_scene_registry_001.json").read_text(
                encoding="utf-8"
            )
        )
        rule = registry["arrival_point_rule"]["rule_3_evidence_tier"]
        tiers = {
            d["coordinate_provenance"]["evidence_tier"]
            for d in registry["destinations"]
            if d["coordinate_provenance"]["from_marker"]
        }
        if "client-observed" in tiers:
            self.assertIn("UNLESS", rule)
            self.assertIn("SCENE-001", rule)

    def test_scene_1_home_is_not_the_marker_and_the_carve_out_says_why(self):
        # The trap rule 1 creates, pinned so it cannot be "fixed" quietly:
        # scene 1 HAS a marker, so a literal reading of rule 1 would move the
        # spawn every new character has used since V135.  This lane read the
        # rule as a default for scenes without an arrival point in use, and
        # the registry carries that as a labelled assumption.  If the COO
        # rules the other way, this test is the one that changes.
        registry = json.loads(
            (ROOT / "scenarios" / "world_scene_registry_001.json").read_text(
                encoding="utf-8"
            )
        )
        home = next(d for d in registry["destinations"] if d["n_id"] == 1)
        self.assertFalse(home["coordinate_provenance"]["from_marker"])
        self.assertEqual(
            (home["spawn"]["x"], home["spawn"]["y"], home["spawn"]["z"]),
            V135_HOME_SPAWN,
        )
        self.assertNotEqual(
            (home["spawn"]["x"], home["spawn"]["y"], home["spawn"]["z"]),
            tuple(float(v) for v in PORT_ROYAL_MARKER),
        )
        self.assertIn(
            "AWAITING COO CONFIRMATION",
            registry["arrival_point_rule"][
                "carve_out_scene_1_home_is_not_retro_moved"
            ],
        )


class Scene14RegistryTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.registry = world_scene_travel.load_scene_registry()
        cls.target = world_scene_travel.destination(
            VOLCANO_SCENE_ID, cls.registry)

    def test_the_pinned_spawn_is_the_marker_and_not_a_placement(self):
        self.assertEqual(
            world_scene_travel.spawn_position(self.target),
            arrival_point(VOLCANO_SCENE_ID).xyz,
        )
        self.assertIn("CLIENT_MARKER_TABLE", self.target.spawn_provenance)

    def test_the_scene_has_no_pinned_ground_on_purpose(self):
        # With ground pinned from this scene's 91 placements the box would be
        # 40312 x 46416 units and a Port Royal row would be KEPT - see the
        # registry nonclaim.  None is what makes the relocation below fire.
        self.assertIsNone(self.target.ground_extent)

    def test_the_door_is_closed_and_this_is_the_load_bearing_test(self):
        """Round vyi2ud opened this door and pf-adversary closed it again.

        Measured, driven end to end, with login_entry_allowed true: a
        login into scene 14 through the per-account login-scene override
        (1) shipped 108 bg0001 actors anchored on the volcano, because
        runtime.py's census dispatch reads the STORED row, which the
        override never rewrites and which still says 1; (2) wrote (scene
        1, volcano XYZ) into character_positions, because
        _checkpoint_exact_target reads the same stored id and the persist
        gate is therefore never asked about scene 14 at all - the GT-106
        incident reproduced by the change that cites GT-106; and (3)
        emitted no PLAYER_FACTION line, because the faction-1 compose
        refuses every scene but 2 and Port Royal.

        The pin is kept as DATA - the marker spawn, the table row, the
        native digest - and the entry stays refused until the runtime asks
        about the scene a character is actually in.  A round that flips
        this to True without that fix is re-opening all three.
        """
        self.assertFalse(self.target.login_entry_allowed)
        self.assertFalse(self.target.persist_position_allowed)
        with self.assertRaises(world_scene_entry.SceneEntryRefused):
            world_scene_entry.resolve_entry(
                Position(VOLCANO_SCENE_ID, 0, *V135_HOME_SPAWN, 0.0),
                registry=self.registry,
                emit=lambda line: None,
            )

    def test_a_non_login_caller_still_lands_on_the_marker_and_says_so(self):
        # The door being shut to logins does not make the pin untestable:
        # this is the resolution the runtime would perform the day the
        # stored-row question is answered, driven through the same code.
        lines = []
        entry = world_scene_entry.resolve_entry(
            Position(VOLCANO_SCENE_ID, 0, *V135_HOME_SPAWN, 0.0),
            registry=self.registry,
            emit=lines.append,
            via_login=False,
        )
        self.assertEqual(
            (entry.position.x, entry.position.y, entry.position.z),
            arrival_point(VOLCANO_SCENE_ID).xyz,
        )
        self.assertTrue(entry.relocated)
        self.assertEqual(
            entry.relocation_reason,
            world_scene_entry.RELOCATED_NO_GROUND_EVIDENCE,
        )
        self.assertTrue(any(line.startswith("WORLD_SCENE ") for line in lines))
        self.assertTrue(
            any(line.startswith("WORLD_SCENE_RELOCATED ") for line in lines))
        for line in lines:
            self.assertTrue(line.isascii())
        scene_id, _seq, x, y, z = entry.teleport_fields
        self.assertEqual(scene_id, VOLCANO_SCENE_ID)
        self.assertEqual(
            (x, y, z),
            (entry.position.x, entry.position.y, entry.position.z),
        )

    def test_the_scene_now_reports_the_roster_it_has_had_all_along(self):
        # Before this round the console line read population=none for a scene
        # world_population_bg0015 has composed 81 actors for since round
        # 02k3w5.  This is a report; nothing here sends the roster.
        self.assertEqual(
            world_scene_travel.population_source(VOLCANO_SCENE_ID),
            "bg0015_roster",
        )
        self.assertIn(
            "population=bg0015_roster",
            world_scene_travel.entry_console_line(self.target),
        )

    def test_the_home_census_still_refuses_this_scene(self):
        # The report above must never become a licence: the bg0001 census
        # builder refuses scene 14 whatever any table says.
        from pirateforce_foundation import world_population
        with self.assertRaises(ValueError):
            world_population.build_world_population(
                None, (0.0, 0.0, 0.0), 3, scene_id=VOLCANO_SCENE_ID,
            )


@BRIDGE_GAMEDATA.skip_unless_present()
class MarkerReverificationOnTheBridgeTest(unittest.TestCase):
    """The check that needs the bridge clone's gamedata beside this repo.

    Replaces a test that asserted the pinned sha256 appears in a string built
    from that same constant - a tautology that could not go red for any hash
    value (pf-adversary, round vyi2ud, D6).  This one EXECUTES the script's own
    assertions against the real tables, so the 271 / 390 / 19 / 13 totals and
    all thirteen rows are checked by something rather than merely stated.

    Guarded through pf_preconditions rather than a hand-written skipTest, and
    pinned in docs/PYTEST_SKIP_PINS.json in the same commit: the first draft
    of this file wrote the bare skip, and the Windows gate's skip census
    closed the round's pull request for it - the fourth time this project has
    made that exact mistake, after rounds ctflxc, 2vxlx2 and y7koj9.
    """

    def test_the_reverification_script_runs_against_the_bridge_tree(self):
        script = world_scene_marker.reverification_script()
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "reverify_world_scene_marker.py"
            path.write_text(script, encoding="ascii")
            done = subprocess.run(
                [sys.executable, str(path)],
                cwd=str(ROOT.parent / "pf_bridge"),
                capture_output=True, text=True,
            )
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("13 rows re-derived", done.stdout)


if __name__ == "__main__":
    unittest.main()
