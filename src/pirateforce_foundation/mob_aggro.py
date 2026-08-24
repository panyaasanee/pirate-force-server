"""MOB-AGGRO-001: the server-side mob threat table and decision tick, pure logic.

WHY THIS MODULE EXISTS -- section 5 of the round-98 design, and only that
--------------------------------------------------------------------------
``drafts/MOB_AGGRO_SERVER_AI_STATIC_AND_DESIGN_R98_20260820.md`` (round 98)
mapped every client part a mob-AI lane must drive and concluded:

    "Because the client's own combat FSM is unreachable for projected NPCs,
     all aggro intelligence must live on our server ... each hostile placement
     gets a lightweight per-NPC AI record -- faction, aggro_radius, a threat
     map keyed by player identity, attack_range, attack_cadence, leash_origin.
     A tick loop selects the highest-threat player in range and drives a
     state: Idle -> Aggro(face+approach) -> Attack(cadence) -> Dead/Leash."

That record and that tick loop are this module, and nothing else.  Three
DELIBERATE divergences from the quoted sentence, so nobody reads the quote as
the implementation: (1) ``faction`` is NOT a field here -- it belongs to the
HYP-PF-027 hostility lane, not to the decision loop; (2) target SELECTION has
no range bound of its own -- an acquired attacker is kept however far they
run, and the spatial bound on the chase is the LEASH (the mob, not the
target, breaking the leash radius ends the pursuit); (3) there is no separate
Attack state -- attack is an intent produced inside the aggro phase when the
cadence and the range allow, so the state graph here is
Idle -> Aggro -> Return/Dead.

The round-98 draft ranked the three doors an aggro loop needs on the client:

* Door A -- HOSTILITY: built elsewhere (SCENE-005 faction semantics; the
  opt-in HYP-PF-027 lane carries the hostility frame), with one attended
  refinement measured AFTER the round-98 draft: GT-043 showed the red
  outline / target panel surfaces only after a client-side Tab-select, not
  from the hostility frame alone.  This module does not re-implement any of
  it and must not be read as claiming the frame alone paints the client red.
* Door B -- ATTACK / ACTION: located in the binary but NEVER opened -- zero
  captures, zero server encoders, every observed behavior lookup returned
  null, and inbound ActionVital is proven inert (SCENE-008/-013).  Because of
  that, the attack decision this module emits is named
  ``INTENT_ATTACK_UNDELIVERABLE`` and :data:`ATTACK_INTENT_DELIVERABLE` is
  ``False``: the server can DECIDE to attack, and today that decision has no
  proven server->client transport.  No emitter for it exists in this module or
  anywhere in ``src/``.
* Door C -- HIT LANDS: the damage numbers and the death window are attended-
  proven (HYP-PF-024 / GT-024, and GT-019); the damage->death LINK
  (HYP-PF-026) is proven at the wire/dispatcher layer HEADLESSLY, its client
  layer being a separate attended question.  This module emits no frame for
  any of it; it only ACCEPTS damage numbers (signed i32, the DAMAGE-MODEL-001
  scope) as threat input through :func:`apply_damage_threat`.

WHAT THIS MODULE IS NOT
-----------------------
PURE SERVER LOGIC.  It sends nothing on the wire, opens no socket, touches no
database, boots no server, imports nothing from the runtime/dispatch layer,
and has NO SCENARIO FLAG.  It is deliberately NOT reachable from production
dispatch: no module in ``src/`` imports it, ``production_allowed`` is False,
and ``MOB_AGGRO_DISPATCH_REACHABLE`` is False.  That is the honest state of
the mob-AI line: the decision loop is computable today, the attack delivery is
not (Door B), and wiring the deliverable intents (approach, leash return) to
real frames is a separate, owner-ruled step.  Importing this module has no
side effects: it reads no file and touches no global state at import time.

DETERMINISM (the point of this checkpoint)
------------------------------------------
There is NO randomness anywhere in this module -- not even an injected rng.
Every decision is a pure function of (profile, state, observation):

* the threat table is carried as a tuple of ``(identity, threat)`` pairs
  sorted by identity, so its representation is unique and hash-seed
  independent;
* target selection is "highest threat wins, ties broken by LOWEST identity",
  re-evaluated every tick -- a player who deals more damage pulls aggro;
* distances are full 3D, compared as squared distances against squared radii
  with INCLUSIVE boundaries (``dist_sq <= radius * radius`` is inside), so no
  square root is ever taken and the boundary can be tested exactly;
* the attack cadence is counted in TICKS, not seconds; this module never reads
  a clock.  The counter is clamped at the cadence value so state stays
  bounded.

Same profile + same state + same observation produce the identical TickResult
in any process, every time.  All state objects are frozen dataclasses; no
input is ever mutated.

FAIL CLOSED, AND NEVER SILENTLY
-------------------------------
Inputs that break the contract raise :class:`MobAiContractError` carrying a
NAMED reason from :data:`MOB_AGGRO_REFUSAL_REASONS` -- never a bare
``ValueError`` and never a silent coercion: a non-numeric or non-finite value
(a string radius, a bool range), a non-positive identity, a damage outside
signed 32-bit range, a non-int hp, a non-bool alive flag, a duplicate player
identity in one observation, an unknown phase or malformed threat table in a
rehydrated state, a cadence below one, and radii that contradict each other
(leash smaller than aggro, home outside leash) are each refused by name.
Within-contract inputs never raise: :func:`tick` is total on well-formed
observations, and every decision is visible in the returned intent and state.
Two deliberate no-ops are declared rather than silent: a NON-NEGATIVE damage
value adds no threat (only the negative case has a recorded meaning), and
damage folded while RETURNING or DEAD adds no threat (those phases keep an
empty table by invariant).

[OUR DESIGN] -- WHOSE NUMBERS AND RULES THESE ARE
-------------------------------------------------
Every rule above is OURS.  The original Pirate Force server is closed, was
never published, and left no capture of a monster deciding to attack; there is
nothing to recover a threat formula FROM (the same measurement that grounds
DAMAGE-MODEL-001: the client computes nothing).  This module therefore chooses
its own rules and says so; :data:`MOB_AGGRO_CHOSEN_READINGS` names each one so
a test can pin them.  Balance values carry NO defaults: aggro radius, leash
radius, home radius, attack range and cadence are all caller-supplied through
:class:`MobAiProfile`, because this project has not established the world
coordinate scale and refuses to invent one silently.

THE DRIVER CONTRACT THIS MODULE ASSUMES (unbuilt, so written down)
------------------------------------------------------------------
Every guarantee above is conditional on the not-yet-written tick driver
honoring four obligations, enforced here where a pure function can and named
here where it cannot:

* observations carry each player identity at most once (ENFORCED: a
  duplicate is refused by name at construction);
* only damage numbers whose meaning is recorded reach the threat table
  (ENFORCED: non-negative values add nothing, by declared design);
* the visible-player set is flicker-free at the driver's timescale -- one
  tick of visibility dropout erases that player's threat row permanently,
  because forgiveness is deliberate and immediate (NOT enforceable here;
  a driver with flickering interest management gets amnesiac mobs);
* a tick has no defined wall-clock duration -- cadence is meaningful only
  relative to whatever period the driver chooses (NOT enforceable here).

NONCLAIMS
---------
* No original-server behaviour is claimed anywhere.  The original threat
  rules, aggro radii and attack cadences are unrecoverable forever.
* Nothing here has ever touched a wire, a client, or a database.  No coverage
  grade moves; ``mob_aggro_and_server_ai`` stays ``not_started`` until a real
  client is watched reacting to a frame we sent (the round-98 rule).
* ``INTENT_ATTACK_UNDELIVERABLE`` is a decision, not a capability: Door B is
  unproven and no attack frame exists.  No claim is made that an NPC can be
  made to attack today.
* Revival is not modeled: ``PHASE_DEAD`` is absorbing.  Whether the original
  game revived mobs in place or respawned fresh placements is [UNKNOWN].
* The world coordinate scale is [UNKNOWN]; every radius in a profile is a
  caller-chosen number in placement units, not a claim about the game world.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional, Tuple


# This lane is not wired to anything and must not become wired by accident.
production_allowed = False
MOB_AGGRO_MILESTONE = "MOB-AGGRO-001"
MOB_AGGRO_DISPATCH_REACHABLE = False

# Door B (attack transport) is unproven -- round-98 draft, sections 2 and 8.
ATTACK_INTENT_DELIVERABLE = False

# Threat is a saturating signed-31-bit-positive count, sized to accept the
# DAMAGE-MODEL-001 scope of one signed i32 per target.
THREAT_MAX = 2 ** 31 - 1
DAMAGE_I32_MIN = -(2 ** 31)
DAMAGE_I32_MAX = 2 ** 31 - 1

# [OUR DESIGN] a player who merely steps inside the aggro radius is floored to
# this much threat -- enough to be targetable, and never accumulating by
# proximity alone.
PROXIMITY_THREAT = 1

PHASE_IDLE = "idle"
PHASE_AGGRO = "aggro"
PHASE_RETURN = "return"
PHASE_DEAD = "dead"
MOB_AGGRO_PHASES = (PHASE_IDLE, PHASE_AGGRO, PHASE_RETURN, PHASE_DEAD)

INTENT_NONE = "none"
INTENT_FACE_AND_APPROACH = "face_and_approach"
INTENT_ATTACK_UNDELIVERABLE = "attack_undeliverable"
INTENT_RETURN_TO_LEASH = "return_to_leash"
MOB_AGGRO_INTENTS = (
    INTENT_NONE,
    INTENT_FACE_AND_APPROACH,
    INTENT_ATTACK_UNDELIVERABLE,
    INTENT_RETURN_TO_LEASH,
)

# Named refusals: every contract violation raises with exactly one of these.
REFUSE_VALUE_NOT_NUMERIC = "value_not_numeric"
REFUSE_PROFILE_VALUE_NOT_FINITE = "profile_value_not_finite"
REFUSE_PROFILE_RADIUS_NOT_POSITIVE = "profile_radius_not_positive"
REFUSE_PROFILE_LEASH_SMALLER_THAN_AGGRO = "profile_leash_smaller_than_aggro"
REFUSE_PROFILE_HOME_OUTSIDE_LEASH = "profile_home_outside_leash"
REFUSE_PROFILE_ATTACK_RANGE_OUTSIDE_AGGRO = "profile_attack_range_outside_aggro"
REFUSE_PROFILE_CADENCE_NOT_POSITIVE = "profile_cadence_not_positive"
REFUSE_POSITION_NOT_FINITE = "position_not_finite"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_DAMAGE_OUTSIDE_I32 = "damage_outside_i32"
REFUSE_HP_NOT_INT = "hp_not_int"
REFUSE_ALIVE_NOT_BOOL = "alive_not_bool"
REFUSE_DUPLICATE_PLAYER_IDENTITY = "duplicate_player_identity"
REFUSE_PHASE_UNKNOWN = "phase_unknown"
REFUSE_STATE_MALFORMED = "state_malformed"
MOB_AGGRO_REFUSAL_REASONS = (
    REFUSE_VALUE_NOT_NUMERIC,
    REFUSE_PROFILE_VALUE_NOT_FINITE,
    REFUSE_PROFILE_RADIUS_NOT_POSITIVE,
    REFUSE_PROFILE_LEASH_SMALLER_THAN_AGGRO,
    REFUSE_PROFILE_HOME_OUTSIDE_LEASH,
    REFUSE_PROFILE_ATTACK_RANGE_OUTSIDE_AGGRO,
    REFUSE_PROFILE_CADENCE_NOT_POSITIVE,
    REFUSE_POSITION_NOT_FINITE,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_DAMAGE_OUTSIDE_I32,
    REFUSE_HP_NOT_INT,
    REFUSE_ALIVE_NOT_BOOL,
    REFUSE_DUPLICATE_PLAYER_IDENTITY,
    REFUSE_PHASE_UNKNOWN,
    REFUSE_STATE_MALFORMED,
)

# [OUR DESIGN] each rule this module chose, named so a test can pin them and a
# reader can see at a glance which behaviours are inventions of ours.
MOB_AGGRO_CHOSEN_READINGS = (
    "threat_is_abs_damage_saturating_at_i32_max",
    "nonnegative_damage_including_miss_adds_no_threat_meaning_unknown",
    "return_and_dead_phases_absorb_no_damage_threat",
    "proximity_inside_aggro_radius_floors_threat_to_one",
    "selection_reevaluated_every_tick_highest_threat_wins",
    "ties_broken_by_lowest_identity",
    "acquired_attacker_kept_outside_aggro_radius_until_leash_or_forgiveness",
    "absent_or_dead_player_forgiven_at_tick_start",
    "leash_break_clears_all_threat_and_returns",
    "return_completes_inside_home_radius_and_yields_idle_that_tick",
    "attack_cadence_counts_ticks_and_fires_only_inside_attack_range",
    "distances_are_3d_with_inclusive_boundaries",
    "phase_dead_is_absorbing_revival_not_modeled",
)


class MobAiContractError(ValueError):
    """A named contract refusal; ``reason`` is one of MOB_AGGRO_REFUSAL_REASONS."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


def _require_number(value, what: str) -> float:
    """int or float only -- a string or a bool is refused BY NAME, never coerced."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MobAiContractError(
            REFUSE_VALUE_NOT_NUMERIC, "%s=%r" % (what, value))
    return float(value)


def _require_finite_triple(value: Tuple[float, float, float], what: str,
                           reason: str) -> Tuple[float, float, float]:
    if len(value) != 3:
        raise MobAiContractError(reason, "%s must have 3 components" % what)
    out = []
    for component in value:
        number = _require_number(component, what)
        if not math.isfinite(number):
            raise MobAiContractError(reason, "%s component %r" % (what, component))
        out.append(number)
    return (out[0], out[1], out[2])


@dataclass(frozen=True)
class MobAiProfile:
    """[OUR DESIGN] the per-NPC balance record.  All values caller-supplied.

    ``aggro_radius``: a live player inside it gains the proximity threat floor.
    ``leash_radius``: the mob farther than this from its leash origin breaks
    off, forgets all threat and returns.  ``home_radius``: the return phase
    completes once the mob is back inside this distance of the origin.
    ``attack_range``: the attack decision fires only with the target inside
    it.  ``attack_cadence_ticks``: the attack PERIOD -- at most one attack
    decision per this many ticks (1 means every tick may attack).
    """

    aggro_radius: float
    leash_radius: float
    home_radius: float
    attack_range: float
    attack_cadence_ticks: int

    def __post_init__(self) -> None:
        for name in ("aggro_radius", "leash_radius", "home_radius",
                     "attack_range"):
            raw = getattr(self, name)
            number = _require_number(raw, name)
            if not math.isfinite(number):
                raise MobAiContractError(
                    REFUSE_PROFILE_VALUE_NOT_FINITE, "%s=%r" % (name, raw))
            if number <= 0.0:
                raise MobAiContractError(
                    REFUSE_PROFILE_RADIUS_NOT_POSITIVE, "%s=%r" % (name, raw))
            object.__setattr__(self, name, number)
        if not isinstance(self.attack_cadence_ticks, int) or isinstance(
                self.attack_cadence_ticks, bool):
            raise MobAiContractError(
                REFUSE_PROFILE_CADENCE_NOT_POSITIVE,
                "attack_cadence_ticks=%r" % (self.attack_cadence_ticks,))
        if self.attack_cadence_ticks < 1:
            raise MobAiContractError(
                REFUSE_PROFILE_CADENCE_NOT_POSITIVE,
                "attack_cadence_ticks=%r" % (self.attack_cadence_ticks,))
        if self.leash_radius < self.aggro_radius:
            raise MobAiContractError(
                REFUSE_PROFILE_LEASH_SMALLER_THAN_AGGRO,
                "leash_radius=%r aggro_radius=%r"
                % (self.leash_radius, self.aggro_radius))
        if self.home_radius > self.leash_radius:
            raise MobAiContractError(
                REFUSE_PROFILE_HOME_OUTSIDE_LEASH,
                "home_radius=%r leash_radius=%r"
                % (self.home_radius, self.leash_radius))
        if self.attack_range > self.aggro_radius:
            raise MobAiContractError(
                REFUSE_PROFILE_ATTACK_RANGE_OUTSIDE_AGGRO,
                "attack_range=%r aggro_radius=%r"
                % (self.attack_range, self.aggro_radius))


@dataclass(frozen=True)
class PlayerObservation:
    """One player as the caller sees it this tick."""

    identity: int
    position: Tuple[float, float, float]
    alive: bool

    def __post_init__(self) -> None:
        if not isinstance(self.identity, int) or isinstance(self.identity, bool) \
                or self.identity <= 0:
            raise MobAiContractError(
                REFUSE_IDENTITY_NOT_POSITIVE,
                "player identity=%r" % (self.identity,))
        object.__setattr__(
            self, "position",
            _require_finite_triple(self.position, "player position",
                                   REFUSE_POSITION_NOT_FINITE))
        if not isinstance(self.alive, bool):
            raise MobAiContractError(
                REFUSE_ALIVE_NOT_BOOL, "alive=%r" % (self.alive,))


@dataclass(frozen=True)
class MobObservation:
    """The mob and the visible players, as the caller sees them this tick."""

    position: Tuple[float, float, float]
    hp: int
    players: Tuple[PlayerObservation, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "position",
            _require_finite_triple(self.position, "mob position",
                                   REFUSE_POSITION_NOT_FINITE))
        if isinstance(self.hp, bool) or not isinstance(self.hp, int):
            raise MobAiContractError(REFUSE_HP_NOT_INT, "hp=%r" % (self.hp,))
        players = tuple(self.players)
        seen = set()
        for player in players:
            if player.identity in seen:
                raise MobAiContractError(
                    REFUSE_DUPLICATE_PLAYER_IDENTITY,
                    "identity=%d appears twice" % player.identity)
            seen.add(player.identity)
        object.__setattr__(self, "players", players)


@dataclass(frozen=True)
class MobAiState:
    """The whole per-mob AI memory.  Threat is sorted pairs, unique per state.

    Validated on construction so a driver that rehydrates state from storage
    gets the same contract protection as one that only ever holds states this
    module produced.
    """

    phase: str
    leash_origin: Tuple[float, float, float]
    threat: Tuple[Tuple[int, int], ...]
    target_identity: Optional[int]
    ticks_since_attack: int

    def __post_init__(self) -> None:
        if self.phase not in MOB_AGGRO_PHASES:
            raise MobAiContractError(
                REFUSE_PHASE_UNKNOWN, "phase=%r" % (self.phase,))
        object.__setattr__(
            self, "leash_origin",
            _require_finite_triple(self.leash_origin, "leash origin",
                                   REFUSE_POSITION_NOT_FINITE))
        rows = tuple(self.threat)
        previous_identity = 0
        for row in rows:
            if len(row) != 2:
                raise MobAiContractError(
                    REFUSE_STATE_MALFORMED, "threat row %r" % (row,))
            identity, value = row
            if isinstance(identity, bool) or not isinstance(identity, int) \
                    or identity <= previous_identity:
                raise MobAiContractError(
                    REFUSE_STATE_MALFORMED,
                    "threat identities must be positive ints, strictly "
                    "ascending; got %r" % (row,))
            if isinstance(value, bool) or not isinstance(value, int) \
                    or value < 1 or value > THREAT_MAX:
                raise MobAiContractError(
                    REFUSE_STATE_MALFORMED,
                    "threat value must be an int in [1, THREAT_MAX]; got %r"
                    % (row,))
            previous_identity = identity
        object.__setattr__(self, "threat", rows)
        if self.target_identity is not None and (
                isinstance(self.target_identity, bool)
                or not isinstance(self.target_identity, int)
                or self.target_identity <= 0):
            raise MobAiContractError(
                REFUSE_STATE_MALFORMED,
                "target_identity=%r" % (self.target_identity,))
        if isinstance(self.ticks_since_attack, bool) \
                or not isinstance(self.ticks_since_attack, int) \
                or self.ticks_since_attack < 0:
            raise MobAiContractError(
                REFUSE_STATE_MALFORMED,
                "ticks_since_attack=%r" % (self.ticks_since_attack,))


@dataclass(frozen=True)
class MobAiIntent:
    """What the server WOULD express as frames.  This module ships no emitter."""

    kind: str
    target_identity: Optional[int]


@dataclass(frozen=True)
class TickResult:
    state: MobAiState
    intent: MobAiIntent


def initial_state(leash_origin: Tuple[float, float, float]) -> MobAiState:
    """A fresh idle mob anchored to its leash origin."""
    origin = _require_finite_triple(leash_origin, "leash origin",
                                    REFUSE_POSITION_NOT_FINITE)
    return MobAiState(
        phase=PHASE_IDLE,
        leash_origin=origin,
        threat=(),
        target_identity=None,
        ticks_since_attack=0,
    )


def apply_damage_threat(state: MobAiState, attacker_identity: int,
                        damage: int) -> MobAiState:
    """Fold one DAMAGE-MODEL-001 number into threat: abs(), saturating.

    Only NEGATIVE damage adds threat, because only the negative case has a
    recorded meaning ("took damage"); what a non-negative value means -- heal,
    absorb, no-op, MISS at 0 -- is UNKNOWN per the damage model's own record,
    so a non-negative value adds nothing, by declared design rather than by
    accident.  A dead mob absorbs nothing, and so does a RETURNING mob: the
    leash break already forgave everything, and a returning mob re-engages
    only by the next proximity acquisition -- so this function keeps the
    invariant that RETURN and DEAD states always carry an empty table.
    """
    if not isinstance(attacker_identity, int) or isinstance(
            attacker_identity, bool) or attacker_identity <= 0:
        raise MobAiContractError(
            REFUSE_IDENTITY_NOT_POSITIVE,
            "attacker identity=%r" % (attacker_identity,))
    if not isinstance(damage, int) or isinstance(damage, bool) \
            or damage < DAMAGE_I32_MIN or damage > DAMAGE_I32_MAX:
        raise MobAiContractError(
            REFUSE_DAMAGE_OUTSIDE_I32, "damage=%r" % (damage,))
    if state.phase in (PHASE_DEAD, PHASE_RETURN) or damage >= 0:
        return state
    added = abs(damage)
    table = dict(state.threat)
    table[attacker_identity] = min(
        THREAT_MAX, table.get(attacker_identity, 0) + added)
    return MobAiState(
        phase=state.phase,
        leash_origin=state.leash_origin,
        threat=_freeze_threat(table),
        target_identity=state.target_identity,
        ticks_since_attack=state.ticks_since_attack,
    )


def tick(profile: MobAiProfile, state: MobAiState,
         observation: MobObservation) -> TickResult:
    """One decision step.  Pure; never raises on well-formed inputs."""
    if state.phase == PHASE_DEAD:
        return TickResult(state, MobAiIntent(INTENT_NONE, None))

    if observation.hp <= 0:
        dead = MobAiState(
            phase=PHASE_DEAD,
            leash_origin=state.leash_origin,
            threat=(),
            target_identity=None,
            ticks_since_attack=0,
        )
        return TickResult(dead, MobAiIntent(INTENT_NONE, None))

    # Forgiveness: threat rows for players that are absent or dead this tick
    # are dropped before anything else looks at the table.
    visible_alive = {
        player.identity: player
        for player in observation.players if player.alive
    }
    table = {
        identity: threat
        for identity, threat in state.threat if identity in visible_alive
    }

    # Leash: too far from the origin means break off, forget, and go home.
    if not _within(observation.position, state.leash_origin,
                   profile.leash_radius):
        returning = MobAiState(
            phase=PHASE_RETURN,
            leash_origin=state.leash_origin,
            threat=(),
            target_identity=None,
            ticks_since_attack=0,
        )
        return TickResult(returning, MobAiIntent(INTENT_RETURN_TO_LEASH, None))

    if state.phase == PHASE_RETURN:
        if _within(observation.position, state.leash_origin,
                   profile.home_radius):
            home = MobAiState(
                phase=PHASE_IDLE,
                leash_origin=state.leash_origin,
                threat=(),
                target_identity=None,
                ticks_since_attack=0,
            )
            return TickResult(home, MobAiIntent(INTENT_NONE, None))
        still_returning = MobAiState(
            phase=PHASE_RETURN,
            leash_origin=state.leash_origin,
            threat=(),
            target_identity=None,
            ticks_since_attack=0,
        )
        return TickResult(still_returning,
                          MobAiIntent(INTENT_RETURN_TO_LEASH, None))

    # Proximity floor: a live player inside the aggro radius becomes
    # targetable at PROXIMITY_THREAT; the floor never accumulates.
    for identity, player in visible_alive.items():
        if _within(player.position, observation.position,
                   profile.aggro_radius):
            table[identity] = max(table.get(identity, 0), PROXIMITY_THREAT)

    target_identity = _select_target(table)
    if target_identity is None:
        idle = MobAiState(
            phase=PHASE_IDLE,
            leash_origin=state.leash_origin,
            threat=(),
            target_identity=None,
            ticks_since_attack=0,
        )
        return TickResult(idle, MobAiIntent(INTENT_NONE, None))

    # Cadence counts ticks spent in aggro, clamped so state stays bounded.
    counter = min(profile.attack_cadence_ticks, state.ticks_since_attack + 1)
    target = visible_alive[target_identity]
    in_attack_range = _within(target.position, observation.position,
                              profile.attack_range)
    if in_attack_range and counter >= profile.attack_cadence_ticks:
        intent = MobAiIntent(INTENT_ATTACK_UNDELIVERABLE, target_identity)
        counter = 0
    elif in_attack_range:
        intent = MobAiIntent(INTENT_NONE, target_identity)
    else:
        intent = MobAiIntent(INTENT_FACE_AND_APPROACH, target_identity)

    aggro = MobAiState(
        phase=PHASE_AGGRO,
        leash_origin=state.leash_origin,
        threat=_freeze_threat(table),
        target_identity=target_identity,
        ticks_since_attack=counter,
    )
    return TickResult(aggro, intent)


def describe_mob_ai(result: TickResult) -> Tuple[str, ...]:
    """ASCII lines for logs and console -- cp874-safe by construction."""
    state = result.state
    intent = result.intent
    lines = [
        "mob_aggro|%s|phase=%s|target=%s|cadence=%d|intent=%s|intent_target=%s"
        % (
            MOB_AGGRO_MILESTONE,
            state.phase,
            "-" if state.target_identity is None else str(state.target_identity),
            state.ticks_since_attack,
            intent.kind,
            "-" if intent.target_identity is None else str(intent.target_identity),
        )
    ]
    for identity, threat in state.threat:
        lines.append("threat|identity=%d|value=%d" % (identity, threat))
    return tuple(lines)


def _freeze_threat(table: dict) -> Tuple[Tuple[int, int], ...]:
    return tuple(sorted(table.items()))


def _select_target(table: dict) -> Optional[int]:
    best = None
    for identity in sorted(table):
        threat = table[identity]
        if threat <= 0:
            continue
        if best is None or threat > table[best]:
            best = identity
    return best


def _within(point: Tuple[float, float, float],
            center: Tuple[float, float, float], radius: float) -> bool:
    dx = point[0] - center[0]
    dy = point[1] - center[1]
    dz = point[2] - center[2]
    return dx * dx + dy * dy + dz * dz <= radius * radius
