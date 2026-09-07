"""LANE-B: the join between the mined AI_COMBAT row and the rule parser.

PANYA-DECISION 20260906_2032 work item 4 -- connect the rule language to the
existing controller without writing a second one.  These pins are about the
join only; the language itself is pinned in tests/test_mob_ai_rules.py and
threat/targeting stays mob_aggro's, untouched here.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import mob_ai_control  # noqa: E402
from pirateforce_foundation import mob_ai_rules  # noqa: E402

SCENES = ("Bg0002", "Bg0003", "Bg0007", "Bg0008", "Bg0009", "Bg0010",
          "Bg0011", "Bg0015", "bg0001", "bg0004", "bg0005", "bg0006")


class EveryShippedMonsterGetsItsOwnRules(unittest.TestCase):

    def test_every_roster_mob_with_a_combat_row_parses(self):
        """The number that matters to a player: how many monsters have rules.

        Measured over every scene ``field_mobs`` can load, not over the AI
        table -- a row that parses but that no monster points at would move
        this number nowhere.
        """
        with_rules = 0
        without = 0
        for scene in SCENES:
            for mob in field_mobs.load_roster(scene):
                program = mob_ai_control.combat_program_of(mob)
                if mob.ai_combat:
                    self.assertIsNotNone(program, f"{scene} {mob.template_id}")
                    self.assertTrue(program.lines)
                    self.assertEqual(program.row_id, mob.ai_combat)
                    with_rules += 1
                else:
                    self.assertIsNone(program, f"{scene} {mob.template_id}")
                    without += 1
        self.assertEqual(with_rules, 99,
                         "99 shipped roster placements carry an AI_COMBAT row; "
                         "if this moved, say which scene changed")
        self.assertGreater(without, 0,
                           "n_AI_COMBAT == 0 is a value, not a missing row")

    def test_a_monster_the_table_gives_no_combat_ai_answers_none(self):
        roster = field_mobs.load_roster("bg0001")
        quiet = [m for m in roster if not m.ai_combat]
        self.assertTrue(quiet)
        self.assertIsNone(mob_ai_control.combat_program_of(quiet[0]))


class TheJoinTakesAnIdentity(unittest.TestCase):

    def _register(self, scene="Bg0015"):
        roster = field_mobs.load_roster(scene)
        return mob_ai_control.open_register(roster, epoch=0), roster

    def test_the_line_comes_from_the_monster_the_identity_names(self):
        register, _roster = self._register()
        identities = register.identities()
        self.assertTrue(identities)
        rng = random.Random(5)
        answered = 0
        for identity in identities:
            mob = register.mob_of(identity)
            state = mob_ai_rules.EvalState(distance_enemy=800, hp_self=1.0)
            line = mob_ai_control.combat_line_for(register, identity, state, rng)
            if not mob.ai_combat:
                self.assertIsNone(line)
                continue
            self.assertIsNotNone(line)
            program = mob_ai_control.combat_program_of(mob)
            self.assertIn(line, program.lines,
                          "the line must come from THIS monster's program")
            answered += 1
        self.assertGreater(answered, 0)

    def test_an_untyped_register_is_refused_by_name(self):
        with self.assertRaises(mob_ai_control.MobAiControlError):
            mob_ai_control.combat_line_for(
                object(), 1, mob_ai_rules.EvalState())

    def test_the_join_adds_no_second_threat_table(self):
        """COO-DECISION 2026-08-26 section 1.3, made mechanical.

        The join may not read or write threat, phase or target: those belong
        to mob_aggro and routing them twice is the duplication the ruling
        forbids.  Asserted against the source of the two new functions only.
        """
        import inspect
        source = (inspect.getsource(mob_ai_control.combat_line_for)
                  + inspect.getsource(mob_ai_control.combat_program_of))
        for forbidden in ("threat", "apply_damage_threat", "target_identity",
                          "phase", "with_state", "mob_aggro.tick"):
            self.assertNotIn(forbidden, source.split('"""')[2],
                             f"the join must not touch {forbidden}")


if __name__ == "__main__":
    unittest.main()
