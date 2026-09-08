"""The fourth UI vital a player presses that the server answers.

A `Community_RequestBeFriendVital` (`0xB9E9`) sent from the shipped
client UI comes back out of the real `state.dispatch()` as a frame.
Before this round three of the eight `_FRIEND_MAIL_PARTY_TRADE_DISPATCH`
vitals were answered (party invite, trade invite, party command); this
one was among the five that got `[]`, and it is the first of the five
`CommunityModule_Client` ids to be answered.

WHY ANSWERING WITH THIS ID IS AN ANSWER AND NOT A GUESS.  RE-312
RESULT-1 (pf_bridge/notes_to_chief/20260908_1038_RE-312-RESULT-*.md)
lists `0xB9E9 Community_RequestBeFriendVital INBOUND_YES
handler=0x00645BF0 next=0x0063F9B0` inside `"CommunityModule_Client"`,
and RESULT-2 pins the caller at `0x005F38B2` inside the batch dispatch
loop, so the slot is reached by the ordinary receive path.

THE TWO THINGS THIS CLASS HAS THAT THE THREE BEFORE IT DO NOT:

1.  Its id is ALREADY read on the production path, by the report-only
    hook `lane_hooks/lane_ui_friend_wire_log.py`.  `runtime.py` fires
    that hook and THEN calls `ui_dispatch.answer()`, so the tests below
    measure that the log line and the answer both still happen -- an
    answerer that silenced the watcher beside it would be a regression
    nobody is watching for.
2.  A tagged wstring, so its width is the player's to move.  The
    reviewed row is a CEILING, and the fixed-width equality the party
    command button uses would be wrong here.  The module's docstring
    claims the decode/encode pair is injective for this class; the scan
    below is that claim, run, not asserted.

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
from pirateforce_foundation import ui_friend_wire as wire  # noqa: E402
from pirateforce_foundation import ui_party_wire as party_wire  # noqa: E402
from pirateforce_foundation import ui_social_wire as social_wire  # noqa: E402
from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_friend_request_answer as answerer_module,
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

FRIEND_ID = wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_ID

# THE REAL REGISTRATIONS, CAPTURED AS `lane_hooks._discover()` MADE THEM
# -- same reason as the three answerer test files beside this one:
# registering from a TEST module puts this module on the gating stack,
# and the gate correctly refuses a module `_discover()` never imported,
# which would read as the answerer not working.
_REAL_ENTRY = ui_dispatch._ANSWERERS.get(FRIEND_ID)
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


def _real_friend_payload(name: str = "Panya") -> bytes:
    """A friend request in ui_friend_wire's pinned shape."""
    return wire.encode_request_be_friend_payload(
        wire.RequestBeFriendFields(
            field1_u64=0x1122334455667788,
            field2_wstring=name,
            field3_u8=1,
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
            ui_dispatch._ANSWERERS[FRIEND_ID] = _REAL_ENTRY
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
            out = answerer_module.answer_request_be_friend(**kwargs)
        return out, stderr.getvalue()

    def test_a_wrong_id_is_refused(self):
        out, said = self._call(
            vital_id=party_wire.PARTY_CMD_VITAL_ID,
            payload=_real_friend_payload(),
        )
        self.assertEqual(out, [])
        self.assertIn("reason=wrong_id", said)

    def test_a_payload_that_is_not_bytes_is_refused(self):
        # `bytearray` too, not just `str`: a mutable buffer handed to an
        # answerer that echoes it back is a payload that can change
        # between the check and the send.
        for bad in ("not bytes", bytearray(_real_friend_payload()), None):
            out, said = self._call(vital_id=FRIEND_ID, payload=bad)
            self.assertEqual(out, [])
            self.assertIn("reason=payload_not_bytes", said)

    def test_an_undecodable_payload_is_refused(self):
        out, said = self._call(vital_id=FRIEND_ID, payload=b"\x00\x01\x99")
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", said)

    def test_a_payload_with_a_trailer_is_refused_as_UNDECODABLE(self):
        # `require_exhausted` is what makes a trailing byte a decode
        # failure rather than something the answerer would echo back
        # WITHOUT the trailer -- i.e. bytes that are not the player's.
        out, said = self._call(
            vital_id=FRIEND_ID, payload=_real_friend_payload() + b"\xAA",
        )
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", said)

    def test_a_lone_surrogate_name_is_refused_not_mangled(self):
        # An even-length, in-bounds UTF-16LE payload the codec still
        # rejects.  The decoder turns it into a WireDecodeError, so this
        # answerer refuses instead of echoing a repaired name.
        payload = (
            social_wire.u64tag(0x32, 1)
            + bytes([0x48]) + struct.pack("<I", 2) + b"\x00\xD8"
            + bytes([0x0B, 1])
        )
        out, said = self._call(vital_id=FRIEND_ID, payload=payload)
        self.assertEqual(out, [])
        self.assertIn("reason=undecodable", said)

    def test_the_round_trip_guard_refuses_when_it_IS_reached(self):
        # The scan below proves the real decoder never reaches this
        # branch.  It still cannot be deleted or inverted under a green
        # suite, because this test makes the encoder disagree and then
        # demands the refusal.
        # Built BEFORE the patch: a payload built by the broken encoder
        # would fail the DECODE and never reach the branch under test.
        payload = _real_friend_payload()
        real_encode = wire.encode_request_be_friend_payload
        try:
            wire.encode_request_be_friend_payload = (
                lambda fields: real_encode(fields) + b"\x00"
            )
            out, said = self._call(vital_id=FRIEND_ID, payload=payload)
        finally:
            wire.encode_request_be_friend_payload = real_encode
        self.assertEqual(out, [])
        self.assertIn("reason=not_byte_exact", said)

    def test_a_label_with_no_reviewed_shape_is_refused_not_skipped(self):
        # pf-adversary round 1gc6hl, D-F: a missing registry row must be
        # a refusal in its own token, not a check that quietly did not
        # apply and a death inside ui_dispatch._compose.
        saved = answerer_module.LABEL
        try:
            answerer_module.LABEL = "UI_NO_SUCH_REVIEWED_LABEL"
            out, said = self._call(
                vital_id=FRIEND_ID, payload=_real_friend_payload(),
            )
        finally:
            answerer_module.LABEL = saved
        self.assertEqual(out, [])
        self.assertIn("reason=no_reviewed_outbound_shape", said)

    def test_a_payload_over_the_reviewed_ceiling_is_refused(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        # A name long enough to push the payload past the reviewed
        # ceiling.  Built from the encoder, so it stays right if the row
        # or the field list moves.
        name = "A" * shape.max_payload_bytes
        payload = _real_friend_payload(name)
        self.assertGreater(len(payload), shape.max_payload_bytes)
        out, said = self._call(vital_id=FRIEND_ID, payload=payload)
        self.assertEqual(out, [])
        self.assertIn("reason=over_reviewed_budget", said)

    def test_this_module_keeps_no_allowance_of_its_own(self):
        # pf-adversary D-B, round vy1m79: the seam charges the session,
        # per vital, at its send point.  Called directly (no seam), this
        # module answers every time -- which is what "keeps no counter"
        # means, measured.
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 5):
            out, _ = self._call(
                vital_id=FRIEND_ID, payload=_real_friend_payload(),
            )
            self.assertEqual(len(out), 1)

    def test_the_reply_is_the_players_own_bytes(self):
        payload = _real_friend_payload("Somebody")
        out, said = self._call(vital_id=FRIEND_ID, payload=payload)
        self.assertEqual(len(out), 1)
        reply = out[0]
        self.assertEqual(reply.payload, payload)
        self.assertEqual(reply.vital_id, FRIEND_ID)
        self.assertEqual(
            reply.version, wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
        )
        self.assertEqual(reply.label, answerer_module.LABEL)
        self.assertIn("UI_FRIEND_REQUEST_ANSWER len=", said)


class TheRoundTripIsInjectiveTests(unittest.TestCase):
    """The module docstring's measurement, run rather than asserted.

    The first draft of that docstring claimed the opposite -- that a
    wstring class must have a live round-trip guard because the decoder
    READS a length the encoder RECOMPUTES.  That claim was false, and
    this class is what made it false in public: strict UTF-16LE decode
    is injective, and `read_untagged_wstring` refuses the two shapes
    that would break it (odd byte length, unpaired surrogate) before
    the codec is reached.
    """

    def _wrap(self, name_bytes: bytes) -> bytes:
        return (
            social_wire.u64tag(0x32, 7)
            + bytes([0x48]) + struct.pack("<I", len(name_bytes)) + name_bytes
            + bytes([0x0B, 3])
        )

    def test_every_two_byte_name_that_decodes_reencodes_identically(self):
        decoded = 0
        for unit in range(0x10000):
            payload = self._wrap(struct.pack("<H", unit))
            fields = wire.decode_request_be_friend_payload(payload)
            if fields is None:
                continue
            decoded += 1
            self.assertEqual(
                wire.encode_request_be_friend_payload(fields), payload,
                "code unit %04X re-encoded to different bytes" % (unit,),
            )
        # The number the module docstring quotes for this half.
        self.assertEqual(decoded, 63488)

    def test_random_four_byte_names_that_decode_reencode_identically(self):
        rnd = random.Random(7)
        decoded = 0
        for _ in range(200000):
            payload = self._wrap(bytes(rnd.randrange(256) for _ in range(4)))
            fields = wire.decode_request_be_friend_payload(payload)
            if fields is None:
                continue
            decoded += 1
            self.assertEqual(
                wire.encode_request_be_friend_payload(fields), payload,
            )
        # Not pinned to an exact count: it is a random scan, and a pinned
        # number here would only pin the seed.  What is pinned is that a
        # large majority decoded, so a decoder that started refusing
        # everything could not make this test pass by testing nothing.
        self.assertGreater(decoded, 150000)


class TheReviewedRowsTests(unittest.TestCase):
    """The two rows this round added to ui_dispatch, checked as rows."""

    def test_the_owner_row_names_this_module_and_only_this_module(self):
        self.assertEqual(
            ui_dispatch._ANSWERER_OWNERS[FRIEND_ID],
            answerer_module.__name__,
        )
        owners = [
            vid for vid, mod in ui_dispatch._ANSWERER_OWNERS.items()
            if mod == answerer_module.__name__
        ]
        self.assertEqual(owners, [FRIEND_ID])

    def test_the_outbound_row_names_this_id_and_a_bound_it_can_meet(self):
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, FRIEND_ID)
        self.assertIn(
            wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION, shape.versions,
        )
        # The row is a CEILING for this class, not a width: a one-letter
        # name and a long one must both fit under it.
        self.assertLess(len(_real_friend_payload("A")), shape.max_payload_bytes)
        self.assertLess(
            len(_real_friend_payload("A" * 100)), shape.max_payload_bytes,
        )

    def test_this_id_was_answerable_before_anybody_wrote_an_answerer(self):
        # The seam's id set is pinned EQUAL to runtime.py's own dispatch
        # set, so this row cannot be a number this lane invented.
        self.assertIn(FRIEND_ID, ui_dispatch.ANSWERABLE_VITAL_IDS)

    def test_the_arming_names_this_module_declares_are_usable(self):
        # The runner that reads these is not on main yet.  What is
        # checked here is the half this file owns: the token is ASCII
        # (cp874 console) and the sample is a frame this module's OWN
        # guards accept -- a sample that its own answerer refuses would
        # make the arming proof read FAIL for a working button.
        self.assertEqual(
            answerer_module.ARMING_TOKEN, "UI_FRIEND_REQUEST_ANSWER_ARMED",
        )
        answerer_module.ARMING_TOKEN.encode("ascii")
        vital_id, version, payload = answerer_module.arming_sample()
        self.assertEqual(vital_id, FRIEND_ID)
        self.assertEqual(
            version, wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
        )
        with contextlib.redirect_stderr(io.StringIO()):
            out = answerer_module.answer_request_be_friend(
                vital_id=vital_id, payload=payload,
            )
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].payload, payload)


class TheOwnerRowDecidesWhoMayTakeThisIdTests(unittest.TestCase):
    """A row exists for 0xB9E9 now, and it names one module."""

    def setUp(self):
        self._saved = dict(ui_dispatch._ANSWERERS)
        self.addCleanup(self._restore)

    def _restore(self):
        ui_dispatch._ANSWERERS.clear()
        ui_dispatch._ANSWERERS.update(self._saved)

    def _lane_module(self, stem, source):
        """A module `_discover()` would import.

        Built the way the three answerer test files beside this one
        build one, and for the reason they record: the seam judges the
        module on the REGISTRATION STACK, so registering from this test
        file would not exercise the rule at all -- a test module is not
        a lane, and the seam says so plainly (it refuses to police
        registrars outside the lane package).  Setting `fn.__module__`
        is likewise not enough, which this file learned by writing that
        test first and watching the thief win.
        """
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
        "    return [('UI_FRIEND_REQUEST_ANSWERED', b'\\xff',"
        " b'\\xff\\xff', 0.0)]\n"
        "def install(vital_id):\n"
        "    return ui_dispatch.register_answerer(vital_id, answerer)\n"
    )

    def test_a_lane_module_that_is_not_the_owner_is_refused(self):
        """The attack from pf-adversary round xqxadg D9, on the new id.

        Alphabetically first, flag on, id free -- and it still loses,
        because `_ANSWERER_OWNERS` names one module per id and this
        round added the row for `0xB9E9` in the same commit as the
        answerer.  Without that row the thief would win: this is the
        test that makes the row load-bearing rather than decorative.
        """
        ui_dispatch.clear_answerers()
        thief = self._lane_module("lane_ui_aaa_friend_thief", self.TAKER)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            self.assertFalse(thief.install(FRIEND_ID))
        self.assertIn("reason=not_the_reviewed_owner", stderr.getvalue())
        self.assertIsNone(ui_dispatch.registered_answerer(FRIEND_ID))

    def test_the_reviewed_owner_is_the_module_that_shipped_the_answerer(self):
        # The row is only worth having if it names the module a player's
        # bytes actually come from, so this reads the shipped
        # registration rather than the table it is being checked against.
        self.assertIsNotNone(_REAL_ENTRY, "the answerer must be registered")
        self.assertEqual(
            _REAL_ENTRY[0], ui_dispatch._ANSWERER_OWNERS[FRIEND_ID],
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

    def test_the_add_friend_button_gets_a_frame_back(self):
        state = self._login_and_start("ui-friend-request-answer")
        payload = _real_friend_payload()
        actions, _ = self._press(state, FRIEND_ID, payload)
        self.assertEqual(len(actions), 1, "the button must be answered")
        label, pc, frame, _delay = actions[0]
        # SECOND LAYER, BUILT WITHOUT THE DISPATCHER.
        expected_pc, expected_frame = self.legacy.make_runtime_vitals(
            [(FRIEND_ID,
              wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION, payload)]
        )
        self.assertEqual(pc, expected_pc)
        self.assertEqual(frame, expected_frame)
        self.assertEqual(frame, self.legacy.frame_pc(pc))
        self.assertEqual(label, answerer_module.LABEL)
        self.assertTrue(frame, "an action carrying no bytes is a no-op")

    def test_the_report_only_watcher_on_this_id_still_prints(self):
        # THE ONE INTERACTION THIS BUTTON HAS THAT THE OTHER THREE DO
        # NOT.  runtime.py fires lane_ui_friend_wire_log's hook and THEN
        # calls answer(); an answerer that swallowed the frame, or a
        # hook order that stopped the log, would take away evidence an
        # attended round depends on.  Both lines, one press.
        state = self._login_and_start("ui-friend-request-watcher")
        actions, said = self._press(state, FRIEND_ID, _real_friend_payload())
        self.assertEqual(len(actions), 1)
        self.assertIn("LANE_UI_FRIEND_REQUEST decoded", said)
        self.assertIn("UI_FRIEND_REQUEST_ANSWER len=", said)

    def test_a_name_of_many_letters_is_answered_as_sent(self):
        # The property the ceiling row exists to allow: this class's
        # width is the player's, so two different name lengths must both
        # come back, and each as its own bytes.
        state = self._login_and_start("ui-friend-request-widths")
        for name in ("A", "A" * 60, "Panya"):
            payload = _real_friend_payload(name)
            actions, _ = self._press(state, FRIEND_ID, payload)
            self.assertEqual(len(actions), 1, name)
            _, _, frame, _ = actions[0]
            self.assertEqual(
                frame,
                self.legacy.make_runtime_vitals(
                    [(FRIEND_ID,
                      wire.COMMUNITY_REQUEST_BE_FRIEND_VITAL_VERSION,
                      payload)]
                )[1],
            )

    def test_a_malformed_request_still_answers_nothing_end_to_end(self):
        state = self._login_and_start("ui-friend-request-junk")
        actions, _ = self._press(state, FRIEND_ID, b"\x00\x01\x99")
        self.assertEqual(actions, [])
        actions, _ = self._press(
            state, FRIEND_ID, _real_friend_payload() + b"\xAA",
        )
        self.assertEqual(actions, [])

    def test_a_peer_that_never_logged_in_gets_nothing(self):
        # pf-adversary D7 (round 1gc6hl) applies to every answerer on
        # this seam, and a new one is exactly where that could be
        # forgotten: the gate is the seam's, so this button inherits it,
        # and this test is what proves the inheritance is real.
        state_type = make_state_class(
            self.legacy, self.lifecycle, self.projector,
        )
        state = state_type("ui-friend-request-nobody")
        with contextlib.redirect_stderr(io.StringIO()):
            actions = state.dispatch(self.legacy.parse_outer(
                _synthetic_pc(self.legacy, FRIEND_ID, _real_friend_payload())
            ))
        self.assertEqual(actions, [])

    def test_a_storm_on_this_button_does_not_silence_the_invite_button(self):
        """The property the allowance is keyed on, measured on the new id.

        pf-adversary round vy1m79, D1 measured this failing the other way
        round when the allowance was keyed on the session alone.  A
        fourth answerer sharing the seam is the moment that could
        regress, so it is measured here rather than argued from the
        key's shape.
        """
        state = self._login_and_start("ui-friend-request-storm")
        answered = 0
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 8):
            actions, _ = self._press(state, FRIEND_ID, _real_friend_payload())
            answered += len(actions)
        self.assertEqual(answered, ui_dispatch.SESSION_ANSWER_BUDGET)
        # ... and the invite button of the SAME session still answers.
        actions, _ = self._press(
            state, party_wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
        )
        self.assertEqual(len(actions), 1)

    def test_another_session_is_not_charged_for_this_ones_storm(self):
        first = self._login_and_start("ui-friend-request-storm-a")
        for _ in range(ui_dispatch.SESSION_ANSWER_BUDGET + 1):
            self._press(first, FRIEND_ID, _real_friend_payload())
        second = self._login_and_start("ui-friend-request-storm-b")
        actions, _ = self._press(second, FRIEND_ID, _real_friend_payload())
        self.assertEqual(len(actions), 1)

    def test_the_answer_carries_the_reviewed_outbound_shape(self):
        # The frame leaves only because ui_dispatch's outbound registry
        # names this label for this id.  Proving it HERE, on the real
        # dispatcher, is what stops the registry from being a table that
        # is true in its own unit test and bypassed on the live path.
        state = self._login_and_start("ui-friend-request-shape")
        shape = ui_dispatch.outbound_shape(answerer_module.LABEL)
        self.assertIsNotNone(shape)
        self.assertEqual(shape.vital_id, FRIEND_ID)
        actions, _ = self._press(state, FRIEND_ID, _real_friend_payload())
        self.assertEqual(len(actions), 1)
        self.assertLessEqual(len(actions[0][2]), shape.max_frame_bytes)

    def test_the_invite_button_still_answers_with_the_new_row_in_place(self):
        # A fourth row must not change the three answers that already
        # shipped -- measured, not assumed, on the real dispatcher.
        state = self._login_and_start("ui-friend-request-neighbour")
        actions, _ = self._press(
            state, party_wire.PARTY_INVITE_VITAL_ID, _real_invite_payload(),
        )
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0][0], invite_module.LABEL)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
