# Pirate Force RE checkpoint — V121 to V122

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

This checkpoint continues
`PF_RE_V116_to_V120_Cash_Monster_and_Shop_20260814.md`. It proves the final
Buy request and a bounded cash-only `UpdateAttrVital` application. It does not
claim a complete or authentic shop purchase response.

## V121 — exact captured final-buy boundary

V120 captured two distinct store requests:

- cart activation: `TradeCmdVital 0x23B5 v0`, command 6, dword 0, one
  `ItemAttr` detail with identity 0, template 2200009, quantity 1;
- final Buy after confirmation: command 8, dword 0, no detail.

V121 corrected the earlier static dword-11 prediction and made the session
state explicit. It acknowledges only the exact command-6 Sword Soul tuple with
the already proven result-13 `Store_ByItemOK`, then journals one exact
command-8 request after that acknowledgement. Command 8, replays, malformed
tuples, and command 12 receive no response and do not mutate cash or inventory.

## Purchase-response audit

A full read-only audit scanned the project corpus from V2 through V121,
including packages, captures, history, backups, reports, and derived artifacts.
It found no authentic/prior-emulator inbound `UpdateAttrVital 0x309A`, no
`TradeItemResultVital` result 15 or 17, and no completed shop-purchase sequence.
The only matching trade result is the emulator-generated V120/V122 result-13
cart acknowledgement.

Static application code proves:

- incoming BackpackAttr through `UpdateAttrVital` replaces the visible primary
  item tree; a one-item delta would delete current identities 1, 2, and 3;
- a safe replacement must contain the complete current item set and matching
  identity collection;
- the client copies the server-supplied item identity and signed slot and does
  not allocate either;
- result 15 and result 17 both dispatch to the same `ResetBuyItem` handler, so
  the client cannot prove which one is the authentic success code;
- no capture proves the order of UpdateAttr versus TradeItemResult;
- Sword Soul declares `s_VARYDATA="43"`, but the exact purchased
  `ItemVaryAttr` wire remains unrecovered.

Therefore result selection, response ordering, new identity, destination slot,
and item-vary construction remain unsupported for a complete purchase.

## V122 — cash-only UpdateAttr boundary

V122 starts from frozen V121. On the first exact sequenced command 8 after the
exact command-6/cart-ack tuple, it sends one populated RuntimeRes v4 with the
required trailing `0B 00`. The nested vital is `UpdateAttrVital 0x309A v0`
containing exactly one full ActorAttr body. That ActorAttr is byte-identical to
the current state except for cash `10000 -> 0`.

V122 deliberately sends no:

- TradeItemResult result 15 or 17;
- BackpackAttr or ItemAttr;
- new item identity or slot;
- ItemVaryAttr;
- command-12 close response.

The exact cash response has decompressed PC length 89 and framed length 100.
Compile, exhaustive self-tests, Snappy roundtrip, exact-three-entry ZIP
verification, and embedded-file hash checks passed before deployment.

## V122 runtime result

The automated runtime test passed:

1. Port Royal bootstrap, population, PIN `1234`, and Sword Soul Shop opened.
2. Two catalog drags emitted no request. One right-click on Sword Soul was the
   runtime-proven activation gesture: it emitted exactly one command-6 request
   with dword 0, identity 0, template 2200009, and quantity 1.
3. Result 13 was accepted; Sword Soul appeared in the Buy cart with cost one
   gold.
4. Buy plus confirmation emitted exactly one command-8 request with dword 0 and
   no detail.
5. V122 sent exactly one 100-byte
   `V122_UPDATE_ATTR_ACTOR_CASH_10000_TO_0_ONCE` frame.
6. The HUD immediately changed from one gold to zero while the cart remained.
7. Clicking Buy again produced the client insufficient-cash behavior and no
   second command-8 request. This independently proves that the store predicate
   reads the updated ActorAttr cash value.
8. The session completed 175 heartbeat responses after the update with no
   version mismatch, `ErrorData`, fatal, exception, traceback, or disconnect
   marker.

The client rendered a white window after several normal close attempts. After
all evidence and the heartbeat window had been captured, only the verified
`GameClient.local.bin` process was stopped. The socket closure caused the
server to flush the raw GAME file successfully to 364,633 bytes.

## Preserved artifacts

Current files:

- `current/pf_login_game_server_v122.py`
- `current/run_v122_port_royal_cash_update_attr_boundary.bat`
- `packages/PF_Login_Game_Test_v122.zip`

SHA-256:

- package: `4A43C6841A9232A1119D43D90BB059530B2ED241F758B3C44D81D1A376752B9B`;
- server: `6E0FF61483B7E1A2B7964414BBE750DC158D7D5F52BCB9AE5A5EF153814F7090`;
- launcher: `B4E4BFD639A8099D8267BA8AC28E22FCABF87B2AF94E48F2AF41D0C0F5907011`;
- raw GAME: `1C7C50B7AD6A4AFDFB4BFA5174408CE35080590355C142B8187033ED91F9DF6D`;
- live event journal: `088F71C1FDBCB43CA67F57C7C655C08BC5DEDE758549923F7632EEAA6CE3DF15`;
- live GAME sidecar: `D3CD840E34C99E718049FFF43C4FDFD186BEF504D2BBEE6AD87F69101E48ACA8`;
- server console: `C1DAC1E5A3405FBD363E5C99FDC82D54DDD5311191621E39F046DC27256BADD6`.

Verified backup:

`backups/v122_cash_update_attr_boundary_20260814_203400/`

The backup manifest covers 9 runtime/source/package data entries with zero
mismatches. This report, the live handoff, and AGENTS.md are preserved beside
that manifest. Manifest SHA-256:

`38E42353849A8FBAD4782E5625E993752333BDDA223BF53911087778F7B3580C`

## Next evidence boundary

Do not describe V122 as a completed Sword Soul purchase. The next complete
purchase build remains blocked on authoritative evidence for all of:

- result 15 versus 17;
- UpdateAttr/TradeItemResult ordering;
- full four-item Backpack snapshot semantics, including preservation of the
  operational range flag;
- server-owned identity and slot allocation policy;
- the exact Sword Soul ItemVaryAttr body.

Progress may continue in another subsystem while these remain unresolved. If
shop work continues, prefer capture/static evidence over introducing any of
those five policy choices as authentic behavior.
