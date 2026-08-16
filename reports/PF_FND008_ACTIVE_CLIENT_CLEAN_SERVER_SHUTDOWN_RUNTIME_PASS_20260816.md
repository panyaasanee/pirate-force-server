# FND-008 — active-client clean requested server shutdown

Date: 2026-08-16
Implementation checkpoints: `1d351e7`, Windows signal corrective `68ee812`
Result: Grade B bounded runtime pass

## Primary claim

In a run where the Windows helper attached to the console associated with exact
target PID 24080 and returned `ctrl_c_sent=true`, the Foundation server stopped
while a selected GAME client was still active. The stop closed the exact
connection-local SQLite lease without rewriting position, closed the listener
logs, emitted exactly one `[FOUNDATION] stopped`, and returned server exit code 0
with empty stderr.

Capture root:
`GameClient/capture_fnd008_clean_shutdown_25690816_134727`.
Database: `state/fnd008_clean_shutdown_25690816_134727.sqlite3`.

## Exact active-connection and signal boundary

- `GAME_LIVE.txt` records 94 heartbeat sends. Its final heartbeat is sequence 94
  at `2026-08-16T13:53:41.225`; the final client request is frame 95 at
  `13:53:41.617`, followed by processed state at `13:53:41.620`. Thus the GAME
  connection was active immediately before the stop rather than already closed.
- `signal_send.json` identifies target PID 24080 and records successful console
  attachment and `ctrl_c_sent=true` between
  `2026-08-16T06:53:42.792204+00:00` and
  `2026-08-16T06:53:42.795041+00:00`. This is evidence for that retained Windows
  helper invocation only, not every console host or signal-delivery mechanism.
- Server stdout then records shutdown-induced GAME and LOGIN `BrokenPipeError`
  diagnostics, `closed login log`, `closed game log`, and exactly one
  `[FOUNDATION] stopped`. `server.exit.txt` is 0 and `server.stderr.txt` is empty.

The Chief directly observed the still-connected client show a disconnect modal
after server stop and then acknowledged it (operator observation; no screenshot
was retained). Client PID 22500 is pinned by sidecar; its wrapper exit is 0 and
both client stdout and stderr are empty. The UI fact is not inferred from the raw
server logs.

## Exact lease and database result

Before the stop, `db_open.json` records exact session
`690593d79d7e4a9bb550900a48f2b21e`, account 1, generation 7, selected character
1, opened `2026-08-16T06:50:10.091626+00:00`, with `closed_at=NULL`. The final
database and `db_closed.json` record the same SID with
`closed_at=2026-08-16T06:53:42.854792+00:00`: 62.588 ms after the retained signal
window began and 59.751 ms after it ended.

Read-only audit confirms one non-deleted `Arena01` row and the unchanged position:
scene 1, sequence 0, `(-9239.95703125,-2830.045166015625,186)`, heading 0,
`updated_at=2026-08-15T05:05:46.799338+00:00`. The shutdown therefore added no
position checkpoint. Final database size is 53,248 bytes and SHA-256 is
`4265B50B4DB17512982AB934906A7C54D5F6E9300C11005328D6BBBBFE299FD0`.
`PRAGMA integrity_check` is `ok`, `foreign_key_check` is empty, and migration
versions 1 and 2 retain their exact stored checksums.

## Evidence ceiling

This checkpoint proves one clean requested shutdown with one active local GAME
client, exact per-connection lease close, bounded server completion marker and
process exit 0. It supersedes the FND-006/FND-007 operational shutdown gap only
for this exact helper-driven requested-stop path. It does not prove crash or power
loss, failure during an active transaction, every Windows console host or signal
source, abrupt network loss, concurrent clients, remote clients, authenticated
multi-account ownership, restart after this stop, or any gameplay/protocol change.
No position was checkpointed and no source was changed for this runtime-result
checkpoint.

The adjacent manifest pins 17 retained artifacts by exact path, size, and SHA-256.
It uses the immutable capture-root pre/post database snapshots; the mutable live
state database and its WAL/SHM paths are excluded.
