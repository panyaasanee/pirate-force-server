# ITEM-MOVE-CONSUMER-001 — ItemOperate response-apply static checkpoint

Date: 2026-08-16
Scope: read-only exact-client audit; no packet, runtime input, database write, or
gameplay implementation change.

## Primary claim

The exact `ItemOperateVitalRes` success path applies each ItemAttr in the first
ItemBag collection as a complete replacement payload. It first clears the
currently displayed item with the same qword identity, then selects the
destination from the incoming ItemAttr slot and clones the complete incoming
identity, template, quantity, slot and remaining raw fields into that slot's
payload object.

This path does not compare the incoming quantity with an old quantity, does not
require the incoming slot to equal the old slot, and contains no destination-
occupancy rejection before replacing the slot payload. Composed with the exact
merged state from ITEM-LIFECYCLE-001 and the free-slot proof from
ITEM-MOVE-ORDER-001, the HYP-PF-008 quantity-2/slot-2 response has no hidden old-
quantity, old-slot, or occupied-destination gate in this exact client consumer
lane.

This is client-consumer proof only. It does **not** authenticate the response or
promote the durable/reconnect policy above Grade D.

## Grade-A static facts

- Exact binaries are `GameClient.bin` SHA-256
  `C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
  and `GameClient.local.bin` SHA-256
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.
  Every reviewed span is byte-identical in both:

  - response apply loops `0x5A8EBD..0x5A9068`, 427 bytes, SHA-256
    `950135C96FF407BA6326B1A1B6339F8F5D7394DA5D6A1E1C41EE03CA90B4C613`;
  - identity clear helper `0x59FB40..0x59FC50`, 272 bytes, SHA-256
    `57AA9A29838E4C57BC9B6528B43C215B1E2F93F86DC281B4B65ACDD635B7DC61`;
  - slot assignment helper `0x5A1240..0x5A1309`, 201 bytes, SHA-256
    `6434F0F14A829A398E3DAB276BBC8823F808D075CA0EDE62C7DB901E260BF971`;
  - slot payload replacement `0x5C15B0..0x5C1668`, 184 bytes, SHA-256
    `BFEEBED09703D388B2477815A75E59AB7311979322E70A8A0F40D4D6EAC2420B`;
  - ItemAttr constructor `0x46B410..0x46B497`, 135 bytes, SHA-256
    `5A5D9ABA90E35EEA8119D252751058561C125FF68E54C3416A8BEF6230872DDC`;
  - ItemAttr vtable `0xF0EBB0..0xF0EBF0`, 64 bytes, SHA-256
    `8BE15B9EE799423FDDE3C7D5E31F698188B503FEE54BD6035843B5B79830EDCC`;
  - ItemAttr clone `0x46BC50..0x46BD2C`, 220 bytes, SHA-256
    `FB3FE799D07B56019A747134D39572AA4A7B31EB33961C6858D43535D93B9BFD`.

- At `0x5A8F30..0x5A8F61`, the handler loads the incoming ItemAttr identity
  qword from `+0x28/+0x2C`, also passes raw `+0x30`, and calls `0x59FB40`.
  That helper compares only the existing slot payload's identity qword against
  the first two arguments; the third argument is not used in this function. It
  invokes the existing slot payload's clear method on an identity match.
- At `0x5A8F8E..0x5A8F9E`, the handler reads the incoming signed slot word at
  `+0x34` and passes both that slot and the incoming ItemAttr pointer to
  `0x5A1240`. The response-apply path does not read ItemAttr quantity `+0x36`.
- `0x5A1240` validates only that the slot lies within the configured slot count
  and resolves the corresponding slot widget through `0x5F8400`. It does not
  compare the destination payload's identity, quantity, or prior slot before
  calling replacement helper `0x5C15B0`.
- For a non-null incoming payload, `0x5C15B0` releases the slot's existing
  payload at `+0x20`, creates a fresh ItemAttr, and dispatches the incoming
  object's vtable slot `+0x24`. ItemAttr constructor `0x46B410` installs vtable
  `0xF0EBB0`; that exact vtable slot resolves to clone `0x46BC50`.
- Clone `0x46BC50` type-checks the source and copies the complete raw ItemAttr
  state, including identity `+0x28/+0x2C`, template `+0x30`, quantity `+0x36`,
  slot `+0x34`, the two byte fields and optional-detail state. It derives none
  of those values from the previous slot payload.

## Composition with the current exact state

ITEM-LIFECYCLE-001 fixes the merged state as `(identity,quantity,slot)` tuples
`(1,2,0)`, `(2,1,1)`, and `(4,1,3)`. ITEM-MOVE-ORDER-001 proves slot 2 is
unoccupied and that identities `[1,2,4]` are client-canonical tree order.
Therefore the exact HYP-PF-008 response payload for identity 1, quantity 2, slot
2 does not encounter an occupied destination in that proven state, and the
consumer does not require quantity 1 or slot 0 after routing begins.

## Evidence ceiling and stop rule

The exact original server's decision to send this response, its outer policy,
durable move authorization and reconnect projection are still absent. Live
client acceptance and visible UI movement remain pending because the controlled
capture is paused at the user-owned second-password dialog. HYP-PF-008 remains
test-only, non-production, and Grade D.

Do not infer occupied-slot swap/displacement from the replacement helper: the
separate Backpack collection can still retain another identity mapped to the
same slot, and that inconsistency has not been tested or authorized. Do not add
another move hypothesis. Resume the exact live run only after the user manually
clears the PIN dialog; otherwise switch milestones.
