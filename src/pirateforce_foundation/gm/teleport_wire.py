"""Wire codec for ForcePos, CWarpResult and TeleportVital -- the three
messages RE-090 pinned as the field-level dependency GM-003's ``warp``
command needs before it can send anything real (see
``pf_bridge/notes_to_chief/20260826_2346_RE-090-RESULT-TELEPORT-FORCEPOS-WARP-FIELDS-PINNED.md``,
verdict PASS/DONE, T0-T3 all closed).

Layout is PROVEN at the byte level and pinned against the bridge repository:
    pf_bridge/external/PF_PROTOCOL_REGISTRY.tsv
    pf_bridge/external/PF_SERIALIZER_FIELDS.tsv

    ForcePos       serializer span [0x005E4250,0x005E427C) sha256
        7c6f6cb751692845d2eb5973fc9499a10dce4eda7caff5f80f82f968bc860e0d
    CWarpResult    serializer span [0x005E51F0,0x005E529D) sha256
        5e3acf83944a252a9c22b4cc42939589e2c1f373ee49881b782e66986c6db6a9
    TeleportVital  serializer span [0x005EB470,0x005EB609) sha256
        fbe813dbd1f9b94d87ee3c101867e8b12aaa36d69c08e68068c8ff06df990487
    TeleportVital  target-object span [0x005DF250,0x005DF2F9) sha256
        ec9a5421ad5304372e440ecbb35184d6e93624444a262b3058569a724df0b5ef
    TeleportVital  aux-object span [0x005DEF10,0x005DEFE9) sha256
        105bad91394ee1dc636ef80cfe3444c293a4114d5f371fafe3ebc76ccc049c93

[สมมติของสาย GM - รอ RE] What RE-090 proves stops at "this many fields, these
tags, this order, this width".  Fields whose meaning IS established are
carried over by name from elsewhere in this codebase (``scene_id``,
``scene_seq`` -- same crosswalk ``player_wire.py``/``npc_wire.py`` already
use, citing RE-077).  Everything else stays a positional name
(``field_0x10``, ``field_0x2c``, ...) exactly like ``gm/command_wire.py``
does for the same reason: RE-090 explicitly declines to say what those bytes
mean.  ``PF_FIELD_VALIDATION.tsv`` frame counts differ by message --
``ForcePos``/``CWarpResult`` are genuinely ``NOT_OBSERVED`` (0 frames each
direction), but ``TeleportVital`` has 132 real candidate frames per
direction at status ``A2_STATIC_OPEN`` (candidate-matched, not
parse-confirmed) -- do not read this docstring as "no capture data exists
for any of these three messages": a future round can and should run those
132 ``TeleportVital`` frames against this codec, in particular to settle
the ``TeleportTarget`` field-order question its docstring flags.  Do not
rename a positional field without a citation to the RE answer that proves
it.

Vital ids: RE-090 confirms these three names are registered in
``external/PF_PROTOCOL_REGISTRY.tsv`` (``name_va``/``id_global_va`` columns)
but that table does not carry a literal wire-id column the way
``VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv`` does for
``TeleportVital``/``TeleportCheckVital`` (``0x25A2``/``0x4477``) -- because
the client computes this id at runtime from the message name, not from a
stored constant.  ``VITAL_REGISTRY_FROM_CLIENT_BINARY_20260817.tsv``'s own
header states the formula:
``sum((i+1)*ord(c) for i,c in enumerate(name)) & 0xFFFF``.  Applying it to
``ForcePos`` and ``CWarpResult`` reproduces ``0x25A2``/``0x4477`` exactly for
the two names the file already lists (``TeleportVital``/``TeleportCheckVital``),
so the same formula is used here rather than treated as a new guess -- see
``docs/GM_LANE.md`` for the reproduction command.  [สมมติของสาย GM - รอ RE]:
that reproduction is this lane's own inference, not a disassembled call
site proving the client computes ``0x0E80``/``0x1BA4`` for the literal
strings ``"ForcePos"``/``"CWarpResult"`` -- it is one step less certain than
the PROVEN byte layout above, flagged the same way this codebase already
flags an unproven-but-safe-default value (see ``docs/GM_LANE.md``'s
``[ASSUMED - awaiting RE]`` state_wire note).

Direction is NOT proven for ``ForcePos`` or ``CWarpResult``
(``PF_FIELD_VALIDATION.tsv`` = NOT_OBSERVED both ways) -- this module
provides both an encoder and a decoder for each message and does not assume
which side sends which in the original protocol.  This lane's own use is
server->client (GM warp), which is a project design choice, not a claim
about original client/server behaviour.

This module builds/reads payload bytes only (the bytes after vital id and
version in the runtime-vital envelope).  It does not execute a warp, does
not touch player/world state, and does not read off a live socket --
wiring a real send is CORE-REQUEST territory (see docs/GM_LANE.md).
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

FORCE_POS_VITAL_ID = 0x0E80
CWARP_RESULT_VITAL_ID = 0x1BA4
TELEPORT_VITAL_ID = 0x25A2

# The vital VERSION byte, which is NOT part of the payload layout above and
# is NOT implied by it.  Layout being byte-proven (RE-090) says nothing about
# which version byte the client's reader will accept for this vital id.
#
# Why this is a named None and not a guess: RE-105 (STATIC-ON-BRIDGE,
# DONE/PASS, pf_bridge/notes_to_chief/20260827_1613_RE-105-RESULT-VITAL-
# VERSION-ZERO-GENERIC-MISMATCH-PATH.md) pinned the MECHANISM, and the
# mechanism is per-vital, not global: the generic VitalData collection reader
# at [0x005F3E20, 0x005F406D) does an EXACT-EQUALITY compare against
# message+0x10, and each vital's own prototype constructor stores that byte
# by direct `mov`.  For 0x5A19 that byte is 0 (gm/state_wire.py).  For
# SELECT_ACTOR_VITAL the value the working server has always sent is 10
# (pf_login_game_server_v141.py:2205, 2289) -- proven by every successful
# login this project has ever done.  Two known vitals, two different values:
# there is no project-wide default to fall back on.
#
# What a wrong guess costs, measured, not theorised: GT-101 (attended,
# OBSERVER_CONFIRMED 2026-08-27T14:39+07:00) sent 0x5A19 with an unproven
# version=1 and the real client raised a modal error naming the vital by id,
# HALTED the whole connection and closed the socket.  Not sending a frame is
# always safe; sending one with the wrong version kills the owner's session.
#
# SUPERSEDED 2026-08-28T22:30+07:00, kept because the reasoning above is
# still why this constant exists at all:
#     "So: None until RE-129 reads the byte the 0x0E80 prototype constructor
#      stores, by exactly the method RE-105 already succeeded with."
# RE-129 ANSWERED IT.  The byte is 0 (see the record constants below).  This
# constant is STILL None, and the reason changed -- read the next paragraph
# before touching it, because "RE-129 is open" is no longer true and is no
# longer what holds this line.
#
# !! HARD LOCK, NOT A TODO.  COO-DECISION 2026-08-28T21:30+07:00
# (pf_bridge/notes_to_chief/20260828_2130_COO-DECISION-position-ownership-
# after-gm-warp.md, answering this lane's ASK-COO of 19:05) ruled on who owns
# a character's position after a GM warp, and ruled it in the direction that
# keeps this line None:
#   * The owner is the position the CLIENT confirmed.  ForcePos is a REQUEST
#     that left the server, never evidence that anything moved.
#   * The server must NEVER write a position it did not observe.  The write
#     happens on the first TargetPos after the frame, not before it.
#   * The lock itself, rendered from the Thai original (not a quote -- the
#     letter's own words are `!! LOCK: ...` in Thai): do not change
#     FORCE_POS_VITAL_VERSION_CONFIRMED from None until that confirmed write
#     point is on main -- EVEN THOUGH RE-129 has already answered.  GT-128's
#     third precondition stays.
# So the release is no longer "one constant".  It is, in order: (a) chief
# wires the confirmed write point in runtime.py (CORE-REQUEST-GM-030, this
# lane's round `fo2lgh`; runtime.py is not this lane's zone), (b) COO lifts
# the lock, (c) this line becomes FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129.
# tests/test_gm_force_pos_version_lock.py enforces (a) mechanically -- this
# file cannot go non-None while runtime.py has no LIVE write point (the token
# must be a string inside a call there, not a comment saying it is coming) --
# because the last two times this lane left a rule standing on a sentence in a
# letter, the sentence lost.
#
# !! RELEASE DAY TOUCHES TWO TEST FILES, NOT ONE.  Step (c) also requires
# editing tests/test_gm_chat_command_action.py::VersionGateTests::test_the_
# shipped_constant_is_still_none_so_no_bytes_can_go_out, which asserts
# assertIsNone UNCONDITIONALLY and predates the lock file.  Left unedited it
# gives whoever lifts the lock three reds with no explanation -- pf-adversary
# (round `fo2lgh`) found that this file, docs/GM_LANE.md and CORE-REQUEST-GM-030
# all documented a release sequence that never mentioned it.
#
# Every caller that would put ForcePos bytes on a real wire MUST gate on this
# being not-None, the same way runtime.py:5168/5173 (re-derived at this
# commit, cb1a847; the pin read 5107 before chief's 0xAC52 merge) gates the
# 0x5A19 login frame on
# state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED.  Unit tests and
# decoders pass their own explicit version and are unaffected -- this
# constant gates SENDING, not composing.
FORCE_POS_VITAL_VERSION_CONFIRMED = None

# --- RE-129 RESULT, RECORDED BUT DELIBERATELY INERT ------------------------
# Source: pf_bridge/notes_to_chief/20260828_2009_RE-129-RESULT-VERSION-ZERO-
# HANDLER-NOOP.md (DONE/PASS, static-on-bridge, image GameClient.local.bin
# sha256 9627211412ac60d50ad189ce5a629443ce928ec23a9f8d219dfb2b157028b623).
#
# ForcePos: the prototype constructor [0x005E5170,0x005E51A2) does
# `xor ecx,ecx` then `mov byte ptr [eax+0x10],cl` at 0x005E5186 -- the version
# byte is written as literal 0 -- and the generic reader compares it with
# exact equality (`cmp cl,byte ptr [esi+0x10]` at 0x005F3EFC, passing only on
# the `je` at 0x005F3F01).  Same method RE-105 used for 0x5A19.
#
# TeleportVital: constructor [0x005E53D0,0x005E5459) does
# `mov byte ptr [esi+0x10],4` at 0x005E5425 -- version 4, not 0.  Recorded
# here as the FOURTH measured data point against ever assuming a project-wide
# default -- and the four are not all the same KIND of evidence, which is why
# they are listed with their layer rather than as one flat set:
#   * 0x5A19 -> 0, ForcePos -> 0, TeleportVital -> 4: static disassembly of the
#     CLIENT's own prototype constructors (RE-105, RE-129).
#   * SelectActor -> 10: a literal in the legacy SERVER source
#     (current/pf_login_game_server_v141.py:2205 and :2289), plus the inference
#     that every successful login this project has done accepted it.  A
#     different layer, and it is only cited because it points the same way.
#
# !! WHAT RE-129 DID *NOT* PROVE, and it is the more important half:
# the handler the client has REGISTERED for ForcePos is the complete body
# [0x00710440,0x00710445) = `mov al,1; ret 4`.  It reads no payload and
# writes no position.  A version-correct ForcePos frame is therefore NOT
# known to move anything on screen; RE-129's own nonclaim 3 says so.  The
# three f32 at +0x14/+0x18/+0x1C are position-shaped by offset, but the axis
# NAMES are still [สมมติของสาย GM - รอ RE]: no client crosswalk
# distinguishes first/second/third as x/y/z (RE-129 T2, bounded negative).
#
# These two names are a RECORD of a measurement, not a switch.  Nothing in
# this package may pass them to a frame builder or use them to gate a send;
# tests/test_gm_force_pos_version_lock.py parses every shipped module under
# src/ (tracked or not, THIS FILE INCLUDED) and fails if either name is ever
# READ -- pf-adversary bypassed an earlier version by adding a sender here,
# the one file that check skipped.  The switch is
# FORCE_POS_VITAL_VERSION_CONFIRMED above, and it is locked by COO.
FORCE_POS_VITAL_VERSION_PROVEN_BY_RE129 = 0
TELEPORT_VITAL_VERSION_PROVEN_BY_RE129 = 4

FORCE_POS_SPAN_SHA256 = (
    "7c6f6cb751692845d2eb5973fc9499a10dce4eda7caff5f80f82f968bc860e0d"
)
CWARP_RESULT_SPAN_SHA256 = (
    "5e3acf83944a252a9c22b4cc42939589e2c1f373ee49881b782e66986c6db6a9"
)
TELEPORT_VITAL_SPAN_SHA256 = (
    "fbe813dbd1f9b94d87ee3c101867e8b12aaa36d69c08e68068c8ff06df990487"
)
TELEPORT_TARGET_SPAN_SHA256 = (
    "ec9a5421ad5304372e440ecbb35184d6e93624444a262b3058569a724df0b5ef"
)
TELEPORT_AUX_SPAN_SHA256 = (
    "105bad91394ee1dc636ef80cfe3444c293a4114d5f371fafe3ebc76ccc049c93"
)

_TAG_U8 = 0x0B
_TAG_U16_A = 0x0F
_TAG_U16_B = 0x12
_TAG_U32_A = 0x14
_TAG_U32_B = 0x19
_TAG_U64 = 0x32
_TAG_F32 = 0x2A


class GmTeleportWireError(ValueError):
    """Raw bytes do not match the RE-090 pinned wire shape for one of
    ForcePos/CWarpResult/TeleportVital.
    """


# ---------------------------------------------------------------- ForcePos

@dataclass(frozen=True)
class ForcePosBody:
    """vec3-only body (RE-090 T0) -- ``ForcePos`` carries no presence bit,
    scene id, sequence, string or control field, unlike ``TeleportVital``.
    """

    x: float
    y: float
    z: float


def make_force_pos_payload(legacy, x: float, y: float, z: float) -> bytes:
    return legacy.f32tag(x) + legacy.f32tag(y) + legacy.f32tag(z)


def make_force_pos_frame(
    legacy, vital_version: int, x: float, y: float, z: float
) -> tuple[bytes, bytes]:
    payload = make_force_pos_payload(legacy, x, y, z)
    return legacy.make_runtime_vital(FORCE_POS_VITAL_ID, vital_version, payload)


def decode_force_pos(raw: bytes) -> ForcePosBody:
    buf = _as_bytes(raw)
    x, offset = _read_tag_f32(buf, 0)
    y, offset = _read_tag_f32(buf, offset)
    z, offset = _read_tag_f32(buf, offset)
    _require_exhausted(buf, offset, "ForcePos")
    return ForcePosBody(x, y, z)


# ------------------------------------------------------------- CWarpResult

@dataclass(frozen=True)
class CWarpResultBody:
    """Flat qword + vec3 + u16 body (RE-090 T1).  ``field_0x18``/
    ``field_0x2c`` meaning and natural direction are NOT proven -- the name
    ``Result`` is not evidence of direction (module docstring).
    """

    field_0x18: int
    x: float
    y: float
    z: float
    field_0x2c: int


def make_cwarp_result_payload(
    legacy, field_0x18: int, x: float, y: float, z: float, field_0x2c: int
) -> bytes:
    _require_u64(field_0x18, "field_0x18")
    _require_u16(field_0x2c, "field_0x2c")
    return (
        legacy.qwordtag(_TAG_U64, field_0x18)
        + legacy.f32tag(x)
        + legacy.f32tag(y)
        + legacy.f32tag(z)
        + legacy.u16tag(_TAG_U16_B, field_0x2c)
    )


def make_cwarp_result_frame(
    legacy,
    vital_version: int,
    field_0x18: int,
    x: float,
    y: float,
    z: float,
    field_0x2c: int,
) -> tuple[bytes, bytes]:
    payload = make_cwarp_result_payload(legacy, field_0x18, x, y, z, field_0x2c)
    return legacy.make_runtime_vital(CWARP_RESULT_VITAL_ID, vital_version, payload)


def decode_cwarp_result(raw: bytes) -> CWarpResultBody:
    buf = _as_bytes(raw)
    field_0x18, offset = _read_tag_u64(buf, 0, _TAG_U64)
    x, offset = _read_tag_f32(buf, offset)
    y, offset = _read_tag_f32(buf, offset)
    z, offset = _read_tag_f32(buf, offset)
    field_0x2c, offset = _read_tag_u16(buf, offset, _TAG_U16_B)
    _require_exhausted(buf, offset, "CWarpResult")
    return CWarpResultBody(field_0x18, x, y, z, field_0x2c)


# ------------------------------------------------------------ TeleportVital

@dataclass(frozen=True)
class TeleportTarget:
    """The presence-gated target object at top+0x14 (RE-090 T0).  ``scene_id``
    and ``scene_seq`` carry the same names/meaning ``player_wire.py`` and
    ``npc_wire.py`` already use (RE-077 crosswalk); ``field_0x10``/
    ``field_0x11`` are positional-only, meaning NOT proven.

    Field order here is RE-090's LISTED stream order (``scene_id``,
    ``scene_seq``, ``field_0x10``, ``field_0x11``, vec3) -- NOT ascending
    object-offset order (which would put ``field_0x10``/``field_0x11``
    first, since they sit at +0x10/+0x11 while ``scene_id``/``scene_seq``
    sit at +0x12/+0x18).  RE-090 proves elsewhere in the same result that
    this serializer's real stream order is not always ascending offset --
    the top-level body writes +0x18 before the +0x14 presence flag, and the
    aux object explicitly writes +0x40 before +0x38 -- so the listed order
    is treated as literal stream order here too, consistent with how the
    aux object's out-of-offset-order fields are handled.  This has NOT been
    checked against a real captured frame (``PF_FIELD_VALIDATION.tsv`` has
    132 ``TeleportVital`` candidate frames per direction at status
    ``A2_STATIC_OPEN`` -- candidate-matched, not parse-confirmed -- that a
    future round should use to settle this if it matters before this is
    used against a real client).
    """

    scene_id: int
    scene_seq: int
    field_0x10: int
    field_0x11: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class TeleportAux:
    """The presence-gated auxiliary object at top+0x1C (RE-090 T0).  Every
    field is positional-only, meaning NOT proven.  ``field_0x40`` is written
    on the wire BEFORE ``field_0x38`` even though its object offset is
    higher -- RE-090 confirms this out-of-offset-order write is real, not a
    transcription error, so the encoder/decoder below preserve that exact
    stream order.
    """

    text: str
    field_0x2c: int
    field_0x30: int
    field_0x34: int
    field_0x38: int
    field_0x40: int


@dataclass(frozen=True)
class TeleportVitalBody:
    """Top-level TeleportVital body (RE-090 T0).  ``field_0x18``,
    ``field_0x20`` and ``field_0x22`` are positional-only, meaning NOT
    proven.  ``target``/``aux`` are ``None`` when their presence flag reads
    0 on decode (a structurally valid, empty sub-object), matching the
    presence-flag convention ``gm/command_wire.py`` already uses.
    """

    field_0x18: int
    target: TeleportTarget | None
    aux: TeleportAux | None
    field_0x20: int
    field_0x22: int


def make_teleport_target_payload(
    legacy,
    scene_id: int,
    scene_seq: int,
    field_0x10: int,
    field_0x11: int,
    x: float,
    y: float,
    z: float,
) -> bytes:
    _require_u16(scene_id, "scene_id")
    _require_u64(scene_seq, "scene_seq")
    _require_u8(field_0x10, "field_0x10")
    _require_u8(field_0x11, "field_0x11")
    return (
        legacy.u16tag(_TAG_U16_B, scene_id)
        + legacy.qwordtag(_TAG_U64, scene_seq)
        + legacy.u8tag(_TAG_U8, field_0x10)
        + legacy.u8tag(_TAG_U8, field_0x11)
        + legacy.f32tag(x)
        + legacy.f32tag(y)
        + legacy.f32tag(z)
    )


def make_teleport_aux_payload(
    legacy,
    text: str,
    field_0x2c: int,
    field_0x30: int,
    field_0x34: int,
    field_0x38: int,
    field_0x40: int,
) -> bytes:
    _require_u16(field_0x2c, "field_0x2c")
    _require_u32(field_0x30, "field_0x30")
    _require_u32(field_0x34, "field_0x34")
    _require_u32(field_0x38, "field_0x38")
    _require_u64(field_0x40, "field_0x40")
    return (
        _write_untagged_wstring(text)
        + legacy.u16tag(_TAG_U16_A, field_0x2c)
        + legacy.u32tag(_TAG_U32_A, field_0x30)
        + legacy.u32tag(_TAG_U32_B, field_0x34)
        + legacy.qwordtag(_TAG_U64, field_0x40)
        + legacy.u32tag(_TAG_U32_B, field_0x38)
    )


def make_teleport_vital_payload(
    legacy,
    field_0x18: int,
    target: TeleportTarget | None,
    aux: TeleportAux | None,
    field_0x20: int,
    field_0x22: int,
) -> bytes:
    _require_u8(field_0x18, "field_0x18")
    _require_u8(field_0x20, "field_0x20")
    _require_u16(field_0x22, "field_0x22")
    out = legacy.u8tag(_TAG_U8, field_0x18)
    out += legacy.u8tag(_TAG_U8, 1 if target is not None else 0)
    if target is not None:
        out += make_teleport_target_payload(
            legacy,
            target.scene_id,
            target.scene_seq,
            target.field_0x10,
            target.field_0x11,
            target.x,
            target.y,
            target.z,
        )
    out += legacy.u8tag(_TAG_U8, 1 if aux is not None else 0)
    if aux is not None:
        out += make_teleport_aux_payload(
            legacy,
            aux.text,
            aux.field_0x2c,
            aux.field_0x30,
            aux.field_0x34,
            aux.field_0x38,
            aux.field_0x40,
        )
    out += legacy.u8tag(_TAG_U8, field_0x20)
    out += legacy.u16tag(_TAG_U16_A, field_0x22)
    return out


def make_teleport_vital_frame(
    legacy,
    vital_version: int,
    field_0x18: int,
    target: TeleportTarget | None,
    aux: TeleportAux | None,
    field_0x20: int,
    field_0x22: int,
) -> tuple[bytes, bytes]:
    payload = make_teleport_vital_payload(
        legacy, field_0x18, target, aux, field_0x20, field_0x22
    )
    return legacy.make_runtime_vital(TELEPORT_VITAL_ID, vital_version, payload)


def decode_teleport_vital(raw: bytes) -> TeleportVitalBody:
    buf = _as_bytes(raw)
    field_0x18, offset = _read_tag_u8(buf, 0, _TAG_U8)
    target_presence, offset = _read_tag_u8(buf, offset, _TAG_U8)
    target = None
    if target_presence != 0:
        target, offset = _decode_teleport_target(buf, offset)
    aux_presence, offset = _read_tag_u8(buf, offset, _TAG_U8)
    aux = None
    if aux_presence != 0:
        aux, offset = _decode_teleport_aux(buf, offset)
    field_0x20, offset = _read_tag_u8(buf, offset, _TAG_U8)
    field_0x22, offset = _read_tag_u16(buf, offset, _TAG_U16_A)
    _require_exhausted(buf, offset, "TeleportVital")
    return TeleportVitalBody(field_0x18, target, aux, field_0x20, field_0x22)


def _decode_teleport_target(buf: bytes, offset: int) -> tuple[TeleportTarget, int]:
    # Stream order per RE-090's listing: scene_id, scene_seq, field_0x10,
    # field_0x11, vec3 -- see the TeleportTarget docstring for why this is
    # NOT ascending object-offset order.
    scene_id, offset = _read_tag_u16(buf, offset, _TAG_U16_B)
    scene_seq, offset = _read_tag_u64(buf, offset, _TAG_U64)
    field_0x10, offset = _read_tag_u8(buf, offset, _TAG_U8)
    field_0x11, offset = _read_tag_u8(buf, offset, _TAG_U8)
    x, offset = _read_tag_f32(buf, offset)
    y, offset = _read_tag_f32(buf, offset)
    z, offset = _read_tag_f32(buf, offset)
    return TeleportTarget(scene_id, scene_seq, field_0x10, field_0x11, x, y, z), offset


def _decode_teleport_aux(buf: bytes, offset: int) -> tuple[TeleportAux, int]:
    text, offset = _read_untagged_wstring(buf, offset)
    field_0x2c, offset = _read_tag_u16(buf, offset, _TAG_U16_A)
    field_0x30, offset = _read_tag_u32(buf, offset, _TAG_U32_A)
    field_0x34, offset = _read_tag_u32(buf, offset, _TAG_U32_B)
    field_0x40, offset = _read_tag_u64(buf, offset, _TAG_U64)
    field_0x38, offset = _read_tag_u32(buf, offset, _TAG_U32_B)
    return TeleportAux(text, field_0x2c, field_0x30, field_0x34, field_0x38, field_0x40), offset


# --------------------------------------------------------------- raw I/O

def _require_u8(value: int, label: str) -> None:
    if not (0 <= value <= 0xFF):
        raise ValueError(f"{label} must fit a u8 (0-255)")


def _require_u16(value: int, label: str) -> None:
    if not (0 <= value <= 0xFFFF):
        raise ValueError(f"{label} must fit a u16 (0-65535)")


def _require_u32(value: int, label: str) -> None:
    if not (0 <= value <= 0xFFFFFFFF):
        raise ValueError(f"{label} must fit a u32 (0-4294967295)")


def _require_u64(value: int, label: str) -> None:
    if not (0 <= value <= 0xFFFFFFFFFFFFFFFF):
        raise ValueError(f"{label} must fit a u64 (0-18446744073709551615)")


def _as_bytes(raw: bytes) -> bytes:
    if not isinstance(raw, (bytes, bytearray)):
        raise TypeError("raw must be bytes")
    return bytes(raw)


def _require_exhausted(buf: bytes, offset: int, label: str) -> None:
    if offset != len(buf):
        raise GmTeleportWireError(
            f"{label} decoded cleanly but {len(buf) - offset} trailing byte(s) remain"
        )


def _read_tag_u8(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 2 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 2 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmTeleportWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected 0x{expected_tag:02X}"
        )
    return buf[offset + 1], offset + 2


def _read_tag_u16(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 3 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 3 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmTeleportWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected 0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<H", buf, offset + 1)[0]
    return value, offset + 3


def _read_tag_u32(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 5 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 5 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmTeleportWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected 0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<I", buf, offset + 1)[0]
    return value, offset + 5


def _read_tag_u64(buf: bytes, offset: int, expected_tag: int) -> tuple[int, int]:
    if offset + 9 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 9 bytes for tag 0x{expected_tag:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != expected_tag:
        raise GmTeleportWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected 0x{expected_tag:02X}"
        )
    value = struct.unpack_from("<Q", buf, offset + 1)[0]
    return value, offset + 9


def _read_tag_f32(buf: bytes, offset: int) -> tuple[float, int]:
    if offset + 5 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 5 bytes for tag 0x{_TAG_F32:02X} at offset "
            f"{offset}, have {len(buf) - offset}"
        )
    tag = buf[offset]
    if tag != _TAG_F32:
        raise GmTeleportWireError(
            f"unexpected tag 0x{tag:02X} at offset {offset}, expected 0x{_TAG_F32:02X}"
        )
    value = struct.unpack_from("<f", buf, offset + 1)[0]
    return value, offset + 5


def _write_untagged_wstring(text: str) -> bytes:
    if not isinstance(text, str):
        raise TypeError("text must be a str")
    encoded = text.encode("utf-16-le")
    if len(encoded) > 0xFFFFFFFF:
        raise ValueError("text exceeds the untagged wstring length field")
    return struct.pack("<I", len(encoded)) + encoded


def _read_untagged_wstring(buf: bytes, offset: int) -> tuple[str, int]:
    if offset + 4 > len(buf):
        raise GmTeleportWireError(
            f"truncated: need 4 bytes for a string length at offset {offset}, "
            f"have {len(buf) - offset}"
        )
    byte_len = struct.unpack_from("<I", buf, offset)[0]
    if byte_len % 2 != 0:
        raise GmTeleportWireError(
            f"string at offset {offset} declares byte_len={byte_len}, not a "
            "whole number of UTF-16LE code units"
        )
    start = offset + 4
    end = start + byte_len
    if end > len(buf):
        raise GmTeleportWireError(
            f"truncated: string at offset {offset} declares {byte_len} bytes, "
            f"have {len(buf) - start}"
        )
    try:
        text = buf[start:end].decode("utf-16-le")
    except UnicodeDecodeError as exc:
        raise GmTeleportWireError(
            f"string at offset {offset} is not valid UTF-16LE: {exc}"
        ) from exc
    return text, end
