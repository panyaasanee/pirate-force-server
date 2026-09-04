"""LANE-B round pcsjfr: the three doors of M4/M5, walked on the shipped roster.

WHY THIS FILE EXISTS.  ``COO-DECISION 2026-09-04T14:50+07:00`` item 3 took
scene 4 out of the queue with a condition attached: no new scene is armed
until at least ONE armed scene has every door -- a monster you can hit, a
monster that dies, and an object on the ground when it does.  Three scenes
were armed (Bg0003, bg0005, Bg0015) and nothing in this tree could answer
that condition: it was answered by reading three modules and believing the
join.  ``scene_door_walk`` walks it instead, and this file is what holds the
walk to the roster the server actually ships.

WHAT THE WALK MEASURED WHEN THIS FILE WAS WRITTEN (2026-09-05T04:5x+07:00,
the numbers below are the assertions, not a transcript)::

    SCENE_DOORS scene='Bg0002' rows=12 target=12 kill=12 drop=12 every_door=yes
    SCENE_DOORS scene='Bg0003' rows=12 target=12 kill=12 drop=12 every_door=yes
    SCENE_DOORS scene='Bg0015' rows=12 target=12 kill=11 drop=11 every_door=no
    SCENE_DOORS scene='bg0001' rows=4  target=4  kill=4  drop=0  every_door=no
    SCENE_DOORS scene='bg0005' rows=6  target=6  kill=6  drop=6  every_door=yes

THE TWO NEGATIVES ARE PINNED AS HARD AS THE POSITIVES, because each is a
different fact and a file that only pinned the wins would let either turn
into a silent yes:

  * ``bg0001``'s four rows are template 916, the Training Iron Man.  It names
    no drop set the shipped tables carry, so it is KILLABLE AND DROPS
    NOTHING -- which is what a training dummy is, not a hole.
  * ``Bg0015`` placement 87 (template 924, Carlos, identity 0x2058) is
    TARGETABLE AND CANNOT DIE.  ``COO-RULING-20260901-1046`` covers six of
    that scene's seven templates and holds Carlos back on purpose, so
    ``mob_death.ruling_for`` refuses him -- and a player who swings at him
    takes him to 0 HP, gets no death frames, and is answered with silence for
    every swing after that.  ``ARowNoLetterCoversStandsAtZero`` measures that
    end to end.  It is disclosed in ``runtime.py``'s own except branch and it
    is NOT fixed here: the fix changes what a player may do to a monster the
    owner deliberately held back, which is the COO's call, asked in this
    round's letter.
"""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import (  # noqa: E402
    field_mobs,
    mob_combat,
    mob_death,
    mob_loot,
    scene_door_walk,
)
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402

V141 = ROOT / "current/pf_login_game_server_v141.py"

#: The scene COO-DECISION 2026-09-04T14:50+07:00 armed and this round is
#: reporting on.  Named once so a reader can see which claim is about it.
SCENE_THREE = "Bg0003"
CARLOS_PLACEMENT = 87
CARLOS_TEMPLATE = 924
CARLOS_IDENTITY = 0x2058
TRAINING_IRON_MAN = 916


class WalkTheShippedRosterTests(unittest.TestCase):
    """The walk, run once against the frozen serializer and the real tables."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)
        cls.walked = {
            one.scene: one
            for one in scene_door_walk.walk_live_scenes(cls.legacy)
        }

    def test_every_live_scene_was_walked_and_none_of_them_refused(self):
        self.assertEqual(
            set(self.walked), set(field_mobs.live_scenes()))
        for scene, one in self.walked.items():
            self.assertEqual(one.reason, "", scene)
            self.assertEqual(one.rows_walked, len(
                field_mobs.load_roster(scene=scene)), scene)

    def test_scene_three_has_every_door_on_every_shipped_row(self):
        """The condition COO-DECISION 2026-09-04T14:50 item 3 put on scene 4.

        Not "a monster in scene 3 can be killed" -- all twelve, through all
        three doors, which is the sentence that letter's item 3 is about.
        """
        scene_three = self.walked[SCENE_THREE]
        self.assertEqual(scene_three.rows_walked, 12)
        self.assertEqual(scene_three.targetable, 12)
        self.assertEqual(scene_three.killable, 12)
        self.assertEqual(scene_three.dropping, 12)
        self.assertEqual(scene_three.rows_short_of_every_door, ())
        self.assertTrue(scene_three.every_door_open)

    def test_at_least_one_armed_scene_is_finished_and_it_is_named(self):
        """The condition itself, plus the two scenes that meet it today.

        DELIBERATELY NOT AN EXACT SET.  A lane arming a fourth scene would
        turn an ``assertEqual`` here red on a change that is none of this
        lane's business, and a tripwire in somebody else's way is a tripwire
        they will delete.  What is pinned is what this round claims: the
        condition is met, and it is met by scene 3 and scene 5.
        """
        finished = tuple(sorted(
            scene for scene, one in self.walked.items()
            if one.every_door_open))
        self.assertIn(SCENE_THREE, finished)
        self.assertIn("bg0005", finished)
        self.assertLessEqual(set(finished), set(self.walked))

    def test_scene_fourteen_is_short_by_carlos_alone(self):
        scene14 = self.walked["Bg0015"]
        self.assertEqual(scene14.rows_walked, 12)
        self.assertEqual(scene14.targetable, 12)
        self.assertEqual(scene14.killable, 11)
        self.assertFalse(scene14.every_door_open)
        short = scene14.rows_short_of_every_door
        self.assertEqual(len(short), 1)
        self.assertEqual(short[0].placement_index, CARLOS_PLACEMENT)
        self.assertEqual(short[0].template_id, CARLOS_TEMPLATE)
        self.assertEqual(short[0].actor_identity, CARLOS_IDENTITY)
        self.assertTrue(short[0].target)
        self.assertFalse(short[0].kill)
        self.assertFalse(short[0].drop)
        self.assertIn(
            "%s:%s" % (scene_door_walk.DOOR_KILL,
                       mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE),
            short[0].refusals)

    def test_the_training_dummies_die_and_drop_nothing_and_that_is_the_row(self):
        """bg0001's four rows: killable, dropping nothing, by their own table.

        A drop door that reads closed for a reason that is NOT "the roll came
        up empty" -- the sweep is 32 fixed seeds and every one of them
        produced nothing, which is what a template naming no shipped drop set
        looks like from the outside.
        """
        town = self.walked["bg0001"]
        self.assertEqual(town.rows_walked, 4)
        self.assertEqual(town.targetable, 4)
        self.assertEqual(town.killable, 4)
        self.assertEqual(town.dropping, 0)
        for row in town.rows:
            self.assertEqual(row.template_id, TRAINING_IRON_MAN)
            self.assertEqual(row.seeds_that_dropped, 0)
            self.assertEqual(row.refusals, ())

    def test_a_row_that_drops_names_how_many_seeds_did(self):
        """The drop door is a SWEEP, so the evidence is a count not a bool.

        A row reported as dropping has to have a nonzero seed count and a row
        reported as not dropping has to have zero -- otherwise the boolean is
        a second, guessable source of truth for the same measurement.
        """
        for scene, one in self.walked.items():
            for row in one.rows:
                self.assertEqual(
                    row.drop, row.seeds_that_dropped > 0,
                    "%s placement %d" % (scene, row.placement_index))


class TheWalkTouchesNothingItDoesNotOwnTests(unittest.TestCase):
    """A diagnostic that changes the game is a diagnostic nobody may run."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_the_world_floor_is_not_seeded_by_walking(self):
        """The walk kills twelve monsters; the world's floor stays as it was.

        ``mob_drop_presence.sustain_a_kill`` is the function that writes the
        process-wide ``WorldGround``, and the walk does not call it.  Measured
        rather than asserted from the source, because "does not call" is
        exactly the kind of claim a later edit breaks silently.
        """
        from pirateforce_foundation import mob_ground_persistence

        floor = mob_ground_persistence.world_ground()
        before = len(floor.standing(SCENE_THREE))
        walked = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        self.assertTrue(walked.every_door_open)
        self.assertEqual(len(floor.standing(SCENE_THREE)), before)

    def test_the_death_register_of_a_walk_does_not_escape_it(self):
        """Two walks answer identically; a shared register would not.

        A register kept between rows would refuse the second kill of the same
        identity (``mob_death`` records a death once), so a walk that leaked
        one would report a scene as finished on the first run and short on
        the second.
        """
        first = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        second = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        self.assertEqual(first.killable, second.killable)
        self.assertEqual(first.rows_short_of_every_door,
                         second.rows_short_of_every_door)


class TheWalkRefusesRatherThanRaisesTests(unittest.TestCase):
    """Every entry point this lane writes fails closed with a name."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_a_scene_nobody_ships_is_refused_by_name(self):
        walked = scene_door_walk.walk_scene(self.legacy, "Bg9999")
        self.assertEqual(walked.reason, scene_door_walk.REFUSE_NOT_A_LIVE_SCENE)
        self.assertEqual(walked.rows, ())
        self.assertFalse(walked.every_door_open)
        self.assertIn(
            scene_door_walk.SCENE_DOORS_REFUSED_TOKEN,
            scene_door_walk.describe_scene_doors(walked))

    def test_a_scene_that_is_not_a_string_is_refused_by_name(self):
        for junk in (None, 3, b"Bg0003", ["Bg0003"]):
            walked = scene_door_walk.walk_scene(self.legacy, junk)
            self.assertEqual(
                walked.reason, scene_door_walk.REFUSE_NOT_A_LIVE_SCENE,
                repr(junk))
            self.assertEqual(walked.scene, "")

    def test_something_that_is_not_the_serializer_is_refused_by_name(self):
        for junk in (None, object(), "legacy"):
            walked = scene_door_walk.walk_scene(junk, SCENE_THREE)
            self.assertEqual(
                walked.reason,
                scene_door_walk.REFUSE_LEGACY_NOT_A_SERIALIZER, repr(junk))

    def test_a_refused_walk_is_never_reported_as_every_door_open(self):
        for reason in ("", scene_door_walk.REFUSE_ROSTER_UNREADABLE):
            walked = scene_door_walk.SceneDoors(SCENE_THREE, (), reason)
            self.assertFalse(walked.every_door_open)

    def test_the_console_line_is_bounded_ascii_on_every_live_scene(self):
        for line in scene_door_walk.describe_live_scene_doors(self.legacy):
            line.encode("ascii")
            self.assertLess(len(line), 300, line)
            self.assertTrue(line.startswith(scene_door_walk.SCENE_DOORS_TOKEN))

    def test_the_summary_line_names_the_finished_scenes(self):
        lines = scene_door_walk.describe_live_scene_doors(self.legacy)
        summary = lines[-1]
        self.assertIn("summary", summary)
        self.assertIn("live_scenes=%d" % len(field_mobs.live_scenes()), summary)
        named = summary.split("every_door=")[1].split()[0].split(",")
        self.assertIn(SCENE_THREE, named)
        self.assertIn("bg0005", named)
        # The summary is the per-scene lines' own answer, never a second one.
        walked = {one.scene: one
                  for one in scene_door_walk.walk_live_scenes(self.legacy)}
        self.assertEqual(
            sorted(named),
            sorted(s for s, one in walked.items() if one.every_door_open))


class ARowNoLetterCoversStandsAtZeroTests(unittest.TestCase):
    """The Bg0015 hole, measured end to end rather than inferred from a table.

    This is the state ``runtime.py``'s except branch calls "honest
    degradation": the kill refuses, no death frames go out, and the monster
    is left at the floor.  What the walk found is the half that sentence does
    not say out loud -- the monster is a TARGET first, so a player can put it
    there, and every swing after that is answered with no frames at all.
    """

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)
        roster = field_mobs.load_roster(scene="Bg0015")
        cls.carlos = [
            m for m in roster if m.template_id == CARLOS_TEMPLATE][0]
        cls.roster = roster

    def test_no_registered_letter_covers_him(self):
        self.assertEqual(mob_death.rulings_covering(self.carlos), ())
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.ruling_for(self.carlos)
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_TARGET_OUTSIDE_THE_SANCTIONED_SCOPE)

    def test_one_swing_takes_him_to_zero_and_the_kill_refuses(self):
        ledger = mob_combat.open_ledger(self.roster)
        step = mob_combat.strike(
            self.legacy, None, ledger, None, self.carlos,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        self.assertTrue(step.outcome.death_due)
        self.assertEqual(step.outcome.hp_after, 0)
        with self.assertRaises(mob_death.MobDeathContractError):
            mob_death.kill(
                self.legacy, self.carlos, step.outcome,
                widened=mob_death.ruling_for(self.carlos))

    def test_the_next_swing_answers_with_no_frames_at_all(self):
        """A monster at 0 HP that never died answers nothing, for ever.

        Pinned so the day somebody changes what a player may do to him, this
        test says which state they changed away from.
        """
        ledger = mob_combat.open_ledger(self.roster)
        first = mob_combat.strike(
            self.legacy, None, ledger, None, self.carlos,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        second = mob_combat.strike(
            self.legacy, None, mob_combat.commit_step(ledger, first), None,
            self.carlos, scene_door_walk.WALKER_IDENTITY,
            scene_door_walk.WALKER)
        self.assertEqual(second.frames, ())
        self.assertEqual(second.outcome.hp_after, 0)


class TheKillDoorAndTheLettersAgreeTests(unittest.TestCase):
    """The walk's kill door is the registered letters, not a second opinion."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_every_row_the_walk_kills_names_the_letter_it_travelled_under(self):
        for one in scene_door_walk.walk_live_scenes(self.legacy):
            for row in one.rows:
                if not row.kill:
                    continue
                mob = [
                    m for m in field_mobs.load_roster(scene=one.scene)
                    if m.placement_index == row.placement_index][0]
                if row.ruling:
                    self.assertIn(row.ruling, mob_death.WIDENING_RULINGS)
                    self.assertIn(row.ruling, mob_death.rulings_covering(mob))
                else:
                    # The sanctioned first target is the one row kill()
                    # admits with no letter at all; nothing else may be here.
                    self.assertEqual(
                        mob.actor_identity,
                        mob_death.SANCTIONED_FIRST_TARGET_IDENTITY)


class TheDropDoorIsTheShippedTablesTests(unittest.TestCase):
    """A drop door opens on the mined tables, never on a composed row."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def test_a_scene_the_walk_calls_dropping_has_its_sets_in_the_table(self):
        import pirateforce_foundation.field_drop_tables as tables

        walked = scene_door_walk.walk_scene(self.legacy, SCENE_THREE)
        self.assertIn(SCENE_THREE, tables.SCENES)
        for row in walked.rows:
            self.assertTrue(row.drop, row.placement_index)
            self.assertGreater(row.seeds_that_dropped, 0, row.placement_index)

    def test_the_walk_places_rows_through_the_cell_and_not_beside_it(self):
        """A placed row carries the scene it fell in, or it is not a row.

        ``GroundDrop.scene`` is the field the publication filter reads, so a
        walk that placed rows without a scene would report a door open on
        objects no player standing there could ever be shown.
        """
        import random

        roster = field_mobs.load_roster(scene=SCENE_THREE)
        mob = roster[0]
        cell = mob_loot.DropLedgerCell()
        cell.enter_scene(SCENE_THREE)
        step = mob_combat.strike(
            self.legacy, None, mob_combat.open_ledger((mob,)), None, mob,
            scene_door_walk.WALKER_IDENTITY, scene_door_walk.WALKER)
        death = mob_death.kill(
            self.legacy, mob, step.outcome,
            widened=mob_death.ruling_for(mob))
        placed = ()
        for seed in scene_door_walk.DROP_SEEDS:
            roll = mob_loot.roll_drops(mob, random.Random(seed))
            placed = cell.loot_a_kill(
                mob, death.record, roll,
                kill_token=death.register.generation, position=None)
            if placed:
                break
            death = mob_death.kill(
                self.legacy, mob, step.outcome,
                widened=mob_death.ruling_for(mob))
        self.assertTrue(placed)
        for row in placed:
            self.assertIs(type(row), mob_loot.GroundDrop)
            self.assertEqual(row.scene, SCENE_THREE)


if __name__ == "__main__":
    unittest.main()
