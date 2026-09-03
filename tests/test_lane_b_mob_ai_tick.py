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
    forwarding and called it completeness (D2), while the block it composed
    omitted 29 of 55 rows -- every row the client's full-object copy would
    then zero, including cash.  The cards below fix the oracle: completeness
    is asked of `persistence_attr_compose`, LANE-DB's adjudicator, and the
    frame is compared against an independently composed full block.
    """

    def setUp(self):
        from pirateforce_foundation import mob_hit_frame, persistence_attr_compose
        from pirateforce_foundation.gm import attr_wire
        from pirateforce_foundation.legacy_bridge import load_legacy
        self.door = mob_hit_frame
        self.attr_wire = attr_wire
        self.adjudicator = persistence_attr_compose
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
        self.door.MOB_HIT_FRAME_CONFIRMED = lane_b
        if encoder is None:
            if previous is not sentinel:
                delattr(self.attr_wire, name)
        else:
            setattr(self.attr_wire, name, encoder)
        try:
            yield
        finally:
            self.door.MOB_HIT_FRAME_CONFIRMED = None
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
        """A hook payload the adjudicator would actually stand behind.

        Derived from `persistence_attr_compose` rather than written out, so
        the day a row changes source class this helper follows it instead of
        pinning a stale set.  Returns `None` when no such payload exists --
        which is the case at this commit, and the point of
        `test_the_block_is_not_adjudicated_on_this_tree`.
        """
        supplied = {}
        for x, owned in self.adjudicator.SERVER_OWNED_FIELDS.items():
            field = self.attr_wire.BY_X[x]
            supplied[x] = "Ann" if field[5] == "wstr" else 2
        return supplied if not self.adjudicator.block_gaps(supplied) else None

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
        self.assertIsNone(self.door.MOB_HIT_FRAME_CONFIRMED)
        self.assertFalse(self.door.hit_frame_encoder_unlocked())
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

    def test_the_read_point_resolution_is_consistent_either_way(self):
        # The half of the old card worth keeping, written as a CONTRACT
        # instead of a snapshot: `resolve_live_attr_values` answers either
        # `(None, a reason naming the attribute)` or `(a callable, "")`.
        # Both branches are legal on `main` at different hours; a pair that
        # is neither is a bug in the door, and this card catches it in
        # whichever direction the tree happens to be pointing today.
        hook, why_not = self.door.resolve_live_attr_values()
        if hook is None:
            self.assertIn(self.door.LIVE_ATTR_VALUES_HOOK_ATTR, why_not)
        else:
            self.assertTrue(callable(hook))
            self.assertEqual(why_not, "")

    def test_the_chiefs_read_point_is_on_this_tree(self):
        # A DELIBERATE BASELINE ON ANOTHER LANE'S CODE, allowed to die on
        # its own (NOW.md, `0053`/`0149`): `COO-DECISION 20260904_0047`
        # point 1 ordered the read point and server `#695` landed it, and
        # Door B's whole route to a player runs through it.  If this card
        # goes red the read point left `main` -- that is news for this
        # lane, and it should arrive as a named failure here rather than
        # as a stand-down line nobody greps.
        hook, why_not = self.door.resolve_live_attr_values()
        self.assertIsNotNone(
            hook,
            "lane_hooks.%s is gone from this tree (%s); it landed in "
            "server #695 and Door B reads its live values through it"
            % (self.door.LIVE_ATTR_VALUES_HOOK_ATTR, why_not))

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
        self.assertIsNotNone(
            self.attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED,
            "the /speed exception is expected to still be in force; if it "
            "was withdrawn this card needs rewording, not deleting")
        with self._gates(lane_b=0, encoder=None):
            result, console = self._compose(hook=lambda cid: {3: 1})
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_ENCODER_LOCKED, console)

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
        payloads = (
            {24: -1},                     # a signed cash read
            {1: b"Panya"},                # a BLOB column where a wstr goes
            {4: 100.0},                   # a float the ordered signature allows
            {9: 1, "scene": 1},           # mixed-type keys: the sorted() crash
            {39: 1},                      # half of a shared mask-bit pair
            {30: 1},                      # SENSITIVE_FIELDS
            {999: 1},                     # not a row at all
            {},                           # empty
            None,                         # not a dict
        )
        for payload in payloads:
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

    # -- the adjudicator, which is the completeness oracle ------------------

    def test_the_block_is_not_adjudicated_on_this_tree(self):
        # THE CARD THAT CARRIES THE ROUND'S HONESTY.  `RE-222` says the
        # client's apply is a full-object copy, so a block is either complete
        # or it blanks what it omits.  "Complete" is not this lane's opinion
        # and not a count written here: it is
        # `persistence_attr_compose.block_gaps`, LANE-DB's own adjudicator,
        # built on the owner's ban of the guessed zero.  At this commit it
        # names all 55 rows, so the door stands down -- and the day somebody
        # closes those gaps, this card is what tells them Door B is now the
        # next thing to look at.
        gaps = self.adjudicator.block_gaps({})
        self.assertEqual(
            len(gaps), len(self.attr_wire.FIELDS),
            "block_gaps no longer refuses every row -- Door B's completeness "
            "oracle has moved and this lane must re-measure what its frame "
            "would now carry before anything flips a gate")
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(hook=lambda cid: {})
        self.assertIsNone(result)
        # An empty dict is refused as "no live source" before the
        # adjudicator; a non-empty one that the adjudicator will not stand
        # behind is refused by name.
        supplied = {x: 2 for x in
                    sorted(self.adjudicator.SERVER_OWNED_FIELDS)[:1]}
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(hook=lambda cid: dict(supplied))
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_BLOCK_NOT_ADJUDICATED, console)
        self.assertIn("block_gaps", console)

    def test_a_row_the_adjudicator_does_not_own_is_refused(self):
        # A value for a row LANE-DB does not treat as server-owned cannot
        # honestly enter a block; the door names that rather than letting
        # `compose_full_block` raise (pf-adversary D4).
        not_owned = sorted(
            x for x in self.attr_wire.BY_X
            if x not in self.adjudicator.SERVER_OWNED_FIELDS)
        self.assertTrue(not_owned)
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(
                hook=lambda cid: {not_owned[0]: 1})
        self.assertIsNone(result)
        self.assertIn(self.door.STANDDOWN_LIVE_SOURCE_NOT_SERVER_OWNED,
                      console)

    def test_when_the_adjudicator_agrees_the_frame_is_a_full_block(self):
        # The completeness card, with an oracle that is NOT the door's own
        # input (the mistake pf-adversary D2 measured).  It runs only in a
        # world where the adjudicator stands behind a block; on this tree it
        # does not, and the card says so out loud instead of passing quietly.
        supplied = self._adjudicated_live_values()
        if supplied is None:
            self.assertTrue(self.adjudicator.block_gaps({}))
            self.skipTest(
                "persistence_attr_compose stands behind no block at this "
                "commit, so there is no full block for Door B to compose; "
                "test_the_block_is_not_adjudicated_on_this_tree is the card "
                "that measures that")
        rows = self.door.hit_frame_vital_rows()
        expected_values = self.adjudicator.compose_full_block(supplied)
        expected_values[rows["hp_current"]] = 90
        expected = self.attr_wire.make_update_attr_frame(
            self.legacy, self.identity[0], self.identity[1], expected_values)
        with self._gates(lane_b=0, encoder=0):
            result, console = self._compose(
                hp_after=90, hook=lambda cid: dict(supplied))
        self.assertIsNotNone(result)
        self.assertEqual(result, expected)
        self.assertEqual(console, "")
        _body, basic_mask, actor_mask = self.attr_wire.encode_block(
            self.legacy, self.identity[0], self.identity[1], expected_values)
        for field in self.attr_wire.FIELDS:
            mask = basic_mask if field[1] == "basic" else actor_mask
            self.assertTrue(mask & field[2],
                            "row %r is missing from the block" % (field[6],))

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
        rows = self.door.hit_frame_vital_rows()
        self.assertEqual(
            rows,
            {"hp_current": 3, "hp_max": 4, "mp_current": 5, "mp_max": 6},
            "gm/attr_wire.FIELDS rows 3-6 have moved or been renamed.  This "
            "lane's hit frame is built out of exactly these four rows "
            "(COO-DECISION 20260904_0045); somebody has to come and say what "
            "changed before it composes another byte.")
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
