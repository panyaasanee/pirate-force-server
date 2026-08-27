"""LANE-B / MOB-AGGRO-001: the ONE controller the threat table and the death
gate share, and the join that gives a monster's profile real numbers.

WHY THIS MODULE EXISTS, IN THE COO'S OWN WORDS.  COO-DECISION
2026-08-26T04:02+07:00 answered the damage lane's question about the threat
handle with two rulings this module is the whole of:

    section 1.3 -- "(a) accepted, but it lands in the M4 SECOND HALF, not in
    some floating 'next round': raise mob_aggro to production together with the
    death driver, because the death gate (RE-071: the timer must be <= 0 too)
    and threat use THE SAME CONTROLLER.  Doing them apart means writing the
    controller twice.  (b) REFUSED -- two sets of threat logic will drift from
    each other for certain, and that kind of drift surfaces when there are two
    real players, not during a test."

    section 2 -- "a lane whose production_allowed is false, reached from
    production through an argument no scan can see, is the hole that makes our
    word 'flagless' meaningless -- so pass None for now, and RAISE THE WHOLE
    MODULE where the scan can see it."

So: one controller, one register, one compare-and-swap, and an IMPORT of
``mob_aggro`` by name rather than a handle argument.  ``mob_aggro`` is
``production_allowed = True`` as of the same commit.  Nothing here is gated by
a scenario id, a flag, an unlock object or a kwarg; a version the owner boots
with no arguments can reach every function in this file.

WHAT IS ONE CONTROLLER AND WHAT IS STILL TWO.  This module owns the AI STATE of
every monster -- phase, threat table, current target -- in a
:class:`MobAiRegister` with a generation and a compare-and-swap, the same shape
``mob_combat.CombatLedger`` and ``mob_death.DeathRegister`` already use.  It
does NOT own HP (that is the combat ledger) and it does NOT own who is a corpse
(that is the death register).  Three registers, one per question, and this one
is the only one that answers "who is this monster angry at".  The COO's ruling
was about the AI state having ONE owner, and it does.

WHAT THIS MODULE DOES *NOT* SHARE WITH THE DEATH GATE, said plainly because an
adversarial review was right that the first draft of this header let a string
constant do the work of a mechanism.  The RE-071 death gate proper -- HP at zero
AND the death timer at or below zero -- lives entirely in ``mob_death``, and
this module never consults it: :func:`death_step` reads only the combat lane's
``HitOutcome``, whose ``death_due`` is the HP half alone.  What is shared is the
AI STATE, which has one owner here and no second copy anywhere.  What is
RECONCILED, not shared, is the two registers' agreement about who is a corpse,
and :func:`reconcile` is the function that does it.

THE ORDER THE DRIVER MUST USE, AND WHY IT IS NOT NEGOTIABLE.  A kill is two
facts in this module's world -- the monster stops holding threat, and its phase
becomes absorbing -- and they must land AFTER the combat commit and AFTER the
death commit, never before:

    1. mob_combat.commit_step   -- HP moved, or REFUSE_LEDGER_STALE
    2. mob_ai_control.damage_step + commit_step  -- threat folded
    3. if step.death_due: mob_death.kill + commit_death   -- the corpse
    4. mob_ai_control.death_step + commit_step   -- the phase goes absorbing

Step 4 before step 3 leaves a monster whose AI says DEAD while the death
register says alive, and the next tick then reports "no intent" for a monster
that is still standing.  Step 2 before step 1 records threat for a subtraction
that a stale ledger refused.  :func:`death_step` refuses an outcome that is not
a kill by name, for the reason ``mob_death.kill`` gives for its own refusal: a
lane that can retire a monster the arithmetic did not kill can retire one at
full HP.

WHERE THE PROFILE NUMBERS COME FROM -- TWO MINED, THREE OURS
------------------------------------------------------------
``mob_aggro.MobAiProfile`` takes five numbers and a flag.  Until this round all
five were caller-invented, and the module said so.  Two of them are in a table
the client ships, and this round read it:

* ``aggro_radius`` <- ``CONSTDATA_TH__AI_WANDER.n_AGGRO`` of the row the
  monster's ``ai_wander`` column names.  1200 placement units for the three
  bg0001 monsters whose row is 11; ZERO for the ten whose row is 16.
* ``offensive``   <- ``CONSTDATA_TH__AI_WANDER.n_OFFESIVE`` of the same row.
  1 for row 11, 0 for row 16.  Ten of the thirteen bg0001 monsters do not
  charge anybody; they answer damage and nothing else.

The other three, and the cadence, are NOT in any committed table, and this
module invents them IN THE OPEN rather than in a caller nobody reads.  Each was
tagged ``[LANE-B ASSUMPTION - AWAITING COO]`` and put to the COO in the letter
``notes_to_chief/20260826_0955_LANE-B-ASK-COO-four-invented-mob-ai-numbers.md``.
``COO-DECISION`` 2026-08-26T11:41+07:00 (``notes_to_chief/20260826_1141_
COO-DECISION-mob-ai-three-answers-and-v5-criterion-rewrite.md``) accepted all
four numbers as chosen, with no revert and nothing re-derived: "keep going as
you are, no need to stop and wait, no need to revert any part" (COO's own
words, translated from the Thai original).  Each is now tagged
``[LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00]`` instead.
Confirmed does not mean derived: each number is still a choice this lane made
without a column to read it from, and rolling one back if it turns out wrong
is still one constant in this file, one test line, and a pin regeneration;
nothing downstream stores them beyond that pin.

WHAT THIS MODULE IS NOT
-----------------------
It sends NOTHING on the wire.  It composes no frame, opens no socket, touches
no database and reads no clock: a "tick" here is one call, and its period is
whatever the driver chooses.  ``mob_aggro.ATTACK_INTENT_DELIVERABLE`` is still
False -- Door B was never opened, and this module does not open it either.  The
attack intent is a DECISION with no transport, and no function here pretends
otherwise.

WHAT THE PLAYER WILL SEE DIFFERENTLY, STATED PLAINLY: nothing today, because
the call site is in ``runtime.py`` and that file belongs to the chief.  The day
the chief writes the line in :data:`MOB_AI_CONTROL_WIRING`, a monster that a
player hits stops being scenery: the server knows which player it owes an
answer to, it stops owing anything the moment it dies, and the three bg0001
monsters whose real AI row says ``n_OFFESIVE = 1`` become the only three that
ever pick a target nobody handed them.  What the player sees on the SCREEN
still waits on Door B, and this module does not claim a pixel.

[STALE as of runtime.py CORE-REQUEST-007, PR #71, round 3lzfhw,
2026-08-26T11:13+07:00] [MEASURED, by call-site reading and
tests/test_mob_ai_control_dispatch.py]: the first sentence above is no
longer true.  The chief HAS written the line: every accepted hit that lands
through the wired dispatch now runs damage_step/commit_step right after
mob_combat.commit_step, and every kill runs death_step/commit_step right
after mob_death.commit_death, unconditionally, on the boot the owner runs
with no flag -- see MOB_AI_CONTROL_NONCLAIMS #1, which was corrected in the
same round this paragraph was not.  What remains true, and is now the ONLY
sentence in this paragraph still gating a pixel, is the last one:
``mob_aggro.ATTACK_INTENT_DELIVERABLE`` is still False, Door B is still
unsent, so no monster picks a target nobody handed it and nothing on the
SCREEN differs yet.  This register now tracks the truth Door B would need
the day it opens; it does not make Door B exist.

NONCLAIMS
---------
* No original-server behaviour is claimed.  The mined ``n_AGGRO`` is a number
  in a shipped table; that the original server used it as a radius the way this
  module does is a READING, and the strongest one available, not a proof.
* No claim that a monster can be made to attack today.  Door B is unproven.
* No claim about anything on the screen.  Nothing here has touched a wire.
* ``CONSTDATA_TH__AI_TACTIC`` is not mined and not read: its rows are keyed by
  crew id and speak of pets and masters, so it is the player-crew table.
* Revival is not modelled: ``mob_aggro.PHASE_DEAD`` is absorbing, so a register
  row for a killed monster stays dead until a rebuild replaces the register.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from . import field_mob_ai_tables
from . import mob_aggro
from .field_mobs import FieldMob
from .mob_combat import HitOutcome


# No flag, no scenario id, no unlock.  See the header.
production_allowed = True

MOB_AI_CONTROL_MILESTONE = "MOB-AGGRO-001"
MOB_AI_CONTROL_BUILD_ORDER = "M4, the promotion COO ordered"
MOB_AI_CONTROL_LANE = "B_COMBAT"
MOB_AI_CONTROL_PROMOTION_RULING = "COO-DECISION 2026-08-26T04:02+07:00 s1.3, s3"

# THE PIN IS DOWNSTREAM STORAGE OF EVERY INVENTED NUMBER, thirteen times over,
# and an earlier draft of the COO letter claimed rolling one back was "one
# constant and one test line".  It is not: scenarios/combat_aggro_001.json
# holds leash_radius, home_radius, attack_range and the cadence for all
# thirteen monsters.  It is GENERATED, by this command, and the test that
# compares it can only catch a stale file - never a wrong number.
PIN_REGENERATION_COMMAND = (
    "python3 tools/pf_write_mob_ai_pin.py --out scenarios/combat_aggro_001.json"
)

# The one line this lane owes the chief, written where a reader of the module
# finds it and not only in a PR body.  It is deliberately additive: every call
# named here happens AFTER an existing committed step, so a runtime that has
# not been changed yet behaves exactly as it does today.
MOB_AI_CONTROL_WIRING = (
    "runtime.py: keep one mob_ai_control.MobAiRegister beside the combat "
    "ledger and the death register, opened with "
    "mob_ai_control.open_register(field_mobs.load_roster(), epoch) at the same "
    "point the combat ledger is opened, and on any REBUILD of the roster open "
    "it again with a STRICTLY GREATER epoch - a step from the old lineage "
    "would otherwise commit onto the rebuild and discard it silently.  "
    "(1) AFTER a mob_combat.commit_step is accepted, call "
    "mob_ai_control.damage_step(register_now, step.outcome) and commit it with "
    "mob_ai_control.commit_step(register_now, ai_step); on "
    "REFUSE_REGISTER_STALE LOOP: re-read the register and call damage_step "
    "again with the SAME outcome until the commit is accepted - do NOT re-run "
    "mob_combat.strike, which would answer no_room.  Guard the call with "
    "register_now.is_tracked(step.outcome.target_identity): the AI register and "
    "the combat ledger are opened from the same roster today but nothing in "
    "code couples them, and an untracked target raises REFUSE_NOT_TRACKED "
    "AFTER the frames have already gone out.  "
    "(2) AFTER a mob_death.commit_death is accepted, call "
    "mob_ai_control.death_step(register_now, step.outcome) and commit it, "
    "AND LOOP ON REFUSE_REGISTER_STALE EXACTLY AS IN (1) - this loop is not "
    "optional and is the one the first draft of this line left out: a driver "
    "that gives up here has a monster that is a corpse in the death register "
    "and IDLE with live threat in this one, with the outcome already dropped "
    "and nothing that will ever notice.  "
    "(3) IF THAT HAPPENS ANYWAY - a crash, a give-up, a rebuild - the repair "
    "needs no outcome: mob_ai_control.reconcile(register_now, death_register) "
    "returns one step that retires every row the death register calls a corpse, "
    "committed the same way.  Call it at the top of every rebuild.  "
    "No call in this line composes or sends a frame, so a refused commit sends "
    "nothing.  The tick loop (mob_ai_control.tick_step) is NOT part of this "
    "line and needs no timer today: with Door B unsent the only intent it can "
    "produce that anyone could act on is INTENT_RETURN_TO_LEASH, and this lane "
    "drives no movement (see CLIENT_RE_QUEUE RE-083)."
)

# ---------------------------------------------------------------------------
# The three numbers this module invents, and the anchor under each one.  They
# are constants rather than arguments so that a scan finds them, a test pins
# them, and rolling one back is one line.
#
# [LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00] leash radius.  Anchor: 2.5x the mined
# aggro radius, floored at 3000.0 -- which is 2.5 * 1200, the radius of the
# offensive rows of bg0001, and also 25% of the 12,095-placement-unit distance
# the FIELD-MOBS-001 note measured from the bg0001 spawn to its nearest
# monster.  A monster may be pulled a quarter of the way to the spawn before it
# forgets and goes home.
#
# IT IS A FORMULA AND NOT ONE NUMBER, and it stopped being one number because a
# flat 3000.0 was a trap for the next scene: mob_aggro refuses a profile whose
# leash is smaller than its aggro radius, and TEN of the 73 shipped AI_WANDER
# rows carry n_AGGRO above 3000 (rows 15 and 39 are 8000; 22, 24, 27, 28 and
# 103 are 5000).  bg0001 happens to touch none of them, so a flat constant was
# green here and would have refused the first roster that pointed at one -- and
# refused it at the first TICK, not at open_register, because opening never
# built a profile.  Both halves of that are fixed: the leash scales, and
# open_register builds every profile up front.
LEASH_RADIUS_FLOOR = 3000.0
LEASH_RADIUS_MULTIPLE = 2.5
LEASH_RADIUS = LEASH_RADIUS_FLOOR
LEASH_RADIUS_ANCHOR = "max(3000.0, 2.5 * the monster's own mined n_AGGRO)"


def leash_radius_for(aggro_radius: float) -> float:
    """The leash this lane gives a monster with that mined aggro radius."""
    return max(LEASH_RADIUS_FLOOR, float(aggro_radius) * LEASH_RADIUS_MULTIPLE)

# [LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00] home radius.  Anchor: the monster's OWN
# n_SPEED_WALK column, which is a real MOBS value (100 for every bg0001 row).
# Reading a speed as a distance is the invented half: it says "the return phase
# ends when the monster is within one step of home", and a step is whatever
# distance the table's walk speed covers in one driver tick.
HOME_RADIUS_IS_SPEED_WALK = True
HOME_RADIUS_ANCHOR = "field_mob_tables.speed_walk of the monster's own row"

# [LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00] attack range.  ANCHOR: NONE.  A BARE
# CHOICE, and saying so is the whole point of this comment.
#
# THE FIRST DRAFT CITED ONE AND THE CITATION IS WITHDRAWN, kept here rather than
# deleted because a withdrawn claim that leaves no trace comes back.  It read:
# "275 is the SMALLEST DISTANCE_ENEMY< band that appears anywhere in the
# AI_COMBAT rows this roster points at (rows 350 and 352 both use it) ... the
# closest range the original AI itself bothered to distinguish, borrowed as a
# reach", with the mitigation that nothing PARSES the rows to get it.
#
# An adversarial review took that apart on two counts and both hold:
#   1. the mitigation changed the TRANSPORT, not the PROVENANCE.  This lane's
#      own generator says in writing that those distances are skill-SELECTION
#      bands and that "reading them as an attack range would be an invention
#      wearing a table's clothes".  Doing the read by hand instead of by regex
#      is the same read.  The letter to the COO listed that exact move as the
#      WORST of the three options and then the code did it.
#   2. "smallest" was a pin nothing could re-derive.  Editing a band in the
#      generated rows left every test green while the word became false, and
#      checking it would need the parse this lane forbade itself.
#
# So the anchor is gone.  275.0 is a number lane B picked, it is inside the
# range of distances the shipped AI rows work in, and that resemblance is NOT
# offered as evidence for it.
MELEE_ATTACK_RANGE = 275.0
MELEE_ATTACK_RANGE_ANCHOR = "NONE - a bare choice by lane B, see the comment"
MELEE_ATTACK_RANGE_WITHDRAWN_ANCHOR = (
    "WITHDRAWN 2026-08-26 after adversarial review: 'smallest DISTANCE_ENEMY< "
    "band in AI_COMBAT 350/352'.  Never cite it again."
)

# [LANE-B ASSUMPTION - CONFIRMED BY COO 2026-08-26T11:41+07:00] cadence.  One, and one is the choice that
# invents the least: mob_aggro counts cadence in TICKS and never reads a clock,
# so a cadence of 1 says "this module adds no period of its own; the driver's
# tick period IS the attack period".  Any other value would be a number of
# seconds in disguise, and this project has not established a tick period.
ATTACK_CADENCE_TICKS = 1

LANE_B_ASSUMPTIONS = (
    "leash_radius " + LEASH_RADIUS_ANCHOR,
    "home_radius=speed_walk " + HOME_RADIUS_ANCHOR,
    "attack_range=275.0 anchor " + MELEE_ATTACK_RANGE_ANCHOR,
    "attack_cadence_ticks=1 the driver's tick period is the attack period",
)

MOB_AI_CONTROL_NONCLAIMS = (
    "1. CORE-REQUEST-007 wired this module into runtime.py's "
    "_dispatch_mob_combat: damage_step/death_step now run AFTER "
    "mob_combat.commit_step / mob_death.commit_death, exactly as "
    "MOB_AI_CONTROL_WIRING describes.  What remains UNDISPATCHED is the "
    "tick loop (mob_ai_control.tick_step) and reconcile() -- the wiring "
    "line says the tick loop needs no timer today (Door B unsent) and "
    "reconcile() has nothing to reach because this class never rebuilds "
    "the roster after opening it once per session.",
    "2. No frame is composed or sent here, so no claim is made about "
    "anything a player can see.",
    "3. n_AGGRO being a radius and n_OFFESIVE being an unprovoked-acquire "
    "flag are READINGS of two shipped columns, not proofs.",
    "4. mob_aggro.ATTACK_INTENT_DELIVERABLE is still False: the attack "
    "decision has no proven transport and this module opens none.",
    "5. Three profile numbers and the cadence are ours; see "
    "LANE_B_ASSUMPTIONS and the letter to the COO.",
)

STEP_DAMAGE = "damage"
STEP_DEATH = "death"
STEP_TICK = "tick"
STEP_RECONCILE = "reconcile"
MOB_AI_STEP_KINDS = (STEP_DAMAGE, STEP_DEATH, STEP_TICK,
                     STEP_RECONCILE)

REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_DUPLICATE_REGISTER_IDENTITY = "duplicate_register_identity"
REFUSE_REGISTER_NOT_SORTED = "register_not_sorted"
REFUSE_REGISTER_STALE = "register_stale"
REFUSE_NOT_TRACKED = "not_tracked"
REFUSE_OUTCOME_IS_NOT_A_KILL = "outcome_is_not_a_kill"
REFUSE_AI_ROW_MISSING = "ai_row_missing"
REFUSE_PROFILE_UNBUILDABLE = "profile_unbuildable"
REFUSE_DEATH_HANDLE_INCOMPLETE = "death_handle_incomplete"
REFUSE_REGISTER_EPOCH_MISMATCH = "register_epoch_mismatch"
REFUSE_STEP_KIND_UNKNOWN = "step_kind_unknown"
MOB_AI_CONTROL_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_DUPLICATE_REGISTER_IDENTITY,
    REFUSE_REGISTER_NOT_SORTED,
    REFUSE_REGISTER_STALE,
    REFUSE_NOT_TRACKED,
    REFUSE_OUTCOME_IS_NOT_A_KILL,
    REFUSE_AI_ROW_MISSING,
    REFUSE_PROFILE_UNBUILDABLE,
    REFUSE_DEATH_HANDLE_INCOMPLETE,
    REFUSE_REGISTER_EPOCH_MISMATCH,
    REFUSE_STEP_KIND_UNKNOWN,
)


class MobAiControlError(ValueError):
    """A named refusal; ``reason`` is one of MOB_AI_CONTROL_REFUSAL_REASONS."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason


def _require_identity(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        raise MobAiControlError(
            REFUSE_IDENTITY_NOT_POSITIVE, "%s=%r" % (label, value))
    return value


def _require_mob(value: Any) -> FieldMob:
    if type(value) is not FieldMob:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "expected a typed FieldMob")
    return value


def _require_outcome(value: Any) -> HitOutcome:
    if type(value) is not HitOutcome:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "expected a typed HitOutcome")
    return value


# ---------------------------------------------------------------------------
# The profile join: two mined values, three of ours.


def ai_rows_of(mob: FieldMob) -> tuple[tuple, tuple]:
    """The mined ``(wander_row, combat_row)`` this monster points at.

    Refused by name rather than defaulted: a monster whose AI row is absent has
    no radius and no offensive flag, and inventing either is exactly what this
    round stopped doing.
    """
    _require_mob(mob)
    wander = field_mob_ai_tables.AI_WANDER_ROWS.get(mob.ai_wander)
    if wander is None:
        raise MobAiControlError(
            REFUSE_AI_ROW_MISSING,
            "placement %d points at AI_WANDER %d, which is not in the mined "
            "rows: regenerate field_mob_ai_tables" % (
                mob.placement_index, mob.ai_wander))
    combat = field_mob_ai_tables.AI_COMBAT_ROWS.get(mob.ai_combat)
    if combat is None:
        raise MobAiControlError(
            REFUSE_AI_ROW_MISSING,
            "placement %d points at AI_COMBAT %d, which is not in the mined "
            "rows: regenerate field_mob_ai_tables" % (
                mob.placement_index, mob.ai_combat))
    return wander, combat


def profile_of(mob: FieldMob) -> mob_aggro.MobAiProfile:
    """The AI profile of one roster monster, mined where a table exists.

    ``aggro_radius`` and ``offensive`` come from the monster's own AI_WANDER
    row.  ``home_radius`` comes from its own ``speed_walk``.  ``leash_radius``,
    ``attack_range`` and the cadence are this module's constants, each tagged
    at its definition.
    """
    wander, _combat = ai_rows_of(mob)
    _script, _faction, offensive, aggro_radius = wander
    return mob_aggro.MobAiProfile(
        aggro_radius=float(aggro_radius),
        leash_radius=leash_radius_for(aggro_radius),
        home_radius=float(mob.speed_walk),
        attack_range=MELEE_ATTACK_RANGE,
        attack_cadence_ticks=ATTACK_CADENCE_TICKS,
        offensive=bool(offensive),
    )


def offensive_identities(mobs: tuple[FieldMob, ...]) -> tuple[int, ...]:
    """The actor identities whose mined AI row acquires a target unprovoked.

    Printed by the round note and pinned by a test because it is the one
    sentence of this round a reader can check against the shipped table by eye:
    three of thirteen, and the other ten answer damage only.
    """
    return tuple(
        mob.actor_identity for mob in mobs if profile_of(mob).offensive
    )


# ---------------------------------------------------------------------------
# The register: one row per monster, a generation, and a compare-and-swap.


@dataclass(frozen=True)
class MobAiRow:
    """One monster's roster row and its AI state, carried together.

    THE ROW CARRIES THE MOB, and that is not storage for its own sake: it makes
    one whole class of driver bug unstateable.  ``mob_aggro.MobObservation``
    carries NO identity -- it is a position, an HP and a list of players -- so a
    tick function that took ``(mob, observation)`` as two arguments would drive
    monster A's state from monster B's surroundings whenever a driver paired
    them wrongly, silently and forever.  With the roster row in the register,
    :func:`tick_step` takes an IDENTITY and looks the row up itself, and there
    is nothing left to pair.
    """

    mob: FieldMob
    state: mob_aggro.MobAiState

    def __post_init__(self) -> None:
        _require_mob(self.mob)
        if type(self.state) is not mob_aggro.MobAiState:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "row state must be a typed mob_aggro.MobAiState")

    @property
    def actor_identity(self) -> int:
        return self.mob.actor_identity


@dataclass(frozen=True)
class MobAiRegister:
    """Every monster's AI state, as a tuple sorted by identity.

    Sorted-tuple with a generation for the reasons ``mob_combat.CombatLedger``
    and ``mob_death.DeathRegister`` each give for theirs, and the second reason
    matters more here than in either: two players hitting two DIFFERENT
    monsters in the same tick both read this register, both return a register
    with one row changed, and whichever is stored second erases the other
    monster's threat WITHOUT RAISING - so a monster that was just pulled goes
    back to idle and nobody is told.  :func:`commit_step` is the compare-and-
    swap that makes the loser retry.
    """

    rows: tuple[MobAiRow, ...] = ()
    generation: int = 0
    epoch: int = 0

    def __post_init__(self) -> None:
        if type(self.rows) is not tuple:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD, "rows must be a tuple")
        seen = set()
        for row in self.rows:
            if type(row) is not MobAiRow:
                raise MobAiControlError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "every register row must be a typed MobAiRow")
            if row.actor_identity in seen:
                raise MobAiControlError(
                    REFUSE_DUPLICATE_REGISTER_IDENTITY,
                    "identity 0x%X appears twice" % row.actor_identity)
            seen.add(row.actor_identity)
        ordered = tuple(sorted(self.rows, key=lambda row: row.actor_identity))
        if ordered != self.rows:
            raise MobAiControlError(
                REFUSE_REGISTER_NOT_SORTED,
                "register rows must be given in ascending identity order")
        for label, value in (("generation", self.generation),
                             ("epoch", self.epoch)):
            if type(value) is not int or value < 0:
                raise MobAiControlError(
                    REFUSE_TYPE_NOT_TYPED_RECORD, "%s=%r" % (label, value))

    def identities(self) -> tuple[int, ...]:
        return tuple(row.actor_identity for row in self.rows)

    def is_tracked(self, actor_identity: int) -> bool:
        wanted = _require_identity(actor_identity, "actor identity")
        return any(row.actor_identity == wanted for row in self.rows)

    def row_of(self, actor_identity: int) -> MobAiRow:
        wanted = _require_identity(actor_identity, "actor identity")
        for row in self.rows:
            if row.actor_identity == wanted:
                return row
        raise MobAiControlError(
            REFUSE_NOT_TRACKED,
            "identity 0x%X is not a monster this register opened" % wanted)

    def mob_of(self, actor_identity: int) -> FieldMob:
        return self.row_of(actor_identity).mob

    def state_of(self, actor_identity: int) -> mob_aggro.MobAiState:
        return self.row_of(actor_identity).state

    def with_state(self, actor_identity: int,
                   state: mob_aggro.MobAiState) -> "MobAiRegister":
        wanted = _require_identity(actor_identity, "actor identity")
        self.row_of(wanted)
        if type(state) is not mob_aggro.MobAiState:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "replacement must be a typed mob_aggro.MobAiState")
        return MobAiRegister(
            tuple(
                MobAiRow(row.mob, state)
                if row.actor_identity == wanted else row
                for row in self.rows
            ),
            self.generation + 1,
            self.epoch,
        )


def open_register(mobs: tuple[FieldMob, ...], epoch: int = 0) -> MobAiRegister:
    """One idle row per monster, each anchored to where the table placed it.

    The leash origin is the PLACEMENT position, not wherever the monster
    happens to be: a monster that is pulled and then forgets must return to the
    spot the table put it on, and the table is the only thing that knows it.

    ``epoch`` IS THE DRIVER'S OBLIGATION AND THE ONE THING THIS MODULE CANNOT
    DERIVE.  A generation is a step counter, so a REBUILD -- a second
    ``open_register`` over the same roster, which the header's own revival note
    contemplates -- produces a register at generation 0 that is
    indistinguishable from the one it replaced.  A step computed before the
    rebuild then commits ONTO it and silently discards the whole rebuild.  The
    identity-set guard cannot see it (same monsters) and the generation guard
    cannot see it (both zero).  So the driver must pass a STRICTLY GREATER
    epoch on every rebuild, and :func:`commit_step` refuses any step whose
    epoch does not match the stored register's.
    """
    if type(epoch) is not int or isinstance(epoch, bool) or epoch < 0:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "epoch=%r" % (epoch,))
    if type(mobs) not in (tuple, list):
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "mobs must be a tuple or list")
    rows = []
    for mob in mobs:
        _require_mob(mob)
        # Refuse here rather than at the first tick: a roster with an AI row
        # missing must not open a register that works until someone is hit.
        # BUILD THE PROFILE HERE, not just find the AI row.  An earlier draft
        # checked only that the row existed, which meant a roster whose mined
        # radius contradicted one of this lane's own invented numbers opened a
        # register that WORKED UNTIL THE FIRST TICK -- and then raised a
        # mob_aggro reason that is not in this module's refusal vocabulary, out
        # of a function the wiring line does not even mention.  That is the
        # exact failure this function's docstring says it exists to prevent.
        try:
            profile_of(mob)
        except mob_aggro.MobAiContractError as error:
            raise MobAiControlError(
                REFUSE_PROFILE_UNBUILDABLE,
                "placement %d cannot be given a profile: %s" % (
                    mob.placement_index, error)) from error
        rows.append(MobAiRow(
            mob, mob_aggro.initial_state((mob.x, mob.y, mob.z))))
    return MobAiRegister(
        tuple(sorted(rows, key=lambda row: row.actor_identity)), 0, epoch)


# ---------------------------------------------------------------------------
# The steps.


@dataclass(frozen=True)
class MobAiStep:
    """One move of one monster's AI state, uncommitted.

    ``base_generation`` is the generation the step was computed FROM, and
    :func:`commit_step` refuses any step whose base has moved.
    """

    kind: str
    actor_identity: int
    before: mob_aggro.MobAiState
    after: mob_aggro.MobAiState
    register: MobAiRegister
    base_generation: int
    intent: Optional[mob_aggro.MobAiIntent] = None

    def __post_init__(self) -> None:
        if self.kind not in MOB_AI_STEP_KINDS:
            raise MobAiControlError(
                REFUSE_STEP_KIND_UNKNOWN, "kind=%r" % (self.kind,))
        _require_identity(self.actor_identity, "actor identity")
        for label, value in (("before", self.before), ("after", self.after)):
            if type(value) is not mob_aggro.MobAiState:
                raise MobAiControlError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be a typed mob_aggro.MobAiState" % label)
        if type(self.register) is not MobAiRegister:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "step register must be a typed MobAiRegister")
        if type(self.base_generation) is not int or self.base_generation < 0:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "base_generation=%r" % (self.base_generation,))
        if self.intent is not None and \
                type(self.intent) is not mob_aggro.MobAiIntent:
            raise MobAiControlError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "intent must be a typed mob_aggro.MobAiIntent or None")

    @property
    def moved(self) -> bool:
        """Did the state actually change, or did the aggro lane decline it?

        ``mob_aggro.apply_damage_threat`` returns the state UNCHANGED and
        without complaint for a monster that is returning or dead.  That is its
        declared design, and a driver that cannot tell the difference reports a
        monster as pulled when it is not, so the answer is on the step.
        """
        return self.after != self.before

    @property
    def target_identity(self) -> Optional[int]:
        return self.after.target_identity


def damage_step(register: MobAiRegister, outcome: HitOutcome) -> MobAiStep:
    """Fold one hit into the target's threat table.

    The number handed to ``mob_aggro.apply_damage_threat`` is the WIRE number,
    which is NEGATIVE, for the reason ``mob_combat.apply_threat`` spells out:
    the aggro lane adds threat only for a negative value and silently ignores a
    positive one, so handing over the positive arithmetic value would build a
    monster that is hit, loses HP, repaints its bar and never once decides it
    has an enemy - with nothing raised anywhere.

    A hit that moved nothing (``damage == 0``, which is ``no_room`` on a
    monster already at the floor) folds nothing and says so through
    ``step.moved``.
    """
    if type(register) is not MobAiRegister:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed MobAiRegister")
    _require_outcome(outcome)
    before = register.state_of(outcome.target_identity)
    if outcome.damage == 0:
        after = before
    else:
        after = mob_aggro.apply_damage_threat(
            before, outcome.attacker_identity, outcome.damage_wire)
    # BY VALUE, not by identity, and the difference is a real case: threat
    # saturates at THREAT_MAX, so a hit on a monster already at the ceiling
    # builds a NEW state object that is EQUAL to the old one.  Comparing by
    # identity there would bump the register's generation - inventing a stale
    # read for every other driver in the same tick - while ``step.moved``, which
    # compares by value, said nothing happened.  One comparison, used
    # everywhere.
    moved = register if after == before else register.with_state(
        outcome.target_identity, after)
    return MobAiStep(
        STEP_DAMAGE, outcome.target_identity, before, after, moved,
        register.generation,
    )


def death_step(register: MobAiRegister, outcome: HitOutcome) -> MobAiStep:
    """Retire the monster's AI: absorbing phase, empty table, no target.

    REFUSES an outcome that is not a kill, by name.  ``mob_death.kill`` refuses
    the same shape for the same reason, written there: a lane that can retire a
    monster the arithmetic did not kill is a lane that can retire one at full
    HP.  ``no_room`` - a hit that landed on something already dead - is not a
    kill either, and is refused here even though the register row is already
    dead, because a caller that reaches this line on a no_room hit has its
    ordering wrong and should hear about it.

    This is called AFTER ``mob_death.commit_death``, never before; see the
    ordering in the module header.
    """
    if type(register) is not MobAiRegister:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed MobAiRegister")
    _require_outcome(outcome)
    if outcome.no_room or not outcome.death_due:
        raise MobAiControlError(
            REFUSE_OUTCOME_IS_NOT_A_KILL,
            "this outcome leaves the monster at %d of %d HP (no_room=%r); only "
            "the hit that reached the floor may retire an AI row" % (
                outcome.hp_after, outcome.max_hp, outcome.no_room))
    before = register.state_of(outcome.target_identity)
    after = mob_aggro.MobAiState(
        phase=mob_aggro.PHASE_DEAD,
        leash_origin=before.leash_origin,
        threat=(),
        target_identity=None,
        ticks_since_attack=0,
    )
    moved = register if after == before else register.with_state(
        outcome.target_identity, after)
    return MobAiStep(
        STEP_DEATH, outcome.target_identity, before, after, moved,
        register.generation,
    )


def tick_step(register: MobAiRegister, actor_identity: int,
              observation: mob_aggro.MobObservation) -> MobAiStep:
    """One decision tick for one monster, against its own mined profile.

    Takes an IDENTITY, not a roster row, and that is deliberate: a
    ``mob_aggro.MobObservation`` carries no identity of its own, so a signature
    that took the row and the observation separately would let a driver pair
    them wrongly and drive one monster's state from another's surroundings
    without raising.  The register knows which row goes with which identity;
    nothing else has to.

    The observation is the driver's; this module neither reads positions off a
    wire nor invents them.
    """
    if type(register) is not MobAiRegister:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed MobAiRegister")
    if type(observation) is not mob_aggro.MobObservation:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "observation must be a typed mob_aggro.MobObservation")
    row = register.row_of(actor_identity)
    result = mob_aggro.tick(profile_of(row.mob), row.state, observation)
    after = result.state
    moved = register if after == row.state else register.with_state(
        row.actor_identity, after)
    return MobAiStep(
        STEP_TICK, row.actor_identity, row.state, after, moved,
        register.generation, result.intent,
    )


def commit_step(current: MobAiRegister, step: MobAiStep) -> MobAiRegister:
    """Compare-and-swap: accept a step only against the register it read.

    Returns the new register.  Refuses with :data:`REFUSE_REGISTER_STALE` when
    the stored register has moved since the step was computed, in which case
    the caller re-reads and re-runs THE SAME STEP FUNCTION with the SAME
    outcome it is still holding.  Do NOT re-run ``mob_combat.strike`` on a
    refusal here: the combat ledger already holds the hit, so it would answer
    ``no_room`` and the threat would be lost for good.

    Nothing is ever sent on a refusal because nothing in this module composes a
    frame in the first place -- but the caller's OTHER lanes have already sent
    theirs by this point in the order, so a refusal here means "retry", never
    "unwind".  The retry is safe: threat is a fold of one hit into one table
    and re-running it from a re-read register produces the same table.
    """
    if type(current) is not MobAiRegister:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "current must be a typed MobAiRegister")
    if type(step) is not MobAiStep:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed MobAiStep")
    if current.epoch != step.register.epoch:
        raise MobAiControlError(
            REFUSE_REGISTER_EPOCH_MISMATCH,
            "this step was computed against register epoch %d and the stored "
            "register is at epoch %d: the roster was rebuilt under the step, "
            "so re-read the register and recompute against the new epoch" % (
                step.register.epoch, current.epoch))
    if current.generation != step.base_generation:
        raise MobAiControlError(
            REFUSE_REGISTER_STALE,
            "this step was computed from generation %d and the register is at "
            "generation %d: re-read the register and call the same step "
            "function again with the outcome you are holding" % (
                step.base_generation, current.generation))
    # A generation is a counter, and a counter is not a value -- the lesson
    # mob_death.commit_death paid for.  Two registers that have taken the same
    # NUMBER of steps carry the same generation while describing different
    # monsters, and committing across lineages would drop rows without a word.
    if set(current.identities()) != set(step.register.identities()):
        raise MobAiControlError(
            REFUSE_REGISTER_STALE,
            "this step was computed from a different lineage that happens to "
            "be the same length: it tracks %d monsters and the stored register "
            "tracks %d" % (
                len(step.register.identities()), len(current.identities())))
    return step.register


def reconcile(register: MobAiRegister, death_register: Any) -> MobAiStep:
    """Retire every AI row the DEATH REGISTER says is a corpse.  The repair.

    THIS FUNCTION EXISTS BECAUSE THE ORDER IN THE HEADER IS NOT SELF-HEALING,
    and an adversarial review was right that saying "not negotiable" is not the
    same as making it enforceable.  Two ways the two registers come apart, both
    reachable by a driver following the wiring line exactly:

      * ``death_step``'s commit is refused as stale (another monster's kill
        landed in the same tick) and the driver treats "commit it the same way"
        as one call rather than a loop.  The monster is then a corpse in the
        death register and IDLE with live threat here, and the ``HitOutcome``
        ``death_step`` would need to fix it has already been dropped;
      * the driver dies between the death commit and the AI commit.

    Neither raises anything, neither logs, and the tick loop that would
    eventually notice ``hp <= 0`` is explicitly OUTSIDE the wiring line today.
    So the repair must not need the outcome, and this one does not: it needs
    only the two registers.  Call it at the top of any rebuild, and after any
    refused ``death_step``.

    ``death_register`` is taken as a HANDLE rather than imported, for the one
    reason a handle is still right here: ``mob_death`` imports ``field_mobs``
    and composes wire frames, and this module composes none - importing it
    would drag a frame composer into the decision lane for one predicate.  Only
    ``is_dead`` and ``identities`` are used, and a handle missing either is
    refused by name rather than skipped.

    NOT UPDATED for COO-DECISION 2026-08-27T22:49+07:00 (``mob_death.
    DeathRegister`` now keys ``is_dead`` by ``(scene, actor_identity)``, with
    ``scene`` an OPTIONAL second parameter defaulting to bg0001) - and this is
    a deliberate scope line, not an oversight.  This function calls ``is_dead(
    row.actor_identity)`` with ONE argument on purpose: the handle contract
    this docstring documents (``is_dead``/``identities``, nothing else) is
    pinned by ``tests/test_mob_ai_control.py``'s own hand-written
    ``FakeDeaths.is_dead(self, identity)`` stand-in, which takes exactly one
    argument, and widening the call here to two positional arguments would
    break that stand-in (and every test built on it) for a collision that
    cannot happen yet: ``MobAiRegister`` is opened from one ``load_roster()``
    call per session, and cross-scene-in-session (M2) is still paused per
    PANYA-DECISION 2026-08-27T20:10+07:00, so a real ``mob_death.
    DeathRegister`` handed here today only ever carries ONE scene's dead
    identities - the default answers correctly with no scene passed.  The day
    M2 lifts, this call site (and the ``FakeDeaths`` duck-type contract with
    it) needs its own scoped decision to add ``scene``; noted here rather than
    guessed at, per this lane's own nonclaim discipline.
    """
    if type(register) is not MobAiRegister:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "register must be a typed MobAiRegister")
    is_dead = getattr(death_register, "is_dead", None)
    identities = getattr(death_register, "identities", None)
    if not callable(is_dead) or not callable(identities):
        raise MobAiControlError(
            REFUSE_DEATH_HANDLE_INCOMPLETE,
            "the death register handle must expose callable is_dead and "
            "identities")
    moved = register
    retired = []
    for row in register.rows:
        if not is_dead(row.actor_identity):
            continue
        if row.state.phase == mob_aggro.PHASE_DEAD:
            continue
        retired.append(row.actor_identity)
        moved = moved.with_state(row.actor_identity, mob_aggro.MobAiState(
            phase=mob_aggro.PHASE_DEAD,
            leash_origin=row.state.leash_origin,
            threat=(),
            target_identity=None,
            ticks_since_attack=0,
        ))
    # One step for the whole sweep, so one compare-and-swap covers it.  The
    # before/after pair names the FIRST row repaired, or the register's own
    # first row when there was nothing to repair.
    anchor = retired[0] if retired else (
        register.rows[0].actor_identity if register.rows else None)
    if anchor is None:
        raise MobAiControlError(
            REFUSE_NOT_TRACKED, "an empty register has nothing to reconcile")
    return MobAiStep(
        STEP_RECONCILE, anchor, register.state_of(anchor),
        moved.state_of(anchor), moved, register.generation,
    )


def describe_step(step: MobAiStep) -> tuple[str, ...]:
    """ASCII lines for logs and console -- cp874-safe by construction."""
    if type(step) is not MobAiStep:
        raise MobAiControlError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "step must be a typed MobAiStep")
    lines = [
        "mob_ai_control|%s|kind=%s|actor=0x%X|phase=%s->%s|moved=%s|target=%s"
        % (
            MOB_AI_CONTROL_MILESTONE,
            step.kind,
            step.actor_identity,
            step.before.phase,
            step.after.phase,
            "yes" if step.moved else "no",
            "-" if step.target_identity is None else str(step.target_identity),
        )
    ]
    for identity, threat in step.after.threat:
        lines.append("threat|identity=%d|value=%d" % (identity, threat))
    if step.kind == STEP_DAMAGE and not step.moved:
        lines.append(
            "  threat NOT recorded: the monster is returning or dead, or the "
            "hit moved no HP")
    if step.intent is not None:
        lines.append(
            "intent|kind=%s|target=%s|deliverable=%s" % (
                step.intent.kind,
                "-" if step.intent.target_identity is None
                else str(step.intent.target_identity),
                "no" if step.intent.kind == mob_aggro.INTENT_ATTACK_UNDELIVERABLE
                else "yes",
            ))
    return tuple(lines)


def pin_document(mobs: tuple[FieldMob, ...]) -> dict:
    """The scenario pin this lane writes, computed rather than typed."""
    roster = tuple(mobs)
    profiles = []
    for mob in roster:
        profile = profile_of(mob)
        profiles.append({
            "placement_index": mob.placement_index,
            "actor_identity": mob.actor_identity,
            "display_name": mob.display_name,
            "ai_wander": mob.ai_wander,
            "ai_combat": mob.ai_combat,
            "aggro_radius": profile.aggro_radius,
            "offensive": profile.offensive,
            "leash_radius": profile.leash_radius,
            "home_radius": profile.home_radius,
            "attack_range": profile.attack_range,
            "attack_cadence_ticks": profile.attack_cadence_ticks,
        })
    return {
        # The markers every sibling pin in scenarios/ carries.  This file is a
        # PIN, not a runnable scenario: nothing loads it, and the lane it
        # describes has no scenario id at all.
        "schema": 1,
        "not_a_scenario": True,
        "test_only": False,
        "regenerated_by": PIN_REGENERATION_COMMAND,
        "pin_id": "port_royal_field_mob_ai_control_001",
        "milestone": MOB_AI_CONTROL_MILESTONE,
        "build_order": MOB_AI_CONTROL_BUILD_ORDER,
        "lane": MOB_AI_CONTROL_LANE,
        "promotion_ruling": MOB_AI_CONTROL_PROMOTION_RULING,
        "production_allowed": production_allowed,
        "mob_aggro_production_allowed": mob_aggro.production_allowed,
        "mob_aggro_dispatch_reachable": mob_aggro.MOB_AGGRO_DISPATCH_REACHABLE,
        "attack_intent_deliverable": mob_aggro.ATTACK_INTENT_DELIVERABLE,
        "source_digests": dict(field_mob_ai_tables.SOURCE_DIGESTS),
        "mined_values": ["aggro_radius", "offensive"],
        "lane_b_assumptions": list(LANE_B_ASSUMPTIONS),
        "offensive_identities": [
            "0x%X" % identity for identity in offensive_identities(roster)
        ],
        "mob_count": len(roster),
        "profiles": profiles,
        "nonclaims": list(MOB_AI_CONTROL_NONCLAIMS),
        "wiring": MOB_AI_CONTROL_WIRING,
    }
