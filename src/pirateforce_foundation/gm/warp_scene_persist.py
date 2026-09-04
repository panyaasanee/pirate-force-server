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
pinned `login_entry_allowed=False` (~~scene 126 today~~ -- STRUCK, and the
number was already wrong when it was written: re-derived from
`scenarios/world_scene_registry_001.json` at HEAD the set is **17 and 126**,
pf-adversary round `741zlx` finding 9; `world_scene_entry.py` carries the
mirror-image half-truth "today: scene 17 only", which is chief's zone and is
named in this round's letter rather than edited here) accepts the write
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
import threading
from collections import abc

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

#: `COO-DECISION 20260904_1646` item 2, answering `20260904_1620`: a tester
#: reads the CONSOLE, not `session.events` -- an event trail already named
#: every one of these outcomes, and GT-172 F-3 stayed unmeasurable from the
#: screen because "wrote" and "wrote-failed-silently" looked identical there.
#: Printed once for every reachable outcome below OTHER than
#: `OUTCOME_PERSISTED` and `OUTCOME_NOT_A_TARGET` -- the latter is not a
#: failed warp, it is this function called with something that was never a
#: warp target at all, and there is no scene id to name.
FAIL_CONSOLE_TOKEN = "GM_WARP_SCENE_PERSIST_FAILED"

#: The two lines the UNDO prints.  `pf-adversary` round `741zlx`, finding 1
#: (CRITICAL, MEASURED): `_make_action` can withhold a composed `/warp <n>`
#: AFTER this module has already moved the row -- an `outcome` row that cannot
#: be appended withholds the action, and until this round nothing put the row
#: back, because `_warp_teleport_action_no_coords` returned a `_Verdict` with
#: `undo=None` while `_Verdict`'s own docstring reserves that for a handler
#: that changed no durable state.  Measured end to end: zero bytes on the
#: wire, `character_positions` reading the destination, the in-memory row
#: still in the departure scene, and the next login landing in a scene the
#: client was never sent to -- the character-bricking shape `CHARTER-02` rule
#: 2 forbids, arriving through a door `COO 1452`'s ruling never opened.
ROLLBACK_CONSOLE_TOKEN = "GM_WARP_SCENE_ROLLED_BACK"
ROLLBACK_FAIL_CONSOLE_TOKEN = "GM_WARP_SCENE_ROLLBACK_FAILED"

#: The two lines the BOOT REGISTRY DOOR prints -- `CORE-REQUEST-GM-056`,
#: accepted by chief in `notes_to_chief/20260905_0045_CHIEF-TO-LANE-GM-core-
#: request-gm-056-accepted.md`.  An operator has to be able to read off the
#: console which of the two registries this process is answering warps from,
#: because the whole point of the door is that the two can disagree.
BOOT_REGISTRY_CONSOLE_TOKEN = "GM_WARP_BOOT_REGISTRY_INSTALLED"
BOOT_REGISTRY_REFUSED_CONSOLE_TOKEN = "GM_WARP_BOOT_REGISTRY_REFUSED"

# The outcome words.  One per reachable state, never collapsed into a single
# "failed": this module exists BECAUSE "the row did not move" and "the row
# moved to the wrong place" had looked identical to a tester, and a report
# that re-merges them would rebuild the same blindness one layer up.
OUTCOME_PERSISTED = "persisted"
OUTCOME_NOT_A_TARGET = "not_a_target"
OUTCOME_NO_SESSION_DOOR = "no_session_door"
OUTCOME_NO_CHARACTER = "no_character"
OUTCOME_LOGIN_WOULD_REFUSE = "login_would_refuse"
# NOT a policy word, and deliberately not folded into the one above it
# (pf-adversary, round `vlk8rq`, finding 5).  "the registry says this scene
# refuses logins" and "this process could not read the registry at all" are
# two different facts, and last round's finding 2 in this same module was
# exactly one word answering two questions.  An operator reading
# `login_would_refuse` goes to look at scene policy; this one sends them to
# the file.
OUTCOME_LOGIN_REGISTRY_UNREADABLE = "login_registry_unreadable"
OUTCOME_COMPOSE_REFUSED_PREFIX = "compose_refused_"
OUTCOME_WRITE_REFUSED_PREFIX = "write_refused_"
OUTCOME_READBACK_UNAVAILABLE = "readback_unavailable"
OUTCOME_ROW_NOT_TOUCHED = "row_not_touched"
# `pf-adversary` round `741zlx`, finding 2 (MAJOR, MEASURED).  `row_not_touched`
# was answering two questions with one word, which is the exact merge the block
# above forbids for itself.  Scene 14 is marker-backed and
# `login_entry_allowed=True`, so it IS a live `/warp` destination -- but it is
# pinned `persist_position_allowed=False`, so `lifecycle.checkpoint` calls
# `save_position(write_position=False)` and RETURNS CLEANLY HAVING WRITTEN
# NOTHING.  Measured: `/warp 14` sends the frame, the row stays in the
# departure scene, the next login comes back to it -- R309's own symptom,
# unclosed, for that scene.  A tester reading `row_not_touched` cannot tell
# "the registry deliberately forbids writing here" from "the store silently
# lied about a write it accepted", and only the second is a defect.  The
# registry answer gets its own word; nothing else changes, and in particular
# this lane does NOT decide whether scene 14 should become persistable -- that
# is a registry question, raised with COO in this round's letter.
OUTCOME_PERSIST_FORBIDDEN_BY_REGISTRY = "persist_forbidden_by_registry"
OUTCOME_SELECTED_NOT_RESTORED = "selected_not_restored"

# The undo's own words.  Same rule as above: "there was nothing to put back"
# and "putting it back failed" are different answers and never share a word.
OUTCOME_ROLLED_BACK = "rolled_back"
OUTCOME_NOTHING_TO_ROLL_BACK = "nothing_to_roll_back"
OUTCOME_ROLLBACK_REFUSED_PREFIX = "rollback_refused_"
OUTCOME_ROLLBACK_NOT_CONFIRMED = "rollback_not_confirmed"

# `rollback_warp_scene_on_send_failure`'s own word for "this call was not
# about a warp at all" -- the v141 send loop calls it after EVERY queued
# action, not only a warp, so most calls must be free.  Named separately
# from `OUTCOME_NOT_A_TARGET` above (that one guards a WarpTarget shape;
# this one guards an action LABEL) so a reader of either return value can
# tell which guard actually fired without reading the caller.
OUTCOME_NOT_A_WARP = "not_a_warp"

# The words `use_boot_scene_registry` answers with.  It is called from the
# BOOT of a server, so it never raises and it never returns a bare bool: a
# refusal has to say WHICH refusal, or an operator staring at a boot log
# cannot tell "chief passed the wrong object" from "the object is right and
# its contents are broken".
OUTCOME_BOOT_REGISTRY_INSTALLED = "boot_registry_installed"
OUTCOME_BOOT_REGISTRY_REFUSED_NOT_A_REGISTRY = (
    "boot_registry_refused_not_a_registry"
)
OUTCOME_BOOT_REGISTRY_REFUSED_UNUSABLE_PREFIX = "boot_registry_refused_unusable_"
#: The one unusable reason that is not an exception type name: rows that
#: cannot be counted without being consumed (pf-adversary, this round, D4).
OUTCOME_BOOT_REGISTRY_UNSIZED_ROWS = "unsized_rows"

#: Which of the two registries this process is answering from.  Read by tests
#: and by `login_registry_source()`; never by a decision in this module -- the
#: answer must not change shape depending on where the registry came from.
REGISTRY_SOURCE_BOOT = "boot"
REGISTRY_SOURCE_SELF_READ = "self_read"

#: The ONLY action label `rollback_warp_scene_on_send_failure` acts on.  A
#: LITERAL COPY of
#: `chat_command_action.WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL`,
#: not an import of it: `chat_command_action` already imports THIS module
#: (`rollback_warp_scene`, `row_before_warp`), so importing the label back
#: would be circular.  `tests/test_gm_warp_scene_rollback.py` pins the two
#: strings equal, so a rename of one without the other fails a test instead
#: of quietly making this function a permanent no-op.
SEND_FAILURE_WARP_ACTION_LABEL = (
    "LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_TELEPORT_VITAL"
)

#: Event names, one per outcome, in this module's own namespace so a reader of
#: `session.events` can tell a warp-persist line from `/speed`'s.
EVENT_PREFIX = "gm_warp_scene_persist_"

#: `pf-adversary` round `741zlx`, finding 4 (MAJOR, MEASURED): a stderr whose
#: `write()` raises used to cost the token SILENTLY -- `persist_warp_scene`
#: returned `persisted` and printed nothing at all, so the one blindness
#: `COO-DECISION 20260904_1646` item 2 exists to abolish ("wrote" and
#: "wrote-failed-silently" identical on the screen a tester reads) was
#: reachable through the console itself.  The sibling call site next door
#: already names its own version of this (`EVENT_CONSOLE_WRITE_FAILED_PREFIX`
#: in `chat_command_action.py`); this module had no such event.  Now every
#: skipped line leaves a named event carrying the reason word whose line was
#: lost, so a skip is counted even when it cannot be seen.
EVENT_CONSOLE_WRITE_FAILED_PREFIX = EVENT_PREFIX + "console_write_failed_"

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


_LOGIN_REGISTRY_SNAPSHOT: object | None = None
_LOGIN_REGISTRY_SNAPSHOT_TAKEN = False
# The read below happens on a game-listener thread, one per connection, and
# two connections can warp at the same moment.  The first draft set the
# "taken" flag BEFORE the load and held no lock, so a second connection
# arriving mid-read saw `TAKEN=True, SNAPSHOT=None`, was told
# `login_would_refuse`, and LOST ITS DURABLE ROW -- reproduced with a slow
# loader (pf-adversary, round `vlk8rq`, finding 4, MEASURED).  The per-call
# read this replaced could not do that.
_LOGIN_REGISTRY_SNAPSHOT_LOCK = threading.Lock()

#: `REGISTRY_SOURCE_BOOT`, `REGISTRY_SOURCE_SELF_READ`, or None when nothing
#: has been taken yet.  Bookkeeping only -- see `login_registry_source`.
_LOGIN_REGISTRY_SOURCE: str | None = None


def reset_login_registry_snapshot_for_tests() -> None:
    """Drop the snapshot below, so the next call re-reads the registry.

    For tests only, and named so it says that.  Same shape and same reason as
    `gm/dispatch.reset_rate_limit_state_for_tests`: process-global state that
    is correct for a server and wrong for a suite where one case writes a
    throwaway registry and the next expects the shipped one.
    """
    global _LOGIN_REGISTRY_SNAPSHOT, _LOGIN_REGISTRY_SNAPSHOT_TAKEN
    global _LOGIN_REGISTRY_SOURCE
    with _LOGIN_REGISTRY_SNAPSHOT_LOCK:
        _LOGIN_REGISTRY_SNAPSHOT = None
        _LOGIN_REGISTRY_SNAPSHOT_TAKEN = False
        # Cleared with the snapshot, not separately: a suite that reset the
        # snapshot and kept the word would report `boot` for an answer that
        # came off the disk on the next call.
        _LOGIN_REGISTRY_SOURCE = None


def _login_registry_snapshot():
    """The scene registry this process will answer from, read ONCE.

    `ADVERSARY_PENDING #745-R2` item 5, ordered fixed by `COO-DECISION
    20260904_2045` item 4: `login_would_accept` asked
    `world_scene_travel.destination` with no registry argument, and that
    helper re-reads `scenarios/world_scene_registry_001.json` FROM DISK on
    every call with no cache.  Two things follow from that, and the second is
    why COO called it fail-open:

      * the answer this module gives can DISAGREE with the answer the login
        path gave, whenever the file changes mid-run -- and this module
        exists precisely to predict that login;
      * the disagreement runs both ways.  A scene edited to
        `login_entry_allowed` after boot would let this module write a row
        the running login path still refuses, which is the exact state the
        module docstring calls bricking a character.

    Read once and held, so this module answers every warp of a process from
    ONE read instead of one per warp.

    !! ~~so the prediction is made against the same registry the server booted
    with ... the difference is one warp early in a process's life, not a disk
    edit.~~ BOTH CLAUSES ARE FALSE AND ARE STRUCK IN THE ROUND THAT WROTE
    THEM (pf-adversary, round `vlk8rq`, finding 3, MEASURED).  The login path
    this module predicts does NOT read this file when it runs: it uses the
    `scene_entry_registry` object `runtime.py` loads once at factory
    construction and threads into `world_scene_entry.resolve_entry`.  This is
    a SECOND, LATER, INDEPENDENT read of the same file -- so it agrees with
    the login path exactly when the file has not changed, and differs from it
    precisely when it has, which is the one case the struck sentence claimed
    was excluded.  Measured: boot with scene N allowed, edit the file to shut
    it, and this snapshot says False while the running login still says True
    (and the harmful direction is the same sentence reversed).

    WHAT ACTUALLY CLOSES IT is being handed the runtime's own registry object
    rather than taking a read of our own -- `runtime.py` is chief's zone, so
    that is `CORE-REQUEST-GM-056`, and until it lands this function is the
    narrower of two wrong answers, not a right one.  What this version does
    buy over the per-call read it replaced: one answer per process instead of
    one per warp, so a warp cannot disagree with the warp before it.

    FAILS CLOSED, and remembers that it failed: an unreadable registry
    leaves the snapshot `None`, `login_would_accept` returns False for every
    scene, and no row is written on a guess.  It does NOT retry on the next
    warp -- a retry would put the disk read back on the hot path this exists
    to take it off.
    """
    global _LOGIN_REGISTRY_SNAPSHOT, _LOGIN_REGISTRY_SNAPSHOT_TAKEN
    global _LOGIN_REGISTRY_SOURCE
    with _LOGIN_REGISTRY_SNAPSHOT_LOCK:
        if not _LOGIN_REGISTRY_SNAPSHOT_TAKEN:
            try:
                _LOGIN_REGISTRY_SNAPSHOT = (
                    world_scene_travel.load_scene_registry()
                )
            except Exception:  # noqa: BLE001 - unreadable registry fails closed
                _LOGIN_REGISTRY_SNAPSHOT = None
            _LOGIN_REGISTRY_SOURCE = REGISTRY_SOURCE_SELF_READ
            # SET LAST, INSIDE THE LOCK.  A second thread that arrives while
            # the read is in flight waits for the answer instead of being
            # handed `None` and told the scene refuses logins.
            _LOGIN_REGISTRY_SNAPSHOT_TAKEN = True
        return _LOGIN_REGISTRY_SNAPSHOT


def login_registry_source() -> str | None:
    """Where this process's registry answers come from, or None if untouched.

    `REGISTRY_SOURCE_BOOT` once `use_boot_scene_registry` has installed the
    runtime's own object; `REGISTRY_SOURCE_SELF_READ` once this module has
    fallen back to its own disk read.  Diagnostic and test vocabulary only:
    nothing in this module branches on it, because the prediction
    `login_would_accept` makes must not change SHAPE with where the registry
    came from -- only WHICH registry it is asking.
    """
    with _LOGIN_REGISTRY_SNAPSHOT_LOCK:
        return _LOGIN_REGISTRY_SOURCE


def login_registry_is(candidate: object) -> bool:
    """Whether the registry this module answers from IS `candidate`.

    IDENTITY, not equality, and that is the entire point (pf-adversary, this
    round, D1, MEASURED).  `use_boot_scene_registry` prints the same line --
    `GM_WARP_BOOT_REGISTRY_INSTALLED scenes=17 replaced=none` -- for the
    correct wiring and for `use_boot_scene_registry(load_scene_registry())`,
    which is a THIRD independent disk read and leaves `vlk8rq` finding 3
    completely open.  Every other signal this module ships (the token, the
    source word, the scene count, `replaced=`) is a function of state, so
    none of them can tell the fix from the non-fix.  This one is a function
    of identity, so it can.

    It exists for the `runtime.py` wiring test that lands with chief's call
    site: `login_registry_is(scene_entry_registry)` is the assertion that
    grades the wire, and nothing weaker does.

    FALSE WHEN NOTHING IS HELD, for either argument.  A bare
    `_LOGIN_REGISTRY_SNAPSHOT is candidate` answers TRUE for
    `login_registry_is(None)` on an untouched module -- "no registry" and
    "the registry you asked about" are not the same fact, and a grading
    helper that conflates them would pass a wire that was never made.
    """
    with _LOGIN_REGISTRY_SNAPSHOT_LOCK:
        if _LOGIN_REGISTRY_SNAPSHOT is None:
            return False
        return _LOGIN_REGISTRY_SNAPSHOT is candidate


def use_boot_scene_registry(registry: object) -> str:
    """Answer every later warp from the registry the RUNTIME booted with.

    `CORE-REQUEST-GM-056`, accepted by chief on 2026-09-05T00:45+07:00.  The
    call site is in `runtime.py` immediately after
    `scene_entry_registry = world_scene_travel.load_scene_registry()` at
    `runtime.py:706` -- not dispatch, not login, and nothing on a hot path.

    IT IS TWO LINES, NOT ONE, and the acceptance letter's "one line" was
    wrong (pf-adversary, this round, D2, MEASURED).  `runtime.py` imports
    five modules from `.gm` and `warp_scene_persist` is not among them, so
    the call alone raises `NameError` on the first `make_state_class` -- at
    `app.py:834`, i.e. the server does not boot at all, in the module whose
    stated reason for NEVER RAISES is that a failure here costs the server.
    Chief needs `from .gm import warp_scene_persist` alongside the existing
    `.gm` imports as well as the call.

    AND THE ARGUMENT MUST BE `scene_entry_registry` ITSELF, never a fresh
    `world_scene_travel.load_scene_registry()`.  A fresh read installs
    cleanly, prints the identical console line, and leaves the defect fully
    open -- see `login_registry_is`, which is the only signal that can tell
    the two apart.

    WHAT THIS CLOSES.  `_login_registry_snapshot` above takes a SECOND, LATER,
    INDEPENDENT read of `scenarios/world_scene_registry_001.json`, while the
    login path this module exists to PREDICT is threaded the runtime's own
    `scene_entry_registry` object.  Two reads of one file agree exactly when
    the file has not changed between them and differ precisely when it has --
    which is the one case that matters, and the harmful direction writes a
    durable row into a scene the running login still refuses (the module
    docstring's "bricks a character").  MEASURED in round `vlk8rq`, finding
    3, and struck in `_login_registry_snapshot`'s own docstring, which names
    this function as the thing that actually closes it.  Once installed, the
    LOGIN PREDICTION in this module and the login path itself read one and
    the same object, and that disagreement has nowhere left to live.

    SCOPED DELIBERATELY, and the wider sentence that stood here is struck
    (pf-adversary, this round, D5): ~~once installed there is ONE registry
    object in the process~~ is FALSE.  `lifecycle.py:121` takes a third,
    independent read at `CharacterLifecycle` construction, and that is the
    one gating the actual durable write (`lifecycle.py:201`/`:252`, through
    `is_position_persist_allowed(..., self._scene_registry)`).  This door
    unifies this module with the runtime's `scene_entry_registry`; it does
    NOT unify `lifecycle`.  The bricking direction is a `login_entry_allowed`
    question and this does close that -- but nobody should read the closing
    sentence of this ticket as more than it is.

    NEVER RAISES, and never for a smaller reason than the others in this file:
    this runs inside chief's boot factory, so an exception here does not cost
    a warp, it costs the SERVER.  A refusal leaves the module exactly as it
    was -- the narrower-but-shipped self-read behaviour, already covered by
    `TheRegistryIsReadOnceTests` -- so a bad argument degrades to today rather
    than to a server that will not boot or one that refuses every warp.

    WHY `isinstance`, WHICH THIS FILE OTHERWISE AVOIDS.  The registry is not
    consumed here; it is handed to `world_scene_travel.destination(scene_id,
    registry)`, whose first line is `(registry or load_scene_registry())`.
    A duck-typed stand-in that happens to be FALSY -- `{}`, `[]`, `0`, an
    empty container double -- would therefore install "successfully" and then
    be silently discarded on every single call, putting back the exact
    per-call disk read this door exists to remove, with a console line saying
    it had been removed.  `SceneRegistry` is a frozen dataclass and is always
    truthy, so requiring the type makes that shape unreachable instead of
    merely unlikely.

    AND THEN IT PROBES.  The right type carrying broken contents is the other
    way to lose every warp quietly: a `SceneRegistry` whose `destinations` do
    not include home makes `destination` raise for that scene, and
    `login_would_accept` fails closed for EVERYTHING with no line anyone
    reads.  Resolving home through the candidate before installing it turns
    that into one loud boot-time refusal.  Home is the probe because a
    registry a server can boot on always pins it -- `destination`'s own
    default argument is `HOME_SCENE_ID`.

    Returns one of `OUTCOME_BOOT_REGISTRY_INSTALLED`,
    `OUTCOME_BOOT_REGISTRY_REFUSED_NOT_A_REGISTRY`, or
    `OUTCOME_BOOT_REGISTRY_REFUSED_UNUSABLE_PREFIX` + the probe's exception
    type name.  The TYPE NAME ONLY, never the message, for the reason
    `persist_warp_scene`'s compose guard gives next door.
    """
    global _LOGIN_REGISTRY_SNAPSHOT, _LOGIN_REGISTRY_SNAPSHOT_TAKEN
    global _LOGIN_REGISTRY_SOURCE

    if not isinstance(registry, world_scene_travel.SceneRegistry):
        return _boot_registry_refused(
            OUTCOME_BOOT_REGISTRY_REFUSED_NOT_A_REGISTRY
        )

    # SIZED BEFORE PROBED, and the order is the whole point (pf-adversary,
    # this round, D4, MEASURED).  `SceneRegistry` is a bare dataclass, so
    # `destinations` can be a GENERATOR -- and the home probe below CONSUMES
    # it.  A generator therefore passed the probe, installed, and then made
    # `destination` re-iterate an exhausted iterator, so `login_would_accept`
    # answered False for EVERY scene for the life of the process: verbatim
    # the outage the probe's own paragraph claims to close, reported as a
    # successful install.  Refusing anything that cannot be measured without
    # being consumed closes it BEFORE the probe can spend it.  Every shape a
    # real registry uses -- tuple, list, set, frozenset -- is `Sized`.
    if not isinstance(getattr(registry, "destinations", None), abc.Sized):
        return _boot_registry_refused(
            f"{OUTCOME_BOOT_REGISTRY_REFUSED_UNUSABLE_PREFIX}"
            f"{OUTCOME_BOOT_REGISTRY_UNSIZED_ROWS}"
        )

    try:
        world_scene_travel.destination(
            world_scene_travel.HOME_SCENE_ID, registry,
        )
    except Exception as error:  # noqa: BLE001 - KeyError for a registry with
        # no home row, ValueError for a bent id; both refuse and keep today's
        # behaviour rather than installing an object nothing can be read from.
        return _boot_registry_refused(
            f"{OUTCOME_BOOT_REGISTRY_REFUSED_UNUSABLE_PREFIX}"
            f"{type(error).__name__}"
        )

    with _LOGIN_REGISTRY_SNAPSHOT_LOCK:
        # `replaced=` is not decoration.  Chief's call site runs at factory
        # construction, before any connection exists, so the honest expected
        # value is `none` -- and a boot log that says `self_read` means this
        # process answered at least one warp from a registry it read itself
        # before the runtime handed over its own, which is a wiring order
        # defect a tester can see instead of one nobody can.
        replaced = _LOGIN_REGISTRY_SOURCE or "none"
        _LOGIN_REGISTRY_SNAPSHOT = registry
        _LOGIN_REGISTRY_SOURCE = REGISTRY_SOURCE_BOOT
        _LOGIN_REGISTRY_SNAPSHOT_TAKEN = True

    # COUNTED OUTSIDE THE LOCK.  `len()` runs `__len__`, which is arbitrary
    # caller code, and this lock is contended by every warp on every
    # connection -- nothing that can block or re-enter this module belongs
    # inside it.  Still guarded, but no longer as the place a non-`Sized`
    # `destinations` is handled: that is refused above, before the probe, so
    # this cannot be reached by the generator shape D4 measured.
    try:
        scenes = len(registry.destinations)
    except Exception:  # noqa: BLE001 - a raising `__len__` on an object that
        # answered `isinstance(..., Sized)`; the count is console decoration
        # and must never cost an install that is otherwise correct.
        scenes = "unknown"

    if not _console(
        f"{BOOT_REGISTRY_CONSOLE_TOKEN} scenes={scenes} replaced={replaced}"
    ):
        # No session exists at boot to hang a lost-line note on, and the
        # install itself has already happened and is correct.  Swallowing the
        # loss is the only option here; it is named so that is a decision and
        # not an oversight.
        pass
    return OUTCOME_BOOT_REGISTRY_INSTALLED


def _boot_registry_refused(reason: str) -> str:
    """Print the refusal, change NOTHING, hand the word back."""
    _console(f"{BOOT_REGISTRY_REFUSED_CONSOLE_TOKEN} reason={reason}")
    return reason


def login_would_accept(scene_id: object) -> bool:
    """Whether a persisted row in this scene would survive the next login.

    The mirror of `world_scene_entry.resolve_entry`'s TWO refusals, asked
    HERE because this write exists for that login and nowhere else:
    `via_login and not target.login_entry_allowed`
    (`REFUSED_NOT_ALLOWED_AT_LOGIN`), and -- `ADVERSARY_PENDING #745-R2` item
    6, MEASURED missing in the round that shipped this function --
    `target.n_id != HOME_SCENE_ID and target.spawn is None`
    (`REFUSED_NO_PINNED_SPAWN`).  `resolve_entry` raises the second one for a
    pinned, login-allowed scene with no spawn just as loudly as the first;
    answering only the first half admitted exactly the silent-lockout shape
    `gm/login_scene_admission.py`'s own `_target_is_admissible` already
    closed on the staging side (see that module's `TWO REGISTRY CONDITIONS,
    not one` docstring) -- this module re-opened it because it was written
    against `login_entry_allowed` alone and never re-read that sibling.  No
    scene in the shipped registry is spawnless today (same as admission's
    guard), so this is a fence against lane A pinning one tomorrow, not a fix
    for data that exists -- `tests/test_gm_warp_scene_persist.py`'s
    `LoginWouldAcceptSpawnConditionTests` bends the registry to prove the
    fence is live, the same way admission's `TheSpawnConditionTests` does.

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
    registry = _login_registry_snapshot()
    if registry is None:
        # The snapshot could not be read at all; see its docstring.
        return False
    try:
        target = world_scene_travel.destination(scene_id, registry)
    except Exception:  # noqa: BLE001 - KeyError for an unpinned scene,
        # ValueError for one outside the wire range; both fail closed.
        return False
    if getattr(target, "login_entry_allowed", False) is not True:
        return False
    if scene_id == world_scene_travel.HOME_SCENE_ID:
        # Home never reads its spawn -- a character arriving home keeps its
        # own persisted position -- so refusing it for a missing spawn would
        # break the one destination that never touches `target.spawn` at all.
        return True
    return getattr(target, "spawn", None) is not None


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
        return _fail(target, OUTCOME_NO_SESSION_DOOR, session)

    selected = getattr(foundation, "selected", None)
    character_id = getattr(selected, "id", None)
    if selected is None or isinstance(character_id, bool) or type(character_id) is not int:
        # `checkpoint` itself raises RuntimeError for a None selection; this
        # branch answers the same state with a word instead, and additionally
        # covers the read-back below, which needs an int id it can look up.
        return _fail(target, OUTCOME_NO_CHARACTER, session)

    if _login_registry_snapshot() is None:
        # THE REGISTRY, NOT THE SCENE (pf-adversary, round `vlk8rq`, finding
        # 5).  `login_would_accept` returns False for both, and this module
        # spent last round learning what one word answering two questions
        # costs: an operator reading `login_would_refuse` goes and looks at
        # scene policy, when what happened is that this process could not read
        # `scenarios/world_scene_registry_001.json` at all -- and, because the
        # snapshot deliberately does not retry, will not for the rest of its
        # life.  Still fail-closed, still no row written; only the word and
        # the console line change.
        return _fail(target, OUTCOME_LOGIN_REGISTRY_UNREADABLE, session)

    if not login_would_accept(target.scene_id):
        # See the module docstring: writing here is what bricks a character.
        return _fail(target, OUTCOME_LOGIN_WOULD_REFUSE, session)

    try:
        position = warp_destination_position(target, getattr(selected, "position", None))
    except Exception as error:  # noqa: BLE001 - see docstring
        # `ADVERSARY_PENDING #745-R2` item 7, MEASURED: neither composer this
        # lane ships can make `warp_destination_position` raise here -- both
        # hand back a `WarpTarget` whose x/y/z are already IEEE binary32
        # floats (see that class's docstring), and `isinstance` is checked
        # above.  This branch is still not dead vocabulary: `persist_warp_
        # scene`'s own contract is NEVER RAISES for ANY `WarpTarget`, not
        # only the two this file happens to build today, and a `WarpTarget`
        # built directly (a replay tool, a future third composer) is not
        # bound to have numeric fields.  `tests/test_gm_warp_scene_persist.py`
        # `TheComposeRefusalGuardTests` constructs one with a non-numeric
        # field and drives it through this call, so the word is pinned as
        # reachable rather than left as a claim nothing exercises.
        #
        # Type name only, never the message: a message can embed the
        # coordinates a GM typed, and console lines are not the place for
        # operator-controlled text (`_one_line`'s reasoning next door).
        return _fail(
            target, f"{OUTCOME_COMPOSE_REFUSED_PREFIX}{type(error).__name__}", session,
        )

    try:
        checkpoint(position)
    except Exception as error:  # noqa: BLE001 - a stale/non-owning session
        # raises PermissionError out of `store.save_position`; a store double
        # can raise anything.  Both are this write's cost, not the warp's.
        # The restore below still runs: `checkpoint` updates `selected` only
        # after the store call returns, but a partially-applied double could
        # have done either, and putting the snapshot back is correct for both.
        _restore_selected(foundation, selected)
        return _fail(
            target, f"{OUTCOME_WRITE_REFUSED_PREFIX}{type(error).__name__}", session,
        )

    if not _restore_selected(foundation, selected):
        # The durable row moved and the in-memory row could not be put back,
        # so `runtime.py`'s cross-scene machinery is now keyed on a row this
        # module changed.  Reported as its own outcome rather than folded
        # into success: the write landed, but not on the terms above.
        return _fail(target, OUTCOME_SELECTED_NOT_RESTORED, session)

    stored = _row_position(foundation, character_id)
    if stored is None:
        return _fail(target, OUTCOME_READBACK_UNAVAILABLE, session)
    for column in _COMPARED_COLUMNS:
        if getattr(stored, column, None) != getattr(position, column):
            # The write door returned cleanly and the row is not the row this
            # call asked for.  ~~Today the one reachable cause is the
            # `is_position_persist_allowed` gate inside `lifecycle.checkpoint`,
            # which skips the column write for a pinned-False scene while
            # still proving ownership.  Whatever the cause: no PERSISTED token
            # -- but the tester watching the console still gets the FAILED
            # one.~~ -- STRUCK, not deleted (finding 2): the cause was named
            # correctly and then reported under a word that hides it.  When
            # the registry is the reason, SAY the registry is the reason; the
            # word is different, the console line is still printed, and the
            # `row_not_touched` word keeps its honest meaning -- "the store
            # accepted a write and the row did not move", which IS a defect.
            if not _registry_forbids_persist(target.scene_id):
                return _fail(target, OUTCOME_ROW_NOT_TOUCHED, session)
            return _fail(target, OUTCOME_PERSIST_FORBIDDEN_BY_REGISTRY, session)

    # From the ROW that came back, not from the value passed in.
    if not _console(f"{CONSOLE_TOKEN} scene={stored.scene_id}"):
        # A closed, detached or raising stderr must not undo a durable write
        # that already succeeded -- but it must not make the write INVISIBLE
        # either (finding 4).  The row is the deliverable; the line about it
        # is not; the record that the line was lost is.
        _note_console_loss(session, OUTCOME_PERSISTED)
    return OUTCOME_PERSISTED


def row_before_warp(session: object):
    """The durable row as it stands RIGHT NOW, or None if it cannot be read.

    Called by `chat_command_action._persist_warp_scene` immediately BEFORE
    `persist_warp_scene`, so that the caller holds the only thing an undo can
    be built from.  Reads through the same `store.get_character` door the
    read-back uses, adds no SQL, and never raises.

    `None` means "no undo is possible", and the caller must offer none rather
    than offer one that cannot put anything back -- reporting a revert that
    did not happen is the false report this module exists to refuse.
    """
    foundation = getattr(session, "foundation", None)
    character_id = getattr(getattr(foundation, "selected", None), "id", None)
    if isinstance(character_id, bool) or type(character_id) is not int:
        return None
    return _row_position(foundation, character_id)


def rollback_warp_scene(session: object, previous: object) -> str:
    """Put the pre-warp row back.  One word back.  NEVER raises.

    THE UNDO `_Verdict` ALREADY EXPECTED AND THIS HANDLER NEVER SUPPLIED.
    `pf-adversary` round `741zlx`, finding 1, MEASURED through the real
    router and the real store: inject one fault the production code already
    handles (`log_gm_command_outcome` raising `OSError` -- a full disk, a
    read-only capture directory) and `_make_action` withholds the composed
    `/warp <n>` action AFTER this module has moved the row.  It reverts the
    staged config, it clears the parked warp target, it sets `action = None`
    -- and the row stayed in the destination scene with ZERO bytes on the
    wire.  The GM's screen never changed; the next login landed in a scene
    the client was never sent to, and only another login could rewrite it.
    That is the bricking shape `CHARTER-02` rule 2 forbids and the exact rule
    `persist_warp_scene`'s own docstring states ("A refused warp leaves no
    bytes on the wire and must leave no row change either").

    THIS IS NOT THE `v141` SEND WINDOW.  `CORE-REQUEST-GM-055` (this round)
    asks chief for the OTHER one: the row is written at compose time and the
    socket write happens ~2,200 lines later, in chief's zone, where this lane
    may not put a call.  The audit-withheld window is entirely inside this
    lane's own files, which is why it is closed here and now instead of being
    added to that letter.

    Goes through the SAME write door, for the same reason the forward write
    does: `FoundationSession.checkpoint` -> `lifecycle.checkpoint` ->
    `store.save_position`, so the ownership check and the persist-allowed
    gate behave exactly as they did on the way out.  Restores
    `foundation.selected` afterwards on the same grounds as the forward
    write, and READS THE ROW BACK: an undo that reports success it cannot
    demonstrate is the failure this module refuses everywhere else.
    """
    if not isinstance(previous, Position):
        # Nothing was captured, so there is nothing to claim.  Named rather
        # than silently "successful": the caller reports it as its own event.
        return OUTCOME_NOTHING_TO_ROLL_BACK

    foundation = getattr(session, "foundation", None)
    checkpoint = getattr(foundation, "checkpoint", None)
    selected = getattr(foundation, "selected", None)
    character_id = getattr(selected, "id", None)
    if (
        not callable(checkpoint)
        or selected is None
        or isinstance(character_id, bool)
        or type(character_id) is not int
    ):
        return _rollback_failed(previous, OUTCOME_NO_SESSION_DOOR, session)

    try:
        checkpoint(previous)
    except Exception as error:  # noqa: BLE001 - see the forward write's own
        # reasoning: a stale or non-owning session raises PermissionError out
        # of `store.save_position`, and a store double can raise anything.
        _restore_selected(foundation, selected)
        return _rollback_failed(
            previous,
            f"{OUTCOME_ROLLBACK_REFUSED_PREFIX}{type(error).__name__}",
            session,
        )

    _restore_selected(foundation, selected)

    stored = _row_position(foundation, character_id)
    if stored is None:
        return _rollback_failed(
            previous, OUTCOME_READBACK_UNAVAILABLE, session,
        )
    for column in _COMPARED_COLUMNS:
        if getattr(stored, column, None) != getattr(previous, column):
            return _rollback_failed(
                previous, OUTCOME_ROLLBACK_NOT_CONFIRMED, session,
            )

    if not _console(f"{ROLLBACK_CONSOLE_TOKEN} scene={stored.scene_id}"):
        _note_console_loss(session, OUTCOME_ROLLED_BACK)
    return OUTCOME_ROLLED_BACK


def rollback_warp_scene_on_send_failure(session: object, label: object) -> str:
    """`CORE-REQUEST-GM-055`'s hookup.  Undo a warp row whose frame never
    left the wire at all.

    THE WINDOW THIS CLOSES.  `persist_warp_scene` writes the destination row
    at FRAME-COMPOSE time (`chat_command_action._persist_warp_scene`, called
    from `_warp_teleport_action_no_coords`), and the socket write for that
    same action happens roughly 2,200 lines later, in `current/pf_login_
    game_server_v141.py`'s own action-send loop -- chief's zone, where this
    lane may not put a call (`AGENTS.md` section 7).  If the socket dies in
    that gap (`ConnectionResetError`, `ConnectionAbortedError`,
    `BrokenPipeError`, `OSError` -- the loop's own `except` clause, which
    already prints `SEND_FAILED {label} {e!r}` before `break`), the row now
    names a scene the client was NEVER SENT TO, and nothing before this
    function put it back.  That is the same character-bricking shape
    `rollback_warp_scene`'s docstring closes for the audit-append window,
    one send-loop iteration later and entirely outside this lane's own call
    stack -- which is why chief calls IN rather than this lane calling OUT.

    ONE ARGUMENT NARROWS THE BLAST RADIUS TO ONE LABEL.  The send loop calls
    this after EVERY queued action fails to go out, not only a warp's, so a
    `say`, a `/speed` frame or a staged-login write must cost this function
    NOTHING.  `label != SEND_FAILURE_WARP_ACTION_LABEL` returns
    `OUTCOME_NOT_A_WARP` before touching `session` at all -- no read, no
    write, no console line -- because a wrong-label call is not evidence of
    anything this module is about.

    WHERE `previous` COMES FROM, AND WHY IT IS SAFE TO TRUST HERE.
    `persist_warp_scene` restores `foundation.selected` to the PRE-WARP
    snapshot immediately after the durable write succeeds (module docstring:
    "the durable row moves; the in-memory row does not" -- it stays the last
    position the client is KNOWN to have reported).  Nothing between then and
    a `SEND_FAILED` on the very same action changes it: the client cannot
    have reported a new position for a frame that never reached it.  So
    `foundation.selected.position`, read HERE, is exactly the row
    `_persist_warp_scene` captured with `row_before_warp` before the write --
    without this function needing a second parameter chief's call site would
    otherwise have to thread through 2,200 lines of unrelated code to supply.

    NEVER RAISES, same house rule as `rollback_warp_scene`: this runs inside
    the send loop's own `except` block, on the game-listener thread, and a
    raise here must not mask the `SEND_FAILED` handling already in flight.
    Delegates every write, restore, read-back and console line to
    `rollback_warp_scene`, so a `session` shape this module cannot act on
    reports the SAME named outcomes (`no_session_door`,
    `rollback_refused_*`, ...) a caller of that function already knows.
    """
    if label != SEND_FAILURE_WARP_ACTION_LABEL:
        return OUTCOME_NOT_A_WARP
    foundation = getattr(session, "foundation", None)
    selected = getattr(foundation, "selected", None)
    previous = getattr(selected, "position", None)
    return rollback_warp_scene(session, previous)


def _rollback_failed(previous: Position, reason: str, session: object) -> str:
    """`_fail`'s twin for the undo: same rule, different token and scene.

    The scene named is the one the row was being put BACK to, because that is
    the fact a tester needs -- "the row should now read scene 1 and does not".
    """
    if not _console(
        f"{ROLLBACK_FAIL_CONSOLE_TOKEN} scene="
        f"{getattr(previous, 'scene_id', '?')} reason={reason}"
    ):
        _note_console_loss(session, reason)
    return reason


def _registry_forbids_persist(scene_id: object) -> bool:
    """Whether THIS scene is pinned `persist_position_allowed=False`.

    Asked only after a read-back has already shown the row did not move, and
    only to pick which true word to report.  Fails CLOSED to "no" -- an
    unreadable or raising registry must not let a real silent-write defect be
    reported as a deliberate policy refusal, which is the direction that
    would hide a bug rather than name one.
    """
    if isinstance(scene_id, bool) or type(scene_id) is not int:
        return False
    try:
        return not world_scene_travel.is_position_persist_allowed(
            # THE SAME REGISTRY THE REST OF THE CALL USED.  Left to its
            # default this helper re-reads the registry FILE, so one
            # `persist_warp_scene` could judge `login_would_accept` against
            # the runtime's boot object and this question against a fresh
            # disk read -- the very two-registry split
            # `use_boot_scene_registry` exists to remove, reintroduced one
            # helper down.  A `None` snapshot (unreadable registry) hands
            # `None` through and this reads the file exactly as it did
            # before, which is the shipped behaviour for that case.
            scene_id, _login_registry_snapshot(),
        )
    except Exception:  # noqa: BLE001 - see docstring: fail closed to "no".
        return False


def _console(line: str) -> bool:
    """Put one line on stderr.  Never raises.  NEVER falls back to stdout.

    `pf-adversary` round `741zlx`, finding 3 (MAJOR, MEASURED).  Both callers
    used to say `print(..., file=sys.stderr)`, and `sys.stderr` can be `None`
    -- a detached console, `pythonw`, a harness that closed it.  `print` reads
    `file=None` as "use stdout" and writes the token there without raising, so
    the guard both call sites had (a `try/except`) could not see it happen.
    That is the exact incident the sibling next door documents and guards
    against (`chat_command_action.py`: "`None` is checked separately ...
    `print` would quietly write the token to STDOUT (pf-adversary D1), which
    is the `lane_hooks` JSON-artifact incident"), and it is the reason this
    module's own `CONSOLE_TOKEN` comment gives for choosing stderr at all:
    `tools/pf_runtimeres_death_headless_replay.py --json` writes its artifact
    on stdout, so a token that lands there corrupts the artifact instead of
    informing a tester.

    Returns whether the line was really written, so a caller can NAME a lost
    line rather than skip it in silence (finding 4).
    """
    stream = sys.stderr
    if stream is None:
        return False
    try:
        print(line, file=stream)
    except Exception:  # noqa: BLE001 - a closed, replaced or raising stderr
        # must not turn a named outcome back into a raise, nor undo whatever
        # the outcome already cost or saved.  The row is the deliverable; the
        # line about it is not.
        return False
    return True


def _note_console_loss(session: object, reason: str) -> None:
    """Record that the console line for `reason` never reached the screen.

    Defensive to the bone: this runs on the game-listener thread inside error
    handling, so a session with no `events`, a read-only `events`, or an
    `append` that raises costs nothing.  A lost line that is also an
    unrecorded loss is the failure mode this exists to end, but it must not
    become a second way to take the thread down.
    """
    try:
        events = getattr(session, "events", None)
        if events is None:
            return
        events.append(f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{reason}")
    except Exception:  # noqa: BLE001 - see docstring
        return


def _fail(target: WarpTarget, reason: str, session: object = None) -> str:
    """Print `FAIL_CONSOLE_TOKEN` and hand the reason word straight back.

    `COO-DECISION 20260904_1646` item 2: every reachable non-persisted
    outcome below `persist_warp_scene`'s target-shape check gets this line,
    named with the SAME reason word the caller already receives as the
    return value -- one source of truth, not a second vocabulary to keep in
    sync.  `target.scene_id` is always readable here: every call site sits
    past the `isinstance(target, WarpTarget)` guard at the top of
    `persist_warp_scene`.
    """
    if not _console(
        f"{FAIL_CONSOLE_TOKEN} scene={target.scene_id} reason={reason}"
    ):
        # The line is gone; the loss is not.  `session` is optional only so
        # the older direct callers in the tests keep working -- every call
        # from `persist_warp_scene` passes it.
        _note_console_loss(session, reason)
    return reason


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
