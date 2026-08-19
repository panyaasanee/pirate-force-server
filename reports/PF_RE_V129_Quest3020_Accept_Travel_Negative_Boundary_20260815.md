# Pirate Force RE checkpoint — V129 quest 3020 acceptance / travel negative boundary

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V129 preserves V128's verified WIELD/Z ActionVital capture, inventory, shop,
cash, population serializers, and stable bootstrap. Its focused change replaces
the level-53 quest-243 harness with the decoded level-1 quest 3020 at exact
Port Royal placement P0/template 1, identity `0x2001`. Runtime positively
completed the already proven action-6 / operation-2 / action-1 client-accept
sequence. It did not produce the hypothesized travel: no post-action-1 travel
request, no `TeleportCheckVital`, and no visually observed teleport occurred.
Post-runtime static tracing explains why: this client binds
`Player.TeleportWithVehicle` to a native no-op stub.

## Evidence-backed quest selection

Current-client data links MOBS row 1 to quest 3020 in both `QUEST_BEGIN` and
`QUEST_END`. QUEST row 3020 names `Q_TELEPORT_WITH_VEHICLE1`; its decoded
`Accept_Run` calls `Player.TeleportWithVehicle(Quest.Var2)` and the row supplies
data-backed `Var2=1`.

V129 therefore changes only the exact quest/actor tuple used by the previously
verified handshake:

- quest: `3020`;
- actor: P0/template 1, identity `0x2001`;
- action 6: `OpenAcceptUI_Run`;
- client request: operation 2 with every other constructor field zero;
- result: action 1 with P0 context.

It does not add QuestAttr, server quest persistence, rewards, progress,
completion, a transport response, or any guessed travel field.

## Static resolution of the travel call

The client registers `Player.TeleportWithVehicle` at `0x462601-0x46262B`
through Lua bridge `0x460AE0`, targeting native function `0x45FA00`.
That function is exactly `xor eax,eax; ret 4`: it reads neither caller state
nor its argument and emits no network request. `Player.Teleport`,
`Player.TeleportCheck`, and `Player.TeleportThenPlayMovie` bind to the same
stub in this client build.

Consequently the runtime negative is expected. It is not evidence of a missing
quest-state gate or a server response that should be guessed.

## Exact runtime sequence

At `2026-08-15T00:08:39.314`, five seconds after the first isolated
P0/P30/P91 population, the server sent the 45-byte RuntimeRes v4 action-6
packet:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E 0B 03 12 CC 0B 08 00 08 06 14 00 00 00 00 32 01 20 00 00 00 00 00 00 05 00 0B 00`

At `00:09:02.455`, frame 39, the client emitted the exact predicted 43-byte
RuntimeReq v0/mask `0x02` containing singleton QuestOperateVital `0x3E34`
version 3:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 34 3E 0B 03 12 CC 0B 08 02 08 00 14 00 00 00 00 32 00 00 00 00 00 00 00 00 05 00`

Decoded tuple:

`(quest_id=3020, operation=2, +0x17=0, +0x18=0, +0x20=0, +0x28=0)`

The one-shot gate recorded:

`V129_QUEST3020_OPERATE_REQUEST_CAPTURED fields=(3020, 2, 0, 0, 0, 0) capture_count=1 result=ACTION1_ACCEPT_SUCCESS_SENT_ONCE`

At `00:09:02.465`, ten milliseconds after the request, the server sent the
exact 45-byte RuntimeRes v4 action-1/P0 result:

`12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12 34 3E 0B 03 12 CC 0B 08 00 08 01 14 00 00 00 00 32 01 20 00 00 00 00 00 00 05 00 0B 00`

The client accepted the response and completed the local accept path. This is
a functional client-accept result only; it does not prove authoritative server
quest ownership or persistence.

## Travel negative boundary

The travel hypothesis failed cleanly. From action 1 until the last heartbeat:

- elapsed time: `225.041 s`;
- successful heartbeats: `112` (sequence 39 through 150);
- incoming post-action-1 RuntimeReq frames: `113`;
- empty heartbeat requests: `112`;
- non-empty requests: one closure-time
  `UserSetting_UpdateServerSettingVital 0x0F01` at frame 145;
- `TeleportCheckVital 0x4477`: zero;
- post-action-1 `TeleportVital` or `TargetPosVital`: zero;
- visually observed teleport: none.

The earlier frame-14 `TeleportVital` at `00:08:17.510` is the normal bootstrap
runtime entry and preceded the quest result by about 45 seconds. It is not a
quest follow-up.

Therefore V129 proves that the exact session-local action-1 acceptance works,
while the decoded `TeleportWithVehicle(1)` call terminates in the client's
native no-op stub. Do not answer `TeleportCheckVital`, invent a travel request,
or claim a successful teleport. No missing server-side prerequisite should be
inferred from this boundary.

## Timing and runtime health

Entry and milestone timing from the live sidecar:

- GAME connected: `00:07:17.519`;
- StartGameReq: `+29.017 s`;
- first runtime request/bootstrap TeleportVital: `+59.991 s`;
- first population-trigger TargetPos: `+76.789 s`;
- action-6 offer: `+81.795 s`;
- operation-2 request: `+104.936 s` from connection and `23.141 s` after
  action 6;
- final heartbeat: sequence 150 at `00:12:47.506`;
- final received game frame: 152.

The flushed capture has zero match for `ErrorData`, VitalData mismatch, read
failure, fatal, exception, traceback, disconnect, `28317`, or `SEND_FAILED`.
Server stderr is empty. Client and server closed cleanly and both raw logs
flushed.

## Build and artifact verification

`py -3 -m py_compile` and the complete V129 self-test passed after runtime
closure. The ZIP opens successfully, contains exactly three entries, and every
embedded byte matches the current source, launcher, and client binary:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v129.py`, 278,889 bytes  
  `FA463841138025412FA76B6A1C4F35A3E57448526E4B51D25CE3906CC36A2CCD`
- `run_v129_port_royal_quest3020_p0_wield_capture.bat`, 481 bytes  
  `5EAFB5CD011AAAD9935C987500046F441E912474D09E68E750EB94AFC9037389`

Exact-three-file package SHA-256:

`9A5992689D98EBE94CFDA68AEE04907D47A03F83DCC54B0097992A6B6CBAC9CF`

Flushed capture hashes:

- raw GAME: `D68C542871063C0EB09FB789536524518F3FD3DE24A32F7E172548A4CDCDFFF0`
- event journal: `720154FF61B9ACDF5DA9123163C53BD690B924DF1E5FC8CFD1AC416536E94DC3`
- live GAME: `3D048827C55635E8C6660BE3F33A720C994370652B3BC047A9FFE84B62029209`
- raw LOGIN: `FC1A4E60D11C71DBAE98763F970F1496F4E63EB575F3333FC2FDD6FE7BF1D557`
- server console: `77C7D3B7EC9F8C7F57DC660C82579DC95790BC0CCF75F4801A8D702566F7782A`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified backup:

`backups/v129_quest3020_accept_travel_negative_20260815_001754/`

Its manifest covers all six flushed capture artifacts plus source, launcher,
and package: nine entries with zero mismatches. The final report, `handoff.txt`,
and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`68B9EC4EDC75D2E0836B09422EF6CB6D4BEA3C40DB1618F2C4A250118BF3C320`

## Disposition

Promote V129 to the current verified evidence checkpoint for the exact quest
3020 operation-2/action-1 client-accept sequence. Preserve the travel outcome
as a resolved negative boundary: action 1 caused neither a travel request nor a
visual teleport because the current client's Lua native is a no-op, and no
TeleportCheck arrived. Do not continue this script-teleport lane unless a
different authentic non-stub implementation is recovered.
