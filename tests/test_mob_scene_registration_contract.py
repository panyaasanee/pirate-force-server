"""LANE-B: the generic per-scene registration contract every live combat
scene must pass, so a new scene's own hole cannot go undetected the way
scenes 3 and 4 each did.

COO-DECISION 20260905_1246 (option (c), answering LANE-B's own
``20260905_1215_LANE-B-ASK-COO-the-per-scene-contract-that-does-not-exist
.md``): one test that walks ``field_mobs.live_scenes()`` -- the one place
that already decides which scenes :func:`field_mobs.load_roster` will
actually load -- and enforces, for EVERY scene, the three things that were
previously proven only per scene, and for scene 3 not proven at all:

  (a) the scene's own kill letter is tied to THAT scene by name in
      ``mob_death.WIDENING_RULING_SCENES``, checked two ways: directly
      against the dict (which cannot be vacuous, because it never walks a
      roster), and by relabelling a REAL roster row to another live scene
      and driving ``mob_death.kill`` on it.  The dict-only check is the one
      that matters most: pf-adversary (round r6isy5) deleted bg0004's tie
      and the WHOLE SUITE stayed green -- 10749 passed, unmoved -- because
      the loop it broke walked the LIVE rosters of the OTHER scenes, none of
      which carried an overlapping template.  A loop over other scenes'
      rosters is exactly that shape again, so this file does not lean on
      one for the fact that actually has to hold.
  (b) the scene's own recompose composer BODY actually runs (not merely
      registered under :func:`mob_scene_recompose.composer_scene_ids`) and
      returns a state in ``mob_scene_recompose.COMPOSING_STATES``.  A table
      entry proves the wiring is complete; only calling the function proves
      it is right -- ``COMPOSER_BG0005: _build_bg0015`` passed the whole
      suite once (round jqeo2m) with the table check alone.
  (c) the composed bytes carry THIS scene's own roster identity, and the
      check is COORDINATES rather than actor-identity bytes: identity is
      ``0x2000 + placement_index + 1`` with no scene term, so a
      neighbouring scene's frame carries most of another scene's identity
      bytes by coincidence (measured, round r6isy5: bg0005's frame carried
      7 of 7 of bg0004's).  Coordinates come from the scene's own placement
      rows and no other's.

SCENE 3 (bg0003) IS NOT SPECIAL-CASED ANYWHERE IN THIS FILE.  On `main`
before this file existed it failed both (a) and (b) silently: deleting its
``WIDENING_RULING_SCENES`` entry and swapping ``_build_bg0003``'s body for
another scene's builder each moved zero tests.  It is expected to be caught,
and to stay caught, by the SAME loop that watches every other scene --
closing it is a side effect of this file existing, not a card of its own
(COO-DECISION item 2).

TWO_SESSIONS_SAME_SCENE: every value this file builds is a local variable
inside one test method, and :func:`mob_scene_recompose.recompose_frames` is
called fresh, once per scene, per test.  Nothing here holds composer state
across scenes or across calls -- this contract tests the composer as a pure
function of (scene, roster, ledger), never as a property of "which session
asked last".  A future round that wires this contract's shape into anything
session-facing must keep that true.

NEW SCENE CHECKLIST, read before this file's table below needs a new row: a
scene only reaches ``field_mobs.live_scenes()`` once its roster table is in
``field_mobs._SCENE_TABLE_MODULES``; it only composes once its composer is
in ``mob_scene_recompose._COMPOSERS``/``_POPULATION_BUILDERS``; it only
kills once its letter is in ``mob_death.WIDENING_RULINGS`` and
``WIDENING_RULING_SCENES``.  Until every one of those exists, THIS FILE
FAILS LOUDLY for that scene, by design -- a new scene that skips one of them
must not be able to register at all.
"""

from __future__ import annotations

import dataclasses
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

from pirateforce_foundation import field_mob_tables  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0002  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0003  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0004  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0005  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0006  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0007  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0008  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0009  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0010  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0011  # noqa: E402
from pirateforce_foundation import field_mob_tables_bg0015  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_scene_recompose  # noqa: E402
from pirateforce_foundation import scene_door_walk  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation import world_population_bg0003  # noqa: E402
from pirateforce_foundation import world_population_bg0004  # noqa: E402
from pirateforce_foundation import world_population_bg0005  # noqa: E402
from pirateforce_foundation import world_population_bg0006  # noqa: E402
from pirateforce_foundation import world_population_bg0007  # noqa: E402
from pirateforce_foundation import world_population_bg0008  # noqa: E402
from pirateforce_foundation import world_population_bg0009  # noqa: E402
from pirateforce_foundation import world_population_bg0010  # noqa: E402
from pirateforce_foundation import world_population_bg0011  # noqa: E402
from pirateforce_foundation import world_population_bg0015  # noqa: E402


V141 = ROOT / "current" / "pf_login_game_server_v141.py"
_LEGACY = None


def _legacy():
    """The project's own frozen-serializer loader, not a hand-rolled one.

    Same helper every other combat-scene test file uses
    (``tests/test_field_mob_tables_bg0004.py`` names the reason: loading
    v141 under an ad-hoc module name breaks ``dataclasses`` on anything that
    touches its classes).
    """
    global _LEGACY
    if _LEGACY is None:
        _LEGACY = load_legacy(V141)
    return _LEGACY


def _outcome_for(mob):
    """A real killing blow on ``mob``, composed by production code.

    Not a hand-built ``HitOutcome``: the point of every test that uses this
    is that a kill would otherwise SUCCEED, so the blow has to be one
    ``mob_death.kill`` would accept if the ruling let it through.
    """
    step = mob_combat.strike(
        _legacy(), None, mob_combat.open_ledger((mob,)), None, mob,
        scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
    return step.outcome


# scene name (``field_mobs.live_scenes()``'s own spelling) -> the population
# module whose builder composes it.  A second table next to
# ``field_mobs._SCENE_TABLE_MODULES``, on purpose: that dict answers "does
# this scene have a roster", not "which module's ``DEFAULT_ACTOR_COUNT``
# is wide enough to carry every one of this scene's placements into the
# arrival census the roster override can then splice into" -- and the two
# questions have different owners (this lane's roster tables vs this
# lane's population builders) and can drift from each other independently.
# f32 coordinate values that legitimately appear in more than one live
# scene, with the evidence for each.  Read the strict companion test
# ``test_no_scene_frame_carries_another_scenes_whole_position`` before adding
# a row here: a single shared float is allowed to be a coincidence, a shared
# (x, y, z) triple never is, and that second test takes no allowances at all.
#
# ROUND 30ja9z, the first and so far only entry.  424.9296875 is the GROUND
# HEIGHT (z) of Bg0011 placements 20 and 49 ("Navy Two Tripods"), and
# Bg0010's arrival census -- not its roster -- carries the same z.  Measured,
# not inferred: the value sits at one offset in Bg0010's composed frame,
# directly behind an f32 tag byte (0x2A) so it is a real aligned payload and
# not an unaligned byte-window coincidence, and it is NOT any Bg0010 roster
# row's own coordinate (`424.9296875 in {row coords}` is False for scene 10,
# True for scene 11).  Bg0010 and Bg0011 are floors 1 and 2 of the same Deep
# Sea Temple; two floors of one building sharing a ground height is what the
# map data says, and neither scene's x or y comes near the other's.
_SHARED_GROUND_HEIGHTS = frozenset({struct.pack("<f", 424.9296875)})

_POPULATION_MODULE_BY_SCENE = {
    field_mob_tables.SCENE: world_population,
    field_mob_tables_bg0002.SCENE: world_population_bg0002,
    field_mob_tables_bg0003.SCENE: world_population_bg0003,
    field_mob_tables_bg0004.SCENE: world_population_bg0004,
    field_mob_tables_bg0005.SCENE: world_population_bg0005,
    field_mob_tables_bg0006.SCENE: world_population_bg0006,
    field_mob_tables_bg0007.SCENE: world_population_bg0007,
    field_mob_tables_bg0008.SCENE: world_population_bg0008,
    field_mob_tables_bg0009.SCENE: world_population_bg0009,
    field_mob_tables_bg0010.SCENE: world_population_bg0010,
    field_mob_tables_bg0011.SCENE: world_population_bg0011,
    field_mob_tables_bg0015.SCENE: world_population_bg0015,
}


def _live_scene_ids():
    """``{scene name: the one scene id addressing it}``, re-derived rather
    than hand-typed, so a scene this lane registers tomorrow is picked up
    with no edit to this file at all -- only the table above, and only
    because a coordinate check needs a module, not because this function
    needs a name.
    """
    mapping = {}
    for scene in field_mobs.live_scenes():
        ids = field_mobs.scene_ids_addressing(scene)
        assert len(ids) == 1, (
            "scene %r is addressed by %d scene ids (%s), not exactly one; "
            "this contract assumes the one-to-one binding "
            "test_field_mobs_scene_binding.py already pins" % (
                scene, len(ids), ids))
        mapping[scene] = ids[0]
    return mapping


class EverySceneKillLetterIsTiedToItsOwnSceneTests(unittest.TestCase):
    """Contract item (a), split into the two halves that each catch a
    different shape of the same defect.
    """

    def test_every_registered_kill_letter_has_a_scene_tie(self) -> None:
        """The direct check.  Never walks a roster, so it cannot be
        vacuously satisfied by one that happens to carry no overlapping
        template -- the exact shape that let bg0004's deleted tie move zero
        of 10749 tests (round r6isy5, pf-adversary D1).
        """
        for name in mob_death.WIDENING_RULINGS:
            with self.subTest(ruling=name):
                self.assertIn(
                    name, mob_death.WIDENING_RULING_SCENES,
                    "%r covers a template set with no scene tie -- a mob "
                    "carrying one of its templates in ANY scene would be "
                    "killable under it" % (name,))

    def test_every_live_scenes_own_roster_ties_to_itself(self) -> None:
        """Every live scene's own roster resolves to a ruling that is tied
        BACK to that same scene -- re-derived from the roster that ships,
        not from a hand-typed list of scene/ruling pairs.
        """
        live_ids = _live_scene_ids()
        for scene, scene_id in live_ids.items():
            with self.subTest(scene=scene):
                roster = field_mobs.roster_for_scene_id(scene_id)
                self.assertTrue(
                    roster,
                    "scene %r is live in field_mobs.live_scenes() and ships "
                    "no roster row through its own scene id %d" % (
                        scene, scene_id))
                for mob in roster:
                    with self.subTest(identity=hex(mob.actor_identity)):
                        ruling = mob_death.ruling_for(mob)
                        self.assertIsNotNone(
                            ruling,
                            "identity 0x%X in scene %r resolves to the "
                            "sanctioned-bypass mob with no ruling at all; "
                            "that is only legal for "
                            "mob_death.SANCTIONED_FIRST_TARGET_SCENE"
                            % (mob.actor_identity, scene))
                        self.assertEqual(
                            mob_death.WIDENING_RULING_SCENES.get(ruling),
                            scene,
                            "ruling %r covers this row but is tied to scene "
                            "%r, not %r" % (
                                ruling,
                                mob_death.WIDENING_RULING_SCENES.get(ruling),
                                scene))

    def test_a_row_wearing_another_live_scenes_name_is_refused_by_kill(
            self) -> None:
        """The row driven all the way to ``mob_death.kill``, on every
        ORDERED (scene, other_scene) pair among live scenes -- not just one
        hand-picked impersonation target per scene, and not just read off
        ``rulings_covering``.  This is the shape pf-adversary drove to
        completion on bg0004 (D1): with the tie deleted, a relabelled row is
        not merely mis-scoped in a helper function, it is KILLABLE, 167
        bytes on the wire, register says dead.

        Walking every ordered pair, the same way
        ``test_the_coordinate_check_is_not_vacuous_across_every_scene_pair``
        does two methods below, is load-bearing, not belt-and-suspenders:
        pf-adversary (this round) found that a single ``next(...)`` pick
        left five of six live scenes never used as an impersonation target,
        and a scene-specific carve-out in ``mob_death.kill`` for exactly one
        of the untested targets passed this file's suite at 100% -- caught
        only by an unrelated, incidentally-exhaustive per-scene test file
        this contract's own docstring treats as no longer load-bearing.
        """
        live_ids = _live_scene_ids()
        for scene, scene_id in live_ids.items():
            roster = field_mobs.roster_for_scene_id(scene_id)
            for other_scene in live_ids:
                if other_scene == scene:
                    continue
                for mob in roster:
                    if (mob.actor_identity
                            == mob_death.SANCTIONED_FIRST_TARGET_IDENTITY
                            and other_scene
                            == mob_death.SANCTIONED_FIRST_TARGET_SCENE):
                        # mob_death.kill()'s own documented, narrow bootstrap
                        # exception: identity 0x201F relabelled to scene
                        # "bg0001" is EXACTLY the sanctioned first target, so
                        # it bypasses every widened-ruling/scene check on
                        # purpose (see kill()'s "SANCTIONED BYPASS" comment) --
                        # this is the one case this contract does not claim
                        # is a scene-tie bug, because production names it and
                        # explains it, rather than this file inventing a new
                        # exception of its own.
                        continue
                    ruling = mob_death.ruling_for(mob)
                    relabelled = dataclasses.replace(mob, scene=other_scene)
                    with self.subTest(scene=scene, other_scene=other_scene,
                                       identity=hex(mob.actor_identity)):
                        self.assertNotIn(
                            ruling, mob_death.rulings_covering(relabelled),
                            "relabelling scene %r's own identity 0x%X to "
                            "scene %r still leaves it covered by %r" % (
                                scene, mob.actor_identity, other_scene,
                                ruling))
                        with self.assertRaises(
                                mob_death.MobDeathContractError) as box:
                            mob_death.kill(
                                _legacy(), relabelled,
                                _outcome_for(relabelled), widened=ruling)
                        self.assertIn(
                            "target_outside_the_sanctioned_scope",
                            str(box.exception))


class EverySceneComposerActuallyRunsTests(unittest.TestCase):
    """Contract items (b) and (c): the composer BODY, not its registration."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.live_ids = _live_scene_ids()
        cls.records = {}
        for scene, scene_id in cls.live_ids.items():
            module = _POPULATION_MODULE_BY_SCENE.get(scene)
            assert module is not None, (
                "scene %r is live in field_mobs.live_scenes() and this "
                "contract's own population-module table (see this file's "
                "_POPULATION_MODULE_BY_SCENE) does not know it yet -- add "
                "a row before this scene can pass the per-scene contract"
                % (scene,))
            anchor = mob_scene_recompose.census_anchor(
                scene_id, (0.0, 0.0, 0.0), module.DEFAULT_ACTOR_COUNT,
            )
            cls.records[scene] = mob_scene_recompose.recompose_frames(
                _legacy(), anchor, mob_death.DeathRegister(),
                ledger=mob_combat.open_ledger_for_scene_id(scene_id),
            )

    def test_every_live_scene_has_a_registered_composer(self) -> None:
        for scene, scene_id in self.live_ids.items():
            with self.subTest(scene=scene):
                self.assertIn(
                    scene_id, mob_scene_recompose.composer_scene_ids(),
                    "scene %r ships a roster and has no recompose composer "
                    "at all -- every hit and kill in it falls to the "
                    "one-entry world-wipe fallback RE-092 named" % (scene,))

    def test_every_composer_body_actually_runs_and_composes(self) -> None:
        """Registration alone proved nothing for scenes 3 and 5 in round
        jqeo2m (``COMPOSER_BG0005: _build_bg0015`` passed the whole suite);
        this calls the real function and reads its real answer.
        """
        for scene in self.live_ids:
            record = self.records[scene]
            with self.subTest(scene=scene):
                self.assertIn(
                    record.state, mob_scene_recompose.COMPOSING_STATES,
                    "scene %r's composer ran and returned %r, which is not "
                    "a state runtime.py's call site may send -- it falls "
                    "back to the one-entry world-wipe frame instead"
                    % (scene, record.state))
                self.assertTrue(record.pc)
                self.assertTrue(record.frame)

    def test_every_composed_frame_carries_its_own_scenes_coordinates(
            self) -> None:
        """The discriminating half of (c).  Necessary but only sufficient
        together with the state check above: a wrong-builder mutant that
        raises before composing anything is caught by ``record.state``
        alone (see the class above); a builder that silently composed a
        DIFFERENT scene while still returning a composing state is caught
        here, because that scene's own placement coordinates would be
        missing.
        """
        for scene, scene_id in self.live_ids.items():
            record = self.records[scene]
            for mob in field_mobs.roster_for_scene_id(scene_id):
                for axis, value in (("x", mob.x), ("y", mob.y), ("z", mob.z)):
                    with self.subTest(
                            scene=scene, identity=hex(mob.actor_identity),
                            axis=axis):
                        self.assertIn(
                            struct.pack("<f", value), record.frame,
                            "scene %r's composed frame does not carry its "
                            "own roster row 0x%X's %s coordinate -- the "
                            "composer body ran, but it did not compose "
                            "THIS scene's census"
                            % (scene, mob.actor_identity, axis))

    def test_the_coordinate_check_is_not_vacuous_across_every_scene_pair(
            self) -> None:
        """The control bg0004's own card demanded (pf-adversary D2): a
        neighbouring scene's frame must NOT carry this scene's coordinates,
        walked over every ordered pair of live scenes rather than one
        hand-picked neighbour, so the next scene this project ships is
        covered by the same measurement and not merely by analogy to it.
        """
        for scene, scene_id in self.live_ids.items():
            own_coordinates = {
                struct.pack("<f", value)
                for mob in field_mobs.roster_for_scene_id(scene_id)
                for value in (mob.x, mob.y, mob.z)
            }
            for other_scene, other_record in self.records.items():
                if other_scene == scene:
                    continue
                if not other_record.frame:
                    # A non-composing neighbour is already a failure of
                    # test_every_composer_body_actually_runs_and_composes
                    # above; this control is only about discrimination
                    # between two frames that both exist.
                    continue
                with self.subTest(scene=scene, neighbour=other_scene):
                    leaked = (own_coordinates - _SHARED_GROUND_HEIGHTS) & {
                        other_record.frame[i:i + 4]
                        for i in range(len(other_record.frame) - 3)
                    }
                    self.assertFalse(
                        leaked,
                        "scene %r's frame carries %d of scene %r's own "
                        "coordinate values -- the check above is not "
                        "discriminating after all" % (
                            other_scene, len(leaked), scene))

    def test_no_scene_frame_carries_another_scenes_whole_position(
            self) -> None:
        """The strict half of the control above, and the reason the one
        allowance in ``_SHARED_GROUND_HEIGHTS`` costs nothing.

        A single shared f32 can be an ordinary coincidence -- two maps built
        on the same ground height carry the same z, and nothing follows from
        it.  A shared (x, y, z) TRIPLE cannot: that is one actor standing at
        another scene's exact placement, which is the failure the control
        above exists to detect.  This walks the same ordered pairs with no
        allowance of any kind, so relaxing that one z value cannot hide a
        real leak: the leak this file is afraid of would have to move all
        three axes, and this test refuses all three.
        """
        for scene, scene_id in self.live_ids.items():
            own_positions = {
                struct.pack("<f", mob.x) + struct.pack("<f", mob.y)
                + struct.pack("<f", mob.z)
                for mob in field_mobs.roster_for_scene_id(scene_id)
            }
            self.assertTrue(own_positions, scene)
            for other_scene, other_record in self.records.items():
                if other_scene == scene or not other_record.frame:
                    continue
                with self.subTest(scene=scene, neighbour=other_scene):
                    for position in own_positions:
                        self.assertNotIn(
                            position, other_record.frame,
                            "scene %r's frame carries a whole (x, y, z) "
                            "position belonging to scene %r" % (
                                other_scene, scene))
