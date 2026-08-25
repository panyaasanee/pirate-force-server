"""LANE-B / MOB-COMBAT-001: the driver that turns a real hit into less HP.

WHAT THIS MODULE IS FOR.  M4 ("hit it, its blood drops, it dies") splits in
two, and the COO ruled the halves in order (COO-DECISION 2026-08-26T01:48+07:00,
section 3): first the driver that lowers a monster's HP from a REAL damage
number and feeds the threat table, then the death half.  This module is the
first half and only the first half.  It holds one integer balance per monster,
moves it by the damage the frozen formula computes, and composes the two frames
the client needs to show that movement: the hit announcement that floats the
number, and the actor frame that repaints the bar.

    damage number      <- the HYP-PF-024 formula, attacker profile vs defender
    balance            <- max_hp from field_mob_tables, moved only by a hit
    threat             <- handed to mob_aggro.apply_damage_threat, unchanged
    announce frame     <- CHitResult (vital 0x16F7), damage at entry +0x08
    bar frame          <- the field_mobs hostile body with a lower current_hp

NO FLAG, AND THAT IS THE POINT.  ``production_allowed`` is True, there is no
scenario id, no dispatch kwarg and no unlock object anywhere in this file.  The
proving lanes for both halves of this behaviour (HYP-PF-024 DAMAGE-MODEL-001,
HYP-PF-029, HYP-PF-038 HOSTILE-HP-LINK-001) are scenario-gated probes pinned to
one target, one ladder and one position; a version the owner boots without
flags cannot call any of them.  So the arithmetic and the two encoders are
RE-DERIVED here from the same static anchors, in general form, and the tests
pin this module's constants against the probe lanes' constants value by value.
This module imports NO probe lane; like ``field_mobs`` it takes the frozen V141
serializers as a passed-in ``legacy`` handle, and it takes ``mob_aggro`` the
same way, because that module states in its own docstring that nothing in
``src/`` imports it and that its dispatch reachability is False.  Passing it in
keeps both statements true and still gives the COO the wiring that was ordered.

WHERE THE EVIDENCE FOR EACH HALF COMES FROM, AND WHERE IT STOPS.

* The number.  DAMAGE-MODEL-001 proved byte-exactly that the client computes
  nothing about damage: what floats over an actor is the signed i32 the server
  put at hit-entry +0x08, passed through abs() and printed with "%d".  So the
  server must say both halves itself.  This module says both halves and refuses
  to let them disagree: the number announced is the number subtracted, always,
  including when the subtraction is clamped (see the floor, below).
* The bar.  GT-035 (2026-08-25, two observers, two runs, PASS both layers)
  watched a REAL hostile's bar walk 3857 -> 2893 -> 2893 -> 771 on a real
  client, driven by exactly this frame pair.  That is the strongest evidence
  this project has for anything in combat, and it is evidence for the SHAPE:
  hit frame announces, actor frame applies.
* What is NOT proven and is not claimed here: that a player's own click can
  reach this driver.  The inbound side is the SCENE-007 EA7D ActionVital the
  client already sends for an action on a target (``action_ack.py``), and no
  attended round has yet shown that shape arriving from a normal attack input
  on a hostile actor.  :func:`attack_from_observed_action` is written against
  that shape because it is the only inbound action shape this project has ever
  parsed, and the ticket that decides whether a real attack input produces it
  is the wiring step below, not a claim of this module.

THE FLOOR, STATED LOUDLY BECAUSE IT IS THE SEAM.  ``HP_FLOOR`` is 1.  A hit
that would take a monster to zero or below lands it at 1 instead, and the
outcome says so in three fields (``clamped_by``, ``at_floor``, ``death_due``)
rather than by silence.  This is not the HYP-PF-038 prohibition being
re-imposed - the owner has approved crossing it to test death - it is the
half-line the COO's own sequencing draws: RE-071 says the client's death gate
is ``HP == 0 && timer <= 0`` -> 0x443990 -> CActorTask_Dead 0x472810, so an HP
of zero without the timer field is a state whose client behaviour nobody in
this project has observed.  The next lane-B round builds that, and it attaches
exactly here: every hit that reaches the floor already carries ``death_due``,
so the death lane's job is to answer the frame, not to re-do the arithmetic.
``field_mobs.hostile_npc_attr`` refuses an HP of zero for the same reason, and
this module would be refused by it even if the floor were removed by accident.

WHAT THE PLAYER SEES THAT THEY DID NOT SEE YESTERDAY.  Nothing yet, and this
paragraph is honest rather than promotional: the module sends nothing, because
the dispatch file that would call it (``runtime.py``) belongs to the chief.
What it delivers is that the wiring is now ONE call - see MOB_COMBAT_WIRING -
instead of a lane to design.  The moment that call exists, hitting a monster in
Port Royal moves that monster's bar, on a build booted with no scenario flag.

NOTHING IS INSTALLED.  No socket, no clock, no randomness, no database, no
global state, no import-time side effect.  Every function is a pure function of
its arguments; every state object is a frozen dataclass; the ledger is carried
as a tuple sorted by identity so its representation is unique.  Contract
breaches raise :class:`MobCombatContractError` with a NAMED reason from
:data:`MOB_COMBAT_REFUSAL_REASONS`, never a bare ValueError and never a silent
coercion.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from . import field_mobs
from .field_mobs import FieldMob
from .population import (
    FULL_MOVEMENT_MASK,
    MOVEMENT_ATTR_ID,
    NPC_ATTR_ID,
    NPC_STYLE_ACTOR_TYPE,
)


# Convention markers only; nothing in this tree branches on them.
production_allowed = True
test_only = False

MOB_COMBAT_MILESTONE = "MOB-COMBAT-001"
MOB_COMBAT_BUILD_ORDER = "BUILD-005 / M4 first half"
MOB_COMBAT_LANE = "B_COMBAT"

# The one line this lane owes the chief, written where a reader of the module
# finds it rather than only in a PR body.
MOB_COMBAT_WIRING = (
    "runtime.py: on an EA7D ActionVital whose target is a field-mob identity, "
    "call mob_combat.attack_from_observed_action(...) and send the two frames "
    "it returns, in order (announce first, bar second)."
)

# ---------------------------------------------------------------------------
# The damage formula.  Copied value-for-value, WITH provenance, from the lanes
# that proved it, because importing a scenario-gated probe into a production
# module is how a flagless build ends up depending on a flag.  Every constant
# below is pinned against its source in tests/test_mob_combat.py.
#   attack  = ATK_BASE + K_ATK_STR * ability_str + K_ATK_LV * level
#   defence = DEF_BASE + K_DEF_CON * ability_con + K_DEF_LV * level
#   damage  = max(MIN_HIT, attack - defence)
# Source: HYP-PF-024 DAMAGE-MODEL-001 (round 83), reused unchanged by HYP-PF-029
# and by HYP-PF-038 HOSTILE-HP-LINK-001, whose ladder GT-035 watched on a
# screen.  The arithmetic is OURS: the original server is unrecoverable and no
# capture in any corpus shows a target's HP moving in either direction.
# ---------------------------------------------------------------------------
ATK_BASE = 100
K_ATK_STR = 7
K_ATK_LV = 3
DEF_BASE = 10
K_DEF_CON = 2
K_DEF_LV = 1
MIN_HIT = 1

# OURS, not a table's: no MOBS column carries a constitution.  The value is the
# one HYP-PF-038 used for this same defender, kept so that the numbers this
# production driver ships are the numbers two observers already watched fall on
# a real screen in GT-035, rather than a second set nobody has seen.
MOB_ABILITY_CON = 22

# The wire, from the same static anchors the probe lanes carry.
CHIT_RESULT_VITAL_ID = 0x16F7
CHIT_RESULT_VITAL_VERSION = 0x00
CHIT_RESULT_HEADER_WIRE_SIZE = 22       # qword performer + 4 reserved fields
HIT_COUNT_WIRE_SIZE = 3
HIT_ELEMENT_WIRE_SIZE = 37              # 9 + 5 + 15 + 5 + 3
TAG_QWORD = 0x32
TAG_U32 = 0x14
TAG_U16 = 0x12
TAG_U8 = 0x0B
HEADER_RESERVED_VALUE = 0
YAW_PINNED = 0.0

# The damage field is READ SIGNED at entry +0x08.  Only negative values have an
# observed meaning; a positive one has never been sent and its meaning is
# unknown, so it is refused rather than guessed.
DAMAGE_WIRE_MIN = -1_000_000
DAMAGE_WIRE_MAX = 0
FLAGS_MISS = 0x0000
FLAGS_HIT = 0x0001
MOB_COMBAT_FLAGS_ALLOWLIST = (FLAGS_MISS, FLAGS_HIT)

# The seam described at the top of this file.
HP_FLOOR = 1

# What this lane does NOT claim.  Written as data so a report cannot quote the
# module without quoting these too.
MOB_COMBAT_NONCLAIMS = (
    "a real attack input has never been observed producing the EA7D "
    "ActionVital this driver reads; the inbound half is unproven",
    "nothing dispatches this module: runtime.py belongs to the chief and the "
    "one wiring line has not been written",
    "death is not delivered: the floor is 1 and RE-071's gate needs the "
    "timer field this lane does not send",
    "the monster's constitution is OURS - no committed table carries one",
    "name colour is not claimed by this lane; RE-067 owns it and is open",
    "the client's draw distance is still unmeasured, so a monster hit from "
    "far away may move a bar nobody can see",
    "threat is only recorded while the mob's aggro phase is idle or aggro: "
    "mob_aggro absorbs damage silently in its return and dead phases, by that "
    "module's declared design, and this driver does not override it",
)

REFUSE_VALUE_NOT_INT = "value_not_int"
REFUSE_VALUE_OUT_OF_RANGE = "value_out_of_range"
REFUSE_POSITION_NOT_FINITE = "position_not_finite"
REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_PERFORMER_IS_THE_TARGET = "performer_is_the_target"
REFUSE_TARGET_NOT_IN_LEDGER = "target_not_in_ledger"
REFUSE_DUPLICATE_LEDGER_IDENTITY = "duplicate_ledger_identity"
REFUSE_BALANCE_ABOVE_MAX = "balance_above_max"
REFUSE_BALANCE_BELOW_FLOOR = "balance_below_floor"
REFUSE_DAMAGE_NOT_POSITIVE = "damage_not_positive"
REFUSE_DAMAGE_WIRE_POSITIVE = "damage_wire_positive"
REFUSE_DAMAGE_WIRE_OUT_OF_RANGE = "damage_wire_out_of_range"
REFUSE_FLAGS_NOT_ALLOWLISTED = "flags_not_allowlisted"
REFUSE_FLAGS_DISAGREE_WITH_DAMAGE = "flags_disagree_with_damage"
REFUSE_AGGRO_HANDLE_INCOMPLETE = "aggro_handle_incomplete"
REFUSE_ACTION_FIELDS_MALFORMED = "action_fields_malformed"
REFUSE_COMPOSED_BYTES_OFF_PIN = "composed_bytes_off_pin"
MOB_COMBAT_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_INT,
    REFUSE_VALUE_OUT_OF_RANGE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_PERFORMER_IS_THE_TARGET,
    REFUSE_TARGET_NOT_IN_LEDGER,
    REFUSE_DUPLICATE_LEDGER_IDENTITY,
    REFUSE_BALANCE_ABOVE_MAX,
    REFUSE_BALANCE_BELOW_FLOOR,
    REFUSE_DAMAGE_NOT_POSITIVE,
    REFUSE_DAMAGE_WIRE_POSITIVE,
    REFUSE_DAMAGE_WIRE_OUT_OF_RANGE,
    REFUSE_FLAGS_NOT_ALLOWLISTED,
    REFUSE_FLAGS_DISAGREE_WITH_DAMAGE,
    REFUSE_AGGRO_HANDLE_INCOMPLETE,
    REFUSE_ACTION_FIELDS_MALFORMED,
    REFUSE_COMPOSED_BYTES_OFF_PIN,
)


class MobCombatContractError(ValueError):
    """A refusal from this module, always carrying a named reason."""

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_COMBAT_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


def _require_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or type(value) is bool:
        raise MobCombatContractError(
            REFUSE_VALUE_NOT_INT, "%s must be a plain int" % label)
    if not minimum <= value <= maximum:
        raise MobCombatContractError(
            REFUSE_VALUE_OUT_OF_RANGE,
            "%s must be within [%d, %d], got %d" % (
                label, minimum, maximum, value),
        )
    return value


def _require_identity(value: Any, label: str) -> int:
    identity = _require_int(value, label, 0, 0xFFFFFFFFFFFFFFFF)
    if identity <= 0:
        raise MobCombatContractError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s must be positive" % label)
    return identity


def _require_position(value: Any) -> tuple[float, float, float]:
    if type(value) is not tuple or len(value) != 3:
        raise MobCombatContractError(
            REFUSE_POSITION_NOT_FINITE, "position must be a 3-tuple")
    out = []
    for component in value:
        if type(component) not in (int, float) or type(component) is bool:
            raise MobCombatContractError(
                REFUSE_POSITION_NOT_FINITE, "position component is not a number")
        as_float = float(component)
        if not math.isfinite(as_float):
            raise MobCombatContractError(
                REFUSE_POSITION_NOT_FINITE, "position component is not finite")
        out.append(as_float)
    return (out[0], out[1], out[2])


@dataclass(frozen=True)
class Combatant:
    """The two ability numbers the formula reads, and the level.

    One record for both sides: the attacker half reads ``level`` and
    ``ability_str``, the defender half reads ``level`` and ``ability_con``.
    Nothing here is invented by this module - the caller supplies the character
    row for the player and the monster row for the mob.
    """

    level: int
    ability_str: int
    ability_con: int

    def __post_init__(self) -> None:
        _require_int(self.level, "level", 1, 1000)
        _require_int(self.ability_str, "ability_str", 0, 100000)
        _require_int(self.ability_con, "ability_con", 0, 100000)

    @property
    def attack(self) -> int:
        return ATK_BASE + K_ATK_STR * self.ability_str + K_ATK_LV * self.level

    @property
    def defence(self) -> int:
        return DEF_BASE + K_DEF_CON * self.ability_con + K_DEF_LV * self.level


@dataclass(frozen=True)
class MobBalance:
    """One monster's live balance: who it is, its ceiling, where it stands."""

    actor_identity: int
    max_hp: int
    current_hp: int

    def __post_init__(self) -> None:
        _require_identity(self.actor_identity, "actor identity")
        _require_int(self.max_hp, "max hp", 1, 0xFFFFFFFF)
        _require_int(self.current_hp, "current hp", 0, 0xFFFFFFFF)
        if self.current_hp > self.max_hp:
            raise MobCombatContractError(
                REFUSE_BALANCE_ABOVE_MAX,
                "current hp %d is above max %d" % (self.current_hp, self.max_hp),
            )
        if self.current_hp < HP_FLOOR:
            raise MobCombatContractError(
                REFUSE_BALANCE_BELOW_FLOOR,
                "current hp %d is below the floor %d this half stops at; the "
                "death half owns everything under it" % (
                    self.current_hp, HP_FLOOR),
            )

    @property
    def at_floor(self) -> bool:
        return self.current_hp == HP_FLOOR

    @property
    def fraction(self) -> float:
        return self.current_hp / self.max_hp


@dataclass(frozen=True)
class CombatLedger:
    """Every monster's balance, as a tuple sorted by identity.

    Sorted-tuple rather than a dict so two ledgers built from the same hits
    compare equal and hash the same in any process, and so no caller can mutate
    a balance behind the driver's back.
    """

    balances: tuple[MobBalance, ...]

    def __post_init__(self) -> None:
        if type(self.balances) is not tuple:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "balances must be a tuple")
        seen = set()
        for balance in self.balances:
            if type(balance) is not MobBalance:
                raise MobCombatContractError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every ledger row must be a typed MobBalance")
            if balance.actor_identity in seen:
                raise MobCombatContractError(
                    REFUSE_DUPLICATE_LEDGER_IDENTITY,
                    "identity 0x%X appears twice" % balance.actor_identity)
            seen.add(balance.actor_identity)
        ordered = tuple(sorted(
            self.balances, key=lambda row: row.actor_identity))
        if ordered != self.balances:
            object.__setattr__(self, "balances", ordered)

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.balances)

    def balance_of(self, actor_identity: int) -> MobBalance:
        wanted = _require_identity(actor_identity, "actor identity")
        for row in self.balances:
            if row.actor_identity == wanted:
                return row
        raise MobCombatContractError(
            REFUSE_TARGET_NOT_IN_LEDGER,
            "identity 0x%X is not a monster this ledger opened" % wanted,
        )

    def with_balance(self, balance: MobBalance) -> "CombatLedger":
        if type(balance) is not MobBalance:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "replacement must be a MobBalance")
        self.balance_of(balance.actor_identity)
        return CombatLedger(tuple(
            balance if row.actor_identity == balance.actor_identity else row
            for row in self.balances
        ))


@dataclass(frozen=True)
class HitOutcome:
    """What one hit did, in numbers a report can print without re-deriving."""

    attacker_identity: int
    target_identity: int
    damage: int
    damage_wire: int
    flags: int
    hp_before: int
    hp_after: int
    max_hp: int
    clamped_by: int
    at_floor: bool
    death_due: bool

    @property
    def applied(self) -> int:
        return self.hp_before - self.hp_after


def mob_defender(mob: FieldMob) -> Combatant:
    """The defender record for a roster monster.

    ``level`` comes from the mined MOBS row.  ``ability_con`` does not come
    from a table at all: no committed table gives a MOBS row a constitution -
    the mined columns are level, rank, the two AI ids, walk speed and the drop
    ids (see ``field_mob_tables``).  :data:`MOB_ABILITY_CON` is therefore OURS,
    and it is not a fresh invention: it is the same 22 the HYP-PF-038 ladder
    used for this exact defender, which is why this production driver
    reproduces the two damage numbers GT-035 watched on a screen
    (``test_the_driver_reproduces_the_ladder_gt035_watched``) instead of
    quietly shipping different ones.  A later round that mines a real defence
    column replaces this function and nothing else.
    """
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    return Combatant(
        level=mob.level, ability_str=0, ability_con=MOB_ABILITY_CON)


def resolve_damage(attacker: Combatant, defender: Combatant) -> int:
    """The frozen formula, floored at :data:`MIN_HIT`.  Positive, always."""
    for who, record in (("attacker", attacker), ("defender", defender)):
        if type(record) is not Combatant:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "%s must be the typed Combatant record" % who)
    return max(MIN_HIT, attacker.attack - defender.defence)


def damage_to_wire(damage: int) -> int:
    """The signed i32 the client prints: negative, and never zero for a hit."""
    value = _require_int(damage, "damage", 1, -DAMAGE_WIRE_MIN)
    return -value


def require_damage_wire(value: Any) -> int:
    wire = _require_int(value, "damage wire", DAMAGE_WIRE_MIN, 0x7FFFFFFF)
    if wire > DAMAGE_WIRE_MAX:
        raise MobCombatContractError(
            REFUSE_DAMAGE_WIRE_POSITIVE,
            "a positive damage number has never been sent and its meaning is "
            "unknown; got %d" % wire,
        )
    if wire < DAMAGE_WIRE_MIN:
        raise MobCombatContractError(
            REFUSE_DAMAGE_WIRE_OUT_OF_RANGE,
            "damage wire %d is outside the proven window" % wire)
    return wire


def require_flags(value: Any) -> int:
    flags = _require_int(value, "flags", 0, 0xFFFF)
    if flags not in MOB_COMBAT_FLAGS_ALLOWLIST:
        raise MobCombatContractError(
            REFUSE_FLAGS_NOT_ALLOWLISTED,
            "flags 0x%04X is outside the two values a hit lane has ever sent"
            % flags,
        )
    return flags


def require_damage_and_flags_agree(damage_wire: int, flags: int) -> None:
    """A miss moves nothing and a hit moves something.  No third case."""
    wire = require_damage_wire(damage_wire)
    value = require_flags(flags)
    if (wire == 0) != (value == FLAGS_MISS):
        raise MobCombatContractError(
            REFUSE_FLAGS_DISAGREE_WITH_DAMAGE,
            "damage %d and flags 0x%04X tell two different stories" % (
                wire, value),
        )


def open_ledger(
    roster: tuple[FieldMob, ...] | None = None,
) -> CombatLedger:
    """Every monster in the roster, standing at its own ceiling."""
    mobs = field_mobs.load_roster() if roster is None else roster
    if type(mobs) is not tuple:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "roster must be a tuple of FieldMob")
    rows = []
    for mob in mobs:
        if type(mob) is not FieldMob:
            raise MobCombatContractError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "roster must be a tuple of FieldMob")
        rows.append(MobBalance(mob.actor_identity, mob.max_hp, mob.max_hp))
    return CombatLedger(tuple(rows))


def apply_hit(
    ledger: CombatLedger,
    attacker_identity: int,
    target_identity: int,
    damage: int,
) -> tuple[CombatLedger, HitOutcome]:
    """Subtract a hit from one monster's balance and say exactly what happened.

    The number announced on the wire is the number subtracted here, including
    when the subtraction is clamped at :data:`HP_FLOOR`: the client prints what
    the server sends and the bar shows what the server sets, so the two halves
    are computed once, together, and never separately.
    """
    if type(ledger) is not CombatLedger:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "ledger must be a typed CombatLedger")
    attacker = _require_identity(attacker_identity, "attacker identity")
    target = _require_identity(target_identity, "target identity")
    if attacker == target:
        raise MobCombatContractError(
            REFUSE_PERFORMER_IS_THE_TARGET,
            "the performer and the target must differ: the client's own "
            "visibility filter at 0x43FEF0 draws nothing otherwise",
        )
    requested = _require_int(damage, "damage", 1, -DAMAGE_WIRE_MIN)
    balance = ledger.balance_of(target)
    room = balance.current_hp - HP_FLOOR
    applied = requested if requested <= room else room
    clamped_by = requested - applied
    if applied == 0:
        # Already at the floor: nothing moves, and the caller is told to stop
        # announcing numbers that do not land.
        outcome = HitOutcome(
            attacker, target, 0, 0, FLAGS_MISS, balance.current_hp,
            balance.current_hp, balance.max_hp, clamped_by, True, True,
        )
        return ledger, outcome
    moved = MobBalance(
        balance.actor_identity, balance.max_hp, balance.current_hp - applied)
    outcome = HitOutcome(
        attacker, target, applied, -applied, FLAGS_HIT,
        balance.current_hp, moved.current_hp, moved.max_hp,
        clamped_by, moved.at_floor, moved.at_floor,
    )
    require_damage_and_flags_agree(outcome.damage_wire, outcome.flags)
    return ledger.with_balance(moved), outcome


def apply_threat(aggro: Any, aggro_state: Any, outcome: HitOutcome) -> Any:
    """Hand the damage to ``mob_aggro.apply_damage_threat``, unchanged.

    ``aggro`` is the module handle, passed in rather than imported: that module
    states that nothing in ``src/`` imports it and that its dispatch
    reachability is False, and both statements stay true this way.

    The number handed over is the WIRE number, which is NEGATIVE.  That is not
    a detail: ``apply_damage_threat`` adds threat only for a negative value,
    because only "took damage" has a recorded meaning, and it returns the state
    UNCHANGED and without complaint for a positive one.  Handing it the
    positive arithmetic value would therefore build a monster that is hit,
    loses HP, repaints its bar and never once decides it has an enemy - a bug
    that no exception would ever announce.  ``test_threat_rises_by_the_damage``
    is the guard on this line.
    """
    if type(outcome) is not HitOutcome:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    apply_damage_threat = getattr(aggro, "apply_damage_threat", None)
    if apply_damage_threat is None or not callable(apply_damage_threat):
        raise MobCombatContractError(
            REFUSE_AGGRO_HANDLE_INCOMPLETE,
            "the aggro handle must expose a callable apply_damage_threat")
    if outcome.damage == 0:
        return aggro_state
    return apply_damage_threat(
        aggro_state, outcome.attacker_identity, outcome.damage_wire)


def encode_hit_entry(
    legacy: Any,
    target_identity: int,
    damage_wire: int,
    position: tuple[float, float, float],
    flags: int,
    *,
    yaw: float = YAW_PINNED,
) -> bytes:
    """One 37-byte hit entry in the proven emission order.

    General where the probe lane is pinned: any target identity, any finite
    position.  The widths, the tag order and the signed damage field are the
    static anchors, and the length check below is what keeps this general form
    honest against them.
    """
    target = _require_identity(target_identity, "target identity")
    wire = require_damage_wire(damage_wire)
    value = require_flags(flags)
    require_damage_and_flags_agree(wire, value)
    x, y, z = _require_position(position)
    if type(yaw) not in (int, float) or type(yaw) is bool or not math.isfinite(
            float(yaw)):
        raise MobCombatContractError(
            REFUSE_POSITION_NOT_FINITE, "yaw must be a finite float")
    out = bytearray()
    out += legacy.qwordtag(TAG_QWORD, target)
    out += legacy.u32tag(TAG_U32, wire & 0xFFFFFFFF)
    for component in (x, y, z):
        out += legacy.f32tag(component)
    out += legacy.f32tag(float(yaw))
    out += legacy.u16tag(TAG_U16, value)
    if len(out) != HIT_ELEMENT_WIRE_SIZE:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "hit entry is %d bytes, the anchor says %d" % (
                len(out), HIT_ELEMENT_WIRE_SIZE),
        )
    return bytes(out)


def encode_chit_result(
    legacy: Any, performer_identity: int, entries: list[bytes],
) -> bytes:
    """The CHitResult payload: the 22-byte header, then the entry array."""
    performer = _require_identity(performer_identity, "performer identity")
    if type(entries) is not list or not entries:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "entries must be a non-empty list")
    header = bytearray()
    header += legacy.qwordtag(TAG_QWORD, performer)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u16tag(TAG_U16, HEADER_RESERVED_VALUE)
    header += legacy.u32tag(TAG_U32, HEADER_RESERVED_VALUE)
    header += legacy.u8tag(TAG_U8, HEADER_RESERVED_VALUE)
    if len(header) != CHIT_RESULT_HEADER_WIRE_SIZE:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "header is %d bytes, the anchor says %d" % (
                len(header), CHIT_RESULT_HEADER_WIRE_SIZE),
        )
    out = bytearray(header)
    out += legacy.u16tag(TAG_U16, len(entries))
    for entry in entries:
        if type(entry) is not bytes or len(entry) != HIT_ELEMENT_WIRE_SIZE:
            raise MobCombatContractError(
                REFUSE_COMPOSED_BYTES_OFF_PIN, "an entry is not 37 bytes")
        out += entry
    expected = (
        CHIT_RESULT_HEADER_WIRE_SIZE + HIT_COUNT_WIRE_SIZE
        + HIT_ELEMENT_WIRE_SIZE * len(entries)
    )
    if len(out) != expected:
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN,
            "payload is %d bytes, the anchor says %d" % (len(out), expected),
        )
    return bytes(out)


def announce_frames(
    legacy: Any,
    performer_identity: int,
    mob: FieldMob,
    outcome: HitOutcome,
) -> tuple[bytes, bytes]:
    """The frame that floats the number over the monster."""
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    if type(outcome) is not HitOutcome:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "outcome must be a typed HitOutcome")
    if mob.actor_identity != outcome.target_identity:
        raise MobCombatContractError(
            REFUSE_TARGET_NOT_IN_LEDGER,
            "the outcome names 0x%X and the mob is 0x%X" % (
                outcome.target_identity, mob.actor_identity),
        )
    entry = encode_hit_entry(
        legacy, outcome.target_identity, outcome.damage_wire,
        (mob.x, mob.y, mob.z), outcome.flags,
    )
    payload = encode_chit_result(legacy, performer_identity, [entry])
    pc, frame = legacy.make_runtime_vitals(
        [(CHIT_RESULT_VITAL_ID, CHIT_RESULT_VITAL_VERSION, payload)])
    if frame != legacy.frame_pc(pc):
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "announce frame drift")
    return pc, frame


def bar_frames(
    legacy: Any,
    mob: FieldMob,
    current_hp: int,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
    with_movement: bool = False,
) -> tuple[bytes, bytes]:
    """The frame that repaints the bar, built from the hostile body itself.

    ``with_movement`` defaults to False, and that default is not a preference:
    it is what GT-035 actually watched.  In the proven ladder only the
    ``TARGET_SPAWN`` step carries the movement attribute; all three
    ``TARGET_HP_AFTER_*`` frames - the ones whose bar movement two observers
    read off a screen - are composed without it.  A refresh that re-sent
    movement would also snap a monster back to its roster row on every hit.
    """
    if type(mob) is not FieldMob:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mob must be the typed FieldMob record")
    hp = _require_int(current_hp, "current hp", HP_FLOOR, mob.max_hp)
    if type(with_movement) is not bool:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "with_movement must be a bool")
    body = field_mobs.hostile_npc_attr(
        legacy, mob, current_hp=hp, faction=faction)
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
    entry = legacy.make_remote_actor_entry(
        NPC_STYLE_ACTOR_TYPE, mob.actor_identity, attrs)
    pc, frame = legacy.make_runtime_remote_actors([entry])
    if frame != legacy.frame_pc(pc):
        raise MobCombatContractError(
            REFUSE_COMPOSED_BYTES_OFF_PIN, "bar frame drift")
    return pc, frame


@dataclass(frozen=True)
class CombatStep:
    """One hit, end to end: the new ledger, the new threat, the two frames."""

    ledger: CombatLedger
    aggro_state: Any
    outcome: HitOutcome
    announce_pc: bytes
    announce_frame: bytes
    bar_pc: bytes
    bar_frame: bytes

    @property
    def frames(self) -> tuple[bytes, bytes]:
        """Announce first, bar second - the order GT-035 watched."""
        return (self.announce_frame, self.bar_frame)


def strike(
    legacy: Any,
    aggro: Any,
    ledger: CombatLedger,
    aggro_state: Any,
    mob: FieldMob,
    attacker_identity: int,
    attacker: Combatant,
    *,
    faction: int = field_mobs.FIELD_MOB_FACTION,
) -> CombatStep:
    """One hit on one monster: arithmetic, ledger, threat and both frames.

    This is the whole first half of M4 in one call, and it is the call the
    wiring line at :data:`MOB_COMBAT_WIRING` makes.  It sends nothing: the
    caller owns dispatch, and owes the frames in the order
    :attr:`CombatStep.frames` returns them.
    """
    damage = resolve_damage(attacker, mob_defender(mob))
    moved_ledger, outcome = apply_hit(
        ledger, attacker_identity, mob.actor_identity, damage)
    moved_state = apply_threat(aggro, aggro_state, outcome)
    announce_pc, announce_frame = announce_frames(
        legacy, attacker_identity, mob, outcome)
    bar_pc, bar_frame = bar_frames(
        legacy, mob, outcome.hp_after, faction=faction)
    return CombatStep(
        moved_ledger, moved_state, outcome,
        announce_pc, announce_frame, bar_pc, bar_frame,
    )


def attack_from_observed_action(
    legacy: Any,
    aggro: Any,
    ledger: CombatLedger,
    aggro_state: Any,
    action_fields: dict,
    attacker_identity: int,
    attacker: Combatant,
    *,
    roster: tuple[FieldMob, ...] | None = None,
    faction: int = field_mobs.FIELD_MOB_FACTION,
) -> CombatStep | None:
    """Drive one hit from an inbound SCENE-007 ActionVital.

    ``action_fields`` is what ``action_ack.parse_scene006_ea7d`` returns: the
    target identity is ``field_qword_20``.  Returns None - not an exception -
    when the target is not a monster this ledger opened, because a player
    actioning a townsperson is an ordinary event and not a contract breach.
    """
    if type(action_fields) is not dict:
        raise MobCombatContractError(
            REFUSE_ACTION_FIELDS_MALFORMED,
            "action fields must be the dict the EA7D parser returns")
    if "field_qword_20" not in action_fields:
        raise MobCombatContractError(
            REFUSE_ACTION_FIELDS_MALFORMED,
            "action fields carry no target identity at field_qword_20")
    target = _require_identity(
        action_fields["field_qword_20"], "target identity")
    mobs = field_mobs.load_roster() if roster is None else roster
    for mob in mobs:
        if mob.actor_identity == target:
            if target not in ledger.identities():
                return None
            return strike(
                legacy, aggro, ledger, aggro_state, mob,
                attacker_identity, attacker, faction=faction,
            )
    return None


def describe_step(step: CombatStep) -> tuple[str, ...]:
    """Console lines for a hit, in the shape the runtime console prints."""
    if type(step) is not CombatStep:
        raise MobCombatContractError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed CombatStep")
    outcome = step.outcome
    lines = [
        "MOB-COMBAT-001 hit: performer 0x%X -> target 0x%X" % (
            outcome.attacker_identity, outcome.target_identity),
        "  damage announced %d, applied %d, hp %d -> %d of %d (%.1f%%)" % (
            outcome.damage_wire, outcome.applied, outcome.hp_before,
            outcome.hp_after, outcome.max_hp,
            100.0 * outcome.hp_after / outcome.max_hp),
        "  frames: announce %d bytes, bar %d bytes" % (
            len(step.announce_frame), len(step.bar_frame)),
    ]
    if outcome.clamped_by:
        lines.append(
            "  clamped by %d at the floor %d: the death half owns what is "
            "under it (RE-071)" % (outcome.clamped_by, HP_FLOOR))
    if outcome.death_due:
        lines.append(
            "  death due: this monster is at the floor and the next hit has "
            "nowhere to go until the death lane lands")
    return tuple(lines)


PIN_ID = "mob_combat_first_half_001"
PIN_BUILD_ORDER = MOB_COMBAT_BUILD_ORDER
PIN_LANE = MOB_COMBAT_LANE

# The pinned attacker is the HYP-PF-038 "MOB_WEAK" profile, on purpose: fed to
# this general driver against placement 30 it must reproduce -964, the first
# rung of the ladder two observers watched land on a real screen in GT-035.  A
# pin whose numbers nobody has ever seen would prove only that the code agrees
# with itself.
PIN_PLACEMENT_INDEX = field_mobs.CONTROL_PLACEMENT_INDEX
PIN_ATTACKER_LEVEL = 7
PIN_ATTACKER_ABILITY_STR = 132


def pin_attacker() -> Combatant:
    return Combatant(
        level=PIN_ATTACKER_LEVEL,
        ability_str=PIN_ATTACKER_ABILITY_STR,
        ability_con=0,
    )


def pin_document(
    legacy: Any, mob: FieldMob, attacker: Combatant | None = None,
) -> dict:
    """The numbers a report should quote, computed rather than transcribed."""
    if attacker is None:
        attacker = pin_attacker()
    ledger = open_ledger()
    step = strike(
        legacy, _NoThreat(), ledger, None, mob, 0x750059, attacker)
    outcome = step.outcome
    return {
        "pin_id": PIN_ID,
        "build_order": PIN_BUILD_ORDER,
        "lane": PIN_LANE,
        "milestone": MOB_COMBAT_MILESTONE,
        "production_allowed": production_allowed,
        "test_only": test_only,
        "target_identity": mob.actor_identity,
        "target_name": mob.display_name,
        "target_level": mob.level,
        "attacker_level": attacker.level,
        "attacker_ability_str": attacker.ability_str,
        "attacker_attack": attacker.attack,
        "target_defence": mob_defender(mob).defence,
        "max_hp": outcome.max_hp,
        "damage": outcome.damage,
        "damage_wire": outcome.damage_wire,
        "hp_after": outcome.hp_after,
        "fraction_after": outcome.hp_after / outcome.max_hp,
        "announce_frame_bytes": len(step.announce_frame),
        "bar_frame_bytes": len(step.bar_frame),
        "hp_floor": HP_FLOOR,
        "wiring": MOB_COMBAT_WIRING,
        "selection": "none_default_behaviour_no_scenario_flag",
        "nonclaims": list(MOB_COMBAT_NONCLAIMS),
    }


class _NoThreat:
    """The threat sink :func:`pin_document` uses so a pin needs no aggro state.

    It satisfies the handle contract and returns the state it was given, which
    is what "this pin measures the damage half only" means in code.
    """

    @staticmethod
    def apply_damage_threat(state: Any, attacker_identity: int, damage: int):
        return state
