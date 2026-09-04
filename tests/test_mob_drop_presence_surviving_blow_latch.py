"""LANE-B round yqbwri: the latch `COO-DECISION 20260905_0247` item 1 ruled
on for the surviving-blow reannounce ``tests/test_mob_drop_presence_
surviving_blow.py`` (round hlwgri) already pins the wire shape of.

That round measured 3-4 extra ground publications per kill if this composer
were called on every non-fatal blow -- an amplification the 2026-08-30T17:42
COO ruling bars until an attended round has measured EXACTLY ONE extra
resend.  This round's letter answers: (b) is a LATCH, at most one extra
publication per NEW ground generation, not one per blow.  This file proves
that shape:

  * across N non-fatal blows against ONE unchanged generation, the composer
    sends exactly ONE reannounce, not N;
  * a NEW generation (another kill's rows landing) unlatches exactly one
    more;
  * a refused or raising compose does NOT spend the one allowed resend --
    the latch stays due until a compose actually succeeds;
  * ``DropLedgerCell.surviving_blow_reannounce_due`` /
    ``note_surviving_blow_reannounced`` themselves, direct.

STILL NOT WIRED.  This file does not touch `runtime.py` and does not change
`GROUND_SURVIVING_BLOW_CALL_SITE_STATUS` -- see
``tests/test_mob_drop_presence_surviving_blow.py``'s own AST tripwire for
that, which stays green because nothing here calls the composer from
`runtime.py`.
"""

from pathlib import Path
import builtins
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, mob_drop_presence, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_drop_presence import (
    GROUND_SURVIVING_BLOW_TOKEN,
    reannounce_ground_after_a_surviving_blow,
    sustain_a_kill,
    loot_actions,
)

KILLER = 0x750059
SCENE = field_mobs.BG0002_SCENE


class _Clock:
    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class _Step:
    def __init__(self, death_due):
        self.death_due = death_due


class _Console:
    def __init__(self):
        self.lines = []

    def __call__(self, *args, **kwargs):
        self.lines.append(" ".join(str(a) for a in args))

    def with_token(self, token):
        return [line for line in self.lines if line.startswith(token)]


class LatchTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster(scene=SCENE)
        cls.dropping = []
        for mob in cls.roster:
            for seed in range(60):
                roll = mob_loot.roll_drops(mob, random.Random(seed))
                if roll.placeable_count:
                    cls.dropping.append((mob, seed))
                    break
        if len(cls.dropping) < 1:
            raise unittest.SkipTest("this scene's tables drop almost nothing")

    def setUp(self):
        self.clock = _Clock()
        self.cell = mob_loot.DropLedgerCell(clock=self.clock, scene=SCENE)
        self.token = 0
        self.console = _Console()
        self._real_print = builtins.print
        builtins.print = self.console
        self.addCleanup(self._restore_console)

    def _restore_console(self):
        builtins.print = self._real_print

    def kill(self, index=0, cell=None):
        cell = self.cell if cell is None else cell
        mob, seed = self.dropping[index % len(self.dropping)]
        self.token += 1
        drops = cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)),
            kill_token=self.token)
        self.assertTrue(drops, "this test needs a kill with rows")
        return drops


class TheLatchCapsOneResendPerGenerationTests(LatchTestBase):
    def test_133_non_fatal_blows_against_one_generation_send_exactly_once(
            self):
        self.kill()
        composed = 0
        for _ in range(133):
            actions = reannounce_ground_after_a_surviving_blow(
                self.cell, self.legacy, _Step(False))
            if actions:
                composed += 1
        self.assertEqual(composed, 1)
        self.assertEqual(
            len(self.console.with_token(GROUND_SURVIVING_BLOW_TOKEN)), 1,
            self.console.lines,
        )

    def test_the_first_call_composes_the_same_bytes_as_the_kill_path(self):
        self.kill()
        expected = loot_actions(sustain_a_kill(self.cell, self.legacy, ()))
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertEqual(list(actions), list(expected))

    def test_suppressed_calls_print_nothing_at_all(self):
        # The whole point of the latch is to remove console spam along with
        # wire spam: 132 suppressed blows must not each cost a line, even a
        # quiet "already announced" one.
        self.kill()
        reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.console.lines.clear()
        for _ in range(50):
            actions = reannounce_ground_after_a_surviving_blow(
                self.cell, self.legacy, _Step(False))
            self.assertEqual(actions, ())
        self.assertEqual(self.console.lines, [])

    def test_a_new_kill_unlatches_exactly_one_more_resend(self):
        self.kill(0)
        first = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertTrue(first)
        again = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertEqual(again, ())
        self.kill(1)
        second = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertTrue(second)
        third = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertEqual(third, ())

    def test_a_fatal_blow_never_consumes_the_survivor_latch(self):
        # The death branch is refused BY NAME before the latch is even
        # consulted (test_mob_drop_presence_surviving_blow.py already pins
        # the refusal); this pins that the survivor latch for THIS
        # generation is still due afterward.
        self.kill()
        reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(True))
        self.assertTrue(
            self.cell.surviving_blow_reannounce_due(),
            "a fatal-blow call must not spend the survivor latch",
        )
        survivor = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertTrue(survivor)

    def test_a_refused_compose_does_not_spend_the_latch(self):
        # A cell with no scene refuses by name (pinned in the sibling file);
        # this proves that refusal leaves the latch due for a later call
        # against a cell that DOES have a scene, on the same generation
        # value -- a refusal must never be mistaken for "told".
        bare_cell = mob_loot.DropLedgerCell(clock=self.clock)
        refused = reannounce_ground_after_a_surviving_blow(
            bare_cell, self.legacy, _Step(False))
        self.assertEqual(refused, ())
        self.assertTrue(
            bare_cell.surviving_blow_reannounce_due(),
            "a refused compose must not consume the one allowed resend",
        )

    def test_a_raising_compose_does_not_spend_the_latch_either(self):
        self.kill()
        real = mob_drop_presence.loot_actions

        def explode(step):
            raise RuntimeError("compose blew up after the latch said due")

        mob_drop_presence.loot_actions = explode
        try:
            actions = reannounce_ground_after_a_surviving_blow(
                self.cell, self.legacy, _Step(False))
        finally:
            mob_drop_presence.loot_actions = real
        self.assertEqual(actions, ())
        self.assertTrue(self.cell.surviving_blow_reannounce_due())
        recovered = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertTrue(recovered)


class DropLedgerCellLatchMethodTests(unittest.TestCase):
    """The cell's own two methods, direct -- no composer, no legacy."""

    def setUp(self):
        self.clock = _Clock()

    def test_a_fresh_cell_is_due_at_its_own_current_generation(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.assertTrue(cell.surviving_blow_reannounce_due())

    def test_note_then_due_flips_to_false_for_the_same_generation(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.assertTrue(cell.surviving_blow_reannounce_due())
        cell.note_surviving_blow_reannounced()
        self.assertFalse(cell.surviving_blow_reannounce_due())

    def test_noting_twice_for_the_same_generation_is_a_harmless_no_op(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        cell.note_surviving_blow_reannounced()
        cell.note_surviving_blow_reannounced()
        self.assertFalse(cell.surviving_blow_reannounce_due())

    def test_an_explicit_generation_argument_is_honoured(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        cell.note_surviving_blow_reannounced(5)
        self.assertFalse(cell.surviving_blow_reannounce_due(5))
        self.assertTrue(cell.surviving_blow_reannounce_due(6))
        # The cell's OWN current generation (0, nothing committed yet) is
        # unaffected by noting an unrelated explicit value.
        self.assertTrue(cell.surviving_blow_reannounce_due())

    def test_generation_zero_is_distinguishable_from_never_noted(self):
        # DropLedger.generation starts at 0; a cell that has never been
        # told must not be confused with one already told about generation
        # 0, or the very first call on a fresh cell would be silently
        # suppressed.
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.assertTrue(cell.surviving_blow_reannounce_due(0))


if __name__ == "__main__":
    unittest.main()
