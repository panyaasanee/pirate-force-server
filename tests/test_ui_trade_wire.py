"""Pure unit tests for ``ui_trade_wire.py`` -- ``TradeInviteVital``
(``0x3700``) encode/decode.

Not wiring tests -- nothing here asserts anything about ``runtime.py``
dispatch. This is only the trade INVITE class; ``TradeCmdVital`` is out of
scope (see ``ui_trade_wire.py``'s module docstring) and has no module
here. STALE CLAIM CORRECTED round `rqwwp8` (pf-adversary): this docstring
previously pointed to ``ui_social_wire.py``'s module docstring for a
"nothing here is wired" claim -- ``runtime.py`` imports
``TRADE_INVITE_VITAL_ID`` and dispatches real inbound frames to
``lane_hooks/lane_ui_trade_wire_log.py`` (``production_allowed = True``,
report-only, ``bytes_out=0`` -- see ``ui_trade_wire.py``'s own
``TradeInviteFields`` docstring for the wiring citation); this file was
never updated to say so.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import ui_party_wire as party  # noqa: E402
from pirateforce_foundation import ui_trade_wire as trade  # noqa: E402


class TradeInviteWireTests(unittest.TestCase):
    def test_round_trip(self):
        fields = trade.TradeInviteFields(
            field1_u8=1, field2_u64=99, field3_wstring="Reads",
        )
        payload = trade.encode_trade_invite_payload(fields)
        decoded = trade.decode_trade_invite_payload(payload)
        self.assertEqual(decoded, fields)

    def test_truncated_payload_fails_closed(self):
        payload = trade.encode_trade_invite_payload(
            trade.TradeInviteFields(1, 2, "hello")
        )
        self.assertIsNone(trade.decode_trade_invite_payload(payload[:-1]))

    def test_trailing_bytes_after_a_full_match_fail_closed(self):
        # COO-DECISION 20260904_1745 item 2 -- see test_ui_party_wire.py's
        # equivalent test for the full rationale.
        clean = trade.encode_trade_invite_payload(
            trade.TradeInviteFields(1, 2, "hello")
        )
        for extra in (b"\xaa", b"\xaa" * 37):
            with self.subTest(extra_len=len(extra)):
                self.assertIsNone(
                    trade.decode_trade_invite_payload(clean + extra)
                )

    def test_shares_wire_shape_with_party_invite_but_not_the_type(self):
        # Same tag sequence (u8, u64, tagged wstring 0x48) as PartyInviteVital
        # -- confirm the BYTES are identical for identical field values,
        # while the two dataclasses remain distinct Python types (nothing
        # proves the two classes share a meaning, only a shape; see this
        # module's docstring).
        shared_values = (1, 2, "same shape")
        trade_payload = trade.encode_trade_invite_payload(
            trade.TradeInviteFields(*shared_values)
        )
        party_payload = party.encode_party_invite_payload(
            party.PartyInviteFields(*shared_values)
        )
        self.assertEqual(trade_payload, party_payload)
        self.assertIsNot(trade.TradeInviteFields, party.PartyInviteFields)


if __name__ == "__main__":
    unittest.main()
