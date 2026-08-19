#!/usr/bin/env python3
"""REMOTE-PLAYER-DISPATCH-001: headless wire proof for HYP-PF-025.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in
``remote_player_hypothesis_visibility_probe`` scenario and a throwaway COPY
of a database, answers ONE accepted client frame with the exact five-frame
``GSCN_RunTimeProtocolRes`` (0x6E9D v4, derived mask bit 0x02) remote-player
visibility sweep HYP-PF-025 declares, and that those frames are

  (a) **byte-for-byte** the frames ``build_remote_player_sweep`` composes --
      same labels, same PCs, same framed bytes, same delays, compared with
      ``==`` on the bytes objects, not by hash summary alone; and
  (b) independently readable, by a tag walker written in THIS file that does
      not import the encoder's decoder or validator, as the sweep the
      round-96 design says it is: actor_type 2 (``CNetActor``, the
      remote-player branch of the client factory 0x446990) on every frame,
      the three probe identities A/B/C, the pinned names, HP 100/100,
      movement masks FF/FF/01/03/FF at the pinned placement-0 offsets, the
      opaque AvatarAttr tail last on SPAWN_AVATAR, EXACTLY one MovementAttr
      on the two move frames, the wrong-class NPCAttr on the negative
      control, and the death lane's BasicAttr bit 0x0080 NOWHERE.

The five steps and their spacing (0.0 then 15.0 s each):

    frame 1  SPAWN_BARE        identity A  ActorAttr + MovementAttr 0xFF
    frame 2  SPAWN_AVATAR      identity B  the same + opaque AvatarAttr tail
    frame 3  MOVE_A_1          identity A  ONE MovementAttr, mask 0x01, X+300
    frame 4  MOVE_A_2          identity A  ONE MovementAttr, mask 0x03, pi/2
    frame 5  NEGATIVE_CONTROL  identity C  wrong-class NPCAttr + Movement

THE DATABASE IS A COPY, ALWAYS
------------------------------
The SPAWN_AVATAR frame replays the selected character's ``avatar_wire``
(per-character database content), so unlike the HYP-PF-023 replay this tool
needs a database with a real character in it.  It NEVER opens the file it is
pointed at: ``--db <path>`` (default ``state/pirateforce.sqlite3``) is copied
with ``shutil.copyfile`` into a fresh ``tempfile.mkdtemp`` directory, every
connection is made against that copy, the copy is deleted on exit, and the
source file's SHA-256 is asserted unchanged at the end of the run.  If the
copy has no character on the synthetic account, the same real lifecycle the
HYP-PF-023 replay drives (login -> V25 create -> start game) establishes
one -- on the copy.  Because the avatar tail is database content, the
SPAWN_AVATAR pin is the module's SKELETON pin (everything the encoder
composes, up to and including the AvatarAttr id tag); this tool reports the
tail's size and hash from this database as information, not as a pin.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of actor_type 2** -- whether a CNetActor renders at all,
whether the name board fills, whether the move frames move it, and whether
the negative control stays nameless are ALL the attended test's questions,
and this file is not that run.  The design is OURS: the original server is
closed, unpublished, and left no server->client capture of a remote human
player, so there is nothing to recover.  It claims nothing about interest
management, cadence, broadcast, despawn (no despawn path exists on this
lane), ground Z at the offset positions, or production (``production_
allowed`` is False everywhere it appears).

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.
The file named by ``--db`` is read once to copy it and once to hash it, and
is never opened by SQLite; everything runs on the temporary copy, which is
deleted on exit.  No repository file is written unless ``--evidence <path>``
is handed in.  Pure stdlib.

Usage:
    py -3 tools/pf_remote_player_headless_replay.py
    py -3 tools/pf_remote_player_headless_replay.py --json
    py -3 tools/pf_remote_player_headless_replay.py --db state/pirateforce.sqlite3
    py -3 tools/pf_remote_player_headless_replay.py \
        --evidence reports/remote_player001_headless.json

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the
list.  Exit 2 = the database file named on the command line does not exist.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import struct
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.chat_input_hypothesis import (  # noqa: E402
    CHAT_INPUT_PROBE_REQUEST_PCS,
)
from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
# The module under test.  This tool calls its loader, its probe resolver,
# its unlock derivation, its encoder (once, to compose the OTHER side of the
# byte-for-byte comparison, and once more to prove it refuses a missing
# unlock) and reads its pins.  It deliberately NEVER calls
# decode_remote_player_actor_entry_frame or validate_remote_player_sweep:
# every dispatched byte below is read by this file's own walker, so a
# symmetrical bug in the encoder's reader cannot hide.
from pirateforce_foundation import remote_player_hypothesis as rph  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "remote_player_hypothesis_visibility_probe.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"
SWEEP_EVENT = "remote_player_hypothesis_visibility_probe_sent"
REPEAT_EVENT = "remote_player_hypothesis_already_sent_no_reply"

# ---------------------------------------------------------------------------
# This reader's own constants.  Written out as literals rather than read off
# the module, so section 0 can measure the module against THEM: a guard that
# asks the encoder what to expect and then checks the encoder against its own
# answer is a restatement, not a check.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
INHERITED_MASK_ABSENT = 0x00
DERIVED_MASK_ACTOR_ENTRIES = 0x02
REMOTE_PLAYER_ACTOR_TYPE = 2       # CNetActor, jump-table case at 0x446B2C

ACTOR_ATTR_ID = 0x12AD
AVATAR_ATTR_ID = 0x16A0
MOVEMENT_ATTR_ID = 0x2067
NPC_ATTR_ID = 0x0AD5

BASIC_MASK_PROBE = 0x030D          # name + HP pair + scene pair
BIT_NAME = 0x0001                  # wstring tag 0x48
BIT_CURRENT_HP = 0x0004            # u32 tag 0x14
BIT_MAX_HP = 0x0008                # u32 tag 0x14
BIT_DEATH_TIMER = 0x0080           # the death lane's field; must appear NOWHERE
BIT_SCENE_ID = 0x0100              # u16 tag 0x12
BIT_SCENE_SEQ = 0x0200             # qword tag 0x32
SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x26: 4,
                0x2A: 4, 0x32: 8}
BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)
MOVEMENT_FIELDS = (
    (0x01, "position"), (0x02, "heading"), (0x04, "mode"), (0x08, "flags"),
    (0x10, "p40"), (0x20, "p44"), (0x40, "p48"),
)

IDENTITY_A = 0x00A00001
IDENTITY_B = 0x00A00002
IDENTITY_C = 0x00A00003
NAME_A = "ProbePlayer01"
NAME_B = "ProbePlayer02"
NAME_C = "ProbeControl03"
SCENE_ID = 1
SCENE_SEQUENCE = 0
HP_ALIVE = 100
HP_MAX = 100
PROBE_B_X_OFFSET = 150.0
PROBE_C_X_OFFSET = -150.0
MOVE_X_OFFSET = 300.0
MOVE_HEADING = math.pi / 2.0
CONTROL_TEMPLATE_ID = 1
CONTROL_VISUAL_PRESET = "P_MALE_002_000_SP1"

STEP_ORDER = (
    "SPAWN_BARE", "SPAWN_AVATAR", "MOVE_A_1", "MOVE_A_2", "NEGATIVE_CONTROL",
)
ACTION_LABEL_PREFIX = "HYP_PF_025_REMOTE_PLAYER_"
ACTION_LABELS = tuple(ACTION_LABEL_PREFIX + step for step in STEP_ORDER)
EXPECTED_DELAYS = (0.0, 15.0, 15.0, 15.0, 15.0)
FULLY_PINNED_STEPS = ("SPAWN_BARE", "MOVE_A_1", "MOVE_A_2", "NEGATIVE_CONTROL")

EXPECTED_IDENTITY = {
    "SPAWN_BARE": IDENTITY_A,
    "SPAWN_AVATAR": IDENTITY_B,
    "MOVE_A_1": IDENTITY_A,
    "MOVE_A_2": IDENTITY_A,
    "NEGATIVE_CONTROL": IDENTITY_C,
}
EXPECTED_ATTR_ORDER = {
    "SPAWN_BARE": (ACTOR_ATTR_ID, MOVEMENT_ATTR_ID),
    "SPAWN_AVATAR": (ACTOR_ATTR_ID, MOVEMENT_ATTR_ID, AVATAR_ATTR_ID),
    "MOVE_A_1": (MOVEMENT_ATTR_ID,),
    "MOVE_A_2": (MOVEMENT_ATTR_ID,),
    "NEGATIVE_CONTROL": (NPC_ATTR_ID, MOVEMENT_ATTR_ID),
}
EXPECTED_MOVEMENT_MASK = {
    "SPAWN_BARE": 0xFF,
    "SPAWN_AVATAR": 0xFF,
    "MOVE_A_1": 0x01,
    "MOVE_A_2": 0x03,
    "NEGATIVE_CONTROL": 0xFF,
}
EXPECTED_NAME = {
    "SPAWN_BARE": NAME_A,
    "SPAWN_AVATAR": NAME_B,
    "NEGATIVE_CONTROL": NAME_C,
}


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def _u64(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 8], "little")


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def _wstr(pc: bytes, cursor: int) -> tuple[str, int]:
    if pc[cursor] != 0x48:
        raise WalkError("expected a wstring tag 0x48 at %d" % cursor)
    length = _u32(pc, cursor + 1)
    if length % 2 or cursor + 5 + length > len(pc):
        raise WalkError("wstring length %d does not fit the frame" % length)
    text = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
    return text, cursor + 5 + length


def _walk_common_prefix(pc: bytes, cursor: int, what: str) -> tuple[int, int]:
    """The proven common-Attr prefix: 0B 01, 32 qword identity."""
    if pc[cursor] != 0x0B or pc[cursor + 1] != 0x01:
        raise WalkError("%s DBAttribute mask is not the identity-only 0x01"
                        % what)
    cursor += 2
    if pc[cursor] != 0x32:
        raise WalkError("%s identity tag drift" % what)
    identity = _u64(pc, cursor + 1)
    return identity, cursor + 9


def _walk_basic_block(pc: bytes, cursor: int) -> tuple[int, dict, int]:
    """BasicAttr: 12 u16 mask, then fields in ascending mask-bit order."""
    if pc[cursor] != 0x12:
        raise WalkError("BasicAttr mask tag drift")
    mask = _u16(pc, cursor + 1)
    cursor += 3
    if mask & ~0x07FF:
        raise WalkError(
            "BasicAttr mask 0x%04X carries a bit this reader cannot read"
            % mask
        )
    fields: dict = {}
    for bit, tag in BASIC_FIELD_ORDER:
        if not mask & bit:
            continue
        if pc[cursor] != tag:
            raise WalkError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, pc[cursor])
            )
        if tag == 0x48:
            fields[bit], cursor = _wstr(pc, cursor)
            continue
        width = SCALAR_WIDTH[tag]
        raw = pc[cursor + 1:cursor + 1 + width]
        fields[bit] = (
            struct.unpack("<f", raw)[0] if tag == 0x2A
            else int.from_bytes(raw, "little")
        )
        cursor += 1 + width
    return mask, fields, cursor


def _walk_actor_attr(pc: bytes, cursor: int) -> tuple[dict, int]:
    identity, cursor = _walk_common_prefix(pc, cursor, "ActorAttr")
    basic_mask, fields, cursor = _walk_basic_block(pc, cursor)
    if pc[cursor] != 0x32:
        raise WalkError("ActorAttr 64-bit mask tag drift")
    actor_mask = _u64(pc, cursor + 1)
    cursor += 9
    if pc[cursor] != 0x05:
        raise WalkError("ActorAttr extra-group tag drift")
    extra_group = pc[cursor + 1]
    cursor += 2
    return (
        {
            "identity": identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "actor_mask": actor_mask,
            "extra_group": extra_group,
        },
        cursor,
    )


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict, int]:
    identity, cursor = _walk_common_prefix(pc, cursor, "NPCAttr")
    basic_mask, fields, cursor = _walk_basic_block(pc, cursor)
    if pc[cursor] != 0x0B:
        raise WalkError("NPCAttr own-mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & 0x01:
        if pc[cursor] != 0x12:
            raise WalkError("NPCAttr template tag drift")
        template_id = _u16(pc, cursor + 1)
        cursor += 3
    if npc_mask & 0x04:
        visual_preset, cursor = _wstr(pc, cursor)
    return (
        {
            "identity": identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "npc_mask": npc_mask,
            "template_id": template_id,
            "visual_preset": visual_preset,
        },
        cursor,
    )


def _walk_movement_attr(pc: bytes, cursor: int) -> tuple[dict, int]:
    identity, cursor = _walk_common_prefix(pc, cursor, "MovementAttr")
    if pc[cursor] != 0x0B:
        raise WalkError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    out: dict = {"identity": identity, "mask": mask}
    for bit, name in MOVEMENT_FIELDS:
        if not mask & bit:
            continue
        if bit == 0x01:
            values = []
            for _ in range(3):
                if pc[cursor] != 0x2A:
                    raise WalkError("MovementAttr position tag drift")
                values.append(
                    struct.unpack("<f", pc[cursor + 1:cursor + 5])[0]
                )
                cursor += 5
            out["position"] = tuple(values)
        elif bit == 0x04:
            if pc[cursor] != 0x0B:
                raise WalkError("MovementAttr mode tag drift")
            out[name] = pc[cursor + 1]
            cursor += 2
        elif bit == 0x08:
            if pc[cursor] != 0x26:
                raise WalkError("MovementAttr flags tag drift")
            out[name] = _u32(pc, cursor + 1)
            cursor += 5
        else:
            if pc[cursor] != 0x2A:
                raise WalkError("MovementAttr f32 tag drift")
            out[name] = struct.unpack("<f", pc[cursor + 1:cursor + 5])[0]
            cursor += 5
    return out, cursor


def walk_remote_player_frame(pc: bytes) -> dict:
    """Read one GSCN_RunTimeProtocolRes actor-entry PC by hand, byte zero to
    the end.  The AvatarAttr body is opaque replay, so the walker requires it
    to be the LAST attr, takes everything to the end of the frame as its
    tail, and checks the two things about it that are not opaque: the proven
    common-Attr prefix and the rebound identity."""
    if type(pc) is not bytes or len(pc) < 17:
        raise WalkError("the frame is shorter than the envelope")
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or _u32(pc, 4) != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != INHERITED_MASK_ABSENT:
        raise WalkError("the inherited VitalData change mask is not absent")
    if pc[12] != 0x0B or pc[13] != DERIVED_MASK_ACTOR_ENTRIES:
        raise WalkError(
            "the derived change mask is not the actor-entry bit 0x02, so the "
            "client would never read the +0x1C collection"
        )
    if pc[14] != 0x12:
        raise WalkError("actor-entry count tag drift")
    count = _u16(pc, 15)
    if count != 1:
        raise WalkError("expected exactly one actor entry, found %d" % count)
    cursor = 17
    if pc[cursor] != 0x0B:
        raise WalkError("actor type tag drift")
    actor_type = pc[cursor + 1]
    cursor += 2
    if pc[cursor] != 0x32:
        raise WalkError("actor identity tag drift")
    identity = _u64(pc, cursor + 1)
    cursor += 9
    if pc[cursor] != 0x0B:
        raise WalkError("attr count tag drift")
    attr_count = pc[cursor + 1]
    cursor += 2

    attr_order: list[int] = []
    actor_attr = None
    npc_attr = None
    movement = None
    avatar = None
    for attr_index in range(attr_count):
        if pc[cursor] != 0x12:
            raise WalkError("attr id tag drift")
        attr_id = _u16(pc, cursor + 1)
        cursor += 3
        attr_order.append(attr_id)
        if attr_id == ACTOR_ATTR_ID:
            actor_attr, cursor = _walk_actor_attr(pc, cursor)
        elif attr_id == NPC_ATTR_ID:
            npc_attr, cursor = _walk_npc_attr(pc, cursor)
        elif attr_id == MOVEMENT_ATTR_ID:
            movement, cursor = _walk_movement_attr(pc, cursor)
        elif attr_id == AVATAR_ATTR_ID:
            if attr_index != attr_count - 1:
                raise WalkError(
                    "the opaque AvatarAttr must be the LAST attr of the "
                    "entry, or no independent walker can find its boundary"
                )
            tail = pc[cursor:]
            if len(tail) < 11 or tail[0] != 0x0B or not tail[1] & 0x01 or (
                tail[2] != 0x32
            ):
                raise WalkError(
                    "the avatar tail is not a common-Attr body"
                )
            avatar = {"identity": _u64(tail, 3), "tail": tail}
            cursor = len(pc)
        else:
            raise WalkError("unexpected attr id 0x%04X" % attr_id)
    if cursor != len(pc):
        raise WalkError(
            "the reader accounted for %d of %d bytes" % (cursor, len(pc))
        )
    return {
        "actor_type": actor_type,
        "identity": identity,
        "attr_order": tuple(attr_order),
        "actor_attr": actor_attr,
        "npc_attr": npc_attr,
        "movement": movement,
        "avatar": avatar,
    }


def table_row_counts(db_path: Path) -> dict:
    """Row count of every user table.  Opens the COPY, never the source."""
    db = sqlite3.connect(str(db_path))
    try:
        names = [
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            name: db.execute('SELECT COUNT(*) FROM "%s"' % name).fetchone()[0]
            for name in names
        }
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
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

    failures: list[str] = []
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

    legacy = load_legacy(LEGACY_PATH)
    scenario = rph.load_remote_player_hypothesis_scenario(SCENARIO)
    pinned = json.loads(SCENARIO.read_text(encoding="utf-8"))
    probes = rph.resolve_probes(legacy)
    by_role = {probe.role: probe for probe in probes}
    probe_a, probe_b, probe_c = by_role["A"], by_role["B"], by_role["C"]

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("id 0x6E9D and envelope version 4 agree with the module",
          RUNTIME_PROTOCOL_RES_ID == rph.RUNTIME_PROTOCOL_RES_ID
          and RUNTIME_PROTOCOL_RES_VERSION == rph.RUNTIME_PROTOCOL_RES_VERSION)
    check("derived change mask bit 0x02 agrees with the module",
          DERIVED_MASK_ACTOR_ENTRIES
          == rph.DERIVED_CHANGE_MASK_ACTOR_ENTRIES)
    check("actor_type 2 (CNetActor) agrees with the module",
          REMOTE_PLAYER_ACTOR_TYPE == rph.REMOTE_PLAYER_ACTOR_TYPE)
    check("attr ids 0x12AD/0x16A0/0x2067/0x0AD5 agree with the module",
          ACTOR_ATTR_ID == rph.ACTOR_ATTR_ID
          and AVATAR_ATTR_ID == rph.AVATAR_ATTR_ID
          and MOVEMENT_ATTR_ID == rph.MOVEMENT_ATTR_ID
          and NPC_ATTR_ID == rph.NPC_ATTR_ID)
    check("BasicAttr probe mask 0x030D agrees with the module",
          BASIC_MASK_PROBE == rph.BASIC_MASK_PROBE)
    check("the forbidden death-timer bit 0x0080 agrees with the module",
          BIT_DEATH_TIMER == rph.BASIC_BIT_DEATH_TIMER_FORBIDDEN)
    check("probe identities A/B/C agree with the module",
          IDENTITY_A == rph.PROBE_IDENTITY_A
          and IDENTITY_B == rph.PROBE_IDENTITY_B
          and IDENTITY_C == rph.PROBE_IDENTITY_C)
    check("probe names agree with the module",
          NAME_A == rph.PROBE_NAME_A and NAME_B == rph.PROBE_NAME_B
          and NAME_C == rph.PROBE_NAME_C)
    check("the X offsets +150/-150/+300 and heading pi/2 agree with the module",
          PROBE_B_X_OFFSET == rph.PROBE_B_X_OFFSET
          and PROBE_C_X_OFFSET == rph.PROBE_C_X_OFFSET
          and MOVE_X_OFFSET == rph.MOVE_X_OFFSET
          and MOVE_HEADING == rph.MOVE_HEADING)
    check("the step order and action labels agree with the module",
          STEP_ORDER == rph.REMOTE_PLAYER_STEP_ORDER
          and ACTION_LABELS == rph.REMOTE_PLAYER_ACTION_LABELS
          and ACTION_LABEL_PREFIX == rph.REMOTE_PLAYER_ACTION_LABEL_PREFIX)
    check("the delays 0.0 then 15.0 agree with the loaded scenario",
          EXPECTED_DELAYS[0] == scenario.first_delay_seconds
          and all(d == scenario.spacing_seconds for d in EXPECTED_DELAYS[1:])
          and scenario.step_order == STEP_ORDER)
    check("the lane is not production-allowed, and the file says so too",
          rph.production_allowed is False
          and pinned["production_allowed"] is False
          and pinned["test_only"] is True)
    check("the lane is HYP-PF-025 behind kwarg remote_player_hypothesis_scenario",
          rph.REMOTE_PLAYER_HYPOTHESIS_ID == "HYP-PF-025"
          and rph.REMOTE_PLAYER_DISPATCH_KWARG
          == "remote_player_hypothesis_scenario")
    check("resolve_probes derives B and C from A by the pinned X offsets",
          probe_b.x == probe_a.x + PROBE_B_X_OFFSET
          and probe_c.x == probe_a.x + PROBE_C_X_OFFSET
          and probe_b.y == probe_a.y == probe_c.y
          and probe_b.z == probe_a.z == probe_c.z)
    check("every probe sits in scene 1 sequence 0",
          all(p.scene_id == SCENE_ID and p.scene_sequence == SCENE_SEQUENCE
              for p in probes))
    check("the scenario file's per_step pins ARE the module's pins",
          all(pinned["probe"]["per_step"][step] == rph.REMOTE_PLAYER_PINS[step]
              for step in STEP_ORDER))

    # Expected geometry, f32-rounded the way the wire stores it.
    def xyz(probe):
        return (_f32(probe.x), _f32(probe.y), _f32(probe.z))

    moved = (_f32(probe_a.x + MOVE_X_OFFSET), _f32(probe_a.y), _f32(probe_a.z))
    expected_position = {
        "SPAWN_BARE": xyz(probe_a),
        "SPAWN_AVATAR": xyz(probe_b),
        "MOVE_A_1": moved,
        "MOVE_A_2": moved,
        "NEGATIVE_CONTROL": xyz(probe_c),
    }
    expected_heading = {
        "SPAWN_BARE": 0.0,
        "SPAWN_AVATAR": 0.0,
        "MOVE_A_1": None,               # mask 0x01 carries no heading at all
        "MOVE_A_2": _f32(MOVE_HEADING),
        "NEGATIVE_CONTROL": 0.0,
    }

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_remote_player001_")
    rows: list[dict] = []
    avatar_tail_info = None
    try:
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real "
                  "session on it --")
        db_path = Path(tmp) / "remote_player001.sqlite3"
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
            Position(
                1, 0, legacy.V135_PLAYER_X, legacy.V135_PLAYER_Y,
                legacy.V135_PLAYER_Z,
            ),
            legacy.extract_avatar_attr_wire_from_actor,
        )

        def boot(token, *, enabled=True):
            """The same session establishment the HYP-PF-023 replay drives:
            login, a V25 create ONLY when the copy has no character yet,
            start game on the last character, then the sequence flags."""
            state_type = make_state_class(
                legacy, lifecycle, projector,
                remote_player_hypothesis_scenario=(
                    scenario if enabled else None
                ),
            )
            state = state_type(token)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc()
            ))
            characters = store.list_characters(state.foundation.account_id)
            if not characters:
                created = state.dispatch(
                    legacy.parse_outer(legacy._V25_REAL_CREATE_PC)
                )
                assert created and created[0][0] == (
                    "FOUNDATION_CREATE_COMMITTED"
                )
                characters = store.list_characters(state.foundation.account_id)
            selected = state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            assert selected and selected[0][0] == (
                "FOUNDATION_SELECTED_START_GAME"
            )
            state.runtime_ack_sent = True
            return state

        state = boot("remote_player001")
        selected = state.foundation.selected
        check("a character is selected on the copy", selected is not None)
        check("the selected character carries a non-empty avatar_wire",
              type(selected.avatar_wire) is bytes
              and len(selected.avatar_wire) > 0)
        selected_identity = (
            (int(selected.identity_hi) << 32) | int(selected.identity_lo)
        )
        check("the selected identity is a qword in the character space",
              0 <= selected_identity <= 0xFFFFFFFFFFFFFFFF
              and selected_identity >= 0x10000000)
        check("the sequence flags the dispatcher gates on are set",
              state.teleport_sent is True and state.runtime_ack_sent is True)
        check("no probe identity collides with the selected character",
              all(p.identity != selected_identity for p in probes))

        # The encoder's own composition, built OUTSIDE the dispatcher, with
        # the SAME avatar wire and selected identity.  This is the
        # expectation every dispatched byte is measured against.
        expected = rph.build_remote_player_sweep(
            legacy, probes, rph.remote_player_wire_unlock(scenario), scenario,
            avatar_wire=selected.avatar_wire,
            selected_identity=selected_identity,
        )

        db_before_sha = sha256_file(db_path)
        counts_before = table_row_counts(db_path)

        if not want_json:
            print("-- 2. one accepted client frame in, five frames out --")
        actions = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("the dispatcher answered with exactly five actions",
              len(actions) == 5, str(len(actions)))
        check("in the pinned order, with the pinned labels",
              tuple(row[0] for row in actions) == ACTION_LABELS,
              str([row[0] for row in actions]))
        check("with the pinned delays 0.0/15.0/15.0/15.0/15.0",
              tuple(row[3] for row in actions) == EXPECTED_DELAYS,
              str([row[3] for row in actions]))
        check("and named the sweep event exactly once",
              state.events.count(SWEEP_EVENT) == 1)
        check("the sweep took no socket action",
              all(len(action) == 4 for action in actions))

        if not want_json:
            print("-- 3. the dispatcher's bytes ARE the encoder's bytes --")
        check("the dispatcher emitted exactly as many actions as the encoder",
              len(actions) == len(expected))
        mismatched = [
            expected[i][0] if i < len(expected) else "<extra frame %d>" % i
            for i in range(max(len(actions), len(expected)))
            if i >= len(actions) or i >= len(expected)
            or actions[i] != expected[i]
        ]
        check("every dispatched action equals the encoder's, byte for byte",
              not mismatched, str(mismatched))
        for index, step in enumerate(STEP_ORDER):
            if index >= len(actions) or index >= len(expected):
                continue
            got, want = actions[index], expected[index]
            check("step %s: the labels are identical" % step,
                  got[0] == want[0])
            check("step %s: the PC bytes are identical" % step,
                  got[1] == want[1])
            check("step %s: the framed bytes are identical" % step,
                  got[2] == want[2])
            check("step %s: the delay is identical" % step,
                  got[3] == want[3])
            check("step %s: frame == frame_pc(pc) on the dispatched PC" % step,
                  got[2] == legacy.frame_pc(got[1]))

        if not want_json:
            print("-- 4. every dispatched frame, read by an independent "
                  "walker from byte zero --")
        walked: list[dict | None] = []
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = STEP_ORDER[index]
            check("frame %s parses with the frozen v141 outer parser" % step,
                  legacy.parse_outer(pc) is not None)
            read = None
            error = ""
            try:
                read = walk_remote_player_frame(pc)
            except WalkError as exc:
                error = str(exc)
            walked.append(read)
            check("frame %s walks end to end with this file's own reader"
                  % step, read is not None, ascii(error))
            if read is None:
                continue
            check("frame %s carries actor_type 2 (CNetActor) and nothing else"
                  % step, read["actor_type"] == REMOTE_PLAYER_ACTOR_TYPE,
                  str(read["actor_type"]))
            check("frame %s names the pinned entry identity 0x%08X"
                  % (step, EXPECTED_IDENTITY[step]),
                  read["identity"] == EXPECTED_IDENTITY[step],
                  hex(read["identity"]))
            check("frame %s carries EXACTLY the planned attrs, in order" % step,
                  read["attr_order"] == EXPECTED_ATTR_ORDER[step],
                  str([hex(a) for a in read["attr_order"]]))
            movement = read["movement"]
            check("frame %s: the MovementAttr identity == the entry identity"
                  % step,
                  movement is not None
                  and movement["identity"] == read["identity"])
            check("frame %s: movement mask is the pinned 0x%02X"
                  % (step, EXPECTED_MOVEMENT_MASK[step]),
                  movement is not None
                  and movement["mask"] == EXPECTED_MOVEMENT_MASK[step],
                  hex(movement["mask"]) if movement else "absent")
            check("frame %s: the position is the pinned placement-derived XYZ"
                  % step,
                  movement is not None
                  and movement.get("position") == expected_position[step],
                  str(movement.get("position")) if movement else "absent")
            want_heading = expected_heading[step]
            if want_heading is None:
                check("frame %s: mask 0x01 carries NO heading field" % step,
                      movement is not None and "heading" not in movement)
            else:
                check("frame %s: the heading is the pinned %r"
                      % (step, want_heading),
                      movement is not None
                      and movement.get("heading") == want_heading,
                      str(movement.get("heading")) if movement else "absent")
            masks_seen = [
                attr["basic_mask"]
                for attr in (read["actor_attr"], read["npc_attr"])
                if attr is not None
            ]
            check("frame %s: BasicAttr bit 0x0080 appears NOWHERE" % step,
                  all(not mask & BIT_DEATH_TIMER for mask in masks_seen),
                  str([hex(m) for m in masks_seen]))
            row = {
                "index": index,
                "step": step,
                "action_label": label,
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "actor_type": read["actor_type"],
                "identity": read["identity"],
                "attr_order": [a for a in read["attr_order"]],
                "movement_mask": movement["mask"] if movement else None,
                "position": list(movement.get("position", ()))
                if movement else None,
                "heading": movement.get("heading") if movement else None,
            }
            if step in ("SPAWN_BARE", "SPAWN_AVATAR"):
                actor = read["actor_attr"]
                check("frame %s: ActorAttr identity == the entry identity"
                      % step,
                      actor is not None
                      and actor["identity"] == read["identity"])
                check("frame %s: ActorAttr BasicAttr mask is the probe 0x030D"
                      % step,
                      actor is not None
                      and actor["basic_mask"] == BASIC_MASK_PROBE,
                      hex(actor["basic_mask"]) if actor else "absent")
                check("frame %s: the name is the pinned %s"
                      % (step, EXPECTED_NAME[step]),
                      actor is not None
                      and actor["fields"].get(BIT_NAME) == EXPECTED_NAME[step],
                      ascii(actor["fields"].get(BIT_NAME)) if actor else "")
                check("frame %s: HP is alive at the pinned 100/100" % step,
                      actor is not None
                      and actor["fields"].get(BIT_CURRENT_HP) == HP_ALIVE
                      and actor["fields"].get(BIT_MAX_HP) == HP_MAX)
                check("frame %s: scene 1 sequence 0" % step,
                      actor is not None
                      and actor["fields"].get(BIT_SCENE_ID) == SCENE_ID
                      and actor["fields"].get(BIT_SCENE_SEQ) == SCENE_SEQUENCE)
                check("frame %s: ActorAttr 64-bit mask 0 and gate byte 1"
                      % step,
                      actor is not None and actor["actor_mask"] == 0
                      and actor["extra_group"] == 1)
                if actor is not None:
                    row["name"] = actor["fields"].get(BIT_NAME)
                    row["basic_mask"] = actor["basic_mask"]
                    row["hp_current"] = actor["fields"].get(BIT_CURRENT_HP)
                    row["hp_max"] = actor["fields"].get(BIT_MAX_HP)
            if step == "SPAWN_AVATAR":
                avatar = read["avatar"]
                check("frame %s: the opaque AvatarAttr tail is the LAST attr"
                      % step,
                      avatar is not None
                      and read["attr_order"][-1] == AVATAR_ATTR_ID)
                check("frame %s: the avatar tail is rebound to identity B "
                      "0x00A00002" % step,
                      avatar is not None
                      and avatar["identity"] == IDENTITY_B
                      and avatar["identity"] == read["identity"],
                      hex(avatar["identity"]) if avatar else "absent")
            if step in ("MOVE_A_1", "MOVE_A_2"):
                check("frame %s: EXACTLY one attr rides the update path"
                      % step, len(read["attr_order"]) == 1,
                      str(len(read["attr_order"])))
            if step == "NEGATIVE_CONTROL":
                npc = read["npc_attr"]
                check("frame %s: the wrong-class NPCAttr identity == the "
                      "entry identity" % step,
                      npc is not None
                      and npc["identity"] == read["identity"])
                check("frame %s: NPCAttr BasicAttr mask is the probe 0x030D"
                      % step,
                      npc is not None
                      and npc["basic_mask"] == BASIC_MASK_PROBE,
                      hex(npc["basic_mask"]) if npc else "absent")
                check("frame %s: the control's name is the pinned %s"
                      % (step, NAME_C),
                      npc is not None
                      and npc["fields"].get(BIT_NAME) == NAME_C,
                      ascii(npc["fields"].get(BIT_NAME)) if npc else "")
                check("frame %s: the control's HP is 100/100" % step,
                      npc is not None
                      and npc["fields"].get(BIT_CURRENT_HP) == HP_ALIVE
                      and npc["fields"].get(BIT_MAX_HP) == HP_MAX)
                check("frame %s: the control sits in scene 1 sequence 0"
                      % step,
                      npc is not None
                      and npc["fields"].get(BIT_SCENE_ID) == SCENE_ID
                      and npc["fields"].get(BIT_SCENE_SEQ) == SCENE_SEQUENCE)
                check("frame %s: NPCAttr template id is the anchor's 1" % step,
                      npc is not None
                      and npc["template_id"] == CONTROL_TEMPLATE_ID,
                      str(npc["template_id"]) if npc else "absent")
                check("frame %s: NPCAttr visual preset is %s"
                      % (step, CONTROL_VISUAL_PRESET),
                      npc is not None
                      and npc["visual_preset"] == CONTROL_VISUAL_PRESET,
                      ascii(npc["visual_preset"]) if npc else "")
                check("frame %s: the NPCAttr own mask names template and "
                      "preset" % step,
                      npc is not None
                      and npc["npc_mask"] & 0x01 and npc["npc_mask"] & 0x04)
                if npc is not None:
                    row["name"] = npc["fields"].get(BIT_NAME)
                    row["basic_mask"] = npc["basic_mask"]
                    row["npc_template_id"] = npc["template_id"]
                    row["npc_visual_preset"] = npc["visual_preset"]
            rows.append(row)

        if not want_json:
            print("-- 5. the pins, recomputed by this file --")
        for step in FULLY_PINNED_STEPS:
            index = STEP_ORDER.index(step)
            _label, pc, frame, _delay = actions[index]
            pin = rph.REMOTE_PLAYER_PINS[step]
            scen = pinned["probe"]["per_step"][step]
            pc_sha = hashlib.sha256(pc).hexdigest().upper()
            frame_sha = hashlib.sha256(frame).hexdigest().upper()
            check("step %s: recomputed PC size and sha equal the module pin"
                  % step,
                  len(pc) == pin["pc_size"] and pc_sha == pin["pc_sha256"],
                  "%d %s" % (len(pc), pc_sha))
            check("step %s: recomputed frame size and sha equal the module pin"
                  % step,
                  len(frame) == pin["frame_size"]
                  and frame_sha == pin["frame_sha256"],
                  "%d %s" % (len(frame), frame_sha))
            check("step %s: the scenario FILE pins the same numbers" % step,
                  scen["pc_size"] == len(pc) and scen["pc_sha256"] == pc_sha
                  and scen["frame_size"] == len(frame)
                  and scen["frame_sha256"] == frame_sha)
            read = walked[index]
            check("step %s: the walker's masks equal the pinned masks" % step,
                  read is not None
                  and read["movement"]["mask"] == pin["movement_mask"]
                  and ("basic_mask" not in pin or (
                      (read["actor_attr"] or read["npc_attr"])["basic_mask"]
                      == pin["basic_mask"])))

        # SPAWN_AVATAR: the skeleton pin.  The avatar tail is per-character
        # database content, so its size and hash are REPORTED, not pinned.
        index = STEP_ORDER.index("SPAWN_AVATAR")
        _label, pc, frame, _delay = actions[index]
        pin = rph.REMOTE_PLAYER_PINS["SPAWN_AVATAR"]
        scen = pinned["probe"]["per_step"]["SPAWN_AVATAR"]
        read = walked[index]
        tail = read["avatar"]["tail"] if read and read["avatar"] else b""
        skeleton = pc[:len(pc) - len(tail)]
        skeleton_sha = hashlib.sha256(skeleton).hexdigest().upper()
        tail_sha = hashlib.sha256(tail).hexdigest().upper()
        check("SPAWN_AVATAR: skeleton + tail reassemble the whole PC",
              len(tail) > 0 and skeleton + tail == pc)
        check("SPAWN_AVATAR: both pins declare the tail excluded",
              pin.get("avatar_tail_excluded_from_pin") is True
              and scen.get("avatar_tail_excluded_from_pin") is True)
        check("SPAWN_AVATAR: the skeleton this walker cut matches the module "
              "pin",
              len(skeleton) == pin["pc_skeleton_size"]
              and skeleton_sha == pin["pc_skeleton_sha256"],
              "%d %s" % (len(skeleton), skeleton_sha))
        check("SPAWN_AVATAR: the scenario FILE pins the same skeleton",
              scen["pc_skeleton_size"] == len(skeleton)
              and scen["pc_skeleton_sha256"] == skeleton_sha)
        avatar_tail_info = {
            "size": len(tail),
            "sha256": tail_sha,
            "note": "informational only: per-character database content, "
                    "not a pin",
        }
        for row in rows:
            if row["step"] == "SPAWN_AVATAR":
                row["avatar_tail_size"] = len(tail)
                row["avatar_tail_sha256"] = tail_sha
                row["pc_skeleton_size"] = len(skeleton)
                row["pc_skeleton_sha256"] = skeleton_sha
        if not want_json:
            print("  INFO  avatar tail from this database: size=%d sha256=%s "
                  "(information, not a pin)" % (len(tail), tail_sha))

        if not want_json:
            print("-- 6. one-shot, fail-closed, containment --")
        again = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [])
        check("and says so with the named already-sent event, exactly once",
              state.events.count(REPEAT_EVENT) == 1)
        check("without re-announcing the sweep event",
              state.events.count(SWEEP_EVENT) == 1,
              str(state.events.count(SWEEP_EVENT)))
        check("the sweep wrote nothing: every user table keeps its row count",
              table_row_counts(db_path) == counts_before)
        check("the sweep wrote nothing: the copy's bytes are unchanged",
              sha256_file(db_path) == db_before_sha)
        off = boot("remote_player001_off", enabled=False)
        off_actions = off.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        off_labels = [row[0] for row in off_actions]
        check("with the scenario absent no remote-player frame is composed",
              not any(label.startswith(ACTION_LABEL_PREFIX)
                      for label in off_labels), str(off_labels))
        check("with the scenario absent none of the sweep's bytes appear",
              not ({row[1] for row in off_actions}
                   & {row[1] for row in expected}))
        check("and names no sweep event", SWEEP_EVENT not in off.events)

        def encoder_refusal(unlock):
            try:
                rph.encode_remote_player_actor_attr(legacy, probe_a, unlock)
            except ValueError as exc:
                return str(exc)
            return ""

        check("the encoder called directly with NO unlock refuses by name",
              "missing_or_forged_wire_unlock" in encoder_refusal(None))
        forged = rph.RemotePlayerWireUnlock(
            rph.REMOTE_PLAYER_SCENARIO_ID, rph.REMOTE_PLAYER_HYPOTHESIS_ID,
        )
        check("a value-equal FORGED unlock is refused too (identity, not ==)",
              "missing_or_forged_wire_unlock" in encoder_refusal(forged))
        sweep_refusal = ""
        try:
            rph.build_remote_player_sweep(
                legacy, probes, forged, scenario,
                avatar_wire=selected.avatar_wire,
                selected_identity=selected_identity,
            )
        except ValueError as exc:
            sweep_refusal = str(exc)
        check("build_remote_player_sweep refuses the forged unlock by name",
              "missing_or_forged_wire_unlock" in sweep_refusal,
              ascii(sweep_refusal))
        check("the source database file was never modified",
              sha256_file(db_source) == source_sha_before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    verdict = {
        "milestone": "REMOTE-PLAYER-DISPATCH-001",
        "hypothesis_id": rph.REMOTE_PLAYER_HYPOTHESIS_ID,
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
            "frames_per_accepted_request": len(rows),
            "sweep_event": SWEEP_EVENT,
            "one_shot": True,
            "socket_action": "none",
            "database_write": "none",
        },
        "avatar_tail": avatar_tail_info,
        "not_claimed": list(rph.REMOTE_PLAYER_NONCLAIMS),
        "frames": rows,
    }
    if evidence_path is not None:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(
            json.dumps(verdict, indent=2) + "\n", encoding="utf-8",
        )
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
                  "five-frame remote-player visibility sweep byte for byte "
                  "(client layer = attended, not run, and no client has "
                  "ever been shown one byte of actor_type 2)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
