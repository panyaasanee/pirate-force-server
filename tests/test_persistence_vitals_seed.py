"""LANE-DB / M4: `migrations/007_character_vitals_seed.sql` writes the three
numbers this server already sends, into the three columns that were empty,
without inventing anything and without touching a row that already has a value.

WHY THIS FILE EXISTS.  `persistence_vitals` refuses every character whose
`hp_current` has never been written -- on this wire zero is DEAD, so an
unseeded column is a NAMED GAP and never a zero (the owner's rule, relayed in
`COO-DECISION 20260901_1059`).  That refusal is correct and it is also why
nothing could be hit and nothing could die: after `006` every one of those
columns was NULL on every row.  `COO-DECISION 20260902_0250` adjudicated the
values -- `level=1`, `hp_current=100`, `hp_max=100`, `IS NULL` only,
transcribed from what `player_wire.py:203-205` already puts on the wire -- and
attached three conditions.  This file is the evidence for the first of them
and the harness for the second.

THE THREE CONDITIONS, AND WHERE EACH IS ANSWERED

1. "the ActorAttr bytes composed from the DB equal the bytes
   `player_wire.py:203-205` sends today, every byte" -- `WireBytesMatchTests`.
   The shipped frame is BUILT, not quoted: the expected side comes out of
   `make_actor_attr_with_name_and_class`, the actual side is re-encoded from
   what the migration left in the database, and the same encoder is used for
   both so that only the VALUES can differ.  `test_a_different_seed_would_have
   _been_caught` runs the comparison again over a tampered row to show the
   assertion can fail.
2. "report `vitals_seeding_census` from a real database, counted, not read out
   of a file" -- the numbers go in the round file; `CensusAfter007Tests` is
   what produces them here and pins their shape.
3. "the migration header carries `TRANSCRIBED from player_wire hardcode --
   original game default OPEN`" -- `MigrationTextTests`.

WHAT THIS FILE DOES NOT PROVE, said here rather than left to be found:

* Nothing is client-observable.  No frame reaches a socket in any test here;
  `player_wire` is called as a library to obtain the bytes it would send, and
  no call site in this repository composes a login block out of these columns
  yet.  A player cannot see this round.
* It has never run against the owner's canonical database.  Every number in
  this file is counted from a database these tests build.
* `test_a_character_created_after_007_is_still_unseeded` pins a HOLE, not a
  success: the seed reaches the rows that exist when it runs, and
  `store.create_character` (`store.py:232`) does not name these columns, so a
  character made afterwards is three gaps again.  It is a test so that nobody
  can report "007 landed, M4 is open" without this going red first if they
  also delete the test.
* v141 is not a criterion anywhere here.  `load_legacy` supplies the tag
  encoder that `player_wire` itself requires in order to produce a frame at
  all; the thing being measured is `player_wire`'s output against the
  database, and the encoder is held identical on both sides of every
  comparison.
"""
import re
import shutil
import sqlite3
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from pirateforce_foundation import persistence_vitals as vitals  # noqa: E402
from pirateforce_foundation import persistence_typed_attrs as typed  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    _encode_character_name,
    make_actor_attr_with_name_and_class,
)
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

MIGRATIONS = ROOT / "migrations"
MIGRATION_007 = MIGRATIONS / "007_character_vitals_seed.sql"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: What the migration is supposed to leave behind, per COO-DECISION
#: 20260902_0250.  Only `MigrationTextTests` compares against these literals;
#: every other test derives its expectation from the shipped wire or from the
#: database, because a constant repeated in a test proves only that it was
#: repeated.
SEED = {"level": 1, "hp_current": 100, "hp_max": 100}

IDENTITY_LO, IDENTITY_HI = 0x30000001, 0
#: NOT ``SCENE_ID = 1``.  A ``pf-adversary`` pass measured what that costs:
#: the scene tag is ``u16tag(0x12, scene_id)`` (``player_wire.py:207``) and
#: the level tag is ``u16tag(0x12, level)`` (``:203``), so with scene 1 and
#: level 1 the two are the SAME THREE BYTES.  The per-tag test below then
#: passed over a `player_wire` with the level field DELETED, because the
#: scene tag alone satisfied it.  With a scene id that is not the seeded
#: level, each tag identifies its own field.
SCENE_ID, SCENE_SEQ = 42, 7
NAME = "SeedChar"


def _build_wire(selector):
    return b"wire", b"avatar", 0x30000001 + selector, 0


def _raw(path):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


class _MigratedDatabase(unittest.TestCase):
    """A database migrated to 006 with a real character in it, so that 007
    meets rows that already exist -- which is the only interesting case.

    Every raw connection is CLOSED rather than left to garbage collection:
    `TemporaryDirectory` cleanup raises `PermissionError [WinError 32]` on the
    Windows gate for a database that is still open, and this lane has lost
    pull requests to exactly that.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.upto006 = self.root / "migrations_upto_006"
        self.upto006.mkdir()
        for path in sorted(MIGRATIONS.glob("[0-9][0-9][0-9]_*.sql")):
            if path.name != MIGRATION_007.name:
                shutil.copy2(path, self.upto006 / path.name)
        self.path = self.root / "state.sqlite3"
        self.old = SQLiteStore(self.path, self.upto006)
        self.old.migrate()
        self.account_id = self.old.ensure_account("vitals-seed-007")
        self.home = Position(SCENE_ID, SCENE_SEQ, 11.0, 22.0, 33.0, heading=1.5)
        self.character = self.old.create_character(
            self.account_id, NAME, NAME.lower(),
            "fingerprint-vitals-seed-007", _build_wire, self.home,
        )

    def apply_007(self):
        SQLiteStore(self.path, MIGRATIONS).migrate()

    def vitals_on_disk(self, character_id=None):
        db = _raw(self.path)
        try:
            row = db.execute(
                "SELECT level,hp_current,hp_max FROM characters WHERE id=?",
                (character_id or self.character.id,),
            ).fetchone()
        finally:
            db.close()
        return {key: row[key] for key in ("level", "hp_current", "hp_max")}

    def soft_delete(self):
        sid = self.old.open_session(self.account_id)
        self.old.soft_delete_character(sid, self.character.selector)

    def dump(self, table):
        db = _raw(self.path)
        try:
            rows = db.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            return [{k: r[k] for k in r.keys()} for r in rows]
        finally:
            db.close()


class WireBytesMatchTests(_MigratedDatabase):
    """COO-DECISION 20260902_0250 point 1, measured rather than asserted.

    The claim is narrow and it is the whole point of the seed: the three
    numbers now in the database are the three numbers the login frame carries,
    in the same encoding, in the same order, in the same place.
    """

    def setUp(self):
        super().setUp()
        self.legacy = load_legacy(LEGACY_PATH)
        self.apply_007()

    def shipped_frame(self):
        return bytes(make_actor_attr_with_name_and_class(
            self.legacy, IDENTITY_LO, IDENTITY_HI, SCENE_ID, SCENE_SEQ, NAME,
        ))

    def bytes_from_database(self):
        """Encode the stored row the way the login frame encodes those fields.

        The order is not chosen here either: `vitals.VITAL_X` is (2, 3, 4) and
        the wire kinds come from `gm/attr_wire.FIELDS` through
        `persistence_typed_attrs`, so a field that moved would move here too.
        """
        stored = self.vitals_on_disk()
        self.assertEqual(
            [typed.TYPED_COLUMNS[c].kind for c in vitals.VITAL_COLUMNS],
            ["u16", "u32", "u32"],
        )
        return (
            self.legacy.u16tag(0x12, stored["level"])
            + self.legacy.u32tag(0x14, stored["hp_current"])
            + self.legacy.u32tag(0x14, stored["hp_max"])
        )

    def test_the_seeded_row_encodes_the_bytes_the_login_frame_carries(self):
        frame = self.shipped_frame()
        from_db = self.bytes_from_database()
        self.assertEqual(
            frame.count(from_db), 1,
            "the three tags must appear exactly once, or an offset proves nothing",
        )
        offset = frame.index(from_db)
        # NOT `frame[:offset+len] == frame[:offset] + from_db` -- that is true
        # of any byte string by the definition of `index`, and an assertion
        # that cannot fail is worse than no assertion.  The pin below is
        # positional: the name wstring ends immediately before these three
        # tags and the f32 movement-speed tag (0x2A) begins immediately after,
        # which is the layout `player_wire.py:201-206` writes.
        self.assertTrue(
            frame[:offset].endswith(bytes(_encode_character_name(self.legacy, NAME))),
            "the seeded tags are not sitting where the login frame puts them",
        )
        self.assertEqual(frame[offset + len(from_db)], 0x2A)

    def test_each_of_the_three_tags_is_the_shipped_one_on_its_own(self):
        """Each stored value on its own, and how often its tag may appear.

        The counts are asserted, not just membership: `hp_current` and
        `hp_max` are both `u32tag(0x14, 100)`, so that tag legitimately
        appears TWICE and a test demanding once would be wrong; `level` must
        appear exactly once, and it only can because `SCENE_ID` above is not
        the seeded level (see the comment there -- a `pf-adversary` pass got
        this test to pass over a wire carrying no level field at all).
        """
        stored = self.vitals_on_disk()
        frame = self.shipped_frame()
        self.assertEqual(
            frame.count(bytes(self.legacy.u16tag(0x12, stored["level"]))), 1,
            "level")
        self.assertEqual(
            frame.count(bytes(self.legacy.u32tag(0x14, stored["hp_current"]))), 2,
            "hp_current and hp_max are the same tag and both are 100")
        self.assertEqual(stored["hp_current"], stored["hp_max"])

    def test_a_different_seed_would_have_been_caught(self):
        """The comparison above can fail; here it does.

        Without this, `test_the_seeded_row_encodes...` would pass just as
        happily over a migration that wrote nothing at all if the encoder
        happened to produce a byte string the frame contains anyway.
        """
        db = _raw(self.path)
        try:
            db.execute("UPDATE characters SET hp_current=99 WHERE id=?",
                       (self.character.id,))
            db.commit()
        finally:
            db.close()
        frame = self.shipped_frame()
        self.assertNotIn(self.bytes_from_database(), frame)
        self.assertEqual(self.vitals_on_disk()["hp_current"], 99)


class SeedIsCorrectAndNarrowTests(_MigratedDatabase):
    """What 007 writes, and everything it refuses to write."""

    def test_a_row_that_was_all_null_gets_the_three_values(self):
        self.assertEqual(self.vitals_on_disk(),
                         {"level": None, "hp_current": None, "hp_max": None})
        self.apply_007()
        self.assertEqual(self.vitals_on_disk(), SEED)

    def test_nothing_outside_the_three_columns_changes(self):
        before = {t: self.dump(t) for t in
                  ("accounts", "characters", "character_positions",
                   "character_backpacks")}
        self.apply_007()
        after = {t: self.dump(t) for t in before}
        for table in ("accounts", "character_positions", "character_backpacks"):
            self.assertEqual(after[table], before[table], table)
        self.assertEqual(len(after["characters"]), 1)
        row, was = after["characters"][0], before["characters"][0]
        changed = {k for k in row if row[k] != was[k]}
        self.assertEqual(changed, set(SEED))
        for column in typed.TYPED_COLUMNS:
            if column not in SEED:
                self.assertIsNone(row[column],
                                  f"007 seeded {column}; it was approved for three")

    def test_a_row_that_already_has_values_is_left_alone(self):
        self.old.write_typed_attributes(
            self.character.id, {"level": 9, "hp_current": 50, "hp_max": 60})
        self.apply_007()
        self.assertEqual(self.vitals_on_disk(),
                         {"level": 9, "hp_current": 50, "hp_max": 60})

    def test_a_half_written_hp_pair_is_not_completed_by_guessing(self):
        """The row 007 refuses, and the reason it refuses it.

        `hp_max=50` with `hp_current` unset: a per-column seed would store
        `hp_current=100` over a maximum of 50 and build a character that
        `persistence_vitals` then refuses as `REASON_HP_ABOVE_MAX` -- damage
        broken by a repair.  So the pair is seeded as a pair or not at all.
        """
        self.old.write_typed_attributes(self.character.id, {"hp_max": 50})
        self.apply_007()
        after = self.vitals_on_disk()
        self.assertEqual(after["hp_max"], 50)
        self.assertIsNone(after["hp_current"])
        self.assertEqual(after["level"], 1, "level stands alone and is seeded")
        resolution = SQLiteStore(self.path, MIGRATIONS).read_character_vitals(
            self.character.id)
        self.assertFalse(resolution.complete)
        self.assertEqual({gap.reason for gap in resolution.gaps},
                         {vitals.REASON_NOT_SEEDED,
                          vitals.REASON_HP_PAIR_INCOMPLETE})

    def test_the_other_half_written_shape_is_also_left_alone(self):
        self.old.write_typed_attributes(self.character.id, {"hp_current": 30})
        self.apply_007()
        after = self.vitals_on_disk()
        self.assertEqual(after["hp_current"], 30)
        self.assertIsNone(after["hp_max"])

    def test_a_soft_deleted_row_is_seeded_too(self):
        self.soft_delete()
        self.apply_007()
        self.assertEqual(self.vitals_on_disk(), SEED)

    def test_a_character_created_after_007_is_still_unseeded(self):
        """The hole this migration does not close, pinned so it stays visible.

        `create_character` names its columns (`store.py:232`) and 006 built
        these three without a DEFAULT, so a new character is three gaps again
        and `apply_hp_damage` refuses it.  Asked in
        `pf_bridge/notes_to_chief/20260902_0420_LANE-DB-ASK-COO-new-characters
        -are-still-unseeded-after-007.md`; not decided by this lane.
        """
        self.apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        fresh = store.create_character(
            self.account_id, "AfterSeven", "afterseven",
            "fingerprint-after-007", _build_wire, self.home,
        )
        self.assertEqual(self.vitals_on_disk(fresh.id),
                         {"level": None, "hp_current": None, "hp_max": None})
        with self.assertRaises(vitals.VitalsError):
            store.apply_hp_damage(fresh.id, 1)

    def test_a_seeded_character_can_now_be_hit_and_killed(self):
        """M4's own sentence, measured: `ตีได้ตายได้` for a row 007 reached."""
        self.apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        state = store.read_character_vitals(self.character.id).require()
        self.assertEqual((state.level, state.hp_current, state.hp_max),
                         (SEED["level"], SEED["hp_current"], SEED["hp_max"]))
        outcome = store.apply_hp_damage(self.character.id, 40)
        self.assertEqual((outcome.hp_before, outcome.hp_after, outcome.applied),
                         (100, 60, 40))
        self.assertFalse(outcome.died)
        self.assertTrue(store.apply_hp_damage(self.character.id, 999).died)
        self.assertEqual(self.vitals_on_disk()["hp_current"], 0)


class LedgerTests(_MigratedDatabase):
    def test_007_is_recorded_and_re_running_changes_nothing(self):
        self.apply_007()
        db = _raw(self.path)
        try:
            applied = {int(r["version"]) for r in
                       db.execute("SELECT version FROM schema_migrations")}
        finally:
            db.close()
        self.assertIn(7, applied)
        self.old.write_typed_attributes(self.character.id, {"hp_current": 3})
        SQLiteStore(self.path, MIGRATIONS).migrate()
        self.assertEqual(self.vitals_on_disk()["hp_current"], 3,
                         "a second migrate() re-applied 007 over a live value")

    def test_a_server_without_007_refuses_the_migrated_database(self):
        self.apply_007()
        with self.assertRaises(RuntimeError):
            SQLiteStore(self.path, self.upto006).migrate()


class CensusAfter007Tests(_MigratedDatabase):
    """The numbers COO-DECISION 20260902_0250 point 2 asks for in the round
    file are produced HERE, by counting rows in a database, and this pins what
    those keys mean."""

    def test_the_census_counts_what_007_seeded(self):
        store = SQLiteStore(self.path, MIGRATIONS)
        self.apply_007()
        census = store.vitals_seeding_census()
        self.assertEqual(census["characters_any"], 1)
        self.assertEqual(census["characters_live"], 1)
        self.assertEqual(census["database"], str(self.path))
        for column in vitals.VITAL_COLUMNS:
            self.assertEqual(census[column + "_seeded_any"], 1, column)
            self.assertEqual(census[column + "_seeded_live"], 1, column)
        self.assertEqual(census["hp_pair_mixed_any"], 0)
        self.assertEqual(census["hp_pair_mixed_live"], 0)
        self.assertEqual(census["vitals_incomplete_any"], 0)
        self.assertEqual(census["vitals_incomplete_live"], 0)

    def test_a_row_007_skipped_is_counted_as_a_mixed_pair(self):
        self.old.write_typed_attributes(self.character.id, {"hp_max": 50})
        self.apply_007()
        census = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        self.assertEqual(census["hp_pair_mixed_any"], 1)
        self.assertEqual(census["hp_pair_mixed_live"], 1)
        self.assertEqual(census["hp_current_seeded_any"], 0)
        self.assertEqual(census["hp_max_seeded_any"], 1)
        self.assertEqual(census["vitals_incomplete_any"], 1)
        self.assertEqual(census["vitals_incomplete_live"], 1)

    def test_a_character_created_after_007_shows_up_as_incomplete(self):
        """The number that keeps "007 ran, everyone is fine" honest.

        `hp_pair_mixed_*` is 0 on a database where 007 reached every row it
        could -- and stays 0 as new, unseeded characters pile up behind it.
        `vitals_incomplete_*` is the count that moves.
        """
        self.apply_007()
        store = SQLiteStore(self.path, MIGRATIONS)
        self.assertEqual(store.vitals_seeding_census()["vitals_incomplete_live"], 0)
        store.create_character(
            self.account_id, "AfterSeven", "afterseven",
            "fingerprint-after-007-census", _build_wire, self.home,
        )
        census = store.vitals_seeding_census()
        self.assertEqual(census["hp_pair_mixed_live"], 0)
        self.assertEqual(census["vitals_incomplete_live"], 1)
        self.assertEqual(census["characters_live"], 2)

    def test_the_mixed_count_ignores_no_row_when_one_is_deleted(self):
        self.old.write_typed_attributes(self.character.id, {"hp_current": 7})
        self.soft_delete()
        self.apply_007()
        census = SQLiteStore(self.path, MIGRATIONS).vitals_seeding_census()
        self.assertEqual(census["hp_pair_mixed_any"], 1)
        self.assertEqual(census["hp_pair_mixed_live"], 0)


class BootSnapshotProtects007Tests(_MigratedDatabase):
    """007 is the first migration of this lane that WRITES INTO EXISTING ROWS,
    so the copy taken before it runs is not a formality -- it is the owner's
    only way back (`COO-DECISION 20260901_1112` point 3).  The mechanism lives
    in `store.migrate_with_backup` and both boot call sites already use it
    (`app.py:784`/`:787`); what is proved here is that it fires for THIS file
    on the real `migrations/` directory, and that what it leaves behind still
    holds the pre-seed row."""

    def test_a_snapshot_is_taken_before_007_and_restores_the_unseeded_row(self):
        from pirateforce_foundation.persistence_backup import should_snapshot

        take, reason = should_snapshot(self.path, MIGRATIONS)
        self.assertTrue(take)
        self.assertIn("007", reason)

        backups = self.root / "backups"
        snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
            backups_root=backups)
        self.assertIsNotNone(snapshot)
        self.assertEqual(self.vitals_on_disk(), SEED)

        copy = Path(snapshot)
        self.assertTrue(copy.exists())
        db = sqlite3.connect(copy)
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT level,hp_current,hp_max FROM characters WHERE id=?",
                (self.character.id,),
            ).fetchone()
        finally:
            db.close()
        self.assertEqual(
            {k: row[k] for k in ("level", "hp_current", "hp_max")},
            {"level": None, "hp_current": None, "hp_max": None},
            "the copy taken before 007 already contains 007's writes",
        )


    def test_the_copy_survives_a_hot_write_ahead_log(self):
        """The state a boot really finds, not the tidy one.

        A killed server leaves rows committed into `-wal` that SQLite has not
        checkpointed into the database file.  A `shutil.copyfile` backup loses
        exactly those rows, and a test that lets every connection close first
        cannot tell the difference -- `BootSnapshotProtects006Tests` in
        `tests/test_persistence_typed_attr_columns.py` learned that from a
        `pf-adversary` pass, and another one pointed out that after the
        migrations directory was sliced by version, THIS file is the only
        place that still runs the hot case against the real `migrations/`.
        """
        holder = sqlite3.connect(str(self.path))
        try:
            holder.execute("PRAGMA journal_mode=WAL")
            holder.execute("BEGIN IMMEDIATE")
            holder.execute(
                "UPDATE characters SET name_key=? WHERE id=?",
                ("hotwalseed", self.character.id))
            holder.commit()
            self.assertTrue(
                self.path.with_name(self.path.name + "-wal").exists(),
                "this test is only worth anything with a hot -wal; there is none",
            )
            snapshot = SQLiteStore(self.path, MIGRATIONS).migrate_with_backup(
                backups_root=self.root / "backups")
        finally:
            holder.close()

        self.assertIsNotNone(snapshot)
        db = sqlite3.connect(str(snapshot))
        db.row_factory = sqlite3.Row
        try:
            row = db.execute(
                "SELECT name_key,level,hp_current,hp_max FROM characters "
                "WHERE id=?", (self.character.id,)).fetchone()
        finally:
            db.close()
        # The uncheckpointed write is IN the copy ...
        self.assertEqual(row["name_key"], "hotwalseed")
        # ... and 007's writes are NOT: the copy predates the seed.
        self.assertEqual(
            (row["level"], row["hp_current"], row["hp_max"]), (None, None, None))
        self.assertEqual(self.vitals_on_disk(), SEED)


class MigrationTextTests(unittest.TestCase):
    """What the file may contain, read as text.

    A statement scan is a weak instrument -- this lane replaced one with a row
    count for exactly that reason -- so it is used here only for what it can
    actually decide: that no statement of a shape this migration was not
    approved for is present at all.  The behaviour is measured above.
    """

    def setUp(self):
        self.text = MIGRATION_007.read_text(encoding="utf-8")
        self.statements = [
            s.strip() for s in
            re.sub(r"^\s*--.*$", "", self.text, flags=re.M).split(";")
            if s.strip()
        ]

    def test_the_transcription_label_coo_required_is_present(self):
        self.assertIn(
            "TRANSCRIBED from player_wire hardcode -- original game default OPEN",
            self.text,
        )

    def test_every_statement_is_a_guarded_update_of_characters(self):
        self.assertEqual(len(self.statements), 2)
        for statement in self.statements:
            upper = " ".join(statement.upper().split())
            self.assertTrue(upper.startswith("UPDATE CHARACTERS SET "), upper)
            self.assertIn(" IS NULL", upper)
            # WORD boundaries, not substrings.  `DELETE` is a substring of
            # `DELETED_AT`, so the substring version of this test would have
            # refused the first migration in this family that wants a
            # `deleted_at IS NULL` guard -- red for a reason that has nothing
            # to do with what the statement does.
            for forbidden in ("DELETE", "DROP", "INSERT", "REPLACE", "TRIGGER",
                              "ALTER", "ATTACH", "PRAGMA", "VACUUM", "JOIN"):
                self.assertIsNone(
                    re.search(r"\b%s\b" % forbidden, upper), statement)

    def test_the_file_names_only_the_three_approved_columns(self):
        """Every column ASSIGNED by the file, cut out of the SET clause.

        The first version of this test used two regexes over the whole text,
        the second of which required a NEWLINE after the comma.  A
        `pf-adversary` pass put `SET level = 1, mp_current = 0, mp_max = 0` on
        ONE line -- two guessed zeros on live rows, the exact shape the owner's
        rule bans -- and this test stayed green.  Now the SET clause is cut out
        and every assignment in it is read, whatever the whitespace.
        """
        assigned = set()
        for statement in self.statements:
            body = re.split(r"\bWHERE\b", statement, maxsplit=1,
                            flags=re.I)[0]
            body = re.split(r"\bSET\b", body, maxsplit=1, flags=re.I)[1]
            for part in body.split(","):
                name, _, value = part.partition("=")
                self.assertTrue(value.strip(), part)
                assigned.add(name.strip())
        self.assertEqual(assigned, set(SEED))

    def test_it_is_cp874_encodable(self):
        # The bridge writes these files through a cp874 console; a character
        # that cannot round-trip there is a boot failure on the owner's
        # machine, not a cosmetic problem.
        self.text.encode("cp874")


if __name__ == "__main__":
    unittest.main()
