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
your hookup".  ~~chief's one line at the `connection.py` layer is the ONLY
thing standing between this module and a live send failure actually
reaching it; until that line lands, these functions simply never get
called by anything outside this lane's own tests and `chat_command_
action.py`'s own compose-time call below.~~  STRUCK by chief's own R348
(`pf_bridge/notes_to_chief/FROM_CHIEF_R348_TO_ALL_20260905_0505.md`): that
one line landed on main in server `#795` (`AcceptedGameSocket.sendall`
now offers `state.on_game_frame_sent` / `state.on_game_frame_send_failed`
if present -- see `connection.py`), and it was NOT the only thing standing
in the way.  A SECOND, separate gap sits on the other side of that opt-in
check: `state` in R348's own words is "no class in `src/` [that] declares
`on_game_frame_sent`/`on_game_frame_send_failed`" -- `getattr(self.state,
hook_name, None)` in `connection.py:150` finds nothing and returns without
ever reaching this module.  `park_warp_send` IS being called for real (the
one production call site, `chat_command_action._warp_teleport_action_no_
coords`), so a live send failure today still leaves the row parked FOREVER
with no observer to ever clear or roll it back -- worse than doing nothing,
because a tester reading `warp_send_watch.SESSION_ATTRIBUTE` off a session
that outlived one connection (it does not; sessions do not outlive their
socket) would have no reason to suspect it.  Closing that second gap means
adding two forwarding methods to the state class whose `self` the call
`connection_bindings.bind(self)` (`runtime.py:1599`) sits inside -- that
`self` already carries `self.foundation` and `self.events`, the exact
shape this module's functions read -- but `runtime.py` is chief's file
this lane may not edit (`AGENTS.md` section 7), so the exact two-method
body is handed over by letter (`CORE-REQUEST-GM-058`) rather than written
here.

R348 asks a second, harder question before that hookup is safe to arm:
"who accepts the offer, on which thread, under which lock" -- `sendall`'s
critical section (`current/pf_login_game_server_v141.py:7754` the action
loop, `:7427` `heartbeat_worker` every 2.0s once `teleport_sent`) is the
SAME `threading.Lock` on both call sites, so `_offer_send_outcome` -- and
therefore this module's two entry points, once wired -- can run on EITHER
thread, synchronously, while that lock is held.  ONE HALF OF THAT QUESTION
IS ANSWERED HERE, BY MEASUREMENT, NOT ARGUMENT
(`tests/test_gm_warp_send_watch.py::CrossThreadObserverTests`): the
`sqlite3.ProgrammingError` R348 named as the risk of "a consumer that
writes sqlite on another thread's connection" does not reach this module's
own database path, because `store.py`'s `SQLiteStore.connect()` opens and
closes a BRAND NEW connection inside the one call that uses it
(`store.py:285-305`) -- there is no connection object held across threads
for either `rollback_warp_scene` or `rollback_warp_scene_on_send_failure`
to collide on, on ANY thread that calls them.  Measured by calling both
observers from a background thread against the real store and reading the
row back on the main thread afterwards; see that test class for the
un-guessed half (`send_lock` hold time: a real rollback opens a real
connection and can block up to `PRAGMA busy_timeout=5000`'s five seconds
while holding the SAME lock the other thread needs for its own next send --
this module does not have an answer for that half, and does not pretend
to; see `CORE-REQUEST-GM-058`).

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
exception handling (~~`connection.py`'s proposed `_offer_send_outcome`~~
STRUCK -- landed on main in server `#795`, no longer proposed; itself
written to swallow and report whatever an observer raises) -- a raise from
a diagnostic must never mask or replace the send failure that triggered it.

CALLERS MUST SERIALIZE PER CONNECTION -- NOT THIS MODULE'S JOB, BUT NOT
OPTIONAL EITHER.  Neither `park_warp_send` nor `on_game_frame_send_failed`
takes a lock of its own: `_parked_record` (read) and `clear_warp_send_watch`
(write) are two separate attribute accesses, not one atomic operation, so
two truly concurrent callers for the SAME session can both read a non-empty
park before either clears it and both attempt the rollback (measured while
drafting `tests/test_gm_warp_send_watch.py::CrossThreadObserverTests`,
which deliberately does NOT exercise that shape -- see its own docstring).
This module gets away with having no lock of its own only because its one
real caller-to-be, `connection.py`'s `_offer_send_outcome`, is only ever
reached from inside `sendall()`, and every `sendall()` call for a given
connection is already made under that SAME connection's own `send_lock`
(`current/pf_login_game_server_v141.py:7754`, `:7427`) -- a per-connection
`threading.Lock`, not a global one, shared by the action loop and
`heartbeat_worker` for that one connection.  A caller outside that
discipline (a future hookup that offers frames without holding the sending
connection's own lock, or a lock shared incorrectly across connections)
would reintroduce the double-rollback race this paragraph names.  Naming
that requirement here is this module's whole contribution to `CORE-REQUEST-
GM-058`'s open threading question; enforcing it is the caller's.

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

from ..model import Position
from .warp_scene_persist import (
    SEND_FAILURE_WARP_ACTION_LABEL,
    rollback_warp_scene,
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

    `previous_position` is THE ROW TO PUT BACK, captured by the call site
    before its own durable write, and it is why round `ff30oi` widened this
    record.  It defaults to `None` so a park made without one still gets the
    older delegate path; see `on_game_frame_send_failed`.
    """

    label: str
    frame_bytes: bytes
    previous_position: object = None


def park_warp_send(
    session: object,
    frame_bytes: object,
    previous_position: object = None,
) -> bool:
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

    `previous_position` IS THE ROW THE UNDO MUST RESTORE, and passing it is
    what round `ff30oi` added.  NOT every park carries one, and the docstring
    that said it did was wrong (pf-adversary D-G): `_persist_warp_scene`
    returns `previous=None` whenever `row_before_warp` finds no row, and the
    call site still parks, because it branches on the write's outcome.  The
    reachable shape is a character with no `character_positions` row yet --
    its first-ever warp CREATES the row, so there is nothing to go back to.
    Those parks take the older delegate path in `on_game_frame_send_failed`.  Measured on this tree before it was added
    (`tests/test_gm_warp_send_watch.py::DoubleWarpTests`): with `/warp 2`
    confirmed sent and `/warp 3` then failing to send, the undo read
    `session.foundation.selected.position` and put the row back to scene 1 --
    the scene the client had already been sent OUT of, and one neither warp
    named.  `selected` is "the last position the CLIENT reported", which a
    warp deliberately does not update, so after a SECOND warp it is two
    warps stale rather than one.  The call site holds the right row
    (`_persist_warp_scene`'s own `previous`), so it hands it over rather
    than making the undo re-derive it from a field that cannot tell one
    warp from two.

    NO LABEL ARGUMENT, WHICH IS A DIFFERENT QUESTION.  This module never
    parks any label other than
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
    # THE OLDEST UNCONFIRMED ROW WINS, and it is the whole of pf-adversary's
    # D-A (round `ff30oi`, MEASURED).  A park that is still here has NOT been
    # confirmed sent -- `on_game_frame_sent` clears it the moment its own
    # bytes go out -- so the warp it belongs to may never have reached the
    # client either.  Taking the NEW `previous_position` on a replacement
    # would name the scene that warp wrote, and the undo would then move the
    # row FORWARD into a scene the client was never sent to: with `/warp 2`
    # and `/warp 3` both composed before either frame left the socket, the
    # first draft of this round left the row at 2 while the client sat in 1.
    # That is the bricking shape `rollback_warp_scene` exists to refuse, and
    # it was a REGRESSION -- the delegate this round replaced got it right.
    #
    # So a replacement keeps the row captured before the FIRST unconfirmed
    # warp.  One cell still tracks one frame (that is what the bytes are
    # for), but the row it would restore is the one that unwinds the whole
    # unconfirmed run, which is the only row that is correct however many
    # of those frames actually made it out.
    carried = previous_position
    standing = _parked_record(session)
    if standing is not None and standing.previous_position is not None:
        carried = standing.previous_position
    record = ParkedWarpSend(
        SEND_FAILURE_WARP_ACTION_LABEL, frame_bytes, carried,
    )
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

    WHICH ROW IT PUTS BACK, and the correction round `ff30oi` made.  When
    the park carries a usable `previous_position`, the undo goes to
    `warp_scene_persist.rollback_warp_scene` with THAT row: the row the call
    site captured with `row_before_warp` immediately before the FIRST
    unconfirmed warp's durable write (see `park_warp_send` on why a
    replacement carries the oldest one forward rather than its own).  It
    therefore unwinds the whole unconfirmed run, which is the only answer
    that is right however many of those frames actually reached the wire.

    ~~Delegates the actual undo, and its outcome word, to `warp_scene_persist.
    rollback_warp_scene_on_send_failure` -- always with the one label this
    module ever parks under, never `frame_bytes` or `error` (that function
    reads the row to revert from `session.foundation.selected` itself; see
    its own docstring for why that is safe).~~  STRUCK, and kept as the
    fallback for a park with no `previous_position` (a caller outside this
    lane, or a record built by hand): that delegate re-derives the row from
    `session.foundation.selected.position`, which is the last position the
    CLIENT reported.  A warp does not update it, so after TWO warps it is two
    warps stale and the undo overshoots -- measured, with `/warp 2` confirmed
    sent and `/warp 3` failing, putting the row back to scene 1.  See
    `DoubleWarpTests` in this module's test file.  The park is cleared
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
    # THE GATE IS "A ROW I CAN ACT ON", NOT "NOT NONE" -- pf-adversary's D-B
    # (MEASURED).  `rollback_warp_scene` answers
    # `OUTCOME_NOTHING_TO_ROLL_BACK` for anything that is not a `Position`,
    # so an `is None` test would send a wrong-TYPED row down the new path and
    # get no rollback AND no fallback: the net disarms itself silently on the
    # one shape it was widened for.  The label is checked here for the same
    # reason `rollback_warp_scene_on_send_failure` checks it -- that
    # discipline must not go dead just because the row now travels with the
    # park.
    usable = (
        record.label == SEND_FAILURE_WARP_ACTION_LABEL
        and isinstance(record.previous_position, Position)
    )
    if usable:
        outcome = rollback_warp_scene(session, record.previous_position)
    else:
        outcome = rollback_warp_scene_on_send_failure(
            session, SEND_FAILURE_WARP_ACTION_LABEL,
        )
    clear_warp_send_watch(session)
    _note(session, f"{EVENT_PREFIX}failed_rollback_{outcome}")
    return outcome
