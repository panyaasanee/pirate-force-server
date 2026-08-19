# Pirate Force RE checkpoint — V138 MARKER1 nearest-20 population reapply pass

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V138 derives from the runtime-passing V137 transport checkpoint. It preserves
the complete P0/q3020/MARKER1/TeleportVital chain and adds one bounded response
to the exact post-transition ready batch observed in V137.

The gate is the byte-exact 76-byte RuntimeReq version 0/mask 2/count 3:

`126F6E140000000008000B0212030012DD1A0B00320000000000000000080212A2250B040B020B000B000B000F000012902A0B002A004821C62A00C03CC42A00C027442A000000000B000B00`

It contains TargetVital version 0 clear, a minimal TeleportVital version 4 ready
record, and TargetPosVital version 0 at exact MARKER1 XYZ
`(-10322,-755,671)`. V138 requires the V137 transport state, matches the entire
raw packet, sets one-shot state before queueing, and sends one immediate
authoritative nearest-20 population snapshot.

## Exact population

Membership is exactly:

`[86,80,0,1,65,22,16,85,5,92,84,50,89,144,145,39,87,82,30,70]`

Every member is a destination entrant and receives full placement MovementAttr.
P30 alone preserves exact HP `3857/3857` and BasicAttr name `Tornado Eagle`;
the other 19 retain the current proven default HP `100/100` and empty BasicAttr
name. The snapshot contains exactly 20 NPCAttr and 20 MovementAttr records.

Uncompressed protocol content is 3,152 bytes, SHA-256:

`6B8DD30BBE29641D99849F96601B61C8F4791FD06F5C900CD095B67C50A40C64`

Its exact 3,165-byte Snappy frame is SHA-256:

`7C844EC3CA4B39231AB9E25A2F14B00922BF7215357E3143E2840687846DAEA0`

Pre-sequence, altered envelope/count/version/body/trailing variants, and replay
send nothing. V138 emits no delayed reapply, message, music, ACK, StartGame, or
additional teleport. Destination interaction remains deferred until a fresh
singleton marker TargetPos and a safe facing builder are available.

## Exact live result

The single flushed session entered Port Royal normally. Runtime readiness was
recorded at `05:54:23.481`. The tested sequence was:

- P0 TargetVital kind 2 plus embedded ChooseNPC, event seq 2/frame 119 at
  `05:57:28.718`;
- exact q3020 operation 1, seq 3/frame 128 at `05:57:44.849`, followed by the
  unchanged action-6 response;
- exact q3020 operation 2, seq 4/frame 135 at `05:57:57.184`, followed by the
  unchanged action-1 response;
- MARKER1 prompt queued at `05:57:57.549` and sent at `05:57:57.553`;
- exact positive TeleportCheck value-1 confirmation, seq 5/frame 145 at
  `05:58:13.142`;
- V137 TeleportVital transport queued at `05:58:13.149` and sent once at
  `05:58:13.151`;
- exact 76-byte post-transition ready batch, seq 6/frame 146 at
  `05:58:33.952`;
- V138 population queued at `05:58:33.957` and exact label
  `V138_MARKER1_READY_AUTHORITATIVE_NEAREST20_FULL_MOVEMENT_REAPPLY_ONCE`
  sent at `05:58:33.958`, 3,165 bytes, late by only 0.2 ms.

Final state proves ready-capture count 1, population-send count 1, current
membership equal to the exact list above, refresh anchor
`(-10322,-755,671)`, and `npc_spawn_sent=true`.

The client remained at the Port Royal marker with coordinate UI
`X:-10,322 Y:-755`; after the snapshot, the local destination population was
visible, including the `Prison Teller` overhead role label. This is the expected
visual consequence of the authoritative snapshot and is consistent with the
exact membership and position data.

## Health and proof boundary

The session completed 192 heartbeats and ended at raw frame 204. There were 57
heartbeats and 58 received frames after the single V138 send. The final
heartbeat at `06:00:27.537` was 113.579 seconds after the snapshot frame.
Across all six flushed capture artifacts there are zero ErrorData, version
mismatch, `28317`, traceback, fatal, SEND_FAILED, or disconnect markers; server
stderr is empty.

The startup console still prints one inherited V123-era sentence:
`Runtime milestone is client acceptance/visible blade at 4/40 plus optional
item-activation event-code-2 capture.` This is stale documentation/logging
residue only; it is not the V138 milestone and caused no item request, response,
or mutation. Preserve the frozen runtime bytes for this checkpoint, then remove
or relabel that sentence in V139 without changing proven behavior.

V138 proves that after the V137 same-connection transport, this client accepts
one immediate authoritative destination population in response to the exact
ready batch, retains all 20 actors, and remains healthy. It does not prove the
original server used this exact q3020/MARKER1 ordering, this exact population
timing, or this exact response composition. It does not establish quest
completion, QuestAttr persistence, rewards, vehicle state, destination NPC
interaction, original-server population policy, or direction semantics.

## Build and artifact verification

Post-runtime verification reran `py_compile`, the full self-test, Snappy
roundtrip, exact packet/hash assertions, and ZIP integrity. The ZIP has exactly
three root entries and every embedded file matches current byte-for-byte:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v138.py`, 331,820 bytes  
  `6026478B9A119FA08358D056255CAE7EB6180233F078D1C54FA58D080F6AE174`
- `run_v138_port_royal_marker1_population_reapply.bat`, 471 bytes  
  `F7D014F3BF92BDABB36123ABB5F5924F218BBA50BBED8E4BC1CD5E0E530975D5`

Package: `packages/PF_Login_Game_Test_v138.zip`, 4,378,200 bytes  
SHA-256: `C97BF8876FF3C7762ABD7675E285FBDE9E6C197DF2929428FEF76702A7F3432B`

Flushed runtime capture hashes:

- raw GAME: `8927FD56A1198FD4FF0F208C19036E74A24F0C05C62D7F061E93425511674138`
- event journal: `9C8D6575205ED91916925FB81BC0F8B3D2B7FE2B9B5E34AEA87911274E657611`
- live GAME: `8854BA53893EEB31EA8DBB3A7867A18359E63992396846C67CE839442CC4C508`
- raw LOGIN: `DCD0BA7118A4F8FD553F8F5C62764B43545942B8CE9EC8D0C4DA402FC4104E58`
- server console: `787474D2A848286124E37ED254A232CB6BBF3868D60D3B65FB64986506968F36`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

V138 is the current passing evidence checkpoint. GameClient files remain in
place; no cleanup was performed and no `references/` or `evidence/` file was
modified.

Verified passing checkpoint backup:

`backups/v138_marker1_population_reapply_20260815_060241/`
