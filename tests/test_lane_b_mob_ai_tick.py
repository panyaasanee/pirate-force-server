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
        self.assertIn("floor_already_reached", printed)

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

    def test_passing_one_of_the_pair_refuses_instead_of_half_working(self):
        store = _RecordingStore(hp_current=100)
        for kwargs in ({"store": store}, {"character_id": 4242}):
            with self.subTest(kwargs=sorted(kwargs)):
                with self.assertRaises(
                        mob_ai_player_damage.MobAiPlayerDamageError):
                    self._tick(**kwargs)
        self.assertEqual(store.damage_calls, [])

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
        self.assertIn("floor_already_reached", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
