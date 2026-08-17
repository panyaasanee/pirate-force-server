# GT-007 — the echo ack stops the logout freeze but does not trigger any client transition

Date: 2026-08-17
Scope: one attended single-client session at HEAD `b90007e` with the server
booted under `--logout-hypothesis-scenario scenarios\logout_hypothesis_ack_echo.json`
against a **fresh copy** of the canonical database
(`state\pirateforce_gt007_20260817_192713.sqlite3`, retained as evidence).
This is the client-observable half of HYP-PF-012; the wire/DB half was already
headless-proven in `PF_LOGOUT_ACK001_HYP_PF_012_ACKNOWLEDGED_LOGOUT_HEADLESS_WIRE_DB_20260817.md`
and is only re-confirmed incidentally here, not re-claimed.

## Result

**Grade B controlled runtime negative** for one claim:

> With the designed echo ack enabled, neither captured `LogoutVital` form
> produces the intended client transition at the real `GameClient.local.bin`:
> subcode 03 does **not** return the client to character select and subcode 01
> does **not** make the window close itself. The echo-only response shape is
> therefore falsified as sufficient for client-side logout, while the
> freeze-until-End-task behavior seen without any response (GT-002 client2) did
> not occur in this run.

The negative is scoped to the response shape. It does not touch the R38 decode
(both frames arrived exactly on their button presses, which reinforces it) and
it does not touch the committed wire/DB behavior of HYP-PF-012, whose ledger
entry LOGOUT-ACK-001 stands unchanged.

## Run identity

| | value |
|---|---|
| HEAD under test | `b90007e` |
| capture root | `GameClient\capture_gt007_20260817_192713` |
| console / server PID | 18308 / 14132 (visible console, scenario flag shown at boot) |
| client PID | 3344 (window title `Pirate Force`) |
| jobs | `080` (copy DB + boot + client), `081` (teardown) |
| driver | attended big round 19:27–19:40, main session as tester with its existing computer-use grant, Panya at the machine |
| database | run copy `pirateforce_gt007_20260817_192713.sqlite3`; the canonical `state\pirateforce.sqlite3` was never attached and its sha `FA794D0B..4400` is unchanged |

## Measurements

### Client-observable layer (each point directly observed on screen)

- The logout dialog opens from the HOME menu → "ออก" and offers three buttons:
  return to game, return to character select, exit game.
- **Subcode 03** (return to character select, clicked 19:32:42): the dialog
  closes, the client **stays in the map**. No transition, but also **no
  freeze** — the in-game UI keeps responding (the HOME menu reopens).
- **Subcode 01** (exit game, clicked 19:33:57): the dialog closes, the window
  does **not** close itself. Again no freeze.
- The window **X button works normally** afterward: confirm dialog → clean
  close, no End task needed. (During the run this was briefly misread as "X is
  dead"; the real cause was the Claude app window invisibly overlapping the
  game window and swallowing the clicks. After moving the game window the X
  behaved normally. Recorded so future testers move the game window left
  before driving UI and never conclude "client ignores clicks" without doing
  so.)
- Delta against GT-002 client2 (no response configured, full freeze, End task
  required): the freeze did not occur here. This is an observation consistent
  with the ack preventing it, **not** a causal proof — this session ran no
  same-boot negative control.

### Wire/DB layer (job `081` plus a direct read of the run copy)

- `GAME_EVENTS`: two `0x1B40` frames exactly on the button presses — seq=3 at
  19:32:42.440 payload `0803…` and seq=5 at 19:33:57.225 payload `0801…`.
- `GAME_LIVE`: `SENT label=HYP_PF_012_LOGOUT_SUBCODE03_ACK_AFTER_CLEAN_CLOSE
  46B late 0.5ms` — the ack went out **only for subcode 03** (marker ×1). The
  01 frame arrived after the session was already closed and was met with
  dispatch silence, which is the designed fail-closed behavior, not a defect.
- Run-copy database: the session opened 19:29:00 (lease 6) has
  **`closed_at` 19:32:42.464 = +24 ms after the 03 frame and before the ack
  at .464→.485** — the first time HYP-PF-012's close-before-ack ordering is
  observed with the real client. Open sessions 0, `integrity_check` ok.
- Canonical database untouched: sha `FA794D0B..4400` before and after.

### Tooling defect recorded (not a game finding)

Job `081`'s built-in DB AFTER snapshot is junk: the `080` info file stores the
run-copy path on a whitespace-split line, so the path (which contains spaces)
was truncated and the snapshot queried a nonexistent database (`no such column:
lease_generation`, `sessions 0`). This is the same defect family as job 069.
The tester read the run copy directly instead; the DB numbers above come from
that direct read. The teardown template is being fixed to write one value per
line; a snapshot failure is never itself a test failure.

## Design data for the next response shape

Recorded for the follow-up hypothesis, without interpretation beyond what was
measured: the client accepts the ack (no freeze) but transitions on neither
subcode, so it plausibly waits for content it never received — for 03 a
character-select/world payload (consistent with R40's finding that the full
`0x3D4B` GetWorldInfoVital form fires when the logout dialog opens, i.e. the client
pre-fetches world info as if preparing a transition), and for 01 a close
instruction or server-side socket close. Raw material for that design is
complete under `GameClient\capture_gt007_20260817_192713\` plus the retained
run copy.

## Non-claims

Not proven here: that the ack causes the freeze prevention (no control run),
any multi-cycle logout/login, logout before scene entry, any subcode other
than 01/03, or any statement about what response shape will succeed — that is
a hypothesis for a future ledger entry, not a finding of this run.

## Evidence

Hash-pinned in `PF_GT007_LOGOUT_ECHO_ACK_CLIENT_TRANSITION_NEGATIVE_20260817.manifest`:
the full capture set under `GameClient\capture_gt007_20260817_192713` (server
console out/err, `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`, raw GAME and LOGIN
logs), the job logs `pf_bridge\outbox\080_gt007_boot.*`,
`081_gt007_teardown.*`, `081_ctrlc_20260817_194023.json`, and the retained run
copy `Pirate Force ServerProject\state\pirateforce_gt007_20260817_192713.sqlite3`.
