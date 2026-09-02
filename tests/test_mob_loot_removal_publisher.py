"""LANE-B round lh21ua: the removal publisher COO-DECISION 0253 asked for.

What this file pins, and why each half is here.

``DropLedgerCell.frames_after_a_row_left`` is the answer to "who tells the
CLIENT that the object a player just picked up is gone".  It is not a new wire
message: ``RE-082`` (closed PASS 2026-08-26) measured that a nonempty
generation erases every key it OMITS, so the removal of one key is the
publication of the others.  The tests here drive the real frozen v141
serializer and read the bytes that come out -- an element carrying the taken
key must not be in them, and an element carrying every remaining key must.

The second half is the hole.  A scene whose LAST row was taken has no nonempty
generation left to send, and RE-082 measured the empty one as a client no-op,
so this lane publishes NOTHING there and says so by name.  ``RE-208`` is open
on whether any message removes one object at a time; until it answers, the
last label keeps today's behaviour.  ``TheLastObjectIsHeldAndSaysSo`` is what
goes red the day somebody quietly starts sending an empty generation instead.
"""

from pathlib import Path
import io
import sys
import unittest
from contextlib import redirect_stdout

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_loot
from pirateforce_foundation.legacy_bridge import load_legacy
from pirateforce_foundation.mob_loot import (
    DropLedger,
    DropLedgerCell,
    GroundDrop,
    MobLootContractError,
    REFUSE_NO_SCENE_TO_PUBLISH,
    REFUSE_ROW_IS_STILL_ON_THE_GROUND,
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
)

V141 = ROOT / "current/pf_login_game_server_v141.py"

ITEM = 2400046
MOB = 0x2068
KILLER = 0x750059
SCENE = "bg0001"
ELSEWHERE = "bg0015"


def a_drop(key_offset=0, scene=SCENE, x=1000.0):
    return GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, 1,
        mob_loot.as_wire_float(x),
        mob_loot.as_wire_float(20.0),
        mob_loot.as_wire_float(3000.0),
        MOB, KILLER, scene,
    )


def a_cell(*drops, scene=SCENE):
    issued = mob_loot.DROP_KEY_BASE
    for drop in drops:
        if drop.drop_key + 1 > issued:
            issued = drop.drop_key + 1
    return DropLedgerCell(
        DropLedger(tuple(sorted(drops, key=lambda d: d.drop_key)), 1, issued,
                   ()),
        scene=scene)


class LegacyCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(V141)

    def keys_on_the_wire(self, frames):
        """Every drop key present in the composed bytes, read back out.

        A SECOND DERIVATION, not a paraphrase of the composer: it scans the
        frames for the element key record (tag, then the key little-endian)
        rather than asking the module which keys it put in.  A composer that
        published the wrong rows cannot answer this test with its own opinion.
        """
        seen = []
        for pc, _frame in frames:
            cursor = 0
            while True:
                index = pc.find(bytes([mob_loot.ELEMENT_KEY_TAG]), cursor)
                if index < 0 or index + 5 > len(pc):
                    break
                key = int.from_bytes(pc[index + 1:index + 5], "little")
                if mob_loot.DROP_KEY_BASE <= key < mob_loot.DROP_KEY_LIMIT:
                    seen.append(key)
                cursor = index + 1
        return seen


class TheRemovalIsThePublicationOfWhatIsLeft(LegacyCase):
    """The headline: take a row, publish the rest, and the key is gone."""

    def test_the_taken_key_is_absent_and_every_survivor_is_present(self):
        cell = a_cell(a_drop(0), a_drop(1), a_drop(2))
        taken = cell.take(mob_loot.DROP_KEY_BASE + 1).drop_key
        rows_left, frames = cell.frames_after_a_row_left(self.legacy, taken)
        self.assertEqual(rows_left, 2)
        self.assertTrue(frames, "two rows remained and nothing was published")
        keys = self.keys_on_the_wire(frames)
        self.assertNotIn(
            taken, keys,
            "the generation carries the key it is supposed to remove")
        self.assertEqual(
            sorted(keys),
            [mob_loot.DROP_KEY_BASE, mob_loot.DROP_KEY_BASE + 2])

    def test_the_bytes_are_the_boundary_publisher_s_bytes(self):
        """Same shape as a scene entry, not a second dialect of the same idea.

        If these two ever diverge, one of them is sending a generation the
        other lane has not pinned -- and the client has only ever been shown
        one shape.
        """
        cell = a_cell(a_drop(0), a_drop(1))
        cell.take(mob_loot.DROP_KEY_BASE + 1)
        _rows, frames = cell.frames_after_a_row_left(
            self.legacy, mob_loot.DROP_KEY_BASE + 1)
        _p, _c, _e, _x, boundary = a_cell(
            a_drop(0), scene=None).enter_scene_frames(self.legacy, SCENE)
        self.assertEqual(frames, boundary)

    def test_only_this_scene_s_rows_ride_in_it(self):
        """Way 1 (COO 0252) is not undone by a removal.

        A drop standing in the scene the player LEFT may not ride in the
        publication they receive here -- and, just as important, must not be
        counted as "still on the ground" for the refusal below.
        """
        cell = a_cell(a_drop(0), a_drop(1),
                      a_drop(2, scene=ELSEWHERE), scene=SCENE)
        cell.take(mob_loot.DROP_KEY_BASE)
        rows_left, frames = cell.frames_after_a_row_left(
            self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(rows_left, 1)
        self.assertEqual(
            self.keys_on_the_wire(frames), [mob_loot.DROP_KEY_BASE + 1])

    def test_a_row_that_expired_instead_of_being_taken_publishes_too(self):
        """The event is A ROW LEFT, not only A PICKUP.

        The lazy per-drop expiry (COO-DECISION 2026-08-29T12:41+07:00) removes
        rows during the sweep this call makes.  A caller naming such a key is
        telling the truth -- the row is not on the ground -- so it publishes
        rather than refusing.
        """
        clock = [1000.0]
        cell = DropLedgerCell(
            DropLedger((a_drop(0), a_drop(1)), 1,
                       mob_loot.DROP_KEY_BASE + 2, ()),
            scene=SCENE, clock=lambda: clock[0])
        clock[0] += mob_loot.DROP_LIFETIME_SECONDS + 1.0
        rows_left, frames = cell.frames_after_a_row_left(
            self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual((rows_left, frames), (0, ()))


class EveryRefusalHasItsOwnName(LegacyCase):

    def test_a_key_still_standing_is_refused_before_a_byte_is_composed(self):
        """The assertion that makes the call honest.

        A generation composed while the key is still there REMOVES NOTHING,
        and the caller -- which has already answered the player's click --
        would never find out.
        """
        cell = a_cell(a_drop(0), a_drop(1))
        with self.assertRaises(MobLootContractError) as caught:
            cell.frames_after_a_row_left(
                self.legacy, mob_loot.DROP_KEY_BASE + 1)
        self.assertEqual(caught.exception.args[0],
                         REFUSE_ROW_IS_STILL_ON_THE_GROUND)

    def test_a_cell_with_no_scene_refuses_rather_than_publishing_everything(
            self):
        cell = DropLedgerCell(DropLedger((), 1, mob_loot.DROP_KEY_BASE, ()))
        with self.assertRaises(MobLootContractError) as caught:
            cell.frames_after_a_row_left(self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(caught.exception.args[0], REFUSE_NO_SCENE_TO_PUBLISH)

    def test_a_key_that_is_not_an_int_or_not_a_key_is_refused_by_name(self):
        cell = a_cell(a_drop(0))
        for value, reason in (
            ("0x1", REFUSE_VALUE_NOT_INT),
            (None, REFUSE_VALUE_NOT_INT),
            (True, REFUSE_VALUE_NOT_INT),
            (-1, REFUSE_VALUE_OUT_OF_RANGE),
            (0x1_0000_0000, REFUSE_VALUE_OUT_OF_RANGE),
        ):
            with self.subTest(value=value):
                with self.assertRaises(MobLootContractError) as caught:
                    cell.frames_after_a_row_left(self.legacy, value)
                self.assertEqual(caught.exception.args[0], reason)

    def test_a_serializer_that_is_not_the_frozen_one_refuses(self):
        """The boundary publisher's own guard, inherited on purpose."""
        cell = a_cell(a_drop(0), a_drop(1))
        cell.take(mob_loot.DROP_KEY_BASE)

        class NotASerializer:
            pass

        with self.assertRaises(MobLootContractError):
            cell.frames_after_a_row_left(
                NotASerializer(), mob_loot.DROP_KEY_BASE)


class TheLastObjectIsHeldAndSaysSo(LegacyCase):
    """RE-208's hole, pinned so nobody closes it by accident."""

    def test_an_empty_scene_publishes_nothing_at_all(self):
        cell = a_cell(a_drop(0))
        cell.take(mob_loot.DROP_KEY_BASE)
        rows_left, frames = cell.frames_after_a_row_left(
            self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(rows_left, 0)
        self.assertEqual(frames, (), "an empty generation was composed; "
                                     "RE-082 measured it as a client no-op "
                                     "and RE-208 is open on what is not")

    def test_the_hole_is_named_in_the_docstring_a_reader_reaches_for(self):
        """Deleting the explanation must not be free.

        The zero return is indistinguishable from a bug unless the reason is
        written where the next reader looks.
        """
        doc = DropLedgerCell.frames_after_a_row_left.__doc__
        self.assertIn("RE-208", doc)
        self.assertIn("RE-082", doc)
        self.assertIn("LAST object", doc)


class TheTrimIsInheritedAndItsCostIsStated(LegacyCase):

    def test_a_scene_wider_than_one_frame_publishes_rather_than_raising(self):
        """A pickup in a crowded scene must not end in an exception.

        pf-adversary's D5 of round 9jrsei is the precedent: the boundary
        publisher raised ``generation_too_wide_to_frame`` out of a scene
        transition until it trimmed.  The same trim is inherited here, and
        this drives it with more rows than one frame can carry.
        """
        cap = (
            mob_loot.DROP_MAX_ELEMENTS_PER_FRAME_WITH_MODEL_TYPE
            if mob_loot.DROP_MODEL_TYPE_FIELD_ENABLED
            else mob_loot.DROP_MAX_ELEMENTS_PER_FRAME
        )
        drops = tuple(a_drop(offset) for offset in range(cap + 2))
        cell = a_cell(*drops)
        cell.take(mob_loot.DROP_KEY_BASE)
        rows_left, frames = cell.frames_after_a_row_left(
            self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(rows_left, cap + 1)
        self.assertTrue(frames)
        keys = self.keys_on_the_wire(frames)
        self.assertEqual(len(keys), cap, "the trim did not hold the cap")
        self.assertNotIn(mob_loot.DROP_KEY_BASE, keys)
        self.assertNotIn(
            mob_loot.DROP_KEY_BASE + cap + 1, keys,
            "the trim keeps the OLDEST rows; the newest is the one dropped")

    def test_the_cost_of_the_trim_is_written_down_where_it_happens(self):
        doc = DropLedgerCell.frames_after_a_row_left.__doc__
        self.assertIn("RE-130", doc)
        self.assertIn("OLDEST", doc)


class NothingHereDeletesARow(LegacyCase):
    """COO-DECISION 2026-09-02T02:53+07:00, executed rather than promised."""

    def test_publishing_removes_nothing_from_the_ledger(self):
        cell = a_cell(a_drop(0), a_drop(1), a_drop(2, scene=ELSEWHERE))
        cell.take(mob_loot.DROP_KEY_BASE)
        before = tuple(row.drop_key for row in cell.ledger.drops)
        cell.frames_after_a_row_left(self.legacy, mob_loot.DROP_KEY_BASE)
        cell.frames_after_a_row_left(self.legacy, mob_loot.DROP_KEY_BASE)
        after = tuple(row.drop_key for row in cell.ledger.drops)
        self.assertEqual(before, after)

    def test_it_moves_neither_generation_nor_the_key_high_water_mark(self):
        cell = a_cell(a_drop(0), a_drop(1))
        cell.take(mob_loot.DROP_KEY_BASE)
        generation = cell.ledger.generation
        issued = cell.ledger.issued_through
        cell.frames_after_a_row_left(self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(cell.ledger.generation, generation)
        self.assertEqual(cell.ledger.issued_through, issued)

    def test_it_prints_nothing_of_its_own(self):
        """The cell composes; the caller decides what an operator sees.

        Same rule as every other publication path here -- a module that
        printed from inside the compose would print from a test, from an
        experiment and from the server alike.
        """
        cell = a_cell(a_drop(0), a_drop(1))
        cell.take(mob_loot.DROP_KEY_BASE)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            cell.frames_after_a_row_left(self.legacy, mob_loot.DROP_KEY_BASE)
        self.assertEqual(buffer.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
