# Pirate Force RE checkpoint — V133 P70 relation-display negative boundary

Date: 2026-08-15  
Client: Pirate Force TH 1.41.01132 / PatchVersion 132

V133 derives from frozen V132 as a focused reproduction of the strongest
preserved V74 cursor/selection candidate.  It sends one authoritative actor:
decoded Port Royal placement P70, template 71, identity `0x2047`, exact
coordinates `(2195.447509765625, 5700.166015625, 983.5487060546875)`, preset
`M001_001_000_SP2`, actor type 4, and exactly the V74 NPCAttr plus full
MovementAttr.  Direct construction tests prove its 78-byte NPCAttr, 55-byte
MovementAttr, and 152-byte actor entry are byte-identical to V74.  No relation,
FightAttr, ActionVital, AI, skill, or combat field was added.

StartGame placed the local actor at P70-100X on the same Y/Z with heading zero.
The isolated subject was therefore exactly 100 units on the local +X axis.
The stable zero-target Login Teleport and inherited bootstrap/inventory state
were preserved.  Population was sent at 0 seconds and reapplied at 3 seconds;
the one-shot Tab/SELECT_TARGET capture gate armed only after successful reapply.

## Exact live result

P70 spawned centered in front of the local character as the large red model
remembered from the V74-era scene.  It displayed no overhead title.  Hovering
the actor produced the TALK speech-bubble cursor and yellow inward-pointing
arrows.  The game screenshot does not capture the OS/game pointer, but it does
capture the yellow arrows.  This is a direct negative against the remembered
sword-cursor/red-arrow interpretation under the exact V133 state.

The population initial frame was sent at `03:12:28.846`; the exact reapply was
sent at `03:12:31.847`.  The capture gate armed at `03:12:31.850` with positive
oracle actor `0x2047`, TargetVital kind 2.  The user then pressed Tab after the
arm marker.  The fully flushed 211,142-byte raw GAME log contains:

- `TargetVital`: zero;
- `ChooseNPC`: zero;
- positive V133 P70 target marker: zero;
- runtime heartbeats: 172;
- final healthy empty RuntimeReq: frame 187 at `03:15:42.060`;
- ErrorData/version mismatch/SEND_FAILED/traceback/fatal/exception/disconnect/
  `28317`: zero across all six capture files;
- server stderr: empty.

The event journal contains only session start, the normal TeleportVital event,
and the P70 Tab-probe arm marker.  There is no post-arm significant request.

## What this proves

The V74 P70 actor attr wire and visual preset alone do not recreate the
remembered hostile/sword relation display in the later V133 session.  Under
V133's current local/global session state, the client classifies the actor for
hover presentation as TALK/yellow and excludes it from Tab's nearby-enemy
selection path.

This does not prove that V74 never displayed a sword cursor.  V74's raw GAME
evidence proves a TargetVital `0x2047`/kind 2 followed by two ChooseNPC requests,
but logs do not encode cursor graphics.  V74 and V133 also differ substantially
in local player/bootstrap/session history even though the P70 actor wire is
identical.  The next analysis must trace client comparator `0x43C380` and its
inputs before changing any BasicAttr/global field.  In particular, BasicAttr
mask fields at `+0x68/+0x6C` and the referenced global singleton state remain
unassigned semantics; do not guess a faction value.

V133 is negative evidence only.  Keep runtime-passing V131 as the passing
baseline and do not promote V133.

## Build and artifact verification

V133 passed `py_compile` and the complete inherited self-test.  Its exact
three-file package passed ZIP integrity and embedded-hash verification:

- `GameClient.local.bin`, 14,759,424 bytes  
  `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- `pf_login_game_server_v133.py`, 297,283 bytes  
  `AFC61A5A8C8A86BAFA95B3FE2277AF7233A95D545818B8531E1920FA9BC00A6A`
- `run_v133_port_royal_p70_v74_relation_repro.bat`, 481 bytes  
  `DDEDC9BFC06D6739CED54110AA6E80565F1D3D7D67B48696C3AA54E57B41B6EE`

Package: `packages/PF_Login_Game_Test_v133.zip`, 4,371,180 bytes  
SHA-256: `FF5DDF967A4555046741EAB2AF72AA04A3C3EEFF0584055D0CADE1B60BFA63BF`

Flushed capture hashes:

- raw GAME: `3943E72DEADB5461FECEFFC9A43D969944DC0B5C9255C22BA650DB507FDCFDD3`
- event journal: `217FA463A0747928ADA4DF56473DB7554B3537FB2D33BB52E85D02394BBE7397`
- live GAME: `61EB32063D5A282A0BAEED9FA7FEB0DA90BCE636E5431D509C02C1FEC3887E5B`
- raw LOGIN: `673DA98C82D046E375E0615D722F4E3A330C0761DE972804859466973B30A8DC`
- server console: `4C16B1A643BC61EE9605CE9105A73EF4DA0B1BFD4064138922F937B30B674EC6`
- empty stderr: `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`
- screenshot `20260815_031346.png`, 1,404,062 bytes:  
  `E085AD6AD1E3DB925FC5CE741B1724CEFEFFECDD9FAB60553A5BE1EB144DC364`

Verified negative checkpoint backup:

`backups/v133_p70_relation_negative_20260815_031748/`

The manifest covers six flushed capture files, the exact screenshot, source,
launcher, and package: ten entries with zero mismatches.  The report,
`handoff.txt`, and `AGENTS.md` are preserved beside it.  Manifest SHA-256:

`A2F4AB2F9AA8D865C5BDC7051F179C65D96A1B8C70D53A4FAFB2EAA66A50ABBE`
