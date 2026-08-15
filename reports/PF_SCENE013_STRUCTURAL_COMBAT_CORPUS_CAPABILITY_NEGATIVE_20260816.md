# SCENE-013 — Structural combat-corpus capability negative

Date: 2026-08-16

## Claim

A deterministic, hash-guarded offline audit proves that the currently curated
structured evidence corpus cannot answer the missing original server-to-client
combat-result question. It does not prove that any combat packet is absent from
the real protocol.

## Method and guarded corpus

The audit freezes six unique logical evidence sources from v74-v76 and v81-v83.
Five are exact text files and one is an exact member of a hash-guarded ZIP. Each
source has exact size, SHA-256, direction and provenance in the checked-in config.
Duplicate logical IDs, paths or payloads, changed hashes, unknown directions and
unknown provenance are rejected.

The parser accepts only two anchored decoder forms:

- `STRUCTURAL_IDS [...] OUTER version=... mask=... count=... nested_version=...`
- timestamped `RECV frame=... pc_len=... ids=[...]`

Malformed anchored lines fail the audit. Hexdump lines, arbitrary byte sequences,
media and unstructured text are ignored. The files under `evidence/` are opened
read-only and never edited, moved or extracted onto disk.

## Deterministic result

The six sources contain 2,621 decoded frames:

- v74: 209
- guarded ZIP member `141904`: 113
- v76: 72
- v81: 681
- v82: 279
- v83: 1,267

Every source has direction `client_to_server` and provenance
`game_client_to_local_emulator`. Eligible frames require both direction
`server_to_client` and provenance `original_server_capture`; the eligible count is
therefore exactly zero.

Across all six client-direction sources, the audited combat-family counts are:

- TargetVital `0x1ADD`: 5
- ActionVital `0x1AEA`: 0
- CHitResult `0x16F7`: 0
- CFightMsgVital `0x29DC`: 0
- CKnockdownVital `0x3123`: 0
- CShotMissileVital `0x3E0F`: 0
- CMissileHitResult `0x3EE5`: 0

The generated JSON explicitly records
`no_eligible_original_server_to_client_frames=true` and
`bounded_target_negative=false`. The latter is essential: with zero eligible
frames, the zero packet counts are not a bounded original-server absence result.

## Evidence ceiling and stop rule

Exact offline fact: the six guarded logical inputs, their direction/provenance,
2,621 decoded-frame inventory and deterministic counts above.

Operational corpus capability negative: no currently curated decoded input has
the original server-to-client direction needed to recover a combat response.

Not proven: absence of CHitResult or any other packet from the real protocol;
EA7D response ordering; authentic payload values; animation; hit/miss/critical;
damage or HP mutation; range/cooldown; FightAttr; AI; death; loot; respawn; skills
or authentic faction.

Do not synthesize CHitResult, HP, UpdateAttr, FightAttr or another combat result
from these zero counts. Resuming this response lane requires either a lawful,
complete original server-to-client combat capture decoded at exact boundaries or
an exact server-side producer/data binding that fixes every serialized field and
flag. Static/read-only preparation in other roadmap lanes may proceed without
claiming this blocker is solved.
