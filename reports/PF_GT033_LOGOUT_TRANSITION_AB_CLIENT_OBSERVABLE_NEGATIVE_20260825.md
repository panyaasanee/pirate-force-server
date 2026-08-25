# GT-033 -- neither of the two response policies we own makes the client leave the map

Date: 2026-08-25 (+07:00)
Scope: three attended single-client sessions driven by the owner at the game
client, jobs `1143/1144/1145/1146` (variant B, subcode 03), `1147/1148/1149`
(variant A, subcode 03) and `1150/1151/1152` (variant A, subcode 01). All three
booted the same commit `06b62abd423cff9fc9c965d52178fd2fca62c38e`, whose tree
matches the `main` head `0a030f97`, with `CODE_DELTA_vs_main = 0` on every run,
each against a **fresh copy** of the canonical database. Gates 6a-6e passed on
every run and every teardown exited 0.

This is the client-observable half of HYP-PF-028 (variant B) and of HYP-PF-013
(variant A). The wire/DB half of both was already headless-proven and is only
re-confirmed incidentally here, not re-claimed.

Source letters (kept in the coordination repo, consumed by chief round 166):
`notes_to_chief/consumed/20260825_1710_GT033-VARIANT-B-RESULT-*.md`,
`20260825_1730_GT033-VARIANT-A-RESULT-*.md`,
`20260825_1745_GT033-SUBCODE01-RESULT-*.md`.

## Result

**Controlled runtime negative** for one claim:

> Neither response policy this project owns makes the real client leave the map.
> With HYP-PF-028 enabled (a hash-pinned `ReturnSelectServerVital 0x709E` sent
> ahead of the ack, then a clean server-side socket close at +250 ms), subcode 03
> does **not** return the client to character select. With HYP-PF-013 enabled
> (the same ack and the same close, differing by exactly that one frame), subcode
> 03 does **not** transition and subcode 01 does **not** make the client exit.

## The four-cell table and the cell that was not measured

|                                   | subcode 03 (return to character select) | subcode 01 (exit game) |
|-----------------------------------|------------------------------------------|------------------------|
| variant A (ack + close)           | measured, no transition (job 1148)       | measured, no self-exit (job 1151) |
| variant B (0x709E -> ack + close) | measured, no transition (job 1145)       | **NOT MEASURED** -- deliberately cut, see below |

**The fourth cell (variant B x subcode 01) was never run.** This is a declared
cut, not an omission, and nobody may read this table as complete. It was cut for
two reasons: the three measured cells all returned the same negative and variant
A is a subset of variant B in the outbound-byte dimension, so the fourth cell
carries the least expected information of the four; and there are in-game
experiments listed below that return more per boot. Two reasons that were
written first and then withdrawn by the same round must not be reused: deciding
by the vital's *name* (the weakest evidence layer available, and the 1-vs-4 mode
mapping that name argument leans on has no evidence at all), and calling the
remaining branch "static only" (it is not -- see branch 2 below).

The cut has a price that is paid knowingly: all three measured runs share one
boot commit, so once the code moves, the fourth cell can never again be measured
under the same commit-level control.

## Wire and DB layer: passed on every run

- The client sent a genuine `LogoutVital 0x1B40`, 34 B PC, with the mode
  discriminator matching the button pressed (`08 03` / `08 01`). The subcode-03
  request was **byte-identical** between the variant A and variant B runs.
- Variant B: the three pinned pieces matched their sha256 pins, recomputed from
  the hexdump rather than trusted from the label -- request 34 B PC
  `EC5B53DC..`, `return_select_first` 38 B PC `A4C8DF42..`, ack 36 B PC
  `FC8B9E2C..`. On the wire the return-select frame is 48 B.
- Variant A: an **outbound-frame census over the whole run** confirms not one
  byte of `0x709E` was sent, which is what makes A a control differing from B by
  exactly one frame rather than merely a run that looked similar.
- `sessions.closed_at` was committed **before** the response bytes were queued.
  This was measured across two clocks only on the variant B run (26 ms). On the
  two variant A runs it rests on the server's own `PF-EVENT` ordering line, which
  reports the order rather than proving it; that layer is headless-proven
  separately, so the weaker evidence there is noted, not waved through.
- `OPEN_SESSIONS 0`, integrity ok, `FK_ROWS 0`, canonical database unchanged on
  every run.

## Client-observable layer: negative on all three measured cells

On every run the logout dialog simply disappeared and nothing else happened: no
character-select screen, no disconnect popup, no error, no freeze, and the client
process never exited on its own -- the tester closed the window by hand each
time. The owner's report was checked against the video rather than taken as
testimony (frames extracted at 2 fps, key points confirmed at 30 fps): 50 s of no
state change on the variant B run, 57.6 s on variant A subcode 03, and roughly 68
to 77 s on variant A subcode 01, with the HUD coordinates `X:-8,553 Y:-2,579`
unmoved to the digit across all three. Where the per-frame pixel delta rose on
the variant A runs, the frames show the tester rotating the camera while waiting;
the HUD coordinates are identical, so it is not a state change.

## What this does NOT establish

1. **`0x709E` is not excluded.** What was measured is that *this composition*
   (`0x709E` with every field zero, then the ack, then the close) does not cause
   a transition.
2. **Three readings remain inseparable**: wrong vital, right vital with wrong
   field values, right vital needing something alongside it. The body is 16 zero
   bytes because no producer exists for it.
3. **Variant A is the control, not the decider.** B does everything A does plus
   one frame. What A answers is whether an unconsumed `0x709E` frame gets in the
   way of the client noticing the connection close. It does not.
4. **The client is not proven unable to return to character select** -- only that
   the two response policies we have do not do it.
5. **The vanishing dialog is not evidence that the client consumed anything from
   the server.** The button handler probably closes it on click; the two readings
   are inseparable from this evidence, and the ~40 ms gap is far below the
   unquantified offset between the video clock and the wire clock, so ordering
   does not separate them either.
6. **No claim is made that our response resembles the original server's.** That
   server is gone and unrecoverable.
7. **Two response shapes were never tried**: closing without acking at all, and
   acking then staying silent without closing.
8. **Nothing was tested with the logout dialog still open.** The adversary caveat
   that made the variant C negative ambiguous applies to A and B as well: by the
   time `0x709E` arrives the dialog has already closed, so B sits in the same
   client state as C in the dimension that caveat is about.

## The claim that must not be made from this report

This report does **not** show that connection teardown fails to cause a
transition. It shows that **we closed the socket and the client did not change
screens**. Nothing here demonstrates that the client ever perceived the close:
after `[G!]` nobody checked whether the client kept sending, errored, or tried to
reconnect, and this project has never once recorded the client showing any
disconnect symptom while in the map, so there is no positive control. The two
readings -- saw it and did nothing, versus never saw it -- are not separated by
this evidence. A zero-cost check that would separate them was requested from the
bridge in the same round: grep the retained captures for any outbound line
timestamped after `[G!]`.

## The decision table this ticket carried was not exhaustive

The ticket's own text said "if neither works, the answer is somewhere else
(mode/timer the orchestrator waits on)" -- a pointer plus a parenthetical guess,
not a closed set. Six branches nobody had written down, most of them still
measurable in-game:

1. The **redirect half was never built**. The best static hypothesis is "end *or
   redirect* the session (close *or hand back to select-server*)"; variant A only
   ever did the `close` half.
2. The **timer is our parameter**, not a static unknown. We closed at 250 ms
   after the ack on every run and never varied it. 0, 2 s, 10 s, or never
   closing are in-game experiments nobody has run.
3. **Frame order** was never varied: the scenario sends `0x709E` before the ack,
   and neither the reverse order nor repeated sends has been tried.
4. **Field values** are all zero, per nonclaim 2.
5. **The other connection was never touched.** There are two ports, login and
   game, with nothing recorded that ties them together, and the static reading
   has the orchestrator closing two sub-objects while we only ever closed the
   game socket.
6. The **logout-dialog state**, per nonclaim 8.

## What is not new here, and a correction to an earlier draft

An earlier draft of this round's notes said the variant B run was the first time
in project history that a real client received the bytes of `0x709E`. **That is
false.** GT-033 variant C delivered the same pinned frame to a real client on
2026-08-23, as this repository's own hypothesis ledger records under
`HYP-PF-031`, amended by chief round 123 on that date. What is genuinely new in
the variant B run is that `0x709E` arrived **as a response to a real
`LogoutVital`** rather than as an unsolicited chat-triggered push. Separately,
the coordination repo's field-validation table records two observed
`ReturnSelectServerVital` frames in a capture corpus frozen on 2026-08-15/16 --
before any of our variants -- and nobody has yet separated a genuine emission
from a validator schema collision; that is carried as a rider on the static
follow-up ticket, not resolved here.

## Where the answer went

The remaining branch chosen by chief round 166 is the session/connection
orchestrator's mode and timer (vtable `0xf45030`, MODE at `+0x28`, timestamp at
`+0x24`), queued on the bridge as ticket RE-070 in the coordination repo, because
the disassembly needs the client image this project does not carry in git.

Three claims about that orchestrator that had been copied forward were corrected
when that ticket was opened: `+0x28 in {1,4}` is the set of values *compared* at
`0x719ab0`/`0x719b90`, not the set the field can hold; the reading of 1 versus 4
as the two non-return-to-game outcomes was an interpretation, never a code
reading, so it must not be used as a `1=exit` / `4=char-select` mapping; and
`[vtable+0xf4]` belongs to the connection sub-object, not to `0xf45030` itself.

A fourth warning is larger than those three and travels with any use of those
addresses: the round-100 static factpack they come from carries **no span and no
sha256 for any function**, unlike every RE ticket since. It cannot be verified
even on the bridge until it is re-derived, so RE-070's first job is to re-derive
it rather than to build on it.

## Evidence that is not in this repository

The video and capture roots for all three runs live only on the bridge machine
and are marked do-not-delete there: `1145_gt033b_FULLROUND_*`,
`1148_gt033a_FULLROUND_*`, `1151_gt033a2_FULLROUND_*` and their matching
`capture_gt033*` directories. The still frames extracted from them are committed
in the coordination repo under `evidence_screens/`. Nothing in this repository
reproduces the client-observable measurement; this report is the record of it.
