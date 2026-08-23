# Pirate Force Server — Foundation Status

Updated: 2026-08-23

Execution is governed by `docs/WORKFLOW.md`: one active milestone, Cloud-first
sanitized work, Local-only proprietary/runtime work, tiered verification,
risk-based audit after a frozen diff, and concise evidence documentation.
Every actual server invocation must now show a visible Foundation console while
mirroring summary stdout/stderr to deterministic per-run files; raw packets remain
file-only. Hidden/background-only server runs are no longer accepted.

AI-provider transfer is governed by `docs/AI_TRANSFER_HANDOFF_20260817.md` and
`docs/AI_WORKSPACE_LEASE.json`: use the existing canonical worktrees only, allow one
active executor, and never create a competing clone/worktree/project directory.
One correction when reading that dated handoff: its section-10 "full
authoritative local gate" (`tools\verify_foundation.ps1`) is superseded — that
script cannot pass; the acceptance set `AGENTS.md` declares is the gate.

## Functional coverage

`docs/FUNCTIONAL_COVERAGE.json` is the canonical, machine-readable record of what
each domain can actually do. `tools/verify_functional_coverage.py` runs inside the
full verifier and rejects `domain_complete=true` while any required capability is
short of `complete`. A narrow fixture, golden, or single controlled run earns
`runtime_pass` at most; it never closes a domain.

- **Inventory: INCOMPLETE** — next missing behavior: `occupied_destination_policy`.
  The generalized free-slot move earned `runtime_pass` via GT-002 (first
  real-client acceptance at HEAD `55c7c59`, opt-in scenario only,
  `production_allowed` still false). Occupied-destination policy, split
  stack, and use/drop/sell are not started; equip/unequip and stack limits are
  characterized but unimplemented.
- **Session lifecycle: INCOMPLETE** — next missing behavior:
  `concurrent_multi_client`. Visible console, requested-stop clean exit, character
  select through scene entry, session-row persistence and abrupt-loss recovery are
  each `runtime_pass` on single-client runs; concurrent clients and authenticated
  multi-account access control are not started. Client-requested logout
  (`clean_logout`) is `in_progress`: the HYP-PF-012 echo ack is wire/DB-proven
  (close-before-ack confirmed on the real client in GT-007) but GT-007 falsified
  the echo-only shape at the client-observable layer — the client neither returns
  to character select nor closes itself, so a content-bearing response shape is
  the next hypothesis.
- **Movement: INCOMPLETE** — next missing behavior:
  `local_player_movement_authority`. Scene-entry placement, NPC gait, authoritative
  scene-actor streaming and one teleport transport are `runtime_pass`; the server
  accepts client-reported positions without any validation, and no remote player's
  movement has ever been projected.
- **Combat: INCOMPLETE** — next missing behavior: `damage_and_hit_result`, which is
  blocked on evidence rather than code: a hash-guarded audit proves the curated
  corpus cannot answer the server-to-client combat-result question, and the client
  image proves the client computes no damage at all. Target selection, the
  attack-command producer and the action acknowledgement are `runtime_pass`, but
  the acknowledged action is inert. `hp_death_and_respawn` earned `runtime_pass`
  via GT-019 (attended, 2026-08-19) **on the death half only**: current HP at zero
  plus the dying timer is enough for the real client to derive a death by itself
  and open a rescue window, repeated eight times in one session. The respawn half
  has no evidence of any kind and GT-021 is the first test that touches it. Mob AI
  and PvP are not started.
- **Character management: INCOMPLETE** — next missing behavior:
  `character_creation`. Character list projection and the persisted player name are
  `runtime_pass`; `character_deletion` joined them via GT-018 (attended,
  2026-08-19) on one controlled observation — a one-character list, one delete
  answered by an acknowledgement plus a `SelectActorVital` rebuild, after which the
  row left the list and the character-select buttons became usable again — while
  slot reuse stays headless-only and the multi-character and negative paths are
  untested. Creation still stops at a characterized boundary, the second-password
  gate is an opt-in test-only bypass, appearance is preserved only as opaque bytes,
  and progression is not modeled.
- **Chat: INCOMPLETE** — next missing behavior: `client_chat_input`. The
  server-originated system message is observed, emitted by the frozen legacy seam
  rather than owned by a Foundation module. One client chat request is now
  captured — an undecoded 34-byte vital `0xAC52`, absent from the v141 registry
  and since resolved to `Channel_LocalTalkMessageVital` by the project names
  table (RESOLVE-001), that nothing dispatches or answers — and routing,
  persistence and moderation are not started.
- **NPC interaction: INCOMPLETE** — next missing behavior:
  `quest_accept_and_progress`. The conversation handshake and one operation/action
  docking sequence are `runtime_pass`; quest state, shop transactions, and monster
  spawn and loot are unimplemented, and the V140 synthetic harness position remains
  a test device only.
- **Presentation and audio: INCOMPLETE** — next missing behavior:
  `scene_music_control`. Opened whole as the eighth domain by the owner's
  2026-08-17 decision. One accepted MusicControlVital, the system-panel rendering
  surface, the PvP/exit dialogs and one WANTED loading screen are observed in
  passing runs; no Foundation module owns any of it and no presentation behavior
  has a test.

## Baselines

- V140 remains the latest runtime-proven evidence checkpoint.
- V141 is closed as a legacy characterization baseline: packaged and deterministic
  offline self-tested. A raw runtime capture exists but has not been formally audited,
  reported or promoted; V141 therefore adds no accepted gameplay claim.
- The accepted Foundation baseline introduces no V142 protocol/gameplay
  hypothesis. Explicit test-only hypothesis modes remain outside that baseline
  and are governed by the canonical hypothesis ledger.

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
- CHARACTER-NAME-001 adds the exact player-name projection. Create/List preserve
  the canonical actor-wire name, while StartGame emits the same persisted value
  through ActorAttr mask `0x01000000`/wstring `+0x164`, the field consumed by
  `NameBoardPlayer`. BasicAttr remains unchanged.
- CHARACTER-NAME-002 is the controlled runtime pass for that projection. The exact
  StartGame wire carries `Arena01` once through ActorAttr low mask `0x01000800`,
  after unchanged BasicAttr mask `0x070C`, mandatory bool `1`, and cash `10000`.
  The Chief directly observed `Arena01` above the selected local player in the
  Port Royal world view, distinct from the target panel; the client remained
  responsive. No screenshot was retained. Remote-player naming, rename/uniqueness
  policy, authenticated ownership, and server-process restart durability remain
  unproven.
- Commit-before-reply: implemented for character creation and selection.
- Golden/state/restart/loopback/negative/legacy-dispatch verification: implemented.
- Deterministic source archive verification: implemented and excluded from Git.
- `docs/HYPOTHESIS_LEDGER.json` is the canonical inventory for every emitted
  guessed value, diagnostic value, retired candidate, and synthetic geometry.
  Its strict verifier pins 15 known entries, evidence markers, three-version
  expiry, `production_allowed=false`, and `authentic=false` for geometry.
  No current entry has an extension approval. Every entry beyond three related
  versions is frozen or `expired_pending_decision`; SCENE-005 faction 1 and the
  SCENE-007 ActionVital acknowledgement are frozen, and no new dependent version
  may layer on any expired entry without proof, retirement, or a future approval
  scoped to exact ledger IDs and an approved-through checkpoint.
- A live assisted-UI run now proves Create -> commit -> List -> Select -> StartGame,
  a position checkpoint, client exit/relaunch, and reload of the same `Arena01`
  character and scene-1 position while the same server process remained running.
- FND-006 extends that boundary across one actual server-process restart. Round A
  checkpointed `Arena01` at scene 1/seq 0, `(-9192.125,-2674.037109375,186)`,
  heading `5.009882926940918`; after the process and listeners stopped, Round B
  expired lease generation 6, opened generation 7, and emitted those exact values
  in fresh Select/StartGame while preserving identity, name, and opaque actor/avatar
  blobs. The Chief directly observed minimap `-9192,-2674` and name `Arena01` in
  the client UI (operator observation; no screenshot retained). This is not a
  clean-shutdown pass: Round A Ctrl+C returned tool exit 1 without a stopped
  marker, Round B signal attempts failed, validated PID 328 required Stop-Process,
  and generation 7 remains open. Crash durability, graceful session close, delete,
  remote/multi-account naming, rename policy, and authenticated ownership remain
  unproven.
- FND-007 closes the normal GAME-disconnect lease boundary in a separate controlled
  run. Exact session `aeee8c26bef046cfa0a8958579d7f68d`, generation 6 and selected
  character 1, was open before the client closed and received
  `closed_at=2026-08-16T05:54:24.102133+00:00` immediately after the GAME connection
  ended. The persisted scene-1 position and its prior update timestamp were
  unchanged. The server process remained alive and ports 10188/10189 remained
  listening after the client exit (operational observation; no netstat sidecar was
  retained). This is not a graceful server-shutdown pass: Ctrl+C still failed and
  exact validated Python PID 12228 required force-stop. Abrupt client loss,
  process-crash recovery, graceful process shutdown, concurrent connections and
  authenticated multi-account ownership remain unproven.
- FND-008 closes one clean requested server-shutdown boundary with an active GAME
  client. A Windows helper attached to the console associated with exact target PID
  24080 and returned `ctrl_c_sent=true`; the server then stopped active LOGIN/GAME
  sockets and closed exact session
  `690593d79d7e4a9bb550900a48f2b21e` generation 7 at
  `2026-08-16T06:53:42.854792+00:00`, emitted one `[FOUNDATION] stopped`, and exited
  0 with empty stderr. The close occurred about 62.6 ms after the retained signal
  window began and did not rewrite the persisted position. The Chief directly
  observed the connected client show a disconnect modal after server stop and then
  acknowledged it (operator observation; no screenshot retained); its wrapper later
  exited 0 with empty streams. This is one Grade B active-client requested-stop pass,
  not proof of every Windows console host/signal source, crash or power-loss safety,
  transaction-failure recovery, concurrency, remote clients, or multi-account use.
- FND-009 closes one bounded abrupt-process restart boundary. Round A committed
  `Arena01` scene 1/seq 0 at
  `(-7292.4833984375,-3187.03759765625,186)`, heading
  `0.18130016326904297`, while exact selected session
  `becd6c1efb9e4443825cfb4f46ce9210` generation 8 remained open. A validated
  `Stop-Process -Force` removed exact server PID 11412 while client PID 2308 was
  still running; the post-kill snapshot retained both the committed checkpoint and
  open lease. Round B startup closed that stale SID before fresh login, then opened
  generation 9 and emitted byte-identical Character List plus StartGame MovementAttr
  containing the exact checkpoint, without CreateActor and without changing the
  opaque actor/avatar blobs. Normal client disconnect closed generation 9; a later
  requested stop emitted one marker and exited 0. This is a Grade B stable-commit
  recovery pass with a Grade E deliberate-loss trigger, not proof of in-flight
  transaction/non-empty-WAL recovery, power loss, every crash mechanism,
  concurrency, remote clients, or authenticated multi-account use.
- FND-010 closes the complementary abrupt-client boundary against one continuously
  running server. One validated `Stop-Process -Force` removed active Client A PID
  7648 while selected generation-10 SID
  `80311b2e090441b68df24a770a64a665` was open. The server observed socket reset,
  closed that exact SID in about 650 ms without rewriting position, and remained
  live on the same PID 20444/listeners. Client B then opened generation 11 and,
  with zero CreateActor, received byte-identical Character List and StartGame PCs
  preserving `Arena01`, identity, opaque blobs and the committed checkpoint. The
  Chief directly observed minimap `-7292,-3187` and world name `Arena01` after the
  reconnect (operator observation; no screenshot retained). Client B exit 0 closed
  generation 11; later requested server stop exited 0. This is a Grade B
  server-reaction/reconnect pass with a Grade E deliberate client-loss trigger,
  not proof of network partition, power loss, intermediate DB/WAL bytes,
  concurrency, remote clients, or authenticated multi-account use.
- OBJECT-POP-002 closes the first typed authoritative NPC-style scene-actor
  membership runtime boundary. One exact scene-1 TargetPos emitted the nearest-20
  initial generation and a byte-identical 3-second reapply; a forward refresh
  retained 19 NPCAttr-only entries, admitted placement 87 with full MovementAttr
  and omitted 82, while the reverse admitted 82 and omitted 87, restoring the
  initial set. All four PCs/frames are byte-identical to the typed builder and
  frozen V141 oracle. No structural DeleteActor occurred, 70 heartbeats followed
  the reverse transition, and the final raw TargetPos XYZ/heading exactly match
  the durable DB checkpoint. The only pre-to-final logical-row deltas are
  generation-12 open/close and position;
  identity, `Arena01`, opaque actor/avatar blobs, migrations, integrity and foreign
  keys are fixed. The Chief directly observed populated radar/models, a new human
  scene actor in the forward view, and a large Warden-style model in the reverse
  view (operator observation; no screenshot retained). Those visual observations
  are not bound to placement IDs and do not prove a visible despawn. This is not
  monster/remote-player classification, authentic population policy, persisted
  membership, combat, or another object-domain claim. Shutdown emitted one stopped
  marker with empty stderr and no remaining listeners, but no exit-code sidecar
  exists, so exit 0 is not claimed.
- ITEM-LIFECYCLE-001 closes one exact persistent Backpack transition. Round A
  StartGame carried the accepted four-record initial Backpack once, then exact
  V111 request `(operation=4,value32=0,item_identity=3)` committed identity 1
  quantity 2 and removed identity 3 before the exact frozen response was sent.
  Round B reconnected without CreateActor or ItemOperate and received an exact
  three-record merged Backpack in StartGame. Replacing only the 159-byte initial
  Backpack subwire with the 124-byte merged subwire produces the complete B
  StartGame PC byte for byte; reframing that PC produces the complete B frame.
  The pre-to-final database allowlist is
  migration 3, the exact Backpack post-state and closed session generations
  12/13; account, `Arena01`, selector, identity, opaque actor/avatar blobs,
  position, older sessions, integrity and foreign keys remain fixed. The Chief
  directly observed the Round A UI count change `4/40` to `3/40` after drag
  (operator observation; no screenshot retained). Policy prevented entering the
  second-password PIN in Round B, so there is no B UI count claim. This proves
  only the exact V111 merge/reconnect projection—not generalized item moves,
  equipment, ownership, concurrency or crash recovery. No retained server exit
  sidecar exists and PTY exit was 1, so no clean-shutdown/exit-0 claim is added.
- ITEM-MOVE-CAPTURE-001 adds a strict capture-only boundary for the exact
  36-byte client request `(operation=4,value32=2,item_identity=1)` from the
  exact merged Backpack. In that explicit mode every ItemOperate-shaped request
  is owned, the target request is recorded once, and no response or durable/
  in-memory Backpack mutation is allowed. The controlled live run captured one
  exact request at frame 49 after a slot-0 to empty-slot-2 drag. No
  `ItemOperateVitalRes` was emitted; the next server write was the normal
  heartbeat, the Backpack stayed `3/40` with identity 1 quantity 2 at slot 0,
  and the post-run SQLite oracle retained exact items `[1@0 qty2,2@1,4@3]`
  with integrity/FK pass. Transport continued through frame 188/heartbeat 116,
  stderr was empty, and requested shutdown emitted one stopped marker. This
  proves the client request producer and capture-only no-reply boundary only;
  it does not prove an authentic move response or persistence policy.
- SECOND-PASSWORD-BYPASS-001 adds the persistent Foundation server parameter
  `--second-password-mode required|bypass`; `required` is the default and the
  option is available alongside every Foundation scenario. The first live
  one-shot trial emitted the exact V110 OK packet but Backpack still opened the
  PIN dialog; opening that dialog emitted no distinct request. SECOND-PASSWORD-
  BYPASS-002 therefore repeats the same hash-pinned response on exact empty
  runtime polls while `bypass` is enabled. The live pulse opened Backpack
  directly, but an unthrottled response loop was observed; the implementation
  now rate-limits pulses to one per 2.0 monotonic seconds. The final controlled
  run opened Backpack directly at `3 / 40` with no PIN dialog; 52 retained
  keepalive sends were spaced by at least 2.018 seconds and server stderr was
  empty. It never receives, stores or synthesizes a PIN/digest. Default sessions
  remain unchanged. This is a local-server runtime pass, not authentic original-
  server credential policy or proof for every client binary/gated UI.
- ITEM-MOVE-HYP-001 implements the first bounded HYP-PF-008 composition behind
  a separate strict test-only scenario. It combines the exact captured slot-2
  request with separately accepted free-slot and quantity-2 response facts,
  commits identity 1 quantity 2 from slot 0 to currently free slot 2, then emits
  one hash-pinned composed response and permits only that same opt-in reconnect
  projection. Occupied slot 3, swap/displacement, every other tuple, stale or
  non-owning sessions, baseline projection and replay fail closed. This is Grade
  D implementation evidence only; no original-server response policy or runtime
  client acceptance is claimed.
- ITEM-MOVE-ORDER-001 narrows two HYP-PF-008 uncertainties with exact static
  client proof. ItemAttr qword identity `+0x28` is the Backpack tree key; the
  comparator and codec successor walk canonicalize small positive identities as
  `[1,2,4]`, independent of their slots. The complete accepted merged snapshot
  occupies only slots 0, 1 and 3, so slot 2 is structurally unoccupied. This
  proves client compatibility/internal ordering, not original-server response,
  reconnect ordering policy, persistence, or runtime acceptance; HYP-PF-008
  remains Grade D and non-production.
- ITEM-MOVE-CONSUMER-001 closes the hidden client-prestate question with exact
  static proof. The ItemOperate result handler clears the displayed payload that
  matches the incoming qword identity, routes by the incoming slot, and clones
  the complete incoming ItemAttr identity/template/quantity/slot into the
  destination slot object. It does not compare old quantity or old slot and has
  no destination-occupancy rejection in that exact slot-widget lane. Composed
  with the proven merged state and free slot 2, the quantity-2/slot-2 response
  has no hidden consumer-side prestate gate. Original-server response selection,
  durable/reconnect policy and live UI acceptance remain missing, so HYP-PF-008
  stays Grade D, test-only and non-production.
- EQUIP-STATE-001 closes a false-equivalence risk in the next equipment lane.
  `ItemBagAttr_Equiped` is an exact registered shared ItemBag structure, but the
  Character equipment refresh explicitly requests the separate
  `CollectionBagAttr`, then maps each non-`0xFF` ItemAttr `+0x39` byte to an
  identity. StartGame generically imports every received attribute before its
  four class-specific Backpack/Actor/Avatar/Movement lookups; neither equipped
  bag has a direct StartGame lookup. No authentic equipped container, absolute
  reserved slot, operation-5 response or server allocation policy exists, so
  Foundation StartGame remains unchanged and no equipment state is synthesized.

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
- SCENE-008 passed the exact downstream consumer boundary with an observe-only,
  checksum/code-guarded runtime trace. The SCENE-007 `0xEA7D`/`0x203D`
  acknowledgement reached the client handler, constructed one generic action with
  implementation pointer zero and terminal bit `8`, entered the selected actor's
  `+0x20` queue, and reached its first common update return with bit `8` unchanged.
  The final clean probe exited while the client remained alive, stdout/stderr were
  empty, server heartbeats continued, and the database main/WAL/SHM guard passed
  unchanged. This proves an inert terminal consumer lifecycle, not animation,
  hit, damage, FightAttr, AI, death, loot, skills or authentic faction.
- SCENE-009 closes the next static provenance and instrumentation-readiness gate.
  Exact client registration, serializer and handler code identify `CHitResult`
  Vital ID `0x16F7` as a distinct inbound result/reaction consumer. Its bounded
  implementation lane requires record flags bit 0 and bit 3 set, bit 4 clear,
  a resolved target and a non-null `0x48D870` result; the handler then reaches
  the preparation boundary for the target actor's `+0x40` queue. Header
  performer/action and the per-record target are the only fields with proven
  semantics; the other values remain opaque, including the signed dword at record
  `+0x08`, which is not proven damage. A checksum/code-guarded ready-only probe
  attached after moving three Frida hooks to relocatable preparation blocks.
  During one controlled hostile TargetVital -> `0xEA7D` ->
  SCENE-007 acknowledgement window it emitted only `probe_ready`; no `CHitResult`
  lifecycle was observed. Server heartbeats continued through 72, server and guard
  stderr were empty, Chief direct UI observation found the client responsive, and
  the database main/WAL/SHM guard passed unchanged. This absence is an operational
  negative, not proof that `CHitResult` is unrelated to combat. No `CHitResult`
  packet/event or CHitResult-driven HP mutation, UpdateAttr or FightAttr was
  observed or composed in this acknowledgement lane.
- SCENE-010 closes the numeric BEHAVIOR-registry lookup boundary with exact
  static provenance and one checksum/code-guarded runtime trace. Registry lookup
  `0x702A10` received raw key `0xEA7D` twice from producer/control return
  `0x44E92A` and once from the inbound ActionVital-handler return `0x7517B5`; all
  three results were null in this session. The paired server trace fixes the final
  consumer lookup 18 ms after the exact SCENE-007 acknowledgement. Static control
  flow proves only that null takes the default branch while generic ActionVital
  construction and actor queueing can still proceed. The probe emitted
  229 valid events, no probe error, exited zero with empty stdout/stderr, and the
  client stayed healthy until controlled close. DB main/WAL/SHM returned
  `PASS_UNCHANGED`. Exact construction and population proof is
  `0x4162A0 -> 0x47BFC0 -> 0x491650`: table `BEHAVIOR`, row `n_ID` stored at entry
  `+0x04`, with named fields `n_AMOUNT_TARGET`, `n_RANGE`, `n_DAMAGE_AREA`,
  `n_PROFIT`, `n_THENDO`, `n_CLASS` and parsers including `s_HIT_KEYFRAME` and
  `s_HITBACK`; the latter populate the `+0xE4` vector consumed by reaction factory
  `0x48D870`. The intervening ACHIEVEMENT correction is superseded: `0x705000`
  belongs to distinct singleton `0x102DB68`, not this registry at `0x102DAD8`.
  This does not prove an exact action/ScriptB binding, animation,
  hit/damage/HP, CHitResult ordering, AI, death, loot, skills or authentic faction.
  Do not insert a synthetic `0xEA7D` BEHAVIOR entry. The observed null applies only
  to the three captured lookup instants. Composing that same null with the exact
  `0x48D870` lookup/fallback path predicts a null CHitResult implementation for
  `EA7D`, but no CHitResult invocation was observed and that composition is not a
  runtime CHitResult fact.
- SCENE-011 closes an instrumentation-only natural BEHAVIOR-entry checkpoint.
  One exact guarded run emitted five non-null results and four instant-scoped
  misses from singleton `0x102DAD8`, with shared strict sequence and no probe
  error. Key 97 at static caller `0x48D2C8` had source-named `n_RANGE=10` and an
  empty `+0xE4` vector. Keys 278 and 279 at static caller `0x7555D2` each repeated
  the same exact values: `n_AMOUNT_TARGET=1`, `n_RANGE=75`,
  `n_DAMAGE_AREA=200`, `n_PROFIT=0`, `n_THENDO=278`, `n_CLASS=0`, vector count 1.
  Key `0xEA7D` missed twice at static caller `0x44E92A`; key 0 missed twice at
  `0x7555D2`. All results are caller- and instant-scoped. Source property
  `n_DAMAGE_AREA` is not observed damage or an HP claim. The paired flow sent an
  EA7D/`0x203D` ActionVital but no TargetVital, so the strict server sent no ACK;
  no inbound EA7D response or CHitResult was tested. Probe exit 0, empty
  stdout/stderr, healthy heartbeat lane and DB `PASS_UNCHANGED`. Do not infer
  ScriptB binding, vector-record contents, animation, hit/damage/HP or send a
  synthesized response. Two preceding ready-only exit-1 attempts are superseded
  timing diagnostics.
- SCENE-012 closes the EA7D geometric-gate lane as a static proof plus an
  instrumented operational negative, not a runtime pass. Exact code at
  `0x44EB1D` calls `0x4758D0` with action `0xEA7D`; the EA7D path computes a
  strict squared-distance comparison against a threshold made from an unknown
  live object scalar plus the `0x755540` mode-0 BEHAVIOR selection. SCENE-011
  observed natural keys 278/279 with `n_RANGE=75`, but the live scalar, object
  identities and XYZ values at the comparison remain unknown, so no offline
  boolean is justified. A narrowed two-hook probe emitted exact
  `gate_enter` at live `0xD0EB1D` and then failed closed on a duplicate operator
  gesture before any `gate_result`; probe exit was 1. The exact uninstrumented
  TargetVital-kind1 -> EA7D -> one-shot SCENE-007 ACK control occurred earlier
  and is not correlated to that probe event. Transport remained active through
  the final logged heartbeat/request window before client close, and DB
  main/WAL/SHM returned `PASS_UNCHANGED`. Do not claim gate true/false,
  in/out-of-range, units, attack success, animation, hit, damage, HP, FightAttr,
  AI, death, loot, skills or authentic faction. Stop adding hooks to this live
  path. The next safe boundary is a structured offline audit for a complete
  original/natural server-to-client combat-result envelope; zero hits remain a
  corpus negative and do not authorize a synthesized CHitResult or attr packet.
- SCENE-013 closes the available structured combat-corpus audit as a capability
  negative. A deterministic, hash-guarded parser audited 2,621 decoded frames
  from six unique logical evidence sources spanning v74-v76 and v81-v83,
  including one exact ZIP member. Every source is a GameClient-to-local-emulator
  receive log; eligible original-server-to-client decoded frames are exactly
  zero. Across all directions the target-family inventory contains five
  TargetVital occurrences and zero ActionVital, CHitResult, CFightMsgVital,
  CKnockdownVital, CShotMissileVital or CMissileHitResult occurrences. Because
  there are no direction-eligible frames, this is not even a bounded absence of
  those packet types: `bounded_target_negative=false`. The tool accepts only
  anchored decoder output (`STRUCTURAL_IDS ... OUTER` or timestamped `RECV ...
  ids=[...]`), ignores raw hexdumps, rejects malformed/drifted/duplicate inputs
  and leaves evidence files read-only. This proves only that the currently
  curated corpus cannot answer the missing inbound combat-response question.
  It does not prove protocol absence or authorize any synthesized combat,
  CHitResult, HP, UpdateAttr or FightAttr payload. The evidence-backed combat
  lane now requires a lawful original server-to-client combat capture or exact
  server-side producer; meanwhile only read-only/static preparation in other
  roadmap lanes may continue.
- SKILL-001 establishes a static skill-protocol boundary and guarded observation
  readiness without changing StartGame or gameplay. Exact registration, vtable
  and codec code identify class `TriggerCastSkillVital` with deterministic class
  ID/hash `0x5CD2`; its wire object contains only raw fields `+0x14 u16`,
  `+0x16 u8` and `+0x18 u32`. When singleton `0x1032EC4` exists, its client
  consumer prepares a candidate (which can be null on allocation failure) and
  submits it through exact edge `0x601880 -> 0x449110`; the no-singleton branch
  skips preparation/submission, and all branches converge on boolean true. No direct local
  UI/hotkey producer was recovered and indirect production remains possible. A
  checksum/PE/code-guarded observe-only probe for codec `0x600A60`, consumer
  `0x601810` and that exact submission edge passed 115 offline tests and an
  independent review; it has not been run against a live client.
- Static state tracing keeps three separate domains distinct. `CSkillAttr`
  (`0x1661`) is an optional ActorAttr-owned ordered container; both omission and
  a present count-zero value are structurally accepted. Each record is only an
  ordered u16 key plus opaque u16/u32 payloads. `CLearnSkillResultVital` replaces
  that set from three positional vectors and `CRevertSkilltVital` removes by the
  same key, but no field is proven to be a skill ID, level or entitlement.
  Separately, `CStartCooldownVital` (`0x4DDA`) carries a count plus repeated raw
  `(s16, f32)` records and updates `CCooldownAttr`; no exact dataflow binds its key
  to `CSkillAttr` or `TriggerCastSkillVital`. Do not add an empty `CSkillAttr`, a
  cooldown attr or any trigger packet to StartGame. No job/class mapping,
  ownership, hotbar, resource cost, cooldown meaning, successful cast, animation,
  attack, damage or persistence/reconnect behavior is proven. The next acceptable
  promotion requires a natural observe-only codec/consumer occurrence or an exact
  named producer/data binding; do not synthesize any of these protocol classes.
- JOB-001 proves the creation-preset table boundary but does not identify a
  persistent job/class wire field. Exact client code resolves named table
  `CHARCREATE_CLASS`; the guarded frozen table has five `n_ID` rows
  `{1,2,4,16,32}` and named starter appearance, equipment and `s_SKILL_*`
  columns. The exact captured CreateActor `test01` AvatarAttr numerically matches
  row-1 chest `2300026`, leggings `2300027` and both weapon slots `2200002`, which
  supports preset provenance only. No setter/copy chain from table `n_ID` into a
  CreateActor, AvatarAttr or ActorAttr offset was recovered. In particular,
  CreateActorDataEx `+0x18` is `0` in that capture while the matching preset key is
  `1`, so it cannot be promoted as class. Keep all current Avatar fields opaque;
  do not synthesize class values or infer skill entitlement from the table's
  preset strings. Resume only after an exact named-key-to-wire setter plus a
  corresponding List/StartGame consumer, or a natural trace designed from such a
  static boundary.
- DELETE-003 proves only the nested `DeleteActorVital` producer/submission
  boundary. Raw operation values 1 and 2 are constructed by distinct UI paths and
  both reach generic `0x4011A0 -> 0x5DD800`; no exact edge binds either object to
  an outer protocol class/version/mask/count or response. An isolated `DelTst01`
  run reached a confirmation dialog by operator observation and was cancelled
  before the affirmative action; no screenshot was retained, all captured logs
  contain zero `0x36DB`, and the isolated database guard is `PASS_UNCHANGED` with
  `deleted_at=NULL`. This is no Delete request, response, refresh, or mutation
  proof. Do not add an outer parser/response/repository delete path. Any future
  affirmative UI delete action requires action-time confirmation.
- HOTBAR-001 proves only the structural boundary of
  `SetItemOnParticularHotKeyPosVital`. Exact registration stores deterministic
  class-name hash `0xE0AC` in `0x10820A4`; standalone getter `0x5E4A40` reads that
  global and must not be confused with following-class vtable method `0x5E4AE0`.
  Codec `0x5E6DE0` carries raw `(u32,i8,i8)` at object `+0x14/+0x18/+0x19`.
  Consumer `0x5EFAF0` calls `0x5C5080` with logical arguments
  `(raw +0x14 u32, sign-extended +0x18, sign-extended +0x19 - 1)` and returns
  true. Generic pool/prototype construction is exact, but no UI producer,
  field meaning, item-versus-skill discriminator, save/load container or reconnect
  path is proven. StartGame remains unchanged; do not synthesize this vital or
  persist guessed hotkey state.
- COMBAT-BIND-001 separates the EA7D geometric selector from the independent
  inbound ActionVital lookup. Grade A static code shows `0x755540` mode 0 retains
  the first non-null BEHAVIOR `n_RANGE`, skips later values greater than or equal
  to it, and returns only the selected scalar. Composed with Grade C SCENE-011
  order `0,278,279`, where both non-null entries have `n_RANGE=75`, key 278 sets
  retained scalar 75 and equal key 279 is skipped. Only 75 survives into the
  distance gate; no candidate key is copied downstream. Inbound `0x7517A5 ->
  0x702A10` instead consumes ActionVital `+0x30`, exact EA7D in the accepted
  shape. Creation value 2200002 has zero literal occurrence in either exact
  client image and no dataflow into this chain; it is not proven equipped,
  owned, weapon-related or a BEHAVIOR key. Do not echo IDs, alter ActionVital or
  synthesize combat responses.
- COMBAT-KNOCK-001/BIND establishes an exact static actor-scheduler boundary for
  `CKnockdownVital` without authorizing a packet. Consumer `0x750700` resolves a
  receiver actor, and `0x47CAD0 -> 0x48D270 -> 0x702A10` uses raw vital `+0x20`
  as a BEHAVIOR key. Raw `+0x24` is stored at inner implementation `+0x50`;
  float `+0x34` is discarded by this concrete path. Success builds a wrapper
  with vtable `0xF0F7DC` and flags `0x40000005`. Wrapper bit `0x40000000`
  selects the receiver actor `+0x40` lane through `0x4843F0`; the subsequent
  `0x4A0C90` queue invocation receives a separate argument `1`. Nullable
  receiver, lookup and actor-side gates remain. No non-framework
  direct writer, EA7D/278/279/CHitResult edge, HP/FightAttr/UpdateAttr mutation,
  visible knockdown/animation or packet fields/order is proven. The class name
  is role provenance only. Resume only with original inbound evidence or an
  exact producer assigning every field.
- COMBAT-KNOCK-DATA-001 closes the asset-name binding lane as a bounded negative.
  The exact frozen expanded BEHAVIOR table has 2,279 rows and 30 columns. Rows
  278/279 share raw `n_RANGE=75`, `n_CLASS=0`, `n_THENDO=278`,
  `n_AMOUNT_TARGET=1`, `n_DAMAGE_AREA=200` and `f_DAMAGE_PHYSICS=10`, but carry
  different source animation/keyframe strings. Ten row IDs contain `KNOCK` in
  a source string, 106 rows have non-empty `s_HITBACK`, and zero source strings
  contain `REACTION`; none has a proven dataflow to `CKnockdownVital +0x20`.
  Accepted SCENE-011 `vector_count=1` for 278/279 is structural only and exposes
  no record content or gameplay meaning. The current packed client asset is a
  separate, unparsed artifact and is not conflated with the guarded frozen
  expanded input. The concrete path still proves only `+0x20` as lookup key,
  `+0x24` stored at inner `+0x50`, and `+0x34` discarded. No direct
  non-framework field writer was found; an indirect/original producer remains
  possible. Stop mining asset names and resume only with lawful original S2C
  evidence or an exact producer assigning every field.
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
multi-account ownership, delete UI, job/class semantics, name uniqueness policy,
generalized inventory/equipment persistence and crash-time item transactions remain later gates.
