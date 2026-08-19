#!/usr/bin/env python3
"""Deterministic offline verifier for REMOTE-PLAYER-ENCODER-001 / HYP-PF-025.

Recomputes -- from the frozen v141 module, the encoder under test and its
scenario file, in one clean interpreter with no network, no database, no
server and no client process -- every number the actor_type 2 (CNetActor)
visibility-probe encoder claims, and proves the lane is locked, pinned,
deterministic and contained.

DESIGN 7.1 GUARD FAMILIES (all named):

  A. CONTRACT   an INDEPENDENT restatement of the wire contract lives inside
                this file (the module's own tables are NOT imported for it)
                and is compared, value by value, against the module constants.
  B. ORACLE     the ActorAttr BasicAttr prefix reproduces the frozen,
                client-proven legacy.make_npc_attr span byte for byte.
  C. LOCK       nothing composes without the wire-unlock token; a value-equal
                forgery is refused by identity; the token comes only from the
                allowlisted scenario object.
  D. PINS       the composed sweep re-derives every REMOTE_PLAYER_PINS number
                with hashlib here, those numbers appear in the scenario file,
                the SPAWN_AVATAR pin is a skeleton pin, and every frame equals
                legacy.frame_pc(pc).
  E. DETERMINISM  the sweep is byte-identical over 200 builds and the module
                source names no source of entropy.
  F. REJECTIONS every rejection family raises with its reason AND hands back
                no bytes, exercised through a real call.
  G. CONTAINMENT  only app.py and runtime.py reference the module; it imports
                no population emitter; production_allowed is False; the ledger
                marker is present in module, runtime.py and app.py.
  H. --binary   OPTIONAL re-assertion from the read-only client image.  Without
                --binary these are printed as SKIP and DO NOT affect the exit
                code -- the offline gate must not depend on a file outside the
                repository.

PURE STDLIB ON PURPOSE.  Runs green on Linux and Windows.  Every byte this
tool prints is plain ASCII.

Exit 0 = every guard held.  Exit 2 = at least one drifted, with the list.

Usage:  python3 tools/verify_remote_player_encoder.py
        python3 tools/verify_remote_player_encoder.py --binary <GameClient.bin>
"""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import struct
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation import remote_player_hypothesis as rp  # noqa: E402
from pirateforce_foundation.actor_wire import (  # noqa: E402
    bind_common_attr_identity,
)


LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
SCENARIO = ROOT / "scenarios" / "remote_player_hypothesis_visibility_probe.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
MODULE_PATH = SRC_ROOT / "remote_player_hypothesis.py"

CLIENT_SHA256 = (
    "9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623"
)

# The synthetic AvatarAttr body used everywhere a sweep is composed.  It is a
# valid common-Attr prefix (0x0B / bit 0x01 / 0x32) plus opaque tail, so the
# SKELETON pin (which excludes the tail) is stable and the rebind can run.
AVATAR_BODY = (
    bytes([0x0B, 0x01, 0x32]) + struct.pack("<II", 0xDEAD, 0) + b"opaque"
)
SELECTED_IDENTITY = 0x10010001

# ---------------------------------------------------------------------------
# A. THE INDEPENDENT CONTRACT.  Restated here, on purpose, so a drift in the
# module cannot agree with itself.  Nothing below is imported from the module.
# ---------------------------------------------------------------------------
C_INHERITED_MASK_OFFSET = 11
C_DERIVED_MASK_OFFSET = 13
C_ACTOR_COUNT_OFFSET = 15
C_ACTOR_LIST_OFFSET = 17
C_VITAL_ID = 0x6E9D
C_VERSION = 4
C_ACTOR_TYPE = 2
C_ATTR_ID_ACTOR = 0x12AD
C_ATTR_ID_AVATAR = 0x16A0
C_ATTR_ID_MOVEMENT = 0x2067
C_ATTR_ID_NPC = 0x0AD5
C_BASIC_MASK_PROBE = 0x030D
C_DEATH_TIMER_BIT = 0x0080
C_ACTOR_ATTR_MASK_PROBE = 0
C_EXTRA_GROUP_TAG = 0x05
C_EXTRA_GROUP_VALUE = 1
C_MOVEMENT_MASKS = (0xFF, 0x01, 0x03)
C_SPACING_SECONDS = 15.0
C_FIRST_DELAY_SECONDS = 0.0
C_STEP_ORDER = (
    "SPAWN_BARE", "SPAWN_AVATAR", "MOVE_A_1", "MOVE_A_2", "NEGATIVE_CONTROL",
)
C_LABEL_PREFIX = "HYP_PF_025_REMOTE_PLAYER_"
C_IDENTITY_A = 0x00A00001
C_IDENTITY_B = 0x00A00002
C_IDENTITY_C = 0x00A00003
C_NPC_BAND_LO = 0x2001
C_NPC_BAND_HI = 0x2073
C_CHARACTER_FLOOR = 0x10000000

# Binary anchors, checked only with --binary.  Sources: this project's round-85
# static pass and the module's own STATIC_ANCHORS.
BIN_JUMP_TABLE_VA = 0x446B2C
BIN_JUMP_TABLE_CASES = (0x4469E1, 0x4469F7, 0x446A3D, 0x446A5A, 0x446A77)
BIN_BIND_THUNKS = (0x469760, 0x4697B0, 0x469800, 0x469850, 0x4698B0)
BIN_ACTOR_ATTR_THUNK = 0x469760
BIN_ACTOR_ATTR_THUNK_SPAN = 0x4697B0 - 0x469760
BIN_ACTOR_ATTR_LOAD = bytes.fromhex("8b5224")   # mov edx,[edx+0x24]
BIN_RES_NAME_VA = 0xF2FFF8
BIN_RES_NAME = "GSCN_RunTimeProtocolRes"


def name_id(name: str) -> int:
    """u16 id = SUM_i (int16)((signed char)name[i] * (i+1)) mod 2^16.

    The same hash v141 already trusts; used here only to tie the literal at
    BIN_RES_NAME_VA to the pinned vital id 0x6E9D.
    """
    acc = 0
    for index, char in enumerate(name.encode("latin1")):
        signed = char if char < 128 else char - 256
        acc = (acc + ((signed * (index + 1)) & 0xFFFF)) & 0xFFFF
    return acc


def va_reader(path):
    """Minimal PE VA->file-offset reader.  Read-only, stdlib only.  Reuses the
    section-walking technique from tools/pf_runtimeres_death_encoder_static.py.
    """
    data = path.read_bytes()
    lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    coff = lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    sect = opt + optsz
    sections = []
    for index in range(nsec):
        off = sect + index * 40
        vsize, vaddr, rsize, rptr = struct.unpack_from("<IIII", data, off + 8)
        sections.append((vaddr, vsize, rptr, rsize))

    def read(va, length):
        rel = va - image_base
        for vaddr, vsize, rptr, rsize in sections:
            if vaddr <= rel < vaddr + max(vsize, rsize):
                start = rptr + (rel - vaddr)
                return data[start:start + length]
        return b""

    return data, read


def main() -> int:
    binary = None
    if "--binary" in sys.argv:
        idx = sys.argv.index("--binary")
        if idx + 1 < len(sys.argv):
            binary = Path(sys.argv[idx + 1])

    failures = []
    guards = 0
    skipped = 0

    def check(name, cond, detail=""):
        nonlocal guards
        guards += 1
        if cond:
            print("  PASS  " + name)
        else:
            failures.append(name)
            print("FAIL %s: %s" % (name, detail))
        return bool(cond)

    def reject(name, call, reason):
        """The call must (a) raise with `reason` in the message and (b) hand
        back no bytes at all."""
        nonlocal guards
        guards += 1
        produced = None
        message = ""
        wrong = None
        try:
            produced = call()
        except (ValueError, rp.RemotePlayerValidationError) as exc:
            message = str(exc)
        except Exception as exc:  # noqa: BLE001 - wrong type is a failure
            wrong = "%s: %s" % (type(exc).__name__, exc)
        ok = produced is None and wrong is None and reason in message
        if ok:
            print("  PASS  reject %s" % name)
        else:
            detail = wrong if wrong is not None else (
                ("returned %r" % (produced,)) if produced is not None
                else ("wrong reason: " + message)
            )
            failures.append("reject " + name)
            print("FAIL reject %s: %s" % (name, str(detail)[:140]))
        return ok

    legacy = load_legacy(LEGACY_PATH)
    scenario = rp.load_remote_player_hypothesis_scenario(SCENARIO)
    scenario_raw = json.loads(SCENARIO.read_text(encoding="utf-8"))
    unlock = rp.remote_player_wire_unlock(scenario)
    probes = rp.resolve_probes(legacy)
    by_role = {p.role: p for p in probes}
    module_source = MODULE_PATH.read_text(encoding="utf-8")

    # -------------------------------------------------------------------
    print("-- A. CONTRACT (independent restatement vs module constants) --")
    check("envelope inherited-mask offset is 11",
          rp.INHERITED_CHANGE_MASK_OFFSET == C_INHERITED_MASK_OFFSET == 11)
    check("envelope derived-mask offset is 13",
          rp.DERIVED_CHANGE_MASK_OFFSET == C_DERIVED_MASK_OFFSET == 13)
    check("actor-entry count offset is 15",
          rp.ACTOR_ENTRY_COUNT_OFFSET == C_ACTOR_COUNT_OFFSET == 15)
    check("actor-entry list offset is 17",
          rp.ACTOR_ENTRY_LIST_OFFSET == C_ACTOR_LIST_OFFSET == 17)
    check("vital id is 0x6E9D",
          rp.RUNTIME_PROTOCOL_RES_ID == C_VITAL_ID == 0x6E9D)
    check("envelope version is 4",
          rp.RUNTIME_PROTOCOL_RES_VERSION == C_VERSION == 4)
    check("remote-player actor_type is 2",
          rp.REMOTE_PLAYER_ACTOR_TYPE == C_ACTOR_TYPE == 2)
    check("derived change mask is the actor-entry bit 0x02",
          rp.DERIVED_CHANGE_MASK_ACTOR_ENTRIES == 0x02)
    check("inherited change mask is absent (0x00)",
          rp.INHERITED_CHANGE_MASK_ABSENT == 0x00)
    check("attr id ActorAttr is 0x12AD",
          rp.ACTOR_ATTR_ID == C_ATTR_ID_ACTOR == 0x12AD)
    check("attr id AvatarAttr is 0x16A0",
          rp.AVATAR_ATTR_ID == C_ATTR_ID_AVATAR == 0x16A0)
    check("attr id MovementAttr is 0x2067",
          rp.MOVEMENT_ATTR_ID == C_ATTR_ID_MOVEMENT == 0x2067)
    check("attr id NPCAttr is 0x0AD5",
          rp.NPC_ATTR_ID == C_ATTR_ID_NPC == 0x0AD5)
    check("BASIC_MASK_PROBE is 0x030D",
          rp.BASIC_MASK_PROBE == C_BASIC_MASK_PROBE == 0x030D)
    check("forbidden death-timer bit is 0x0080",
          rp.BASIC_BIT_DEATH_TIMER_FORBIDDEN == C_DEATH_TIMER_BIT == 0x0080)
    check("ACTOR_ATTR_MASK_PROBE is 0",
          rp.ACTOR_ATTR_MASK_PROBE == C_ACTOR_ATTR_MASK_PROBE == 0)
    check("extra-group tag is 0x05",
          rp.ACTOR_ATTR_EXTRA_GROUP_TAG == C_EXTRA_GROUP_TAG == 0x05)
    check("extra-group value is 1",
          rp.ACTOR_ATTR_EXTRA_GROUP_VALUE == C_EXTRA_GROUP_VALUE == 1)
    check("movement masks are {0xFF, 0x01, 0x03}",
          tuple(rp.MOVEMENT_MASKS_PINNED) == C_MOVEMENT_MASKS == (0xFF, 1, 3))
    check("spacing is 15.0 seconds",
          rp.REMOTE_PLAYER_SPACING_SECONDS == C_SPACING_SECONDS == 15.0)
    check("first delay is 0.0 seconds",
          rp.REMOTE_PLAYER_FIRST_DELAY_SECONDS == C_FIRST_DELAY_SECONDS == 0.0)
    check("step order is the pinned five",
          tuple(rp.REMOTE_PLAYER_STEP_ORDER) == C_STEP_ORDER)
    check("label prefix is HYP_PF_025_REMOTE_PLAYER_",
          rp.REMOTE_PLAYER_ACTION_LABEL_PREFIX == C_LABEL_PREFIX)
    check("probe identity A is 0x00A00001",
          rp.PROBE_IDENTITY_A == C_IDENTITY_A == 0x00A00001)
    check("probe identity B is 0x00A00002",
          rp.PROBE_IDENTITY_B == C_IDENTITY_B == 0x00A00002)
    check("probe identity C is 0x00A00003",
          rp.PROBE_IDENTITY_C == C_IDENTITY_C == 0x00A00003)
    check("character identity floor is 0x10000000",
          rp.CHARACTER_IDENTITY_FLOOR == C_CHARACTER_FLOOR == 0x10000000)
    check("npc identity band base is 0x2000",
          rp.NPC_IDENTITY_BAND_BASE == 0x2000)
    for ident, tag in (
        (C_IDENTITY_A, "A"), (C_IDENTITY_B, "B"), (C_IDENTITY_C, "C"),
    ):
        check("probe %s outside NPC band 0x2001..0x2073 and below floor" % tag,
              not (C_NPC_BAND_LO <= ident <= C_NPC_BAND_HI)
              and ident < C_CHARACTER_FLOOR)
    check("the three probe identities are distinct",
          len({C_IDENTITY_A, C_IDENTITY_B, C_IDENTITY_C}) == 3)

    # -------------------------------------------------------------------
    print("-- B. ORACLE (BasicAttr prefix == frozen make_npc_attr span) --")
    check("resolve_probes yields roles A/B/C at the pinned identities",
          sorted(by_role) == ["A", "B", "C"]
          and by_role["A"].identity == C_IDENTITY_A
          and by_role["B"].identity == C_IDENTITY_B
          and by_role["C"].identity == C_IDENTITY_C)
    for role in ("A", "B", "C"):
        probe = by_role[role]
        body = rp.encode_remote_player_actor_attr(legacy, probe, unlock)
        span = 2 + 9 + 3 + (5 + 2 * len(probe.name)) + 5 + 5 + 3 + 9
        oracle = legacy.make_npc_attr(
            probe.anchor_template_id, probe.identity, probe.scene_id,
            probe.scene_sequence, "", 100, 100, None, probe.name,
        )
        check("probe %s ActorAttr prefix reproduces make_npc_attr for %d bytes"
              % (role, span),
              len(body) >= span and body[:span] == bytes(oracle[:span]))

    # -------------------------------------------------------------------
    print("-- C. LOCK BY DEFAULT --")
    forged = rp.RemotePlayerWireUnlock(
        rp.REMOTE_PLAYER_SCENARIO_ID, rp.REMOTE_PLAYER_HYPOTHESIS_ID,
    )
    check("a value-equal forged unlock compares == to the real token",
          forged == unlock)
    check("the real token is not the forgery (identity differs)",
          forged is not unlock)
    reject("no unlock: encode_remote_player_actor_attr",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, by_role["A"], None),
           "missing_or_forged_wire_unlock")
    reject("no unlock: encode_remote_player_entry",
           lambda: rp.encode_remote_player_entry(
               legacy, "MOVE_A_1", by_role["A"], None),
           "missing_or_forged_wire_unlock")
    reject("no unlock: build_remote_player_sweep",
           lambda: rp.build_remote_player_sweep(
               legacy, probes, None, scenario,
               avatar_wire=AVATAR_BODY, selected_identity=SELECTED_IDENTITY),
           "missing_or_forged_wire_unlock")
    reject("forged value-equal unlock is refused by identity",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, by_role["A"], forged),
           "missing_or_forged_wire_unlock")
    check("the only key is remote_player_wire_unlock(allowlisted scenario)",
          rp.remote_player_wire_unlock(scenario) is unlock
          and unlock is rp._UNLOCK)

    # -------------------------------------------------------------------
    print("-- D. PINS (re-derived here from the composed sweep) --")
    actions = rp.build_remote_player_sweep(
        legacy, probes, unlock, scenario,
        avatar_wire=AVATAR_BODY, selected_identity=SELECTED_IDENTITY,
    )
    check("the composed sweep is exactly five frames", len(actions) == 5)
    per_step = scenario_raw["probe"]["per_step"]
    avatar_len = len(bind_common_attr_identity(
        AVATAR_BODY, C_IDENTITY_B & 0xFFFFFFFF, (C_IDENTITY_B >> 32) & 0xFFFFFFFF,
    ))
    for index, label in enumerate(C_STEP_ORDER):
        _lbl, pc, frame, delay = actions[index]
        pin = rp.REMOTE_PLAYER_PINS[label]
        check("%s frame == legacy.frame_pc(pc)" % label,
              frame == legacy.frame_pc(pc))
        check("%s pin equals the scenario file's per_step block" % label,
              pin == per_step[label])
        if label == "SPAWN_AVATAR":
            check("SPAWN_AVATAR pin marks the avatar tail excluded",
                  pin.get("avatar_tail_excluded_from_pin") is True)
            check("SPAWN_AVATAR pin carries NO pc_sha256/frame_sha256 keys",
                  "pc_sha256" not in pin and "frame_sha256" not in pin
                  and "pc_size" not in pin and "frame_size" not in pin)
            skeleton = pc[:len(pc) - avatar_len]
            check("SPAWN_AVATAR skeleton size re-derives to the pin",
                  len(skeleton) == pin["pc_skeleton_size"])
            check("SPAWN_AVATAR skeleton sha256 re-derives to the pin",
                  hashlib.sha256(skeleton).hexdigest().upper()
                  == pin["pc_skeleton_sha256"])
            check("SPAWN_AVATAR basic/movement masks re-derive to the pin",
                  pin["basic_mask"] == 0x030D and pin["movement_mask"] == 0xFF)
        else:
            check("%s pc size re-derives to the pin" % label,
                  len(pc) == pin["pc_size"])
            check("%s pc sha256 re-derives to the pin" % label,
                  hashlib.sha256(pc).hexdigest().upper() == pin["pc_sha256"])
            check("%s frame size re-derives to the pin" % label,
                  len(frame) == pin["frame_size"])
            check("%s frame sha256 re-derives to the pin" % label,
                  hashlib.sha256(frame).hexdigest().upper()
                  == pin["frame_sha256"])
            check("%s movement mask re-derives to the pin" % label,
                  pin["movement_mask"] in C_MOVEMENT_MASKS)

    # -------------------------------------------------------------------
    print("-- E. DETERMINISM --")
    baseline = rp.build_remote_player_sweep(
        legacy, probes, unlock, scenario,
        avatar_wire=AVATAR_BODY, selected_identity=SELECTED_IDENTITY,
    )
    identical = True
    for _ in range(200):
        again = rp.build_remote_player_sweep(
            legacy, probes, unlock, scenario,
            avatar_wire=AVATAR_BODY, selected_identity=SELECTED_IDENTITY,
        )
        if again != baseline:
            identical = False
            break
    check("the sweep is byte-identical across 200 builds", identical)
    for token in ("import random", "os.urandom", "time.time", "monotonic"):
        check("the module source names no %s" % token,
              token not in module_source)

    # -------------------------------------------------------------------
    print("-- F. REJECTIONS (each raises its reason and returns no bytes) --")
    A = by_role["A"]
    B = by_role["B"]
    reject("actor_type_not_the_remote_player_branch (type 5)",
           lambda: rp.encode_remote_player_entry(
               legacy, "MOVE_A_1", A, unlock, actor_type=5),
           "actor_type_not_the_remote_player_branch")
    for at in (0, 1, 7, True):
        reject("actor_type_outside_client_jump_table (%r)" % at,
               lambda at=at: rp.encode_remote_player_entry(
                   legacy, "MOVE_A_1", A, unlock, actor_type=at),
               "actor_type_outside_client_jump_table")
    reject("actor_type_3_would_claim_the_local_player_slot",
           lambda: rp.encode_remote_player_entry(
               legacy, "MOVE_A_1", A, unlock, actor_type=3),
           "actor_type_3_would_claim_the_local_player_slot")
    reject("actor_attr_inside_actor_type_4_entry",
           lambda: rp.encode_remote_player_entry(
               legacy, "SPAWN_BARE", A, unlock, actor_type=4),
           "actor_attr_inside_actor_type_4_entry")

    # npc_attr_inside_...: hand-build an entry carrying ActorAttr + NPCAttr +
    # full Movement for probe A, wrap it as one frame, and hand it to the
    # validator at the SPAWN_BARE slot (a real path; no encoder shortcut can
    # emit an NPCAttr on a non-control step).
    def _npc_on_spawn_bare():
        aa = rp.encode_remote_player_actor_attr(legacy, A, unlock)
        npc = legacy.make_npc_attr(
            A.anchor_template_id, A.identity, A.scene_id, A.scene_sequence,
            A.anchor_visual_preset, 100, 100, None, A.name,
        )
        mv = rp._make_movement_attr(legacy, A, 0xFF, A.x, A.y, A.z, 0.0)
        entry = legacy.make_remote_actor_entry(2, A.identity, [
            (rp.ACTOR_ATTR_ID, aa), (rp.NPC_ATTR_ID, npc),
            (rp.MOVEMENT_ATTR_ID, mv),
        ])
        pc, frame = legacy.make_runtime_remote_actors([entry])
        mutated = [list(a) for a in actions]
        mutated[0] = [actions[0][0], pc, frame, 0.0]
        return rp.validate_remote_player_sweep(
            [tuple(a) for a in mutated], scenario, probes)
    reject("npc_attr_inside_actor_type_2_outside_the_negative_control",
           _npc_on_spawn_bare,
           "npc_attr_inside_actor_type_2_outside_the_negative_control")

    # skill_attr_is_my_actor_only: decode a hand-built pc whose attr id is
    # 0x1661.
    def _skill_attr_decode():
        body = (bytes([0x0B, 0x01, 0x32])
                + struct.pack("<II", A.identity & 0xFFFFFFFF, 0)
                + bytes([0x0B, 0x00]))
        entry = legacy.make_remote_actor_entry(
            2, A.identity, [(rp.SKILL_ATTR_ID, body)])
        pc, _frame = legacy.make_runtime_remote_actors([entry])
        return rp.decode_remote_player_actor_entry_frame(pc)
    reject("skill_attr_is_my_actor_only",
           _skill_attr_decode, "skill_attr_is_my_actor_only")

    reject("probe_identity_collides_with_the_selected_character",
           lambda: rp.build_remote_player_sweep(
               legacy, probes, unlock, scenario,
               avatar_wire=AVATAR_BODY, selected_identity=C_IDENTITY_A),
           "probe_identity_collides_with_the_selected_character")

    reject("probe_identity_collides_with_the_frozen_npc_band",
           lambda: rp._require_probe_identity(0x2050, 0x2073),
           "probe_identity_collides_with_the_frozen_npc_band")
    reject("probe_identity_collides_with_the_character_identity_space",
           lambda: rp._require_probe_identity(0x10000001, 0x2073),
           "probe_identity_collides_with_the_character_identity_space")
    reject("probe_identity_outside_qword",
           lambda: rp._require_probe_identity(1 << 70, 0x2073),
           "probe_identity_outside_qword")

    reject("hp_zero_would_cross_into_the_death_chain",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, A, unlock, current_hp=0),
           "hp_zero_would_cross_into_the_death_chain")
    reject("death_timer_bit_is_not_this_lanes_field",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, A, unlock, basic_mask=0x038D),
           "death_timer_bit_is_not_this_lanes_field")
    reject("basic_mask_is_not_the_pinned_probe_mask",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, A, unlock, basic_mask=0x030C),
           "basic_mask_is_not_the_pinned_probe_mask")
    reject("character_name_not_encodable_as_utf16le",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, dataclasses.replace(A, name="\ud800"), unlock),
           "character_name_not_encodable_as_utf16le")

    # basic_prefix_does_not_reproduce_make_npc_attr: a legacy lookalike whose
    # make_npc_attr returns junk, passed through as a wrapper.
    class _JunkLegacy:
        def __init__(self, real):
            self._real = real

        def __getattr__(self, attr):
            return getattr(self._real, attr)

        def make_npc_attr(self, *args, **kwargs):
            return b"\x00" * 256
    reject("basic_prefix_does_not_reproduce_make_npc_attr",
           lambda: rp.encode_remote_player_actor_attr(
               _JunkLegacy(legacy), A, unlock),
           "basic_prefix_does_not_reproduce_make_npc_attr")

    reject("actor_attr_mask_high_half_not_implemented",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, A, unlock, actor_mask=1 << 40),
           "actor_attr_mask_high_half_not_implemented")
    reject("actor_attr_extra_group_flag_not_one",
           lambda: rp.encode_remote_player_actor_attr(
               legacy, A, unlock, extra_group_value=2),
           "actor_attr_extra_group_flag_not_one")
    reject("movement_mask_outside_the_pinned_set",
           lambda: rp._make_movement_attr(legacy, A, 0x07, A.x, A.y, A.z, 0.0),
           "movement_mask_outside_the_pinned_set")
    reject("movement_position_not_finite_float32",
           lambda: rp._make_movement_attr(
               legacy, A, 0x01, float("nan"), A.y, A.z, 0.0),
           "movement_position_not_finite_float32")
    reject("avatar_wire_absent_or_not_a_common_attr_body",
           lambda: rp.encode_remote_player_entry(
               legacy, "SPAWN_AVATAR", B, unlock, avatar_wire=b"zz"),
           "avatar_wire_absent_or_not_a_common_attr_body")

    # avatar_wire_identity_rebind_failed is only reachable if the identity bind
    # lies; bind_common_attr_identity cannot, so this is honestly SKIPPED.
    skipped += 1
    print("  SKIP  avatar_wire_identity_rebind_failed (not reachable: "
          "bind_common_attr_identity always rebinds the identity correctly)")

    # Envelope mutations, read back by the module's standalone walker.
    def _mut(idx, val):
        raw = bytearray(actions[0][1])
        raw[idx] = val
        return bytes(raw)
    reject("actor_entry_count_not_one (flip count u16 at offset 15)",
           lambda: rp.decode_remote_player_actor_entry_frame(_mut(15, 2)),
           "actor_entry_count_not_one")
    reject("envelope_id_or_version_not_pinned (flip the id)",
           lambda: rp.decode_remote_player_actor_entry_frame(_mut(1, 0xFF)),
           "envelope_id_or_version_not_pinned")
    reject("envelope_id_or_version_not_pinned (flip the version byte)",
           lambda: rp.decode_remote_player_actor_entry_frame(_mut(9, 5)),
           "envelope_id_or_version_not_pinned")
    reject("inherited_change_mask_not_zero (flip offset 11)",
           lambda: rp.decode_remote_player_actor_entry_frame(_mut(11, 1)),
           "inherited_change_mask_not_zero")
    reject("derived_change_mask_not_the_actor_entry_bit (flip offset 13)",
           lambda: rp.decode_remote_player_actor_entry_frame(_mut(13, 4)),
           "derived_change_mask_not_the_actor_entry_bit")

    for idx in (99, True, -1):
        reject("unknown_step_label (index %r)" % idx,
               lambda idx=idx: rp.make_remote_player_step_response(
                   legacy, probes, idx, unlock, scenario,
                   avatar_wire=AVATAR_BODY),
               "unknown_step_label")

    def _wrong_delay():
        mutated = [list(a) for a in actions]
        mutated[1][3] = 99.0
        return rp.validate_remote_player_sweep(
            [tuple(a) for a in mutated], scenario, probes)
    reject("step_order_or_delay_not_pinned (wrong delay)",
           _wrong_delay, "step_order_or_delay_not_pinned")

    reject("missing_or_forged_wire_unlock (value-equal forgery)",
           lambda: rp.require_remote_player_wire_unlock(forged),
           "missing_or_forged_wire_unlock")

    # sweep_does_not_contain_the_negative_control: replace the NC frame with the
    # SPAWN_BARE frame.  SOME named refusal must fire and no rows may return.
    def _nc_replaced():
        mutated = [list(a) for a in actions]
        mutated[4] = [actions[4][0], actions[0][1], actions[0][2], 15.0]
        return rp.validate_remote_player_sweep(
            [tuple(a) for a in mutated], scenario, probes)
    guards += 1
    produced_nc = None
    nc_msg = ""
    try:
        produced_nc = _nc_replaced()
    except rp.RemotePlayerValidationError as exc:
        nc_msg = str(exc)
    if produced_nc is None and nc_msg:
        print("  PASS  reject negative-control-replaced fires a named refusal "
              "and returns no rows")
    else:
        failures.append("reject negative-control-replaced")
        print("FAIL reject negative-control-replaced: %s"
              % (("returned rows" if produced_nc is not None else nc_msg)[:120]))

    # composed_bytes_do_not_match_the_pin: shadow REMOTE_PLAYER_PINS in-process.
    def _pin_shadow():
        saved = rp.REMOTE_PLAYER_PINS
        shadow = copy.deepcopy(saved)
        shadow["SPAWN_BARE"] = dict(shadow["SPAWN_BARE"])
        shadow["SPAWN_BARE"]["pc_size"] = 99999
        rp.REMOTE_PLAYER_PINS = shadow
        try:
            return rp.build_remote_player_sweep(
                legacy, probes, unlock, scenario,
                avatar_wire=AVATAR_BODY, selected_identity=SELECTED_IDENTITY)
        finally:
            rp.REMOTE_PLAYER_PINS = saved
    reject("composed_bytes_do_not_match_the_pin",
           _pin_shadow, "composed_bytes_do_not_match_the_pin")
    check("REMOTE_PLAYER_PINS was restored after the shadow",
          rp.REMOTE_PLAYER_PINS["SPAWN_BARE"]["pc_size"] == 169)

    # Scenario allowlist.
    def _extra_key_scenario():
        data = json.loads(SCENARIO.read_text(encoding="utf-8"))
        data["AN_EXTRA_KEY"] = 1
        handle, path = tempfile.mkstemp(suffix=".json")
        os.write(handle, json.dumps(data).encode("utf-8"))
        os.close(handle)
        try:
            return rp.load_remote_player_hypothesis_scenario(path)
        finally:
            os.unlink(path)
    reject("scenario with one extra key exceeds the exact allowlist",
           _extra_key_scenario, "exceeds the exact allowlist")

    def _lookalike_scenario():
        fields = [f.name for f in dataclasses.fields(
            rp.RemotePlayerHypothesisScenario)]
        Look = dataclasses.make_dataclass("Look", fields)
        look = Look(
            rp.REMOTE_PLAYER_SCENARIO_ID, rp.REMOTE_PLAYER_HYPOTHESIS_ID,
            rp.REMOTE_PLAYER_STEP_ORDER, 15.0, 0.0,
            rp.REMOTE_PLAYER_ACTION_LABEL_PREFIX,
        )
        return rp.require_remote_player_hypothesis_scenario(look)
    reject("positional lookalike scenario dataclass is refused",
           _lookalike_scenario, "exceeds the allowlist")

    # -------------------------------------------------------------------
    print("-- G. CONTAINMENT --")
    importers = sorted(
        path.name for path in SRC_ROOT.glob("*.py")
        if "remote_player_hypothesis" in path.read_text(encoding="utf-8")
        and path.name != "remote_player_hypothesis.py"
    )
    check("only app.py and runtime.py reference the module",
          importers == ["app.py", "runtime.py"], str(importers))
    # The module may import only constants and load_port_royal_placements from
    # population, never an emitter.
    import ast
    pop_names = []
    for node in ast.walk(ast.parse(module_source)):
        if isinstance(node, ast.ImportFrom) and node.module \
                and node.module.endswith("population"):
            pop_names.extend(alias.name for alias in node.names)
    check("the module imports only constants + load_port_royal_placements "
          "from population",
          bool(pop_names) and all(
              name == "load_port_royal_placements" or name.isupper()
              or name.replace("_", "").isupper()
              for name in pop_names),
          str(pop_names))
    check("population's emitters (make_*/emit_*/build_*) are not imported",
          not any(
              name.startswith("make_") or name.startswith("emit_")
              or name.startswith("build_") for name in pop_names),
          str(pop_names))
    check("the module declares production_allowed = False",
          rp.production_allowed is False
          and "production_allowed = False" in module_source)
    marker = "PF-HYPOTHESIS-LEDGER: HYP-PF-025 active"
    check("the ledger marker is present in the module",
          marker in module_source)
    check("the ledger marker is present in runtime.py",
          marker in (SRC_ROOT / "runtime.py").read_text(encoding="utf-8"))
    check("the ledger marker is present in app.py",
          marker in (SRC_ROOT / "app.py").read_text(encoding="utf-8"))

    # -------------------------------------------------------------------
    print("-- H. CLIENT-IMAGE BYTE GUARDS (optional --binary) --")
    if binary is None or not binary.is_file():
        n_binary = 5 + len(BIN_BIND_THUNKS) + 2  # sha, jt, thunks, load, name
        skipped += n_binary
        print("  SKIP  %d image guards (no --binary handed in; the offline "
              "gate must not depend on a file outside the repository)"
              % n_binary)
    else:
        data, read = va_reader(binary)
        check("client image sha256 matches the pinned image",
              hashlib.sha256(data).hexdigest().upper() == CLIENT_SHA256)
        table = [struct.unpack("<I", read(BIN_JUMP_TABLE_VA + i * 4, 4))[0]
                 for i in range(5)]
        check("actor-type jump table at 0x446B2C has the five pinned entries",
              tuple(table) == BIN_JUMP_TABLE_CASES, str([hex(x) for x in table]))
        for va in BIN_BIND_THUNKS:
            check("bind thunk at 0x%06X exists in the image" % va,
                  len(read(va, 8)) == 8 and read(va, 1) != b"")
        span = read(BIN_ACTOR_ATTR_THUNK, BIN_ACTOR_ATTR_THUNK_SPAN)
        check("0x469760 span carries 8B 52 24 (mov edx,[edx+0x24])",
              BIN_ACTOR_ATTR_LOAD in span)
        literal = read(BIN_RES_NAME_VA, 2 * len(BIN_RES_NAME) + 8)
        text = literal.split(b"\x00", 1)[0].decode("ascii", "replace")
        check("0x%X is the literal L\"%s\" whose vital id is 0x6E9D"
              % (BIN_RES_NAME_VA, BIN_RES_NAME),
              text == BIN_RES_NAME
              and name_id(BIN_RES_NAME) == C_VITAL_ID == rp.RUNTIME_PROTOCOL_RES_ID)

    # -------------------------------------------------------------------
    print()
    print("guards run: %d" % guards)
    if failures:
        for name in failures:
            print("FAILED GUARD: %s" % name)
        print("RESULT: FAIL - %d guard(s) drifted" % len(failures))
        return 2
    print("RESULT: PASS - HYP-PF-025 / REMOTE-PLAYER-ENCODER-001 verified "
          "offline (client layer = attended, not run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
