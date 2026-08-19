#!/usr/bin/env python3
"""RUNTIMERES-DISPATCH-001: headless wire proof for the spawn-then-kill sweep.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in scenario
``scenarios/runtimeres_death_hypothesis_spawn_then_kill.json`` and a throwaway
database, answers ONE accepted client frame with THREE
``GSCN_RunTimeProtocolRes`` id ``0x6E9D`` frames, and that those frames are

  (a) **byte-for-byte** the frames ``build_runtimeres_death_sweep`` composes --
      same labels, same PCs, same framed bytes, same delays, compared with
      ``==`` on the bytes objects, not by hash summary alone; and
  (b) independently readable, by a tag walker written in THIS file that does
      not import the encoder's decoder, as the sweep the round-85 static RE
      says can reach ``L"_F_DIE_000"``:

        frame 1  SPAWN        identity I, HP  > 0, no BasicAttr bit 0x0080
        frame 2  DYING_LATCH  identity I, HP == 0, timer  20.0f  > 0
        frame 3  DEATH_TASK   identity I, HP == 0, timer   0.0f <= 0

      all three carrying the inherited change mask ``0x00`` and the derived
      change mask bit ``0x02`` (the actor-entry collection at ``+0x1C``).

The polarity is inverted from intuition and is the point of the third frame:
``vt+0x40`` (0x43BDA0) is ``HP == 0 AND timer > 0`` and only latches
``[actor+0x70] |= 0x200``; ``vt+0x3C`` (0x43BD70) is ``HP == 0 AND timer <= 0``
and is what gates ``0x443990`` -> ``call 0x472810`` -> ``CActorTask_Dead``.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of this profile.**  That is GT-022, attended, not run here.
It does not prove that the dying latch is a prerequisite for the death task
(the two predicates are mutually exclusive branches inside ``0x4437C0`` and the
task gate does not read the ``0x200`` flag).  It does not narrow round 85's 229
unresolved vtable ``+0x20`` dispatch sites.  It claims nothing about the
original server, about any damage model, about persistence (nothing on this
path has a write path), or about production (``production_allowed`` is False
everywhere it appears).

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.  The
canonical database is never opened: everything runs on a fresh temporary SQLite
file that is deleted on exit.  No repository file is written unless
``--evidence <path>`` is handed in.  Pure stdlib.

Usage:
    py -3 tools/pf_runtimeres_death_headless_replay.py
    py -3 tools/pf_runtimeres_death_headless_replay.py --json
    py -3 tools/pf_runtimeres_death_headless_replay.py \
        --evidence reports/runtimeres_death001_headless.json

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the list.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
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
from pirateforce_foundation.runtime import make_state_class  # noqa: E402
from pirateforce_foundation import runtimeres_death_hypothesis as rdh  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SWEEP_EVENT = "runtimeres_death_hypothesis_spawn_then_kill_sent"
REPEAT_EVENT = "runtimeres_death_hypothesis_already_sent_no_reply"

# ---------------------------------------------------------------------------
# An INDEPENDENT reader.  It deliberately does not import
# decode_runtimeres_actor_entry_frame: the point of this file is to check the
# dispatcher's bytes with a second pair of eyes.  Every constant below is
# written out here rather than imported, and cross-checked against the module's
# own constant in section 0 so the two cannot drift apart in silence.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
RUNTIME_PROTOCOL_RES_VERSION = 4
INHERITED_MASK_ABSENT = 0x00
DERIVED_MASK_ACTOR_ENTRIES = 0x02
NPC_ACTOR_TYPE = 4                 # CNetNPC, jump-table case at 0x446B2C
NPC_ATTR_ID = 0x0AD5
MOVEMENT_ATTR_ID = 0x2067
BIT_CURRENT_HP = 0x0004            # u32 tag 0x14 @ BasicAttr +0x44
BIT_DEATH_TIMER = 0x0080           # f32 tag 0x2A @ BasicAttr +0x58
SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                0x26: 4, 0x2A: 4, 0x32: 8}
BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)
MOVEMENT_FIELD_SIZE = (
    (0x01, 15), (0x02, 5), (0x04, 2), (0x08, 5), (0x10, 5), (0x20, 5),
    (0x40, 5),
)


class WalkError(ValueError):
    """The dispatcher emitted something this reader cannot account for."""


def _u16(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 2], "little")


def _u64(buf: bytes, at: int) -> int:
    return int.from_bytes(buf[at:at + 8], "little")


def _wstr(pc: bytes, cursor: int) -> tuple[str, int]:
    if pc[cursor] != 0x48:
        raise WalkError("expected a wstring tag 0x48 at %d" % cursor)
    length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
    text = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
    return text, cursor + 5 + length


def walk_actor_entry_frame(pc: bytes) -> dict:
    """Read one GSCN_RunTimeProtocolRes actor-entry PC by hand, end to end."""
    if pc[0] != 0x12 or _u16(pc, 1) != RUNTIME_PROTOCOL_RES_ID:
        raise WalkError("the frame does not open with id 0x6E9D")
    if pc[3] != 0x14 or int.from_bytes(pc[4:8], "little") != 0:
        raise WalkError("envelope u32 field drift")
    if pc[8] != 0x08 or pc[9] != RUNTIME_PROTOCOL_RES_VERSION:
        raise WalkError("the envelope is not version 4")
    if pc[10] != 0x0B or pc[11] != INHERITED_MASK_ABSENT:
        raise WalkError("the inherited VitalData change mask is not absent")
    if pc[12] != 0x0B:
        raise WalkError("derived change mask tag drift")
    derived = pc[13]
    if not derived & DERIVED_MASK_ACTOR_ENTRIES:
        raise WalkError(
            "the derived change mask 0x%02X is missing bit 0x02, so the "
            "client never reads the +0x1C actor-entry collection" % derived
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

    attr_ids = []
    basic_mask = None
    attr_identity = None
    template_id = None
    visual_preset = None
    fields: dict = {}
    for _ in range(attr_count):
        if pc[cursor] != 0x12:
            raise WalkError("attr id tag drift")
        attr_id = _u16(pc, cursor + 1)
        attr_ids.append(attr_id)
        cursor += 3
        if pc[cursor] != 0x0B or pc[cursor + 1] != 0x01:
            raise WalkError("DBAttribute mask is not the identity-only 0x01")
        cursor += 2
        if pc[cursor] != 0x32:
            raise WalkError("attr identity tag drift")
        this_identity = _u64(pc, cursor + 1)
        cursor += 9
        if attr_id == NPC_ATTR_ID:
            attr_identity = this_identity
            if pc[cursor] != 0x12:
                raise WalkError("BasicAttr mask tag drift")
            basic_mask = _u16(pc, cursor + 1)
            cursor += 3
            if basic_mask & ~0x07FF:
                raise WalkError(
                    "BasicAttr mask 0x%04X carries a bit this reader cannot "
                    "read" % basic_mask
                )
            for bit, tag in BASIC_FIELD_ORDER:
                if not basic_mask & bit:
                    continue
                if pc[cursor] != tag:
                    raise WalkError(
                        "BasicAttr bit 0x%04X expected tag 0x%02X, found "
                        "0x%02X" % (bit, tag, pc[cursor])
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
            if pc[cursor] != 0x0B:
                raise WalkError("NPCAttr mask tag drift")
            npc_mask = pc[cursor + 1]
            cursor += 2
            if npc_mask & 0x01:
                if pc[cursor] != 0x12:
                    raise WalkError("NPCAttr template tag drift")
                template_id = _u16(pc, cursor + 1)
                cursor += 3
            if npc_mask & 0x04:
                visual_preset, cursor = _wstr(pc, cursor)
        elif attr_id == MOVEMENT_ATTR_ID:
            if pc[cursor] != 0x0B:
                raise WalkError("MovementAttr mask tag drift")
            mask = pc[cursor + 1]
            cursor += 2
            for bit, size in MOVEMENT_FIELD_SIZE:
                if mask & bit:
                    cursor += size
        else:
            raise WalkError("unexpected attr id 0x%04X" % attr_id)
    if cursor != len(pc):
        raise WalkError(
            "the reader accounted for %d of %d bytes" % (cursor, len(pc))
        )
    return {
        "derived_mask": derived,
        "actor_type": actor_type,
        "identity": identity,
        "attr_ids": attr_ids,
        "attr_identity": attr_identity,
        "basic_mask": basic_mask,
        "template_id": template_id,
        "visual_preset": visual_preset,
        "hp_current_bit_0x0004": fields.get(BIT_CURRENT_HP),
        "death_timer_bit_0x0080": fields.get(BIT_DEATH_TIMER),
    }


def main() -> int:
    want_json = "--json" in sys.argv
    evidence_path = None
    if "--evidence" in sys.argv:
        evidence_path = Path(sys.argv[sys.argv.index("--evidence") + 1])

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
    scenario = rdh.load_runtimeres_death_hypothesis_scenario(SCENARIO)
    pinned = json.loads(SCENARIO.read_text(encoding="utf-8"))

    if not want_json:
        print("-- 0. this reader's constants against the module's --")
    check("id 0x6E9D agrees with the module",
          RUNTIME_PROTOCOL_RES_ID == rdh.RUNTIME_PROTOCOL_RES_ID)
    check("envelope version 4 agrees with the module",
          RUNTIME_PROTOCOL_RES_VERSION == rdh.RUNTIME_PROTOCOL_RES_VERSION)
    check("derived change mask bit 0x02 agrees with the module",
          DERIVED_MASK_ACTOR_ENTRIES
          == rdh.DERIVED_CHANGE_MASK_ACTOR_ENTRIES)
    check("BasicAttr bits 0x0004/0x0080 agree with the module",
          BIT_CURRENT_HP == rdh.BASIC_BIT_CURRENT_HP
          and BIT_DEATH_TIMER == rdh.BASIC_BIT_DEATH_TIMER)
    check("the lane is not production-allowed", rdh.production_allowed is False)

    # The encoder's own composition, built OUTSIDE the dispatcher.  This is the
    # expectation every dispatched byte is measured against.
    probe = rdh.resolve_probe(legacy)
    expected = rdh.build_runtimeres_death_sweep(
        legacy, probe, rdh.runtimeres_death_lethal_unlock(scenario), scenario,
    )

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "runtimeres_death001.sqlite3"
        store = SQLiteStore(db_path, ROOT / "migrations")
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
            state_type = make_state_class(
                legacy, lifecycle, projector,
                runtimeres_death_hypothesis_scenario=(
                    scenario if enabled else None
                ),
            )
            state = state_type(token)
            state.dispatch(legacy.parse_outer(
                legacy._synthetic_client_login_pc()
            ))
            created = state.dispatch(
                legacy.parse_outer(legacy._V25_REAL_CREATE_PC)
            )
            assert created and created[0][0] == "FOUNDATION_CREATE_COMMITTED"
            characters = store.list_characters(state.foundation.account_id)
            selected = state.dispatch(legacy.parse_outer(
                legacy._synthetic_start_game_pc(characters[-1].selector)
            ))
            assert selected and selected[0][0] == "FOUNDATION_SELECTED_START_GAME"
            state.runtime_ack_sent = True
            return state

        if not want_json:
            print("-- 1. one accepted client frame in, three frames out --")
        state = boot("runtimeres_death001")
        db_before = hashlib.sha256(db_path.read_bytes()).hexdigest().upper()
        actions = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("the dispatcher answered with three frames",
              len(actions) == len(rdh.RUNTIMERES_DEATH_STEP_ORDER),
              str(len(actions)))
        check("in the scenario's pinned order",
              [row[0] for row in actions]
              == list(rdh.RUNTIMERES_DEATH_ACTION_LABELS))
        check("and named the sweep event exactly once",
              state.events.count(SWEEP_EVENT) == 1)
        check("the sweep took no socket action",
              all(len(action) == 4 for action in actions))

        if not want_json:
            print("-- 2. the dispatcher's bytes ARE the encoder's bytes --")
        # This is the load-bearing comparison of this whole file: if the
        # dispatcher ever composes a sweep of its own, invents a delay, or
        # reorders one step, these guards go red on the raw bytes.
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
        for index, label in enumerate(rdh.RUNTIMERES_DEATH_STEP_ORDER):
            if index >= len(actions) or index >= len(expected):
                continue
            got, want = actions[index], expected[index]
            check("step %s: the PC bytes are identical" % label,
                  got[1] == want[1])
            check("step %s: the framed bytes are identical" % label,
                  got[2] == want[2])
            check("step %s: the delay is identical" % label,
                  got[3] == want[3])
            check("step %s: frame == frame_pc(pc) on the dispatched PC" % label,
                  got[2] == legacy.frame_pc(got[1]))

        if not want_json:
            print("-- 3. every dispatched frame, read by an independent walker --")
        rows = []
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = rdh.RUNTIMERES_DEATH_STEP_ORDER[index]
            pin = rdh.RUNTIMERES_DEATH_PINS[step]
            parsed = legacy.parse_outer(pc)
            check("frame %s parses with the frozen v141 outer parser" % step,
                  parsed is not None)
            read = walk_actor_entry_frame(pc)
            check("frame %s carries derived change mask bit 0x02" % step,
                  bool(read["derived_mask"] & DERIVED_MASK_ACTOR_ENTRIES))
            check("frame %s carries actor_type 4 (CNetNPC)" % step,
                  read["actor_type"] == NPC_ACTOR_TYPE,
                  str(read["actor_type"]))
            check("frame %s: entry identity == NPCAttr identity" % step,
                  read["identity"] == read["attr_identity"])
            check("frame %s carries a visual preset" % step,
                  bool(read["visual_preset"]), repr(read["visual_preset"]))
            check("frame %s reproduces its module BasicAttr pin 0x%04X"
                  % (step, pin["basic_mask"]),
                  read["basic_mask"] == pin["basic_mask"],
                  hex(read["basic_mask"] or 0))
            check("frame %s reproduces its module byte pins" % step,
                  len(pc) == pin["pc_size"]
                  and len(frame) == pin["frame_size"]
                  and hashlib.sha256(pc).hexdigest().upper()
                  == pin["pc_sha256"]
                  and hashlib.sha256(frame).hexdigest().upper()
                  == pin["frame_sha256"])
            check("frame %s reproduces its scenario pin" % step,
                  pinned["probe"]["per_step"][step]["pc_sha256"]
                  == hashlib.sha256(pc).hexdigest().upper())
            hp = read["hp_current_bit_0x0004"]
            timer = read["death_timer_bit_0x0080"]
            rows.append({
                "index": index,
                "step": step,
                "action_label": label,
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "derived_mask": read["derived_mask"],
                "actor_type": read["actor_type"],
                "identity": read["identity"],
                "attr_ids": read["attr_ids"],
                "basic_mask": read["basic_mask"],
                "template_id": read["template_id"],
                "visual_preset": read["visual_preset"],
                "hp_current_bit_0x0004": hp,
                "death_timer_bit_0x0080": timer,
                "dying_latch_predicate_vt40":
                    hp == 0 and timer is not None and timer > 0.0,
                "death_task_predicate_vt3c":
                    hp == 0 and timer is not None and timer <= 0.0,
                "pc_hex": pc.hex(),
            })

        if not want_json:
            print("-- 4. spawn-then-kill, and the inverted polarity --")
        check("all three frames name ONE identity",
              len({row["identity"] for row in rows}) == 1,
              str([hex(row["identity"]) for row in rows]))
        check("that identity is the pinned probe 0x%04X"
              % rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY,
              rows[0]["identity"] == rdh.RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY)
        check("frame 1 is a LIVE spawn (an actor cannot be born dead)",
              rows[0]["hp_current_bit_0x0004"] > 0
              and rows[0]["death_timer_bit_0x0080"] is None)
        check("frame 1 places the actor (MovementAttr present)",
              MOVEMENT_ATTR_ID in rows[0]["attr_ids"])
        check("frames 2 and 3 both carry current HP == 0",
              all(row["hp_current_bit_0x0004"] == 0 for row in rows[1:]))
        check("frame 2 satisfies vt+0x40 (timer > 0) and NOT vt+0x3C",
              rows[1]["dying_latch_predicate_vt40"] is True
              and rows[1]["death_task_predicate_vt3c"] is False)
        check("frame 2 carries the pinned dying-latch timer %.1f"
              % rdh.DYING_LATCH_TIMER_SECONDS,
              rows[1]["death_timer_bit_0x0080"]
              == rdh.DYING_LATCH_TIMER_SECONDS)
        check("frame 3 satisfies vt+0x3C (timer <= 0) and NOT vt+0x40",
              rows[2]["death_task_predicate_vt3c"] is True
              and rows[2]["dying_latch_predicate_vt40"] is False)
        check("frame 3 carries the pinned death-task timer %.1f"
              % rdh.DEATH_TASK_TIMER_SECONDS,
              rows[2]["death_timer_bit_0x0080"]
              == rdh.DEATH_TASK_TIMER_SECONDS)
        check("the LAST frame is the one that opens the task gate",
              rows[-1]["death_task_predicate_vt3c"] is True)
        check("the spacing is the scenario's spacing",
              [row["delay_seconds"] for row in rows]
              == [rdh.RUNTIMERES_DEATH_FIRST_DELAY_SECONDS]
              + [scenario.spacing_seconds] * (len(rows) - 1))

        if not want_json:
            print("-- 5. one-shot, fail-closed, containment --")
        again = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [])
        check("and says so with a named event",
              state.events.count(REPEAT_EVENT) == 1)
        check("the sweep wrote nothing to the database",
              hashlib.sha256(db_path.read_bytes()).hexdigest().upper()
              == db_before)
        off = boot("runtimeres_death001_off", enabled=False)
        off_actions = off.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        # With the flag absent the frame keeps its frozen inherited answer (the
        # V99/V100 pair the baseline has always sent), which is the point: this
        # lane must add a branch, not replace the baseline everywhere.  What it
        # must NOT do is compose one byte of the sweep.
        off_labels = [row[0] for row in off_actions]
        check("with the scenario absent no death frame is composed",
              not any(
                  label.startswith(rdh.RUNTIMERES_DEATH_ACTION_LABEL_PREFIX)
                  for label in off_labels
              ), str(off_labels))
        check("with the scenario absent none of the sweep's bytes appear",
              not ({row[1] for row in off_actions}
                   & {row[1] for row in expected}))
        check("and names no sweep event",
              SWEEP_EVENT not in off.events)

    verdict = {
        "milestone": "RUNTIMERES-DISPATCH-001",
        "hypothesis_id": rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "scenario": SCENARIO.relative_to(ROOT).as_posix(),
        "layer": "wire_only_no_client_no_socket_no_server_process",
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "dispatch": {
            "trigger": "one accepted 34-byte ascii12 chat-input frame",
            "frames_per_accepted_request": len(actions),
            "one_shot": True,
            "socket_action": "none",
            "database_write": "none",
        },
        "polarity": {
            "dying_latch_predicate_vt40": rdh.DYING_LATCH_PREDICATE_VA,
            "dying_latch_rule": "hp == 0 AND timer > 0.0f",
            "death_task_predicate_vt3c": rdh.DEATH_TASK_PREDICATE_VA,
            "death_task_rule": "hp == 0 AND timer <= 0.0f",
        },
        "not_claimed": list(rdh.RUNTIMERES_DEATH_NONCLAIMS),
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
                  "spawn-then-kill sweep byte for byte (client layer = "
                  "GT-022, not run)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
