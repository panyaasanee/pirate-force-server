"""LANE-DB: the ground-drop persistence door -- write, then read it back.

WHAT THIS FILE IS THE EVIDENCE FOR.  `20260903_1740_LANE-DB-REPORT-ground-
ledger-in-memory-no-table-door-proposed.md` measured that "what is on the
ground and has not been picked up yet" lives ONLY in a per-session,
in-memory `mob_loot.DropLedgerCell` -- a second login on the same account
sees an empty ground where the first login's kill left a drop.
`COO-DECISION 20260903_1843` ordered the door this file proves: a bare
table (`migrations/010_ground_drops.sql`) plus `SQLiteStore.
commit_ground_drop`/`list_ground_drops_for_scene`.  This file measures the
wire/DB half only -- there is no call site yet (that is LANE-B's, ordered
separately in `20260903_1844`), so nothing here is client-observable.

WHAT THIS FILE DOES NOT CLAIM.  It does not claim a ground drop reaches a
player -- there is no call site.  It does not claim removal/expiry works --
`COO-DECISION 20260901_0253` holds that no ledger row may be removed until a
removal publisher exists, and this round's scope, per `COO-DECISION
20260903_1843` point 5, is write-then-read-back only; `test_there_is_no_
delete_or_expiry_method_on_this_door` measures that the scope was actually
kept, not just described. It does not import or exercise `mob_loot.
GroundDrop` -- this lane's charter (`COO-DECISION 20260901_1100`) keeps
`mob_loot.py` entirely LANE-B's, so the fixtures below build primitives by
hand rather than through that module, the same choice `persistence_ground_
drops.py`'s own docstring explains for why `store.py` does not import it.
"""
from __future__ import annotations

import io
import contextlib
import math
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import store as store_module          # noqa: E402
from pirateforce_foundation.persistence_ground_drops import (     # noqa: E402
    GroundDropRow,
)
from pirateforce_foundation.store import SQLiteStore              # noqa: E402

MIGRATIONS = ROOT / "migrations"
TEN = MIGRATIONS / "010_ground_drops.sql"

#: A round-trippable ground drop, with a value in every column that is not
#: the natural default of its type (0 / 0.0 / ""), so a column silently
#: dropped or swapped for another shows up as a mismatch rather than a
#: coincidental match.
A_DROP = dict(
    scene="bg0001", drop_key=0x00100000, item_id=2400046, quantity=3,
    x=10.5, y=-20.25, z=30.75, mob_identity=0x2068, killer_identity=0x750059,
)


def _raw_rows(path):
    """The table's own rows, read outside the store's accessors entirely."""
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT id,scene,scene_fold,drop_key,item_id,quantity,x,y,z,"
            "mob_identity,killer_identity,created_at FROM ground_drops "
            "ORDER BY id"
        )]
    finally:
        db.close()


def _table_info(path, table="ground_drops"):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT cid,name,type,\"notnull\",dflt_value,pk "
            "FROM pragma_table_info(?)", (table,))]
    finally:
        db.close()


def _applied(path):
    db = sqlite3.connect(str(path))
    try:
        return sorted(int(row[0]) for row in db.execute(
            "SELECT version FROM schema_migrations"))
    finally:
        db.close()


def _all_characters(path):
    db = sqlite3.connect(str(path))
    try:
        return [tuple(row) for row in db.execute(
            "SELECT * FROM characters ORDER BY id")]
    finally:
        db.close()


class _StoreFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()


class TheMigrationItselfTests(_StoreFixture):

    def test_010_is_on_disk_and_is_the_newest_version(self):
        self.assertTrue(TEN.exists(), TEN)
        versions = sorted(
            int(p.name[:3]) for p in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")
        )
        self.assertEqual(versions[-1], 10)
        self.assertEqual(len(versions), len(set(versions)))

    def test_the_ledger_records_version_10(self):
        self.assertIn(10, _applied(self.path))

    def test_applying_twice_changes_nothing(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(_applied(self.path).count(10), 1)
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_edited_010_is_refused_on_a_database_that_applied_it(self):
        mutated = Path(self.tmp.name) / "mutated_migrations"
        mutated.mkdir()
        for path in MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql"):
            text = path.read_text(encoding="utf-8")
            if path.name == TEN.name:
                text = text.replace(
                    "-- 010_ground_drops.sql",
                    "-- 010 (edited after it was applied)",
                )
            (mutated / path.name).write_text(text, encoding="utf-8")
        with self.assertRaises(RuntimeError) as caught:
            SQLiteStore(self.path, mutated).migrate()
        self.assertIn("checksum mismatch", str(caught.exception))

    def test_no_existing_table_or_row_is_touched(self):
        """010 is a bare CREATE TABLE -- not a rebuild, not a backfill.

        Measured, not assumed: a fresh account+character built on THIS
        database (already at 010) round-trips exactly like one built at 009,
        and `characters`' own DDL text is exactly what a 009-only database
        produces.
        """
        db = sqlite3.connect(str(self.path))
        try:
            after_ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='characters'"
            ).fetchone()[0]
        finally:
            db.close()

        nine_only = Path(self.tmp.name) / "nine_only.sqlite3"
        nine_only_migrations = Path(self.tmp.name) / "nine_only_migrations"
        nine_only_migrations.mkdir()
        for path in sorted(MIGRATIONS.glob("00[1-9]_*.sql")):
            (nine_only_migrations / path.name).write_text(
                path.read_text(encoding="utf-8"), encoding="utf-8")
        SQLiteStore(nine_only, nine_only_migrations).migrate()
        db = sqlite3.connect(str(nine_only))
        try:
            before_ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='characters'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertEqual(after_ddl, before_ddl)
        self.assertEqual(_all_characters(self.path), [])


class TheTableShapeTests(_StoreFixture):

    def test_the_columns_match_ground_drop_plus_the_folded_key(self):
        columns = {row[1] for row in _table_info(self.path)}
        self.assertEqual(
            columns,
            {
                "id", "scene", "scene_fold", "drop_key", "item_id",
                "quantity", "x", "y", "z", "mob_identity", "killer_identity",
                "created_at",
            },
        )

    def test_the_unique_constraint_is_on_the_folded_scene_and_the_key(self):
        db = sqlite3.connect(str(self.path))
        try:
            ddl = db.execute(
                "SELECT sql FROM sqlite_master "
                "WHERE type='table' AND name='ground_drops'"
            ).fetchone()[0]
        finally:
            db.close()
        self.assertIn("UNIQUE(scene_fold,drop_key)", ddl.replace(" ", ""))
        self.assertNotIn(
            "UNIQUE(scene,drop_key)", ddl.replace(" ", ""),
            "the constraint must key off the case-folded column, not the "
            "raw one, or two spellings of one scene each mint the same key",
        )


class TheWriteThenReadBackDoorTests(_StoreFixture):

    def test_every_field_survives_the_round_trip_exactly(self):
        row = self.store.commit_ground_drop(**A_DROP)
        self.assertIsInstance(row, GroundDropRow)
        for field, value in A_DROP.items():
            self.assertEqual(getattr(row, field), value, field)
        self.assertGreater(row.id, 0)
        self.assertTrue(row.created_at)

    def test_the_raw_table_holds_the_same_row_the_store_returned(self):
        row = self.store.commit_ground_drop(**A_DROP)
        raw = _raw_rows(self.path)
        self.assertEqual(len(raw), 1)
        (rid, scene, scene_fold, drop_key, item_id, quantity, x, y, z,
         mob_identity, killer_identity, created_at) = raw[0]
        self.assertEqual(rid, row.id)
        self.assertEqual(scene, A_DROP["scene"])
        self.assertEqual(scene_fold, A_DROP["scene"].casefold())
        self.assertEqual(drop_key, A_DROP["drop_key"])
        self.assertEqual(item_id, A_DROP["item_id"])
        self.assertEqual(quantity, A_DROP["quantity"])
        self.assertEqual((x, y, z), (A_DROP["x"], A_DROP["y"], A_DROP["z"]))
        self.assertEqual(mob_identity, A_DROP["mob_identity"])
        self.assertEqual(killer_identity, A_DROP["killer_identity"])
        self.assertEqual(created_at, row.created_at)

    def test_the_row_survives_a_brand_new_store_against_the_same_file(self):
        """The whole point of the door: a second login sees the first
        login's drop, unlike `mob_loot.DropLedgerCell` today."""
        self.store.commit_ground_drop(**A_DROP)
        reopened = SQLiteStore(self.path, MIGRATIONS)
        seen = reopened.list_ground_drops_for_scene(A_DROP["scene"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].drop_key, A_DROP["drop_key"])

    def test_two_drops_in_one_scene_both_come_back_in_insertion_order(self):
        first = self.store.commit_ground_drop(**A_DROP)
        second = self.store.commit_ground_drop(
            **{**A_DROP, "drop_key": A_DROP["drop_key"] + 1, "quantity": 1},
        )
        seen = self.store.list_ground_drops_for_scene(A_DROP["scene"])
        self.assertEqual([row.id for row in seen], [first.id, second.id])

    def test_a_different_scene_is_not_returned(self):
        self.store.commit_ground_drop(**A_DROP)
        self.assertEqual(
            self.store.list_ground_drops_for_scene("bg0002"), (),
        )

    def test_lookup_is_case_insensitive_like_scene_key(self):
        self.store.commit_ground_drop(**A_DROP)
        for spelling in ("bg0001", "Bg0001", "BG0001"):
            with self.subTest(spelling=spelling):
                seen = self.store.list_ground_drops_for_scene(spelling)
                self.assertEqual(len(seen), 1)
                self.assertEqual(seen[0].drop_key, A_DROP["drop_key"])

    def test_an_empty_scene_returns_nothing_not_an_error(self):
        self.assertEqual(self.store.list_ground_drops_for_scene("bg9999"), ())


class TheCollisionIsRefusedLoudlyTests(_StoreFixture):

    def test_the_same_scene_and_key_twice_raises_and_writes_nothing_more(self):
        self.store.commit_ground_drop(**A_DROP)
        with self.assertRaises(ValueError) as caught:
            self.store.commit_ground_drop(
                **{**A_DROP, "quantity": 99},
            )
        self.assertIn("0x%X" % A_DROP["drop_key"], str(caught.exception))
        rows = self.store.list_ground_drops_for_scene(A_DROP["scene"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].quantity, A_DROP["quantity"])

    def test_the_refusal_prints_the_console_token(self):
        self.store.commit_ground_drop(**A_DROP)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(ValueError):
                self.store.commit_ground_drop(**A_DROP)
        self.assertIn(
            store_module.GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN,
            buffer.getvalue(),
        )

    def test_two_spellings_of_one_scene_collide_too(self):
        """The whole reason the UNIQUE constraint keys off `scene_fold`."""
        self.store.commit_ground_drop(**A_DROP)
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(
                **{**A_DROP, "scene": A_DROP["scene"].upper()},
            )
        self.assertEqual(
            len(self.store.list_ground_drops_for_scene(A_DROP["scene"])), 1,
        )

    def test_the_same_key_in_a_different_scene_does_not_collide(self):
        self.store.commit_ground_drop(**A_DROP)
        other = self.store.commit_ground_drop(**{**A_DROP, "scene": "bg0002"})
        self.assertEqual(other.drop_key, A_DROP["drop_key"])
        self.assertEqual(
            len(self.store.list_ground_drops_for_scene("bg0002")), 1,
        )


class ANonCollisionIntegrityErrorIsNotMislabelledTests(_StoreFixture):
    """`pf-adversary`, round `5d02mu`: an earlier draft caught EVERY
    `sqlite3.IntegrityError` in `commit_ground_drop` -- not only the UNIQUE
    violation the collision guard exists for -- and reported all of them as
    a key collision, demonstrated live by disabling the Python-side
    `math.isfinite` guard and watching a non-finite coordinate get
    diagnosed as "already on the ground". These tests bypass that one
    Python validator on purpose, the same way, to prove the SQL-side CHECK
    (`migrations/010_ground_drops.sql`) is a REAL independent backstop and
    that its own refusal is not swallowed into the collision message.
    """

    def test_the_sql_check_independently_refuses_a_non_finite_coordinate(self):
        with mock.patch.object(store_module.math, "isfinite", return_value=True):
            with self.assertRaises(sqlite3.IntegrityError) as caught:
                self.store.commit_ground_drop(**{**A_DROP, "x": math.inf})
        self.assertNotIsInstance(caught.exception, ValueError)
        self.assertNotIn("already on the ground", str(caught.exception))
        self.assertEqual(_raw_rows(self.path), [])

    def test_that_refusal_does_not_print_the_collision_token(self):
        buffer = io.StringIO()
        with mock.patch.object(store_module.math, "isfinite", return_value=True):
            with contextlib.redirect_stdout(buffer):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.store.commit_ground_drop(**{**A_DROP, "x": math.inf})
        self.assertNotIn(
            store_module.GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN,
            buffer.getvalue(),
        )

    def test_a_real_collision_afterward_still_works_normally(self):
        """The narrowed `except` does not accidentally stop catching the
        collision it exists for."""
        self.store.commit_ground_drop(**A_DROP)
        with self.assertRaises(ValueError) as caught:
            self.store.commit_ground_drop(**A_DROP)
        self.assertIn("already on the ground", str(caught.exception))


class TheDoorRefusesBadInputBeforeWritingTests(_StoreFixture):

    def _assert_nothing_written(self):
        self.assertEqual(_raw_rows(self.path), [])

    def test_an_empty_scene_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "scene": ""})
        self._assert_nothing_written()

    def test_a_non_str_scene_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "scene": 1})
        self._assert_nothing_written()

    def test_a_drop_key_outside_u32_is_refused(self):
        for bad in (-1, 0x100000000):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.store.commit_ground_drop(**{**A_DROP, "drop_key": bad})
        self._assert_nothing_written()

    def test_a_bool_drop_key_is_refused_not_coerced_to_0_or_1(self):
        with self.assertRaises(TypeError):
            self.store.commit_ground_drop(**{**A_DROP, "drop_key": True})
        self._assert_nothing_written()

    def test_a_zero_item_id_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "item_id": 0})
        self._assert_nothing_written()

    def test_a_zero_quantity_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "quantity": 0})
        self._assert_nothing_written()

    def test_a_quantity_above_u16_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "quantity": 0x10000})
        self._assert_nothing_written()

    def test_a_non_finite_coordinate_is_refused(self):
        for bad in (math.inf, -math.inf, math.nan):
            for axis in ("x", "y", "z"):
                with self.subTest(axis=axis, bad=bad):
                    with self.assertRaises(ValueError):
                        self.store.commit_ground_drop(**{**A_DROP, axis: bad})
        self._assert_nothing_written()

    def test_an_int_coordinate_is_accepted_and_stored_as_real(self):
        row = self.store.commit_ground_drop(**{**A_DROP, "x": 10})
        self.assertEqual(row.x, 10.0)
        self.assertIsInstance(row.x, float)

    def test_an_out_of_range_identity_is_refused(self):
        for field in ("mob_identity", "killer_identity"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    self.store.commit_ground_drop(
                        **{**A_DROP, field: 0x100000000},
                    )
        self._assert_nothing_written()


class TheSceneMustBeASCIISafeTests(_StoreFixture):
    """pf-adversary (round `orpati`): `migrations/010_ground_drops.sql`'s
    own comment claims "every scene value this table ever holds is
    required ASCII" by `mob_loot._require_scene` -- true only once a
    LANE-B call site that constructs through `mob_loot.GroundDrop` exists.
    Before this class's fix, `commit_ground_drop`/`list_ground_drops_for_
    scene` accepted ANY non-empty str, so a direct caller (a test, an
    admin tool) could reach two live defects: a false collision between
    two scenes that differ only by a character with no ASCII fold
    equivalent, and a `UnicodeEncodeError` crash in the collision-refusal
    `print()` on this lane's cp874 console."""

    def test_a_non_ascii_scene_is_refused_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "scene": "Straße"})
        self.assertEqual(_raw_rows(self.path), [])

    def test_two_scenes_that_only_differ_by_a_non_ascii_fold_do_not_collide(self):
        """`"Straße"` and `"STRASSE"` both `.casefold()` to `"strasse"`
        under full Unicode folding -- proving the door refuses the
        non-ASCII spelling outright, rather than letting it collide with
        an unrelated scene that happens to share the folded form."""
        self.store.commit_ground_drop(**{**A_DROP, "scene": "STRASSE"})
        with self.assertRaises(ValueError) as caught:
            self.store.commit_ground_drop(**{**A_DROP, "scene": "Straße"})
        self.assertNotIn("already on the ground", str(caught.exception))
        self.assertEqual(len(self.store.list_ground_drops_for_scene("STRASSE")), 1)

    def test_the_refusal_of_a_non_ascii_scene_does_not_crash_printing(self):
        """The collision-refusal path prints `scene` with `%r` -- if a
        non-ASCII scene ever reached that `print()`, it would raise
        `UnicodeEncodeError` on a cp874 console rather than deliver the
        `ValueError` cleanly.  Validating `scene` before that branch means
        this call never gets far enough to try."""
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            with self.assertRaises(ValueError):
                self.store.commit_ground_drop(**{**A_DROP, "scene": "Straße"})
        self.assertNotIn(
            store_module.GROUND_DROP_KEY_COLLISION_REFUSED_TOKEN,
            buffer.getvalue(),
        )

    def test_a_scene_with_whitespace_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(**{**A_DROP, "scene": "bg 0001"})
        self._assert_nothing_written()

    def _assert_nothing_written(self):
        self.assertEqual(_raw_rows(self.path), [])

    def test_a_scene_over_the_length_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            self.store.commit_ground_drop(
                **{**A_DROP, "scene": "b" * (store_module.GROUND_DROP_SCENE_MAX + 1)},
            )
        self._assert_nothing_written()

    def test_list_also_refuses_a_non_ascii_scene(self):
        with self.assertRaises(ValueError):
            self.store.list_ground_drops_for_scene("Straße")


class TheDoorsScopeStaysWhatWasOrderedTests(_StoreFixture):

    def test_there_is_no_delete_or_expiry_method_on_this_door(self):
        """`COO-DECISION 20260903_1843` point 5 / `20260901_0253`: no
        removal until a removal publisher exists.  Measured against the
        store's own attribute list so a later round that adds one without
        updating this test is the failure, not a silent scope change."""
        forbidden_fragments = ("delete_ground", "expire_ground", "remove_ground")
        names = [name for name in dir(SQLiteStore) if not name.startswith("_")]
        for name in names:
            for fragment in forbidden_fragments:
                self.assertNotIn(
                    fragment, name,
                    "a removal method exists before a removal publisher does",
                )

    def test_commit_ground_drop_takes_no_session_argument(self):
        """A ground drop is world state for a scene, not a session's own
        row -- unlike `commit_acquired_backpack_item`, which is why this
        door's signature carries no `sid`."""
        import inspect
        params = list(inspect.signature(
            SQLiteStore.commit_ground_drop).parameters)
        self.assertNotIn("sid", params)
        self.assertNotIn("character_id", params)


if __name__ == "__main__":
    unittest.main()
