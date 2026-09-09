"""LANE-UI: report-only subscribers for ``Community_RequestBeFriendVital``
(``0xB9E9``) / ``Community_RemoveFriendVital`` (``0x98A1``) -- see
``lane_ui_party_wire_log.py``'s module docstring for the shared shape,
limits, and the CORE-REQUEST/letter chain this belongs to
(``pf_bridge/notes_to_chief/20260904_1120`` /
``20260904_1522``). Repeated in full there rather than cross-imported here,
same reasoning ``lane_a_enter_instance_log.py`` gives for not sharing code
with its own trigger-vital sibling: one broken file must never take another
lane point down with it (``lane_hooks/__init__.py`` docstring, layer 2).

Field shapes decoded here come from ``ui_friend_wire.py``, already proven
and on ``main``. Nothing here guesses which client action sends either
class, or what a friend-request/friend-removal field value means -- letter
1120 nonclaim (2) stands.

``consumed=<c>/<n>`` on every decoded line -- see
``lane_ui_party_wire_log.py``'s module docstring for why (pf-adversary,
this round: a decode success with unconsumed trailing bytes must never
read identically to a fully-matched frame).
"""
from __future__ import annotations

import sys

from . import console_safe, hook
from .. import ui_friend_wire as wire

production_allowed = True

_TOKEN_REQUEST = "LANE_UI_FRIEND_REQUEST"
_TOKEN_REMOVE = "LANE_UI_FRIEND_REMOVE"

_MAX_HEX_BYTES = 96

# THE DECODED LINE NEEDS THE SAME CAP THE UNPARSED LINE ALWAYS HAD, and
# pf-adversary (round `asw0n3`, D5) measured why: the only variable-width
# field on either of these two classes is `field2_wstring`, this file
# printed it with `!r` and NO bound, and `runtime.py` fires this hook
# BEFORE `ui_dispatch.answer()` -- so neither the login gate nor the
# per-session answer allowance is between a peer and this print.  A peer
# that never logged in could therefore drive roughly 2.5 stderr bytes per
# payload byte (astral characters, `repr` escaping each one), once per
# frame, forever, bounded only by `recv_frame`'s u32 length, which is
# 4 GiB.  96 characters is chosen to match `_MAX_HEX_BYTES` rather than
# to fit a name: this file may not reason about what the field MEANS
# (letter `20260904_1120` nonclaim (2)), so it may not argue "no real
# name is longer than this".  It is a console budget, not a semantic
# claim, and the `+` says a value was cut exactly as the hex line does.
_MAX_TEXT_CHARS = 96


def _clip(value: str) -> str:
    """``repr`` of at most ``_MAX_TEXT_CHARS`` characters, marked if cut.

    The clip is applied to the STRING and the repr is taken after, so
    the bound holds in characters of the value; ``repr`` still adds its
    own quoting and escapes, which is why this is a budget rather than a
    byte count.  ``console_safe`` folds what survives.
    """
    shown = value[:_MAX_TEXT_CHARS]
    return f"{shown!r}{'+' if len(value) > len(shown) else ''}"


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


@hook("vital_inbound_community_request_be_friend_vital")
def _on_request_be_friend(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_REQUEST, payload)
    if raw is None:
        return
    fields = wire.decode_request_be_friend_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_REQUEST, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_request_be_friend_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_REQUEST} decoded consumed={consumed}/{len(raw)}"
            f" field1_u64={fields.field1_u64}"
            f" field2_wstring={_clip(fields.field2_wstring)}"
            f" field3_u8={fields.field3_u8} bytes_out=0"
        ),
        file=sys.stderr,
    )


@hook("vital_inbound_community_remove_friend_vital")
def _on_remove_friend(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_REMOVE, payload)
    if raw is None:
        return
    fields = wire.decode_remove_friend_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_REMOVE, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_remove_friend_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_REMOVE} decoded consumed={consumed}/{len(raw)}"
            f" field1_u64={fields.field1_u64}"
            f" field2_u64={fields.field2_u64}"
            f" field3_u8={fields.field3_u8} bytes_out=0"
        ),
        file=sys.stderr,
    )
