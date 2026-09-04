"""Grades `src/pirateforce_foundation/persistence_class_id_backfill.py`.

This is the WRITE half of the boot-time `class_id` backfill
`COO-DECISION 20260904_0445` orders: `store.list_character_ids_missing_
class_id` (the read half) names every live character the creation-time
hookup never reached, and `backfill_missing_class_ids` walks that list once
and resolves each one the same way a fresh creation would have.

The module under test deliberately calls
`lifecycle.persist_class_id_from_starting_gear` rather than decoding
`avatar_wire` itself -- `tests/test_world_avatar_attr.py`'s Rule 14.13(d)
guard makes `lifecycle.py` the only production file allowed to mention that
decoder at all.  This test file is free to use `world_avatar_attr.
build_body`/`decode_avatar_attr` directly (that guard only scans
`src/pirateforce_foundation`, `current`, `tools`, `migrations` and
`scenarios`, not `tests`) to build real, decodable fixtures -- the same
freedom `tests/test_persistence_class_id.py` already uses.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import persistence_class_id_backfill as backfill
from pirateforce_foundation.model import Position
from pirateforce_foundation.persistence_class_id import CLASS_PRESETS
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.world_avatar_attr import build_body

MIGRATIONS = ROOT / "migrations"

# Bit positions the corpus assigns these three fields (world_avatar_attr.FIELDS).
BIT_CHEST = 5
BIT_LEGGINGS = 6
BIT_RHAND = 10

RESOLVABLE_CLASS_ID, RESOLVABLE_CHEST, RESOLVABLE_LEGGINGS, RESOLVABLE_RHAND = (
    CLASS_PRESETS[0]
)


def _resolvable_avatar_wire() -> bytes:
    """A real, decodable body whose gear trio matches exactly one
    `CLASS_PRESETS` row -- what a fresh `CreateActorVital` would carry for
    a player who picked that class/look."""
    return build_body(
        (BIT_CHEST, BIT_LEGGINGS, BIT_RHAND),
        {
            BIT_CHEST: RESOLVABLE_CHEST,
            BIT_LEGGINGS: RESOLVABLE_LEGGINGS,
            BIT_RHAND: RESOLVABLE_RHAND,
        },
    )


def _unresolvable_avatar_wire() -> bytes:
    """A real, decodable body whose gear trio matches no `CLASS_PRESETS`
    row at all -- the "no field or no single preset match" case, not a
    decode failure."""
    return build_body(
        (BIT_CHEST, BIT_LEGGINGS, BIT_RHAND),
        {BIT_CHEST: 0xFFFFFFFF, BIT_LEGGINGS: 0xFFFFFFFE, BIT_RHAND: 0xFFFFFFFD},
    )


class BackfillMissingClassIdsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("backfill-account")
        self.backups_root = Path(self.tmp.name) / "db_backups"

    def _make(self, tag, avatar_wire):
        def build_wire(selector):
            return b"actor-wire-" + tag.encode("ascii"), avatar_wire, 0x20000001 + selector, 0

        return self.store.create_character(
            self.account_id, f"Char{tag}", f"char{tag}",
            f"fingerprint-{tag}", build_wire, self.home,
        )

    def test_empty_database_does_nothing_and_takes_no_snapshot(self):
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(report.outcomes, ())
        self.assertIsNone(report.snapshot_path)
        self.assertFalse(self.backups_root.exists())

    def test_a_resolvable_character_is_written_and_read_back_true(self):
        character = self._make("resolvable", _resolvable_avatar_wire())
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(len(report.outcomes), 1)
        outcome = report.outcomes[0]
        self.assertEqual(outcome.character_id, character.id)
        self.assertEqual(outcome.class_id, RESOLVABLE_CLASS_ID)
        self.assertTrue(outcome.written)
        self.assertEqual(report.written_count, 1)
        self.assertEqual(report.unresolved_count, 0)
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["class_id"],
            RESOLVABLE_CLASS_ID,
        )

    def test_an_unresolvable_character_stays_null(self):
        character = self._make("unresolvable", _unresolvable_avatar_wire())
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(len(report.outcomes), 1)
        outcome = report.outcomes[0]
        self.assertEqual(outcome.character_id, character.id)
        self.assertIsNone(outcome.class_id)
        self.assertFalse(outcome.written)
        self.assertEqual(report.written_count, 0)
        self.assertEqual(report.unresolved_count, 1)
        self.assertNotIn(
            "class_id", self.store.read_typed_attributes(character.id),
        )

    def test_a_garbage_avatar_wire_is_unresolved_not_a_crash(self):
        """Not decodable at all (too short) -- must fold into the same
        UNRESOLVED outcome as "decodable but no preset match", never raise
        out of a boot pass over one bad row."""
        character = self._make("garbage", b"\x00")
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        outcome = report.outcomes[0]
        self.assertEqual(outcome.character_id, character.id)
        self.assertIsNone(outcome.class_id)
        self.assertFalse(outcome.written)

    def test_two_rows_are_both_visited_in_one_pass(self):
        resolvable = self._make("r", _resolvable_avatar_wire())
        unresolvable = self._make("u", _unresolvable_avatar_wire())
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        by_id = {o.character_id: o for o in report.outcomes}
        self.assertEqual(set(by_id), {resolvable.id, unresolvable.id})
        self.assertTrue(by_id[resolvable.id].written)
        self.assertFalse(by_id[unresolvable.id].written)
        self.assertEqual(report.written_count, 1)
        self.assertEqual(report.unresolved_count, 1)

    def test_a_soft_deleted_character_is_excluded_entirely(self):
        deleted = self._make("deleted", _resolvable_avatar_wire())
        self.store.soft_delete_character(
            self.store.open_session(self.account_id), deleted.selector,
        )
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(report.outcomes, ())

    def test_a_second_pass_over_an_already_resolved_database_writes_nothing(self):
        """Idempotent: once a row is resolved, it drops out of `store.list_
        character_ids_missing_class_id`, so a second boot's pass never
        touches it again."""
        self._make("once", _resolvable_avatar_wire())
        first = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(first.written_count, 1)
        second = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertEqual(second.outcomes, ())
        self.assertIsNone(second.snapshot_path)

    def test_a_row_already_set_between_listing_and_reaching_it_is_not_reguessed(self):
        """The TOCTOU window `write_typed_attribute_if_unset`'s own
        docstring names: something else set this row's `class_id` after
        `list_character_ids_missing_class_id` listed it, but before this
        pass's per-row loop reached it.  Must not raise, must not attempt a
        second write, must report the value that is actually there."""
        character = self._make("raced", _resolvable_avatar_wire())
        # Simulate the race directly against `_backfill_one`: the row is
        # already non-NULL by the time it is visited.
        self.store.write_typed_attributes(character.id, {"class_id": 3})
        outcome = backfill._backfill_one(self.store, character.id)
        self.assertEqual(outcome.character_id, character.id)
        self.assertEqual(outcome.class_id, 3)
        self.assertFalse(outcome.written)
        # Untouched: still exactly the raced-in value, not overwritten by
        # whatever this character's real gear would have resolved to.
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["class_id"], 3,
        )

    def test_a_character_that_vanishes_before_reaching_it_is_unresolved(self):
        character = self._make("vanishing", _resolvable_avatar_wire())
        self.store.soft_delete_character(
            self.store.open_session(self.account_id), character.selector,
        )
        outcome = backfill._backfill_one(self.store, character.id)
        self.assertEqual(outcome.character_id, character.id)
        self.assertIsNone(outcome.class_id)
        self.assertFalse(outcome.written)

    def test_console_lines_for_written_and_unresolved_rows(self):
        """`_backfill_one` prints nothing of its own -- the per-row line is
        `lifecycle.persist_class_id_from_starting_gear`'s existing
        `CHARACTER_CLASS_ID ...` line (`COO-DECISION 20260904_0446`/`0549`,
        confirmed still sufficient by `pf_bridge/notes_to_chief/
        20260904_0938_CHIEF-TO-LANE-DB-...md`: "the real format wins over
        the old letter's text").  This module only adds the snapshot line
        rule (c) needs, which nothing else prints."""
        written = self._make("w", _resolvable_avatar_wire())
        unresolved = self._make("x", _unresolvable_avatar_wire())
        with mock.patch("builtins.print") as mocked_print:
            backfill.backfill_missing_class_ids(
                self.store, backups_root=self.backups_root,
            )
        lines = [call.args[0] for call in mocked_print.call_args_list]
        self.assertIn(
            f"CHARACTER_CLASS_ID cid={written.id} written "
            f"class_id={RESOLVABLE_CLASS_ID}",
            lines,
        )
        self.assertIn(
            f"CHARACTER_CLASS_ID cid={unresolved.id} not_written "
            "reason=starting_gear_matches_no_single_preset",
            lines,
        )
        self.assertTrue(
            any(
                line.startswith("CLASS_ID_BACKFILL_SNAPSHOT path=")
                for line in lines
            ),
        )

    def test_already_set_by_someone_else_is_reported_without_a_second_write(self):
        character = self._make("raced2", _resolvable_avatar_wire())
        self.store.write_typed_attributes(character.id, {"class_id": 2})
        with mock.patch("builtins.print") as mocked_print:
            outcome = backfill._backfill_one(self.store, character.id)
        lines = [call.args[0] for call in mocked_print.call_args_list]
        self.assertEqual(outcome.class_id, 2)
        self.assertFalse(outcome.written)
        # `persist_class_id_from_starting_gear`'s own line for this case --
        # proves the row was actually offered to the one real writer (not
        # silently skipped by a stale pre-check) and that writer, correctly,
        # refused it.
        self.assertIn(
            f"CHARACTER_CLASS_ID cid={character.id} not_written "
            "reason=already_set",
            lines,
        )

    def test_a_read_back_mismatch_raises_loudly(self):
        """Rule (d)'s verification is a live check, not decoration: a store
        whose read-back disagrees with what this pass itself just wrote
        must stop this row's processing with a `RuntimeError`."""
        character = self._make("mismatch", _resolvable_avatar_wire())

        class LyingReadBackStore:
            """Delegates everything to the real store, except that
            `read_typed_attributes` always reports a wrong value.  There is
            only one call to it on the success path this test drives (the
            post-write verification -- the redesigned module has no
            pre-write check left to call it a second time), so lying
            unconditionally is enough to isolate it."""

            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def read_typed_attributes(self, cid):
                return {"class_id": 999999}

        lying = LyingReadBackStore(self.store)
        with self.assertRaises(RuntimeError):
            backfill._backfill_one(lying, character.id)
        # The real row itself is untouched by the lie -- only the read that
        # reported it was wrong.
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["class_id"],
            RESOLVABLE_CLASS_ID,
        )

    def test_a_read_back_that_finds_the_row_vanished_does_not_raise(self):
        """The write already committed, inside its own transaction, before
        this check ever runs -- a row that then vanishes (soft-delete
        racing the read-back itself) is not this check's business, and
        must not turn a genuinely successful write into a raised error."""
        character = self._make("vanish-after-write", _resolvable_avatar_wire())

        class VanishesOnReadBackStore:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def read_typed_attributes(self, cid):
                raise KeyError(cid)

        outcome = backfill._backfill_one(
            VanishesOnReadBackStore(self.store), character.id,
        )
        self.assertEqual(outcome.class_id, RESOLVABLE_CLASS_ID)
        self.assertTrue(outcome.written)
        # The real store's row genuinely holds the write -- only the lying
        # wrapper's read-back claimed otherwise.
        self.assertEqual(
            self.store.read_typed_attributes(character.id)["class_id"],
            RESOLVABLE_CLASS_ID,
        )


class _FakeInMemoryStore:
    """The method surface `backfill_missing_class_ids`/`_backfill_one`/
    `lifecycle.persist_class_id_from_starting_gear` need, backed by plain
    Python dicts instead of SQLite.

    Not a stand-in for `SQLiteStore` in general -- just the minimum this
    module's write path touches.  Used here because a REAL `SQLiteStore(":
    memory:", ...)` cannot actually hold state across this module's several
    separate calls: `SQLiteStore.connect()` opens a brand new
    `sqlite3.connect(":memory:")` connection every time (`store.py`'s own
    docstring names no persistence guarantee across calls for that path,
    and `tests/test_persistence_premigration_backup.py`'s own `:memory:`
    coverage only ever exercises one call, `migrate_with_backup()`, for the
    same reason) -- so each call after the first would see an empty,
    freshly-created database with none of this fixture's rows in it.  This
    fake is what makes "the code path for a real in-memory database, with a
    row actually in it, end to end" testable at all.
    """

    path = ":memory:"

    def __init__(self, characters: dict[int, bytes]):
        self._avatar_wire = dict(characters)
        self._class_id: dict[int, int] = {}

    def list_character_ids_missing_class_id(self):
        return tuple(
            sorted(cid for cid in self._avatar_wire if cid not in self._class_id)
        )

    def get_character(self, cid: int):
        if cid not in self._avatar_wire:
            raise KeyError(cid)
        return SimpleNamespace(id=cid, avatar_wire=self._avatar_wire[cid])

    def read_typed_attributes(self, cid: int):
        if cid not in self._avatar_wire:
            raise KeyError(cid)
        return {"class_id": self._class_id[cid]} if cid in self._class_id else {}

    def write_typed_attribute_if_unset(self, cid: int, column: str, value):
        assert column == "class_id"
        if cid not in self._avatar_wire:
            raise KeyError(cid)
        if cid in self._class_id:
            return None
        self._class_id[cid] = value
        return value


class InMemoryStoreSkipsSnapshotTests(unittest.TestCase):
    """`:memory:` has nothing on disk to protect -- the same carve-out
    `persistence_backup.should_snapshot` documents. This must not raise
    `persistence_backup.BackupError` (it would, for a path that does not
    exist on disk) and must still resolve and write real rows."""

    def test_snapshot_is_skipped_but_the_row_is_still_backfilled(self):
        store = _FakeInMemoryStore({7: _resolvable_avatar_wire()})
        with mock.patch(
            "pirateforce_foundation.persistence_class_id_backfill.snapshot_database"
        ) as mocked_snapshot:
            report = backfill.backfill_missing_class_ids(store)
        mocked_snapshot.assert_not_called()
        self.assertIsNone(report.snapshot_path)
        self.assertEqual(report.written_count, 1)
        self.assertEqual(report.outcomes[0].class_id, RESOLVABLE_CLASS_ID)
        self.assertEqual(store._class_id[7], RESOLVABLE_CLASS_ID)


class BackupOnDiskTests(unittest.TestCase):
    """The snapshot itself, for a real on-disk database: taken before the
    first write, path printed, and a real directory a human could open."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.path, MIGRATIONS)
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=0.0)
        self.account_id = self.store.ensure_account("backup-account")
        self.backups_root = Path(self.tmp.name) / "db_backups"

    def test_a_snapshot_directory_lands_on_disk_before_the_write(self):
        def build_wire(selector):
            return b"actor-wire", _resolvable_avatar_wire(), 0x20000001 + selector, 0

        self.store.create_character(
            self.account_id, "BackupChar", "backupchar", "fp-backup",
            build_wire, self.home,
        )
        report = backfill.backfill_missing_class_ids(
            self.store, backups_root=self.backups_root,
        )
        self.assertIsNotNone(report.snapshot_path)
        self.assertTrue(report.snapshot_path.exists())
        self.assertTrue((report.snapshot_path).is_file())
        self.assertIn("classid_backfill", report.snapshot_path.parent.name)


if __name__ == "__main__":
    unittest.main()
