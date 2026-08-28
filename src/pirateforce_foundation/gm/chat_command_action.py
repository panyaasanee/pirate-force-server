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
`gm_state_action` (CORE-REQUEST-006) already uses at `runtime.py:5181` and
appends at `runtime.py:5396`.  `CORE-REQUEST-GM-029` asks for that one
call site and SUPERSEDES GM-028's fire-only shape.

!! WIRE EXACTLY ONE OF THE TWO -- AND THE OTHER ONE IS ALREADY WIRED.
Chief answered GM-028 before this module's own pull request could land (it
was closed gate-RED for an unrelated reason, see below), so as of
`runtime.py:4784` on main the `fire()` point EXISTS and the hook route is the
live one.  This module is therefore DORMANT: nothing calls it, and
`CORE-REQUEST-GM-029` no longer asks chief to ADD a call site.  It asks him
to REPLACE the `fire()` line with a call to this function, in one commit, so
that the two never coexist.  If both were wired, every GM chat line would be
authorized twice, audited twice (two ndjson rows for one typed line) and
charged twice against `chat_command`'s own rate limit -- the second charge
being the one that silently starts refusing real commands.

That is also why this module's event names were renamed away from the hook
route's, and not the other way round: the hook route is live, chief pinned
its names as literals in `tests/test_gm_chat_command_dispatch_wiring.py` on
main, and GT-127's headless drill greps for them.  A dormant route renames
for free; a live one does not.  See `EVENT_ACCEPTED_PREFIX` below.

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
  (CORE-REQUEST-GM-030), while `say` waits on one measurable byte (RE-132)
  and on nothing about position at all -- it moves nobody and writes no DB
  row.  `say` is therefore the SHORTEST REMAINING PATH from a typed chat line
  to something a tester can see -- [สมมติของสาย GM - รอ RE], and the label is
  not decoration.  What is measured: the payload codec (CHAT-CHANNEL-001) and
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
  reason `runtime.py:5168`/`5173` gates the login GM-state frame on
  `state_wire.GM_UPDATE_STATE_VITAL_VERSION_CONFIRMED`, and refuses by name
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

from . import say_wire, teleport_wire
from .chat_command import handle_local_talk_chat
from .say_wire import make_say_broadcast_frame
from .warp_executor import make_warp_force_pos_frame

# The action label the serve loop logs for a real GM warp.  ASCII, screaming
# snake case, same convention as every other label in runtime.py's action
# lists ("GM_UPDATE_STATE_AFTER_LOGIN", "V113_TELEPORT_..."), so an attended
# run can grep the console for it the same way.
#
# !! THE SUBSTRING `TELEPORT` IS LOAD-BEARING, NOT DECORATION.
# `runtime.py:3654` (`_move_authority_note_server_moves`, the label test at
# 3668 -- re-derived at this commit, not carried over) identifies a
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
# LABEL MUST.  The rule at `runtime.py:3654-3675` is a substring test on the
# label of a queued action -- `if action and "TELEPORT" in action[0]` -- and
# it reopens the move-authority grace window, which admits position readings
# far from the last one the gate accepted.
# PRECISION, after pf-adversary (this round) re-derived the call site rather
# than trusting the earlier wording here: it is NOT "every queued action" on
# every boot.  `runtime.py:4518-4521` calls
# `_move_authority_note_server_moves(actions)` only when
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
EVENT_WARP_REFUSED_PREFIX = "gm_chat_action_warp_refused_"
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
) -> tuple[str, bytes, bytes, float] | None:
    """Authorize + audit one chat line; return one outbound action, or None.

    `session` is `runtime.py`'s session object (`self` at the call site).
    Only two attributes are read: `.token` (the authenticated login name --
    the identity, never read from `payload`) and `.events` (diagnostics), plus
    `.foundation.selected.position` for the warp case, which is the
    connection's own current scene/elevation.

    `legacy` is the loaded `pf_login_game_server_v141` module, the same seam
    `state_wire`/`teleport_wire` already take from their wiring caller rather
    than importing the frozen serializer themselves.

    Returns `(label, pc, frame, delay_before)` -- append it to the action
    list, exactly like `gm_state_action` -- or None, which means "this frame
    is not ours; behave exactly as the server did before this lane existed".
    """
    try:
        return _make_action(
            session, payload, legacy, config_path=config_path, log_path=log_path
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
    print(f"{CONSOLE_TOKEN} {command.name} route=action", file=sys.stderr)

    if command.name == "warp":
        return _warp_action(session, command, legacy)
    if command.name == "say":
        return _say_action(session, command, legacy)

    # Parsed and audited, but this lane has no proven server->client
    # wire for it yet.  Named, not silent: "nothing happened" and "we
    # never built that half" look identical on screen.
    _note(session, f"{EVENT_NO_WIRE_PATH_PREFIX}{command.name}")
    return None


def _warp_action(
    session: object, command: object, legacy: object
) -> tuple[str, bytes, bytes, float] | None:
    version = teleport_wire.FORCE_POS_VITAL_VERSION_CONFIRMED
    if version is None:
        # RE-129.  Refusing here is the whole safety property: GT-101
        # measured an unproven vital version killing the owner's session.
        _note(session, EVENT_WARP_WITHHELD_NO_VERSION)
        return None

    position = _current_position(session)
    if position is None:
        _note(session, EVENT_WARP_NO_POSITION)
        return None

    try:
        pc, frame = make_warp_force_pos_frame(
            legacy, version, command, position.scene_id, position.z
        )
    except Exception as error:  # noqa: BLE001 - includes WarpExecutorError
        # Covers the cross-scene refusal, the scene-only `warp <id>` form
        # with no position to carry, and every malformed-argument case
        # warp_executor re-validates.  Type name only, same reasoning as
        # above -- a WarpExecutorError message embeds the typed arguments.
        _note(session, f"{EVENT_WARP_REFUSED_PREFIX}{type(error).__name__}")
        return None

    return (WARP_ACTION_LABEL, pc, frame, 0.0)


def _say_action(
    session: object, command: object, legacy: object
) -> tuple[str, bytes, bytes, float] | None:
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
    `runtime.py:4765-4774`, at the very 0xAC52 branch CORE-REQUEST-GM-029
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
        return None
    if version != say_wire.CHANNEL_CODEC_VITAL_VERSION:
        # The confirmed byte exists but the imported codec hardcodes a
        # different one, so composing here would put a version on the wire
        # that RE just measured as WRONG.  See that constant's release-day
        # note: the fix is a letter to the codec's owning lane, never a
        # second codec in this lane's zone.
        _note(session, EVENT_SAY_VERSION_CODEC_MISMATCH)
        return None

    try:
        pc, frame = make_say_broadcast_frame(legacy, command)
    except Exception as error:  # noqa: BLE001 - includes SayWireError
        # Covers the over-length message, the wrong `args` shape, and every
        # rejection the channel codec itself raises.  Type name only: a
        # SayWireError message embeds the GM's typed text, which is both a
        # console cp874 hazard and a needless echo of client-supplied bytes.
        _note(session, f"{EVENT_SAY_REFUSED_PREFIX}{type(error).__name__}")
        return None

    return (SAY_ACTION_LABEL, pc, frame, 0.0)


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
