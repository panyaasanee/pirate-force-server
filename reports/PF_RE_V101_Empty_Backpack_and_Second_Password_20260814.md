# Pirate Force V101 empty BackpackAttr and second-password capture

Date: 2026-08-14

## Outcome

V101 preserves V100 and adds one constructor-default empty `BackpackAttr` to
the `StartGameRes` attribute collection. The client accepted the fourth
attribute, entered Port Royal normally, retained the V99 system message and V94
nearest-20 population, and opened the authentic second-password prompt when the
bag button was pressed. This proves both the empty Backpack wire and its
top-level `StartGameRes` ownership path without guessing a populated item.

The server intentionally does not answer the password check yet. A second
runtime run captured the client's exact `CheckSecondPwdVital` request after the
test password was entered. No password was changed and no success response was
fabricated.

## Static proof: BackpackAttr

- class/protocol ID: `0x1F81`;
- registration global: `0x103353C`;
- constructor: `0x46AC70`;
- object size: `0x98`;
- vtable: `0xF0EA88`;
- serializer: `0x469FA0`;
- base-container serializer: `0x46F180`;
- common attribute serializer: `0x467790`.

The constructor leaves both nested container counts empty and sets the final
byte at `+0x68` to zero. The exact constructor-default wire is:

```text
0B FF 32 00 00 00 00 00 00 00 00 0F 00 00 0F 00 00 0B 00
```

The `StartGameRes` handler at `0x5DDAE0` looks up `BackpackAttr` separately
from Actor/Avatar/Movement and inserts it into the backpack manager at global
`0x1093198 + 0x590` through `0x5A2970`. Therefore Backpack is a separate
attribute-collection member, not an unproven field nested into `ActorAttr`.

Relevant derived evidence:

- `derived/v101_inventory_registration_constructors.asm`
- `derived/v101_actor_inventory_base_path.asm`
- `derived/v101_backpack_full_vtable.asm`
- `derived/v101_backpack_base_serializer.asm`
- `derived/v101_backpack_serializer_base.asm`

## Runtime result

Two clean V101 sessions were completed and the game was closed normally so the
raw logs flushed.

First session:

- `capture_v101/GAME_20260814_090927_801237_55513.txt`
- Port Royal bootstrap accepted the four-entry `StartGameRes`;
- runtime heartbeats continued;
- one TargetPos movement key produced the preserved V94 local population;
- clicking the bag opened the second-password UI;
- no ErrorData 28317, traceback, exception, fatal, or disconnect marker.

Second session:

- `capture_v101/GAME_20260814_091821_281339_49693.txt`
- entering four keys and pressing Enter emitted one 64-byte decompressed
  runtime request containing `CheckSecondPwdVital` ID `0x4B98`;
- the request carried the 32-byte uppercase digest
  `7D014E541AFAA43267CA80BCCBC3FD6B`, not the plaintext password;
- the server did not respond, so client state and password state were not
  changed;
- no error/exception/fatal/disconnect marker was present.

The exact decompressed request was:

```text
12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12
98 4B 0B 00 08 00 19 00 00 00 00 44 20 00 00 00
37 44 30 31 34 45 35 34 31 41 46 41 41 34 33 32
36 37 43 41 38 30 42 43 43 42 43 33 46 44 36 42
```

This proves the request framing and digest transport. It does not yet prove
which response result value means accepted/unset/incorrect, so V101 sends none.

## Second-password static boundary

- `CheckSecondPwdVital` ID: `0x4B98`, constructor `0x4E5150`, vtable
  `0xF1A780`, object size `0x38`, serializer `0x5E6060`, handler `0x5F05B0`;
- its fields serialize as u8 at `+0x14`, u32 at `+0x18`, and ANSI string at
  `+0x1C`; the runtime digest used tag `0x44` and length 32;
- `ChangeSecondPwdVital` constructor `0x4E5030`, vtable `0xF1A75C`, object
  size `0x50`, serializer `0x5E5FF0`, handler `0x5F0460`;
- Change serializes u8 at `+0x14` and two ANSI strings at `+0x18`/`+0x34`.

The handler branches prove multiple result states exist, but their user-facing
meaning still needs an evidence-backed mapping before a response is emitted.

## Verification

- Python compile: PASS
- project self-test: PASS
- exact constructor-default Backpack wire assertion: PASS
- four-entry StartGameRes assertion: PASS
- Snappy roundtrip: PASS
- live bootstrap/client acceptance: PASS
- authentic bag password prompt: PASS
- V99 message and V94 population regression: PASS
- password request raw capture: PASS

Runtime/static backup:
`backups/v101_empty_backpack_20260814_092719/`

Package: `packages/PF_Login_Game_Test_v101.zip` (exactly three root files)

SHA-256: `B4F265542BD1AA503CFA341B32DA825CC2D6CCEE20DCAEB2B4E917D629D36192`
