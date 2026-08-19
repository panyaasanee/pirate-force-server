# Pirate Force RE checkpoint — V140 P86 synthetic-harness interaction pass

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V140 derives from the frozen V139 interaction boundary. V139's protocol and
serializer design were statically valid but operationally unreachable because
authentic P86 was behind-left of MARKER1 and the available Computer Use backend
could not perform a genuine right-mouse-button hold drag. V140 changes only an
explicit visual test harness: in the destination population and later safe-face
snapshot, P86 MovementAttr XYZ is replaced with MARKER1 `+100X,+50Y` at marker
Z, or `(-10222,-705,671)`.

This is a synthetic emulator-side test position. It is not an authentic P86
placement, decoded-ground coordinate, original-server population choice, or
permission to substitute synthetic positions in production population data.

## Exact build boundary

The frozen V138 destination population remains available byte-for-byte. The
V140 population changes only nine P86 XYZ float-value bytes at offsets
`[128,129,130,133,134,135,138,139,140]` from the 3,152-byte V138 protocol
content. Its exact hashes are:

- V140 population PC, 3,152 bytes:  
  `0DB101113B5317822657CA965B1EBC50E239F9A423CF4CA307CA8B6006D1A188`
- V140 population Snappy frame, 3,165 bytes:  
  `21F27276C9646EE961E68862041A1FD7F3F623AF36BD2402D8A3492F68FFA58E`

The frozen V139 face packet also remains available byte-for-byte. V140's face
packet differs only at twelve P86 XYZ/derived-heading float-value bytes at
offsets `[128,129,130,133,134,135,138,139,140,143,144,145]`:

- V140 face PC, 2,028 bytes:  
  `B8F0B7E54B2A317109C174BBC31DD7EABC647EDE14E41874D12900EA1C983439`
- V140 face Snappy frame, 2,041 bytes:  
  `6A682109699F6BD769F6A73B2C891BE43ED7534DFB7B64C93A9B371F0E2A4E89`

Both V140 packets retain all 20 NPCAttr records. P30 remains byte-exact at HP
`3857/3857` with BasicAttr name `Tornado Eagle`. The population has 20 complete
MovementAttr records; the interaction snapshot has exactly one MovementAttr
mask `0x03`, on P86, at the same synthetic harness XYZ. Login, select,
game-login ACK, StartGame, V137 transport, frozen V138/V139 fixtures, exact
gates, one-shot behavior, and the empty P86 conversation are unchanged.

## Exact live sequence

The single flushed session completed the entire preserved prerequisite chain:

- runtime first-request ACK at `06:43:08.016`;
- P0 TargetVital kind 2 plus embedded ChooseNPC at `06:43:54.099`;
- exact q3020 operation 1 at `06:44:10.107`, followed by action 6;
- exact q3020 operation 2 at `06:44:24.201`, followed by action 1;
- compositional MARKER1 prompt queued at `06:44:24.637`;
- exact positive TeleportCheck value 1 at `06:44:38.397`;
- V137 transport queued once at `06:44:38.404`;
- exact post-transition ready batch, event seq 6/frame 72, at
  `06:44:56.858`;
- V140 nearest-20 population queued at `06:44:56.861` and sent once at
  `06:44:56.862`, late by only 0.1 ms;
- exact singleton MARKER1 TargetPos, event seq 7/frame 80, at
  `06:45:10.562`, arming the P86 interaction once at `06:45:10.566`;
- exact TargetVital actor `0x2057`, kind 2, followed by embedded ChooseNPC for
  the same identity, event seq 8/frame 94, at `06:45:38.504`;
- V140 full-20 safe-face and unchanged empty conversation queued at
  `06:45:38.509` and sent once at `06:45:38.514` / `06:45:38.529`.

The accepted request protocol content is 45 bytes and includes the exact body:

`325720000000000000080212B60F0B00325720000000000000`

This is TargetVital version 0 for identity `0x2057`, kind 2, with one embedded
ChooseNPC version 0 for identity `0x2057`. The strict V139/V140 walker accepted
this already-observed shape and did not need a guessed field or relaxed parser.

## Visible result

The client displayed P86's overhead title `Vagabond Messenger`. The default
conversation opened with dialog/person name `Mori Hiroko` and the expected
local Thai default chat. This is consistent with the already-proven V97 rule:
the overhead role title and dialog/person name are two fields from the same
client template, not an actor mismatch. The server still sent an empty,
serializer-exact NPCConversation; the visible name/text came from client data.

This runtime therefore proves the complete V139 interaction transport boundary
when the target is operationally selectable: exact P86 Target+Choose parsing,
one P30-preserving full-20 safe-facing snapshot, the unchanged empty
NPCConversation, and successful client UI rendering. It does not prove the
synthetic P86 position is authentic, that the original server used this
population/timing/order, or that conversation state, quests, shops, combat,
rewards, persistence, vehicle state, or travel completion exist.

## Health

The session completed 153 heartbeats and ended at raw frame 162. After the V140
face/conversation send, 67 heartbeats and 68 received frames continued. The
final heartbeat at `06:47:53.324` was 134.810 seconds after the face send.

Across all six flushed capture artifacts there are zero ErrorData, version
mismatch, `28317`, traceback, exception, fatal, SEND_FAILED, or disconnect
markers. Server stderr is empty. The only later significant close-time request
was the existing UserSetting update; it did not repeat the V140 interaction.

## Build and artifact verification

Post-runtime verification reran `py_compile`, the full self-test, Snappy
roundtrips, exact V138/V139 regression fixtures, the V140 byte-difference
assertions, strict interaction negatives/replay tests, and ZIP integrity. The
ZIP has exactly three root entries and every embedded file matches current
byte-for-byte:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v140.py`, 362,282 bytes  
  `595DFECD4F08E49CAEFF60963E20FBB482FFC73D621DCC454CC31A3912189D9C`
- `run_v140_port_royal_p86_harness.bat`, 469 bytes  
  `AC204FCCFF6F42B6C323002D7E35388BE9EC0103291D4FE1C840F1D4A59987CE`

Package: `packages/PF_Login_Game_Test_v140.zip`, 4,384,420 bytes  
SHA-256: `4E199F2ADCF9325B949A82CC3C5B30F98D8EB29089D030575C4F98A7D56D0FF7`

Flushed runtime capture hashes:

- raw GAME: `2C27E2F096D5978827C9A46FD479037932B8E83E01797A9D7BDC2059255AF043`
- event journal: `12DFFA7DDE9624E2C609810EF9D28B07F034D7C58654E116A5676967D89B3DC1`
- live GAME: `400F505CE74FD1B91A084A2E9A49B9F273B3014BF1141573F7DECDF9E2359DFF`
- raw LOGIN: `FC50A01D0BE1E3BD1F1D7CAF0AA8DBFA5A9E76504EF1A22CE2BB784E71DC7ADF`
- server console: `841B49D7BC232F7683064A895766ADCEFD2A7D7CE034D4EB7860377C113FF806`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

V140 is the current passing evidence checkpoint, with its synthetic-position
caveat carried forward. GameClient files remain in place; no cleanup was
performed and no `references/` or `evidence/` file was modified.

Verified passing checkpoint backup:

`backups/v140_p86_synthetic_harness_interaction_20260815_065019/`
