import dataclasses
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.lifecycle import CharacterLifecycle
from pirateforce_foundation.model import Position
from pirateforce_foundation.store import SQLiteStore
from pirateforce_foundation.world_scene_travel import (
    SceneRegistry, load_scene_registry)


def _build_wire(selector):
    return b"wire", b"avatar", 0x10000001 + selector, 0


class LifecyclePersistPositionGateTest(unittest.TestCase):
    """CORE-REQUEST-018 / GT-106 (4).3: a character whose CURRENT scene is
    pinned persist_position_allowed=False must not have its
    character_positions row overwritten -- GT-106 caught a real character
    coming out of scene 17 with scene_id=1 and scene 17's XYZ written back, a
    row nobody chose and wrong on both columns.  checkpoint() and exit() are
    the only two callers of store.save_position in this codebase; both must
    honor the gate.

    ~~(today: only scene 17, which has no measured return path)~~ -- STRUCK,
    LANE-A round 9lv3fa, 2026-09-08.  PANYA-DECISION 20260908_1218 lifted the
    last two pins (14 and 17), so the SHIPPED registry now writes everywhere,
    and the two tests that used scene 17 as the pinned scene use a synthetic
    pinned registry instead.  That is the stronger test either way: it holds
    whatever the shipped registry says, and it is what keeps this gate under
    test for a destination pinned False in future.

    WHAT SCENE 17 PROVES NOW, in test_checkpoint_writes_scene_17_on_both_
    columns: the write GT-106 caught being wrong is right.  The row that
    lands reads scene_id=17 with scene 17's own XYZ - not GT-106's
    scene_id=1-carrying-17's-coordinates, which is the pair that made the
    original row wrong twice over.  Under 1218 that row is what puts the
    character back on the deck it logged out from -- HALF OF IT.  Writing
    the right row is this file's whole subject and is necessary; it was
    never sufficient, and saying so flatly here was an overclaim for two
    rounds (pf-adversary D1, round 3a11a0: the row was written correctly
    and the character still arrived on (0,0,0)).  What reads the row back
    without discarding it is ``world_scene_entry._ground_refutes_stored_row``
    and the login-door test that now asserts the arrival equals the stored
    point; this file does not test that and must not be cited for it."""

    @staticmethod
    def _registry_with_scene_17_pinned_shut():
        real = load_scene_registry()
        return SceneRegistry(destinations=tuple(
            dataclasses.replace(d, persist_position_allowed=False)
            if d.n_id == 17 else d
            for d in real.destinations))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.home = Position(1, 0, 100.0, 200.0, 300.0, heading=1.5)
        self.lifecycle = CharacterLifecycle(self.store, self.home)
        self.account_id = self.store.ensure_account("persist-gate-test")
        self.sid = self.store.open_session(self.account_id)
        self.character = self.store.create_character(
            self.account_id, "PersistGateTest", "persistgatetest",
            "fingerprint-persist-gate", _build_wire, self.home,
        )
        self.store.select_character(self.sid, self.character.selector)
        self.addCleanup(self.tmp.cleanup)

    def _stored_position(self):
        return self.store.get_character(self.character.id).position

    def test_checkpoint_writes_through_for_an_unpinned_scene(self):
        moved = Position(1, 0, 111.0, 222.0, 333.0, heading=2.0)
        self.lifecycle.checkpoint(self.sid, self.character, moved)
        self.assertEqual(self._stored_position(), moved)

    def test_checkpoint_writes_scene_17_on_both_columns(self):
        """PANYA-DECISION 20260908_1218 at the write path.

        The assertion is deliberately on the WHOLE Position: GT-106's row was
        wrong because the scene column and the coordinate columns disagreed,
        and a test that checked only "something was written" would have
        passed for that row too.
        """
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        self.lifecycle.checkpoint(self.sid, self.character, into_scene_17)
        self.assertEqual(self._stored_position(), into_scene_17)
        self.assertNotEqual(self._stored_position().scene_id, 1)

    def test_checkpoint_skips_the_write_for_a_pinned_scene(self):
        self.lifecycle._scene_registry = (
            self._registry_with_scene_17_pinned_shut())
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        self.lifecycle.checkpoint(self.sid, self.character, into_scene_17)
        # The row must stay exactly what it was before this checkpoint --
        # not scene_id=1 with scene 17's XYZ (GT-106's bug), and not
        # scene_id=17 either, because this registry pins the scene shut.
        self.assertEqual(self._stored_position(), self.home)

    def test_checkpoint_resumes_writing_once_back_in_an_unpinned_scene(self):
        self.lifecycle._scene_registry = (
            self._registry_with_scene_17_pinned_shut())
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        self.lifecycle.checkpoint(self.sid, self.character, into_scene_17)
        self.assertEqual(self._stored_position(), self.home)
        back_home = Position(1, 0, 5.0, 6.0, 7.0, heading=3.0)
        self.lifecycle.checkpoint(self.sid, self.character, back_home)
        self.assertEqual(self._stored_position(), back_home)

    def test_exit_skips_the_write_for_a_pinned_scene_but_still_closes(self):
        self.lifecycle._scene_registry = (
            self._registry_with_scene_17_pinned_shut())
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        self.lifecycle.exit(self.sid, self.character, into_scene_17)
        self.assertEqual(self._stored_position(), self.home)
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (self.sid,),
            ).fetchone()
        self.assertIsNotNone(row["closed_at"])

    def test_exit_writes_through_and_closes_for_an_unpinned_scene(self):
        moved = Position(1, 0, 9.0, 8.0, 7.0, heading=0.5)
        self.lifecycle.exit(self.sid, self.character, moved)
        self.assertEqual(self._stored_position(), moved)
        with self.store.connect() as db:
            row = db.execute(
                "SELECT closed_at FROM sessions WHERE id=?", (self.sid,),
            ).fetchone()
        self.assertIsNotNone(row["closed_at"])

    def test_checkpoint_still_detects_a_stale_session_even_in_scene_17(self):
        """pf-adversary finding 1: skipping the write for a gated scene must
        not also skip the ownership/staleness check store.save_position
        normally performs -- that EXISTS check is this project's only
        detection signal for a stolen/superseded lease (see
        reports/PF_MULTIPLAYER_READINESS_AUDIT001_*). Opening a second
        session for the same account closes the first one (single-session
        lease takeover, store.open_session); a checkpoint on the now-stale
        first session id must still raise, scene 17 or not."""
        stale_sid = self.sid
        self.store.open_session(self.account_id)  # closes stale_sid's lease
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        with self.assertRaises(PermissionError):
            self.lifecycle.checkpoint(stale_sid, self.character, into_scene_17)
        # And the row is untouched either way -- not because of the gate
        # this time, but because the write never happens on a stale session.
        self.assertEqual(self._stored_position(), self.home)

    def test_exit_still_detects_a_stale_session_even_in_scene_17(self):
        stale_sid = self.sid
        self.store.open_session(self.account_id)  # closes stale_sid's lease
        into_scene_17 = Position(17, 0, -149.0, -1250.3, 745.0, heading=0.0)
        with self.assertRaises(PermissionError):
            self.lifecycle.exit(stale_sid, self.character, into_scene_17)
        self.assertEqual(self._stored_position(), self.home)


if __name__ == "__main__":
    unittest.main()
