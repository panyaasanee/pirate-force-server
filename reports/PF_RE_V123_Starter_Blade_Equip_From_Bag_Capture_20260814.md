# Pirate Force RE checkpoint — V123 starter blade and equip-from-bag request

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

This checkpoint continues
`PF_RE_V121_to_V122_Final_Buy_Cash_Update_20260814.md`. It adds one complete,
data-backed starter weapon to the initial Backpack and captures the exact
client request produced when that item reaches the equip-from-bag activation
path. It does not claim that the blade was equipped, because V123 deliberately
sends no ItemOperate response or inventory/equipment mutation.

## Four-item initial Backpack

V123 starts from frozen V122. Its only initial-state addition is:

- server item identity: 4;
- global template: 2200002;
- decoded client row: `EQUIPMENT_BASE` row 2, Create Character Blade;
- quantity: 1;
- Backpack slot: 3;
- ItemAttr `+0x38=0`, `+0x39=0xFF`;
- no nested detail.

The previous three identities, items, quantities, and slots remain unchanged.
Both ItemBag collections contain four entries and identities 1, 2, 3, and 4.
The final Backpack base-range flag remains `0B 01`, so the predicted capacity is
`40 - 4 = 36` free base slots. The exact new 26-byte ItemAttr is:

`32 04 00 00 00 00 00 00 00 14 C2 91 21 00 0F 01 00 0F 03 00 08 00 08 FF 0B 00`

The complete V123 Backpack is exactly the V122 Backpack plus that 26-byte
ItemAttr and one 9-byte qword identity entry: a 35-byte increase with the old
three ItemAttrs byte-identical. The flushed runtime StartGameRes records this
exact full snapshot.

`+0x39=0xFF` is intentional. It is the constructor-default unequipped state,
not a guessed equipment-slot assignment. Static audit proved that the separate
operation-6/current-equipped lookup cannot select this item while that byte is
`0xFF`; V123 therefore makes no operation-6 claim.

## Exact equip-from-bag producer

The final corrected static call chain is:

1. Item activation handler `0x5771E2` requires event payload `+8 == 2` and
   passes the selected item control's `+0x94` value to `0x5A64A0`.
2. The equipment path reads decoded `n_EQUIPSLOT` through string address
   `0xF0EC7C`. Create Character Blade row 2 supplies exact value `0x4000`.
3. `0x5A6814..0x5A683F` maps that row value to request dword 8 by default, or
   16 when `0x448EC0(0x10)` selects the alternate branch.
4. `0x5A6879` calls `0x4DF1C0` on the selected ItemAttr and obtains its qword
   identity; `0x5A6884` calls producer `0x59F800`.
5. `0x59F800` emits ItemOperate operation 5, writes the mapped value to request
   `+0x18`, and writes the selected ItemAttr identity to `+0x20/+0x24`.

The static code proves only the label **item activation event code 2**. It does
not by itself prove a raw mouse-button enum. Earlier controlled V109/V110
runtime evidence made right-click the strongest operational first action, but
that historical observation is kept separate from the static event label.

## Exact V123 request gate

V123 recognizes only:

- GSCN Runtime request;
- nested ItemOperateVitalReq `0x4BED` version 0;
- exactly one vital;
- operation 5;
- identity qword 4;
- mapped dword 8 or 16.

It journals the chosen mapped value and sends no response or mutation. The
self-test covers exact 36-byte request fixtures for both 8 and 16, plus
wrong-version, wrong-count, raw `0x4000`, wrong-identity, wrong-operation, and
trailing-field no-reply cases.

## Runtime result

The deployed V123 run passed its complete boundary:

1. Login, character selection, StartGame, Port Royal runtime readiness, PIN
   unlock, and all preserved bootstrap behavior completed normally.
2. The client accepted the four-item Backpack sufficiently to activate the
   newly supplied identity 4. This is machine-backed by the request identity,
   not an inference from icon placement alone.
3. At `2026-08-14T21:37:35.780`, inbound frame 84 contained exactly one
   ItemOperateVitalReq version 0/count 1.
4. The nested request was operation 5, mapped dword 8, identity 4. The exact
   36-byte decompressed request was:

   `12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 ED 4B 0B 00 0B 05 14 08 00 00 00 32 04 00 00 00 00 00 00 00`

5. The corresponding framed request had magic `0x5F253EAC`, compressed length
   38, and total frame length 46.
6. V123 recorded
   `V123_EQUIP_FROM_BAG_REQUEST_CAPTURED_NO_REPLY`, capture count 1, and sent
   no ItemOperate response.
7. Heartbeat 68 preceded the request. Heartbeats 69 through 235 continued
   afterward: 167 successful heartbeat responses after the no-reply capture.
   The clean final state reached inbound frame 251 with the captured values
   still `value32=8`, identity 4.
8. The game and server closed cleanly. The raw GAME log flushed to 189,880
   bytes and the raw LOGIN log to 2,326 bytes.
9. Raw GAME, live GAME, live event journal, and server stderr contain zero match
   for `ErrorData`, version mismatch, fatal, exception, traceback, disconnect,
   `28317`, or `SEND_FAILED`. Server stderr is empty.

Runtime proved the default mapped value 8. Value 16 remains a statically proven
producer branch and self-tested accepted boundary, not a value observed in this
run.

## What V123 does not prove

V123 does not prove or implement:

- the successful ItemOperate response body or response ordering;
- equipped-state transport or the authentic new `+0x39` value;
- AvatarAttr/equipment-model mutation;
- Backpack removal or slot mutation after equip;
- operation-6 unequip response semantics;
- whether activation event code 2 corresponds to one universal mouse gesture;
- the alternate mapped value 16 at runtime.

Do not turn any of those boundaries into a server response without new static
or captured evidence.

## Build and artifact verification

Before deployment, V123 passed `py_compile`, the complete inherited self-test,
exact ItemAttr/Backpack/StartGame reconstruction, both exact op5 fixtures,
negative no-reply tests, Snappy roundtrip, ZIP integrity, exact-three-entry ZIP
verification, and embedded-file hash comparison.

Current artifacts and SHA-256:

- `current/pf_login_game_server_v123.py`  
  `099F902E6529F92B45CCCF5FF0882FB9CC774F56EADE180D5BB269C6C27751E9`
- `current/run_v123_port_royal_equipment_request_capture.bat`  
  `9A12A5EFFBFB17E93B9952BE8725310E2B8D98811E8B011989794838CBDAFBDE`
- `packages/PF_Login_Game_Test_v123.zip`  
  `05CB5A05A5D8205B04D8794376C5EDAA051BA8933605D03067F549EFF8046A14`
- raw GAME  
  `8B3535453EEAD4B084958C8466A88FBFC5FCBC7E506F37EF98110F251F5C0ABC`
- live event journal  
  `9050B1D9A179E3AA1096151252E3D1C7688D06602130CBA62C88AA5373541092`
- live GAME sidecar  
  `8C8E2EE44855BED0A77D0BC6979C9119771DFE4740368067EEFC93CB533BF7AC`
- raw LOGIN  
  `064D04008DEC70A2B6CE58AB87B08DB4EC53CFA4C80DB13FACD2E862F710D3B0`
- server console  
  `25D7BDC91F42D57A477DD0C29375C34F609A84781196072525852129A2ACAEFF`

Verified backup:

`backups/v123_starter_blade_op5_capture_20260814_214616/`

The backup manifest covers the runtime capture, source, launcher, and package
entries with zero mismatches. This report, the live handoff, and AGENTS.md are
preserved beside the manifest. Manifest SHA-256:

`B24512B4E48FBD6C3C211BEC937D53B9767B3B1A420F0971719264B29C11D353`

## Next evidence boundary

The strongest next equipment milestone is a static recovery of the registered
ItemOperate operation-5 success response and its exact effects on both
BackpackAttr and equipped/avatar state. A response build remains blocked until
those transports and all required fields are proven together. Capture-only
experiments may continue without assigning unknown result or equipment fields.
