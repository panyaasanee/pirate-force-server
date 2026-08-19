"""DAMAGE-ENCODER-001: the CHitResult frame this project designed for itself.

READ THIS FIRST -- WHOSE FORMULA THIS IS
----------------------------------------
**The numbers in this module are OURS.  They are not the original server's.**
The original server for this game was shut down years ago, was never published
anywhere, and cannot be recovered.  ``reports/PF_DAMAGE_MODEL001_CLIENT_HIT_
RESULT_EXPECTATION_20260819.md`` (round 83, 235 byte-exact guards) proved the
reason that matters here: **the client computes nothing**.  It carries no
damage formula, applies no scaling and never subtracts damage from hit points.
The number a player sees floating over a target is the signed 32-bit integer
the server placed at hit-entry ``+0x08``, passed through ``abs()`` and printed
with ``"%d"`` -- no multiply, no divide, no table lookup anywhere on the path.

So there is nothing in the image to recover a formula FROM, and the owner
approved designing one instead (2026-08-19 11:45, scope: **one signed i32 plus
one flag word per target**).  Every constant in section "OUR FORMULA" below is
a number this project chose.  Everything in section "THE CONTRACT" is a fact
about one immutable, hash-pinned client image, with the address that proves it.

WHAT THIS MODULE COMPOSES
-------------------------
One ``GSCN_RunTimeProtocolRes`` frame per step, carrying a ``CHitResult``
(wire id ``0x16F7``, **version byte 0**) as a single element of the **VitalData
collection** -- the BASE change mask ``0x02`` object at ``this+0x18``, which is
what the frozen V141 helper ``make_runtime_vitals`` already emits.

    NOTE, because two rounds have now confused these two collections:
    the VitalData collection (base mask ``0x02``, ``this+0x18``) is NOT the
    actor-entry collection (DERIVED mask ``0x02``, ``this+0x1C``) that
    ``runtimeres_death_hypothesis`` rides.  Same bit number, different mask
    byte, different reader.  ``drafts/DAMAGE_MODEL_UNKNOWNS_R90_STATIC.md``
    section 1 pins both.

The sweep is four frames against ONE target.  The lane now ships TWO named
profiles of the same four-step plan, and the second one exists because GT-024
left exactly one question the first profile cannot ask:

* ``hit_sweep`` (the original): the player's own actor is BOTH performer and
  target -- the only identity this lane can be SURE the client already knows.
  Spacing 6.0 s.  GT-024 ran it attended and the numbers rendered.
* ``npc_target`` (DAMAGE-NPC-TARGET-001, the LAST version this entry's budget
  allows): the performer stays the player's own actor -- one side of the frame
  must be the player or the six-stage visibility filter at ``0x43FEF0`` draws
  nothing -- but the hit entry's TARGET is the fixed NPC placement identity
  ``0x2001`` (``0x2000 + placement_idx + 1``, the first Port Royal placement,
  the same identity HYP-PF-023 drives).  Whether ``0x2001`` is actually IN the
  client's identity map at runtime is UNPROVEN and is exactly what GT-027
  tests: a target the client cannot resolve is skipped silently at
  ``0x750D27``, so "no number over the NPC" is the meaningful negative.
  Spacing 15.0 s, so an attended tester can photograph each frame without
  racing their own capture latency (the round-84 lesson).

    HIT_WEAK      damage ``-63``  flags ``0x0001``   a number on screen
    HIT_STRONG    damage ``-379`` flags ``0x0001``   a bigger number
    MISS          damage ``0``    flags ``0x0000``   the control: no NUMBER --
                                                     but NOT silence; see below
    HIT_REACTION  damage ``-63``  flags ``0x0009``   the same number, plus the
                                                     branch behind bit 3

``MISS`` is not filler.  A sweep that only ever shows numbers cannot tell a
tester whether the client is reading our bytes or drawing something of its own,
so :func:`validate_damage_model_sweep` refuses any sweep that does not contain
one -- ``sweep_does_not_contain_a_miss_frame``.

    ERRATUM (round 95, from the round-93 static pass, FINDINGS_R93_CHITRESULT_
    DISPLAY_TARGET_STATIC.md): an earlier revision of this docstring called the
    MISS frame "the control: NO number" as if nothing should appear at all.
    The bytes say otherwise: ``bit0 clear AND damage == 0`` selects FxNumber
    type 6 at ``0x440093`` (``6A 06``), key ``0x2D``, which is the texture
    ``bm_miss.tga`` -- the client is DESIGNED to draw a MISS marker for this
    frame.  Seeing the word MISS on screen is therefore POSITIVE evidence the
    client read our flags and damage; only a floating NUMBER must be absent.
    GT-024 observed exactly that (Panya, eyewitness, 2026-08-20 biground 8).

THE SIGN IS THE MEANING
-----------------------
``+0x08`` is compared **signed** at four sites, all ``cmp dword ptr [ebx+8], 0``
followed by ``jge``, so a negative value is the "took damage" side and the
player still sees a positive number because the display path calls ``abs()``.
This is the single easiest thing in this lane to get backwards, so a positive
value is refused outright (``damage_positive_heal_semantics_unknown``): what a
non-negative value means -- heal, absorb, no-op -- is **unknown**, and unknown
means we do not send it.

``INT32_MIN`` is refused as its own separate rejection, because ``abs()`` built
from ``cdq/xor/sub`` returns ``0x80000000`` unchanged and ``"%d"`` would then
print ``-2147483648``: a minus sign on screen, from the one path designed never
to show one.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is compared against an EXACT allowlist -- one extra or
  missing key anywhere in the tree and the loader refuses.
* Neither the damage field nor the flag word can be named at all without the
  wire unlock token, and the only source of that token is the allowlisted
  scenario object.  With the flag absent, nothing in the process can emit a
  ``CHitResult``.
* Every composed sweep is re-read by an independent tag walker and compared
  against ``DAMAGE_MODEL_PINS`` before a single byte is returned.

WHAT THIS DOES NOT DO
---------------------
It does not touch hit points.  Nothing in this lane subtracts the number it
sends from anything: the client provably will not, and this module opens no
write path of its own.  Tying damage to HP is a later checkpoint and it will
need its own entry.  No client has ever been shown one byte of this profile;
whether the number renders at all is GT-024, attended, not run.  There is one
named runtime risk behind that test, and it is written down rather than
smoothed over: the gate at ``0x5CAE00`` reads a singleton at ``[0x10339B0]``
and returns true when it is NULL, and a true there suppresses the number no
matter what we send.  Static reading cannot say whether that pointer is set
in-game.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from .population import RUNTIME_PROTOCOL_RES_ID


production_allowed = False

DAMAGE_MODEL_SCENARIO_ID = "damage_model_hypothesis_hit_sweep"
DAMAGE_MODEL_NPC_SCENARIO_ID = "damage_model_hypothesis_npc_sweep"
# PF-HYPOTHESIS-LEDGER: HYP-PF-024 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-90 append.  The
# annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
DAMAGE_MODEL_HYPOTHESIS_ID = "HYP-PF-024"
DAMAGE_MODEL_DISPATCH_KWARG = "damage_model_hypothesis_scenario"


# ===========================================================================
# THE CONTRACT.  Facts about the client image, each with the address that
# proves it.  Nothing in this block is a design choice.
# ===========================================================================
CHIT_RESULT_VITAL_ID = 0x16F7
# PROVEN.  The version byte is NOT a vtable slot: it is the instance field at
# ``obj+0x10``, written by the ctor and compared by the collection reader at
# 0x5F3EFC (``3A 4E 10`` = ``cmp cl,[esi+0x10]``, mismatch -> throw
# 0xE0000031).  CHitResult's ctor 0x74F940 zeroes al at 0x74F968 (``33 C0``)
# and stores it at 0x74F979 (``88 46 10``), so the pinned value is 0.  The same
# read cross-checks against classes whose version this project already knew:
# SelectActorVital 10, UpdateNPCAppearVital 0, CreateActorVital 8.
CHIT_RESULT_VITAL_VERSION = 0x00

RUNTIME_PROTOCOL_RES_VERSION = 4
# The BASE change mask (serializer 0x5F4070).  Bit 0x02 selects the VitalData
# collection at ``this+0x18``.  make_runtime_vitals emits exactly this.
BASE_CHANGE_MASK_VITAL_COLLECTION = 0x02
# The DERIVED change mask (serializer 0x5E3EE0), emitted after the collection.
# 0 = no actor-entry collection on this frame.  Omitting the byte entirely is
# what made the client over-read and raise ErrorData=28317 in round 82.
DERIVED_CHANGE_MASK_ABSENT = 0x00

# Byte offsets into the PC that make_runtime_vitals emits.  Each VALUE offset
# is one past its TAG offset, because every field on this wire is a tag byte
# then its payload -- the first draft of this block was off by one on all eight
# constants for exactly that reason, and it went unnoticed because nothing read
# them.  They are now read: validate_damage_model_sweep indexes the composed PC
# with them, so a repeat of that mistake is a red test rather than a comment
# that quietly disagrees with the bytes.
BASE_CHANGE_MASK_TAG_OFFSET = 10
BASE_CHANGE_MASK_OFFSET = 11
VITAL_COUNT_TAG_OFFSET = 12
VITAL_COUNT_OFFSET = 13
VITAL_ID_TAG_OFFSET = 15
VITAL_ID_OFFSET = 16
VITAL_VERSION_TAG_OFFSET = 18
VITAL_VERSION_OFFSET = 19
CHIT_RESULT_PAYLOAD_OFFSET = 20

# Tag map (tag byte -> payload width).  The wire is self-describing: the reader
# compares the tag byte and raises on a mismatch, so a correct width with a
# wrong tag is a broken stream, not a tolerated one.
TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32

# CHitResult header, in the emission order of serializer 0x750040.
HEADER_PERFORMER_OFFSET = 0x18       # tag 0x32 qword, emit 0x750059
HEADER_FIELD2_OFFSET = 0x20          # tag 0x12 u16,   emit 0x750068
HEADER_FIELD3_OFFSET = 0x22          # tag 0x12 u16,   emit 0x750077
HEADER_FIELD4_OFFSET = 0x24          # tag 0x14 u32,   emit 0x750086
HEADER_FIELD5_OFFSET = 0x28          # tag 0x0B u8,    emit 0x750095
HEADER_ARRAY_OFFSET = 0x2C           # array serializer 0x74F5A0, call 0x75009F
CHIT_RESULT_HEADER_WIRE_SIZE = 22    # 9 + 3 + 3 + 5 + 2

# The four header fields whose MEANING is unknown.  We pin them at zero and
# refuse anything else.  Zero is inert on every branch that was read:
#   +0x22 == 0 != 0xEA7A  -> the bail at 0x7507FE (``75 1F``) is not taken
#   +0x24 == 0            -> 0x750E0A (``74 3C``) SKIPS a second effect, no return
#   +0x28 == 0            -> passed through as a parameter, never compared
#   +0x20 == 0            -> 0x702A10 returns NULL (0x702A1A ``33 C0``), so the
#                            gate 0x5CAE00 is false and the number path stays open
# "Inert" is a statement about those branches, not a claim that zero is what
# the original server sent.  See NONCLAIMS.
HEADER_RESERVED_VALUE = 0

# Hit-entry array (shared with CMissileHitResult, which holds it at +0x40).
HIT_ARRAY_WRITE_VA = 0x74F5A0
HIT_ELEMENT_STRIDE = 32              # sar eax,5 @0x74F5B3 and add ebx,0x20 @0x74F686
HIT_ENTRY_TARGET_OFFSET = 0x00       # tag 0x32 qword, write 0x74F62C
HIT_ENTRY_DAMAGE_OFFSET = 0x08       # tag 0x14 u32 READ SIGNED, write 0x74F63E
HIT_ENTRY_POSITION_OFFSET = 0x0C     # 3x tag 0x2A, write 0x74F645 -> 0x5F3490
HIT_ENTRY_YAW_OFFSET = 0x18          # tag 0x2A f32, write 0x74F657  -- an ANGLE
HIT_ENTRY_FLAGS_OFFSET = 0x1C        # tag 0x12 u16, write 0x74F666  -- a bitfield
HIT_ELEMENT_WIRE_SIZE = 37           # 9 + 5 + 15 + 5 + 3
HIT_COUNT_WIRE_SIZE = 3
CHIT_RESULT_PAYLOAD_WIRE_SIZE = (
    CHIT_RESULT_HEADER_WIRE_SIZE + HIT_COUNT_WIRE_SIZE + HIT_ELEMENT_WIRE_SIZE
)

STATIC_ANCHORS = {
    # class identity
    "chit_result_name_literal": 0xF0B5F8,
    "chit_result_registration_thunk": 0xC0C180,
    "chit_result_id_global": 0x108A2E4,
    "chit_result_vtable": 0xF48AA0,
    "chit_result_ctor": 0x74F940,
    "chit_result_sizeof": 0x48,
    "chit_result_serializer": 0x750040,
    "chit_result_inbound_handler": 0x750770,
    "cmissile_hit_result_vtable": 0xF48AC4,
    # the version byte
    "vital_collection_reader": 0x5F3E20,
    "vital_collection_writer": 0x5F38F0,
    "vital_version_tag_site": 0x5F3EE9,
    "vital_version_compare_site": 0x5F3EFC,
    "chit_result_ctor_version_zero": 0x74F979,
    # construction by id: a red-black tree lookup on a u16 key, NOT an allowlist
    "vital_registry_singleton": 0x5E3260,
    "vital_create_by_id": 0x5E2E00,
    "vital_id_map_lookup": 0x731380,
    "chit_result_prototype_registration": 0x755048,
    "vital_dispatch_gate_stub": 0x710440,
    # the number path
    "damage_signed_compare_hit": 0x750919,
    "damage_number_gate": 0x750D45,
    "header_field2_lookup": 0x702A10,
    "header_field2_gate": 0x5CAE00,
    "header_field4_skip": 0x750E0A,
    "entry_flag_bit0_reaction_gate": 0x7509DA,
    "performer_not_found_does_not_return": 0x7507C3,
}


# ===========================================================================
# OUR FORMULA.  Every number below was chosen by this project.
# ===========================================================================
ATK_BASE = 100          # a starting character still connects
K_ATK_STR = 7           # prime, so an on-screen number cannot be mistaken for
K_ATK_LV = 3            # a coincidence of squares or round tens
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1             # the floor of a hit; a miss is damage 0, not damage 1

# Phase 1 has no jitter at all: the tester has to be able to predict the exact
# number before the frame is sent, or the test cannot fail.  Phase 2's jitter,
# if it happens, is a hash of the identities and the step index -- never RNG.
JITTER_PCT_MAX = 0

# The u16 domain the wire itself imposes on every input this formula reads.
FORMULA_INPUT_MIN = 0
FORMULA_INPUT_MAX = 0xFFFF

# Safe band for the value that goes on the wire.
DAMAGE_WIRE_MAX = 0                 # positive is refused: meaning unknown
DAMAGE_WIRE_MIN = -1_000_000        # far from INT32_MIN, abs() stays safe
DAMAGE_WIRE_SCENARIO_MIN = -9999    # phase 1: four digits, readable on screen
INT32_MIN = -2147483648

# The flag word.  Only whole values this project can defend are accepted, and
# the mask is checked as well, so a new bit cannot arrive by arithmetic.
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
FLAGS_HIT_REACTION = 0x0009
FLAGS_VALUE_ALLOWLIST_PHASE1 = (FLAGS_MISS, FLAGS_HIT, FLAGS_HIT_REACTION)
FLAGS_ALLOWED_MASK_PHASE1 = 0x0009
# bit 2, 7, 8 and 11..15.  Bit 7 is the dangerous one: 0x750A84 tests it, so it
# does something, and we do not know what.  Tested-but-unexplained is exactly
# the case for refusing to send it.
FLAGS_FORBIDDEN_MASK = 0xF184
# bit 4 makes the client play _F_KNOCKED_002 INSTEAD of showing the number, so
# it may never ride a frame whose whole purpose is that the number is legible.
FLAGS_BIT_SUPPRESSES_THE_NUMBER = 0x0010
# bit 0 gates the reaction block at 0x7509DA (``0F 84 77 02 00 00``).  The
# number itself is drawn by a second pass that does NOT read this bit, which is
# why the encoder chooses it deliberately instead of leaving it zero.
FLAGS_BIT_REACTION_PASS = 0x0001

# Phase 1 pins the yaw at exactly 0.0f.  It is an angle -- it is fed to sin/cos
# and offset by pi (0xF0D140 = 3.14159274) -- so 0.0 is the most inert value
# that is still type-correct.
YAW_PINNED = 0.0
FLOAT32_MAX = 3.4028234663852886e38

HIT_ENTRY_COUNT_PINNED = 1


@dataclass(frozen=True)
class DamageProfile:
    """The inputs OUR formula reads.  All of them are u16 wire fields."""

    name: str
    level: int
    ability_str: int
    ability_bonus_str: int
    ability_con: int
    ability_bonus_con: int


# The defender is the player as HYP-PF-020's sweep leaves the character: those
# two numbers are already on screen after GT-017, so a tester can check the
# arithmetic from the character sheet without being told the answer.
#
# They are COPIED here rather than imported, deliberately.  A test in
# tests/test_damage_model_hypothesis.py asserts they still equal the two
# level/constitution constants the HYP-PF-020 progression lane ships, so a
# drift is caught -- but the import itself would widen that lane's blast
# radius, and its containment test requires that exactly two foundation
# modules (app.py and runtime.py) mention it AT ALL.  That check is a
# substring match rather than an import scan, which is why this comment does
# not spell the module name out either.  A drift check belongs in a test; a
# dependency does not belong in an encoder.
DEFENDER_LEVEL = 7                  # == STATS_PROGRESSION_LEVEL
DEFENDER_ABILITY_CON = 22           # == STATS_PROGRESSION_ABILITY_CON
DEFENDER_PLAYER_BASELINE = DamageProfile(
    "PLAYER_BASELINE", DEFENDER_LEVEL, 0, 0, DEFENDER_ABILITY_CON, 0,
)
ATTACKER_MOB_WEAK = DamageProfile("MOB_WEAK", 1, 3, 0, 0, 0)
ATTACKER_MOB_STRONG = DamageProfile("MOB_STRONG", 20, 40, 0, 0, 0)

ATTACKER_PROFILES = {
    "MOB_WEAK": ATTACKER_MOB_WEAK,
    "MOB_STRONG": ATTACKER_MOB_STRONG,
}


class DamageModelValidationError(RuntimeError):
    """A composed sweep or entry that must never reach a socket."""


def _require_formula_input(value: Any, label: str) -> int:
    if type(value) is not int or type(value) is bool:
        raise DamageModelValidationError(
            f"formula_input_outside_declared_domain: {label} is not an int"
        )
    if not FORMULA_INPUT_MIN <= value <= FORMULA_INPUT_MAX:
        raise DamageModelValidationError(
            f"formula_input_outside_declared_domain: {label}={value!r}"
        )
    return value


def _require_profile(profile: Any, label: str) -> DamageProfile:
    if type(profile) is not DamageProfile:
        raise DamageModelValidationError(
            f"formula_input_outside_declared_domain: {label} is not a profile"
        )
    _require_formula_input(profile.level, f"{label}.level")
    _require_formula_input(profile.ability_str, f"{label}.ability_str")
    _require_formula_input(
        profile.ability_bonus_str, f"{label}.ability_bonus_str")
    _require_formula_input(profile.ability_con, f"{label}.ability_con")
    _require_formula_input(
        profile.ability_bonus_con, f"{label}.ability_bonus_con")
    return profile


def compute_attack(attacker: Any) -> int:
    """OUR attack number.  Not the client's, which has none."""
    profile = _require_profile(attacker, "attacker")
    return (
        ATK_BASE
        + K_ATK_STR * (profile.ability_str + profile.ability_bonus_str)
        + K_ATK_LV * profile.level
    )


def compute_defense(defender: Any) -> int:
    """OUR defence number."""
    profile = _require_profile(defender, "defender")
    return (
        DEF_BASE
        + K_DEF_CON * (profile.ability_con + profile.ability_bonus_con)
        + K_DEF_LV * profile.level
    )


def compute_damage(attacker: Any, defender: Any) -> int:
    """OUR damage, as the NEGATIVE integer that goes on the wire.

    Computed with Python ints (unbounded), then range-checked.  Nothing here
    wraps, masks or silently clamps to the band: a formula that quietly clamps
    can never be caught drifting.
    """
    rolled = compute_attack(attacker) - compute_defense(defender)
    if rolled < MIN_HIT:
        rolled = MIN_HIT
    if JITTER_PCT_MAX:                                  # pragma: no cover
        raise DamageModelValidationError(
            "jitter is a phase 2 feature and is not implemented"
        )
    damage_wire = -rolled
    result = require_damage_wire_value(damage_wire)
    if -result != rolled:
        raise DamageModelValidationError("formula_output_not_reproducible")
    return result


def require_damage_wire_value(value: Any) -> int:
    """Every refusal the signed i32 at +0x08 can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise DamageModelValidationError("damage_not_integer")
    if value > DAMAGE_WIRE_MAX:
        raise DamageModelValidationError(
            "damage_positive_heal_semantics_unknown")
    if value == INT32_MIN:
        raise DamageModelValidationError("damage_is_int32_min")
    if value < DAMAGE_WIRE_MIN:
        raise DamageModelValidationError("damage_below_safe_band")
    return value


def require_scenario_band(value: int) -> int:
    if not DAMAGE_WIRE_SCENARIO_MIN <= value <= DAMAGE_WIRE_MAX:
        raise DamageModelValidationError("damage_outside_scenario_band")
    return value


def require_flags_value(value: Any) -> int:
    """Every refusal the u16 flag word at +0x1C can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise DamageModelValidationError("flags_not_u16")
    if not 0 <= value <= 0xFFFF:
        raise DamageModelValidationError("flags_not_u16")
    if value & FLAGS_FORBIDDEN_MASK:
        raise DamageModelValidationError("flags_forbidden_bit")
    if value & ~FLAGS_ALLOWED_MASK_PHASE1:
        raise DamageModelValidationError("flags_bit_outside_allowed_mask")
    if value not in FLAGS_VALUE_ALLOWLIST_PHASE1:
        raise DamageModelValidationError("flags_outside_value_allowlist")
    return value


def require_damage_and_flags_agree(damage_wire: int, flags: int) -> None:
    """The two designed fields have to tell the same story.

    A zero with the reaction bit set would ask the client to react to nothing;
    a number without it would draw a figure with no reaction behind it.  Both
    are states no frame of ours should be able to describe.
    """
    if damage_wire == 0 and flags & FLAGS_BIT_REACTION_PASS:
        raise DamageModelValidationError("damage_zero_with_apply_flag")
    if damage_wire != 0 and not flags & FLAGS_BIT_REACTION_PASS:
        raise DamageModelValidationError("damage_nonzero_without_apply_flag")
    if flags & FLAGS_BIT_SUPPRESSES_THE_NUMBER:
        raise DamageModelValidationError(
            "flags_knockback_bit_suppresses_the_number")


# ===========================================================================
# The sweep plan.
# ===========================================================================
HIT_WEAK_STEP_LABEL = "HIT_WEAK"
HIT_STRONG_STEP_LABEL = "HIT_STRONG"
MISS_STEP_LABEL = "MISS"
HIT_REACTION_STEP_LABEL = "HIT_REACTION"

# (label, attacker profile name or None for a miss, flag word)
DAMAGE_MODEL_STEPS = (
    (HIT_WEAK_STEP_LABEL, "MOB_WEAK", FLAGS_HIT),
    (HIT_STRONG_STEP_LABEL, "MOB_STRONG", FLAGS_HIT),
    (MISS_STEP_LABEL, None, FLAGS_MISS),
    (HIT_REACTION_STEP_LABEL, "MOB_WEAK", FLAGS_HIT_REACTION),
)
DAMAGE_MODEL_STEP_ORDER = tuple(row[0] for row in DAMAGE_MODEL_STEPS)
DAMAGE_MODEL_MISS_STEP_LABELS = (MISS_STEP_LABEL,)

DAMAGE_MODEL_FIRST_DELAY_SECONDS = 0.0
DAMAGE_MODEL_SPACING_SECONDS = 6.0
DAMAGE_MODEL_ACTION_LABEL_PREFIX = "HYP_PF_024_DAMAGE_MODEL_"
DAMAGE_MODEL_ACTION_LABELS = tuple(
    DAMAGE_MODEL_ACTION_LABEL_PREFIX + label
    for label in DAMAGE_MODEL_STEP_ORDER
)

# The npc_target profile (DAMAGE-NPC-TARGET-001).  SAME four-step plan -- both
# profiles resolve step i to the same DAMAGE_MODEL_STEPS row object, so the
# damage values, the flag words and the MISS control cannot drift between
# them.  What changes is WHO the hit entry names, and how far apart the frames
# ride:
#
#   * the TARGET is the fixed NPC placement identity 0x2001 -- 0x2000 +
#     placement_idx + 1, the first Port Royal placement, the same identity the
#     HYP-PF-023 death lane drives (RUNTIMERES_DEATH_PROBE_ACTOR_IDENTITY; the
#     value is COPIED here rather than imported, with a drift test beside the
#     defender constants' one, because an encoder should not import a
#     neighbouring lane);
#   * the PERFORMER stays the player's own actor, because one side of the
#     frame must be the player or the six-stage visibility filter at 0x43FEF0
#     draws nothing at all (GT-027 spec, from the round-93 static pass);
#   * the spacing is 15.0 s so an attended tester can photograph every frame
#     without racing their own capture latency (the round-84 lesson: never use
#     your own screenshot as the clock).
#
# Whether 0x2001 is IN the client's identity map at runtime is UNPROVEN.  A
# target the client cannot resolve is skipped silently at 0x750D27, so GT-027
# reads "no number over the NPC" as the meaningful negative, not as nothing.
DAMAGE_NPC_TARGET_IDENTITY_LO = 0x2001
DAMAGE_NPC_TARGET_IDENTITY_HI = 0
DAMAGE_MODEL_NPC_FIRST_DELAY_SECONDS = 0.0
DAMAGE_MODEL_NPC_SPACING_SECONDS = 15.0
DAMAGE_MODEL_NPC_ACTION_LABEL_PREFIX = "HYP_PF_024_DAMAGE_NPC_"
DAMAGE_MODEL_NPC_ACTION_LABELS = tuple(
    DAMAGE_MODEL_NPC_ACTION_LABEL_PREFIX + label
    for label in DAMAGE_MODEL_STEP_ORDER
)


@dataclass(frozen=True)
class DamageModelActor:
    """The per-session inputs a composed frame needs, and nothing else."""

    identity_lo: int
    identity_hi: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class DamageModelWireUnlock:
    scenario_id: str
    hypothesis_id: str


# One token PER PROFILE, compared by identity, so the key issued for one
# profile opens no byte of the other (the same round-91 repair HYP-PF-023
# got when it grew its second profile).
_UNLOCK = DamageModelWireUnlock(
    DAMAGE_MODEL_SCENARIO_ID, DAMAGE_MODEL_HYPOTHESIS_ID,
)
_UNLOCK_NPC = DamageModelWireUnlock(
    DAMAGE_MODEL_NPC_SCENARIO_ID, DAMAGE_MODEL_HYPOTHESIS_ID,
)


@dataclass(frozen=True)
class DamageModelHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str


_PROFILE = DamageModelHypothesisScenario(
    DAMAGE_MODEL_SCENARIO_ID,
    DAMAGE_MODEL_HYPOTHESIS_ID,
    DAMAGE_MODEL_STEP_ORDER,
    DAMAGE_MODEL_SPACING_SECONDS,
    DAMAGE_MODEL_FIRST_DELAY_SECONDS,
    DAMAGE_MODEL_ACTION_LABEL_PREFIX,
)

# Both profiles hold the SAME step tuple object: DAMAGE_MODEL_STEPS is the one
# plan, and a profile is a policy about identities and timing, never a second
# copy of the plan.
_PROFILE_NPC = DamageModelHypothesisScenario(
    DAMAGE_MODEL_NPC_SCENARIO_ID,
    DAMAGE_MODEL_HYPOTHESIS_ID,
    DAMAGE_MODEL_STEP_ORDER,
    DAMAGE_MODEL_NPC_SPACING_SECONDS,
    DAMAGE_MODEL_NPC_FIRST_DELAY_SECONDS,
    DAMAGE_MODEL_NPC_ACTION_LABEL_PREFIX,
)

_UNLOCK_BY_SCENARIO_ID = {
    DAMAGE_MODEL_SCENARIO_ID: _UNLOCK,
    DAMAGE_MODEL_NPC_SCENARIO_ID: _UNLOCK_NPC,
}


def damage_model_wire_unlock(value: Any) -> DamageModelWireUnlock:
    """The only key that lets this process name +0x08 or +0x1C.

    The key is issued FOR the profile that was handed in, and the composers
    compare it by identity against that profile's own token, so a key minted
    from one profile opens no byte of the other.
    """
    profile = require_damage_model_hypothesis_scenario(value)
    return _UNLOCK_BY_SCENARIO_ID[profile.scenario_id]


def require_damage_model_wire_unlock(value: Any) -> DamageModelWireUnlock:
    # Identity, not equality: a forged token that compares equal must not open
    # the lane.
    if value is not _UNLOCK and value is not _UNLOCK_NPC:
        raise DamageModelValidationError(
            "missing_or_forged_wire_unlock: HYP-PF-024 refuses to emit a "
            "CHitResult without the unlock derived from the opt-in scenario"
        )
    return value


def require_damage_model_unlock_for_profile(
    unlock: Any, profile: DamageModelHypothesisScenario,
) -> DamageModelWireUnlock:
    """The pairing check: this profile's own token, by identity, or nothing."""
    require_damage_model_wire_unlock(unlock)
    if unlock is not _UNLOCK_BY_SCENARIO_ID[profile.scenario_id]:
        raise DamageModelValidationError(
            "wire_unlock_is_for_a_different_profile: the key issued for one "
            "profile of HYP-PF-024 opens no byte of the other"
        )
    return unlock


def require_damage_model_hypothesis_scenario(
    value: Any,
) -> DamageModelHypothesisScenario:
    if type(value) is not DamageModelHypothesisScenario or (
        value != _PROFILE and value != _PROFILE_NPC
    ):
        raise DamageModelValidationError(
            "scenario_object_exceeds_allowlist")
    return value


def resolve_actor(legacy: Any, selected: Any) -> DamageModelActor:
    """The player's own actor, at the frozen, hash-pinned V135 spawn point.

    Phase 1 makes the player both performer and target.  That is a DESIGN
    CHOICE to stay on proven ground, not a claim that a real hit looks like
    this: the player's identity is the only one the client is certain to know,
    and 0x7508AD / 0x750D27 skip any entry whose TARGET cannot be found.  (The
    performer is different: 0x7507C3 (``74 25``) proves a missing performer
    does NOT bail -- it just leaves a local slot NULL and falls through.)

    The position is not invented either: it is the frozen V135 player spawn,
    the same hash-pinned source population.py already uses.
    """
    identity_lo = getattr(selected, "identity_lo", None)
    identity_hi = getattr(selected, "identity_hi", None)
    if type(identity_lo) is not int or type(identity_lo) is bool:
        raise DamageModelValidationError("target_identity_outside_qword")
    if type(identity_hi) is not int or type(identity_hi) is bool:
        raise DamageModelValidationError("target_identity_outside_qword")
    if not 0 <= identity_lo <= 0xFFFFFFFF or not 0 <= identity_hi <= 0xFFFFFFFF:
        raise DamageModelValidationError("target_identity_outside_qword")
    return DamageModelActor(
        identity_lo, identity_hi,
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )


# The pinned probe.  The bytes of a live sweep depend on the session's own
# character identity, so they cannot be hashed to a constant.  The fix is the
# one HYP-PF-020 already uses: pin the composition of a FIXED probe identity --
# 0x10010001, the canonical smoke identity the pinned V25 create wire commits --
# and re-compose it on every live build as a drift check.  A live sweep is then
# held to the pinned SIZES and values, and the encoder itself is held to the
# pinned BYTES, on every call.
DAMAGE_PROBE_IDENTITY_LO = 0x10010001
DAMAGE_PROBE_IDENTITY_HI = 0


def damage_probe_actor(legacy: Any) -> DamageModelActor:
    return DamageModelActor(
        DAMAGE_PROBE_IDENTITY_LO, DAMAGE_PROBE_IDENTITY_HI,
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )


def actor_identity(actor: DamageModelActor) -> int:
    if type(actor) is not DamageModelActor:
        raise DamageModelValidationError("target_identity_outside_qword")
    value = (
        ((actor.identity_hi & 0xFFFFFFFF) << 32)
        | (actor.identity_lo & 0xFFFFFFFF)
    )
    if not 0 <= value <= 0xFFFFFFFFFFFFFFFF:
        raise DamageModelValidationError("target_identity_outside_qword")
    return value


def _require_pinned_position(legacy: Any, actor: DamageModelActor) -> None:
    for value, pinned, label in (
        (actor.x, float(legacy.V135_PLAYER_X), "x"),
        (actor.y, float(legacy.V135_PLAYER_Y), "y"),
        (actor.z, float(legacy.V135_PLAYER_Z), "z"),
    ):
        if type(value) is not float or value != pinned:
            raise DamageModelValidationError(
                f"position_not_from_the_pinned_source: {label}")
        if not math.isfinite(value):
            raise DamageModelValidationError(
                f"position_not_from_the_pinned_source: {label}")


def _require_pinned_yaw(value: Any) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise DamageModelValidationError("yaw_not_finite_float32")
    result = float(value)
    if not math.isfinite(result) or abs(result) > FLOAT32_MAX:
        raise DamageModelValidationError("yaw_not_finite_float32")
    if struct.unpack("<f", struct.pack("<f", result))[0] != result:
        raise DamageModelValidationError("yaw_not_finite_float32")
    if result != YAW_PINNED:
        raise DamageModelValidationError("yaw_outside_pinned_value")
    return result


# ===========================================================================
# The encoder.
# ===========================================================================
def encode_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    yaw: float,
    flags: int,
    unlock: Any,
) -> bytes:
    """One 32-byte-stride hit entry, in the write order of 0x74F625..0x74F670."""
    require_damage_model_wire_unlock(unlock)
    if type(target_identity) is not int or type(target_identity) is bool:
        raise DamageModelValidationError("target_identity_outside_qword")
    if not 0 <= target_identity <= 0xFFFFFFFFFFFFFFFF:
        raise DamageModelValidationError("target_identity_outside_qword")
    require_damage_wire_value(damage_wire)
    require_scenario_band(damage_wire)
    require_flags_value(flags)
    require_damage_and_flags_agree(damage_wire, flags)
    yaw = _require_pinned_yaw(yaw)
    if type(position) is not tuple or len(position) != 3:
        raise DamageModelValidationError("position_not_from_the_pinned_source")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target_identity)
    out += legacy.u32tag(TAG_U32, damage_wire & 0xFFFFFFFF)
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise DamageModelValidationError(
                "position_not_from_the_pinned_source")
        out += legacy.f32tag(component)
    out += legacy.f32tag(yaw)
    out += legacy.u16tag(TAG_U16, flags)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise DamageModelValidationError(
            "composed_bytes_do_not_match_the_pin: hit entry is %d bytes"
            % len(out)
        )
    return bytes(out)


def encode_chit_result(
    legacy: Any,
    performer_identity: int,
    entries: list[bytes],
    unlock: Any,
) -> bytes:
    """The CHitResult payload: 5 header fields, then the entry array."""
    require_damage_model_wire_unlock(unlock)
    if type(performer_identity) is not int or type(performer_identity) is bool:
        raise DamageModelValidationError("target_identity_outside_qword")
    if not 0 <= performer_identity <= 0xFFFFFFFFFFFFFFFF:
        raise DamageModelValidationError("target_identity_outside_qword")
    if type(entries) is not list or len(entries) != HIT_ENTRY_COUNT_PINNED:
        raise DamageModelValidationError("entry_count_not_pinned")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer_identity)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise DamageModelValidationError(
            "composed_bytes_do_not_match_the_pin: header is %d bytes"
            % len(header)
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise DamageModelValidationError(
                "composed_bytes_do_not_match_the_pin: entry width")
        out += entry
    if len(out) != CHIT_RESULT_PAYLOAD_WIRE_SIZE:
        raise DamageModelValidationError(
            "composed_bytes_do_not_match_the_pin: payload is %d bytes"
            % len(out)
        )
    return bytes(out)


def step_plan(index: Any) -> tuple[str, str | None, int]:
    if type(index) is not int or type(index) is bool:
        raise DamageModelValidationError("unknown_step_label")
    if not 0 <= index < len(DAMAGE_MODEL_STEPS):
        raise DamageModelValidationError("unknown_step_label")
    return DAMAGE_MODEL_STEPS[index]


def step_damage_wire(index: Any) -> int:
    """The number OUR formula produces for one step of the plan."""
    _label, attacker_name, _flags = step_plan(index)
    if attacker_name is None:
        return 0
    return require_scenario_band(
        compute_damage(ATTACKER_PROFILES[attacker_name],
                       DEFENDER_PLAYER_BASELINE)
    )


def npc_target_identity() -> int:
    """The fixed NPC placement identity the npc_target profile addresses."""
    return (
        ((DAMAGE_NPC_TARGET_IDENTITY_HI & 0xFFFFFFFF) << 32)
        | (DAMAGE_NPC_TARGET_IDENTITY_LO & 0xFFFFFFFF)
    )


def profile_target_identity(
    profile: DamageModelHypothesisScenario, performer_identity: int,
) -> int:
    """WHO the hit entry names, per profile.

    hit_sweep: the performer's own identity -- the player is both sides.
    npc_target: the fixed placement identity 0x2001; the performer must NOT be
    that identity, because the whole point of the profile is that the two
    sides differ (and a session actor with a placement identity would mean
    something upstream is already broken).
    """
    if profile.scenario_id == DAMAGE_MODEL_NPC_SCENARIO_ID:
        if performer_identity == npc_target_identity():
            raise DamageModelValidationError(
                "npc_performer_must_not_be_the_npc_target")
        return npc_target_identity()
    return performer_identity


def make_damage_model_step_response(
    legacy: Any,
    actor: DamageModelActor,
    index: int,
    unlock: Any,
    profile: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the hit sweep."""
    profile = require_damage_model_hypothesis_scenario(profile)
    require_damage_model_unlock_for_profile(unlock, profile)
    label, _attacker_name, flags = step_plan(index)
    if label != profile.step_order[index]:
        raise DamageModelValidationError("unknown_step_label")
    _require_pinned_position(legacy, actor)
    identity = actor_identity(actor)
    target = profile_target_identity(profile, identity)
    entry = encode_hit_entry(
        legacy, target, step_damage_wire(index),
        (actor.x, actor.y, actor.z), YAW_PINNED, flags, unlock,
    )
    payload = encode_chit_result(legacy, identity, [entry], unlock)
    pc, frame = legacy.make_runtime_vitals(
        [(CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION, payload)]
    )
    if frame != legacy.frame_pc(pc):
        raise DamageModelValidationError("HYP-PF-024 frame drift")
    return pc, frame


def build_damage_model_sweep(
    legacy: Any,
    actor: DamageModelActor,
    unlock: Any,
    profile: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole sweep, then refuse to return it unless it is the pin."""
    profile = require_damage_model_hypothesis_scenario(profile)
    require_damage_model_unlock_for_profile(unlock, profile)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(profile.step_order):
        pc, frame = make_damage_model_step_response(
            legacy, actor, index, unlock, profile,
        )
        delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        actions.append((profile.action_label_prefix + label, pc, frame, delay))
    rows = validate_damage_model_sweep(legacy, actions, profile)
    _require_pinned_composition(legacy, profile, unlock, rows)
    return actions


def _require_pinned_composition(
    legacy: Any,
    profile: DamageModelHypothesisScenario,
    unlock: Any,
    rows: list[dict[str, Any]],
) -> None:
    """Two checks, because a live sweep cannot be hashed to a constant.

    The live rows are held to the values and the widths; the encoder itself is
    held to the exact bytes, by re-composing the pinned probe identity here on
    every build.  A drifted encoder therefore cannot ship even once.
    """
    probe = damage_probe_actor(legacy)
    pins = pins_for_profile(profile)
    for index, label in enumerate(profile.step_order):
        pin = pins[label]
        row = rows[index]
        for key in ("damage_wire", "flags", "pc_size", "frame_size"):
            if row[key] != pin[key]:
                raise DamageModelValidationError(
                    "composed_bytes_do_not_match_the_pin: %s %s %r != %r"
                    % (label, key, row[key], pin[key])
                )
        pc, frame = make_damage_model_step_response(
            legacy, probe, index, unlock, profile,
        )
        for value, key in (
            (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
            (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
        ):
            if value != pin[key]:
                raise DamageModelValidationError(
                    "composed_bytes_do_not_match_the_pin: probe %s %s %r != %r"
                    % (label, key, value, pin[key])
                )


# ===========================================================================
# The independent reader.  Deliberately does not reuse the encoder's helpers
# for anything except the pinned constants, so a symmetrical bug in the
# encoder cannot hide here.
# ===========================================================================
def _scalar(pc: bytes, cursor: int, tag: int, width: int, label: str):
    if cursor + 1 + width > len(pc):
        raise DamageModelValidationError(f"{label}: truncated")
    if pc[cursor] != tag:
        raise DamageModelValidationError(
            "%s: tag 0x%02X != 0x%02X" % (label, pc[cursor], tag))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def decode_chit_result_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back with a strict, standalone tag walker."""
    if type(pc) is not bytes:
        raise DamageModelValidationError("pc is not bytes")
    cursor = 0
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "envelope id")
    envelope_id = struct.unpack("<H", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "envelope error data")
    error_data = struct.unpack("<I", raw)[0]
    raw, cursor = _scalar(pc, cursor, 0x08, 1, "envelope version")
    envelope_version = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "base change mask")
    base_mask = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital count")
    vital_count = struct.unpack("<H", raw)[0]
    vitals = []
    for _index in range(vital_count):
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital id")
        vital_id = struct.unpack("<H", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "vital version")
        vital_version = raw[0]
        if vital_id != CHIT_RESULT_VITAL_ID:
            raise DamageModelValidationError(
                "decoder refuses a vital other than CHitResult")
        body, cursor = _decode_chit_result_body(pc, cursor)
        body["vital_id"] = vital_id
        body["vital_version"] = vital_version
        vitals.append(body)
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
    derived_mask = raw[0]
    if cursor != len(pc):
        raise DamageModelValidationError(
            "trailing bytes after the derived change mask")
    return {
        "envelope_id": envelope_id,
        "error_data": error_data,
        "envelope_version": envelope_version,
        "base_change_mask": base_mask,
        "derived_change_mask": derived_mask,
        "vital_count": vital_count,
        "vitals": vitals,
    }


def _decode_chit_result_body(pc: bytes, cursor: int) -> tuple[dict, int]:
    start = cursor
    raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "performer")
    performer = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "header field 2")
    field2 = struct.unpack("<H", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "header field 3")
    field3 = struct.unpack("<H", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "header field 4")
    field4 = struct.unpack("<I", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "header field 5")
    field5 = raw[0]
    header_size = cursor - start
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "hit entry count")
    count = struct.unpack("<H", raw)[0]
    entries = []
    for _index in range(count):
        entry_start = cursor
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "target")
        target = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "damage")
        # read SIGNED: the four cmp/jge sites are what make this field mean
        # anything at all
        damage = struct.unpack("<i", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = _scalar(pc, cursor, TAG_F32, 4, f"position {axis}")
            position.append(struct.unpack("<f", raw)[0])
        raw, cursor = _scalar(pc, cursor, TAG_F32, 4, "yaw")
        yaw = struct.unpack("<f", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "flags")
        flags = struct.unpack("<H", raw)[0]
        entries.append({
            "target_identity": target,
            "damage_wire": damage,
            "position": tuple(position),
            "yaw": yaw,
            "flags": flags,
            "wire_size": cursor - entry_start,
        })
    return (
        {
            "performer_identity": performer,
            "header_field2": field2,
            "header_field3": field3,
            "header_field4": field4,
            "header_field5": field5,
            "header_wire_size": header_size,
            "entry_count": count,
            "entries": entries,
        },
        cursor,
    )


def _require_pinned_offsets(pc: bytes) -> None:
    """Index the composed PC by the named offsets and check what is there.

    A second, positional reading of the same frame the tag walker reads.  It
    exists so the offset constants above cannot drift away from the bytes
    without something going red.
    """
    if len(pc) < CHIT_RESULT_PAYLOAD_OFFSET:
        raise DamageModelValidationError("pc is shorter than the pinned header")
    for offset, expected, label in (
        (BASE_CHANGE_MASK_TAG_OFFSET, TAG_U8, "base change mask tag"),
        (BASE_CHANGE_MASK_OFFSET, BASE_CHANGE_MASK_VITAL_COLLECTION,
         "base change mask"),
        (VITAL_COUNT_TAG_OFFSET, TAG_U16, "vital count tag"),
        (VITAL_COUNT_OFFSET, 1, "vital count"),
        (VITAL_ID_TAG_OFFSET, TAG_U16, "vital id tag"),
        (VITAL_ID_OFFSET, CHIT_RESULT_VITAL_ID & 0xFF, "vital id low byte"),
        (VITAL_VERSION_TAG_OFFSET, TAG_U8, "vital version tag"),
        (VITAL_VERSION_OFFSET, CHIT_RESULT_VITAL_VERSION, "vital version"),
    ):
        if pc[offset] != expected:
            raise DamageModelValidationError(
                "composed_bytes_do_not_match_the_pin: %s at offset %d is "
                "0x%02X, not 0x%02X" % (label, offset, pc[offset], expected)
            )


def validate_damage_model_sweep(
    legacy: Any,
    actions: list[tuple[str, bytes, bytes, float]],
    profile: Any,
) -> list[dict[str, Any]]:
    """Re-read every composed frame and refuse anything the plan does not allow.

    This is the guard the trap tests exist to break.  It returns one row per
    step so the caller can compare against the pins.
    """
    profile = require_damage_model_hypothesis_scenario(profile)
    if type(actions) is not list or len(actions) != len(profile.step_order):
        raise DamageModelValidationError("sweep length is not the pinned plan")
    npc_profile = profile.scenario_id == DAMAGE_MODEL_NPC_SCENARIO_ID
    rows: list[dict[str, Any]] = []
    identities: set[int] = set()
    performers: set[int] = set()
    seen_miss = False
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise DamageModelValidationError("sweep action shape")
        label, pc, frame, delay = action
        expected_label = profile.action_label_prefix + profile.step_order[index]
        if label != expected_label:
            raise DamageModelValidationError("unknown_step_label")
        if type(pc) is not bytes or type(frame) is not bytes:
            raise DamageModelValidationError("sweep action payload type")
        if frame != legacy.frame_pc(pc):
            raise DamageModelValidationError("HYP-PF-024 frame drift")
        expected_delay = (
            profile.first_delay_seconds if index == 0
            else profile.spacing_seconds
        )
        if type(delay) is not float or delay != expected_delay:
            raise DamageModelValidationError("sweep delay is not the plan")
        decoded = decode_chit_result_frame(pc)
        if decoded["envelope_id"] != RUNTIME_PROTOCOL_RES_ID:
            raise DamageModelValidationError("envelope id is not 0x6E9D")
        if decoded["envelope_version"] != RUNTIME_PROTOCOL_RES_VERSION:
            raise DamageModelValidationError("envelope is not version 4")
        if decoded["base_change_mask"] != BASE_CHANGE_MASK_VITAL_COLLECTION:
            raise DamageModelValidationError(
                "base change mask does not select the VitalData collection")
        if decoded["derived_change_mask"] != DERIVED_CHANGE_MASK_ABSENT:
            raise DamageModelValidationError(
                "derived change mask must be absent on this lane")
        if decoded["vital_count"] != 1:
            raise DamageModelValidationError("entry_count_not_pinned")
        body = decoded["vitals"][0]
        if body["vital_id"] != CHIT_RESULT_VITAL_ID:
            raise DamageModelValidationError("vital id is not CHitResult")
        if body["vital_version"] != CHIT_RESULT_VITAL_VERSION:
            raise DamageModelValidationError("vital_version_not_pinned")
        # The same frame read a second way, positionally.  It runs AFTER the
        # tag walker on purpose: the walker's refusals are the specific,
        # named ones a reader is looking for, and this one exists only to
        # catch the offset constants drifting away from the bytes.
        _require_pinned_offsets(pc)
        if body["header_wire_size"] != CHIT_RESULT_HEADER_WIRE_SIZE:
            raise DamageModelValidationError(
                "composed_bytes_do_not_match_the_pin: header width")
        for key in ("header_field2", "header_field3",
                    "header_field4", "header_field5"):
            if body[key] != HEADER_RESERVED_VALUE:
                raise DamageModelValidationError(
                    "header_reserved_field_nonzero")
        if body["entry_count"] != HIT_ENTRY_COUNT_PINNED:
            raise DamageModelValidationError("entry_count_not_pinned")
        entry = body["entries"][0]
        if entry["wire_size"] != HIT_ELEMENT_WIRE_SIZE:
            raise DamageModelValidationError(
                "composed_bytes_do_not_match_the_pin: entry width")
        if npc_profile:
            # The npc_target profile: the entry names the fixed placement
            # identity, and the performer must be somebody ELSE (the player),
            # because one side of the frame has to pass the visibility filter
            # and the point of the profile is that the two sides differ.
            if entry["target_identity"] != npc_target_identity():
                raise DamageModelValidationError(
                    "npc_target_identity_not_pinned")
            if body["performer_identity"] == entry["target_identity"]:
                raise DamageModelValidationError(
                    "npc_performer_must_not_be_the_npc_target")
        elif entry["target_identity"] != body["performer_identity"]:
            raise DamageModelValidationError(
                "performer_identity_not_the_selected_actor")
        identities.add(entry["target_identity"])
        performers.add(body["performer_identity"])
        require_damage_wire_value(entry["damage_wire"])
        require_scenario_band(entry["damage_wire"])
        require_flags_value(entry["flags"])
        require_damage_and_flags_agree(entry["damage_wire"], entry["flags"])
        if entry["damage_wire"] != step_damage_wire(index):
            raise DamageModelValidationError("formula_output_not_reproducible")
        if entry["flags"] != DAMAGE_MODEL_STEPS[index][2]:
            raise DamageModelValidationError("flags_outside_value_allowlist")
        if entry["yaw"] != YAW_PINNED:
            raise DamageModelValidationError("yaw_outside_pinned_value")
        pinned_position = (
            float(legacy.V135_PLAYER_X),
            float(legacy.V135_PLAYER_Y),
            float(legacy.V135_PLAYER_Z),
        )
        for got, want in zip(entry["position"], pinned_position):
            if struct.pack("<f", got) != struct.pack("<f", want):
                raise DamageModelValidationError(
                    "position_not_from_the_pinned_source")
        if entry["damage_wire"] == 0 and entry["flags"] == FLAGS_MISS:
            seen_miss = True
        rows.append({
            "label": profile.step_order[index],
            "damage_wire": entry["damage_wire"],
            "flags": entry["flags"],
            "target_identity": entry["target_identity"],
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        })
    if len(identities) != 1 or len(performers) != 1:
        raise DamageModelValidationError(
            "performer_identity_not_the_selected_actor")
    if not seen_miss:
        raise DamageModelValidationError(
            "sweep_does_not_contain_a_miss_frame")
    return rows


# The composed bytes of the PROBE identity, pinned.  Every value here was
# produced by this encoder and read back by the independent walker; none of it
# was copied in from anywhere.  Regenerated only when a wire change is
# intended, and a wire change belongs in a report.
DAMAGE_MODEL_PINS: dict[str, dict[str, Any]] = {
    "HIT_WEAK": {
        "damage_wire": -63,
        "flags": 1,
        "pc_size": 84,
        "pc_sha256": (
            "D824597F0C9AC24F64BE665699A83FF38A792C3342BCAC70202C3F46B5B584D4"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "D0C0C33C9A3ED9A5C8C1C6BCFBBBFB4762793D053002CD97C9A6C9576C98F999"
        ),
    },
    "HIT_STRONG": {
        "damage_wire": -379,
        "flags": 1,
        "pc_size": 84,
        "pc_sha256": (
            "D7A708CBA4642452848D90523852235779D41F8E7869C57F386AE8AC3C285665"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "910669B9029C1E082740BC820BD33E5C1C89E1C2F26924EA2A44FF86C2415FD9"
        ),
    },
    "MISS": {
        "damage_wire": 0,
        "flags": 0,
        "pc_size": 84,
        "pc_sha256": (
            "A1A746E4C2D4A35448531FD878E17A93AE5F2FB778C4A343D288D04621EEB77A"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "AC009503A61ACD2ADCB87C93B12A4C96AB1D6FC7F7313163B093158011EF558C"
        ),
    },
    "HIT_REACTION": {
        "damage_wire": -63,
        "flags": 9,
        "pc_size": 84,
        "pc_sha256": (
            "595B7B5D037BC2EE06D205194A23E8946B1E2F67A0FBC2F31F8A93A65C189F6C"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "0B7DF0A8CAA20E65C2BE6B85D65162BEB6840CF315FFDCD793CCFDE74DDAA8B9"
        ),
    },
}


# The composed bytes of the npc_target profile for the SAME probe performer
# (0x10010001) against the fixed NPC target (0x2001).  Same discipline as
# DAMAGE_MODEL_PINS: every value here was produced by this encoder and read
# back by the independent walker; none of it was copied in from anywhere.
DAMAGE_MODEL_PINS_NPC: dict[str, dict[str, Any]] = {
    "HIT_WEAK": {
        "damage_wire": -63,
        "flags": 1,
        "pc_size": 84,
        "pc_sha256": (
            "D07A4F48E56085982E511FF24E4C4C079DF1318E60A7386BF1B93F5D54A8A4C3"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "0B4537B6240F7C202B5FAF1A9BADCB0E0F7BAFC40191724DFDE953F797F89706"
        ),
    },
    "HIT_STRONG": {
        "damage_wire": -379,
        "flags": 1,
        "pc_size": 84,
        "pc_sha256": (
            "237CB09D44742068F8304FF02CFDA4E61E1045719DE00BE06F0B2CBAAA1E41A5"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "3363C2A44878732D97F204987963B277E47DAF4016F6BDA27D0E92E2F0128FA9"
        ),
    },
    "MISS": {
        "damage_wire": 0,
        "flags": 0,
        "pc_size": 84,
        "pc_sha256": (
            "36702C4201652DBB84C5F712515D28729AC994D07353AAE069D53E454DDD3891"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "E369DDC41CA253CBE3ABD5474760C2F0F4C9D76FD12A7BD1783B1D68D67E7458"
        ),
    },
    "HIT_REACTION": {
        "damage_wire": -63,
        "flags": 9,
        "pc_size": 84,
        "pc_sha256": (
            "5765546FC310F909F39899497472FEE58B4B1825537226FDE71E54D2CFE07F1A"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "166C53D856C974CB009C34423757F09D3CB441D576585E6D3BA3F29B3E7F3FC1"
        ),
    },
}


def pins_for_profile(
    profile: DamageModelHypothesisScenario,
) -> dict[str, dict[str, Any]]:
    if profile.scenario_id == DAMAGE_MODEL_NPC_SCENARIO_ID:
        return DAMAGE_MODEL_PINS_NPC
    return DAMAGE_MODEL_PINS


DAMAGE_MODEL_CAPABILITIES = (
    "emit_chitresult_0x16f7_version_0_inside_the_vitaldata_collection",
    "carry_one_signed_i32_damage_value_and_one_u16_flag_word_per_target",
    "compute_that_value_from_a_formula_this_project_designed_and_pinned",
    "send_a_control_frame_with_no_number_so_a_positive_result_is_falsifiable",
    "refuse_every_value_whose_client_meaning_this_project_cannot_name",
)

DAMAGE_MODEL_NONCLAIMS = (
    "the_original_server_damage_formula_which_this_project_cannot_recover",
    "that_zero_is_what_the_original_server_put_in_the_four_reserved_header_fields",
    "the_meaning_of_any_individual_bit_in_the_hit_entry_flag_word",
    "what_a_non_negative_value_at_entry_plus_0x08_means_to_the_client",
    "that_the_number_renders_at_all_which_depends_on_a_singleton_static_cannot_read",
    "any_link_between_this_number_and_hit_points_no_write_path_is_opened",
    "no_client_has_ever_been_shown_one_byte_of_this_profile",
    "production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false",
    "production_baseline_behavior",
)

DAMAGE_MODEL_NPC_CAPABILITIES = DAMAGE_MODEL_CAPABILITIES + (
    "address_the_hit_entry_at_the_fixed_npc_placement_identity_0x2001",
    "keep_the_players_own_actor_as_performer_for_the_visibility_filter",
    "space_the_frames_fifteen_seconds_apart_so_each_one_can_be_photographed",
)

DAMAGE_MODEL_NPC_NONCLAIMS = DAMAGE_MODEL_NONCLAIMS + (
    "that_0x2001_is_registered_in_the_clients_identity_map_at_runtime_gt_027_tests_exactly_that",
    "what_the_entry_position_field_means_for_a_target_that_is_not_the_performer",
    "that_the_number_if_it_renders_anchors_to_the_npc_rather_than_the_player",
)


# ===========================================================================
# The scenario file.  Compared against an EXACT expected tree.
# ===========================================================================
def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        if not (
            type(expected) is float and type(actual) is int
        ):
            return False
    if type(expected) is dict:
        if set(actual.keys()) != set(expected.keys()):
            return False
        return all(_exact_equal(actual[key], expected[key])
                   for key in expected)
    if type(expected) is list:
        if len(actual) != len(expected):
            return False
        return all(_exact_equal(a, e) for a, e in zip(actual, expected))
    return actual == expected


def _expected_scenario() -> dict[str, Any]:
    return {
        "schema": 1,
        "id": DAMAGE_MODEL_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": DAMAGE_MODEL_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "our_own_formula_not_the_original_servers": True,
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_chit_result_hit_entries_from_our_own_formula"
                "_no_write_no_close"
            ),
        },
        "dispatch": {
            "wired": True,
            "wiring_owner": "damage_dispatch_001_round_90",
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "frames_per_accepted_request": len(DAMAGE_MODEL_STEP_ORDER),
            "step_order": list(DAMAGE_MODEL_STEP_ORDER),
            "miss_steps": list(DAMAGE_MODEL_MISS_STEP_LABELS),
            "spacing_seconds": DAMAGE_MODEL_SPACING_SECONDS,
            "first_frame_delay_seconds": DAMAGE_MODEL_FIRST_DELAY_SECONDS,
            "delay_semantics": (
                "gap_before_each_send_on_a_cumulative_deadline"
            ),
            "action_label_prefix": DAMAGE_MODEL_ACTION_LABEL_PREFIX,
            "action_labels": list(DAMAGE_MODEL_ACTION_LABELS),
            "one_shot": True,
            "socket_action": "none",
        },
        "wire": {
            "envelope_vital_id": RUNTIME_PROTOCOL_RES_ID,
            "envelope_vital_version": RUNTIME_PROTOCOL_RES_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_vitaldata_collection",
            "base_change_mask": BASE_CHANGE_MASK_VITAL_COLLECTION,
            "derived_change_mask": DERIVED_CHANGE_MASK_ABSENT,
            "base_object_offset": 24,
            "chit_result_vital_id": CHIT_RESULT_VITAL_ID,
            "chit_result_vital_version": CHIT_RESULT_VITAL_VERSION,
            "chit_result_vital_version_compare_site": 6242044,
            "chit_result_ctor_version_store_site": 7666041,
            "header_wire_size": CHIT_RESULT_HEADER_WIRE_SIZE,
            "header_reserved_fields": [32, 34, 36, 40],
            "header_reserved_value": HEADER_RESERVED_VALUE,
            "hit_element_stride": HIT_ELEMENT_STRIDE,
            "hit_element_wire_size": HIT_ELEMENT_WIRE_SIZE,
            "hit_entry_count": HIT_ENTRY_COUNT_PINNED,
            "damage_field": {
                "name": "damage_wire",
                "object_offset": HIT_ENTRY_DAMAGE_OFFSET,
                "wire_tag": TAG_U32,
                "width": "i32_read_signed",
                "signed_compare_sites": [
                    7670041, 7670240, 7672345, 7672544,
                ],
                "safe_band": [DAMAGE_WIRE_MIN, DAMAGE_WIRE_MAX],
                "scenario_band": [DAMAGE_WIRE_SCENARIO_MIN, DAMAGE_WIRE_MAX],
            },
            "flag_field": {
                "name": "result_flags",
                "object_offset": HIT_ENTRY_FLAGS_OFFSET,
                "wire_tag": TAG_U16,
                "width": "u16",
                "value_allowlist": list(FLAGS_VALUE_ALLOWLIST_PHASE1),
                "allowed_mask": FLAGS_ALLOWED_MASK_PHASE1,
                "forbidden_mask": FLAGS_FORBIDDEN_MASK,
                "reaction_pass_gate_site": 7670234,
            },
            "yaw_field": {
                "name": "reaction_yaw",
                "object_offset": HIT_ENTRY_YAW_OFFSET,
                "wire_tag": TAG_F32,
                "pinned_value": YAW_PINNED,
                "note": "an_angle_not_a_damage_value",
            },
        },
        "formula": {
            "owner": "this_project_not_the_original_server",
            "deterministic": True,
            "uses_random": False,
            "atk_base": ATK_BASE,
            "k_atk_str": K_ATK_STR,
            "k_atk_lv": K_ATK_LV,
            "def_base": DEF_BASE,
            "k_def_con": K_DEF_CON,
            "k_def_lv": K_DEF_LV,
            "min_hit": MIN_HIT,
            "jitter_pct_max": JITTER_PCT_MAX,
            "input_domain": [FORMULA_INPUT_MIN, FORMULA_INPUT_MAX],
            "defender": {
                "name": DEFENDER_PLAYER_BASELINE.name,
                "level": DEFENDER_PLAYER_BASELINE.level,
                "ability_con": DEFENDER_PLAYER_BASELINE.ability_con,
                "source": "the_character_as_hyp_pf_020_sweep_leaves_it",
            },
            "attackers": {
                "MOB_WEAK": {
                    "level": ATTACKER_MOB_WEAK.level,
                    "ability_str": ATTACKER_MOB_WEAK.ability_str,
                },
                "MOB_STRONG": {
                    "level": ATTACKER_MOB_STRONG.level,
                    "ability_str": ATTACKER_MOB_STRONG.ability_str,
                },
            },
        },
        "target": {
            "rule": "the_players_own_actor_is_both_performer_and_target",
            "reason": (
                "the_only_identity_the_client_is_certain_to_know_in_phase_1"
            ),
            "position_source": "frozen_v135_player_spawn",
            "pins_are_composed_from_a_fixed_probe_identity": True,
            "probe_identity_lo": DAMAGE_PROBE_IDENTITY_LO,
            "probe_identity_hi": DAMAGE_PROBE_IDENTITY_HI,
            "per_step": {
                label: {
                    "damage_wire": DAMAGE_MODEL_PINS[label]["damage_wire"],
                    "flags": DAMAGE_MODEL_PINS[label]["flags"],
                    "pc_size": DAMAGE_MODEL_PINS[label]["pc_size"],
                    "pc_sha256": DAMAGE_MODEL_PINS[label]["pc_sha256"],
                    "frame_size": DAMAGE_MODEL_PINS[label]["frame_size"],
                    "frame_sha256": DAMAGE_MODEL_PINS[label]["frame_sha256"],
                }
                for label in DAMAGE_MODEL_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(DAMAGE_MODEL_CAPABILITIES),
        "nonclaims": list(DAMAGE_MODEL_NONCLAIMS),
    }


def _expected_scenario_npc() -> dict[str, Any]:
    """The EXACT tree of the npc_target opt-in file.

    Built by editing the hit_sweep tree rather than by copying it, so the two
    expectations cannot drift apart on the parts they share: the wire block,
    the formula block and the entry policy are the SAME objects.
    """
    tree = _expected_scenario()
    tree["id"] = DAMAGE_MODEL_NPC_SCENARIO_ID
    tree["dispatch"] = dict(tree["dispatch"])
    tree["dispatch"]["wiring_owner"] = "damage_npc_target_001_round_95"
    tree["dispatch"]["spacing_seconds"] = DAMAGE_MODEL_NPC_SPACING_SECONDS
    tree["dispatch"]["first_frame_delay_seconds"] = (
        DAMAGE_MODEL_NPC_FIRST_DELAY_SECONDS
    )
    tree["dispatch"]["action_label_prefix"] = (
        DAMAGE_MODEL_NPC_ACTION_LABEL_PREFIX
    )
    tree["dispatch"]["action_labels"] = list(DAMAGE_MODEL_NPC_ACTION_LABELS)
    tree["target"] = {
        "rule": (
            "a_fixed_npc_placement_identity_the_client_already_holds"
            "_in_map_data"
        ),
        "reason": (
            "gt_027_asks_whether_0x2001_is_in_the_identity_map_at_runtime"
            "_a_target_the_client_cannot_resolve_is_skipped_silently"
        ),
        "performer_rule": (
            "the_players_own_actor_stays_performer_or_the_visibility"
            "_filter_draws_nothing"
        ),
        "position_source": "frozen_v135_player_spawn",
        "pins_are_composed_from_a_fixed_probe_identity": True,
        "probe_identity_lo": DAMAGE_PROBE_IDENTITY_LO,
        "probe_identity_hi": DAMAGE_PROBE_IDENTITY_HI,
        "npc_target_identity_lo": DAMAGE_NPC_TARGET_IDENTITY_LO,
        "npc_target_identity_hi": DAMAGE_NPC_TARGET_IDENTITY_HI,
        "per_step": {
            label: {
                "damage_wire": DAMAGE_MODEL_PINS_NPC[label]["damage_wire"],
                "flags": DAMAGE_MODEL_PINS_NPC[label]["flags"],
                "pc_size": DAMAGE_MODEL_PINS_NPC[label]["pc_size"],
                "pc_sha256": DAMAGE_MODEL_PINS_NPC[label]["pc_sha256"],
                "frame_size": DAMAGE_MODEL_PINS_NPC[label]["frame_size"],
                "frame_sha256": DAMAGE_MODEL_PINS_NPC[label]["frame_sha256"],
            }
            for label in DAMAGE_MODEL_STEP_ORDER
        },
    }
    tree["capabilities"] = list(DAMAGE_MODEL_NPC_CAPABILITIES)
    tree["nonclaims"] = list(DAMAGE_MODEL_NPC_NONCLAIMS)
    return tree


def load_damage_model_hypothesis_scenario(
    path: Any,
) -> DamageModelHypothesisScenario:
    """Load one of the two opt-in scenario files, or refuse with no lane.

    The file's whole tree decides which profile it is: an exact match against
    the hit_sweep expectation yields the hit_sweep profile, an exact match
    against the npc_target expectation yields the npc_target profile, and
    anything else -- one key added or removed anywhere -- is refused.
    """
    if path is None:
        raise DamageModelValidationError("scenario_file_exceeds_allowlist")
    resolved = Path(path)
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DamageModelValidationError(
            "scenario_file_exceeds_allowlist: %s" % exc
        ) from exc
    if _exact_equal(raw, _expected_scenario()):
        return _PROFILE
    if _exact_equal(raw, _expected_scenario_npc()):
        return _PROFILE_NPC
    raise DamageModelValidationError("scenario_file_exceeds_allowlist")
