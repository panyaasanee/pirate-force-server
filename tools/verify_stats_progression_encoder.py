"""Deterministic verifier for the STATS-PROG-002 / HYP-PF-020 progression encoder.

Recomputes -- from the frozen v141 module, the encoder and the scenario file, in
one clean interpreter and with no network, no database and no client image --
every number STATS-PROG-002 claims:

  1. the field table matches STATS-PROG-001's tables (mask bit, object offset,
     wire tag, width) for all 23 implemented fields;
  2. the report's gate-pin addresses ascend with the mask bits in both blocks,
     which is the entire basis for "emission order == ascending mask bit";
  3. the generic mask-driven encoder reproduces the hand-written, already
     client-accepted ``player_wire.make_actor_attr_with_name`` byte for byte,
     for the pinned probe and for three unrelated identities/scenes/names;
  4. every implemented field round-trips through the decoder on its own and all
     together;
  5. the nine sweep frames are cumulative, change exactly one field each, and
     reproduce the 27 sha256 pins carried in the module AND in the scenario;
  6. the module pins and the scenario pins are the same values;
  7. the lane's containment holds: exactly app.py and runtime.py import it, and
     the module names none of the five progression verbs.

Exit 0 = every guard held.  Exit 1 = at least one drifted, with the list.

Usage:  py -3 tools/verify_stats_progression_encoder.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pirateforce_foundation.legacy_bridge import load_legacy  # noqa: E402
from pirateforce_foundation.player_wire import (  # noqa: E402
    make_actor_attr_with_name,
)
import pirateforce_foundation.stats_progression_hypothesis as sp  # noqa: E402


SCENARIO = ROOT / "scenarios" / "stats_progression_hypothesis_xp_sweep.json"
SRC_ROOT = ROOT / "src" / "pirateforce_foundation"
LEGACY_PATH = ROOT / "current" / "pf_login_game_server_v141.py"

# STATS-PROG-001 sections 4 and 5, transcribed once, here, independently of the
# module under test.
REPORT_FIELDS = {
    "level": (0x0002, 0x5E, 0x12, "u16"),
    "hp_current": (0x0004, 0x44, 0x14, "u32"),
    "hp_max": (0x0008, 0x48, 0x14, "u32"),
    "mp_current": (0x0010, 0x4C, 0x14, "u32"),
    "mp_max": (0x0020, 0x50, 0x14, "u32"),
    "scene_id": (0x0100, 0x5C, 0x12, "u16"),
    "scene_sequence": (0x0200, 0x60, 0x32, "qword"),
    "class_id": (0x00000001, 0x8C, 0x19, "u32"),
    "skill_points": (0x00000008, 0x7C, 0x19, "u32"),
    "unspent_ability_points": (0x00000010, 0x80, 0x12, "u16"),
    "ability_str": (0x00000020, 0x82, 0x12, "u16"),
    "ability_con": (0x00000040, 0x84, 0x12, "u16"),
    "ability_dex": (0x00000080, 0x86, 0x12, "u16"),
    "ability_int": (0x00000100, 0x88, 0x12, "u16"),
    "ability_per": (0x00000200, 0x8A, 0x12, "u16"),
    "experience": (0x00000400, 0xA0, 0x32, "qword"),
    "cash": (0x00000800, 0xA8, 0x32, "qword"),
    "ability_bonus_str": (0x00040000, 0x182, 0x12, "u16"),
    "ability_bonus_con": (0x00080000, 0x184, 0x12, "u16"),
    "ability_bonus_dex": (0x00100000, 0x186, 0x12, "u16"),
    "ability_bonus_int": (0x00200000, 0x188, 0x12, "u16"),
    "ability_bonus_per": (0x00400000, 0x18A, 0x12, "u16"),
    "character_name": (0x01000000, 0x164, 0x48, "wstring"),
}

SAMPLES = {
    "level": 250, "hp_current": 7, "hp_max": 9, "mp_current": 11,
    "mp_max": 13, "scene_id": 3, "scene_sequence": 2 ** 40,
    "class_id": 4, "skill_points": 6, "unspent_ability_points": 8,
    "ability_str": 1, "ability_con": 2, "ability_dex": 3, "ability_int": 4,
    "ability_per": 5, "experience": 2 ** 33, "cash": 12345,
    "ability_bonus_str": 6, "ability_bonus_con": 7, "ability_bonus_dex": 8,
    "ability_bonus_int": 9, "ability_bonus_per": 10,
    "character_name": "test01",
}

PROGRESSION_VERBS = (
    "AbilityDepoly", "CLearnSkillVital", "CLearnSkillResultVital",
    "CRevertSkilltVital", "CSkillAttr",
)

failures: list[str] = []
guards = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global guards
    guards += 1
    if ok:
        print("  PASS  %s" % label)
        return
    failures.append(label)
    print("  FAIL  %s%s" % (label, ("  [%s]" % detail) if detail else ""))


def main() -> int:
    legacy = load_legacy(LEGACY_PATH)
    scenario = json.loads(SCENARIO.read_text(encoding="utf-8"))

    print("-- 1. field table against STATS-PROG-001 sections 4 and 5 --")
    check("the module implements exactly the 23 transcribed fields",
          set(sp.PROGRESSION_FIELDS) == set(REPORT_FIELDS),
          str(sorted(set(sp.PROGRESSION_FIELDS) ^ set(REPORT_FIELDS))))
    for name, expected in REPORT_FIELDS.items():
        field = sp.PROGRESSION_FIELDS.get(name)
        check("field %s carries the report's (bit, offset, tag, width)" % name,
              field is not None
              and (field.mask_bit, field.offset, field.tag, field.kind)
              == expected)

    print("-- 2. emission order == ascending mask bit --")
    for label, fields, pins in (
        ("BasicAttr", sp.BASIC_ATTR_FIELDS, sp.BASIC_ATTR_GATE_PINS),
        ("ActorAttr", sp.ACTOR_ATTR_FIELDS, sp.ACTOR_ATTR_GATE_PINS),
    ):
        bits = [f.mask_bit for f in fields]
        check("%s field order is ascending mask bit" % label,
              bits == sorted(bits) and len(set(bits)) == len(bits))
        addresses = [pins[f.mask_bit] for f in fields if f.mask_bit in pins]
        check("%s gate pins ascend with the mask bits" % label,
              addresses == sorted(addresses)
              and len(set(addresses)) == len(addresses))
    check("only the ActorAttr name bit is unpinned and says it is derived",
          [f.name for f in sp.ACTOR_ATTR_FIELDS
           if f.mask_bit not in sp.ACTOR_ATTR_GATE_PINS] == ["character_name"]
          and "derived" in sp.PROGRESSION_FIELDS["character_name"].evidence)
    check("the name bit plus the cash bit is the mask player_wire has shipped",
          sp.PROGRESSION_FIELDS["character_name"].mask_bit
          | sp.PROGRESSION_FIELDS["cash"].mask_bit == 0x01000800)

    print("-- 3. cross-check against the proven player_wire projection --")
    actors = [
        sp.STATS_PROBE_ACTOR,
        sp.StatsProgressionActor(0x10020007, 0, 2, 0, "test01"),
        sp.StatsProgressionActor(1, 0, 1, 9, "A"),
        sp.StatsProgressionActor(0xFFFFFFFF, 0xFFFFFFFF, 0xFFFF, 5, "abcdef"),
    ]
    for actor in actors:
        composed = sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi,
            sp.stats_progression_baseline_fields(legacy, actor),
        )
        proven = make_actor_attr_with_name(
            legacy, actor.identity_lo, actor.identity_hi, actor.scene_id,
            actor.scene_sequence, actor.character_name,
        )
        check("baseline for identity 0x%08X is byte-identical to player_wire"
              % actor.identity_lo, composed == proven)
    check("the baseline cash constant still matches the frozen module",
          legacy.V116_INITIAL_CASH == sp.STATS_PROBE_CASH)
    check("the two ids still match the frozen module",
          legacy.UPDATE_ATTR_VITAL == sp.UPDATE_ATTR_VITAL_ID
          and legacy.ACTOR_ATTR == sp.ACTOR_ATTR_ID)

    print("-- 4. encoder/decoder round trip --")
    ok = True
    for name, value in SAMPLES.items():
        body = sp.encode_actor_attr(legacy, 0x11, 0x22, {name: value})
        ok = ok and sp.decode_actor_attr(body) == (0x11, 0x22, {name: value})
    check("every implemented field round-trips on its own", ok)
    every = sp.encode_actor_attr(legacy, 0x11, 0x22, dict(SAMPLES))
    check("all 23 fields together round-trip",
          sp.decode_actor_attr(every) == (0x11, 0x22, SAMPLES))
    refused = 0
    for bad in ({"nope": 1}, {"experience": True}, {"level": 0x10000},
                {"character_name": ""}, {"experience": -1},
                {"character_name": "a\U0001F600b"}):
        try:
            sp.encode_actor_attr(legacy, 1, 0, bad)
        except ValueError:
            refused += 1
    check("the six representative bad field sets are all refused", refused == 6)

    print("-- 5. the nine sweep frames --")
    actor = sp.STATS_PROBE_ACTOR
    previous: dict = sp.stats_progression_baseline_fields(legacy, actor)
    for index, label in enumerate(sp.STATS_PROGRESSION_STEP_ORDER):
        fields = sp.stats_progression_step_fields(legacy, actor, index)
        added = sp.STATS_PROGRESSION_STEP_FIELDS[label]
        body = sp.encode_actor_attr(
            legacy, actor.identity_lo, actor.identity_hi, fields,
        )
        pc, frame = sp.make_stats_progression_step_response(
            legacy, actor, index,
        )
        check("step %s is cumulative over the previous field set" % label,
              set(previous) <= set(fields)
              and all(fields[k] == v for k, v in previous.items()
                      if k not in added))
        check("step %s reproduces its attr body / pc / frame pins" % label,
              hashlib.sha256(body).hexdigest().upper()
              == sp.STATS_PROBE_ATTR_BODY_SHA256[label]
              and hashlib.sha256(pc).hexdigest().upper()
              == sp.STATS_PROBE_PC_SHA256[label]
              and hashlib.sha256(frame).hexdigest().upper()
              == sp.STATS_PROBE_FRAME_SHA256[label]
              and len(body) == sp.STATS_PROBE_ATTR_BODY_SIZE[label]
              and len(pc) == sp.STATS_PROBE_PC_SIZE[label]
              and len(frame) == sp.STATS_PROBE_FRAME_SIZE[label])
        check("step %s body sits at the fixed envelope offset" % label,
              pc[sp.STATS_PC_ATTR_BODY_OFFSET:
                 sp.STATS_PC_ATTR_BODY_OFFSET + len(body)] == body)
        check("step %s carries vital 0x309A" % label,
              pc[16:18] == sp.UPDATE_ATTR_VITAL_ID.to_bytes(2, "little"))
        previous = fields
    check("the last frame carries level, both ability halves and the second "
          "experience value",
          previous["level"] == sp.STATS_PROGRESSION_LEVEL
          and previous["experience"] == sp.STATS_PROGRESSION_EXPERIENCE_2
          and [previous[n] for n in ("ability_str", "ability_con",
                                     "ability_dex", "ability_int",
                                     "ability_per")] == [11, 22, 33, 44, 55])
    check("the two experience values differ",
          sp.STATS_PROGRESSION_EXPERIENCE_1
          != sp.STATS_PROGRESSION_EXPERIENCE_2)

    print("-- 6. the scenario file pins the same values --")
    check("the scenario loads through the exact allowlist",
          sp.load_stats_progression_hypothesis_scenario(SCENARIO).step_order
          == sp.STATS_PROGRESSION_STEP_ORDER)
    check("the scenario stays test-only with no database write",
          scenario["test_only"] is True
          and scenario["production_allowed"] is False
          and scenario["persisted_post_state"]["database_write"] == "none")
    per_step = scenario["probe"]["per_step"]
    check("the scenario's 27 hashes are the module's 27 hashes",
          all(per_step[label]["pc_sha256"] == sp.STATS_PROBE_PC_SHA256[label]
              and per_step[label]["frame_sha256"]
              == sp.STATS_PROBE_FRAME_SHA256[label]
              and per_step[label]["attr_body_sha256"]
              == sp.STATS_PROBE_ATTR_BODY_SHA256[label]
              for label in sp.STATS_PROGRESSION_STEP_ORDER))
    declared = dict(scenario["wire"]["basic_attr_fields"])
    declared.update(scenario["wire"]["actor_attr_fields"])
    check("the scenario's field schema is the module's field table",
          set(declared) == set(REPORT_FIELDS)
          and all((declared[n]["mask_bit"], declared[n]["object_offset"],
                   declared[n]["wire_tag"], declared[n]["width"])
                  == REPORT_FIELDS[n] for n in REPORT_FIELDS))

    print("-- 7. containment --")
    module_name = "stats_progression_hypothesis"
    importers = sorted(
        path.name for path in SRC_ROOT.glob("*.py")
        if module_name in path.read_text(encoding="utf-8")
        and path.name != module_name + ".py"
    )
    check("exactly app.py and runtime.py import the lane",
          importers == ["app.py", "runtime.py"], str(importers))
    module_source = (SRC_ROOT / (module_name + ".py")).read_text(
        encoding="utf-8",
    )
    check("the module names none of the five progression verbs",
          not [v for v in PROGRESSION_VERBS if v in module_source])
    runtime_source = (SRC_ROOT / "runtime.py").read_text(encoding="utf-8")
    check("every runtime mention sits behind the scenario gate",
          "if stats_progression_hypothesis_scenario is not None:"
          in runtime_source
          and runtime_source.count(
              "make_stats_progression_step_response(") == 1)
    app_source = (SRC_ROOT / "app.py").read_text(encoding="utf-8")
    check("the CLI flag demands an explicit existing database",
          "'--stats-progression-hypothesis-scenario requires an explicit "
          "existing --db'" in app_source)

    print()
    print("guards run: %d" % guards)
    if failures:
        print("RESULT: FAIL - %d guard(s) drifted: %s"
              % (len(failures), failures))
        return 1
    print("RESULT: PASS - STATS-PROG-002 encoder verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
