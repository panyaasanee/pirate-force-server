# Pirate Force ServerProject — Agent Contract

This is the persistent workspace for the Pirate Force local-server reverse-
engineering and implementation effort.

## Paths and safety

- Project: `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject`
- Runtime client: `C:\Users\Panya\Desktop\Pirate Force\GameClient`
- Frozen/current experiments: `current\`
- Reports: `reports\`; backups: `backups\`; packages: `packages\`
- `references\` and `evidence\` are read-only. Never edit, move, rename or delete
  them. Copy an input elsewhere before deriving work.
- Do not clean old versions every iteration. Batch cleanup only after explicit
  approval, manifests and recoverable-path validation.
- Never publish proprietary client binaries, decoded game data, captures or private
  screenshots. Local Git is code-only and currently has no remote.

## Authoritative status

- Read `STATUS.md` first, then `docs/EXPERIMENT_LEDGER.md`.
- Read and follow `docs/WORKFLOW.md`; it is the canonical execution, Cloud/local,
  verification, audit, and documentation workflow. Older handoff prose cannot
  override it.
- V140 is the latest formally accepted runtime checkpoint.
- V141 is the immutable legacy characterization source used by the modular adapter.
  It is offline self-tested; a raw capture exists but is not yet formally audited,
  reported or promoted.
- Foundation code is under `src/pirateforce_foundation/` and introduces no V142
  gameplay/protocol hypothesis.
- Full historical narrative remains in `handoff.txt`, `reports/`, backup manifests,
  and Git commit `5c200e2`. Do not load all history unless the current question needs
  it.

## Current Foundation boundary

- Python remains the primary implementation language. Use typed modular code;
  consider Rust only after profiling proves a bottleneck.
- SQLite is the first persistence backend. Protocol/domain code depends on a
  repository seam; SQL stays in the adapter.
- Create, Character List, Select and StartGame must resolve the same persisted
  character identity. Actor, embedded AvatarAttr, ActorAttr and MovementAttr must
  agree.
- Persist opaque actor/avatar bytes losslessly. Do not assign job/class semantics to
  unknown AvatarAttr fields.
- The configured server token represents one local test account only. Authenticated
  multi-account ownership is not yet proven.
- World-visible player name, delete UI, job/class, inventory/equipment/skills
  persistence and crash-tested live lifecycle remain incomplete.
- Runtime experiment one-shot flags are connection-local and must never be persisted.

## Evidence rules

Classify every claim:

- A — exact original capture or exact static producer/consumer proof
- B — uninstrumented emulator runtime pass
- C — instrumented runtime trace
- D — compositional hypothesis
- E — operational negative

Never promote a broad claim from a narrower test. Preserve raw bytes and separate:
fact, inference, hypothesis, negative and superseded claim.

Protocol hypotheses may be used as a bounded escape hatch when static/original
evidence makes a candidate highly probable, the current lane is genuinely blocked,
or the evidence cost has become disproportionate. Every guessed value must be
labelled explicitly as a hypothesis, kept out of accepted baselines and production
claims, and paired with a concrete proof or falsification plan and stop rule.
Related hypotheses may accumulate across at most two or three experimental versions
when that is necessary to keep the investigation moving. At that boundary, prove,
retire or obtain explicit approval to extend them; do not let them silently become
accepted behavior. This exception does not permit rewriting V141 or overstating an
evidence grade.

Important retired claims:

- Quest action 1 is not an offer; it is client-local Accept_Run/tracker behavior.
- G is the Guild hotkey. WIELD/`เก็บอาวุธ` is HOTKEY 71 on Z; `0xEA7E` is not
  proven attack/combat/damage.
- V129 `Player.TeleportWithVehicle` reaches a native no-op; q3020 did not itself
  travel. V136/V137 transport is an explicit emulator-side composition.
- V130 equipment failed: signed slot -1 is rejected and CollectionBag/equipment-tail
  ownership is unresolved. Do not guess an absolute equipment slot.
- V132/V133 negatives do not justify guessed faction, FightAttr or AI fields.
- V140 P86 coordinates are a synthetic interaction harness, not authentic placement.

## Regression ceilings to preserve

The V141 legacy self-test preserves the accepted wire history, including V94
population, V97 default talk, V98 facing, V99 message, V100 music, V102 inventory
unlock, V111 stack merge, V119 P30 data, V120 Backpack range, V122 cash boundary,
V123 op5 capture, V128 WIELD capture, V131 docking confirm, V135 conversation,
V136 composition, V137 position ownership, V138 destination population and V140 P86
interaction. Passing a regression does not expand any historical evidence ceiling.

## Verification

Before accepting a material Foundation implementation change run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify_foundation.ps1
```

The verifier must cover legacy self-test, modular tests, malformed/negative paths,
migration atomicity/checksum, account/session isolation, deterministic archive,
forbidden Git paths and diff hygiene.

Use the T0-T3 tiers in `docs/WORKFLOW.md`: focused tests are the editing loop and
the full verifier runs once after a stable implementation diff. Docs-only wording
or evidence corrections do not require the full verifier unless they change an
executable contract, canonical ledger, release input, or verifier.

Do not combine an architecture migration with a new gameplay/protocol hypothesis.
One milestone has one primary claim and explicit nonclaims. Commit state before
queueing a success response; set one-shot state before queueing a one-shot packet.

## Git and artifacts

- Track authored source, tests, migrations, tools, concise docs and selected frozen
  legacy source only.
- Never track binaries, packages, backups, captures, databases, generated releases,
  decoded proprietary material or media.
- Generated release artifacts are never hand-edited.
- Normally use one implementation commit, one corrective commit only when a real
  finding requires it, then one runtime-result commit/tag. Do not manufacture
  audit/corrective cycles or rewrite frozen evidence history.

## Team and token economy

- `/root`: Chief Architect; owns roadmap, acceptance, cross-domain design and final
  evidence claims.
- Character Wire Audit: protocol/identity/order reviewer.
- Persistence Design: database/transaction/crash reviewer.
- Static RE/QA: client provenance, repository, release and documentation reviewer.
- Keep one active milestone and one implementer. Apply the risk tiers in
  `docs/WORKFLOW.md`: one independent reviewer is mandatory for high-risk work,
  targeted when useful for medium risk, and unnecessary for low-risk work. Review
  only a frozen diff; avoid duplicate or reassurance-only audits.
- Keep mobile status updates short. Use `STATUS.md` and the experiment ledger instead
  of repeating history. Write long reports only for major runtime pass/negative
  checkpoints.
- Default sanitized coding, portable tests, static analysis, and review to Cloud.
  Reserve local Windows for proprietary inputs, GameClient/runtime/instrumentation,
  Windows integration, and the final authoritative gate. Never duplicate Cloud and
  local execution without an explicit portability or integration purpose.

## Roadmap order

1. Foundation: characterization, Git, modular codecs/state, SQLite lifecycle.
2. Object lifecycle: player, remote player, NPC, monster, item/container, vehicle,
   portal/environment; spawn/update/remove.
3. Interaction: target/relation/cursor, NPC/service and environment activation.
4. Character core: create/list/select/delete, job/class, stats, movement,
   death/respawn and persistence.
5. Inventory and equipment.
6. Skills, hotbar, resource/cooldown/buff/heal.
7. Monster relation, combat, damage, death, loot and AI.
8. World travel, maps, portals/ships, population and reconnect.
9. Economy/social.
10. Quests last, after their dependencies are authoritative.

Completion requires function-by-function runtime evidence and persistence/reconnect
where stateful. The project is not complete until full gameplay works from the game
client; do not redefine completion around a passing subset.
