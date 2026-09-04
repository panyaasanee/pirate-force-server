"""The three defects `pf-adversary` measured against `#745` in round `741zlx`.

The round's job was the SECOND adversary pass over the CRITICAL D1/D2 fix
(`COO-DECISION 20260904_1744` item 3, restated by `20260904_1848` item 2).
It found the fix itself sound and three things around it that were not.  This
file is the pinning half of each.

FINDING 1 (CRITICAL, MEASURED).  A WITHHELD `/warp <n>` still moved the row.
`chat_command_action._make_action` withholds a composed action when the
`outcome` audit row cannot be appended -- it reverts the staged config, it
clears the parked warp target, it sets `action = None`, and it runs
`verdict.undo` for exactly this case.  `_warp_teleport_action_no_coords`
returned `undo=None`, while `_Verdict.undo`'s own docstring reserves that for
"a handler that already changed durable state by the time it returns".  So
with one injected fault the production code already handles (a
`log_gm_command_outcome` that raises `OSError` -- a full disk, a read-only
capture directory) the measurement was: zero bytes on the wire,
`character_positions` reading the destination scene, the in-memory row still
in the departure scene, and the next login landing where the client was never
sent.  That is the character-bricking shape `CHARTER-02` rule 2 forbids, and
it falsified `warp_scene_persist`'s own stated rule ("a refused warp leaves no
bytes on the wire and must leave no row change either").

FINDING 3 (MAJOR, MEASURED).  `print(..., file=sys.stderr)` writes to STDOUT
when `sys.stderr` is `None` -- a detached console, `pythonw`, a harness that
closed it -- and raises nothing, so neither call site's `try/except` could
see it.  Both tokens landing on stdout is the `lane_hooks` JSON-artifact
incident the sibling call site next door already guards against by name, and
it is the whole reason this module chose stderr.

FINDING 4 (MAJOR, MEASURED).  A stderr whose `write()` raises cost the token
SILENTLY: `persisted` came back with no console line at all and no event from
the module.  `COO-DECISION 20260904_1646` item 2's premise is that a tester
reads the CONSOLE, so a line that is lost without a record rebuilds the exact
blindness `#750` was written to abolish.

NONCLAIM.  Headless, server-side.  Nothing here is evidence about a screen, a
scene rendering, or `GT-172` F-3; no account gains or loses GM status, and no
GM step is skipped -- these are refusals and undos, not shortcuts.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command as gm_chat_command,
    chat_command_action,
    dispatch as gm_dispatch,
    login_scene_override,
    warp_scene_persist,
)
from pirateforce_foundation.gm.warp_executor import WarpTarget  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.session import FoundationSession  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: Prison Exile: marker-backed, `login_entry_allowed` true, the destination
#: the owner typed in R309 and the one every sibling file uses.
DESTINATION_SCENE = 2

#: Pinned `login_entry_allowed=False`, so the forward write refuses it.
REFUSED_SCENE = 126


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _chat_payload(message: str, speaker: str = "") -> bytes:
    """0xAC52 payload in the GT-006/GT-009 measured shape.

    Copied rather than imported from `tests/test_gm_command_audit_outcome.py`
    for the reason this house imports nothing test-to-test: a helper that two
    files share silently couples what one of them may change.
    """
    import struct

    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(gm_chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


def _wire_floats(values):
    """What the spawn triple becomes after one round trip through the wire."""
    import struct

    return tuple(
        struct.unpack("<f", struct.pack("<f", value))[0] for value in values
    )


def _target(scene_id):
    """The scene's own pinned spawn, as `WarpTarget` -- the same helper shape
    `tests/test_gm_warp_scene_persist.py` uses, for the same reason: the
    coordinates must be the binary32 values that go ON THE WIRE, or the
    read-back's full-row comparison is asked a question the write never
    answered."""
    spawn = world_scene_travel.spawn_position(
        world_scene_travel.destination(scene_id),
    )
    return WarpTarget(scene_id, *_wire_floats(spawn))


class _Session:
    """The two attributes these functions read off a runtime session."""

    def __init__(self, foundation):
        self.foundation = foundation
        self.events = []


class _RaisingStderr:
    """A stream whose `write` raises, the way a closed pipe behaves."""

    def write(self, _text):  # pragma: no cover - the raise IS the behaviour
        raise OSError("stderr is gone")

    def flush(self):  # pragma: no cover
        raise OSError("stderr is gone")


class RealDatabaseTests(unittest.TestCase):
    """Real store, real lifecycle, real session, real router."""

    def setUp(self):
        # Two of these tests drive the whole router, which rate-limits per
        # account across calls; without this reset the second one inherits
        # the first one's budget and the failure looks like a warp defect.
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

    # ---- finding 1: the undo exists, and it really puts the row back ----

    def test_the_no_coords_branch_hands_back_an_undo_that_restores_the_row(
        self,
    ):
        session = self._session("rollback01")
        before = self._row(session)
        self.assertEqual(before.scene_id, 1)

        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIsNotNone(verdict.undo)

        with redirect_stderr(stream):
            self.assertTrue(verdict.undo())

        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertEqual((after.x, after.y, after.z), (before.x, before.y, before.z))
        self.assertIn(
            f"{warp_scene_persist.ROLLBACK_CONSOLE_TOKEN} scene={before.scene_id}",
            stream.getvalue(),
        )
        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_ROLLBACK_PREFIX
            + warp_scene_persist.OUTCOME_ROLLED_BACK,
            session.events,
        )

    def test_a_refused_write_offers_no_undo_at_all(self):
        """An undo that could put nothing back must not be advertised.

        `_make_action` reports `EVENT_OUTCOME_STAGE_REVERTED` on the strength
        of the returned callable, so offering one here would turn "nothing
        happened" into a claim that something was reverted.
        """
        session = self._session("rollback02")
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome, undo = chat_command_action._persist_warp_scene(
                session, _target(REFUSED_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)
        self.assertIsNone(undo)
        self.assertEqual(self._row(session).scene_id, 1)

    def test_the_in_memory_row_is_left_alone_by_the_rollback_too(self):
        """Same rule as the forward write: the durable row moves, the
        connection's own copy of it does not."""
        session = self._session("rollback03")
        before_selected = session.foundation.selected
        stream = io.StringIO()
        with redirect_stderr(stream):
            _outcome, undo = chat_command_action._persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
            self.assertTrue(undo())
        self.assertIs(session.foundation.selected, before_selected)
        self.assertEqual(session.foundation.selected.position.scene_id, 1)

    def test_a_rollback_with_nothing_captured_says_so_rather_than_succeeding(
        self,
    ):
        session = self._session("rollback04")
        self.assertEqual(
            warp_scene_persist.rollback_warp_scene(session, None),
            warp_scene_persist.OUTCOME_NOTHING_TO_ROLL_BACK,
        )

    def test_a_raising_write_door_costs_the_rollback_not_the_thread(self):
        session = self._session("rollback05")
        previous = self._row(session)
        stream = io.StringIO()
        with redirect_stderr(stream):
            session.foundation.checkpoint = mock.Mock(
                side_effect=PermissionError("stale session"),
            )
            outcome = warp_scene_persist.rollback_warp_scene(session, previous)
        self.assertEqual(
            outcome,
            warp_scene_persist.OUTCOME_ROLLBACK_REFUSED_PREFIX + "PermissionError",
        )
        self.assertIn(
            f"{warp_scene_persist.ROLLBACK_FAIL_CONSOLE_TOKEN} "
            f"scene={previous.scene_id} reason={outcome}",
            stream.getvalue(),
        )

    def test_the_forward_write_still_returns_its_word_unchanged(self):
        """`persist_warp_scene`'s own contract did not move.

        The undo was added at the CALLER (`_persist_warp_scene`), not by
        changing what the module's public function answers -- 38 tests in
        `test_gm_warp_scene_persist.py` and every reader of the outcome word
        depend on that.
        """
        session = self._session("rollback06")
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertIsInstance(outcome, str)

    # ---- finding 1, END TO END, the way it was measured ----------------

    def test_a_withheld_warp_leaves_the_row_where_it_started(self):
        """The adversary's own scenario, reproduced and then closed.

        One injected fault the production code already handles --
        `log_gm_command_outcome` raising `OSError`, i.e. a full disk or a
        read-only capture directory -- through `make_gm_chat_command_action`,
        the real router, on a REAL `SQLiteStore`/`FoundationSession`.
        Measured before the fix: `action is None` (zero bytes on the wire) and
        `character_positions` reading scene 2.  A tester who then closed the
        client came back in a scene the client had never been sent to, and
        only another login could rewrite the row.

        The row assertion is the point of this test.  The event assertions
        below it are how a reader tells "the undo ran" from "there was
        nothing to undo", which `_make_action` deliberately reports as two
        different answers.
        """
        session = self._session("withheld01")
        session.token = "GM_ONE"
        before = self._row(session)
        self.assertEqual(before.scene_id, 1)

        config_path = Path(self.tmp.name) / "gm_accounts.json"
        config_path.write_text(
            '{"gm_accounts": ["GM_ONE"]}', encoding="utf-8",
        )
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

        # Nothing went out ...
        self.assertIsNone(action)
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            session.events,
        )
        # ... so nothing durable may be left behind.
        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertEqual(
            (after.x, after.y, after.z), (before.x, before.y, before.z),
        )
        self.assertIn(
            chat_command_action.EVENT_OUTCOME_STAGE_REVERTED, session.events,
        )
        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_ROLLBACK_PREFIX
            + warp_scene_persist.OUTCOME_ROLLED_BACK,
            session.events,
        )
        self.assertIn(warp_scene_persist.ROLLBACK_CONSOLE_TOKEN, stream.getvalue())

    def test_the_same_command_audited_normally_keeps_the_row(self):
        """The other half of the pair, and the reason it is not one test.

        An undo that fires on the ORDINARY path would be a worse bug than the
        one it fixes: it would silently withdraw `#745` entirely, and every
        test of the forward write would still pass because they never audit.
        """
        session = self._session("withheld02")
        session.token = "GM_ONE"

        config_path = Path(self.tmp.name) / "gm_accounts.json"
        config_path.write_text(
            '{"gm_accounts": ["GM_ONE"]}', encoding="utf-8",
        )
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
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertNotIn(
            chat_command_action.EVENT_WARP_SCENE_ROLLBACK_PREFIX
            + warp_scene_persist.OUTCOME_ROLLED_BACK,
            session.events,
        )
        self.assertNotIn(
            warp_scene_persist.ROLLBACK_CONSOLE_TOKEN, stream.getvalue(),
        )

    # ---- finding 2: scene 14 names the registry, not a phantom defect --

    def test_a_registry_forbidden_destination_says_the_registry_refused(self):
        """The production-reachable cause, executed for the first time.

        pf-adversary round `741zlx` finding 2: every `row_not_touched` test in
        `tests/test_gm_warp_scene_persist.py` stubs `foundation.checkpoint` to
        a no-op, so the ONE cause a real `/warp` can reach -- a destination
        pinned `persist_position_allowed=False`, where `lifecycle.checkpoint`
        calls `save_position(write_position=False)` and returns cleanly having
        written nothing -- had never run in any test.  It runs here, through
        the real store and the real lifecycle.

        Scene 14 is the one that matters: marker-backed and
        `login_entry_allowed=True`, so `login_would_accept` passes and it IS a
        live `/warp` destination, unlike 17 and 126.

        WHAT THIS TEST DOES NOT SAY: that `/warp 14` is fixed.  R309's gap is
        still open for that scene -- the frame goes out, the row does not
        move, the next login comes back to the departure scene.  Whether the
        registry should let scene 14 persist is a registry question this lane
        does not own; it is raised with COO in this round's letter.  What the
        fix here buys a tester is that the console now says WHY.
        """
        session = self._session("registry01")
        before = self._row(session)
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(session, _target(14))

        self.assertEqual(
            outcome, warp_scene_persist.OUTCOME_PERSIST_FORBIDDEN_BY_REGISTRY,
        )
        self.assertNotEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)
        # The row really did not move -- the reason word is about a fact.
        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertIn(
            f"{warp_scene_persist.FAIL_CONSOLE_TOKEN} scene=14 reason={outcome}",
            stream.getvalue(),
        )
        self.assertNotIn(
            warp_scene_persist.CONSOLE_TOKEN + " ", stream.getvalue(),
        )

    def test_a_store_that_silently_writes_nothing_still_says_row_not_touched(
        self,
    ):
        """The other side of the split, and the reason it is a split.

        `row_not_touched` keeps its honest meaning -- "the write door
        accepted this and the row did not move" -- which IS a defect and must
        never be laundered into the registry's deliberate refusal.  Scene 2
        is persistable, so the registry cannot be the explanation here.
        """
        session = self._session("registry02")
        stream = io.StringIO()
        with redirect_stderr(stream):
            session.foundation.checkpoint = lambda _position: None
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)

    def test_an_unreadable_registry_does_not_launder_a_real_defect(self):
        """Fails CLOSED to `row_not_touched`.

        Reporting a silent-write defect as "the registry refused" is the
        direction that HIDES a bug, so a registry that cannot answer must not
        be allowed to supply the kinder word.
        """
        session = self._session("registry03")
        stream = io.StringIO()
        with redirect_stderr(stream):
            session.foundation.checkpoint = lambda _position: None
            with mock.patch.object(
                warp_scene_persist.world_scene_travel,
                "is_position_persist_allowed",
                side_effect=OSError("registry gone"),
            ):
                outcome = warp_scene_persist.persist_warp_scene(
                    session, _target(DESTINATION_SCENE),
                )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)

    # ---- finding 3: a None stderr must not become stdout ---------------

    def test_a_none_stderr_never_sends_the_success_token_to_stdout(self):
        session = self._session("stderrnone01")
        out = io.StringIO()
        with mock.patch.object(warp_scene_persist.sys, "stderr", None):
            with redirect_stdout(out):
                outcome = warp_scene_persist.persist_warp_scene(
                    session, _target(DESTINATION_SCENE),
                )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertEqual(out.getvalue(), "")
        # The write still landed: losing the console line costs the line.
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)

    def test_a_none_stderr_never_sends_the_failed_token_to_stdout(self):
        session = self._session("stderrnone02")
        out = io.StringIO()
        with mock.patch.object(warp_scene_persist.sys, "stderr", None):
            with redirect_stdout(out):
                outcome = warp_scene_persist.persist_warp_scene(
                    session, _target(REFUSED_SCENE),
                )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)
        self.assertEqual(out.getvalue(), "")

    def test_a_none_stderr_never_sends_the_rollback_token_to_stdout(self):
        session = self._session("stderrnone03")
        previous = self._row(session)
        out = io.StringIO()
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        with mock.patch.object(warp_scene_persist.sys, "stderr", None):
            with redirect_stdout(out):
                outcome = warp_scene_persist.rollback_warp_scene(session, previous)
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        self.assertEqual(out.getvalue(), "")

    # ---- finding 4: a lost line is named, never silent -----------------

    def test_a_raising_stderr_leaves_a_named_event_for_the_lost_success_line(
        self,
    ):
        session = self._session("lostline01")
        with mock.patch.object(
            warp_scene_persist.sys, "stderr", _RaisingStderr(),
        ):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertIn(
            warp_scene_persist.EVENT_CONSOLE_WRITE_FAILED_PREFIX
            + warp_scene_persist.OUTCOME_PERSISTED,
            session.events,
        )

    def test_a_raising_stderr_leaves_a_named_event_for_the_lost_failed_line(
        self,
    ):
        session = self._session("lostline02")
        with mock.patch.object(
            warp_scene_persist.sys, "stderr", _RaisingStderr(),
        ):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(REFUSED_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)
        self.assertIn(
            warp_scene_persist.EVENT_CONSOLE_WRITE_FAILED_PREFIX + outcome,
            session.events,
        )

    def test_a_none_stderr_is_recorded_as_a_lost_line_too(self):
        """The `None` case is the one no `try/except` could ever see, so it
        is the one that most needs its own record."""
        session = self._session("lostline03")
        with mock.patch.object(warp_scene_persist.sys, "stderr", None):
            warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertIn(
            warp_scene_persist.EVENT_CONSOLE_WRITE_FAILED_PREFIX
            + warp_scene_persist.OUTCOME_PERSISTED,
            session.events,
        )

    def test_a_session_with_no_events_list_costs_nothing(self):
        """This runs on the game-listener thread inside error handling: a
        session shape with no `events` must not become a second way to take
        the thread down."""
        session = self._session("lostline04")
        del session.events
        with mock.patch.object(warp_scene_persist.sys, "stderr", None):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)


class SendFailureHookupTests(RealDatabaseTests):
    """`rollback_warp_scene_on_send_failure` -- `CORE-REQUEST-GM-055`'s own
    wrapper, exercised through the same real store/session/router
    `RealDatabaseTests` uses, BEFORE chief's `v141` call site exists to
    drive it directly.  Subclasses that class rather than repeating its
    `setUp`/`_session`/`_row`: the "no test-to-test imports" rule the file's
    header states is about coupling ACROSS files, not within one.

    THE LABEL GUARD IS THE WHOLE POINT, measured first for that reason: the
    send loop calls this after EVERY queued action's socket write fails, not
    only a warp's.
    """

    def test_a_send_failure_after_a_no_coords_warp_rolls_the_row_back(self):
        """The exact window `CORE-REQUEST-GM-055` names: the row already
        moved (frame composed, DB written) and the socket write that should
        have followed it never happened."""
        session = self._session("sendfail01")
        before = self._row(session)
        self.assertEqual(before.scene_id, 1)

        stream = io.StringIO()
        with redirect_stderr(stream):
            verdict = chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        # The frame composed; nothing about the SEND has happened yet, so the
        # in-memory row is still the departure scene `persist_warp_scene`
        # restored it to -- exactly what chief's call site would see.
        self.assertEqual(session.foundation.selected.position.scene_id, 1)

        with redirect_stderr(stream):
            outcome = warp_scene_persist.rollback_warp_scene_on_send_failure(
                session,
                chat_command_action.
                WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROLLED_BACK)
        after = self._row(session)
        self.assertEqual(after.scene_id, before.scene_id)
        self.assertEqual(
            (after.x, after.y, after.z), (before.x, before.y, before.z),
        )
        self.assertIn(
            f"{warp_scene_persist.ROLLBACK_CONSOLE_TOKEN} scene={before.scene_id}",
            stream.getvalue(),
        )
        # The audit-append undo is a SEPARATE window (finding 1, above) --
        # this send-failure rollback must not consume or disable it.
        self.assertIsNotNone(verdict.undo)

    def test_the_label_is_pinned_against_chat_command_actions_own_constant(
        self,
    ):
        """`SEND_FAILURE_WARP_ACTION_LABEL` is a literal copy, not an import
        (the function's own docstring gives the circular-import reason).
        This is the guard against the two drifting apart silently."""
        self.assertEqual(
            warp_scene_persist.SEND_FAILURE_WARP_ACTION_LABEL,
            chat_command_action.
            WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )

    def test_every_other_action_label_is_free(self):
        """The send loop calls this after ANY action's socket write fails.
        A `say`, a `/speed` frame, a with-coordinates warp (`ForcePos`) and
        the two-argument cross-scene `TeleportVital` must all cost nothing
        -- not a read, not a write, not a console line."""
        session = self._session("sendfail02")
        before = self._row(session)
        other_labels = (
            chat_command_action.WARP_ACTION_LABEL,
            chat_command_action.WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL,
            chat_command_action.SAY_ACTION_LABEL,
            chat_command_action.SPEED_ACTION_LABEL,
            "",
            None,
        )
        for label in other_labels:
            with self.subTest(label=label):
                stream = io.StringIO()
                with redirect_stderr(stream):
                    outcome = (
                        warp_scene_persist
                        .rollback_warp_scene_on_send_failure(session, label)
                    )
                self.assertEqual(
                    outcome, warp_scene_persist.OUTCOME_NOT_A_WARP,
                )
                self.assertEqual(stream.getvalue(), "")
        self.assertEqual(self._row(session).scene_id, before.scene_id)

    def test_a_raising_write_door_reports_the_same_refusal_word(self):
        """No warp happened first, on purpose: this measures that the
        wrapper's failure path IS `rollback_warp_scene`'s own, not a second
        vocabulary invented for the wrapper."""
        session = self._session("sendfail03")
        stream = io.StringIO()
        with redirect_stderr(stream):
            session.foundation.checkpoint = mock.Mock(
                side_effect=PermissionError("stale session"),
            )
            outcome = warp_scene_persist.rollback_warp_scene_on_send_failure(
                session,
                chat_command_action.
                WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
            )
        self.assertEqual(
            outcome,
            warp_scene_persist.OUTCOME_ROLLBACK_REFUSED_PREFIX
            + "PermissionError",
        )
        self.assertIn(
            f"{warp_scene_persist.ROLLBACK_FAIL_CONSOLE_TOKEN} "
            f"scene=1 reason={outcome}",
            stream.getvalue(),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
