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
chief's read point, and every row this door adjudicates comes from
``gm/attr_wire.named_field_x()`` -- LANE-DB's ``persistence_attr_compose``
adjudicator is withdrawn from this door entirely (``COO-DECISION
20260904_0546``, pf-adversary D2; see "THE GATES" below).  Reported to the
COO as a deviation from the file ``0045`` named.

THE GATES, IN THE ORDER THEY ARE CHECKED
-----------------------------------------
1. :data:`MOB_HIT_FRAME_CONFIRMED` -- THIS LANE'S, gate (ii) of ``0045``
   point 3.  ``None`` today.
2. ``gm/attr_wire``'s full-block unlock -- LANE-GM'S, gate (i).  Absent
   today.  Deliberately NOT ``UPDATE_ATTR_VITAL_VERSION_CONFIRMED``, which is
   already ``0`` but only from the scoped ``/speed`` exception ``0045``
   point 2 forbids this lane from inheriting.
3. A SESSION ``RawBlockCache``, handed in by a caller -- READ FOR SHAPE ONLY,
   SUPERSEDED 2026-09-04 ``COO-DECISION 20260904_0847``.  This door used to
   compose the bytes it sends from this cache; it no longer does (see gate 4
   below).  What survives is narrower: the cache is still the one
   per-CONNECTION record of which rows THIS connection's own login composed
   (``attr_wire``'s own docstring: one instance per connection, "so the next
   command in this connection builds on real prior state"), and this module
   still will not manufacture one -- a per-compose cache would mean two
   copies of the player's state on one connection (pf-adversary D6).  Its
   VALUES are never read again; only its key set is, and only to learn a
   shape.
4. THE LIVE VALUE SOURCE, checked against ``gm/attr_wire.named_field_x()``
   -- the 27-row set a hit frame is "about" -- and NEVER against LANE-DB's
   55-row ``persistence_attr_compose.compose_full_block``/``block_gaps``,
   withdrawn from this door's adjudication path entirely (``COO-DECISION
   20260904_0546``, pf-adversary round ``f2qyxx`` D2).  Every key the live
   source hands back must be a real row of ``attr_wire.FIELDS``
   (:data:`STANDDOWN_LIVE_SOURCE_NOT_A_FIELD`) and must be one of the 27
   named rows (:data:`STANDDOWN_LIVE_SOURCE_NOT_NAMED`) -- SUPERSEDED
   2026-09-04, ``COO-DECISION 20260904_0847``: these two checks used to
   guard a dict whose VALUES this door then discarded, composing from the
   cache instead (pf-adversary round ``yq5gzr`` D6, the open question that
   letter answered).  They no longer do: the COO's ruling is option (a) in
   strict form -- ``live`` IS the truth, and every row this door's frame carries
   for the 27-row named set comes from it, through
   ``gm/attr_wire.live_full_block_values`` (LANE-GM's own shared function,
   the same one ``seed_cache_from_live_values`` calls -- this door is a
   CALLER of it, per ``0045``, not a second implementation of its
   partitioning).  The rows this connection's login shape needs OUTSIDE the
   named set (x=9/x=10/x=11 -- ``attr_wire.LOGIN_SOURCED_ROWS``) come from
   the SAME function's login-byte half, never from a real-time read and
   never from the cache.  COMPLETENESS is measured against the SHAPE gate 3
   read off the cache's keys, from these live sources -- a row that shape
   needs and neither source can answer is a whole-frame stand-down
   (:data:`STANDDOWN_LIVE_SOURCE_INCOMPLETE`), never a fill from the cache
   and never a fill with zero.

WHY "FULL BLOCK" IS A REQUIREMENT AND NOT A PREFERENCE.  ``RE-222`` (static,
SHA-pinned, LANE-GM) established that the client's apply path for 0x309A is
a FULL-OBJECT COPY: every field the frame omits comes back as the fresh
constructor's zero.  A hit frame carrying ``hp_current`` alone would zero
the player's cash and HP-max -- which is not an analogy for ``GT-218``, it
is what ``GT-218`` was.  So this module composes a block shaped exactly like
this connection's own login send, or it composes nothing.  THE UNIT IS NOT A
COUNT WRITTEN HERE: it is whatever ``login_mask.admitted_field_x_sets``
admits, read off the CONNECTION's cache (gate 3) and enforced a second time,
structurally, by ``gm/attr_wire.make_update_attr_frame`` itself -- so a shape
this door got wrong from any source still cannot reach a socket.  A stale
value inside that correctly-shaped block is the OTHER half of ``RE-222`` Q0,
and it is what ``COO-DECISION 20260904_0847`` closed: a shape can be right
while a VALUE inside it is wrong, if that value came from anywhere other
than a live read -- which is why gate 4 now sources every value the same
way it sources the shape's membership, from ``live_full_block_values``,
and never from the cache gate 3 already consulted.

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
* NO claim that this door still calls ``gm/attr_wire.build_named_field_
  update``.  SUPERSEDED 2026-09-04, ``COO-DECISION 20260904_0847``: that
  function reads its OTHER rows from the connection's cache, which this
  door is now forbidden to do, so it calls ``live_full_block_values`` (for
  every row's value) and ``make_update_attr_frame`` (the header-adding wall
  that still refuses a wrong shape) directly instead.  ``RawBlockCache``
  gains no new write from this: ``record_sent`` is called exactly where it
  always was, by this door, after a successful compose -- only the read
  side moved.
* NO claim that a resolved ``live`` dict of fewer than 27 rows is
  survivable.  It was, briefly, before this round: an incomplete answer
  used to fail the encoder's OWN completeness gate one function later, with
  the same stand-down name.  ``live_full_block_values`` now asks the same
  question of a NARROWER, per-connection set (this connection's login
  shape, not the full named table), so a hook this permissive still refuses
  -- just earlier, and by :data:`STANDDOWN_LIVE_SOURCE_INCOMPLETE` rather
  than :data:`STANDDOWN_ENCODER_REFUSED`.
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
#: at module scope.  ~~it does not exist yet~~ -- SUPERSEDED 2026-09-04: it
#: landed on ``main`` in server ``#695`` (R330), so this door's live-value
#: gate is now the only one of the four that another lane has opened.  The
#: call-time resolution stays exactly as written: a module-scope import of a
#: name that may not be there is an ImportError in a walking player's
#: dispatch, and the day chief moves it this lane stands down instead of
#: raising.
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
#: RENAMED from ``STANDDOWN_LIVE_SOURCE_NOT_SERVER_OWNED`` (pf-adversary
#: round f2qyxx D2, ``COO-DECISION 20260904_0546``): this door no longer
#: measures a live row against LANE-DB's ``SERVER_OWNED_FIELDS`` -- it
#: measures it against ``gm/attr_wire.named_field_x()``, the 27-row set a
#: hit frame is "about".  The old name would now describe a check this
#: module does not make.
STANDDOWN_LIVE_SOURCE_NOT_NAMED = "live_source_not_named"
#: NEW 2026-09-04 (``COO-DECISION 20260904_0847`` item 1/2): this connection's
#: login shape names a row that neither ``live_full_block_values``'s named
#: source nor its login-byte source can answer.  Never filled from the
#: cache gate 3 already read for shape, and never filled with zero -- both
#: are exactly the ``GT-218`` family this ruling closed.
STANDDOWN_LIVE_SOURCE_INCOMPLETE = "live_source_incomplete"
#: NEW 2026-09-04, pf-adversary (this round), Finding 1, MEASURED: a cache's
#: key set is "PUBLIC and unvalidated" (``RawBlockCache``'s own docstring),
#: and passing an unadmitted shape straight to ``live_full_block_values``
#: reaches an unguarded ``BY_X[x]`` lookup in ``attr_wire.live_named_values``/
#: ``live_login_bytes`` -- a bare ``KeyError``, not ``AttrWireError``, the
#: moment a hook's answer happens to include that same bogus key.  Checked
#: BEFORE that call, against ``login_mask.admitted_field_x_sets``, the same
#: check ``attr_wire.build_named_field_update`` already carried for this
#: same reason before this door stopped routing through it.
STANDDOWN_CACHE_SHAPE_NOT_ADMITTED = "cache_shape_not_admitted"
STANDDOWN_ENCODER_REFUSED = "encoder_refused"

MOB_HIT_FRAME_STAND_DOWN_REASONS = (
    STANDDOWN_GATE_NOT_CONFIRMED,
    STANDDOWN_ENCODER_LOCKED,
    STANDDOWN_NO_SESSION_CACHE,
    STANDDOWN_NO_LIVE_SOURCE,
    STANDDOWN_LIVE_SOURCE_REFUSED,
    STANDDOWN_LIVE_SOURCE_NOT_A_FIELD,
    STANDDOWN_LIVE_SOURCE_NOT_NAMED,
    STANDDOWN_LIVE_SOURCE_INCOMPLETE,
    STANDDOWN_CACHE_SHAPE_NOT_ADMITTED,
    STANDDOWN_ENCODER_REFUSED,
)

#: Everything the encoder can throw at this door.  ``persistence_attr_
#: compose.AttrComposeError`` used to be named here too; it is withdrawn
#: along with the import (pf-adversary D2, ``COO-DECISION 20260904_0546``)
#: -- this door no longer calls anything that can raise it.
#: ``struct.error`` is a ``ValueError`` subclass on CPython but is named
#: anyway, because that inheritance is an implementation detail nobody here
#: should have to know.
_ENCODER_ERRORS = (
    attr_wire.AttrWireError,
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

    Returns ``(pc, frame)`` only when all the gates in the module docstring
    are open AND every row this connection's login shape needs resolves to
    a real, live value.  In every other case it prints exactly one named
    :func:`hit_frame_stand_down_line` and returns ``None``.  At this commit
    every call returns ``None`` at the first gate.

    NOTHING BELOW RAISES ONCE THE ARGUMENTS ARE VALID.  This runs inside a
    walking player's own dispatch, so a hook that explodes, an encoder that
    refuses, a row LANE-GM renamed and a value the encoder will not accept
    are all STAND-DOWNS with a name, never an exception.  What
    does raise is a bad ARGUMENT -- a caller passing an HP this lane is
    forbidden to write is a programmer error, and swallowing it behind a
    gate that will one day be open is how it would reach a player.

    ``cache`` is the CONNECTION's ``RawBlockCache``, not one made here; see
    gate 3 in the module docstring for why this module refuses to make one.
    SUPERSEDED 2026-09-04 (``COO-DECISION 20260904_0847``): its VALUES no
    longer feed this frame at all -- only its key set does, to learn this
    connection's own login shape.  Every byte the frame carries comes from
    ``gm/attr_wire.live_full_block_values`` instead.
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

    # -- gate 3, the connection's own cache -- READ FOR SHAPE, NEVER VALUE --
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

    # A hit frame is "about" the 27-row NAMED set only, never LANE-DB's
    # 55-row persistence block -- `COO-DECISION 20260904_0546`, which
    # withdrew `persistence_attr_compose` (`compose_full_block`/
    # `block_gaps`) from this door's adjudication path entirely
    # (pf-adversary D2).  A value for any row outside `named_field_x()`
    # cannot honestly be something a hit frame is about.  SUPERSEDED
    # 2026-09-04 (`COO-DECISION 20260904_0847`): these two checks used to
    # guard a `live` dict this door then discarded in favour of the cache
    # (pf-adversary round yq5gzr D6).  It no longer does -- `live` is read
    # again below, by `live_full_block_values`, as the actual byte source.
    named = set(attr_wire.named_field_x())
    stray = sorted(x for x in live if x not in named)
    if stray:
        stand_down(STANDDOWN_LIVE_SOURCE_NOT_NAMED,
                   "the read point supplied rows outside "
                   "gm.attr_wire.named_field_x(): %r" % (stray,))
        return None

    # -- this connection's own login SHAPE, from the cache's KEYS only -----
    # `COO-DECISION 20260904_0847` item 2: completeness is measured against
    # the login set, from live sources -- not against the cache.  The cache
    # remains the one per-connection record of WHICH rows this connection's
    # login composed (the same reasoning `attr_wire.build_named_field_
    # update` uses its own cache for, pf-adversary round `4fxkam` D1): an
    # unseeded cache has no shape to measure against, so this door will not
    # guess one.
    shape = set(cache.current_values())
    if not shape:
        stand_down(STANDDOWN_NO_SESSION_CACHE,
                   "cache holds no captured login shape yet for this "
                   "connection; this door will not guess one")
        return None

    # `RawBlockCache.capture_initial` IS, BY ITS OWN DOCSTRING, "PUBLIC and
    # unvalidated": `shape` is not proven to hold only real `attr_wire.
    # FIELDS` rows yet, and pf-adversary (this round) MEASURED what that
    # costs -- an `x` in `shape` that is not a real row still reaches
    # `gm.attr_wire.live_named_values`/`live_login_bytes`'s own `BY_X[x]`
    # lookup one call below, an UNGUARDED dict index that raises a bare
    # `KeyError`, not `AttrWireError`, the instant a hook's answer happens
    # to include that same bogus key.  `attr_wire.build_named_field_update`
    # -- the function this door used to route through -- already carried
    # this exact check, for this exact reason, before it ever touched the
    # cache's key set; dropping it when this door stopped calling that
    # function reopened the hole.  Checked here, the same way, against
    # `login_mask.admitted_field_x_sets`: every admitted shape is derived
    # from a REAL production login composition, so membership in one is
    # already a proof that every row in it is a real `FIELDS` row -- no
    # second, narrower table of "real x values" needs inventing.
    from .gm import login_mask  # noqa: PLC0415 - avoids an import cycle, see attr_wire.py
    admitted = login_mask.admitted_field_x_sets(legacy)
    if not any(shape == set(known_shape) for known_shape in admitted):
        stand_down(STANDDOWN_CACHE_SHAPE_NOT_ADMITTED,
                   "cache holds %r, which is not one of the admitted login "
                   "shapes %r; this door will not guess at, or compose "
                   "for, a shape production login never sends"
                   % (sorted(shape), [sorted(s) for s in admitted]))
        return None

    # -- (b'') IN FULL, from live sources ONLY -----------------------------
    # `COO-DECISION 20260904_0847` (option a, strict): `live` IS the truth, and the
    # cache just consulted for shape may not fill a single row of the frame
    # -- a row the shape needs that neither source can answer is a whole
    # -frame stand-down, never a fill from the cache and never a fill with
    # zero.  `gm/attr_wire.live_full_block_values` is LANE-GM's own shared
    # function (the same one `seed_cache_from_live_values` calls); this door
    # is a CALLER of it, per `COO-DECISION 20260904_0045`, not a second
    # implementation of its named/login-byte partitioning.  `rows=shape`
    # (not the default union) is what keeps this call scoped to THIS
    # connection's own branch -- the same D1 finding `build_named_field_
    # update` already carries a comment about: the union would admit x=11
    # for a connection whose login composed the plain branch.
    #
    # `hooks=_same_live_hooks`, NOT the raw `lane_hooks_module`
    # (pf-adversary this round, Finding 2, MEASURED): passing the module
    # straight through would have `live_full_block_values` call the NAMED
    # hook a SECOND, independent time to build `values` -- a call the two
    # gates just above never see, so their validation would cover only the
    # FIRST call's answer while the bytes this door actually sends come
    # from a possibly-different second one (nothing here or in `attr_wire`
    # proves the hook is idempotent between calls).  `_same_live_hooks`
    # answers the named read point with the EXACT `live` dict already
    # fetched and validated above, so the hook is invoked at most once per
    # compose; the login-byte read point is untouched, resolved off
    # whichever module this door was actually given.
    resolved_hooks_module = lane_hooks_module
    if resolved_hooks_module is None:
        from . import lane_hooks as resolved_hooks_module  # noqa: PLC0415
    login_byte_hook = getattr(
        resolved_hooks_module, attr_wire.LOGIN_BYTES_READ_POINT, None)

    class _same_live_hooks:
        """A `hooks=` stand-in: answers the named point with the `live`
        dict this door already fetched and validated (never calls the
        real hook again); the login-byte point passes straight through."""

    setattr(_same_live_hooks, attr_wire.LIVE_VALUE_READ_POINT,
            staticmethod(lambda character_id, _live=live: dict(_live)))
    if login_byte_hook is not None:
        setattr(_same_live_hooks, attr_wire.LOGIN_BYTES_READ_POINT,
                staticmethod(login_byte_hook))

    try:
        values = attr_wire.live_full_block_values(
            character_id, hooks=_same_live_hooks, legacy=legacy, rows=shape)
    except attr_wire.AttrWireError as exc:
        stand_down(STANDDOWN_LIVE_SOURCE_INCOMPLETE, "%r" % (exc,))
        return None

    # -- compose, through the ONE encoder 0045 names -----------------------
    try:
        rows = hit_frame_vital_rows()
        hp_x = rows[HIT_FRAME_CHANGED_FIELD_NAME]
        if hp_x not in values:
            # Not reachable through a real production login today (every
            # admitted shape carries the four named vital rows), kept as a
            # named stand-down rather than a KeyError because this door may
            # not raise on a row LANE-GM's tables moved.
            stand_down(STANDDOWN_LIVE_SOURCE_INCOMPLETE,
                       "hp_current row x=%d is not in this connection's "
                       "login shape %r" % (hp_x, sorted(shape)))
            return None
        # The ONE row this door changes; every other row rides at its LIVE
        # value -- never the cache's -- so the client's full-object copy
        # does not revert a value another door already moved on this
        # connection since the cache was last written (`RE-222` Q0; the
        # GT-218 family `COO-DECISION 20260904_0847` closed).
        values = dict(values)
        values[hp_x] = hp_after
        pc, frame = attr_wire.make_update_attr_frame(
            legacy, identity_lo, identity_hi, values)
    except MobAiPlayerDamageError as exc:
        # A renamed or demoted vital row.  Named, not raised: LANE-GM moving
        # their own table may not take a walking player's dispatch down.
        stand_down(STANDDOWN_ENCODER_REFUSED, "%r" % (exc,))
        return None
    except _ENCODER_ERRORS as exc:
        stand_down(STANDDOWN_ENCODER_REFUSED, "%r" % (exc,))
        return None

    # The cache still remembers what was actually sent -- its one remaining
    # write, unchanged by this round (`COO-DECISION 20260904_0847` item 2:
    # "RawBlockCache keeps exactly one job: reader/diagnostic + record_sent,
    # as before").  `build_named_field_update` used to call this on this
    # door's behalf; now this door calls it directly, in the same place.
    cache.record_sent(values)
    return pc, frame
