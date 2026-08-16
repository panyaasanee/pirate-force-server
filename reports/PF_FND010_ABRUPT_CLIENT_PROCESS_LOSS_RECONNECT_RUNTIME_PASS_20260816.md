# FND-010 — abrupt client-process loss and same-server reconnect

Date: 2026-08-16
Result: Grade B bounded server-reaction/reconnect pass; Grade E deliberate client-loss trigger

## Primary claim

One forced GameClient process loss closed exactly its selected, connection-local
SQLite lease without rewriting the committed character position while the same
Foundation server process and listeners remained live. A fresh client then used
that same server process to List/Select/StartGame the same character with
byte-identical projected identity/name/opaque-wire/position bytes and no
CreateActor request.

Capture root:
`GameClient/capture_fnd010_abrupt_client_25690816_160000`.
Live database:
`state/fnd010_abrupt_client_25690816_160000.sqlite3`.

## Client A — active selected lease and forced loss

- Exact selected session `80311b2e090441b68df24a770a64a665`, generation 10,
  opened `2026-08-16T08:01:08.567779+00:00`, remained open in two pre-kill
  audits. Its selected character was `Arena01`, selector 0, identity
  `0x10010001:0`.
- GAME traffic was active immediately before the trigger: heartbeat sequence 122
  was sent at local time `15:05:56.036`, frame 135 arrived at `15:05:56.242`,
  and its state was processed at `15:05:56.244`.
- The retained precheck at `2026-08-16T08:05:56.4225046Z` pins exact client PID
  7648, server PID 20444, both executable/command lines, the isolated DB/capture
  paths, and server-owned listeners 10188/10189. The helper performed one
  `Stop-Process -Force` against client PID 7648 between
  `08:05:56.5827148Z` and `08:05:56.7574606Z`; it records the client present
  before and absent after with no helper error. Client A's wrapper exit is
  `4294967295`.
- Server stdout records exact LOGIN and GAME `ConnectionResetError(10054)` paths
  and closure of Client A's GAME log. The same generation-10 SID gained
  `closed_at=2026-08-16T08:05:57.232852+00:00`, 650.137 ms after the trigger
  began and 475.391 ms after it ended.
- The retained post-kill process audit at `08:06:37.6732700Z` records client PID
  7648 absent while the same server PID 20444, exact command line, and listeners
  10188/10189 remained live.

The position before and after the forced loss is unchanged: scene 1/sequence 0,
`x=-7292.4833984375`, `y=-3187.03759765625`, `z=186`,
`heading=0.18130016326904297`, and
`updated_at=2026-08-16T07:17:27.397323+00:00`. Therefore this connection close
did not add a position checkpoint.

## Client B — same-process reconnect

- Client B connected to the still-running server at local time `15:07:54.508`.
  Exact session `2c78f59372bc427eb4a36ee83901206e`, generation 11, opened
  `2026-08-16T08:07:54.477764+00:00` and selected character 1.
- Both Client-A and Client-B Character List PCs are byte-identical: 253 bytes,
  SHA-256
  `8F92597B7FB8AEADB6506FDDC89EF0EA12ECF90CB90654F6AE74F4BC80D9DE6F`.
  Both StartGame PCs are byte-identical: 440 bytes, SHA-256
  `0F7E5C58B41EF075B4F89E573704C978B2B4921B45AA4D5AA0E3A436A03A86FA`.
  Each exact 55-byte MovementAttr payload has SHA-256
  `65D6CB27153560D2F35DB658F63F212D2B6FFFBF70E581DC9E7FDB69FD224436`
  and carries identity `0x10010001`, the unchanged coordinates/heading, and
  moving 0. Both GAME logs contain zero CreateActor.
- Initial and final SQLite snapshots retain the same 208-byte actor wire SHA-256
  `DC16B24104E863D428B4BEF7F7CB47CCE8E5CB9FBF025AE36E558FA18704C66D`
  and 103-byte avatar wire SHA-256
  `B8F3CBEBF0F7CCC071C3D4D46EF24BAF33DF2A2FEB87FA8CEF692D1551EC32C0`.
- The Chief directly observed minimap coordinates `-7292,-3187` and world name
  `Arena01` after Client B entered the world (operator observation; no screenshot
  was retained). This UI fact is not inferred from the raw logs.
- Client B exited with wrapper code 0. Generation 11 closed at
  `2026-08-16T08:09:48.718543+00:00` without rewriting position, while the same
  server PID/listeners remained live.

Client B's normal disconnect closed the GAME and LOGIN logs. The retained shutdown
helper later attached to the console associated with exact server PID 20444 and
returned `ctrl_c_sent=true`; the server then emitted exactly one
`[FOUNDATION] stopped`, produced empty stderr, exited 0, and left no listeners.
This is cleanup evidence, not a second primary claim.

## Database and artifact audit

Read-only inspection of the immutable snapshots found one non-deleted `Arena01`,
integrity `ok`, empty foreign-key violations, and unchanged stored checksums for
migration versions 1 and 2. The initial main snapshot is 53,248 bytes/SHA-256
`EB260DF6C27D89DAA2D76FBC2F02EA41FE77ADFB854BFC11FB7726F9BA1E5CD1`.
The final main snapshot is 53,248 bytes/SHA-256
`2641F30BB8122BDE2F02CDC2095B867F934EEE2EBEE1C6D0F598B7A94B4C99F1`;
its retained SHM is 32,768 bytes and its WAL is zero bytes.

Artifact limitation: no byte-frozen main/WAL/SHM snapshot was retained at the
post-kill, pre-reconnect boundary. `db_postkill.json`, audited at
`2026-08-16T08:06:36.854852+00:00`, is the sole retained intermediate logical
database oracle. It records generation 10 closed and the unchanged position before
generation 11 opened; the final immutable database independently retains the same
close timestamp and position. This supports the logical lease/position claim but
does not support an intermediate file-byte or WAL/SHM-state claim.

The adjacent manifest pins all 37 retained capture artifacts with exact paths,
sizes and SHA-256 values, including the two audit scripts. It excludes the mutable
live state database and its live WAL/SHM paths.

## Evidence ceiling

This checkpoint proves one controlled abrupt local-client process loss, exact
connection-local lease close, same-server/listener continuity, and one fresh
client reconnect with byte-identical persisted character projection. The client
kill is Grade E operational setup; the server reaction/reconnect is Grade B. It
does not prove network partition or half-open timeout behavior, client/OS power
loss, in-flight or uncommitted movement, intermediate DB/WAL bytes, non-empty-WAL
recovery, server crash, close-error retry, concurrent clients, remote clients,
authenticated multi-account ownership, or any new gameplay/protocol behavior.
No source, scenario, migration, V141 file, or runtime behavior changed.
