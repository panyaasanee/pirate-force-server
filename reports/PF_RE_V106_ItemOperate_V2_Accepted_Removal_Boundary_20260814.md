# Pirate Force RE V106 - ItemOperate v2 accepted, removal boundary

Date: 2026-08-14

## Outcome

V106 changed exactly one response-wire byte from V105: the nested
`ItemOperateVitalRes` version at PC offset 19 changed from 0 to the
constructor-proven value 2. The exact captured request gate and the complete
V105 response body were otherwise preserved.

The client accepted response ID `0x4C13` version 2. There was no VitalData
version-mismatch dialog, no `ErrorData=19475`, and normal runtime requests and
heartbeats continued after the response. This proves the response version and
handler-entry boundary.

It did **not** prove the proposed move response. Immediately after the response,
the item icon appeared transiently in slot 1 while the Backpack counter changed
from `1/40` to `0/40`. Closing and reopening the Backpack showed `0/40` and no
item in either slot. Therefore the V105/V106 body was processed as a removal (or
produced equivalent removal state), not as a persistent slot-0 to slot-1 move.
The exact meaning of request operation 4 and the response ItemBagAttr body must
be recovered statically before another field is changed.

## Controlled runtime evidence

Initial state was the proven V103 Adventure Key in Backpack slot 0 with counter
`1/40`. Exactly one drag was made from slot 0 to slot 1. It emitted:

```text
ItemOperateVitalReq id=0x4BED version=0
operation=4 value32=1 item_identity=0x0000000000000001
payload=0B041401000000320100000000000000
```

The request occurred at `2026-08-14T11:52:24.689` as GAME frame 87. The server
sent exactly one 91-byte response at frame 91, 0.6 ms late, under the V106 test
label. Frames after the response show the client continued its normal runtime
traffic. A case-insensitive scan of the final capture found none of:
`28317`, `mismatch`, `ErrorData`, `disconnect`, `fatal`, `Traceback`,
`Exception`, or `AssertionError`.

Final capture hashes:

- `GAME_20260814_114904_869804_60358.txt` - 97,020 bytes, SHA-256
  `2E3A5EF12286E638F9559D6A6BE1675566B8C90FC16B976353511B2A623E3327`
- `GAME_LIVE.txt` - 32,079 bytes, SHA-256
  `62B8BD42C2883FDA94E2274EEF4B4F0319A6CDEE369FB97F66CB260F4D7B3E0E`
- `GAME_EVENTS_LIVE.txt` - 821 bytes, SHA-256
  `56076A4C5CC7F78AE60EBB961C886EFC90B345E88677142EF138C1A786242FA6`
- `LOGIN_20260814_114705_342039_55703.txt` - 2,326 bytes, SHA-256
  `8B97FEDD8CDF1F20D343550A7E4D2291B54DEA8B00D5A67E066C07737AFE1ACE`
- `server_console_live.out.txt` - 32,259 bytes, SHA-256
  `ABEF3FEA249139987D7DBC96B6C12C96A5E9CA4241F40D2D88688680B4C8C9AF`
- `server_console_live.err.txt` - 0 bytes, SHA-256
  `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`

The game was closed normally through its own exit confirmation. The exact V106
server process was then stopped after its command line and capture output were
checked.

## Exact V105 to V106 wire delta

The nested PC payload length remains 80 bytes. The only byte difference is:

```text
offset 19: 00 -> 02
```

V106 PC payload:

```text
129D6E140000000008040B0212010012134C0B0208000B010BFF3200000000000000000F01003201000000000000001441AC27000F01000F0100080008FF0B000F010032010000000000000008000B00
```

This isolates acceptance of nested response version 2 from every body field.

## Static boundary for the next version

Do not reinterpret this as evidence that slot 1, result 0, identity 1, or the
standalone ItemBagAttr encoding is correct for a move. Before V107, recover at
least one of the following from executable code or an additional exact UI
request capture:

1. the operation enum meaning for request byte `4`;
2. the semantic role of request `value32=1`;
3. whether `ItemOperateVitalRes` carries a bag snapshot, a delta/removal set, or
   another operation-specific structure;
4. which code path constructs a true move request, if drag-to-slot is not one.

No alternate result, bag mask, owner, identity, quantity, slot, or affected-list
value is justified yet.

## V106 artifacts

- source: `current/pf_login_game_server_v106.py`
- source SHA-256:
  `DC0ECF6D52313DE0CA7960B3D2074F29E99278C12ED904183646B6856A6A7D2E`
- launcher: `current/run_v106_port_royal_item_move_response_v2.bat`
- launcher SHA-256:
  `1FB9FC86268EF8859FF24E4C9846B9A308A18D665C75058924708EBF8EFF4221`
- exact-three-file package: `packages/PF_Login_Game_Test_v106.zip`
- package SHA-256:
  `43A204C189973F945D4CAA78978581D05CFE4329302B8C304AEBFFF06B75371D`

The ZIP contains exactly `GameClient.local.bin`,
`pf_login_game_server_v106.py`, and
`run_v106_port_royal_item_move_response_v2.bat`. Source compilation, project
self-test, Snappy checks, ZIP integrity, exact entry count, and embedded hashes
were verified before runtime testing.

Verified checkpoint backup:
`backups/v106_item_operate_v2_removal_boundary_20260814_120216/` with 22
manifest entries, zero verification mismatches, and manifest SHA-256
`ED3994230D63C9156AA5FFE7CF24899D0617F9849A04EFF35B87F29E52F4D090`.
