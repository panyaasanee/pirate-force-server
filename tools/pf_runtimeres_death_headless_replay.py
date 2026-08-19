#!/usr/bin/env python3
"""RUNTIMERES-DISPATCH-001 / RUNTIMERES-LATCHONLY-001: headless wire proof for
BOTH named profiles of HYP-PF-023.

WHAT THIS PROVES, and it is a wire-layer claim only
---------------------------------------------------
That a real ``make_state_class`` dispatcher, booted with one of the two opt-in
scenario files this lane ships and a throwaway database, answers ONE accepted
client frame with the exact ``GSCN_RunTimeProtocolRes`` id ``0x6E9D`` sweep the
named profile declares, and that those frames are

  (a) **byte-for-byte** the frames ``build_runtimeres_death_sweep`` composes --
      same labels, same PCs, same framed bytes, same delays, compared with
      ``==`` on the bytes objects, not by hash summary alone; and
  (b) independently readable, by a tag walker written in THIS file that does
      not import the encoder's decoder, as the sweep the round-85 static RE
      says can (or, for the two-frame profile, deliberately CANNOT) reach
      ``L"_F_DIE_000"``.

``--profile spawn_then_kill`` (the default, and the only thing the gate job
runs, because it runs this tool with no arguments at all) is the three-frame
sweep:

    frame 1  SPAWN        identity I, HP  > 0, no BasicAttr bit 0x0080
    frame 2  DYING_LATCH  identity I, HP == 0, timer  20.0f  > 0
    frame 3  DEATH_TASK   identity I, HP == 0, timer   0.0f <= 0

``--profile dying_latch_only`` is the same sweep with the third frame simply
never composed: SPAWN, then DYING_LATCH, then nothing.  All frames of either
profile carry the inherited change mask ``0x00`` and the derived change mask
bit ``0x02`` (the actor-entry collection at ``+0x1C``).

The polarity is inverted from intuition and is the point of the third frame:
``vt+0x40`` (0x43BDA0) is ``HP == 0 AND timer > 0`` and only latches
``[actor+0x70] |= 0x200``; ``vt+0x3C`` (0x43BD70) is ``HP == 0 AND timer <= 0``
and is what gates ``0x443990`` -> ``call 0x472810`` -> ``CActorTask_Dead``.

WHY THE TWO-FRAME PROFILE EXISTS AT ALL
---------------------------------------
The attended GT-022 session put a real corpse on a real client -- a body that
lay down and stayed down -- and that is a genuine result.  What it could not do
is say WHICH frame produced the pose.  The photographs were taken roughly a
second away from the t+6 / t+12 boundary between the DYING_LATCH frame and the
DEATH_TASK frame, and the capture latency of that photography was never
measured, so "the timestamp says t+7, therefore it was the latch frame" is an
argument about an unmeasured clock and not evidence.  Round 91's answer is to
delete the clock from the question entirely: run a sweep that STOPS after
DYING_LATCH, so the DEATH_TASK frame is not late, it is absent.  If a body
still lies down, the latch frame alone did it; if it does not, the latch frame
alone does not.  Neither branch needs anyone to know how long a screenshot
takes.

That experiment is only sound if the sole difference between the two runs is
the missing third frame, so this tool composes the three-frame sweep IN THIS
PROCESS (which needs no server, no socket and no database) and compares the
two dispatched frames against its first two with ``==`` on the raw bytes.  A
hash string that matched would be weaker: it would prove two digests agree,
which is what you check when you cannot hold both sides at once, and here we
can.

WHAT IT DOES NOT PROVE
----------------------
That any client does anything with these bytes.  **No client has ever been
shown one byte of the two-frame profile either** -- GT-022 saw the three-frame
one, and the two-frame variant is the TEST that would tell the two apart, not
the answer to it.  Nothing here decides which frame produced the pose GT-022
photographed; that decision needs an attended run of ``dying_latch_only`` on a
real client, and this file is not that run.  It does not prove that the dying
latch is a prerequisite for the death task (the two predicates are mutually
exclusive branches inside ``0x4437C0`` and the task gate does not read the
``0x200`` flag).  It does not narrow round 85's 229 unresolved vtable ``+0x20``
dispatch sites.  It claims nothing about the original server, about any damage
model, about persistence (nothing on this path has a write path), or about
production (``production_allowed`` is False everywhere it appears).

DISCIPLINE
----------
No server process, no socket, no network, no client, no GameClient window.  The
canonical database is never opened: everything runs on a fresh temporary SQLite
file that is deleted on exit.  No repository file is written unless
``--evidence <path>`` is handed in.  Pure stdlib.

The default is ``spawn_then_kill`` and it is load-bearing: every existing
caller, including the Windows gate job, invokes this tool with no arguments and
must keep getting today's run and today's guard set unchanged.  The two-frame
profile adds guards, it does not move or weaken one of them.

Usage:
    py -3 tools/pf_runtimeres_death_headless_replay.py
    py -3 tools/pf_runtimeres_death_headless_replay.py --json
    py -3 tools/pf_runtimeres_death_headless_replay.py --profile spawn_then_kill
    py -3 tools/pf_runtimeres_death_headless_replay.py --profile dying_latch_only
    py -3 tools/pf_runtimeres_death_headless_replay.py \
        --evidence reports/runtimeres_death001_headless.json

Exit 0 = every wire guard held.  Exit 1 = at least one drifted, with the list.
Exit 2 = the profile name on the command line is not one this lane ships.
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


# ---------------------------------------------------------------------------
# The two named profiles.  Same shape as tools/pf_hp_death002_headless_replay.py
# uses for HYP-PF-022, and for the same reason: the second profile of a lane is
# the SAME question one frame earlier or later, so it belongs in the tool that
# already knows how to ask it rather than in a copy of that tool that will drift
# away from it.
#
# SPAWN_THEN_KILL_PROFILE is the default and must stay the default.  Callers
# that pass no argument -- the Windows gate job among them -- get exactly the
# run they got before this file learned the word "profile".
# ---------------------------------------------------------------------------
SPAWN_THEN_KILL_PROFILE = "spawn_then_kill"
DYING_LATCH_ONLY_PROFILE = "dying_latch_only"
SCENARIO = ROOT / "scenarios" / "runtimeres_death_hypothesis_spawn_then_kill.json"
LATCH_ONLY_SCENARIO = (
    ROOT / "scenarios" / "runtimeres_death_hypothesis_dying_latch_only.json"
)
SCENARIO_BY_PROFILE = {
    SPAWN_THEN_KILL_PROFILE: SCENARIO,
    DYING_LATCH_ONLY_PROFILE: LATCH_ONLY_SCENARIO,
}
DEFAULT_PROFILE = SPAWN_THEN_KILL_PROFILE
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
# The dispatcher names the profile it sent (round 91), so the event this tool
# waits for is composed the same way the dispatcher composes it.  The
# three-frame profile's string is therefore unchanged and still
# "runtimeres_death_hypothesis_spawn_then_kill_sent"; SWEEP_EVENT is kept as
# that literal because it is the name the ledger and the dispatch tests pin,
# and section 1 checks the composed name against it for the default profile.
SWEEP_EVENT = "runtimeres_death_hypothesis_spawn_then_kill_sent"
REPEAT_EVENT = "runtimeres_death_hypothesis_already_sent_no_reply"
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


# ---------------------------------------------------------------------------
# What the dying_latch_only profile is REQUIRED to be, written out here as
# literals rather than read off the profile object.  A guard that asks the
# profile what it expects and then checks the profile against its own answer
# is a restatement, not a check; these five lines are the tool's independent
# opinion of what round 91 pinned, and section 4b measures the dispatcher
# against THEM.
# ---------------------------------------------------------------------------
LATCH_ONLY_ACTION_LABELS = (
    "HYP_PF_023_RUNTIMERES_DEATH_SPAWN",
    "HYP_PF_023_RUNTIMERES_DEATH_DYING_LATCH",
)
LATCH_ONLY_DELAYS_SECONDS = (0.0, 6.0)
LATCH_ONLY_TIMER_SECONDS = 20.0
LATCH_ONLY_FRAME_COUNT = 2
# Only used to keep the printed guard labels reading like English at either
# length.  Nothing depends on it.
FRAME_COUNT_WORD = {1: "one", 2: "two", 3: "three", 4: "four"}


def main() -> int:
    want_json = "--json" in sys.argv
    evidence_path = None
    if "--evidence" in sys.argv:
        evidence_path = Path(sys.argv[sys.argv.index("--evidence") + 1])
    # --profile, copied from tools/pf_hp_death002_headless_replay.py so the two
    # death lanes are driven the same way.  Absent means the default, which is
    # the three-frame sweep and everything that has ever run this tool.
    profile_name = DEFAULT_PROFILE
    if "--profile" in sys.argv:
        at = sys.argv.index("--profile") + 1
        profile_name = sys.argv[at] if at < len(sys.argv) else ""
    if profile_name not in SCENARIO_BY_PROFILE:
        print("unknown profile %r; pick one of %s"
              % (profile_name, sorted(SCENARIO_BY_PROFILE)))
        return 2
    scenario_path = SCENARIO_BY_PROFILE[profile_name]

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
    scenario = rdh.load_runtimeres_death_hypothesis_scenario(scenario_path)
    pinned = json.loads(scenario_path.read_text(encoding="utf-8"))
    # The loader picks the profile the FILE names.  If that is not the profile
    # the command line asked for, the run is meaningless and no guard result
    # would mean anything either, so this is a hard stop and not a red guard.
    if scenario.profile_name != profile_name:
        print("scenario %s names profile %r, not the requested %r"
              % (scenario_path.name, scenario.profile_name, profile_name))
        return 2
    latch_only = not scenario.ends_on_death_task
    # Everything below that used to be a three-frame literal now comes off the
    # loaded profile: the step order, the labels, the frame count, the delays
    # and the dispatcher event name.  The dispatcher composes the event the
    # same way (runtime.py, round 91), so a rename on either side turns this
    # tool red instead of leaving it waiting for a string nobody sends.
    step_order = scenario.step_order
    expected_labels = [
        scenario.action_label_prefix + label for label in step_order
    ]
    sweep_event = (
        "runtimeres_death_hypothesis_" + scenario.profile_name + "_sent"
    )
    frame_word = FRAME_COUNT_WORD.get(len(step_order), str(len(step_order)))

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

    # And, when the two-frame profile is the one under test, the OTHER
    # profile's sweep as well.  Composing it costs nothing -- no server, no
    # socket, no database, just the frozen v141 encoder and the same probe --
    # and it is the only way to say the thing the experiment actually rests on:
    # that the two runs differ by the absent third frame and by NOTHING else.
    # If frame 1 or frame 2 drifted by a single byte between the profiles, then
    # an attended run of dying_latch_only would be testing a different sweep
    # and could not be compared against GT-022's three-frame run at all.
    three_frame = None
    if latch_only:
        three_frame_profile = rdh.load_runtimeres_death_hypothesis_scenario(
            SCENARIO_BY_PROFILE[SPAWN_THEN_KILL_PROFILE]
        )
        three_frame = rdh.build_runtimeres_death_sweep(
            legacy, probe,
            rdh.runtimeres_death_lethal_unlock(three_frame_profile),
            three_frame_profile,
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
            print("-- 1. one accepted client frame in, %s frames out --"
                  % frame_word)
        state = boot("runtimeres_death001")
        db_before = hashlib.sha256(db_path.read_bytes()).hexdigest().upper()
        actions = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("the dispatcher answered with %s frames" % frame_word,
              len(actions) == len(step_order),
              str(len(actions)))
        check("in the scenario's pinned order",
              [row[0] for row in actions] == expected_labels)
        check("and named the sweep event exactly once",
              state.events.count(sweep_event) == 1
              and (latch_only or sweep_event == SWEEP_EVENT))
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
        for index, label in enumerate(step_order):
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
            step = step_order[index]
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
            # The header names the profile so an attended tester reading a
            # pasted log can tell the two runs apart at a glance.  For
            # spawn_then_kill this reproduces the pre-round-91 line verbatim.
            print("-- 4. %s, and the inverted polarity --"
                  % scenario.profile_name.replace("_", "-"))
        check("all %s frames name ONE identity" % frame_word,
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
        if scenario.ends_on_death_task:
            check("frames 2 and 3 both carry current HP == 0",
                  all(row["hp_current_bit_0x0004"] == 0 for row in rows[1:]))
        else:
            check("frame 2 carries current HP == 0",
                  all(row["hp_current_bit_0x0004"] == 0 for row in rows[1:]))
        check("frame 2 satisfies vt+0x40 (timer > 0) and NOT vt+0x3C",
              rows[1]["dying_latch_predicate_vt40"] is True
              and rows[1]["death_task_predicate_vt3c"] is False)
        check("frame 2 carries the pinned dying-latch timer %.1f"
              % rdh.DYING_LATCH_TIMER_SECONDS,
              rows[1]["death_timer_bit_0x0080"]
              == rdh.DYING_LATCH_TIMER_SECONDS)
        if scenario.ends_on_death_task:
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
              == [scenario.first_delay_seconds]
              + [scenario.spacing_seconds] * (len(rows) - 1))

        prefix_is_identical = None
        if latch_only:
            if not want_json:
                print("-- 4b. dying_latch_only: the frame that is NOT sent --")
            # Everything in this section is a CHECK, not a restatement.  The
            # expected labels, delays, frame count and timer above are this
            # file's own literals; the three-frame sweep below is composed by
            # the encoder in this process; and the negative -- that no frame
            # here opens the task gate -- is measured by the walker on the
            # dispatched bytes, not asserted from the profile's own promise.
            check("the dispatcher returned EXACTLY two actions",
                  len(actions) == LATCH_ONLY_FRAME_COUNT, str(len(actions)))
            check("with the two pinned action labels, in order",
                  tuple(row[0] for row in actions) == LATCH_ONLY_ACTION_LABELS,
                  str([row[0] for row in actions]))
            check("with the pinned delays 0.0 then 6.0",
                  tuple(row[3] for row in actions) == LATCH_ONLY_DELAYS_SECONDS,
                  str([row[3] for row in actions]))
            check("frame 1, re-read: HP > 0 (the probe is alive on the wire)",
                  rows[0]["hp_current_bit_0x0004"] > 0,
                  str(rows[0]["hp_current_bit_0x0004"]))
            check("frame 1, re-read: NO BasicAttr bit 0x0080 in mask or body",
                  not rows[0]["basic_mask"] & BIT_DEATH_TIMER
                  and rows[0]["death_timer_bit_0x0080"] is None,
                  hex(rows[0]["basic_mask"] or 0))
            check("frame 2, re-read: the SAME identity as frame 1",
                  rows[1]["identity"] == rows[0]["identity"],
                  "%s vs %s" % (hex(rows[1]["identity"]),
                                hex(rows[0]["identity"])))
            check("frame 2, re-read: HP == 0",
                  rows[1]["hp_current_bit_0x0004"] == 0,
                  str(rows[1]["hp_current_bit_0x0004"]))
            check("frame 2, re-read: BasicAttr bit 0x0080 set, timer 20.0f",
                  bool(rows[1]["basic_mask"] & BIT_DEATH_TIMER)
                  and rows[1]["death_timer_bit_0x0080"]
                  == LATCH_ONLY_TIMER_SECONDS
                  and LATCH_ONLY_TIMER_SECONDS == rdh.DYING_LATCH_TIMER_SECONDS,
                  repr(rows[1]["death_timer_bit_0x0080"]))
            # THE load-bearing negative of the whole experiment.  If any frame
            # of this profile satisfied vt+0x3C then an attended run could not
            # tell the two profiles apart and the round would prove nothing.
            check("NO frame in this sweep satisfies the death-task predicate "
                  "vt+0x3C (hp == 0 AND timer <= 0)",
                  not any(row["death_task_predicate_vt3c"] for row in rows),
                  str([row["step"] for row in rows
                       if row["death_task_predicate_vt3c"]]))
            check("the LAST frame satisfies the dying-latch predicate vt+0x40 "
                  "(hp == 0 AND timer > 0)",
                  rows[-1]["dying_latch_predicate_vt40"] is True,
                  rows[-1]["step"])
            check("the encoder composed three actions for the other profile",
                  len(three_frame) == 3, str(len(three_frame)))
            check("dispatched frame 1 PC bytes == three-frame frame 1 PC bytes",
                  actions[0][1] == three_frame[0][1])
            check("dispatched frame 1 framed bytes == three-frame frame 1's",
                  actions[0][2] == three_frame[0][2])
            check("dispatched frame 2 PC bytes == three-frame frame 2 PC bytes",
                  actions[1][1] == three_frame[1][1])
            check("dispatched frame 2 framed bytes == three-frame frame 2's",
                  actions[1][2] == three_frame[1][2])
            check("their labels and delays agree too",
                  [(row[0], row[3]) for row in actions]
                  == [(row[0], row[3]) for row in three_frame[:2]])
            prefix_is_identical = (
                list(actions) == list(three_frame[:LATCH_ONLY_FRAME_COUNT])
            )
            check("so the whole dispatched sweep IS the three-frame sweep's "
                  "first two actions, compared with == and not by hash",
                  prefix_is_identical)
            check("and not one byte of the third frame appears in this run",
                  three_frame[2][0] not in {row[0] for row in actions}
                  and three_frame[2][1] not in {row[1] for row in actions}
                  and three_frame[2][2] not in {row[2] for row in actions})

        if not want_json:
            print("-- 5. one-shot, fail-closed, containment --")
        again = state.dispatch(
            legacy.parse_outer(CHAT_INPUT_PROBE_REQUEST_PCS["probe1"])
        )
        check("a second trigger emits nothing (the sweep is one-shot)",
              again == [])
        check("and says so with a named event",
              state.events.count(REPEAT_EVENT) == 1)
        if latch_only:
            # The one-shot guard above says the repeat produced no actions.
            # This one says the refusal did not ALSO re-announce the sweep: an
            # attended tester reading the event log has to be able to count
            # sends by counting that one string, and a second copy of it would
            # make the log lie about how many latch frames left the process.
            check("the refused repeat produced no bytes and no second sweep "
                  "event",
                  again == []
                  and state.events.count(sweep_event) == 1
                  and state.events.count(REPEAT_EVENT) == 1,
                  str(state.events.count(sweep_event)))
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
              sweep_event not in off.events)

    verdict = {
        "milestone": (
            "RUNTIMERES-LATCHONLY-001" if latch_only
            else "RUNTIMERES-DISPATCH-001"
        ),
        "profile": scenario.profile_name,
        "hypothesis_id": rdh.RUNTIMERES_DEATH_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "scenario": scenario_path.relative_to(ROOT).as_posix(),
        "layer": "wire_only_no_client_no_socket_no_server_process",
        "guards_run": guards,
        "failures": failures,
        "result": "PASS" if not failures else "FAIL",
        "dispatch": {
            "trigger": "one accepted 34-byte ascii12 chat-input frame",
            "frames_per_accepted_request": len(actions),
            "sweep_event": sweep_event,
            "one_shot": True,
            "socket_action": "none",
            "database_write": "none",
        },
        "polarity": {
            "dying_latch_predicate_vt40": rdh.DYING_LATCH_PREDICATE_VA,
            "dying_latch_rule": "hp == 0 AND timer > 0.0f",
            "death_task_predicate_vt3c": rdh.DEATH_TASK_PREDICATE_VA,
            "death_task_rule": "hp == 0 AND timer <= 0.0f",
            "any_frame_opens_the_task_gate": any(
                row["death_task_predicate_vt3c"] for row in rows
            ),
        },
        "not_claimed": list(
            rdh.RUNTIMERES_DEATH_LATCH_ONLY_NONCLAIMS if latch_only
            else rdh.RUNTIMERES_DEATH_NONCLAIMS
        ),
        "frames": rows,
    }
    if latch_only:
        verdict["byte_prefix_of_spawn_then_kill"] = {
            "compared": "raw bytes with ==, both sweeps composed in this "
                        "process, no hash string relied on",
            "first_two_actions_identical": prefix_is_identical,
            "third_frame_step": rdh.DEATH_TASK_STEP_LABEL,
            "third_frame_pc_sha256": hashlib.sha256(
                three_frame[2][1]
            ).hexdigest().upper(),
            "third_frame_was_dispatched": False,
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
        elif latch_only:
            print("RESULT: PASS - the real dispatcher emits the encoder's "
                  "dying-latch-only sweep byte for byte, NO frame in it "
                  "opens the death-task gate, and its two frames are the "
                  "three-frame sweep's first two byte for byte (client "
                  "layer = GT-022, not run, and no client has ever been "
                  "shown this profile)")
        else:
            print("RESULT: PASS - the real dispatcher emits the encoder's "
                  "spawn-then-kill sweep byte for byte (client layer = "
                  "GT-022, not run)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
