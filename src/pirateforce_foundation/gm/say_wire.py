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

# The vital_version byte that `channel_message_hypothesis.
# make_channel_message_response` hardcodes for EVERY channel on serializer
# 0x65AD40 -- it is the middle element of the one tuple it hands
# `legacy.make_runtime_vitals`, and v141 writes it as `u8tag(0x0B, ...)` per
# nested vital (`current/pf_login_game_server_v141.py:702-704`, re-derived at
# this commit).  Named here, not because this lane may change it (that module
# is another lane's proven work and is NOT in this lane's write zone), but
# because the gate below has to be able to say WHICH byte it is gating.
CHANNEL_CODEC_VITAL_VERSION = 0

# !! THIS LANE'S SEND GATE FOR 0x9F2C.  `None` means: no vital_version byte
# has been proven for THIS vital, so no GM COMMAND may put a `say` frame on a
# real socket.
#
# THAT IS A LANE-LOCAL PROPERTY, NOT A REPO-WIDE ONE, and the first draft of
# this comment overstated it (pf-adversary, this round, enumerated every
# caller rather than trusting the sentence).  `make_channel_message_response`
# has exactly two call sites in `src/`: this module, and
# `runtime.py:2126-2147`, which is NOT gated by this constant.  Booted with
# `--channel-message-hypothesis-scenario .../channel_sweep.json`, that path
# already composes a real `Channel_GMGlobalMessageVital` frame carrying the
# very byte RE-132 is being asked to prove, and the v141 serve loop sends it
# (`v141:7755`).  So the honest claim is: no GM command can send one, and
# nothing in this lane can open that.
#
# WHICH MEANS RE-132 IS NOT THE ONLY INSTRUMENT AIMED AT THIS BYTE.
# `docs/HYPOTHESIS_LEDGER.json` and `docs/FUNCTIONAL_COVERAGE.json` both name
# **GT-016** as the queued attended test that sends all five shared-serializer
# channels, GMGlobal included, to a real client and reads what renders -- a
# client-observable measurement, which is a STRONGER layer than RE-132's
# static constructor read.  If GT-016 runs first and the client accepts the
# frame, that answers this byte from the higher rung and RE-132 becomes a
# corroboration rather than the gate's key.  Whoever opens this constant
# should check GT-016's state first.
#
# It is deliberately shaped like
# `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` and read at the same
# place -- the module that returns an ACTION, not this one, which stays a
# pure byte builder its own tests can exercise.
#
# WHAT IS PROVEN, AND IT IS A LOT (do not re-derive):
#   CHAT-CHANNEL-001 (`reports/PF_CHAT_CHANNEL001_CHANNEL_FAMILY_AND_ROUTING_
#   STATIC_20260818.md`, byte-exact static read) pins this channel's 16-bit
#   wire id 0x9F2C, pins that five channels share serializer 0x65AD40
#   wire-IDENTICALLY, and pins the field order and the `0x48` + u32-length
#   UTF-16LE wstring codec.  `channel_message_hypothesis.py` then reproduces
#   real captured GT-006 payload bytes and the CHAT-ECHO-001/002 pinned PC and
#   frame hashes exactly.  None of that is in question here.
#
# WHAT IS NOT PROVEN, AND IT IS EXACTLY ONE BYTE:
#   every one of those three byte-level cross-checks composes `channel_id ==
#   0xAC52` (Channel_LocalTalkMessageVital).  They pin the PAYLOAD codec,
#   which the family shares; they say nothing about the vital_version this
#   family's OTHER class ids are accepted with, because that byte is not part
#   of the payload -- it sits in the envelope, one per nested vital.
#   This lane has measured that byte four times and it is per-vital with no
#   project default: 0x5A19 -> 0 and ForcePos -> 0 and TeleportVital -> 4
#   (RE-105 / RE-129, from the client's own constructors), SelectActor -> 10
#   (server source, a different layer).  Inheriting 0xAC52's byte for 0x9F2C
#   because the payload codec is shared is precisely the reasoning shape that
#   produced the hardcoded `1` GT-101 measured as fatal on a real client
#   (modal `ErrorData=23065`, connection halted, socket closed).
#   `RE-132` (filed this round, via chief) asks for this vital's constructor
#   byte using the recipe RE-105/RE-129 already ran twice.
#
# !! WHO GETS TO OPEN THIS, AND IT IS NOT THIS LANE ALONE.
#   `teleport_wire`'s constant has an external lock (COO-DECISION
#   20260828_2130 + `tests/test_gm_force_pos_version_lock.py`).  This one had
#   nothing but the lane's own test -- and the release-day note below tells a
#   future round to edit that very test, so "who else has to agree" answered
#   itself with "nobody".  pf-adversary asked the question; the lane's answer,
#   pending COO ([สมมติของสาย GM - รอ COO ยืนยัน], letter filed round
#   `w8hnu9`), is that TWO conditions outside this lane must hold first:
#     (A) the per-connection identity question at `runtime.py:4765-4774` is
#         resolved -- while every connection shares one `--token`, opening
#         this gate hands `/say` to whoever connects, and the allowlist that
#         is supposed to stop them cannot tell two humans apart; and
#     (B) something has established that the client's GMGlobal branch RENDERS
#         a received frame (GT-016, or RE-132 question 3).  A byte-perfect
#         frame into a branch that draws nothing looks exactly like a wrong
#         version byte from the tester's chair.
#
# RELEASE DAY, IN ORDER (which branch is likelier is NOT known -- nothing in
# this repo measures it, which is the whole reason RE-132 exists):
#   0. (A) and (B) above hold, and COO has said the flip is allowed.
#   1. RE-132 answers with a byte V for Channel_GMGlobalMessageVital.
#   2. If V == CHANNEL_CODEC_VITAL_VERSION, set this constant to V.  The
#      codec already emits that byte, so nothing else changes.
#   3. If V != CHANNEL_CODEC_VITAL_VERSION, STOP: setting this constant would
#      open a gate onto a frame the codec cannot build.  The version-mismatch
#      refusal in `gm/chat_command_action.py` catches that, but the fix is a
#      letter to `channel_message_hypothesis.py`'s owning lane asking for a
#      version parameter -- NOT a second codec in this lane's zone (that is
#      the round `rounds/GM_20260827_1415_broadcast-wire-attempted-and-
#      retracted.md` already tried and retracted).
#   4. Either way, release day also edits ONE test: `tests/test_gm_say_
#      action.py`'s `SayVersionGateTests::test_the_shipped_constant_is_still_
#      none_so_no_bytes_can_go_out` asserts this constant is None
#      unconditionally, on purpose.  (Unlike ForcePos, whose release day edits
#      TWO test files -- there is no second assertion on this one, because
#      this lane owns `say_wire.py`'s suite outright and did not need a
#      separate lock file for it.)
GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED: int | None = None


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
    if type(args) is not tuple:
        # GmCommand.args is typed tuple[str, ...] (gm/commands.py) -- every
        # legitimate caller, parse_gm_command included, produces a plain
        # tuple. A blacklist of individually-discovered wrong shapes (None,
        # a set, a dict, a str/bytes scalar) is unbounded and was twice
        # defeated by a shape that happened not to raise (a string-keyed
        # dict, then an integer-keyed one). An isinstance(args, tuple)
        # allowlist closed those but was itself defeated by a tuple
        # *subclass* overriding __len__/__getitem__ to raise something
        # other than this module's own error type -- exactly the
        # "regardless of source, hand-built GmCommand" threat model this
        # docstring already claims to defend against, since nothing in
        # GmCommand (a plain frozen dataclass, gm/commands.py) stops a
        # caller from constructing one. Requiring the exact type, not an
        # isinstance match, rejects every subclass outright -- a real tuple
        # can never raise on len()/indexing, so there is no dunder left to
        # lie through.
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
    except (ValueError, RuntimeError) as exc:
        # `RuntimeError` added round `w8hnu9` after pf-adversary: this clause
        # caught only `ValueError`, but every drift check inside
        # `make_channel_message_response` raises `RuntimeError`
        # (`channel_message_hypothesis.py:547/549/555/570/572` -- composed PC
        # size drift, payload mismatch, re-decode mismatch, pinned-composition
        # drift), so a bare `RuntimeError` could escape a function whose
        # docstring promises every failure surfaces as `SayWireError`.  Not
        # reachable from a typed `/say` today (the pinned checks only fire for
        # the probe bodies), but `gm/chat_command_action._say_action` is the
        # first caller that turns an escape into a wrong event name.
        raise SayWireError(
            f"say command rejected by the channel wire codec: {exc}"
        ) from exc
