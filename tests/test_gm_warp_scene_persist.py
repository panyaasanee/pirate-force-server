"""`PANYA-DECISION 20260904_1430` / `COO-DECISION 20260904_1452`.

A live `/warp <n>` must leave the destination scene in `character_positions`
AT SEND TIME, even if the player never takes a step.  R309 measured the gap:
warp, close the client with X, and the next login came back to the scene the
character had left.

`COO 1452` item 3 names the evidence this file has to carry: a test that
reads the DB after the frame is composed with NO walk frame after it, and a
MUTANT that skips the write, which must go RED.

THIS FILE DRIVES THE REAL THING, and that is a correction rather than a
choice.  ~~Its first draft asserted both of those against a hand-written
`_Foundation` double whose `checkpoint` was written by the same author to do
the thing being asserted~~ -- STRUCK: pf-adversary (round `q3cde9`, D6)
measured that there was no database and no frame anywhere in it, and that
its headline mutant test constructed a fixture and asserted the fixture held
its constructor value, so it could not go red for ANY change to ANY
production file.  So the DB half below now uses the real `SQLiteStore`, the
real `CharacterLifecycle`, the real `FoundationSession` and the real router
`chat_command_action._warp_action`, in the shape
`tests/test_gm_warp_position_confirmed.py` already uses.  The pure helper
`warp_destination_position` is still unit-tested on its own, which is what
it exists for.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from dataclasses import replace
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import world_scene_travel  # noqa: E402
from pirateforce_foundation.gm import (  # noqa: E402
    accounts as gm_accounts,
    chat_command_action,
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
from pirateforce_foundation.world_scene_travel import SCENE_SEQUENCE  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: Scene 2, Prison Exile -- marker-backed, `login_entry_allowed` true, and the
#: destination the owner actually typed in R309.
DESTINATION_SCENE = 2


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


class _Session:
    """The two attributes this module reads off a runtime session."""

    def __init__(self, foundation):
        self.foundation = foundation
        self.events = []


class RealDatabaseTests(unittest.TestCase):
    """Real store, real lifecycle, real session, real router."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        # Same pin `test_gm_warp_position_confirmed.py` documents: an
        # unpinned login-scene override resolves to the repo-relative config
        # and can turn a login into a VISIT, which never writes a row.
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
        """A real logged-in, character-selected connection.

        The create wire is the one the repo ships and every other test uses
        (`_V25_REAL_CREATE_PC`), parsed by the real legacy parser rather than
        hand-built, so this session's character is the same shape production
        makes.
        """
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
        """The row as the DATABASE holds it -- not the in-memory copy."""
        return self.store.get_character(session.foundation.selected.id).position

    # ---- the headline -------------------------------------------------

    def test_the_row_holds_the_destination_after_a_warp_and_no_walk_frame(self):
        session = self._session("persist01")
        self.assertEqual(self._row(session).scene_id, 1)
        outcome = warp_scene_persist.persist_warp_scene(
            session, _target(DESTINATION_SCENE),
        )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        row = self._row(session)
        self.assertEqual(row.scene_id, DESTINATION_SCENE)
        self.assertEqual(row.scene_seq, SCENE_SEQUENCE)
        spawn = world_scene_travel.spawn_position(
            world_scene_travel.destination(DESTINATION_SCENE),
        )
        self.assertEqual((row.x, row.y, row.z), _wire_floats(spawn))

    def test_the_production_branch_persists_a_bare_warp(self):
        """Through `_warp_teleport_action_no_coords`, and through the real
        frame builder it calls -- the branch `_warp_action` routes a bare
        `/warp <n>` to, and the send point `COO 1452` named.

        `_warp_action` itself is not driven here on purpose: it would need a
        GM-account config and a token, which is `test_gm_chat_command_action.py`'s
        subject, not this file's.  What this file has to pin is that the
        branch which composes the frame also moves the row, and that is this
        function.
        """
        session = self._session("persist02")
        verdict = chat_command_action._warp_teleport_action_no_coords(
            session, DESTINATION_SCENE, self.legacy,
        )
        self.assertIsNotNone(verdict.action)
        self.assertEqual(
            verdict.action[0],
            chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
        )
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertIn(
            chat_command_action.EVENT_WARP_SCENE_PERSIST_PREFIX
            + warp_scene_persist.OUTCOME_PERSISTED,
            session.events,
        )

    def test_the_console_token_names_the_scene(self):
        session = self._session("persist03")
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertIn(
            f"GM_WARP_SCENE_PERSISTED scene={DESTINATION_SCENE}",
            stream.getvalue(),
        )

    # ---- D1/D3/D4: the in-memory row must NOT move --------------------

    def test_the_in_memory_row_is_put_back_exactly_as_it_was(self):
        """`runtime.py` keys the whole cross-scene machinery on this row.

        `_gm_warp_resync_selected_scene` early-returns when
        `target.scene_id == selected.position.scene_id`, so a pre-empted
        in-memory row makes a live cross-scene warp look same-scene: the
        destination's census is never composed, `last_target_pos` is never
        cleared, and `scene_label_is_server_guess` is never set.
        pf-adversary measured all three on the first draft of this module.
        """
        session = self._session("persist04")
        before = session.foundation.selected
        warp_scene_persist.persist_warp_scene(session, _target(DESTINATION_SCENE))
        self.assertIs(session.foundation.selected, before)
        self.assertEqual(session.foundation.selected.position, self.home)

    def test_the_durable_row_and_the_in_memory_row_deliberately_disagree(self):
        """The point of the restore, stated as an assertion rather than prose."""
        session = self._session("persist05")
        warp_scene_persist.persist_warp_scene(session, _target(DESTINATION_SCENE))
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)
        self.assertEqual(session.foundation.selected.position.scene_id, 1)

    def test_the_router_leaves_the_in_memory_row_alone_too(self):
        session = self._session("persist06")
        before = session.foundation.selected.position
        chat_command_action._warp_teleport_action_no_coords(
            session, DESTINATION_SCENE, self.legacy,
        )
        self.assertEqual(session.foundation.selected.position, before)

    def test_a_session_that_cannot_be_restored_is_reported_not_hidden(self):
        session = self._session("persist07")
        real = session.foundation

        class _Unrestorable:
            def __init__(self, inner):
                self._inner = inner
                self.lifecycle = inner.lifecycle
                self.selected = inner.selected
                self._locked = False

            def checkpoint(self, position):
                self._inner.checkpoint(position)
                self.selected = self._inner.selected
                self._locked = True

            def __setattr__(self, name, value):
                if name == "selected" and getattr(self, "_locked", False):
                    return  # swallowed, exactly the shape the read-back catches
                object.__setattr__(self, name, value)

        self.assertEqual(
            warp_scene_persist.persist_warp_scene(
                _Session(_Unrestorable(real)), _target(DESTINATION_SCENE),
            ),
            warp_scene_persist.OUTCOME_SELECTED_NOT_RESTORED,
        )

    # ---- D2: a destination the next login would refuse ----------------

    def test_a_scene_the_next_login_would_refuse_is_never_written(self):
        """Scene 126: `persist_position_allowed=True`, `login_entry_allowed=False`.

        pf-adversary measured the first draft writing it and the next login
        refusing with `scene_not_allowed_at_login` -- and only a login can
        rewrite the row, so the character was durably unreachable.  Before
        this round the row was untouched and the character survived; taking
        that away is what CHARTER-02 rule 2 forbids.
        """
        self.assertFalse(
            world_scene_travel.destination(126).login_entry_allowed,
            "this test's premise: scene 126 is pinned login_entry_allowed=False",
        )
        session = self._session("persist08")
        outcome = warp_scene_persist.persist_warp_scene(session, _target(126, x=3050.0))
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)
        self.assertEqual(self._row(session).scene_id, 1)

    def test_the_refused_destination_prints_no_token(self):
        session = self._session("persist09")
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(session, _target(126, x=3050.0))
        self.assertNotIn("GM_WARP_SCENE_PERSISTED", stream.getvalue())

    # ---- COO 1646 item 2: a failed write must be readable off the console,
    # not just off `session.events` ---------------------------------------

    def test_the_refused_destination_prints_the_failed_token_with_its_reason(self):
        """`COO-DECISION 20260904_1646` item 2, answering `1620`.

        A tester who only reads the console must be able to tell "wrote" from
        "wrote-failed-silently" apart -- `GT-172` F-3 cannot be closed off a
        trail entry nobody watching the screen ever sees.
        """
        session = self._session("persist16")
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(126, x=3050.0),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)
        self.assertIn(
            f"GM_WARP_SCENE_PERSIST_FAILED scene=126 reason={outcome}",
            stream.getvalue(),
        )

    def test_a_same_scene_no_op_write_prints_the_failed_token_too(self):
        session = self._session("persist17")
        stored = self._row(session)
        session.foundation.checkpoint = lambda _position: None
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(
                session, WarpTarget(stored.scene_id, 26414.0, 20998.0, 186.0),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)
        self.assertNotIn("GM_WARP_SCENE_PERSISTED ", stream.getvalue())
        self.assertIn(
            f"GM_WARP_SCENE_PERSIST_FAILED scene={stored.scene_id} reason={outcome}",
            stream.getvalue(),
        )

    def test_a_raising_write_door_prints_the_failed_token_type_name_only(self):
        session = self._session("persist18")

        def raising(_position):
            raise PermissionError("stale or non-owning character session 5678")

        session.foundation.checkpoint = raising
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertIn(
            f"GM_WARP_SCENE_PERSIST_FAILED scene={DESTINATION_SCENE} "
            f"reason={outcome}",
            stream.getvalue(),
        )
        self.assertNotIn("5678", stream.getvalue())

    def test_a_broken_stderr_on_a_failed_write_costs_the_line_not_the_call(self):
        class _Closed:
            def write(self, _text):
                raise ValueError("I/O operation on closed file")

            def flush(self):
                raise ValueError("I/O operation on closed file")

        session = self._session("persist19")
        with redirect_stderr(_Closed()):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(126, x=3050.0),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE)

    # ---- D5: the read-back compares the whole row ---------------------

    def test_a_same_scene_warp_that_writes_nothing_is_not_reported_persisted(self):
        """The mutant `COO 1452` item 3 requires, in the shape that hid it.

        A same-scene warp's destination scene id ALREADY equals the stored
        one, so a read-back that compares only `scene_id` is satisfied before
        any write happens -- pf-adversary measured the first draft printing
        the token over a row where nothing had moved.
        """
        session = self._session("persist10")
        stored = self._row(session)
        session.foundation.checkpoint = lambda _position: None  # writes nothing
        outcome = warp_scene_persist.persist_warp_scene(
            session, WarpTarget(stored.scene_id, 26414.0, 20998.0, 186.0),
        )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED)
        self.assertEqual(self._row(session), stored)

    def test_a_write_door_that_writes_nothing_cross_scene_is_red_too(self):
        session = self._session("persist11")
        stored = self._row(session)
        session.foundation.checkpoint = lambda _position: None
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            ),
            warp_scene_persist.OUTCOME_ROW_NOT_TOUCHED,
        )
        self.assertEqual(self._row(session), stored)

    def test_the_mutant_that_never_calls_the_persister_leaves_the_old_scene(self):
        """The real mutant: the production code path on `main` before #745.

        ~~The first draft asserted a fixture held its constructor value and
        called no production code at all~~ -- struck; this one patches the
        persister out of the module under test and drives the real router, so
        deleting the call in `chat_command_action` makes it red.
        """
        session = self._session("persist12")
        with mock.patch.object(
            chat_command_action, "persist_warp_scene", return_value="skipped",
        ):
            chat_command_action._warp_teleport_action_no_coords(
                session, DESTINATION_SCENE, self.legacy,
            )
        self.assertEqual(self._row(session).scene_id, 1)

    # ---- failures cost the write, never the thread ---------------------

    def test_a_raising_write_door_is_named_by_type_only(self):
        session = self._session("persist13")

        def raising(_position):
            raise PermissionError("stale or non-owning character session 1234")

        session.foundation.checkpoint = raising
        outcome = warp_scene_persist.persist_warp_scene(
            session, _target(DESTINATION_SCENE),
        )
        self.assertEqual(
            outcome,
            warp_scene_persist.OUTCOME_WRITE_REFUSED_PREFIX + "PermissionError",
        )
        self.assertNotIn("1234", outcome)
        self.assertEqual(self._row(session).scene_id, 1)

    def test_a_raising_read_back_is_not_reported_as_a_failed_write(self):
        session = self._session("persist14")

        def raising(_character_id):
            raise RuntimeError("database is locked")

        session.foundation.lifecycle = _Shadow(
            session.foundation.lifecycle, get_character=raising,
        )
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            ),
            warp_scene_persist.OUTCOME_READBACK_UNAVAILABLE,
        )

    def test_a_broken_stderr_does_not_undo_a_durable_write(self):
        class _Closed:
            def write(self, _text):
                raise ValueError("I/O operation on closed file")

            def flush(self):
                raise ValueError("I/O operation on closed file")

        session = self._session("persist15")
        with redirect_stderr(_Closed()):
            outcome = warp_scene_persist.persist_warp_scene(
                session, _target(DESTINATION_SCENE),
            )
        self.assertEqual(outcome, warp_scene_persist.OUTCOME_PERSISTED)
        self.assertEqual(self._row(session).scene_id, DESTINATION_SCENE)


class _Shadow:
    """A lifecycle whose store answers one method differently."""

    def __init__(self, inner, **store_overrides):
        self._inner = inner
        self.store = _StoreShadow(inner.store, store_overrides)

    def __getattr__(self, name):
        return getattr(self._inner, name)


class _StoreShadow:
    def __init__(self, inner, overrides):
        self._inner = inner
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._inner, name)


class SessionShapesThatCannotWriteTests(unittest.TestCase):
    """No database needed: these never reach one."""

    def test_a_session_with_no_write_door_is_named_not_raised(self):
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(object()), _target(2)),
            warp_scene_persist.OUTCOME_NO_SESSION_DOOR,
        )

    def test_a_session_with_no_write_door_prints_the_failed_token(self):
        stream = io.StringIO()
        with redirect_stderr(stream):
            outcome = warp_scene_persist.persist_warp_scene(
                _Session(object()), _target(2),
            )
        self.assertIn(
            f"GM_WARP_SCENE_PERSIST_FAILED scene=2 reason={outcome}",
            stream.getvalue(),
        )

    def test_no_selected_character_is_named_not_raised(self):
        class _NoCharacter:
            selected = None

            def checkpoint(self, position):
                raise AssertionError("must not be reached")

        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(_NoCharacter()), _target(2)),
            warp_scene_persist.OUTCOME_NO_CHARACTER,
        )

    def test_a_non_int_character_id_is_refused_rather_than_looked_up(self):
        class _StringId:
            class selected:
                id = "7"
                position = None

            def checkpoint(self, position):
                raise AssertionError("must not be reached")

        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(_StringId()), _target(2)),
            warp_scene_persist.OUTCOME_NO_CHARACTER,
        )

    def test_a_target_this_module_did_not_get_is_refused(self):
        self.assertEqual(
            warp_scene_persist.persist_warp_scene(_Session(object()), None),
            warp_scene_persist.OUTCOME_NOT_A_TARGET,
        )

    def test_a_target_this_module_did_not_get_prints_no_token_at_all(self):
        """There is no scene id to name -- this call was never a real warp."""
        stream = io.StringIO()
        with redirect_stderr(stream):
            warp_scene_persist.persist_warp_scene(_Session(object()), None)
        self.assertEqual(stream.getvalue(), "")


class LoginWouldAcceptTests(unittest.TestCase):
    """Fails closed for everything it cannot answer for."""

    def setUp(self):
        # The snapshot below is process-global; a case that installs its own
        # registry must not leave it behind for the next one.
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        self.addCleanup(
            warp_scene_persist.reset_login_registry_snapshot_for_tests
        )

    def test_a_marker_backed_scene_is_accepted(self):
        self.assertTrue(warp_scene_persist.login_would_accept(DESTINATION_SCENE))

    def test_a_scene_pinned_not_allowed_at_login_is_refused(self):
        self.assertFalse(warp_scene_persist.login_would_accept(126))

    def test_a_scene_the_registry_does_not_pin_is_refused(self):
        self.assertFalse(warp_scene_persist.login_would_accept(64000))

    def test_a_scene_id_outside_the_wire_range_is_refused(self):
        self.assertFalse(warp_scene_persist.login_would_accept(0))
        self.assertFalse(warp_scene_persist.login_would_accept(0x1FFFF))

    def test_a_non_int_scene_id_is_refused_rather_than_raising(self):
        for value in (None, "2", 2.0, True):
            self.assertFalse(warp_scene_persist.login_would_accept(value))


class TheRegistryIsReadOnceTests(unittest.TestCase):
    """`ADVERSARY_PENDING #745-R2` item 5, fixed per `COO 2045` item 4.

    The defect was not that the read was slow.  It was that this module
    predicts what the RUNNING login path will do, and it was asking a FILE
    that can change under the running process -- so its prediction and the
    login it predicts could disagree, in the direction that writes a row a
    login then refuses (the module docstring's "bricks a character").
    """

    def setUp(self):
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        self.addCleanup(
            warp_scene_persist.reset_login_registry_snapshot_for_tests
        )

    def test_the_disk_is_read_once_no_matter_how_many_warps_ask(self):
        real = world_scene_travel.load_scene_registry
        calls = []

        def counted(*args, **kwargs):
            calls.append(1)
            return real(*args, **kwargs)

        with mock.patch.object(
            world_scene_travel, "load_scene_registry", counted
        ):
            for _ in range(5):
                warp_scene_persist.login_would_accept(DESTINATION_SCENE)
        self.assertEqual(1, len(calls))

    def test_a_registry_that_changes_mid_run_does_not_change_the_answer(self):
        self.assertTrue(warp_scene_persist.login_would_accept(DESTINATION_SCENE))
        # The same file now says this scene refuses logins.  A per-call disk
        # read would follow it; the snapshot answers as the server booted.
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            lambda *a, **k: (_ for _ in ()).throw(
                AssertionError("the snapshot re-read the registry")
            ),
        ):
            self.assertTrue(
                warp_scene_persist.login_would_accept(DESTINATION_SCENE)
            )

    def test_a_second_thread_arriving_mid_read_is_not_told_the_scene_refuses(self):
        """pf-adversary round `vlk8rq`, finding 4, MEASURED.

        The first draft set the "taken" flag BEFORE the load and held no
        lock, so a second connection warping while the read was in flight saw
        `TAKEN=True, SNAPSHOT=None`, was answered False, and LOST ITS DURABLE
        ROW under a word that blames scene policy.  `persist_warp_scene` runs
        on a per-connection listener thread, so this is a real pair of
        callers, not a hypothetical one.
        """
        import threading
        import time

        real = world_scene_travel.load_scene_registry

        def slow(*args, **kwargs):
            time.sleep(0.3)
            return real(*args, **kwargs)

        answers = {}

        def ask(name):
            answers[name] = warp_scene_persist.login_would_accept(
                DESTINATION_SCENE
            )

        with mock.patch.object(world_scene_travel, "load_scene_registry", slow):
            first = threading.Thread(target=ask, args=("first",))
            first.start()
            time.sleep(0.1)
            second = threading.Thread(target=ask, args=("second",))
            second.start()
            first.join()
            second.join()
        self.assertEqual({"first": True, "second": True}, answers)

    def test_an_unreadable_registry_refuses_every_scene(self):
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            lambda *a, **k: (_ for _ in ()).throw(OSError("no registry")),
        ):
            self.assertFalse(
                warp_scene_persist.login_would_accept(DESTINATION_SCENE)
            )
        # And it does not go back to the disk on the next warp: the retry is
        # the hot-path read this change exists to remove.
        self.assertFalse(warp_scene_persist.login_would_accept(DESTINATION_SCENE))


class AnUnreadableRegistryGetsItsOwnWordTests(RealDatabaseTests):
    """pf-adversary round `vlk8rq`, finding 5.

    `login_would_accept` fails closed for two different reasons and the
    caller used to report both as `login_would_refuse` -- the same
    one-word-two-questions defect this module closed LAST round as finding 2.
    An operator reading the console has to be able to tell "this scene is
    pinned shut" from "this process cannot read the registry and, by design,
    will not retry".
    """

    def setUp(self):
        super().setUp()
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        self.addCleanup(
            warp_scene_persist.reset_login_registry_snapshot_for_tests
        )

    def test_the_word_names_the_registry_not_the_scene(self):
        session = self._session("registry01")
        # Built BEFORE the registry is taken away: the target is the frame's
        # own, composed while the file was readable, which is the real
        # sequence -- the read this test breaks is the one that happens at
        # persist time, not at compose time.
        target = _target(DESTINATION_SCENE)
        with mock.patch.object(
            world_scene_travel,
            "load_scene_registry",
            lambda *a, **k: (_ for _ in ()).throw(OSError("no registry")),
        ):
            stream = io.StringIO()
            with redirect_stderr(stream):
                outcome = warp_scene_persist.persist_warp_scene(
                    session, target
                )
        self.assertEqual(
            warp_scene_persist.OUTCOME_LOGIN_REGISTRY_UNREADABLE, outcome
        )
        self.assertNotEqual(
            warp_scene_persist.OUTCOME_LOGIN_WOULD_REFUSE, outcome
        )
        self.assertIn(warp_scene_persist.FAIL_CONSOLE_TOKEN, stream.getvalue())
        self.assertIn(
            warp_scene_persist.OUTCOME_LOGIN_REGISTRY_UNREADABLE,
            stream.getvalue(),
        )


class TheRowIsBuiltFromTheFrameTests(unittest.TestCase):
    def test_a_position_with_no_readable_heading_costs_the_angle_not_the_write(self):
        row = warp_scene_persist.warp_destination_position(_target(2), None)
        self.assertEqual(row.heading, 0.0)
        self.assertEqual(row.scene_id, 2)

    def test_a_bool_heading_is_not_read_as_a_number(self):
        # `isinstance(True, int)` is True, so a bool would otherwise become a
        # heading of 1.0 -- a rotation from a type confusion.
        class _BoolHeading:
            heading = True

        row = warp_scene_persist.warp_destination_position(_target(2), _BoolHeading())
        self.assertEqual(row.heading, 0.0)

    def test_a_real_heading_survives(self):
        row = warp_scene_persist.warp_destination_position(
            _target(2), Position(1, 0, 0.0, 0.0, 0.0, 2.5),
        )
        self.assertEqual(row.heading, 2.5)

    def test_scene_seq_is_the_constant_the_frame_carries(self):
        row = warp_scene_persist.warp_destination_position(_target(2), None)
        self.assertEqual(row.scene_seq, SCENE_SEQUENCE)

    def test_a_non_target_cannot_produce_a_row(self):
        with self.assertRaises(ValueError):
            warp_scene_persist.warp_destination_position("scene 2", None)


class TheBranchesThatCallItTests(unittest.TestCase):
    """Which warp shapes persist and which do not -- source-level pins.

    Text assertions, and labelled as such: the behavioural pins for the
    no-coordinate branch are in `RealDatabaseTests` above.  These exist for
    the two branches whose CORRECT behaviour is that nothing happens, which
    no behavioural test can distinguish from a call that silently did
    nothing.
    """

    def test_the_force_pos_branch_is_not_wired_to_the_persister(self):
        # RE-129: the client's ForcePos handler is `mov al,1; ret 4` -- it
        # ignores the frame.  Persisting there would move the row to a point
        # the client is known not to have gone to.
        import inspect

        source = inspect.getsource(chat_command_action._warp_action)
        self.assertNotIn("_persist_warp_scene", source)

    def test_the_with_coordinates_branch_is_not_wired_to_the_persister(self):
        """`COO 1452` item 4 said do not touch `/warp <n> <x> <y>`.

        pf-adversary measured what wiring it cost: `/warp 126 <x> <y>` wrote
        a row the next login refuses, and R306 measured that shape making the
        client close itself, so no TargetPos ever arrives to correct it.

        ~~`assertNotIn("\\n    _persist_warp_scene(session, target)")` alone~~
        -- STRUCK, pf-adversary round `741zlx` finding 8: that is a SUBSTRING
        match on ONE exact spelling, and `_persist_warp_scene(session,
        target=target)`, `outcome = _persist_warp_scene(session, target)` or
        the same call indented one level inside an `if` all slip past it
        while restoring the measured character-bricking behaviour.

        The sibling guard one method up can simply forbid the NAME; this one
        cannot, because this function's body deliberately KEEPS the struck
        call in a comment (`#745` needed a reader to see why the wiring
        stopped being the reasoning, and this house strikes rather than
        deletes).  So the check is on the parsed CALL GRAPH instead of the
        text: every `Call` node in the function, whatever its spelling,
        keyword form or nesting.  A comment cannot be a `Call`; a re-wiring
        cannot avoid being one.
        """
        import ast
        import inspect
        import textwrap

        source = inspect.getsource(chat_command_action._warp_teleport_action)
        tree = ast.parse(textwrap.dedent(source))
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertNotIn("_persist_warp_scene", called)
        self.assertNotIn("persist_warp_scene", called)
        # The struck spelling stays asserted too -- a strictly weaker claim,
        # kept so a reader of this file can see the old guard is subsumed
        # rather than quietly dropped.
        self.assertNotIn("\n    _persist_warp_scene(session, target)", source)

    def test_the_no_coords_branch_calls_the_persister(self):
        import inspect

        self.assertIn(
            "_persist_warp_scene(session, target)",
            inspect.getsource(chat_command_action._warp_teleport_action_no_coords),
        )


def _target(scene_id, *, x=None, y=0.0, z=0.0):
    """A `WarpTarget` carrying the scene's own pinned spawn unless told otherwise."""
    if x is not None:
        return WarpTarget(scene_id, x, y, z)
    spawn = world_scene_travel.spawn_position(world_scene_travel.destination(scene_id))
    return WarpTarget(scene_id, *_wire_floats(spawn))


def _wire_floats(values):
    import struct

    return tuple(
        struct.unpack("<f", struct.pack("<f", value))[0] for value in values
    )


if __name__ == "__main__":
    unittest.main()
