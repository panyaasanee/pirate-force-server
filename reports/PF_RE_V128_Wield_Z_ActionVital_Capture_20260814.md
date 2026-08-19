# Pirate Force RE checkpoint — V128 WIELD/Z ActionVital capture

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V128 preserves V127's verified quest operation-2/action-1 sequence,
deterministic P30 observation point, isolated P30/P91 population, inventory,
shop, cash, and stable bootstrap bytes. It corrects only the disproved G-key
wording and tests the exact producer recovered from current-client HOTKEY data
and dispatcher code. Runtime passed: selecting P30 and pressing Z emitted the
predicted target-bound `ActionVital 0x1AEA` version 0 with action `0xEA7E`.
The server captured it once and deliberately sent no reply.

## Exact input provenance

The earlier confusion came from two distinct numeric namespaces. Physical key
code 71 is G, but HOTKEY row ID 71 is not G:

- `B_CONSTDATA_TH` HOTKEY row 71: `s_NAME=WIELD`, `n_KEY_2=90`.
- `B_TEXTDATA_TH` HOTKEY_TIP row 71: `เก็บอาวุธ`.
- `B_TEXTDATA_TH` KEY_TIP row 90: `Z`.
- Physical G resolves to HOTKEY row 79 `GUILD`, which explains V127's local
  Guild modal and zero ActionVital.

Input handler `0x450610` passes the raw keyboard event to resolver `0x5D0CD0`.
For keydown, `0x450B20-0x450B38` dispatches the normalized HOTKEY ID through
byte table `0x4519C4`; ID 71 selects class 11 and branch `0x451026`, which
calls producer `0x44BC70`.

Producer `0x44BC70` requires a live runtime, local actor/controller, and clear
blocking state bits `0x14`. Its online branch allocates ActionVital, sets action
`0xEA7E` at `0x44BD0C`, copies heading/XYZ and the controller target qwords,
then sends it through `0x5DD800` at `0x44BD72-0x44BD79`.

This proves only the client-data meaning WIELD/`เก็บอาวุธ`, described neutrally
as a wield/stow toggle. It is not evidence of attack, combat, damage, FightAttr,
AI, or skill behavior.

## Runtime ActionVital pass

At `2026-08-14T23:47:42.107`, significant event 3 / game frame 73 selected the
isolated P30 Tornado Eagle with exact TargetVital identity `0x201F`, kind 2,
and embedded ChooseNPC `0x201F`. This armed the single-use capture gate.

At `23:48:10.349`, significant event 4 / game frame 87, pressing Z produced
this exact 84-byte decompressed RuntimeReq:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 EA 1A 0B 00 32 00 00 00 00 00 00 00 00 32 00 00 00 00 00 00 00 00 32 1F 20 00 00 00 00 00 00 14 7E EA 00 00 19 00 00 00 00 2A 63 E6 A4 3F 2A C8 F0 E6 44 2A 95 ED F4 C5 2A 00 C0 68 44 0B 00 12 01 00 0B 00`

Decoded envelope and body:

- outer `GSCN_RunTimeProtocolReq 0x6E6F`, version 0, mask `0x02`;
- singleton `ActionVital 0x1AEA`, version 0, fixed 64-byte body;
- qwords `+0x18/+0x20/+0x28 = 0 / 0 / 0x201F`;
- action `+0x30 = 0xEA7E`;
- dword `+0x34 = 0`;
- heading `1.2882808446884155`;
- XYZ `(1847.5244140625, -7837.69775390625, 931.0)`;
- remaining audited values `+0x48/+0x4A/+0x4C = 0 / 1 / 0`;
- no trailing bytes.

The exact live milestone was:

`V128_TARGET_BOUND_WIELD_Z_ACTION_CAPTURED_NO_REPLY ... capture_count=1 semantic=wield_stow_toggle_not_attack_or_combat`

No response, actor mutation, combat interpretation, or new unknown field was
added. The result validates the real producer, the complete serializer shape,
the selected-target copy, and V128's capture gate.

## V127 quest regression pass

The inherited quest lane remained byte-exact. At `23:46:45.682`, frame 44,
the client sent the proven 43-byte quest-243 operation-2 request. V128 returned
the inherited 45-byte RuntimeRes v4 with one QuestOperateVital v3 action-1/P91
tuple and required trailing `0B 00`. The one-shot milestone remained:

`V127_QUEST_OPERATE_REQUEST_CAPTURED fields=(243, 2, 0, 0, 0, 0) capture_count=1 result=ACTION1_ACCEPT_SUCCESS_SENT_ONCE`

This remains a bounded client-local/session acceptance result only. It does not
prove QuestAttr persistence, progress, rewards, completion, quest 244, or
authentic P91 quest ownership.

## Runtime health

The cleanly closed session completed 155 successful heartbeats. Sequence 82
preceded the ActionVital; sequences 83 through 155 provide 73 successful
heartbeats after the capture milestone. The final game frame was 160 and the
final heartbeat was timestamped `23:50:37.027`.

The flushed capture has zero match for `ErrorData`, VitalData mismatch, read
failure, fatal, exception, traceback, disconnect, `28317`, or `SEND_FAILED`.
Server stderr is empty. The game, login client, and server were closed normally.

## Build and artifact verification

`py -3 -m py_compile` and the complete V128 self-test passed. Fourteen selected
V127/V128 deterministic packet fixtures were byte-identical, including login,
select, StartGame, Teleport, population, quest, inventory, shop, cash, music,
and ActionVital fixture paths. The ZIP passed integrity checks, contains exactly
three files, and every embedded byte matches the frozen source files:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v128.py`, 265,920 bytes  
  `CA8914120F30FC2256A557DCB81962290F24E42743662E5448FFBF70AA1ADB29`
- `run_v128_port_royal_quest_accept_p30_wield_capture.bat`, 475 bytes  
  `CB8EF46587ABD3CC07367695299EFB129659E7E5BF0F3784F6473BD81984371D`

Exact-three-file package SHA-256:

`10400E9D2AA7EE6F44B6BF0D9990DB02B4CF32C3DC9730A4954ABC2F7571366F`

Flushed capture hashes:

- raw GAME: `C34F7AE9AE3995058D635DFA7A290DBFDB185C111A6D7471CD932D0E699AA07B`
- event journal: `5B2886A84000E496D22FB434E27F6B8455E67DAAE3791591A268601D3CFCB25C`
- live GAME: `32C2548139E7ABD76650A977C81BBFEED3263A1FD41B227B819CD9626241364B`
- raw LOGIN: `9475E577CDEB14D95DC74B4CDB7543FA613402CE6A0EB3F4F223CC3C86B5472D`
- server console: `CCE7CCF5BDCB8380218D5D6F0843444A7337011915E9E01C878F8266638BF035`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified backup:

`backups/v128_wield_z_action_capture_20260814_235039/`

Its manifest covers all six flushed capture artifacts plus source, launcher,
and package: nine entries with zero mismatches. The final report, `handoff.txt`,
and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`820E83A1F846AE424CCF28C2EF3B447A36A681B37F9A0A617BDAEF6DA7B2EFB4`

## Disposition

Promote V128 to the current verified runtime checkpoint. Preserve Z as the
exact WIELD/`เก็บอาวุธ` producer for ActionVital `0xEA7E`; preserve G as the
separate Guild hotkey. Keep this milestone capture-only and no-reply. Do not
reinterpret it as attack/combat or invent ActionVital response, FightAttr,
damage, AI, or skill semantics.
