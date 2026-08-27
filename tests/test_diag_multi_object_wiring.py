"""GT-DIAG-MULTI-OBJECT-001: the runtime-facing wiring layer for GT-114.

Three things this file is built to prove, in this order of importance:

1. WITH THE GATE OFF -- which is every account on every boot of this
   repository, since no ``config/diag_multi_object.json`` is shipped -- every
   function in :mod:`diag_multi_object_wiring` is a no-op: it returns the
   caller's own objects, or the same bytes the production call already
   returned, so the four runtime.py call sites can be pasted in
   unconditionally and change nothing for a real login.
2. WITH THE GATE ON, the five objects reach the census additively (115 + 5 =
   120 on the wire, the original 115 entries byte-unchanged), resolve as
   combat targets, and dispatch their deaths by label at the two different
   holds RE-107 needs.
3. D1b IS NOT ANSWERED WITH A GUESS.  Nothing here passes
   ``target_vital_seen=True``, and two tests fail if a later edit does.
"""
from __future__ import annotations

import ast
import contextlib
import inspect
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import diag_multi_object_wiring as wiring  # noqa: E402
from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_combat  # noqa: E402
from pirateforce_foundation import mob_death  # noqa: E402
from pirateforce_foundation import mob_diag_multi_object as diag  # noqa: E402
from pirateforce_foundation import world_population  # noqa: E402
from pirateforce_foundation.diag_multi_object_config import CONFIG_KEY  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
ANCHOR = (diag.DIAG_CENTER_X, diag.DIAG_CENTER_Y, diag.DIAG_CENTER_Z)
PERFORMER = 0x750059
LETHAL = mob_combat.Combatant(level=1000, ability_str=100000, ability_con=0)
CENSUS_COUNT = world_population.CENSUS_COUNT


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _Fixture(unittest.TestCase):
    """Shared setup: a real legacy bridge, a real census, a real ledger."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _legacy()
        cls.objects = diag.diagnostic_objects()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / "diag_multi_object.json"
        self.config.write_text(
            json.dumps({CONFIG_KEY: ["attended_test"]}), encoding="utf-8")
        self.missing_config = Path(self.tmp.name) / "no_such_file.json"

    def census(self, count=CENSUS_COUNT):
        return world_population.build_world_population(
            self.legacy, ANCHOR, count, scene_id=world_population.SCENE_ID,
            count_source=world_population.COUNT_SOURCE_FULL_CENSUS,
        )

    def opened(self):
        """A roster and a ledger the way runtime.py's session opens them."""
        roster = field_mobs.load_roster()
        return roster, mob_combat.open_ledger(roster)

    def hit(self, legacy, roster, ledger, identity, attacker=LETHAL):
        step = mob_combat.attack_from_observed_action(
            legacy, None, ledger, None, {"field_qword_20": identity},
            PERFORMER, attacker, roster=roster,
        )
        return step


class DiagGateTests(_Fixture):
    def test_missing_config_means_no_objects(self):
        activation = wiring.activate(
            "attended_test", world_population.SCENE_ID,
            config_path=self.missing_config,
        )
        self.assertEqual(activation.objects, ())
        self.assertFalse(activation.active)
        self.assertIsNone(activation.event)

    def test_unlisted_account_gets_no_objects_and_says_nothing(self):
        # SILENCE IS THE ASSERTION.  An ordinary login must not gain even one
        # event string from this feature: tests/test_arena.py pins that list
        # exactly, and it went red the first time this returned an "off"
        # event for every player in the world.
        activation = wiring.activate(
            "some_player", world_population.SCENE_ID, config_path=self.config,
        )
        self.assertEqual(activation.objects, ())
        self.assertIsNone(activation.event)

    def test_listed_account_at_home_gets_all_five_in_order(self):
        activation = wiring.activate(
            "attended_test", world_population.SCENE_ID, config_path=self.config,
        )
        self.assertTrue(activation.active)
        self.assertEqual(
            tuple(obj.label for obj in activation.objects), diag.DIAG_LABELS)
        self.assertEqual(activation.event, "diag_multi_object_active_5")

    def test_listed_account_away_from_bg0001_gets_nothing(self):
        # These bodies encode scene 1 in every entry and sit at a bg0001
        # point; delivering them into another map is the same mistake
        # runtime.py's own world_census_skipped_scene_N branch refuses.
        activation = wiring.activate(
            "attended_test", 2, config_path=self.config)
        self.assertEqual(activation.objects, ())
        self.assertEqual(activation.event, "diag_multi_object_skipped_scene_2")

    def test_malformed_config_fails_closed_and_never_raises(self):
        bad = Path(self.tmp.name) / "bad.json"
        bad.write_text(json.dumps({CONFIG_KEY: "attended_test"}), encoding="utf-8")
        activation = wiring.activate(
            "attended_test", world_population.SCENE_ID, config_path=bad)
        self.assertEqual(activation.objects, ())
        self.assertEqual(
            activation.event, "diag_multi_object_config_lookup_failed_ValueError")

    def test_no_account_name_fails_closed(self):
        for name in (None, "", 12345, b"attended_test"):
            activation = wiring.activate(
                name, world_population.SCENE_ID, config_path=self.config)
            self.assertEqual(activation.objects, (), name)
            self.assertIsNone(activation.event, name)


class DiagCensusTests(_Fixture):
    def test_gate_off_returns_the_callers_own_bytes_untouched(self):
        generation = self.census()
        pc, frame, refusal = wiring.census_frames(self.legacy, generation, ())
        self.assertIs(pc, generation.pc)
        self.assertIs(frame, generation.frame)
        self.assertIsNone(refusal)

    def test_five_objects_are_added_to_the_census_not_swapped_into_it(self):
        generation = self.census()
        pc, frame, refusal = wiring.census_frames(
            self.legacy, generation, self.objects)
        self.assertIsNone(refusal)
        self.assertEqual(
            world_population.wire_actor_count(generation), CENSUS_COUNT)
        self.assertEqual(wiring.wire_actor_count(pc), CENSUS_COUNT + 5)
        # The census's own 115 entries are byte-identical and still first:
        # only the header (which now says 120) and the appended tail differ.
        body = world_population.WIRE_HEADER_BYTES
        original_body_len = sum(generation.entry_bytes)
        self.assertEqual(
            pc[body:body + original_body_len],
            generation.pc[body:body + original_body_len],
        )
        self.assertGreater(len(pc), len(generation.pc))
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_the_appended_tail_is_exactly_the_five_alive_entries(self):
        generation = self.census()
        pc, _frame, _refusal = wiring.census_frames(
            self.legacy, generation, self.objects)
        tail = pc[world_population.WIRE_HEADER_BYTES + sum(generation.entry_bytes):]
        expected = b"".join(
            diag.alive_entry(self.legacy, obj) for obj in self.objects)
        self.assertEqual(tail, expected)

    def test_generation_itself_is_never_mutated(self):
        # runtime.py stores generation.actor_count as
        # self.world_census_actor_count and hands it back to
        # build_world_population on every later recompose, which refuses any
        # count above CENSUS_COUNT.  A "helpfully" updated 120 there would
        # turn every later hit into a compose failure.
        generation = self.census()
        before = (generation.actor_count, generation.entry_bytes, generation.pc)
        wiring.census_frames(self.legacy, generation, self.objects)
        self.assertEqual(
            (generation.actor_count, generation.entry_bytes, generation.pc),
            before,
        )
        self.assertEqual(generation.actor_count, CENSUS_COUNT)

    def test_console_lines_are_one_per_object_in_order(self):
        lines = wiring.console_lines(self.objects)
        self.assertEqual(len(lines), 5)
        for line, obj in zip(lines, self.objects):
            self.assertEqual(line, diag.describe_diag_object(obj))
            self.assertTrue(line.startswith("DIAG object=%s " % obj.label))
        self.assertEqual(lines, diag.describe_boot(self.objects))

    def test_console_lines_are_cp874_encodable(self):
        for line in wiring.console_lines(self.objects):
            line.encode("cp874")

    def test_describe_census_counts_what_went_out_not_what_was_asked_for(self):
        generation = self.census()
        pc, _frame, _refusal = wiring.census_frames(
            self.legacy, generation, self.objects)
        line = wiring.describe_census(generation, self.objects, pc)
        self.assertIn("assembled=5", line)
        self.assertIn("census=115", line)
        self.assertIn("wire=120", line)
        self.assertNotIn("MISMATCH", line)
        line.encode("cp874")

    def test_describe_census_says_mismatch_rather_than_a_reassuring_number(self):
        generation = self.census()
        # Bytes that carry only the census: the number this line would print
        # if the splice had silently not happened.
        line = wiring.describe_census(generation, self.objects, generation.pc)
        self.assertIn("MISMATCH:expected_120", line)

    def test_a_broken_splice_fails_closed_to_the_real_census(self):
        class _Broken:
            def __getattr__(self, name):
                raise RuntimeError("legacy bridge is gone")

        generation = self.census()
        pc, frame, refusal = wiring.census_frames(
            _Broken(), generation, self.objects)
        self.assertIs(pc, generation.pc)
        self.assertIs(frame, generation.frame)
        self.assertEqual(
            refusal, "diag_multi_object_census_splice_refused_RuntimeError")


class DiagCombatResolutionTests(_Fixture):
    def test_gate_off_leaves_the_roster_and_ledger_identical(self):
        roster, ledger = self.opened()
        wider_roster, wider_ledger, refusal = wiring.widen_for_combat(
            roster, ledger, ())
        self.assertIs(wider_roster, roster)
        self.assertIs(wider_ledger, ledger)
        self.assertIsNone(refusal)

    def test_gate_off_a_diagnostic_identity_resolves_to_nothing(self):
        roster, ledger = self.opened()
        for obj in self.objects:
            self.assertIsNone(
                self.hit(self.legacy, roster, ledger, obj.mob.actor_identity),
                obj.label,
            )

    def test_gate_on_all_five_identities_resolve_as_combat_targets(self):
        roster, ledger = self.opened()
        roster, ledger, refusal = wiring.widen_for_combat(
            roster, ledger, self.objects)
        self.assertIsNone(refusal)
        self.assertEqual(len(roster), 13 + 5)
        self.assertEqual(len(ledger.balances), 13 + 5)
        for obj in self.objects:
            step = self.hit(
                self.legacy, roster, ledger, obj.mob.actor_identity,
                attacker=mob_combat.pin_attacker(),
            )
            self.assertIsNotNone(step, obj.label)
            self.assertEqual(
                step.outcome.target_identity, obj.mob.actor_identity)
            self.assertEqual(step.outcome.max_hp, diag.DIAG_MOUNTAIN_DEER_MAX_HP)

    def test_the_five_open_at_their_ceiling_like_every_other_monster(self):
        roster, ledger = self.opened()
        _roster, ledger, _refusal = wiring.widen_for_combat(
            roster, ledger, self.objects)
        for obj in self.objects:
            balance = ledger.balance_of(obj.mob.actor_identity)
            self.assertEqual(balance.current_hp, obj.mob.max_hp)
            self.assertEqual(balance.max_hp, obj.mob.max_hp)

    def test_widening_twice_neither_duplicates_a_row_nor_heals_one(self):
        # runtime.py calls load_roster() fresh on every frame and keeps the
        # ledger in session state, so the second frame of a session widens a
        # 13-row roster against an already-18-row ledger.
        roster, ledger = self.opened()
        roster, ledger, _ = wiring.widen_for_combat(roster, ledger, self.objects)
        target = self.objects[0].mob.actor_identity
        step = self.hit(self.legacy, roster, ledger, target,
                        attacker=mob_combat.pin_attacker())
        ledger = mob_combat.commit_step(ledger, step)
        damaged = ledger.balance_of(target).current_hp
        self.assertLess(damaged, diag.DIAG_MOUNTAIN_DEER_MAX_HP)

        roster2, ledger2, refusal = wiring.widen_for_combat(
            field_mobs.load_roster(), ledger, self.objects)
        self.assertIsNone(refusal)
        self.assertEqual(len(roster2), 13 + 5)
        self.assertEqual(len(ledger2.balances), 13 + 5)
        self.assertEqual(ledger2.balance_of(target).current_hp, damaged)
        self.assertIsNotNone(
            self.hit(self.legacy, roster2, ledger2, target,
                     attacker=mob_combat.pin_attacker()))

    def test_widening_never_touches_a_real_roster_identity(self):
        roster, ledger = self.opened()
        wider_roster, wider_ledger, _ = wiring.widen_for_combat(
            roster, ledger, self.objects)
        self.assertEqual(wider_roster[:len(roster)], roster)
        self.assertEqual(wider_ledger.balances[:len(ledger.balances)],
                         ledger.balances)
        self.assertEqual(wider_ledger.generation, ledger.generation)

    def test_a_broken_ledger_fails_closed_to_the_untouched_pair(self):
        class _Broken:
            balances = ()

            def identities(self):
                raise RuntimeError("ledger is gone")

        roster, _ledger = self.opened()
        broken = _Broken()
        wider_roster, wider_ledger, refusal = wiring.widen_for_combat(
            roster, broken, self.objects)
        self.assertIs(wider_roster, roster)
        self.assertIs(wider_ledger, broken)
        self.assertEqual(
            refusal, "diag_multi_object_combat_widen_refused_RuntimeError")

    def test_diag_object_for_identifies_only_the_five(self):
        roster, _ledger = self.opened()
        for mob in roster:
            self.assertIsNone(
                wiring.diag_object_for(self.objects, mob.actor_identity))
        for obj in self.objects:
            self.assertIs(
                wiring.diag_object_for(self.objects, obj.mob.actor_identity),
                obj,
            )
        self.assertIsNone(wiring.diag_object_for((), 0x4329))


class DiagDeathDispatchTests(_Fixture):
    def setUp(self):
        super().setUp()
        roster, ledger = self.opened()
        self.roster, self.ledger, _ = wiring.widen_for_combat(
            roster, ledger, self.objects)
        self.register = mob_death.DeathRegister()
        self.by_label = {obj.label: obj for obj in self.objects}

    def kill_outcome(self, obj):
        step = self.hit(
            self.legacy, self.roster, self.ledger, obj.mob.actor_identity)
        self.assertTrue(step.death_due)
        self.ledger = mob_combat.commit_step(self.ledger, step)
        return step.outcome

    def test_d0_and_d2_get_the_production_hold(self):
        for label in (diag.DIAG_LABEL_CONTROL, diag.DIAG_LABEL_REPEAT_CONTROL):
            obj = self.by_label[label]
            dispatch = wiring.death_dispatch(
                self.legacy, obj, self.kill_outcome(obj), self.register)
            self.assertTrue(dispatch.has_frames, label)
            self.assertEqual(dispatch.step.hold_ms, mob_death.DEATH_TASK_HOLD_MS)
            self.assertEqual(
                dispatch.event, "diag_multi_object_death_%s_hold_ms_700" % label)
            self.register = mob_death.commit_death(self.register, dispatch.step)

    def test_d1a_holds_for_twenty_seconds_and_changes_nothing_else(self):
        d1a = self.by_label[diag.DIAG_LABEL_DYING_TIMER_HOLD]
        outcome = self.kill_outcome(d1a)
        dispatch = wiring.death_dispatch(
            self.legacy, d1a, outcome, self.register)
        self.assertEqual(
            dispatch.step.hold_ms, int(mob_death.DYING_TIMER_SECONDS * 1000))
        self.assertEqual(dispatch.step.hold_ms, 20000)
        self.assertEqual(
            dispatch.event, "diag_multi_object_death_D1a_hold_ms_20000")
        # RE-107's own byte-diff, at the wiring layer: the SAME production
        # call at the production hold produces the SAME two frames for this
        # identity.  Only the gap between sending them differs -- which is
        # exactly what makes D1a a one-field variant of D0 and not a second
        # composer.
        production = mob_death.kill(
            self.legacy, d1a.mob, outcome, self.register,
            widened=diag.DIAG_WIDENED_RULING,
        )
        self.assertEqual(production.dying_pc, dispatch.step.dying_pc)
        self.assertEqual(production.dying_frame, dispatch.step.dying_frame)
        self.assertEqual(production.dead_pc, dispatch.step.dead_pc)
        self.assertEqual(production.dead_frame, dispatch.step.dead_frame)
        self.assertEqual(production.hold_ms, mob_death.DEATH_TASK_HOLD_MS)

    def test_d1b_is_left_unwired_rather_than_answered_with_true(self):
        d1b = self.by_label[diag.DIAG_LABEL_DEAD_ONLY_AFTER_TARGET]
        dispatch = wiring.death_dispatch(
            self.legacy, d1b, self.kill_outcome(d1b), self.register)
        self.assertFalse(dispatch.has_frames)
        self.assertIsNone(dispatch.step)
        self.assertEqual(dispatch.event, wiring.EVENT_DEATH_D1B_UNWIRED)

    def test_no_call_site_in_this_lane_passes_target_vital_seen_true(self):
        # The refusal in dead_only_schedule is the whole of D1b's experiment.
        # A future edit that satisfies it with a literal True would leave
        # every test above green while answering the question the object
        # exists to ask.  Checked against the module's PARSED SYNTAX, not
        # against a substring of its text: this module's own comments have to
        # be able to discuss the keyword by name (they are where the reason it
        # is unwired is written down), and a grep-shaped test would either
        # forbid that or be defeated by it.
        tree = ast.parse(inspect.getsource(wiring))
        offenders = [
            node.lineno for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == "target_vital_seen"
        ]
        self.assertEqual(offenders, [])
        calls = [
            node.func.attr for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        ]
        self.assertNotIn("dead_only_schedule", calls)

    def test_d3_gets_no_death_handling(self):
        d3 = self.by_label[diag.DIAG_LABEL_NO_FACTION_SPLICE]
        dispatch = wiring.death_dispatch(
            self.legacy, d3, self.kill_outcome(d3), self.register)
        self.assertFalse(dispatch.has_frames)
        self.assertEqual(dispatch.event, wiring.EVENT_DEATH_D3_NO_HANDLING)

    def test_a_refused_kill_degrades_to_no_frames_and_never_raises(self):
        d0 = self.by_label[diag.DIAG_LABEL_CONTROL]
        outcome = self.kill_outcome(d0)
        first = wiring.death_dispatch(self.legacy, d0, outcome, self.register)
        self.register = mob_death.commit_death(self.register, first.step)
        # Same identity, already dead: mob_death.kill refuses by name.
        again = wiring.death_dispatch(self.legacy, d0, outcome, self.register)
        self.assertFalse(again.has_frames)
        self.assertEqual(
            again.event,
            "diag_multi_object_death_refused_MobDeathContractError",
        )


class DiagRecomposeTests(_Fixture):
    """The fourth call site: the whole-census recompose on hit and on death."""

    def setUp(self):
        super().setUp()
        roster, ledger = self.opened()
        self.real_roster = roster
        self.roster, self.ledger, _ = wiring.widen_for_combat(
            roster, ledger, self.objects)
        self.register = mob_death.DeathRegister()

    def test_gate_off_is_a_byte_identical_passthrough(self):
        expected = mob_death.hostile_census_frames(
            self.legacy, ANCHOR, CENSUS_COUNT, self.real_roster,
            self.register, ledger=mob_combat.open_ledger(self.real_roster),
        )
        actual = wiring.hostile_census_frames(
            self.legacy, ANCHOR, CENSUS_COUNT, self.real_roster,
            self.register, ledger=mob_combat.open_ledger(self.real_roster),
            objects=(),
        )
        self.assertEqual(actual, expected)

    def kill(self, obj):
        step = self.hit(
            self.legacy, self.roster, self.ledger, obj.mob.actor_identity)
        self.ledger = mob_combat.commit_step(self.ledger, step)
        dispatch = wiring.death_dispatch(
            self.legacy, obj, step.outcome, self.register)
        if dispatch.step is not None:
            self.register = mob_death.commit_death(self.register, dispatch.step)
        return dispatch

    def test_real_roster_recompose_refuses_once_a_diag_object_is_dead(self):
        # THE FINDING, pinned by execution rather than argued: without the
        # fourth call site, the first diagnostic KILL makes every later
        # recompose in that session raise, runtime.py's except falls back to
        # the one-entry frame, and RE-092 says that frame erases the town.
        self.kill(self.objects[0])
        with self.assertRaises(mob_death.MobDeathContractError) as caught:
            mob_death.hostile_census_frames(
                self.legacy, ANCHOR, CENSUS_COUNT, self.real_roster,
                self.register, ledger=self.ledger,
            )
        self.assertEqual(
            caught.exception.reason,
            mob_death.REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
        )

    def test_diag_recompose_carries_the_census_and_all_five_objects(self):
        pc, frame = wiring.hostile_census_frames(
            self.legacy, ANCHOR, CENSUS_COUNT, self.roster, self.register,
            ledger=self.ledger, objects=self.objects,
        )
        self.assertEqual(wiring.wire_actor_count(pc), CENSUS_COUNT + 5)
        self.assertEqual(frame, self.legacy.frame_pc(pc))

    def test_a_killed_diag_object_is_recomposed_as_a_corpse_not_healed(self):
        d0 = self.objects[0]
        self.kill(d0)
        pc, _frame = wiring.hostile_census_frames(
            self.legacy, ANCHOR, CENSUS_COUNT, self.roster, self.register,
            ledger=self.ledger, objects=self.objects,
        )
        self.assertEqual(wiring.wire_actor_count(pc), CENSUS_COUNT + 5)
        corpse = mob_death.death_actor_entry(
            self.legacy, d0.mob, death_timer=mob_death.DEAD_TIMER_SECONDS)
        alive = diag.alive_entry(self.legacy, d0)
        self.assertIn(corpse, pc)
        self.assertNotIn(alive, pc)

    def test_d3_keeps_its_unspliced_body_through_a_recompose(self):
        # D3's whole experiment is the ABSENCE of the faction splice.  The
        # production override composes every live body WITH it, so taking D3's
        # entry from there would quietly turn D3 into a fifth D0.
        pc, _frame = wiring.hostile_census_frames(
            self.legacy, ANCHOR, CENSUS_COUNT, self.roster, self.register,
            ledger=self.ledger, objects=self.objects,
        )
        d3 = self.objects[4]
        self.assertIn(diag.alive_entry(self.legacy, d3), pc)
        self.assertNotIn(
            field_mobs.hostile_actor_entry(self.legacy, d3.mob), pc)

    def test_an_unanswered_d1b_is_dropped_loudly_not_silently_or_fatally(self):
        d1b = self.objects[2]
        dispatch = self.kill(d1b)
        self.assertIsNone(dispatch.step)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            pc, _frame = wiring.hostile_census_frames(
                self.legacy, ANCHOR, CENSUS_COUNT, self.roster, self.register,
                ledger=self.ledger, objects=self.objects,
            )
        printed = buffer.getvalue()
        self.assertIn("DIAG_CENSUS_SKIPPED object=D1b", printed)
        self.assertIn(wiring.SKIP_REASON_ZERO_HP_NOT_DEAD, printed)
        printed.encode("cp874")
        # Four objects, the whole census, and no exception: the other four
        # diagnostic objects and every real actor survive D1b's own experiment.
        self.assertEqual(wiring.wire_actor_count(pc), CENSUS_COUNT + 4)

    def test_calling_with_the_real_roster_while_active_refuses_by_name(self):
        with self.assertRaises(wiring.DiagWiringError):
            wiring.hostile_census_frames(
                self.legacy, ANCHOR, CENSUS_COUNT, self.real_roster,
                self.register, ledger=self.ledger, objects=self.objects,
            )


class DiagWiringHygieneTests(unittest.TestCase):
    def test_every_module_this_lane_added_is_cp874_encodable(self):
        for path in (
            ROOT / "src/pirateforce_foundation/diag_multi_object_wiring.py",
            ROOT / "src/pirateforce_foundation/diag_multi_object_config.py",
        ):
            path.read_text(encoding="utf-8").encode("cp874")

    def test_both_new_modules_carry_the_projects_convention_markers(self):
        # Same two flags every other shippable module in this tree sets, and
        # the ones lane_hooks._discover() reads before it will keep a hook:
        # this wiring is default-path code behind an operator config, not a
        # scenario probe, and it says so where the tree already looks.
        for module in (wiring, wiring.diag_multi_object_config):
            self.assertIs(module.production_allowed, True, module.__name__)
            self.assertIs(module.test_only, False, module.__name__)

    def test_the_runtime_patch_text_names_every_call_site_it_claims(self):
        patch = wiring.RUNTIME_WIRING_PATCH
        for needed in (
            "diag_multi_object_wiring.activate",
            "diag_multi_object_wiring.census_frames",
            "diag_multi_object_wiring.widen_for_combat",
            "diag_multi_object_wiring.death_dispatch",
            "diag_multi_object_wiring.hostile_census_frames",
            "self.diag_multi_objects",
        ):
            self.assertIn(needed, patch)
        patch.encode("cp874")


if __name__ == "__main__":
    unittest.main()
