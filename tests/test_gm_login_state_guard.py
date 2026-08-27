"""CORE-REQUEST-016 (LANE-GM, 2026-08-27T15:24+07:00) -- guard around
``GM_UPDATE_STATE_AFTER_LOGIN``, driven through the REAL dispatcher.

GT-101 (attended, OBSERVER_CONFIRMED 2026-08-27T14:39+07:00) measured that
sending ``GM_UpdateGMStateVital`` (0x5A19) with ``vital_version=1`` makes the
client reject the frame by this vital's own id, halt, and close the socket --
against the owner's own real GM account.  ``gm.state_wire.
GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED`` stayed ``None`` -- and runtime.py's
call site stayed gated on it being not-None -- until RE-105 (STATIC-ON-BRIDGE,
notes_to_chief/20260827_1613_RE-105-RESULT-VITAL-VERSION-ZERO-GENERIC-MISMATCH-PATH.md)
pinned the real value as ``0``.

This drives the real dispatcher end to end and proves three things: a GM
account now gets the frame, at the exact byte-level header RE-105 traced
(``12 19 5A 0B 00``); a non-GM account is unaffected; and the guard is a real
conditional, not a hardcoded always-send -- closing it again (module constant
back to ``None``) withholds the frame exactly as it did before this round.
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
from pirateforce_foundation.gm import state_wire  # noqa: E402
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


class GmLoginStateGuardTests(unittest.TestCase):
    def setUp(self):
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
        actions = state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state, actions

    def test_a_gm_account_gets_the_re105_pinned_state_frame(self):
        self.assertEqual(state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED, 0)
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("gm_runner")
        by_label = {action[0]: action for action in actions}
        self.assertIn("GM_UPDATE_STATE_AFTER_LOGIN", by_label)
        self.assertNotIn(
            "gm_update_state_frame_withheld_no_confirmed_vital_version_"
            "re105_open",
            state.events,
        )
        _, pc, frame, delay = by_label["GM_UPDATE_STATE_AFTER_LOGIN"]
        self.assertEqual(delay, 0.0)
        expected_pc, expected_frame = state_wire.make_gm_update_state_frame(
            self.legacy, 0, 0, 0, 0,
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        # RE-105 T1/T3: nested vital id 0x5A19 (tag 0x12, u16 LE) followed
        # directly by version tag 0x0B with value 0 -- the one byte GT-101
        # proved fatal as 1. The outer envelope's own protocol version
        # (0x08, 4) is a separate field and is untouched by this change.
        self.assertIn(b"\x08\x04", pc)
        self.assertIn(b"\x12\x19\x5a\x0b\x00", pc)
        self.assertNotIn(b"\x12\x19\x5a\x0b\x01", pc)

    def test_a_non_gm_account_is_unaffected(self):
        path = self._config(["gm_runner"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("not_a_gm")
        labels = [action[0] for action in actions]
        self.assertNotIn("GM_UPDATE_STATE_AFTER_LOGIN", labels)
        self.assertNotIn(
            "gm_update_state_frame_withheld_no_confirmed_vital_version_"
            "re105_open",
            state.events,
        )

    def test_the_guard_still_closes_if_the_constant_is_unset(self):
        # Proves this is a real gate, not a hardcoded always-send: patch the
        # module's own constant back to None (not a local copy runtime.py
        # could have captured at import time) and the frame must be
        # withheld again, exactly as it was before RE-105 closed.
        path = self._config(["gm_runner"])
        with mock.patch.object(
            state_wire, "GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED", None,
        ), mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("gm_runner")
        labels = [action[0] for action in actions]
        self.assertNotIn("GM_UPDATE_STATE_AFTER_LOGIN", labels)
        self.assertIn(
            "gm_update_state_frame_withheld_no_confirmed_vital_version_"
            "re105_open",
            state.events,
        )


if __name__ == "__main__":
    unittest.main()
