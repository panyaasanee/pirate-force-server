# Pirate Force V96 runtime and V97 NPCConversation probe

Date: 2026-08-14

## V96 runtime result

The user tested single click, double click, and ground click against several
members of the streamed Port Royal population. The client showed no dialog or
service icon and NPCs did not turn. This is expected for V96: it captures
interaction requests and intentionally sends no interaction response.

The flushed `capture_v96` evidence proves:

- single click emits `TargetVital` (`0x1ADD`);
- double click/use emits `ChooseNPC` (`0x0FB6`);
- `ChooseNPC` v0 contains exactly tag `0x32` plus the selected qword actor ID;
- one double click can place `TargetVital` and `ChooseNPC` in the same runtime
  collection, or repeat `ChooseNPC` for the same actor;
- observed actor IDs mapped exactly to current P50/Plato, P39/Carle,
  P89/Betula, P144/Jessica, P84/Qina, P30/Tornado Eagle, and P91/Local people.

V94 had already captured a separate `TargetVital` with actor identity zero,
which proves ground-click target clearing exists. Failure to see a visible
clear effect in this V96 session does not change that packet evidence.

## Historical sword-cursor check

The V74 GAME log contains `ChooseNPC` for actor `0x2047`, which maps by the
established placement identity formula to P70/Lecherous slave buyer. This proves
that an NPC was double-clicked in V74, but logs do not encode cursor graphics,
so it does not prove which actor displayed the sword cursor. The user remembers
the sword cursor from the V74-era scene; retain V74 as the leading historical
candidate, not as a proven cursor-source version.

## Static proof for V97

Direct analysis of `GameClient.local.bin` recovered:

- `ChooseNPC` ID registration at `0xBF2B10`, constructor at `0x621790`, and
  serializer entry `0x6C0180`, which writes qword object field `+0x18` with
  wire tag `0x32`;
- `NPCConversation` ID registration at `0xBF2B50`, constructor at `0x622A00`,
  ID getter `0x622A70`, and serializer at `0x622F10`;
- `NPCConversation` v0 writes qword actor ID `+0x18/+0x1C` using tag `0x32`,
  then a `u16` collection count using tag `0x0F`, followed by nested items only
  when the count is nonzero;
- its client handler reaches the quest/NPC UI path and uses the same actor ID.

Therefore an empty collection is a constructor-valid, serializer-exact focused
probe. It does not invent a conversation, quest, shop, service type, or unknown
field.

## V97 behavior

V97 preserves V94 population streaming, V96 live journals, and the stable
bootstrap. On a `ChooseNPC` for a member of the current authoritative nearest-20
population, it replies once per distinct actor in that request with:

`NPCConversation v0 = tag32 actor_qword + tag0F count_zero`

Repeated copies of the same `ChooseNPC` in one runtime collection are
deduplicated. A non-current/unknown identity receives no response. TargetVital
still receives no movement response, so the rejected V95 teleport cannot recur.

The runtime question is narrow: does double-clicking a current NPC now open or
change the NPC conversation UI path? An empty dialog/list or a clean no-op are
both informative; movement or teleport would be a failure.

## Verification

- Python compile: PASS
- project self-test: PASS
- V94 population bootstrap/refresh regression: PASS
- V96 TargetVital event capture regression: PASS
- standalone and TargetVital-bundled ChooseNPC decode: PASS
- repeated ChooseNPC deduplication: PASS
- exact NPCConversation payload and Snappy roundtrip: PASS
- non-current actor ignored: PASS
- stable bootstrap unchanged: PASS

Package: `packages/PF_Login_Game_Test_v97.zip` (exactly three files)

SHA-256: `E44A3E77B34B5A5075CEE58BF840A9FD1635392E3458BC4F9537BE270C6F920A`
