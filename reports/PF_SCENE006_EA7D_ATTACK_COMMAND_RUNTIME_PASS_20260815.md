# SCENE-006 — EA7D target-bound attack-command producer runtime pass

Date: 2026-08-15

## Claim

The unchanged local client, after SCENE-005 hostile P60 selection, produces and
queues ActionVital action `0xEA7D` when the visible Fighting Fish soldier is
double-clicked.  The target tuple carries exact actor identity `0x203D`, and the
same ActionVital reaches the server wire.  This result repeated in a fresh client
and server session.

## Evidence

The checksum- and code-guarded observe-only probe intercepted exact generic
producer `0x44D260` and queue boundary `0x5DD800`.  In each run it recorded:

- action `60029` / `0xEA7D`;
- no optional position argument;
- opaque target dwords `[0x203D,0,0,0]`;
- scene 2 and finite heading/XYZ;
- one matching producer/queue pair on the same thread.

The first server trace carries ActionVital ID `0x1AEA` inside a two-vital
runtime request; the fresh trace carries the same ActionVital semantics inside
a six-vital runtime request together with movement records.  Both wires contain
qword target `0x203D` and action `0xEA7D`.  Tab selection alone produced
TargetVital but no ActionVital probe event.  The previously proven `0xEA7E`
remains WIELD/stow and is not reused.

The first probe file retains one superseded pre-input ASLR guard failure from the
initial attach attempt.  After the explicit PE HIGHLOW relocation correction it
records `probe_ready` followed by the accepted pair.  The fresh-session probe
starts cleanly with `probe_ready` and the same pair.

Both source database guards returned `PASS_UNCHANGED` for main, WAL and SHM.
Artifact paths, sizes and SHA-256 values are frozen in the adjacent manifest.

## Evidence ceiling

Proven: exact client producer/queue boundary for the target-bound `0xEA7D`
command, double-click gesture correlation against hostile P60, exact target
identity `0x203D`, matching server wire, fresh-session repeat, Tab-only negative
control, and unchanged persistence files.

Not proven: a server combat response, damage formula, FightAttr, animation
acceptance, hit/miss, range enforcement, cooldown, death, loot, AI, respawn,
skills, or authentic original-server faction assignment.  `0xEA7D` is promoted
only as the client attack-command producer for this controlled P60 scenario.
