#!/usr/bin/env python3
"""HP-DEATH-002: headless wire proof for the HYP-PF-022 death sweep.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with the opt-in scenario
``scenarios/hp_death_hypothesis_death_sweep.json`` and a throwaway database,
answers ONE accepted client frame with FOUR ``UpdateAttrVital`` 0x309A frames,
and that the third of them carries -- verified by an INDEPENDENT tag walker in
this file, not by the encoder's own decoder -- the exact pair the client's
``IsDead`` predicate (``0x454AC0``) reads:

    BasicAttr mask bit 0x0004, wire tag 0x14, value == 0          (current HP)
    BasicAttr mask bit 0x0080, wire tag 0x2A, value  > 0.0f       (death timer)

in ascending-mask-bit order inside the block, riding the same envelope the
client has been accepting since NAME-002.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with those bytes.  That is GT-019, attended.
It also does not prove the death ANIMATION or the ``TargetIsDead`` panel: the
dead-state sync ``0x4437C0`` has exactly one caller in the client image
(``0x4566A7``, the actor-entry update path), so ``UpdateAttrVital`` cannot
reach it.  The local player's ``L"Main_Dead"`` window is a different mechanism
-- a per-frame gate in ``CMyActor::Update`` -- and IS expected to fire.

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.  The
canonical database is never opened: everything runs on a fresh temporary
SQLite file that is deleted on exit.  No repository file is written unless
``--evidence <path>`` is handed in.

Usage:
    py -3 tools/pf_hp_death002_headless_replay.py
    py -3 tools/pf_hp_death002_headless_replay.py --json
    py -3 tools/pf_hp_death002_headless_replay.py --evidence reports/hp_death002_headless.json

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
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402
from pirateforce_foundation.store import SQLiteStore  # noqa: E402


SCENARIO = ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# ---------------------------------------------------------------------------
# An INDEPENDENT reader.  It deliberately does not import decode_actor_attr:
# the point of this file is to check the dispatcher's bytes with a second pair
# of eyes.  It knows only the block layout HP-DEATH-001 and STATS-PROG-001
# recorded, and the four tag widths it needs.
# ---------------------------------------------------------------------------
SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                0x26: 4, 0x2A: 4, 0x32: 8}
BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32),
)


def walk_basic_block(body: bytes) -> dict:
    """Read the DBAttribute + BasicAttr head of one ActorAttr body, by hand.

    Returns ``{"identity": int, "basic_mask": int, "fields": {bit: value}}``.
    Raises ``ValueError`` on anything that is not the pinned layout.
    """
    if len(body) < 11 or body[0] != 0x0B:
        raise ValueError("body does not open with the DBAttribute u8 mask")
    if body[1] != 0x01:
        raise ValueError("DBAttribute mask is not the identity-only 0x01")
    if body[2] != 0x32:
        raise ValueError("the identity is not a qword tag 0x32")
    identity = int.from_bytes(body[3:11], "little")
    cursor = 11
    if body[cursor] != 0x12:
        raise ValueError("the BasicAttr mask is not a u16 tag 0x12")
    basic_mask = int.from_bytes(body[cursor + 1:cursor + 3], "little")
    cursor += 3
    fields = {}
    for bit, tag in BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if body[cursor] != tag:
            raise ValueError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, body[cursor])
            )
        if tag == 0x48:
            length = int.from_bytes(body[cursor + 1:cursor + 5], "little")
            fields[bit] = body[cursor + 5:cursor + 5 + length].decode("utf-16-le")
            cursor += 5 + length
            continue
        width = SCALAR_WIDTH[tag]
        raw = body[cursor + 1:cursor + 1 + width]
        fields[bit] = (
            struct.unpack("<f", raw)[0] if tag == 0x2A
            else int.from_bytes(raw, "little")
        )
        cursor += 1 + width
    return {"identity": identity, "basic_mask": basic_mask, "fields": fields,
            "cursor": cursor}


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
    scenario = sp.load_hp_death_hypothesis_scenario(SCENARIO)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "hp_death002.sqlite3"
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
        state_type = make_state_class(
            legacy, lifecycle, projector,
            hp_death_hypothesis_scenario=scenario,
        )
        state = state_type("hp_death002")
        state.dispatch(legacy.parse_outer(legacy._synthetic_client_login_pc()))
        created = state.dispatch(
            legacy.parse_outer(legacy._V25_REAL_CREATE_PC)
        )
        if not want_json:
            print("-- 0. bring one writable character to runtime --")
        check("the harness committed a character",
              created and created[0][0] == "FOUNDATION_CREATE_COMMITTED")
        characters = store.list_characters(state.foundation.account_id)
        selected = state.dispatch(legacy.parse_outer(
            legacy._synthetic_start_game_pc(characters[0].selector)
        ))
        check("the harness selected it",
              selected and selected[0][0] == "FOUNDATION_SELECTED_START_GAME")
        state.runtime_ack_sent = True

        db_before = hashlib.sha256(db_path.read_bytes()).hexdigest().upper()

        if not want_json:
            print("-- 1. one accepted client frame in, four frames out --")
        actions = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("the dispatcher answered with four frames",
              len(actions) == len(sp.HP_DEATH_STEP_ORDER), str(len(actions)))
        check("in the scenario's pinned order",
              [label for label, _p, _f, _d in actions]
              == [sp.HP_DEATH_ACTION_LABEL_PREFIX + label
                  for label in scenario.step_order])
        check("and named the sweep event exactly once",
              state.events.count("hp_death_hypothesis_death_sweep_sent") == 1)

        if not want_json:
            print("-- 2. every frame, read by an independent tag walker --")
        rows = []
        lethal_labels = []
        for index, (label, pc, frame, delay) in enumerate(actions):
            step = sp.HP_DEATH_STEP_ORDER[index]
            parsed = legacy.parse_outer(pc)
            check("frame %s parses with the frozen v141 outer parser" % step,
                  parsed is not None)
            check("frame %s is UpdateAttrVital 0x309A" % step,
                  pc[16:18] == sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"))
            check("frame %s carries an ActorAttr 0x12AD collection" % step,
                  pc[sp.STATS_PC_PAYLOAD_OFFSET + 3:
                     sp.STATS_PC_PAYLOAD_OFFSET + 6]
                  == legacy.u16tag(0x12, sp.ACTOR_ATTR_ID))
            body = sp.hp_death_attr_body(pc)
            read = walk_basic_block(body)
            check("frame %s carries the pinned BasicAttr mask 0x%04X"
                  % (step, sp.HP_DEATH_PROBE_BASIC_MASK[step]),
                  read["basic_mask"] == sp.HP_DEATH_PROBE_BASIC_MASK[step],
                  hex(read["basic_mask"]))
            hp_current = read["fields"].get(0x0004)
            timer = read["fields"].get(0x0080)
            is_dead = hp_current == 0 and timer is not None and timer > 0.0
            if is_dead:
                lethal_labels.append(step)
            rows.append({
                "index": index,
                "step": step,
                "action_label": label,
                "delay_seconds": delay,
                "pc_size": len(pc),
                "frame_size": len(frame),
                "attr_body_size": len(body),
                "attr_body_sha256": hashlib.sha256(body).hexdigest().upper(),
                "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
                "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
                "basic_mask": read["basic_mask"],
                "identity": read["identity"],
                "hp_current_bit_0x0004": hp_current,
                "death_timer_bit_0x0080": timer,
                "client_is_dead_predicate": is_dead,
                "attr_body_hex": body.hex(),
            })

        if not want_json:
            print("-- 3. the death predicate, on the wire --")
        check("exactly one frame satisfies IsDead (hp==0 AND timer>0)",
              lethal_labels == list(sp.HP_DEATH_LETHAL_STEP_LABELS),
              str(lethal_labels))
        armed = rows[sp.HP_DEATH_STEP_ORDER.index("TIMER_ARMED")]
        check("the armed frame carries the timer but is NOT lethal",
              armed["death_timer_bit_0x0080"] == sp.HP_DEATH_TIMER_SECONDS
              and armed["client_is_dead_predicate"] is False)
        killed = rows[sp.HP_DEATH_STEP_ORDER.index("HP_ZERO")]
        check("the lethal frame carries current HP == 0",
              killed["hp_current_bit_0x0004"] == 0)
        check("the lethal frame carries a positive death timer",
              killed["death_timer_bit_0x0080"] > 0.0)
        check("that timer clears the L\"Main_Dead\" gate DURATION_DYING - 0.5",
              killed["death_timer_bit_0x0080"]
              >= sp.DURATION_DYING_IMAGE_DEFAULT
              - sp.DURATION_DYING_WINDOW_MARGIN)
        check("the baseline frame carries no death bit at all",
              rows[0]["death_timer_bit_0x0080"] is None
              and not rows[0]["basic_mask"] & sp.HP_DEATH_TIMER_MASK_BIT)
        check("the sweep ends with the character alive on the wire",
              rows[-1]["hp_current_bit_0x0004"] > 0)

        if not want_json:
            print("-- 4. pins and discipline --")
        check("every frame reproduces its module pin",
              all(row["attr_body_sha256"]
                  == sp.HP_DEATH_PROBE_ATTR_BODY_SHA256[row["step"]]
                  and row["pc_sha256"]
                  == sp.HP_DEATH_PROBE_PC_SHA256[row["step"]]
                  and row["frame_sha256"]
                  == sp.HP_DEATH_PROBE_FRAME_SHA256[row["step"]]
                  for row in rows))
        check("every frame reproduces its scenario pin",
              all(json.loads(SCENARIO.read_text(encoding="utf-8"))
                  ["probe"]["per_step"][row["step"]]["pc_sha256"]
                  == row["pc_sha256"] for row in rows))
        check("the spacing is the scenario's spacing",
              [row["delay_seconds"] for row in rows]
              == [sp.HP_DEATH_FIRST_DELAY_SECONDS]
              + [scenario.spacing_seconds] * (len(rows) - 1))
        check("the sweep wrote nothing to the database",
              hashlib.sha256(db_path.read_bytes()).hexdigest().upper()
              == db_before)
        check("the sweep took no socket action",
              all(len(action) == 4 for action in actions))

    verdict = {
        "milestone": "HP-DEATH-002",
        "hypothesis_id": sp.HP_DEATH_HYPOTHESIS_ID,
        "scenario": SCENARIO.relative_to(ROOT).as_posix(),
        "layer": "wire_only_no_client_no_socket_no_server_process",
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "death_predicate": {
            "source": "HP-DEATH-001 IsDead 0x454AC0",
            "rule": "f32[BasicAttr+0x58] > 0.0f AND u32[BasicAttr+0x44] == 0",
            "lethal_steps_observed": lethal_labels,
        },
        "not_claimed": [
            "any client rendering of death (GT-019, attended, not run)",
            "the death animation or TargetIsDead panel, which UpdateAttrVital "
            "cannot reach: 0x4437C0 has exactly one caller, 0x4566A7",
            "the deployed value of DURATION_DYING",
            "any respawn, relive or marker behavior",
            "any persistence: HP has no write path in this project",
        ],
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
            print("RESULT: PASS - HP-DEATH-002 death sweep proven at the "
                  "wire layer (client layer = GT-019, not run)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
