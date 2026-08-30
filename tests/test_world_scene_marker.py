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

from pirateforce_foundation import world_faction_admission
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
        # ~~assertGreater(SCENES_..._FOR, 20 * len(agreeing))~~ REMOVED
        # (pf-adversary, round 8ubiku2, E12): both operands are pinned to
        # exact values by the two assertions above and by a sibling test, so
        # no input could reach this line with it false.  It was not a
        # tautology any more, it was unreachable - and this repo deletes
        # guards that cannot fail rather than shipping them for the comfort
        # of the sentence attached.

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
            # ~~if not provenance["from_marker"]: continue~~ REMOVED
            # (pf-adversary, round 8ubiku2, E2): the ceiling covered only
            # marker-sourced rows, so scene 17 - an invented (0,0,0) owner
            # decree on the scene RE-103 closed bounded-negative - could be
            # relabelled "client-observed" with the suite green.  The tier
            # claim is about whether a client stood on the point; that
            # question does not care where the coordinate came from.
            tier = provenance["evidence_tier"]
            with self.subTest(scene=destination["n_id"]):
                # No row, marker-sourced or not, may call itself confirmed:
                # only an attended round grants that (COO 20260828_2250).
                self.assertNotIn("confirmed", destination["status"])
                if tier != "client-observed":
                    # "authored", "decreed_provisional" and
                    # "chosen_no_evidence" are all AT OR BELOW the ceiling,
                    # so they need no justification here.
                    continue
                # Above "authored" the row must say, in itself, what stood a
                # client on that exact point.
                self.assertTrue(
                    provenance["note"].strip(),
                    "a client-observed tier with no stated observation",
                )
                self.assertRegex(
                    provenance["note"],
                    r"EXPERIMENT_LEDGER|SCENE-001|every default boot|V135",
                    "scene %d claims client-observed without naming the run "
                    "that observed it" % (destination["n_id"],),
                )
                raised.append(destination["n_id"])
        # Two rows have cleared that bar: scene 1 (the spawn every boot
        # stands a character on) and scene 2 (MARKER[2], stood on in
        # SCENE-001).  A third appearing without an attended round is what
        # this is here to notice.
        self.assertEqual(raised, [1, 2])

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
        carve_out = registry["arrival_point_rule"][
            "carve_out_scene_1_home_is_not_retro_moved"
        ]
        # ~~The carve-out carries this lane's pending label.~~  It carried one
        # until COO-DECISION 20260829_0848 answered it; round i8timv struck the
        # label and this assertion moved with it.  Asserting the PENDING label
        # would now be asserting that the question is still open, which would
        # go red the day someone tidies the struck text away - the opposite of
        # what this test is for.
        self.assertIn("~~[LANE-A ASSUMPTION", carve_out)
        self.assertIn("COO-DECISION 20260829_0848", carve_out)
        # The two things the ruling made permanent.  A round that moves home
        # has to delete one of these sentences to make its own change read as
        # consistent, and deleting either one fails here.
        self.assertIn("PERMANENT UNTIL A NEW RULING", carve_out)
        self.assertIn("SPAWN-MOVE", carve_out)

    def test_no_answered_assumption_label_is_still_pending_in_the_registry(self):
        """Every ``AWAITING COO CONFIRMATION`` here must be struck or live.

        The defect this pins is the one round i8timv found: scene 14's spawn
        provenance still carried a label that ``COO-DECISION 20260829_0542``
        had answered two rulings earlier, because the round that struck the
        copy in ``world_scene_marker.py`` never looked for the second copy.
        A pending label is legitimate - a live question SHOULD be labelled -
        so this does not forbid them; it requires that a labelled string names
        the letter that asks, which is what makes the pair findable next time.
        """
        registry_text = (ROOT / "scenarios" / "world_scene_registry_001.json")
        registry = json.loads(registry_text.read_text(encoding="utf-8"))

        def strings(node):
            if isinstance(node, dict):
                for value in node.values():
                    yield from strings(value)
            elif isinstance(node, list):
                for value in node:
                    yield from strings(value)
            elif isinstance(node, str):
                yield node

        for text in strings(registry):
            if "AWAITING COO CONFIRMATION" not in text:
                continue
            struck = "~~[LANE-A ASSUMPTION - AWAITING COO CONFIRMATION]~~" in text
            struck = struck or "~~[LANE-A ASSUMPTION - AWAITING COO" in text
            struck = struck or "~~WITHDRAWN" in text
            with self.subTest(label=text[:60]):
                self.assertTrue(
                    struck or "notes_to_chief/" in text,
                    "a pending assumption label must name the letter that "
                    "asks for it, so the answer can find its way back here",
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

    def test_the_door_is_open_and_all_three_defects_have_a_closure(self):
        """~~test_the_door_is_closed_and_this_is_the_load_bearing_test~~

        THE DOOR IS OPEN AS OF LANE-A ROUND vvy6q7, ON COO-DECISION
        20260829_2342.  The old test's own closing sentence set the terms:
        "a round that flips this to True WITHOUT THAT FIX is re-opening all
        three".  So this test did not become an assertion that the door is
        open -- that would be a snapshot of a boolean.  It asserts the
        CONDITION the old test attached to the flip: each of the three
        defects it named has a closure that is itself checkable here.

        The three, verbatim from the test this replaces, with what closed
        them:

        (1) 108 bg0001 actors anchored on the volcano, because the census
            dispatch read the STORED row.  Closed ON THE FLAGLESS PRODUCTION
            PATH, twice: CHIEF-DECISION 20260829_0520 option A resyncs the
            selected position to the RESOLVED scene, and scene 14 now has a
            census OF ITS OWN (lane_hooks/lane_a_scene_census.py, 81 actors
            from world_population_bg0015).  Driven end to end in
            tests/test_lane_a_scene_census.py on the real registry.
            !! NARROWED AFTER pf-adversary (D1), BECAUSE THE UNQUALIFIED
            WORD "CLOSED" WAS FALSE.  That closure holds only while
            runtime.py's world_census_enabled is True.  On an OPT-IN boot
            (--*-scenario, or --second-password-mode bypass) the lane census
            never fires, the inherited v141:4292 dispatcher stays armed, and
            three bg0001 Port Royal placements ship into this scene with no
            scene test -- defect (1) in reduced form.  Yesterday's shut door
            refused that login outright; today it succeeds, so opening the
            door made that path REACHABLE.  It is an open hazard, guarded
            today only by GT-134's hard precondition, and it is pinned by
            tests/test_world_faction_admission.py::TheOptInBootHazardTests
            rather than left to this docstring.
        (2) (scene 1, volcano XYZ) written into character_positions.
            Closed by runtime.py's login_scene_override_visit branch
            withholding the durable write -- and belt-and-braces, THIS ROW
            STILL PINS persist_position_allowed FALSE, asserted below.  This
            round flipped one boolean, not two.
        (3) no PLAYER_FACTION line, because the faction-1 compose refused
            every scene but 2 and Port Royal.  Closed by this same commit:
            world_faction_admission admits scene 14 now, asserted below
            against the module rather than quoted from this docstring.
        """
        self.assertTrue(self.target.login_entry_allowed)
        # (2): the second boolean did NOT move, and a round that moves it is
        # a different round with a different ruling behind it.
        self.assertFalse(self.target.persist_position_allowed)
        # (3): the defect that was open when the old test was written.
        self.assertTrue(
            world_faction_admission.admits(VOLCANO_SCENE_ID, self.registry))
        # ...and it is admitted for the two REASONS the COO wrote down,
        # not because the module holds a literal 14 somewhere.
        self.assertEqual(self.target.save_flag, 1)
        self.assertIn(
            "open_at_login_and_n_save_1",
            world_faction_admission.refusal_reason(
                VOLCANO_SCENE_ID, self.registry),
        )
        # The login the old test asserted was refused now resolves.
        entry = world_scene_entry.resolve_entry(
            Position(VOLCANO_SCENE_ID, 0, *V135_HOME_SPAWN, 0.0),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(entry.position.scene_id, VOLCANO_SCENE_ID)

    def test_the_other_ten_marker_doors_did_not_open_with_it(self):
        """The blast radius of round vvy6q7, asserted rather than promised.

        Ten marker scenes were addressed in round ga91m5 and every one of
        them stayed shut.  Opening scene 14 was one ruling about one scene;
        if this ever goes red, a door opened without one.

        UPDATED round bq4mst: scene 4 left this set the same way scene 14
        left it here -- its OWN census composer was judged ready
        (COO-DECISION 20260830_1441) and its door opened.  See
        ``test_scene_4_opened_separately_and_that_is_a_different_round``
        below for the assertion that replaces it, so a reader of THIS test
        does not have to infer why the tuple below shrank by one.
        """
        for scene_id in (3, 5, 6, 7, 8, 9, 10, 11, 130):
            with self.subTest(scene_id=scene_id):
                target = world_scene_travel.destination(
                    scene_id, self.registry)
                self.assertFalse(target.login_entry_allowed)
                self.assertFalse(
                    world_faction_admission.admits(scene_id, self.registry))

    def test_scene_4_opened_separately_and_that_is_a_different_round(self):
        """ADDED round bq4mst: the one scene removed from the tuple above.

        Not this round's ruling (COO-DECISION 20260830_1441, LANE-A round
        bq4mst) -- named here so this file's own blast-radius claim for
        scene 14 stays accurate rather than silently wrong about a scene
        this file does not otherwise mention.
        """
        target = world_scene_travel.destination(4, self.registry)
        self.assertTrue(target.login_entry_allowed)
        self.assertTrue(world_faction_admission.admits(4, self.registry))

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


class TheCopyBindingSurvivesLosingItsOwnTestFileTest(unittest.TestCase):
    """A second, independent copy of the guarantee round ``i8timv`` added.

    pf-adversary deleted ``tests/test_world_marker_copy.py`` outright and the
    suite went green with a forged coordinate in ``_ROWS`` (round ``i8timv``,
    D2a): nothing anywhere pinned that the file exists, and the skip census
    only notices modules that SKIP, never modules that vanish.  So the binding
    is asserted here too, in a file with its own reasons to exist, and this
    class also fails if the other file goes missing.

    Two files can still both be deleted.  The point is not that it is
    impossible - it is that it stops being a one-line change that reads like
    tidying, and starts being the deletion of a test file that this module's
    own docstring names.
    """

    def test_the_pinned_rows_re_derive_from_the_committed_copy(self):
        from pirateforce_foundation import world_marker_copy

        self.assertEqual(world_marker_copy.derive_rows(),
                         world_scene_marker._ROWS)

    def test_the_dedicated_test_file_is_still_in_the_tree(self):
        companion = ROOT / "tests" / "test_world_marker_copy.py"
        self.assertTrue(
            companion.is_file(),
            "tests/test_world_marker_copy.py is the gate-side half of "
            "COO-DECISION 20260829_0941 and may not be deleted",
        )
        self.assertIn(
            "def test_every_pinned_row_re_derives_from_the_copy",
            companion.read_text(encoding="utf-8"),
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

    def test_the_committed_copy_is_what_the_client_tables_produce(self):
        """The one hop the gate cannot make: copy vs the client's own bytes.

        Added in round ``i8timv`` INSIDE this already-pinned class rather than
        as a new skipping class, because a second
        ``@BRIDGE_GAMEDATA.skip_unless_present()`` class would move the
        ``bridge_gamedata`` count in ``docs/PYTEST_SKIP_PINS.json`` and the
        skip census goes red in either direction.  Same precondition, same
        pin, one more assertion under it.
        """
        from pirateforce_foundation import world_marker_copy

        world_marker_copy.verify_against_sources(
            ROOT.parent / "pf_bridge" / "gamedata" / "tables"
        )


if __name__ == "__main__":
    unittest.main()
