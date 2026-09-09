"""LANE-DB: ``SQLiteStore.mint_backpack_item`` -- give a character one row
for a known catalog item with NO ground drop involved.

WHY THIS FILE EXISTS.  ``COO-DECISION 20260908_2055`` ("the item minter next
to your own door is yours") answers LANE-Q's `20260908_1942` ask (routed to
COO): the write door (``commit_acquired_backpack_item``) already existed,
what was missing was something that composes an ``ItemAttrState`` from an
item number and a quantity instead of a caller building one by hand.  This
file is the evidence that the new door (a) actually lands a row, (b) lands
it THROUGH the existing gate rather than a second write path, and (c)
refuses the three named cases readably instead of writing a half-row.

THE NAME IS [PROPOSED].  ``COO-DECISION 20260908_2055`` requires agreeing
the function name with LANE-Q by letter before landing; this round proposes
`mint_backpack_item` in `pf_bridge/notes_to_chief/` and implements under
that name.  If LANE-Q's own pinned test wants a different one, that is a
rename in this file and in `store.py`, not a redesign -- the shape is
already the one COO ordered.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import tempfile  # noqa: E402

from pirateforce_foundation import store as store_module  # noqa: E402
from pirateforce_foundation.gm import item_catalog  # noqa: E402
from pirateforce_foundation.inventory import INITIAL_BACKPACK  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


def _known_misc_item_id() -> int:
    """One real id from the committed catalog, DERIVED from the same file
    ``item_catalog`` reads rather than a literal picked by hand -- if the
    extraction ever drops row one this test moves with it instead of
    silently testing an id nobody ships any more."""
    data_path = Path(item_catalog.__file__).parent / "data" / "gm_item_misc.tsv"
    with data_path.open("r", encoding="utf-8", newline="") as handle:
        next(handle)  # header
        first_data_row = next(handle)
    item_id = int(first_data_row.split("\t", 1)[0])
    assert item_catalog.is_known_item(item_id, category="misc"), (
        "the derived id is not what item_catalog itself reports as known -- "
        "the two are reading different files"
    )
    return item_id


KNOWN_ITEM_ID = _known_misc_item_id()

# One past INITIAL_BACKPACK's own slots (0..3): the lowest free slot on a
# freshly created character, derived rather than spelled, the same way
# tests/test_store_acquired_item_insert.py derives its own seed.
FIRST_FREE_SLOT = max(item.slot for item in INITIAL_BACKPACK.items) + 1


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


class MintBackpackItemTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, ROOT / "migrations")
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("mint-backpack-item")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "MintOne", "mintone",
            "fingerprint-mint-backpack-item", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)

    def _ground_drop_count(self):
        with self.store.connect() as db:
            return db.execute("SELECT count(*) FROM ground_drops").fetchone()[0]

    # ----- the happy path -----------------------------------------------

    def test_mints_a_known_item_into_the_first_free_slot_with_no_ground_drop(self):
        before_drops = self._ground_drop_count()
        after = self.store.mint_backpack_item(
            self.sid, self.character.id, KNOWN_ITEM_ID, 3,
        )
        new_rows = [row for row in after.items if row.template_id == KNOWN_ITEM_ID]
        self.assertEqual(len(new_rows), 1)
        minted = new_rows[0]
        self.assertEqual(minted.slot, FIRST_FREE_SLOT)
        self.assertEqual(minted.quantity, 3)
        self.assertEqual(
            minted.identity,
            max(item.identity for item in INITIAL_BACKPACK.items) + 1,
        )
        # No ground drop was ever involved -- this is the whole point of the
        # door existing (LANE-Q's reward payout has no drop to pick up).
        self.assertEqual(self._ground_drop_count(), before_drops)
        # Read back through a fresh call, same as a relog would see.
        reread = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(reread, after)

    def test_lands_the_row_through_the_existing_door_not_a_new_one(self):
        """The contract COO wrote: 'writes through the existing gate -- not
        a new one'.  Proven by SPYING on the real door rather than re-typing
        its SQL here: if this method ever stops calling it and starts
        executing its own INSERT, this goes red without needing an AST walk
        of store.py to notice."""
        with mock.patch.object(
            self.store, "commit_acquired_backpack_item",
            wraps=self.store.commit_acquired_backpack_item,
        ) as spy:
            self.store.mint_backpack_item(
                self.sid, self.character.id, KNOWN_ITEM_ID, 1,
            )
        spy.assert_called_once()
        (sid_arg, cid_arg, item_arg), _kwargs = spy.call_args
        self.assertEqual(sid_arg, self.sid)
        self.assertEqual(cid_arg, self.character.id)
        self.assertEqual(item_arg.template_id, KNOWN_ITEM_ID)

    # ----- the three named refusals --------------------------------------

    def test_refuses_an_item_id_outside_the_committed_catalog(self):
        unknown_id = 0xFFFFFFF  # not in any of the three committed tables
        self.assertFalse(item_catalog.is_known_item(unknown_id))
        before = self.store.get_backpack(self.sid, self.character.id)
        with self.assertRaises(KeyError):
            self.store.mint_backpack_item(
                self.sid, self.character.id, unknown_id, 1,
            )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_a_zero_or_negative_quantity(self):
        before = self.store.get_backpack(self.sid, self.character.id)
        for bad_quantity in (0, -1, -100):
            with self.assertRaises(ValueError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, KNOWN_ITEM_ID, bad_quantity,
                )
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )

    def test_refuses_a_non_integer_quantity_by_type(self):
        for bad_quantity in (1.0, "1", True, None):
            with self.assertRaises(TypeError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, KNOWN_ITEM_ID, bad_quantity,
                )

    def test_refuses_a_non_integer_item_id_by_type(self):
        for bad_item_id in (1.0, "1", True, None):
            with self.assertRaises(TypeError):
                self.store.mint_backpack_item(
                    self.sid, self.character.id, bad_item_id, 1,
                )

    def test_refuses_when_the_backpack_is_full_before_composing_anything(self):
        # Fill every remaining slot (4..39) directly, the same shape
        # test_store_acquired_item_insert.py's own fixtures use, so the next
        # mint has nowhere free to land.
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            next_identity = db.execute(
                "SELECT next_item_identity FROM character_backpacks "
                "WHERE character_id=?", (self.character.id,),
            ).fetchone()[0]
            filler_rows = [
                (self.character.id, next_identity + offset, KNOWN_ITEM_ID, 1, slot, 0, 0xFF, 0)
                for offset, slot in enumerate(range(FIRST_FREE_SLOT, 40))
            ]
            db.executemany(
                "INSERT INTO character_backpack_items("
                "character_id,item_identity,template_id,quantity,slot,"
                "raw_u8_38,raw_u8_39,detail_present"
                ") VALUES (?,?,?,?,?,?,?,?)",
                filler_rows,
            )
            db.execute(
                "UPDATE character_backpacks SET next_item_identity=? "
                "WHERE character_id=?",
                (next_identity + len(filler_rows), self.character.id),
            )
        before = self.store.get_backpack(self.sid, self.character.id)
        self.assertEqual(len(before.items), 40)
        with self.assertRaises(ValueError):
            self.store.mint_backpack_item(
                self.sid, self.character.id, KNOWN_ITEM_ID, 1,
            )
        # Nothing moved: a full bag refuses before anything is composed,
        # not after a half-written row.
        self.assertEqual(
            self.store.get_backpack(self.sid, self.character.id), before,
        )


if __name__ == "__main__":
    unittest.main()
