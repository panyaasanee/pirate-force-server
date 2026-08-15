# Experiment ledger

| ID | Classification | Result | Evidence ceiling |
|---|---|---|---|
| V140 | Runtime evidence checkpoint | Pass | P86 synthetic-harness interaction transport/UI only; all AGENTS.md nonclaims remain |
| V141 | Legacy characterization | Offline pass | Source/launcher/package consistent; raw capture exists but is not formally audited/reported/promoted |
| FND-001 | Architecture | Pass | Modular lifecycle/persistence only; no protocol hypothesis |
| FND-002 | Character lifecycle | Offline pass | Create/List/Select/StartGame share identity across actor/Avatar/ActorAttr/MovementAttr |
| FND-003 | Restart/loopback | Offline pass | Session-bound position and identity survive DB reopen; exact projected frames round-trip locally |
| FND-004 | Corrective audit | Offline pass | StartGame Teleport restored; malformed/replay/account/lease/migration negatives pass |
| FND-005 | Assisted client reconnect | Runtime pass | Arena01 Create/List/Select/StartGame and scene-1 position survive client exit/relaunch against the same running server; server-process restart is unproven |
| ARENA-001 | Test Arena P30 object spawn/target | Runtime pass / classification negative | One P30 renders with name and HP and emits TargetVital; stable UI remains green/person/talk, so hostile relation and combat are unproven |
| ARENA-002 | BasicAttr faction-only diagnostic | Runtime transport pass / classification negative | Exact faction-6 transport/TargetVital pass; stable UI stays green/person/talk, while a frame burst proves pink-red/red-outline/non-talk UI only after exit confirmation, so the candidate is retired and teardown is not hostility |
| REL-001 | Relation comparator instrumentation | Runtime trace pass | 1,023 stable comparisons read injected P30 operand 6 against current local/default operand 0; 16 post-exit entries bypass both reads, so teardown UI is not an observed faction mutation; authentic player faction/policy remain unknown |
| SCENE-001 | Scene2 marker2 load-only | Runtime load pass | Existing Arena01 was read-only projected coherently in ActorAttr/MovementAttr/Teleport at `(26905,21185,1680)`; the client loaded and rendered Prison Exile Island and returned runtime-ready traffic; seq0/heading0 remain compositional |
| SCENE-002 | Authentic MOBS34/P60 single population | Runtime render pass / target negative | Fighting Fish soldier rendered with exact name/model at authentic P60 while the test player used a labeled synthetic 100X/50Y offset; DB main/WAL/SHM stayed byte-identical; clicks/Tab produced no TargetVital, so targetability/hostility/combat remain unproven |
| SCENE-003 | MOBS34/P60 HP liveness diagnostic | Runtime target-selection pass | SCENE-002 plus only mask `0x0701`→`0x070D` and canonical current/max HP `3857/3857` caused one click to emit exact P60 TargetVital kind2 + ChooseNPC; HP/liveness controls this selection gate, while 3857 remains a bounded diagnostic rather than proven spawn policy |
| SCENE-004 | P60 hover-refresh interaction characterization | Runtime pass / hostile-relation negative | Explicit pointer off/on refresh produced P60 TargetVital on the first model click; after selection the refreshed talk cursor persisted and the next model click emitted exact 29-byte ChooseNPC for identity `0x203D`. This excludes stale cursor and ground click for the run and proves the present actor follows the NPC-style interaction path; hostile relation/combat remain unproven. DB guard: `PASS_UNCHANGED` |
| REL-002 | FACTION lookup matrix | Static producer/consumer + guarded read-only runtime pass | Client loads `FACTION.n_ID` and `s_ENEMY`; exact lookup `0x4A1D50` maps target 6 against IDs 0-31. Candidate 0 retains the neutral result; 1, 2, 3 and 18 produce the opposite result symmetrically. This selects candidate 1 for a bounded test, not as authentic player faction. |
| SCENE-005 | P60 faction-table-guided relation composition | Runtime hostile-relation pass | StartGame adds only BasicAttr `0x0400`/u32 candidate 1. P60 becomes stably red/outlined, Tab-selectable with red target UI and emits exact TargetVital kind 1 for `0x203D` with no ChooseNPC. The SCENE-004 NPC interaction defect is resolved within this scenario; attack/damage/AI/death/loot and authentic player faction remain unproven. DB guard: `PASS_UNCHANGED` |
| SCENE-006 | P60 target-bound attack command | Static producer/consumer + repeated runtime pass | Guarded producer `0x44D260` and queue `0x5DD800` plus two fresh runtime wires agree that double-clicking selected hostile P60 emits ActionVital `0xEA7D` with target `0x203D`; Tab-only emits no ActionVital and both DB guards pass unchanged. Server response, damage, hit/miss, FightAttr, AI, death and loot remain unproven. |

V141 artifacts:

- source SHA-256 `2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22`
- launcher SHA-256 `6D8E410033E91D435BB3D65D3FECD02D93634C922B1D284440DEACF2FC0C5009`
- three-entry package SHA-256 `0572F476437E47302E3CD742239F56EFC96A90D7465F73C08EE77CB1EBAF1F00`

V141 is not described as runtime-passing until its existing raw capture is audited and promoted, or a new verified run is produced.
Foundation is not described as a durable server lifecycle until a later audited run
also proves server-process restart/crash recovery and the remaining state domains.
