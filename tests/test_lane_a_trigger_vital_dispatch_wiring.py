"""CORE-REQUEST of `pf_bridge/notes_to_chief/20260904_0434` and `0437`
(LANE-A) -- the TriggerVital (0x1FB2) inbound call site, on the REAL
dispatcher.

`tests/test_lane_a_island_trigger_log.py` proves the hook module itself
offline (the R307 capture bytes decode to the right console line, the
registration/call-site relation stays in step through the handover -- see
that file's `TheHookNeverSendsAndNeverRaisesTests`). That file cannot prove
the one thing chief's edit adds: that a raw `TriggerVital` frame reaching
`runtime.py` on a real login actually reaches
`lane_hooks.fire("vital_inbound_trigger_vital", ...)`. This file drives
`make_state_class` headless (no server process, no socket, no client) and
proves that, mirroring `tests/test_gm_run_command_dispatch_wiring.py`'s
shape for the sibling `vital_inbound_gm_run_command` point next to this one
in `runtime.py`.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
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


def _synthetic_trigger_vital_pc(legacy, payload: bytes) -> bytes:
    """A minimal outer envelope carrying one `TRIGGER_VITAL` (0x1FB2) nested
    vital, `payload` used verbatim as its body.

    Same shape as `test_gm_run_command_dispatch_wiring.py`'s
    `_synthetic_gm_run_command_pc` -- that file's own docstring is the
    reference for why this is the outer-frame shape (mirrors
    `current/pf_login_game_server_v141.py`'s own `_synthetic_action_vital_pc`
    for V126) -- with `legacy.TRIGGER_VITAL` standing in for the nested id.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TRIGGER_VITAL)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class TriggerVitalDispatchWiringTests(unittest.TestCase):
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

    def _send_trigger_vital(self, state, payload):
        pc = _synthetic_trigger_vital_pc(self.legacy, payload)
        return state.dispatch(self.legacy.parse_outer(pc))

    def test_an_island_trigger_id_reaches_the_hook_and_sends_nothing(self):
        # trigger id 153 = Prison Exile Island (world_island_dock_table.py).
        payload = self.legacy.u16tag(0x0F, 153)
        state = self._login_and_start("islandtrig")
        rx_before = state.rx_frames
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = self._send_trigger_vital(state, payload)
        console = stderr.getvalue()
        self.assertEqual(actions, [], "the hook must send nothing back")
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertIn("LANE_A_TRIGGER_VITAL", console)
        self.assertIn("ISLAND", console)
        self.assertIn("153", console)
        self.assertIn("no_responder bytes_out=0", console)

    def test_a_non_island_trigger_id_still_reaches_the_hook(self):
        # trigger id 40 = R307 frame #114's own id (a mid-ocean prop, not an
        # island) -- proves the call site fires for every TriggerVital, not
        # only ones the console happens to name ISLAND.
        payload = self.legacy.u16tag(0x0F, 40)
        state = self._login_and_start("proptrig")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = self._send_trigger_vital(state, payload)
        console = stderr.getvalue()
        self.assertEqual(actions, [])
        self.assertIn("LANE_A_TRIGGER_VITAL", console)
        self.assertIn("PROP", console)

    def test_console_line_is_ascii(self):
        payload = self.legacy.u16tag(0x0F, 153)
        state = self._login_and_start("asciitrig")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self._send_trigger_vital(state, payload)
        stderr.getvalue().encode("ascii")


if __name__ == "__main__":
    unittest.main()
