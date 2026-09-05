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
import re
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import weakref
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import connection  # noqa: E402
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
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
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

    def _park(self, session):
        """Move the row with a REAL `/warp` and return its parked frame.

        The same three lines `LiveSocketFacadeTests._warp_frame` runs, hoisted
        here in round `j2jluj` because two more classes now need exactly this
        starting state: a durable row at the destination, and one unconfirmed
        park holding the composed frame's own bytes.
        """
        with redirect_stderr(io.StringIO()):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertIsNotNone(verdict.action)
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIsNotNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))
        return bytes(verdict.action[2])

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



class _SwallowingSession:
    """A session whose attribute writes are silently lost.

    `_RefusingSession` above pins one specific attribute; this one loses
    every write, which is what `install_send_outcome_observers` has to
    survive: `setattr` does not raise, the read-back finds nothing, and a
    half-installed connection (success forward present, failure forward
    absent) would clear parks it can never roll back.
    """

    def __setattr__(self, name, value):
        pass


class _NoWeakrefSession:
    """A session that cannot be weak-referenced.

    `__slots__` without `__weakref__` is the shape `weakref.ref()` raises
    `TypeError` on.  The installer must still install (a delayed
    collection is a smaller defect than a warp that never rolls back) --
    that fallback is measured, not asserted from reading the code.
    """

    __slots__ = (
        "foundation", "events",
        warp_send_watch.SESSION_ATTRIBUTE,
        warp_send_watch.SENT_OBSERVER_ATTRIBUTE,
        warp_send_watch.FAILED_OBSERVER_ATTRIBUTE,
    )

    def __init__(self):
        self.foundation = _FakeFoundation(_FakeSelected(_FakePosition()))
        self.events = []
        setattr(self, warp_send_watch.SESSION_ATTRIBUTE, None)
        setattr(self, warp_send_watch.SENT_OBSERVER_ATTRIBUTE, None)
        setattr(self, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE, None)


class _HalfWritableSession(_FakeSession):
    """Accepts the success forward, RAISES on the failure forward.

    pf-adversary D5: the shape a real refusal takes.  `__setattr__` raising
    is what `__slots__`, a read-only property and a frozen dataclass all do,
    and it is the branch the previous version of this test never reached.
    """

    def __setattr__(self, name, value):
        if name == warp_send_watch.FAILED_OBSERVER_ATTRIBUTE and callable(
            value
        ):
            raise AttributeError(name)
        object.__setattr__(self, name, value)


class _UndoHostileSession(_FakeSession):
    """Accepts the first forward, raises on the second AND on the undo.

    pf-adversary D5: the branch where even taking the half back off fails.
    """

    def __setattr__(self, name, value):
        if name == warp_send_watch.FAILED_OBSERVER_ATTRIBUTE and callable(
            value
        ):
            raise AttributeError(name)
        if name == warp_send_watch.SENT_OBSERVER_ATTRIBUTE and value is None:
            raise AttributeError(name)
        object.__setattr__(self, name, value)


class _HostileSession:
    """Every attribute read raises.  pf-adversary D5: the OTHER `except`."""

    def __getattr__(self, name):
        raise RuntimeError(f"hostile read of {name}")


class InstallSendOutcomeObserverTests(unittest.TestCase):
    """`install_send_outcome_observers` -- the second layer, unit half."""

    def test_the_two_names_it_installs_are_the_ones_connection_py_reads(self):
        """The one string pair that must not drift, checked against the
        file that owns it rather than against a copy in this test.

        `connection.py` is not this lane's file; if chief ever renames
        either hook name there, an installer that kept writing the old
        name would install two attributes nothing ever reads, and every
        other test in this class would still pass.  This is the only
        assertion in this file that reads another lane's source.
        """
        source = (
            ROOT / "src" / "pirateforce_foundation" / "connection.py"
        ).read_text(encoding="utf-8")
        self.assertIn(
            f'_offer_send_outcome("{warp_send_watch.FAILED_OBSERVER_ATTRIBUTE}"',
            source,
        )
        self.assertIn(
            f'_offer_send_outcome("{warp_send_watch.SENT_OBSERVER_ATTRIBUTE}"',
            source,
        )

    def test_install_puts_both_forwards_on_a_plain_session(self):
        session = _FakeSession()
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_OK,
        )
        self.assertTrue(
            callable(getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE))
        )
        self.assertTrue(
            callable(getattr(session, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE))
        )

    def test_the_installed_forwards_take_connection_pys_own_arities(self):
        """`observer(data)` on success, `observer(data, error)` on failure
        (`connection.py:154`) -- a forward with the wrong arity would raise
        into `_offer_send_outcome`'s swallowing except and be invisible."""
        session = _FakeSession()
        warp_send_watch.install_send_outcome_observers(session)
        warp_send_watch.park_warp_send(session, b"warp-frame", None)

        sent = getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE)
        self.assertEqual(
            sent(b"some-other-frame"),
            warp_send_watch.OUTCOME_LEFT_PARKED_OTHER_FRAME,
        )
        self.assertEqual(
            sent(b"warp-frame"), warp_send_watch.OUTCOME_CLEARED_OWN_FRAME,
        )

        failed = getattr(session, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE)
        self.assertEqual(
            failed(b"anything", ConnectionResetError()),
            warp_send_watch.OUTCOME_NOTHING_PARKED,
        )

    def test_a_second_install_refuses_rather_than_replacing(self):
        session = _FakeSession()
        warp_send_watch.install_send_outcome_observers(session)
        first = getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE)
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_REFUSED_ALREADY_PRESENT,
        )
        self.assertIs(
            getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE), first,
        )

    def test_a_real_class_method_of_the_same_name_is_never_shadowed(self):
        """If chief takes `CORE-REQUEST-GM-058`'s two-method shape instead,
        a stray installer call must not overwrite his methods with instance
        attributes -- that would replace a working hookup with this one and
        nobody would see the difference until it broke."""
        calls = []

        class _SessionWithChiefsMethods(_FakeSession):
            def on_game_frame_sent(self, frame_bytes):
                calls.append("sent")
                return "chiefs"

            def on_game_frame_send_failed(self, frame_bytes, error):
                calls.append("failed")
                return "chiefs"

        session = _SessionWithChiefsMethods()
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_REFUSED_ALREADY_PRESENT,
        )
        self.assertEqual(session.on_game_frame_sent(b""), "chiefs")
        self.assertEqual(calls, ["sent"])

    def test_a_session_that_swallows_writes_refuses_and_leaves_no_half(self):
        session = _SwallowingSession()
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_REFUSED_NOT_WRITABLE,
        )
        self.assertIsNone(
            getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE, None)
        )
        self.assertIsNone(
            getattr(session, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE, None)
        )

    def test_a_partial_install_is_undone_not_left_armed(self):
        """The failure half refuses to land, the success half already did.
        A connection left with only the success forward would CLEAR parks
        it can never roll back -- strictly worse than having neither.

        pf-adversary D5 (MEASURED, round `goxj0y`) rewrote this test.  It
        used to force the refusal by patching a module-global `setattr` onto
        `warp_send_watch` with `create=True` -- a global the production
        module does not have, so the `except` branch it claimed to cover was
        never executed by anything.  `_HalfWritableSession` RAISES on the
        second name, which is what a real refusal looks like (`__slots__`, a
        read-only property, a frozen dataclass).
        """
        session = _HalfWritableSession()
        outcome = warp_send_watch.install_send_outcome_observers(session)

        self.assertEqual(outcome, warp_send_watch.INSTALL_REFUSED_NOT_WRITABLE)
        self.assertIsNone(
            getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE, None)
        )
        self.assertIsNone(
            getattr(session, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE, None)
        )

    def test_the_console_half_of_the_announcement_cannot_raise(self):
        """pf-adversary D5: the announcer's own guard, exercised.

        `_persist_console` is reused precisely because it already guards a
        `None` stderr, but this module must survive it raising anyway -- the
        announcement runs inside a `sendall` critical section on the game
        listener thread, and an exception escaping here would unwind it.
        """
        session = _FakeSession()
        with mock.patch.object(
            warp_send_watch, "_persist_console",
            side_effect=RuntimeError("stderr is gone"),
        ):
            self.assertEqual(
                warp_send_watch.install_send_outcome_observers(session),
                warp_send_watch.INSTALL_OK,
            )
        # The event half still landed, so the outcome is not lost entirely.
        self.assertEqual(session.events, [
            f"{warp_send_watch.EVENT_PREFIX}install_"
            f"{warp_send_watch.INSTALL_OK}",
        ])

    def test_an_undo_that_itself_refuses_still_returns_not_writable(self):
        """pf-adversary D5: the last-ditch guard in the undo loop.

        A session that accepted the first forward, raised on the second, and
        then raises again when the first is being taken back off.  There is
        nothing more this module can do for such a session -- the contract
        it must still keep is "do not raise, and say so".
        """
        session = _UndoHostileSession()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(
                warp_send_watch.install_send_outcome_observers(session),
                warp_send_watch.INSTALL_REFUSED_NOT_WRITABLE,
            )

    def test_a_session_whose_getattr_raises_refuses_instead_of_exploding(self):
        """pf-adversary D5: the first `except` branch, exercised for real."""
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(_HostileSession()),
            warp_send_watch.INSTALL_REFUSED_NOT_WRITABLE,
        )

    def test_exactly_one_name_present_gets_the_OTHER_one_supplied(self):
        """pf-adversary D1/D4 (MEASURED).  Refusing on "at least one
        present" was measured to be worse than doing nothing: with only the
        failure forward declared, a warp whose frame really reached the wire
        is never cleared, and the next unrelated disconnect rolls the
        durable row back while the client stands in the destination.  The
        missing half is supplied; the present half is left strictly alone.

        This is also the test that kills the `or` -> `and` mutant D4 found
        surviving: with `and`, a session carrying one name gets the OTHER
        written AND the existing one shadowed.
        """
        for present_name, missing_name in (
            (
                warp_send_watch.SENT_OBSERVER_ATTRIBUTE,
                warp_send_watch.FAILED_OBSERVER_ATTRIBUTE,
            ),
            (
                warp_send_watch.FAILED_OBSERVER_ATTRIBUTE,
                warp_send_watch.SENT_OBSERVER_ATTRIBUTE,
            ),
        ):
            with self.subTest(present=present_name):
                session = _FakeSession()
                sentinel = lambda *a, **k: "someone-elses"  # noqa: E731
                setattr(session, present_name, sentinel)

                outcome = warp_send_watch.install_send_outcome_observers(
                    session,
                )

                self.assertEqual(
                    outcome,
                    warp_send_watch.INSTALL_COMPLETED_HALF_DECLARED,
                )
                # The one that was there is untouched -- never shadowed.
                self.assertIs(getattr(session, present_name), sentinel)
                # The one that was missing is now this module's forward.
                self.assertTrue(callable(getattr(session, missing_name)))
                self.assertNotEqual(
                    getattr(session, missing_name), sentinel,
                )

    def test_every_outcome_reaches_the_event_trail_and_the_console(self):
        """pf-adversary D1/D3 (MEASURED).  The installer used to be the one
        function here that refused without saying so, while its only
        intended caller throws the return value away -- a refusal on a live
        connection was invisible to chief, to CI and to the console alike.
        """
        cases = (
            (_FakeSession(), warp_send_watch.INSTALL_OK),
            (_SwallowingSession(), warp_send_watch.INSTALL_REFUSED_NOT_WRITABLE),
        )
        for session, expected in cases:
            with self.subTest(expected=expected):
                stream = io.StringIO()
                with redirect_stderr(stream):
                    self.assertEqual(
                        warp_send_watch.install_send_outcome_observers(session),
                        expected,
                    )
                self.assertIn(
                    f"{warp_send_watch.INSTALL_CONSOLE_TOKEN} {expected}",
                    stream.getvalue(),
                )

        # The event trail half, on a session that actually keeps events.
        session = _FakeSession()
        with redirect_stderr(io.StringIO()):
            warp_send_watch.install_send_outcome_observers(session)
            warp_send_watch.install_send_outcome_observers(session)
        self.assertEqual(session.events, [
            f"{warp_send_watch.EVENT_PREFIX}install_"
            f"{warp_send_watch.INSTALL_OK}",
            f"{warp_send_watch.EVENT_PREFIX}install_"
            f"{warp_send_watch.INSTALL_REFUSED_ALREADY_PRESENT}",
        ])

    def test_the_session_is_not_kept_alive_by_its_own_forwards(self):
        """A strongly-capturing closure stored ON the session would be a
        reference cycle, collectable only by a full `gc` pass, and
        `lane_hooks`'s live-session registry holds sessions WEAKLY so a
        dead connection stops answering `current_session_scene_id`
        promptly.  Measured with a real `weakref`, no `gc.collect()`.
        """
        session = _FakeSession()
        warp_send_watch.install_send_outcome_observers(session)
        witness = weakref.ref(session)
        self.assertIsNotNone(witness())
        del session
        self.assertIsNone(witness())

    def test_a_session_that_cannot_be_weak_referenced_still_installs(self):
        session = _NoWeakrefSession()
        with self.assertRaises(TypeError):
            weakref.ref(session)
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_OK,
        )
        warp_send_watch.park_warp_send(session, b"frame", None)
        self.assertEqual(
            getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE)(b"frame"),
            warp_send_watch.OUTCOME_CLEARED_OWN_FRAME,
        )

    def test_a_forward_whose_session_died_answers_nothing_parked(self):
        """The weak half's own failure mode, forced.  A forward that
        outlived its session must return the empty answer, not raise into
        `_offer_send_outcome`'s swallowing except."""
        session = _FakeSession()
        warp_send_watch.install_send_outcome_observers(session)
        sent = getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE)
        failed = getattr(session, warp_send_watch.FAILED_OBSERVER_ATTRIBUTE)
        del session
        self.assertEqual(
            sent(b"frame"), warp_send_watch.OUTCOME_NOTHING_PARKED,
        )
        self.assertEqual(
            failed(b"frame", ConnectionResetError()),
            warp_send_watch.OUTCOME_NOTHING_PARKED,
        )


class LiveSocketFacadeTests(RealDatabaseTests):
    """The whole second layer, end to end, through the REAL facade.

    Everything else in this file calls this module's observers directly.
    This class does not: it builds a real `GameConnectionBindings`, a real
    `AcceptedGameSocket` over a fake raw socket, binds a real session with
    a real character row, composes a real `/warp` frame through the real
    router, and then calls `AcceptedGameSocket.sendall` -- the same method
    `current/pf_login_game_server_v141.py:7755` calls through
    `__getattr__` today.  Nothing below reaches into
    `_offer_send_outcome`; the only thing this lane does is install the
    two names on the session, which is the ONE step still missing on main.

    THE NEGATIVE CONTROL IS THE POINT OF THE CLASS.  `test_without_the_
    install_...` reproduces main's behaviour today: the identical failure,
    on the identical socket, leaves the row wrong and the park orphaned.
    If someone deletes `install_send_outcome_observers` and this class
    still passes, the class is worthless -- so that test asserts the
    BROKEN outcome deliberately, and the two beside it assert the fixed
    one.

    NONCLAIM.  The raw socket here is a fake object with a `sendall`
    method; no byte reaches a network, no client is involved, and nothing
    here is evidence about a screen.  It is evidence about which rows the
    server holds after a send raises.
    """

    class _RawSocket:
        """The two methods the facade touches, and a record of the bytes."""

        def __init__(self, error=None):
            self.error = error
            self.sent = []

        def sendall(self, data, *args, **kwargs):
            if self.error is not None:
                raise self.error
            self.sent.append(bytes(data))
            return None

        def shutdown(self, how):
            return None

        def close(self):
            return None

    def _accepted(self, session, error=None):
        """Bind through the real facade, on the branches production takes.

        pf-adversary D7 (MEASURED, round `goxj0y`): `_Session` carries only
        `foundation` / `events` / `token`, so `AcceptedGameSocket.bind`
        skipped its `attach_transport_socket_closer` branch
        (`connection.py:97-99`) and `GameConnectionBindings.release` had no
        `close_connection` to call -- two behaviours the real state class
        DOES have (`runtime.py:1625`, `runtime.py:1607`) around the very
        call this round proposes to append the install to.  The two members
        are grafted on here, and `release()` is exercised, so the fixture
        walks the same branches rather than a shorter path that happens to
        agree.
        """
        closers = []
        session.attach_transport_socket_closer = closers.append
        session.close_connection = lambda: True

        raw = self._RawSocket(error)
        bindings = connection.GameConnectionBindings()
        wrapped = bindings.accepted(raw)
        bindings.bind(session)
        self.assertIs(wrapped.state, session)
        # bind() really took the opt-in branch, rather than silently
        # skipping it the way it did for the barer fixture.
        self.assertEqual(len(closers), 1)
        self.addCleanup(self._release, bindings, wrapped)
        return wrapped, raw

    def _release(self, bindings, wrapped):
        """Exit the connection the way production does.  Idempotent."""
        if not wrapped.released:
            self.assertTrue(bindings.release(wrapped))

    def _warp_frame(self, session):
        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertIsNotNone(verdict.action)
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIsNotNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE),
        )
        return bytes(verdict.action[2])

    def test_a_failed_send_on_the_real_facade_puts_the_row_back(self):
        session = self._session("facade01")
        self.assertEqual(
            warp_send_watch.install_send_outcome_observers(session),
            warp_send_watch.INSTALL_OK,
        )
        before = self._row(session)
        self.assertEqual(before.scene_id, 1)
        frame = self._warp_frame(session)

        wrapped, _raw = self._accepted(session, ConnectionResetError(104, "reset"))
        stream = io.StringIO()
        with redirect_stderr(stream):
            # The facade must NEVER swallow the error: v141's own catch is
            # what decides to break the action list.
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(frame)

        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertEqual(
            (after.x, after.y, after.z), (before.x, before.y, before.z),
        )
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))
        self.assertIn(warp_scene_persist.ROLLBACK_CONSOLE_TOKEN, stream.getvalue())

    def test_a_successful_send_on_the_real_facade_keeps_the_row_and_clears(self):
        session = self._session("facade02")
        warp_send_watch.install_send_outcome_observers(session)
        frame = self._warp_frame(session)

        wrapped, raw = self._accepted(session)
        with redirect_stderr(io.StringIO()):
            wrapped.sendall(frame)

        self.assertEqual(raw.sent, [frame])
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_an_earlier_frames_failure_on_the_real_facade_still_rolls_back(self):
        """v141 breaks the whole action list on the first failure, so the
        warp's own bytes never reach `sendall`.  The facade only ever
        reports the frame it was handed -- here, a `say`'s."""
        session = self._session("facade03")
        warp_send_watch.install_send_outcome_observers(session)
        before = self._row(session)
        self._warp_frame(session)

        wrapped, _raw = self._accepted(session, BrokenPipeError(32, "pipe"))
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(BrokenPipeError):
                wrapped.sendall(b"an-earlier-say-frames-bytes")

        self.assertEqual(self._row(session).scene_id, before.scene_id)
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

    def test_without_the_install_the_same_failure_leaves_the_row_wrong(self):
        """The defect the installer closes, kept as the measurement of WHY.

        REWRITTEN BY CHIEF, round `rs8uyz`/R350, as edit (3) of the three
        `HookupWiringPinTests` demanded from the commit that lands the
        call.  It used to open "MAIN'S BEHAVIOUR TODAY, asserted on
        purpose", and it was: R348 measured that no class in `src/`
        declared either observer name, so `getattr(self.state, hook_name,
        None)` (`connection.py:154`) found nothing and this module was
        never reached in production.  **That stopped being true in the
        same commit as this edit** -- `runtime.py` now installs both
        forwards on every accepted connection -- and a test that keeps
        claiming to describe `main` after `main` moved is worse than no
        test, because the next round greps it and believes it.

        What it measures is unchanged and still worth having: a session
        that never had the installer run gets NO rollback.  The row stays
        at a destination the client never reached and the park is orphaned
        for the life of the connection.  That is the cost of the hookup
        being absent, which is exactly what makes the two tests above
        mean something -- they are otherwise green against a module that
        might do nothing at all.

        It is NO LONGER a canary for "the hookup landed somewhere else".
        It never could be: pf-adversary D2 measured that it binds
        `_Session`, a fixture defined in this file, so nothing chief does
        to the real state class can move it.  `HookupWiringPinTests` is
        the canary now, and it reads `runtime.py` itself.
        """
        session = self._session("facade04")
        self.assertIsNone(
            getattr(session, warp_send_watch.SENT_OBSERVER_ATTRIBUTE, None),
        )
        before = self._row(session)
        self._warp_frame(session)

        wrapped, _raw = self._accepted(session, ConnectionResetError())
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(b"whatever")

        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertNotEqual(self._row(session).scene_id, before.scene_id)
        self.assertIsNotNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE),
        )

    def test_a_half_declared_class_no_longer_corrupts_the_row(self):
        """pf-adversary D1's own measured scenario, through the real facade.

        Chief takes shape A but only ONE method lands (a merge trim, or any
        future lane adding an attribute of that name).  Before the fix the
        installer refused outright, so with only `on_game_frame_send_failed`
        declared: a `/warp` whose frame REALLY REACHED THE WIRE was never
        cleared (no success observer), and the next unrelated disconnect
        rolled the durable row back to scene 1 while the client was really
        standing in scene 2.  Refusing produced durable position
        corruption.  The installer now supplies only the MISSING name, so
        the successful send closes the window and the later failure finds
        nothing to undo.
        """
        session = self._session("facade05")
        seen = []
        # Only the failure half is declared, the way a trimmed shape A looks.
        session.on_game_frame_send_failed = (
            lambda frame_bytes, error: seen.append(error) or "chiefs"
        )
        with redirect_stderr(io.StringIO()):
            self.assertEqual(
                warp_send_watch.install_send_outcome_observers(session),
                warp_send_watch.INSTALL_COMPLETED_HALF_DECLARED,
            )
        frame = self._warp_frame(session)

        wrapped, raw = self._accepted(session)
        with redirect_stderr(io.StringIO()):
            wrapped.sendall(frame)
        self.assertEqual(raw.sent, [frame])
        # The window really closed -- this is the assertion that used to be
        # False, and the reason the later failure could corrupt the row.
        self.assertIsNone(getattr(session, warp_send_watch.SESSION_ATTRIBUTE))

        # A later, unrelated disconnect on the same connection.
        later, _raw2 = self._accepted(session, ConnectionResetError())
        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                later.sendall(b"some-later-frame")

        # chief's own half still owns the failure side -- it was never
        # shadowed, and it really fired.
        self.assertEqual(len(seen), 1)
        self.assertIsInstance(seen[0], ConnectionResetError)
        # And the row is still where the client actually is.
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)


class HookupWiringPinTests(RealDatabaseTests):
    """Is the hookup REALLY on, on an object production really builds?

    ROUND `j2jluj` REWROTE THIS CLASS.  It used to answer that question by
    reading `runtime.py` as text and asking whether the string
    `"install_send_outcome_observers("` appeared anywhere in it.
    pf-adversary killed that in round `rs8uyz`/R350, and chief published the
    mutant (`pf_bridge/notes_to_chief/20260905_0902_FROM_CHIEF_R350_
    ADVERSARY-RESULT-wired-must-mean-observed-not-named.md`): comment the
    real call out, assign two no-op lambdas to the same two names, and
    `/warp` send-failure rollback is completely dead in production while
    all 10,598 tests -- these included -- stay byte-identical.  A
    commented-out line is still a substring.

    ~~`_wiring_present` / `HOOKUP_IS_ON_MAIN`: either shape of
    `CORE-REQUEST-GM-058`, as it would really appear in the text of
    `runtime.py`.~~  STRUCK, not deleted: the pin was right to exist and
    right about WHERE to look, and it did force the three edits it was
    built to force when shape B landed.  It was wrong about WHAT to look
    at.  `COO-DECISION 20260905_0947` made that a house rule -- "WIRED =
    observed, not named", and `getattr(...) is not None`, `callable(...)`,
    a substring and an AST name scan are all explicitly not guards -- and
    `COO-DECISION 20260905_0948` item 2(a) ordered this class rewritten to
    anchor on the event instead.

    WHAT IT ANCHORS ON NOW, AND WHY THAT CANNOT BE FORGED.  The event
    `gm_warp_send_watch_install_installed` has exactly ONE writer in the
    whole codebase -- `warp_send_watch._announce_install` -- and it is
    written onto the session that was passed in.  So its presence on a
    session that came out of `make_state_class(...)` + `GameConnectionBindings.
    accepted()` + `bind()` (the three production steps, in production
    order, from `runtime.py`'s own `__init__` and `connection.py`'s own
    binding protocol) means the REAL installer really ran on THAT REAL
    object.  No lambda, no stub, no `getattr` and no comment can put it
    there.

    WHAT THE EVENT ALONE DOES *NOT* PROVE, said plainly because a sentence
    here once claimed more than the assertions make (pf-adversary D-4,
    round `j2jluj`).  Since `WIRED_INSTALL_OUTCOMES` widened this to accept
    every outcome that means "this connection is wired", the event proves
    the installer RAN and did not refuse -- it does not by itself prove the
    two observers are live, because `refused_already_present` is a correct
    answer for a class that declares them itself.  pf-adversary built the
    mutant that walks through exactly that gap (assign two no-op lambdas
    BEFORE the installer, so it answers `refused_already_present`) and
    measured: this assertion passes it, and the two end-to-end row tests
    below kill it.  The class is the guard; this test is one half of it.  Chief's own `tests/test_connection_lifecycle.py` pins the same
    event from his side of the seam; this is the same standard applied on
    the lane that owns the module, so a revert of either half is caught by
    the half that did not move.

    AND ONE STEP FURTHER THAN THE EVENT.  `test_a_real_send_failure_on_a_
    production_built_session_puts_the_row_back` does not read the trail at
    all: it builds the production session, moves a REAL character row with
    a REAL `/warp` through the REAL router, makes the REAL
    `AcceptedGameSocket.sendall` raise, and reads the DATABASE ROW back.
    That is the whole chain -- constructor, installer, facade, observer,
    store -- observed end to end, with nothing in it this file supplied.

    NONCLAIM.  The raw socket is a fake object with a `sendall`; no byte
    reaches a network and no client is involved.  This is evidence about
    which rows the server holds after a send raises, not about a screen.
    """

    class _RawSocket:
        """The three methods the facade touches, and a record of the bytes."""

        def __init__(self, error=None):
            self.error = error
            self.sent = []

        def sendall(self, data, *args, **kwargs):
            if self.error is not None:
                raise self.error
            self.sent.append(bytes(data))
            return None

        def shutdown(self, how):
            return None

        def close(self):
            return None

    def _production_session(self, token, error=None):
        """The three steps production takes, in production's order.

        `runtime.py`'s state `__init__` is what calls
        `connection_bindings.bind(self)` and then the installer, so the ONLY
        thing this helper supplies is the accepted socket that `bind` needs
        -- exactly what `game_listener` supplies on a real login.  Nothing
        here installs anything itself; if the constructor stops doing it,
        every assertion below has nothing to find.
        """
        bindings = connection.GameConnectionBindings()
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
            connection_bindings=bindings,
        )
        raw = self._RawSocket(error)
        wrapped = bindings.accepted(raw)
        stream = io.StringIO()
        with redirect_stderr(stream):
            state = state_type(token)
        self.assertIs(wrapped.state, state)
        self.addCleanup(self._release, bindings, wrapped)
        return state, wrapped, raw, stream.getvalue()

    def _release(self, bindings, wrapped):
        if not wrapped.released:
            with redirect_stderr(io.StringIO()):
                bindings.release(wrapped)

    def _adopt_character(self, state, login_name):
        """Give the production-built session a real, selected character.

        `_session` (this fixture's own helper) builds a `FoundationSession`
        by hand for the lighter `_Session` double; here the session already
        exists and came out of `runtime.py`, so only the character half is
        supplied -- through the SAME `create` / `select_and_start` calls a
        real login makes.  Returns the row as it stands before any warp.
        """
        foundation = state.foundation
        _op, _has_actor, wire = self.legacy.parse_create_actor(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC),
        )
        character, _reply = foundation.create(
            self.legacy.decode_create_actor_data_ex(wire)["name"], wire,
        )
        with redirect_stderr(io.StringIO()):
            foundation.select_and_start(character.selector)
        return self._row(state)

    def _warp_on(self, state):
        with redirect_stderr(io.StringIO()):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                state, DESTINATION_SCENE, self.legacy,
            )
        self.assertIsNotNone(verdict.action)
        self.assertIsNotNone(getattr(state, warp_send_watch.SESSION_ATTRIBUTE))
        return bytes(verdict.action[2])

    def _install_events(self, state):
        return [
            event for event in getattr(state, "events", [])
            if isinstance(event, str)
            and event.startswith(f"{warp_send_watch.EVENT_PREFIX}install_")
        ]

    #: The three outcomes that all mean "this connection is wired".  Only
    #: `refused_not_writable` means it is not.  pf-adversary D5 (round
    #: `j2jluj`, MEASURED): the first draft asserted `INSTALL_OK` alone, so
    #: landing shape A -- two real forwarding methods on chief's own class,
    #: which this module's docstring says is still supported and still
    #: compatible -- turned this pin RED with a message blaming the R350
    #: mutant, while the end-to-end row test beside it stayed green because
    #: production really was wired.  A pin that reds on the supported
    #: alternative is a pin that will be deleted by whoever lands it.
    WIRED_INSTALL_OUTCOMES = (
        warp_send_watch.INSTALL_OK,
        warp_send_watch.INSTALL_COMPLETED_HALF_DECLARED,
        warp_send_watch.INSTALL_REFUSED_ALREADY_PRESENT,
    )

    def test_the_real_installer_ran_on_a_production_built_session(self):
        state, _wrapped, _raw, stderr_text = self._production_session("pin01")
        events = self._install_events(state)
        self.assertEqual(
            len(events), 1,
            "expected exactly one install announcement on a session built the "
            "way production builds one, got "
            f"{events!r}. Either runtime.py no longer calls "
            "install_send_outcome_observers on the line after "
            "connection_bindings.bind(self), or something else is supplying "
            "those two names -- which is pf-adversary's R350 D1 mutant, and "
            "it disarms /warp send-failure rollback silently.",
        )
        self.assertIn(
            events[0].rsplit("install_", 1)[1],
            self.WIRED_INSTALL_OUTCOMES,
            "the installer ran and REFUSED on a production session: this "
            "connection cannot carry the two observers at all, so a failed "
            f"/warp send will not roll back on it. {events[0]!r}",
        )
        # The second channel `_announce_install` writes, for the owner
        # grepping a boot log rather than a test reading a trail.
        self.assertIn(warp_send_watch.INSTALL_CONSOLE_TOKEN, stderr_text)

    def test_the_two_names_a_lambda_could_fake_are_not_what_is_asserted(self):
        """The guard chief's first draft had, kept ONLY as a cross-check.

        `callable(...)` is explicitly not a guard under the `0947` rule.  It
        is asserted here anyway, immediately beside the event, because the
        two together say something neither says alone: the names resolve AND
        the thing that put them there was the real installer.  If a future
        round ever deletes the event assertion, this one alone must not be
        mistaken for a pin -- hence this docstring.
        """
        state, _wrapped, _raw, _stderr = self._production_session("pin02")
        for name in (
            warp_send_watch.SENT_OBSERVER_ATTRIBUTE,
            warp_send_watch.FAILED_OBSERVER_ATTRIBUTE,
        ):
            self.assertTrue(callable(getattr(state, name, None)), name)
        self.assertEqual(len(self._install_events(state)), 1)

    def test_a_real_send_failure_on_a_production_built_session_puts_the_row_back(
        self,
    ):
        """Constructor, installer, facade, observer, store -- end to end."""
        state, wrapped, _raw, _stderr = self._production_session(
            "pin03", error=ConnectionResetError(),
        )
        before = self._adopt_character(state, "pin03")
        frame = self._warp_on(state)
        self.assertEqual(self._row(state).scene_id, DESTINATION_SCENE)

        with redirect_stderr(io.StringIO()):
            with self.assertRaises(ConnectionResetError):
                wrapped.sendall(frame)

        self.assertEqual(self._row(state).scene_id, before.scene_id)
        self.assertIsNone(getattr(state, warp_send_watch.SESSION_ATTRIBUTE))

    def test_a_real_successful_send_on_a_production_built_session_clears_the_park(
        self,
    ):
        """The other side of the same chain: nothing is rolled back when the
        frame really does reach the wire, and the park retires."""
        state, wrapped, raw, _stderr = self._production_session("pin04")
        self._adopt_character(state, "pin04")
        frame = self._warp_on(state)

        with redirect_stderr(io.StringIO()):
            wrapped.sendall(frame)

        self.assertEqual(raw.sent, [frame])
        self.assertEqual(self._row(state).scene_id, DESTINATION_SCENE)
        self.assertIsNone(getattr(state, warp_send_watch.SESSION_ATTRIBUTE))

    def test_the_bind_point_this_lane_asks_chief_for_still_exists(self):
        """A pin on the ADDRESS in the letter, and NOT a wiring guard.

        Deliberately kept after the rewrite, and deliberately named for what
        it is: `CORE-REQUEST-GM-058` and this module's docstring both point
        at the line after `connection_bindings.bind(self)`, and if that call
        is ever moved or renamed both documents point at nothing.  Under the
        `0947` rule this is a DOCUMENTATION pin, not evidence that anything
        is wired -- the four tests above are that.
        """
        source = (
            ROOT / "src" / "pirateforce_foundation" / "runtime.py"
        ).read_text(encoding="utf-8")
        self.assertIn("connection_bindings.bind(self)", source)


class SendLockLivenessTests(RealDatabaseTests):
    """R348's OTHER half, ordered measured rather than argued.

    `COO-DECISION 20260905_0948` item 2(b): "answer your own liveness
    question with a test, not a letter: `send_lock` is held across a
    rollback that opens a new sqlite connection while `heartbeat_worker`
    fires every 2.0s -- measure whether the heartbeat stalls; if it does,
    fix it in the same round; if it does not, pin the test that proves it."
    This lane had asked that question twice (this module's own docstring,
    `CrossThreadObserverTests`'s "what this does not answer, on purpose")
    and chief's R350 letter confirmed nobody -- including chief -- had
    answered it.

    THE REAL SHAPE, WHICH IS WHAT MAKES THE NUMBERS MEAN ANYTHING.  Every
    `sendall()` on one connection is made under that connection's own
    `send_lock` (`current/pf_login_game_server_v141.py:7754` the action
    loop, `:7427` `heartbeat_worker`), and this module's observers are
    reached from INSIDE `sendall()` (`connection.py`'s
    `_offer_send_outcome`).  So a rollback's disk I/O really does run with
    that lock held, and the other thread really is behind it.  The tests
    below hold a REAL `threading.Lock` across a REAL rollback against the
    REAL store, with a REAL second writer holding `BEGIN IMMEDIATE`, and
    time it.

    THE ANSWER: IT STALLS, AND ONE CALL'S STALL IS BOUNDED AT ONE
    `busy_timeout`.  Measured on this tree (the table is in
    `warp_send_watch.py`'s module docstring): 0.0023s uncontended, tracking
    the contention while it is under the budget, and 5.010s -- never ten --
    beyond it.  Never ten because `checkpoint()` never reaches the
    read-back: `save_position` (`store.py:668-671`) is a bare
    `with self.connect() as db:` + `UPDATE`, an implicit DEFERRED
    transaction, and it is that `UPDATE` that waits and raises, so the
    second connection is never opened.  (pf-adversary D7, round `j2jluj`:
    an earlier draft of this paragraph said "fails at `BEGIN IMMEDIATE`".
    `SQLiteStore.connect()` issues no such statement; `BEGIN IMMEDIATE`
    belongs to the healing doors and to this class's own contending writer.
    The non-stacking therefore rests on WAL, which
    `test_the_database_is_really_in_wal_mode` now asserts rather than
    assumes.)  Worst case therefore costs `heartbeat_worker` at most two of
    its 2.0s beats, on a connection whose socket has just failed.

    WHAT ROUND `j2jluj` CHANGED, AND WHAT IT DELIBERATELY DID NOT.  It did
    not shorten the wait: `busy_timeout` lives in `store.py`, outside this
    lane's zone, and shortening it would trade a bounded delay on a dying
    connection for a durable row left naming a scene the client never
    reached.  It also did not change `on_game_frame_send_failed` -- a
    re-park-and-retry for the >5s case was built this round and WITHDRAWN
    before pushing, on this round's own two `pf-adversary` passes; see the
    module docstring for both defects and for the design question underneath
    them.  So `test_a_busy_database_leaves_the_row_wrong_and_says_nothing`
    below pins the DEFECT as it stands on `main`, deliberately, rather than
    a half-understood fix to the durable position path.

    NONCLAIM.  Headless.  No socket, no client, no screen.  These are wall
    clock numbers about one process's own lock and its own sqlite file.
    """

    #: `current/pf_login_game_server_v141.py:7420` -- `conn_done.wait(2.0)`.
    HEARTBEAT_PERIOD_S = 2.0

    @staticmethod
    def _busy_timeout_seconds():
        """`store.py`'s own `PRAGMA busy_timeout`, DERIVED not retyped.

        pf-adversary D9 (round `j2jluj`): a hand-typed 5.0 here is a number
        that stops being re-derivable the day `store.py` changes its budget
        -- the assertions would stay green while the measurement table in
        `warp_send_watch.py`'s docstring went stale with nothing to say so.
        Read out of the file instead, and fail loudly if the pragma this
        whole class is about is no longer there to read.
        """
        source = (
            ROOT / "src" / "pirateforce_foundation" / "store.py"
        ).read_text(encoding="utf-8")
        found = re.findall(r"PRAGMA busy_timeout=(\d+)", source)
        if not found:
            raise AssertionError(
                "store.py no longer sets PRAGMA busy_timeout anywhere: the"
                " bound these tests measure has moved, and the numbers in"
                " gm/warp_send_watch.py's docstring are now unsourced."
            )
        return int(found[0]) / 1000.0

    def setUp(self):
        super().setUp()
        self.BUSY_TIMEOUT_S = self._busy_timeout_seconds()

    def _hold_the_write_lock(self, seconds):
        """A second writer, on its own thread, holding `BEGIN IMMEDIATE`.

        The ordinary shape of contention on this database: another
        connection in the middle of its own transaction.  Returns once the
        lock is REALLY held.

        pf-adversary D8 (round `j2jluj`): the first draft signalled from a
        `finally`, so a `BEGIN IMMEDIATE` that RAISED (any pre-existing
        writer) still reported "held" and the caller then measured an
        uncontended call while believing it was contended -- a wrong
        diagnosis, not a false green, but a wrong diagnosis on the one
        fixture the whole class rests on.  The flag is now set only on the
        line after the statement that took the lock, the failure is carried
        back across the thread boundary, and the join has a bound.
        """
        held = threading.Event()
        finished = threading.Event()
        failure: list = []

        def _hog():
            db = sqlite3.connect(str(self.store.path))
            try:
                db.execute(
                    f"PRAGMA busy_timeout={int(self.BUSY_TIMEOUT_S * 1000)}"
                )
                db.execute("BEGIN IMMEDIATE")
                held.set()
                time.sleep(seconds)
                db.rollback()
            except BaseException as error:  # noqa: BLE001 - re-raised below
                failure.append(error)
            finally:
                finished.set()
                db.close()

        thread = threading.Thread(target=_hog)
        thread.start()
        self.addCleanup(self._join_hog, thread, finished, failure, seconds)
        self.assertTrue(
            held.wait(10) or finished.wait(0),
            "the contending writer never took the write lock",
        )
        if failure:
            raise failure[0]
        return thread

    def _join_hog(self, thread, finished, failure, seconds):
        thread.join(timeout=seconds + 30)
        self.assertFalse(thread.is_alive(), "the contending writer wedged")
        self.assertTrue(finished.is_set())
        if failure:
            raise failure[0]

    def test_the_database_is_really_in_wal_mode(self):
        """The non-stacking bound rests on WAL, so it is asserted, not hoped.

        pf-adversary D7 (round `j2jluj`): `SQLiteStore.connect()` opens an
        implicit DEFERRED transaction, so "one budget, not two" is a
        property of WAL rather than of the transaction shape, and
        `connect()` sets WAL only for a file database (`store.py:293-294`)
        -- `PRAGMA journal_mode=WAL` can also silently fail to take on some
        mounts.  If this ever comes back anything but `wal`, the lock
        escalation moves to COMMIT and the numbers in this class stop being
        the numbers production sees.
        """
        with self.store.connect() as db:
            mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        self.assertEqual(str(mode).lower(), "wal")

    def _timed_failed_send(self, session, frame):
        started = time.monotonic()
        with redirect_stderr(io.StringIO()):
            outcome = warp_send_watch.on_game_frame_send_failed(
                session, frame, ConnectionResetError(),
            )
        return outcome, time.monotonic() - started

    def test_an_uncontended_rollback_costs_far_less_than_one_heartbeat(self):
        """The ordinary case, which is every case where nothing else is
        writing: the lock is held for milliseconds, not beats."""
        session = self._session("live01")
        frame = self._park(session)
        outcome, held = self._timed_failed_send(session, frame)
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        self.assertEqual(self._row(session).scene_id, 1)
        self.assertLess(
            held, self.HEARTBEAT_PERIOD_S / 2,
            f"an uncontended rollback held send_lock for {held:.3f}s; measured"
            " 0.0023s on this tree, and anything approaching one heartbeat"
            " period here means the undo grew disk work it did not have.",
        )

    # KNOWN_DEFECT -- delete in the PR that fixes it (COO 1150)
    def test_a_busy_database_leaves_the_row_wrong_and_says_nothing(self):
        """The worst case -- pinned as the DEFECT it still is on `main`.

        One contending writer holds the database for longer than the store's
        own budget.  Three facts, and the third is the one worth having:

        1. The hold is bounded by ONE budget, not the two connections' worth
           the undo would need if it reached its read-back.
        2. The undo is REFUSED: the outcome is the busy-database word.
        3. The park is cleared anyway, so the durable row is left at a scene
           the client was never sent to, and nothing on this connection will
           ever try again.

        Fact 3 is the character-bricking shape this whole module exists to
        refuse, reached through a busy database instead of a refused write.
        Round `j2jluj` built a re-park-and-retry for it and WITHDREW it
        before pushing (see the class docstring), so this test asserts the
        broken outcome ON PURPOSE, the same way
        `LiveSocketFacadeTests.test_without_the_install_the_same_failure_
        leaves_the_row_wrong` asserts its own.  It is the measurement the
        letter to COO cites, and it goes red the day someone fixes it --
        which is the point.
        """
        session = self._session("live02")
        frame = self._park(session)
        # pf-adversary D9: three seconds of headroom past the budget, not
        # one, so a scheduling gap between the hog taking the lock and this
        # thread reaching sqlite cannot turn a real measurement into a red.
        self._hold_the_write_lock(self.BUSY_TIMEOUT_S + 3.0)

        outcome, held = self._timed_failed_send(session, frame)

        self.assertEqual(
            outcome,
            f"{warp_scene_persist.OUTCOME_ROLLBACK_REFUSED_PREFIX}"
            "OperationalError",
        )
        self.assertLess(
            held, self.BUSY_TIMEOUT_S * 2,
            f"the hold was {held:.3f}s. One `PRAGMA busy_timeout` is the"
            " bound because save_position's own UPDATE waits and raises, so"
            " the read-back's second connection is never opened; two"
            " budgets' worth means that stopped being true and"
            " heartbeat_worker now waits twice as long.",
        )
        # 3. The row is wrong and the park that could have fixed it is gone.
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIsNone(
            getattr(session, warp_send_watch.SESSION_ATTRIBUTE),
            "if this is no longer None someone has given the undo a second"
            " chance -- good, but then this test's whole subject has moved"
            " and it must be rewritten rather than relaxed.",
        )

    def test_the_other_threads_next_send_waits_behind_the_rollback_and_then_goes(
        self,
    ):
        """`heartbeat_worker`'s own position, reproduced with v141's lock.

        One `threading.Lock` shared by both threads, exactly as v141 shares
        one per connection.  The action-loop thread takes it and calls this
        module's observer inside it, the way `connection.py` does from
        inside `sendall()`; the heartbeat thread then asks for the same
        lock.  What is measured is how long the heartbeat waits -- the
        question, in the shape it is really asked.

        The answer is a WAIT, not a hang: it is at least one 2.0s beat under
        this contention, and it ends.  A starved heartbeat would never reach
        the assertion at all.
        """
        session = self._session("live03")
        frame = self._park(session)
        # D9 again: 5.0s of contention against a >= 2.0s assertion leaves
        # three seconds of slack instead of one.
        contention = 5.0
        self._hold_the_write_lock(contention)

        send_lock = threading.Lock()
        holding = threading.Event()
        rollback_outcome: list = []
        heartbeat_waits: list = []

        def action_loop():
            with send_lock:
                holding.set()
                with redirect_stderr(io.StringIO()):
                    rollback_outcome.append(
                        warp_send_watch.on_game_frame_send_failed(
                            session, frame, ConnectionResetError(),
                        )
                    )

        def heartbeat_worker():
            # Only contend once the other thread really holds it, so this
            # measures the wait and not a start-up race.
            holding.wait(10)
            asked_at = time.monotonic()
            with send_lock:
                heartbeat_waits.append(time.monotonic() - asked_at)

        sender = threading.Thread(target=action_loop)
        heartbeat = threading.Thread(target=heartbeat_worker)
        sender.start()
        heartbeat.start()
        sender.join(timeout=30)
        heartbeat.join(timeout=30)
        self.assertFalse(sender.is_alive())
        self.assertFalse(heartbeat.is_alive(), "the heartbeat never got the lock")

        # Which outcome the undo reached is NOT this test's subject, and
        # pinning it here would put the contention exactly on the budget's
        # edge to satisfy two assertions at once (pf-adversary D9).  Either
        # word is a real run of the code path being timed; the row is
        # asserted only for the one that claims to have moved it.
        self.assertIn(
            rollback_outcome[0],
            (
                warp_scene_persist.OUTCOME_ROLLED_BACK,
                f"{warp_scene_persist.OUTCOME_ROLLBACK_REFUSED_PREFIX}"
                "OperationalError",
            ),
        )
        if rollback_outcome[0] == warp_scene_persist.OUTCOME_ROLLED_BACK:
            self.assertEqual(self._row(session).scene_id, 1)
        waited = heartbeat_waits[0]
        self.assertGreaterEqual(
            waited, self.HEARTBEAT_PERIOD_S,
            f"the heartbeat waited only {waited:.3f}s under {contention:.1f}s"
            " of database contention. If this stops being true the fixture"
            " has stopped reproducing the shape it exists to measure, not"
            " the stall has been fixed.",
        )
        self.assertLess(
            waited, self.BUSY_TIMEOUT_S * 2,
            f"the heartbeat waited {waited:.3f}s -- more than the store's own"
            " budget can explain, which means something in the undo now"
            " blocks without one.",
        )


# pf-adversary D9 (MEASURED, round `goxj0y`): this block used to sit ABOVE the
# classes appended by that round, so `python tests/test_gm_warp_send_watch.py`
# ran 51 of 72 tests and printed OK.  CI is unaffected (`AGENTS.md:123` and
# `.github/workflows/gate-windows.yml` both drive pytest), but a human
# spot-checking the very file this round is defended by got a green that meant
# nothing.  It belongs last, and every future append goes ABOVE it.
if __name__ == "__main__":  # pragma: no cover
    unittest.main()
