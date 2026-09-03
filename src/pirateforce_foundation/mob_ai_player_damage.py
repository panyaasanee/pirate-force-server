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
from typing import Any, Iterable, Optional, Tuple

from . import mob_aggro

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


#: DOOR B LIVES IN ITS OWN MODULE, AND THAT IS NOT A STYLE CHOICE.
#: `COO-DECISION 20260904_0045` point 3 named THIS file for the combat send
#: gate.  It is in `mob_hit_frame.py` instead, and the reason is measured,
#: not preferred: `tests/test_persistence_vitals_or_none.py`'s
#: `NothingComposesFromThisDoorTests` -- another lane's standing card, built
#: on the owner's ban of the guessed zero (`COO-DECISION 20260901_1059`,
#: "zero on the HP field means DEAD") -- goes RED for any single file that
#: both names `read_character_vitals_or_none` and hands anything to an
#: attribute composer.  This file names that door (`_read_vitals`), so a
#: composer in it turns that card red; the first draft of this round did
#: exactly that and the full suite caught it.  Splitting is not an evasion of
#: that card: the block Door B composes never comes from the vitals door at
#: all -- it comes from the chief's read point, through LANE-DB's own
#: adjudicator (`persistence_attr_compose.block_gaps`).  Reported to the COO
#: in this round's letter as a deviation from the file `0045` named.
#: See :mod:`pirateforce_foundation.mob_hit_frame`.
MOB_HIT_FRAME_MODULE = "pirateforce_foundation.mob_hit_frame"
