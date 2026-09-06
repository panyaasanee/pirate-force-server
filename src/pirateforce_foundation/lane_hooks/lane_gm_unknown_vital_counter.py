"""LANE-GM hook: count/record any inbound vital id no dispatch branch claims.

CORE-REQUEST-GM-063 (option (b), COO-DECISION 20260906T11:49+07:00,
answering `pf_bridge/notes_to_chief/20260906_1119_LANE-GM-ASK-COO-...md`).
The problem this closes: GT-146's P-3 acceptance reads an empty
`capture/gm_command_capture/` folder as "this button sends nothing", but an
empty folder is also what a button sending ANY opcode this project has not
yet built a sink for produces -- 0x51E9 and 0x6CEC both have one now
(round `eu2g1d`), 0x162E (`CheatVital`) does not, and the list is not
closed at three: whichever GM-surface opcode the next GMUI page turns out
to use, if it is one nobody has wired a sink for yet, reads exactly the
same "empty folder = sent nothing" false negative. Chasing sinks one
opcode at a time (the letter's option (a), what round `eu2g1d` did for
0x6CEC) never catches up to that list.

This hook is the other option: one counter, at the ONE point in
`runtime.py`'s dispatch chain that already knows a frame's nested vital id
matched no branch at all, closing the ambiguity for every present and
future opcode at once, at the cost of a single call site instead of one
per opcode.

~~MEASURED BEFORE BUILDING THIS, PER COO-DECISION ITEM 2 (round `yajien`):
does the hot path already print an inbound frame's id before dispatch,
making this zero new code? NO, not on the path that actually serves a real
connection today. ... grepping `app.py`/`connection.py`/`runtime.py` ...
found NONE.~~

**THAT MEASUREMENT WAS WRONG, AND IT WAS THE MEASUREMENT THE DECISION TO
BUILD THIS RESTED ON.** `pf-adversary` (round `vq07el`) falsified it two
independent ways, and round `vq07el` re-derived both by hand before
writing this paragraph rather than taking the report on trust:

  1. THE FROZEN FILE IS ON THE LIVE PATH.  `app.py:733` loads it
     (`legacy = load_legacy(root/'current/pf_login_game_server_v141.py')`),
     `app.py:930` installs `legacy.game_listener`, `app.py:933` adapts
     `legacy.main`, and `connection.py:290` rebuilds the listener with
     `types.FunctionType(original.__code__, ...)` -- the ORIGINAL code
     object, with late-bound globals.  So v141's own per-frame
     `print(f"[G< #...] ... IDs={ids}")` and its `STRUCTURAL_IDS` log line,
     both before `state.dispatch(parsed)`, run on a real connection.  The
     grep above missed it because the call sites spell it `legacy.main` and
     `legacy.game_listener`, never `pf_login_game_server_v141.main(`: a
     grep for a SPELLING, where the question was about a MECHANISM.
  2. `runtime.py` HAS ONE OF ITS OWN.  `runtime.py:6710` -- the first line
     of `dispatch()` itself -- calls `_say_dispatch_nested_vitals(parsed)`,
     whose own docstring says "One log-only console line per frame", and
     which prints `first_nested_id=0x%04X` unconditionally, for every
     frame, known id or not.  It landed by `COO-DECISION 20260904_0848`
     item 4, two days before the paragraph above claimed nothing like it
     existed.

WHAT THAT DOES AND DOES NOT DO TO THIS MODULE.  It does NOT make the hook
a duplicate: both existing lines print the FIRST nested id of every frame,
and neither says "no dispatch branch claimed this one", which is the
distinction GT-146's false negative actually turns on.  It DOES mean
COO-DECISION item 2's condition -- "if the line already exists, take
option (b): zero new code on the hot path, just write down how to read it"
-- was answered on a wrong measurement, and the choice between (b) and (c)
is COO's to remake, not this lane's to assume.  Round `vq07el` reported it
in `pf_bridge/notes_to_chief/20260906_1334_LANE-GM-CORRECTION-gm063-premise-
falsified-two-per-frame-id-prints-are-live.md`; until COO rules, this
module stays unwired and nothing depends on it.

CONTRACT (COO-DECISION item 3, verbatim): count/record the id only, one
line per id PER SESSION -- no payload stored, no reply sent, no per-frame
memory allocation for an id a KNOWN branch already claims (this hook is
never called for one; that is the call site's job, not this function's).
Deduplication is per (session, vital_id): a scripted sender replaying the
same unknown id thousands of times costs this hook one `set` membership
check per frame and exactly one `session.events` line for the life of the
connection, never one line per frame.

~~the same "bounded, not per-frame" discipline `gm/dispatch.py`'s own rate
limiter and capture quota already hold GM's two other opcodes to~~ -- FALSE
as first written, and `pf-adversary` (round `vq07el`) measured the gap
rather than arguing it.  Dedup bounds REPEATS of one id; it bounds nothing
about how many DIFFERENT ids one connection may present.  `nested_id` is
`c.u16(0x12)`, so the id space is 65,536; `GameSessionState.events` is a
plain list with no `clear()` anywhere in `v141` or `runtime.py`; and this
hook's call site is in `dispatch()`, which runs from the first frame,
BEFORE login.  Measured on the real `_EventEchoList` and event exporter:
one peer walking 0x0000..0xFFFF once each produced 65,536 events, 15.05
MiB of heap and 65,536 flushed console lines -- from an unauthenticated
peer, past every guard `gm/dispatch.py` holds, because none of them are on
this path.

So the bound is now explicit and is this module's own:
`MAX_UNKNOWN_IDS_PER_SESSION`.  Past it the hook emits ONE final line and
then costs a set-membership check per frame forever.  The cap is a
SKIP, so it is named, counted and visible rather than silent -- a reader
of a P-3 capture who sees the cap line knows the list they are holding is
truncated, which is the difference between a bounded record and a lie.

NOT WIRED YET (same shape as `lane_gm_activity_cheat_code.py` before
GM-062): the call site is chief's one edit, at the END of the dispatch
chain, past every existing branch -- see `registered_but_not_fired`
below. THE COMMIT THAT ADDS THAT CALL MUST DELETE THIS DECLARATION IN THE
SAME COMMIT, same reason as every other module in this package that has
carried one.

NOT CLAIMED: which GMUI button, if any, sends an opcode this project has
not wired -- this hook only makes that question answerable by attended
capture instead of guessed at from a folder that reads the same whether
the button sent nothing or sent something unrecognized.
"""
from __future__ import annotations

from . import hook

production_allowed = True

# NOT FIRED YET -- see module docstring. The call site is
# CORE-REQUEST-GM-063, chief's one edit at the end of runtime.py's inbound
# vital dispatch chain (after every existing branch, GM's own two
# included): a frame whose nested_id matched nothing above it.
registered_but_not_fired = ("vital_inbound_unknown_id",)


#: How many DISTINCT unknown ids one connection may record before this hook
#: stops recording and says so once.  32 because the question a P-3 capture
#: asks is "which opcode did that button send", and a button sends one; a
#: session presenting more than 32 ids nothing claims is not a P-3
#: observation, it is a scan, and the 33rd line would not answer anybody's
#: question.  The whole id space is 65,536 (`nested_id = c.u16(0x12)`), and
#: the measurement behind this number is in the docstring above.
MAX_UNKNOWN_IDS_PER_SESSION = 32

#: The one line emitted when the cap is reached.  A cap that recorded
#: nothing about itself would leave a truncated list looking like a complete
#: one, which is the failure mode this module exists to prevent, not commit.
CAP_REACHED_EVENT = (
    f"unknown_vital_id_cap_reached_{MAX_UNKNOWN_IDS_PER_SESSION}"
)

#: The id space of the field this hook is handed (`c.u16`).  An id outside
#: it did not come from a frame, so it is not recorded as if it had.
VITAL_ID_MAX = 0xFFFF


@hook("vital_inbound_unknown_id")
def _on_unknown_vital(session: object, vital_id: int) -> None:
    """Record ``vital_id`` once for this session; never twice, never a payload.

    ``session`` carries the per-connection dedup set as a plain attribute
    rather than a module-level dict keyed by some session identifier,
    matching this package's own session-scoped state elsewhere
    (``register_live_session``'s per-session bookkeeping) rather than
    inventing a second lifetime/cleanup story: the set is garbage the
    session object itself already is when the connection closes, nothing
    here has to evict it.

    ``vital_id`` IS VALIDATED, NOT COERCED.  The first draft called
    ``int(vital_id)`` and let anything survive that: ``pf-adversary`` (round
    ``vq07el``) fed it ``4660.9`` and got ``unknown_vital_id_0x1234``
    recorded as fact -- a DIFFERENT id from the one handed in, in a record
    whose only job is to say which id arrived.  ``0x12345`` produced a
    five-digit line the tests' own comment called a "fixed hex shape", and
    ``-1`` produced ``0x-001``.  A value this hook cannot report truthfully
    is dropped: silence here is recoverable, a wrong id in a P-3 capture is
    not.  ``bool`` is rejected with it -- ``True`` is an ``int`` to Python
    and is not a vital id to anybody else.

    Every attribute touch on ``session`` is guarded, matching
    ``lane_hooks/__init__.py``'s own ``register_live_session`` and
    ``lane_a_enter_instance_log.py``: this runs per frame, so an
    ``AttributeError`` here would not be one error, it would be one error
    PER FRAME through ``fire()`` -- the same shape as the flood the cap
    above exists to stop.
    """
    if isinstance(vital_id, bool) or not isinstance(vital_id, int):
        return
    if not 0 <= vital_id <= VITAL_ID_MAX:
        return
    seen = getattr(session, "_lane_gm_unknown_vital_ids_seen", None)
    if seen is None:
        seen = set()
        try:
            session._lane_gm_unknown_vital_ids_seen = seen  # type: ignore[attr-defined]
        except (AttributeError, TypeError):
            # A session object that will not carry the set cannot dedup, and
            # a hook that cannot dedup must not record: without the set,
            # every frame is a first sighting and this becomes the per-frame
            # line the contract forbids.
            return
    if vital_id in seen:
        return
    if len(seen) >= MAX_UNKNOWN_IDS_PER_SESSION:
        # The cap line is remembered IN the same set, as a str among ints,
        # rather than on a second session attribute: a second attribute is a
        # second guarded setattr that can fail on its own, and a failure
        # there would re-arm the cap line every frame -- the flood again.
        # So `seen` holds ids plus at most this one sentinel, and after the
        # cap `len(seen)` is deliberately not a count of ids.
        if CAP_REACHED_EVENT not in seen:
            seen.add(CAP_REACHED_EVENT)
            _append_event(session, CAP_REACHED_EVENT)
        return
    seen.add(vital_id)
    _append_event(session, f"unknown_vital_id_0x{vital_id:04X}")


def _append_event(session: object, line: str) -> None:
    """Append one line to ``session.events``, or drop it.

    Separate function so the cap line and the id line take the identical
    path -- a guard that protected one and not the other would leave exactly
    the flood it was added to prevent.
    """
    try:
        session.events.append(line)  # type: ignore[attr-defined]
    except (AttributeError, TypeError):
        return
