"""LANE-B, DOOR B: the frame that would tell a player their HP moved.

WHAT THIS MODULE IS FOR.  ``mob_ai_player_damage`` moves a NUMBER IN THE
DATABASE and prints a console line.  A player staring at the client sees
none of it, and ``COO-DECISION 20260903_2050`` is explicit that the live HP
write may only go live TOGETHER with a frame they actually see land.  This
module is that frame's COMPOSER -- the "Door B" the COO named -- and today
it composes nothing at all, by four independent named refusals.

WHO OWNS WHAT, DECIDED AND NOT ASSUMED.  Round ``5pvte3`` routed one
architecture question to the COO (does combat reuse ``gm/attr_wire.py``'s
encoder, or does LANE-B build a narrower one against the same four rows?)
and ``COO-DECISION 20260904_0045`` answered it: LANE-B is a CALLER of
``gm/attr_wire.py``; a narrow LANE-B encoder was rejected outright; the
``/speed`` sparse-x=7 exception is NOT inherited (``GT-218`` proved it kills
the client in one frame, so it may not become anybody's precedent); and the
bytes may leave only when BOTH lanes' gates are open.

WHY THIS IS NOT IN ``mob_ai_player_damage.py``, WHICH IS THE FILE ``0045``
NAMED.  Measured, not preferred:
``tests/test_persistence_vitals_or_none.py::NothingComposesFromThisDoorTests``
-- another lane's standing card, built on the owner's ban of the guessed
zero (``COO-DECISION 20260901_1059``: on the HP field, zero means DEAD) --
goes red for any ONE FILE that both names ``read_character_vitals_or_none``
and hands anything to an attribute composer.  That file names the vitals
door; this round's first draft put the composer beside it and the full suite
caught it.  The split is not an evasion of that card, because the thing the
card protects is provenance and the provenance here is different: the block
this module composes never comes from the vitals door.  It comes from the
chief's read point, and it may only be composed at all once LANE-DB's own
adjudicator says every row in it has an honest value.  Reported to the COO
as a deviation from the file ``0045`` named.

THE FOUR GATES, IN THE ORDER THEY ARE CHECKED
---------------------------------------------
1. :data:`MOB_HIT_FRAME_CONFIRMED` -- THIS LANE'S, gate (ii) of ``0045``
   point 3.  ``None`` today.
2. ``gm/attr_wire``'s full-block unlock -- LANE-GM'S, gate (i).  Absent
   today.  Deliberately NOT ``UPDATE_ATTR_VITAL_VERSION_CONFIRMED``, which is
   already ``0`` but only from the scoped ``/speed`` exception ``0045``
   point 2 forbids this lane from inheriting.
3. A SESSION ``RawBlockCache``, handed in by a caller.  ``attr_wire``'s own
   docstring says one instance per CONNECTION, held on the session object,
   "so the NEXT command in this connection builds on real prior state, not a
   second guess".  This module will not manufacture one: a per-compose cache
   would mean two copies of the player's state on one connection, and the
   next ``/lv`` would re-assert the HP this frame just changed
   (pf-adversary D6, which measured exactly that on the first draft).
4. LANE-DB'S ADJUDICATOR.  ``persistence_attr_compose.block_gaps`` is the
   in-repo module that already answers "may the server put a value in a
   0x309A block at all", and at this commit it answers NO for all 55 rows.
   Nothing here overrides it or reimplements it.

WHY "FULL BLOCK" IS A REQUIREMENT AND NOT A PREFERENCE.  ``RE-222`` (static,
SHA-pinned, LANE-GM) established that the client's apply path for 0x309A is
a FULL-OBJECT COPY: every field the frame omits comes back as the fresh
constructor's zero.  A hit frame carrying ``hp_current`` alone would zero
the player's cash and HP-max -- which is not an analogy for ``GT-218``, it
is what ``GT-218`` was.  So this module composes a 55-row block or it
composes nothing, and "55" is enforced by the adjudicator above rather than
by a count written here.

NONCLAIMS
---------
* NO claim that anything sends, or can.  All four gates are shut at this
  commit and there is no call site anywhere in ``src/``
  (``test_nothing_calls_this_door_yet`` derives that from the tree, and the
  ``.pyc`` files a naive grep also matches are not the claim).
* NO claim that this closes ``attr_wire``'s unlock condition (b'), and one
  measurement says it cannot: the chief's read point carries ``known=True``
  rows only (``COO-DECISION 20260904_0047`` point 1 names exactly those),
  while (b') also governs the UNNAMED rows, whose bytes come from the
  owner's own probe.  The chief's hook landing does not by itself open gate
  (i).
* NO claim that the ordered read-point SIGNATURE can carry this block.
  ``0047`` point 1 types it ``dict[int, int|float]``, and two ``known=True``
  rows are ``wstr`` (x=1 ``name``, x=37 ``wstr_164_guild``): an int for
  either is an encoder error, and omitting them blanks the player's name and
  guild on their own client.  Measured by pf-adversary D3 against the first
  draft, reported to the COO and the chief in this round's letters, and
  handled here only in the sense that an encoder refusal is a named stand-
  down rather than an exception in a walking player's dispatch.
* NO claim about a damage MODEL or a rate.  Nothing here chooses a number;
  ``hp_after`` is an argument, and the only value it is meant to carry is
  one ``mob_ai_player_damage`` already read back out of the database.
* NO claim that ``0045``'s "0x309A has exactly ONE encoder in this
  repository" is a measured property of this tree.  It is not -- pf-adversary
  D8 named three other in-tree composers for that opcode, and this round's
  file and letter name them (they are NOT named here on purpose: two of the
  three carry containment cards that scan for their own module name as a
  SUBSTRING across `src/`, so writing them into this docstring turns another
  lane's card red for a sentence.  Measured: it did, in this round's second
  full-suite run).  ``0045`` is a FORWARD POLICY about which encoder THIS
  door calls, and this module obeys it as one.
"""
from __future__ import annotations

import struct
from typing import Any, Dict, Optional, Tuple

from . import persistence_attr_compose
from .gm import attr_wire
from .mob_ai_player_damage import (
    HP_FLOOR,
    MobAiPlayerDamageError,
    REFUSE_FLOOR_WAS_BREACHED,
    REFUSE_IDENTITY_NOT_POSITIVE,
    REFUSE_TYPE_NOT_TYPED_RECORD,
    console_safe,
)

# Nothing a scenario flag could gate here that the four gates below do not
# already gate harder.  Same convention as every other shippable module in
# this lane.
production_allowed = True

#: LANE-B'S OWN SEND GATE -- gate (ii) of ``COO-DECISION 20260904_0045``
#: point 3.  Same shape as ``gm/attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED``
#: and ``gm/teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED``: ``None`` means
#: no frame this lane composes may reach a real socket; an ``int`` means a
#: measured vital_version byte AND a COO-approved flip.
#:
#: THE ONE THING THAT FLIPS IT, quoted from ``0045`` so nobody has to go find
#: the letter: a single GT ticket on the owner's own screen -- one monster
#: hits her once, HP drops by exactly the value this lane read back, and cash
#: / HP-max / MP do not move.  The STOP-on-HP-0 rule applies.
#: ``pf-queue-author`` writes that ticket only once this caller is on ``main``.
MOB_HIT_FRAME_CONFIRMED: Optional[int] = None

#: Gate (i) is LANE-GM's, and it is read STRICTLY: only a real ``int`` (never
#: a ``bool``, never a string, never a missing attribute) counts as open.
#:
#: THE STRICTNESS IS THE FIX FOR A MEASURED HOLE (pf-adversary D5).  The
#: first draft asked ``is not None``, and a LANE-GM engineer who lands
#: ``FULL_BLOCK_UNLOCK_CONFIRMED = False`` to mean "named, not yet unlocked"
#: -- the obvious reading of a ``_CONFIRMED`` name -- would have opened this
#: lane's gate from the other side of the repository.  ``type(v) is int``
#: closes it: ``False`` is a ``bool``, ``'pending'`` is a ``str``, and both
#: read as LOCKED.
#:
#: It is deliberately NOT ``attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED``:
#: that constant is already ``0``, but only because of the scoped ``/speed``
#: exception that ``0045`` point 2 forbids this lane from inheriting.
#: Reading it here would be this lane quietly taking a permission granted to
#: one other door.  The attribute below does not exist in ``gm/attr_wire.py``
#: today -- absent means locked -- and the request for LANE-GM to define it
#: when their (b') unlock lands goes out as this round's letter.
#: [LANE-B assumption -- awaiting COO confirmation]
ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR = "FULL_BLOCK_UNLOCK_CONFIRMED"

#: The chief's read point, by name, resolved at call time and never imported
#: at module scope: it does not exist yet, and a module-scope import of a
#: name that is not there is an ImportError in a walking player's dispatch.
LIVE_ATTR_VALUES_HOOK_ATTR = "current_named_attr_values"

#: The four rows a hit frame is ABOUT, named rather than numbered.  The ``x``
#: numbers and byte offsets live in exactly one place (``attr_wire.FIELDS``)
#: and are looked up through :func:`hit_frame_vital_rows` -- so the day
#: LANE-GM renames one of them, this lane's tests go red and somebody has to
#: come and say what changed, instead of a silently mis-encoded frame.
HIT_FRAME_VITAL_FIELD_NAMES = ("hp_current", "hp_max", "mp_current", "mp_max")

#: The one row a hit CHANGES.  Every other row rides at its live value so the
#: client's full-object copy does not zero it.
HIT_FRAME_CHANGED_FIELD_NAME = "hp_current"

#: ``attr_wire.FIELDS`` encodes ``hp_current`` as ``u32``; a value outside
#: that is an encoder error, and this module names it before the encoder has
#: to (pf-adversary D4 measured ``hp_after = 2**32`` reaching ``struct``).
HP_CEILING = 0xFFFFFFFF

STANDDOWN_GATE_NOT_CONFIRMED = "gate_not_confirmed"
STANDDOWN_ENCODER_LOCKED = "encoder_locked"
STANDDOWN_NO_SESSION_CACHE = "no_session_cache"
STANDDOWN_NO_LIVE_SOURCE = "no_live_source"
STANDDOWN_LIVE_SOURCE_REFUSED = "live_source_refused"
STANDDOWN_LIVE_SOURCE_NOT_A_FIELD = "live_source_not_a_field"
STANDDOWN_LIVE_SOURCE_NOT_SERVER_OWNED = "live_source_not_server_owned"
STANDDOWN_BLOCK_NOT_ADJUDICATED = "block_not_adjudicated"
STANDDOWN_ENCODER_REFUSED = "encoder_refused"

MOB_HIT_FRAME_STAND_DOWN_REASONS = (
    STANDDOWN_GATE_NOT_CONFIRMED,
    STANDDOWN_ENCODER_LOCKED,
    STANDDOWN_NO_SESSION_CACHE,
    STANDDOWN_NO_LIVE_SOURCE,
    STANDDOWN_LIVE_SOURCE_REFUSED,
    STANDDOWN_LIVE_SOURCE_NOT_A_FIELD,
    STANDDOWN_LIVE_SOURCE_NOT_SERVER_OWNED,
    STANDDOWN_BLOCK_NOT_ADJUDICATED,
    STANDDOWN_ENCODER_REFUSED,
)

#: Everything the encoder or the adjudicator can throw at this door.
#: ``struct.error`` is a ``ValueError`` subclass on CPython but is named
#: anyway, because that inheritance is an implementation detail nobody here
#: should have to know.
_ENCODER_ERRORS = (
    attr_wire.AttrWireError,
    persistence_attr_compose.AttrComposeError,
    struct.error,
    TypeError,
    ValueError,
)


def hit_frame_stand_down_line(reason: str, character_id: Any,
                              detail: str) -> str:
    """The line printed instead of a frame, ASCII, greppable.

    ``COO-DECISION 20260904_0045`` point 4 spells the missing-read-point case
    literally -- ``MOB_HIT_FRAME_STANDDOWN reason=no_live_source`` -- so the
    prefix and the first key are that letter's, not this lane's invention,
    and the other reasons are spelled the same way for one grep.
    """
    if reason not in MOB_HIT_FRAME_STAND_DOWN_REASONS:
        raise AssertionError(
            console_safe("unnamed stand-down reason: %s" % (reason,)))
    return console_safe(
        "MOB_HIT_FRAME_STANDDOWN reason=%s char=%r detail=%s"
        % (reason, character_id, detail)
    )


def hit_frame_vital_rows() -> Dict[str, int]:
    """``{name: x}`` for :data:`HIT_FRAME_VITAL_FIELD_NAMES`, resolved from
    ``attr_wire.BY_NAME`` -- the encoder's own table, never a copy.

    Raises :class:`MobAiPlayerDamageError` when a name has gone or has
    stopped being ``known=True``: both mean the row this lane thought it was
    carrying is not the row the encoder would encode.  Callers inside the
    gated path convert this into a named stand-down rather than letting it
    out (pf-adversary D4).
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


def hit_frame_encoder_unlocked() -> bool:
    """Gate (i): has LANE-GM opened ``attr_wire``'s full-block unlock?

    Strict on purpose -- see :data:`ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR`.
    Absent, ``None``, ``False`` and any non-``int`` all mean LOCKED.
    """
    value = getattr(attr_wire, ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR, None)
    return type(value) is int


def resolve_live_attr_values(lane_hooks_module: Any = None) -> Tuple[Any, str]:
    """``(hook, why_not)`` -- the chief's read point, or why there is none.

    Returns the REASON it measured rather than a sentence written today, so
    the console cannot assert "the hook is not on this tree" on the day the
    hook lands and its module raises on import instead (pf-adversary D10).
    """
    module = lane_hooks_module
    if module is None:
        try:
            from . import lane_hooks as module  # type: ignore[no-redef]
        except Exception as exc:
            return None, ("importing lane_hooks raised %r" % (exc,))
    hook = getattr(module, LIVE_ATTR_VALUES_HOOK_ATTR, None)
    if hook is None:
        return None, ("lane_hooks.%s is not defined on this tree "
                      "(ordered from chief in COO-DECISION 20260904_0047 "
                      "point 1)" % (LIVE_ATTR_VALUES_HOOK_ATTR,))
    if not callable(hook):
        return None, ("lane_hooks.%s is %r, not callable"
                      % (LIVE_ATTR_VALUES_HOOK_ATTR, type(hook).__name__))
    return hook, ""


def compose_player_hit_frame(
    legacy: Any,
    cache: Optional[attr_wire.RawBlockCache],
    character_id: int,
    identity_lo: int,
    identity_hi: int,
    hp_after: int,
    lane_hooks_module: Any = None,
) -> Optional[Tuple[bytes, bytes]]:
    """The ``UpdateAttrVital`` a hit would send -- composed, never sent.

    Returns ``(pc, frame)`` only when all four gates are open AND LANE-DB's
    adjudicator agrees every row of the block has an honest value.  In every
    other case it prints exactly one named :func:`hit_frame_stand_down_line`
    and returns ``None``.  At this commit every call returns ``None`` at the
    first gate.

    NOTHING BELOW RAISES ONCE THE ARGUMENTS ARE VALID.  This runs inside a
    walking player's own dispatch, so a hook that explodes, an encoder that
    refuses, a row LANE-GM renamed and a value the adjudicator will not
    stand behind are all STAND-DOWNS with a name, never an exception.  What
    does raise is a bad ARGUMENT -- a caller passing an HP this lane is
    forbidden to write is a programmer error, and swallowing it behind a
    gate that will one day be open is how it would reach a player.

    ``cache`` is the CONNECTION's ``RawBlockCache``, not one made here; see
    gate 3 in the module docstring for why this module refuses to make one.
    """
    if type(character_id) is not int or character_id <= 0:
        raise MobAiPlayerDamageError(
            REFUSE_IDENTITY_NOT_POSITIVE, "character_id=%r" % (character_id,))
    if type(hp_after) is not int:
        raise MobAiPlayerDamageError(
            REFUSE_TYPE_NOT_TYPED_RECORD, "hp_after=%r" % (hp_after,))
    if hp_after < HP_FLOOR or hp_after > HP_CEILING:
        raise MobAiPlayerDamageError(
            REFUSE_FLOOR_WAS_BREACHED,
            "hp_after=%d is outside [%d, %d]"
            % (hp_after, HP_FLOOR, HP_CEILING))

    def stand_down(reason: str, detail: str) -> None:
        print(hit_frame_stand_down_line(reason, character_id, detail))

    # -- gate (ii), this lane's own, before the first byte is built --------
    if type(MOB_HIT_FRAME_CONFIRMED) is not int:
        stand_down(STANDDOWN_GATE_NOT_CONFIRMED,
                   "MOB_HIT_FRAME_CONFIRMED is %r (COO-DECISION 20260904_0045 "
                   "point 3 gate ii)" % (MOB_HIT_FRAME_CONFIRMED,))
        return None

    # -- gate (i), LANE-GM's ----------------------------------------------
    if not hit_frame_encoder_unlocked():
        stand_down(STANDDOWN_ENCODER_LOCKED,
                   "gm.attr_wire.%s is %r, not an int (LANE-GM unlock b')"
                   % (ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR,
                      getattr(attr_wire, ATTR_WIRE_FULL_BLOCK_UNLOCK_ATTR,
                              None)))
        return None

    # -- gate 3, the connection's own cache --------------------------------
    if not isinstance(cache, attr_wire.RawBlockCache):
        stand_down(STANDDOWN_NO_SESSION_CACHE,
                   "no per-connection RawBlockCache was handed in (got %r); "
                   "this module will not make a second copy of the player's "
                   "state" % (type(cache).__name__,))
        return None

    # -- the live values ---------------------------------------------------
    hook, why_not = resolve_live_attr_values(lane_hooks_module)
    if hook is None:
        stand_down(STANDDOWN_NO_LIVE_SOURCE, why_not)
        return None
    try:
        live = hook(character_id)
    except Exception as exc:  # the hook's own errors, not this lane's
        stand_down(STANDDOWN_LIVE_SOURCE_REFUSED, "%r" % (exc,))
        return None
    if not isinstance(live, dict) or not live:
        stand_down(STANDDOWN_NO_LIVE_SOURCE,
                   "the read point returned %r" % (live,))
        return None

    # Sorting mixed-type keys is itself a crash (pf-adversary D4 measured it
    # inside the refusal that exists to prevent crashes), so the keys are
    # checked for shape BEFORE anything sorts them.
    not_fields = [x for x in live
                  if type(x) is not int or x not in attr_wire.BY_X]
    if not_fields:
        stand_down(STANDDOWN_LIVE_SOURCE_NOT_A_FIELD,
                   "keys that are not rows of attr_wire.FIELDS: %r"
                   % (sorted(map(repr, not_fields)),))
        return None

    # LANE-DB's adjudicator only accepts values for rows IT considers
    # server-owned; a value for any other row cannot honestly enter a block
    # (`persistence_attr_compose.compose_full_block` refuses them outright,
    # and this door names the refusal instead of catching an exception).
    stray = sorted(x for x in live
                   if x not in persistence_attr_compose.SERVER_OWNED_FIELDS)
    if stray:
        stand_down(STANDDOWN_LIVE_SOURCE_NOT_SERVER_OWNED,
                   "the read point supplied rows LANE-DB does not treat as "
                   "server-owned: %r" % (stray,))
        return None

    # -- the adjudicator: the answer to "is this block complete?" ----------
    # NOT a count written here, and not this lane's opinion.  At this commit
    # it answers NO for all 55 rows, which is why a reader who opens the
    # console finds this line and not a frame.
    gaps = persistence_attr_compose.block_gaps(live)
    if gaps:
        stand_down(
            STANDDOWN_BLOCK_NOT_ADJUDICATED,
            "persistence_attr_compose.block_gaps names %d row(s) with no "
            "honest value; first: %s"
            % (len(gaps), ", ".join(
                "x=%d(%s):%s" % (g.x, g.field_name, g.reason)
                for g in gaps[:3])))
        return None

    # -- compose, through the ONE encoder 0045 names -----------------------
    try:
        rows = hit_frame_vital_rows()
        block = persistence_attr_compose.compose_full_block(live)
        if not cache.is_captured():
            cache.capture_initial(block)
        return attr_wire.build_named_field_update(
            legacy, cache, identity_lo, identity_hi,
            rows[HIT_FRAME_CHANGED_FIELD_NAME], hp_after,
        )
    except MobAiPlayerDamageError as exc:
        # A renamed or demoted vital row.  Named, not raised: LANE-GM moving
        # their own table may not take a walking player's dispatch down.
        stand_down(STANDDOWN_ENCODER_REFUSED, "%r" % (exc,))
        return None
    except _ENCODER_ERRORS as exc:
        stand_down(STANDDOWN_ENCODER_REFUSED, "%r" % (exc,))
        return None
