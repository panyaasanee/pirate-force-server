#!/usr/bin/env python3
"""GROUND-LOOT-001: headless replay for HYP-PF-032 (GT-045).

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the ground-loot lane, driven through the REAL make_state_class
dispatcher on a throwaway COPY of the database, APPENDS exactly TWO extra
actions -- the pinned GSCN_RunTimeProtocolRes (0x6E9D) derived-bit-0x08
frames, NEAR at delay 0.0 then FAR at delay 0.10, each carrying ONE
0x5F85B0 element under count=1 -- AFTER the inherited actions of the first
exact TargetPos following the runtime ack, exactly once (a second TargetPos
adds neither frame), commits NOTHING (no table changes row count, no socket
action rides any action), and leaves the frozen population and the position
checkpoint of the triggering frame untouched.  ONE element per frame is the
V43 lesson: a real client raised ErrorData=28317 on a combined multi-record
derived-mask RuntimeRes collection, and the shipped fix is one record per
frame (make_port_royal_npc_single_packets) -- the attended run must measure
rendering, not the count.  An independent walker in this file reads each
emitted 44-byte PC back from byte zero (msg id 0x6E9D, version 4, inherited
mask 0, derived mask 0x08, count 1, then key u32, dirty mask 0x12, payload
dword u32, three f32 world coordinates) WITHOUT importing the module's
composer for the read -- the tag layouts of the legacy helpers are
re-stated locally, which is the point.

It proves NOTHING about a client.  No client has ever been shown a bit-0x08
frame; whether the client RENDERS anything for the 0x5F85B0 list is GT-045
(attended, not run).  Bit 0x08 = "ground loot" is UNPROVEN, the payload
dword is NOT claimed to be an item template id, and drawing is not pickup.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.
The file named by ``--db`` (default ``state/pirateforce.sqlite3``) is read
once to copy it and once to hash it, and is never opened by SQLite for the
session; everything runs on the temporary copy, which is deleted on exit.

Usage:
    py -3 tools/pf_ground_loot_headless_replay.py
    py -3 tools/pf_ground_loot_headless_replay.py --json
    py -3 tools/pf_ground_loot_headless_replay.py --db state/pirateforce.sqlite3

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
from pirateforce_foundation import ground_loot_hypothesis as G  # noqa: E402
from pirateforce_foundation.model import Position  # noqa: E402
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "ground_loot_hypothesis_bit08_render.json"
DEFAULT_DB = ROOT / "state" / "pirateforce.sqlite3"

RUNTIME_PROTOCOL_RES_ID = 0x6E9D
DERIVED_BIT = 0x08
ELEMENT_MASK = 0x12
PC_SIZE = 44
FRAME_SIZE = 54
NEAR_PC_SHA = (
    "A3570BC9185BEF70ABB3810448F6E3F605437B2F1BFAB1DF474882AD3661EA03"
)
NEAR_FRAME_SHA = (
    "A9D4F13409DF636C40FEA7FE7DEA38DD542D09E140BB073FBDD367B5758A5AE0"
)
FAR_PC_SHA = (
    "4B14A026763F53FFD65210C2F2BCC0122B096A6877455C84DAAED71366F07F3A"
)
FAR_FRAME_SHA = (
    "B13942BBCC933B4E135BCD40FE0C3D39B4EF053C31892F1F8EC929F702223989"
)
NEAR_LABEL = "GROUND_LOOT_BIT08_RENDER_NEAR_ONCE"
FAR_LABEL = "GROUND_LOOT_BIT08_RENDER_FAR_ONCE"
LANE_LABELS = (NEAR_LABEL, FAR_LABEL)
PAIR_EVENT = "hyp_pf_032_ground_loot_bit08_pair_committed"
# The frozen profile's two elements, restated here so the walker's element
# comparison shares nothing with the module: key, payload dword, x, y, z.
# One frame per element -- near first, far second.
EXPECTED_ELEMENTS = (
    (1, 2600001, -9209.95703125, -2830.045166015625, 223.29209899902344),
    (2, 2600001, -8439.95703125, -2830.045166015625, 223.29209899902344),
)
EXPECTED_DELAYS = (0.0, 0.10)
EXPECTED_SHAS = (
    (NEAR_PC_SHA, NEAR_FRAME_SHA),
    (FAR_PC_SHA, FAR_FRAME_SHA),
)


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u32(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 4], "little")


def _f32(buf: bytes, at: int) -> float:
    return struct.unpack_from("<f", buf, at)[0]


def walk_ground_loot_frame(pc: bytes) -> dict:
    """Read one single-element bit-0x08 PC by hand, byte zero to the end.

    Tag layouts re-stated locally from the legacy helpers: u16tag = tag byte
    then <H; u32tag = tag byte then <I; u8tag = tag byte then one value
    byte; f32tag = tag byte 0x2A then <f.
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
    if len(pc) < cur + 27:
        raise WalkError("the one element is truncated")
    if pc[cur] != 0x14:
        raise WalkError("the element key tag is not 0x14")
    key = _u32(pc, cur + 1)
    cur += 5
    if pc[cur] != 0x0B:
        raise WalkError("the element mask tag is not 0x0B")
    mask = pc[cur + 1]
    cur += 2
    if mask != ELEMENT_MASK:
        raise WalkError("the element dirty mask is not 0x12")
    if pc[cur] != 0x14:
        raise WalkError("the element dword tag is not 0x14")
    dword = _u32(pc, cur + 1)
    cur += 5
    position = []
    for axis in ("x", "y", "z"):
        if pc[cur] != 0x2A:
            raise WalkError("the element %s tag is not 0x2A" % axis)
        position.append(_f32(pc, cur + 1))
        cur += 5
    if cur != len(pc):
        raise WalkError("the reader accounted for %d of %d bytes"
                        % (cur, len(pc)))
    return {"count": count, "key": key, "mask": mask, "dword": dword,
            "position": tuple(position)}


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
    scenario = G.load_ground_loot_hypothesis_scenario(SCENARIO)

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("the msg id, masks and pins agree with the module",
          RUNTIME_PROTOCOL_RES_ID == legacy.GSCN_RUNTIME_PROTOCOL_RES
          and DERIVED_BIT == G.GROUND_LOOT_DERIVED_BIT
          and ELEMENT_MASK == G.GROUND_LOOT_ELEMENT_MASK
          and PC_SIZE == G.GROUND_LOOT_PC_SIZE
          and FRAME_SIZE == G.GROUND_LOOT_FRAME_SIZE
          and NEAR_PC_SHA == G.GROUND_LOOT_NEAR_PC_SHA256
          and NEAR_FRAME_SHA == G.GROUND_LOOT_NEAR_FRAME_SHA256
          and FAR_PC_SHA == G.GROUND_LOOT_FAR_PC_SHA256
          and FAR_FRAME_SHA == G.GROUND_LOOT_FAR_FRAME_SHA256)
    check("the scenario is the allowlisted HYP-PF-032 profile",
          scenario.hypothesis_id == "HYP-PF-032"
          and scenario.scenario_id == "ground_loot_hypothesis_bit08_render"
          and len(scenario.elements) == 2)
    check("this reader's frozen elements agree with the profile's",
          tuple(
              (e.element_key, e.payload_dword, e.x, e.y, e.z)
              for e in scenario.elements
          ) == EXPECTED_ELEMENTS)

    source_sha_before = sha256_file(db_source)
    tmp = tempfile.mkdtemp(prefix="pf_ground_loot001_")
    results: list[dict] = []
    try:
        db_path = Path(tmp) / "ground_loot001.sqlite3"
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
            ground_loot_hypothesis_scenario=scenario,
        )
        state = state_type("ground_loot")
        state.dispatch(legacy.parse_outer(
            legacy._synthetic_client_login_pc("ground_loot")))
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
              state.ground_loot_pair_sent is False)

        if not want_json:
            print("-- 2. the first exact TargetPos, two appended "
                  "single-element frames --")
        before = table_row_counts(db_path)
        expected_frames = G.make_ground_loot_frames(legacy, scenario)
        position = state.foundation.selected.position
        trigger = legacy.parse_outer(target_pos_pc(
            legacy, position.x, position.y, position.z))
        actions = state.dispatch(trigger)
        ground = [a for a in actions if a[0] in LANE_LABELS]

        check("exactly two ground-loot actions leave the dispatcher",
              len(ground) == 2, str([a[0] for a in actions]))
        check("the two actions are APPENDED LAST, near then far, after the "
              "inherited actions",
              len(actions) >= 2
              and [a[0] for a in actions[-2:]] == [NEAR_LABEL, FAR_LABEL]
              and all(a[0] not in LANE_LABELS for a in actions[:-2]),
              str([a[0] for a in actions]))
        check("inherited actions still ride the same trigger frame",
              len(actions) > 2, str([a[0] for a in actions]))
        check("the emitted bytes equal the composer's, frame for frame",
              len(ground) == 2 and all(
                  bytes(action[1]) == expected[0]
                  and bytes(action[2]) == expected[1]
                  for action, expected in zip(ground, expected_frames)
              ))
        check("the delays are 0.0 (near) then 0.10 (far)",
              len(ground) == 2
              and tuple(action[3] for action in ground) == EXPECTED_DELAYS,
              str([a[3] for a in ground]))
        check("no socket action rides any action",
              all(len(a) == 4 for a in actions))
        check("each emitted pc and frame matches its size and sha256 pins",
              len(ground) == 2 and all(
                  len(bytes(action[1])) == PC_SIZE
                  and hashlib.sha256(bytes(action[1])).hexdigest().upper()
                  == pc_sha
                  and len(bytes(action[2])) == FRAME_SIZE
                  and hashlib.sha256(bytes(action[2])).hexdigest().upper()
                  == frame_sha
                  for action, (pc_sha, frame_sha)
                  in zip(ground, EXPECTED_SHAS)
              ))
        check("frame == frame_pc(pc) on both dispatched PCs",
              len(ground) == 2 and all(
                  bytes(action[2]) == legacy.frame_pc(bytes(action[1]))
                  for action in ground
              ))
        check("the pair event is named once",
              state.events.count(PAIR_EVENT) == 1)
        check("the one-shot latch is set",
              state.ground_loot_pair_sent is True)

        if not want_json:
            print("-- 3. the independent walker, byte zero to the end, both "
                  "frames --")
        walked = []
        for ordinal, (key, dword, x, y, z) in enumerate(EXPECTED_ELEMENTS):
            read = None
            error = ""
            try:
                read = walk_ground_loot_frame(
                    bytes(ground[ordinal][1])
                    if ordinal < len(ground) else b"")
            except WalkError as exc:
                error = str(exc)
            walked.append(read)
            check("frame %d parses by hand with count=1" % ordinal,
                  read is not None, error)
            if read is None:
                continue
            wire_xyz = tuple(
                struct.unpack("<f", struct.pack("<f", value))[0]
                for value in (x, y, z)
            )
            check("walked frame %d: key %d, mask 0x12, dword %d"
                  % (ordinal, key, dword),
                  read["key"] == key and read["mask"] == ELEMENT_MASK
                  and read["dword"] == dword, str(read))
            check("walked frame %d position equals the frozen coordinates"
                  % ordinal,
                  read["position"] == wire_xyz, str(read))

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

        results.append({
            "action_labels": [a[0] for a in ground],
            "pc_sha256": [
                hashlib.sha256(bytes(a[1])).hexdigest().upper()
                for a in ground
            ],
            "frame_sha256": [
                hashlib.sha256(bytes(a[2])).hexdigest().upper()
                for a in ground
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
        print("RESULT: PASS - the real dispatcher appends the two pinned "
              "single-element bit-0x08 frames (near 0.0, far 0.10; count=1 "
              "each, the V43-safe shape) exactly once after the inherited "
              "actions of the first exact TargetPos, the independent walker "
              "reads both frozen elements back from byte zero, nothing is "
              "committed, the second TargetPos adds nothing, and the source "
              "database is untouched (whether the client renders anything "
              "is GT-045, attended, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
