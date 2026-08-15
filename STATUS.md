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
- Runtime UI verification remains pending; no durable live-lifecycle claim is made.

The legacy V141 source remains immutable and is loaded as a compatibility oracle.
Gameplay dispatch falls through to it unchanged outside the lifecycle boundary.
The configured server token currently identifies one local test account. Authenticated
multi-account ownership, delete UI, world-visible character name, job/class semantics,
name uniqueness policy, inventory persistence and crash-time live capture remain later gates.
