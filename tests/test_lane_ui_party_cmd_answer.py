"""The third UI vital a player presses that the server answers.

A `PartyCmdVital` (`0x2466`) sent from the shipped client UI comes back
out of the real `state.dispatch()` as a frame.  Before this round two of
the eight `_FRIEND_MAIL_PARTY_TRADE_DISPATCH` vitals were answered (the
party invite and the trade invite); this one was among the six that got
`[]`.

WHY ANSWERING WITH THIS ID IS AN ANSWER AND NOT A GUESS.  RE-312
RESULT-1 (pf_bridge/notes_to_chief/20260908_1038_RE-312-RESULT-*.md)
lists `0x2466 PartyCmdVital INBOUND_YES handler=0x0062EA70` -- the same
handler VA, in the same `"PartyModule_Client"`, as the party invite this
lane already answers -- and RESULT-2 pins the caller at `0x005F38B2`
inside the batch dispatch loop, so the slot is reached by the ordinary
receive path.

THE ONE THING THIS CLASS HAS THAT THE OTHER TWO DO NOT is a payload that
cannot vary: `u8 + u64`, no string.  So the reviewed outbound shape pins
the EXACT width and the answerer requires equality rather than a
ceiling, and the tests below measure the property that pin rests on
instead of asserting it.

What the client DRAWS is not decided here.  That is a GT ticket's job,
on a screen: `observed_frames = 0` for this class as for the other seven.
"""
from __future__ import annotations

import contextlib
import io
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import ui_dispatch  # noqa: E402
from pirateforce_foundation import ui_party_wire as wire  # noqa: E402
from pirateforce_foundation import ui_social_wire as social_wire  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_party_cmd_answer as answerer_module,
    lane_ui_party_invite_answer as invite_module,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# THE REAL REGISTRATIONS, CAPTURED AS `lane_hooks._discover()` MADE THEM
# -- same reason as the two answerer test files beside this one:
# registering from a TEST module puts this module on the gating stack,
# and the gate correctly refuses a module `_discover()` never imported,
# which would read as the answerer not working.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(wire.PARTY_CMD_VITAL_ID)
_REAL_INVITE_ENTRY = ui_dispatch._ANSWERERS.get(wire.PARTY_INVITE_VITAL_ID)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """The same outer envelope every sibling dispatch test builds."""
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


def _real_cmd_payload() -> bytes:
    """A party command in ui_party_wire's pinned shape."""
    return wire.encode_party_cmd_payload(
        wire.PartyCmdFields(field1_u8=1, field2_u64=0x1122334455667788)
    )


def _real_invite_payload() -> bytes:
    return wire.encode_party_invite_payload(
        wire.PartyInviteFields(
            field1_u8=1, field2_u64=0x1122334455667788,
            field3_wstring="Panya",
        )
    )


class _AnswererRegistered(unittest.TestCase):
    """Register the real answerers, and put the registry back."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)
        ui_dispatch.reset_session_budgets_for_tests()
        self.addCleanup(ui_dispatch.reset_session_budgets_for_tests)
        ui_dispatch.clear_answerers()
        if _REAL_ENTRY is not None:
            ui_dispatch._ANSWERERS[wire.PARTY_CMD_VITAL_ID] = _REAL_ENTRY
        if _REAL_INVITE_ENTRY is not None:
            ui_dispatch._ANSWERERS[wire.PARTY_INVITE_VITAL_ID] = (
                _REAL_INVITE_ENTRY
            )

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)


class RefusalTests(_AnswererRegistered):
    """Every way this answerer can be wrong ends in an empty list."""

    def _call(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = answerer_module.answer_party_cmd(**kwargs)
        return out, stderr.getvalue()

    def test_a_wrong_id_is_refused(self):
        out, console = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=_real_cmd_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", console)

    def test_a_payload_that_is_not_bytes_is_refused(self):
        for bad in (bytearray(_real_cmd_payload()), "x", memoryview(b"")):
            with self.subTest(kind=type(bad).__name__):
                out, console = self._call(
                    vital_id=wire.PARTY_CMD_VITAL_ID, payload=bad,
                )
                self.assertEqual(out, [])
                self.assertIn("reason=payload_not_bytes", console)

    def test_an_undecodable_payload_is_refused(self):
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=b"\x00\x01\x99",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_a_payload_with_a_trailer_is_refused_as_UNDECODABLE(self):
        """Named for the refusal it actually gets, not the one it looks
        like (the lesson of pf-adversary round xqxadg, D5).

        `decode_party_cmd_payload` calls `require_exhausted`, so one
        unexplained trailing byte dies one step BEFORE the round-trip
        comparison and two steps before the fixed-width check.  Each of
        those three guards is measured on its own below.
        """
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID,
            payload=_real_cmd_payload() + b"\x77",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_no_decodable_payload_reaches_the_round_trip_refusal(self):
        """The round-trip guard is dead code today, measured not claimed.

        4,000 structurally valid payloads; every one that decodes
        re-encodes byte for byte.  A decoder that ever loosens turns
        this red, which is the moment the guard stops being dead code.
        """
        rng = random.Random(20260908)
        decoded = 0
        for _ in range(4000):
            payload = (
                bytes([wire._TAG_FIELD1_U8, rng.getrandbits(8)])
                + social_wire.u64tag(
                    wire._TAG_FIELD2_U64, rng.getrandbits(64)
                )
            )
            fields = wire.decode_party_cmd_payload(payload)
            if fields is None:
                continue
            decoded += 1
            self.assertEqual(
                wire.encode_party_cmd_payload(fields), payload,
            )
        self.assertGreater(decoded, 1000, "the sample decoded too little")

    def test_the_round_trip_guard_refuses_when_it_IS_reached(self):
        """The guard is exercised, so deleting it cannot stay green.

        The encoder is made to disagree with the decoder by a byte that
        does NOT change the length -- otherwise the fixed-width check
        below could be the thing that catches it, and this test would be
        measuring the wrong guard.
        """
        payload = _real_cmd_payload()
        real = wire.encode_party_cmd_payload

        def one_bit_off(fields):
            out = bytearray(real(fields))
            out[-1] ^= 0xFF
            return bytes(out)

        wire.encode_party_cmd_payload = one_bit_off
        self.addCleanup(
            setattr, wire, "encode_party_cmd_payload", real,
        )
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=payload,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=not_byte_exact", console)
        self.assertIn(
            "in=%d out=%d" % (len(payload), len(payload)), console,
        )

    def test_a_label_with_no_reviewed_shape_is_refused_not_skipped(self):
        # pf-adversary D-F, inherited by construction: a renamed registry
        # key must be a refusal here, not a check that quietly does not
        # apply and dies later inside ui_dispatch._compose.
        saved = ui_dispatch._OUTBOUND_FRAME_SHAPES.pop(
            answerer_module.LABEL
        )
        self.addCleanup(
            ui_dispatch._OUTBOUND_FRAME_SHAPES.__setitem__,
            answerer_module.LABEL, saved,
        )
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=_real_cmd_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=no_reviewed_outbound_shape", console)

    def test_this_module_keeps_no_allowance_of_its_own(self):
        # pf-adversary D-B: a per-module counter is a storm guard bought
        # at the price of one player silencing every other player.
        self.assertFalse(hasattr(answerer_module, "ANSWER_BUDGET"))
        self.assertFalse(hasattr(answerer_module, "_answers_sent"))
        self.assertFalse(hasattr(answerer_module, "reset_budget_for_tests"))

    def test_the_reply_is_the_players_own_bytes(self):
        payload = _real_cmd_payload()
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=payload,
        )
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertIsInstance(reply, ui_dispatch.VitalReply)
        self.assertEqual(reply.payload, payload)
        self.assertEqual(reply.vital_id, wire.PARTY_CMD_VITAL_ID)
        self.assertEqual(reply.version, wire.PARTY_CMD_VITAL_VERSION)
        self.assertEqual(reply.label, answerer_module.LABEL)
        # THE DELAY IS A NUMBER SOMEBODY SLEEPS ON (pf-adversary round
        # m54yxh, D8).  `current/pf_login_game_server_v141.py` sleeps
        # `delay` in the CONNECTION THREAD before sending, and neither
        # `_actions_are_well_formed` nor the outbound shape bounds it --
        # so an edit here setting 30.0 stalls one player's socket for
        # half a minute per press under a fully green suite.  Nothing
        # else pinned it; this does.
        self.assertEqual(reply.delay, 0.0)
        # And the accept token is evidence an attended round reads off
        # the console, so deleting it must not be free either.
        self.assertIn("UI_PARTY_CMD_ANSWER len=11", console)


class TheWidthIsFixedAndCheckedAsFixedTests(_AnswererRegistered):
    """The pin that makes this class different from the other two.

    `max_payload_bytes` is not headroom here, it is the width, and the
    answerer requires EQUALITY.  A ceiling nothing approaches is a check
    that never fires; these tests measure that the width really cannot
    vary, that the reviewed number is the encoder's own, and that the
    equality check fires in BOTH directions -- which a `>` test would
    only manage in one.
    """

    def _call(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = answerer_module.answer_party_cmd(**kwargs)
        return out, stderr.getvalue()

    def test_every_field_value_encodes_to_the_same_width(self):
        rng = random.Random(24660908)
        widths = {
            len(wire.encode_party_cmd_payload(
                wire.PartyCmdFields(field1_u8=a, field2_u64=b)
            ))
            for a in (0, 1, 0x7F, 0x80, 0xFF)
            for b in (0, 1, (1 << 63), (1 << 64) - 1)
        }
        for _ in range(4000):
            widths.add(len(wire.encode_party_cmd_payload(
                wire.PartyCmdFields(
                    field1_u8=rng.getrandbits(8),
                    field2_u64=rng.getrandbits(64),
                )
            )))
        self.assertEqual(
            widths, {11},
            "PartyCmdVital's payload is u8 + u64 with no string; if this"
            " set ever holds more than one width the equality check in"
            " the answerer is the wrong shape of check",
        )

    def test_the_reviewed_number_is_the_encoders_own_width(self):
        # The literal in ui_dispatch is the REVIEW, and a review that
        # reads the value it reviews pins nothing -- so the comparison
        # is made here, between two numbers that were written down
        # independently.
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.max_payload_bytes, 11)
        self.assertEqual(
            shape.max_payload_bytes,
            len(wire.encode_party_cmd_payload(
                wire.PartyCmdFields(field1_u8=0, field2_u64=0)
            )),
        )
        self.assertEqual(
            shape.max_payload_bytes,
            answerer_module._PARTY_CMD_PAYLOAD_BYTES,
        )

    def test_a_reencoding_that_is_too_LONG_is_refused(self):
        payload = _real_cmd_payload()
        real = wire.encode_party_cmd_payload
        wire.encode_party_cmd_payload = lambda f: real(f) + b"\x00"
        self.addCleanup(setattr, wire, "encode_party_cmd_payload", real)
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=payload,
        )
        self.assertEqual(out, [])
        # It fails the round trip first -- which is correct and is the
        # point: the width check is the SECOND wall, not the only one.
        self.assertIn("reason=not_byte_exact", console)

    def test_a_reencoding_that_is_too_SHORT_is_refused_by_the_width_check(self):
        """The half a `>` ceiling would let through.

        The encoder is replaced by one that returns the player's own
        bytes minus the last byte, and the decoder by one that accepts
        the short form -- so the round trip AGREES and only the width
        check can refuse.  Under `len(...) > budget` this passes and a
        10-byte frame goes out under a label reviewed for 11.
        """
        short = _real_cmd_payload()[:-1]
        real_encode = wire.encode_party_cmd_payload
        real_decode = wire.decode_party_cmd_payload
        wire.encode_party_cmd_payload = lambda f: short
        wire.decode_party_cmd_payload = lambda p: wire.PartyCmdFields(0, 0)
        self.addCleanup(
            setattr, wire, "encode_party_cmd_payload", real_encode,
        )
        self.addCleanup(
            setattr, wire, "decode_party_cmd_payload", real_decode,
        )
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=short,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=not_the_reviewed_fixed_width", console)
        self.assertIn(
            "len=%d encoder=11 reviewed=11" % (len(short),), console,
        )

    def test_the_encoders_own_width_is_on_the_path_not_just_in_a_test(self):
        """pf-adversary round m54yxh, D7 -- the constant used to be dead.

        The guard compared the payload against the REGISTRY only, so
        ``_PARTY_CMD_PAYLOAD_BYTES`` -- the number derived from the
        encoder, whose comment claimed the module and the wire module
        "cannot disagree" -- could be set to anything at all and the
        button kept working.  It is now one of the two numbers the
        payload has to match, so a module that disagrees with its own
        wire module answers nothing.
        """
        saved = answerer_module._PARTY_CMD_PAYLOAD_BYTES
        answerer_module._PARTY_CMD_PAYLOAD_BYTES = 999
        self.addCleanup(
            setattr, answerer_module, "_PARTY_CMD_PAYLOAD_BYTES", saved,
        )
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=_real_cmd_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=not_the_reviewed_fixed_width", console)
        self.assertIn("encoder=999", console)

    def test_a_width_the_registry_disagrees_with_is_refused(self):
        """The other direction: the registry moves, the encoder does not.

        This is the drift the equality check exists to catch -- somebody
        widening the reviewed row without a wire change, or a wire change
        landing without the row being re-reviewed.
        """
        saved = ui_dispatch._OUTBOUND_FRAME_SHAPES[answerer_module.LABEL]
        ui_dispatch._OUTBOUND_FRAME_SHAPES[answerer_module.LABEL] = (
            saved._replace(max_payload_bytes=12)
        )
        self.addCleanup(
            ui_dispatch._OUTBOUND_FRAME_SHAPES.__setitem__,
            answerer_module.LABEL, saved,
        )
        out, console = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=_real_cmd_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=not_the_reviewed_fixed_width", console)


class TheProcessCeilingIsPerVitalTests(unittest.TestCase):
    """pf-adversary round m54yxh, D1 -- the third answerer used to cost
    the two shipped ones a third of the pot they share.

    `SESSION_ANSWER_BUDGET` is per (session, vital), and the storm test
    below proves it.  The ceiling ABOVE it was one integer for the whole
    process, shared by every session AND every vital, so adding an
    answerable vital raised what one player could draw from the shared
    pot (measured: 64 -> 96) and lowered the number of sessions needed
    to empty it (64 -> 43); after that a bystander who had pressed
    nothing got nothing back until a restart.  The ceiling is per vital
    id now, so a new button cannot spend an old one's allowance.

    Driven against `_charge_session_answer` with a small ceiling rather
    than through `state.dispatch()` 4,096 times: the property is about
    the counter's KEY, and a test that takes four minutes to say so is a
    test the next round deletes.
    """

    def setUp(self):
        self._keep = []
        ui_dispatch.reset_session_budgets_for_tests()
        self.addCleanup(ui_dispatch.reset_session_budgets_for_tests)
        self._saved_budget = ui_dispatch.PROCESS_ANSWER_BUDGET
        ui_dispatch.PROCESS_ANSWER_BUDGET = 4
        self.addCleanup(
            setattr, ui_dispatch, "PROCESS_ANSWER_BUDGET",
            self._saved_budget,
        )

    class _Session:
        """A weak-referenceable stand-in.  A bare `object()` is not, and
        the seam refuses a session it cannot key (`session_budget_
        unbounded`) -- which would make every case below pass for the
        wrong reason."""

    def _session(self):
        session = self._Session()
        self._keep.append(session)   # the seam holds only a weak ref
        return session

    def _spend(self, vital_id, count):
        """Spend `count` answers for `vital_id`, one session each, so the
        per-SESSION allowance is never what refuses."""
        return [
            ui_dispatch._charge_session_answer(self._session(), vital_id, 1)
            for _ in range(count)
        ]

    def test_emptying_one_vitals_pot_leaves_another_vitals_pot_full(self):
        spent = self._spend(wire.PARTY_CMD_VITAL_ID, 5)
        self.assertEqual(spent[:4], ["", "", "", ""])
        self.assertEqual(spent[4], "process_budget_spent")
        # The party invite button, on a session that has pressed nothing.
        self.assertEqual(
            ui_dispatch._charge_session_answer(
                self._session(), wire.PARTY_INVITE_VITAL_ID, 1,
            ),
            "",
        )

    def test_the_counter_is_keyed_by_vital_and_not_by_session(self):
        self._spend(wire.PARTY_CMD_VITAL_ID, 2)
        self._spend(wire.PARTY_INVITE_VITAL_ID, 1)
        self.assertEqual(
            ui_dispatch._PROCESS_ANSWERS_SENT,
            {wire.PARTY_CMD_VITAL_ID: 2, wire.PARTY_INVITE_VITAL_ID: 1},
        )

    def test_the_ceiling_still_bounds_a_client_that_reconnects(self):
        # The property the process ceiling exists for (pf-adversary round
        # vy1m79, D2) is not weakened by keying it per vital: fresh
        # sessions on ONE vital still run out.
        self.assertIn(
            "process_budget_spent",
            self._spend(wire.PARTY_CMD_VITAL_ID, 6),
        )

    def test_the_shipped_number_is_still_the_reviewed_one(self):
        self.assertEqual(self._saved_budget, 4096)


class TheReviewedRowsTests(unittest.TestCase):
    """The two rows in ui_dispatch that let this button answer at all."""

    def test_the_owner_row_names_this_module_and_only_this_module(self):
        self.assertEqual(
            ui_dispatch._ANSWERER_OWNERS[wire.PARTY_CMD_VITAL_ID],
            answerer_module.__name__,
        )
        # And it did not disturb the two rows that were already there.
        self.assertEqual(
            ui_dispatch._ANSWERER_OWNERS[wire.PARTY_INVITE_VITAL_ID],
            invite_module.__name__,
        )

    def test_the_outbound_row_names_this_id_and_a_frame_bound_it_can_meet(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, wire.PARTY_CMD_VITAL_ID)
        self.assertEqual(shape.versions, frozenset((0,)))
        self.assertEqual(shape.max_frame_bytes, 64)
        # 43 measured on this commit; the bound is the envelope's room,
        # not this lane's, so it is checked against a frame the project
        # builds rather than against itself.
        legacy = _legacy()
        _pc, frame = legacy.make_runtime_vitals(
            [(wire.PARTY_CMD_VITAL_ID, wire.PARTY_CMD_VITAL_VERSION,
              _real_cmd_payload())]
        )
        self.assertEqual(len(frame), 43)
        self.assertLessEqual(len(frame), shape.max_frame_bytes)

    def test_this_id_was_answerable_before_anybody_wrote_an_answerer(self):
        # The row did not widen the seam: 0x2466 has been one of the
        # eight ids runtime.py routes here all along -- what was missing
        # was somebody to answer it.
        self.assertIn(
            wire.PARTY_CMD_VITAL_ID, ui_dispatch.ANSWERABLE_VITAL_IDS,
        )

    def test_the_version_this_lane_sends_is_the_one_the_row_reviewed(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIn(wire.PARTY_CMD_VITAL_VERSION, shape.versions)


class EndToEndThroughTheRealDispatcherTests(_AnswererRegistered):
    """A button press comes back as bytes, through state.dispatch()."""

    def setUp(self):
        super().setUp()
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
        state.dispatch(
            self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC)
        )
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def _press(self, state, vital_id, payload):
        with contextlib.redirect_stderr(io.StringIO()):
            return state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, payload)
            ))

    def test_the_party_command_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-party-cmd-answer")
        payload = _real_cmd_payload()
        actions = self._press(state, wire.PARTY_CMD_VITAL_ID, payload)
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, _delay = actions[0]
        # SECOND LAYER, BUILT WITHOUT THE DISPATCHER.
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(wire.PARTY_CMD_VITAL_ID,
              wire.PARTY_CMD_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_a_malformed_command_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-party-cmd-junk")
        self.assertEqual(
            self._press(state, wire.PARTY_CMD_VITAL_ID, b"\x00\x01\x99"), [],
        )
        self.assertEqual(
            self._press(
                state, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload() + b"\xAA",
            ),
            [],
        )

    def test_a_peer_that_never_logged_in_gets_nothing(self):
        # pf-adversary D7 (round 1gc6hl) applies to every answerer on
        # this seam, and a new one is exactly where that could be
        # forgotten: the gate is the seam's, so this button inherits it,
        # and this test is what proves the inheritance is real.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("ui-party-cmd-nobody")
        self.assertEqual(
            self._press(state, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload()),
            [],
        )

    def test_a_storm_on_this_button_does_not_silence_the_invite_button(self):
        """The property the allowance is keyed on, measured on the new id.

        pf-adversary round vy1m79, D1 measured this failing the other way
        round when the allowance was keyed on the session alone.  A third
        answerer sharing the seam is the moment that could regress, so it
        is measured here rather than argued from the key's shape.
        """
        state = self._login_and_start("ui-party-cmd-storm")
        answered = 0
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 8):
            answered += len(
                self._press(
                    state, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload(),
                )
            )
        self.assertEqual(answered, ui_dispatch.SESSION_ANSWER_BUDGET)
        # ... and the invite button of the SAME session still answers.
        self.assertEqual(
            len(self._press(
                state, wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
            )),
            1,
        )

    def test_another_session_is_not_charged_for_this_ones_storm(self):
        first = self._login_and_start("ui-party-cmd-storm-a")
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 1):
            self._press(first, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload())
        second = self._login_and_start("ui-party-cmd-storm-b")
        self.assertEqual(
            len(self._press(
                second, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload(),
            )),
            1,
        )

    def test_the_answer_carries_the_reviewed_outbound_shape(self):
        # The frame leaves only because ui_dispatch's outbound registry
        # names this label for this id.  Proving it HERE, on the real
        # dispatcher, is what stops the registry from being a table that
        # is true in its own unit test and bypassed on the live path.
        state = self._login_and_start("ui-party-cmd-shape")
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, wire.PARTY_CMD_VITAL_ID)
        actions = self._press(
            state, wire.PARTY_CMD_VITAL_ID, _real_cmd_payload(),
        )
        self.assertEqual(len(actions), 1)
        self.assertLessEqual(len(actions[0][2]), shape.max_frame_bytes)

    def test_the_invite_button_still_answers_with_the_new_row_in_place(self):
        # A third row must not change the two answers that already
        # shipped -- measured, not assumed, on the real dispatcher.
        state = self._login_and_start("ui-party-cmd-neighbour")
        actions = self._press(
            state, wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], invite_module.LABEL)


class TheOwnerRowDecidesWhoMayTakeThisIdTests(unittest.TestCase):
    """A lane that is not the reviewed owner cannot take 0x2466."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)

    def _lane_module(self, stem, source):
        """A module `_discover()` would import, built the way
        `tests/test_ui_dispatch.py::TheReviewedOwnerTakesTheIdTests`
        builds one -- registering from THIS file would not exercise the
        rule at all, because the seam judges the module on the
        registration stack and a test module is not a lane.
        """
        import types

        qualified = "%s.%s" % (lane_hooks.__name__, stem)
        module = types.ModuleType(qualified)
        module.__file__ = "<%s>" % (stem,)
        module.production_allowed = True
        sys.modules[qualified] = module
        self.addCleanup(sys.modules.pop, qualified, None)
        lane_hooks._PRODUCTION_ALLOWED[qualified] = True
        self.addCleanup(
            lane_hooks._PRODUCTION_ALLOWED.pop, qualified, None,
        )
        exec(compile(source, "<%s>" % (stem,), "exec"), module.__dict__)
        return module

    TAKER = (
        "from pirateforce_foundation import ui_dispatch\n"
        "def answerer(session=None, vital_id=None, payload=None):\n"
        "    return [('UI_PARTY_CMD_ANSWERED', b'\\xff',"
        " b'\\xff\\xff', 0.0)]\n"
        "def install(vital_id):\n"
        "    return ui_dispatch.register_answerer(vital_id, answerer)\n"
    )

    def test_a_lane_module_that_is_not_the_owner_is_refused(self):
        """The attack from pf-adversary round xqxadg D9, on the new id.

        Alphabetically first, flag on, id free -- and it still loses,
        because `_ANSWERER_OWNERS` now names one module per id and this
        round added the row for `0x2466` in the same commit as the
        answerer.  Without that row the thief would win: an id with no
        row cannot be taken by anybody, and an id whose row names
        somebody else cannot be taken by this one.
        """
        ui_dispatch.clear_answerers()
        thief = self._lane_module("lane_ui_aaa_cmd_thief", self.TAKER)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(thief.install(wire.PARTY_CMD_VITAL_ID))
        self.assertIn("reason=not_the_reviewed_owner", stderr.getvalue())
        self.assertIsNone(
            ui_dispatch.registered_answerer(wire.PARTY_CMD_VITAL_ID)
        )

    def test_the_reviewed_owner_is_the_module_that_shipped_the_answerer(self):
        # The row is only worth having if it names the module a player's
        # bytes actually come from, so this reads the shipped
        # registration rather than the table it is being checked against.
        self.assertIsNotNone(_REAL_ENTRY, "the answerer must be registered")
        self.assertEqual(
            _REAL_ENTRY[0],
            ui_dispatch._ANSWERER_OWNERS[wire.PARTY_CMD_VITAL_ID],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
