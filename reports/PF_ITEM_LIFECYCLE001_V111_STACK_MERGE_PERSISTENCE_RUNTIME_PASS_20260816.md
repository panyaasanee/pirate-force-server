# ITEM-LIFECYCLE-001 — exact V111 stack-merge persistence runtime pass

Date: 2026-08-16
Result: Grade B controlled runtime pass

## Primary claim

The typed Foundation persisted the one already accepted V111 Backpack transition
through an unchanged GameClient and projected that exact post-state after a fresh
client reconnect:

1. Round A StartGame contained the exact four-record initial Backpack once.
2. The client emitted the exact 36-byte V111 request
   `(operation=4,value32=0,item_identity=3)`.
3. SQLite committed only the allowlisted transition: identity 1 quantity changed
   from 1 to 2 and identity 3 was removed.
4. The server emitted the exact frozen 80-byte/91-byte response.
5. Round B reconnected without CreateActor or another ItemOperate request and its
   StartGame contained the exact three-record merged Backpack once.

The implementation under test is commit `f1cfbce`. Frozen V141 remained unchanged
at SHA-256
`2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22`.

Capture root:
`GameClient/capture_item_lifecycle001_25690816_172425`.
The adjacent manifest pins 16 retained artifacts.

## Exact wire evidence

Round A raw GAME is
`GAME_20260816_172756_032705_62087.txt`, 194,864 bytes, SHA-256
`B35EF7694E4946FFD31EC9A63948A19819009F477D2A783F48AAE722BFB6BE16`.

Its initial StartGame is byte-identical to the typed initial-state oracle:

- PC: 440 bytes, SHA-256
  `0F7E5C58B41EF075B4F89E573704C978B2B4921B45AA4D5AA0E3A436A03A86FA`;
- frame: 453 bytes, SHA-256
  `4136C81272E438493E36B61AA3675046DC6490E43F6730D4BE861A9C5C700891`;
- exact initial Backpack subwire: 159 bytes, SHA-256
  `B402FCF536BA5D0DED1E0038283FDED2C6B708C6522D0D799E6E17FB8EB5A448`,
  occurring once.

At local `17:30:39.266`, frame 75 carried the exact 36-byte request, SHA-256
`5659139FDB38D2BFFF748BC33EC8AB4686C914D08D2A59A6851DE62B158A0E5E`:

`12 6F 6E 14 00000000 08 00 0B 02 12 0100 12 ED4B 0B 00`
`0B 04 14 00000000 32 0300000000000000`.

The outer object is `GSCN_RunTimeProtocolReq` `0x6E6F`, version 0, mask 2,
count 1; the nested object is `ItemOperateVitalReq` `0x4BED`, version 0. The
retained raw contains exactly one such structural request.

The persisted Backpack timestamp is
`2026-08-16T10:30:39.278511+00:00`, equivalent to local
`17:30:39.278511`. It falls after the retained request receive at `.266` and
before the retained response send at `.288`. At `.288`, the server sent
`FOUNDATION_V111_ITEM_STACK_ID3_INTO_ID1_QTY2_COMMITTED`:

- PC: 80 bytes, SHA-256
  `4E69BB513A7AA40C585BBE18C3ABB8A5B3B21CFAFC5261622A4FF9679B0E7A4B`;
- frame: 91 bytes, SHA-256
  `A9899EB936AC562E6AC4F15D1DEE1AEA22076B8185CC93558232D21F9E1B1541`.

Both response objects are byte-identical to frozen
`make_item_operate_stack_merge_success`. The timestamp ordering corroborates the
offline transaction contract that commits before returning the success action.

## Reconnect projection

Round B raw GAME is
`GAME_20260816_173941_734734_49683.txt`, 169,695 bytes, SHA-256
`4CA426868A7C11C9954C354650CAA285C564C762F851AF183DDC7D68C13DC7AD`.
It contains zero CreateActor and zero ItemOperate structural requests.

The A and B Character List objects are byte-identical and match the typed
persisted-character oracle:

- PC: 253 bytes, SHA-256
  `8F92597B7FB8AEADB6506FDDC89EF0EA12ECF90CB90654F6AE74F4BC80D9DE6F`;
- frame: 265 bytes, SHA-256
  `57E2D0EB0355C449454F2A8DEF7AF3B2193F050DB6CFDF0F357CFC33676AA8FE`.

Round B StartGame is byte-identical to the typed merged-state oracle:

- PC: 405 bytes, SHA-256
  `DA7517267E73B93F10528B5C4CDB5E4EAB18E1E6660C106A53BB52350C4AC635`;
- frame: 418 bytes, SHA-256
  `5CAC58402E9B748301F37332AB48038DB4DE50AAC1123924D0A2F87E2A9307F6`;
- exact merged Backpack subwire: 124 bytes, SHA-256
  `5EAF82A73AAC460B74C25B451F246C85ED13ABB2C38C1447F479AF0F4458872D`,
  occurring once.

Replacing the one 159-byte initial Backpack subwire in Round A StartGame with
the one 124-byte merged subwire produces the complete Round B PC byte for byte;
framing that replaced PC produces the complete Round B frame byte for byte. The
35-byte reconnect delta is therefore only the persisted Backpack projection.

## Database allowlist

The immutable pre-run main database is 53,248 bytes/SHA-256
`2641F30BB8122BDE2F02CDC2095B867F934EEE2EBEE1C6D0F598B7A94B4C99F1`.
It contains migration versions 1 and 2 and no inventory tables. The immutable
final main database is 69,632 bytes/SHA-256
`819D12DBE963C56A80A0CD754EC965F88CB74D42CA4A400FAFE7274E8EB3B559`.
It adds migration 3 with exact source checksum
`E21A2F9E4C72A2A8F7200D3C9C44C8476DC2148CC909C138C1EB9F9C17C82531`.
Both databases return integrity `ok` and zero foreign-key violations.

The final Backpack header is exactly `(base_mask=255,base_identity=0,range_mask=1)`.
Its ordered ItemAttr rows are:

- identity 1, template 2600001, quantity 2, slot 0, raw bytes 0/255,
  detail-present 0;
- identity 2, template 2400901, quantity 1, slot 1, raw bytes 0/255,
  detail-present 0;
- identity 4, template 2200002, quantity 1, slot 3, raw bytes 0/255,
  detail-present 0.

There is no identity-3 row. Account, character, selector 0, `Arena01`, identity
`0x10010001:0`, 208-byte actor wire SHA-256
`DC16B24104E863D428B4BEF7F7CB47CCE8E5CB9FBF025AE36E558FA18704C66D`,
103-byte avatar wire SHA-256
`B8F3CBEBF0F7CCC071C3D4D46EF24BAF33DF2A2FEB87FA8CEF692D1551EC32C0`,
and the complete position row are unchanged. Every pre-existing session row is
unchanged.

Round A used selected generation-12 SID
`e48e23bc789e416084a36c0609dac9e7`, opened
`2026-08-16T10:27:56.011330+00:00` and closed
`2026-08-16T10:32:14.451428+00:00`. Round B used selected generation-13 SID
`1f1437a3d0574e578842e487ff7db709`, opened
`2026-08-16T10:39:41.708968+00:00` and closed
`2026-08-16T10:43:46.038172+00:00`.

The final retained WAL is zero bytes. The 32,768-byte SHM is an auxiliary
sidecar; the immutable main database and deterministic logical oracle carry the
accepted state claim.

## Runtime health and UI ceiling

Round A retained 107 runtime heartbeats and Round B retained 87. Both raw GAME
files have zero audited `Traceback`, `ERROR`, `BAD_MAGIC` or `PROTOCOL_ERROR`
markers. Client A/B stdout and stderr are all zero bytes.

The Chief directly observed Round A Backpack UI change from `4/40` to `3/40`
after the drag (operator observation; no screenshot retained). Computer-use
policy prevented entering the second-password PIN in Round B, so this checkpoint
makes no Round B UI item-count claim. Persistence after reconnect is proven by
the exact raw StartGame bytes and final SQLite state, not by a Round B UI view.

The Chief observed the live server console close both GAME logs and emit one
`[FOUNDATION] stopped`, but no server-console or server-exit sidecar was retained.
The PTY tool reported exit code 1. Therefore this checkpoint does not claim clean
server shutdown or process exit 0; that operational ceiling is separate from the
inventory pass.

## Artifact audit and evidence ceiling

The deterministic capture-local `audit_item_lifecycle.py` reads both database
snapshots with SQLite immutable/read-only mode, validates full typed A/B packet
parity, exact request/response bytes, the database allowlist and session closure,
and writes `item_lifecycle_oracle.json`. The adjacent manifest pins those files,
all six protocol logs, four empty client streams, and the four database artifacts.

This is a Grade B pass for one exact V111 stack-merge transition, its exact
committed persistence, and exact StartGame projection after one reconnect.
Transaction atomicity remains an offline implementation/test property, not a
runtime crash or concurrency claim. This result does not generalize item move,
split, drop, use, equipment, ownership, template meaning, container policy,
concurrency, authenticated multi-account use, crash or in-flight transaction
recovery. No new wire value or gameplay hypothesis was introduced.

The stop rule is met for this one transition. The next item milestone must begin
from another exact accepted producer/response/state boundary; it must not broaden
this result into a general inventory implementation.
