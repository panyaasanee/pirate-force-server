"""LANE-B round 59iqwi/next: reannounce_ground, the answer to chief's ask.

`pf_bridge/notes_to_chief/20260904_1708_CHIEF-TO-LANE-B-ground-reannounce-
function-request-and-two-guard-exemptions.md` (COO-DECISION 20260904_1649
item 2) asks for one function: given a session's ground-loot cell and the
legacy encoder, resend everything still live on that cell's scene as
actions ready to queue -- for the call site right after
`CheckSecondPwdVital 0x4B98` is answered, whose own reply frame KA1A
measured (finding 1, R309, `pf_bridge/notes_to_chief/20260904_1430`) ends
with an empty ground-list and makes the client clear a floor the server is
still holding.

This file pins the WIRE-LEVEL half of that answer: reannounce_ground()
composes the same frames `sustain_a_kill` would, never returns anything but
a tuple, and never raises out of the listener thread it is meant to sit
under.  GT-242 is the client-observable ticket that measures whether the
resent frame actually redraws the item on a real screen; nothing here
claims that.
"""

from pathlib import Path
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
    GROUND_REANNOUNCE_REFUSED_TOKEN,
    GROUND_REANNOUNCE_TOKEN,
    REFUSE_SCENE_DISAGREES,
    loot_actions,
    reannounce_ground,
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


class ReannounceTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster(scene=field_mobs.BG0002_SCENE)
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


class ReturnsATupleNeverNoneTests(ReannounceTestBase):
    """The contract chief's letter names explicitly: () not None, always."""

    def test_a_cell_with_nothing_on_the_ground_returns_an_explicit_empty_tuple(self):
        result = reannounce_ground(self.cell, self.legacy)
        self.assertEqual(result, ())
        self.assertIsInstance(result, tuple)

    def test_a_cell_with_something_on_the_ground_returns_a_nonempty_tuple(self):
        self.kill()
        result = reannounce_ground(self.cell, self.legacy)
        self.assertIsInstance(result, tuple)
        self.assertGreater(len(result), 0)

    def test_not_a_cell_at_all_returns_an_empty_tuple_not_none(self):
        self.assertEqual(reannounce_ground(None, self.legacy), ())
        self.assertEqual(reannounce_ground("not a cell", self.legacy), ())

    def test_a_cell_with_no_scene_returns_an_empty_tuple(self):
        cell = mob_loot.DropLedgerCell(clock=self.clock)
        self.assertEqual(reannounce_ground(cell, self.legacy), ())


class MatchesSustainAKillTests(ReannounceTestBase):
    """It reuses the shipped mechanism -- this pins that it really does."""

    def test_the_actions_equal_loot_actions_of_a_fresh_sustain_a_kill_call(self):
        self.kill()
        step = sustain_a_kill(self.cell, self.legacy, ())
        expected = loot_actions(step)
        got = reannounce_ground(self.cell, self.legacy)
        self.assertEqual(got, expected)

    def test_does_not_take_or_expire_anything_it_only_resends(self):
        drops = self.kill()
        before = self.cell.time_left(drops[0].drop_key)
        reannounce_ground(self.cell, self.legacy)
        after = self.cell.time_left(drops[0].drop_key)
        self.assertAlmostEqual(before, after, places=6)
        # still claimable afterwards -- nothing was removed from the ledger
        taken = self.cell.take(drops[0].drop_key)
        self.assertEqual(taken.drop_key, drops[0].drop_key)

    def test_two_calls_in_a_row_both_carry_the_whole_floor(self):
        first = self.kill(0)
        reannounce_ground(self.cell, self.legacy)
        second = self.kill(1)
        result = reannounce_ground(self.cell, self.legacy)
        self.assertEqual(len(result), 1)  # one generation, one frame
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(
            {row.drop_key for row in step.rows},
            {d.drop_key for d in first} | {d.drop_key for d in second})


class SceneCrossCheckTests(ReannounceTestBase):
    """``scene`` is an optional cross-check, never a source of truth."""

    def test_a_matching_scene_argument_still_composes(self):
        self.kill()
        got_without = reannounce_ground(self.cell, self.legacy)
        got_with = reannounce_ground(self.cell, self.legacy, scene=SCENE)
        self.assertEqual(got_without, got_with)

    def test_case_folding_matches_the_rest_of_the_lane(self):
        self.kill()
        got = reannounce_ground(self.cell, self.legacy, scene=SCENE.upper())
        self.assertNotEqual(got, ())

    def test_a_disagreeing_scene_is_refused_not_silently_resolved(self):
        self.kill()
        result = reannounce_ground(self.cell, self.legacy, scene="bg9999")
        self.assertEqual(result, ())

    def test_disagreeing_scene_refusal_does_not_touch_the_ledger(self):
        drops = self.kill()
        reannounce_ground(self.cell, self.legacy, scene="bg9999")
        # the row is exactly as it was -- a refused cross-check must not have
        # claimed, expired, or re-timed anything
        taken = self.cell.take(drops[0].drop_key)
        self.assertEqual(taken.drop_key, drops[0].drop_key)


class ConsoleTokenTests(ReannounceTestBase):
    """G-OBS: the token an attended round's GT-242 RECHECK greps for."""

    def test_a_composed_call_prints_the_token_with_items_count(self):
        self.kill()
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reannounce_ground(self.cell, self.legacy)
        out = buf.getvalue()
        self.assertIn(GROUND_REANNOUNCE_TOKEN, out)
        self.assertNotIn(GROUND_REANNOUNCE_REFUSED_TOKEN, out)
        self.assertIn("items=1", out)

    def test_an_empty_floor_still_prints_items_zero_not_silence(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = reannounce_ground(self.cell, self.legacy)
        out = buf.getvalue()
        self.assertEqual(result, ())
        self.assertIn(GROUND_REANNOUNCE_TOKEN, out)
        self.assertIn("items=0", out)
        self.assertNotIn(GROUND_REANNOUNCE_REFUSED_TOKEN, out)

    def test_a_refusal_prints_the_refused_token_and_a_named_reason(self):
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reannounce_ground(None, self.legacy)
        out = buf.getvalue()
        self.assertIn(GROUND_REANNOUNCE_REFUSED_TOKEN, out)

    def test_scene_disagreement_names_its_own_reason(self):
        self.kill()
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            reannounce_ground(self.cell, self.legacy, scene="bg9999")
        out = buf.getvalue()
        self.assertIn(GROUND_REANNOUNCE_REFUSED_TOKEN, out)
        self.assertIn(REFUSE_SCENE_DISAGREES, out)


class FailClosedTests(ReannounceTestBase):
    """A stranger's frame sits above this call.  Nothing here may raise."""

    def test_a_legacy_that_cannot_encode_is_refused_not_raised(self):
        self.kill()

        class _BrokenLegacy:
            def __getattr__(self, name):
                raise RuntimeError("no encoder here")

        result = reannounce_ground(self.cell, _BrokenLegacy())
        self.assertEqual(result, ())

    def test_a_scene_argument_that_cannot_be_read_is_refused_not_raised(self):
        self.kill()

        class _UnreadableScene:
            def __eq__(self, other):
                raise RuntimeError("scenes do not compare")

            def __hash__(self):
                return 0

        result = reannounce_ground(self.cell, self.legacy, scene=_UnreadableScene())
        self.assertEqual(result, ())


if __name__ == "__main__":
    unittest.main()
