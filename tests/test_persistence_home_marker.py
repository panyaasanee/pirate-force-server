"""LANE-DB: the home-marker persistence door -- write, then read it back.

WHAT THIS FILE IS THE EVIDENCE FOR.  A live attended round (R317,
`pf_bridge/notes_to_chief/20260905_1125_KA1A-R317-RESULTS-*.md`) measured
the server refusing quest 3205 ("born again") every time with
`COLUMBUS_QUEST3205_BORNAGAIN_REFUSED reason=no_home_marker_persistence_
row_evidence` -- there was nowhere in this database to hold which scene is
a character's home.  `pf_bridge/notes_to_chief/
20260905_1154_COO-DECISION-db-takes-no-world-work-home-marker-persistence-
row-queued-after-1044-LANE-DB.md` point 3(b) ordered the door this file
proves: a bare table (`migrations/013_character_home_marker.sql`) plus
`SQLiteStore.set_home_marker`/`get_home_marker`.  This file measures the
wire/DB half only -- quest 3205's own dispatch lives in `runtime.py`, which
this lane's charter (`COO-DECISION 20260901_1100`) does not touch, so
there is no call site yet and nothing here is client-observable.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim quest 3205 stops
refusing -- that needs `runtime.py` wired to call this door, a CORE-REQUEST
to chief, not this lane's write zone.  It does not claim a home marker
survives across a server RESTART with a different database file -- it
claims the ordinary case every other typed column in this schema already
proves: the row is still there the next time this SAME database is opened,
which is what "survives relog" reduces to at the storage layer.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.model import Position          # noqa: E402
from pirateforce_foundation.persistence_home_marker import (  # noqa: E402
    HomeMarkerRow,
)
from pirateforce_foundation.store import SQLiteStore        # noqa: E402

MIGRATIONS = ROOT / "migrations"
THIRTEEN = MIGRATIONS / "013_character_home_marker.sql"


def _raw_row(path, character_id):
    """The table's own row, read outside the store's accessors entirely."""
    db = sqlite3.connect(str(path))
    try:
        return db.execute(
            "SELECT character_id,home_scene_id,updated_at "
            "FROM character_home_marker WHERE character_id=?",
            (character_id,),
        ).fetchone()
    finally:
        db.close()


def _table_info(path):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT cid,name,type,\"notnull\",dflt_value,pk "
            "FROM pragma_table_info('character_home_marker')"
        )]
    finally:
        db.close()


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


class _Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "home_marker_test.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 0.0, 0.0, 0.0, heading=0.0)
        self.account_id = self.store.ensure_account("home-marker-tests")

    def _make_character(self, tag):
        return self.store.create_character(
            self.account_id, f"HM{tag}", f"hm{tag}",
            f"fingerprint-hm-{tag}", _build_wire, self.home,
        ).id


class MigrationShapeTests(unittest.TestCase):
    def test_013_creates_exactly_one_new_table_no_default_no_backfill(self):
        sql = THIRTEEN.read_text(encoding="utf-8")
        code_only = "\n".join(
            line for line in sql.splitlines()
            if not line.strip().startswith("--")
        )
        statements = [s.strip() for s in code_only.split(";") if s.strip()]
        self.assertEqual(len(statements), 1)
        self.assertIn("CREATE TABLE character_home_marker", statements[0])
        self.assertTrue(statements[0].upper().startswith("CREATE TABLE"))
        self.assertNotIn("DEFAULT", statements[0].upper())

    def test_column_shape_is_pk_plus_scene_id_plus_timestamp(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            path = Path(tmp.name) / "shape.sqlite3"
            SQLiteStore(path, MIGRATIONS).migrate()
            columns = {row[1]: row for row in _table_info(path)}
            self.assertEqual(
                set(columns), {"character_id", "home_scene_id", "updated_at"}
            )
            self.assertEqual(columns["character_id"][5], 1)  # pk
            self.assertEqual(columns["home_scene_id"][3], 1)  # notnull
            self.assertEqual(columns["updated_at"][3], 1)  # notnull
        finally:
            tmp.cleanup()

    def test_a_fresh_migrate_leaves_zero_rows_for_an_existing_character(self):
        """No backfill: a character born before this migration gets no
        guessed home -- `get_home_marker` must answer `None`, not a row
        this file invented."""
        store = SQLiteStore(
            Path(tempfile.mkdtemp()) / "zero_rows.sqlite3", MIGRATIONS
        )
        store.migrate()
        account_id = store.ensure_account("predates-013")
        character_id = store.create_character(
            account_id, "Predates", "predates", "fingerprint-predates",
            _build_wire, Position(1, 0, 0.0, 0.0, 0.0, heading=0.0),
        ).id
        self.assertIsNone(store.get_home_marker(character_id))


class SetHomeMarkerWritesAndReadsBackTests(_Workspace):
    def test_a_first_call_creates_the_row_and_returns_it(self):
        character_id = self._make_character("A")
        result = self.store.set_home_marker(character_id, 1)
        self.assertIsInstance(result, HomeMarkerRow)
        self.assertEqual(result.character_id, character_id)
        self.assertEqual(result.home_scene_id, 1)
        raw = _raw_row(self.path, character_id)
        self.assertEqual(raw[0], character_id)
        self.assertEqual(raw[1], 1)
        self.assertEqual(raw[2], result.updated_at)

    def test_get_home_marker_reads_back_exactly_what_was_set(self):
        character_id = self._make_character("B")
        self.store.set_home_marker(character_id, 3)
        readback = self.store.get_home_marker(character_id)
        self.assertEqual(readback, HomeMarkerRow(character_id, 3, readback.updated_at))

    def test_a_second_call_upserts_in_place_not_a_second_row(self):
        character_id = self._make_character("C")
        first = self.store.set_home_marker(character_id, 1)
        second = self.store.set_home_marker(character_id, 2)
        self.assertNotEqual(first.updated_at, second.updated_at)
        readback = self.store.get_home_marker(character_id)
        self.assertEqual(readback.home_scene_id, 2)
        db = sqlite3.connect(str(self.path))
        try:
            count = db.execute(
                "SELECT COUNT(*) FROM character_home_marker WHERE character_id=?",
                (character_id,),
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(count, 1)

    def test_two_different_characters_get_two_independent_rows(self):
        first_id = self._make_character("D")
        second_id = self._make_character("E")
        self.store.set_home_marker(first_id, 1)
        self.store.set_home_marker(second_id, 3)
        self.assertEqual(self.store.get_home_marker(first_id).home_scene_id, 1)
        self.assertEqual(self.store.get_home_marker(second_id).home_scene_id, 3)

    def test_survives_reopening_the_same_database(self):
        """The storage-layer half of "survives relog": a fresh `SQLiteStore`
        pointed at the same file, no in-memory state carried over, still
        answers the marker a previous handle wrote."""
        character_id = self._make_character("F")
        self.store.set_home_marker(character_id, 1)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        reopened.migrate()
        self.assertEqual(reopened.get_home_marker(character_id).home_scene_id, 1)


class GetHomeMarkerBeforeAnySetTests(_Workspace):
    def test_a_character_with_no_marker_set_yet_reads_back_none(self):
        character_id = self._make_character("G")
        self.assertIsNone(self.store.get_home_marker(character_id))

    def test_an_id_nothing_created_also_reads_back_none_not_an_error(self):
        self.assertIsNone(self.store.get_home_marker(999999))


class UnknownOrSoftDeletedCharacterIsRefusedOnWriteTests(_Workspace):
    def test_setting_a_marker_for_an_id_nothing_created_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.store.set_home_marker(999999, 1)

    def test_setting_a_marker_for_a_soft_deleted_character_raises_keyerror(self):
        character_id = self._make_character("H")
        sid = self.store.open_session(self.account_id)
        character = self.store.list_characters(self.account_id)[0]
        self.store.soft_delete_character(sid, character.selector)
        with self.assertRaises(KeyError):
            self.store.set_home_marker(character_id, 1)

    def test_nothing_is_written_when_the_character_check_fails(self):
        with self.assertRaises(KeyError):
            self.store.set_home_marker(999999, 1)
        self.assertIsNone(_raw_row(self.path, 999999))


class InputValidationRefusesBeforeAnySQLTests(_Workspace):
    def test_a_bool_is_refused_not_silently_coerced_to_0_or_1(self):
        character_id = self._make_character("I")
        with self.assertRaises(TypeError):
            self.store.set_home_marker(character_id, True)
        self.assertIsNone(_raw_row(self.path, character_id))

    def test_a_float_is_refused(self):
        character_id = self._make_character("J")
        with self.assertRaises(TypeError):
            self.store.set_home_marker(character_id, 1.5)

    def test_a_negative_scene_id_is_refused(self):
        character_id = self._make_character("K")
        with self.assertRaises(ValueError):
            self.store.set_home_marker(character_id, -1)

    def test_a_scene_id_above_the_u16_range_is_refused(self):
        character_id = self._make_character("L")
        with self.assertRaises(ValueError):
            self.store.set_home_marker(character_id, 0x10000)

    def test_the_top_of_the_u16_range_is_accepted(self):
        character_id = self._make_character("M")
        result = self.store.set_home_marker(character_id, 0xFFFF)
        self.assertEqual(result.home_scene_id, 0xFFFF)


class SelectCharacterHonoringHomeMarkerTests(_Workspace):
    """`select_character_honoring_home_marker` -- `COO-DECISION
    20260905_1946` item 1, option (a) of `pf_bridge/notes_to_chief/
    20260905_1606_LANE-DB-REPLY-*`.  `select_character` itself is asserted
    untouched throughout: every case below also calls it directly and
    checks it still returns the raw, un-swapped row.
    """

    def _character_and_session(self, tag):
        character = self.store.create_character(
            self.account_id, f"HMH{tag}", f"hmh{tag}",
            f"fingerprint-hmh-{tag}", _build_wire, self.home,
        )
        sid = self.store.open_session(self.account_id)
        return character, sid

    def test_no_home_marker_is_byte_for_byte_what_select_character_returns(self):
        character, sid = self._character_and_session("A")
        plain = self.store.select_character(sid, character.selector)
        honoring = self.store.select_character_honoring_home_marker(
            sid, character.selector)
        self.assertEqual(honoring, plain)

    def test_home_marker_naming_the_current_scene_changes_nothing(self):
        character, sid = self._character_and_session("B")
        self.store.set_home_marker(character.id, self.home.scene_id)
        plain = self.store.select_character(sid, character.selector)
        honoring = self.store.select_character_honoring_home_marker(
            sid, character.selector)
        self.assertEqual(honoring, plain)

    def test_home_marker_naming_another_scene_swaps_only_scene_id(self):
        character, sid = self._character_and_session("C")
        self.store.set_home_marker(character.id, 3)
        plain = self.store.select_character(sid, character.selector)
        honoring = self.store.select_character_honoring_home_marker(
            sid, character.selector)
        self.assertEqual(honoring.position.scene_id, 3)
        self.assertEqual(honoring.position.scene_seq, plain.position.scene_seq)
        self.assertEqual(honoring.position.x, plain.position.x)
        self.assertEqual(honoring.position.y, plain.position.y)
        self.assertEqual(honoring.position.z, plain.position.z)
        self.assertEqual(honoring.position.heading, plain.position.heading)
        self.assertEqual(honoring.id, plain.id)
        self.assertEqual(honoring.name, plain.name)
        self.assertEqual(honoring.account_id, plain.account_id)
        self.assertEqual(honoring.selector, plain.selector)

    def test_select_character_itself_still_returns_the_raw_scene_id(self):
        """The one thing this whole feature is not allowed to touch."""
        character, sid = self._character_and_session("D")
        self.store.set_home_marker(character.id, 5)
        plain = self.store.select_character(sid, character.selector)
        self.assertEqual(plain.position.scene_id, self.home.scene_id)

    def test_an_unknown_selector_raises_keyerror_same_as_select_character(self):
        sid = self.store.open_session(self.account_id)
        with self.assertRaises(KeyError):
            self.store.select_character(sid, 999)
        with self.assertRaises(KeyError):
            self.store.select_character_honoring_home_marker(sid, 999)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
