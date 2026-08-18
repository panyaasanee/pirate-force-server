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
  3. the four sweep frames reproduce the twelve sha256 pins carried in the
     module AND in the scenario file, from the same live computation, and the
     BASELINE frame is byte-identical to HYP-PF-020's baseline and to the
     ``player_wire`` projection a real client has accepted since NAME-002;
  4. the exact pair the client's IsDead predicate reads is present on exactly
     one frame -- current HP (bit 0x0004) == 0 AND the death timer (bit 0x0080)
     > 0.0f -- read out of the composed bytes, tag by tag;
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

    print("-- 3. the four frames reproduce their pins --")
    per_step = scenario_raw["probe"]["per_step"]
    frames = []
    for index, label in enumerate(sp.HP_DEATH_STEP_ORDER):
        pc, frame = sp.make_hp_death_step_response(legacy, actor, index, unlock)
        body = sp.hp_death_attr_body(pc)
        frames.append((label, body, pc, frame))
        check(
            "step %s reproduces its attr body / pc / frame pins" % label,
            hashlib.sha256(body).hexdigest().upper()
            == sp.HP_DEATH_PROBE_ATTR_BODY_SHA256[label]
            and hashlib.sha256(pc).hexdigest().upper()
            == sp.HP_DEATH_PROBE_PC_SHA256[label]
            and hashlib.sha256(frame).hexdigest().upper()
            == sp.HP_DEATH_PROBE_FRAME_SHA256[label]
            and len(body) == sp.HP_DEATH_PROBE_ATTR_BODY_SIZE[label]
            and len(pc) == sp.HP_DEATH_PROBE_PC_SIZE[label]
            and len(frame) == sp.HP_DEATH_PROBE_FRAME_SIZE[label],
        )
        check(
            "step %s matches the scenario's own pins" % label,
            per_step[label]["attr_body_sha256"]
            == sp.HP_DEATH_PROBE_ATTR_BODY_SHA256[label]
            and per_step[label]["pc_sha256"] == sp.HP_DEATH_PROBE_PC_SHA256[label]
            and per_step[label]["frame_sha256"]
            == sp.HP_DEATH_PROBE_FRAME_SHA256[label]
            and per_step[label]["lethal"]
            == (label in sp.HP_DEATH_LETHAL_STEP_LABELS),
        )
        check(
            "step %s carries vital 0x309A with the body at the fixed offset"
            % label,
            pc[16:18] == sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little")
            and pc[sp.STATS_PC_ATTR_BODY_OFFSET:
                   sp.STATS_PC_ATTR_BODY_OFFSET + len(body)] == body,
        )
        check(
            "step %s re-decodes to its declared field set" % label,
            sp.decode_actor_attr(body, unlock)
            == (
                actor.identity_lo, actor.identity_hi,
                sp.hp_death_step_fields(legacy, actor, index),
            ),
        )
    check(
        "the BASELINE frame is HYP-PF-020's baseline and the proven "
        "player_wire projection",
        frames[0][1] == make_actor_attr_with_name(
            legacy, actor.identity_lo, actor.identity_hi, actor.scene_id,
            actor.scene_sequence, actor.character_name,
        )
        and hashlib.sha256(frames[0][1]).hexdigest().upper()
        == sp.STATS_PROBE_ATTR_BODY_SHA256["BASELINE"],
    )

    print("-- 4. exactly one frame satisfies the client's IsDead predicate --")
    lethal_labels = []
    for label, body, _pc, _frame in frames:
        mask = int.from_bytes(
            body[BASIC_MASK_OFFSET:BASIC_MASK_OFFSET + 2], "little",
        )
        check(
            "step %s carries the pinned BasicAttr mask" % label,
            mask == sp.HP_DEATH_PROBE_BASIC_MASK[label], hex(mask),
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
        "exactly the HP_ZERO frame is lethal",
        lethal_labels == list(sp.HP_DEATH_LETHAL_STEP_LABELS),
        str(lethal_labels),
    )
    armed = frames[sp.HP_DEATH_STEP_ORDER.index("TIMER_ARMED")][1]
    check(
        "the timer goes out as tag 0x2A + %r seconds little-endian"
        % sp.HP_DEATH_TIMER_SECONDS,
        sp.HP_DEATH_TIMER_WIRE_BYTES in armed
        and struct.unpack(
            "<f",
            armed[armed.index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 1:
                  armed.index(sp.HP_DEATH_TIMER_WIRE_BYTES) + 5],
        )[0] == sp.HP_DEATH_TIMER_SECONDS,
    )
    check(
        "the timer clears the death-window gate DURATION_DYING - 0.5",
        sp.HP_DEATH_TIMER_SECONDS
        >= sp.DURATION_DYING_IMAGE_DEFAULT - sp.DURATION_DYING_WINDOW_MARGIN,
    )
    _lo, _hi, last = sp.decode_actor_attr(frames[-1][1], unlock)
    check("the sweep ends with the character alive", last["hp_current"] > 0)

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
