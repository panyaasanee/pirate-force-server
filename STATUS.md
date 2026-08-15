# Pirate Force Server — Foundation Status

Updated: 2026-08-15

## Baselines

- V140 remains the latest runtime-proven evidence checkpoint.
- V141 is closed as a legacy characterization baseline: packaged and deterministic
  offline self-tested, but not independently runtime-proven. It adds no new gameplay
  claim.
- Foundation work introduces no V142 protocol/gameplay hypothesis.

## Foundation gates

- Modular typed Python core: implemented.
- Migration-first SQLite with WAL, foreign keys, transactions, accounts,
  characters, opaque actor/avatar wire, sessions, soft-delete field, and position:
  implemented.
- Character Create -> List -> Select -> StartGame identity continuity: implemented
  in the real V141 dispatch adapter; unknown job/class bytes remain opaque.
- Commit-before-reply: implemented for character creation and selection.
- Golden/state/restart/loopback/legacy-dispatch verification: implemented.
- Generated deterministic source release: implemented and excluded from Git.
- Runtime UI verification: deliberately pending until all offline gates pass.

The legacy V141 source remains immutable and is loaded as a compatibility oracle.
Gameplay dispatch falls through to it unchanged outside the lifecycle boundary.
