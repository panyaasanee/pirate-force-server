# Pirate Force RE — V107 to V110 stateful inventory and ActionItem capture

Date: 2026-08-14

## Outcome

V107 and V108 close the Backpack move-mutation boundary. V109 and V110 then
open a new item-use boundary without guessing any protocol field. The final
V110 runtime proves that right-clicking the data-backed Camouflage Item-Cask
sends `ActionItemVital 0x3058`, not `UseItemVital 0x1F4F`.

No ActionItem response is implemented yet. The actor therefore does not
transform and the cask remains in the Backpack. This is a request-capture and
static-identification checkpoint, not a completed consumable system.

## V107 and V108 inventory baseline

Static recovery of response handler `0x5A8A00` explained V106's removal: the
first ItemBagAttr collection updates ItemAttrs, while identities in the second
collection reach removal call `0x59FC50`. V107 kept the updated ItemAttr and
made the removal-identity collection empty. Runtime moved Adventure Key from
slot 0 to slot 1 while preserving `1 / 40`, including after closing/reopening
the Backpack.

V108 added one server-side current-slot state. A single live session moved the
same identity `0 -> 1 -> 2 -> 0`; each response preserved exactly one item and
`1 / 40`. Exact request evidence in both directions proves operation `4` and
the request dword as destination bag slot for this path.

V108 is the golden stateful multi-destination bag-move baseline.

Package hashes:

- V107: `11919B151969CACA8B4E0184754B7BB82DAD928A0C91B9A6567A461680054EA1`
- V108: `BE5A541F7743FFF150B33EC76B12291C1E972DF0A770F8D3F3A6F233E766376F`

## V109 negative use probe

Decoded STORE_NORMAL store 1 explicitly lists global item `2400036`.
ITEM_CONSUMABLES row 36 and its Thai text row identify the level-1 Beginner
Oblivion White Pill, usage 580. V109 added it as identity 2 in slot 1 with
constructor-default ItemAttr detail fields.

The authentic UI result is important:

- Backpack opened at `2 / 40` with Adventure Key and the correct pill.
- Double-click did not emit a request.
- Right-click opened the skill-reset window.
- The level-1 actor has no learned skills, so the list was empty and the reset
  button emitted no item request.

This rejects the pill as a useful network probe for the current actor without
rejecting its ItemAttr construction. No server response was guessed.

V109 package SHA-256:
`D4D7740923D061F4FCBEEB2A8D7B52A15BE8895E9DD5DF506B5EC785CF5D6D18`.

## V110 data-backed camouflage probe

STORE_NORMAL store 1 also explicitly lists global item `2400901`.
ITEM_CONSUMABLES row 901 proves:

- level condition 1;
- usage 5023;
- cooldown group 110;
- stack limit 99.

ITEM_CONSUMABLES_TIP row 901 names it `Camouflage Item-Cask` and states that
using it transforms the actor into a cask. V110 replaced only V109's second
probe ItemAttr with this template. It preserved Adventure Key identity 1,
stateful moves, password response, population, conversations, facing, system
message, music, and stable bootstrap.

Compile, self-test, Snappy roundtrip, deployed-hash comparison, and exact-three
ZIP verification passed before runtime. Package entries are exactly:

- `GameClient.local.bin`
- `pf_login_game_server_v110.py`
- `run_v110_port_royal_use_item_capture.bat`

V110 package SHA-256:
`C5254A7F540336B0C38357247A4DA078A8E8A0B27A79C9CBBFECDFE84A639899`.

## Exact runtime request

The V110 Backpack opened at `2 / 40` with the correct cask icon and tooltip.
Two controlled right-clicks produced byte-identical nested requests:

- ID `0x3058`;
- nested version 0;
- 93-byte nested payload;
- global template `2400901`;
- item identity 2;
- request position `(0, 0, 0)`.

The recovered protocol-name algorithm is the 16-bit sum of each ASCII byte
multiplied by its one-based index. Running it over the recovered 731 client
protocol class names gives one match for `0x3058`: `ActionItemVital`.

Static and read-only Frida evidence independently prove:

- constructor `0x74E8E0`;
- ID getter `0x74E960`;
- vtable `0xF48A34`;
- serializer `0x74E980`;
- shared base serializer `0x74E6A0`;
- client receive handler `0x750230`.

The serializer writes the shared action base, then dword `+0x50`, qword
`+0x58`, and vec3 `+0x60`. The live request object contained `2400901`, item
identity 2, and zero vec3 respectively. Its seven shared action dwords at
`+0x18..+0x30` were all zero.

Handler `0x750230` forwards those seven shared action dwords to `0x5CAF80` and
does not establish that echoing the client request is a valid success response.
Therefore V111 must not reflect the request or invent action values. First
recover the authoritative server-to-client item-action/result path.

Evidence:

- `derived/v110_action_item_trace.jsonl`
- trace SHA-256:
  `E23AF94744C1AA70A37215EEFCA521FCB0D450A14B63AB3DEDDCF3B142DCB44D`
- runtime capture:
  `C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_v110`

## Faster UI automation, measured

The previous automation spent a tool round trip and screenshot after every PIN
digit. V110 runtime proves the game accepts the entire literal `1234` through
one `type_text` action; one following `Return` opened the Backpack and emitted
`CheckSecondPwdVital`. The custom field remains visually blank, so masked-digit
screenshots are not useful evidence.

Timeline analysis measured `character-ready -> StartGame` at 13.812 seconds in
this run. Most of that avoidable delay came from an expensive screenshot
refresh while the client was already changing screens. The persistent fast
workflow now uses:

- one server-list observation and Enter;
- one confirmation observation and Enter;
- lightweight post-action refreshes during loading;
- live protocol milestones rather than blind waits;
- one character observation and Enter;
- one complete PIN text action plus Enter.

The client itself took about 41.9 seconds from Teleport send to first runtime
request in this run. That loading interval is separated from automation delay.
The durable workflow is documented in `tools/PF_FAST_ENTRY_AUTOMATION.md`.

## Consolidated checkpoint backup

The requested five-version checkpoint is preserved at:

`backups/v110_actionitem_capture_20260814_150007/`

Its manifest contains 25 files and verified with zero mismatches. Manifest
SHA-256:

`853C387D5BB807ACC04ADB8790F22F349C213039F5EAD8A412D8F451DF216062`

The live V110 game/server session remained open; the backup therefore treats
the line-buffered live logs as authoritative and does not require the raw GAME
file to be flushed.

## Next evidence boundary

Continue static/dynamic analysis of ActionItemVital and the item-usage dispatch
for usage 5023. Build V111 only after a constructor/handler-backed response or
state update is recovered. Do not try action IDs, shared action dwords, result
values, or alternate item fields by experiment.
