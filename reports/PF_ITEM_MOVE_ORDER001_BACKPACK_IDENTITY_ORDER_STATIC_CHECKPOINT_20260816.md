# ITEM-MOVE-ORDER-001 — Backpack identity-order static checkpoint

Date: 2026-08-16
Scope: read-only exact-client audit; no packet, runtime input, database write, or
gameplay implementation change.

## Primary claim

The exact client stores the first Backpack ItemAttr collection in a tree keyed
by the ItemAttr qword identity, not by its bag slot. The codec write branch walks
that tree through its in-order successor. For the small positive identities in
the accepted current state, the client therefore canonicalizes the collection as
`[1,2,4]`. The exact post-V111 merge state has slots `{0,1,3}`, so slot 2 is
structurally unoccupied at this boundary.

This reduces two compatibility uncertainties around HYP-PF-008. It does **not**
turn the composed response or persistence policy into original-server evidence.

## Grade-A static facts

- Exact binaries are `GameClient.bin` SHA-256
  `C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
  and `GameClient.local.bin` SHA-256
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.
  Every reviewed span below is byte-identical in both:

  - ItemAttr codec `0x46BD30..0x46BEA1`, 369 bytes, SHA-256
    `B21137BDE28452C08F8FA6A2EDA18ACCF9C2D51B9B7D82A1B6997986FEBA86C1`;
  - ItemBag/Backpack container codec `0x46F180..0x46F3E9`, 617 bytes,
    SHA-256 `29E38267AB54C852E3F1338C2FB833E3B9D1A41903544A390489C264C09FA813`;
  - ItemAttr insertion `0x46EC20..0x46EDF0`, 464 bytes, SHA-256
    `4C07FEB6722C81256E3ACECFD8A66BFC88B7B53DAE35AF210A7B3AF78D105F7D`;
  - identity-tree insertion/comparator `0x5FC970..0x5FCA61`, 241 bytes,
    SHA-256 `C97047A3030806658AC26A4BF9569114EBBD63FF3DA2B3C34D121C088B56B1A3`;
  - tree successor `0x46D2B0..0x46D31C`, 108 bytes, SHA-256
    `492E39AFB9FAF38F4F862ABCDAA6278740417A4B1FC1E56D61A6B992421D5CF9`.

- ItemAttr codec `0x46BD30` writes and reads the tag-`0x32` qword at object
  `+0x28`. Existing accepted wire mapping identifies this value as the ItemAttr
  identity.
- On the Backpack read/apply path, `0x46ED1E/0x46ED21` copy ItemAttr
  `+0x28/+0x2C` into the tree key passed at `0x46ED48 -> 0x5FC970`.
- Comparator `0x5FC991..0x5FC9A2` compares the high dword first and the low
  dword unsigned when the highs are equal. For identities 1, 2, and 4 (all high
  dword zero), this is ascending numeric identity order.
- The write branch at `0x46F1C5..0x46F25F` writes the collection count,
  serializes each pointed ItemAttr, and advances through exact successor
  `0x46D2B0`. It never consults ItemAttr slot `+0x34` to choose order.
- The accepted merged Backpack consists exactly of identities/quantity/slot
  `(1,2,0)`, `(2,1,1)`, `(4,1,3)`. No ItemAttr occupies slot 2 in that complete
  snapshot.

## Inference and evidence ceiling

An inbound collection containing unique identities 1, 2, and 4 is structurally
compatible with the client codec, and its internal tree state becomes identity
ordered regardless of input order. Emitting `[1,2,4]` on the HYP-PF-008
reconnect is therefore a client-compatible canonical choice rather than a
slot-order guess.

The exact original server's reconnect ordering, move-response selection, durable
move policy, and acceptance of the combined quantity-2/slot-2 response are still
missing. HYP-PF-008 remains Grade D, test-only, and non-production until the
paused controlled client capture/runtime test or lawful original evidence proves
or falsifies it.

## Nonclaims and stop rule

No occupied-slot swap, displacement, generalized movement, split, drop, equip,
ownership, economy, or UI acceptance is proven. Do not add a second move
hypothesis or change occupied slot 3. Resume the exact live capture only after the
user manually clears the Backpack PIN dialog; otherwise move to a separate
milestone rather than layering another guessed response.
