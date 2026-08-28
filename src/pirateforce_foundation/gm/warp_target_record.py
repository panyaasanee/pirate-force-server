"""Where the last accepted `/warp` sent ONE connection, for one frame.

WHY THIS MODULE EXISTS.  `runtime.py` prints `GM_WARP_POSITION_CONFIRMED`
when the first TargetPos report after a GM warp causes a real durable
position write (chief, `CORE-REQUEST-GM-030`, merged as PR #212).  Chief's
own reply filed the limit of that token in writing
(`notes_to_chief/20260828_2301_CHIEF-REPLY-LANE-GM-030-wired-029-deferred.md`,
appendix item 5): the action tuple `(label, pc, frame, delay)` that
`chat_command_action.make_gm_chat_command_action` returns carries no
destination, so the token can only mean "a row was written", never "the row
is the point the GM asked for".  Chief cannot fix that from `runtime.py` --
the destination only exists inside this lane -- and asked this lane to expose
it.  This module is that half.

WHAT IT DOES NOT DO, DELIBERATELY.  It does not decide anything and it sends
nothing.  It parks one `WarpTarget` on the session that a warp frame was just
built for, and hands it back once.  Whether a later position row counts as a
match is the caller's call; `position_matches_target` only offers this lane's
arithmetic and its stated tolerance.

WHY THE SESSION OBJECT AND NOT A MODULE-LEVEL DICT.  The record must have
exactly the lifetime of the connection it belongs to, and must never be
readable from another connection: a module-level map keyed by session would
outlive dropped sockets (a leak per connection, plus a stale target that a
reconnecting GM could collect), and keyed by anything coarser -- account,
token -- it would hand connection A's target to connection B, which is the
same identity confusion `runtime.py`'s `IDENTITY, STATED HONESTLY` comment
records already has, and this lane
refuses to add a second copy of.  An attribute on the session dies with the
session, for free.  `runtime.py` already carries chief's own
`gm_warp_position_pending` flag the same way, so the shape is not new.

CONSUME-ONCE, AND WHY IT IS NOT OPTIONAL.  `take_warp_target` clears what it
returns.  RE-129 measured the client's ForcePos handler as `mov al,1;
ret 4` -- it ignores the frame -- so the realistic sequence today is: warp,
then a TargetPos report at the OLD position, then the GM walks.  A target
that survived to the second report would be compared against a position the
warp never caused, and would report a mismatch (or, worse, a match if the GM
happened to walk there) about the wrong frame entirely.  Chief's own
arming flag learned this the hard way -- pf-adversary made it fire on a
player's own footstep before the window was narrowed to one frame -- so this
record narrows the same way, on purpose.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .warp_executor import WarpTarget

# The attribute the record is parked under.  Named here so that the writing
# side and the reading side cannot drift apart, and so `runtime.py` (chief's
# zone) can import the accessor functions instead of hardcoding a string that
# this lane would then be unable to rename.
SESSION_ATTRIBUTE = "gm_last_warp_target"

# Returned by `current_character_id` when the connection HAS a character whose
# id this module could not read as an int.
#
# It exists because pf-adversary broke the first draft, which returned None for
# that case as well as for "no character selected": two connections that both
# fail to read an id would then compare equal, and one GM's destination would
# be handed to another character -- the exact leak this module's docstring says
# it prevents.  A sentinel cannot be confused with a real id, and
# `take_warp_target` refuses whenever either side is this value rather than
# comparing them, so an unreadable id fails closed on BOTH sides instead of
# matching itself.
UNREADABLE_CHARACTER_ID = object()

# Why `take_warp_target_with_reason` exists at all.  pf-adversary's finding:
# mapping every not-comparable state onto one silent "unknown" makes a
# permanent disagreement between this lane's belt and chief's produce exactly
# the output of a GM who never typed `/warp` -- and this record exists BECAUSE
# "did not move" and "moved to the wrong place" must stop looking identical.
# The reason is the caller's to log; the plain `take_warp_target` below is the
# same call with the reason dropped, for callers that do not log.
REASON_OK = "ok"
REASON_NOTHING_PARKED = "nothing_parked"
REASON_FOREIGN_VALUE = "foreign_value"
REASON_CHARACTER_MISMATCH = "character_mismatch"
REASON_CHARACTER_UNREADABLE = "character_unreadable"
REASON_NOT_CLEARED = "not_cleared"

# How close a reported position has to be to the target before this lane will
# call it the same point, in world units.
#
# [สมมติของสาย GM - รอ COO ยืนยัน]  Nothing in this repo has measured how far
# a client lands from a point the server sent it to, because no client has
# ever honored one of our ForcePos frames (RE-129).  What IS measured:
# `teleport_wire` puts the coordinate on the wire as IEEE binary32, whose
# spacing at the owner's own test coordinates (X 11,865 / Y 6,147) is about
# 0.001 units -- three orders of magnitude below this tolerance -- so the
# encoding can never be what makes a comparison fail here, which is the one
# error this number has to be immune to.  The number is otherwise
# deliberately small: `move_authority_hypothesis` records that a continuous
# moving run steps 400-500 units between reports, so a GM walking away from
# the point cannot stay inside 1.0 by accident for a whole frame.
# If an attended run ever measures a real snap distance, replace this with
# the measurement and say so; do not widen it to make a red comparison green.
WARP_TARGET_MATCH_TOLERANCE = 1.0


@dataclass(frozen=True)
class WarpTargetRecord:
    """One parked target, plus who it was parked for."""

    target: WarpTarget
    # The character selected on the connection at the moment the warp frame
    # was built, or None if the connection had none.  A GM who warps, then
    # re-selects, then walks would otherwise have the second character's
    # position measured against the first character's destination.  Chief
    # binds his own pending flag to `character.id` for exactly this reason
    # (his appendix item 4); the two halves have to agree or the comparison
    # is about two different actors.
    character_id: int | None


def current_character_id(session: object):
    """The id of the character selected on this connection.

    Three outcomes, deliberately distinct: an `int`; `None` for "no character
    selected"; `UNREADABLE_CHARACTER_ID` for "there is a character but its id
    is not an int".  See that constant for why the last two must not be the
    same value.

    Defined here rather than at each call site so the recording side and the
    reading side read it from the same place: a mismatch check is worthless
    if the two sides can disagree about where the id lives.

    Never raises.  It runs on the game-listener thread AFTER a warp frame has
    already been built, so a session whose `id` is a property that raises must
    cost the comparison, never the warp -- pf-adversary reproduced exactly
    that, with the frame discarded and the event trail blaming this module.
    """
    try:
        selected = getattr(getattr(session, "foundation", None), "selected", None)
        if selected is None:
            return None
        identifier = getattr(selected, "id", None)
    except Exception:  # noqa: BLE001 - see docstring; nothing escapes this module
        return UNREADABLE_CHARACTER_ID
    if identifier is None:
        return None
    return identifier if type(identifier) is int else UNREADABLE_CHARACTER_ID


def record_warp_target(session: object, target: WarpTarget, character_id) -> bool:
    """Park `target` on `session`, replacing any target already there.

    Returns whether it was parked.  Replacing is correct, not lossy: two
    warps before any position report means the older frame's destination can
    no longer be what the next report is about.  Never raises -- a session
    that refuses attributes (`__slots__`, a read-only test double) must cost
    the caller a lost comparison, not a crashed listener thread, since the
    frame itself has already been built by the time this runs.
    """
    if not isinstance(target, WarpTarget):
        return False
    record = WarpTargetRecord(target, character_id)
    try:
        setattr(session, SESSION_ATTRIBUTE, record)
    except Exception:  # noqa: BLE001 - see docstring; nothing escapes this module
        return False
    # Read it back.  pf-adversary's finding: a session whose `__setattr__`
    # SWALLOWS the write raises nothing, so returning True on "the call did
    # not raise" reports a parked target that is not there, and the caller
    # emits no event about it.  Verifying costs one attribute read and turns
    # that into the same named refusal as a session that raises.
    try:
        return getattr(session, SESSION_ATTRIBUTE, None) is record
    except Exception:  # noqa: BLE001
        return False


def take_warp_target_with_reason(session: object, character_id):
    """`(record, reason)` -- the parked record and why, or `(None, why not)`.

    Every `None` here has a different cause and a caller that logs the reason
    can tell them apart: nothing was parked at all (the ordinary case: no warp
    happened), a value this module did not write, a changed character, an
    unreadable character on either side, or a record that could not be
    cleared.  That last one is why this returns None: if the clear failed, the
    record is still on the session, so handing it out once would be handing it
    out again on the next frame.  Fail closed -- a comparison lost is cheap,
    a comparison about the wrong frame is a lie.
    """
    try:
        record = getattr(session, SESSION_ATTRIBUTE, None)
    except Exception:  # noqa: BLE001 - see module docstring
        return None, REASON_NOTHING_PARKED
    if record is None:
        return None, REASON_NOTHING_PARKED
    cleared = clear_warp_target(session)
    if not isinstance(record, WarpTargetRecord):
        return None, REASON_FOREIGN_VALUE
    if (
        record.character_id is UNREADABLE_CHARACTER_ID
        or character_id is UNREADABLE_CHARACTER_ID
    ):
        # Never compared, on purpose: two unreadable ids are not evidence of
        # the same character, and `is` would make the sentinel match itself.
        return None, REASON_CHARACTER_UNREADABLE
    if record.character_id != character_id:
        return None, REASON_CHARACTER_MISMATCH
    if not cleared:
        return None, REASON_NOT_CLEARED
    return record, REASON_OK


def take_warp_target(session: object, character_id) -> WarpTargetRecord | None:
    """`take_warp_target_with_reason` with the reason dropped."""
    record, _reason = take_warp_target_with_reason(session, character_id)
    return record


def clear_warp_target(session: object) -> bool:
    """Drop any parked record; whether it is now gone.

    Never raises, for `record_warp_target`'s reason: this runs on the dispatch
    path.  The return value is not decoration -- a session that swallows the
    write leaves the record in place, and `take_warp_target_with_reason` has
    to refuse rather than hand out a record it could not consume.
    """
    try:
        setattr(session, SESSION_ATTRIBUTE, None)
    except Exception:  # noqa: BLE001
        return False
    try:
        return getattr(session, SESSION_ATTRIBUTE, None) is None
    except Exception:  # noqa: BLE001
        return False


def distance_to_target(target: WarpTarget, position: object) -> float | None:
    """3-D distance from `position` to `target`, or None if not comparable.

    None -- not a large number and not an exception -- is the answer whenever
    the two are not the same kind of thing: a different scene (ForcePos
    carries no scene id, so a row in another scene cannot be the result of
    this frame), a position missing a coordinate, or any non-finite value.
    A caller that logs the distance therefore logs a number only when a
    number means something.

    The distance is 3-D on purpose even though `z` came from the connection's
    own current z: if the client ever does honor a ForcePos, a report that
    matches in x/y but not in z is exactly the "it moved, but not to where we
    said" case this whole comparison exists to make visible.
    """
    if not isinstance(target, WarpTarget):
        return None
    scene_id = getattr(position, "scene_id", None)
    if type(scene_id) is not int or scene_id != target.scene_id:
        return None
    total = 0.0
    for axis in ("x", "y", "z"):
        try:
            reported = getattr(position, axis, None)
        except Exception:  # noqa: BLE001 - a position whose axis is a raising
            # property must cost the comparison, not the listener thread.
            return None
        if not isinstance(reported, (int, float)) or isinstance(reported, bool):
            return None
        try:
            reported = float(reported)
        except (OverflowError, ValueError):
            # `isinstance(x, int)` admits arbitrary precision: `float(10**400)`
            # raises OverflowError, which pf-adversary reproduced escaping this
            # function even though the guard three lines down already knew that
            # exception had to be caught.
            return None
        if not math.isfinite(reported):
            return None
        try:
            total += (reported - getattr(target, axis)) ** 2
        except OverflowError:
            # Measured, not theorised: a finite coordinate of 1e200 raises
            # here rather than returning inf, so an unguarded square turns a
            # malformed row into an exception on the dispatch path.  "Too far
            # to say" is the honest reading of it, and it is not a match.
            return None
    if not math.isfinite(total):
        return None
    return math.sqrt(total)


def position_matches_target(
    target: WarpTarget,
    position: object,
    *,
    tolerance: float = WARP_TARGET_MATCH_TOLERANCE,
) -> bool:
    """Whether `position` is the point `target` sent the connection to.

    False for every not-comparable case, by construction: `None` from
    `distance_to_target` is not a match.  A True here still is NOT evidence
    that the warp moved anyone -- a GM standing where he warped to would
    match too.  It is evidence about the ROW, which is all chief's token
    claims to be about.
    """
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        return False
    try:
        tolerance = float(tolerance)
    except (OverflowError, ValueError):
        return False
    if not math.isfinite(tolerance) or tolerance < 0.0:
        # `tolerance=float("inf")` would match every comparable position,
        # which is a caller turning this function into `return True` while
        # still reading as a measurement.  Refuse instead: a nonsense
        # tolerance is not a match.
        return False
    distance = distance_to_target(target, position)
    if distance is None:
        return False
    return distance <= tolerance
