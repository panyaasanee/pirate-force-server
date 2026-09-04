"""LANE-B round hlwgri: the floor after a blow that did NOT kill.

`COO-DECISION 20260903_1942` point 4 ratified option (b) of RE-208's "it
comes back" half word for word: ``refresh_frames`` after a blow that does
not kill, same 47-byte shape, no new mask, one action to roll back.  This
round MEASURED that no such call exists on `origin/main`: the non-fatal
branch of `mob_combat.strike` returns `(announce_frame, bar_frame)` and
runtime.py's hit dispatch reaches `return actions` with every ground
re-emit sitting inside `if step.death_due:`.

This file pins the WIRE-LEVEL half of the composer that closes that gap:
`reannounce_ground_after_a_surviving_blow` sends exactly what the per-kill
path would send for the same ledger, refuses BY NAME on a blow that killed
(so one blow can never put the generation on the wire twice), fails closed
on a step it cannot read, and never raises out of the listener thread.

NOTHING HERE CLAIMS THE LABEL STOPS BLINKING ON A REAL SCREEN.  `GT-223`
step (8) is that measurement, and until it passes the fix stays labelled
`[LANE-B ASSUMPTION - AWAITING COO CONFIRMATION]` exactly as the COO's own
ratification requires.
"""

from pathlib import Path
import builtins
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pirateforce_foundation import field_mobs, mob_drop_presence, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_drop_presence import (
    GROUND_REANNOUNCE_TOKEN,
    GROUND_SURVIVING_BLOW_REFUSED_TOKEN,
    GROUND_SURVIVING_BLOW_TOKEN,
    REFUSE_DEATH_DUE_UNREADABLE,
    REFUSE_NO_SCENE,
    REFUSE_THE_BLOW_KILLED,
    loot_actions,
    reannounce_ground,
    reannounce_ground_after_a_surviving_blow,
    sustain_a_kill,
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
    """The one field this call site reads off `mob_combat.CombatStep`."""

    def __init__(self, death_due):
        self.death_due = death_due


class _StepThatRaises:
    @property
    def death_due(self):
        raise RuntimeError("a property that raises is a step we cannot read")


class _Console:
    """Collects the lines this module prints, and can refuse to take one."""

    def __init__(self, raising=False):
        self.lines = []
        self.raising = raising

    def __call__(self, *args, **kwargs):
        if self.raising:
            raise UnicodeEncodeError("cp874", "x", 0, 1, "cannot encode")
        self.lines.append(" ".join(str(a) for a in args))

    def with_token(self, token):
        return [line for line in self.lines if line.startswith(token)]


class SurvivingBlowTestBase(unittest.TestCase):
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


class ASurvivingBlowResendsTheFloorTests(SurvivingBlowTestBase):
    def test_it_sends_exactly_what_the_kill_path_would_send(self):
        self.kill()
        expected = loot_actions(sustain_a_kill(self.cell, self.legacy, ()))
        self.console.lines.clear()
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertIsInstance(actions, tuple)
        self.assertTrue(actions, "a floor with rows must put frames on the wire")
        self.assertEqual(
            [a[1:] for a in actions], [a[1:] for a in expected],
            "the surviving-blow call must compose the same bytes as the "
            "per-kill call site, not a second encoder path")

    def test_the_console_line_names_this_call_site_and_counts_the_floor(self):
        self.kill()
        reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        said = self.console.with_token(GROUND_SURVIVING_BLOW_TOKEN)
        self.assertEqual(len(said), 1, self.console.lines)
        self.assertIn("items=", said[0])
        self.assertNotIn("items=0", said[0])

    def test_it_does_not_print_gt242s_negative_control_token(self):
        # GT-242's RECHECK greps GROUND_REANNOUNCE_AFTER_SECOND_PWD as its
        # "this build has no call site" control.  A second call site printing
        # that exact string would make the control lie.
        self.kill()
        reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        for line in self.console.lines:
            self.assertFalse(
                line.startswith(GROUND_REANNOUNCE_TOKEN),
                "this call site must not print the 0x4B98 call site's token")
        self.assertNotEqual(
            GROUND_SURVIVING_BLOW_TOKEN, GROUND_REANNOUNCE_TOKEN)

    def test_neither_token_is_a_prefix_of_the_other(self):
        # A refusal line that a grep for the success token also counts is how
        # "the floor was resent N times" becomes a number nobody can trust.
        self.assertFalse(GROUND_SURVIVING_BLOW_REFUSED_TOKEN.startswith(
            GROUND_SURVIVING_BLOW_TOKEN))
        self.assertFalse(GROUND_SURVIVING_BLOW_TOKEN.startswith(
            GROUND_SURVIVING_BLOW_REFUSED_TOKEN))

    def test_a_bare_floor_is_checked_and_said_not_silent(self):
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertEqual(actions, ())
        said = self.console.with_token(GROUND_SURVIVING_BLOW_TOKEN)
        self.assertEqual(len(said), 1, self.console.lines)
        self.assertIn("items=0", said[0])
        self.assertEqual(
            self.console.with_token(GROUND_SURVIVING_BLOW_REFUSED_TOKEN), [],
            "a bare floor is not a refusal")


class TheKillPathKeepsItsOwnFrameTests(SurvivingBlowTestBase):
    def test_a_fatal_blow_is_refused_by_name(self):
        self.kill()
        self.console.lines.clear()
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(True))
        self.assertEqual(actions, (), "the death branch owns that generation")
        said = self.console.with_token(GROUND_SURVIVING_BLOW_REFUSED_TOKEN)
        self.assertEqual(len(said), 1, self.console.lines)
        self.assertIn(REFUSE_THE_BLOW_KILLED, said[0])
        self.assertEqual(
            self.console.with_token(GROUND_SURVIVING_BLOW_TOKEN), [])

    def test_one_blow_never_puts_the_generation_on_the_wire_twice(self):
        # The wire cost of getting the guard wrong, stated as a test: for one
        # fatal blow the kill path composes the generation, and this call must
        # add nothing to it.
        self.kill()
        kill_path = loot_actions(sustain_a_kill(self.cell, self.legacy, ()))
        extra = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(True))
        self.assertTrue(kill_path)
        self.assertEqual(extra, ())


class FailClosedOnAStepItCannotReadTests(SurvivingBlowTestBase):
    def _refused(self, step):
        self.kill()
        self.console.lines.clear()
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, step)
        self.assertEqual(actions, ())
        said = self.console.with_token(GROUND_SURVIVING_BLOW_REFUSED_TOKEN)
        self.assertEqual(len(said), 1, self.console.lines)
        self.assertIn(REFUSE_DEATH_DUE_UNREADABLE, said[0])

    def test_no_step_at_all(self):
        self._refused(None)

    def test_a_step_without_the_field(self):
        self._refused(object())

    def test_a_step_whose_field_raises(self):
        self._refused(_StepThatRaises())

    def test_death_due_none_is_not_read_as_false(self):
        self._refused(_Step(None))

    def test_a_truthy_int_is_not_read_as_true_either(self):
        # 1 is not False, so it refuses -- and it refuses as UNREADABLE, not
        # as "the blow killed": the two are different findings on a console.
        self._refused(_Step(1))

    def test_a_falsy_int_is_not_read_as_false(self):
        self._refused(_Step(0))


class NeverRaisesTests(SurvivingBlowTestBase):
    def test_a_cell_that_is_not_a_cell(self):
        for cell in (None, object(), 7, "bg0002"):
            with self.subTest(cell=cell):
                self.assertEqual(
                    reannounce_ground_after_a_surviving_blow(
                        cell, self.legacy, _Step(False)),
                    ())

    def test_a_legacy_that_cannot_frame(self):
        self.kill()
        for legacy in (None, object()):
            with self.subTest(legacy=legacy):
                self.assertEqual(
                    reannounce_ground_after_a_surviving_blow(
                        self.cell, legacy, _Step(False)),
                    ())

    def test_a_cell_with_no_scene_refuses_by_name(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        actions = reannounce_ground_after_a_surviving_blow(
            cell, self.legacy, _Step(False))
        self.assertEqual(actions, ())
        said = self.console.with_token(GROUND_SURVIVING_BLOW_REFUSED_TOKEN)
        self.assertEqual(len(said), 1, self.console.lines)
        self.assertIn(REFUSE_NO_SCENE, said[0])


class AConsoleThatCannotBeWrittenToCostsALineNotAFrameTests(
        SurvivingBlowTestBase):
    """Round 59iqwi's D7 scar, pinned for both call sites in this file's area.

    The cp874 console this project runs on raised UnicodeEncodeError out of
    a bare print once already.  Neither of these functions may lose a frame
    to that.
    """

    def test_the_surviving_blow_call_keeps_its_frames(self):
        self.kill()
        expected = loot_actions(sustain_a_kill(self.cell, self.legacy, ()))
        builtins.print = _Console(raising=True)
        actions = reannounce_ground_after_a_surviving_blow(
            self.cell, self.legacy, _Step(False))
        self.assertEqual(
            [a[1:] for a in actions], [a[1:] for a in expected],
            "the line is what a dead console costs, never the frames")

    def test_reannounce_ground_keeps_its_frames_too(self):
        # The sibling call site (chief's 0x4B98 responder) said NEVER RAISES
        # in its docstring while printing bare.  Same round, same fix.
        self.kill()
        expected = loot_actions(sustain_a_kill(self.cell, self.legacy, ()))
        builtins.print = _Console(raising=True)
        actions = reannounce_ground(self.cell, self.legacy)
        self.assertEqual(
            [a[1:] for a in actions], [a[1:] for a in expected])

    def test_reannounce_ground_refusal_path_does_not_raise_either(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        builtins.print = _Console(raising=True)
        self.assertEqual(reannounce_ground(cell, self.legacy), ())
        self.assertEqual(
            reannounce_ground(cell, self.legacy, scene=SCENE), ())


class TheWiringAskIsOneLineForChiefTests(unittest.TestCase):
    def test_the_wiring_string_names_the_function_and_the_branch(self):
        wiring = mob_drop_presence.GROUND_SURVIVING_BLOW_WIRING
        self.assertIn("reannounce_ground_after_a_surviving_blow", wiring)
        self.assertIn("MOB_COMBAT_BAR", wiring)
        self.assertIn("step.death_due", wiring)

    def test_it_is_not_the_withdrawn_movement_resend(self):
        wiring = mob_drop_presence.GROUND_SURVIVING_BLOW_WIRING
        self.assertNotIn("TARGET_POS_VITAL", wiring)
        self.assertNotIn("scenario", wiring)


if __name__ == "__main__":
    unittest.main()
