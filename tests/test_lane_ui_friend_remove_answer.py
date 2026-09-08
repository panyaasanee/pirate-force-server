"""The fourth UI vital a player presses that the server answers.

A `Community_RemoveFriendVital` (`0x98A1`) sent from the shipped client
UI comes back out of the real `state.dispatch()` as a frame.  Before this
round three of the eight `_FRIEND_MAIL_PARTY_TRADE_DISPATCH` vitals were
answered on `main` (party invite, trade invite, party command); this one
was among the five that got `[]`.

WHY ANSWERING WITH THIS ID IS AN ANSWER AND NOT A GUESS.  RE-312
RESULT-1 (pf_bridge/notes_to_chief/20260908_1038_RE-312-RESULT-*.md)
lists `0x98A1 Community_RemoveFriendVital INBOUND_YES
handler=0x00645BF0 next=0x0063F9B0`, and RESULT-2 pins the caller at
`0x005F38B2` inside the batch dispatch loop.

WHAT THAT LETTER DID NOT SETTLE is carried in the module docstring and
not softened here: the five `Community_` ids share one vtable entry and
split INSIDE `0x0063F9B0`, and nobody has read that function.

THE ONE THING THIS CLASS HAS is a payload that cannot vary: `u64 + u64 +
u8`, no string.  So the reviewed outbound row pins the EXACT width and
the answerer requires equality rather than a ceiling, and the tests
below measure the property that pin rests on instead of asserting it.

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
from pirateforce_foundation import ui_friend_wire as wire  # noqa: E402
from pirateforce_foundation import ui_social_wire as social_wire  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_friend_remove_answer as answerer_module,
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
# same reason as the three answerer test files beside this one:
# registering from a TEST module puts this module on the gating stack,
# and the gate correctly refuses a module `_discover()` never imported,
# which would read as the answerer not working.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(
    wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID
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


def _real_remove_payload() -> bytes:
    """A friend removal in ui_friend_wire's pinned shape."""
    return wire.encode_remove_friend_payload(
        wire.RemoveFriendFields(
            field1_u64=0x1122334455667788,
            field2_u64=0x99AABBCCDDEEFF00,
            field3_u8=1,
        )
    )


class _AnswererRegistered(unittest.TestCase):
    """Register the real answerer, and put the registry back."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)
        ui_dispatch.reset_session_budgets_for_tests()
        self.addCleanup(ui_dispatch.reset_session_budgets_for_tests)
        ui_dispatch.clear_answerers()
        if _REAL_ENTRY is not None:
            ui_dispatch._ANSWERERS[
                wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID
            ] = _REAL_ENTRY

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)


class RefusalTests(_AnswererRegistered):
    """Every way this answerer can be wrong ends in an empty list."""

    def _call(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            out = answerer_module.answer_remove_friend(**kwargs)
        return out, stderr.getvalue()

    def test_a_wrong_id_is_refused(self):
        out, console = self._call(
            vital_id=wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID,
            payload=_real_remove_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", console)

    def test_a_payload_that_is_not_bytes_is_refused(self):
        for bad in (bytearray(_real_remove_payload()), "x", memoryview(b"")):
            with self.subTest(kind=type(bad).__name__):
                out, console = self._call(
                    vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                    payload=bad,
                )
                self.assertEqual(out, [])
                self.assertIn("reason=payload_not_bytes", console)

    def test_an_undecodable_payload_is_refused(self):
        out, console = self._call(
            vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
            payload=b"\x00\x01\x99",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_a_payload_with_a_trailer_is_refused_as_UNDECODABLE(self):
        """Named for the refusal it actually gets, not the one it looks
        like.

        `decode_remove_friend_payload` calls `require_exhausted`, so one
        unexplained trailing byte dies one step BEFORE the round-trip
        comparison and two steps before the fixed-width check.  Each of
        those three guards is measured on its own below.
        """
        out, console = self._call(
            vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
            payload=_real_remove_payload() + b"\x77",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", console)

    def test_no_decodable_payload_reaches_the_round_trip_refusal(self):
        """The round-trip guard is dead code today, measured not claimed.

        4,000 structurally valid payloads, both u64 extremes included;
        every one that decodes re-encodes byte for byte.  A decoder that
        ever loosens turns this red, which is the moment the guard stops
        being dead code.
        """
        rng = random.Random(20260908)
        extremes = [(0, 0, 0), ((1 << 64) - 1, (1 << 64) - 1, 0xFF)]
        decoded = 0
        for index in range(4000):
            if index < len(extremes):
                one, two, three = extremes[index]
            else:
                one, two, three = (
                    rng.getrandbits(64), rng.getrandbits(64),
                    rng.getrandbits(8),
                )
            payload = (
                social_wire.u64tag(wire._TAG_U64, one)
                + social_wire.u64tag(wire._TAG_U64, two)
                + bytes([wire._TAG_U8, three])
            )
            fields = wire.decode_remove_friend_payload(payload)
            if fields is None:
                continue
            decoded += 1
            self.assertEqual(
                wire.encode_remove_friend_payload(fields), payload,
            )
        self.assertGreater(decoded, 1000, "the sample decoded too little")

    def test_the_round_trip_guard_refuses_when_it_IS_reached(self):
        """The guard is exercised, so deleting it cannot stay green."""
        payload = _real_remove_payload()
        real_encoder = wire.encode_remove_friend_payload

        def _wrong_encoder(fields):
            return real_encoder(fields)[:-1] + b"\xEE"

        wire.encode_remove_friend_payload = _wrong_encoder
        try:
            out, console = self._call(
                vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                payload=payload,
            )
        finally:
            wire.encode_remove_friend_payload = real_encoder
        self.assertEqual(out, [])
        self.assertIn("reason=not_byte_exact", console)

    def test_a_label_with_no_reviewed_shape_is_refused_not_skipped(self):
        """A missing registry row is a refusal, never a skipped check."""
        real_label = answerer_module.LABEL
        answerer_module.LABEL = "UI_FRIEND_REMOVE_ANSWERED_NOT_REVIEWED"
        try:
            out, console = self._call(
                vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                payload=_real_remove_payload(),
            )
        finally:
            answerer_module.LABEL = real_label
        self.assertEqual(out, [])
        self.assertIn("reason=no_reviewed_outbound_shape", console)

    def test_this_module_keeps_no_allowance_of_its_own(self):
        """The allowance is the seam's, per (session, vital id)."""
        source = Path(answerer_module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("_ANSWERS_SENT", source)
        self.assertNotIn("global ", source)

    def test_the_reply_is_the_players_own_bytes(self):
        payload = _real_remove_payload()
        out, console = self._call(
            vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID, payload=payload,
        )
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertEqual(reply.payload, payload)
        self.assertEqual(
            reply.vital_id, wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
        )
        self.assertEqual(
            reply.version, wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION,
        )
        self.assertEqual(reply.label, answerer_module.LABEL)
        self.assertIn("UI_FRIEND_REMOVE_ANSWER len=20", console)


class TheWidthIsFixedAndCheckedAsFixedTests(_AnswererRegistered):
    """The pin rests on a measured property, not on a comment."""

    def test_every_field_value_encodes_to_the_same_width(self):
        rng = random.Random(7)
        widths = set()
        for _ in range(4000):
            widths.add(len(wire.encode_remove_friend_payload(
                wire.RemoveFriendFields(
                    rng.getrandbits(64), rng.getrandbits(64),
                    rng.getrandbits(8),
                )
            )))
        widths.add(len(wire.encode_remove_friend_payload(
            wire.RemoveFriendFields(0, 0, 0)
        )))
        widths.add(len(wire.encode_remove_friend_payload(
            wire.RemoveFriendFields((1 << 64) - 1, (1 << 64) - 1, 0xFF)
        )))
        self.assertEqual(widths, {20})

    def test_the_reviewed_number_is_the_encoders_own_width(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertEqual(
            shape.max_payload_bytes, len(_real_remove_payload()),
        )

    def test_a_reencoding_that_is_too_LONG_is_refused(self):
        payload = _real_remove_payload()
        real_encoder = wire.encode_remove_friend_payload

        def _long_encoder(fields):
            return real_encoder(fields) + b"\x00"

        wire.encode_remove_friend_payload = _long_encoder
        try:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                out = answerer_module.answer_remove_friend(
                    vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                    payload=payload,
                )
        finally:
            wire.encode_remove_friend_payload = real_encoder
        self.assertEqual(out, [])
        # It dies at the byte-exact guard first, which is the point:
        # the width check is the SECOND net, not the only one.
        self.assertIn("reason=not_byte_exact", stderr.getvalue())

    def test_a_width_the_registry_disagrees_with_is_refused(self):
        """Move the reviewed number and the button goes silent, loudly."""
        real = ui_dispatch._OUTBOUND_FRAME_SHAPES[answerer_module.LABEL]
        ui_dispatch._OUTBOUND_FRAME_SHAPES[answerer_module.LABEL] = (
            real._replace(max_payload_bytes=19)
        )
        try:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                out = answerer_module.answer_remove_friend(
                    vital_id=wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                    payload=_real_remove_payload(),
                )
        finally:
            ui_dispatch._OUTBOUND_FRAME_SHAPES[answerer_module.LABEL] = real
        self.assertEqual(out, [])
        self.assertIn("reason=not_the_fixed_payload_width", stderr.getvalue())


class TheReviewedRowsTests(unittest.TestCase):
    """The two rows a lane cannot write for itself."""

    def test_the_owner_row_names_this_module_and_only_this_module(self):
        self.assertEqual(
            ui_dispatch._ANSWERER_OWNERS[
                wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID
            ],
            answerer_module.__name__,
        )

    def test_the_outbound_row_names_this_id_and_a_frame_bound_it_can_meet(
        self,
    ):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(
            shape.vital_id, wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
        )
        self.assertEqual(shape.versions, frozenset((0,)))
        self.assertEqual(shape.max_frame_bytes, 64)
        # 52 measured on this commit; the bound is the envelope's room,
        # not this lane's, so it is checked against a frame the project
        # builds rather than against itself.
        legacy = _legacy()
        _pc, frame = legacy.make_runtime_vitals(
            [(wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
              wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION,
              _real_remove_payload())]
        )
        self.assertEqual(len(frame), 52)
        self.assertLessEqual(len(frame), shape.max_frame_bytes)

    def test_this_id_was_answerable_before_anybody_wrote_an_answerer(self):
        # The row did not widen the seam: 0x98A1 has been one of the
        # eight ids runtime.py routes here all along -- what was missing
        # was somebody to answer it.
        self.assertIn(
            wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
            ui_dispatch.ANSWERABLE_VITAL_IDS,
        )

    def test_the_version_this_lane_sends_is_the_one_the_row_reviewed(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIn(
            wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION, shape.versions,
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
        with contextlib.redirect_stderr(io.StringIO()):
            return state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, vital_id, payload)
            ))

    def test_the_remove_friend_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-friend-remove-answer")
        payload = _real_remove_payload()
        actions = self._press(
            state, wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID, payload,
        )
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, _delay = actions[0]
        # SECOND LAYER, BUILT WITHOUT THE DISPATCHER.
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
              wire.COMMUNITY_REMOVE_FRIEND_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_a_malformed_removal_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-friend-remove-junk")
        self.assertEqual(
            self._press(
                state, wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                b"\x00\x01\x99",
            ),
            [],
        )

    def test_a_peer_that_never_logged_in_gets_nothing(self):
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("ui-friend-remove-nologin")
        self.assertEqual(
            self._press(
                state, wire.COMMUNITY_REMOVE_FRIEND_VITAL_ID,
                _real_remove_payload(),
            ),
            [],
        )


class TheReportOnlyHookCapsWhatItPrintsTests(unittest.TestCase):
    """pf-adversary round `asw0n3`, D5, measured on the sibling hook.

    ``lane_ui_friend_wire_log`` runs BEFORE ``ui_dispatch.answer()``, so
    a peer that never logged in reaches it: the login gate and the
    per-session answer allowance are both downstream.  Its UNPARSED line
    was always capped at 96 bytes of hex; its DECODED line printed
    ``field2_wstring`` with no bound at all, which made stderr an
    amplifier a stranger could drive.  These tests pin the cap on the
    path that lacked it and on the path that already had it.
    """

    def test_a_long_name_does_not_reach_stderr_in_full(self):
        from pirateforce_foundation.lane_hooks import (
            lane_ui_friend_wire_log as log_hook,
        )

        name = "A" * 5000
        payload = wire.encode_request_be_friend_payload(
            wire.RequestBeFriendFields(1, name, 0)
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            log_hook._on_request_be_friend(payload=payload)
        line = stderr.getvalue()
        self.assertIn("LANE_UI_FRIEND_REQUEST decoded", line)
        self.assertNotIn("A" * 200, line)
        # The whole line, not just the clipped field: an unbounded value
        # anywhere else on it would fail here too.
        self.assertLess(len(line), 400)

    def test_the_cut_is_announced_and_a_short_name_is_not_marked(self):
        from pirateforce_foundation.lane_hooks import (
            lane_ui_friend_wire_log as log_hook,
        )

        for name, cut in (("A" * 5000, True), ("Panya", False)):
            with self.subTest(length=len(name)):
                payload = wire.encode_request_be_friend_payload(
                    wire.RequestBeFriendFields(1, name, 0)
                )
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    log_hook._on_request_be_friend(payload=payload)
                line = stderr.getvalue()
                self.assertEqual("'+" in line, cut)

    def test_astral_characters_cannot_multiply_the_line_either(self):
        """The measured amplifier was astral text, so it is the case
        pinned: `repr` escapes each one, so a character budget is what
        bounds the line, not a byte budget."""
        from pirateforce_foundation.lane_hooks import (
            lane_ui_friend_wire_log as log_hook,
        )

        payload = wire.encode_request_be_friend_payload(
            wire.RequestBeFriendFields(1, "\U0001F600" * 2000, 0)
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            log_hook._on_request_be_friend(payload=payload)
        self.assertLess(len(stderr.getvalue()), 1200)

    def test_the_undecodable_line_was_already_capped_and_still_is(self):
        from pirateforce_foundation.lane_hooks import (
            lane_ui_friend_wire_log as log_hook,
        )

        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            log_hook._on_remove_friend(payload=b"\x99" * 100000)
        line = stderr.getvalue()
        self.assertIn("UNPARSED len=100000", line)
        self.assertLess(len(line), 400)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
