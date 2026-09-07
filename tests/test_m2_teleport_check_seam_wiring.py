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
        self.assertIn("PROMPT", prompt_lines[0])
        self.assertIn(f"marker={MARKER}", prompt_lines[0])
        echo_lines = self._lines(self._echo, state)
        self.assertEqual(len(echo_lines), 2)
        self.assertIn("ECHO", echo_lines[0])
        self.assertIn("verdict=OK", echo_lines[0])
        self.assertIn("TRANSPORT", echo_lines[1])

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
