# Pirate Force V102 second-password response and inventory unlock

Date: 2026-08-14

## Outcome

V102 preserves the complete V101/V100/V99/V98/V97/V94 behavior and adds one
evidence-backed response path for `CheckSecondPwdVital` (`0x4B98`). Direct
handler analysis proves result byte 1 is the accepted/OK branch. V102 therefore
returns result 1, constructor-default u32 zero, and an empty ANSI string. The
client accepted the response and opened its authentic empty Backpack UI.

This is the first verified usable inventory shell: the general bag displayed
`0 / 40`, the secondary section displayed `0 / 0`, and the existing client UI
showed its category tabs, empty grid, and three zero-valued currencies. No item,
slot, template, quantity, password persistence, or unknown attribute field was
invented.

## Static proof: result meanings

`CheckSecondPwdVital`:

- ID `0x4B98`;
- constructor `0x4E5150`;
- vtable `0xF1A780`;
- object size `0x38`;
- serializer `0x5E6060`;
- handler `0x5F05B0`.

The serializer fields are u8 at `+0x14`, u32 at `+0x18`, and ANSI string at
`+0x1C`. The handler's direct branches map result 1 to the UI literal `OK` and
result 2 to `Fail`. The related `ChangeSecondPwdVital` handler maps result 1 to
`OK`, result 2 to `CurrentPwdInvalid`, and result 3 to `NewPwdError`. These
literal-bearing branches remove the ambiguity left at the V101 checkpoint.

Relevant derived evidence:

- `derived/v101_second_password_static_objects.txt`
- `derived/v101_second_password_serializers_handlers.asm`
- `derived/v101_second_password_full_vtables.asm`
- `derived/inspect_pe_static.py`

## Exact runtime wire

The captured client request remained byte-identical to V101. Its 64-byte
decompressed payload was:

```text
12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12
98 4B 0B 00 08 00 19 00 00 00 00 44 20 00 00 00
37 44 30 31 34 45 35 34 31 41 46 41 41 34 33 32
36 37 43 41 38 30 42 43 43 42 43 33 46 44 36 42
```

V102 returned this 34-byte decompressed response:

```text
12 9D 6E 14 00 00 00 00 08 04 0B 02 12 01 00 12
98 4B 0B 00 08 01 19 00 00 00 00 44 00 00 00 00
0B 00
```

The final `0B 00` is the mandatory derived field of populated
`GSCN_RunTimeProtocolRes` v4 established in V99. The response does not echo the
captured digest and does not claim that a password was stored server-side.

## Runtime verification

The clean V102 session used:

- `capture_v102/GAME_20260814_093734_168720_58850.txt`
- `capture_v102/LOGIN_20260814_093645_443999_64847.txt`
- `capture_v102/GAME_EVENTS_LIVE.txt`

Observed sequence:

1. state-driven fast entry reached Port Royal;
2. V99's online message and the preserved local-world behavior remained active;
3. clicking the bag opened the authentic second-password prompt;
4. four test keys produced the already-proven uppercase client digest;
5. the server sent `V102_CHECK_SECOND_PASSWORD_OK`, 44 framed bytes, with
   measured sender lateness 0.3 ms;
6. the authentic Backpack window opened immediately at `0 / 40`;
7. normal runtime heartbeats continued through sequence 84;
8. the game was closed normally and both raw logs flushed.

The final game log contains no case-insensitive match for ErrorData 28317,
error, exception, fatal, traceback, disconnect, or connection reset.

## Verification

- Python compile: PASS
- project self-test: PASS
- captured-request assertion: PASS
- exact 34-byte response assertion: PASS
- response does not echo digest: PASS
- Snappy roundtrip: PASS
- live bootstrap/client acceptance: PASS
- authentic Backpack UI opened: PASS
- V99 message and prior population/conversation paths preserved: PASS
- normal raw-log flush: PASS

Runtime/static backup: `backups/v102_inventory_unlock_20260814_094550/`

Package: `packages/PF_Login_Game_Test_v102.zip` (exactly three root files)

SHA-256: `D3273F1F6C0B56685816D4F55DBF099B586E6759D6BB34736B80F9A8620CCBCB`
