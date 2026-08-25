"""LANE-B / MOB-DEATH-001: the half where the monster actually dies.

WHAT THIS MODULE IS FOR.  M4 is "hit it, its blood drops, it dies".  The
previous lane-B round built the first half (``mob_combat``) and stopped at a
floor of 1 HP on purpose, because an HP of zero WITHOUT the death timer field
is a state whose client behaviour nobody in this project has observed.  This
module is the second half: it takes a hit outcome that reached zero and
composes the two actor frames the client's own death chain requires, keeps a
register of who is dead, and rebuilds a population without resurrecting them.

    dying frame   <- the SAME identity, HP 0 and death timer STRICTLY POSITIVE
    death frame   <- the SAME identity, HP 0 and death timer <= 0
    register      <- who died, to whom, so nothing re-spawns them alive
    corpse entry  <- what a later re-apply must send for a dead identity

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True.  There is no
scenario id, no dispatch kwarg, no unlock object and no allowlisted profile
anywhere in this file.  The lane that PROVED this chain
(``runtimeres_death_hypothesis``, HYP-PF-023) is a scenario-gated probe whose
BasicAttr bit 0x0080 cannot even be NAMED without a lethal unlock token that
only an allowlisted scenario object hands out - a build the owner boots with no
flags cannot reach one byte of it.  So the encoder is RE-DERIVED here, in
general form, from the same static anchors, and ``tests/test_mob_death.py``
pins every constant and the composed bytes against that probe lane value by
value and byte by byte.  This module imports NO probe lane.  The owner has
approved crossing the ad-hoc "never send HP 0" restriction in order to test
death (COO CHARTER-02 / BUILD-005), so the restriction that remains is the one
this module enforces itself: HP 0 may only be composed TOGETHER with the timer
field, which is exactly the pair the client's gate reads.

THE CHAIN, AND WHY IT IS TWO FRAMES AND NOT ONE.

* The carrier is the actor-entry collection of ``GSCN_RunTimeProtocolRes``
  (derived change-mask bit 0x02) - the same carrier ``field_mobs`` and
  ``mob_combat.bar_frames`` already use.  ``UpdateAttrVital`` cannot reach the
  death chain at all (its inbound handler contains zero indirect dispatch
  shapes over its whole extent), which is why the bar-refresh carrier is the
  right one and the vital carrier is not.
* AN ACTOR CANNOT BE BORN DEAD.  The inbound handler looks the entry's 64-bit
  identity up: FOUND -> the apply-and-dead-sync path; NOT FOUND -> the spawn,
  which never touches the dead sync.  A field mob is already on screen when a
  player kills it, so this lane always takes the FOUND branch - but that is
  also why a re-apply that re-sends a dead monster as a live body brings it
  back to life, and why :func:`repopulation_entries` exists.
* THE TIMER POLARITY IS INVERTED FROM INTUITION.  ``timer > 0`` is the DYING
  side (the latch); ``timer <= 0`` is the DEAD side (the task that builds
  CActorTask_Dead and plays the die animation).  Getting this backwards
  composes two frames that look right and kill nothing.
* THE CLIENT DOES NOT COUNT THE TIMER DOWN.  FACTPACK R102 settled this against
  a live observation: after a dying frame the on-screen number ticks down, but
  ``BasicAttr.f32[+0x58]`` has NO writer anywhere in the image that decrements
  it - not float, not integer - and no display path reads it at all.  The
  number a tester watched belongs to a UI widget counting on its own clock.
  So the field FREEZES at whatever the server last sent, and the second frame
  is REQUIRED: without it the monster falls, shows a countdown, and then stands
  there dying forever.

WHAT IS CLIENT-OBSERVABLE ALREADY, AND WHAT IS NOT.  READ THIS BEFORE WRITING
ANY SENTENCE ABOUT A CORPSE.  Both frames have already been sent to a real
client through this exact carrier, and the results are split:

* THE FALL IS PROVEN, TWICE OVER.  GT-022 (2026-08-19, run 2, Panya at the
  screen) and GT-025 (repeated twice) sent SPAWN + DYING_LATCH to an
  actor_type 4 NPC standing in Port Royal at identity 0x2001 - a placement the
  client already had on its map, exactly like this lane's monsters.  The NPC
  went from standing to LYING FLAT ON ITS BACK, stayed down at t+10, t+13 and
  t+16, and the client itself wrote a line into chat: "badly wounded and
  fell".  GT-025 is what isolated it: it sent NO death-task frame at all
  (``grep -c DEATH_TASK`` = 0 over the whole console) and got the same fall.
  So the lying pose belongs to the DYING frame.
* THE DEATH TASK'S OWN EFFECT IS NOT PROVEN, AND THIS PROJECT FORBIDS
  CLAIMING IT.  The dead frame has been sent twice and nothing distinguishable
  followed it; ``_F_DIE_000`` has never been observed by anyone here, and
  GT-025's result says in terms that every sentence reading GT-022 as evidence
  of that animation must be withdrawn.  This module therefore sends the frame
  for what is DERIVED (the static gate needs it, and R102 proves the timer
  freezes at 20.0 without it) and claims nothing about what it draws.
* What GT-023 watched escalate all the way to a death window was the LOCAL
  PLAYER's own path, a different actor class, and it is not this lane's
  evidence either.

WHAT THE PLAYER SEES THAT THEY DID NOT SEE YESTERDAY.  Yesterday a monster a
player fought converged to 1 HP and stayed there forever, and the server
answered every further hit with silence - that was this lane's own nonclaim.
Today the last hit takes it to zero and this module hands back the frames that
drop it, plus the register that keeps it down through a re-apply.
[PROPOSED, not measured] once the chief writes the wiring line, a monster in
Port Royal that a player hits enough times falls flat and stays there on a
build booted with no flags - the state GT-022 and GT-025 watched, reached for
the first time by HITTING something rather than by typing a chat trigger.
It is PROPOSED and not MEASURED for two named reasons: nobody has yet observed
a real attack input producing the EA7D ActionVital ``mob_combat`` reads, and
nobody has watched this lane's own body - named AND hostile AND at zero - land
on a screen at all.

NOTHING IS INSTALLED.  No socket, no clock, no randomness, no database, no
global state, no import-time side effect.  Every function is a pure function of
its arguments and every state object is a frozen dataclass.  Contract breaches
raise :class:`MobDeathContractError` with a NAMED reason.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mobs
from . import mob_combat
from .field_mobs import FieldMob
from .mob_combat import HitOutcome
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
    SCENE_ID,
    SCENE_SEQUENCE,
)


# Convention markers only; nothing in this tree branches on them.
production_allowed = True
test_only = False

MOB_DEATH_MILESTONE = "MOB-DEATH-001"
MOB_DEATH_BUILD_ORDER = "BUILD-005 / M4 second half"
MOB_DEATH_LANE = "B_COMBAT"

# The one line this lane owes the chief, written where a reader of the module
# finds it rather than only in a PR body.
MOB_DEATH_WIRING = (
    "runtime.py: after mob_combat.commit_step accepts a step whose "
    "outcome.death_due is True, call mob_death.kill(legacy, mob, "
    "step.outcome, register); send step.frames (the announce) first, then "
    "death_step.dying_frame, then death_step.dead_frame after "
    "death_step.hold_ms; keep death_step.register and build every later "
    "collection for this scene with mob_death.repopulation_entries(legacy, "
    "roster, register, ledger=ledger) so a re-apply neither resurrects a "
    "corpse nor heals a wounded monster back to its ceiling."
)

# ---------------------------------------------------------------------------
# The wire.  Every constant below is a static anchor carried WITH provenance
# rather than imported from the probe lane that proved it, and every one of
# them is pinned value-for-value against that lane in tests/test_mob_death.py.
#
#   BasicAttr serializer 0x4656F0 writes its fields in ASCENDING MASK-BIT
#   order.  Bit 0x0080 is the f32 at object offset +0x58, wire tag 0x2A, and it
#   is written after 0x0008 (max HP) and before 0x0100 (scene id).
#   legacy.make_npc_attr cannot emit it: V62 chose to omit bit 0x0080 entirely.
# ---------------------------------------------------------------------------
BASIC_BIT_NAME = 0x0001
BASIC_BIT_CURRENT_HP = 0x0004          # u32 tag 0x14 @ +0x44
BASIC_BIT_MAX_HP = 0x0008              # u32 tag 0x14 @ +0x48
BASIC_BIT_DEATH_TIMER = 0x0080         # f32 tag 0x2A @ +0x58
BASIC_BIT_SCENE_ID = 0x0100            # u16 tag 0x12
BASIC_BIT_SCENE_SEQ = 0x0200           # qword tag 0x32
BASIC_BIT_FACTION = 0x0400             # u32 tag 0x14 @ +0x68

DEATH_TIMER_TAG = 0x2A
DEATH_TIMER_OBJECT_OFFSET = 0x58
DEATH_TIMER_WIDTH = 4
DEATH_TIMER_SPLICE_BYTES = 1 + DEATH_TIMER_WIDTH

DB_ATTRIBUTE_MASK_TAG = 0x0B
DB_ATTRIBUTE_IDENTITY_MASK = 0x01
BASIC_ATTR_MASK_TAG = 0x12
IDENTITY_TAG = 0x32
U32_TAG = 0x14
NPC_ATTR_MASK_TAG = 0x0B
NPC_BIT_TEMPLATE = 0x01
NPC_BIT_VISUAL_PRESET = 0x04

# The two sides of the gate.  Timer STRICTLY POSITIVE latches the dying state;
# timer <= 0 is what lets the death task be constructed.  Read that twice: it
# is the single fact most likely to be got backwards.
HP_WHEN_DEAD = 0
DYING_TIMER_SECONDS = 20.0
DEAD_TIMER_SECONDS = 0.0

# Static anchors of the chain, kept so a reader does not have to go and find
# them, and so a test can pin them against the lane that derived them.
DYING_PREDICATE_VA = 0x43BDA0          # actor vtable +0x40, needs timer > 0
DEATH_PREDICATE_VA = 0x43BD70          # actor vtable +0x3C, needs timer <= 0
DYING_LATCH_WRITE_VA = 0x44384C        # [actor+0x70] |= 0x200
DEATH_TASK_GATE_VA = 0x443990          # builds the task when the gate holds
DEATH_TASK_CTOR_VA = 0x472810          # CActorTask_Dead
DEATH_ANIMATION_NAME_VA = 0xF0F060     # L"_F_DIE_000"
DEATH_ANIMATION_NAME = "_F_DIE_000"
# FACTPACK R102 pins a SECOND pair of predicates reading the same +0x58 field
# (0x454A70 at vt+0x3C and 0x454AC0 at vt+0x40) plus the local player's
# Main_Dead open-gate at 0x44A540.  This lane does not claim which actor class
# each pair belongs to; it composes the field both pairs read.
R102_PREDICATE_VAS = (0x454A70, 0x454AC0, 0x44A540)

# OURS, not measured: how long the fallen monster is left in the dying state
# before the frame that finishes it.  Two frames processed inside one client
# frame would race the per-frame update that consumes the latch, so the hold is
# far above any plausible tick.  The ONLY spacing ever put on a client through
# this carrier is GT-022's 6000 ms, and that number was chosen so a human with
# a camera could keep up - six seconds between a monster falling and a monster
# dying is not a game.  700 ms is far clear of any frame and is the only
# death-adjacent duration this project has measured for anything (GT-030's
# ~0.7 s animation on the other actor class), so the fall and the finish read
# as one motion.
# [LANE-B ASSUMPTION - awaiting COO confirmation] - the letter for this round
# carries the question and what has to be undone if the answer is different:
# nothing but this one number, which no other value in the module depends on.
DEATH_TASK_HOLD_MS = 700

MOB_DEATH_NONCLAIMS = (
    "the death animation _F_DIE_000 has never been observed by anyone in this "
    "project; GT-025 proved the lying pose belongs to the DYING frame and "
    "requires every reading of GT-022 as evidence of that animation to be "
    "withdrawn, so this lane claims the FALL and not the corpse",
    "the death-task frame has been sent to a real client twice with nothing "
    "distinguishable following it; it is sent here because the static gate "
    "needs it, not because its effect has been watched",
    "nothing dispatches this module: runtime.py belongs to the chief and the "
    "one wiring line has not been written",
    "the hold between the two frames is OURS and unmeasured; the only spacing "
    "ever sent to a client on this carrier is GT-022's 6000 ms, which is "
    "unplayable, and whether the client needs any hold at all is unknown",
    "the dying frame's countdown widget is a client-side counter on its own "
    "clock (FACTPACK R102); how long it lingers over a monster this lane "
    "kills has not been observed",
    "the fall was watched on a NAMELESS, FACTIONLESS actor_type 4 body "
    "(GT-022/GT-025 at identity 0x2001); this lane's body is named and "
    "hostile and nobody has seen one of those at zero HP",
    "a real attack input has never been observed producing the EA7D "
    "ActionVital that reaches mob_combat, so the inbound half of the kill is "
    "as unproven as the inbound half of the hit",
    "named AND hostile in one body has never been sent and never been "
    "observed; the corpse body inherits that nonclaim from field_mobs and "
    "adds a bit nobody has combined with it either (mask 0x078D)",
    "nothing here decides loot: what a dead monster drops is M5, and the "
    "drop ids in the roster are carried, not read, by this lane",
    "the register lives in the caller's process only; nothing in this project "
    "persists a monster's death across a server restart",
)

REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_TIMER_NOT_FINITE = "timer_not_finite"
REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE = "timer_wrong_side_of_the_gate"
REFUSE_LIVE_HP_WITH_A_DEATH_TIMER = "live_hp_with_a_death_timer"
REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER = "dead_hp_without_a_death_timer"
REFUSE_BODY_OFF_THE_LIVE_PROJECTION = "body_off_the_live_projection"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"
REFUSE_OUTCOME_IS_NOT_A_KILL = "outcome_is_not_a_kill"
REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER = "outcome_names_another_monster"
REFUSE_ALREADY_DEAD = "already_dead"
REFUSE_NOT_DEAD = "not_dead"
REFUSE_REGISTER_NOT_SORTED = "register_not_sorted"
REFUSE_DUPLICATE_REGISTER_IDENTITY = "duplicate_register_identity"
REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER = "register_row_disagrees_with_roster"
REFUSE_LEDGER_DISAGREES_WITH_REGISTER = "ledger_disagrees_with_register"
REFUSE_OUTCOME_DISAGREES_WITH_ROSTER = "outcome_disagrees_with_roster"
# ~~REFUSE_HOLD_OUT_OF_RANGE~~ never declared as its own name: the hold is
# checked by the same range check as every other integer here, which raises
# REFUSE_VALUE_OUT_OF_RANGE, and a second name that can never be raised is a
# lie told to whoever counts them.
MOB_DEATH_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_TIMER_NOT_FINITE,
    REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
    REFUSE_LIVE_HP_WITH_A_DEATH_TIMER,
    REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER,
    REFUSE_BODY_OFF_THE_LIVE_PROJECTION,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
    REFUSE_OUTCOME_IS_NOT_A_KILL,
    REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
    REFUSE_ALREADY_DEAD,
    REFUSE_NOT_DEAD,
    REFUSE_REGISTER_NOT_SORTED,
    REFUSE_DUPLICATE_REGISTER_IDENTITY,
    REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
    REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
    REFUSE_OUTCOME_DISAGREES_WITH_ROSTER,
)

_FLOAT32_MAX = 3.4028234663852886e38


class MobDeathContractError(ValueError):
    """A refusal from this module, always carrying a named reason."""

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_DEATH_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise MobDeathContractError(
            REFUSE_VALUE_NOT_INT, "%s must be a plain int" % label)
    if not minimum <= value <= maximum:
        raise MobDeathContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "%s must be within [%d, %d], got %d" % (
                label, minimum, maximum, value),
        )
    return value


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, 0xFFFFFFFFFFFFFFFF)
    if identity <= 0:
        raise MobDeathContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_timer(value: Any) -> float:
    if type(value) not in (int, float) or type(value) is bool:
        raise MobDeathContractError(
            REFUSE_TIMER_NOT_FINITE, "the death timer must be a number")
    timer = float(value)
    if not math.isfinite(timer) or abs(timer) > _FLOAT32_MAX:
        raise MobDeathContractError(
            REFUSE_TIMER_NOT_FINITE,
            "the death timer must be a finite float32 value")
    return timer


def _require_mob(mob: Any) -> FieldMob:
    if type(mob) is not FieldMob:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    return mob


@dataclass(frozen=True)
class DeathRecord:
    """One monster's death: who it was, who killed it, what it stood at."""

    actor_identity: int
    killer_identity: int
    max_hp: int

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity, "actor identity")
        _require_identity(self.killer_identity, "killer identity")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        if self.actor_identity == self.killer_identity:
            raise MobDeathContractError(
                REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
                "a monster cannot be its own killer on this lane")


@dataclass(frozen=True)
class DeathRegister:
    """Who is dead, as a tuple sorted by identity.

    Sorted-tuple rather than a set or a dict for the reason ``CombatLedger``
    gives: two registers built from the same kills compare equal in any
    process, and no caller can mutate a record behind the lane's back.
    """

    records: tuple[DeathRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple:
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "records must be a tuple")
        seen = set()
        for record in self.records:
            if type(record) is not DeathRecord:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every register row must be a typed DeathRecord")
            if record.actor_identity in seen:
                raise MobDeathContractError(
                    REFUSE_DUPLICATE_REGISTER_IDENTITY,
                    "identity 0x%X appears twice" % record.actor_identity)
            seen.add(record.actor_identity)
        ordered = tuple(sorted(
            self.records, key=lambda row: row.actor_identity))
        if ordered != self.records:
            raise MobDeathContractError(
                REFUSE_REGISTER_NOT_SORTED,
                "register rows must be given in ascending identity order")

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.records)

    def is_dead(self, actor_identity: int) -> bool:
        wanted = _require_identity(actor_identity, "actor identity")
        return any(row.actor_identity == wanted for row in self.records)

    def record_of(self, actor_identity: int) -> DeathRecord:
        wanted = _require_identity(actor_identity, "actor identity")
        for row in self.records:
            if row.actor_identity == wanted:
                return row
        raise MobDeathContractError(
            REFUSE_NOT_DEAD,
            "identity 0x%X is not in this register" % wanted)

    def with_death(self, record: DeathRecord) -> "DeathRegister":
        if type(record) is not DeathRecord:
            raise MobDeathContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "the addition must be a typed DeathRecord")
        if self.is_dead(record.actor_identity):
            raise MobDeathContractError(
                REFUSE_ALREADY_DEAD,
                "identity 0x%X is already in the register: a second kill on "
                "the same monster is a caller bug, not an event" % (
                    record.actor_identity),
            )
        return DeathRegister(tuple(sorted(
            self.records + (record,), key=lambda row: row.actor_identity)))


def _compose_body(
    legacy: Any,
    mob: FieldMob,
    *,
    current_hp: int,
    death_timer: float | None,
    faction: int,
    scene_id: int,
    scene_sequence: int,
    with_name: bool,
) -> bytes:
    """The hostile body, optionally carrying BasicAttr bit 0x0080.

    Written out field by field rather than spliced, because the timer lands in
    the MIDDLE of the BasicAttr block (after max HP, before scene id) and a
    splice would have to compute that offset from a body whose name field is
    variable-length.  What keeps a hand-written composer honest is the check in
    :func:`corpse_npc_attr`: with the timer absent it must reproduce
    ``field_mobs.hostile_npc_attr`` byte for byte.
    """
    basic_mask = (
        BASIC_BIT_CURRENT_HP | BASIC_BIT_MAX_HP
        | BASIC_BIT_SCENE_ID | BASIC_BIT_SCENE_SEQ | BASIC_BIT_FACTION
    )
    if with_name and mob.display_name:
        basic_mask |= BASIC_BIT_NAME
    if death_timer is not None:
        basic_mask |= BASIC_BIT_DEATH_TIMER
    npc_mask = NPC_BIT_TEMPLATE | (
        NPC_BIT_VISUAL_PRESET if mob.visual_preset else 0)
    out = bytearray()
    out += legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK)
    out += legacy.qwordtag(IDENTITY_TAG, mob.actor_identity)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, basic_mask)
    # Ascending mask-bit order, which is the order BasicAttr's serializer
    # 0x4656F0 writes and its reader expects.
    if basic_mask & BASIC_BIT_NAME:
        out += legacy.wstr_tag(mob.display_name)               # 0x0001
    out += legacy.u32tag(U32_TAG, current_hp)                  # 0x0004
    out += legacy.u32tag(U32_TAG, mob.max_hp)                  # 0x0008
    if death_timer is not None:
        out += legacy.f32tag(death_timer)                      # 0x0080
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, scene_id)        # 0x0100
    out += legacy.qwordtag(IDENTITY_TAG, scene_sequence)       # 0x0200
    out += legacy.u32tag(U32_TAG, faction)                     # 0x0400
    out += legacy.u8tag(NPC_ATTR_MASK_TAG, npc_mask)
    out += legacy.u16tag(BASIC_ATTR_MASK_TAG, mob.template_id)
    if mob.visual_preset:
        out += legacy.wstr_tag(mob.visual_preset)
    return bytes(out)


def basic_mask_of(legacy: Any, body: bytes, actor_identity: int) -> int:
    """The BasicAttr u16 mask a composed body actually carries.

    Read out of the bytes rather than remembered, so a pin or a test that
    quotes "mask 0x078D" is quoting the wire and not this module's opinion of
    it.  The head is the DBAttribute mask plus the tagged identity, and the
    mask value follows its own tag byte.
    """
    identity = _require_identity(actor_identity, "actor identity")
    if type(body) is not bytes:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "body must be bytes")
    head = (
        bytes(legacy.u8tag(DB_ATTRIBUTE_MASK_TAG, DB_ATTRIBUTE_IDENTITY_MASK))
        + bytes(legacy.qwordtag(IDENTITY_TAG, identity))
    )
    if not body.startswith(head) or len(body) < len(head) + 3:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "this body does not open with the DBAttribute mask and the "
            "tagged identity 0x%X" % identity,
        )
    at = len(head) + 1
    return int.from_bytes(body[at:at + 2], "little")


def corpse_npc_attr(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float | None,
    current_hp: int = HP_WHEN_DEAD,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> bytes:
    """The hostile body at HP 0 plus EXACTLY the five bytes of the timer.

    THE SELF-CHECK IS THE PROOF, and it runs on every call.  The same composer,
    asked for a LIVE body with no timer, must reproduce
    ``field_mobs.hostile_npc_attr`` byte for byte - the body this project
    already ships and whose bar movement GT-035 watched.  A composer that
    drifts therefore fails closed instead of putting a guessed body on the
    wire, and the lethal body is that known-good body plus one tagged f32 in
    the one position the serializer's ascending-bit order allows.
    """
    _require_mob(mob)
    if type(with_name) is not bool:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_name must be a bool")
    hp = _require_int(current_hp, "current hp", 0, mob.max_hp)
    if death_timer is None:
        # The pair is the whole point.  A body at zero HP with no timer field
        # satisfies NEITHER side of the client's gate - 0x43BD70 wants
        # timer <= 0 and 0x43BDA0 wants timer > 0, and an absent field is
        # whatever the actor's BasicAttr already held - so it composes a
        # monster that is empty and not dying and not dead.
        raise MobDeathContractError(
            REFUSE_DEAD_HP_WITHOUT_A_DEATH_TIMER,
            "a body at HP %d must carry the death timer; pick a side of the "
            "gate rather than sending neither" % hp,
        )
    timer = _require_timer(death_timer)
    _require_int(faction, "faction", 1, 0xFFFFFFFF)
    if hp != HP_WHEN_DEAD:
        # Bit 0x0080 on a body that still has HP is a state this project has
        # never composed and whose meaning nobody has derived: 0x43BD70 and
        # 0x43BDA0 both require +0x44 == 0 before they look at the timer at
        # all, so such a frame would carry a lethal field that no gate reads.
        raise MobDeathContractError(
            REFUSE_LIVE_HP_WITH_A_DEATH_TIMER,
            "a death timer belongs on a body at HP %d, not %d" % (
                HP_WHEN_DEAD, hp),
        )
    live_reference = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=mob.max_hp, scene_id=scene_id,
        scene_sequence=scene_sequence, faction=faction, with_name=with_name,
    )
    degraded = _compose_body(
        legacy, mob, current_hp=mob.max_hp, death_timer=None, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if degraded != live_reference:
        raise MobDeathContractError(
            REFUSE_BODY_OFF_THE_LIVE_PROJECTION,
            "the timerless projection of this composer no longer reproduces "
            "field_mobs.hostile_npc_attr byte for byte, so the lethal body it "
            "would compose is a guess",
        )
    composed = _compose_body(
        legacy, mob, current_hp=hp, death_timer=timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if len(composed) != len(live_reference) + DEATH_TIMER_SPLICE_BYTES:
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "the corpse body is %d bytes and the live body plus a tagged f32 "
            "is %d" % (len(composed), len(live_reference)
                       + DEATH_TIMER_SPLICE_BYTES),
        )
    return composed


def death_actor_entry(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
    with_movement: bool = False,
) -> bytes:
    """One actor entry carrying the corpse body.

    ``with_movement`` defaults to False for the reason ``mob_combat.bar_frames``
    gives: a refresh that re-sends the movement attribute snaps the actor back
    to its roster row, which on a kill would teleport the body to where the
    monster was standing when the scene loaded rather than where it fell.
    """
    body = corpse_npc_attr(
        legacy, mob, death_timer=death_timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    if type(with_movement) is not bool:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_movement must be a bool")
    attrs = [(NPC_ATTR_ID, body)]
    if with_movement:
        attrs.append((
            MOVEMENT_ATTR_ID,
            legacy.make_remote_movement_attr(
                mob.actor_identity, mob.x, mob.y, mob.z,
                field_mobs.HEADINGS[mob.placement_index & 3],
                mask=FULL_MOVEMENT_MASK,
            ),
        ))
    return legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, mob.actor_identity, attrs)


def death_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """One RuntimeRes collection carrying one corpse entry."""
    entry = death_actor_entry(
        legacy, mob, death_timer=death_timer, faction=faction,
        scene_id=scene_id, scene_sequence=scene_sequence, with_name=with_name,
    )
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "death frame drift")
    return pc, frame


def dying_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float = DYING_TIMER_SECONDS,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """The frame that drops the monster: HP 0 and a STRICTLY POSITIVE timer."""
    timer = _require_timer(death_timer)
    if not timer > 0.0:
        raise MobDeathContractError(
            REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
            "the dying latch needs a timer above zero (vtable +0x40 at "
            "0x%X compares 0.0 < timer); got %r" % (DYING_PREDICATE_VA, timer),
        )
    return death_frames(
        legacy, mob, death_timer=timer, faction=faction, scene_id=scene_id,
        scene_sequence=scene_sequence, with_name=with_name,
    )


def dead_frames(
    legacy: Any,
    mob: FieldMob,
    *,
    death_timer: float = DEAD_TIMER_SECONDS,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    scene_id: int = SCENE_ID,
    scene_sequence: int = SCENE_SEQUENCE,
    with_name: bool = True,
) -> tuple[bytes, bytes]:
    """The frame that finishes it: HP 0 and a timer AT OR BELOW zero."""
    timer = _require_timer(death_timer)
    if timer > 0.0:
        raise MobDeathContractError(
            REFUSE_TIMER_WRONG_SIDE_OF_THE_GATE,
            "the death task needs a timer at or below zero (vtable +0x3C at "
            "0x%X refuses while 0.0 < timer); got %r" % (
                DEATH_PREDICATE_VA, timer),
        )
    return death_frames(
        legacy, mob, death_timer=timer, faction=faction, scene_id=scene_id,
        scene_sequence=scene_sequence, with_name=with_name,
    )


@dataclass(frozen=True)
class DeathStep:
    """One kill, end to end: both frames, the hold between them, the register.

    The caller owns dispatch.  It owes the two frames IN ORDER with the hold
    between them, and it owes storing :attr:`register` - a caller that sends
    the frames and drops the register has a corpse on screen that the next
    re-apply stands back up at full HP.
    """

    record: DeathRecord
    dying_pc: bytes
    dying_frame: bytes
    dead_pc: bytes
    dead_frame: bytes
    register: DeathRegister
    hold_ms: int = DEATH_TASK_HOLD_MS

    def __post_init__(self) -> None:
        for label, value in (("record", self.record),
                             ("register", self.register)):
            expected = DeathRecord if label == "record" else DeathRegister
            if type(value) is not expected:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be a typed %s" % (label, expected.__name__))
        for label, value in (("dying pc", self.dying_pc),
                             ("dying frame", self.dying_frame),
                             ("dead pc", self.dead_pc),
                             ("dead frame", self.dead_frame)):
            if type(value) is not bytes or not value:
                raise MobDeathContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be non-empty bytes" % label)
        _require_int(self.hold_ms, "hold ms", 0, 60_000)
        if not self.register.is_dead(self.record.actor_identity):
            raise MobDeathContractError(
                REFUSE_NOT_DEAD,
                "the step's own register does not carry the monster it killed")

    @property
    def frames(self) -> tuple[bytes, ...]:
        """Dying first, dead second.  Never one without the other.

        The client freezes ``BasicAttr.f32[+0x58]`` at whatever the server last
        sent (FACTPACK R102: no writer in the image decrements it), so a caller
        that sends only the first frame leaves a monster dying forever.
        """
        return (self.dying_frame, self.dead_frame)

    @property
    def schedule(self) -> tuple[tuple[int, bytes], ...]:
        """The same two frames with the delay each one owes, in milliseconds."""
        return ((0, self.dying_frame), (self.hold_ms, self.dead_frame))


def kill(
    legacy: Any,
    mob: FieldMob,
    outcome: HitOutcome,
    register: DeathRegister | None = None,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    hold_ms: int = DEATH_TASK_HOLD_MS,
    dying_timer: float = DYING_TIMER_SECONDS,
    dead_timer: float = DEAD_TIMER_SECONDS,
    with_name: bool = True,
) -> DeathStep:
    """Finish a monster that a hit already took to zero.

    This lane does NO arithmetic.  ``mob_combat`` computed the damage, moved
    the balance and set ``death_due``; the only thing left is to answer the
    frames.  An outcome that is not a kill is REFUSED by name rather than
    quietly turned into one, because a lane that can kill a monster the
    arithmetic did not kill is a lane that can kill a monster at full HP.
    """
    _require_mob(mob)
    if type(outcome) is not HitOutcome:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    live = DeathRegister() if register is None else register
    if type(live) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    if outcome.target_identity != mob.actor_identity:
        raise MobDeathContractError(
            REFUSE_OUTCOME_NAMES_ANOTHER_MONSTER,
            "the outcome names 0x%X and the mob is 0x%X" % (
                outcome.target_identity, mob.actor_identity),
        )
    if outcome.max_hp != mob.max_hp:
        # Its own name, not the register's: the announced number came from
        # one ceiling and the body would be composed against another.
        raise MobDeathContractError(
            REFUSE_OUTCOME_DISAGREES_WITH_ROSTER,
            "the outcome stands at a ceiling of %d and the roster says %d" % (
                outcome.max_hp, mob.max_hp),
        )
    if not outcome.death_due or outcome.hp_after != HP_WHEN_DEAD:
        raise MobDeathContractError(
            REFUSE_OUTCOME_IS_NOT_A_KILL,
            "this outcome leaves the monster at %d of %d HP; only a hit that "
            "reached %d may be finished here" % (
                outcome.hp_after, outcome.max_hp, HP_WHEN_DEAD),
        )
    if live.is_dead(mob.actor_identity):
        raise MobDeathContractError(
            REFUSE_ALREADY_DEAD,
            "identity 0x%X is already dead: a second kill would send a second "
            "pair of frames for a corpse" % mob.actor_identity,
        )
    _require_int(hold_ms, "hold ms", 0, 60_000)
    record = DeathRecord(
        mob.actor_identity, outcome.attacker_identity, mob.max_hp)
    dying_pc, dying_frame = dying_frames(
        legacy, mob, death_timer=dying_timer, faction=faction,
        with_name=with_name)
    dead_pc, dead_frame = dead_frames(
        legacy, mob, death_timer=dead_timer, faction=faction,
        with_name=with_name)
    return DeathStep(
        record, dying_pc, dying_frame, dead_pc, dead_frame,
        live.with_death(record), hold_ms,
    )


def live_roster(
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
) -> tuple[FieldMob, ...]:
    """The monsters that are still alive, in the order they were given."""
    if type(roster) is not tuple:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    if type(register) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    for mob in roster:
        _require_mob(mob)
    dead = set(register.identities())
    return tuple(m for m in roster if m.actor_identity not in dead)


def repopulation_entries(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    ledger: Any = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
) -> list[bytes]:
    """Actor entries for a re-apply that must not resurrect anybody.

    PASS THE LEDGER.  It is optional only because a caller that has not opened
    one yet should still be able to build a scene, and leaving it out has a
    cost written here rather than discovered later: without it every LIVING
    monster is re-sent at its ceiling, so the bar a player just watched fall
    to a third snaps back to full on the next re-apply.  With it, each living
    monster is re-sent at the HP the arithmetic actually holds.

    THE HAZARD THIS CLOSES IS REAL AND IT IS THIS LANE'S OWN.  ``field_mobs``
    states that the accepted evidence was measured with the identical
    collection queued twice, the second time after model readiness
    (``INITIAL_REAPPLY_MS``), and any later census rebuild sends it again.
    Every one of those sends carries a LIVE body for every roster row, so a
    monster killed between two of them stands back up at full HP with no hit,
    no frame and no error anywhere - the client is simply told it is alive.
    A dead identity gets its corpse body here instead: same identity, HP 0,
    timer already on the dead side of the gate.
    """
    if type(roster) is not tuple:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    if type(register) is not DeathRegister:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed DeathRegister")
    if ledger is not None and type(ledger) is not mob_combat.CombatLedger:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "ledger must be a typed mob_combat.CombatLedger or None")
    entries = []
    for mob in roster:
        _require_mob(mob)
        if not register.is_dead(mob.actor_identity):
            current_hp = None
            if ledger is not None:
                # balance_of raises mob_combat's own named refusal when the
                # ledger and the roster were built from different rosters.
                current_hp = ledger.balance_of(mob.actor_identity).current_hp
                if current_hp == HP_WHEN_DEAD:
                    # Dead in the arithmetic and alive in the register: the
                    # kill was computed and never finished.  Sending a live
                    # body resurrects it, sending a corpse claims a kill
                    # nobody committed, so this refuses and names both.
                    raise MobDeathContractError(
                        REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
                        "identity 0x%X stands at 0 HP in the ledger and is "
                        "not in the death register: call mob_death.kill for "
                        "it, or re-open the ledger" % mob.actor_identity,
                    )
            entries.append(field_mobs.hostile_actor_entry(
                legacy, mob, current_hp=current_hp, faction=faction,
                with_name=with_name))
            continue
        row = register.record_of(mob.actor_identity)
        if ledger is not None:
            # The mirror of the case above: dead in the register and standing
            # in the arithmetic.  Sending the corpse would be right on the
            # wire and wrong in the ledger, and the next hit on it would be
            # answered with a real damage number for a monster already down.
            standing = ledger.balance_of(mob.actor_identity).current_hp
            if standing != HP_WHEN_DEAD:
                raise MobDeathContractError(
                    REFUSE_LEDGER_DISAGREES_WITH_REGISTER,
                    "identity 0x%X is in the death register and stands at %d "
                    "HP in the ledger: the two were built from different "
                    "runs" % (mob.actor_identity, standing),
                )
        if row.max_hp != mob.max_hp:
            raise MobDeathContractError(
                REFUSE_REGISTER_ROW_DISAGREES_WITH_ROSTER,
                "identity 0x%X died at a ceiling of %d and the roster says "
                "%d: the two were built from different rosters" % (
                    mob.actor_identity, row.max_hp, mob.max_hp),
            )
        entries.append(death_actor_entry(
            legacy, mob, death_timer=dead_timer, faction=faction,
            with_name=with_name))
    return entries


def repopulation_frames(
    legacy: Any,
    roster: tuple[FieldMob, ...],
    register: DeathRegister,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_name: bool = True,
    dead_timer: float = DEAD_TIMER_SECONDS,
) -> tuple[bytes, bytes]:
    """One collection for a whole scene, with the dead sent as corpses."""
    entries = repopulation_entries(
        legacy, roster, register, faction=faction, with_name=with_name,
        dead_timer=dead_timer,
    )
    if not entries:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "a collection needs at least one entry")
    pc, frame = legacy.make_runtime_remote_actors(entries)
    if frame != legacy.frame_pc(pc):
        raise MobDeathContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "repopulation frame drift")
    return pc, frame


def describe_death(step: DeathStep) -> tuple[str, ...]:
    """Console lines for a kill, in the shape the runtime console prints."""
    if type(step) is not DeathStep:
        raise MobDeathContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed DeathStep")
    record = step.record
    return (
        "MOB-DEATH-001 kill: performer 0x%X -> target 0x%X (ceiling %d)" % (
            record.killer_identity, record.actor_identity, record.max_hp),
        "  dying frame %d bytes, timer %.1f (> 0, latches 0x%X) - this is the "
        "frame GT-022/GT-025 watched drop an NPC" % (
            len(step.dying_frame), DYING_TIMER_SECONDS, DYING_LATCH_WRITE_VA),
        "  dead frame %d bytes, timer %.1f (<= 0, gates 0x%X -> "
        "CActorTask_Dead 0x%X) - gate is static; its effect has never been "
        "observed" % (
            len(step.dead_frame), DEAD_TIMER_SECONDS, DEATH_TASK_GATE_VA,
            DEATH_TASK_CTOR_VA),
        "  hold %d ms between them [LANE-B assumption, unmeasured]" % (
            step.hold_ms),
        "  register now holds %d dead: %s" % (
            len(step.register.records),
            ", ".join("0x%X" % i for i in step.register.identities())),
    )


PIN_ID = "mob_death_second_half_001"
PIN_BUILD_ORDER = MOB_DEATH_BUILD_ORDER
PIN_LANE = MOB_DEATH_LANE
PIN_PLACEMENT_INDEX = field_mobs.CONTROL_PLACEMENT_INDEX


def pin_document(legacy: Any, mob: FieldMob, killer_identity: int = 0x750059) -> dict:
    """The numbers a report should quote, computed rather than transcribed.

    Lives in ``scenarios/`` because that is where this project keeps its pins;
    it is NOT a scenario, declares so in its own body, and no loader reads it.
    The kill it pins is driven all the way through ``mob_combat`` - an attacker
    strong enough to reach zero in one hit - so the pin proves the two lanes
    are joined rather than merely present in the same tree.
    """
    _require_mob(mob)
    ledger = mob_combat.open_ledger()
    attacker = mob_combat.Combatant(
        level=1000, ability_str=100000, ability_con=0)
    step = mob_combat.strike(
        legacy, None, ledger, None, mob, killer_identity, attacker)
    death = kill(legacy, mob, step.outcome, DeathRegister())
    live_body = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=mob.max_hp)
    corpse_body = corpse_npc_attr(legacy, mob, death_timer=DEAD_TIMER_SECONDS)
    return {
        "pin_id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_DEATH_MILESTONE,
        "production_allowed": production_allowed,
        "test_only": test_only,
        "not_a_scenario": True,
        "target_identity": mob.actor_identity,
        "target_name": ascii(mob.display_name),
        "target_faction": field_mobs.FIELD_MOB_FACTION,
        "max_hp": mob.max_hp,
        "hp_when_dead": HP_WHEN_DEAD,
        "killer_identity": killer_identity,
        "damage_wire": step.outcome.damage_wire,
        "announce_frame_bytes": len(step.announce_frame),
        "bar_frame_bytes": len(step.bar_frame),
        "dying_timer_seconds": DYING_TIMER_SECONDS,
        "dead_timer_seconds": DEAD_TIMER_SECONDS,
        "dying_frame_bytes": len(death.dying_frame),
        "dead_frame_bytes": len(death.dead_frame),
        "hold_ms": death.hold_ms,
        "hold_ms_is_ours": True,
        "live_body_bytes": len(live_body),
        "corpse_body_bytes": len(corpse_body),
        "basic_mask_live": "0x%04X" % basic_mask_of(
            legacy, live_body, mob.actor_identity),
        "basic_mask_corpse": "0x%04X" % basic_mask_of(
            legacy, corpse_body, mob.actor_identity),
        "death_timer_tag": "0x%02X" % DEATH_TIMER_TAG,
        "death_timer_object_offset": "0x%02X" % DEATH_TIMER_OBJECT_OFFSET,
        "dying_predicate_va": "0x%X" % DYING_PREDICATE_VA,
        "death_predicate_va": "0x%X" % DEATH_PREDICATE_VA,
        "death_task_gate_va": "0x%X" % DEATH_TASK_GATE_VA,
        "death_task_ctor_va": "0x%X" % DEATH_TASK_CTOR_VA,
        "death_animation": DEATH_ANIMATION_NAME,
        "wiring": MOB_DEATH_WIRING,
        "selection": "none_default_behaviour_no_scenario_flag",
        "nonclaims": list(MOB_DEATH_NONCLAIMS),
    }
