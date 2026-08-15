import hashlib
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pirateforce_foundation.actor_wire import read_identity, read_selector
from pirateforce_foundation.legacy_bridge import LegacyProjector, load_legacy
from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
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

    def preset(self): return self.legacy.get_preset_actor_wire()

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
        self.assertEqual(pc.count(ident), 2)  # ActorAttr + MovementAttr; opaque AvatarAttr has no identity bit.
        self.assertIn(c.avatar_wire, pc)
        self.assertIn(c.actor_wire, list_frame)
        self.assertIn(c.actor_wire, create_frame)
        self.assertNotIn("test01".encode("utf-16le"), pc)
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
        c, _ = s.create("restart", self.preset()); s.select_and_start(c.selector)
        saved = Position(1, 0, -10001.25, -700.5, 671.0)
        s.close(saved)
        reopened = SQLiteStore(self.db_path, ROOT / "migrations"); reopened.migrate()
        s2 = FoundationSession(CharacterLifecycle(reopened, self.default, self.legacy.extract_avatar_attr_wire_from_actor), self.projector, "restart")
        c2, (pc, _) = s2.select_and_start(c.selector)
        self.assertEqual((c2.identity_lo,c2.identity_hi), (c.identity_lo,c.identity_hi))
        self.assertEqual(c2.actor_wire, c.actor_wire)
        self.assertEqual(c2.position, saved)
        self.assertIn(self.legacy.f32tag(saved.x), pc)

    def test_loopback_exact_frame(self):
        s = FoundationSession(self.lifecycle, self.projector, "loopback")
        c, _ = s.create("loopback", self.preset())
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
        self.assertEqual(entered[0][0], "FOUNDATION_SELECTED_START_GAME")

if __name__ == "__main__": unittest.main()
