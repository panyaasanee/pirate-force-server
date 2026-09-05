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
the session object has to ANSWER to those two names, at the call
`connection_bindings.bind(self)` (`runtime.py:1599`) whose `self` becomes
`AcceptedGameSocket.state` -- that `self` already carries
`self.foundation` and `self.events`, the exact shape this module's
functions read -- but `runtime.py` is chief's file this lane may not edit
(`AGENTS.md` section 7), so the code goes here and only the call goes to
him.  `install_send_outcome_observers` (bottom of this file, round
`goxj0y`) is that code: one call installs both forwards on one session,
weakly, idempotently, fail-closed.  `CORE-REQUEST-GM-058` had already
handed chief two forwarding METHODS to paste into his class; the
installer is offered as the alternative shape of the same hookup, so the
forwarding logic and its failure discipline stay in this lane's zone
instead of being copied into his.  Either shape closes the gap; ~~NEITHER
IS ON MAIN YET -- until one is, everything below is still reachable only
from this lane's own tests and `chat_command_action.py`'s compose-time
park.~~ **SHAPE B IS ON MAIN as of chief round `rs8uyz`/R350**: `runtime.py`
calls `install_send_outcome_observers(self)` on the line after
`connection_bindings.bind(self)`, so everything below now runs on every
accepted connection in production.  Struck rather than deleted, because
the sentence dates the change.  `HookupWiringPinTests` in this module's
test file is what forced this edit into the same commit as the call, and
it now pins the opposite answer -- if the call is ever reverted, that pin
goes red instead of this paragraph going quietly stale.  Shape A (two
forwarding methods on chief's class) is still not withdrawn and is still
compatible: the installer leaves any name that already resolves alone.

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
~~un-guessed half (`send_lock` hold time: a real rollback opens a real
connection and can block up to `PRAGMA busy_timeout=5000`'s five seconds
while holding the SAME lock the other thread needs for its own next send --
this module does not have an answer for that half, and does not pretend
to; see `CORE-REQUEST-GM-058`).~~  **MEASURED, round `j2jluj`**
(`COO-DECISION 20260905_0948` item 2(b) ordered the measurement rather than
another letter; `SendLockLivenessTests` in this module's test file IS the
measurement, and its numbers are re-derived there, not retyped here):

    contention held by another writer   this observer's hold   outcome
      none                                0.0023s              rolled_back
      1.0s                                1.035s               rolled_back
      3.0s                                3.038s               rolled_back
      7.0s                                5.010s               rollback_refused_OperationalError
     12.0s                                5.010s               rollback_refused_OperationalError

IT STALLS, AND ONE CALL'S STALL IS BOUNDED AT ONE `busy_timeout`, NOT TWO.
`checkpoint()` never reaches the read-back: `save_position`
(`store.py:668-671`) is a bare `with self.connect() as db:` + `UPDATE`, an
implicit DEFERRED transaction, and it is that `UPDATE` that waits and
raises, so the second connection the read-back would open is never opened.
The non-stacking therefore rests on WAL rather than on the transaction
shape -- `connect()` sets WAL only for a file database
(`store.py:293-294`) -- so `SendLockLivenessTests` asserts WAL is really in
force rather than assuming it.  `heartbeat_worker` wakes every 2.0s and
takes the SAME `send_lock`, so a worst-case hold makes it miss at most two
beats, on a connection whose socket has just failed.

THE WAIT IS NOT SHORTENED, AND THIS LANE CANNOT SHORTEN IT: `busy_timeout`
is set in `store.py`, outside this lane's zone, and shortening it would
trade a bounded delay on a dying connection for a durable row left naming a
scene the client never reached.

WHAT THE MEASUREMENT EXPOSED, AND WHY THIS FILE STILL DOES NOTHING ABOUT
IT.  The last two rows are runs in which the undo DID NOT HAPPEN and the
park was cleared anyway, so the row stays at the destination the client
never reached with nothing left on the connection that would ever try
again.  Round `j2jluj` built a re-park-and-retry for exactly that and
WITHDREW IT BEFORE PUSHING, on its own two `pf-adversary` passes:

  * pass 1 (D1): keeping the park removed the one thing that always retired
    one, and on a connection whose send error was TRANSIENT the record
    stayed armed and fired at logout, rewinding a position the player had
    legitimately walked to since.
  * pass 2 (D-1): the guard added for that compared
    `foundation.selected.position` against the park's pre-warp row -- but
    `runtime.py:6887` `_gm_warp_resync_selected_scene` rewrites
    `selected.position.scene_id` to the DESTINATION in the same dispatch
    that composed the warp, before any send.  So the guard answered "the
    world moved" for every cross-scene warp, immediately, with zero client
    frames: the retry could never complete and the give-up branch was
    unreachable.

Both are symptoms of a question this lane has not answered and will not
guess at under a deadline: WHICH POSITION IS THE UNDO'S AUTHORITY.  Three
different things are being read as one -- the durable `character_positions`
row, the in-memory `foundation.selected.position`, and "did the client
report something" -- and `runtime.py` writes the second without the first
and derives the first FROM the second on every movement frame.  The
question is in `notes_to_chief/20260905_1105_LANE-GM-ASK-COO-*`; until it
has an answer this module keeps the behaviour it had on `main`, which is
honest about losing the undo rather than wrong about restoring it.

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

~~WHERE THE UNDO'S `previous` COMES FROM IS NOT THIS MODULE'S PROBLEM.
`rollback_warp_scene_on_send_failure` reads `foundation.selected.position`
itself -- the pre-warp snapshot `persist_warp_scene` restores there the
moment the durable write lands (see that module's own docstring) -- so this
file never needs to carry a position of its own.  It only ever needs to
know ONE thing: is there still an unconfirmed persisted warp on this
connection, yes or no.~~  STRUCK by pf-adversary D10 (round `goxj0y`), which
caught this paragraph still asserting the story round `ff30oi` already
refuted 60 lines below it: `ParkedWarpSend.previous_position` exists
precisely because the delegate's re-derived row is two warps stale after two
warps, and `on_game_frame_send_failed` prefers `rollback_warp_scene(session,
record.previous_position)` when the park carries a usable one.  This file
DOES carry a position of its own, and it needs to know two things, not one.
The delegate path survives only as the fallback for a park without one.

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

import weakref
from dataclasses import dataclass, replace

from ..model import Position
from .warp_scene_persist import (
    OUTCOME_ROLLED_BACK,
    SEND_FAILURE_WARP_ACTION_LABEL,
    _console as _persist_console,
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

#: The four words `_restore_selected_scene` can answer (CORE-REQUEST-GM-059).
#: Every one of them reaches `session.events` under `EVENT_PREFIX` + `failed_`,
#: so the trail says which happened even when the durable row alone cannot:
#: a rollback that restored the label and one that could not both leave the
#: SAME row behind, and only the next walk frame tells them apart.
#: The in-memory label went back to the pre-warp scene, read back and confirmed.
SELECTED_SCENE_RESTORED = "selected_scene_restored"
#: The label was ALREADY the pre-warp scene: a same-scene warp, or a resync
#: that never ran.  Nothing was written -- distinguished from `RESTORED` so
#: the trail never claims work this module did not do.
SELECTED_SCENE_ALREADY_THERE = "selected_scene_already_there"
#: `foundation.selected.position` could not be read, is not a `Position`, or
#: its `scene_id` refused to compare.  Fail closed and say so; the durable row
#: is still correct.
SELECTED_SCENE_UNREADABLE = "selected_scene_unreadable"
#: The PARK carries no in-memory label (`previous_selected_scene_id` is None,
#: or not a real `int`).  Nothing is written: the durable row's scene is NOT a
#: stand-in for it (pf-adversary D1), so the honest answer is that this park
#: cannot say, not a plausible-looking guess.
SELECTED_SCENE_UNKNOWN = "selected_scene_unknown"
#: The assignment raised, or did not survive its own read-back.  The one
#: outcome that also prints a console line (see `_report_restore_failure`).
SELECTED_SCENE_NOT_RESTORED = "selected_scene_not_restored"

#: Console token for `SELECTED_SCENE_NOT_RESTORED`, the module's second one
#: (`INSTALL_CONSOLE_TOKEN` below is the first).  Spelled here rather than at
#: the print so the test that greps for it and the code that emits it cannot
#: drift.
RESTORE_FAILED_CONSOLE_TOKEN = "GM_WARP_SELECTED_SCENE_RESTORE_FAILED"

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

    `previous_selected_scene_id` is A DIFFERENT VALUE FROM A DIFFERENT PLACE,
    and round `bdl0w3` widened this record a second time rather than reusing
    the first (pf-adversary D1, MEASURED).  `previous_position` is the
    DURABLE `character_positions` row (`warp_scene_persist.row_before_warp`
    reads the store).  This is the IN-MEMORY label,
    `foundation.selected.position.scene_id`, read at compose time.  Treating
    them as one value is wrong on a live path: `lifecycle.py:311` writes the
    durable row only when `is_position_persist_allowed(scene_id)` says so,
    while `FoundationSession.checkpoint` updates `selected` unconditionally,
    so a session standing in scene 17 (`persist_position_allowed=False` in
    the world registry, and a scene `runtime.py` reaches on a flagless boot)
    has an in-memory 17 and a durable row naming some other scene entirely.
    A GM staged through the login-scene override is the same shape with no
    durable row written at all.  `_restore_selected_scene` undoes an
    IN-MEMORY relabel, so it needs the in-memory value; given the durable
    one it would confidently restore a scene the session was never in and
    the trail would call it `selected_scene_restored`.

    `None` means "this park does not know", and that is answered with its
    own word rather than a guess -- see `SELECTED_SCENE_UNKNOWN`.
    """

    label: str
    frame_bytes: bytes
    previous_position: object = None
    previous_selected_scene_id: object = None


def park_warp_send(
    session: object,
    frame_bytes: object,
    previous_position: object = None,
    previous_selected_scene_id: object = None,
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
    carried_label = previous_selected_scene_id
    standing = _parked_record(session)
    if standing is not None and standing.previous_position is not None:
        carried = standing.previous_position
    # THE LABEL CARRIES FORWARD ON ITS OWN CONDITION, not on the row's.
    # The two are separate values from separate places (see `ParkedWarpSend`),
    # and the row's carry-forward test is `standing.previous_position is not
    # None` -- a park whose row is None but whose label is known would lose
    # the label if it rode along on that test.  The REASON to carry forward is
    # identical though: after two unconfirmed warps the oldest label is the
    # one the client last really had, exactly as the oldest row is.
    if standing is not None and standing.previous_selected_scene_id is not None:
        carried_label = standing.previous_selected_scene_id
    record = ParkedWarpSend(
        SEND_FAILURE_WARP_ACTION_LABEL, frame_bytes, carried, carried_label,
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


def _restore_selected_scene(session: object, previous_scene_id: object) -> str:
    """Put the IN-MEMORY scene label back after a confirmed rollback.

    WHY THIS EXISTS (CORE-REQUEST-GM-059, chief's reply 20260905_1522
    handed the line back to this lane because every byte of it lives in
    `gm/`).  The order of a cross-scene `/warp <n>` whose frame then fails
    to send, MEASURED on a real SQLite store through `runtime.dispatch`:

    1. `warp_scene_persist.persist_warp_scene` writes the durable row to
       the DESTINATION and puts `foundation.selected` back the way it found
       it (`_restore_selected`, that module's line 1021) -- so the snapshot
       is clean at this point, and that is why the rollback of the DURABLE
       row is right.
    2. `runtime.py`'s `_gm_warp_resync_selected_scene` THEN relabels
       `selected.position.scene_id` to the destination, on purpose
       (CORE-REQUEST-GM-045: the census must read the new scene).
    3. The send fails.  `rollback_warp_scene` puts the DURABLE row back to
       `record.previous_position` and answers `OUTCOME_ROLLED_BACK`.
    4. Nobody undoes step 2.  The next ordinary movement frame reaches
       `runtime.py:4164`, which builds its `candidate` row with `scene_id`
       from `selected` and x/y/z from the CLIENT's report -- so one step of
       walking writes the durable row back to the destination scene the
       client was never sent to, with real coordinates from the scene it is
       really standing in.  The undo is silently spent.

    SCENE_ID ONLY, x/y/z/heading untouched -- the exact inverse of what
    step 2 changed, and no more.  A walk frame is EXPECTED to write new
    coordinates (that is `_checkpoint_exact_target`'s own change detection
    working), so pinning the pre-warp x/y here would be pinning a row that
    the very next honest report has to move.  `COO 1150`'s acceptance
    sentence asked for "scene AND coordinates before the warp"; the
    coordinate half is not reachable and `CORE-REQUEST-GM-059` says so.

    THE VALUE COMES FROM THE PARK'S `previous_selected_scene_id`, NOT FROM
    ITS `previous_position` (pf-adversary D1/D2, MEASURED, round `bdl0w3`).
    The first cut of this function took the durable row's scene, on the
    assumption that the durable row and the in-memory label agree before a
    warp.  They do not have to: `lifecycle.py:311` gates the durable write
    on `is_position_persist_allowed(scene_id)` while `FoundationSession.
    checkpoint` updates `selected` unconditionally, so a session in scene 17
    carries an in-memory 17 over a durable row naming something else.
    Measured, on that shape: `/warp 2` from an in-memory 17 with a durable
    row of 1 restored the label to **1** -- a scene the session had never
    been in -- and the trail said `selected_scene_restored`.  Worse,
    `/warp 1` answered `SELECTED_SCENE_ALREADY_THERE`, whose own meaning is
    "no relabel happened", two entries after
    `gm_warp_selected_scene_resynced_1` in the same trail.  Reading the
    label the resync actually overwrote is the only value that makes either
    word true, and the call site can read it for free at compose time --
    `persist_warp_scene` has already restored `selected` by then and the
    resync has not run yet.

    A PARK WITH NO LABEL ANSWERS `SELECTED_SCENE_UNKNOWN` AND WRITES
    NOTHING.  That is a park built outside this lane, or by hand -- the same
    population `previous_position`'s own `None` case serves.  Guessing the
    label from the durable row is exactly the defect above, so the honest
    answer is a word, not a write.

    ONLY ON `OUTCOME_ROLLED_BACK`, and only on the branch that carries a
    parked `previous_position`.  The fallback delegate
    (`rollback_warp_scene_on_send_failure`) derives the row it reverts to
    from `selected.position` itself, so there is no independent pre-warp
    scene here to restore and re-deriving one from the row it just wrote
    would be circular.

    NEVER RAISES: it is called from inside `on_game_frame_send_failed`,
    whose whole contract is that a failed send never costs the listener
    thread.  Every outcome is a WORD, appended to the session trail by the
    caller, so a dead line is visible in the trail and not only in a row.
    """
    # The park did not record what the label was.  Fail closed with a word.
    if not isinstance(previous_scene_id, int) or isinstance(
        previous_scene_id, bool
    ):
        # `bool` is an `int` in Python and `True == 1`, so a park carrying
        # `True` would restore scene 1 and look entirely ordinary doing it --
        # the same trap `#826`'s `class_id=True` fell into one lane over.
        return SELECTED_SCENE_UNKNOWN
    try:
        foundation = session.foundation  # type: ignore[attr-defined]
        selected = foundation.selected
        current = selected.position
    except Exception:  # noqa: BLE001 - see docstring
        return SELECTED_SCENE_UNREADABLE
    if not isinstance(current, Position):
        return SELECTED_SCENE_UNREADABLE
    try:
        already_there = current.scene_id == previous_scene_id
    except Exception:  # noqa: BLE001 - pf-adversary D6: `Position` is an
        # unvalidated dataclass, so a hand-built park can carry a `scene_id`
        # whose `__eq__` raises.  This comparison used to sit outside every
        # `try`, which made the NEVER RAISES contract two paragraphs up false
        # for exactly the population the `UNKNOWN` branch above exists for.
        return SELECTED_SCENE_UNREADABLE
    if already_there:
        # A same-scene warp, or a resync that never ran.  Nothing was
        # relabelled, so there is nothing to put back -- and answering
        # "restored" here would make the trail claim work this function
        # did not do.  Honest only because `previous_scene_id` is the label
        # the resync overwrote; against the durable row it was a lie (D2).
        return SELECTED_SCENE_ALREADY_THERE
    try:
        foundation.selected = replace(
            selected, position=replace(current, scene_id=previous_scene_id),
        )
    except Exception:  # noqa: BLE001 - see docstring
        _report_restore_failure(session, previous_scene_id)
        return SELECTED_SCENE_NOT_RESTORED
    # READ BACK, for the same reason `warp_scene_persist._restore_selected`
    # reads its own assignment back: a `__setattr__` that swallows the write
    # raises nothing, and a restore reported but not performed is exactly
    # the false report the durable read-back in that module exists to stop.
    try:
        landed = foundation.selected.position.scene_id == previous_scene_id
    except Exception:  # noqa: BLE001 - see docstring
        landed = False
    if not landed:
        _report_restore_failure(session, previous_scene_id)
        return SELECTED_SCENE_NOT_RESTORED
    return SELECTED_SCENE_RESTORED


#: The four attributes `runtime.py`'s warp-confirmation window is armed
#: through (`runtime.py:6750-6791`), spelled once here for the same reason
#: `SENT_OBSERVER_ATTRIBUTE` is: the other copy lives in a file this lane may
#: not edit, so a third spelling would drift silently.  Verified against
#: `runtime.py` on `main` this round, not from memory.
CONFIRM_WINDOW_ATTRIBUTES = (
    ("gm_warp_position_pending", False),
    ("gm_warp_confirm_window_open", False),
    ("gm_warp_confirm_target", None),
    ("gm_warp_confirm_target_reason", None),
)

#: The word for a disarm that had something to disarm, and for one that did
#: not.  Both are `_note`d: "the window was already shut" and "the window was
#: shut by this undo" are different facts about the same connection, and this
#: module's founding rule is that two different states never share a word.
CONFIRM_WINDOW_DISARMED = "confirm_window_disarmed"
CONFIRM_WINDOW_ALREADY_SHUT = "confirm_window_already_shut"


def _disarm_warp_confirm_window(session: object) -> str:
    """Shut the confirmation window a warp that never left the box opened.

    pf-adversary round `w7gah1`, D1 (CRITICAL, MEASURED WITH A CONTROL).  The
    previous round taught the send-failure undo to put the in-memory scene
    label back.  That fix is right and stays -- but it turned a loud failure
    into a false SUCCESS, because it restored ONE member of a set that
    `runtime.py`'s `_gm_warp_resync_selected_scene` writes as a group.

    Measured, `/warp 2` from scene 1 with `sendall` raising, then one ordinary
    step:

        restore OFF: verdict `mismatch` (43,413 units), token withheld -- correct
        restore ON:  verdict `unknown` (different scene), so `runtime.py:4227`
                     prints GM_WARP_POSITION_CONFIRMED, appends
                     `gm_warp_position_confirmed`, notes
                     `client_confirmed_scene_1_warp_confirmed` and CLEARS
                     `scene_label_is_server_guess`

    So the project's own warp proof token printed green for a warp whose
    frame never reached the wire, and the trail recorded a confirmation to a
    scene nobody warped to.  A false green is worse than the defect it hid:
    every gate in `EVIDENCE_GATES.md` that reads that token reads it wrong.

    THE INVERSE HAS TO INCLUDE THE WINDOW, because the window is what makes
    the label mean something.  The resync arms `gm_warp_position_pending` and
    parks `gm_warp_confirm_target` at the DESTINATION's spawn; putting the
    label back while leaving that armed asks the next walk step "does the
    client agree with a warp?" about a warp that was undone -- and
    `distance_to_target` cannot answer across scenes, so it answers
    `unknown`, which `runtime.py` reads as "not a mismatch" and therefore as
    confirmation.

    UNCONDITIONAL ON THE SEND FAILURE, not on the rollback's outcome.  The
    frame did not reach the wire; that alone is the whole reason the window is
    wrong, and it is true whether or not the durable undo then succeeded.
    Gating this on `OUTCOME_ROLLED_BACK` would leave the false-confirm path
    open on exactly the runs where the row could not be put back -- the ones
    already in the worst state.

    WHAT IT DOES NOT TOUCH, on purpose: `scene_label_is_server_guess`.  After
    an undone warp that flag is HONESTLY set -- the client has confirmed
    nothing -- and this lane has asked chief to restore its pre-warp value in
    `CORE-REQUEST-GM-060` rather than guess at one here.  Clearing it would be
    the same class of lie this function exists to stop.

    NEVER RAISES: a session that refuses attributes answers a word.
    """
    touched = False
    for name, cleared in CONFIRM_WINDOW_ATTRIBUTES:
        try:
            if getattr(session, name, cleared) == cleared:
                continue
        except Exception:  # noqa: BLE001 - a property that raises on read
            continue
        try:
            setattr(session, name, cleared)
        except Exception:  # noqa: BLE001 - a session that refuses writes
            continue
        touched = True
    return CONFIRM_WINDOW_DISARMED if touched else CONFIRM_WINDOW_ALREADY_SHUT


def _report_restore_failure(session: object, scene_id: object) -> None:
    """One console line for the one outcome nobody could otherwise see.

    The durable row IS correct when this prints -- `rollback_warp_scene`
    already confirmed it -- so this is not a bricked character.  It is the
    state where the next walk frame will re-break the row, and the tester
    watching the console is the only reader who can act on it before that
    happens.  Losing the line costs nothing else (`_persist_console`
    already answers False rather than raising on a dead stderr).
    """
    if not _persist_console(f"{RESTORE_FAILED_CONSOLE_TOKEN} scene={scene_id}"):
        _note(session, f"{EVENT_PREFIX}console_lost_{SELECTED_SCENE_NOT_RESTORED}")


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
        if outcome == OUTCOME_ROLLED_BACK:
            # GM-059.  The durable row is back in the departure scene; the
            # IN-MEMORY label is not, and nothing else in the tree puts it
            # back.  See `_restore_selected_scene` for the measured defect
            # this closes.
            _note(
                session,
                f"{EVENT_PREFIX}failed_"
                f"{_restore_selected_scene(session, record.previous_selected_scene_id)}",
            )
    else:
        # THE LABEL GOES BACK FIRST, AND THE ORDER IS THE FIX (pf-adversary
        # round `w7gah1`, D2, MEASURED).  This delegate re-derives the row it
        # reverts to from `foundation.selected.position` -- which the resync
        # has ALREADY moved to the destination.  So on a park whose
        # `previous_position` is missing (a transient read failure at compose
        # time is enough: this module's own `SendLockLivenessTests` measured
        # `rollback_refused_OperationalError` under contention) the "rollback"
        # wrote the durable row FORWARD to the destination scene the client
        # was never sent to, reported it as `rolled_back`, and the next login
        # landed there.  Measured: row `1 -> 2` under the word `rolled_back`.
        #
        # The park held `previous_selected_scene_id` the whole time and the
        # branch did not use it.  Putting the label back BEFORE delegating
        # makes the delegate re-derive from the departure scene, which is the
        # row it was always documented to write.  A park with no label answers
        # `SELECTED_SCENE_UNKNOWN`, writes nothing, and this branch then
        # behaves exactly as it did before -- the honest old behaviour for the
        # only population that cannot be helped.
        _note(
            session,
            f"{EVENT_PREFIX}failed_"
            f"{_restore_selected_scene(session, record.previous_selected_scene_id)}",
        )
        outcome = rollback_warp_scene_on_send_failure(
            session, SEND_FAILURE_WARP_ACTION_LABEL,
        )
    # D1, and deliberately outside both branches: the frame did not reach the
    # wire, so the confirmation window this warp opened is wrong however the
    # durable undo went.  See `_disarm_warp_confirm_window` for the measured
    # false `GM_WARP_POSITION_CONFIRMED` that leaving it armed produces.
    _note(session, f"{EVENT_PREFIX}failed_{_disarm_warp_confirm_window(session)}")
    clear_warp_send_watch(session)
    _note(session, f"{EVENT_PREFIX}failed_rollback_{outcome}")
    return outcome


#: The two attribute names `connection.py`'s `AcceptedGameSocket._offer_
#: send_outcome` looks up with `getattr(self.state, hook_name, None)`
#: (`connection.py:150`).  Spelled once, here, so this module and the
#: installer below cannot drift onto a third spelling of a string whose
#: only other copy lives in a file this lane may not edit.  Verified
#: against that file on `origin/main` this round, not from memory.
SENT_OBSERVER_ATTRIBUTE = "on_game_frame_sent"
FAILED_OBSERVER_ATTRIBUTE = "on_game_frame_send_failed"

#: Console token every outcome of `install_send_outcome_observers` prints,
#: on stderr, exactly once per connection.  pf-adversary D1/D3 (MEASURED,
#: round `goxj0y`): the installer used to be the ONE function in this module
#: that refused without saying so -- no `_note`, no console line -- while
#: its only intended caller is a bare statement in `runtime.py` that
#: discards the return value.  A refusal on a live connection was therefore
#: invisible to chief, to CI, and to the owner's console alike, and the
#: whole suite was bit-identical whether the hookup was armed, absent, or
#: silently disarmed.  A word nobody can read is not an answer.
INSTALL_CONSOLE_TOKEN = "GM_WARP_SEND_OBSERVERS"

#: Both names were absent and both forwards landed.
INSTALL_OK = "installed"
#: BOTH names already resolve -- chief's own two methods
#: (`CORE-REQUEST-GM-058` shape A), or a second install on this connection.
#: Nothing is written: an instance attribute would SHADOW a class method, so
#: an installer that overwrote would silently disarm the very hookup it is
#: standing in for.
INSTALL_REFUSED_ALREADY_PRESENT = "refused_already_present"
#: EXACTLY ONE name resolved, and this call supplied the other.
#:
#: pf-adversary D1 (MEASURED, round `goxj0y`).  Refusing outright on "at
#: least one present" was measured to be worse than doing nothing, in the
#: real facade, against the real store: with only `on_game_frame_send_failed`
#: declared, a `/warp` whose frame REALLY REACHED THE WIRE is never cleared
#: (no success observer), and the next unrelated disconnect on that same
#: connection rolls the durable row back to the origin scene while the
#: client is really standing in the destination.  That is durable position
#: corruption caused by refusing.  Supplying only the MISSING name shadows
#: nothing -- the name being written did not resolve -- and completes a pair
#: that is meaningless half-declared.  It is still a defect in whatever
#: declared one half, so it gets its own word and its own console line
#: rather than being folded into `installed`.
INSTALL_COMPLETED_HALF_DECLARED = "completed_half_declared"
#: `setattr` raised, or the read-back did not find what was written (a
#: session that swallows attribute writes, `__slots__`, a read-only
#: property).  Any partial install is undone before returning; see the
#: function body.
INSTALL_REFUSED_NOT_WRITABLE = "refused_not_writable"


def _announce_install(session: object, outcome: str) -> str:
    """Say the outcome out loud, then return it.  Never raises.

    pf-adversary D1/D3 (MEASURED, round `goxj0y`).  Every other refusal in
    this module reaches a reader: `park_warp_send`'s `False` becomes
    `chat_command_action.EVENT_WARP_SEND_WATCH_NOT_PARKED`, the rollbacks
    print `warp_scene_persist.ROLLBACK_CONSOLE_TOKEN`.  The installer
    reported only through a return value that its one intended caller -- a
    bare statement in `runtime.py` -- throws away, so a live connection that
    refused was invisible everywhere: no event, no console line, and the
    whole suite bit-identical whether the hookup was armed or silently
    disarmed.  Two channels, because they answer different people: the
    event trail is what a test or a lane reads back, the stderr token is
    what the owner greps in a boot log.

    STDERR, VIA `warp_scene_persist`'S OWN GUARDED WRITER, NOT `print`.
    `sys.stderr` can be `None` (a detached console, `pythonw`), and `print`
    reads `file=None` as "use stdout" and writes the token there without
    raising -- the `lane_hooks` JSON-artifact incident (pf-adversary round
    `741zlx`, finding 3).  Reusing that module's `_console` rather than
    copying its guard means this line cannot drift away from the fix.
    """
    _note(session, f"{EVENT_PREFIX}install_{outcome}")
    try:
        _persist_console(f"{INSTALL_CONSOLE_TOKEN} {outcome}")
    except Exception:  # noqa: BLE001 - the report must never raise
        pass
    return outcome


def install_send_outcome_observers(session: object) -> str:
    """Give one session the two names `connection.py` looks for.  Never raises.

    WHY THIS EXISTS.  `#795` landed the first layer -- `AcceptedGameSocket.
    sendall` offers each send's outcome to `state.on_game_frame_sent` /
    `state.on_game_frame_send_failed` "if present".  R348's own measurement
    (`pf_bridge/notes_to_chief/FROM_CHIEF_R348_TO_ALL_20260905_0505.md`) is
    that NO class in `src/` declares either name, so that `getattr` finds
    nothing and this module is never reached: `park_warp_send` is already
    called in production and a live send failure today leaves the row parked
    forever.  Closing that needs the session object to answer to those two
    names.  `CORE-REQUEST-GM-058` hands chief two forwarding methods for
    `runtime.py` (his file, `AGENTS.md` section 7); THIS function is the
    same hookup as a single call this lane owns and tests, so that whichever
    shape chief prefers, the forwarding logic and its failure discipline
    stay in this lane's zone instead of being copied into his.

    WHERE IT IS MEANT TO BE CALLED, AND WHY THAT PLACE AND NOT ANOTHER.
    Once, per connection, on the connection's own thread, at the point that
    already binds this session to its accepted socket -- `connection_
    bindings.bind(self)` (`runtime.py:1599`), whose `self` is the SAME
    object `connection.py` then stores as `AcceptedGameSocket.state`
    (`connection.py:92`) and reads the two names off.  Installing there
    means both forwards exist before this connection's first send, so no
    frame can slip through the window between bind and install.  It is also
    provably single-threaded: v141 constructs the state at `:7399` and only
    starts `hb_thread` at `:7439`, so the install completes before the only
    other thread that could touch this connection exists.

    EACH NAME IS DECIDED SEPARATELY -- pf-adversary D1 (MEASURED).  A name
    that ALREADY resolves is never touched, because an instance attribute
    would shadow a real class method and silently disarm the very hookup
    this stands in for.  A name that does NOT resolve is supplied, even when
    its partner is already there.  Refusing outright on "at least one
    present" was measured, in the real facade against the real store, to be
    WORSE than doing nothing: with only `on_game_frame_send_failed`
    declared, a `/warp` whose frame really reached the wire is never cleared
    and the next unrelated disconnect rolls the durable row back while the
    client is standing in the destination scene.  Completing the pair
    shadows nothing and cannot produce that.  Three answers, not two:
    `installed` (both were absent), `completed_half_declared` (exactly one
    was, and this call supplied the other -- still somebody's defect, so it
    keeps its own word), `refused_already_present` (both were).

    THE SESSION IS HELD WEAKLY, ON PURPOSE.  A closure that captured the
    session strongly and was then stored ON that session is a reference
    cycle, freed by a full `gc` pass and not by refcount -- measured, with
    the collector disabled.  ~~and `lane_hooks`'s live-session registry
    holds sessions by WEAK reference precisely so a dead connection's
    session stops answering `current_session_scene_id` promptly; a cycle
    here would keep dead sessions answering for another lane until the
    collector happened to run.~~  HALF STRUCK by pf-adversary D6 (MEASURED):
    that registry is a `WeakValueDictionary` (`lane_hooks/__init__.py:
    955-957`) and its assignment is UNGUARDED, so `register_live_session`
    RAISES `TypeError` for a session that cannot be weak-referenced -- such
    a session can never be in the registry, and therefore the fallback
    branch below can never cause the harm that sentence used it to justify.
    The weak default is still right for the ordinary path (the real state
    class IS weak-referenceable, so that is the branch production takes);
    the fallback is there only so a `__slots__` session gets a working
    rollback instead of a refusal, and it is honest to say it protects
    nothing else.

    NEVER RAISES, and read-back is the proof, not `setattr` returning --
    the same discipline `park_warp_send` and `clear_warp_send_watch` carry,
    for the same reason (`_RefusingSession` in this module's test file).
    Every outcome, including both refusals, is announced on the event trail
    and on stderr by `_announce_install`; see that function on why a return
    value alone was not an answer.
    """
    try:
        present = tuple(
            getattr(session, name, None) is not None
            for name in (SENT_OBSERVER_ATTRIBUTE, FAILED_OBSERVER_ATTRIBUTE)
        )
    except Exception:  # noqa: BLE001 - a session whose getattr raises
        return _announce_install(session, INSTALL_REFUSED_NOT_WRITABLE)
    if all(present):
        return _announce_install(session, INSTALL_REFUSED_ALREADY_PRESENT)

    try:
        holder = weakref.ref(session)
    except TypeError:
        # Not weak-referenceable; see the docstring on why this still
        # installs rather than refusing.
        strong = session

        def holder():  # type: ignore[misc]
            return strong

    def _sent(frame_bytes: object) -> str:
        live = holder()
        if live is None:
            return OUTCOME_NOTHING_PARKED
        return on_game_frame_sent(live, frame_bytes)

    def _failed(frame_bytes: object, error: object) -> str:
        live = holder()
        if live is None:
            return OUTCOME_NOTHING_PARKED
        return on_game_frame_send_failed(live, frame_bytes, error)

    # PER NAME, NOT ALL-OR-NOTHING -- pf-adversary D1 (MEASURED).  A name
    # that already resolves is left strictly alone (never shadowed); a name
    # that does not is supplied.  `all(present)` above already returned, so
    # at least one name is being written here.
    written = []
    for already, name, forward in (
        (present[0], SENT_OBSERVER_ATTRIBUTE, _sent),
        (present[1], FAILED_OBSERVER_ATTRIBUTE, _failed),
    ):
        if already:
            continue
        try:
            setattr(session, name, forward)
            landed = getattr(session, name, None) is forward
        except Exception:  # noqa: BLE001 - see docstring
            landed = False
        if not landed:
            # Undo whatever this call itself put on, and ONLY that -- a
            # connection left with only the success forward would clear
            # parks it can never roll back, strictly worse than having
            # neither.  A name that was already there when this call
            # started is never in `written`, so it is never disturbed.
            for done in written:
                try:
                    setattr(session, done, None)
                except Exception:  # noqa: BLE001
                    pass
            return _announce_install(session, INSTALL_REFUSED_NOT_WRITABLE)
        written.append(name)
    return _announce_install(
        session,
        INSTALL_COMPLETED_HALF_DECLARED if any(present) else INSTALL_OK,
    )
