"""Pure unit tests for ``ui_trade_wire.py`` -- ``TradeInviteVital``
(``0x3700``) encode/decode.

Not wiring tests -- see ``ui_social_wire.py``'s module docstring. This is
only the trade INVITE class; ``TradeCmdVital`` is out of scope (see
``ui_trade_wire.py``'s module docstring) and has no module here.
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

    def test_shares_wire_shape_with_party_invite_but_not_the_type(self):
        # Same tag sequence (u8, u64, untagged wstring) as PartyInviteVital
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
