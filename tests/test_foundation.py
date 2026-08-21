import hashlib
import json
import math
import socket
import sqlite3
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

# One test below reads the original schema out of git history, which a shallow
# clone does not carry.  Round 118 measured that as a hard failure on an
# untouched main.  See tests/pf_preconditions.py.
from pf_preconditions import (  # noqa: E402
    ORIGINAL_SCHEMA_COMMIT,
    ORIGINAL_SCHEMA_HISTORY,
)

from pirateforce_foundation.actor_wire import read_identity, read_selector
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.player_wire import make_actor_attr_with_name
from pirateforce_foundation.session import FoundationSession
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.runtime import make_state_class

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
EXPECTED_V141 = "2eb05ed2fdbdd5ee3d91f7fbb8c1d16a4c7a02a843bc97169b16a389e4ea4c22"

class FoundationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "state.sqlite3"
        self.store = SQLiteStore(self.db_path, ROOT / "migrations")
        self.store.migrate(); self.store.migrate()
        self.legacy = load_legacy(LEGACY_PATH)
        self.projector = LegacyProjector(self.legacy)
        self.default = Position(1, 0, self.legacy.V135_PLAYER_X, self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z)
        self.lifecycle = CharacterLifecycle(self.store, self.default, self.legacy.extract_avatar_attr_wire_from_actor)

    def tearDown(self): self.tmp.cleanup()

    def preset(self, name="test01"):
        actor = self.legacy.get_preset_actor_wire()
        old = self.legacy.wstr_tag("test01")
        if name == "test01":
            return actor
        self.assertEqual(actor.count(old), 1)
        return actor.replace(old, self.legacy.wstr_tag(name), 1)

    def test_v141_characterization_hash(self):
        self.assertEqual(hashlib.sha256(LEGACY_PATH.read_bytes()).hexdigest(), EXPECTED_V141)

    def test_create_list_select_start_same_identity(self):
        s = FoundationSession(self.lifecycle, self.projector, "test01")
        c, (_, create_frame) = s.create("test01", self.preset())
        self.assertEqual(read_identity(c.actor_wire), (c.identity_lo, c.identity_hi))
        self.assertEqual(read_selector(c.actor_wire), c.selector)
        (_, list_frame) = s.character_list()
        selected, (pc, start_frame) = s.select_and_start(c.selector)
        ident = bytes([0x32]) + c.identity_lo.to_bytes(4,"little") + c.identity_hi.to_bytes(4,"little")
        self.assertEqual(selected.id, c.id)
        self.assertEqual(c.actor_wire.count(ident), 2)  # Actor object + embedded AvatarAttr.
        self.assertEqual(c.avatar_wire[3:11], ident[1:])
        self.assertEqual(pc.count(ident), 3)  # ActorAttr + AvatarAttr + MovementAttr.
        self.assertIn(c.avatar_wire, pc)
        self.assertIn(c.actor_wire, list_frame)
        self.assertIn(c.actor_wire, create_frame)
        name_wire = self.legacy.wstr_tag(c.name)
        self.assertEqual(pc.count(name_wire), 1)
        expected_actor = make_actor_attr_with_name(
            self.legacy, c.identity_lo, c.identity_hi,
            c.position.scene_id, c.position.scene_seq, c.name,
        )
        self.assertIn(expected_actor, pc)
        self.assertTrue(start_frame)

    def test_character_lifecycle_golden_hashes(self):
        golden = json.loads((ROOT/'tests/golden/foundation_v1.json').read_text())
        s = FoundationSession(self.lifecycle, self.projector, "golden")
        c, (create_pc, _) = s.create("test01", self.preset())
        list_pc, _ = s.character_list(); _, (start_pc, start_frame) = s.select_and_start(c.selector)
        actual = {"actor_wire_sha256":hashlib.sha256(c.actor_wire).hexdigest().upper(),
                  "create_pc_sha256":hashlib.sha256(create_pc).hexdigest().upper(),
                  "list_pc_sha256":hashlib.sha256(list_pc).hexdigest().upper(),
                  "start_pc_sha256":hashlib.sha256(start_pc).hexdigest().upper(),
                  "start_frame_sha256":hashlib.sha256(start_frame).hexdigest().upper()}
        self.assertEqual(actual, golden)

    def test_exit_restart_load_position(self):
        s = FoundationSession(self.lifecycle, self.projector, "restart")
        c, _ = s.create("restart", self.preset("restart")); s.select_and_start(c.selector)
        saved = Position(1, 0, -10001.25, -700.5, 671.0, 1.25)
        s.close(saved)
        reopened = SQLiteStore(self.db_path, ROOT / "migrations"); reopened.migrate()
        s2 = FoundationSession(CharacterLifecycle(reopened, self.default, self.legacy.extract_avatar_attr_wire_from_actor), self.projector, "restart")
        c2, (pc, _) = s2.select_and_start(c.selector)
        self.assertEqual((c2.identity_lo,c2.identity_hi), (c.identity_lo,c.identity_hi))
        self.assertEqual(c2.actor_wire, c.actor_wire)
        self.assertEqual(c2.position, saved)
        self.assertIn(self.legacy.f32tag(saved.x), pc)
        self.assertIn(self.legacy.f32tag(saved.heading), pc)

    def test_zero_heading_projection_is_legacy_byte_exact(self):
        s = FoundationSession(self.lifecycle, self.projector, "zero-heading")
        c, _ = s.create("zero-heading", self.preset("zero-heading"))
        expected = self.legacy.make_movement_attr_minimal(
            c.identity_lo, c.identity_hi,
            c.position.x, c.position.y, c.position.z,
        )
        self.assertEqual(self.projector.movement_attr(c), expected)

    def test_loopback_exact_frame(self):
        s = FoundationSession(self.lifecycle, self.projector, "loopback")
        c, _ = s.create("loopback", self.preset("loopback"))
        expected = s.character_list()[1]
        left, right = socket.socketpair()
        def server():
            self.assertEqual(left.recv(1), bytes([c.selector])); left.sendall(expected); left.close()
        t = threading.Thread(target=server); t.start()
        right.sendall(bytes([c.selector])); got = bytearray()
        while len(got) < len(expected): got += right.recv(len(expected)-len(got))
        right.close(); t.join()
        self.assertEqual(bytes(got), expected)

    def test_real_v141_dispatch_lifecycle(self):
        state_type = make_state_class(self.legacy, self.lifecycle, self.projector)
        state = state_type("dispatch")
        login = self.legacy.parse_outer(self.legacy._synthetic_client_login_pc())
        actions = state.dispatch(login)
        self.assertEqual([a[0] for a in actions], ["LOGIN_VERIFY_ACK_ONCE", "FOUNDATION_CHARACTER_LIST_ONCE"])
        create = self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        created = state.dispatch(create)
        self.assertEqual(created[0][0], "FOUNDATION_CREATE_COMMITTED")
        c = self.store.list_characters(state.foundation.account_id)[0]
        start = self.legacy.parse_outer(self.legacy._synthetic_start_game_pc(c.selector))
        entered = state.dispatch(start)
        self.assertEqual([a[0] for a in entered], [
            "FOUNDATION_SELECTED_START_GAME",
            "V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE",
        ])
        self.assertTrue(state.teleport_sent)
        self.assertIn("start_game_res_scene_identity_sent", state.events)

        target_pc = (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(-10001.25)
            + self.legacy.f32tag(-700.5)
            + self.legacy.f32tag(671.0)
            + self.legacy.f32tag(1.25)
            + self.legacy.u8tag(0x0B, 1)
            + self.legacy.u8tag(0x0B, 0)
        )
        state.dispatch(self.legacy.parse_outer(target_pc))
        persisted = self.store.get_character(c.id)
        self.assertEqual(
            persisted.position,
            Position(1, 0, -10001.25, -700.5, 671.0, 1.25),
        )

        malformed = self.legacy.parse_outer(target_pc)
        malformed.vital_count = 2
        malformed.nested_payload = (
            self.legacy.f32tag(100.0)
            + self.legacy.f32tag(200.0)
            + self.legacy.f32tag(300.0)
            + self.legacy.f32tag(2.0)
            + self.legacy.u8tag(0x0B, 1)
            + self.legacy.u8tag(0x0B, 0)
        )
        state.dispatch(malformed)
        self.assertEqual(self.store.get_character(c.id).position, persisted.position)

    def test_malformed_create_is_strict_no_reply(self):
        state = make_state_class(self.legacy, self.lifecycle, self.projector)("bad-create")
        parsed = self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        parsed.nested_payload = parsed.nested_payload[:6]
        self.assertEqual(state.dispatch(parsed), [])
        self.assertIn("foundation_create_rejected_no_reply", state.events)
        self.assertEqual(self.store.list_characters(state.foundation.account_id), [])

    def test_retry_multi_character_and_account_isolation(self):
        one = FoundationSession(self.lifecycle, self.projector, "account-one")
        c1, _ = one.create("test01", self.preset())
        retry, _ = one.create("test01", self.preset())
        self.assertEqual(retry.id, c1.id)
        actor2 = self.preset("test02")
        c2, _ = one.create("test02", actor2)
        self.assertEqual((c1.selector, c2.selector), (0, 1))
        self.assertEqual(len(one.character_list()[0]) > 0, True)

        other = FoundationSession(self.lifecycle, self.projector, "account-two")
        with self.assertRaises(KeyError):
            other.select_and_start(c1.selector)

    def test_new_session_revokes_stale_position_writer(self):
        first = FoundationSession(self.lifecycle, self.projector, "lease")
        character, _ = first.create("lease", self.preset("lease"))
        first.select_and_start(character.selector)
        second = FoundationSession(self.lifecycle, self.projector, "lease")
        second.select_and_start(character.selector)
        with self.assertRaises(PermissionError):
            first.checkpoint(Position(1, 0, 1.0, 2.0, 3.0, 0.0))
        second.checkpoint(Position(1, 0, 4.0, 5.0, 6.0, 0.5))
        self.assertEqual(self.store.get_character(character.id).position.x, 4.0)

    def test_position_rejects_nonfinite(self):
        session = FoundationSession(self.lifecycle, self.projector, "finite")
        character, _ = session.create("finite", self.preset("finite"))
        session.select_and_start(character.selector)
        with self.assertRaises(ValueError):
            session.checkpoint(Position(1, 0, math.nan, 0.0, 0.0, 0.0))

    def test_migration_atomicity_and_checksum(self):
        bad_dir = Path(self.tmp.name) / "bad-migrations"
        bad_dir.mkdir()
        (bad_dir / "001_bad.sql").write_text(
            "CREATE TABLE survived(id INTEGER);\nTHIS IS INVALID;", encoding="utf-8"
        )
        bad_db = Path(self.tmp.name) / "bad.sqlite3"
        with self.assertRaises(sqlite3.OperationalError):
            SQLiteStore(bad_db, bad_dir).migrate()
        db = sqlite3.connect(bad_db)
        try:
            self.assertIsNone(db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='survived'"
            ).fetchone())
        finally:
            db.close()

        good_dir = Path(self.tmp.name) / "good-migrations"
        shutil.copytree(ROOT / "migrations", good_dir)
        good_db = Path(self.tmp.name) / "good.sqlite3"
        SQLiteStore(good_db, good_dir).migrate()
        migration = good_dir / "001_initial.sql"
        migration.write_text(migration.read_text(encoding="utf-8") + "\n-- changed\n", encoding="utf-8")
        with self.assertRaises(RuntimeError):
            SQLiteStore(good_db, good_dir).migrate()

    def test_upgrade_from_original_foundation_schema(self):
        # The original schema exists only in git history, so this test needs a
        # clone deep enough to hold it.  On a shallow clone the git call used
        # to die with a bare CalledProcessError, which reads as "main is red"
        # when nothing is wrong with main at all.  See tests/pf_preconditions.py.
        ORIGINAL_SCHEMA_HISTORY.require(self)
        legacy_db = Path(self.tmp.name) / "legacy.sqlite3"
        original_sql = subprocess.run(
            ["git", "show", ORIGINAL_SCHEMA_COMMIT + ":migrations/001_initial.sql"],
            cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
        db = sqlite3.connect(legacy_db)
        try:
            db.executescript(original_sql)
            db.execute(
                "INSERT INTO schema_migrations(version,applied_at) VALUES (1,'legacy')"
            )
            db.execute("INSERT INTO accounts VALUES (1,'legacy','legacy')")
            db.execute(
                "INSERT INTO characters VALUES (1,1,0,'old',X'01',X'02',NULL,1,0,'legacy','legacy',NULL)"
            )
            db.execute(
                "INSERT INTO characters VALUES (2,1,1,'old',X'03',X'04',NULL,2,0,'legacy','legacy',NULL)"
            )
            db.execute(
                "INSERT INTO characters VALUES (3,1,2,'gone',X'05',X'06',NULL,3,0,'legacy','legacy','deleted')"
            )
            db.execute(
                "INSERT INTO character_positions VALUES (1,1,0,10.0,20.0,30.0,'legacy')"
            )
            db.execute(
                "INSERT INTO character_positions VALUES (2,1,0,40.0,50.0,60.0,'legacy')"
            )
            db.execute(
                "INSERT INTO character_positions VALUES (3,1,0,70.0,80.0,90.0,'legacy')"
            )
            db.commit()
        finally:
            db.close()
        upgraded = SQLiteStore(legacy_db, ROOT / "migrations")
        upgraded.migrate()
        with upgraded.connect() as db:
            versions = db.execute(
                "SELECT version,checksum FROM schema_migrations ORDER BY version"
            ).fetchall()
            self.assertEqual([int(row[0]) for row in versions], [1, 2, 3, 4])
            self.assertTrue(all(row[1] for row in versions))
            row = db.execute(
                "SELECT name_key,create_fingerprint FROM characters WHERE id=1"
            ).fetchone()
            self.assertEqual(tuple(row), ("old", "legacy:1"))
            duplicate = db.execute(
                "SELECT name,name_key FROM characters WHERE deleted_at IS NULL ORDER BY id"
            ).fetchall()
            self.assertEqual([tuple(row) for row in duplicate], [("old", "old"), ("old", "old")])
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM character_backpacks").fetchone()[0],
                2,
            )
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM character_backpack_items").fetchone()[0],
                8,
            )
            self.assertIsNone(db.execute(
                "SELECT 1 FROM character_backpacks WHERE character_id=3"
            ).fetchone())
            self.assertEqual(
                db.execute("SELECT heading FROM character_positions WHERE character_id=1").fetchone()[0],
                0.0,
            )

if __name__ == "__main__": unittest.main()
