#!/usr/bin/env python3
"""GROUND-LOOT-NAMEPROP-001: headless replay for HYP-PF-039 (GT-069).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the name-property lane, driven through the REAL make_state_class
dispatcher on a throwaway COPY of the database, APPENDS exactly TWO extra
actions -- a CONTROL frame (element dirty mask 0x12, no selector fields, the
shape HYP-PF-032 already ships) at scheduler delay 0.0, and a TREATMENT
frame (element dirty mask 0x3A, carrying the name-property GATE at +0x1B and
the INDEX 6 at +0x1A) at scheduler delay 1.50 -- AFTER the inherited actions
of the first exact TargetPos following the runtime ack, exactly once (a
second TargetPos adds neither frame), commits NOTHING (no table changes row
count, no socket action rides any action), and leaves the frozen population
and the position checkpoint of the triggering frame untouched.

The guards that matter for the attended round, and that no static reading
could give it:

  * an independent hand-walker reads the GATE byte and the INDEX byte back
    out of the dispatched treatment frame, from byte zero, without asking the
    module to decode anything.  That is the only proof in this repository
    that those two fields are on the wire at all.
  * the control and the treatment carry a BYTE-IDENTICAL payload dword and
    BYTE-IDENTICAL coordinates, and differ only in the element key, the mask
    byte and the two selector fields.  The experiment is single-variable or
    it is nothing.
  * the HYP-PF-032 lane never fires: its latch never moves and its event is
    never named.

ONE element per frame, count=1, is the V43 lesson: a real client raised
ErrorData=28317 on a combined multi-record derived-mask RuntimeRes
collection, and the shipped fix is one record per frame
(make_port_royal_npc_single_packets).

WHAT IS NOT MEASURED HERE, and must not be claimed anywhere else:

  * THE REALIZED WIRE GAP.  The 1.50 is a scheduler DEADLINE OFFSET.  The
    frozen sender accumulates an absolute deadline and a zero-delay action
    does not advance it, so realized_gap is roughly 1.50 minus however late
    the control frame was actually sent -- about 1.41-1.44 s at the ~85 ms
    lateness the project's own 2026-08-25 capture measured.  Nothing in this
    tree measures it; only the attended capture can.
  * ANYTHING ABOUT A CLIENT.  No client has ever been shown element mask
    0x3A.  Whether it is accepted, whether the selector reaches the label,
    and what UI text property 0x34 or 0x5D..0x62 MEAN are all open, and the
    last of those is not even a colour question until something says so.

DISCIPLINE
----------
No server process, no socket, no network, no client, no game window.  The
file named by ``--db`` (default ``state/pirateforce.sqlite3``) is read once
to copy it and once to hash it, and is never opened by SQLite for the
session; everything runs on the temporary copy, which is deleted on exit.

Usage:
    py -3 tools/pf_ground_loot_nameprop_headless_replay.py
    py -3 tools/pf_ground_loot_nameprop_headless_replay.py --json
    py -3 tools/pf_ground_loot_nameprop_headless_replay.py --db state/pirateforce.sqlite3

Exit 0 = every wire guard held.  Exit 1 = at least one drifted.  Exit 2 = the
database file named on the command line does not exist.
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

from pirateforce_foundation.legacy_bridge import (  # noqa: E402
    LegacyProjector, load_legacy,
)
from pirateforce_foundation.lifecycle import CharacterLifecycle  # noqa: E402
# The module under test.  This tool calls its loader and its composer ONCE
# (to build the OTHER side of the byte comparison); it NEVER asks the module
# to decode the dispatched bytes -- the walker below reads them by hand.
from pirateforce_foundation import (  # noqa: E402
    ground_loot_nameprop_hypothesis as G,
)
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "ground_loot_nameprop_probe.json"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"

RUNTIME_PROTOCOL_RES_ID = 0x6E9D
DERIVED_BIT = 0x08
CONTROL_MASK = 0x12   # dword | position -- the already-proven shape
TREATMENT_MASK = 0x3A  # the same, plus gate (+0x1B) and index (+0x1A)

# Per element, because the masks differ and so do the lengths and the spans.
# Restated locally on purpose: this reader shares no constant with the module
# it is checking.
CONTROL_PC_SIZE = 44
CONTROL_FRAME_SIZE = 54
CONTROL_COORD_SPANS = ((30, 34), (35, 39), (40, 44))
CONTROL_PC_TEMPLATE_SHA = (
    "8657614E33073F5C1969AA6CB1FEAA441E0A1ED011F38AD13B22270183B8E26D"
)
CONTROL_FRAME_TEMPLATE_SHA = (
    "FB419334817234FFEA7A2A8A498E2C24DF7D223915783D5CBFBB87B2866BAD9D"
)
TREATMENT_PC_SIZE = 48
TREATMENT_FRAME_SIZE = 58
TREATMENT_COORD_SPANS = ((32, 36), (37, 41), (42, 46))
TREATMENT_PC_TEMPLATE_SHA = (
    "34E4D5B285258FD8BE929704195F2C704B6B25A03ECDDC9F41C2D8E42C115FF2"
)
TREATMENT_FRAME_TEMPLATE_SHA = (
    "A91392DDC1F092DDFE7F5897E2A38CAB9C7C93646BB06BA5248F5161578E1D07"
)
FRAME_COORD_SHIFT = 10

CONTROL_LABEL = "GROUND_LOOT_NAMEPROP_CONTROL_ONCE"
TREATMENT_LABEL = "GROUND_LOOT_NAMEPROP_IDX6_ONCE"
LANE_LABELS = (CONTROL_LABEL, TREATMENT_LABEL)
PAIR_EVENT = "hyp_pf_039_ground_loot_nameprop_pair_committed"
SIBLING_EVENT = "hyp_pf_032_ground_loot_bit08_pair_committed"

# key, dword, mask, gate (None on the control), index (None), x_offset, delay
EXPECTED_ELEMENTS = (
    (3, 2200423, CONTROL_MASK, None, None, 30.0, 0.0),
    (4, 2200423, TREATMENT_MASK, 1, 6, 30.0, 1.50),
)
EXPECTED_GEOMETRY = (
    (CONTROL_PC_SIZE, CONTROL_FRAME_SIZE, CONTROL_COORD_SPANS,
     CONTROL_PC_TEMPLATE_SHA, CONTROL_FRAME_TEMPLATE_SHA),
    (TREATMENT_PC_SIZE, TREATMENT_FRAME_SIZE, TREATMENT_COORD_SPANS,
     TREATMENT_PC_TEMPLATE_SHA, TREATMENT_FRAME_TEMPLATE_SHA),
)


def masked_pc_sha(pc: bytes, spans) -> str:
    masked = bytearray(pc)
    for start, end in spans:
        masked[start:end] = b"\x00" * (end - start)
    return hashlib.sha256(bytes(masked)).hexdigest().upper()


def masked_frame_sha(frame: bytes, spans) -> str:
    masked = bytearray(frame)
    for start, end in spans:
        masked[start + FRAME_COORD_SHIFT:end + FRAME_COORD_SHIFT] = (
            b"\x00" * (end - start)
        )
    return hashlib.sha256(bytes(masked)).hexdigest().upper()


def f32_exact(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def _f32(buf: bytes, at: int) -> float:
    return struct.unpack_from("<f", buf, at)[0]


def walk_nameprop_frame(pc: bytes) -> dict:
    """Read one single-element bit-0x08 PC by hand, byte zero to the end.

    Handles BOTH masks this lane emits.  Tag layouts re-stated locally from
    the legacy helpers: u16tag = tag byte then <H; u32tag = tag byte then
    <I; u8tag = tag byte then one value byte; f32tag = tag byte 0x2A then
    <f.  The FIELD ORDER is the codec's, ascending by mask bit -- dword,
    gate, position, index -- which is what the client walks.
    """
    if type(pc) is not bytes or len(pc) < 17:
        raise WalkError("the frame is shorter than the envelope")
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or _u32(pc, 4) != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != 4:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != 0x00:
        raise WalkError("the inherited VitalData mask is not 0")
    if pc[12] != 0x0B or pc[13] != DERIVED_BIT:
        raise WalkError("the derived change mask is not 0x08")
    if pc[14] != 0x12:
        raise WalkError("the element count tag is not 0x12")
    count = _u16(pc, 15)
    if count != 1:
        raise WalkError(
            "count is %d, not the V43-safe single record" % count)
    cur = 17
    if pc[cur] != 0x14:
        raise WalkError("the element key tag is not 0x14")
    key = _u32(pc, cur + 1)
    cur += 5
    if pc[cur] != 0x0B:
        raise WalkError("the element mask tag is not 0x0B")
    mask = pc[cur + 1]
    cur += 2
    if mask not in (CONTROL_MASK, TREATMENT_MASK):
        raise WalkError("the element dirty mask is neither 0x12 nor 0x3A")
    if not mask & 0x02:
        raise WalkError("this reader only walks elements carrying the dword")
    if pc[cur] != 0x14:
        raise WalkError("the element dword tag is not 0x14")
    dword = _u32(pc, cur + 1)
    cur += 5
    gate = None
    if mask & 0x08:
        if pc[cur] != 0x05:
            raise WalkError("the name-property gate tag is not 0x05")
        gate = pc[cur + 1]
        cur += 2
    position = []
    for axis in ("x", "y", "z"):
        if pc[cur] != 0x2A:
            raise WalkError("the element %s tag is not 0x2A" % axis)
        position.append(_f32(pc, cur + 1))
        cur += 5
    index = None
    if mask & 0x20:
        if pc[cur] != 0x08:
            raise WalkError("the name-property index tag is not 0x08")
        index = pc[cur + 1]
        cur += 2
    if cur != len(pc):
        raise WalkError("the reader accounted for %d of %d bytes"
                        % (cur, len(pc)))
    return {"count": count, "key": key, "mask": mask, "dword": dword,
            "gate": gate, "index": index, "position": tuple(position)}


def table_row_counts(db_path: Path) -> dict:
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


def target_pos_pc(legacy, x, y, z, heading=0.0, moving=1):
    """The exact singleton TargetPos shape the frozen parser accepts."""
    return (
        legacy.u16tag(0x12, legacy.GSCN_RUNTIME_PROTOCOL_REQ)
        + legacy.u32tag(0x14, 0)
        + legacy.u8tag(0x08, 0)
        + legacy.u8tag(0x0B, 2)
        + legacy.u16tag(0x12, 1)
        + legacy.u16tag(0x12, legacy.TARGET_POS_VITAL)
        + legacy.u8tag(0x0B, 0)
        + legacy.f32tag(x) + legacy.f32tag(y)
        + legacy.f32tag(z) + legacy.f32tag(heading)
        + legacy.u8tag(0x0B, moving)
        + legacy.u8tag(0x0B, 0)
    )


def main() -> int:
    want_json = "--json" in sys.argv
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
    scenario = G.load_ground_loot_nameprop_scenario(SCENARIO)

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("the msg id, bit and labels agree with the module",
          RUNTIME_PROTOCOL_RES_ID == legacy.GSCN_RUNTIME_PROTOCOL_RES
          and DERIVED_BIT == G.GROUND_LOOT_NAMEPROP_DERIVED_BIT
          and CONTROL_MASK == G.GROUND_LOOT_NAMEPROP_CONTROL_MASK
          and TREATMENT_MASK == G.GROUND_LOOT_NAMEPROP_TREATMENT_MASK
          and FRAME_COORD_SHIFT == G.GROUND_LOOT_NAMEPROP_FRAME_COORD_SHIFT
          and LANE_LABELS == G.GROUND_LOOT_NAMEPROP_LABELS)
    check("the per-element geometry pins agree with the module",
          tuple(
              (g.pc_size, g.frame_size, g.coord_spans,
               g.pc_template_sha256, g.frame_template_sha256)
              for g in G.GROUND_LOOT_NAMEPROP_GEOMETRY
          ) == EXPECTED_GEOMETRY)
    check("the control mask names no selector field and the treatment "
          "mask names both",
          CONTROL_MASK == (0x02 | 0x10)
          and TREATMENT_MASK == (0x02 | 0x08 | 0x10 | 0x20)
          and not CONTROL_MASK & 0x08 and not CONTROL_MASK & 0x20
          and not TREATMENT_MASK & 0x04)
    check("the scenario is the allowlisted HYP-PF-039 profile",
          scenario.hypothesis_id == "HYP-PF-039"
          and scenario.scenario_id == "ground_loot_nameprop_probe"
          and len(scenario.elements) == 2)
    check("this reader's frozen elements agree with the profile's",
          tuple(
              (e.element_key, e.payload_dword, e.element_mask,
               e.property_gate, e.property_index, e.x_offset, e.delay)
              for e in scenario.elements
          ) == EXPECTED_ELEMENTS)
    check("the two elements hold the payload dword and the offset EQUAL, "
          "so the selector fields are the only variable",
          len({e.payload_dword for e in scenario.elements}) == 1
          and len({e.x_offset for e in scenario.elements}) == 1)
    check("the treatment opens the gate and stays inside the client's "
          "1..6 index window, and is not the ctor default 1",
          scenario.elements[1].property_gate not in (0, None)
          and G.GROUND_LOOT_NAMEPROP_INDEX_MIN
          <= scenario.elements[1].property_index
          <= G.GROUND_LOOT_NAMEPROP_INDEX_MAX
          and scenario.elements[1].property_index != 1)

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_ground_loot_nameprop_")
    results: list[dict] = []
    try:
        db_path = Path(tmp) / "nameprop.sqlite3"
        shutil.copyfile(db_source, db_path)
        if not want_json:
            print("-- 1. a throwaway COPY of the database, and a real session "
                  "on it --")
        check("the copy lives in the temp directory, not at the source",
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

        state_type = make_state_class(
            legacy, lifecycle, projector,
            ground_loot_nameprop_scenario=scenario,
        )
        state = state_type("nameprop")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("nameprop")))
        characters = store.list_characters(state.foundation.account_id)
        if not characters:
            created = state.dispatch(
                legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            assert created and created[0][0] == "FOUNDATION_CREATE_COMMITTED"
            characters = store.list_characters(state.foundation.account_id)
        start = state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(characters[-1].selector)))
        assert start and start[0][0] in (
            "FOUNDATION_SELECTED_START_GAME",
            "SCENE2_LOAD_ONLY_SELECTED_START_GAME",
        )
        state.runtime_ack_sent = True

        check("a character is selected on the copy",
              state.foundation.selected is not None)
        check("the runtime-ready sequence flags are set",
              state.teleport_sent is True and state.runtime_ack_sent is True)
        check("the one-shot latch starts False",
              state.ground_loot_nameprop_sent is False)
        check("the HYP-PF-032 latch is present and starts False",
              state.ground_loot_pair_sent is False)

        if not want_json:
            print("-- 2. the first exact TargetPos, the control and the "
                  "treatment appended --")
        before = table_row_counts(db_path)
        position = state.foundation.selected.position
        trigger_xyz = (
            f32_exact(position.x), f32_exact(position.y),
            f32_exact(position.z),
        )
        expected_frames = G.make_ground_loot_nameprop_frames(
            legacy, scenario, trigger_xyz)
        trigger = legacy.parse_outer(target_pos_pc(
            legacy, trigger_xyz[0], trigger_xyz[1], trigger_xyz[2]))
        actions = state.dispatch(trigger)
        lane = [a for a in actions if a[0] in LANE_LABELS]

        check("exactly two lane actions leave the dispatcher",
              len(lane) == 2, str([a[0] for a in actions]))
        check("the two actions are APPENDED LAST, control then treatment, "
              "after the inherited actions",
              len(actions) >= 2
              and [a[0] for a in actions[-2:]]
              == [CONTROL_LABEL, TREATMENT_LABEL]
              and all(a[0] not in LANE_LABELS for a in actions[:-2]),
              str([a[0] for a in actions]))
        check("inherited actions still ride the same trigger frame",
              len(actions) > 2, str([a[0] for a in actions]))
        check("the emitted bytes equal the composer's, frame for frame",
              len(lane) == 2 and all(
                  bytes(action[1]) == expected[0]
                  and bytes(action[2]) == expected[1]
                  for action, expected in zip(lane, expected_frames)
              ))
        check("the scheduler delays are 0.0 then 1.50",
              len(lane) == 2
              and tuple(action[3] for action in lane) == (0.0, 1.50),
              str([a[3] for a in lane]))
        check("no socket action rides any action",
              all(len(a) == 4 for a in actions))
        check("each emitted pc and frame matches ITS OWN size and "
              "masked-template pin (the two differ)",
              len(lane) == 2 and all(
                  len(bytes(action[1])) == pc_size
                  and masked_pc_sha(bytes(action[1]), spans) == pc_sha
                  and len(bytes(action[2])) == frame_size
                  and masked_frame_sha(bytes(action[2]), spans) == frame_sha
                  for action, (pc_size, frame_size, spans, pc_sha, frame_sha)
                  in zip(lane, EXPECTED_GEOMETRY)
              ))
        check("the control is the 44/54 shape and the treatment is 48/58, "
              "so the selector fields really are the difference",
              len(lane) == 2
              and (len(bytes(lane[0][1])), len(bytes(lane[0][2])))
              == (CONTROL_PC_SIZE, CONTROL_FRAME_SIZE)
              and (len(bytes(lane[1][1])), len(bytes(lane[1][2])))
              == (TREATMENT_PC_SIZE, TREATMENT_FRAME_SIZE),
              str([(len(bytes(a[1])), len(bytes(a[2]))) for a in lane]))
        check("each emitted pc carries trigger+offset coordinates, "
              "byte-exact, at ITS OWN spans",
              len(lane) == 2 and all(
                  b"".join(bytes(action[1])[s:e] for s, e in spans)
                  == struct.pack(
                      "<fff",
                      f32_exact(trigger_xyz[0] + spec[5]),
                      trigger_xyz[1], trigger_xyz[2])
                  for action, spec, (_p, _f, spans, _ps, _fs)
                  in zip(lane, EXPECTED_ELEMENTS, EXPECTED_GEOMETRY)
              ))
        check("frame == frame_pc(pc) on both dispatched PCs",
              len(lane) == 2 and all(
                  bytes(action[2]) == legacy.frame_pc(bytes(action[1]))
                  for action in lane
              ))
        check("the pair event is named once",
              state.events.count(PAIR_EVENT) == 1)
        check("the one-shot latch is set",
              state.ground_loot_nameprop_sent is True)
        check("the HYP-PF-032 lane never fired: its latch and its event are "
              "untouched",
              state.ground_loot_pair_sent is False
              and state.events.count(SIBLING_EVENT) == 0)

        if not want_json:
            print("-- 3. the independent walker, byte zero to the end, both "
                  "frames --")
        walked = []
        for ordinal, spec in enumerate(EXPECTED_ELEMENTS):
            key, dword, mask, gate, index, x_offset, _delay = spec
            read = None
            error = ""
            try:
                read = walk_nameprop_frame(
                    bytes(lane[ordinal][1])
                    if ordinal < len(lane) else b"")
            except WalkError as exc:
                error = str(exc)
            walked.append(read)
            check("frame %d parses by hand with count=1" % ordinal,
                  read is not None, error)
            if read is None:
                continue
            wire_xyz = (
                f32_exact(trigger_xyz[0] + x_offset),
                trigger_xyz[1], trigger_xyz[2],
            )
            check("walked frame %d: key %d, mask 0x%02X, dword %d, gate %s, "
                  "index %s" % (ordinal, key, mask, dword, gate, index),
                  read["key"] == key and read["mask"] == mask
                  and read["dword"] == dword and read["gate"] == gate
                  and read["index"] == index, str(read))
            check("walked frame %d position equals trigger+offset" % ordinal,
                  read["position"] == wire_xyz, str(read))

        if len(walked) == 2 and all(w is not None for w in walked):
            check("the walker read NO gate and NO index out of the control, "
                  "and gate 1 with index 6 out of the treatment",
                  walked[0]["gate"] is None and walked[0]["index"] is None
                  and walked[1]["gate"] == 1 and walked[1]["index"] == 6,
                  str(walked))
            check("the walker read the SAME dword and the SAME position out "
                  "of both frames",
                  walked[0]["dword"] == walked[1]["dword"]
                  and walked[0]["position"] == walked[1]["position"],
                  str(walked))

        if not want_json:
            print("-- 3b. the two frames differ ONLY where the experiment "
                  "says they may --")
        if len(lane) == 2:
            a, b = bytes(lane[0][1]), bytes(lane[1][1])
            # Envelope through the element key is the same length in both, so
            # a byte-for-byte comparison is meaningful up to the mask byte.
            check("the envelope up to the element key differs in nothing",
                  a[:17] == b[:17], "%s | %s" % (a[:17].hex(), b[:17].hex()))
            check("the element keys differ (3 vs 4) and the mask bytes "
                  "differ (0x12 vs 0x3A)",
                  a[17:22] != b[17:22] and a[23] == CONTROL_MASK
                  and b[23] == TREATMENT_MASK)
            check("the payload dword bytes are identical, so the label TEXT "
                  "is the same string in both frames",
                  a[24:29] == b[24:29], "%s | %s" % (a[24:29].hex(),
                                                     b[24:29].hex()))
            check("the coordinate bytes are identical, so the two labels "
                  "land on the same pixels",
                  b"".join(a[s:e] for s, e in CONTROL_COORD_SPANS)
                  == b"".join(b[s:e] for s, e in TREATMENT_COORD_SPANS))
            check("the treatment is exactly four bytes longer, which is the "
                  "gate tag pair plus the index tag pair and nothing else",
                  len(b) - len(a) == 4)

        if not want_json:
            print("-- 4. nothing committed, and the one-shot guard --")
        after = table_row_counts(db_path)
        check("NO table changed row count on the pair",
              after == before,
              json.dumps({k: (before[k], after[k]) for k in after
                          if before[k] != after[k]}))
        again = state.dispatch(legacy.parse_outer(target_pos_pc(
            legacy, position.x, position.y, position.z)))
        check("a second TargetPos adds neither frame",
              all(a[0] not in LANE_LABELS for a in again),
              str([a[0] for a in again]))
        check("the pair event stayed one-shot end to end",
              state.events.count(PAIR_EVENT) == 1)
        final = table_row_counts(db_path)
        check("NO table changed row count across the whole probe",
              final == before)

        if not want_json:
            print("-- 4b. a second session, a SHIFTED trigger: the frames "
                  "must follow the trigger, not any constant --")
        state2 = state_type("nameprop_shift")
        state2.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("nameprop_shift")))
        characters2 = store.list_characters(state2.foundation.account_id)
        if not characters2:
            created2 = state2.dispatch(
                legacy.parse_outer(legacy._V25_REAL_CREATE_PC))
            assert created2 and created2[0][0] == "FOUNDATION_CREATE_COMMITTED"
            characters2 = store.list_characters(state2.foundation.account_id)
        start2 = state2.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(characters2[-1].selector)))
        assert start2
        state2.runtime_ack_sent = True
        shifted_xyz = (
            f32_exact(trigger_xyz[0] + 1000.0),
            f32_exact(trigger_xyz[1] - 250.0),
            f32_exact(trigger_xyz[2] + 5.0),
        )
        actions2 = state2.dispatch(legacy.parse_outer(target_pos_pc(
            legacy, shifted_xyz[0], shifted_xyz[1], shifted_xyz[2])))
        lane2 = [a for a in actions2 if a[0] in LANE_LABELS]
        check("the shifted trigger also emits exactly two frames",
              len(lane2) == 2, str([a[0] for a in actions2]))
        check("the shifted frames carry shifted-trigger+offset coordinates, "
              "byte-exact (trigger-relative, not constant)",
              len(lane2) == 2 and all(
                  b"".join(bytes(action[1])[s:e] for s, e in spans)
                  == struct.pack(
                      "<fff",
                      f32_exact(shifted_xyz[0] + spec[5]),
                      shifted_xyz[1], shifted_xyz[2])
                  for action, spec, (_p, _f, spans, _ps, _fs)
                  in zip(lane2, EXPECTED_ELEMENTS, EXPECTED_GEOMETRY)
              ))
        check("the shifted frames still match their masked-template pins",
              len(lane2) == 2 and all(
                  masked_pc_sha(bytes(action[1]), spans) == pc_sha
                  for action, (_p, _f, spans, pc_sha, _fs)
                  in zip(lane2, EXPECTED_GEOMETRY)
              ))

        results.append({
            "action_labels": [a[0] for a in lane],
            "scheduler_delays": [a[3] for a in lane],
            "pc_lengths": [len(bytes(a[1])) for a in lane],
            "frame_lengths": [len(bytes(a[2])) for a in lane],
            "pc_sha256": [
                hashlib.sha256(bytes(a[1])).hexdigest().upper()
                for a in lane
            ],
            "frame_sha256": [
                hashlib.sha256(bytes(a[2])).hexdigest().upper()
                for a in lane
            ],
            "walked_frames": walked,
        })

        source_sha_after = sha256_file(db_source)
        if not want_json:
            print("-- 5. the source database was never touched --")
        check("the source database sha is unchanged end to end",
              source_sha_after == source_sha_before,
              "%s -> %s" % (source_sha_before, source_sha_after))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if want_json:
        print(json.dumps({
            "guards": guards,
            "failures": failures,
            "results": results,
            "source_sha256": source_sha_before,
        }, indent=2))
    else:
        print()
        print("guards run: %d" % guards)
    if failures:
        if not want_json:
            print("RESULT: FAIL - %d guard(s) drifted: %s"
                  % (len(failures), failures))
        return 1
    if not want_json:
        print("RESULT: PASS - the real dispatcher appends a CONTROL frame "
              "(mask 0x12, pc 44 / frame 54, no selector fields) and a "
              "TREATMENT frame (mask 0x3A, pc 48 / frame 58, gate 1 and "
              "index 6) exactly once after the inherited actions of the "
              "first exact TargetPos; the two carry byte-identical payload "
              "dwords and byte-identical coordinates and differ by exactly "
              "the four selector bytes; the independent walker reads no "
              "selector out of the control and gate 1 with index 6 out of "
              "the treatment; every masked-template pin holds at its own "
              "spans and follows a shifted trigger; nothing is committed; "
              "the second TargetPos adds nothing; the HYP-PF-032 lane never "
              "fires; and the source database is untouched.  The scheduler "
              "delays are 0.0 and 1.50 -- a DEADLINE OFFSET, not a measured "
              "wire gap -- and whether the client accepts mask 0x3A at all, "
              "or the selector reaches any label, is GT-069, attended, "
              "not run")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
