"""Per-connection watch for whether a durably-persisted `/warp` frame ever
reached the wire, and the undo when it did not.

WHY THIS MODULE EXISTS.  `warp_scene_persist.rollback_warp_scene_on_send_
failure` (`CORE-REQUEST-GM-055`, redirected by chief's `20260905_0045`
reply) is the undo for the send-loop window: `_persist_warp_scene` writes
the destination row at FRAME-COMPOSE time, and the socket write for that
same frame happens roughly 2,200 lines later, in `current/pf_login_game_
server_v141.py`'s own action-send loop -- chief's zone, where this lane may
not put a call (`AGENTS.md` section 7).  That function is complete and
tested (`tests/test_gm_warp_scene_rollback.py`) but nothing CALLS it: chief
has to tell it a send failed, and `CORE-REQUEST-GM-057` (`pf_bridge/notes_
to_chief/20260905_0121_LANE-GM-CORE-REQUEST-GM-057-send-failure-observer.md`)
asks for exactly one hookup in `connection.py`'s `AcceptedGameSocket.
sendall`, offering `(frame_bytes)` on success and `(frame_bytes, error)` on
failure to `state.on_game_frame_sent` / `state.on_game_frame_send_failed`
if either is present -- the SAME opt-in shape `attach_transport_socket_
closer` already uses in that file (`connection.py:97-99`).

THIS MODULE IS THE OTHER HALF OF THAT HOOKUP, AND IT DOES NOT WAIT FOR IT.
Everything below is written and tested against a plain fake session, the
same way `warp_target_record.py` and `warp_scene_persist.py` are; the
letter's own words (translated) are "writable and testable in full without
your hookup".  chief's one line at the
`connection.py` layer is the ONLY thing standing between this module and a
live send failure actually reaching it; until that line lands, these
functions simply never get called by anything outside this lane's own
tests and `chat_command_action.py`'s own compose-time call below.

THE CELL, AND WHY IT LIVES ON THE SESSION.  `park_warp_send` records the
exact frame bytes a persisted no-coords warp just composed, the moment
`_persist_warp_scene` (`chat_command_action.py`) reports `OUTCOME_
PERSISTED`.  Same reasoning as `warp_target_record.SESSION_ATTRIBUTE`'s own
docstring: a module-level map keyed by session would outlive a dropped
socket and could hand one connection's park to another; an attribute on the
session dies with the session, for free, and reads/writes only ever touch
the one connection that composed the frame.

THE SUCCESS SIDE COMPARES BYTES, ON PURPOSE.  `on_game_frame_sent` clears
the park only when the frame the facade reports as SENT is byte-identical
to the one this module parked.  The send loop calls the observer after
EVERY queued action's frame, not only a warp's -- a `say`, a staged-login
write, another GM's `/speed` frame on a different connection's cell -- so a
park that cleared on ANY successful send would report "the warp's row is
now confirmed reachable" the moment an unrelated frame went out first, and
be silently wrong until the warp's own frame either sends or fails.

THE FAILURE SIDE DOES NOT COMPARE BYTES, AND THAT ASYMMETRY IS THE WHOLE
POINT.  `CORE-REQUEST-GM-057`'s own words (translated): "including the case
where v141's `break` drops a warp frame that never reached the queue".
The send loop's own `except` clause
prints `SEND_FAILED {label} {e!r}` and then `break`s out of the WHOLE
action list on the FIRST failure -- so if an EARLIER queued action's frame
is the one whose `sendall` raises, the warp's own frame is never attempted
at all, and no call naming the warp's bytes will EVER arrive on this
connection.  The only observable fact by then is "a send failed on this
connection while the warp's row was still unconfirmed", and that fact alone
already means the client cannot have received the warp -- a frame that
never left this listener thread cannot have reached anyone.  So `on_game_
frame_send_failed` acts whenever the cell is non-empty, regardless of which
frame's bytes are attached to the failure; matching them would only narrow
which failures this module notices, not which ones actually orphaned the
row.

WHERE THE UNDO'S `previous` COMES FROM IS NOT THIS MODULE'S PROBLEM.
`rollback_warp_scene_on_send_failure` reads `foundation.selected.position`
itself -- the pre-warp snapshot `persist_warp_scene` restores there the
moment the durable write lands (see that module's own docstring) -- so this
file never needs to carry a position of its own.  It only ever needs to
know ONE thing: is there still an unconfirmed persisted warp on this
connection, yes or no.

NEVER RAISES, ANYWHERE IN THIS FILE.  Every entry point here can run on the
game-listener thread, most of them inside a `sendall` failure's own
exception handling (`connection.py`'s proposed `_offer_send_outcome`,
itself written to swallow and report whatever an observer raises) -- a
raise from a diagnostic must never mask or replace the send failure that
triggered it.

NONCLAIM.  Nothing in this file sends a byte, opens a socket, or touches
`runtime.py` / `app.py` / `current/pf_login_game_server_v141.py` / the
canonical DB / lane A's `scenarios/world_*.json` / lane B's `scenarios/
combat_*.json`.  Parking a frame is not evidence anyone received it, and
clearing a park is not evidence a client rendered anything -- both are
statements about which bytes this listener thread believes it queued and
whether the socket layer later agreed.
"""
from __future__ import annotations

from dataclasses import dataclass

from .warp_scene_persist import (
    SEND_FAILURE_WARP_ACTION_LABEL,
    rollback_warp_scene_on_send_failure,
)

#: The attribute the park lives under.  Named here, once, so the writing
#: side (`park_warp_send`) and the reading sides (`on_game_frame_sent`,
#: `on_game_frame_send_failed`, and any future `chat_command_action.py`
#: withhold-path cleanup) cannot drift onto two different strings.
SESSION_ATTRIBUTE = "gm_warp_send_watch_park"

#: Event names this module appends to `session.events`, all under one
#: prefix so a reader of the trail can tell a send-watch line from
#: `warp_scene_persist`'s own (`gm_chat_action_warp_scene_rollback_*`) or
#: `warp_target_record`'s.
EVENT_PREFIX = "gm_warp_send_watch_"

# The outcome words `on_game_frame_sent` and `on_game_frame_send_failed`
# return.  `nothing_parked` is shared by both entry points on purpose: it
# means the identical thing in either direction -- "this connection had no
# unconfirmed persisted warp when the facade called in" -- and the send
# loop calls both after EVERY queued frame, so this is deliberately the
# cheapest, most common answer for each.
OUTCOME_NOTHING_PARKED = "nothing_parked"
#: The frame that just went out was not the one parked here; left in place
#: to keep waiting for either a match or a failure.
OUTCOME_LEFT_PARKED_OTHER_FRAME = "left_parked_other_frame"
#: The frame that just went out WAS the one parked here.  The park is now
#: cleared; this is the ordinary, expected close of the window.
OUTCOME_CLEARED_OWN_FRAME = "cleared_own_frame"
#: The bytes matched and this module tried to clear the park, but the
#: session would not confirm the clear (a session that swallows attribute
#: writes).  The row is still fine -- the frame really did reach the wire --
#: only the bookkeeping could not be retired.
OUTCOME_CLEAR_NOT_CONFIRMED = "clear_not_confirmed"


@dataclass(frozen=True)
class ParkedWarpSend:
    """One unconfirmed persisted warp's frame, plus the label it is for.

    `label` is carried for diagnostics only -- every park this module ever
    makes uses the same constant (`SEND_FAILURE_WARP_ACTION_LABEL`), because
    `park_warp_send` does not take a label argument at all (see its own
    docstring for why that is deliberate, not an omission).
    """

    label: str
    frame_bytes: bytes


def park_warp_send(session: object, frame_bytes: object) -> bool:
    """Remember `frame_bytes` as the persisted warp still owed a send.

    Called from `chat_command_action._warp_teleport_action_no_coords`,
    and ONLY when `_persist_warp_scene` just reported `OUTCOME_PERSISTED`
    -- a durable row moved, and until this connection's `AcceptedGameSocket`
    confirms the frame reached the wire (or fails to), the row and the
    client's actual scene can disagree.

    REPLACES, RATHER THAN REFUSES, AN EXISTING PARK.  Same reasoning as
    `warp_target_record.record_warp_target`'s own docstring: a second
    persisted warp before the first one's frame is confirmed means the
    durable row has already moved again, so the STALE park's bytes could
    never confirm anything the row still cares about, and holding onto them
    would only delay noticing the frame that matters now.

    ONE ARGUMENT, NOT TWO.  This module never parks any label other than
    `SEND_FAILURE_WARP_ACTION_LABEL` -- there is exactly one call site, and
    it is this lane's own -- so taking a caller-supplied label would only
    add a way for a future call site to park the wrong constant by typo,
    for zero behavioural benefit today.

    Returns whether the park is really on the session afterwards, verified
    by reading it back rather than trusted from "`setattr` did not raise" --
    `record_warp_target`'s own finding: a session whose `__setattr__`
    swallows the write raises nothing, and reporting success on that would
    tell `_warp_teleport_action_no_coords` a safety net is armed that is
    not there.  NEVER RAISES: an object with no `__bytes__`/buffer support,
    or a session that refuses the attribute, costs this call `False`, never
    an exception on the path that has already sent the client a real frame.
    """
    try:
        frame_bytes = bytes(frame_bytes)
    except Exception:  # noqa: BLE001 - see docstring; nothing escapes this
        return False
    record = ParkedWarpSend(SEND_FAILURE_WARP_ACTION_LABEL, frame_bytes)
    try:
        setattr(session, SESSION_ATTRIBUTE, record)
    except Exception:  # noqa: BLE001
        return False
    try:
        return getattr(session, SESSION_ATTRIBUTE, None) is record
    except Exception:  # noqa: BLE001
        return False


def clear_warp_send_watch(session: object) -> bool:
    """Drop any parked frame; whether it is now really gone.

    Used by this module's own two observer entry points, and by
    `chat_command_action.py`'s withhold path (`_make_action`) for the case
    where the row's own undo (`verdict.undo`) already ran synchronously
    because the outcome row could not be appended -- the frame that would
    have confirmed or failed this park is never going to be queued at all
    in that case (`action` is set to `None` on the same branch), and a park
    left behind would let a LATER, unrelated send failure on this same
    connection trigger a second, spurious rollback attempt.

    NEVER RAISES, verified by read-back, same discipline as `park_warp_
    send` and `warp_target_record.clear_warp_target`.
    """
    try:
        setattr(session, SESSION_ATTRIBUTE, None)
    except Exception:  # noqa: BLE001
        return False
    try:
        return getattr(session, SESSION_ATTRIBUTE, None) is None
    except Exception:  # noqa: BLE001
        return False


def _parked_record(session: object) -> ParkedWarpSend | None:
    """The session's own park, or `None` for "empty or unreadable".

    A foreign, non-`ParkedWarpSend` value (nothing in this codebase writes
    one; defensive only) is treated the same as `None` rather than raising
    a comparison error two lines later in either observer -- this module
    only ever acts on records it wrote itself.
    """
    try:
        record = getattr(session, SESSION_ATTRIBUTE, None)
    except Exception:  # noqa: BLE001
        return None
    return record if isinstance(record, ParkedWarpSend) else None


def _note(session: object, event: str) -> None:
    """Append one event name, and never raise doing it.

    Same contract as `chat_command_action._note`, copied rather than
    imported: that module already imports FROM `warp_scene_persist`, which
    this module also imports from, and importing a private helper back out
    of a sibling that does not export it would be the wrong direction for a
    three-line function.
    """
    try:
        session.events.append(event)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - see docstring
        pass


def on_game_frame_sent(session: object, frame_bytes: object) -> str:
    """A frame really reached the wire on this connection.  Clear if ours.

    Called for EVERY frame this connection sends, not only a warp's, so
    `OUTCOME_NOTHING_PARKED` -- no read, no write, no comparison beyond the
    one attribute lookup -- must be, and is, the answer for most calls.

    Compares BYTES, not identity or label: the facade this is designed for
    (`CORE-REQUEST-GM-057`) only ever offers the raw frame it just sent, and
    a byte-identical frame from an unrelated command is not a fact this
    module has any way to rule out -- nor does it need to: two identical
    TeleportVital frames confirm the same destination row regardless of
    which command built them.

    NEVER RAISES.  A `frame_bytes` this module cannot coerce to `bytes` is
    treated as "not a match" -- fail closed, leaving the park in place for a
    later call that might actually confirm or fail it, rather than clearing
    on a comparison this module could not really make.
    """
    record = _parked_record(session)
    if record is None:
        return OUTCOME_NOTHING_PARKED
    try:
        matches = bytes(frame_bytes) == record.frame_bytes
    except Exception:  # noqa: BLE001 - see docstring
        matches = False
    if not matches:
        return OUTCOME_LEFT_PARKED_OTHER_FRAME
    outcome = (
        OUTCOME_CLEARED_OWN_FRAME
        if clear_warp_send_watch(session)
        else OUTCOME_CLEAR_NOT_CONFIRMED
    )
    _note(session, f"{EVENT_PREFIX}sent_{outcome}")
    return outcome


def on_game_frame_send_failed(session: object, frame_bytes: object, error: object) -> str:
    """A send failed on this connection.  Undo the row if one is unconfirmed.

    Called for EVERY failed send on this connection, not only a warp's --
    `OUTCOME_NOTHING_PARKED` must be, and is, the answer whenever the cell
    is empty, with no read of `frame_bytes` or `error` beyond that.

    DOES NOT COMPARE `frame_bytes` TO THE PARK.  See the module docstring's
    own paragraph on why: v141's send loop `break`s the WHOLE action list on
    the first failure, so a warp frame still parked can be orphaned by a
    DIFFERENT, earlier frame's failure without its own bytes ever reaching
    this function at all.  The only fact this function can act on is "this
    connection's socket just failed while a persisted warp was still
    unconfirmed", and that alone already means the client cannot have
    received the warp.

    Delegates the actual undo, and its outcome word, to `warp_scene_persist.
    rollback_warp_scene_on_send_failure` -- always with the one label this
    module ever parks under, never `frame_bytes` or `error` (that function
    reads the row to revert from `session.foundation.selected` itself; see
    its own docstring for why that is safe).  The park is cleared
    afterwards UNCONDITIONALLY, whether the undo itself reports success or
    a named failure: either way the story this cell was tracking is over,
    and leaving it parked would only make the NEXT unrelated failure on
    this connection attempt a second, spurious undo.

    NEVER RAISES: both the delegate and `clear_warp_send_watch` already
    carry that contract, and this function adds no operation of its own
    that could break it.
    """
    record = _parked_record(session)
    if record is None:
        return OUTCOME_NOTHING_PARKED
    outcome = rollback_warp_scene_on_send_failure(
        session, SEND_FAILURE_WARP_ACTION_LABEL,
    )
    clear_warp_send_watch(session)
    _note(session, f"{EVENT_PREFIX}failed_rollback_{outcome}")
    return outcome
