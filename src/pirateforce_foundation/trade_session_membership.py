"""LANE-B / TRADE-SESSION-001 (RE-157 job 1): the active-store-session guard
``runtime.py`` still needs, built and pinned so wiring it is one predicate
call, not a design task -- the companion of ``mob_combat_membership.py``
(RE-157 job 2, already merged) for the other guard seam the same result
letter named.

WHAT A PLAYER SEES BECAUSE OF THIS FILE, STATED HONESTLY AND FIRST.  Nothing
yet.  This module has no call site in ``runtime.py`` -- ``runtime.py`` is
chief's file, not this lane's, so the guard this file builds cannot flip
live TradeCmd behaviour by itself.  See the CORE-REQUEST below for the one
predicate call that would wire it.

WHY THIS MODULE EXISTS.  ``pf_bridge/notes_to_chief/20260830_1111_RE-157-
RESULT-*.md`` (the RE-157 result letter, Job 1) named a real gap: the frozen
``TradeCmdVital`` branch (``current/pf_login_game_server_v141.py:4128``
onward) tracks exactly one piece of state, ``shop_store5_open_sent: bool``
(``:3534``), and never clears it on store-close (``:4211-4223`` increments
``trade_store_close_capture_count`` but does not touch the flag -- verified
again this round by reading the live frozen file, not by trusting the
letter's line numbers, and they still match exactly since v141 is pinned and
cannot drift). A cart-add or final-buy frame is accepted whenever that one
bit has ever been set once, regardless of which scene the connection is now
in, which actor (if any) actually opened a store for this session, or
whether a scene/census change since then invalidated the session the store
was opened under. This module does not fix that -- it only builds the
fail-closed predicate the letter asked for, so nobody has to re-derive its
shape under time pressure once a runtime.py round picks up the wiring.

WHY THE SAME SHAPE AS ``mob_combat_membership.py``, NOT A NEW ONE.  Both
RE-157 guards are "does this caller-held record admit this specific
request," checked once, with no frame composed on refusal -- a plain
predicate over state the caller already has on hand, not a ``lane_hooks``
responder (there is no scene-keyed hook point for a non-composing yes/no
gate today, same reasoning ``mob_combat_membership.py`` already gives in
full). Reusing the shape means one contract to review, not two.

FAIL CLOSED, ALWAYS.  ``admits()`` returns ``False`` (never an exception)
whenever the session record is missing, the scene does not match, the
generation does not match, or the actor identity that opened the store does
not match the one presented now. It never widens: an unmatched anything is a
refusal, and the only way past it is an explicit, exact match on all three.

WHAT "GENERATION" MEANS HERE.  Same convention as
``mob_combat_membership.AnnouncedActorMembership``: an opaque,
caller-supplied, ``==``-comparable token stamped at store-open time and
compared again at cart/final-buy/close time. This module does not read
``runtime.py``'s own commit points or decide what a generation counts --
RE-157 says only ``runtime.py`` knows that (it names the store-open queue
point as ``current/pf_login_game_server_v141.py:4395-4411`` and
``:4433-4442`` for the P91 announcement this stamp must be tied to).

CORE-REQUEST (for chief, ``runtime.py``): the sole point today where a
``TradeCmdVital`` frame reaches the frozen branch is the generic
``actions = super().dispatch(parsed)`` fallback inside ``_dispatch_with_
lanes`` (currently line 6925 -- verified this round by grepping the whole
file for ``TRADE_CMD_VITAL``/``TradeCmdVital`` and finding no dedicated
``nested_id ==`` branch anywhere in ``runtime.py``, unlike ``TARGET_POS_
VITAL`` or ``CHOOSE_NPC``). Before that fallback, when
``nested_id == legacy.TRADE_CMD_VITAL``, add::

    if nested_id == legacy.TRADE_CMD_VITAL and not trade_session_membership.admits(
        self.active_store_session,
        scene_id=self.foundation.selected.position.scene_id,
        actor_identity=<the store owner actor identity this cart/buy/close
                         frame is being sent against -- this lane does not
                         know which existing attribute, if any, already
                         holds it>,
        generation=<the session's current census generation counter -- same
                     open question mob_combat_membership.py's own
                     CORE-REQUEST already raises>,
    ):
        self.events.append("trade_cmd_no_active_session_no_reply")
        return []

and stamp ``self.active_store_session`` via ``build_session()`` only at the
point a store-open frame is actually queued from an announced P91 identity
(``v141:4433-4442``), clearing it on close command, scene handoff, or
census replace/refuse -- the same four clear points RE-157 names for this
job. This lane does not know which existing ``runtime.py`` attribute (if
any) already holds "the actor identity this store was opened for" or "the
session's current census generation counter" -- both are exactly the state
RE-157 says only ``runtime.py``'s own commit points can supply, so the exact
wiring, including whether it shares a generation counter with the mob-combat
guard, is chief's call. This module supplies the predicate and its contract
only, pinned by ``tests/test_trade_session_membership.py``.
"""
from __future__ import annotations

from typing import Any, NamedTuple


class ActiveStoreSession(NamedTuple):
    """One store-open's worth of "this session is allowed to keep trading
    with this actor" -- the ``scene_id`` the store was opened in, the exact
    actor identity that opened it, and an opaque ``generation`` token the
    caller can compare with ``==`` to know whether this record is still the
    session's current one.
    """

    scene_id: int
    actor_identity: int
    generation: Any


def build_session(
    scene_id: int, actor_identity: int, generation: Any,
) -> ActiveStoreSession:
    """Stamp a store-open into a comparable, immutable session record."""
    return ActiveStoreSession(scene_id, actor_identity, generation)


def admits(
    session: "ActiveStoreSession | None",
    *,
    scene_id: int,
    actor_identity: int,
    generation: Any,
) -> bool:
    """RE-157 Job 1's predicate.  ``False`` for anything not an EXACT match
    on all three fields, including a ``None`` session (no store has ever
    been opened this session, or it was already cleared) -- see the module
    docstring's FAIL CLOSED section for why there is no partial-match
    branch.
    """
    if session is None:
        return False
    if session.scene_id != scene_id:
        return False
    if session.generation != generation:
        return False
    return session.actor_identity == actor_identity
