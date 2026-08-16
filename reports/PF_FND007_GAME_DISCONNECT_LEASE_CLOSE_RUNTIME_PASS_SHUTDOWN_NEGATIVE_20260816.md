# FND-007 — GAME disconnect lease close pass / shutdown negative

Date: 2026-08-16
Implementation checkpoint: `177e1fa`
Result: Grade B bounded runtime pass; Grade E server-shutdown negative

## Primary claim

One normal client GAME disconnect closed exactly its connection-local SQLite
session lease while the server process and listeners remained live. The close did
not rewrite the persisted character position. This proves one normal-disconnect
lifecycle only, not graceful server shutdown, crash recovery, or concurrent-client
behavior.

Capture root:
`GameClient/capture_fnd007_disconnect_25690816_124917`.
Database: `state/fnd007_disconnect_25690816_124917.sqlite3`.

## Exact connection and lease evidence

- Before client close, read-only inspection recorded session
  `aeee8c26bef046cfa0a8958579d7f68d`, account 1, generation 6, selected character
  1, opened `2026-08-16T05:52:14.981124+00:00`, with `closed_at=NULL`.
- `GAME_LIVE.txt` records the final request at `12:54:23.995` and its processed
  state at `12:54:23.997`. The server transcript then records `game client closed`
  and `closed game log`.
- The same SID has exact
  `closed_at=2026-08-16T05:54:24.102133+00:00`. The post-close snapshot was taken
  after that transition. This was not startup expiry or account-wide replacement:
  the server had not restarted and no later session was opened.
- The Chief directly observed the normal UI-confirmed exit and confirmed that
  client PID 1872 was gone (operator observation). The retained PID file is an
  identifier, not an exit-code sidecar, so exit code zero is not claimed.
- Read-only pre/post inspection found the character position unchanged at scene 1,
  sequence 0, `(-9239.95703125,-2830.045166015625,186)`, heading 0, with unchanged
  `updated_at=2026-08-15T05:05:46.799338+00:00`. Disconnect therefore closed the
  lease without adding a position checkpoint.

The pre-close main database SHA-256 was
`7AD4F7F2CEF6B656C9526CA37B036594149B51FF0541F66553B34A09FA2CD713`;
the post-close and final main database SHA-256 is
`E667A6714C9CBA712BDC43F8A1D7C361A95AC92032FFECD8A7701B0520720FD2`.
Final read-only audit returned `PRAGMA integrity_check=ok`, an empty foreign-key
check, one non-deleted `Arena01` row, and the unchanged two migration checksums.

## Listener continuity and operational negative

After the GAME log closed, exact validated Python server PID 12228 remained alive
and ports 10188/10189 remained listening. This was a direct operational system
observation; no separate netstat/PID-query sidecar was retained. The server
transcript remained open until `12:55:44`, more than one minute after the database
close, and was then ended by the stop procedure.

Ctrl+C still did not stop the server. After exact command-line validation, PID
12228 was force-stopped; the PTY/pipeline ended with exit 1 and the transcript has
no graceful stopped marker. This remains a Grade E server-shutdown result and is
separate from the successful per-connection lease close.

## Evidence ceiling

This checkpoint proves one selected local character's exact session lease closes
on a normal GAME disconnect, with no position rewrite, while the same server
continues listening. It does not prove graceful process shutdown, abrupt network
loss, process/power-loss recovery, close-error retry, multiple simultaneous or
sequential GAME clients, authenticated multi-account ownership, remote characters,
or any new protocol/gameplay behavior. No source, scenario, packet, schema,
migration, hypothesis, or immutable V141 file changed for this runtime-result
checkpoint.

The adjacent manifest pins eight minimal retained artifacts by path, size, and
SHA-256.
