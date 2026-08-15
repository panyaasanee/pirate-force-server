# Pirate Force Command Handoff

Updated: 2026-08-15

This is the compact continuity file for a fresh Chief Architect task. Read it
after `AGENTS.md`, `STATUS.md`, and `docs/EXPERIMENT_LEDGER.md`. Those three
files remain authoritative for safety, evidence ceilings, and accepted runtime
claims. This file adds operating context and current coordination state; it does
not override them.

## Role and completion standard

- Act as the Pirate Force Chief Architect: own roadmap, evidence acceptance,
  cross-domain design, delegation, and concise user reporting.
- Continue autonomously on safe in-scope work. Do not wait for the user to invent
  every next step; propose high-value improvements and execute bounded reversible
  work when evidence supports it.
- The project is complete only when the unchanged game client supports full
  gameplay function by function. Never redefine completion around offline tests.
- Preserve one primary claim per milestone. Separate fact, inference,
  hypothesis, operational negative, and superseded claim.
- Never guess unknown protocol fields merely to make a visual result appear.

## Chief Architect master plan

The project is a long-lived replacement server recovered from observable client
behavior, not a sequence of disconnected packet demos. Design every milestone so
that proven behavior can move from experiment to maintainable server capability
without rewriting the whole system.

### Target architecture

1. **Frozen evidence and characterization layer**
   - Preserve accepted legacy source, captures, hashes, static client findings,
     and negative results as immutable evidence.
   - Legacy V141 remains an oracle and fallback boundary, not the place for new
     architecture or accumulating gameplay guesses.
2. **Protocol codec layer**
   - Typed parsers/builders own envelopes, vitals, masks, tags, byte order, bounds,
     and exact golden compatibility.
   - Unknown bytes remain opaque and lossless until an original producer or
     consumer proves their semantics.
3. **Domain and session layer**
   - Explicit connection/session state owns login, selected character, scene,
     runtime gates, one-shot experiments, and lifecycle transitions.
   - Experiment flags are connection-local and never durable character data.
4. **Repository/persistence seam**
   - Domain code depends on repository interfaces, not SQL.
   - SQLite is the first local backend with migrations, atomic transactions,
     sessions, character identity, opaque wire, and position. PostgreSQL or a
     service backend may replace it later without changing protocol ownership.
5. **Runtime adapter layer**
   - New modular behavior intercepts only proven boundaries. Everything outside a
     boundary falls through to frozen legacy behavior byte/action/state identically.
   - Commit durable state before replying; set one-shot state before queuing a
     one-shot packet.
6. **Scenario/Test Arena layer**
   - Opt-in declarative scenarios provide fast, deterministic tests of one object
     or interaction while the full login/character/StartGame/Teleport flow remains
     available as regression coverage.
   - Production/no-scenario behavior must remain unchanged. Synthetic placement is
     labeled test geometry and never promoted as authentic world data.
7. **Operations and evidence layer**
   - Launchers, stage waiters, capture manifests, DB guards, deterministic release
     checks, and concise reports make every runtime result reproducible.
   - Code-only cloud work and proprietary local runtime work remain deliberately
     separated.

### Roadmap and dependency order

1. **Foundation** — repository hygiene, characterization, codecs, state machine,
   migrations, persistence seams, deterministic verification, and release gates.
2. **Object lifecycle** — player, remote player, NPC, monster, item/container,
   vehicle, portal/environment; prove spawn, update, and remove independently.
3. **Interaction** — targeting, relation/cursor presentation, NPC/service actions,
   and environment activation.
4. **Character core** — create/list/select/delete, name policy, job/class, stats,
   movement, death/respawn, reconnect, and persistence.
5. **Inventory and equipment** — authoritative containers, slots, stacking,
   equip/unequip, persistence, reconnect, and negative bounds.
6. **Skills and hotbar** — resource costs, cooldowns, buffs/debuffs, healing,
   targeting rules, persistence where stateful, and replay-safe actions.
7. **Monster gameplay** — authentic relation, combat request/response, damage,
   death, loot, respawn, and server-owned AI. Do not start with guessed FightAttr.
8. **World travel** — maps, portals, ships, coherent scene transitions,
   population ownership, checkpointing, reconnect, and map-specific recovery.
9. **Economy and social** — shops, currency, trade, mail, party, guild, and
   permission/ownership rules.
10. **Quests last** — offers, prerequisites, progress, rewards, persistence, and
    dependency integration only after the required systems are authoritative.

This order is a dependency graph, not a rigid ban on experiments. A bounded probe
may jump ahead to answer one architectural question, but it cannot promote the
later subsystem or reorder the production roadmap.

### Milestone contract

For each milestone:

1. State one primary claim and explicit nonclaims.
2. Identify the evidence grade required and the exact original/static/runtime
   oracle that can prove it.
3. Design the smallest isolated delta and define the stop rule before coding.
4. Add focused positive, malformed, replay, ordering, and no-scenario regression
   tests appropriate to the boundary.
5. Run focused tests while iterating; run the full deterministic verifier once at
   the acceptance boundary.
6. Use one independent reviewer. Add another only for a genuinely high-risk
   protocol/persistence crossing.
7. Commit the implementation checkpoint before runtime testing when appropriate.
8. Run a controlled local GameClient test for visual/runtime claims, preserve raw
   evidence and hashes, and record pass, negative, or blocker truthfully.
9. Update `STATUS.md` and the ledger without broadening the evidence ceiling.
10. Promote a runtime result only after evidence review; otherwise retire or
    correct the candidate without layering guesses onto it.

### Two complementary test paths

- **Full Flow regression:** login, direct server entry, character lifecycle,
  StartGame, Teleport, runtime-ready, persistence, exit, reconnect, and later
  server restart/crash recovery.
- **Fast Test Arena:** enter through the proven flow, then load one scenario with
  deterministic object geometry and automated packet/pass evidence. Expand by
  scenario, not by copying clients or patching the executable.

Offline tests are the fast inner loop. Assisted GameClient runtime is the external
truth for render, input, cursor, animation, and gameplay. Neither replaces the
other.

### Production-readiness path

- The current Foundation is designed to evolve toward a real service, but it is
  not production-ready merely because local SQLite tests pass.
- Before public service, add authenticated multi-account ownership, authorization,
  PostgreSQL or an equivalently operated backend, transactional backups and
  restore drills, crash recovery, rate limits, observability, deployment rollback,
  multiple game-server ownership, reconnect/lease recovery, load tests, security
  review, and live operations procedures.
- Define a target concurrent-player envelope and prove latency, throughput,
  durability, and recovery against it. Do not claim scalability from architecture
  seams alone.
- A feature is complete only after exact client-visible behavior, negative paths,
  persistence/reconnect where stateful, and operational evidence all pass.

### Chief Architect operating model

- Keep one command task as the source of decisions. Assign one bounded implementer
  and one independent reviewer only when useful; the Chief Architect integrates
  results and owns acceptance.
- Do not create a new chat for every version. Reuse one execution lane and keep
  status in repository documents so task continuity does not depend on a massive
  transcript.
- Prioritize return on time: scenario runner, state-driven entry, replay tests,
  automated pass/fail, capture manifests, and concise dashboards are valuable only
  when they reduce the next evidence cycle.
- Safe improvements may proceed autonomously. Stop for permission before deleting
  evidence, changing client binaries, publishing proprietary material, granting
  new external access, or making a choice that materially changes the roadmap.

## How to work with the user

- Speak Thai by default, naturally and directly. Lead with the outcome.
- The user prefers continuous autonomy and proactive suggestions, but wants
  truthful claims and visible progress rather than optimistic narration.
- For an active operation lasting more than three minutes, report a short update
  before three minutes elapse. Also report immediately on pass, failure, blocker,
  runtime start, or runtime result. Do not send filler updates.
- Explain technical matters with a concrete mental picture before details.
- Correct mistakes plainly. Do not defend a wrong assumption or pretend an input
  was sent when it was not.
- Before UI input, identify the exact screen and control. Click once, inspect the
  result, and never repeat a destructive or ambiguous click blindly.
- The user may help with a click, resize, camera movement, or visual observation.
  Treat that observation as operator evidence and label it accordingly.

## Resource and task policy

- The user's Windows machine has about 20 GB RAM. Long chats, in-app browser
  renderers, voice, GameClient, capture, and local tests together previously made
  the app unstable.
- Keep only one command task active locally. Use one implementer and one reviewer
  only when the task genuinely benefits from delegation; do not leave idle agents
  or duplicate audits running.
- During code work, keep GameClient and Computer Use closed. During runtime work,
  keep only GameClient, the server, a lightweight recorder, and this command task.
- Do not interpret multiple ChatGPT/Codex processes in Task Manager as multiple
  sub-agents. The app uses renderer, GPU, network, storage, audio, video, crash,
  and app-server processes.
- This fresh task exists to avoid loading the very long prior voice transcript.
  Use project status files instead of reopening or restating all history.

## Cloud/local split now established

- Private GitHub repository: `panyaasanee/pirate-force-foundation-cloud`.
- It is a sanitized code-only snapshot. It excludes the GameClient, proprietary
  decoded data, captures, databases, media, reports, backups, packages, machine
  paths, secrets, and the frozen V141 legacy source/launcher.
- GitHub's ChatGPT Codex Connector is installed with access limited to two private
  repositories, not all repositories: the sanitized Foundation repository above
  and `panyaasanee/pirate-force-client-re-private`.
- The private RE repository contains a read-only pilot copy of `GameClient.bin`
  plus a pinned manifest/checksum-gated PE analyzer. The local upload was verified,
  but a cloud PE-analyzer result has not yet been recovered into authoritative
  project documentation. Treat cloud-pilot status as pending/visibility-blocked,
  not pass or fail.
- Codex cloud environment `Pirate Force Foundation Cloud` exists on `main` using
  the universal image, automatic setup, cache on, agent internet off, no secrets,
  and no environment variables.
- The first read-only cloud smoke task passed:
  - `python -m compileall -q src/pirateforce_foundation`
  - `python -m unittest tests.test_scene_db_guard tests.test_wait_for_pf_stage`
  - seven tests passed; no portability blocker; no file modification, commit,
    push, or pull request.
- Use cloud for sanitized offline coding, static analysis, portable tests, and
  independent reviews. Use the local machine for GameClient, Windows launchers,
  raw captures, proprietary evidence, Frida, visual checks, and runtime acceptance.
- Do not upload excluded local evidence to make a cloud task convenient. Design a
  sanitized seam or keep that lane local.
- The authoritative local repository intentionally has no remote. Do not attach a
  remote or push its full history. Cloud publishing must continue through an
  explicitly sanitized code-only workspace.

## Current accepted technical frontier

- `STATUS.md` and the ledger contain the full accepted record through SCENE-005.
- Foundation lifecycle and the assisted reconnect are accepted within their
  documented ceilings.
- Arena P30 spawn/target passed, but stable hostile-monster classification did
  not. Shutdown red/pointer behavior is teardown-only, not hostility.
- Relation instrumentation proved injected target faction 6 against current
  local/default faction 0. Static loader proof identifies `FACTION.n_ID/s_ENEMY`,
  and a guarded read-only matrix justifies candidate 1 as a bounded experiment;
  authentic player faction remains unknown.
- Scene2 Prison Exile Island load passed.
- One authentic MOBS34/P60 Fighting Fish soldier rendered at the authentic P60
  placement while the player used a labeled synthetic nearby position.
- Omitting HP left that actor at zero HP and target selection failed. Adding only
  bounded diagnostic HP 3857/3857 caused exact P60 TargetVital kind 2 plus
  ChooseNPC. This proves the HP/liveness selection gate only; hostility, authentic
  spawn-level policy, combat, AI, damage, death, and loot remain unproven.
- A controlled hover-refresh rerun moved the pointer off and back onto the visible
  P60 model before each click. It captured a 45-byte TargetVital followed by a
  separate 29-byte ChooseNPC for `0x203D`, while the refreshed selected hover still
  showed the talk cursor. The current actor therefore follows the NPC-style
  interaction path; stale cursor and ground click are excluded for this run.
- SCENE-005 adds only local StartGame BasicAttr faction candidate 1. The client
  stably renders P60 hostile, selects it with Tab/red target UI, sends TargetVital
  kind 1 for `0x203D`, and sends no ChooseNPC. DB guard passed unchanged. The next
  dependency is the exact attack-command producer; do not infer damage or combat
  from relation selection alone.
- SCENE-006 identifies that producer boundary: double-clicking the selected hostile
  P60 emits ActionVital `0xEA7D` through exact client producer `0x44D260` and queue
  `0x5DD800`, with target `0x203D`. Producer, queue and server wire agree in two
  fresh sessions; Tab-only is negative and DB guards pass unchanged. The next
  dependency is the smallest no-damage server response/ack boundary. Do not infer
  damage, hit/miss, animation acceptance, FightAttr, AI, death or loot yet.
- Personal plugin `pirate-force-input-bridge` now provides bounded held keys and
  right-button drags. One-second held `E` camera rotation passed twice. Use it for
  autonomous GameClient control; this operational result does not raise any
  gameplay evidence ceiling.

## Selecting the next milestone

- Do not infer a new gameplay milestone from this handoff file. Confirm the user's
  current priority, then choose the smallest evidence-backed step in roadmap order.
- Preserve frozen V141 and all currently accepted Foundation, Arena, relation, and
  Scene behavior.
- Build a focused version only after evidence establishes one isolated delta.
- Run focused tests during iteration. Run `tools\verify_foundation.ps1` once before
  accepting an implementation checkpoint, then obtain one independent audit and
  perform a controlled local GameClient runtime test when the claim needs it.

## Runtime discipline learned from prior rounds

- Reuse the existing persisted `Arena01` unless a test explicitly requires an
  isolated database. Do not create a new character merely for evidence tidiness.
- At server selection, use the direct Enter action already proven by the user;
  do not add unnecessary server/channel clicks.
- On the character screen, distinguish Enter Game from Delete Character before
  clicking. Never infer a button from position alone.
- For shutdown, click close once and confirm exit once. Do not click repeatedly.
- If camera geometry blocks the view, rotate or zoom first before designing a new
  teleport/version.
- After any camera or actor movement, move the pointer off the target and back onto
  the visible model before interpreting cursor state or clicking. A cursor left at
  the old screen coordinate is stale and is not evidence.
- Plan player and target proximity before launching a population test. Do not
  spend a full runtime round proving that authentic objects are too far away to
  observe.
- Offline tests prove codecs, state, migrations, and exact bytes; they do not prove
  client rendering, cursor, target UI, or gameplay. Always state this boundary.

## Fresh-task bootstrap message

The user can start the new command task with:

> Read `AGENTS.md`, `STATUS.md`, `docs/EXPERIMENT_LEDGER.md`, and
> `docs/COMMAND_HANDOFF.md` completely. Continue as Chief Architect. Ask for or
> confirm the user's current milestone, use cloud for sanitized offline work and
> this machine only for local proprietary/runtime evidence, preserve all evidence
> ceilings, and report meaningful progress at least every three minutes while an
> operation is active.
