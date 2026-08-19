# Pirate Force V111-V115: inventory merge, monster boundary, and shop UI

Date: 2026-08-14  
Current verified runtime build: V115

## Result

V111 proved a persistent stack merge without guessing an unknown item field.
The Backpack began with Adventure Key identity 1 in slot 0, Camouflage
Item-Cask identity 2 in slot 1, and Adventure Key identity 3 in slot 2.  The
captured operation-4 request `(destination=0, source=3)` was answered with an
update for identity 1 at quantity 2 and a removal for identity 3.  The client
showed `2 / 40`, the key stack showed quantity 2, the cask remained, and later
moves preserved quantity 2.

V112-V114 established two independent boundaries.  P30/template 31 (`Tornado
Eagle`, actor identity `0x201F`) is a data-proven usage-1 monster at its exact
Port Royal placement.  P91/template 91 (`Local people`, identity `0x205C`) is a
nearby usage-2 control.  Both are streamed as actor type 4 with only proven
NPCAttr and initial MovementAttr; no FightAttr, ActionVital, AI, combat, or
unknown fields are emitted.  P30 receives no NPC conversation/facing response.

V112 also disproved that the target vec3 inside the existing login
TeleportVital positions the local avatar: TargetPos remained `(0,0,931)`.
V113 proved that the local StartGameRes MovementAttr does position the avatar.
V114 placed the avatar at P91+100X on the same Z and sent a delayed shop test
harness packet, but the client displayed a `TradeZoomVital` VitalData read
failure with decimal `ErrorData=10874`, exactly protocol ID `0x2A7A`.

Static re-audit found the exact V114 fault.  TradeZoomVital constructor
`0x664CA0` sets nested version 2, so version 2 was correct.  Serializer
`0x6652E0` handles the member at `+0x24` through helper `0x89A810`; that helper
doubles the character count and emits tag `0x48`, proving a UTF-16 string.
V114 sent tag `0x44` (ANSI).  V115 changed only that empty string tag:

```text
V114: ... 14 05 00 00 00 44 00 00 00 00 0F 00 00 0B 00
V115: ... 14 05 00 00 00 48 00 00 00 00 0F 00 00 0B 00
```

The corrected complete RuntimeRes PC remains 48 bytes:

```text
12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12
7A 2A 0B 02 08 02 08 02 32 00 00 00 00 00 00 00
14 05 00 00 00 48 00 00 00 00 0F 00 00 0B 00
```

## V115 runtime proof

The same delayed packet no longer produced an Error dialog.  It reached the
shop handler and first opened the authentic second-password prompt.  Direct
text entry `1234` produced `CheckSecondPwdVital 0x4B98`; the established OK
response unlocked the UI.  The client then displayed `Sword Soul Shop`, one
`Sword Soul` product, its icon and local tooltip data, plus buy and sell grids.

The product could be dragged from the catalog into the buy grid.  With all
three player currencies at zero, pressing Buy did not emit a purchase request;
the client cleared the cart locally.  Closing the shop emitted one exact
capture-only `TradeCmdVital 0x23B5 v0`:

```text
payload: 08 0C 19 00 00 00 00 08 00
decoded: command=12, dword=0, has_detail=0
```

This command is correlated with close only; no response was invented.  The
run continued with heartbeats and the final flushed GAME/log scan contained no
ErrorData, VitalData mismatch/read failure, fatal, exception, or disconnect
marker.

## Limits preserved

- Store 5 and product 2200009 are client-data-backed, but there is still no
  authoritative NPC-to-store ownership mapping.  P91 remains explicitly a
  test-harness trigger, not a claimed merchant.
- No buy request was captured because the player had zero currency.  Currency
  fields and purchase-result semantics remain unproven and must not be guessed.
- P30 transport and usage-1 service suppression are proven; combat, aggro,
  chase, damage, death, loot, respawn, and authentic FightAttr composition are
  not implemented.
- V111's stateful inventory merge remains the accepted inventory baseline.

## Artifacts

- Server: `current/pf_login_game_server_v115.py`
- Launcher: `current/run_v115_port_royal_monster_shop_milestone.bat`
- Static proof: `derived/v115_tradezoom_utf16_proof.asm`
- Runtime capture: `C:/Users/Panya/Desktop/Pirate Force/GameClient/capture_v115`
- Raw GAME SHA-256:
  `4B1C5023FFD9C21422A937634219F8AAD19E6D08ADB8545C05CF382C52FA3EC6`
- Live event journal SHA-256:
  `B5956E92D0EF6FEAE66D070CB5F08AA67AE5DA4355FBEAC63F85409BE3693EB9`
- Exact-three-file package:
  `packages/PF_Login_Game_Test_v115.zip`
- Package SHA-256:
  `9B7F6C555A510016645118ABBE51C194E08380AB16E501932E0633FB9E0ECCCE`
- Verified checkpoint backup:
  `backups/v115_inventory_monster_shop_20260814_175357/`
- Backup manifest: 51 entries, zero mismatches; manifest SHA-256:
  `54543654176F7AB32127C8F055A5CC5C579D38C66796CB0476509B1F53DE1B84`

## Next evidence-backed work

Continue from V115.  The most useful next static lane is the captured
TradeCmdVital command 12 close path and the store/player currency source.  A
purchase test is justified only after an authentic currency field or server
state update is recovered; do not fabricate money merely to force a request.
In parallel, the isolated P30 boundary can be extended only with statically
proven target/combat packets and data-backed stats, not FightAttr guessing.
