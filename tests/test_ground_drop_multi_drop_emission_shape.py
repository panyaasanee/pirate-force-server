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

* ~~the ground list (derived bit 0x08) emits N drops as N SEPARATE
  collections, each declaring a count of ONE~~ -- TRUE WHEN THIS FILE WAS
  WRITTEN, FALSE NOW, and struck rather than deleted because the contrast
  below is why the question got asked.  Round ``zxnwtd`` changed it on
  ``RE-130`` (DONE/PASS 2026-08-28T20:18+07:00): the ground list now emits
  N drops as ONE collection declaring a count of N, like its sibling,
  because the consumer ERASES every key a nonempty generation omits
  (``0x005E0D40`` at ``0x006AFF84``/``0x006B0368``) and the old shape
  therefore left only the LAST drop of a multi-drop kill in the client's
  keyed tree.  The tests below now measure the NEW shape and the
  ``kfs01z``-era ones that asserted the old one are struck in place;
* the census list (derived bit 0x02), through the SAME
  ``GSCN_RunTimeProtocolRes`` envelope, puts N actors in ONE collection
  with a count of N.

THE ONLY CLIENT-OBSERVABLE NUMBER THIS FILE MAY CITE IS 97.  GT-121 is a
PASS with OBSERVER_CONFIRMED 2026-08-28T09:2x: a 97-element single
collection (``WORLD_CENSUS assembled=97/97``) reached a real client and the
owner reported every NPC standing there on arrival.  ~~"115 actors, to real
clients, accepted"~~ IS STRUCK AND MUST NOT BE WRITTEN: GT-078's 115/115 is
a WIRE-layer count on a ticket the owner REJECTED on the identity layer
(the ticket forbids closing it as PASS), and GT-076 -- the ticket whose
entire question is how many actors a client takes in ONE collection -- is
BLOCKED and has never run.  Its 115 row is a pre-declared outcome table,
not a result.  An earlier draft of this docstring cited 115 as accepted;
that is the same wire-number-wearing-a-client-verb move this file was
rewritten to remove.

So "a combined multi-record derived-mask collection is the one shape a real
client has already rejected" (``drop_frames``'s own justification, from the
V43 ErrorData=28317 note) is NOT a property of this envelope in general.
Its sibling ships a 97-element collection that a client demonstrably drew.
~~Whether the 0x08 CONSUMER can take the same treatment is RE-130's
question~~ -- RE-130 ANSWERED IT: the codec loop reads its count from the
list object at ``+0x2C`` and takes more than one (span ``[0x006AF970,
0x006B03E3)``, sha e5eb9e15..).  What is still open, and is now ``GT-131``
rather than an RE ticket, is whether a client DRAWS the labels it accepts.
This file kept the contrast precise enough for the question to be answered
instead of guessed at, and that is what it was for.

AND THE V43 NUMBER DOES NOT MEAN WHAT drop_frames SAYS IT MEANS.  This is
not this file's finding -- ``world_population.py:105-115`` settled it on
2026-08-18 and this file only cites it: 28317 = 0x6E9D =
GSCN_RunTimeProtocolRes, the client echoing the CLASS ID of whichever
envelope failed to deserialize.  "It is a parse-failure echo, not a count
report", and V43's six actors were on the 0x02 REMOTE-ACTOR list -- the
very list offered above as the counter-example.  So the V43 note is an
interval, not a ceiling, and several modules still describe it as a
rejection of multi-record collections.  Correcting that prose is lane work,
not an RE question; it is named in RE-130 as such.

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
* ~~NOT CLAIMED: that the 0x08 list is replace-by-omission.  RE-092 settled
  that for the 0x02 list ONLY.~~  IT IS NOW CLAIMED, AND NOT BY THIS FILE:
  ``RE-130`` closed DONE/PASS on 2026-08-28T20:18+07:00 with the spans --
  a nonempty generation reconciles the keyed tree and erases every key it
  omits (``0x005E0D40`` at ``0x006AFF84``/``0x006B0368``), and the element
  key is the wire's ``u32 tag 0x14`` at element ``+0x10`` with no
  transform.  That is a STATIC fact about the deserialiser, still not a
  statement about what gets drawn.  ~~"GT-045's own evidence leans the other
  way -- two elements 42 ms apart and a label was still seen"~~ IS
  DOWNGRADED to a conditional: that reading needs BOTH that the label seen
  was the FIRST element (contested in-repo -- mob_loot.py:57 says it was
  NEAR, ground_loot_nameprop_hypothesis.py:103 says the observer could not
  tell which element it belonged to) AND that a label's life is bound to
  its element's membership in the list at all (nobody knows; it is
  RE-130's first objective).  If labels are one-shot and self-expiring,
  seeing one is evidence about omission in neither direction.
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
* NOT CLAIMED: that EVERY census emission carries count=N.  It does not.
  ``runtime.py:4017`` degrades to a ONE-entry 0x02 frame by design when the
  population anchor is missing or mismatched (event
  ``mob_combat_bar_census_compose_skipped_no_population_anchor``), which a
  client swinging before its first position report can reach.  So "the
  census puts N in one collection" is true of the normal path and false of
  a named, reachable branch, and this file -- which imports neither
  ``runtime`` nor ``world_population`` -- cannot see that branch move.  If
  a later round makes the degrade path the default, every test here stays
  green while the contrast the file draws dies.
* NOT CLAIMED: that ``_census_pc`` composes what GT-121 sent.  It builds a
  DEATH census (``mob_death.death_actor_entry``); GT-121's was the
  world/arrival census, a different entry payload.  Same envelope, same
  count field -- which is the whole of what is asserted -- but the
  entry bytes are not that run's.
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
        # ANCHOR THE OFFSETS BEFORE ANY CALLER READS THEM.  The two offsets
        # this file indexes with are pinned to a literal for the GROUND pc
        # (test 5), but nothing pinned them on the CENSUS side, and
        # pf-adversary showed what that costs: shorten the census envelope
        # by one tag-pair and byte 13 becomes the count's low byte, so a
        # count=2 collection reads 0x02 there and "the census bit is 0x02"
        # passes for entirely the wrong reason.  Checking that both 0x0B
        # tags are where this file thinks they are makes the index mean
        # what its name says.
        self.assertEqual(
            pc[10], 0x0B,
            "the census inherited-mask tag moved; every offset this file "
            "indexes the census pc with is now pointing at something else")
        self.assertEqual(
            pc[12], 0x0B,
            "the census derived-mask tag moved; byte 13 is no longer the "
            "derived mask and this file's reads are meaningless")
        return pc

    # -- the measurement ---------------------------------------------------
    def test_a_multi_drop_kill_travels_as_one_collection_of_exactly_n(self):
        """~~N drops -> N collections~~ -> N drops -> ONE collection of N.

        Struck and inverted in round ``zxnwtd`` on ``RE-130``.  The reason
        the old assertion is not merely re-pointed: it described the DEFECT.
        Under replacement-by-omission, N collections of one leave one drop.

        The count field alone is still not enough -- a count of N in front
        of a one-element payload is the mirror of the defect the previous
        version of this test guarded against -- so the payload LENGTH is
        still asserted against the element width written in this file.
        """
        drops = self._multi_drop_kill()
        frames = drop_frames(self.legacy, drops)
        self.assertEqual(
            len(frames), 1,
            "a multi-drop kill must be ONE generation; %d of them erase "
            "each other's keys" % len(frames))
        self.assertGreaterEqual(
            len(drops), 2,
            "this test is about a collection carrying MORE than one "
            "element; with one drop the assertions below are vacuous")
        pc, _frame = frames[0]
        self.assertEqual(
            struct.unpack("<H", pc[ELEMENT_COUNT_OFFSET:
                                   ELEMENT_COUNT_OFFSET + 2])[0],
            len(drops),
            "the collection does not declare the number of drops it carries")
        self.assertEqual(
            len(pc), DROP_ENVELOPE_SIZE + GROUND_ELEMENT_BYTES * len(drops),
            "the collection's payload is not exactly %d elements wide, so "
            "its count is a lie" % len(drops))

    def test_the_one_collection_carries_every_drops_element_exactly_once(self):
        """Presence by CONTENT, not only by the count field."""
        drops = self._multi_drop_kill()
        (pc, frame), = drop_frames(self.legacy, drops)
        elements = [drop_element(self.legacy, drop) for drop in drops]
        self.assertEqual(
            len(set(elements)), len(elements),
            "the drops composed to identical element bytes; the containment "
            "assertion below would then pass for the wrong reason")
        self.assertEqual(pc[DROP_ENVELOPE_SIZE:], b"".join(elements))
        for index, element in enumerate(elements):
            self.assertEqual(
                pc.count(element), 1,
                "drop %d's element appears %d times in the collection"
                % (index, pc.count(element)))
            self.assertIn(
                element, frame,
                "drop %d's element did not survive framing" % index)

    def test_a_one_drop_kill_is_byte_for_byte_what_gt045_sent(self):
        """The change must not move the only shape a client has taken.

        This is the guard on the round-``zxnwtd`` change: whatever the wide
        generation looks like, a kill that rolled ONE object still composes
        the 44-byte pc and 54-byte frame of GT-045, and the count record in
        it still reads one.
        """
        drops = self._multi_drop_kill()
        (pc, frame), = drop_frames(self.legacy, drops[:1])
        self.assertEqual(len(pc), GROUND_PC_BYTES)
        self.assertEqual(len(frame), GROUND_FRAME_BYTES)
        self.assertEqual(pc[:DROP_ENVELOPE_SIZE], DROP_ENVELOPE_PIN)
        self.assertEqual(
            struct.unpack("<H", pc[ELEMENT_COUNT_OFFSET:
                                   ELEMENT_COUNT_OFFSET + 2])[0], 1)

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

        ~~``drop_frames`` justifies one-element-per-frame with the V43
        ErrorData=28317 note~~ -- it no longer does either thing (round
        ``zxnwtd``).  This test still measures that the SAME envelope, one
        derived bit over, ships N elements in ONE collection, and it is now
        the SIDE the ground list also emits on.  The client-observable
        number that licenses the contrast is 97 (GT-121, PASS) -- NOT 115,
        see the module docstring.  And per world_population.py:105-115 the
        V43 number is a parse-failure echo, not a count report, measured on
        the 0x02 list itself.  Whether multi-element is DRAWN by the 0x08
        consumer is GT-131; that its codec ACCEPTS it is RE-130, closed.
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
