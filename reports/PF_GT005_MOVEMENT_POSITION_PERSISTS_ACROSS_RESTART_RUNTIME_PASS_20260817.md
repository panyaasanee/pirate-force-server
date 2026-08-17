# GT-005 — a position the player walked to survives a server restart and is where the client respawns

Date: 2026-08-17
Scope: one attended two-boot session driven through the real `GameClient.local.bin`
against the canonical database `state\pirateforce.sqlite3`. Movement-persistence
claim only; no protocol hypothesis changed, no inventory mutation, no ledger edit.

## Result

**Grade B runtime pass** for one claim:

> A position the local player actually walked to through the real client is
> checkpointed into `character_positions`, survives a full server process
> restart, and is the position the client is standing at on the next entry —
> confirmed on the wire, in the database, and on screen.

Superseded observation: the previous evidence for this row
(`PF_FND010_ABRUPT_CLIENT_PROCESS_LOSS_RECONNECT_RUNTIME_PASS_20260816.md`)
only showed an *unchanged* position surviving an abrupt client loss, which left
"a position the player moved to survives" unproven. This run closes exactly that
gap and nothing wider.

## Run identity

| | boot 1 (walk) | boot 2 (respawn) |
|---|---|---|
| capture root | `GameClient\capture_gt005_boot1_20260817_122339` | `GameClient\capture_gt005_boot2_20260817_123551` |
| shim / server PID | 18260 / 2868 | 12216 / 7052 |
| client PID | 19576 | 3636 |
| jobs | `047` (boot+client), `048` (stop+read) | `049` (boot+client), `050` (stop+final read) |
| window resolved | `pid=19576 name=GameClient.local.bin title='Pirate Force'` | `window 'Pirate Force' after 0s` |

Both boots ran on the **same database file**; boot 2 started only after boot 1's
server process had exited (`server exited=True code=0` at `12:34:01`).

## Measurements

### A1 — the walked position is in the database (fact)

`character_positions` for character 1, read over a read-only connection after
each server had exited:

```
BEFORE (12:23:40)  x=-9098.5507812500  y=-2866.8618164062  z=186.0  h=2.9943714142  updated_at=2026-08-16T16:35:08Z
AFTER  (12:34:05)  x=-8094.6079101562  y=-3207.8305664062  z=186.0  h=2.4992544651  updated_at=2026-08-17T05:32:03Z
FINAL  (12:40:50)  x=-8094.6079101562  y=-3207.8305664062  z=186.0  h=2.4992544651  updated_at=2026-08-17T05:32:03Z
```

`updated_at` moved to a timestamp inside the walk window, and the row did not
move again across the restart. Re-verified independently after the session at
`12:5x` over a fresh read-only copy: identical row, `sha256` of the canonical
database `F37BEFE6CFFC967DA7F8BF954F5554363D5FA1517FF5F7D6B6BFAFFA3CB795C8`.

### A2 — the real client is what produced those writes (fact)

Boot 1's visible server console recorded **330 inbound frames, 29 of them
`TargetPosVital`**, and exactly one client-initiated `TeleportVital`. The
client-side capture agrees from the other end: `capture_v141\GAME_LIVE.txt` for
boot 1 carries **29** `TargetPos` mentions. Boot 2, where the player only entered
and stood still, recorded **0** `TargetPosVital` on both sides.

Two independent recorders, one at each end of the socket, agree on the same
count. This retires the open question from
`FINDINGS_R22` — the walking frames that write the row are emitted by the real
client, not only by the synthetic replay client.

### A3 — the same value comes back out and is where the character stands (fact)

Each boot sent exactly one `FOUNDATION_SELECTED_START_GAME` response (418 bytes)
followed by one `V113_TELEPORT_SCENE1_STABLE_ZERO_TARGET_ONCE` (73 bytes). On
screen the coordinate readout was:

```
entry, boot 1     X:-9,098  Y:-2,866   = database BEFORE
after walking     X:-8,094  Y:-3,207   = database AFTER
entry, boot 2     X:-8,094  Y:-3,207   = database AFTER, not the original spawn
```

Screenshots: `pf_bridge\evidence_screens\gt005_r1_UI_BEFORE_x-9098_y-2866.jpg`,
`gt005_r1_UI_AFTER_x-8094_y-3207.jpg`, `gt005_r2_UI_RESPAWN_x-8094_y-3207.jpg`
plus three world-context frames and the clean-exit dialog.

### A4 — lifecycle and blast radius (fact)

- server exit 0 and shim exit 0 on both boots; one `[FOUNDATION] stopped` marker
  per boot; listeners remaining 0; mirrored `stderr` 0 bytes for both capture
  roots (`server_console_live.err.txt` is 0 bytes on disk for both).
- `sessions` with `selected_character_id IS NOT NULL`: 1 → 2 → 3, one per entry;
  `open sessions` 0; `lease_generation` 1 → 2 → 3; all three rows carry a
  `closed_at`.
- `character_backpacks` unchanged at `updated_at=2026-08-16T10:30:39Z` — the
  one-shot backpack write path was never touched.
- `pragma integrity_check` = `ok`, `pragma foreign_key_check` empty, and
  `git status --porcelain` 6 lines before and after.
- Sidecar files: job `050` checked at `12:40:50.144` and found no `-wal`/`-shm`,
  then opened the database itself to read the final state, which left
  `pirateforce.sqlite3-wal` (0 bytes) and `pirateforce.sqlite3-shm` (32 KiB)
  behind at `12:40:50`/`12:40:51`. The check ran before the reader, so the
  "no sidecars" line in that job's log describes the moment before its own read.
  The database file itself is byte-identical to the value hashed above, and the
  `-wal` is empty, so no committed content is parked outside the main file. A
  cleanliness gate that means "no sidecars after the run" has to run after the
  last reader, not before it.

### A5 — the zero-target teleport did not displace the character (negative result)

`FINDINGS_R23` flagged `runtime.py:466` sending `make_login_teleport(1, 0)`
(default `x=y=z=0.0`) immediately after `START_GAME_RES`, and predicted it as the
first suspect if the database were right but the screen wrong. Both entries
placed the character at the persisted position, so at the observable layer this
frame does not win. **Why** the client ignores it was not measured; see nonclaims.

### Evidence correction

Job `048` printed `stderr = -1 bytes` at `12:34:05`. That is the job's
"file not found yet" sentinel for the mirrored stderr path, not a measurement of
a negative size. Job `050` re-read both paths at `12:40:49` and reported
`0 bytes` for boot 1 and boot 2; the files are 0 bytes on disk today. Use the
`050` figures.

## Deliberate state change

The canonical database sha256 changed **by design** from
`673F4BFB1C35EC390D6ED3B0C1FE3F581B20C6895ACE9183C86A5971BCCC9708` to
`F37BEFE6CFFC967DA7F8BF954F5554363D5FA1517FF5F7D6B6BFAFFA3CB795C8` (position row
plus three session rows). The pre-test copy is preserved at
`pf_bridge\backup\pirateforce_before_gt005_20260817_122339.sqlite3`. Any job that
gates on a hard-coded canonical sha must be updated to the new value before use.

## Nonclaims

This proves one walk, in one scene (Port Royal, scene 1), with one client, on one
machine. It is **not** proof of: server-side movement validation or authoritative
correction (reported positions are still accepted as given); scene transitions or
any other scene, spawn point, or instance; the number of checkpoints written per
walk (only the last value was read back); the visible heading (the UI shows no
heading figure — the heading claim is database-only); multi-client behaviour (the
server is strictly serial, see `FINDINGS_R18`); the mechanism by which the client
ignores the zero-target teleport frame; and any persistence outside the
`character_positions` and `sessions` tables. No hypothesis ledger entry changed;
`production_allowed` remains `false` everywhere.
