"""The sixth UI vital a player presses that the server answers.

A `Community_SendMailVital` (`0x6E12`) sent from the shipped client UI
comes back out of the real `state.dispatch()` as a frame.  Before this
round five of the eight `_FRIEND_MAIL_PARTY_TRADE_DISPATCH` vitals were
answered (party invite, trade invite, party command, friend request,
friend removal); this one was among the three that got `[]`.

WHY ANSWERING WITH THIS ID IS AN ANSWER AND NOT A GUESS.  RE-312
RESULT-1 (pf_bridge/notes_to_chief/20260908_1038_RE-312-RESULT-*.md)
lists `0x6E12 Community_SendMailVital INBOUND_YES
handler=0x00645BF0 next=0x0063F9B0`, and RESULT-2 pins the caller at
`0x005F38B2` inside the batch dispatch loop, so the slot is reached by
the ordinary receive path -- the same evidence shape the five answered
ids beside this one already carry.

What the client DRAWS is not decided here.  That is a GT ticket's job,
on a screen: `observed_frames = 0` for this class as for the other
seven.
"""
from __future__ import annotations

import contextlib
import io
import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import field_mobs  # noqa: E402
from pirateforce_foundation import ui_dispatch  # noqa: E402
from pirateforce_foundation import ui_mail_wire as wire  # noqa: E402
from pirateforce_foundation import ui_party_wire as party_wire  # noqa: E402
from pirateforce_foundation import ui_social_wire as social_wire  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_mail_send_answer as answerer_module,
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

MAIL_ID = wire.COMMUNITY_SEND_MAIL_VITAL_ID

# THE REAL REGISTRATIONS, CAPTURED AS `lane_hooks._discover()` MADE THEM
# -- same reason as every answerer test file beside this one: registering
# from a TEST module puts this module on the gating stack, and the gate
# correctly refuses a module `_discover()` never imported, which would
# read as the answerer not working.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(MAIL_ID)
_REAL_INVITE_ENTRY = ui_dispatch._ANSWERERS.get(
    party_wire.PARTY_INVITE_VITAL_ID
)


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


def _real_mail_payload(
    subject: str = "Ahoy", body: str = "Meet at the dock",
) -> bytes:
    """A send-mail frame in ui_mail_wire's pinned shape."""
    return wire.encode_send_mail_payload(
        wire.SendMailFields(
            field1_u64=0x1122334455667788,
            field2_wstring="Ann",
            field3_u64=0x99AABBCCDDEEFF00,
            field4_wstring=subject,
            field5_wstring=body,
            field6_wstring="",
            field7_wstring="",
            field8_wstring="",
            field9_u8=1,
        )
    )


def _real_invite_payload() -> bytes:
    return party_wire.encode_party_invite_payload(
        party_wire.PartyInviteFields(
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
            ui_dispatch._ANSWERERS[MAIL_ID] = _REAL_ENTRY
        if _REAL_INVITE_ENTRY is not None:
            ui_dispatch._ANSWERERS[party_wire.PARTY_INVITE_VITAL_ID] = (
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
            out = answerer_module.answer_send_mail(**kwargs)
        return out, stderr.getvalue()

    def test_a_wrong_id_is_refused(self):
        out, said = self._call(
            vital_id=party_wire.PARTY_INVITE_VITAL_ID,
            payload=_real_mail_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", said)

    def test_a_payload_that_is_not_bytes_is_refused(self):
        for bad in ("not bytes", bytearray(_real_mail_payload()), None):
            out, said = self._call(vital_id=MAIL_ID, payload=bad)
            self.assertEqual(out, [])
            self.assertIn("reason=payload_not_bytes", said)

    def test_an_undecodable_payload_is_refused(self):
        out, said = self._call(vital_id=MAIL_ID, payload=b"\x00\x01\x99")
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", said)

    def test_a_payload_with_a_trailer_is_refused_as_UNDECODABLE(self):
        out, said = self._call(
            vital_id=MAIL_ID, payload=_real_mail_payload() + b"\xAA",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", said)

    def test_the_round_trip_guard_refuses_when_it_IS_reached(self):
        # The scan below proves the real decoder never reaches this
        # branch.  It still cannot be deleted or inverted under a green
        # suite, because this test makes the encoder disagree and then
        # demands the refusal.
        payload = _real_mail_payload()
        real_encode = wire.encode_send_mail_payload
        try:
            wire.encode_send_mail_payload = (
                lambda fields: real_encode(fields) + b"\x00"
            )
            out, said = self._call(vital_id=MAIL_ID, payload=payload)
        finally:
            wire.encode_send_mail_payload = real_encode
        self.assertEqual(out, [])
        self.assertIn("reason=not_byte_exact", said)

    def test_a_label_with_no_reviewed_shape_is_refused_not_skipped(self):
        saved = answerer_module.LABEL
        try:
            answerer_module.LABEL = "UI_NO_SUCH_REVIEWED_LABEL"
            out, said = self._call(
                vital_id=MAIL_ID, payload=_real_mail_payload(),
            )
        finally:
            answerer_module.LABEL = saved
        self.assertEqual(out, [])
        self.assertIn("reason=no_reviewed_outbound_shape", said)

    def test_a_payload_over_the_reviewed_ceiling_is_refused(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        # Six wstring fields, each long enough to push the payload past
        # the reviewed ceiling.  Built from the encoder, so it stays
        # right if the row or the field list moves.
        long_field = "A" * (shape.max_payload_bytes // 4)
        payload = _real_mail_payload(subject=long_field, body=long_field)
        self.assertGreater(len(payload), shape.max_payload_bytes)
        out, said = self._call(vital_id=MAIL_ID, payload=payload)
        self.assertEqual(out, [])
        self.assertIn("reason=over_reviewed_budget", said)

    def test_this_module_keeps_no_allowance_of_its_own(self):
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 5):
            out, _ = self._call(
                vital_id=MAIL_ID, payload=_real_mail_payload(),
            )
            self.assertEqual(len(out), 1)

    def test_the_reply_is_the_players_own_bytes(self):
        payload = _real_mail_payload("Ship's log", "All quiet")
        out, said = self._call(vital_id=MAIL_ID, payload=payload)
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertEqual(reply.payload, payload)
        self.assertEqual(reply.vital_id, MAIL_ID)
        self.assertEqual(
            reply.version, wire.COMMUNITY_SEND_MAIL_VITAL_VERSION,
        )
        self.assertEqual(reply.label, answerer_module.LABEL)
        self.assertIn("UI_SEND_MAIL_ACCEPTED len=", said)


class TheRoundTripHoldsAcrossAllNineFieldsTests(unittest.TestCase):
    """This class's own composition, fuzzed -- not the single-field scan.

    `read_wstring_tag` (every wstring field here goes through it) wraps
    the same `read_untagged_wstring` that
    `test_lane_ui_friend_request_answer.py` already scanned exhaustively
    and found injective (every two-byte code unit, plus 200,000 random
    four-byte names, zero non-identical re-encodes).  That primitive is
    not re-scanned per field here -- six independent calls to an
    already-proven function is not six new facts.  What IS new, and what
    this class's own module docstring claims without measuring it
    directly, is that COMPOSING nine fields (one u64, five wstrings, one
    more u64, one u8) round-trips as a whole, including cases where
    several wstring fields are non-empty and different lengths at once.
    """

    def test_random_well_formed_frames_reencode_identically(self):
        rnd = random.Random(6812)
        decoded = 0
        for _ in range(2000):
            length = rnd.choice((0, 1, 3, 7, 40))
            fields = wire.SendMailFields(
                field1_u64=rnd.getrandbits(64),
                field2_wstring="A" * rnd.choice((0, 1, 5)),
                field3_u64=rnd.getrandbits(64),
                field4_wstring="B" * length,
                field5_wstring="C" * rnd.choice((0, 2, 9)),
                field6_wstring="D" * rnd.choice((0, 1)),
                field7_wstring="",
                field8_wstring="E" * rnd.choice((0, 3)),
                field9_u8=rnd.getrandbits(8),
            )
            payload = wire.encode_send_mail_payload(fields)
            decoded_fields = wire.decode_send_mail_payload(payload)
            self.assertIsNotNone(decoded_fields)
            decoded += 1
            self.assertEqual(
                wire.encode_send_mail_payload(decoded_fields), payload,
            )
        self.assertEqual(decoded, 2000)

    def test_a_lone_surrogate_in_any_wstring_field_is_refused_not_mangled(self):
        # An even-length, in-bounds UTF-16LE payload the codec still
        # rejects for the SECOND wstring field (field4) -- proving the
        # guard applies past the first field, not only to it.
        payload = (
            social_wire.u64tag(wire._TAG_U64, 1)
            + social_wire.wstring_tag("Ann")
            + social_wire.u64tag(wire._TAG_U64, 2)
            + bytes([0x48]) + struct.pack("<I", 2) + b"\x00\xD8"
        )
        fields = wire.decode_send_mail_payload(payload)
        self.assertIsNone(fields)


class TheReviewedRowsTests(unittest.TestCase):
    """The two rows this round added to ui_dispatch, checked as rows."""

    def test_the_owner_row_names_this_module_and_only_this_module(self):
        self.assertEqual(
            ui_dispatch._ANSWERER_OWNERS[MAIL_ID], answerer_module.__name__,
        )
        owners = [
            vid for vid, mod in ui_dispatch._ANSWERER_OWNERS.items()
            if mod == answerer_module.__name__
        ]
        self.assertEqual(owners, [MAIL_ID])

    def test_the_outbound_row_names_this_id_and_a_bound_it_can_meet(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, MAIL_ID)
        self.assertIn(
            wire.COMMUNITY_SEND_MAIL_VITAL_VERSION, shape.versions,
        )
        # The row is a CEILING, not a width: an all-empty mail and one
        # with real text in two fields must both fit under it.
        self.assertLess(len(_real_mail_payload("", "")), shape.max_payload_bytes)
        self.assertLess(
            len(_real_mail_payload("A" * 20, "B" * 60)),
            shape.max_payload_bytes,
        )

    def test_this_id_was_answerable_before_anybody_wrote_an_answerer(self):
        self.assertIn(MAIL_ID, ui_dispatch.ANSWERABLE_VITAL_IDS)

    def test_the_arming_names_this_module_declares_are_usable(self):
        self.assertEqual(
            answerer_module.ARMING_TOKEN, "UI_SEND_MAIL_ANSWER_ARMED",
        )
        answerer_module.ARMING_TOKEN.encode("ascii")
        vital_id, version, payload = answerer_module.arming_sample()
        self.assertEqual(vital_id, MAIL_ID)
        self.assertEqual(
            version, wire.COMMUNITY_SEND_MAIL_VITAL_VERSION,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            out = answerer_module.answer_send_mail(
                vital_id=vital_id, payload=payload,
            )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].payload, payload)

    def test_the_adopt_side_contract_names_are_declared(self):
        self.assertEqual(answerer_module.ANSWERS_VITAL_ID, MAIL_ID)
        self.assertIs(answerer_module.ANSWERS_WITH, answerer_module.answer_send_mail)


class TheOwnerRowDecidesWhoMayTakeThisIdTests(unittest.TestCase):
    """A row exists for 0x6E12 now, and it names one module."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)

    def _lane_module(self, stem, source):
        import types

        qualified = "%s.%s" % (lane_hooks.__name__, stem)
        module = types.ModuleType(qualified)
        module.__file__ = "<%s>" % (stem,)
        module.production_allowed = True
        sys.modules[qualified] = module
        self.addCleanup(sys.modules.pop, qualified, None)
        lane_hooks._PRODUCTION_ALLOWED[qualified] = True
        self.addCleanup(lane_hooks._PRODUCTION_ALLOWED.pop, qualified, None)
        exec(compile(source, "<%s>" % (stem,), "exec"), module.__dict__)
        return module

    TAKER = (
        "from pirateforce_foundation import ui_dispatch\n"
        "def answerer(session=None, vital_id=None, payload=None):\n"
        "    return [('UI_SEND_MAIL_ANSWERED', b'\\xff',"
        " b'\\xff\\xff', 0.0)]\n"
        "def install(vital_id):\n"
        "    return ui_dispatch.register_answerer(vital_id, answerer)\n"
    )

    def test_a_lane_module_that_is_not_the_owner_is_refused(self):
        ui_dispatch.clear_answerers()
        thief = self._lane_module("lane_ui_aaa_mail_thief", self.TAKER)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(thief.install(MAIL_ID))
        self.assertIn("reason=not_the_reviewed_owner", stderr.getvalue())
        self.assertIsNone(ui_dispatch.registered_answerer(MAIL_ID))

    def test_the_reviewed_owner_is_the_module_that_shipped_the_answerer(self):
        self.assertIsNotNone(_REAL_ENTRY, "the answerer must be registered")
        self.assertEqual(
            _REAL_ENTRY[0], ui_dispatch._ANSWERER_OWNERS[MAIL_ID],
        )


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
        said = io.StringIO()
        with contextlib.redirect_stderr(said):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, payload)
            ))
        return actions, said.getvalue()

    def test_the_send_mail_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-mail-send-answer")
        payload = _real_mail_payload()
        actions, _ = self._press(state, MAIL_ID, payload)
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, _delay = actions[0]
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(MAIL_ID,
              wire.COMMUNITY_SEND_MAIL_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_the_report_only_watcher_on_this_id_still_prints(self):
        state = self._login_and_start("ui-mail-send-watcher")
        actions, said = self._press(state, MAIL_ID, _real_mail_payload())
        self.assertEqual(len(actions), 1)
        self.assertIn("LANE_UI_MAIL_SEND decoded", said)
        self.assertIn("UI_SEND_MAIL_ACCEPTED len=", said)

    def test_mails_of_different_lengths_are_each_answered_as_sent(self):
        state = self._login_and_start("ui-mail-send-widths")
        for subject, body in (("", ""), ("Ahoy", ""), ("A" * 40, "B" * 40)):
            payload = _real_mail_payload(subject, body)
            actions, _ = self._press(state, MAIL_ID, payload)
            self.assertEqual(len(actions), 1, (subject, body))
            _, _, frame, _ = actions[0]
            self.assertEqual(
                frame,
                self.legacy.make_runtime_vitals(
                    [(MAIL_ID,
                      wire.COMMUNITY_SEND_MAIL_VITAL_VERSION, payload)]
                )[1],
            )

    def test_a_malformed_request_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-mail-send-junk")
        actions, _ = self._press(state, MAIL_ID, b"\x00\x01\x99")
        self.assertEqual(actions, [])
        actions, _ = self._press(
            state, MAIL_ID, _real_mail_payload() + b"\xAA",
        )
        self.assertEqual(actions, [])

    def test_a_peer_that_never_logged_in_gets_nothing(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("ui-mail-send-nobody")
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, MAIL_ID, _real_mail_payload())
            ))
        self.assertEqual(actions, [])

    def test_a_storm_on_this_button_does_not_silence_the_invite_button(self):
        state = self._login_and_start("ui-mail-send-storm")
        answered = 0
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 8):
            actions, _ = self._press(state, MAIL_ID, _real_mail_payload())
            answered += len(actions)
        self.assertEqual(answered, ui_dispatch.SESSION_ANSWER_BUDGET)
        actions, _ = self._press(
            state, party_wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
        )
        self.assertEqual(len(actions), 1)

    def test_another_session_is_not_charged_for_this_ones_storm(self):
        first = self._login_and_start("ui-mail-send-storm-a")
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 1):
            self._press(first, MAIL_ID, _real_mail_payload())
        second = self._login_and_start("ui-mail-send-storm-b")
        actions, _ = self._press(second, MAIL_ID, _real_mail_payload())
        self.assertEqual(len(actions), 1)

    def test_the_answer_carries_the_reviewed_outbound_shape(self):
        state = self._login_and_start("ui-mail-send-shape")
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, MAIL_ID)
        actions, _ = self._press(state, MAIL_ID, _real_mail_payload())
        self.assertEqual(len(actions), 1)
        self.assertLessEqual(len(actions[0][2]), shape.max_frame_bytes)

    def test_the_invite_button_still_answers_with_the_new_row_in_place(self):
        state = self._login_and_start("ui-mail-send-neighbour")
        actions, _ = self._press(
            state, party_wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], invite_module.LABEL)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
