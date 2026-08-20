#!/usr/bin/env python3
"""NPC-HOSTILE-DISPATCH: headless wire proof for HYP-PF-027.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in
``npc_hostile_hypothesis_faction_pairing`` scenario and a throwaway COPY of a
database, delivers BOTH halves of the SCENE-005 faction pairing:

  (a) THE ENTRY HALF: the StartGame response for the pinned canonical smoke
      identity 0x10010001/0 carries the frozen faction-1 player ActorAttr --
      byte-provable, because the recomposed response must CONTAIN the exact
      ``make_actor_attr_with_basic_faction`` bytes and must NOT contain the
      production ``make_actor_attr_with_name`` bytes, and must be exactly
      five bytes longer than the production response would have been; and
  (b) THE SWEEP HALF: ONE accepted client frame is answered with ONE
      ``GSCN_RunTimeProtocolRes`` (0x6E9D v4, derived mask bit 0x02) actor
      entry -- actor_type 4, NPC 0x2001, alive at 100/100, placed, BasicAttr
      mask EXACTLY 0x070C, faction EXACTLY 6 -- byte-for-byte the frame
      ``build_npc_hostile_sweep`` composes, re-read from byte zero by a tag
      walker written in THIS file that never imports the module's decoder.

And that every refusal is a named event with no bytes: a non-pinned identity
(refused at the entry AND at the dispatch), a missing pairing, no selected
character, a wrong sequence, and a repeat trigger (one-shot).

WHAT IT DOES NOT PROVE
----------------------
That any client renders anything.  **No client has ever been shown one byte
of this profile** -- whether NPC 0x2001 presents as hostile (red outline,
red target panel; there is no name board, this spawn carries no name bit) is
GT-032, attended, not run.  The faction values (player 1, NPC 6) are OUR
composition, the pair SCENE-005 proved hostile on a real screen; the
original server's faction assignment is unknown and unrecoverable.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.
The file named by ``--db`` (default ``state/pirateforce.sqlite3``) is read
once to copy it and once to hash it, and is never opened by SQLite;
everything runs on the temporary copy, which is deleted on exit.  No
repository file is written unless ``--evidence <path>`` is handed in.  Pure
stdlib.

Usage:
    py -3 tools/pf_npc_hostile_headless_replay.py
    py -3 tools/pf_npc_hostile_headless_replay.py --json
    py -3 tools/pf_npc_hostile_headless_replay.py --db state/pirateforce.sqlite3

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the
list.  Exit 2 = the database file named on the command line does not exist.
"""
from __future__ import annotations

import hashlib
import json
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
# The module under test.  This tool calls its loader, its probe resolver, its
# unlock derivation and its encoder (once, to compose the OTHER side of the
# byte-for-byte comparison).  It deliberately NEVER calls
# decode_npc_hostile_actor_entry_frame or validate_npc_hostile_sweep: every
# dispatched byte below is read by this file's own walker.
from pirateforce_foundation import npc_hostile_hypothesis as nhm  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
)
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "npc_hostile_hypothesis_faction_pairing.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"
# The login whose first character IS the pinned smoke identity 0x10010001.
PINNED_LOGIN_TOKEN = "localtest"
ALT_LOGIN_TOKEN = "npc_hostile_alt_identity"

SWEEP_EVENT = "npc_hostile_hypothesis_faction_pairing_sent"
ENTRY_EVENT = "npc_hostile_hypothesis_player_faction1_start_game_sent"
ENTRY_NOT_PINNED_EVENT = (
    "npc_hostile_hypothesis_player_identity_not_pinned_production_start_game"
)
REPEAT_EVENT = "npc_hostile_hypothesis_already_sent_no_reply"
NO_SELECTED_EVENT = "npc_hostile_hypothesis_no_selected_no_reply"
WRONG_SEQUENCE_EVENT = "npc_hostile_hypothesis_wrong_sequence_no_reply"
IDENTITY_NOT_PINNED_EVENT = (
    "npc_hostile_hypothesis_player_identity_not_pinned_no_reply"
)
PAIRING_NOT_APPLIED_EVENT = (
    "npc_hostile_hypothesis_player_faction_not_applied_no_reply"
)

# ---------------------------------------------------------------------------
# This reader's own constants, written as literals so the walk below measures
# the dispatched bytes against THEM, not against the module.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
DERIVED_MASK_ACTOR_ENTRIES = 0x02
NPC_ACTOR_TYPE = 4
NPC_ATTR_ID = 0x0AD5
MOVEMENT_ATTR_ID = 0x2067
HOSTILE_MASK = 0x070C
FACTION_BIT = 0x0400
FACTION_TAG = 0x14
NPC_FACTION_VALUE = 6
PLAYER_PAIR_FACTION = 1
PINNED_IDENTITY_LO = 0x10010001
PINNED_IDENTITY_HI = 0
PROBE_IDENTITY = 0x2001
PROBE_TEMPLATE = 1
PROBE_PRESET = "P_MALE_002_000_SP1"
SCENE_ID = 1
SCENE_SEQUENCE = 0
HP_ALIVE = 100
HP_MAX = 100
ACTION_LABEL = "HYP_PF_027_NPC_HOSTILE_HOSTILE_SPAWN"
EXPECTED_DELAYS = (0.0,)
PIN_PC_SIZE = 178
PIN_PC_SHA = "A85DD9F7C11D5F7B5C7779E0C9B0C5032459458A103B5282D42CDDEB8C7FC21B"
PIN_FRAME_SIZE = 190
PIN_FRAME_SHA = "BB2B59486989C69B083436AC694A4085594ED4A386C4144AB227C7616C6D5983"

# The ONLY BasicAttr fields a 0x070C mask carries, in ascending bit order.
BASIC_FIELD_ORDER = (
    (0x0004, 0x14, 4), (0x0008, 0x14, 4), (0x0100, 0x12, 2),
    (0x0200, 0x32, 8), (0x0400, 0x14, 4),
)
MOVEMENT_FIELD_WIDTH = (
    (0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5), (0x10, 5), (0x20, 5),
    (0x40, 5),
)


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def _u64(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 8], "little")


def walk_npc_hostile_frame(pc: bytes) -> dict:
    """Read the one hostile-spawn PC by hand, byte zero to the end."""
    if type(pc) is not bytes or len(pc) < 17:
        raise WalkError("the frame is shorter than the envelope")
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or _u32(pc, 4) != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != 0x00:
        raise WalkError("the inherited VitalData change mask is not absent")
    if pc[12] != 0x0B or pc[13] != DERIVED_MASK_ACTOR_ENTRIES:
        raise WalkError("the derived change mask is not the actor-entry 0x02")
    if pc[14] != 0x12 or _u16(pc, 15) != 1:
        raise WalkError("expected exactly one actor entry")
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
    npc = None
    movement = None
    for _ in range(attr_count):
        if pc[cursor] != 0x12:
            raise WalkError("attr id tag drift")
        attr_id = _u16(pc, cursor + 1)
        cursor += 3
        attr_order.append(attr_id)
        if attr_id == NPC_ATTR_ID:
            npc, cursor = _walk_npc_attr(pc, cursor)
        elif attr_id == MOVEMENT_ATTR_ID:
            movement, cursor = _walk_movement_attr(pc, cursor)
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
        "npc": npc,
        "movement": movement,
    }


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict, int]:
    if pc[cursor] != 0x0B or pc[cursor + 1] != 0x01:
        raise WalkError("NPCAttr DBAttribute mask is not the identity-only 0x01")
    cursor += 2
    if pc[cursor] != 0x32:
        raise WalkError("NPCAttr identity tag drift")
    identity = _u64(pc, cursor + 1)
    cursor += 9
    if pc[cursor] != 0x12:
        raise WalkError("BasicAttr mask tag drift")
    mask = _u16(pc, cursor + 1)
    cursor += 3
    if mask != HOSTILE_MASK:
        raise WalkError(
            "BasicAttr mask 0x%04X is not the one designed mask 0x070C" % mask
        )
    fields: dict = {}
    for bit, tag, width in BASIC_FIELD_ORDER:
        if pc[cursor] != tag:
            raise WalkError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, pc[cursor])
            )
        fields[bit] = int.from_bytes(pc[cursor + 1:cursor + 1 + width], "little")
        cursor += 1 + width
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
        if pc[cursor] != 0x48:
            raise WalkError("NPCAttr preset tag drift")
        length = _u32(pc, cursor + 1)
        visual_preset = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
        cursor += 5 + length
    return (
        {
            "identity": identity,
            "basic_mask": mask,
            "fields": fields,
            "npc_mask": npc_mask,
            "template_id": template_id,
            "visual_preset": visual_preset,
        },
        cursor,
    )


def _walk_movement_attr(pc: bytes, cursor: int) -> tuple[dict, int]:
    if pc[cursor] != 0x0B or pc[cursor + 1] != 0x01:
        raise WalkError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != 0x32:
        raise WalkError("MovementAttr identity tag drift")
    identity = _u64(pc, cursor + 1)
    cursor += 9
    if pc[cursor] != 0x0B:
        raise WalkError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    out = {"identity": identity, "mask": mask}
    if mask & 0x01:
        values = []
        for _ in range(3):
            if pc[cursor] != 0x2A:
                raise WalkError("MovementAttr position tag drift")
            values.append(struct.unpack("<f", pc[cursor + 1:cursor + 5])[0])
            cursor += 5
        out["position"] = tuple(values)
        rest = MOVEMENT_FIELD_WIDTH[1:]
    else:
        rest = MOVEMENT_FIELD_WIDTH
    for bit, width in rest:
        if bit == 0x01:
            continue
        if mask & bit:
            cursor += width
    return out, cursor


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


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


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
    scenario = nhm.load_npc_hostile_hypothesis_scenario(SCENARIO)
    pinned = json.loads(SCENARIO.read_text(encoding="utf-8"))
    probe = nhm.resolve_probe(legacy)
    wire = nhm.npc_hostile_wire_unlock(scenario)

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("envelope, actor type, attr ids and mask agree with the module",
          RUNTIME_PROTOCOL_RES_ID == nhm.RUNTIME_PROTOCOL_RES_ID
          and NPC_ACTOR_TYPE == nhm.NPC_STYLE_ACTOR_TYPE
          and NPC_ATTR_ID == nhm.NPC_ATTR_ID
          and MOVEMENT_ATTR_ID == nhm.MOVEMENT_ATTR_ID
          and HOSTILE_MASK == nhm.NPC_HOSTILE_BASIC_MASK)
    check("the pairing values agree with the module",
          NPC_FACTION_VALUE == nhm.NPC_HOSTILE_NPC_FACTION_VALUE
          and PLAYER_PAIR_FACTION == nhm.NPC_HOSTILE_PLAYER_PAIR_FACTION
          and PINNED_IDENTITY_LO == nhm.NPC_HOSTILE_PLAYER_IDENTITY_LO
          and PINNED_IDENTITY_HI == nhm.NPC_HOSTILE_PLAYER_IDENTITY_HI)
    check("the probe pins agree with the module",
          PROBE_IDENTITY == nhm.NPC_HOSTILE_PROBE_ACTOR_IDENTITY
          and PROBE_TEMPLATE == nhm.NPC_HOSTILE_PROBE_TEMPLATE_ID
          and PROBE_PRESET == nhm.NPC_HOSTILE_PROBE_VISUAL_PRESET)
    check("the label and pins agree with the module and the scenario file",
          ACTION_LABEL == nhm.NPC_HOSTILE_ACTION_LABELS[0]
          and PIN_PC_SIZE == nhm.NPC_HOSTILE_PINS["HOSTILE_SPAWN"]["pc_size"]
          and PIN_PC_SHA == nhm.NPC_HOSTILE_PINS["HOSTILE_SPAWN"]["pc_sha256"]
          and PIN_FRAME_SIZE
          == nhm.NPC_HOSTILE_PINS["HOSTILE_SPAWN"]["frame_size"]
          and PIN_FRAME_SHA
          == nhm.NPC_HOSTILE_PINS["HOSTILE_SPAWN"]["frame_sha256"]
          and pinned["probe"]["per_step"]["HOSTILE_SPAWN"]
          == nhm.NPC_HOSTILE_PINS["HOSTILE_SPAWN"])
    check("production is not allowed anywhere",
          nhm.production_allowed is False
          and pinned["production_allowed"] is False)

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_npc_hostile001_")
    rows: list[dict] = []
    try:
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real "
                  "session on it --")
        db_path = Path(tmp) / "npc_hostile001.sqlite3"
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

        def boot(token, *, enabled=True, select=True, ready=True):
            """Login, a V25 create ONLY when the login account has no
            character yet, start game on the last character, then the
            sequence flags.  The pinned login lands on the smoke identity
            0x10010001; any other login lands on a fresh account and
            therefore a different identity."""
            state_type = make_state_class(
                legacy, lifecycle, projector,
                npc_hostile_hypothesis_scenario=(
                    scenario if enabled else None),
            )
            state = state_type(token)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc(token)))
            start_actions = None
            if select:
                characters = store.list_characters(state.foundation.account_id)
                if not characters:
                    created = state.dispatch(
                        legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
                    assert created and created[0][0] == (
                        "FOUNDATION_CREATE_COMMITTED")
                    characters = store.list_characters(
                        state.foundation.account_id)
                start_actions = state.dispatch(legacy.parse_outer(
                    legacy._synthetic_start_game_pc(characters[-1].selector)))
                assert start_actions and start_actions[0][0] in (
                    "FOUNDATION_SELECTED_START_GAME",
                    "SCENE2_LOAD_ONLY_SELECTED_START_GAME",
                )
            state.runtime_ack_sent = ready
            return state, start_actions

        def trigger(probe_name="probe1"):
            return legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS[probe_name])

        state, start_actions = boot(PINNED_LOGIN_TOKEN)
        selected = state.foundation.selected
        check("a character is selected on the copy", selected is not None)
        check("the selected identity is the pinned smoke identity "
              "0x10010001/0",
              (selected.identity_lo, selected.identity_hi)
              == (PINNED_IDENTITY_LO, PINNED_IDENTITY_HI),
              hex(selected.identity_lo))
        check("the sequence flags the dispatcher gates on are set",
              state.teleport_sent is True and state.runtime_ack_sent is True)

        if not want_json:
            print("-- 2. THE ENTRY HALF: the StartGame response carries the "
                  "frozen faction-1 player ActorAttr --")
        check("the entry event was named exactly once",
              state.events.count(ENTRY_EVENT) == 1)
        check("and the pairing flag the dispatch gates on is set",
              state.npc_hostile_player_faction_start_sent is True)
        p = selected.position
        plain_attr = bytes(make_actor_attr_with_name(
            legacy, selected.identity_lo, selected.identity_hi,
            p.scene_id, p.scene_seq, selected.name,
        ))
        paired_attr = bytes(make_actor_attr_with_basic_faction(
            legacy, selected.identity_lo, selected.identity_hi,
            p.scene_id, p.scene_seq, selected.name, PLAYER_PAIR_FACTION,
        ))
        sg_pc = bytes(start_actions[0][1])
        sg_frame = bytes(start_actions[0][2])
        check("the StartGame PC CONTAINS the faction-1 ActorAttr bytes",
              paired_attr in sg_pc)
        check("and does NOT contain the production ActorAttr bytes",
              plain_attr not in sg_pc)
        check("the faction-1 attr is the production attr plus exactly 5 bytes",
              len(paired_attr) == len(plain_attr)
              + nhm.NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA)
        check("the StartGame frame still frames its PC",
              sg_frame == legacy.frame_pc(sg_pc))
        entry_info = {
            "start_game_pc_size": len(sg_pc),
            "start_game_pc_sha256":
                hashlib.sha256(sg_pc).hexdigest().upper(),
            "note": "informational: the StartGame bytes depend on the "
                    "character row; the PIN is the containment of the "
                    "frozen faction-1 ActorAttr",
        }

        # The encoder's own composition, built OUTSIDE the dispatcher.
        expected = nhm.build_npc_hostile_sweep(legacy, probe, wire, scenario)

        db_before_sha = sha256_file(db_path)
        counts_before = table_row_counts(db_path)

        if not want_json:
            print("-- 3. one accepted client frame in, ONE frame out --")
        actions = state.dispatch(trigger())
        check("the dispatcher answered with exactly one action",
              len(actions) == 1, str(len(actions)))
        check("with the pinned label and delay",
              actions and actions[0][0] == ACTION_LABEL
              and actions[0][3] == EXPECTED_DELAYS[0])
        check("and named the sweep event exactly once",
              state.events.count(SWEEP_EVENT) == 1)
        check("the sweep took no socket action",
              all(len(action) == 4 for action in actions))
        check("the dispatched action equals the encoder's, byte for byte",
              actions == expected)
        label, pc, frame, delay = actions[0]
        check("frame == frame_pc(pc) on the dispatched PC",
              frame == legacy.frame_pc(pc))
        check("the dispatched PC parses with the frozen v141 outer parser",
              legacy.parse_outer(pc) is not None)

        if not want_json:
            print("-- 4. the dispatched frame, read by an independent "
                  "walker from byte zero --")
        read = None
        error = ""
        try:
            read = walk_npc_hostile_frame(pc)
        except WalkError as exc:
            error = str(exc)
        check("the frame walks end to end with this file's own reader",
              read is not None, ascii(error))
        if read is not None:
            npc = read["npc"]
            movement = read["movement"]
            check("actor_type 4 (CNetNPC), identity 0x2001",
                  read["actor_type"] == NPC_ACTOR_TYPE
                  and read["identity"] == PROBE_IDENTITY)
            check("EXACTLY the planned attrs, in order: NPCAttr, MovementAttr",
                  read["attr_order"] == (NPC_ATTR_ID, MOVEMENT_ATTR_ID))
            check("the NPCAttr identity == the entry identity",
                  npc is not None and npc["identity"] == read["identity"])
            check("the BasicAttr mask is EXACTLY 0x070C (walker refuses any "
                  "other)", npc is not None
                  and npc["basic_mask"] == HOSTILE_MASK)
            check("alive at the pinned 100/100, scene 1 sequence 0",
                  npc is not None
                  and npc["fields"][0x0004] == HP_ALIVE
                  and npc["fields"][0x0008] == HP_MAX
                  and npc["fields"][0x0100] == SCENE_ID
                  and npc["fields"][0x0200] == SCENE_SEQUENCE)
            check("THE FACTION FIELD IS ON THE WIRE: bit 0x0400 == 6",
                  npc is not None
                  and npc["fields"][FACTION_BIT] == NPC_FACTION_VALUE)
            check("template 1 and the pinned visual preset",
                  npc is not None
                  and npc["template_id"] == PROBE_TEMPLATE
                  and npc["visual_preset"] == PROBE_PRESET)
            check("the MovementAttr places the probe at its frozen placement",
                  movement is not None
                  and movement["identity"] == PROBE_IDENTITY
                  and movement["mask"] == 0xFF
                  and movement.get("position")
                  == (_f32(probe.x), _f32(probe.y), _f32(probe.z)))
            rows.append({
                "index": 0,
                "step": "HOSTILE_SPAWN",
                "action_label": label,
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "actor_type": read["actor_type"],
                "identity": read["identity"],
                "basic_mask": npc["basic_mask"] if npc else None,
                "faction_value":
                    npc["fields"].get(FACTION_BIT) if npc else None,
                "hp_current": npc["fields"].get(0x0004) if npc else None,
                "movement_mask": movement["mask"] if movement else None,
            })

        if not want_json:
            print("-- 5. the pins, recomputed by this file --")
        pc_sha = hashlib.sha256(pc).hexdigest().upper()
        frame_sha = hashlib.sha256(frame).hexdigest().upper()
        check("recomputed PC size and sha equal this file's pins",
              len(pc) == PIN_PC_SIZE and pc_sha == PIN_PC_SHA,
              "%d %s" % (len(pc), pc_sha))
        check("recomputed frame size and sha equal this file's pins",
              len(frame) == PIN_FRAME_SIZE and frame_sha == PIN_FRAME_SHA,
              "%d %s" % (len(frame), frame_sha))

        if not want_json:
            print("-- 6. one-shot, write-free, fail-closed --")
        again = state.dispatch(trigger())
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [])
        check("and says so with the named already-sent event, exactly once",
              state.events.count(REPEAT_EVENT) == 1)
        check("without re-announcing the sweep event",
              state.events.count(SWEEP_EVENT) == 1)
        check("the sweep wrote nothing: every user table keeps its row count",
              table_row_counts(db_path) == counts_before)
        check("the sweep wrote nothing: the copy's bytes are unchanged",
              sha256_file(db_path) == db_before_sha)

        off, off_start = boot(PINNED_LOGIN_TOKEN + "_off", enabled=False)
        off_actions = off.dispatch(trigger())
        off_labels = [row[0] for row in off_actions]
        check("with the scenario absent no hostile frame is composed",
              not any(lbl.startswith("HYP_PF_027") for lbl in off_labels),
              str(off_labels))
        check("with the scenario absent the StartGame is production "
              "(no faction attr bytes)",
              paired_attr not in bytes(off_start[0][1])
              if off_start else False)
        check("and names no lane event at all",
              not any("npc_hostile" in event for event in off.events))

        if not want_json:
            print("-- 7. the identity gate and the refusal ladder --")
        alt, alt_start = boot(ALT_LOGIN_TOKEN)
        alt_selected = alt.foundation.selected
        check("the second login lands on a DIFFERENT, non-pinned identity",
              (alt_selected.identity_lo, alt_selected.identity_hi)
              != (PINNED_IDENTITY_LO, PINNED_IDENTITY_HI),
              hex(alt_selected.identity_lo))
        check("the entry hook fell back to production bytes, by name",
              alt.events.count(ENTRY_NOT_PINNED_EVENT) == 1
              and alt.npc_hostile_player_faction_start_sent is False)
        check("and the non-pinned StartGame carries NO faction-1 attr for "
              "its own identity",
              bytes(make_actor_attr_with_basic_faction(
                  legacy, alt_selected.identity_lo, alt_selected.identity_hi,
                  alt_selected.position.scene_id,
                  alt_selected.position.scene_seq,
                  alt_selected.name, PLAYER_PAIR_FACTION,
              )) not in bytes(alt_start[0][1]))
        alt_actions = alt.dispatch(trigger())
        check("the dispatcher refuses the non-pinned identity: no bytes",
              alt_actions == [] and alt.npc_hostile_sweep_count == 0)
        check("and says so with the identity-not-pinned event, exactly once",
              alt.events.count(IDENTITY_NOT_PINNED_EVENT) == 1
              and SWEEP_EVENT not in alt.events)

        no_select, _ = boot(PINNED_LOGIN_TOKEN, select=False)
        out = no_select.dispatch(trigger())
        check("no selected character: no bytes, the named event",
              out == [] and no_select.events.count(NO_SELECTED_EVENT) == 1)
        not_ready, _ = boot(PINNED_LOGIN_TOKEN, ready=False)
        out = not_ready.dispatch(trigger())
        check("wrong sequence: no bytes, the named event",
              out == [] and not_ready.events.count(WRONG_SEQUENCE_EVENT) == 1)
        # The pairing gate, held wrong ON PURPOSE: a session whose entry half
        # never applied the player faction must refuse even with the pinned
        # identity.  The flag is forced back to its constructor value to
        # simulate an entry fallback.
        unpaired, _ = boot(PINNED_LOGIN_TOKEN)
        unpaired.npc_hostile_player_faction_start_sent = False
        out = unpaired.dispatch(trigger())
        check("an unapplied pairing: no bytes, the named event",
              out == []
              and unpaired.events.count(PAIRING_NOT_APPLIED_EVENT) == 1
              and unpaired.npc_hostile_sweep_count == 0)

        check("the source database file was never modified",
              sha256_file(db_source) == source_sha_before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    verdict = {
        "milestone": "NPC-HOSTILE-DISPATCH",
        "hypothesis_id": nhm.NPC_HOSTILE_HYPOTHESIS_ID,
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
        "entry_half": entry_info if not failures else None,
        "dispatch": {
            "trigger": "one accepted 34-byte ascii12 chat-input frame",
            "frames_per_accepted_request": len(rows),
            "sweep_event": SWEEP_EVENT,
            "one_shot": True,
            "socket_action": "none",
            "database_write": "none",
        },
        "not_claimed": list(nhm.NPC_HOSTILE_NONCLAIMS),
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
            print("RESULT: PASS - the real dispatcher delivers both halves "
                  "of the faction pairing byte for byte: the frozen "
                  "faction-1 StartGame for the pinned identity, and one "
                  "hostile spawn whose faction 6 an independent walker read "
                  "back from the wire (client layer = GT-032, attended, not "
                  "run, and no client has ever been shown one byte of this "
                  "profile)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
