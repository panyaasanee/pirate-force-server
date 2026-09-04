"""The four LANE-UI report-only ``lane_hooks/lane_ui_*_wire_log.py``
modules that subscribe onto the eight friend/mail/party/trade points
``runtime.py`` opened in ``_FRIEND_MAIL_PARTY_TRADE_DISPATCH``
(CORE-REQUEST ``pf_bridge/notes_to_chief/20260904_1120``, hooks landed per
chief letter ``20260904_1522`` which explicitly hands the ``lane_ui_*.py``
registration to LANE-UI without a further CORE-REQUEST round).

Mirrors ``tests/test_lane_a_enter_instance_log.py``'s own shape for the one
comparable sibling point already on ``main``: decode-with-a-valid-payload,
decode-with-garbage, ascii-safety, hex-cap, non-bytes payload, and the
registration/production_allowed contract every ``lane_hooks`` module must
satisfy. Field values are round-tripped through each wire module's own
``encode_*`` function rather than hand-typed bytes, so a change to either
side of an encode/decode pair breaks this test instead of silently
agreeing with itself.

NOT PROVEN HERE (same limit ``test_lane_ui_friend_mail_party_trade_dispatch_
wiring.py`` states for itself): that a real client has ever sent any of
these eight frames, or what any field means. These hooks print raw
positional field values and nothing else -- no field is renamed, no store
row is touched, no frame is sent back.
"""
from __future__ import annotations

import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import lane_hooks  # noqa: E402
from pirateforce_foundation import ui_friend_wire  # noqa: E402
from pirateforce_foundation import ui_mail_wire  # noqa: E402
from pirateforce_foundation import ui_party_wire  # noqa: E402
from pirateforce_foundation import ui_trade_wire  # noqa: E402
from pirateforce_foundation.lane_hooks import (  # noqa: E402
    lane_ui_friend_wire_log,
    lane_ui_mail_wire_log,
    lane_ui_party_wire_log,
    lane_ui_trade_wire_log,
)

# (hook module, point name, hook fn, encode fn, decode fn, valid fields)
_CASES = (
    (
        lane_ui_party_wire_log, "vital_inbound_party_invite_vital",
        lane_ui_party_wire_log._on_party_invite,
        ui_party_wire.encode_party_invite_payload,
        ui_party_wire.decode_party_invite_payload,
        ui_party_wire.PartyInviteFields(7, 1234567890, "hello"),
    ),
    (
        lane_ui_party_wire_log, "vital_inbound_party_cmd_vital",
        lane_ui_party_wire_log._on_party_cmd,
        ui_party_wire.encode_party_cmd_payload,
        ui_party_wire.decode_party_cmd_payload,
        ui_party_wire.PartyCmdFields(3, 42),
    ),
    (
        lane_ui_friend_wire_log, "vital_inbound_community_request_be_friend_vital",
        lane_ui_friend_wire_log._on_request_be_friend,
        ui_friend_wire.encode_request_be_friend_payload,
        ui_friend_wire.decode_request_be_friend_payload,
        ui_friend_wire.RequestBeFriendFields(99, "ahoy", 1),
    ),
    (
        lane_ui_friend_wire_log, "vital_inbound_community_remove_friend_vital",
        lane_ui_friend_wire_log._on_remove_friend,
        ui_friend_wire.encode_remove_friend_payload,
        ui_friend_wire.decode_remove_friend_payload,
        ui_friend_wire.RemoveFriendFields(5, 6, 0),
    ),
    (
        lane_ui_mail_wire_log, "vital_inbound_community_send_mail_vital",
        lane_ui_mail_wire_log._on_send_mail,
        ui_mail_wire.encode_send_mail_payload,
        ui_mail_wire.decode_send_mail_payload,
        ui_mail_wire.SendMailFields(1, "a", 2, "b", "c", "d", "e", "f", 9),
    ),
    (
        lane_ui_mail_wire_log, "vital_inbound_community_get_mail_content_vital",
        lane_ui_mail_wire_log._on_get_mail_content,
        ui_mail_wire.encode_get_mail_content_payload,
        ui_mail_wire.decode_get_mail_content_payload,
        ui_mail_wire.GetMailContentFields(11, 22, 3, "g"),
    ),
    (
        lane_ui_mail_wire_log, "vital_inbound_community_delete_mail_vital",
        lane_ui_mail_wire_log._on_delete_mail,
        ui_mail_wire.encode_delete_mail_payload,
        ui_mail_wire.decode_delete_mail_payload,
        ui_mail_wire.DeleteMailFields(44, 55, 6),
    ),
    (
        lane_ui_trade_wire_log, "vital_inbound_trade_invite_vital",
        lane_ui_trade_wire_log._on_trade_invite,
        ui_trade_wire.encode_trade_invite_payload,
        ui_trade_wire.decode_trade_invite_payload,
        ui_trade_wire.TradeInviteFields(2, 987654321, "yo-ho"),
    ),
)


class RegistrationAndProductionAllowedTests(unittest.TestCase):
    def test_every_one_of_the_eight_points_has_at_least_one_subscriber(self):
        points = lane_hooks.registered_points()
        for _mod, point, *_rest in _CASES:
            with self.subTest(point=point):
                self.assertGreaterEqual(points.get(point, 0), 1)

    def test_all_four_modules_declare_production_allowed_true(self):
        for module in (
            lane_ui_party_wire_log, lane_ui_friend_wire_log,
            lane_ui_mail_wire_log, lane_ui_trade_wire_log,
        ):
            with self.subTest(module=module.__name__):
                self.assertIs(module.production_allowed, True)
                self.assertIs(
                    lane_hooks.module_production_allowed(module.__name__),
                    True,
                )


class DecodeAndConsoleLineTests(unittest.TestCase):
    def test_a_valid_payload_decodes_and_prints_every_field_no_unparsed(self):
        for _mod, point, hook_fn, encode, _decode, fields in _CASES:
            with self.subTest(point=point):
                payload = encode(fields)
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    result = hook_fn(session=object(), payload=payload)
                self.assertIsNone(result, "hooks never return a value")
                console = stderr.getvalue()
                self.assertNotIn("UNPARSED", console)
                self.assertIn("decoded", console)
                self.assertIn("bytes_out=0", console)
                self.assertIn(f"consumed={len(payload)}/{len(payload)}", console)
                for value in vars(fields).values():
                    self.assertIn(str(value), console)

    def test_trailing_bytes_after_a_full_match_are_never_silently_dropped(self):
        # pf-adversary (this round): none of the ui_*_wire.py decode_*
        # functions check that a match consumed the WHOLE payload -- a
        # match against the first `c` bytes returns success even with
        # `n - c` bytes of unexplained trailer following. A bare "decoded
        # field... bytes_out=0" line would read identically to a real,
        # fully-matched frame. `consumed=<c>/<n>` with c < n is how a
        # partial match stays visibly partial.
        for _mod, point, hook_fn, encode, _decode, fields in _CASES:
            with self.subTest(point=point):
                clean = encode(fields)
                trailing = clean + b"\xaa" * 37
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    hook_fn(session=object(), payload=trailing)
                console = stderr.getvalue()
                self.assertNotIn("UNPARSED", console)
                self.assertIn(f"consumed={len(clean)}/{len(trailing)}", console)
                self.assertNotIn(f"consumed={len(trailing)}/{len(trailing)}", console)

    def test_garbage_of_every_wrong_length_is_unparsed_never_raises(self):
        for _mod, point, hook_fn, _encode, _decode, _fields in _CASES:
            for payload in (b"", b"\x00", b"\xff" * 3, b"\xff" * 200):
                with self.subTest(point=point, length=len(payload)):
                    stderr = io.StringIO()
                    with contextlib.redirect_stderr(stderr):
                        result = hook_fn(session=object(), payload=payload)
                    self.assertIsNone(result)
                    console = stderr.getvalue()
                    self.assertIn("UNPARSED", console)
                    self.assertIn(f"len={len(payload)}", console)

    def test_a_non_bytes_payload_is_refused_loudly_not_raised(self):
        for _mod, point, hook_fn, *_rest in _CASES:
            with self.subTest(point=point):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    result = hook_fn(session=object(), payload="not bytes")
                self.assertIsNone(result)
                console = stderr.getvalue()
                self.assertIn("UNPARSED", console)
                self.assertIn("bad_payload_type=str", console)

    def test_a_bytearray_and_memoryview_payload_both_decode(self):
        _mod, _point, hook_fn, encode, _decode, fields = _CASES[0]
        payload = encode(fields)
        for wrapped in (bytearray(payload), memoryview(payload)):
            with self.subTest(type=type(wrapped).__name__):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    hook_fn(session=object(), payload=wrapped)
                self.assertNotIn("UNPARSED", stderr.getvalue())

    def test_console_output_is_always_ascii(self):
        cases_with_unicode_field = [
            (
                lane_ui_party_wire_log._on_party_invite,
                ui_party_wire.encode_party_invite_payload(
                    ui_party_wire.PartyInviteFields(1, 2, "การ")
                ),
            ),
        ]
        for hook_fn, payload in cases_with_unicode_field:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                hook_fn(session=object(), payload=payload)
            stderr.getvalue().encode("ascii")
        for _mod, _point, hook_fn, *_rest in _CASES:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                hook_fn(session=object(), payload=b"\xff\xfe\x00garbage")
            stderr.getvalue().encode("ascii")

    def test_an_unparsed_hex_line_is_capped_not_written_unbounded(self):
        _mod, _point, hook_fn, *_rest = _CASES[0]
        huge = b"\xab" * 2_000_000
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            hook_fn(session=object(), payload=huge)
        console = stderr.getvalue()
        self.assertLess(len(console), 1_000)
        self.assertIn(f"len={len(huge)}", console)

    def test_no_field_is_named_with_guessed_meaning(self):
        # Letter 1120 nonclaim (2): CALL_UNCLASSIFIED for all eight classes.
        # A decoded line must only ever show positional field names.
        forbidden = (
            "recipient", "subject", "sender", "invite_target", "party_id",
            "friend_id", "trade_target", "gold", "price",
        )
        for _mod, point, hook_fn, encode, _decode, fields in _CASES:
            payload = encode(fields)
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                hook_fn(session=object(), payload=payload)
            console = stderr.getvalue().lower()
            for word in forbidden:
                with self.subTest(point=point, word=word):
                    self.assertNotIn(word, console)


if __name__ == "__main__":
    unittest.main()
