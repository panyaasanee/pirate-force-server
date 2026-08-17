# GT-006 — an unattended scheduled run cannot drive the client past the login list, and the boot it leaves behind writes nothing

Date: 2026-08-17
Scope: one unattended boot of the visible Foundation server plus the real
`GameClient.local.bin`, launched by scheduled-task jobs `053` / `054` / `055`
against the canonical database `state\pirateforce.sqlite3`.
Operational/negative claim only. No protocol hypothesis changed, no inventory
mutation, no ledger edit, no coverage grade moved.

## Result

**Grade E operational negative** for one claim:

> Inside a scheduled (unattended) run the Chief can boot the server and launch
> the real client, but cannot obtain computer-use control of the client window;
> the client therefore stops at the login/server-list screen, opens no GAME
> connection, creates no `sessions` row, consumes no lease, and leaves the
> canonical database byte-identical.

This closes the *harness* question that rounds 26–29 left open. It does **not**
advance GT-006's actual subject (chat input observation), which stays `PENDING`.

## Run identity

| | value |
|---|---|
| capture root | `GameClient\capture_gt006_boot_20260817_132858` |
| shim / server PID | `12528` / `13672` (both `start=13:29:03`) |
| client PID | `15348`, window title `'Pirate Force'` |
| jobs | `053` boot+client · `054` teardown (buggy) · `055` teardown fix |
| server stop | `13:50:59`, Ctrl+C accepted, `[FOUNDATION] stopped` ×1 |

## Measurements

### A1 — the authorization refusal is a property of scheduled runs, not of window state (fact)

Job `053` deliberately booted the client **first** so a live window existed, then
called `mcp__computer-use__request_access(["GameClient.local.bin"])`. The reply
was neither `notInstalled` nor an approval dialog, but a policy refusal stating
that access cannot be approved during a scheduled run and that retrying returns
the same result. `list_granted_applications` returned `allowedApps: []` on every
round from 26 through 30 inclusive.

This falsifies the earlier working hypothesis that a live game window would cause
an approval dialog to appear. The window was live and the refusal was identical.

### A2 — an unattended client reaches LoginVitalRes on its own, and stops there (fact)

The client needed no UI input to get onto the wire. From
`capture_v141\LOGIN_20260817_132926_035499_53075.txt` and the live console:

```
13:29:26  [+] LOGIN connection ('127.0.0.1', 53075)
          [L<] 38 bytes IDs=[(0, 9375, '0x249F'), (15, 17087, 'LSCN_LoginVitalReq')]   account 'test'
          [L>] LoginVitalRes + one local server/channel   ("Pirate Force Local" / "Channel 1")
          [*] login idle timeout
          [+] closed login log
```

No GAME connection on `10189` was ever opened: the capture directory contains a
`LOGIN_*` log and **no** `GAME_*` log, and `GAME_LIVE.txt files = 0`.

**Inference (not fact):** the boundary of an unattended run is exactly the
server-list screen — everything past it needs a click, so every GT item whose
evidence lives past that screen is blocked on authorization, not on tooling.

### A3 — the unattended boot left the database byte-identical (fact)

Read over a read-only URI after the server process had exited:

```
POS      (1, 'Arena01', 1, 0, -8094.60791015625, -3207.83056640625, 186.0, 2.4992544651031494,
          '2026-08-17T05:32:03.064945+00:00')
sessions with char   : 3        (unchanged from the GT-005 end state)
sessions blank-conn  : 0
max lease_generation : 3        (unchanged)
integrity            : ok
canonical sha AFTER  = F37BEFE6CFFC967DA7F8BF954F5554363D5FA1517FF5F7D6B6BFAFFA3CB795C8
```

The SHA equals the canonical value on record, and the three `sessions` rows are
the same three (`08509a0d…`, `6af845a5…`, `b88cc7a2…`), all already closed.

Note the scope of the word *persistence* here: the only table this claim touches
is `sessions` (plus a read of `character_positions`). Nothing was written.

**Correction to a standing note:** the rule of thumb "a bare TCP connect creates a
`sessions` row and consumes a lease" did **not** hold for this connection. A
LOGIN-port (`10188`) connection that completed LoginVitalReq/Res and then idled
out produced no row and no lease bump. The standing note should be read as
applying to the GAME port `10189` only. Treated as an inference about port scope
until a deliberate LOGIN-only probe confirms it.

### A4 — job `054` mis-parsed its own input and stopped nothing (negative, harness defect)

`054` read `053_client_info_*.txt`, which is a **single line** of
space-separated `k=v` pairs:

```
clientpid=15348 shim=12528 server=13672 stamp=20260817_132858
```

Its per-line regex `^(\w+)=(.+)$` matched greedily, so `clientpid` captured the
entire remainder of the line and `shim` / `server` were never set. The casts
produced PID `0`, and every subsequent operation targeted the System Idle
Process — hence `"Access is denied"` on `Kill`/`WaitForExit`, a Ctrl+C sidecar
with `"target_pid": 0, "attach_error": 1341, "ctrl_c_sent": false`, and the
give-away line `listeners remaining = 2`.

`054`'s one trustworthy measurement is `GameClient processes remaining = 0`,
which came from a name query rather than the bad PID: the client really was gone
(closed externally, which is what unblocked the bridge).

### A5 — job `055` finished the teardown cleanly (fact)

`055` re-parsed on whitespace, guarded against PID reuse by checking process name
and start time against the `053` boot window, and only then signalled:

```
BEFORE listener port=10189 owningPid=13672
BEFORE listener port=10188 owningPid=13672
server pid=13672 name=python start=13:29:03 hasExited=False
shim   pid=12528 name=py     start=13:29:03 hasExited=False
ctrl-c helper exit = 0        ctrl_c_sent: true, target_pid: 12528
server exited=True   shim exited=True
AFTER listeners = 0           AFTER GameClient processes = 0
stopped markers = 1           traceback markers = 0     stderr = 0 bytes
```

Graceful Ctrl+C shutdown worked on the first attempt this time — worth recording,
because FND-006/007/009 all had to fall back to `Stop-Process -Force`.

`-wal` (0 bytes) and `-shm` (32768 bytes) remain on disk after the clean stop,
consistent with the standing note that Ctrl+C always leaves both behind.

## What this does not prove

- Nothing about chat input, the actual subject of GT-006.
- Nothing about any client-observable layer: no screenshot, no UI reading, no
  rendered state was obtained this round, by construction.
- Not that the client *cannot* be driven — only that it cannot be driven from
  inside a scheduled run while `allowedApps` is empty.
- Not that a LOGIN-only connection never touches `sessions` in general; one
  observation on one port with one idle timeout.

## Unblock condition

Exactly one of:

1. add `GameClient.local.bin` to the scheduled task `pirate-force-chief-continue`
   settings (permanent; unblocks GT-001 / GT-003 / GT-006 unattended), or
2. an attended session in which Panya sends a message so the approval card can
   appear (per-session only).
