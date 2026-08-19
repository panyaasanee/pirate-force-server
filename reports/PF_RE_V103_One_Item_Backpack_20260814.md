# Pirate Force RE — V103 One-Item Backpack Runtime

Date: 2026-08-14 (Asia/Bangkok)

## Result

V103 passed its focused runtime test. The client accepted a populated
BackpackAttr, unlocked it through the already-proven CheckSecondPwd response,
and displayed `1 / 40` with one key-shaped item icon in the first slot.
Runtime traffic remained healthy through heartbeat response 103 and the game
closed normally, flushing the full GAME and LOGIN logs.

This proves the recovered ItemAttr wire, first slot, item identity, and both
ItemBag containers are mutually consistent with this client. The Adventure Key
name comes from decoded client data for global template `2600001`; the runtime
test did not open a tooltip, so it does not separately claim a localized
tooltip observation.

## Focused delta from V102

All V102 login, StartGame, Teleport, population, movement, conversation,
message, music, heartbeat, and CheckSecondPwd behavior is preserved. The only
behavioral change is the BackpackAttr body in StartGameRes:

- global template: `2600001` (`STORE_NORMAL` row 1 -> `ITEM_MISC` row 1)
- server-local item sequence: `1`
- quantity: `1`
- signed bag slot: `0`
- ItemAttr `+0x38`: constructor default `0`
- ItemAttr `+0x39`: constructor default `0xFF`
- optional nested detail: absent
- second ItemBag identity container: one matching qword `1`

Nested ItemAttr wire, 26 bytes:

`32 01 00 00 00 00 00 00 00 14 41 AC 27 00 0F 01 00 0F 00 00 08 00 08 FF 0B 00`

Populated BackpackAttr body length: 54 bytes. ItemAttr is nested directly; no
incorrect `0x0ECD` class-ID prefix is emitted inside the collection.

## Verification

- `py -3 -m py_compile`: pass
- project self-test: pass
- exact ItemAttr and Backpack byte assertions: pass
- Snappy response-frame roundtrip: pass
- ZIP entry count and names: pass, exactly three root files
- runtime Backpack unlock: pass
- runtime visual state: `1 / 40`, item icon in slot 0
- CheckSecondPwd request/response: pass
- heartbeat continuity: pass through response 103
- clean game closure and log flush: pass
- final error scan (`28317`, fatal, traceback, disconnect, exception, error,
  assert): no matches

## Runtime evidence

Capture directory:

`C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_v103`

Important files:

- `GAME_20260814_102513_943326_56115.txt`
  SHA-256 `FA29C7F7928C95D9B2E0B88753D4DA1BE9FD57E8647A5CCF96435A42D3EA6994`
- `GAME_LIVE.txt`
  SHA-256 `DC9594744E337AB662A7055FFFBE222B419A19D567E9622617E7EAA37CA1FF72`
- `GAME_EVENTS_LIVE.txt`
  SHA-256 `BC0A341C2C0CEF12268493B7FC6107CEA0A396D41528AE0852676965270A4072`
- `LOGIN_20260814_102434_878796_49209.txt`
  SHA-256 `9759AB8E9F15A9FE3376036E098B37F23772FA3E69A8113BD30CF6549CC9B078`

At 10:27:33 the client sent CheckSecondPwdVital `0x4B98`; V103 replied in
0.3 ms with the exact 44-byte framed result-1 response. The Backpack then
opened with the populated state and heartbeats continued normally.

## Build artifacts

- server: `current/pf_login_game_server_v103.py`
  SHA-256 `2587E9120A2FCEC7BC7F1E9C2FA3718EA4C32B697A2164DD9C51830262DAF859`
- launcher: `current/run_v103_port_royal_one_item_backpack.bat`
  SHA-256 `E72118FAA902964E74AB6870B37DA5FF2BACE6908BE209E14C4CFBDC182EC5CE`
- package: `packages/PF_Login_Game_Test_v103.zip`
  SHA-256 `4AEC12B170D4AECC4399B12A4C48CE7CB555A53E9D5E25B1281BD6DC03C09B67`
- verified checkpoint backup:
  `backups/v103_one_item_backpack_20260814_103143`
- backup manifest: 120 entries, zero mismatches, manifest SHA-256
  `E915595C6641A1016E6D1A3C3678E0EB1124F91E5C4E9DC4EBAF2D74D007F7B5`

The package contains exactly:

1. `GameClient.local.bin`
2. `pf_login_game_server_v103.py`
3. `run_v103_port_royal_one_item_backpack.bat`

## Next evidence boundary

V103 proves initial inventory construction, not item mutation. Before testing
use, move, split, discard, buy, or sell operations, recover the exact client
request Vital and server response/mutation semantics for one operation. Do not
infer an operation from the icon or brute-force packet IDs.
