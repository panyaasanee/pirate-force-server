"""CORE-REQUEST-025 (LANE-A, 20260828_0427) on the REAL dispatcher.

RE-119 (STATIC-ON-BRIDGE, PASS/DONE) proved the client's own response
handler treats an empty ``CTracePathVital`` (0x2F92, record count=0) as a
clean end-of-search signal that clears the permanent "finding path..."
stall the client shows after a ``CTracePathReqVital`` (0x4391) GO! click
never gets answered.  Before this round's wiring nothing in ``runtime.py``
recognized 0x4391 at all (KA1A finding, 20260828_0235); this file drives
``make_state_class`` headless the same way ``tests/test_mob_combat_cadence_
wiring.py`` does and checks the production dispatch path actually answers
it, with the exact empty-vector byte layout ``trace_path.py`` promises --
and that a connection with no character selected yet gets no reply
(fail-closed, matching every other lane in this file).

NOT proven here: any waypoint/auto-walk semantics -- CORE-REQUEST-025
explicitly scopes this to the empty-vector fallback, and RE-119 T4 leaves
the request's own discriminator field bounded negative.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import trace_path  # noqa: E402
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


class TracePathWiringTests(unittest.TestCase):
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

    def _state_type(self):
        return make_state_class(self.legacy, self.lifecycle, self.projector)

    def _req_pc(self):
        legacy = self.legacy
        return (
            legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + legacy.u32tag(0x14, 0)
            + legacy.u8tag(0x08, 0)
            + legacy.u8tag(0x0B, 2)
            + legacy.u16tag(0x12, 1)
            + legacy.u16tag(0x12, trace_path.TRACE_PATH_REQ_VITAL_ID)
            + legacy.u8tag(0x0B, 0)
        )

    def test_no_selected_character_gets_no_reply(self):
        state = self._state_type()("trace_path_no_select")
        actions = state.dispatch(self.legacy.parse_outer(self._req_pc()))
        self.assertEqual(actions, [])
        self.assertIn("trace_path_no_selected_no_reply", state.events)
        self.assertEqual(state.rx_frames, 1)

    def _logged_in_state(self, token):
        legacy = self.legacy
        state = self._state_type()(token)
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc(token)
        ))
        state.dispatch(legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def test_selected_character_gets_the_exact_empty_vector_reply(self):
        state = self._logged_in_state("trace_path_select")
        expected_pc, expected_frame = trace_path.make_trace_path_empty_response(
            self.legacy
        )
        actions = state.dispatch(self.legacy.parse_outer(self._req_pc()))
        self.assertEqual(len(actions), 1)
        label, pc, frame, delay = actions[0]
        self.assertEqual(label, "TRACE_PATH_EMPTY_VECTOR_REPLY")
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(delay, 0.0)
        self.assertIn("trace_path_empty_vector_reply", state.events)

    def test_response_payload_is_a_bare_zero_record_count(self):
        legacy = self.legacy
        pc, _frame = trace_path.make_trace_path_empty_response(legacy)
        # Structurally re-parse the produced pc as a single-vital RuntimeRes
        # and confirm the nested vital IS CTracePathVital with a payload
        # that is exactly one u16 tag 0x12 = 0 (record count) and nothing
        # else -- i.e. no accidental extra bytes leaking past the count
        # field before the collection's trailing derived-class mask.
        parsed = legacy.parse_outer(pc)
        self.assertEqual(parsed.vital_count, 1)
        self.assertEqual(parsed.nested_id, trace_path.TRACE_PATH_VITAL_ID)
        self.assertEqual(
            parsed.nested_payload,
            legacy.u16tag(0x12, 0) + legacy.u8tag(0x0B, 0),
        )

    def test_repeated_requests_each_get_their_own_empty_reply(self):
        state = self._logged_in_state("trace_path_repeat")
        rx_before = state.rx_frames
        first = state.dispatch(self.legacy.parse_outer(self._req_pc()))
        second = state.dispatch(self.legacy.parse_outer(self._req_pc()))
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertEqual(first[0][1], second[0][1])
        self.assertEqual(state.rx_frames, rx_before + 2)


if __name__ == "__main__":
    unittest.main()
