"""LANE-UI: report-only subscribers for ``PartyInviteVital`` (``0x37B1``) /
``PartyCmdVital`` (``0x2466``) -- the two party-family classes wired onto
the shared dispatch table in ``runtime.py``'s
``_FRIEND_MAIL_PARTY_TRADE_DISPATCH`` (CORE-REQUEST
``pf_bridge/notes_to_chief/20260904_1120``, call site landed by chief round
``cool-johnson-7qcsux``/R339, letter ``20260904_1522``, which explicitly
hands the ``lane_hooks/lane_ui_*.py`` registration to LANE-UI without a
further CORE-REQUEST).

WHAT THIS DOES NOT CLAIM.  Letter 1120 nonclaim (2) stands: knowing a
frame's wire SHAPE is not knowing its caller/verb SEMANTICS.  Nobody has
traced which client action sends either of these two classes, or what a
real ``field1_u8``/``field2_u64``/``field3_wstring`` value means for a
party invite or a party command.  This module decodes with
``ui_party_wire``'s already-proven field shape and prints the raw
positional values -- it invites no one to a party, forms no party, and
touches no store row.  Same shape and same limit as
``lane_a_enter_instance_log.py``'s own module docstring.

IT SENDS NOTHING.  No frame is composed, no bytes are queued, nothing is
returned -- ``lane_hooks.fire()`` is report-only by construction and this
module stays inside that shape.

``UNPARSED`` means the payload did not match ``ui_party_wire``'s pinned
field shape for that class (wrong tag, wrong width, or truncated) -- the
raw hex is printed, capped, so the next round works from bytes rather than
from this module's opinion of them.

``consumed=<c>/<n>`` ON EVERY DECODED LINE, NOT JUST A BARE "decoded".
pf-adversary (this round) measured the gap: none of ``ui_party_wire.py``'s
``decode_*`` functions check that a successful parse consumed the WHOLE
payload -- a match against the first ``c`` bytes returns success even when
``n - c`` bytes of unexplained trailer follow, and a bare "decoded field...
bytes_out=0" line would have looked identical to a real, fully-matched
frame. Re-encoding the decoded fields with ``ui_party_wire``'s own
``encode_*`` (a proven lossless round trip of the exact bytes consumed --
every tag+value write is a fixed-width ``struct.pack`` or a length-prefixed
string, so two decodes of the same value always re-encode to the same
bytes) recovers ``c`` without touching that module. ``c == n`` is the
everyday, fully-matched case; ``c < n`` means this class may have more
fields than currently modeled and the next round should treat that
specific capture as PARTIAL, not proven.
"""
from __future__ import annotations

import sys

from . import console_safe, hook
from .. import ui_party_wire as wire

production_allowed = True

_POINT_INVITE = "vital_inbound_party_invite_vital"
_POINT_CMD = "vital_inbound_party_cmd_vital"
_TOKEN_INVITE = "LANE_UI_PARTY_INVITE"
_TOKEN_CMD = "LANE_UI_PARTY_CMD"

# Same cap and same reason as lane_a_enter_instance_log.py's own
# _MAX_HEX_BYTES: the payload is client-supplied off the shared dispatch
# path, and a malformed/hostile one must not buy an unbounded console line.
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


def _consumed_of(raw_len: int) -> str:
    """``consumed=<c>/<n>`` fragment -- see module docstring. ``c`` is filled
    in by the caller (the length of the decoded fields' own round-trip
    encoding); this only formats the ``/n`` half so every call site spells
    the fragment identically."""
    return f"/{raw_len}"


@hook("vital_inbound_party_invite_vital")
def _on_party_invite(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_INVITE, payload)
    if raw is None:
        return
    fields = wire.decode_party_invite_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_INVITE, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_party_invite_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_INVITE} decoded consumed={consumed}{_consumed_of(len(raw))}"
            f" field1_u8={fields.field1_u8}"
            f" field2_u64={fields.field2_u64}"
            f" field3_wstring={fields.field3_wstring!r} bytes_out=0"
        ),
        file=sys.stderr,
    )


@hook("vital_inbound_party_cmd_vital")
def _on_party_cmd(session: object = None, payload: object = b"", **_ignored) -> None:
    raw = _as_bytes(_TOKEN_CMD, payload)
    if raw is None:
        return
    fields = wire.decode_party_cmd_payload(raw)
    if fields is None:
        print(console_safe(_hex_line(_TOKEN_CMD, raw)), file=sys.stderr)
        return
    consumed = len(wire.encode_party_cmd_payload(fields))
    print(
        console_safe(
            f"{_TOKEN_CMD} decoded consumed={consumed}{_consumed_of(len(raw))}"
            f" field1_u8={fields.field1_u8}"
            f" field2_u64={fields.field2_u64} bytes_out=0"
        ),
        file=sys.stderr,
    )
