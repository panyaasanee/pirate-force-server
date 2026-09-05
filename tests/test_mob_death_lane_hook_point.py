"""LANE-B round ``2zybdx``: the "a monster died" seam, proven by firing it.

WHY THIS FILE EXISTS AND NOT ONE MORE CLASS IN ``test_mob_death.py``.  The
lesson is chief's, paid for in ``pirate-force-server#794``: an AST scan that
finds the string ``lane_hooks.fire`` somewhere under ``src/`` proves the NAME
is present and nothing else.  A mutant that moved a ``fire()`` call into
unreachable code below a ``return`` left that audit green AND the full suite
green, byte-identical, 10434 passed either way.  So every assertion below
runs the REAL ``lane_hooks.fire`` through a REAL ``mob_death.commit_death``
on a REAL kill composed from the shipped roster, and reads what the
subscriber actually received.  Reachability is a measurement here, not a
grep.

WHAT THE SEAM IS FOR.  ``COO-DECISION 20260905_2057`` told LANE-B to declare
the combat events LANE-Q needs for quest kill counts.  LANE-B's answer
(``pf_bridge/notes_to_chief/20260905_2112_LANE-B-TO-LANE-Q-*.md``) measured
the tree and reported that the ``lane_hooks`` MECHANISM exists while every
call site on main is an inbound client packet -- nothing fires when a monster
dies.  Round ``2zybdx`` opened the call site inside ``commit_death``, which
is LANE-B's own file, so no chief round stands between LANE-Q and a counter.

WHAT IS NOT CLAIMED HERE.  No lane registers a production hook on this point
today, no quest counts anything, and no player sees any difference.  These
tests prove the door opens and closes correctly; they do not claim anyone has
walked through it.
"""

import contextlib
import io
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, lane_hooks, mob_death
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_combat import Combatant, open_ledger, strike
from pirateforce_foundation.mob_death import DeathRegister, kill


PERFORMER = 0x750059
LETHAL = Combatant(level=1000, ability_str=100000, ability_con=0)
POINT = mob_death.MOB_DEATH_LANE_HOOK_POINT
# The real ruling that widens the death scope to this lane's control row, not
# a test-only string: ``kill()`` fails closed on any ``widened=`` that is not
# an exact key of ``mob_death.WIDENING_RULINGS``, and a hook test has no
# business standing on a weaker gate than the production path does.
CONTROL_WIDENING = (
    "COO-DECISION widen-death-scope-916-training-iron-man "
    "2026-08-27T09:55+07:00 (ref PANYA-DECISION 2026-08-27T09:50+07:00 "
    "section 3, supersedes COO 0954)"
)


class MobDeathLaneHookPointTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        cls.mob = [
            m for m in cls.roster
            if m.placement_index == field_mobs.CONTROL_PLACEMENT_INDEX
        ][0]

    def setUp(self):
        # SAVE AND RESTORE, never pop.  ``_HOOKS`` is module-global and this
        # is a REAL point name, not a private one invented for a test: the
        # day a lane file registers on it, a ``pop`` here would delete that
        # registration for every test that runs after this file and the
        # deletion would look like a lane bug somewhere else entirely.
        self._registered_before = list(lane_hooks._HOOKS.get(POINT, ()))
        self.addCleanup(self._restore_hooks)
        lane_hooks._HOOKS[POINT] = []
        self.received = []

    def _restore_hooks(self):
        if self._registered_before:
            lane_hooks._HOOKS[POINT] = list(self._registered_before)
        else:
            lane_hooks._HOOKS.pop(POINT, None)

    def _subscribe(self, fn):
        """Register ``fn`` on the real point through the real registry."""
        lane_hooks._HOOKS.setdefault(POINT, []).append((__name__, fn))
        return fn

    def _a_kill(self, register=None):
        stored = DeathRegister() if register is None else register
        step = strike(
            self.legacy, None, open_ledger(), None, self.mob, PERFORMER,
            LETHAL)
        return stored, kill(
            self.legacy, self.mob, step.outcome, stored,
            widened=CONTROL_WIDENING)

    # ------------------------------------------------------------------
    # the point fires, once, with what the letter says it carries
    # ------------------------------------------------------------------

    def test_an_accepted_kill_fires_the_point_exactly_once(self):
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            after = mob_death.commit_death(stored, step, announce=False)
        self.assertEqual(len(self.received), 1)
        self.assertIs(after, step.register)

    def test_the_arguments_are_the_ones_this_lane_published(self):
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored, step, announce=False)
        self.assertEqual(
            sorted(self.received[0]),
            sorted(mob_death.MOB_DEATH_LANE_HOOK_ARGUMENTS),
            "the published contract and what is actually passed have drifted",
        )
        self.assertEqual(
            self.received[0]["mob_id"], step.record.actor_identity)
        self.assertEqual(self.received[0]["scene_id"], step.record.scene)
        self.assertEqual(
            self.received[0]["killer_actor_identity"],
            step.record.killer_identity)

    def test_a_subscriber_written_the_way_the_letter_says_it_can_be(self):
        # The signature LANE-B told LANE-Q to write, run for real: keyword
        # only, with **_ so a later argument cannot break an old hook.
        def count_it(*, mob_id, scene_id, killer_actor_identity, **_):
            self.received.append((mob_id, scene_id, killer_actor_identity))

        self._subscribe(count_it)
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored, step, announce=False)
        self.assertEqual(
            self.received,
            [(step.record.actor_identity, step.record.scene,
              step.record.killer_identity)],
        )

    def test_the_scene_the_hook_is_told_is_the_scene_the_grave_is_in(self):
        # ``scene_id`` is a scene KEY STRING (the project's own scene name),
        # never an integer, and a LANE-Q author who assumed otherwise would
        # index a table with it.  Pinned as a type, not only as a value.
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored, step, announce=False)
        self.assertIsInstance(self.received[0]["scene_id"], str)
        self.assertEqual(self.received[0]["scene_id"], self.mob.scene)

    # ------------------------------------------------------------------
    # what must NOT fire
    # ------------------------------------------------------------------

    def test_a_refused_commit_announces_no_death_to_anybody(self):
        # THE DEFECT THIS PREVENTS: a quest crediting a player for a monster
        # whose death frames were never sent.  commit_death refuses a stale
        # step by name, the caller sends nothing -- and the hook must hear
        # nothing either, or the counter and the screen disagree forever.
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            moved = mob_death.commit_death(stored, step, announce=False)
            self.assertEqual(len(self.received), 1)
            with self.assertRaises(mob_death.MobDeathContractError) as caught:
                mob_death.commit_death(moved, step, announce=False)
        self.assertEqual(
            caught.exception.reason, mob_death.REFUSE_REGISTER_STALE)
        self.assertEqual(
            len(self.received), 1,
            "a refused kill fired the point: a quest would count a death "
            "the player never saw")

    def test_composing_a_kill_without_committing_it_fires_nothing(self):
        # kill() may be called and its step thrown away (the caller re-reads
        # a fresher register and recomputes).  Only commit_death announces.
        self._subscribe(lambda **kw: self.received.append(kw))
        self._a_kill()
        self.assertEqual(self.received, [])

    # ------------------------------------------------------------------
    # the seam can cost the world a hook and never the player a kill
    # ------------------------------------------------------------------

    def test_a_raising_subscriber_costs_the_hook_and_not_the_kill(self):
        def explode(**_):
            raise RuntimeError("a lane hook with a bug in it")

        self._subscribe(explode)
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            after = mob_death.commit_death(stored, step, announce=False)
        self.assertIs(after, step.register)
        self.assertEqual(
            len(self.received), 1,
            "one lane's broken hook stopped the next lane's working one")
        self.assertIn("ERR", stderr.getvalue())

    def test_a_hook_door_that_raises_is_named_and_costs_nothing(self):
        # ``fire`` is fail-closed by its own contract; what this pins is the
        # try/except AROUND it in commit_death, which exists for the failure
        # that contract cannot cover -- the import of the package itself.
        def raising_fire(point, **kwargs):
            raise RuntimeError("the hook door is broken")

        original = lane_hooks.fire
        lane_hooks.fire = raising_fire
        self.addCleanup(setattr, lane_hooks, "fire", original)
        stored, step = self._a_kill()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            after = mob_death.commit_death(stored, step)
        self.assertIs(
            after, step.register,
            "a broken hook door cost the caller the register it dispatches "
            "the death frames on")
        self.assertIn("MOB_DEATH_LANE_HOOK_REFUSED", out.getvalue())

    def test_a_silent_commit_stays_silent_even_when_the_door_raises(self):
        def raising_fire(point, **kwargs):
            raise RuntimeError("the hook door is broken")

        original = lane_hooks.fire
        lane_hooks.fire = raising_fire
        self.addCleanup(setattr, lane_hooks, "fire", original)
        stored, step = self._a_kill()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(io.StringIO()):
            after = mob_death.commit_death(stored, step, announce=False)
        self.assertIs(after, step.register)
        self.assertEqual(out.getvalue(), "")

    def test_a_dead_console_costs_neither_the_hook_nor_the_kill(self):
        # The failure chief's #794 measured, applied to this site: a server
        # started as `python app.py 2>log` on a full volume.  Every print on
        # this path is guarded, so the kill survives a stderr that raises.
        class DeadStream(io.StringIO):
            def write(self, text):
                raise OSError(9, "Bad file descriptor")

        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        real_stderr = sys.stderr
        sys.stderr = DeadStream()
        try:
            after = mob_death.commit_death(stored, step, announce=False)
        finally:
            sys.stderr = real_stderr
        self.assertIs(after, step.register)
        self.assertEqual(len(self.received), 1)

    # ------------------------------------------------------------------
    # the declared contract is a value, not a sentence in a comment
    # ------------------------------------------------------------------

    def test_the_point_name_is_a_constant_a_registering_module_can_import(self):
        self.assertEqual(mob_death.MOB_DEATH_LANE_HOOK_POINT, "mob_death")
        self.assertIsInstance(mob_death.MOB_DEATH_LANE_HOOK_ARGUMENTS, tuple)
        self.assertEqual(
            mob_death.MOB_DEATH_LANE_HOOK_ARGUMENTS,
            ("mob_id", "scene_id", "killer_actor_identity"))

    def test_the_module_does_not_claim_a_quest_counts_anything(self):
        joined = " ".join(mob_death.MOB_DEATH_NONCLAIMS)
        self.assertIn("MOB_DEATH_LANE_HOOK_POINT", joined)
        self.assertIn("OPEN DOOR AND NOT A FEATURE", joined)

    def test_nothing_in_this_tree_registers_on_the_point_yet(self):
        # A NEGATIVE THAT IS ALLOWED TO GO STALE ON PURPOSE.  The nonclaim
        # above says no lane has registered a production hook on this point;
        # this is the grep behind that sentence, so the DAY LANE-Q lands one
        # this test fails and forces the nonclaim to be rewritten instead of
        # left standing as a lie.
        hooks_dir = ROOT / "src/pirateforce_foundation/lane_hooks"
        registering = [
            path.name for path in sorted(hooks_dir.glob("lane_*.py"))
            if 'hook("mob_death")' in path.read_text(encoding="utf-8")
            or "hook(mob_death.MOB_DEATH_LANE_HOOK_POINT)"
            in path.read_text(encoding="utf-8")
        ]
        self.assertEqual(
            registering, [],
            "a lane registered on the mob_death point: rewrite the nonclaim "
            "in mob_death.py that says nobody has, then update this test")


if __name__ == "__main__":
    unittest.main()
