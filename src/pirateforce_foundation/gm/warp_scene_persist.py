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

WHAT IT IS NOT.  It does not send anything and does not decide routing.  It
goes through the DB write door that already exists and that every other
durable position write in this project uses -- `FoundationSession.checkpoint`
-> `lifecycle.checkpoint` -> `store.save_position` -- so the ownership check
and the `is_position_persist_allowed` gate behave here exactly as they do on
a walk frame.  `COO 1452` item 2 requires that door and forbids new SQL.

THE ONE THING IT MUST PUT BACK, AND WHY THE FIRST DRAFT WAS A CRITICAL BUG.
`FoundationSession.checkpoint` ends with `self.selected = replace(
self.selected, position=position)` (`session.py`), i.e. the write door ALSO
rewrites the connection's IN-MEMORY row.  On a walk frame that is right: the
in-memory row is downstream of the client's own report.  Here it would be
upstream of it, and `runtime.py` keys the whole cross-scene machinery on the
in-memory row still naming where the client last WAS:

  * `_gm_warp_resync_selected_scene` returns early when
    `target.scene_id == selected.position.scene_id` -- so a pre-empted
    in-memory row makes a live cross-scene warp look same-scene, and the
    destination scene's census is never composed, `last_target_pos` is never
    cleared, the mob-combat membership never resets, and
    `scene_label_is_server_guess` is never set.  That is KA1A-ROOTCAUSE and
    `GT-172` F-1 reopened at once.
  * `_checkpoint_exact_target` does everything behind
    `elif candidate != selected.position:` -- so the client's arrival report
    matches and `GM_WARP_POSITION_CONFIRMED` (`CORE-REQUEST-GM-030`) is
    suppressed, while the trail asserts `no_durable_position_write` about a
    frame whose warp DID write durably.
  * with `scene_label_is_server_guess` never set, `_note_client_confirmed_
    scene` launders the server's own unconfirmed guess into
    `client_confirmed_scene` -- pf-adversary R328 D3/D4's hole, in full.

`runtime.py`'s own comment already settled the design ("SCENE_ID ONLY,
x/y/z/heading untouched, and this is deliberate, not an oversight").  So this
module RESTORES `foundation.selected` to the object it snapshotted before the
write.  The durable row moves; the in-memory row does not.  That is the whole
answer to "which row is `selected.position` supposed to be": it stays the
last thing the client is known to have reported, and `character_positions`
becomes what the GM commanded.  Measured by pf-adversary on the first draft;
`tests/test_gm_warp_scene_persist.py` pins the restoration in both
directions.

A DESTINATION THE NEXT LOGIN WOULD REFUSE IS NOT PERSISTED.  This write
exists FOR the next login -- that is the entire content of `1430`.  A scene
pinned `login_entry_allowed=False` (scene 126 today) accepts the write
through `is_position_persist_allowed`, which is a different question, and
`world_scene_entry.resolve_entry` then refuses the next login with
`scene_not_allowed_at_login`: the row is written, the character cannot get
back in, and only a login could rewrite the row.  pf-adversary measured that
end to end on the first draft.  Refusing to write is strictly better than
bricking the character, and it costs nothing a tester had yesterday.

THE POSITION IT WRITES IS THE FRAME'S OWN, NOT A SECOND OPINION.  Every
coordinate comes off the `WarpTarget` the composer handed back, which is
already the binary32 value ON THE WIRE (see `warp_executor.WarpTarget`).
`scene_seq` is `world_scene_travel.SCENE_SEQUENCE`, the same constant the
composer put in the frame; `heading` is CARRIED OVER from the row the
connection already has, because a TeleportVital carries no heading and
inventing one would rotate a character nobody asked to rotate.

READ-BACK IS NOT DECORATION (`COO 1452` item 2, "อ่านกลับหลังเขียน"), AND IT
COMPARES THE WHOLE ROW.  `lifecycle.checkpoint` calls
`store.save_position(..., write_position=allowed)` and, for a scene pinned
`persist_position_allowed=False`, that call RETURNS CLEANLY HAVING WRITTEN NO
ROW.  ~~Comparing `scene_id` alone~~ -- STRUCK: pf-adversary measured that a
same-scene warp (the shape `PANYA-DECISION 20260903_1800` ships) already
satisfies a scene-id comparison BEFORE any write, so the token fired over a
row where nothing had moved.  The comparison is the full
`(scene_id, scene_seq, x, y, z)`, and the token is printed from the row that
came back, never from the value that was passed in.
"""
from __future__ import annotations

import sys

from .. import world_scene_travel
from ..model import Position
from ..world_scene_travel import SCENE_SEQUENCE
from .warp_executor import WarpTarget

#: Printed to stderr, once, only after the row has been read back and found to
#: hold the destination.  `COO 1452` item 2 named this token.
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
OUTCOME_LOGIN_WOULD_REFUSE = "login_would_refuse"
OUTCOME_COMPOSE_REFUSED_PREFIX = "compose_refused_"
OUTCOME_WRITE_REFUSED_PREFIX = "write_refused_"
OUTCOME_READBACK_UNAVAILABLE = "readback_unavailable"
OUTCOME_ROW_NOT_TOUCHED = "row_not_touched"
OUTCOME_SELECTED_NOT_RESTORED = "selected_not_restored"

#: Event names, one per outcome, in this module's own namespace so a reader of
#: `session.events` can tell a warp-persist line from `/speed`'s.
EVENT_PREFIX = "gm_warp_scene_persist_"

# The columns the read-back compares.  `heading` is deliberately absent: the
# write carries the row's own heading over unchanged, so it can never be
# evidence that this write landed.
_COMPARED_COLUMNS = ("scene_id", "scene_seq", "x", "y", "z")


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


def login_would_accept(scene_id: object) -> bool:
    """Whether a persisted row in this scene would survive the next login.

    The mirror of `world_scene_entry.resolve_entry`'s own `via_login and not
    target.login_entry_allowed` refusal, asked HERE because this write exists
    for that login and nowhere else.

    FAILS CLOSED for every scene this module cannot answer for -- unknown to
    the registry, unreadable, a raising registry.  `is_position_persist_
    allowed` fails OPEN for an unpinned scene, and that is right for its own
    question (an ordinary walk in a scene nobody pinned must still save); it
    is wrong for this one, because a `/warp` destination is ALWAYS a scene
    `warp_no_coords_live_target` already resolved through this same registry,
    so "not in the registry" here means something is wrong, not something is
    ordinary.
    """
    if isinstance(scene_id, bool) or type(scene_id) is not int:
        return False
    try:
        target = world_scene_travel.destination(scene_id)
    except Exception:  # noqa: BLE001 - KeyError for an unpinned scene,
        # ValueError for one outside the wire range; both fail closed.
        return False
    return getattr(target, "login_entry_allowed", False) is True


def persist_warp_scene(session: object, target: object) -> str:
    """Write `target`'s scene and spawn point to the row now.  One word back.

    Called from the no-coordinate TeleportVital branch of
    `chat_command_action` AFTER the frame exists -- never before.  A refused
    warp leaves no bytes on the wire and must leave no row change either, the
    same rule `_park_warp_target` already states for the target record.

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
    if selected is None or isinstance(character_id, bool) or type(character_id) is not int:
        # `checkpoint` itself raises RuntimeError for a None selection; this
        # branch answers the same state with a word instead, and additionally
        # covers the read-back below, which needs an int id it can look up.
        return OUTCOME_NO_CHARACTER

    if not login_would_accept(target.scene_id):
        # See the module docstring: writing here is what bricks a character.
        return OUTCOME_LOGIN_WOULD_REFUSE

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
        # The restore below still runs: `checkpoint` updates `selected` only
        # after the store call returns, but a partially-applied double could
        # have done either, and putting the snapshot back is correct for both.
        _restore_selected(foundation, selected)
        return f"{OUTCOME_WRITE_REFUSED_PREFIX}{type(error).__name__}"

    if not _restore_selected(foundation, selected):
        # The durable row moved and the in-memory row could not be put back,
        # so `runtime.py`'s cross-scene machinery is now keyed on a row this
        # module changed.  Reported as its own outcome rather than folded
        # into success: the write landed, but not on the terms above.
        return OUTCOME_SELECTED_NOT_RESTORED

    stored = _row_position(foundation, character_id)
    if stored is None:
        return OUTCOME_READBACK_UNAVAILABLE
    for column in _COMPARED_COLUMNS:
        if getattr(stored, column, None) != getattr(position, column):
            # The write door returned cleanly and the row is not the row this
            # call asked for.  Today the one reachable cause is the
            # `is_position_persist_allowed` gate inside `lifecycle.checkpoint`,
            # which skips the column write for a pinned-False scene while
            # still proving ownership.  Whatever the cause: no token.
            return OUTCOME_ROW_NOT_TOUCHED

    try:
        # From the ROW that came back, not from the value passed in.
        print(f"{CONSOLE_TOKEN} scene={stored.scene_id}", file=sys.stderr)
    except Exception:  # noqa: BLE001 - a closed or replaced stderr must not
        # undo a durable write that already succeeded.  The row is the
        # deliverable; the line about it is not.
        pass
    return OUTCOME_PERSISTED


def _restore_selected(foundation: object, snapshot: object) -> bool:
    """Put the in-memory character back the way the write door found it.

    See the module docstring for why this is load-bearing rather than tidy.
    Returns whether the restore is verifiable -- read back for the reason
    `warp_target_record.record_warp_target` reads its own write back: a
    `__setattr__` that swallows the assignment raises nothing, and reporting
    a restore that did not happen is the same class of false report this
    module's read-back exists to stop.
    """
    try:
        foundation.selected = snapshot  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - never costs the listener thread
        return False
    try:
        return getattr(foundation, "selected", None) is snapshot
    except Exception:  # noqa: BLE001
        return False


def _row_position(foundation: object, character_id: int):
    """The `character_positions` row for this character, or None.

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
    return getattr(row, "position", None)
