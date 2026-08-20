"""DAMAGE-HP-LINK-001: THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS
UNRECOVERABLE.

READ THIS FIRST -- WHOSE ARITHMETIC THIS IS
-------------------------------------------
**Every rule in this module is OURS.**  The original server for this game was
shut down years ago, was never published anywhere, and cannot be recovered.
No capture this project holds shows damage linked to hit points in either
direction, and the round-83 static pass proved the half that matters: **the
client computes nothing and subtracts nothing**.  The number a player sees
floating over an actor is the signed i32 the server placed at hit-entry
``+0x08``, and the HP bar is the u32 the server placed at BasicAttr ``+0x44``;
the client never derives one from the other.  So if hit -> bleed -> die is
ever to happen on a screen, the server has to SAY both halves, and this lane
is the middle piece that says them in ONE linked sweep:

  * the floating damage number rides ``CHitResult`` 0x16F7 version 0 -- the
    exact carrier GT-024 watched render on the player;
  * the shrinking HP bar rides ``UpdateAttrVital`` 0x309A carrying an
    ``ActorAttr`` 0x12AD whose ``hp_current`` is a SERVER-HELD balance -- the
    exact carrier GT-019 watched move the HUD;
  * the ending is the proven dying window: ``hp_current`` at the floor with
    the death timer at the client's own DURATION_DYING value (20.0 s), then
    the pinned elapsed frame (timer 0.0) behind which the client opens
    L"Common_Death" -- the pair GT-019 and GT-023 observed.

THE PLAN -- EIGHT FRAMES, ONE PROFILE
-------------------------------------
The server keeps one integer balance and this module is the only thing that
moves it.  A hit frame ANNOUNCES a number; the hp frame that follows it
APPLIES that same number to the balance and shows the result.  The ladder of
balances after each step is pinned, re-derived by the arithmetic engine on
every composition, and refused on any mismatch:

    HP_BASELINE     balance 100      the byte shape a real client accepted
    HIT_WEAK        damage -63       our formula, MOB_WEAK vs the defender
    HP_AFTER_WEAK   balance 37       100 - 63, applied by the server
    MISS            damage 0         the control frame
    HP_AFTER_MISS   balance 37       a miss moves nothing
    HIT_STRONG      damage -379      our formula, MOB_STRONG vs the defender
    HP_ZERO_DYING   balance 0        37 - 379 clamps at the floor; the same
                                     frame arms the 20.0 s dying timer
    DYING_ELAPSED   balance 0        the pinned elapsed frame, timer 0.0

``MISS`` and ``HP_AFTER_MISS`` are not filler: a sweep in which every frame
lowers the bar cannot tell a tester whether the client is reading our
arithmetic or animating something of its own, so the validator refuses a
sweep without the miss pair.  What the pair PROVES is bounded and written
into the nonclaims: it shows only that OUR arithmetic holds a miss at zero,
not that the client checks any of it.

Spacing is 15.0 s between frames -- the round-84 photography lesson: an
attended tester must be able to photograph every frame without racing their
own capture latency.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is compared against an EXACT allowlist tree -- one extra
  or missing key anywhere and the loader refuses.
* No byte can be composed without the wire unlock token, and the only minter
  of that token takes the allowlisted scenario object, compared by identity.
* The lethal fields -- ``hp_current`` at the floor, or ANY death-timer field
  -- may only be composed for the two step labels the plan declares lethal.
* Every composed sweep is re-read by an independent walker (envelope, both
  vital kinds, and the outer transport frame down to the raw literal) and
  compared against ``DAMAGE_HP_LINK_PINS`` before anything is returned.

WHAT THIS DOES NOT DO
---------------------
It writes nothing: there is no HP column in any table of this project and
this lane does not add one -- the balance lives in this module's arithmetic
for the duration of one sweep and nowhere else.  It claims nothing about the
original server ever linking these two carriers; the link is OUR design.  It
composes nothing for any path OUT of the death window -- what happens after
L"Common_Death" is deliberately outside this lane, and the exit path is not
named, not encoded and not dispatched here.  No client has ever been shown
one byte of this profile; whether the two halves READ as one event on a
screen is the attended lane, not run.
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

DAMAGE_HP_LINK_SCENARIO_ID = "damage_hp_link_hypothesis_link_sweep"
# PF-HYPOTHESIS-LEDGER: HYP-PF-026 active
DAMAGE_HP_LINK_HYPOTHESIS_ID = "HYP-PF-026"
DAMAGE_HP_LINK_DISPATCH_KWARG = "damage_hp_link_hypothesis_scenario"
DAMAGE_HP_LINK_EVENT_NAME = "damage_hp_link_hypothesis_link_sweep_sent"
DAMAGE_HP_LINK_WIRING_OWNER = "damage_hp_link_001_round_97"


class DamageHpLinkValidationError(ValueError):
    """A composed frame or balance move that must never reach a socket."""


# ===========================================================================
# THE ENVELOPE.  The shared GSCN_RunTimeProtocolRes v4 VitalData collection,
# exactly what the frozen V141 helper make_runtime_vitals emits for both of
# the proven carriers this lane links.
# ===========================================================================
RUNTIME_PROTOCOL_RES_VERSION = 4
HP_LINK_BASE_CHANGE_MASK = 0x02       # the VitalData collection at this+0x18
HP_LINK_DERIVED_CHANGE_MASK = 0x00    # no actor-entry collection on this lane
# The frozen V141 transport: u32 magic + u32 length + one raw literal.
HP_LINK_FRAME_MAGIC = 0x5F253EAC

TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32
TAG_ENVELOPE_VERSION = 0x08
TAG_WSTRING = 0x48


# ===========================================================================
# CARRIER ONE: the CHitResult frame.
# Copied, not imported, from the damage-model lane (HYP-PF-024); the drift
# test lives in tests/.  These are facts about the one hash-pinned client
# image, not design choices.
# ===========================================================================
CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0x00
CHIT_RESULT_HEADER_WIRE_SIZE = 22     # qword performer at +0x18 + 4 reserved
HIT_COUNT_WIRE_SIZE = 3
HIT_ELEMENT_WIRE_SIZE = 37            # 9 + 5 + 15 + 5 + 3
HIT_ENTRY_TARGET_OFFSET = 0x00        # tag 0x32 qword
HIT_ENTRY_DAMAGE_OFFSET = 0x08        # tag 0x14 u32 READ SIGNED
HIT_ENTRY_POSITION_OFFSET = 0x0C      # 3x tag 0x2A f32
HIT_ENTRY_YAW_OFFSET = 0x18           # tag 0x2A f32, pinned 0.0
HIT_ENTRY_FLAGS_OFFSET = 0x1C         # tag 0x12 u16
HEADER_RESERVED_VALUE = 0
HIT_ENTRY_COUNT_PINNED = 1
CHIT_RESULT_PAYLOAD_WIRE_SIZE = (
    CHIT_RESULT_HEADER_WIRE_SIZE + HIT_COUNT_WIRE_SIZE + HIT_ELEMENT_WIRE_SIZE
)

# Copied, not imported, from the damage-model lane; drift test lives in
# tests/.  Only the two flag words this plan uses are allowed here.
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
HP_LINK_FLAGS_VALUE_ALLOWLIST = (FLAGS_MISS, FLAGS_HIT)
FLAGS_FORBIDDEN_MASK = 0xF184
FLAGS_BIT_APPLY = 0x0001
YAW_PINNED = 0.0

DAMAGE_WIRE_MAX = 0                   # positive is refused: meaning unknown
DAMAGE_WIRE_MIN = -1_000_000
INT32_MIN = -2147483648


# ===========================================================================
# OUR FORMULA.  Copied, not imported, from the damage-model lane; the drift
# test lives in tests/.  Every number here was chosen by this project.
# ===========================================================================
ATK_BASE = 100
K_ATK_STR = 7
K_ATK_LV = 3
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1

# Copied, not imported, from the damage-model lane (attackers) and from the
# stats-progression lane (the defender's level and constitution, which are on
# screen after GT-017); drift test lives in tests/.
ATTACKER_MOB_WEAK_LEVEL = 1
ATTACKER_MOB_WEAK_ABILITY_STR = 3
ATTACKER_MOB_STRONG_LEVEL = 20
ATTACKER_MOB_STRONG_ABILITY_STR = 40
DEFENDER_LEVEL = 7
DEFENDER_ABILITY_CON = 22

# (level, ability_str) per named attacker.
HP_LINK_ATTACKER_PROFILES = {
    "MOB_WEAK": (ATTACKER_MOB_WEAK_LEVEL, ATTACKER_MOB_WEAK_ABILITY_STR),
    "MOB_STRONG": (ATTACKER_MOB_STRONG_LEVEL, ATTACKER_MOB_STRONG_ABILITY_STR),
}
# The two wire values the formula must reproduce, refused on any mismatch.
HP_LINK_DAMAGE_PINNED = {"MOB_WEAK": -63, "MOB_STRONG": -379}


def compute_hp_link_attack(level: int, ability_str: int) -> int:
    """OUR attack number.  Not the client's, which has none."""
    return ATK_BASE + K_ATK_STR * ability_str + K_ATK_LV * level


def compute_hp_link_defense(level: int, ability_con: int) -> int:
    """OUR defense number."""
    return DEF_BASE + K_DEF_CON * ability_con + K_DEF_LV * level


def compute_hp_link_damage_wire(attacker_name: Any) -> int:
    """OUR damage for one named attacker, as the NEGATIVE wire integer.

    Recomputed from the formula constants on every call and compared against
    the pinned value, so a drifted constant can never ship a frame.
    """
    if attacker_name not in HP_LINK_ATTACKER_PROFILES:
        raise DamageHpLinkValidationError("unknown_step_label")
    level, ability_str = HP_LINK_ATTACKER_PROFILES[attacker_name]
    rolled = compute_hp_link_attack(level, ability_str) - (
        compute_hp_link_defense(DEFENDER_LEVEL, DEFENDER_ABILITY_CON)
    )
    if rolled < MIN_HIT:
        rolled = MIN_HIT
    wire = require_hp_link_damage_wire_value(-rolled)
    if wire != HP_LINK_DAMAGE_PINNED[attacker_name]:
        raise DamageHpLinkValidationError("formula_output_not_reproducible")
    return wire


def require_hp_link_damage_wire_value(value: Any) -> int:
    """Every refusal the signed i32 at +0x08 can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise DamageHpLinkValidationError("damage_not_integer")
    if value > DAMAGE_WIRE_MAX:
        raise DamageHpLinkValidationError(
            "damage_positive_heal_semantics_unknown")
    if value == INT32_MIN:
        raise DamageHpLinkValidationError("damage_is_int32_min")
    if value < DAMAGE_WIRE_MIN:
        raise DamageHpLinkValidationError("damage_below_safe_band")
    return value


def require_hp_link_flags_value(value: Any) -> int:
    """Every refusal the u16 flag word at +0x1C can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise DamageHpLinkValidationError("flags_not_u16")
    if not 0 <= value <= 0xFFFF:
        raise DamageHpLinkValidationError("flags_not_u16")
    if value & FLAGS_FORBIDDEN_MASK:
        raise DamageHpLinkValidationError("flags_forbidden_bit")
    if value not in HP_LINK_FLAGS_VALUE_ALLOWLIST:
        raise DamageHpLinkValidationError("flags_outside_value_allowlist")
    return value


def require_hp_link_damage_and_flags_agree(damage_wire: int, flags: int) -> None:
    """The number and the flag word have to tell the same story."""
    if damage_wire == 0 and flags & FLAGS_BIT_APPLY:
        raise DamageHpLinkValidationError("damage_zero_with_apply_flag")
    if damage_wire != 0 and not flags & FLAGS_BIT_APPLY:
        raise DamageHpLinkValidationError("damage_nonzero_without_apply_flag")


# ===========================================================================
# CARRIER TWO: the ActorAttr delta.
# Copied, not imported, from the stats-progression lane (HYP-PF-020 and its
# HYP-PF-022 lethal tenant); the drift test lives in tests/.  The block order
# is DBAttribute u8 mask + identity qword, then the BasicAttr u16 mask and
# its fields in ascending mask-bit order, then the ActorAttr mask qword, the
# u8 extra-group flag, and the actor fields in ascending mask-bit order.
# ===========================================================================
HP_LINK_UPDATE_ATTR_VITAL_ID = 0x309A
HP_LINK_UPDATE_ATTR_VITAL_VERSION = 0
HP_LINK_ACTOR_ATTR_ID = 0x12AD
HP_LINK_DB_ATTRIBUTE_MASK_TAG = 0x0B
HP_LINK_DB_ATTRIBUTE_IDENTITY_BIT = 0x01
HP_LINK_DB_ATTRIBUTE_IDENTITY_TAG = 0x32
HP_LINK_BASIC_MASK_TAG = 0x12
HP_LINK_ACTOR_MASK_TAG = 0x32
HP_LINK_EXTRA_GROUP_TAG = 0x05
HP_LINK_EXTRA_GROUP_VALUE = 1
# u16tag count (3) + u16tag attr id (3) + u32tag body length (5).
HP_LINK_ATTR_COLLECTION_HEADER_SIZE = 11
HP_LINK_ATTR_COLLECTION_COUNT = 1

HP_LINK_FIELD_KIND_WIDTH = {"u16": 2, "u32": 4, "qword": 8, "f32": 4}
HP_LINK_WSTRING_HEADER_SIZE = 5

HP_LINK_DEATH_TIMER_NAME = "hp_death_timer"


@dataclass(frozen=True)
class HpLinkAttrField:
    """One mask-gated field: block, bit, object offset, wire tag, width."""

    name: str
    block: str
    mask_bit: int
    offset: int
    tag: int
    kind: str


def _ordered(fields: tuple[HpLinkAttrField, ...]) -> tuple[HpLinkAttrField, ...]:
    """Emission order IS ascending mask-bit order (proven in the source lane)."""
    return tuple(sorted(fields, key=lambda field: field.mask_bit))


# Copied, not imported, from the stats-progression lane; drift test lives in
# tests/.  This is the exact field set the proven baseline projection puts on
# the wire, plus the one f32 the dying window reads.
HP_LINK_BASIC_FIELDS = _ordered((
    HpLinkAttrField("hp_current", "basic", 0x0004, 0x44, 0x14, "u32"),
    HpLinkAttrField("hp_max", "basic", 0x0008, 0x48, 0x14, "u32"),
    HpLinkAttrField(HP_LINK_DEATH_TIMER_NAME, "basic", 0x0080, 0x58, 0x2A,
                    "f32"),
    HpLinkAttrField("scene_id", "basic", 0x0100, 0x5C, 0x12, "u16"),
    HpLinkAttrField("scene_sequence", "basic", 0x0200, 0x60, 0x32, "qword"),
))
HP_LINK_ACTOR_FIELDS = _ordered((
    HpLinkAttrField("cash", "actor", 0x00000800, 0xA8, 0x32, "qword"),
    HpLinkAttrField("character_name", "actor", 0x01000000, 0x164, TAG_WSTRING,
                    "wstring"),
))
HP_LINK_FIELD_TABLE = {
    field.name: field
    for field in (*HP_LINK_BASIC_FIELDS, *HP_LINK_ACTOR_FIELDS)
}

# Copied, not imported, from the lethal tenant of the stats-progression lane;
# drift test lives in tests/.  20 is the int compiled into the client image
# for DURATION_DYING; the window opens iff DURATION_DYING - 0.5 <= timer, and
# the elapsed frame must pack to exactly tag 0x2A plus four zero bytes.
HP_LINK_DURATION_DYING_IMAGE_DEFAULT = 20
HP_LINK_DYING_WINDOW_MARGIN = 0.5
HP_LINK_TIMER_ELAPSED_WIRE_BYTES = bytes.fromhex("2a00000000")


# ===========================================================================
# THE BALANCE.  Our numbers, our clamp, our ladder.
# ===========================================================================
HP_LINK_HP_START = 100
HP_LINK_HP_MAX = 100
HP_LINK_HP_FLOOR = 0
HP_LINK_DYING_TIMER_SECONDS = 20.0
HP_LINK_TIMER_ELAPSED_SECONDS = 0.0

# Copied, not imported, from the stats-progression lane's pinned probe
# projection (the canonical smoke character the frozen V25 create wire
# commits); drift test lives in tests/.  Every hp frame carries the FULL
# baseline field set because the client's ActorAttr apply copies the whole
# block -- a sparse two-field delta would zero what it omits.
HP_LINK_BASELINE_SCENE_ID = 1
HP_LINK_BASELINE_SCENE_SEQUENCE = 0
HP_LINK_BASELINE_CHARACTER_NAME = "test01"
HP_LINK_BASELINE_CASH = 10000

# The probe identity the pins are composed from.  Copied, not imported, from
# the neighbouring lanes' shared probe; drift test lives in tests/.
HP_LINK_PROBE_IDENTITY_LO = 0x10010001
HP_LINK_PROBE_IDENTITY_HI = 0

DAMAGE_HP_LINK_SPACING_SECONDS = 15.0   # the round-84 photography lesson
DAMAGE_HP_LINK_FIRST_DELAY_SECONDS = 0.0
DAMAGE_HP_LINK_ACTION_LABEL_PREFIX = "HYP_PF_026_HP_LINK_"

HP_LINK_STEP_KIND_HP = "hp"
HP_LINK_STEP_KIND_HIT = "hit"

# The server-held balance AFTER each step.  A hit frame only ANNOUNCES its
# number; the hp frame that follows it APPLIES the number, which is why the
# ladder holds still on every hit index.  Declared here and re-derived by
# replay_hp_link_balance_ladder on every composition -- any disagreement is
# hp_arithmetic_not_reproducible and no byte leaves.
HP_LINK_BALANCE_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)

# (label, kind, spec, flags): for an "hp" step the spec is the DELTA field
# dict this step adds on top of the running baseline (the same cumulative
# shape the proven lethal lane uses); for a "hit" step the spec is the named
# attacker, or None for the miss control.
DAMAGE_HP_LINK_STEPS = (
    ("HP_BASELINE", HP_LINK_STEP_KIND_HP, {}, None),
    ("HIT_WEAK", HP_LINK_STEP_KIND_HIT, "MOB_WEAK", FLAGS_HIT),
    ("HP_AFTER_WEAK", HP_LINK_STEP_KIND_HP,
     {"hp_current": HP_LINK_BALANCE_LADDER[2]}, None),
    ("MISS", HP_LINK_STEP_KIND_HIT, None, FLAGS_MISS),
    ("HP_AFTER_MISS", HP_LINK_STEP_KIND_HP,
     {"hp_current": HP_LINK_BALANCE_LADDER[4]}, None),
    ("HIT_STRONG", HP_LINK_STEP_KIND_HIT, "MOB_STRONG", FLAGS_HIT),
    ("HP_ZERO_DYING", HP_LINK_STEP_KIND_HP,
     {"hp_current": HP_LINK_HP_FLOOR,
      HP_LINK_DEATH_TIMER_NAME: HP_LINK_DYING_TIMER_SECONDS}, None),
    ("DYING_ELAPSED", HP_LINK_STEP_KIND_HP,
     {HP_LINK_DEATH_TIMER_NAME: HP_LINK_TIMER_ELAPSED_SECONDS}, None),
)
DAMAGE_HP_LINK_STEP_ORDER = tuple(row[0] for row in DAMAGE_HP_LINK_STEPS)
DAMAGE_HP_LINK_ACTION_LABELS = tuple(
    DAMAGE_HP_LINK_ACTION_LABEL_PREFIX + label
    for label in DAMAGE_HP_LINK_STEP_ORDER
)
DAMAGE_HP_LINK_MISS_STEP_LABELS = ("MISS",)
# The only two steps allowed to compose a lethal field, and the only step
# allowed to clamp the balance.
DAMAGE_HP_LINK_LETHAL_STEP_LABELS = ("HP_ZERO_DYING", "DYING_ELAPSED")
DAMAGE_HP_LINK_CLAMP_STEP_LABEL = "HP_ZERO_DYING"
# Which hp step carries which timer value.  Cumulative like the source lane:
# a frame that dropped bit 0x0080 after arming it would PRESERVE the armed
# value in the client (merge copies a clear-bit field forward), so the
# elapsed step carries the bit explicitly with the pinned zero.
DAMAGE_HP_LINK_TIMER_BY_STEP = {
    "HP_ZERO_DYING": HP_LINK_DYING_TIMER_SECONDS,
    "DYING_ELAPSED": HP_LINK_TIMER_ELAPSED_SECONDS,
}


def step_plan(index: Any) -> tuple[str, str, Any, Any]:
    if type(index) is not int or type(index) is bool:
        raise DamageHpLinkValidationError("unknown_step_label")
    if not 0 <= index < len(DAMAGE_HP_LINK_STEPS):
        raise DamageHpLinkValidationError("unknown_step_label")
    return DAMAGE_HP_LINK_STEPS[index]


def step_damage_wire(index: Any) -> int:
    """The number OUR formula produces for one hit step of the plan."""
    _label, kind, spec, _flags = step_plan(index)
    if kind != HP_LINK_STEP_KIND_HIT:
        raise DamageHpLinkValidationError("unknown_step_label")
    if spec is None:
        return 0
    return compute_hp_link_damage_wire(spec)


# ===========================================================================
# THE ARITHMETIC ENGINE.
# ===========================================================================
def apply_hit_to_balance(balance: Any, damage_wire: Any, flags: Any) -> int:
    """Move the server-held balance by one announced hit, or refuse.

    The clamp at the floor is performed here; WHERE clamping is allowed to
    happen is not this function's decision -- replay_hp_link_balance_ladder
    records every clamp and refuses one outside the pinned step.
    """
    if type(balance) is not int or type(balance) is bool:
        raise DamageHpLinkValidationError("hp_balance_not_integer")
    if not HP_LINK_HP_FLOOR <= balance <= HP_LINK_HP_MAX:
        raise DamageHpLinkValidationError("hp_balance_outside_the_declared_band")
    require_hp_link_damage_wire_value(damage_wire)
    require_hp_link_flags_value(flags)
    require_hp_link_damage_and_flags_agree(damage_wire, flags)
    moved = balance + damage_wire
    if moved < HP_LINK_HP_FLOOR:
        moved = HP_LINK_HP_FLOOR
    return moved


def replay_hp_link_balance_ladder() -> tuple[int, ...]:
    """Walk the whole plan through the engine and return the derived ladder.

    A clamp anywhere but the pinned clamp step is refused, and the pinned
    clamp step must actually clamp -- a plan whose strong hit stopped
    clamping would otherwise drift in silence.
    """
    balance = HP_LINK_HP_START
    pending: Any = None
    ladder: list[int] = []
    for label, kind, spec, flags in DAMAGE_HP_LINK_STEPS:
        if kind == HP_LINK_STEP_KIND_HIT:
            if pending is not None:
                raise DamageHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: two hit frames in a "
                    "row leave a number nothing applied"
                )
            damage = 0 if spec is None else compute_hp_link_damage_wire(spec)
            pending = (damage, flags)
        else:
            if pending is not None:
                damage, hit_flags = pending
                moved = apply_hit_to_balance(balance, damage, hit_flags)
                clamped = balance + damage < HP_LINK_HP_FLOOR
                if clamped and label != DAMAGE_HP_LINK_CLAMP_STEP_LABEL:
                    raise DamageHpLinkValidationError(
                        "hp_clamp_outside_the_pinned_step")
                if not clamped and label == DAMAGE_HP_LINK_CLAMP_STEP_LABEL:
                    raise DamageHpLinkValidationError(
                        "hp_clamp_outside_the_pinned_step: the pinned clamp "
                        "step did not clamp"
                    )
                balance = moved
                pending = None
        ladder.append(balance)
    return tuple(ladder)


def require_hp_link_balance_ladder() -> tuple[int, ...]:
    """The declared ladder, or a refusal if the engine cannot reproduce it."""
    derived = replay_hp_link_balance_ladder()
    if derived != HP_LINK_BALANCE_LADDER:
        raise DamageHpLinkValidationError("hp_arithmetic_not_reproducible")
    return derived


def _require_step_plan() -> None:
    """Shape checks on the pinned plan itself, run before any composition."""
    if len(set(DAMAGE_HP_LINK_STEP_ORDER)) != len(DAMAGE_HP_LINK_STEP_ORDER):
        raise DamageHpLinkValidationError("unknown_step_label")
    if len(DAMAGE_HP_LINK_STEPS) != len(HP_LINK_BALANCE_LADDER):
        raise DamageHpLinkValidationError("hp_arithmetic_not_reproducible")
    first_label, first_kind, first_spec, _flags = DAMAGE_HP_LINK_STEPS[0]
    if first_label != "HP_BASELINE" or first_kind != HP_LINK_STEP_KIND_HP:
        raise DamageHpLinkValidationError("unknown_step_label")
    if first_spec != {}:
        raise DamageHpLinkValidationError(
            "lethal_field_outside_the_pinned_step: the baseline must add "
            "no field"
        )
    last_label, last_kind, _spec, _flags = DAMAGE_HP_LINK_STEPS[-1]
    if last_label != "DYING_ELAPSED" or last_kind != HP_LINK_STEP_KIND_HP:
        raise DamageHpLinkValidationError("unknown_step_label")
    miss_labels = []
    for index, (label, kind, spec, flags) in enumerate(DAMAGE_HP_LINK_STEPS):
        if kind == HP_LINK_STEP_KIND_HIT:
            follower = DAMAGE_HP_LINK_STEPS[index + 1]
            if follower[1] != HP_LINK_STEP_KIND_HP:
                raise DamageHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: every hit frame must "
                    "be followed by the hp frame that applies it"
                )
            if spec is None:
                if flags != FLAGS_MISS:
                    raise DamageHpLinkValidationError(
                        "damage_zero_with_apply_flag")
                miss_labels.append(label)
            elif flags != FLAGS_HIT:
                raise DamageHpLinkValidationError(
                    "damage_nonzero_without_apply_flag")
        elif kind != HP_LINK_STEP_KIND_HP:
            raise DamageHpLinkValidationError("unknown_step_label")
    if tuple(miss_labels) != DAMAGE_HP_LINK_MISS_STEP_LABELS:
        raise DamageHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    ladder = require_hp_link_balance_ladder()
    # The declared hp deltas must be the derived balances, so the plan cannot
    # write a bar the arithmetic did not produce.
    for index, (label, kind, spec, _flags) in enumerate(DAMAGE_HP_LINK_STEPS):
        if kind != HP_LINK_STEP_KIND_HP or not spec:
            continue
        declared = spec.get("hp_current")
        if declared is not None and declared != ladder[index]:
            raise DamageHpLinkValidationError("hp_arithmetic_not_reproducible")
    for label in DAMAGE_HP_LINK_LETHAL_STEP_LABELS:
        if label not in DAMAGE_HP_LINK_STEP_ORDER:
            raise DamageHpLinkValidationError("unknown_step_label")
    if DAMAGE_HP_LINK_CLAMP_STEP_LABEL not in DAMAGE_HP_LINK_LETHAL_STEP_LABELS:
        raise DamageHpLinkValidationError("hp_clamp_outside_the_pinned_step")
    if set(DAMAGE_HP_LINK_TIMER_BY_STEP) != set(DAMAGE_HP_LINK_LETHAL_STEP_LABELS):
        raise DamageHpLinkValidationError("lethal_field_outside_the_pinned_step")


# ===========================================================================
# THE UNLOCK.  One token, minted only from the allowlisted scenario object,
# compared by identity everywhere.
# ===========================================================================
@dataclass(frozen=True)
class DamageHpLinkWireUnlock:
    scenario_id: str
    hypothesis_id: str


_UNLOCK = DamageHpLinkWireUnlock(
    DAMAGE_HP_LINK_SCENARIO_ID, DAMAGE_HP_LINK_HYPOTHESIS_ID,
)


@dataclass(frozen=True)
class DamageHpLinkHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str


_PROFILE = DamageHpLinkHypothesisScenario(
    DAMAGE_HP_LINK_SCENARIO_ID,
    DAMAGE_HP_LINK_HYPOTHESIS_ID,
    DAMAGE_HP_LINK_STEP_ORDER,
    DAMAGE_HP_LINK_SPACING_SECONDS,
    DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
    DAMAGE_HP_LINK_ACTION_LABEL_PREFIX,
)


def damage_hp_link_wire_unlock(scenario: Any) -> DamageHpLinkWireUnlock:
    """The ONLY minter.  Requires the allowlisted scenario object ITSELF.

    Identity, not equality: a scenario assembled elsewhere that happens to
    compare equal is still not the one this module ships, and it mints
    nothing.
    """
    require_damage_hp_link_hypothesis_scenario(scenario)
    if scenario is not _PROFILE:
        raise DamageHpLinkValidationError("scenario_object_exceeds_allowlist")
    return _UNLOCK


def require_damage_hp_link_wire_unlock(value: Any) -> DamageHpLinkWireUnlock:
    # Identity, not equality: a forged token that compares equal must not
    # open the lane.
    if value is not _UNLOCK:
        raise DamageHpLinkValidationError(
            "missing_or_forged_wire_unlock: HYP-PF-026 refuses to emit a "
            "byte without the unlock derived from the opt-in scenario"
        )
    return value


def require_damage_hp_link_hypothesis_scenario(
    value: Any,
) -> DamageHpLinkHypothesisScenario:
    if type(value) is not DamageHpLinkHypothesisScenario or value != _PROFILE:
        raise DamageHpLinkValidationError("scenario_object_exceeds_allowlist")
    _require_step_plan()
    return value


# ===========================================================================
# THE ENCODERS.
# ===========================================================================
def _require_identity_pair(identity_lo: Any, identity_hi: Any) -> int:
    for value in (identity_lo, identity_hi):
        if type(value) is not int or type(value) is bool:
            raise DamageHpLinkValidationError("target_identity_outside_qword")
        if not 0 <= value <= 0xFFFFFFFF:
            raise DamageHpLinkValidationError("target_identity_outside_qword")
    return ((identity_hi & 0xFFFFFFFF) << 32) | (identity_lo & 0xFFFFFFFF)


def _require_pinned_position(legacy: Any) -> tuple[float, float, float]:
    """The frozen V135 player spawn -- the same pinned source the proven
    damage-model lane reads.  Nothing here invents a coordinate."""
    position = (
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise DamageHpLinkValidationError(
                "position_not_from_the_pinned_source")
    return position


def _require_pinned_yaw(value: Any) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise DamageHpLinkValidationError("yaw_outside_pinned_value")
    if value != YAW_PINNED:
        raise DamageHpLinkValidationError("yaw_outside_pinned_value")
    return value


def encode_hp_link_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    yaw: float,
    flags: int,
    unlock: Any,
) -> bytes:
    """One 37-byte hit entry, in the proven emission order."""
    require_damage_hp_link_wire_unlock(unlock)
    if type(target_identity) is not int or type(target_identity) is bool:
        raise DamageHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= target_identity <= 0xFFFFFFFFFFFFFFFF:
        raise DamageHpLinkValidationError("target_identity_outside_qword")
    require_hp_link_damage_wire_value(damage_wire)
    require_hp_link_flags_value(flags)
    require_hp_link_damage_and_flags_agree(damage_wire, flags)
    yaw = _require_pinned_yaw(yaw)
    if type(position) is not tuple or len(position) != 3:
        raise DamageHpLinkValidationError("position_not_from_the_pinned_source")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target_identity)
    out += legacy.u32tag(TAG_U32, damage_wire & 0xFFFFFFFF)
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise DamageHpLinkValidationError(
                "position_not_from_the_pinned_source")
        out += legacy.f32tag(component)
    out += legacy.f32tag(yaw)
    out += legacy.u16tag(TAG_U16, flags)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: hit entry is %d bytes"
            % len(out)
        )
    return bytes(out)


def encode_hp_link_chit_result(
    legacy: Any,
    performer_identity: int,
    entries: list[bytes],
    unlock: Any,
) -> bytes:
    """The CHitResult payload: the 22-byte header, then the entry array."""
    require_damage_hp_link_wire_unlock(unlock)
    if type(performer_identity) is not int or type(performer_identity) is bool:
        raise DamageHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= performer_identity <= 0xFFFFFFFFFFFFFFFF:
        raise DamageHpLinkValidationError("target_identity_outside_qword")
    if type(entries) is not list or len(entries) != HIT_ENTRY_COUNT_PINNED:
        raise DamageHpLinkValidationError("entry_count_not_pinned")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer_identity)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: header is %d bytes"
            % len(header)
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise DamageHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: entry width")
        out += entry
    if len(out) != CHIT_RESULT_PAYLOAD_WIRE_SIZE:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: payload is %d bytes"
            % len(out)
        )
    return bytes(out)


def damage_hp_link_baseline_fields(legacy: Any) -> dict[str, Any]:
    """The full baseline field set every hp frame of this lane carries."""
    if legacy.V116_INITIAL_CASH != HP_LINK_BASELINE_CASH:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: baseline cash drift "
            "against the frozen module"
        )
    return {
        "hp_current": HP_LINK_HP_START,
        "hp_max": HP_LINK_HP_MAX,
        "scene_id": HP_LINK_BASELINE_SCENE_ID,
        "scene_sequence": HP_LINK_BASELINE_SCENE_SEQUENCE,
        "cash": legacy.V116_INITIAL_CASH,
        "character_name": HP_LINK_BASELINE_CHARACTER_NAME,
    }


def damage_hp_link_step_fields(legacy: Any, step_index: Any) -> dict[str, Any]:
    """Baseline plus every hp delta up to and including this step.

    Cumulative on purpose, for the byte-proven reason the source lane wrote
    down: the client's ActorAttr apply copies the complete block, so a field
    dropped from a later frame is overwritten, not left alone.
    """
    label, kind, _spec, _flags = step_plan(step_index)
    if kind != HP_LINK_STEP_KIND_HP:
        raise DamageHpLinkValidationError("unknown_step_label")
    require_hp_link_balance_ladder()
    fields = damage_hp_link_baseline_fields(legacy)
    for row_label, row_kind, row_spec, _row_flags in (
        DAMAGE_HP_LINK_STEPS[:step_index + 1]
    ):
        if row_kind == HP_LINK_STEP_KIND_HP:
            fields.update(row_spec)
    return fields


def _require_lethal_window(step_label: str, fields: dict[str, Any]) -> None:
    """The two lethal values may exist only on the two pinned steps."""
    lethal = step_label in DAMAGE_HP_LINK_LETHAL_STEP_LABELS
    if HP_LINK_DEATH_TIMER_NAME in fields and not lethal:
        raise DamageHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if fields.get("hp_current") == HP_LINK_HP_FLOOR and not lethal:
        raise DamageHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if lethal:
        if HP_LINK_DEATH_TIMER_NAME not in fields:
            raise DamageHpLinkValidationError(
                "lethal_field_outside_the_pinned_step: a lethal step must "
                "carry the death timer"
            )
        if fields.get("hp_current") != HP_LINK_HP_FLOOR:
            raise DamageHpLinkValidationError(
                "lethal_field_outside_the_pinned_step: a lethal step must "
                "hold the balance at the floor"
            )


def _encode_hp_link_timer(legacy: Any, field: HpLinkAttrField, value: Any,
                          step_label: str) -> bytes:
    """The one f32 this lane may put at BasicAttr +0x58, per pinned step.

    The discipline is copied from the proven lethal lane: a real float only,
    finite, exactly representable in 32 bits; the dying step must clear the
    death-window gate; the elapsed step must pack to the pinned five bytes
    (negative zero packs differently and is refused)."""
    expected = DAMAGE_HP_LINK_TIMER_BY_STEP.get(step_label)
    if expected is None:
        raise DamageHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if type(value) is not float:
        raise DamageHpLinkValidationError("death_timer_not_float")
    if value != value or value in (float("inf"), float("-inf")):
        raise DamageHpLinkValidationError("death_timer_not_finite")
    if value != expected:
        raise DamageHpLinkValidationError("death_timer_outside_the_pinned_plan")
    encoded = legacy.f32tag(value)
    if len(encoded) != 1 + HP_LINK_FIELD_KIND_WIDTH["f32"] or (
        encoded[0] != field.tag
    ):
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: f32 tag drift")
    if struct.unpack("<f", encoded[1:])[0] != value:
        raise DamageHpLinkValidationError(
            "death_timer_not_exactly_representable")
    if value > 0.0:
        gate = (HP_LINK_DURATION_DYING_IMAGE_DEFAULT
                - HP_LINK_DYING_WINDOW_MARGIN)
        if value < gate:
            raise DamageHpLinkValidationError(
                "death_timer_below_the_death_window_gate")
    elif encoded != HP_LINK_TIMER_ELAPSED_WIRE_BYTES:
        raise DamageHpLinkValidationError(
            "death_timer_elapsed_is_not_the_pinned_zero")
    return encoded


def _encode_hp_link_field(legacy: Any, field: HpLinkAttrField, value: Any,
                          step_label: str) -> bytes:
    if field.kind == "f32":
        return _encode_hp_link_timer(legacy, field, value, step_label)
    if field.kind == "wstring":
        if type(value) is not str or not value:
            raise DamageHpLinkValidationError(
                "character_name_not_two_bytes_per_code_unit")
        raw = value.encode("utf-16le")
        if len(raw) != 2 * len(value):
            raise DamageHpLinkValidationError(
                "character_name_not_two_bytes_per_code_unit")
        return legacy.wstr_tag(value)
    if type(value) is not int or type(value) is bool:
        raise DamageHpLinkValidationError("hp_field_value_not_integer")
    width = HP_LINK_FIELD_KIND_WIDTH[field.kind]
    if value < 0 or value >= (1 << (8 * width)):
        raise DamageHpLinkValidationError("hp_field_value_outside_width")
    if field.kind == "u16":
        return legacy.u16tag(field.tag, value)
    if field.kind == "u32":
        return legacy.u32tag(field.tag, value)
    return legacy.qwordtag(field.tag, value)


def encode_hp_link_actor_attr(
    legacy: Any,
    identity_lo: int,
    identity_hi: int,
    fields: dict[str, Any],
    step_label: str,
    unlock: Any,
) -> bytes:
    """Compose one mask-gated ActorAttr body for one pinned hp step.

    The wire is the proven class chain, base first: the DBAttribute u8 mask
    and identity qword, the BasicAttr u16 mask and its set fields in
    ascending mask-bit order, then the ActorAttr mask qword, the u8
    extra-group flag, and the actor fields.  Unknown names, missing baseline
    names, wrong types, out-of-range values and any lethal value outside the
    pinned window all refuse with no bytes.
    """
    require_damage_hp_link_wire_unlock(unlock)
    identity = _require_identity_pair(identity_lo, identity_hi)
    if type(step_label) is not str or step_label not in DAMAGE_HP_LINK_STEP_ORDER:
        raise DamageHpLinkValidationError("unknown_step_label")
    if type(fields) is not dict:
        raise DamageHpLinkValidationError("hp_field_outside_the_pinned_table")
    unknown = sorted(set(fields) - set(HP_LINK_FIELD_TABLE))
    if unknown:
        raise DamageHpLinkValidationError(
            "hp_field_outside_the_pinned_table: " + unknown[0])
    missing = sorted(
        set(HP_LINK_FIELD_TABLE) - set(fields) - {HP_LINK_DEATH_TIMER_NAME}
    )
    if missing:
        raise DamageHpLinkValidationError(
            "hp_frame_missing_baseline_field: " + missing[0])
    _require_lethal_window(step_label, fields)
    out = bytearray()
    out += legacy.u8tag(HP_LINK_DB_ATTRIBUTE_MASK_TAG,
                        HP_LINK_DB_ATTRIBUTE_IDENTITY_BIT)
    out += legacy.qwordtag(HP_LINK_DB_ATTRIBUTE_IDENTITY_TAG, identity)
    block_mask = 0
    block_body = b""
    for field in HP_LINK_BASIC_FIELDS:
        if field.name not in fields:
            continue
        block_mask |= field.mask_bit
        block_body += _encode_hp_link_field(
            legacy, field, fields[field.name], step_label)
    out += legacy.u16tag(HP_LINK_BASIC_MASK_TAG, block_mask)
    out += block_body
    actor_bits = 0
    actor_body = b""
    for field in HP_LINK_ACTOR_FIELDS:
        if field.name not in fields:
            continue
        actor_bits |= field.mask_bit
        actor_body += _encode_hp_link_field(
            legacy, field, fields[field.name], step_label)
    out += legacy.qwordtag(HP_LINK_ACTOR_MASK_TAG, actor_bits)
    out += legacy.u8tag(HP_LINK_EXTRA_GROUP_TAG, HP_LINK_EXTRA_GROUP_VALUE)
    out += actor_body
    body = bytes(out)
    if _decode_hp_link_attr_body(body) != (identity_lo, identity_hi,
                                           dict(fields)):
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: the encoder is not the "
            "decoder's inverse"
        )
    return body


def make_hp_link_attr_payload(legacy: Any, body: bytes) -> bytes:
    """Wrap one ActorAttr body in the shared Attr-collection payload."""
    if legacy.ACTOR_ATTR != HP_LINK_ACTOR_ATTR_ID:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: ActorAttr id drift "
            "against the frozen module"
        )
    return (
        legacy.u16tag(TAG_U16, HP_LINK_ATTR_COLLECTION_COUNT)
        + legacy.u16tag(TAG_U16, legacy.ACTOR_ATTR)
        + legacy.u32tag(TAG_U32, len(body))
        + body
    )


def _compose_hp_link_runtime_frame(
    legacy: Any, vital_id: int, vital_version: int, payload: bytes,
    unlock: Any,
) -> tuple[bytes, bytes]:
    """The single seam onto the shared envelope helper."""
    require_damage_hp_link_wire_unlock(unlock)
    pc, frame = legacy.make_runtime_vitals(
        [(vital_id, vital_version, payload)]
    )
    if frame != legacy.frame_pc(pc):
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: HYP-PF-026 frame drift")
    return pc, frame


def make_damage_hp_link_step_response(
    legacy: Any,
    performer_identity_lo: int,
    performer_identity_hi: int,
    step_index: int,
    unlock: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the linked sweep, either carrier."""
    require_damage_hp_link_wire_unlock(unlock)
    _require_step_plan()
    identity = _require_identity_pair(
        performer_identity_lo, performer_identity_hi)
    label, kind, spec, flags = step_plan(step_index)
    if kind == HP_LINK_STEP_KIND_HIT:
        # Performer == target: the player is both sides, the same proven
        # ground the damage-model hit_sweep profile stands on.
        entry = encode_hp_link_hit_entry(
            legacy, identity, step_damage_wire(step_index),
            _require_pinned_position(legacy), YAW_PINNED, flags, unlock,
        )
        payload = encode_hp_link_chit_result(legacy, identity, [entry], unlock)
        pc, frame = _compose_hp_link_runtime_frame(
            legacy, CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION,
            payload, unlock,
        )
    else:
        if legacy.UPDATE_ATTR_VITAL != HP_LINK_UPDATE_ATTR_VITAL_ID:
            raise DamageHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: UpdateAttrVital id "
                "drift against the frozen module"
            )
        fields = damage_hp_link_step_fields(legacy, step_index)
        body = encode_hp_link_actor_attr(
            legacy, performer_identity_lo, performer_identity_hi, fields,
            label, unlock,
        )
        payload = make_hp_link_attr_payload(legacy, body)
        pc, frame = _compose_hp_link_runtime_frame(
            legacy, legacy.UPDATE_ATTR_VITAL,
            HP_LINK_UPDATE_ATTR_VITAL_VERSION, payload, unlock,
        )
    _require_probe_pins(
        label, pc, frame, performer_identity_lo, performer_identity_hi)
    return pc, frame


def _require_probe_pins(
    label: str, pc: bytes, frame: bytes, identity_lo: int, identity_hi: int,
) -> None:
    """Sizes for ANY identity; exact bytes for the pinned probe identity."""
    if not DAMAGE_HP_LINK_PINS:
        return
    pin = DAMAGE_HP_LINK_PINS[label]
    if len(pc) != pin["pc_size"] or len(frame) != pin["frame_size"]:
        raise DamageHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: %s size %d/%d != %d/%d"
            % (label, len(pc), len(frame), pin["pc_size"], pin["frame_size"])
        )
    if (identity_lo, identity_hi) != (
        HP_LINK_PROBE_IDENTITY_LO, HP_LINK_PROBE_IDENTITY_HI,
    ):
        return
    for value, key in (
        (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
        (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
    ):
        if value != pin[key]:
            raise DamageHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: probe %s %s %r != %r"
                % (label, key, value, pin[key])
            )


def build_damage_hp_link_sweep(
    legacy: Any,
    performer_identity_lo: int,
    performer_identity_hi: int,
    unlock: Any,
    scenario: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole sweep, then refuse to return it unless it validates.

    The delay is a gap on a cumulative deadline, the same semantics every
    neighbouring lane ships: the first frame carries the first delay and
    each later frame the full spacing.
    """
    scenario = require_damage_hp_link_hypothesis_scenario(scenario)
    require_damage_hp_link_wire_unlock(unlock)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(scenario.step_order):
        pc, frame = make_damage_hp_link_step_response(
            legacy, performer_identity_lo, performer_identity_hi, index,
            unlock,
        )
        delay = (
            scenario.first_delay_seconds if index == 0
            else scenario.spacing_seconds
        )
        actions.append((scenario.action_label_prefix + label, pc, frame, delay))
    validate_damage_hp_link_sweep(actions)
    _require_pinned_probe_composition(legacy, unlock)
    return actions


def _require_pinned_probe_composition(legacy: Any, unlock: Any) -> None:
    """Hold the ENCODER to the pinned bytes on every build.

    A live sweep for a session identity cannot be hashed to a constant, so
    the probe identity is re-composed here on every build and compared to
    the pins -- a drifted encoder therefore cannot ship even once.
    """
    if not DAMAGE_HP_LINK_PINS:
        return
    for index, label in enumerate(DAMAGE_HP_LINK_STEP_ORDER):
        pc, frame = make_damage_hp_link_step_response(
            legacy, HP_LINK_PROBE_IDENTITY_LO, HP_LINK_PROBE_IDENTITY_HI,
            index, unlock,
        )
        pin = DAMAGE_HP_LINK_PINS[label]
        for value, key in (
            (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
            (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
        ):
            if value != pin[key]:
                raise DamageHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: probe %s %s"
                    % (label, key)
                )


# ===========================================================================
# THE INDEPENDENT READER.  Deliberately reuses nothing from the encoders
# except the pinned constants, so a symmetrical bug cannot hide here.  It
# walks from byte 0 and reads BOTH frame kinds, plus the outer transport.
# ===========================================================================
def _scalar(pc: bytes, cursor: int, tag: int, width: int, label: str):
    if cursor + 1 + width > len(pc):
        raise DamageHpLinkValidationError(f"{label}: truncated")
    if pc[cursor] != tag:
        raise DamageHpLinkValidationError(
            "%s: tag 0x%02X != 0x%02X" % (label, pc[cursor], tag))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def decode_hp_link_transport(frame: bytes) -> bytes:
    """Read the outer transport frame back to its PC, byte for byte.

    The frozen framer is u32 magic + u32 body length + ONE raw literal
    stream, so this walker accepts only literal elements and must land
    exactly on the declared uncompressed length.
    """
    if type(frame) is not bytes or len(frame) < 8:
        raise DamageHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != HP_LINK_FRAME_MAGIC:
        raise DamageHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: magic")
    if body_len != len(frame) - 8:
        raise DamageHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length")
    body = frame[8:]
    total = 0
    shift = 0
    cursor = 0
    while True:
        if cursor >= len(body):
            raise DamageHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
        byte = body[cursor]
        cursor += 1
        total |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 28:
            raise DamageHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
    out = bytearray()
    while cursor < len(body):
        tag = body[cursor]
        cursor += 1
        if tag & 0x03:
            raise DamageHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: non-literal")
        code = tag >> 2
        if code <= 59:
            count = code + 1
        else:
            extra = code - 59
            if cursor + extra > len(body):
                raise DamageHpLinkValidationError(
                    "transport_frame_does_not_reproduce_the_pc: truncated")
            count = int.from_bytes(body[cursor:cursor + extra], "little") + 1
            cursor += extra
        if cursor + count > len(body):
            raise DamageHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: truncated")
        out += body[cursor:cursor + count]
        cursor += count
    if len(out) != total:
        raise DamageHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length mismatch")
    return bytes(out)


def _decode_hp_link_attr_body(body: bytes) -> tuple[int, int, dict[str, Any]]:
    """Read one composed ActorAttr body back into (lo, hi, fields)."""
    if type(body) is not bytes or len(body) < 2:
        raise DamageHpLinkValidationError("attr body: truncated")
    cursor = 0
    raw, cursor = _scalar(body, cursor, HP_LINK_DB_ATTRIBUTE_MASK_TAG, 1,
                          "db mask")
    if raw[0] != HP_LINK_DB_ATTRIBUTE_IDENTITY_BIT:
        raise DamageHpLinkValidationError("attr body: db mask bit")
    raw, cursor = _scalar(body, cursor, HP_LINK_DB_ATTRIBUTE_IDENTITY_TAG, 8,
                          "identity")
    identity = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, HP_LINK_BASIC_MASK_TAG, 2,
                          "basic block mask")
    remaining = struct.unpack("<H", raw)[0]
    values: dict[str, Any] = {}
    for field in HP_LINK_BASIC_FIELDS:
        if not remaining & field.mask_bit:
            continue
        remaining &= ~field.mask_bit
        width = HP_LINK_FIELD_KIND_WIDTH[field.kind]
        raw, cursor = _scalar(body, cursor, field.tag, width, field.name)
        if field.kind == "f32":
            values[field.name] = struct.unpack("<f", raw)[0]
        else:
            values[field.name] = int.from_bytes(raw, "little")
    if remaining:
        raise DamageHpLinkValidationError("attr body: unimplemented mask bit")
    raw, cursor = _scalar(body, cursor, HP_LINK_ACTOR_MASK_TAG, 8,
                          "actor block mask")
    remaining = struct.unpack("<Q", raw)[0]
    raw, cursor = _scalar(body, cursor, HP_LINK_EXTRA_GROUP_TAG, 1,
                          "extra group flag")
    if raw[0] != HP_LINK_EXTRA_GROUP_VALUE:
        raise DamageHpLinkValidationError("attr body: extra group flag")
    for field in HP_LINK_ACTOR_FIELDS:
        if not remaining & field.mask_bit:
            continue
        remaining &= ~field.mask_bit
        if field.kind == "wstring":
            if cursor + HP_LINK_WSTRING_HEADER_SIZE > len(body) or (
                body[cursor] != TAG_WSTRING
            ):
                raise DamageHpLinkValidationError("attr body: wstring header")
            byte_length = int.from_bytes(body[cursor + 1:cursor + 5], "little")
            cursor += HP_LINK_WSTRING_HEADER_SIZE
            if byte_length % 2 or cursor + byte_length > len(body):
                raise DamageHpLinkValidationError("attr body: wstring length")
            values[field.name] = body[cursor:cursor + byte_length].decode(
                "utf-16-le")
            cursor += byte_length
        else:
            width = HP_LINK_FIELD_KIND_WIDTH[field.kind]
            raw, cursor = _scalar(body, cursor, field.tag, width, field.name)
            values[field.name] = int.from_bytes(raw, "little")
    if remaining:
        raise DamageHpLinkValidationError("attr body: unimplemented mask bit")
    if cursor != len(body):
        raise DamageHpLinkValidationError("attr body: trailing bytes")
    return identity & 0xFFFFFFFF, (identity >> 32) & 0xFFFFFFFF, values


def decode_damage_hp_link_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back, whichever of the two carriers it holds."""
    if type(pc) is not bytes:
        raise DamageHpLinkValidationError("pc is not bytes")
    cursor = 0
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "envelope id")
    envelope_id = struct.unpack("<H", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "envelope error data")
    error_data = struct.unpack("<I", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_ENVELOPE_VERSION, 1,
                          "envelope version")
    envelope_version = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "base change mask")
    base_mask = raw[0]
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital count")
    vital_count = struct.unpack("<H", raw)[0]
    if vital_count != 1:
        raise DamageHpLinkValidationError("entry_count_not_pinned")
    raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital id")
    vital_id = struct.unpack("<H", raw)[0]
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "vital version")
    vital_version = raw[0]
    result: dict[str, Any] = {
        "envelope_id": envelope_id,
        "error_data": error_data,
        "envelope_version": envelope_version,
        "base_change_mask": base_mask,
        "vital_id": vital_id,
        "vital_version": vital_version,
    }
    if vital_id == CHIT_RESULT_VITAL_ID:
        result["kind"] = HP_LINK_STEP_KIND_HIT
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "performer")
        result["performer_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "header field 2")
        result["header_field2"] = struct.unpack("<H", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "header field 3")
        result["header_field3"] = struct.unpack("<H", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "header field 4")
        result["header_field4"] = struct.unpack("<I", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "header field 5")
        result["header_field5"] = raw[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "hit entry count")
        count = struct.unpack("<H", raw)[0]
        if count != HIT_ENTRY_COUNT_PINNED:
            raise DamageHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "target")
        result["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "damage")
        # Read SIGNED: the client's compare sites make the field mean
        # anything at all only under the signed reading.
        result["damage_wire"] = struct.unpack("<i", raw)[0]
        position = []
        for axis in "xyz":
            raw, cursor = _scalar(pc, cursor, TAG_F32, 4, f"position {axis}")
            position.append(struct.unpack("<f", raw)[0])
        result["position"] = tuple(position)
        raw, cursor = _scalar(pc, cursor, TAG_F32, 4, "yaw")
        result["yaw"] = struct.unpack("<f", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "flags")
        result["flags"] = struct.unpack("<H", raw)[0]
    elif vital_id == HP_LINK_UPDATE_ATTR_VITAL_ID:
        result["kind"] = HP_LINK_STEP_KIND_HP
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "attr count")
        if struct.unpack("<H", raw)[0] != HP_LINK_ATTR_COLLECTION_COUNT:
            raise DamageHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "attr id")
        attr_id = struct.unpack("<H", raw)[0]
        if attr_id != HP_LINK_ACTOR_ATTR_ID:
            raise DamageHpLinkValidationError(
                "the decoder refuses an Attr other than ActorAttr")
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "attr body length")
        body_length = struct.unpack("<I", raw)[0]
        if cursor + body_length > len(pc):
            raise DamageHpLinkValidationError("attr body: truncated")
        body = pc[cursor:cursor + body_length]
        cursor += body_length
        lo, hi, fields = _decode_hp_link_attr_body(body)
        result["identity_lo"] = lo
        result["identity_hi"] = hi
        result["performer_identity"] = (hi << 32) | lo
        result["fields"] = fields
    else:
        raise DamageHpLinkValidationError(
            "the decoder refuses a vital outside the two pinned carriers")
    raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
    result["derived_change_mask"] = raw[0]
    if cursor != len(pc):
        raise DamageHpLinkValidationError(
            "trailing bytes after the derived change mask")
    return result


def validate_damage_hp_link_sweep(
    actions: list[tuple[str, bytes, bytes, float]],
) -> list[dict[str, Any]]:
    """Re-read every composed frame and refuse anything the plan disallows.

    Runs entirely on the bytes: the transport frame is unwrapped by the
    independent walker and must reproduce the PC exactly, both carriers are
    re-decoded from byte 0, the balance ladder is re-derived and compared,
    and the pinned probe identity is held to the exact hashes.
    """
    _require_step_plan()
    ladder = require_hp_link_balance_ladder()
    if type(actions) is not list or len(actions) != len(DAMAGE_HP_LINK_STEPS):
        raise DamageHpLinkValidationError("sweep length is not the pinned plan")
    rows: list[dict[str, Any]] = []
    performers: set[int] = set()
    seen_miss = False
    hit_position_bytes: set[bytes] = set()
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise DamageHpLinkValidationError("sweep action shape")
        label, pc, frame, delay = action
        step_label, kind, spec, plan_flags = DAMAGE_HP_LINK_STEPS[index]
        if label != DAMAGE_HP_LINK_ACTION_LABEL_PREFIX + step_label:
            raise DamageHpLinkValidationError("unknown_step_label")
        if type(pc) is not bytes or type(frame) is not bytes:
            raise DamageHpLinkValidationError("sweep action payload type")
        expected_delay = (
            DAMAGE_HP_LINK_FIRST_DELAY_SECONDS if index == 0
            else DAMAGE_HP_LINK_SPACING_SECONDS
        )
        if type(delay) is not float or delay != expected_delay:
            raise DamageHpLinkValidationError("sweep delay is not the plan")
        if decode_hp_link_transport(frame) != pc:
            raise DamageHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc")
        decoded = decode_damage_hp_link_frame(pc)
        if decoded["envelope_id"] != RUNTIME_PROTOCOL_RES_ID:
            raise DamageHpLinkValidationError("envelope id is not 0x6E9D")
        if decoded["error_data"] != 0:
            raise DamageHpLinkValidationError("envelope error data nonzero")
        if decoded["envelope_version"] != RUNTIME_PROTOCOL_RES_VERSION:
            raise DamageHpLinkValidationError("envelope is not version 4")
        if decoded["base_change_mask"] != HP_LINK_BASE_CHANGE_MASK:
            raise DamageHpLinkValidationError(
                "base change mask does not select the VitalData collection")
        if decoded["derived_change_mask"] != HP_LINK_DERIVED_CHANGE_MASK:
            raise DamageHpLinkValidationError(
                "derived change mask must be absent on this lane")
        if decoded["kind"] != kind:
            raise DamageHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: carrier kind")
        if decoded["vital_version"] != (
            CHIT_RESULT_VITAL_VERSION if kind == HP_LINK_STEP_KIND_HIT
            else HP_LINK_UPDATE_ATTR_VITAL_VERSION
        ):
            raise DamageHpLinkValidationError("vital_version_not_pinned")
        performers.add(decoded["performer_identity"])
        row: dict[str, Any] = {
            "label": step_label,
            "kind": kind,
            "performer_identity": decoded["performer_identity"],
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        if kind == HP_LINK_STEP_KIND_HIT:
            for key in ("header_field2", "header_field3",
                        "header_field4", "header_field5"):
                if decoded[key] != HEADER_RESERVED_VALUE:
                    raise DamageHpLinkValidationError(
                        "header_reserved_field_nonzero")
            if decoded["target_identity"] != decoded["performer_identity"]:
                raise DamageHpLinkValidationError(
                    "performer_identity_not_the_selected_actor")
            require_hp_link_damage_wire_value(decoded["damage_wire"])
            require_hp_link_flags_value(decoded["flags"])
            require_hp_link_damage_and_flags_agree(
                decoded["damage_wire"], decoded["flags"])
            if decoded["damage_wire"] != step_damage_wire(index):
                raise DamageHpLinkValidationError(
                    "formula_output_not_reproducible")
            if decoded["flags"] != plan_flags:
                raise DamageHpLinkValidationError(
                    "flags_outside_value_allowlist")
            if decoded["yaw"] != YAW_PINNED:
                raise DamageHpLinkValidationError("yaw_outside_pinned_value")
            for component in decoded["position"]:
                if not math.isfinite(component):
                    raise DamageHpLinkValidationError(
                        "position_not_from_the_pinned_source")
            hit_position_bytes.add(
                b"".join(struct.pack("<f", value)
                         for value in decoded["position"])
            )
            if decoded["damage_wire"] == 0 and decoded["flags"] == FLAGS_MISS:
                seen_miss = True
            row["damage_wire"] = decoded["damage_wire"]
            row["flags"] = decoded["flags"]
        else:
            fields = decoded["fields"]
            if fields.get("hp_current") != ladder[index]:
                raise DamageHpLinkValidationError(
                    "hp_arithmetic_not_reproducible")
            if fields.get("hp_max") != HP_LINK_HP_MAX:
                raise DamageHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: hp_max")
            if fields.get("scene_id") != HP_LINK_BASELINE_SCENE_ID or (
                fields.get("scene_sequence")
                != HP_LINK_BASELINE_SCENE_SEQUENCE
            ):
                raise DamageHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: scene pair")
            if fields.get("cash") != HP_LINK_BASELINE_CASH:
                raise DamageHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: cash")
            if fields.get("character_name") != (
                HP_LINK_BASELINE_CHARACTER_NAME
            ):
                raise DamageHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: character name")
            timer = fields.get(HP_LINK_DEATH_TIMER_NAME)
            expected_timer = DAMAGE_HP_LINK_TIMER_BY_STEP.get(step_label)
            if timer != expected_timer:
                raise DamageHpLinkValidationError(
                    "lethal_field_outside_the_pinned_step"
                    if expected_timer is None
                    else "death_timer_outside_the_pinned_plan"
                )
            _require_lethal_window(step_label, fields)
            row["hp_current"] = fields["hp_current"]
            row["hp_death_timer"] = timer
        _require_probe_pins(
            step_label, pc, frame,
            decoded["performer_identity"] & 0xFFFFFFFF,
            (decoded["performer_identity"] >> 32) & 0xFFFFFFFF,
        )
        rows.append(row)
    if len(performers) != 1:
        raise DamageHpLinkValidationError(
            "performer_identity_not_the_selected_actor")
    if len(hit_position_bytes) != 1:
        raise DamageHpLinkValidationError("position_not_from_the_pinned_source")
    if not seen_miss:
        raise DamageHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    return rows


# ===========================================================================
# PINS, CAPABILITIES, NONCLAIMS.
# ===========================================================================
# The composed bytes of the PROBE identity, pinned.  Every value here was
# produced by this encoder and read back by the independent walker; none of
# it was copied in from anywhere.  HP_AFTER_WEAK and HP_AFTER_MISS are
# byte-identical on purpose -- the miss control moves nothing, and identical
# bytes are the strongest way to say so.  HP_BASELINE, HP_ZERO_DYING and
# DYING_ELAPSED reproduce the neighbouring lanes' probe pins byte for byte,
# and the three hit frames reproduce the damage-model probe pins byte for
# byte -- the check snippet for this lane diffs all of them.
DAMAGE_HP_LINK_PINS: dict[str, dict[str, Any]] = {
    "HP_BASELINE": {
        "pc_size": 106,
        "pc_sha256": (
            "DB3CE0B5D14196181EF9EA26A0D435E0489212634334CB562F840E368B5F0049"
        ),
        "frame_size": 117,
        "frame_sha256": (
            "04E2B40152B633A48C84713B1C24A2910B7AB84E178E268094C0D10B179D9FBC"
        ),
    },
    "HIT_WEAK": {
        "pc_size": 84,
        "pc_sha256": (
            "D824597F0C9AC24F64BE665699A83FF38A792C3342BCAC70202C3F46B5B584D4"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "D0C0C33C9A3ED9A5C8C1C6BCFBBBFB4762793D053002CD97C9A6C9576C98F999"
        ),
    },
    "HP_AFTER_WEAK": {
        "pc_size": 106,
        "pc_sha256": (
            "EFF10D939CA54436CF3DC3BF6E534BC8599944E83313F0475D14D4D100EFA75E"
        ),
        "frame_size": 117,
        "frame_sha256": (
            "4DEC1F6040A42F3FEF7B9A7EAE519F2B75006AB9217322E2CA088FCBFE2B87CD"
        ),
    },
    "MISS": {
        "pc_size": 84,
        "pc_sha256": (
            "A1A746E4C2D4A35448531FD878E17A93AE5F2FB778C4A343D288D04621EEB77A"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "AC009503A61ACD2ADCB87C93B12A4C96AB1D6FC7F7313163B093158011EF558C"
        ),
    },
    "HP_AFTER_MISS": {
        "pc_size": 106,
        "pc_sha256": (
            "EFF10D939CA54436CF3DC3BF6E534BC8599944E83313F0475D14D4D100EFA75E"
        ),
        "frame_size": 117,
        "frame_sha256": (
            "4DEC1F6040A42F3FEF7B9A7EAE519F2B75006AB9217322E2CA088FCBFE2B87CD"
        ),
    },
    "HIT_STRONG": {
        "pc_size": 84,
        "pc_sha256": (
            "D7A708CBA4642452848D90523852235779D41F8E7869C57F386AE8AC3C285665"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "910669B9029C1E082740BC820BD33E5C1C89E1C2F26924EA2A44FF86C2415FD9"
        ),
    },
    "HP_ZERO_DYING": {
        "pc_size": 111,
        "pc_sha256": (
            "1099931C80FAA0394BE1DADCA587ED890A04ED7C72118F1888D6708CF9967E44"
        ),
        "frame_size": 122,
        "frame_sha256": (
            "77E98AD69434C112FD4D7B6F29B04DCCE306B42187E92B3BDB91383F0C1B200D"
        ),
    },
    "DYING_ELAPSED": {
        "pc_size": 111,
        "pc_sha256": (
            "7C1951CE3090F219D374E19227110E57A40A3EBF3A4EC2A93F139A12718E7F35"
        ),
        "frame_size": 122,
        "frame_sha256": (
            "FE5A6D9B05FC4ECE72C0D066D1AAF373B8C4D5269D8594EA182E6AAB60EA0CD4"
        ),
    },
}


DAMAGE_HP_LINK_CAPABILITIES = (
    "run_our_damage_arithmetic_against_a_server_held_hp_balance",
    "emit_the_floating_number_and_the_shrinking_hp_bar_for_one_client",
    "link_the_two_proven_carriers_chitresult_and_updateattrvital_in_one_sweep",
    "clamp_the_balance_at_the_floor_on_exactly_one_pinned_step",
    "end_in_the_proven_dying_window_and_the_pinned_elapsed_frame",
    "refuse_every_value_whose_client_meaning_this_project_cannot_name",
)

DAMAGE_HP_LINK_NONCLAIMS = (
    "this_is_our_design_not_the_original_servers_which_is_unrecoverable",
    "no_capture_shows_damage_linked_to_hit_points_in_either_direction",
    "the_client_does_not_subtract_damage_that_is_why_the_server_must_say_both_halves",
    "no_claim_the_original_server_ever_linked_these_frames",
    "no_database_write_no_hp_column_exists_and_none_is_added",
    "wire_and_dispatch_layer_only_no_client_has_seen_these_bytes",
    "one_shot_per_process",
    "no_claim_about_any_death_window_exit_path",
    "miss_control_proves_only_that_our_arithmetic_holds_not_that_the_client_checks_it",
    "production_dispatch_wiring_the_wiring_is_opt_in_and_production_allowed_is_false",
    "production_baseline_behavior",
)


# ===========================================================================
# THE SCENARIO FILE.  Compared against an EXACT expected tree.
# ===========================================================================
def _exact_equal(actual: Any, expected: Any) -> bool:
    if type(actual) is not type(expected):
        if not (type(expected) is float and type(actual) is int):
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
        "id": DAMAGE_HP_LINK_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": DAMAGE_HP_LINK_HYPOTHESIS_ID,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "design_not_recovery": (
            "this_is_our_design_not_the_original_servers_which_is_"
            "unrecoverable"
        ),
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_linked_damage_and_hp_frames_from_our_own_arithmetic"
                "_no_write_no_close"
            ),
        },
        "dispatch": {
            "wired": True,
            "wiring_owner": DAMAGE_HP_LINK_WIRING_OWNER,
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "frames_per_accepted_request": len(DAMAGE_HP_LINK_STEP_ORDER),
            "step_order": list(DAMAGE_HP_LINK_STEP_ORDER),
            "spacing_seconds": DAMAGE_HP_LINK_SPACING_SECONDS,
            "first_frame_delay_seconds": DAMAGE_HP_LINK_FIRST_DELAY_SECONDS,
            "delay_semantics": (
                "gap_before_each_send_on_a_cumulative_deadline"
            ),
            "action_label_prefix": DAMAGE_HP_LINK_ACTION_LABEL_PREFIX,
            "action_labels": list(DAMAGE_HP_LINK_ACTION_LABELS),
            "one_shot": True,
            "socket_action": "none",
        },
        "wire": {
            "envelope_vital_id": RUNTIME_PROTOCOL_RES_ID,
            "envelope_vital_version": RUNTIME_PROTOCOL_RES_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_vitaldata_collection",
            "base_change_mask": HP_LINK_BASE_CHANGE_MASK,
            "derived_change_mask": HP_LINK_DERIVED_CHANGE_MASK,
            "chit_result_vital_id": CHIT_RESULT_VITAL_ID,
            "chit_result_vital_version": CHIT_RESULT_VITAL_VERSION,
            "header_wire_size": CHIT_RESULT_HEADER_WIRE_SIZE,
            "header_reserved_value": HEADER_RESERVED_VALUE,
            "hit_element_wire_size": HIT_ELEMENT_WIRE_SIZE,
            "hit_entry_count": HIT_ENTRY_COUNT_PINNED,
            "damage_field": {
                "name": "damage_wire",
                "object_offset": HIT_ENTRY_DAMAGE_OFFSET,
                "wire_tag": TAG_U32,
                "width": "i32_read_signed",
                "safe_band": [DAMAGE_WIRE_MIN, DAMAGE_WIRE_MAX],
            },
            "flag_field": {
                "name": "result_flags",
                "object_offset": HIT_ENTRY_FLAGS_OFFSET,
                "wire_tag": TAG_U16,
                "width": "u16",
                "value_allowlist": list(HP_LINK_FLAGS_VALUE_ALLOWLIST),
                "forbidden_mask": FLAGS_FORBIDDEN_MASK,
            },
            "yaw_field": {
                "name": "reaction_yaw",
                "object_offset": HIT_ENTRY_YAW_OFFSET,
                "wire_tag": TAG_F32,
                "pinned_value": YAW_PINNED,
            },
            "update_attr_vital_id": HP_LINK_UPDATE_ATTR_VITAL_ID,
            "update_attr_vital_version": HP_LINK_UPDATE_ATTR_VITAL_VERSION,
            "actor_attr_id": HP_LINK_ACTOR_ATTR_ID,
            "attr_collection": (
                "tag12_u16_count_tag12_u16_attr_id_tag14_u32_length_then_body"
            ),
            "field_order_rule": "ascending_mask_bit_within_each_block",
            "extra_group_flag_value": HP_LINK_EXTRA_GROUP_VALUE,
            "hp_fields": {
                field.name: {
                    "mask_bit": field.mask_bit,
                    "object_offset": field.offset,
                    "wire_tag": field.tag,
                    "width": field.kind,
                }
                for field in (*HP_LINK_BASIC_FIELDS, *HP_LINK_ACTOR_FIELDS)
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
                "defender": {
                    "name": "PLAYER_BASELINE",
                    "level": DEFENDER_LEVEL,
                    "ability_con": DEFENDER_ABILITY_CON,
                },
                "attackers": {
                    "MOB_WEAK": {
                        "level": ATTACKER_MOB_WEAK_LEVEL,
                        "ability_str": ATTACKER_MOB_WEAK_ABILITY_STR,
                    },
                    "MOB_STRONG": {
                        "level": ATTACKER_MOB_STRONG_LEVEL,
                        "ability_str": ATTACKER_MOB_STRONG_ABILITY_STR,
                    },
                },
            },
            "hp_ladder": {
                "start": HP_LINK_HP_START,
                "max": HP_LINK_HP_MAX,
                "floor": HP_LINK_HP_FLOOR,
                "ladder": list(HP_LINK_BALANCE_LADDER),
                "clamp_step": DAMAGE_HP_LINK_CLAMP_STEP_LABEL,
                "applies_on": "the_hp_frame_that_follows_each_hit_frame",
            },
            "timer": {
                "name": HP_LINK_DEATH_TIMER_NAME,
                "dying_seconds": HP_LINK_DYING_TIMER_SECONDS,
                "elapsed_seconds": HP_LINK_TIMER_ELAPSED_SECONDS,
                "duration_dying_image_default": (
                    HP_LINK_DURATION_DYING_IMAGE_DEFAULT
                ),
                "window_margin_seconds": HP_LINK_DYING_WINDOW_MARGIN,
                "elapsed_wire_bytes": HP_LINK_TIMER_ELAPSED_WIRE_BYTES.hex(),
            },
        },
        "probe": {
            "rule": "the_players_own_actor_is_both_performer_and_target",
            "position_source": "frozen_v135_player_spawn",
            "pins_are_composed_from_a_fixed_probe_identity": True,
            "identity_lo": HP_LINK_PROBE_IDENTITY_LO,
            "identity_hi": HP_LINK_PROBE_IDENTITY_HI,
            "per_step": {
                label: {
                    "pc_size": DAMAGE_HP_LINK_PINS[label]["pc_size"],
                    "pc_sha256": DAMAGE_HP_LINK_PINS[label]["pc_sha256"],
                    "frame_size": DAMAGE_HP_LINK_PINS[label]["frame_size"],
                    "frame_sha256": DAMAGE_HP_LINK_PINS[label]["frame_sha256"],
                }
                for label in DAMAGE_HP_LINK_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(DAMAGE_HP_LINK_CAPABILITIES),
        "nonclaims": list(DAMAGE_HP_LINK_NONCLAIMS),
    }


def load_damage_hp_link_hypothesis_scenario(
    path: Any,
) -> DamageHpLinkHypothesisScenario:
    """Load the one opt-in scenario file, or refuse with no lane."""
    if path is None:
        raise DamageHpLinkValidationError("scenario_file_exceeds_allowlist")
    resolved = Path(path)
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise DamageHpLinkValidationError(
            "scenario_file_exceeds_allowlist: %s" % exc
        ) from exc
    if _exact_equal(raw, _expected_scenario()):
        return _PROFILE
    raise DamageHpLinkValidationError("scenario_file_exceeds_allowlist")
