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

import contextlib
import io
import sys
import tempfile
import types
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
from pirateforce_foundation.gm import warp_scene_persist  # noqa: E402
from pirateforce_foundation.gm.warp_target_record import (  # noqa: E402
    UNREADABLE_CHARACTER_ID,
)
from dataclasses import replace  # noqa: E402
from unittest import mock  # noqa: E402
from pirateforce_foundation import world_scene_travel  # noqa: E402
import pf_bent_scene_registry as bent_registry  # noqa: E402
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

    def _login_only(self, token):
        """Logged in, no character selected -- the unauthenticated shape."""
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type(token)
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_client_login_pc(token)
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


class ReplayDebtTests(_SeamCase):
    """pf-adversary D1 of #1109: the replay this branch built, and its fix.

    The finding, measured on the real dispatcher: one recorded order, the
    same echo bytes twice, TWO travel frames -- the seam's on echo #1 and
    v141's own V137 transport probe on echo #2, because the fall-through
    handed the frame to a route whose one-shot latch the seam had left
    unfired.  What is pinned here is the ownership rule that closes it: from
    the first transport this seam sends, an echo it cannot consume is
    REFUSED here, not passed on; before that first transport nothing changes.
    """

    def _v141_saw_this_frame(self, state, before):
        """How many v131/v136 capture events v141 appended since `before`.

        v141's own branch appends two events for EVERY decodable frame of
        this class that reaches it, whether or not it recognises the bytes
        (current/pf_login_game_server_v141.py:4109-4126).  Counting them is
        the only direct read of "the frame fell through", which is the thing
        the mutant must break -- an assertion on transport actions alone
        cannot see it, because these synthetic bytes are not v141's exact
        V136 confirm PC and so buy no probe even when they do fall through.
        """
        return len([
            e for e in state.events[before:]
            if str(e).startswith("v131_teleport_check_")
            or str(e).startswith("v136_marker1_positive_confirm_capture")
        ])

    def test_before_the_first_transport_an_unmatched_echo_reaches_v141(self):
        # The control for the test below, and the behaviour #1101's own
        # fall-through exists to protect.  Without this pair, "the seam
        # refuses" and "the seam never falls through" are indistinguishable.
        state = self._login_and_start("m2ctl")
        before = len(state.events)
        self._echo(state, 343)
        self.assertGreater(self._v141_saw_this_frame(state, before), 0)
        self.assertEqual(state.teleport_check_sink().refusals, [])

    def test_after_the_first_transport_a_replay_never_reaches_v141(self):
        state = self._login_and_start("m2replayv141")
        self._record(state)
        self._tick(state)
        self.assertEqual(len(self._of(self._echo(state), TRANSPORT_ACTION)), 1)
        self.assertEqual(
            state.teleport_check_sink().answered,
            {(self._character_id(state), MARKER)},
        )
        before = len(state.events)
        self.assertEqual(self._of(self._echo(state), TRANSPORT_ACTION), [])
        self.assertEqual(
            self._v141_saw_this_frame(state, before), 0,
            "the replay must not be handed to the frozen route, whose "
            "one-shot latch is still unfired and would pay a second journey",
        )
        self.assertEqual(
            state.teleport_check_sink().refusals,
            [tc.ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER],
        )

    def _v141_marker1_confirm(self, state):
        """v141's OWN exact marker-1 confirm, the bytes that buy its probe.

        The synthetic echo helper cannot reach v141's payout at all -- its
        `exact_v136_marker1_confirm` test compares `parsed.raw_pc` against
        this frozen constant.  Arming `v136_marker1_prompt_sent` is what
        v141's own Q3020 accept chain does at
        current/pf_login_game_server_v141.py:3718.
        """
        state.v136_marker1_prompt_sent = True
        return state.dispatch(
            self.legacy.parse_outer(self.legacy.V136_MARKER1_CONFIRM_PC))

    def test_v141s_marker1_probe_still_fires_after_this_seam_moved_the_player(self):
        # pf-adversary F1, the regression a BROADER ownership rule caused and
        # this is the control against it returning: keying the refusal on
        # "has this seam ever transported" made the seam swallow every later
        # frame of this class, so v141's probe -- and both of its
        # unconditional capture events -- went dark for the rest of the
        # session, on a connection whose order was for marker 17.
        state = self._login_and_start("m2f1")
        self._record(state)
        self._tick(state)
        self.assertEqual(len(self._of(self._echo(state), TRANSPORT_ACTION)), 1)
        labels = [a[0] for a in self._v141_marker1_confirm(state) if a]
        self.assertIn(
            "V137_ISOLATED_COMPOSITIONAL_MARKER1_TELEPORTVITAL_TRANSPORT_"
            "PROBE_ONCE", labels,
        )
        self.assertTrue(state.v137_marker1_transport_sent)

    def test_one_order_buys_one_travel_frame_however_often_it_is_echoed(self):
        # pf-adversary F2: D1's own symptom, on v141's exact bytes, which is
        # the only shape that can pay TWICE.  Counting travel frames across
        # BOTH routes is the assertion D1 was actually about -- the seam's
        # own action alone cannot see v141's payout.
        state = self._login_and_start("m2f2")
        self._record(state, marker_id=1)
        self._tick(state)
        travel = []
        for _ in range(2):
            travel += [
                a[0] for a in self._v141_marker1_confirm(state) if a
                and (a[0] == TRANSPORT_ACTION or "TRANSPORT_PROBE" in a[0])
            ]
        self.assertEqual(travel, [TRANSPORT_ACTION])
        self.assertFalse(state.v137_marker1_transport_sent)

    def test_the_replay_is_still_counted_exactly_once(self):
        state = self._login_and_start("m2replaycount")
        self._record(state)
        self._tick(state)
        self._echo(state)
        before = state.rx_frames
        self._echo(state)
        self.assertEqual(state.rx_frames, before + 1)

    def test_v141s_own_marker1_latch_is_never_written_by_this_seam(self):
        # The one-line fix that was NOT taken, pinned so it cannot be taken
        # later: `v137_marker1_transport_sent` is also read as "this
        # connection is at marker 1" by the V138 ready -> V140 population
        # branch, so writing it here would hand a population snapshot to a
        # connection v141 never transported.
        state = self._login_and_start("m2latch")
        self._record(state)
        self._tick(state)
        self.assertEqual(len(self._of(self._echo(state), TRANSPORT_ACTION)), 1)
        self.assertFalse(state.v137_marker1_transport_sent)
        self.assertFalse(state.v136_marker1_prompt_sent)


class ClosedSessionTests(_SeamCase):
    """pf-adversary D3 of #1109: the drain ran outside the logout guards."""

    def test_no_prompt_goes_out_after_the_logout_is_acknowledged(self):
        state = self._login_and_start("m2logout")
        self._record(state)
        state.logout_acknowledged = True
        self.assertEqual(self._of(self._tick(state), PROMPT_ACTION), [])

    def test_the_order_is_left_queued_on_a_closed_session(self):
        # Left queued, not dropped: a drain that emptied the queue would
        # erase the evidence of what the closed session was owed.
        state = self._login_and_start("m2logoutqueue")
        self._record(state)
        state.logout_acknowledged = True
        self._tick(state)
        self.assertEqual(len(state.teleport_check_sink().unsent), 1)
        self.assertIn("lane_a_m2_teleport_check_post_ack_no_prompt",
                      state.events)

    def test_a_connection_with_no_character_selected_composes_nothing(self):
        state = self._login_only("m2nosel")
        self.assertIsNone(state.foundation.selected)
        state.teleport_check_sink().record(1, tc.open_check(MARKER))
        self.assertEqual(self._of(self._tick(state), PROMPT_ACTION), [])
        self.assertEqual(len(state.teleport_check_sink().unsent), 1)
        self.assertIn("lane_a_m2_teleport_check_no_selected_no_prompt",
                      state.events)

    def test_a_closed_session_is_noted_once_not_once_per_late_frame(self):
        # pf-adversary F7: 20 post-ack frames left 20 rows in the events of a
        # session whose guards exist to stop lanes writing through it.
        state = self._login_and_start("m2postackonce")
        self._record(state)
        state.logout_acknowledged = True
        for _ in range(5):
            self._tick(state)
        self.assertEqual(
            len([e for e in state.events
                 if e == "lane_a_m2_teleport_check_post_ack_no_prompt"]), 1)


class ConsoleNeverKillsTheListenerTests(_SeamCase):
    """pf-adversary D2 of #1109: five bare print() calls on the dispatch path.

    v141's `game_listener` wraps `state.dispatch()` in a `try:` with no
    `except`, so anything raising here kills the accept loop for every
    session on the process.
    """

    def test_a_console_line_that_cannot_be_built_costs_the_frame_nothing(self):
        state = self._login_and_start("m2sayraise")
        self._record(state)
        original = tc.prompt_console_line

        def boom(_pending):
            raise RuntimeError("console line builder exploded")

        tc.prompt_console_line = boom
        try:
            actions = self._tick(state)
        finally:
            tc.prompt_console_line = original
        self.assertEqual(len(self._of(actions, PROMPT_ACTION)), 1)

    def test_a_dead_stdout_costs_the_frame_nothing(self):
        state = self._login_and_start("m2deadout")
        self._record(state)

        class _DeadOut:
            def write(self, _text):
                raise ValueError("I/O operation on closed file")

            def flush(self):
                raise ValueError("I/O operation on closed file")

        with contextlib.redirect_stdout(_DeadOut()):
            actions = self._tick(state)
        self.assertEqual(len(self._of(actions, PROMPT_ACTION)), 1)

    def test_an_order_that_raises_does_not_strand_the_ones_behind_it(self):
        # The second half of D2: the first draft moved the whole queue into
        # a local and emptied `unsent` before the loop, so anything raising
        # on one order silently stranded every order behind it -- never
        # prompted, never counted, still redeemable.
        state = self._login_and_start("m2strand")
        self._record(state)
        self._record(state, marker_id=343)
        original = tc.encode_prompt
        calls = []

        def boom(legacy, marker_id):
            calls.append(marker_id)
            if len(calls) == 1:
                raise MemoryError("not a TeleportCheckError")
            return original(legacy, marker_id)

        tc.encode_prompt = boom
        try:
            # NOT `assertRaises`.  The first draft of this test pinned the
            # MemoryError escaping dispatch() as intended -- in the class
            # written to answer a finding whose whole point is that nothing
            # here may raise into a listener with no `except` (pf-adversary
            # F3).  What must hold is that the frame survives AND the order
            # behind the failure is still prompted, on this same frame.
            actions = self._tick(state)
        finally:
            tc.encode_prompt = original
        self.assertEqual(len(self._of(actions, PROMPT_ACTION)), 1)
        self.assertEqual(state.teleport_check_sink().unsent, [])
        self.assertIn("CHECK_REFUSED_PROMPT_ENCODER_RAISED",
                      state.teleport_check_sink().refusals)

    def test_a_transport_encoder_that_raises_does_not_kill_the_listener(self):
        # pf-adversary F3: `encode_transport` reads `pending.destination` raw
        # -- it does not re-resolve through `marker_destination` the way
        # `encode_prompt` does -- and three shapes of a hand-built
        # destination raise out of it AFTER the player has been asked.
        state = self._login_and_start("m2transportraise")
        pending = self._record(state)
        self._tick(state)
        original = tc.encode_transport

        def boom(_legacy, _pending):
            raise OverflowError("float too large to pack with f format")

        tc.encode_transport = boom
        try:
            actions = self._echo(state)
        finally:
            tc.encode_transport = original
        self.assertEqual(self._of(actions, TRANSPORT_ACTION), [])
        self.assertIn("ECHO_REFUSED_TRANSPORT_ENCODER_RAISED",
                      state.teleport_check_sink().refusals)
        # Nothing reached the socket, so nothing is recorded as answered --
        # an honest retry must not be refused as a replay.
        self.assertEqual(state.teleport_check_sink().answered, set())
        self.assertIsNotNone(pending)

    def test_the_prompts_go_out_in_the_order_they_were_recorded(self):
        # pf-adversary F5 M2: `pop()` instead of `pop(0)` reverses the queue
        # and nothing noticed.  Two orders, two windows, and the player is
        # asked about the first one first.
        state = self._login_and_start("m2fifo")
        self._record(state, marker_id=MARKER)
        self._record(state, marker_id=343)
        prompts = self._of(self._tick(state), PROMPT_ACTION)
        self.assertEqual(len(prompts), 2)
        first, _ = tc.encode_prompt(self.legacy, MARKER)
        self.assertEqual(prompts[0][1], first)


class ConsoleLinesTests(_SeamCase):
    """pf-adversary F5: the D2 wrapper turned every console defect silent.

    Five mutants -- the wrapper returning immediately, either console call
    deleted, its arguments swapped, the `None` guard removed -- left the
    whole file green, because no test captured stdout.  The attended round
    reads exactly these lines off the bridge console, so a seam that prints
    nothing is a seam whose test says nothing.
    """

    def _lines(self, fn, *args):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            fn(*args)
        return [ln for ln in buffer.getvalue().splitlines()
                if ln.startswith(tc.TOKEN)]

    def test_the_prompt_the_echo_and_the_transport_each_say_one_line(self):
        state = self._login_and_start("m2console")
        self._record(state)
        prompt_lines = self._lines(self._tick, state)
        self.assertEqual(len(prompt_lines), 1)
        # The verb is read out of the module, not spelled here.  LANE-A
        # renamed this line on main (their 0422 letter: "line 1 is not proof
        # of a send", so it says ORDER_RECORDED ... sent=0 and the TRANSPORT
        # line below is the only one that claims bytes left).  It is their
        # module and their wording; this file must follow it, not pin a word
        # it does not own -- and an assertion spelling "PROMPT" is exactly
        # what went red on the merge that brought the rename in.
        self.assertIn(
            tc.prompt_console_line(tc.open_check(MARKER)).split()[1],
            prompt_lines[0])
        self.assertIn(f"marker={MARKER}", prompt_lines[0])
        echo_lines = self._lines(self._echo, state)
        # THREE since R401, not two: the scene relabel prints its own line
        # between the echo verdict and the transport receipt.  It has to,
        # because without it an attended tester reading the console saw the
        # identical `TRANSPORT ... scene=126` whether the relabel had been
        # applied or refused (pf-adversary R401 D6; COO-DECISION 20260904_1646
        # item 2, "a tester reads the CONSOLE, not session.events").
        self.assertEqual(len(echo_lines), 3)
        self.assertIn("ECHO", echo_lines[0])
        self.assertIn("verdict=OK", echo_lines[0])
        self.assertIn("TRANSPORT_RESYNC", echo_lines[1])
        # `applied=` is the whole point of the line, and after
        # PANYA-DECISION 20260908_1218 the shipped registry ADMITS marker
        # 17's destination at login, so the relabel is applied here.  The
        # digit is read out of the registry rather than spelled, so this
        # case says what the console must agree with instead of pinning
        # which way a row happens to be set today; the REFUSED reading is
        # driven, under a bent row, by the case below -- neither half is
        # a skip.
        scene_id = tc.marker_destination(MARKER).scene_id
        self.assertTrue(warp_scene_persist.login_would_accept(scene_id))
        self.assertIn("applied=1", echo_lines[1])
        self.assertIn("scene=%d" % scene_id, echo_lines[1])
        self.assertIn("TRANSPORT", echo_lines[2])
        self.assertNotIn("RESYNC", echo_lines[2])

    def test_a_refused_relabel_still_says_applied_0_on_the_console(self):
        """The other reading of the same line, kept alive by a bent row.

        Before 1218 the shipped registry drove this branch on its own; it
        no longer does, and the console wording for a REFUSED relabel is
        exactly what an attended tester needs to tell "the scene moved"
        from "the scene did not".  `pf_bent_scene_registry` shuts the one
        row and asserts the bend took, so this is the refusal path itself
        and not a fixture proving nothing.
        """
        scene_id = tc.marker_destination(MARKER).scene_id
        with bent_registry.process_reads(bent_registry.shut_at_login(scene_id)):
            state = self._login_and_start("m2consolebarred")
            self._record(state)
            self._lines(self._tick, state)
            echo_lines = self._lines(self._echo, state)
            self.assertEqual(len(echo_lines), 3)
            self.assertIn("TRANSPORT_RESYNC", echo_lines[1])
            self.assertIn("applied=0", echo_lines[1])
            self.assertIn("scene=%d" % scene_id, echo_lines[1])

    def test_a_refused_replay_says_why_on_the_console(self):
        state = self._login_and_start("m2consolerefuse")
        self._record(state)
        self._tick(state)
        self._echo(state)
        lines = self._lines(self._echo, state)
        self.assertEqual(len(lines), 1)
        self.assertIn(tc.ECHO_REFUSED_NO_ORDER_FOR_THIS_PLAYER, lines[0])


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


class RecordingDoorTests(_SeamCase):
    """pf-adversary G2 of #1109: the advertised door validated nothing.

    The damage was never on the frame that recorded the bad row.  It was on
    an UNRELATED LATER frame: `resolve_echo` walks every row in `orders`
    reading `order.pending.marker_id`, so the next inbound echo of ANY marker
    id raised out of `dispatch()` into a listener with no `except`, and the
    accept loop died for every session on the process.
    """

    def test_a_row_that_is_not_a_pending_check_is_refused_at_the_door(self):
        state = self._login_and_start("m2doorshape")
        stored = state.teleport_check_sink().record(
            self._character_id(state), "not a PendingCheck",
        )
        self.assertEqual(stored, 0)
        self.assertEqual(state.teleport_check_sink().orders, [])
        self.assertEqual(state.teleport_check_sink().unsent, [])
        self.assertIn("CHECK_REFUSED_ORDER_PENDING_NOT_A_PENDING_CHECK",
                      state.teleport_check_sink().refusals)

    def test_a_refused_row_cannot_kill_a_later_echo(self):
        # THE MEASURED DAMAGE, driven end to end: record the bad row through
        # the real door, then send an ordinary echo of a marker that has
        # nothing to do with it.  Before the door check this raised
        # AttributeError out of dispatch(); the accept loop dies there.
        state = self._login_and_start("m2doorlaterecho")
        state.teleport_check_sink().record(self._character_id(state), object())
        actions = self._echo(state, marker_id=MARKER)
        self.assertIsInstance(actions, list)

    def test_a_refused_row_costs_no_slot_of_the_cap(self):
        state = self._login_and_start("m2doorcap")
        for _ in range(5):
            state.teleport_check_sink().record(
                self._character_id(state), None)
        self.assertEqual(len(state.teleport_check_sink().orders), 0)

    def test_an_order_nobody_could_redeem_is_refused_not_stored(self):
        # Not a crash -- resolve_echo already refuses a non-int owner -- but
        # a row no echo can ever consume, holding one of the 64 slots for the
        # life of the connection while the recorder answered "stored".
        state = self._login_and_start("m2doorowner")
        stored = state.teleport_check_sink().record("7", tc.open_check(MARKER))
        self.assertEqual(stored, 0)
        self.assertIn("CHECK_REFUSED_ORDER_CHARACTER_ID_NOT_AN_INT",
                      state.teleport_check_sink().refusals)

    def test_a_bool_owner_is_refused_with_the_non_ints(self):
        # `True` is a valid Python int and a catastrophic character id --
        # `_coerce_marker_id`'s own reason, applied to the other field.
        state = self._login_and_start("m2doorbool")
        self.assertEqual(
            state.teleport_check_sink().record(True, tc.open_check(MARKER)), 0)
        self.assertEqual(state.teleport_check_sink().orders, [])

    def test_a_subclass_of_pending_check_is_refused_too(self):
        # pf-adversary R399: the `type(...) is not` / `isinstance` choice was
        # argued in the docstring and pinned by nothing -- swapping it for
        # `isinstance` left the whole file green.  A subclass is a tuple this
        # file did not build, and `encode_transport` reads its `destination`
        # raw without re-resolving it, so the narrow test is the one this
        # door promises: exactly what `open_check` returns.
        class _LooksLikeOne(tc.PendingCheck):
            pass

        state = self._login_and_start("m2doorsubclass")
        real = tc.open_check(MARKER)
        stored = state.teleport_check_sink().record(
            self._character_id(state), _LooksLikeOne(*real))
        self.assertEqual(stored, 0)
        self.assertEqual(state.teleport_check_sink().orders, [])

    def test_the_door_still_takes_the_order_it_was_built_for(self):
        state = self._login_and_start("m2doorgood")
        self.assertEqual(
            state.teleport_check_sink().record(
                self._character_id(state), tc.open_check(MARKER)), 1)
        self.assertEqual(len(state.teleport_check_sink().unsent), 1)


class _JourneyFixture(_SeamCase):
    """The journey helpers the two classes below share.

    Split out of `SelectedSceneIsRelabelledOnlyWhenTheLoginCanTakeItBackTests`
    when the arrival class arrived: a subclass would have re-run every test of
    that class under a second name, and a second copy of `_report`/`_journey`
    would let the two halves of one seam drift apart in their fixtures.  No
    test methods live here on purpose.
    """


    def _target_pos_pc(self, x, y, z, heading=0.0, moving=1):
        """The exact singleton shape parse_v141_refresh_target_pos accepts.

        Copied from tests/test_gm_warp_position_confirmed.py for the reason
        that file gives: the server never composes a client->server TargetPos,
        so the envelope lives in the tests.
        """
        return (
            self.legacy.u16tag(0x12, self.legacy.GSCN_RUNTIME_PROTOCOL_REQ)
            + self.legacy.u32tag(0x14, 0)
            + self.legacy.u8tag(0x08, 0)
            + self.legacy.u8tag(0x0B, 2)
            + self.legacy.u16tag(0x12, 1)
            + self.legacy.u16tag(0x12, self.legacy.TARGET_POS_VITAL)
            + self.legacy.u8tag(0x0B, 0)
            + self.legacy.f32tag(x) + self.legacy.f32tag(y)
            + self.legacy.f32tag(z) + self.legacy.f32tag(heading)
            + self.legacy.u8tag(0x0B, moving)
            + self.legacy.u8tag(0x0B, 0)
        )

    def _report(self, state, x, y, z):
        with contextlib.redirect_stderr(io.StringIO()):
            with contextlib.redirect_stdout(io.StringIO()):
                return state.dispatch(self.legacy.parse_outer(
                    self._target_pos_pc(x, y, z)
                ))

    def _journey(self, token, marker_id=MARKER):
        state = self._login_and_start(token)
        self._record(state, marker_id=marker_id)
        self._tick(state)
        actions = self._echo(state, marker_id=marker_id)
        return state, actions

    def test_every_marker_this_seam_can_prompt_for_is_now_login_accepted(self):
        """~~test_every_marker_this_seam_can_prompt_for_a_sea_scene_is_login_
        barred~~ -- INVERTED, LANE-A round 9lv3fa, 2026-09-08.

        This case was written to "fail loudly the day the registry changes
        and this refusal stops being necessary".  That day is
        PANYA-DECISION 20260908_1218, and it did fail loudly, so here is what
        it means rather than a deleted assertion:

        WHAT THIS CLASS PINS IS UNCHANGED.  The seam still does not write the
        durable row at send time.  What changed is WHICH reason holds it.  It
        used to have two: the client has not confirmed the move yet
        (COO-DECISION 20260828_2130 - a frame that left the server is a
        REQUEST, and the durable write happens on the first TargetPos after
        it), and the destination was barred at login so a written row would
        have locked the character out.  1218 removed the second.  The first
        is untouched by 1218 and is the whole reason on its own; every other
        case in this class drives it directly.
        """
        for marker_id in (17, 343, 345):
            destination = tc.marker_destination(marker_id)
            self.assertTrue(
                warp_scene_persist.login_would_accept(destination.scene_id),
                "marker %d -> scene %d must be login-accepted under 1218"
                % (marker_id, destination.scene_id),
            )
        self.assertTrue(warp_scene_persist.login_would_accept(
            tc.marker_destination(1).scene_id))

    @contextlib.contextmanager
    def _registry_open_at_login_on(self, scene_id):
        """The registry LANE-A's PR (PANYA 1218 item 1) leaves behind.

        Bent rather than waited for, deliberately: this seam's behaviour after
        that flip is chief's to prove, and a test that can only run once
        somebody else's PR has merged proves it on nobody's schedule.  Only
        `login_entry_allowed` moves; the row keeps its own decreed spawn, so
        `login_would_accept`'s OTHER condition is answered by the real data.
        """
        real = world_scene_travel.load_scene_registry()
        bent = replace(
            real,
            destinations=tuple(
                replace(target, login_entry_allowed=True)
                if target.n_id == scene_id else target
                for target in real.destinations
            ),
        )
        self.assertIsNotNone(
            bent[scene_id].spawn,
            "this row must keep a spawn or login_would_accept refuses it for "
            "the OTHER reason and the fixture proves nothing",
        )
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        try:
            with mock.patch.object(
                world_scene_travel, "load_scene_registry", return_value=bent
            ):
                self.assertTrue(warp_scene_persist.login_would_accept(scene_id),
                                "the fixture bent nothing")
                yield bent
        finally:
            warp_scene_persist.reset_login_registry_snapshot_for_tests()

    @contextlib.contextmanager
    def _registry_barred_at_login_on(self, scene_id):
        """The other half of the same fixture, and NOT a skip.

        The refusal branch has to stay tested after LANE-A opens the four
        pins, and `NOW 2050` bars skip/xfail/allowlist outright, so the case
        below bends the row shut rather than standing down when the shipped
        registry stops being shut on its own.  Today this fixture agrees with
        the shipped data; the day it stops agreeing it is still the fence a
        future spawnless scene will take.
        """
        real = world_scene_travel.load_scene_registry()
        bent = replace(
            real,
            destinations=tuple(
                replace(target, login_entry_allowed=False)
                if target.n_id == scene_id else target
                for target in real.destinations
            ),
        )
        warp_scene_persist.reset_login_registry_snapshot_for_tests()
        try:
            with mock.patch.object(
                world_scene_travel, "load_scene_registry", return_value=bent
            ):
                self.assertFalse(
                    warp_scene_persist.login_would_accept(scene_id),
                    "the fixture bent nothing")
                yield bent
        finally:
            warp_scene_persist.reset_login_registry_snapshot_for_tests()

    def _destination_scene(self, marker_id=MARKER):
        return tc.marker_destination(marker_id).scene_id

class SelectedSceneIsRelabelledOnlyWhenTheLoginCanTakeItBackTests(_JourneyFixture):
    """What a completed M2 journey does to `selected.position.scene_id`.

    PANYA-DECISION 20260908_1218 item 2 is the owner's answer to the question
    round R399 could not decide alone: logging back in must put a character at
    the last point before logout, in ANY scene, the open sea included.  So the
    relabel R399 withdrew is back -- BEHIND THE FENCE THAT MADE THE WITHDRAWAL
    NECESSARY.  See `_m2_transport_resync_selected_scene` for the two fences;
    both halves are proved here, the second against a bent registry, so this
    file does not go red on the day LANE-A lands and does not quietly stop
    testing anything either.
    """

    def test_the_seam_agrees_with_the_registry_about_all_three_sea_scenes(self):
        # THE CONTRACT, RE-DERIVED RATHER THAN QUOTED, for the three decreed
        # arrival rows M2 exists to reach.  This is deliberately NOT an
        # assertion that they are barred (they are today, and PANYA 1218 item
        # 1 orders them opened): it asserts that whatever the registry says,
        # the seam does the matching thing.  It therefore stays meaningful
        # across LANE-A's flip instead of going red on it.
        for marker_id in (17, 343, 345):
            scene_id = self._destination_scene(marker_id)
            open_at_login = warp_scene_persist.login_would_accept(scene_id)
            state, actions = self._journey(
                "m2agrees%d" % marker_id, marker_id=marker_id)
            self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
            relabelled = state.foundation.selected.position.scene_id == scene_id
            self.assertEqual(
                open_at_login, relabelled,
                "marker %d -> scene %d: login_would_accept=%r but the seam "
                "%s relabel"
                % (marker_id, scene_id, open_at_login,
                   "did" if relabelled else "did not"),
            )

    def test_a_login_barred_destination_is_declined_and_says_so(self):
        scene_id = self._destination_scene()
        with self._registry_barred_at_login_on(scene_id):
            state, actions = self._journey("m2barred")
            self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
            # LAYER 1 (server state): the label is untouched...
            self.assertEqual(state.foundation.selected.position.scene_id, 1)
            self.assertFalse(
                getattr(state, "scene_label_is_server_guess", False))
            # ...and the decline is NAMED.  A silent decline is how the
            # pre-existing wrong-label bug hid for as long as it did.
            self.assertIn(
                "lane_a_m2_transport_resync_refused_login_barred_%d" % scene_id,
                state.events,
            )

    def test_an_open_destination_is_relabelled_with_the_census_unlatched(self):
        scene_id = self._destination_scene()
        with self._registry_open_at_login_on(scene_id):
            # LATCHED FIRST, AND THIS IS THE WHOLE TEST.  A first draft of
            # this case asserted the fields were falsy after a journey and
            # MEASURED NOTHING: on a fresh session they are already falsy, so
            # deleting the clearing block outright left all 50 cases green
            # (mutant run, this round).  `world_census_sent` is latched once
            # per CONNECTION and is exactly the field whose stale True makes
            # every later scene of a session silent, so the fixture puts the
            # session in the state a real second scene arrives in.
            state = self._login_and_start("m2open")
            state.world_census_sent = True
            state.world_census_refused = True
            state.last_target_pos = (1.0, 2.0, 3.0)
            state.population_indices = (7,)
            state.world_census_indices = (7,)
            state.population_refresh_anchor = (1.0, 2.0, 3.0)
            state.census_anchor_record = (1.0, 2.0, 3.0)
            state.npc_idle_action_sent = True
            state.world_census_identity_resolved = True
            state.world_census_actor_count = 97
            state.mob_combat_announced_membership = (11, 12)
            generation_before = state.mob_combat_announced_membership_generation
            self._record(state)
            self._tick(state)
            actions = self._echo(state)
            self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
            self.assertEqual(
                state.foundation.selected.position.scene_id, scene_id)
            # The label is the SERVER'S GUESS until the client reports from
            # there (CORE-REQUEST-GM-051 item 3).
            self.assertTrue(state.scene_label_is_server_guess)
            # KA1A-ROOTCAUSE: shipping the relabel without this block is what
            # left every later scene of a session with no census, no roster
            # and every field-mob ActionVital refused.
            self.assertIn(
                "lane_a_m2_transport_census_latch_cleared_%d" % scene_id,
                state.events,
            )
            self.assertFalse(state.world_census_sent)
            self.assertFalse(state.world_census_refused)
            self.assertFalse(state.npc_idle_action_sent)
            self.assertFalse(state.world_census_identity_resolved)
            self.assertIsNone(state.population_refresh_anchor)
            # Bumped, never reset: an old generation for a scene visited
            # earlier this session must not be replayable as current.
            self.assertGreater(
                state.mob_combat_announced_membership_generation,
                generation_before)
            self.assertIsNone(state.last_target_pos)
            self.assertIsNone(state.population_indices)
            self.assertIsNone(state.world_census_indices)
            self.assertIsNone(state.census_anchor_record)
            self.assertIsNone(state.world_census_actor_count)
            self.assertIsNone(state.mob_combat_announced_membership)

    def test_x_y_z_are_left_at_the_departure_row(self):
        # SCENE ONLY.  The coordinates in the relocation record are the frame
        # this server SENT, and a frame that left the server is a request.
        # Copying them here would also make the first real report compare
        # EQUAL to the stored row and skip the durable write entirely.
        scene_id = self._destination_scene()
        with self._registry_open_at_login_on(scene_id):
            before = self._login_and_start("m2xyzbefore")
            origin = before.foundation.selected.position
            state, _ = self._journey("m2xyz")
            after = state.foundation.selected.position
            self.assertEqual(
                (after.x, after.y, after.z, after.heading),
                (origin.x, origin.y, origin.z, origin.heading),
            )

    def test_the_durable_row_names_the_destination_after_one_step(self):
        # LAYER 2 (wire/DB), and this is the half PANYA 1218 item 2 is about:
        # once the pins are open, a journey plus one step leaves a row that
        # brings the character back to the sea rather than to Port Royal.
        scene_id = self._destination_scene()
        with self._registry_open_at_login_on(scene_id):
            state, _ = self._journey("m2durableopen")
            destination = tc.marker_destination(MARKER)
            self._report(state, float(destination.x) + 40.0,
                         float(destination.y) + 40.0, float(destination.z))
            row = self.store.list_characters(
                state.foundation.account_id)[-1]
            self.assertEqual(row.position.scene_id, scene_id)
            self.assertTrue(
                warp_scene_persist.login_would_accept(row.position.scene_id))

    def test_an_ordinary_marker_relabels_today_with_no_bent_registry(self):
        """WHAT THIS SEAM ACTUALLY DOES ON THE SHIPPED REGISTRY.

        pf-adversary R401 D2, MEASURED: `marker_destination` pins 15 markers
        and `login_would_accept` answers True for scenes 1-11 and 14 today,
        so the relabel is live for the ORDINARY in-game markers and dormant
        only for the three decreed sea rows.  The first draft of this class
        drove nothing but 17/343/345, which let a mutant that restricted the
        relabel to those three scenes survive the whole suite.  This case is
        the one that fails it.
        """
        marker_id = 2
        scene_id = self._destination_scene(marker_id)
        self.assertNotEqual(scene_id, 1, "this marker must leave scene 1")
        self.assertTrue(warp_scene_persist.login_would_accept(scene_id))
        state, actions = self._journey("m2ordinary", marker_id=marker_id)
        self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
        self.assertEqual(state.foundation.selected.position.scene_id, scene_id)
        self.assertIn(
            "lane_a_m2_transport_selected_scene_resynced_%d" % scene_id,
            state.events)

    def test_a_scene_whose_row_may_not_be_written_is_refused(self):
        """FENCE 2, and it is a different question from fence 1.

        pf-adversary R401 D4, MEASURED on marker 14: scene 14 is
        `login_entry_allowed=True` and `persist_position_allowed=False`, so
        the login fence alone let the label move while `lifecycle.checkpoint`
        declined the write.  The in-memory label then diverged from the
        durable row for the life of the session and the resync event fired
        green over a feature that had not happened.  PANYA-DECISION 1218
        item 2 asks for the DURABLE ROW to name where the player is, which a
        scene like this cannot deliver.
        """
        marker_id = 14
        scene_id = self._destination_scene(marker_id)
        # CORRECTED, LANE-A round ioz8fd: 1218 opened scene 14's write-back
        # pin too, so no SHIPPED row carries the login-open persist-barred
        # shape any more and this case used to read the fence off data that
        # had stopped having it.  The fence is still in the code, so the row
        # is bent shut here instead -- the edit an operator makes to the
        # JSON between two boots -- and the bend is asserted before the
        # journey runs.
        with bent_registry.process_reads(
                bent_registry.unpersisted(scene_id)) as bent:
            self.assertTrue(warp_scene_persist.login_would_accept(scene_id))
            self.assertFalse(
                world_scene_travel.is_position_persist_allowed(scene_id),
                "the fixture bent nothing: this row must be login-open and "
                "persist-barred or the case proves nothing")
            self.assertIsNotNone(bent[scene_id].spawn)
            state, actions = self._journey(
                "m2persistbarred", marker_id=marker_id)
            self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
            self.assertEqual(state.foundation.selected.position.scene_id, 1)
            self.assertFalse(
                getattr(state, "scene_label_is_server_guess", False))
            self.assertIn(
                "lane_a_m2_transport_resync_refused_persist_barred_%d"
                % scene_id,
                state.events)

    def test_a_same_scene_journey_clears_nothing(self):
        """The early return, pinned - a mutant deleting it survived the suite.

        Marker 1 resolves to the scene a fresh character already stands in.
        Unlatching the census and bumping the membership generation there
        would cost a re-announce for a journey that moved nobody.
        """
        state = self._login_and_start("m2samescene")
        state.world_census_sent = True
        state.last_target_pos = (1.0, 2.0, 3.0)
        generation_before = state.mob_combat_announced_membership_generation
        self._record(state, marker_id=1)
        self._tick(state)
        self._echo(state, marker_id=1)
        self.assertEqual(state.foundation.selected.position.scene_id, 1)
        self.assertTrue(state.world_census_sent)
        self.assertEqual(state.last_target_pos, (1.0, 2.0, 3.0))
        self.assertEqual(
            state.mob_combat_announced_membership_generation,
            generation_before)
        self.assertFalse(getattr(state, "scene_label_is_server_guess", False))
        self.assertIn("lane_a_m2_transport_resync_same_scene_1", state.events)

    def test_a_selected_row_with_no_position_is_declined_not_crashed(self):
        """The guard against a shape nobody has produced, pinned anyway.

        A mutant deleting it survived the suite, which means the guard was
        prose.  `replace()` on a row with no `position` is an AttributeError
        inside the window where an escape costs the listener thread, so the
        guard is cheap and the pin is cheaper than finding out.

        CALLED DIRECTLY, not through a journey, and that is a real limit of
        this pin rather than a convenience: a session whose `selected` row
        has no position does not survive the rest of the echo path either
        (measured: the AttributeError comes back out of a neighbouring
        reader), so a dispatch-level version of this case would be testing
        those readers, not this guard.  What is pinned here is that THIS
        method declines by name instead of raising into the window where a
        raise costs the listener thread.
        """
        state = self._login_and_start("m2noposition")
        selected = state.foundation.selected
        state.foundation.selected = types.SimpleNamespace(
            id=getattr(selected, "id", None), position=None)
        before = len(state.events)
        state._m2_transport_resync_selected_scene(tc.open_check(MARKER))
        events = state.events[before:]
        self.assertIn("lane_a_m2_transport_resync_refused_no_position", events)
        self.assertNotIn("lane_a_m2_transport_resync_refused_raised", events)

    def test_a_relabel_that_raises_costs_the_relabel_and_nothing_else(self):
        """NEVER RAISES, measured rather than asserted in a docstring.

        pf-adversary R401 D5: only the relocation read was inside the try, and
        the call sits between `sink.answered.add(...)` and the return that
        hands out the transport frame - so an escape killed the listener
        thread AND the journey, since the order is already popped.
        """
        state = self._login_and_start("m2resyncraises")
        self._record(state)
        self._tick(state)
        with mock.patch.object(
            warp_scene_persist, "login_would_accept",
            side_effect=RuntimeError("registry object died"),
        ):
            actions = self._echo(state)
        # The frame still leaves.
        self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
        self.assertIn("lane_a_m2_transport_resync_refused_raised",
                      state.events)
        # And nothing was half-applied.
        self.assertEqual(state.foundation.selected.position.scene_id, 1)
        self.assertFalse(getattr(state, "scene_label_is_server_guess", False))

    def test_the_durable_row_never_names_a_scene_the_login_refuses(self):
        # THE INVARIANT THAT OUTRANKS THE RELABEL, asserted against whichever
        # registry this run actually has.  This is the assertion the naive G1
        # fix broke: with an unfenced relabel the row read back here was
        # Position(scene_id=126, ...) and the next login answered StartGame
        # with an empty action list and world_scene_entry_refused_no_reply.
        state, _ = self._journey("m2durablelogin")
        destination = tc.marker_destination(MARKER)
        self._report(state, float(destination.x) + 40.0,
                     float(destination.y) + 40.0, float(destination.z))
        row = self.store.list_characters(state.foundation.account_id)[-1]
        self.assertTrue(
            warp_scene_persist.login_would_accept(row.position.scene_id),
            "this seam persisted scene %r, which the next login refuses -- "
            "the character can no longer log in at all"
            % (row.position.scene_id,),
        )

    def test_the_character_can_still_log_in_after_a_journey(self):
        # The same fact read from the other end, because the row is only the
        # mechanism: what matters is that StartGame still answers.
        state, _ = self._journey("m2reloginafter")
        destination = tc.marker_destination(MARKER)
        self._report(state, float(destination.x) + 40.0,
                     float(destination.y) + 40.0, float(destination.z))
        character = self.store.list_characters(
            state.foundation.account_id)[-1]
        again = self._login_and_start("m2reloginafter2")
        with contextlib.redirect_stderr(io.StringIO()):
            with contextlib.redirect_stdout(io.StringIO()):
                actions = again.dispatch(self.legacy.parse_outer(
                    self.legacy._synthetic_start_game_pc(character.selector)
                ))
        self.assertNotIn("world_scene_entry_refused_no_reply", again.events)
        self.assertIsNotNone(actions)

class SurvivingMutantTests(_SeamCase):
    """The five mutants R398 measured surviving the suite at 41 passed."""

    def _v141_saw_this_frame(self, state, before):
        """v141's own unconditional capture events since `before`.

        Same read `ReplayDebtTests` uses, and for the same reason its
        docstring gives: v141 appends these for EVERY decodable frame of this
        class that reaches it, so they are the only direct answer to "did the
        frame fall through".  An assertion on transport actions cannot see
        it -- these synthetic bytes are not v141's exact V136 confirm PC, so
        they buy no probe even when they do fall through.
        """
        return len([
            e for e in state.events[before:]
            if str(e).startswith("v131_teleport_check_")
            or str(e).startswith("v136_marker1_positive_confirm_capture")
        ])

    def test_a_failed_transport_encoder_still_owns_the_frame(self):
        # MUTANT (a): `return []` -> `return None` after the encoder raised.
        # Every assertion in the file survived it, INCLUDING a first attempt
        # of this test that read v141's `teleport_check_echo_capture_count`
        # -- that counter only moves for v141's own exact scene-1 challenge
        # echo, which these bytes are not, so it read 0 either way and
        # measured nothing.
        #
        # WHAT THE MUTANT COSTS: `None` is the fall-through signal, so a
        # journey this seam REFUSED (the bytes never existed, the order is
        # already popped, `answered` was never written) is handed to the
        # frozen v141 route as if this seam had no opinion.  On the one echo
        # v141 does recognise -- the exact V136 marker-1 confirm -- that
        # route pays a V137 transport built from scene-1 constants, so the
        # player travels on a frame this seam's console line says was never
        # sent.  The kill is ownership, measured directly.
        state = self._login_and_start("m2mutantreturn")
        self._record(state)
        self._tick(state)
        original = tc.encode_transport

        def boom(_legacy, _pending):
            raise OverflowError("float too large to pack with f format")

        tc.encode_transport = boom
        before = len(state.events)
        try:
            actions = self._echo(state)
        finally:
            tc.encode_transport = original
        self.assertEqual(actions, [])
        self.assertEqual(self._v141_saw_this_frame(state, before), 0)

    def test_two_orders_for_one_marker_buy_two_journeys(self):
        # MUTANT (b): the memo gate moved ABOVE `resolve_echo` refuses the
        # second echo of a pair this seam has answered -- even when a second
        # legitimate order for the same marker is sitting recorded.  A player
        # asked twice to sail to the same island could then never accept the
        # second invitation.  The memo may only speak when nothing is
        # recorded.
        state = self._login_and_start("m2mutantmemo")
        self._record(state)
        self._tick(state)
        first = self._of(self._echo(state), TRANSPORT_ACTION)
        self._record(state)
        self._tick(state)
        second = self._of(self._echo(state), TRANSPORT_ACTION)
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)

    def test_the_failed_transport_says_so_on_the_console(self):
        # MUTANT (c): F3's own console line was captured by nothing, so
        # deleting the `_teleport_check_say` call cost no test -- and the
        # attended round reads this seam off the bridge console.
        state = self._login_and_start("m2mutantconsole")
        self._record(state)
        self._tick(state)
        original = tc.encode_transport

        def boom(_legacy, _pending):
            raise OverflowError("float too large to pack with f format")

        tc.encode_transport = boom
        captured = io.StringIO()
        try:
            with contextlib.redirect_stdout(captured):
                self._echo(state)
        finally:
            tc.encode_transport = original
        self.assertIn("ECHO_REFUSED_TRANSPORT_ENCODER_RAISED",
                      captured.getvalue())

    def test_an_unauthenticated_connection_is_noted_once(self):
        # MUTANT (d): the no-selected event grew one row per frame on a
        # connection that has proved nothing -- the same shape F7 measured
        # and capped on the post-ack path.
        state = self._login_only("m2mutantnoselonce")
        state.teleport_check_sink().record(1, tc.open_check(MARKER))
        for _ in range(5):
            self._tick(state)
        self.assertEqual(
            len([e for e in state.events
                 if e == "lane_a_m2_teleport_check_no_selected_no_prompt"]), 1)

    def test_an_empty_queue_notes_nothing_at_all(self):
        # MUTANT (e): `if not sink.unsent: return` could be deleted free.
        # It is observable exactly here -- a connection with nothing queued
        # must not be described by this seam at all.
        state = self._login_only("m2mutantemptyqueue")
        for _ in range(3):
            self._tick(state)
        self.assertFalse([e for e in state.events
                          if e.startswith("lane_a_m2_teleport_check")])


class M2ArrivalAnswersTheGuessTests(_JourneyFixture):
    """The flag a journey sets can be cleared again, and only by the client.

    pf-adversary on pirate-force-server#1132 found D3 (CRITICAL) and it is
    what kept that PR draft: `_m2_transport_resync_inner` sets
    `scene_label_is_server_guess`, and until this round the only two sites
    that ever cleared it were login and the `gm_warp_confirm_window_open`
    branch of `_checkpoint_exact_target`.  An M2 journey opens no GM confirm
    window, so a travelling session could never clear it and
    `client_confirmed_scene` stayed None for the rest of its life -- measured
    against a control that did not travel and read the departure scene.

    THE EVIDENCE THAT ENDS THE REFUSAL is the same evidence
    `GM_WARP_POSITION_CONFIRMED` rests on: the client reports coordinates
    within `WARP_TARGET_MATCH_TOLERANCE` of the point the transport frame
    sent it to.  NONCLAIM, stated in `_m2_note_arrival_if_confirmed` and
    repeated here because a reader of these test names would otherwise
    over-read them: the SCENE half of that comparison is a tautology (the
    relabel already put the destination in `candidate.scene_id`), so what is
    tested is x/y/z, and nobody has watched a client draw the arrival --
    that is `GT-309` rhythm (c), which is HELD.
    """

    ORDINARY_MARKER = 2

    def _arrived_journey(self, token, marker_id=None):
        """A journey whose relabel actually happened, plus its destination."""
        marker_id = self.ORDINARY_MARKER if marker_id is None else marker_id
        destination = tc.marker_destination(marker_id)
        self.assertTrue(
            warp_scene_persist.login_would_accept(destination.scene_id),
            "this marker must relabel on the shipped registry or the "
            "arrival path is never armed and the test proves nothing",
        )
        state, actions = self._journey(token, marker_id=marker_id)
        self.assertEqual(len(self._of(actions, TRANSPORT_ACTION)), 1)
        self.assertTrue(state.scene_label_is_server_guess)
        self.assertIn(
            "lane_a_m2_arrival_armed_scene_%d" % destination.scene_id,
            state.events)
        return state, destination

    def _report_at(self, state, destination, offset=0.0):
        return self._report(
            state, float(destination.x) + offset,
            float(destination.y), float(destination.z),
        )

    def _say(self, state, destination, offset=0.0):
        """One position report with stdout captured, returned as text."""
        out = io.StringIO()
        with contextlib.redirect_stderr(io.StringIO()):
            with contextlib.redirect_stdout(out):
                state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
                    float(destination.x) + offset, float(destination.y),
                    float(destination.z),
                )))
        return out.getvalue()

    # ------------------------------------------------------------------
    # the hole itself

    def test_a_report_from_the_destination_clears_the_guess(self):
        state, destination = self._arrived_journey("m2arrive")
        self._report_at(state, destination)
        self.assertFalse(
            state.scene_label_is_server_guess,
            "the client reported from the point the transport frame named, "
            "which is the whole evidence this flag was waiting for",
        )
        self.assertEqual(state.client_confirmed_scene, destination.scene_id)
        self.assertIn(
            "lane_a_m2_arrival_confirmed_scene_%d" % destination.scene_id,
            state.events)
        self.assertIn(
            "client_confirmed_scene_%d_m2_arrival_report" % destination.scene_id,
            state.events)

    def test_the_control_that_did_not_travel_is_unaffected(self):
        """The measurement D3 was stated against, kept as a test.

        A session that never travels reads its scene back on the first
        ordinary report, through the branch that has always been there.  If
        this ever goes red with the case above green, the arrival path has
        started answering for journeys that did not happen.
        """
        state = self._login_and_start("m2control")
        destination = tc.marker_destination(self.ORDINARY_MARKER)
        self.assertFalse(state.scene_label_is_server_guess)
        self._report_at(state, destination)
        self.assertEqual(state.client_confirmed_scene, 1)
        self.assertNotIn("lane_a_m2_arrival_armed_scene_%d"
                         % destination.scene_id, state.events)

    def test_a_report_somewhere_else_confirms_nothing(self):
        state, destination = self._arrived_journey("m2elsewhere")
        self._report_at(state, destination, offset=4000.0)
        self.assertTrue(
            state.scene_label_is_server_guess,
            "a report 4000 units from the destination is not an arrival",
        )
        self.assertIsNone(state.client_confirmed_scene)
        self.assertIn("lane_a_m2_arrival_not_at_target_4000", state.events)

    def test_a_late_arrival_still_confirms(self):
        """WHY THE EXPECTATION IS NOT CONSUMED ON THE FIRST REPORT.

        LANE-GM's parked warp target consumes once because RE-129 measured
        the client IGNORING ForcePos, so its second report is about a frame
        the warp never caused.  The M2 transport is the other composer, and
        the cost of being wrong here is asymmetric: an expectation consumed
        one frame early leaves the flag stuck for the session, which is D3
        again.  This is the case that fails a consume-once mutant.
        """
        state, destination = self._arrived_journey("m2late")
        self._report_at(state, destination, offset=4000.0)
        self.assertTrue(state.scene_label_is_server_guess)
        self._report_at(state, destination)
        self.assertFalse(state.scene_label_is_server_guess)
        self.assertEqual(state.client_confirmed_scene, destination.scene_id)

    def test_a_refused_relabel_arms_nothing(self):
        """No relabel, no guess, and so nothing for an arrival to answer.

        Under a login-barred destination the seam declines, the label stays
        the client's own departure scene, and the ordinary report path -- not
        this one -- records it.  An expectation armed on this branch would be
        an arrival for a journey the server itself refused to believe in.
        """
        scene_id = self._destination_scene()
        with self._registry_barred_at_login_on(scene_id):
            state, _ = self._journey("m2barred")
            destination = tc.marker_destination(MARKER)
            self.assertFalse(state.scene_label_is_server_guess)
            self._report_at(state, destination)
        self.assertNotIn("lane_a_m2_arrival_armed_scene_%d" % scene_id,
                         state.events)
        self.assertNotIn("lane_a_m2_arrival_confirmed_scene_%d" % scene_id,
                         state.events)
        self.assertEqual(state.client_confirmed_scene, 1)

    # ------------------------------------------------------------------
    # who the expectation belongs to, and what it refuses

    def test_another_character_cannot_answer_this_journey(self):
        state, destination = self._arrived_journey("m2othercharacter")
        parked = state._m2_arrival_expected
        state._m2_arrival_expected = replace(
            parked, character_id=parked.character_id + 1)
        self._report_at(state, destination)
        self.assertTrue(state.scene_label_is_server_guess)
        self.assertIsNone(state.client_confirmed_scene)
        self.assertIn("lane_a_m2_arrival_refused_character_mismatch",
                      state.events)
        self.assertIsNotNone(
            state._m2_arrival_expected,
            "a re-selectable character keeps the journey parked; only an "
            "answer or a newer journey takes it away",
        )

    def test_an_unreadable_character_is_never_compared(self):
        state, destination = self._arrived_journey("m2unreadable")
        parked = state._m2_arrival_expected
        state._m2_arrival_expected = replace(
            parked, character_id=UNREADABLE_CHARACTER_ID)
        self._report_at(state, destination)
        self.assertTrue(state.scene_label_is_server_guess)
        self.assertIn("lane_a_m2_arrival_refused_character_mismatch",
                      state.events)

    def test_a_foreign_value_on_the_slot_is_dropped_not_read(self):
        state, destination = self._arrived_journey("m2foreign")
        state._m2_arrival_expected = object()
        self._report_at(state, destination)
        self.assertIsNone(state._m2_arrival_expected)
        self.assertIn("lane_a_m2_arrival_dropped_foreign_value", state.events)
        self.assertTrue(state.scene_label_is_server_guess)

    def test_an_expectation_is_dropped_once_the_label_is_not_a_guess(self):
        state, destination = self._arrived_journey("m2notaguess")
        state.scene_label_is_server_guess = False
        self._report_at(state, destination, offset=4000.0)
        self.assertIsNone(state._m2_arrival_expected)
        self.assertIn("lane_a_m2_arrival_dropped_label_not_a_guess",
                      state.events)

    def test_a_second_journey_replaces_the_first_destination(self):
        state, first = self._arrived_journey("m2twice")
        second_marker = 3
        second = tc.marker_destination(second_marker)
        self.assertNotEqual(second.scene_id, first.scene_id)
        self.assertTrue(warp_scene_persist.login_would_accept(second.scene_id))
        self._record(state, marker_id=second_marker)
        self._tick(state)
        self._echo(state, marker_id=second_marker)
        self.assertEqual(state._m2_arrival_expected.target.scene_id,
                         second.scene_id)
        self._report_at(state, first)
        self.assertTrue(
            state.scene_label_is_server_guess,
            "the older destination can no longer be what a report is about",
        )
        self._report_at(state, second)
        self.assertEqual(state.client_confirmed_scene, second.scene_id)

    # ------------------------------------------------------------------
    # never raises, never floods

    def test_a_position_whose_axis_raises_costs_the_comparison_only(self):
        """v141 wraps `dispatch()` with no `except`; nothing here may escape."""
        state, _destination = self._arrived_journey("m2raises")

        class _Raising:
            scene_id = state._m2_arrival_expected.target.scene_id

            @property
            def x(self):
                raise RuntimeError("axis")

        self.assertEqual(
            state._m2_note_arrival_if_confirmed(_Raising()), "unknown")
        self.assertTrue(state.scene_label_is_server_guess)

    def test_a_destination_that_is_not_numbers_arms_nothing(self):
        """`transport_relocation` reads `pending.destination` raw.

        A hand-built PendingCheck can therefore carry coordinates that are
        not numbers at all.  The relabel above it still stands -- its own
        fences passed on the scene id -- but the arrival path must say it
        cannot be answered rather than park something it will only ever
        compare as "unknown".
        """
        state, destination = self._arrived_journey("m2badxyz")
        bent = tc.PendingCheck(
            marker_id=destination.marker_id,
            destination=destination._replace(x="not a number"),
            window_expected=True,
            confirm_id=tc.CONFIRM_ID_DOCKING,
        )
        relocation = tc.transport_relocation(bent)
        state._m2_arrival_arm(bent, relocation,
                              state.foundation.selected.position)
        self.assertIsNone(state._m2_arrival_expected)
        self.assertIn("lane_a_m2_arrival_not_armed_destination_unreadable",
                      state.events)

    def test_a_non_finite_destination_arms_nothing(self):
        state, destination = self._arrived_journey("m2infxyz")
        bent = tc.PendingCheck(
            marker_id=destination.marker_id,
            destination=destination._replace(x=float("inf")),
            window_expected=True,
            confirm_id=tc.CONFIRM_ID_DOCKING,
        )
        state._m2_arrival_arm(bent, tc.transport_relocation(bent),
                              state.foundation.selected.position)
        self.assertIsNone(state._m2_arrival_expected)
        self.assertIn("lane_a_m2_arrival_not_armed_destination_not_finite",
                      state.events)

    def test_the_console_says_the_arrival_once_and_the_confirmation_once(self):
        state, destination = self._arrived_journey("m2console")
        first = self._say(state, destination, offset=4000.0)
        self.assertIn("ARRIVAL", first)
        self.assertIn("confirmed=0", first)
        self.assertIn("dist=4000.000", first)
        second = self._say(state, destination, offset=3000.0)
        self.assertNotIn(
            "ARRIVAL", second,
            "one line per journey on the unconfirmed branch: every ordinary "
            "walk frame would otherwise bury the confirmation",
        )
        third = self._say(state, destination)
        self.assertIn("ARRIVAL", third)
        self.assertIn("confirmed=1", third)
        self.assertIn("scene=%d" % destination.scene_id, third)

    def test_an_unconfirmed_journey_costs_one_event_not_one_per_step(self):
        """The events list may not grow for as long as the player walks.

        Found in this round's own self-review, not by a test that was already
        there: the first draft printed the console line once but appended an
        event on EVERY report, so a session that travelled and then walked for
        an hour grew `self.events` without bound.  That is the leak
        `lane_hooks.fire()`'s per-session ceiling exists to stop (R393).
        """
        state, destination = self._arrived_journey("m2eventonce")
        for step in range(5):
            self._report_at(state, destination, offset=4000.0 + step)
        misses = [e for e in state.events
                  if e.startswith("lane_a_m2_arrival_not_at_target_")]
        self.assertEqual(
            len(misses), 1,
            "one event per journey, not one per step: %r" % misses)
        self.assertTrue(state.scene_label_is_server_guess)
        # ... and the journey is still answerable after all that walking.
        self._report_at(state, destination)
        self.assertEqual(state.client_confirmed_scene, destination.scene_id)

    def test_the_console_line_carries_the_marker_the_journey_used(self):
        state, destination = self._arrived_journey("m2markerline")
        line = self._say(state, destination)
        self.assertIn("marker=%d" % self.ORDINARY_MARKER, line)
        self.assertTrue(line.startswith(tc.TOKEN),
                        "one prefix for the whole journey: %r" % line)


class ArrivalFindingsPaidTests(_JourneyFixture):
    """The three pf-adversary findings this round's own first draft earned.

    D1 and D3 are defects the draft introduced; D2 is the laundering path the
    draft's disclosed tautology turned from annotated into load-bearing.  Each
    case below is the adversary's own measured sequence, kept as a test so the
    fix cannot be undone by a later edit that looks harmless.
    """

    ORDINARY_MARKER = 2

    class _MarkerIdThatRaises:
        """A `marker_id` that raises something `_m2_arrival_arm` does not guard.

        `int()` on it raises RuntimeError, which is outside the
        OverflowError/TypeError/ValueError the arm catches - the exact input
        the adversary drove through the public recorder door.
        """

        def __int__(self):
            raise RuntimeError("marker id")

        def __eq__(self, other):
            return other == 2

        def __hash__(self):
            return hash(2)

    def test_an_arm_that_raises_costs_the_answer_and_not_the_census(self):
        """D1: the census unlatch must not depend on the arm surviving."""
        state = self._login_and_start("m2armraises")
        destination = tc.marker_destination(self.ORDINARY_MARKER)
        pending = tc.PendingCheck(
            marker_id=self._MarkerIdThatRaises(),
            destination=destination,
            window_expected=True,
            confirm_id=tc.CONFIRM_ID_DOCKING,
        )
        state.world_census_sent = True
        with contextlib.redirect_stdout(io.StringIO()):
            state._m2_transport_resync_selected_scene(pending)
        self.assertEqual(state.foundation.selected.position.scene_id,
                         destination.scene_id, "the relabel still happened")
        self.assertFalse(
            state.world_census_sent,
            "the KA1A-ROOTCAUSE block must run whatever the arm did: a scene "
            "relabelled with the census still latched dispatches a teleport "
            "frame and nothing else for the rest of the session (R399)",
        )
        self.assertIn(
            "lane_a_m2_transport_census_latch_cleared_%d" % destination.scene_id,
            state.events)
        self.assertNotIn(
            "lane_a_m2_transport_resync_refused_raised", state.events,
            "an arm that raises may not escape into the caller's blanket "
            "except at all: the console line the operator reads is built "
            "after it",
        )
        self.assertIn("lane_a_m2_arrival_not_armed_raised", state.events)
        self.assertIsNone(state._m2_arrival_expected)

    def test_turning_on_the_spot_is_not_an_arrival(self):
        """D2: the confirmation needs displacement, not only coordinates.

        The adversary's own sequence, and it needs no hostile input at all:
        `marker_destination(N)` is bit-identical to scene N's registry spawn,
        the relabel deliberately leaves x/y/z on the departure row, and
        `Position` carries `heading` - so a client that reports the marker's
        coordinates BEFORE echoing and then turns on the spot reached the
        arrival check with `dist=0.000` and confirmed a transport it never
        processed.
        """
        state = self._login_and_start("m2turnonspot")
        destination = tc.marker_destination(self.ORDINARY_MARKER)
        # The client is standing on the destination's coordinates already,
        # in the DEPARTURE scene.
        self._report(state, float(destination.x), float(destination.y),
                     float(destination.z))
        self._record(state, marker_id=self.ORDINARY_MARKER)
        self._tick(state)
        self._echo(state, marker_id=self.ORDINARY_MARKER)
        self.assertTrue(state.scene_label_is_server_guess)
        # ... and now it only turns: same point, different heading.
        with contextlib.redirect_stderr(io.StringIO()):
            with contextlib.redirect_stdout(io.StringIO()):
                state.dispatch(self.legacy.parse_outer(self._target_pos_pc(
                    float(destination.x), float(destination.y),
                    float(destination.z), heading=1.5,
                )))
        self.assertTrue(
            state.scene_label_is_server_guess,
            "zero displacement is not evidence that a transport moved anyone",
        )
        self.assertEqual(
            state.client_confirmed_scene, 1,
            "the field still names the last scene the client really backed, "
            "which is the departure scene it reported from before echoing",
        )
        self.assertIn("lane_a_m2_arrival_refused_no_displacement", state.events)

    def test_the_gm_confirm_window_owns_its_own_frame(self):
        """D3: a parked journey may not take the credit for a GM warp.

        Measured by the adversary end to end: journey armed, client misses,
        the expectation stays parked (by design), a GM `/warp` then lands the
        client on the destination's spawn - which IS the marker point - and
        this seam printed `confirmed=1` for a journey that delivered nothing,
        then swallowed the GM path's own `warp_confirmed` event because
        `_note_client_confirmed_scene` returns early on an unchanged value.
        """
        state, destination = self._journey("m2gmwindow",
                                           marker_id=self.ORDINARY_MARKER), None
        state = state[0]
        destination = tc.marker_destination(self.ORDINARY_MARKER)
        self.assertTrue(state.scene_label_is_server_guess)
        parked = state._m2_arrival_expected
        state.gm_warp_confirm_window_open = True
        position = state.foundation.selected.position
        candidate = Position(
            position.scene_id, position.scene_seq,
            float(destination.x), float(destination.y), float(destination.z),
            0.0,
        )
        with contextlib.redirect_stdout(io.StringIO()):
            verdict = state._m2_note_arrival_if_confirmed(candidate)
        self.assertEqual(verdict, "none")
        self.assertTrue(state.scene_label_is_server_guess)
        self.assertIsNone(state.client_confirmed_scene)
        self.assertIn("lane_a_m2_arrival_yielded_to_gm_confirm", state.events)
        self.assertIs(
            state._m2_arrival_expected, parked,
            "a journey does not expire because a GM warped in the middle of it",
        )
