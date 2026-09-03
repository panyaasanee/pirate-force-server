"""LANE-B: the aggro tick's decision to attack becomes a number on disk.

WHY THIS MODULE EXISTS.  ``store.apply_hp_damage`` -- the DB half of M4, the
"hit it, kill it" milestone -- has had ZERO production callers since the day
LANE-DB landed it: grepped at HEAD in the round that wrote this file, every
occurrence outside ``store.py`` itself is a test or a docstring.  A door
nobody opens is not a feature, and COO-DECISION ``20260903_1745`` point 2
released the lock that was holding this shut ("start calling
``apply_hp_damage`` from the aggro tick the moment the tick gate at
``:5887`` is really open on ``main``"; it is -- ``server#668``, ticket 1648,
merged 2026-09-03T18:49+07:00, verified here as an ancestor of ``main``
rather than read off the letter).

WHAT THIS MODULE IS.  The join between two things that already exist and
have never been introduced: the per-row ``SchedulerStepResult`` tuple
``mob_ai_scheduler.tick_session`` already returns, and the store's damage
door.  One tick, one player, one write.

THE FOUR RULES THIS FILE IS BUILT AROUND, all four from
``COO-DECISION 20260903_1745`` point 2 and none of them optional:

1. A FLOOR OF 1 HP THAT IS NEVER BREACHED.  ``store.apply_hp_damage``
   floors at ZERO and reports ``died`` -- read it, it says so.  So the floor
   this lane was given is NOT the store's; it is enforced HERE, by clamping
   the amount to ``hp_current - HP_FLOOR`` before the call, and then by
   REFUSING LOUDLY if the outcome comes back at or below the floor anyway.
   A monster may not kill a player through this path, this round, at all.
2. READ BACK AFTER THE WRITE.  The ``DamageOutcome`` the store hands back
   is what the store believes; a second, independent read is what the
   database holds.  They disagreeing is a defect that must be heard, so it
   raises rather than logs (house rule: a write that reports success and
   does not land is a failure, never a log line).
3. A CONSOLE LINE, ASCII.  The bridge console is cp874 with strict errors --
   see :func:`console_safe`, same shape as ``mob_pickup_persist``'s.
4. ``store.py`` IS NOT TOUCHED.  Nothing here edits, wraps, monkeypatches or
   re-implements a store method; this module only calls two of them.

WHAT THE PLAYER WILL SEE DIFFERENTLY, STATED PLAINLY.  Nothing today, and
this file says why rather than letting a reader assume otherwise: the
caller that would pass a store into it does not exist yet.
``lane_b_mob_ai_tick.maybe_tick`` grew two OPTIONAL arguments for it
(``store``/``character_id``), both defaulting to ``None`` = "do not touch
the database", and ``runtime.py`` -- the chief's file -- still passes
neither.  The one line that changes that is in
``lane_b_mob_ai_tick.LANE_B_MOB_AI_TICK_WIRING``, written where a reader
finds it and not only in a PR body.  Until it lands, this module is a door
with a working lock and no one on the other side, and saying that plainly
is cheaper than a round spent discovering it.

WHEN IT DOES LAND, THE INPUT SET IS NOT EMPTY, AND THAT IS THIS ROUND'S
LOAD-BEARING MEASUREMENT.  The prose on ``main`` -- ``mob_aggro.py``'s own,
this lane's file -- says "every shipped roster is non-offensive, so on a
walk past an undamaged mob the tick returns a register equal to the one it
was given".  Driven on the real Bg0002 roster (the scene the owner plays
in) it is false, and the correction is written where the sentence is, not
only here:

    17 rows.  FIVE acquire a player by proximity (ai_wander 11:
    n_OFFESIVE = 1, n_AGGRO = 1200).  ONE of them -- placement 92,
    "Orc Chief", template 103, the only row of the five with a combat
    script -- produces INTENT_ATTACK_UNDELIVERABLE at every distance
    inside mob_ai_control.MELEE_ATTACK_RANGE (275.0), on EVERY tick,
    because mob_ai_control.ATTACK_CADENCE_TICKS is 1.

So the moment the order below is pasted, a player standing next to that one
monster loses :data:`PLAYER_DAMAGE_PER_ATTACK_DECISION` HP per TargetPos
frame they send, down to (never through) the floor.  THAT RATE IS WHY THE
ORDER IS ON HOLD and not merely written: it is one line for the chief to
paste and one letter for the COO to answer first, and this file is not
going to smuggle a rate nobody chose into a live dispatch.  See
:data:`MOB_AI_PLAYER_DAMAGE_WIRING`.

NONCLAIMS
---------
* NO claim that a monster attacks anybody today.  Nothing production calls
  this module: ``runtime.py`` passes no store, so the door is reachable and
  unopened.  What is measured is that its input set is NOT empty the moment
  it is opened -- the opposite of the "empty set" this file's first draft
  claimed on the strength of a sentence in a sibling docstring instead of a
  measurement.
* NO claim about a damage MODEL.  :data:`PLAYER_DAMAGE_PER_ATTACK_DECISION`
  is ONE, and it is [OUR DESIGN], not a mined column:
  ``field_mob_ai_tables``/``field_mob_tables*`` carry ``n_AGGRO``,
  ``n_OFFESIVE`` and a derived ``max_hp`` and NO attack-power column at all
  (grepped in the round that wrote this).  One is the smallest number that
  is not zero -- it makes the write real without inventing a formula, and
  with the floor above it can never be the number that kills anybody.
  [LANE-B assumption -- awaiting COO confirmation; see this round's letter.]
  The day an attack-power column is mined, this constant is what that
  round deletes, and the tests below pin the SHAPE (clamped, floored, read
  back), never the number 1 alone.
* [SUPERSEDED round 096evp, 2026-09-04 -- kept, not deleted, because it was
  true when it was written and a reader of an old letter will come looking
  for it] ~~NO claim that this composes a frame.  It sends nothing; the
  player's own client is not told its HP changed by anything in this file.
  A vital frame for that is a separate decision this lane has not been
  given.~~  The decision LANDED: ``COO-DECISION 20260904_0045`` gave this
  lane the caller for that frame, and it is the DOOR B section at the foot
  of this file.  What survives of the old sentence, unchanged and now
  enforced by a gate rather than by an absence: NOTHING THIS FILE COMPOSES
  REACHES A SOCKET.  See :data:`MOB_HIT_FRAME_CONFIRMED`.
* NO claim that this file sends anything.  It composes; it has no socket, no
  call site, and two shut gates.
* NO claim about a second player.  ``tick_session`` sees exactly one, so a
  write here is always against the character its caller named.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from . import mob_aggro
from .gm import attr_wire

# Same convention every other shippable module in this lane uses: True means
# "no scenario flag needed, safe for every connection".  There is nothing a
# flag could gate here that the caller's own two arguments do not already
# gate: pass no store and this module writes nothing.
production_allowed = True

MOB_AI_PLAYER_DAMAGE_LANE = "B_COMBAT"
# ASCII on purpose, and so is every other byte of this file: a constant can
# be interpolated into a console line one day, and the bridge console is
# cp874 with errors='strict'.  store.py's own damage door spells this
# milestone in Thai in its docstring; this file does not, so that no future
# reader has to decide which of its bytes are safe to print.
MOB_AI_PLAYER_DAMAGE_MILESTONE = "M4 (hit it, kill it), the HP-loss half"
MOB_AI_PLAYER_DAMAGE_ORIGIN = (
    "COO-DECISION 20260903_1745 point 2, unlocked by GT-216 passing on the "
    "owner's screen in R306 and by server#668 (ticket 1648) landing the "
    "tick gate on main"
)

#: The floor this lane may not write through.  NOT the store's floor -- the
#: store's is zero and reports a death; this one is a rule about what a
#: monster is allowed to do to a player in the round that first wires it.
HP_FLOOR = 1

#: [OUR DESIGN, LANE-B assumption -- awaiting COO] see the NONCLAIMS.
PLAYER_DAMAGE_PER_ATTACK_DECISION = 1

REFUSE_TYPE_NOT_TYPED_RECORD = "type_not_typed_record"
REFUSE_IDENTITY_NOT_POSITIVE = "identity_not_positive"
REFUSE_STORE_CANNOT_BE_ASKED = "store_cannot_be_asked"
REFUSE_VITALS_NOT_READABLE = "vitals_not_readable"
REFUSE_WRITE_DID_NOT_LAND = "write_did_not_land"
REFUSE_FLOOR_WAS_BREACHED = "floor_was_breached"

MOB_AI_PLAYER_DAMAGE_REFUSAL_REASONS = (
    REFUSE_TYPE_NOT_TYPED_RECORD,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_STORE_CANNOT_BE_ASKED,
    REFUSE_VITALS_NOT_READABLE,
    REFUSE_WRITE_DID_NOT_LAND,
    REFUSE_FLOOR_WAS_BREACHED,
)

#: The two refusals that are ENVIRONMENT, not programmer error: a character
#: whose vitals the database cannot resolve, and a store that raises when
#: asked.  These stand the write down and let the frame path live, because
#: this module runs inside a moving player's own dispatch and taking their
#: session down over an unseeded HP column would be a worse bug than the one
#: it reports.  Everything else RAISES -- most of all anything that happens
#: AFTER a write, which may never be swallowed.
#: NOT A REFUSAL AND DELIBERATELY NOT IN THE TUPLE ABOVE: the floor doing
#: all of the work is this lane behaving exactly as ordered, not a failure.
#: It is named anyway because it PRINTS, and a console reason a reader
#: cannot find in the source is a reason nobody can grep for.
STAND_DOWN_FLOOR_ALREADY_REACHED = "floor_already_reached"

MOB_AI_PLAYER_DAMAGE_STAND_DOWN_REASONS = (
    REFUSE_STORE_CANNOT_BE_ASKED,
    REFUSE_VITALS_NOT_READABLE,
)


class MobAiPlayerDamageError(ValueError):
    """A named refusal from this module.

    Deliberately not a subclass of ``mob_aggro.MobAiContractError`` or of
    ``persistence_vitals.VitalsError``: a caller reading this exception is
    reading a decision about THE WRITE, never about the AI decision that
    asked for it nor about the schema underneath.
    """

    def __init__(self, reason: str, detail: str) -> None:
        if reason not in MOB_AI_PLAYER_DAMAGE_REFUSAL_REASONS:
            raise AssertionError("unnamed refusal reason: %s" % reason)
        super().__init__("%s: %s" % (reason, detail))
        self.reason = reason


def console_safe(text: str) -> str:
    """ASCII, always, for a string this module did not compose.

    The bridge console is cp874 with ``errors='strict'``: one unmappable
    character in a ``print()`` raises, and the round-142 precedent in
    ``.github/workflows/gate-windows.yml`` is a tool that died having
    reported nothing.  The refusal line below interpolates ``%r`` of the
    STORE's exception, which can carry a Windows path with anything in it.
    Same shape as ``mob_pickup_persist.console_safe``.
    """
    return text.encode("ascii", "backslashreplace").decode("ascii")


@dataclass(frozen=True)
class PlayerDamageOutcome:
    """What one tick's attack decisions did to one player's stored HP.

    ``requested`` is what the decisions asked for and ``applied`` is what
    the floor allowed; they differ exactly when the floor did work, which is
    why ``floor_held`` is derived from them rather than declared.
    """

    character_id: int
    attackers: Tuple[int, ...]
    requested: int
    applied: int
    hp_before: int
    hp_after: int
    hp_max: int

    @property
    def floor_held(self) -> bool:
        return self.applied < self.requested


def attack_decisions(results: Iterable[Any]) -> Tuple[int, ...]:
    """The actor identities in ``results`` that decided to attack, in order.

    Reads ``intent_kind`` against ``mob_aggro.INTENT_ATTACK_UNDELIVERABLE``
    -- the constant, never a copy of its spelling, because a hand-typed
    literal here is exactly the defect that kept the tick gate shut for
    three days (``COO-DECISION 20260903_1647``).

    Order is the caller's: ``tick_session`` returns rows in ascending
    identity order and this function does not re-sort, so a reader of the
    console line sees the same order the register was walked in.
    """
    identities = []
    for result in results:
        kind = getattr(result, "intent_kind", None)
        if type(kind) is not str:
            raise MobAiPlayerDamageError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "result has no str intent_kind: %r" % (result,))
        if kind != mob_aggro.INTENT_ATTACK_UNDELIVERABLE:
            continue
        actor = getattr(result, "actor_identity", None)
        if type(actor) is not int or isinstance(actor, bool) or actor <= 0:
            raise MobAiPlayerDamageError(
                REFUSE_IDENTITY_NOT_POSITIVE,
                "actor_identity=%r" % (actor,))
        identities.append(actor)
    return tuple(identities)


def damage_console_line(outcome: PlayerDamageOutcome) -> str:
    """The one line a tester greps for, derived from the outcome only."""
    return console_safe(
        "MOB_AI_PLAYER_DAMAGE char=%d attackers=%d requested=%d applied=%d "
        "hp=%d->%d/%d floor_held=%d"
        % (
            outcome.character_id, len(outcome.attackers), outcome.requested,
            outcome.applied, outcome.hp_before, outcome.hp_after,
            outcome.hp_max, 1 if outcome.floor_held else 0,
        )
    )


def stand_down_console_line(reason: str, character_id: Any,
                            detail: str) -> str:
    """The line printed instead of a write, when the environment refuses.

    Silence here would be the whole defect this lane keeps paying for: a
    door that declines is indistinguishable from a door nobody opened
    unless it says so.
    """
    return console_safe(
        "MOB_AI_PLAYER_DAMAGE_STAND_DOWN reason=%s char=%r detail=%s"
        % (reason, character_id, detail)
    )


def _require_character_id(character_id: Any) -> int:
    if type(character_id) is not int or character_id <= 0:
        raise MobAiPlayerDamageError(
            REFUSE_IDENTITY_NOT_POSITIVE,
            "character_id=%r" % (character_id,))
    return character_id


def _read_vitals(store: Any, character_id: int):
    """This character's vitals, or a named stand-down.

    Returns ``(vitals, None)`` or ``(None, reason)``; never raises for the
    ordinary "not seeded yet" case, which
    ``store.read_character_vitals_or_none`` already reports as ``None``.
    """
    try:
        vitals = store.read_character_vitals_or_none(character_id)
    except Exception as exc:  # the store's own errors, not this lane's
        return None, (REFUSE_STORE_CANNOT_BE_ASKED, "%r" % (exc,))
    if vitals is None:
        return None, (REFUSE_VITALS_NOT_READABLE,
                      "read_character_vitals_or_none returned None")
    for name in ("hp_current", "hp_max"):
        value = getattr(vitals, name, None)
        if type(value) is not int:
            return None, (REFUSE_VITALS_NOT_READABLE,
                          "%s=%r" % (name, value))
    return vitals, None


def apply_tick_damage(
    store: Any,
    character_id: int,
    results: Iterable[Any],
    per_attack: int = PLAYER_DAMAGE_PER_ATTACK_DECISION,
) -> Optional[PlayerDamageOutcome]:
    """Turn one tick's attack decisions into one clamped, floored,
    read-back HP write, and print the line that proves it happened.

    Returns the :class:`PlayerDamageOutcome` when a write landed, and
    ``None`` when there was nothing to do (no attack decision this tick) or
    when the environment stood the write down (a named line is printed for
    the second case and nothing at all for the first -- a tick with no
    attacker is the common case and must not flood the console).

    Raises :class:`MobAiPlayerDamageError` for a contract violation, and --
    the important half -- for anything wrong AFTER the write: a read-back
    that disagrees with the store's own outcome, or an HP BELOW
    :data:`HP_FLOOR`.  Neither may be logged and continued.  Landing exactly
    ON the floor is the clamp working and is not an error; an earlier draft
    of this paragraph said "at or below", which described a module that
    would raise on its own success path (pf-adversary D10).
    """
    character_id = _require_character_id(character_id)
    if type(per_attack) is not int or per_attack < 1:
        raise MobAiPlayerDamageError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "per_attack=%r" % (per_attack,))

    attackers = attack_decisions(results)
    if not attackers:
        return None

    vitals, stand_down = _read_vitals(store, character_id)
    if stand_down is not None:
        reason, detail = stand_down
        print(stand_down_console_line(reason, character_id, detail))
        return None

    hp_before = vitals.hp_current
    hp_max = vitals.hp_max
    requested = len(attackers) * per_attack
    headroom = hp_before - HP_FLOOR
    applied = requested if requested < headroom else headroom
    if applied <= 0:
        # The floor did ALL of the work.  No write at all -- clamping to
        # zero and calling the door anyway would put a no-op transaction on
        # the write lock of a strictly serial server (FINDINGS_R18) once per
        # frame per attacking monster, for nothing.
        print(stand_down_console_line(
            STAND_DOWN_FLOOR_ALREADY_REACHED, character_id,
            "hp=%d floor=%d requested=%d" % (hp_before, HP_FLOOR, requested)))
        return None

    # THE WRITE IS WRAPPED AND THE READ-BACK IS NOT, AND THAT ASYMMETRY IS
    # THE POINT (pf-adversary D7).  A raise out of `apply_hp_damage` means
    # the transaction did not commit: `_begin_immediate_for_damage` gives up
    # after DAMAGE_LOCK_BUSY_TIMEOUT_MS with nothing opened, which happens on
    # this strictly serial server whenever a healing door (which may hold the
    # same lock for up to HEAL_LOCK_TOTAL_WAIT_S) is in flight.  So it is an
    # ENVIRONMENT refusal like the read above: no HP moved, stand down by
    # name.  Letting it propagate would take a walking player's dispatch down
    # -- and worse, it would skip runtime.py's own close of the GM warp
    # confirm window a few lines below the call site, latching state past its
    # frame.  Anything AFTER a committed write still raises; see below.
    try:
        outcome = store.apply_hp_damage(character_id, applied)
    except Exception as exc:  # the store's own errors, not this lane's
        print(stand_down_console_line(
            REFUSE_STORE_CANNOT_BE_ASKED, character_id,
            "the damage door refused the write (nothing committed): %r"
            % (exc,)))
        return None

    if outcome.hp_after < HP_FLOOR or outcome.died:
        raise MobAiPlayerDamageError(
            REFUSE_FLOOR_WAS_BREACHED,
            "hp_after=%r died=%r floor=%d applied=%d"
            % (outcome.hp_after, outcome.died, HP_FLOOR, applied))

    after, stand_down = _read_vitals(store, character_id)
    if stand_down is not None:
        # A read that fails AFTER a write is not the ordinary unseeded case
        # this module stands down for; the row was readable one line ago.
        raise MobAiPlayerDamageError(
            REFUSE_WRITE_DID_NOT_LAND,
            "read-back refused after the write: %s" % (stand_down[1],))
    if after.hp_current != outcome.hp_after:
        raise MobAiPlayerDamageError(
            REFUSE_WRITE_DID_NOT_LAND,
            "store said hp_after=%d, the database holds %d"
            % (outcome.hp_after, after.hp_current))

    landed = PlayerDamageOutcome(
        character_id=character_id,
        attackers=attackers,
        requested=requested,
        applied=applied,
        hp_before=outcome.hp_before,
        hp_after=after.hp_current,
        hp_max=hp_max,
    )
    print(damage_console_line(landed))
    return landed


#: The one line this lane owes the chief, written where a reader of the
#: module finds it and not only in a PR body -- the same convention
#: ``mob_ai_scheduler.MOB_AI_SCHEDULER_WIRING`` uses, and the same one whose
#: HAND-TYPED GATE ARGUMENT cost three days (COO-DECISION 20260903_1647).
#: So this order names attributes, not spellings, wherever it can.
#: ON HOLD -- NOT A LINE TO PASTE THIS ROUND.  ASCII marker below so a
#: grep finds it: MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD.  The door is built,
#: tested and floored, and the rate it would run at is measured rather than
#: assumed (module docstring): one HP per TargetPos frame for a player
#: inside 275 units of Bg0002 placement 92, because that roster row is
#: offensive and the cadence constant is 1.  Grinding a player to 1 HP with
#: no frame telling them is not a decision this lane may take alone, so the
#: order below WENT to the COO with three options in round nfrrqa's letter
#: (throttle in this lane / cadence from a mined column / wire as is).
#:
#: ANSWERED, round `5pvte3`, 2026-09-04: COO-DECISION 20260903_2050 (cc
#: chief) rejected options 1 and 2 outright and left option 3 open only on
#: a condition neither this module nor the `1952` letter had named yet --
#: the write may go live ONLY together with a frame the player actually
#: sees land (``UpdateAttrVital``, the same frame LANE-GM's RE-222 was
#: already decoding).  RE-222 answered PARTIAL the same night: its Q0 gives
#: the exact ``UpdateAttrVital``/``ActorAttr`` wire container and proves
#: the apply path is a FULL-OBJECT COPY -- any BasicAttr/ActorAttr field
#: this lane's frame omits reverts to the fresh constructor's zero, which
#: is what zeroed GT-218's cash and HP-max.
#:
#: WHAT "PREPARE DOOR B" (the COO's own next-step wording) NEEDS, AND WHERE
#: IT ALREADY LIVES: the byte offset and presence-mask bit for
#: hp_current/hp_max/mp_current/mp_max inside BasicAttr.  This round found
#: it is NOT an open research question -- it is already named, as
#: ``known=True`` rows, in ``gm/attr_wire.FIELDS`` (LANE-GM's module, rows
#: 3-6: mask 0x0004/offset 0x044 hp_current, 0x0008/0x048 hp_max,
#: 0x0010/0x04C mp_current, 0x0020/0x050 mp_max), sourced from the owner's
#: own live ``PF_ADHOC_ATTR_PROBE`` run (266 commands, one connection, no
#: crash) rather than a static guess.  What is NOT true yet, checked the
#: ANSWERED IN FULL, round `096evp`, 2026-09-04: `COO-DECISION 20260904_0045`
#: closed the cross-lane question below.  ONE encoder, `gm/attr_wire.py`,
#: and LANE-B is its CALLER (option (b), a narrower LANE-B encoder, was
#: rejected outright).  The caller is the DOOR B section at the foot of this
#: file.  THE HOLD ON THIS ORDER DOES NOT LIFT WITH IT, and the reason is
#: now two named gates instead of an unanswered question: the frame cannot
#: leave until LANE-GM opens `attr_wire`'s full-block unlock (b') AND this
#: lane sets :data:`MOB_HIT_FRAME_CONFIRMED`, and a live HP write with no
#: frame the player sees is exactly what `20260903_2050` forbids.  So the
#: two paragraphs below are HISTORY, not the current state: they describe
#: the question, and `0045` is the answer.
#:
#: [SUPERSEDED -- the open cross-lane question, kept for the reader of an
#: older letter] ~~which lane's encoder this door calls is an architecture
#: question this lane has not been given and has not decided~~ -- decided,
#: see above.
#:
#: same round: that module's own send gate,
#: ``gm.attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED``, is locked to every
#: caller except one scoped exception (``/speed`` sparse x=7 only,
#: COO-DECISION 2026-09-01T18:47+07:00), and that module's own docstring
#: says its 3-point unlock condition (b) -- lossless preservation of every
#: UNNAMED field -- is still open.  So this is not an RE gap, it is a
#: CROSS-LANE ONE: whether combat damage reuses ``gm/attr_wire.py``'s
#: encoder (and inherits its still-open unlock condition) or LANE-B builds
#: an independent, narrower encoder against the same four named rows is an
#: architecture question this lane has not been given and has not decided.
#: See this round's letter to COO. ~~[LANE-B assumption -- awaiting COO; not
#: an RE ticket, because the RE fact already exists and is cited above.]~~
#: TAG WITHDRAWN round `096evp`: the COO answered on 2026-09-04T00:45 and
#: the answer is recorded above; an "awaiting COO" tag left standing over an
#: answered question is a reader being told to wait for a letter that has
#: already arrived.
#:
#: BOTH EXPRESSIONS BELOW WERE READ OUT OF runtime.py, NOT COMPOSED: the
#: store is fetched exactly as the pickup branch already fetches it
#: (runtime.py:7278-7279) and the id is the one that branch names as the
#: selected character's (runtime.py:8416, ``self.foundation.selected.id`` --
#: ``.id``, not ``.character_id``, which does not exist on that record).
MOB_AI_PLAYER_DAMAGE_WIRING = (
    "MOB_AI_PLAYER_DAMAGE_WIRING_ON_HOLD -- do not paste this line until "
    "a Door B send path exists that fires UpdateAttrVital carrying the "
    "full current BasicAttr/ActorAttr state (COO-DECISION 20260903_2050). "
    "The field layout is not missing -- gm/attr_wire.FIELDS rows 3-6 "
    "already name hp_current/hp_max/mp_current/mp_max's offset and mask -- "
    "but that module's own send gate and its open lossless-preservation "
    "condition are LANE-GM's.  WHICH LANE'S ENCODER IS NO LONGER OPEN: "
    "COO-DECISION 20260904_0045 says gm/attr_wire.py, called by this lane, "
    "and mob_ai_player_damage.compose_player_hit_frame is that caller.  What "
    "still holds this order shut is the two gates that caller reads -- "
    "LANE-GM's attr_wire full-block unlock and this lane's own "
    "MOB_HIT_FRAME_CONFIRMED, both closed at this commit"
    "; the rate it would run at is measured, not chosen (one HP per "
    "TargetPos frame for a player inside 275 units of Bg0002 placement 92, "
    "with no frame telling them). "
    "runtime.py dispatch(self, parsed), the existing lane_b_mob_ai_tick."
    "maybe_tick call: add the two optional arguments it already accepts -- "
    "store=getattr(getattr(self.foundation, 'lifecycle', None), 'store', "
    "None), character_id=self.foundation.selected.id -- so a monster's "
    "attack decision becomes a persisted HP loss.  Nothing else about that "
    "call site changes: the return shape is the same (register, results) "
    "pair, no frame is composed, and passing neither argument (today) "
    "writes nothing.  A None store is refused BY NAME as "
    "store_cannot_be_asked, never crashed on.  The floor of "
    "mob_ai_player_damage.HP_FLOOR is enforced inside this lane, so this "
    "line cannot kill a player."
)


# ===========================================================================
# DOOR B -- the frame that tells the player their HP moved
# ===========================================================================
#
# WHAT THIS HALF IS FOR.  Everything above this line moves a NUMBER IN THE
# DATABASE and says so on the console.  A player staring at the client sees
# none of it: `COO-DECISION 20260903_2050` is explicit that the live HP write
# may only go live TOGETHER with a frame they actually see land, and this
# section is that frame's composer -- the "Door B" the COO named.
#
# WHO OWNS WHAT, DECIDED AND NOT ASSUMED.  Round `5pvte3` routed one
# architecture question to the COO (does combat reuse `gm/attr_wire.py`'s
# encoder, or does LANE-B build a narrower one against the same four rows?)
# and `COO-DECISION 20260904_0045` answered it in as many words:
#
#   1. opcode 0x309A has exactly ONE encoder in this repository,
#      `gm/attr_wire.py`, owned by LANE-GM.  LANE-B is a CALLER.  Option (b),
#      a narrow LANE-B encoder, was rejected outright -- two lanes holding
#      two encoders for one opcode is two future bug sets.
#   2. combat does NOT inherit the `/speed` sparse-x=7 exception of
#      `COO-DECISION 2026-09-01T18:47+07:00`.  `GT-218` proved that exception
#      kills the client in one frame (HP `0/1`, cash `0`, death dialog), so
#      it may not become anybody's precedent.  A hit frame is FULL BLOCK or
#      it is nothing.
#   3. the bytes may leave only when BOTH gates are true: LANE-GM's own
#      unlock of `attr_wire` AND this lane's own constant below.  Either lane
#      flipping its own gate must not put the other lane's bytes on a socket.
#
# WHY FULL BLOCK, IN ONE SENTENCE, WITH ITS SOURCE.  `RE-222` (static,
# SHA-pinned, LANE-GM, 2026-09-03) established that the client's apply path
# for 0x309A is a FULL-OBJECT COPY: every BasicAttr/ActorAttr field the frame
# omits comes back as the fresh constructor's zero.  A hit frame carrying
# `hp_current` alone would therefore zero the player's cash and HP-max --
# which is precisely, and not by analogy, what happened on the owner's screen
# in `GT-218`.
#
# NONCLAIMS FOR THIS HALF
# -----------------------
# * NO claim that anything sends.  :data:`MOB_HIT_FRAME_CONFIRMED` is `None`
#   and there is no call site: `grep -rn "compose_player_hit_frame" src/`
#   finds this file and nothing else.  The gate is checked BEFORE the first
#   byte is built, so "gate is None" and "zero bytes" are the same statement
#   rather than two hopeful ones (`HitFrameGateMutantTests`).
# * NO claim that the live-value read point exists.  It does not, at the
#   commit that writes this: `lane_hooks.current_named_attr_values` was
#   ordered from the chief in `COO-DECISION 20260904_0047` point 1 and is
#   not on `main` yet -- grepped, whole repo, in this round.  Until it lands
#   this door stands down BY NAME, which is the behaviour the COO asked for
#   in `0045` point 4 and not a fallback this lane chose.
# * NO claim that this closes `attr_wire`'s unlock condition (b'), and one
#   measurement says it CANNOT: the read point carries `known=True` rows
#   only (`0047` point 1 names exactly those), while (b') also governs the
#   UNNAMED rows, whose bytes come from the owner's own probe.  So the
#   chief's hook landing does not by itself open gate (i); LANE-GM still has
#   to flip its own, and this lane cannot do it for them.
# * NO claim about a damage MODEL or a rate.  Nothing in this half chooses a
#   number; `hp_after` is an argument, and the only value it is ever meant to
#   carry is one this module already read back out of the database.

#: LANE-B'S OWN SEND GATE for the hit frame -- gate (ii) of
#: `COO-DECISION 20260904_0045` point 3.  Same shape as
#: `gm/attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED` and
#: `gm/teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED`: `None` means no
#: frame this lane composes may reach a real socket, an `int` means a
#: measured vital_version byte AND a COO-approved flip.
#:
#: THE ONE THING THAT FLIPS IT, quoted from `0045` so nobody has to go and
#: find the letter: a single GT ticket on the owner's own screen -- one
#: monster hits her once, HP drops by exactly the value this module read
#: back, and cash / HP-max / MP do not move.  The STOP-on-HP-0 rule applies.
#: `pf-queue-author` writes that ticket only once this caller is on `main`.
MOB_HIT_FRAME_CONFIRMED: Optional[int] = None

#: Gate (i) is LANE-GM's and is read, never guessed at.  It is deliberately
#: NOT `attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED`: that constant is
#: already `0`, but only because of the scoped `/speed` exception that
#: `0045` point 2 forbids this lane from inheriting.  Reading it here would
#: be this lane quietly taking a permission that was granted to one other
#: door.  So the gate this half reads is a SEPARATE attribute that
#: `gm/attr_wire.py` does not define today -- absent means locked, which is
#: fail-closed by construction -- and the request for LANE-GM to define it
#: when their (b') unlock lands goes out as this round's letter.
#: [LANE-B assumption -- awaiting COO confirmation]
ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR = "FULL_BLOCK_UNLOCK_CONFIRMED"

#: The chief's read point, by name, resolved at call time and never imported
#: at module scope: it does not exist yet, and a module-scope import of a
#: name that is not there is an ImportError in a walking player's dispatch.
LIVE_ATTR_VALUES_HOOK_ATTR = "current_named_attr_values"

#: The four rows a hit frame is ABOUT, named rather than numbered.  The `x`
#: numbers and byte offsets live in exactly one place (`attr_wire.FIELDS`)
#: and are looked up through :func:`hit_frame_vital_rows` -- so the day
#: LANE-GM renames one of them, this lane's tests go red and somebody has to
#: come and say what changed, instead of a silently mis-encoded frame.
HIT_FRAME_VITAL_FIELD_NAMES = ("hp_current", "hp_max", "mp_current", "mp_max")

#: The one row a hit CHANGES.  The other three are carried at their live
#: value so the full-object copy does not zero them.
HIT_FRAME_CHANGED_FIELD_NAME = "hp_current"

STANDDOWN_GATE_NOT_CONFIRMED = "gate_not_confirmed"
STANDDOWN_ENCODER_LOCKED = "encoder_locked"
STANDDOWN_NO_LIVE_SOURCE = "no_live_source"
STANDDOWN_LIVE_SOURCE_REFUSED = "live_source_refused"
STANDDOWN_LIVE_SOURCE_INCOMPLETE = "live_source_incomplete"
STANDDOWN_LIVE_SOURCE_UNNAMED_ROW = "live_source_unnamed_row"

MOB_HIT_FRAME_STAND_DOWN_REASONS = (
    STANDDOWN_GATE_NOT_CONFIRMED,
    STANDDOWN_ENCODER_LOCKED,
    STANDDOWN_NO_LIVE_SOURCE,
    STANDDOWN_LIVE_SOURCE_REFUSED,
    STANDDOWN_LIVE_SOURCE_INCOMPLETE,
    STANDDOWN_LIVE_SOURCE_UNNAMED_ROW,
)


def hit_frame_stand_down_line(reason: str, character_id: Any,
                              detail: str) -> str:
    """The line printed instead of a frame, ASCII, greppable.

    `COO-DECISION 20260904_0045` point 4 spells the missing-read-point case
    literally -- ``MOB_HIT_FRAME_STANDDOWN reason=no_live_source`` -- so the
    prefix and the first key are that letter's, not this lane's invention,
    and the other five reasons are spelled the same way for one grep.
    """
    if reason not in MOB_HIT_FRAME_STAND_DOWN_REASONS:
        raise AssertionError("unnamed stand-down reason: %s" % reason)
    return console_safe(
        "MOB_HIT_FRAME_STANDDOWN reason=%s char=%r detail=%s"
        % (reason, character_id, detail)
    )


def hit_frame_vital_rows() -> Dict[str, int]:
    """``{name: x}`` for :data:`HIT_FRAME_VITAL_FIELD_NAMES`, from
    ``attr_wire.BY_NAME`` -- the encoder's own table, never a copy.

    Raises :class:`MobAiPlayerDamageError` when a name has gone or has
    stopped being `known=True`, because both mean the same thing for this
    door: the row this lane thought it was carrying is not the row the
    encoder would encode.
    """
    rows: Dict[str, int] = {}
    for name in HIT_FRAME_VITAL_FIELD_NAMES:
        field = attr_wire.BY_NAME.get(name)
        if field is None:
            raise MobAiPlayerDamageError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "attr_wire.FIELDS no longer names a row %r" % (name,))
        if not field[7]:
            raise MobAiPlayerDamageError(
                REFUSE_TYPE_NOT_TYPED_RECORD,
                "attr_wire row %r is no longer known=True" % (name,))
        rows[name] = field[0]
    return rows


def _resolve_live_attr_values(lane_hooks_module: Any = None) -> Any:
    """The chief's read point, or ``None`` when it is not on this tree.

    Import failure and attribute absence collapse to the same answer on
    purpose: from this door's side "the hook module blew up" and "the hook
    is not written yet" are both "there is no live source", and both must
    stand the frame down rather than raise inside a player's dispatch.
    """
    module = lane_hooks_module
    if module is None:
        try:
            from . import lane_hooks as module  # type: ignore[no-redef]
        except Exception:
            return None
    hook = getattr(module, LIVE_ATTR_VALUES_HOOK_ATTR, None)
    return hook if callable(hook) else None


def hit_frame_encoder_unlocked() -> bool:
    """Gate (i): has LANE-GM opened `attr_wire`'s full-block unlock?

    Absent attribute (today) and `None` both mean locked.  See
    :data:`ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR` for why this is not the
    `/speed` constant.
    """
    return getattr(attr_wire, ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR, None) is not None


def _named_known_rows() -> Dict[int, str]:
    return {f[0]: f[6] for f in attr_wire.FIELDS
            if f[7] and f[0] not in attr_wire.SENSITIVE_FIELDS}


def compose_player_hit_frame(
    legacy: Any,
    character_id: int,
    identity_lo: int,
    identity_hi: int,
    hp_after: int,
    lane_hooks_module: Any = None,
) -> Optional[Tuple[bytes, bytes]]:
    """The ``UpdateAttrVital`` a hit would send -- composed, never sent.

    Returns ``(pc, frame)`` when both gates are open and the chief's read
    point handed over a live block, and ``None`` -- after printing one named
    :func:`hit_frame_stand_down_line` -- in every other case.  Today every
    call returns ``None`` at the first check.

    The order of the checks is load-bearing and is the order of `0045`:
    THIS LANE'S gate first, then LANE-GM's, then the values.  A reader of a
    stand-down line learns which lane owes the next move, and no byte is
    built by a tree whose own gate is shut.

    ``hp_after`` is the number the caller READ BACK out of the database
    (:func:`apply_tick_damage` returns it as ``PlayerDamageOutcome.hp_after``)
    -- this function does not compute damage, does not look at the store, and
    will not accept a value below :data:`HP_FLOOR`, so the frame can never
    tell a client something this lane is forbidden to write.
    """
    character_id = _require_character_id(character_id)
    if type(hp_after) is not int or isinstance(hp_after, bool):
        raise MobAiPlayerDamageError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "hp_after=%r" % (hp_after,))
    if hp_after < HP_FLOOR:
        raise MobAiPlayerDamageError(
            REFUSE_FLOOR_WAS_BREACHED,
            "hp_after=%d is below floor=%d" % (hp_after, HP_FLOOR))

    if MOB_HIT_FRAME_CONFIRMED is None:
        print(hit_frame_stand_down_line(
            STANDDOWN_GATE_NOT_CONFIRMED, character_id,
            "MOB_HIT_FRAME_CONFIRMED is None (COO-DECISION 20260904_0045 "
            "point 3 gate ii)"))
        return None

    if not hit_frame_encoder_unlocked():
        print(hit_frame_stand_down_line(
            STANDDOWN_ENCODER_LOCKED, character_id,
            "gm.attr_wire.%s is not set (LANE-GM unlock b')"
            % (ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR,)))
        return None

    hook = _resolve_live_attr_values(lane_hooks_module)
    if hook is None:
        print(hit_frame_stand_down_line(
            STANDDOWN_NO_LIVE_SOURCE, character_id,
            "lane_hooks.%s is not on this tree (COO-DECISION 20260904_0047 "
            "point 1)" % (LIVE_ATTR_VALUES_HOOK_ATTR,)))
        return None

    try:
        live = hook(character_id)
    except Exception as exc:  # the hook's own errors, not this lane's
        print(hit_frame_stand_down_line(
            STANDDOWN_LIVE_SOURCE_REFUSED, character_id, "%r" % (exc,)))
        return None
    if not isinstance(live, dict) or not live:
        print(hit_frame_stand_down_line(
            STANDDOWN_NO_LIVE_SOURCE, character_id,
            "the read point returned %r" % (live,)))
        return None

    known = _named_known_rows()
    unnamed = sorted(x for x in live if x not in known)
    if unnamed:
        # `0047` point 1 forbids the read point to guess or to fill a row
        # with 0; a key this encoder does not name as known is either a
        # guess or a row the encoder itself would refuse, and either way
        # this door does not launder it into a frame.
        print(hit_frame_stand_down_line(
            STANDDOWN_LIVE_SOURCE_UNNAMED_ROW, character_id,
            "rows not known=True in attr_wire.FIELDS: %r" % (unnamed,)))
        return None

    rows = hit_frame_vital_rows()
    missing = sorted(name for name, x in rows.items() if x not in live)
    if missing:
        print(hit_frame_stand_down_line(
            STANDDOWN_LIVE_SOURCE_INCOMPLETE, character_id,
            "the read point has no value for %r" % (missing,)))
        return None

    # The cache is the encoder's OWN baseline object and it is seeded with
    # the live block, never with a synthesized one -- that is the single
    # unconditional guarantee `attr_wire`'s docstring ships, and this caller
    # keeps it rather than working around it.  One instance per compose: a
    # cache that outlived a frame would be this lane holding a second copy
    # of the player's state, which is the whole class of bug `0045` point 1
    # refused.
    cache = attr_wire.RawBlockCache()
    cache.capture_initial(dict(live))
    return attr_wire.build_named_field_update(
        legacy, cache, identity_lo, identity_hi,
        rows[HIT_FRAME_CHANGED_FIELD_NAME], hp_after,
    )
