"""LANE-B: what a multi-drop kill puts on the wire, and what the sibling
list does with the same envelope.

WHY THIS FILE EXISTS -- AND A WITHDRAWN CLAIM FIRST.

~~"GT-045 dropped one item and a label was drawn; GT-084-R2 dropped two and
nothing was seen, so the multi-drop emission shape is the named difference
between those two runs."~~  WITHDRAWN, and struck rather than deleted
because the letter and the RE ticket of round `j6cbdc` both quoted it before
pf-adversary took it apart.  IT IS FALSE AT THE SOURCE: GT-045 was ALSO a
two-element emission, and of the identical shape --
``ground_loot_hypothesis.py`` says so in terms ("the two elements travel as
TWO single-element frames, count=1 each, NOT as one count=2 collection")
and ``mob_loot.py``'s own header records that its two elements "went out 42
ms apart (NEAR 2200423 ... FAR 2200003)".  Same element count, same shape,
same derived bit.  There is no independent variable between the two runs on
this axis, so nothing here may be read as explaining why the owner saw
nothing in GT-084-R2.

WHAT IS ACTUALLY MEASURED HERE, then, is narrower and does not depend on
that comparison: the SHAPE this server emits for N drops, and the shape its
SIBLING list emits for N actors through the very same envelope.  The
contrast is the point, and it is what makes the open question worth asking:

* the ground list (derived bit 0x08) emits N drops as N SEPARATE
  collections, each declaring a count of ONE;
* the census list (derived bit 0x02), through the SAME
  ``GSCN_RunTimeProtocolRes`` envelope, puts N actors in ONE collection
  with a count of N -- and that is the shipped production path that has
  carried 115 actors to real clients (GT-078 wire layer 115/115, GT-121
  97/97).

So "a combined multi-record derived-mask collection is the one shape a real
client has already rejected" (``drop_frames``'s own justification, from the
V43 ErrorData=28317 measurement) is NOT a property of this envelope in
general.  Its sibling does exactly that, at 115 elements, in production,
accepted.  Whether the 0x08 CONSUMER can take the same treatment is
RE-129's question, and this file exists to state the contrast precisely
enough that the question can be answered instead of guessed at.

WHAT IS NOT CLAIMED.  Read before quoting anything here.

* NOT CLAIMED: that the emission shape is why any drop was invisible.  The
  round that wrote this file could not separate FOUR candidates and does
  not pretend to: (1) this shape, (2) the measured label lifetime of
  0.2-0.4 s, (3) the ITEM TABLE -- ``mob_loot`` NONCLAIM 3 records that
  2600001 (ITEM_MISC) "drew none in the run that carried it", and
  GT-084-R2's items 2400046/2400047 come from ITEM_CONSUMABLES, a table
  that has never drawn anything on this wire -- and (4) the state of the
  GT-084-R2 client itself, which in that same run froze the corpse in
  mid-air and would not open a target panel at all.  A client that will not
  draw a target panel is not a controlled observer for "did a label
  render".
* NOT CLAIMED: that the 0x08 list is replace-by-omission.  RE-092 settled
  that for the 0x02 list ONLY.  Indeed GT-045's own evidence leans the
  OTHER way: its two elements went out 42 ms apart and a label was still
  seen, which strict replace-by-omission would have to explain.
* NOT CLAIMED: that a count of one MEANS "the list is exactly this".  That
  reading is the question, not a finding.  What is measured is the count
  field's value and the payload's length -- both bytes.
* PARTLY A CLIENT CLAIM, AND SAID SO: the object offsets +0x1C and +0x20
  are offsets inside the CLIENT's deserialized object, from static RE
  (GT-040/GT-042 span pins).  This file does not assert over them; it
  asserts over the derived-mask BYTES the two composers emit, which is a
  wire fact.  The earlier draft of this docstring claimed "nothing about a
  client at all" while test 3 compared client-side offsets; that overreach
  is withdrawn too.
* NOT CLAIMED: that this file is the first line of defence.  ``mob_loot``
  refuses a drifted shape AT RUN TIME, in the server, on every emission
  (mob_loot.py:1455 pc size, :1461 envelope pin, :1488 frame size, :1493
  frame header).  A planted accumulating emitter is caught by the SIZE
  guards, not by the header pin an earlier draft of this note credited.
* NOT CLAIMED: that this file reproduces GT-084-R2.  It does not.
  ``load_roster()`` defaults to bg0001, so the mob driven here is
  "Fighting Fish Sergeant" (0x200D); Tornado Eagle (0x201F) lives in
  Bg0002.  The shape measured is the emitter's, not that run's.
"""

from pathlib import Path
import random
import struct
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_death, mob_loot
from pirateforce_foundation.field_mobs import load_roster
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_death import DeathRecord
from pirateforce_foundation.mob_loot import (
    DROP_ENVELOPE_PIN,
    DROP_ENVELOPE_SIZE,
    DROP_FRAME_HEADER_SIZE,
    DROP_FRAME_SIZE,
    DROP_KEY_BASE,
    DROP_PC_SIZE,
    RUNTIME_DERIVED_BIT_GROUND_LIST,
    drop_element,
    drop_frames,
    place_drops,
    roll_drops,
)


KILLER = 0x750059

# Where the envelope keeps the two fields this file reads.  Both are offsets
# into the composed pc and both are checked against a composed frame below,
# never against another constant in this file.
DERIVED_MASK_VALUE_OFFSET = 13         # the u8 after the second 0x0B tag
ELEMENT_COUNT_OFFSET = 15              # the u16 of the trailing 0x12 record

# Written here as literals so a round that edits mob_loot's own pin moves
# the module AWAY from this file instead of moving both together.
GROUND_PC_BYTES = 44
GROUND_FRAME_BYTES = 54
GROUND_ELEMENT_BYTES = GROUND_PC_BYTES - 17


class MultiDropEmissionShapeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(ROOT / "current/pf_login_game_server_v141.py")
        cls.roster = load_roster()
        cls.mob = cls.roster[0]

    def _multi_drop_kill(self, seed=3, minimum=2, attempts=500):
        """Roll until one kill drops at least ``minimum`` objects.

        Bounded, not ``while True``: a regenerated table that made this
        impossible would HANG the suite instead of failing it.
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
            "place_drops returned fewer objects than the roll produced; "
            "there is no longer a multi-drop kill here to measure")
        return drops

    def _census_pc(self, count):
        """One census collection carrying ``count`` corpse entries."""
        mobs = self.roster[:count]
        self.assertEqual(
            len(mobs), count,
            "the bg0001 roster is too small to compose a %d-entry census"
            % count)
        entries = [
            mob_death.death_actor_entry(self.legacy, mob, death_timer=20.0)
            for mob in mobs
        ]
        pc, _frame = self.legacy.make_runtime_remote_actors(entries)
        return pc

    # -- the measurement ---------------------------------------------------
    def test_each_drop_travels_as_its_own_collection_of_exactly_one(self):
        """N drops -> N collections, each count=1 with a ONE-element payload.

        The count byte alone would not be enough: a count of one in front of
        a concatenated payload is a different defect, and an earlier draft
        of this test passed on exactly that.  So the payload LENGTH is
        asserted against a literal element width written in this file, which
        is what makes the count meaningful.
        """
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        self.assertEqual(len(frames), len(drops))
        self.assertGreaterEqual(
            len(frames), 2,
            "this test is about what the SECOND collection contains; with "
            "one frame the assertions below are vacuous")
        for index, (pc, _frame) in enumerate(frames):
            self.assertEqual(
                struct.unpack("<H", pc[ELEMENT_COUNT_OFFSET:
                                       ELEMENT_COUNT_OFFSET + 2])[0],
                1,
                "collection %d does not declare a count of one" % index)
            self.assertEqual(
                len(pc), GROUND_PC_BYTES,
                "collection %d is not the pinned 44-byte pc" % index)
            self.assertEqual(
                len(pc) - DROP_ENVELOPE_SIZE, GROUND_ELEMENT_BYTES,
                "collection %d carries a payload that is not exactly one "
                "element wide, so its count of one is a lie" % index)

    def test_no_frame_of_a_multi_drop_kill_carries_another_drops_element(self):
        """The omission is by CONTENT, not only by the count field."""
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        elements = [drop_element(self.legacy, drop) for drop in drops]
        self.assertEqual(
            len(set(elements)), len(elements),
            "the drops composed to identical element bytes; the containment "
            "assertion below would then pass for the wrong reason")
        for index, (pc, _frame) in enumerate(frames):
            self.assertEqual(pc[DROP_ENVELOPE_SIZE:], elements[index])
            for other, element in enumerate(elements):
                if other == index:
                    continue
                self.assertNotIn(
                    element, pc,
                    "collection %d carries drop %d's element too" % (
                        index, other))

    def test_the_ground_bit_and_the_census_bit_are_read_off_real_frames(self):
        """Both composers are RUN, and their derived-mask bytes compared.

        The earlier draft of this test compared two literals typed eleven
        lines apart in this file and would have stayed green while the
        census moved onto the ground bit -- pf-adversary reproduced exactly
        that.  This version composes a real census collection through
        ``make_runtime_remote_actors`` and a real drop collection through
        ``drop_frames``, and reads the byte out of each.
        """
        drops = self._multi_drop_kill()
        ground_pc, _frame = drop_frames(self.legacy, drops)[0]
        census_pc = self._census_pc(1)

        ground_bit = ground_pc[DERIVED_MASK_VALUE_OFFSET]
        census_bit = census_pc[DERIVED_MASK_VALUE_OFFSET]

        self.assertEqual(ground_bit, RUNTIME_DERIVED_BIT_GROUND_LIST)
        self.assertEqual(ground_bit, 0x08)
        self.assertEqual(census_bit, 0x02)
        self.assertNotEqual(
            ground_bit, census_bit,
            "the census and the ground drops now travel on the SAME derived "
            "bit.  They are one list, and every sentence this lane has "
            "written about them being independent is void")

    def test_the_same_envelope_carries_many_elements_on_the_census_bit(self):
        """The sibling list does what the ground list refuses to do.

        ``drop_frames`` justifies one-element-per-frame with the V43
        ErrorData=28317 measurement on "a combined multi-record derived-mask
        collection".  This test measures that the SAME envelope, one derived
        bit over, ships N elements in ONE collection -- and that path is the
        production census that has carried 115 actors to real clients.  So
        the V43 lesson is not a property of the envelope; whether it is a
        property of the 0x08 CONSUMER is RE-129.
        """
        for count in (2, 5):
            census_pc = self._census_pc(count)
            self.assertEqual(
                census_pc[DERIVED_MASK_VALUE_OFFSET], 0x02)
            self.assertEqual(
                struct.unpack("<H", census_pc[ELEMENT_COUNT_OFFSET:
                                              ELEMENT_COUNT_OFFSET + 2])[0],
                count,
                "the census collection no longer declares its own element "
                "count; the contrast this file draws has moved")
        # And the two envelopes are otherwise the same shape: same message
        # id, same zero id, same version, same inherited mask.  If they ever
        # stop matching, the contrast is between two different things and
        # the argument in this file needs redoing.
        self.assertEqual(
            self._census_pc(2)[:10], DROP_ENVELOPE_PIN[:10],
            "the census and ground envelopes no longer share a header, so "
            "'the same envelope' is no longer an accurate description")

    def test_the_pinned_envelope_is_the_bytes_this_file_was_written_against(
            self):
        """The one assertion that cannot be shadowed by the module's guards.

        Every other test here reaches mob_loot's composer, which refuses a
        drifted shape before this file gets a word in.  This one compares
        the CONSTANT against a literal written here.
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
            "the ground envelope moved.  If that was deliberate, this "
            "file's reading has to be re-argued, not re-pinned")
        self.assertEqual(DROP_ENVELOPE_SIZE, 17)
        self.assertEqual(DROP_PC_SIZE, GROUND_PC_BYTES)
        self.assertEqual(DROP_FRAME_SIZE, GROUND_FRAME_BYTES)
        self.assertEqual(
            DROP_FRAME_HEADER_SIZE, GROUND_FRAME_BYTES - GROUND_PC_BYTES)

    # -- the file's own honesty guard --------------------------------------
    def test_the_other_candidates_are_still_recorded_in_the_module(self):
        """The competing explanations must stay visible next to this finding.

        If a later round deletes or widens the measured label lifetime, or
        loses the item-table negative, this file's nonclaim ("four
        candidates, none separated") stops being true and somebody will
        read the emission shape as a settled cause.  Then this goes red.
        """
        low, high = mob_loot.GROUND_LABEL_OBSERVED_LIFETIME_SECONDS
        self.assertLess(high, 1.0)
        self.assertGreater(low, 0.0)
        self.assertTrue(mob_loot.NO_MODEL_UNDER_THE_LABEL_THAT_WAS_SEEN)
        self.assertTrue(
            any("2600001" in line for line in mob_loot.MOB_LOOT_NONCLAIMS),
            "the item-table negative (2600001 drew no label) has left the "
            "module's nonclaims; candidate (3) in this file's docstring no "
            "longer has a source")


if __name__ == "__main__":
    unittest.main()
