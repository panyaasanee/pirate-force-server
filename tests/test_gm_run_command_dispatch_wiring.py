"""CORE-REQUEST-010 -- GM run-command inbound dispatch, on the REAL dispatcher.

``tests/test_gm_command_dispatch.py`` proves ``handle_gm_run_command_vital``
offline (module-level: allowlist, refusal-by-name, the 64 KiB cap).  This
file drives ``make_state_class`` headless (no server process, no socket, no
client) and proves the part CORE-REQUEST-010 asked the chief to wire: a raw
``GM_RunGMCommandVital`` (0x51E9) frame reaching ``runtime.py`` for a GM
account produces a capture file and the right event, an account not on the
allowlist produces neither, and no reply frame is ever sent either way (this
wiring has no decode/execute/reply step -- see the CORE-REQUEST-010 letter's
own nonclaim).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation.gm import accounts as gm_accounts  # noqa: E402
from pirateforce_foundation.gm.dispatch import (  # noqa: E402
    GM_RUN_GM_COMMAND_VITAL_ID,
    MAX_RAW_PAYLOAD_LENGTH,
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


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_gm_run_command_pc(legacy, payload: bytes) -> bytes:
    """Build a minimal outer envelope carrying one 0x51E9 nested vital.

    Mirrors the outer-frame shape ``_synthetic_action_vital_pc`` in
    ``current/pf_login_game_server_v141.py`` builds for V126 -- same header
    tags, same structure -- but with GM_RUN_GM_COMMAND_VITAL_ID as the
    nested vital id and ``payload`` used verbatim as the nested body (no
    presence/tag wrapping): CORE-REQUEST-010 is explicit that this wiring
    hands ``handle_gm_run_command_vital`` the raw payload bytes untouched,
    the same slice ``gm/command_wire.py``/``gm/command_capture.py`` already
    expect, without stripping or re-encoding an envelope itself.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, GM_RUN_GM_COMMAND_VITAL_ID)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class GmRunCommandDispatchWiringTests(unittest.TestCase):
    def setUp(self):
        # Rate-limit history is process-global (gm/dispatch.py's own
        # thread-safety/test-isolation tradeoff) -- start every test from a
        # known-empty state regardless of what ran before it in this
        # process, same as tests/test_gm_command_dispatch.py's own setUp.
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
        # handle_gm_run_command_vital's capture_root defaults to a path
        # relative to the process CWD (see gm/command_capture.py) -- the
        # real wiring in runtime.py does not override it (matching the
        # CORE-REQUEST-010 letter's exact call shape), so this test runs
        # inside its own scratch directory rather than writing into the
        # repo checkout.
        self._owd = Path.cwd()
        import os
        os.chdir(self.tmp.name)
        self.addCleanup(os.chdir, self._owd)

    def _config(self, gm_accounts_value):
        path = Path(self.tmp.name) / "gm_accounts.json"
        path.write_text(json.dumps({"gm_accounts": gm_accounts_value}))
        return path

    def _login_and_start(self, token):
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

    def _send_run_command(self, state, payload=b"hello"):
        pc = _synthetic_gm_run_command_pc(self.legacy, payload)
        return state.dispatch(self.legacy.parse_outer(pc))

    # ----- a GM account: capture file written, right event fires ----------

    def test_a_gm_account_gets_a_capture_and_the_authorized_event(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            rx_before = state.rx_frames
            actions = self._send_run_command(state)
        self.assertEqual(actions, [])
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertIn("gm_run_command_authorized_capture", state.events)
        captured = list(Path("capture/gm_command_capture").rglob("*"))
        self.assertTrue(
            any(p.is_file() for p in captured),
            f"expected a capture file under capture/gm_command_capture, "
            f"found: {captured}",
        )

    # ----- a non-GM account: no capture, no reply, refusal event ----------

    def test_a_non_gm_account_gets_no_capture_and_a_refusal_event(self):
        path = self._config(["someone_else"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("not_a_gm")
            actions = self._send_run_command(state)
        self.assertEqual(actions, [])
        self.assertTrue(any(
            event.startswith("gm_run_command_refused_")
            for event in state.events
        ))
        self.assertFalse(Path("capture/gm_command_capture").exists())

    # ----- pf-adversary (round 3t3klq): a GM account whose payload is over
    # ----- the cap is authorized=True but captured_path=None -- this must
    # ----- NOT be reported the same way as a real capture.  Guards against
    # ----- a regression that reads outcome.authorized instead of
    # ----- outcome.captured_path in runtime.py's own branch. -------------

    def test_a_gm_account_over_the_cap_is_authorized_but_not_captured(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state = self._login_and_start("gm_runner")
            oversized = b"x" * (MAX_RAW_PAYLOAD_LENGTH + 1)
            actions = self._send_run_command(state, payload=oversized)
        self.assertEqual(actions, [])
        # The authorized-capture event must NOT fire for this outcome: an
        # oversized send from a real GM account is still a refusal, not a
        # capture, even though the account itself is legitimate.
        self.assertNotIn("gm_run_command_authorized_capture", state.events)
        self.assertTrue(any(
            event == "gm_run_command_refused_payload_too_large"
            for event in state.events
        ))
        self.assertFalse(Path("capture/gm_command_capture").exists())

    # ----- default boot, no gm_accounts.json at all: same as non-GM -------

    def test_default_boot_with_no_gm_config_refuses_by_name(self):
        missing = Path(self.tmp.name) / "does_not_exist.json"
        with mock.patch.dict(
            gm_accounts.os.environ,
            {gm_accounts.ENV_OVERRIDE: str(missing)},
        ):
            state = self._login_and_start("gm_default")
            actions = self._send_run_command(state)
        self.assertEqual(actions, [])
        self.assertTrue(any(
            event.startswith("gm_run_command_refused_")
            for event in state.events
        ))
        self.assertFalse(Path("capture/gm_command_capture").exists())


if __name__ == "__main__":
    unittest.main()
