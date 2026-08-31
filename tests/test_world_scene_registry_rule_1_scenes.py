"""The ten scenes rule 1 addressed in round ga91m5, and the door it did NOT open.

WHAT THIS FILE IS FOR.  ``COO-DECISION 20260829_0542`` made one rule standing:
a scene whose ``SCENE_NAME[n].n_MARKER`` is non-zero takes ``MARKER[n_MARKER]``
as its arrival point, with no per-scene ruling asked for.  Round 8ubiku put the
rule's text on main under the COO's own hold ("do not apply this rule to any
further scene before the rule text lands on main").  This round spent it on the
ten scenes that qualified and were not already pinned: 3, 4, 5, 6, 7, 8, 9, 10,
11 and 130.

WHAT THE TEN ARE, AND THE WORD THAT MATTERS.  They are ADDRESSES, not doors.
Every one carries ``login_entry_allowed: false``, so the login path refuses
them and the GM ``/warp`` stageable set is unchanged.  The round intended to
leave them open, wrote a safety case, and ``pf-adversary`` refuted both of its
legs before the commit:

* the inherited ``V134_P0_P30_P91`` dispatcher
  (``current/pf_login_game_server_v141.py:4292``) is only disarmed when
  ``runtime.py``'s ``world_census_enabled`` is true, and on any other boot it
  composes three ``scene_id=1`` Port Royal actors into whatever scene the
  player is standing in, with no scene test at all -- so "these ten have no
  population" was an inventory of ``world_population*`` modules standing in
  for a gate, and there is no gate;
* ``gm/login_scene_consume.py``'s STANDALONE map grants a login scene with no
  ``gm_accounts.json`` membership and is never consumed -- so "GM-only, and
  single-use" was false of that path.

So these tests check what the round can actually stand behind: that the ten are
exactly the scenes the client's table qualifies, that each stands on its own
marker's point, and that the door is shut.

GATE-WALK DECLARATION (``COO-DECISION 20260829_0742``, rule for every test
written from this round on -- state in the file which branches are walked, and
which are not walked because a gate is shut).

WALKED, THROUGH THE PRODUCTION CALL SHAPE:

* ``world_scene_entry.resolve_entry(stored, registry=...)`` for all ten,
  called exactly as ``runtime.py``'s ``START_GAME_REQ`` path calls it:
  positional stored row, ``registry`` from a load done once, ``emit`` and
  ``via_login`` left on their defaults.  ``via_login`` in particular is NOT
  passed: the production login path does not pass it, and a test that passed
  ``via_login=False`` would walk a branch only
  ``columbus_quest_dispatch.resolve_columbus_arrival`` walks and would report
  coverage the login path does not have.  That call is asserted to REFUSE.
* ``gm/login_scene_stage.login_entry_is_pinned`` and ``stageable_scene_ids``,
  the real predicates the ``/warp`` writer asks, for all ten.
* ``world_scene_travel.load_scene_registry()`` at its real path, with the real
  file -- every relation the loader enforces on the ten rows is walked by
  loading them, not by a fixture that restates them.

NOT WALKED, AND WHY -- these are gates that are shut, not coverage this file
claims:

* No frame for any of the ten ever goes on a wire here, and no arrival is
  composed for one.  ``via_login=False`` is deliberately never exercised for
  these scenes: no caller in this tree passes it for them, so a test that did
  would be walking a branch that does not exist in production.
* The inherited v141 population branch is NOT driven here.  It is the defect
  that shut these doors, it lives in a file frozen by enforcement
  (``COO-DECISION 20260829_0345``), and this lane may not gate it.  ACCEPTED
  IS NOT REACHED (rule 3 of GATE-WALK): nothing in this file counts that
  branch as covered by having reasoned about it in a docstring.
* ``runtime.py``'s census dispatch and its override-visit branch are chief's
  branches with chief's tests
  (``tests/test_gm_login_scene_override_position_resync.py``).
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_marker  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import login_scene_stage  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

# The ten this round added.  Written out rather than derived, so that a future
# round which drops one silently has to edit this line and say so.  Used for
# the ADDRESS-only properties below (geometry, marker source, deviation flag)
# that do not depend on the door -- those are true of all ten regardless of
# login_entry_allowed.
RULE_1_SCENES_ADDED_THIS_ROUND = (3, 4, 5, 6, 7, 8, 9, 10, 11, 130)

# ADDED round bq4mst (LANE-A): of the ten above, scene 4 (Slave Market
# Island) opened this round (COO-DECISION 20260830_1441 + this round's own
# safety case on the registry row).  UPDATED round 3t75jw: scene 10 (Deep
# Sea Temple floor 1) opened second, same basis.  UPDATED round l03cgh:
# scene 5 (Evil Port) opened third, same basis, built+wired+opened in one
# round instead of three (see that round's own login_entry_allowed_because
# on the registry row for why).  UPDATED round fx0007: scene 6 (Ocean
# Walled City) opened fourth, same basis, same compressed shape.  UPDATED
# round p4wire: scene 8 (Silver Harbour) opened fifth, same basis, same
# compressed shape.  UPDATED round p7wm17: scene 3 (Spice Paradise Island)
# opened sixth, same basis, same compressed shape.  UPDATED round 78zayw:
# scene 7 (Voodoo Island) opened seventh, same basis, same compressed
# shape.  UPDATED round ir0lpw: scene 9 (Death City Sea) opened eighth,
# same basis, same compressed shape.  UPDATED round 68mm02: scene 11 (Deep
# Sea Temple floor 2) opened ninth, same basis, same compressed shape --
# the elevated-risk row (the_two_interiors, shared only with scene 10).
# UPDATED this round (yfbqmg): scene 130 (Navy Training Camp) opened
# TENTH AND LAST, same basis, same compressed shape, NOT an elevated-risk
# row.  RULE_1_SCENES_STILL_SHUT is now EMPTY -- every one of the ten
# doors this file names is open at login.  Kept as a tuple (not deleted)
# so every loop below that iterates it still runs, vacuously, rather than
# needing to be rewritten scene-by-scene one more time.
RULE_1_SCENES_STILL_SHUT = tuple(
    n_id for n_id in RULE_1_SCENES_ADDED_THIS_ROUND
    if n_id not in (3, 4, 5, 6, 7, 8, 9, 10, 11, 130))

# The three marker scenes that were already pinned, each by its own ruling.
MARKER_SCENES_ALREADY_PINNED = (1, 2, 14)

# The one of the three that declines its marker, under a declared deviation.
SCENE_THAT_DEVIATES_FROM_RULE_1 = 1

# Measured this round against each scene's own native placements.  Four of the
# ten marker points fall INSIDE their scene's placement extents and six fall
# outside; the split decides nothing at load time and is pinned because the
# ground-block reasoning in the registry cites it.
MARKER_POINT_INSIDE_PLACEMENT_BOUNDS = (7, 8, 9, 11)


def _raw_rows() -> dict[int, dict]:
    data = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    return {row["n_id"]: row for row in data["destinations"]}


class TheTenAreExactlyWhatTheClientTableQualifies(unittest.TestCase):
    """The set, not the members: a hand-picked ten would pass a per-row test."""

    def test_the_ten_are_every_marker_scene_that_was_not_already_pinned(self):
        # world_scene_marker's crosswalk is the client's table, transcribed and
        # self-checked there; this derives the expected set FROM it rather than
        # from the registry the set is supposed to be checking.
        qualified = set(world_scene_marker.scenes_with_an_arrival_point())
        self.assertEqual(len(qualified), world_scene_marker.SCENES_WITH_A_MARKER)
        expected = qualified - set(MARKER_SCENES_ALREADY_PINNED)
        self.assertEqual(expected, set(RULE_1_SCENES_ADDED_THIS_ROUND))

    def test_no_scene_was_added_that_the_rule_does_not_reach(self):
        rows = _raw_rows()
        for n_id in RULE_1_SCENES_ADDED_THIS_ROUND:
            with self.subTest(scene=n_id):
                self.assertNotEqual(rows[n_id]["table_row"]["n_MARKER"], 0)


class EachOfTheTenStandsOnItsOwnMarkersPoint(unittest.TestCase):
    """The loader already enforces this; these say what it enforces, out loud.

    Not a tautology check: the assertions here read the marker crosswalk
    directly and compare against the registry's own JSON, so a commit that
    edited the coordinate and the provenance field together -- which the
    loader's cross-check is specifically built to catch -- fails here too, from
    the other side.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()
        cls.rows = _raw_rows()

    def test_every_new_row_uses_the_marker_its_own_table_row_names(self):
        for n_id in RULE_1_SCENES_ADDED_THIS_ROUND:
            with self.subTest(scene=n_id):
                row = self.rows[n_id]
                arrival = world_scene_marker.arrival_point(n_id)
                self.assertIsNotNone(arrival)
                self.assertEqual(
                    row["coordinate_provenance"]["marker_n_id"],
                    arrival.marker_n_id)
                self.assertEqual(
                    row["table_row"]["n_MARKER"], arrival.marker_n_id)
                spawn = world_scene_travel.destination(n_id, self.registry).spawn
                self.assertEqual(spawn, arrival.xyz)

    def test_scene_130_is_the_row_that_makes_rule_2_load_bearing(self):
        # The whole reason the ruling forbids indexing MARKER by a scene id.
        # If this ever equals 130, the indirection stopped mattering and
        # somebody should find out why before relaxing anything.
        arrival = world_scene_marker.arrival_point(130)
        self.assertEqual(arrival.marker_n_id, 1000)
        self.assertNotEqual(arrival.marker_n_id, 130)

    def test_every_new_row_is_authored_and_claims_no_more(self):
        for n_id in RULE_1_SCENES_ADDED_THIS_ROUND:
            with self.subTest(scene=n_id):
                provenance = self.rows[n_id]["coordinate_provenance"]
                self.assertEqual(provenance["evidence_tier"], "authored")
                self.assertEqual(
                    provenance["evidence_tier"],
                    world_scene_marker.EVIDENCE_TIER)
                self.assertIs(provenance["from_marker"], True)
                self.assertIs(provenance["deviates_from_rule_1"], False)

    def test_the_ten_carry_no_ground_block(self):
        # TWO REASONS, AND THEY APPLY TO DIFFERENT ROWS - keeping them apart is
        # pf-adversary's finding (round ga91m5, D6), because an earlier draft
        # gave all ten the six-of-ten reason.
        #
        # For the SIX whose marker point is outside their scene's placement
        # extents, a ground block would make _spawn()'s bound check refuse the
        # row outright, so adding one would break the load.
        #
        # For the FOUR inside (7, 8, 9, 11) the registry WOULD still load with
        # a ground block, and the reason is the one scene 278's and scene 17's
        # own ground blocks already state in their `limit` field: a .npc file
        # carries NPC placements, not terrain, so bounding an authored
        # player-arrival point by where the developers put monsters would
        # invent a constraint the client's data does not assert.
        for n_id in RULE_1_SCENES_ADDED_THIS_ROUND:
            with self.subTest(scene=n_id):
                self.assertIsNone(self.rows[n_id]["ground"])

    def test_the_inside_outside_split_the_ground_reasoning_cites(self):
        # The registry's why_the_ten_carry_no_ground_block quotes this split.
        # Pinned from the rows' own measured field so the prose and the data
        # cannot drift apart silently.
        inside = tuple(sorted(
            n_id for n_id in RULE_1_SCENES_ADDED_THIS_ROUND
            if self.rows[n_id]["table_row_differences"]
            ["marker_geometry_measured_not_enforced"]
            ["marker_point_inside_placement_bounds"]
        ))
        self.assertEqual(inside, MARKER_POINT_INSIDE_PLACEMENT_BOUNDS)

    def test_scene_1_is_still_the_only_declared_deviation(self):
        deviating = [
            n_id for n_id, row in self.rows.items()
            if row["coordinate_provenance"]["deviates_from_rule_1"]
        ]
        self.assertEqual(deviating, [SCENE_THAT_DEVIATES_FROM_RULE_1])


class TheDoorIsShutAndThisIsTheLoadBearingTest(unittest.TestCase):
    """Ten addresses, zero doors.  If this file has one test, it is this one.

    Same shape, and for a related reason, as scene 14's
    ``test_the_door_is_closed_and_this_is_the_load_bearing_test`` in
    ``tests/test_world_scene_travel.py``.  Scene 14's door is shut because
    defect D3 (``player_wire``'s faction-1 serializer refusing every scene
    outside ``(1, 2)``) is open and it has 81 composed actors for that to
    matter to.  These ten are shut for a wider reason: there is no gate that
    every actor-composing path passes before a frame is sent into scene N.
    ``world_population``, ``world_population_bg0002``,
    ``world_population_bg0015``, ``field_mobs.load_roster`` and the inherited
    v141 ``make_v112_monster_shop_population_state`` each decide for
    themselves, and the last of those decides nothing at all -- it composes
    ``scene_id=1`` actors whatever scene the player is in.

    AN EARLIER DRAFT OF THIS FILE TESTED THE OPPOSITE, and the way it failed
    is worth more than the tests it is replaced by.  It asserted that no
    ``world_population*`` module names one of the ten, and claimed in its own
    docstring that this "goes red the day" one does.  pf-adversary defeated it
    twice in three lines each: once with a ``field_mob_tables_bg0003.py``
    naming its scene as the string ``'Bg0003'`` (a module shape the glob never
    looked at), and once with a ``world_population_bg0003.py`` exposing
    ``SCENE``, ``SCENES`` and a default argument instead of ``SCENE_ID`` (an
    attribute shape the filter never matched).  Both stayed green.  An
    inventory of the composers somebody thought of is not a gate, and no test
    of this shape can be made complete -- so the claim is withdrawn rather
    than patched, and the door is shut instead.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = world_scene_travel.load_scene_registry()

    def _stored_row(self, scene_id: int) -> Position:
        # The shape a persisted row actually has at a login: seq 0, and a
        # coordinate that is NOT the destination's spawn, because a stored row
        # never carries the arrival point of a scene it has not been to.
        return Position(scene_id, 0, 0.0, 0.0, 0.0, 0)

    def test_the_login_path_refuses_every_one_of_the_ten(self):
        # ADDED round bq4mst: iterates RULE_1_SCENES_STILL_SHUT, not the
        # original ten -- scene 4 opened this round and has its own test
        # below (``test_the_one_scene_that_opened_is_no_longer_in_this_set``)
        # asserting the opposite fact, same reasoning as scene 14's own file.
        for n_id in RULE_1_SCENES_STILL_SHUT:
            with self.subTest(scene=n_id):
                with self.assertRaises(
                    world_scene_entry.SceneEntryRefused
                ) as caught:
                    world_scene_entry.resolve_entry(
                        self._stored_row(n_id),
                        registry=self.registry,
                        emit=lambda line: None,
                    )
                self.assertEqual(
                    caught.exception.reason,
                    world_scene_entry.REFUSED_NOT_ALLOWED_AT_LOGIN)

    def test_the_registry_says_so_in_the_field_that_carries_it(self):
        rows = _raw_rows()
        for n_id in RULE_1_SCENES_STILL_SHUT:
            with self.subTest(scene=n_id):
                self.assertIs(rows[n_id]["login_entry_allowed"], False)
                self.assertIs(
                    world_scene_travel.destination(
                        n_id, self.registry).login_entry_allowed,
                    False)

    def test_the_gm_warp_writer_still_refuses_all_ten(self):
        # The predicate the /warp writer actually asks, not a copy of it.
        # "all ten" in this method's name is the nine still shut plus the
        # method below that drives scene 4 through the same predicate and
        # gets the opposite answer -- kept together rather than renamed, so
        # a reader scanning method names sees both halves of the same pair.
        for n_id in RULE_1_SCENES_STILL_SHUT:
            with self.subTest(scene=n_id):
                self.assertFalse(login_scene_stage.login_entry_is_pinned(n_id))

    def test_the_stageable_set_did_not_grow_by_a_single_scene(self):
        # "did not grow" is now true of the nine still shut, not the ten --
        # see the docstring on RULE_1_SCENES_STILL_SHUT for why.
        stageable = set(login_scene_stage.stageable_scene_ids())
        self.assertEqual(
            stageable & set(RULE_1_SCENES_STILL_SHUT), set())

    def test_the_one_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 4's own half of the pair, ADDED round bq4mst.

        Same predicates as the four tests above, driven at scene 4, asserting
        the opposite of what they assert for the other nine -- the shape
        ``tests/test_lane_a_scene_census.py::SlaveMarketRegistrationTests``
        already proves at the census-composer layer; this is the admission
        layer this file otherwise owns for all ten.
        """
        self.assertNotIn(4, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[4]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                4, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(4))
        self.assertIn(4, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(4),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 4)
        self.assertEqual(result.position.scene_id, 4)

    def test_the_second_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 10's own half of the pair, ADDED round 3t75jw.

        Same shape as ``test_the_one_scene_that_opened_is_no_longer_in_
        this_set`` above, driven at scene 10 (Deep Sea Temple floor 1),
        the second of the ten doors this lane has opened.  The elevated
        landing-geometry flag on this row (``the_two_interiors``) is not
        this file's concern -- this file owns the admission layer, not
        the landing point, and GT-166 is where that risk is tracked.
        """
        self.assertNotIn(10, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[10]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                10, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(10))
        self.assertIn(10, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(10),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 10)
        self.assertEqual(result.position.scene_id, 10)

    def test_the_third_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 5's own half of the pair, ADDED round l03cgh.

        Same shape as the two tests above, driven at scene 5 (Evil Port),
        the third of the ten doors this lane has opened -- built, wired and
        opened in one round rather than three.  Unlike scene 10, this row
        does NOT carry the elevated ``the_two_interiors`` landing-geometry
        flag (checked, not assumed, in the module that built it).
        """
        self.assertNotIn(5, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[5]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                5, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(5))
        self.assertIn(5, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(5),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 5)
        self.assertEqual(result.position.scene_id, 5)

    def test_the_fourth_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 6's own half of the pair, ADDED round fx0007.

        Same shape as the three tests above, driven at scene 6 (Ocean
        Walled City), the fourth of the ten doors this lane has opened --
        built, wired and opened in one round, same compressed shape as
        scene 5's.  This row does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it).
        """
        self.assertNotIn(6, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[6]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                6, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(6))
        self.assertIn(6, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(6),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 6)
        self.assertEqual(result.position.scene_id, 6)

    def test_the_fifth_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 8's own half of the pair, ADDED round p4wire.

        Same shape as the four tests above, driven at scene 8 (Silver
        Harbour), the fifth of the ten doors this lane has opened -- built,
        wired and opened in one round, same compressed shape as scenes 5's
        and 6's.  This row does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it), and its marker point is the
        tightest-fitting of any door opened so far (8.8 units from the
        nearest native placement, inside the placement extents).
        """
        self.assertNotIn(8, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[8]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                8, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(8))
        self.assertIn(8, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(8),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 8)
        self.assertEqual(result.position.scene_id, 8)

    def test_the_sixth_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 3's own half of the pair, ADDED round p7wm17.

        Same shape as the five tests above, driven at scene 3 (Spice
        Paradise Island), the sixth of the ten doors this lane has opened
        -- built, wired and opened in one round, same compressed shape as
        scenes 5's, 6's and 8's.  This row does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it).
        """
        self.assertNotIn(3, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[3]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                3, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(3))
        self.assertIn(3, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(3),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 3)
        self.assertEqual(result.position.scene_id, 3)

    def test_the_seventh_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 7's own half of the pair, ADDED this round (78zayw).

        Same shape as the six tests above, driven at scene 7 (Voodoo
        Island), the seventh of the ten doors this lane has opened -- built,
        wired and opened in one round, same compressed shape as scenes 5's,
        6's, 8's and 3's.  This row does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it).
        """
        self.assertNotIn(7, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[7]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                7, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(7))
        self.assertIn(7, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(7),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 7)
        self.assertEqual(result.position.scene_id, 7)

    def test_the_eighth_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 9's own half of the pair, ADDED this round (ir0lpw).

        Same shape as the seven tests above, driven at scene 9 (Death City
        Sea), the eighth of the ten doors this lane has opened -- built,
        wired and opened in one round, same compressed shape as scenes
        5's, 6's, 8's, 3's and 7's.  This row does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it), and its marker point IS inside its
        own placement extents (see MARKER_POINT_INSIDE_PLACEMENT_BOUNDS
        above -- an address-only geometry fact, unaffected by the door).
        """
        self.assertNotIn(9, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[9]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                9, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(9))
        self.assertIn(9, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(9),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 9)
        self.assertEqual(result.position.scene_id, 9)

    def test_the_ninth_scene_that_opened_is_no_longer_in_this_set(self):
        """Scene 11's own half of the pair, ADDED this round (68mm02).

        Same shape as the eight tests above, driven at scene 11 (Deep Sea
        Temple floor 2), the ninth of the ten doors this lane has opened --
        built, wired and opened in one round, same compressed shape as
        scenes 5's, 6's, 8's, 3's, 7's and 9's.  UNLIKE those, this row
        DOES carry the elevated ``the_two_interiors`` landing-geometry
        flag (checked, not assumed, in the module that built it), shared
        only with scene 10, already open on ``COO-DECISION
        20260831T10:42+07:00``'s own precedent.
        """
        self.assertNotIn(11, RULE_1_SCENES_STILL_SHUT)
        rows = _raw_rows()
        self.assertIs(rows[11]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                11, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(11))
        self.assertIn(11, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(11),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 11)
        self.assertEqual(result.position.scene_id, 11)

    def test_the_tenth_and_last_scene_that_opened_is_no_longer_in_this_set(
        self,
    ):
        """Scene 130's own half of the pair, ADDED this round (yfbqmg).

        Same shape as the nine tests above, driven at scene 130 (Navy
        Training Camp), the TENTH AND LAST of the ten doors this lane has
        opened -- built, wired and opened in one round, same compressed
        shape as scenes 5's, 6's, 8's, 3's, 7's, 9's and 11's.  UNLIKE
        scene 11's row, this one does NOT carry the elevated
        ``the_two_interiors`` landing-geometry flag (checked, not assumed,
        in the module that built it: n_CANGLIDE 1, n_LIMIT_HEIGHT 0, not
        the (0, 0) pair that flag names).  With this test green,
        ``RULE_1_SCENES_STILL_SHUT`` is empty and every one of the ten
        doors round ``12lyda`` surveyed is open at login.
        """
        self.assertNotIn(130, RULE_1_SCENES_STILL_SHUT)
        self.assertEqual(RULE_1_SCENES_STILL_SHUT, ())
        rows = _raw_rows()
        self.assertIs(rows[130]["login_entry_allowed"], True)
        self.assertIs(
            world_scene_travel.destination(
                130, self.registry).login_entry_allowed,
            True)
        self.assertTrue(login_scene_stage.login_entry_is_pinned(130))
        self.assertIn(130, login_scene_stage.stageable_scene_ids())
        result = world_scene_entry.resolve_entry(
            self._stored_row(130),
            registry=self.registry,
            emit=lambda line: None,
        )
        self.assertEqual(result.destination.n_id, 130)
        self.assertEqual(result.position.scene_id, 130)

    def test_a_scene_with_no_marker_and_no_ruling_is_refused_differently(self):
        # The control: rule 1 reached the marker scenes and NOTHING else, and
        # the two refusals are distinguishable.
        #
        # THIS USED TO NAME SCENE 126, AND ITS OWN COMMENT PREDICTED WHY IT
        # STOPPED BEING A VALID CONTROL: "it is the id most likely to be
        # reached for next."  LANE-A round 2026-08-30 pinned scene 126 (per
        # CHIEF-DECISION R229 - see test_world_scene_travel.py's
        # ``test_scene_126_is_a_diagnostic_pin_not_a_destination``), so it
        # now HAS a ruling behind it even though it still has no
        # self-referencing marker - it is neither this test's case (no
        # marker, no ruling) nor the rule-1 case (marker, no ruling needed)
        # above.  Scene 18 (Bg1002, the next sea-family ship scene after 17)
        # replaces it: same n_MARKER=0 shape, still genuinely unpinned.
        with self.assertRaises(world_scene_entry.SceneEntryRefused) as caught:
            world_scene_entry.resolve_entry(
                self._stored_row(18),
                registry=self.registry,
                emit=lambda line: None,
            )
        self.assertEqual(
            caught.exception.reason, world_scene_entry.REFUSED_SCENE_NOT_PINNED)


if __name__ == "__main__":
    unittest.main()
