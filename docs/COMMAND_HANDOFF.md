# Pirate Force Command Handoff

Updated: 2026-08-16

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
- Read `docs/HYPOTHESIS_LEDGER.json` before adding or inheriting any guessed
  value. Every value must be registered with falsification and a stop rule,
  remain non-production, and be proved, retired, or frozen after at most three
  related versions. No current entry has extension approval. A future approval
  is valid only when it names exact ledger IDs and an approved-through
  checkpoint. SCENE-005 faction 1 and the SCENE-007 acknowledgement are frozen;
  do not add another dependent version to either or any expired entry.

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

The canonical hypothesis ledger verifier is part of the deterministic gate.
Run it directly with `py -3 tools/verify_hypothesis_ledger.py`; never edit an
emitted hypothesis in source without updating the ledger in the same governance
checkpoint. Synthetic geometry always remains `authentic=false`.

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

- CHARACTER-NAME-001 closes the static/offline local-player name projection.
  Create now rejects noncanonical names and any mismatch between the supplied
  name and exact CreateActorDataEx prefix wstring without rewriting opaque wire.
  Create/List retain that actor wire; StartGame emits persisted `Character.name`
  only through ActorAttr low-mask `0x01000000` at wstring `+0x164`, after the
  existing cash field. Exact `NameBoardPlayer` update `0x5BD320` consumes that
  field at `0x5BD4D5..0x5BD512`. Do not use BasicAttr `+0x28` for this claim;
  it belongs to NPC/other UI lanes.
- CHARACTER-NAME-002 supplies the controlled runtime proof. Exact StartGame raw
  bytes carry actor identity `0x10010001`, unchanged BasicAttr mask `0x070C`,
  ActorAttr low/high masks `0x01000800/0`, mandatory bool `1`, cash `10000`, and
  one tag-`0x48`/14-byte UTF-16LE `Arena01`. The Chief directly observed `Arena01`
  over the selected local player in Port Royal, separate from the target panel;
  the client remained responsive and DB guard was `PASS_UNCHANGED`. No screenshot
  was retained, so keep the visual fact attributed to the direct UI observation.
  This does not prove remote-player names, rename/uniqueness policy, authenticated
  ownership, or server-process restart durability.
- FND-006 proves one bounded server-process restart. Round A started existing
  `Arena01` at scene 1/seq 0 `(-9239.95703125,-2830.045166015625,186)`, heading 0;
  a single click-to-move gesture produced TargetPos updates and committed final
  checkpoint `(-9192.125,-2674.037109375,186)`, heading `5.009882926940918`.
  After the Round-A process/listeners stopped, Round B expired lease generation 6,
  opened generation 7, and fresh Select/StartGame emitted the exact checkpoint
  while preserving selector 0, identity `0x10010001:0`, name `Arena01`, and opaque
  actor/avatar blobs. The Chief directly observed minimap `-9192,-2674` and world
  name `Arena01` in the client UI (operator observation; no screenshot retained).
  Do not call this graceful or crash-safe: Round A Ctrl+C ended with
  tool exit 1 and no stopped marker; Round B console-control attempts failed and
  validated server PID 328 was terminated by Stop-Process under the stop rule;
  generation 7 remains open. Next durability work must prove clean server shutdown
  and session closure separately before crash recovery.
- FND-007 separately proves the normal GAME-disconnect lease close. Session
  `aeee8c26bef046cfa0a8958579d7f68d` was open at generation 6 with selected
  character 1 before the Chief directly observed the UI-confirmed client exit
  (operator observation), then the same SID gained exact
  `closed_at=2026-08-16T05:54:24.102133+00:00` immediately after the GAME socket
  ended. Its scene-1 position and update timestamp were not rewritten. The exact
  Python server PID remained alive and ports 10188/10189 remained listening after
  disconnect (operational observation; no netstat sidecar retained), so this is a
  connection-local result rather than a startup-expiry effect. Do not call server
  shutdown graceful: Ctrl+C still failed, validated PID 12228 required force-stop,
  and the PTY ended exit 1. Next operations work is clean server-stop handling;
  abrupt client loss, process crash recovery and concurrent-client isolation still
  need controlled runtime evidence.

- `STATUS.md` and the ledger contain the full accepted record through SCENE-010.
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
  dependency was the smallest no-damage server response/ack boundary.
- SCENE-007 now passes that response boundary twice. The opt-in Port Royal harness
  restores the V74 scene-1 player start and reuses the P144 beer-tray visual position
  for P60, putting both in the initial camera without rotation. Each exact hostile
  kind-1 target followed by `0xEA7D` receives one RuntimeRes v4/count-1 ActionVital
  response and omits the request's trailing TargetPos. Within the echoed 64-byte
  ActionVital body, only performer zero changes to the persisted selected identity.
  Clients stay
  responsive, visible HP remains unchanged, stderr is empty and both DB guards pass.
  No clear attack animation was observed, so the next dependency was the smallest
  evidence-backed downstream action-consumer boundary.
- SCENE-008 closes that consumer boundary. A guarded observe-only trace shows the
  exact SCENE-007 ACK reaching the ActionVital handler, constructing a generic
  `0xEA7D`/`0x203D` action with null implementation and terminal bit `8`, entering
  the selected actor's `+0x20` queue once, and reaching the first common update
  return with bit `8` unchanged. The clean probe exits independently while the
  client remains alive; server heartbeats continue and DB main/WAL/SHM remain
  unchanged. The next evidence lane must recover a distinct server response/action
  code with an actual client implementation or original combat provenance. Do not
  invent HP, UpdateAttr or FightAttr packets, and do not infer animation, hit,
  damage, AI, death, loot, skills or authentic faction from this inert lifecycle.
- SCENE-009 identifies a distinct exact inbound consumer without inventing a
  response. Static registration/serializer/handler proof fixes `CHitResult` at
  Vital ID `0x16F7`. Its bounded reaction-implementation path requires record
  bit0+bit3, no bit4, a resolved target and non-null factory result, then reaches
  preparation for the target actor's `+0x40` queue. Other record fields remain
  opaque; record `+0x08` is not proven damage. The corrected guarded probe emitted
  only `probe_ready` during one exact hostile target -> EA7D -> SCENE-007 ACK
  window; the server continued heartbeats and the DB stayed unchanged. Treat the
  absent event as an operational negative only. Do not send a CHitResult until an
  authentic payload, natural trace or exact producer/data binding fixes every
  header/record scalar and flag.
- SCENE-010 closes the BEHAVIOR-registry lookup boundary. Exact identity and
  population proof follows `0x4162A0 -> 0x47BFC0 -> 0x491650`, loads table
  `BEHAVIOR`, stores row `n_ID` at entry `+0x04`, and populates named behavior
  fields plus the `s_HIT_KEYFRAME`/`s_HITBACK` vector at `+0xE4`. The guarded
  numeric lookup probe observed key `0xEA7D`
  returning null twice at exact producer/control
  return `0x44E92A` and once at exact inbound ActionVital-handler return `0x7517B5`.
  The latter followed the SCENE-007 acknowledgement by 18 ms. Static control flow
  shows that null takes the default branch but generic action construction/queue
  remains available. The probe
  exited zero, stdout/stderr were empty, heartbeats continued until controlled
  close and DB main/WAL/SHM were unchanged. The prior ACHIEVEMENT correction is
  superseded: `0x705000` populates a separate singleton at `0x102DB68`, while this
  lookup uses `0x102DAD8`. Do not infer an exact action/ScriptB row mapping, add a
  synthetic EA7D behavior entry, or send CHitResult/HP/UpdateAttr/FightAttr. The
  observed null is instant-scoped; `0x48D870` returning null for the same EA7D is
  an A+C composition, not an observed CHitResult. Next safe lane: observe natural
  BEHAVIOR population/lookup and correlate a natural CHitResult without writes.
- SCENE-011 observes natural BEHAVIOR entry storage without changing gameplay.
  The accepted guarded run records key 97 non-null at static caller `0x48D2C8`,
  keys 278/279 non-null at `0x7555D2`, EA7D null twice at `0x44E92A`, and key 0
  null twice at `0x7555D2`. Keys 278/279 both carry only the exact source-named
  dwords `n_AMOUNT_TARGET=1`, `n_RANGE=75`, `n_DAMAGE_AREA=200`, `n_PROFIT=0`,
  `n_THENDO=278`, `n_CLASS=0`, with one `0x38`-stride record in the proven `+0xE4`
  vector. Do not reinterpret `n_DAMAGE_AREA` as damage, radius units or HP change;
  the probe did not read the vector record. The paired flow had no TargetVital,
  therefore no strict SCENE-007 ACK, and proves no inbound response or CHitResult.
  Runtime exit was zero, stderr/stdout empty, heartbeats healthy and DB unchanged.
  Next lane must observe a natural consumer or naturally correlated CHitResult;
  do not synthesize a BEHAVIOR row or result packet.
- SCENE-012 must be treated as a stopped runtime-instrumentation lane. Exact
  static code proves that EA7D at `0x44EB1D` enters `0x4758D0`, combines an
  unknown live object scalar with the mode-0 BEHAVIOR selection, squares that
  threshold, and returns true only when it is strictly greater than live squared
  XYZ separation. SCENE-011 supplies natural raw `n_RANGE=75` for keys 278/279,
  but not the other live inputs, so do not compute a guessed result from server
  coordinates. The result-only probe captured one exact callsite `gate_enter`
  and then a duplicate-gesture error; no return event exists and exit was 1.
  The earlier TargetVital-kind1 -> EA7D -> one-shot ACK control predates the
  probe and must stay separate. DB remained unchanged and transport continued
  until client close. Do not add another internal hook, send a packet or claim
  gate result/range/attack/hit/damage. Continue with a structured offline search
  for a complete original/natural inbound combat-result envelope; if none exists,
  record a bounded corpus negative and require a lawful original-server capture.
- SCENE-013 has already audited the complete curated structured evidence set that
  can be guarded without raw-byte scanning. Six unique logical sources produced
  2,621 decoded frames, but every source is GameClient -> local emulator and none
  is an original server -> client capture. The generated result intentionally
  reports `no_eligible_original_server_to_client_frames=true` and
  `bounded_target_negative=false`. Five TargetVital IDs exist across the client
  direction; ActionVital and the CHitResult/CFightMsg/knockdown/missile families
  are zero in that same bounded inventory. Do not describe this as absence from
  the protocol and do not widen the corpus with unguarded raw-byte searches.
  Resuming the missing combat-response lane requires a lawful original inbound
  combat capture or an exact server-side producer fixing every field. Until then,
  continue only static/read-only preparation that does not invent combat values.
- SKILL-001 records the first safe static preparation beyond the blocked combat
  response lane. `TriggerCastSkillVital` is exact at class ID/hash `0x5CD2`, codec
  `0x600A60` and consumer `0x601810`; the codec exposes only raw `(u16,u8,u32)`
  fields. With singleton `0x1032EC4` present, the consumer prepares a possibly
  null candidate and uses exact submission edge `0x601880 -> 0x449110`; with no
  singleton it skips that edge, while every branch returns true.
  A reviewed observe-only probe is committed, but it has no live result. Direct
  xrefs expose factory/prototype paths and the virtual consumer only, not a proven
  UI/hotkey producer. `CSkillAttr` (`0x1661`) remains optional and absent in the
  accepted StartGame; present-empty is valid and its record payloads stay opaque.
  LearnSkillResult population and RevertSkill key removal do not prove entitlement
  or level semantics. `CStartCooldownVital` (`0x4DDA`) updates a separate cooldown
  container from raw `(s16,f32)` records, with no exact key edge to either prior
  class. Do not synthesize any of these packets/attrs. Resume only with a natural
  observe-only occurrence or an exact named producer/data binding.
- JOB-001 audits the character-creation class-preset boundary without changing the
  character model. Exact client code loads `CHARCREATE_CLASS`, whose guarded frozen
  rows use `n_ID` keys `{1,2,4,16,32}` and contain starter appearance, equipment
  and `s_SKILL_*` preset columns. Existing CreateActor `test01` numerically matches
  row-1 starter chest/leggings/weapons, but no exact table-key setter reaches a
  transported CreateActor/AvatarAttr/ActorAttr offset. Do not name CreateActorDataEx
  `+0x18` as class: it is zero in the capture while the matching preset key is one.
  Preserve all Avatar bytes losslessly and opaquely. Resume only after a named-key
  setter/copy chain and matching List/StartGame consumer are exact.
- DELETE-003 closes only the nested-object producer boundary. Exact UI paths
  construct `DeleteActorVital` raw operation values 1 and 2 and submit both through
  generic `0x4011A0 -> 0x5DD800`; no exact static edge proves the outer protocol
  class/version/mask/count, response, list refresh or repository mutation. The
  isolated `DelTst01` UI run was cancelled at the observed confirmation dialog;
  no screenshot was retained, no `0x36DB` appears in the retained logs, and the
  isolated main/WAL/SHM DB guard is `PASS_UNCHANGED` with `deleted_at=NULL`.
  Treat that as a no-request/no-mutation operational negative, not a delete pass.
  Do not name op 1/2, implement an outer parser/response/delete path, or perform a
  final affirmative UI action without fresh action-time confirmation.
- HOTBAR-001 establishes only the exact structural codec and client-consumer
  boundary for `SetItemOnParticularHotKeyPosVital`. Registration stores the
  deterministic name hash `0xE0AC` at `0x10820A4`; getter `0x5E4A40` reads it.
  Do not conflate this with `0x5E4AE0`, which is a method of the following
  `LoginVerifyVital` vtable and reads `0x1081FC0`. The proven wire is raw
  `(u32,i8,i8)` through codec `0x5E6DE0`; consumer `0x5EFAF0` calls client-state
  method `0x5C5080` with logical arguments `(raw +0x14 u32, sign-extended +0x18,
  sign-extended +0x19 - 1)`. Pool/prototype constructors do not prove a direct UI
  producer. No field semantics, item/skill discriminator, persistence/reconnect
  path or StartGame state is proven. Do not synthesize the vital; resume only
  with an exact producer/submission edge or natural observe-only occurrence.
- COMBAT-BIND-001 proves the bounded EA7D BEHAVIOR-selection ceiling. Static
  `0x755540` mode 0 retains the first non-null `n_RANGE` and rejects later values
  greater than or equal to the current value. With accepted SCENE-011 lookup
  order `0,278,279` and equal raw `n_RANGE=75`, key 278 supplies 75 and key 279
  is skipped. The selector returns only scalar 75, not the key. The inbound
  ActionVital lookup at `0x7517A5 -> 0x702A10` separately uses object `+0x30`,
  exact EA7D in the accepted shape. Value 2200002 has zero literal occurrence in
  both exact client profiles and no source edge here; never call it equipped,
  owned or weapon-bound. Stop this lane: no echoed IDs, row insertion, ActionVital
  alteration, CHitResult/HP/FightAttr synthesis, hook expansion or packet test.
- COMBAT-KNOCK-001/BIND proves a separate static consumer boundary only.
  `CKnockdownVital` consumer `0x750700` resolves the receiver actor; concrete
  path `0x47CAD0 -> 0x48D270 -> 0x702A10` uses raw object `+0x20` as a BEHAVIOR
  key. Raw `+0x24` is stored at inner implementation `+0x50`, while `+0x34` is
  discarded. Success creates a wrapper with vtable `0xF0F7DC` and flags
  `0x40000005`. Wrapper bit `0x40000000` selects the actor `+0x40` lane through
  `0x4843F0`; the `0x4A0C90` queue invocation receives a separate argument `1`.
  No direct non-framework writer,
  EA7D/278/279/CHitResult binding, HP/FightAttr/UpdateAttr mutation, visible
  animation or packet shape is proven. Treat the class name as role provenance
  only. Do not synthesize it; resume only from original S2C evidence or an exact
  producer assigning every field. SCENE-013 is not static-consumer exhaustion.
- COMBAT-KNOCK-DATA-001 retires the asset-name binding branch. The exact frozen
  expanded `B_CONSTDATA_TH.pc_.dec` BEHAVIOR table has 2,279 rows/30 columns.
  Rows 278 and 279 share the reported numeric values but have different source
  animation/keyframe strings. Ten row IDs contain `KNOCK`, 106 rows have a
  non-empty `s_HITBACK`, and zero source strings contain `REACTION`. These names
  do not select a `CKnockdownVital +0x20` value. Accepted SCENE-011
  `vector_count=1` for both rows is structural only; do not infer vector content,
  animation, hit, damage or response ordering. Keep the current packed client
  asset separate: it was hash/size guarded but not parsed by this checkpoint.
  Static code continues to prove only `+0x20` as the BEHAVIOR key, `+0x24`
  stored at inner `+0x50`, and `+0x34` discarded. No direct non-framework writer
  was found; an indirect/original producer remains possible. Stop asset-name
  mining and resume only with original S2C evidence or an exact producer that
  assigns every field. Do not synthesize a row ID or packet.
- Personal plugin `pirate-force-input-bridge` now provides bounded held keys and
  right-button drags. One-second held `E` camera rotation passed twice. Use it for
  autonomous GameClient control; this operational result does not raise any
  gameplay evidence ceiling.

## Selecting the next milestone

- The user has explicitly delegated milestone design and set monster combat as the
  current priority. Continue autonomously with the smallest evidence-backed step;
  ask only when new authority, destructive action or a major roadmap change is needed.
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
