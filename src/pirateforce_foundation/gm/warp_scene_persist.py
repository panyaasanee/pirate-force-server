"""Write a live `/warp`'s DESTINATION SCENE into the row, at send time.

WHY THIS MODULE EXISTS.  `PANYA-DECISION 2026-09-04 14:30 +07:00`
(`pf_bridge/notes_to_chief/20260904_1430_PANYA-DECISION-a-live-warp-must-
persist-the-scene-immediately-even-if-the-player-never-walks.md`), routed to
this lane by `COO-DECISION 20260904_1452`.  Measured in the attended round
R309, in the owner's own words: `/warp 2` from Port Royal printed
`WORLD_SCENE scene_id=2` and the screen changed; closing the client with X
left `character_positions` reading `scene_id=1` at the pre-warp point, so the
next login came back to Port Royal.  Walking ONE STEP first wrote
`scene_id=2 (26414, 20998)` and the next login landed correctly.

So the durable write in this project has always been a property of the WALK
frame (`runtime.py`'s TargetPos branch -> `foundation.checkpoint`), never of
the warp.  `GT-172` finding F-3 is that gap.  The owner's ruling is that a
tester must not have to remember a special condition ("walk before you close
it") to make a warp stick.  This module is the write that removes it.

WHAT IT IS NOT.  It does not send anything, decide anything about routing, or
touch `store.py`.  It goes through the DB write door that already exists and
that every other durable position write in this project uses --
`FoundationSession.checkpoint` -> `lifecycle.checkpoint` ->
`store.save_position` -- so the ownership check, the
`is_position_persist_allowed` gate and the in-memory `selected` update all
behave here exactly as they do on a walk frame.  `COO 1452` item 2 requires
that door and forbids new SQL; this module is what keeps that requirement in
one place instead of at each warp branch.

THE POSITION IT WRITES IS THE FRAME'S OWN, NOT A SECOND OPINION.  Every
coordinate comes off the `WarpTarget` the composer handed back, which is
already the binary32 value ON THE WIRE (see `warp_executor.WarpTarget`).  A
row derived from anything else -- the registry read a second time, the GM's
typed arguments -- could differ from what the client was told in the last
place anyone would look for it.  `scene_seq` is
`world_scene_travel.SCENE_SEQUENCE`, the same constant the composer put in
the frame; `heading` is CARRIED OVER from the row the connection already has,
because a TeleportVital carries no heading and inventing one would rotate a
character nobody asked to rotate.

READ-BACK IS NOT DECORATION (`COO 1452` item 2, "อ่านกลับหลังเขียน").
`lifecycle.checkpoint` calls `store.save_position(..., write_position=allowed)`
and, for a scene pinned `persist_position_allowed=False`, that call RETURNS
CLEANLY HAVING WRITTEN NO ROW.  Without reading the row back, this module
would print a token saying the scene was persisted over a row that still
holds the old scene -- the same false-token shape `runtime.py`'s own
`GM_WARP_POSITION_CONFIRMED` comment records paying for once already.  So the
console token is printed from the row, after the read, or not at all.

WHY A FAILED WRITE DOES NOT WITHHOLD THE WARP.  [สมมติของสาย GM - รอ COO
ยืนยัน]  `/speed`'s persistence half is DB-FIRST and refuses the frame when
the row cannot be written; this one is not, and the difference is deliberate.
`/speed` was ADDING a capability whose row and screen had to agree from the
first frame.  `/warp <n>` is a capability the tester has today and uses to
reach the scenes M2/M3/M4 are tested in: making a store failure also delete
the warp would take away a working tool to fix a bookkeeping gap, which is
not what `1430` asked for.  Every failure is named in the event trail and in
a console line instead, so an attended round can still tell "warped and
stuck" from "warped and did not stick".  Put to COO in
`20260904_16xx_LANE-GM-ASK-COO-*`; if COO rules the other way it is one
branch in `chat_command_action`, not a rewrite here.
"""
from __future__ import annotations

import sys

from ..model import Position
from ..world_scene_travel import SCENE_SEQUENCE
from .warp_executor import WarpTarget

#: Printed to stderr, once, only after the row has been read back and found
#: to hold the destination scene.  `COO 1452` item 2 named this token.
#:
#: stderr, not stdout, for the reason `runtime.py`'s GM_WARP_POSITION_CONFIRMED
#: block already records: a token on stdout once landed inside the JSON
#: artifact of `tools/pf_runtimeres_death_headless_replay.py --json`.
CONSOLE_TOKEN = "GM_WARP_SCENE_PERSISTED"

# The outcome words.  One per reachable state, never collapsed into a single
# "failed": this module exists BECAUSE "the row did not move" and "the row
# moved to the wrong place" had looked identical to a tester, and a report
# that re-merges them would rebuild the same blindness one layer up.
OUTCOME_PERSISTED = "persisted"
OUTCOME_NOT_A_TARGET = "not_a_target"
OUTCOME_NO_SESSION_DOOR = "no_session_door"
OUTCOME_NO_CHARACTER = "no_character"
OUTCOME_COMPOSE_REFUSED_PREFIX = "compose_refused_"
OUTCOME_WRITE_REFUSED_PREFIX = "write_refused_"
OUTCOME_READBACK_UNAVAILABLE = "readback_unavailable"
OUTCOME_ROW_NOT_TOUCHED = "row_not_touched"

#: Event names, one per outcome, in this module's own namespace so a reader of
#: `session.events` can tell a warp-persist line from `/speed`'s.
EVENT_PREFIX = "gm_warp_scene_persist_"


def warp_destination_position(target: object, current: object) -> Position:
    """The row a live warp to `target` should leave behind.

    Pure, and separated from the write on purpose: it is the half a test can
    pin without a database, and the half whose mistake would be silent
    (a plausible-looking row in the wrong place).

    `current` supplies `heading` ONLY.  A `current` that has no readable
    heading yields 0.0 rather than raising -- the scene is the thing `1430`
    is about, and losing a facing angle must never cost the write.
    """
    if not isinstance(target, WarpTarget):
        raise ValueError("a warp destination row needs a WarpTarget")
    heading = getattr(current, "heading", None)
    if isinstance(heading, bool) or not isinstance(heading, (int, float)):
        heading = 0.0
    return Position(
        target.scene_id,
        SCENE_SEQUENCE,
        float(target.x),
        float(target.y),
        float(target.z),
        float(heading),
    )


def persist_warp_scene(session: object, target: object) -> str:
    """Write `target`'s scene and spawn point to the row now.  One word back.

    Called from the warp branches of `chat_command_action` AFTER the frame
    exists -- never before.  A refused warp leaves no bytes on the wire and
    must leave no row change either, the same rule `_park_warp_target`
    already states for the target record.

    NEVER RAISES.  It runs on the game-listener thread, after a frame has
    already been built and while the connection is waiting for it; a store
    that is missing, locked, or lying must cost this write and its token, not
    the warp and not the thread.
    """
    if not isinstance(target, WarpTarget):
        return OUTCOME_NOT_A_TARGET

    foundation = getattr(session, "foundation", None)
    checkpoint = getattr(foundation, "checkpoint", None)
    if not callable(checkpoint):
        # A session shape with no write door is not an error to raise; it is
        # a replay tool, a test double, or a connection that has not reached
        # the game stage.  Named, and the warp still goes out.
        return OUTCOME_NO_SESSION_DOOR

    selected = getattr(foundation, "selected", None)
    character_id = getattr(selected, "id", None)
    if selected is None or type(character_id) is not int:
        # `checkpoint` itself raises RuntimeError for a None selection; this
        # branch answers the same state with a word instead, and additionally
        # covers the read-back below, which needs an int id it can look up.
        return OUTCOME_NO_CHARACTER

    try:
        position = warp_destination_position(target, getattr(selected, "position", None))
    except Exception as error:  # noqa: BLE001 - see docstring
        # Type name only, never the message: a message can embed the
        # coordinates a GM typed, and console lines are not the place for
        # operator-controlled text (`_one_line`'s reasoning next door).
        return f"{OUTCOME_COMPOSE_REFUSED_PREFIX}{type(error).__name__}"

    try:
        checkpoint(position)
    except Exception as error:  # noqa: BLE001 - a stale/non-owning session
        # raises PermissionError out of `store.save_position`; a store double
        # can raise anything.  Both are this write's cost, not the warp's.
        return f"{OUTCOME_WRITE_REFUSED_PREFIX}{type(error).__name__}"

    stored = _row_scene_id(foundation, character_id)
    if stored is None:
        return OUTCOME_READBACK_UNAVAILABLE
    if stored != position.scene_id:
        # The write door returned cleanly and the row still names another
        # scene.  Today the one reachable cause is the
        # `is_position_persist_allowed` gate inside `lifecycle.checkpoint`,
        # which skips the column write for a pinned-False scene while still
        # proving ownership.  Whatever the cause, the honest report is that
        # the scene did NOT stick -- and no token.
        return OUTCOME_ROW_NOT_TOUCHED

    try:
        print(f"{CONSOLE_TOKEN} scene={position.scene_id}", file=sys.stderr)
    except Exception:  # noqa: BLE001 - a closed or replaced stderr must not
        # undo a durable write that already succeeded.  The row is the
        # deliverable; the line about it is not.
        pass
    return OUTCOME_PERSISTED


def _row_scene_id(foundation: object, character_id: int):
    """The scene id `character_positions` holds for this character, or None.

    Reads through `store.get_character`, an existing door on LANE-DB's own
    repository protocol (`repository.CharacterRepository`), so this lane adds
    no read path of its own and touches no SQL.

    `None` means "could not be read" for every cause -- no store, no such
    method, a raising store, a character row that has gone away -- and the
    caller reports that as its own outcome rather than as a failed write:
    the write may well have landed, and claiming otherwise would be the
    mirror image of the false token this read-back exists to prevent.
    """
    store = getattr(getattr(foundation, "lifecycle", None), "store", None)
    reader = getattr(store, "get_character", None)
    if not callable(reader):
        return None
    try:
        row = reader(character_id)
    except Exception:  # noqa: BLE001 - see docstring
        return None
    scene_id = getattr(getattr(row, "position", None), "scene_id", None)
    return scene_id if type(scene_id) is int else None
