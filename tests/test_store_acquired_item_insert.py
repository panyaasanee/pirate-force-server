"""STORE-INSERT-001: a picked-up row reaches the database, and the identity
counter moves with it -- in one transaction or not at all.

WHAT THIS FILE IS THE EVIDENCE FOR.  Until this round ``store.py`` had exactly
one backpack INSERT (``_insert_initial_backpack``, at character create) and
nothing anywhere advanced ``character_backpacks.next_item_identity``; the item
lane could only LOG the row it would have written
(``MOB_PICKUP_ROW_WOULD_INSERT`` -- WOULD, and the token says so).  So the
wire/DB half of M5's loop -- pick an item up, log out, log back in, it is
still in the bag -- had no write to prove.  This file proves that half and
only that half.

THE BAGS ARE NOT ASSEMBLED HERE.  Every acquired row in this file is the
return value of the real ``mob_pickup.place_in_bag`` fed a real
``mob_loot.GroundDrop``, and every read-back goes through the real
``store.get_backpack``.  A test that hand-built the row it then writes would
prove the store agrees with this file's idea of a pickup, not that a pickup
survives a database.

WHAT THIS FILE DOES NOT PROVE.  There is still no call site: ``runtime.py``
does not call ``mob_pickup.dispatch_pickup_request`` (that is ``GT-124``), so
nothing here says a player clicking a label gets a row.  Nothing here is
client-observable evidence either; the relog in this file is a session close
and reopen against the store, not a client.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import bag_admission, mob_loot, mob_pickup  # noqa: E402
from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.inventory import (  # noqa: E402
    BackpackState,
    INITIAL_BACKPACK,
    ItemAttrState,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

ITEM = 2400046  # the roster's most common drop, as tests/test_mob_pickup.py uses
MOB = 0x2068
KILLER = 0x750059


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


def a_drop(key_offset=0, quantity=1):
    return mob_loot.GroundDrop(
        mob_loot.DROP_KEY_BASE + key_offset, ITEM, quantity,
        mob_loot.as_wire_float(10.0),
        mob_loot.as_wire_float(20.0),
        mob_loot.as_wire_float(30.0),
        MOB, KILLER,
    )


class StoreAcquiredItemInsertTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("store-insert-001")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "StoreInsertOne", "storeinsertone",
            "fingerprint-store-insert-001", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    # ----- harness -----------------------------------------------------

    def _column(self):
        """The raw counter, read outside the store's own accessors."""
        with sqlite3.connect(self.path) as db:
            return int(db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?",
                (self.character.id,),
            ).fetchone()[0])

    def _set_column(self, value):
        with sqlite3.connect(self.path) as db:
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (value, self.character.id),
            )

    def _rows(self):
        with sqlite3.connect(self.path) as db:
            return [
                tuple(row) for row in db.execute(
                    "SELECT item_identity,template_id,quantity,slot "
                    "FROM character_backpack_items WHERE character_id=? "
                    "ORDER BY item_identity",
                    (self.character.id,),
                )
            ]

    def _mint(self, key_offset=0, quantity=1):
        """One acquired row, minted the way the item lane mints it."""
        bag = self.store.get_backpack(self.sid, self.character.id)
        issued = self.store.backpack_issued_through(self.sid, self.character.id)
        _, item = mob_pickup.place_in_bag(bag, a_drop(key_offset, quantity), issued)
        return item

    def _relog(self):
        """Close this session and open a new one on the same character."""
        self.store.close_session(self.sid)
        self.sid = self.store.open_session(self.account_id)
        self.store.select_character(self.sid, self.character.selector)

    # ----- the counter's own arithmetic --------------------------------

    def test_a_new_character_counter_comes_from_the_initial_bag(self):
        # Pinned against INITIAL_BACKPACK rather than against the literal 5,
        # which is migration 005's ADD COLUMN default: if the two ever drift
        # the first pickup collides with a starting row.
        self.assertEqual(
            self._column(),
            max(item.identity for item in INITIAL_BACKPACK.items) + 1,
        )

    def test_the_seed_follows_the_starting_bag_rather_than_the_default(self):
        """The test above cannot see the difference; this one can.

        ``max(identity)+1`` over INITIAL_BACKPACK and migration 005's literal
        DEFAULT 5 agree TODAY, and only today.  A fifth starting row makes
        them disagree, and the disagreement is a first pickup that collides
        with a row the player already owns -- so the seed is measured against
        a five-row starting bag, where a store that trusted the default hands
        out 5 twice.
        """
        five_rows = BackpackState(
            INITIAL_BACKPACK.base_mask, INITIAL_BACKPACK.base_identity,
            INITIAL_BACKPACK.range_mask,
            INITIAL_BACKPACK.items + (
                ItemAttrState(5, ITEM, 1, 4, 0, 0xFF, 0),
            ),
        )
        with mock.patch.object(store_module, "INITIAL_BACKPACK", five_rows):
            other = self.store.create_character(
                self.account_id, "StoreInsertFive", "storeinsertfive",
                "fingerprint-store-insert-001-five", _build_wire, self.home,
            )
        with sqlite3.connect(self.path) as db:
            seeded = int(db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?",
                (other.id,),
            ).fetchone()[0])
        self.assertEqual(seeded, 6)

    def test_issued_through_is_one_below_the_column(self):
        # Migration 005's trap, pinned: the column is EXCLUSIVE, the item
        # lane's parameter is INCLUSIVE.  A store that returned the column
        # here would skip an identity per session.
        self.assertEqual(
            self.store.backpack_issued_through(self.sid, self.character.id),
            self._column() - 1,
        )

    def test_a_minted_identity_is_the_column_itself(self):
        # The two halves meet: what mob_pickup mints from this store's own
        # issued_through mark is exactly the identity the store will accept.
        self.assertEqual(self._mint().identity, self._column())

    # ----- the write ---------------------------------------------------

    def test_the_row_lands_and_the_counter_advances(self):
        item = self._mint()
        after = self.store.commit_acquired_backpack_item(
            self.sid, self.character.id, item,
        )
        self.assertIn(item, after.items)
        self.assertEqual(len(after.items), len(INITIAL_BACKPACK.items) + 1)
        self.assertEqual(self._column(), item.identity + 1)
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), after,
        )

    def test_the_row_survives_a_relog_and_passes_gate_2(self):
        item = self._mint()
        self.store.commit_acquired_backpack_item(
            self.sid, self.character.id, item,
        )
        self._relog()
        reloaded = self.store.get_backpack(self.sid, self.character.id)
        self.assertIn(item, reloaded.items)
        admission = bag_admission.classify(reloaded)
        self.assertEqual(
            admission.verdict, bag_admission.VERDICT_GOLDEN_PLUS_ACQUIRED,
        )
        self.assertEqual(admission.acquired, (item,))
        # With the HYP-PF-008 opt-in OFF, so admission is earned by the
        # acquired row itself rather than by the permissive term.
        self.assertTrue(bag_admission.may_enter_world(
            reloaded, allow_hypothesized_item_move=False,
        ))

    def test_two_pickups_take_two_identities(self):
        first = self._mint()
        self.store.commit_acquired_backpack_item(
            self.sid, self.character.id, first,
        )
        second = self._mint(key_offset=1)
        self.store.commit_acquired_backpack_item(
            self.sid, self.character.id, second,
        )
        self.assertEqual(second.identity, first.identity + 1)
        self.assertNotEqual(second.slot, first.slot)
        self.assertEqual(self._column(), second.identity + 1)
        bag = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(bag.items), len(INITIAL_BACKPACK.items) + 2)

    # ----- the refusals ------------------------------------------------

    def test_an_identity_derived_from_the_bag_is_refused(self):
        """The discriminating case for criterion 2 of STORE-INSERT-001.

        A character who has spent an item has a counter ABOVE the highest
        identity still in the bag.  ``MAX(item_identity)+1`` computed live
        would hand out an identity that character was already issued -- the
        bug migration 005 exists for -- so the store must refuse it and
        accept only the counter's own value.
        """
        self._set_column(9)  # as if identities 5..8 had been issued and spent
        highest_in_bag = max(
            row[0] for row in self._rows()
        )
        stale = ItemAttrState(
            highest_in_bag + 1, ITEM, 1, 4,
            mob_pickup.NEW_ROW_RAW_U8_38,
            mob_pickup.NEW_ROW_RAW_U8_39,
            mob_pickup.NEW_ROW_DETAIL_PRESENT,
        )
        with self.assertRaises(ValueError) as caught:
            self.store.commit_acquired_backpack_item(
                self.sid, self.character.id, stale,
            )
        self.assertIn("next free identity 9", str(caught.exception))
        self.assertEqual(self._column(), 9)
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))
        # and the counter's own value is accepted on the same bag
        accepted = ItemAttrState(
            9, ITEM, 1, 4,
            mob_pickup.NEW_ROW_RAW_U8_38,
            mob_pickup.NEW_ROW_RAW_U8_39,
            mob_pickup.NEW_ROW_DETAIL_PRESENT,
        )
        self.store.commit_acquired_backpack_item(
            self.sid, self.character.id, accepted,
        )
        self.assertEqual(self._column(), 10)

    def test_a_session_without_this_character_selected_cannot_write(self):
        item = self._mint()
        other_account = self.store.ensure_account("store-insert-001-other")
        other_sid = self.store.open_session(other_account)
        with self.assertRaises(PermissionError):
            self.store.commit_acquired_backpack_item(
                other_sid, self.character.id, item,
            )
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))
        self.assertEqual(self._column(), item.identity)

    def test_a_closed_session_cannot_write(self):
        item = self._mint()
        self.store.close_session(self.sid)
        with self.assertRaises(PermissionError):
            self.store.commit_acquired_backpack_item(
                self.sid, self.character.id, item,
            )
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))

    def test_an_occupied_slot_is_refused_by_name(self):
        occupied = ItemAttrState(
            self._column(), ITEM, 1, INITIAL_BACKPACK.items[0].slot,
            mob_pickup.NEW_ROW_RAW_U8_38,
            mob_pickup.NEW_ROW_RAW_U8_39,
            mob_pickup.NEW_ROW_DETAIL_PRESENT,
        )
        with self.assertRaises(ValueError) as caught:
            self.store.commit_acquired_backpack_item(
                self.sid, self.character.id, occupied,
            )
        self.assertIn("occupied", str(caught.exception))
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))

    def test_a_row_gate_2_would_refuse_forever_is_refused_here(self):
        """Containment: everything committed here must be admissible there.

        Found by an adversarial pass, which measured the store committing a
        quantity-0 row that ``bag_admission`` then refuses -- and there is no
        delete-item path, so that character could never enter the world
        again.  Not reachable through ``place_in_bag`` today (it bounds
        quantity, and ``GroundDrop`` bounds the template), which is exactly
        why the store must not rely on the caller for it.
        """
        for bad, label in (
            (ItemAttrState(
                self._column(), ITEM, 0, 4,
                mob_pickup.NEW_ROW_RAW_U8_38,
                mob_pickup.NEW_ROW_RAW_U8_39,
                mob_pickup.NEW_ROW_DETAIL_PRESENT,
            ), "quantity"),
            (ItemAttrState(
                self._column(), 0, 1, 4,
                mob_pickup.NEW_ROW_RAW_U8_38,
                mob_pickup.NEW_ROW_RAW_U8_39,
                mob_pickup.NEW_ROW_DETAIL_PRESENT,
            ), "template"),
        ):
            with self.subTest(field=label):
                # the gate's own verdict on the bag this row would make
                would_be = BackpackState(
                    INITIAL_BACKPACK.base_mask,
                    INITIAL_BACKPACK.base_identity,
                    INITIAL_BACKPACK.range_mask,
                    INITIAL_BACKPACK.items + (bad,),
                )
                self.assertFalse(bag_admission.may_enter_world(
                    would_be, allow_hypothesized_item_move=False,
                ))
                with self.assertRaises(ValueError):
                    self.store.commit_acquired_backpack_item(
                        self.sid, self.character.id, bad,
                    )
                self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))
                self.assertEqual(self._column(), bad.identity)

    def test_an_untyped_row_is_refused_before_the_transaction(self):
        with self.assertRaises(TypeError):
            self.store.commit_acquired_backpack_item(
                self.sid, self.character.id,
                (self._column(), ITEM, 1, 4, 0, 255, 0),
            )
        self.assertEqual(len(self._rows()), len(INITIAL_BACKPACK.items))

    # ----- atomicity ---------------------------------------------------

    def test_the_row_and_the_counter_fail_together(self):
        """Criterion 1: one transaction, so a late failure leaves NEITHER.

        The failure is injected at the post-state read, which runs after both
        writes -- the one window where a non-transactional implementation
        would already have a row on disk with the counter behind it, or a
        counter ahead of a row that never landed.
        """
        item = self._mint()
        before_rows, before_column = self._rows(), self._column()

        def explode(db, character_id):
            raise RuntimeError("injected failure after both writes")

        original = SQLiteStore._load_backpack
        loaded = []

        def load_then_explode(db, character_id):
            loaded.append(character_id)
            if len(loaded) > 1:  # the post-state read, not the pre-state one
                return explode(db, character_id)
            return original(db, character_id)

        SQLiteStore._load_backpack = staticmethod(load_then_explode)
        self.addCleanup(
            setattr, SQLiteStore, "_load_backpack", staticmethod(original),
        )
        try:
            with self.assertRaises(RuntimeError):
                self.store.commit_acquired_backpack_item(
                    self.sid, self.character.id, item,
                )
        finally:
            SQLiteStore._load_backpack = staticmethod(original)
        self.assertEqual(self._rows(), before_rows)
        self.assertEqual(self._column(), before_column)


if __name__ == "__main__":
    unittest.main()
