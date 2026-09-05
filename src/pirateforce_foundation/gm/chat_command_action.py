"""Turns one authorized GM chat line into an outbound wire ACTION, or None.

WHY THIS MODULE EXISTS (the measured gap it closes)
---------------------------------------------------
`lane_hooks/lane_gm_chat_command.py` already routes an inbound 0xAC52 chat
line to `gm/chat_command.handle_local_talk_chat`, and `CORE-REQUEST-GM-028`
asks chief for a `lane_hooks.fire()` point at the 0xAC52 branch to drive it.
That request, as written, CANNOT ever move a character on screen, and this
module exists because that was worth stating plainly instead of discovering
it after an attended boot:

`lane_hooks.fire()` is fire-and-forget by explicit contract -- its own
docstring says "Never returns a value; hooks that need to hand something
back to runtime.py are not what this point shape is for".  And a LANE can put
bytes on the wire by exactly one route: the `(label, pc, frame, delay)`
action list `runtime.py`'s `dispatch()` RETURNS, which the legacy serve loop
drains at `current/pf_login_game_server_v141.py:7755`.  (Precision, after
pf-adversary's defect 11: that is not the only `sendall` in the process --
the legacy file has four, including a heartbeat worker thread at 7428 and the
login/select sites at 7994/8002.  None of them is reachable from a lane; the
claim is about what a lane can queue, not about how many sockets writes exist.)
Nothing on a session object can queue a frame either -- `src/.../connection.py`
is accept/bind/close plumbing with no action queue, and `gm/dispatch.py`'s own
docstring already said it, though only as the tail of a bullet about not sending
0x8C77 back on the 0x51E9 lane: "this lane has no send path outside a
CORE-REQUEST wiring point regardless" (`gm/dispatch.py:40`, quoted with its
last word restored -- pf-adversary round `vvxkft` flagged the earlier
version for dropping it and reading the caveat as an architectural fact).

So GT-127 under GM-028's shape decides "did the server READ the line",
judged on the ndjson audit log -- which is what that entry honestly says it
decides.  It does not and cannot decide "did the character move".  This
module is the missing half: a single function chief can call from the same
0xAC52 branch that RETURNS an action, in exactly the shape
`gm_state_action` (CORE-REQUEST-006) already uses -- assigned at the
`GM_UPDATE_STATE_AFTER_LOGIN` tuple and appended under `if gm_state_action
is not None:` about 200 lines further down, both in `runtime.py`.

!! NO LINE NUMBERS FOR FILES THIS LANE DOES NOT OWN.  ~~`runtime.py:5181`
(assign) / `runtime.py:5396` (append) / `runtime.py:4784` (fire point)~~ --
all three were wrong, and the round that fixed them (`xk4wmz`) found they
had drifted AGAIN between chief's letter naming the corrected values
(`5303-5305` / `5518`, letter `20260829_0015`) and the commit that read
them (`5334` / `5549`).  Two corrections in one day is the argument:
`runtime.py` is chief's file, this lane cannot stop it moving, and a pin
into it rots silently -- it never fails, it just quietly points at damage
dispatch instead of the thing it names.  Cite ANCHOR TEXT that greps, and
let the numbers go.  (`say_wire.py` and `tests/test_gm_say_action.py` took
the same medicine for the `IDENTITY, STATED HONESTLY` citation.)

!! WIRE EXACTLY ONE OF THE TWO -- ~~AND THE OTHER ONE IS ALREADY WIRED~~.
That sentence described GM-028's shape, where chief had landed the
`fire()` point first and this module was DORMANT.  RESOLVED, and the
direction is now REVERSED: chief did what `CORE-REQUEST-GM-029` asked in
round `apk7ue` (R217, `pirate-force-server#214`, letter
`notes_to_chief/20260829_0015_CHIEF-REPLY-CORE-REQUEST-GM-029-route-
replaced-on-main.md`) -- one commit, the `fire()` line DELETED and a direct
call to `make_gm_chat_command_action` put in its place.  So THIS module is
the live route, and `lane_hooks/lane_gm_chat_command.py` is the one that is
now registered-and-never-fired (its own docstring records why this lane
kept it anyway).

The one-of-two rule itself is unchanged and is the reason the replacement
had to be one commit: if both were wired, every GM chat line would be
authorized twice, written to the ndjson audit log twice for one typed line,
and charged twice against `chat_command`'s own rate limit -- the second
charge being the one that silently starts refusing real commands.  It is no
longer held by a sentence in a letter: `tests/test_gm_chat_command_action.py
::OneOfTwoWiringTests` reads the real `runtime.py` and refuses both states
(both wired, and neither wired).

That is also why this module's event names were renamed away from the hook
route's, and not the other way round: at the time the hook route was the
live one, chief had pinned its names as literals in
`tests/test_gm_chat_command_dispatch_wiring.py` on main, and GT-127's
headless drill greped for them.  A dormant route renames for free; a live
one does not.  The renaming outlived the reason -- the `gm_chat_action_*`
namespace this module emits is now the live one, and GT-127's gate-2 greps
were rewritten against it in round `xk4wmz` after the attended tester's
job 1331 aborted on the stale ones.  See `EVENT_ACCEPTED_PREFIX` below.

WHAT IT DOES NOT DO
-------------------
* It does not decide GM status.  `handle_local_talk_chat` does, on the
  authenticated `session.token`, before it decodes a byte -- one
  authorization point for this lane, not two (the mistake this module would
  make by re-checking the allowlist "to be safe").
* `ForcePos` does not cross scenes, and never will -- it carries no scene id
  at all (RE-090); `gm/warp_executor.py` refuses to send an in-scene hop for
  a command that asked to leave the scene, because that would misrepresent
  what happened.  ~~So this module does not cross scenes.~~ NO LONGER TRUE
  OF THE WHOLE MODULE, only of that one composer (round `gejldf` first, this
  round further): a cross-scene `/warp` with coordinates now DOES cross a
  scene, live, mid-session, via `legacy.make_login_teleport` -- the SAME
  encoder `runtime.py`'s own call sites already send, proven by GT-106-R2 to
  move a real client's screen (COO-DECISION 2026-08-31T14:41+07:00).  A
  cross-scene `/warp` with NO coordinates still cannot cross anything mid-
  session (neither composer has a position for that shape) and still STAGES
  the account's next login scene through `gm/login_scene_stage.py` instead
  -- a config write, not a frame; the GM has to log out and back in, and
  every report that uses it has to say so.  See `_warp_action`'s routing
  rule for which of the three shapes a given command takes.
* It does not send anything for `npc`/`item`/`lv`/`spawn`.  Those
  parse and audit exactly as before and return no action -- naming them here
  as "not wired yet" by event is the difference between a lane that is
  honest about its coverage and one that looks broken.
  ~~`say` belongs in that list too~~ -- NO LONGER TRUE as of round `w8hnu9`:
  `say` now has an action path of its own (`_say_action`), gated on
  `say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` exactly the way `warp`
  is gated on `teleport_wire`'s.  Both gates are shut today, but they are
  shut on DIFFERENT things and that difference is the point of the round:
  `warp` waits on chief's confirmed-position write point plus a COO unlock
  (CORE-REQUEST-GM-030), while `say` waits on ~~one measurable byte
  (RE-132)~~ and on nothing about position at all -- it moves nobody and
  writes no DB row.  THE BYTE IS NO LONGER WHAT `say` WAITS ON: RE-132
  answered `0` (result letter `20260829_0010`, consumed round `z6gu2n`), and
  it is the byte the imported codec already emits.  What `say` waits on now
  is an OFFICIAL LOCK -- COO-DECISION 2026-08-29T00:41+07:00
  (`notes_to_chief/20260829_0041_COO-DECISION-say-gate-lock-is-official-and-
  gt016-goes-first.md`): condition (A), per-connection identity, plus (B),
  the client-observable screen, liftable only by a NEW COO-DECISION and
  explicitly not by a round of this lane.  `tests/test_gm_say_gate_lock.py`
  holds it.  `say` is therefore still the SHORTEST REMAINING PATH from a
  typed chat line to something a tester can see -- [สมมติของสาย GM - รอ RE],
  and the label is not decoration.  What is measured: the payload codec (CHAT-CHANNEL-001) and
  the blocker count.  What is NOT: that the client draws it.
  `reports/PF_CHAT_CHANNEL001_*_20260818.md` enumerates eight per-channel
  style names off the client's ordered downcast chain at `0x659870`
  (LocalTalk, WhisperTalk, GuildTalk, PartyTalk, YellTalk, LocalPerformance,
  CustomDefine, ClassTalk) and GMGlobal is NOT among them, and that report's
  own section 6 lists on-screen rendering under "does not claim".  RE-129
  taught this lane the difference the hard way -- `ForcePos`'s registered
  handler turned out to be `mov al,1; ret 4` -- so RE-132 asks for 0x9F2C's
  downcast branch body alongside the version byte.  Until one of those
  answers, "shortest path" ranks the blockers; it does not promise a pixel.
* It does not broadcast.  `say` returns a per-connection action like every
  other action in this file; the GM sees his own line.  See `_say_action`.
* ~~!! It does not put a single ForcePos byte on the wire today, because
  `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` is None.~~ ~~(RE-129
  open)~~ RE-129 ANSWERED on 2026-08-28T20:09+07:00 -- the byte is 0 -- and
  ~~the constant is still None on purpose: COO-DECISION 21:30 locks it there
  until chief's confirmed-position write point is on main (CORE-REQUEST-GM-030).~~
  That write point (`GM_WARP_POSITION_CONFIRMED`, `runtime.py`) landed on
  main, and COO-DECISION 20260830_1645/1742 lifted the lock: the constant is
  now `0` and `/warp` (same-scene) composes real wire actions by default.
  See that constant's block and `test_gm_force_pos_version_lock.py` -- ~~and
  note that release day edits TWO test files: `VersionGateTests` in this
  module's own suite asserts the constant is None unconditionally.~~ that
  release day did edit both test files; `VersionGateTests` now asserts the
  constant equals `0`.
  The rest of that constant's comment still holds: the vital version byte is
  per-vital (0x5A19 -> 0, ForcePos -> 0, TeleportVital -> 4 from the client's
  own constructors; SelectActor -> 10 from the legacy server source -- four
  values, two layers, still no default) and GT-101 measured what an unproven
  version does to a real client -- modal error, connection halted, socket
  closed.  This module gates on the constant being not-None for the same
  reason `runtime.py` gates the login GM-state frame on
  `state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` -- grep that constant
  for TWO adjacent hits, the `and ...` test and the value handed to the frame
  builder, with the withheld branch just below spelling
  `gm_update_state_frame_withheld_no_confirmed_` (grep THAT fragment, not the
  full event name: the name is split across two source lines by the line
  wrap, so the whole string matches nothing -- checked, and it is the same
  rot as a line number, caught in this round's own edit) -- and refuses by
  name
  instead.  ~~When RE-129 answers, that one constant is the whole change.~~
  It answered, and it is not: the change is chief's write point on main, then
  COO lifting the lock, then the constant, then the second test file above.

POSITION OWNERSHIP AFTER A WARP -- ANSWERED, AND THE ANSWER IS THE DESIGN
--------------------------------------------------------------------------
~~OPEN, AND IT MUST BE ANSWERED BEFORE RE-129 CHANGES THE CONSTANT~~
ANSWERED 2026-08-28T21:30+07:00 by COO-DECISION (pf_bridge/notes_to_chief/
20260828_2130_COO-DECISION-position-ownership-after-gm-warp.md), replying to
this lane's ASK-COO of 19:05.  The question and the reasoning that produced it
are kept below unchanged, because they are why the rule exists.  The ruling,
in three lines, is now the contract of this module:

  1. THE OWNER OF A POSITION IS THE POSITION THE CLIENT CONFIRMED.
     A `ForcePos` frame is a REQUEST that left the server.  It is never
     evidence that a character moved -- and RE-129 (2026-08-28T20:09+07:00)
     made that concrete rather than cautious: the handler the client has
     REGISTERED for ForcePos is `mov al,1; ret 4` and reads no payload at all.
  2. THE SERVER MUST NEVER WRITE A POSITION IT DID NOT OBSERVE.  Not to the
     durable row, not to `selected.position`.  Writing the requested point at
     send time is the "false green" this project has already paid for three
     times, except that this one would make the DB lie silently and take
     aggro range, pickup range and the logout point down with it.
  3. THE CONFIRMING EVENT IS THE FIRST `TargetPos` AFTER THE FRAME, and the
     write belongs there.  That write point lives in `runtime.py`, which is
     not this lane's zone: CORE-REQUEST-GM-030 (round `fo2lgh`) asks chief
     for it, and until it is on main the version constant stays locked (see
     `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED`).

So THIS MODULE'S BEHAVIOUR IS ALREADY CORRECT AND MUST NOT BE "FIXED": it
composes a frame and does not checkpoint.  A future round that adds a
`foundation.checkpoint` call here, meaning well, would be implementing the
one option COO explicitly struck out.  The gap that remains is not in this
file; it is the missing confirmed write point in runtime.py.

THE SAME RULE, APPLIED TO THE CROSS-SCENE TELEPORT PATH WITHOUT RE-ASKING
IT.  `_warp_teleport_action`'s `TeleportVital` frame is a REQUEST in the
identical sense a `ForcePos` frame is -- GT-106-R2 proved the mechanism
moves a real client's screen, which is a stronger fact than anything ever
measured about `ForcePos`, but it is still not per-frame confirmation, and
`WarpTarget`'s own docstring says so explicitly.  `_warp_teleport_action`
therefore composes and parks exactly the way `_warp_action`'s ForcePos
branch does, and does not checkpoint either -- the three-line ruling above
was never scoped to one vital id, and this module does not narrow it to one
just because a second composer arrived.

THE QUESTION AS IT WAS ASKED (kept, not deleted)
------------------------------------------------
pf-adversary (round `gr2q9j`) asked the question that design did not answer:
after a ForcePos leaves, WHO OWNS THE CHARACTER'S POSITION?  This module
composes a frame and stops.  It does not call `foundation.checkpoint`, so the
durable row and `selected.position` still hold the pre-warp point, and the
only thing that reconciles them is the client's next `TargetPos` -- which
requires the GM to move, and which `runtime.py`'s scene-load path does not
even checkpoint while a `scene_load_scenario` is loaded.  Meanwhile the ndjson audit row says
`executed: false` and is written identically whether the frame went out or
was withheld at the version gate, so the log cannot answer it either.

That is a deliberate limit of GM-003 v1 (parse/audit only), not an oversight
found late -- but it stops being harmless the moment bytes actually go out,
because "the client is at (3000,3000), the database says (0,0)" then has no
defined answer.  Written into `GT-128`'s preconditions as a third blocker so
nobody boots the visible warp before the question is settled, and raised to
COO in `notes_to_chief/20260828_18xx_LANE-GM-ASK-COO-*`.

ALSO OPEN, same reason (recorded, not fixed here):
* ~~No coordinate range check.  `warp_executor` rejects NaN/Inf but accepts
  anything up to +/-3.4e38, so a decimal slip (`/warp 2 100000 200`) composes
  a real frame for a point this project elsewhere calls off the map --
  `world_scene_entry.py` refuses exactly that with `RELOCATED_OUTSIDE_GROUND`
  against a scene's `ground_extent`.  The fix is to reuse lane A's check by
  import (never to copy its logic here); it is not done this round, and the
  version gate means nothing can reach a client before it is.~~ DONE (round
  `<see docs/GM_LANE.md changelog>`, `pf_bridge/notes_to_chief/20260901_2252_
  LANE-A-REPLY-to-lane-gm-ground-check-api-ready.md` opened
  `world_scene_entry.is_position_within_scene_ground`, imported by import as
  asked, never copied). `warp_executor._refuse_if_outside_ground` now calls
  it from both `make_warp_force_pos_frame_with_target` and
  `make_warp_teleport_frame_with_target`, and refuses a `False` verdict --
  except for a scene whose only spawn evidence is a PROVISIONAL-OWNER-DECREE
  (scene 17 today), where the underlying check returns `False` for every
  point and a hard gate would have silently revoked the one cross-scene
  destination COO-DECISION 2026-08-31T14:41+07:00 already authorized; see
  `_refuse_if_outside_ground`'s own docstring for why that carve-out is
  read from `spawn_provenance`, not guessed.  STILL OPEN: any scene with NO
  `ground_extent` at all (every scene in the registry today except 17 and
  278, including scene 2 in the `/warp 2 100000 200` example above) has no
  ground data to check against, so this fix protects only the scenes that
  happen to carry it -- not a general bound on every scene.
* `accounts.is_gm_account` re-reads and re-parses the allowlist JSON on every
  call, and this module is what first makes that read reachable on every chat
  line of every player.  Identity-first ordering means a non-GM still causes
  no write, no decode and no rate-limit charge (measured) -- but it is one
  uncached `stat` + `open` + `json.load` per frame on the shared listener
  thread.  Caching it changes what "editing the config takes effect when"
  means, which deserves its own decision rather than a silent change here.
* `ForcePosBody`'s field names.  `PF_SERIALIZER_FIELDS.tsv` proves three f32
  at struct +0/+4/+8 and carries NO axis names; `x, y, z` is a name this lane
  assigned, and this module is what makes it load-bearing by pairing the
  command's two arguments with `Position.z`.  `Position`'s own ordering is
  proven by `make_login_teleport`, but that is a different message, and two
  layers agreeing is consistency, not proof.  ~~RE-129 carries this as its
  second question.~~ RE-129 ANSWERED the version and CLOSED THE OFFSETS
  (f32 at struct +0/+4/+8, i.e. ForcePos +0x14/+0x18/+0x1C) but returned a
  BOUNDED NEGATIVE on the names: the common vec3 helper carries no field
  names, the registered handler never reads the three values, and
  `PF_FIELD_VALIDATION.tsv` is NOT_OBSERVED both ways -- so no client-side
  crosswalk separates first/second/third into x/y/z.  RE-129's own words:
  do not use the resemblance to another message's Position as evidence.
  Still [สมมติของสาย GM - รอ RE].

FAIL-CLOSED
-----------
The call site is inside chief's dispatch, on the game-listener thread, for
every chat line every player sends.  An exception escaping here would take
that thread down for everyone -- so nothing escapes: every failure is caught,
named on `session.events`, and reported as "no action".  Not sending is
always safe; this module can never do worse than the server did before it.
Event names carry refusal reasons and exception TYPE names only, never the
sentence a human typed and never an exception's message text (which can
embed client bytes): a console full of these leaks nothing about what
players said, and stays cp874-safe on the bridge console.
"""
from __future__ import annotations

import sys

from dataclasses import dataclass
from types import MappingProxyType

from .. import gm_npc_toggle_recompose
from .. import persistence_typed_attrs
from . import (
    bt_gm_probe,
    item_catalog,
    level_command,
    login_scene_stage,
    npc_switch_catalog,
    say_wire,
    speed_wire,
    teleport_wire,
    warp_executor,
)
from .chat_command import (
    REFUSAL_LOG_QUOTA_EXCEEDED,
    REFUSAL_LOG_WRITE_FAILED_PREFIX,
    # THE ONE REFUSAL THAT GETS AN ON-SCREEN SENTENCE (COO-DECISION `0647`).
    # Imported by NAME from the module that owns it, never re-spelled here as
    # a literal: `chat_command.py` keeps its refusal words beside the comment
    # that says which of them may and may not reach a human, and a second
    # copy of the string in this file is how the two would drift apart.
    REFUSAL_PARSE_ERROR_PREFIX,
    REFUSAL_RATE_LIMITED,
    # CHAT-TAIL-001: the one refusal this round may retry, imported by name
    # from the module that owns the word, for the reason spelled out three
    # imports above.
    REFUSAL_UNDECODABLE_PREFIX,
    SERVER_SIDE_DROP_REFUSALS,
    TYPED_COMMAND_REFUSAL_PREFIXES,
    handle_local_talk_chat,
)
from . import chat_frame_tail
from . import login_scene_admission
from .login_scene_admission import stageable_scene_ids
# The way out for THIS module's refusals: `/warp` writes the single-use map,
# so it must offer the set that map admits.  Imported by name, like
# `stageable_scene_ids` beside it, so the seam a test moves is this module's
# own binding rather than a predicate two layers down that the config reader
# also depends on.
from .login_scene_admission import single_use_stageable_scene_ids
from .login_scene_override import console_safe
from .commands import (
    COMMAND_NAMES,
    OUTCOME_COMPOSED,
    OUTCOME_LV_ROW_WRITTEN,
    OUTCOME_REFUSED_PREFIX,
    OUTCOME_STAGED_LOGIN_SCENE,
    OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED,
    OUTCOME_WITHHELD_PREFIX,
    log_gm_command_outcome,
    # CORE-REQUEST-GM-040.  Imported by NAME, and note what is NOT imported
    # beside it: `OUTCOME_QUEUED`.  The writer takes no outcome parameter and
    # hard-codes the word, so this module never names it -- which keeps
    # `QueuedIsReservedTests`' AST scan over the lane's source both green and
    # honest ("no lane file outside the definition site names the reserved
    # word") on the very round the word became writable.
    log_gm_command_queued,
)
from .say_wire import make_say_broadcast_frame
from .warp_executor import (
    make_warp_force_pos_frame_with_target,
    make_warp_teleport_frame_no_coords_with_target,
    make_warp_teleport_frame_with_target,
    warp_command_has_coordinates,
    warp_command_scene_id,
    warp_no_coords_live_target,
)
from .warp_target_record import (
    clear_warp_target,
    current_character_id,
    record_warp_target,
)
from .warp_scene_persist import (
    OUTCOME_PERSISTED as WARP_SCENE_OUTCOME_PERSISTED,
    OUTCOME_ROLLED_BACK as WARP_SCENE_OUTCOME_ROLLED_BACK,
    persist_warp_scene,
    rollback_warp_scene,
    row_before_warp,
)
from . import warp_send_watch
from . import warp_relog_stage

# The action label the serve loop logs for a real GM warp.  ASCII, screaming
# snake case, same convention as every other label in runtime.py's action
# lists ("GM_UPDATE_STATE_AFTER_LOGIN", "V113_TELEPORT_..."), so an attended
# run can grep the console for it the same way.
#
# !! THE SUBSTRING `TELEPORT` IS LOAD-BEARING, NOT DECORATION.
# `runtime.py`'s `_move_authority_note_server_moves` (grep the def; the label
# test is the `if action and "TELEPORT" in action[0]` line inside it)
# identifies a
# server-initiated move by exactly one thing -- "the action it queued carries
# TELEPORT in its label" -- and reopens the move-authority grace window on it.
# pf-adversary (this round) measured what a label without it costs, and it is
# not cosmetic: a GM warps 4243 units, the client honestly reports the new
# position, the gate measures that against a baseline the warp never moved,
# refuses the reading as over budget, and -- because
# `_move_authority_verdict`'s own docstring says the baseline advances only on
# readings the gate admitted -- refuses EVERY later reading too.  The durable
# row stays frozen for the rest of the session and logout persists the
# pre-warp point, which is the exact failure that function was written to
# prevent.  A test pins this substring against that call site; do not rename
# this constant without reading it.
WARP_ACTION_LABEL = "LANE_GM_CHAT_WARP_TELEPORT_FORCE_POS"

# The action label for a GM `/warp <scene_id> x y` that crosses scenes and
# fires LIVE (COO-DECISION 2026-08-31T14:41+07:00) instead of staging.
#
# !! THE SAME "SUBSTRING `TELEPORT` IS LOAD-BEARING" RULE AS
# `WARP_ACTION_LABEL` ABOVE APPLIES HERE, MORE LITERALLY THAN IT DOES THERE.
# `WARP_ACTION_LABEL` carries `TELEPORT` even though its frame is a
# `ForcePos`, because `runtime.py`'s `_move_authority_note_server_moves`
# keys on the substring, not on which vital actually went out.  This
# label's frame genuinely IS a `TeleportVital`, so the same requirement
# applies for the same reason and for an even more literal one: a GM who
# crosses scenes is exactly the case where a stale move-authority baseline
# (still holding the pre-warp scene's coordinates) would refuse the very
# next position report the new scene sends.  A test pins this substring
# against the same call site `WARP_ACTION_LABEL`'s own test does; do not
# rename this constant without reading that one first.
#
# Deliberately NOT `WARP_ACTION_LABEL` reused for both frame shapes: this
# label's own name says `FORCE_POS`, which would be a lie on the console for
# a `TeleportVital` send, and an attended tester reading `[G>] <label>` off
# the server console (see GT-106-R2's own wire log) needs to be able to
# tell which mechanism actually fired without opening this file.
WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL = (
    "LANE_GM_CHAT_WARP_CROSS_SCENE_TELEPORT_VITAL"
)

# GM-A (`PANYA-ORDER 20260901_0215` section 3, chief's `R278` broadcast,
# `GT-182`): the action label for a `/warp <scene_id>` that crosses scenes
# with NO typed coordinates and fires LIVE at the destination's own
# `world_scene_travel`-pinned marker spawn, instead of only staging the
# next login the way this shape has since round `gejldf`.
#
# !! THE SAME "SUBSTRING `TELEPORT` IS LOAD-BEARING" RULE AS
# `WARP_ACTION_LABEL`/`WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL` ABOVE APPLIES
# HERE TOO, for the identical reason: this frame genuinely is a
# `TeleportVital` (`legacy.make_login_teleport`), and a GM who crosses
# scenes this way is exactly the case where a stale move-authority baseline
# would refuse the new scene's very next position report.  Deliberately a
# DIFFERENT label from `WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL`, not that
# one reused: an attended tester reading `[G>] <label>` off the console
# needs to tell "GM typed x/y" from "server picked the marker spawn" apart
# without opening this file -- the two shapes have different wire/DB pass
# criteria in `GT-182`/`GT-172` and must not share one console line.
WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL = (
    "LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_TELEPORT_VITAL"
)

# The action label for a GM `say`.
#
# !! THIS ONE MUST *NOT* CONTAIN `TELEPORT`, FOR THE SAME REASON THE WARP
# LABEL MUST.  The rule inside `runtime.py`'s
# `_move_authority_note_server_moves` is a substring test on the
# label of a queued action -- `if action and "TELEPORT" in action[0]` -- and
# it reopens the move-authority grace window, which admits position readings
# far from the last one the gate accepted.
# PRECISION, after pf-adversary (this round) re-derived the call site rather
# than trusting the earlier wording here: it is NOT "every queued action" on
# every boot.  `runtime.py`'s sole call of
# `_move_authority_note_server_moves(actions)` runs only when
# `move_authority_hypothesis_scenario is not None`, so on a default boot the
# substring is inert -- in BOTH directions, which also means the warp label's
# TELEPORT is inert there.  The label still must not carry it: the scenario
# is exactly the configuration an anti-cheat measurement runs under, and that
# is the run where a `say` must not look like a server-initiated move.
# A `say` moves nobody.
# Naming this label "..._TELEPORT_..." out of symmetry would hand every GM a
# way to widen the anti-cheat window on demand, one chat line at a time,
# while the character never moved an inch.  A test pins the absence of that
# substring against the same call site, not against this comment.
SAY_ACTION_LABEL = "LANE_GM_CHAT_SAY_GM_GLOBAL_MESSAGE"

# The action label for a GM `/gmprobe <variant_id>` (CORE-REQUEST-GM-043).
#
# !! MUST NOT CONTAIN `TELEPORT`, same reason as `SAY_ACTION_LABEL` above: a
# probe variant repositions nobody, so it must never reopen the
# move-authority grace window `runtime.py`'s `_move_authority_note_server_
# moves` keys on that substring.
GMPROBE_ACTION_LABEL = "LANE_GM_CHAT_GMPROBE_STATE_VITAL"

# The action label for a GM `/speed <value>` (CORE-REQUEST-GM-049): a sparse
# `UpdateAttrVital` (0x309A) send that sets ONLY the x=7 mask bit
# (`gm/speed_wire.py`).
#
# !! MUST NOT CONTAIN `TELEPORT`, same reason as `SAY_ACTION_LABEL`/
# `GMPROBE_ACTION_LABEL` above: `runtime.py`'s `_move_authority_note_server_
# moves` reopens the move-authority grace window on that exact substring,
# and `/speed` repositions nobody -- it changes one attribute field, not a
# position.  The CORE-REQUEST letter that asked chief to wire this branch
# says so in the same sentence it names the label
# (`pf_bridge/notes_to_chief/20260901_1728_LANE-GM-CORE-REQUEST-GM-049-
# speed-sparse-x7-runtime-send-point.md`).
SPEED_ACTION_LABEL = "LANE_GM_CHAT_SPEED_UPDATE_ATTR_VITAL"

# The label a REFUSAL's on-screen sentence goes out under, and it is a
# separate label on purpose -- COO-DECISION 2026-09-02T03:45+07:00
# (`pf_bridge/notes_to_chief/20260902_0345_COO-DECISION-speed-refusal-
# localtalk-via-say-wire-12-ascii.md`) ordered the refusal to reach the
# screen, and nothing else about `/speed` changed with it.
#
# !! A NOTICE IS NOT THE COMMAND'S FRAME, and that distinction is load-
# bearing in two places downstream (`_make_action`'s `sent=` argument and
# its `_arm_queued_confirm` call).  LANE-GM's letter `pf_bridge/notes_to_
# chief/20260902_0419_LANE-GM-REPLY-CHIEF-speed-notice-two-decisions.md`
# measured what happens if the two are conflated: `_announce_console_
# outcome` opens with `if sent: return`, so returning a notice action from
# a refusal path would DELETE the `GM_CHAT_NO_BYTES_SENT ... why=refused_
# speed_* character_id=<rowid>` line that PR #527 landed for COO-DECISION
# `0147`'s half (b) -- closing the on-screen half by reopening the
# server-log half, with no test in the repo catching it (the tests that pin
# that line stand on `action is None`).  Hence `_Verdict.is_notice` below.
# It also MUST NOT contain `TELEPORT`, for the same `runtime.py` reason
# spelled out above this line.
SPEED_DENIED_NOTICE_ACTION_LABEL = "LANE_GM_CHAT_SPEED_DENIED_LOCAL_TALK_NOTICE"

# The SAME shape for the SYNTAX layer, ordered by COO-DECISION
# 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/20260902_0647_
# COO-DECISION-typo-layer-notice-is-TYPO-REFUSED-12-ascii-after-p1.md`): a GM
# who mistypes ANY command gets `say_wire.TYPO_REFUSED_NOTICE_TEXT` on screen
# instead of a chat line that vanishes.
#
# A SEPARATE LABEL FROM THE ONE ABOVE, for the reason that one is separate
# from `SPEED_ACTION_LABEL`: the two notices answer different questions
# ("the grammar refused you" vs "the command ran and the value was refused"),
# and an attended run that greps the serve loop's own action lines must be
# able to tell which sentence went out without decoding the frame.
#
# !! MUST NOT CONTAIN `TELEPORT`, same reason as every label above:
# `runtime.py`'s `_move_authority_note_server_moves` reopens the
# move-authority grace window on that exact substring, and a refused typo
# repositions nobody.
TYPO_REFUSED_NOTICE_ACTION_LABEL = "LANE_GM_CHAT_TYPO_REFUSED_LOCAL_TALK_NOTICE"

# `/lv <n>`'s two on-screen sentences (PANYA-ORDER 2026-09-06 01:55).  Two
# labels rather than one, for the reason the two above are separate: an
# attended run greps the serve loop's action lines to tell "the row was
# written" from "nothing was written", and both sentences ride the SAME
# `Channel_LocalTalkMessageVital` codec, so the label is the only thing that
# tells them apart without decoding bytes.
#
# !! NEITHER MAY CONTAIN `TELEPORT`, same reason as every label above:
# `runtime.py`'s `_move_authority_note_server_moves` reopens the
# move-authority grace window on that exact substring, and `/lv` moves
# nobody.
LV_SET_NOTICE_ACTION_LABEL = "LANE_GM_CHAT_LV_SET_LOCAL_TALK_NOTICE"
LV_REFUSED_NOTICE_ACTION_LABEL = "LANE_GM_CHAT_LV_REFUSED_LOCAL_TALK_NOTICE"

# The `characters` column LANE-DB's persistence entry point is keyed by for
# this one field, resolved THROUGH their own table rather than spelled here
# as the literal `"speed_walk"`.  Two reasons, both measured rather than
# stylistic: (1) `persistence_typed_attrs.column_for` raises `TypedAttrError`
# at IMPORT time if x=7 ever loses its column, so a schema change is loud
# instead of a `/speed` that silently refuses in front of a tester -- and be
# precise about how loud, because an earlier draft of this comment said "in
# this lane" and pf-adversary (round `hw6dix`, D5) measured otherwise:
# `runtime.py:40` imports this module at module level, so the failure is THE
# WHOLE SERVER REFUSING TO START, not one command refusing.  That is a
# deliberate trade -- a typed column that moved under this send site is a
# schema/lane disagreement nobody should discover mid-attended-round -- but
# it is a trade, and it is stated here rather than discovered on a boot;
# (2) it keeps the x -> column mapping owned in exactly
# one place, the way `speed_wire.SPEED_FIELD_NAME` already reads its own
# label out of `attr_wire.BY_X` rather than copying the string.
SPEED_TYPED_COLUMN = persistence_typed_attrs.column_for(speed_wire.SPEED_FIELD_X)

# Console token printed on the production path whenever an authorized GM
# command is handled.  `lane_hooks` prints `LANE_HOOK_FIRED` for the route
# this one replaces, and its docstring explains why that matters: the
# project's WIRED-v2 rule is that "import alone does not count, emission on
# the production path does".  Without a token here, a correctly wired call
# site and a call site chief never wrote produce identical console output for
# as long as RE-129 keeps the version gate shut (no action means no `[G>]`
# line from the serve loop) -- pf-adversary's defect 15.  Printed only for a
# line that passed the allowlist, so an ordinary player's chat never reaches
# it and the console does not fill with one line per player per sentence.
CONSOLE_TOKEN = "LANE_GM_CHAT_ACTION"

# Printed to stderr, once per refused cross-scene `/warp`, when the scene the
# GM typed is not one the login path could enter.  Deliberately NOT
# `login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN`: that token means "a
# file on disk is malformed" and this one means "the line you just typed
# named the wrong scene".  A tester greps for one or the other, and an
# operator hunting a bad config must not have to sift the tester's typos out
# of the same grep.  Spelled once so a test can match it exactly.
WARP_REFUSED_CONSOLE_TOKEN = "GM_CHAT_WARP_REFUSED"

# Printed to stderr, once, when a GM typed a line that LOOKS like a command
# and this lane refused it before the grammar produced anything to act on.
# A third token rather than a reuse of the two above, for the same reason
# they are separate from each other: `GM_CHAT_WARP_REFUSED` means "the scene
# you named is not one login can enter" and answers with a scene list, while
# this one means "that is not a command this lane knows how to read" and
# answers with a usage line.  An operator greps for one question at a time.
COMMAND_REFUSED_CONSOLE_TOKEN = "GM_CHAT_COMMAND_REFUSED"
# THE THIRD REFUSAL TOKEN, and the reason it is a third one rather than a
# reuse of either neighbour.  `COMMAND_REFUSED` means "you typed it wrong,
# here is the grammar"; `NO_BYTES_SENT` means "an ACCEPTED command reached a
# handler and the handler sent nothing".  Neither is true of a command that
# was well formed, came from an allowlisted GM, and was dropped by the SERVER
# ITSELF before dispatch ever saw it -- the rate limiter, the audit-log quota,
# an unwritable audit log.  Printing those under either neighbour's token
# would teach an operator grepping that token a false meaning for it, which
# costs more than a third word to learn.
#
# WHY IT EXISTS AT ALL: `COO-DECISION 2026-09-02T01:47+07:00` ruled that a
# refused GM command may not be SILENT.  pf-adversary (round `c637o1`)
# measured that the round's first draft closed that only for the refusals
# `_speed_action` itself produces -- 25 rapid `/speed 400` frames printed 20
# route lines and then NOTHING for the five the limiter dropped, which is
# exactly "the route was never wired" as seen from an attended chair.  The
# limiter's ceiling (`dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW`) is
# reachable by hand in a real session, so this was not a theoretical hole.
DROPPED_CONSOLE_TOKEN = "GM_CHAT_DROPPED_BEFORE_DISPATCH"

# Printed to stderr, once, when a command this lane ACCEPTED put no bytes on
# the wire and no other line said so.
#
# THE HOLE THIS CLOSES, MEASURED THROUGH THE REAL DISPATCHER THIS ROUND (the
# six inputs are reproduced in `rounds/GM_20260829_2231_accepted_and_sent_
# nothing_now_says_so.md`; the first draft of this comment cited a round file
# name that never existed, caught by pf-adversary D11):
#
#   /warp 2 100 200 -> events say `..._warp_withheld_no_confirmed_force_pos_
#                      vital_version_re129_open`; the CONSOLE said exactly
#                      `LANE_GM_CHAT_ACTION warp route=action` and nothing else
#   /say hello      -> same shape, `..._say_withheld_...`
#   /lv 10, /item, /npc, /spawn -> `..._no_wire_path_<name>`, console silent
#
# `route=action` is printed BEFORE any handler runs -- it means "this route
# was reached", which is the only thing it ever claimed -- so on the four
# commands that can never send today, and on the two whose version gates are
# shut, the last word the console said about the command was a line that
# reads like success.  A refused command was better served than an accepted
# one: `/warp 9999` gets a scene list, `/warp island` gets a usage line, and
# `/warp 2 100 200` -- the ONE command that can move a character on screen,
# and the whole subject of `GT-128` -- got a line that looks like it worked.
#
# WHO PAYS FOR IT, in the order the queue would have found out: an attended
# tester types the warp, nothing moves, and the console cannot separate "the
# version gate withheld the frame", "the client ignored a frame we did send"
# and "the route is dead".  Two of those three are PASS-shaped for the
# wiring and one is not, and the entry is graded from that console.
#
# A FOURTH TOKEN, not a reuse of the three above, for the reason they are
# each separate: this one means "we read you, and deliberately sent nothing".
#
# WHAT IT COSTS THE CONSOLE, stated because it is client-driven volume
# (pf-adversary D10, measured): an accepted command used to print one line
# and now prints two, so the ceiling doubles from 20 to 40 lines per
# `gm/dispatch.py` rate-limit window.  On the wired server `session.token`
# is the process-wide `--token`, so ANY connected player's `/lv 10` is an
# "authorized GM command" paying into that one shared bucket -- the same
# identity fact `_say_action` states.  Bounded by
# `RATE_LIMIT_MAX_CALLS_PER_WINDOW`, so a nuisance, not a flood; named here
# rather than discovered on an attended boot.
WITHHELD_CONSOLE_TOKEN = "GM_CHAT_NO_BYTES_SENT"

# And a FIFTH, for the one accepted command that sends no bytes and is not a
# disappointment: the cross-scene `/warp`, which writes the account's
# next-login scene and lands the GM there on the NEXT login.
#
# WHY IT IS NOT THE FOURTH TOKEN WEARING A HAT (pf-adversary D3, and the
# first version of this round earned it): `GM_CHAT_NO_BYTES_SENT` was made
# to say "nothing happened, here is the blocker".  A staged warp DID happen
# -- there is a config entry on disk deciding the next login -- so printing
# the no-bytes token for it would be false in the only direction that
# matters to a tester.  But printing NOTHING, which is what the first draft
# did, left the exact hole this round says it closes open for the ONE
# `/warp` form that changes anything today: the console said `route=action`
# and stopped, and the tester grading `GT-141` from that console could not
# tell a staged entry from a dead route.
#
# It carries the coordinates verdict because nothing else does: `/warp 278
# 100 200` silently drops the two numbers the GM typed (`ForcePos` cannot
# cross scenes, so the cross-scene half stages the SCENE and nothing else).
# That was invisible everywhere except the ndjson `outcome` word.
STAGED_CONSOLE_TOKEN = "GM_CHAT_STAGED_NEXT_LOGIN"

# THE `next=` SENTENCE THIS TOKEN CARRIES, and it is six sentences (three
# blockers x two tails, joined by `staged_next_step`) since
# `COO-DECISION 20260903_2050` item 2 ("the wording change is approved") --
# the decision that
# answered this lane's own letter `20260903_2005`.
#
# ~~next='log out and log back in to land there; nothing was sent to the
# client now'~~ -- STRUCK, one shape at a time, for two DIFFERENT reasons:
#
#   * IT LED WITH AN INSTRUCTION AND NEVER GAVE THE REASON.  The owner read
#     this line during R307 and reported it as "nothing happened"
#     (`PANYA-DECISION 20260903_1800`).  She was right about her screen: no
#     bytes went out.  What the line never said is WHY -- the destination is
#     a scene with `n_MARKER == 0` (17/126/278/997, `GT-182` nonclaim 4), so
#     no live composer has a spawn point to put in a frame there.  A reason
#     is what turns "nothing happened" into "nothing COULD be sent, and here
#     is the thing that is missing".  `PANYA-DECISION 1800`'s own remedy
#     (fire the live teleport instead) reached the marker-backed scenes in
#     round `07kjfd`; `COO-DECISION 2050` item 1 held the markerless scenes
#     shut -- deliberately, because R306 measured a coordinates-bearing warp
#     frame CLOSING the client (`ErrorData=28317`), so aiming one at an
#     inferred spawn is not merely unproven but dangerous.  Wording is
#     therefore the whole of what this lane may fix here, and it is item 2 of
#     that same decision.
#
#   * FOR A SAME-SCENE STAGE THE INSTRUCTION WAS ALSO USELESS.  `/warp 278`
#     typed while standing in 278 stages 278 and tells her to spend a whole
#     session on a relog that lands her exactly where she already is -- while
#     the logout buttons are still refused (UI-A/UI-B), that is the most
#     expensive no-op the console can recommend.
#
# EVERY SENTENCE ENDS ITS REASON IN THE SAME SIX WORDS, on purpose: an
# attended tester greps `no teleport could be sent` to find every staged
# shape at once, reads the clause in FRONT of it to learn which blocker to
# act on, and the clause BEHIND it to learn whether a relog would move her.
# No sentence claims a markerless spawn point is unusable -- only that
# nobody has confirmed one, which is the honest claim and the one this
# lane's letter `2005` made.
# THE THREE BLOCKERS, one sentence each.  Every one of them ends in the same
# six words (`no teleport could be sent`) so that ONE grep finds every staged
# shape at once; the clause in front of those six words is what an operator
# has to act on, and getting it wrong sends her to fix something that is not
# broken.
#
# ~~"an attended tester greps STAGED_NO_CONFIRMED_SPAWN_REASON to find every
# scene the markerless rule holds shut"~~ -- struck the moment there was more
# than one reason (pf-adversary, round `spt6fv`, D7): that constant now finds
# only ONE of the three.  The shared six words are the grep.
STAGED_NO_CONFIRMED_SPAWN_REASON = (
    "this scene has no confirmed spawn point, so no teleport could be sent"
)
# THE SECOND BLOCKER, and it is the one the FIRST DRAFT of this round got
# wrong in both directions (pf-adversary, round `spt6fv`, D1, MEASURED on the
# real dispatcher).
#
# That draft derived the reason from `warp_no_coords_live_target(scene)` --
# "does this destination have a pinned arrival marker" -- and printed the
# answer in the grammar of a different question: "why did THIS COMMAND send
# nothing".  Those two come apart the moment coordinates are typed.  With
# `WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED` down, `/warp 997 100 200` from
# scene 5 stages and printed "this scene has no confirmed spawn point" -- yet
# the control on the same input with the flag UP sends a real 73-byte
# TeleportVital, because a coordinates-bearing warp never needed the marker.
# The operator would have gone hunting a spawn point for 997, pinned one, and
# nothing would have changed: the flag was the blocker all along.
#
# So the marker question is asked ONLY of the shape it governs (the bare
# warp), and every coordinates-bearing stage names this reason instead.
STAGED_LIVE_ROUTE_SHUT_REASON = (
    "the live teleport route for this scene is shut, so no teleport"
    " could be sent"
)
# THE THIRD BLOCKER, which exists because the registry read can fail and a
# console must never guess (same finding, D3).  `_no_coords_live_target`
# swallows the failure so that no disk error can take an accepted command off
# the console, and this is what the line says when it does: not "there is no
# marker" (unknown) and not "the route is shut" (also unknown), but the one
# thing that IS known.
STAGED_SPAWN_UNREADABLE_REASON = (
    "this scene's spawn point could not be read, so no teleport"
    " could be sent"
)
# The three of them, in the order `_staged_blocker` returns them, so a reader
# can see at a glance that the shared six words really are shared.
STAGED_BLOCKER_REASONS = (
    STAGED_NO_CONFIRMED_SPAWN_REASON,
    STAGED_LIVE_ROUTE_SHUT_REASON,
    STAGED_SPAWN_UNREADABLE_REASON,
)
# The blocker names carried on `_Verdict`.  Names rather than the sentences
# themselves: the verdict is dispatch state, and a rewording must never have
# to touch the routing.
STAGED_BLOCKER_NO_SPAWN = "no_confirmed_spawn"
STAGED_BLOCKER_ROUTE_SHUT = "live_route_shut"
STAGED_BLOCKER_SPAWN_UNREADABLE = "spawn_unreadable"
_STAGED_BLOCKER_REASONS = {
    STAGED_BLOCKER_NO_SPAWN: STAGED_NO_CONFIRMED_SPAWN_REASON,
    STAGED_BLOCKER_ROUTE_SHUT: STAGED_LIVE_ROUTE_SHUT_REASON,
    STAGED_BLOCKER_SPAWN_UNREADABLE: STAGED_SPAWN_UNREADABLE_REASON,
}
# The tail for a stage that DOES change where the next login lands.  The
# relog fact survives the rewrite because it is the only useful thing this
# command did -- what changed is that it no longer arrives as a bare
# instruction with no reason in front of it.
#
# "IS STAGED TO START", not "will start" (pf-adversary, round `spt6fv`, D8).
# `runtime.py`'s login path can still refuse the override against the boot
# snapshot (`GM_LOGIN_SCENE_OVERRIDE_REFUSED ... source=boot_snapshot`) and
# put her back on her own stored row.  The struck sentence made the stronger
# promise too ("land there"), so this is not a regression being fixed -- it
# is a promise this round declined to repeat now that it is rewriting the
# words anyway.
STAGED_TAIL_CROSS_SCENE = (
    "the next login for this account is staged to start in it"
)
# The tail for a stage into the scene the GM is standing in.  It states the
# no-op rather than recommending it.
STAGED_TAIL_SAME_SCENE = (
    "you are standing in it already, so a relog would change nothing"
)


def _no_coords_live_target(
    session: object,
    scene_id: int,
    has_coordinates: bool,
) -> tuple[object | None, bool]:
    """`warp_no_coords_live_target`, asked once per command and never raising.

    Returns `(target, read_ok)`.  `read_ok` is False ONLY when the lookup
    itself failed; a scene that simply has no marker returns `(None, True)`,
    which is a different fact and a different console sentence.

    ASKED ONLY FOR THE BARE SHAPE.  A coordinates-bearing warp is not routed
    by this answer, so asking would be a disk read taken for a question
    nobody has -- and taking it was defect D3.

    FAIL-CLOSED, AND THE FAILURE IS SWALLOWED ON PURPOSE.  The caller uses
    this to decide whether to send a live teleport; an unreadable registry is
    not permission to send one, so `None` (stage instead) is the safe answer.
    Swallowing it is what keeps an accepted command on the console: this
    value feeds a console sentence as well as the routing, and the whole
    point of this module is that an accepted command that sent nothing says
    so.  The event name is kept so the failure is not silent to an operator
    reading `session.events`.
    """
    if has_coordinates:
        return None, True
    try:
        return warp_no_coords_live_target(scene_id), True
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}live_target_{type(error).__name__}")
        return None, False


def _staged_blocker(
    *,
    has_coordinates: bool,
    live_target: object | None,
    live_target_read: bool,
) -> str:
    """Which blocker actually held this command's frame.

    THE QUESTION THIS ANSWERS is "why did THIS COMMAND send nothing", not
    "what does this DESTINATION lack".  The first draft answered the second
    and printed it as the first; see `STAGED_LIVE_ROUTE_SHUT_REASON` for the
    measured input where they disagree.

    A COORDINATES-BEARING WARP IS NEVER BLOCKED BY A MISSING MARKER.  Its
    live branch (`_warp_teleport_action`) reads coordinates the GM typed and
    never consults `warp_no_coords_live_target` at all, so the only thing
    that can have sent it here is
    `WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED` being down.  (The same-scene
    coordinates shape does not reach staging at all -- it is refused above by
    the ForcePos gate.)

    FOR A BARE WARP both blockers can be true at once when the flag is down
    AND the scene is markerless.  The marker wins because it is the durable
    one: the flag is a kill switch that a decision can lift in an afternoon,
    while `GT-182` nonclaim 4 has held the markerless scenes shut since it
    was written, and it is the fact that would still be there tomorrow.
    """
    if not live_target_read:
        return STAGED_BLOCKER_SPAWN_UNREADABLE
    if has_coordinates:
        return STAGED_BLOCKER_ROUTE_SHUT
    if live_target is None:
        return STAGED_BLOCKER_NO_SPAWN
    return STAGED_BLOCKER_ROUTE_SHUT


def staged_next_step(*, same_scene: bool, blocker: str) -> str:
    """The `next=` sentence: one reason, one tail, joined here and nowhere else.

    SIX SENTENCES FROM FIVE CONSTANTS rather than six constants, because the
    two questions are independent -- WHY no frame went out, and whether a
    relog would move her -- and writing them out would be six strings to keep
    in agreement by hand, which `AGENTS.md` section 7 names as the thing to
    derive instead ("one fact, one place").

    An unknown blocker name renders the missing-spawn reason rather than
    raising: this builds a diagnostic, and a diagnostic may never alter
    dispatch.  It is the reason that is true of every line this printer emits
    on the shipped flags, so an impossible caller understates rather than
    invents.
    """
    reason = _STAGED_BLOCKER_REASONS.get(
        blocker, STAGED_NO_CONFIRMED_SPAWN_REASON
    )
    tail = STAGED_TAIL_SAME_SCENE if same_scene else STAGED_TAIL_CROSS_SCENE
    return f"{reason}; {tail}"

# And a SIXTH, asked for by name in `COO-DECISION 20260903_1845` item 2
# ("a new console token that says same-scene teleport sent"), serving
# `PANYA-DECISION 1800`.
#
# WHY IT IS NOT SILENCE, which is what every other SENT command gets.  A sent
# command normally says nothing here -- `route=action` plus the serve loop's
# own `[G>] <label>` line is its record, and `_announce_console_outcome`
# returns early on `sent` for exactly that reason.  This one shape is the
# case where that record is ambiguous to the person who typed it: the label
# it carries is `LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_TELEPORT_VITAL`,
# whose own comment promises an attended tester it means "the GM crossed
# scenes".  Since `PANYA-DECISION 1800` that same label also goes out for a
# warp that crosses nothing, and a console that cannot tell the two apart
# would make the label's promise false rather than merely incomplete.
#
# WHY IT IS NOT `STAGED_CONSOLE_TOKEN` WITH A NEW `next=` FIELD, the cheap
# version this round rejected: that token's whole meaning is "no bytes were
# sent and your NEXT login is what changed".  Both halves are now false for
# this shape, and the owner's own report of the bug is that she read the
# staged line as "nothing happened".  Reusing it would keep the sentence she
# misread and change only the words after it.  `GM_CHAT_STAGED_NEXT_LOGIN`
# must NOT appear for a marker-backed same-scene warp any more -- that is a
# pass criterion of the attended ticket, not a nicety, and the test named
# `test_the_staged_token_is_not_printed_for_a_same_scene_marker_warp` pins
# it against the mutant that keeps the old routing.
SAME_SCENE_TELEPORT_CONSOLE_TOKEN = "GM_CHAT_SAME_SCENE_TELEPORT_SENT"

# The `basis=` field on that line, and it is a correction, not decoration
# (pf-adversary, round `07kjfd`, D2, MEASURED on the real dispatcher).
#
# `_warp_action` decides "same scene" by comparing the typed scene id against
# `session.foundation.selected.position.scene_id`.  `runtime.py`'s
# `_gm_warp_resync_selected_scene` REWRITES that field to a cross-scene
# warp's DESTINATION at queue time, with nothing from the client confirming
# the arrival.  So a GM in scene 1 who types `/warp 5` and then, seeing
# nothing happen, types `/warp 5` again gets this token on the second one --
# and typing it again is exactly what the round exists to make work.
#
# The routing is still right (both shapes send the same frame to the same
# pinned spawn, so the retry does what she wants), but the WORD "same scene"
# is the server's belief about where she is, not a measured fact about where
# she is.  Naming the basis on the line is what this lane can honestly do
# from inside its own zone: the field that would fix it -- a last
# CLIENT-CONFIRMED scene, distinct from the label the server wrote for
# itself -- lives in `runtime.py`, which is chief's file.  Asked for in
# `CORE-REQUEST-GM-051` (letter `pf_bridge/notes_to_chief/20260903_2001_
# LANE-GM-CORE-REQUEST-CHIEF-051-052-*`), whose sibling `-052` covers the
# move-authority grace window this same change made reachable.
SAME_SCENE_BASIS_FIELD = "server_believed_scene"

# THE STRONGER OF THE TWO BASES, AND IT LANDED (chief, R328, letter
# `pf_bridge/notes_to_chief/20260903_2306_CHIEF-TO-LANE-GM-051-item3-the-
# client-never-names-a-scene.md`, answering `CORE-REQUEST-GM-051` item 3).
# Both docstrings above promised that "the day chief's
# `client_confirmed_scene` lands, both lines change basis together"; this
# constant and `same_scene_with_basis` below are that day.
#
# WHAT THE FIELD IS, IN CHIEF'S OWN CORRECTED WORDS, because this name is
# the most over-claimable thing this module prints.  It is NOT a scene the
# client named: a static sweep of every inbound frame this server decodes
# (chief R328, pf-static-re) found that NO client->server frame carries a
# scene or map id at all -- `StartGameReq` is one selector byte,
# `TargetPosVital` is x/y/z/heading, `ChooseNPC` is one identity qword, and
# the two near-misses (`ActionVital.field_u16_4a`,
# `TeleportCheckVital.field_u16_14`) are called opaque/unassigned by the
# parser itself.  It is NOT a label the client's COORDINATES corroborate
# either -- chief struck that wording himself; nothing compares a position
# against a scene's geometry, and a report at (1e9, -7.5e8, 3.3e8) still
# records scene 1.  What it IS: the scene label as of the last frame the
# CLIENT sent, in a moment we had no reason to disbelieve that label --
# `scene_label_at_last_trusted_client_report` is the honest long name.
#
# WHY IT IS STILL STRICTLY BETTER THAN THE OTHER BASIS for this one word.
# `server_believed_scene` reads `selected.position.scene_id`, which
# `_gm_warp_resync_selected_scene` REWRITES to a cross-scene warp's
# destination at queue time with nothing from the client involved -- so a GM
# in scene 1 who types `/warp 5` twice gets "you are standing in it already"
# on the second, which is what pf-adversary D2 measured and what this lane
# has been printing a basis label about ever since.  The new field is
# advanced ONLY by frames the client actually sent, and chief's permanent
# `scene_label_is_server_guess` flag keeps a missed warp from being adopted
# by the walking that follows it (his own first draft refused for exactly
# one frame; his `test_walking_after_a_missed_warp_never_adopts_the_
# destination` is what pins the fix).
#
# STILL A WIRE-LAYER FACT, NOT A SCREEN ONE (G5).  It outranks
# `selected.position.scene_id`, which can be pure server guess; it does not
# reach client-observable evidence, and no line printed from it may be read
# as "seen on screen".
CLIENT_CONFIRMED_SCENE_BASIS_FIELD = "client_confirmed_scene"


def same_scene_with_basis(session: object, target_scene_id, position) -> tuple:
    """Is the typed scene the one the GM is in -- and on whose word.

    Returns `(same_scene, basis)`.  The caller is `_warp_action`, once, and
    both halves travel on the `_Verdict` to whichever console printer runs;
    neither is ever re-derived at print time (see `staged_same_scene`).

    THE FIELD NAME IS A LITERAL, NOT AN IMPORT.  `runtime.py` exports it as
    `CLIENT_CONFIRMED_SCENE_FIELD` and chief pins the two spellings equal
    with a test on his side; importing `runtime` from a `gm/` module would
    close an import cycle (runtime imports this lane, never the other way),
    which is the case chief named when he offered the constant.
    `test_the_basis_field_name_matches_runtimes_own_constant` pins it from
    this side too, so a rename on either side fails loudly rather than
    silently falling back to the weaker basis forever.

    `None` IS THE SHIPPED FIRST ANSWER, NOT AN ERROR.  A connection that has
    logged in and not yet moved has never sent a frame this field is written
    from, so the honest value is "the client has told us nothing", and chief
    chose `None` for it deliberately over "the scene of the row at login" --
    logging in is not the client saying where it is.  On `None` this falls
    back to the old comparison AND says so in `basis=`, which is the whole
    reason the label is printed rather than assumed: a tester reading
    `basis=server_believed_scene` knows the word "same scene" is the
    server's belief, exactly as it was before this field existed.

    THERE ARE THREE STATES AND THIS RETURNS TWO WORDS, WHICH IS WHY THE
    STALE ONE IS REFUSED OUTRIGHT (pf-adversary, round `3qh50k`, D1,
    MEASURED with a control, and it is the reason this function is not the
    two-line version it was in this round's first draft).  A client can be
    confirmed-here, confirmed-elsewhere, or its last report can be KNOWN
    STALE -- and chief's own letter says the third state latches: from the
    moment `_gm_warp_resync_selected_scene` relabels the scene, his
    `scene_label_is_server_guess` is True and STAYS True for the rest of the
    session unless a warp's coordinates confirm.  Through that whole window
    `client_confirmed_scene` is frozen at wherever the client last spoke
    from, which is evidence of nothing about where she is standing now.

    The first draft spent it as evidence anyway, and the measurement is
    ugly: client really in scene 5 after an unconfirmed `/warp 5`, frozen
    field still 1, GM types `/warp 1` -- and the console printed
    `GM_CHAT_SAME_SCENE_TELEPORT_SENT ... basis=client_confirmed_scene`,
    an affirmative false claim stamped with the STRONGER word, where `main`
    had correctly printed nothing at all.  The mirror case
    (`/warp <destination>`) was the one chief's letter described and the one
    this round tested; the return warp is where the new basis is wrong.  It
    also let one STAGED line hold two contradictory premises at once (D3):
    "a relog would change nothing" printed by the branch that had just
    WRITTEN a next-login scene, because the two halves no longer came from
    one comparison.

    So a known-stale label is not upgraded, downgraded or hedged -- it is
    NOT USED.  On `scene_label_is_server_guess` this answers exactly what it
    answered before chief's field existed, and says `basis=
    server_believed_scene`, which is a true statement about a weak fact
    rather than a strong-sounding statement about a stale one.

    IT FALLS BACK ON ANYTHING IT CANNOT READ, never raises and never guesses.
    A session object without either attribute (every replay tool and most
    tests), a value that is not an int, an attribute whose property raises,
    a `position` whose `scene_id` cannot be read -- all land on the same
    conservative answer.  The reads are INSIDE the `try` (D4): the first
    draft left the `getattr` outside it, so a session whose attribute was a
    raising property escaped this function, in the one module whose founding
    property is that an accepted command never vanishes without a line.
    This runs on the dispatch path of an ACCEPTED command; a diagnostic may
    never alter dispatch, and `same_scene` picks a console sentence only.
    """
    try:
        target = int(target_scene_id)
    except Exception:  # noqa: BLE001 - see the paragraph above; nothing escapes
        return False, SAME_SCENE_BASIS_FIELD
    # TWO SEPARATE `try`s, NOT ONE, and the split is the fix's second half:
    # an unreadable CLIENT field must cost only the upgrade, never the
    # answer.  Folding both reads into one guard made a raising property on
    # chief's field collapse the whole function to "not same scene", which
    # silently deletes a console line that the pre-chief code printed
    # correctly -- trading one over-claim for one disappearance.
    try:
        if not getattr(session, "scene_label_is_server_guess", False):
            confirmed = getattr(session, "client_confirmed_scene", None)
            # `bool` is an `int` subclass and would compare equal to scene 1.
            if isinstance(confirmed, int) and not isinstance(confirmed, bool):
                return target == confirmed, CLIENT_CONFIRMED_SCENE_BASIS_FIELD
    except Exception:  # noqa: BLE001 - fall through to the pre-chief answer
        pass
    try:
        believed = int(getattr(position, "scene_id"))
    except Exception:  # noqa: BLE001 - no position, no comparison, no claim
        return False, SAME_SCENE_BASIS_FIELD
    return target == believed, SAME_SCENE_BASIS_FIELD

# The token that answers "did the sentence really leave the server?".
#
# pf-adversary (round `aa9ajr`) asked the one question this change had not
# answered: with `queued` deliberately not armed for a notice and the console
# saying `GM_CHAT_NO_BYTES_SENT`, "the GM saw nothing" and "the notice was
# composed, then dropped" looked identical in every artifact.  For `GT-193`
# step 9 that distinction IS the result, so it gets its own line, printed only
# when the notice is really being returned to the serve loop.  It sits BESIDE
# the no-bytes line rather than replacing it: both statements are true at once
# -- the COMMAND put nothing on the wire, and a sentence about that went out.
NOTICE_CONSOLE_TOKEN = "GM_CHAT_NOTICE_SENT"

# The line COO-DECISION 2026-09-02T18:47+07:00 asked for BY ITS EXACT FIRST
# TWO WORDS: "the `route=action` path must refuse and print one pure-ASCII
# line: `SPEED DEFERRED` (a short reason may follow, but the prefix must be
# those two words)".  Spelled as one constant so a test can pin the prefix
# and an attended tester can grep for it without knowing this module.
#
# A THIRD TOKEN RATHER THAN A REUSE OF `WITHHELD_CONSOLE_TOKEN`, and the
# reason is the decision itself: an attended round that types `/speed` needs
# to tell "this lane is holding every frame on purpose, project-wide, until
# LANE-DB lands the login read" apart from "your value/session/DB was
# refused by one of the eight gates above".  Both print no bytes; only one of
# them is a state the tester can do nothing about.  Grepping `GM_CHAT_NO_
# BYTES_SENT` and reading `why=` would answer it too, and that is exactly the
# indirection COO's "print these two words" removes.
#
# ASCII BY CONSTRUCTION (a space, no punctuation): the bridge console is
# cp874 and this line is read there.
SPEED_DEFERRED_CONSOLE_TOKEN = "SPEED DEFERRED"

# `/lv`'s own console token, ONE word so an attended run can grep it without
# quoting a space, and separate from every token above because the line it
# leads reports a DURABLE effect (a row) rather than a frame.  The tester
# grading the `/lv` ticket greps this and reads the level the store handed
# back, which is the number the next login will send -- not the number the GM
# typed.  ASCII by construction: the bridge console is cp874.
LV_CONSOLE_TOKEN = "GM_LV"

# The trial gate's own console token -- COO `0646` item 2, fourth bullet: the
# person watching the screen must be able to read WHICH value the door was
# opened for without opening a source file.  A separate token rather than a
# field on `SPEED DEFERRED`, because the two lines report opposite outcomes
# (nothing left the process / this one frame did) and an attended tester
# greps for one word, not for a word plus a field value.
#
# ASCII, spaces only between words, for the reason the token above is: the
# bridge console is cp874.
SPEED_TRIAL_CONSOLE_TOKEN = "SPEED TRIAL OPEN"
# What the console says when this process could not ASK the trial gate at
# all.  Deliberately a third word beside `speed_wire.TRIAL_UNSET` and
# `TRIAL_MALFORMED`: "nothing is armed" and "the gate did not answer" are
# different facts, and a line that merged them would tell an operator the
# door is shut on evidence it does not have.
SPEED_TRIAL_UNAVAILABLE = "unavailable"

# `SPEED_TRIAL_CONSOLE_TOKEN` above is DEAD CODE since `COO-DECISION
# 20260904_0345` item 2 (pf-adversary, round `tof9cw`, measured; recorded in
# `pf_bridge#1067`): `speed_wire.compose_sparse_speed_update` now raises
# `SpeedWireError` UNCONDITIONALLY, so `_speed_action`'s `try: pc, frame =
# speed_wire.compose_sparse_speed_update(...)` always lands in the `except`
# branch before the `if trial_admitted:` block below it is ever reached --
# `SPEED TRIAL OPEN` cannot print on any route that exists on `main` today.
# That silently erased the one guarantee COO `0646` item 2's fourth bullet
# asked for: an owner who arms `PF_SPEED_TRIAL` must be able to tell, from
# the console alone, that the key was RECOGNISED even though the value never
# shipped -- otherwise a grep for `trial_opens_for=` reads identically
# whether the key was never set or was set and still refused.  This token is
# that line's replacement: printed from the COMPOSE-REFUSED branch instead
# of the send branch, so it can never claim bytes went out.
#
# ASCII, spaces only, for the reason every console token in this lane is.
SPEED_TRIAL_ARMED_REFUSED_CONSOLE_TOKEN = "SPEED TRIAL ARMED REFUSED"

# The three fillers for the row fields `_print_speed_deferred` appends after
# `why=`.  Spelled as constants so a test and an attended grep name the same
# strings, and kept ASCII and space-free for the reason the token above is.
#
# `unknown` is NOT `0` and NOT an empty field: this route runs below a DB
# write, so "the console could not say what the row holds" and "the row holds
# nothing" are different facts and the owner's standing rule is that a guessed
# zero is banned (`COO-DECISION 20260901_1059`, quoted in `login_speed.py`).
SPEED_DEFERRED_ROW_UNKNOWN = "unknown"
# The row was never handed to the printer at all -- a caller that has no
# read-back to report, which on the shipped route cannot happen (the branch
# runs below `EVENT_SPEED_PERSIST_READBACK_UNUSABLE`) and is therefore its own
# word rather than being folded into a resolver failure.
SPEED_DEFERRED_NEXT_LOGIN_NOT_EVALUATED = "not_evaluated"
# `login_speed.resolve` itself could not answer.  Type name only, the same
# rule every refusal in this module follows: an exception message can carry
# text this lane did not write.
SPEED_DEFERRED_NEXT_LOGIN_UNRESOLVED_PREFIX = "unresolved_"

# What each no-bytes outcome is waiting on, as fixed sentences this lane
# wrote -- never a string built from anything a client typed.  Keyed on the
# audit outcome so the ndjson word and the console line cannot drift apart:
# one decision, spelled once, read twice.
#
# NOT EXHAUSTIVE, ON PURPOSE -- BUT NARROWER THAN THE FIRST DRAFT THOUGHT.
# `refused_warp_<ExcType>` and `refused_stage_<ExcType>` name a type, not a
# blocker, and inventing a sentence for a family whose members do not exist
# yet is how a console line starts lying.  Those print `NO_BLOCKER_RECORDED`
# -- the operator still learns the two facts this token exists for: nothing
# was sent, and which word the audit file carries.
#
# !! WHAT THAT PARAGRAPH GOT WRONG (pf-adversary D4, measured): five of the
# `refused_stage_*` outcomes are NOT an `<ExcType>` family.  They are the
# named constants in `login_scene_stage.NOT_DESTINATION_SHAPED_REASONS`,
# every one of them a server-side fault with a knowable remedy -- and one of
# them, `config_not_writable`, has a one-command fix.  They were printing
# `no blocker recorded` on the very boot where the operator most needs the
# sentence.  They are in the table below now, and the contract test derives
# the list FROM that module instead of hand-copying it, so a sixth reason
# added upstream turns a test red rather than inheriting a shrug.
NO_BLOCKER_RECORDED = "no blocker recorded"

# Why nothing went out when the command itself was fine and the AUDIT was
# not.  Not an audit outcome -- that row is precisely what could not be
# written -- so it is spelled here and never passed to `log_gm_command_
# outcome`.  `_make_action`'s own comment explains the withholding; this is
# the console's half of it.
#
# !! IT COVERS THE NO-ACTION COMMANDS TOO, and the first version of this
# round did not (pf-adversary D1/D2, both measured).  That version printed
# the line BEFORE the audit write and keyed it on `verdict.audit_outcome`,
# so on an unwritable capture directory a `/warp 2 100 200` said
# `why=withheld_force_pos_vital_version` while the ndjson carried no outcome
# row at all -- the console naming a word the audit file does not have, on
# the one boot where the operator is grepping both.  The branch that DID say
# `audit_row_not_written` sat behind `action is not None`, which cannot
# happen at HEAD because both version gates are shut: the reachable case
# printed the wrong word and the right word sat in unreachable code.
# One call site now, after the audit, for every shape.
WHY_AUDIT_ROW_NOT_WRITTEN = "audit_row_not_written"
# THE SAME AUDIT FAILURE, WITH THE DURABLE EFFECT STILL IN PLACE.  Measured
# by pf-adversary (round `c637o1`, D4): a first-ever `/speed` on a character
# whose `speed_walk` was NULL commits 400.0, then loses the audit write, then
# runs `_speed_undo` -- which has nothing to restore, reports False, and
# leaves the row AT 400.0.  With one word for both states the console printed
# `blocked_on='...anything it had in hand was dropped with it'` while the row
# it had just named (`character_id=`) held the new value.  Naming a row and
# lying about it in the same line is worse than the silence this round set
# out to fix, and it is the exact property `COO-DECISION 0147` cites
# (its founding principle: the screen may not lie about the real state).
# The revert-succeeded case keeps the original word
# and the original sentence; only the not-reverted case gets this one.
WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT = "audit_row_not_written_effect_kept"

# Width bound for the hint half of a console line, held at the PRINTER.
# TWO suppliers now (pf-adversary D11 -- this comment said "the one supplier"
# one commit after the second arrived): `commands.usage_hint_for`'s seven
# fixed sentences, and `NO_BYTES_BLOCKERS` below.  Both are short, so the cap
# has never fired on a real value -- which is exactly why it is here and why
# a test drives a long sentence through it: the bound belongs to the line,
# not to whichever table happened to fill it in this time.
MAX_CONSOLE_HINT_LENGTH = 240

# A console line this module MEANT to write and could not.  Named rather than
# swallowed (pf-adversary D5): `CONSOLE_TOKEN`'s own comment says the token
# exists because a wired call site and a call site chief never wrote produce
# identical console output -- and after this round a BROKEN CONSOLE produced
# identical output too, with nothing in the event trail to separate the
# three.  An attended `GT-127` run greps for `LANE_GM_CHAT_ACTION`, finds
# nothing and concludes the route is dead: a false negative manufactured by
# the fix.  `_note` cannot raise, so naming this costs nothing the swallow
# was protecting.
EVENT_CONSOLE_WRITE_FAILED_PREFIX = "gm_chat_action_console_write_failed_"

# Every event this route emits is namespaced `gm_chat_action_`, and the live
# hook route keeps the `gm_chat_command_` names it has always had.  The
# direction of that rename is the whole point and is not a style choice:
# chief's `tests/test_gm_chat_command_dispatch_wiring.py` on main pins
# `gm_chat_command_accepted_warp` and `gm_chat_command_refused_*` as literals
# against the LIVE hook, and GT-127's headless drill greps the console for
# them.  Renaming the live route to disambiguate would have broken both --
# which is exactly what round `gr2q9j` tried to do and why the fix belongs on
# the dormant side.
#
# What the two namespaces buy, if a future commit ever wires both call sites
# at once: pf-adversary measured that with shared names one typed
# `/warp 2 100 200` produced two byte-identical ndjson rows at the same
# second-granularity timestamp -- indistinguishable from a GM typing the same
# command twice -- and two identical event lines, while silently charging the
# rate limit twice and halving the GM's real command budget.  Distinct
# prefixes cannot PREVENT a double-wire; they make one legible the first time
# anyone reads the event trail, instead of looking like normal operation.
EVENT_ACCEPTED_PREFIX = "gm_chat_action_accepted_"
EVENT_REFUSED_PREFIX = "gm_chat_action_refused_"
EVENT_NO_WIRE_PATH_PREFIX = "gm_chat_action_no_wire_path_"

# CORE-REQUEST-GM-041's read point (`gm_npc_toggle_recompose.
# npc_toggle_would_recompose`) answers a question chief built specifically
# for this lane to ask from the `no_wire_path` branch below: would toggling
# THIS mob_id change what the next recompose sends, today.  This is a
# diagnostic event on top of `EVENT_NO_WIRE_PATH_PREFIX`, never a
# replacement for it and never a change to `verdict` -- `npc` still composes
# no action (see the module's own no-wire-path comment table).  Answer is
# always `false` at HEAD (letter 20260830_1909: no on/off state store exists
# yet for a recompose call site to read), and this event is what turns that
# from a claim in a letter into something `GT-127`'s console grep can see on
# every `/npc` line without opening a file.
EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX = "gm_chat_action_npc_recompose_diagnostic_"

# GM-042 prep's read point (`gm.item_catalog`, committed round `opr2xd`)
# answers the same shape of question for `item` that
# `EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX` answers for `npc`: is the id the
# GM typed even a real item, today -- BEFORE this lane has any grant call
# site to wire (letter 20260830_1924: no CORE-REQUEST opened yet, no
# "give it to the runtime.py backpack" path exists the way
# `mob_scene_recompose` exists for `npc`).  A diagnostic on top of
# `EVENT_NO_WIRE_PATH_PREFIX`, never a replacement for it and never a
# change to `verdict` -- `item` still composes no action either way, the
# same rule `_note_npc_recompose_diagnostic`'s own docstring states.
#
# Three answers, not two, because `item_catalog.item_category()` can name
# zero, one, or MORE than one category for the same numeric id (the
# module's own docstring: 230 ids collide between misc/consumable alone).
# An id that is ambiguous today would silently grant the wrong item's
# stack size the day a grant call site lands if this lane's future
# `item <id> <n>` wiring picked one category at random -- naming the
# ambiguity now, while it is still parse+log, is what round `opr2xd`
# asked "chief/Panya เป็นคนตัดสิน" about; this event is the measurement
# that question is asked from, not a decision this lane made for them.
EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX = "gm_chat_action_item_catalog_diagnostic_"
EVENT_BAD_SESSION_PREFIX = "gm_chat_action_bad_session_"
EVENT_BAD_PAYLOAD_PREFIX = "gm_chat_action_bad_payload_"
# CHAT-TAIL-001.  One event per frame whose payload was NOT a bare chat body
# -- either because the tail walked (the command still runs, on the isolated
# body) or because it did not (the command is refused exactly as it is on
# main today).  `no_tail` -- every frame ever captured -- writes nothing.
EVENT_CHAT_TAIL_PREFIX = "gm_chat_action_chat_tail_"
# The per-connection latch that keeps the console line above bounded.  Held
# on the session, not on the module, so two connections do not silence each
# other and a reconnect reports again.
SESSION_CHAT_TAIL_REPORTED = "_gm_chat_tail_reported"
EVENT_WARP_WITHHELD_NO_VERSION = (
    "gm_chat_action_warp_withheld_no_confirmed_force_pos_vital_version_re129_open"
)
EVENT_WARP_NO_POSITION = "gm_chat_action_warp_no_current_position"
# COO-DECISION `20260903_1744` item 3: the same-scene ForcePos shape is shut
# by POLICY after R306 measured it closing the client (`ErrorData=28317`).
# Its own event name, not a reuse of `EVENT_WARP_WITHHELD_NO_VERSION`: a
# replay tool reading the trail must be able to tell "RE-129's byte is
# missing" (answered, and open again would be news) from "the shape this
# byte sits in killed a client and COO shut the route".
EVENT_WARP_WITHHELD_FORCE_POS_CLOSED = (
    "gm_chat_action_warp_withheld_same_scene_force_pos_closed_r306"
)
# COO-DECISION `20260904_2045` item 1: EVERY typed-coordinate `/warp` shape
# is shut, at ONE point, above every branch.  Its own event name for the same
# reason the line above has one -- an attended tester greps a console line to
# find out WHICH closure held a command, and "the same-scene ForcePos frame
# shape" and "coordinates, in any shape" are two different answers that would
# send them to two different tickets.
EVENT_WARP_WITHHELD_TYPED_COORDS_CLOSED = (
    "gm_chat_action_warp_withheld_typed_coordinates_closed_coo_2045"
)
# The warp went out but its destination could not be parked for the position
# reader (a session that refuses attributes).  NOT a refusal -- the frame is
# real -- so it is deliberately outside `EVENT_WARP_REFUSED_PREFIX`, whose
# contract is "exception type names only" and whose consumers read it as
# "nothing was sent".
EVENT_WARP_TARGET_NOT_RECORDED = "gm_chat_action_warp_target_not_recorded"
# `PANYA-DECISION 20260904_1430` / `COO-DECISION 20260904_1452`: the durable
# scene write a live warp now makes for itself, instead of waiting for the
# player's next step.  The suffix is `warp_scene_persist`'s own outcome word,
# INCLUDING the success one -- unlike `EVENT_WARP_TARGET_NOT_RECORDED` above,
# which stays silent on success because nothing observable happened.  Here
# something did: a row moved, and a headless test asserting `1430` needs a
# line to assert on that does not depend on capturing stderr.
EVENT_WARP_SCENE_PERSIST_PREFIX = "gm_chat_action_warp_scene_persist_"

# The undo's own trail, kept SEPARATE from the forward write's prefix above
# so a reader of `session.events` can never mistake "the row went back" for
# "the row was written" -- the two lines would otherwise differ only by a
# word buried at the end of a long name (pf-adversary round `741zlx`,
# finding 1: the whole defect was two states that looked alike).
EVENT_WARP_SCENE_ROLLBACK_PREFIX = "gm_chat_action_warp_scene_rollback_"
# `CORE-REQUEST-GM-057`'s own park (`gm/warp_send_watch.py`): the persisted
# row's frame could not be recorded as owed a send (a session that refuses
# attributes).  Same "not a refusal, the frame is real" reasoning as
# `EVENT_WARP_TARGET_NOT_RECORDED` above, and deliberately silent on
# success for the identical reason chief's own confirmation-token appendix
# gave for that sibling: a park succeeding is not itself an observable
# event, only its later confirm/rollback is.
EVENT_WARP_SEND_WATCH_NOT_PARKED = "gm_chat_action_warp_send_watch_not_parked"
# The withheld warp's OWN park could not be dropped once `verdict.undo` had
# already reverted the row synchronously (a session that swallows the
# write).  Named separately from `EVENT_OUTCOME_STALE_TARGET_NOT_CLEARED`:
# that one is chief's position-confirmation record, this one is the
# send-failure safety net, and pf-adversary has already found this lane
# folding two different "could not clear" facts into one word once
# (`OUTCOME_ROW_NOT_TOUCHED`, `warp_scene_persist.py`'s own comment).
EVENT_WARP_SEND_WATCH_STALE_PARK_NOT_CLEARED = (
    "gm_chat_action_warp_send_watch_stale_park_not_cleared"
)
# `COO-DECISION 20260905_1746` item 4: the relog half of a LIVE warp whose
# durable row was refused by login policy.  The suffix is
# `warp_relog_stage`'s own outcome word, including the "this is not that
# route" one -- unlike the parks above this line is written on EVERY
# non-persisted live warp, because the question a reader of `session.events`
# is asking here is "did anything arrange my next login", and the answer
# "no, and here is which no" is exactly as load-bearing as the yes.  Kept
# out of `EVENT_WARP_SCENE_PERSIST_PREFIX`'s vocabulary on purpose: that
# prefix answers what happened to the ROW, this one what happened to the
# next LOGIN, and they now disagree by design for scene 126.
EVENT_WARP_RELOG_STAGE_PREFIX = "gm_chat_action_warp_relog_stage_"
EVENT_WARP_REFUSED_PREFIX = "gm_chat_action_warp_refused_"
# The cross-scene half of `/warp` (gm/login_scene_stage.py).  The suffix is
# the scene_id that was staged, so an attended run can grep one line and read
# both that it happened and where to -- and so it cannot be confused with the
# same-scene path, which never gets this far while the version gate is shut.
# NOT under `EVENT_WARP_REFUSED_PREFIX` and not under the accepted prefix
# either: a staged scene is neither "nothing happened" nor "a frame went
# out", and this lane has been bitten before by folding a third state into
# one of two existing names.
EVENT_WARP_STAGED_PREFIX = "gm_chat_action_warp_staged_login_scene_"
# The stage itself was refused; the suffix is `login_scene_stage`'s own
# REASON_* value or an exception TYPE name.  Separate from
# `EVENT_WARP_REFUSED_PREFIX`, whose contract is exception type names only.
EVENT_WARP_STAGE_REFUSED_PREFIX = "gm_chat_action_warp_stage_refused_"
EVENT_UNEXPECTED_PREFIX = "gm_chat_action_unexpected_"
EVENT_SAY_WITHHELD_NO_VERSION = (
    "gm_chat_action_say_withheld_no_confirmed_gm_global_vital_version_re132_open"
)
# Not the same refusal as the one above, and the difference is the whole
# point: this one fires only AFTER RE-132 answered, when the answer is a byte
# `channel_message_hypothesis.py` cannot emit.  Reading them as one event
# would let release day look like "still waiting for RE" forever.
# !! DELIBERATELY NOT UNDER `EVENT_SAY_REFUSED_PREFIX`.  pf-adversary (this
# round) measured that the first spelling of this name --
# `gm_chat_action_say_refused_confirmed_version_is_not_the_codec_version` --
# started with that prefix, whose own contract is "exception TYPE names only".
# A consumer stripping the prefix to recover a class name would have got a
# sentence, and the round's own over-length test already read the two as one
# family.  `EVENT_WARP_WITHHELD_NO_VERSION` has no such collision with the
# warp prefix; this one now has none either.
EVENT_SAY_VERSION_CODEC_MISMATCH = "gm_chat_action_say_version_codec_mismatch"
EVENT_SAY_REFUSED_PREFIX = "gm_chat_action_say_refused_"

# CORE-REQUEST-GM-049's `/speed <value>`.  Same naming convention as the
# `say` events immediately above -- `withheld` for the version gate,
# `refused_<ExcType>` for a composer failure -- and one more of this
# command's own: `no_selected_character`, for the read `_speed_action` needs
# that `say` never did (`identity_lo`/`identity_hi` off the connection's own
# selected character; `say` reads no character at all).
EVENT_SPEED_WITHHELD_NO_VERSION = (
    "gm_chat_action_speed_withheld_no_confirmed_update_attr_vital_version"
)
# The run-copy-DB gate (`_speed_db_is_canonical`), fired BEFORE the identity
# read and the version-gate read above -- see `_speed_action`'s own
# docstring for what this filename heuristic does and does not prove.
EVENT_SPEED_WITHHELD_CANONICAL_DB = "gm_chat_action_speed_withheld_canonical_db"
# The event trail's half of `SPEED_DEFERRED_CONSOLE_TOKEN` above.  Its own
# name, not a reuse of the shape-hold event beneath it, for the reason the
# console token is its own: a replay tool reading `session.events` must be
# able to separate the project-wide deferral from the shape question.
EVENT_SPEED_DEFERRED = "gm_chat_action_speed_deferred_login_read"
# COO `0646` item 2's runtime trial gate let this ONE value through both
# holds.  Its own event, never a reuse of `EVENT_SPEED_DEFERRED`, because the
# two say opposite things about the same command: a replay tool must be able
# to answer "did any `/speed` frame leave this process, and under whose
# authority" from `session.events` alone, without reading an environment it
# was not running in.  See `speed_wire.trial_admits`.
EVENT_SPEED_TRIAL_ADMITTED = "gm_chat_action_speed_runtime_trial_admitted"
# Fires ALONGSIDE `EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX` below, never
# instead of it, when the trial gate admitted this value and the compose
# wall refused it anyway -- see `SPEED_TRIAL_ARMED_REFUSED_CONSOLE_TOKEN`'s
# own comment for why this pairing exists now that `EVENT_SPEED_TRIAL_
# ADMITTED` above can no longer reach the send branch that used to note it.
EVENT_SPEED_TRIAL_ADMITTED_BUT_REFUSED = (
    "gm_chat_action_speed_trial_admitted_but_refused"
)
EVENT_SPEED_NO_SELECTED_CHARACTER = "gm_chat_action_speed_no_selected_character"
EVENT_SPEED_REFUSED_PREFIX = "gm_chat_action_speed_refused_"
# GT-193 [FAIL] (attended R303, 2026-09-02): this door's frame went to a real
# client, and immediately afterwards the character showed HP 0 and money 0 and
# died, and 426 inbound frames carried ZERO non-heartbeat (the client locked
# itself out and the round lost it until a re-login).  WHICH BYTE DID THAT IS
# NOT KNOWN -- the tester's own nonclaim -- so the hold is keyed on the SHAPE
# being uncleared, not on a cause: see `speed_wire.shape_cleared` and the
# block comment above `SHAPES_CLEARED_BY_A_REAL_CLIENT`.  `withheld`, not
# `refused`: nothing about the GM's line was wrong, this lane is holding its
# own frame.
EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED = (
    "gm_chat_action_speed_withheld_sparse_shape_not_cleared_by_a_real_client"
)
# The on-screen notice for a refused `/speed` (COO-DECISION `0345`).  Two
# events, because "the sentence went out" and "the sentence could not even be
# built" are different facts and a refusal that silently loses its notice is
# exactly the silence that decision exists to end.  The compose failure is
# NAMED BY EXCEPTION TYPE ONLY, same discipline as every other refusal here.
EVENT_SPEED_DENIED_NOTICE_COMPOSED = "gm_chat_action_speed_denied_notice_composed"
EVENT_SPEED_DENIED_NOTICE_FAILED_PREFIX = (
    "gm_chat_action_speed_denied_notice_failed_"
)

# The on-screen notice for a MISTYPED command (COO-DECISION `0647`).  Two
# events for the same reason the pair above has two, and named after the LAYER
# (`typo`) rather than after a command, because this one fires for every
# command name and for a verb this lane does not have at all.
#
# THE SECOND NAME IS NOT DECORATION.  This route composes and returns in one
# step -- there is no audit row between the two, because a command refused by
# the grammar was never logged (`chat_command.handle_local_talk_chat` returns
# the parse refusal ABOVE its `log_gm_command` call) -- so unlike the
# `/speed` notice, `..._composed` here really does mean "the bytes were
# handed back to the serve loop".  A composer failure is therefore the ONLY
# way the screen stays silent on this path, and it says so by name.
EVENT_TYPO_REFUSED_NOTICE_COMPOSED = "gm_chat_action_typo_refused_notice_composed"
EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX = (
    "gm_chat_action_typo_refused_notice_failed_"
)

# The PERSISTENCE half of `/speed`, added the round LANE-DB's
# `store.write_typed_attributes_and_compose_sparse` was measured live on
# `main` (their letter `pf_bridge/notes_to_chief/20260901_2213_LANE-DB-TO-
# LANE-GM-speed-sparse-live-on-main-but-speed-does-not-persist.md`, which
# also stated the gap this closes: before this round `/speed` composed a
# frame and wrote no row, so a value "applied" on screen was forgotten by
# the next login).
#
# DB FIRST, WIRE SECOND -- and that ordering is [ASSUMPTION OF LANE-GM,
# AWAITING COO] per `pf_bridge/notes_to_chief/20260902_0017_LANE-GM-ASK-COO-
# speed-db-first-ordering-change.md`.  Every name below is therefore a
# NO-FRAME outcome: a value the database would not take must never be
# painted on a client, because a screen that disagrees with the row is the
# one failure mode this lane may not ship.
EVENT_SPEED_NO_STORE = "gm_chat_action_speed_no_store"
EVENT_SPEED_NO_CHARACTER_ID = "gm_chat_action_speed_no_character_id"

# `/lv`'s event trail.  Every one of them is a NAMED refusal or a named
# success; `/lv` has no silent branch, because the whole point of the command
# is that a tester can tell "the level did not change" from "the level
# changed and this client has not been told yet" -- and those two look
# identical on the screen until the relog.
EVENT_LV_REFUSED_PREFIX = "gm_chat_action_lv_refused_"
EVENT_LV_WITHHELD_CANONICAL_DB = "gm_chat_action_lv_withheld_canonical_db"
EVENT_LV_ROW_WRITTEN = "gm_chat_action_lv_row_written"
EVENT_LV_NOTICE_COMPOSED_PREFIX = "gm_chat_action_lv_notice_composed_"
EVENT_LV_NOTICE_FAILED_PREFIX = "gm_chat_action_lv_notice_failed_"
EVENT_SPEED_PERSIST_REFUSED_PREFIX = "gm_chat_action_speed_persist_refused_"
# THE STORE DOOR REFUSED AND THE ROW IS UNTOUCHED.  Its own name, deliberately
# NOT a suffix under the prefix above: that prefix's console sentence says "do
# NOT read this as 'nothing was stored'", which is the exact OPPOSITE of what
# `store.write_speed_by_identity` returning `None` guarantees -- every refusal
# inside that door raises within its transaction, so the row is rolled back
# before it returns.  One word may not mean both durable states, for the same
# reason `EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX` below has its own.
EVENT_SPEED_ROW_NOT_TOUCHED = "gm_chat_action_speed_row_not_touched"
# The read-back the store handed us was not a number this module can encode.
# Distinct from the prefix above on purpose: nothing raised, the write
# COMMITTED, and only the composed view of it is unusable.
EVENT_SPEED_PERSIST_READBACK_UNUSABLE = (
    "gm_chat_action_speed_persist_readback_unusable"
)
# THE WRITE COMMITTED AND THE COMPOSER THEN FAILED.  Its own name, not the
# pre-write `EVENT_SPEED_REFUSED_PREFIX` one -- pf-adversary (round `hw6dix`,
# D2) measured that reusing that prefix made one word mean two OPPOSITE
# durable states: a parse refusal (nothing stored) and a post-commit compose
# refusal (row at the new value, no client told).  An attended tester grading
# GT-193 step 6 reads the audit trail to decide what the row should say, so
# the two may not share a word.
EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX = (
    "gm_chat_action_speed_persist_compose_refused_"
)

# CORE-REQUEST-GM-043's `/gmprobe <variant_id>`.  No withheld-by-version-gate
# event exists for this command -- see `_gmprobe_action`'s own docstring for
# why: `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` was pinned outright by
# RE-105, it was never a `None`-until-proven gate the way `warp`/`say`'s
# constants are.
#
# The typed token itself is NEVER embedded in either name below (unlike
# `EVENT_WARP_STAGED_PREFIX` + an int scene_id) -- `variant_id` is arbitrary
# GM-typed text, the same class of value `usage_hint_for`'s own docstring
# refuses to echo, and a fixed literal is exactly what the "unknown variant"
# case needs since there is nothing about a real variant id worth reporting.
EVENT_GMPROBE_UNKNOWN_VARIANT = "gm_chat_action_gmprobe_unknown_variant"
# The suffix is an exception TYPE name, same contract as
# `EVENT_WARP_REFUSED_PREFIX`/`EVENT_SAY_REFUSED_PREFIX` -- never a message,
# which could embed the GM's typed text.
EVENT_GMPROBE_REFUSED_PREFIX = "gm_chat_action_gmprobe_refused_"
# The `outcome` audit row could not be appended (CORE-REQUEST-GM-032).  Two
# names, because the two failures need different reading: the log write
# failed for a reason the OS named, or the issued row handed back no id to
# close.  The third name is what it COST -- a composed frame thrown away
# rather than sent with a broken audit trail behind it.
EVENT_OUTCOME_LOG_FAILED_PREFIX = "gm_chat_action_outcome_log_failed_"
EVENT_OUTCOME_NO_RECORD_ID = "gm_chat_action_outcome_no_record_id"
EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD = (
    "gm_chat_action_outcome_not_audited_action_withheld"
)
# The same branch, for a REFUSAL NOTICE rather than a command frame, and it
# needs its own name for two reasons pf-adversary (round `aa9ajr`, D4)
# measured: `..._action_withheld` is documented and asserted elsewhere as "a
# composed COMMAND frame was withheld", and without a second name the boot
# where the audit log cannot be written -- the boot where a human most needs
# to be told something -- goes silent on screen again with nothing in the
# trail saying the sentence was dropped rather than never built.
EVENT_OUTCOME_NOT_AUDITED_NOTICE_DROPPED = (
    "gm_chat_action_outcome_not_audited_notice_dropped"
)
# The withheld warp's parked destination could not be dropped (a session that
# swallows the write).  Named because the alternative is chief's position
# token comparing a later step against a warp nobody sent.
# The staged login-scene entry could not be taken back off disk after its
# outcome row failed to append.  This is the one state where an effect
# outlives the audit that should have described it, so it gets its own name
# rather than sharing the target-not-cleared one: an operator who sees it has
# a config entry to check by hand.
EVENT_OUTCOME_STAGE_NOT_REVERTED = "gm_chat_action_outcome_stage_not_reverted"
# The undo SUCCEEDED, so the `..._warp_staged_login_scene_<id>` line further
# up the same event list is now describing a config entry that no longer
# exists.  pf-adversary: an event trail that only ever adds "it happened"
# lines reads as if it did, and the audit row that would have corrected it is
# the one that could not be written.  Retract it explicitly.
EVENT_OUTCOME_STAGE_REVERTED = "gm_chat_action_outcome_stage_reverted"
EVENT_OUTCOME_STALE_TARGET_NOT_CLEARED = (
    "gm_chat_action_outcome_stale_warp_target_not_cleared"
)

# CORE-REQUEST-GM-040, this lane's half.  Four names, because four different
# things can go wrong on the road between "we handed an action back" and
# "the ndjson says it was appended", and a single name would let a reader
# conclude the wrong one.
#
# ..._not_armed_<ExcType>: the pairing could not be stored on the session at
# all (a session object that refuses the attribute).  The command still
# goes out; only its `queued` row is lost, and this says so rather than
# leaving a silent gap that reads like "the frame was never appended".
EVENT_QUEUED_CONFIRM_NOT_ARMED_PREFIX = "gm_chat_action_queued_confirm_not_armed_"
# ..._overwrote_pending: we armed while a pairing from an EARLIER frame was
# still sitting on the session unfired.  By construction that earlier action
# was composed and then never appended, which should not happen on any route
# this module has today -- so it is an anomaly worth a name, not a routine
# event.  We overwrite deliberately (the stale pairing can never fire again
# anyway: chief's check is `is`, and that object is not coming back), but a
# reader has to be able to see that a command's `queued` row went missing
# for this reason and not because the append failed.
EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING = (
    "gm_chat_action_queued_confirm_overwrote_pending"
)
# ..._write_failed_<ExcType>: the append really happened, chief's hook really
# fired us, and the `queued` row still could not be appended (a full disk, a
# permission change mid-run).  NOTHING IS WITHHELD HERE, and that asymmetry
# with `_log_outcome` is deliberate: by the time this runs the action is
# already in runtime.py's action list, so there is nothing left to take
# back.  The honest report is "it went out and we failed to record that",
# which is what this event says.
EVENT_QUEUED_CONFIRM_WRITE_FAILED_PREFIX = (
    "gm_chat_action_queued_confirm_write_failed_"
)
# ..._fired_twice: the callback was invoked a second time for the same
# command.  Chief's hook clears the pairing before it calls, so this cannot
# come from that path; it would mean some OTHER caller got hold of the
# callback.  Refused rather than written, because two `queued` rows for one
# record_id would read like two appends.
EVENT_QUEUED_CONFIRM_FIRED_TWICE = "gm_chat_action_queued_confirm_fired_twice"

# Audit outcomes this route can write, spelled once here so the ndjson value
# and the console event stay one decision.  The gate names are the ones the
# RE tickets use, so a reader of the audit file can go straight to the open
# question: `withheld_force_pos_vital_version` is RE-129,
# `withheld_gm_global_message_vital_version` is RE-132.
OUTCOME_WARP_WITHHELD_NO_VERSION = (
    f"{OUTCOME_WITHHELD_PREFIX}force_pos_vital_version"
)
OUTCOME_SAY_WITHHELD_NO_VERSION = (
    f"{OUTCOME_WITHHELD_PREFIX}gm_global_message_vital_version"
)
OUTCOME_WARP_NO_POSITION = f"{OUTCOME_REFUSED_PREFIX}warp_no_current_position"
# The audit word for COO `1744` item 3's closure.  `withheld_`, not
# `refused_`: the command was well formed and came from an allowlisted GM,
# and this route's own vocabulary reserves `refused_` for "we could not read
# what you typed".  The gate name is spelled the way the RE tickets will --
# an audit reader goes straight to the open question, same rule the two
# `withheld_*_vital_version` words above keep.
OUTCOME_WARP_WITHHELD_FORCE_POS_CLOSED = (
    f"{OUTCOME_WITHHELD_PREFIX}same_scene_force_pos_frame_shape"
)
# COO `2045` item 1's audit word.  `withheld_`, same reading as its
# neighbour: the command parsed and came from an allowlisted GM, and this
# lane chose not to send it.  Named after WHAT WAS TYPED (coordinates), not
# after a frame shape, because the closure spans two composers.
OUTCOME_WARP_WITHHELD_TYPED_COORDS_CLOSED = (
    f"{OUTCOME_WITHHELD_PREFIX}typed_coordinates"
)
OUTCOME_SAY_VERSION_CODEC_MISMATCH = (
    f"{OUTCOME_REFUSED_PREFIX}say_version_codec_mismatch"
)
# CORE-REQUEST-GM-049's `/speed`.  See the matching `EVENT_SPEED_*` pair
# above for the naming rationale.
OUTCOME_SPEED_WITHHELD_NO_VERSION = (
    f"{OUTCOME_WITHHELD_PREFIX}update_attr_vital_version"
)
# The run-copy-DB gate.  Prefixed `speed_` (unlike the version-gate outcome
# above) because this check's shape -- filename heuristic against a live
# `store.path` -- is not specific to `/speed`, and a future command reusing
# `_speed_db_is_canonical`'s pattern for its own send site would need its
# own outcome word rather than colliding with this one.
OUTCOME_SPEED_WITHHELD_CANONICAL_DB = f"{OUTCOME_WITHHELD_PREFIX}speed_canonical_db"
# COO-DECISION `1847`'s deferral, as the word the audit row carries.  A
# `withheld_` word rather than a `refused_` one, matching this module's own
# split: `refused_` means "this command was wrong", `withheld_` means "this
# command was fine and this lane did not send it".  A `/speed` that reaches
# this point parsed, authorized, passed every gate and WROTE ITS ROW.
OUTCOME_SPEED_DEFERRED = f"{OUTCOME_WITHHELD_PREFIX}speed_deferred_login_read"
OUTCOME_SPEED_NO_SELECTED_CHARACTER = (
    f"{OUTCOME_REFUSED_PREFIX}speed_no_selected_character"
)
# GT-193's hold.  See the matching `EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED`
# comment above.  Named after the SHAPE rather than after `/speed`, because a
# second door that ships an equally empty section earns the same hold and
# should be able to reuse this word instead of inventing a near-duplicate.
OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED = (
    f"{OUTCOME_WITHHELD_PREFIX}sparse_shape_empty_section"
)
# The persistence half's five named refusals.  See the matching
# `EVENT_SPEED_*` block above for why all five withhold the frame too.
OUTCOME_SPEED_NO_STORE = f"{OUTCOME_REFUSED_PREFIX}speed_no_store"
OUTCOME_SPEED_NO_CHARACTER_ID = f"{OUTCOME_REFUSED_PREFIX}speed_no_character_id"
# `refused_speed_persist_<ExcType>` -- the store raised.  Same TYPE-name-only
# discipline as `refused_speed_<ExcType>` above: a `TypedAttrError` message
# can embed the GM's typed text, and audit rows carry no typed text.
OUTCOME_SPEED_PERSIST_REFUSED_PREFIX = f"{OUTCOME_REFUSED_PREFIX}speed_persist_"
# `refused_speed_row_not_touched` -- the store door refused and rolled back.
# Spelled OUTSIDE the prefix above on purpose so `COMMITTED_ROW_BLOCKER_
# PREFIXES` cannot match it: that table exists to warn a reader that a row
# may already be committed, and this word means the opposite.  See the
# matching EVENT above.
OUTCOME_SPEED_ROW_NOT_TOUCHED = f"{OUTCOME_REFUSED_PREFIX}speed_row_not_touched"
# Snake-cased on purpose so it can never collide with an `<ExcType>` suffix
# above, which is always CamelCase.
OUTCOME_SPEED_PERSIST_READBACK_UNUSABLE = (
    f"{OUTCOME_SPEED_PERSIST_REFUSED_PREFIX}readback_unusable"
)
# `refused_speed_persist_compose_<ExcType>` -- see the matching EVENT above.
OUTCOME_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX = (
    f"{OUTCOME_SPEED_PERSIST_REFUSED_PREFIX}compose_"
)

# THE OUTCOME WORDS THAT MEAN A ROW IS ALREADY COMMITTED.  Every one of them
# is a NO-BYTES outcome, so the console printer reaches for a blocker
# sentence and would otherwise print `no blocker recorded` for exactly the
# states an attended tester most needs explained (pf-adversary D2).  Matched
# by PREFIX because two of the three carry an exception TYPE name that
# cannot be enumerated ahead of time, unlike every fixed key in
# `_NO_BYTES_BLOCKERS_SOURCE`.
COMMITTED_ROW_BLOCKER_PREFIXES = (
    (
        OUTCOME_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX,
        "the speed IS committed to the character row; the frame could not be"
        " composed afterwards, so no client was told -- the row is the truth",
    ),
    (
        # ~~"its compose gate can raise AFTER the write commits"~~ -- STRUCK
        # in round `ntf90h` (pf-adversary D6): that was true of the door this
        # route used to call, and `store.write_speed_by_identity` has no
        # post-commit compose gate.  The WARNING still stands, for a
        # different and worse reason: this prefix now only fires when
        # something raised ACROSS a boundary that door contracts never to
        # raise across, and the state behind such a break is by definition
        # unknown.  A door refusing NORMALLY reports
        # `refused_speed_row_not_touched` instead.
        OUTCOME_SPEED_PERSIST_REFUSED_PREFIX,
        "the store door raised across a boundary it contracts never to raise"
        " across, so the row's state is UNKNOWN -- do NOT read this as"
        " 'nothing was stored' (that word is refused_speed_row_not_touched)",
    ),
)
# The one named refusal `/gmprobe` can write that is not an exception TYPE
# suffix: the typed `variant_id` matched no row in
# `bt_gm_probe.VARIANTS_BY_ID`.  A GM typo, not this lane's error -- and not
# a guess at the closest match either (module docstring's own nonclaim).
OUTCOME_GMPROBE_UNKNOWN_VARIANT = f"{OUTCOME_REFUSED_PREFIX}gmprobe_unknown_variant"
OUTCOME_NO_WIRE_PATH = f"{OUTCOME_REFUSED_PREFIX}no_wire_path"
# `/lv`'s audit words.  The success one lives in `commands.py`'s
# `AUDIT_OUTCOMES` (`OUTCOME_LV_ROW_WRITTEN`) because it names a durable
# effect and the writer only accepts words from that tuple; the refusals below
# ride the two prefixes, same grammar as every other command's.
OUTCOME_LV_WITHHELD_CANONICAL_DB = f"{OUTCOME_WITHHELD_PREFIX}lv_canonical_db"
OUTCOME_LV_REFUSED_PREFIX = f"{OUTCOME_REFUSED_PREFIX}lv_"
# `refused_stage_<reason>`, where the reason is one of
# `login_scene_stage`'s own REASON_* values (`not_gm_account`,
# `unknown_scene`, `config_unreadable`, `write_failed`) or an exception TYPE
# name.  Same shape as `refused_warp_<ExcType>`, so a reader of the audit
# file does not have to learn a second grammar for the cross-scene half.
OUTCOME_STAGE_REFUSED_PREFIX = f"{OUTCOME_REFUSED_PREFIX}stage_"

# The two outcomes that mean AN EFFECT IS ON DISK: the cross-scene `/warp`
# wrote the account's next-login scene.  Spelled as a pair once, here,
# because two places used to test them inline and a third would have been
# the one that forgot the `_coords_ignored` half.
STAGED_OUTCOMES = (
    OUTCOME_STAGED_LOGIN_SCENE,
    OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED,
)

# The blocker sentence for each no-bytes outcome.  Read by the console line
# only; nothing here reaches the audit file or a client.  A `MappingProxyType`
# for the same reason `login_scene_admission` uses one: it stops a later
# module from editing this in place by accident, and it is NOT a safety
# boundary (the module attribute can still be rebound).
# The dict the proxy wraps, kept as its own name so a test can put a long
# sentence in it and prove the printer's cap actually cuts one (the cap has
# never fired on a real supplier, and that is how pf-adversary's M1 -- delete
# the cap, suite still green -- survived).  Read through the proxy below
# everywhere else.
_NO_BYTES_BLOCKERS_SOURCE = {
    OUTCOME_WARP_WITHHELD_NO_VERSION: (
        "RE-129 open: no confirmed ForcePos vital_version, so"
        " gm/teleport_wire.py cannot compose the frame"
    ),
    OUTCOME_SAY_WITHHELD_NO_VERSION: (
        "gm/say_wire.py gate shut: RE-132 answered the byte, the"
        " per-connection identity fix and a COO decision are what is left"
    ),
    OUTCOME_NO_WIRE_PATH: (
        "this lane has no proven server->client wire for that command;"
        " a CORE-REQUEST-GM opens one"
    ),
    OUTCOME_WARP_NO_POSITION: (
        "this connection has no current position to warp from"
    ),
    OUTCOME_WARP_WITHHELD_FORCE_POS_CLOSED: (
        "R306 closed the client with ErrorData=28317 on this 45-byte"
        " ForcePos; COO shut the same-scene coordinate warp until the frame"
        " shape is diffed against a real capture -- bare /warp <n> still works"
    ),
    OUTCOME_WARP_WITHHELD_TYPED_COORDS_CLOSED: (
        "COO-DECISION 2045 item 1 shut EVERY typed-coordinate /warp above"
        " every composer after R306 closed the client with ErrorData=28317;"
        " no frame is built and no row is touched -- bare /warp <n> still"
        " works"
    ),
    OUTCOME_SAY_VERSION_CODEC_MISMATCH: (
        "the confirmed vital_version is not the codec's; composing"
        " would build a frame the client cannot read"
    ),
    OUTCOME_SPEED_WITHHELD_NO_VERSION: (
        "no confirmed UpdateAttrVital version for the /speed sparse door;"
        " see attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED's own comment"
    ),
    OUTCOME_SPEED_WITHHELD_CANONICAL_DB: (
        "session.foundation.lifecycle.store.path's filename is (or could not"
        " be read as anything but) the canonical pirateforce.sqlite3; /speed"
        " refuses to send against it -- boot with an explicit --db run-copy"
    ),
    OUTCOME_SPEED_NO_SELECTED_CHARACTER: (
        "this connection has no selected character to read identity_lo/hi"
        " from"
    ),
    OUTCOME_SPEED_DEFERRED: (
        "COO-DECISION 1847 holds every /speed frame until LANE-DB lands the"
        " speed_walk login read on main; the row was written, the frame was"
        " not sent"
    ),
    OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED: (
        "GT-193 sent this frame shape and the character died and the client"
        " locked out immediately after; no client has been measured accepting"
        " any shape of this door, so every send is held until one is"
    ),
    OUTCOME_SPEED_NO_STORE: (
        "session.foundation.lifecycle.store is unreadable, so /speed has no"
        " database to write the value to before painting it"
    ),
    OUTCOME_SPEED_NO_CHARACTER_ID: (
        "this connection's selected character carries no usable id, so"
        " /speed cannot name the row to persist into"
    ),
    OUTCOME_SPEED_PERSIST_READBACK_UNUSABLE: (
        "the value was committed but the store's composed read-back for x=7"
        " is not a number this lane may encode; no frame was sent"
    ),
    # NOT a `/speed` word, and added in a `/speed` round on purpose: making
    # `test_every_no_bytes_outcome_this_module_can_write_has_a_blocker`
    # DERIVE its list instead of hand-typing it (pf-adversary round `ntf90h`,
    # D3) turned this pre-existing gap red.  Until now a GM who typed an
    # unknown `/gmprobe` variant read `no blocker recorded` on the console.
    OUTCOME_GMPROBE_UNKNOWN_VARIANT: (
        "the typed variant id matched no row in bt_gm_probe.VARIANTS_BY_ID,"
        " so there was no probe to send; nothing was guessed at and nothing"
        " went out"
    ),
    OUTCOME_SPEED_ROW_NOT_TOUCHED: (
        "the store door refused and rolled its own transaction back, so the"
        " character row still holds exactly what it held before this command"
        " -- nothing was stored, and no frame was sent"
    ),
    WHY_AUDIT_ROW_NOT_WRITTEN: (
        "the outcome row could not be appended, so this command's audit"
        " trail is broken; anything it had in hand was dropped with it"
    ),
    WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT: (
        "the outcome row could not be appended AND the revert failed, so the"
        " durable change named by character_id above is STILL IN PLACE --"
        " read the row, do not assume it was rolled back"
    ),
    # The five server-side stage faults (pf-adversary D4).  Keyed by the
    # audit word `_stage_action` writes, built from the reason constants
    # rather than spelled as literals so a rename upstream is a red test
    # here instead of a silent `no blocker recorded`.
    f"{OUTCOME_STAGE_REFUSED_PREFIX}"
    f"{login_scene_stage.REASON_NOT_GM_ACCOUNT}": (
        "the account is not in gm_accounts.json at the path this process"
        " booted with; the command was authorized against another reading"
    ),
    f"{OUTCOME_STAGE_REFUSED_PREFIX}"
    f"{login_scene_stage.REASON_CONFIG_UNREADABLE}": (
        "the gm_login_scene.json this process reads is malformed; fix or"
        " delete that file (see GM_LOGIN_SCENE_CONFIG_REFUSED)"
    ),
    f"{OUTCOME_STAGE_REFUSED_PREFIX}"
    f"{login_scene_stage.REASON_EXISTING_ENTRY_NOT_ADMISSIBLE}": (
        "another ACCOUNT's line in gm_login_scene.json names a scene"
        " login will not admit; the whole file is refused until it goes"
    ),
    f"{OUTCOME_STAGE_REFUSED_PREFIX}"
    f"{login_scene_stage.REASON_CONFIG_NOT_WRITABLE}": (
        "the config DIRECTORY is not writable by this process; os.replace"
        " needs the directory's write bit, not the file's"
    ),
f"{OUTCOME_STAGE_REFUSED_PREFIX}"
f"{login_scene_stage.REASON_WRITE_FAILED}": (
    "the write to gm_login_scene.json failed; the previous entry, if"
    " any, is untouched"
),
}

# `/lv`'s blockers, BUILT FROM `level_command`'s own reason constants rather
# than hand-typed here -- the same lesson `test_every_named_stage_fault_has_a_
# blocker_derived_from_upstream` records for the staged-scene reasons: a
# hand-typed list said five when upstream had ten, and the five that were
# missing inherited `no blocker recorded` in silence.  A reason added in
# `level_command.py` therefore arrives here with a sentence or turns the
# coverage test red; it cannot arrive mute.
_LV_BLOCKERS = {
    level_command.REFUSED_ARGS_SHAPE: (
        "lv got something other than one plain word as its argument"
    ),
    level_command.REFUSED_NOT_AN_INTEGER: (
        "lv takes a whole number; nothing was written"
    ),
    level_command.REFUSED_OUT_OF_RANGE: (
        "the level is outside the range the column stores; nothing was"
        " written"
    ),
    level_command.REFUSED_NO_CHARACTER: (
        "this connection has no selected character to set a level on"
    ),
    level_command.REFUSED_NO_STORE: (
        "this session has no store to write a level to"
    ),
    level_command.REFUSED_ROW_MISSING: (
        "the selected character has no live row; nothing was written"
    ),
    level_command.REFUSED_WRITE_FAILED: (
        "the store refused the level write; see the audit row for the"
        " exception type"
    ),
    level_command.REFUSED_READBACK_MISMATCH: (
        "the row read back a different level than the one asked for"
    ),
    level_command.REFUSED_LOGIN_WOULD_NOT_SEND: (
        "the row took the level but this character's login vitals do not"
        " resolve, so the next login would send the constant; fix"
        " hp_current/hp_max for the row first"
    ),
}
# THE TWO REFUSALS THAT WROTE SOMETHING FIRST CARRY A REPAIR SUFFIX, and the
# suffix changes what the tester must do next -- so each variant gets its own
# sentence rather than sharing the bare reason's.  Built by product rather
# than typed out, for the reason the base table is: a reason added upstream
# must arrive here with a sentence or turn the coverage test red.
for _lv_reason in (
    level_command.REFUSED_READBACK_MISMATCH,
    level_command.REFUSED_LOGIN_WOULD_NOT_SEND,
):
    _LV_BLOCKERS[f"{_lv_reason}{level_command.REPAIRED_SUFFIX}"] = (
        f"{_LV_BLOCKERS[_lv_reason]}; the previous level was put back"
    )
    _LV_BLOCKERS[f"{_lv_reason}{level_command.REPAIR_FAILED_SUFFIX}"] = (
        f"{_LV_BLOCKERS[_lv_reason]}; putting the previous level back FAILED"
        " -- treat the row as UNKNOWN"
    )
for _lv_reason, _lv_sentence in _LV_BLOCKERS.items():
    _NO_BYTES_BLOCKERS_SOURCE[f"{OUTCOME_LV_REFUSED_PREFIX}{_lv_reason}"] = (
        _lv_sentence
    )
_NO_BYTES_BLOCKERS_SOURCE[OUTCOME_LV_WITHHELD_CANONICAL_DB] = (
    "lv writes a row, and this process is on the canonical database; boot"
    " a run copy (--db) and type it again"
)
del _lv_reason, _lv_sentence

NO_BYTES_BLOCKERS = MappingProxyType(_NO_BYTES_BLOCKERS_SOURCE)

# The sentence for each SERVER-SIDE DROP (`chat_command.SERVER_SIDE_DROP_
# REFUSALS`).  Same shape and same rules as the mapping above: lane-authored
# text only, one ASCII line each, never built from what was typed.  Matched by
# PREFIX because the log-write member carries an exception TYPE name.
SERVER_DROP_BLOCKERS = (
    (
        REFUSAL_RATE_LIMITED,
        "this GM account hit the per-account command ceiling; the command was"
        " dropped whole, nothing was written and nothing was sent -- wait out"
        " the window and retype it",
    ),
    (
        REFUSAL_LOG_QUOTA_EXCEEDED,
        "the GM command audit log is at its size quota, and this lane refuses"
        " to run a command it cannot record -- rotate or move"
        " capture/gm_command_log.ndjson",
    ),
    (
        REFUSAL_LOG_WRITE_FAILED_PREFIX,
        "the GM command audit log could not be written (disk full, read-only,"
        " or the directory is gone), and this lane refuses to run a command"
        " it cannot record",
    ),
)


@dataclass(frozen=True)
class _Verdict:
    """What one command handler decided, on its way to the ONE write point.

    `action` is the outbound action tuple or None, `audit_outcome` is the
    word the `outcome` row will carry, and `undo` -- new with the cross-scene
    warp -- is a zero-argument callable returning True on success, present
    only for a handler that already changed durable state by the time it
    returns.  `_make_action` runs it if, and only if, the outcome row cannot
    be written: this house does not keep an effect it could not record, and
    for every other handler "do not keep it" costs nothing because nothing
    was sent.  `login_scene_stage` writes a config file, so its undo has to
    be a real one.
    """

    action: tuple[str, bytes, bytes, float] | None
    audit_outcome: str
    undo: object | None = None
    # True when this handler ALREADY wrote a console line explaining itself.
    # `_make_action`'s no-bytes line is the backstop for handlers that did
    # not, and a backstop that cannot tell whether the specific line was
    # written prints a second one next to it -- which is how `/warp 9999`
    # would come to answer the same question twice, in two different
    # vocabularies, on the console an attended run greps.  Reported by the
    # handler rather than inferred from the outcome word, because the
    # printer has early returns (`DESTINATION_SHAPED_REASONS`, a `None`
    # stderr, a stream that raises) that the outcome word cannot see.
    line_printed: bool = False
    # True when `action` is an ON-SCREEN NOTICE about a command that did NOT
    # run, rather than the command's own frame.  Reported by the handler, not
    # inferred from the label, for the reason the `SPEED_DENIED_NOTICE_ACTION_
    # LABEL` comment gives: two call sites downstream ask "did the command go
    # out?" and both of them would answer "yes" for a sentence that says the
    # opposite.  A notice therefore:
    #   * does not suppress the `GM_CHAT_NO_BYTES_SENT` console line
    #     (`_announce_console_outcome`'s `sent` argument), and
    #   * does not arm CORE-REQUEST-GM-040's `queued` confirmation, because a
    #     `queued` row means "this command's frame reached runtime" and an
    #     audit reader cannot tell such a pair from a command that really ran
    #     (LANE-GM's letter `20260902_0419`, question 1).
    is_notice: bool = False
    # True when this handler composed the bare `/warp <n>` TeleportVital for
    # the scene the connection is ALREADY IN (`PANYA-DECISION 1800`).  Read
    # by `_announce_console_outcome` and by nothing else: it picks WHICH
    # console token an attended tester greps, and it can never change which
    # bytes go out -- the frame, the label and the audit outcome are
    # identical to the cross-scene shape's, on purpose.
    #
    # A FIELD RATHER THAN A SECOND ACTION LABEL, because the label is read by
    # `runtime.py`'s `_GM_WARP_LABELS` resync and by the `TELEPORT`-substring
    # move-authority rule, and a fourth label would have had to be added to
    # both by hand -- the exact drift `WARP_CROSS_SCENE_NO_COORDS_TELEPORT_
    # ACTION_LABEL` already caused once (pf-adversary, round `zkqaq1`).
    same_scene_teleport: bool = False
    # True when the STAGE this verdict carries named the scene the connection
    # is already in.  Read by `_announce_console_outcome` and by nothing else:
    # it picks which of the two `next=` tails `_print_staged_way_out` prints
    # (`COO-DECISION 20260903_2050` item 2), and it can never change what is
    # written to disk -- a markerless same-scene `/warp` stages exactly what
    # it staged before this field existed.
    #
    # A SECOND FIELD RATHER THAN A REUSE OF `same_scene_teleport`, which is
    # about a SENT frame: `_announce_console_outcome` returns on `sent` before
    # it ever reaches the staged branch, so one field serving both would be
    # read on a path where its own docstring's meaning is false.
    #
    # DECIDED IN `_warp_action` AND CARRIED, never re-derived at print time --
    # but NOT for the reason this comment first gave (pf-adversary, round
    # `spt6fv`, D6, MEASURED).
    #
    # ~~"`runtime.py`'s `_gm_warp_resync_selected_scene` rewrites
    # `selected.position.scene_id` to a warp's DESTINATION at queue time, so a
    # printer that re-read the position would call every stage 'same scene'
    # once the resync had run"~~ -- that hazard cannot occur on THIS path, and
    # a mutant that re-derives the value at print time survives the whole
    # suite, which is how it was caught.  The resync loop fires only for
    # actions whose label is in `_GM_WARP_LABELS`, and a staged verdict
    # returns `action=None`, so nothing can resync between `_warp_action`'s
    # read and a print-time read WITHIN one command; and when an EARLIER live
    # warp has already poisoned the field, `_warp_action`'s own read is
    # poisoned identically -- which is not a reason to prefer one read over
    # the other, it is `basis=` (D2, printed on the line since this round).
    #
    # The real reason is smaller and holds anyway: `_warp_action` is the one
    # function that knows the current scene, it has already answered this,
    # and a second answer to an answered question is a second thing to keep
    # in agreement.  `SAME_SCENE_BASIS_FIELD` one token up carries the same
    # struck rationale; it is left as written -- history is not deleted -- and
    # is corrected by this note and by `docs/GM_LANE.md`.
    staged_same_scene: bool = False
    # WHICH BLOCKER held this command's frame, for the console only: one of
    # the three `STAGED_BLOCKER_*` names, decided by `_staged_blocker` from
    # what the routing already learned.  A NAME, not the sentence: the
    # verdict is dispatch state, and rewording must never reach the routing.
    # Defaults to the missing-spawn blocker because that is the only one that
    # can hold a frame on the shipped flags.
    staged_blocker: str = STAGED_BLOCKER_NO_SPAWN
    # ON WHOSE WORD the two `same_scene` fields above were decided, for the
    # console only: `SAME_SCENE_BASIS_FIELD` or
    # `CLIENT_CONFIRMED_SCENE_BASIS_FIELD`, answered once by
    # `same_scene_with_basis` in `_warp_action`.
    #
    # ONE FIELD SERVING BOTH `same_scene_teleport` AND `staged_same_scene`,
    # unlike those two, and the difference is not an inconsistency: those are
    # two ANSWERS on two mutually exclusive paths (a sent frame vs a staged
    # entry, and `_announce_console_outcome` returns on `sent` before it can
    # reach the staged branch), while this is the SOURCE of whichever answer
    # was reached -- one comparison in one function, so one field.
    #
    # DEFAULTS TO THE WEAKER BASIS, deliberately, on the same rule as
    # `staged_blocker` and `same_scene`: a construction site that does not
    # set it -- every refusal verdict, every non-warp command -- says the
    # thing that was true before chief's field landed rather than claiming
    # the client backed a word it never saw.
    same_scene_basis: str = SAME_SCENE_BASIS_FIELD


def _note(session: object, event: str) -> None:
    """Append one event name, and never raise doing it.

    `session.events` is a plain list on every real runtime session, but this
    module is reached from a call site that also runs under tests, replay
    tools and future callers; a missing or read-only `events` must not turn
    a refusal into a crash on the listener thread.
    """
    try:
        session.events.append(event)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - see docstring; nothing escapes this module
        pass


def _selected_scene_id(session: object):
    """The IN-MEMORY scene label right now, or None if it cannot be read.

    `CORE-REQUEST-GM-059`.  Deliberately NOT `warp_scene_persist.
    row_before_warp`, which reads the durable row -- see the call site in
    `_warp_teleport_action_no_coords` for the measured case where the two
    disagree, and `warp_send_watch.ParkedWarpSend` for what goes wrong when
    one is used for the other.

    Returns None rather than raising, for the same reason every other helper
    on this path does: it is called while composing a frame the client is
    about to be sent, and a session shaped unexpectedly must cost the park
    its extra field, never the warp.  `warp_send_watch` answers `selected_
    scene_unknown` for that park and writes nothing.
    """
    try:
        scene_id = session.foundation.selected.position.scene_id
    except Exception:  # noqa: BLE001 - see docstring
        return None
    if not isinstance(scene_id, int) or isinstance(scene_id, bool):
        return None
    return scene_id


def _print_chat_tail_once(
    session: object,
    split: object,
    payload_length: int,
) -> None:
    """One console line per connection per reason, and never more.

    WHY A LATCH AND NOT A PLAIN PRINT.  This still runs ahead of the rate
    limiter -- the limiter lives inside `handle_local_talk_chat`, below the
    decode this round is retrying -- so an unlatched line would be one
    console write per frame, which is the defect pf-adversary measured on
    this very module (D3, round `9wy444`: 100 console lines from 100 crafted
    frames).  The bound here is per-connection: at most one line for each
    distinct reason, at most as many lines as `chat_frame_tail` has reason
    names, for the life of a connection.

    WHO CAN DRIVE IT AT ALL, which is the half that matters more than the
    latch: only an account already on the GM allowlist.  The call site
    reaches this function only after `handle_local_talk_chat` has authorized
    the account and refused the frame, so a stranger's chat -- however
    crafted -- reaches neither this print nor the `_note` beside it.

    WHAT IS LOST BY LATCHING, said plainly: the console cannot be used to
    COUNT these frames, only to learn that this connection saw one.  The
    count lives on `session.events`.

    !! AND `session.events` IS NOT A QUIET TRAIL -- pf-adversary (D7, round
    `uyzr8c`) is right that calling it one would be wrong.  `runtime.py`'s
    `_EventEchoList` echoes EVERY append through the stdout exporter when
    the process runs with `--export-events`, so an event here is a stdout
    line there.  It is not latched, and this round does not claim it is
    bounded: it is one extra line on a path that already writes
    `gm_chat_action_refused_*` for the same frame, driven only by an
    allowlisted GM, which is why it is left un-latched rather than made to
    lie about how many frames arrived.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- the rule the three sibling
    printers in this file hold: everything that can raise is inside the
    guard, a `None` stderr returns rather than letting `print` fall back to
    STDOUT, and a console that cannot be written is NAMED on the event trail.
    A session that will not hold the latch attribute still gets its command;
    it just gets a line per frame instead of one, which is why the failure to
    latch is itself recorded rather than swallowed.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        reason = split.reason
        reported = getattr(session, SESSION_CHAT_TAIL_REPORTED, None)
        if isinstance(reported, set):
            if reason in reported:
                return
            reported.add(reason)
        else:
            try:
                setattr(session, SESSION_CHAT_TAIL_REPORTED, {reason})
            except Exception:  # noqa: BLE001 - see the docstring's last line
                _note(session, f"{EVENT_CHAT_TAIL_PREFIX}latch_unavailable")
        print(
            console_safe(
                chat_frame_tail.tail_console_line(split, payload_length),
                stream,
            ),
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - a diagnostic may not raise
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _is_undecodable_payload(outcome: object) -> bool:
    """True for the ONE refusal CHAT-TAIL-001 is allowed to retry.

    Narrow on purpose.  `chat_payload_undecodable_*` is the refusal a chat
    body with another vital glued to its end produces, and it is the only
    one this round may look at: it is returned below the identity check and
    below the size ceiling, so seeing it proves both have already passed.
    Every other refusal -- not a GM, too large, rate limited, not a command,
    a parse error -- means the frame was understood and answered, and
    retrying any of them would be this lane arguing with a verdict.
    """
    reason = getattr(outcome, "refusal_reason", None)
    if not isinstance(reason, str):
        return False
    return reason.startswith(REFUSAL_UNDECODABLE_PREFIX)


def _isolated_chat_payload(
    session: object,
    payload: bytes,
    legacy: object,
) -> bytes:
    """The chat body of `payload`, which on every captured frame IS `payload`.

    CHAT-TAIL-001, and the whole of what it changes: when v141 hands this
    lane a payload that is a chat body FOLLOWED BY whole nested vitals, the
    command runs on the isolated body instead of being refused as
    `chat_payload_undecodable_ChatDecodeError`.  In every other case --
    including every frame this project has ever captured -- THE CALLER'S OWN
    OBJECT is returned (identity, not equality: the call site tests `is not`
    to decide whether to retry at all) and the route behaves exactly as it
    does on main.

    IT NEVER WIDENS WHO MAY COMMAND, and after pf-adversary's D1 it never
    even RUNS for a non-GM: the call site reaches this only after
    `handle_local_talk_chat` has authorized the account and refused the
    frame as undecodable.  See `gm/chat_frame_tail.py`'s docstring for the
    argument in full, and for the sentence that says no multi-vital chat
    frame has ever been captured.
    """
    split = chat_frame_tail.split_local_talk_payload(payload, legacy)
    if split.reason == chat_frame_tail.NO_TAIL:
        return payload
    if split.reason == chat_frame_tail.TAIL_WALKED:
        _note(session, f"{EVENT_CHAT_TAIL_PREFIX}walked_{len(split.tail_ids)}")
        _print_chat_tail_once(session, split, len(payload))
        return split.body
    if split.reason == chat_frame_tail.TAIL_SECOND_CHAT_DROPPED:
        # pf-adversary D-F: the first chat line runs and the second is lost.
        # It gets its own event because it is the one shape where accepting
        # the body COSTS something -- everywhere else the tail was never
        # going to be read by anybody.
        _note(
            session,
            f"{EVENT_CHAT_TAIL_PREFIX}second_chat_dropped_{len(split.tail_ids)}",
        )
        _print_chat_tail_once(session, split, len(payload))
        return split.body
    if split.reason == chat_frame_tail.TAIL_UNDECLARED_BODY:
        # R313's frame, and the reason this branch exists rather than
        # folding into the one above: the two outcomes must stay countable
        # apart on `session.events`.  `walked_n` means every tail vital
        # closed; this one means the walk stopped at an id with no declared
        # body length and the command ran anyway on a boundary the strict
        # decoder had already proved.  A round that reads them as one number
        # cannot tell "the client sent a shape we fully understand" from
        # "the client sent a shape we understand the front of", and R313 is
        # the second.
        _note(
            session,
            f"{EVENT_CHAT_TAIL_PREFIX}undeclared_body_{len(split.tail_ids)}",
        )
        _print_chat_tail_once(session, split, len(payload))
        return split.body
    if split.reason not in chat_frame_tail.QUIET_REASONS:
        _note(session, f"{EVENT_CHAT_TAIL_PREFIX}{split.reason}")
        _print_chat_tail_once(session, split, len(payload))
    return payload


def _note_npc_recompose_diagnostic(session: object, command: object) -> None:
    """Read-only diagnostic for a parsed `npc` command; never touches verdict.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH (this module's own rule, stated at
    the `CONSOLE_TOKEN` print above) -- this function's only effect is one
    `_note` call, exactly like that print.  The call site below runs it
    AFTER `verdict` is already bound to `_Verdict(None, OUTCOME_NO_WIRE_PATH)`
    -- pf-adversary (round `nbihci`) measured the first draft calling this
    one line too early, before `verdict` was bound, so an uncaught exception
    here would have propagated past the assignment instead of landing inside
    it; harmless only because of the wrap below, and the wrong order to
    trust by reading this docstring.  `_note` itself cannot raise (see its
    own docstring); everything upstream of it here is wrapped so this
    function cannot either -- a caller-supplied `command.args` of the wrong
    shape (`GmCommandArgsError`'s own threat model -- a `tuple` SUBCLASS
    lying through `__len__`/`__getitem__` defeats a plain `isinstance`
    check, per `commands.py`'s own `_require_args_tuple`, which is why this
    uses `type(args) is not tuple` and not `isinstance`) or a `mob_id` that
    is not one of the 7 GM-switchable rows (`npc_toggle_would_recompose`'s
    `ValueError`) must not turn a diagnostic into the reason `/npc` stopped
    working.
    """
    try:
        args = command.args
        if type(args) is not tuple or len(args) != 2:
            _note(session, f"{EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}bad_args_shape")
            return
        mob_id = int(args[1])
        if not npc_switch_catalog.is_gm_switchable_npc(mob_id):
            _note(
                session,
                f"{EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}not_switchable",
            )
            return
        would_recompose = gm_npc_toggle_recompose.npc_toggle_would_recompose(mob_id)
        _note(
            session,
            f"{EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}would_recompose_"
            f"{'true' if would_recompose else 'false'}",
        )
    except Exception as error:  # noqa: BLE001 - a diagnostic must not raise
        _note(
            session,
            f"{EVENT_NPC_RECOMPOSE_DIAGNOSTIC_PREFIX}unexpected_{type(error).__name__}",
        )


def _note_item_catalog_diagnostic(session: object, command: object) -> None:
    """Read-only diagnostic for a parsed `item` command; never touches verdict.

    Mirrors `_note_npc_recompose_diagnostic` exactly (same shape guard, same
    `noqa: BLE001` boundary, same "diagnostic may never alter dispatch"
    rule) -- see that function's docstring for why `type(args) is not tuple`
    and not `isinstance` guards the shape check.  `command.args` for `item`
    is `(id, n)` (see `commands.py::parse_gm_command`'s `item` branch); only
    `args[0]` is read here, `n` is not this diagnostic's question.

    Three outcomes instead of two, because `item_catalog.item_category`
    can name zero, one, or more than one category for the same id:
      unknown            -- item_id is in none of the three tables
      known_<category>   -- item_id resolves in exactly one (the common
                             case); the category is named so a reader does
                             not have to cross-reference a second file
      ambiguous_<n>       -- item_id resolves in `n` categories (2 or 3);
                             this is the exact shape round `opr2xd` found
                             and asked chief/Panya to decide the grammar
                             for -- naming it here does not decide it
    """
    try:
        args = command.args
        if type(args) is not tuple or len(args) != 2:
            _note(session, f"{EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}bad_args_shape")
            return
        item_id = int(args[0])
        cats = item_catalog.item_category(item_id)
        if not cats:
            _note(session, f"{EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}unknown")
        elif len(cats) == 1:
            _note(
                session,
                f"{EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}known_{cats[0]}",
            )
        else:
            _note(
                session,
                f"{EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}ambiguous_{len(cats)}",
            )
    except Exception as error:  # noqa: BLE001 - a diagnostic must not raise
        _note(
            session,
            f"{EVENT_ITEM_CATALOG_DIAGNOSTIC_PREFIX}unexpected_{type(error).__name__}",
        )


def _typo_refused_notice(
    session: object,
    legacy: object,
    refusal_reason: object,
) -> tuple[str, bytes, bytes, float] | None:
    """`TYPO REFUSED` on screen for a command the GRAMMAR refused, or None.

    COO-DECISION 2026-09-02T06:47+07:00 (`pf_bridge/notes_to_chief/consumed/
    20260902_0647_COO-DECISION-typo-layer-notice-is-TYPO-REFUSED-12-ascii-
    after-p1.md`), which is the follow-up `0345`'s own round asked for: the
    `/speed` notice closed the DB-refusal layer, and left the commonest GM
    mistake of all -- a line the parser could not read -- exactly as silent as
    it was before (`tests/test_gm_speed_denied_notice.py` pinned that silence
    at the time, citing this decision as the thing that would lift it).

    ONE LAYER, EVERY COMMAND NAME.  The gate is `refusal_reason.startswith(
    REFUSAL_PARSE_ERROR_PREFIX)` and nothing else, so it fires for
    `/warp island`, a bare `/warp`, `/lv`, `/spawn x`, `/speed fast`,
    `/nonsense` and `/` alike -- the parse layer is the one place that reports
    all of them under one word.  Every OTHER refusal `chat_command.py` can
    return composes NOTHING, and each exclusion is somebody's stated reason
    rather than an omission (the long comment above that module's
    `TYPED_COMMAND_REFUSAL_PREFIXES` names them one by one):

      REFUSAL_NOT_GM               -- nothing was decoded; this lane never
      REFUSAL_LOOKUP_FAILED_PREFIX    looked at the line and must not learn to
      REFUSAL_NOT_A_COMMAND        -- a GM talking.  A frame per sentence, to
                                      say "that was not a typo", is noise
      REFUSAL_PAYLOAD_TOO_LARGE    -- a malformed FRAME, which no typing can
      REFUSAL_UNDECODABLE_PREFIX      fix; calling it a typo blames a human
      REFUSAL_UNSAFE_COMMAND_TEXT  -- the bidi/format-character refusal.  It
                                      is a typed-command refusal and it is
                                      still NOT this layer: the decision names
                                      `parse_gm_command` alone, and this one
                                      is refused above the parser
      REFUSAL_RATE_LIMITED         -- the ceiling that BOUNDS this feature.  A
      REFUSAL_LOG_QUOTA_EXCEEDED      notice for it would be a frame composed
      REFUSAL_LOG_WRITE_FAILED_*      per frame the limiter is refusing, and
                                      the last two mean the audit log is
                                      broken, which is not a typo either

    That exclusion list is also what caps the wire cost: a parse refusal is
    returned BELOW `rate_limit_allows` in `handle_local_talk_chat`, so at most
    `dispatch.RATE_LIMIT_MAX_CALLS_PER_WINDOW` of these can be composed per
    account per window, however fast a client types.

    FAIL CLOSED, AND NAMED.  A composer failure returns None -- the refusal
    itself is untouched, because it was already decided by the time this runs
    and the caller returns whatever this returns as its whole answer -- and it
    is recorded as `EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX + <ExcType>`.
    TYPE NAME ONLY: a `NoticeWireError` message is this lane's own text today,
    but the `except` below is deliberately broad (the `legacy` seam raises
    `AttributeError`, measured in round `aa9ajr` D7), and an arbitrary
    exception's message can carry bytes this lane may not print to a cp874
    console.  Nothing escapes onto the listener thread: an on-screen courtesy
    may never turn a named refusal into `gm_chat_action_unexpected_<Type>`,
    which is this module's standing rule for diagnostics.

    NO `queued` ROW, and not by omission: this function never touches
    `_arm_queued_confirm`.  `queued` closes a command's `issued` row and means
    "this COMMAND's frame reached runtime" -- a mistyped command has no
    `issued` row at all (the grammar refused it above `log_gm_command`), so a
    `queued` row here would close nothing and read like a command that ran
    (LANE-GM's letter `20260902_0419` question 1, accepted by COO-DECISION
    `0647` item 2).  For the same reason there is no `_Verdict` and no
    `_log_outcome` on this path: there is no audit pair to keep honest.
    """
    if not isinstance(refusal_reason, str):
        # `handle_local_talk_chat` always sets a string here; this module also
        # reads its outcome fields off an arbitrary object in tests and in any
        # future caller, and a non-string must be a quiet "not my layer"
        # rather than an `AttributeError` one frame up.
        return None
    if not refusal_reason.startswith(REFUSAL_PARSE_ERROR_PREFIX):
        return None
    try:
        pc, frame = say_wire.make_local_talk_notice_frame(
            legacy, say_wire.TYPO_REFUSED_NOTICE_TEXT
        )
    except Exception as error:  # noqa: BLE001 - includes NoticeWireError
        _note(
            session,
            f"{EVENT_TYPO_REFUSED_NOTICE_FAILED_PREFIX}{type(error).__name__}",
        )
        return None
    _note(session, EVENT_TYPO_REFUSED_NOTICE_COMPOSED)
    return (TYPO_REFUSED_NOTICE_ACTION_LABEL, pc, frame, 0.0)


def make_gm_chat_command_action(
    session: object,
    payload: bytes,
    legacy: object,
    *,
    config_path: str | None = None,
    log_path: str | None = None,
    login_scene_config_path: str | None = None,
    scene_registry=None,
) -> tuple[str, bytes, bytes, float] | None:
    """Authorize + audit one chat line; return one outbound action, or None.

    `session` is `runtime.py`'s session object (`self` at the call site).
    The full surface this module touches, which chief's call site has to
    provide (pinned by `SessionSurfaceTests`, not by this sentence):
    READS `.token` (the authenticated login name -- the identity, never read
    from `payload`), `.events` (diagnostics), and for the warp case
    `.foundation.selected.position` (the connection's own current
    scene/elevation) and `.foundation.selected.id` (which character the warp
    was for).  WRITES `.gm_last_warp_target` on an accepted warp only --
    `warp_target_record`'s parked destination, for `runtime.py` to compare a
    later position row against; a session that cannot hold it still gets its
    warp.  READS AND WRITES `._gm_action_queued_confirm` whenever an action
    is returned (CORE-REQUEST-GM-040): the `(action, callback)` pair chief's
    append site in `runtime.py` fires to confirm the action really reached
    the action list.  A session that cannot hold that one still gets its
    command -- only the `queued` audit row is lost, and the loss is named
    on `.events` rather than left as a silent gap.

    `legacy` is the loaded `pf_login_game_server_v141` module, the same seam
    `state_wire`/`teleport_wire` already take from their wiring caller rather
    than importing the frozen serializer themselves.

    Returns `(label, pc, frame, delay_before)` -- append it to the action
    list, exactly like `gm_state_action` -- or None, which means "this frame
    is not ours; behave exactly as the server did before this lane existed".

    !! AN ACTION IS NOT ALWAYS A COMMAND.  Two of the labels this can return
    are ON-SCREEN NOTICES about a command that did NOT run -- a refused
    `/speed` (`SPEED_DENIED_NOTICE_ACTION_LABEL`, COO-DECISION `0345`) and a
    MISTYPED command of any name (`TYPO_REFUSED_NOTICE_ACTION_LABEL`,
    COO-DECISION `0647`).  The caller appends them the same way; nothing at
    the call site changes.  It is said here because "an action came back"
    stopped meaning "the command ran" the day the first notice landed, and a
    reader of this docstring is exactly who would otherwise assume it.

    `scene_registry` -- OPTIONAL, AND THE ONE ARGUMENT WHOSE ABSENCE COSTS
    THE TESTER SOMETHING.  `/warp` decides whether a destination can be
    entered at login, and left `None` it decides that from lane A's registry
    FILE while the login that follows is placed from the snapshot
    `runtime.py` loaded at boot.  A file edited wider since boot makes
    `/warp` accept a scene the login then refuses -- and the refusal reaches
    the server console, never the person who typed the command.  Passing
    the caller's own `scene_entry_registry` moves that refusal to the chat
    line, and makes the list of destinations printed with it the list the
    running process would really accept.  `CORE-REQUEST-GM-036`.

    WIRED: chief passes `runtime.py`'s boot snapshot into the chat factory
    (`CHIEF-REPLY` 2026-08-29T15:16+07:00, main as `pirate-force-server`
    #264), by naming the closure variable directly rather than through
    `getattr` -- so if that variable is ever renamed the result is a loud
    `NameError` and not a quiet fall back to reading the file.  An earlier
    revision of this line said "no caller passes it in this commit", which
    was true when written and false from that merge on.  `None` is still
    the default and still means a fresh read.
    """
    try:
        return _make_action(
            session,
            payload,
            legacy,
            config_path=config_path,
            log_path=log_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
    except Exception as error:  # noqa: BLE001 - fail-closed, see module docstring
        # Type name only: an exception MESSAGE can embed client-supplied
        # bytes, which is both a leak and a cp874 console hazard.
        _note(session, f"{EVENT_UNEXPECTED_PREFIX}{type(error).__name__}")
        return None


def _make_action(
    session: object,
    payload: bytes,
    legacy: object,
    *,
    config_path: str | None,
    log_path: str | None,
    login_scene_config_path: str | None = None,
    scene_registry=None,
) -> tuple[str, bytes, bytes, float] | None:
    token = getattr(session, "token", None)
    # `type(...) is not str`, not isinstance, and checked HERE rather than
    # left to handle_local_talk_chat's own ValueError: a str subclass lying
    # through __eq__/__hash__ is the allowlist bypass accounts.is_gm_account
    # closes, and a session with no token at all (pre-login frame, test
    # double) must be a named refusal on this path, not an exception caught
    # one frame up as if the module had a bug.
    if type(token) is not str or not token:
        _note(session, f"{EVENT_BAD_SESSION_PREFIX}{type(token).__name__}")
        return None
    # Same treatment for the OTHER argument chief constructs at the call site.
    # `parsed.nested_payload` is declared bytes today, so this is not live --
    # but pf-adversary's defect 13 is right that a call site written one day
    # as a memoryview slice would make every GM command fail under
    # `..._unexpected_TypeError`, a name that blames this module for chief's
    # call shape.  Name the refusal for what it is instead.
    if not isinstance(payload, (bytes, bytearray)):
        _note(session, f"{EVENT_BAD_PAYLOAD_PREFIX}{type(payload).__name__}")
        return None

    outcome = handle_local_talk_chat(
        token, payload, config_path=config_path, log_path=log_path
    )
    # CHAT-TAIL-001, AND IT RUNS SECOND ON PURPOSE.  The first draft of this
    # round split the payload BEFORE this call, and pf-adversary (D1, round
    # `uyzr8c`) measured what that cost: a non-GM's chat line reached a
    # UTF-16 decode, a `session.events` append and a stderr write, which
    # falsifies two `[MEASURED]` sentences that were true on main -- this
    # module's own "a non-GM still causes no write, no decode and no
    # rate-limit charge" and `runtime.py`'s "a non-GM chat line produces
    # stdout='' AND stderr=''".  It also moved an 8 KB decode ahead of the
    # 4096-byte ceiling `MAX_CHAT_PAYLOAD_LENGTH` exists to enforce.
    #
    # Asking the question SECOND costs nothing and keeps every one of those
    # properties, because the refusal we retry on is returned BELOW the
    # identity check, BELOW the size ceiling and ABOVE the rate limiter and
    # the audit writer (`chat_command.handle_local_talk_chat`): reaching it
    # proves the account is on the allowlist, proves the frame is under the
    # ceiling, and spends no limiter slot and writes no audit row that the
    # retry would then duplicate.
    if _is_undecodable_payload(outcome):
        isolated = _isolated_chat_payload(session, payload, legacy)
        if isolated is not payload:
            outcome = handle_local_talk_chat(
                token, isolated, config_path=config_path, log_path=log_path
            )
    if outcome.command is None:
        _note(session, f"{EVENT_REFUSED_PREFIX}{outcome.refusal_reason}")
        _print_command_refusal_way_out(session, token, outcome)
        # The two printers are mutually exclusive by their own reason sets
        # (`TYPED_COMMAND_REFUSAL_PREFIXES` vs `SERVER_SIDE_DROP_REFUSALS`),
        # so a refusal gets one line or none, never two -- asserted by
        # `tests/test_gm_chat_no_bytes_line.py`, not left to reading.
        _print_server_drop_way_out(session, token, outcome)
        # AND, FOR ONE OF THOSE REFUSALS ONLY, A SENTENCE ON THE SCREEN.
        # COO-DECISION `0647`: the two printers above reach the SERVER HOST'S
        # console and nobody else -- which is what every docstring in this
        # module has said about them since round `9wy444` -- so the person who
        # actually mistyped the command still watched their chat line vanish.
        # This is the only line on this branch that answers them.
        #
        # AFTER both printers, never before: the console line is decided by
        # the refusal alone and must not change shape because a codec was
        # unhappy.  `_typo_refused_notice` returns None for every refusal
        # except the parse layer, so this stays `return None` for all of them.
        return _typo_refused_notice(session, legacy, outcome.refusal_reason)

    command = outcome.command
    _note(session, f"{EVENT_ACCEPTED_PREFIX}{command.name}")
    # WIRED-v2 evidence, on the production path, for an authorized command
    # only.  See CONSOLE_TOKEN's own comment.
    #
    # !! STDERR, NOT STDOUT, AND THAT IS NOT A STYLE CHOICE.
    # `lane_hooks/__init__.py` (lines 117-123) records the incident this
    # would otherwise repeat verbatim: when its own console token went to
    # stdout, `tools/pf_runtimeres_death_headless_replay.py --json` gained a
    # stray token line inside its JSON artifact, because that tool's
    # scenario-off control dispatches a chat frame.  Its fix was
    # `file=sys.stderr` (lane_hooks/__init__.py:161).  This route sits on the
    # same 0xAC52 branch, which every client sends freely, so it inherits the
    # same exposure the moment CORE-REQUEST-GM-029 is wired -- found by
    # pf-adversary in round `vvxkft` before that wiring exists, not after.
    #
    # !! AND WRAPPED, FOR THE SAME REASON THE REFUSAL LINE BELOW IS.
    # MEASURED this round by the hostile-console case in
    # `tests/test_gm_chat_warp_way_out.py` (class
    # `TheLineNeverAltersDispatchTests`; the method name is not spelled here
    # because it does not survive a line wrap, which is the citation rot this
    # module's own docstring warns about at 152-155).  With a stderr whose
    # `write` raises, this bare `print` sent the error up through
    # `make_gm_chat_command_action` and the caller's blanket handler recorded
    # `gm_chat_action_unexpected_OSError`: every GM command failing on the
    # console's fault, named after this module.  That is the rule this file
    # quotes elsewhere -- A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- broken by
    # the diagnostic that announces the dispatch.  The evidence token is the
    # courtesy; the command is the product.
    #
    # `None` is checked separately because it is not an error: `print` would
    # quietly write the token to STDOUT (pf-adversary D1), which is the
    # `lane_hooks` JSON-artifact incident above, arriving through the fix for
    # a different one.  And the failure is NAMED, never silent (D5) -- a
    # missing token must not read as "the route was never wired".
    if sys.stderr is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
    else:
        try:
            print(f"{CONSOLE_TOKEN} {command.name} route=action", file=sys.stderr)
        except Exception as error:  # noqa: BLE001 - see the paragraph above
            _note(
                session,
                f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}",
            )

    if command.name == "warp":
        verdict = _warp_action(
            session,
            command,
            legacy,
            token=token,
            gm_accounts_config_path=config_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
    elif command.name == "say":
        verdict = _say_action(session, command, legacy)
    elif command.name == "gmprobe":
        verdict = _gmprobe_action(session, command, legacy)
    elif command.name == "speed":
        verdict = _speed_action(session, command, legacy)
    elif command.name == "lv":
        # PANYA-ORDER 2026-09-06 01:55.  `lv` left the `else` branch below on
        # this round: it is no longer "parsed and audited with no proven
        # wire", it writes `characters.level` and the next login sends it.
        verdict = _lv_action(session, command, legacy, token=token)
    else:
        # Parsed and audited, but this lane has no proven server->client
        # wire for it yet.  Named, not silent: "nothing happened" and "we
        # never built that half" look identical on screen.
        _note(session, f"{EVENT_NO_WIRE_PATH_PREFIX}{command.name}")
        verdict = _Verdict(None, OUTCOME_NO_WIRE_PATH)
        if command.name == "npc":
            _note_npc_recompose_diagnostic(session, command)
        elif command.name == "item":
            _note_item_catalog_diagnostic(session, command)

    action = verdict.action
    # ONE write point for the `outcome` row, deliberately: CORE-REQUEST-GM-032
    # item 1 exists because the audit could not tell a withheld command from a
    # sent one, and an audit whose closing row is appended at four different
    # `return` statements grows a fifth return that forgets it.  Every branch
    # above therefore reports its verdict back here instead of writing.
    audited = _log_outcome(
        session, token, command, outcome.record_id, verdict.audit_outcome, log_path
    )
    # `None` = there was nothing to undo, which is not the same answer as
    # "the undo ran and failed" -- see `_announce_console_outcome`'s own
    # paragraph and `WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT`.
    reverted: bool | None = None
    if not audited:
        # AN EFFECT THAT IS ALREADY ON DISK HAS TO COME BACK OFF IT.  Until
        # the cross-scene warp, every branch above could be "withheld" for
        # free, because withholding meant not returning bytes that had never
        # left this function.  A staged login-scene entry is in
        # `config/gm_login_scene.json` by the time we get here, so the same
        # rule -- no effect this lane could not record -- costs a real undo.
        if verdict.undo is not None:
            try:
                reverted = bool(verdict.undo())
            except Exception:  # noqa: BLE001 - a failed undo must not mask the
                # audit failure that caused it; both are reported as events.
                reverted = False
            _note(
                session,
                EVENT_OUTCOME_STAGE_REVERTED
                if reverted
                else EVENT_OUTCOME_STAGE_NOT_REVERTED,
            )
        # The issued row is on disk and its outcome is not, so this command's
        # audit trail is broken -- and `handle_local_talk_chat` already
        # refuses to hand onward a command it could not record at all, for
        # the same reason.  Withhold the action rather than send bytes whose
        # only record says "a GM typed something".  A withheld or refused
        # command has nothing left to withhold; it just carries the note.
        if action is not None:
            # THE PARKED TARGET HAS TO GO WITH IT.  `_warp_action` parks the
            # destination only after the frame exists, precisely so that "no
            # bytes went out" and "no target is parked" never disagree --
            # chief's confirmation token (CORE-REQUEST-GM-031) compares the
            # next position report against whatever is parked, so a target
            # left behind by a withheld warp would let it measure a real
            # step the player took against a warp that never happened.
            # Withholding here is a new way to reach that state, so it
            # clears it the same way the refusal paths never create it.
            #
            # ONLY FOR THE COMMAND THAT PARKED IT.  A withheld `/say` must not
            # clear the target an EARLIER `/warp` parked and really sent: that
            # would delete a live comparison because an unrelated chat line
            # could not be audited, which is a second bug wearing the first
            # one's clothes.  `say` parks nothing, so it has nothing to undo.
            #
            # ALL THREE WARP LABELS, not just the ForcePos one: the two
            # cross-scene TeleportVital paths (`WARP_CROSS_SCENE_TELEPORT_
            # ACTION_LABEL` via `_warp_teleport_action`, and GM-A's
            # `WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL` via
            # `_warp_teleport_action_no_coords`) each park a target through
            # the same `record_warp_target` call, so a withheld warp of
            # either shape has exactly the same stale-target hazard this
            # branch exists to close for the same-scene one.  This tuple
            # already drifted out of sync once (GM-A added the third label
            # and its own park call without updating this set -- caught by
            # pf-adversary round `zkqaq1`, not by a test); it is not the
            # single shared source of truth for "does this label park a
            # target" and has to be kept in step with the label defs above
            # by hand.
            if action[0] in (
                WARP_ACTION_LABEL,
                WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL,
                WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL,
            ):
                if not clear_warp_target(session):
                    _note(session, EVENT_OUTCOME_STALE_TARGET_NOT_CLEARED)
                if action[0] == WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL:
                    # `CORE-REQUEST-GM-057`'s own park.  ONLY this label's
                    # compose call can have made one (`_persist_warp_scene`'s
                    # only caller, three lines above `undo` in this
                    # function's own branch) -- the other two warp labels
                    # never call `_persist_warp_scene` at all.  `verdict.undo`
                    # has ALREADY reverted the row synchronously by the time
                    # this line runs, and `action` is about to become `None`
                    # on this same branch, so the frame that would have
                    # confirmed or failed the park is never going to be
                    # queued.  Leaving the park would let a LATER, unrelated
                    # send failure on this connection trigger a second,
                    # spurious rollback attempt against whatever the row
                    # holds by then.
                    if not warp_send_watch.clear_warp_send_watch(session):
                        _note(
                            session,
                            EVENT_WARP_SEND_WATCH_STALE_PARK_NOT_CLEARED,
                        )
            # TWO NAMES, because two different things reach this line now.
            # A refusal NOTICE dropped here is not "a composed command frame
            # was withheld" -- that phrase is documented and asserted
            # elsewhere with the narrower meaning -- and it is the case a
            # reader most needs named: on this boot the screen goes silent
            # again (pf-adversary, round `aa9ajr`, D4).  ~~"A withheld or
            # refused command has nothing left to withhold; it just carries
            # the note."~~ struck three lines above: since the refusal
            # notice, a refused command CAN have something to withhold.
            _note(
                session,
                EVENT_OUTCOME_NOT_AUDITED_NOTICE_DROPPED
                if verdict.is_notice
                else EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD,
            )
            # Dropped, not returned -- and the console is told below, on the
            # same call site every other shape uses.  An early `return None`
            # here is how the first version of this round grew two
            # announcers that disagreed (pf-adversary D2/D7).
            action = None
    # THE ONE PLACE THE CONSOLE IS TOLD, and it is AFTER the audit write on
    # purpose: `why` has to be the word the ndjson actually carries, and
    # until this line runs nobody knows whether the row landed.
    _announce_console_outcome(
        session,
        token,
        command,
        verdict,
        audited=audited,
        # Read AFTER the audit-failure branch above, which can set `action`
        # to None: "a notice went out" has to mean the same thing the return
        # value means, or the console gains a line for bytes nobody sent.
        notice_sent=action is not None and verdict.is_notice,
        # `sent` MEANS "THE COMMAND'S OWN FRAME WENT OUT", not "some bytes
        # did".  `_announce_console_outcome` opens with `if sent: return`, so
        # counting an on-screen refusal notice here would delete the
        # `GM_CHAT_NO_BYTES_SENT ... why=... character_id=<rowid>` line that
        # is half (b) of COO-DECISION `0147` -- measured and reported by
        # LANE-GM before this change existed (`pf_bridge/notes_to_chief/
        # 20260902_0419_LANE-GM-REPLY-CHIEF-speed-notice-two-decisions.md`),
        # who also noted that no test in the repo would have caught it
        # because the tests that pin that line stand on `action is None`.
        sent=action is not None and not verdict.is_notice,
        reverted=reverted,
    )
    # CORE-REQUEST-GM-040.  LAST, and only for an action we are really
    # returning.  Arming earlier would pair a callback with an object one of
    # the branches above can still throw away (`audited` False sets `action`
    # to None), and chief's `is` check would then hold a pairing for a frame
    # that was deliberately withheld -- inert, but it would sit on the
    # session until the next command overwrote it, which is exactly the
    # state `EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING` exists to report as an
    # anomaly.  Arming here means "armed" and "returned" are the same
    # decision, taken once.
    #
    # AND NOT FOR A NOTICE.  `log_gm_command_queued` writes the `queued` row
    # that closes this command's `issued` row, and that row means "this
    # COMMAND's frame reached runtime".  A notice frame says the command did
    # NOT run, so pairing `issued`+`queued` around it would produce an audit
    # trail an executed command's is indistinguishable from -- the exact
    # failure CORE-REQUEST-GM-032 item 1 was opened to fix.  If a trace of
    # "the notice went out" is ever wanted, it is a NEW row or token, never
    # `queued` carrying two meanings (LANE-GM, letter `20260902_0419`,
    # question 1; the file is chief's this round, so the shape is his call
    # and this is it).
    if action is not None and not verdict.is_notice:
        _arm_queued_confirm(
            session, action, command, token, outcome.record_id, log_path
        )
    return action


def _arm_queued_confirm(
    session: object,
    action: tuple,
    command: object,
    account_name: str,
    record_id: str | None,
    log_path: str | None,
) -> None:
    """Park `(action, callback)` for chief's append site to fire.

    CORE-REQUEST-GM-040, the half `gm/` owns.  Chief's half is at
    `runtime.py`'s `actions = actions + [gm_action]`: right after the
    append it reads `session._gm_action_queued_confirm`, checks
    `pending[0] is gm_action`, clears the slot, and calls `pending[1]()`.
    So the object we store MUST be the exact tuple `_make_action` returns --
    an equal-but-not-identical copy would never match, and would fail
    SILENTLY (no append, no row, no event), which is the one failure shape
    this function must not have.

    Never raises.  This runs on the listener thread, and the command it
    belongs to has already been authorized, composed and audited; a failure
    to arm a confirmation must cost that command its `queued` row and
    nothing else.
    """
    if not isinstance(record_id, str) or not record_id:
        # `_log_outcome` has already refused and reported this same case
        # (EVENT_OUTCOME_NO_RECORD_ID), and `audited` False means we are not
        # reached with an action anyway.  Belt and braces: a `queued` row
        # whose id closes no issued row is the one row worse than no row.
        return

    fired = []

    def _confirm_appended() -> None:
        # Chief's hook clears the pairing BEFORE calling this, so a second
        # call cannot come from him.  If one arrives anyway, something else
        # is holding this closure, and two `queued` rows for one record_id
        # would read like the command was appended twice.
        if fired:
            _note(session, EVENT_QUEUED_CONFIRM_FIRED_TWICE)
            return
        fired.append(True)
        try:
            if log_path is None:
                log_gm_command_queued(command, account_name, record_id=record_id)
            else:
                log_gm_command_queued(
                    command, account_name, record_id=record_id, log_path=log_path
                )
        except Exception as error:  # noqa: BLE001 - OSError and any encoder
            # Type name only: an exception message can carry the GM's typed
            # text, same rule as every other refusal in this module.  Chief's
            # hook also wraps us (`gm_action_queued_confirm_failed_<Type>`),
            # but relying on that would name the failure in HIS vocabulary
            # for a write that is entirely ours.
            _note(
                session,
                f"{EVENT_QUEUED_CONFIRM_WRITE_FAILED_PREFIX}{type(error).__name__}",
            )

    try:
        if getattr(session, "_gm_action_queued_confirm", None) is not None:
            _note(session, EVENT_QUEUED_CONFIRM_OVERWROTE_PENDING)
        session._gm_action_queued_confirm = (action, _confirm_appended)
    except Exception as error:  # noqa: BLE001 - a session that refuses the
        # attribute (slots, a read-only proxy) must still get its command.
        _note(
            session,
            f"{EVENT_QUEUED_CONFIRM_NOT_ARMED_PREFIX}{type(error).__name__}",
        )


def _log_outcome(
    session: object,
    account_name: str,
    command: object,
    record_id: str | None,
    audit_outcome: str,
    log_path: str | None,
) -> bool:
    """Append the `outcome` row closing this command's `issued` row.

    Returns True when the row is on disk, False when it is not and the
    caller has to decide what that costs.  Never raises: this runs on the
    listener thread, and an audit failure must be a named refusal, not a
    traceback attributed to whatever frame arrived next.

    `record_id` None means `handle_local_talk_chat` returned a command
    without an id, which today is unreachable (it mints one on the only path
    that produces a command).  Treated as a failure rather than papered over
    with a fresh id: an outcome row whose id matches no issued row is worse
    than a missing one, because it reads like a complete pair.
    """
    if not isinstance(record_id, str) or not record_id:
        _note(session, EVENT_OUTCOME_NO_RECORD_ID)
        return False
    try:
        if log_path is None:
            log_gm_command_outcome(
                command, account_name, audit_outcome, record_id=record_id
            )
        else:
            log_gm_command_outcome(
                command,
                account_name,
                audit_outcome,
                record_id=record_id,
                log_path=log_path,
            )
    except Exception as error:  # noqa: BLE001 - OSError and any encoder error
        # Type name only, same reasoning as every other refusal in this
        # module: an exception message can carry the GM's typed text.
        _note(session, f"{EVENT_OUTCOME_LOG_FAILED_PREFIX}{type(error).__name__}")
        return False
    return True


def _warp_action(
    session: object,
    command: object,
    legacy: object,
    *,
    token: str,
    gm_accounts_config_path: str | None,
    login_scene_config_path: str | None,
    scene_registry=None,
) -> _Verdict:
    """`/warp`'s four shapes -- see `_make_action`'s single write point.

    THE ROUTING RULE, IN ONE SENTENCE, AS THIS FUNCTION ACTUALLY ROUTES AT
    HEAD (rewritten in round `07kjfd`; the paragraph it replaced is struck
    below, because pf-adversary D11 measured it describing the PREVIOUS
    round's behaviour on both halves -- and it is the paragraph a reviewer
    reads first):
      * FIRST, ABOVE EVERY ROUTING DECISION (`COO-DECISION 20260904_2045`
        item 1): ANY `warp <n> x y` -- any scene, any shape -- is refused
        while `warp_executor.WARP_TYPED_COORDINATES_AUTHORIZED` ships False.
        ONE READ SITS ABOVE IT and can answer first: a connection with no
        readable position is refused `refused_warp_no_current_position` two
        lines up, because without a current scene this function cannot tell
        the shapes apart at all (pf-adversary, round `vlk8rq`, finding 8 --
        zero bytes either way, but an attended tester greps the console to
        pick a ticket, so the exception is written down rather than implied).
        No
        composer runs, no target is parked, no row is written, no login-scene
        entry is staged; the console names the closure and zero bytes leave.
        The three bullets below therefore describe where a coordinate warp
        WOULD go if that flag were flipped back, and are reached today only
        by a test that patches it.
      * `warp <n> x y` INSIDE the scene the connection is already in is the
        ForcePos half, and it is CLOSED -- `warp_executor.
        WARP_SAME_SCENE_FORCE_POS_AUTHORIZED` ships False after R306
        measured that 45-byte frame closing the client with
        `ErrorData=28317` (COO-DECISION `20260903_1744` item 3).  It refuses
        above the version read and above `_park_warp_target`.
      * `warp <n> x y` naming a DIFFERENT scene is the live cross-scene
        TeleportVital half (`_warp_teleport_action`, gated on
        `warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED`, True).
      * BARE `warp <n>` into any MARKER-BACKED scene -- same scene or a
        different one -- is live: `_warp_teleport_action_no_coords`, aimed at
        that scene's own pinned marker spawn.  The same-scene case became
        live by `PANYA-DECISION 20260903_1800`; it differs from the
        cross-scene case only in which console token gets printed.
      * What is LEFT staging the account's next login scene is exactly one
        thing: a bare `warp <n>` into a MARKERLESS destination
        (17/126/278/997, `n_MARKER == 0`, GT-182 nonclaim 4) -- same scene or
        not, because no live composer has a spawn to put in a frame there.

    ~~THE ROUTING RULE ... UPDATED BY COO-DECISION 2026-08-31T14:41+07:00
    AND THEN BY GM-A (R278): `warp <scene_id> x y` inside the scene the
    connection is already in is the ForcePos half (frozen shut by
    COO-DECISION 20260829_0041 until chief's confirmation token compares
    against the commanded point) ... and every remaining bare-form case
    (same scene, or a markerless destination such as 17/126/278/997) still
    stages the account's next login scene, because neither live composer has
    a position to put in a frame there.~~ Both of those clauses went false
    in round `07kjfd`: the ForcePos half is shut by a DIFFERENT gate than the
    one named (that one is about a confirmation token; this one is about a
    frame that killed a client), and "same scene" left the staging bucket.

    ~~EVERYTHING ELSE ... stages the account's next login scene instead of
    being refused outright.~~ That was true from round `gejldf` (which
    replaced an outright refusal with staging) through COO-DECISION
    20260830_2048 (which held the live cross-scene case shut pending
    `GT-106-R2`).  GT-106-R2 came back PASS and COO-DECISION 1441 lifted the
    lock, so "a different scene, with coordinates" is no longer folded into
    "everything else that stages" -- it is its own branch.  GM-A (this
    round) peels one more slice off "everything else": "a different,
    MARKER-BACKED scene, with NO coordinates" is now its own branch too,
    aimed at the destination's pinned spawn rather than staging.  What is
    left inside "everything else that stages" is smaller than either
    docstring before it described, not gone -- see `warp_no_coords_live_
    target`'s own docstring for exactly which scene ids still fall through.

    THE ORDER CHANGED, AND IT MATTERS TO A READER OF THE AUDIT FILE.  The
    ForcePos version gate used to be the first thing this function read, so
    with the gate shut EVERY warp wrote `withheld_force_pos_vital_version`.
    It is now read only on the branch it actually governs.  A cross-scene
    warp -- staged OR live -- never touches that gate and never claims to
    have been withheld by it: the ForcePos version byte has nothing to do
    with why either cross-scene branch does what it does.  `GT-127`'s
    criteria were rewritten in round `gejldf`, per the owner's stale-entry
    ruling (PANYA-RULING 20260829_0127); this round does not reopen that.
    """
    position = _current_position(session)
    if position is None:
        # Read before the routing decision, not after: without a current
        # scene this function cannot tell its shapes apart, so it must
        # refuse rather than guess which one the GM meant.
        _note(session, EVENT_WARP_NO_POSITION)
        return _Verdict(None, OUTCOME_WARP_NO_POSITION)

    try:
        target_scene_id = warp_command_scene_id(command)
        has_coordinates = warp_command_has_coordinates(command)
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # A malformed `args` shape cannot be routed at all. Type name
        # only, same reasoning as every other refusal here.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(None, f"{OUTCOME_REFUSED_PREFIX}warp_{type(error).__name__}")

    if has_coordinates and not warp_executor.WARP_TYPED_COORDINATES_AUTHORIZED:
        # COO-DECISION `20260904_2045` item 1.  THE ONE POINT, and it is here
        # rather than in any branch below on purpose: below this line
        # `/warp <n> <x> <y>` forks three ways -- cross-scene live
        # TeleportVital (which COMPOSED AND SENT a real 73-byte frame with
        # the GM's typed coordinates until this round: round `741zlx`
        # adversary finding 10, MEASURED, reported in `1930`), same-scene
        # ForcePos (already shut by `WARP_SAME_SCENE_FORCE_POS_AUTHORIZED`),
        # and staging (which writes a login-scene entry).  A closure written
        # per branch would be three closures to keep in step, and finding 10
        # is exactly what happens when one of them is missed.
        #
        # ABOVE `_no_coords_live_target`, `same_scene_with_basis`, both
        # composers, `_park_warp_target`, the durable scene write of
        # `warp_scene_persist` (spelled without its private wrapper's name on
        # purpose -- `test_gm_warp_scene_persist.py::TheBranchesThatCallIt
        # Tests` greps this very function's source for that identifier to
        # prove the ForcePos half never persists) and `_stage_action`.  So a
        # refused coordinate warp leaves NO bytes, NO
        # parked target, NO staged entry and NO row change -- the four things
        # a later reader could otherwise mistake for a warp that happened.
        # The two reads above this line are the command's own text and the
        # connection's current position; neither writes anything.
        #
        # `has_coordinates` is the WHOLE condition on the typed side: the
        # scene comparison deliberately does not appear, because "which scene
        # did they name" is what split the old closure in two.
        _note(session, EVENT_WARP_WITHHELD_TYPED_COORDS_CLOSED)
        return _Verdict(None, OUTCOME_WARP_WITHHELD_TYPED_COORDS_CLOSED)

    if (
        target_scene_id != position.scene_id
        and has_coordinates
        and warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED
    ):
        return _warp_teleport_action(session, command, legacy, position.z)

    # GM-A: the bare (no-coordinates) cross-scene shape now ALSO fires live,
    # but only into a scene `warp_no_coords_live_target` names as
    # marker-backed -- ~~everything else (same scene with no coordinates, or
    # a markerless destination such as 17/126/278/997, GT-182 nonclaim 4)
    # falls through unchanged to the stage-only branch two lines down.~~
    #
    # STRUCK BY THE OWNER, 2026-09-03T17:58+07:00, live in the R307 attended
    # round (`pf_bridge/notes_to_chief/20260903_1800_PANYA-DECISION-warp-to-
    # the-scene-you-are-already-in-must-teleport-to-that-scenes-spawn-not-
    # stage-next-login.md`, carried into this lane's order by `COO-DECISION
    # 20260903_1845`).  "SAME scene with no coordinates" is no longer part of
    # "everything else": `/warp 2` typed while standing in scene 2 now fires
    # the SAME live 73-byte TeleportVital at scene 2's own pinned marker
    # spawn that a cross-scene `/warp 2` fires.  What she measured before
    # this change: the command staged her NEXT login and sent nothing, which
    # mid-session reads as "nothing happened" -- and relogging costs the
    # whole session while the logout buttons are still refused (UI-A/UI-B).
    # Her workaround was `/warp 1` then `/warp 2`, i.e. paying for two live
    # cross-scene teleports to get the one this branch now sends directly.
    #
    # THE SCENE-ID TEST IS GONE FROM THIS CONDITION, NOT INVERTED INTO A
    # SECOND BRANCH.  Both shapes send byte-identical frames built by the
    # same composer from the same registry entry -- a second branch would be
    # two spellings of one behaviour, and the only real difference (which
    # console token an attended tester greps) is carried by `same_scene`
    # below, decided here, in the one function that knows the current scene.
    #
    # WHAT STILL FALLS THROUGH TO STAGING is now exactly one thing: a
    # destination with NO ARRIVAL POINT -- same scene or not.
    # ~~MARKERLESS (17/126/278/997, `n_MARKER == 0`, GT-182 nonclaim 4)~~
    # AMENDED 2026-09-05 (LANE-A round ihjytc): that set is 17/278/997 now.
    # Scene 126's table row still carries `n_MARKER == 0`, but the owner
    # pinned its arrival by decree (`PANYA-DECISION 20260905_1329`), so
    # `warp_no_coords_live_target` resolves it and `/warp 126` takes the live
    # branch.  That function is still the one place that decides which scenes
    # qualify, and GT-141's pinned scene-278 answer is unchanged.
    #
    # THE LOOKUP IS DONE ONCE, HERE, AND ITS ANSWER IS CARRIED (pf-adversary,
    # round `spt6fv`, D3, MEASURED).  It used to be inlined in the condition
    # below and asked a SECOND time in the stage call's argument list, which
    # bought two defects for one fact: `world_scene_travel.destination`
    # re-reads `scenarios/world_scene_registry_001.json` from disk on every
    # call with no cache, so the console's copy of the question doubled the
    # reads on the shipped path AND put an unguarded disk read on the
    # coordinates-bearing path that never had one -- where an `OSError` (a
    # class `warp_no_coords_live_target` does not catch) escaped `_warp_
    # action` entirely and an ACCEPTED command vanished with no console line
    # at all, in the module whose founding property is that it never does
    # that.  `_no_coords_live_target` below cannot raise, so no reading of
    # the registry can take a command down any more, and a read that fails
    # falls CLOSED to staging with its own honest reason.
    live_target, live_target_read = _no_coords_live_target(
        session, target_scene_id, has_coordinates
    )
    # ASKED ONCE, HERE, AND CARRIED (the same discipline as `live_target` one
    # line up and as `same_scene` was before chief's field landed).  Both
    # branches below print a `basis=` word, and they must never disagree
    # about which comparison produced their `same_scene`: one call, one
    # answer, two consumers.
    same_scene, same_scene_basis = same_scene_with_basis(
        session, target_scene_id, position
    )
    if (
        not has_coordinates
        and warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED
        and live_target is not None
    ):
        return _warp_teleport_action_no_coords(
            session,
            target_scene_id,
            legacy,
            same_scene=same_scene,
            same_scene_basis=same_scene_basis,
            # THE RELOG HALF (`COO-DECISION 20260905_1746` item 4).  These
            # four are the SAME values `_stage_action` below is handed, from
            # the same reads, for the same reason its own docstring gives:
            # the account this may stage for has to be the account
            # `handle_local_talk_chat` already authorized, out of the same
            # allowlist file.  Passing the defaults here instead would let a
            # listener booted with `PF_GM_ACCOUNTS_CONFIG` authorize against
            # one allowlist and write against another.
            token=token,
            gm_accounts_config_path=gm_accounts_config_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )

    if target_scene_id != position.scene_id or not has_coordinates:
        return _stage_action(
            session,
            target_scene_id,
            has_coordinates,
            token=token,
            gm_accounts_config_path=gm_accounts_config_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
            # DECIDED HERE, in the one function that reads the current scene,
            # for the same reason `same_scene` on the live branch above is
            # (`COO-DECISION 20260903_2050` item 2).  It changes the console
            # sentence and nothing else: a markerless `/warp` stages the same
            # entry either way.  The comparison itself moved into
            # `same_scene_with_basis` above the branch, so the staged line
            # and the sent line answer this from ONE read on ONE basis
            # (chief's `client_confirmed_scene` when the client has ever
            # spoken, the server's own label when it has not).
            same_scene=same_scene,
            same_scene_basis=same_scene_basis,
            # WHICH BLOCKER ACTUALLY HELD THIS COMMAND'S FRAME -- not "what
            # does this destination lack", which is a different question and
            # the one the first draft answered (pf-adversary, round `spt6fv`,
            # D1, MEASURED).  `staged_blocker` reads the answer the routing
            # above already got; see that helper for why a coordinates-
            # bearing warp can never be blocked by a missing arrival marker.
            blocker=_staged_blocker(
                has_coordinates=has_coordinates,
                live_target=live_target,
                live_target_read=live_target_read,
            ),
        )

    if not warp_executor.WARP_SAME_SCENE_FORCE_POS_AUTHORIZED:
        # COO-DECISION `1744` item 3 / `1845` item 3, from R306's cross-lane
        # finding 3: this frame closed the owner's client with
        # `ErrorData=28317`.  Refused HERE, above the version read, so the
        # console line names the R306 measurement rather than RE-129 -- the
        # byte is not what is wrong, and an attended tester sent to the wrong
        # ticket by a `why=` word is the whole reason this route prints one.
        #
        # ABOVE the composer and above `_park_warp_target`, so this refusal
        # cannot leave a parked target behind for chief's confirmation token
        # to compare a real step against (the hazard `_park_warp_target`'s own
        # docstring names).  Nothing below this line runs.
        #
        # !! WHAT THIS SHADOWS, WRITTEN DOWN BECAUSE NOTHING ELSE RECORDS IT
        # (pf-adversary, round `07kjfd`, D12).  With this gate shipped False
        # and read FIRST, every line below is now unreachable on a real boot:
        # `EVENT_WARP_WITHHELD_NO_VERSION`, `OUTCOME_WARP_WITHHELD_NO_VERSION`,
        # `make_warp_force_pos_frame_with_target`, `WARP_ACTION_LABEL` and its
        # entries in `_make_action`'s stale-target-clear tuple and in
        # `runtime.py`'s `_GM_WARP_LABELS`.  Their tests all reach them
        # through a patched flag, so they are green because they are never
        # got to -- not because a boot proves them.  That is the honest state
        # of RE-129's gate while COO's closure stands, and the round that
        # reopens this gate inherits, not discovers, that fact.
        _note(session, EVENT_WARP_WITHHELD_FORCE_POS_CLOSED)
        return _Verdict(None, OUTCOME_WARP_WITHHELD_FORCE_POS_CLOSED)

    version = teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED
    if version is None:
        # RE-129.  Refusing here is the whole safety property: GT-101
        # measured an unproven vital version killing the owner's session.
        _note(session, EVENT_WARP_WITHHELD_NO_VERSION)
        return _Verdict(None, OUTCOME_WARP_WITHHELD_NO_VERSION)

    try:
        pc, frame, target = make_warp_force_pos_frame_with_target(
            legacy, version, command, position.scene_id, position.z
        )
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # Covers the cross-scene refusal, the scene-only `warp <id>` form
        # with no position to carry, and every malformed-argument case
        # warp_executor re-validates.  Type name only, same reasoning as
        # above -- a WarpExecutorError message embeds the typed arguments.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(
            None, f"{OUTCOME_REFUSED_PREFIX}warp_{type(error).__name__}"
        )

    if not _park_warp_target(session, target):
        _note(session, EVENT_WARP_TARGET_NOT_RECORDED)

    return _Verdict((WARP_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED)


def _park_warp_target(session: object, target) -> bool:
    """Park the destination for the reader of the NEXT position report.

    Shared by both composing branches of `/warp` (same-scene ForcePos and
    live cross-scene TeleportVital) so the rule stays written once: called
    AFTER the frame exists, never before -- a refusal leaves no bytes on the
    wire, so it must leave no target either, or chief's confirmation token
    (CORE-REQUEST-GM-031) could measure a position row against a warp that
    never went out.

    Nothing is claimed by the parking itself, and no event is emitted for
    success: `EVENT_ACCEPTED_PREFIX` above already names the accepted
    command once, and a second line per warp saying only "the module
    remembered where it sent you" is console noise that reads, wrongly,
    like an extra step succeeding.  The caller names the FAILURE case,
    because a session that could not hold the record still gets its warp
    and that loss deserves a reason in the trail.
    """
    return record_warp_target(session, target, current_character_id(session))


def _persist_warp_scene(session: object, target: object) -> tuple:
    """Make the destination scene durable NOW, and name what happened.

    Returns `(outcome, undo, previous_row)`.  The annotation said `str` and
    had said so since the undo was added a round earlier -- corrected here
    rather than left, since this round adds a third element to the same
    tuple and a wrong annotation over a widened return is worse than a wrong
    annotation over a stable one.

    `PANYA-DECISION 20260904_1430`, routed here by `COO-DECISION 20260904_1452`
    item 2: a live warp must write `character_positions` in the same breath as
    the TeleportVital goes out, never wait for the next `TargetPos`.  R309
    measured the gap it closes -- warp, close the client without walking, and
    the next login came back to the scene the character had LEFT.

    CALLED FROM ONE BRANCH ONLY -- the no-coordinate TeleportVital, which is
    the send point `COO 1452` named (`LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_
    TELEPORT_VITAL`, the `/warp 2` the owner measured in R309).  ~~from the two
    teleport branches~~ -- struck in the same round; see
    `_warp_teleport_action`'s own block for what the second one cost.

    NEVER FROM THE FORCEPOS BRANCH, and the difference is not tidiness.  A
    TeleportVital is measured to move a real client's screen (`GT-106-R2`);
    RE-129 measured the client's ForcePos handler as `mov al,1; ret 4`, i.e.
    it ignores the frame entirely.  Persisting there would move the row to a
    point the client is known NOT to have gone to -- the exact
    row-disagrees-with-screen state `1430` is complaining about, inverted.

    Called AFTER the frame exists.  IT IS NOT CONDITIONAL ON
    `_park_warp_target`, and that is stated rather than implied: pf-adversary
    read the first draft's comment as a claim that it was.  A failed park
    costs the CONFIRMATION MACHINERY (nothing downstream can compare the
    client's next report against this destination); it is not evidence the
    frame was refused, and a warp whose frame exists still has a destination
    the row should name.  A refusal is a different thing entirely and returns
    long before this line.

    The outcome word is returned as well as noted so a caller that wants to
    branch on it can, and so the pinning tests do not have to read
    `session.events` to know what this call decided.

    AND IT HANDS BACK AN UNDO, WHICH IS NEW AND IS NOT OPTIONAL.  pf-adversary
    round `741zlx` finding 1 (CRITICAL, MEASURED): `_make_action` withholds
    this very action when the `outcome` row cannot be appended, and it already
    runs `verdict.undo` for exactly that case -- but this handler had always
    returned `undo=None`, so the durable write stayed while ZERO bytes went
    out.  The pre-warp row is captured BEFORE the write, because after it
    there is nothing left to capture, and the undo is offered only when there
    is both a row to go back to and a write that really happened.  `None`
    otherwise: an undo that cannot put anything back must not be advertised,
    since `_make_action` reports `EVENT_OUTCOME_STAGE_REVERTED` on the
    strength of it.
    """
    previous = row_before_warp(session)
    outcome = persist_warp_scene(session, target)
    _note(session, f"{EVENT_WARP_SCENE_PERSIST_PREFIX}{outcome}")
    if outcome != WARP_SCENE_OUTCOME_PERSISTED or previous is None:
        # Nothing durable changed (or nothing was captured to change back to),
        # so there is nothing to undo and nothing to claim.
        return outcome, None, None

    def _undo() -> bool:
        result = rollback_warp_scene(session, previous)
        _note(session, f"{EVENT_WARP_SCENE_ROLLBACK_PREFIX}{result}")
        return result == WARP_SCENE_OUTCOME_ROLLED_BACK

    # THE THIRD RETURN VALUE, added round `ff30oi`: `previous` is the row the
    # SEND-failure undo needs too, and it is only correct here.  Read later
    # from `session.foundation.selected.position` it is the last position the
    # CLIENT reported, which a warp does not update -- so after a second warp
    # on the same connection it names a scene two warps back.  Handing it to
    # `park_warp_send` is cheaper than making the observer guess.
    return outcome, _undo, previous


def _warp_teleport_action(
    session: object,
    command: object,
    legacy: object,
    z: float,
) -> _Verdict:
    """The cross-scene half of `/warp` WITH coordinates: a live TeleportVital.

    COO-DECISION 2026-08-31T14:41+07:00 (`pf_bridge/notes_to_chief/
    20260831_1441_COO-DECISION-warp-cross-scene-opens-gt106r2-passed.md`)
    lifted the stage-only lock `COO-DECISION 20260828_2130`/`20260830_2048`
    held for exactly this shape, once `GT-106-R2` (OBSERVER_CONFIRMED
    2026-08-31T10:0x+07:00) proved a real client renders the destination
    scene when `legacy.make_login_teleport` fires mid-session.  See
    `warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED` for the gate
    this function's only caller (`_warp_action`) checks before routing here,
    and why it is a named boolean rather than a version constant -- this
    function does not re-check it, the same way `_stage_action` does not
    re-check the allowlist its own caller already checked.

    THE BARE `warp <scene_id>` FORM (no x/y) NEVER REACHES THIS FUNCTION --
    `_warp_action` only calls it when `warp_command_has_coordinates` is
    True.  There is no position here to put on the wire for that shape, and
    this lane does not invent a spawn point (see
    `warp_executor.make_warp_teleport_frame_with_target`'s own refusal, kept
    as a second, independent guard in case that routing is ever wrong).

    NO SEND MECHANISM IS NEW HERE, ON PURPOSE.  This returns a
    `(label, pc, frame, delay)` tuple through the exact same `_Verdict` ->
    `_make_action` -> `make_gm_chat_command_action` -> `runtime.py` action-
    list pipe every other command in this module already uses -- the same
    pipe `WARP_ACTION_LABEL`'s ForcePos frame has used since RE-129's byte
    shipped.  No new call site in `runtime.py` was needed to land this
    (checked before writing this function: chief's zone was not touched).

    NONCLAIM, same shape as `_warp_action`'s own G-OBS rule.  Composing and
    returning this frame is evidence bytes went out correctly-shaped; it is
    not evidence any particular destination renders.  GT-106-R2 confirmed
    scene 17 through a DIFFERENT call site (`_dispatch_columbus_quest3021`,
    fixed X=834 Y=-598) -- this is `/warp`'s FIRST live cross-scene send,
    never itself attended-tested.  Every destination this command can now
    reach needs its own attended, client-observable pass before anyone
    calls it PASS.  RE-162 also found the destination scene's census/actor
    frame does not follow a mid-session TeleportVital -- not even chief's
    own Columbus dispatch sends one -- and this path inherits that exact
    gap, does not close it, and does not claim to.
    """
    try:
        pc, frame, target = make_warp_teleport_frame_with_target(legacy, command, z)
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # Same reasoning as every other refusal here: type name only, never
        # the exception message, which can embed the GM's typed arguments.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(None, f"{OUTCOME_REFUSED_PREFIX}warp_{type(error).__name__}")

    if not _park_warp_target(session, target):
        _note(session, EVENT_WARP_TARGET_NOT_RECORDED)
    # NO DURABLE WRITE ON THIS SHAPE.  ~~`_persist_warp_scene(session, target)`
    # -- `1430` applies to this shape too, even though `COO 1452` item 4 says
    # `/warp <n> <x> <y>` is still closed by `1744` item 3: the branch is live
    # in code, so leaving it out would rebuild the gap the day it reopens.~~
    # STRUCK IN THE ROUND THAT WROTE IT (`q3cde9`), not deleted, because a
    # reader of `#745` needs to see why it stopped being the reasoning.
    # pf-adversary measured what it cost, end to end through the real router
    # and the real store: `/warp 126 <x> <y>` wrote `scene_id=126` with the GM's
    # typed x/y and the DEPARTURE scene's z, scene 126 is pinned
    # `login_entry_allowed=False`, and the next login was refused
    # `scene_not_allowed_at_login` -- with only a login able to rewrite the row.
    # R306 also measured this shape making the client close itself, so no
    # TargetPos ever arrives to correct it.  Before this round the row was
    # untouched and the character survived; the "improvement" took that away,
    # which CHARTER-02 rule 2 forbids outright.
    #
    # And the premise was simply wrong: `1744` item 3's closure was implemented
    # on the ForcePos route only (see `EVENT_WARP_WITHHELD_FORCE_POS_CLOSED`'s
    # own comment, "the SAME-SCENE ForcePos shape is shut by POLICY").  This
    # cross-scene-with-coordinates route has no closure at all, so it is not
    # dormant code -- it is a live command, and `COO 1452` item 4 said do not
    # touch it.  Persisting here needs COO's own ruling, not this lane's.

    return _Verdict(
        (WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED
    )


def _warp_teleport_action_no_coords(
    session: object,
    scene_id: int,
    legacy: object,
    *,
    same_scene: bool = False,
    same_scene_basis: str = SAME_SCENE_BASIS_FIELD,
    token: str | None = None,
    gm_accounts_config_path: str | None = None,
    login_scene_config_path: str | None = None,
    scene_registry=None,
) -> _Verdict:
    """GM-A: the half of `/warp` WITHOUT typed coordinates.

    ~~the cross-scene half~~ -- struck 2026-09-03 by `PANYA-DECISION 1800`
    (see `_warp_action`'s own record of it): this function now serves the
    same-scene bare `/warp <n>` too, and the two cases differ in exactly one
    observable way, `same_scene`.

    `same_scene` DECIDES A CONSOLE TOKEN AND NOTHING ELSE, and
    `same_scene_basis` decides one WORD on that token's line -- on whose
    authority the first was answered (`same_scene_with_basis`).  Neither is
    read by the frame builder, neither reaches the wire, and neither can
    change which bytes go out -- both shapes send the same 73-byte TeleportVital aimed at
    `scene_id`'s own pinned marker spawn, which is the whole reason the
    owner's decision could be served by widening one branch instead of
    opening a second wire path.  It is passed in rather than re-derived here
    because `_warp_action` already read the connection's current position
    (it has to, to route at all) and a second read could disagree with the
    first one across an intervening client update.

    Sibling of `_warp_teleport_action` above -- same `_Verdict` shape, same
    `_park_warp_target`/audit discipline, same "no new runtime.py call site"
    property (this still goes through the one action-list pipe every
    command in this module already uses).  The one real difference is the
    frame builder it calls: `make_warp_teleport_frame_no_coords_with_target`
    takes only a `scene_id` (no `command`, no caller-supplied `z`) because
    there is no typed x/y for this shape to carry -- the destination's own
    `world_scene_travel`-pinned marker spawn supplies all three coordinates.

    ONLY REACHED when `warp_no_coords_live_target(scene_id)` is not None --
    `_warp_action` checks that before routing here, and this function
    re-derives the same target through the frame builder's own call to it
    rather than trusting the caller's check, the same double-check
    discipline `_warp_teleport_action`'s sibling functions already use.

    NONCLAIM, identical in kind to `_warp_teleport_action`'s own: composing
    and returning this frame is evidence the bytes went out correctly
    shaped for the destination's pinned marker point; it is not evidence
    any particular destination renders, or that the marker's geometry is
    walkable (`GT-182`'s own nonclaim 1). This shape has never been
    attended-tested -- `GT-182` is the paired ticket an attended round must
    close before this claims anything about the client's screen.
    """
    try:
        pc, frame, target = make_warp_teleport_frame_no_coords_with_target(
            legacy, scene_id
        )
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # Same reasoning as every other refusal here: type name only, never
        # the exception message.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(None, f"{OUTCOME_REFUSED_PREFIX}warp_{type(error).__name__}")

    if not _park_warp_target(session, target):
        _note(session, EVENT_WARP_TARGET_NOT_RECORDED)
    # THE BRANCH `COO 1452` NAMED.  This is the send point behind
    # `LANE_GM_CHAT_WARP_CROSS_SCENE_NO_COORDS_TELEPORT_VITAL`, i.e. the
    # `/warp 2` the owner measured in R309, and the same call serves the
    # same-scene shape `PANYA-DECISION 20260903_1800` widened this function to
    # carry: that shape also sends a real TeleportVital to the scene's pinned
    # spawn, so its row has to move to the spawn too or a tester who warps in
    # place and closes the client lands back at the old coordinates.
    # THE UNDO IS CARRIED, not discarded (pf-adversary round `741zlx`, finding
    # 1, CRITICAL, MEASURED).  This branch has changed durable state by the
    # time it returns, which is precisely the condition `_Verdict.undo`'s own
    # docstring reserves the field for -- and `_make_action` already runs it
    # for the one case that needs it (the `outcome` row could not be appended,
    # so the action is withheld and nothing goes out).  Before this round the
    # field stayed `None` here, so a withheld `/warp 2` left the row in the
    # destination scene with zero bytes on the wire and the next login landed
    # somewhere the client had never been sent.
    _outcome, undo, previous_row = _persist_warp_scene(session, target)
    # `CORE-REQUEST-GM-057`.  The row just moved durably; until this
    # connection's socket layer confirms `frame` reached the wire (or fails
    # to -- see `gm/warp_send_watch.py`'s own docstring for why that side
    # does not need these exact bytes back), the row and the client's real
    # scene can disagree the same way `1430`'s own bug did before this
    # module existed.  Parked ONLY on `OUTCOME_PERSISTED`: every other
    # outcome already means nothing durable changed, so there is nothing
    # this connection is owed a send confirmation for.
    if _outcome == WARP_SCENE_OUTCOME_PERSISTED:
        # `CORE-REQUEST-GM-059` (pf-adversary D1, MEASURED, round `bdl0w3`).
        # The park carries TWO pre-warp values, because there are two and they
        # can disagree: `previous_row` is the durable `character_positions`
        # row, and this is the IN-MEMORY scene label.  `lifecycle.py:311`
        # writes the durable row only when the registry allows it for that
        # scene while `FoundationSession.checkpoint` updates `selected`
        # regardless, so a session in scene 17 has an in-memory 17 over a
        # durable row naming another scene.  `warp_send_watch` undoes an
        # in-memory relabel, so it needs the in-memory value; handed the
        # durable one it restored a scene the session was never in.
        #
        # READ HERE, AND ONLY HERE, BECAUSE OF WHEN "HERE" IS.
        # `_persist_warp_scene` has already put `selected` back the way it
        # found it (`warp_scene_persist._restore_selected`), and
        # `runtime.py`'s `_gm_warp_resync_selected_scene` does not run until
        # later in the same dispatch -- so this is the last instant at which
        # the true pre-warp label is still readable, and the observer that
        # needs it runs long after the relabel.
        if not warp_send_watch.park_warp_send(
            session, frame, previous_row, _selected_scene_id(session),
        ):
            _note(session, EVENT_WARP_SEND_WATCH_NOT_PARKED)
    else:
        # THE RELOG HALF, `COO-DECISION 20260905_1746` item 4.  The frame is
        # already built and about to move the ship on screen; the durable row
        # was refused.  For a sanctioned-barred scene (126 today, and only
        # because a chief letter names it) the relog is arranged through the
        # single-use login entry instead, so `PANYA 1329` (live) and
        # `PANYA 1430` (still there after a relog) are both served without
        # opening the login door `COO 20260829_1444` shut.
        #
        # ELSE, NOT A SECOND `if`, and the difference is the whole guard: this
        # runs on outcomes that are NOT `persisted`, so a warp whose row DID
        # move can never also stage an entry.  Two sources of truth for the
        # same login is the defect this branch is shaped to make unreachable.
        #
        # Its outcome word is noted, never branched on: every one of them
        # means the frame still goes out, and the console already carries the
        # two lines a tester reads.
        # `stage_relog_entry_after_refused_persist` cannot raise, so nothing
        # here can take down a composed command.
        relog = warp_relog_stage.stage_relog_entry_after_refused_persist(
            _outcome,
            scene_id,
            token,
            gm_accounts_config_path=gm_accounts_config_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
        _note(session, f"{EVENT_WARP_RELOG_STAGE_PREFIX}{relog.outcome}")
        # ITS UNDO IS CARRIED, and it is the whole reason the call returns a
        # result object instead of a word.  `undo` reached this branch as
        # `None` -- `_persist_warp_scene` offers one only for `persisted`, and
        # this branch is everything else -- so before this line a `/warp 126`
        # that `_make_action` WITHHELD (an `outcome` audit row that cannot be
        # appended: a full disk, a read-only capture directory) left the
        # staged entry on disk with ZERO BYTES on the wire, and the next login
        # put the character into 126 off a command that never reached it.
        # Same shape as pf-adversary's round `741zlx` finding 1, arriving
        # through the door this round opened, so it is closed in the same
        # round rather than reported.
        #
        # NO `or`, NO CHAINING: the two undos are never both present here.
        # `undo` is None on every outcome this branch can see, and
        # `relog.undo` is None unless an entry was really written.
        undo = relog.undo

    return _Verdict(
        (WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL, pc, frame, 0.0),
        OUTCOME_COMPOSED,
        undo=undo,
        same_scene_teleport=same_scene,
        same_scene_basis=same_scene_basis,
    )


def _one_line(text: str) -> str:
    """Keep an operator-controlled field from forging console LINES.

    `console_safe` folds ENCODING, not structure, so a newline in an account
    name passed straight through and the field could spell a whole second
    line -- including `GM_LOGIN_SCENE_CONFIG_REFUSED`, the OTHER lane's grep
    token, with attacker-chosen fields after it (pf-adversary D9, measured
    through the real dispatch).  That is precisely the property
    `test_its_token_is_not_the_config_loaders_token` claims: an operator
    hunting a malformed config must not have to sift this route's lines out
    of the same search.

    Operator-side input, so this is not a client-reachable attack -- it needs
    a newline in `gm_accounts.json` or in `--token`.  Fixed anyway because
    the claim is the lane's own, and a fold that stops at encoding is the
    same half-measure this file has now been burned by twice.
    """
    return text.replace("\r", "\\r").replace("\n", "\\n")


def _identity_fields(session: object, stream: object) -> str:
    """`character_id=<n|none> identity=<lo>:<hi>|none` for a console line.

    ONE BUILDER FOR EVERY LINE THAT CARRIES THEM, so the two printers that
    answer `COO-DECISION 2026-09-02T01:47+07:00`'s identity requirement
    cannot drift into two spellings of the same fact.

    WHY THE READ HAPPENS HERE RATHER THAN BEING PASSED IN, corrected by
    pf-adversary (round `c637o1`): the first version of this comment argued
    that a caller-supplied identity "could disagree with the one the handler
    wrote against", which has the argument backwards -- passing a value down
    cannot disagree with itself, and re-reading is the only one of the two
    that could.  The real reason is narrower and still good: one of the two
    call sites (`_print_server_drop_way_out`) runs for refusals produced
    BEFORE any handler ran, so there is no handler value to be handed, and a
    single builder that always reads is simpler than one that sometimes
    does.  The read is safe to repeat because this server is strictly serial
    (`pf_bridge/FINDINGS_R18_SERVER_IS_STRICTLY_SERIAL.md`) and neither
    `close` nor `checkpoint` clears or renumbers `.selected`.

    WHAT THESE FIELDS ARE, AND WHAT THEY ARE NOT -- stated because the first
    draft of this round oversold them and pf-adversary (D5) measured the
    gap.  They name the CHARACTER ROW this connection has selected: the row
    `/speed` writes and the row a `GT-193` grader diffs.  They do NOT
    identify a connection.  Two connections that selected the same character
    print byte-identical fields (`store.select_character` has no exclusivity
    check, and every connection shares the process-wide `--token`), and
    `identity_hi` is `0` for every character this server has ever created
    (`lifecycle.py`), so `identity=<lo>:0` is a restatement of
    `account_id`+`selector`.  The claim this supports is "WHICH ROW", not
    "WHO".

    SANITISED LIKE EVERY OTHER FIELD ON THE LINE.  Both values are
    lane-authored `int`s today (`type(...) is not int` excludes `bool`,
    `str`, and int subclasses at both read sites), so `console_safe`/
    `_one_line` cannot currently change them -- they are applied anyway
    because pf-adversary (D7) is right that being the only unsanitised
    fields on a line is a discipline hole, not a proof of safety, and
    because a `str()` of a huge int is the one shape that could raise
    INSIDE a printer whose whole contract is that it never does.
    """
    character_id = _selected_speed_character_id(session)
    identity_lo, identity_hi = _selected_speed_identity(session)
    identity = (
        "none"
        if identity_lo is None or identity_hi is None
        else f"{identity_lo}:{identity_hi}"
    )
    rendered_id = "none" if character_id is None else str(character_id)
    return (
        f"character_id={console_safe(_one_line(rendered_id), stream)} "
        f"identity={console_safe(_one_line(identity), stream)}"
    )


def _print_command_refusal_way_out(
    session: object,
    token: str,
    outcome: object,
) -> None:
    """Name what a mistyped GM command should have been.

    D8, ruled on by COO-DECISION 20260829_1344.  `/warp 9999` has had a way
    out since round `c48x1n`; `/warp island`, a bare `/warp`, `/warp 3 100`
    and `/nonsense` had none -- the refusal happens at the parse layer,
    upstream of every printer this module owns, so the tester who does not
    know `scene_id` is a number saw a chat line vanish and nothing else.

    !! IT NEVER PRINTS WHAT WAS TYPED, and that is this line's single most
    important property.  The first version printed the parse error's own
    message, which quotes the offending token.  pf-adversary (round
    `9wy444`, D1) measured what that means on the WIRED server:
    `runtime.py:5140-5150` says `session.token` is the process-wide
    `--token`, not a per-connection login, so every connection shares one
    identity -- and any player's chat line would have been printed here
    under the operator's own GM account, by a lane whose founding rule is
    that a non-GM's chat is never written anywhere.  `refusal_hint` now
    carries only text this lane wrote (see its contract in `chat_command`).

    WHO THIS REACHES, stated next because the same claim was got wrong here
    once already (pf-adversary D7, `_print_warp_way_out`'s docstring): the
    SERVER HOST'S CONSOLE, and nobody else.  It is not a reply to the person
    typing, and this lane cannot send one until the server->client channel
    behind `/say` opens (COO-DECISION 20260829_1344 keeps that shut and
    keeps `CORE-REQUEST-GM-036` shut with it).  What it buys is that an
    operator watching stderr can tell a typo from a dead route, which before
    this round they could not do at all.

    WHICH REFUSALS, and the list is NOT kept here:
    `chat_command.TYPED_COMMAND_REFUSAL_PREFIXES` owns it, beside the
    refusal constants themselves, so a refusal added to that module cannot
    inherit "no way out" by default.  In particular a non-GM's chat and a
    GM's ordinary conversation are not in it and must never be: this lane
    never decoded the first, and printing the second would put a console
    line under every sentence a GM says.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- the same rule, held the same
    way as `_print_warp_way_out`: the refusal is already decided and this
    function's caller returns None whatever happens in here; everything that
    can raise is inside the guard; the guard catches `Exception` (a closed
    stream raises `ValueError`, an unmappable one `UnicodeEncodeError`, not
    `OSError`); a `None` stderr returns rather than letting `print` fall
    back to STDOUT and drop a GM token into another tool's `--json`
    artifact; and a console that cannot be written is NAMED, because "the
    console is broken" and "the route was never wired" must not look alike
    to an attended run.
    """
    reason = getattr(outcome, "refusal_reason", None)
    if not isinstance(reason, str):
        return
    if not reason.startswith(TYPED_COMMAND_REFUSAL_PREFIXES):
        return
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        hint = getattr(outcome, "refusal_hint", None)
        # A refusal in the set with no hint is a bug in this lane, not a
        # reason to print nothing: the operator still learns that a command
        # was refused and which refusal it was, which is the half that was
        # missing.  Named rather than blank so it cannot be read as "the GM
        # typed an empty explanation".
        described = hint if isinstance(hint, str) else "no usage recorded"
        # CAPPED HERE, not only where the hint is built.  `usage_hint_for`
        # returns one of seven fixed sentences, so today nothing can exceed
        # this -- but this function reads its fields with `getattr` off an
        # arbitrary object (that is its real call shape, see
        # `ThePrinterFoldsWhatItIsHandedTests`), and a cap that lives only in
        # one of several suppliers is a property of that supplier, not of
        # this line.  pf-adversary D10.
        if len(described) > MAX_CONSOLE_HINT_LENGTH:
            described = described[:MAX_CONSOLE_HINT_LENGTH] + "..."
        print(
            f"{COMMAND_REFUSED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"reason={reason} "
            f"usage='{console_safe(_one_line(described), stream)}'",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _print_server_drop_way_out(
    session: object,
    token: str,
    outcome: object,
) -> None:
    """Say that the SERVER dropped a well-formed GM command, and why.

    THE THIRD WAY OUT, and the gap it closes was measured, not guessed.
    pf-adversary (round `c637o1`, D1) ran 25 rapid `/speed 400` frames
    through the real route: 20 printed `LANE_GM_CHAT_ACTION`, and the five
    the limiter dropped printed NOTHING AT ALL -- not this module's
    `GM_CHAT_NO_BYTES_SENT` (they never reached a handler) and not
    `GM_CHAT_COMMAND_REFUSED` (they were not typing mistakes, so
    `TYPED_COMMAND_REFUSAL_PREFIXES` correctly declines them).  From an
    attended chair that is indistinguishable from "the route was never
    wired", which is the state `COO-DECISION 2026-09-02T01:47+07:00` names
    as forbidden rather than merely unwanted.

    WHICH REFUSALS, and the list is NOT kept here:
    `chat_command.SERVER_SIDE_DROP_REFUSALS` owns it, beside the constants
    themselves, exactly as `TYPED_COMMAND_REFUSAL_PREFIXES` does for the
    typo half -- so a refusal added to that module cannot inherit "no way
    out" by default.  Every member of that tuple is returned BELOW the
    `is_gm` check, which is what makes printing it safe: this lane still
    never says a word about a non-GM's chat, about a GM's ordinary
    conversation, about an unreadable allowlist, or about a malformed frame.
    That tuple's own comment lists those four and says plainly that they
    remain silent.

    IT NEVER PRINTS WHAT WAS TYPED -- the property both sibling printers
    spend their docstrings on, and the reason this one prints no command
    NAME either: two of the three members are returned before
    `parse_gm_command` has run, so there is no lane-authored name to render
    and the only string in reach would be the GM's own text.  The `why=`
    word answers the operator's question without it.

    IT CARRIES THE CONNECTION'S IDENTITY for the same reason
    `_print_no_bytes_way_out` does -- see that function's own paragraph on
    why `account=` is not identity.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- held exactly as the two sibling
    printers hold it: the refusal is already decided and the caller returns
    None whatever happens here; everything that can raise is inside the
    guard; a `None` stderr returns rather than letting `print` fall back to
    STDOUT; a console that cannot be written is NAMED on the event trail.
    """
    reason = getattr(outcome, "refusal_reason", None)
    if not isinstance(reason, str):
        return
    if not reason.startswith(SERVER_SIDE_DROP_REFUSALS):
        return
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        blocker = next(
            (
                sentence
                for prefix, sentence in SERVER_DROP_BLOCKERS
                if reason.startswith(prefix)
            ),
            NO_BLOCKER_RECORDED,
        )
        if len(blocker) > MAX_CONSOLE_HINT_LENGTH:
            blocker = blocker[:MAX_CONSOLE_HINT_LENGTH] + "..."
        print(
            f"{DROPPED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"why={console_safe(_one_line(reason), stream)} "
            f"blocked_on='{console_safe(_one_line(blocker), stream)}' "
            f"{_identity_fields(session, stream)}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _print_warp_way_out(
    session: object,
    token: str,
    scene_id: int,
    reason: str,
    scene_registry=None,
) -> bool:
    """Name the destinations a refused chat `/warp` could have used instead.

    WHO IS STANDING WHERE WHEN THIS IS READ -- stated first, because the
    first version of this docstring got it wrong and pf-adversary (D7) was
    right to call the error the load-bearing one.

    The CONFIG path has had a way out since round `qq0i9u`: a malformed
    `gm_login_scene.json` prints the file, the account, the scene and the
    admissible ids (`login_scene_override.CONFIG_REFUSED_CONSOLE_TOKEN`).
    The CHAT path printed nothing.  What this closes is the CONSOLE-WATCHER's
    half of that gap: whoever is already reading the server's stderr now gets
    the current admissible set at the moment of refusal, instead of stopping
    to open `GAME_TEST_QUEUE.md` or read a gitignored config.

    !! IT DOES NOT REACH THE TESTER AT THE GAME CLIENT, and the earlier
    claim that it did was self-defeating: this writes to the server host's
    stderr, and anyone who can read that is ON the server host and therefore
    has the shell the argument said they lacked.  A way out that arrives at
    the client needs a server->client reply, which is blocked behind the same
    identity and vital-version locks as `/say` (see `_say_action`).  Until
    that exists, this is a convenience for the operator, not a fix for the
    tester -- and `GT-141` still tells the tester the set in prose.

    ONLY THE REASONS A DIFFERENT DESTINATION WOULD FIX, and the list is not
    kept here.  `login_scene_stage.DESTINATION_SHAPED_REASONS` owns it,
    beside the constants themselves, so a new refusal reason added upstream
    cannot silently inherit "no way out" (pf-adversary D3 measured exactly
    that happening).  The excluded reasons are three server-side faults --
    where naming a scene would blame the tester's typing for something no
    typing can fix -- and the allowlist re-check.

    !! THE ALLOWLIST EXCLUSION IS NOT A DISCLOSURE CONTROL, which is what
    this docstring used to call it (pf-adversary D6).  This line goes to the
    server's own stderr; no client can read it, so withholding it from a
    refused caller protects nothing.  And the case is unreachable as it was
    described: `handle_local_talk_chat` has already refused an unlisted
    account before `_stage_action` runs, so the only routes to
    `REASON_NOT_GM_ACCOUNT` here are the allowlist file changing mid-command
    and the standalone-config door.  The exclusion stays because a way out
    answers a question neither of those asked, which is a tidiness reason
    honestly labelled, not a safety one.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH.  The refusal is the product and is
    already decided by the time this runs; the line is the courtesy.  So:
    everything that could raise is evaluated INSIDE the guarded block (D2 --
    a hoist of either call out of it was a mutation that survived the whole
    suite, because the safety rested on `stageable_scene_ids` choosing to
    swallow rather than on structure); the guard catches `Exception`, not
    `OSError`, because a closed stream raises `ValueError` and an unmappable
    one `UnicodeEncodeError` (D4); a `None` stderr returns rather than
    letting `print` fall back to STDOUT and repeat the `lane_hooks` incident
    this token exists to avoid (D1); and the failure is NAMED rather than
    swallowed in silence (D5), because "the console is broken" and "the route
    was never wired" must not look identical to an attended `GT-127` run.

    RETURNS whether the line actually reached the stream, for
    `WITHHELD_CONSOLE_TOKEN`'s backstop.  `False` on every early return
    above, so a refusal this printer declined to explain still gets the
    shorter no-bytes line rather than nothing -- and a refusal it DID
    explain does not get both.  It is deliberately not "did I intend to
    print": a `None` or exploding stderr means the operator has no line,
    whatever this function meant to do, and the backstop's own guard will
    fail the same way and name it once more rather than claim a line exists.
    """
    if reason not in login_scene_stage.DESTINATION_SHAPED_REASONS:
        return False
    stream = sys.stderr
    if stream is None:
        # `print(file=None)` writes to STDOUT.  On `pythonw.exe` or a service
        # started with stdio detached -- the "detached service console" this
        # module names two paragraphs up -- that is how a GM token lands in
        # another tool's `--json` artifact.  MEASURED by pf-adversary (D1).
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return False
    try:
        # EVERYTHING THAT COULD RAISE STAYS INSIDE THE GUARD (D2 again): the
        # blocker call reads lane A's registry from disk and can raise for
        # every reason `stageable_scene_ids` can.  Built here rather than
        # hoisted, for the same reason the rest of this line is.
        suffix = ""
        if reason == login_scene_stage.REASON_SANCTIONED_NOT_YET_REACHABLE:
            # The DISK reading, with no snapshot, because the refusal being
            # explained is the disk one -- see `sanctioned_barred_blocker`.
            # Mixing the two readings in one console line is the defect the
            # `scene_registry` parameter was added to close, not to create.
            # `provenance` is None only if the REASON and the sanction map
            # disagree -- which is a bug in this lane, not a citation.  It
            # is rendered as `unknown` rather than as the literal `None`,
            # because the blocker on the same line already says
            # `not_sanctioned` in exactly that case and the pair is the
            # signal.  A reader must not have to guess whether "None" was
            # the letter's name.
            provenance = login_scene_admission.sanctioned_barred_provenance(
                scene_id
            )
            suffix = (
                " blocker="
                f"{login_scene_admission.sanctioned_barred_blocker(scene_id)}"
                " sanction="
                f"'{console_safe(_one_line(provenance or 'unknown'), stream)}'"
            )
        print(
            f"{WARP_REFUSED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"scene_id={scene_id} reason={reason} "
            # THE SINGLE-USE LIST, because `/warp` writes the single-use map
            # and a way out from the other map's rule would omit exactly the
            # destinations this command CAN reach since `CORE-REQUEST-GM-038`
            # -- telling a refused operator that a scene they may stage is
            # not on the menu.  `login_scene_admission`'s
            # `single_use_stageable_scene_ids` is the same tuple judged by
            # the rule `stage_login_scene` applies.
            "stageable="
            f"{single_use_stageable_scene_ids(scene_registry=scene_registry)}"
            f"{suffix}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")
        return False
    return True


def _print_no_bytes_way_out(
    session: object,
    token: str,
    command_name: object,
    why: str,
) -> None:
    """Say that an ACCEPTED GM command put nothing on the wire, and why.

    THE BACKSTOP, not a fourth way out.  `WITHHELD_CONSOLE_TOKEN`'s own
    comment carries the measurement that made it necessary; what belongs
    here is the shape:

    * it runs only for a command that PARSED -- an ordinary sentence a GM
      typed is refused upstream with `refused_not_a_command` and returns
      long before this, which is the founding rule that a non-GM's chat and
      a GM's conversation are never written anywhere;
    * it runs only when nothing went to the client and no handler printed
      its own line (`_Verdict.line_printed`), so the scene list `/warp 9999`
      gets is never doubled by a shorter line saying the same thing worse;
    * a staged cross-scene warp gets `STAGED_CONSOLE_TOKEN` instead, not
      this token and not silence.  That command had a real effect -- a
      config entry that decides the next login -- so "no bytes sent" would
      be true in the only sense nobody cares about;
    * `why` is what the AUDIT FILE ended up carrying, decided after the
      write: `verdict.audit_outcome` when the row was appended, and
      `WHY_AUDIT_ROW_NOT_WRITTEN` when it was not.  Reading the verdict
      before the write -- what the first draft did -- prints a word the
      ndjson does not have on exactly the boot where both are being read
      together (pf-adversary D1).

    IT NEVER PRINTS WHAT WAS TYPED -- the same property
    `_print_command_refusal_way_out` spends its docstring on, and for the
    same measured reason (`session.token` is the process-wide `--token`, so
    on the wired server any player's sentence would be printed under the
    operator's own GM account).  Two fields, both lane-authored: the command
    NAME, which is rendered only if it is one of `commands.COMMAND_NAMES`,
    and the blocker sentence, which is looked up in `NO_BYTES_BLOCKERS` and
    never built from the command's arguments.  A `GmCommand` is accepted
    "regardless of source" everywhere in this lane, so the name is checked
    here rather than trusted from the parser.

    IT CARRIES THE CONNECTION'S OWN IDENTITY, AND `account=` IS NOT THAT.
    `COO-DECISION 2026-09-02T01:47+07:00` (`pf_bridge/notes_to_chief/
    20260902_0147_COO-DECISION-speed-db-first-then-wire-refusal-must-be-
    visible.md`) requires, for every `/speed` refusal, "log fang server one
    line carrying identity and the reason".  The reason half has been here
    since round `tvbiqc` (`why=` plus `blocked_on=`); the identity half was
    NOT, and `account=` does not supply it -- this same docstring already
    records that `session.token` is the process-wide `--token` CLI value,
    one string shared by every connection, which is exactly why it may not
    be read as "who did this".  So two more fields are appended, read off
    the connection's own selected character through the read sites
    `_speed_action` itself uses (`_selected_speed_character_id`,
    `_selected_speed_identity` -- both defensive, neither raises, both
    answer `None` for a session with nothing selected yet):

      * `character_id=` -- the `characters` rowid the `/speed` write names,
        i.e. the row an attended tester diffs in step 6 of `GT-193`; and
      * `identity=<lo>:<hi>` -- the pair the composed frame addresses, so a
        console line can be matched against a captured frame.

    `none` for either one is a real answer, not a gap: it is the state the
    `refused_speed_no_selected_character` / `refused_speed_no_character_id`
    outcomes on the same line are naming.  The fields are lane-authored ints
    rendered as ints, so the "never prints what was typed" property above is
    untouched -- there is no path from the GM's typed text into either.

    WHAT THIS LINE STILL DOES NOT DO, said here rather than in a round file
    nobody greps: it is the SERVER HOST'S stderr, not the GM's screen.  The
    other half of that same COO decision -- an immediate chat line the GM
    reads at the client -- is NOT delivered by this function and is not
    delivered anywhere in this lane's zone.  ~~"The only proven
    server->client text route this lane has is
    `say_wire.make_say_broadcast_frame`."~~  STRUCK: pf-adversary (round
    `c637o1`, D3) refuted it from this repository's own ledger.
    `docs/FUNCTIONAL_COVERAGE.json`'s `chat_input_echo_hypothesis` row is
    `runtime_pass` on attended GT-009 -- the real client RENDERED echoed
    text in its chat window, over `0xAC52 Channel_LocalTalkMessageVital`,
    through the same shared serializer `say_wire` imports -- while `0x9F2C`
    GMGlobal has never been seen on a screen at all.  Two routes exist and
    the better-evidenced one is not the one this lane owns.

    NEITHER IS USABLE FROM HERE TODAY, which is why the conclusion did not
    change even though the reason did:

      * `0x9F2C` -- its gate `GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED` is
        held shut by `COO-DECISION 2026-08-29T00:41+07:00` on three
        conditions this round cannot clear (the per-connection identity fix
        in `runtime.py`, a COO word on the flip, and a client-observable
        render).  That constant's comment ends "only a NEW COO-DECISION
        lifts it".
      * `0xAC52` -- the echo lane is behind a scenario opt-in with
        `production_allowed: False`, GT-009 proved the render at exactly one
        message length (12 printable ASCII; a 5-character message stayed
        silent), it echoes the CLIENT's own frame rather than server-composed
        text, and `tests/test_gm_say_gate_lock.py::NoSecondCompositionRoute
        Tests` forbids any file in this zone except `say_wire.py` from
        calling that codec.  `PROMOTE-153` (open, chief's) is the ticket that
        would land it on a default boot.

    So this lane asked instead of building either -- `pf_bridge/
    notes_to_chief/20260902_0229_LANE-GM-ASK-COO-speed-refusal-on-screen-
    needs-the-say-gate.md`, which now puts FOUR options to COO rather than
    the three the first draft could see.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH -- held exactly as the two
    printers above hold it: everything that can raise is inside the guard,
    the guard catches `Exception` (a closed stream raises `ValueError`, an
    unmappable one `UnicodeEncodeError`), a `None` stderr returns rather
    than letting `print` fall back to STDOUT, and a console that cannot be
    written is NAMED on the event trail instead of swallowed.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        # Membership, not truthiness: a name outside the vocabulary is a
        # `GmCommand` this lane did not parse, and rendering it would put
        # caller-chosen text on the operator's console through the one field
        # that looks trustworthy.  `unnamed` is not a failure -- the outcome
        # word beside it is the answer either way.
        name = command_name if command_name in COMMAND_NAMES else "unnamed"
        blocker = NO_BYTES_BLOCKERS.get(why)
        if blocker is None:
            # Prefix fallback, ONLY for the committed-row outcomes: their
            # suffix is an exception type name, so they cannot be fixed keys
            # in the mapping above.  Ordered longest-prefix-first in the
            # tuple itself, so the compose-refused word does not match the
            # more general persist-refused prefix it starts with.
            blocker = next(
                (
                    sentence
                    for prefix, sentence in COMMITTED_ROW_BLOCKER_PREFIXES
                    if str(why).startswith(prefix)
                ),
                NO_BLOCKER_RECORDED,
            )
        # Capped at the printer for the reason the other cap is: this
        # function reads its blocker out of a mapping a later round edits,
        # and a bound that lives with the supplier is the supplier's
        # property, not this line's.
        if len(blocker) > MAX_CONSOLE_HINT_LENGTH:
            blocker = blocker[:MAX_CONSOLE_HINT_LENGTH] + "..."
        print(
            f"{WITHHELD_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"command={name} why={console_safe(_one_line(str(why)), stream)} "
            f"blocked_on='{console_safe(_one_line(blocker), stream)}' "
            f"{_identity_fields(session, stream)}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _print_staged_way_out(
    session: object,
    token: str,
    command: object,
    outcome: str,
    *,
    same_scene: bool = False,
    basis: str = SAME_SCENE_BASIS_FIELD,
    blocker: str = STAGED_BLOCKER_NO_SPAWN,
) -> None:
    """Say that a cross-scene `/warp` was staged, and what the GM must do now.

    The one accepted command that sends no bytes and is not a
    disappointment.  See `STAGED_CONSOLE_TOKEN` for why it is a separate
    token from the no-bytes one rather than either sharing it or staying
    silent, which is what this round shipped first and pf-adversary D3
    measured as leaving the hole open for the only `/warp` that does
    anything.

    THREE FIELDS, and the middle one is the reason this exists rather than
    being a nicety: the SCENE the next login will use, whether the typed
    COORDINATES were dropped, and the next step.  `/warp 278 100 200` drops
    the two numbers the GM typed -- `ForcePos` carries no scene id, so the
    cross-scene half stages the scene and nothing else -- and before this
    line that fact appeared nowhere a human would look, only in the ndjson
    `outcome` word `staged_login_scene_coords_ignored`.

    THE SCENE ID IS THE ONE FIELD DERIVED FROM WHAT WAS TYPED, and it is an
    INT, re-derived inside the guard by the same helper the handler used --
    the same shape and the same rung as `GM_CHAT_WARP_REFUSED`, which has
    printed a typed `scene_id` since round `c48x1n`.  A `GmCommand` whose
    args cannot be read renders `unknown` rather than raising: a diagnostic
    may never alter dispatch, and by the time this runs the entry is already
    on disk.

    THE `next=` FIELD IS BUILT BY `staged_next_step` from two independent
    answers this printer is TOLD rather than guesses (`COO-DECISION
    20260903_2050` item 2): which `blocker` held the frame, and whether a
    relog would move her (`same_scene`).  The struck sentence gave neither --
    it led with an instruction, and that is the whole of what the owner's
    "nothing happened" report turned on.

    BOTH ARE PASSED IN, never re-derived here, because both belong to
    `_warp_action`: it is the function that knows the current scene and the
    one that already asked the registry.  Re-asking the registry here was
    defect D3 (a second, unguarded disk read on the dispatch path), and
    re-reading the position here would be a second answer to a question
    already answered.

    A FOURTH FIELD, `basis=`, AND IT IS A CORRECTION (pf-adversary, round
    `spt6fv`, D2, MEASURED).  `same_scene` is decided by comparing the typed
    scene against `selected.position.scene_id`, which `runtime.py`'s
    `_gm_warp_resync_selected_scene` rewrites to a cross-scene warp's
    DESTINATION at queue time, with nothing from the client confirming the
    arrival.  Measured end to end: a client really in scene 1, `/warp 997 100
    200`, then `/warp 997` -- and this line said "you are standing in it
    already", which was the server's belief and was false.
    `GM_CHAT_SAME_SCENE_TELEPORT_SENT` has carried `basis=` for exactly this
    since round `07kjfd`; this line makes the STRONGER claim and carried no
    label at all.  It has one now, and the day chief's
    `client_confirmed_scene` lands (CORE-REQUEST-GM-051 item 3) both lines
    change basis together.

    ~~AND THAT LABEL IS A CONSTANT~~ -- struck 2026-09-04: chief's field
    landed (letter `20260903_2306`), so `basis` is now PASSED IN, decided
    once by `same_scene_with_basis` alongside the `same_scene` it explains,
    and it prints `client_confirmed_scene` on any connection whose client has
    ever sent a frame this lane may trust.  The default is still the weaker
    word, on the same rule as every other default here: a caller that forgets
    the argument understates what it knows.

    THE DEFAULTS ARE THE SHIPPED SHAPE, not neutral values: on the shipped
    flags the missing marker is the only blocker that can hold a frame, so a
    call site that forgets an argument says what is true of the default build
    rather than inventing a blocker -- and `same_scene` defaults to the
    cross-scene tail so such a caller understates what it knows instead of
    telling a GM already standing in the scene that a relog will move her.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        try:
            scene_id = int(warp_command_scene_id(command))
        except Exception:  # noqa: BLE001 - see the last paragraph above
            scene_id = "unknown"
        coordinates = (
            "ignored"
            if outcome == OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED
            else "none"
        )
        next_step = staged_next_step(same_scene=same_scene, blocker=blocker)
        print(
            f"{STAGED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"command=warp scene_id={scene_id} coordinates={coordinates} "
            f"basis={basis} "
            f"next='{next_step}'",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _print_same_scene_teleport(
    session: object,
    token: str,
    command: object,
    *,
    basis: str = SAME_SCENE_BASIS_FIELD,
) -> None:
    """Say that a bare `/warp <n>` moved the GM inside the scene she is in.

    The one SENT command that also speaks here.  See
    `SAME_SCENE_TELEPORT_CONSOLE_TOKEN` for why this shape is the exception
    to "a sent command's record is `route=action` plus the serve loop's
    label", and `_announce_console_outcome` for the one call site.

    THE SCENE ID IS RE-DERIVED FROM THE COMMAND, exactly as
    `_print_staged_way_out` re-derives its own, and renders `unknown` rather
    than raising when the args cannot be read: a diagnostic may never alter
    dispatch, and by the time this runs the frame is already on its way.

    NO COORDINATES ARE PRINTED, deliberately.  The spawn point this warp
    aimed at is already recorded in exactly one place -- the parked
    `WarpTarget`, which is what chief's confirmation token
    (CORE-REQUEST-GM-031) compares the next position report against.  A
    second rendering of the same three floats on the console is a second
    source of truth for the one fact this line is NOT evidence of.

    NONCLAIM, and it is the reason the token ends in `SENT` rather than in
    anything about arriving: this line says the frame left the server. It is
    not evidence the client moved, that the marker spawn is walkable, or
    that the scene re-rendered -- `RE-162`'s finding that no census follows a
    mid-session TeleportVital is inherited by this shape unchanged, and the
    owner's own decision (`1800` item 3) left the census question with
    LANE-A/LANE-B.

    ~~next='you were moved to this scene own spawn point now; nothing was
    staged for the next login'~~ -- THE FIRST DRAFT OF THIS LINE SAID BOTH OF
    THOSE AND BOTH WERE WRONG (pf-adversary, round `07kjfd`, D1, MEASURED).
    "You were moved" is a claim about her SCREEN made from a wire fact, i.e.
    the exact claim the paragraph above and this round's own `docs/GM_LANE.md`
    NONCLAIM forbid -- printed on the one artifact an attended tester
    actually greps, where it outranks three explanations she will never read.
    "Nothing was staged for the next login" is a claim about ACCOUNT STATE
    this printer never reads: measured end to end, `/warp 278` then `/warp 1`
    left `gm_login_scene.json` still holding 278 while this line told her
    nothing was staged, so she would relog into 278 having been told
    otherwise.  What replaced them says only what this command did: a frame
    left the server, this line is not the client's answer, and THIS COMMAND
    wrote no next-login scene (which is true; an EARLIER `/warp` may still
    have, and that is `GM_CHAT_STAGED_NEXT_LOGIN`'s line to answer for).
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        try:
            scene_id = int(warp_command_scene_id(command))
        except Exception:  # noqa: BLE001 - see the docstring
            scene_id = "unknown"
        print(
            f"{SAME_SCENE_TELEPORT_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"command=warp scene_id={scene_id} coordinates=none "
            f"basis={basis} "
            "next='a teleport frame for this scene own pinned spawn left the"
            " server; this line does not say the client moved, and this"
            " command wrote no next-login scene'",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _trial_console_field() -> str:
    """`speed_wire.trial_console_field()`, wrapped so a printer never raises.

    That function already promises not to raise; this wrapper exists because
    the promise is made in ANOTHER module and a console line in this one must
    not depend on it staying true.  `unavailable` is a third word, distinct
    from that module's `unset`/`malformed`, so an operator reading the line
    can tell "the gate says nothing is armed" from "this process could not
    ask the gate at all" -- two facts a single word would merge.
    """
    try:
        return speed_wire.trial_console_field()
    except Exception:  # noqa: BLE001 - a diagnostic never alters dispatch
        return SPEED_TRIAL_UNAVAILABLE


def _trial_admits(value: object) -> bool:
    """`speed_wire.trial_admits(value)`, wrapped, and FALSE ON ANY FAILURE.

    The wrapping direction is the whole point: this is the one predicate in
    this route that can let a frame out, so a gate that could not answer must
    read as "not admitted".  `speed_wire.trial_admits` does not raise today;
    if a later edit there makes it able to, the frame is held rather than
    sent, which is the standing posture of every `/speed` gate above it.
    """
    try:
        return bool(speed_wire.trial_admits(value))
    except Exception:  # noqa: BLE001 - an unanswerable gate is a closed gate
        return False


def _print_speed_trial_open(
    session: object, token: object, command_name: object, stored: object,
) -> bool:
    """Say that the RUNTIME TRIAL GATE let this one frame past both holds.

    COO-DECISION `20260903_0646` item 2, fourth bullet, in as many words:
    "บรรทัดคอนโซลต้องบอกว่าประตูเปิดให้ค่าไหน ผู้คุมจอต้องอ่านออกโดยไม่ต้องเปิด
    ซอร์ส".  This is that line, and it is printed on the SEND path -- the
    only path in this module where a `/speed` frame reaches a dispatcher --
    so the console cannot be quiet about the one case that costs an attended
    round if it goes wrong.

    THREE FIELDS, ALL LANE-AUTHORED, NOTHING TYPED EVER PRINTED, the same
    rule `_print_speed_deferred` and `_print_notice_sent` state for their own
    lines: the command NAME rendered only when it is one of
    `commands.COMMAND_NAMES`, `repr()` of the finite f32 the row holds, and
    `speed_wire.trial_console_field()`'s own ASCII word.  The environment
    variable's RAW text never reaches the console -- see that function.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH, and here that rule cuts the way it
    always does rather than the way it might seem to: a console this line
    could not reach costs the LINE, not the frame.  The frame was admitted by
    `speed_wire.trial_admits` before this function was called, and a printer
    that could veto a send would be a second, invisible gate -- exactly the
    shape this lane refuses everywhere else.  The boolean it returns is the
    printer's own answer, carried into the verdict the same way
    `_print_speed_deferred`'s is, so a round that greps for this token and
    finds nothing can tell a held frame from a lost line.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return False
    try:
        name = command_name if command_name in COMMAND_NAMES else "unnamed"
        try:
            row = repr(float(stored))
        except Exception:  # noqa: BLE001 - a printer never raises
            # Unreachable on the shipped route (this line runs below
            # `EVENT_SPEED_PERSIST_READBACK_UNUSABLE`, which already refused
            # anything but a real number), and spelled anyway: the word the
            # deferral line uses for the same hole, so one grep answers both.
            row = SPEED_DEFERRED_ROW_UNKNOWN
        print(
            f"{SPEED_TRIAL_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(str(token)), stream)}' "
            f"command={name} env={speed_wire.SPEED_TRIAL_ENV} "
            f"trial_opens_for={_trial_console_field()} sending={row} "
            f"{_identity_fields(session, stream)}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")
        return False
    return True


def _print_speed_trial_armed_refused(
    session: object,
    token: object,
    command_name: object,
    refused_by: str,
) -> bool:
    """Say that the RUNTIME TRIAL GATE recognised this value and the wall
    refused it anyway -- the replacement for the dead `_print_speed_trial_
    open` (see `SPEED_TRIAL_ARMED_REFUSED_CONSOLE_TOKEN`'s own comment).

    WHY THIS EXISTS.  `speed_wire.compose_sparse_speed_update` raises for
    every value since `COO-DECISION 20260904_0345` item 2, so the SEND
    branch `_print_speed_trial_open` was written for is unreachable: every
    `PF_SPEED_TRIAL`-armed call now falls into the COMPOSE-REFUSED branch
    below, and until this function existed that branch printed the SAME two
    words (`GM_CHAT_NOTICE_SENT` / `GM_CHAT_NO_BYTES_SENT`) whether the
    environment variable was set or not -- an owner watching the console
    could not tell "the key never armed" from "the key armed and the wall
    still said no", which is exactly the distinction COO `0646` item 2's
    fourth bullet asked the trial gate's console line to make.

    NOTHING SENT IS CLAIMED.  Unlike `_print_speed_trial_open`, this line
    never says `sending=`: no `0x309A` byte reaches a wire on this branch,
    ever, so a field that named one would be the exact overclaim `pf_bridge
    #1067` measured and this round exists to remove. `refused_by` names the
    exception type only (`type(error).__name__`), the same discipline every
    other refusal event in this module keeps.

    THREE FIELDS, ALL LANE-AUTHORED, NOTHING TYPED EVER PRINTED, the same
    rule the token it replaces stated for itself: the command NAME rendered
    only when it is one of `commands.COMMAND_NAMES`, `_trial_console_field()`
    for the value the gate admitted (never the raw environment text -- see
    that helper), and the refusing exception's own type name.  Read through
    the same `_trial_console_field()` wrapper the send-branch printer uses
    rather than a value passed in by the caller: this branch runs strictly
    after `_trial_admits` already returned `True` this same dispatch, so the
    two reads answer identically, and reusing the wrapper means a future
    change to how that value is derived cannot leave the two printers
    disagreeing.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH: this prints AFTER the refusal is
    already decided (the caller has already noted `EVENT_SPEED_PERSIST_
    COMPOSE_REFUSED_PREFIX` and is about to return `_speed_denied`), so a
    console this line cannot reach costs the LINE, never the outcome.  The
    boolean it returns is not consulted by the caller for that reason --
    unlike `_print_speed_deferred`, there is no `line_printed` backstop to
    feed, because `_speed_denied`'s own notice-or-no-bytes lines already
    cover the "was the refusal itself silent" question this printer does
    not answer.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return False
    try:
        name = command_name if command_name in COMMAND_NAMES else "unnamed"
        print(
            f"{SPEED_TRIAL_ARMED_REFUSED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(str(token)), stream)}' "
            f"command={name} env={speed_wire.SPEED_TRIAL_ENV} "
            f"trial_opens_for={_trial_console_field()} "
            f"refused_by={console_safe(_one_line(refused_by), stream)} "
            f"{_identity_fields(session, stream)}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")
        return False
    return True


def _print_speed_deferred(
    session: object, token: str, command_name: object, stored: object,
) -> bool:
    """Print COO-DECISION `1847`'s line and say whether it reached the stream.

    RETURNS WHETHER IT PRINTED, unlike every other printer in this module,
    and the caller puts that answer in `_Verdict.line_printed` so the backstop
    is not suppressed by a line that never appeared.

    ~~"a console this line could not reach falls back to
    `GM_CHAT_NO_BYTES_SENT ...` instead of leaving an accepted command
    silent"~~ -- STRUCK IN THE ROUND THAT WROTE IT, because pf-adversary (D4)
    measured that the fallback does not exist for the two ways `printed`
    actually becomes False in production.  Both printers read the SAME
    `sys.stderr` through the same helpers, so a `None` stream returns from
    both and a raising stream raises in both: the measured result is ZERO
    console lines and two `console_write_failed_*` events, not a second line.

    So what this return value really buys is narrower, and it is worth having
    for that alone: the honest report keeps `_announce_console_outcome` from
    treating an unwritten line as spoken, which matters the moment either
    printer stops sharing a stream with the other, and it puts the failure on
    the EVENT TRAIL under a name a replay tool can find (`session.events`),
    which is the only record that survives a dead console at all.

    THE PREFIX IS THE CONTRACT.  `SPEED_DEFERRED_CONSOLE_TOKEN` leads the
    line, unconditionally, before any field -- COO's wording is "the prefix
    must be those two words".  The fields after it are the same lane-authored
    ones `_print_no_bytes_way_out` carries, built by the SAME
    `_identity_fields` builder for the reason that builder exists: two lines
    naming the same row must not drift into two spellings of it.

    NOTHING TYPED IS EVER PRINTED -- the property every printer in this
    module holds.  The command NAME is rendered only when it is one of
    `commands.COMMAND_NAMES`, and `session.token` names a process, not a
    person (see `_print_no_bytes_way_out`).

    IT NAMES THE ROW IT LEFT BEHIND, AND THAT IS THE POINT OF THE THREE
    FIELDS ADDED AFTER `why=`.  COO `1847` stopped the FRAME and deliberately
    kept the DB write ("the DB write continues as before ... what has to stop
    is the outbound frame, and only that"), so on this route the command DID
    change the character's row and then printed a line that said only that
    something was deferred.  A tester reading `SPEED DEFERRED` and concluding
    "nothing happened" was reading the console correctly and the system
    wrongly -- and since `#605` landed the `speed_walk` login read on `main`
    (`session.py:192` -> `login_speed.resolve_for_character` ->
    `player_wire.py:266`), the row this route leaves behind is no longer
    inert: THE NEXT LOGIN FOR THAT CHARACTER READS IT AND PUTS IT ON THE
    WIRE.  The recovery step of `GT-218` (`pf_bridge/GAME_TEST_QUEUE.md` --
    a BRIDGE-side ticket, not in this repository, so a reader here cannot
    grep it) is a re-login, so the gap is reachable in the ticket this route
    was written for.

      * `row_after_write=` -- the store's OWN read-back, the same number the
        composer below would have carried, never the GM's typed text (the
        property every printer in this module holds).  `validate` rounds an
        f32 on the way in, so `/speed 400.1` reads back
        `400.1000061035156`: this is what the WRITE RETURNED, not what was
        asked for.
      * `next_login=` / `next_login_sends=` -- answered by
        ~~`login_speed.resolve`, THE VERY FUNCTION the login path runs~~ --
        STRUCK BY `CHIEF-TO-LANE-GM 20260903_0725`, WHICH MEASURED THE LINE
        LYING.  `resolve` is NOT the function the login path runs; it is the
        second half of it.  `session.select_and_start` calls
        `login_speed.resolve_for_character`, and since the login gate of
        `COO-DECISION 20260903_0645` landed (`#632`), that function asks
        `login_speed.held_by_the_speed_deferral` FIRST and returns the
        CONSTANT whatever the row holds.  So on the `SPEED DEFERRED` route --
        the only route that exists on `main` today -- this line printed
        `next_login=from_row next_login_sends=300.0` while the very next
        login sent `400.0` and said `wire_deferred`.  The two fields were a
        promise this module had no standing to make, on the one route it is
        printed from, for as long as that gate has been on `main`.

        SO THE GATE IS ASKED HERE FIRST TOO, IN THE SAME ORDER, and by
        composition rather than by a call to `resolve_for_character` itself:
        that function needs a STORE and would put a database read on a
        console path (a printer may never alter dispatch, and a read is the
        one thing on this line that could block).  `held_by_the_speed_
        deferral(fallback)` then `resolve(value, fallback=...)` IS its body
        with the store read taken out.  ~~"the only part skipped is
        `_withheld_row_detail`"~~ -- STRUCK, pf-adversary D3: the skipped read
        also decides two REASONS this line can therefore never print,
        `ROW_COULD_NOT_BE_READ` and `ROW_HAS_NO_VALUE`, and on an open wire it
        could disagree with the write's read-back outright (the undo of branch
        B above, a login-time store failure, a second `/speed` in between).
        The narrower true claim: what this line reports is THE ROW THIS
        HANDLER WROTE, graded by the login's own rules -- the same scope
        `row_after_write=` states for itself two paragraphs up, and the reason
        both names say `row`.  `login_speed`'s ban on re-typing its range is
        still obeyed: both halves are still ITS functions.

      * `row_verdict=` -- WHAT THE ROW ITSELF EARNS, asked of
        `login_speed.resolve` unconditionally and independently of the gate.
        pf-adversary (round `3vqkpn`, D1b) measured why one field cannot do
        both jobs: with only the gate asked, `next_login=` prints `wire_
        deferred` for EVERY value while the gate stands, so `/speed 0` and
        `/speed -1` -- rows `login_speed` itself classifies as unusable
        (`ROW_SPEED_NOT_POSITIVE`) -- became indistinguishable from a healthy
        `/speed 400`.  `main` before this round could say `row_speed_not_
        positive`, and losing that word would have been a REGRESSION dressed
        as a fix, in the ticket whose recovery step is a re-login.

        This is also the question `login_speed.py`'s own point 4 says the
        field exists to answer, so the two modules now agree again instead of
        documenting opposite designs for one name.

    SO THE LINE CARRIES TWO ANSWERS AND NAMES WHICH IS WHICH.  `row_verdict=`
    is about the ROW (`from_row` / `row_refused_by_validator` /
    `row_speed_not_positive` / `row_has_no_value`); `next_login=` is about
    what the LOGIN WILL DO (`wire_deferred` / `wire_trial_only` /
    `deferral_unreadable` while the gate stands, the row's own word if it ever
    does not).  Today they read `row_verdict=<the row's word>
    next_login=wire_deferred`, and the pair is the whole point: a tester sees
    that her row is poisoned AND that the login will not carry it out.

    !! `next_login=` CANNOT PRINT A ROW WORD FROM THIS CALL SITE, and saying
    so is the honest version of a sentence an earlier draft got wrong.  This
    printer runs only inside `if speed_wire.send_deferred():`, and
    `held_by_the_speed_deferral` returns `None` only when that same flag makes
    `send_deferred()` False -- one flag, one process, read microseconds apart.
    The fall-through is kept exact rather than deleted because the call site,
    not this function, is what makes it unreachable.

    !! WHY `row_after_write=` AND NOT `row_written=`, WHICH IS WHAT THE FIRST
    DRAFT CALLED IT.  pf-adversary (round `gj77z5`, D1) measured the branch
    that makes the shorter name a lie.  This printer runs inside
    `_speed_action`; the row is not final until `_make_action` has appended
    the outcome row and, IF THAT APPEND FAILS, run `verdict.undo()`.  Three
    branches, all measured on a real store with a prior row of `100.0` and
    `/speed 777.0`:

      A. audit appended, row kept        -> row IS 777.0
      B. audit FAILED, undo REVERTED it  -> row IS 100.0, and this line has
                                            already printed 777.0
      C. audit FAILED, undo could not    -> row IS 777.0

    So THE DESIGN QUESTION pf-adversary closed his report with -- is this a
    line about what the HANDLER DID, or about what the DATABASE NOW HOLDS? --
    is answered here, deliberately, and the name follows the answer: IT IS A
    LINE ABOUT WHAT THIS HANDLER DID.  That is the only claim a function
    running strictly before the last thing that can change the row is
    entitled to make.  `row_after_write=` says exactly that and no more.
    [ASSUMPTION OF LANE-GM, AWAITING COO -- letter `20260903_0529`; the
    alternative, moving the assertion down into `_announce_console_outcome`
    where `reverted` is known, changes the shape of a line COO `1847`
    specified and is not a lane's call.]

    THE OPERATOR IS NOT LEFT GUESSING ON BRANCH B, and that is what makes the
    narrower name honest rather than merely defensible: when the audit fails,
    `_announce_console_outcome` prints a SECOND line beside this one, and its
    `why=` word already separates B from C -- `WHY_AUDIT_ROW_NOT_WRITTEN`
    (the effect was put back) versus `WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT`
    (it was not).  The pairing is pinned by tests below so neither line can
    start meaning something else on its own.

    WHAT THESE FIELDS DO NOT DO: they change no byte, lift no lock, and make
    no claim that the value is safe on a client.  Both `/speed` locks stand
    exactly where they stood (`speed_wire.send_deferred`,
    `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT`); this line only stops
    under-reporting what the route already did.  The resolve is wrapped for
    the same reason the print is: a printer may never alter dispatch, so a
    resolver that raises costs these fields a name and nothing else.

    A DIAGNOSTIC MAY NEVER ALTER DISPATCH: a `None` stderr and a stream that
    raises both cost this line and nothing else.  The frame is held either
    way -- the hold is decided by `speed_wire.send_deferred()` before this
    function is reached, never by whether the console accepted a line.
    """
    stream = sys.stderr
    if stream is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return False
    row_written = SPEED_DEFERRED_ROW_UNKNOWN
    row_verdict = SPEED_DEFERRED_NEXT_LOGIN_NOT_EVALUATED
    next_login = SPEED_DEFERRED_NEXT_LOGIN_NOT_EVALUATED
    next_login_sends = SPEED_DEFERRED_ROW_UNKNOWN
    if stored is not None:
        # Imported HERE rather than at module scope, and lazily on purpose:
        # this file is imported by the listener thread's dispatch path, a
        # printer may never alter dispatch, and an import that fails must cost
        # two console fields rather than the module.  `login_speed` uses the
        # same lazy form for `persistence_typed_attrs` for its own reason.
        try:
            from .. import login_speed, player_wire

            value = float(stored)
            row_written = repr(value)
            fallback = player_wire.PLAYER_LOGIN_MOVEMENT_SPEED
            # BOTH QUESTIONS ARE ASKED, AND THE ROW'S IS ASKED
            # UNCONDITIONALLY -- see the `next_login=` / `row_verdict=`
            # paragraphs above.  `resolve` is what the row WOULD earn; the
            # gate is what the login WILL do.  A first draft of this fix
            # asked only the gate, and pf-adversary (round `3vqkpn`, D1b)
            # measured what that cost: `/speed 0` and `/speed -1` write a row
            # `login_speed` itself calls unusable, and the line stopped being
            # able to say so -- every value printed the gate's one word.
            row_verdict_resolved = login_speed.resolve(value, fallback=fallback)
            resolved = login_speed.held_by_the_speed_deferral(fallback)
            if resolved is None:
                # Unreachable from this call site today and kept exact rather
                # than collapsed (pf-adversary D1): the branch above this
                # printer runs only while `send_deferred()` is True, and the
                # gate returns `None` only while it is False.  If that call
                # site ever moves, this must still be `resolve_for_character`
                # order and not a guess.
                resolved = row_verdict_resolved
            row_verdict = console_safe(
                _one_line(str(row_verdict_resolved.reason)), stream
            )
            # `console_safe` on THIS one only, and the asymmetry is the
            # point (pf-adversary D6): the two numeric fields are `repr()` of
            # a finite float and cannot carry a space, a quote, an `=`, a
            # newline or a non-ASCII byte, but `next_login` can also be
            # `unresolved_<ExcType>`, and a Python class name may be
            # non-ASCII.  One such name would cost the whole two-word line on
            # a cp874 console -- COO `1847` point 2 asks for one PURE-ASCII
            # line, and a lost prefix is a lost grep for an attended tester.
            # No exception class on today's path between `login_speed.resolve`
            # and `persistence_typed_attrs.validate` is non-ASCII, so this is
            # a contract being kept, not a live bug being fixed.
            next_login = console_safe(_one_line(str(resolved.reason)), stream)
            next_login_sends = repr(float(resolved.value))
        except Exception as error:  # noqa: BLE001 - a printer never raises
            unresolved = console_safe(
                _one_line(
                    f"{SPEED_DEFERRED_NEXT_LOGIN_UNRESOLVED_PREFIX}"
                    f"{type(error).__name__}"
                ),
                stream,
            )
            # BOTH reason fields lose their name together, never one of them:
            # the two questions are asked in one `try`, so a failure anywhere
            # in it leaves neither answer measured.  A half-named line would
            # invite an operator to read the surviving word as current.
            row_verdict = unresolved
            next_login = unresolved
            next_login_sends = SPEED_DEFERRED_ROW_UNKNOWN
    try:
        name = command_name if command_name in COMMAND_NAMES else "unnamed"
        print(
            f"{SPEED_DEFERRED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"command={name} why={OUTCOME_SPEED_DEFERRED} "
            f"row_after_write={row_written} row_verdict={row_verdict} "
            f"next_login={next_login} "
            f"next_login_sends={next_login_sends} "
            f"trial_opens_for={_trial_console_field()} "
            f"{_identity_fields(session, stream)}",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")
        return False
    return True


#: Which sentence each notice label carries.  NAMED so it does NOT end in
#: `_ACTION_LABEL`: `tests/test_gm_chat_command_action.py`'s contract scan
#: collects every module attribute with that suffix as a label to pin, and a
#: MAPPING answering that scan would have been pinned as if it were a string.  A MAP rather than a constant,
#: since `/lv` landed: this printer used to spell
#: `say_wire.SPEED_DENIED_NOTICE_TEXT` unconditionally, and the FIRST second
#: notice to reach it -- `/lv`'s -- made the console report `SPEED DENIED` for
#: a command that never touched the speed door.  Measured on this round, on
#: `tests/test_gm_command_audit_outcome.py`'s own captured stderr.  A label
#: missing from this map prints no sentence at all rather than another
#: command's: the console may be quiet, it may not be wrong.
NOTICE_TEXT_FOR_LABEL = MappingProxyType({
    SPEED_DENIED_NOTICE_ACTION_LABEL: say_wire.SPEED_DENIED_NOTICE_TEXT,
    TYPO_REFUSED_NOTICE_ACTION_LABEL: say_wire.TYPO_REFUSED_NOTICE_TEXT,
    LV_SET_NOTICE_ACTION_LABEL: say_wire.LV_SET_NOTICE_TEXT,
    LV_REFUSED_NOTICE_ACTION_LABEL: say_wire.LV_REFUSED_NOTICE_TEXT,
})

#: What the line says for a notice label this module does not know.  Not a
#: guess at the closest match, and not the old default -- an attended tester
#: greps this line to decide WHICH sentence a player saw.
UNNAMED_NOTICE_TEXT = "unnamed_notice"


def _print_notice_sent(
    session: object,
    token: str,
    command_name: object,
    action_label: object = None,
) -> None:
    """Say that a NOTICE went to the client for this command.

    Same shape as the other way-out printers in this module, and for the same
    measured reasons rather than for symmetry:

    * NOTHING TYPED IS EVER PRINTED.  Two fields, both lane-authored: the
      command NAME, rendered only when it is one of `commands.COMMAND_NAMES`,
      and the notice text, which is this lane's own frozen constant.
      `session.token` is the process-wide `--token` (see
      `_print_no_bytes_way_out`), so it names a process, not a person.
    * A DIAGNOSTIC MAY NEVER ALTER DISPATCH.  A stderr that is `None` or that
      raises must cost this line and nothing else -- the notice has already
      been composed and is about to be returned.
    * STDERR, not stdout: a JSON artifact from a headless replay tool must
      not gain a stray line (`lane_hooks/__init__.py`'s own incident).
    """
    if command_name not in COMMAND_NAMES:
        return
    if sys.stderr is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    text = NOTICE_TEXT_FOR_LABEL.get(action_label, UNNAMED_NOTICE_TEXT)
    try:
        print(
            f"{NOTICE_CONSOLE_TOKEN} account={token!r} command={command_name}"
            f" notice={text!r}",
            file=sys.stderr,
        )
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(
            session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}"
        )


def _announce_console_outcome(
    session: object,
    token: str,
    command: object,
    verdict: "_Verdict",
    *,
    audited: bool,
    sent: bool,
    reverted: bool | None = None,
    notice_sent: bool = False,
) -> None:
    """The ONE place this route decides what the console is told, and when.

    One call site, after the audit write, for every shape an accepted
    command can end in.  The first version of this round had two, one of
    them unreachable at HEAD, and they disagreed about what to print on the
    boot that reaches the reachable one (pf-adversary D1, D2, D7, D12).

    Nothing here can decide to SEND or WITHHOLD anything: the caller has
    already decided that and holds the action.  This function only speaks.

    `sent` is the caller's FINAL answer, not the verdict's: a frame the
    audit failure dropped is not sent, and a command whose bytes are on
    their way says nothing here -- `route=action` and the serve loop's own
    label are that command's record.  Keyed on the caller's variable rather
    than on `verdict.action` for exactly that reason.

    `reverted` is the caller's answer to the SECOND question the audit
    failure raises: did the undo actually put the durable change back?
    `None` means there was nothing to undo (the common case: no handler
    below this one parked or wrote anything).  `False` is the case
    pf-adversary D4 measured -- the row is still carrying the new value
    while the line names that very row -- and it is the only one that
    changes the word this function prints.  Passed in rather than re-derived
    because only `_make_action` ever sees the undo's answer.
    """
    if notice_sent:
        # BEFORE every early return below, and never instead of one of them.
        # The command still put nothing on the wire -- that is what the rest
        # of this function says -- but a sentence about the refusal did go
        # out, and `GT-193` step 9 grades exactly that. Printing it here
        # keeps the "ONE place the console is told" property intact.
        _print_notice_sent(
            session,
            token,
            getattr(command, "name", None),
            # The label off the verdict's own action, so the sentence named
            # here is the sentence whose bytes went out -- never a second
            # command's, which is what a hardcoded constant printed for the
            # first notice that was not `/speed`'s.
            (verdict.action or (None,))[0],
        )
    if sent and verdict.same_scene_teleport:
        # THE ONE SENT SHAPE THAT SPEAKS HERE (`PANYA-DECISION 1800`), and it
        # is keyed on the caller's `sent`, not on the verdict's action, for
        # the same reason every other branch below is: a frame the audit
        # failure dropped is not sent, and this line must not claim a
        # teleport for a command whose bytes were withheld one function up.
        # Falling through to the `sent` return below would leave the tester
        # with a label that says "cross-scene" for a warp that crossed
        # nothing; falling into the no-bytes branches would be worse still.
        _print_same_scene_teleport(
            session, token, command, basis=verdict.same_scene_basis
        )
        return
    if sent:
        return
    if verdict.audit_outcome in STAGED_OUTCOMES and audited:
        _print_staged_way_out(
            session,
            token,
            command,
            verdict.audit_outcome,
            same_scene=verdict.staged_same_scene,
            basis=verdict.same_scene_basis,
            blocker=verdict.staged_blocker,
        )
        return
    if verdict.line_printed and audited:
        # A handler already said it, in a vocabulary built for that refusal.
        return
    if verdict.line_printed:
        # ...BUT ONLY WHEN THE AUDIT ROW LANDED, and `and audited` is a fix,
        # not a nicety (pf-adversary, round `hj2cry`, D1, measured on three
        # runs).  A handler's line explains the REFUSAL; it cannot know that
        # the outcome row failed to append afterwards, because it returned
        # before the write.  With a bare `if verdict.line_printed: return`,
        # `SPEED DEFERRED` printed byte-identical output in all three of:
        # the row written and kept, the row written then REVERTED by the
        # undo, and the row written and NOT revertable -- while
        # `WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT`, a constant that exists
        # because pf-adversary D4 measured exactly that state one round
        # earlier, became unreachable on the only route the shipped default
        # takes.  So when the audit failed, the backstop speaks BESIDE the
        # handler's line rather than instead of it: two lines, one about the
        # refusal and one about the row, which is two facts, not a
        # duplicate.
        _print_no_bytes_way_out(
            session,
            token,
            getattr(command, "name", None),
            WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT
            if reverted is False
            else WHY_AUDIT_ROW_NOT_WRITTEN,
        )
        return
    if audited:
        why = verdict.audit_outcome
    elif reverted is False:
        why = WHY_AUDIT_ROW_NOT_WRITTEN_EFFECT_KEPT
    else:
        why = WHY_AUDIT_ROW_NOT_WRITTEN
    _print_no_bytes_way_out(
        session,
        token,
        getattr(command, "name", None),
        why,
    )


def _stage_action(
    session: object,
    scene_id: int,
    has_coordinates: bool,
    *,
    token: str,
    gm_accounts_config_path: str | None,
    login_scene_config_path: str | None,
    scene_registry=None,
    same_scene: bool = False,
    same_scene_basis: str = SAME_SCENE_BASIS_FIELD,
    blocker: str = STAGED_BLOCKER_NO_SPAWN,
) -> _Verdict:
    """The cross-scene half of `/warp`: write the next-login scene, send nothing.

    THE ALLOWLIST PATH IS THE SAME ONE THAT AUTHORIZED THE COMMAND.
    `gm_accounts_config_path` is `_make_action`'s own `config_path`, so the
    account this stages for is the account `handle_local_talk_chat` already
    checked, read from the same file.  Passing the default here instead would
    let a listener booted with `PF_GM_ACCOUNTS_CONFIG` authorize against one
    allowlist and stage against another -- and `stage_login_scene` re-checks
    membership, so the mismatch would show up as a mystery refusal rather
    than as a privilege bug.  It is still a re-check, not a second
    authorization point: it can only ever refuse a command the first check
    already accepted.

    NO UNDO IS OFFERED FOR ANYTHING BUT THE AUDIT FAILURE.  The returned
    `_Verdict` carries an undo that `_make_action` runs only when the outcome
    row cannot be written.  A GM who staged the wrong scene fixes it by
    typing another `/warp`, which is one more chat line; a general "undo the
    last command" surface is a feature nobody asked for and one more thing
    that can write to a config file.
    """
    try:
        result = login_scene_stage.stage_login_scene(
            token,
            scene_id,
            gm_accounts_config_path=gm_accounts_config_path,
            config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )
    except Exception as error:  # noqa: BLE001 - type name only, as everywhere
        _note(session, f"{EVENT_WARP_STAGE_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(
            None, f"{OUTCOME_STAGE_REFUSED_PREFIX}{type(error).__name__}"
        )

    if not result.staged:
        _note(session, f"{EVENT_WARP_STAGE_REFUSED_PREFIX}{result.reason}")
        printed = _print_warp_way_out(
            session, token, scene_id, result.reason, scene_registry
        )
        return _Verdict(
            None,
            f"{OUTCOME_STAGE_REFUSED_PREFIX}{result.reason}",
            line_printed=printed,
        )

    _note(session, f"{EVENT_WARP_STAGED_PREFIX}{scene_id}")

    previous_scene_id = result.previous_scene_id

    def _undo() -> bool:
        # THE SAME READING THE STAGE USED.  `restore_login_scene`
        # re-validates the whole file, so an undo judged against the file
        # while the stage was judged against a snapshot refuses and leaves
        # the entry it was called to remove sitting on disk.
        return login_scene_stage.restore_login_scene(
            token,
            previous_scene_id,
            gm_accounts_config_path=gm_accounts_config_path,
            config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )

    return _Verdict(
        None,
        (
            OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED
            if has_coordinates
            else OUTCOME_STAGED_LOGIN_SCENE
        ),
        _undo,
        # CONSOLE WORDING ONLY (`COO-DECISION 20260903_2050` item 2).  It is
        # carried on the SUCCESS return alone: every refusal above returns
        # before this point, and a refusal prints `GM_CHAT_WARP_REFUSED`,
        # which has its own vocabulary and never speaks of a relog.
        staged_same_scene=same_scene,
        same_scene_basis=same_scene_basis,
        staged_blocker=blocker,
    )


def _say_action(session: object, command: object, legacy: object) -> _Verdict:
    """One authorized `say` -> a `Channel_GMGlobalMessageVital` action.

    !! WHAT THIS SENDS AND TO WHOM.  An action goes to ONE socket -- the
    connection whose frame this dispatch is answering, i.e. the GM's own.
    The vital is NAMED GMGlobal because that is the client class the GM
    client renders it as; nothing in this path fans the message out to other
    players, and nothing in this lane can: the action list `dispatch()`
    returns is per-connection by construction.  A server-wide announcement is
    a separate runtime point and a separate CORE-REQUEST, not a rename of
    this one.  Said here so an attended run reads "the GM saw his own line"
    as the expected result rather than as a half-broken broadcast.

    Position is not read, and there is no equivalent of the warp path's
    COO position-ownership lock here: a chat line moves nobody, writes no
    DB row, and leaves the move-authority baseline exactly where it was.
    (`no DB row` is the precise claim, corrected by pf-adversary: an ndjson
    AUDIT row is written by `handle_local_talk_chat` before either gate is
    reached, and GT-133's wire-layer criterion counts exactly those rows.)

    !! WHAT THAT DOES *NOT* MEAN.  It does not make `say` two blockers away
    from a screen.  There is a third, and it is not this lane's:
    `runtime.py`'s `IDENTITY, STATED HONESTLY` comment (4886-4896 at this
    commit), at the very 0xAC52 branch CORE-REQUEST-GM-029
    would convert, records that `self.token` is the process-wide `--token`
    CLI value, NOT a per-connection authenticated login, and says the
    question "has to be answered before any executor is wired onto this
    point, not after".  Corroborated independently by
    `reports/PF_MULTIPLAYER_READINESS_AUDIT001_*_20260818.md` (I01-I04:
    `v141:7859` default `"localtest"`, `v141:7399` one token per accepted
    connection, no `parse_login*` anywhere, so the account name a client puts
    on the wire is never read).  Until that is fixed, "GM status is decided
    on the authenticated token" is true of THIS MODULE and false of THIS
    SERVER, and every allowlist test in this lane is a module-layer fact.
    `say` is the command that reaches that point first precisely because it
    is the least locked, so it is the one that would cash the identity bug.
    """
    version = say_wire.GM_GLOBAL_MESSAGE_VITAL_VERSION_CONFIRMED
    if version is None:
        # RE-132.  Same safety property as the warp gate above, same
        # precedent behind it (GT-101): an unproven vital_version byte is
        # what kills a real client's session, and 0x9F2C's byte has never
        # been measured -- only the shared PAYLOAD codec has.
        _note(session, EVENT_SAY_WITHHELD_NO_VERSION)
        return _Verdict(None, OUTCOME_SAY_WITHHELD_NO_VERSION)
    if version != say_wire.CHANNEL_CODEC_VITAL_VERSION:
        # The confirmed byte exists but the imported codec hardcodes a
        # different one, so composing here would put a version on the wire
        # that RE just measured as WRONG.  See that constant's release-day
        # note: the fix is a letter to the codec's owning lane, never a
        # second codec in this lane's zone.
        _note(session, EVENT_SAY_VERSION_CODEC_MISMATCH)
        return _Verdict(None, OUTCOME_SAY_VERSION_CODEC_MISMATCH)

    try:
        pc, frame = make_say_broadcast_frame(legacy, command)
    except Exception as error:  # noqa: BLE001 - includes SayWireError
        # Covers the over-length message, the wrong `args` shape, and every
        # rejection the channel codec itself raises.  Type name only: a
        # SayWireError message embeds the GM's typed text, which is both a
        # console cp874 hazard and a needless echo of client-supplied bytes.
        _note(session, f"{EVENT_SAY_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(
            None, f"{OUTCOME_REFUSED_PREFIX}say_{type(error).__name__}"
        )

    return _Verdict((SAY_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED)


def _gmprobe_action(session: object, command: object, legacy: object) -> _Verdict:
    """One authorized `/gmprobe <variant_id>` -> a `GM_UpdateGMStateVital` action.

    CORE-REQUEST-GM-043 (chief CHIEF-REPLY 2026-08-31T03:57+07:00, option A):
    lets an attended tester fire any of
    `bt_gm_probe.iter_state_vital_bit_variants`'s 14 named field-combinations
    mid-session by typing its `variant_id`, instead of the one hardcoded
    value the login-time call site already sends once per boot (`GT-164` was
    BLOCKED on exactly that limit -- pf_bridge notes_to_chief 20260831_0321).
    No new wire logic lives here: this composes through
    `bt_gm_probe.build_variant_frame` -> `gm.state_wire`'s pinned
    `GM_UpdateGMStateVital` builder (span_sha256-pinned byte layout,
    RE-089/RE-105), the same seam `_warp_action`/`_say_action` use for their
    own composers.

    NO VERSION GATE HERE, unlike `_warp_action`/`_say_action`.  Both of those
    gate on a vital_version constant that started life as `None` until an RE
    ticket proved a byte (`RE-129`, `RE-132`).
    `GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED` was never that kind of
    constant -- RE-105 pinned it at `0` outright, as the one value that
    survives the generic VitalData version check for this vital, not as an
    unmeasured placeholder waiting on a follow-up RE.  `build_variant_frame`
    already defaults to that pinned value; this function passes the variant
    through and lets the composer supply it, rather than re-importing the
    constant here, so the two modules cannot drift apart on which byte is
    "confirmed".

    UNKNOWN `variant_id` IS A NAMED REFUSAL, NEVER A GUESS.
    `gm/commands.py::parse_gm_command` accepts any single-token
    `variant_id` -- it does not import this lane's variant table, the same
    separation `warp`'s `scene_catalog` hint keeps (a catalog miss there is
    a hint for the log, decided downstream, never a parse-time rule; see
    `describe_warp_target`).  Whether the token names a REAL variant is
    decided HERE, at dispatch, the one place this module and
    `bt_gm_probe.VARIANTS_BY_ID` are both in scope -- so a typo is refused
    by name (`OUTCOME_GMPROBE_UNKNOWN_VARIANT`), never rounded to the
    nearest known id.

    THE SAME "REGARDLESS OF SOURCE" GUARD `warp_executor`/`say_wire` apply
    to their own `command.args` reads.  `parse_gm_command` always hands back
    a real 1-tuple of `str`, but this module accepts a `GmCommand`
    regardless of where it came from (see `GmCommandArgsError`'s docstring
    in `commands.py`), so a hand-built one with the wrong SHAPE must not
    raise a bare `TypeError`/`IndexError` out of this function -- `type(args)
    is not tuple`, not `isinstance`, for the same tuple-subclass reason
    `warp_executor._require_args_tuple`'s own comment gives.

    NONCLAIM, carried from `bt_gm_probe`'s own module docstring: composing
    and sending this frame is not evidence that anything renders on a
    client.  Whether `GMUI_BASIC` opens for a given variant is a
    client-observable fact only an attended `GT-164` run can produce.
    """
    args = command.args
    if type(args) is not tuple or len(args) != 1:
        _note(session, f"{EVENT_GMPROBE_REFUSED_PREFIX}GmProbeArgsShape")
        return _Verdict(
            None, f"{OUTCOME_REFUSED_PREFIX}gmprobe_GmProbeArgsShape"
        )

    variant = bt_gm_probe.variant_by_id(args[0])
    if variant is None:
        _note(session, EVENT_GMPROBE_UNKNOWN_VARIANT)
        return _Verdict(None, OUTCOME_GMPROBE_UNKNOWN_VARIANT)

    try:
        pc, frame = bt_gm_probe.build_variant_frame(legacy, variant)
    except Exception as error:  # noqa: BLE001 - a composer failure must
        # surface as a named refusal, never an exception escaping onto the
        # shared listener thread.  Type name only, same reasoning as every
        # other refusal in this module.
        _note(session, f"{EVENT_GMPROBE_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(
            None, f"{OUTCOME_REFUSED_PREFIX}gmprobe_{type(error).__name__}"
        )

    return _Verdict((GMPROBE_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED)


def _selected_speed_identity(session: object) -> tuple[int | None, int | None]:
    """`identity_lo`/`identity_hi` off the connection's own selected character.

    Reads `session.foundation.selected` the exact same way
    `_current_position` reads it for `.position` -- CORE-REQUEST-GM-049's
    letter named this as the one field `gm/` had no read site for yet, even
    though `model.Character` (`id, account_id, selector, name, actor_wire,
    avatar_wire, identity_lo, identity_hi, position`) has carried it all
    along.  `(None, None)` for "no character selected on this connection" or
    for a value this module cannot trust as an `int` (a test double, a
    half-built session); never raises.  `bool` is excluded for free by the
    `type(...) is not int` check -- `type(True) is bool`, not `int`.
    """
    selected = getattr(getattr(session, "foundation", None), "selected", None)
    if selected is None:
        return None, None
    identity_lo = getattr(selected, "identity_lo", None)
    identity_hi = getattr(selected, "identity_hi", None)
    if type(identity_lo) is not int or type(identity_hi) is not int:
        return None, None
    return identity_lo, identity_hi


def _speed_store(session: object) -> object | None:
    """The ONE read site for the store `/speed` both checks and writes to.

    `_speed_db_filename` (the run-copy gate) and `_persist_speed` (the row
    write) must never disagree about WHICH database they mean -- a gate that
    inspected one object and a write that landed in another would be a gate
    in name only.  Spelling the attribute chain once, here, is what makes
    that divergence impossible to introduce by editing one of them.

    `None` for any break in `session.foundation.lifecycle.store`; never
    raises, the same posture `_selected_speed_identity` states for itself.
    """
    return getattr(
        getattr(getattr(session, "foundation", None), "lifecycle", None),
        "store",
        None,
    )


def _speed_undo(store: object, character_id: int) -> object:
    """A zero-argument callable that puts `speed_walk` back where it was.

    WHY `/speed` NEEDS ONE AT ALL (pf-adversary round `hw6dix`, D1).  Since
    this command started writing a row, it became the SECOND handler in this
    module with durable state -- and `_make_action`'s own comment states the
    house rule for that: "AN EFFECT THAT IS ALREADY ON DISK HAS TO COME BACK
    OFF IT" when the outcome row cannot be written.  Without this, an audit
    append that failed between the `issued` row and the `outcome` row left
    the column at the new value while the console printed "anything it had
    in hand was dropped with it", which was measurably false.

    READ BEFORE THE WRITE, ON PURPOSE, and here is what that does and does
    not buy.  The previous value is read on its own connection before the
    store door runs (~~`write_typed_attributes_and_compose_sparse`~~ --
    `store.write_speed_by_identity` since round `ntf90h`; it is read before
    either), so a concurrent writer in that window makes this undo restore
    WHAT THIS COMMAND SAW, not whatever was there an instant before the
    write.  That is weaker than
    `login_scene_stage.restore_login_scene`'s undo, which re-validates the
    whole file it is putting back.  It is not made stronger by pretending:
    the alternative -- reading inside LANE-DB's transaction -- would need an
    API in their zone that does not exist, and this lane does not add one.

    RETURNS FALSE RATHER THAN RAISING, always.  Three honest failures:
    the column was NULL before (a first-ever `/speed` for this character --
    `write_typed_attributes` refuses `None` outright and this API offers no
    way to clear a column back to NULL, so there is nothing to put back);
    the store cannot be read; the restoring write itself fails.  A `False`
    surfaces as `EVENT_OUTCOME_STAGE_NOT_REVERTED`, which is the truth.

    Migration `008` NARROWS the first of those three and does not remove it
    (`COO-DECISION 20260902_1147`).  It ran `UPDATE characters SET
    speed_walk = 400.0 WHERE speed_walk IS NULL`, so a character holding
    NULL at that moment now has this undo restore 400.0 instead of reporting
    nothing to put back.  A character `/speed` had already written keeps what
    it held -- the predicate skips it.

    ~~"and a character created afterwards still reaches this undo NULL,
    because `SQLiteStore.create_character` does not write THIS column"~~ --
    STRUCK in round `selrsl`.  `migrations/009_character_birth_defaults.sql`
    is on `main` (merge `f5b3fd1`) and rebuilds `characters` with
    `speed_walk` carrying `DEFAULT 400.0`.  `create_character` still names
    three columns and not this one -- that half of the old sentence is
    unchanged -- but for a character born AFTER `009` ran, the column it
    leaves alone is no longer NULL: SQLite supplies the default.  LANE-DB
    said it first, from their own side, in `notes_to_chief/20260902_2140_
    LANE-DB-NOTICE-lane-gm-your-speed-undo-null-branch-is-unreachable-after-
    009.md`, and their scope is the one that holds: **a character born on a
    database that already carries `009`**.

    ~~"So on any database that has run `009`, a first-ever `/speed` no longer
    reaches the NULL branch at all"~~ -- STRUCK IN THE ROUND THAT WROTE IT
    (pf-adversary, round `selrsl`, D1, measured on sqlite3 rather than read
    off the migration's prose).  `009` REBUILDS the table and its
    `INSERT INTO characters_rebuild (...) SELECT ... speed_walk ... FROM
    characters` NAMES the column, and a `DEFAULT` applies only to a column an
    INSERT OMITS -- so a row already holding NULL is copied through STILL
    NULL.  `008` backfilled the cohort alive when `008` ran; a character
    created after `008` and before `009` holds NULL, survives the rebuild
    holding NULL, and its first-ever `/speed` walks this branch ON A DATABASE
    THAT HAS RUN `009`.  The quantifier was the error, not the direction.

    THE BRANCH STAYS, and it is NOT dead code.  `previous is None` is reached
    by: a character born between `008` and `009` and never `/speed`-ed since
    (above); a row on a file that never ran `009` at all; a store with no
    `read_typed_attributes`; a read that RAISES (caught right below and
    folded into `previous = None`); and a store that is not `SQLiteStore`.
    What `009` retired is exactly one source -- the first-ever `/speed` of a
    character born after it -- and a reader deleting the branch on the
    strength of "009 makes it unreachable" would be deleting a live path.

    ~~"because `SQLiteStore.create_character` writes no typed column at all
    today"~~ -- STRUCK, and the correction is COO-DECISION `20260902_1948`
    item 3, which is right: LANE-DB's birth plug `009` landed on `main` and
    `store.py:create_character`'s INSERT now carries `level, hp_current,
    hp_max` (read at HEAD, not quoted from a letter).  `speed_walk` is NOT
    among them.  ~~"so THE CONCLUSION ABOVE IS UNCHANGED -- a character
    created today still reaches this undo with the column NULL"~~ -- STRUCK
    in round `selrsl`: `009` landed after this paragraph was written and puts
    `400.0` in that column at birth, so a character created TODAY does not.
    Read the `009` paragraph above for what is and is not retired; this one
    is kept only for what it still says truthfully, which is that
    `create_character` names three columns and none of them is this one.
    COO's hazard stands and is why nothing here is deleted: the next reader
    adds `speed_walk` to that INSERT believing this docstring already
    describes their change, and this undo silently stops being the "nothing
    to put back" case it documents.

    The event names `_make_action` writes still say `STAGE` -- they were
    minted for the staged-login-scene undo and are pinned by the event-name
    contract table.  Renaming them to cover a second handler is a separate,
    louder change than this fix; recorded here rather than left for a reader
    of the audit trail to wonder about.
    """
    read = getattr(store, "read_typed_attributes", None)
    write = getattr(store, "write_typed_attributes", None)
    previous = None
    if callable(read):
        try:
            previous = read(character_id).get(SPEED_TYPED_COLUMN)
        except Exception:  # noqa: BLE001 - an unreadable prior value is a
            # refused undo, never a crash on the listener thread.
            previous = None

    def _undo() -> bool:
        if previous is None or not callable(write):
            return False
        try:
            write(character_id, {SPEED_TYPED_COLUMN: previous})
        except Exception:  # noqa: BLE001 - see docstring
            return False
        return True

    return _undo


def _selected_speed_character_id(session: object) -> int | None:
    """`characters.id` off the connection's own selected character.

    ~~"LANE-DB's persistence entry point is keyed by `character_id`, not by
    `identity_lo`/`identity_hi` ... so the method LANE-GM asked LANE-DB for in
    `20260902_0017` (an identity_lo/hi-keyed overload) TURNED OUT NOT TO BE
    NEEDED: this read is the whole translation, and it lives in this lane
    where it belongs rather than adding an API to theirs."~~ -- STRUCK in
    round `ntf90h`, and it is the flatly wrong half: LANE-DB DID build that
    overload (`store.write_speed_by_identity`, handed back in their letter
    `pf_bridge/notes_to_chief/20260903_0635_LANE-DB-TO-LANE-GM-the-speed-
    write-door-is-built.md`; their own docstring for that method cites their
    earlier `20260903_0525`, so a reader chasing one ID should know both
    exist), and `_speed_action` calls it.  pf-adversary (round `ntf90h`, D6)
    found this paragraph and the commit body citing the SAME letter to
    opposite conclusions.

    WHAT THIS READ IS STILL FOR, which is narrower than it was: `_speed_undo`
    restores through `write_typed_attributes`, which IS keyed by
    `character_id`.  The write itself is not keyed by it any more.

    `None` for "no character selected" or for an id this module cannot trust
    as a positive `int` (a test double, a half-built session).  `bool` is
    excluded for free by `type(...) is not int`.  A non-positive id is
    refused rather than passed down: SQLite rowids start at 1, so `0`/`-1`
    is a sentinel that leaked, and handing it to a keyed write would look
    like a real lookup miss instead of the read fault it is.
    """
    selected = getattr(getattr(session, "foundation", None), "selected", None)
    character_id = getattr(selected, "id", None)
    if type(character_id) is not int or character_id <= 0:
        return None
    return character_id


# CORE-REQUEST-GM-049's run-copy-DB requirement (`pf_bridge/notes_to_chief/
# 20260901_1728_LANE-GM-CORE-REQUEST-GM-049-speed-sparse-x7-runtime-send-
# point.md`).  The literal is cited from its one authoritative source:
# `app.py:660-664` builds `db_path` from `known.db or str(root / (... else
# 'state/pirateforce.sqlite3'))` -- `pirateforce.sqlite3` is the filename
# this process's default DB path ends in when no `--db` is passed, and a
# run-copy boot always passes an explicit different `--db` value (see
# `pf_bridge/GAME_TEST_QUEUE.md`'s GT-193 db section: a timestamped filename
# per run).
CANONICAL_DB_FILENAME = "pirateforce.sqlite3"


def _speed_db_filename(session: object) -> str | None:
    """The last path component of the DB `session`'s process booted with.

    Reads `session.foundation.lifecycle.store.path`
    (`FoundationSession.lifecycle` -> `CharacterLifecycle.store` ->
    `SQLiteStore.path`; `session.py:35`, `lifecycle.py:9`, `store.py:26`) --
    the same live string production code elsewhere in this file already
    dereferences (`session.py:49,54,68,252,261`), read here the same
    attribute-chain way `_selected_speed_identity` above reads
    `session.foundation.selected`.  Defensive at every step: a missing link
    anywhere in the chain, or a `path` that is not a non-empty `str`,
    returns `None` rather than raising -- a read for a SAFETY gate must
    never become the reason the gate crashes instead of refusing.

    Splits on BOTH `/` and `\\`.  `pf_bridge` composes the `/speed` command
    on a Windows bridge machine while this checked-out clone is Linux, and
    `os.path.basename` only ever splits on the separator of the platform IT
    is running on -- on Linux it would leave a Windows-style
    `state\\pirateforce.sqlite3` path whole instead of isolating the
    filename, and a whole path never equals the bare canonical literal.
    """
    path = getattr(_speed_store(session), "path", None)
    if type(path) is not str or not path:
        return None
    return path.replace("\\", "/").rsplit("/", 1)[-1]


# Every way Windows lets one file answer to more than one name, as far as a
# STRING can see it.  pf-adversary (round `hw6dix`, D3) measured the previous
# exact `==` comparison authorizing a WRITE to the canonical database through
# all of these, because `app.py:660` keeps the operator's `--db` string
# verbatim -- no `resolve()`, no normalization:
#
#   state\PirateForce.sqlite3        case (NTFS is case-insensitive)
#   state\pirateforce.sqlite3 	     trailing space
#   state\pirateforce.sqlite3.       trailing dot
#   state\pirateforce.sqlite3::$DATA the NTFS default data stream
#   state\PIRATE~1.SQL               the 8.3 short name
#
# The first four are normalized away below.  The fifth CANNOT be resolved
# from a string, so a `~<digits>` name is refused outright -- an 8.3 alias is
# never what a GT-193 run-copy boot passes, and "cannot tell" has to mean
# "refuse" on a gate that now guards a write.
NTFS_STREAM_SEPARATOR = ":"
SHORT_NAME_MARKER = "~"


def _speed_db_normalized_filename(filename: str) -> str:
    """The filename as Windows would resolve it, minus the aliases a string
    can see.  Case-folded last, so the caller compares one lowered form."""
    # The stream suffix first: `a.sqlite3::$DATA` -> `a.sqlite3`.  Everything
    # from the first `:` on is a stream name, never part of the file's own.
    filename = filename.split(NTFS_STREAM_SEPARATOR, 1)[0]
    # Windows silently drops trailing dots and spaces when opening a path,
    # so `x.sqlite3.` and `x.sqlite3 ` open `x.sqlite3`.
    return filename.rstrip(". ").casefold()


def _speed_db_is_canonical(session: object) -> bool:
    """True unless this process can be PROVEN to be on a non-canonical DB.

    "Proven" means: the full attribute chain to `store.path` read, and its
    filename read -- after the Windows-alias normalization above -- as
    something other than the canonical literal.  Anything short of that is
    "cannot prove this is safe", which this function treats identically to
    "proven canonical": refused, never assumed safe.  That covers the
    canonical filename itself, a chain this function could not walk at all
    (a test double, an unusual session shape), and an 8.3 short name.

    ONE REAL CHECK ON TOP OF THE STRING, when the filesystem can answer it:
    if a file named `pirateforce.sqlite3` sits in the SAME directory as this
    process's DB and the two are the same file, this refuses -- `samefile`
    sees through case, 8.3 aliases, hard links and junctions, which no amount
    of string work does.  Any error asking that question is itself a refusal.
    It cannot see a canonical copy living in a DIFFERENT directory under a
    different name; that limit is unchanged and is stated in `_speed_action`'s
    own docstring.
    """
    filename = _speed_db_filename(session)
    if filename is None:
        return True
    normalized = _speed_db_normalized_filename(filename)
    if normalized == CANONICAL_DB_FILENAME.casefold():
        return True
    if SHORT_NAME_MARKER in normalized:
        # An 8.3 alias resolves only against a live filesystem, and this may
        # be running on the wrong OS to ask.  Refuse rather than guess.
        return True
    return _speed_db_is_the_canonical_file_on_disk(session)


def _speed_db_is_the_canonical_file_on_disk(session: object) -> bool:
    """True when this process's DB IS the canonical file under another name.

    Fails closed: an unreadable path, a raising `samefile`, anything at all
    other than a clean "these are two different files" answers True.  The one
    case that answers False without asking is a sibling canonical file that
    does not exist -- there is then nothing for this DB to be an alias OF, in
    this directory, which is the only directory this check can speak about.
    """
    path = getattr(_speed_store(session), "path", None)
    if type(path) is not str or not path:
        return True
    try:
        import os

        directory = os.path.dirname(path.replace("\\", "/"))
        sibling = os.path.join(directory, CANONICAL_DB_FILENAME)
        if not os.path.exists(sibling):
            return False
        return os.path.samefile(path, sibling)
    except Exception:  # noqa: BLE001 - see docstring; cannot ask => refuse
        return True


def _speed_denied(
    session: object,
    legacy: object,
    outcome: str,
    undo: object | None = None,
) -> _Verdict:
    """One refused `/speed`, with the on-screen sentence attached when it can
    be built -- COO-DECISION `0345`, path 1.

    THE REFUSAL IS THE PRODUCT, THE SENTENCE IS THE COURTESY.  This function
    can only ever ADD an action to a verdict that was going to be
    `_Verdict(None, outcome, undo)`; the outcome word, the `undo` and the
    event already noted by the caller are passed through untouched.  A notice
    that cannot be composed is NAMED and dropped, never raised: an on-screen
    courtesy must not turn a named refusal into
    `gm_chat_action_unexpected_<Type>` on the listener thread, which is this
    module's own standing rule for diagnostics (`_note_npc_recompose_
    diagnostic`, `A DIAGNOSTIC MAY NEVER ALTER DISPATCH`).

    `audit_outcome` deliberately keeps the `refused_*`/`withheld_*` word even
    though bytes now go out.  LANE-GM's letter `20260902_0419` (question 2)
    settled why: the `outcome` column answers "did the command have its
    effect?", not "did any byte leave", and a `/speed` the DB refused was
    refused whether or not the GM was told about it.
    """
    try:
        pc, frame = say_wire.make_local_talk_notice_frame(
            legacy, say_wire.SPEED_DENIED_NOTICE_TEXT
        )
    except Exception as error:  # noqa: BLE001 - includes NoticeWireError
        _note(
            session,
            f"{EVENT_SPEED_DENIED_NOTICE_FAILED_PREFIX}{type(error).__name__}",
        )
        return _Verdict(None, outcome, undo)
    _note(session, EVENT_SPEED_DENIED_NOTICE_COMPOSED)
    return _Verdict(
        (SPEED_DENIED_NOTICE_ACTION_LABEL, pc, frame, 0.0),
        outcome,
        undo,
        is_notice=True,
    )


def _speed_action(session: object, command: object, legacy: object) -> _Verdict:
    """One authorized `/speed <value>` -> a sparse `UpdateAttrVital` action.

    CORE-REQUEST-GM-049 (`pf_bridge/notes_to_chief/20260901_1728_LANE-GM-
    CORE-REQUEST-GM-049-speed-sparse-x7-runtime-send-point.md`): composes
    through `gm.speed_wire.compose_sparse_speed_update`, the ONE frame that
    module exists to build -- x=7 (BasicAttr +0x54, f32) alone, never any of
    the other 54 fields `attr_wire.FIELDS` describes, never a merge with any
    prior block.  No new wire logic lives here, the same seam
    `_warp_action`/`_say_action`/`_gmprobe_action` use for their own
    composers.

    !! WHAT THIS SENDS AND TO WHOM, same property `_say_action` states for
    itself: one action goes to ONE socket, the connection whose frame this
    dispatch is answering.  It moves nobody -- `x=7` is a single BasicAttr
    field, not a position.

    !! AND SINCE GT-193 IT SENDS NOTHING AT ALL.  Attended round R303
    (2026-09-02) typed `/speed 300` on a real client: this function's frame
    went out, the character showed HP 0 and money 0 and DIED, and the client
    then answered nothing at all (426 inbound frames, zero of them
    non-heartbeat -- the revive buttons never reached the server).  The run DB
    was healthy throughout, so the client reacted to BYTES THIS LANE SENT.
    Which byte killed the character is NOT known and this function does not
    pretend it is (the tester's own nonclaim).  TWO gates stand between the
    read-back and the composer now, both below the DB write:

      * COO-DECISION `20260902_1847` -- every frame of this door is DEFERRED,
        whatever its shape, until LANE-DB lands the `speed_walk` login read on
        `main` (`speed_wire.send_deferred`).  Unconditional today.  The route
        prints `SPEED DEFERRED` and returns no action.
      * the GT-193 shape hold -- has a real client been measured accepting
        THIS shape (`speed_wire.shape_cleared`, keyed on the signature
        `declared_empty_sections` returns; today that set is empty, so the
        answer is always no).

    ~~"it fires BEFORE the DB write, so a held frame never leaves a moved row
    behind it"~~ -- STRUCK: COO `1847` ruled the other way in the same letter
    ("the DB write continues as before; what has to stop is the outbound
    frame, and only that"), so both gates moved below the write.  See
    `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT`,
    `speed_wire.SPEED_LOGIN_READ_LANDED`, `tests/test_gm_speed_shape_hold.py`
    and `tests/test_gm_speed_deferred.py`.

    !! IT NOW WRITES A DB ROW.  ~~"writes no DB row: this composes a WIRE
    FRAME only, never touching `store`/`characters`"~~ -- struck, not
    deleted, because it was true of every earlier round of this function and
    a reader of an old audit line needs to know when it stopped being true.
    LANE-DB's `store.write_typed_attributes_and_compose_sparse` landed on
    `main` and their letter `pf_bridge/notes_to_chief/20260901_2213_LANE-DB-
    TO-LANE-GM-speed-sparse-live-on-main-but-speed-does-not-persist.md`
    named the consequence of not calling it: `GT-193` would have graded a
    frame, not a memory, and `/speed 400` would be gone by the next login.
    ~~"This function now calls it FIRST and composes from its read-back"~~ --
    the ORDER is unchanged and the read-back is still the source, but the
    DOOR is not that one any more: this function calls
    `store.write_speed_by_identity(identity_lo, identity_hi, value)`, the
    method this lane asked LANE-DB for in `20260902_0017` and they handed
    back in `20260903_0635`.  Read the DB FIRST block in the body for what
    that swap buys (a refusal that means the row is UNTOUCHED, which the
    composing door could not promise) and what it costs (one anonymous
    `None` where there used to be an exception type name).  Everything in
    the list below still holds, with the second bullet's "named by
    `characters.id`" now reading "named by the identity pair the door looks
    the row up from, off this connection's own selected character":

      * the ORDER is DB -> wire, and a store refusal means NO FRAME AT ALL
        ([ASSUMPTION OF LANE-GM, AWAITING COO] -- `pf_bridge/notes_to_chief/
        20260902_0017_LANE-GM-ASK-COO-speed-db-first-ordering-change.md`;
        before this round a parse-clean value ALWAYS sent);
      * the row is named by `characters.id` off this connection's own
        selected character (`_selected_speed_character_id`), never by an id
        this module was handed;
      * the composed number is the store's read-back, not the GM's typed
        text -- see the WIRE SECOND comment in the body;
      * the run-copy-DB gate below is now load-bearing for a WRITE, not just
        for a send, and it fails closed (an unreadable store path counts as
        canonical and refuses).  `ห้ามแตะ canonical DB` is a project rule,
        not a preference, and this is the only thing standing between this
        function and breaking it.

    THE VERSION GATE IS A SCOPED, TEMPORARY EXCEPTION, NOT THE GENERAL ONE.
    `speed_wire.shared_vital_version_confirmed()` reads
    `attr_wire.UPDATE_ATTR_VITAL_VERSION_CONFIRMED` live, which
    `COO-DECISION 2026-09-01T18:47+07:00` flipped `None` -> `0` for exactly
    this send site (see that constant's own comment in attr_wire.py for the
    full reasoning) -- it is not evidence attr_wire.py's own three-point
    full-block unlock has been answered, and this function must never be
    copied as a template for a full-block send.

    IDENTITY HAS NO ESTABLISHED READ SITE OF ITS OWN, UNLIKE POSITION.
    `_selected_speed_identity` mirrors `_current_position`'s read of
    `session.foundation.selected` exactly, but for `identity_lo`/
    `identity_hi` rather than `.position` -- a connection with no character
    selected yet (or a test double missing the fields) is a named refusal,
    never a crash.

    !! RUN-COPY DB REQUIREMENT -- ENFORCED HERE, AS A FILENAME HEURISTIC,
    NOT THE CRYPTOGRAPHIC GUARANTEE A PRIOR DRAFT OF THIS DOCSTRING WOULD
    HAVE IMPLIED BY SAYING NOTHING.  CORE-REQUEST-GM-049's letter requires
    "the send site must check it is running on a run-copy DB before every
    send" (never canonical).  An earlier round of this docstring claimed no
    code-level mechanism existed anywhere in this repository to tell "booted
    against a run-copy" from "booted against canonical" -- THAT CLAIM WAS
    FALSE, and pf-adversary measured the gap it excused as live-reachable:
    `session` already carries `session.foundation.lifecycle.store.path`
    (`FoundationSession.lifecycle` -> `CharacterLifecycle.store` ->
    `SQLiteStore.path`; `session.py:35`, `lifecycle.py:9`, `store.py:26`), the
    exact live path string this process booted against, read the same
    attribute-chain way `_selected_speed_identity` above already reads
    `session.foundation.selected`, and already dereferenced by production
    code elsewhere in this same file (`session.py:49,54,68,252,261`).
    `_speed_db_is_canonical` below reads it defensively (never raises; a
    chain it cannot walk is treated as "cannot prove this is safe", i.e.
    refused, never as "assume safe") and compares its filename -- split on
    both `/` and `\\`, since `pf_bridge` composes this command on a Windows
    bridge machine while this clone is Linux and `os.path.basename` alone
    would not isolate the name out of a `state\\pirateforce.sqlite3` style
    path -- against the literal `"pirateforce.sqlite3"`, the canonical
    default `app.py:660-664` builds when `--db` is not passed.  Run FIRST in
    this function, before the identity read and the version-gate read below:
    a wrong-DB refusal is the more fundamental safety gate and must not
    depend on a character having been selected first.

    THE LIMIT, STATED PLAINLY RATHER THAN OVERSOLD: this is a filename
    heuristic, not a cryptographic guarantee of anything about the bytes on
    disk.  A bridge script that named a real production copy of the DB
    `pirateforce.sqlite3` in some other directory would fool this check into
    sending against it; a run-copy DB that happened to be renamed back to
    the canonical filename would fool this check into withholding a send
    that was actually safe.  It proves nothing beyond the name the path
    string ends in.
    """
    if _speed_db_is_canonical(session):
        # The more fundamental gate: refuse before either read below, so a
        # wrong-DB refusal never depends on a character being selected.
        _note(session, EVENT_SPEED_WITHHELD_CANONICAL_DB)
        return _speed_denied(session, legacy, OUTCOME_SPEED_WITHHELD_CANONICAL_DB)

    identity_lo, identity_hi = _selected_speed_identity(session)
    if identity_lo is None or identity_hi is None:
        _note(session, EVENT_SPEED_NO_SELECTED_CHARACTER)
        return _speed_denied(session, legacy, OUTCOME_SPEED_NO_SELECTED_CHARACTER)

    version = speed_wire.shared_vital_version_confirmed()
    if version is None:
        # The scoped exception above has not (or no longer) landed --
        # withhold exactly the way `_say_action`/`_warp_action` do for their
        # own still-shut gates.  GT-101 measured what an unproven
        # vital_version does to a real client: modal error, socket closed.
        _note(session, EVENT_SPEED_WITHHELD_NO_VERSION)
        return _speed_denied(session, legacy, OUTCOME_SPEED_WITHHELD_NO_VERSION)

    try:
        value = speed_wire.parse_speed_value(command.args[0])
    except Exception as error:  # noqa: BLE001 - includes SpeedWireError
        # Type name only: an exception message can embed the GM's typed
        # text, same reasoning as every other refusal in this module.
        _note(session, f"{EVENT_SPEED_REFUSED_PREFIX}{type(error).__name__}")
        return _speed_denied(
            session,
            legacy,
            f"{OUTCOME_REFUSED_PREFIX}speed_{type(error).__name__}",
        )

    # ---- DB FIRST ----------------------------------------------------
    # Everything from here to the compose below is the persistence half.
    # Read the `EVENT_SPEED_NO_STORE` comment block for the ordering
    # decision and the letter it is still waiting on.
    #
    # THE WRITE GOES THROUGH LANE-DB'S IDENTITY DOOR, AND THE REASON IS ONE
    # SENTENCE THIS ROUTE COULD NOT SAY BEFORE.
    # ~~`persist = store.write_typed_attributes_and_compose_sparse` ...
    # `sparse = persist(character_id, {SPEED_TYPED_COLUMN: value})`~~ --
    # STRUCK, not deleted: it was this route's write for four rounds and a
    # reader of those audit rows needs to know when it stopped being one.
    # That door COMPOSES AFTER IT COMMITS, so its raise can land on either
    # side of a durable change -- which is why `_speed_undo` exists at all,
    # and why the struck comment on it said, correctly, that "this branch
    # refused" was not the same as "this branch changed nothing".
    #
    # `store.write_speed_by_identity(identity_lo, identity_hi, value)` is the
    # door THIS LANE ASKED FOR (`pf_bridge/notes_to_chief/20260902_0017_LANE-
    # GM-TO-LANE-DB-request-speed-persistence-method.md`), built by LANE-DB to
    # that letter's shape and handed back in `20260903_0635_LANE-DB-TO-LANE-
    # GM-the-speed-write-door-is-built.md`.  Its contract IS the property:
    # every refusal raises INSIDE the transaction, so `None` means the row is
    # exactly as it was, never "written, then something went wrong".
    # `GT-193` step 6 is a diff of that row, and until now no refusal word on
    # this route could tell a tester which side of the write it was on.
    #
    # WHAT THE SWAP COSTS, SAID PLAINLY RATHER THAN LEFT TO BE DISCOVERED.
    # The old door named its failure by exception TYPE
    # (`refused_speed_persist_TypedAttrError`).  This one collapses every
    # refusal -- a value `validate` rejects, a schema this database does not
    # have, a lock it could not take within `busy_timeout`, no single active
    # row for the pair -- into one `None`, by design ("a caller that needs the
    # REASON must use `write_typed_attributes`, which names it").  This lane
    # takes the trade: for an attended tester the durable question outranks
    # the diagnostic one, and the old word could not answer the durable one at
    # all.  Nothing here reaches for the naming door as a second attempt: two
    # writes for one command is how two ideas of "refused" get built.
    #
    # A SECOND THING THE SWAP DROPPED, NAMED HERE BECAUSE pf-adversary (round
    # `ntf90h`, D7) HAD TO FIND IT RATHER THAN READ IT.  The old door ended in
    # `persistence_attr_compose.compose_sparse_block`, whose own docstring
    # calls itself "the ONLY thing between a caller and SENSITIVE_FIELDS" on
    # that path; the new door composes through `typed_values_for_compose` and
    # does not apply `SPARSE_APPROVED_FIELDS`.  Nothing downstream re-applies
    # it either -- `speed_wire.compose_sparse_speed_update` builds
    # `{SPEED_FIELD_X: fvalue}` directly.  That gate is a NO-OP FOR THIS ROUTE
    # TODAY, and only because of an equality nobody had written down: the
    # approved set is exactly `{speed_wire.SPEED_FIELD_X}`.  pf-adversary
    # measured both doors over `400.1, -0.0, 0.0, 620.0, 1e-46, 3.4e38` and
    # got identical composed dicts and BYTE-IDENTICAL frames, so no byte
    # changed -- but the day that set stops being exactly this one field, this
    # route composes past a policy gate.  `tests/test_gm_speed_action.py` pins
    # the equality so that day is a red test rather than a silent widening.
    store = _speed_store(session)
    persist = getattr(store, "write_speed_by_identity", None)
    if not callable(persist):
        # A session shape with no store to write to is NOT "send the frame
        # anyway": that is precisely the screen-disagrees-with-the-row case
        # this ordering exists to make impossible.  A store that predates
        # LANE-DB's door earns the SAME refusal rather than falling back to
        # the composing write -- a silent fallback would put the two
        # meanings of "refused" back into one route.
        _note(session, EVENT_SPEED_NO_STORE)
        return _speed_denied(session, legacy, OUTCOME_SPEED_NO_STORE)

    character_id = _selected_speed_character_id(session)
    if character_id is None:
        _note(session, EVENT_SPEED_NO_CHARACTER_ID)
        return _speed_denied(session, legacy, OUTCOME_SPEED_NO_CHARACTER_ID)

    # Built BEFORE the write, because it has to remember what was there
    # first.  Carried by the verdicts BELOW the write -- and NOT by the
    # `row_not_touched` branch, which is the whole point of the swap.
    #
    # IT STILL NAMES THE ROW BY `character_id` WHILE THE WRITE NAMES IT BY
    # THE IDENTITY PAIR, and that difference is stated rather than hidden.
    #
    # ~~"in production both come off the same `session.foundation.selected`
    # row, and the door refuses outright unless the pair matches EXACTLY ONE
    # active character, so a session that could make them disagree is one
    # where the write never lands"~~ -- STRUCK IN THE ROUND THAT WROTE IT.
    # pf-adversary (D5) showed the second half is a non-sequitur: "the pair
    # matches exactly one ACTIVE row" constrains the identity side only and
    # never ties that row to `selected.id`.  And identity reuse is DESIGNED
    # here, not hypothetical: `store.build_wire` derives `lo,hi` from the
    # SELECTOR, and `migrations/004_character_soft_delete_reuse.sql` says in
    # its own header that a soft-deleted slot can be recreated in place with
    # the same selector and the same derived identity.  So a stale
    # `session.foundation.selected` could in principle name row A while the
    # pair now resolves to a recreated row B.
    #
    # WHAT ACTUALLY HOLDS, stated as what it is -- a fail-closed OUTCOME, not
    # a proof of impossibility.  `store.soft_delete_character` refuses for a
    # character any open session has selected, and pf-adversary could not
    # build the divergent state through the API.  If it were reached anyway,
    # `write_typed_attributes` re-checks `deleted_at IS NULL` and raises, so
    # this undo returns False and reports `EVENT_OUTCOME_STAGE_NOT_REVERTED`
    # honestly rather than writing the wrong row.  Narrowing the undo to the
    # door's own lookup would need an API in LANE-DB's zone that does not
    # exist, and this lane does not add one (same posture as this undo's
    # docstring).
    undo = _speed_undo(store, character_id)

    try:
        sparse = persist(identity_lo, identity_hi, value)
    except Exception as error:  # noqa: BLE001 - the door contracts NOT to
        # raise across `gm/`'s boundary; this branch is what happens when
        # something breaks that contract (a store double, a future edit).
        # The state it leaves behind is unknown, so the undo IS carried here
        # and the console sentence for this prefix still says the rest.
        _note(
            session,
            f"{EVENT_SPEED_PERSIST_REFUSED_PREFIX}{type(error).__name__}",
        )
        return _speed_denied(
            session,
            legacy,
            f"{OUTCOME_SPEED_PERSIST_REFUSED_PREFIX}{type(error).__name__}",
            undo,
        )

    if sparse is None:
        # THE ONE SENTENCE THE OLD DOOR COULD NOT SAY.  `None` is this door's
        # only failure report and it is an honest one: the row is untouched.
        # NO UNDO IS CARRIED, deliberately -- there is nothing to put back,
        # and handing one over would let `_make_action` report a revert of a
        # write that never happened, which is the same class of false audit
        # line this whole persistence half was built to stop.
        _note(session, EVENT_SPEED_ROW_NOT_TOUCHED)
        return _speed_denied(session, legacy, OUTCOME_SPEED_ROW_NOT_TOUCHED)

    # ---- WIRE SECOND, FROM THE ROW, NOT FROM THE TYPED TEXT ----------
    # The composed value comes out of the store's own read-back rather than
    # `value`, so the number on the client is by construction the number the
    # database holds.  `validate` rounds an f32 on the way in (`400.1` is
    # stored as `400.1000061035156`), which is exactly the divergence a
    # caller-side compose would hide.
    stored = sparse.get(speed_wire.SPEED_FIELD_X) if isinstance(sparse, dict) else None
    if isinstance(stored, bool) or not isinstance(stored, (int, float)):
        _note(session, EVENT_SPEED_PERSIST_READBACK_UNUSABLE)
        return _speed_denied(
            session, legacy, OUTCOME_SPEED_PERSIST_READBACK_UNUSABLE, undo
        )

    # ---- COO 1847: THE ROW IS WRITTEN, THE FRAME IS NOT SENT ---------
    # THE FIRST GATE ON THIS SIDE OF THE WRITE, AND IT IS UNCONDITIONAL
    # TODAY.  COO-DECISION 2026-09-02T18:47+07:00 after the R303 attended
    # round: `/speed 300` went out of this function, the character showed
    # HP 0 and money 0 and DIED, and the client then LOCKED ITSELF -- 426
    # inbound frames, not one of them a click, the revive buttons never
    # sending a byte.  The price of leaving it live is one whole attended
    # round every time the owner types the command, and an attended round is
    # the most expensive resource this project has.
    #
    # WHAT THAT DECISION MOVED, SAID EXACTLY, BECAUSE IT REVERSED THIS
    # FUNCTION'S OWN EARLIER ORDERING.  ~~"Fired BEFORE the row is written,
    # on purpose ... a withheld frame plus a written row is precisely the
    # screen-disagrees-with-the-database case the DB-FIRST ordering exists
    # to prevent."~~  STRUCK, not deleted, because it was this function's
    # reasoning for the shape hold one round ago and a reader of that round
    # needs to see when it stopped being the ordering.  COO `1847` ruled the
    # other way, in one sentence: "THE DB WRITE CONTINUES AS BEFORE -- the DB
    # is already clean; what has to stop is the OUTBOUND FRAME, and only
    # that."  So both gates now stand BELOW the write, and the withheld
    # frame/written row disagreement the struck paragraph feared is accepted
    # deliberately: ~~`speed_walk` has no login read yet either way, so the
    # row is what a later login-read can honour~~ and the frame is what killed
    # a client.  Keeping the row also keeps `GT-193` step 6 (diff the row)
    # gradeable at all.
    #
    # !! THAT STRUCK CLAUSE WAS THE PREMISE, AND IT HAS EXPIRED.  PR #605
    # landed the `speed_walk` login read on `main` -- `session.py:192` calls
    # `login_speed.resolve_for_character(store, id, fallback=player_wire.
    # PLAYER_LOGIN_MOVEMENT_SPEED)` and `player_wire.py:266` encodes the
    # answer -- so the row this route leaves behind is NO LONGER INERT: the
    # next login reads it and puts it on the wire, in the login frame, on a
    # path that has none of this lane's two locks.  `GT-193`'s own recovery
    # step is a re-login.
    #
    # WHAT THIS ROUND DID AND DID NOT DO ABOUT THAT.  It did not change the
    # ordering: COO `1847` ruled "the DB write continues as before" in as many
    # words, and a lane that stopped the write on its own reading of an
    # expired premise would be overriding a decision rather than reporting to
    # it.  What it did was make the console stop under-reporting the write
    # (`_print_speed_deferred`'s row fields) and put the leak in front of the
    # COO by name -- `pf_bridge/notes_to_chief/20260903_0529_LANE-GM-ASK-COO-
    # speed-deferred-names-the-row-and-a-lock-deadlock.md`.  Measured, not
    # inferred: with both locks held, `/speed 300` sends zero bytes and the
    # NEXT login frame carries f32(300.0) where it carried f32(400.0) before.
    #
    # IT IS NOT A GUESS ABOUT WHICH BYTE KILLED THE CHARACTER, and COO `1847`
    # forbids making one: "do not guess which field killed the client and
    # then fix your guess -- your job here is to STOP SENDING, not to repair
    # the frame".  Nothing below composes a different frame; the door holds.
    # ---- COO `0646` ITEM 2: THE ONE RUNTIME KEY, READ ONCE ----------
    # Read HERE, above both holds, and held in a local for the rest of the
    # route so the two gates below cannot disagree with each other: an
    # environment that changed between two separate reads (another thread, a
    # test that patches mid-call) would otherwise be able to produce the one
    # combination neither gate was designed for -- deferral bypassed while the
    # shape hold still stands, or the reverse.  One read, one answer, both
    # gates.
    #
    # `stored`, not `value`: the gate admits ONE f32, and the number this
    # route would actually put on the wire is the store's read-back, not the
    # typed text.  Arming `PF_SPEED_TRIAL=400.1` therefore admits the row's
    # `400.1000061035156`, because `speed_wire.trial_opening` rounds the
    # environment through the SAME f32 trip `persistence_typed_attrs.validate`
    # rounds the row through -- see that function's own docstring.
    trial_admitted = _trial_admits(stored)

    # ---- THE KEY SKIPS THE HOLDS -- IT DOES NOT LOOSEN THEM ---------
    # WHY THIS IS A WRAPPER AND NOT A SECOND TERM IN THE TWO CONDITIONS
    # BELOW, which is what the first draft of this round wrote.  The
    # deferral's own guard is pinned by
    # `tests/test_gm_speed_denied_nine_paths.py::_assert_the_deferral_
    # branch_holds_one_reason` to be ONE call and nothing else, and that
    # pin is pf-adversary's (round `ha492g`, D6): he wrote the mutant
    # `if speed_wire.send_deferred() or <anything>:` and measured 276
    # tests green while a silent refusal wore COO `1847`'s audit word.
    # Writing `and not trial_admitted` into that line turned the pin red,
    # correctly -- a reader cannot tell a term that WIDENS a hold from one
    # that narrows it by looking at the AST, and the pin refuses both
    # rather than guessing.  So the two holds keep their exact conditions,
    # their exact audit words and their exact console lines, and the key
    # decides only whether this route ARRIVES at them.
    #
    # THE GUARD IS DELIBERATELY ONE `not` OVER ONE NAME, for the same
    # reason: a second reason folded in HERE could only ever make the
    # holds MORE likely (this branch is the withholding side), so it
    # cannot hide a silent send -- but it could hide a silent refusal that
    # never reaches either branch's audit word, so
    # `tests/test_gm_speed_trial_gate.py` pins its shape too.
    if not trial_admitted:
        if speed_wire.send_deferred():
            _note(session, EVENT_SPEED_DEFERRED)
            # `line_printed` carries the printer's OWN answer: a console this
            # line could not reach falls through to `GM_CHAT_NO_BYTES_SENT`
            # rather than leaving an accepted command silent.
            # `stored`, not `value`: the read-back is the number the row HOLDS
            # and the number the next login will resolve, and it is the same
            # source the composer below would have used.  See the printer's own
            # "IT NAMES THE ROW IT LEFT BEHIND" paragraph.
            printed = _print_speed_deferred(
                session,
                getattr(session, "token", None),
                getattr(command, "name", None),
                stored,
            )
            # No notice action, and that is the one thing here this lane decided
            # rather than was told -- COO `1847` says "refuse AND PRINT" and its
            # test requirement is "pin that NO BYTES go out on this route", while
            # COO `0345` had ordered refusals to reach the screen through
            # `_speed_denied`'s local-talk notice.  Read together, the narrower
            # reading (zero bytes) is the one that cannot cost an attended round
            # if it is wrong: the GM loses an on-screen sentence, the console
            # still says `SPEED DEFERRED`.  The other reading risks the thing the
            # decision exists to stop.  [ASSUMPTION OF LANE-GM, AWAITING COO --
            # `pf_bridge/notes_to_chief/20260902_2038_LANE-GM-ASK-COO-speed-
            # deferral-drops-the-on-screen-notice.md`]
            return _Verdict(None, OUTCOME_SPEED_DEFERRED, undo, line_printed=printed)

        # ---- THE SHAPE GT-193 MEASURED -----------------------------------
        # THE SECOND LOCK, and unreachable today because the first one above is
        # unconditional -- kept, and kept BELOW the write with it, because the
        # two answer different questions and the round that lifts one must not
        # inherit the other by accident (`speed_wire.send_deferred`'s own comment
        # spells the split: this one is about the BYTES, that one is about
        # whether the number survives the next login).
        #
        # EVERY send needs a clearance, and the shape's signature is the key --
        # `speed_wire.SHAPES_CLEARED_BY_A_REAL_CLIENT` is empty today, so every
        # send is held.  It is NOT "hold only while a section is empty": that was
        # an earlier round's first draft, and pf-adversary measured what it meant
        # (D6) -- a lane that filled the section would have shipped a new,
        # never-measured shape to an attended tester without any clearance at
        # all.  The shape is measured, not hardcoded, so a future round clears
        # exactly the shape it measured and no other.  A composer that raises
        # here is a shape this lane cannot measure, which is not a shape it may
        # put in front of a tester either: that path holds too, rather than
        # falling through to the send.
        #
        # COMPOSED FROM `stored`, NOT FROM `value`, now that it stands below the
        # read-back: the shape is measured off the very number the frame beneath
        # it would carry, which is strictly closer to the shipped frame than the
        # typed value was.  `declared_empty_sections`' own docstring says the
        # shape does not depend on the value and pins it with a test; this
        # ordering no longer has to lean on that pin.
        try:
            shape = speed_wire.declared_empty_sections(
                legacy, identity_lo, identity_hi, stored
            )
        except Exception:  # noqa: BLE001 - unmeasurable shape == held shape
            # `None`, not "an empty section": a shape that could not be measured
            # is never cleared, whatever the clearance set holds -- nothing here
            # knows which shape it would have been.
            shape = None
        if not speed_wire.shape_cleared(shape):
            _note(session, EVENT_SPEED_WITHHELD_SHAPE_UNCLEARED)
            return _speed_denied(
                session, legacy, OUTCOME_SPEED_WITHHELD_SHAPE_UNCLEARED, undo
            )

    try:
        pc, frame = speed_wire.compose_sparse_speed_update(
            legacy, identity_lo, identity_hi, stored
        )
    except Exception as error:  # noqa: BLE001 - includes SpeedWireError
        # ITS OWN WORD, not the pre-write `speed_<ExcType>` one: the row is
        # committed by the time this branch runs, and the pre-write refusal
        # means the opposite (see the EVENT constant's own comment).
        _note(
            session,
            f"{EVENT_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX}"
            f"{type(error).__name__}",
        )
        if trial_admitted:
            # `SPEED_TRIAL_CONSOLE_TOKEN`'s send branch below is dead on
            # every route that exists today (see its own comment) -- this is
            # its replacement, fired from the branch a trial-armed call
            # actually reaches now.  BESIDE the note above, never instead of
            # it: an armed-but-refused `/speed` still gets the ordinary
            # `speed_persist_compose_refused_<ExcType>` audit word, plus this
            # second event naming that the trial key was the reason dispatch
            # got this far at all.
            _note(session, EVENT_SPEED_TRIAL_ADMITTED_BUT_REFUSED)
            _print_speed_trial_armed_refused(
                session,
                getattr(session, "token", None),
                getattr(command, "name", None),
                type(error).__name__,
            )
        return _speed_denied(
            session,
            legacy,
            f"{OUTCOME_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX}"
            f"{type(error).__name__}",
            undo,
        )

    # ---- THE ONE PLACE A `/speed` FRAME LEAVES THIS ROUTE ------------
    # If the runtime key is what got it here, say so -- on the console and in
    # the event trail -- BELOW the compose.  A line that said `sending=` above
    # a composer that then refused would be the console lying about bytes,
    # which is the exact failure `_print_speed_deferred`'s own round was
    # opened to fix.  Both are skipped entirely when the trial admitted
    # nothing, so a future round that opens the two locks properly gets this
    # route back with no trial noise on it.
    if trial_admitted:
        _note(session, EVENT_SPEED_TRIAL_ADMITTED)
        _print_speed_trial_open(
            session,
            getattr(session, "token", None),
            getattr(command, "name", None),
            stored,
        )
    return _Verdict(
        (SPEED_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED, undo
    )


def _lv_notice(
    session: object,
    legacy: object,
    text: str,
    label: str,
    outcome: str,
    undo: object | None = None,
) -> _Verdict:
    """One `/lv` verdict, with its on-screen sentence attached when it composes.

    THE VERDICT IS THE PRODUCT, THE SENTENCE IS THE COURTESY -- the posture
    `_speed_denied` states for itself, and for the same reason: a notice that
    cannot be composed is NAMED and dropped, never raised, because an
    on-screen courtesy must not turn a decided outcome into
    `gm_chat_action_unexpected_<Type>` on the listener thread.

    `is_notice=True` ON BOTH BRANCHES, THE SUCCESS ONE INCLUDED, and that is
    the one place this differs from every other handler in this file.  The
    field's own comment defines a notice as "a sentence ABOUT a command that
    did not run" -- and `/lv`'s success frame is exactly that: the command's
    effect is a DATABASE ROW, and the bytes leaving here say so rather than
    carrying the effect.  Reporting `is_notice=False` for the success would
    tell the two downstream readers ("did the command's frame go out?") that
    a level frame reached the client, which is the claim `GT-218` cost this
    lane the right to make.
    """
    try:
        pc, frame = say_wire.make_local_talk_notice_frame(legacy, text)
    except Exception as error:  # noqa: BLE001 - includes NoticeWireError
        _note(session, f"{EVENT_LV_NOTICE_FAILED_PREFIX}{type(error).__name__}")
        return _Verdict(None, outcome, undo, line_printed=True)
    _note(session, f"{EVENT_LV_NOTICE_COMPOSED_PREFIX}{label}")
    return _Verdict(
        (label, pc, frame, 0.0),
        outcome,
        undo,
        line_printed=True,
        is_notice=True,
    )


def _print_lv_line(session: object, token: str, line: str) -> None:
    """One `GM_LV` console line on STDERR.  Never alters dispatch.

    STDERR, not stdout, for the incident `lane_hooks/__init__.py:117-123`
    records (a stray token line inside a headless replay tool's JSON
    artifact), and wrapped for the reason every printer here is wrapped: a
    `None` stream or a stream that raises costs this line and nothing else.

    NOTHING THE GM TYPED IS EVER PRINTED.  `line` is built by
    `level_command.console_line` out of numbers this module validated and
    the store read back -- never out of the raw chat text, which is the
    property every printer in this module holds.
    """
    if sys.stderr is None:
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}no_stderr")
        return
    try:
        print(f"{LV_CONSOLE_TOKEN} account={token!r} {line}", file=sys.stderr)
    except Exception as error:  # noqa: BLE001 - see the docstring
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _lv_action(
    session: object, command: object, legacy: object, *, token: str
) -> _Verdict:
    """One authorized `/lv <n>` -> a `characters.level` row write.

    PANYA-ORDER 2026-09-06 01:55.  The design, the refusals and the reason no
    frame carrying a level ever leaves here are in `gm/level_command.py`'s
    module docstring; this function is the dispatch half only.

    THE ORDER IS: argument -> canonical-DB gate -> write -> notice.  The gate
    stands ABOVE the write and not beside it, because it is the only thing
    between this command and `AGENTS.md` section 7's `ห้ามแตะ canonical DB` -- the
    same load-bearing position it holds for `/speed`, whose helpers this
    function reuses rather than re-implements.  Those helpers are still named
    `_speed_db_*`: they ask a question about the PROCESS, not about a command,
    and renaming them would touch `/speed`'s own pinned tests for no gain.

    IT MOVES NOBODY AND TELLS NOBODY ELSE.  One row, named by the id of the
    character selected on THIS connection, and one sentence back down THIS
    socket.  Nothing here is per-scene or process-global, so two GMs typing
    `/lv` in one scene write two rows and see two sentences
    (`TWO_SESSIONS_SAME_SCENE`).
    """
    try:
        level = level_command.parse_level(getattr(command, "args", None))
    except level_command.LevelArgumentError as error:
        _note(session, f"{EVENT_LV_REFUSED_PREFIX}{error.reason}")
        _print_lv_line(
            session,
            token,
            f"REFUSED [{error.reason}]: {level_command.usage()}",
        )
        return _lv_notice(
            session,
            legacy,
            say_wire.LV_REFUSED_NOTICE_TEXT,
            LV_REFUSED_NOTICE_ACTION_LABEL,
            f"{OUTCOME_LV_REFUSED_PREFIX}{error.reason}",
        )

    # THE GATE, BEFORE ANY WRITE.  It fails closed: a store path this lane
    # cannot read counts as canonical (`_speed_db_is_canonical`'s own
    # docstring), so the refusal below is what a test double gets too.
    if _speed_db_is_canonical(session):
        _note(session, EVENT_LV_WITHHELD_CANONICAL_DB)
        _print_lv_line(
            session,
            token,
            "WITHHELD [canonical_db]: boot a run copy (--db) to use /lv",
        )
        return _lv_notice(
            session,
            legacy,
            say_wire.LV_REFUSED_NOTICE_TEXT,
            LV_REFUSED_NOTICE_ACTION_LABEL,
            OUTCOME_LV_WITHHELD_CANONICAL_DB,
        )

    store = _speed_store(session)
    character_id = _selected_speed_character_id(session)
    result = level_command.write_level(store, character_id, level)
    _print_lv_line(session, token, level_command.console_line(result, character_id))
    if not result.ok:
        _note(session, f"{EVENT_LV_REFUSED_PREFIX}{result.refusal}")
        return _lv_notice(
            session,
            legacy,
            say_wire.LV_REFUSED_NOTICE_TEXT,
            LV_REFUSED_NOTICE_ACTION_LABEL,
            f"{OUTCOME_LV_REFUSED_PREFIX}{result.refusal}",
            # NO UNDO ON THIS BRANCH, and that is a correction rather than an
            # omission: the two refusals that CAN leave a value on disk repair
            # themselves inside `level_command.write_level` and say in their
            # own reason word whether the repair held.  An undo here would
            # only ever run when the audit row failed to write
            # (`_make_action`'s `if not audited`), which pf-adversary (round
            # `l86bt4`, D6) measured is not the case this branch is about.
        )
    _note(session, EVENT_LV_ROW_WRITTEN)
    return _lv_notice(
        session,
        legacy,
        say_wire.LV_SET_NOTICE_TEXT,
        LV_SET_NOTICE_ACTION_LABEL,
        OUTCOME_LV_ROW_WRITTEN,
        level_command.undo(store, character_id, result.previous),
    )


def _current_position(session: object) -> object | None:
    """The connection's own current position, or None if it has none yet.

    A GM who has not finished selecting a character has no scene to warp
    within; `warp_executor` needs the real current scene id (to refuse a
    cross-scene command honestly) and the real current z (the `warp` grammar
    carries no elevation, and inventing one is the guess this lane forbids).
    """
    selected = getattr(getattr(session, "foundation", None), "selected", None)
    position = getattr(selected, "position", None)
    if position is None:
        return None
    # A position missing either field is not a position this module can build
    # honest bytes from; treat it as absent rather than half-read it.
    if getattr(position, "scene_id", None) is None:
        return None
    if getattr(position, "z", None) is None:
        return None
    return position
