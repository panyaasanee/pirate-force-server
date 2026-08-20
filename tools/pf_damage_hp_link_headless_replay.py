#!/usr/bin/env python3
"""DAMAGE-HP-LINK-001: headless wire proof for the HYP-PF-026 linked sweep.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in scenario
``scenarios/damage_hp_link_hypothesis_link_sweep.json`` and a throwaway COPY of
a database, answers ONE accepted client frame with the exact EIGHT-frame
``GSCN_RunTimeProtocolRes`` (id 0x6E9D version 4) sweep that alternates the two
proven carriers, and that those frames are

  (a) **byte-for-byte** the frames ``build_damage_hp_link_sweep`` composes for
      the SAME session identity -- same labels, same PCs, same framed bytes,
      same delays, compared with ``==`` on the bytes objects; and
  (b) independently readable, by a walker written in THIS file that imports
      none of the module's decoder and reads every dispatched byte from byte 0,
      as the hit -> bleed -> die sentence the design says it is:

        HP_BASELINE     hp 100/100                         delay 0.0
        HIT_WEAK        damage  -63  flags 0x0001           delay 15.0
        HP_AFTER_WEAK   hp_current 37   (100 - 63)          delay 15.0
        MISS            damage    0  flags 0x0000  control   delay 15.0
        HP_AFTER_MISS   hp_current 37   (a miss moves none)  delay 15.0
        HIT_STRONG      damage -379  flags 0x0001           delay 15.0
        HP_ZERO_DYING   hp_current 0 + death timer 20.0      delay 15.0
        DYING_ELAPSED   death timer 0.0                      delay 15.0

      The point of the lane, computed from the BYTES and not from the module:
      the walker-read hp values equal the walker-read damage arithmetic applied
      to the walker-read baseline (100 + -63 = 37; 37 + 0 = 37; 37 + -379
      clamps to 0), which is the linked balance made visible.

THE DATABASE IS A COPY, ALWAYS -- AND THE IDENTITY IS PINNED
-----------------------------------------------------------
The dispatcher refuses this lane unless the session's selected identity is
exactly the canonical smoke identity 0x10010001/0 the pins were composed for,
so the bytes a tester sees are the pinned bytes byte for byte or nothing.
``--db <path>`` (default ``state/pirateforce.sqlite3``) is copied with
``shutil.copyfile`` into a fresh ``tempfile.mkdtemp`` directory; every
connection is made against that copy, the copy is deleted on exit, and the
source file's SHA-256 is asserted unchanged at the end of the run.  The pinned
session logs in as account "localtest", whose first character IS 0x10010001; if
that account has no character yet on the copy, the same pinned V25 create wire
the neighbour replays use establishes it, committing exactly that identity.  A
SECOND session on a different login lands on a different identity, and this file
proves the dispatcher then refuses with ``identity_not_pinned_no_reply``.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of this profile.**  The link is OUR design: the original server
is closed, was never published, and no capture shows damage linked to hit
points in either direction, so there is nothing to recover.  It claims nothing
about the original server ever linking these frames, opens no write path to HP
(no HP column exists and none is added), and says nothing about any death-window
exit path.  ``production_allowed`` is False everywhere it appears.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.  The
file named by ``--db`` is read once to copy it and once to hash it, and is never
opened by SQLite; everything runs on the temporary copy, which is deleted on
exit.  While the sweep runs, ``socket.socket`` and its neighbours are replaced
with objects that record and refuse, so "no socket" is a measurement here and
not an assurance.  No repository file is written unless ``--evidence <path>`` is
handed in.  Pure stdlib.

Usage:
    py -3 tools/pf_damage_hp_link_headless_replay.py
    py -3 tools/pf_damage_hp_link_headless_replay.py --json
    py -3 tools/pf_damage_hp_link_headless_replay.py --db state/pirateforce.sqlite3
    py -3 tools/pf_damage_hp_link_headless_replay.py \
        --evidence reports/damage_hp_link001_headless.json

Every byte this file prints is ASCII: it is expected to run on a Windows console
under code page cp874, where one non-ASCII character is a crash.

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the list.
Exit 2 = the database file named on the command line does not exist.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import struct
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
    CHAT_INPUT_VITAL_ID,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
# The module under test.  This tool calls its loader, its unlock derivation and
# its encoder (once, to compose the OTHER side of the byte-for-byte comparison)
# and reads its nonclaims.  It deliberately NEVER calls
# decode_damage_hp_link_frame or validate_damage_hp_link_sweep: every dispatched
# byte below is read by this file's own walker, so a symmetrical bug in the
# encoder's reader cannot hide.
from pirateforce_foundation import damage_hp_link_hypothesis as dh  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "damage_hp_link_hypothesis_link_sweep.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"
# The login whose first character IS the pinned smoke identity 0x10010001.
PINNED_LOGIN_TOKEN = "localtest"
ALT_LOGIN_TOKEN = "hp_link_alt_identity"

SWEEP_EVENT = "damage_hp_link_hypothesis_link_sweep_sent"
REPEAT_EVENT = "damage_hp_link_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "damage_hp_link_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "damage_hp_link_hypothesis_wrong_sequence_no_reply"
WRONG_TEXT_EVENT = "damage_hp_link_hypothesis_wrong_text_no_reply"
IDENTITY_NOT_PINNED_EVENT = (
    "damage_hp_link_hypothesis_identity_not_pinned_no_reply"
)
EVENT_PREFIX = "damage_hp_link_hypothesis_"


# ---------------------------------------------------------------------------
# This reader's own constants.  Written out as literals rather than read off the
# module, so section 0 can measure the module against THEM: a guard that asks
# the encoder what to expect and then checks the encoder against its own answer
# is a restatement, not a check.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
BASE_CHANGE_MASK = 0x02
DERIVED_CHANGE_MASK = 0x00
FRAME_MAGIC = 0x5F253EAC

TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32
TAG_ENVELOPE_VERSION = 0x08
TAG_WSTRING = 0x48
TAG_EXTRA_GROUP = 0x05

CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0
UPDATE_ATTR_VITAL_ID = 0x309A
UPDATE_ATTR_VITAL_VERSION = 0
ACTOR_ATTR_ID = 0x12AD
EXTRA_GROUP_VALUE = 1
HIT_ENTRY_COUNT = 1
YAW_PINNED = 0.0

FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001

PINNED_IDENTITY_LO = 0x10010001
PINNED_IDENTITY_HI = 0

HP_START = 100
HP_MAX = 100
HP_FLOOR = 0
BASELINE_SCENE_ID = 1
BASELINE_SCENE_SEQUENCE = 0
BASELINE_CHARACTER_NAME = "test01"
BASELINE_CASH = 10000

# name -> (mask_bit, wire_tag, kind)
HP_FIELDS = {
    "hp_current": (0x0004, 0x14, "u32"),
    "hp_max": (0x0008, 0x14, "u32"),
    "hp_death_timer": (0x0080, 0x2A, "f32"),
    "scene_id": (0x0100, 0x12, "u16"),
    "scene_sequence": (0x0200, 0x32, "qword"),
    "cash": (0x00000800, 0x32, "qword"),
    "character_name": (0x01000000, 0x48, "wstring"),
}
BASIC_ORDER = ("hp_current", "hp_max", "hp_death_timer", "scene_id",
               "scene_sequence")
ACTOR_ORDER = ("cash", "character_name")

STEP_ORDER = (
    "HP_BASELINE", "HIT_WEAK", "HP_AFTER_WEAK", "MISS", "HP_AFTER_MISS",
    "HIT_STRONG", "HP_ZERO_DYING", "DYING_ELAPSED",
)
ACTION_LABEL_PREFIX = "HYP_PF_026_HP_LINK_"
ACTION_LABELS = tuple(ACTION_LABEL_PREFIX + step for step in STEP_ORDER)
EXPECTED_DELAYS = (0.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0, 15.0)
HIT_STEPS = {"HIT_WEAK": FLAGS_HIT, "MISS": FLAGS_MISS, "HIT_STRONG": FLAGS_HIT}
EXPECTED_DAMAGE = {"HIT_WEAK": -63, "MISS": 0, "HIT_STRONG": -379}
EXPECTED_HP = {
    "HP_BASELINE": 100, "HP_AFTER_WEAK": 37, "HP_AFTER_MISS": 37,
    "HP_ZERO_DYING": 0, "DYING_ELAPSED": 0,
}
EXPECTED_TIMER = {"HP_ZERO_DYING": 20.0, "DYING_ELAPSED": 0.0}
LADDER_INDEX = {
    "HP_BASELINE": 0, "HP_AFTER_WEAK": 2, "HP_AFTER_MISS": 4,
    "HP_ZERO_DYING": 6, "DYING_ELAPSED": 7,
}


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _scalar(pc, cursor, tag, width, label):
    if cursor + 1 + width > len(pc):
        raise WalkError("%s: truncated at %d" % (label, cursor))
    if pc[cursor] != tag:
        raise WalkError(
            "%s: tag 0x%02X != 0x%02X at %d" % (label, pc[cursor], tag, cursor))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def walk_transport(frame):
    """Unwrap the outer transport frame (u32 magic + u32 length + one raw
    literal stream) back to its PC, byte for byte."""
    if type(frame) is not bytes or len(frame) < 8:
        raise WalkError("transport: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != FRAME_MAGIC:
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
    cursor = 0
    raw, cursor = _scalar(body, cursor, TAG_U8, 1, "db mask")
    if raw[0] != 0x01:
        raise WalkError("db mask bit != 0x01")
    raw, cursor = _scalar(body, cursor, TAG_QWORD, 8, "identity")
    identity = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, TAG_U16, 2, "basic mask")
    basic_mask = struct.unpack("<H", raw)[0]
    values = {}
    for name in BASIC_ORDER:
        bit, tag, kind = HP_FIELDS[name]
        if not basic_mask & bit:
            continue
        basic_mask &= ~bit
        width = {"u16": 2, "u32": 4, "qword": 8, "f32": 4}[kind]
        raw, cursor = _scalar(body, cursor, tag, width, name)
        values[name] = (struct.unpack("<f", raw)[0] if kind == "f32"
                        else int.from_bytes(raw, "little"))
    if basic_mask:
        raise WalkError("basic mask leftover 0x%X" % basic_mask)
    raw, cursor = _scalar(body, cursor, TAG_QWORD, 8, "actor mask")
    actor_mask = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, TAG_EXTRA_GROUP, 1, "extra group")
    if raw[0] != EXTRA_GROUP_VALUE:
        raise WalkError("extra group flag")
    for name in ACTOR_ORDER:
        bit, tag, kind = HP_FIELDS[name]
        if not actor_mask & bit:
            continue
        actor_mask &= ~bit
        if kind == "wstring":
            if cursor + 5 > len(body) or body[cursor] != TAG_WSTRING:
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
    """Read one dispatched PC from byte 0, whichever carrier it holds."""
    if type(pc) is not bytes:
        raise WalkError("the pc is not bytes")
    cursor = 0
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "envelope id")
    result = {"envelope_id": struct.unpack("<H", raw)[0]}
    raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "envelope error data")
    result["error_data"] = struct.unpack("<I", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_ENVELOPE_VERSION, 1, "env version")
    result["envelope_version"] = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "base change mask")
    result["base_change_mask"] = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital count")
    if struct.unpack("<H", raw)[0] != 1:
        raise WalkError("vital count != 1")
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital id")
    vital_id = struct.unpack("<H", raw)[0]
    result["vital_id"] = vital_id
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "vital version")
    result["vital_version"] = raw[0]
    if vital_id == CHIT_RESULT_VITAL_ID:
        result["kind"] = "hit"
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "performer")
        result["performer_identity"] = struct.unpack("<Q", raw)[0]
        for name in ("hf2", "hf3"):
            raw, cursor = _scalar(pc, cursor, TAG_U16, 2, name)
            result[name] = struct.unpack("<H", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "hf4")
        result["hf4"] = struct.unpack("<I", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "hf5")
        result["hf5"] = raw[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "entry count")
        if struct.unpack("<H", raw)[0] != HIT_ENTRY_COUNT:
            raise WalkError("hit entry count != 1")
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "target")
        result["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "damage")
        # SIGNED: the client's cmp/jge sites only make sense signed.
        result["damage_signed"] = struct.unpack("<i", raw)[0]
        result["damage_unsigned"] = struct.unpack("<I", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = _scalar(pc, cursor, TAG_F32, 4, "position %s" % axis)
            position.append(struct.unpack("<f", raw)[0])
        result["position"] = tuple(position)
        raw, cursor = _scalar(pc, cursor, TAG_F32, 4, "yaw")
        result["yaw"] = struct.unpack("<f", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "flags")
        result["flags"] = struct.unpack("<H", raw)[0]
    elif vital_id == UPDATE_ATTR_VITAL_ID:
        result["kind"] = "hp"
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "attr count")
        if struct.unpack("<H", raw)[0] != 1:
            raise WalkError("attr count != 1")
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "attr id")
        if struct.unpack("<H", raw)[0] != ACTOR_ATTR_ID:
            raise WalkError("attr id != ActorAttr")
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "attr body length")
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
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
    result["derived_change_mask"] = raw[0]
    if cursor != len(pc):
        raise WalkError("trailing bytes after derived change mask")
    return result


# ---------------------------------------------------------------------------
# Containment helpers.
# ---------------------------------------------------------------------------
class SocketOpened(RuntimeError):
    """Something tried to open a socket while the sweep was running."""


class _SocketTrap:
    """Records every attempt to build a socket, and refuses all of them."""

    def __init__(self):
        self.attempts = []
        self._saved = {}

    def _refuse(self, name):
        def _call(*_args, **_kwargs):
            self.attempts.append(name)
            raise SocketOpened(
                "the HYP-PF-026 headless replay opens no socket (%s)" % name)
        return _call

    def __enter__(self):
        for name in ("socket", "socketpair", "create_connection",
                     "create_server"):
            if hasattr(socket, name):
                self._saved[name] = getattr(socket, name)
                setattr(socket, name, self._refuse("socket." + name))
        return self

    def __exit__(self, *_exc):
        for name, original in self._saved.items():
            setattr(socket, name, original)
        return False


def directory_digest(folder):
    """Name, size and sha256 of every file in a folder, sorted.  The store runs
    in WAL mode, so the -wal and -shm sidecars are part of the database state."""
    rows = []
    for entry in sorted(os.listdir(folder)):
        path = folder / entry
        if not path.is_file():
            continue
        data = path.read_bytes()
        rows.append((entry, len(data), hashlib.sha256(data).hexdigest().upper()))
    return rows


def table_row_counts(db_path):
    """Row count of every user table.  Opens the COPY, never the source."""
    db = sqlite3.connect(str(db_path))
    try:
        names = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {name: db.execute('SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
                for name in names}
    finally:
        db.close()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def main():
    want_json = "--json" in sys.argv
    evidence_path = None
    if "--evidence" in sys.argv:
        evidence_path = Path(sys.argv[sys.argv.index("--evidence") + 1])
    db_source = DEFAULT_DB
    if "--db" in sys.argv:
        at = sys.argv.index("--db") + 1
        db_source = Path(sys.argv[at]) if at < len(sys.argv) else DEFAULT_DB
    db_source = db_source.resolve()
    if not db_source.is_file():
        print("no database file at %s" % ascii(str(db_source)))
        return 2

    failures = []
    guards = 0

    def check(label, condition, detail=""):
        nonlocal guards
        guards += 1
        if condition:
            if not want_json:
                print("  PASS  %s" % label)
        else:
            failures.append(label)
            if not want_json:
                print("  FAIL  %s %s" % (label, detail))

    legacy = load_legacy(str(LEGACY_PATH))
    scenario = dh.load_damage_hp_link_hypothesis_scenario(str(SCENARIO))
    pinned = json.loads(SCENARIO.read_text(encoding="utf-8"))
    unlock = dh.damage_hp_link_wire_unlock(scenario)

    # -------------------------------------------------------------------
    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("envelope id 0x6E9D and version 4 agree with the module",
          RUNTIME_PROTOCOL_RES_ID == dh.RUNTIME_PROTOCOL_RES_ID
          and RUNTIME_PROTOCOL_RES_VERSION == dh.RUNTIME_PROTOCOL_RES_VERSION)
    check("BASE change mask 0x02 and DERIVED 0x00 agree with the module",
          BASE_CHANGE_MASK == dh.HP_LINK_BASE_CHANGE_MASK
          and DERIVED_CHANGE_MASK == dh.HP_LINK_DERIVED_CHANGE_MASK)
    check("the transport frame magic 0x5F253EAC agrees with the module",
          FRAME_MAGIC == dh.HP_LINK_FRAME_MAGIC)
    check("CHitResult 0x16F7 v0 agrees with the module",
          CHIT_RESULT_VITAL_ID == dh.CHIT_RESULT_VITAL_ID
          and CHIT_RESULT_VITAL_VERSION == dh.CHIT_RESULT_VITAL_VERSION)
    check("UpdateAttrVital 0x309A v0 and ActorAttr 0x12AD agree with the module",
          UPDATE_ATTR_VITAL_ID == dh.HP_LINK_UPDATE_ATTR_VITAL_ID
          and UPDATE_ATTR_VITAL_VERSION == dh.HP_LINK_UPDATE_ATTR_VITAL_VERSION
          and ACTOR_ATTR_ID == dh.HP_LINK_ACTOR_ATTR_ID)
    check("the flag words 0x0000 / 0x0001 agree with the module",
          FLAGS_MISS == dh.FLAGS_MISS and FLAGS_HIT == dh.FLAGS_HIT)
    check("the pinned probe identity 0x10010001/0 agrees with the module",
          PINNED_IDENTITY_LO == dh.HP_LINK_PROBE_IDENTITY_LO
          and PINNED_IDENTITY_HI == dh.HP_LINK_PROBE_IDENTITY_HI)
    check("the HP start/max/floor 100/100/0 agree with the module",
          HP_START == dh.HP_LINK_HP_START and HP_MAX == dh.HP_LINK_HP_MAX
          and HP_FLOOR == dh.HP_LINK_HP_FLOOR)
    check("the dying / elapsed timer 20.0 / 0.0 agree with the module",
          EXPECTED_TIMER["HP_ZERO_DYING"] == dh.HP_LINK_DYING_TIMER_SECONDS
          and EXPECTED_TIMER["DYING_ELAPSED"]
          == dh.HP_LINK_TIMER_ELAPSED_SECONDS)
    check("the step order and action labels agree with the module",
          STEP_ORDER == dh.DAMAGE_HP_LINK_STEP_ORDER
          and ACTION_LABELS == dh.DAMAGE_HP_LINK_ACTION_LABELS
          and ACTION_LABEL_PREFIX == dh.DAMAGE_HP_LINK_ACTION_LABEL_PREFIX)
    check("the delays 0.0 then 15.0 agree with the loaded scenario",
          EXPECTED_DELAYS[0] == scenario.first_delay_seconds
          and all(d == scenario.spacing_seconds for d in EXPECTED_DELAYS[1:])
          and scenario.step_order == STEP_ORDER)
    check("the HP ladder 100/100/37/37/37/37/0/0 agrees with the module",
          tuple(EXPECTED_HP[s] for s in ("HP_BASELINE", "HP_AFTER_WEAK",
                "HP_AFTER_MISS", "HP_ZERO_DYING"))
          == (100, 37, 37, 0)
          and dh.HP_LINK_BALANCE_LADDER == (100, 100, 37, 37, 37, 37, 0, 0))
    check("the two pinned damage numbers -63 / -379 agree with the module",
          EXPECTED_DAMAGE["HIT_WEAK"] == dh.HP_LINK_DAMAGE_PINNED["MOB_WEAK"]
          and EXPECTED_DAMAGE["HIT_STRONG"]
          == dh.HP_LINK_DAMAGE_PINNED["MOB_STRONG"])
    check("the lane is not production-allowed, and the file says so too",
          dh.production_allowed is False
          and pinned["production_allowed"] is False
          and pinned["test_only"] is True)
    check("the lane is HYP-PF-026 behind kwarg damage_hp_link_hypothesis_scenario",
          dh.DAMAGE_HP_LINK_HYPOTHESIS_ID == "HYP-PF-026"
          and dh.DAMAGE_HP_LINK_DISPATCH_KWARG
          == "damage_hp_link_hypothesis_scenario")
    check("the scenario file's per_step pins ARE the module's pins",
          all(pinned["probe"]["per_step"][step] == dh.DAMAGE_HP_LINK_PINS[step]
              for step in STEP_ORDER))

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_damage_hp_link001_")
    rows = []
    trap = _SocketTrap()
    session_identity = None
    dir_before = dir_after = None
    counts_before = counts_after = None
    try:
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real "
                  "pinned session on it --")
        db_path = Path(tmp) / "damage_hp_link001.sqlite3"
        shutil.copyfile(db_source, db_path)
        check("the copy lives in the temporary directory, not at the source",
              db_path.is_file() and db_path.resolve() != db_source)
        check("the copy is byte-identical to the source before any use",
              sha256_file(db_path) == source_sha_before)
        store = SQLiteStore(db_path, ROOT / "migrations")
        check("the store is opened on the copy path ONLY",
              Path(store.path).resolve() == db_path.resolve()
              and Path(store.path).resolve() != db_source)
        store.migrate()
        projector = LegacyProjector(legacy)
        lifecycle = CharacterLifecycle(
            store,
            Position(1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                     legacy.V135_PLAYER_Z),
            legacy.extract_avatar_attr_wire_from_actor,
        )

        def boot(token, *, enabled=True, select=True, ready=True):
            """Login, a V25 create ONLY when the login account has no character
            yet, start game on the last character, then the sequence flags.  The
            pinned login lands on the smoke identity 0x10010001; any other login
            lands on a fresh account and therefore a different identity."""
            state_type = make_state_class(
                legacy, lifecycle, projector,
                damage_hp_link_hypothesis_scenario=(
                    scenario if enabled else None),
            )
            state = state_type(token)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc(token)))
            if select:
                characters = store.list_characters(state.foundation.account_id)
                if not characters:
                    created = state.dispatch(
                        legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
                    assert created and created[0][0] == (
                        "FOUNDATION_CREATE_COMMITTED")
                    characters = store.list_characters(
                        state.foundation.account_id)
                selected = state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(characters[-1].selector)))
                assert selected and selected[0][0] == (
                    "FOUNDATION_SELECTED_START_GAME")
            state.runtime_ack_sent = ready
            return state

        def trigger(probe="probe1"):
            return legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe])

        state = boot(PINNED_LOGIN_TOKEN)
        selected = state.foundation.selected
        check("a character is selected on the copy", selected is not None)
        session_identity = (
            ((int(selected.identity_hi) & 0xFFFFFFFF) << 32)
            | (int(selected.identity_lo) & 0xFFFFFFFF))
        check("the selected identity is the pinned smoke identity 0x10010001/0",
              (selected.identity_lo, selected.identity_hi)
              == (PINNED_IDENTITY_LO, PINNED_IDENTITY_HI),
              hex(session_identity))
        check("the sequence flags the dispatcher gates on are set",
              state.teleport_sent is True and state.runtime_ack_sent is True)

        # The encoder's own composition, OUTSIDE the dispatcher, for the SAME
        # session identity.  This is what every dispatched byte is measured
        # against.  A second composition against a DIFFERENT identity makes
        # "the frames name the session" a falsifiable statement.
        expected = dh.build_damage_hp_link_sweep(
            legacy, selected.identity_lo, selected.identity_hi, unlock, scenario)
        other_sweep = dh.build_damage_hp_link_sweep(
            legacy, (selected.identity_lo ^ 0x00ABCDEF) & 0xFFFFFFFF, 0,
            unlock, scenario)

        dir_before = directory_digest(Path(tmp))
        counts_before = table_row_counts(db_path)
        db_before_sha = sha256_file(db_path)

        if not want_json:
            print("-- 2. one accepted client frame in, eight frames out --")
        with trap:
            actions = state.dispatch(trigger())
        # Measure the copy immediately after the sweep dispatch, BEFORE the
        # later refusal boots (which legitimately create fresh accounts on the
        # copy).  These three readings bracket only the sweep.
        dir_after = directory_digest(Path(tmp))
        db_after_sha = sha256_file(db_path)
        counts_after = table_row_counts(db_path)

        check("the dispatcher answered with exactly eight actions",
              len(actions) == 8, str(len(actions)))
        check("in the scenario's pinned order, with the pinned labels",
              tuple(row[0] for row in actions) == ACTION_LABELS,
              str([row[0] for row in actions]))
        check("with the pinned delays 0.0 then 15.0 x7",
              tuple(row[3] for row in actions) == EXPECTED_DELAYS,
              str([row[3] for row in actions]))
        check("and named the sweep event exactly once",
              state.events.count(SWEEP_EVENT) == 1)
        check("the sweep took no socket action (every action is a 4-tuple)",
              all(len(action) == 4 for action in actions))
        check("no socket was constructed while the sweep ran",
              trap.attempts == [], str(trap.attempts))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 3. the dispatcher's bytes ARE the encoder's bytes --")
        check("the dispatcher emitted as many actions as the encoder",
              len(actions) == len(expected))
        check("every dispatched action equals the encoder's, byte for byte",
              actions == expected)
        for index, step in enumerate(STEP_ORDER):
            got, want = actions[index], expected[index]
            check("step %s: the label is identical" % step, got[0] == want[0])
            check("step %s: the PC bytes are identical" % step,
                  got[1] == want[1])
            check("step %s: the framed bytes are identical" % step,
                  got[2] == want[2])
            check("step %s: the delay is identical" % step, got[3] == want[3])
            check("step %s: frame == frame_pc(pc) on the dispatched PC" % step,
                  got[2] == legacy.frame_pc(got[1]))
        check("a sweep composed against a DIFFERENT identity does NOT equal the "
              "dispatched bytes",
              [row[1] for row in other_sweep] != [row[1] for row in actions])

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 4. every dispatched frame, read from byte 0 by an "
                  "independent walker --")
        walked = {}
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = STEP_ORDER[index]
            pin = dh.DAMAGE_HP_LINK_PINS[step]
            scenario_pin = pinned["probe"]["per_step"][step]
            check("frame %s: the transport frame walks back to the exact PC"
                  % step, walk_transport(frame) == pc)
            read = walk_frame(pc)
            walked[step] = read
            check("frame %s is envelope 0x6E9D version 4, error data 0" % step,
                  read["envelope_id"] == RUNTIME_PROTOCOL_RES_ID
                  and read["envelope_version"] == RUNTIME_PROTOCOL_RES_VERSION
                  and read["error_data"] == 0)
            check("frame %s carries BASE change mask 0x02 and DERIVED 0x00"
                  % step,
                  read["base_change_mask"] == BASE_CHANGE_MASK
                  and read["derived_change_mask"] == DERIVED_CHANGE_MASK)
            check("frame %s names the pinned performer identity 0x10010001"
                  % step, read["performer_identity"] == PINNED_IDENTITY_LO)
            row = {
                "index": index,
                "step": step,
                "action_label": label,
                "kind": read["kind"],
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "performer_identity": read["performer_identity"],
            }
            if step in HIT_STEPS:
                check("frame %s is a CHitResult 0x16F7 version 0" % step,
                      read["kind"] == "hit"
                      and read["vital_id"] == CHIT_RESULT_VITAL_ID
                      and read["vital_version"] == CHIT_RESULT_VITAL_VERSION)
                check("frame %s: the four reserved header fields are all zero"
                      % step,
                      read["hf2"] == 0 and read["hf3"] == 0
                      and read["hf4"] == 0 and read["hf5"] == 0)
                check("frame %s: performer == target (the player is both sides)"
                      % step,
                      read["target_identity"] == read["performer_identity"])
                check("frame %s: the damage read SIGNED off tag 0x14 is %d"
                      % (step, EXPECTED_DAMAGE[step]),
                      read["damage_signed"] == EXPECTED_DAMAGE[step],
                      str(read["damage_signed"]))
                check("frame %s: the unsigned reading is the two's complement, "
                      "so SIGNED is a deliberate choice" % step,
                      read["damage_unsigned"]
                      == (EXPECTED_DAMAGE[step] & 0xFFFFFFFF))
                check("frame %s: the flags are 0x%04X"
                      % (step, HIT_STEPS[step]),
                      read["flags"] == HIT_STEPS[step])
                check("frame %s: damage and flags tell the same story" % step,
                      (read["damage_signed"] == 0)
                      == (read["flags"] == FLAGS_MISS))
                check("frame %s: the yaw is the pinned 0.0f" % step,
                      read["yaw"] == YAW_PINNED
                      and struct.pack("<f", read["yaw"]) == b"\x00\x00\x00\x00")
                check("frame %s: every position component is finite" % step,
                      all(math.isfinite(v) for v in read["position"]))
                row["damage_signed"] = read["damage_signed"]
                row["flags"] = read["flags"]
                row["target_identity"] = read["target_identity"]
            else:
                check("frame %s is an UpdateAttrVital 0x309A version 0" % step,
                      read["kind"] == "hp"
                      and read["vital_id"] == UPDATE_ATTR_VITAL_ID
                      and read["vital_version"] == UPDATE_ATTR_VITAL_VERSION)
                fields = read["fields"]
                check("frame %s: the hp_current is the ladder value %d"
                      % (step, EXPECTED_HP[step]),
                      fields.get("hp_current") == EXPECTED_HP[step],
                      str(fields.get("hp_current")))
                check("frame %s: hp_max 100, scene 1/0, cash and name baseline"
                      % step,
                      fields.get("hp_max") == HP_MAX
                      and fields.get("scene_id") == BASELINE_SCENE_ID
                      and fields.get("scene_sequence") == BASELINE_SCENE_SEQUENCE
                      and fields.get("cash") == BASELINE_CASH
                      and fields.get("character_name")
                      == BASELINE_CHARACTER_NAME)
                expected_timer = EXPECTED_TIMER.get(step)
                check("frame %s: the death timer is %r (only on lethal steps)"
                      % (step, expected_timer),
                      fields.get("hp_death_timer") == expected_timer)
                if step in ("HP_ZERO_DYING", "DYING_ELAPSED"):
                    check("frame %s: a lethal step holds the balance at floor 0"
                          % step, fields.get("hp_current") == HP_FLOOR)
                row["hp_current"] = fields.get("hp_current")
                row["hp_death_timer"] = fields.get("hp_death_timer")
            check("frame %s reproduces its MODULE byte pins" % step,
                  len(pc) == pin["pc_size"]
                  and len(frame) == pin["frame_size"]
                  and hashlib.sha256(pc).hexdigest().upper() == pin["pc_sha256"]
                  and hashlib.sha256(frame).hexdigest().upper()
                  == pin["frame_sha256"])
            check("frame %s reproduces its SCENARIO FILE byte pins" % step,
                  scenario_pin["pc_sha256"]
                  == hashlib.sha256(pc).hexdigest().upper()
                  and scenario_pin["frame_sha256"]
                  == hashlib.sha256(frame).hexdigest().upper())
            rows.append(row)

        # The point of the lane, computed from the BYTES the walker read, not
        # from the module: the hp ladder equals the hit arithmetic applied to
        # the baseline.
        baseline_hp = walked["HP_BASELINE"]["fields"]["hp_current"]
        weak = walked["HIT_WEAK"]["damage_signed"]
        miss = walked["MISS"]["damage_signed"]
        strong = walked["HIT_STRONG"]["damage_signed"]
        check("BYTES: hp_after_weak == baseline + weak damage (100 + -63 = 37)",
              walked["HP_AFTER_WEAK"]["fields"]["hp_current"]
              == baseline_hp + weak == 37)
        check("BYTES: hp_after_miss == hp_after_weak + miss (37 + 0 = 37)",
              walked["HP_AFTER_MISS"]["fields"]["hp_current"]
              == walked["HP_AFTER_WEAK"]["fields"]["hp_current"] + miss == 37)
        check("BYTES: hp_zero_dying == max(floor, 37 + strong) (37 + -379 "
              "clamps to 0)",
              walked["HP_ZERO_DYING"]["fields"]["hp_current"]
              == max(HP_FLOOR,
                     walked["HP_AFTER_MISS"]["fields"]["hp_current"] + strong)
              == 0)
        check("BYTES: only the strong hit crosses the floor (weak and miss do "
              "not)", baseline_hp + weak >= HP_FLOOR and 37 + strong < HP_FLOOR)
        check("BYTES: the dying timer is 20.0 and the elapsed timer is 0.0",
              walked["HP_ZERO_DYING"]["fields"]["hp_death_timer"] == 20.0
              and walked["DYING_ELAPSED"]["fields"]["hp_death_timer"] == 0.0)
        check("BYTES: exactly one control MISS frame (damage 0, flags 0)",
              [s for s in HIT_STEPS
               if walked[s]["damage_signed"] == 0
               and walked[s]["flags"] == FLAGS_MISS] == ["MISS"])

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 5. one-shot --")
        seen_pcs = {row[1] for row in actions}
        again = state.dispatch(trigger())
        again2 = state.dispatch(trigger("probe2"))
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [] and again2 == [])
        check("and says so with the named already-sent event, once per try",
              state.events.count(REPEAT_EVENT) == 2)
        check("the repeat put no new byte on the wire",
              not ({row[1] for row in again} | {row[1] for row in again2})
              - seen_pcs)
        check("the sweep counter stayed at one",
              state.damage_hp_link_sweep_count == 1)

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 6. the identity gate: a non-pinned session is refused --")
        alt = boot(ALT_LOGIN_TOKEN)
        alt_selected = alt.foundation.selected
        alt_identity = (int(alt_selected.identity_hi) << 32) | int(
            alt_selected.identity_lo)
        check("the second login lands on a DIFFERENT, non-pinned identity",
              (alt_selected.identity_lo, alt_selected.identity_hi)
              != (PINNED_IDENTITY_LO, PINNED_IDENTITY_HI),
              hex(alt_identity))
        alt_actions = alt.dispatch(trigger())
        check("the dispatcher refuses the non-pinned identity: no bytes",
              alt_actions == [] and alt.damage_hp_link_sweep_count == 0)
        check("and says so with the identity-not-pinned event, exactly",
              alt.events.count(IDENTITY_NOT_PINNED_EVENT) == 1
              and SWEEP_EVENT not in alt.events)

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 7. the refusal ladder --")
        refusals = []
        no_select = boot(PINNED_LOGIN_TOKEN, select=False)
        out = no_select.dispatch(trigger())
        check("no selected character: no bytes",
              out == [] and no_select.damage_hp_link_sweep_count == 0)
        check("no selected character: the named event, exactly",
              no_select.events.count(NO_SELECTED_EVENT) == 1
              and SWEEP_EVENT not in no_select.events)
        refusals.append({"case": "no_selected_character",
                         "event": NO_SELECTED_EVENT, "actions": len(out)})

        not_ready = boot(PINNED_LOGIN_TOKEN, ready=False)
        out = not_ready.dispatch(trigger())
        check("not yet runtime ready: no bytes",
              out == [] and not_ready.damage_hp_link_sweep_count == 0)
        check("not yet runtime ready: the named event, exactly",
              not_ready.events.count(WRONG_SEQUENCE_EVENT) == 1
              and SWEEP_EVENT not in not_ready.events)
        refusals.append({"case": "not_runtime_ready",
                         "event": WRONG_SEQUENCE_EVENT, "actions": len(out)})

        bad_text = bytearray(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        bad_text[-1] ^= 0xFF
        wrong_text = boot(PINNED_LOGIN_TOKEN)
        out = wrong_text.dispatch(legacy.parse_outer(bytes(bad_text)))
        check("a frame that is not ascii12: no bytes",
              out == [] and wrong_text.damage_hp_link_sweep_count == 0)
        check("a frame that is not ascii12: the named event, exactly",
              wrong_text.events.count(WRONG_TEXT_EVENT) == 1
              and SWEEP_EVENT not in wrong_text.events)
        refusals.append({"case": "not_ascii12_text",
                         "event": WRONG_TEXT_EVENT, "actions": len(out)})

        check("no refusal path ever names the sweep event",
              not any(SWEEP_EVENT in candidate.events
                      for candidate in (alt, no_select, not_ready, wrong_text)))

        # ---------------------------------------------------------------
        if not want_json:
            print("-- 8. containment: no db write, no lane when the flag is "
                  "absent --")
        check("no file in the database directory changed across the sweep "
              "(main file AND the WAL/SHM sidecars, by size and sha256)",
              dir_after == dir_before, "%s -> %s" % (dir_before, dir_after))
        check("every user table kept its row count across the sweep",
              counts_after == counts_before)
        check("the copy's bytes are unchanged across the sweep",
              db_after_sha == db_before_sha)
        check("the database this run built lives under the system temp dir",
              Path(tempfile.gettempdir()).resolve()
              in db_path.resolve().parents)
        check("the database this run built is nowhere in the committed state "
              "directory, so the canonical database cannot be the file tested",
              (ROOT / "state").resolve() not in db_path.resolve().parents)

        off = boot("hp_link_flag_off", enabled=False)
        off_actions = off.dispatch(trigger())
        off_labels = [row[0] for row in off_actions]
        check("with the scenario absent no HYP-PF-026 action is composed",
              not any(label.startswith(ACTION_LABEL_PREFIX)
                      for label in off_labels), str(off_labels))
        check("with the scenario absent none of the sweep's bytes appear",
              not ({row[1] for row in off_actions} & seen_pcs))
        check("with the scenario absent no damage-hp-link event is named",
              not any(event.startswith(EVENT_PREFIX) for event in off.events))
        check("with the scenario absent the state carries no sweep count",
              getattr(off, "damage_hp_link_sweep_count", 0) == 0)

        check("the source database file was never modified",
              sha256_file(db_source) == source_sha_before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    verdict = {
        "milestone": "DAMAGE-HP-LINK-001",
        "hypothesis_id": dh.DAMAGE_HP_LINK_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "scenario": SCENARIO.relative_to(ROOT).as_posix(),
        "layer": "wire_only_no_client_no_socket_no_server_process",
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "database": {
            "source": str(db_source),
            "source_opened_by_sqlite": False,
            "ran_against": "a shutil.copyfile copy in tempfile.mkdtemp, "
                           "deleted on exit",
            "source_sha256": source_sha_before,
        },
        "dispatch": {
            "trigger": "one accepted 34-byte ascii12 chat-input frame",
            "trigger_vital_id": CHAT_INPUT_VITAL_ID,
            "frames_per_accepted_request": len(rows),
            "sweep_event": SWEEP_EVENT,
            "one_shot": True,
            "socket_action": "none",
            "socket_constructor_attempts": trap.attempts,
            "database_write": "none",
        },
        "identity": {
            "rule": "the dispatcher refuses unless the selected identity IS the "
                    "canonical smoke identity 0x10010001/0",
            "session_identity": session_identity,
            "coincides_with_the_pinned_probe_identity": (
                session_identity == PINNED_IDENTITY_LO),
        },
        "not_claimed": list(dh.DAMAGE_HP_LINK_NONCLAIMS),
        "frames": rows,
    }
    if evidence_path is not None:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(verdict, indent=2) + "\n", encoding="utf-8")
    if want_json:
        print(json.dumps(verdict, indent=2))
    else:
        print()
        print("guards run: %d" % guards)
        if failures:
            print("RESULT: FAIL - %d guard(s) drifted: %s"
                  % (len(failures), failures))
        else:
            print("RESULT: PASS - the real dispatcher emits the encoder's "
                  "eight-frame hit -> bleed -> die linked sweep byte for byte "
                  "for the pinned identity (client layer = attended, not run, "
                  "and no client has ever been shown one byte of this profile)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
