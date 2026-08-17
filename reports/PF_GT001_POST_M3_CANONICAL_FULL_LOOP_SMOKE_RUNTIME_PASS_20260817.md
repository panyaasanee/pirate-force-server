# GT-001 — the canonical full loop still passes at the first HEAD that carries HYP-PF-010

Date: 2026-08-17
Scope: one attended single-client session driven through the real
`GameClient.local.bin` against the canonical database `state\pirateforce.sqlite3`
at HEAD `abf3696`, the commit that landed the HYP-PF-010 generalized free-slot
move (5 `src/` files touched). Recurring smoke claim only; no protocol
hypothesis changed, no inventory mutation, no ledger edit, no matrix grade is
moved by this report alone.

## Result

**Grade B runtime pass** for one claim:

> At HEAD `abf3696` the basic loop — login, server select, character select,
> scene entry into Port Royal, clean client exit, requested server stop — still
> passes on the canonical database with a clean shutdown, zero stderr, and
> exactly the expected one-session database delta.

This is the recurring GT-001 smoke defined in `pf_bridge\GAME_TEST_QUEUE.md`,
re-armed because `abf3696` touched `src/`. It proves the landed WIP did not
break the baseline loop. It does not exercise the new HYP-PF-010 path at all:
nothing in `runtime.py` calls it yet (that is M4).

## Run identity

| | value |
|---|---|
| HEAD under test | `abf3696` |
| capture root | `GameClient\capture_gt001_20260817_143122` |
| shim / server PID | 4184 / 14612 |
| client PID | 9140 (window title `Pirate Force`) |
| jobs | `060` (boot+client), `061` (teardown, queued in inbox before the client opened per the R31 rule) |
| driver | attended session, Claude as tester, Panya at the machine; computer-use granted tier full at 14:34 while the game window was open |
| pre-test backup | `pf_bridge\backup\pirateforce_before_gt001_20260817_143122.sqlite3` (sha equal to the pre-run canonical `F37BEFE6..95C8`) |

## Measurements

### Client-observable layer (each point directly observed on screen)

- Server select `Pirate Force Local` / `Channel 1` → PvP warning dialog →
  confirmed → character select shows `Arena01` with nameboard `Port Royal`
  (the persisted position's map name) → middle button → WANTED loading screen
  (~30 s) → scene entry with **HP 100/100, LV.1, minimap, map name Port Royal,
  chat line `[ระบบ] : Pirate Force local server online`**.
- Spawn coordinate readout **X:-8,094 Y:-3,207** — exactly the position GT-005
  persisted. Position persistence is therefore re-confirmed in passing on a HEAD
  that includes the M3 landing, though that is a bonus observation, not this
  report's claim.
- Clean exit: one X click → confirm dialog → left button → window closed
  normally. No screenshots were retained; the observations above are operator
  observations in the ledger's established sense.

### Wire/DB layer (job `061` after the window closed)

- Ctrl+C stopped the server on the first attempt: helper json records
  `ctrl_c_sent: true` against shim PID 4184, exit 0. Server and shim
  `exited=True` (ExitCode reads empty as in job 057 — markers are the
  deciding evidence per the R30 lesson): `stopped ×1`, `ready ×2`,
  `traceback 0`, **stderr 0 bytes**, listeners remaining 0, GameClient
  processes remaining 0.
- Database delta is exactly the expected one: sessions with a selected
  character 3→**4**, blank-connection sessions 0, open sessions 0,
  `lease_generation` 3→**4**, `integrity_check` ok, empty foreign-key check,
  backpack rows unchanged `[identity 1 @ slot 0, identity 2 @ slot 1,
  identity 4 @ slot 3]`, `character_positions` row unmoved (the player did not
  walk in this run).
- **The canonical database sha moved, by expectation, from
  `F37BEFE6CFFC967DA7F8BF954F5554363D5FA1517FF5F7D6B6BFAFFA3CB795C8` to
  `CACE7F7755E79AF0C2E637BC6C09C131E6152436F3141E136BC457ECA74DF493`** (the new
  closed session row). Any job that gates on the canonical sha must be updated
  to the new value before use.

### Observation recorded without interpretation

`TargetPos` mentions in the server console numbered 6 although the player never
walked. GT-005's actual walk produced 29. The boot-and-entry baseline is
therefore not zero, and `mentions > 0` must never be used as evidence of
walking in a future test.

## Non-claims

Not proven here: any inventory move (the HYP-PF-010 path landed by `abf3696`
has no runtime caller yet), combat, chat semantics, movement or persistence in
this run (the player did not walk), multi-client behavior, or anything beyond
the single loop above. The two `0xAC52` chat-input frames captured later in
this same session are claimed separately in
`PF_GT006_CHAT_INPUT_UNKNOWN_FRAME_WIRE_CAPTURE_20260817.md`.

## Evidence

Hash-pinned in `PF_GT001_POST_M3_CANONICAL_FULL_LOOP_SMOKE_RUNTIME_PASS_20260817.manifest`:
the full capture set under `GameClient\capture_gt001_20260817_143122` (server
console out/err, `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`, raw GAME and LOGIN
logs) and the job logs `pf_bridge\outbox\060_gt001_boot.*`,
`061_gt001_teardown.*`, `061_console_tail_20260817_143920.txt`,
`061_ctrlc_20260817_143920.json`.
