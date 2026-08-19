# Pirate Force RE checkpoint — V130 equipped-blade negative boundary

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V130 derives from frozen V129 and changes only identity 4, the data-backed
Create Character Blade template `2200002`, inside the full initial
`BackpackAttr`. It changes the signed ItemAttr slot from the V123-proven bag
slot 3 to `-1` and changes byte `+0x39` from `0xFF` to the statically mapped
right-hand-one equipment index 3. It also retains a capture-only gate for the
predicted current-equipped ItemOperate request: version 0, operation 6, dword
8, identity 4. No response or mutation is sent.

The live result is a clean negative boundary. The Backpack showed `3 / 40`,
the blade was absent from the Backpack, `Character / ITEM_RH_ONE` was empty,
and controlled right-click plus left double-click produced zero operation-6
request. The session remained healthy for 252 heartbeats. Static re-audit now
explains the result exactly: V130 omitted both state transports required by the
client's current-equipped producer.

## Runtime result

The user observed all of the following in the same clean V130 session:

- the unlocked Backpack displayed `3 / 40`, not four items;
- identity 4 / Create Character Blade was absent from its old slot;
- the Character window's `ITEM_RH_ONE` control was empty;
- right-clicking that empty equipment control emitted no ItemOperate request;
- left double-clicking it also emitted no ItemOperate request.

The live and flushed logs agree with the observation:

- `ItemOperateVitalReq 0x4BED`: zero;
- V130 operation-6 milestone: zero;
- event journal entries: only the normal bootstrap `TeleportVital` and the
  controlled `CheckSecondPwdVital` submission;
- final successful heartbeat: sequence 252;
- final received game frame: 274;
- the only late non-empty request was normal closure-time
  `UserSetting_UpdateServerSettingVital 0x0F01` at frame 266;
- zero match for `ErrorData`, VitalData mismatch, read failure, fatal,
  exception, traceback, disconnect, `28317`, or `SEND_FAILED`;
- server stderr is empty.

Timing from the live sidecar:

- GAME session start: `00:27:07.276`;
- StartGameReq frame 31: `00:28:09.802`;
- StartGameRes sent: `00:28:09.907`;
- first RuntimeReq / bootstrap Teleport: `00:28:30.355`;
- second-password request: `00:31:08.855`;
- final game frame: `00:36:37.011`.

This runtime did not reject the V130 serializer or disconnect. It rejected the
state hypothesis semantically: the blade was neither in live inventory nor in
the equipment UI source.

## Exact Backpack rejection

`StartGameRes` handler `0x5DDAE0` first inserts all attributes into the player
attribute manager. It then looks up `BackpackAttr` and passes it to inventory
apply routine `0x5A2970`.

`0x5A2970` iterates every Backpack ItemAttr. At `0x5A2A01` it sign-extends
ItemAttr `+0x34`, pushes that signed slot, and calls `0x5A1240`. The insertion
routine performs:

- `0x5A124C`: `test eax,eax`;
- `0x5A124E`: jump to the return path when the slot is negative.

Therefore V130's wire slot `FFFF` is rejected before identity 4 can enter the
live inventory manager. This directly explains the visible `3 / 40` result.
Keeping identity 4 in both serialized Backpack collections does not override
the signed-slot gate.

## Proven inventory ranges

Static initializer code and initialized data prove the complete live inventory
range without using raw uninitialized globals:

- `0x102208C = 40`;
- `0x1022090 = 40`;
- `0x1022094 = 80`;
- `0x1022098 = 40`;
- `0x102209C = 30`.

Initializers `0xBEB3C0..0xBEB4DF` derive the consecutive ranges and total:
`40 + 40 + 80 + 40 + 30 = 230`, or slots `0..229`. They derive
`0x1080B74 = 230 - 30 = 200`. Equipment-aware routines `0x5A1630` and
`0x5A1780` iterate exactly `[0x1080B74, 0x1080B70)`, hence slots `200..229`,
and inspect ItemAttr `+0x39` to resolve the equipped mask/state.

This proves that `-1` is not an equipped inventory slot and that current
equipment lives in the final reserved range. It does **not** prove which exact
absolute slot inside `200..229` the original server allocates to this blade.
Do not choose 200, 203, or any other member until allocation evidence is
recovered.

## Separate CollectionBagAttr requirement

The Character equipment UI does not populate itself from `BackpackAttr`.
Refresh routine `0x583290` obtains the current player, adds `+0x130`, and at
`0x5832EA..0x583306` requests the literal type name `CollectionBagAttr` from
the player's attribute manager. The recovered protocol-name hash gives exact
ID:

`CollectionBagAttr = 0x3CD0`.

After type validation through `0x46AED0`, the refresh iterates that separate
ItemBag collection. For each non-`0xFF` ItemAttr `+0x39`, it computes
`1 << +0x39` and maps the resulting equipment mask to the ItemAttr identity.
V130 sent no `CollectionBagAttr`, so `ITEM_RH_ONE` had no identity to display.

The exact class construction/serialization boundary is also recovered:

- allocator/constructor path: `0x46B030` -> base `0x471970`;
- vtable: `0xF0EAF8`;
- serializer: vtable slot 13, `0x471830`;
- body: exact `ItemBagAttr` serializer `0x46F180`, followed by tagged u16
  object `+0x8A`;
- constructor default `+0x8A = 8`, serialized as `0F 08 00`.

This is sufficient to identify the missing attribute and its serializer, but
not sufficient to invent the server's absolute equipment-slot allocation.

## Why operation 6 needs both states

The current-equipped UI producer at `0x582730` proves the two-source
requirement:

1. `0x5827AF..0x5827CB` reads the equipment control's mask and resolves a qword
   identity from the map built by `CollectionBagAttr` refresh.
2. `0x582823..0x582829` passes that same qword to live inventory lookup
   `0x5A0120`.
3. Only when the item exists in both places does the event continue to
   producer `0x59F870`, which writes operation 6.

V130 supplied neither a valid live inventory entry (slot `-1` was rejected)
nor the required `CollectionBagAttr` mirror. Zero operation 6 is therefore the
expected deterministic result.

## Safe disposition and remaining blocker

Preserve V130 as a negative evidence checkpoint only. The latest passing
baseline remains V129. Do not promote V130 and do not repeat the slot-`-1`
initial-equipped hypothesis.

A future focused equipment build must, at minimum, carry the same identity in:

- a complete Backpack snapshot at a valid reserved equipment slot in
  `200..229`; and
- a separate serializer-exact `CollectionBagAttr 0x3CD0` entry with matching
  ItemAttr identity and equipment index.

The exact absolute slot within `200..229` and authentic server allocation
policy remain unresolved. Because choosing one would be guessing an ItemAttr
field, no V131 equipment build is authorized by this audit yet. Recover an
original packet, server-side allocation evidence, or another exact client
producer/handler relation before changing that field.

## Build and artifact verification

After runtime closure, V130 passed `py_compile` and the complete inherited
self-test. The ZIP opens successfully, contains exactly three entries, and
each entry is byte-identical to the current runtime artifact:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v130.py`, 288,758 bytes  
  `6161619FE0E7CCF6B56EAE9F4C13742B0407B9CE51B6C29ADA30B89A3680285E`
- `run_v130_port_royal_equipped_blade_op6_capture.bat`, 494 bytes  
  `B8A947440747491DCFDA9745FADEA8E70A44CFC9CB21891BD9EA374CFB59BDDF`

Exact-three-file package SHA-256:

`6DEA3EAFA75B5D08483299865FFBD8AB11326608D9916019BF2E7C96D53A15D9`

Flushed capture hashes:

- raw GAME: `1BE4214CAEE60B1EC85D26A1EDABB6ABAF5B32155B784639F2252C3E58DCB185`
- event journal: `74DEE52E90E13C51744029FEE0825FE561E438921A69D11C4CB4660AB9E0A1D7`
- live GAME: `8B0998EB62B3BA256BDC5E255FF9A69E8E07002F741BE4F51221FF3306FCF29E`
- raw LOGIN: `49F7B1BCE80CAD9B6458164E80490BC8B61F081E25E5E89F663D4F52EA822C2D`
- server console: `D6FB2FC34047F32CA76D97A19684FFCCB7395ED4720283B9AB9D0A49949C5BF6`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

Verified negative checkpoint backup:

`backups/v130_equipped_blade_negative_20260815_005123/`

Its manifest covers the six flushed capture artifacts plus source, launcher,
and package: nine entries with zero mismatches. The final report,
`handoff.txt`, and `AGENTS.md` are preserved beside it. Manifest SHA-256:

`ABC349CA9D10220BE99FFABFE431AD4E7262AA0A2CFDAFB11D47825F8C5EB8E7`
