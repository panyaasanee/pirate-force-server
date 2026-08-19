# Pirate Force RE — V104 ItemOperate request capture

Date: 2026-08-14 (Asia/Bangkok)

## Result

V104 completed its capture-only runtime test without sending a speculative
item response. Dragging the one V103 Adventure Key from Backpack slot 0 onto
slot 1 produced one exact 16-byte nested request payload while the client kept
running normally. Because the server intentionally did not answer, the icon
returned to slot 0. The game then closed normally and flushed the full GAME
log.

The runtime request ID is `0x4BED`. The protocol registration hash recovered
from client function `0x89B220` resolves it uniquely to
`ItemOperateVitalReq`; the paired registered response is
`ItemOperateVitalRes = 0x4C13`. The earlier generic class hashes
`ItemOperateVital = 0x36FE` and `UseItemVital = 0x1F4F` are not this request
wire and were never answered.

## Exact captured request

Event time: `2026-08-14T10:42:39.378`

Full decompressed protocol:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 ED 4B 0B 00 0B 04 14 01 00 00 00 32 01 00 00 00 00 00 00 00`

Nested payload:

`0B 04 14 01 00 00 00 32 01 00 00 00 00 00 00 00`

Client constructor `0x5E5A90` and serializer `0x5E5AF0` independently prove
the exact object layout and wire order:

| Object field | Wire | Runtime value |
| --- | --- | --- |
| `+0x14` | tag `0x0B`, byte | `4` |
| `+0x18` | tag `0x14`, dword | `1` |
| `+0x20/+0x24` | tag `0x32`, qword | item identity `1` |

The post-capture V104 decoder deliberately records the fields as
`operation`, `value32`, and `item_identity`. The UI action makes destination
slot 1 a supported hypothesis for `value32`, but V104 does not promote that
semantic name or mutate inventory.

## Exact response class recovered statically

`ItemOperateVitalRes` has object size `0x34`, constructor `0x5EBED0`, vtable
`0xF30668`, ID getter `0x5EBF70`, serializer `0x5EDA20`, and client handler
`0x5EF5E0`.

Serializer `0x5EDA20` proves this response order:

1. tag `0x08`, one-byte result from `+0x30`;
2. tag `0x0B`, presence of one optional ItemBagAttr at `+0x14`, then that
   object's ItemBag serializer when present;
3. tag `0x08`, one-byte count of `0x20`-byte entries held by the container at
   `+0x18`;
4. for each entry: tag `0x32` qword from entry `+0x10`, then tag `0x08` byte
   from entry `+0x18`.

The deserialization branch at `0x5EDB56` calls fixed allocator `0x46F4D0` on
pool `0x1031420`. Direct disassembly proves that allocator always creates a
size-`0x68` ItemBagAttr via constructor `0x46F3F0`; ItemBagAttr vtable
`0xF0ECB8` has serializer `0x46F180` in the exact virtual slot invoked by the
response. No dynamic class ID or guessed polymorphic type is involved.

Handler `0x5EF5E0` forwards the optional ItemBagAttr, entry list, and result to
the two inventory models at `0x5A8A00` and `0x5C6D20`. `0x5A8A00` treats a
nonzero result as an error path. On result zero, both handlers process the
ItemBagAttr and affected-identity list. This is strong static evidence that a
successful slot move should return an ItemBagAttr carrying the updated item,
but V104 does not yet emit that hypothesis.

The V103 ItemAttr slot role is already independently proven at object
`+0x34`, serialized as the second tag-`0x0F` word. Therefore the next focused
runtime hypothesis may return result zero, one ItemBagAttr whose two containers
carry the existing identity/template/quantity with only slot
`0 -> requested value32`, and an empty affected-entry list. The ItemBagAttr
body is the already-proven 52-byte ItemBag serializer shape; it is the V103
54-byte Backpack body without BackpackAttr's final subclass byte. No other
unknown field needs to change.

## Runtime verification

- V103 Backpack remains `1 / 40` and shows one item in slot 0 before action;
- one controlled drag from slot 0 to slot 1 emitted exactly one request;
- server sent no response for `0x4BED`;
- client heartbeat traffic continued normally;
- game closed normally and flushed logs;
- final scan for `28317`, fatal, traceback, disconnect, exception, error,
  assert, send failure, or decode error: no matches.

Capture directory:

`C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_v104`

Important capture hashes:

- `GAME_20260814_104001_945460_58812.txt` —
  `5C4B8DED65365D94E133D2877F606CC3D5D5B6D7D14EF3DF6CCC6A6E3F6ECB44`
- `GAME_LIVE.txt` —
  `AA13217DDEED0E44F1CC0131C9E3B2B0F0194130B1D13C345E5AE26732003744`
- `GAME_EVENTS_LIVE.txt` —
  `C59B674B9C42BE1BF1164169227FB7816420A98D0B805997CFD784FFB17E6C3E`
- `LOGIN_20260814_103925_049762_55589.txt` —
  `05977A2FAC796F496C86DC2E63FB3DF17FA2584C59409D896684DFEFCEC7E9C6`

## Corrected checkpoint artifacts

After capture, V104's labels and self-test were corrected to the exact
Req/Res class names. This changes no outbound runtime behavior: the request
still receives no response.

- server `current/pf_login_game_server_v104.py` —
  `44C9103744940CDA87DC901D19F0190169A55BAAD98C4CE917B7A84E6C30B469`
- launcher `current/run_v104_port_royal_item_operation_capture.bat` —
  `6A90B11BCF9FE59AFCB73E6583688C4CCA4122409E74911BE40911B56BC7BFB4`
- package `packages/PF_Login_Game_Test_v104.zip` —
  `DC3F6B6253A5AB49020C726502DB3232AAC018F52E7F39A583B87B38B2449D83`

The corrected package contains exactly the binary, current V104 server, and
current launcher at the ZIP root. Each embedded SHA-256 matches its source.
Compile, self-test, exact captured-request decode, and Snappy response-frame
roundtrip all pass.

The pre-capture provisional ZIP is preserved, not overwritten, at
`packages/provisional/PF_Login_Game_Test_v104_pre_capture.zip` with SHA-256
`A183C8A61AAC185F53BAE7196704860FF324965A54AB0CAA410ED530CC406262`.

Verified checkpoint backup:

`backups/v104_item_operate_capture_20260814_111326`

The final manifest contains 164 entries with zero missing, length, or hash
mismatches. Manifest SHA-256:
`15645B9AACEA404E02FA819A13024B77D34DE7DDB906D2020D68A2753A091F73`.
