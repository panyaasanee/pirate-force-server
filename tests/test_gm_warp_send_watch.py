"""`CORE-REQUEST-GM-057`'s own half: `gm/warp_send_watch.py`.

The module this pins is the piece of `#745`'s send-failure window this lane
can build without chief -- `pf_bridge/notes_to_chief/20260905_0121_LANE-GM-
CORE-REQUEST-GM-057-send-failure-observer.md` asks chief for exactly one
`connection.py` hookup, and none of what follows depends on it existing yet.

THREE THINGS THIS FILE PROVES:

1. THE PARK IS WIRED IN, at the ONE real call site
   (`chat_command_action._warp_teleport_action_no_coords`), through the
   REAL router, the REAL store and a REAL composed frame -- not a fake
   session with a fake `frame_bytes` this module invented for itself.
2. THE SUCCESS SIDE COMPARES BYTES.  An unrelated frame going out first does
   not clear a still-unconfirmed park; the warp's own bytes do.
3. THE FAILURE SIDE DOES NOT NEED A MATCH, AND THAT IS THE POINT.  The
   scenario `CORE-REQUEST-GM-057` names by name -- v141's send loop
   `break`s the whole action list on the FIRST failed frame, so a warp
   parked behind an EARLIER frame in the same batch can be orphaned by that
   earlier frame's failure without the warp's own bytes ever reaching
   `sendall` at all.  `RealDatabaseTests.
   test_an_earlier_unrelated_frames_failure_still_rolls_back_the_parked_warp`
   reproduces exactly that shape and checks the row, not only the return
   word.

NONCLAIM.  Headless, server-side, no client involved.  Nothing here is
evidence about a screen, a socket, or `GT-172` F-3; no account gains or
loses GM status, and no GM step is skipped -- every assertion below is
about a session attribute and a database row.  `on_game_frame_sent` /
`on_game_frame_send_failed` are proven callable and correct here, but
NOTHING calls them outside this file and `chat_command_action.py`'s own
compose-time park until chief's `connection.py` line lands -- see this
module's own docstring.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command_action,
    dispatch as gm_dispatch,
    login_scene_override,
    warp_scene_persist,
    warp_send_watch,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: Prison Exile: marker-backed, `login_entry_allowed` true -- the same
#: destination every sibling warp-scene test file uses.
DESTINATION_SCENE = 2

#: Pinned `login_entry_allowed=False`, so the forward write refuses it and
#: `_persist_warp_scene` never reaches `OUTCOME_PERSISTED` at all.
REFUSED_SCENE = 126


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload -- copied, not imported, per this house's own rule
    that no test file imports test helpers from another one."""
    import struct

    from pirateforce_foundation.gm import chat_command as gm_chat_command

    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(gm_chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


class _FakePosition:
    def __init__(self, scene_id=2, x=0.0, y=0.0, z=0.0):
        self.scene_id = scene_id
        self.x = x
        self.y = y
        self.z = z


class _FakeSelected:
    def __init__(self, position=None):
        self.position = position


class _FakeFoundation:
    def __init__(self, selected=None):
        self.selected = selected


class _FakeSession:
    """The two attributes `warp_send_watch` reads/writes, nothing more."""

    def __init__(self):
        self.foundation = _FakeFoundation(_FakeSelected(_FakePosition()))
        self.events = []


class _RefusingSession:
    """A session whose relevant attribute never changes no matter what is
    assigned to it -- `setattr` does not raise, but the write is silently
    lost.  Same shape `warp_target_record.py`'s own tests use for the
    identical finding: `setattr` not raising is not evidence the value
    landed, and a fixture that returns `None` from `__getattr__` regardless
    would coincidentally look like a successful CLEAR every time, which
    proves nothing about a write that was actually swallowed.
    """

    def __init__(self):
        object.__setattr__(self, warp_send_watch.SESSION_ATTRIBUTE, "unchanged")

    def __setattr__(self, name, value):
        pass


class ParkAndClearUnitTests(unittest.TestCase):
    """The cell itself, against a fake session -- no store, no legacy."""

    def test_park_records_the_exact_bytes_and_the_one_label(self):
        session = _FakeSession()
        self.assertTrue(warp_send_watch.park_warp_send(session, b"\x01\x02\x03"))
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertEqual(record.frame_bytes, b"\x01\x02\x03")
        self.assertEqual(
            record.label, warp_scene_persist.SEND_FAILURE_WARP_ACTION_LABEL,
        )

    def test_park_accepts_a_bytearray_and_normalises_to_bytes(self):
        session = _FakeSession()
        self.assertTrue(
            warp_send_watch.park_warp_send(session, bytearray(b"\x09\x0a")),
        )
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsInstance(record.frame_bytes, bytes)
        self.assertEqual(record.frame_bytes, b"\x09\x0a")

    def test_park_refuses_an_object_with_no_bytes_conversion(self):
        session = _FakeSession()
        self.assertFalse(warp_send_watch.park_warp_send(session, object()))
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None))

    def test_park_never_raises_on_a_session_that_swallows_the_write(self):
        session = _RefusingSession()
        self.assertFalse(warp_send_watch.park_warp_send(session, b"\x00"))

    def test_a_second_park_replaces_the_first(self):
        """Same reasoning as `warp_target_record.record_warp_target`: a
        second persisted warp means the FIRST frame's fate no longer bears
        on the row, which has already moved again."""
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"first-frame")
        warp_send_watch.park_warp_send(session, b"second-frame")
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertEqual(record.frame_bytes, b"second-frame")

    def test_clear_empties_the_cell_and_confirms_by_readback(self):
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"frame")
        self.assertTrue(warp_send_watch.clear_warp_send_watch(session))
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_clear_on_an_already_empty_cell_still_confirms_true(self):
        session = _FakeSession()
        self.assertTrue(warp_send_watch.clear_warp_send_watch(session))

    def test_clear_never_raises_on_a_session_that_swallows_the_write(self):
        session = _RefusingSession()
        self.assertFalse(warp_send_watch.clear_warp_send_watch(session))


class OnGameFrameSentTests(unittest.TestCase):
    """The success side.  Byte comparison decides everything."""

    def test_nothing_parked_costs_nothing_and_touches_no_state(self):
        session = _FakeSession()
        outcome = warp_send_watch.on_game_frame_sent(session, b"anything")
        self.assertEqual(outcome, warp_send_watch.OUTCOME_NOTHING_PARKED)
        self.assertEqual(session.events, [])

    def test_a_matching_frame_clears_the_park(self):
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        outcome = warp_send_watch.on_game_frame_sent(session, b"the-warp-frame")
        self.assertEqual(outcome, warp_send_watch.OUTCOME_CLEARED_OWN_FRAME)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_a_different_frame_leaves_the_park_in_place(self):
        """An unrelated frame reaching the wire first must not report the
        warp's own row as confirmed reachable."""
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        outcome = warp_send_watch.on_game_frame_sent(session, b"a-say-frame")
        self.assertEqual(outcome, warp_send_watch.OUTCOME_LEFT_PARKED_OTHER_FRAME)
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertEqual(record.frame_bytes, b"the-warp-frame")

    def test_an_unbytesable_argument_leaves_the_park_in_place(self):
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        outcome = warp_send_watch.on_game_frame_sent(session, object())
        self.assertEqual(outcome, warp_send_watch.OUTCOME_LEFT_PARKED_OTHER_FRAME)
        self.assertIsNotNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))


class OnGameFrameSendFailedTests(unittest.TestCase):
    """The failure side.  No byte comparison -- only "is the cell empty"."""

    def test_nothing_parked_costs_nothing_and_never_calls_the_rollback(self):
        session = _FakeSession()
        with mock.patch.object(
            warp_send_watch, "rollback_warp_scene_on_send_failure",
        ) as rollback:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"anything", ConnectionResetError(),
            )
        self.assertEqual(outcome, warp_send_watch.OUTCOME_NOTHING_PARKED)
        rollback.assert_not_called()
        self.assertEqual(session.events, [])

    def test_a_parked_cell_delegates_to_the_rollback_and_then_clears(self):
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        with mock.patch.object(
            warp_send_watch,
            "rollback_warp_scene_on_send_failure",
            return_value="rolled_back",
        ) as rollback:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"the-warp-frame", ConnectionResetError(),
            )
        rollback.assert_called_once_with(
            session, warp_scene_persist.SEND_FAILURE_WARP_ACTION_LABEL,
        )
        self.assertEqual(outcome, "rolled_back")
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_a_different_frames_failure_still_rolls_back_the_parked_warp(self):
        """`CORE-REQUEST-GM-057`'s own scenario: v141 `break`s the action
        list on the FIRST failure, so the frame attached to the failure is
        not necessarily the warp's.  The cell being non-empty is the only
        fact this function needs."""
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        with mock.patch.object(
            warp_send_watch,
            "rollback_warp_scene_on_send_failure",
            return_value="rolled_back",
        ) as rollback:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"an-earlier-unrelated-frame", OSError("gone"),
            )
        rollback.assert_called_once()
        self.assertEqual(outcome, "rolled_back")
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_the_park_clears_even_when_the_rollback_itself_reports_a_failure(
        self,
    ):
        """The park's story is over either way -- see the module's own
        docstring on why leaving it would risk a second, spurious undo."""
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        with mock.patch.object(
            warp_send_watch,
            "rollback_warp_scene_on_send_failure",
            return_value="rollback_refused_PermissionError",
        ):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"the-warp-frame", OSError("gone"),
            )
        self.assertEqual(outcome, "rollback_refused_PermissionError")
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_event_trail_names_the_rollback_outcome(self):
        session = _FakeSession()
        warp_send_watch.park_warp_send(session, b"the-warp-frame")
        with mock.patch.object(
            warp_send_watch,
            "rollback_warp_scene_on_send_failure",
            return_value="rolled_back",
        ):
            warp_send_watch.on_game_frame_send_failed(
                session, b"the-warp-frame", ConnectionResetError(),
            )
        self.assertIn(
            f"{warp_send_watch.EVENT_PREFIX}failed_rollback_rolled_back",
            session.events,
        )


class _Session:
    """The attributes these functions read/write off a runtime session.

    A plain object, not a `Mock(spec=...)`: `warp_send_watch` sets a session
    attribute (`SESSION_ATTRIBUTE`) that is not one of `foundation` /
    `events` / `token`, and a spec'd mock would refuse that write outright
    -- the exact "session that refuses attributes" case these functions are
    already written to survive, but not the one this fixture means to be.
    """

    def __init__(self, foundation):
        self.foundation = foundation
        self.events = []
        self.token = None


class RealDatabaseTests(unittest.TestCase):
    """Real store, real lifecycle, real session, real router, real frame."""

    def setUp(self):
        gm_dispatch.reset_rate_limit_state_for_tests()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        env_pin.start()
        self.addCleanup(env_pin.stop)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.home = Position(
            1, 0, self.legacy.V135_PLAYER_X,
            self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
        )
        self.lifecycle = CharacterLifecycle(
            self.store, self.home,
            self.legacy.extract_avatar_attr_wire_from_actor,
        )

    def _session(self, login_name):
        foundation = FoundationSession(self.lifecycle, self.projector, login_name)
        _op, _has_actor, wire = self.legacy.parse_create_actor(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC),
        )
        character, _reply = foundation.create(
            self.legacy.decode_create_actor_data_ex(wire)["name"], wire,
        )
        foundation.select_and_start(character.selector)
        return _Session(foundation)

    def _row(self, session):
        return self.store.get_character(session.foundation.selected.id).position

    # ---- the real call site really parks the real frame -----------------

    def test_a_persisted_no_coords_warp_parks_its_own_composed_frame(self):
        session = self._session("watch01")
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsNotNone(record)
        # `verdict.action` is `(label, pc, frame, delay)`; the parked bytes
        # must be byte-identical to the frame the composer actually built,
        # not a re-derivation this test invents independently.
        self.assertEqual(record.frame_bytes, bytes(verdict.action[2]))
        self.assertNotIn(
            chat_command_action.EVENT_WARP_SEND_WATCH_NOT_PARKED, session.events,
        )

    def test_a_refused_destination_never_parks_anything(self):
        """`OUTCOME_LOGIN_WOULD_REFUSE` -- nothing durable moved, so there is
        nothing this connection is owed a send confirmation for."""
        session = self._session("watch02")
        stream = io.StringIO()
        with redirect_stderr(stream):
            chat_command_action._warp_teleport_action_no_coords(
                session, REFUSED_SCENE, self.legacy,
            )
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None))

    # ---- confirmed reachable through the real facade shape ---------------

    def test_the_parked_frame_clears_when_its_own_bytes_are_reported_sent(
        self,
    ):
        session = self._session("watch03")
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        outcome = warp_send_watch.on_game_frame_sent(
            session, bytes(verdict.action[2]),
        )
        self.assertEqual(outcome, warp_send_watch.OUTCOME_CLEARED_OWN_FRAME)
        # The row is unaffected -- confirming a send is not a write.
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

    # ---- the scenario `CORE-REQUEST-GM-057` was written to name ----------

    def test_an_earlier_unrelated_frames_failure_still_rolls_back_the_parked_warp(
        self,
    ):
        """v141's send loop `break`s the whole action list on the FIRST
        failed `sendall`.  A `say` queued ahead of a persisted `/warp`
        whose OWN frame never reaches `sendall` at all must still put the
        row back -- the client cannot have received a frame the loop never
        attempted."""
        session = self._session("watch04")
        before = self._row(session)
        self.assertEqual(before.scene_id, 1)

        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

        with redirect_stderr(stream):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"an-earlier-say-frames-bytes", ConnectionResetError(),
            )

        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertEqual(
            (after.x, after.y, after.z), (before.x, before.y, before.z),
        )
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))
        self.assertIn(warp_scene_persist.ROLLBACK_CONSOLE_TOKEN, stream.getvalue())
        # And the warp's own frame, arriving late (it never really would,
        # since the loop already broke) would find nothing left to clear.
        late = warp_send_watch.on_game_frame_sent(
            session, bytes(verdict.action[2]),
        )
        self.assertEqual(late, warp_send_watch.OUTCOME_NOTHING_PARKED)

    def test_the_warps_own_frame_failing_directly_rolls_back_too(self):
        session = self._session("watch05")
        before = self._row(session)
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        with redirect_stderr(stream):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, bytes(verdict.action[2]), BrokenPipeError(),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        self.assertEqual(self._row(session).scene_id, before.scene_id)

    # ---- the withhold path clears its own park, and only its own --------

    def test_a_withheld_warp_clears_its_own_send_watch_park_too(self):
        """`verdict.undo` already reverted the row synchronously here; the
        frame that would have confirmed or failed the park is never going
        to be queued (`action` becomes `None` on this same branch).  A park
        left behind would let a LATER, unrelated send failure on this same
        connection roll back a row that already went back once."""
        session = self._session("watch06")
        session.token = "GM_ONE"
        before = self._row(session)

        config_path = Path(self.tmp.name) / "gm_accounts.json"
        config_path.write_text('{"gm_accounts": ["GM_ONE"]}', encoding="utf-8")
        log_path = Path(self.tmp.name) / "capture" / "gm_command_log.ndjson"
        login_scene_config_path = (
            Path(self.tmp.name) / "config" / "gm_login_scene.json"
        )

        stream = io.StringIO()
        with redirect_stderr(stream):
            with mock.patch.object(
                chat_command_action,
                "log_gm_command_outcome",
                side_effect=OSError("disk full"),
            ):
                action = chat_command_action.make_gm_chat_command_action(
                    session,
                    _chat_payload(f"/warp {DESTINATION_SCENE}"),
                    self.legacy,
                    config_path=str(config_path),
                    log_path=str(log_path),
                    login_scene_config_path=str(login_scene_config_path),
                )

        self.assertIsNone(action)
        self.assertEqual(self._row(session).scene_id, before.scene_id)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None))
        self.assertNotIn(
            chat_command_action.EVENT_WARP_SEND_WATCH_STALE_PARK_NOT_CLEARED,
            session.events,
        )

    def test_the_ordinary_audited_warp_leaves_its_park_alone(self):
        """The sibling of the withhold test above: the ORDINARY path must
        not clear a park it has no reason to touch."""
        session = self._session("watch07")
        session.token = "GM_ONE"

        config_path = Path(self.tmp.name) / "gm_accounts.json"
        config_path.write_text('{"gm_accounts": ["GM_ONE"]}', encoding="utf-8")
        log_path = Path(self.tmp.name) / "capture" / "gm_command_log.ndjson"
        login_scene_config_path = (
            Path(self.tmp.name) / "config" / "gm_login_scene.json"
        )

        stream = io.StringIO()
        with redirect_stderr(stream):
            action = chat_command_action.make_gm_chat_command_action(
                session,
                _chat_payload(f"/warp {DESTINATION_SCENE}"),
                self.legacy,
                config_path=str(config_path),
                log_path=str(log_path),
                login_scene_config_path=str(login_scene_config_path),
            )

        self.assertIsNotNone(action)
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsNotNone(record)
        self.assertEqual(record.frame_bytes, bytes(action[2]))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
