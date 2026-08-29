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
        """~~``self.assertEqual(record.state, recompose.STATE_COMPOSED)``~~
        CORRECTED ROUND le2dox.  This test was written in round y9s0xo with
        the right title and the wrong pin: it asserted the state a clean
        compose reports, so the only thing "saying so" was ``ledger_state``
        on a console field a reader had to know to correlate.  The bytes it
        pins below are unchanged and still right -- the state is what was
        lying.  See ``DeclinedLedgerHealsTests``."""
        record = recompose.recompose_frames(
            self.legacy, self.anchor2, self.register, ledger=self.ledger1)
        self.assertEqual(record.state, recompose.STATE_COMPOSED_HEALING)
        self.assertIs(record.heals, True)
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


class DeclinedLedgerHealsTests(unittest.TestCase):
    """ROUND le2dox.  A ledger the admission DECLINES composed the scene-2
    census at ceiling HP, reported ``composed``, and said nothing.

    The pins here are all BYTE pins against the two frames that bracket the
    question -- the census composed from the ledger as it really is, and the
    census composed from an untouched one.  "Heals" is not an adjective in
    this file: it is ``frame == the ceiling frame``.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)
        cls.roster = field_mobs.roster_for_scene_id(SCENE2)
        cls.anchor = recompose.census_anchor(
            SCENE2, ANCHOR, world_population_bg0002.DEFAULT_ACTOR_COUNT)

    def setUp(self):
        self.register = mob_death.DeathRegister()
        self.ceiling_ledger = mob_combat.open_ledger_for_scene_id(SCENE2)
        self.first = self.roster[0]
        balance = self.ceiling_ledger.balance_of(self.first.actor_identity)
        self.max_hp = balance.max_hp
        self.wounded_ledger = self.ceiling_ledger.with_balance(
            mob_combat.MobBalance(
                self.first.actor_identity, self.max_hp, self.max_hp // 3))

    def _recompose(self, ledger, register=None):
        return recompose.recompose_frames(
            self.legacy, self.anchor, register or self.register,
            ledger=ledger, roster=self.roster)

    def _ceiling_frame(self):
        return self._recompose(self.ceiling_ledger).frame

    def _declined_incomplete(self):
        """A same-scene ledger missing one roster row, wounded on another.

        This is the shape the defect actually reaches production in: the
        admission declines for containment, and the row it CAN read is the
        one whose HP the client is looking at.
        """
        short = mob_combat.open_ledger(self.roster[:-1])
        return short.with_balance(mob_combat.MobBalance(
            self.first.actor_identity, self.max_hp, self.max_hp // 3))

    # -- what the defect was --------------------------------------------

    def test_a_wounded_admitted_ledger_does_not_send_the_ceiling_frame(self):
        """The control.  Without this the healing pins below would pass on a
        composer that ignores the ledger entirely."""
        self.assertNotEqual(
            self._recompose(self.wounded_ledger).frame, self._ceiling_frame())

    def test_a_declined_ledger_still_sends_the_ceiling_frame(self):
        """MEASURED, and the bytes are deliberately NOT changed by this
        round: the fallback for a non-composing record is the one-entry
        world-wipe frame, so refusing here would trade one wrong HP bar for
        every actor in the map."""
        for tag, ledger in (
            ("other scene", mob_combat.open_ledger_for_scene_id(SCENE1)),
            ("incomplete", self._declined_incomplete()),
        ):
            with self.subTest(tag):
                self.assertEqual(
                    self._recompose(ledger).frame, self._ceiling_frame())

    def test_a_declined_ledger_no_longer_reports_itself_as_composed(self):
        record = self._recompose(self._declined_incomplete())
        self.assertEqual(record.state, recompose.STATE_COMPOSED_HEALING)
        self.assertIs(record.heals, True)

    def test_the_healing_record_is_still_sendable(self):
        """The mutant this kills is the obvious fix: give the healing state
        its own name and let ``composed`` stay an equality test.  The call
        site's ``if record.composed`` would then take the fallback arm, and
        the round that set out to stop one HP bar healing would have started
        erasing the whole map instead."""
        record = self._recompose(self._declined_incomplete())
        self.assertIs(record.composed, True)
        self.assertIsNotNone(record.frame)
        self.assertIn(record.state, recompose.COMPOSING_STATES)

    def test_an_admitted_ledger_never_claims_to_heal(self):
        record = self._recompose(self.wounded_ledger)
        self.assertEqual(record.state, recompose.STATE_COMPOSED)
        self.assertIs(record.heals, False)
        self.assertIsNone(record.healed_identities)

    # -- what it counts, and what it refuses to count --------------------

    def test_the_healed_identities_are_measured_when_the_ledger_is_readable(
            self):
        """A same-scene ledger that covers the roster but contradicts the
        death register: declined by D1, every row still readable."""
        lying = self.ceiling_ledger.with_balance(mob_combat.MobBalance(
            self.first.actor_identity, self.max_hp, 0))
        record = self._recompose(lying)
        self.assertIs(record.heals, True)
        self.assertEqual(
            record.healed_identities, (self.first.actor_identity,))

    def test_a_foreign_ledger_reports_unmeasured_and_never_zero(self):
        """Another scene's rows carry another scene's HP under identity
        numbers that collide with these.  ``0`` here would be a number a
        reader trusts; ``None`` makes them look."""
        record = self._recompose(mob_combat.open_ledger_for_scene_id(SCENE1))
        self.assertIs(record.heals, True)
        self.assertIsNone(record.healed_identities)

    def test_the_console_line_says_which_identities_and_says_unmeasured(self):
        readable = self._recompose(self.ceiling_ledger.with_balance(
            mob_combat.MobBalance(self.first.actor_identity, self.max_hp, 0)))
        lines = recompose.describe_recompose(readable)
        self.assertTrue(any(
            line.startswith(mob_ledger_admission.FATAL_TOKEN)
            and "effect=wounded_rows_resent_at_ceiling" in line
            and "0x%04X" % self.first.actor_identity in line
            for line in lines), lines)
        self.assertTrue(any("heals=1" in line for line in lines), lines)

        foreign = self._recompose(mob_combat.open_ledger_for_scene_id(SCENE1))
        lines = recompose.describe_recompose(foreign)
        self.assertTrue(any(
            "identities=unmeasured" in line for line in lines), lines)
        self.assertTrue(
            any("heals=unmeasured" in line for line in lines), lines)

    def test_a_healthy_recompose_prints_no_fatal_line(self):
        """The alarm must not fire on the normal case, or a tester learns to
        ignore it -- the lesson this module already recorded once about
        ``wire=MISMATCH``."""
        lines = recompose.describe_recompose(
            self._recompose(self.wounded_ledger))
        self.assertFalse([
            line for line in lines
            if line.startswith(mob_ledger_admission.FATAL_TOKEN)], lines)
        self.assertTrue(any("heals=no" in line for line in lines), lines)

    # -- the register argument that was never passed ---------------------

    def test_the_recompose_path_measures_the_death_register(self):
        """``admit_ledger``'s own docstring names this path as the one that
        must check D1 -- "the path that can actually raise is the path that
        can always check" -- and this function held the register and passed
        it to the composer without ever passing it to the admission.  The
        mutant that removes the keyword again puts the record back to
        ``refused_MobDeathContractError`` with no bytes at all."""
        lying = self.ceiling_ledger.with_balance(mob_combat.MobBalance(
            self.first.actor_identity, self.max_hp, 0))
        with_register = mob_ledger_admission.require_ledger_for_recompose(
            SCENE2, lying, roster=self.roster, register=self.register)
        self.assertIs(with_register["register_checked"], True)
        self.assertEqual(
            with_register["state"],
            mob_ledger_admission.STATE_LEDGER_DISAGREES_WITH_REGISTER)
        record = self._recompose(lying)
        self.assertIs(record.composed, True)
        self.assertEqual(
            record.ledger_state,
            mob_ledger_admission.STATE_LEDGER_DISAGREES_WITH_REGISTER)

    def test_scene_1_is_never_flagged_as_healing(self):
        """Healing is a property of the composer, not of the admission: the
        delegated scene-1 path is handed the RAW ledger and keeps the HP it
        holds.  A mutant that flags on ``admission['ledger'] is None`` alone
        prints a healing warning over a frame whose HP is correct."""
        roster1 = field_mobs.roster_for_scene_id(SCENE1)
        anchor1 = recompose.census_anchor(
            SCENE1, ANCHOR, world_population.CENSUS_COUNT)
        record = recompose.recompose_frames(
            self.legacy, anchor1, self.register,
            ledger=mob_combat.open_ledger_for_scene_id(SCENE1),
            roster=roster1)
        self.assertIs(record.heals, False)
        declined = recompose.recompose_frames(
            self.legacy, anchor1, self.register,
            ledger=mob_combat.open_ledger(roster1[:-1]), roster=roster1)
        self.assertIs(declined.heals, False)
        self.assertIs(declined.composed, False)


class SceneAccountedForTests(unittest.TestCase):
    """ROUND le2dox, answering the chief's letter ``20260829_2340``.

    The pin that already existed (``test_every_scene_this_lane_ships_
    monsters_for_can_be_recomposed``) fires on a scene with ROSTER ROWS.
    Scene 14 has none: it has an ARRIVAL CENSUS composed by another lane,
    and no test in this lane looked at that table -- which is exactly how it
    arrived without this lane noticing.
    """

    def test_every_scene_a_lane_composes_a_census_for_is_accounted_for(self):
        """RED the day another lane opens a scene this lane has neither a
        composer nor a written acknowledgement for.  A scene a player can
        stand in is a scene a player will eventually swing in, and the
        recompose for a scene with no composer is the one-entry world wipe."""
        from pirateforce_foundation import lane_hooks

        # The registry is private and there is no public reader for its KEYS
        # (``scene_census_composer`` answers per id).  Reaching the private
        # name is the smaller cost than adding a public function to
        # ``lane_hooks/__init__.py``, which is the chief's file and outside
        # this lane's write zone -- named here rather than hidden, the same
        # way ``field_mobs.scene_ids_addressing`` names its own reach.
        # Discovery already ran at import (``_discover()`` at module scope).
        registered = set(lane_hooks._SCENE_CENSUS_COMPOSERS)
        # Scenes 1 and 2 keep their dedicated runtime.py branches and are
        # never consulted in that table; they are composed here regardless.
        unaccounted = {
            scene_id for scene_id in registered
            if not recompose.scene_is_accounted_for(scene_id)
        }
        self.assertEqual(
            unaccounted, set(),
            "another lane composes an arrival census for these scenes and "
            "this lane has neither a recompose composer nor an entry in "
            "ACKNOWLEDGED_WITHOUT_COMPOSER for them",
        )

    def test_scene_14_is_acknowledged_rather_than_silently_absent(self):
        self.assertIn(14, recompose.ACKNOWLEDGED_WITHOUT_COMPOSER)
        self.assertIs(recompose.scene_is_accounted_for(14), True)
        self.assertIsNone(recompose.composer_for_scene_id(14))

    def test_an_acknowledgement_is_not_a_composer(self):
        """The mutant this kills folds the acknowledgement table into
        ``composer_for_scene_id``, which would make a recompose in scene 14
        claim a composer it does not have."""
        for scene_id in recompose.declared_without_composer():
            with self.subTest(scene_id):
                self.assertIsNone(recompose.composer_for_scene_id(scene_id))
                self.assertNotIn(scene_id, recompose.composer_scene_ids())

    def test_a_new_unacknowledged_scene_is_red(self):
        """The tripwire's own control: it has to FAIL on the condition it
        exists to catch, measured here rather than assumed."""
        self.assertIs(recompose.scene_is_accounted_for(997), False)
        self.assertIs(recompose.scene_is_accounted_for("14"), False)
        self.assertIs(recompose.scene_is_accounted_for(True), False)


if __name__ == "__main__":
    unittest.main()
