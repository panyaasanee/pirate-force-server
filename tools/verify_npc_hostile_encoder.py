#!/usr/bin/env python3
"""NPC-HOSTILE-001: offline verifier for HYP-PF-027.

WHAT THIS PROVES, and where the proof stops
-------------------------------------------
That the hostile-presentation lane composes EXACTLY the one designed frame --
the HYP-PF-023 SPAWN body for the frozen probe NPC 0x2001 plus a five-byte
BasicAttr faction splice (bit 0x0400, u32 value 6) -- and refuses, by name and
with no bytes, every way of holding it wrong that this file can drive.  The
strongest guard is section C, CROSS-LANE BYTE EQUALITY: the parent lane's own
composer (its module, its profile object) recomposes its SPAWN frame, and this
lane's frame must equal that frame with the splice at the computed offset and
a mask that differs by exactly one bit.  This lane can therefore drift from
its parent only by turning two verifiers red at once.

It proves NOTHING about a client.  No client has ever been shown one byte of
this profile; whether NPC 0x2001 presents as hostile is GT-032, attended, not
run.  The faction values (player 1, NPC 6) are OUR composition -- the exact
pair a real client rendered as hostile in SCENE-005 -- and the original
server's faction assignment is unknown and unrecoverable.

DISCIPLINE
----------
Pure stdlib.  No server process, no socket, no database, no client, no
GameClient window, no repository write.  Tools are allowed to import
neighbouring lanes; section C does, deliberately.  Sections A/B/D re-derive
everything they check rather than asking the module what to expect.

Usage:
    py -3 tools/verify_npc_hostile_encoder.py

Exit 0 = every guard held.  Exit 1 = at least one drifted, with the list.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import npc_hostile_hypothesis as nhm  # noqa: E402
# The parent lane, imported ON PURPOSE: section C composes its SPAWN through
# its own composer and diffs bytes.  Tools may import both lanes; the src
# modules themselves never import each other.
from pirateforce_foundation import runtimeres_death_hypothesis as parent  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_basic_faction,
    make_actor_attr_with_name,
)

SCENARIO = ROOT / "scenarios" / "npc_hostile_hypothesis_faction_pairing.json"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# ---------------------------------------------------------------------------
# This reader's own constants, written as literals so section A can measure
# the module against THEM.
# ---------------------------------------------------------------------------
RUNTIME_PROTOCOL_RES_ID = 0x6E9D
DERIVED_MASK_ACTOR_ENTRIES = 0x02
NPC_ACTOR_TYPE = 4
NPC_ATTR_ID = 0x0AD5
MOVEMENT_ATTR_ID = 0x2067
PARENT_SPAWN_MASK = 0x030C
FACTION_BIT = 0x0400
HOSTILE_MASK = 0x070C
FACTION_TAG = 0x14
NPC_FACTION_VALUE = 6
PLAYER_PAIR_FACTION = 1
PLAYER_IDENTITY_LO = 0x10010001
PLAYER_IDENTITY_HI = 0
PLAYER_FACTION_DELTA = 5
PROBE_IDENTITY = 0x2001
PROBE_TEMPLATE = 1
PROBE_PRESET = "P_MALE_002_000_SP1"
RELATION_LOOKUP = 0x4A1D50
STEP_LABEL = "HOSTILE_SPAWN"
ACTION_LABEL = "HYP_PF_027_NPC_HOSTILE_HOSTILE_SPAWN"
PIN_PC_SIZE = 178
PIN_PC_SHA = "A85DD9F7C11D5F7B5C7779E0C9B0C5032459458A103B5282D42CDDEB8C7FC21B"
PIN_FRAME_SIZE = 190
PIN_FRAME_SHA = "BB2B59486989C69B083436AC694A4085594ED4A386C4144AB227C7616C6D5983"
MASK_OFFSET_IN_ATTR = 12
FACTION_INSERT_IN_ATTR = 36

failures: list[str] = []
guards = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global guards
    guards += 1
    if condition:
        print("  PASS  %s" % label)
    else:
        failures.append(label)
        print("  FAIL  %s %s" % (label, detail))


def reject(label: str, thunk, needle: str) -> None:
    """The named-refusal driver: the call must raise and must say why."""
    global guards
    guards += 1
    try:
        thunk()
    except (ValueError, RuntimeError) as exc:
        if needle in str(exc):
            print("  PASS  %s" % label)
            return
        failures.append(label)
        print("  FAIL  %s raised the wrong refusal: %s" % (label, ascii(str(exc))))
        return
    failures.append(label)
    print("  FAIL  %s did not refuse at all" % label)


def main() -> int:
    legacy = load_legacy(LEGACY_PATH)
    scenario = nhm.load_npc_hostile_hypothesis_scenario(SCENARIO)
    pinned = json.loads(SCENARIO.read_text(encoding="utf-8"))
    probe = nhm.resolve_probe(legacy)
    wire = nhm.npc_hostile_wire_unlock(scenario)

    print("-- A. this reader's constants against the module's --")
    check("envelope id/mask agree", RUNTIME_PROTOCOL_RES_ID == nhm.RUNTIME_PROTOCOL_RES_ID
          and DERIVED_MASK_ACTOR_ENTRIES == nhm.DERIVED_CHANGE_MASK_ACTOR_ENTRIES)
    check("actor_type 4 (CNetNPC) and attr ids agree",
          NPC_ACTOR_TYPE == nhm.NPC_STYLE_ACTOR_TYPE
          and NPC_ATTR_ID == nhm.NPC_ATTR_ID
          and MOVEMENT_ATTR_ID == nhm.MOVEMENT_ATTR_ID)
    check("the mask algebra is one bit wide: 0x030C | 0x0400 == 0x070C",
          PARENT_SPAWN_MASK == nhm.HYP23_SPAWN_BASIC_MASK
          and FACTION_BIT == nhm.BASIC_BIT_FACTION
          and HOSTILE_MASK == nhm.NPC_HOSTILE_BASIC_MASK
          and PARENT_SPAWN_MASK | FACTION_BIT == HOSTILE_MASK
          and PARENT_SPAWN_MASK & FACTION_BIT == 0)
    check("the pinned pairing is player 1 / NPC 6, and both are ours",
          NPC_FACTION_VALUE == nhm.NPC_HOSTILE_NPC_FACTION_VALUE
          and PLAYER_PAIR_FACTION == nhm.NPC_HOSTILE_PLAYER_PAIR_FACTION)
    check("the pinned player identity is the canonical smoke 0x10010001/0",
          PLAYER_IDENTITY_LO == nhm.NPC_HOSTILE_PLAYER_IDENTITY_LO
          and PLAYER_IDENTITY_HI == nhm.NPC_HOSTILE_PLAYER_IDENTITY_HI)
    check("the relation lookup anchor agrees",
          RELATION_LOOKUP == nhm.RELATION_LOOKUP_VA
          and nhm.STATIC_ANCHORS["relation_lookup"] == RELATION_LOOKUP)
    check("the lane is HYP-PF-027 behind kwarg npc_hostile_hypothesis_scenario",
          nhm.NPC_HOSTILE_HYPOTHESIS_ID == "HYP-PF-027"
          and nhm.NPC_HOSTILE_DISPATCH_KWARG == "npc_hostile_hypothesis_scenario")
    check("production is not allowed, in the module and in the file",
          nhm.production_allowed is False
          and pinned["production_allowed"] is False
          and pinned["test_only"] is True and pinned["lethal"] is False)
    check("one step, first delay 0.0, spacing 15.0",
          nhm.NPC_HOSTILE_STEP_ORDER == (STEP_LABEL,)
          and nhm.NPC_HOSTILE_FIRST_DELAY_SECONDS == 0.0
          and nhm.NPC_HOSTILE_SPACING_SECONDS == 15.0
          and nhm.NPC_HOSTILE_ACTION_LABELS == (ACTION_LABEL,))
    check("the scenario file's per_step pins ARE the module's pins",
          pinned["probe"]["per_step"][STEP_LABEL]
          == nhm.NPC_HOSTILE_PINS[STEP_LABEL])
    check("the probe is the frozen placement 0 (0x2001, template 1)",
          probe.actor_identity == PROBE_IDENTITY
          and probe.template_id == PROBE_TEMPLATE
          and probe.visual_preset == PROBE_PRESET)

    print("-- B. the composition, recomputed and pinned three ways --")
    actions = nhm.build_npc_hostile_sweep(legacy, probe, wire, scenario)
    check("the sweep is exactly one action", len(actions) == 1)
    label, pc, frame, delay = actions[0]
    check("with the pinned label and delay",
          label == ACTION_LABEL and delay == 0.0)
    pc_sha = hashlib.sha256(pc).hexdigest().upper()
    frame_sha = hashlib.sha256(frame).hexdigest().upper()
    check("the PC recomputes to the pinned size and sha",
          len(pc) == PIN_PC_SIZE and pc_sha == PIN_PC_SHA,
          "%d %s" % (len(pc), pc_sha))
    check("the frame recomputes to the pinned size and sha",
          len(frame) == PIN_FRAME_SIZE and frame_sha == PIN_FRAME_SHA,
          "%d %s" % (len(frame), frame_sha))
    check("frame == frame_pc(pc)", frame == legacy.frame_pc(pc))
    check("the module pins the same numbers",
          nhm.NPC_HOSTILE_PINS[STEP_LABEL]["pc_size"] == len(pc)
          and nhm.NPC_HOSTILE_PINS[STEP_LABEL]["pc_sha256"] == pc_sha
          and nhm.NPC_HOSTILE_PINS[STEP_LABEL]["frame_size"] == len(frame)
          and nhm.NPC_HOSTILE_PINS[STEP_LABEL]["frame_sha256"] == frame_sha)
    scen_pin = pinned["probe"]["per_step"][STEP_LABEL]
    check("the scenario FILE pins the same numbers",
          scen_pin["pc_size"] == len(pc) and scen_pin["pc_sha256"] == pc_sha
          and scen_pin["frame_size"] == len(frame)
          and scen_pin["frame_sha256"] == frame_sha)
    read = nhm.decode_npc_hostile_actor_entry_frame(pc)
    npc = read["attrs"][NPC_ATTR_ID]
    check("the module's walker reads back type 4, 0x2001, mask 0x070C, faction 6",
          read["actor_type"] == NPC_ACTOR_TYPE
          and read["identity"] == PROBE_IDENTITY
          and npc["basic_mask"] == HOSTILE_MASK
          and npc["fields"][FACTION_BIT] == NPC_FACTION_VALUE)
    check("the spawn is alive at 100 and placed (MovementAttr present)",
          npc["fields"][nhm.BASIC_BIT_CURRENT_HP] == 100
          and MOVEMENT_ATTR_ID in read["attrs"])

    print("-- C. CROSS-LANE BYTE EQUALITY against the parent's own composer --")
    parent_probe = parent.resolve_probe(legacy)
    check("both lanes resolve the SAME frozen probe",
          (parent_probe.placement_index, parent_probe.template_id,
           parent_probe.actor_identity, parent_probe.visual_preset,
           parent_probe.x, parent_probe.y, parent_probe.z)
          == (probe.placement_index, probe.template_id, probe.actor_identity,
              probe.visual_preset, probe.x, probe.y, probe.z))
    parent_pc, parent_frame = parent.make_runtimeres_death_step_response(
        legacy, parent_probe, 0, None, parent._PROFILE,
    )
    check("the parent SPAWN recomputes to ITS OWN pins",
          len(parent_pc) == parent.RUNTIMERES_DEATH_PINS["SPAWN"]["pc_size"]
          and hashlib.sha256(parent_pc).hexdigest().upper()
          == parent.RUNTIMERES_DEATH_PINS["SPAWN"]["pc_sha256"])
    check("the parent spawn mask constant copied into this lane is honest",
          parent.RUNTIMERES_DEATH_PINS["SPAWN"]["basic_mask"]
          == PARENT_SPAWN_MASK)
    # The NPCAttr body starts at the same place in both PCs.  Locate it once,
    # in the parent, from the envelope layout both lanes pin.
    attr_start = 17 + 2 + 9 + 2 + 3   # entry list + type + identity + count + attr id tag
    check("both PCs open with the identical envelope and entry header",
          pc[:attr_start] == parent_pc[:attr_start])
    splice_at = attr_start + FACTION_INSERT_IN_ATTR
    mask_at = attr_start + MASK_OFFSET_IN_ATTR
    faction_wire = bytes(legacy.u32tag(FACTION_TAG, NPC_FACTION_VALUE))
    expected_pc = (
        parent_pc[:mask_at]
        + int(HOSTILE_MASK).to_bytes(2, "little")
        + parent_pc[mask_at + 2:splice_at]
        + faction_wire
        + parent_pc[splice_at:]
    )
    check("THE LANE'S FRAME IS THE PARENT'S SPAWN PLUS EXACTLY THE SPLICE",
          pc == expected_pc)
    check("the delta is exactly 5 bytes and exactly one mask bit",
          len(pc) == len(parent_pc) + 5
          and int.from_bytes(pc[mask_at:mask_at + 2], "little")
          ^ int.from_bytes(parent_pc[mask_at:mask_at + 2], "little")
          == FACTION_BIT)
    check("everything after the splice -- scene fields, NPC mask, template, "
          "preset, MovementAttr -- is byte-identical to the parent",
          pc[splice_at + 5:] == parent_pc[splice_at:])
    check("the five spliced bytes are the tagged u32 faction 6",
          pc[splice_at:splice_at + 5] == faction_wire
          and faction_wire == bytes([FACTION_TAG, 6, 0, 0, 0]))

    print("-- D. the refusal ladder --")
    reject("no unlock refuses by name",
           lambda: nhm.encode_hostile_npc_attr(legacy, probe, wire=None),
           "missing_or_forged_wire_unlock")
    forged = nhm.NpcHostileWireUnlock(
        nhm.NPC_HOSTILE_SCENARIO_ID, nhm.NPC_HOSTILE_HYPOTHESIS_ID,
    )
    reject("a value-equal FORGED unlock is refused (identity, not ==)",
           lambda: nhm.encode_hostile_npc_attr(legacy, probe, wire=forged),
           "missing_or_forged_wire_unlock")
    reject("build_npc_hostile_sweep refuses the forged unlock",
           lambda: nhm.build_npc_hostile_sweep(legacy, probe, forged, scenario),
           "missing_or_forged_wire_unlock")
    reject("faction 1 on the NPC side refuses by name (1 is the PLAYER half)",
           lambda: nhm.encode_hostile_npc_attr(
               legacy, probe, faction=1, wire=wire),
           "faction_value_not_pinned")
    reject("faction 0 refuses by name",
           lambda: nhm.encode_hostile_npc_attr(
               legacy, probe, faction=0, wire=wire),
           "faction_value_not_pinned")
    reject("a zero-HP hostile spawn refuses by name",
           lambda: nhm.encode_hostile_npc_attr(
               legacy, probe, current_hp=0, wire=wire),
           "refuses_zero_hp")
    reject("a bare tuple is not a probe",
           lambda: nhm.encode_hostile_npc_attr(
               legacy, (0, 1, 0x2001), wire=wire),
           "typed probe object")

    def _lookalike():
        look = nhm.NpcHostileHypothesisScenario(
            nhm.NPC_HOSTILE_SCENARIO_ID, nhm.NPC_HOSTILE_HYPOTHESIS_ID,
            nhm.NPC_HOSTILE_STEP_ORDER, 15.0, 0.0,
            nhm.NPC_HOSTILE_ACTION_LABEL_PREFIX, 7, 1,
        )
        return nhm.require_npc_hostile_hypothesis_scenario(look)
    reject("a lookalike scenario dataclass with faction 7 is refused",
           _lookalike, "exceeds the allowlist")

    base = json.loads(SCENARIO.read_text(encoding="utf-8"))
    def _mutant(mutate):
        data = copy.deepcopy(base)
        mutate(data)
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        try:
            return lambda: nhm.load_npc_hostile_hypothesis_scenario(path)
        finally:
            pass
    reject("a scenario file with production_allowed true is refused",
           _mutant(lambda d: d.update(production_allowed=True)),
           "exceeds the exact allowlist")
    reject("a scenario file with an extra key anywhere is refused",
           _mutant(lambda d: d["wire"].update(extra=1)),
           "exceeds the exact allowlist")
    reject("a scenario file with a different NPC faction is refused",
           _mutant(lambda d: d["wire"]["relation"].update(npc_side_value=1)),
           "exceeds the exact allowlist")
    reject("a scenario file with a different player faction is refused",
           _mutant(lambda d: d["entry"]["player_start_game"].update(
               basic_faction=6)),
           "exceeds the exact allowlist")
    reject("a scenario file missing the pairing requirement is refused",
           _mutant(lambda d: d["dispatch"].pop(
               "requires_player_faction_start_game")),
           "exceeds the exact allowlist")
    reject("a scenario file with tampered pins is refused",
           _mutant(lambda d: d["probe"]["per_step"][STEP_LABEL].update(
               pc_sha256="00" * 32)),
           "exceeds the exact allowlist")
    reject("a file that is not JSON at all is refused",
           lambda: nhm.load_npc_hostile_hypothesis_scenario(LEGACY_PATH),
           "invalid npc hostile hypothesis scenario")

    print("-- D2. validator traps: hand-built wrong sweeps must refuse --")
    def _validate(actions_):
        return nhm.validate_npc_hostile_sweep(actions_, scenario)
    reject("an empty sweep is refused",
           lambda: _validate([]), "exactly 1 frame")
    reject("a two-frame sweep is refused",
           lambda: _validate([actions[0], actions[0]]), "exactly 1 frame")
    reject("a wrong label is refused",
           lambda: _validate([("HYP_PF_027_NPC_HOSTILE_WRONG", pc, frame, 0.0)]),
           "labelled")
    # Flip the mask WITHOUT the faction field: the walker must catch the
    # missing bytes, not just the mask.
    mask_at_local = 17 + 2 + 9 + 2 + 3 + MASK_OFFSET_IN_ATTR
    bad_mask_pc = (
        pc[:mask_at_local]
        + int(PARENT_SPAWN_MASK).to_bytes(2, "little")
        + pc[mask_at_local + 2:]
    )
    reject("a frame whose mask lost the faction bit is refused",
           lambda: _validate([(ACTION_LABEL, bad_mask_pc,
                               legacy.frame_pc(bad_mask_pc), 0.0)]),
           "not exactly the HYP-PF-023 spawn mask")
    # Widen the mask by one extra bit (0x0002, level): strict equality must
    # refuse it before any field walk.
    wide_mask_pc = (
        pc[:mask_at_local]
        + int(HOSTILE_MASK | 0x0002).to_bytes(2, "little")
        + pc[mask_at_local + 2:]
    )
    reject("a frame whose mask carries ANY extra bit is refused",
           lambda: _validate([(ACTION_LABEL, wide_mask_pc,
                               legacy.frame_pc(wide_mask_pc), 0.0)]),
           "not exactly the HYP-PF-023 spawn mask")
    # Patch the faction value to 1 on the wire: the pinned-value check must
    # catch bytes, not just the composer argument.
    splice_local = 17 + 2 + 9 + 2 + 3 + FACTION_INSERT_IN_ATTR
    patched = bytearray(pc)
    patched[splice_local + 1:splice_local + 5] = (1).to_bytes(4, "little")
    reject("a frame whose wire faction is not 6 is refused",
           lambda: _validate([(ACTION_LABEL, bytes(patched),
                               legacy.frame_pc(bytes(patched)), 0.0)]),
           "not the pinned 6")

    print("-- E. the entry half: the frozen player faction serializer --")
    plain = make_actor_attr_with_name(
        legacy, PLAYER_IDENTITY_LO, PLAYER_IDENTITY_HI, 1, 0, "SmokeName",
    )
    paired = make_actor_attr_with_basic_faction(
        legacy, PLAYER_IDENTITY_LO, PLAYER_IDENTITY_HI, 1, 0, "SmokeName",
        PLAYER_PAIR_FACTION,
    )
    check("the faction-1 ActorAttr is the production one plus EXACTLY 5 bytes",
          len(paired) == len(plain) + PLAYER_FACTION_DELTA
          and PLAYER_FACTION_DELTA
          == nhm.NPC_HOSTILE_PLAYER_FACTION_WIRE_DELTA)
    check("and the five bytes are the tagged u32 faction 1",
          bytes([FACTION_TAG, 1, 0, 0, 0]) in bytes(paired)
          and bytes([FACTION_TAG, 1, 0, 0, 0]) not in bytes(plain))
    reject("the frozen serializer refuses any faction but 1",
           lambda: make_actor_attr_with_basic_faction(
               legacy, PLAYER_IDENTITY_LO, PLAYER_IDENTITY_HI, 1, 0, "X", 6),
           "faction-1 probe")
    reject("the frozen serializer refuses a non-zero scene_seq",
           lambda: make_actor_attr_with_basic_faction(
               legacy, PLAYER_IDENTITY_LO, PLAYER_IDENTITY_HI, 1, 7, "X", 1),
           "faction-1 probe")
    reject("the frozen serializer refuses scene ids outside (1, 2)",
           lambda: make_actor_attr_with_basic_faction(
               legacy, PLAYER_IDENTITY_LO, PLAYER_IDENTITY_HI, 3, 0, "X", 1),
           "faction-1 probe")

    print("-- F. containment --")
    module_name = "npc_hostile_hypothesis"
    importers = sorted(
        path.name for path in SRC_ROOT.glob("*.py")
        if module_name in path.read_text(encoding="utf-8")
        and path.name != module_name + ".py"
    )
    check("only app.py and runtime.py reference the module",
          importers == ["app.py", "runtime.py"], str(importers))
    module_source = (SRC_ROOT / (module_name + ".py")).read_text(
        encoding="utf-8",
    )
    check("the module carries exactly one ledger marker",
          module_source.count(
              "# PF-HYPOTHESIS-LEDGER: HYP-PF-027 active") == 1)
    check("the module never names the death lane's timer bit",
          "0x0080" not in module_source)
    imported_modules = [
        node.module for node in ast.walk(ast.parse(module_source))
        if isinstance(node, ast.ImportFrom) and node.module
    ]
    check("the module imports population constants and nothing cross-lane",
          all(m in ("__future__", "dataclasses", "pathlib", "typing",
                    "population") or m.endswith("population")
              for m in imported_modules), str(imported_modules))
    runtime_source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
    check("runtime gates the lane behind the scenario-present check",
          "if npc_hostile_hypothesis_scenario is not None:" in runtime_source
          and runtime_source.count("build_npc_hostile_sweep(") >= 1)
    check("runtime requires the applied pairing before composing",
          "npc_hostile_hypothesis_player_faction_not_applied_no_reply"
          in runtime_source)
    app_source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
    check("the CLI flag demands an explicit existing database",
          "'--npc-hostile-hypothesis-scenario requires an explicit '"
          in app_source)
    check("the scenario stays test-only, non-lethal and write-free",
          base["test_only"] is True and base["production_allowed"] is False
          and base["lethal"] is False
          and base["persisted_post_state"]["database_write"] == "none")
    check("the nonclaims say whose values these are",
          "faction_values_1_and_6_are_our_composition_not_the_original_"
          "servers_which_is_unrecoverable" in base["nonclaims"]
          and "no_client_has_ever_been_shown_one_byte_of_this_profile"
          in base["nonclaims"])

    print()
    print("guards run: %d" % guards)
    if failures:
        print("RESULT: FAIL - %d guard(s) drifted: %s"
              % (len(failures), failures))
        return 1
    print("RESULT: PASS - the hostile-presentation lane composes the parent's "
          "proven SPAWN plus exactly the five-byte faction splice, refuses "
          "every driven wrong hold by name, and claims nothing about a "
          "client (GT-032 is queued, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
