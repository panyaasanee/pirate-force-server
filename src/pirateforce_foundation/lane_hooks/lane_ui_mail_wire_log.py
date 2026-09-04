"""LANE-UI: report-only subscribers for ``Community_SendMailVital``
(``0x6E12``) / ``Community_GetMailContentVital`` (``0xAF60``) /
``Community_DeleteMailVital`` (``0x8183``) -- see
``lane_ui_party_wire_log.py``'s module docstring for the shared shape,
limits, and the CORE-REQUEST/letter chain this belongs to.

Field shapes decoded here come from ``ui_mail_wire.py``, already proven and
on ``main``. ``Community_SendMailVital`` has five wstring fields in a row;
per letter 1120 nonclaim (2) none of them is named "recipient"/"subject"/
"body" here -- that would be guessing meaning nothing has proven yet, the
same limit ``ui_mail_wire.py``'s own docstring states for itself.

``consumed=<c>/<n>`` on every decoded line -- see
``lane_ui_party_wire_log.py``'s module docstring for why (pf-adversary,
this round: a decode success with unconsumed trailing bytes must never
read identically to a fully-matched frame).
"""
from __future__ import annotations

import sys

from . import console_safe, hook
from .. import ui_mail_wire as wire

production_allowed = True

_TOKEN_SEND = "LANE_UI_MAIL_SEND"
_TOKEN_GET = "LANE_UI_MAIL_GET"
_TOKEN_DELETE = "LANE_UI_MAIL_DELETE"

_MAX_HEX_BYTES = 96


def _hex_line(token: str, payload: bytes) -> str:
    shown = payload[:_MAX_HEX_BYTES]
    truncated = "+" if len(payload) > len(shown) else ""
    return f"{token} UNPARSED len={len(payload)} hex={shown.hex()}{truncated} bytes_out=0"


def _as_bytes(token: str, payload: object) -> bytes | None:
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    print(
        console_safe(
            f"{token} UNPARSED len=0 hex= bytes_out=0"
            f" bad_payload_type={type(payload).__name__}"
        ),
        file=sys.stderr,
    )
    return None


@hook("vital_inbound_community_send_mail_vital")
def _on_send_mail(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_SEND, payload)
    if raw is None:
        return
    fields = wire.decode_send_mail_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_SEND, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_send_mail_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_SEND} decoded consumed={consumed}/{len(raw)}"
            f" field1_u64={fields.field1_u64}"
            f" field2_wstring={fields.field2_wstring!r}"
            f" field3_u64={fields.field3_u64}"
            f" field4_wstring={fields.field4_wstring!r}"
            f" field5_wstring={fields.field5_wstring!r}"
            f" field6_wstring={fields.field6_wstring!r}"
            f" field7_wstring={fields.field7_wstring!r}"
            f" field8_wstring={fields.field8_wstring!r}"
            f" field9_u8={fields.field9_u8} bytes_out=0"
        ),
        file=sys.stderr,
    )


@hook("vital_inbound_community_get_mail_content_vital")
def _on_get_mail_content(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_GET, payload)
    if raw is None:
        return
    fields = wire.decode_get_mail_content_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_GET, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_get_mail_content_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_GET} decoded consumed={consumed}/{len(raw)}"
            f" field1_u64={fields.field1_u64}"
            f" field2_u64={fields.field2_u64}"
            f" field3_u8={fields.field3_u8}"
            f" field4_wstring={fields.field4_wstring!r} bytes_out=0"
        ),
        file=sys.stderr,
    )


@hook("vital_inbound_community_delete_mail_vital")
def _on_delete_mail(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_DELETE, payload)
    if raw is None:
        return
    fields = wire.decode_delete_mail_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_DELETE, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_delete_mail_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_DELETE} decoded consumed={consumed}/{len(raw)}"
            f" field1_u64={fields.field1_u64}"
            f" field2_u64={fields.field2_u64}"
            f" field3_u8={fields.field3_u8} bytes_out=0"
        ),
        file=sys.stderr,
    )
