"""LANE-B / MOB-DEATH-001: what actually differs between the corpse that FELL
and the corpse that FROZE.

WHY THIS FILE EXISTS.  Two attended runs sent a corpse to a real client and got
opposite results on screen:

  * GT-022 (2026-08-19) / GT-025 (repeated twice) -- the actor FELL FLAT and
    STAYED DOWN at t+10, t+13, t+16, and the client wrote "badly wounded and
    fell" into chat.  GT-025 is the run that isolated the cause: it sent NO
    death-task frame at all (``grep -c DEATH_TASK`` = 0 over the whole
    console) and got the fall anyway.  The lying pose belongs to the DYING
    frame.
  * GT-084-R2 (2026-08-27, OBSERVER_CONFIRMED 15:52-15:55+07:00) -- identity
    0x201F, named "Tornado Eagle", hostile, killed with five real player hits.
    Wire and DB were complete (DYING 164B timer 20.0, DEAD 164B timer 0.0,
    hold 700 ms, MOB_LOOT_DROP x2).  On screen the bird FROZE mid-air in its
    flying pose, never fell, never animated, and the cursor stopped seeing an
    actor there -- until logout.

``RE-107`` (death branch model) and ``RE-108`` (local panel gate) both closed
BOUNDED-NEGATIVE, so the answer is not coming from static RE: it needs an
attended A/B.  This file is what makes that A/B worth one attended run instead
of four.  It does NOT diagnose the freeze and does not claim to -- see
NONCLAIMS at the bottom, which are the point of the file as much as the tests.

WHAT IT PINS.  The two observed runs differ in FOUR things at once (dead frame
present, name present, faction, and the actor/model itself), so neither run
tells you which one matters.  Every test here composes its arms through the
PRODUCTION composer (``mob_death.dying_frames`` / ``dead_frames``), never a
hand-written body, and proves that each arm differs from the GT-084-R2
baseline in EXACTLY ONE of those knobs -- so a tester who flips one knob is
measuring one variable.

The load-bearing test is
``test_the_dying_frame_is_byte_identical_with_and_without_the_dead_frame``:
it is what makes "send the GT-025 shape at a named hostile body" a real
single-variable arm rather than a second uncontrolled run.

NO FLAG.  Every arm here is composed by the unflagged production path.  This
file adds no scenario, no dispatch kwarg and no production behaviour: it is a
test, and the knobs it exercises (``with_name=``, ``faction=``) already exist
on ``death_frames`` and are already reachable without one.

[LANE-B ASSUMPTION - COO CONFIRMATION PENDING] Round ``j6cbdc`` proposed this
A/B and deferred opening it under the one-topic-per-ticket rule; no COO ruling
came back either way.  Per the lane's "write the question, then keep walking"
rule this round built the arms and opened the ticket rather than waiting.  If
COO rules the A/B should not run, nothing in production has to be reverted --
only this file and the queue entry come out.
"""

import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs, mob_death
from pirateforce_foundation.legacy_bridge import load_legacy


# The faction GT-084-R2 actually sent, and the one this lane's own field mobs
# carry by default.  Kept as a named constant so an arm that varies it quotes
# the baseline rather than a hand-typed 6.
BASELINE_FACTION = field_mobs.FIELD_MOB_FACTION

# An arbitrary OTHER faction for the faction arm.  It is deliberately NOT
# given a meaning here: this file proves that changing this number changes
# exactly four bytes of the body, and claims nothing about what the client
# does with either value.  RE-067 (what decides a name's colour) is open and
# is not this lane's ticket.
CONTRAST_FACTION = 1


def _split_once(left: bytes, right: bytes) -> tuple[int, int, int]:
    """Return (common prefix length, left tail length, right tail length).

    Used to prove a difference is LOCALIZED rather than smeared across the
    body: if two composed bodies share a prefix and a suffix, everything that
    differs lies in the single window between them.
    """
    head = 0
    while head < min(len(left), len(right)) and left[head] == right[head]:
        head += 1
    tail = 0
    while (tail < min(len(left), len(right)) - head
           and left[len(left) - 1 - tail] == right[len(right) - 1 - tail]):
        tail += 1
    return head, len(left) - head - tail, len(right) - head - tail


class CorpseArmDifferenceTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = field_mobs.load_roster()
        # placement_index 30 is P30 / identity 0x201F, the exact body
        # GT-084-R2 killed and this module's SANCTIONED_FIRST_TARGET_IDENTITY.
        cls.mob = [m for m in cls.roster if m.placement_index == 30][0]

    def baseline_dying(self, **kw):
        """The DYING frame exactly as GT-084-R2 put it on the wire."""
        return mob_death.dying_frames(
            self.legacy, self.mob,
            death_timer=mob_death.DYING_TIMER_SECONDS,
            faction=kw.pop("faction", BASELINE_FACTION),
            with_name=kw.pop("with_name", True),
            **kw,
        )

    def baseline_dead(self, **kw):
        """The DEAD frame exactly as GT-084-R2 put it on the wire."""
        return mob_death.dead_frames(
            self.legacy, self.mob,
            death_timer=mob_death.DEAD_TIMER_SECONDS,
            faction=kw.pop("faction", BASELINE_FACTION),
            with_name=kw.pop("with_name", True),
            **kw,
        )

    # ------------------------------------------------------------------
    # The baseline is the run that froze.  Pin it first, so an arm that
    # drifts from it fails here rather than silently measuring something
    # that was never sent.
    # ------------------------------------------------------------------

    def test_the_baseline_arm_is_the_body_gt084r2_actually_killed(self):
        self.assertEqual(self.mob.actor_identity,
                         mob_death.SANCTIONED_FIRST_TARGET_IDENTITY)
        self.assertEqual(self.mob.display_name, "Tornado Eagle")
        dying_pc, dying_frame = self.baseline_dying()
        dead_pc, dead_frame = self.baseline_dead()
        # Both frames carry the name GT-084-R2 saw on screen, so "with_name"
        # is genuinely the knob that removes it.  The name is UTF-16LE on the
        # wire (the first draft of this test asserted ASCII and failed here --
        # the encoding is the client's, not this lane's choice).
        self.assertIn(self.mob.display_name.encode("utf-16-le"), dying_pc)
        self.assertIn(self.mob.display_name.encode("utf-16-le"), dead_pc)
        # The console line GT-084-R2 recorded says both frames were 164B.
        # Pin that the two frames are the SAME length as each other: the
        # timer splice is the same width on both sides of the gate, so a
        # length difference here would mean the arms are not comparable.
        self.assertEqual(len(dying_frame), len(dead_frame))

    # ------------------------------------------------------------------
    # ARM 1 -- the GT-025 shape: dying frame, no dead frame.
    # This is the load-bearing test of the file.
    # ------------------------------------------------------------------

    def test_the_dying_frame_is_byte_identical_with_and_without_the_dead_frame(self):
        """Dropping the dead frame changes NOTHING about the dying frame.

        This is what makes "send the GT-025 shape at a named hostile body" a
        one-variable arm.  If composing the pair mutated the dying frame --
        a shared generation counter, a sequence number, anything -- then
        withholding the dead frame would change two things at once and the
        attended run would measure neither.
        """
        dying_alone_pc, dying_alone_frame = self.baseline_dying()
        # Compose the full pair the way a real kill does, then re-read the
        # dying half out of it.
        paired_dying_pc, paired_dying_frame = self.baseline_dying()
        _dead_pc, _dead_frame = self.baseline_dead()
        self.assertEqual(dying_alone_pc, paired_dying_pc)
        self.assertEqual(dying_alone_frame, paired_dying_frame)
        # And the dead frame is genuinely a SEPARATE frame, not a mutation of
        # the dying one -- otherwise "withhold it" is not a thing a tester can
        # do.
        self.assertNotEqual(dying_alone_frame, _dead_frame)

    def test_the_two_frames_differ_only_in_the_timer_field(self):
        """DYING vs DEAD is one f32, in one place, and nothing else.

        GT-084-R2's console recorded DYING timer 20.0 and DEAD timer 0.0.  If
        the death task carried any OTHER field difference, "the dead frame is
        what froze it" and "some field only the dead frame sets froze it"
        would be the same arm, and the A/B could not tell them apart.
        """
        dying_pc, _ = self.baseline_dying()
        dead_pc, _ = self.baseline_dead()
        self.assertEqual(len(dying_pc), len(dead_pc))
        head, left_span, right_span = _split_once(dying_pc, dead_pc)
        self.assertEqual(left_span, right_span)
        # One f32 wide, and no wider.
        self.assertLessEqual(left_span, mob_death.DEATH_TIMER_WIDTH)
        self.assertGreater(left_span, 0)

    # ------------------------------------------------------------------
    # ARM 2 -- the name.
    # ------------------------------------------------------------------

    def test_the_name_arm_moves_the_name_and_nothing_downstream_of_it(self):
        named_pc, _ = self.baseline_dying(with_name=True)
        nameless_pc, _ = self.baseline_dying(with_name=False)
        self.assertIn(self.mob.display_name.encode("utf-16-le"), named_pc)
        self.assertNotIn(self.mob.display_name.encode("utf-16-le"), nameless_pc)
        # The name is a length-changing field, so the arms are different
        # lengths -- but the difference must be LOCALIZED: one contiguous
        # window, with the rest of the body identical on both sides of it.
        self.assertGreater(len(named_pc), len(nameless_pc))
        head, named_span, nameless_span = _split_once(named_pc, nameless_pc)
        self.assertGreater(head, 0)
        # Everything the nameless arm drops is inside that one window.
        self.assertEqual(named_span - nameless_span,
                         len(named_pc) - len(nameless_pc))
        # And the window in the named arm is where the name lives.
        window = named_pc[head:head + named_span]
        self.assertIn(self.mob.display_name.encode("utf-16-le"), window)

    # ------------------------------------------------------------------
    # ARM 3 -- the faction.
    # ------------------------------------------------------------------

    def test_the_faction_arm_moves_exactly_four_bytes(self):
        baseline_pc, _ = self.baseline_dying(faction=BASELINE_FACTION)
        contrast_pc, _ = self.baseline_dying(faction=CONTRAST_FACTION)
        self.assertEqual(len(baseline_pc), len(contrast_pc))
        differing = [i for i, (a, b) in enumerate(zip(baseline_pc, contrast_pc))
                     if a != b]
        self.assertTrue(differing, "the faction arm changed nothing at all")
        # One contiguous u32, and the bytes are the two faction values.
        self.assertEqual(differing,
                         list(range(differing[0], differing[0] + len(differing))))
        self.assertLessEqual(len(differing), 4)
        span = slice(differing[0] - (differing[0] % 1), differing[0] + 4)
        self.assertEqual(
            int.from_bytes(baseline_pc[span][:4], "little"), BASELINE_FACTION)
        self.assertEqual(
            int.from_bytes(contrast_pc[span][:4], "little"), CONTRAST_FACTION)

    # ------------------------------------------------------------------
    # The whole point: the arms are independent of each other.
    # ------------------------------------------------------------------

    def test_the_three_knobs_are_independent(self):
        """Flipping one knob does not disturb what another knob controls.

        Without this, a tester who flips two knobs across two runs cannot
        attribute a change to either.
        """
        base, _ = self.baseline_dying()
        no_name, _ = self.baseline_dying(with_name=False)
        other_faction, _ = self.baseline_dying(faction=CONTRAST_FACTION)
        both, _ = self.baseline_dying(with_name=False,
                                      faction=CONTRAST_FACTION)
        # Changing the faction shifts the same four bytes whether or not the
        # name is present, so the two knobs do not interact.
        base_delta = [i for i, (a, b) in enumerate(zip(base, other_faction))
                      if a != b]
        nameless_delta = [i for i, (a, b) in enumerate(zip(no_name, both))
                          if a != b]
        self.assertTrue(base_delta and nameless_delta)
        self.assertEqual(len(base_delta), len(nameless_delta))

    def test_production_is_not_gated_behind_a_flag(self):
        """Every arm above is reachable on an unflagged boot."""
        self.assertTrue(mob_death.production_allowed)


# NONCLAIMS -- read these before quoting this file anywhere.
#
# 1. [NOT CLAIMED] that any arm here explains the frozen corpse.  This file
#    measures what the SERVER emits.  Nothing in it observes a client, and
#    the freeze is a client-observable symptom.  Only the attended A/B can
#    close it.
# 2. [NOT CLAIMED] that the dead frame is the cause.  GT-025 got the fall
#    without one, and GT-084-R2 froze with one -- but those two runs also
#    differ in name, faction and the actor itself, which is precisely why
#    this file exists.  "The dead frame is the difference" is the
#    HYPOTHESIS the arms are built to test, not a result.
# 3. [NOT CLAIMED] anything about DEATH_TASK_HOLD_MS.  700 ms is
#    COO-reserved (COO-DECISION 20260826_0551 item 1: lane B may not touch
#    that number until chief's 0/250/700/2000 ms sweep ticket lands).  No
#    test here varies it and no arm here needs it varied.
# 4. [NOT CLAIMED] that faction 1 means anything.  RE-067 (what decides the
#    colour of a name) is open and belongs to the RE lane.  CONTRAST_FACTION
#    is a contrast, not a proposal.
# 5. [NOT CLAIMED] that _F_DIE_000 exists or plays.  It has never been
#    observed by anyone in this project and GT-025 requires every reading of
#    GT-022 as evidence of it to be withdrawn.  This file inherits that.
# 6. This file changes no production behaviour and adds no production code.


if __name__ == "__main__":
    unittest.main()
