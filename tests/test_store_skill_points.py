"""LANE-DB: the `characters.skill_points` read/spend door.

`PANYA-DECISION 20260904_0328` piece 5 / `LANE-CS CORE-REQUEST
pf_bridge/notes_to_chief/20260905_1510_LANE-CS-CORE-REQUEST-store-py-skill-
points-hookup-to-lane-db-rerouted-from-chief.md` (rerouted from chief, who
answered that `store.py` is this lane's write zone, not his): LANE-CS built
`skill_learn_validator.can_afford_to_learn`/`skill_points_after_learning` as
pure functions over a plain `int` balance a caller supplies -- this file
measures the two new `SQLiteStore` methods that ARE that caller's read and
write half, `get_skill_points`/`spend_skill_points`.

WHAT THIS FILE DOES NOT PROVE.  Nothing here is client-observable.  There is
no production call site yet on either side (LANE-CS's own module says so,
and neither method appears in `runtime.py`/`session.py`), so nobody has
learned a skill on a real connection because of this file.  `skill_points`
is one of `migrations/006_character_typed_attribute_columns.sql`'s typed
columns and `migrations/009_character_birth_defaults.sql` does NOT give it a
default -- so a freshly created character's balance is NULL (unmeasured)
until something else writes it, and this file's fixtures write it directly
with `write_typed_attributes` rather than pretending `create_character`
already seeds it.
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
from pirateforce_foundation.store import (  # noqa: E402
    InsufficientSkillPointsError,
    SQLiteStore,
    UnmeasuredSkillPointsError,
    WriteLockTimeout,
)

MIGRATIONS = ROOT / "migrations"

_HOME = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)

#: Bumped per character so two rows never collide on
#: `UNIQUE(identity_lo, identity_hi)` -- unrelated to anything this file
#: measures, same idiom `test_persistence_character_skills_011.py` uses.
_next_identity = iter(range(0x30000001, 0x30001000))


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


class GetSkillPointsTests(_StoreFixture):
    def test_a_fresh_character_reads_none_not_zero(self):
        # `009` gives no DEFAULT for `skill_points` -- a newborn's balance is
        # NULL, and `COO-DECISION 20260901_1059` forbids reporting that as a
        # measured `0`.
        character = self._make_character()
        self.assertIsNone(self.store.get_skill_points(character.id))

    def test_reads_back_a_value_written_by_write_typed_attributes(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 7})
        self.assertEqual(self.store.get_skill_points(character.id), 7)

    def test_zero_is_a_real_measured_value_distinct_from_none(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 0})
        self.assertEqual(self.store.get_skill_points(character.id), 0)

    def test_unknown_character_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.store.get_skill_points(999999)

    def test_character_id_past_sqlite_int64_range_is_key_error_not_overflow(self):
        # [pf-adversary, this round] reproduced a raw `OverflowError` from
        # `read_typed_attributes` here before this guard existed.
        with self.assertRaises(KeyError):
            self.store.get_skill_points(2 ** 63)

    def test_soft_deleted_character_is_treated_as_gone(self):
        account_id = self.store.ensure_account("acct03")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted", "deleted", "fp-acct03",
            _build_wire, _HOME,
        )
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.get_skill_points(character.id)


class SpendSkillPointsTests(_StoreFixture):
    def test_unmeasured_balance_refuses_rather_than_guessing(self):
        character = self._make_character()
        with self.assertRaises(UnmeasuredSkillPointsError):
            self.store.spend_skill_points(character.id, 1)
        # Refusing must not have written anything -- still NULL, not 0.
        self.assertIsNone(self.store.get_skill_points(character.id))

    def test_spends_and_returns_the_new_balance(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 10})
        remaining = self.store.spend_skill_points(character.id, 4)
        self.assertEqual(remaining, 6)
        # Read-after-write agrees with the returned value.
        self.assertEqual(self.store.get_skill_points(character.id), 6)

    def test_spending_the_full_balance_reaches_zero(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 3})
        self.assertEqual(self.store.spend_skill_points(character.id, 3), 0)

    def test_spending_zero_is_a_no_op_that_still_reads_back(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        self.assertEqual(self.store.spend_skill_points(character.id, 0), 5)

    def test_insufficient_balance_refuses_and_writes_nothing(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 2})
        with self.assertRaises(InsufficientSkillPointsError):
            self.store.spend_skill_points(character.id, 3)
        # No partial spend -- the balance is exactly what it was before.
        self.assertEqual(self.store.get_skill_points(character.id), 2)

    def test_negative_cost_is_refused_before_any_sql_runs(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        with self.assertRaises(ValueError):
            self.store.spend_skill_points(character.id, -1)
        self.assertEqual(self.store.get_skill_points(character.id), 5)

    def test_bool_cost_is_refused_like_every_other_typed_write(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        with self.assertRaises(TypeError):
            self.store.spend_skill_points(character.id, True)

    def test_bool_character_id_is_refused(self):
        with self.assertRaises(TypeError):
            self.store.spend_skill_points(True, 1)

    def test_non_int_cost_is_refused(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        with self.assertRaises(TypeError):
            self.store.spend_skill_points(character.id, 1.5)

    def test_unknown_character_raises_key_error(self):
        with self.assertRaises(KeyError):
            self.store.spend_skill_points(999999, 1)

    def test_soft_deleted_character_is_treated_as_gone(self):
        account_id = self.store.ensure_account("acct04")
        sid = self.store.open_session(account_id)
        character = self.store.create_character(
            account_id, "Deleted2", "deleted2", "fp-acct04",
            _build_wire, _HOME,
        )
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.spend_skill_points(character.id, 1)

    def test_character_id_past_sqlite_int64_range_is_key_error_not_overflow(self):
        # [pf-adversary, this round] reproduced a raw `OverflowError` here
        # before the `_fits_sqlite_integer` guard was added -- an id this
        # far out of range can never be a real row, so `KeyError` is the
        # honest answer, not an undocumented arithmetic crash.
        with self.assertRaises(KeyError):
            self.store.spend_skill_points(2 ** 63, 1)
        with self.assertRaises(KeyError):
            self.store.spend_skill_points(-(2 ** 63) - 1, 1)

    def test_cost_past_sqlite_int64_range_is_value_error_not_overflow(self):
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})
        with self.assertRaises(ValueError):
            self.store.spend_skill_points(character.id, 2 ** 63)

    def test_write_lock_timeout_replaces_a_raw_operational_error(self):
        # [pf-adversary, this round] reproduced a raw
        # `sqlite3.OperationalError: database is locked` leaking out of
        # `spend_skill_points` under real write contention -- a caller
        # following this method's documented exception contract would not
        # catch that.  Reproduced deterministically here (no real lock, no
        # multi-second wait): `sqlite3.Connection` is a C type and cannot be
        # monkeypatched directly (`TypeError: cannot set 'execute' attribute
        # of immutable type`), so `sqlite3.connect` itself is patched to hand
        # back a thin proxy whose first `execute("BEGIN IMMEDIATE")` raises
        # the same error real contention raises; every other call --
        # `row_factory` assignment included -- passes straight through to a
        # genuine `sqlite3.Connection` against the real temp-file database.
        character = self._make_character()
        self.store.write_typed_attributes(character.id, {"skill_points": 5})

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
                self.store.spend_skill_points(character.id, 1)
        # The refused `BEGIN IMMEDIATE` opened no transaction -- nothing was
        # written, so a retry on a real connection still sees the old balance.
        self.assertEqual(self.store.get_skill_points(character.id), 5)


class SchemaDriftGuardTests(_StoreFixture):
    """A database that predates migration 006 must not crash with a raw
    `sqlite3.OperationalError` naming no column -- same guard every other
    typed-attribute-writing method in `store.py` already carries.
    """

    def setUp(self):
        super().setUp()
        self.character = self._make_character()
        self.store.write_typed_attributes(
            self.character.id, {"skill_points": 8},
        )
        with self.store.connect() as db:
            db.execute("ALTER TABLE characters DROP COLUMN skill_points")

    def test_spend_raises_schema_drift_error_not_a_raw_sqlite_error(self):
        from pirateforce_foundation import persistence_vitals as vitals

        with self.assertRaises(vitals.SchemaDriftError):
            self.store.spend_skill_points(self.character.id, 1)

    def test_get_omits_the_missing_column_instead_of_crashing(self):
        # `read_typed_attributes` already guards this path (its own test
        # file measures it in depth); this just confirms the thin wrapper
        # inherits the guard rather than bypassing it with its own SQL.
        self.assertIsNone(self.store.get_skill_points(self.character.id))


if __name__ == "__main__":
    unittest.main()
