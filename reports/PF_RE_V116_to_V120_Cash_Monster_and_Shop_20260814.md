# Pirate Force RE checkpoint — V116 to V120

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

This checkpoint supersedes any earlier note that the V115 Sword Soul icon was
successfully inserted into the Buy grid. V115 captured only `TradeCmdVital`
command 12 and no command 6/detail. V118 plus the static inventory-manager path
prove that the earlier visual observation was an icon-follow/drag state, not a
completed cart insertion.

## V116 — exact initial cash field

`ActorAttr` cash is the qword at `+0xA8/+0xAC`, selected by the ActorAttr mask
bit `0x800`. The client Lua binding names the same value `GetCash`; the normal
store buy predicate and HUD money panel read that exact qword.

V116 changed only the initial ActorAttr own mask from zero to `0x800` and sent
cash `10000`, the decoded buy price of Store 5 product `2200009` (`Sword Soul`).
The normal store displayed the corresponding one-gold denomination. This did
not prove a purchase request or purchase response.

## V117 — exact P30 HP

P30/template 31 is the data-backed usage-1 monster `Tornado Eagle`. Its exact
level is 27 and decoded `STANDARD_MOB` row 27 gives max HP `3857`. V117 changed
only P30 current/max HP from `100/100` to `3857/3857`; P91 remained the
`100/100` control. The decompressed population packet retained its length and
changed only the four expected HP bytes. No `FightAttr`, `ActionVital`, AI,
skill, damage, or combat packet was added.

Runtime accepted V117 for more than eight minutes with normal heartbeats and no
version mismatch, `ErrorData`, fatal, exception, or disconnect marker.

## V118 — cart acknowledgement implementation and failed activation boundary

Static producer tracing established the catalog/cart request:

- `TradeCmdVital` ID `0x23B5`, nested version 0;
- command 6;
- dword 0 (the prior value 8 was an internal controller event type, not wire);
- required `ItemAttr` detail.

V118 implemented only the exact command-6 boundary for Sword Soul quantity 1.
It returns `TradeItemResultVital` ID `0x557B`, version 0, result 13
(`Trade_Shop/Store_ByItemOK`), copying identity/template/quantity and retaining
constructor-default slot `-1`, `+0x38=0`, `+0x39=0xFF`, no nested detail. Cash
and Backpack are not mutated.

The V118 runtime could not emit command 6. A clean catalog-to-Buy-grid drag
displayed Thai message 127, `not enough space`, and emitted no `TradeCmdVital`.
The client continued hundreds of heartbeats without error.

## V119 — P30 target-panel name

The client target panel reads its name from `BasicAttr+0x28`. V119 added only
BasicAttr mask bit `0x0001` and the exact current-client `MOBS_TIP` row-31
wstring `Tornado Eagle` to P30. P91 remained byte-identical; P30 HP remained
`3857/3857`. Population PC length changed `317 -> 348` and framed length
`330 -> 361`. No server response was added for the runtime-proven
`TargetVital kind=2`; target name/HP presentation is client-local.

## V120 — Backpack operational range and exact shop requests

The V118 blocker was not `TradeZoomVital`. `BackpackAttr` serializer writes its
final tagged byte from object `+0x68`. StartGame handler `0x5A2970` copies this
byte verbatim into inventory-manager enabled-segment mask `+0x30`.

Free-slot counter `0x5A19E0` tests:

- bit 0 for the base 40-slot range;
- bit 1 for an additional 40-slot range;
- bit 2 for an additional 80-slot range.

V101 through V119 used constructor-default zero. The Backpack UI could still
display its items and `3/40`, but the store free-slot validator scanned no
enabled segment and returned zero. V120 changed only the live three-item
Backpack trailing wire byte `0B 00 -> 0B 01`. Items, both collections,
identities `1/2/3`, slots `0/1/2`, cash, population, and bootstrap were
unchanged. The client therefore counts `40 - 3 = 37` free base slots and caps
the Buy grid at its 18 cells.

V120 runtime passed this boundary:

1. The Buy cells were enabled and the same clean drag inserted Sword Soul.
2. Client request was captured exactly as command 6, dword 0, detail present,
   identity 0, template `2200009`, quantity 1.
3. V118 result-13 acknowledgement was accepted; the cart displayed Sword Soul
   and cost one gold.
4. Clicking Buy and confirming emitted the exact final request command 8,
   dword 0, no detail. The earlier predicted dword 11 was another internal UI
   event type and is disproven on the wire.
5. With no final response, cash and inventory stayed unchanged and the cart
   remained open.
6. Repeated close attempts emitted command 12, dword 0, no detail. With no
   response, the shop remained open, so command 12 is not a proven
   fire-and-forget close.

Exact captured nested bodies:

```text
cmd6:  08 06 19 00000000 08 01 32 0000000000000000 14 C9912100 0F 0100
cmd8:  08 08 19 00000000 08 00
cmd12: 08 0C 19 00000000 08 00
```

Final V120 capture contains no version mismatch, `ErrorData`, fatal,
exception, or disconnect marker. The flushed capture and verified source,
launcher, and package are preserved at:

`backups/v120_shop_cmd6_cmd8_boundary_20260814_195625/`

V120 package SHA-256:

`97CBBC829BD74E5A27EDEC3F754742359829A93D146E012B6F809A84CE535653`

## Exact next boundary

V121 corrects the runtime model and journals only a sequenced command 8 after
an acknowledged command 6. It does not reply or mutate state. Before a complete
purchase is implemented, resolve with instruction-level evidence:

- result 15 versus 17 for `ResetBuyItem`;
- `UpdateAttrVital` ordering relative to the trade result;
- whether incoming `BackpackAttr` is a merge delta or a full replacement;
- the server-owned new item identity and slot policy;
- whether Sword Soul requires its data-backed `ItemVaryAttr` on purchase.

Do not use `ItemOperateVitalRes` as a shop mutation carrier and do not invent a
cash/item mutation from command 8 alone.
