# Pirate Force Server — Foundation Status

Updated: 2026-08-15

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
  which explains this negative. No original-server capture proves the authentic
  player faction, so value 1 remains forbidden as a guess.
- Hostile relation, sword cursor, combat, FightAttr, AI, damage and loot remain
  unproven.

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

The legacy V141 source remains immutable and is loaded as a compatibility oracle.
Gameplay dispatch falls through to it unchanged outside the lifecycle boundary.
The configured server token currently identifies one local test account. Authenticated
multi-account ownership, delete UI, world-visible character name, job/class semantics,
name uniqueness policy, inventory persistence and crash-time live capture remain later gates.
