"""CORE-REQUEST-GM-029 -- the 0xAC52 chat route, on the REAL dispatcher.

ROUTE CHANGE, round `apk7ue` (chief, LANE-E).  This file was written for
CORE-REQUEST-GM-028, whose route was ``lane_hooks.fire()`` at the 0xAC52
branch.  CORE-REQUEST-GM-029 (LANE-GM, letter 20260828_1930) replaced that
call with ``chat_command_action.make_gm_chat_command_action(...)``, whose
return value is appended to the actions ``dispatch()`` returns -- the hook
route could never put a byte on the wire, which is why the lane asked for the
replacement.  ``tests/test_gm_chat_command_action.py::OneOfTwoWiringTests``
enforces that exactly one of the two exists in ``runtime.py``.

Three things in here moved with the route and are named where they are used:
the event namespace (``gm_chat_command_*`` -> ``gm_chat_action_*``), the
console token (``LANE_HOOK_FIRED`` -> ``LANE_GM_CHAT_ACTION``), and the
control helper, which used to work by emptying the hook registry and would
now be inert.  The audit log did NOT move: both routes call the same
``handle_local_talk_chat``.

The original header follows, still true of the branch's placement.

CORE-REQUEST-GM-028 -- the 0xAC52 chat point, on the REAL dispatcher.

``tests/test_gm_chat_command.py`` proves ``handle_local_talk_chat`` and the
lane hook offline: the captured payload shapes, the allowlist-first order,
the hook's argument order.  What no test could prove until this file is
that the hook ever runs on the path a player is on, because the point
``vital_inbound_chat_local_talk`` had nothing firing it -- ``runtime.py``
carried exactly one ``lane_hooks.fire()`` call, at the 0x51E9 branch.

This file drives ``make_state_class`` headless with NO scenario objects and
no flags at all -- the only shape a real client ever meets -- pushes one
0xAC52 frame through ``dispatch()``, and checks the three things the wiring
itself can get wrong:

1. the route runs for a GM and the command reaches the audit log,
2. it runs for a non-GM too and refuses on identity, writing nothing,
3. the frame's own behaviour is unchanged apart from the composed action --
   under GM-028 that meant the actions ``dispatch()`` returns were
   byte-for-byte what the same frame produced before; under GM-029 it means
   those same actions plus, at most, ONE appended action, pinned by
   test_the_composed_action_is_appended_exactly_once_and_last.

(Items 1 and 2 said "the hook fires" until round `apk7ue`; the hook is
registered and never fired now, so the word would have been false.)

Modelled on ``tests/test_gm_run_command_dispatch_wiring.py``, which does
the same job for 0x51E9; the synthetic outer envelope is that file's,
retargeted at the chat vital id.
"""
from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm.dispatch import (  # noqa: E402
    reset_rate_limit_state_for_tests,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation import runtime as runtime_module  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
HOOK_POINT = "vital_inbound_chat_local_talk"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _chat_payload(message: str, speaker: str = "") -> bytes:
    """One 0xAC52 payload in the measured shape (tag 0x48, u32 LE, UTF-16LE).

    Same builder as ``tests/test_gm_chat_command.py``'s, and kept in the
    tests for the same reason: the server never composes a client->server
    chat frame, so a composer next to the decoder would be production code
    with no production caller.
    """
    out = bytearray()
    for field in (speaker, message):
        encoded = field.encode("utf-16-le")
        out.append(chat_command.WSTRING_TAG)
        out += struct.pack("<I", len(encoded))
        out += encoded
    return bytes(out)


def _synthetic_chat_pc(legacy, payload: bytes) -> bytes:
    """Outer envelope carrying one 0xAC52 nested vital, payload verbatim."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, CHAT_INPUT_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class ChatCommandDispatchWiringTests(unittest.TestCase):
    def setUp(self):
        # Rate-limit history is process-global (gm/dispatch.py's own
        # thread-safety/test-isolation tradeoff), and this file's whole
        # subject goes through it: 20 calls / 5 s keyed by account name,
        # and "gm_runner" is used by other files in this suite.  Without
        # this line the file is green on a slow runner and red on a fast
        # one -- pf-adversary reproduced exactly that.  Same first line as
        # tests/test_gm_run_command_dispatch_wiring.py's setUp.
        reset_rate_limit_state_for_tests()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = SQLiteStore(
            Path(self.tmp.name) / "state.sqlite3", ROOT / "migrations",
        )
        self.store.migrate()
        self.legacy = _legacy()
        self.projector = LegacyProjector(self.legacy)
        self.lifecycle = CharacterLifecycle(
            self.store,
            Position(
                1, 0, self.legacy.V135_PLAYER_X,
                self.legacy.V135_PLAYER_Y, self.legacy.V135_PLAYER_Z,
            ),
            self.legacy.extract_avatar_attr_wire_from_actor,
        )
        field_mobs.load_roster()
        # The wiring passes no log_path, so gm/commands.py's
        # DEFAULT_LOG_PATH ("capture/gm_command_log.ndjson") resolves
        # against the process CWD -- run in a scratch directory rather than
        # writing into the checkout.  Same reason and same shape as
        # tests/test_gm_run_command_dispatch_wiring.py's setUp.
        import os
        self._owd = Path.cwd()
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self._owd)

    # ----- harness -------------------------------------------------------

    def _config(self, gm_accounts_value):
        path = Path(self.tmp.name) / "gm_accounts.json"
        path.write_text(json.dumps({"gm_accounts": gm_accounts_value}))
        return path

    def _login_and_start(self, token):
        # No scenario arguments of any kind: this is the flagless boot.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def _say(self, state, message):
        pc = _synthetic_chat_pc(self.legacy, _chat_payload(message))
        return state.dispatch(self.legacy.parse_outer(pc))

    def _labels(self, actions):
        return [action[0] for action in actions]

    def _actions_without_the_route(self, token, message):
        """Same frame on a tree where the route composes nothing.

        GM-029 note: the old version of this helper emptied
        `lane_hooks._HOOKS`, which is inert against the action route --
        removing hooks no longer changes what the branch does.  The
        equivalent control is a module that returns None for every line,
        which is exactly what the route does today for `/warp` anyway while
        RE-129 keeps the version gate shut.

        This is NOT a control for "does the branch change the frame" -- both
        sides still run the same runtime.py, so a `return []` added at the
        call site would move both sides together.  pf-adversary measured
        exactly that: mutations M1 (`return []`) and M2 (`rx_frames += 1`)
        survived an earlier version of this file.  The pins in
        test_the_point_does_not_change_what_the_frame_itself_does are the
        real control; this helper only proves the ROUTE's own work adds no
        action, which is a different (smaller) claim.
        """
        with mock.patch.object(
            runtime_module.chat_command_action,
            "make_gm_chat_command_action",
            return_value=None,
        ):
            state = self._login_and_start(token)
            return self._say(state, message)

    def _audit_lines(self):
        log = Path("capture/gm_command_log.ndjson")
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines() if line.strip()
        ]

    # ----- the point exists at all --------------------------------------

    def test_the_chat_point_has_a_hook_registered_on_it(self):
        # If this fails, the lane's half is gone and every test below would
        # be passing against a point nothing listens to.
        self.assertGreaterEqual(
            lane_hooks.registered_points().get(HOOK_POINT, 0), 1
        )

    # ----- a GM account --------------------------------------------------

    def test_a_gm_command_typed_in_chat_reaches_the_audit_log(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            actions = self._say(state, "/warp 2")
            # Observe-only: the point adds no reply of its own.
            self.assertEqual(
                actions, self._actions_without_the_route("gm_runner", "/warp 2")
            )
        self.assertIn("gm_chat_action_accepted_warp", state.events)
        records = self._audit_lines()
        # Two rows since CORE-REQUEST-GM-032 (issued + outcome), one pair per
        # command.  The count is asserted, not just the first row, because a
        # THIRD row here would mean the double-wire this file exists to catch.
        self.assertEqual(len(records), 2, f"audit log: {records}")
        self.assertEqual(records[0].get("account"), "gm_runner")
        self.assertEqual(records[1].get("record"), "outcome")
        self.assertEqual(
            records[0].get("record_id"), records[1].get("record_id")
        )

    def test_a_gms_ordinary_chat_line_is_refused_and_never_logged(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            actions = self._say(state, "hello everyone")
            self.assertEqual(
                actions,
                self._actions_without_the_route("gm_runner", "hello everyone"),
            )
        self.assertIn(
            f"gm_chat_action_refused_{chat_command.REFUSAL_NOT_A_COMMAND}",
            state.events,
        )
        self.assertEqual(self._audit_lines(), [])

    # ----- a non-GM account ----------------------------------------------

    def test_a_non_gm_typing_the_same_command_is_refused_on_identity(self):
        path = self._config(["someone_else"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("not_a_gm")
            actions = self._say(state, "/warp 2")
            self.assertEqual(
                actions, self._actions_without_the_route("not_a_gm", "/warp 2")
            )
        self.assertTrue(
            any(
                event.startswith("gm_chat_action_refused_")
                for event in state.events
            ),
            state.events,
        )
        self.assertNotIn("gm_chat_action_accepted_warp", state.events)
        self.assertEqual(self._audit_lines(), [])

    # ----- the frame's own behaviour is untouched ------------------------

    def test_the_point_does_not_change_what_the_frame_itself_does(self):
        """Pin what a chat frame did BEFORE this branch existed.

        Measured on the tree without the branch (pf-adversary, round
        lo7e03), first runtime request of a flagless session: three
        actions -- the RuntimeRes ack, the welcome message and the music
        control -- and rx_frames + 1, from the frozen v141 default path.
        The branch adds no `return` and no counter bump, so those numbers
        must be exactly what a session sees today.

        Pinned as literals ON PURPOSE.  A control built by emptying
        lane_hooks._HOOKS runs the same runtime.py on both sides and so
        cannot see a `return []` or an rx_frames bump added at the call
        site; these three labels can, and that is the mutation this test
        exists to catch.  tests/test_chat_input_echo.py::
        test_without_scenario_nothing_changes pins the same counter for the
        same frame, and would go red beside this one.
        """
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            rx_before = state.rx_frames
            actions = self._say(state, "/warp 2")
        self.assertEqual(
            self._labels(actions),
            [
                "RUNTIME_RES_ACK_FIRST_REQ",
                "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
                "V100_MUSIC_CONTROL_CURRENT_SCENE",
            ],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)

    def test_the_composed_action_is_appended_exactly_once_and_last(self):
        """The line CORE-REQUEST-GM-029 exists to add, pinned.

        pf-adversary (round `apk7ue`) measured that nothing in this
        repository could see the append at all: through the real dispatcher
        the route returns None for every input the suite drives -- the RE-129
        version gate is shut, and even with it forced open this file's own
        `/warp 2` is a cross-scene command the executor refuses.  Three
        mutations of the append line (append twice, never append, prepend
        instead of append) left the whole 3963-test suite green.  So did
        deleting the guard's body.  Every other property of the branch was
        pinned; the one line the request asked for was not.

        `_actions_without_the_route` cannot close that hole: it patches the
        route to return None, which is what the route already does, so both
        sides of its comparison are identical by construction.  This test
        patches the route to return a SENTINEL action instead, which is the
        only way to make the append observable while the version gate is
        shut -- and it stays meaningful after RE-129 lands.
        """
        sentinel = ("SENTINEL_GM_ACTION", b"", b"", 0.0)
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=sentinel,
            ):
                state = self._login_and_start("gm_runner")
                rx_before = state.rx_frames
                actions = self._say(state, "hello everyone")
        labels = self._labels(actions)
        self.assertEqual(
            labels.count("SENTINEL_GM_ACTION"), 1,
            "the composed action must be appended exactly once: %s" % labels,
        )
        self.assertEqual(
            labels[-1], "SENTINEL_GM_ACTION",
            "the composed action must land after everything the inherited "
            "dispatch produced, not before it: %s" % labels,
        )
        # The append must not disturb the rest of the frame either.
        self.assertEqual(
            labels[:-1],
            [
                "RUNTIME_RES_ACK_FIRST_REQ",
                "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
                "V100_MUSIC_CONTROL_CURRENT_SCENE",
            ],
        )
        self.assertEqual(state.rx_frames, rx_before + 1)

    def test_no_action_is_appended_when_the_route_composes_nothing(self):
        """The guard, pinned: a None return must add nothing.

        Without this, `actions = actions + [gm_action]` written without its
        `is not None` guard would put a bare None into the action list of
        every ordinary frame -- and the serve loop unpacks four fields from
        each action.
        """
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=None,
            ):
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "hello everyone")
        self.assertNotIn(None, actions)
        self.assertEqual(
            self._labels(actions),
            [
                "RUNTIME_RES_ACK_FIRST_REQ",
                "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
                "V100_MUSIC_CONTROL_CURRENT_SCENE",
            ],
        )

    def test_a_chat_frame_before_character_select_is_not_audited(self):
        """The readiness guard, which the first version of this wiring lacked.

        pf-adversary drove one 0xAC52 frame as the FIRST frame of a
        connection -- no login verify, no create, no start-game -- and got
        an accepted GM command with an audit record.  Harmless while
        nothing executes; not harmless once an executor is attached.
        """
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state_type = make_state_class(
                self.legacy, self.lifecycle, self.projector,
            )
            state = state_type("gm_runner")
            self._say(state, "/warp 17")
        self.assertNotIn("gm_chat_action_accepted_warp", state.events)
        self.assertEqual(self._audit_lines(), [])

    def test_the_fired_token_goes_to_stderr_so_tool_stdout_stays_clean(self):
        """0xAC52 is a vital every client sends; stdout is a tool contract.

        Measured leak (pf-adversary): with this token on stdout,
        tools/pf_runtimeres_death_headless_replay.py --json gained a
        LANE_HOOK_FIRED line inside its JSON artifact, because its
        scenario-off control dispatches a chat frame.
        """
        import io
        from contextlib import redirect_stderr, redirect_stdout

        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                self._say(state, "/warp 2")
        token_text = chat_command_action.CONSOLE_TOKEN
        self.assertIn(token_text, err.getvalue())
        self.assertNotIn(token_text, out.getvalue())

    def test_a_route_that_raises_does_not_break_the_connection(self):
        """fail-closed at the call site, not only in the module's unit tests.

        GM-029 note: this test used to inject a raising HOOK into
        `lane_hooks._HOOKS`.  With the hook route gone that injection is
        inert -- the test would have passed while proving nothing.  The
        equivalent for the action route is the module's own internals
        raising, which its top-level `except Exception` is written to
        swallow into an event; what is checked here is the half that
        exception handler cannot check for itself: that the CONNECTION
        survives it and keeps serving later frames.
        """
        path = self._config(["gm_runner"])

        def _boom(*_args, **_kwargs):
            raise RuntimeError("route is broken")

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                chat_command_action, "_make_action", _boom,
            ):
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
                # The connection survives and keeps serving later frames.
                later = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc("gm_runner")
                ))
            self.assertEqual(
                actions, self._actions_without_the_route("gm_runner", "/warp 2")
            )
        self.assertTrue(
            any(
                event.startswith("gm_chat_action_unexpected_")
                for event in state.events
            ),
            state.events,
        )
        self.assertIsInstance(later, list)


if __name__ == "__main__":
    unittest.main()
