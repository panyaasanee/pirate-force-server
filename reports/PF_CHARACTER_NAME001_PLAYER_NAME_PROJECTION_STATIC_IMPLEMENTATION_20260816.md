# CHARACTER-NAME-001 — persisted player-name projection

Date: 2026-08-16
Result: Grade A static boundary; offline implementation pass pending runtime

## Primary claim

The persisted selected-character name now has one exact typed path into the
client field consumed by `NameBoardPlayer`. Foundation keeps Create/List actor
wire lossless, requires its embedded name to equal the canonical persisted name,
and emits that same name in StartGame `ActorAttr` mask bit `0x01000000` at object
wstring `+0x164`. This is not the NPC/target-panel `BasicAttr+0x28` field.

## Exact client facts

Both exact 14,759,424-byte client profiles have identical relevant code:

- `GameClient.bin` SHA-256
  `C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`.
- `GameClient.local.bin` SHA-256
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`.
- CreateActorDataEx codec `0x5DFF60` writes/reads its name wstring at object
  `+0x24` after identity and selector (`0x5DFF93 -> 0x89A810`; mirrored reader
  `0x5E0086 -> 0x89A880`). SelectActor consumer `0x5EFC40 -> 0x5DDD00`
  retains the full actor records.
- ActorAttr constructor entry `0x464BE0` constructs the wstring at `+0x164` at
  `0x464C84`.
  Serializer `0x466230` writes the 64-bit mask, its mandatory bool, then fields
  in ascending mask-bit order. Cash bit `0x00000800` writes qword `+0xA8` at
  `0x4663C6..0x4663DF`; name bit `0x01000000` writes wstring `+0x164` at
  `0x466544..0x466559`. Reader `0x466A61..0x466A76` mirrors the name field.
- Custom RTTI identifies `NameBoardPlayer` through its type descriptor and
  type getter `0x5BB300 -> 0x102DA44`; its vtable `0xF2CD08` selects update
  `0x5BD320`. That update obtains ActorAttr through `0x43B9B0`, then
  `0x5BD4DA` addresses ActorAttr `+0x164` and `0x5BD500..0x5BD512` assigns the
  wstring to its `LABEL_NAME` widget. Loader `0x5BE080` resolves the exact
  `NameBoard_Player` layout.
- `0x51F920` and the following `NameBoardNPC` update use `BasicAttr+0x28` for
  other UI/name lanes. They are negative controls and are not the player
  name-board source.

Compact static guard spans, byte-identical in both profiles:

- `0x4663C6..0x4663E4`:
  `F786B40100000008000074126A088D96A8000000526A328BCFE81C424300`.
- `0x466544..0x46655E`:
  `F786B401000000000001740E8D8664010000508BCFE8B2424300`.
- `0x466A61..0x466A7B`:
  `F786B401000000000001740E8D8664010000508BCFE8053E4300`.
- `0x5BD4C4..0x5BD512` contains the exact ActorAttr downcast, `lea edi,[eax+164]`,
  compare, and label-set sequence.

## Foundation implementation

- `actor_wire.read_name()` parses only the exact CreateActorDataEx prefix:
  tag `0x48`, u32 byte length, even and input-bounded strict UTF-16LE.
- `CharacterLifecycle.create()` requires the submitted name to already equal
  its NFKC+trim canonical form and to equal the embedded actor-wire name. It
  rejects without rewriting opaque actor/avatar bytes.
- `LegacyProjector.start_game()` uses persisted `Character.name` for both normal
  and frozen faction-1 paths. BasicAttr remains `0x030C` or `0x070C`; ActorAttr
  low mask becomes `0x01000800`, followed by mandatory bool, existing cash qword,
  then exactly one tag-`0x48` name wstring.
- Create success and Character List still emit the exact persisted actor wire.
  Identity, selector, opaque AvatarAttr and the frozen faction value are unchanged.

Focused tests cover canonical source equality, non-ASCII exact wire, mask/order,
normal/faction differential, Create/List continuity, strict malformed prefix,
empty/non-string/unencodable names, canonical mismatch rejection, no-row/no-reply
for noncanonical Create, and updated StartGame golden hashes.

## Nonclaims and stop rule

This checkpoint does not prove a live visible label, remote-player naming,
rename/name-uniqueness policy, job/class semantics, authenticated ownership, or
server-process restart durability. It adds no hypothesis and does not change
immutable V141. Accept only after the deterministic verifier and independent
review pass; a separate controlled runtime must confirm the selected player's
world name board before promoting a visual claim.
