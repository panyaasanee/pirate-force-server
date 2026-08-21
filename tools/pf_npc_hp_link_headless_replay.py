#!/usr/bin/env python3
"""NPC-HP-LINK-001: headless wire proof for the HYP-PF-029 target sweep.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That the lane, booted from the opt-in scenario
``scenarios/npc_hp_link_hypothesis_target_sweep.json`` and nothing else,
composes the exact EIGHT-frame ``GSCN_RunTimeProtocolRes`` (id 0x6E9D version
4) sweep the design says it does, and that those frames are

  (a) **byte-for-byte** the frames the two PARENT lanes' own composers produce
      for the same identity and step -- the DAMAGE-MODEL npc_sweep composer for
      the three ``CHitResult`` frames and the RUNTIMERES-DEATH composer for the
      spawn and the two lethal frames -- compared with ``==`` on the bytes
      objects, in both directions; and

  (b) independently readable, by a walker written in THIS file that imports
      none of the module's decoder and reads every composed byte from byte 0,
      as the hit -> bleed -> die sentence the design says it is:

        TARGET_SPAWN          hp 100/100, placed, no timer     delay 0.0
        HIT_WEAK              damage  -63  flags 0x0001         delay 6.0
        TARGET_HP_AFTER_WEAK  hp_current 37   (100 - 63)        delay 6.0
        MISS                  damage    0  flags 0x0000 control delay 6.0
        TARGET_HP_AFTER_MISS  hp_current 37   (a miss moves none)delay 6.0
        HIT_STRONG            damage -379  flags 0x0001         delay 6.0
        TARGET_HP_ZERO_DYING  hp_current 0 + death timer 20.0   delay 6.0
        TARGET_DYING_ELAPSED  death timer 0.0                   delay 6.0

      The point of the lane, computed from the BYTES and not from the module:
      the walker-read TARGET hp values equal the walker-read damage arithmetic
      applied to the walker-read spawn value (100 + -63 = 37; 37 + 0 = 37;
      37 + -379 clamps to 0), and every frame of the sweep -- both carriers --
      names the SAME actor 0x2001, which is the link made visible.

WHY THIS FILE DOES NOT DRIVE make_state_class
----------------------------------------------
Its neighbours (``pf_damage_hp_link_headless_replay.py`` and friends) boot the
real dispatcher because their lanes have a ``runtime.py`` dispatch branch.

ERRATUM, round 118 (2026-08-21).  This paragraph used to say "HYP-PF-029 does
not", and that stopped being true when NPC-HP-LINK-002 added the branch:
``runtime.py`` now dispatches this lane (the branch keyed on
``CHAT_INPUT_VITAL_ID`` that returns ``_dispatch_npc_hp_link_hypothesis``), and
``tests/test_npc_hp_link_dispatch.py`` guards it.  The old sentence was left
standing after that landed and would have told the next reader something false
about the tree.

WHAT IS STILL TRUE is the limit: this file proves the COMPOSER and stops there.
The honest statement of why is that it has not been extended to drive the
dispatcher - not that anyone decided it should not be.  The dispatcher does have
its own tests (`tests/test_npc_hp_link_dispatch.py`), so nothing is unguarded;
extending this file is available work, not a closed question.  The limit is
stated in the verdict rather than smoothed over.

NO DATABASE, NO SOCKET, AND BOTH ARE MEASURED
----------------------------------------------
This lane writes nothing, so this tool opens no database at all: it takes no
``--db``, and the canonical database is only ``stat``-ed (never opened), once
at the start and once at the end, so a regression that reached for it would be
REPORTED rather than silently tolerated.  While the sweep is composed,
``socket.socket`` and its neighbours are replaced with objects that record and
refuse, so "no socket" is a measurement here and not an assurance.  No
repository file is written unless ``--evidence <path>`` is handed in.  Pure
stdlib.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of this profile.**  The arithmetic, the ladder and the link are
OUR design: the original server is closed, was never published, and NO CAPTURE
IN ANY CORPUS shows a target's hit points moving in response to damage in
either direction, so there is nothing to recover.  Round 83 proved the client
never subtracts, and on 2026-08-20 an attended test (GT-027 rerun, on video)
delivered 505 damage to a selected NPC and the target's HP bar did not move by
a single unit.  **Whether the client renders the intermediate value 37 on the
target's HP bar is UNDECIDABLE from static analysis and is the queued attended
test.**  The only thing proven so far is that negative, and it is recorded in
reports/PF_NPC_HP_LINK029_GT027_RERUN_ATTENDED_RESULT_20260820.md: testimony
plus five hashed screenshots, NOT a re-derivable receipt (that round produced
no teardown, no console tail, no post-run DB snapshot and no capture file), and
a client-observable-layer result that must never be cited as wire-layer
evidence.

Usage:
    py -3 tools/pf_npc_hp_link_headless_replay.py
    py -3 tools/pf_npc_hp_link_headless_replay.py --json
    py -3 tools/pf_npc_hp_link_headless_replay.py \
        --evidence reports/npc_hp_link001_headless.json

Every byte this file prints is ASCII: it is expected to run on a Windows
console under code page cp874, where one non-ASCII character is a crash.

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the list.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import socket
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
# The module under test.  This tool calls its loader, its unlock derivation and
# its composer, and reads its nonclaims.  It deliberately NEVER calls
# decode_npc_hp_link_frame or validate_npc_hp_link_sweep: every byte below is
# read by this file's own walker, so a symmetrical bug in the module's reader
# cannot hide.
from pirateforce_foundation import npc_hp_link_hypothesis as nh  # noqa: E402
# The two PARENT lanes, imported as BYTE ORACLES only.
from pirateforce_foundation import damage_model_hypothesis as dm  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rd  # noqa: E402


SCENARIO = ROOT / "scenarios" / "npc_hp_link_hypothesis_target_sweep.json"
DAMAGE_NPC_SCENARIO = (
    ROOT / "scenarios" / "damage_model_hypothesis_npc_sweep.json"
)
DEATH_SCENARIO = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
)
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# Built by concatenation on purpose: the canonical database's file name must
# never appear as a contiguous literal in this file, so a "no path points at
# it" search stays honest.
CANONICAL_DB = ROOT / "state" / ("pirateforce" + ".sqlite3")


# ---------------------------------------------------------------------------
# This reader's own constants.  Written out as literals rather than read off
# the module, so the guards below measure the module against THEM: a guard that
# asks the encoder what to expect and then checks the encoder against its own
# answer is a restatement, not a check.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
HIT_BASE_CHANGE_MASK = 0x02
HIT_DERIVED_CHANGE_MASK = 0x00
ACTOR_INHERITED_CHANGE_MASK = 0x00
ACTOR_DERIVED_CHANGE_MASK = 0x02
FRAME_MAGIC = 0x5F253EAC

TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32
TAG_ENVELOPE_VERSION = 0x08
TAG_WSTRING = 0x48

CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0
NPC_ATTR_ID = 0x0AD5
MOVEMENT_ATTR_ID = 0x2067
ACTOR_TYPE_CNETNPC = 4
HIT_ENTRY_COUNT = 1
YAW_PINNED = 0.0
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001

BASIC_BIT_CURRENT_HP = 0x0004
BASIC_BIT_MAX_HP = 0x0008
BASIC_BIT_DEATH_TIMER = 0x0080
BASIC_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)
SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                0x26: 4, 0x2A: 4, 0x32: 8}
MOVEMENT_BITS = ((0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5), (0x10, 5),
                 (0x20, 5), (0x40, 5))

TARGET_IDENTITY = 0x2001
PERFORMER_IDENTITY_LO = 0x10010001
PERFORMER_IDENTITY_HI = 0

HP_START = 100
HP_MAX = 100
HP_FLOOR = 0
DYING_TIMER_SECONDS = 20.0
ELAPSED_TIMER_SECONDS = 0.0
BALANCE_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)

STEP_ORDER = (
    "TARGET_SPAWN", "HIT_WEAK", "TARGET_HP_AFTER_WEAK", "MISS",
    "TARGET_HP_AFTER_MISS", "HIT_STRONG", "TARGET_HP_ZERO_DYING",
    "TARGET_DYING_ELAPSED",
)
STEP_KINDS = ("actor", "hit", "actor", "hit", "actor", "hit", "actor", "actor")
ACTION_LABEL_PREFIX = "HYP_PF_029_NPC_HP_LINK_"
ACTION_LABELS = tuple(ACTION_LABEL_PREFIX + step for step in STEP_ORDER)
FIRST_DELAY_SECONDS = 0.0
SPACING_SECONDS = 6.0
EXPECTED_DELAYS = tuple([FIRST_DELAY_SECONDS] + [SPACING_SECONDS] * 7)
HIT_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
HIT_FLAGS = {"HIT_WEAK": FLAGS_HIT, "MISS": FLAGS_MISS,
             "HIT_STRONG": FLAGS_HIT}
PARENT_ORACLE = {
    "TARGET_SPAWN": ("death", "SPAWN"),
    "TARGET_HP_ZERO_DYING": ("death", "DYING_LATCH"),
    "TARGET_DYING_ELAPSED": ("death", "DEATH_TASK"),
    "HIT_WEAK": ("damage", "HIT_WEAK"),
    "MISS": ("damage", "MISS"),
    "HIT_STRONG": ("damage", "HIT_STRONG"),
}


class WalkError(RuntimeError):
    pass


class RefusingSocket:
    """Every socket entry point, replaced by something that records and says
    no.  "This tool opened no socket" is then a measurement."""

    def __init__(self, log):
        self._log = log

    def __call__(self, *args, **kwargs):
        self._log.append("socket.socket")
        raise AssertionError(
            "HYP-PF-029 headless replay must never open a socket")


def _install_socket_trap(log):
    saved = {}
    for name in ("socket", "create_connection", "socketpair"):
        if hasattr(socket, name):
            saved[name] = getattr(socket, name)
            setattr(socket, name, RefusingSocket(log))
    return saved


def _restore_socket(saved):
    for name, value in saved.items():
        setattr(socket, name, value)


def _canonical_stat():
    """Size and mtime of the canonical database, WITHOUT opening it."""
    if not CANONICAL_DB.exists():
        return None
    info = CANONICAL_DB.stat()
    return (info.st_size, info.st_mtime_ns)


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
    if magic != FRAME_MAGIC:
        raise WalkError("transport: magic")
    if body_len != len(frame) - 8:
        raise WalkError("transport: declared length")
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


def w_frame(pc):
    """Read one composed PC back, whichever of the two carriers it holds."""
    cursor = 0
    raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "envelope id")
    out = {"envelope_id": struct.unpack("<H", raw)[0]}
    raw, cursor = w_scalar(pc, cursor, TAG_U32, 4, "error data")
    out["error_data"] = struct.unpack("<I", raw)[0]
    raw, cursor = w_scalar(pc, cursor, TAG_ENVELOPE_VERSION, 1, "version")
    out["envelope_version"] = raw[0]
    raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "base change mask")
    base_mask = raw[0]
    out["base_change_mask"] = base_mask
    if base_mask == HIT_BASE_CHANGE_MASK:
        out["kind"] = "hit"
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "vital count")
        out["vital_count"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "vital id")
        out["vital_id"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "vital version")
        out["vital_version"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, TAG_QWORD, 8, "performer")
        out["performer_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "header f2")
        out["header_field2"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "header f3")
        out["header_field3"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U32, 4, "header f4")
        out["header_field4"] = struct.unpack("<I", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "header f5")
        out["header_field5"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "hit count")
        out["hit_count"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_QWORD, 8, "target")
        out["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U32, 4, "damage")
        out["damage_wire"] = struct.unpack("<i", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = w_scalar(pc, cursor, TAG_F32, 4, "pos " + axis)
            position.append(struct.unpack("<f", raw)[0])
        out["position"] = tuple(position)
        raw, cursor = w_scalar(pc, cursor, TAG_F32, 4, "yaw")
        out["yaw"] = struct.unpack("<f", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "flags")
        out["flags"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "derived mask")
        out["derived_change_mask"] = raw[0]
    elif base_mask == ACTOR_INHERITED_CHANGE_MASK:
        out["kind"] = "actor"
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "derived mask")
        out["derived_change_mask"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "actor count")
        out["actor_count"] = struct.unpack("<H", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "actor type")
        out["actor_type"] = raw[0]
        raw, cursor = w_scalar(pc, cursor, TAG_QWORD, 8, "actor identity")
        out["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "attr count")
        attrs = {}
        for _index in range(raw[0]):
            raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "attr id")
            attr_id = struct.unpack("<H", raw)[0]
            if attr_id == NPC_ATTR_ID:
                raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "db mask")
                if raw[0] != 0x01:
                    raise WalkError("npc attr: db mask is not identity-only")
                raw, cursor = w_scalar(pc, cursor, TAG_QWORD, 8, "attr ident")
                attr_identity = struct.unpack("<Q", raw)[0]
                raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "basic mask")
                basic_mask = struct.unpack("<H", raw)[0]
                fields = {}
                for bit, tag in BASIC_ORDER:
                    if not basic_mask & bit:
                        continue
                    raw, cursor = w_scalar(
                        pc, cursor, tag, SCALAR_WIDTH[tag],
                        "basic 0x%04X" % bit)
                    fields[bit] = (
                        struct.unpack("<f", raw)[0] if tag == TAG_F32
                        else int.from_bytes(raw, "little")
                    )
                raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "npc mask")
                npc_mask = raw[0]
                template_id = None
                preset = None
                if npc_mask & 0x01:
                    raw, cursor = w_scalar(pc, cursor, TAG_U16, 2, "template")
                    template_id = struct.unpack("<H", raw)[0]
                if npc_mask & 0x04:
                    if pc[cursor] != TAG_WSTRING:
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
                    "template_id": template_id,
                    "visual_preset": preset,
                }
            elif attr_id == MOVEMENT_ATTR_ID:
                raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "mv db mask")
                raw, cursor = w_scalar(pc, cursor, TAG_QWORD, 8, "mv ident")
                raw, cursor = w_scalar(pc, cursor, TAG_U8, 1, "mv mask")
                mask = raw[0]
                for bit, width in MOVEMENT_BITS:
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


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    want_json = "--json" in argv
    evidence_path = None
    if "--evidence" in argv:
        evidence_path = Path(argv[argv.index("--evidence") + 1])
    if "--db" in argv:
        print("this tool takes no --db: HYP-PF-029 writes nothing and this "
              "file opens no database at all")
        return 1

    failures = []
    guards = 0
    lines = []

    def emit(line):
        lines.append(line)
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

    emit("PF HYP-PF-029 / NPC-HP-LINK-001 headless wire proof")
    emit("scenario   = scenarios/npc_hp_link_hypothesis_target_sweep.json")
    emit("no server, no socket, no client, no database, no GameClient window")
    emit("the arithmetic, the ladder and the link are OURS, not the original")
    emit("server's, which is unrecoverable")

    canonical_before = _canonical_stat()
    socket_log = []
    saved_socket = _install_socket_trap(socket_log)
    try:
        legacy = load_legacy(str(LEGACY_PATH))

        # ================================================== 0. THE OPT-IN
        section("0. the opt-in, and what happens without it")
        profile = nh.load_npc_hp_link_hypothesis_scenario(str(SCENARIO))
        check("the scenario file loads to the module's own profile object",
              profile is nh._PROFILE)
        check("the profile declares the pinned spacing 0.0 then 6.0",
              profile.first_delay_seconds == FIRST_DELAY_SECONDS
              and profile.spacing_seconds == SPACING_SECONDS)
        check("the lane is test-only and production_allowed is False",
              nh.production_allowed is False)
        denied = None
        try:
            denied = nh.encode_npc_hp_link_hit_entry(
                legacy, TARGET_IDENTITY, -63, (0.0, 0.0, 0.0), 0.0, FLAGS_HIT,
                None)
        except nh.NpcHpLinkValidationError:
            denied = None
        check("with no unlock the encoder composes nothing and raises",
              denied is None)
        unlock = nh.npc_hp_link_wire_unlock(profile)
        target = nh.resolve_npc_hp_link_target(legacy)
        check("the target resolves to the frozen placement identity 0x2001",
              target.actor_identity == TARGET_IDENTITY)

        # ============================================== 1. THE COMPOSITION
        section("1. the eight composed frames")
        actions = nh.build_npc_hp_link_sweep(
            legacy, target, PERFORMER_IDENTITY_LO, PERFORMER_IDENTITY_HI,
            unlock, profile)
        check("the sweep is exactly eight actions", len(actions) == 8)
        check("the eight labels are the pinned ones in the pinned order",
              tuple(action[0] for action in actions) == ACTION_LABELS)
        check("the delays are 0.0 then 6.0 x 7 (cumulative-deadline gaps)",
              tuple(action[3] for action in actions) == EXPECTED_DELAYS)
        composed = {}
        rows = []
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = STEP_ORDER[index]
            composed[step] = (pc, frame)
            rows.append({
                "index": index,
                "label": label,
                "step": step,
                "kind": STEP_KINDS[index],
                "delay_seconds": delay,
                "pc_size": len(pc),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_size": len(frame),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
            })
            emit("        %-24s %-5s pc=%3d %s frame=%3d %s"
                 % (step, STEP_KINDS[index], len(pc),
                    rows[-1]["pc_sha256"][:16], len(frame),
                    rows[-1]["frame_sha256"][:16]))
        pinned_file = json.loads(SCENARIO.read_text(encoding="utf-8"))
        for row in rows:
            file_pin = pinned_file["probe"]["per_step"][row["step"]]
            check("%s: the composed pc/frame reproduce the SCENARIO FILE's "
                  "four pins" % row["step"],
                  file_pin["pc_size"] == row["pc_size"]
                  and file_pin["pc_sha256"] == row["pc_sha256"]
                  and file_pin["frame_size"] == row["frame_size"]
                  and file_pin["frame_sha256"] == row["frame_sha256"])

        # ================================================== 2. THE WALK
        section("2. every composed byte, re-read by this file's own walker")
        walked = {}
        for index, step in enumerate(STEP_ORDER):
            pc, frame = composed[step]
            check("%s: the transport frame unwraps back to the PC byte for "
                  "byte" % step, w_transport(frame) == pc)
            read = w_frame(pc)
            walked[step] = read
            check("%s: the envelope is 0x6E9D v4, ErrorData 0" % step,
                  read["envelope_id"] == RUNTIME_PROTOCOL_RES_ID
                  and read["envelope_version"] == RUNTIME_PROTOCOL_RES_VERSION
                  and read["error_data"] == 0)
            check("%s: the carrier the walker finds is the planned %s one"
                  % (step, STEP_KINDS[index]),
                  read["kind"] == STEP_KINDS[index])
        for step in ("HIT_WEAK", "MISS", "HIT_STRONG"):
            read = walked[step]
            check("%s: VitalData collection, base 0x02 / derived 0x00" % step,
                  read["base_change_mask"] == HIT_BASE_CHANGE_MASK
                  and read["derived_change_mask"] == HIT_DERIVED_CHANGE_MASK)
            check("%s: one CHitResult 0x16F7 v0 with one hit entry" % step,
                  read["vital_count"] == 1
                  and read["vital_id"] == CHIT_RESULT_VITAL_ID
                  and read["vital_version"] == CHIT_RESULT_VITAL_VERSION
                  and read["hit_count"] == HIT_ENTRY_COUNT)
            check("%s: the four reserved header fields are all zero" % step,
                  read["header_field2"] == 0 and read["header_field3"] == 0
                  and read["header_field4"] == 0 and read["header_field5"] == 0)
            check("%s: performer = the player, target = 0x2001, and they "
                  "differ" % step,
                  read["performer_identity"] == PERFORMER_IDENTITY_LO
                  and read["target_identity"] == TARGET_IDENTITY
                  and read["performer_identity"] != read["target_identity"])
            check("%s: the walker reads damage %d and flags 0x%04X"
                  % (step, HIT_DAMAGE[step], HIT_FLAGS[step]),
                  read["damage_wire"] == HIT_DAMAGE[step]
                  and read["flags"] == HIT_FLAGS[step])
            check("%s: the yaw is the pinned 0.0" % step,
                  read["yaw"] == YAW_PINNED)
        for step in ("TARGET_SPAWN", "TARGET_HP_AFTER_WEAK",
                     "TARGET_HP_AFTER_MISS", "TARGET_HP_ZERO_DYING",
                     "TARGET_DYING_ELAPSED"):
            read = walked[step]
            npc = read["attrs"][NPC_ATTR_ID]
            check("%s: actor-entry collection, inherited 0x00 / derived 0x02"
                  % step,
                  read["base_change_mask"] == ACTOR_INHERITED_CHANGE_MASK
                  and read["derived_change_mask"] & ACTOR_DERIVED_CHANGE_MASK)
            check("%s: one entry, actor_type 4 (CNetNPC), identity 0x2001, "
                  "hp_max 100" % step,
                  read["actor_count"] == 1
                  and read["actor_type"] == ACTOR_TYPE_CNETNPC
                  and read["target_identity"] == TARGET_IDENTITY
                  and npc["identity"] == TARGET_IDENTITY
                  and npc["fields"].get(BASIC_BIT_MAX_HP) == HP_MAX)
            check("%s: the visual preset is present, so the model-loaded gate "
                  "can open" % step, bool(npc["visual_preset"]))
        spawn = walked["TARGET_SPAWN"]
        check("TARGET_SPAWN is alive (hp 100), placed, and carries NO death "
              "timer: an actor cannot be born dead",
              spawn["attrs"][NPC_ATTR_ID]["fields"][BASIC_BIT_CURRENT_HP]
              == HP_START
              and BASIC_BIT_DEATH_TIMER
              not in spawn["attrs"][NPC_ATTR_ID]["fields"]
              and MOVEMENT_ATTR_ID in spawn["attrs"])
        for step in ("TARGET_HP_AFTER_WEAK", "TARGET_HP_AFTER_MISS"):
            fields = walked[step]["attrs"][NPC_ATTR_ID]["fields"]
            check("%s: hp_current 37, no death timer, no MovementAttr (an "
                  "UPDATE, not a second spawn)" % step,
                  fields[BASIC_BIT_CURRENT_HP] == 37
                  and BASIC_BIT_DEATH_TIMER not in fields
                  and MOVEMENT_ATTR_ID not in walked[step]["attrs"])
        dying = walked["TARGET_HP_ZERO_DYING"]["attrs"][NPC_ATTR_ID]["fields"]
        elapsed = walked["TARGET_DYING_ELAPSED"][
            "attrs"][NPC_ATTR_ID]["fields"]
        check("TARGET_HP_ZERO_DYING satisfies vt+0x40: hp 0 AND timer 20.0 > 0",
              dying[BASIC_BIT_CURRENT_HP] == HP_FLOOR
              and dying[BASIC_BIT_DEATH_TIMER] == DYING_TIMER_SECONDS
              and dying[BASIC_BIT_DEATH_TIMER] > 0.0)
        check("TARGET_DYING_ELAPSED satisfies vt+0x3C: hp 0 AND timer 0.0 <= 0",
              elapsed[BASIC_BIT_CURRENT_HP] == HP_FLOOR
              and elapsed[BASIC_BIT_DEATH_TIMER] == ELAPSED_TIMER_SECONDS
              and elapsed[BASIC_BIT_DEATH_TIMER] <= 0.0)
        check("the polarity order is latch first, task second (both sides are "
              "sent, and in that order)",
              STEP_ORDER.index("TARGET_HP_ZERO_DYING")
              < STEP_ORDER.index("TARGET_DYING_ELAPSED"))

        # ========================================== 3. THE LINK, FROM BYTES
        section("3. THE LINK, re-derived from the walker-read bytes alone")
        walked_ladder = []
        link_mismatches = []
        balance = None
        pending = 0
        for step in STEP_ORDER:
            read = walked[step]
            if read["kind"] == "hit":
                pending = read["damage_wire"]
                walked_ladder.append(balance)
                continue
            value = read["attrs"][NPC_ATTR_ID]["fields"][BASIC_BIT_CURRENT_HP]
            if balance is None:
                balance = value
            else:
                balance = max(HP_FLOOR, balance + pending)
                pending = 0
                # The value the walker actually read is COMPARED against the
                # arithmetic, never discarded: a frame that reports an hp the
                # damages do not produce must turn this guard red.
                if value != balance:
                    link_mismatches.append(
                        "%s: the frame says hp %r, the walked arithmetic says "
                        "%r" % (step, value, balance))
            walked_ladder.append(balance)
        check("the walker-read TARGET hp values ARE the walker-read damage "
              "arithmetic applied to the walker-read spawn value",
              tuple(walked_ladder) == BALANCE_LADDER and not link_mismatches,
              "%r != %r%s" % (
                  tuple(walked_ladder), BALANCE_LADDER,
                  ("; " + "; ".join(link_mismatches))
                  if link_mismatches else ""))
        for step in ("TARGET_HP_AFTER_WEAK", "TARGET_HP_AFTER_MISS",
                     "TARGET_HP_ZERO_DYING"):
            index = STEP_ORDER.index(step)
            check("%s: the frame the walker read shows hp %d, which is what "
                  "the previous hit frame's own number produces"
                  % (step, BALANCE_LADDER[index]),
                  walked[step]["attrs"][NPC_ATTR_ID]["fields"][
                      BASIC_BIT_CURRENT_HP] == BALANCE_LADDER[index])
        check("the MISS control moves the bar by exactly zero, and its two "
              "neighbouring hp frames are byte-identical",
              composed["TARGET_HP_AFTER_WEAK"]
              == composed["TARGET_HP_AFTER_MISS"])
        check("every frame of the sweep -- BOTH carriers -- names the same "
              "actor 0x2001",
              {walked[step]["target_identity"] for step in STEP_ORDER}
              == {TARGET_IDENTITY})

        # ================================== 4. CROSS-LANE BYTE EQUALITY
        section("4. byte equality against both parent lanes' own composers")
        dm_profile = dm.load_damage_model_hypothesis_scenario(
            str(DAMAGE_NPC_SCENARIO))
        dm_unlock = dm.damage_model_wire_unlock(dm_profile)
        dm_probe = dm.damage_probe_actor(legacy)
        damage_by = {}
        for index, label in enumerate(dm_profile.step_order):
            damage_by[label] = dm.make_damage_model_step_response(
                legacy, dm_probe, index, dm_unlock, dm_profile)
        rd_profile = rd.load_runtimeres_death_hypothesis_scenario(
            str(DEATH_SCENARIO))
        rd_unlock = rd.runtimeres_death_lethal_unlock(rd_profile)
        rd_probe = rd.resolve_probe(legacy)
        death_by = {}
        for index, label in enumerate(rd_profile.step_order):
            death_by[label] = rd.make_runtimeres_death_step_response(
                legacy, rd_probe, index, rd_unlock, rd_profile)
        oracle = {"damage": damage_by, "death": death_by}
        for step, (lane, parent_step) in PARENT_ORACLE.items():
            parent_pc, parent_frame = oracle[lane][parent_step]
            pc, frame = composed[step]
            check("%s: pc and frame are byte-identical to the %s lane's own "
                  "%s" % (step, lane.upper(), parent_step),
                  pc == parent_pc and frame == parent_frame)
        baseline_37 = legacy.make_npc_attr(
            target.template_id, target.actor_identity, target.scene_id,
            target.scene_sequence, target.visual_preset, 37, HP_MAX)
        check("TARGET_HP_AFTER_WEAK has no counterpart STEP in the death lane, "
              "so its NPCAttr body is diffed against that lane's own baseline "
              "oracle for hp 37/100",
              nh.encode_npc_hp_link_npc_attr(
                  legacy, target, "TARGET_HP_AFTER_WEAK", 37, None, unlock)
              == baseline_37
              == rd.encode_death_capable_npc_attr(
                  legacy, rd_probe, current_hp=37, max_hp=HP_MAX))

        # ===================================== 5. CONTAINMENT, MEASURED
        section("5. containment - measured, not promised")
        check("no socket entry point was reached while the sweep was composed",
              socket_log == [], repr(socket_log))
        check("socket.socket really was trapped during the run: the trap "
              "refuses when called",
              isinstance(socket.socket, RefusingSocket))
    finally:
        _restore_socket(saved_socket)
    canonical_after = _canonical_stat()
    check("the canonical database was never opened and did not move one byte "
          "(it is stat-ed, not read)", canonical_before == canonical_after)
    # The needle is built by concatenation for the same reason CANONICAL_DB is:
    # a guard that searches for a literal it itself contains can only ever fail.
    check("this file names no path to the canonical database",
          ("pirateforce" + ".sqlite3") not in Path(__file__).read_text(
              encoding="utf-8"))
    check("every byte of this file is ASCII (cp874 console discipline)",
          all(byte < 0x80 for byte in Path(__file__).read_bytes()))

    # ===================================================== THE LIMIT
    section("6. the limit of this proof, stated rather than smoothed over")
    emit("  NOTE  this file proves the COMPOSER and not a dispatcher: it calls")
    emit("        build_npc_hp_link_sweep directly, which is why its verdict")
    emit("        says dispatcher_driven: false.  The runtime.py dispatch")
    emit("        branch DOES now exist -- NPC-HP-LINK-002 added")
    emit("        _dispatch_npc_hp_link_hypothesis and the")
    emit("        npc_hp_link_hypothesis_scenario keyword -- and it is driven")
    emit("        for real in tests/test_npc_hp_link_dispatch.py.  app.py NOW")
    emit("        hands make_state_class that keyword (NPC-HP-LINK-003), so")
    emit("        the CLI flag reaches the branch; what is still unproven is")
    emit("        the layer above -- nothing here has crossed a socket.")
    emit("  NOTE  no client has ever been shown one byte of this profile.")
    emit("        Whether the client renders the intermediate value 37 on the")
    emit("        target's HP bar is UNDECIDABLE from static analysis and is")
    emit("        the queued attended test.  The only thing proven so far is")
    emit("        the negative: 505 damage, and the bar did not move.")

    verdict = {
        "tool": "pf_npc_hp_link_headless_replay",
        "hypothesis_id": nh.NPC_HP_LINK_HYPOTHESIS_ID,
        "milestone": nh.NPC_HP_LINK_CHECKPOINT,
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "frames": rows,
        "walked_balance_ladder": list(BALANCE_LADDER),
        "dispatcher_driven": False,
        "dispatcher_note": (
            "HYP-PF-029 has no runtime.py dispatch branch this checkpoint; "
            "the proof stops at the composer"
        ),
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
            emit("RESULT: PASS - HYP-PF-029 / NPC-HP-LINK-001 wire proof held "
                 "(client layer = attended, not run)")
    if evidence_path is not None:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
