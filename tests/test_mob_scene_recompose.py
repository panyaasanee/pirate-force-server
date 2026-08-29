"""LANE-B round y9s0xo -- the scene-dispatched recompose census.

WHAT THESE TESTS ARE FOR.  ``mob_scene_recompose`` exists so that a hit or a
kill in Bg0002 stops shipping the ONE-ENTRY frame ``RE-092`` proved is
replace-by-omission.  Two claims carry that, and both are pinned here against
the REAL tables and the REAL frozen serializer, never a fake:

  1. the scene-1 path is BYTE-IDENTICAL to the composer that is live today
     (``diag_multi_object_wiring.hostile_census_frames``), so wiring the new
     module cannot change what Port Royal already sends; and
  2. the scene-2 path composes the SAME census arrival composes -- byte for
     byte when nothing has happened yet -- and differs from it in exactly the
     entries of the monsters something HAS happened to.

The second one is the load-bearing pin of the round: "a recompose is a
refresh, not a membership change" is the sentence, and a byte comparison
against the arrival path is the only way to say it that a mutant cannot
satisfy by accident.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import diag_multi_object_wiring  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_census_hostility  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_ledger_admission  # noqa: E402
from pirateforce_foundation import mob_scene_recompose as recompose  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation import world_population_bg0002  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.runtime import (  # noqa: E402
    _apply_mob_death_census_override,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
ANCHOR = (10.0, 20.0, 30.0)
SCENE1 = world_population.SCENE_ID
SCENE2 = world_population_bg0002.SCENE2_N_ID
# The ruling that authorises killing the roster's control row, quoted from
# tests/test_mob_ai_control.py rather than invented here.
WIDENING_RULING = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)"
)


def _entries(pc: bytes, generation) -> list[bytes]:
    """Per-actor entry bytes of a built collection, in wire order."""
    offset = world_population.WIRE_HEADER_BYTES
    out = []
    for length in generation.entry_bytes:
        out.append(pc[offset:offset + length])
        offset += length
    return out


class SceneRecomposeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.roster1 = field_mobs.roster_for_scene_id(SCENE1)
        cls.roster2 = field_mobs.roster_for_scene_id(SCENE2)
        cls.ledger1 = mob_combat.open_ledger_for_scene_id(SCENE1)
        cls.ledger2 = mob_combat.open_ledger_for_scene_id(SCENE2)
        cls.anchor1 = recompose.census_anchor(
            SCENE1, ANCHOR, world_population.CENSUS_COUNT)
        cls.anchor2 = recompose.census_anchor(
            SCENE2, ANCHOR, world_population_bg0002.DEFAULT_ACTOR_COUNT)

    def setUp(self):
        self.register = mob_death.DeathRegister()

    # -- 1. the scene-1 path is the live one, not a second implementation ---

    def test_scene_1_is_byte_identical_to_the_composer_live_today(self):
        live_pc, live_frame = diag_multi_object_wiring.hostile_census_frames(
            self.legacy, ANCHOR, world_population.CENSUS_COUNT, self.roster1,
            self.register, ledger=self.ledger1, objects=(),
        )
        record = recompose.recompose_frames(
            self.legacy, self.anchor1, self.register, ledger=self.ledger1)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        self.assertEqual(record.pc, live_pc)
        self.assertEqual(record.frame, live_frame)

    def test_scene_1_dying_and_dead_timers_reach_the_live_composer(self):
        """A mutant that drops ``dead_timer`` on the way through would ship
        the DEAD frame for a DYING transition and no byte pin above would
        notice, because both are full censuses of the same membership."""
        register, ledger = self._register_with_a_real_corpse()
        both = {}
        for timer in (mob_death.DYING_TIMER_SECONDS, mob_death.DEAD_TIMER_SECONDS):
            record = recompose.recompose_frames(
                self.legacy, self.anchor1, register,
                ledger=ledger, dead_timer=timer)
            self.assertEqual(record.state, recompose.STATE_COMPOSED)
            both[timer] = record.pc
            self.assertEqual(record.dead_timer, timer)
        self.assertNotEqual(
            both[mob_death.DYING_TIMER_SECONDS],
            both[mob_death.DEAD_TIMER_SECONDS],
            "the dying and dead frames are identical: dead_timer is not "
            "reaching the composer",
        )

    def _register_with_a_real_corpse(self):
        """One committed corpse, through strike -> kill -> commit_death, WITH
        the ledger that kill left behind.

        The control row and the ruling that authorises killing it, exactly as
        ``tests/test_mob_ai_control.py`` drives them -- no synthetic register,
        because a corpse this lane invented would prove nothing about the
        register the runtime actually holds.

        THE LEDGER COMES BACK WITH IT AND THAT IS NOT A CONVENIENCE.  Handing
        the post-kill register to a ledger that still has the mob at its
        ceiling is the pair ``repopulation_entries`` refuses by name
        (``ledger_disagrees_with_register``) -- measured while writing this
        test, which is exactly the state ``mob_ledger_admission`` calls
        ``same_scene_incomplete``'s cousin: the two halves of a session
        disagreeing about whether something is dead.
        """
        mob = [
            m for m in self.roster1
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]
        step = mob_combat.strike(
            self.legacy, None, self.ledger1, None, mob, 0x1001,
            mob_combat.Combatant(level=1000, ability_str=100000, ability_con=0),
        )
        self.assertTrue(step.outcome.death_due)
        register = mob_death.DeathRegister()
        death = mob_death.kill(
            self.legacy, mob, step.outcome, register, widened=WIDENING_RULING)
        return mob_death.commit_death(register, death), step.ledger

    # -- 2. the scene-2 path: a refresh, not a membership change ------------

    def test_scene_2_untouched_recompose_equals_the_arrival_census(self):
        """THE LOAD-BEARING PIN.  With nothing hit and nothing dead, the
        recompose must reproduce the bytes arrival already sent -- otherwise
        the first swing in Bg0002 changes the world for a reason unrelated to
        the swing."""
        generation = world_population_bg0002.build_bg0002_population(
            self.legacy, ANCHOR, scene_id=SCENE2,
            count_source=world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
        )
        override = mob_census_hostility.hostile_override_for_scene_id(
            self.legacy, SCENE2, self.register, ledger=self.ledger2)
        arrival = _apply_mob_death_census_override(
            self.legacy, generation, override)
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        self.assertEqual(record.pc, arrival.pc)
        self.assertEqual(record.frame, arrival.frame)

    def test_scene_2_carries_the_whole_census_not_one_entry(self):
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        self.assertEqual(
            record.wire_actor_count,
            world_population_bg0002.DEFAULT_ACTOR_COUNT)
        self.assertEqual(record.actor_count, record.wire_actor_count)
        self.assertGreater(record.wire_actor_count, 1)

    def test_scene_2_a_wound_survives_and_touches_only_that_actor(self):
        target = self.roster2[0]
        wounded = self.ledger2.with_balance(mob_combat.MobBalance(
            target.actor_identity, target.max_hp, target.max_hp // 2))
        ceiling = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        hurt = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=wounded)
        self.assertNotEqual(ceiling.pc, hurt.pc)
        self.assertEqual(ceiling.wire_actor_count, hurt.wire_actor_count)

        # The per-actor walk has to use EACH composition's OWN entry lengths.
        # Walking both with the unspliced generation's lengths (the first
        # draft of this test) reports the wrong identity as the changed one --
        # a hostile body is a different size from the plain one, so every
        # offset after the first spliced entry is shifted.  The bug was in
        # the test, and it would have been read as a product defect.
        generation = world_population_bg0002.build_bg0002_population(
            self.legacy, ANCHOR,
            world_population_bg0002.DEFAULT_ACTOR_COUNT, scene_id=SCENE2,
            count_source=world_population_bg0002.COUNT_SOURCE_CALLER,
        )
        identities = generation.actor_identities
        composed = {}
        for label, ledger in (("before", self.ledger2), ("after", wounded)):
            override = mob_death.full_roster_override(
                self.legacy, self.roster2, self.register, ledger=ledger)
            spliced = recompose.splice_identity_override(
                self.legacy, generation, override)
            composed[label] = _entries(spliced.pc, spliced)
        self.assertEqual(ceiling.pc, self.legacy.make_runtime_remote_actors(
            composed["before"])[0])
        before, after = composed["before"], composed["after"]
        self.assertEqual(len(before), len(after))
        differing = {
            identities[i] for i in range(len(before)) if before[i] != after[i]
        }
        self.assertEqual(
            differing, {target.actor_identity},
            "a wound on one monster changed another monster's body",
        )

    def test_the_count_source_is_reported_and_is_the_callers_not_the_rosters(self):
        """THIS PIN EXISTS BECAUSE OF THIS ROUND'S OWN MUTATION SWEEP (M15).

        Changing the scene-2 build from ``COUNT_SOURCE_CALLER`` to
        ``COUNT_SOURCE_FULL_ROSTER`` SURVIVED the whole suite: the argument
        changes no bytes, so the paragraph in ``_compose`` explaining the
        choice was guarding nothing.  The provenance of the count is a real
        fact about the frame -- ``world_population_bg0002.dispatch_report``
        builds its ``shortfall`` string out of it -- so it is reported on the
        record and the console line, where a wrong value is visible.
        """
        for anchor in (self.anchor1, self.anchor2):
            record = recompose.recompose_frames(
                self.legacy, anchor, self.register,
                ledger=(self.ledger1 if anchor is self.anchor1
                        else self.ledger2))
            self.assertEqual(record.state, recompose.STATE_COMPOSED)
            self.assertEqual(
                record.count_source,
                world_population.COUNT_SOURCE_CALLER,
                "a recompose sends the count the caller committed at "
                "arrival, and must say so",
            )
            self.assertIn(
                "source=%s" % world_population.COUNT_SOURCE_CALLER,
                recompose.describe_recompose(record)[0])
        self.assertNotEqual(
            world_population.COUNT_SOURCE_CALLER,
            world_population_bg0002.COUNT_SOURCE_FULL_ROSTER,
            "the two sources must stay distinguishable for this pin to bite",
        )

    def test_scene_2_membership_follows_the_anchor_count(self):
        """A recompose sends the count ARRIVAL committed.  A composer that
        silently re-derived the full roster count would resend a different
        world than the one on screen."""
        narrow = recompose.census_anchor(SCENE2, ANCHOR, 40)
        record = recompose.recompose_frames(
            self.legacy, narrow, self.register, ledger=self.ledger2)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        self.assertEqual(record.wire_actor_count, 40)
        self.assertEqual(record.requested_count, 40)

    # -- 3. the splice, pinned against the frozen one ----------------------

    def test_the_generic_splice_is_byte_identical_to_the_frozen_one(self):
        generation = world_population.build_world_population(
            self.legacy, ANCHOR, world_population.CENSUS_COUNT,
            scene_id=SCENE1,
            count_source=world_population.COUNT_SOURCE_CALLER,
        )
        override = mob_death.full_roster_override(
            self.legacy, self.roster1, self.register, ledger=self.ledger1)
        self.assertTrue(override, "an empty override would prove nothing")
        frozen = world_population.apply_identity_override(
            self.legacy, generation, override)
        mine = recompose.splice_identity_override(
            self.legacy, generation, override)
        self.assertEqual(frozen.pc, mine.pc)
        self.assertEqual(frozen.frame, mine.frame)
        self.assertEqual(frozen.entry_bytes, mine.entry_bytes)

    def test_the_splice_returns_the_generation_untouched_for_no_override(self):
        generation = world_population_bg0002.build_bg0002_population(
            self.legacy, ANCHOR, scene_id=SCENE2)
        self.assertIs(
            recompose.splice_identity_override(self.legacy, generation, {}),
            generation)

    def test_the_splice_refuses_a_generation_that_is_not_one(self):
        with self.assertRaises(recompose.SceneRecomposeError):
            recompose.splice_identity_override(self.legacy, object(), {1: b"x"})

    def test_the_splice_refuses_lengths_that_do_not_cover_the_collection(self):
        generation = world_population_bg0002.build_bg0002_population(
            self.legacy, ANCHOR, scene_id=SCENE2)
        short = type(generation)(
            **{**generation.__dict__,
               "entry_bytes": generation.entry_bytes[:-1] + (1,)}
        )
        with self.assertRaises(recompose.SceneRecomposeError):
            recompose.splice_identity_override(
                self.legacy, short, {generation.actor_identities[0]: b"\x01"})

    # -- 4. the ledger ban (item 1 of the chief's division) ----------------

    def test_the_ledger_keyword_has_no_default_at_all(self):
        with self.assertRaises(TypeError):
            recompose.recompose_frames(
                self.legacy, self.anchor2, self.register)

    def test_the_scene_census_override_ledger_keyword_has_no_default(self):
        with self.assertRaises(TypeError):
            mob_census_hostility.hostile_override_for_scene_id(
                self.legacy, SCENE2, self.register)

    def test_an_explicit_none_ledger_is_refused_loudly_and_composes_nothing(self):
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=None)
        self.assertEqual(record.state, recompose.STATE_NO_LEDGER)
        self.assertTrue(record.fatal)
        self.assertIsNone(record.pc)
        self.assertIsNone(record.frame)
        lines = recompose.describe_recompose(record)
        self.assertTrue(
            any(line.startswith(mob_ledger_admission.FATAL_TOKEN)
                for line in lines),
            lines)

    def test_an_explicit_none_ledger_still_means_ceiling_hp_on_the_arrival_path(self):
        """The ban is on the DEFAULT, not on the meaning.  A scene arriving
        before any combat still composes at ceiling HP by saying so."""
        override = mob_census_hostility.hostile_override_for_scene_id(
            self.legacy, SCENE2, self.register, ledger=None)
        self.assertEqual(len(override), len(self.roster2))

    # -- 5. every refusal is a record, never an escape ---------------------

    def test_a_foreign_ledger_composes_at_ceiling_and_says_so(self):
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger1)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        self.assertEqual(
            record.ledger_state, mob_ledger_admission.STATE_OTHER_SCENE)
        clean = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        self.assertEqual(record.pc, clean.pc)

    def test_a_composition_that_refuses_comes_back_as_a_record(self):
        """Scene 1 delegates to a composer that RAISES on a ledger it cannot
        use (measured: ``target_not_in_ledger`` at 0x2068).  The point of
        this module is that the listener thread never sees it."""
        record = recompose.recompose_frames(
            self.legacy, self.anchor1, self.register, ledger=self.ledger2)
        self.assertTrue(
            record.state.startswith(recompose.STATE_REFUSED_PREFIX), record.state)
        self.assertIsNone(record.pc)
        self.assertIn("MobDeathContractError", record.state)

    def test_a_scene_with_no_composer_is_a_named_answer(self):
        record = recompose.recompose_frames(
            self.legacy, recompose.census_anchor(9, ANCHOR, 10),
            self.register, ledger=self.ledger2)
        self.assertEqual(record.state, recompose.STATE_NO_COMPOSER)
        self.assertIsNone(record.pc)

    def test_the_diagnostic_objects_are_refused_outside_scene_1(self):
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2,
            objects=("anything at all",))
        self.assertTrue(record.state.startswith(recompose.STATE_REFUSED_PREFIX))
        self.assertIsNone(record.pc)

    # -- 6. the anchor carries its scene ------------------------------------

    def test_a_bare_tuple_anchor_is_refused_at_the_door(self):
        with self.assertRaises(recompose.SceneRecomposeError):
            recompose.recompose_frames(
                self.legacy, ANCHOR, self.register, ledger=self.ledger2)

    def test_a_roster_that_is_not_one_is_refused_before_anything_is_composed(self):
        """The admission walks ``mob.actor_identity`` over these rows outside
        the composition's own try, so rows that are not roster rows would
        escape as an AttributeError past the never-raises contract."""
        for bad in (["not a row"], ("not a row",), object(), 7):
            with self.assertRaises(recompose.SceneRecomposeError, msg=repr(bad)):
                recompose.recompose_frames(
                    self.legacy, self.anchor2, self.register,
                    ledger=self.ledger2, roster=bad)

    def test_census_anchor_refuses_every_shape_that_is_not_one(self):
        for bad in (
            (SCENE2, [1.0, 2.0, 3.0], 97),          # a list, not a tuple
            (SCENE2, (1.0, 2.0), 97),               # two axes
            (SCENE2, (1.0, 2.0, float("nan")), 97),  # not finite
            (SCENE2, (1.0, 2.0, float("inf")), 97),
            (SCENE2, (1.0, 2.0, True), 97),         # a bool is not a coordinate
            (SCENE2, ANCHOR, 0),                    # a census of nobody
            (SCENE2, ANCHOR, 97.0),                 # a float count
            (SCENE2, ANCHOR, True),
            (True, ANCHOR, 97),                     # a bool scene id
        ):
            with self.assertRaises(recompose.SceneRecomposeError, msg=repr(bad)):
                recompose.census_anchor(*bad)

    def test_the_anchor_decides_the_scene_not_the_ledger(self):
        """Two anchors, one ledger: the composition follows the anchor.  A
        mutant that read the scene off the ledger would pass every scene-2
        test above and put Prison Exile bodies in Port Royal."""
        record = recompose.recompose_frames(
            self.legacy, self.anchor1, self.register, ledger=self.ledger1)
        self.assertEqual(record.scene_id, SCENE1)
        self.assertNotEqual(record.wire_actor_count,
                            world_population_bg0002.DEFAULT_ACTOR_COUNT)

    # -- 7. the console line (G-OBS) ---------------------------------------

    def test_every_state_prints_a_line_and_all_of_them_are_ascii(self):
        records = [
            recompose.recompose_frames(
                self.legacy, self.anchor2, self.register, ledger=self.ledger2),
            recompose.recompose_frames(
                self.legacy, self.anchor2, self.register, ledger=None),
            recompose.recompose_frames(
                self.legacy, recompose.census_anchor(9, ANCHOR, 10),
                self.register, ledger=self.ledger2),
            recompose.recompose_frames(
                self.legacy, self.anchor1, self.register, ledger=self.ledger2),
        ]
        for record in records:
            lines = recompose.describe_recompose(record)
            self.assertTrue(lines, record.state)
            for line in lines:
                line.encode("ascii")
                self.assertNotIn("\n", line)
            self.assertTrue(
                lines[0].startswith(recompose.CONSOLE_TOKEN), lines[0])
            self.assertIn("state=%s" % record.state, lines[0])

    def test_the_line_does_not_cry_mismatch_on_a_healthy_scene_1_recompose(self):
        """MEASURED, round y9s0xo: scene 1 requests 115 and puts 108 bodies on
        the wire (the BUILD-001 data ceiling).  An alarm that fires on the
        normal case is an alarm a tester learns to ignore."""
        record = recompose.recompose_frames(
            self.legacy, self.anchor1, self.register, ledger=self.ledger1)
        line = recompose.describe_recompose(record)[0]
        self.assertNotIn("MISMATCH", line)
        self.assertIn("requested=%d" % world_population.CENSUS_COUNT, line)

    def test_the_line_does_cry_mismatch_when_a_composer_contradicts_its_bytes(self):
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        lying = type(record)(
            **{**record.__dict__, "actor_count": record.wire_actor_count + 1})
        self.assertIn("MISMATCH", recompose.describe_recompose(lying)[0])

    def test_something_that_is_not_a_record_is_described_not_raised_on(self):
        lines = recompose.describe_recompose({"state": "composed"})
        self.assertTrue(lines[0].startswith(recompose.CONSOLE_TOKEN))
        self.assertIn("undescribable", lines[0])

    def test_the_module_prints_nothing_by_itself(self):
        """A composer that printed would print once per hit, per session."""
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            recompose.recompose_frames(
                self.legacy, self.anchor2, self.register, ledger=self.ledger2)
        self.assertEqual(stream.getvalue(), "")

    # -- 8. the registry itself --------------------------------------------

    def test_the_composer_table_agrees_with_itself(self):
        for scene_id in recompose.composer_scene_ids():
            composer = recompose.composer_for_scene_id(scene_id)
            self.assertEqual(composer.scene_id, scene_id)
            self.assertIn(
                composer.kind,
                (recompose.COMPOSER_DELEGATED, recompose.COMPOSER_BG0002))

    def test_every_scene_this_lane_ships_monsters_for_can_be_recomposed(self):
        """The drift pin.  A future scene that gains a roster -- and therefore
        a combat ledger, and therefore hits -- but no recompose composer would
        ship the one-entry world-wipe frame on its first swing, silently.
        This is the test that turns that day red."""
        with_monsters = {
            scene_id for scene_id in range(0, 1000)
            if field_mobs.roster_for_scene_id(scene_id)
        }
        self.assertTrue(with_monsters)
        self.assertEqual(
            with_monsters - set(recompose.composer_scene_ids()), set(),
            "a scene ships monsters and has no recompose composer",
        )

    def test_the_module_is_not_flag_gated(self):
        self.assertIs(recompose.production_allowed, True)
        self.assertIs(recompose.test_only, False)


if __name__ == "__main__":
    unittest.main()
