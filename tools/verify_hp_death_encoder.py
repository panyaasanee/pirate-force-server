#!/usr/bin/env python3
"""Deterministic verifier for the HP-DEATH-002 / HYP-PF-022 lethal encoder.

Recomputes -- from the frozen v141 module, the encoder and the scenario file, in
one clean interpreter and with no network, no database and no client image --
every number HP-DEATH-002 claims:

  1. the death field is HP-DEATH-001's field (mask bit 0x0080, object offset
     +0x58, wire tag 0x2A, four bytes, gate pin 0x4657AE) and the widened
     BasicAttr table's gate pins still ascend with the mask bits, which is the
     whole basis for "emission order == ascending mask bit";
  2. the lane is LOCKED by default: the 23-field progression table is
     bit-for-bit unchanged, bit 0x0080 is still declared not-implemented for
     HYP-PF-020, the encoder cannot name the field without the unlock token,
     the decoder refuses a body that carries the bit, and a forged token that
     compares EQUAL to the real one still does not open it;
  3. BOTH named step profiles reproduce every sha256 pin carried in the module
     AND in their own scenario file, from the same live computation, and each
     BASELINE frame is byte-identical to HYP-PF-020's baseline and to the
     ``player_wire`` projection a real client has accepted since NAME-002;
  4. the exact pair the client's IsDead predicate reads is present on exactly
     one frame of each profile -- current HP (bit 0x0004) == 0 AND the death
     timer (bit 0x0080) > 0.0f -- read out of the composed bytes, tag by tag,
     and each profile ends the way it says it ends (``death_sweep`` alive,
     ``dying_hold`` dead);
  4b. the two profiles differ ONLY where they are meant to: identical BASELINE
     bytes, and a TIMER_ARMED that differs in exactly the four f32 bytes of the
     timer value and nowhere else;
  4c. the step-plan validator FAILS on a profile that breaks its own contract --
     an ends-dead plan that still restores HP, an ends-dead plan whose timer is
     under the death-window gate, an ends-alive plan that stops on the kill, and
     a plan that kills before it arms;
  5. every rejection family produces no bytes at all;
  6. the lane's containment holds: exactly app.py and runtime.py import the
     module, the runtime mention sits behind the scenario gate, and the module
     names none of the three Relive verbs.

Optionally, with a path to the read-only client image, it re-asserts the six
byte spans this lane's static conclusions rest on (guards 7.x).  Without an
image those guards are SKIPPED and the exit code is unaffected -- the release
gate must not depend on a file outside the repository.

PURE STDLIB ON PURPOSE: the release gate runs `py -3` with no third-party
packages.

Exit 0 = every guard held.  Exit 1 = at least one drifted, with the list.

Usage:  py -3 tools/verify_hp_death_encoder.py
        py -3 tools/verify_hp_death_encoder.py --binary <GameClient.local.bin>
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_name,
)
from pirateforce_foundation import stats_progression_hypothesis as sp  # noqa: E402


SCENARIO = ROOT / "scenarios" / "hp_death_hypothesis_death_sweep.json"
DYING_HOLD_SCENARIO = ROOT / "scenarios" / "hp_death_hypothesis_dying_hold.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"
BASIC_MASK_OFFSET = 12

# HP-DEATH-001 sections 1 and 2, transcribed once, here, independently of the
# module under test.
REPORT_DEATH_FIELD = (0x0080, 0x58, 0x2A, "f32", 0x4657AE)
REPORT_HP_CURRENT = (0x0004, 0x44, 0x14, "u32")
REPORT_ADDRESSES = {
    "is_dead_player": 0x454AC0,
    "is_dead_player_timer_elapsed": 0x454A70,
    "is_dead_npc": 0x43BDA0,
    "zero_float_constant": 0xF0989C,
    "my_actor_update": 0x44E4E0,
    "main_dead_gate": 0x44A540,
    "main_dead_literal": 0xF0D738,
    "dead_state_sync": 0x4437C0,
    "attr_apply_and_dead_sync": 0x4446F0,
    "attr_apply_and_dead_sync_only_caller": 0x4566A7,
}
RELIVE_VERBS = ("ReliveVital", "ReliveMarkerVital", "Pets_NotifySailorDeadVital")

# The byte spans this lane's own static pass rests on.  Checked only when a
# client image is handed in.  Every one of these is a literal read out of the
# read-only image; none of them is dereferenced or executed.
BINARY_GUARDS = (
    (
        0x44A540,
        "568bf18b068b5040ffd284c0745af646108075546838d7f000b908070901e89d496500"
        "85c0753f8b8648030000f30f104058",
        "0x44A540 calls vtable +0x40 (IsDead) and only then looks up "
        "L\"Main_Dead\"",
    ),
    (
        0x44A572,
        "f20f2a0d9c240201f20f5c0dd092f0000f5ac0660f2fc8771b",
        "the death window is behind `(double)[0x102249C] - 0.5 <= timer`",
    ),
    (
        0x48346A,
        "681c19f10056e8cbf1ffff689c24020168fc18f10056",
        "the by-name binder binds 0x102249C to the literal at 0xF118FC",
    ),
    (
        0x5F24C9,
        "8b0b8b018b5010ffd28b0dc42e03010fb7c05081c130010000e849670000",
        "UpdateAttrVital 0x5F2400 resolves the Attr by CLASS ID against "
        "[0x1032EC4]+0x130",
    ),
    (
        0x5F2504,
        "8b0b8b018b502457ffd2",
        "... and then calls the incoming Attr's vtable +0x24 with it",
    ),
    (
        0x464E40,
        "66a1a0340301c3",
        "ActorAttr vtable +0x10 is `mov ax,[0x10334A0]` -- the class id",
    ),
    (
        0x464B8F,
        "8b57448956448b47488946488b4f4c894e4c8b57508956"
        "50d94754d95e54d94758d95e58",
        "BasicAttr's copy 0x464B40 copies +0x44 and the +0x58 float with NO "
        "mask consulted",
    ),
    (
        0x4573BC,
        "e85ff9ffff8dbe30010000508bcf898648030000",
        "the actor caches the same Attr pointer at +0x348 and in its +0x130 "
        "collection",
    ),
    # DEATH-ESCALATE-001's five.  Source:
    # reports/PF_RESCUE_AND_DEATH_ESCALATION_STATIC_20260819.md section 8.
    (
        0x44E58D,
        "8b068b503c8bceffd284c00f8486000000",
        "CMyActor::Update calls vtable +0x3C (the timer-elapsed predicate) and "
        "skips the whole block when it is false",
    ),
    (
        0x44E5BD,
        "6860d8f000b908070901e844216500",
        "... and the ONE thing behind that predicate is OpenWindow of "
        "L\"Common_Death\" at 0xF0D860",
    ),
    (
        0x454A7A,
        "0f57c00f2f4058722e",
        "0x454A70 is `xorps xmm0,xmm0; comiss xmm0,[attr+0x58]; jb` -- an "
        "UNORDERED compare takes the jb, so a NaN timer returns FALSE",
    ),
    (
        0x454AA5,
        "33d2395044",
        "... and the value it finally compares is [attr+0x44], current HP, "
        "against 0",
    ),
    (
        0x4656A3,
        "84c07806d94658d95f58",
        "BasicAttr::Merge copies +0x58 FORWARD when bit 0x0080 is CLEAR, which "
        "is why the elapsed frame carries the bit instead of dropping it",
    ),
)
DURATION_DYING_NAME = "DURATION_DYING"


def _va_reader(path: Path):
    """Minimal PE VA->file-offset reader.  Read-only, stdlib only."""
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

    return read


def main() -> int:
    binary = None
    if "--binary" in sys.argv:
        binary = Path(sys.argv[sys.argv.index("--binary") + 1])

    failures: list[str] = []
    guards = 0
    skipped = 0

    def check(label, condition, detail=""):
        nonlocal guards
        guards += 1
        if condition:
            print("  PASS  %s" % label)
        else:
            failures.append(label)
            print("  FAIL  %s %s" % (label, detail))

    legacy = load_legacy(LEGACY_PATH)
    scenario_raw = json.loads(SCENARIO.read_text(encoding="utf-8"))
    scenario = sp.load_hp_death_hypothesis_scenario(SCENARIO)
    unlock = sp.hp_death_lethal_unlock(scenario)
    actor = sp.HP_DEATH_PROBE_ACTOR
    # DYING-HOLD-001: the same lane, the same token, the second step profile.
    dying_hold_raw = json.loads(DYING_HOLD_SCENARIO.read_text(encoding="utf-8"))
    dying_hold_scenario = sp.load_hp_death_hypothesis_scenario(
        DYING_HOLD_SCENARIO,
    )
    PROFILES = (
        (sp.HP_DEATH_PROFILE_DEATH_SWEEP, scenario, scenario_raw),
        (sp.HP_DEATH_PROFILE_DYING_HOLD, dying_hold_scenario, dying_hold_raw),
    )

    print("-- 1. the death field is HP-DEATH-001's field --")
    field = sp.HP_DEATH_TIMER_FIELD
    check(
        "the death field is bit 0x0080 / +0x58 / tag 0x2A / f32 / pin 0x4657AE",
        (
            field.mask_bit, field.offset, field.tag, field.kind,
            sp.HP_DEATH_TIMER_GATE_PIN,
        ) == REPORT_DEATH_FIELD,
    )
    hp_current = sp.PROGRESSION_FIELDS["hp_current"]
    check(
        "current HP is still bit 0x0004 / +0x44 / tag 0x14 / u32",
        (hp_current.mask_bit, hp_current.offset, hp_current.tag,
         hp_current.kind) == REPORT_HP_CURRENT,
    )
    check("the f32 width is four bytes", sp.FIELD_KIND_WIDTH["f32"] == 4)
    pins = [
        sp.LETHAL_BASIC_ATTR_GATE_PINS[item.mask_bit]
        for item in sp.LETHAL_BASIC_ATTR_FIELDS
        if item.mask_bit in sp.LETHAL_BASIC_ATTR_GATE_PINS
    ]
    check(
        "the widened gate pins ascend strictly with the mask bits",
        pins == sorted(pins) and len(set(pins)) == len(pins), str(pins),
    )
    order = [item.name for item in sp.LETHAL_BASIC_ATTR_FIELDS]
    check(
        "the timer is emitted between mp_max and scene_id",
        order.index("hp_death_timer") - 1 == order.index("mp_max")
        and order.index("hp_death_timer") + 1 == order.index("scene_id"),
    )
    check(
        "every documented address matches HP-DEATH-001",
        all(
            getattr(sp, name.upper() + "_VA", None) == value
            for name, value in (
                ("is_dead_player", REPORT_ADDRESSES["is_dead_player"]),
                ("is_dead_npc", REPORT_ADDRESSES["is_dead_npc"]),
                ("zero_float_constant", REPORT_ADDRESSES["zero_float_constant"]),
                ("my_actor_update", REPORT_ADDRESSES["my_actor_update"]),
                ("main_dead_gate", REPORT_ADDRESSES["main_dead_gate"]),
                ("dead_state_sync", REPORT_ADDRESSES["dead_state_sync"]),
            )
        ),
    )

    print("-- 2. the lane is locked by default --")
    check(
        "the 23-field progression table is unchanged",
        "hp_death_timer" not in sp.PROGRESSION_FIELDS
        and len(sp.PROGRESSION_FIELDS) == 23
        and 0x0080 not in {f.mask_bit for f in sp.BASIC_ATTR_FIELDS},
    )
    check(
        "bit 0x0080 is still declared not-implemented for HYP-PF-020",
        0x0080 in sp.NOT_IMPLEMENTED_BASIC_ATTR_BITS,
    )
    locked = False
    try:
        sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi,
            {"hp_current": 0, "hp_death_timer": 60.0},
        )
    except ValueError as exc:
        locked = "unknown_field" in str(exc)
    check("without the token the field name does not exist", locked)
    lethal_body = sp.encode_actor_attr(
        legacy, actor.identity_lo, actor.identity_hi,
        {"hp_current": 0, "hp_death_timer": 60.0}, unlock,
    )
    refused = False
    try:
        sp.decode_actor_attr(lethal_body)
    except ValueError as exc:
        refused = "unimplemented_mask_bit" in str(exc)
    check("without the token a lethal body cannot be decoded", refused)
    forged = sp.HpDeathLethalUnlock(
        sp.HP_DEATH_SCENARIO_ID, sp.HP_DEATH_HYPOTHESIS_ID,
    )
    forged_refused = False
    try:
        sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi,
            {"hp_current": 0, "hp_death_timer": 60.0}, forged,
        )
    except ValueError as exc:
        forged_refused = "lethal_lane_locked" in str(exc)
    check(
        "a forged token that compares EQUAL still does not unlock the lane",
        forged == sp._HP_DEATH_UNLOCK and forged_refused,
    )
    baseline = sp.stats_progression_baseline_fields(legacy, actor)
    check(
        "the baseline projection is byte-identical with and without the token",
        sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi, baseline,
        ) == sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi, baseline, unlock,
        ),
    )

    print("-- 3. every frame of every profile reproduces its pins --")
    composed = {}
    for profile, profile_scenario, raw in PROFILES:
        per_step = raw["probe"]["per_step"]
        frames = []
        for index, label in enumerate(profile.step_order):
            pc, frame = sp.make_hp_death_step_response(
                legacy, actor, index, unlock, profile,
            )
            body = sp.hp_death_attr_body(pc)
            frames.append((label, body, pc, frame))
            check(
                "%s step %s reproduces its attr body / pc / frame pins"
                % (profile.name, label),
                hashlib.sha256(body).hexdigest().upper()
                == profile.probe_attr_body_sha256[label]
                and hashlib.sha256(pc).hexdigest().upper()
                == profile.probe_pc_sha256[label]
                and hashlib.sha256(frame).hexdigest().upper()
                == profile.probe_frame_sha256[label]
                and len(body) == profile.probe_attr_body_size[label]
                and len(pc) == profile.probe_pc_size[label]
                and len(frame) == profile.probe_frame_size[label],
            )
            check(
                "%s step %s matches the scenario's own pins"
                % (profile.name, label),
                per_step[label]["attr_body_sha256"]
                == profile.probe_attr_body_sha256[label]
                and per_step[label]["pc_sha256"] == profile.probe_pc_sha256[label]
                and per_step[label]["frame_sha256"]
                == profile.probe_frame_sha256[label]
                and per_step[label]["attr_body_size"]
                == profile.probe_attr_body_size[label]
                and per_step[label]["pc_size"] == profile.probe_pc_size[label]
                and per_step[label]["frame_size"]
                == profile.probe_frame_size[label]
                and per_step[label]["lethal"]
                == (label in profile.lethal_step_labels),
            )
            check(
                "%s step %s carries vital 0x309A with the body at the fixed "
                "offset" % (profile.name, label),
                pc[16:18] == sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little")
                and pc[sp.STATS_PC_ATTR_BODY_OFFSET:
                       sp.STATS_PC_ATTR_BODY_OFFSET + len(body)] == body,
            )
            check(
                "%s step %s re-decodes to its declared field set"
                % (profile.name, label),
                sp.decode_actor_attr(body, unlock)
                == (
                    actor.identity_lo, actor.identity_hi,
                    sp.hp_death_step_fields(legacy, actor, index, profile),
                ),
            )
        composed[profile.name] = frames
        check(
            "%s BASELINE is HYP-PF-020's baseline and the proven player_wire "
            "projection" % profile.name,
            frames[0][1] == make_actor_attr_with_name(
                legacy, actor.identity_lo, actor.identity_hi, actor.scene_id,
                actor.scene_sequence, actor.character_name,
            )
            and hashlib.sha256(frames[0][1]).hexdigest().upper()
            == sp.STATS_PROBE_ATTR_BODY_SHA256["BASELINE"],
        )
        check(
            "%s scenario declares the plan the module carries" % profile.name,
            raw["id"] == profile.scenario_id
            and raw["dispatch"]["step_order"] == list(profile.step_order)
            and raw["dispatch"]["frames_per_accepted_request"]
            == len(profile.step_order)
            and raw["wire"]["death_field"]["value_seconds"]
            == profile.timer_seconds
            and profile_scenario.death_timer_seconds == profile.timer_seconds
            and profile_scenario.ends_dead is profile.ends_dead,
        )
        check(
            "%s scenario stays test-only, lethal-labelled and write-free"
            % profile.name,
            raw["test_only"] is True
            and raw["production_allowed"] is False
            and raw["lethal"] is True
            and raw["persisted_post_state"]["database_write"] == "none",
        )

    print("-- 4. exactly one frame per profile satisfies IsDead --")
    for profile, _profile_scenario, _raw in PROFILES:
        frames = composed[profile.name]
        lethal_labels = []
        for label, body, _pc, _frame in frames:
            mask = int.from_bytes(
                body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
            )
            check(
                "%s step %s carries the pinned BasicAttr mask"
                % (profile.name, label),
                mask == profile.probe_basic_mask[label], hex(mask),
            )
            _lo, _hi, fields = sp.decode_actor_attr(body, unlock)
            if (
                mask & sp.HP_DEATH_TIMER_MASK_BIT
                and mask & hp_current.mask_bit
                and fields["hp_current"] == 0
                and fields["hp_death_timer"] > 0.0
            ):
                lethal_labels.append(label)
        check(
            "%s: exactly the HP_ZERO frame is lethal" % profile.name,
            lethal_labels == list(profile.lethal_step_labels),
            str(lethal_labels),
        )
        armed = frames[profile.step_order.index("TIMER_ARMED")][1]
        check(
            "%s: the timer goes out as tag 0x2A + %r seconds little-endian"
            % (profile.name, profile.timer_seconds),
            profile.timer_wire_bytes in armed
            and struct.unpack(
                "<f",
                armed[armed.index(profile.timer_wire_bytes) + 1:
                      armed.index(profile.timer_wire_bytes) + 5],
            )[0] == profile.timer_seconds,
        )
        check(
            "%s: the timer clears the death-window gate DURATION_DYING - 0.5"
            % profile.name,
            profile.timer_seconds
            >= sp.DURATION_DYING_IMAGE_DEFAULT - sp.DURATION_DYING_WINDOW_MARGIN,
        )
        _lo, _hi, last = sp.decode_actor_attr(frames[-1][1], unlock)
        if profile.ends_dead and profile.elapsed_step_labels:
            # DEATH-ESCALATE-001.  A profile that carries an elapsed step ends
            # on the OTHER predicate, and the difference is the whole point:
            # HP == 0 with timer > 0 is 0x454AC0 (dying, window open, no
            # animation); HP == 0 with timer <= 0 is 0x454A70, the one
            # CMyActor::Update reads before it opens L"Common_Death".  Reading
            # the wrong one here would let a lane that never escalates pass.
            check(
                "%s ends with the timer elapsed, on the bytes" % profile.name,
                last["hp_current"] == 0
                and last["hp_death_timer"] <= 0.0
                and struct.pack("<f", last["hp_death_timer"])
                == sp.HP_DEATH_TIMER_ELAPSED_WIRE_BYTES[1:]
                and profile.step_order[-1] == profile.elapsed_step_labels[-1]
                and "HP_RESTORED" not in profile.step_order,
            )
            kill_index = profile.step_order.index("HP_ZERO")
            _lo, _hi, killed = sp.decode_actor_attr(
                frames[kill_index][1], unlock,
            )
            check(
                "%s is dying on the kill frame and only there" % profile.name,
                killed["hp_current"] == 0
                and killed["hp_death_timer"] > 0.0
                and profile.step_order.index(profile.elapsed_step_labels[0])
                == kill_index + 1,
            )
        elif profile.ends_dead:
            check(
                "%s ends with the character dead, on the bytes" % profile.name,
                last["hp_current"] == 0 and last["hp_death_timer"] > 0.0
                and profile.step_order[-1] == "HP_ZERO"
                and "HP_RESTORED" not in profile.step_order,
            )
        else:
            check(
                "%s ends with the character alive" % profile.name,
                last["hp_current"] > 0,
            )
    check(
        "dying_hold's timer IS the DURATION_DYING compiled into the image",
        sp.HP_DEATH_DYING_HOLD_TIMER_SECONDS
        == float(sp.DURATION_DYING_IMAGE_DEFAULT)
        and sp.DURATION_DYING_GLOBAL_VA == 0x102249C
        and sp.COMMON_DEATH_LITERAL_VA == 0xF0D860,
    )

    print("-- 4b. the two profiles differ only where they are meant to --")
    sweep = dict(
        (label, body) for label, body, _pc, _frame in composed["death_sweep"]
    )
    hold = dict(
        (label, body) for label, body, _pc, _frame in composed["dying_hold"]
    )
    check(
        "the two BASELINE bodies are byte-identical",
        sweep["BASELINE"] == hold["BASELINE"],
    )
    # 60.0f is 00 00 70 42 and 20.0f is 00 00 A0 41, so two of the four value
    # bytes happen to be equal.  The claim is therefore "nothing OUTSIDE the
    # f32 moved", which is the claim that matters: the tag, the mask, every
    # other field and the whole envelope are the same bytes.
    _timer_at = sweep["TIMER_ARMED"].index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 1
    _differing = [
        index for index, (left, right) in enumerate(
            zip(sweep["TIMER_ARMED"], hold["TIMER_ARMED"])
        ) if left != right
    ]
    check(
        "the two TIMER_ARMED bodies differ only inside the f32 timer value",
        sweep["TIMER_ARMED"] != hold["TIMER_ARMED"]
        and len(sweep["TIMER_ARMED"]) == len(hold["TIMER_ARMED"])
        and _differing
        and set(_differing) <= set(range(_timer_at, _timer_at + 4)),
        str(_differing),
    )
    check(
        "those four bytes are the two f32 timer values and nothing else",
        struct.unpack("<f", sweep["TIMER_ARMED"][
            sweep["TIMER_ARMED"].index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 1:
            sweep["TIMER_ARMED"].index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 5
        ])[0] == sp.HP_DEATH_TIMER_SECONDS
        and struct.unpack("<f", hold["TIMER_ARMED"][
            hold["TIMER_ARMED"].index(sp.HP_DEATH_DYING_HOLD_TIMER_WIRE_BYTES)
            + 1:
            hold["TIMER_ARMED"].index(sp.HP_DEATH_DYING_HOLD_TIMER_WIRE_BYTES)
            + 5
        ])[0] == sp.HP_DEATH_DYING_HOLD_TIMER_SECONDS,
    )

    print("-- 4c. the step-plan validator fails on a broken profile --")

    def _mutant(name, steps, ends_dead, timer, lethal=("HP_ZERO",)):
        """A profile that is deliberately wrong, built from the real one."""
        base = sp.HP_DEATH_PROFILE_DYING_HOLD
        return sp.HpDeathStepProfile(
            name, base.scenario_id, timer, steps, lethal, ends_dead,
            base.spacing_seconds, base.first_delay_seconds,
            base.action_label_prefix, base.response_policy, base.capabilities,
            base.nonclaims, base.probe_attr_body_sha256, base.probe_pc_sha256,
            base.probe_frame_sha256, base.probe_attr_body_size,
            base.probe_pc_size, base.probe_frame_size, base.probe_basic_mask,
            base.timer_wire_bytes,
        )

    _armed_20 = {sp.HP_DEATH_TIMER_NAME: 20.0}
    _armed_19 = {sp.HP_DEATH_TIMER_NAME: 19.0}
    _kill = {"hp_current": 0}
    _restore = {"hp_current": 100}
    traps = (
        (
            "an ends-dead plan that still restores HP",
            _mutant("trap_a", (
                ("BASELINE", {}), ("TIMER_ARMED", _armed_20),
                ("HP_ZERO", _kill), ("HP_RESTORED", _restore),
            ), True, 20.0),
        ),
        (
            "an ends-dead plan whose timer is under the window gate",
            _mutant("trap_b", (
                ("BASELINE", {}), ("TIMER_ARMED", _armed_19),
                ("HP_ZERO", _kill),
            ), True, 19.0),
        ),
        (
            "an ends-alive plan that stops on the kill",
            _mutant("trap_c", (
                ("BASELINE", {}), ("TIMER_ARMED", _armed_20),
                ("HP_ZERO", _kill),
            ), False, 20.0),
        ),
        (
            "a plan that kills before it arms",
            _mutant("trap_d", (
                ("BASELINE", {}), ("HP_ZERO", _kill),
                ("TIMER_ARMED", _armed_20), ("HP_RESTORED", _restore),
            ), False, 20.0),
        ),
    )
    for label, mutant in traps:
        raised = False
        try:
            sp._require_hp_death_step_plan(mutant)
        except RuntimeError:
            raised = True
        check("the validator refuses %s" % label, raised)
        composed_refused = False
        try:
            sp.make_hp_death_step_response(legacy, actor, 1, unlock, mutant)
        except ValueError as exc:
            composed_refused = "unknown_step_profile" in str(exc)
        check(
            "the composer refuses %s outright" % label, composed_refused,
        )
    check(
        "both shipped profiles pass the same validator",
        all(
            sp._require_hp_death_step_plan(profile) is None
            for profile, _s, _r in PROFILES
        ),
    )

    print("-- 5. every rejection produces no bytes --")
    rejections = (
        ({"hp_current": 0, "hp_death_timer": 60}, "death_timer_not_float"),
        ({"hp_current": 0, "hp_death_timer": True}, "death_timer_not_float"),
        ({"hp_current": 0, "hp_death_timer": 0.0}, "death_timer_not_positive"),
        ({"hp_current": 0, "hp_death_timer": -60.0},
         "death_timer_not_positive"),
        ({"hp_current": 0, "hp_death_timer": float("inf")},
         "death_timer_not_finite"),
        ({"hp_current": 0, "hp_death_timer": float("nan")},
         "death_timer_not_finite"),
        ({"hp_current": 0, "hp_death_timer": 20.123456789},
         "death_timer_not_exactly_representable"),
        ({"hp_current": 0, "hp_death_timer": 1.0},
         "death_timer_below_the_death_window_gate"),
        ({"hp_max": 100, "hp_death_timer": 60.0},
         "death_timer_without_hp_current"),
    )
    for fields, reason in rejections:
        produced = None
        message = ""
        try:
            produced = sp.encode_actor_attr(
                legacy, actor.identity_lo, actor.identity_hi, fields, unlock,
            )
        except ValueError as exc:
            message = str(exc)
        check(
            "rejection %s produces no bytes" % reason,
            produced is None and reason in message, message,
        )
    for index in (-1, len(sp.HP_DEATH_STEP_ORDER), True, 1.0):
        rejected = False
        try:
            sp.hp_death_step_fields(legacy, actor, index)
        except ValueError as exc:
            rejected = "unknown_step_label" in str(exc)
        check("step index %r is refused" % (index,), rejected)

    print("-- 5b. the elapsed band is closed by default (DEATH-ESCALATE-001) --")
    hold_profile = sp.HP_DEATH_PROFILE_DYING_HOLD
    elapsed_index = hold_profile.step_order.index("TIMER_ELAPSED")

    def _elapsed_fields(**overrides):
        fields = sp.hp_death_step_fields(
            legacy, actor, elapsed_index, hold_profile,
        )
        fields.update(overrides)
        return fields

    elapsed_refusals = (
        (None, {}, "death_timer_not_positive",
         "no label at all keeps the pre-checkpoint behaviour"),
        ("HP_ZERO", {}, "death_timer_elapsed_outside_the_pinned_final_step",
         "the value cannot be smuggled onto the kill frame"),
        ("BASELINE", {}, "death_timer_elapsed_outside_the_pinned_final_step",
         "nor onto the baseline"),
        ("NOPE", {}, "unknown_step_label",
         "a label the profile does not know is not a quiet no-op"),
        ("TIMER_ELAPSED", {"hp_death_timer": -0.0},
         "death_timer_elapsed_is_not_the_pinned_zero",
         "negative zero packs to four other bytes"),
        ("TIMER_ELAPSED", {"hp_death_timer": -1.0},
         "death_timer_elapsed_is_not_the_pinned_zero",
         "a negative timer would satisfy the predicate and is still refused"),
        ("TIMER_ELAPSED", {"hp_death_timer": float("nan")},
         "death_timer_not_finite",
         "NaN is unordered at 0x454A7D and makes the predicate FALSE"),
        ("TIMER_ELAPSED", {"hp_current": 100},
         "death_timer_elapsed_without_zero_hp",
         "an elapsed frame with HP left is inert"),
    )
    for label, overrides, reason, why in elapsed_refusals:
        produced = None
        message = ""
        try:
            produced = sp.make_hp_death_response(
                legacy, actor, _elapsed_fields(**overrides), unlock,
                hold_profile, label,
            )
        except ValueError as exc:
            message = str(exc)
        check(
            "elapsed refusal: %s (%s)" % (why, reason),
            produced is None and reason in message, message,
        )
    for label in (None, "HP_ZERO", "HP_RESTORED"):
        sweep_fields = sp.hp_death_step_fields(
            legacy, actor, 2, sp.HP_DEATH_PROFILE_DEATH_SWEEP,
        )
        sweep_fields["hp_death_timer"] = 0.0
        produced = None
        try:
            produced = sp.make_hp_death_response(
                legacy, actor, sweep_fields, unlock,
                sp.HP_DEATH_PROFILE_DEATH_SWEEP, label,
            )
        except ValueError:
            pass
        check(
            "death_sweep cannot open the elapsed band with label %r" % (label,),
            produced is None,
        )
    for candidate in (1, 0, "true", None, 1.0):
        produced = None
        message = ""
        try:
            produced = sp.encode_actor_attr(
                legacy, actor.identity_lo, actor.identity_hi,
                _elapsed_fields(), unlock, candidate,
            )
        except ValueError as exc:
            message = str(exc)
        check(
            "the elapsed gate argument %r is not a bool" % (candidate,),
            produced is None and "elapsed_gate_is_not_a_bool" in message,
            message,
        )
    check(
        "the four DEATH-ESCALATE-001 rejections are declared",
        all(
            name in sp.HP_DEATH_REJECTIONS for name in (
                "elapsed_gate_is_not_a_bool",
                "death_timer_elapsed_is_not_the_pinned_zero",
                "death_timer_elapsed_outside_the_pinned_final_step",
                "death_timer_elapsed_without_zero_hp",
            )
        ),
    )
    check(
        "the pinned elapsed value is tag 0x2A and four zero bytes",
        sp.HP_DEATH_TIMER_ELAPSED_WIRE_BYTES == bytes.fromhex("2a00000000")
        and sp.HP_DEATH_TIMER_ELAPSED_SECONDS == 0.0
        and struct.pack("<f", sp.HP_DEATH_TIMER_ELAPSED_SECONDS)
        == sp.HP_DEATH_TIMER_ELAPSED_WIRE_BYTES[1:],
    )

    print("-- 6. containment --")
    module_name = "stats_progression_hypothesis"
    importers = sorted(
        path.name for path in SRC_ROOT.glob("*.py")
        if module_name in path.read_text(encoding="utf-8")
        and path.name != module_name + ".py"
    )
    check(
        "exactly app.py and runtime.py import the lane",
        importers == ["app.py", "runtime.py"], str(importers),
    )
    module_source = (SRC_ROOT / (module_name + ".py")).read_text(
        encoding="utf-8",
    )
    check(
        "the module composes none of the three Relive verbs",
        not [verb for verb in RELIVE_VERBS if verb + "(" in module_source],
    )
    check(
        "the module carries exactly one ledger marker per entry",
        module_source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-020 active") == 1
        and module_source.count("# PF-HYPOTHESIS-LEDGER: HYP-PF-022 active") == 1,
    )
    runtime_source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
    check(
        "every runtime mention sits behind the scenario gate",
        "if hp_death_hypothesis_scenario is not None:" in runtime_source
        and runtime_source.count("make_hp_death_step_response(") == 1,
    )
    app_source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
    check(
        "the CLI flag demands an explicit existing database",
        "'--hp-death-hypothesis-scenario requires an explicit existing --db'"
        in app_source,
    )
    check(
        "the scenario stays test-only, lethal-labelled and write-free",
        scenario_raw["test_only"] is True
        and scenario_raw["production_allowed"] is False
        and scenario_raw["lethal"] is True
        and scenario_raw["persisted_post_state"]["database_write"] == "none",
    )
    check(
        "the scenario records that this transport cannot reach 0x4437C0",
        scenario_raw["wire"]["apply_chain"]["reaches_dead_state_sync"] is False
        and scenario_raw["wire"]["apply_chain"]["copy_is_mask_gated"] is False,
    )
    check(
        "dying_hold states the four things nobody may claim from it",
        {
            "no_client_has_ever_been_shown_one_byte_of_this_profile",
            "the_common_death_window_has_never_been_observed_by_this_project",
            "no_persistence_hp_has_no_write_path_and_this_lane_opens_none",
            "not_a_rule_of_the_original_server_which_this_project_cannot_read",
        } <= set(dying_hold_raw["nonclaims"]),
    )
    check(
        "the second profile added no second key",
        sp.hp_death_lethal_unlock(dying_hold_scenario)
        is sp.hp_death_lethal_unlock(scenario)
        and sp.hp_death_lethal_unlock(dying_hold_scenario)
        is sp._HP_DEATH_UNLOCK,
    )
    unlisted_refused = False
    try:
        sp.load_hp_death_hypothesis_scenario(
            ROOT / "scenarios" / "stats_progression_hypothesis_xp_sweep.json",
        )
    except ValueError as exc:
        unlisted_refused = "exact allowlist" in str(exc)
    check(
        "a scenario file outside the two-name allowlist is refused",
        unlisted_refused,
    )
    check(
        "the module ships exactly the two named profiles",
        set(sp.HP_DEATH_PROFILES) == {"death_sweep", "dying_hold"}
        and sp.HP_DEATH_PROFILES["death_sweep"].ends_dead is False
        and sp.HP_DEATH_PROFILES["dying_hold"].ends_dead is True,
    )
    check(
        "the legacy module symbols still name the death_sweep profile",
        sp.HP_DEATH_STEP_ORDER
        == sp.HP_DEATH_PROFILE_DEATH_SWEEP.step_order
        and sp.HP_DEATH_STEP_FIELDS
        == sp.HP_DEATH_PROFILE_DEATH_SWEEP.step_fields
        and sp.HP_DEATH_TIMER_SECONDS
        == sp.HP_DEATH_PROFILE_DEATH_SWEEP.timer_seconds
        and sp.HP_DEATH_LETHAL_STEP_LABELS
        == sp.HP_DEATH_PROFILE_DEATH_SWEEP.lethal_step_labels
        and sp.HP_DEATH_SCENARIO_ID
        == sp.HP_DEATH_PROFILE_DEATH_SWEEP.scenario_id,
    )

    print("-- 7. client-image byte guards --")
    if binary is None or not binary.is_file():
        skipped = len(BINARY_GUARDS) + 1
        print(
            "  SKIP  %d byte guards (no --binary handed in; the release gate "
            "must not depend on a file outside the repository)" % skipped
        )
    else:
        read = _va_reader(binary)
        for va, expected_hex, label in BINARY_GUARDS:
            expected = bytes.fromhex(expected_hex)
            check(
                "0x%X: %s" % (va, label),
                read(va, len(expected)) == expected,
            )
        name = read(sp.DURATION_DYING_NAME_VA, 2 * (len(DURATION_DYING_NAME) + 1))
        check(
            "0x%X is the literal L\"DURATION_DYING\""
            % sp.DURATION_DYING_NAME_VA,
            name.decode("utf-16-le", "replace").startswith(DURATION_DYING_NAME),
        )

    print()
    print("guards run: %d (skipped: %d)" % (guards, skipped))
    if failures:
        print(
            "RESULT: FAIL - %d guard(s) drifted: %s"
            % (len(failures), failures)
        )
        return 1
    print("RESULT: PASS - HP-DEATH-002 lethal encoder verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
