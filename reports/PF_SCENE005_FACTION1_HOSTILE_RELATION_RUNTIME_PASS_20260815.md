# SCENE-005 — faction-table-guided hostile relation runtime pass

Date: 2026-08-15

## Outcome

Static producer/consumer proof identifies client table `FACTION` fields `n_ID`
and `s_ENEMY`. A guarded read-only Frida call of the exact relation lookup
`0x4A1D50` then mapped faction 6 against candidates 0-31. Candidate 0 returned
the existing neutral result; candidates 1, 2, 3 and 18 returned the opposite
result symmetrically. Candidate 1 was selected as the first bounded experiment.

The isolated Scene2 runtime changed only the local StartGame BasicAttr by adding
mask bit `0x0400` and canonical u32 value 1. The Fighting Fish soldier retained
faction 6, identity `0x203D`, HP `3857/3857`, model, name and placement from
SCENE-004.

In stable gameplay the client rendered a pink/red name and red outline. Pressing
Tab selected the actor with a red target arrow and red HP target panel. The client
sent exact 31-byte `TargetVital` kind 1 for `0x203D`:

`12 6F 6E 14 00 00 00 00 08 00 0B 02 12 01 00 12 DD 1A 0B 00 32 3D 20 00 00 00 00 00 00 08 01`

No `ChooseNPC` accompanied this selection. SCENE-004 had produced kind 2 plus
`ChooseNPC`, so the relation-controlled NPC interaction defect is resolved for
this bounded scenario. The SQLite main/WAL/SHM guard is `PASS_UNCHANGED`.

## Artifacts

Authoritative capture directories:

- `GameClient/capture_scene2_fish_p60_hp3857_20260815_184551`
- `GameClient/capture_scene2_fish_p60_hp3857_player_faction1_20260815_185147`

The frozen three-entry manifest is
`reports/PF_SCENE005_FACTION1_HOSTILE_RELATION_RUNTIME_PASS_20260815.manifest`.

- Relation matrix JSONL: 9,758 bytes, SHA-256
  `14F8E5AAD02B45C0D632D282C47AACF300360BCEE19CCD9926AA88D518888996`
- Runtime server log: 32,820 bytes, SHA-256
  `FECE98A56607981A4C31FFCADE4BE273F51A33C969012E296BC2DA1FD8F0CB63`
- DB guard result: 1,398 bytes, SHA-256
  `303B8109FD1992FA4E417337612C4B12628D0728578D176FF0EC829FA9AA0913`

## Evidence ceiling

Proven: exact-client FACTION lookup behavior for bounded IDs 0-31, isolated
player-faction-1 transport, stable hostile presentation, Tab selection,
`TargetVital` kind 1, absence of `ChooseNPC`, and unchanged persistence files.

Not proven: faction 1 as the authentic original-server player faction, generic
faction policy, attack command, damage, FightAttr, skills, AI, death, respawn or
loot. Candidate 1 remains an explicit emulator-side relation composition until
an original producer or capture proves authenticity.
