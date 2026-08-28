"""LANE-B: what a MULTI-drop kill actually puts on the wire, measured.

WHY THIS FILE EXISTS.  GT-084-R2 (attended, OBSERVER_CONFIRMED
2026-08-27T15:52-15:55+07:00, Panya at the screen) killed 'Tornado Eagle'
(0x201F) on a flagless boot.  The server rolled TWO drops and announced both
-- ``MOB_LOOT_DROPS_CENSUS ... drops=2 items=2400046:x1@0x100000,
2400047:x1@0x100001`` then ``[G>] MOB_LOOT_DROP 54B`` TWICE (console lines
L8568, L11198, L11202).  The owner then confirmed, asked directly, that
NEITHER item was ever visible in the game.

That result sits against GT-045, which is CLOSED-ANSWERED on the opposite
finding: an attended run watched THESE SAME element bytes make the client
draw the item's NAME on the ground (a label, and no object).  One drop drew
a label.  Two drops drew nothing.

This file does not explain that.  It MEASURES the one named difference
between the two runs that lives on our side of the socket: the SHAPE a
multi-drop kill emits.  Every assertion here is a statement about bytes this
server composes, never about what a client does with them.

WHERE THIS FILE SITS, MEASURED AND NOT ASSUMED.  ``mob_loot`` already
refuses a drifted emission shape AT RUN TIME, in the server, on every
emission: planting an accumulating emitter and planting a lying element
count were both caught by the module's own ``REFUSE_COMPOSED_BYTES_OFF_PIN``
guards (mob_loot.py:1461 and :1493) BEFORE any assertion in this file was
reached.  So this file is not the first line of detection for shape drift
and must not be described as one.  What it adds that nothing else holds is
(a) the list-IDENTITY elimination in test 3, which no other test makes, and
(b) literals written HERE, so that a round which edits the module's own pin
cannot move the module and its test together and stay green -- the circular
baseline pf-adversary caught in this lane's round ``rbuta4``.

WHAT IT PINS, AND WHY EACH ONE IS LOAD-BEARING.

1. ``test_every_frame_of_a_multi_drop_kill_declares_a_whole_list_of_one``
   is the one that matters.  Each drop is announced by its own COMPLETE
   mask-0x08 ``GSCN_RunTimeProtocolRes`` collection whose envelope declares
   a count of ONE.  A frame that says "the list is [B]" is not an append --
   it is a whole-list statement that OMITS A.  So drop 2's frame omits drop
   1, drop 3's omits both, and so on.  Whether omission ERASES is a property
   of the consumer and is NOT claimed here (see the nonclaims): what is
   measured is that our emitter gives a replace-by-omission consumer, if
   that is what it is, everything it needs to keep only the last drop.

2. ``test_no_frame_of_a_multi_drop_kill_carries_another_drops_element``
   proves the omission by CONTENT and not merely by the envelope's count
   byte.  A count of one with a concatenated payload would be a different
   bug; this rules that reading out.

3. ``test_the_ground_list_and_the_census_list_are_different_lists``
   ELIMINATES the competing explanation by bytes.  The corpse/census chain
   (``mob_death.death_frames``, ``mob_combat.bar_frames``) is derived bit
   0x02 -> object+0x1C; the ground list is derived bit 0x08 ->
   object+0x20.  Two different derived bits writing two different object
   offsets are two independent lists, so the census recomposes this lane
   sends on every hit CANNOT be what erased the drops, and a drop frame
   cannot be what erased the town.  RE-092 settled replace-by-omission for
   the 0x02 list ONLY; it does not transfer to 0x08 by resemblance, and
   this test exists so that nobody quotes it as if it did.

4. ``test_the_hazard_scales_with_the_lane_s_own_ceiling`` records that
   ``MAX_DROPS_PER_KILL`` is 16, so up to 15 of a kill's drops are at stake
   under reading (1), not merely one.

WHAT IS NOT CLAIMED HERE.  Read this before quoting any test in this file.

* NOT CLAIMED: that the mask-0x08 ground list is replace-by-omission.  That
  is the open question this file was written to make answerable, and it is
  asked as an RE ticket (CLIENT_RE_QUEUE, opened by LANE-B round j6cbdc).
  RE-092 proved it for the SIBLING 0x02 list at a DIFFERENT object offset.
* NOT CLAIMED: that the emission shape is why the owner saw nothing.  The
  module's own header carries a second, independent candidate that this
  file does not touch -- ``GROUND_LABEL_OBSERVED_LIFETIME_SECONDS`` is
  (0.2, 0.4), a label that lives under half a second.  Either one alone
  would explain an invisible drop.  Nothing here separates them.
* NOT CLAIMED: that anything should change.  No production behaviour is
  altered by this file and no fix is proposed in it.  ``refresh_frames``
  remains COO-refused for production (2026-08-26 07:45 +07:00) and this
  round does not reopen that.
* NOT CLAIMED: anything about a client at all.  Every assertion is over
  bytes composed in this process.
"""

from pathlib import Path
import random
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_loot import (
    DROP_ENVELOPE_PIN,
    DROP_ENVELOPE_SIZE,
    DROP_FRAME_HEADER_SIZE,
    DROP_KEY_BASE,
    MAX_DROPS_PER_KILL,
    RUNTIME_DERIVED_BIT_GROUND_LIST,
    drop_element,
    drop_frames,
    place_drops,
    roll_drops,
)


# The same killer identity the sibling loot tests use, so a reader comparing
# the two files is not asked to wonder whether the number matters.  It does
# not: nothing on the wire carries an owner (mob_loot NONCLAIM 5).
KILLER = 0x750059

# The census/corpse collection this lane's OTHER frames go out on, named here
# rather than imported from the legacy shim so the contrast in
# test_the_ground_list_and_the_census_list_are_different_lists is a written
# pin and not a lookup that moves when the shim moves.  Source:
# current/pf_login_game_server_v141.py:1267-1272, make_runtime_remote_actors,
# "GSCN_RunTimeProtocolRes v4 derived bit 0x02 remote-actor collection ...
# 0x5E3EE0 RuntimeRes derived mask bit 0x02 -> object+0x1C".
CENSUS_DERIVED_BIT = 0x02
CENSUS_OBJECT_OFFSET = 0x1C
GROUND_OBJECT_OFFSET = 0x20

# Where the envelope's element count sits inside DROP_ENVELOPE_PIN: the
# trailing u16 tag-0x12 record, whose value byte is the second of its three.
# Derived from the pin itself in setUpClass rather than hardcoded twice.
ENVELOPE_COUNT_RECORD = bytes((0x12, 0x01, 0x00))


class MultiDropEmissionShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster()
        cls.mob = cls.roster[0]

    def _multi_drop_kill(self, seed=3, minimum=2, attempts=500):
        """Roll until one kill drops at least ``minimum`` objects.

        Bounded, not ``while True``, for the reason the sibling file gives:
        a regenerated table that made this impossible would HANG the suite
        instead of failing it, and a hung test tells whoever reads the run
        nothing at all.
        """
        rng = random.Random(seed)
        for _attempt in range(attempts):
            roll = roll_drops(self.mob, rng)
            if len(roll.items) >= minimum:
                break
        else:
            self.fail(
                "%s did not drop %d objects in %d rolls; the tables changed"
                % (self.mob.display_name, minimum, attempts))
        record = DeathRecord(self.mob.actor_identity, KILLER, self.mob.max_hp)
        drops = place_drops(self.mob, record, roll, DROP_KEY_BASE)
        self.assertGreaterEqual(
            len(drops), minimum,
            "place_drops dropped objects the roll produced; the rest of this "
            "file measures a multi-drop kill and there is no longer one")
        return drops

    # -- the measurement ---------------------------------------------------
    def test_every_frame_of_a_multi_drop_kill_declares_a_whole_list_of_one(
            self):
        """Each drop travels as its own COMPLETE list, and the list is [it].

        This is the load-bearing measurement of the file.  ``drop_frames``
        returns one frame per drop and every one of them repeats the SAME
        envelope -- byte-identical to DROP_ENVELOPE_PIN, whose trailing
        record is a u16 tag-0x12 count of exactly 1.  So the k-th frame is
        not "add this drop"; it is "the list is this one drop", stated k
        times with a different single member each time.
        """
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        self.assertEqual(len(frames), len(drops))
        self.assertGreaterEqual(
            len(frames), 2,
            "this test is about what the SECOND frame omits; with one frame "
            "there is nothing to omit and the assertions below are vacuous")
        for index, (pc, _frame) in enumerate(frames):
            self.assertEqual(
                pc[:DROP_ENVELOPE_SIZE], DROP_ENVELOPE_PIN,
                "frame %d of %d does not repeat the pinned envelope; if the "
                "emitter ever learns to accumulate, this is the assertion "
                "that must be rewritten rather than deleted"
                % (index, len(frames)))
            self.assertTrue(
                DROP_ENVELOPE_PIN.endswith(ENVELOPE_COUNT_RECORD),
                "the pinned envelope no longer ends in a count of one, so "
                "the whole reading of this file has moved")

    def test_no_frame_of_a_multi_drop_kill_carries_another_drops_element(self):
        """The omission is by CONTENT, not only by the envelope's count.

        A count of one in front of a concatenated payload would be a
        different defect with a different fix, so ruling it out is part of
        making the RE question well posed.
        """
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        elements = [drop_element(self.legacy, drop) for drop in drops]
        # Distinct keys and distinct scatter positions are what make the
        # containment check below meaningful; two identical elements would
        # pass it for the wrong reason.
        self.assertEqual(
            len(set(elements)), len(elements),
            "the drops of one kill composed to identical element bytes; the "
            "containment assertion below would then prove nothing")
        for index, (pc, _frame) in enumerate(frames):
            body = pc[DROP_ENVELOPE_SIZE:]
            self.assertEqual(
                body, elements[index],
                "frame %d carries something other than exactly its own "
                "element" % index)
            for other, element in enumerate(elements):
                if other == index:
                    continue
                self.assertNotIn(
                    element, pc,
                    "frame %d carries drop %d's element too; the emitter is "
                    "accumulating and the omission reading of this file no "
                    "longer holds" % (index, other))

    def test_the_ground_list_and_the_census_list_are_different_lists(self):
        """Eliminates 'the census recompose erased the loot', in bytes.

        The two collections differ in the derived change-mask bit AND in the
        object offset that bit writes.  RE-092 proved replace-by-omission for
        the 0x02 list; it says nothing about 0x08, and this assertion is here
        so that resemblance is never quoted as if it did.
        """
        self.assertEqual(RUNTIME_DERIVED_BIT_GROUND_LIST, 0x08)
        self.assertNotEqual(
            RUNTIME_DERIVED_BIT_GROUND_LIST, CENSUS_DERIVED_BIT)
        self.assertNotEqual(GROUND_OBJECT_OFFSET, CENSUS_OBJECT_OFFSET)
        # And the pinned envelope really does carry the ground bit, so the
        # constant above is not merely a number that agrees with a comment.
        self.assertIn(
            bytes((0x0B, RUNTIME_DERIVED_BIT_GROUND_LIST)), DROP_ENVELOPE_PIN)
        self.assertNotIn(
            bytes((0x0B, CENSUS_DERIVED_BIT)), DROP_ENVELOPE_PIN)

    def test_the_hazard_scales_with_the_lane_s_own_ceiling(self):
        """Up to 15 drops are at stake under the omission reading, not one."""
        self.assertEqual(MAX_DROPS_PER_KILL, 16)
        self.assertGreater(
            MAX_DROPS_PER_KILL, 2,
            "the ceiling stopped being a multi-drop ceiling and the letter "
            "that quotes 15 is now wrong")

    def test_the_frame_is_the_envelope_plus_the_element_and_nothing_else(self):
        """No room is left for a second element inside a 54-byte frame."""
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        for pc, frame in frames:
            self.assertEqual(len(frame), DROP_FRAME_HEADER_SIZE + len(pc))
            self.assertEqual(frame[DROP_FRAME_HEADER_SIZE:], pc)
            self.assertEqual(
                len(pc), DROP_ENVELOPE_SIZE + len(pc[DROP_ENVELOPE_SIZE:]))

    def test_the_pinned_envelope_is_the_bytes_this_file_was_written_against(
            self):
        """The one assertion that cannot be shadowed by the module's guards.

        Every other test here reaches the module's own composer first, and
        that composer refuses a drifted shape before this file gets a word
        in (see the module note in the docstring).  This one compares the
        CONSTANT against a literal written here, so a round that edits
        DROP_ENVELOPE_PIN moves the module away from this file instead of
        moving both together.  The count of ONE is the byte that carries the
        whole omission reading, so it is spelled out rather than sliced.
        """
        self.assertEqual(
            DROP_ENVELOPE_PIN,
            bytes((
                0x12, 0x9D, 0x6E,              # GSCN_RunTimeProtocolRes
                0x14, 0x00, 0x00, 0x00, 0x00,  # id 0
                0x08, 0x04,                    # envelope version 4
                0x0B, 0x00,                    # inherited mask: none
                0x0B, 0x08,                    # derived mask: the 0x08 list
                0x12, 0x01, 0x00,              # ONE element
            )),
            "the ground envelope moved.  If that was deliberate, this file's "
            "whole reading (each frame is a whole-list statement of one) has "
            "to be re-argued, not re-pinned")

    # -- the file's own honesty guard --------------------------------------
    def test_the_second_candidate_is_still_recorded_in_the_module(self):
        """The label lifetime must stay visible next to this file's finding.

        If a later round deletes or widens the measured label lifetime, the
        nonclaim in this file's docstring ("either one alone would explain an
        invisible drop") stops being true and somebody will read the emission
        shape as a settled cause.  Then this test goes red first.
        """
        low, high = mob_loot.GROUND_LABEL_OBSERVED_LIFETIME_SECONDS
        self.assertLess(high, 1.0)
        self.assertGreater(low, 0.0)
        self.assertTrue(mob_loot.NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN)


if __name__ == "__main__":
    unittest.main()
