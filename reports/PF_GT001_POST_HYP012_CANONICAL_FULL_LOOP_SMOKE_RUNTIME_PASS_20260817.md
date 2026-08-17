# GT-001 — the canonical full loop still passes at the HEAD that carries M4, item-14 and HYP-PF-012

Date: 2026-08-17
Scope: one attended single-client session driven through the real
`GameClient.local.bin` against the canonical database `state\pirateforce.sqlite3`
at HEAD `b90007e`, the commit that landed the HYP-PF-012 acknowledged-logout
path (following `4c29a63` M4 runtime hookup and `55c7c59` item-14, the three
`src/`-touching commits since the previous GT-001 pass). Recurring smoke claim
only; no protocol hypothesis changed, no inventory mutation, no ledger edit, no
matrix grade is moved by this report alone.

## Result

**Grade B runtime pass** for one claim:

> At HEAD `b90007e` the basic loop — login, server select, character select,
> scene entry into Port Royal, clean client exit, requested server stop — still
> passes on the canonical database with a clean shutdown, zero stderr, and
> exactly the expected one-session database delta.

This is the recurring GT-001 smoke defined in `pf_bridge\GAME_TEST_QUEUE.md`,
re-armed because `4c29a63`, `55c7c59` and `b90007e` touched `src/`. The boot was
the standard one **without** `--logout-hypothesis-scenario`; the HYP-PF-012 path
is therefore untouched in this run (it is exercised separately in GT-007, the
same big round). It proves the landed WIP did not break the baseline loop.

## Run identity

| | value |
|---|---|
| HEAD under test | `b90007e` |
| capture root | `GameClient\capture_gt001_20260817_192033` |
| shim / server PID | 20432 / 10008 |
| client PID | 14328 (window title `Pirate Force`) |
| jobs | `072` (boot+client, staged in round 39 and used unmodified), `073` (teardown, queued before the client opened per the R31 rule) |
| driver | attended big round 19:20–19:24, main session as tester with its existing computer-use grant, Panya at the machine |
| pre-test backup | `pf_bridge\backup\pirateforce_before_gt001_20260817_192033.sqlite3` (sha equal to the pre-run canonical `CACE7F77..F493`) |

## Measurements

### Client-observable layer (each point directly observed on screen)

- Server select `Pirate Force Local` / `Channel 1` → PvP warning dialog →
  confirmed → character select shows `Arena01` with nameboard `Port Royal` →
  middle button → WANTED loading screen → scene entry with **HP 100/100,
  minimap, map name Port Royal, chat online line**.
- Spawn coordinate readout **X:-8,094 Y:-3,207** — exactly the position GT-005
  persisted, re-confirmed in passing for the second consecutive GT-001 run
  (bonus observation, not this report's claim).
- Clean exit: one X click → confirm dialog → window closed normally.

### Wire/DB layer (job `073` after the window closed)

- Ctrl+C stopped the server on the first attempt: helper json records
  `ctrl_c_sent: true` against shim PID 20432, exit 0. Server and shim
  `exited=True`; `stopped ×1`, `ready ×2`, `traceback 0`, **stderr 0 bytes**,
  listeners remaining 0, GameClient processes remaining 0.
- Database delta is exactly the expected one: sessions with a selected
  character 4→**5**, blank-connection sessions 0, open sessions 0,
  `lease_generation` 4→**5**, `integrity_check` ok, empty foreign-key check,
  backpack rows unchanged `[identity 1 @ slot 0, identity 2 @ slot 1,
  identity 4 @ slot 3]`, `character_positions` row unmoved (the player did not
  walk in this run).
- **The canonical database sha moved, by expectation, from
  `CACE7F7755E79AF0C2E637BC6C09C131E6152436F3141E136BC457ECA74DF493` to
  `FA794D0B1B69C6DCF0C7BCF0869FBEDC18138890C623547275952B3FEFE14400`** (the new
  closed session row). Any job that gates on the canonical sha must be updated
  to the new value before use; the staged-job practice of checking the sha
  against the latest LOCK release note before running exists for exactly this.

### Observation recorded without interpretation

`TargetPos` mentions in the server console numbered 6 with no walking, matching
the boot-and-entry baseline of the previous GT-001 run (also 6). The earlier
rule stands: `mentions > 0` must never be used as evidence of walking.

## Non-claims

Not proven here: any inventory move, combat, chat semantics, movement or
persistence in this run (the player did not walk), multi-client behavior, the
HYP-PF-012 logout path (standard boot, no scenario flag — see GT-007), or
anything beyond the single loop above.

## Evidence

Hash-pinned in `PF_GT001_POST_HYP012_CANONICAL_FULL_LOOP_SMOKE_RUNTIME_PASS_20260817.manifest`:
the full capture set under `GameClient\capture_gt001_20260817_192033` (server
console out/err, `GAME_LIVE.txt`, `GAME_EVENTS_LIVE.txt`, raw GAME and LOGIN
logs), the job logs `pf_bridge\outbox\072_gt001_boot.*`,
`073_gt001_teardown.*`, `073_console_tail_20260817_192447.txt`,
`073_ctrlc_20260817_192447.json`, and the pre-test backup
`pf_bridge\backup\pirateforce_before_gt001_20260817_192033.sqlite3`.
