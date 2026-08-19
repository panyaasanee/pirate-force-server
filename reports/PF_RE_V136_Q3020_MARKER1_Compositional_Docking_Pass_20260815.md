# Pirate Force RE checkpoint — V136 q3020 → MARKER1 compositional docking pass

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V136 derives from the complete V135 q3020 conversation/accept pass and preserves
its visual harness, bootstrap, P0/P30/P91 population, safe facing, inventory,
cash, and exact conversation/op1/action6/op2/action1 packets.  Its only new
runtime behavior is a bounded composition of two independently proven client
boundaries.

After exact q3020 operation 2 queues the unchanged action-1 accept-success
response, V136 arms one pending flag.  The first byte-exact 12-byte empty
RuntimeReq version 0/mask 0/count 0 that follows sends the independently
V131-proven MARKER row-1 Port Royal docking prompt once:

`126F6E140000000008000B00`

Prompt wire, exact 25-byte RuntimeRes version 4 with trailing mask:

`129D6E140000000008040B021201001277440B000F01000B00`

The exact 23-byte positive-confirm request is captured once and receives no
reply:

`126F6E140000000008000B021201001277440B000F0100`

## Exact live result

The client entered Port Royal normally and received the exact V135 population.
At `05:08:47.606`, clicking P0 emitted TargetVital actor `0x2001`, kind 2,
with embedded ChooseNPC `0x2001`; the q3020 conversation rendered normally.

At `05:09:01.864`, the UI emitted exact QuestOperate tuple
`(3020,1,0,0,0,0)` and V136 returned action 6 once.  At `05:09:13.799`, the UI
emitted exact tuple `(3020,2,0,0,0,0)`; V136 queued the unchanged action-1
response at `05:09:13.804` and armed the compositional pending flag.

The next exact empty RuntimeReq arrived immediately.  At `05:09:14.217` the
state gate queued the MARKER1 docking prompt, and the exact 25-byte prompt was
sent at `05:09:14.219`.  This was 0.415 seconds after action 1.

After one positive UI confirmation, frame 64 at `05:09:28.137` carried exact
TeleportCheckVital `0x4477`, nested version 0, value 1, singleton count, and no
trailing bytes.  The event journal recorded the one-shot milestone at
`05:09:28.142`.  V136 sent no response or mutation.

Final state proves the complete tested sequence:

- q3020 conversation sent: true;
- action-6 accept UI sent: true;
- action-1 accept success sent: true;
- compositional pending: false;
- MARKER1 prompt sent: true;
- MARKER1 confirm capture count: 1;
- confirmed value: 1.

The only later non-empty request was closure-time
`UserSetting_UpdateServerSettingVital 0x0F01`; its causal linkage is unassigned.

## Health and proof boundary

The session completed 119 runtime heartbeats.  Heartbeats 55 through 119 give
65 successful heartbeats after the positive confirmation.  The final heartbeat
at `05:11:38.392` is 130.250 seconds after capture.

Across all six flushed capture files there are zero ErrorData, version
mismatch, `28317`, traceback, fatal, SEND_FAILED, or disconnect markers.
Server stderr is empty.

V136 proves that this exact server-side composition is accepted by the client:

`q3020 action1 -> next exact empty RuntimeReq -> MARKER1 prompt -> positive
TeleportCheck request`.

It does not prove that the original server connected q3020 `Var2=1` to MARKER1
in this way.  It also does not prove travel, vehicle state, quest completion,
QuestAttr persistence, destination direction, rewards, progress, or the server
response to the confirmation.  Do not fabricate those states.  Pre-sequence,
wrong envelope/value/version/count, trailing, and replay paths remain strict
no-reply/no-advance boundaries.

## Build and artifact verification

The independent pre-runtime audit passed full self-test, Snappy roundtrip,
V135 byte-preservation comparisons, ZIP integrity, and embedded hashes:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v136.py`, 307,342 bytes  
  `57AA263367B471A4A48A1854E8159EEE71E26001AE01B1FABD41BB444829F7D4`
- `run_v136_port_royal_q3020_marker1_composition.bat`, 474 bytes  
  `C2976873CBE39ADAF012EB338BE47FCF2581106DEDEA70A183AE89658C13851A`

Package: `packages/PF_Login_Game_Test_v136.zip`, 4,373,032 bytes  
SHA-256: `92ACDA5A642F275790CB333DE276B23620B477D881E8E50079F29F334B266797`

Flushed capture hashes:

- raw GAME: `306D0016B81896AC0993D222AE8626B025F6697F28401BACCEBCEDA9EC15AF81`
- event journal: `F2462F75F84CEB5714C7DDCE44373B26D3E11D59BFF5A5916C671D836E5CED49`
- live GAME: `D992347257C7A52A8F950D7F61FD0D703ABC2B2DD1C31930FA9A46ECA6DB5FA9`
- raw LOGIN: `62410B13BE00D6A139BA15EA30ABC766E49573255EDCDAB3CF594E271B7DD31A`
- server console: `BC9AEDA4F570F82A5787CC6788AEEB61176F27160200062B3DDD69B4396541A4`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified passing checkpoint backup:

`backups/v136_q3020_marker1_composition_20260815_051330/`

V136 is now the current passing baseline.  GameClient files remain in place;
no references or evidence files were modified.
