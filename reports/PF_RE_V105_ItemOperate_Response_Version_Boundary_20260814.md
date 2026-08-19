# Pirate Force RE V105 - ItemOperate response version boundary

Date: 2026-08-14

## Outcome

V105 answered the one exact V104 request tuple `(operation=4, value32=1,
item_identity=1)` with the statically recovered `ItemOperateVitalRes` body.
The client recognized the response protocol ID `0x4C13`, but rejected the
nested VitalData header before processing the body. It displayed:

`VitalData version mismatch --- ErrorData=19475`

Decimal 19475 is exactly `0x4C13`. The Adventure Key remained in Backpack slot
0. After the dialog, the game stopped returning runtime requests and became
unresponsive during normal closure, so the exact GameClient process was stopped
after the capture files had been preserved. The raw GAME and LOGIN logs flushed
successfully.

This result does **not** reject the ItemBagAttr body hypothesis. It proves that
the V105 nested version byte was wrong and that the client did not reach the
response deserializer/handler.

## Runtime evidence

The controlled drag again emitted exactly:

`ItemOperateVitalReq id=0x4BED version=0 operation=4 value32=1 item_identity=1`

The server then sent exactly one response labeled:

`V105_ITEM_OPERATE_MOVE_ID1_SLOT0_TO_SLOT1_SUCCESS`

The live server log records that response immediately after request frame 131.
The client continued receiving server heartbeats, but ceased sending its normal
runtime requests after the mismatch dialog. No second drag or alternate tuple
was attempted.

Capture files:

- `GAME_20260814_112953_207669_49855.txt` - 71,419 bytes, SHA-256
  `1BA0F4C712A6DDCF25AF4A31FF3A4714DB5079BB251DE838E9B50E77A91FBC10`
- `GAME_LIVE.txt` - 23,863 bytes, SHA-256
  `D80F1C86CD8118A1F4950015F4DFEBD192690977D1933ACA56AE69912BFD71C1`
- `GAME_EVENTS_LIVE.txt` - 824 bytes, SHA-256
  `AFD5049663401686C6515CAB11F187C155795A452DB78E9CC715E13A2FC20BD8`
- `LOGIN_20260814_112849_889182_49680.txt` - 2,326 bytes, SHA-256
  `5148914410001B76E788F790FE8BCB665CC9DD5A571C279E646A01DB91E1543F`

The capture directory also retains the first launcher attempt's empty stdout
and Python path-quoting error. That attempt never reached protocol testing. The
launcher was corrected before the runtime session above.

## Static cause

The ItemOperateVitalRes constructor region supplies direct evidence that the
class version is 2:

```asm
005EBF0A: mov byte ptr [esi + 0x10], bl
...
005EBF10: mov dword ptr [esi], 0xf30668
...
005EBF3E: mov byte ptr [esi + 0x10], 2
```

The base portion initially clears the object version at `+0x10`, then the
derived ItemOperateVitalRes constructor overwrites it with constant 2. V105
incorrectly emitted nested version 0. This exactly explains the runtime dialog
and is not an inferred or guessed correction.

Preserved excerpt:
`derived/v105_item_operate_res_version_proof.asm`.

## Focused V106 boundary

V106 may change only the nested ItemOperateVitalRes version from 0 to 2. It must
preserve the exact V105 response body, exact request tuple gate, initial V103
Backpack, login/bootstrap, password response, and all unrelated runtime bytes.

Success requires all of the following:

1. no VitalData version mismatch dialog;
2. Adventure Key visibly moves from slot 0 to slot 1;
3. closing and reopening the Backpack preserves the client-side slot 1 view;
4. runtime requests/heartbeats continue without 28317, disconnect, fatal, or
   exception evidence;
5. logs flush and package/backup verification pass.

If the body is rejected after version 2, preserve V106 and continue static
analysis from the exact new error boundary. Do not vary result, ItemBagAttr,
affected-list, template, identity, quantity, or any unknown item field in the
same build.

## V105 artifacts

- source SHA-256:
  `3CE2D43CB62A96A8736EADF88330EB458DD19762A3DA6EF7747EE4DFFD7030BE`
- launcher SHA-256:
  `16A04F6A251D4E580AC713458D6BF4986CB5BDD7AD96A1B23033C0A6BE53D60F`
- exact-three-file package:
  `packages/PF_Login_Game_Test_v105.zip`
- package SHA-256:
  `968B395F91E1764CDAABA9F58FC810963D6789E261B54C105852B638E5E49935`

The ZIP contains exactly `GameClient.local.bin`,
`pf_login_game_server_v105.py`, and
`run_v105_port_royal_item_move_response.bat`; each embedded SHA-256 was verified
against the source file.

Verified checkpoint backup:
`backups/v105_item_operate_version_boundary_20260814_114147/` with 22 manifest
entries, zero verification mismatches, and manifest SHA-256
`660B8C8473228F55216D766DCB0E3D6820E290D4D60A9F619E92B3FE1BA76A42`.
