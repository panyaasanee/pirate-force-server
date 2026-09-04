"""LANE-UI: report-only subscriber for ``TradeInviteVital`` (``0x3700``) --
see ``lane_ui_party_wire_log.py``'s module docstring for the shared shape,
limits, and the CORE-REQUEST/letter chain this belongs to.

NOT ``TradeCmdVital``.  Same distinction ``ui_trade_wire.py`` draws for
itself: this is only the invite class this letter resolved; the class that
would actually execute an exchange is separately tracked
(``notes_to_chief/20260904_0621``) and out of scope here.

Field shape decoded here comes from ``ui_trade_wire.py``, already proven
and on ``main``.

``consumed=<c>/<n>`` on the decoded line -- see
``lane_ui_party_wire_log.py``'s module docstring for why (pf-adversary,
this round: a decode success with unconsumed trailing bytes must never
read identically to a fully-matched frame).
"""
from __future__ import annotations

import sys

from . import console_safe, hook
from .. import ui_trade_wire as wire

production_allowed = True

_TOKEN = "LANE_UI_TRADE_INVITE"

_MAX_HEX_BYTES = 96


def _hex_line(payload: bytes) -> str:
    shown = payload[:_MAX_HEX_BYTES]
    truncated = "+" if len(payload) > len(shown) else ""
    return f"{_TOKEN} UNPARSED len={len(payload)} hex={shown.hex()}{truncated} bytes_out=0"


@hook("vital_inbound_trade_invite_vital")
def _on_trade_invite(session: object = None, payload: object = b"", **_ignored) -> None:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        raw = bytes(payload)
    else:
        print(
            console_safe(
                f"{_TOKEN} UNPARSED len=0 hex= bytes_out=0"
                f" bad_payload_type={type(payload).__name__}"
            ),
            file=sys.stderr,
        )
        return
    fields = wire.decode_trade_invite_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_trade_invite_payload(fields))
    print(
        console_safe(
            f"{_TOKEN} decoded consumed={consumed}/{len(raw)}"
            f" field1_u8={fields.field1_u8}"
            f" field2_u64={fields.field2_u64}"
            f" field3_wstring={fields.field3_wstring!r} bytes_out=0"
        ),
        file=sys.stderr,
    )
