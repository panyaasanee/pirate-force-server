"""chief: the `character_quest_flags`/`character_quest_counters` persistence
door, on LANE-Q's CORE-REQUEST.

`pf_bridge/notes_to_chief/20260906_1950_LANE-Q-CORE-REQUEST-quest-flag-
counter-daily-stamp-columns.md`: `lua_api.quest.QuestStateStore` (PR #947)
already codes against this exact contract, backed today only by
`InMemoryQuestStateStore` -- explicitly not the production answer (does not
survive a relog). This file measures the persistence half only --
`SQLiteStore.get_quest_flag`/`set_quest_flag`/`get_quest_counter`/
`set_quest_counter`, the doors of `migrations/016_character_quest_state.sql`.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable or even
LANE-Q-observable yet: no call site in `lua_api/quest.py` reaches these
methods (that wiring is a separate round's work, once this door exists) --
same "schema/store door ready before the seam calls it" shape
`test_store_character_equipment.py` measures for `equip_item`.
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

_next_identity = iter(range(0x30004001, 0x30005000))


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


class QuestFlagTests(_StoreFixture):
    def test_unset_flag_reads_back_none_not_an_error(self):
        character = self._make_character()
        self.assertIsNone(self.store.get_quest_flag(character.id, 42))

    def test_set_then_get_reads_back_the_value(self):
        character = self._make_character()
        self.assertEqual(self.store.set_quest_flag(character.id, 42, 1), 1)
        self.assertEqual(self.store.get_quest_flag(character.id, 42), 1)

    def test_set_the_same_quest_twice_replaces_not_duplicates(self):
        character = self._make_character()
        self.store.set_quest_flag(character.id, 42, 1)
        self.store.set_quest_flag(character.id, 42, 2)
        self.assertEqual(self.store.get_quest_flag(character.id, 42), 2)

    def test_different_quests_coexist(self):
        character = self._make_character()
        self.store.set_quest_flag(character.id, 42, 1)
        self.store.set_quest_flag(character.id, 99, 2)
        self.assertEqual(self.store.get_quest_flag(character.id, 42), 1)
        self.assertEqual(self.store.get_quest_flag(character.id, 99), 2)

    def test_two_characters_do_not_share_flags(self):
        alice = self._make_character("acct-a", "Alice")
        bob = self._make_character("acct-b", "Bob")
        self.store.set_quest_flag(alice.id, 42, 1)
        self.assertIsNone(self.store.get_quest_flag(bob.id, 42))

    def test_flag_survives_a_relog(self):
        # The whole point of the door: a fresh SQLiteStore instance on the
        # same file, matching test_store_character_equipment.py's own
        # "the row survives a fresh store instance" shape elsewhere in this
        # project (test_persistence_backpack_relogin.py).
        character = self._make_character()
        self.store.set_quest_flag(character.id, 42, 2)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        self.assertEqual(reopened.get_quest_flag(character.id, 42), 2)

    def test_unknown_character_raises_key_error_on_every_door(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_flag(999999, 42, 1)
        with self.assertRaises(KeyError):
            self.store.get_quest_flag(999999, 42)

    def test_soft_deleted_character_is_treated_as_gone(self):
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03",
            _build_wire, _HOME,
        )
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.set_quest_flag(character.id, 42, 1)

    def test_quest_id_out_of_range_raises_value_error_before_any_write(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.set_quest_flag(character.id, 65536, 1)
        with self.assertRaises(ValueError):
            self.store.set_quest_flag(character.id, -1, 1)
        self.assertIsNone(self.store.get_quest_flag(character.id, 65535))

    def test_flag_value_out_of_u32_range_raises_value_error(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.set_quest_flag(character.id, 42, 2 ** 32)
        with self.assertRaises(ValueError):
            self.store.set_quest_flag(character.id, 42, -1)

    def test_non_int_arguments_raise_type_error(self):
        character = self._make_character()
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(character.id, "42", 1)
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(character.id, 42, 1.0)
        with self.assertRaises(TypeError):
            self.store.set_quest_flag(character.id, 42, True)
        with self.assertRaises(TypeError):
            self.store.get_quest_flag(character.id, "42")

    def test_character_id_past_sqlite_int64_range_is_key_error_not_overflow(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_flag(2 ** 63, 42, 1)
        with self.assertRaises(KeyError):
            self.store.get_quest_flag(2 ** 63, 42)

    def test_write_lock_timeout_replaces_a_raw_operational_error(self):
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
                self.store.set_quest_flag(character.id, 42, 1)
        self.assertIsNone(self.store.get_quest_flag(character.id, 42))


class QuestCounterTests(_StoreFixture):
    def test_unset_counter_reads_back_none_not_an_error(self):
        character = self._make_character()
        self.assertIsNone(
            self.store.get_quest_counter(character.id, 42, "1234"))

    def test_set_then_get_reads_back_the_value(self):
        character = self._make_character()
        self.assertEqual(
            self.store.set_quest_counter(character.id, 42, "1234", 3), 3)
        self.assertEqual(
            self.store.get_quest_counter(character.id, 42, "1234"), 3)

    def test_set_is_absolute_not_an_increment(self):
        character = self._make_character()
        self.store.set_quest_counter(character.id, 42, "1234", 3)
        self.store.set_quest_counter(character.id, 42, "1234", 1)
        self.assertEqual(
            self.store.get_quest_counter(character.id, 42, "1234"), 1)

    def test_two_counters_in_the_same_quest_are_separate_rows(self):
        # q_kill5.lua's own shape: two mobs tracked at once in one quest.
        character = self._make_character()
        self.store.set_quest_counter(character.id, 42, "1234", 3)
        self.store.set_quest_counter(character.id, 42, "5678", 1)
        self.assertEqual(
            self.store.get_quest_counter(character.id, 42, "1234"), 3)
        self.assertEqual(
            self.store.get_quest_counter(character.id, 42, "5678"), 1)

    def test_the_daily_stamp_key_and_a_kill_count_key_coexist(self):
        character = self._make_character()
        self.store.set_quest_counter(character.id, 42, "1234", 2)
        self.store.set_quest_counter(
            character.id, 42, "daily_report_epoch_day", 19972)
        self.assertEqual(
            self.store.get_quest_counter(character.id, 42, "1234"), 2)
        self.assertEqual(
            self.store.get_quest_counter(
                character.id, 42, "daily_report_epoch_day"),
            19972,
        )

    def test_two_characters_do_not_share_counters(self):
        alice = self._make_character("acct-a", "Alice")
        bob = self._make_character("acct-b", "Bob")
        self.store.set_quest_counter(alice.id, 42, "1234", 3)
        self.assertIsNone(self.store.get_quest_counter(bob.id, 42, "1234"))

    def test_counter_survives_a_relog(self):
        character = self._make_character()
        self.store.set_quest_counter(character.id, 42, "1234", 3)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        self.assertEqual(
            reopened.get_quest_counter(character.id, 42, "1234"), 3)

    def test_unknown_character_raises_key_error_on_every_door(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_counter(999999, 42, "1234", 1)
        with self.assertRaises(KeyError):
            self.store.get_quest_counter(999999, 42, "1234")

    def test_soft_deleted_character_is_treated_as_gone(self):
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03",
            _build_wire, _HOME,
        )
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.set_quest_counter(character.id, 42, "1234", 1)

    def test_quest_id_out_of_range_raises_value_error_before_any_write(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, 65536, "1234", 1)
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, -1, "1234", 1)
        self.assertIsNone(
            self.store.get_quest_counter(character.id, 65535, "1234"))

    def test_counter_value_out_of_u32_range_raises_value_error(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, 42, "1234", 2 ** 32)
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, 42, "1234", -1)

    def test_counter_name_length_out_of_range_raises_value_error(self):
        character = self._make_character()
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, 42, "", 1)
        with self.assertRaises(ValueError):
            self.store.set_quest_counter(character.id, 42, "x" * 129, 1)
        self.assertEqual(
            self.store.set_quest_counter(character.id, 42, "x" * 128, 1), 1)

    def test_non_int_or_non_str_arguments_raise_type_error(self):
        character = self._make_character()
        with self.assertRaises(TypeError):
            self.store.set_quest_counter(character.id, "42", "1234", 1)
        with self.assertRaises(TypeError):
            self.store.set_quest_counter(character.id, 42, 1234, 1)
        with self.assertRaises(TypeError):
            self.store.set_quest_counter(character.id, 42, "1234", 1.0)
        with self.assertRaises(TypeError):
            self.store.set_quest_counter(character.id, 42, "1234", True)
        with self.assertRaises(TypeError):
            self.store.get_quest_counter(character.id, 42, 1234)

    def test_character_id_past_sqlite_int64_range_is_key_error_not_overflow(self):
        with self.assertRaises(KeyError):
            self.store.set_quest_counter(2 ** 63, 42, "1234", 1)
        with self.assertRaises(KeyError):
            self.store.get_quest_counter(2 ** 63, 42, "1234")

    def test_write_lock_timeout_replaces_a_raw_operational_error(self):
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
                self.store.set_quest_counter(character.id, 42, "1234", 1)
        self.assertIsNone(
            self.store.get_quest_counter(character.id, 42, "1234"))


if __name__ == "__main__":
    unittest.main()
