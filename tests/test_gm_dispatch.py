"""CORE-REQUEST-006 -- GM state after login, on the REAL dispatcher.

``tests/test_gm_accounts.py`` and ``tests/test_gm_state_wire.py`` prove the
allowlist and the frame encoder offline.  This file drives
``make_state_class`` headless (no server process, no socket, no client) and
proves the part CORE-REQUEST-006 asked the chief to wire: after a successful
login, an account listed in ``config/gm_accounts.json`` gets a
``GM_UPDATE_STATE_AFTER_LOGIN`` frame appended to its START_GAME_REQ
response, and an account that is not listed -- including the default
"nobody is GM" case -- gets nothing extra.

Also proves the pf-adversary finding from round 3lzfhw: a malformed
``gm_accounts.json`` (the allowlist config, not this file) must not crash
the whole dispatcher for every player's login -- ``is_gm_account()`` raises
``ValueError`` BY DESIGN on a bad config (see ``gm/accounts.py``), and that
call runs unconditionally on every START_GAME_REQ, so an unguarded call
would take the entire game-listener thread down over one operator typo,
not just refuse the one login that tripped it.
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


class GmDispatchTests(unittest.TestCase):
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
        # field_mobs.load_roster() is exercised by make_state_class's own
        # boot path (mob_ai_register/mob_loot_cell setup); loaded here only
        # so a failure there does not masquerade as a GM-lane failure.
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

    def _gm_action(self, actions):
        matches = [a for a in actions if a[0] == "GM_UPDATE_STATE_AFTER_LOGIN"]
        return matches[0] if matches else None

    # ----- default: no config file at all -> nobody is GM -----------------

    def test_default_boot_with_no_gm_config_sends_no_gm_frame(self):
        missing = Path(self.tmp.name) / "does_not_exist.json"
        with mock.patch.dict(
            gm_accounts.os.environ,
            {gm_accounts.ENV_OVERRIDE: str(missing)},
        ):
            state, actions = self._login_and_start("gm_default")
        self.assertIsNone(self._gm_action(actions))

    # ----- an account NOT on the allowlist gets nothing extra --------------

    def test_a_non_gm_account_sends_no_gm_frame(self):
        path = self._config(["someone_else"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("gm_not_listed")
        self.assertIsNone(self._gm_action(actions))

    # ----- an account ON the allowlist gets the frame, riding alongside ----

    def test_a_gm_account_gets_no_state_frame_while_the_version_guard_is_closed(self):
        # UPDATED CORE-REQUEST-016 (LANE-GM, 2026-08-27T15:24+07:00): GT-101
        # (attended, OBSERVER_CONFIRMED) measured that sending this frame
        # with vital_version=1 kills the client's session -- the exact
        # placeholder this test used to pin as correct wiring. runtime.py's
        # call site is now gated on gm.state_wire.
        # GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED (None until RE-105 pins
        # the real version), so a GM account gets NO frame today. See
        # tests/test_gm_login_state_guard.py for the real-dispatcher proof
        # that the guard actually opens once that constant is set.
        path = self._config(["gm_listed"])
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("gm_listed")
        self.assertIsNone(self._gm_action(actions))
        self.assertIn(
            "gm_update_state_frame_withheld_no_confirmed_vital_version_"
            "re105_open",
            state.events,
        )
        # The rest of login is unaffected: the ordinary START_GAME response
        # action is still present.
        self.assertTrue(
            any(a[0] == "FOUNDATION_SELECTED_START_GAME" for a in actions)
        )

    # ----- pf-adversary (round 3lzfhw): a malformed config must not -------
    # ----- crash the dispatcher for every player's login -------------------

    def test_a_malformed_gm_config_refuses_by_name_not_by_crashing(self):
        path = Path(self.tmp.name) / "gm_accounts.json"
        # gm_accounts must be a list; a string here is exactly the operator
        # typo gm/accounts.py's own docstring says must raise loudly rather
        # than silently resolve to "nobody is GM" -- proven at the
        # load_gm_accounts layer by tests/test_gm_accounts.py.  What this
        # test proves is the layer above: that raise must not propagate out
        # of dispatch() and kill the whole game-listener thread over one
        # non-GM player's login.
        path.write_text(json.dumps({"gm_accounts": "not_a_list"}))
        with mock.patch.dict(
            gm_accounts.os.environ, {gm_accounts.ENV_OVERRIDE: str(path)},
        ):
            state, actions = self._login_and_start("gm_any_player")
        self.assertIsNone(self._gm_action(actions))
        self.assertTrue(any(
            event.startswith("gm_account_lookup_failed_")
            for event in state.events
        ))
        # And the rest of the login response was unaffected: the connection
        # is still alive and answered normally, which is the whole point.
        self.assertTrue(
            any(a[0] == "FOUNDATION_SELECTED_START_GAME" for a in actions)
        )


if __name__ == "__main__":
    unittest.main()
