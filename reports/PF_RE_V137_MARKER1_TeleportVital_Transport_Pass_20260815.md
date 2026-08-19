# Pirate Force RE checkpoint — V137 MARKER1 TeleportVital transport pass

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V137 derives from the passing V136 q3020/MARKER1 composition and preserves its
complete bootstrap, P0/P30/P91 population, conversation, operation-1/action-6,
operation-2/action-1, and docking-confirm sequence.  Its only new runtime action
occurs after the exact V136 positive confirmation: it sends one standalone
RuntimeRes version 4 containing one TeleportVital version 4 whose target is the
decoded MARKER row 1.

Exact 64-byte protocol content:

`129D6E140000000008040B0212010012A2250B040B020B011201003200000000000000000B000B002A004821C62A00C03CC42A00C027440B000B000F00000B00`

The decoded fields are scene 1, scene sequence 0, and XYZ
`(-10322,-755,671)`. Both target bytes and the final u16 remain constructor
zero. MARKER direction 3 is deliberately not assigned to either unknown field.
RuntimeRes retains the required trailing derived mask `0B00`.

The uncompressed protocol content is 64 bytes, SHA-256
`9860A1145E4448A47B50EB817F6FFCD97B9F0723E079EE25B840DC766E34FD08`.
Its exact 75-byte Snappy frame is SHA-256
`8FF158EE379DCFFAD8AB2BDCD115387BADA245951F20DA1B3444AC508A17841D`.

## Two-session runtime record

`capture_v137` contains two complete raw GAME/LOGIN attempts and cumulative live
sidecars. Attempt 1 started at `05:24:12.184`, completed the q3020 action chain,
and sent the MARKER1 prompt. A PrintScreen overlay followed by Escape canceled
the docking prompt, so no positive confirmation and no V137 transport send
occurred. It completed 106 heartbeats. This is an operationally canceled attempt,
not a negative result for the V137 packet.

The passing attempt is raw GAME
`GAME_20260815_052956_222262_59254.txt` with LOGIN
`LOGIN_20260815_052915_585307_59238.txt`. Its exact sequence was:

- runtime ready at `05:31:13.881`;
- P0 TargetVital kind 2 plus embedded ChooseNPC at `05:31:57.320`;
- exact q3020 operation 1 at `05:32:13.283`, followed by unchanged action 6;
- exact q3020 operation 2/action 1 at `05:32:29.309`;
- MARKER1 prompt queued at `05:32:29.697`;
- exact positive TeleportCheck value-1 confirmation at `05:32:57.512`;
- V137 one-shot transport queued at `05:32:57.521` and exact 75-byte frame sent
  at `05:32:57.526`.

The final state recorded positive-confirm count 1 and V137 send count 1. The
strict gate sets the one-shot state before queueing. Pre-sequence, malformed,
wrong-envelope/version/count/value/trailing, and replay variants remain no-send.

## Post-init transition and position ownership

The same GAME connection remained alive. At `05:33:17.575`, frame 84 was a
three-vital ready/transition batch containing target clear, TeleportVital, and
TargetPosVital. The embedded position bytes were the exact marker floats:

`2A004821C62A00C03CC42A00C02744`

The visible client reloaded the game scene and its coordinate UI reported
`X:-10,322 Y:-755`.

At `05:34:09.679`, one short W press emitted a singleton TargetPosVital with
the exact payload:

`2A004821C62A00C03CC42A00C027442A000000000B010B00`

Its first vec3 is exactly `(-10322,-755,671)`. This machine-captured client
request decisively proves that a post-init server TeleportVital owns the local
player position and performs the accepted transition for this client. It is
stronger than a visual-only coordinate observation.

## Health and proof boundary

The passing session completed 127 heartbeats and ended at raw frame 136. There
were 62 heartbeats and 53 received frames after the single V137 send. The final
heartbeat at `05:35:01.783` was 124.257 seconds after the transport frame.
Across both attempts, the flushed capture has zero ErrorData, version mismatch,
`28317`, traceback, fatal, SEND_FAILED, or disconnect markers; server stderr is
empty.

V137 proves these bounded facts:

- RuntimeRes v4 can carry a singleton TeleportVital v4 after world init;
- the exact MARKER1 scene/sequence/XYZ target is accepted;
- the client performs a same-connection transition and owns the marker position;
- the one-shot sequence remains healthy afterward.

It remains an emulator-side composition. It does not prove that the original
server used this exact q3020/MARKER1 ordering or this exact response packet. It
does not establish quest completion, QuestAttr persistence, rewards, vehicle
state, original-server destination policy, or direction-field semantics.

## Build and artifact verification

Independent pre-runtime verification passed `py_compile`, full self-test,
Snappy roundtrip, V136 packet-preservation comparisons, ZIP CRC/integrity, exact
three-root-entry count, and embedded/current hashes:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v137.py`, 316,357 bytes  
  `2944C4B6BE8E8DC32638853174F1D8A8A88E04CEC2637CE0F1A9165E2C02A21C`
- `run_v137_port_royal_marker1_transport_probe.bat`, 476 bytes  
  `8BFF492FFFD75ED8BBCAAAE58A1A324DA5733F23C6CC8AC100B87D18183C26EA`

Package: `packages/PF_Login_Game_Test_v137.zip`, 4,374,881 bytes  
SHA-256: `DCF6AAEB1B6E14300C171F40548B3352A46F7A749E568A7035348C0719FFF74B`

Flushed runtime capture hashes:

- attempt-1 raw GAME: `DCC9ED933117842B9A1E65580F07D4074167A60F9D1356D3EC677410E7DA1ED1`
- attempt-2 passing raw GAME: `E28A1454800214E213547D3A7D5588DCDA4337E7A01E1FA14519648A25DC5DEE`
- cumulative event journal: `86A5187E521649BB76BE296D88DA15B0F81B8A26E246ED7F3A1EB2C82921B037`
- cumulative live GAME: `7E0D45F6C59166697891167F662CF19353E6E308838BDF132935387E15FC646D`
- attempt-1 raw LOGIN: `30DEE08874C6722177DC212F97401A7FCB7D43FC87330533D1BB869488D6105F`
- attempt-2 raw LOGIN: `2020730C684B06E7F1A8DF0EDCE33118306E103A36D8D644E0996D76AD68BE59`
- server console: `709FD6AAAAAC524B745D2F43D4CF42E46B73A809701FD8EF4F4BFDE97681D272`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

V137 is the current passing evidence checkpoint. GameClient files remain in
place; no cleanup was performed and no `references/` or `evidence/` file was
modified.

Verified passing checkpoint backup:

`backups/v137_marker1_teleport_transport_20260815_054009/`
