#!/usr/bin/env python3
"""Offline verifier for HYP-PF-026 / DAMAGE-HP-LINK-001, the linked sweep.

WHAT THIS LANE IS
-----------------
HYP-PF-026 composes ONE eight-frame ``GSCN_RunTimeProtocolRes`` (id 0x6E9D
version 4) sweep that alternates the two client-proven carriers so a hit
finally COSTS something on a server-held hit-point balance:

  * ``CHitResult`` 0x16F7 version 0 -- the floating damage number, a signed
    i32 at hit-entry +0x08 and a u16 flag word at +0x1C -- the GT-024 carrier;
  * ``UpdateAttrVital`` 0x309A version 0 carrying an ``ActorAttr`` 0x12AD --
    the shrinking HP bar, ``hp_current`` bit 0x0004 tag 0x14, ``hp_max`` bit
    0x0008, the death timer bit 0x0080 tag 0x2A f32 -- the GT-019 carrier;

both inside the make_runtime_vitals envelope (BASE change mask 0x02, trailing
derived change mask 0x00).  A hit frame ANNOUNCES a number; the hp frame that
follows it APPLIES that number to the balance and shows the result.  The ladder
of balances is 100, 100, 37, 37, 37, 37, 0, 0, clamped only at the one pinned
step HP_ZERO_DYING, ending in the proven dying window (timer 20.0) then the
pinned elapsed frame (timer 0.0).

WHOSE ARITHMETIC THIS IS
------------------------
**Every rule this file verifies is OURS.**  The original server was shut down
years ago, was never published, and cannot be recovered.  The round-83 static
pass proved the client computes nothing and never subtracts damage from hit
points, so if hit -> bleed -> die is ever to happen on a screen the server has
to SAY both halves; this lane is the sentence that says them once, end to end.
Nothing in this file is evidence about the original server.

WHAT THIS TOOL CHECKS, in the order it checks it
------------------------------------------------
A. CONTRACT.  An INDEPENDENT restatement of the wire contract lives inside this
   file as its own literal constants and is compared, value by value, against
   the module's constants.  A guard that asks the encoder what to expect and
   then checks the encoder against its own answer is a restatement, not a
   check, so nothing in section A is imported from the module.
B. IMAGE GUARDS -- DELIBERATELY ABSENT.  This lane pins NOTHING new from the
   read-only client image: its ids, offsets, tags and formula constants are all
   copied (with drift tests in tests/) from the damage-model, stats-progression
   and hp-death lanes, which already hold the client image to those bytes.  So
   the ``--binary`` image-guard family the damage-model verifier carries is not
   reproduced here and NO ``--binary`` flag is accepted; a single SKIP line
   records that on purpose.
C. PINS.  The pinned probe sweep is recomposed and all eight per-step pins
   (pc_size, pc_sha256, frame_size, frame_sha256) are reproduced with hashlib
   here, and are the same pins the scenario file declares.
D. THE WALK.  Every composed frame is re-read by a walker written in THIS file
   -- both carriers, from byte 0, plus the outer transport frame -- that
   imports none of the module's decoder.  The two damage numbers are re-derived
   from the formula constants, and the whole HP ladder (clamp included) is
   re-walked from the walker-read bytes: the walker-read hp values must equal
   the walker-read damage arithmetic applied to the walker-read baseline, which
   is the point of the lane.
E. REJECTIONS.  Every named refusal raises DamageHpLinkValidationError with the
   right reason AND hands back no bytes, exercised through a real call.
F. SCENARIO + FORGERY.  The scenario file loads to the module's own profile
   object, a one-key mutation of its tree refuses, and a value-equal but
   non-identical unlock (and scenario) is refused by identity.
G. CROSS-LANE BYTE EQUALITY -- the strongest drift guard this lane can have.
   The two hit frames are byte-identical to what the DAMAGE-MODEL lane's own
   composer produces for the same probe identity, and every hp frame is
   byte-identical to the STATS/HP-DEATH lane's composer output for the same
   fields.  Tools are allowed to import both neighbouring lanes; this file does.
H. TRAPS.  Pinned data is mutated in memory and the same guard helpers are
   required to go red, so a verifier that has never seen itself fail is not one.

No server is booted, no client is launched, no socket is opened and no database
is touched.  PURE STDLIB ON PURPOSE, and ASCII-ONLY OUTPUT ON PURPOSE: the
release gate runs ``py -3`` on a Windows console whose code page is cp874, where
one unmappable character kills the process mid-print, so every byte this tool
prints is plain ASCII.

Usage:  py -3 tools/verify_damage_hp_link_encoder.py
        py -3 tools/verify_damage_hp_link_encoder.py --json
        python3 tools/verify_damage_hp_link_encoder.py

Exit 0 = every guard held.  Exit 2 = at least one drifted, with the list.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import damage_hp_link_hypothesis as dh  # noqa: E402
# Tools may import both neighbouring lanes; section G diffs against them.
from pirateforce_foundation import damage_model_hypothesis as dm  # noqa: E402
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "damage_hp_link_hypothesis_link_sweep.json"
OTHER_SCENARIO = ROOT / "scenarios" / "damage_model_hypothesis_hit_sweep.json"
SRC_MODULE = ROOT / "src" / "pirateforce_foundation" / "damage_hp_link_hypothesis.py"


# ===========================================================================
# A. THE INDEPENDENT CONTRACT.  Restated here on purpose so a drift in the
# module cannot agree with itself.  Nothing below is imported from the module.
# ===========================================================================
C_ENVELOPE_ID = 0x6E9D
C_ENVELOPE_VERSION = 4
C_BASE_CHANGE_MASK = 0x02
C_DERIVED_CHANGE_MASK = 0x00
C_FRAME_MAGIC = 0x5F253EAC

C_TAG_U8 = 0x0B
C_TAG_U16 = 0x12
C_TAG_U32 = 0x14
C_TAG_F32 = 0x2A
C_TAG_QWORD = 0x32
C_TAG_ENVELOPE_VERSION = 0x08
C_TAG_WSTRING = 0x48

C_CHIT_RESULT_VITAL_ID = 0x16F7
C_CHIT_RESULT_VITAL_VERSION = 0
C_CHIT_HEADER_WIRE_SIZE = 22
C_HIT_COUNT_WIRE_SIZE = 3
C_HIT_ELEMENT_WIRE_SIZE = 37
C_HIT_ENTRY_DAMAGE_OFFSET = 0x08
C_HIT_ENTRY_YAW_OFFSET = 0x18
C_HIT_ENTRY_FLAGS_OFFSET = 0x1C
C_HIT_ENTRY_COUNT = 1

C_FLAGS_MISS = 0x0000
C_FLAGS_HIT = 0x0001
C_FLAGS_FORBIDDEN_MASK = 0xF184
C_YAW_PINNED = 0.0
C_DAMAGE_WIRE_MAX = 0
C_DAMAGE_WIRE_MIN = -1_000_000
C_INT32_MIN = -2147483648

# OUR formula, restated.
C_ATK_BASE = 100
C_K_ATK_STR = 7
C_K_ATK_LV = 3
C_DEF_BASE = 10
C_K_DEF_CON = 2
C_K_DEF_LV = 1
C_MIN_HIT = 1
C_ATTACKERS = {"MOB_WEAK": (1, 3), "MOB_STRONG": (20, 40)}
C_DEFENDER_LEVEL = 7
C_DEFENDER_ABILITY_CON = 22
C_DAMAGE_PINNED = {"MOB_WEAK": -63, "MOB_STRONG": -379}

C_UPDATE_ATTR_VITAL_ID = 0x309A
C_UPDATE_ATTR_VITAL_VERSION = 0
C_ACTOR_ATTR_ID = 0x12AD
C_EXTRA_GROUP_VALUE = 1
# name -> (mask_bit, object_offset, wire_tag, width)
C_HP_FIELDS = {
    "hp_current": (0x0004, 0x44, 0x14, "u32"),
    "hp_max": (0x0008, 0x48, 0x14, "u32"),
    "hp_death_timer": (0x0080, 0x58, 0x2A, "f32"),
    "scene_id": (0x0100, 0x5C, 0x12, "u16"),
    "scene_sequence": (0x0200, 0x60, 0x32, "qword"),
    "cash": (0x00000800, 0xA8, 0x32, "qword"),
    "character_name": (0x01000000, 0x164, 0x48, "wstring"),
}

C_HP_START = 100
C_HP_MAX = 100
C_HP_FLOOR = 0
C_BALANCE_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
C_DYING_TIMER_SECONDS = 20.0
C_ELAPSED_TIMER_SECONDS = 0.0
C_DURATION_DYING_IMAGE_DEFAULT = 20
C_DYING_WINDOW_MARGIN = 0.5
C_ELAPSED_WIRE_BYTES = bytes.fromhex("2a00000000")

C_PROBE_IDENTITY_LO = 0x10010001
C_PROBE_IDENTITY_HI = 0
C_SPACING_SECONDS = 15.0
C_FIRST_DELAY_SECONDS = 0.0
C_LABEL_PREFIX = "HYP_PF_026_HP_LINK_"
C_STEP_ORDER = (
    "HP_BASELINE", "HIT_WEAK", "HP_AFTER_WEAK", "MISS", "HP_AFTER_MISS",
    "HIT_STRONG", "HP_ZERO_DYING", "DYING_ELAPSED",
)
C_MISS_STEP_LABELS = ("MISS",)
C_LETHAL_STEP_LABELS = ("HP_ZERO_DYING", "DYING_ELAPSED")
C_CLAMP_STEP_LABEL = "HP_ZERO_DYING"
C_HIT_STEPS = {"HIT_WEAK": "MOB_WEAK", "HIT_STRONG": "MOB_STRONG", "MISS": None}
C_HP_STEP_INDEX = {
    "HP_BASELINE": 0, "HP_AFTER_WEAK": 2, "HP_AFTER_MISS": 4,
    "HP_ZERO_DYING": 6, "DYING_ELAPSED": 7,
}
C_TIMER_BY_STEP = {"HP_ZERO_DYING": 20.0, "DYING_ELAPSED": 0.0}
C_BASELINE_SCENE_ID = 1
C_BASELINE_SCENE_SEQUENCE = 0
C_BASELINE_CHARACTER_NAME = "test01"
C_BASELINE_CASH = 10000

PIN_KEYS = ("pc_size", "pc_sha256", "frame_size", "frame_sha256")


# ===========================================================================
# INDEPENDENT WALKERS.  These import nothing from the module's decoder: the
# whole point of the tool is to read the composed bytes with a second pair of
# eyes.  Both carriers, from byte 0, plus the outer transport frame.
# ===========================================================================
class WalkError(ValueError):
    """The composer emitted something this reader cannot account for."""


def _scalar(pc, cursor, tag, width, label):
    if cursor + 1 + width > len(pc):
        raise WalkError("%s: truncated at %d" % (label, cursor))
    if pc[cursor] != tag:
        raise WalkError(
            "%s: tag 0x%02X != 0x%02X at %d" % (label, pc[cursor], tag, cursor))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def walk_transport(frame):
    """Read the outer transport frame (u32 magic + u32 length + one raw
    literal stream) back to its PC, byte for byte."""
    if type(frame) is not bytes or len(frame) < 8:
        raise WalkError("transport: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != C_FRAME_MAGIC:
        raise WalkError("transport: magic 0x%08X" % magic)
    if body_len != len(frame) - 8:
        raise WalkError("transport: length")
    body = frame[8:]
    total = 0
    shift = 0
    cursor = 0
    while True:
        if cursor >= len(body):
            raise WalkError("transport: varint")
        byte = body[cursor]
        cursor += 1
        total |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 28:
            raise WalkError("transport: varint too long")
    out = bytearray()
    while cursor < len(body):
        tag = body[cursor]
        cursor += 1
        if tag & 0x03:
            raise WalkError("transport: non-literal element")
        code = tag >> 2
        if code <= 59:
            count = code + 1
        else:
            extra = code - 59
            if cursor + extra > len(body):
                raise WalkError("transport: truncated length")
            count = int.from_bytes(body[cursor:cursor + extra], "little") + 1
            cursor += extra
        if cursor + count > len(body):
            raise WalkError("transport: truncated literal")
        out += body[cursor:cursor + count]
        cursor += count
    if len(out) != total:
        raise WalkError("transport: length mismatch")
    return bytes(out)


def _walk_attr_body(body):
    """Read one composed ActorAttr body back into (lo, hi, fields)."""
    cursor = 0
    raw, cursor = _scalar(body, cursor, C_TAG_U8, 1, "db mask")
    if raw[0] != 0x01:
        raise WalkError("db mask bit != 0x01")
    raw, cursor = _scalar(body, cursor, C_TAG_QWORD, 8, "identity")
    identity = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, C_TAG_U16, 2, "basic mask")
    basic_mask = struct.unpack("<H", raw)[0]
    values = {}
    # BasicAttr fields in ascending mask-bit order.
    for name in ("hp_current", "hp_max", "hp_death_timer", "scene_id",
                 "scene_sequence"):
        bit, _off, tag, kind = C_HP_FIELDS[name]
        if not basic_mask & bit:
            continue
        basic_mask &= ~bit
        width = {"u16": 2, "u32": 4, "qword": 8, "f32": 4}[kind]
        raw, cursor = _scalar(body, cursor, tag, width, name)
        if kind == "f32":
            values[name] = struct.unpack("<f", raw)[0]
        else:
            values[name] = int.from_bytes(raw, "little")
    if basic_mask:
        raise WalkError("basic mask leftover 0x%X" % basic_mask)
    raw, cursor = _scalar(body, cursor, C_TAG_QWORD, 8, "actor mask")
    actor_mask = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, 0x05, 1, "extra group")
    if raw[0] != C_EXTRA_GROUP_VALUE:
        raise WalkError("extra group flag")
    for name in ("cash", "character_name"):
        bit, _off, tag, kind = C_HP_FIELDS[name]
        if not actor_mask & bit:
            continue
        actor_mask &= ~bit
        if kind == "wstring":
            if cursor + 5 > len(body) or body[cursor] != C_TAG_WSTRING:
                raise WalkError("wstring header")
            blen = int.from_bytes(body[cursor + 1:cursor + 5], "little")
            cursor += 5
            if blen % 2 or cursor + blen > len(body):
                raise WalkError("wstring length")
            values[name] = body[cursor:cursor + blen].decode("utf-16-le")
            cursor += blen
        else:
            raw, cursor = _scalar(body, cursor, tag, 8, name)
            values[name] = int.from_bytes(raw, "little")
    if actor_mask:
        raise WalkError("actor mask leftover 0x%X" % actor_mask)
    if cursor != len(body):
        raise WalkError("attr body trailing bytes")
    return identity & 0xFFFFFFFF, (identity >> 32) & 0xFFFFFFFF, values


def walk_frame(pc):
    """Read one composed PC back, whichever of the two carriers it holds."""
    if type(pc) is not bytes:
        raise WalkError("pc is not bytes")
    cursor = 0
    raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "envelope id")
    result = {"envelope_id": struct.unpack("<H", raw)[0]}
    raw, cursor = _scalar(pc, cursor, C_TAG_U32, 4, "envelope error data")
    result["error_data"] = struct.unpack("<I", raw)[0]
    raw, cursor = _scalar(pc, cursor, C_TAG_ENVELOPE_VERSION, 1, "env version")
    result["envelope_version"] = raw[0]
    raw, cursor = _scalar(pc, cursor, C_TAG_U8, 1, "base change mask")
    result["base_change_mask"] = raw[0]
    raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "vital count")
    if struct.unpack("<H", raw)[0] != 1:
        raise WalkError("vital count != 1")
    raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "vital id")
    vital_id = struct.unpack("<H", raw)[0]
    result["vital_id"] = vital_id
    raw, cursor = _scalar(pc, cursor, C_TAG_U8, 1, "vital version")
    result["vital_version"] = raw[0]
    if vital_id == C_CHIT_RESULT_VITAL_ID:
        result["kind"] = "hit"
        raw, cursor = _scalar(pc, cursor, C_TAG_QWORD, 8, "performer")
        result["performer_identity"] = struct.unpack("<Q", raw)[0]
        for name in ("hf2", "hf3"):
            raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, name)
            result[name] = struct.unpack("<H", raw)[0]
        raw, cursor = _scalar(pc, cursor, C_TAG_U32, 4, "hf4")
        result["hf4"] = struct.unpack("<I", raw)[0]
        raw, cursor = _scalar(pc, cursor, C_TAG_U8, 1, "hf5")
        result["hf5"] = raw[0]
        raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "entry count")
        if struct.unpack("<H", raw)[0] != C_HIT_ENTRY_COUNT:
            raise WalkError("hit entry count != 1")
        raw, cursor = _scalar(pc, cursor, C_TAG_QWORD, 8, "target")
        result["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, C_TAG_U32, 4, "damage")
        # SIGNED: the client's compare sites only make sense signed.
        result["damage_wire"] = struct.unpack("<i", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = _scalar(pc, cursor, C_TAG_F32, 4, "position %s" % axis)
            position.append(struct.unpack("<f", raw)[0])
        result["position"] = tuple(position)
        raw, cursor = _scalar(pc, cursor, C_TAG_F32, 4, "yaw")
        result["yaw"] = struct.unpack("<f", raw)[0]
        raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "flags")
        result["flags"] = struct.unpack("<H", raw)[0]
    elif vital_id == C_UPDATE_ATTR_VITAL_ID:
        result["kind"] = "hp"
        raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "attr count")
        if struct.unpack("<H", raw)[0] != 1:
            raise WalkError("attr count != 1")
        raw, cursor = _scalar(pc, cursor, C_TAG_U16, 2, "attr id")
        if struct.unpack("<H", raw)[0] != C_ACTOR_ATTR_ID:
            raise WalkError("attr id != ActorAttr")
        raw, cursor = _scalar(pc, cursor, C_TAG_U32, 4, "attr body length")
        blen = struct.unpack("<I", raw)[0]
        if cursor + blen > len(pc):
            raise WalkError("attr body truncated")
        lo, hi, fields = _walk_attr_body(pc[cursor:cursor + blen])
        cursor += blen
        result["identity_lo"] = lo
        result["identity_hi"] = hi
        result["performer_identity"] = (hi << 32) | lo
        result["fields"] = fields
    else:
        raise WalkError("unexpected vital id 0x%04X" % vital_id)
    raw, cursor = _scalar(pc, cursor, C_TAG_U8, 1, "derived change mask")
    result["derived_change_mask"] = raw[0]
    if cursor != len(pc):
        raise WalkError("trailing bytes after derived mask")
    return result


# Independent formula, restated from OUR constants.
def _our_attack(level, ability_str):
    return C_ATK_BASE + C_K_ATK_STR * ability_str + C_K_ATK_LV * level


def _our_defense(level, ability_con):
    return C_DEF_BASE + C_K_DEF_CON * ability_con + C_K_DEF_LV * level


def _our_damage_wire(attacker):
    level, ability_str = C_ATTACKERS[attacker]
    rolled = _our_attack(level, ability_str) - _our_defense(
        C_DEFENDER_LEVEL, C_DEFENDER_ABILITY_CON)
    if rolled < C_MIN_HIT:
        rolled = C_MIN_HIT
    return -rolled


def _our_ladder():
    """Re-walk the ladder from our arithmetic, clamp included."""
    balance = C_HP_START
    pending = None
    ladder = []
    clamps = []
    for label in C_STEP_ORDER:
        if label in C_HIT_STEPS:
            attacker = C_HIT_STEPS[label]
            pending = 0 if attacker is None else _our_damage_wire(attacker)
        else:
            if pending is not None:
                moved = balance + pending
                if moved < C_HP_FLOOR:
                    clamps.append(label)
                    moved = C_HP_FLOOR
                balance = moved
                pending = None
        ladder.append(balance)
    return tuple(ladder), clamps


def main():
    want_json = "--json" in sys.argv[1:]
    if "--binary" in sys.argv[1:]:
        print("this lane accepts no --binary flag; see section B")
        return 2

    failures = []
    guards = 0

    def emit(line):
        if not want_json:
            print(line)

    def section(title):
        emit("")
        emit("== " + title)

    def check(label, cond, detail=""):
        nonlocal guards
        guards += 1
        if cond:
            emit("  PASS  " + label)
        else:
            failures.append(label)
            emit("  FAIL  " + label + (("  " + detail) if detail else ""))
        return bool(cond)

    def reject(reason, label, call):
        """A refusal must (a) raise DamageHpLinkValidationError carrying
        `reason` and (b) hand back no bytes at all."""
        nonlocal guards
        guards += 1
        produced = None
        message = ""
        wrong = None
        try:
            produced = call()
        except dh.DamageHpLinkValidationError as exc:
            message = str(exc)
        except Exception as exc:  # noqa: BLE001 - a wrong type is a failure
            wrong = "%s: %s" % (type(exc).__name__, exc)
        first = message.split(":")[0].strip()
        ok = produced is None and wrong is None and first == reason
        if ok:
            emit("  PASS  reject %s (%s)" % (reason, label))
        else:
            detail = wrong if wrong is not None else (
                ("returned %r" % (produced,)) if produced is not None
                else ("wrong reason: " + message))
            failures.append("reject %s (%s)" % (reason, label))
            emit("  FAIL  reject %s (%s)  %s" % (reason, label, str(detail)[:160]))
        return ok

    emit("PF HYP-PF-026 / DAMAGE-HP-LINK-001 offline verifier")
    emit("module          = src/pirateforce_foundation/damage_hp_link_hypothesis.py")
    emit("scenario        = scenarios/damage_hp_link_hypothesis_link_sweep.json")

    legacy = load_legacy(str(LEGACY_PATH))

    # ===================================================== A. THE CONTRACT
    section("A. contract (independent restatement vs the module's constants)")
    check("envelope id 0x6E9D agrees with the module",
          C_ENVELOPE_ID == dh.RUNTIME_PROTOCOL_RES_ID == 0x6E9D)
    check("envelope version 4 agrees with the module",
          C_ENVELOPE_VERSION == dh.RUNTIME_PROTOCOL_RES_VERSION == 4)
    check("BASE change mask 0x02 agrees with the module",
          C_BASE_CHANGE_MASK == dh.HP_LINK_BASE_CHANGE_MASK == 0x02)
    check("DERIVED change mask 0x00 agrees with the module",
          C_DERIVED_CHANGE_MASK == dh.HP_LINK_DERIVED_CHANGE_MASK == 0x00)
    check("transport frame magic 0x5F253EAC agrees with the module",
          C_FRAME_MAGIC == dh.HP_LINK_FRAME_MAGIC)
    check("the seven wire tags agree with the module",
          C_TAG_U8 == dh.TAG_U8 and C_TAG_U16 == dh.TAG_U16
          and C_TAG_U32 == dh.TAG_U32 and C_TAG_F32 == dh.TAG_F32
          and C_TAG_QWORD == dh.TAG_QWORD
          and C_TAG_ENVELOPE_VERSION == dh.TAG_ENVELOPE_VERSION
          and C_TAG_WSTRING == dh.TAG_WSTRING)
    check("CHitResult 0x16F7 version 0 agrees with the module",
          C_CHIT_RESULT_VITAL_ID == dh.CHIT_RESULT_VITAL_ID
          and C_CHIT_RESULT_VITAL_VERSION == dh.CHIT_RESULT_VITAL_VERSION)
    check("the 22-byte header, 37-byte entry and 3-byte count agree",
          C_CHIT_HEADER_WIRE_SIZE == dh.CHIT_RESULT_HEADER_WIRE_SIZE
          and C_HIT_ELEMENT_WIRE_SIZE == dh.HIT_ELEMENT_WIRE_SIZE
          and C_HIT_COUNT_WIRE_SIZE == dh.HIT_COUNT_WIRE_SIZE)
    check("the hit-entry field offsets +0x08 / +0x18 / +0x1C agree",
          C_HIT_ENTRY_DAMAGE_OFFSET == dh.HIT_ENTRY_DAMAGE_OFFSET
          and C_HIT_ENTRY_YAW_OFFSET == dh.HIT_ENTRY_YAW_OFFSET
          and C_HIT_ENTRY_FLAGS_OFFSET == dh.HIT_ENTRY_FLAGS_OFFSET)
    check("the pinned entry count is exactly one",
          C_HIT_ENTRY_COUNT == dh.HIT_ENTRY_COUNT_PINNED == 1)
    check("the flag words 0x0000 / 0x0001 and forbidden mask 0xF184 agree",
          C_FLAGS_MISS == dh.FLAGS_MISS and C_FLAGS_HIT == dh.FLAGS_HIT
          and C_FLAGS_FORBIDDEN_MASK == dh.FLAGS_FORBIDDEN_MASK)
    check("the pinned yaw 0.0 agrees with the module",
          C_YAW_PINNED == dh.YAW_PINNED == 0.0)
    check("the damage safe band [-1000000, 0] and INT32_MIN agree",
          C_DAMAGE_WIRE_MAX == dh.DAMAGE_WIRE_MAX
          and C_DAMAGE_WIRE_MIN == dh.DAMAGE_WIRE_MIN
          and C_INT32_MIN == dh.INT32_MIN)
    check("the seven formula constants agree with the module",
          C_ATK_BASE == dh.ATK_BASE and C_K_ATK_STR == dh.K_ATK_STR
          and C_K_ATK_LV == dh.K_ATK_LV and C_DEF_BASE == dh.DEF_BASE
          and C_K_DEF_CON == dh.K_DEF_CON and C_K_DEF_LV == dh.K_DEF_LV
          and C_MIN_HIT == dh.MIN_HIT)
    check("the attacker and defender profiles agree with the module",
          C_ATTACKERS["MOB_WEAK"] == dh.HP_LINK_ATTACKER_PROFILES["MOB_WEAK"]
          and C_ATTACKERS["MOB_STRONG"]
          == dh.HP_LINK_ATTACKER_PROFILES["MOB_STRONG"]
          and C_DEFENDER_LEVEL == dh.DEFENDER_LEVEL
          and C_DEFENDER_ABILITY_CON == dh.DEFENDER_ABILITY_CON)
    check("the two pinned damage wire values -63 / -379 agree",
          C_DAMAGE_PINNED == dh.HP_LINK_DAMAGE_PINNED)
    check("UpdateAttrVital 0x309A version 0 and ActorAttr 0x12AD agree",
          C_UPDATE_ATTR_VITAL_ID == dh.HP_LINK_UPDATE_ATTR_VITAL_ID
          and C_UPDATE_ATTR_VITAL_VERSION
          == dh.HP_LINK_UPDATE_ATTR_VITAL_VERSION
          and C_ACTOR_ATTR_ID == dh.HP_LINK_ACTOR_ATTR_ID)
    check("the extra-group flag value 1 agrees with the module",
          C_EXTRA_GROUP_VALUE == dh.HP_LINK_EXTRA_GROUP_VALUE == 1)
    module_fields = {
        f.name: (f.mask_bit, f.offset, f.tag, f.kind)
        for f in (*dh.HP_LINK_BASIC_FIELDS, *dh.HP_LINK_ACTOR_FIELDS)
    }
    for name, spec in C_HP_FIELDS.items():
        mine = spec if spec[3] != "wstring" else spec
        theirs = module_fields[name]
        # The module marks wstring width by "wstring"; compare tag+offset+bit.
        check("hp field %s: mask/offset/tag agree with the module" % name,
              mine[0] == theirs[0] and mine[1] == theirs[1]
              and mine[2] == theirs[2],
              "%r != %r" % (mine, theirs))
    check("the HP ladder 100/100/37/37/37/37/0/0 agrees with the module",
          C_BALANCE_LADDER == dh.HP_LINK_BALANCE_LADDER)
    check("the HP start/max/floor 100/100/0 agree with the module",
          C_HP_START == dh.HP_LINK_HP_START and C_HP_MAX == dh.HP_LINK_HP_MAX
          and C_HP_FLOOR == dh.HP_LINK_HP_FLOOR)
    check("the dying / elapsed timer 20.0 / 0.0 agree with the module",
          C_DYING_TIMER_SECONDS == dh.HP_LINK_DYING_TIMER_SECONDS
          and C_ELAPSED_TIMER_SECONDS == dh.HP_LINK_TIMER_ELAPSED_SECONDS)
    check("the death-window gate 20 / 0.5 and elapsed wire bytes agree",
          C_DURATION_DYING_IMAGE_DEFAULT
          == dh.HP_LINK_DURATION_DYING_IMAGE_DEFAULT
          and C_DYING_WINDOW_MARGIN == dh.HP_LINK_DYING_WINDOW_MARGIN
          and C_ELAPSED_WIRE_BYTES == dh.HP_LINK_TIMER_ELAPSED_WIRE_BYTES)
    check("the pinned probe identity 0x10010001/0 agrees with the module",
          C_PROBE_IDENTITY_LO == dh.HP_LINK_PROBE_IDENTITY_LO == 0x10010001
          and C_PROBE_IDENTITY_HI == dh.HP_LINK_PROBE_IDENTITY_HI == 0)
    check("the spacing 15.0 / first delay 0.0 / label prefix agree",
          C_SPACING_SECONDS == dh.DAMAGE_HP_LINK_SPACING_SECONDS
          and C_FIRST_DELAY_SECONDS == dh.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS
          and C_LABEL_PREFIX == dh.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX)
    check("the eight-step order agrees with the module",
          C_STEP_ORDER == dh.DAMAGE_HP_LINK_STEP_ORDER)
    check("the miss / lethal / clamp step labels agree with the module",
          C_MISS_STEP_LABELS == dh.DAMAGE_HP_LINK_MISS_STEP_LABELS
          and C_LETHAL_STEP_LABELS == dh.DAMAGE_HP_LINK_LETHAL_STEP_LABELS
          and C_CLAMP_STEP_LABEL == dh.DAMAGE_HP_LINK_CLAMP_STEP_LABEL)
    check("the timer-by-step map agrees with the module",
          C_TIMER_BY_STEP == dict(dh.DAMAGE_HP_LINK_TIMER_BY_STEP))
    check("the baseline scene/name/cash agree with the module",
          C_BASELINE_SCENE_ID == dh.HP_LINK_BASELINE_SCENE_ID
          and C_BASELINE_SCENE_SEQUENCE == dh.HP_LINK_BASELINE_SCENE_SEQUENCE
          and C_BASELINE_CHARACTER_NAME == dh.HP_LINK_BASELINE_CHARACTER_NAME
          and C_BASELINE_CASH == dh.HP_LINK_BASELINE_CASH
          == legacy.V116_INITIAL_CASH)
    check("the lane is not production-allowed",
          dh.production_allowed is False)
    check("the lane is HYP-PF-026 behind the pinned kwarg and event name",
          dh.DAMAGE_HP_LINK_HYPOTHESIS_ID == "HYP-PF-026"
          and dh.DAMAGE_HP_LINK_DISPATCH_KWARG
          == "damage_hp_link_hypothesis_scenario"
          and dh.DAMAGE_HP_LINK_EVENT_NAME
          == "damage_hp_link_hypothesis_link_sweep_sent")

    # ================================================= B. IMAGE GUARDS ABSENT
    section("B. client-image byte guards - deliberately absent on this lane")
    # This lane pins NOTHING new from the read-only client image: every id,
    # offset, tag and formula constant is copied (with drift tests in tests/)
    # from the damage-model, stats-progression and hp-death lanes, which hold
    # the image to those bytes.  So no --binary flag is accepted and the whole
    # image-guard family the damage-model verifier carries is intentionally not
    # reproduced here.
    emit("  SKIP  image-guard family: this lane pins nothing new from the "
         "client image (its bytes are cross-checked against the neighbouring "
         "lanes in section G instead)")

    # =========================================================== C. THE PINS
    section("C. the pinned probe sweep, recomposed here")
    profile = dh.load_damage_hp_link_hypothesis_scenario(str(SCENARIO))
    check("the scenario file loads and yields the module's own profile object",
          profile is dh._PROFILE
          and profile.scenario_id == dh.DAMAGE_HP_LINK_SCENARIO_ID
          and profile.hypothesis_id == dh.DAMAGE_HP_LINK_HYPOTHESIS_ID)
    unlock = dh.damage_hp_link_wire_unlock(profile)
    check("the unlock is the lane's own token, by identity",
          unlock is dh._UNLOCK)
    actions = dh.build_damage_hp_link_sweep(
        legacy, C_PROBE_IDENTITY_LO, C_PROBE_IDENTITY_HI, unlock, profile)
    check("the sweep is the eight pinned steps in the pinned order",
          [a[0] for a in actions]
          == [C_LABEL_PREFIX + label for label in C_STEP_ORDER]
          == list(dh.DAMAGE_HP_LINK_ACTION_LABELS))
    file_raw = json.loads(SCENARIO.read_text(encoding="utf-8"))
    per_step = file_raw["probe"]["per_step"]
    composed = {}
    for index, label in enumerate(C_STEP_ORDER):
        _name, pc, frame, delay = actions[index]
        composed[label] = (pc, frame)
        pin = dh.DAMAGE_HP_LINK_PINS[label]
        live = {
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        for key in PIN_KEYS:
            check("%s: composed %s reproduces DAMAGE_HP_LINK_PINS"
                  % (label, key), live[key] == pin[key],
                  "%r != %r" % (live[key], pin[key]))
            check("%s: the module pin and the scenario file pin agree on %s"
                  % (label, key), per_step[label][key] == pin[key])
        expected_delay = (C_FIRST_DELAY_SECONDS if index == 0
                          else C_SPACING_SECONDS)
        check("%s: the delay is the pinned plan (%.1f s)"
              % (label, expected_delay), delay == expected_delay)
        check("%s: the frame is exactly frame_pc(pc)" % label,
              frame == legacy.frame_pc(pc))
    check("HP_AFTER_WEAK and HP_AFTER_MISS are byte-identical (a miss moves "
          "nothing)",
          composed["HP_AFTER_WEAK"] == composed["HP_AFTER_MISS"])
    check("the pin table is not self-fulfilling: the hit frames all differ",
          len({dh.DAMAGE_HP_LINK_PINS[label]["pc_sha256"]
               for label in ("HIT_WEAK", "MISS", "HIT_STRONG")}) == 3)

    # ============================================================ D. THE WALK
    section("D. the walk (both carriers, from byte 0) and the re-derivation")
    our_ladder, our_clamps = _our_ladder()
    check("our independent ladder reproduces 100/100/37/37/37/37/0/0",
          our_ladder == C_BALANCE_LADDER)
    check("our independent ladder clamps at exactly one step, HP_ZERO_DYING",
          our_clamps == [C_CLAMP_STEP_LABEL])
    check("the module's replay_hp_link_balance_ladder reproduces our ladder",
          dh.replay_hp_link_balance_ladder() == our_ladder)
    check("our formula reproduces the two pinned damage numbers -63 / -379",
          _our_damage_wire("MOB_WEAK") == -63
          and _our_damage_wire("MOB_STRONG") == -379)

    walked = {}
    for index, label in enumerate(C_STEP_ORDER):
        pc, frame = composed[label]
        check("%s: the transport frame walks back to the exact PC" % label,
              walk_transport(frame) == pc)
        read = walk_frame(pc)
        walked[label] = read
        check("%s: envelope is id 0x6E9D version 4, error data 0" % label,
              read["envelope_id"] == C_ENVELOPE_ID
              and read["envelope_version"] == C_ENVELOPE_VERSION
              and read["error_data"] == 0)
        check("%s: BASE change mask 0x02 and DERIVED change mask 0x00" % label,
              read["base_change_mask"] == C_BASE_CHANGE_MASK
              and read["derived_change_mask"] == C_DERIVED_CHANGE_MASK)
        check("%s: the performer identity is the pinned probe" % label,
              read["performer_identity"] == C_PROBE_IDENTITY_LO)
        if label in C_HIT_STEPS:
            check("%s: the frame is a CHitResult 0x16F7 version 0" % label,
                  read["kind"] == "hit"
                  and read["vital_id"] == C_CHIT_RESULT_VITAL_ID
                  and read["vital_version"] == C_CHIT_RESULT_VITAL_VERSION)
            check("%s: the four reserved header fields are all zero" % label,
                  read["hf2"] == 0 and read["hf3"] == 0
                  and read["hf4"] == 0 and read["hf5"] == 0)
            check("%s: performer == target (the player is both sides)" % label,
                  read["target_identity"] == read["performer_identity"])
            attacker = C_HIT_STEPS[label]
            expected_damage = 0 if attacker is None else _our_damage_wire(attacker)
            check("%s: the walked damage equals our formula's %d"
                  % (label, expected_damage),
                  read["damage_wire"] == expected_damage,
                  str(read["damage_wire"]))
            expected_flags = C_FLAGS_MISS if attacker is None else C_FLAGS_HIT
            check("%s: the walked flags are 0x%04X" % (label, expected_flags),
                  read["flags"] == expected_flags)
            check("%s: damage and flags tell the same story" % label,
                  (read["damage_wire"] == 0) == (read["flags"] == C_FLAGS_MISS))
            check("%s: the yaw is the pinned 0.0f" % label,
                  read["yaw"] == C_YAW_PINNED
                  and struct.pack("<f", read["yaw"]) == b"\x00\x00\x00\x00")
            check("%s: every position component is finite" % label,
                  all(math.isfinite(v) for v in read["position"]))
        else:
            check("%s: the frame is an UpdateAttrVital 0x309A version 0" % label,
                  read["kind"] == "hp"
                  and read["vital_id"] == C_UPDATE_ATTR_VITAL_ID
                  and read["vital_version"] == C_UPDATE_ATTR_VITAL_VERSION)
            fields = read["fields"]
            ladder_index = C_HP_STEP_INDEX[label]
            check("%s: the walked hp_current equals the ladder value %d"
                  % (label, our_ladder[ladder_index]),
                  fields.get("hp_current") == our_ladder[ladder_index])
            check("%s: hp_max is 100, scene is 1/0, cash and name are baseline"
                  % label,
                  fields.get("hp_max") == C_HP_MAX
                  and fields.get("scene_id") == C_BASELINE_SCENE_ID
                  and fields.get("scene_sequence") == C_BASELINE_SCENE_SEQUENCE
                  and fields.get("cash") == C_BASELINE_CASH
                  and fields.get("character_name") == C_BASELINE_CHARACTER_NAME)
            expected_timer = C_TIMER_BY_STEP.get(label)
            check("%s: the death timer is %r (present only on lethal steps)"
                  % (label, expected_timer),
                  fields.get("hp_death_timer") == expected_timer)
            if label in C_LETHAL_STEP_LABELS:
                check("%s: a lethal step holds the balance at the floor 0"
                      % label, fields.get("hp_current") == C_HP_FLOOR)

    # The point of the lane: the walker-read hp values equal the walker-read
    # damage arithmetic applied to the walker-read baseline, all from BYTES.
    baseline_hp = walked["HP_BASELINE"]["fields"]["hp_current"]
    weak_damage = walked["HIT_WEAK"]["damage_wire"]
    miss_damage = walked["MISS"]["damage_wire"]
    strong_damage = walked["HIT_STRONG"]["damage_wire"]
    check("BYTES: hp_after_weak == baseline + weak damage (100 + -63 == 37)",
          walked["HP_AFTER_WEAK"]["fields"]["hp_current"]
          == baseline_hp + weak_damage == 37)
    check("BYTES: hp_after_miss == hp_after_weak + miss damage (37 + 0 == 37)",
          walked["HP_AFTER_MISS"]["fields"]["hp_current"]
          == walked["HP_AFTER_WEAK"]["fields"]["hp_current"] + miss_damage
          == 37)
    check("BYTES: hp_zero_dying == max(floor, 37 + strong damage) (37 + -379 "
          "clamps to 0)",
          walked["HP_ZERO_DYING"]["fields"]["hp_current"]
          == max(C_HP_FLOOR,
                 walked["HP_AFTER_MISS"]["fields"]["hp_current"] + strong_damage)
          == 0)
    check("BYTES: only the strong hit would cross the floor (weak and miss do "
          "not)", baseline_hp + weak_damage >= C_HP_FLOOR
          and 37 + strong_damage < C_HP_FLOOR)

    # ======================================================= E. REJECTIONS
    section("E. every rejection produces no bytes")
    position = dh._require_pinned_position(legacy)
    identity_lo, identity_hi = C_PROBE_IDENTITY_LO, C_PROBE_IDENTITY_HI
    identity_q = (identity_hi << 32) | identity_lo

    reject("damage_not_integer", "a float damage",
           lambda: dh.require_hp_link_damage_wire_value(-63.0))
    reject("damage_not_integer", "a bool damage",
           lambda: dh.require_hp_link_damage_wire_value(True))
    reject("damage_positive_heal_semantics_unknown", "a positive number",
           lambda: dh.require_hp_link_damage_wire_value(1))
    reject("damage_is_int32_min", "INT32_MIN",
           lambda: dh.require_hp_link_damage_wire_value(dh.INT32_MIN))
    reject("damage_below_safe_band", "far below the safe band",
           lambda: dh.require_hp_link_damage_wire_value(-2_000_000))
    reject("flags_not_u16", "a string flag word",
           lambda: dh.require_hp_link_flags_value("1"))
    reject("flags_not_u16", "a bool flag word",
           lambda: dh.require_hp_link_flags_value(True))
    reject("flags_not_u16", "wider than u16",
           lambda: dh.require_hp_link_flags_value(0x10000))
    reject("flags_forbidden_bit", "a forbidden bit",
           lambda: dh.require_hp_link_flags_value(0x0080))
    reject("flags_outside_value_allowlist", "an in-range value we do not defend",
           lambda: dh.require_hp_link_flags_value(0x0008))
    reject("damage_zero_with_apply_flag", "a miss that asks to apply",
           lambda: dh.require_hp_link_damage_and_flags_agree(0, dh.FLAGS_HIT))
    reject("damage_nonzero_without_apply_flag", "a number with no apply bit",
           lambda: dh.require_hp_link_damage_and_flags_agree(-63, dh.FLAGS_MISS))
    reject("hp_balance_not_integer", "a float balance",
           lambda: dh.apply_hit_to_balance(100.0, -1, dh.FLAGS_HIT))
    reject("hp_balance_outside_the_declared_band", "a balance above the max",
           lambda: dh.apply_hit_to_balance(101, -1, dh.FLAGS_HIT))
    reject("unknown_step_label", "a negative step index",
           lambda: dh.step_plan(-1))
    reject("unknown_step_label", "past the end of the plan",
           lambda: dh.step_plan(len(dh.DAMAGE_HP_LINK_STEPS)))
    reject("unknown_step_label", "a bool step index",
           lambda: dh.step_plan(True))
    reject("unknown_step_label", "damage asked of an hp step",
           lambda: dh.step_damage_wire(0))
    reject("unknown_step_label", "an unknown attacker name",
           lambda: dh.compute_hp_link_damage_wire("MOB_MYSTERY"))
    reject("missing_or_forged_wire_unlock", "no unlock token",
           lambda: dh.encode_hp_link_hit_entry(
               legacy, identity_q, -63, position, 0.0, dh.FLAGS_HIT, None))
    reject("yaw_outside_pinned_value", "any angle but the pinned 0.0f",
           lambda: dh.encode_hp_link_hit_entry(
               legacy, identity_q, -63, position, 1.0, dh.FLAGS_HIT, unlock))
    reject("position_not_from_the_pinned_source", "a list, not a tuple",
           lambda: dh.encode_hp_link_hit_entry(
               legacy, identity_q, -63, [1.0, 2.0, 3.0], 0.0, dh.FLAGS_HIT,
               unlock))
    reject("target_identity_outside_qword", "a negative identity",
           lambda: dh.encode_hp_link_hit_entry(
               legacy, -1, -63, position, 0.0, dh.FLAGS_HIT, unlock))
    reject("entry_count_not_pinned", "two entries in one frame",
           lambda: dh.encode_hp_link_chit_result(
               legacy, identity_q, [b"\x00" * 37, b"\x00" * 37], unlock))
    reject("hp_field_outside_the_pinned_table", "an unknown hp field name",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               {"mana": 1}, "HP_BASELINE", unlock))
    reject("hp_frame_missing_baseline_field", "a frame missing a baseline field",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               {"hp_current": 100}, "HP_BASELINE", unlock))
    reject("lethal_field_outside_the_pinned_step",
           "a death timer on a non-lethal step",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               dict(dh.damage_hp_link_baseline_fields(legacy),
                    hp_death_timer=20.0),
               "HP_BASELINE", unlock))
    reject("lethal_field_outside_the_pinned_step",
           "hp_current at the floor on a non-lethal step",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               dict(dh.damage_hp_link_baseline_fields(legacy), hp_current=0),
               "HP_AFTER_WEAK", unlock))
    reject("death_timer_outside_the_pinned_plan",
           "an armed timer that is not the pinned 20.0 on the dying step",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               dict(dh.damage_hp_link_baseline_fields(legacy),
                    hp_current=0, hp_death_timer=25.0),
               "HP_ZERO_DYING", unlock))
    reject("death_timer_not_float", "an int death timer",
           lambda: dh.encode_hp_link_actor_attr(
               legacy, identity_lo, identity_hi,
               dict(dh.damage_hp_link_baseline_fields(legacy),
                    hp_current=0, hp_death_timer=20),
               "HP_ZERO_DYING", unlock))

    # ============================================ F. SCENARIO + FORGERY
    section("F. the scenario file, a mutated tree, and unlock forgery")
    reject("scenario_file_exceeds_allowlist", "no path",
           lambda: dh.load_damage_hp_link_hypothesis_scenario(None))
    reject("scenario_file_exceeds_allowlist", "another lane's scenario",
           lambda: dh.load_damage_hp_link_hypothesis_scenario(str(OTHER_SCENARIO)))
    reject("scenario_file_exceeds_allowlist", "a path that does not exist",
           lambda: dh.load_damage_hp_link_hypothesis_scenario(
               str(ROOT / "scenarios" / "no_such_scenario.json")))

    def _mutated_tree_load():
        data = json.loads(SCENARIO.read_text(encoding="utf-8"))
        data["dispatch"]["spacing_seconds"] = 99.0
        handle, path = tempfile.mkstemp(suffix=".json")
        os.write(handle, json.dumps(data).encode("utf-8"))
        os.close(handle)
        try:
            return dh.load_damage_hp_link_hypothesis_scenario(path)
        finally:
            os.unlink(path)
    reject("scenario_file_exceeds_allowlist",
           "a one-value mutation of the scenario tree", _mutated_tree_load)

    def _extra_key_load():
        data = json.loads(SCENARIO.read_text(encoding="utf-8"))
        data["AN_EXTRA_KEY"] = 1
        handle, path = tempfile.mkstemp(suffix=".json")
        os.write(handle, json.dumps(data).encode("utf-8"))
        os.close(handle)
        try:
            return dh.load_damage_hp_link_hypothesis_scenario(path)
        finally:
            os.unlink(path)
    reject("scenario_file_exceeds_allowlist",
           "one extra key anywhere in the tree", _extra_key_load)

    forged_unlock = dh.DamageHpLinkWireUnlock(
        dh.DAMAGE_HP_LINK_SCENARIO_ID, dh.DAMAGE_HP_LINK_HYPOTHESIS_ID)
    check("the forged unlock compares EQUAL to the real one, so identity is "
          "what defends the lane",
          forged_unlock == dh._UNLOCK and forged_unlock is not dh._UNLOCK)
    reject("missing_or_forged_wire_unlock",
           "a value-equal but non-identical unlock",
           lambda: dh.require_damage_hp_link_wire_unlock(forged_unlock))
    reject("missing_or_forged_wire_unlock",
           "the forged unlock opens no sweep byte",
           lambda: dh.build_damage_hp_link_sweep(
               legacy, identity_lo, identity_hi, forged_unlock, profile))
    forged_scenario = dh.DamageHpLinkHypothesisScenario(
        dh.DAMAGE_HP_LINK_SCENARIO_ID, dh.DAMAGE_HP_LINK_HYPOTHESIS_ID,
        dh.DAMAGE_HP_LINK_STEP_ORDER, dh.DAMAGE_HP_LINK_SPACING_SECONDS,
        dh.DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
        dh.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX)
    check("the forged scenario compares EQUAL to the real profile",
          forged_scenario == dh._PROFILE and forged_scenario is not dh._PROFILE)
    reject("scenario_object_exceeds_allowlist",
           "a value-equal but non-identical scenario mints no unlock",
           lambda: dh.damage_hp_link_wire_unlock(forged_scenario))
    reject("scenario_object_exceeds_allowlist", "any other object",
           lambda: dh.require_damage_hp_link_hypothesis_scenario(object()))

    # ============================== G. CROSS-LANE BYTE EQUALITY (the strongest)
    section("G. cross-lane byte equality vs the damage-model and stats lanes")
    dm_profile = dm.load_damage_model_hypothesis_scenario(str(OTHER_SCENARIO))
    dm_unlock = dm.damage_model_wire_unlock(dm_profile)
    dm_probe = dm.damage_probe_actor(legacy)
    check("the damage-model probe identity is the same pinned smoke identity",
          (dm_probe.identity_lo, dm_probe.identity_hi)
          == (C_PROBE_IDENTITY_LO, C_PROBE_IDENTITY_HI))
    dm_actions = dm.build_damage_model_sweep(
        legacy, dm_probe, dm_unlock, dm_profile)
    dm_by = {a[0].replace(dm.DAMAGE_MODEL_ACTION_LABEL_PREFIX, ""): a
             for a in dm_actions}
    for step in ("HIT_WEAK", "HIT_STRONG"):
        pc, frame = composed[step]
        dm_pc, dm_frame = dm_by[step][1], dm_by[step][2]
        check("%s: the hit PC is byte-identical to the DAMAGE-MODEL composer's"
              % step, pc == dm_pc)
        check("%s: the hit frame is byte-identical to the DAMAGE-MODEL "
              "composer's" % step, frame == dm_frame)
    # The MISS control frame reproduces the damage-model MISS too.
    miss_pc, miss_frame = composed["MISS"]
    check("MISS: the control frame is byte-identical to the DAMAGE-MODEL "
          "composer's MISS", miss_pc == dm_by["MISS"][1]
          and miss_frame == dm_by["MISS"][2])

    sp_actor = sp.StatsProgressionActor(
        C_PROBE_IDENTITY_LO, C_PROBE_IDENTITY_HI, C_BASELINE_SCENE_ID,
        C_BASELINE_SCENE_SEQUENCE, C_BASELINE_CHARACTER_NAME)
    for label in ("HP_BASELINE", "HP_AFTER_WEAK", "HP_AFTER_MISS",
                  "HP_ZERO_DYING", "DYING_ELAPSED"):
        index = C_HP_STEP_INDEX[label]
        fields = dh.damage_hp_link_step_fields(legacy, index)
        if label in C_LETHAL_STEP_LABELS:
            body = sp.encode_actor_attr(
                legacy, C_PROBE_IDENTITY_LO, C_PROBE_IDENTITY_HI, fields,
                sp._HP_DEATH_UNLOCK,
                allow_elapsed_death_timer=(label == "DYING_ELAPSED"))
            payload = sp.make_stats_progression_attr_payload(legacy, body)
            sp_pc, sp_frame = legacy.make_runtime_vitals([
                (legacy.UPDATE_ATTR_VITAL, sp.UPDATE_ATTR_VITAL_VERSION,
                 payload),
            ])
        else:
            sp_pc, sp_frame = sp.make_stats_progression_response(
                legacy, sp_actor, fields)
        pc, frame = composed[label]
        check("%s: the hp PC is byte-identical to the STATS/HP-DEATH composer's"
              % label, pc == sp_pc)
        check("%s: the hp frame is byte-identical to the STATS/HP-DEATH "
              "composer's" % label, frame == sp_frame)

    # ============================================================ H. TRAPS
    section("H. traps - the verifier must be able to go red")
    baseline_pin = dh.DAMAGE_HP_LINK_PINS["HP_BASELINE"]
    pc0, _frame0 = composed["HP_BASELINE"]
    flipped = bytearray(pc0)
    flipped[40] ^= 0x01
    check("TRAP: a flipped bit in a COPY of the HP_BASELINE pc no longer "
          "matches its pinned sha256",
          hashlib.sha256(pc0).hexdigest().upper() == baseline_pin["pc_sha256"]
          and hashlib.sha256(bytes(flipped)).hexdigest().upper()
          != baseline_pin["pc_sha256"])
    broke = None
    try:
        broke = dh.validate_damage_hp_link_sweep(list(reversed(actions)))
    except dh.DamageHpLinkValidationError:
        broke = None
    check("TRAP: the sweep validator rejects the eight real frames reversed",
          broke is None)
    check("the trap harness itself is sound: the eight real frames validate",
          dh.validate_damage_hp_link_sweep(list(actions)) is not None)
    # Flip one payload byte of a real hp frame, reframe, and require the
    # walker-backed validator to refuse it.
    bad_pc = bytearray(composed["HP_AFTER_WEAK"][0])
    bad_pc[40] ^= 0x01
    bad_pc_bytes = bytes(bad_pc)
    tampered = list(actions)
    tampered[2] = (tampered[2][0], bad_pc_bytes,
                   legacy.frame_pc(bad_pc_bytes), tampered[2][3])
    tampered_broke = None
    try:
        tampered_broke = dh.validate_damage_hp_link_sweep(tampered)
    except dh.DamageHpLinkValidationError:
        tampered_broke = None
    check("TRAP: the validator rejects a sweep with one flipped payload byte",
          tampered_broke is None)
    module_text = SRC_MODULE.read_text(encoding="utf-8")
    check("the module carries its production_allowed = False line",
          "production_allowed = False" in module_text)

    # ============================================================== summary
    verdict = {
        "tool": "verify_damage_hp_link_encoder",
        "hypothesis_id": dh.DAMAGE_HP_LINK_HYPOTHESIS_ID,
        "milestone": "DAMAGE-HP-LINK-001",
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "not_claimed": list(dh.DAMAGE_HP_LINK_NONCLAIMS),
    }
    if want_json:
        print(json.dumps(verdict, indent=2))
    else:
        emit("")
        emit("guards run: %d" % guards)
        if failures:
            emit("RESULT: FAIL - %d guard(s) drifted:" % len(failures))
            for item in failures:
                emit("  - " + item)
        else:
            emit("RESULT: PASS - HYP-PF-026 / DAMAGE-HP-LINK-001 verified "
                 "offline (client layer = attended, not run)")
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
