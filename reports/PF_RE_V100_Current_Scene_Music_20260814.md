# Pirate Force V100 current-scene music control

Date: 2026-08-14

## Outcome

V100 preserves the passing V99 system message and all V94/V97/V98 behavior,
then sends one constructor-default `MusicControlVital`. The client accepted the
packet without a runtime protocol error and continued its normal request
stream. The local population regression also passed after one TargetPos tap.

## Evidence and wire

- protocol ID: `0x3EAF`;
- constructor: `0x5E4800`, vtable `0xF300A4`;
- constructor makes the ANSI string at `+0x14` empty and sets `+0x30 = 1`;
- serializer `0x5E60D0` writes ANSI string then tag `0x08`/u8 mode;
- handler `0x5F06D0` proves mode 1 plus empty string follows the client's
  current-scene/local-music-data branch.

Payload is therefore exactly `astr_tag("") + u8tag(0x08, 1)`. It is enclosed
with the V99-proven trailing RuntimeRes v4 derived mask. No track name, music
ID, or unknown field is supplied.

## Runtime result

At `2026-08-14T02:39:22.908` the server sent
`V100_MUSIC_CONTROL_CURRENT_SCENE`, frame size 39. The client then continued
empty runtime requests and server-setting traffic, proving parsing/dispatch did
not abort. The V99 system message remained visible and the nearest-20
population appeared after TargetPos.

Runtime backup:
`backups/v100_runtime_music_20260814_024150/`

## Verification

- Python compile: PASS
- project self-test: PASS
- exact constructor-default MusicControl wire: PASS
- Snappy roundtrip: PASS
- live client acceptance/no error dialog: PASS
- continued runtime request stream: PASS
- V99 message regression: PASS
- V94 population regression: PASS

Package: `packages/PF_Login_Game_Test_v100.zip` (exactly three files)

SHA-256: `DDC3BFABD342A7C502E35DE6EBD07430887DFA342DAE1A7A9A8795BFA05E86C3`

