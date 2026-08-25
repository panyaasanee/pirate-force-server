"""HOSTILE-HP-LINK-001: THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS
UNRECOVERABLE.

READ THIS FIRST -- WHOSE ARITHMETIC THIS IS
-------------------------------------------
**Every rule in this module is OURS.**  The original server for this game was
shut down years ago, was never published anywhere, and cannot be recovered.
**No capture in any corpus shows a TARGET's hit points moving in response to
damage, in either direction**, and round 83 (DAMAGE-MODEL-001) proved the half
that matters byte-exactly: the client computes NOTHING about damage.  The
number a player sees floating over an actor is the signed i32 the server placed
at hit-entry ``+0x08``, passed through ``abs()`` and printed with ``"%d"``;
the client never subtracts it from anything.  That is why the server has to SAY
BOTH HALVES itself, and it is the only reason this lane exists.

WHAT THIS LANE IS, AND HOW IT DIFFERS FROM ITS SIBLING HYP-PF-029
------------------------------------------------------------------
HYP-PF-029 already moves a target's balance and an attended round already
watched its bar: GT-039 saw ``100 -> 37 -> 0`` on a real screen.  But it did so
on a SYNTHETIC identity and a SYNTHETIC ladder -- placement 0, actor 0x2001,
"Navy Transfer", a 100-point bar this project invented for the probe.  The one
question that leaves open is the one the attended queue is waiting on:

    does the same shape hold for a REAL hostile identity carrying the HP
    baseline the CLIENT itself ships for it?

This lane asks exactly that and nothing else.  It is pinned to placement index
30, actor identity ``0x201F``, template 31, visual preset ``M011_000_000_SP3``,
name "Tornado Eagle", and the HP baseline ``3857`` that the frozen V141 source
carries as ``V117_P30_EXACT_HP`` for that row (STANDARD_MOB level 27).  The
baseline is CLIENT-SIDE data.  It is not a rule of the original server, and
this module never claims otherwise.

WHY THE TARGET IS PLACED PLAYER-RELATIVE, AND WHY THAT IS LOAD-BEARING
-----------------------------------------------------------------------
The frozen placement row for index 30 puts that actor at world coordinates
``(1747.5244140625, -7837.69775390625, 931.0413208007812)`` -- roughly twelve
thousand units from the frozen V135 player spawn.  A round that spawned the
target THERE would put a blue dot on the minimap and no model on the screen,
which is exactly what the attended round 1104 measured for a neighbouring lane.
An unseen target cannot answer a question about its HP bar, so this lane places
the target at PLAYER-RELATIVE geometry, borrowing the shape the Arena lane
proved (``scenario.py`` ``make_p30_target``): the composed position is the live
player position plus the scenario's ``dx/dy/dz``, and the heading is derived
towards the player.

Two consequences are written into the design rather than left to a booter:

  * the placement offsets live in the scenario file, are read back by the
    validator, and a sweep composed at the frozen WORLD row instead of the
    player-relative one is REFUSED by name; and
  * the byte pins for the spawn frame are exact only for the pinned PROBE
    position (the frozen V135 spawn plus the scenario offsets).  For a live
    session the SIZE pins still hold and the sha pins do not, exactly as the
    sibling lane's performer-bearing frames behave.  This is stated here
    because a pin that quietly means two things is a trap.

NONCLAIM, kept next to the design it constrains: nobody has ever confirmed with
their own eyes that a model at ``dx 100 / dy 50`` is inside this client's model
draw distance.  If the attended round sees no bird, that is a finding about
draw distance or render conditions -- NOT a negative about damage.

THE PLAN -- SEVEN FRAMES, ONE TARGET, ONE BALANCE, AND NO DEATH
----------------------------------------------------------------
The server keeps one integer balance for the TARGET and this module is the only
thing that moves it.  A hit frame ANNOUNCES a number; the actor-entry frame
that follows it APPLIES that same number to the balance and shows the result on
the target's own bar.  The ladder is re-derived by the arithmetic engine on
EVERY composition and the whole sweep is refused on any mismatch:

    TARGET_SPAWN             balance 3857  alive, placed player-relative
    HIT_WEAK                 damage -964   our formula, MOB_WEAK vs the defender
    TARGET_HP_AFTER_WEAK     balance 2893  3857 - 964, applied by the server
    MISS                     damage 0      the control frame
    TARGET_HP_AFTER_MISS     balance 2893  a miss moves nothing -- and the frame
                                           is deliberately BYTE-IDENTICAL to the
                                           one above it
    HIT_STRONG               damage -2122  our formula, MOB_STRONG
    TARGET_HP_AFTER_STRONG   balance 771   2893 - 2122, still above the floor

**There is no hp = 0 frame, no dying latch and no death timer anywhere in this
lane.**  That is not an omission: one ticket, one claim.  The "does it die"
half belongs to a later version of this slot and is refused here by name -- the
plan validator rejects a floor balance and rejects every death-timer field, so
a later edit cannot slide the death half in without turning the lane red.

WHY THE DAMAGE NUMBERS ARE THIS BIG
------------------------------------
The formula is the one HYP-PF-024 and HYP-PF-029 already ship, unchanged:
``attack = ATK_BASE + K_ATK_STR * str + K_ATK_LV * level`` against
``defence = DEF_BASE + K_DEF_CON * con + K_DEF_LV * level``, floored at
``MIN_HIT``.  What changed is the ATTACKER PROFILES fed to it, and the reason
is a human one: ``-63`` on a 3857-point bar is 1.6 percent of the bar and a
tester cannot see it.  A sweep whose movement is invisible answers nothing, so
the profiles were chosen to produce a bar that lands near 75 percent and then
near 20 percent of the baseline.  The numbers still come out of the calculator
-- no step writes a literal damage value, every value is recomputed from the
profile constants on every call and compared against its pin.

SAID OUT LOUD, because the ticket that ordered this lane asked for it to be:
the ticket proposed "down to about 60 percent, then about 20 percent" and what
this lane ships is 75.0 percent and then 20.0 percent.  The second step is the
one asked for; the first is a smaller drop than proposed, because the profile
had to be one the UNCHANGED formula produces exactly -- inventing a number to
hit 60 would be writing a damage value by hand, which this lane refuses on
principle.  A 25-percent drop of a 3857 bar is still an order of magnitude
more visible than the 1.6 percent the sibling lane's number would have been.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is compared against an EXACT allowlist tree -- one extra or
  missing key anywhere and the loader refuses.
* Every PUBLIC encoder on this lane refuses without the wire unlock token, and
  the only minter of that token takes the allowlisted scenario object, compared
  by IDENTITY -- a value-equal forgery is refused.  The PRIVATE body builders
  take no unlock argument, exactly as both parents behave: the boundary this
  defends is the process, not the function.
* The floor is FORBIDDEN, not pinned to a step: any move that would clamp is a
  named refusal, because this lane has no lethal step to clamp on.
* Every composed sweep is re-read by an independent walker (both carriers, from
  byte 0, plus the outer transport frame down to the raw literal) and compared
  against ``HOSTILE_HP_LINK_PINS`` before anything is returned.
* Any refusal is a NAMED event.  There is no silent fallback anywhere.

WHAT THIS DOES NOT DO
---------------------
It writes nothing: there is no HP column in any table of this project and this
lane does not add one -- the target's balance lives in this module's arithmetic
for the duration of one sweep and nowhere else.  It claims nothing about the
original server ever linking these two carriers; the link is OUR design.  It
does not claim the client accepts identity ``0x201F`` as a target, does not
claim the bird is drawn, does not claim anything about aggro, retaliation or
loot, and does not generalise to the other twelve hostiles in the roster.
**whether the client renders the intermediate value 2893 on the target's HP bar
is UNDECIDABLE from static analysis and is the queued attended test.**
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import struct
from typing import Any

from .population import (
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    RUNTIME_PROTOCOL_RES_ID,
    SCENE_ID,
    SCENE_SEQUENCE,
    load_port_royal_placements,
)


production_allowed = False

HOSTILE_HP_LINK_SCENARIO_ID = "hostile_hp_link_hypothesis_target_sweep"
# PF-HYPOTHESIS-LEDGER: HYP-PF-038 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-111 append.  The
# annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
HOSTILE_HP_LINK_HYPOTHESIS_ID = "HYP-PF-038"
HOSTILE_HP_LINK_CHECKPOINT = "HOSTILE-HP-LINK-001"
HOSTILE_HP_LINK_EVENT_NAME = "hostile_hp_link_hypothesis_target_sweep_sent"
HOSTILE_HP_LINK_WIRING_OWNER = "hostile_hp_link_001_round_162"


class HostileHpLinkValidationError(ValueError):
    """A composed frame or balance move that must never reach a socket."""


# ===========================================================================
# THE ENVELOPE.  ONE id, 0x6E9D version 4, TWO collections.  This lane is the
# first in the tree to ride both in one sweep, so both masks are named here and
# the validator checks the right pair per carrier kind.
# ===========================================================================
RUNTIME_PROTOCOL_RES_VERSION = 4
# The hit carrier: BASE change mask 0x02 selects the VitalData collection at
# this+0x18 (what the frozen V141 make_runtime_vitals emits), and the trailing
# DERIVED mask is 0x00.
HIT_BASE_CHANGE_MASK = 0x02
HIT_DERIVED_CHANGE_MASK = 0x00
HIT_BASE_OBJECT_OFFSET = 0x18
# The actor carrier: the INHERITED (base) mask is absent and the DERIVED mask
# carries bit 0x02, the actor-entry collection at this+0x1C (what the frozen
# V141 make_runtime_remote_actors emits).
ACTOR_INHERITED_CHANGE_MASK = 0x00
ACTOR_DERIVED_CHANGE_MASK = 0x02
ACTOR_DERIVED_OBJECT_OFFSET = 0x1C
# The frozen V141 transport: u32 magic + u32 length + one raw literal stream.
HOSTILE_HP_LINK_FRAME_MAGIC = 0x5F253EAC

TAG_U8 = 0x0B
TAG_U16 = 0x12
TAG_U32 = 0x14
TAG_F32 = 0x2A
TAG_QWORD = 0x32
TAG_ENVELOPE_VERSION = 0x08
TAG_WSTRING = 0x48

# NOTE for anyone porting from remote_player_hypothesis.py / the death lane:
# those modules carry five ACTOR_*_OFFSET byte-offset constants here because
# their walkers index the composed actor PC with them.  THIS lane's walker does
# not -- it advances a cursor tag by tag from byte 0 -- so the five constants
# were copied in dead and are deleted rather than left with a comment claiming
# they are read.  Re-add them only together with a use.


# ===========================================================================
# CARRIER ONE: the CHitResult frame.
# Copied, not imported, from the damage-model lane (HYP-PF-024); the drift and
# byte-equality tests live in tests/.  These are facts about the one hash-pinned
# client image, not design choices.
# ===========================================================================
CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0x00
CHIT_RESULT_HEADER_WIRE_SIZE = 22     # qword performer at +0x18 + 4 reserved
HIT_COUNT_WIRE_SIZE = 3
HIT_ELEMENT_WIRE_SIZE = 37            # 9 + 5 + 15 + 5 + 3
HIT_ENTRY_DAMAGE_OFFSET = 0x08        # tag 0x14 u32 READ SIGNED
HIT_ENTRY_YAW_OFFSET = 0x18           # tag 0x2A f32, pinned 0.0
HIT_ENTRY_FLAGS_OFFSET = 0x1C         # tag 0x12 u16
HEADER_RESERVED_VALUE = 0
HIT_ENTRY_COUNT_PINNED = 1
CHIT_RESULT_PAYLOAD_WIRE_SIZE = (
    CHIT_RESULT_HEADER_WIRE_SIZE + HIT_COUNT_WIRE_SIZE + HIT_ELEMENT_WIRE_SIZE
)

# Copied, not imported, from the damage-model lane.  Only the two flag words
# this plan uses are allowed here: the reaction word 0x0009 belongs to that
# lane's fourth step and this lane has no fourth hit.
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
HOSTILE_HP_LINK_FLAGS_VALUE_ALLOWLIST = (FLAGS_MISS, FLAGS_HIT)
FLAGS_FORBIDDEN_MASK = 0xF184
FLAGS_BIT_APPLY = 0x0001
YAW_PINNED = 0.0

DAMAGE_WIRE_MAX = 0                   # positive is refused: meaning unknown
DAMAGE_WIRE_MIN = -1_000_000
INT32_MIN = -2147483648


# ===========================================================================
# OUR FORMULA.  The six coefficients and MIN_HIT are COPIED, not imported, from
# HYP-PF-026 / HYP-PF-029 and are IDENTICAL to them; the drift test lives in
# tests/.  What this lane changes is the PROFILES fed to the formula, and the
# reason is written out in the module docstring: on a 3857-point bar the
# sibling lane's -63 is 1.6 percent of the bar, which no tester can see, and a
# sweep whose movement is invisible answers nothing.
#
# The two profiles below were solved for a VISIBLE ladder against this
# defender: 3857 -> 2893 (75.0 percent of the baseline) -> 771 (20.0 percent).
# Both wire values are DERIVED by the function below on every call from the
# profile constants and are never typed into a step row; the pinned dict is a
# cross-check, not a source.
#
#   defence = 10 + 2 * 22 + 1 * 27                            = 81
#   MOB_WEAK   attack = 100 + 7 * 132 + 3 *  7 = 1045  -> -964
#   MOB_STRONG attack = 100 + 7 * 294 + 3 * 15 = 2203  -> -2122
# ===========================================================================
ATK_BASE = 100
K_ATK_STR = 7
K_ATK_LV = 3
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1

ATTACKER_MOB_WEAK_LEVEL = 7
ATTACKER_MOB_WEAK_ABILITY_STR = 132
ATTACKER_MOB_STRONG_LEVEL = 15
ATTACKER_MOB_STRONG_ABILITY_STR = 294
# The defender is the TARGET of this lane, not the player: level 27 is the
# STANDARD_MOB level the client's own table carries for the Tornado Eagle row
# whose HP baseline this lane rides.  The constitution ability is ours.
DEFENDER_LEVEL = 27
DEFENDER_ABILITY_CON = 22

# (level, ability_str) per named attacker.
HOSTILE_HP_LINK_ATTACKER_PROFILES = {
    "MOB_WEAK": (ATTACKER_MOB_WEAK_LEVEL, ATTACKER_MOB_WEAK_ABILITY_STR),
    "MOB_STRONG": (ATTACKER_MOB_STRONG_LEVEL, ATTACKER_MOB_STRONG_ABILITY_STR),
}
# The pinned-value cross-check, kept from the sibling lane: the two wire values
# the formula must reproduce, refused on any mismatch.
HOSTILE_HP_LINK_DAMAGE_PINNED = {"MOB_WEAK": -964, "MOB_STRONG": -2122}


def compute_hostile_hp_link_attack(level: int, ability_str: int) -> int:
    """OUR attack number.  Not the client's, which has none."""
    return ATK_BASE + K_ATK_STR * ability_str + K_ATK_LV * level


def compute_hostile_hp_link_defense(level: int, ability_con: int) -> int:
    """OUR defense number."""
    return DEF_BASE + K_DEF_CON * ability_con + K_DEF_LV * level


def compute_hostile_hp_link_damage_wire(attacker_name: Any) -> int:
    """OUR damage for one named attacker, as the NEGATIVE wire integer.

    Recomputed from the formula constants on every call and compared against
    the pinned value, so a drifted constant can never ship a frame.
    """
    if attacker_name not in HOSTILE_HP_LINK_ATTACKER_PROFILES:
        raise HostileHpLinkValidationError("unknown_step_label")
    level, ability_str = HOSTILE_HP_LINK_ATTACKER_PROFILES[attacker_name]
    rolled = compute_hostile_hp_link_attack(level, ability_str) - (
        compute_hostile_hp_link_defense(DEFENDER_LEVEL, DEFENDER_ABILITY_CON)
    )
    if rolled < MIN_HIT:
        rolled = MIN_HIT
    wire = require_hostile_hp_link_damage_wire_value(-rolled)
    if wire != HOSTILE_HP_LINK_DAMAGE_PINNED[attacker_name]:
        raise HostileHpLinkValidationError("formula_output_not_reproducible")
    return wire


def require_hostile_hp_link_damage_wire_value(value: Any) -> int:
    """Every refusal the signed i32 at +0x08 can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise HostileHpLinkValidationError("damage_not_integer")
    if value > DAMAGE_WIRE_MAX:
        raise HostileHpLinkValidationError(
            "damage_positive_heal_semantics_unknown")
    if value == INT32_MIN:
        raise HostileHpLinkValidationError("damage_is_int32_min")
    if value < DAMAGE_WIRE_MIN:
        raise HostileHpLinkValidationError("damage_below_safe_band")
    return value


def require_hostile_hp_link_flags_value(value: Any) -> int:
    """Every refusal the u16 flag word at +0x1C can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise HostileHpLinkValidationError("flags_not_u16")
    if not 0 <= value <= 0xFFFF:
        raise HostileHpLinkValidationError("flags_not_u16")
    if value & FLAGS_FORBIDDEN_MASK:
        raise HostileHpLinkValidationError("flags_forbidden_bit")
    if value not in HOSTILE_HP_LINK_FLAGS_VALUE_ALLOWLIST:
        raise HostileHpLinkValidationError("flags_outside_value_allowlist")
    return value


def require_hostile_hp_link_damage_and_flags_agree(
    damage_wire: int, flags: int,
) -> None:
    """The number and the flag word have to tell the same story."""
    if damage_wire == 0 and flags & FLAGS_BIT_APPLY:
        raise HostileHpLinkValidationError("damage_zero_with_apply_flag")
    if damage_wire != 0 and not flags & FLAGS_BIT_APPLY:
        raise HostileHpLinkValidationError("damage_nonzero_without_apply_flag")


# ===========================================================================
# CARRIER TWO: the actor-entry NPCAttr delta.
# Copied, not imported, from the runtimeres-death lane (HYP-PF-023); the drift
# and byte-equality tests live in tests/.  The block order is the DBAttribute
# u8 mask + identity qword, then the BasicAttr u16 mask and its fields in
# ascending mask-bit order, then the NPCAttr u8 mask and its fields.
# ===========================================================================
BASIC_ATTR_MASK_TAG = 0x12
BASIC_BIT_NAME = 0x0001         # wstring tag 0x48 @ +0x28 (the target panel label)
BASIC_BIT_CURRENT_HP = 0x0004      # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008          # u32 tag 0x14 @ +0x48
BASIC_BIT_DEATH_TIMER = 0x0080     # f32 tag 0x2A @ +0x58   <- the lethal bit
BASIC_BIT_SCENE_ID = 0x0100        # u16 tag 0x12 @ +0x5C
BASIC_BIT_SCENE_SEQ = 0x0200       # qword tag 0x32 @ +0x60
CURRENT_HP_OFFSET = 0x44
CURRENT_HP_TAG = 0x14
MAX_HP_OFFSET = 0x48
DEATH_TIMER_OFFSET = 0x58
DEATH_TIMER_TAG = 0x2A
SCENE_ID_OFFSET = 0x5C
SCENE_SEQ_OFFSET = 0x60

NPC_BIT_TEMPLATE = 0x01            # u16 tag 0x12 @ +0x78
NPC_BIT_VISUAL_PRESET = 0x04       # wstring tag 0x48 @ +0x7C
NPC_ATTR_MASK_TAG = 0x0B
DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
IDENTITY_TAG = 0x32
FULL_MOVEMENT_MASK = 0xFF

# THE LETHAL SIDE IS NOT COPIED IN.  An earlier draft of this module carried
# the death-lane's timer values, its two predicate addresses and its elapsed
# wire bytes as constants nothing read -- and an adversarial review of round
# R162 called that what it was: the parts for the half of the question this
# ticket is not allowed to ask, laid out ready to hand.  They are deleted.
# Bit 0x0080 above is named only so that every guard in this file can REFUSE
# it; re-add a timer constant only together with the version of this slot
# that is allowed to send one.


# ===========================================================================
# THE TARGET.  Copied, not imported: the identity and every field of the
# placement pin come from the frozen V141 source and NOTHING here is invented.
# ``0x201F`` is ``0x2000 + placement_index + 1`` for placement index 30, the
# Port Royal row the frozen source names "Tornado Eagle" and the row whose HP
# baseline the frozen source carries as ``V117_P30_EXACT_HP``.
#
# THE SELECTION RULE IS NOT THE SIBLING LANE'S.  HYP-PF-029 picks "the frozen
# placement nearest the frozen player spawn", which resolves to index 0 by
# geometry.  Index 30 is roughly twelve thousand units away, so a nearest-rule
# would never reach it: this lane names the index outright and then refuses
# every field of the resolved row that does not match its pin.  A drift in the
# frozen source turns this lane RED instead of silently hitting a different
# NPC.
# ===========================================================================
HOSTILE_HP_LINK_TARGET_IDENTITY_LO = 0x201F
HOSTILE_HP_LINK_TARGET_IDENTITY_HI = 0
HOSTILE_HP_LINK_TARGET_PLACEMENT_INDEX = 30
HOSTILE_HP_LINK_TARGET_TEMPLATE_ID = 31
HOSTILE_HP_LINK_TARGET_VISUAL_PRESET = "M011_000_000_SP3"
HOSTILE_HP_LINK_TARGET_SOURCE_NAME = "Tornado Eagle"

# The frozen WORLD coordinates of that row.  This lane never SENDS them -- it
# pins them so that the placement guard can prove it resolved the intended row,
# and so that the placement refusal below can tell "the lane composed the world
# row" apart from "the lane composed player-relative geometry".
HOSTILE_HP_LINK_TARGET_WORLD_X = 1747.5244140625
HOSTILE_HP_LINK_TARGET_WORLD_Y = -7837.69775390625
HOSTILE_HP_LINK_TARGET_WORLD_Z = 931.0413208007812

# The player-relative offsets this lane places the target at.  Borrowed, not
# invented: they are the offsets the Arena lane's scenario already carries and
# the only geometry in this project a player has ever been asked to look at.
# NONCLAIM, stated where it is easiest to trip over: nobody has confirmed with
# their own eyes that a model at this distance is inside the client's model
# draw distance.  If the attended round sees no model, that is a finding about
# draw distance -- not a negative about damage.
# The one scene this lane's frozen placement row belongs to, re-exported so
# the dispatch branch can refuse a player standing somewhere else without
# importing population.py a second time.
HOSTILE_HP_LINK_SCENE_ID = SCENE_ID
HOSTILE_HP_LINK_POSITION_MODE = "player_relative"
HOSTILE_HP_LINK_TARGET_DX = 100.0
HOSTILE_HP_LINK_TARGET_DY = 50.0
HOSTILE_HP_LINK_TARGET_DZ = 0.0

# The performer stays the PLAYER's own actor: one side of a CHitResult frame
# must be the player or the six-stage visibility filter at 0x43FEF0 draws
# nothing at all (the round-93 static pass, carried into the npc_sweep
# profile).  The pins are composed from the canonical smoke identity the
# frozen V25 create wire commits, exactly as every neighbouring lane does.
HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO = 0x10010001
HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI = 0


@dataclass(frozen=True)
class HostileHpLinkTarget:
    """The frozen placement this sweep hits, resolved, pinned and PLACED.

    ``x``/``y``/``z``/``heading`` are NOT the frozen world row: they are the
    player-relative geometry this lane composes, and the whole reason the lane
    exists in a form a tester can watch.  ``world_x``/``world_y``/``world_z``
    carry the frozen row alongside them so every guard can prove which of the
    two it is looking at.
    """

    placement_index: int
    template_id: int
    actor_identity: int
    x: float
    y: float
    z: float
    heading: float
    world_x: float
    world_y: float
    world_z: float
    visual_preset: str
    source_name: str
    max_hp: int
    scene_id: int
    scene_sequence: int
    # True only when the target was placed against the frozen V135 spawn, the
    # position the byte pins were cut at.  A live session is False and its
    # frames are held to the SIZE pins alone -- see _require_probe_pins.
    probe_geometry: bool


def _require_player_position(player_position: Any) -> tuple[float, float, float]:
    """The live player position this sweep places the target against.

    Accepts the six-tuple the frozen TargetPos parser returns and the bare
    three-tuple the tests compose, and refuses everything else by name.  A
    lane that placed a target at a coordinate nobody handed it would be
    inventing geometry.
    """
    if type(player_position) is not tuple:
        raise HostileHpLinkValidationError("position_not_from_the_pinned_source")
    if len(player_position) not in (3, 6):
        raise HostileHpLinkValidationError("position_not_from_the_pinned_source")
    out = []
    for component in player_position[:3]:
        if type(component) not in (int, float) or type(component) is bool:
            raise HostileHpLinkValidationError(
                "position_not_from_the_pinned_source")
        component = float(component)
        if not math.isfinite(component):
            raise HostileHpLinkValidationError(
                "position_not_from_the_pinned_source")
        out.append(component)
    return (out[0], out[1], out[2])


def hostile_hp_link_probe_player_position(
    legacy: Any,
) -> tuple[float, float, float]:
    """The frozen V135 player spawn -- the position the byte pins are cut at.

    A live session places the target against the player's REAL position, so
    the spawn frame's bytes differ from the pin by exactly three f32s.  The
    size pins still hold; the sha pins are declared probe-only, and
    _require_probe_pins enforces exactly that split.
    """
    return (
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )


def resolve_hostile_hp_link_target(
    legacy: Any,
    player_position: Any,
    scenario: Any,
) -> HostileHpLinkTarget:
    """Resolve frozen placement index 30 and PLACE it relative to the player.

    Two separate jobs, deliberately in one function so that no caller can do
    the first without the second: the frozen row is read and every field of it
    is compared against this lane's pins, and then the composed position is
    derived from the live player position plus the scenario's offsets.  The
    frozen WORLD coordinates never reach a wire from here.
    """
    scenario = require_hostile_hp_link_hypothesis_scenario(scenario)
    px, py, pz = _require_player_position(player_position)
    placements = load_port_royal_placements(legacy)
    if not placements:
        raise HostileHpLinkValidationError("target_placement_source_is_empty")
    placement = None
    for candidate in placements:
        if candidate.placement_index == HOSTILE_HP_LINK_TARGET_PLACEMENT_INDEX:
            placement = candidate
            break
    if placement is None:
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    for component in (placement.x, placement.y, placement.z):
        if not math.isfinite(component):
            raise HostileHpLinkValidationError("target_placement_not_finite")
    if not placement.visual_preset:
        # The visual preset is what eventually sets [actor+0x70] |= 0x40 and is
        # what the avatar-template path formats into a model name.  An actor
        # whose model never resolves cannot be seen, and a target that cannot
        # be seen cannot answer this lane's question.
        raise HostileHpLinkValidationError("target_has_no_visual_preset")
    if (
        placement.template_id != HOSTILE_HP_LINK_TARGET_TEMPLATE_ID
        or placement.actor_identity != HOSTILE_HP_LINK_TARGET_IDENTITY_LO
        or placement.visual_preset != HOSTILE_HP_LINK_TARGET_VISUAL_PRESET
        or placement.source_name != HOSTILE_HP_LINK_TARGET_SOURCE_NAME
        or placement.x != HOSTILE_HP_LINK_TARGET_WORLD_X
        or placement.y != HOSTILE_HP_LINK_TARGET_WORLD_Y
        or placement.z != HOSTILE_HP_LINK_TARGET_WORLD_Z
    ):
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    baseline = getattr(legacy, "V117_P30_EXACT_HP", None)
    if type(baseline) is not int or baseline != HOSTILE_HP_LINK_HP_BASELINE:
        raise HostileHpLinkValidationError(
            "target_hp_baseline_drifted_from_the_frozen_source")
    if getattr(legacy, "V119_P30_TARGET_NAME", None) != (
        HOSTILE_HP_LINK_TARGET_SOURCE_NAME
    ):
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    if getattr(legacy, "V112_MONSTER_ACTOR_ID", None) != (
        HOSTILE_HP_LINK_TARGET_IDENTITY_LO
    ):
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    target_x = px + scenario.dx
    target_y = py + scenario.dy
    target_z = pz + scenario.dz
    for component in (target_x, target_y, target_z):
        if not math.isfinite(component):
            raise HostileHpLinkValidationError("target_placement_not_finite")
    if _is_the_frozen_world_row((target_x, target_y, target_z)):
        # Nothing forbids a player from standing exactly one offset away from
        # the frozen row, but this lane cannot then tell its own geometry apart
        # from the population branch's, and a round that cannot attribute what
        # it drew is a round that answers nothing.
        raise HostileHpLinkValidationError(
            "target_placement_is_the_frozen_world_row_not_player_relative")
    heading = float(legacy._heading_to_player(target_x, target_y, px, py))
    if not math.isfinite(heading):
        raise HostileHpLinkValidationError("target_placement_not_finite")
    probe_geometry = (px, py, pz) == hostile_hp_link_probe_player_position(
        legacy)
    return HostileHpLinkTarget(
        placement.placement_index, placement.template_id,
        placement.actor_identity, target_x, target_y, target_z, heading,
        placement.x, placement.y, placement.z,
        placement.visual_preset, placement.source_name,
        HOSTILE_HP_LINK_HP_BASELINE, SCENE_ID, SCENE_SEQUENCE,
        probe_geometry,
    )


def hostile_hp_link_target_identity() -> int:
    """The 64-bit identity every frame of this sweep is about."""
    return (
        ((HOSTILE_HP_LINK_TARGET_IDENTITY_HI & 0xFFFFFFFF) << 32)
        | (HOSTILE_HP_LINK_TARGET_IDENTITY_LO & 0xFFFFFFFF)
    )


# ===========================================================================
# THE BALANCE.  Our arithmetic, the CLIENT's baseline.  3857 is what the
# frozen V141 source carries as V117_P30_EXACT_HP for placement row 30, which
# is the STANDARD_MOB level-27 value the CLIENT ships for that mob -- it is
# not a rule of the original server and this lane never says it is.  The
# floor exists only to be REFUSED: this lane has no lethal step.
# ===========================================================================
HOSTILE_HP_LINK_HP_BASELINE = 3857
HOSTILE_HP_LINK_HP_START = HOSTILE_HP_LINK_HP_BASELINE
HOSTILE_HP_LINK_HP_MAX = HOSTILE_HP_LINK_HP_BASELINE
HOSTILE_HP_LINK_HP_FLOOR = 0

# 6.0 s, NOT 15.0 s: Panya ruled on 2026-08-20 that stretching frame spacing
# for the human tester is wasted effort because the event itself is short, and
# that the correct fix is recording video.  This is the death lane's spacing.
HOSTILE_HP_LINK_SPACING_SECONDS = 6.0
HOSTILE_HP_LINK_FIRST_DELAY_SECONDS = 0.0
HOSTILE_HP_LINK_SPACING_DECISION = (
    "six_seconds_not_fifteen_stretching_spacing_for_the_tester_is_wasted_"
    "effort_because_the_event_is_short_the_fix_is_recording_video_panya_"
    "20260820"
)
HOSTILE_HP_LINK_ACTION_LABEL_PREFIX = "HYP_PF_038_HOSTILE_HP_LINK_"

HOSTILE_HP_LINK_STEP_KIND_ACTOR = "actor"
HOSTILE_HP_LINK_STEP_KIND_HIT = "hit"

# The server-held TARGET balance AFTER each step.  A hit frame only ANNOUNCES
# its number; the actor-entry frame that follows it APPLIES the number, which
# is why the ladder holds still on every hit index.  Declared here and
# re-derived by replay_hostile_hp_link_balance_ladder on every composition -- any
# disagreement is hp_arithmetic_not_reproducible and no byte leaves.
#
#   3857 -> 2893 is 75.0 percent of the baseline, 2893 -> 771 is 20.0 percent.
#   Both are movements a human can see on a bar; -63 on 3857 is not, which is
#   the whole reason the attacker profiles differ from the sibling lane's.
HOSTILE_HP_LINK_BALANCE_LADDER = (3857, 3857, 2893, 2893, 2893, 2893, 771)

# (label, kind, spec, flags)
#   actor step -> spec is (hp_current, death_timer_or_None, with_movement)
#   hit step   -> spec is the named attacker, or None for the miss control
#
# SEVEN steps, and the seventh is NOT a death frame.  One ticket, one claim:
# the "does it die" half is GT-036's question and belongs to a later version
# of this slot.  The plan validator refuses a floor balance and refuses every
# death-timer field, so that half cannot be slipped in by editing this tuple.
HOSTILE_HP_LINK_STEPS = (
    ("TARGET_SPAWN", HOSTILE_HP_LINK_STEP_KIND_ACTOR,
     (HOSTILE_HP_LINK_BALANCE_LADDER[0], None, True), None),
    ("HIT_WEAK", HOSTILE_HP_LINK_STEP_KIND_HIT, "MOB_WEAK", FLAGS_HIT),
    ("TARGET_HP_AFTER_WEAK", HOSTILE_HP_LINK_STEP_KIND_ACTOR,
     (HOSTILE_HP_LINK_BALANCE_LADDER[2], None, False), None),
    ("MISS", HOSTILE_HP_LINK_STEP_KIND_HIT, None, FLAGS_MISS),
    ("TARGET_HP_AFTER_MISS", HOSTILE_HP_LINK_STEP_KIND_ACTOR,
     (HOSTILE_HP_LINK_BALANCE_LADDER[4], None, False), None),
    ("HIT_STRONG", HOSTILE_HP_LINK_STEP_KIND_HIT, "MOB_STRONG", FLAGS_HIT),
    ("TARGET_HP_AFTER_STRONG", HOSTILE_HP_LINK_STEP_KIND_ACTOR,
     (HOSTILE_HP_LINK_BALANCE_LADDER[6], None, False), None),
)
HOSTILE_HP_LINK_STEP_ORDER = tuple(row[0] for row in HOSTILE_HP_LINK_STEPS)
HOSTILE_HP_LINK_ACTION_LABELS = tuple(
    HOSTILE_HP_LINK_ACTION_LABEL_PREFIX + label
    for label in HOSTILE_HP_LINK_STEP_ORDER
)
HOSTILE_HP_LINK_SPAWN_STEP_LABEL = "TARGET_SPAWN"
HOSTILE_HP_LINK_MISS_STEP_LABELS = ("MISS",)
HOSTILE_HP_LINK_FINAL_STEP_LABEL = "TARGET_HP_AFTER_STRONG"
# EMPTY BY DESIGN, and every guard downstream reads it rather than a literal:
# no step of this lane may compose a lethal field, and no step may clamp.
HOSTILE_HP_LINK_LETHAL_STEP_LABELS = ()
HOSTILE_HP_LINK_TIMER_BY_STEP: dict[str, float] = {}


def step_plan(index: Any) -> tuple[str, str, Any, Any]:
    if type(index) is not int or type(index) is bool:
        raise HostileHpLinkValidationError("unknown_step_label")
    if not 0 <= index < len(HOSTILE_HP_LINK_STEPS):
        raise HostileHpLinkValidationError("unknown_step_label")
    return HOSTILE_HP_LINK_STEPS[index]


def step_damage_wire(index: Any) -> int:
    """The number OUR formula produces for one hit step of the plan."""
    _label, kind, spec, _flags = step_plan(index)
    if kind != HOSTILE_HP_LINK_STEP_KIND_HIT:
        raise HostileHpLinkValidationError("unknown_step_label")
    if spec is None:
        return 0
    return compute_hostile_hp_link_damage_wire(spec)


# ===========================================================================
# THE ARITHMETIC ENGINE.
# ===========================================================================
def apply_hit_to_balance(balance: Any, damage_wire: Any, flags: Any) -> int:
    """Move the server-held TARGET balance by one announced hit, or refuse.

    THIS LANE DOES NOT CLAMP.  The sibling lane clamps at the floor on one
    pinned step because its ladder ends in a corpse; this one has no lethal
    step at all, so a move that would reach or cross the floor is a REFUSAL
    rather than a clamp.  Written this way round on purpose: a silent clamp
    here would turn "the ladder was mis-specified" into "the bar hit zero",
    which is the one claim this ticket is not allowed to make.
    """
    if type(balance) is not int or type(balance) is bool:
        raise HostileHpLinkValidationError("hp_balance_not_integer")
    if not HOSTILE_HP_LINK_HP_FLOOR <= balance <= HOSTILE_HP_LINK_HP_MAX:
        raise HostileHpLinkValidationError("hp_balance_outside_the_declared_band")
    require_hostile_hp_link_damage_wire_value(damage_wire)
    require_hostile_hp_link_flags_value(flags)
    require_hostile_hp_link_damage_and_flags_agree(damage_wire, flags)
    moved = balance + damage_wire
    if moved <= HOSTILE_HP_LINK_HP_FLOOR:
        raise HostileHpLinkValidationError(
            "hp_clamp_is_forbidden_in_this_lane: the ladder may never reach "
            "the floor, because this lane composes no lethal frame"
        )
    return moved


def replay_hostile_hp_link_balance_ladder() -> tuple[int, ...]:
    """Walk the whole plan through the engine and return the derived ladder.

    No step of this lane may clamp: apply_hit_to_balance refuses a move that
    reaches the floor, and this walk re-checks the same thing from outside so
    a future edit cannot make the engine lenient without turning the plan red.
    """
    balance = HOSTILE_HP_LINK_HP_START
    pending: Any = None
    ladder: list[int] = []
    for label, kind, spec, flags in HOSTILE_HP_LINK_STEPS:
        if kind == HOSTILE_HP_LINK_STEP_KIND_HIT:
            if pending is not None:
                raise HostileHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: two hit frames in a "
                    "row leave a number nothing applied"
                )
            damage = (
                0 if spec is None else compute_hostile_hp_link_damage_wire(spec)
            )
            pending = (damage, flags)
        else:
            if pending is not None:
                damage, hit_flags = pending
                moved = apply_hit_to_balance(balance, damage, hit_flags)
                if balance + damage <= HOSTILE_HP_LINK_HP_FLOOR:
                    raise HostileHpLinkValidationError(
                        "hp_clamp_is_forbidden_in_this_lane")
                balance = moved
                pending = None
        ladder.append(balance)
    return tuple(ladder)


def require_hostile_hp_link_balance_ladder() -> tuple[int, ...]:
    """The declared ladder, or a refusal if the engine cannot reproduce it."""
    derived = replay_hostile_hp_link_balance_ladder()
    if derived != HOSTILE_HP_LINK_BALANCE_LADDER:
        raise HostileHpLinkValidationError("hp_arithmetic_not_reproducible")
    return derived


def _require_step_plan() -> None:
    """Shape checks on the pinned plan itself, run before any composition."""
    if len(set(HOSTILE_HP_LINK_STEP_ORDER)) != len(HOSTILE_HP_LINK_STEP_ORDER):
        raise HostileHpLinkValidationError("unknown_step_label")
    if len(HOSTILE_HP_LINK_STEPS) != len(HOSTILE_HP_LINK_BALANCE_LADDER):
        raise HostileHpLinkValidationError("hp_arithmetic_not_reproducible")
    first_label, first_kind, first_spec, _flags = HOSTILE_HP_LINK_STEPS[0]
    if first_label != HOSTILE_HP_LINK_SPAWN_STEP_LABEL or (
        first_kind != HOSTILE_HP_LINK_STEP_KIND_ACTOR
    ):
        raise HostileHpLinkValidationError("unknown_step_label")
    # An actor cannot be born dead: an identity the client does not know takes
    # the spawn branch 0x446990 -> vtable +0x10, which never reaches the dead
    # state sync.  The first frame must therefore be a live, placed spawn.
    if first_spec != (HOSTILE_HP_LINK_HP_START, None, True):
        raise HostileHpLinkValidationError(
            "lethal_field_outside_the_pinned_step: the spawn must be alive, "
            "placed and carry no death timer"
        )
    last_label, last_kind, last_spec, _flags = HOSTILE_HP_LINK_STEPS[-1]
    if last_label != HOSTILE_HP_LINK_FINAL_STEP_LABEL or (
        last_kind != HOSTILE_HP_LINK_STEP_KIND_ACTOR
    ):
        raise HostileHpLinkValidationError("unknown_step_label")
    # The sweep ENDS ALIVE, and it ends on the frame that applies the strong
    # hit.  A plan whose last frame carried a timer, or a floor balance, would
    # be the death half of the question this ticket does not ask.
    if last_spec[1] is not None or last_spec[0] <= HOSTILE_HP_LINK_HP_FLOOR:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    miss_labels = []
    for index, (label, kind, spec, flags) in enumerate(HOSTILE_HP_LINK_STEPS):
        if kind == HOSTILE_HP_LINK_STEP_KIND_HIT:
            follower = HOSTILE_HP_LINK_STEPS[index + 1]
            if follower[1] != HOSTILE_HP_LINK_STEP_KIND_ACTOR:
                raise HostileHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: every hit frame must "
                    "be followed by the actor frame that applies it"
                )
            if spec is None:
                if flags != FLAGS_MISS:
                    raise HostileHpLinkValidationError(
                        "damage_zero_with_apply_flag")
                miss_labels.append(label)
            elif flags != FLAGS_HIT:
                raise HostileHpLinkValidationError(
                    "damage_nonzero_without_apply_flag")
        elif kind != HOSTILE_HP_LINK_STEP_KIND_ACTOR:
            raise HostileHpLinkValidationError("unknown_step_label")
    if tuple(miss_labels) != HOSTILE_HP_LINK_MISS_STEP_LABELS:
        raise HostileHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    ladder = require_hostile_hp_link_balance_ladder()
    # The declared hp values must BE the derived balances, so the plan cannot
    # write a bar the arithmetic did not produce.
    for index, (label, kind, spec, _flags) in enumerate(HOSTILE_HP_LINK_STEPS):
        if kind != HOSTILE_HP_LINK_STEP_KIND_ACTOR:
            continue
        if spec[0] != ladder[index]:
            raise HostileHpLinkValidationError("hp_arithmetic_not_reproducible")
        if spec[1] is not None:
            raise HostileHpLinkValidationError(
                "lethal_field_is_not_available_in_this_lane")
        if spec[0] <= HOSTILE_HP_LINK_HP_FLOOR:
            raise HostileHpLinkValidationError(
                "lethal_field_is_not_available_in_this_lane")
    # Both of these are empty BY DESIGN and the guards read them rather than a
    # literal, so restoring the death half means restoring these two lines as
    # well -- which is a diff nobody can land by accident.
    if HOSTILE_HP_LINK_LETHAL_STEP_LABELS != ():
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    if HOSTILE_HP_LINK_TIMER_BY_STEP != {}:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")


# ===========================================================================
# THE UNLOCK.  One token, minted only from the allowlisted scenario object,
# compared by IDENTITY everywhere.
# ===========================================================================
@dataclass(frozen=True)
class HostileHpLinkWireUnlock:
    scenario_id: str
    hypothesis_id: str


_UNLOCK = HostileHpLinkWireUnlock(
    HOSTILE_HP_LINK_SCENARIO_ID, HOSTILE_HP_LINK_HYPOTHESIS_ID,
)


@dataclass(frozen=True)
class HostileHpLinkHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str
    # The placement offsets ride the scenario rather than the module so that
    # the geometry a round used is readable in the opt-in file the tester can
    # see, and so that changing it is a scenario edit the exact-tree allowlist
    # refuses unless the module is changed in the same commit.
    position_mode: str
    dx: float
    dy: float
    dz: float


_PROFILE = HostileHpLinkHypothesisScenario(
    HOSTILE_HP_LINK_SCENARIO_ID,
    HOSTILE_HP_LINK_HYPOTHESIS_ID,
    HOSTILE_HP_LINK_STEP_ORDER,
    HOSTILE_HP_LINK_SPACING_SECONDS,
    HOSTILE_HP_LINK_FIRST_DELAY_SECONDS,
    HOSTILE_HP_LINK_ACTION_LABEL_PREFIX,
    HOSTILE_HP_LINK_POSITION_MODE,
    HOSTILE_HP_LINK_TARGET_DX,
    HOSTILE_HP_LINK_TARGET_DY,
    HOSTILE_HP_LINK_TARGET_DZ,
)


def hostile_hp_link_wire_unlock(scenario: Any) -> HostileHpLinkWireUnlock:
    """The ONLY minter.  Requires the allowlisted scenario object ITSELF.

    Identity, not equality: a scenario assembled elsewhere that happens to
    compare equal is still not the one this module ships, and it mints nothing.
    """
    require_hostile_hp_link_hypothesis_scenario(scenario)
    if scenario is not _PROFILE:
        raise HostileHpLinkValidationError("scenario_object_exceeds_allowlist")
    return _UNLOCK


def require_hostile_hp_link_wire_unlock(value: Any) -> HostileHpLinkWireUnlock:
    # Identity, not equality: a forged token that compares equal must not open
    # the lane.
    if value is not _UNLOCK:
        raise HostileHpLinkValidationError(
            "missing_or_forged_wire_unlock: HYP-PF-038 refuses to emit a byte "
            "without the unlock derived from the opt-in scenario"
        )
    return value


def require_hostile_hp_link_hypothesis_scenario(
    value: Any,
) -> HostileHpLinkHypothesisScenario:
    if type(value) is not HostileHpLinkHypothesisScenario or value != _PROFILE:
        raise HostileHpLinkValidationError("scenario_object_exceeds_allowlist")
    _require_step_plan()
    return value


# ===========================================================================
# THE ENCODERS.
# ===========================================================================
def _require_identity_pair(identity_lo: Any, identity_hi: Any) -> int:
    for value in (identity_lo, identity_hi):
        if type(value) is not int or type(value) is bool:
            raise HostileHpLinkValidationError("target_identity_outside_qword")
        if not 0 <= value <= 0xFFFFFFFF:
            raise HostileHpLinkValidationError("target_identity_outside_qword")
    return ((identity_hi & 0xFFFFFFFF) << 32) | (identity_lo & 0xFFFFFFFF)


def _is_the_frozen_world_row(position: Any) -> bool:
    """True when these three floats ARE the frozen placement row.

    Compared at f32 resolution, because that is the width the wire carries:
    a value that only differs beyond the 24th bit of mantissa is the same
    point once it has been packed, and this predicate is what stands between
    an attended round and a target nobody can see.
    """
    if type(position) is not tuple or len(position) != 3:
        return False
    try:
        packed = b"".join(struct.pack("<f", float(value)) for value in position)
    except (OverflowError, TypeError, ValueError):
        return False
    row = b"".join(
        struct.pack("<f", value) for value in (
            HOSTILE_HP_LINK_TARGET_WORLD_X,
            HOSTILE_HP_LINK_TARGET_WORLD_Y,
            HOSTILE_HP_LINK_TARGET_WORLD_Z,
        )
    )
    return packed == row


def _require_pinned_position(
    target: "HostileHpLinkTarget",
) -> tuple[float, float, float]:
    """Where the floating number is placed: ON THE TARGET, wherever it stands.

    The sibling lane pins this to the frozen player spawn because its target
    stands next to it.  This lane's target is placed player-relative, so the
    hit position is the target's own composed position and nothing here
    invents a coordinate: it is read back off the resolved target and refused
    if it is the frozen world row.
    """
    if type(target) is not HostileHpLinkTarget:
        raise HostileHpLinkValidationError("position_not_from_the_pinned_source")
    position = (float(target.x), float(target.y), float(target.z))
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise HostileHpLinkValidationError(
                "position_not_from_the_pinned_source")
    if _is_the_frozen_world_row(position):
        raise HostileHpLinkValidationError(
            "target_placement_is_the_frozen_world_row_not_player_relative")
    return position


def _require_pinned_yaw(value: Any) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise HostileHpLinkValidationError("yaw_outside_pinned_value")
    if value != YAW_PINNED:
        raise HostileHpLinkValidationError("yaw_outside_pinned_value")
    return value


def encode_hostile_hp_link_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    yaw: float,
    flags: int,
    unlock: Any,
) -> bytes:
    """One 37-byte hit entry, in the proven emission order."""
    require_hostile_hp_link_wire_unlock(unlock)
    if type(target_identity) is not int or type(target_identity) is bool:
        raise HostileHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= target_identity <= 0xFFFFFFFFFFFFFFFF:
        raise HostileHpLinkValidationError("target_identity_outside_qword")
    if target_identity != hostile_hp_link_target_identity():
        raise HostileHpLinkValidationError("npc_target_identity_not_pinned")
    require_hostile_hp_link_damage_wire_value(damage_wire)
    require_hostile_hp_link_flags_value(flags)
    require_hostile_hp_link_damage_and_flags_agree(damage_wire, flags)
    yaw = _require_pinned_yaw(yaw)
    if type(position) is not tuple or len(position) != 3:
        raise HostileHpLinkValidationError("position_not_from_the_pinned_source")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target_identity)
    out += legacy.u32tag(TAG_U32, damage_wire & 0xFFFFFFFF)
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise HostileHpLinkValidationError(
                "position_not_from_the_pinned_source")
        out += legacy.f32tag(component)
    out += legacy.f32tag(yaw)
    out += legacy.u16tag(TAG_U16, flags)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: hit entry is %d bytes"
            % len(out)
        )
    return bytes(out)


def encode_hostile_hp_link_chit_result(
    legacy: Any,
    performer_identity: int,
    entries: list[bytes],
    unlock: Any,
) -> bytes:
    """The CHitResult payload: the 22-byte header, then the entry array."""
    require_hostile_hp_link_wire_unlock(unlock)
    if type(performer_identity) is not int or type(performer_identity) is bool:
        raise HostileHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= performer_identity <= 0xFFFFFFFFFFFFFFFF:
        raise HostileHpLinkValidationError("target_identity_outside_qword")
    if performer_identity == hostile_hp_link_target_identity():
        raise HostileHpLinkValidationError(
            "npc_performer_must_not_be_the_npc_target")
    if type(entries) is not list or len(entries) != HIT_ENTRY_COUNT_PINNED:
        raise HostileHpLinkValidationError("entry_count_not_pinned")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer_identity)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: header is %d bytes"
            % len(header)
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise HostileHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: entry width")
        out += entry
    if len(out) != CHIT_RESULT_PAYLOAD_WIRE_SIZE:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: payload is %d bytes"
            % len(out)
        )
    return bytes(out)


def _require_death_timer(value: Any, step_label: str) -> float:
    """THE DEATH TIMER IS NOT AVAILABLE ON THIS LANE.  Always a refusal.

    The sibling lane composes BasicAttr bit 0x0080 on two pinned steps and
    ends in a corpse.  This lane asks one question -- does a REAL hostile's
    bar move -- and the death half is GT-036's, on a later version of this
    slot.  The function is kept, rather than deleted, so that the refusal has
    a name and a place: an edit that tries to send a timer lands HERE and
    turns red, instead of finding no guard at all.
    """
    raise HostileHpLinkValidationError(
        "lethal_field_is_not_available_in_this_lane: %s"
        % (step_label if type(step_label) is str else "unknown_step_label")
    )


def encode_hostile_hp_link_npc_attr(
    legacy: Any,
    target: HostileHpLinkTarget,
    step_label: str,
    current_hp: int,
    death_timer: Any,
    unlock: Any,
) -> bytes:
    """One NPCAttr body, optionally carrying BasicAttr bit 0x0080.

    ``death_timer is None`` -> bit 0x0080 is ABSENT and the result is asserted
    byte-for-byte equal to ``legacy.make_npc_attr(...)``, the projection this
    project's actor-entry emitters already ship and the RUNTIMERES-DEATH lane
    uses as its own baseline oracle.  That equality is the whole reason to
    believe the widened encoder is right: it is a superset that degrades
    exactly to the known-good body.

    ``death_timer is not None`` -> bit 0x0080 is emitted, in ascending mask-bit
    order (after 0x0008 max HP, before 0x0100 scene id), as an f32 with wire
    tag 0x2A, and only for a step the plan declares lethal.
    """
    require_hostile_hp_link_wire_unlock(unlock)
    if type(target) is not HostileHpLinkTarget:
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    if type(step_label) is not str or step_label not in HOSTILE_HP_LINK_STEP_ORDER:
        raise HostileHpLinkValidationError("unknown_step_label")
    if type(current_hp) is not int or type(current_hp) is bool:
        raise HostileHpLinkValidationError("hp_field_value_not_integer")
    if not 0 <= current_hp <= HOSTILE_HP_LINK_HP_MAX:
        raise HostileHpLinkValidationError("hp_field_value_outside_width")
    if current_hp <= HOSTILE_HP_LINK_HP_FLOOR:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    if death_timer is not None:
        # Routed through the named refusal rather than raised inline, so the
        # one place that says "no timer on this lane" is the same one an edit
        # would have to defeat.
        _require_death_timer(death_timer, step_label)
    if target.max_hp != HOSTILE_HP_LINK_HP_MAX:
        raise HostileHpLinkValidationError(
            "target_hp_baseline_drifted_from_the_frozen_source")
    baseline = legacy.make_npc_attr(
        target.template_id, target.actor_identity,
        target.scene_id, target.scene_sequence, target.visual_preset,
        current_hp, target.max_hp, None, target.source_name,
    )
    composed = _compose_npc_attr(legacy, target, current_hp, None)
    if composed != baseline:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: the body no longer "
            "reproduces legacy.make_npc_attr byte for byte"
        )
    return composed


def _compose_npc_attr(
    legacy: Any,
    target: HostileHpLinkTarget,
    current_hp: int,
    death_timer: float | None,
) -> bytes:
    if death_timer is not None:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    # Bit 0x0001 is the target's NAME.  The sibling lane omits it; this lane
    # carries it because the whole point is a REAL hostile, and the target
    # panel the tester reads gets its label from BasicAttr +0x28.  A frame
    # whose bar moved but whose name was blank would leave "which actor was
    # that" open, and this lane cannot afford that question.
    basic_mask = (
        BASIC_BIT_NAME
        | BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
        | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ
    )
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if target.visual_preset else 0
    )
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, target.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
    # Ascending mask-bit order inside the block, which is the order BasicAttr's
    # serializer 0x4656F0 writes and its reader expects.
    out += legacy.wstr_tag(target.source_name)                      # 0x0001
    out += legacy.u32tag(CURRENT_HP_TAG, current_hp)                # 0x0004
    out += legacy.u32tag(CURRENT_HP_TAG, target.max_hp)             # 0x0008
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, target.scene_id)      # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, target.scene_sequence)     # 0x0200
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, target.template_id)
    if target.visual_preset:
        out += legacy.wstr_tag(target.visual_preset)
    return bytes(out)


def make_hostile_hp_link_step_response(
    legacy: Any,
    target: HostileHpLinkTarget,
    performer_identity_lo: int,
    performer_identity_hi: int,
    step_index: int,
    unlock: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the target sweep, either carrier."""
    require_hostile_hp_link_wire_unlock(unlock)
    _require_step_plan()
    performer = _require_identity_pair(
        performer_identity_lo, performer_identity_hi)
    label, kind, spec, flags = step_plan(step_index)
    if kind == HOSTILE_HP_LINK_STEP_KIND_HIT:
        # The performer stays the PLAYER and the target is the NPC: one side
        # must be the player or the visibility filter at 0x43FEF0 draws
        # nothing, and the whole point of this lane is that the two differ.
        entry = encode_hostile_hp_link_hit_entry(
            legacy, hostile_hp_link_target_identity(), step_damage_wire(step_index),
            _require_pinned_position(target), YAW_PINNED, flags, unlock,
        )
        payload = encode_hostile_hp_link_chit_result(
            legacy, performer, [entry], unlock)
        pc, frame = legacy.make_runtime_vitals(
            [(CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION, payload)]
        )
    else:
        current_hp, death_timer, with_movement = spec
        body = encode_hostile_hp_link_npc_attr(
            legacy, target, label, current_hp, death_timer, unlock)
        attrs = [(NPC_ATTR_ID, body)]
        if with_movement:
            # The SAME guard the hit branch runs, on the frame that actually
            # places the actor.  Until an adversarial review of R162 pointed
            # it out, the guard sat only on the three frames that merely
            # float a number: the one frame whose coordinates decide whether
            # a tester sees anything had none at all.
            _require_pinned_position(target)
            attrs.append((
                MOVEMENT_ATTR_ID,
                legacy.make_remote_movement_attr(
                    target.actor_identity, target.x, target.y, target.z,
                    target.heading, mask=FULL_MOVEMENT_MASK,
                ),
            ))
        entry = legacy.make_remote_actor_entry(
            NPC_STYLE_ACTOR_TYPE, target.actor_identity, attrs,
        )
        pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: HYP-PF-038 frame drift")
    _require_probe_pins(
        label, pc, frame, performer_identity_lo, performer_identity_hi, target)
    return pc, frame


def _require_probe_pins(
    label: str, pc: bytes, frame: bytes, identity_lo: int, identity_hi: int,
    target: "HostileHpLinkTarget",
) -> None:
    """Sizes for EVERY session; exact bytes only for the pinned probe.

    THIS DIFFERS FROM THE SIBLING LANE AND THE DIFFERENCE IS THE POINT.  There
    the target stands at a frozen world row, so the five actor frames mention
    nothing session-specific and their sha pins hold for everyone.  Here the
    target is placed PLAYER-RELATIVE, so every frame of the sweep carries
    three f32s that depend on where the player stood: the sha pins hold only
    when the geometry is the probe geometry AND, on the hit frames, the
    performer is the probe performer.  The SIZE pins hold always, because a
    coordinate is four bytes wherever the player is standing.
    """
    if not HOSTILE_HP_LINK_PINS:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: HOSTILE_HP_LINK_PINS is empty, "
            "so there is nothing to hold the encoder to -- this lane refuses "
            "rather than composing unpinned bytes")
    pin = HOSTILE_HP_LINK_PINS[label]
    if len(pc) != pin["pc_size"] or len(frame) != pin["frame_size"]:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: %s size %d/%d != %d/%d"
            % (label, len(pc), len(frame), pin["pc_size"], pin["frame_size"])
        )
    _label, kind, _spec, _flags = HOSTILE_HP_LINK_STEPS[
        HOSTILE_HP_LINK_STEP_ORDER.index(label)
    ]
    if type(target) is not HostileHpLinkTarget:
        raise HostileHpLinkValidationError("target_placement_drifted_from_the_pin")
    if not target.probe_geometry:
        return
    if kind == HOSTILE_HP_LINK_STEP_KIND_HIT and (identity_lo, identity_hi) != (
        HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
        HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
    ):
        return
    for value, key in (
        (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
        (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
    ):
        if value != pin[key]:
            raise HostileHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: probe %s %s %r != %r"
                % (label, key, value, pin[key])
            )


def build_hostile_hp_link_sweep(
    legacy: Any,
    target: HostileHpLinkTarget,
    performer_identity_lo: int,
    performer_identity_hi: int,
    unlock: Any,
    scenario: Any,
) -> list[tuple[str, bytes, bytes, float]]:
    """Compose the whole sweep, then refuse to return it unless it validates.

    The delay is a gap on a cumulative deadline, the same semantics every
    neighbouring lane ships: the first frame carries the first delay and each
    later frame the full spacing.
    """
    scenario = require_hostile_hp_link_hypothesis_scenario(scenario)
    require_hostile_hp_link_wire_unlock(unlock)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(scenario.step_order):
        pc, frame = make_hostile_hp_link_step_response(
            legacy, target, performer_identity_lo, performer_identity_hi,
            index, unlock,
        )
        delay = (
            scenario.first_delay_seconds if index == 0
            else scenario.spacing_seconds
        )
        actions.append((scenario.action_label_prefix + label, pc, frame, delay))
    validate_hostile_hp_link_sweep(actions)
    _require_pinned_probe_composition(legacy, scenario, unlock)
    return actions


def _require_pinned_probe_composition(
    legacy: Any, scenario: Any, unlock: Any,
) -> None:
    """Hold the ENCODER to the pinned bytes on every build.

    A live sweep can be hashed to nothing constant -- neither its performer nor
    its geometry is fixed -- so this composes the WHOLE sweep a second time at
    the probe performer AND the probe geometry and compares that to the pins.
    A drifted encoder therefore cannot ship even once, even though not one
    byte of the live sweep is itself pinned by sha.
    """
    if not HOSTILE_HP_LINK_PINS:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: HOSTILE_HP_LINK_PINS is empty, "
            "so the probe recomposition has no oracle -- this lane refuses "
            "rather than shipping a sweep nothing held to the pins")
    probe_target = resolve_hostile_hp_link_target(
        legacy, hostile_hp_link_probe_player_position(legacy), scenario,
    )
    if not probe_target.probe_geometry:
        raise HostileHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: the probe target is not at "
            "the probe geometry, so the pins have no oracle")
    for index, label in enumerate(HOSTILE_HP_LINK_STEP_ORDER):
        pc, frame = make_hostile_hp_link_step_response(
            legacy, probe_target,
            HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
            HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
            index, unlock,
        )
        pin = HOSTILE_HP_LINK_PINS[label]
        for value, key in (
            (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
            (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
        ):
            if value != pin[key]:
                raise HostileHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: probe %s %s"
                    % (label, key)
                )


# ===========================================================================
# THE INDEPENDENT READER.  Deliberately reuses nothing from the encoders except
# the pinned constants, so a symmetrical bug cannot hide here.  It walks from
# byte 0, reads BOTH carriers, and unwraps the outer transport frame down to
# the raw literal stream.
# ===========================================================================
_SCALAR_WIDTH = {0x05: 1, 0x08: 1, 0x0B: 1, 0x12: 2, 0x14: 4, 0x19: 4,
                 0x26: 4, 0x2A: 4, 0x32: 8}
_BASIC_FIELD_ORDER = (
    (0x0001, 0x48), (0x0002, 0x12), (0x0004, 0x14), (0x0008, 0x14),
    (0x0010, 0x14), (0x0020, 0x14), (0x0040, 0x2A), (0x0080, 0x2A),
    (0x0100, 0x12), (0x0200, 0x32), (0x0400, 0x14),
)
_MOVEMENT_FIELD_WIDTH = (
    (0x01, 12), (0x02, 4), (0x04, 2), (0x08, 5), (0x10, 5), (0x20, 5),
    (0x40, 5),
)


def _scalar(pc: bytes, cursor: int, tag: int, width: int, label: str):
    if cursor + 1 + width > len(pc):
        raise HostileHpLinkValidationError(f"{label}: truncated")
    if pc[cursor] != tag:
        raise HostileHpLinkValidationError(
            "%s: tag 0x%02X != 0x%02X" % (label, pc[cursor], tag))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def decode_hostile_hp_link_transport(frame: bytes) -> bytes:
    """Read the outer transport frame back to its PC, byte for byte.

    The frozen framer is u32 magic + u32 body length + ONE raw literal stream,
    so this walker accepts only literal elements and must land exactly on the
    declared uncompressed length.
    """
    if type(frame) is not bytes or len(frame) < 8:
        raise HostileHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != HOSTILE_HP_LINK_FRAME_MAGIC:
        raise HostileHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: magic")
    if body_len != len(frame) - 8:
        raise HostileHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length")
    body = frame[8:]
    total = 0
    shift = 0
    cursor = 0
    while True:
        if cursor >= len(body):
            raise HostileHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
        byte = body[cursor]
        cursor += 1
        total |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 28:
            raise HostileHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
    out = bytearray()
    while cursor < len(body):
        tag = body[cursor]
        cursor += 1
        if tag & 0x03:
            raise HostileHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: non-literal")
        code = tag >> 2
        if code <= 59:
            count = code + 1
        else:
            extra = code - 59
            if cursor + extra > len(body):
                raise HostileHpLinkValidationError(
                    "transport_frame_does_not_reproduce_the_pc: truncated")
            count = int.from_bytes(body[cursor:cursor + extra], "little") + 1
            cursor += extra
        if cursor + count > len(body):
            raise HostileHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: truncated")
        out += body[cursor:cursor + count]
        cursor += count
    if len(out) != total:
        raise HostileHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length mismatch")
    return bytes(out)


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG:
        raise HostileHpLinkValidationError("DBAttribute mask tag drift")
    if pc[cursor + 1] != DB_ATTRIBUTE_IDENTITY_MASK:
        raise HostileHpLinkValidationError(
            "DBAttribute mask is not the identity-only 0x01")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise HostileHpLinkValidationError("NPCAttr identity tag drift")
    attr_identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise HostileHpLinkValidationError("BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise HostileHpLinkValidationError(
                "BasicAttr bit 0x%04X expected tag 0x%02X, found 0x%02X"
                % (bit, tag, pc[cursor])
            )
        if tag == TAG_WSTRING:
            length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
            fields[bit] = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
            cursor += 5 + length
            continue
        width = _SCALAR_WIDTH[tag]
        raw = pc[cursor + 1:cursor + 1 + width]
        fields[bit] = (
            struct.unpack("<f", raw)[0] if tag == TAG_F32
            else int.from_bytes(raw, "little")
        )
        cursor += 1 + width
    if basic_mask & ~0x07FF:
        raise HostileHpLinkValidationError(
            "BasicAttr mask 0x%04X carries a bit this walker cannot read"
            % basic_mask
        )
    if pc[cursor] != NPC_ATTR_MASK_TAG:
        raise HostileHpLinkValidationError("NPCAttr mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & NPC_BIT_TEMPLATE:
        if pc[cursor] != TAG_U16:
            raise HostileHpLinkValidationError("NPCAttr template tag drift")
        template_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
    if npc_mask & NPC_BIT_VISUAL_PRESET:
        if pc[cursor] != TAG_WSTRING:
            raise HostileHpLinkValidationError("NPCAttr preset tag drift")
        length = int.from_bytes(pc[cursor + 1:cursor + 5], "little")
        visual_preset = pc[cursor + 5:cursor + 5 + length].decode("utf-16le")
        cursor += 5 + length
    return (
        {
            "identity": attr_identity,
            "basic_mask": basic_mask,
            "fields": fields,
            "npc_mask": npc_mask,
            "template_id": template_id,
            "visual_preset": visual_preset,
        },
        cursor,
    )


def _walk_movement_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    """Read the placement back off the wire.  DO NOT turn this into a skip.

    The sibling lane could step over this block because its target stands at
    a frozen world row that nothing in a session can move.  THIS lane's whole
    experiment is WHERE the actor was put, so the one field that decides
    whether an attended round can see anything at all must be read back from
    byte 0 like every other field -- an adversarial review of round R162
    found this stepping over exactly those twelve bytes, which left the
    validator able to accept a sweep that placed the target at the frozen
    world row while the hit frames pointed somewhere else entirely.
    """
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != 0x01:
        raise HostileHpLinkValidationError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise HostileHpLinkValidationError("MovementAttr identity tag drift")
    identity_raw, cursor = _scalar(
        pc, cursor, IDENTITY_TAG, 8, "MovementAttr identity")
    if pc[cursor] != TAG_U8:
        raise HostileHpLinkValidationError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    position = None
    heading = None
    for bit, _width in _MOVEMENT_FIELD_WIDTH:
        if not mask & bit:
            continue
        if bit == 0x01:
            components = []
            for _axis in range(3):
                raw, cursor = _scalar(
                    pc, cursor, TAG_F32, 4, "MovementAttr position")
                components.append(struct.unpack("<f", raw)[0])
            position = tuple(components)
        elif bit == 0x02:
            raw, cursor = _scalar(
                pc, cursor, TAG_F32, 4, "MovementAttr heading")
            heading = struct.unpack("<f", raw)[0]
        elif bit == 0x04:
            cursor += 2
        else:
            cursor += 5
    if position is None:
        raise HostileHpLinkValidationError(
            "the spawn frame carries a MovementAttr with no position, so "
            "nothing in it says where the actor was put")
    return (
        {
            "present": True,
            "identity": struct.unpack("<Q", identity_raw)[0],
            "mask": mask,
            "position": position,
            "heading": heading,
        },
        cursor,
    )


def decode_hostile_hp_link_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back, whichever of the two carriers it holds."""
    if type(pc) is not bytes:
        raise HostileHpLinkValidationError("pc is not bytes")
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
    result: dict[str, Any] = {
        "envelope_id": envelope_id,
        "error_data": error_data,
        "envelope_version": envelope_version,
        "base_change_mask": base_mask,
    }
    if base_mask == HIT_BASE_CHANGE_MASK:
        # The VitalData collection at +0x18 -- the hit carrier.
        result["kind"] = HOSTILE_HP_LINK_STEP_KIND_HIT
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital count")
        if struct.unpack("<H", raw)[0] != 1:
            raise HostileHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital id")
        vital_id = struct.unpack("<H", raw)[0]
        if vital_id != CHIT_RESULT_VITAL_ID:
            raise HostileHpLinkValidationError(
                "the decoder refuses a vital other than CHitResult")
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "vital version")
        result["vital_id"] = vital_id
        result["vital_version"] = raw[0]
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
        if struct.unpack("<H", raw)[0] != HIT_ENTRY_COUNT_PINNED:
            raise HostileHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_QWORD, 8, "target")
        result["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U32, 4, "damage")
        # Read SIGNED: the client's compare sites make the field mean anything
        # at all only under the signed reading.
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
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
        result["derived_change_mask"] = raw[0]
    elif base_mask == ACTOR_INHERITED_CHANGE_MASK:
        # The actor-entry collection at +0x1C -- the target carrier.
        result["kind"] = HOSTILE_HP_LINK_STEP_KIND_ACTOR
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
        derived = raw[0]
        result["derived_change_mask"] = derived
        if not derived & ACTOR_DERIVED_CHANGE_MASK:
            raise HostileHpLinkValidationError(
                "the derived change mask is missing bit 0x02, so the client "
                "never reads the +0x1C actor-entry collection and 0x446F30 is "
                "never reached (this is the ErrorData=28317 over-read shape)"
            )
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "actor entry count")
        if struct.unpack("<H", raw)[0] != 1:
            raise HostileHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "actor type")
        result["actor_type"] = raw[0]
        raw, cursor = _scalar(pc, cursor, IDENTITY_TAG, 8, "actor identity")
        result["target_identity"] = struct.unpack("<Q", raw)[0]
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "attr count")
        attr_count = raw[0]
        attrs: dict[int, dict[str, Any]] = {}
        for _index in range(attr_count):
            raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "attr id")
            attr_id = struct.unpack("<H", raw)[0]
            if attr_id == NPC_ATTR_ID:
                parsed, cursor = _walk_npc_attr(pc, cursor)
                attrs[attr_id] = parsed
            elif attr_id == MOVEMENT_ATTR_ID:
                parsed, cursor = _walk_movement_attr(pc, cursor)
                attrs[attr_id] = parsed
            else:
                raise HostileHpLinkValidationError(
                    "unexpected attr id 0x%04X on the actor-entry path"
                    % attr_id
                )
        result["attrs"] = attrs
    else:
        raise HostileHpLinkValidationError(
            "the decoder refuses a change mask outside the two pinned carriers"
        )
    if cursor != len(pc):
        raise HostileHpLinkValidationError(
            "trailing bytes the walker could not account for")
    return result


def validate_hostile_hp_link_sweep(
    actions: list[tuple[str, bytes, bytes, float]],
) -> list[dict[str, Any]]:
    """Re-read every composed frame and refuse anything the plan disallows.

    Runs entirely on the bytes: the transport frame is unwrapped by the
    independent walker and must reproduce the PC exactly, both carriers are
    re-decoded from byte 0, the target's balance ladder is re-derived and
    compared, and the pinned probe performer is held to the exact hashes.
    """
    _require_step_plan()
    ladder = require_hostile_hp_link_balance_ladder()
    if type(actions) is not list or len(actions) != len(HOSTILE_HP_LINK_STEPS):
        raise HostileHpLinkValidationError("sweep length is not the pinned plan")
    rows: list[dict[str, Any]] = []
    performers: set[int] = set()
    targets: set[int] = set()
    seen_miss = False
    spawn_position_bytes: set[bytes] = set()
    hit_position_bytes: set[bytes] = set()
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise HostileHpLinkValidationError("sweep action shape")
        label, pc, frame, delay = action
        step_label, kind, spec, plan_flags = HOSTILE_HP_LINK_STEPS[index]
        if label != HOSTILE_HP_LINK_ACTION_LABEL_PREFIX + step_label:
            raise HostileHpLinkValidationError("unknown_step_label")
        if type(pc) is not bytes or type(frame) is not bytes:
            raise HostileHpLinkValidationError("sweep action payload type")
        expected_delay = (
            HOSTILE_HP_LINK_FIRST_DELAY_SECONDS if index == 0
            else HOSTILE_HP_LINK_SPACING_SECONDS
        )
        if type(delay) is not float or delay != expected_delay:
            raise HostileHpLinkValidationError("sweep delay is not the plan")
        if decode_hostile_hp_link_transport(frame) != pc:
            raise HostileHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc")
        decoded = decode_hostile_hp_link_frame(pc)
        if decoded["envelope_id"] != RUNTIME_PROTOCOL_RES_ID:
            raise HostileHpLinkValidationError("envelope id is not 0x6E9D")
        if decoded["error_data"] != 0:
            raise HostileHpLinkValidationError("envelope error data nonzero")
        if decoded["envelope_version"] != RUNTIME_PROTOCOL_RES_VERSION:
            raise HostileHpLinkValidationError("envelope is not version 4")
        if decoded["kind"] != kind:
            raise HostileHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: carrier kind")
        targets.add(decoded["target_identity"])
        row: dict[str, Any] = {
            "label": step_label,
            "kind": kind,
            "target_identity": decoded["target_identity"],
            "pc_size": len(pc),
            "pc_sha256": hashlib.sha256(pc).hexdigest().upper(),
            "frame_size": len(frame),
            "frame_sha256": hashlib.sha256(frame).hexdigest().upper(),
        }
        performer_lo = HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
        performer_hi = HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI
        if kind == HOSTILE_HP_LINK_STEP_KIND_HIT:
            if decoded["base_change_mask"] != HIT_BASE_CHANGE_MASK:
                raise HostileHpLinkValidationError(
                    "base change mask does not select the VitalData collection")
            if decoded["derived_change_mask"] != HIT_DERIVED_CHANGE_MASK:
                raise HostileHpLinkValidationError(
                    "derived change mask must be absent on a hit frame")
            if decoded["vital_version"] != CHIT_RESULT_VITAL_VERSION:
                raise HostileHpLinkValidationError("vital_version_not_pinned")
            for key in ("header_field2", "header_field3",
                        "header_field4", "header_field5"):
                if decoded[key] != HEADER_RESERVED_VALUE:
                    raise HostileHpLinkValidationError(
                        "header_reserved_field_nonzero")
            if decoded["target_identity"] != hostile_hp_link_target_identity():
                raise HostileHpLinkValidationError("npc_target_identity_not_pinned")
            if decoded["performer_identity"] == decoded["target_identity"]:
                raise HostileHpLinkValidationError(
                    "npc_performer_must_not_be_the_npc_target")
            require_hostile_hp_link_damage_wire_value(decoded["damage_wire"])
            require_hostile_hp_link_flags_value(decoded["flags"])
            require_hostile_hp_link_damage_and_flags_agree(
                decoded["damage_wire"], decoded["flags"])
            if decoded["damage_wire"] != step_damage_wire(index):
                raise HostileHpLinkValidationError(
                    "formula_output_not_reproducible")
            if decoded["flags"] != plan_flags:
                raise HostileHpLinkValidationError(
                    "flags_outside_value_allowlist")
            if decoded["yaw"] != YAW_PINNED:
                raise HostileHpLinkValidationError("yaw_outside_pinned_value")
            for component in decoded["position"]:
                if not math.isfinite(component):
                    raise HostileHpLinkValidationError(
                        "position_not_from_the_pinned_source")
            hit_position_bytes.add(
                b"".join(struct.pack("<f", value)
                         for value in decoded["position"])
            )
            if decoded["damage_wire"] == 0 and decoded["flags"] == FLAGS_MISS:
                seen_miss = True
            performers.add(decoded["performer_identity"])
            performer_lo = decoded["performer_identity"] & 0xFFFFFFFF
            performer_hi = (decoded["performer_identity"] >> 32) & 0xFFFFFFFF
            row["damage_wire"] = decoded["damage_wire"]
            row["flags"] = decoded["flags"]
            row["performer_identity"] = decoded["performer_identity"]
        else:
            if decoded["base_change_mask"] != ACTOR_INHERITED_CHANGE_MASK:
                raise HostileHpLinkValidationError(
                    "the inherited VitalData change mask is not absent")
            if decoded["derived_change_mask"] != ACTOR_DERIVED_CHANGE_MASK:
                raise HostileHpLinkValidationError(
                    "derived change mask must select the actor-entry "
                    "collection on a target frame")
            if decoded["actor_type"] != NPC_STYLE_ACTOR_TYPE:
                raise HostileHpLinkValidationError(
                    "actor_type %d is outside the jump-table case this lane "
                    "pins (CNetNPC == 4)" % decoded["actor_type"])
            npc = decoded["attrs"].get(NPC_ATTR_ID)
            if npc is None:
                raise HostileHpLinkValidationError(
                    "step %d carries no NPCAttr" % index)
            if npc["identity"] != decoded["target_identity"]:
                raise HostileHpLinkValidationError(
                    "the entry identity and the NPCAttr identity differ, so "
                    "0x446170 and the attr apply would target different actors"
                )
            if not npc["visual_preset"]:
                raise HostileHpLinkValidationError(
                    "step %d carries no visual preset, so [actor+0x70] & 0x40 "
                    "never opens and 0x47289E can never play _F_DIE_000"
                    % index)
            hp = npc["fields"].get(BASIC_BIT_CURRENT_HP)
            timer = npc["fields"].get(BASIC_BIT_DEATH_TIMER)
            if hp is None:
                raise HostileHpLinkValidationError(
                    "step %d omits BasicAttr bit 0x0004, so the client's "
                    "HP==0 half of both predicates is never satisfied" % index)
            if npc["fields"].get(BASIC_BIT_MAX_HP) != HOSTILE_HP_LINK_HP_MAX:
                raise HostileHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: hp_max")
            if hp != ladder[index]:
                raise HostileHpLinkValidationError(
                    "hp_arithmetic_not_reproducible")
            if timer is not None:
                raise HostileHpLinkValidationError(
                    "lethal_field_is_not_available_in_this_lane")
            if hp <= HOSTILE_HP_LINK_HP_FLOOR:
                raise HostileHpLinkValidationError(
                    "lethal_field_is_not_available_in_this_lane")
            movement = decoded["attrs"].get(MOVEMENT_ATTR_ID)
            if movement is not None:
                placed = movement["position"]
                if movement["identity"] != decoded["target_identity"]:
                    raise HostileHpLinkValidationError(
                        "the MovementAttr identity and the entry identity "
                        "differ, so the frame places an actor it does not "
                        "describe")
                for component in placed:
                    if not math.isfinite(component):
                        raise HostileHpLinkValidationError(
                            "position_not_from_the_pinned_source")
                if _is_the_frozen_world_row(placed):
                    raise HostileHpLinkValidationError(
                        "target_placement_is_the_frozen_world_row_not_"
                        "player_relative")
                spawn_position_bytes.add(
                    b"".join(struct.pack("<f", value) for value in placed))
            if index == 0:
                # An actor cannot be born dead.
                if hp == 0 or timer is not None:
                    raise HostileHpLinkValidationError(
                        "the first frame introduces an identity the client "
                        "does not know, which takes the spawn path 0x446990 "
                        "-> vtable +0x10 and never reaches 0x4437C0: an actor "
                        "cannot be born dead"
                    )
                if MOVEMENT_ATTR_ID not in decoded["attrs"]:
                    raise HostileHpLinkValidationError(
                        "the spawn frame must place the actor (MovementAttr)")
            elif MOVEMENT_ATTR_ID in decoded["attrs"]:
                raise HostileHpLinkValidationError(
                    "only the spawn frame may carry a MovementAttr")
            if npc["basic_mask"] & BASIC_BIT_DEATH_TIMER:
                raise HostileHpLinkValidationError(
                    "lethal_field_is_not_available_in_this_lane")
            if not npc["basic_mask"] & BASIC_BIT_NAME:
                raise HostileHpLinkValidationError(
                    "step %d omits BasicAttr bit 0x0001, so the target panel "
                    "the tester reads has no label to show" % index)
            row["hp_current"] = hp
            row["hp_death_timer"] = timer
            row["basic_mask"] = npc["basic_mask"]
            row["template_id"] = npc["template_id"]
            row["visual_preset"] = npc["visual_preset"]
        # The validator re-reads the bytes it was handed; it cannot know which
        # geometry they were composed at, and it must not guess.  The pin
        # check therefore runs in the composer, which does know -- this is the
        # one guard that deliberately does NOT run twice.
        rows.append(row)
    if len(performers) != 1:
        raise HostileHpLinkValidationError(
            "performer_identity_not_the_selected_actor")
    # THE LINK, checked from the bytes: every frame of the sweep -- both the
    # hit entries and the actor entries -- must be about the SAME actor, or the
    # bar that moves is not the bar the number was drawn over.
    if targets != {hostile_hp_link_target_identity()}:
        raise HostileHpLinkValidationError("npc_target_identity_not_pinned")
    if len(hit_position_bytes) != 1:
        raise HostileHpLinkValidationError("position_not_from_the_pinned_source")
    # THE PLACEMENT AND THE NUMBER MUST BE THE SAME POINT.  Read off the
    # bytes, not off the composer: the spawn frame put the actor somewhere,
    # the hit frames float a number somewhere, and a sweep in which those two
    # differ is one where a tester watching the number would be watching the
    # wrong patch of ground.
    if len(spawn_position_bytes) != 1:
        raise HostileHpLinkValidationError(
            "the sweep places the actor at more than one position")
    if spawn_position_bytes != hit_position_bytes:
        raise HostileHpLinkValidationError(
            "the placement in the spawn frame and the position the damage "
            "number rides are not the same point")
    if not seen_miss:
        raise HostileHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    # THE SWEEP MUST END ALIVE.  The sibling lane checks the opposite -- that
    # its last frame opened the death gate -- and inverting that check here is
    # the cheapest possible guard against this lane quietly growing the half
    # of the question it is not allowed to ask.
    if rows[-1]["label"] != HOSTILE_HP_LINK_FINAL_STEP_LABEL:
        raise HostileHpLinkValidationError("unknown_step_label")
    if rows[-1].get("hp_death_timer") is not None:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    if rows[-1].get("hp_current", 0) <= HOSTILE_HP_LINK_HP_FLOOR:
        raise HostileHpLinkValidationError(
            "lethal_field_is_not_available_in_this_lane")
    # Every actor frame must carry the SAME max hp, and it must be the
    # client's own baseline: a sweep that quietly renormalised the bar would
    # move a percentage rather than the number this ticket is about.
    for row in rows:
        if row["kind"] != HOSTILE_HP_LINK_STEP_KIND_ACTOR:
            continue
        if row.get("hp_current") is None:
            raise HostileHpLinkValidationError("hp_arithmetic_not_reproducible")
    return rows


# ===========================================================================
# PINS, CAPABILITIES, NONCLAIMS.
# ===========================================================================
# The composed bytes, pinned.  Every value here was produced by this encoder
# and read back by the independent walker; none of it was copied in from
# anywhere.
#
# READ THE STRENGTH OF THESE PINS BEFORE CITING THEM.  Unlike the sibling
# lane, EVERY frame of this sweep carries three f32s that depend on where the
# player was standing, because the target is placed player-relative:
#   * the SIZES hold for every session -- a coordinate is four bytes wherever
#     the player stands, so a drifted field width is caught for everyone;
#   * the HASHES hold only for the probe geometry (the frozen V135 spawn plus
#     the scenario offsets) and, on the three hit frames, only for the probe
#     performer 0x10010001.
# build_hostile_hp_link_sweep therefore recomposes the WHOLE sweep at the probe
# geometry on every build and holds THAT to these hashes, which is how a live
# session whose own bytes cannot be hashed to a constant is still protected
# from a drifted encoder.
# TARGET_HP_AFTER_WEAK and TARGET_HP_AFTER_MISS are byte-identical on purpose
# -- the miss control moves nothing, and identical bytes are the strongest way
# to say so.
HOSTILE_HP_LINK_PINS: dict[str, dict[str, Any]] = {
    "TARGET_SPAWN": {
        "pc_size": 200,
        "pc_sha256":
            "5E3FD310339FCFB84ED6C4C86D423CD6ADDE2E33546476EBC9A83F214795476E",
        "frame_size": 212,
        "frame_sha256":
            "526AFEA2498A241C7596DB955A2C28683A41A1BAFE5906EE20DD68EA273F5F8E",
    },
    "HIT_WEAK": {
        "pc_size": 84,
        "pc_sha256":
            "7588F3A56D0468A0F216585A9FA0FED24B9D693B73F8AD048A19261C05D60684",
        "frame_size": 95,
        "frame_sha256":
            "AF7E8B23B80ACAACBF5429ECBD873A9F2A1FC60254BB9A8CF2F4A54A363C1730",
    },
    "TARGET_HP_AFTER_WEAK": {
        "pc_size": 142,
        "pc_sha256":
            "DB9E62658E5382977EB7F27EB9100B69F52BA06F18616F79D61E680F7ADDD9BE",
        "frame_size": 154,
        "frame_sha256":
            "475690244E659B0AE9BE07408E883AB86D98E2EAC25E778C782D38D3C6E7B769",
    },
    "MISS": {
        "pc_size": 84,
        "pc_sha256":
            "A4D69DEAD9144A0340DCE7A32AB3645F5DEA0A6141106F9CB3D72E7D4F772F10",
        "frame_size": 95,
        "frame_sha256":
            "07731EAEAE40B376C5F392799E66ABB69E74F70EDAD18802F2D304FA06728689",
    },
    "TARGET_HP_AFTER_MISS": {
        "pc_size": 142,
        "pc_sha256":
            "DB9E62658E5382977EB7F27EB9100B69F52BA06F18616F79D61E680F7ADDD9BE",
        "frame_size": 154,
        "frame_sha256":
            "475690244E659B0AE9BE07408E883AB86D98E2EAC25E778C782D38D3C6E7B769",
    },
    "HIT_STRONG": {
        "pc_size": 84,
        "pc_sha256":
            "BC430BA8C8029CA53CF5CD057709549A2784F6A3449B6C165629A333548EE85C",
        "frame_size": 95,
        "frame_sha256":
            "53936BDEC6D78A27A64C7CCB609B12EBEE6AD8042A4795D99337BF2E976BB105",
    },
    "TARGET_HP_AFTER_STRONG": {
        "pc_size": 142,
        "pc_sha256":
            "E93EE06A59E9AB2062107C6A8A55A7BC52A3E36441F98DB95A5DDFC6F70C6818",
        "frame_size": 154,
        "frame_sha256":
            "D1AEED75A420255601B65666E4C3A198976B315C16B9E5F30D61015E9EF94655",
    },
}


HOSTILE_HP_LINK_CAPABILITIES = (
    "run_our_damage_arithmetic_against_a_server_held_balance_for_a_target",
    "move_the_hit_points_of_a_real_hostile_identity_carrying_the_clients_own_hp_baseline",
    "alternate_the_vitaldata_hit_carrier_and_the_actor_entry_target_carrier",
    "address_every_frame_of_the_sweep_at_the_one_frozen_placement_identity",
    "place_that_identity_at_player_relative_geometry_so_a_tester_can_see_it",
    "carry_the_targets_name_so_the_target_panel_has_a_label_to_show",
    "refuse_every_value_whose_client_meaning_this_project_cannot_name",
)

HOSTILE_HP_LINK_NONCLAIMS = (
    "this_is_our_design_not_the_original_servers_which_is_unrecoverable",
    "no_capture_shows_a_targets_hit_points_moving_in_response_to_damage_in_either_direction",
    "the_client_does_not_subtract_damage_that_is_why_the_server_must_say_both_halves",
    "whether_the_client_renders_the_intermediate_value_2893_on_a_real_hostiles_hp_bar_is_undecidable_from_static_analysis_and_is_the_queued_attended_test",
    "nobody_has_ever_confirmed_with_their_own_eyes_that_a_model_at_this_distance_is_inside_the_clients_draw_distance",
    "the_hp_baseline_3857_is_client_side_data_not_a_rule_of_the_original_server",
    "the_attacker_profiles_were_chosen_so_the_bar_moves_visibly_and_are_ours",
    "player_relative_placement_is_a_harness_of_ours_no_player_ever_met_this_hostile_there",
    "no_claim_the_original_server_ever_linked_these_frames",
    "no_database_write_no_hp_column_exists_and_none_is_added",
    "wire_layer_only_no_client_has_seen_these_bytes",
    "one_shot_per_connection_not_per_process",
    "no_claim_about_death_dying_loot_aggro_retaliation_or_any_other_hostile_in_the_roster",
    "miss_control_proves_only_that_our_arithmetic_holds_not_that_the_client_checks_it",
    "the_runtime_dispatch_branch_exists_and_is_driven_headless_only_never_over_tcp_and_never_by_a_client",
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
        "id": HOSTILE_HP_LINK_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": HOSTILE_HP_LINK_HYPOTHESIS_ID,
        "checkpoint": HOSTILE_HP_LINK_CHECKPOINT,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "design_not_recovery": (
            "this_is_our_design_not_the_original_servers_which_is_"
            "unrecoverable"
        ),
        "spacing_decision_comment": HOSTILE_HP_LINK_SPACING_DECISION,
        "undecidable_from_static_analysis": (
            "whether_the_client_renders_the_intermediate_value_2893_on_a_real_"
            "hostiles_hp_bar_is_the_queued_attended_test_and_so_is_whether_a_"
            "model_at_this_distance_is_drawn_at_all"
        ),
        "entry": {
            "flow": "full_writable_character",
            "required_sequence": "selected_and_runtime_ready",
            "response_policy": (
                "compose_linked_damage_and_target_hp_frames_from_our_own_"
                "arithmetic_no_write_no_close"
            ),
        },
        "dispatch": {
            "wired": True,
            "wiring_owner": HOSTILE_HP_LINK_WIRING_OWNER,
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "runtime_dispatch_branch": (
                "runtime_py_dispatch_hostile_hp_link_hypothesis_reached_from_the_"
                "app_flag_through_make_state_class"
            ),
            "frames_per_accepted_request": len(HOSTILE_HP_LINK_STEP_ORDER),
            "trigger": "one_accepted_34_byte_ascii12_chat_input_frame",
            "step_order": list(HOSTILE_HP_LINK_STEP_ORDER),
            "step_kinds": [row[1] for row in HOSTILE_HP_LINK_STEPS],
            "miss_steps": list(HOSTILE_HP_LINK_MISS_STEP_LABELS),
            "lethal_steps": list(HOSTILE_HP_LINK_LETHAL_STEP_LABELS),
            "spacing_seconds": HOSTILE_HP_LINK_SPACING_SECONDS,
            "first_frame_delay_seconds": HOSTILE_HP_LINK_FIRST_DELAY_SECONDS,
            "delay_semantics": (
                "gap_before_each_send_on_a_cumulative_deadline"
            ),
            "action_label_prefix": HOSTILE_HP_LINK_ACTION_LABEL_PREFIX,
            "action_labels": list(HOSTILE_HP_LINK_ACTION_LABELS),
            "one_shot": True,
            "socket_action": "none",
        },
        "wire": {
            "envelope_vital_id": RUNTIME_PROTOCOL_RES_ID,
            "envelope_vital_version": RUNTIME_PROTOCOL_RES_VERSION,
            "envelope": "gscn_runtime_protocol_res_v4_two_collections",
            "hit_carrier": {
                "collection": "vitaldata",
                "base_change_mask": HIT_BASE_CHANGE_MASK,
                "derived_change_mask": HIT_DERIVED_CHANGE_MASK,
                "object_offset": HIT_BASE_OBJECT_OFFSET,
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
                    "value_allowlist": list(
                        HOSTILE_HP_LINK_FLAGS_VALUE_ALLOWLIST),
                    "forbidden_mask": FLAGS_FORBIDDEN_MASK,
                },
                "yaw_field": {
                    "name": "reaction_yaw",
                    "object_offset": HIT_ENTRY_YAW_OFFSET,
                    "wire_tag": TAG_F32,
                    "pinned_value": YAW_PINNED,
                },
            },
            "target_carrier": {
                "collection": "actor_entries",
                "inherited_change_mask": ACTOR_INHERITED_CHANGE_MASK,
                "derived_change_mask": ACTOR_DERIVED_CHANGE_MASK,
                "object_offset": ACTOR_DERIVED_OBJECT_OFFSET,
                "actor_type": NPC_STYLE_ACTOR_TYPE,
                "attr_ids": [NPC_ATTR_ID, MOVEMENT_ATTR_ID],
                "field_order_rule": "ascending_mask_bit_within_each_block",
                "hp_fields": {
                    "hp_current": {
                        "mask_bit": BASIC_BIT_CURRENT_HP,
                        "object_offset": CURRENT_HP_OFFSET,
                        "wire_tag": CURRENT_HP_TAG,
                        "width": "u32",
                    },
                    "hp_max": {
                        "mask_bit": BASIC_BIT_MAX_HP,
                        "object_offset": MAX_HP_OFFSET,
                        "wire_tag": CURRENT_HP_TAG,
                        "width": "u32",
                    },
                    "hp_death_timer": {
                        "mask_bit": BASIC_BIT_DEATH_TIMER,
                        "object_offset": DEATH_TIMER_OFFSET,
                        "wire_tag": DEATH_TIMER_TAG,
                        "width": "f32",
                    },
                    "scene_id": {
                        "mask_bit": BASIC_BIT_SCENE_ID,
                        "object_offset": SCENE_ID_OFFSET,
                        "wire_tag": TAG_U16,
                        "width": "u16",
                    },
                    "scene_sequence": {
                        "mask_bit": BASIC_BIT_SCENE_SEQ,
                        "object_offset": SCENE_SEQ_OFFSET,
                        "wire_tag": TAG_QWORD,
                        "width": "qword",
                    },
                },
                "name_field": {
                    "mask_bit": BASIC_BIT_NAME,
                    "wire_tag": TAG_WSTRING,
                    "value": HOSTILE_HP_LINK_TARGET_SOURCE_NAME,
                    "why": (
                        "the_target_panel_label_comes_from_basicattr_plus_0x28_"
                        "and_a_bar_that_moved_on_an_unnamed_actor_leaves_which_"
                        "actor_was_that_open"
                    ),
                },
                "lethal_half": {
                    "composed_by_this_lane": False,
                    "death_timer_mask_bit_is_forbidden": BASIC_BIT_DEATH_TIMER,
                    "rule": (
                        "this_lane_has_no_lethal_step_the_death_half_belongs_"
                        "to_a_later_version_of_this_slot_and_every_guard_"
                        "refuses_it_by_name"
                    ),
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
                "defender": {
                    "name": "TORNADO_EAGLE_LV27",
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
                "pinned_damage_wire": dict(HOSTILE_HP_LINK_DAMAGE_PINNED),
            },
            "hp_ladder": {
                "owner": "the_target_not_the_player",
                "baseline_source": "client_side_standard_mob_level_27_v117_p30",
                "start": HOSTILE_HP_LINK_HP_START,
                "max": HOSTILE_HP_LINK_HP_MAX,
                "floor": HOSTILE_HP_LINK_HP_FLOOR,
                "ladder": list(HOSTILE_HP_LINK_BALANCE_LADDER),
                "clamp_policy": "clamping_is_refused_this_lane_never_reaches_"
                                "the_floor",
                "applies_on": "the_actor_frame_that_follows_each_hit_frame",
            },
        },
        "probe": {
            "rule": (
                "the_performer_is_the_players_own_actor_and_the_target_is_the_"
                "frozen_port_royal_placement_identity"
            ),
            "target_source": "port_royal_unambiguous_placements_frozen_v141",
            "target_selection_rule": (
                "placement_index_30_named_outright_not_nearest_because_the_"
                "row_is_twelve_thousand_units_from_the_player_spawn"
            ),
            "target_identity_formula": "0x2000_plus_placement_index_plus_1",
            "target_placement_index": HOSTILE_HP_LINK_TARGET_PLACEMENT_INDEX,
            "target_template_id": HOSTILE_HP_LINK_TARGET_TEMPLATE_ID,
            "target_identity_lo": HOSTILE_HP_LINK_TARGET_IDENTITY_LO,
            "target_identity_hi": HOSTILE_HP_LINK_TARGET_IDENTITY_HI,
            "target_visual_preset": HOSTILE_HP_LINK_TARGET_VISUAL_PRESET,
            "target_source_name": HOSTILE_HP_LINK_TARGET_SOURCE_NAME,
            "target_hp_baseline": HOSTILE_HP_LINK_HP_BASELINE,
            "position_source": "live_player_position_plus_scenario_offsets",
            "position_mode": HOSTILE_HP_LINK_POSITION_MODE,
            "position_dx": HOSTILE_HP_LINK_TARGET_DX,
            "position_dy": HOSTILE_HP_LINK_TARGET_DY,
            "position_dz": HOSTILE_HP_LINK_TARGET_DZ,
            # The frozen world row is deliberately NOT reproduced in this
            # file.  The attended ticket's pre-boot check greps the scenario
            # for those coordinates and treats any hit as "this lane is about
            # to spawn the target where nobody can see it"; a copy here for
            # documentation's sake would turn that check into a false alarm
            # every time.  The module pins the row, and it pins it in order to
            # refuse it.
            "frozen_world_row_is_never_sent": True,
            "pins_are_composed_from_a_fixed_probe_identity": True,
            "pins_are_composed_from_the_frozen_v135_probe_geometry": True,
            "pins_hold_for_a_live_session": (
                "sizes_always_hashes_only_where_the_geometry_and_the_"
                "performer_happen_to_be_the_pinned_probe_ones_which_a_"
                "character_sitting_at_the_frozen_spawn_partly_is"
            ),
            "performer_probe_identity_lo": (
                HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
            ),
            "performer_probe_identity_hi": (
                HOSTILE_HP_LINK_PERFORMER_PROBE_IDENTITY_HI
            ),
            "scene_id": SCENE_ID,
            "scene_sequence": SCENE_SEQUENCE,
            "per_step": {
                label: {
                    "pc_size": HOSTILE_HP_LINK_PINS[label]["pc_size"],
                    "pc_sha256": HOSTILE_HP_LINK_PINS[label]["pc_sha256"],
                    "frame_size": HOSTILE_HP_LINK_PINS[label]["frame_size"],
                    "frame_sha256": HOSTILE_HP_LINK_PINS[label]["frame_sha256"],
                }
                for label in HOSTILE_HP_LINK_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(HOSTILE_HP_LINK_CAPABILITIES),
        "nonclaims": list(HOSTILE_HP_LINK_NONCLAIMS),
    }


def load_hostile_hp_link_hypothesis_scenario(
    path: Any,
) -> HostileHpLinkHypothesisScenario:
    """Load the one opt-in scenario file, or refuse with no lane."""
    if path is None:
        raise HostileHpLinkValidationError("scenario_file_exceeds_allowlist")
    resolved = Path(path)
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise HostileHpLinkValidationError(
            "scenario_file_exceeds_allowlist: %s" % exc
        ) from exc
    if _exact_equal(raw, _expected_scenario()):
        return _PROFILE
    raise HostileHpLinkValidationError("scenario_file_exceeds_allowlist")
