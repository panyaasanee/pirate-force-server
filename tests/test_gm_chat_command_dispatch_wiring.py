"""CORE-REQUEST-GM-028 -- the 0xAC52 chat point, on the REAL dispatcher.

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

1. the hook fires for a GM and the command reaches the audit log,
2. it fires for a non-GM too and refuses on identity, writing nothing,
3. the frame's own behaviour is unchanged by the point existing -- the
   actions ``dispatch()`` returns are byte-for-byte what the same frame
   produced before, which is what "observe and fall through" has to mean.

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
from pirateforce_foundation.gm.dispatch import (  # noqa: E402
    reset_rate_limit_state_for_tests,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
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

    def _actions_without_the_hook(self, token, message):
        """Same frame on a tree where the point is registered but inert.

        Emptying the registry is NOT a control for "does the branch change
        the frame" -- both sides still run the same runtime.py, so a
        `return []` added at the call site would move both sides together.
        pf-adversary measured exactly that: mutations M1 (`return []`) and
        M2 (`rx_frames += 1`) survived an earlier version of this file.
        The pins in test_the_point_does_not_change_what_the_frame_itself_
        does are the real control; this helper only proves the HOOK's own
        work adds no action, which is a different (smaller) claim.
        """
        saved = lane_hooks._HOOKS.get(HOOK_POINT, [])
        lane_hooks._HOOKS[HOOK_POINT] = []
        try:
            state = self._login_and_start(token)
            return self._say(state, message)
        finally:
            lane_hooks._HOOKS[HOOK_POINT] = saved

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
                actions, self._actions_without_the_hook("gm_runner", "/warp 2")
            )
        self.assertIn("gm_chat_command_accepted_warp", state.events)
        records = self._audit_lines()
        self.assertEqual(len(records), 1, f"audit log: {records}")
        self.assertEqual(records[0].get("account"), "gm_runner")

    def test_a_gms_ordinary_chat_line_is_refused_and_never_logged(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            actions = self._say(state, "hello everyone")
            self.assertEqual(
                actions,
                self._actions_without_the_hook("gm_runner", "hello everyone"),
            )
        self.assertIn(
            f"gm_chat_command_refused_{chat_command.REFUSAL_NOT_A_COMMAND}",
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
                actions, self._actions_without_the_hook("not_a_gm", "/warp 2")
            )
        self.assertTrue(
            any(
                event.startswith("gm_chat_command_refused_")
                for event in state.events
            ),
            state.events,
        )
        self.assertNotIn("gm_chat_command_accepted_warp", state.events)
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
        self.assertNotIn("gm_chat_command_accepted_warp", state.events)
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
        self.assertIn("LANE_HOOK_FIRED", err.getvalue())
        self.assertNotIn("LANE_HOOK_FIRED", out.getvalue())

    def test_a_hook_that_raises_does_not_break_the_connection(self):
        """fail-closed at the call site, not only in lane_hooks' unit tests."""
        path = self._config(["gm_runner"])
        saved = lane_hooks._HOOKS.get(HOOK_POINT, [])

        def _boom(**_kwargs):
            raise RuntimeError("hook is broken")

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            lane_hooks._HOOKS[HOOK_POINT] = [("test_broken_hook", _boom)]
            try:
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
                # The connection survives and keeps serving later frames.
                later = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc("gm_runner")
                ))
            finally:
                lane_hooks._HOOKS[HOOK_POINT] = saved
            self.assertEqual(
                actions, self._actions_without_the_hook("gm_runner", "/warp 2")
            )
        self.assertIsInstance(later, list)


if __name__ == "__main__":
    unittest.main()
