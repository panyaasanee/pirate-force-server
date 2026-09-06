"""LANE-DB: the `character_equipment` persistence door.

`PANYA-ORDER 20260906_1312` arm (b) ("equip weapon"): the client's
`ItemOperateVitalReq` op=5 (equip) has no server response today
(`notes_to_chief/20260906_1255_KA1A-R321-RESULTS-*.md` -- RE-272 CAPTURED).
This file measures the persistence half only -- `SQLiteStore.equip_item`/
`unequip_slot`/`list_equipped_items`, the write/read doors of
`migrations/015_character_equipment.sql`.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable: there is
no production call site yet (this round's `notes_to_chief/
20260906_1434_LANE-DB-RE-TICKET-*` explains why the response-frame half is
blocked on RE), so equipping a slot here does not make any bytes leave a
socket or change what a real client screen shows. `slot_id` is exercised
here only as the opaque validated integer the migration's own docstring
describes -- no meaning ("weapon slot", "head slot") is asserted for any
particular value.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.store import SQLiteStore, WriteLockTimeout  # noqa: E402

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

_next_identity = iter(range(0x30002001, 0x30003000))


def _build_wire(selector):
    return b"wire", b"avatar", next(_next_identity), 0


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()

    def _make_character(self, login="acct01", name="Test01"):
        account_id = self.store.ensure_account(login)
        self.store.open_session(account_id)
        return self.store.create_character(
            account_id, name, name.casefold(), "fp-" + login,
            _build_wire, _HOME,
        )


class EquipItemTests(_StoreFixture):
    def test_equip_then_list_reads_back_the_row(self):
        character = self._make_character()
        self.store.equip_item(character.id, 8, 4, 2200002)
        self.assertEqual(
            self.store.list_equipped_items(character.id),
            ((8, 4, 2200002),),
        )

    def test_equip_the_same_slot_twice_replaces_not_duplicates(self):
        character = self._make_character()
        self.store.equip_item(character.id, 8, 4, 2200002)
        self.store.equip_item(character.id, 8, 9, 2200005)
        self.assertEqual(
            self.store.list_equipped_items(character.id),
            ((8, 9, 2200005),),
        )

    def test_different_slots_coexist(self):
        character = self._make_character()
        self.store.equip_item(character.id, 8, 4, 2200002)
        self.store.equip_item(character.id, 3, 5, 2400901)
        self.assertEqual(
            self.store.list_equipped_items(character.id),
            ((3, 5, 2400901), (8, 4, 2200002)),
        )

    def test_two_characters_do_not_share_slots(self):
        alice = self._make_character("acct-a", "Alice")
        bob = self._make_character("acct-b", "Bob")
        self.store.equip_item(alice.id, 8, 4, 2200002)
        self.assertEqual(self.store.list_equipped_items(bob.id), ())

    def test_unequip_removes_the_row_and_returns_true(self):
        character = self._make_character()
        self.store.equip_item(character.id, 8, 4, 2200002)
        self.assertTrue(self.store.unequip_slot(character.id, 8))
        self.assertEqual(self.store.list_equipped_items(character.id), ())

    def test_unequip_an_empty_slot_is_a_no_op_returning_false(self):
        character = self._make_character()
        self.assertFalse(self.store.unequip_slot(character.id, 8))

    def test_unknown_character_raises_key_error_on_every_door(self):
        with self.assertRaises(KeyError):
            self.store.equip_item(999999, 8, 4, 2200002)
        with self.assertRaises(KeyError):
            self.store.unequip_slot(999999, 8)
        with self.assertRaises(KeyError):
            self.store.list_equipped_items(999999)

    def test_soft_deleted_character_is_treated_as_gone(self):
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03",
            _build_wire, _HOME,
        )
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.equip_item(character.id, 8, 4, 2200002)

    def test_slot_id_out_of_range_raises_value_error_before_any_write(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.equip_item(character.id, 256, 4, 2200002)
        with self.assertRaises(ValueError):
            self.store.equip_item(character.id, -1, 4, 2200002)
        self.assertEqual(self.store.list_equipped_items(character.id), ())

    def test_item_template_id_out_of_u32_range_raises_value_error(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.equip_item(character.id, 8, 4, 2 ** 32)

    def test_item_identity_negative_raises_value_error(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.equip_item(character.id, 8, -1, 2200002)

    def test_non_int_arguments_raise_type_error(self):
        character = self._make_character()
        with self.assertRaises(TypeError):
            self.store.equip_item(character.id, "8", 4, 2200002)
        with self.assertRaises(TypeError):
            self.store.equip_item(character.id, 8, 4, 2200002.0)
        with self.assertRaises(TypeError):
            self.store.equip_item(character.id, True, 4, 2200002)
        with self.assertRaises(TypeError):
            self.store.unequip_slot(character.id, "8")
        with self.assertRaises(TypeError):
            self.store.list_equipped_items("not-an-int")

    def test_character_id_past_sqlite_int64_range_is_key_error_not_overflow(self):
        # Same class of bug [pf-adversary] caught in `spend_skill_points`
        # and `get_skill_points` -- a raw Python int this large must not
        # reach `sqlite3` as a bind parameter unrefused.
        with self.assertRaises(KeyError):
            self.store.equip_item(2 ** 63, 8, 4, 2200002)
        with self.assertRaises(KeyError):
            self.store.unequip_slot(2 ** 63, 8)
        with self.assertRaises(KeyError):
            self.store.list_equipped_items(2 ** 63)
        with self.assertRaises(KeyError):
            self.store.equip_item(-(2 ** 63) - 1, 8, 4, 2200002)

    def test_write_lock_timeout_replaces_a_raw_operational_error(self):
        # Same deterministic reproduction `test_store_skill_points.py::
        # test_write_lock_timeout_replaces_a_raw_operational_error` uses (no
        # real lock, no multi-second wait): `sqlite3.connect` is patched to
        # hand back a thin proxy whose first `execute("BEGIN IMMEDIATE")`
        # raises the same error real contention raises; every other call
        # passes straight through to a genuine `sqlite3.Connection`.
        character = self._make_character()

        class _RaisesOnFirstBeginImmediate:
            def __init__(self, real):
                object.__setattr__(self, "_real", real)
                object.__setattr__(self, "_raised", False)

            def execute(self, sql, *args, **kwargs):
                if sql == "BEGIN IMMEDIATE" and not self._raised:
                    object.__setattr__(self, "_raised", True)
                    raise sqlite3.OperationalError("database is locked")
                return self._real.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._real, name)

            def __setattr__(self, name, value):
                setattr(self._real, name, value)

        real_connect = sqlite3.connect

        def flaky_connect(*args, **kwargs):
            return _RaisesOnFirstBeginImmediate(real_connect(*args, **kwargs))

        with mock.patch("sqlite3.connect", side_effect=flaky_connect):
            with self.assertRaises(WriteLockTimeout):
                self.store.equip_item(character.id, 8, 4, 2200002)
        # The refused `BEGIN IMMEDIATE` opened no transaction -- nothing was
        # written, so a retry on a real connection sees an empty slot list.
        self.assertEqual(self.store.list_equipped_items(character.id), ())


if __name__ == "__main__":
    unittest.main()
