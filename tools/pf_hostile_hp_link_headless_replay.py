#!/usr/bin/env python3
"""HOSTILE-HP-LINK-001 (HYP-PF-038) headless replay -- the wire, without a game.

WHY THIS TOOL EXISTS
--------------------
Two things about this lane cannot be seen from a chair in front of the game:

  1. **Every named refusal is invisible in an attended round.**  The lane
     appends its refusals to an in-memory event list and nothing in ``src/``
     prints them, so a tester who triggers one sees a silent console and
     cannot tell "refused by name" from "nothing happened".  This tool drives
     every refusal on purpose and prints the name of each one.

  2. **Where the target was actually placed.**  The lane puts the target at
     the player's position plus the scenario's offsets, and an attended round
     that reports "I could not see the bird" needs to separate "the model was
     out of draw distance" from "the frame put it somewhere else".  Neither
     explanation is ruled out by GT-035: one round saw a model at the shipped
     offsets, which does not exclude ground-Z, occlusion, camera or terrain at
     any other position.  This tool decodes the placement back out of the
     composed bytes and prints it so the two can be told apart with evidence
     rather than by assumption.

Run it before an attended round with the player position the tester expects to
spawn at, and the numbers printed here are the numbers the round should see.

DISCIPLINE.  No database, no socket, no client, no arguments that could reach
one.  A socket trap is installed while the sweep is composed, so "this lane
opens no socket" is MEASURED here rather than asserted.  Exit 0 = every guard
held; exit 1 = something did not.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import socket
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation import hostile_hp_link_hypothesis as hh  # noqa: E402
from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO_PATH = (
    ROOT / "scenarios" / "hostile_hp_link_hypothesis_p30_sweep.json"
)


class RefusingSocket:
    """Any attempt to construct a socket while composing is a failure."""

    def __init__(self, *args, **kwargs):
        raise AssertionError(
            "this lane took a socket action; it is composer-only")


def _install_socket_trap():
    saved = socket.socket
    socket.socket = RefusingSocket
    return saved


def _restore_socket(saved):
    socket.socket = saved


def _as_f32(value):
    """The value as the wire will carry it, at four bytes of precision."""
    return struct.unpack("<f", struct.pack("<f", float(value)))[0]


def _decode(pc):
    return hh.decode_hostile_hp_link_frame(pc)


def _frame_rows(actions):
    rows = []
    for label, pc, frame, delay in actions:
        step = label.replace(hh.HOSTILE_HP_LINK_ACTION_LABEL_PREFIX, "")
        decoded = _decode(pc)
        row = {
            "step": step,
            "label": label,
            "delay_seconds": delay,
            "kind": decoded["kind"],
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "target_identity": "0x%04X" % decoded["target_identity"],
        }
        if decoded["kind"] == hh.HOSTILE_HP_LINK_STEP_KIND_HIT:
            row["damage_wire"] = decoded["damage_wire"]
            row["flags"] = decoded["flags"]
            row["number_floats_at"] = [
                round(value, 4) for value in decoded["position"]
            ]
        else:
            npc = decoded["attrs"][hh.NPC_ATTR_ID]
            row["hp_current"] = npc["fields"].get(hh.BASIC_BIT_CURRENT_HP)
            row["hp_max"] = npc["fields"].get(hh.BASIC_BIT_MAX_HP)
            row["carries_death_timer"] = bool(
                npc["basic_mask"] & hh.BASIC_BIT_DEATH_TIMER)
            movement = decoded["attrs"].get(hh.MOVEMENT_ATTR_ID)
            if movement is not None:
                row["actor_placed_at"] = [
                    round(value, 4) for value in movement["position"]
                ]
                row["heading"] = round(movement["heading"], 6)
        rows.append(row)
    return rows


def _drive_the_refusals(legacy, target, unlock, scenario):
    """Call every refusal this lane owns and report the NAME of each."""
    seen = []

    def _expect(name, call):
        try:
            call()
        except hh.HostileHpLinkValidationError as exc:
            seen.append({"expected": name, "raised": str(exc)[:120]})
            return str(exc).startswith(name)
        seen.append({"expected": name, "raised": None})
        return False

    world_row = (
        hh.HOSTILE_HP_LINK_TARGET_WORLD_X,
        hh.HOSTILE_HP_LINK_TARGET_WORLD_Y,
        hh.HOSTILE_HP_LINK_TARGET_WORLD_Z,
    )
    offsets = (
        hh.HOSTILE_HP_LINK_TARGET_DX,
        hh.HOSTILE_HP_LINK_TARGET_DY,
        hh.HOSTILE_HP_LINK_TARGET_DZ,
    )
    standing_on_the_row = tuple(
        row - offset for row, offset in zip(world_row, offsets))
    ok = [
        _expect(
            "missing_or_forged_wire_unlock",
            lambda: hh.encode_hostile_hp_link_npc_attr(
                legacy, target, "TARGET_SPAWN", 3857, None, None),
        ),
        _expect(
            "lethal_field_is_not_available_in_this_lane",
            lambda: hh.encode_hostile_hp_link_npc_attr(
                legacy, target, "TARGET_SPAWN", 3857, 20.0, unlock),
        ),
        _expect(
            "lethal_field_is_not_available_in_this_lane",
            lambda: hh.encode_hostile_hp_link_npc_attr(
                legacy, target, "TARGET_SPAWN", 0, None, unlock),
        ),
        _expect(
            "hp_clamp_is_forbidden_in_this_lane",
            lambda: hh.apply_hit_to_balance(100, -100, 0x0001),
        ),
        _expect(
            "target_placement_is_the_frozen_world_row_not_player_relative",
            lambda: hh.resolve_hostile_hp_link_target(
                legacy, standing_on_the_row, scenario),
        ),
        _expect(
            "npc_target_identity_not_pinned",
            lambda: hh.encode_hostile_hp_link_hit_entry(
                legacy, 0x2001, -964,
                (target.x, target.y, target.z), 0.0, 0x0001, unlock),
        ),
        _expect(
            "position_not_from_the_pinned_source",
            lambda: hh.resolve_hostile_hp_link_target(
                legacy, (1.0, 2.0, float("nan")), scenario),
        ),
        _expect(
            "scenario_object_exceeds_allowlist",
            lambda: hh.hostile_hp_link_wire_unlock("not the profile"),
        ),
    ]
    return all(ok), seen


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--player-position", default=None,
        help="x,y,z the player is standing at; default = the frozen V135 "
             "spawn the byte pins were cut at",
    )
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--evidence", default=None)
    args = parser.parse_args(argv)

    legacy = load_legacy(LEGACY_PATH)
    scenario = hh.load_hostile_hp_link_hypothesis_scenario(SCENARIO_PATH)
    unlock = hh.hostile_hp_link_wire_unlock(scenario)
    if args.player_position:
        parts = [value.strip() for value in args.player_position.split(",")]
        if len(parts) != 3:
            parser.error("--player-position wants exactly x,y,z")
        position = tuple(float(value) for value in parts)
    else:
        position = hh.hostile_hp_link_probe_player_position(legacy)

    saved = _install_socket_trap()
    try:
        target = hh.resolve_hostile_hp_link_target(legacy, position, scenario)
        actions = hh.build_hostile_hp_link_sweep(
            legacy, target,
            hh.HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
            hh.HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
            unlock, scenario,
        )
        rows = hh.validate_hostile_hp_link_sweep(actions)
        frames = _frame_rows(actions)
        refusals_held, refusals = _drive_the_refusals(
            legacy, target, unlock, scenario)
    finally:
        _restore_socket(saved)

    ladder = [
        row["hp_current"] for row in rows
        if row["kind"] == hh.HOSTILE_HP_LINK_STEP_KIND_ACTOR
    ]
    placed = [
        frame["actor_placed_at"] for frame in frames
        if "actor_placed_at" in frame
    ]
    checks = {
        "seven_frames": len(actions) == len(hh.HOSTILE_HP_LINK_STEP_ORDER),
        "ladder_is_the_pinned_one": (
            tuple(ladder) == (3857, 2893, 2893, 771)),
        "no_frame_carries_a_death_timer": not any(
            frame.get("carries_death_timer") for frame in frames),
        "the_actor_is_placed_exactly_once": len(placed) == 1,
        # Compared at f32 resolution, because that is what the wire carries:
        # a player standing at -8553.947 is placed at -8453.9473 and not at
        # -8453.947, and a check that missed that would cry wolf on every
        # live position it was ever run with.
        "the_placement_is_player_relative": bool(placed) and placed[0] == [
            round(_as_f32(position[index] + offset), 4)
            for index, offset in enumerate((
                hh.HOSTILE_HP_LINK_TARGET_DX,
                hh.HOSTILE_HP_LINK_TARGET_DY,
                hh.HOSTILE_HP_LINK_TARGET_DZ,
            ))
        ],
        "every_refusal_is_named": refusals_held,
    }
    verdict = {
        "tool": Path(__file__).name,
        "hypothesis_id": hh.HOSTILE_HP_LINK_HYPOTHESIS_ID,
        "milestone": hh.HOSTILE_HP_LINK_CHECKPOINT,
        "player_position": [round(value, 4) for value in position],
        "probe_geometry": target.probe_geometry,
        "target": {
            "identity": "0x%04X" % target.actor_identity,
            "name": target.source_name,
            "visual_preset": target.visual_preset,
            "max_hp": target.max_hp,
            "placed_at": [
                round(value, 4) for value in (target.x, target.y, target.z)
            ],
            "frozen_world_row_never_sent": [
                hh.HOSTILE_HP_LINK_TARGET_WORLD_X,
                hh.HOSTILE_HP_LINK_TARGET_WORLD_Y,
                hh.HOSTILE_HP_LINK_TARGET_WORLD_Z,
            ],
        },
        "frames": frames,
        "refusals": refusals,
        "checks": checks,
        "result": "PASS" if all(checks.values()) else "FAIL",
        "not_claimed": [
            "one client was shown this profile once, in the attended round "
            "GT-035 of 2026-08-25; nothing else has, and nothing here "
            "re-derives what that client did with the bytes",
            "nothing here re-derives what a client draws; the 2026-08-25 "
            "round saw this offset drawn, and the draw distance limit "
            "is unmeasured",
            "the hp baseline 3857 is client-side data, not a server rule",
            "no claim about death, loot, aggro or any other hostile",
        ],
    }
    text = json.dumps(verdict, indent=2, ensure_ascii=True)
    if args.evidence:
        Path(args.evidence).write_text(text + "\n", encoding="utf-8")
    if args.json:
        print(text)
    else:
        print("HOSTILE_HP_LINK_HEADLESS_REPLAY %s" % verdict["result"])
        print("  player at        %s" % (verdict["player_position"],))
        print("  target placed at %s  (%s %s)" % (
            verdict["target"]["placed_at"], verdict["target"]["identity"],
            verdict["target"]["name"]))
        print("  ladder           %s of %d" % (ladder, target.max_hp))
        for frame in frames:
            print("  %-24s %4d B  %s" % (
                frame["step"], frame["frame_size"],
                frame.get("actor_placed_at",
                          frame.get("number_floats_at", ""))))
        for name, held in checks.items():
            print("  [%s] %s" % ("ok" if held else "FAILED", name))
    return 0 if verdict["result"] == "PASS" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
