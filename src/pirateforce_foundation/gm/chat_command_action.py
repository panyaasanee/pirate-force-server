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
    login_scene_stage,
    npc_switch_catalog,
    say_wire,
    speed_wire,
    teleport_wire,
    warp_executor,
)
from .chat_command import (
    TYPED_COMMAND_REFUSAL_PREFIXES,
    handle_local_talk_chat,
)
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
EVENT_WARP_WITHHELD_NO_VERSION = (
    "gm_chat_action_warp_withheld_no_confirmed_force_pos_vital_version_re129_open"
)
EVENT_WARP_NO_POSITION = "gm_chat_action_warp_no_current_position"
# The warp went out but its destination could not be parked for the position
# reader (a session that refuses attributes).  NOT a refusal -- the frame is
# real -- so it is deliberately outside `EVENT_WARP_REFUSED_PREFIX`, whose
# contract is "exception type names only" and whose consumers read it as
# "nothing was sent".
EVENT_WARP_TARGET_NOT_RECORDED = "gm_chat_action_warp_target_not_recorded"
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
EVENT_SPEED_NO_SELECTED_CHARACTER = "gm_chat_action_speed_no_selected_character"
EVENT_SPEED_REFUSED_PREFIX = "gm_chat_action_speed_refused_"

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
EVENT_SPEED_PERSIST_REFUSED_PREFIX = "gm_chat_action_speed_persist_refused_"
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
OUTCOME_SPEED_NO_SELECTED_CHARACTER = (
    f"{OUTCOME_REFUSED_PREFIX}speed_no_selected_character"
)
# The persistence half's four named refusals.  See the matching
# `EVENT_SPEED_*` block above for why all four withhold the frame too.
OUTCOME_SPEED_NO_STORE = f"{OUTCOME_REFUSED_PREFIX}speed_no_store"
OUTCOME_SPEED_NO_CHARACTER_ID = f"{OUTCOME_REFUSED_PREFIX}speed_no_character_id"
# `refused_speed_persist_<ExcType>` -- the store raised.  Same TYPE-name-only
# discipline as `refused_speed_<ExcType>` above: a `TypedAttrError` message
# can embed the GM's typed text, and audit rows carry no typed text.
OUTCOME_SPEED_PERSIST_REFUSED_PREFIX = f"{OUTCOME_REFUSED_PREFIX}speed_persist_"
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
        OUTCOME_SPEED_PERSIST_REFUSED_PREFIX,
        "the store refused or failed; its compose gate can raise AFTER the"
        " write commits, so do NOT read this as 'nothing was stored'",
    ),
)
# The one named refusal `/gmprobe` can write that is not an exception TYPE
# suffix: the typed `variant_id` matched no row in
# `bt_gm_probe.VARIANTS_BY_ID`.  A GM typo, not this lane's error -- and not
# a guess at the closest match either (module docstring's own nonclaim).
OUTCOME_GMPROBE_UNKNOWN_VARIANT = f"{OUTCOME_REFUSED_PREFIX}gmprobe_unknown_variant"
OUTCOME_NO_WIRE_PATH = f"{OUTCOME_REFUSED_PREFIX}no_wire_path"
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
    WHY_AUDIT_ROW_NOT_WRITTEN: (
        "the outcome row could not be appended, so this command's audit"
        " trail is broken; anything it had in hand was dropped with it"
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
NO_BYTES_BLOCKERS = MappingProxyType(_NO_BYTES_BLOCKERS_SOURCE)


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
    if outcome.command is None:
        _note(session, f"{EVENT_REFUSED_PREFIX}{outcome.refusal_reason}")
        _print_command_refusal_way_out(session, token, outcome)
        return None

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
            _note(session, EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD)
            # Dropped, not returned -- and the console is told below, on the
            # same call site every other shape uses.  An early `return None`
            # here is how the first version of this round grew two
            # announcers that disagreed (pf-adversary D2/D7).
            action = None
    # THE ONE PLACE THE CONSOLE IS TOLD, and it is AFTER the audit write on
    # purpose: `why` has to be the word the ndjson actually carries, and
    # until this line runs nobody knows whether the row landed.
    _announce_console_outcome(
        session, token, command, verdict, audited=audited, sent=action is not None
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
    if action is not None:
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

    THE ROUTING RULE, IN ONE SENTENCE, UPDATED BY COO-DECISION
    2026-08-31T14:41+07:00 AND THEN BY GM-A (`R278`, this round): `warp
    <scene_id> x y` inside the scene the connection is already in is the
    ForcePos half (frozen shut by COO-DECISION 20260829_0041 until chief's
    confirmation token compares against the commanded point); `warp
    <scene_id> x y` naming a DIFFERENT scene is the live cross-scene
    TeleportVital half (`_warp_teleport_action`, gated on
    `warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED`); the bare
    `warp <scene_id>` form naming a DIFFERENT, MARKER-BACKED scene
    (`warp_no_coords_live_target` not None) is NOW ALSO live -- a second
    TeleportVital half, `_warp_teleport_action_no_coords`, aimed at the
    destination's own pinned marker spawn instead of typed coordinates; and
    every remaining bare-form case (same scene, or a markerless destination
    such as 17/126/278/997) still stages the account's next login scene,
    because neither live composer has a position to put in a frame there.

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

    if (
        target_scene_id != position.scene_id
        and has_coordinates
        and warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED
    ):
        return _warp_teleport_action(session, command, legacy, position.z)

    # GM-A: the bare (no-coordinates) cross-scene shape now ALSO fires live,
    # but only into a scene `warp_no_coords_live_target` names as
    # marker-backed -- everything else (same scene with no coordinates, or
    # a markerless destination such as 17/126/278/997, GT-182 nonclaim 4)
    # falls through unchanged to the stage-only branch two lines down.
    if (
        target_scene_id != position.scene_id
        and not has_coordinates
        and warp_executor.WARP_CROSS_SCENE_LIVE_TELEPORT_AUTHORIZED
        and warp_no_coords_live_target(target_scene_id) is not None
    ):
        return _warp_teleport_action_no_coords(session, target_scene_id, legacy)

    if target_scene_id != position.scene_id or not has_coordinates:
        return _stage_action(
            session,
            target_scene_id,
            has_coordinates,
            token=token,
            gm_accounts_config_path=gm_accounts_config_path,
            login_scene_config_path=login_scene_config_path,
            scene_registry=scene_registry,
        )

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

    return _Verdict(
        (WARP_CROSS_SCENE_TELEPORT_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED
    )


def _warp_teleport_action_no_coords(
    session: object,
    scene_id: int,
    legacy: object,
) -> _Verdict:
    """GM-A: the cross-scene half of `/warp` WITHOUT typed coordinates.

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

    return _Verdict(
        (WARP_CROSS_SCENE_NO_COORDS_TELEPORT_ACTION_LABEL, pc, frame, 0.0),
        OUTCOME_COMPOSED,
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
            f"blocked_on='{console_safe(_one_line(blocker), stream)}'",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _print_staged_way_out(
    session: object,
    token: str,
    command: object,
    outcome: str,
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
        print(
            f"{STAGED_CONSOLE_TOKEN} "
            f"account='{console_safe(_one_line(token), stream)}' "
            f"command=warp scene_id={scene_id} coordinates={coordinates} "
            "next='log out and log back in to land there;"
            " nothing was sent to the client now'",
            file=stream,
        )
    except Exception as error:  # noqa: BLE001 - see the last paragraph above
        _note(session, f"{EVENT_CONSOLE_WRITE_FAILED_PREFIX}{type(error).__name__}")


def _announce_console_outcome(
    session: object,
    token: str,
    command: object,
    verdict: "_Verdict",
    *,
    audited: bool,
    sent: bool,
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
    """
    if sent:
        return
    if verdict.audit_outcome in STAGED_OUTCOMES and audited:
        _print_staged_way_out(session, token, command, verdict.audit_outcome)
        return
    if verdict.line_printed:
        # A handler already said it, in a vocabulary built for that refusal.
        return
    _print_no_bytes_way_out(
        session,
        token,
        getattr(command, "name", None),
        verdict.audit_outcome if audited else WHY_AUDIT_ROW_NOT_WRITTEN,
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
    not buy.  The previous value is read on its own connection before
    `write_typed_attributes_and_compose_sparse` runs, so a concurrent writer
    in that window makes this undo restore WHAT THIS COMMAND SAW, not
    whatever was there an instant before the write.  That is weaker than
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

    LANE-DB's persistence entry point is keyed by `character_id`, not by
    `identity_lo`/`identity_hi` -- and `model.Character` has carried `id` as
    its first field all along, so the method LANE-GM asked LANE-DB for in
    `pf_bridge/notes_to_chief/20260902_0017_LANE-GM-TO-LANE-DB-request-speed-
    persistence-method.md` (an identity_lo/hi-keyed overload) turned out not
    to be needed: this read is the whole translation, and it lives in this
    lane where it belongs rather than adding an API to theirs.

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

    !! IT NOW WRITES A DB ROW.  ~~"writes no DB row: this composes a WIRE
    FRAME only, never touching `store`/`characters`"~~ -- struck, not
    deleted, because it was true of every earlier round of this function and
    a reader of an old audit line needs to know when it stopped being true.
    LANE-DB's `store.write_typed_attributes_and_compose_sparse` landed on
    `main` and their letter `pf_bridge/notes_to_chief/20260901_2213_LANE-DB-
    TO-LANE-GM-speed-sparse-live-on-main-but-speed-does-not-persist.md`
    named the consequence of not calling it: `GT-193` would have graded a
    frame, not a memory, and `/speed 400` would be gone by the next login.
    This function now calls it FIRST and composes from its read-back:

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
        return _Verdict(None, OUTCOME_SPEED_WITHHELD_CANONICAL_DB)

    identity_lo, identity_hi = _selected_speed_identity(session)
    if identity_lo is None or identity_hi is None:
        _note(session, EVENT_SPEED_NO_SELECTED_CHARACTER)
        return _Verdict(None, OUTCOME_SPEED_NO_SELECTED_CHARACTER)

    version = speed_wire.shared_vital_version_confirmed()
    if version is None:
        # The scoped exception above has not (or no longer) landed --
        # withhold exactly the way `_say_action`/`_warp_action` do for their
        # own still-shut gates.  GT-101 measured what an unproven
        # vital_version does to a real client: modal error, socket closed.
        _note(session, EVENT_SPEED_WITHHELD_NO_VERSION)
        return _Verdict(None, OUTCOME_SPEED_WITHHELD_NO_VERSION)

    try:
        value = speed_wire.parse_speed_value(command.args[0])
    except Exception as error:  # noqa: BLE001 - includes SpeedWireError
        # Type name only: an exception message can embed the GM's typed
        # text, same reasoning as every other refusal in this module.
        _note(session, f"{EVENT_SPEED_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(
            None, f"{OUTCOME_REFUSED_PREFIX}speed_{type(error).__name__}"
        )

    # ---- DB FIRST ----------------------------------------------------
    # Everything from here to the compose below is the persistence half.
    # Read the `EVENT_SPEED_NO_STORE` comment block for the ordering
    # decision and the letter it is still waiting on.
    store = _speed_store(session)
    persist = getattr(store, "write_typed_attributes_and_compose_sparse", None)
    if not callable(persist):
        # A session shape with no store to write to is NOT "send the frame
        # anyway": that is precisely the screen-disagrees-with-the-row case
        # this ordering exists to make impossible.
        _note(session, EVENT_SPEED_NO_STORE)
        return _Verdict(None, OUTCOME_SPEED_NO_STORE)

    character_id = _selected_speed_character_id(session)
    if character_id is None:
        _note(session, EVENT_SPEED_NO_CHARACTER_ID)
        return _Verdict(None, OUTCOME_SPEED_NO_CHARACTER_ID)

    # Built BEFORE the write, because it has to remember what was there
    # first.  Carried by every verdict from here down, including the
    # refusals: `store.write_typed_attributes_and_compose_sparse`'s own
    # docstring warns its compose gate can raise AFTER the write commits, so
    # "this branch refused" is not the same as "this branch changed nothing".
    undo = _speed_undo(store, character_id)

    try:
        sparse = persist(character_id, {SPEED_TYPED_COLUMN: value})
    except Exception as error:  # noqa: BLE001 - KeyError/TypedAttrError/...
        # Deliberately does not say "nothing was stored" -- see `undo` above.
        # It says the send was refused, which is the only half this lane can
        # speak for, and the console sentence for this prefix says the rest.
        _note(
            session,
            f"{EVENT_SPEED_PERSIST_REFUSED_PREFIX}{type(error).__name__}",
        )
        return _Verdict(
            None,
            f"{OUTCOME_SPEED_PERSIST_REFUSED_PREFIX}{type(error).__name__}",
            undo,
        )

    # ---- WIRE SECOND, FROM THE ROW, NOT FROM THE TYPED TEXT ----------
    # The composed value comes out of the store's own read-back rather than
    # `value`, so the number on the client is by construction the number the
    # database holds.  `validate` rounds an f32 on the way in (`400.1` is
    # stored as `400.1000061035156`), which is exactly the divergence a
    # caller-side compose would hide.
    stored = sparse.get(speed_wire.SPEED_FIELD_X) if isinstance(sparse, dict) else None
    if isinstance(stored, bool) or not isinstance(stored, (int, float)):
        _note(session, EVENT_SPEED_PERSIST_READBACK_UNUSABLE)
        return _Verdict(
            None, OUTCOME_SPEED_PERSIST_READBACK_UNUSABLE, undo
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
        return _Verdict(
            None,
            f"{OUTCOME_SPEED_PERSIST_COMPOSE_REFUSED_PREFIX}"
            f"{type(error).__name__}",
            undo,
        )

    return _Verdict(
        (SPEED_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED, undo
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
