"""LANE-B: pins for the AI_COMBAT rule language and the AI_WANDER script.

PANYA-DECISION 20260906_2032 work item 1.  The letter's own acceptance test
is "zero unparsed tokens over every shipped row"; the rest of this file pins
the readings the module declares, so a later round that changes one of them
has to change a test that says why.
"""

from __future__ import annotations

import inspect
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mob_ai_tables  # noqa: E402
from pirateforce_foundation import mob_ai_rules  # noqa: E402


class ParseEveryShippedRow(unittest.TestCase):
    """The letter's acceptance test, and the trap underneath it."""

    def test_every_shipped_combat_row_parses_with_no_unknown_token(self):
        programs = mob_ai_rules.parse_all(field_mob_ai_tables.AI_COMBAT_ROWS)
        self.assertEqual(len(programs), len(field_mob_ai_tables.AI_COMBAT_ROWS))
        # Not "it did not raise": count what was actually built, so a parse
        # that silently produced empty programs cannot pass.
        total_lines = sum(len(p.lines) for p in programs.values())
        self.assertGreater(total_lines, len(programs),
                           "every shipped row has more than one rule line")
        for program in programs.values():
            for line in program.lines:
                self.assertTrue(line.conditions,
                                "a rule line with no condition token")

    def test_the_separator_is_two_characters_not_a_newline(self):
        """The lie the module docstring exists to prevent, measured.

        The shipped columns hold BACKSLASH + 'n', never chr(10).  A parser
        that split on a real newline would read each row as ONE line -- and
        that one line ENDS in GO(0), so a lenient parser would find a default
        and answer it forever while looking parsed.  Measured here both ways:
        the data has the shape that makes the failure possible, and this
        parser fails closed on it (raises) instead of quietly defaulting.
        """
        self.assertEqual(mob_ai_rules.RULE_SEPARATOR, "\\n")
        rows = field_mob_ai_tables.AI_COMBAT_ROWS
        for row_id, (conditions, actions) in rows.items():
            self.assertNotIn("\n", conditions, f"row {row_id}")
            self.assertNotIn("\n", actions, f"row {row_id}")
            self.assertIn("\\n", conditions, f"row {row_id}")
            self.assertTrue(conditions.endswith("GO(0)"), f"row {row_id}")
        row_id, (conditions, actions) = sorted(rows.items())[0]
        wrong = conditions.split("\n")
        self.assertEqual(len(wrong), 1,
                         "the whole row is one line under the wrong reading")
        with self.assertRaises(mob_ai_rules.UnknownRuleToken):
            mob_ai_rules.parse_program(
                row_id, conditions.replace("\\n", "\n"),
                actions.replace("\\n", "\n"))
        real = mob_ai_rules.parse_program(row_id, conditions, actions)
        self.assertGreater(len(real.lines), 1)

    def test_this_modules_parallel_measurement_agrees_with_the_table(self):
        """Two independent readings of the same property, compared.

        ``AI_COMBAT_PARALLEL`` is the miner's answer; ``CombatProgram.
        parallel`` is this parser's.  They are computed from different code,
        so this is a check, not a restatement.
        """
        programs = mob_ai_rules.parse_all(field_mob_ai_tables.AI_COMBAT_ROWS)
        for row_id, program in programs.items():
            self.assertEqual(
                program.parallel,
                field_mob_ai_tables.AI_COMBAT_PARALLEL[row_id],
                f"row {row_id}")

    def test_the_slice_this_repository_ships_is_all_parallel_and_defaulted(self):
        """MEASURED, not desired.

        The decision letter describes six non-parallel rows and eight without
        a GO(0) default in the FULL 276-row table.  None of them is in the
        34-row bg0001 slice committed here.  If a later mining run brings one
        in, this test goes red and the round that brought it must say which
        shape arrived -- the parser already declares behaviour for both.
        """
        programs = mob_ai_rules.parse_all(field_mob_ai_tables.AI_COMBAT_ROWS)
        self.assertEqual(
            [r for r, p in programs.items() if not p.parallel], [])
        self.assertEqual(
            [r for r, p in programs.items() if not p.ends_with_default], [])

    def test_an_unknown_token_raises_instead_of_being_skipped(self):
        for bad in ("MANA_I<(0.5)", "HP_I<(0.5,0.6)", "HP_I<(low)",
                    "not a token", ""):
            with self.assertRaises(mob_ai_rules.UnknownRuleToken):
                mob_ai_rules.parse_condition_token(bad)
        with self.assertRaises(mob_ai_rules.UnknownRuleToken):
            mob_ai_rules.parse_action_token("FLEE(1)")
        with self.assertRaises(mob_ai_rules.UnknownRuleToken):
            mob_ai_rules.parse_program(1, "GO(0)", "CHASE(1);CHASE(2)")


class ChooseOneLine(unittest.TestCase):

    def _program(self):
        return mob_ai_rules.parse_program(
            999,
            "DISTANCE_ENEMY>(700)\\nHP_I<(0.5)\\nGO(0)",
            "CHASE(2)\\nCHASE(5)\\nCHASE(1)")

    def test_the_first_matching_line_wins_not_the_most_specific(self):
        program = self._program()
        far_and_hurt = mob_ai_rules.EvalState(distance_enemy=900, hp_self=0.1)
        self.assertEqual(
            mob_ai_rules.choose(program, far_and_hurt).action.skill_slot, 2)

    def test_the_default_is_reached_only_when_nothing_above_matches(self):
        program = self._program()
        near_and_healthy = mob_ai_rules.EvalState(
            distance_enemy=100, hp_self=1.0)
        chosen = mob_ai_rules.choose(program, near_and_healthy)
        self.assertTrue(chosen.is_default)
        self.assertEqual(chosen.action.skill_slot, 1)
        hurt = mob_ai_rules.EvalState(distance_enemy=100, hp_self=0.4)
        self.assertEqual(mob_ai_rules.choose(program, hurt).action.skill_slot, 5)

    def test_a_row_with_no_default_can_answer_nothing_to_do(self):
        program = mob_ai_rules.parse_program(
            998, "DISTANCE_ENEMY>(700)", "CHASE(2)")
        self.assertFalse(program.ends_with_default)
        self.assertIsNone(mob_ai_rules.choose(
            program, mob_ai_rules.EvalState(distance_enemy=10)))

    def test_a_condition_line_with_no_action_does_not_fall_through(self):
        """The non-parallel shape: doing nothing beats borrowing an action."""
        program = mob_ai_rules.parse_program(
            997, "DISTANCE_ENEMY>(700)\\nGO(0)", "CHASE(2)")
        self.assertFalse(program.parallel)
        chosen = mob_ai_rules.choose(
            program, mob_ai_rules.EvalState(distance_enemy=10))
        self.assertTrue(chosen.is_default)
        self.assertIsNone(chosen.action,
                          "line 1 has no action of its own and must not take "
                          "line 0's CHASE(2)")

    def test_every_condition_on_a_line_must_hold(self):
        program = mob_ai_rules.parse_program(
            996, "DISTANCE_ENEMY<(500);HP_I<(0.5)\\nGO(0)",
            "CHASE(3)\\nCHASE(1)")
        both = mob_ai_rules.EvalState(distance_enemy=100, hp_self=0.2)
        self.assertEqual(mob_ai_rules.choose(program, both).action.skill_slot, 3)
        one = mob_ai_rules.EvalState(distance_enemy=100, hp_self=0.9)
        self.assertEqual(mob_ai_rules.choose(program, one).action.skill_slot, 1)

    def test_rate_without_a_generator_raises_rather_than_drawing_globally(self):
        program = mob_ai_rules.parse_program(995, "RATE(50)", "CHASE(1)")
        with self.assertRaises(mob_ai_rules.UnknownRuleToken):
            mob_ai_rules.choose(program, mob_ai_rules.EvalState())

    def test_rate_is_a_percent_chance_per_evaluation(self):
        always = mob_ai_rules.parse_program(994, "RATE(100)", "CHASE(1)")
        never = mob_ai_rules.parse_program(993, "RATE(0)", "CHASE(1)")
        rng = random.Random(7)
        for _ in range(50):
            self.assertIsNotNone(
                mob_ai_rules.choose(always, mob_ai_rules.EvalState(), rng))
            self.assertIsNone(
                mob_ai_rules.choose(never, mob_ai_rules.EvalState(), rng))
        half = mob_ai_rules.parse_program(992, "RATE(50)", "CHASE(1)")
        rng = random.Random(11)
        state = mob_ai_rules.EvalState()
        hits = sum(
            1 for _ in range(1000)
            if mob_ai_rules.choose(half, state, rng) is not None)
        self.assertTrue(400 < hits < 600, f"RATE(50) fired {hits}/1000")

    def test_doonce_fires_once_per_monster_life(self):
        program = mob_ai_rules.parse_program(
            991, "DOONCE(0);HP_I<(0.9)\\nGO(0)", "CHASE(4)\\nCHASE(1)")
        state = mob_ai_rules.EvalState(hp_self=0.5)
        self.assertEqual(mob_ai_rules.choose(program, state).action.skill_slot, 4)
        self.assertEqual(mob_ai_rules.choose(program, state).action.skill_slot, 1)
        fresh = mob_ai_rules.EvalState(hp_self=0.5)
        self.assertEqual(mob_ai_rules.choose(program, fresh).action.skill_slot, 4)

    def test_a_doonce_line_that_never_matched_is_not_spent(self):
        program = mob_ai_rules.parse_program(
            990, "DOONCE(0);HP_I<(0.2)\\nGO(0)", "CHASE(4)\\nCHASE(1)")
        state = mob_ai_rules.EvalState(hp_self=0.9)
        self.assertEqual(mob_ai_rules.choose(program, state).action.skill_slot, 1)
        state.hp_self = 0.1
        self.assertEqual(mob_ai_rules.choose(program, state).action.skill_slot, 4)

    def test_the_other_condition_words_read_the_state_they_name(self):
        cases = (
            ("KD_ENEMY(1)", {"enemy_knocked_down": True},
             {"enemy_knocked_down": False}),
            ("HP_ENEMY<(0.5)", {"hp_enemy": 0.2}, {"hp_enemy": 0.8}),
            ("HP_ALLY<(0.7)", {"hp_ally": 0.2}, {"hp_ally": 0.9}),
            ("HP_I>(0.5)", {"hp_self": 0.9}, {"hp_self": 0.1}),
            ("BUFF_I(4985,0,0)", {"buffs_self": frozenset({4985})},
             {"buffs_self": frozenset({1})}),
            ("BUFF_ENEMY(4985,0,0)", {"buffs_enemy": frozenset({4985})},
             {"buffs_enemy": frozenset()}),
        )
        for token, holds, fails in cases:
            program = mob_ai_rules.parse_program(
                989, token + "\\nGO(0)", "CHASE(6)\\nCHASE(1)")
            self.assertEqual(
                mob_ai_rules.choose(
                    program, mob_ai_rules.EvalState(**holds)).action.skill_slot,
                6, token)
            self.assertEqual(
                mob_ai_rules.choose(
                    program, mob_ai_rules.EvalState(**fails)).action.skill_slot,
                1, token)


class WanderScriptReading(unittest.TestCase):

    def test_every_shipped_wander_row_reads(self):
        rows = field_mob_ai_tables.AI_WANDER_ROWS
        self.assertTrue(rows)
        for row_id, columns in rows.items():
            script = mob_ai_rules.parse_wander(columns[0])
            self.assertEqual(len(script.steps), 2, f"row {row_id}")
            self.assertEqual(
                {s.mode for s in script.steps}, {"IDLE", "RUN"},
                f"row {row_id}")

    def test_a_malformed_step_raises(self):
        for bad in ("IDLE;9", "SWIM;1;2", "IDLE;a;b", "IDLE;15;9", ""):
            with self.assertRaises(mob_ai_rules.UnknownRuleToken):
                mob_ai_rules.parse_wander(bad)

    def test_the_plan_repeats_the_steps_in_order_and_stays_in_bounds(self):
        script = mob_ai_rules.parse_wander("IDLE;9;15\\nRUN;0;1")
        rng = random.Random(3)
        plan = mob_ai_rules.wander_plan(script, rng, cycles=3)
        self.assertEqual([mode for mode, _ in plan],
                         ["IDLE", "RUN"] * 3)
        for mode, seconds in plan:
            low, high = (9.0, 15.0) if mode == "IDLE" else (0.0, 1.0)
            self.assertGreaterEqual(seconds, low * mob_ai_rules.WANDER_UNIT_SECONDS)
            self.assertLessEqual(seconds, high * mob_ai_rules.WANDER_UNIT_SECONDS)

    def test_the_unit_reading_lives_in_one_constant(self):
        """The nonclaim the letter asked for, made mechanical.

        The units of a and b are not known.  What IS pinned is that exactly
        one constant multiplies them, so changing the reading is a one-line
        change rather than a hunt.
        """
        source = inspect.getsource(mob_ai_rules)
        self.assertEqual(source.count("WANDER_UNIT_SECONDS"), 3,
                         "one definition, one docstring mention, one use")


class ModuleHygiene(unittest.TestCase):

    def test_the_module_is_ascii(self):
        source = inspect.getsource(mob_ai_rules)
        source.encode("ascii")
        self.assertNotIn("\r", source)
        self.assertNotIn("\t", source)


if __name__ == "__main__":
    unittest.main()
