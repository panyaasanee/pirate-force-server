# Pirate Force RE checkpoint — V135 q3020 conversation handshake pass

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V135 derives from frozen V134 and changes only the local StartGame visual
harness.  The decompressed StartGame response changes two bytes in the player Y
float, from `-2780.045166` to `-2830.045166`.  P0 remains at its exact decoded
placement, so it begins at relative `(+100,+50,0)`, 26.565 degrees off the
heading-zero center line.  Initial P0/P30/P91 population, stable zero-target
Teleport, conversation/action wires, inventory, cash, appearance, and all
server-side gameplay semantics are inherited.

## Exact live result

The client entered Port Royal normally.  Initial isolated population was sent
at `04:34:14.830` and reapplied at `04:34:17.830`.

At `04:34:31.454`, one click on P0 produced an exact RuntimeReq version 0,
mask `0x02`, two-vital frame containing:

- `TargetVital 0x1ADD` version 0, actor `0x2001`, kind 2;
- embedded `ChooseNPC 0x0FB6` version 0, actor `0x2001`.

The server returned the safe full facing snapshot and exactly one 39-byte
`NPCConversation 0x31D8` version 0 containing actor `0x2001`, one descriptor,
quest 3020, and constructor-default descriptor byte zero.  The client rendered
the q3020 conversation UI successfully.

At `04:35:01.301`, the UI emitted the exact 43-byte QuestOperate request:

`quest=3020, operation(+0x16)=1, +0x17=0, dword=0, qword=0, +0x28=0`.

The server's ordered state gate accepted it only after the P0 conversation and
sent the exact 45-byte action-6 `OpenAcceptUI_Run` response once.

At `04:35:11.479`, the accept UI emitted the exact 43-byte operation-2 request:

`quest=3020, operation(+0x16)=2, +0x17=0, dword=0, qword=0, +0x28=0`.

The server accepted it only after action 6 and sent the exact 45-byte action-1
accept-success response once.  The client accepted the response and remained
healthy.  This completes the live chain:

`P0 ChooseNPC -> NPCConversation(q3020) -> op1 -> action6 -> op2 -> action1`.

The post-action request journal later recorded only
`UserSetting_UpdateServerSettingVital 0x0F01`; its causal relationship is
unassigned and it received no V135-specific response.

## Health and proof boundary

The session completed 101 runtime heartbeats.  Heartbeats 49 through 101 give
53 successful heartbeats after action 1; the final heartbeat at `04:36:57.661`
is 106.175 seconds after the response.  The final raw state is:

- `quest_conversation=True`;
- `quest_accept_ui=True`;
- `quest_accept_success=True`;
- `quest_op1_count=1`;
- `quest_op2_count=1`;
- `quest_capture_count=2`;
- last tuple `(3020,2,0,0,0,0)`.

Across all six flushed capture files there are zero ErrorData, version
mismatch, `28317`, traceback, fatal, SEND_FAILED, or disconnect markers.
Server stderr is empty.

V135 proves the complete client-local q3020 conversation/accept handshake and
the exact request/response ordering.  It does not prove server QuestAttr
persistence, rewards, progress, completion, travel, vehicle state, or the
authentic original-server quest database transaction.  Do not fabricate those
states.  Replays and wrong order/tuple/envelope remain strict no-reply paths.

## Build and artifact verification

V135 passed the complete inherited self-test, Snappy roundtrip, exact
V134-to-V135 two-byte StartGame comparison, ZIP integrity, and embedded-hash
verification:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v135.py`, 294,768 bytes  
  `62B85E1B0FD2CAC8429A57C67192F8F93A0A6DD3FB66D90E478DD08A3396830E`
- `run_v135_port_royal_p0_q3020_lateral_view.bat`, 469 bytes  
  `08FFD90DA85BBC87620A1CB2EA7E1455178C40FA05009F2CA377E61593424C75`

Package: `packages/PF_Login_Game_Test_v135.zip`, 4,370,693 bytes  
SHA-256: `0FE4C5E775C847D3294046168DEAFF84AA36FC884582B5629CE526CC5BB5DB62`

Flushed capture hashes:

- raw GAME: `91509F4ED3784969B675A49A742C47F1AD6E7AD48397C77374C7BE590E12DD13`
- event journal: `C3E90DD993C90E1496C2B5F52BF9EB9E04812B42A29B334FBEC1380DB506017B`
- live GAME: `A836FB65FE180B96EFB29FDC55D83D084E4B05EEFA0692CED35F2D5BD8835EBE`
- raw LOGIN: `3AA2A3B0CF601FB6504F8F441CFFE8D2DF4866EDDEF4D4CB2CC718AD31F39866`
- server console: `3B2BFE5041DD15811277AA40BA1416C8BE55C4F212A44BB5A4F2B8701E07286A`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified passing checkpoint backup:

`backups/v135_q3020_conversation_handshake_20260815_044150/`

V135 is now the current passing baseline.  GameClient runtime files remain in
place; no references or evidence files were modified.
