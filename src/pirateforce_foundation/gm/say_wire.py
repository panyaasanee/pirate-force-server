"""Bridges a parsed GM-003 `say` command into a real outbound
`Channel_GMGlobalMessageVital` (0x9F2C) wire frame.

`gm/commands.py` parses `say <message...>` into a `GmCommand` but does not
build a wire frame for it -- its own docstring says wiring `say` needs the
0x9F2C `Channel_GMGlobalMessageVital` codec, and left that unbuilt. The
retracted broadcast-wire round (`rounds/GM_20260827_1415_broadcast-wire-
attempted-and-retracted.md`) found the reason this lane must NOT build a
second, competing wire codec for that vital: `channel_message_hypothesis.py`
(CHAT-CHANNEL-001/002, committed 2026-08-18, byte-exact static read of the
client binary plus a three-way hash cross-check against a real captured
frame) already owns the proven encoder for `Channel_GMGlobalMessageVital`
and the four sibling channels that share serializer `0x65AD40` -- the
`gm/broadcast_wire.py` this lane wrote and deleted in that round assumed an
untagged wstring pair straight off `PF_SERIALIZER_FIELDS.tsv`'s coarser tag
column; the real wire carries a `0x48` tag + u32 byte-length header per
string that only `channel_message_hypothesis.py` had already proven.

This module therefore imports that encoder rather than re-deriving it
(GM-003's own rule, notes_to_chief 20260826_1630: reuse another lane's
proven work via import, never by copying its logic into this lane's zone).
It adds no new wire knowledge -- it only adapts a parsed `GmCommand` to the
existing `encode_channel_message`/`make_channel_message_response` call
shape, the same role `gm/warp_executor.py` plays for `gm/teleport_wire.py`.

This module does not read off a live socket, does not track player state,
and does not send anything -- it returns frame bytes for a caller to send,
same posture as `gm/warp_executor.py`. Wiring a real send is CORE-REQUEST
territory (see docs/GM_LANE.md).

`pf-adversary` (this round) found two gaps against the "regardless of
source" contract this module's docstring already claimed:

1. `gm/commands.py`'s `MAX_SAY_MESSAGE_LENGTH` cap is enforced only inside
   `parse_gm_command`, by that module's own comment specifically so a
   "fat-fingered or hostile `say`" cannot grow unbounded "once execution is
   wired in" -- this module IS that execution wiring, and a hand-built
   `GmCommand` bypasses `parse_gm_command` entirely, so the cap must be
   re-checked here too, not merely inherited by convention.
2. `command.args` was indexed/measured with plain `len()`/`[0]`, which
   raises a bare `TypeError`/`KeyError`/`IndexError` (never `SayWireError`)
   for an `args` container of the wrong *shape* (not `None`, not missing
   `__len__`, not a mapping) -- the checked-in tests only ever varied
   `args`' *values*, never its *shape*, so this gap shipped asserted-safe
   without being exercised. `gm/warp_executor.py` has the identical gap
   (confirmed, not fixed here -- out of this module's write scope for this
   round; see docs/GM_LANE.md for the follow-up note).
"""
from __future__ import annotations

from ..channel_message_hypothesis import (
    SHARED_SERIALIZER_CHANNEL_IDS,
    make_channel_message_response,
)
from .commands import MAX_SAY_MESSAGE_LENGTH, GmCommand

GM_GLOBAL_CHANNEL_ID = SHARED_SERIALIZER_CHANNEL_IDS["Channel_GMGlobalMessageVital"]

# Every captured GT-006 frame on this shared serializer has carried an empty
# speaker (channel_message_hypothesis.py docstring); this module does not
# invent a GM display name, so a caller who wants one must pass it.
DEFAULT_SPEAKER = ""


class SayWireError(ValueError):
    """A `say` command cannot be composed into a `Channel_GMGlobalMessageVital`
    frame as given."""


def make_say_broadcast_frame(
    legacy, command: GmCommand, *, speaker: str = DEFAULT_SPEAKER,
) -> tuple[bytes, bytes]:
    """Build a server->client `Channel_GMGlobalMessageVital` frame for a
    parsed `say` command.

    `command` is re-validated here regardless of whether it came from
    `parse_gm_command` -- same policy `gm/warp_executor.py` follows, and for
    the same reason: `docs/GM_LANE.md` commits to accepting a `GmCommand`
    "regardless of source." Every failure surfaces as `SayWireError`, never
    a bare `ValueError`/`TypeError`/`KeyError`/`IndexError`.
    """
    if command.name != "say":
        raise SayWireError(
            f"make_say_broadcast_frame only applies to say commands, got {command.name!r}"
        )
    args = command.args
    try:
        arg_count = len(args)
    except TypeError as exc:
        raise SayWireError(f"say command args must be a sequence, got {args!r}") from exc
    if arg_count != 1:
        raise SayWireError("say <message> must carry exactly one message argument")
    try:
        body = args[0]
    except (TypeError, KeyError, IndexError) as exc:
        raise SayWireError(f"say command args must be indexable, got {args!r}") from exc
    if not isinstance(body, str):
        raise SayWireError(f"say message must be a str, got {body!r}")
    if len(body) > MAX_SAY_MESSAGE_LENGTH:
        raise SayWireError(
            f"say message exceeds {MAX_SAY_MESSAGE_LENGTH} characters "
            f"({len(body)} given)"
        )
    if not isinstance(speaker, str):
        raise SayWireError(f"speaker must be a str, got {speaker!r}")
    try:
        return make_channel_message_response(
            legacy, GM_GLOBAL_CHANNEL_ID, speaker, body,
        )
    except ValueError as exc:
        raise SayWireError(
            f"say command rejected by the channel wire codec: {exc}"
        ) from exc
