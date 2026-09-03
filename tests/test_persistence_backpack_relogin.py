"""LANE-DB round dskm1o -- COO ``0951``: does the row a pickup writes come
back at the NEXT login through the real production entry point
(``FoundationSession.select_and_start``), and does it ride the actual wire
bytes that entry point composes -- not ``store.get_backpack`` called
directly, and not raw SQL?

WHAT ALREADY EXISTED before this file, and why neither answers COO's
question by itself:

* ``tests/test_mob_pickup_persist.py`` (LANE-B, round ``uq2lxw``) proves a
  pickup's row survives a relog -- but its relog is ``store.close_session``
  / ``store.open_session`` / ``store.select_character`` called directly, and
  its read-back is ``store.get_backpack``.  ``FoundationSession`` -- the
  class ``select_and_start`` actually lives on, and the only thing that
  turns a bag into wire bytes -- never appears in that file.
* ``tests/test_item_lifecycle.py`` (chief) drives a reconnect through the
  real state machine and checks the wire, for a DIFFERENT write: a v111
  stack merge (``store.apply_v111_stack_merge``), not a pickup.

Nobody had put a PICKUP's row through ``FoundationSession.select_and_start``
after a close/reopen and looked at the bytes it hands the client.  That is
the one thing this file measures, and only that.

THE THIRD TEST closes a gap ``pf-adversary`` named in this round's review:
the first two tests relog through the SAME ``SQLiteStore`` object ``setUp``
builds once, which proves the row survives a session close/reopen but not
that it survives independently of that one long-lived object.  The third
test reopens with a brand new ``SQLiteStore`` pointed at the same file --
the shape an actual server restart has -- so persistence is checked against
the file on disk, not against anything the first store instance happened to
be holding in memory.

WHAT THIS FILE DOES NOT PROVE.  It is not client-observable: no window
opens, no click happens, and (as LANE-B's own file documents) ``runtime.py``
still has no inbound pickup opcode, so nothing here is caused by a player.
The write half is driven exactly as LANE-B's dispatch line does it
(``mob_pickup_persist.pickup_and_persist``), read only, never edited by this
round.
"""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import mob_loot, mob_pickup, mob_pickup_persist  # noqa: E402
from pirateforce_foundation.inventory import (  # noqa: E402
    INITIAL_BACKPACK,
    make_backpack_attr,
)
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy  # noqa: E402
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.mob_loot import DropLedger, DropLedgerCell  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

ITEM = 2400046           # the roster's most common drop (matches LANE-B's fixture)
MOB = 0x2068
KILLER = 0x750059
SCENE = "bg0001"
DROP_AT = (1000.0, 20.0, 3000.0)


class PickupSurvivesRelogThroughSelectAndStartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = load_legacy(LEGACY_PATH)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate()
        self.projector = LegacyProjector(self.legacy)
        self.home = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.home,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        self.login_name = "backpack-relog-dskm1o"

    def _login(self):
        return FoundationSession(self.lifecycle, self.projector, self.login_name)

    def _a_ground_cell(self):
        # The claim in pickup_and_persist() below is made AT this exact
        # (x, y, z) -- the same tuple the drop itself carries -- so the
        # radius check passes by construction and is not what this fixture
        # is testing (pf-adversary, this round: an earlier comment here
        # implied the distance was measured against where the character
        # spawned, which it is not).  What the three far-apart DROP_AT
        # values still guard is a swapped x/y/z argument anywhere between
        # here and the store, same reasoning as LANE-B's own fixture note.
        drop = mob_loot.GroundDrop(
            mob_loot.DROP_KEY_BASE, ITEM, 1,
            mob_loot.as_wire_float(DROP_AT[0]),
            mob_loot.as_wire_float(DROP_AT[1]),
            mob_loot.as_wire_float(DROP_AT[2]),
            MOB, KILLER, SCENE,
        )
        return DropLedgerCell(
            DropLedger((drop,), 1, drop.drop_key + 1, ()), scene=SCENE)

    def test_a_pickup_rides_the_wire_select_and_start_composes_after_a_relog(self):
        first = self._login()
        # "test01" matches the name already embedded in the preset wire --
        # tests/test_item_lifecycle.py's own preset() helper depends on the
        # same fact, so this is not a new assumption.
        character, _ = first.create("test01", self.legacy.get_preset_actor_wire())
        selected, (start_pc0, _start_frame0) = first.select_and_start(
            character.selector)
        self.assertEqual(first.backpack, INITIAL_BACKPACK)
        # S0: the fresh login's own wire carries the four-item stub, not yet
        # anything this round writes.
        self.assertEqual(
            start_pc0.count(self.legacy.make_backpack_attr_four_items()), 1)

        # The write half, run exactly as LANE-B's dispatch line runs it --
        # this round reads that module, never edits it.
        registry = mob_pickup.BagCellRegistry()
        cell = registry.claim(
            selected.id,
            first.lifecycle.store.get_backpack(first.session_id, selected.id),
            first.lifecycle.store.backpack_issued_through(
                first.session_id, selected.id),
        )
        result = mob_pickup_persist.pickup_and_persist(
            first.lifecycle.store, first.session_id, selected.id, cell,
            self._a_ground_cell(), self.legacy, KILLER,
            DROP_AT[0], DROP_AT[1], DROP_AT[2], mob_loot.DROP_KEY_BASE, 0,
            echo=False,
        )
        self.assertTrue(result.agrees)
        # A relog: this session's own bag cell is released (the same way
        # LANE-B's _relog() helper documents a logout releasing it), and the
        # connection closes without a position write -- backpack persistence
        # does not depend on where the character stood.
        registry.release(selected.id)
        first.close_connection()

        second = self._login()
        _selected2, (start_pc2, _start_frame2) = second.select_and_start(
            character.selector)

        # 1. the BackpackState the NEW login's own select_and_start composed
        #    carries the picked-up item -- this is `self.backpack` as
        #    session.py sets it, not a value this test asked the store for.
        self.assertIn(result.outcome.item, second.backpack.items)
        self.assertEqual(len(second.backpack.items), len(INITIAL_BACKPACK.items) + 1)

        # 2. and the WIRE BYTES that login actually sends carry that exact
        #    bag: the frame a client would parse, not "a Python object was
        #    loaded".  select_and_start's fallback to the four-item stub
        #    (legacy_bridge.py: `backpack=None`) never fires when this path
        #    works, so the two assertions below are the same fact checked
        #    from both ends.
        expected_wire = make_backpack_attr(self.legacy, second.backpack)
        self.assertEqual(start_pc2.count(expected_wire), 1)
        self.assertEqual(
            start_pc2.count(self.legacy.make_backpack_attr_four_items()), 0,
            "the second login's frame still carries the pre-pickup stub",
        )

    def test_without_a_pickup_a_second_login_still_carries_the_stub(self):
        """The control this file's headline test needs to mean anything.

        If ``select_and_start`` composed the four-item stub on EVERY login
        regardless of what the database holds, the test above would pass for
        the wrong reason.  This proves the stub is what an UNCHANGED
        character's second login actually carries, so the item's appearance
        above is the pickup's doing and not always-true noise.
        """
        first = self._login()
        character, _ = first.create("test01", self.legacy.get_preset_actor_wire())
        first.select_and_start(character.selector)
        first.close_connection()

        second = self._login()
        _selected2, (start_pc2, _start_frame2) = second.select_and_start(
            character.selector)
        self.assertEqual(second.backpack, INITIAL_BACKPACK)
        self.assertEqual(
            start_pc2.count(self.legacy.make_backpack_attr_four_items()), 1)

    def test_the_row_survives_a_fresh_store_instance_not_just_a_fresh_session(self):
        """Closes the gap pf-adversary named in this round's review.

        Every other test in this file reopens a session through
        ``self.lifecycle``/``self.store`` built once in ``setUp`` -- a real
        relog, but still the SAME ``SQLiteStore`` Python object underneath
        both logins.  That leaves one thing unproven: that the row's
        survival is a fact about THE FILE ON DISK, and not an artifact of
        one long-lived object's own state (a cache this round did not know
        to look for, say).  A real server restart constructs a brand new
        ``SQLiteStore`` against the same path, so this test does exactly
        that instead of reusing ``self.store``/``self.lifecycle``.
        """
        first = self._login()
        character, _ = first.create("test01", self.legacy.get_preset_actor_wire())
        selected, _ = first.select_and_start(character.selector)
        registry = mob_pickup.BagCellRegistry()
        cell = registry.claim(
            selected.id,
            first.lifecycle.store.get_backpack(first.session_id, selected.id),
            first.lifecycle.store.backpack_issued_through(
                first.session_id, selected.id),
        )
        result = mob_pickup_persist.pickup_and_persist(
            first.lifecycle.store, first.session_id, selected.id, cell,
            self._a_ground_cell(), self.legacy, KILLER,
            DROP_AT[0], DROP_AT[1], DROP_AT[2], mob_loot.DROP_KEY_BASE, 0,
            echo=False,
        )
        registry.release(selected.id)
        first.close_connection()

        # A NEW SQLiteStore against the SAME file, a new CharacterLifecycle
        # wrapping it, and a new FoundationSession -- nothing here is the
        # object that performed the write.
        reopened_store = SQLiteStore(self.db_path, ROOT / "migrations")
        reopened_store.migrate()
        reopened_lifecycle = CharacterLifecycle(
            reopened_store, self.home,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        third = FoundationSession(
            reopened_lifecycle, self.projector, self.login_name)
        _selected3, (start_pc3, _start_frame3) = third.select_and_start(
            character.selector)

        self.assertIn(result.outcome.item, third.backpack.items)
        expected_wire = make_backpack_attr(self.legacy, third.backpack)
        self.assertEqual(start_pc3.count(expected_wire), 1)


if __name__ == "__main__":
    unittest.main()
