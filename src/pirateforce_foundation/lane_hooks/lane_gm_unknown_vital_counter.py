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

MEASURED BEFORE BUILDING THIS, PER COO-DECISION ITEM 2 (round `yajien`):
does the hot path already print an inbound frame's id before dispatch,
making this zero new code? NO, not on the path that actually serves a
real connection today. `current/pf_login_game_server_v141.py`'s own
`main()` connection loop (~line 7481) DOES do exactly this --
`print(f"[G< #{state.rx_frames + 1}] {len(pc)} bytes IDs={ids}")` plus a
`STRUCTURAL_IDS {ids!r}` line to the per-connection log file, both BEFORE
`state.dispatch(parsed)` at line 7558 -- which is almost certainly what
`runtime.py`'s own "v141 prints the capture line BEFORE dispatch" comment
(line ~8159) is describing. But grepping `app.py`/`connection.py`/
`runtime.py` -- the modules that actually own today's live connection
loop, per `V141_FREEZE.md`'s own statement that a bug in the frozen file
is fixed at its destination, never inside the frozen file -- for any call
into `pf_login_game_server_v141.main()`/`.GameState()`/`.dispatch(`/
`.recv_frame(`, or for any equivalent unconditional per-frame id print of
their own, found NONE (`current/pf_login_game_server_v141.py`'s own
`main()`/`GameState.dispatch()` are reachable only from that file's own
test/self-test functions and its standalone `main()`, never from the
package's real boot path). So this module is not zero-cost duplication of
an existing line -- it is new code on the hot path, exactly as small as
the letter above says it has to be, and the constraints below hold it to
that.

CONTRACT (COO-DECISION item 3, verbatim): count/record the id only, one
line per id PER SESSION -- no payload stored, no reply sent, no per-frame
memory allocation for an id a KNOWN branch already claims (this hook is
never called for one; that is the call site's job, not this function's).
Deduplication is per (session, vital_id): a scripted sender replaying the
same unknown id thousands of times costs this hook one `set` membership
check per frame and exactly one `session.events` line for the life of the
connection, never one line per frame -- the same "bounded, not per-frame"
discipline `gm/dispatch.py`'s own rate limiter and capture quota already
hold GM's two other opcodes to, applied here because nothing about being
UNRECOGNIZED should mean a flood costs less to log than a recognized one
does to capture.

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
    """
    seen = getattr(session, "_lane_gm_unknown_vital_ids_seen", None)  # type: ignore[attr-defined]
    if seen is None:
        seen = set()
        session._lane_gm_unknown_vital_ids_seen = seen  # type: ignore[attr-defined]
    vital_id = int(vital_id)
    if vital_id in seen:
        return
    seen.add(vital_id)
    session.events.append(f"unknown_vital_id_0x{vital_id:04X}")  # type: ignore[attr-defined]
