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

import ast
import contextlib
import io
import sys
import types
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (
    field_mobs,
    lane_hooks,
    mob_death,
    mob_death_persistence,
)
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

    def test_an_older_subscriber_survives_a_later_argument(self):
        # WHY **_ IS NOT DECORATION.  This round already added a fourth
        # argument to a contract published in a letter three hours earlier.
        # A hook written against the first three still has to run.
        def count_it(*, mob_id, **_):
            self.received.append(mob_id)

        self._subscribe(count_it)
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored, step, announce=False)
        self.assertEqual(self.received, [step.record.actor_identity])

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
    # the field that makes a kill COUNTER possible (pf-adversary D1)
    # ------------------------------------------------------------------

    def test_two_sessions_killing_one_monster_are_told_apart(self):
        # THE DEFECT THIS EXISTS FOR, measured before it was fixed: the
        # register commit_death compare-and-swaps against is built PER
        # CONNECTION (runtime.py), so two players standing in one scene each
        # read a live monster, each kill it, and BOTH commits are accepted.
        # The point fired twice for one monster, and a quest counting the
        # events counted two kills.  The world's grave book is the one
        # process-wide answer, and it is now carried on the event.
        world = mob_death_persistence.WorldDeaths()
        self._subscribe(lambda **kw: self.received.append(kw))
        first_register, first_step = self._a_kill()
        second_register, second_step = self._a_kill()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(
                first_register, first_step, world=world, announce=False)
            mob_death.commit_death(
                second_register, second_step, world=world, announce=False)
        self.assertEqual(
            len(self.received), 2,
            "both commits are accepted -- that part is correct and is why "
            "the field below has to exist")
        self.assertEqual(
            [event["first_in_the_world"] for event in self.received],
            [True, False],
            "a kill counter cannot tell one monster's death from two")

    def test_a_world_book_that_could_not_answer_says_so_rather_than_true(self):
        # A refused burial must not read as "this is the first death": a
        # counter that treated the unknown as a yes would over-count exactly
        # when the books are already broken.
        class RefusingWorld:
            def remember(self, *a, **k):
                raise RuntimeError("the grave book is unavailable")

        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            after = mob_death.commit_death(
                stored, step, world=RefusingWorld(), announce=False)
        self.assertIs(after, step.register)
        self.assertEqual(len(self.received), 1)
        self.assertIsNone(self.received[0]["first_in_the_world"])

    def test_an_outcome_of_an_unexpected_shape_is_unknown_not_a_crash(self):
        # _first_in_the_world sits one statement from the lane hook and on
        # the death path: an outcome it does not recognise has to become
        # None, never an AttributeError.
        self.assertIsNone(mob_death._first_in_the_world(None))
        self.assertIsNone(mob_death._first_in_the_world(object()))
        self.assertIsNone(
            mob_death._first_in_the_world(
                types.SimpleNamespace(buried=True, already_buried="no")))
        self.assertIs(
            mob_death._first_in_the_world(
                types.SimpleNamespace(buried=True, already_buried=False)),
            True)
        self.assertIs(
            mob_death._first_in_the_world(
                types.SimpleNamespace(buried=True, already_buried=True)),
            False)

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
        mob_death._LANE_HOOK_DOOR_REFUSAL_ANNOUNCED = False
        self.addCleanup(
            setattr, mob_death, "_LANE_HOOK_DOOR_REFUSAL_ANNOUNCED", False)
        stored, step = self._a_kill()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            after = mob_death.commit_death(stored, step)
            # THE LATCH, measured on the path a player drives: the door that
            # raises is a broken IMPORT, identical on every kill and retried
            # on every kill.  Unlatched, a player with a sword drives an
            # unbounded log.  pf-adversary measured three kills, three lines.
            second_register, second_step = self._a_kill()
            mob_death.commit_death(second_register, second_step)
        self.assertIs(
            after, step.register,
            "a broken hook door cost the caller the register it dispatches "
            "the death frames on")
        self.assertEqual(
            err.getvalue().count("MOB_DEATH_LANE_HOOK_REFUSED"), 1,
            "the hook door refusal is not latched")
        self.assertNotIn(
            "MOB_DEATH_LANE_HOOK_REFUSED", out.getvalue(),
            "this token belongs on stderr: every other token this package "
            "prints moved there the day one landed in a --json artifact")

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
            ("mob_id", "scene_id", "killer_actor_identity",
             "first_in_the_world"))

    def test_the_literal_at_the_call_site_is_the_constant_lanes_import(self):
        # THE ONE PLACE THIS FEATURE CAN DRIFT IN SILENCE.  The call site has
        # to pass a string LITERAL -- ``gm/lane_gate_name_audit.py`` grades
        # every hook point in this tree by reading the source, and a Name
        # node there makes "does anything fire this point?" unanswerable for
        # every point in the tree, not only this one (the gate rehearsal
        # caught exactly that on this round's first draft).  A registering
        # lane, meanwhile, is told to import the constant.  So two spellings
        # of one name exist on purpose, and nothing but this test stops one
        # of them from being edited alone -- after which LANE-Q's hook would
        # register on a point nothing fires, with no error anywhere.
        source = (ROOT / "src/pirateforce_foundation/mob_death.py").read_text(
            encoding="utf-8")
        tree = ast.parse(source)
        fired = [
            node.args[0].value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "fire"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ]
        self.assertEqual(
            fired, [mob_death.MOB_DEATH_LANE_HOOK_POINT],
            "the literal fired and the constant lanes register on have "
            "drifted apart")

    def test_the_module_does_not_claim_a_quest_counts_anything(self):
        joined = " ".join(mob_death.MOB_DEATH_NONCLAIMS)
        self.assertIn("MOB_DEATH_LANE_HOOK_POINT", joined)
        self.assertIn("OPEN DOOR AND NOT A FEATURE", joined)

    # ------------------------------------------------------------------
    # D11 (pf-adversary, round 2zybdx, deferred to round dggvou): the hook
    # can fire BEFORE the caller writes its own register back, because
    # ``self.mob_death_register = mob_death.commit_death(...)`` is one
    # Python statement and the assignment happens only after the whole
    # right-hand side (hook included) has returned.
    # ------------------------------------------------------------------

    def test_the_ordering_hazard_is_real_on_the_undivided_call(self):
        # THE EXACT STATEMENT SHAPE runtime.py's two roster kill sites use:
        # ``self.mob_death_register = mob_death.commit_death(...)``.  A
        # session-like stand-in plays the part of ``self`` here so the test
        # can observe what a subscriber sees DURING the fire, before the
        # assignment on this same line has happened.
        session = types.SimpleNamespace(mob_death_register=DeathRegister())
        observed_during_fire = []

        def nosy_subscriber(*, mob_id, scene_id, **_):
            # A real subscriber reaching back into the connection's own
            # live state the way lane_hooks.current_session_scene_id lets
            # one reach into OTHER per-session facts.
            observed_during_fire.append(
                session.mob_death_register.is_dead(mob_id, scene_id))

        self._subscribe(nosy_subscriber)
        stored, step = self._a_kill(session.mob_death_register)
        with contextlib.redirect_stderr(io.StringIO()):
            session.mob_death_register = mob_death.commit_death(
                stored, step, announce=False)
        self.assertEqual(
            observed_during_fire, [False],
            "the hazard is that a subscriber sees the OLD register while "
            "still inside this statement's right-hand side")
        self.assertTrue(
            session.mob_death_register.is_dead(
                step.record.actor_identity, step.record.scene),
            "after the statement completes the write-back is visible, "
            "which is exactly what makes the mid-statement False a real "
            "ordering hazard and not simply a wrong answer")

    def test_the_split_call_lets_a_caller_close_the_gap(self):
        # THE FIX A CALLER CAN APPLY TODAY, without this lane touching
        # runtime.py: write the register back BEFORE firing, using the two
        # halves this round split commit_death into.
        session = types.SimpleNamespace(mob_death_register=DeathRegister())
        observed_during_fire = []

        def nosy_subscriber(*, mob_id, scene_id, **_):
            observed_during_fire.append(
                session.mob_death_register.is_dead(mob_id, scene_id))

        self._subscribe(nosy_subscriber)
        stored, step = self._a_kill(session.mob_death_register)
        with contextlib.redirect_stderr(io.StringIO()):
            new_register, pending = mob_death.commit_death_and_prepare_hook(
                stored, step, announce=False)
            session.mob_death_register = new_register  # write back FIRST
            mob_death.fire_mob_death_hook(pending, announce=False)  # THEN fire
        self.assertEqual(
            observed_during_fire, [True],
            "writing the register back before firing closes the gap the "
            "test above measures on the undivided call")

    def test_commit_death_and_prepare_hook_fires_nothing_by_itself(self):
        # Mirrors test_composing_a_kill_without_committing_it_fires_nothing:
        # the split half that does the world-book write must not ALSO fire
        # the point, or a caller using the split path would get it twice.
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death_and_prepare_hook(
                stored, step, announce=False)
        self.assertEqual(self.received, [])

    def test_the_split_path_and_the_undivided_path_send_the_same_arguments(
            self):
        # PARITY: two ways to reach the same point must not drift into two
        # different contracts.
        self._subscribe(lambda **kw: self.received.append(kw))
        stored_a, step_a = self._a_kill()
        stored_b, step_b = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored_a, step_a, announce=False)
            new_register, pending = mob_death.commit_death_and_prepare_hook(
                stored_b, step_b, announce=False)
            mob_death.fire_mob_death_hook(pending, announce=False)
        self.assertEqual(len(self.received), 2)
        undivided, split = self.received
        self.assertEqual(sorted(undivided), sorted(split))
        self.assertEqual(pending.mob_id, step_b.record.actor_identity)
        self.assertEqual(pending.scene_id, step_b.record.scene)
        self.assertEqual(
            pending.killer_actor_identity, step_b.record.killer_identity)

    def test_a_raising_subscriber_on_the_split_path_costs_only_the_hook(self):
        # The same guarantee test_a_raising_subscriber_costs_the_hook_and_
        # not_the_kill pins for commit_death, held for the split path too:
        # the kill is committed (register returned) and the well-behaved
        # SECOND subscriber still gets delivered, even though the first one
        # raised.  NOT a mutation-target for fire_mob_death_hook's own
        # try/except (pf-adversary, round dggvou, measured that removing it
        # leaves this test green: lane_hooks.fire() already isolates each
        # subscriber's own exception before it reaches this function - see
        # that function's docstring for what its try/except actually guards,
        # which is the `from . import lane_hooks` door, not a subscriber).
        def explode(**_):
            raise RuntimeError("a lane hook with a bug in it")

        self._subscribe(explode)
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            register, pending = mob_death.commit_death_and_prepare_hook(
                stored, step, announce=False)
            mob_death.fire_mob_death_hook(pending, announce=False)
        self.assertIs(register, step.register)
        self.assertEqual(len(self.received), 1)

    def test_firing_the_same_pending_hook_twice_is_refused(self):
        # pf-adversary, round dggvou, reviewing the D11 split above: nothing
        # stopped a caller from firing one PendingMobDeathHook twice, which
        # sends a subscriber two identical mob_death events for one accepted
        # kill - the exact double-count first_in_the_world exists to let a
        # subscriber detect, reopened one layer up where that field cannot
        # see it, because both fires would carry the same payload.
        self._subscribe(lambda **kw: self.received.append(kw))
        stored, step = self._a_kill()
        with contextlib.redirect_stderr(io.StringIO()):
            _, pending = mob_death.commit_death_and_prepare_hook(
                stored, step, announce=False)
            mob_death.fire_mob_death_hook(pending, announce=False)
            with self.assertRaises(mob_death.MobDeathContractError) as ctx:
                mob_death.fire_mob_death_hook(pending, announce=False)
        self.assertEqual(
            ctx.exception.reason, mob_death.REFUSE_HOOK_ALREADY_FIRED)
        self.assertEqual(
            len(self.received), 1,
            "the refused second fire must not reach any subscriber")

    # ------------------------------------------------------------------
    # D10 (pf-adversary, round 2zybdx, deferred to round dggvou): the hook
    # has no timeout and runs on the caller's own thread.  This measures the
    # CURRENT blocking behaviour for real rather than only asserting it in
    # prose -- see notes_to_chief for why this stays a measurement plus a
    # letter rather than a fix in this lane's own files.
    # ------------------------------------------------------------------

    def test_a_slow_subscriber_blocks_commit_death_for_its_full_duration(self):
        import time as _time  # local import: this module's OWN import list
        # is audited (test_nothing_is_installed_by_importing_this_module in
        # test_mob_death.py) to carry no `time` -- this is the TEST file,
        # which measures the production module from outside it, the same
        # licence test_mob_death.py's own clock-based tests already use.

        SLEEP_SECONDS = 0.05

        def slow_subscriber(**_):
            _time.sleep(SLEEP_SECONDS)

        self._subscribe(slow_subscriber)
        stored, step = self._a_kill()
        started = _time.monotonic()
        with contextlib.redirect_stderr(io.StringIO()):
            mob_death.commit_death(stored, step, announce=False)
        elapsed = _time.monotonic() - started
        self.assertGreaterEqual(
            elapsed, SLEEP_SECONDS,
            "commit_death returned before its own subscriber finished "
            "sleeping: this project's lane_hooks would then have grown a "
            "timeout nobody wrote a letter about")

    def test_nothing_in_this_tree_registers_on_the_point_yet(self):
        # A NEGATIVE THAT IS ALLOWED TO GO STALE ON PURPOSE.  The nonclaim
        # above says no lane has registered a production hook on this point;
        # this is the grep behind that sentence, so the DAY LANE-Q lands one
        # this test fails and forces the nonclaim to be rewritten instead of
        # left standing as a lie.
        # READ WITH THE PARSER, NOT WITH ``in``.  A substring version of
        # this test was written first and pf-adversary defeated it in one
        # line: wrapping the decorator to this project's own 79-column
        # style breaks ``hook("mob_death")`` across a newline and the guard
        # goes green over a live registration.  So does importing the
        # constant by any other spelling.  The parser sees the call however
        # it is laid out, and resolves the two spellings this file
        # deliberately maintains.
        hooks_dir = ROOT / "src/pirateforce_foundation/lane_hooks"
        registering = []
        for path in sorted(hooks_dir.glob("lane_*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                called = node.func
                name = getattr(called, "attr", None) or getattr(
                    called, "id", None)
                if name != "hook":
                    continue
                first = node.args[0]
                names_the_point = (
                    (isinstance(first, ast.Constant)
                     and first.value == mob_death.MOB_DEATH_LANE_HOOK_POINT)
                    or getattr(first, "attr", None)
                    == "MOB_DEATH_LANE_HOOK_POINT"
                    or getattr(first, "id", None)
                    == "MOB_DEATH_LANE_HOOK_POINT"
                )
                if names_the_point:
                    registering.append(path.name)
                    break
        self.assertEqual(
            registering, [],
            "a lane registered on the mob_death point: rewrite the nonclaim "
            "in mob_death.py that says nobody has, then update this test")


if __name__ == "__main__":
    unittest.main()
