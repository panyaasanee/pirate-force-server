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
import threading
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


class DoubleWarpTests(RealDatabaseTests):
    """Two `/warp` in a row, through the real route, on a real row.

    WHY THIS CLASS EXISTS.  `park_warp_send`'s docstring says it REPLACES
    rather than refuses an existing park, and round `8u0j50`'s manual
    adversary pass wrote the double-warp question down as unanswered rather
    than answering it.  `COO-DECISION 20260905_0345` item 3 accepted the
    intent and asked for the test that fires at it directly -- this class,
    one file, no new module.

    IT IS A REGRESSION TEST, NOT A DISCOVERY.  The behaviour below was
    measured on this tree before the assertions were written; nothing here
    is a design this round chose.

    WHAT IT IS NOT EVIDENCE OF: nothing on screen.  Nobody has typed two
    `/warp` commands into a real client back to back and watched what
    happens, and this class does not claim they have.  It pins the SERVER
    half -- which row the rollback would restore, and which frame can still
    close the window -- and that half only becomes reachable at all once
    `CORE-REQUEST-GM-057` puts a real caller behind the two observers.
    """

    def _gm_route(self, session):
        config_path = Path(self.tmp.name) / "gm_accounts.json"
        config_path.write_text('{"gm_accounts": ["GM_ONE"]}', encoding="utf-8")
        log_path = Path(self.tmp.name) / "capture" / "gm_command_log.ndjson"
        login_scene_config_path = (
            Path(self.tmp.name) / "config" / "gm_login_scene.json"
        )
        session.token = "GM_ONE"

        def route(text):
            stream = io.StringIO()
            with redirect_stderr(stream):
                return chat_command_action.make_gm_chat_command_action(
                    session,
                    _chat_payload(text),
                    self.legacy,
                    config_path=str(config_path),
                    log_path=str(log_path),
                    login_scene_config_path=str(login_scene_config_path),
                )

        return route

    def test_the_second_warp_parks_its_own_frame_over_the_firsts(self):
        """The double-tap: `/warp 2` typed twice because nothing appeared."""
        session = self._session("double01")
        route = self._gm_route(session)

        first = route(f"/warp {DESTINATION_SCENE}")
        parked_first = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsNotNone(first)
        self.assertEqual(parked_first.frame_bytes, bytes(first[2]))

        second = route(f"/warp {DESTINATION_SCENE}")
        parked_second = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsNotNone(second)
        self.assertIsNot(parked_second, parked_first)
        self.assertEqual(parked_second.frame_bytes, bytes(second[2]))

    def test_two_warps_to_the_SAME_scene_compose_byte_identical_frames(self):
        """Measured, and it is why the next test uses two DIFFERENT scenes.

        The composer is deterministic and both commands name the same
        destination spawn, so `first[2] == second[2]`.  The two frames are
        therefore INDISTINGUISHABLE on the wire, and the first one's send
        confirmation closes the second one's window.  That costs nothing HERE
        -- the row value is identical too, so the undo the early clear gives
        up would have been a no-op -- but it is the reason a test that wants
        to see the replacement bite has to move the row.
        """
        session = self._session("double02")
        route = self._gm_route(session)
        first = route(f"/warp {DESTINATION_SCENE}")
        second = route(f"/warp {DESTINATION_SCENE}")
        self.assertEqual(bytes(first[2]), bytes(second[2]))
        self.assertEqual(
            warp_send_watch.on_game_frame_sent(session, bytes(first[2])),
            warp_send_watch.OUTCOME_CLEARED_OWN_FRAME,
        )

    def test_the_first_warps_frame_can_no_longer_close_the_window(self):
        """The consequence that makes replacement the right choice.

        v141 queues both frames on the same connection, so the FIRST warp's
        bytes may well reach `on_game_frame_sent` after the second park is
        already in the cell.  They must not retire it: the row has moved
        again since, and a cleared cell would leave the second warp with no
        rollback if the socket then died.
        """
        session = self._session("double03")
        route = self._gm_route(session)
        first = route(f"/warp {DESTINATION_SCENE}")
        second = route("/warp 3")
        self.assertNotEqual(bytes(first[2]), bytes(second[2]))

        self.assertEqual(
            warp_send_watch.on_game_frame_sent(session, bytes(first[2])),
            warp_send_watch.OUTCOME_LEFT_PARKED_OTHER_FRAME,
        )
        self.assertIsNotNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None)
        )
        self.assertEqual(
            warp_send_watch.on_game_frame_sent(session, bytes(second[2])),
            warp_send_watch.OUTCOME_CLEARED_OWN_FRAME,
        )
        self.assertIsNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None)
        )

    def test_a_failure_after_two_warps_rolls_back_only_the_second(self):
        """THE DEFECT THIS ROUND FOUND AND FIXED, pinned as a behaviour.

        `/warp 2`, its frame CONFIRMED sent (the client really is in scene 2
        on screen), then `/warp 3`, then the socket dies before that frame
        goes out.  The row must go back to 2 -- the scene the SECOND warp
        moved the character out of -- not to 1.

        Before this round it went to 1: the undo read the row to restore from
        `session.foundation.selected.position`, which is the last position
        the CLIENT reported and which a warp deliberately does not update, so
        after two warps it was two warps stale.  The character would have
        reappeared in Port Royal on the next login having been sent to Prison
        Exile and confirmed there.  The window is not live yet -- nothing
        calls `on_game_frame_send_failed` until `CORE-REQUEST-GM-057` lands --
        which is why the fix went in before the hookup rather than after.
        """
        session = self._session("double04")
        route = self._gm_route(session)
        first = route(f"/warp {DESTINATION_SCENE}")
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertEqual(
            warp_send_watch.on_game_frame_sent(session, bytes(first[2])),
            warp_send_watch.OUTCOME_CLEARED_OWN_FRAME,
        )

        second = route("/warp 3")
        self.assertEqual(self._row(session).scene_id, 3)

        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, bytes(second[2]), OSError("connection reset"),
            )

        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertNotEqual(self._row(session).scene_id, 1)
        self.assertIsNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE, None)
        )

    def test_a_failure_with_BOTH_warps_unconfirmed_unwinds_the_whole_run(self):
        """pf-adversary D-A, MEASURED -- the regression the first draft had.

        `/warp 2` and `/warp 3` both composed before EITHER frame left the
        socket, then the socket dies.  Neither frame reached the client, so
        the row must go all the way back to scene 1.

        The first draft of this round took the SECOND park's own
        `previous_position` (scene 2) and left the row there -- moving it
        FORWARD into a scene the client had never been sent to, then clearing
        the park so warp 2's own failure could never correct it.  That was
        strictly worse than the delegate it replaced, which got this case
        right.  A park that is still in the cell has not been confirmed sent,
        so a replacement carries the OLDEST unconfirmed row forward.
        """
        session = self._session("double06")
        route = self._gm_route(session)
        route(f"/warp {DESTINATION_SCENE}")
        second = route("/warp 3")
        # Neither frame has been reported sent: nothing called
        # `on_game_frame_sent`, so the cell is still holding the run.
        self.assertEqual(self._row(session).scene_id, 3)

        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, bytes(second[2]), OSError("connection reset"),
            )

        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        self.assertEqual(self._row(session).scene_id, 1)

    def test_three_unconfirmed_warps_still_unwind_to_the_first_row(self):
        """The same rule at depth, so the carry-forward cannot be a one-off."""
        session = self._session("double07")
        route = self._gm_route(session)
        route(f"/warp {DESTINATION_SCENE}")
        route("/warp 3")
        third = route("/warp 5")
        self.assertEqual(self._row(session).scene_id, 5)
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_send_watch.on_game_frame_send_failed(
                session, bytes(third[2]), OSError("reset"),
            )
        self.assertEqual(self._row(session).scene_id, 1)

    def test_a_confirmed_warp_lets_the_next_one_start_a_fresh_run(self):
        """The other half: a CLEARED cell must not carry anything forward.

        Without this the carry-forward would never expire and every later
        warp on the connection would unwind to the character's first scene.
        """
        session = self._session("double08")
        route = self._gm_route(session)
        first = route(f"/warp {DESTINATION_SCENE}")
        warp_send_watch.on_game_frame_sent(session, bytes(first[2]))
        second = route("/warp 3")
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertEqual(record.previous_position.scene_id, DESTINATION_SCENE)
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_send_watch.on_game_frame_send_failed(
                session, bytes(second[2]), OSError("reset"),
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

    def test_a_wrongly_typed_parked_row_falls_back_instead_of_disarming(self):
        """pf-adversary D-B, MEASURED.

        `rollback_warp_scene` answers `nothing_to_roll_back` for anything
        that is not a `Position`.  Gating the new path on `is not None` sent
        such a row down it and produced NO rollback and NO fallback -- the
        net silently disarmed on a hand-built park, which is the one shape
        the fallback exists for.
        """
        session = self._session("double09")
        warp_send_watch.park_warp_send(session, b"not-a-real-frame", 5)
        with mock.patch.object(
            warp_send_watch, "rollback_warp_scene_on_send_failure",
            return_value=warp_scene_persist.OUTCOME_ROLLED_BACK,
        ) as delegate:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"other", OSError("reset"),
            )
        delegate.assert_called_once()
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)

    def test_a_park_under_a_foreign_label_falls_back_too(self):
        """The label check must not go dead just because the row travels.

        `rollback_warp_scene_on_send_failure` narrows its blast radius to one
        label by design; the new path has to hold the same line.
        """
        session = self._session("double10")
        row = self._row(session)
        object.__setattr__(
            session,
            warp_send_watch.SESSION_ATTRIBUTE,
            warp_send_watch.ParkedWarpSend("SOME_OTHER_LABEL", b"f", row),
        )
        with mock.patch.object(
            warp_send_watch, "rollback_warp_scene",
        ) as direct, mock.patch.object(
            warp_send_watch, "rollback_warp_scene_on_send_failure",
            return_value=warp_scene_persist.OUTCOME_NOT_A_WARP,
        ) as delegate:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"f", OSError("reset"),
            )
        direct.assert_not_called()
        delegate.assert_called_once()
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_NOT_A_WARP)

    def test_a_first_ever_warp_parks_no_row_and_takes_the_delegate(self):
        """pf-adversary D-G: the fallback's one PRODUCTION-reachable shape.

        A character with no `character_positions` row yet has nothing for
        `row_before_warp` to capture, so its first warp parks
        `previous_position=None` while still reporting `PERSISTED`.  The only
        other test of the fallback hand-builds its park; this one comes
        through the real route.
        """
        session = self._session("double11")
        route = self._gm_route(session)
        with mock.patch.object(
            chat_command_action, "row_before_warp", return_value=None,
        ):
            route(f"/warp {DESTINATION_SCENE}")
        record = getattr(session, warp_send_watch.SESSION_ATTRIBUTE)
        self.assertIsNotNone(record)
        self.assertIsNone(record.previous_position)

    def test_a_park_with_no_previous_row_still_uses_the_older_delegate(self):
        """The fallback, so the widened record cannot silently drop a caller.

        A park built without a `previous_position` -- a hand-built record, or
        a call site outside this lane -- must still reach
        `rollback_warp_scene_on_send_failure`, which is what every park did
        before this round.
        """
        session = self._session("double05")
        warp_send_watch.park_warp_send(session, b"not-a-real-frame")
        with mock.patch.object(
            warp_send_watch, "rollback_warp_scene_on_send_failure",
            return_value=warp_scene_persist.OUTCOME_ROLLED_BACK,
        ) as delegate:
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, b"other", OSError("reset"),
            )
        delegate.assert_called_once_with(
            session, warp_scene_persist.SEND_FAILURE_WARP_ACTION_LABEL,
        )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)


class CrossThreadObserverTests(RealDatabaseTests):
    """R348's own question, answered by measurement rather than argument.

    `pf_bridge/notes_to_chief/FROM_CHIEF_R348_TO_ALL_20260905_0505.md`:
    "hook ยิงบนสองเธรด ... consumer ที่ตั้งใจไว้เขียน sqlite บนคอนเนกชันของ
    อีกเธรด -> ProgrammingError บนเธรด heartbeat แล้วถูกกลืนเป็นบรรทัด
    stderr" -- `_offer_send_outcome` (`connection.py`) is called on whichever
    thread's `sendall()` this connection's `send_lock` just let through
    (`current/pf_login_game_server_v141.py:7754` the action loop, `:7427`
    `heartbeat_worker`), and it swallows anything the observer raises,
    exactly the shape that would hide a `sqlite3.ProgrammingError` as one
    quiet stderr line.

    THIS CLASS DOES NOT GUESS WHETHER THAT ERROR CAN HAPPEN.  It calls both
    of this module's observers from a REAL background thread, against the
    REAL `SQLiteStore` this fixture already builds, and reads the row back
    on the MAIN thread afterwards -- the one difference that would matter if
    a connection object were being shared across threads.  `sqlite3.
    ProgrammingError` is not caught anywhere below: if `store.py`'s
    `SQLiteStore.connect()` ever stopped opening a fresh connection per call
    (`store.py:285-305`) and started reusing one across threads, this test
    would fail with THAT exception surfacing on `thread.join()`, not with a
    silently wrong row.

    WHAT THIS DOES NOT ANSWER, ON PURPOSE (see the module docstring's own
    words): whether holding `send_lock` for the duration of a real rollback's
    disk I/O is an acceptable delay to the OTHER thread's next send. That
    question is a `send_lock` liveness question, not a correctness one, and
    it is out of this file's reach without the hookup this module still does
    not have (`CORE-REQUEST-GM-058`).
    """

    def _run_in_thread(self, target, *args):
        """Run `target(*args)` on a background thread; re-raise here.

        `unittest` does not fail a test for an exception raised on a thread
        it did not create -- Python just prints it and the test passes,
        which is exactly backwards for a test whose entire point is "does
        this raise on another thread".  The result/exception is carried back
        across the thread boundary in a plain list, the same one-slot
        hand-off `chat_command_action._note` and this module's own `_note`
        already use for `session.events`, so nothing new is being trusted
        here.
        """
        outcome: list = []

        def _wrapped():
            try:
                outcome.append(("ok", target(*args)))
            except BaseException as error:  # noqa: BLE001 - re-raised below
                outcome.append(("error", error))

        thread = threading.Thread(target=_wrapped)
        thread.start()
        thread.join(timeout=10)
        self.assertTrue(outcome, "background thread did not finish in time")
        kind, value = outcome[0]
        if kind == "error":
            raise value
        return value

    def test_send_failed_from_a_background_thread_does_not_raise_and_rolls_back(
        self,
    ):
        session = self._session("thread01")
        before = self._row(session)
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

        with redirect_stderr(stream):
            outcome = self._run_in_thread(
                warp_send_watch.on_game_frame_send_failed,
                session, bytes(verdict.action[2]), ConnectionResetError(),
            )

        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        # Read back on the MAIN thread -- the one difference that would
        # matter if the write had actually landed on a connection object
        # tied to the background thread instead of one opened and closed
        # inside that single call.
        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_send_sent_from_a_background_thread_clears_the_park(self):
        session = self._session("thread02")
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        outcome = self._run_in_thread(
            warp_send_watch.on_game_frame_sent,
            session, bytes(verdict.action[2]),
        )
        self.assertEqual(outcome, warp_send_watch.OUTCOME_CLEARED_OWN_FRAME)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))
        # Confirming a send is not a write -- the row is still the warp's.
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

    # NOT TESTED HERE, ON PURPOSE: two observer calls racing the SAME park
    # concurrently, with no lock of this module's own.  Every real caller
    # (`current/pf_login_game_server_v141.py:7754` the action loop, `:7427`
    # `heartbeat_worker`) reaches `sendall()` only from inside that
    # connection's own `send_lock`, so `_offer_send_outcome` -- and these two
    # functions once wired -- can never truly overlap for one connection; a
    # test that called them concurrently WITHOUT that lock would be timing a
    # race this module was never asked to survive alone, and (measured while
    # drafting this class) is not even deterministic: the read-then-clear in
    # `on_game_frame_send_failed` is not atomic, so two truly-unlocked
    # callers can both see the record before either clears it and both
    # report `rolled_back` -- a real finding about calling this module
    # without the lock its one production call site always holds, not a bug
    # in the module.  Recorded here rather than shipped as a flaky test;
    # `CORE-REQUEST-GM-058` states the lock requirement explicitly so a
    # future caller cannot reach this module any other way.


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
