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

V141 artifacts:

- source SHA-256 `2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22`
- launcher SHA-256 `6D8E410033E91D435BB3D65D3FECD02D93634C922B1D284440DEACF2FC0C5009`
- three-entry package SHA-256 `0572F476437E47302E3CD742239F56EFC96A90D7465F73C08EE77CB1EBAF1F00`

V141 is not described as runtime-passing until its existing raw capture is audited and promoted, or a new verified run is produced.
Foundation is not described as a durable server lifecycle until a later audited run
also proves server-process restart/crash recovery and the remaining state domains.
