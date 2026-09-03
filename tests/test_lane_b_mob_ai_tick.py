"""LANE-B: lane_hooks/lane_b_mob_ai_tick.py -- the option-(b) wrapper around
mob_ai_scheduler.tick_session, and the exact call site it names for a future
runtime.py round (round iok5z1, 2026-08-31).

Three load-bearing tests in this file.

``test_maybe_tick_passes_through_the_same_register_and_results`` is the
whole contract: this file changes nothing about tick_session's own outcome,
only what prints.

``test_only_a_phase_transition_prints_a_row_line`` pins the console-spam
guard named in the module's own docstring: a register full of rows that did
not change phase must not flood stdout on every TargetPos a moving player
sends.

~~``test_nothing_in_runtime_py_calls_maybe_tick_yet`` is this round's own
honest half, the same discipline test_mob_ai_scheduler.py's sibling test
already uses: nothing calls this today, and this test fails the day that
stops being true without the module docstring's "WHAT THE PLAYER WILL SEE
DIFFERENTLY" section being updated to match.~~
[STALE as of round `p05wire`, 2026-09-01, COO-DECISION 20260901_0145]
[MEASURED, by reading this file itself]: that day arrived in round
`p05wire`.  The negative test above was flipped (not deleted) to
``test_runtime_py_now_calls_maybe_tick_per_coo_decision_0145``, and the
module docstring's "WHAT THE PLAYER WILL SEE DIFFERENTLY" section was
updated to match in round `3w2mfu` (this correction) -- the promise this
paragraph made to itself, kept one round later than the code that
triggered it.
"""
from __future__ import annotations

import ast
import contextlib
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import (  # noqa: E402
    field_mob_tables_bg0002, field_mobs, mob_aggro, mob_ai_control,
    mob_ai_player_damage, mob_combat,
)
from pirateforce_foundation.lane_hooks import lane_b_mob_ai_tick  # noqa: E402
from pirateforce_foundation.mob_ai_player_damage import (  # noqa: E402
    MobAiPlayerDamageError,
)

SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
PLAYER = 0x750059
BG0002_OFFENSIVE_PLACEMENT = 92  # Orc Chief, ai_wander=11 (offensive)


class MaybeTickTests(unittest.TestCase):
    def setUp(self):
        bg0002_roster = field_mobs._parse_hostile_placements(
            field_mob_tables_bg0002)
        self.bg0002_by_placement = {
            m.placement_index: m for m in bg0002_roster}
        self.register = mob_ai_control.open_register(bg0002_roster)
        self.ledger = mob_combat.open_ledger(bg0002_roster)

        dummy_roster = field_mobs.load_roster()  # bg0001: four dummies
        self.dummy_register = mob_ai_control.open_register(dummy_roster)
        self.dummy_ledger = mob_combat.open_ledger(dummy_roster)

    def test_production_allowed_is_true_with_no_flag(self):
        self.assertIs(lane_b_mob_ai_tick.production_allowed, True)

    def test_maybe_tick_passes_through_the_same_register_and_results(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        with redirect_stdout(io.StringIO()):
            wrapped_register, wrapped_results = lane_b_mob_ai_tick.maybe_tick(
                self.register, self.ledger, PLAYER,
                (mob.x + 100.0, mob.y, mob.z))
        from pirateforce_foundation.mob_ai_scheduler import tick_session
        direct_register, direct_results = tick_session(
            self.register, self.ledger, PLAYER, (mob.x + 100.0, mob.y, mob.z))
        self.assertEqual(
            wrapped_register.identities(), direct_register.identities())
        for identity in wrapped_register.identities():
            self.assertEqual(
                wrapped_register.state_of(identity).phase,
                direct_register.state_of(identity).phase)
        self.assertEqual(len(wrapped_results), len(direct_results))
        self.assertEqual(
            [r.after_phase for r in wrapped_results],
            [r.after_phase for r in direct_results])

    def test_only_a_phase_transition_prints_a_row_line(self):
        mob = self.bg0002_by_placement[BG0002_OFFENSIVE_PLACEMENT]
        buf = io.StringIO()
        with redirect_stdout(buf):
            _register, results = lane_b_mob_ai_tick.maybe_tick(
                self.register, self.ledger, PLAYER,
                (mob.x + 100.0, mob.y, mob.z))
        lines = [
            line for line in buf.getvalue().splitlines()
            if line.startswith("LANE_B_MOB_AI_TICK")
        ]
        transitioned = [
            r for r in results if r.before_phase != r.after_phase]
        # Measured: placement 92 (Orc Chief) is one of a five-mob offensive
        # group at this position, so more than one row acquires -- the
        # count this test pins is "one line per row that actually changed",
        # not a fixed number of mobs.  17 rows total in this register (this
        # project's largest per-session roster); the rest stay idle->idle
        # and must print nothing.
        self.assertTrue(0 < len(transitioned) < len(results))
        self.assertEqual(len(lines), len(transitioned))
        self.assertIn("idle->aggro", lines[0])
        self.assertIn("0x%X" % mob.actor_identity, "\n".join(lines))

    def test_a_no_op_pass_prints_no_row_lines(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            lane_b_mob_ai_tick.maybe_tick(
                self.dummy_register, self.dummy_ledger, PLAYER,
                (0.0, 0.0, 0.0))
        lines = [
            line for line in buf.getvalue().splitlines()
            if line.startswith("LANE_B_MOB_AI_TICK")
        ]
        self.assertEqual(lines, [])

    def test_the_fired_token_lands_on_stderr_not_stdout(self):
        # Same reason as every other lane_hooks direct-call consumer
        # (announce_direct_fire's own docstring): a --json tool's stdout
        # contract must stay pure JSON even once a future runtime.py round
        # wires this in.
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                lane_b_mob_ai_tick.maybe_tick(
                    self.dummy_register, self.dummy_ledger, PLAYER,
                    (0.0, 0.0, 0.0))
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertNotIn("LANE_HOOK_FIRED", out.getvalue())

    def test_a_mismatched_ledger_still_raises_not_swallowed(self):
        dummy_roster = field_mobs.load_roster()
        dummy_ledger = mob_combat.open_ledger(dummy_roster)
        with self.assertRaises(mob_combat.MobCombatContractError):
            lane_b_mob_ai_tick.maybe_tick(
                self.register, dummy_ledger, PLAYER, (0.0, 0.0, 0.0))


class WiringLineTests(unittest.TestCase):
    def test_the_wiring_line_names_dispatch_and_the_target_pos_vital(self):
        line = lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING
        self.assertIn("runtime.py dispatch", line)
        self.assertIn("TARGET_POS_VITAL", line)
        self.assertIn("identity_hi", line)
        self.assertIn("identity_lo", line)
        self.assertIn("lane_b_mob_ai_tick.maybe_tick", line)

    def test_the_wiring_line_orders_the_attribute_not_a_typed_key(self):
        # ROUND `a7k5gy`, COO-DECISION 2026-09-03T16:47+07:00 item 3 -- THE
        # ROOT CAUSE WAS IN THIS FILE, not in the chief's.  This wiring line
        # ordered the gate call with a hand-typed
        # 'lane_hooks.lane_b_mob_ai_tick', the chief pasted it verbatim into
        # runtime.py:5887 as an order from this file is meant to be pasted, and
        # lane_hooks.__init__ prefixed it into a key that exists nowhere.  The
        # gate answered False on every frame from the day the wiring landed
        # (5ac93b31, 2026-08-31 -- three days, not the eight a draft of this
        # comment borrowed off a neighbouring fact, pf-adversary D4) and the
        # only card watching was a substring search for "maybe_tick(", which
        # stayed green because the CALL was there; the gate above it was not
        # being read.
        #
        # THE GUARD, and why it is shaped like this: a literal in an order is
        # wrong in a way no reader sees, because it is a string in prose and
        # nobody diffs prose against a registry.  MODULE_NAME is the key
        # _discover() actually registers, so it cannot drift from it.  This
        # card therefore requires the ATTRIBUTE and forbids ANY quoted form of
        # the module's name inside the gate order -- not just today's exact
        # spelling, since the next hand-typed key would be a different wrong
        # string, and a card that only knows the last mistake is a card against
        # history.
        line = lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING
        opener = "module_production_allowed("
        self.assertIn(opener, line)
        # THE ARGUMENTS ONLY, AND ALL OF THEM.  Two earlier drafts of this
        # card were wrong in opposite directions and pf-adversary measured
        # both (D5):
        #  * the first forbade any quoted word starting "lane" ANYWHERE in the
        #    string.  Over-broad: this same order already quotes
        #    'from .lane_hooks import lane_b_mob_ai_tick' as the import a
        #    future round must add -- prose about a source line, not a key
        #    handed to a resolver -- and any future 'lane_id' dict key or
        #    'lane_b_tick' telemetry string would be accused of the
        #    20260903_1647 defect it has nothing to do with.
        #  * the second read only the FIRST module_production_allowed( in the
        #    order.  Under-broad: an order that gates correctly on
        #    MODULE_NAME and then gates a SECOND lane on a hand-typed key
        #    passed every assertion, the chief pastes it, and the identical
        #    bug ships one module over in a line this card certified.
        # So: every gate the order places, and what may not appear in any of
        # their arguments is a quote.
        arguments = [chunk.split(")", 1)[0]
                     for chunk in line.split(opener)[1:]]
        for argument in arguments:
            for quote in ("'", '"'):
                self.assertNotIn(
                    quote, argument,
                    "the wiring order hands a gate a hand-typed key (%r): "
                    "that is the exact defect COO-DECISION 20260903_1647 "
                    "item 3 ordered removed from this line, and a literal "
                    "here is wrong in a way no reader of prose can see"
                    % (argument,))
        self.assertIn(
            "lane_b_mob_ai_tick.MODULE_NAME", arguments,
            "the wiring order must hand the gate this module's own "
            "MODULE_NAME, so the argument cannot drift from the key "
            "lane_hooks._discover() registered -- it currently orders %r"
            % (arguments,))
        # And the attribute it orders has to EXIST and be the registry key, or
        # the order is a different kind of wrong: runtime.py would raise
        # AttributeError instead of silently answering False.
        self.assertEqual(
            lane_b_mob_ai_tick.MODULE_NAME,
            lane_b_mob_ai_tick.__name__,
            "MODULE_NAME is not this module's own __name__, so it is not the "
            "key lane_hooks registers it under")

    # ~~test_the_gate_answers_true_to_the_name_the_wiring_orders~~ -- WRITTEN
    # AND DELETED IN THE SAME ROUND (`a7k5gy`), by pf-adversary D3, which is
    # the round's own subject caught in the round's own new code.  It asserted
    # module_production_allowed(MODULE_NAME) is True.  But _discover()
    # registers under __name__, the card above already requires MODULE_NAME to
    # EQUAL __name__, and test_production_allowed_is_true_with_no_flag already
    # pins the flag -- so it was a whole test that could only fail after one of
    # those had already failed.  Decoration, and this diff's own prose condemns
    # it twelve lines away: "repeating it here would be a second copy, not a
    # second guard."  The one place that expression earns its keep is inside
    # tests/test_mob_aggro.py::test_the_tick_gate_is_reported_not_assumed,
    # where it is the CONTROL that separates "the argument did not resolve"
    # from "the lane was switched off" -- two states the gate answers
    # identically, on purpose, by its own docstring.

    def test_this_module_and_runtime_py_are_the_only_importers_in_src(self):
        # WAS test_this_module_is_the_only_importer_of_itself_in_src
        # (asserted the importer list was empty). COO-DECISION 20260901_0145
        # named runtime.py as the one call site this round wires -- a SECOND
        # importer beyond that would still be a second, undocumented call
        # site this round did not review, so the guard stays, just widened
        # by exactly one named file.
        importers = []
        for path in SRC_ROOT.rglob("*.py"):
            if path.name == "lane_b_mob_ai_tick.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
            names = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""] + [
                        alias.name for alias in node.names]
                if any("lane_b_mob_ai_tick" in name for name in names):
                    importers.append(str(path.relative_to(SRC_ROOT)))
        self.assertEqual(sorted(set(importers)), ["runtime.py"])


class _RecordingStore:
    """A stub that records, over a dict of vitals this test owns.

    A STUB AND NOT THE REAL STORE, ON PURPOSE, FOR THE BRANCH CARDS ONLY:
    these cards measure THIS lane's arithmetic (the clamp, the floor, the
    read-back comparison, what is and is not called), and a real database
    would measure LANE-DB's door instead.  The card that has to be driven
    against a real database -- because the claim there is "a number that
    survives on disk" -- is
    ``RealDatabaseDamageTests.test_the_write_lands_in_a_real_database``
    below, which uses no stub at all.
    """

    def __init__(self, hp_current, hp_max=100, level=1):
        self.vitals = _StubVitals(level, hp_current, hp_max)
        self.damage_calls = []
        self.reads = 0

    def read_character_vitals_or_none(self, character_id):
        self.reads += 1
        return self.vitals

    def apply_hp_damage(self, character_id, amount):
        self.damage_calls.append((character_id, amount))
        before = self.vitals.hp_current
        after = before - amount
        self.vitals = _StubVitals(
            self.vitals.level, after, self.vitals.hp_max)
        return _StubDamageOutcome(
            hp_before=before, hp_after=after, hp_max=self.vitals.hp_max,
            requested=amount, applied=amount, died=after <= 0,
            was_already_zero=before <= 0,
        )


class _StubVitals:
    def __init__(self, level, hp_current, hp_max):
        self.level = level
        self.hp_current = hp_current
        self.hp_max = hp_max


class _StubDamageOutcome:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _attack_results(*identities):
    """Real ``SchedulerStepResult`` rows, one attack decision each.

    Built through the shipped dataclass rather than out of simple objects so
    that a row this lane could never actually receive (identity 0, a
    non-string intent) refuses HERE, in the fixture, exactly as it would in
    production.
    """
    from pirateforce_foundation.mob_ai_scheduler import SchedulerStepResult
    return tuple(
        SchedulerStepResult(
            actor_identity=identity,
            before_phase=mob_aggro.PHASE_IDLE,
            after_phase=mob_aggro.PHASE_AGGRO,
            intent_kind=mob_aggro.INTENT_ATTACK_UNDELIVERABLE,
            intent_target_identity=PLAYER,
        )
        for identity in identities
    )


def _quiet_results(*identities):
    from pirateforce_foundation.mob_ai_scheduler import SchedulerStepResult
    return tuple(
        SchedulerStepResult(
            actor_identity=identity,
            before_phase=mob_aggro.PHASE_IDLE,
            after_phase=mob_aggro.PHASE_IDLE,
            intent_kind=mob_aggro.INTENT_NONE,
            intent_target_identity=None,
        )
        for identity in identities
    )


class PlayerDamageDoorTests(unittest.TestCase):
    """LANE-B round `nfrrqa`: the aggro tick's attack decision becomes HP.

    COO-DECISION 20260903_1745 point 2 gave this lane four rules and every
    card below is one of them going red when it is broken: the floor of 1
    is never written through, the write is read back, a line is printed,
    and ``store.py`` is not touched (nothing here patches or wraps a store
    method -- the module only calls two).
    """

    CHARACTER = 4242

    def _run(self, store, results, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            outcome = mob_ai_player_damage.apply_tick_damage(
                store, self.CHARACTER, results, **kwargs)
        return outcome, buf.getvalue()

    def test_a_tick_with_no_attack_decision_writes_nothing_and_is_silent(self):
        store = _RecordingStore(hp_current=100)
        outcome, printed = self._run(store, _quiet_results(0x2001, 0x2002))
        self.assertIsNone(outcome)
        self.assertEqual(store.damage_calls, [])
        # NOT EVEN A READ: the common case is every frame of every moving
        # player, so a door that opens a database read to decide it has
        # nothing to do is a cost paid continuously for nothing.
        self.assertEqual(store.reads, 0)
        self.assertEqual(printed, "")

    def test_one_attacker_costs_exactly_the_per_attack_number(self):
        store = _RecordingStore(hp_current=100)
        outcome, printed = self._run(store, _attack_results(0x2001))
        self.assertEqual(
            store.damage_calls,
            [(self.CHARACTER,
              mob_ai_player_damage.PLAYER_DAMAGE_PER_ATTACK_DECISION)])
        self.assertEqual(outcome.applied, outcome.requested)
        self.assertIs(outcome.floor_held, False)
        self.assertEqual(
            outcome.hp_after,
            100 - mob_ai_player_damage.PLAYER_DAMAGE_PER_ATTACK_DECISION)
        self.assertIn("MOB_AI_PLAYER_DAMAGE char=%d" % self.CHARACTER,
                      printed)

    def test_three_attackers_cost_three_times_it_in_one_write(self):
        # ONE WRITE, not three: this server is strictly serial (FINDINGS_R18)
        # and the damage door takes the write lock, so a per-attacker
        # transaction would be three lock acquisitions per frame for a number
        # that is a sum.
        store = _RecordingStore(hp_current=100)
        outcome, _printed = self._run(
            store, _attack_results(0x2001, 0x2002, 0x2003))
        self.assertEqual(len(store.damage_calls), 1)
        self.assertEqual(
            outcome.requested,
            3 * mob_ai_player_damage.PLAYER_DAMAGE_PER_ATTACK_DECISION)
        self.assertEqual(outcome.attackers, (0x2001, 0x2002, 0x2003))

    def test_the_floor_clamps_the_amount_instead_of_the_result(self):
        # hp 2, floor 1, three attackers asking for 3: the CLAMP is what
        # reaches the store, so the store is never asked for a write this
        # lane would then have to apologise for.
        store = _RecordingStore(hp_current=2)
        outcome, printed = self._run(
            store, _attack_results(0x2001, 0x2002, 0x2003))
        self.assertEqual(
            store.damage_calls,
            [(self.CHARACTER, 2 - mob_ai_player_damage.HP_FLOOR)])
        self.assertEqual(outcome.hp_after, mob_ai_player_damage.HP_FLOOR)
        self.assertIs(outcome.floor_held, True)
        self.assertIn("floor_held=1", printed)

    def test_a_player_already_at_the_floor_is_not_written_to_at_all(self):
        store = _RecordingStore(hp_current=mob_ai_player_damage.HP_FLOOR)
        outcome, printed = self._run(store, _attack_results(0x2001))
        self.assertIsNone(outcome)
        self.assertEqual(store.damage_calls, [])
        self.assertIn("MOB_AI_PLAYER_DAMAGE_STAND_DOWN", printed)
        self.assertIn(mob_ai_player_damage.STAND_DOWN_FLOOR_ALREADY_REACHED,
                      printed)

    def test_a_store_that_raises_stands_the_write_down_and_says_so(self):
        class _Angry:
            def read_character_vitals_or_none(self, character_id):
                raise RuntimeError("database is locked: C:\\\\pf\\\\state.db")

        outcome, printed = self._run(_Angry(), _attack_results(0x2001))
        self.assertIsNone(outcome)
        self.assertIn("store_cannot_be_asked", printed)
        # ASCII, always: the line interpolates the STORE's exception, which
        # can carry a Windows path with anything in it, and the bridge
        # console is cp874 with errors='strict'.
        printed.encode("ascii")

    def test_a_none_store_is_refused_by_name_not_crashed_on(self):
        # The wiring order tells the chief to pass a store fetched with
        # getattr(..., None), so None is a value this door will really be
        # handed on a session whose lifecycle is not up yet.
        outcome, printed = self._run(None, _attack_results(0x2001))
        self.assertIsNone(outcome)
        self.assertIn("store_cannot_be_asked", printed)

    def test_unreadable_vitals_stand_the_write_down(self):
        class _Unseeded:
            def read_character_vitals_or_none(self, character_id):
                return None

        outcome, printed = self._run(_Unseeded(), _attack_results(0x2001))
        self.assertIsNone(outcome)
        self.assertIn("vitals_not_readable", printed)

    def test_a_read_back_that_disagrees_raises_instead_of_logging(self):
        # THE CARD THAT COSTS THE MOST TO GET WRONG.  A store that reports a
        # write it did not make is the one failure this lane may not swallow
        # (house rule: a write that reports success and does not land is a
        # failure), so this is a raise and not a console line.
        class _Liar(_RecordingStore):
            def apply_hp_damage(self, character_id, amount):
                outcome = super().apply_hp_damage(character_id, amount)
                # put the row back, as a lost write would
                self.vitals = _StubVitals(
                    self.vitals.level, outcome.hp_before, self.vitals.hp_max)
                return outcome

        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            self._run(_Liar(hp_current=100), _attack_results(0x2001))
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_WRITE_DID_NOT_LAND)

    def test_a_read_back_that_refuses_after_the_write_also_raises(self):
        # pf-adversary D8: replacing this branch with `return None` left the
        # whole suite green, in the one place the module's own docstring
        # calls "the important half ... which may never be swallowed".  A
        # read that WORKED one line ago and refuses after the write is not
        # the ordinary unseeded case; it is a row that moved under us.
        class _GoesBlindAfterTheWrite(_RecordingStore):
            def read_character_vitals_or_none(self, character_id):
                if self.damage_calls:
                    return None
                return super().read_character_vitals_or_none(character_id)

        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            self._run(_GoesBlindAfterTheWrite(hp_current=100),
                      _attack_results(0x2001))
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_WRITE_DID_NOT_LAND)

    def test_a_write_the_store_refuses_stands_down_and_does_not_raise(self):
        # pf-adversary D7: the READ was wrapped and the WRITE was not, and
        # the write is the one with a documented failure mode -- the damage
        # door gives up after DAMAGE_LOCK_BUSY_TIMEOUT_MS, which on this
        # strictly serial server happens whenever a healing door holds the
        # same lock.  A raise there would come out of dispatch(), taking a
        # walking player's session with it AND skipping runtime.py's own
        # close of the GM warp-confirm window a few lines below the call.
        # Nothing committed, so this is an environment refusal, by name.
        class _LockedOut(_RecordingStore):
            def apply_hp_damage(self, character_id, amount):
                raise RuntimeError("database is locked")

        store = _LockedOut(hp_current=100)
        outcome, printed = self._run(store, _attack_results(0x2001))
        self.assertIsNone(outcome)
        self.assertIn(mob_ai_player_damage.REFUSE_STORE_CANNOT_BE_ASKED,
                      printed)
        self.assertEqual(store.vitals.hp_current, 100)

    def test_a_character_id_that_is_not_a_positive_int_is_refused(self):
        # pf-adversary D8: deleting _require_character_id left the suite
        # green -- a whole named refusal nothing executed.
        store = _RecordingStore(hp_current=100)
        for bad in (0, -1, None, "4242", True):
            with self.subTest(character_id=bad):
                with self.assertRaises(
                        mob_ai_player_damage.MobAiPlayerDamageError) as caught:
                    with redirect_stdout(io.StringIO()):
                        mob_ai_player_damage.apply_tick_damage(
                            store, bad, _attack_results(0x2001))
                self.assertEqual(
                    caught.exception.reason,
                    mob_ai_player_damage.REFUSE_IDENTITY_NOT_POSITIVE)
        self.assertEqual(store.damage_calls, [])

    def test_a_per_attack_that_is_not_a_positive_int_is_refused(self):
        # pf-adversary D8, same shape: the validation was dead to the suite.
        store = _RecordingStore(hp_current=100)
        for bad in (0, -3, None, 1.0):
            with self.subTest(per_attack=bad):
                with self.assertRaises(
                        mob_ai_player_damage.MobAiPlayerDamageError):
                    with redirect_stdout(io.StringIO()):
                        mob_ai_player_damage.apply_tick_damage(
                            store, self.CHARACTER, _attack_results(0x2001),
                            per_attack=bad)
        self.assertEqual(store.damage_calls, [])

    def test_a_result_row_that_is_not_a_typed_record_is_refused(self):
        # pf-adversary D8: both type guards in attack_decisions were dead.
        class _Loose:
            def __init__(self, kind, actor):
                self.intent_kind = kind
                self.actor_identity = actor

        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            mob_ai_player_damage.attack_decisions([_Loose(None, 0x2001)])
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_TYPE_NOT_TYPED_RECORD)
        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            mob_ai_player_damage.attack_decisions(
                [_Loose(mob_aggro.INTENT_ATTACK_UNDELIVERABLE, 0)])
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_IDENTITY_NOT_POSITIVE)

    def test_the_console_line_reports_every_number_the_outcome_carries(self):
        # pf-adversary D8: hp_max and hp_before could be replaced with
        # anything and no card noticed, while both are printed.
        store = _RecordingStore(hp_current=57, hp_max=123)
        outcome, printed = self._run(store, _attack_results(0x2001))
        self.assertEqual(outcome.hp_before, 57)
        self.assertEqual(outcome.hp_max, 123)
        self.assertIn("hp=57->56/123", printed)

    def test_an_outcome_that_reports_a_death_raises(self):
        # The floor above makes this unreachable through this lane's own
        # arithmetic; the card exists because the floor is enforced HERE and
        # a store whose own floor is zero is one refactor away from being the
        # thing that kills a player.
        class _Overkill(_RecordingStore):
            def apply_hp_damage(self, character_id, amount):
                outcome = super().apply_hp_damage(character_id, amount)
                outcome.died = True
                return outcome

        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            self._run(_Overkill(hp_current=100), _attack_results(0x2001))
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_FLOOR_WAS_BREACHED)

    def test_attack_decisions_reads_the_constant_not_a_spelling(self):
        # The three-day defect this lane paid for was a hand-typed string
        # standing in for a name.  If mob_aggro renames its intent, this
        # door must follow it, not keep matching a literal.
        results = _attack_results(0x2001)
        self.assertEqual(
            mob_ai_player_damage.attack_decisions(results), (0x2001,))
        renamed = [r for r in _quiet_results(0x2002)]
        self.assertEqual(
            mob_ai_player_damage.attack_decisions(renamed), ())
        source = (SRC_ROOT / "mob_ai_player_damage.py").read_text(
            encoding="utf-8")
        self.assertNotIn(
            '"' + mob_aggro.INTENT_ATTACK_UNDELIVERABLE + '"', source)


class MaybeTickDamageOptInTests(unittest.TestCase):
    """The two optional arguments are the whole opt-in, and they are a pair."""

    def setUp(self):
        bg0002_roster = field_mobs._parse_hostile_placements(
            field_mob_tables_bg0002)
        self.by_placement = {m.placement_index: m for m in bg0002_roster}
        self.register = mob_ai_control.open_register(bg0002_roster)
        self.ledger = mob_combat.open_ledger(bg0002_roster)
        self.mob = self.by_placement[BG0002_OFFENSIVE_PLACEMENT]

    def _tick(self, **kwargs):
        buf = io.StringIO()
        with redirect_stdout(buf):
            register, results = lane_b_mob_ai_tick.maybe_tick(
                self.register, self.ledger, PLAYER,
                (self.mob.x, self.mob.y, self.mob.z), **kwargs)
        return register, results, buf.getvalue()

    def test_todays_call_site_passes_neither_and_touches_no_database(self):
        # This is what runtime.py does RIGHT NOW, and this card is what makes
        # "nothing changed for a player this round" a measurement instead of
        # a sentence in a PR body.
        _register, results, printed = self._tick()
        self.assertNotIn("MOB_AI_PLAYER_DAMAGE", printed)
        self.assertTrue(any(
            r.intent_kind == mob_aggro.INTENT_ATTACK_UNDELIVERABLE
            for r in results),
            "this fixture must produce the intent the door reads, or the "
            "card above proves nothing")

    def test_passing_both_writes_and_prints(self):
        store = _RecordingStore(hp_current=100)
        _register, _results, printed = self._tick(
            store=store, character_id=4242)
        self.assertEqual(len(store.damage_calls), 1)
        self.assertIn("MOB_AI_PLAYER_DAMAGE char=4242", printed)
        # The tick's own console lines survive the damage door: a refusal
        # there may not eat the evidence of the tick that produced it.
        self.assertIn("LANE_B_MOB_AI_TICK", printed)

    def test_a_store_with_no_character_is_a_caller_defect_and_raises(self):
        store = _RecordingStore(hp_current=100)
        with self.assertRaises(
                mob_ai_player_damage.MobAiPlayerDamageError) as caught:
            self._tick(store=store)
        self.assertEqual(caught.exception.reason,
                         mob_ai_player_damage.REFUSE_IDENTITY_NOT_POSITIVE)
        self.assertEqual(store.damage_calls, [])

    def test_a_character_with_no_store_stands_down_and_the_tick_survives(self):
        # pf-adversary D3, MEASURED ON A SHIPPED SESSION CLASS.  The first
        # draft raised here, symmetrically with the card above.  That was
        # wrong, and the proof is that the published order -- pasted
        # verbatim, as an order is meant to be -- produces exactly this
        # shape on `session.ReadOnlyFoundationSession`, which `app.py`
        # installs for every scene-load scenario: it has a `store` but no
        # `lifecycle`, so the order's getattr chain yields None while
        # `selected.id` is a real number.  The raise came out of dispatch()
        # and took the session's frame with it.  A missing store is an
        # ENVIRONMENT fact -- the module's own order already promised it
        # would be "refused by name, never crashed on" -- so it stands down,
        # says so once per process, and the tick still runs.
        del lane_b_mob_ai_tick._STORELESS_ANNOUNCED[:]
        _register, results, printed = self._tick(character_id=4242)
        self.assertIn(mob_ai_player_damage.REFUSE_STORE_CANNOT_BE_ASKED,
                      printed)
        self.assertTrue(any(
            r.intent_kind == mob_aggro.INTENT_ATTACK_UNDELIVERABLE
            for r in results),
            "the tick must still have run: standing the WRITE down may not "
            "stand the decision loop down with it")
        # ONCE PER PROCESS, not once per frame: this fires on every TargetPos
        # such a session sends, and a truth repeated that often is noise.
        _r2, _res2, printed_again = self._tick(character_id=4242)
        self.assertNotIn(mob_ai_player_damage.REFUSE_STORE_CANNOT_BE_ASKED,
                         printed_again)

    def test_the_order_names_the_arguments_the_function_really_takes(self):
        # THE BINDING THE THREE-DAY DEFECT DID NOT HAVE.  The order is a
        # string the chief pastes; if it names a keyword this function does
        # not accept, the paste is refused at import time on a live server.
        # So the order is parsed and bound against the real signature here,
        # rather than both being read by a human.
        import inspect
        order = lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING
        signature = inspect.signature(lane_b_mob_ai_tick.maybe_tick)
        for keyword in ("store=", "character_id="):
            self.assertIn(keyword, order)
            self.assertIn(keyword[:-1], signature.parameters)
        self.assertIn("store=", mob_ai_player_damage
                      .MOB_AI_PLAYER_DAMAGE_WIRING)
        # ON HOLD, and the marker says so in ASCII a grep can find -- IN THE
        # ORDER ITSELF, not only in the module that owns the door.  An order
        # is a thing somebody pastes: a hold notice a reader has to go to
        # another file to find is a hold notice that does not exist.
        for text in (order,
                     mob_ai_player_damage.MOB_AI_PLAYER_DAMAGE_WIRING,
                     (SRC_ROOT / "mob_ai_player_damage.py").read_text(
                         encoding="utf-8")):
            self.assertIn("MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD", text)

    def test_the_hold_is_a_state_of_runtime_py_and_not_a_comment(self):
        # pf-adversary D2 OF THIS ROUND, AND THE QUESTION IT CLOSED WITH:
        # "what, executable, goes red on the day someone pastes those two
        # keyword arguments into runtime.py without a COO answer?"  It
        # measured that the answer was NOTHING -- it pasted the order and
        # every card in the round stayed green, because the only thing
        # holding the hold was a string in a comment.  This card is the
        # answer, and it is the whole point of writing it: the marker and
        # the call site are read TOGETHER, out of the AST, so exactly one of
        # the two states is green.
        #
        # WHILE THE MARKER STANDS: the maybe_tick call in runtime.py must
        # pass NEITHER keyword.  THE DAY THE COO ANSWERS: the marker comes
        # out of the order in the same round the keywords go in, and this
        # card requires BOTH -- so a paste without an answer is red, and an
        # answer without a paste is red too.  Neither half can drift alone.
        runtime_tree = ast.parse(
            (SRC_ROOT / "runtime.py").read_text(encoding="utf-8"))
        passed = set()
        calls = 0
        for node in ast.walk(runtime_tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute)
                    and func.attr == "maybe_tick"):
                continue
            calls += 1
            passed.update(
                keyword.arg for keyword in node.keywords if keyword.arg)
        self.assertEqual(
            calls, 1,
            "expected exactly one maybe_tick call site in runtime.py; found "
            "%d, so this card cannot say which one carries the hold" % calls)
        held = "MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD" in (
            lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING)
        wired = {"store", "character_id"} & passed
        if held:
            self.assertEqual(
                wired, set(),
                "the order still carries MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD "
                "but runtime.py already passes %r to maybe_tick.  Either the "
                "COO answered and the marker must come out of the order in "
                "the same round, or this is the paste the hold exists to "
                "stop -- see pf_bridge/notes_to_chief/20260903_1952_LANE-B-"
                "ASK-COO-*" % (sorted(wired),))
        else:
            self.assertEqual(
                wired, {"store", "character_id"},
                "the hold marker is gone from the order, so the COO has "
                "answered -- but runtime.py passes %r.  A lifted hold with no "
                "call site is a door nobody opened wearing an open sign"
                % (sorted(wired),))


class RealDatabaseDamageTests(unittest.TestCase):
    """One card, on a real database, because the claim is about disk.

    Everything above measures this lane's arithmetic against a stub.  The
    sentence this round wants to be able to say -- "an attack decision
    becomes a number that survives" -- is about SQLite, so this card uses
    the real store, the real migrations and the real damage door, and reads
    the row back through a SECOND, independent read.
    """

    def setUp(self):
        import tempfile
        from pirateforce_foundation.model import Position
        from pirateforce_foundation.store import SQLiteStore
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations")
        self.store.migrate()
        account = self.store.ensure_account("lane-b-damage")
        character = self.store.create_character(
            account, "DamageDoor", "dd", "fingerprint-dd",
            lambda selector: (b"wire-%d" % selector, b"avatar",
                              0x30000001 + selector, 0),
            Position(1, 0, 1.0, 2.0, 3.0, heading=0.0))
        self.character_id = character.id

    def test_the_write_lands_in_a_real_database(self):
        before = self.store.read_character_vitals_or_none(self.character_id)
        self.assertIsNotNone(
            before, "migrations must seed a new character's vitals, or this "
                    "card is measuring the stand-down path instead")
        buf = io.StringIO()
        with redirect_stdout(buf):
            outcome = mob_ai_player_damage.apply_tick_damage(
                self.store, self.character_id, _attack_results(0x2001, 0x2002))
        expected = (
            before.hp_current
            - 2 * mob_ai_player_damage.PLAYER_DAMAGE_PER_ATTACK_DECISION)
        self.assertEqual(outcome.hp_after, expected)
        # THE INDEPENDENT READ: not the outcome the door returned, and not
        # the one this lane already read back inside it.
        again = self.store.read_character_vitals_or_none(self.character_id)
        self.assertEqual(again.hp_current, expected)
        self.assertIn("MOB_AI_PLAYER_DAMAGE char=%d" % self.character_id,
                      buf.getvalue())

    def test_the_floor_holds_against_the_real_door_whose_floor_is_zero(self):
        # store.apply_hp_damage floors at ZERO and reports died=True.  This
        # card drives a character down to 1 through the real door and then
        # asks this lane for more: the store would happily write 0, and this
        # lane must not let it.
        vitals = self.store.read_character_vitals_or_none(self.character_id)
        self.store.apply_hp_damage(
            self.character_id,
            vitals.hp_current - mob_ai_player_damage.HP_FLOOR)
        buf = io.StringIO()
        with redirect_stdout(buf):
            outcome = mob_ai_player_damage.apply_tick_damage(
                self.store, self.character_id, _attack_results(0x2001))
        self.assertIsNone(outcome)
        after = self.store.read_character_vitals_or_none(self.character_id)
        self.assertEqual(after.hp_current, mob_ai_player_damage.HP_FLOOR)
        self.assertIs(after.alive, True)
        self.assertIn(mob_ai_player_damage.STAND_DOWN_FLOOR_ALREADY_REACHED,
                      buf.getvalue())


class HitFrameDoorBTests(unittest.TestCase):
    """DOOR B (`mob_hit_frame`): the frame a hit would send, and the four
    gates holding it shut.

    THIS CLASS IS THE SECOND DRAFT.  The first one was measured by
    pf-adversary and it was worse than it read: its "full live block" card
    compared the door's output against the door's own input, so it proved
    forwarding and called it completeness (round `5pvte3`'s own D2), while
    the block it composed omitted 29 of 55 rows -- every row the client's
    full-object copy would then zero, including cash.

    THAT DRAFT ASKED `persistence_attr_compose`, LANE-DB's adjudicator,
    directly.  `COO-DECISION 20260904_0546` (round `f2qyxx`'s own D2)
    withdrew it from this door's adjudication path entirely: Door B's frame
    is about `gm/attr_wire.named_field_x()`, the 26-row named set, never
    LANE-DB's 55-row persistence block.  The completeness promise `RE-222`
    demands did not go away -- it is enforced by
    `gm.attr_wire.build_named_field_update` itself now, against the
    CONNECTION's own cache, not by a second check this door used to run and
    then discard the result of.  The cards below test that shape.
    """

    def setUp(self):
        from pirateforce_foundation import mob_hit_frame
        from pirateforce_foundation.gm import attr_wire
        from pirateforce_foundation.legacy_bridge import load_legacy
        self.door = mob_hit_frame
        self.attr_wire = attr_wire
        self.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        self.character_id = 0x750059
        self.identity = (0x11, 0x22)

    # -- helpers -----------------------------------------------------------

    @contextlib.contextmanager
    def _gates(self, lane_b=0, encoder=0):
        """Open one or both gates for the duration of a card.

        Patched, never edited on disk: this lane may not set its own gate
        without the GT ticket `COO-DECISION 20260904_0045` names, and it may
        not set LANE-GM's at all.  A non-`int` for either argument leaves
        that gate shut, which is the contract the door reads.
        """
        sentinel = object()
        name = self.door.ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR
        previous = getattr(self.attr_wire, name, sentinel)
        # pf-adversary D14, MEASURED: this finally block used to restore
        # `MOB_HIT_FRAME_CONFIRMED` to a hardcoded `None` instead of the
        # value it actually held before this context manager patched it --
        # inconsistent with gate (i)'s own `previous`/`sentinel` dance three
        # lines below, which restores the REAL prior value.  Harmless only
        # because nothing else in this suite leaves that constant non-None
        # across a test boundary today; a future nested `_gates` use (or a
        # module-level fixture that pre-sets it) would have this context
        # manager silently clobber a value it never touched.
        previous_lane_b = self.door.MOB_HIT_FRAME_CONFIRMED
        self.door.MOB_HIT_FRAME_CONFIRMED = lane_b
        if encoder is None:
            if previous is not sentinel:
                delattr(self.attr_wire, name)
        else:
            setattr(self.attr_wire, name, encoder)
        try:
            yield
        finally:
            self.door.MOB_HIT_FRAME_CONFIRMED = previous_lane_b
            if previous is sentinel:
                if hasattr(self.attr_wire, name):
                    delattr(self.attr_wire, name)
            else:
                setattr(self.attr_wire, name, previous)

    def _compose(self, hp_after=90, hook=None, cache=-1):
        """Run the door, capturing stdout, and return `(result, console)`."""
        class _Hooks:
            pass
        module = _Hooks()
        if hook is not None:
            setattr(module, self.door.LIVE_ATTR_VALUES_HOOK_ATTR, hook)
        if cache == -1:
            cache = self.attr_wire.RawBlockCache()
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            result = self.door.compose_player_hit_frame(
                self.legacy, cache, self.character_id, self.identity[0],
                self.identity[1], hp_after, lane_hooks_module=module)
        return result, buffer.getvalue()

    def _adjudicated_live_values(self):
        """A hook payload THIS DOOR's own adjudication would accept.

        Built from `attr_wire.named_field_x()` -- the 26-row set
        `COO-DECISION 20260904_0546` settled Door B's frame is about, never
        LANE-DB's 55-row `persistence_attr_compose` block (withdrawn from
        this door entirely, pf-adversary D2).  Derived rather than written
        out, so the day LANE-GM renames or widens `named_field_x()` this
        helper follows it instead of pinning a stale set.  `None` only if
        that set is ever empty -- not reachable on this tree, kept as a
        guard rather than an assumption.
        """
        wanted = self.attr_wire.named_field_x()
        if not wanted:
            return None
        supplied = {}
        for x in wanted:
            field = self.attr_wire.BY_X[x]
            supplied[x] = "Ann" if field[5] == "wstr" else 2
        return supplied

    def _full_valid_baseline(self):
        """`{x: value}` for every `attr_wire.FIELDS` row, type-correct for
        each row's own `kind` -- NOT an adjudicated block (LANE-DB stands
        behind none on this tree, see `_adjudicated_live_values`).
        `RawBlockCache` is source-agnostic by its own docstring, so seeding
        one for a card that only needs the ENCODER to survive a bad byte
        (pf-adversary D12) needs no LANE-DB sign-off -- only shapes
        `attr_wire.validate_field_value` itself would accept.
        """
        values = {}
        for field in self.attr_wire.FIELDS:
            x, kind = field[0], field[5]
            if kind == "wstr":
                values[x] = "x"
            elif kind == "blob":
                values[x] = b""
            elif kind == "f32":
                values[x] = 0.0
            else:
                values[x] = 0
        return values

    # -- the gates ---------------------------------------------------------

    def test_shipped_state_is_every_gate_shut(self):
        # THIS CARD IS WHAT CLOSED server `#694` AND `#697`.  Its first
        # draft read `assertIsNone(hook)` -- it pinned the ABSENCE of
        # another lane's code (`lane_hooks.current_named_attr_values`) as
        # this door's shipped state, so the hour chief landed the read
        # point on `main` (server `#695`, R330) the card went red on a
        # branch that had not changed a line of it.  The branch was cut
        # before `#695`, the push-triggered gate ran the pure branch and
        # was GREEN, the pull_request gate ran branch-merged-with-`main`
        # and was RED, and the reaper closed the round on the red one.
        #
        # What is actually shipped-shut is THIS LANE's two gates, and they
        # are shut whoever else has landed what: gate (ii) is read before
        # a single byte is built, and gate (i) right after it, both ahead
        # of the read point in `compose_player_hit_frame`.  So the card
        # now measures the door, not the calendar.
        #
        # SECOND DRAFT, pf-adversary D1, MEASURED: this card's first rewrite
        # still carried `assertFalse(hit_frame_encoder_unlocked())`, and the
        # adversary landed `FULL_BLOCK_UNLOCK_CONFIRMED = 0` in
        # `gm/attr_wire.py` and turned this card red -- with the constant
        # THIS ROUND'S OWN LETTER asks LANE-GM to define.  That is the same
        # death, one file over: the day LANE-GM answers, a branch cut before
        # that hour is green on the push gate and red on the pull_request
        # gate.  So the shipped-state card now names ONE thing, and it is
        # this lane's own: gate (ii).  The encoder gate is read as a
        # CONTRACT under `_gates`, in the cards below, where the value is
        # patched and never read off whatever `main` happens to hold.
        self.assertIsNone(self.door.MOB_HIT_FRAME_CONFIRMED)
        # ...and the door composed through the REAL `lane_hooks` -- not a
        # stand-in -- still sends nothing and says which gate stopped it.
        with redirect_stdout(io.StringIO()) as buffer:
            result = self.door.compose_player_hit_frame(
                self.legacy, self.attr_wire.RawBlockCache(),
                self.character_id, self.identity[0], self.identity[1], 90)
        self.assertIsNone(result)
        self.assertIn("MOB_HIT_FRAME_STANDDOWN reason=%s"
                      % self.door.STANDDOWN_GATE_NOT_CONFIRMED,
                      buffer.getvalue())

    def test_the_gates_helper_restores_the_lane_gate_it_actually_held(self):
        # pf-adversary D14, MEASURED: `_gates`' own `finally` block used to
        # hardcode `MOB_HIT_FRAME_CONFIRMED = None` on the way out instead
        # of restoring whatever value was really there on entry --
        # inconsistent with how the SAME context manager already treats
        # gate (i) three lines below (`previous`/`sentinel`).  Nesting one
        # `_gates()` call inside another is what makes the bug observable:
        # with the old code the inner call's exit stomped the outer call's
        # value back to `None` instead of leaving it standing.
        self.assertIsNone(self.door.MOB_HIT_FRAME_CONFIRMED)
        with self._gates(lane_b=7, encoder=0):
            self.assertEqual(self.door.MOB_HIT_FRAME_CONFIRMED, 7)
            with self._gates(lane_b=9, encoder=0):
                self.assertEqual(self.door.MOB_HIT_FRAME_CONFIRMED, 9)
            self.assertEqual(
                self.door.MOB_HIT_FRAME_CONFIRMED, 7,
                "the inner _gates() call did not restore the outer call's "
                "own value on exit")
        self.assertIsNone(self.door.MOB_HIT_FRAME_CONFIRMED)

    def test_the_read_point_resolution_is_consistent_either_way(self):
        # SECOND DRAFT, pf-adversary D13, MEASURED: the first one read the
        # REAL tree and branched on what it found, so on a tree where the
        # hook exists it asserted `callable(hook)` about a value the
        # function only returns AFTER checking `callable` -- a tautology.
        # The adversary deleted the callable guard from `mob_hit_frame.py`
        # outright and the whole file stayed green.  It also mislabelled its
        # other branch: an unimportable `lane_hooks` answers "importing
        # lane_hooks raised ...", which does not contain the attribute name.
        #
        # So the contract is exercised with STAND-IN MODULES, one per
        # branch, and every branch can now die for its own reason.
        class _Empty:
            pass

        class _NotCallable:
            pass
        setattr(_NotCallable, self.door.LIVE_ATTR_VALUES_HOOK_ATTR, 7)

        class _Good:
            pass
        setattr(_Good, self.door.LIVE_ATTR_VALUES_HOOK_ATTR,
                staticmethod(lambda cid: {3: 1}))

        hook, why_not = self.door.resolve_live_attr_values(_Empty)
        self.assertIsNone(hook)
        self.assertIn(self.door.LIVE_ATTR_VALUES_HOOK_ATTR, why_not)
        self.assertIn("not defined on this tree", why_not)

        hook, why_not = self.door.resolve_live_attr_values(_NotCallable)
        self.assertIsNone(hook, "a non-callable read point resolved as one")
        self.assertIn("not callable", why_not)

        hook, why_not = self.door.resolve_live_attr_values(_Good)
        self.assertTrue(callable(hook))
        self.assertEqual(why_not, "")

    def test_gate_none_composes_zero_bytes_whatever_else_is_open(self):
        # THE MUTANT `0045` ASKS FOR, run as a mutant rather than asserted as
        # a promise: every other thing the door needs is handed to it and the
        # ONLY shut thing is this lane's own constant.
        with self._gates(lane_b=None, encoder=0):
            result, console = self._compose(hook=lambda cid: {3: 1})
        self.assertIsNone(result)
        self.assertIn("MOB_HIT_FRAME_STANDDOWN reason=%s"
                      % self.door.STANDDOWN_GATE_NOT_CONFIRMED, console)

    def test_a_falsy_sentinel_does_not_open_either_gate(self):
        # pf-adversary D5: `_CONFIRMED` is a boolean-shaped name, and a
        # LANE-GM engineer landing `= False` to mean "named, not unlocked"
        # must not open this lane's door from the other side of the repo.
        for value in (False, True, "", "pending", 0.0, None):
            with self._gates(lane_b=0, encoder=value):
                self.assertFalse(
                    self.door.hit_frame_encoder_unlocked(),
                    "gate (i) opened on %r" % (value,))
            with self._gates(lane_b=value, encoder=0):
                result, console = self._compose(hook=lambda cid: {3: 1})
            self.assertIsNone(result, "gate (ii) opened on %r" % (value,))
            self.assertIn(self.door.STANDDOWN_GATE_NOT_CONFIRMED, console)

    def test_the_speed_exception_is_not_this_lanes_gate(self):
        # `0045` point 2: combat does NOT inherit the /speed sparse x=7
        # exception.  That exception is what set
        # UPDATE_ATTR_VITAL_VERSION_CONFIRMED, and this card measures that
        # the constant being set buys this door NOTHING.  It goes red the day
        # somebody "simplifies" gate (i) into reading that constant -- the
        # exact shortcut GT-218 punished.
        #
        # pf-adversary D3, MEASURED: an earlier draft of this card pinned
        # `assertIsNotNone(UPDATE_ATTR_VITAL_VERSION_CONFIRMED)` -- LANE-GM's
        # OWN constant, not this lane's.  `GT-218`'s own finding is that
        # withdrawing that exception is the SAFER direction, so a LANE-GM
        # round that does exactly that would turn this card red for a
        # reason entirely outside this lane's control, on a value this card
        # does not actually need for its own claim.  What this lane owns
        # and can promise is that its OWN gate name is never the /speed
        # exception's constant -- derived from source, not pinned as a
        # number that assumes the exception still exists, so this card
        # survives GM's withdrawal either way.
        self.assertNotEqual(
            self.door.ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR,
            "UPDATE_ATTR_VITAL_VERSION_CONFIRMED",
            "gate (i) must read gm.attr_wire.FULL_BLOCK_UNLOCK_CONFIRMED, "
            "never the /speed exception's own constant")
        with self._gates(lane_b=0, encoder=None):
            result, console = self._compose(hook=lambda cid: {3: 1})
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_ENCODER_LOCKED, console)
        # Whatever UPDATE_ATTR_VITAL_VERSION_CONFIRMED currently holds --
        # still set by the /speed exception, or None once LANE-GM withdraws
        # it -- is deliberately NOT asserted here: that value belongs to
        # LANE-GM, and this card's claim does not depend on it either way.

    def test_the_door_will_not_manufacture_a_connections_cache(self):
        # pf-adversary D6: a per-compose cache means the session cache never
        # learns what this lane sent, and the next /lv re-asserts the HP this
        # frame just changed.  attr_wire's own docstring says one instance
        # per CONNECTION; this door takes one and refuses to invent one.
        for absent in (None, object()):
            with self._gates(lane_b=0, encoder=0):
                result, console = self._compose(
                    hook=lambda cid: {3: 1}, cache=absent)
            self.assertIsNone(result)
            self.assertIn(self.door.STANDDOWN_NO_SESSION_CACHE, console)

    # -- the live source ---------------------------------------------------

    def test_no_read_point_stands_down_by_the_name_the_coo_wrote(self):
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(hook=None)
        self.assertIsNone(result)
        self.assertIn("MOB_HIT_FRAME_STANDDOWN reason=no_live_source", console)

    def test_the_door_matches_whichever_tree_it_is_running_on(self):
        # THE JOIN WITH THE CHIEF'S CORE-REQUEST, written so it can die on its
        # own rather than turning chief's landing round red: it does not pin
        # whether `lane_hooks.current_named_attr_values` exists, it pins that
        # this door AGREES with reality either way.
        from pirateforce_foundation import lane_hooks
        hook, why_not = self.door.resolve_live_attr_values()
        present = getattr(
            lane_hooks, self.door.LIVE_ATTR_VALUES_HOOK_ATTR, None)
        if callable(present):
            self.assertIs(hook, present)
            self.assertEqual(why_not, "")
        else:
            self.assertIsNone(hook)
            self.assertTrue(why_not)

    def test_a_read_point_that_raises_is_a_stand_down_not_a_crash(self):
        def _angry(character_id):
            raise RuntimeError("no row for %r" % (character_id,))
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(hook=_angry)
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_LIVE_SOURCE_REFUSED, console)

    def test_nothing_a_hook_can_return_reaches_an_uncaught_exception(self):
        # pf-adversary D4 measured FIVE uncaught paths out of the first
        # draft, one of them inside the refusal that existed to protect this.
        # Every row below is one of those, replayed.
        #
        # THREE OF THESE ARE ABOUT A *VALUE*, NOT A KEY -- and pf-adversary
        # D12, MEASURED, found that with this class's DEFAULT (fresh,
        # unseeded) cache, all three used to stop at the withdrawn
        # `block_gaps` completeness gate before ever reaching code that
        # inspects the value itself; `live`'s VALUES are never fed into the
        # frame this door builds (only the cache's own baseline and
        # `hp_after` are), so the only way to prove a bad value survives the
        # real encoder is to put it INTO a seeded cache, where
        # `attr_wire.build_named_field_update` will actually try to encode
        # it.  The other six payloads are about KEYS, which the door's own
        # checks inspect directly, so they keep the default unseeded cache.
        value_cases = {
            24: -1,        # a signed cash read (u64 field, negative)
            1: b"Panya",   # a BLOB where a wstr goes
            4: 100.0,      # a float on a u32 row
        }
        for x, bad_value in value_cases.items():
            baseline = self._full_valid_baseline()
            baseline[x] = bad_value
            cache = self.attr_wire.RawBlockCache()
            cache.capture_initial(baseline)
            with self._gates(lane_b=0, encoder=0):
                result, console = self._compose(
                    hook=lambda cid, v=x: {v: 1}, cache=cache)
            self.assertIsNone(result, "x=%d bad value composed" % (x,))
            self.assertIn(
                self.door.STANDDOWN_ENCODER_REFUSED, console,
                "x=%d bad value did not reach the real encoder" % (x,))

        key_payloads = (
            {9: 1, "scene": 1},           # mixed-type keys: the sorted() crash
            {39: 1},                      # half of a shared mask-bit pair
            {30: 1},                      # SENSITIVE_FIELDS
            {999: 1},                     # not a row at all
            {},                           # empty
            None,                         # not a dict
        )
        for payload in key_payloads:
            with self._gates(lane_b=0, encoder=0):
                result, console = self._compose(
                    hook=lambda cid, v=payload: v)
            self.assertIsNone(result, "payload %r composed" % (payload,))
            self.assertIn("MOB_HIT_FRAME_STANDDOWN reason=", console,
                          "payload %r produced no named line" % (payload,))

    def test_a_renamed_vital_row_is_a_stand_down_inside_the_gated_path(self):
        # LANE-GM moving their own table may turn this lane's cards red; it
        # may not take a walking player's dispatch down.
        original = dict(self.attr_wire.BY_NAME)
        self.attr_wire.BY_NAME.pop("hp_current")
        try:
            with self.assertRaises(MobAiPlayerDamageError):
                self.door.hit_frame_vital_rows()
            supplied = self._adjudicated_live_values()
            if supplied is not None:
                with self._gates(lane_b=0, encoder=0):
                    result, console = self._compose(
                        hook=lambda cid: dict(supplied))
                self.assertIsNone(result)
                self.assertIn(self.door.STANDDOWN_ENCODER_REFUSED, console)
        finally:
            self.attr_wire.BY_NAME.clear()
            self.attr_wire.BY_NAME.update(original)

    # -- the withdrawal: LANE-DB's persistence composer is not this door's --

    def test_the_door_never_touches_persistence_attr_compose(self):
        # THE CARD THAT CARRIES THIS ROUND'S WITHDRAWAL.  `COO-DECISION
        # 20260904_0546` settled the question `test_the_block_is_not_
        # adjudicated_on_this_tree` (WAS here: pinned `len(block_gaps({}))
        # == 55`) was blocked on: Door B's frame is about the 26-row
        # `gm/attr_wire.named_field_x()` set, never LANE-DB's 55-row
        # `persistence_attr_compose` block.  That module is withdrawn from
        # this door's adjudication path entirely (pf-adversary D2) --
        # measured out of the AST, same discipline as
        # `test_this_door_never_writes_into_the_connections_cache` above,
        # rather than asserted as a promise, so a reimport (even one nobody
        # calls) goes red on the line number.  Checked BOTH WAYS an import
        # could sneak back in -- the import statement itself, and a call to
        # either function through some other alias -- per the house rule
        # that a refusal claim must go red both ways, not a single scan.
        tree = ast.parse(
            (SRC_ROOT / "mob_hit_frame.py").read_text(encoding="utf-8"))
        import_hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "persistence_attr_compose" in alias.name:
                        import_hits.append(
                            "import %s:%d" % (alias.name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "persistence_attr_compose" in module:
                    import_hits.append(
                        "from %s import ...:%d" % (module, node.lineno))
                # `from . import persistence_attr_compose` (a relative
                # import, exactly the shape this module used before this
                # round) has `module is None` -- the name lives in the
                # ALIAS, not the module path.  MEASURED: the first draft of
                # this card checked `node.module` alone and reintroducing
                # that exact import line left it green.
                for alias in node.names:
                    if "persistence_attr_compose" in alias.name:
                        import_hits.append(
                            "from %s import %s:%d"
                            % (module or ".", alias.name, node.lineno))
        self.assertEqual(
            import_hits, [],
            "Door B re-imported LANE-DB's persistence composer: %r -- "
            "COO-DECISION 20260904_0546 withdrew it from this door's "
            "adjudication path entirely" % (import_hits,))
        call_hits = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (func.attr if isinstance(func, ast.Attribute)
                    else getattr(func, "id", None))
            if name in ("compose_full_block", "block_gaps"):
                call_hits.append("%s:%d" % (name, node.lineno))
        self.assertEqual(
            call_hits, [],
            "Door B calls LANE-DB's adjudicator: %r" % (call_hits,))

    def test_a_row_outside_the_named_set_is_refused(self):
        # A value for a row that is not in `named_field_x()` cannot honestly
        # be something a hit frame is "about" (`COO-DECISION 20260904_0546`:
        # the door adjudicates only against the 26-row named set, never
        # LANE-DB's 55-row block).  WAS `test_a_row_the_adjudicator_does_
        # not_own_is_refused`, measured against `persistence_attr_compose.
        # SERVER_OWNED_FIELDS` -- retired with that module's withdrawal.
        not_named = sorted(
            x for x in self.attr_wire.BY_X
            if x not in set(self.attr_wire.named_field_x()))
        self.assertTrue(not_named)
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(
                hook=lambda cid: {not_named[0]: 1})
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_LIVE_SOURCE_NOT_NAMED, console)

    def test_when_the_connection_cache_is_complete_the_frame_composes(self):
        # THE POSITIVE-PATH CARD.  WAS `test_when_the_adjudicator_agrees_
        # the_frame_is_a_full_block`, which asked `persistence_attr_
        # compose.compose_full_block` for an oracle -- retired along with
        # that dependency.  What proves a real frame can leave this door now
        # is narrower and matches what actually ships: a CONNECTION cache
        # that already satisfies `attr_wire.build_named_field_update`'s own
        # completeness gate (`all_field_x()`, seeded here with
        # `_full_valid_baseline()` -- source-agnostic, per `RawBlockCache`'s
        # own docstring, and something gate 3 forbids THIS door from
        # building for itself) plus a live source naming rows entirely
        # within `named_field_x()`.  The frame that comes out is built from
        # the CACHE's own values with only `hp_current` overridden -- NOT
        # from `live`, which this door never feeds into the bytes it sends
        # (module docstring, gate 4) -- so `expected_values` below is
        # derived from `baseline`, not from `supplied`.
        baseline = self._full_valid_baseline()
        cache = self.attr_wire.RawBlockCache()
        cache.capture_initial(baseline)
        supplied = self._adjudicated_live_values()
        self.assertIsNotNone(supplied)
        rows = self.door.hit_frame_vital_rows()
        expected_values = dict(baseline)
        expected_values[rows["hp_current"]] = 90
        expected = self.attr_wire.make_update_attr_frame(
            self.legacy, self.identity[0], self.identity[1], expected_values)
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(
                hp_after=90, hook=lambda cid: dict(supplied), cache=cache)
        self.assertIsNotNone(result)
        self.assertEqual(result, expected)
        self.assertEqual(console, "")
        _body, basic_mask, actor_mask = self.attr_wire.encode_block(
            self.legacy, self.identity[0], self.identity[1], expected_values)
        for field in self.attr_wire.FIELDS:
            mask = basic_mask if field[1] == "basic" else actor_mask
            self.assertTrue(mask & field[2],
                            "row %r is missing from the block" % (field[6],))
        # The cache now remembers what was actually sent
        # (`RawBlockCache.record_sent`, called by `build_named_field_update`
        # on success) -- the next command on this connection builds on real
        # prior state, not the stale baseline it started from.
        self.assertEqual(cache.current_values(), expected_values)

    # -- arguments still raise ---------------------------------------------

    def test_an_hp_outside_the_writable_range_is_refused_before_any_gate(self):
        for bad in (self.door.HP_FLOOR - 1, self.door.HP_CEILING + 1):
            with self.assertRaises(MobAiPlayerDamageError) as caught:
                self.door.compose_player_hit_frame(
                    self.legacy, self.attr_wire.RawBlockCache(),
                    self.character_id, 0x11, 0x22, bad)
            self.assertEqual(caught.exception.reason,
                             mob_ai_player_damage.REFUSE_FLOOR_WAS_BREACHED)

    # -- the four rows are LANE-GM's ---------------------------------------

    def test_the_four_vital_rows_are_resolved_from_the_encoders_own_table(self):
        # pf-adversary D5, MEASURED: an earlier draft pinned the raw indices
        # `{hp_current: 3, hp_max: 4, mp_current: 5, mp_max: 6}` by hand --
        # a second, hand-typed copy of a list that already exists at a real
        # source (`attr_wire.BY_NAME`).  Derived below instead, so a future
        # LANE-GM renumbering of `FIELDS` cannot silently agree with a
        # stale copy this card never re-reads.
        rows = self.door.hit_frame_vital_rows()
        expected = {
            name: self.attr_wire.BY_NAME[name][0]
            for name in self.door.HIT_FRAME_VITAL_FIELD_NAMES
        }
        self.assertEqual(
            rows, expected,
            "gm/attr_wire.FIELDS rows for %r have moved or been renamed.  "
            "This lane's hit frame is built out of exactly these four rows "
            "(COO-DECISION 20260904_0045); somebody has to come and say what "
            "changed before it composes another byte."
            % (self.door.HIT_FRAME_VITAL_FIELD_NAMES,))
        for name, x in rows.items():
            field = self.attr_wire.BY_X[x]
            self.assertEqual(field[6], name)
            self.assertTrue(field[7], "row %r stopped being known=True" % name)
            self.assertNotIn(x, self.attr_wire.SENSITIVE_FIELDS)
        self.assertEqual(self.door.HIT_FRAME_CHANGED_FIELD_NAME, "hp_current")

    # -- housekeeping ------------------------------------------------------

    def test_nothing_calls_this_door_yet(self):
        # A CALL, out of the AST -- not a substring.  pf-adversary D10: the
        # first draft's NONCLAIM cited `grep -rn compose_player_hit_frame
        # src/`, which also matches this module's own prose and the .pyc
        # files beside it.  A claim about call sites has to ask about calls.
        callers = []
        for path in sorted(SRC_ROOT.rglob("*.py")):
            if path.name == "mob_hit_frame.py":
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = (func.attr if isinstance(func, ast.Attribute)
                        else getattr(func, "id", None))
                if name == "compose_player_hit_frame":
                    callers.append("%s:%d" % (path.name, node.lineno))
        self.assertEqual(callers, [], "Door B grew a call site: %r" % (callers,))

    def test_this_door_never_writes_into_the_connections_cache(self):
        # pf-adversary round f2qyxx D7, MEASURED on the recovered draft:
        # `compose_player_hit_frame` ended with
        #     if not cache.is_captured(): cache.capture_initial(block)
        # so a door standing DOWN still left 55 rows in the CONNECTION's
        # RawBlockCache -- and `build_named_field_update` requires exactly
        # the 26 `named_field_x()` rows, so one refusal broke every later
        # named send on that connection.
        #
        # A behavioural card cannot reach that line today (LANE-DB's
        # adjudicator refuses all 55 rows first), and a card that cannot
        # reach the bug is a card that cannot die for it. So this asks the
        # AST, like `test_nothing_calls_this_door_yet` above: this module
        # calls NOTHING that mutates the cache it was handed. Re-add the
        # line and this goes red on the line number.
        mutators = ("capture_initial", "capture", "update", "seed",
                    "seed_cache_from_live_values")
        found = []
        tree = ast.parse(
            (SRC_ROOT / "mob_hit_frame.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in mutators:
                continue
            target = getattr(func.value, "id", None)
            if target in ("cache", "attr_wire"):
                found.append("%s.%s at line %d"
                             % (target, func.attr, node.lineno))
        self.assertEqual(
            found, [],
            "Door B writes into state it does not own: %r. The cache "
            "belongs to the connection and is seeded by its owner; this "
            "door reads it and composes from it, and on every refusal it "
            "leaves it exactly as it found it." % (found,))

    def test_this_module_is_pure_ascii(self):
        # The sibling guard `test_mob_stat_fabrication_guard` reads every
        # LANE-B module as ASCII and DIES on the first non-ASCII byte instead
        # of reporting it -- so one Thai character in this file silently
        # stops fifteen other modules from ever being swept.  The first draft
        # of this round shipped exactly that byte.  This card is the cheap
        # half of the fix that is inside this lane's own zone.
        for module in ("mob_hit_frame.py", "mob_ai_player_damage.py"):
            text = (SRC_ROOT / module).read_bytes()
            try:
                text.decode("ascii")
            except UnicodeDecodeError as exc:
                self.fail("%s is not pure ASCII: %s" % (module, exc))

    def test_every_stand_down_line_survives_the_bridge_console(self):
        for reason in self.door.MOB_HIT_FRAME_STAND_DOWN_REASONS:
            line = self.door.hit_frame_stand_down_line(
                reason, self.character_id, "path=C:\\pf\\\u0e01")
            line.encode("cp874", errors="strict")
            self.assertTrue(line.startswith("MOB_HIT_FRAME_STANDDOWN reason="))
        with self.assertRaises(AssertionError):
            self.door.hit_frame_stand_down_line("not_a_named_reason", 1, "")


if __name__ == "__main__":
    unittest.main()
