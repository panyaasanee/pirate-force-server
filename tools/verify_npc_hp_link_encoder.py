#!/usr/bin/env python3
"""Offline verifier for HYP-PF-029 / NPC-HP-LINK-001, the target sweep.

WHAT THIS LANE IS
-----------------
HYP-PF-029 composes ONE eight-frame ``GSCN_RunTimeProtocolRes`` (id 0x6E9D
version 4) sweep that alternates the two client-proven carriers so that a hit
finally COSTS a TARGET something:

  * ``CHitResult`` 0x16F7 version 0 inside the VitalData collection (BASE
    change mask 0x02, object +0x18, trailing DERIVED mask 0x00) -- the floating
    damage number, performer = the player, target = the frozen Port Royal
    placement identity 0x2001;
  * the actor-entry collection (INHERITED mask 0x00, DERIVED mask 0x02, object
    +0x1C, ``actor_type`` 4 = CNetNPC) carrying an ``NPCAttr`` whose BasicAttr
    ``hp_current`` is a server-held balance, and whose bit 0x0080 f32 at +0x58
    arms the dying window.

    Same bit NUMBER, different mask BYTE, different reader.  This tool names
    the two collections apart in every guard for exactly that reason.

The ladder of TARGET balances is 100, 100, 37, 37, 37, 37, 0, 0, clamped only
at the one pinned step TARGET_HP_ZERO_DYING, ending on the pinned death-task
frame (timer 0.0).

WHOSE ARITHMETIC THIS IS
------------------------
**Every rule this file verifies is OURS.**  The original server was shut down
years ago, was never published, and cannot be recovered.  No capture in any
corpus shows a target's hit points moving in response to damage in either
direction, and round 83 proved the client computes nothing and never subtracts
-- which is exactly why the server must say both halves itself.  On 2026-08-20
an attended test (GT-027 rerun, on video) delivered 63 + 379 + 63 = 505 damage
to a selected NPC and **the target's HP bar did not move by a single unit**.
That negative is the only client-layer fact this lane has.  It is recorded in
reports/PF_NPC_HP_LINK029_GT027_RERUN_ATTENDED_RESULT_20260820.md, and it rests
on the tester's testimony plus five hashed screenshots rather than on a
re-derivable receipt: that round produced no wire-layer evidence at all.  It is
a client-observable-layer result and must never be cited as a wire-layer one.
Whether the client
renders the intermediate value 37 on the target's bar is UNDECIDABLE from
static analysis and is the queued attended test.  Nothing in this file is
evidence about the original server, and nothing in it is evidence about a
client.

WHAT THIS TOOL CHECKS, in the order it checks it
------------------------------------------------
A. CONTRACT.  An INDEPENDENT restatement of the wire contract lives inside this
   file as its own literal constants and is compared, value by value, against
   the module's constants.  A guard that asks the encoder what to expect and
   then checks the encoder against its own answer is a restatement, not a
   check, so nothing in section A is imported from the module.
B. IMAGE GUARDS -- DELIBERATELY ABSENT.  This lane pins NOTHING new from the
   read-only client image: its ids, offsets, tags and formula constants are all
   copied (with drift tests in tests/) from the damage-model and
   runtimeres-death lanes, which already hold the client image to those bytes.
   No ``--binary`` flag is accepted; a single SKIP line records that on purpose.
C. PINS.  The pinned sweep is recomposed and all eight per-step pins (pc_size,
   pc_sha256, frame_size, frame_sha256) are reproduced with hashlib here, and
   are the same pins the scenario file declares.
D. THE WALK.  Every composed frame is re-read by a walker written in THIS file
   -- both carriers, from byte 0, plus the outer transport frame -- that
   imports none of the module's decoder.  The two damage numbers are re-derived
   from the formula constants, and the whole ladder (clamp included) is
   re-walked FROM the walker-read bytes: the walker-read target hp values must
   equal the walker-read damage arithmetic applied to the walker-read spawn
   value, which is the point of the lane.
E. REJECTIONS.  Every named refusal raises NpcHpLinkValidationError with the
   right reason AND hands back no bytes, exercised through a real call.
F. SCENARIO + FORGERY.  The scenario file loads to the module's own profile
   object, a one-key mutation of its tree refuses, and a value-equal but
   non-identical unlock (and scenario) is refused by identity.
G. CROSS-LANE BYTE EQUALITY -- the strongest drift guard this lane can have.
   The three hit frames are byte-identical to what the DAMAGE-MODEL lane's own
   npc_sweep composer produces for the same probe performer, and the spawn and
   the two lethal frames are byte-identical to what the RUNTIMERES-DEATH lane's
   own composer produces for SPAWN / DYING_LATCH / DEATH_TASK.  The two
   intermediate 37-HP frames have no counterpart step in that lane, so their
   NPCAttr body is diffed against the frozen ``legacy.make_npc_attr``
   projection that lane uses as its OWN baseline oracle.  Tools are allowed to
   import both neighbouring lanes; this file does.
H. TRAPS.  Pinned data is mutated in memory and the same guard helpers are
   required to go red, so a verifier that has never seen itself fail is not one.

No server is booted, no client is launched, no socket is opened and no database
is touched.  PURE STDLIB ON PURPOSE, and ASCII-ONLY OUTPUT ON PURPOSE: the
release gate runs ``py -3`` on a Windows console whose code page is cp874,
where one unmappable character kills the process mid-print, so every byte this
tool prints is plain ASCII.

Usage:  py -3 tools/verify_npc_hp_link_encoder.py
        py -3 tools/verify_npc_hp_link_encoder.py --json
        python3 tools/verify_npc_hp_link_encoder.py

Exit 0 = every guard held.  Exit 2 = at least one drifted, with the list.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import npc_hp_link_hypothesis as nh  # noqa: E402
# Tools may import both neighbouring lanes; section G diffs against them.
from pirateforce_foundation import damage_model_hypothesis as dm  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rd  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "npc_hp_link_hypothesis_target_sweep.json"
DAMAGE_NPC_SCENARIO = (
    ROOT / "scenarios" / "damage_model_hypothesis_npc_sweep.json"
)
DEATH_SCENARIO = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
)
OTHER_SCENARIO = (
    ROOT / "scenarios" / "damage_hp_link_hypothesis_link_sweep.json"
)
SRC_MODULE = (
    ROOT / "src" / "pirateforce_foundation" / "npc_hp_link_hypothesis.py"
)
RUNTIME_SOURCE = ROOT / "src" / "pirateforce_foundation" / "runtime.py"
APP_SOURCE = ROOT / "src" / "pirateforce_foundation" / "app.py"


# ===========================================================================
# A. THE INDEPENDENT CONTRACT.  Restated here on purpose so a drift in the
# module cannot agree with itself.  Nothing below is imported from the module.
# ===========================================================================
C_ENVELOPE_ID = 0x6E9D
C_ENVELOPE_VERSION = 4
C_HIT_BASE_CHANGE_MASK = 0x02
C_HIT_DERIVED_CHANGE_MASK = 0x00
C_ACTOR_INHERITED_CHANGE_MASK = 0x00
C_ACTOR_DERIVED_CHANGE_MASK = 0x02
C_ACTOR_DERIVED_OBJECT_OFFSET = 0x1C
C_HIT_BASE_OBJECT_OFFSET = 0x18
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
C_HIT_ELEMENT_WIRE_SIZE = 37
C_HIT_ENTRY_COUNT = 1
C_HEADER_RESERVED_VALUE = 0
C_FLAGS_MISS = 0x0000
C_FLAGS_HIT = 0x0001
C_FLAGS_FORBIDDEN_MASK = 0xF184
C_YAW_PINNED = 0.0
C_DAMAGE_WIRE_MIN = -1_000_000
C_DAMAGE_WIRE_MAX = 0

C_ACTOR_TYPE_CNETNPC = 4
C_BASIC_BIT_CURRENT_HP = 0x0004
C_BASIC_BIT_MAX_HP = 0x0008
C_BASIC_BIT_DEATH_TIMER = 0x0080
C_BASIC_BIT_SCENE_ID = 0x0100
C_BASIC_BIT_SCENE_SEQ = 0x0200
C_CURRENT_HP_OFFSET = 0x44
C_MAX_HP_OFFSET = 0x48
C_DEATH_TIMER_OFFSET = 0x58
C_DEATH_TIMER_TAG = 0x2A
C_ELAPSED_WIRE_BYTES = bytes.fromhex("2a00000000")
C_DYING_LATCH_PREDICATE_VA = 0x43BDA0
C_DEATH_TASK_PREDICATE_VA = 0x43BD70
C_ZERO_FLOAT_CONSTANT_VA = 0xF0989C

C_ATK_BASE = 100
C_K_ATK_STR = 7
C_K_ATK_LV = 3
C_DEF_BASE = 10
C_K_DEF_CON = 2
C_K_DEF_LV = 1
C_MIN_HIT = 1
C_DEFENDER_LEVEL = 7
C_DEFENDER_ABILITY_CON = 22
C_ATTACKERS = {"MOB_WEAK": (1, 3), "MOB_STRONG": (20, 40)}
C_DAMAGE_PINNED = {"MOB_WEAK": -63, "MOB_STRONG": -379}

C_HP_START = 100
C_HP_MAX = 100
C_HP_FLOOR = 0
C_BALANCE_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)
C_DYING_TIMER_SECONDS = 20.0
C_ELAPSED_TIMER_SECONDS = 0.0

C_TARGET_IDENTITY_LO = 0x2001
C_TARGET_IDENTITY_HI = 0
C_TARGET_PLACEMENT_INDEX = 0
C_TARGET_TEMPLATE_ID = 1
C_TARGET_VISUAL_PRESET = "P_MALE_002_000_SP1"
C_TARGET_SOURCE_NAME = "Navy Transfer"
C_PERFORMER_PROBE_IDENTITY_LO = 0x10010001
C_PERFORMER_PROBE_IDENTITY_HI = 0

C_SPACING_SECONDS = 6.0
C_FIRST_DELAY_SECONDS = 0.0
C_LABEL_PREFIX = "HYP_PF_029_NPC_HP_LINK_"
C_STEP_ORDER = (
    "TARGET_SPAWN", "HIT_WEAK", "TARGET_HP_AFTER_WEAK", "MISS",
    "TARGET_HP_AFTER_MISS", "HIT_STRONG", "TARGET_HP_ZERO_DYING",
    "TARGET_DYING_ELAPSED",
)
C_STEP_KINDS = ("actor", "hit", "actor", "hit", "actor", "hit", "actor",
                "actor")
C_MISS_STEP_LABELS = ("MISS",)
C_LETHAL_STEP_LABELS = ("TARGET_HP_ZERO_DYING", "TARGET_DYING_ELAPSED")
C_CLAMP_STEP_LABEL = "TARGET_HP_ZERO_DYING"
C_TIMER_BY_STEP = {
    "TARGET_HP_ZERO_DYING": 20.0,
    "TARGET_DYING_ELAPSED": 0.0,
}
C_HIT_STEP_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
C_HIT_STEP_FLAGS = {"HIT_WEAK": 0x0001, "MISS": 0x0000, "HIT_STRONG": 0x0001}
# The parent lanes this sweep must reproduce byte for byte, per step.
C_PARENT_PIN_SOURCES = {
    "TARGET_SPAWN": ("HYP-PF-023", "SPAWN"),
    "TARGET_HP_ZERO_DYING": ("HYP-PF-023", "DYING_LATCH"),
    "TARGET_DYING_ELAPSED": ("HYP-PF-023", "DEATH_TASK"),
    "HIT_WEAK": ("HYP-PF-024", "HIT_WEAK"),
    "MISS": ("HYP-PF-024", "MISS"),
    "HIT_STRONG": ("HYP-PF-024", "HIT_STRONG"),
}


# ===========================================================================
# THIS FILE'S OWN WALKER.  It imports none of the module's decoder.
# ===========================================================================
class WalkError(RuntimeError):
    pass


def w_scalar(pc, cursor, tag, width, label):
    if cursor + 1 + width > len(pc):
        raise WalkError(f"{label}: truncated")
    if pc[cursor] != tag:
        raise WalkError("%s: tag 0x%02X != 0x%02X" % (label, pc[cursor], tag))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def w_transport(frame):
    """u32 magic + u32 length + one raw-literal snappy stream -> the PC."""
    if len(frame) < 8:
        raise WalkError("transport: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != C_FRAME_MAGIC:
        raise WalkError("transport: magic")
    if body_len != len(frame) - 8:
        raise WalkError("transport: length")
    body = frame[8:]
    total = 0
    shift = 0
    cursor = 0
    while True:
        byte = body[cursor]
        cursor += 1
        total |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
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
            count = int.from_bytes(body[cursor:cursor + extra], "little") + 1
            cursor += extra
        out += body[cursor:cursor + count]
        cursor += count
    if len(out) != total:
        raise WalkError("transport: uncompressed length mismatch")
    return bytes(out)


W_BASIC_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)
W_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4, 0x26: 4,
           0x2A: 4, 0x32: 8}
W_MOVEMENT_BITS = ((0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5), (0x10, 5),
                   (0x20, 5), (0x40, 5))
W_NPC_ATTR_ID = 0x0AD5
W_MOVEMENT_ATTR_ID = 0x2067


def w_frame(pc):
    """Read one composed PC back, whichever of the two carriers it holds."""
    cursor = 0
    raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "envelope id")
    envelope_id = struct.unpack("<H", raw)[0]
    raw, cursor = w_scalar(pc, cursor, C_TAG_U32, 4, "error data")
    error_data = struct.unpack("<I", raw)[0]
    raw, cursor = w_scalar(pc, cursor, C_TAG_ENVELOPE_VERSION, 1, "version")
    envelope_version = raw[0]
    raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "base change mask")
    base_mask = raw[0]
    out = {
        "envelope_id": envelope_id,
        "error_data": error_data,
        "envelope_version": envelope_version,
        "base_change_mask": base_mask,
    }
    if base_mask == C_HIT_BASE_CHANGE_MASK:
        out["kind"] = "hit"
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "vital count")
        out["vital_count"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "vital id")
        out["vital_id"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "vital version")
        out["vital_version"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_QWORD, 8, "performer")
        out["performer_identity"] = struct.unpack("<Q", raw)[0]
        header_start = cursor - 9
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "header f2")
        out["header_field2"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "header f3")
        out["header_field3"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U32, 4, "header f4")
        out["header_field4"] = struct.unpack("<I", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "header f5")
        out["header_field5"] = raw[0]
        out["header_wire_size"] = cursor - header_start
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "hit count")
        out["hit_count"] = struct.unpack("<H", raw)[0]
        entry_start = cursor
        raw, cursor = w_scalar(pc, cursor, C_TAG_QWORD, 8, "target")
        out["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U32, 4, "damage")
        out["damage_wire"] = struct.unpack("<i", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = w_scalar(pc, cursor, C_TAG_F32, 4, "pos " + axis)
            position.append(struct.unpack("<f", raw)[0])
        out["position"] = tuple(position)
        raw, cursor = w_scalar(pc, cursor, C_TAG_F32, 4, "yaw")
        out["yaw"] = struct.unpack("<f", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "flags")
        out["flags"] = struct.unpack("<H", raw)[0]
        out["hit_entry_wire_size"] = cursor - entry_start
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "derived mask")
        out["derived_change_mask"] = raw[0]
    elif base_mask == C_ACTOR_INHERITED_CHANGE_MASK:
        out["kind"] = "actor"
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "derived mask")
        out["derived_change_mask"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "actor count")
        out["actor_count"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "actor type")
        out["actor_type"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_QWORD, 8, "actor identity")
        out["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "attr count")
        attr_count = raw[0]
        attrs = {}
        for _index in range(attr_count):
            raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "attr id")
            attr_id = struct.unpack("<H", raw)[0]
            if attr_id == W_NPC_ATTR_ID:
                raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "db mask")
                if raw[0] != 0x01:
                    raise WalkError("npc attr: db mask is not identity-only")
                raw, cursor = w_scalar(pc, cursor, C_TAG_QWORD, 8, "attr id")
                attr_identity = struct.unpack("<Q", raw)[0]
                raw, cursor = w_scalar(pc, cursor, C_TAG_U16, 2, "basic mask")
                basic_mask = struct.unpack("<H", raw)[0]
                fields = {}
                for bit, tag in W_BASIC_ORDER:
                    if not basic_mask & bit:
                        continue
                    if tag == C_TAG_WSTRING:
                        raise WalkError("npc attr: unexpected wstring bit")
                    raw, cursor = w_scalar(
                        pc, cursor, tag, W_WIDTH[tag], "basic 0x%04X" % bit)
                    fields[bit] = (
                        struct.unpack("<f", raw)[0] if tag == C_TAG_F32
                        else int.from_bytes(raw, "little")
                    )
                raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "npc mask")
                npc_mask = raw[0]
                template_id = None
                preset = None
                if npc_mask & 0x01:
                    raw, cursor = w_scalar(
                        pc, cursor, C_TAG_U16, 2, "template")
                    template_id = struct.unpack("<H", raw)[0]
                if npc_mask & 0x04:
                    if pc[cursor] != C_TAG_WSTRING:
                        raise WalkError("npc attr: preset tag")
                    length = int.from_bytes(pc[cursor + 1:cursor + 5],
                                            "little")
                    preset = pc[cursor + 5:cursor + 5 + length].decode(
                        "utf-16le")
                    cursor += 5 + length
                attrs[attr_id] = {
                    "identity": attr_identity,
                    "basic_mask": basic_mask,
                    "fields": fields,
                    "npc_mask": npc_mask,
                    "template_id": template_id,
                    "visual_preset": preset,
                }
            elif attr_id == W_MOVEMENT_ATTR_ID:
                raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "mv db mask")
                raw, cursor = w_scalar(pc, cursor, C_TAG_QWORD, 8, "mv id")
                raw, cursor = w_scalar(pc, cursor, C_TAG_U8, 1, "mv mask")
                mask = raw[0]
                for bit, width in W_MOVEMENT_BITS:
                    if mask & bit:
                        cursor += width
                attrs[attr_id] = {"present": True}
            else:
                raise WalkError("unexpected attr id 0x%04X" % attr_id)
        out["attrs"] = attrs
    else:
        raise WalkError("base change mask 0x%02X is neither carrier"
                        % base_mask)
    if cursor != len(pc):
        raise WalkError("trailing bytes: %d" % (len(pc) - cursor))
    return out


def w_damage(name):
    """OUR formula, restated here, so the module cannot grade its own work."""
    level, ability_str = C_ATTACKERS[name]
    attack = C_ATK_BASE + C_K_ATK_STR * ability_str + C_K_ATK_LV * level
    defense = (
        C_DEF_BASE + C_K_DEF_CON * C_DEFENDER_ABILITY_CON
        + C_K_DEF_LV * C_DEFENDER_LEVEL
    )
    rolled = attack - defense
    if rolled < C_MIN_HIT:
        rolled = C_MIN_HIT
    return -rolled


def main():
    want_json = "--json" in sys.argv[1:]
    if "--binary" in sys.argv[1:]:
        print("this lane accepts no --binary flag; see section B")
        return 2

    failures = []
    guards = 0

    # Every emitted line is RECORDED as well as printed, so the ASCII guard at
    # the end of section H can check what this tool actually put on the console
    # instead of only checking its own source bytes.
    printed = []

    def emit(line):
        printed.append(line)
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
        """A refusal must (a) raise NpcHpLinkValidationError carrying `reason`
        and (b) hand back no bytes at all."""
        nonlocal guards
        guards += 1
        produced = None
        message = ""
        wrong = None
        try:
            produced = call()
        except nh.NpcHpLinkValidationError as exc:
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
            emit("  FAIL  reject %s (%s)  %s"
                 % (reason, label, str(detail)[:160]))
        return ok

    emit("PF HYP-PF-029 / NPC-HP-LINK-001 offline verifier")
    emit("module          = src/pirateforce_foundation/npc_hp_link_hypothesis.py")
    emit("scenario        = scenarios/npc_hp_link_hypothesis_target_sweep.json")
    emit("the arithmetic, the ladder and the link are OURS, not the original")
    emit("server's, which is unrecoverable.  Whether the client renders 37 on")
    emit("the target's bar is UNDECIDABLE statically and is the attended test.")

    legacy = load_legacy(str(LEGACY_PATH))

    # ======================================================== A. THE CONTRACT
    section("A. the wire contract, restated independently in this file")
    check("the envelope is GSCN_RunTimeProtocolRes 0x6E9D version 4",
          C_ENVELOPE_ID == 0x6E9D and C_ENVELOPE_VERSION == 4
          and C_ENVELOPE_VERSION == nh.RUNTIME_PROTOCOL_RES_VERSION)
    check("the HIT carrier is the VitalData collection: base 0x02 / derived "
          "0x00 at object +0x18",
          C_HIT_BASE_CHANGE_MASK == nh.HIT_BASE_CHANGE_MASK
          and C_HIT_DERIVED_CHANGE_MASK == nh.HIT_DERIVED_CHANGE_MASK
          and C_HIT_BASE_OBJECT_OFFSET == nh.HIT_BASE_OBJECT_OFFSET)
    check("the TARGET carrier is the actor-entry collection: inherited 0x00 / "
          "derived 0x02 at object +0x1C",
          C_ACTOR_INHERITED_CHANGE_MASK == nh.ACTOR_INHERITED_CHANGE_MASK
          and C_ACTOR_DERIVED_CHANGE_MASK == nh.ACTOR_DERIVED_CHANGE_MASK
          and C_ACTOR_DERIVED_OBJECT_OFFSET == nh.ACTOR_DERIVED_OBJECT_OFFSET)
    check("the two collections are NOT the same object despite the same bit "
          "number", nh.HIT_BASE_OBJECT_OFFSET != nh.ACTOR_DERIVED_OBJECT_OFFSET)
    check("the transport magic agrees with the module",
          C_FRAME_MAGIC == nh.NPC_HP_LINK_FRAME_MAGIC)
    check("the tag map agrees with the module",
          (C_TAG_U8, C_TAG_U16, C_TAG_U32, C_TAG_F32, C_TAG_QWORD,
           C_TAG_ENVELOPE_VERSION, C_TAG_WSTRING)
          == (nh.TAG_U8, nh.TAG_U16, nh.TAG_U32, nh.TAG_F32, nh.TAG_QWORD,
              nh.TAG_ENVELOPE_VERSION, nh.TAG_WSTRING))
    check("CHitResult 0x16F7 version 0 and its widths agree with the module",
          C_CHIT_RESULT_VITAL_ID == nh.CHIT_RESULT_VITAL_ID
          and C_CHIT_RESULT_VITAL_VERSION == nh.CHIT_RESULT_VITAL_VERSION
          and C_CHIT_HEADER_WIRE_SIZE == nh.CHIT_RESULT_HEADER_WIRE_SIZE
          and C_HIT_ELEMENT_WIRE_SIZE == nh.HIT_ELEMENT_WIRE_SIZE
          and C_HIT_ENTRY_COUNT == nh.HIT_ENTRY_COUNT_PINNED)
    check("the flag allowlist is exactly MISS and HIT (no reaction word)",
          (C_FLAGS_MISS, C_FLAGS_HIT)
          == tuple(nh.NPC_HP_LINK_FLAGS_VALUE_ALLOWLIST)
          and C_FLAGS_FORBIDDEN_MASK == nh.FLAGS_FORBIDDEN_MASK)
    check("the damage safe band and the pinned yaw agree with the module",
          C_DAMAGE_WIRE_MIN == nh.DAMAGE_WIRE_MIN
          and C_DAMAGE_WIRE_MAX == nh.DAMAGE_WIRE_MAX
          and C_YAW_PINNED == nh.YAW_PINNED)
    check("actor_type 4 (CNetNPC) agrees with the module's shared constant",
          C_ACTOR_TYPE_CNETNPC == nh.NPC_STYLE_ACTOR_TYPE)
    check("the BasicAttr bits/offsets/tags agree with the module",
          (C_BASIC_BIT_CURRENT_HP, C_BASIC_BIT_MAX_HP, C_BASIC_BIT_DEATH_TIMER,
           C_BASIC_BIT_SCENE_ID, C_BASIC_BIT_SCENE_SEQ)
          == (nh.BASIC_BIT_CURRENT_HP, nh.BASIC_BIT_MAX_HP,
              nh.BASIC_BIT_DEATH_TIMER, nh.BASIC_BIT_SCENE_ID,
              nh.BASIC_BIT_SCENE_SEQ)
          and (C_CURRENT_HP_OFFSET, C_MAX_HP_OFFSET, C_DEATH_TIMER_OFFSET,
               C_DEATH_TIMER_TAG)
          == (nh.CURRENT_HP_OFFSET, nh.MAX_HP_OFFSET, nh.DEATH_TIMER_OFFSET,
              nh.DEATH_TIMER_TAG))
    check("the timer polarity addresses and the pinned elapsed bytes agree",
          C_DYING_LATCH_PREDICATE_VA == nh.DYING_LATCH_PREDICATE_VA
          and C_DEATH_TASK_PREDICATE_VA == nh.DEATH_TASK_PREDICATE_VA
          and C_ZERO_FLOAT_CONSTANT_VA == nh.ZERO_FLOAT_CONSTANT_VA
          and C_ELAPSED_WIRE_BYTES == nh.NPC_HP_LINK_TIMER_ELAPSED_WIRE_BYTES)
    check("OUR formula constants agree with the module",
          (C_ATK_BASE, C_K_ATK_STR, C_K_ATK_LV, C_DEF_BASE, C_K_DEF_CON,
           C_K_DEF_LV, C_MIN_HIT)
          == (nh.ATK_BASE, nh.K_ATK_STR, nh.K_ATK_LV, nh.DEF_BASE,
              nh.K_DEF_CON, nh.K_DEF_LV, nh.MIN_HIT))
    check("the defender and the two attacker profiles agree with the module",
          C_DEFENDER_LEVEL == nh.DEFENDER_LEVEL
          and C_DEFENDER_ABILITY_CON == nh.DEFENDER_ABILITY_CON
          and C_ATTACKERS == dict(nh.NPC_HP_LINK_ATTACKER_PROFILES))
    check("the formula DERIVES -63 and -379 here, independently of the module",
          {name: w_damage(name) for name in C_ATTACKERS} == C_DAMAGE_PINNED
          and C_DAMAGE_PINNED == dict(nh.NPC_HP_LINK_DAMAGE_PINNED))
    check("the target ladder 100/100/37/37/37/37/0/0 agrees with the module",
          C_BALANCE_LADDER == nh.NPC_HP_LINK_BALANCE_LADDER)
    check("the ladder is arithmetic, not a table: 100-63=37, 37+0=37, "
          "37-379 clamps to 0",
          C_HP_START + w_damage("MOB_WEAK") == C_BALANCE_LADDER[2]
          and C_BALANCE_LADDER[2] + 0 == C_BALANCE_LADDER[4]
          and max(C_HP_FLOOR, C_BALANCE_LADDER[4] + w_damage("MOB_STRONG"))
          == C_BALANCE_LADDER[6])
    check("the hp start/max/floor 100/100/0 agree with the module",
          C_HP_START == nh.NPC_HP_LINK_HP_START
          and C_HP_MAX == nh.NPC_HP_LINK_HP_MAX
          and C_HP_FLOOR == nh.NPC_HP_LINK_HP_FLOOR)
    check("the dying / elapsed timers 20.0 / 0.0 agree with the module",
          C_DYING_TIMER_SECONDS == nh.DYING_LATCH_TIMER_SECONDS
          and C_ELAPSED_TIMER_SECONDS == nh.DEATH_TASK_TIMER_SECONDS)
    check("the frozen target identity 0x2001 and its placement pin agree",
          C_TARGET_IDENTITY_LO == nh.NPC_HP_LINK_TARGET_IDENTITY_LO == 0x2001
          and C_TARGET_IDENTITY_HI == nh.NPC_HP_LINK_TARGET_IDENTITY_HI
          and C_TARGET_PLACEMENT_INDEX
          == nh.NPC_HP_LINK_TARGET_PLACEMENT_INDEX
          and C_TARGET_TEMPLATE_ID == nh.NPC_HP_LINK_TARGET_TEMPLATE_ID
          and C_TARGET_VISUAL_PRESET == nh.NPC_HP_LINK_TARGET_VISUAL_PRESET
          and C_TARGET_SOURCE_NAME == nh.NPC_HP_LINK_TARGET_SOURCE_NAME)
    check("the target identity is 0x2000 + placement_index + 1",
          C_TARGET_IDENTITY_LO == 0x2000 + C_TARGET_PLACEMENT_INDEX + 1)
    check("the probe performer 0x10010001/0 agrees with the module",
          C_PERFORMER_PROBE_IDENTITY_LO
          == nh.NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
          and C_PERFORMER_PROBE_IDENTITY_HI
          == nh.NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI)
    check("the spacing is 6.0 s, NOT the 15.0 s photography profile",
          C_SPACING_SECONDS == nh.NPC_HP_LINK_SPACING_SECONDS == 6.0
          and C_SPACING_SECONDS != dm.DAMAGE_MODEL_NPC_SPACING_SECONDS)
    check("the module writes down WHY the spacing is short (video, not "
          "stretching)",
          "recording_video" in nh.NPC_HP_LINK_SPACING_DECISION
          and "wasted_effort" in nh.NPC_HP_LINK_SPACING_DECISION)
    check("the first delay 0.0 and the label prefix agree with the module",
          C_FIRST_DELAY_SECONDS == nh.NPC_HP_LINK_FIRST_DELAY_SECONDS
          and C_LABEL_PREFIX == nh.NPC_HP_LINK_ACTION_LABEL_PREFIX)
    check("the eight-step order and its carrier kinds agree with the module",
          C_STEP_ORDER == nh.NPC_HP_LINK_STEP_ORDER
          and C_STEP_KINDS == tuple(row[1] for row in nh.NPC_HP_LINK_STEPS))
    check("the miss / lethal / clamp step labels agree with the module",
          C_MISS_STEP_LABELS == nh.NPC_HP_LINK_MISS_STEP_LABELS
          and C_LETHAL_STEP_LABELS == nh.NPC_HP_LINK_LETHAL_STEP_LABELS
          and C_CLAMP_STEP_LABEL == nh.NPC_HP_LINK_CLAMP_STEP_LABEL)
    check("the timer-by-step map agrees with the module",
          C_TIMER_BY_STEP == dict(nh.NPC_HP_LINK_TIMER_BY_STEP))
    check("the parent pin sources agree with the module",
          C_PARENT_PIN_SOURCES
          == {k: tuple(v)
              for k, v in nh.NPC_HP_LINK_PARENT_PIN_SOURCES.items()})
    check("the lane is not production-allowed",
          nh.production_allowed is False)
    check("the lane is HYP-PF-029 / NPC-HP-LINK-001 behind the pinned kwarg, "
          "event name and wiring owner",
          nh.NPC_HP_LINK_HYPOTHESIS_ID == "HYP-PF-029"
          and nh.NPC_HP_LINK_CHECKPOINT == "NPC-HP-LINK-001"
          and nh.NPC_HP_LINK_DISPATCH_KWARG == "npc_hp_link_hypothesis_scenario"
          and nh.NPC_HP_LINK_EVENT_NAME
          == "npc_hp_link_hypothesis_target_sweep_sent"
          and nh.NPC_HP_LINK_WIRING_OWNER == "npc_hp_link_002_round_111")
    check("the nonclaims carry the design statement and the undecidable one",
          "this_is_our_design_not_the_original_servers_which_is_unrecoverable"
          in nh.NPC_HP_LINK_NONCLAIMS
          and any("undecidable_from_static_analysis" in item
                  for item in nh.NPC_HP_LINK_NONCLAIMS)
          and any("505_damage" in item for item in nh.NPC_HP_LINK_NONCLAIMS))

    # ================================================= B. IMAGE GUARDS ABSENT
    section("B. client-image byte guards - deliberately absent on this lane")
    emit("  SKIP  image-guard family: this lane pins nothing new from the "
         "client image (its bytes are cross-checked against the neighbouring "
         "lanes in section G instead)")

    # =========================================================== C. THE PINS
    section("C. the pinned sweep, recomposed here")
    profile = nh.load_npc_hp_link_hypothesis_scenario(str(SCENARIO))
    check("the scenario file loads and yields the module's own profile object",
          profile is nh._PROFILE
          and profile.scenario_id == nh.NPC_HP_LINK_SCENARIO_ID
          and profile.hypothesis_id == nh.NPC_HP_LINK_HYPOTHESIS_ID)
    unlock = nh.npc_hp_link_wire_unlock(profile)
    target = nh.resolve_npc_hp_link_target(legacy)
    check("the target resolves to the pinned frozen placement",
          (target.placement_index, target.template_id, target.actor_identity,
           target.visual_preset, target.source_name)
          == (C_TARGET_PLACEMENT_INDEX, C_TARGET_TEMPLATE_ID,
              C_TARGET_IDENTITY_LO, C_TARGET_VISUAL_PRESET,
              C_TARGET_SOURCE_NAME))
    actions = nh.build_npc_hp_link_sweep(
        legacy, target, C_PERFORMER_PROBE_IDENTITY_LO,
        C_PERFORMER_PROBE_IDENTITY_HI, unlock, profile)
    check("the sweep is exactly eight actions", len(actions) == 8)
    composed = {}
    for index, (label, pc, frame, delay) in enumerate(actions):
        step = C_STEP_ORDER[index]
        composed[step] = (pc, frame)
        check("%s: the action label is the pinned one" % step,
              label == C_LABEL_PREFIX + step)
        check("%s: the delay is %.1f" % (step, C_FIRST_DELAY_SECONDS
                                         if index == 0 else C_SPACING_SECONDS),
              delay == (C_FIRST_DELAY_SECONDS if index == 0
                        else C_SPACING_SECONDS))
    pinned_file = json.loads(SCENARIO.read_text(encoding="utf-8"))
    for step in C_STEP_ORDER:
        pc, frame = composed[step]
        module_pin = nh.NPC_HP_LINK_PINS[step]
        file_pin = pinned_file["probe"]["per_step"][step]
        pc_sha = hashlib.sha256(pc).hexdigest().upper()
        frame_sha = hashlib.sha256(frame).hexdigest().upper()
        check("%s: pc %d bytes sha %s reproduces the module pin"
              % (step, len(pc), pc_sha[:16]),
              len(pc) == module_pin["pc_size"]
              and pc_sha == module_pin["pc_sha256"])
        check("%s: frame %d bytes sha %s reproduces the module pin"
              % (step, len(frame), frame_sha[:16]),
              len(frame) == module_pin["frame_size"]
              and frame_sha == module_pin["frame_sha256"])
        check("%s: the scenario file declares the same four pins" % step,
              file_pin == {
                  "pc_size": module_pin["pc_size"],
                  "pc_sha256": module_pin["pc_sha256"],
                  "frame_size": module_pin["frame_size"],
                  "frame_sha256": module_pin["frame_sha256"],
              })
    check("TARGET_HP_AFTER_WEAK and TARGET_HP_AFTER_MISS are byte-identical: "
          "a miss moves nothing",
          composed["TARGET_HP_AFTER_WEAK"] == composed["TARGET_HP_AFTER_MISS"])
    check("the two lethal frames are NOT byte-identical: the polarity flips",
          composed["TARGET_HP_ZERO_DYING"] != composed["TARGET_DYING_ELAPSED"])

    # ============================================================ D. THE WALK
    section("D. every composed byte, re-read by this file's own walker")
    walked = {}
    for step in C_STEP_ORDER:
        pc, frame = composed[step]
        check("%s: the transport frame unwraps back to the PC byte for byte"
              % step, w_transport(frame) == pc)
        read = w_frame(pc)
        walked[step] = read
        check("%s: the envelope is 0x6E9D v4 with ErrorData 0" % step,
              read["envelope_id"] == C_ENVELOPE_ID
              and read["envelope_version"] == C_ENVELOPE_VERSION
              and read["error_data"] == 0)
    for step in ("HIT_WEAK", "MISS", "HIT_STRONG"):
        read = walked[step]
        check("%s: rides the VitalData collection (base 0x02 / derived 0x00)"
              % step,
              read["kind"] == "hit"
              and read["base_change_mask"] == C_HIT_BASE_CHANGE_MASK
              and read["derived_change_mask"] == C_HIT_DERIVED_CHANGE_MASK)
        check("%s: one CHitResult 0x16F7 version 0, one hit entry" % step,
              read["vital_count"] == 1
              and read["vital_id"] == C_CHIT_RESULT_VITAL_ID
              and read["vital_version"] == C_CHIT_RESULT_VITAL_VERSION
              and read["hit_count"] == C_HIT_ENTRY_COUNT)
        check("%s: the header is %d bytes and its four reserved fields are 0"
              % (step, C_CHIT_HEADER_WIRE_SIZE),
              read["header_wire_size"] == C_CHIT_HEADER_WIRE_SIZE
              and read["header_field2"] == C_HEADER_RESERVED_VALUE
              and read["header_field3"] == C_HEADER_RESERVED_VALUE
              and read["header_field4"] == C_HEADER_RESERVED_VALUE
              and read["header_field5"] == C_HEADER_RESERVED_VALUE)
        check("%s: the hit entry is %d bytes" % (step, C_HIT_ELEMENT_WIRE_SIZE),
              read["hit_entry_wire_size"] == C_HIT_ELEMENT_WIRE_SIZE)
        check("%s: the performer is the player and the target is 0x2001" % step,
              read["performer_identity"] == C_PERFORMER_PROBE_IDENTITY_LO
              and read["target_identity"] == C_TARGET_IDENTITY_LO
              and read["performer_identity"] != read["target_identity"])
        check("%s: the walker reads damage %d and flags 0x%04X"
              % (step, C_HIT_STEP_DAMAGE[step], C_HIT_STEP_FLAGS[step]),
              read["damage_wire"] == C_HIT_STEP_DAMAGE[step]
              and read["flags"] == C_HIT_STEP_FLAGS[step])
        check("%s: the yaw is the pinned 0.0 and the position is the frozen "
              "V135 spawn" % step,
              read["yaw"] == C_YAW_PINNED
              and all(struct.pack("<f", got) == struct.pack("<f", want)
                      for got, want in zip(read["position"],
                                           (legacy.V135_PLAYER_X,
                                            legacy.V135_PLAYER_Y,
                                            legacy.V135_PLAYER_Z))))
    for step in ("TARGET_SPAWN", "TARGET_HP_AFTER_WEAK",
                 "TARGET_HP_AFTER_MISS", "TARGET_HP_ZERO_DYING",
                 "TARGET_DYING_ELAPSED"):
        read = walked[step]
        npc = read["attrs"][W_NPC_ATTR_ID]
        check("%s: rides the actor-entry collection (inherited 0x00 / derived "
              "0x02)" % step,
              read["kind"] == "actor"
              and read["base_change_mask"] == C_ACTOR_INHERITED_CHANGE_MASK
              and read["derived_change_mask"] & C_ACTOR_DERIVED_CHANGE_MASK)
        check("%s: one entry, actor_type 4 (CNetNPC), identity 0x2001" % step,
              read["actor_count"] == 1
              and read["actor_type"] == C_ACTOR_TYPE_CNETNPC
              and read["target_identity"] == C_TARGET_IDENTITY_LO)
        check("%s: the entry identity and the NPCAttr identity are the same "
              "actor" % step, npc["identity"] == read["target_identity"])
        check("%s: the visual preset is present, so the animation gate can "
              "open" % step, npc["visual_preset"] == C_TARGET_VISUAL_PRESET)
        check("%s: hp_max is 100" % step,
              npc["fields"].get(C_BASIC_BIT_MAX_HP) == C_HP_MAX)
    check("TARGET_SPAWN is alive, placed and carries NO death timer: an actor "
          "cannot be born dead",
          walked["TARGET_SPAWN"]["attrs"][W_NPC_ATTR_ID]["fields"][
              C_BASIC_BIT_CURRENT_HP] == C_HP_START
          and C_BASIC_BIT_DEATH_TIMER not in walked["TARGET_SPAWN"]["attrs"][
              W_NPC_ATTR_ID]["fields"]
          and W_MOVEMENT_ATTR_ID in walked["TARGET_SPAWN"]["attrs"])
    for step in ("TARGET_HP_AFTER_WEAK", "TARGET_HP_AFTER_MISS"):
        fields = walked[step]["attrs"][W_NPC_ATTR_ID]["fields"]
        check("%s: the walker reads hp_current 37 and no death timer" % step,
              fields[C_BASIC_BIT_CURRENT_HP] == 37
              and C_BASIC_BIT_DEATH_TIMER not in fields)
        check("%s: it carries no MovementAttr - it is an UPDATE, not a second "
              "spawn" % step, W_MOVEMENT_ATTR_ID not in walked[step]["attrs"])
    dying = walked["TARGET_HP_ZERO_DYING"]["attrs"][W_NPC_ATTR_ID]["fields"]
    elapsed = walked["TARGET_DYING_ELAPSED"]["attrs"][W_NPC_ATTR_ID]["fields"]
    check("TARGET_HP_ZERO_DYING satisfies vt+0x40: hp 0 AND timer 20.0 > 0",
          dying[C_BASIC_BIT_CURRENT_HP] == C_HP_FLOOR
          and dying[C_BASIC_BIT_DEATH_TIMER] == C_DYING_TIMER_SECONDS
          and dying[C_BASIC_BIT_DEATH_TIMER] > 0.0)
    check("TARGET_DYING_ELAPSED satisfies vt+0x3C: hp 0 AND timer 0.0 <= 0",
          elapsed[C_BASIC_BIT_CURRENT_HP] == C_HP_FLOOR
          and elapsed[C_BASIC_BIT_DEATH_TIMER] == C_ELAPSED_TIMER_SECONDS
          and elapsed[C_BASIC_BIT_DEATH_TIMER] <= 0.0)
    check("the elapsed timer packs to the pinned five bytes (a negative zero "
          "would not)",
          bytes([C_DEATH_TIMER_TAG])
          + struct.pack("<f", elapsed[C_BASIC_BIT_DEATH_TIMER])
          == C_ELAPSED_WIRE_BYTES)
    # THE POINT OF THE LANE, computed from the walker-read bytes only.
    # The walked balance is derived from the walker-read spawn value plus the
    # walker-read damages; the value the walker actually reads out of each
    # post-spawn actor frame is compared AGAINST it rather than discarded.
    # Discarding it was a real defect: a walker output in which every
    # post-spawn frame reported the same wrong hp still passed this guard.
    walked_ladder = []
    link_mismatches = []
    balance = None
    pending = 0
    for index, step in enumerate(C_STEP_ORDER):
        read = walked[step]
        if read["kind"] == "hit":
            pending = read["damage_wire"]
            walked_ladder.append(balance)
            continue
        fields = read["attrs"][W_NPC_ATTR_ID]["fields"]
        value = fields[C_BASIC_BIT_CURRENT_HP]
        if balance is None:
            balance = value
        else:
            balance = max(C_HP_FLOOR, balance + pending)
            pending = 0
            if value != balance:
                link_mismatches.append(
                    "%s: the frame says hp %r, the walked arithmetic says %r"
                    % (step, value, balance))
        walked_ladder.append(balance)
    check("THE LINK: the walker-read target hp values ARE the walker-read "
          "damage arithmetic applied to the walker-read spawn value",
          tuple(walked_ladder) == C_BALANCE_LADDER and not link_mismatches,
          "%r != %r%s" % (
              tuple(walked_ladder), C_BALANCE_LADDER,
              ("; " + "; ".join(link_mismatches)) if link_mismatches else ""))
    check("every frame of the sweep is about the SAME actor: the bar that "
          "moves is the bar the number was drawn over",
          {walked[step]["target_identity"] for step in C_STEP_ORDER}
          == {C_TARGET_IDENTITY_LO})
    check("the module's own validator agrees with this file's walker",
          [row["label"] for row in nh.validate_npc_hp_link_sweep(list(actions))]
          == list(C_STEP_ORDER))

    # ========================================================= E. REJECTIONS
    section("E. every named refusal, driven through a real call")
    reject("missing_or_forged_wire_unlock", "a forged value-equal unlock",
           lambda: nh.encode_npc_hp_link_hit_entry(
               legacy, nh.npc_hp_link_target_identity(), -63,
               (0.0, 0.0, 0.0), 0.0, C_FLAGS_HIT,
               nh.NpcHpLinkWireUnlock(nh.NPC_HP_LINK_SCENARIO_ID,
                                      nh.NPC_HP_LINK_HYPOTHESIS_ID)))
    reject("damage_positive_heal_semantics_unknown", "a positive damage",
           lambda: nh.require_npc_hp_link_damage_wire_value(1))
    reject("damage_is_int32_min", "INT32_MIN",
           lambda: nh.require_npc_hp_link_damage_wire_value(-2147483648))
    reject("damage_below_safe_band", "below the safe band",
           lambda: nh.require_npc_hp_link_damage_wire_value(-2_000_000))
    reject("damage_not_integer", "a float damage",
           lambda: nh.require_npc_hp_link_damage_wire_value(-63.0))
    reject("flags_forbidden_bit", "flag bit 7",
           lambda: nh.require_npc_hp_link_flags_value(0x0080))
    reject("flags_outside_value_allowlist", "the reaction word 0x0009",
           lambda: nh.require_npc_hp_link_flags_value(0x0009))
    reject("flags_not_u16", "a flag word above u16",
           lambda: nh.require_npc_hp_link_flags_value(0x1FFFF))
    reject("damage_zero_with_apply_flag", "a miss carrying the apply bit",
           lambda: nh.require_npc_hp_link_damage_and_flags_agree(0, C_FLAGS_HIT))
    reject("damage_nonzero_without_apply_flag", "a number with no apply bit",
           lambda: nh.require_npc_hp_link_damage_and_flags_agree(
               -63, C_FLAGS_MISS))
    reject("npc_target_identity_not_pinned", "a hit entry at another target",
           lambda: nh.encode_npc_hp_link_hit_entry(
               legacy, 0x2002, -63,
               (float(legacy.V135_PLAYER_X), float(legacy.V135_PLAYER_Y),
                float(legacy.V135_PLAYER_Z)), 0.0, C_FLAGS_HIT, unlock))
    reject("npc_performer_must_not_be_the_npc_target",
           "the NPC swinging at itself",
           lambda: nh.encode_npc_hp_link_chit_result(
               legacy, nh.npc_hp_link_target_identity(), [b"\x00" * 37],
               unlock))
    reject("yaw_outside_pinned_value", "a yaw that is not 0.0",
           lambda: nh.encode_npc_hp_link_hit_entry(
               legacy, nh.npc_hp_link_target_identity(), -63,
               (float(legacy.V135_PLAYER_X), float(legacy.V135_PLAYER_Y),
                float(legacy.V135_PLAYER_Z)), 1.5, C_FLAGS_HIT, unlock))
    reject("entry_count_not_pinned", "two hit entries in one frame",
           lambda: nh.encode_npc_hp_link_chit_result(
               legacy, C_PERFORMER_PROBE_IDENTITY_LO,
               [b"\x00" * 37, b"\x00" * 37], unlock))
    reject("hp_balance_not_integer", "a float balance",
           lambda: nh.apply_hit_to_balance(100.0, -63, C_FLAGS_HIT))
    reject("hp_balance_outside_the_declared_band", "a balance above the max",
           lambda: nh.apply_hit_to_balance(101, -63, C_FLAGS_HIT))
    reject("lethal_field_outside_the_pinned_step",
           "a death timer on a non-lethal step",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_HP_AFTER_WEAK", 37, 20.0, unlock))
    reject("lethal_field_outside_the_pinned_step",
           "hp at the floor on a non-lethal step",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_HP_AFTER_WEAK", 0, None, unlock))
    reject("lethal_field_outside_the_pinned_step",
           "a lethal step with no timer",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_HP_ZERO_DYING", 0, None, unlock))
    reject("death_timer_outside_the_pinned_plan", "an unpinned timer value",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_HP_ZERO_DYING", 0, 19.0, unlock))
    reject("death_timer_not_float", "an int timer",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_DYING_ELAPSED", 0, 0, unlock))
    reject("death_timer_elapsed_is_not_the_pinned_zero", "a negative zero",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_DYING_ELAPSED", 0, -0.0, unlock))
    reject("unknown_step_label", "a step label outside the plan",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "HP_BASELINE", 37, None, unlock))
    reject("unknown_step_label", "a step index outside the plan",
           lambda: nh.step_plan(8))
    reject("unknown_step_label", "an attacker nobody declared",
           lambda: nh.compute_npc_hp_link_damage_wire("MOB_MIDDLING"))
    reject("hp_field_value_outside_width", "hp above the max",
           lambda: nh.encode_npc_hp_link_npc_attr(
               legacy, target, "TARGET_HP_AFTER_WEAK", 101, None, unlock))
    reject("scenario_object_exceeds_allowlist", "a lookalike scenario object",
           lambda: nh.npc_hp_link_wire_unlock(
               nh.NpcHpLinkHypothesisScenario(
                   nh.NPC_HP_LINK_SCENARIO_ID, nh.NPC_HP_LINK_HYPOTHESIS_ID,
                   nh.NPC_HP_LINK_STEP_ORDER, C_SPACING_SECONDS,
                   C_FIRST_DELAY_SECONDS, C_LABEL_PREFIX)))
    reject("sweep length is not the pinned plan", "a seven-frame sweep",
           lambda: nh.validate_npc_hp_link_sweep(list(actions)[:7]))
    reject("unknown_step_label", "the eight real frames reversed",
           lambda: nh.validate_npc_hp_link_sweep(list(reversed(actions))))
    reject("scenario_file_exceeds_allowlist", "a scenario path that is None",
           lambda: nh.load_npc_hp_link_hypothesis_scenario(None))

    # =============================================== F. SCENARIO AND FORGERY
    section("F. the scenario file, and the forgeries it must refuse")
    check("the scenario declares test_only, production_allowed false, "
          "one_shot, socket_action none and no database write",
          pinned_file["test_only"] is True
          and pinned_file["production_allowed"] is False
          and pinned_file["dispatch"]["one_shot"] is True
          and pinned_file["dispatch"]["socket_action"] == "none"
          and pinned_file["persisted_post_state"]["database_write"] == "none")
    check("the scenario declares the hypothesis id, the checkpoint and the "
          "wiring owner",
          pinned_file["hypothesis_id"] == "HYP-PF-029"
          and pinned_file["checkpoint"] == "NPC-HP-LINK-001"
          and pinned_file["dispatch"]["wiring_owner"]
          == "npc_hp_link_002_round_111")
    check("the scenario declares the dispatch branch that now exists and names "
          "the real runtime method",
          pinned_file["dispatch"]["wired"] is True
          and pinned_file["dispatch"]["runtime_dispatch_branch"]
          == "runtime_py_dispatch_npc_hp_link_hypothesis_reached_from_the_"
             "app_flag_through_make_state_class"
          and "_dispatch_npc_hp_link_hypothesis" in RUNTIME_SOURCE.read_text(
              encoding="utf-8")
          and "npc_hp_link_hypothesis_scenario=npc_hp_link_hypothesis"
          in APP_SOURCE.read_text(encoding="utf-8"))
    check("the scenario declares the 6.0 s spacing AND the reason it is not "
          "15.0",
          pinned_file["dispatch"]["spacing_seconds"] == 6.0
          and pinned_file["dispatch"]["first_frame_delay_seconds"] == 0.0
          and "recording_video" in pinned_file["spacing_decision_comment"])
    check("the scenario carries the design nonclaim and the undecidable one",
          pinned_file["design_not_recovery"]
          == "this_is_our_design_not_the_original_servers_which_is_"
             "unrecoverable"
          and "undecidable" in json.dumps(pinned_file))
    check("the scenario declares the ladder as the TARGET's, not the player's",
          pinned_file["wire"]["hp_ladder"]["owner"] == "the_target_not_the_player"
          and pinned_file["wire"]["hp_ladder"]["ladder"]
          == list(C_BALANCE_LADDER))
    with tempfile.TemporaryDirectory() as tmp:
        mutated = json.loads(json.dumps(pinned_file))
        mutated["dispatch"]["spacing_seconds"] = 15.0
        bad = Path(tmp) / "mutated.json"
        bad.write_text(json.dumps(mutated), encoding="utf-8")
        reject("scenario_file_exceeds_allowlist",
               "a one-value mutation of the scenario tree",
               lambda: nh.load_npc_hp_link_hypothesis_scenario(str(bad)))
        extra = json.loads(json.dumps(pinned_file))
        extra["unexpected_key"] = 1
        bad2 = Path(tmp) / "extra.json"
        bad2.write_text(json.dumps(extra), encoding="utf-8")
        reject("scenario_file_exceeds_allowlist",
               "one extra key anywhere in the tree",
               lambda: nh.load_npc_hp_link_hypothesis_scenario(str(bad2)))
        reject("scenario_file_exceeds_allowlist",
               "a neighbouring lane's scenario file",
               lambda: nh.load_npc_hp_link_hypothesis_scenario(
                   str(OTHER_SCENARIO)))
    forged = nh.NpcHpLinkWireUnlock(nh.NPC_HP_LINK_SCENARIO_ID,
                                    nh.NPC_HP_LINK_HYPOTHESIS_ID)
    check("a value-equal unlock compares == but is refused by identity",
          forged == unlock and forged is not unlock)
    reject("missing_or_forged_wire_unlock", "the forged unlock, again",
           lambda: nh.require_npc_hp_link_wire_unlock(forged))

    # ============================== G. CROSS-LANE BYTE EQUALITY (the strongest)
    section("G. cross-lane byte equality vs the damage-model and death lanes")
    dm_profile = dm.load_damage_model_hypothesis_scenario(
        str(DAMAGE_NPC_SCENARIO))
    check("the damage lane's npc_sweep profile is the one that targets 0x2001",
          dm_profile.scenario_id == dm.DAMAGE_MODEL_NPC_SCENARIO_ID
          and dm.DAMAGE_NPC_TARGET_IDENTITY_LO == C_TARGET_IDENTITY_LO)
    dm_unlock = dm.damage_model_wire_unlock(dm_profile)
    dm_probe = dm.damage_probe_actor(legacy)
    check("the damage lane's probe performer is the same pinned smoke identity",
          (dm_probe.identity_lo, dm_probe.identity_hi)
          == (C_PERFORMER_PROBE_IDENTITY_LO, C_PERFORMER_PROBE_IDENTITY_HI))
    dm_by = {}
    for index, label in enumerate(dm_profile.step_order):
        dm_by[label] = dm.make_damage_model_step_response(
            legacy, dm_probe, index, dm_unlock, dm_profile)
    for step in ("HIT_WEAK", "MISS", "HIT_STRONG"):
        pc, frame = composed[step]
        check("%s: the hit PC is byte-identical to the DAMAGE-MODEL npc_sweep "
              "composer's" % step, pc == dm_by[step][0])
        check("%s: the hit frame is byte-identical to the DAMAGE-MODEL "
              "npc_sweep composer's" % step, frame == dm_by[step][1])

    rd_profile = rd.load_runtimeres_death_hypothesis_scenario(
        str(DEATH_SCENARIO))
    rd_unlock = rd.runtimeres_death_lethal_unlock(rd_profile)
    rd_probe = rd.resolve_probe(legacy)
    check("the death lane's probe is the SAME frozen placement identity",
          rd_probe.actor_identity == target.actor_identity
          == C_TARGET_IDENTITY_LO
          and rd_probe.visual_preset == target.visual_preset)
    rd_by = {}
    for index, label in enumerate(rd_profile.step_order):
        rd_by[label] = rd.make_runtimeres_death_step_response(
            legacy, rd_probe, index, rd_unlock, rd_profile)
    for mine, theirs in (("TARGET_SPAWN", "SPAWN"),
                         ("TARGET_HP_ZERO_DYING", "DYING_LATCH"),
                         ("TARGET_DYING_ELAPSED", "DEATH_TASK")):
        pc, frame = composed[mine]
        check("%s: the actor PC is byte-identical to the RUNTIMERES-DEATH "
              "composer's %s" % (mine, theirs), pc == rd_by[theirs][0])
        check("%s: the actor frame is byte-identical to the RUNTIMERES-DEATH "
              "composer's %s" % (mine, theirs), frame == rd_by[theirs][1])
    # The two 37-HP frames have no counterpart STEP in the death lane, so the
    # oracle is the frozen projection that lane uses as its own baseline.
    baseline_37 = legacy.make_npc_attr(
        target.template_id, target.actor_identity, target.scene_id,
        target.scene_sequence, target.visual_preset, 37, C_HP_MAX)
    mine_37 = nh.encode_npc_hp_link_npc_attr(
        legacy, target, "TARGET_HP_AFTER_WEAK", 37, None, unlock)
    check("TARGET_HP_AFTER_WEAK: the NPCAttr body is byte-identical to the "
          "frozen legacy.make_npc_attr projection for hp 37/100",
          mine_37 == baseline_37)
    death_lane_37 = rd.encode_death_capable_npc_attr(
        legacy, rd_probe, current_hp=37, max_hp=C_HP_MAX)
    check("TARGET_HP_AFTER_WEAK: it is also byte-identical to what the "
          "RUNTIMERES-DEATH encoder produces for hp 37/100",
          mine_37 == death_lane_37)
    check("the module's copied parent pins agree with the parents' live pin "
          "tables in BOTH directions",
          all(
              nh.NPC_HP_LINK_PINS[mine]["pc_sha256"]
              == rd.RUNTIMERES_DEATH_PINS[theirs]["pc_sha256"]
              and nh.NPC_HP_LINK_PINS[mine]["frame_sha256"]
              == rd.RUNTIMERES_DEATH_PINS[theirs]["frame_sha256"]
              for mine, theirs in (("TARGET_SPAWN", "SPAWN"),
                                   ("TARGET_HP_ZERO_DYING", "DYING_LATCH"),
                                   ("TARGET_DYING_ELAPSED", "DEATH_TASK"))
          ) and all(
              nh.NPC_HP_LINK_PINS[step]["pc_sha256"]
              == dm.DAMAGE_MODEL_PINS_NPC[step]["pc_sha256"]
              and nh.NPC_HP_LINK_PINS[step]["frame_sha256"]
              == dm.DAMAGE_MODEL_PINS_NPC[step]["frame_sha256"]
              for step in ("HIT_WEAK", "MISS", "HIT_STRONG")
          ))
    check("this lane's formula reproduces the damage lane's own numbers",
          nh.compute_npc_hp_link_damage_wire("MOB_WEAK")
          == dm.compute_damage(dm.ATTACKER_MOB_WEAK,
                               dm.DEFENDER_PLAYER_BASELINE)
          and nh.compute_npc_hp_link_damage_wire("MOB_STRONG")
          == dm.compute_damage(dm.ATTACKER_MOB_STRONG,
                               dm.DEFENDER_PLAYER_BASELINE))

    # ============================================================ H. TRAPS
    section("H. traps - the verifier must be able to go red")
    spawn_pin = nh.NPC_HP_LINK_PINS["TARGET_SPAWN"]
    pc0, _frame0 = composed["TARGET_SPAWN"]
    flipped = bytearray(pc0)
    flipped[40] ^= 0x01
    check("TRAP: a flipped bit in a COPY of the TARGET_SPAWN pc no longer "
          "matches its pinned sha256",
          hashlib.sha256(pc0).hexdigest().upper() == spawn_pin["pc_sha256"]
          and hashlib.sha256(bytes(flipped)).hexdigest().upper()
          != spawn_pin["pc_sha256"])
    broke = None
    try:
        broke = nh.validate_npc_hp_link_sweep(list(reversed(actions)))
    except nh.NpcHpLinkValidationError:
        broke = None
    check("TRAP: the sweep validator rejects the eight real frames reversed",
          broke is None)
    check("the trap harness itself is sound: the eight real frames validate",
          nh.validate_npc_hp_link_sweep(list(actions)) is not None)
    bad_pc = bytearray(composed["TARGET_HP_AFTER_WEAK"][0])
    # BasicAttr hp_current is the u32 right after the 0x14 tag; flipping any
    # payload byte must make the walker-backed validator refuse.
    bad_pc[40] ^= 0x01
    bad_pc_bytes = bytes(bad_pc)
    tampered = list(actions)
    tampered[2] = (tampered[2][0], bad_pc_bytes,
                   legacy.frame_pc(bad_pc_bytes), tampered[2][3])
    tampered_broke = None
    try:
        tampered_broke = nh.validate_npc_hp_link_sweep(tampered)
    except nh.NpcHpLinkValidationError:
        tampered_broke = None
    check("TRAP: the validator rejects a sweep with one flipped payload byte",
          tampered_broke is None)
    swapped = list(actions)
    swapped[6], swapped[7] = swapped[7], swapped[6]
    swapped[6] = (actions[6][0], swapped[6][1], swapped[6][2], swapped[6][3])
    swapped[7] = (actions[7][0], swapped[7][1], swapped[7][2], swapped[7][3])
    swapped_broke = None
    try:
        swapped_broke = nh.validate_npc_hp_link_sweep(swapped)
    except nh.NpcHpLinkValidationError:
        swapped_broke = None
    check("TRAP: the validator rejects the two lethal frames in the wrong "
          "polarity order (task gate before the latch)", swapped_broke is None)
    check("TRAP: this file's own walker refuses a truncated frame",
          _walker_refuses(pc0[:-1]))
    module_text = SRC_MODULE.read_text(encoding="utf-8")
    check("the module carries its production_allowed = False line",
          "production_allowed = False" in module_text)
    check("the module carries its ledger annotation",
          "# PF-HYPOTHESIS-LEDGER: HYP-PF-029 active" in module_text)
    check("every line this tool has actually emitted is ASCII, and so is the "
          "text the JSON verdict carries (cp874 console discipline)",
          all(ord(ch) < 0x80 for line in printed for ch in line)
          and all(ord(ch) < 0x80 for ch in json.dumps(
              [list(nh.NPC_HP_LINK_NONCLAIMS), nh.NPC_HP_LINK_HYPOTHESIS_ID,
               nh.NPC_HP_LINK_CHECKPOINT])))
    check("this tool's own source file is pure ASCII on disk (a separate "
          "claim from what it printed, and it is what this guard reads)",
          _this_file_is_ascii())

    # ============================================================== summary
    verdict = {
        "tool": "verify_npc_hp_link_encoder",
        "hypothesis_id": nh.NPC_HP_LINK_HYPOTHESIS_ID,
        "milestone": nh.NPC_HP_LINK_CHECKPOINT,
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "not_claimed": list(nh.NPC_HP_LINK_NONCLAIMS),
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
            emit("RESULT: PASS - HYP-PF-029 / NPC-HP-LINK-001 verified "
                 "offline (client layer = attended, not run)")
    return 2 if failures else 0


def _walker_refuses(pc):
    try:
        w_frame(pc)
    except Exception:  # noqa: BLE001 - any refusal is the point
        return True
    return False


def _this_file_is_ascii():
    raw = Path(__file__).read_bytes()
    return all(byte < 0x80 for byte in raw)


if __name__ == "__main__":
    raise SystemExit(main())
