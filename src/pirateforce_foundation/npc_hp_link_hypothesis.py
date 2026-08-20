"""NPC-HP-LINK-001: THIS IS OUR DESIGN, NOT THE ORIGINAL SERVER'S, WHICH IS
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
the client never subtracts it from anything.

On 2026-08-20 an attended in-game test (the GT-027 rerun, confirmed on video)
proved the consequence on a real screen: after cumulative damage of
``63 + 379 + 63 = 505`` delivered as ``CHitResult`` frames against a SELECTED
NPC target, **the target's HP bar did not move by a single unit** -- 100 Lv.1,
full bar, before and after.  That is the only thing proven so far, and it is a
negative.  It is also exactly why the server has to SAY BOTH HALVES itself.

That observation is WRITTEN DOWN, with its provenance, in
``reports/PF_NPC_HP_LINK029_GT027_RERUN_ATTENDED_RESULT_20260820.md``.  Read
the caveat at the top of it before citing it: the result is the tester's
testimony plus five hashed screenshots, NOT a re-derivable receipt -- that
round produced no teardown, no console tail, no post-run DB snapshot and no
capture file -- and it is a CLIENT-OBSERVABLE-LAYER negative that must never
be cited as wire-layer evidence.

WHAT THIS LANE ADDS THAT NO LANE IN THIS TREE HAS EVER DONE
-----------------------------------------------------------
HYP-PF-026, the damage-hp-link lane, already links damage to hit points -- but
only for the PLAYER's own actor, on the base ``VitalData`` carrier, with
``HP_LINK_DERIVED_CHANGE_MASK = 0x00`` (no actor-entry collection on that
lane).  That lane's own containment test requires that exactly two foundation
modules mention it BY MODULE NAME, which is why this paragraph names it by
hypothesis id instead: naming it here would turn a neighbour's guard red for
no reason, and a docstring is not worth a false alarm.  **Nothing in this tree has ever moved a TARGET's hit points.**  That is
the gap this lane closes, and it closes it by alternating the two carriers this
project has already rendered on a real screen, against the SAME frozen Port
Royal placement NPC identity the damage lane's ``npc_sweep`` profile already
targets:

  * the floating damage number rides ``CHitResult`` 0x16F7 version 0 inside the
    **VitalData** collection (BASE change mask ``0x02``, object ``this+0x18``),
    performer = the player, target = the fixed placement identity ``0x2001``;
  * the target's HP bar rides the **actor-entry** collection (DERIVED change
    mask ``0x02``, object ``this+0x1C``, ``actor_type`` 4 = CNetNPC) carrying an
    ``NPCAttr`` whose ``BasicAttr`` ``hp_current`` is a SERVER-HELD balance --
    the carrier HYP-PF-023 drove to a real corpse at GT-022.

    NOTE, because three rounds have now confused these two collections: the
    VitalData collection (BASE mask ``0x02``, ``+0x18``) is NOT the actor-entry
    collection (DERIVED mask ``0x02``, ``+0x1C``).  Same bit number, different
    mask byte, different reader.  This lane is the first in the tree to put
    BOTH on the same wire in the same sweep, so it names them apart everywhere.

THE PLAN -- EIGHT FRAMES, ONE TARGET, ONE BALANCE
--------------------------------------------------
The server keeps one integer balance for the TARGET and this module is the only
thing that moves it.  A hit frame ANNOUNCES a number; the actor-entry frame
that follows it APPLIES that same number to the balance and shows the result on
the target's own bar.  The ladder of balances after each step is pinned,
re-derived by the arithmetic engine on EVERY composition, and the whole sweep
is refused on any mismatch:

    TARGET_SPAWN          balance 100   the HYP-PF-023 SPAWN body, alive
    HIT_WEAK              damage -63    our formula, MOB_WEAK vs the defender
    TARGET_HP_AFTER_WEAK  balance 37    100 - 63, applied by the server
    MISS                  damage 0      the control frame
    TARGET_HP_AFTER_MISS  balance 37    a miss moves nothing -- and the frame
                                        is deliberately BYTE-IDENTICAL to the
                                        one above it
    HIT_STRONG            damage -379   our formula, MOB_STRONG vs the defender
    TARGET_HP_ZERO_DYING  balance 0     37 - 379 clamps at the floor, and the
                                        SAME frame arms the 20.0 s dying timer
                                        (the HYP-PF-023 DYING_LATCH shape)
    TARGET_DYING_ELAPSED  balance 0     timer 0.0 (the DEATH_TASK shape)

``MISS`` and ``TARGET_HP_AFTER_MISS`` are not filler: a sweep in which every
frame lowers the bar cannot tell a tester whether the client is reading our
arithmetic or animating something of its own, so the validator refuses a sweep
without the miss pair.  What the pair PROVES is bounded and written into the
nonclaims: it shows only that OUR arithmetic holds a miss at zero, not that the
client checks any of it.

SPACING -- 6.0 s, AND WHY IT IS NOT 15.0
-----------------------------------------
``first_frame_delay_seconds`` 0.0, ``spacing_seconds`` 6.0, cumulative-deadline
semantics (the same profile the death lane ships).  This lane deliberately does
NOT use the stretched 15-second photography profile the damage lane's
``npc_sweep`` carries.  Panya ruled on 2026-08-20 that **stretching frame
spacing for the human tester is wasted effort, because the event itself is
short; the correct fix is recording video**, which the GT-027 rerun did.  The
spacing is therefore the short one and the evidence discipline is the camera.

COPIED, NEVER IMPORTED
----------------------
Every ``CHitResult`` frame this module composes is byte-identical to the
DAMAGE-MODEL lane's own composer for the same identity and step, and every
actor-entry frame is byte-identical to the RUNTIMERES-DEATH lane's own composer
for the same step (for the two intermediate 37-HP frames, which have no
counterpart step in that lane, the ``NPCAttr`` body is byte-identical to the
frozen ``legacy.make_npc_attr`` projection that lane uses as its own baseline
oracle).  The constants are COPIED here with drift tests in ``tests/``, never
imported: cross-lane byte-equality guards run in both directions.  What that
actually buys, stated exactly -- an earlier draft of this paragraph overclaimed
it and an adversarial review measured the truth: a drift in a PARENT turns that
parent's own verifier red AND turns this lane's verifier red, because this
lane's section G recomposes the parent's frames and diffs them.  A drift in
THIS lane turns THIS lane's verifier red and nothing else: the parents do not
import, read or check this module, so mutating a constant here leaves every
parent tool green.  Copying is safe because the guard is here, not because two
tools are guaranteed to fail together.

FAIL CLOSED
-----------
* ``production_allowed`` is ``False`` and the scenario file must say so too.
* The scenario JSON is compared against an EXACT allowlist tree -- one extra or
  missing key anywhere and the loader refuses.
* Every PUBLIC encoder on this lane refuses without the wire unlock token, and
  the only minter of that token takes the allowlisted scenario object, compared
  by IDENTITY -- a value-equal forgery is refused.  Stated exactly, because an
  earlier draft of this line said "no byte can be composed without the unlock"
  and that is not what the code guarantees: the PRIVATE body builders
  (``_compose_npc_attr`` and its siblings) take no unlock argument and will
  return a body if an in-process caller reaches for them directly, and the
  module-global scenario profile means the token can be minted without opening
  the scenario file.  Both parents behave the same way; this is the tree's
  convention, and the boundary it defends is the process, not the function.
* The lethal fields -- ``hp_current`` at the floor, or ANY death-timer field --
  may only be composed for the two step labels the plan declares lethal.
* Every composed sweep is re-read by an independent walker (both carriers, from
  byte 0, plus the outer transport frame down to the raw literal) and compared
  against ``NPC_HP_LINK_PINS`` before anything is returned.
* Any refusal is a NAMED event.  There is no silent fallback anywhere.

WHAT THIS DOES NOT DO
---------------------
It writes nothing: there is no HP column in any table of this project and this
lane does not add one -- the target's balance lives in this module's arithmetic
for the duration of one sweep and nowhere else.  It claims nothing about the
original server ever linking these two carriers; the link is OUR design.  It
composes nothing for any path OUT of the death window.  And the load-bearing
open question is stated plainly here and in the scenario, the ledger entry and
the report alike: **whether the client renders the intermediate value 37 on the
target's HP bar is UNDECIDABLE from static analysis and is the queued attended
test.**  The only thing proven so far is the negative -- 505 damage, and the
bar did not move.
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

NPC_HP_LINK_SCENARIO_ID = "npc_hp_link_hypothesis_target_sweep"
# PF-HYPOTHESIS-LEDGER: HYP-PF-029 active
# Registered in docs/HYPOTHESIS_LEDGER.json by the round-111 append.  The
# annotation above and that entry's source_refs bind each other both ways:
# removing either one turns tools/verify_hypothesis_ledger.py red.
NPC_HP_LINK_HYPOTHESIS_ID = "HYP-PF-029"
NPC_HP_LINK_CHECKPOINT = "NPC-HP-LINK-001"
NPC_HP_LINK_DISPATCH_KWARG = "npc_hp_link_hypothesis_scenario"
NPC_HP_LINK_EVENT_NAME = "npc_hp_link_hypothesis_target_sweep_sent"
NPC_HP_LINK_WIRING_OWNER = "npc_hp_link_002_round_111"


class NpcHpLinkValidationError(ValueError):
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
NPC_HP_LINK_FRAME_MAGIC = 0x5F253EAC

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

# Copied, not imported, from the damage-model lane.  Only the two flag words
# this plan uses are allowed here: the reaction word 0x0009 belongs to that
# lane's fourth step and this lane has no fourth hit.
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
NPC_HP_LINK_FLAGS_VALUE_ALLOWLIST = (FLAGS_MISS, FLAGS_HIT)
FLAGS_FORBIDDEN_MASK = 0xF184
FLAGS_BIT_APPLY = 0x0001
YAW_PINNED = 0.0

DAMAGE_WIRE_MAX = 0                   # positive is refused: meaning unknown
DAMAGE_WIRE_MIN = -1_000_000
INT32_MIN = -2147483648


# ===========================================================================
# OUR FORMULA.  Copied, not imported, from HYP-PF-026 (which copied it from the
# damage-model lane); the drift test lives in tests/.  Every number here was
# chosen by this project.  -63 and -379 are DERIVED by the function below on
# every call, never typed into a step row.
# ===========================================================================
ATK_BASE = 100
K_ATK_STR = 7
K_ATK_LV = 3
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1

ATTACKER_MOB_WEAK_LEVEL = 1
ATTACKER_MOB_WEAK_ABILITY_STR = 3
ATTACKER_MOB_STRONG_LEVEL = 20
ATTACKER_MOB_STRONG_ABILITY_STR = 40
DEFENDER_LEVEL = 7
DEFENDER_ABILITY_CON = 22

# (level, ability_str) per named attacker.
NPC_HP_LINK_ATTACKER_PROFILES = {
    "MOB_WEAK": (ATTACKER_MOB_WEAK_LEVEL, ATTACKER_MOB_WEAK_ABILITY_STR),
    "MOB_STRONG": (ATTACKER_MOB_STRONG_LEVEL, ATTACKER_MOB_STRONG_ABILITY_STR),
}
# HYP-PF-026's pinned-value cross-check, kept: the two wire values the formula
# must reproduce, refused on any mismatch.
NPC_HP_LINK_DAMAGE_PINNED = {"MOB_WEAK": -63, "MOB_STRONG": -379}


def compute_npc_hp_link_attack(level: int, ability_str: int) -> int:
    """OUR attack number.  Not the client's, which has none."""
    return ATK_BASE + K_ATK_STR * ability_str + K_ATK_LV * level


def compute_npc_hp_link_defense(level: int, ability_con: int) -> int:
    """OUR defense number."""
    return DEF_BASE + K_DEF_CON * ability_con + K_DEF_LV * level


def compute_npc_hp_link_damage_wire(attacker_name: Any) -> int:
    """OUR damage for one named attacker, as the NEGATIVE wire integer.

    Recomputed from the formula constants on every call and compared against
    the pinned value, so a drifted constant can never ship a frame.
    """
    if attacker_name not in NPC_HP_LINK_ATTACKER_PROFILES:
        raise NpcHpLinkValidationError("unknown_step_label")
    level, ability_str = NPC_HP_LINK_ATTACKER_PROFILES[attacker_name]
    rolled = compute_npc_hp_link_attack(level, ability_str) - (
        compute_npc_hp_link_defense(DEFENDER_LEVEL, DEFENDER_ABILITY_CON)
    )
    if rolled < MIN_HIT:
        rolled = MIN_HIT
    wire = require_npc_hp_link_damage_wire_value(-rolled)
    if wire != NPC_HP_LINK_DAMAGE_PINNED[attacker_name]:
        raise NpcHpLinkValidationError("formula_output_not_reproducible")
    return wire


def require_npc_hp_link_damage_wire_value(value: Any) -> int:
    """Every refusal the signed i32 at +0x08 can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise NpcHpLinkValidationError("damage_not_integer")
    if value > DAMAGE_WIRE_MAX:
        raise NpcHpLinkValidationError(
            "damage_positive_heal_semantics_unknown")
    if value == INT32_MIN:
        raise NpcHpLinkValidationError("damage_is_int32_min")
    if value < DAMAGE_WIRE_MIN:
        raise NpcHpLinkValidationError("damage_below_safe_band")
    return value


def require_npc_hp_link_flags_value(value: Any) -> int:
    """Every refusal the u16 flag word at +0x1C can produce, each named."""
    if type(value) is not int or type(value) is bool:
        raise NpcHpLinkValidationError("flags_not_u16")
    if not 0 <= value <= 0xFFFF:
        raise NpcHpLinkValidationError("flags_not_u16")
    if value & FLAGS_FORBIDDEN_MASK:
        raise NpcHpLinkValidationError("flags_forbidden_bit")
    if value not in NPC_HP_LINK_FLAGS_VALUE_ALLOWLIST:
        raise NpcHpLinkValidationError("flags_outside_value_allowlist")
    return value


def require_npc_hp_link_damage_and_flags_agree(
    damage_wire: int, flags: int,
) -> None:
    """The number and the flag word have to tell the same story."""
    if damage_wire == 0 and flags & FLAGS_BIT_APPLY:
        raise NpcHpLinkValidationError("damage_zero_with_apply_flag")
    if damage_wire != 0 and not flags & FLAGS_BIT_APPLY:
        raise NpcHpLinkValidationError("damage_nonzero_without_apply_flag")


# ===========================================================================
# CARRIER TWO: the actor-entry NPCAttr delta.
# Copied, not imported, from the runtimeres-death lane (HYP-PF-023); the drift
# and byte-equality tests live in tests/.  The block order is the DBAttribute
# u8 mask + identity qword, then the BasicAttr u16 mask and its fields in
# ascending mask-bit order, then the NPCAttr u8 mask and its fields.
# ===========================================================================
BASIC_ATTR_MASK_TAG = 0x12
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
DEATH_TIMER_WIDTH = 4
SCENE_ID_OFFSET = 0x5C
SCENE_SEQ_OFFSET = 0x60

NPC_BIT_TEMPLATE = 0x01            # u16 tag 0x12 @ +0x78
NPC_BIT_VISUAL_PRESET = 0x04       # wstring tag 0x48 @ +0x7C
NPC_ATTR_MASK_TAG = 0x0B
DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
IDENTITY_TAG = 0x32
FULL_MOVEMENT_MASK = 0xFF

# Copied, not imported, from the lethal side of the runtimeres-death lane.
# THE POLARITY IS INVERTED FROM INTUITION and is the single fact most likely to
# be got wrong: actor vtable +0x40 (0x43BDA0) is HP == 0 AND timer > 0.0f and
# latches [actor+0x70] |= 0x200 (the DYING latch); actor vtable +0x3C
# (0x43BD70) is HP == 0 AND timer <= 0.0f and is what gates the
# CActorTask_Dead construction that plays L"_F_DIE_000".  The two are mutually
# exclusive on any one snapshot, so the sweep must send BOTH sides in order:
# positive first (latch), then <= 0 (task).
DYING_LATCH_TIMER_SECONDS = 20.0
DEATH_TASK_TIMER_SECONDS = 0.0
DEATH_TASK_TIMER_CEILING = 0.0
DYING_LATCH_PREDICATE_VA = 0x43BDA0        # actor vtable +0x40
DEATH_TASK_PREDICATE_VA = 0x43BD70         # actor vtable +0x3C
ZERO_FLOAT_CONSTANT_VA = 0xF0989C
# The elapsed frame must pack to exactly tag 0x2A plus four zero bytes;
# negative zero packs differently and is refused.
NPC_HP_LINK_TIMER_ELAPSED_WIRE_BYTES = bytes.fromhex("2a00000000")


# ===========================================================================
# THE TARGET.  Copied, not imported: the identity and the placement pin both
# come from the neighbouring lanes and NOTHING here is invented.  0x2001 is
# ``0x2000 + placement_index + 1``, the first Port Royal placement -- the
# identity HYP-PF-023 drives and the identity the HYP-PF-024 npc_sweep profile
# already addresses.  The selection rule is the same "nearest frozen placement
# to the frozen V135 player spawn" rule population.py uses, and the resolved
# answer is pinned so a drift in either frozen source turns this lane RED
# instead of silently hitting a different NPC in a different place.
# ===========================================================================
NPC_HP_LINK_TARGET_IDENTITY_LO = 0x2001
NPC_HP_LINK_TARGET_IDENTITY_HI = 0
NPC_HP_LINK_TARGET_PLACEMENT_INDEX = 0
NPC_HP_LINK_TARGET_TEMPLATE_ID = 1
NPC_HP_LINK_TARGET_VISUAL_PRESET = "P_MALE_002_000_SP1"
NPC_HP_LINK_TARGET_SOURCE_NAME = "Navy Transfer"

# The performer stays the PLAYER's own actor: one side of a CHitResult frame
# must be the player or the six-stage visibility filter at 0x43FEF0 draws
# nothing at all (the round-93 static pass, carried into the npc_sweep
# profile).  The pins are composed from the canonical smoke identity the
# frozen V25 create wire commits, exactly as every neighbouring lane does.
NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO = 0x10010001
NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI = 0


@dataclass(frozen=True)
class NpcHpLinkTarget:
    """The frozen placement this sweep hits, resolved and pinned."""

    placement_index: int
    template_id: int
    actor_identity: int
    x: float
    y: float
    z: float
    visual_preset: str
    source_name: str
    scene_id: int
    scene_sequence: int


def resolve_npc_hp_link_target(legacy: Any) -> NpcHpLinkTarget:
    """Pick the single frozen placement nearest the frozen player spawn."""
    placements = load_port_royal_placements(legacy)
    px = float(legacy.V135_PLAYER_X)
    py = float(legacy.V135_PLAYER_Y)
    pz = float(legacy.V135_PLAYER_Z)
    best = None
    for placement in placements:
        distance2 = (
            (placement.x - px) ** 2
            + (placement.y - py) ** 2
            + (placement.z - pz) ** 2
        )
        if not math.isfinite(distance2):
            raise NpcHpLinkValidationError("target_placement_not_finite")
        key = (distance2, placement.placement_index)
        if best is None or key < best[0]:
            best = (key, placement)
    if best is None:
        raise NpcHpLinkValidationError("target_placement_source_is_empty")
    placement = best[1]
    if not placement.visual_preset:
        # The visual preset is what eventually sets [actor+0x70] |= 0x40, and
        # 0x47289E gates the death animation on that bit.  An actor whose model
        # never resolves would latch, build the task and still never animate.
        raise NpcHpLinkValidationError("target_has_no_visual_preset")
    if (
        placement.placement_index != NPC_HP_LINK_TARGET_PLACEMENT_INDEX
        or placement.template_id != NPC_HP_LINK_TARGET_TEMPLATE_ID
        or placement.actor_identity != NPC_HP_LINK_TARGET_IDENTITY_LO
        or placement.visual_preset != NPC_HP_LINK_TARGET_VISUAL_PRESET
        or placement.source_name != NPC_HP_LINK_TARGET_SOURCE_NAME
    ):
        raise NpcHpLinkValidationError("target_placement_drifted_from_the_pin")
    return NpcHpLinkTarget(
        placement.placement_index, placement.template_id,
        placement.actor_identity, placement.x, placement.y, placement.z,
        placement.visual_preset, placement.source_name,
        SCENE_ID, SCENE_SEQUENCE,
    )


def npc_hp_link_target_identity() -> int:
    """The 64-bit identity every frame of this sweep is about."""
    return (
        ((NPC_HP_LINK_TARGET_IDENTITY_HI & 0xFFFFFFFF) << 32)
        | (NPC_HP_LINK_TARGET_IDENTITY_LO & 0xFFFFFFFF)
    )


# ===========================================================================
# THE BALANCE.  Our numbers, our clamp, our ladder -- and this is the first
# ladder in this tree that belongs to a TARGET rather than to the player.
# ===========================================================================
NPC_HP_LINK_HP_START = 100
NPC_HP_LINK_HP_MAX = 100
NPC_HP_LINK_HP_FLOOR = 0

# 6.0 s, NOT 15.0 s: Panya ruled on 2026-08-20 that stretching frame spacing
# for the human tester is wasted effort because the event itself is short, and
# that the correct fix is recording video.  This is the death lane's spacing.
NPC_HP_LINK_SPACING_SECONDS = 6.0
NPC_HP_LINK_FIRST_DELAY_SECONDS = 0.0
NPC_HP_LINK_SPACING_DECISION = (
    "six_seconds_not_fifteen_stretching_spacing_for_the_tester_is_wasted_"
    "effort_because_the_event_is_short_the_fix_is_recording_video_panya_"
    "20260820"
)
NPC_HP_LINK_ACTION_LABEL_PREFIX = "HYP_PF_029_NPC_HP_LINK_"

NPC_HP_LINK_STEP_KIND_ACTOR = "actor"
NPC_HP_LINK_STEP_KIND_HIT = "hit"

# The server-held TARGET balance AFTER each step.  A hit frame only ANNOUNCES
# its number; the actor-entry frame that follows it APPLIES the number, which
# is why the ladder holds still on every hit index.  Declared here and
# re-derived by replay_npc_hp_link_balance_ladder on every composition -- any
# disagreement is hp_arithmetic_not_reproducible and no byte leaves.
NPC_HP_LINK_BALANCE_LADDER = (100, 100, 37, 37, 37, 37, 0, 0)

# (label, kind, spec, flags)
#   actor step -> spec is (hp_current, death_timer_or_None, with_movement)
#   hit step   -> spec is the named attacker, or None for the miss control
NPC_HP_LINK_STEPS = (
    ("TARGET_SPAWN", NPC_HP_LINK_STEP_KIND_ACTOR,
     (NPC_HP_LINK_BALANCE_LADDER[0], None, True), None),
    ("HIT_WEAK", NPC_HP_LINK_STEP_KIND_HIT, "MOB_WEAK", FLAGS_HIT),
    ("TARGET_HP_AFTER_WEAK", NPC_HP_LINK_STEP_KIND_ACTOR,
     (NPC_HP_LINK_BALANCE_LADDER[2], None, False), None),
    ("MISS", NPC_HP_LINK_STEP_KIND_HIT, None, FLAGS_MISS),
    ("TARGET_HP_AFTER_MISS", NPC_HP_LINK_STEP_KIND_ACTOR,
     (NPC_HP_LINK_BALANCE_LADDER[4], None, False), None),
    ("HIT_STRONG", NPC_HP_LINK_STEP_KIND_HIT, "MOB_STRONG", FLAGS_HIT),
    ("TARGET_HP_ZERO_DYING", NPC_HP_LINK_STEP_KIND_ACTOR,
     (NPC_HP_LINK_HP_FLOOR, DYING_LATCH_TIMER_SECONDS, False), None),
    ("TARGET_DYING_ELAPSED", NPC_HP_LINK_STEP_KIND_ACTOR,
     (NPC_HP_LINK_HP_FLOOR, DEATH_TASK_TIMER_SECONDS, False), None),
)
NPC_HP_LINK_STEP_ORDER = tuple(row[0] for row in NPC_HP_LINK_STEPS)
NPC_HP_LINK_ACTION_LABELS = tuple(
    NPC_HP_LINK_ACTION_LABEL_PREFIX + label
    for label in NPC_HP_LINK_STEP_ORDER
)
NPC_HP_LINK_SPAWN_STEP_LABEL = "TARGET_SPAWN"
NPC_HP_LINK_MISS_STEP_LABELS = ("MISS",)
# The only two steps allowed to compose a lethal field, and the only step
# allowed to clamp the balance.
NPC_HP_LINK_LETHAL_STEP_LABELS = (
    "TARGET_HP_ZERO_DYING", "TARGET_DYING_ELAPSED",
)
NPC_HP_LINK_CLAMP_STEP_LABEL = "TARGET_HP_ZERO_DYING"
NPC_HP_LINK_TIMER_BY_STEP = {
    "TARGET_HP_ZERO_DYING": DYING_LATCH_TIMER_SECONDS,
    "TARGET_DYING_ELAPSED": DEATH_TASK_TIMER_SECONDS,
}


def step_plan(index: Any) -> tuple[str, str, Any, Any]:
    if type(index) is not int or type(index) is bool:
        raise NpcHpLinkValidationError("unknown_step_label")
    if not 0 <= index < len(NPC_HP_LINK_STEPS):
        raise NpcHpLinkValidationError("unknown_step_label")
    return NPC_HP_LINK_STEPS[index]


def step_damage_wire(index: Any) -> int:
    """The number OUR formula produces for one hit step of the plan."""
    _label, kind, spec, _flags = step_plan(index)
    if kind != NPC_HP_LINK_STEP_KIND_HIT:
        raise NpcHpLinkValidationError("unknown_step_label")
    if spec is None:
        return 0
    return compute_npc_hp_link_damage_wire(spec)


# ===========================================================================
# THE ARITHMETIC ENGINE.
# ===========================================================================
def apply_hit_to_balance(balance: Any, damage_wire: Any, flags: Any) -> int:
    """Move the server-held TARGET balance by one announced hit, or refuse.

    The clamp at the floor is performed here; WHERE clamping is allowed to
    happen is not this function's decision -- replay_npc_hp_link_balance_ladder
    records every clamp and refuses one outside the pinned step.
    """
    if type(balance) is not int or type(balance) is bool:
        raise NpcHpLinkValidationError("hp_balance_not_integer")
    if not NPC_HP_LINK_HP_FLOOR <= balance <= NPC_HP_LINK_HP_MAX:
        raise NpcHpLinkValidationError("hp_balance_outside_the_declared_band")
    require_npc_hp_link_damage_wire_value(damage_wire)
    require_npc_hp_link_flags_value(flags)
    require_npc_hp_link_damage_and_flags_agree(damage_wire, flags)
    moved = balance + damage_wire
    if moved < NPC_HP_LINK_HP_FLOOR:
        moved = NPC_HP_LINK_HP_FLOOR
    return moved


def replay_npc_hp_link_balance_ladder() -> tuple[int, ...]:
    """Walk the whole plan through the engine and return the derived ladder.

    A clamp anywhere but the pinned clamp step is refused, and the pinned clamp
    step must actually clamp -- a plan whose strong hit stopped clamping would
    otherwise drift in silence.
    """
    balance = NPC_HP_LINK_HP_START
    pending: Any = None
    ladder: list[int] = []
    for label, kind, spec, flags in NPC_HP_LINK_STEPS:
        if kind == NPC_HP_LINK_STEP_KIND_HIT:
            if pending is not None:
                raise NpcHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: two hit frames in a "
                    "row leave a number nothing applied"
                )
            damage = (
                0 if spec is None else compute_npc_hp_link_damage_wire(spec)
            )
            pending = (damage, flags)
        else:
            if pending is not None:
                damage, hit_flags = pending
                moved = apply_hit_to_balance(balance, damage, hit_flags)
                clamped = balance + damage < NPC_HP_LINK_HP_FLOOR
                if clamped and label != NPC_HP_LINK_CLAMP_STEP_LABEL:
                    raise NpcHpLinkValidationError(
                        "hp_clamp_outside_the_pinned_step")
                if not clamped and label == NPC_HP_LINK_CLAMP_STEP_LABEL:
                    raise NpcHpLinkValidationError(
                        "hp_clamp_outside_the_pinned_step: the pinned clamp "
                        "step did not clamp"
                    )
                balance = moved
                pending = None
        ladder.append(balance)
    return tuple(ladder)


def require_npc_hp_link_balance_ladder() -> tuple[int, ...]:
    """The declared ladder, or a refusal if the engine cannot reproduce it."""
    derived = replay_npc_hp_link_balance_ladder()
    if derived != NPC_HP_LINK_BALANCE_LADDER:
        raise NpcHpLinkValidationError("hp_arithmetic_not_reproducible")
    return derived


def _require_step_plan() -> None:
    """Shape checks on the pinned plan itself, run before any composition."""
    if len(set(NPC_HP_LINK_STEP_ORDER)) != len(NPC_HP_LINK_STEP_ORDER):
        raise NpcHpLinkValidationError("unknown_step_label")
    if len(NPC_HP_LINK_STEPS) != len(NPC_HP_LINK_BALANCE_LADDER):
        raise NpcHpLinkValidationError("hp_arithmetic_not_reproducible")
    first_label, first_kind, first_spec, _flags = NPC_HP_LINK_STEPS[0]
    if first_label != NPC_HP_LINK_SPAWN_STEP_LABEL or (
        first_kind != NPC_HP_LINK_STEP_KIND_ACTOR
    ):
        raise NpcHpLinkValidationError("unknown_step_label")
    # An actor cannot be born dead: an identity the client does not know takes
    # the spawn branch 0x446990 -> vtable +0x10, which never reaches the dead
    # state sync.  The first frame must therefore be a live, placed spawn.
    if first_spec != (NPC_HP_LINK_HP_START, None, True):
        raise NpcHpLinkValidationError(
            "lethal_field_outside_the_pinned_step: the spawn must be alive, "
            "placed and carry no death timer"
        )
    last_label, last_kind, _spec, _flags = NPC_HP_LINK_STEPS[-1]
    if last_label != "TARGET_DYING_ELAPSED" or (
        last_kind != NPC_HP_LINK_STEP_KIND_ACTOR
    ):
        raise NpcHpLinkValidationError("unknown_step_label")
    miss_labels = []
    for index, (label, kind, spec, flags) in enumerate(NPC_HP_LINK_STEPS):
        if kind == NPC_HP_LINK_STEP_KIND_HIT:
            follower = NPC_HP_LINK_STEPS[index + 1]
            if follower[1] != NPC_HP_LINK_STEP_KIND_ACTOR:
                raise NpcHpLinkValidationError(
                    "hp_clamp_outside_the_pinned_step: every hit frame must "
                    "be followed by the actor frame that applies it"
                )
            if spec is None:
                if flags != FLAGS_MISS:
                    raise NpcHpLinkValidationError(
                        "damage_zero_with_apply_flag")
                miss_labels.append(label)
            elif flags != FLAGS_HIT:
                raise NpcHpLinkValidationError(
                    "damage_nonzero_without_apply_flag")
        elif kind != NPC_HP_LINK_STEP_KIND_ACTOR:
            raise NpcHpLinkValidationError("unknown_step_label")
    if tuple(miss_labels) != NPC_HP_LINK_MISS_STEP_LABELS:
        raise NpcHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    ladder = require_npc_hp_link_balance_ladder()
    # The declared hp values must BE the derived balances, so the plan cannot
    # write a bar the arithmetic did not produce.
    for index, (label, kind, spec, _flags) in enumerate(NPC_HP_LINK_STEPS):
        if kind != NPC_HP_LINK_STEP_KIND_ACTOR:
            continue
        if spec[0] != ladder[index]:
            raise NpcHpLinkValidationError("hp_arithmetic_not_reproducible")
        timer = spec[1]
        lethal = label in NPC_HP_LINK_LETHAL_STEP_LABELS
        if (timer is not None) != lethal:
            raise NpcHpLinkValidationError(
                "lethal_field_outside_the_pinned_step")
        if lethal and spec[0] != NPC_HP_LINK_HP_FLOOR:
            raise NpcHpLinkValidationError(
                "lethal_field_outside_the_pinned_step: a lethal step must "
                "hold the balance at the floor"
            )
        if not lethal and spec[0] == NPC_HP_LINK_HP_FLOOR:
            raise NpcHpLinkValidationError(
                "lethal_field_outside_the_pinned_step")
    if NPC_HP_LINK_CLAMP_STEP_LABEL not in NPC_HP_LINK_LETHAL_STEP_LABELS:
        raise NpcHpLinkValidationError("hp_clamp_outside_the_pinned_step")
    if set(NPC_HP_LINK_TIMER_BY_STEP) != set(NPC_HP_LINK_LETHAL_STEP_LABELS):
        raise NpcHpLinkValidationError("lethal_field_outside_the_pinned_step")


# ===========================================================================
# THE UNLOCK.  One token, minted only from the allowlisted scenario object,
# compared by IDENTITY everywhere.
# ===========================================================================
@dataclass(frozen=True)
class NpcHpLinkWireUnlock:
    scenario_id: str
    hypothesis_id: str


_UNLOCK = NpcHpLinkWireUnlock(
    NPC_HP_LINK_SCENARIO_ID, NPC_HP_LINK_HYPOTHESIS_ID,
)


@dataclass(frozen=True)
class NpcHpLinkHypothesisScenario:
    scenario_id: str
    hypothesis_id: str
    step_order: tuple[str, ...]
    spacing_seconds: float
    first_delay_seconds: float
    action_label_prefix: str


_PROFILE = NpcHpLinkHypothesisScenario(
    NPC_HP_LINK_SCENARIO_ID,
    NPC_HP_LINK_HYPOTHESIS_ID,
    NPC_HP_LINK_STEP_ORDER,
    NPC_HP_LINK_SPACING_SECONDS,
    NPC_HP_LINK_FIRST_DELAY_SECONDS,
    NPC_HP_LINK_ACTION_LABEL_PREFIX,
)


def npc_hp_link_wire_unlock(scenario: Any) -> NpcHpLinkWireUnlock:
    """The ONLY minter.  Requires the allowlisted scenario object ITSELF.

    Identity, not equality: a scenario assembled elsewhere that happens to
    compare equal is still not the one this module ships, and it mints nothing.
    """
    require_npc_hp_link_hypothesis_scenario(scenario)
    if scenario is not _PROFILE:
        raise NpcHpLinkValidationError("scenario_object_exceeds_allowlist")
    return _UNLOCK


def require_npc_hp_link_wire_unlock(value: Any) -> NpcHpLinkWireUnlock:
    # Identity, not equality: a forged token that compares equal must not open
    # the lane.
    if value is not _UNLOCK:
        raise NpcHpLinkValidationError(
            "missing_or_forged_wire_unlock: HYP-PF-029 refuses to emit a byte "
            "without the unlock derived from the opt-in scenario"
        )
    return value


def require_npc_hp_link_hypothesis_scenario(
    value: Any,
) -> NpcHpLinkHypothesisScenario:
    if type(value) is not NpcHpLinkHypothesisScenario or value != _PROFILE:
        raise NpcHpLinkValidationError("scenario_object_exceeds_allowlist")
    _require_step_plan()
    return value


# ===========================================================================
# THE ENCODERS.
# ===========================================================================
def _require_identity_pair(identity_lo: Any, identity_hi: Any) -> int:
    for value in (identity_lo, identity_hi):
        if type(value) is not int or type(value) is bool:
            raise NpcHpLinkValidationError("target_identity_outside_qword")
        if not 0 <= value <= 0xFFFFFFFF:
            raise NpcHpLinkValidationError("target_identity_outside_qword")
    return ((identity_hi & 0xFFFFFFFF) << 32) | (identity_lo & 0xFFFFFFFF)


def _require_pinned_position(legacy: Any) -> tuple[float, float, float]:
    """The frozen V135 player spawn -- the same pinned source the proven
    damage-model npc_sweep reads.  Nothing here invents a coordinate."""
    position = (
        float(legacy.V135_PLAYER_X),
        float(legacy.V135_PLAYER_Y),
        float(legacy.V135_PLAYER_Z),
    )
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise NpcHpLinkValidationError(
                "position_not_from_the_pinned_source")
    return position


def _require_pinned_yaw(value: Any) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise NpcHpLinkValidationError("yaw_outside_pinned_value")
    if value != YAW_PINNED:
        raise NpcHpLinkValidationError("yaw_outside_pinned_value")
    return value


def encode_npc_hp_link_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    yaw: float,
    flags: int,
    unlock: Any,
) -> bytes:
    """One 37-byte hit entry, in the proven emission order."""
    require_npc_hp_link_wire_unlock(unlock)
    if type(target_identity) is not int or type(target_identity) is bool:
        raise NpcHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= target_identity <= 0xFFFFFFFFFFFFFFFF:
        raise NpcHpLinkValidationError("target_identity_outside_qword")
    if target_identity != npc_hp_link_target_identity():
        raise NpcHpLinkValidationError("npc_target_identity_not_pinned")
    require_npc_hp_link_damage_wire_value(damage_wire)
    require_npc_hp_link_flags_value(flags)
    require_npc_hp_link_damage_and_flags_agree(damage_wire, flags)
    yaw = _require_pinned_yaw(yaw)
    if type(position) is not tuple or len(position) != 3:
        raise NpcHpLinkValidationError("position_not_from_the_pinned_source")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target_identity)
    out += legacy.u32tag(TAG_U32, damage_wire & 0xFFFFFFFF)
    for component in position:
        if type(component) is not float or not math.isfinite(component):
            raise NpcHpLinkValidationError(
                "position_not_from_the_pinned_source")
        out += legacy.f32tag(component)
    out += legacy.f32tag(yaw)
    out += legacy.u16tag(TAG_U16, flags)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: hit entry is %d bytes"
            % len(out)
        )
    return bytes(out)


def encode_npc_hp_link_chit_result(
    legacy: Any,
    performer_identity: int,
    entries: list[bytes],
    unlock: Any,
) -> bytes:
    """The CHitResult payload: the 22-byte header, then the entry array."""
    require_npc_hp_link_wire_unlock(unlock)
    if type(performer_identity) is not int or type(performer_identity) is bool:
        raise NpcHpLinkValidationError("target_identity_outside_qword")
    if not 0 <= performer_identity <= 0xFFFFFFFFFFFFFFFF:
        raise NpcHpLinkValidationError("target_identity_outside_qword")
    if performer_identity == npc_hp_link_target_identity():
        raise NpcHpLinkValidationError(
            "npc_performer_must_not_be_the_npc_target")
    if type(entries) is not list or len(entries) != HIT_ENTRY_COUNT_PINNED:
        raise NpcHpLinkValidationError("entry_count_not_pinned")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer_identity)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: header is %d bytes"
            % len(header)
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise NpcHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: entry width")
        out += entry
    if len(out) != CHIT_RESULT_PAYLOAD_WIRE_SIZE:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: payload is %d bytes"
            % len(out)
        )
    return bytes(out)


def _require_death_timer(value: Any, step_label: str) -> float:
    """The one f32 this lane may put at BasicAttr +0x58, per pinned step.

    The discipline is copied from the proven lethal lanes: a real float only,
    finite, exactly representable in 32 bits; the dying step must be strictly
    positive so vt+0x40 latches; the elapsed step must pack to the pinned five
    bytes (negative zero packs differently and is refused).
    """
    expected = NPC_HP_LINK_TIMER_BY_STEP.get(step_label)
    if expected is None:
        raise NpcHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if type(value) is not float:
        raise NpcHpLinkValidationError("death_timer_not_float")
    if value != value or value in (float("inf"), float("-inf")):
        raise NpcHpLinkValidationError("death_timer_not_finite")
    if value != expected:
        raise NpcHpLinkValidationError("death_timer_outside_the_pinned_plan")
    packed = struct.pack("<f", value)
    if struct.unpack("<f", packed)[0] != value:
        raise NpcHpLinkValidationError(
            "death_timer_not_exactly_representable")
    if value <= 0.0 and bytes([DEATH_TIMER_TAG]) + packed != (
        NPC_HP_LINK_TIMER_ELAPSED_WIRE_BYTES
    ):
        raise NpcHpLinkValidationError(
            "death_timer_elapsed_is_not_the_pinned_zero")
    return value


def encode_npc_hp_link_npc_attr(
    legacy: Any,
    target: NpcHpLinkTarget,
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
    require_npc_hp_link_wire_unlock(unlock)
    if type(target) is not NpcHpLinkTarget:
        raise NpcHpLinkValidationError("target_placement_drifted_from_the_pin")
    if type(step_label) is not str or step_label not in NPC_HP_LINK_STEP_ORDER:
        raise NpcHpLinkValidationError("unknown_step_label")
    if type(current_hp) is not int or type(current_hp) is bool:
        raise NpcHpLinkValidationError("hp_field_value_not_integer")
    if not 0 <= current_hp <= NPC_HP_LINK_HP_MAX:
        raise NpcHpLinkValidationError("hp_field_value_outside_width")
    lethal = step_label in NPC_HP_LINK_LETHAL_STEP_LABELS
    if (death_timer is not None) != lethal:
        raise NpcHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if current_hp == NPC_HP_LINK_HP_FLOOR and not lethal:
        raise NpcHpLinkValidationError("lethal_field_outside_the_pinned_step")
    if lethal and current_hp != NPC_HP_LINK_HP_FLOOR:
        raise NpcHpLinkValidationError(
            "lethal_field_outside_the_pinned_step: a lethal step must hold "
            "the balance at the floor"
        )
    baseline = legacy.make_npc_attr(
        target.template_id, target.actor_identity,
        target.scene_id, target.scene_sequence, target.visual_preset,
        current_hp, NPC_HP_LINK_HP_MAX,
    )
    if death_timer is None:
        composed = _compose_npc_attr(legacy, target, current_hp, None)
        if composed != baseline:
            raise NpcHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: the timerless body no "
                "longer reproduces legacy.make_npc_attr byte for byte"
            )
        return composed
    timer = _require_death_timer(death_timer, step_label)
    composed = _compose_npc_attr(legacy, target, current_hp, timer)
    # The lethal body must be the timerless body plus EXACTLY the five bytes of
    # the tag-0x2A f32.  Any other delta means the field landed in the wrong
    # place.
    if len(composed) != len(baseline) + 1 + DEATH_TIMER_WIDTH:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: lethal NPCAttr length")
    return composed


def _compose_npc_attr(
    legacy: Any,
    target: NpcHpLinkTarget,
    current_hp: int,
    death_timer: float | None,
) -> bytes:
    basic_mask = (
        BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
        | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ
    )
    if death_timer is not None:
        basic_mask |= BASIC_BIT_DEATH_TIMER
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if target.visual_preset else 0
    )
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, target.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
    # Ascending mask-bit order inside the block, which is the order BasicAttr's
    # serializer 0x4656F0 writes and its reader expects.
    out += legacy.u32tag(CURRENT_HP_TAG, current_hp)                # 0x0004
    out += legacy.u32tag(CURRENT_HP_TAG, NPC_HP_LINK_HP_MAX)        # 0x0008
    if death_timer is not None:
        out += legacy.f32tag(death_timer)                           # 0x0080
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, target.scene_id)      # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, target.scene_sequence)     # 0x0200
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, target.template_id)
    if target.visual_preset:
        out += legacy.wstr_tag(target.visual_preset)
    return bytes(out)


def make_npc_hp_link_step_response(
    legacy: Any,
    target: NpcHpLinkTarget,
    performer_identity_lo: int,
    performer_identity_hi: int,
    step_index: int,
    unlock: Any,
) -> tuple[bytes, bytes]:
    """Compose one step of the target sweep, either carrier."""
    require_npc_hp_link_wire_unlock(unlock)
    _require_step_plan()
    performer = _require_identity_pair(
        performer_identity_lo, performer_identity_hi)
    label, kind, spec, flags = step_plan(step_index)
    if kind == NPC_HP_LINK_STEP_KIND_HIT:
        # The performer stays the PLAYER and the target is the NPC: one side
        # must be the player or the visibility filter at 0x43FEF0 draws
        # nothing, and the whole point of this lane is that the two differ.
        entry = encode_npc_hp_link_hit_entry(
            legacy, npc_hp_link_target_identity(), step_damage_wire(step_index),
            _require_pinned_position(legacy), YAW_PINNED, flags, unlock,
        )
        payload = encode_npc_hp_link_chit_result(
            legacy, performer, [entry], unlock)
        pc, frame = legacy.make_runtime_vitals(
            [(CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION, payload)]
        )
    else:
        current_hp, death_timer, with_movement = spec
        body = encode_npc_hp_link_npc_attr(
            legacy, target, label, current_hp, death_timer, unlock)
        attrs = [(NPC_ATTR_ID, body)]
        if with_movement:
            attrs.append((
                MOVEMENT_ATTR_ID,
                legacy.make_remote_movement_attr(
                    target.actor_identity, target.x, target.y, target.z, 0.0,
                    mask=FULL_MOVEMENT_MASK,
                ),
            ))
        entry = legacy.make_remote_actor_entry(
            NPC_STYLE_ACTOR_TYPE, target.actor_identity, attrs,
        )
        pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: HYP-PF-029 frame drift")
    _require_probe_pins(
        label, pc, frame, performer_identity_lo, performer_identity_hi)
    return pc, frame


def _require_probe_pins(
    label: str, pc: bytes, frame: bytes, identity_lo: int, identity_hi: int,
) -> None:
    """Sizes for ANY performer; exact bytes for the pinned probe performer.

    The actor-entry frames do not mention the performer at all, so their bytes
    are pinned for EVERY session -- that is a property of this lane worth
    stating: only the three hit frames vary with who is swinging.
    """
    if not NPC_HP_LINK_PINS:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: NPC_HP_LINK_PINS is empty, "
            "so there is nothing to hold the encoder to -- this lane refuses "
            "rather than composing unpinned bytes")
    pin = NPC_HP_LINK_PINS[label]
    if len(pc) != pin["pc_size"] or len(frame) != pin["frame_size"]:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: %s size %d/%d != %d/%d"
            % (label, len(pc), len(frame), pin["pc_size"], pin["frame_size"])
        )
    _label, kind, _spec, _flags = NPC_HP_LINK_STEPS[
        NPC_HP_LINK_STEP_ORDER.index(label)
    ]
    if kind == NPC_HP_LINK_STEP_KIND_HIT and (identity_lo, identity_hi) != (
        NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
        NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
    ):
        return
    for value, key in (
        (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
        (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
    ):
        if value != pin[key]:
            raise NpcHpLinkValidationError(
                "composed_bytes_do_not_match_the_pin: probe %s %s %r != %r"
                % (label, key, value, pin[key])
            )


def build_npc_hp_link_sweep(
    legacy: Any,
    target: NpcHpLinkTarget,
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
    scenario = require_npc_hp_link_hypothesis_scenario(scenario)
    require_npc_hp_link_wire_unlock(unlock)
    actions: list[tuple[str, bytes, bytes, float]] = []
    for index, label in enumerate(scenario.step_order):
        pc, frame = make_npc_hp_link_step_response(
            legacy, target, performer_identity_lo, performer_identity_hi,
            index, unlock,
        )
        delay = (
            scenario.first_delay_seconds if index == 0
            else scenario.spacing_seconds
        )
        actions.append((scenario.action_label_prefix + label, pc, frame, delay))
    validate_npc_hp_link_sweep(actions)
    _require_pinned_probe_composition(legacy, target, unlock)
    return actions


def _require_pinned_probe_composition(
    legacy: Any, target: NpcHpLinkTarget, unlock: Any,
) -> None:
    """Hold the ENCODER to the pinned bytes on every build.

    A live sweep for a session performer cannot be hashed to a constant, so the
    probe performer is re-composed here on every build and compared to the pins
    -- a drifted encoder therefore cannot ship even once.
    """
    if not NPC_HP_LINK_PINS:
        raise NpcHpLinkValidationError(
            "composed_bytes_do_not_match_the_pin: NPC_HP_LINK_PINS is empty, "
            "so the probe recomposition has no oracle -- this lane refuses "
            "rather than shipping a sweep nothing held to the pins")
    for index, label in enumerate(NPC_HP_LINK_STEP_ORDER):
        pc, frame = make_npc_hp_link_step_response(
            legacy, target,
            NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO,
            NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI,
            index, unlock,
        )
        pin = NPC_HP_LINK_PINS[label]
        for value, key in (
            (hashlib.sha256(pc).hexdigest().upper(), "pc_sha256"),
            (hashlib.sha256(frame).hexdigest().upper(), "frame_sha256"),
        ):
            if value != pin[key]:
                raise NpcHpLinkValidationError(
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
        raise NpcHpLinkValidationError(f"{label}: truncated")
    if pc[cursor] != tag:
        raise NpcHpLinkValidationError(
            "%s: tag 0x%02X != 0x%02X" % (label, pc[cursor], tag))
    return pc[cursor + 1:cursor + 1 + width], cursor + 1 + width


def decode_npc_hp_link_transport(frame: bytes) -> bytes:
    """Read the outer transport frame back to its PC, byte for byte.

    The frozen framer is u32 magic + u32 body length + ONE raw literal stream,
    so this walker accepts only literal elements and must land exactly on the
    declared uncompressed length.
    """
    if type(frame) is not bytes or len(frame) < 8:
        raise NpcHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: short header")
    magic, body_len = struct.unpack_from("<II", frame, 0)
    if magic != NPC_HP_LINK_FRAME_MAGIC:
        raise NpcHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: magic")
    if body_len != len(frame) - 8:
        raise NpcHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length")
    body = frame[8:]
    total = 0
    shift = 0
    cursor = 0
    while True:
        if cursor >= len(body):
            raise NpcHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
        byte = body[cursor]
        cursor += 1
        total |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 28:
            raise NpcHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: varint")
    out = bytearray()
    while cursor < len(body):
        tag = body[cursor]
        cursor += 1
        if tag & 0x03:
            raise NpcHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: non-literal")
        code = tag >> 2
        if code <= 59:
            count = code + 1
        else:
            extra = code - 59
            if cursor + extra > len(body):
                raise NpcHpLinkValidationError(
                    "transport_frame_does_not_reproduce_the_pc: truncated")
            count = int.from_bytes(body[cursor:cursor + extra], "little") + 1
            cursor += extra
        if cursor + count > len(body):
            raise NpcHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc: truncated")
        out += body[cursor:cursor + count]
        cursor += count
    if len(out) != total:
        raise NpcHpLinkValidationError(
            "transport_frame_does_not_reproduce_the_pc: length mismatch")
    return bytes(out)


def _walk_npc_attr(pc: bytes, cursor: int) -> tuple[dict[str, Any], int]:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG:
        raise NpcHpLinkValidationError("DBAttribute mask tag drift")
    if pc[cursor + 1] != DB_ATTRIBUTE_IDENTITY_MASK:
        raise NpcHpLinkValidationError(
            "DBAttribute mask is not the identity-only 0x01")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise NpcHpLinkValidationError("NPCAttr identity tag drift")
    attr_identity = int.from_bytes(pc[cursor + 1:cursor + 9], "little")
    cursor += 9
    if pc[cursor] != BASIC_ATTR_MASK_TAG:
        raise NpcHpLinkValidationError("BasicAttr mask tag drift")
    basic_mask = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
    cursor += 3
    fields: dict[int, Any] = {}
    for bit, tag in _BASIC_FIELD_ORDER:
        if not basic_mask & bit:
            continue
        if pc[cursor] != tag:
            raise NpcHpLinkValidationError(
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
        raise NpcHpLinkValidationError(
            "BasicAttr mask 0x%04X carries a bit this walker cannot read"
            % basic_mask
        )
    if pc[cursor] != NPC_ATTR_MASK_TAG:
        raise NpcHpLinkValidationError("NPCAttr mask tag drift")
    npc_mask = pc[cursor + 1]
    cursor += 2
    template_id = None
    visual_preset = None
    if npc_mask & NPC_BIT_TEMPLATE:
        if pc[cursor] != TAG_U16:
            raise NpcHpLinkValidationError("NPCAttr template tag drift")
        template_id = int.from_bytes(pc[cursor + 1:cursor + 3], "little")
        cursor += 3
    if npc_mask & NPC_BIT_VISUAL_PRESET:
        if pc[cursor] != TAG_WSTRING:
            raise NpcHpLinkValidationError("NPCAttr preset tag drift")
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


def _skip_movement_attr(pc: bytes, cursor: int) -> int:
    if pc[cursor] != DB_ATTRIBUTE_MASK_TAG or pc[cursor + 1] != 0x01:
        raise NpcHpLinkValidationError("MovementAttr DBAttribute drift")
    cursor += 2
    if pc[cursor] != IDENTITY_TAG:
        raise NpcHpLinkValidationError("MovementAttr identity tag drift")
    cursor += 9
    if pc[cursor] != TAG_U8:
        raise NpcHpLinkValidationError("MovementAttr mask tag drift")
    mask = pc[cursor + 1]
    cursor += 2
    for bit, _width in _MOVEMENT_FIELD_WIDTH:
        if mask & bit:
            cursor += 15 if bit == 0x01 else (2 if bit == 0x04 else 5)
    return cursor


def decode_npc_hp_link_frame(pc: bytes) -> dict[str, Any]:
    """Read one composed PC back, whichever of the two carriers it holds."""
    if type(pc) is not bytes:
        raise NpcHpLinkValidationError("pc is not bytes")
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
        result["kind"] = NPC_HP_LINK_STEP_KIND_HIT
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital count")
        if struct.unpack("<H", raw)[0] != 1:
            raise NpcHpLinkValidationError("entry_count_not_pinned")
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "vital id")
        vital_id = struct.unpack("<H", raw)[0]
        if vital_id != CHIT_RESULT_VITAL_ID:
            raise NpcHpLinkValidationError(
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
            raise NpcHpLinkValidationError("entry_count_not_pinned")
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
        result["kind"] = NPC_HP_LINK_STEP_KIND_ACTOR
        raw, cursor = _scalar(pc, cursor, TAG_U8, 1, "derived change mask")
        derived = raw[0]
        result["derived_change_mask"] = derived
        if not derived & ACTOR_DERIVED_CHANGE_MASK:
            raise NpcHpLinkValidationError(
                "the derived change mask is missing bit 0x02, so the client "
                "never reads the +0x1C actor-entry collection and 0x446F30 is "
                "never reached (this is the ErrorData=28317 over-read shape)"
            )
        raw, cursor = _scalar(pc, cursor, TAG_U16, 2, "actor entry count")
        if struct.unpack("<H", raw)[0] != 1:
            raise NpcHpLinkValidationError("entry_count_not_pinned")
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
                cursor = _skip_movement_attr(pc, cursor)
                attrs[attr_id] = {"present": True}
            else:
                raise NpcHpLinkValidationError(
                    "unexpected attr id 0x%04X on the actor-entry path"
                    % attr_id
                )
        result["attrs"] = attrs
    else:
        raise NpcHpLinkValidationError(
            "the decoder refuses a change mask outside the two pinned carriers"
        )
    if cursor != len(pc):
        raise NpcHpLinkValidationError(
            "trailing bytes the walker could not account for")
    return result


def validate_npc_hp_link_sweep(
    actions: list[tuple[str, bytes, bytes, float]],
) -> list[dict[str, Any]]:
    """Re-read every composed frame and refuse anything the plan disallows.

    Runs entirely on the bytes: the transport frame is unwrapped by the
    independent walker and must reproduce the PC exactly, both carriers are
    re-decoded from byte 0, the target's balance ladder is re-derived and
    compared, and the pinned probe performer is held to the exact hashes.
    """
    _require_step_plan()
    ladder = require_npc_hp_link_balance_ladder()
    if type(actions) is not list or len(actions) != len(NPC_HP_LINK_STEPS):
        raise NpcHpLinkValidationError("sweep length is not the pinned plan")
    rows: list[dict[str, Any]] = []
    performers: set[int] = set()
    targets: set[int] = set()
    seen_miss = False
    latched_dying = False
    reached_le_zero = False
    hit_position_bytes: set[bytes] = set()
    for index, action in enumerate(actions):
        if type(action) is not tuple or len(action) != 4:
            raise NpcHpLinkValidationError("sweep action shape")
        label, pc, frame, delay = action
        step_label, kind, spec, plan_flags = NPC_HP_LINK_STEPS[index]
        if label != NPC_HP_LINK_ACTION_LABEL_PREFIX + step_label:
            raise NpcHpLinkValidationError("unknown_step_label")
        if type(pc) is not bytes or type(frame) is not bytes:
            raise NpcHpLinkValidationError("sweep action payload type")
        expected_delay = (
            NPC_HP_LINK_FIRST_DELAY_SECONDS if index == 0
            else NPC_HP_LINK_SPACING_SECONDS
        )
        if type(delay) is not float or delay != expected_delay:
            raise NpcHpLinkValidationError("sweep delay is not the plan")
        if decode_npc_hp_link_transport(frame) != pc:
            raise NpcHpLinkValidationError(
                "transport_frame_does_not_reproduce_the_pc")
        decoded = decode_npc_hp_link_frame(pc)
        if decoded["envelope_id"] != RUNTIME_PROTOCOL_RES_ID:
            raise NpcHpLinkValidationError("envelope id is not 0x6E9D")
        if decoded["error_data"] != 0:
            raise NpcHpLinkValidationError("envelope error data nonzero")
        if decoded["envelope_version"] != RUNTIME_PROTOCOL_RES_VERSION:
            raise NpcHpLinkValidationError("envelope is not version 4")
        if decoded["kind"] != kind:
            raise NpcHpLinkValidationError(
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
        performer_lo = NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
        performer_hi = NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI
        if kind == NPC_HP_LINK_STEP_KIND_HIT:
            if decoded["base_change_mask"] != HIT_BASE_CHANGE_MASK:
                raise NpcHpLinkValidationError(
                    "base change mask does not select the VitalData collection")
            if decoded["derived_change_mask"] != HIT_DERIVED_CHANGE_MASK:
                raise NpcHpLinkValidationError(
                    "derived change mask must be absent on a hit frame")
            if decoded["vital_version"] != CHIT_RESULT_VITAL_VERSION:
                raise NpcHpLinkValidationError("vital_version_not_pinned")
            for key in ("header_field2", "header_field3",
                        "header_field4", "header_field5"):
                if decoded[key] != HEADER_RESERVED_VALUE:
                    raise NpcHpLinkValidationError(
                        "header_reserved_field_nonzero")
            if decoded["target_identity"] != npc_hp_link_target_identity():
                raise NpcHpLinkValidationError("npc_target_identity_not_pinned")
            if decoded["performer_identity"] == decoded["target_identity"]:
                raise NpcHpLinkValidationError(
                    "npc_performer_must_not_be_the_npc_target")
            require_npc_hp_link_damage_wire_value(decoded["damage_wire"])
            require_npc_hp_link_flags_value(decoded["flags"])
            require_npc_hp_link_damage_and_flags_agree(
                decoded["damage_wire"], decoded["flags"])
            if decoded["damage_wire"] != step_damage_wire(index):
                raise NpcHpLinkValidationError(
                    "formula_output_not_reproducible")
            if decoded["flags"] != plan_flags:
                raise NpcHpLinkValidationError(
                    "flags_outside_value_allowlist")
            if decoded["yaw"] != YAW_PINNED:
                raise NpcHpLinkValidationError("yaw_outside_pinned_value")
            for component in decoded["position"]:
                if not math.isfinite(component):
                    raise NpcHpLinkValidationError(
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
                raise NpcHpLinkValidationError(
                    "the inherited VitalData change mask is not absent")
            if decoded["derived_change_mask"] != ACTOR_DERIVED_CHANGE_MASK:
                raise NpcHpLinkValidationError(
                    "derived change mask must select the actor-entry "
                    "collection on a target frame")
            if decoded["actor_type"] != NPC_STYLE_ACTOR_TYPE:
                raise NpcHpLinkValidationError(
                    "actor_type %d is outside the jump-table case this lane "
                    "pins (CNetNPC == 4)" % decoded["actor_type"])
            npc = decoded["attrs"].get(NPC_ATTR_ID)
            if npc is None:
                raise NpcHpLinkValidationError(
                    "step %d carries no NPCAttr" % index)
            if npc["identity"] != decoded["target_identity"]:
                raise NpcHpLinkValidationError(
                    "the entry identity and the NPCAttr identity differ, so "
                    "0x446170 and the attr apply would target different actors"
                )
            if not npc["visual_preset"]:
                raise NpcHpLinkValidationError(
                    "step %d carries no visual preset, so [actor+0x70] & 0x40 "
                    "never opens and 0x47289E can never play _F_DIE_000"
                    % index)
            hp = npc["fields"].get(BASIC_BIT_CURRENT_HP)
            timer = npc["fields"].get(BASIC_BIT_DEATH_TIMER)
            if hp is None:
                raise NpcHpLinkValidationError(
                    "step %d omits BasicAttr bit 0x0004, so the client's "
                    "HP==0 half of both predicates is never satisfied" % index)
            if npc["fields"].get(BASIC_BIT_MAX_HP) != NPC_HP_LINK_HP_MAX:
                raise NpcHpLinkValidationError(
                    "composed_bytes_do_not_match_the_pin: hp_max")
            if hp != ladder[index]:
                raise NpcHpLinkValidationError(
                    "hp_arithmetic_not_reproducible")
            expected_timer = NPC_HP_LINK_TIMER_BY_STEP.get(step_label)
            if timer != expected_timer:
                raise NpcHpLinkValidationError(
                    "lethal_field_outside_the_pinned_step"
                    if expected_timer is None
                    else "death_timer_outside_the_pinned_plan"
                )
            if index == 0:
                # An actor cannot be born dead.
                if hp == 0 or timer is not None:
                    raise NpcHpLinkValidationError(
                        "the first frame introduces an identity the client "
                        "does not know, which takes the spawn path 0x446990 "
                        "-> vtable +0x10 and never reaches 0x4437C0: an actor "
                        "cannot be born dead"
                    )
                if MOVEMENT_ATTR_ID not in decoded["attrs"]:
                    raise NpcHpLinkValidationError(
                        "the spawn frame must place the actor (MovementAttr)")
            elif MOVEMENT_ATTR_ID in decoded["attrs"]:
                raise NpcHpLinkValidationError(
                    "only the spawn frame may carry a MovementAttr")
            if timer is not None:
                if hp != NPC_HP_LINK_HP_FLOOR:
                    raise NpcHpLinkValidationError(
                        "lethal_field_outside_the_pinned_step: a lethal step "
                        "must hold the balance at the floor")
                if timer > 0.0:
                    latched_dying = True
                if timer <= DEATH_TASK_TIMER_CEILING:
                    reached_le_zero = True
            row["hp_current"] = hp
            row["hp_death_timer"] = timer
            row["basic_mask"] = npc["basic_mask"]
            row["template_id"] = npc["template_id"]
            row["visual_preset"] = npc["visual_preset"]
        _require_probe_pins(step_label, pc, frame, performer_lo, performer_hi)
        rows.append(row)
    if len(performers) != 1:
        raise NpcHpLinkValidationError(
            "performer_identity_not_the_selected_actor")
    # THE LINK, checked from the bytes: every frame of the sweep -- both the
    # hit entries and the actor entries -- must be about the SAME actor, or the
    # bar that moves is not the bar the number was drawn over.
    if targets != {npc_hp_link_target_identity()}:
        raise NpcHpLinkValidationError("npc_target_identity_not_pinned")
    if len(hit_position_bytes) != 1:
        raise NpcHpLinkValidationError("position_not_from_the_pinned_source")
    if not seen_miss:
        raise NpcHpLinkValidationError("sweep_does_not_contain_a_miss_frame")
    if not latched_dying:
        raise NpcHpLinkValidationError(
            "no frame satisfies vt+0x40 (HP==0 AND timer>0), so the dying "
            "latch [actor+0x70] |= 0x200 is never set")
    if not reached_le_zero:
        raise NpcHpLinkValidationError(
            "the death timer never reaches <= 0, so vt+0x3C is never true and "
            "CActorTask_Dead is never constructed")
    if rows[-1].get("hp_death_timer") != DEATH_TASK_TIMER_SECONDS:
        raise NpcHpLinkValidationError(
            "the LAST frame must be the one that satisfies vt+0x3C, or the "
            "sweep re-arms the timer after opening the task gate")
    return rows


# ===========================================================================
# PINS, CAPABILITIES, NONCLAIMS.
# ===========================================================================
# The composed bytes, pinned.  Every value here was produced by this encoder
# and read back by the independent walker; none of it was copied in from
# anywhere.  Two families of pin live in this table and they are not the same
# strength:
#   * the FIVE actor-entry frames mention no performer at all, so their bytes
#     are pinned for EVERY session, not only for the probe;
#   * the THREE hit frames carry the session performer, so their pinned hashes
#     hold for the probe performer 0x10010001 and their SIZES hold for any.
# TARGET_HP_AFTER_WEAK and TARGET_HP_AFTER_MISS are byte-identical on purpose
# -- the miss control moves nothing, and identical bytes are the strongest way
# to say so.  TARGET_SPAWN, TARGET_HP_ZERO_DYING and TARGET_DYING_ELAPSED
# reproduce the RUNTIMERES-DEATH lane's SPAWN / DYING_LATCH / DEATH_TASK probe
# pins byte for byte, and the three hit frames reproduce the DAMAGE-MODEL
# npc_sweep probe pins byte for byte.
NPC_HP_LINK_PINS: dict[str, dict[str, Any]] = {
    "TARGET_SPAWN": {
        "pc_size": 173,
        "pc_sha256": (
            "8965DCF2574B733B119741D2350FB5BAB6D416A9168113AA3E95A5F2FBAC698C"
        ),
        "frame_size": 185,
        "frame_sha256": (
            "E7E2B0C671C1B023F5FD6FAE4D6489CC670F648DBD3802A67B760816A78AB0C4"
        ),
    },
    "HIT_WEAK": {
        "pc_size": 84,
        "pc_sha256": (
            "D07A4F48E56085982E511FF24E4C4C079DF1318E60A7386BF1B93F5D54A8A4C3"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "0B4537B6240F7C202B5FAF1A9BADCB0E0F7BAFC40191724DFDE953F797F89706"
        ),
    },
    "TARGET_HP_AFTER_WEAK": {
        "pc_size": 115,
        "pc_sha256": (
            "D455806EAAB39E46E1E671515286E6D61054CF9B49D2ADA900CE8D62D951F651"
        ),
        "frame_size": 126,
        "frame_sha256": (
            "5DF25D7E42D46875D98F55C439142AA1EE479E3D3D157F28F591B9FB17EE2349"
        ),
    },
    "MISS": {
        "pc_size": 84,
        "pc_sha256": (
            "36702C4201652DBB84C5F712515D28729AC994D07353AAE069D53E454DDD3891"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "E369DDC41CA253CBE3ABD5474760C2F0F4C9D76FD12A7BD1783B1D68D67E7458"
        ),
    },
    "TARGET_HP_AFTER_MISS": {
        "pc_size": 115,
        "pc_sha256": (
            "D455806EAAB39E46E1E671515286E6D61054CF9B49D2ADA900CE8D62D951F651"
        ),
        "frame_size": 126,
        "frame_sha256": (
            "5DF25D7E42D46875D98F55C439142AA1EE479E3D3D157F28F591B9FB17EE2349"
        ),
    },
    "HIT_STRONG": {
        "pc_size": 84,
        "pc_sha256": (
            "237CB09D44742068F8304FF02CFDA4E61E1045719DE00BE06F0B2CBAAA1E41A5"
        ),
        "frame_size": 95,
        "frame_sha256": (
            "3363C2A44878732D97F204987963B277E47DAF4016F6BDA27D0E92E2F0128FA9"
        ),
    },
    "TARGET_HP_ZERO_DYING": {
        "pc_size": 120,
        "pc_sha256": (
            "451D73AD2AB0360D206DDD3A3C4CED9A7A328FFD8455B84C4018A27B635D21EA"
        ),
        "frame_size": 131,
        "frame_sha256": (
            "CDBFED6788E418110C1D8FE177BE9D4275DC7FF376A8E654F3B734C14BCDA2E4"
        ),
    },
    "TARGET_DYING_ELAPSED": {
        "pc_size": 120,
        "pc_sha256": (
            "0116A7300814CA53F38668B2CAA193123324360F172EE2A9F9B5791BDE81BF0C"
        ),
        "frame_size": 131,
        "frame_sha256": (
            "D545EC392D880D96BBC669A1F5646741268E8D0E29FD32B90474FF080160D1A0"
        ),
    },
}

# The parent lanes' own pins, COPIED here so the cross-lane equality claim is
# checkable without importing either parent.  The drift tests in tests/ compare
# these against the parents' live tables in both directions.
NPC_HP_LINK_PARENT_PIN_SOURCES = {
    "TARGET_SPAWN": ("HYP-PF-023", "SPAWN"),
    "TARGET_HP_ZERO_DYING": ("HYP-PF-023", "DYING_LATCH"),
    "TARGET_DYING_ELAPSED": ("HYP-PF-023", "DEATH_TASK"),
    "HIT_WEAK": ("HYP-PF-024", "HIT_WEAK"),
    "MISS": ("HYP-PF-024", "MISS"),
    "HIT_STRONG": ("HYP-PF-024", "HIT_STRONG"),
}


NPC_HP_LINK_CAPABILITIES = (
    "run_our_damage_arithmetic_against_a_server_held_balance_for_a_target",
    "move_a_targets_hit_points_which_no_lane_in_this_tree_has_ever_done",
    "alternate_the_vitaldata_hit_carrier_and_the_actor_entry_target_carrier",
    "address_every_frame_of_the_sweep_at_the_one_frozen_placement_identity",
    "clamp_the_balance_at_the_floor_on_exactly_one_pinned_step",
    "end_in_the_proven_dying_latch_then_the_pinned_death_task_frame",
    "refuse_every_value_whose_client_meaning_this_project_cannot_name",
)

NPC_HP_LINK_NONCLAIMS = (
    "this_is_our_design_not_the_original_servers_which_is_unrecoverable",
    "no_capture_shows_a_targets_hit_points_moving_in_response_to_damage_in_either_direction",
    "the_client_does_not_subtract_damage_that_is_why_the_server_must_say_both_halves",
    "whether_the_client_renders_the_intermediate_value_37_on_the_targets_hp_bar_is_undecidable_from_static_analysis_and_is_the_queued_attended_test",
    "the_only_thing_proven_so_far_is_the_negative_505_damage_and_the_bar_did_not_move",
    "no_claim_the_original_server_ever_linked_these_frames",
    "no_database_write_no_hp_column_exists_and_none_is_added",
    "wire_layer_only_no_client_has_seen_these_bytes",
    "one_shot_per_process",
    "no_claim_about_any_death_window_exit_path",
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
        "id": NPC_HP_LINK_SCENARIO_ID,
        "test_only": True,
        "production_allowed": False,
        "hypothesis_id": NPC_HP_LINK_HYPOTHESIS_ID,
        "checkpoint": NPC_HP_LINK_CHECKPOINT,
        "hypothesis_id_is_registered_in_the_ledger": True,
        "design_not_recovery": (
            "this_is_our_design_not_the_original_servers_which_is_"
            "unrecoverable"
        ),
        "spacing_decision_comment": NPC_HP_LINK_SPACING_DECISION,
        "undecidable_from_static_analysis": (
            "whether_the_client_renders_the_intermediate_value_37_on_the_"
            "targets_hp_bar_is_the_queued_attended_test_the_only_thing_"
            "proven_so_far_is_the_negative_505_damage_and_the_bar_did_not_move"
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
            "wiring_owner": NPC_HP_LINK_WIRING_OWNER,
            "app_policy_when_lane_disabled": (
                "no_frames_composed_and_the_encoder_raises_if_called_directly"
            ),
            "runtime_dispatch_branch": (
                "runtime_py_dispatch_npc_hp_link_hypothesis_reached_from_the_"
                "app_flag_through_make_state_class"
            ),
            "frames_per_accepted_request": len(NPC_HP_LINK_STEP_ORDER),
            "trigger": "one_accepted_34_byte_ascii12_chat_input_frame",
            "step_order": list(NPC_HP_LINK_STEP_ORDER),
            "step_kinds": [row[1] for row in NPC_HP_LINK_STEPS],
            "miss_steps": list(NPC_HP_LINK_MISS_STEP_LABELS),
            "lethal_steps": list(NPC_HP_LINK_LETHAL_STEP_LABELS),
            "spacing_seconds": NPC_HP_LINK_SPACING_SECONDS,
            "first_frame_delay_seconds": NPC_HP_LINK_FIRST_DELAY_SECONDS,
            "delay_semantics": (
                "gap_before_each_send_on_a_cumulative_deadline"
            ),
            "action_label_prefix": NPC_HP_LINK_ACTION_LABEL_PREFIX,
            "action_labels": list(NPC_HP_LINK_ACTION_LABELS),
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
                        NPC_HP_LINK_FLAGS_VALUE_ALLOWLIST),
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
                "polarity": {
                    "dying_latch_predicate": DYING_LATCH_PREDICATE_VA,
                    "dying_latch_vtable_slot": 0x40,
                    "dying_latch_rule": (
                        "current_hp_zero_and_death_timer_greater_than_zero"
                    ),
                    "dying_latch_value_seconds": DYING_LATCH_TIMER_SECONDS,
                    "death_task_predicate": DEATH_TASK_PREDICATE_VA,
                    "death_task_vtable_slot": 0x3C,
                    "death_task_rule": (
                        "current_hp_zero_and_death_timer_less_than_or_equal_"
                        "to_zero"
                    ),
                    "death_task_value_seconds": DEATH_TASK_TIMER_SECONDS,
                    "zero_float_constant": ZERO_FLOAT_CONSTANT_VA,
                    "elapsed_wire_bytes": (
                        NPC_HP_LINK_TIMER_ELAPSED_WIRE_BYTES.hex()
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
                "pinned_damage_wire": dict(NPC_HP_LINK_DAMAGE_PINNED),
            },
            "hp_ladder": {
                "owner": "the_target_not_the_player",
                "start": NPC_HP_LINK_HP_START,
                "max": NPC_HP_LINK_HP_MAX,
                "floor": NPC_HP_LINK_HP_FLOOR,
                "ladder": list(NPC_HP_LINK_BALANCE_LADDER),
                "clamp_step": NPC_HP_LINK_CLAMP_STEP_LABEL,
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
                "nearest_placement_to_the_frozen_v135_player_spawn"
            ),
            "target_identity_formula": "0x2000_plus_placement_index_plus_1",
            "target_placement_index": NPC_HP_LINK_TARGET_PLACEMENT_INDEX,
            "target_template_id": NPC_HP_LINK_TARGET_TEMPLATE_ID,
            "target_identity_lo": NPC_HP_LINK_TARGET_IDENTITY_LO,
            "target_identity_hi": NPC_HP_LINK_TARGET_IDENTITY_HI,
            "target_visual_preset": NPC_HP_LINK_TARGET_VISUAL_PRESET,
            "target_source_name": NPC_HP_LINK_TARGET_SOURCE_NAME,
            "position_source": "frozen_v135_player_spawn",
            "pins_are_composed_from_a_fixed_probe_identity": True,
            "performer_probe_identity_lo": (
                NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_LO
            ),
            "performer_probe_identity_hi": (
                NPC_HP_LINK_PERFORMER_PROBE_IDENTITY_HI
            ),
            "scene_id": SCENE_ID,
            "scene_sequence": SCENE_SEQUENCE,
            "parent_pin_sources": {
                label: list(source)
                for label, source in NPC_HP_LINK_PARENT_PIN_SOURCES.items()
            },
            "per_step": {
                label: {
                    "pc_size": NPC_HP_LINK_PINS[label]["pc_size"],
                    "pc_sha256": NPC_HP_LINK_PINS[label]["pc_sha256"],
                    "frame_size": NPC_HP_LINK_PINS[label]["frame_size"],
                    "frame_sha256": NPC_HP_LINK_PINS[label]["frame_sha256"],
                }
                for label in NPC_HP_LINK_STEP_ORDER
            },
        },
        "persisted_post_state": {
            "database_write": "none",
        },
        "capabilities": list(NPC_HP_LINK_CAPABILITIES),
        "nonclaims": list(NPC_HP_LINK_NONCLAIMS),
    }


def load_npc_hp_link_hypothesis_scenario(
    path: Any,
) -> NpcHpLinkHypothesisScenario:
    """Load the one opt-in scenario file, or refuse with no lane."""
    if path is None:
        raise NpcHpLinkValidationError("scenario_file_exceeds_allowlist")
    resolved = Path(path)
    try:
        raw = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise NpcHpLinkValidationError(
            "scenario_file_exceeds_allowlist: %s" % exc
        ) from exc
    if _exact_equal(raw, _expected_scenario()):
        return _PROFILE
    raise NpcHpLinkValidationError("scenario_file_exceeds_allowlist")
