# FND-009 — abrupt server-process loss and restart recovery

Date: 2026-08-16
Result: Grade B bounded recovery pass; Grade E deliberate process-loss trigger

## Primary claim

One fully committed TargetPos checkpoint and its selected character/session state
survived a forced Foundation server-process loss. A fresh server process using the
same isolated SQLite database closed the stale open lease before the new client
login, then Character List/Select/StartGame projected the same character identity,
name, opaque actor/avatar blobs, and exact persisted MovementAttr without a
CreateActor request. The replacement connection later closed normally and the
replacement server completed the already-proven requested-stop path with exit 0.

Round A capture:
`GameClient/capture_fnd009_abrupt_restart_25690816_141001_A`.
Round B capture:
`GameClient/capture_fnd009_abrupt_restart_25690816_141001_B`.
Live database used by both rounds:
`state/fnd009_abrupt_restart_25690816_141001.sqlite3`.

## Round A — committed checkpoint and forced loss

- Character `Arena01`, selector 0, identity `0x10010001:0`, used exact persisted
  actor wire 208 bytes/SHA-256
  `DC16B24104E863D428B4BEF7F7CB47CCE8E5CB9FBF025AE36E558FA18704C66D`
  and avatar wire 103 bytes/SHA-256
  `B8F3CBEBF0F7CCC071C3D4D46EF24BAF33DF2A2FEB87FA8CEF692D1551EC32C0`.
- The final captured 44-byte singleton TargetPos request was frame 74 at
  `2026-08-16T14:17:27.384`; its PC SHA-256 is
  `96AD005FFBE513707617D681C30D7554DF37AD0B2514665E16895ECD5DC2F47B`.
  It decodes to `x=-7292.4833984375`, `y=-3187.03759765625`, `z=186`,
  `heading=0.18130016326904297`, moving 0. The database records the same values
  in the persisted Position at scene 1/sequence 0, with
  `updated_at=2026-08-16T07:17:27.397323+00:00`.
- Exact session `becd6c1efb9e4443825cfb4f46ce9210`, generation 8, was selected on
  character 1 and remained open. The pre-kill audit found integrity `ok`, empty
  foreign-key violations, and unchanged migration checksums.
- At `2026-08-16T07:19:22.4737475Z`, the retained precheck pinned Python server
  PID 11412, its exact command line/database/capture paths, active listeners
  10188/10189, and active client PID 2308. The retained helper then performed
  `Stop-Process -Id 11412 -Force` between
  `07:19:40.8515826Z` and `07:19:40.9729527Z`; it records the process present
  before and absent after with no helper error.
- The GAME live stream was still active immediately before that helper window:
  heartbeat sequence 98 was sent at local time `14:19:40.549`, client request
  frame 141 arrived at `14:19:40.755`, and its processed state followed at
  `14:19:40.757`.
- The post-kill process audit records server PID 11412 absent, no listeners, and
  the same client PID 2308 still running. The server exit sidecar is
  `4294967295`; no clean-stop marker is claimed. The post-kill database snapshot
  still has the exact checkpoint and generation 8 with `closed_at=NULL`.

The forced termination is Grade E operational setup evidence. It is not a clean
or graceful shutdown and does not by itself prove crash safety.

## Round B — startup repair and exact reload

- The retained pre-login audit at `2026-08-16T07:24:10.287684+00:00` records the
  same generation-8 SID closed at
  `2026-08-16T07:23:35.700246+00:00`, before the fresh client login flow. The
  checkpoint and opaque blobs are unchanged.
- Round B contains no CreateActor request. Character List at
  `2026-08-16T14:26:11.230` emits a 253-byte PC with SHA-256
  `8F92597B7FB8AEADB6506FDDC89EF0EA12ECF90CB90654F6AE74F4BC80D9DE6F`,
  byte-identical to Round A. It retains `Arena01`, selector 0 and identity
  `0x10010001:0`.
- StartGame at `2026-08-16T14:27:23.637` emits a 440-byte PC with SHA-256
  `0F7E5C58B41EF075B4F89E573704C978B2B4921B45AA4D5AA0E3A436A03A86FA`.
  Its exact 55-byte MovementAttr payload has SHA-256
  `65D6CB27153560D2F35DB658F63F212D2B6FFFBF70E581DC9E7FDB69FD224436`
  and carries identity `0x10010001`, the exact Round-A checkpoint
  coordinates/heading, and moving 0. StartGame carries scene 1/sequence 0
  separately in its ActorAttr projection.
- The new selected session is `fc31d7574cf748a29cc340005f50aa4c`, generation
  9, opened `2026-08-16T07:26:10.396348+00:00`. Normal GAME disconnect closed
  that exact SID at `2026-08-16T07:30:04.951647+00:00` without rewriting the
  checkpoint. The final retained GAME request/state immediately before the close
  are frame 104 at local time `14:30:03.741` and processed state at
  `14:30:03.744`.
- For final server teardown, the retained helper records console attachment for
  the console associated with exact target PID 20252 and `ctrl_c_sent=true`
  between `07:32:19.136828Z` and `07:32:19.137617Z`; the server then closed the
  GAME/LOGIN logs, emitted one `[FOUNDATION] stopped`, and exited 0 with empty
  stderr. `final_process.json` records both server PID 20252 and client PID 12704
  absent with wrapper exit 0 and no remaining listeners.

## Database and artifact audit

The immutable initial, post-kill, and final snapshots are 53,248 bytes with
SHA-256 values respectively:

- `4265B50B4DB17512982AB934906A7C54D5F6E9300C11005328D6BBBBFE299FD0`;
- `DB6DCA5EA4E38DBB76550AEA103634EDBDEB65E6559571F95943C21DADBD0CD3`;
- `EB260DF6C27D89DAA2D76FBC2F02EA41FE77ADFB854BFC11FB7726F9BA1E5CD1`.

The post-kill and final snapshot sets retain a 32,768-byte SHM and zero-byte WAL.
The final audit records one non-deleted `Arena01`, integrity `ok`, empty
foreign-key violations, and the exact stored migration checksums for versions 1
and 2. The adjacent manifest pins 43 immutable artifacts by path, size and
SHA-256. It excludes the mutable live database and its live WAL/SHM paths.

## Evidence ceiling

This checkpoint proves recovery of one stable, already-committed local character
checkpoint across one exact forced process loss and fresh server/client
Select/StartGame, plus startup closure of one stale selected lease and normal
closure of its replacement. It does not prove durability of an in-flight or
uncommitted transaction, non-empty-WAL recovery, database corruption recovery,
power loss, every crash/kill mechanism, concurrent or remote clients,
authenticated multi-account ownership, rename/delete behavior, or any new
gameplay/protocol hypothesis. No source, scenario, migration, V141 file, or
runtime behavior changed for this checkpoint.
