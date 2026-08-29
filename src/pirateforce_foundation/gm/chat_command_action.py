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
* It does not cross scenes.  `ForcePos` carries no scene id at all (RE-090);
  `gm/warp_executor.py` refuses a cross-scene `warp` rather than send an
  in-scene hop that misrepresents what happened.  Cross-scene warp needs
  `TeleportVital`, whose target/aux fields RE-090 leaves unproven.
  STILL TRUE OF THE WIRE, and now only of the wire (round `gejldf`): a
  cross-scene `/warp` no longer dead-ends in a refusal, it STAGES the
  account's next login scene through `gm/login_scene_stage.py` -- a config
  write, not a frame.  Nothing crosses a scene while the GM is logged in;
  the GM has to log out and back in, and every report that uses it has to
  say so.  See `_warp_action`'s routing rule for which half a given command
  takes.
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
* !! It does not put a single ForcePos byte on the wire today, because
  `teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED` is None.  ~~(RE-129
  open)~~ RE-129 ANSWERED on 2026-08-28T20:09+07:00 -- the byte is 0 -- and
  the constant is still None on purpose: COO-DECISION 21:30 locks it there
  until chief's confirmed-position write point is on main (CORE-REQUEST-GM-030).
  See that constant's block and `test_gm_force_pos_version_lock.py` -- and note
  that release day edits TWO test files: `VersionGateTests` in this module's
  own suite asserts the constant is None unconditionally.
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
* No coordinate range check.  `warp_executor` rejects NaN/Inf but accepts
  anything up to +/-3.4e38, so a decimal slip (`/warp 2 100000 200`) composes
  a real frame for a point this project elsewhere calls off the map --
  `world_scene_entry.py` refuses exactly that with `RELOCATED_OUTSIDE_GROUND`
  against a scene's `ground_extent`.  The fix is to reuse lane A's check by
  import (never to copy its logic here); it is not done this round, and the
  version gate means nothing can reach a client before it is.
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

from . import login_scene_stage, say_wire, teleport_wire
from .chat_command import (
    TYPED_COMMAND_REFUSAL_PREFIXES,
    handle_local_talk_chat,
)
from . import login_scene_admission
from .login_scene_admission import stageable_scene_ids
from .login_scene_override import console_safe
from .commands import (
    COMMAND_NAMES,
    OUTCOME_COMPOSED,
    OUTCOME_REFUSED_PREFIX,
    OUTCOME_STAGED_LOGIN_SCENE,
    OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED,
    OUTCOME_WITHHELD_PREFIX,
    log_gm_command_outcome,
)
from .say_wire import make_say_broadcast_frame
from .warp_executor import (
    make_warp_force_pos_frame_with_target,
    warp_command_has_coordinates,
    warp_command_scene_id,
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
# five inputs are in `rounds/GM_20260829_2112_*.md`):
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
WITHHELD_CONSOLE_TOKEN = "GM_CHAT_NO_BYTES_SENT"

# What each no-bytes outcome is waiting on, as fixed sentences this lane
# wrote -- never a string built from anything a client typed.  Keyed on the
# audit outcome so the ndjson word and the console line cannot drift apart:
# one decision, spelled once, read twice.
#
# NOT EXHAUSTIVE, ON PURPOSE.  `refused_warp_<ExcType>` and
# `refused_stage_<ExcType>` name a type, not a blocker, and inventing a
# sentence for a family whose members do not exist yet is how a console line
# starts lying.  Those print `NO_BLOCKER_RECORDED` instead -- the operator
# still learns the two facts this token exists for: nothing was sent, and
# which outcome the audit file will carry.
NO_BLOCKER_RECORDED = "no blocker recorded"

# Why nothing went out when the command itself was fine and the AUDIT was
# not.  Not an audit outcome -- that row is precisely what could not be
# written -- so it is spelled here and never passed to `log_gm_command_
# outcome`.  `_make_action`'s own comment explains the withholding; this is
# the console's half of it.
WHY_AUDIT_ROW_NOT_WRITTEN = "audit_row_not_written"

# Width bound for the usage half of that line, held at the PRINTER.  The one
# supplier in this tree returns one of seven fixed sentences (the longest is
# the six-command vocabulary, ~100 characters), so this never binds today --
# which is exactly why it is here: the bound belongs to the line, not to
# whichever function happened to build the string this time.
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
OUTCOME_NO_WIRE_PATH = f"{OUTCOME_REFUSED_PREFIX}no_wire_path"
# `refused_stage_<reason>`, where the reason is one of
# `login_scene_stage`'s own REASON_* values (`not_gm_account`,
# `unknown_scene`, `config_unreadable`, `write_failed`) or an exception TYPE
# name.  Same shape as `refused_warp_<ExcType>`, so a reader of the audit
# file does not have to learn a second grammar for the cross-scene half.
OUTCOME_STAGE_REFUSED_PREFIX = f"{OUTCOME_REFUSED_PREFIX}stage_"

# The blocker sentence for each no-bytes outcome.  Read by the console line
# only; nothing here reaches the audit file or a client.  A `MappingProxyType`
# for the same reason `login_scene_admission` uses one: it stops a later
# module from editing this in place by accident, and it is NOT a safety
# boundary (the module attribute can still be rebound).
NO_BYTES_BLOCKERS = MappingProxyType(
    {
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
        WHY_AUDIT_ROW_NOT_WRITTEN: (
            "the frame was built and then dropped: its outcome row could not"
            " be appended, and this house keeps no effect it cannot record"
        ),
    }
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
    warp.

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
    else:
        # Parsed and audited, but this lane has no proven server->client
        # wire for it yet.  Named, not silent: "nothing happened" and "we
        # never built that half" look identical on screen.
        _note(session, f"{EVENT_NO_WIRE_PATH_PREFIX}{command.name}")
        verdict = _Verdict(None, OUTCOME_NO_WIRE_PATH)

    action = verdict.action
    # THE BACKSTOP LINE, before the audit write and not after it: this says
    # "no bytes went to the client", which is already true and does not
    # depend on a file append succeeding.  Running it after would make the
    # console silent again on exactly the boot where the capture directory
    # is unwritable -- an attended shape this lane has already shipped a fix
    # for once (round `vb3ktn`).
    #
    # The staged cross-scene warp is excluded by outcome, not by command
    # name: `/warp` reaches here both ways, and the half that wrote a config
    # entry is not a command that "sent nothing" in any sense worth
    # greping.  See `_print_no_bytes_way_out`.
    if (
        action is None
        and not verdict.line_printed
        and verdict.audit_outcome
        not in (
            OUTCOME_STAGED_LOGIN_SCENE,
            OUTCOME_STAGED_LOGIN_SCENE_COORDS_IGNORED,
        )
    ):
        _print_no_bytes_way_out(
            session, token, getattr(command, "name", None), verdict.audit_outcome
        )
    # ONE write point for the `outcome` row, deliberately: CORE-REQUEST-GM-032
    # item 1 exists because the audit could not tell a withheld command from a
    # sent one, and an audit whose closing row is appended at four different
    # `return` statements grows a fifth return that forgets it.  Every branch
    # above therefore reports its verdict back here instead of writing.
    if not _log_outcome(
        session, token, command, outcome.record_id, verdict.audit_outcome, log_path
    ):
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
            if action[0] == WARP_ACTION_LABEL:
                if not clear_warp_target(session):
                    _note(session, EVENT_OUTCOME_STALE_TARGET_NOT_CLEARED)
            _note(session, EVENT_OUTCOME_NOT_AUDITED_ACTION_WITHHELD)
            # The one no-bytes path that gets here with a frame in hand.
            # It is the WORST one to leave silent: every other withhold is a
            # gate this lane knows is shut, while this one means the console
            # already printed `route=action`, the command was good, and the
            # frame was dropped for a reason that lives on disk.  Its `why`
            # is not an audit outcome on purpose -- that row is the thing
            # that could not be written.
            _print_no_bytes_way_out(
                session,
                token,
                getattr(command, "name", None),
                WHY_AUDIT_ROW_NOT_WRITTEN,
            )
            return None
    return action


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
    """`/warp`'s two halves -- see `_make_action`'s single write point.

    THE ROUTING RULE, IN ONE SENTENCE: `warp <scene_id> x y` inside the scene
    the connection is already in is the ForcePos half (frozen shut by
    COO-DECISION 20260829_0041 until chief's confirmation token compares
    against the commanded point); EVERYTHING ELSE -- a different scene, or
    the bare `warp <scene_id>` form that carries no coordinates for ForcePos
    to put in a frame -- stages the account's next login scene instead of
    being refused outright.

    THE ORDER CHANGED, AND IT MATTERS TO A READER OF THE AUDIT FILE.  The
    version gate used to be the first thing this function read, so with the
    gate shut EVERY warp wrote `withheld_force_pos_vital_version`.  It is now
    read only on the branch it actually governs.  A cross-scene warp never
    touches it and never claims to have been withheld by it -- the old word
    named a gate that had nothing to do with why that command did nothing.
    `GT-127`'s criteria were rewritten in the same round, per the owner's
    stale-entry ruling (PANYA-RULING 20260829_0127).
    """
    position = _current_position(session)
    if position is None:
        # Read before the routing decision, not after: without a current
        # scene this function cannot tell its two halves apart, so it must
        # refuse rather than guess which one the GM meant.
        _note(session, EVENT_WARP_NO_POSITION)
        return _Verdict(None, OUTCOME_WARP_NO_POSITION)

    try:
        target_scene_id = warp_command_scene_id(command)
        has_coordinates = warp_command_has_coordinates(command)
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # A malformed `args` shape cannot be routed either way.  Type name
        # only, same reasoning as every other refusal here.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return _Verdict(None, f"{OUTCOME_REFUSED_PREFIX}warp_{type(error).__name__}")

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

    # Park the destination for the reader of the NEXT position report.  After
    # the frame was built, never before: a refusal above leaves no bytes on
    # the wire, so it must leave no target either -- a parked target that no
    # frame corresponds to would let chief's confirmation token measure a
    # position row against a warp that never went out.
    #
    # Nothing is claimed by the parking itself, and no event is emitted for
    # it: `EVENT_ACCEPTED_PREFIX` above already names the accepted command
    # once, and a second line per warp saying only "the module remembered
    # where it sent you" is console noise that reads, wrongly, like an extra
    # step succeeding.  The consumer is `runtime.py`; the round's
    # CORE-REQUEST is what asks for it to be read.
    if not record_warp_target(session, target, current_character_id(session)):
        # A session that cannot hold the record loses the comparison, not the
        # warp: the frame is real and is still returned.  Named so a missing
        # confirmation line has a reason in the trail instead of looking like
        # the warp itself failing.
        _note(session, EVENT_WARP_TARGET_NOT_RECORDED)

    return _Verdict((WARP_ACTION_LABEL, pc, frame, 0.0), OUTCOME_COMPOSED)


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
            "stageable="
            f"{stageable_scene_ids(scene_registry=scene_registry)}"
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
    * it runs only when the verdict carried NO action and no handler printed
      its own line (`_Verdict.line_printed`), so the scene list `/warp 9999`
      gets is never doubled by a shorter line saying the same thing worse;
    * it does NOT run for a staged cross-scene warp.  That command had a
      real effect -- a config entry that decides the next login -- and a
      token whose name says NO_BYTES_SENT is true of it only in the most
      useless sense.  Whether the console should announce a stage is a
      separate question with a separate answer (`GT-141` tells the tester in
      prose today); borrowing this token for it would make "nothing
      happened" and "something happened elsewhere" grep the same.

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
        blocker = NO_BYTES_BLOCKERS.get(why, NO_BLOCKER_RECORDED)
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
