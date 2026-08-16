# FND-006 — server restart durability pass / shutdown negative

Date: 2026-08-16
Result: Grade B bounded runtime pass; Grade E clean-shutdown negative

## Primary claim

One persisted local character's identity, name, opaque actor/avatar bytes, and
movement checkpoint survived a stopped server process and were re-emitted by a
fresh server process to a fresh client Select/StartGame flow. This proves one
bounded server-process restart, not graceful shutdown or crash durability.

## Round A — checkpoint before restart

Capture root: `GameClient/capture_fnd006_restart_a_25690816_120850`.

- The existing non-deleted row was `Arena01`, selector 0, identity
  `0x10010001:0`. Initial StartGame emitted scene 1/seq 0,
  `(-9239.95703125,-2830.045166015625,186)`, heading 0.
- One operator click-to-move gesture produced the captured TargetPos movement
  stream. Its final exact value and persisted checkpoint were scene 1/seq 0,
  `x=-9192.125`, `y=-2674.037109375`, `z=186`,
  `heading=5.009882926940918`, updated
  `2026-08-16T05:13:51.669640+00:00`.
- The client exited through the normal UI and recorded PID 8012 was gone. There
  is no client exit-code sidecar, so exit code zero is not claimed.
- PTY Ctrl+C stopped the Round-A process and listeners, but the control tool
  returned exit 1 and no `[*] stopped` marker was recorded. This is enough to
  establish a process boundary, not a graceful-shutdown pass.

## Round B — reload after restart

Capture root: `GameClient/capture_fnd006_restart_b_25690816_120850`.

- On startup against the same database, Round B expired prior lease generation 6
  with `closed_at=2026-08-16T05:16:25.766297+00:00`, then opened generation 7.
- No CreateActor occurred. Character List/Select/StartGame used the same
  `Arena01`, selector 0, identity `0x10010001:0`, and persisted opaque wire data.
  Round-A and Round-B Character List PCs are byte-identical: 253 bytes, SHA-256
  `8F92597B7FB8AEADB6506FDDC89EF0EA12ECF90CB90654F6AE74F4BC80D9DE6F`.
  Final database values are actor wire 208 bytes/SHA-256
  `DC16B24104E863D428B4BEF7F7CB47CCE8E5CB9FBF025AE36E558FA18704C66D`
  and avatar wire 103 bytes/SHA-256
  `B8F3CBEBF0F7CCC071C3D4D46EF24BAF33DF2A2FEB87FA8CEF692D1551EC32C0`.
- Round-B StartGame MovementAttr contains the exact Round-A checkpoint:
  scene 1/seq 0, `(-9192.125,-2674.037109375,186)`, heading
  `5.009882926940918`. The 440-byte Round-A and Round-B StartGame PCs have
  SHA-256 `C7518540A7113D7CBD77B9A1F42CF25693A44412D5431CA3E64B4DD6F3C7246D`
  and `6117366B1F472AB381706BB0B5A9B3B4354686B54D48198749BAF237C9141953`,
  respectively. The operator directly observed minimap `-9192,-2674` and world
  label `Arena01` in the client.
- The client exited through the normal UI and recorded PID 22344 was gone; again,
  no exit-code-zero claim is made.
- PTY Ctrl+C and `GenerateConsoleCtrlEvent` did not reach the Python server.
  Exact validated server PID 328 was terminated with Stop-Process under the stop
  rule. Therefore clean process shutdown is an operational failure. The final
  generation-7 session remains open, which is the expected current limitation,
  not a session-close pass.

The first attempted Round-B launcher transcript is retained as a diagnostic only:
it failed before server start because `PYTHONPATH` was missing. It supplies no
gameplay, persistence, or restart evidence.

## Database and artifact audit

Read-only final audit of
`state/fnd006_restart_25690816_120850.sqlite3` found:

- exactly one character row and one non-deleted row;
- `PRAGMA integrity_check = ok` and empty `PRAGMA foreign_key_check`;
- unchanged migration versions/checksums:
  `1/9c1ad7eec36a3b7296eb398731941d08f6bb6ef809e0bd1dae9305485978c2e8`
  and
  `2/3c07171f45d6fcc4e7582cbdb4f23d0e23187cfd074b86761a8980f4aa8f0add`;
- exact final DB size 53,248 and SHA-256
  `25BFD5031376F41C2E4C7C4BA1B73F383C6AB756A58757854E2E9B822E2EF36B`.

The adjacent manifest pins every retained file in both capture roots plus the
final database: 21 artifacts with exact path, byte count, and SHA-256.

## Evidence ceiling

This checkpoint proves one server-process restart with durable local identity,
name, opaque wire data, and movement, followed by fresh client selection/start.
It does not prove graceful server shutdown, closed-session persistence, abrupt
crash/power-loss recovery, a second restart after Stop-Process, remote characters,
authenticated multi-account ownership, rename/uniqueness policy, delete, or any
new gameplay/protocol behavior. No source, scenario, V141, packet hypothesis, or
database schema changed.
