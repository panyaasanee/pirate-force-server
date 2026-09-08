"""The first UI vital a player presses that the server answers.

This file exists to prove ONE thing a player can feel: a PartyInviteVital
sent from the shipped client UI comes back out of the real
`state.dispatch()` as a frame, instead of the `[]` every one of the eight
`_FRIEND_MAIL_PARTY_TRADE_DISPATCH` vitals returned before this round.

The evidence is deliberately two-layer and the layers do not lean on each
other: the end-to-end class drives the REAL dispatcher and compares the
frame it gets to one built independently by `legacy.make_runtime_vitals`,
while the refusal class calls the answerer directly and pins that every
way it can be wrong ends in `[]`.

RE-312 (pf_bridge/notes_to_chief/20260908_1038_RE-312-RESULT-*.md and
20260908_1105_RE-312-RESULT-2-*.md) is why answering with the SAME vital
id is an answer and not a guess: all eight classes carry a live inbound
handler at vtable slot +0x1C, reached from the batch dispatch loop at
0x005F38B2.  What the client DRAWS is not decided here -- that is the GT
ticket's job, on a screen.
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
from pirateforce_foundation import ui_party_wire as wire  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_party_invite_answer as answerer_module,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402

LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# THE REAL REGISTRATION, CAPTURED AS `lane_hooks._discover()` MADE IT.
# Re-registering from THIS file would be a different registration: the
# seam collects every lane module on the registration stack, so a test
# that registers puts its own module in the gating set, and the gate --
# correctly -- refuses a test module, which `_discover()` never imported.
# Measured: doing that turned the end-to-end proof into
# `UI_DISPATCH_GATED ... reason=not_production_allowed`, which would have
# looked like the answerer not working.  So the entry is snapshotted and
# put back, never rebuilt.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(wire.PARTY_INVITE_VITAL_ID)


def _legacy():
    if not hasattr(_legacy, "cached"):
        _legacy.cached = load_legacy(LEGACY_PATH)
    return _legacy.cached


def _synthetic_pc(legacy, nested_id: int, payload: bytes) -> bytes:
    """The same outer envelope both sibling dispatch tests build."""
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
    """A party invite in ui_party_wire's pinned shape."""
    return wire.encode_party_invite_payload(
        wire.PartyInviteFields(
            field1_u8=1, field2_u64=0x1122334455667788,
            field3_wstring="Panya",
        )
    )


class _AnswererRegistered(unittest.TestCase):
    """Register the real module's answerer, and put the registry back.

    SAVE AND RESTORE, NOT CLEAR, for the same reason
    tests/test_ui_dispatch.py's own isolation gives: `_ANSWERERS` is
    process-global, and a file that empties it makes another file's
    proofs pass for the wrong reason.  The budget is a module global for
    the same reason and gets the same treatment.
    """

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)
        answerer_module.reset_budget_for_tests()
        self.addCleanup(answerer_module.reset_budget_for_tests)
        ui_dispatch.clear_answerers()
        if _REAL_ENTRY is not None:
            ui_dispatch._ANSWERERS[wire.PARTY_INVITE_VITAL_ID] = _REAL_ENTRY

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)


class RefusalTests(_AnswererRegistered):
    """Every way this answerer can be wrong ends in an empty list."""

    def _call(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = answerer_module.answer_party_invite(**kwargs)
        return out, stderr.getvalue()

    def test_a_real_invite_is_answered_with_one_reply(self):
        payload = _real_invite_payload()
        out, log = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=payload,
        )
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertIsInstance(reply, ui_dispatch.VitalReply)
        self.assertEqual(reply.vital_id, wire.PARTY_INVITE_VITAL_ID)
        self.assertEqual(reply.payload, payload)
        self.assertEqual(reply.version, wire.PARTY_INVITE_VITAL_VERSION)
        self.assertIn("UI_PARTY_INVITE_ANSWER", log)

    def test_the_payload_that_goes_back_is_the_one_that_arrived(self):
        # Not "equal to a payload this test also built" -- the object
        # identity of the bytes is irrelevant, the VALUE must be what the
        # client sent, byte for byte, or the lane invented something.
        payload = _real_invite_payload()
        out, _ = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=payload,
        )
        self.assertEqual(bytes(out[0].payload), payload)

    def test_an_undecodable_payload_is_answered_with_nothing(self):
        out, log = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=b"\x00\x01\x99",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", log)

    def test_a_trailing_byte_is_not_byte_exact_and_is_refused(self):
        # The decoders in this project can succeed on a prefix; the round
        # trip is what turns "parsed" into "these are the bytes that
        # parsed".  Without it a payload with an unexplained trailer
        # would come back SHORTER than it went out.
        out, log = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID,
            payload=_real_invite_payload() + b"\xAA",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=", log)

    def test_a_frame_for_another_id_is_refused(self):
        out, log = self._call(
            vital_id=wire.PARTY_CMD_VITAL_ID, payload=_real_invite_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", log)

    def test_a_non_bytes_payload_is_refused_not_coerced(self):
        out, log = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID,
            payload=bytearray(_real_invite_payload()),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=payload_not_bytes", log)

    def test_the_budget_stops_answering_and_says_so(self):
        payload = _real_invite_payload()
        for _ in range(answerer_module.ANSWER_BUDGET):
            out, _ = self._call(
                vital_id=wire.PARTY_INVITE_VITAL_ID, payload=payload,
            )
            self.assertEqual(len(out), 1)
        out, log = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=payload,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=budget_spent", log)

    def test_a_refused_frame_does_not_spend_budget(self):
        # Ordering, not decoration: if the budget were charged before the
        # decode, a client sending junk could spend the whole allowance
        # and silence the button for the session that follows.
        for _ in range(answerer_module.ANSWER_BUDGET + 5):
            self._call(
                vital_id=wire.PARTY_INVITE_VITAL_ID, payload=b"\x00",
            )
        out, _ = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID,
            payload=_real_invite_payload(),
        )
        self.assertEqual(len(out), 1)

    def test_the_label_is_this_lanes_own(self):
        # The seam refuses a batch whose label is not UI_-prefixed or
        # carries a substring another consumer keys on; a label this
        # module ships must pass that check without an exemption.
        self.assertTrue(
            ui_dispatch._label_is_this_lanes_own(answerer_module.LABEL)
        )

    def test_the_module_is_production_allowed(self):
        # Without this the seam gates every frame at call time and the
        # button answers nothing on a normal boot.
        self.assertIs(answerer_module.production_allowed, True)


    def test_a_payload_past_the_reviewed_budget_does_not_spend_budget(self):
        # pf-adversary round xqxadg, D8.  The seam refuses a payload past
        # the reviewed budget AFTER this module has counted an answer, so
        # well-formed invites carrying a very long name could burn the
        # whole process allowance with zero bytes ever reaching anybody.
        # This module now asks the registry first, and the refusal must
        # be free.
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        oversized = wire.encode_party_invite_payload(
            wire.PartyInviteFields(
                field1_u8=1, field2_u64=0x1122334455667788,
                field3_wstring="A" * 260,
            )
        )
        self.assertGreater(len(oversized), shape.max_payload_bytes)
        out, console = self._call(
            vital_id=wire.PARTY_INVITE_VITAL_ID, payload=oversized,
        )
        self.assertEqual(out, [])
        self.assertIn("reason=over_reviewed_payload_budget", console)
        # Free: an ordinary invite right after it is still answered, and
        # the whole allowance is still there.
        for _ in range(answerer_module.ANSWER_BUDGET):
            out, _ = self._call(
                vital_id=wire.PARTY_INVITE_VITAL_ID, payload=_real_invite_payload(),
            )
            self.assertEqual(len(out), 1)


class SeamComposesTests(_AnswererRegistered):
    """answer() turns the reply into an action, and refuses what it can't."""

    def setUp(self):
        super().setUp()
        self.legacy = _legacy()

    def test_the_seam_composes_the_frame_the_envelope_builds(self):
        payload = _real_invite_payload()
        with contextlib.redirect_stderr(io.StringIO()):
            actions = ui_dispatch.answer(
                object(), wire.PARTY_INVITE_VITAL_ID, payload,
                envelope=self.legacy,
            )
        self.assertEqual(len(actions), 1)
        label, pc, frame, delay = actions[0]
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(wire.PARTY_INVITE_VITAL_ID,
              wire.PARTY_INVITE_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(label, answerer_module.LABEL)
        self.assertEqual(delay, 0.0)
        self.assertIs(type(actions[0]), tuple)

    def test_without_an_envelope_the_batch_is_refused_not_half_sent(self):
        # The default keeps every caller that does not pass an envelope --
        # a test, an older call site -- at exactly today's behaviour.
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            actions = ui_dispatch.answer(
                object(), wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
            )
        self.assertEqual(actions, [])
        self.assertIn("UI_DISPATCH_ANSWER_ERR", stderr.getvalue())

    def test_a_reply_may_not_answer_a_different_id(self):
        # Proven on `_compose` itself rather than through `answer()`: a
        # fake answerer registered from a TEST module puts that module in
        # the gating set, and the gate refuses it before composition is
        # ever reached -- so an end-to-end version of this test would go
        # green on the gate and prove nothing about the id rule.
        with self.assertRaises(ValueError):
            ui_dispatch._compose(
                self.legacy, wire.PARTY_INVITE_VITAL_ID,
                ui_dispatch.VitalReply(
                    label="UI_LIAR", vital_id=wire.PARTY_CMD_VITAL_ID,
                    version=0, payload=b"\x00", delay=0.0,
                ),
            )

    def test_a_composed_reply_dies_at_both_gates_on_a_foreign_label(self):
        # This test used to read "compose succeeds -- the label rule is
        # not `_compose`'s job -- and the validator refuses what it
        # built".  Half of that is no longer true: since COO-DECISION
        # 20260908_1142 item 7 route (b), `_compose` refuses a label the
        # outbound registry does not name, so a foreign label dies one
        # gate EARLIER and no frame is ever built for it.
        with self.assertRaises(ValueError):
            ui_dispatch._compose(
                self.legacy, wire.PARTY_INVITE_VITAL_ID,
                ui_dispatch.VitalReply(
                    label="UI_TELEPORT_NOW",
                    vital_id=wire.PARTY_INVITE_VITAL_ID,
                    version=0, payload=b"", delay=0.0,
                ),
            )
        # And the gate it used to die at still refuses it, checked on a
        # hand-built action: a new gate in front of an old one must not
        # quietly become the reason the old one is never exercised.
        self.assertFalse(
            ui_dispatch._actions_are_well_formed(
                [("UI_TELEPORT_NOW", b"\x01", b"\x02", 0.0)]
            )
        )

    def test_a_version_outside_one_byte_is_refused(self):
        with self.assertRaises(ValueError):
            ui_dispatch._compose(
                self.legacy, wire.PARTY_INVITE_VITAL_ID,
                ui_dispatch.VitalReply(
                    label="UI_X", vital_id=wire.PARTY_INVITE_VITAL_ID,
                    version=256, payload=b"", delay=0.0,
                ),
            )

    def test_an_id_that_merely_claims_to_be_equal_is_refused(self):
        # `!=` runs the lane's own `__eq__`.  An object that answers
        # "equal" would pass the id rule and then be handed to the
        # envelope builder itself, which is the forged-`__module__` hole
        # in a new place.  The type check runs first, so it never gets
        # to answer.
        class SaysYes(int):
            def __eq__(self, other):
                return True

            def __ne__(self, other):
                return False

            __hash__ = int.__hash__

        with self.assertRaises(TypeError):
            ui_dispatch._compose(
                self.legacy, wire.PARTY_INVITE_VITAL_ID,
                ui_dispatch.VitalReply(
                    label="UI_X", vital_id=SaysYes(0xDEAD),
                    version=0, payload=b"", delay=0.0,
                ),
            )

    def test_a_field_that_changes_between_reads_cannot_be_used(self):
        # A lane may subclass the namedtuple and make a field a property.
        # `_compose` reads each field once into a local, so the bytes
        # that were checked are the bytes that go out.
        class Shifty(ui_dispatch.VitalReply):
            _reads = 0

            @property
            def payload(self):
                type(self)._reads += 1
                return b"" if type(self)._reads == 1 else b"\xff" * 8

        item = Shifty(
            label="UI_PARTY_INVITE_ANSWERED",
            vital_id=wire.PARTY_INVITE_VITAL_ID,
            version=0, payload=b"", delay=0.0,
        )
        action = ui_dispatch._compose(
            self.legacy, wire.PARTY_INVITE_VITAL_ID, item,
        )
        expected_pc, _ = self.legacy.make_runtime_vitals(
            [(wire.PARTY_INVITE_VITAL_ID, 0, b"")]
        )
        self.assertEqual(action[1], expected_pc)

    def test_a_mutable_payload_is_refused_not_copied(self):
        # bytearray is mutable after the check; str would be encoded by
        # somebody else's guess of a codec.  Same rule the batch
        # validator already applies to `pc` and `frame`.
        for bad in (bytearray(b"\x00"), "\x00", memoryview(b"\x00")):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaises(TypeError):
                    ui_dispatch._compose(
                        self.legacy, wire.PARTY_INVITE_VITAL_ID,
                        ui_dispatch.VitalReply(
                            label="UI_X",
                            vital_id=wire.PARTY_INVITE_VITAL_ID,
                            version=0, payload=bad, delay=0.0,
                        ),
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

    def test_the_party_invite_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-party-answer")
        payload = _real_invite_payload()
        rx_before = state.rx_frames
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, wire.PARTY_INVITE_VITAL_ID, payload)
            ))
        self.assertEqual(state.rx_frames, rx_before + 1)
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, delay = actions[0]
        # SECOND LAYER, BUILT WITHOUT THE DISPATCHER: the frame the
        # player would receive is the envelope this project already
        # ships, carrying the id and payload that arrived.
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(wire.PARTY_INVITE_VITAL_ID,
              wire.PARTY_INVITE_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_a_malformed_invite_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-party-junk")
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(
                    self.legacy, wire.PARTY_INVITE_VITAL_ID, b"\x00\x01\x99",
                )
            ))
        self.assertEqual(actions, [])

    def test_the_other_ids_are_unchanged_when_only_this_one_is_registered(
        self,
    ):
        # This fixture installs exactly ONE registry entry (see
        # `_AnswererRegistered`), so what this measures is that the seam
        # answers only the id it was given an answerer for -- not that
        # seven ids are unanswered in production.  As of the round that
        # added `lane_ui_trade_invite_answer`, two of the eight are
        # answered on a real boot, and the test that would go stale on
        # that number is the one that must not be written here.
        for vital_id in sorted(ui_dispatch.ANSWERABLE_VITAL_IDS):
            if vital_id == wire.PARTY_INVITE_VITAL_ID:
                continue
            with self.subTest(vital_id=f"{vital_id:#06x}"):
                state = self._login_and_start(f"ui-other-{vital_id:04x}")
                with contextlib.redirect_stderr(io.StringIO()):
                    actions = state.dispatch(self.legacy.parse_outer(
                        _synthetic_pc(self.legacy, vital_id, b"\x00\x01")
                    ))
                self.assertEqual(actions, [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
