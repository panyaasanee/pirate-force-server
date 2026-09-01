"""LANE-B / MOB-AGGRO-001 continuation: the driver mob_ai_control's own
header names as still missing, and nothing more than that.

WHY THIS MODULE EXISTS.  ``mob_ai_control.tick_step`` has existed since round
3lzfhw and no caller anywhere in this tree runs it in production -- confirmed
this round (``notes_to_chief/20260831_1700_KA1B-TO-LANE-B-...`` finding 2,
re-verified against HEAD by reading ``runtime.py`` for every
``mob_ai_control.`` call site: only ``damage_step``/``death_step``, never
``tick_step``).  ``damage_step``/``death_step`` are REACTIVE -- they fire off
an already-committed hit or an already-committed kill.  ``tick_step`` is the
only PROACTIVE half: the one that lets a monster whose mined
``n_OFFESIVE = 1`` notice a player who never swung at it.  Without a caller,
every monster in this project is a target dummy that happens to fight back,
never one that starts anything -- which is the concrete shape of the
owner's "monsters do not move" complaint, read off the code rather than off
a screen.

[STALE as of round p05wire, 2026-08-31T~19:11 UTC (COO-DECISION
20260901_0145)][MEASURED, round bgwgso, 2026-09-01T16:39+07:00] "no caller
anywhere in this tree runs it in production" and "only damage_step/
death_step, never tick_step" are both false again: ``runtime.py``'s
``dispatch()`` now calls ``lane_hooks.lane_b_mob_ai_tick.maybe_tick`` on
every ``TARGET_POS_VITAL`` frame once ``mob_ai_register``/
``mob_combat_ledger``/``foundation.selected`` are all set (guard read at
``runtime.py:5196-5202``, commit ``5ac93b31``), and ``maybe_tick`` is a thin
wrapper whose only body is a call into THIS module's own
:func:`tick_session` (``lane_hooks/lane_b_mob_ai_tick.py:181``), which in
turn is what calls ``mob_ai_control.tick_step`` per row (see this file's own
:func:`tick_session` below).  Every one of ``lane_b_mob_ai_tick``,
``mob_ai_scheduler`` and ``mob_ai_control`` has ``production_allowed =
True`` (grepped all three at HEAD, round bgwgso), so this is the live,
flagless path, not a scenario-gated probe.  ``tick_step`` is proactive-only
in the sense this paragraph describes; that part of the analysis still
holds -- only the "no caller" claim is what changed.

WHAT THIS MODULE ADDS, AND ONLY THIS.  A caller.  One deterministic pass, one
player, over every mob row a SESSION already tracks in its own
``mob_ai_control.MobAiRegister`` -- because every register in this codebase
is already per-session (``runtime.py`` comment at the ``open_register`` call
site: "same per-session choice as mob_combat_ledger/mob_death_register just
above... follows the pattern every other mutable structure on this class
already uses").  A session's register never holds another session's monsters,
and this module does not change that: it takes the register and the ledger a
caller already has, and the ONE player observation a per-session driver can
ever honestly build -- its own connection's own last known position.  Nothing
here discovers OTHER players in the scene; that registry does not exist in
``src/`` today (grepped for one: none), and inventing a scene-wide session
list is not this module's job.

WHY THIS IS "ONE MOB, ONE SCENE, DETERMINISTIC CLOCK, STOP RULE" AND NOT A
WORLD LOOP.  The letter that asked for this named the shape before the code
existed; this module is built to that shape on purpose, not by accident:

* ONE SCENE per call, because the register itself is opened for exactly one
  scene's roster (``_sync_combat_scene_state`` re-opens it on travel) --
  :func:`tick_session` never merges two registers.
* THE CLOCK IS THE CALLER'S, not a wall clock and not a new timer this module
  starts.  :func:`tick_session` is a plain function call; its cadence is
  whatever the driver calls it at.  (Today: nothing calls it.  See
  CORE-REQUEST below for the smallest true next step, which this module does
  NOT take.)
  [STALE as of round p05wire][MEASURED, round bgwgso] "nothing calls it" is
  now false -- the cadence today is "once per TARGET_POS_VITAL frame a moving
  player already sends", via ``lane_hooks.lane_b_mob_ai_tick.maybe_tick``
  (see the paragraph above).  Still not a wall clock or a new timer -- that
  part of the sentence still holds.
* THE STOP RULE is that the loop is bounded by the register's own row count
  -- a per-session roster this project has never shipped larger than
  seventeen rows (Bg0002's ``PREDICATE_CENSUS``) -- and nothing here re-reads
  the register from storage or retries: :func:`mob_ai_control.commit_step` is
  called exactly once per row, against the register THIS function is still
  holding, never against a value re-fetched mid-loop.  A concurrent writer
  refusing that commit is a bug in a caller this module does not have yet
  (single-threaded, single-call), not a case this function silently papers
  over -- see NONCLAIMS.

WHAT THIS MODULE IS NOT, SAID IN THE SAME WORDS ``mob_ai_control`` USES FOR
ITSELF.  It sends NOTHING on the wire.  It composes no frame, opens no
socket, touches no database and reads no clock.
``mob_aggro.ATTACK_INTENT_DELIVERABLE`` is still ``False`` -- Door B is still
unopened, and this module does not open it either.  Every
:class:`SchedulerStepResult` this function returns is read-only truth for a
caller to log or inspect; nothing here decides what a client should render.

WHAT THE PLAYER WILL SEE DIFFERENTLY, STATED PLAINLY: nothing today.  The
call site is in ``runtime.py`` and that file belongs to the chief, and even
once called, this function still sends no frame -- Door B (turning
``MobAiIntent`` into bytes a client renders as movement or an attack) is a
separate, larger decision this module does not make.  What changes the
moment a caller DOES call this on every relevant dispatch is internal only:
the AI register starts recording proactive threat/phase truth
(``MobAiState.phase``, ``.threat``, ``.target_identity``) instead of staying
permanently idle between hits, which is the prerequisite Door B needs and did
not have before this round.

[STALE as of round p05wire][MEASURED, round bgwgso] "nothing today" and "The
call site is in runtime.py and that file belongs to the chief" (future
tense, as if unwritten) are both stale: the call site was added by the chief
in round p05wire (commit ``5ac93b31``, via the
``lane_hooks.lane_b_mob_ai_tick`` wrapper this module's own header names in
its first line).  It is called on every relevant dispatch now, so the
"moment a caller DOES call this" described above is not hypothetical --
it already happened, and the internal-only effect it describes
(``MobAiState.phase``/``.threat``/``.target_identity`` now update on live
traffic) is the current, measured behavior, still with zero bytes on the
wire (Door B remains closed; unchanged).

NONCLAIMS
---------
* No claim that a monster can be made to walk, attack, or otherwise animate
  today.  Door B is unproven and unbuilt; this module tracks a truth Door B
  would need, it does not make Door B exist (same sentence
  ``mob_ai_control``'s own header uses for itself, and true here for the
  same reason).
* No claim about "the players in a scene".  This module knows about exactly
  ONE player per call: the one its caller names.  A register with monsters
  that should be reacting to a SECOND player this session cannot see will
  not react to that second player -- that gap is named, not hidden, and is
  the reason CORE-REQUEST below asks for a call site tied to an existing
  per-session dispatch point rather than a new server-wide timer.
* No claim about original-server AI cadence.  How often the real server
  ticked a monster's brain is not recovered anywhere in this project; the
  cadence here is "however often the caller calls this", stated as a
  parameter-free fact rather than a number this lane would otherwise have to
  invent.
* :func:`tick_session` raises (does not swallow) any
  :class:`mob_ai_control.MobAiControlError` or
  :class:`mob_combat.MobCombatContractError` a row triggers -- a monster in
  the AI register that the combat ledger does not also track is a real
  mismatch between two registers a caller opened from the same roster, and
  fixing that silently would hide the bug that produced it (see
  the roster loader's own single-scene guard for the sibling promise this
  keeps).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from . import mob_aggro
from . import mob_ai_control
from . import mob_combat


# No flag, no scenario id, no unlock -- same reason mob_ai_control gives for
# itself: a lane whose production_allowed is false, reached from production
# through an argument no scan can see, is the hole that makes "flagless"
# meaningless.  This module sends no wire bytes either way, so there is
# nothing a flag could gate.
production_allowed = True

MOB_AI_SCHEDULER_MILESTONE = "MOB-AGGRO-001 continuation (tick_step caller)"
MOB_AI_SCHEDULER_LANE = "B_COMBAT"
MOB_AI_SCHEDULER_ORIGIN = (
    "notes_to_chief/20260831_1700_KA1B-TO-LANE-B-three-code-defects-"
    "from-owner-audit-verify-then-ticket.md finding 2, verified against "
    "HEAD by LANE-B round 256rvs (2026-08-31T18:50+07:00)"
)

REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"

MOB_AI_SCHEDULER_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
)


class MobAiSchedulerError(ValueError):
    """A named refusal; ``reason`` is one of MOB_AI_SCHEDULER_REFUSAL_REASONS."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason


@dataclass(frozen=True)
class SchedulerStepResult:
    """One monster's outcome from one :func:`tick_session` pass.

    Carries the phase transition and the intent by NAME, not just the
    boolean "did it move" a caller could get from comparing registers --
    console logging (the one thing this module is allowed to do) needs the
    reason, not just the fact.
    """

    actor_identity: int
    before_phase: str
    after_phase: str
    intent_kind: str
    intent_target_identity: int | None

    def __post_init__(self) -> None:
        if type(self.actor_identity) is not int or self.actor_identity <= 0:
            raise MobAiSchedulerError(
                REFUSE_IDENTITY_NOT_POSITIVE,
                "actor_identity=%r" % (self.actor_identity,))
        for label, value in (("before_phase", self.before_phase),
                              ("after_phase", self.after_phase),
                              ("intent_kind", self.intent_kind)):
            if type(value) is not str or not value:
                raise MobAiSchedulerError(
                    REFUSE_TYPE_NOT_TYPED_RECORD,
                    "%s must be a non-empty str, got %r" % (label, value))


def tick_session(
    ai_register: mob_ai_control.MobAiRegister,
    combat_ledger: mob_combat.CombatLedger,
    player_identity: int,
    player_position: Tuple[float, float, float],
    player_alive: bool = True,
) -> Tuple[mob_ai_control.MobAiRegister, Tuple[SchedulerStepResult, ...]]:
    """One deterministic pass over every mob one session's register tracks.

    Builds each mob's :class:`mob_aggro.MobObservation` from data this
    session already owns -- the mob's own PLACEMENT position (no monster in
    this project moves yet, so the placement position IS its current
    position; the day one moves, this line is what stops being true, and it
    is one line to change, not a redesign) and its live HP from
    ``combat_ledger.balance_of`` (never re-derived, never invented) -- and
    the ONE player this session can see.  Ticks every row through
    :func:`mob_ai_control.tick_step` / :func:`mob_ai_control.commit_step` in
    ascending identity order (the register's own sort order,
    ``ai_register.identities()``), threading the register through so row 2's
    tick sees row 1's committed state, exactly as two separate driver calls
    in the same tick would.

    Returns the new register and one :class:`SchedulerStepResult` per row,
    in the same ascending order, for a caller to log.  Composes no frame,
    sends nothing, and is safe to call as often as the caller likes: a
    monster whose observation has not changed since the last call ticks to
    the same state (:func:`mob_ai_control.tick_step` is pure) and produces
    ``INTENT_NONE`` or a repeat of its last real intent, never a side effect.
    """
    if type(ai_register) is not mob_ai_control.MobAiRegister:
        raise MobAiSchedulerError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "ai_register must be a typed mob_ai_control.MobAiRegister")
    if type(combat_ledger) is not mob_combat.CombatLedger:
        raise MobAiSchedulerError(
            REFUSE_TYPE_NOT_TYPED_RECORD,
            "combat_ledger must be a typed mob_combat.CombatLedger")

    # Constructing this once validates identity/position/alive the same way
    # mob_aggro.PlayerObservation always has; a bad caller input refuses here
    # with mob_aggro's own error, before any row is touched.
    player = mob_aggro.PlayerObservation(
        identity=player_identity, position=player_position,
        alive=player_alive,
    )

    register = ai_register
    results = []
    for identity in ai_register.identities():
        before_phase = register.state_of(identity).phase
        mob = register.mob_of(identity)
        balance = combat_ledger.balance_of(identity)
        observation = mob_aggro.MobObservation(
            position=(mob.x, mob.y, mob.z),
            hp=balance.current_hp,
            players=(player,),
        )
        step = mob_ai_control.tick_step(register, identity, observation)
        register = mob_ai_control.commit_step(register, step)
        results.append(SchedulerStepResult(
            actor_identity=identity,
            before_phase=before_phase,
            after_phase=step.after.phase,
            intent_kind=step.intent.kind,
            intent_target_identity=step.intent.target_identity,
        ))
    return register, tuple(results)


# The one line this lane owes the chief, written where a reader of the
# module finds it and not only in a PR body -- same convention
# mob_ai_control.MOB_AI_CONTROL_WIRING uses.  Deliberately NOT proposed as a
# concrete runtime.py line number this round: the honest call site is "some
# existing per-session dispatch that already runs often enough to feel live"
# (e.g. wherever TargetPosVital / last_target_pos already updates -- see
# runtime.py's own last_target_pos references), and naming the wrong one
# would cost the chief more than naming none.  See CORE-REQUEST in this
# round's letter for the question this line does not answer.
#
# [STALE as of round p05wire, COO-DECISION 20260901_0145][MEASURED, round
# bgwgso, 2026-09-01T16:39+07:00] this ask is fulfilled, not open: the chief
# wired the TARGET_POS_VITAL dispatch point (runtime.py:5196-5210, commit
# 5ac93b31) to lane_hooks.lane_b_mob_ai_tick.maybe_tick, which is exactly
# this string's own call shape (same four positional args this string names,
# read from self.mob_ai_register/self.mob_combat_ledger/self.foundation.
# selected/self.last_target_pos, with the result stored back onto
# self.mob_ai_register) -- just reached through the option-(b) wrapper this
# module's own header already named at the top of the file, rather than as a
# direct import.  The string below is left verbatim (not the literal diff
# that landed) because it is still an accurate description of the SHAPE of
# what runtime.py now does, and tests/test_mob_ai_scheduler.py pins its two
# substrings; do not delete them.
MOB_AI_SCHEDULER_WIRING = (
    "runtime.py: call mob_ai_scheduler.tick_session(self.mob_ai_register, "
    "self.mob_combat_ledger, <this connection's own player identity>, "
    "self.last_target_pos[:3] if self.last_target_pos else <no call: skip "
    "this tick, this session's own position is not known yet>, "
    "player_alive=True) from an EXISTING per-session dispatch point that "
    "already runs on a live cadence, and store the returned register back "
    "onto self.mob_ai_register the same way the existing damage_step/"
    "death_step call sites already do.  Composes no frame either way -- "
    "see this module's own NONCLAIMS -- so this line is safe to add without "
    "opening Door B (mob_aggro.ATTACK_INTENT_DELIVERABLE) in the same "
    "round."
)
