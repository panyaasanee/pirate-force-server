# EQUIP-STATE-001 — equipped-bag versus Character equipment source

Date: 2026-08-16  
Scope: exact read-only client audit; no packet, runtime input, database write,
equipment implementation or new hypothesis.

## Primary claim

`ItemBagAttr_Equiped` is an exact registered structural ItemBag attribute, but it
is **not** the exact named source requested by the Character equipment refresh.
That UI path requests the separate registered `CollectionBagAttr`, type-checks
it, and derives its equipment-control identity map from each contained ItemAttr
byte `+0x39`.

The StartGame handler first imports every received attribute into the local
player's generic attribute aggregate. It then performs class-specific handling
for only `BackpackAttr`, `ActorAttr`, `AvatarAttr` and `MovementAttr`; it has no
direct `ItemBagAttr_Equiped` or `CollectionBagAttr` lookup. Therefore an
`ItemBagAttr_Equiped` record could be retained by the generic aggregate if an
authentic server sent one, but current evidence does not make it the Character
equipment UI source and does not justify synthesizing either attribute.

## Exact registered-class facts

The exact binaries are `GameClient.bin` SHA-256
`C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
and `GameClient.local.bin` SHA-256
`9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.
Every reviewed span below is byte-identical in both.

### `ItemBagAttr_Equiped`

- Exact ASCII class name is at `0xF0EAE4`; its deterministic weighted
  signed-byte registration hash is `0x4B83`.
- Registration `0xBD9690..0xBD96A8` stores the registered u16 at
  `0x1033544`; span length 24, SHA-256
  `D3BE48FDE64E0D28E7A8E3260CEBF4339970D6C503BF2EA7589EA28B26B8F15A`.
  The class name has only that registration immediate reference, and the ID
  global has only the registration store and getter read in the bounded raw
  immediate inventory.
- Custom type registration `0xBD9770..0xBD97A7` binds the exact decorated
  class type separately from `CollectionBagAttr`; length 55, SHA-256
  `0C433A34D012331DFA6E397837D9440FDAEC9327EA2C834F707EEE3E9E1B0560`.
- Pool/factory implementation `0x46A210..0x46A32F` allocates exact size
  `0x68`, constructs the shared ItemBag base through `0x46F3F0` and installs
  vtable `0xF0EA30`; length 287, SHA-256
  `FCC0401C2F27F7698B0EFC7BAB5BC4FB7BB2514E47AA88AFE024E8F188EDCFD8`.
- Vtable `0xF0EA30..0xF0EA78` binds ID getter `0x469E80`, factory
  `0x46A360`, shared clone `0x46EFF0` and shared codec `0x46F180`; length 72,
  SHA-256
  `1DE9B7944B65EB1E6C4F6CC318EF6B68D88551E58C64192F3886990D61751184`.
- Shared codec `0x46F180..0x46F3E9` serializes the Attr base, an ordered
  ItemAttr collection, then a qword-identity collection; length 617, SHA-256
  `29E38267AB54C852E3F1338C2FB833E3B9D1A41903544A390489C264C09FA813`.
  It has no additional class-specific equipment slot, ownership or UI field.

These are structural facts only. The misspelling `Equiped` is retained exactly
from the client class name and is not a semantic correction.

### `CollectionBagAttr`

- Exact ASCII class name is at `0xF0EB40`; its deterministic registration hash
  is `0x3CD0`.
- Registration `0xBD97B0..0xBD97C8` stores the u16 at `0x1033570`; length
  24, SHA-256
  `877E8A2A02E08B046AA5737003E4549A211AC3CC22A7939EF84B27DC86B36568`.
- Custom type registration `0xBD97F0..0xBD9827` binds its distinct decorated
  type; length 55, SHA-256
  `9CFA6AC21E95B97422964E50713AA0956927E2354D553BADE4877EB58C668614`.
- Constructor `0x46AEA0..0x46AEB6` calls base constructor `0x471970`,
  installs vtable `0xF0EAF8` and sets version byte `+0x10=4`; length 22,
  SHA-256
  `35D6C2578D944AD1C538C13D65297A4947CAD4A77C0639359DF78F4940BF025F`.
- Vtable `0xF0EAF8..0xF0EB40` binds ID getter `0x46AEC0`, factory
  `0x46B160`, shared clone `0x46EFF0` and codec `0x471830`; length 72,
  SHA-256
  `05C9297DB41EA3C3082EC3745E3F623C1F46D354CFE2BAC71F846AE2EBEF0570`.
- Codec `0x471830..0x471910` delegates the two shared ItemBag collections to
  `0x46F180`, then adds tagged u16 object `+0x8A`; length 224, SHA-256
  `0756593899A697399B4CBDC8F03F32928F1829C20EBCC9CBCD34B8254C0A0692`.
  Constructor default for that field is `8`, but its gameplay meaning is not
  promoted here.

## StartGame and Character UI boundary

- StartGame handler `0x5DDAE0..0x5DDCFF`, length 543, SHA-256
  `3F958430ED9EFE41BA760FEE8AF192FF7EC802B4E3E31A32EC8C34AA393FBCB8`,
  calls generic aggregate import `0x463870` before any class-specific lookup.
- Generic import `0x463870..0x4638F3`, length 131, SHA-256
  `2F607A9A1E3E36A22D5420DF5871D8CCE89349A41E6C2112FE94C4FB5ADD601C`,
  iterates every source attribute and inserts/clones it through `0x463720`.
  This supports generic retention, not equipment display or ownership.
- The handler's four direct `0x463800` lookups use registered-ID globals
  `0x103353C` (`BackpackAttr`), `0x10334A0` (`ActorAttr`), `0x1033468`
  (`AvatarAttr`) and `0x10334A8` (`MovementAttr`). It contains neither
  `0x1033544` nor `0x1033570`.
- Character equipment refresh focus span `0x5832C7..0x583455`, length 398,
  SHA-256
  `3601887A7BA7E2EA8983ABFB363907EF236DCB497021CC64428F79367565046F`,
  resolves literal `CollectionBagAttr` from the current actor manager at
  `+0x130`, type-checks it through `0x46AED0`, skips ItemAttrs whose raw
  `+0x39` is `0xFF`, and otherwise forms `1 << +0x39` with the ItemAttr qword
  identity. It does not request literal `ItemBagAttr_Equiped`.

- Exact `ItemOperateVitalRes` codec `0x5EDA20..0x5EDC31`, length 529,
  SHA-256
  `B5F6A1586A810C0A98CEB7C925A0D4AFA10CFF41DB661EB0947B8918F3A11D54`,
  allocates its optional decoded bag through `0x46F4D0`. That path allocates a
  plain `0x68`-byte ItemBag and invokes base constructor `0x46F3F0`; it does
  not allocate the `0x90`-byte `CollectionBagAttr` or install vtable
  `0xF0EAF8`. Handler `0x5EF5E0..0x5EF61A` passes the optional plain bag to
  the ordinary ItemOperate result consumer. An operation-5 response using this
  envelope therefore does not itself prove a hidden `CollectionBagAttr`
  update.

This exact distinction is consistent with the retained V130 operational
negative: changing a Backpack ItemAttr to signed slot `-1` and raw `+0x39=3`
did not populate the Character equipment control, because the live inventory
slot was rejected and no `CollectionBagAttr` state was supplied. This report
does not broaden that negative into a new equipment policy.

## Bounded negative, nonclaims and stop rule

Foundation currently emits only the accepted `BackpackAttr` plus Actor/Avatar/
Movement attributes. That remains correct. No original inbound
`ItemBagAttr_Equiped` or `CollectionBagAttr`, no authentic absolute equipment
slot in the proven reserved range `200..229`, no operation-5 response and no
server allocation policy has been recovered.

Do not synthesize either class, reuse bag slot `-1`, choose a reserved absolute
slot, or infer that the two container names are interchangeable. No equipped
item ownership, hand/part mapping, visual weapon state, equip/unequip success,
operation-5/6 response, persistence or reconnect behavior is established.

Resume this domain only after one of the following exact anchors exists:

1. a lawful original inbound `CollectionBagAttr`/equipment response;
2. an exact producer that assigns the same identity to a valid live inventory
   slot and the `CollectionBagAttr` record; or
3. a bounded natural capture that reveals the full response and both state
   transports without guessed fields.

Until then, the equipment milestone stops at this structural distinction and
Foundation StartGame remains unchanged.
