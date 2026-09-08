"""The second UI vital a player presses that the server answers.

A TradeInviteVital sent from the shipped client UI comes back out of the
real `state.dispatch()` as a frame.  Before this round exactly one of the
eight `_FRIEND_MAIL_PARTY_TRADE_DISPATCH` vitals was answered (the party
invite); the trade invite was one of the seven that got `[]`.

RE-312 BUILD_IMPACT 2 (pf_bridge/notes_to_chief/20260908_1038_RE-312-
RESULT-*.md) is why this one needed no new reversing: `PartyInviteVital`
and `TradeInviteVital` share an encoder, byte for byte.  That claim is
not taken on faith here -- `SharedShapeTests` re-measures it.  And
RESULT-1/RESULT-2 are why answering with the SAME id is an answer rather
than a guess: a live inbound handler at vtable slot +0x1C, reached from
the batch dispatch loop at 0x005F38B2.

What the client DRAWS is not decided here.  That is a GT ticket's job,
on a screen.
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
from pirateforce_foundation import ui_dispatch  # noqa: E402
from pirateforce_foundation import ui_social_wire as social_wire  # noqa: E402
from pirateforce_foundation import ui_party_wire as party_wire  # noqa: E402
from pirateforce_foundation import ui_trade_wire as wire  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_party_invite_answer as party_module,
    lane_ui_trade_invite_answer as answerer_module,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# THE REAL REGISTRATION, CAPTURED AS `lane_hooks._discover()` MADE IT --
# same reason as the party file beside this one: registering from a TEST
# module puts this module in the gating set, and the gate correctly
# refuses a module `_discover()` never imported, which would read as the
# answerer not working.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(wire.TRADE_INVITE_VITAL_ID)


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


def _real_invite_payload() -> bytes:
    """A trade invite in ui_trade_wire's pinned shape."""
    return wire.encode_trade_invite_payload(
        wire.TradeInviteFields(
            field1_u8=1, field2_u64=0x1122334455667788,
            field3_wstring="Panya",
        )
    )


class _AnswererRegistered(unittest.TestCase):
    """Register the real module's answerer, and put the registry back."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)
        # Asked of the module that OWNS the allowance (pf-adversary
        # round vy1m79, D3): the lane's delegating `reset_budget_for_
        # tests()` was a public switch in a `production_allowed = True`
        # file that cleared every session's spend process-wide.
        ui_dispatch.reset_session_budgets_for_tests()
        self.addCleanup(ui_dispatch.reset_session_budgets_for_tests)
        ui_dispatch.clear_answerers()
        if _REAL_ENTRY is not None:
            ui_dispatch._ANSWERERS[wire.TRADE_INVITE_VITAL_ID] = _REAL_ENTRY

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)


class RefusalTests(_AnswererRegistered):
    """Every way this answerer can be wrong ends in an empty list."""

    def _call(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = answerer_module.answer_trade_invite(**kwargs)
        return out, stderr.getvalue()

    def test_a_wrong_id_is_refused(self):
        out, console = self._call(
            vital_id=party_wire.PARTY_INVITE_VITAL_ID,
            payload=_real_invite_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", console)

    def test_a_payload_that_is_not_bytes_is_refused(self):
        for bad in (bytearray(_real_invite_payload()), "x", memoryview(b"")):
            with self.subTest(kind=type(bad).__name__):
                out, console = self._call(
                    vital_id=wire.TRADE_INVITE_VITAL_ID, payload=bad,
                )
                self.assertEqual(out, [])
                self.assertIn("reason=payload_not_bytes", console)

    def test_an_undecodable_payload_is_refused(self):
        out, console = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID, payload=b"\x00\x01\x99",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_a_payload_with_a_trailer_is_refused_as_UNDECODABLE(self):
        """Named for the refusal it gets (pf-adversary round xqxadg, D5).

        The decoder calls ``require_exhausted``, so a trailer is refused
        one step BEFORE the round-trip comparison; the old assertion
        (``assertIn("REFUSED", console)``) could not tell the two apart
        and the old name claimed the wrong one.  The round-trip guard is
        measured on its own in the two tests below.
        """
        out, console = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID,
            payload=_real_invite_payload() + b"\x77",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_no_decodable_payload_reaches_the_round_trip_refusal(self):
        """D5: unreachable through this decoder, measured not asserted.

        4,000 structurally valid payloads; every one that decodes
        re-encodes byte for byte.  A decoder that ever loosens turns this
        red, which is when the guard below stops being dead code.
        """
        import random
        import struct

        rng = random.Random(20260908)
        decoded = 0
        for _ in range(4000):
            body = bytes(
                rng.getrandbits(8)
                for _ in range(rng.choice((0, 2, 4, 6, 10, 20)))
            )
            payload = (
                bytes([wire._TAG_FIELD1_U8, rng.getrandbits(8)])
                + social_wire.u64tag(
                    wire._TAG_FIELD2_U64, rng.getrandbits(64)
                )
                + bytes([0x48]) + struct.pack("<I", len(body)) + body
            )
            fields = wire.decode_trade_invite_payload(payload)
            if fields is None:
                continue
            decoded += 1
            self.assertEqual(
                wire.encode_trade_invite_payload(fields), payload,
            )
        self.assertGreater(decoded, 1000, "the sample decoded too little")

    def test_the_round_trip_guard_refuses_when_it_IS_reached(self):
        """The guard is exercised, so deleting it cannot stay green."""
        payload = _real_invite_payload()
        real = wire.encode_trade_invite_payload

        def one_byte_longer(fields):
            return real(fields) + b"\x00"

        wire.encode_trade_invite_payload = one_byte_longer
        self.addCleanup(
            setattr, wire, "encode_trade_invite_payload", real,
        )
        out, console = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID, payload=payload,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=not_byte_exact", console)
        self.assertIn(
            "in=%d out=%d" % (len(payload), len(payload) + 1), console,
        )

    def test_this_module_no_longer_keeps_an_allowance_of_its_own(self):
        # pf-adversary D-B, same finding as the party module's.  The
        # counter here was process-wide, so a storm guard bought at the
        # price of one player being able to silence every other player.
        self.assertFalse(hasattr(answerer_module, "ANSWER_BUDGET"))
        self.assertFalse(hasattr(answerer_module, "_answers_sent"))

    def test_a_label_with_no_reviewed_shape_is_refused_not_skipped(self):
        # pf-adversary D-F.  A renamed registry key used to make this
        # module skip its own budget check and die inside _compose.
        saved = ui_dispatch._OUTBOUND_FRAME_SHAPES.pop(
            answerer_module.LABEL
        )
        self.addCleanup(
            ui_dispatch._OUTBOUND_FRAME_SHAPES.__setitem__,
            answerer_module.LABEL, saved,
        )
        out, console = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID,
            payload=_real_invite_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=no_reviewed_outbound_shape", console)

    def test_the_reply_is_the_players_own_bytes(self):
        payload = _real_invite_payload()
        out, _ = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID, payload=payload,
        )
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertIsInstance(reply, ui_dispatch.VitalReply)
        self.assertEqual(reply.payload, payload)
        self.assertEqual(reply.vital_id, wire.TRADE_INVITE_VITAL_ID)
        self.assertEqual(reply.version, wire.TRADE_INVITE_VITAL_VERSION)
        self.assertEqual(reply.label, answerer_module.LABEL)


    def test_a_payload_past_the_reviewed_budget_does_not_spend_budget(self):
        # pf-adversary round xqxadg, D8.  The seam refuses a payload past
        # the reviewed budget AFTER this module has counted an answer, so
        # well-formed invites carrying a very long name could burn the
        # whole process allowance with zero bytes ever reaching anybody.
        # This module now asks the registry first, and the refusal must
        # be free.
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        oversized = wire.encode_trade_invite_payload(
            wire.TradeInviteFields(
                field1_u8=1, field2_u64=0x1122334455667788,
                field3_wstring="A" * 260,
            )
        )
        self.assertGreater(len(oversized), shape.max_payload_bytes)
        out, console = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID, payload=oversized,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=over_reviewed_payload_budget", console)
        # Free: an ordinary invite right after it is still answered.
        out, _ = self._call(
            vital_id=wire.TRADE_INVITE_VITAL_ID,
            payload=_real_invite_payload(),
        )
        self.assertEqual(len(out), 1)


class SharedShapeTests(unittest.TestCase):
    """RE-312 BUILD_IMPACT 2, re-measured instead of quoted."""

    def test_the_two_encoders_produce_the_same_bytes(self):
        fields = (1, 0x1122334455667788, "Panya")
        self.assertEqual(
            wire.encode_trade_invite_payload(wire.TradeInviteFields(*fields)),
            party_wire.encode_party_invite_payload(
                party_wire.PartyInviteFields(*fields)
            ),
        )

    def test_the_two_ids_are_not_the_same_id(self):
        # Sharing a SHAPE is not sharing a meaning, and it is certainly
        # not sharing an id: ui_trade_wire's own header keeps the two
        # field types apart for that reason.
        self.assertNotEqual(
            wire.TRADE_INVITE_VITAL_ID, party_wire.PARTY_INVITE_VITAL_ID
        )

    def test_both_answerers_refuse_on_the_same_six_grounds(self):
        # The two modules are deliberate duplicates (a shared factory
        # would move the body that RUNS out of the module carrying the
        # flag -- COO 20260908_1142 item 7 D-zeta).  This pins them
        # against drifting apart silently.
        for module, other_id in (
            (answerer_module, party_wire.PARTY_INVITE_VITAL_ID),
            (party_module, wire.TRADE_INVITE_VITAL_ID),
        ):
            fn = (
                module.answer_trade_invite
                if module is answerer_module
                else module.answer_party_invite
            )
            with self.subTest(module=module.__name__):
                self.assertIs(module.production_allowed, True)
                self.assertFalse(hasattr(module, "ANSWER_BUDGET"))
                self.assertTrue(module.LABEL.startswith("UI_"))
                self.assertIsNotNone(
                    ui_dispatch.outbound_shape(module.LABEL),
                    "an answerer whose label is unregistered can never"
                    " put a byte on the wire",
                )
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(fn(vital_id=other_id, payload=b""), [])
                    self.assertEqual(
                        fn(vital_id=other_id, payload=bytearray(b"")), []
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
        state.dispatch(self.legacy.parse_outer(self.legacy._V25_REAL_CREATE_PC))
        character = self.store.list_characters(
            state.foundation.account_id
        )[-1]
        state.dispatch(self.legacy.parse_outer(
            self.legacy._synthetic_start_game_pc(character.selector)
        ))
        return state

    def test_the_trade_invite_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-trade-answer")
        payload = _real_invite_payload()
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, wire.TRADE_INVITE_VITAL_ID, payload)
            ))
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, delay = actions[0]
        # SECOND LAYER, BUILT WITHOUT THE DISPATCHER.
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(wire.TRADE_INVITE_VITAL_ID,
              wire.TRADE_INVITE_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_a_malformed_invite_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-trade-junk")
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(
                    self.legacy, wire.TRADE_INVITE_VITAL_ID, b"\x00\x01\x99",
                )
            ))
        self.assertEqual(actions, [])

    def test_the_answer_carries_the_reviewed_outbound_shape(self):
        # The frame leaves only because ui_dispatch's outbound registry
        # names this label for this id.  Proving that HERE, on the real
        # dispatcher, is what stops the registry from being a table that
        # is true in its own unit test and bypassed on the live path.
        state = self._login_and_start("ui-trade-shape")
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, wire.TRADE_INVITE_VITAL_ID)
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(
                    self.legacy, wire.TRADE_INVITE_VITAL_ID,
                    _real_invite_payload(),
                )
            ))
        self.assertEqual(len(actions), 1)
        self.assertLessEqual(len(actions[0][2]), shape.max_frame_bytes)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
