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
from pirateforce_foundation.gm import (  # noqa: E402
    login_scene_override,
)
from pirateforce_foundation.gm import chat_command  # noqa: E402
from pirateforce_foundation.gm import chat_command_action  # noqa: E402
from pirateforce_foundation.gm import commands  # noqa: E402
from pirateforce_foundation.gm import teleport_wire  # noqa: E402
from pirateforce_foundation.gm import warp_executor  # noqa: E402
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
        # Both login-scene override configs pinned inside this test's own
        # temp dir, at paths nothing writes.  Left unpinned they resolve to
        # the repo-relative defaults (`config/gm_login_scene.json`,
        # `config/gm_login_scene_standalone.json`), and `config/` is
        # gitignored -- so "this account has no staged login scene" would be
        # a fact about the machine running the suite rather than about this
        # fixture.  pf-adversary measured it: dropping one standalone map
        # into `config/` turns eight tests across this lane red.  A later
        # `patch.dict` in an individual test still wins for the keys it sets.
        _login_scene_env_pin = mock.patch.dict(gm_accounts.os.environ, {
            login_scene_override.ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_gm_login_scene.json"),
            login_scene_override.STANDALONE_ENV_OVERRIDE:
                str(Path(self.tmp.name) / "no_standalone_map.json"),
        })
        _login_scene_env_pin.start()
        self.addCleanup(_login_scene_env_pin.stop)
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
            # The control is measured FIRST, and the order is load-bearing
            # (chief, round ngwnnj/R223).  A GM's `/warp` to another scene
            # STAGES a single-use login-scene override for this same account
            # (LANE-GM's cross-scene warp), and the control's own login is a
            # second login of "gm_runner": measured after the subject, it
            # spends that entry and arrives in scene 2 for real, which since
            # CHIEF-DECISION 20260829_0520 also moves the in-memory
            # character -- so the very next frame composes scene 2's census
            # and the "control" carries two actions the subject never had.
            # That is not this route's doing; it is a control that is no
            # longer the same login.  With the route mocked out, the control
            # stages nothing, so running it first leaves both sides on a
            # login with no override.
            # GM-A (R278, round jd4jqp) made a bare cross-scene `/warp` to a
            # MARKER-BACKED scene fire live instead of staging -- scene 2
            # (Prison Exile Island) is one of those scenes. This test's own
            # subject is dispatch-wiring/audit parity, not GM-A's new live
            # branch, so the live short-circuit is turned off here to keep
            # exercising the STAGE mechanism this test was built around --
            # the same isolation `warp_executor`'s own
            # `test_flipping_the_authorization_flag_off_falls_back_to_
            # staging` test uses for the with-coordinates sibling.
            with mock.patch.object(
                warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
            ):
                control = self._actions_without_the_route("gm_runner", "/warp 2")
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
            # Observe-only: the point adds no reply of its own.
            self.assertEqual(actions, control)
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
            # Same isolation as `test_a_gm_command_typed_in_chat_reaches_
            # the_audit_log` above, same reason: this test pins the frame's
            # OWN three-action baseline, unrelated to GM-A's new live
            # branch for a bare cross-scene `/warp` -- the flag is turned
            # off so scene 2 keeps staging (no fourth action) here too.
            with mock.patch.object(
                warp_executor, "WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED", False
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

    def test_the_kill_switch_closes_this_route_when_the_lane_is_not_allowed(self):
        """`production_allowed = False` must shut the door GM-029 opened.

        Round wi1m62, COO-DECISION 20260829_0041 option (b).  GM-029 left
        the hook shape for a direct call, and with it the withdrawal that
        made `production_allowed` mean anything: for one round the owner's
        approved switch (PANYA-ORDER 20260827_1230) could be flipped to
        False and this branch would keep authorizing chat lines anyway.

        Driven at `lane_hooks`' recorded answer rather than by rewriting
        the lane's file, which is the same value flipping the flag on disk
        produces -- discovery reads the file once, at import, and a test
        process has already passed that point.  What it pins is the only
        thing runtime.py can get wrong: whether the branch ASKS.
        """
        qualified = "pirateforce_foundation.lane_hooks.lane_gm_chat_command"
        path = self._config(["gm_runner"])
        previous = lane_hooks._PRODUCTION_ALLOWED[qualified]
        self.assertIs(previous, True)  # the state the other tests run in
        lane_hooks._PRODUCTION_ALLOWED[qualified] = False
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.__setitem__, qualified, previous
        )
        import io
        from contextlib import redirect_stderr, redirect_stdout

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                actions = self._say(state, "/warp 2")
        # Nothing composed: no appended action, no audit row -- and the
        # frame itself still behaves exactly as it did.
        self.assertEqual(
            self._labels(actions),
            [
                "RUNTIME_RES_ACK_FIRST_REQ",
                "V99_SHOW_MESSAGE_LOCAL_SERVER_ONLINE",
                "V100_MUSIC_CONTROL_CURRENT_SCENE",
            ],
        )
        self.assertEqual(self._audit_lines(), [])
        # But NOT silent, on either trail. An empty audit log means three
        # different things (switch off / wiring dead / nobody typed) and
        # GT-127 grades on that file; the stand-down has to say which.
        # [pf-adversary, round wi1m62]
        self.assertEqual(
            [event for event in state.events if event.startswith("gm_chat_")],
            ["gm_chat_action_route_closed_not_production_allowed"],
        )
        self.assertIn("LANE_GM_CHAT_ACTION route=closed", err.getvalue())
        self.assertNotIn("LANE_GM_CHAT_ACTION", out.getvalue())

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


class ActionQueuedConfirmHookTests(ChatCommandDispatchWiringTests):
    """CORE-REQUEST-GM-040 -- the append-site confirm hook, on the REAL
    dispatcher.

    `gm/commands.py`'s `OUTCOME_QUEUED` has been reserved and unreachable
    since CORE-REQUEST-GM-032 item 3: it may only be written once the
    append site at `runtime.py`'s `if gm_action is not None:` branch reports
    back that the append actually ran.  This class does not wire that
    reporting -- `gm/` owns the reader half, and no round of it has landed
    yet -- it proves the HOOK chief's half adds: an optional
    `_gm_action_queued_confirm` pairing, `(the exact action object, a
    callback)`, set on the session by whatever composed the action, fired
    exactly once at the one line that ever runs the append for THAT SAME
    action object (identity, not equality), and cleared before the callback
    runs so it cannot be replayed against a later, unrelated frame.

    THE CONTRACT IS PAIR-AND-MATCH, NOT A BARE FLAG, and that is not a
    style choice: pf-adversary's review of this hook's first version
    (round `hd6tac`, D1/D2) measured that a bare "something is pending"
    flag, set by a composer whose action was then withheld (the route
    returned `None`, so the append below never ran for it that frame),
    survived on `self` and fired against the NEXT frame's unrelated append
    instead -- crediting one command's confirmation to a different one.
    Every test below that proves non-replay uses a second composer that
    does NOT touch `_gm_action_queued_confirm` at all, which is the case
    the first version's equivalent test failed to cover (its second
    composer always re-armed the attribute itself, so it only proved
    "replacement works", not "a stale pairing cannot misfire").

    Reuses `ChatCommandDispatchWiringTests`'s whole harness (setUp,
    `_login_and_start`, `_say`) rather than a fresh copy of it, the same way
    that class's own docstring says it borrowed its outer envelope from
    `test_gm_run_command_dispatch_wiring.py`.
    """

    _FAKE_ACTION = ("FAKE_GM_ACTION", b"", b"", 0.0)
    # A second, textually-identical-but-distinct action object.  Tuples of
    # equal content still compare `==`, so every match below is asserted
    # with `is` at the production code, and this constant exists so a test
    # can hand out an action that is `==` to `_FAKE_ACTION` but never `is`
    # it -- proving the match is on identity, not on the tuple's value.
    # Built via `tuple(list(...))` rather than a second literal: CPython's
    # compiler deduplicates identical literal tuples in one module's
    # constant pool, so a second `("FAKE_GM_ACTION", b"", b"", 0.0)` literal
    # here would in fact BE `_FAKE_ACTION` (`is` True) -- measured, not
    # assumed, the same discipline this codebase applies to every other
    # "obviously true" assumption about the interpreter.
    _OTHER_ACTION = tuple(["FAKE_GM_ACTION", b"", b"", 0.0])

    def test_absent_confirm_attribute_costs_nothing(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=self._FAKE_ACTION,
            ):
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
        self.assertIn(self._FAKE_ACTION, actions)
        self.assertFalse(hasattr(state, "_gm_action_queued_confirm"))

    def test_confirm_callback_fires_exactly_once_when_the_append_runs(self):
        path = self._config(["gm_runner"])
        calls = []

        def _compose(*_args, **kwargs):
            action = self._FAKE_ACTION
            kwargs["session"]._gm_action_queued_confirm = (
                action, lambda: calls.append(1),
            )
            return action

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                side_effect=_compose,
            ):
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
        self.assertEqual(calls, [1])
        self.assertIn(self._FAKE_ACTION, actions)
        # Cleared, not merely fired -- a leftover reference here would be
        # matched against the next frame that appends this exact object.
        self.assertIsNone(
            getattr(state, "_gm_action_queued_confirm", "MISSING")
        )

    def test_a_raising_confirm_is_named_and_does_not_break_dispatch(self):
        path = self._config(["gm_runner"])

        def _compose(*_args, **kwargs):
            def _boom():
                raise RuntimeError("confirm blew up")

            action = self._FAKE_ACTION
            kwargs["session"]._gm_action_queued_confirm = (action, _boom)
            return action

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                side_effect=_compose,
            ):
                state = self._login_and_start("gm_runner")
                actions = self._say(state, "/warp 2")
                # The connection survives and keeps serving later frames --
                # the same shape as test_a_route_that_raises_does_not_break_
                # the_connection above, for the hook this class adds.
                later = state.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_client_login_pc("gm_runner")
                ))
        self.assertIn(self._FAKE_ACTION, actions)
        self.assertIn(
            "gm_action_queued_confirm_failed_RuntimeError", state.events,
        )
        self.assertIsInstance(later, list)

    def test_a_stale_pairing_from_a_withheld_action_never_fires_for_a_later_unrelated_append(
        self,
    ):
        """Composed-then-withheld (route returns `None`, so the append below
        never runs this frame) leaves the pairing set.  The NEXT frame's
        composer, in this test, sets NOTHING at all -- proving the leftover
        pairing cannot be matched against (and therefore cannot fire for)
        an action it was never paired with, with no re-arming to hide
        behind.  This is the case pf-adversary's D1 measured the first
        version of this hook's equivalent test never actually covered.
        """
        path = self._config(["gm_runner"])
        calls = []

        def _compose_but_withhold(*_args, **kwargs):
            kwargs["session"]._gm_action_queued_confirm = (
                self._FAKE_ACTION, lambda: calls.append("stale"),
            )
            return None

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                side_effect=_compose_but_withhold,
            ):
                state = self._login_and_start("gm_runner")
                self._say(state, "hello everyone")
            self.assertEqual(calls, [])
            pending = getattr(state, "_gm_action_queued_confirm", "MISSING")
            self.assertNotEqual(pending, "MISSING")

            # The next frame's composer returns a DIFFERENT (but `==`)
            # action object and touches `_gm_action_queued_confirm` not at
            # all -- the append below still runs (this action is real, not
            # withheld), but nothing may fire for it.
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=self._OTHER_ACTION,
            ):
                actions = self._say(state, "/warp 2")
        self.assertIn(self._OTHER_ACTION, actions)
        self.assertEqual(calls, [])
        # The stale pairing is still sitting there, unfired and uncleared --
        # inert forever, since `_FAKE_ACTION` is never appended again, but
        # never wrongly fired either.
        self.assertEqual(
            getattr(state, "_gm_action_queued_confirm", "MISSING"), pending,
        )

    def test_a_reentrant_confirm_that_rearms_only_fires_for_the_action_it_names(
        self,
    ):
        """A callback that sets a NEW pairing while it runs (a retry/re-arm
        pattern) must not have that new pairing fire against THIS SAME
        append (clear-before-call already prevents that) nor against a
        LATER, unrelated append -- only against an append of the exact
        object the new pairing names.  Closes pf-adversary's D2.
        """
        path = self._config(["gm_runner"])
        calls = []

        def _compose_first(*_args, **kwargs):
            session = kwargs["session"]

            def _rearm():
                calls.append("first")
                # Re-arms for OTHER_ACTION, an action this frame never
                # composed and never appends.
                session._gm_action_queued_confirm = (
                    self._OTHER_ACTION, lambda: calls.append("rearmed"),
                )

            session._gm_action_queued_confirm = (self._FAKE_ACTION, _rearm)
            return self._FAKE_ACTION

        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                side_effect=_compose_first,
            ):
                state = self._login_and_start("gm_runner")
                self._say(state, "/warp 2")
            self.assertEqual(calls, ["first"])

            # A second, unrelated frame whose composer sets nothing.  The
            # re-armed pairing names `_OTHER_ACTION`, not whatever this
            # frame appends, so it must not fire here.
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=("SOME_OTHER_LABEL", b"", b"", 0.0),
            ):
                self._say(state, "/warp 2")
        self.assertEqual(calls, ["first"])

        # It DOES fire once `_OTHER_ACTION` itself is the one appended.
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                runtime_module.chat_command_action,
                "make_gm_chat_command_action",
                return_value=self._OTHER_ACTION,
            ):
                self._say(state, "/warp 2")
        self.assertEqual(calls, ["first", "rearmed"])


class QueuedRowLandsEndToEndTests(ChatCommandDispatchWiringTests):
    """CORE-REQUEST-GM-040, BOTH halves, with nothing mocked between them.

    `ActionQueuedConfirmHookTests` above proves chief's half by handing the
    hook a fake action and a fake callback -- which is the right shape for
    proving the hook, and cannot prove the feature: every one of its tests
    replaces `make_gm_chat_command_action` with a stub, so the real GM lane
    never runs and no real audit row is ever written.  Round `dm8o4l` (this
    lane's half) makes the composed pairing real, so the two halves can
    finally be measured TOGETHER:

        a GM types /warp -> the real lane authorizes, composes, audits and
        ARMS -> the real runtime appends and FIRES -> a real `queued` row
        lands in the real ndjson.

    Nothing here patches `chat_command_action`.  The only patch is the
    ForcePos version gate -- opened to a test value for the tests that need
    a composed frame, the same patch `test_gm_chat_command_action.py` has
    always used, and forced explicitly SHUT for the one test below that
    proves the withheld branch.  The gate shipped at `0` since COO-DECISION
    20260830_1645/1742 (RE-129's measured byte), so `None` is no longer the
    default either patch can rely on falling out of.

    Scene 1, not scene 2: `_login_and_start` places the character at
    `Position(1, ...)`, and `/warp <own scene> x y` is the same-scene
    ForcePos half.  A cross-scene warp stages a login scene and returns no
    action at all, so it would prove nothing about the append site.
    """

    def _rows(self):
        # The harness chdir'd into its own temp dir, so gm/commands.py's
        # repo-relative DEFAULT_LOG_PATH lands there and not in the checkout.
        path = Path(self.tmp.name) / "capture" / "gm_command_log.ndjson"
        if not path.exists():
            return []
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _warp_in_place(self, token="gm_runner"):
        path = self._config([token])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            with mock.patch.object(
                teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", 7,
            ):
                state = self._login_and_start(token)
                return state, self._say(state, "/warp 1 100 200")

    def test_the_lane_arms_the_runtime_fires_and_the_queued_row_lands(self):
        state, actions = self._warp_in_place()
        self.assertIn(
            chat_command_action.WARP_ACTION_LABEL, self._labels(actions),
            "fixture must really compose an action, or this proves nothing",
        )
        outcomes = [
            row["outcome"] for row in self._rows()
            if row["record"] == commands.AUDIT_RECORD_OUTCOME
        ]
        self.assertEqual(
            outcomes, [commands.OUTCOME_COMPOSED, commands.OUTCOME_QUEUED],
        )
        # Cleared by the append site, so nothing is left to misfire against
        # the next frame -- the property chief's hook owns, re-measured here
        # against a REAL pairing rather than a hand-built one.
        self.assertIsNone(getattr(state, "_gm_action_queued_confirm", "MISSING"))

    def test_all_three_rows_belong_to_the_one_command(self):
        self._warp_in_place()
        rows = self._rows()
        self.assertEqual(len(rows), 3)
        self.assertEqual(len({row["record_id"] for row in rows}), 1)
        self.assertEqual(
            [row["record"] for row in rows],
            [
                commands.AUDIT_RECORD_ISSUED,
                commands.AUDIT_RECORD_OUTCOME,
                commands.AUDIT_RECORD_OUTCOME,
            ],
        )

    def test_a_line_the_lane_withholds_never_reaches_the_queued_word(self):
        # The control, and the one that would catch an arming that fired on
        # composition instead of on the append: same route, same GM, gate
        # forced SHUT -- no longer the shipped state since COO-DECISION
        # 20260830_1645/1742, so this test patches it shut itself -- so
        # nothing is appended and the audit must stop at the withheld word.
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ), mock.patch.object(
            teleport_wire, "FORCE_POS_VITAL_VERSION_CONFIRMED", None,
        ):
            state = self._login_and_start("gm_runner")
            actions = self._say(state, "/warp 1 100 200")
        self.assertNotIn(
            chat_command_action.WARP_ACTION_LABEL, self._labels(actions)
        )
        outcomes = [
            row["outcome"] for row in self._rows()
            if row["record"] == commands.AUDIT_RECORD_OUTCOME
        ]
        self.assertEqual(len(outcomes), 1)
        self.assertNotEqual(outcomes[0], commands.OUTCOME_QUEUED)
        self.assertFalse(hasattr(state, "_gm_action_queued_confirm"))


if __name__ == "__main__":
    unittest.main()
