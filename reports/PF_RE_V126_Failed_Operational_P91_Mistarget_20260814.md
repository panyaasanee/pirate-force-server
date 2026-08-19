# Pirate Force RE — V126 failed operational P91 mistarget run

Date: 2026-08-14  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V126 was built as a capture-only boundary for the exact client-produced
`ActionVital 0x1AEA` version 0 after selecting isolated P30/Tornado Eagle
identity `0x201F` with `TargetVital` kind 2. The build and offline parser audit
passed, but this live session did not execute that test procedure. It is
preserved as failed operational/UI evidence and must not be described as a
positive or negative runtime judgment of the V126 ActionVital parser.

## What happened

The finalized event journal contains only three significant events:

1. Teleport at event 1/frame 9;
2. `TargetVital 0x1ADD` at event 2/frame 248 for P91 identity `0x205C`, kind 2,
   followed in the same two-vital collection by `ChooseNPC 0x205C`;
3. `TradeCmdVital 0x23B5` command 12/dword 0/no detail at event 3/frame 267,
   produced by closing the P91-triggered test shop.

The exact P91 target payload was:

`32 5C 20 00 00 00 00 00 00 08 02 12 B6 0F 0B 00 32 5C 20 00 00 00 00 00 00`

There are zero P30/`0x201F` target records, zero ActionVital records, and zero
`V126_GENERIC_TARGET_BOUND_G_ACTION_CAPTURED_NO_REPLY` milestones. Therefore
the P30 arm was never established and pressing G could not exercise the
focused capture gate.

The live log contains 11 `TargetPosVital` records. The final cluster at frames
308, 309, 310, 311, and 313 from `22:58:39.735` through `22:58:49.906`
corresponds to the observed accidental left-drag/ground relocation attempt.
Those position requests are an operational input mistake, not ActionVital or
combat evidence.

## Runtime health

The client/server session itself remained healthy:

- 411 successful heartbeat responses, ending at `23:02:14.824`;
- inbound runtime traffic continued through frame 415;
- zero match for `ErrorData`, VitalData mismatch/read failure, fatal,
  exception, traceback, disconnect, `28317`, or `SEND_FAILED`;
- server stderr is empty;
- clean closure flushed raw GAME to 388,128 bytes, live GAME to 101,995 bytes,
  raw LOGIN to 2,326 bytes, and server console to 95,144 bytes.

This health result confirms stable V125 behavior remained operational during
the failed procedure. It does not validate the new ActionVital runtime path.

## Interpretation and disposition

Keep this capture as explicitly labeled failed operational evidence. It
explains why no ActionVital milestone exists and prevents a later reviewer from
mistaking absence of a request for a parser/protocol failure. Do not promote
V126 to the passing current baseline and do not use this run to change any
ActionVital field hypothesis.

A repeat should use a fresh version/capture directory and a deterministic
P30-selection aid. Success still requires an exact P30 `TargetVital` arm before
one G action. The V126 capture should be archived outside the clean runtime
folder after backup rather than silently discarded.

## Artifact verification

The frozen V126 package contains exactly three files and its embedded hashes
match the current source and launcher:

- `current/pf_login_game_server_v126.py`, 254,283 bytes  
  `34CD0E9C34987970DA5AA211BC3AD6261E6082385F75899F1A3D0B448C6D62CD`
- `current/run_v126_port_royal_p30_generic_g_action_capture.bat`, 482 bytes  
  `4DB3E0C50AB277305E971D4F7B1816A6A97BCD601AF11A152726196203F46A6C`
- `packages/PF_Login_Game_Test_v126.zip`, 4,361,852 bytes  
  `DA38E4F261D8B7D41936E4FE9E4057A922A6C363558D37AA98F7AF0319D70418`

Flushed capture hashes:

- raw GAME: `87DA65F6BC90B06FE6CE0472FD0D9B6DF1FDBE3419A0550F61769A76FD20AC0C`
- event journal: `A4ED13DCEFDBD2ADDD202214E2B7DC2A1A2EE7AED2C43CE9BAE6C64BAA13DEBE`
- live GAME: `D0029861B948E80FBB293C46D6FA6B24501A80F486CFA1E420B05BE9E9E15B6F`
- raw LOGIN: `037C69499FD8A289257B5DF9583165EF4D6FAEC90A7FEDE2F93436A38B165587`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- server console: `B0F5C473221F7E9401B71B6EDADFE715D9CCF590168DB8936364D8016C09A112`

Verified backup:

`backups/v126_failed_operational_p91_mistarget_20260814_230341/`

The manifest covers all six flushed capture files plus the source, launcher,
and package: nine entries with zero mismatches. This report is preserved beside
the manifest. Manifest SHA-256:

`27C022DBE1A079219F52821FC6A947729317DE64A61592A36D173EB76DB27D38`
