"""LANE-A's own scene census composers, and the gate that keeps them shut.

WHAT THIS FILE PROVES.  ``lane_hooks/lane_a_scene_census.py`` is the first
time this lane has wired itself to a player without a chief round in between:
chief built the per-scene composer point in round ``73fhoc`` and this lane
registered scene 14's composer against it.  These tests drive that composer on
the REAL dispatcher, not against a double.

THE GATE, AND WHY THESE TESTS DRIVE IT INSTEAD OF READING IT BACK.  An earlier
version of this file asserted that scene 14's registry row says
``login_entry_allowed: false`` and called that "the door is shut".
pf-adversary refuted it: ``world_scene_entry.resolve_entry`` refuses scene 14
only on its ``via_login=True`` path, and a ``via_login=False`` call site - the
thing LANE-GM's ``CORE-REQUEST-GM-038`` is currently asking chief for, for a
different scene - reaches it with the registry key untouched.  Simulated, and
81 actors shipped to a player while that assertion stayed green.  A test that
watches a proxy for the property instead of the property is the scar this
project has paid for more than once.

So the module now carries an ADMISSION CHECK - it declines for any scene the
registry does not declare open - and these tests drive the refusal:
``TheAdmissionCheckIsTheGateTests`` calls the composer directly, through the
factory, and through a ``via_login=False`` resolution, and gets ``None`` every
time.  The registry boolean is asserted too, but as a second-order fact and
never on its own.

GATE-WALK DECLARATION (``COO-DECISION 20260829_0742``).

WALKED, THROUGH THE PRODUCTION CALL SHAPE:

* The composer invoked the way ``runtime.py``'s lane branch invokes it -
  keyword-only ``legacy``, ``anchor``, ``scene_id``, ``scene_entry_registry``
  - and once by that branch itself, through a full dispatcher boot, login,
  ``START_GAME`` and a first ``TargetPosVital``.
* ``lane_hooks.census_composer`` registration as ``_discover()`` performs it
  at import: the registry is read after a real import of the real module.
* The admission check's refusal path, which is the LIVE production path for
  scene 14 today - not a hypothetical branch.
* The strict-entry-point choice, driven by making the seam raise and checking
  the exception reaches the caller instead of becoming a decline.

NOT WALKED, AND WHY - gates that are shut, not coverage this file claims:

* No frame reaches a client here, and no claim is made that a client renders
  81 actors on the volcano.  That is ``GT-134``, attended, still BLOCKED.
* ~~The faction-1 path (defect D3) is NOT exercised: ``player_wire`` refuses
  every scene outside ``(1, 2)``, so no ``PLAYER_FACTION`` frame exists for
  scene 14 to test.~~ D3 WAS CLOSED IN ROUND vvy6q7 and the frame now exists;
  ``tests/test_world_faction_admission.py`` owns that proof, and this file
  still does not exercise it.  ACCEPTED IS STILL NOT REACHED: nothing here,
  and nothing there, treats a census firing or a faction field reaching the
  wire as evidence that a hostile will READ as hostile.  That is ``GT-134``,
  attended, on a screen.
* !! THE OPT-IN BOOT IS NOT WALKED HERE, AND IT IS NOW A REACHABLE HAZARD
  RATHER THAN AN UNREACHABLE ONE.  Every boot in this file has
  ``world_census_enabled`` True.  On a ``--*-scenario`` or
  ``--second-password-mode bypass`` boot the lane census never fires AND the
  inherited ``v141:4292`` dispatcher stays armed, so three bg0001 Port Royal
  placements ship into scene 14 with no scene test.  Until round vvy6q7 the
  shut door refused that login and the path could not be reached; opening
  the door reached it.  pf-adversary measured it (D1) and it is pinned in
  ``tests/test_world_faction_admission.py::TheOptInBootHazardTests``.  This
  bullet exists because the omission itself was a finding: the list below
  did not name it, which is how a gate-walk declaration turns into a
  formality.
* Scene 2's composer is not registered and not driven - the runtime keeps
  that branch and ``tests/test_lane_scene_census_wiring.py`` owns that proof.
* The call site's own decline latch is chief's branch, proven with a stub in
  chief's file.  This file proves what the composer returns, not what the
  runtime does with it.
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import world_population_bg0004  # noqa: E402
from pirateforce_foundation import world_population_bg0005  # noqa: E402
from pirateforce_foundation import world_population_bg0006  # noqa: E402
from pirateforce_foundation import world_population_bg0010  # noqa: E402
from pirateforce_foundation import world_population_bg0015  # noqa: E402
from pirateforce_foundation import world_population_handoff  # noqa: E402
from pirateforce_foundation import world_scene_entry  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_a_scene_census as lane_a,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
VOLCANO = 14
ROSTER_COUNT = 81
# ADDED round 2jdde8 (LANE-A): bg0004's own scene id and roster size, wired
# this round into the same two tables VOLCANO uses.  Unlike VOLCANO the real
# registry row stays SHUT (COO-DECISION 2026-08-30T14:41+07:00) -- see
# ``SlaveMarketRegistrationTests`` below for the test that pins that fact.
# ADDED round bq4mst (LANE-A): the real registry row flipped OPEN
# (COO-DECISION 20260830_1441's own instruction: build first, then judge
# readiness, then flip). ~~Unlike VOLCANO the real registry row stays
# SHUT (COO-DECISION 2026-08-30T14:41+07:00)~~ -- struck, not deleted, per
# this project's history rule: it was true for two rounds (6p22bu, 2jdde8).
SLAVE_MARKET = 4
SLAVE_MARKET_ROSTER_COUNT = 109
# ADDED round c42axq (LANE-A): bg0010's own scene id and roster size, wired
# this round into the same two tables VOLCANO/SLAVE_MARKET use.  Same shape
# as SLAVE_MARKET at round 2jdde8 -- the real registry row stays SHUT -- see
# ``DeepSeaTempleRegistrationTests`` below for the test that pins that fact.
DEEP_SEA_TEMPLE = 10
DEEP_SEA_TEMPLE_ROSTER_COUNT = 94
# ADDED round l03cgh (LANE-A): bg0005's own scene id and roster size, built,
# wired AND OPENED in one round (COO-DECISION 20260830_1441's queue, third
# door) rather than across three -- see ``EvilPortRegistrationTests`` below
# for the test that pins that fact.
EVIL_PORT = 5
EVIL_PORT_ROSTER_COUNT = 87
# ADDED round fx0007 (LANE-A): bg0006's own scene id and roster size, built,
# wired AND OPENED in one round (COO-DECISION 20260830_1441's queue, fourth
# door) -- same compressed shape round l03cgh used for scene 5 -- see
# ``OceanWalledCityRegistrationTests`` below for the test that pins that fact.
OCEAN_WALLED_CITY = 6
OCEAN_WALLED_CITY_ROSTER_COUNT = 66


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _registry_with_door(work: Path, scene_id=VOLCANO, allowed=True):
    """A loaded registry whose ``scene_id`` row(s) are open/shut.  Temp only.

    Never the repository's file: this exists to measure what the one boolean
    is worth, not to turn it.  ``scene_id`` accepts a single int (the
    original shape) or an iterable of ints -- ADDED round 2jdde8 because
    ``ComposerContractTests`` needs more than one of this lane's scenes open
    in the SAME registry now that there are two, and writing a second
    near-identical helper to open a second door is the duplication this
    module's own docstring warns a second implementation always is.

    ROUND vvy6q7 TURNED THE HELPER AROUND, because the repository's file
    turned.  Scene 14 is OPEN on main now (COO-DECISION 20260829_2342), so
    the interesting temp registry is the SHUT one: the admission property
    this file exists for -- "no route ships a roster into a scene the
    registry says is shut" -- can only be driven against a shut registry, and
    driving it against the real one would now assert the opposite thing while
    still passing.  ``allowed`` is the whole of the change.
    """
    scene_ids = (scene_id,) if isinstance(scene_id, int) else tuple(scene_id)
    raw = json.loads(
        world_scene_travel.REGISTRY_PATH.read_text(encoding="ascii"))
    for row in raw["destinations"]:
        if row["n_id"] in scene_ids:
            row["login_entry_allowed"] = bool(allowed)
    state = "open" if allowed else "shut"
    tag = "-".join(str(s) for s in scene_ids)
    path = work / f"registry_scene_{tag}_{state}.json"
    path.write_text(
        json.dumps(raw, indent=2, ensure_ascii=True) + "\n", encoding="ascii")
    return world_scene_travel.load_scene_registry(path), path


def _registry_with_door_open(work: Path, scene_id=VOLCANO):
    """Back-compatible name for the open case."""
    return _registry_with_door(work, scene_id, allowed=True)


def _registry_with_door_shut(work: Path, scene_id=VOLCANO):
    """The registry as it read before round vvy6q7: this scene refused."""
    return _registry_with_door(work, scene_id, allowed=False)


class RegistrationTests(unittest.TestCase):
    def test_the_module_is_discovered_and_gated_open(self):
        self.assertTrue(
            lane_hooks.module_production_allowed("lane_a_scene_census"))

    def test_scene_14_has_this_lanes_composer_registered(self):
        composer = lane_hooks.scene_census_composer(VOLCANO)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)

    def test_the_registered_set_is_exactly_what_the_module_declares(self):
        for scene_id in lane_a.scenes_this_lane_composes_for():
            with self.subTest(scene=scene_id):
                composer = lane_hooks.scene_census_composer(scene_id)
                self.assertIsNotNone(composer)
                self.assertEqual(composer.module, lane_a.__name__)

    def test_a_console_reader_with_no_scene_is_a_dead_table_row(self):
        # ~~the other direction used to be asserted here too~~ -- it restated
        # scenes_this_lane_composes_for()'s own filter predicate verbatim and
        # could not fail under any table state (pf-adversary, round
        # ga91m5-r2, D5).  The dangerous direction is driven in
        # SkippedScenesAreNamedTests below.
        sources = set(world_scene_travel.CENSUS_SOURCES.values())
        for source in lane_a._CONSOLE_LINES_OF:
            with self.subTest(source=source):
                self.assertIn(source, sources)

    def test_each_composer_binds_its_own_scene(self):
        # runtime.py passes scene_id explicitly, so a late-binding closure
        # would still compose the right scene THERE.  This is about direct
        # callers - this lane's own tests, and any future non-runtime one.
        first = lane_a._compose_for_scene(VOLCANO)
        second = lane_a._compose_for_scene(278)
        self.assertEqual(first.__kwdefaults__["scene_id"], VOLCANO)
        self.assertEqual(second.__kwdefaults__["scene_id"], 278)


class SkippedScenesAreNamedTests(unittest.TestCase):
    """A scene dropped in silence is the defect, not the drop.

    pf-adversary added a row to the seam's ``CENSUS_SOURCES`` with no console
    reader and measured that it vanished: no event, no line, nothing red
    (round ga91m5-r2, D3).  These drive both filters, each on its own, so a
    refactor that deletes either conjunct goes red - the mutants that survived
    that pass.
    """

    def setUp(self):
        self._sources = dict(world_scene_travel.CENSUS_SOURCES)
        self._readers = dict(lane_a._CONSOLE_LINES_OF)
        self.addCleanup(self._restore)

    def _restore(self):
        world_scene_travel.CENSUS_SOURCES.clear()
        world_scene_travel.CENSUS_SOURCES.update(self._sources)
        lane_a._CONSOLE_LINES_OF.clear()
        lane_a._CONSOLE_LINES_OF.update(self._readers)

    def test_a_scene_with_no_console_reader_is_skipped_and_named(self):
        world_scene_travel.CENSUS_SOURCES[130] = "bg0130_roster_not_written"
        self.assertNotIn(130, lane_a.scenes_this_lane_composes_for())
        skipped = {
            scene_id: reason
            for scene_id, _source, reason in lane_a.skipped_scenes()
        }
        self.assertEqual(
            skipped.get(130), "no_console_reader_in_this_lane_file")

    def test_a_reserved_scene_stays_out_even_with_a_console_reader(self):
        # Drives the reserved filter ALONE.  Without this, giving scene 1 a
        # reader is the only thing standing between the runtime's home census
        # and a lane composer registered over it - and pf-adversary measured
        # that deleting the reserved filter changed nothing any test saw.
        home = world_scene_travel.CENSUS_SCENE_ID
        lane_a._CONSOLE_LINES_OF[
            world_scene_travel.CENSUS_SOURCES[home]] = lambda generation: ()
        self.assertNotIn(home, lane_a.scenes_this_lane_composes_for())
        skipped = {
            scene_id: reason
            for scene_id, _source, reason in lane_a.skipped_scenes()
        }
        self.assertEqual(skipped.get(home), "reserved_by_a_runtime_branch")

    def test_the_two_reserved_scenes_are_named_as_skipped_today(self):
        skipped = {
            scene_id for scene_id, _source, _reason in lane_a.skipped_scenes()
        }
        for scene_id in lane_a.RESERVED_BY_RUNTIME_BRANCHES:
            with self.subTest(scene=scene_id):
                self.assertIn(scene_id, skipped)


class TheAdmissionCheckIsTheGateTests(unittest.TestCase):
    """The property, driven three ways, instead of the registry boolean once.

    Every route pf-adversary found into scene 14 ends here, including the one
    that needs no registry edit at all.

    ROUND vvy6q7 REPOINTED THIS CLASS AT A SHUT TEMP REGISTRY, AND THE REASON
    MATTERS MORE THAN THE EDIT.  Scene 14 is OPEN on main now (COO-DECISION
    20260829_2342), so every assertion here that used to read the repository's
    file would now be asserting the OPPOSITE PROPERTY WHILE STILL PASSING --
    "the composer declines" would have quietly become "the composer declines
    for scenes nobody registered", which is true of a module that does
    nothing.  The property this class is for is unchanged and is not about
    scene 14 at all: NO ROUTE SHIPS A ROSTER INTO A SCENE THE REGISTRY SAYS
    IS SHUT.  It is driven against a registry that says shut, which is the
    only registry that can drive it.  What the real file does today is pinned
    below in ``test_the_real_registry_now_composes_and_that_is_the_round``.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(VOLCANO))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)
        cls.shut_registry, _ = _registry_with_door_shut(Path(cls._work.name))

    def _compose_with_shut_registry(self, scene_id=VOLCANO):
        return lane_a._compose_for_scene(scene_id)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=scene_id,
            scene_entry_registry=self.shut_registry,
        )

    def test_the_composer_declines_for_every_scene_it_registered(self):
        # Every scene this lane registers a composer for, asked with that
        # scene's own door shut.  If any of these returns a result, the
        # admission check has stopped being a check.
        for scene_id in lane_a.scenes_this_lane_composes_for():
            with self.subTest(scene=scene_id):
                shut, _ = _registry_with_door_shut(
                    Path(self._work.name), scene_id)
                self.assertIsNone(lane_a._compose_for_scene(scene_id)(
                    legacy=self.legacy,
                    anchor=self.anchor,
                    scene_id=scene_id,
                    scene_entry_registry=shut,
                ))

    def test_the_registered_composer_object_declines_too(self):
        # Not the factory: the exact callable runtime.py holds.
        composer = lane_hooks.scene_census_composer(VOLCANO)
        self.assertIsNone(composer.compose(
            legacy=self.legacy, anchor=self.anchor, scene_id=VOLCANO,
            scene_entry_registry=self.shut_registry,
        ))

    def test_a_via_login_false_resolution_still_gets_no_census(self):
        """The route that needs no registry edit, and the reason for the check.

        ``resolve_entry(..., via_login=False)`` resolves scene 14 whatever the
        login key says - asserted here rather than assumed, because that is
        the route pf-adversary used to ship 81 actors past a shut door with
        one lambda and no registry edit.  With the door shut the census still
        refuses, and THAT is what makes the boolean the only key.
        """
        entry = world_scene_entry.resolve_entry(
            Position(VOLCANO, 0, 0.0, 0.0, 0.0, 0),
            registry=self.shut_registry,
            emit=lambda line: None,
            via_login=False,
        )
        self.assertEqual(entry.position.scene_id, VOLCANO)
        self.assertIsNone(self._compose_with_shut_registry())

    def test_a_missing_or_unreadable_registry_declines_rather_than_ships(self):
        # Fail-closed in the direction that matters: no registry is not a
        # licence to populate.
        self.assertFalse(lane_a.scene_is_open_to_players(VOLCANO, object()))
        self.assertFalse(lane_a.scene_is_open_to_players(999999))

    def test_the_real_registry_now_composes_and_that_is_the_round(self):
        """What the file on main does today, stated as an assertion.

        The inverse of the test this replaced (``test_the_registry_row_says_
        shut_too``, which asserted ``login_entry_allowed`` was False).  It is
        kept as an assertion rather than deleted because a silent revert of
        that boolean is exactly the kind of change this lane wants to hear
        about from a red test rather than from an attended round that boots
        into an empty island.
        """
        destination = world_scene_travel.destination(
            VOLCANO, world_scene_travel.load_scene_registry())
        self.assertTrue(destination.login_entry_allowed)
        result = lane_a._compose_for_scene(VOLCANO)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=VOLCANO,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, ROSTER_COUNT)


class ComposerContractTests(unittest.TestCase):
    """What the composer returns once a scene IS open.

    The registry is opened in a temp file and handed to the composer as
    ``scene_entry_registry`` - the same argument runtime.py passes - so
    nothing here monkeypatches a loader or touches the repository's file.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(VOLCANO))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)
        # ALL THREE of this lane's scenes open in the one registry the
        # loop-based tests below share (ADDED round 2jdde8, WIDENED round
        # c42axq): a registry that leaves DEEP_SEA_TEMPLE shut makes every
        # ``scenes_this_lane_composes_for()`` loop below silently decline for
        # scene 10 the moment that scene registered, which is the same
        # "identical to an oversight" shape this file's own
        # SkippedScenesAreNamedTests exists to catch on the production
        # tables -- a test fixture can commit the same sin.
        cls.open_registry, _ = _registry_with_door_open(
            Path(cls._work.name), (VOLCANO, SLAVE_MARKET, DEEP_SEA_TEMPLE))

    def _compose(self, scene_id=VOLCANO, anchor=None):
        return lane_a._compose_for_scene(scene_id)(
            legacy=self.legacy,
            anchor=self.anchor if anchor is None else anchor,
            scene_id=scene_id,
            scene_entry_registry=self.open_registry,
        )

    def test_the_result_is_the_contract_tuple_and_nothing_else(self):
        result = self._compose()
        self.assertIsInstance(result, lane_hooks.SceneCensusResult)
        self.assertEqual(result.actor_count, ROSTER_COUNT)
        self.assertIsInstance(result.pc, bytes)
        self.assertIsInstance(result.frame, bytes)
        self.assertGreater(len(result.pc), 0)

    def test_the_count_and_bytes_are_the_seams_and_not_recounted_here(self):
        handoff = world_population_handoff.handoff_for_arrival(
            self.legacy, VOLCANO, self.anchor)
        result = self._compose()
        self.assertEqual(result.actor_count, handoff.actor_count)
        self.assertEqual(result.pc, handoff.pc)
        self.assertEqual(result.frame, handoff.frame)

    def test_the_reapply_is_the_scenes_own_schedule_not_zero(self):
        # pf-adversary mutated this to 0 and nothing went red (round
        # ga91m5-r2, D4): a 0 ms reapply collapses the model-readiness resend
        # into the initial frame, which is the one thing the second action
        # exists to avoid.
        result = self._compose()
        self.assertEqual(
            result.initial_reapply_ms,
            world_population_bg0015.INITIAL_REAPPLY_MS)
        self.assertGreater(result.initial_reapply_ms, 0)

    def test_the_reapply_field_can_never_reach_the_call_site_as_none(self):
        # SceneHandoff.reapply_ms is `int | None` and the call site coerces
        # it, so None there would refuse the census instead of shipping it.
        # Measured, and corrected after pf-adversary refuted an earlier
        # version of this comment: BOTH non-census kinds carry None -
        # KIND_CLEAR through world_population_handoff.CLEAR_REAPPLY_MS (that
        # module declares it `int | None = None`) and KIND_UNAVAILABLE
        # through the builder that returns it.  The earlier comment named
        # "only KIND_UNAVAILABLE" and cited an `_unavailable` builder that
        # does not exist under that name.  Declining every non-census kind is
        # what keeps both out.
        for scene_id in lane_a.scenes_this_lane_composes_for():
            with self.subTest(scene=scene_id):
                handoff = world_population_handoff.handoff_for_arrival(
                    self.legacy, scene_id,
                    world_scene_travel.spawn_position(
                        world_scene_travel.destination(scene_id)))
                self.assertEqual(
                    handoff.kind, world_population_handoff.KIND_CENSUS)
                self.assertIsNotNone(handoff.reapply_ms)
                self.assertIsInstance(
                    self._compose(scene_id).initial_reapply_ms, int)

    def test_the_console_carries_the_seam_line_the_census_and_the_shortfall(
            self):
        result = self._compose()
        self.assertTrue(
            result.console_lines[0].startswith("WORLD_POP_HANDOFF scene=14 "),
            result.console_lines[0])
        self.assertTrue(
            any(line.startswith("WORLD_CENSUS_BG0015 ")
                for line in result.console_lines))
        # The dropped placements are CHARTER-02's shortfall evidence, and
        # pf-adversary measured that deleting unresolved_lines() left every
        # assertion green (round ga91m5-r2, D4).  Counted, not bounded.
        unshipped = [
            line for line in result.console_lines
            if line.startswith("BG0015_UNSHIPPED ")
        ]
        self.assertEqual(
            len(unshipped),
            len(world_population_bg0015.unresolved_lines()))
        self.assertGreater(len(unshipped), 0)
        # The hostility-coverage line, added round ucaybn after pf-adversary
        # measured its absence (D10): describe_census_hostility's contract is
        # "printed UNCONDITIONALLY", and "no line at all" is the state GT-084
        # misread once.  Its CONTENT for scene 14 is expected to be
        # unbacked=none - no actor here carries a faction bit - so what is
        # asserted is that the line EXISTS and names this scene.
        hostility = [
            line for line in result.console_lines
            if line.startswith("MOB_CENSUS_HOSTILITY ")
        ]
        self.assertEqual(len(hostility), 1)
        self.assertIn("scene_id=%d" % VOLCANO, hostility[0])
        self.assertEqual(
            len(result.console_lines),
            1 + 1 + ROSTER_COUNT + len(unshipped) + 1)

    def test_every_console_line_is_ascii(self):
        # The bridge console is cp874; a non-ASCII line raises inside the
        # print itself, which is the scar rounds 86 and 142 left.
        for line in self._compose().console_lines:
            with self.subTest(line=line[:40]):
                line.encode("ascii")

    def test_a_composition_failure_raises_instead_of_declining(self):
        """The strict entry point, pinned.

        ``handoff_for_arrival`` raises where ``handoff_on_crossing`` returns
        ``KIND_UNAVAILABLE``.  Swapping them would turn every composition
        crash into ``..._declined_scene_14`` - a crash relabelled as a lane
        decision - and pf-adversary measured that no test could see the
        difference (round ga91m5-r2, D4).  A bad anchor is a composition
        failure the seam raises on.
        """
        with self.assertRaises(Exception) as caught:
            self._compose(anchor="not-a-point")
        self.assertNotIsInstance(caught.exception, AssertionError)

    def test_a_scene_the_seam_leaves_empty_is_declined_not_cleared(self):
        # 278 is in SCENES_INTENTIONALLY_UNPOPULATED, so the seam answers
        # `clear`.  The arrival path never asked for a clear frame, so the
        # honest answer is None.  Driven with 278's door open, so that the
        # admission check is not what produces the None.
        self.assertIn(
            278, world_population_handoff.SCENES_INTENTIONALLY_UNPOPULATED)
        with tempfile.TemporaryDirectory() as work:
            registry, _ = _registry_with_door_open(Path(work), 278)
            self.assertTrue(lane_a.scene_is_open_to_players(278, registry))
            self.assertIsNone(lane_a._compose_for_scene(278)(
                legacy=self.legacy,
                anchor=world_scene_travel.spawn_position(
                    world_scene_travel.destination(278, registry)),
                scene_id=278,
                scene_entry_registry=registry,
            ))


class OnTheRealDispatcherTests(unittest.TestCase):
    """End to end: open the door in a temp registry and 81 actors ship.

    This is the only test that monkeypatches the loader, because the runtime
    loads the registry itself at boot.  The cleanup restores it on failure as
    well as on success.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()

    @staticmethod
    def _target_pos_pc(legacy, xyz, heading=0.0, moving=0, derived=0):
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
            + legacy.u8tag(0x0B, 0)
            + b"".join(legacy.f32tag(value) for value in (*xyz, heading))
            + legacy.u8tag(0x0B, moving)
            + legacy.u8tag(0x0B, derived)
        )

    def test_with_the_real_registry_the_lane_census_ships_81_actors(self):
        """THE ROUND vvy6q7 CLAIM, DRIVEN ON THE FILE THAT IS ACTUALLY ON MAIN.

        This test used to open the door in a temp registry and patch the
        loader, because the repository's door was shut.  COO-DECISION
        20260829_2342 opened it, so the patch is gone and this is now the
        production path: no flags, no monkeypatched loader, the registry file
        this repository ships.  A boot that logs a character into scene 14
        composes and sends 81 actors.  That is the sentence GT-134 goes and
        looks at on a screen.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            self.assertTrue(
                world_scene_travel.destination(
                    VOLCANO, world_scene_travel.load_scene_registry()
                ).login_entry_allowed,
                "scene 14's door is shut again - this test is now measuring "
                "the wrong registry; see COO-DECISION 20260829_2342",
            )
            store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            legacy = self.legacy
            lifecycle = CharacterLifecycle(
                store,
                Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                         legacy.V135_PLAYER_Z),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = make_state_class(
                legacy, lifecycle, LegacyProjector(legacy))
            state = state_type("driver")
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("driver")))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id)[-1]
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(
                    VOLCANO, world_scene_travel.load_scene_registry()))
            store.select_character(
                state.foundation.session_id, character.selector)
            store.save_position(
                state.foundation.session_id, character.id,
                Position(VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0))
            with contextlib.redirect_stdout(io.StringIO()):
                state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(character.selector)))
            # The login reached a teleport, which is exactly what the shut
            # door prevents in production.
            self.assertTrue(state.teleport_sent)
            state.runtime_ack_sent = True
            state.welcome_message_sent = True
            state.current_scene_music_sent = True
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                actions = state.dispatch(legacy.parse_outer(
                    self._target_pos_pc(legacy, spawn)))
            census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
            self.assertEqual(
                [a[0] for a in census],
                [f"WORLD_CENSUS_LANE_SCENE{VOLCANO}_INITIAL_{ROSTER_COUNT}",
                 f"WORLD_CENSUS_LANE_SCENE{VOLCANO}_REAPPLY_{ROSTER_COUNT}"])
            # Byte counts derived by the call site with len(), so this is the
            # wire agreeing with the label rather than the lane asserting it.
            self.assertIn(
                f"world_census_lane_committed_actors_{ROSTER_COUNT}"
                f"_pc_{len(census[0][1])}_frame_{len(census[0][2])}",
                state.events)
            printed = buf.getvalue()
            self.assertIn("WORLD_POP_HANDOFF scene=14 kind=census", printed)
            self.assertIn("WORLD_CENSUS_BG0015 assembled=81/91", printed)

    def test_with_the_real_registry_the_slave_market_census_ships_109(self):
        """SCENE 4'S OWN COPY OF THE TEST ABOVE, ADDED LANE-A ROUND bq4mst.

        Same shape as ``test_with_the_real_registry_the_lane_census_ships_
        81_actors``, on the scene COO-DECISION 20260830_1441 named as the
        first of the ten to open once its composer was ready
        (COO-DECISION 20260830_1441: 'do not flip login_entry_allowed until
        the composer is truly ready'). Round bq4mst is the round that judged
        it ready and flipped the one boolean on ``scenarios/world_scene_
        registry_001.json``. No flag, no monkeypatched loader -- the
        registry file this repository ships.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            self.assertTrue(
                world_scene_travel.destination(
                    SLAVE_MARKET, world_scene_travel.load_scene_registry()
                ).login_entry_allowed,
                "scene 4's door is shut again - this test is now measuring "
                "the wrong registry; see this round's own letter/round file",
            )
            store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            legacy = self.legacy
            lifecycle = CharacterLifecycle(
                store,
                Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                         legacy.V135_PLAYER_Z),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = make_state_class(
                legacy, lifecycle, LegacyProjector(legacy))
            state = state_type("driver")
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("driver")))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id)[-1]
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(
                    SLAVE_MARKET, world_scene_travel.load_scene_registry()))
            store.select_character(
                state.foundation.session_id, character.selector)
            store.save_position(
                state.foundation.session_id, character.id,
                Position(SLAVE_MARKET, 0, spawn[0], spawn[1], spawn[2], 0.0))
            with contextlib.redirect_stdout(io.StringIO()):
                state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(character.selector)))
            self.assertTrue(state.teleport_sent)
            state.runtime_ack_sent = True
            state.welcome_message_sent = True
            state.current_scene_music_sent = True
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                actions = state.dispatch(legacy.parse_outer(
                    self._target_pos_pc(legacy, spawn)))
            census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
            self.assertEqual(
                [a[0] for a in census],
                [f"WORLD_CENSUS_LANE_SCENE{SLAVE_MARKET}_INITIAL_"
                 f"{SLAVE_MARKET_ROSTER_COUNT}",
                 f"WORLD_CENSUS_LANE_SCENE{SLAVE_MARKET}_REAPPLY_"
                 f"{SLAVE_MARKET_ROSTER_COUNT}"])
            self.assertIn(
                f"world_census_lane_committed_actors_"
                f"{SLAVE_MARKET_ROSTER_COUNT}"
                f"_pc_{len(census[0][1])}_frame_{len(census[0][2])}",
                state.events)
            printed = buf.getvalue()
            self.assertIn(
                "WORLD_POP_HANDOFF scene=4 kind=census", printed)
            self.assertIn(
                "WORLD_CENSUS_BG0004 assembled=109/116", printed)

    def test_with_the_real_registry_the_deep_sea_temple_census_ships_94(self):
        """SCENE 10'S OWN COPY OF THE TEST ABOVE, ADDED LANE-A ROUND 3t75jw.

        Same shape as ``test_with_the_real_registry_the_slave_market_
        census_ships_109``, on the second of the ten doors this lane has
        opened (COO-DECISION 20260830_1441's queue, same instruction: do
        not flip until the composer is ready).  Round 3t75jw is the round
        that judged it ready and flipped the boolean.  No flag, no
        monkeypatched loader -- the registry file this repository ships.
        This test proves the census ships; it does not and cannot prove
        the landing point is standable ground -- see GT-166 for that.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            self.assertTrue(
                world_scene_travel.destination(
                    DEEP_SEA_TEMPLE, world_scene_travel.load_scene_registry()
                ).login_entry_allowed,
                "scene 10's door is shut again - this test is now measuring "
                "the wrong registry; see this round's own letter/round file",
            )
            store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            legacy = self.legacy
            lifecycle = CharacterLifecycle(
                store,
                Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                         legacy.V135_PLAYER_Z),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = make_state_class(
                legacy, lifecycle, LegacyProjector(legacy))
            state = state_type("driver")
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("driver")))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id)[-1]
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(
                    DEEP_SEA_TEMPLE, world_scene_travel.load_scene_registry()))
            store.select_character(
                state.foundation.session_id, character.selector)
            store.save_position(
                state.foundation.session_id, character.id,
                Position(
                    DEEP_SEA_TEMPLE, 0, spawn[0], spawn[1], spawn[2], 0.0))
            with contextlib.redirect_stdout(io.StringIO()):
                state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(character.selector)))
            self.assertTrue(state.teleport_sent)
            state.runtime_ack_sent = True
            state.welcome_message_sent = True
            state.current_scene_music_sent = True
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                actions = state.dispatch(legacy.parse_outer(
                    self._target_pos_pc(legacy, spawn)))
            census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
            self.assertEqual(
                [a[0] for a in census],
                [f"WORLD_CENSUS_LANE_SCENE{DEEP_SEA_TEMPLE}_INITIAL_"
                 f"{DEEP_SEA_TEMPLE_ROSTER_COUNT}",
                 f"WORLD_CENSUS_LANE_SCENE{DEEP_SEA_TEMPLE}_REAPPLY_"
                 f"{DEEP_SEA_TEMPLE_ROSTER_COUNT}"])
            self.assertIn(
                f"world_census_lane_committed_actors_"
                f"{DEEP_SEA_TEMPLE_ROSTER_COUNT}"
                f"_pc_{len(census[0][1])}_frame_{len(census[0][2])}",
                state.events)
            printed = buf.getvalue()
            self.assertIn(
                "WORLD_POP_HANDOFF scene=10 kind=census", printed)
            self.assertIn(
                "WORLD_CENSUS_BG0010 assembled=94/100", printed)

    def test_with_the_real_registry_the_evil_port_census_ships_87(self):
        """SCENE 5'S OWN COPY OF THE TEST ABOVE, ADDED LANE-A ROUND l03cgh.

        Same shape as ``test_with_the_real_registry_the_deep_sea_temple_
        census_ships_94``, on the third of the ten doors this lane has
        opened (COO-DECISION 20260830_1441's queue).  UNLIKE scenes 4 and
        10, this round builds, wires AND opens scene 5 in one pass rather
        than three -- see ``EvilPortRegistrationTests`` below and this
        round's own round file for why.  No flag, no monkeypatched loader
        -- the registry file this repository ships.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            self.assertTrue(
                world_scene_travel.destination(
                    EVIL_PORT, world_scene_travel.load_scene_registry()
                ).login_entry_allowed,
                "scene 5's door is shut again - this test is now measuring "
                "the wrong registry; see this round's own letter/round file",
            )
            store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            legacy = self.legacy
            lifecycle = CharacterLifecycle(
                store,
                Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                         legacy.V135_PLAYER_Z),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = make_state_class(
                legacy, lifecycle, LegacyProjector(legacy))
            state = state_type("driver")
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("driver")))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id)[-1]
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(
                    EVIL_PORT, world_scene_travel.load_scene_registry()))
            store.select_character(
                state.foundation.session_id, character.selector)
            store.save_position(
                state.foundation.session_id, character.id,
                Position(
                    EVIL_PORT, 0, spawn[0], spawn[1], spawn[2], 0.0))
            with contextlib.redirect_stdout(io.StringIO()):
                state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(character.selector)))
            self.assertTrue(state.teleport_sent)
            state.runtime_ack_sent = True
            state.welcome_message_sent = True
            state.current_scene_music_sent = True
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                actions = state.dispatch(legacy.parse_outer(
                    self._target_pos_pc(legacy, spawn)))
            census = [a for a in actions if a[0].startswith("WORLD_CENSUS_")]
            self.assertEqual(
                [a[0] for a in census],
                [f"WORLD_CENSUS_LANE_SCENE{EVIL_PORT}_INITIAL_"
                 f"{EVIL_PORT_ROSTER_COUNT}",
                 f"WORLD_CENSUS_LANE_SCENE{EVIL_PORT}_REAPPLY_"
                 f"{EVIL_PORT_ROSTER_COUNT}"])
            self.assertIn(
                f"world_census_lane_committed_actors_"
                f"{EVIL_PORT_ROSTER_COUNT}"
                f"_pc_{len(census[0][1])}_frame_{len(census[0][2])}",
                state.events)
            printed = buf.getvalue()
            self.assertIn(
                "WORLD_POP_HANDOFF scene=5 kind=census", printed)
            self.assertIn(
                "WORLD_CENSUS_BG0005 assembled=87/92", printed)

    def test_with_the_door_shut_the_login_never_reaches_the_census(self):
        """The other half of the pair: refused at the login, no census at all.

        UNTIL ROUND vvy6q7 THIS TEST USED THE REPOSITORY'S REGISTRY, because
        the repository's registry was the shut one.  Scene 14 is open on main
        now (COO-DECISION 20260829_2342), so the shut registry has moved into
        a temp file and the patching that used to belong to the other test
        belongs to this one.  Nothing about what is asserted changed: with the
        door shut the login is refused by name, no teleport is sent, and the
        census branch is never reached.  Together the pair still says the
        difference between an empty island and 81 actors is one boolean, and
        that nothing else in this file's chain is missing.
        """
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            _, patched = _registry_with_door_shut(work)
            real_loader = world_scene_travel.load_scene_registry
            world_scene_travel.load_scene_registry = (
                lambda *a, _f=real_loader, _p=patched, **k: _f(_p))
            self.addCleanup(
                setattr, world_scene_travel, "load_scene_registry",
                real_loader)
            store = SQLiteStore(work / "state.sqlite3", ROOT / "migrations")
            store.migrate()
            legacy = self.legacy
            lifecycle = CharacterLifecycle(
                store,
                Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                         legacy.V135_PLAYER_Z),
                legacy.extract_avatar_attr_wire_from_actor,
            )
            state_type = make_state_class(
                legacy, lifecycle, LegacyProjector(legacy))
            state = state_type("driver")
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc("driver")))
            state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            character = store.list_characters(
                state.foundation.account_id)[-1]
            spawn = world_scene_travel.spawn_position(
                world_scene_travel.destination(VOLCANO))
            store.select_character(
                state.foundation.session_id, character.selector)
            store.save_position(
                state.foundation.session_id, character.id,
                Position(VOLCANO, 0, spawn[0], spawn[1], spawn[2], 0.0))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(character.selector)))
            self.assertFalse(state.teleport_sent)
            self.assertIn(
                "WORLD_SCENE_ENTRY_REFUSED [scene_not_allowed_at_login]",
                buf.getvalue())


class SlaveMarketRegistrationTests(unittest.TestCase):
    """Scene 4's own half of this round: wired round 2jdde8, OPENED round bq4mst.

    ADDED round 2jdde8 (LANE-A).  ~~this class is deliberately narrow: it
    drives the ONE thing those loops do not - what the REPOSITORY'S OWN
    registry file says about scene 4 today, which is the opposite of what
    it says about scene 14.~~ STRUCK, NOT DELETED: true for two rounds
    (2jdde8, oprday-adjacent), false as of round bq4mst, which flipped
    ``login_entry_allowed`` on the same evidence COO-DECISION 20260830_1441
    asked for ("do not flip until the composer is truly ready").  This
    class now mirrors ``OnTheRealDispatcherTests.test_with_the_real_
    registry_the_lane_census_ships_81_actors`` in shape for the registry
    read-back half (the end-to-end dispatch proof itself lives in that
    class, alongside VOLCANO's, per this file's own convention of keeping
    the two production-path tests together).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(SLAVE_MARKET))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)

    def test_the_module_registered_a_composer_for_scene_4(self):
        composer = lane_hooks.scene_census_composer(SLAVE_MARKET)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)

    def test_the_real_registry_now_composes_and_that_is_the_round(self):
        """WHAT THE FILE ON MAIN DOES TODAY, STATED AS AN ASSERTION.

        The inverse of the test this replaced
        (``test_the_real_registry_still_shuts_this_door``, which asserted
        ``login_entry_allowed`` was False).  Kept as an assertion rather
        than deleted, same reasoning as VOLCANO's own version of this test:
        a silent revert of this boolean should be caught by a red test, not
        discovered in an attended round that boots into a refusal.
        """
        destination = world_scene_travel.destination(
            SLAVE_MARKET, world_scene_travel.load_scene_registry())
        self.assertTrue(destination.login_entry_allowed)
        result = lane_a._compose_for_scene(SLAVE_MARKET)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=SLAVE_MARKET,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, SLAVE_MARKET_ROSTER_COUNT)

    def test_opened_in_a_temp_registry_it_composes_the_full_roster(self):
        """PLUMBING PROOF, KEPT INDEPENDENT OF THE REPOSITORY'S OWN FILE.

        Never against the repository's file (see the module above this
        test file borrows its temp-registry pattern from) - this proves the
        PLUMBING is sound on its own terms, not by riding on whatever the
        real registry happens to say this round (that is the test above,
        and ``OnTheRealDispatcherTests``, added separately).
        """
        with tempfile.TemporaryDirectory() as work:
            registry, _ = _registry_with_door_open(
                Path(work), SLAVE_MARKET)
            result = lane_a._compose_for_scene(SLAVE_MARKET)(
                legacy=self.legacy,
                anchor=self.anchor,
                scene_id=SLAVE_MARKET,
                scene_entry_registry=registry,
            )
            self.assertIsNotNone(result)
            self.assertEqual(result.actor_count, SLAVE_MARKET_ROSTER_COUNT)
            self.assertTrue(
                result.console_lines[0].startswith(
                    "WORLD_POP_HANDOFF scene=4 "),
                result.console_lines[0])
            self.assertTrue(
                any(line.startswith("WORLD_CENSUS_BG0004 ")
                    for line in result.console_lines))
            unshipped = [
                line for line in result.console_lines
                if line.startswith("BG0004_UNSHIPPED ")
            ]
            self.assertEqual(
                len(unshipped),
                len(world_population_bg0004.unresolved_lines()))
            for line in result.console_lines:
                with self.subTest(line=line[:40]):
                    line.encode("ascii")


class DeepSeaTempleRegistrationTests(unittest.TestCase):
    """Scene 10's own half of this round: wired round c42axq, OPENED round 3t75jw.

    ADDED round c42axq (LANE-A), same shape as ``SlaveMarketRegistrationTests``
    at round 2jdde8.  ~~this class is deliberately narrow: it drives the ONE
    thing those loops do not - what the REPOSITORY'S OWN registry file says
    about scene 10 today, which is the opposite of what it says about scene
    14.~~ STRUCK, NOT DELETED: true for one round (c42axq), false as of round
    3t75jw, which flipped ``login_entry_allowed`` on the same evidence
    ``login_entry_allowed_because`` on this row records, the second door in
    the queue ``COO-DECISION 2026-08-30T14:41+07:00`` approved.  This class
    now mirrors ``SlaveMarketRegistrationTests`` in shape for the registry
    read-back half (the end-to-end dispatch proof itself lives in
    ``OnTheRealDispatcherTests``, alongside VOLCANO's and SLAVE_MARKET's, per
    this file's own convention of keeping the production-path tests
    together).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(DEEP_SEA_TEMPLE))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)

    def test_the_module_registered_a_composer_for_scene_10(self):
        composer = lane_hooks.scene_census_composer(DEEP_SEA_TEMPLE)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)

    def test_the_real_registry_now_composes_and_that_is_the_round(self):
        """WHAT THE FILE ON MAIN DOES TODAY, STATED AS AN ASSERTION.

        The inverse of the test this replaced
        (``test_the_real_registry_still_shuts_this_door``, which asserted
        ``login_entry_allowed`` was False).  Kept as an assertion rather
        than deleted, same reasoning as SLAVE_MARKET's own version of this
        test: a silent revert of this boolean should be caught by a red
        test, not discovered in an attended round that boots into a
        refusal.
        """
        destination = world_scene_travel.destination(
            DEEP_SEA_TEMPLE, world_scene_travel.load_scene_registry())
        self.assertTrue(destination.login_entry_allowed)
        result = lane_a._compose_for_scene(DEEP_SEA_TEMPLE)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=DEEP_SEA_TEMPLE,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, DEEP_SEA_TEMPLE_ROSTER_COUNT)

    def test_opened_in_a_temp_registry_it_composes_the_full_roster(self):
        """The other half: the wiring itself works once a door opens.

        Never against the repository's file (see the module above this
        test file borrows its temp-registry pattern from) - this proves the
        PLUMBING is sound, not that the door should open today.
        """
        with tempfile.TemporaryDirectory() as work:
            registry, _ = _registry_with_door_open(
                Path(work), DEEP_SEA_TEMPLE)
            result = lane_a._compose_for_scene(DEEP_SEA_TEMPLE)(
                legacy=self.legacy,
                anchor=self.anchor,
                scene_id=DEEP_SEA_TEMPLE,
                scene_entry_registry=registry,
            )
            self.assertIsNotNone(result)
            self.assertEqual(result.actor_count, DEEP_SEA_TEMPLE_ROSTER_COUNT)
            self.assertTrue(
                result.console_lines[0].startswith(
                    "WORLD_POP_HANDOFF scene=10 "),
                result.console_lines[0])
            self.assertTrue(
                any(line.startswith("WORLD_CENSUS_BG0010 ")
                    for line in result.console_lines))
            unshipped = [
                line for line in result.console_lines
                if line.startswith("BG0010_UNSHIPPED ")
            ]
            self.assertEqual(
                len(unshipped),
                len(world_population_bg0010.unresolved_lines()))
            for line in result.console_lines:
                with self.subTest(line=line[:40]):
                    line.encode("ascii")


class EvilPortRegistrationTests(unittest.TestCase):
    """Scene 5's own half of this round: built, wired AND OPENED, round l03cgh.

    ADDED round l03cgh (LANE-A), same shape as ``SlaveMarketRegistrationTests``
    (round 2jdde8) and ``DeepSeaTempleRegistrationTests`` (round c42axq),
    with ONE DIFFERENCE: those two classes each started narrow (wired, door
    still shut) and were widened by a LATER round once the door opened. This
    class starts already-widened, because build/wire/open all land in this
    one round -- see this round's own round file for why (the existing
    generic ``ComposerContractTests`` already assumed every wired scene in
    this lane is open, since scenes 4/10/14 all were by the time this round
    started).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(EVIL_PORT))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)

    def test_the_module_registered_a_composer_for_scene_5(self):
        composer = lane_hooks.scene_census_composer(EVIL_PORT)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)

    def test_the_real_registry_now_composes_and_that_is_the_round(self):
        """WHAT THE FILE ON MAIN DOES TODAY, STATED AS AN ASSERTION.

        Same reasoning as ``SlaveMarketRegistrationTests``'s and
        ``DeepSeaTempleRegistrationTests``'s own versions of this test: a
        silent revert of this boolean should be caught by a red test, not
        discovered in an attended round that boots into a refusal.
        """
        destination = world_scene_travel.destination(
            EVIL_PORT, world_scene_travel.load_scene_registry())
        self.assertTrue(destination.login_entry_allowed)
        result = lane_a._compose_for_scene(EVIL_PORT)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=EVIL_PORT,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, EVIL_PORT_ROSTER_COUNT)

    def test_opened_in_a_temp_registry_it_composes_the_full_roster(self):
        """The other half: the wiring itself works once a door opens.

        Never against the repository's file (see the module above this
        test file borrows its temp-registry pattern from) - this proves the
        PLUMBING is sound, driven independently of what the real registry
        file happens to say this round.
        """
        with tempfile.TemporaryDirectory() as work:
            registry, _ = _registry_with_door_open(
                Path(work), EVIL_PORT)
            result = lane_a._compose_for_scene(EVIL_PORT)(
                legacy=self.legacy,
                anchor=self.anchor,
                scene_id=EVIL_PORT,
                scene_entry_registry=registry,
            )
            self.assertIsNotNone(result)
            self.assertEqual(result.actor_count, EVIL_PORT_ROSTER_COUNT)
            self.assertTrue(
                result.console_lines[0].startswith(
                    "WORLD_POP_HANDOFF scene=5 "),
                result.console_lines[0])
            self.assertTrue(
                any(line.startswith("WORLD_CENSUS_BG0005 ")
                    for line in result.console_lines))
            unshipped = [
                line for line in result.console_lines
                if line.startswith("BG0005_UNSHIPPED ")
            ]
            self.assertEqual(
                len(unshipped),
                len(world_population_bg0005.unresolved_lines()))
            for line in result.console_lines:
                with self.subTest(line=line[:40]):
                    line.encode("ascii")


class OceanWalledCityRegistrationTests(unittest.TestCase):
    """Scene 6's own half of this round: built, wired AND OPENED, round fx0007.

    ADDED round fx0007 (LANE-A), same shape as ``EvilPortRegistrationTests``
    (round l03cgh): build/wire/open all land in this one round -- see this
    round's own round file for why (the existing generic
    ``ComposerContractTests`` already assumed every wired scene in this lane
    is open, since scenes 4/5/10/14 all were by the time this round
    started).
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.legacy = _legacy()
        cls.anchor = world_scene_travel.spawn_position(
            world_scene_travel.destination(OCEAN_WALLED_CITY))
        cls._work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._work.cleanup)

    def test_the_module_registered_a_composer_for_scene_6(self):
        composer = lane_hooks.scene_census_composer(OCEAN_WALLED_CITY)
        self.assertIsNotNone(composer)
        self.assertEqual(composer.module, lane_a.__name__)

    def test_the_real_registry_now_composes_and_that_is_the_round(self):
        """WHAT THE FILE ON MAIN DOES TODAY, STATED AS AN ASSERTION.

        Same reasoning as ``EvilPortRegistrationTests``'s own version of this
        test: a silent revert of this boolean should be caught by a red
        test, not discovered in an attended round that boots into a
        refusal.
        """
        destination = world_scene_travel.destination(
            OCEAN_WALLED_CITY, world_scene_travel.load_scene_registry())
        self.assertTrue(destination.login_entry_allowed)
        result = lane_a._compose_for_scene(OCEAN_WALLED_CITY)(
            legacy=self.legacy,
            anchor=self.anchor,
            scene_id=OCEAN_WALLED_CITY,
            scene_entry_registry=world_scene_travel.load_scene_registry(),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.actor_count, OCEAN_WALLED_CITY_ROSTER_COUNT)

    def test_opened_in_a_temp_registry_it_composes_the_full_roster(self):
        """The other half: the wiring itself works once a door opens.

        Never against the repository's file (see the module above this
        test file borrows its temp-registry pattern from) - this proves the
        PLUMBING is sound, driven independently of what the real registry
        file happens to say this round.
        """
        with tempfile.TemporaryDirectory() as work:
            registry, _ = _registry_with_door_open(
                Path(work), OCEAN_WALLED_CITY)
            result = lane_a._compose_for_scene(OCEAN_WALLED_CITY)(
                legacy=self.legacy,
                anchor=self.anchor,
                scene_id=OCEAN_WALLED_CITY,
                scene_entry_registry=registry,
            )
            self.assertIsNotNone(result)
            self.assertEqual(
                result.actor_count, OCEAN_WALLED_CITY_ROSTER_COUNT)
            self.assertTrue(
                result.console_lines[0].startswith(
                    "WORLD_POP_HANDOFF scene=6 "),
                result.console_lines[0])
            self.assertTrue(
                any(line.startswith("WORLD_CENSUS_BG0006 ")
                    for line in result.console_lines))
            unshipped = [
                line for line in result.console_lines
                if line.startswith("BG0006_UNSHIPPED ")
            ]
            self.assertEqual(
                len(unshipped),
                len(world_population_bg0006.unresolved_lines()))
            for line in result.console_lines:
                with self.subTest(line=line[:40]):
                    line.encode("ascii")


if __name__ == "__main__":
    unittest.main()
