# Pirate Force Server — Foundation Status

Updated: 2026-08-16

## Baselines

- V140 remains the latest runtime-proven evidence checkpoint.
- V141 is closed as a legacy characterization baseline: packaged and deterministic
  offline self-tested. A raw runtime capture exists but has not been formally audited,
  reported or promoted; V141 therefore adds no accepted gameplay claim.
- Foundation work introduces no V142 protocol/gameplay hypothesis.

## Foundation gates

- Modular typed Python core: implemented.
- Migration-first SQLite with WAL, foreign keys, transactions, accounts,
  characters, opaque actor/avatar wire, sessions, soft-delete field, and position:
  implemented.
- Atomic migrations with checksums, stale-session replacement and session-bound
  finite position checkpoints: implemented and negative-tested offline.
- Character Create -> List -> Select -> StartGame identity continuity: implemented
  in the V141 dispatch adapter across actor, AvatarAttr, ActorAttr and MovementAttr;
  unknown job/class bytes remain opaque.
- Commit-before-reply: implemented for character creation and selection.
- Golden/state/restart/loopback/negative/legacy-dispatch verification: implemented.
- Deterministic source archive verification: implemented and excluded from Git.
- A live assisted-UI run now proves Create -> commit -> List -> Select -> StartGame,
  a position checkpoint, client exit/relaunch, and reload of the same `Arena01`
  character and scene-1 position while the same server process remained running.
  Server-process restart/crash durability, delete, world-visible player name and
  authenticated multi-account ownership remain unproven.

## Test Arena V1

- Opt-in scenario `arena_v1_player_p30_target` is implemented and offline-tested.
- It preserves Full Flow, then replaces only the inherited first population with
  one test-only P30/Tornado Eagle at player-relative `+100X,+50Y`.
- The exact target profile retains template 31, identity `0x201F`, HP 3857/3857,
  and BasicAttr name `Tornado Eagle`.
- Arena V1 has an assisted GameClient runtime result. The client rendered one
  `Tornado Eagle` model, displayed HP 3857, and emitted the exact P30 TargetVital
  after click; more than 60 post-target runtime states continued with no error or
  disconnect marker.
- Hostile-monster classification is a runtime negative: the ordinary stable view
  used a green name, person target icon and talk cursor. A later controlled V2 exit
  burst reproduced the shutdown-only transition: immediately after exit confirmation
  the name became pink/red, the actor gained a red outline, and the talk cursor was
  replaced. This confirms teardown-specific UI change, not stable hostile gameplay.
- Arena V1 therefore proves object spawn/render/name/HP/click-target transport, not
  hostile relation, combat, AI, damage or loot.
- Combat, AI, damage, loot, Tab selection and authentic placement are nonclaims.

## Test Arena V2 runtime diagnostic

- Opt-in scenario `arena_v2_p30_basic_faction6_diagnostic` adds only the
  statically proven BasicAttr mask bit `0x0400` and its serializer-ordered u32
  value `6` to the Arena V1 P30 profile.
- Golden comparison proves the uncompressed V2 P30 differs from V1 only in the
  two mask bytes and one tagged u32 field. V1 and no-scenario behavior remain
  unchanged.
- An assisted GameClient runtime run sent the exact V2 initial packet and identical
  three-second reapply, then captured the exact P30 TargetVital after click. The
  run continued for more than 60 post-target heartbeats with empty stderr and no
  bad marker.
- The stable client presentation remained green/person/talk before and after the
  reapply. A separate controlled exit run captured about nine frames per second and
  reproduced a transition immediately after exit confirmation: pink/red name, red
  actor outline and a non-talk pointer. This is screenshot evidence of shutdown
  teardown behavior, not a stable hostile-relation pass.
- The stop rule has been applied: this candidate is retired without adding guessed
  FightAttr, AI, `+0x6C`, or local-player faction fields. The next evidence lane is
  recovery of the player's actual BasicAttr faction producer/value.
- Static tracing proves the current StartGame ActorAttr omits faction mask `0x0400`,
  so the client retains BasicAttr faction 0. Faction 6 does not list 0 as an enemy,
  which explains this negative. SCENE-005 later promotes value 1 only as a bounded,
  table-guided emulator hypothesis; it is not an authentic player-faction claim.
- Hostile relation, sword cursor, combat, FightAttr, AI, damage and loot remain
  unproven.

## Scene2 and first authentic population runtime

- Strict opt-in `scene2_load_only_marker2` projects the existing `Arena01` into
  Scene2 marker2 at `(26905,21185,1680)` without migration, session writes,
  checkpoints, or population. ActorAttr, MovementAttr and Teleport agree.
- Scene sequence 0 is compositional. Direction 8 has no proven heading mapping,
  so heading 0 is only the constructor fallback. Direct load is not travel proof.
- SCENE-001 runtime passed: the unchanged client loaded Prison Exile Island at
  marker2, returned the runtime-ready flow, and rendered the Scene2 environment.
  The camera initially intersected geometry but zooming exposed the avatar/world.
- SCENE-002 runtime partially passed: one authentic MOBS34/P60 Fighting Fish
  soldier rendered with its exact model/name at its authentic P60 position while
  the transient test player was placed 100X/50Y away. The database main/WAL/SHM
  guard returned `PASS_UNCHANGED` after close.
- SCENE-002 target selection failed: direct clicks and Tab produced no captured
  TargetVital while BasicAttr omitted HP and therefore left the actor at zero HP.
- SCENE-003 runtime passed the narrow liveness gate: relative to SCENE-002 it
  changes only BasicAttr mask `0x0701` to `0x070D` and inserts current/max HP
  `3857/3857` after the name. One direct click then emitted exact TargetVital
  kind 2 and embedded ChooseNPC for P60 identity `0x203D`. This proves HP/liveness
  controls target-selection transport for this actor. The value is a bounded
  level-27 diagnostic, not authentic MOBS34 spawn policy. Hostility, target UI,
  combat, AI, damage, death and loot remain unproven.
- SCENE-004 repeated the SCENE-003 scenario with explicit hover refresh: move the
  pointer off the actor, move it back onto the visible model, then click once and
  inspect before the next action. The first click emitted a 45-byte TargetVital
  for P60. After selection, a second off/on hover still showed the talk cursor and
  the next click emitted a 29-byte ChooseNPC for identity `0x203D`. This rules out
  stale-cursor and ground-click explanations for this run and proves the current
  actor enters the client NPC-style interaction path. It does not prove authentic
  player faction, hostile relation, attack, combat, damage, AI, death or loot. The
  main/WAL/SHM guard passed unchanged.
- SCENE-005 passed the relation boundary. Static parser proof identifies the
  `FACTION` table's `n_ID` and `s_ENEMY` columns; a guarded read-only lookup matrix
  showed current pair 0/6 is neutral and candidate 1/6 produces the opposite result
  symmetrically. Adding only StartGame BasicAttr mask `0x0400` plus u32 candidate 1
  made the stable P60 name/outline red, allowed Tab selection with a red target
  panel/arrow, and emitted exact 31-byte TargetVital kind 1 for `0x203D` with no
  ChooseNPC. DB guard passed unchanged. This proves the bounded relation composition,
  not authentic player faction, attack, damage, AI, death or loot.
- SCENE-006 passed the next narrow boundary. A checksum/code-guarded observe-only
  probe at exact producer `0x44D260` and queue `0x5DD800` showed that one
  double-click on the selected hostile P60 produces ActionVital `0xEA7D` with
  target identity `0x203D`. The same wire reached the server and repeated in a
  fresh client/server session; Tab-only selection produced no ActionVital, and
  both DB guards passed unchanged. This proves the target-bound attack command,
  not a combat response, damage, hit/miss, FightAttr, AI, death or loot.
- SCENE-007 passed the minimum no-damage server-response boundary in two fresh
  Port Royal sessions. The opt-in harness restores the persisted player to the
  exact V74 scene-1 start `(0,0,931)` and places P60 at the P144 beer-tray visual
  coordinates, so both render in the default camera frame after the first movement
  without camera rotation. After exact hostile TargetVital kind 1, each target-bound
  `0xEA7D` request received exactly one base ActionVital response. The response
  uses RuntimeRes v4/count 1 and omits the request's trailing TargetPos. Within its
  echoed 64-byte ActionVital body, only the zero performer qword changes to the
  persisted selected-player identity. Both clients remained
  responsive, the visible player/P60 HP stayed `100/100` and `3857/3857`, stderr was
  empty, and both database main/WAL/SHM guards returned `PASS_UNCHANGED`. A visible
  attack animation was not confirmed; this proves response transport/acceptance
  only, not hit, damage, FightAttr, AI, death, loot, skills or authentic faction.
- The launcher starts a detached database guard. After both client and server close,
  runtime acceptance additionally requires `PASS_UNCHANGED` for the main SQLite file
  and the exact pre-run existence/hash/size state of both `-wal` and `-shm`.

## Relation comparator instrumentation

- The capture-only Python/Frida probe passed an exact-client runtime trace. It
  refuses mismatched binaries using SHA/size/PE/code guards; Frida 17 pointer-read
  compatibility and one explicit ASLR relocation are regression-tested.
- It observes StartGame address `0x5DDC57`, comparator entry `0x43C380`, and the
  two bounded BasicAttr `+0x68` reads without writing memory, packets, or UI.
- The authoritative JSONL has 3,087 validated events. Stable sequences 1-1023
  each read `first=6` and `second=0` from the same two BasicAttr pointers. In this
  controlled single-P30 run, the injected P30 value 6 correlates to `first`, while
  the current StartGame/default value 0 correlates to `second`; this does not prove
  an authentic player faction or original-server policy.
- The paired server capture records the exact P30 TargetVital, reaches heartbeat
  78, and has empty server/probe stderr plus zero audited failure markers.
- After one exit confirmation, sequences 1024-1039 entered the comparator but
  exited before either `+0x68` read. The shutdown-only red/outline/pointer change
  is therefore an early-gate path that bypasses the faction comparison, not an
  observed faction mutation or stable hostility.
- The two earlier one-line initialization failures are retained as superseded
  diagnostics for the Frida 17 API and ASLR guard fixes. Authentic player faction,
  relation-table meaning, hostile gameplay and combat remain unproven.
- REL-002 adds a guarded read-only call of exact lookup `0x4A1D50` after proving the
  loader consumes `FACTION.n_ID` and `FACTION.s_ENEMY`. For target 6, symmetric
  opposite-result candidates within 0-31 are 1, 2, 3 and 18. This justifies candidate
  1 as the first bounded runtime hypothesis without claiming original-server policy.

## Local GameClient input bridge

- Personal plugin `pirate-force-input-bridge` is installed and exposes bounded
  timed key holds plus right-button drags for the single visible Pirate Force
  window. Key/button release is guaranteed in `finally` paths.
- A one-second held `E` action passed twice and visibly rotated the camera. The
  bridge enabled the SCENE-004 hover-refresh run without operator camera control.
  This is operational tooling evidence, not gameplay/protocol evidence.

The legacy V141 source remains immutable and is loaded as a compatibility oracle.
Gameplay dispatch falls through to it unchanged outside the lifecycle boundary.
The configured server token currently identifies one local test account. Authenticated
multi-account ownership, delete UI, world-visible character name, job/class semantics,
name uniqueness policy, inventory persistence and crash-time live capture remain later gates.
