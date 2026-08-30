"""LANE-B: PANYA-ORDER 2026-08-30T14:50+07:00, step 1-2 -- can the ground-loot
element be made to stay visible and clickable for >= 30 seconds, and can that
be proven headless before any attended round burns a boot on it.

THE ANSWER THIS FILE PROVES, MECHANICALLY.  ``mob_drop_presence.sustain_a_kill``
(MOB-DROP-PRESENCE-001, already wired into runtime.py's per-kill path) composes
its frames from the WHOLE LIVE LEDGER every time it is called, whether or not
that call carries a new kill's drops.  Calling it again with ``drops=()`` costs
no placement, no key, no byte layout this project has not already shipped: it
is the same function the per-kill dispatch already calls, called one more
time.  So "resend the frame periodically" -- the second option PANYA-ORDER's
letter names ("ยืดอายุ หรือส่งเฟรมซ้ำเป็นระยะ") -- is not a new mechanism to
build.  It already exists, and this file is the proof.

WHAT THIS FILE DOES NOT CLAIM.  It proves the SERVER can keep re-emitting valid
frames for a live row across a >= 30 s window (here, 34 s of simulated time,
comfortably inside the 120 s ``DROP_LIFETIME_SECONDS`` ceiling).  It does NOT
touch a client, and ``mob_drop_presence.REEMISSION_REDRAWS_THE_LABEL`` stays
``None`` -- whether the client's label is actually redrawn by a resend is an
attended-only question this file cannot answer.  What it retires is the
question of whether the SERVER side of "resend periodically" needs new code:
it does not.

WHY A CLOCK THAT IS A LIST OF NUMBERS.  Same shape as
tests/test_mob_drop_presence.py and tests/test_mob_loot_expiry.py, and for the
same reason: nothing here sleeps, races, or depends on wall time.

CORE-REQUEST for chief (runtime.py -- out of this lane's write zone): the one
call site this proof justifies is documented as
``DROP_PRESENCE_RESEND_ON_MOVEMENT_WIRING`` in
``src/pirateforce_foundation/mob_drop_presence.py``.
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
    STATE_SUSTAINED,
    sustain_a_kill,
)

KILLER = 0x750059
# The window PANYA-ORDER named, plus a margin so an off-by-one at the boundary
# would show up as a hole in the middle of the run, not just at the edge.
REQUESTED_MIN_VISIBLE_SECONDS = 30.0
PROVEN_WINDOW_SECONDS = 34.0
# Arbitrary and deliberately NOT a round number: a caller driven by a real
# client event (TargetPosVital) does not arrive on a metronome, and a test
# that only ever advances the clock by 1.0 would not catch a boundary defect
# that only shows up on an uneven cadence.
RESEND_INTERVALS = (0.0, 2.0, 5.0, 3.0, 4.0, 1.0, 6.0, 2.0, 5.0, 4.0, 2.0)


class _Clock:
    """A clock that only moves when a test says so."""

    def __init__(self, now=1000.0):
        self.now = float(now)

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += float(seconds)


class TheResendMechanismAlreadyWorksTests(unittest.TestCase):
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
        if not cls.dropping:
            raise unittest.SkipTest("this scene's tables drop almost nothing")

    def setUp(self):
        self.clock = _Clock()
        self.cell = mob_loot.DropLedgerCell(clock=self.clock)

    def _kill(self):
        mob, seed = self.dropping[0]
        drops = self.cell.loot_a_kill(
            mob, DeathRecord(mob.actor_identity, KILLER, mob.max_hp),
            mob_loot.roll_drops(mob, random.Random(seed)), kill_token=1)
        self.assertTrue(drops, "this test needs a kill with rows")
        return drops

    def test_a_resend_with_no_new_kill_still_sustains_the_row(self):
        """The one-call proof: drops=() is not a no-op, it is a resend."""
        drops = self._kill()
        step = sustain_a_kill(self.cell, self.legacy, drops)
        self.assertEqual(step.state, STATE_SUSTAINED)

        self.clock.advance(10.0)
        resend = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(resend.state, STATE_SUSTAINED)
        self.assertTrue(resend.frames, "a resend must still carry the row")
        self.assertEqual(resend.announced, 0, "no new kill, nothing new")
        self.assertEqual(resend.carried, len(drops))
        # And the row is still there to be taken -- a resend never re-places.
        self.cell.take(drops[0].drop_key)

    def test_repeated_resends_cover_a_window_well_past_thirty_seconds(self):
        """The headless proof PANYA-ORDER step 2 asks for.

        Drives ``sustain_a_kill(cell, legacy, ())`` on an uneven cadence
        across >= 30 s of simulated time (34 s here) and asserts every single
        call in that window returns a live, non-empty frame for the row that
        was there from the start -- exactly what a caller wired to a
        frequent, already-existing client event (TargetPosVital) would see.
        """
        drops = self._kill()
        first = sustain_a_kill(self.cell, self.legacy, drops)
        self.assertEqual(first.state, STATE_SUSTAINED)

        elapsed = 0.0
        calls = 0
        for interval in RESEND_INTERVALS:
            self.clock.advance(interval)
            elapsed += interval
            step = sustain_a_kill(self.cell, self.legacy, ())
            calls += 1
            self.assertEqual(
                step.state, STATE_SUSTAINED,
                "resend #%d at t=%.1fs did not sustain the row" % (
                    calls, elapsed))
            self.assertTrue(
                step.frames, "resend #%d at t=%.1fs sent no frame" % (
                    calls, elapsed))
            self.assertIn(drops[0].drop_key, {row.drop_key for row in step.rows})
            self.assertGreater(
                self.cell.time_left(drops[0].drop_key), 0.0,
                "the row expired inside the proven window")

        self.assertGreaterEqual(elapsed, PROVEN_WINDOW_SECONDS)
        self.assertGreaterEqual(elapsed, REQUESTED_MIN_VISIBLE_SECONDS)
        # Still takeable at the end of the window: a resend never spends the
        # row it keeps re-announcing.
        taken = self.cell.take(drops[0].drop_key)
        self.assertEqual(taken.drop_key, drops[0].drop_key)

    def test_a_resend_never_places_a_new_row_or_moves_the_deadline(self):
        """The cost claim: N resends of one kill still cost exactly one row.

        pf-adversary check: a resend that silently re-placed the drop (instead
        of reading the existing ledger) would still pass the two tests above
        by accident, because a freshly-placed row is also live and also
        announced.  This test would catch that: the deadline must not move.
        """
        drops = self._kill()
        sustain_a_kill(self.cell, self.legacy, drops)
        deadline_before = self.cell.time_left(drops[0].drop_key)

        for _ in range(5):
            self.clock.advance(1.0)
            sustain_a_kill(self.cell, self.legacy, ())

        self.assertEqual(len(self.cell.ledger.drops), 1)
        # 5 s of clock advanced, zero re-placement: time left dropped by
        # exactly the elapsed time, not reset by any resend.
        self.assertAlmostEqual(
            self.cell.time_left(drops[0].drop_key),
            deadline_before - 5.0, places=6)

    def test_a_resend_after_the_row_expires_reports_nothing_on_the_ground(self):
        """The honest edge: past the 120 s ceiling, a resend has nothing to
        resend, and must say so rather than fabricate a frame."""
        drops = self._kill()
        sustain_a_kill(self.cell, self.legacy, drops)
        self.clock.advance(mob_loot.DROP_LIFETIME_SECONDS + 1.0)
        step = sustain_a_kill(self.cell, self.legacy, ())
        self.assertEqual(step.state, mob_drop_presence.STATE_NOTHING_ON_THE_GROUND)
        self.assertFalse(step.frames)


if __name__ == "__main__":
    unittest.main()
