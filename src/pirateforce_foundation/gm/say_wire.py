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

`pf-adversary` (say-wire round) found two gaps against the "regardless of
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
   without being exercised.

The warp-executor args-shape follow-up round then fixed the identical gap
in `gm/warp_executor.py` and found the `say_wire.py`-style three-type catch
itself (`TypeError`/`KeyError`/`IndexError`) still left two gaps open,
flagged in `docs/GM_LANE.md` as this module's own follow-up: (a) a custom
`__len__`/`__getitem__` raising anything outside those three types (e.g.
`AttributeError`, `ValueError`) would still leak past this module's own
"every failure surfaces as `SayWireError`" promise; (b) a `str`/`bytes`
scalar of length 1 (e.g. `"x"`) passes `len(args) == 1` and is positionally
indexable, so it would be read as a real one-element args sequence instead
of being refused as the wrong container shape.

A later round (`say-wire args-shape follow-up`, not the warp-executor round
itself) first applied that same blacklist-style fix here (broad `except
Exception` plus an `isinstance(args, (str, bytes))` reject), then
`pf-adversary` broke it again the same day: an integer-keyed `dict` (e.g.
`{0: "hello"}`) is exactly the "mapping" shape `docs/GM_LANE.md` already
names as one of the three canonical wrong shapes (`None`, a `set`, a
`dict`), yet `len(d)` and `d[0]` both succeed normally for it -- no
exception is ever raised, so neither the `str`/`bytes` guard nor either
`except Exception` clause fires, and a hand-built `GmCommand` with such a
dict silently builds a real frame. `warp_executor.py` has the identical
gap for the same reason. Enumerating one more forbidden shape every time
adversary finds one that happens not to raise is an unbounded blacklist
against a `tuple[str, ...]`-typed field (see `gm/commands.py`'s
`GmCommand.args` annotation) with exactly one legitimate shape -- so this
module now asserts that shape directly (`isinstance(args, tuple)`) instead
of continuing to chase individual non-tuple shapes that happen not to
raise. Every non-`tuple` `args` -- `None`, a `set`, a `dict` of any key
type, a `str`/`bytes` scalar, a `bytearray`, a custom object, a `list` --
is refused up front, before `len()`/indexing ever runs.
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
    if not isinstance(args, tuple):
        # GmCommand.args is typed tuple[str, ...] (gm/commands.py) -- every
        # legitimate caller, parse_gm_command included, produces a tuple.
        # A blacklist of individually-discovered wrong shapes (None, a set,
        # a dict, a str/bytes scalar) is unbounded and was twice defeated by
        # a shape that happened not to raise (a string-keyed dict, then an
        # integer-keyed one) -- asserting the one legitimate shape directly
        # closes the whole class at once, including shapes not yet tried
        # (bytearray, memoryview, a list).
        raise SayWireError(f"say command args must be a tuple, got {args!r}")
    if len(args) != 1:
        raise SayWireError("say <message> must carry exactly one message argument")
    body = args[0]
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
