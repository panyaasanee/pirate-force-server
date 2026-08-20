# PF MULTIPLAYER-READINESS-AUDIT-001 — where the server assumes one player, what is already ready, and what a second player would cost

Round 77 (2026-08-18) · assistant lane · **audit only, report-only, additive** · HEAD `5cc0eda` · reproduce: `py -3 tools/pf_multiplayer_readiness_audit.py` (exit 0) and `py -3 -m pytest tests/test_multiplayer_readiness_audit.py -q`

Requested by the project owner on 2026-08-18 ~14:05 ICT: *"ขอดูข้อมูลก่อน"* — she is deciding between keeping the game single-player and making it genuinely playable together. This document exists to put numbers and `path:line` under that decision. **It implements nothing, changes no `src/` file, flips no matrix row, opens no hypothesis, and recommends no commitment.** It is not permission to build multiplayer.

> **One-paragraph answer.** The server can only serve one player, and the reason splits cleanly in two. **40 concrete assumption sites** exist. **18 of them are inside `current/pf_login_game_server_v141.py`, which project policy declares immutable** — so the accept-and-serve layer cannot be *edited*, only *replaced from outside*, and that single fact decides the architecture of any multiplayer work. Against that, **17 sites are already keyed by session and account rather than by process**: the schema, the lease table, every backpack and position write, and the actor-stream serializers are already multi-player-shaped. The chief's working hypothesis — *transport is expensive to retrofit, visibility is cheap to bolt on later* — is **half right and half wrong, and the wrong half matters more**. Transport is expensive exactly as predicted (**7 files, 32 sites, 89 pinned test functions, risk C, and the current limitation is load-bearing as an interlock for an unguarded database write**). Visibility is indeed cheap *in code* (**5 files, 6 sites, 52 pinned test functions**) — but it is **not** "just adding a frame type", because the one byte that distinguishes a remote *player* from a remote *NPC* is the single field in the whole projection path with **no evidence at all**. Of the **18 frames** a second visible player needs, **7 are fully anchored, 2 are partially anchored, and 9 must be guessed** — and one of the nine (`actor_type`) is answerable statically from the client binary today, with one client, using the exact method MOVE-PROJECT-001 already used.

---

## 0. Method, scope and what this is not

**Method.** Source scan only. Every claim below is a `(path, pattern, expected occurrence count)` triple re-derived by `tools/pf_multiplayer_readiness_audit.py`, plus two AST checks and one byte-exact check against an archived capture. Nothing was executed: no server was booted, no GameClient was opened, no socket was created, no database was touched, no disassembler was run.

**Line numbers.** All `path:line` citations are **as observed at HEAD `5cc0eda`**, read via `git --no-optional-locks show 5cc0eda:<path>`. A concurrent lane is editing `runtime.py`, `app.py` and `channel_message_hypothesis.py` while this audit was written, so the verifier deliberately locates every site **by content, not by line number**, and prints where it landed today. A moved line is not drift; a missing or duplicated site is, and exits nonzero.

**Risk grades A–E used in this document** are on the *risk* axis, not the evidence axis, and are defined here so they cannot be read loosely:

| grade | meaning |
| --- | --- |
| **A** | contained and reversible; every behaviour changed already has a pinned test and existing evidence |
| **B** | contained, but it re-grades a behaviour something currently asserts |
| **C** | crosses an interlock or an immutable boundary; **a partial landing is worse than not starting** |
| **D** | the change itself puts a guessed value on the wire (a compositional hypothesis by the `AGENTS.md` rubric) |
| **E** | the evidence needed does not exist and cannot be obtained from the available corpus |

**This is not.** Not an estimate in hours. Not a claim about the original server (it is gone; `v141` is a reconstruction notebook, not a captured server). Not a claim about what a second GameClient displays. Not a recommendation to start.

---

## 1. Where the code assumes exactly one player — 40 sites

`immutable` = the site lives in `current/pf_login_game_server_v141.py`, which cannot be edited under project policy.

### 1.1 Transport — one connection is served at a time (12 sites)

| id | site at HEAD `5cc0eda` | immutable | what it means |
| --- | --- | --- | --- |
| **T01** | `current/pf_login_game_server_v141.py:7388,7939` | **yes** | `s.listen(4)` on both listeners, and nothing services the backlog in parallel |
| **T02** | `current/pf_login_game_server_v141.py:7395` | **yes** | `c, a = s.accept()` is followed by the whole GAME connection handled inline in the same loop (body `7410`–`7849`) |
| **T03** | `current/pf_login_game_server_v141.py:7393` | **yes** | `while not stop.is_set():` advances to the next accept only after the current connection ends |
| **T04** | `current/pf_login_game_server_v141.py:7406,7947` | **yes** | `c.settimeout(600)` — one stalled client can hold its listener for ten minutes before the next accept |
| **T05** | `current/pf_login_game_server_v141.py:7943` | **yes** | LOGIN `c, addr = s.accept()`, likewise inline (`7951`–`8007`) |
| **T06** | `current/pf_login_game_server_v141.py:7993` | **yes** | LOGIN per-connection flags (`sent_login`, `sent_select`) live in the loop body, not in a per-connection object |
| **T07** | `current/pf_login_game_server_v141.py:7926` | **yes** | exactly one GAME listener thread is ever started |
| **T08** | `src/pirateforce_foundation/connection.py:35` | no | `self._local = threading.local()` — the accepted-connection binding is **thread-affine**, so accept and state construction must occur on the same thread |
| **T09** | `src/pirateforce_foundation/connection.py:51` | no | `raise RuntimeError("GAME connection already pending on listener thread")` — a second accept before release is a hard error by construction |
| **T10** | `src/pirateforce_foundation/connection.py:66` | no | `release()` only accepts the *single* pending connection of the calling thread |
| **T11** | `src/pirateforce_foundation/connection.py:73` | no | `abort_pending` can abort at most one pending connection |
| **T12** | `src/pirateforce_foundation/shutdown.py:259` | no | `raise RuntimeError("unexpected frozen GAME thread construction")` — the managed threading seam refuses any `Thread` that is not the frozen 4-argument GAME listener, so **no per-connection worker thread can be created through it** |

T08–T11 are the sharp edge. A thread-per-connection design accepts on the listener thread and hands the socket to a worker; the worker then constructs `GameSessionState`, which calls `connection_bindings.bind(self)` (`runtime.py:206` at HEAD), which reads the *worker's* thread-local, finds `pending is None`, and raises `"GAME state constructed without an accepted connection"` (`connection.py:59`). The binding must be re-modelled as a registry, not a thread-local slot.

### 1.2 Identity — one account per process (7 sites)

| id | site at HEAD `5cc0eda` | immutable | what it means |
| --- | --- | --- | --- |
| **I01** | `current/pf_login_game_server_v141.py:7859` | **yes** | `--token` default `"localtest"` — account identity is a **server-side CLI argument** |
| **I02** | `current/pf_login_game_server_v141.py:7399` | **yes** | `state = GameSessionState(token)` — every accepted GAME connection gets that same process-wide token |
| **I03** | `current/pf_login_game_server_v141.py:7869` | **yes** | `login_frame` is built once *before* the accept loop and replayed byte-identically to every client |
| **I04** | `current/pf_login_game_server_v141.py` — **absent** | **yes** | there is **no** `parse_login*` function. `v141` has 15 `parse_*` functions and none of them reads `LSCN_LoginVitalReq` (`0x42BF`), so the account name the client puts on the wire is never read |
| **I05** | `src/pirateforce_foundation/session.py:45` | no | `lifecycle.login(login_name)` with `login_name` = that token → `store.ensure_account(token)` |
| **I06** | `src/pirateforce_foundation/store.py:143` | no | `open_session` closes **every** open lease of the same account before inserting the new one |
| **I07** | `src/pirateforce_foundation/store.py:156` | no | `expire_open_sessions()` closes every open lease of **every** account at process start (`app.py:158,162` at HEAD) |

**This is the deepest single-player assumption in the project, and it is not the accept loop.** Two GameClients that both connected would resolve to the *same account row*, and I06 would then close the first client's lease the instant the second logged in. Fixing T01–T12 without fixing I01–I07 produces two connections fighting over one identity.

The account name *is* on the wire. Every archived LOGIN capture carries the same 22-byte nested record, verified byte-exact by the tool:

```
bf 42  0b 00  48 04 00 00 00  0e 00 00 00  44 04 00 00 00  74 65 73 74
 └id   └ver   └ tag 0x48 wstring, 4 bytes  └ tag 0x44 ASCII, 4 bytes = "test"
```

(`analysis/lost_eden_leisure_runtime/capture_v110/LOGIN_20260814_152723_188831_59376.txt`; the same record appears in every archived `LOGIN_*.txt` in `backups/` and `analysis/`.) The field is decodable. What it is *not* is **proven**, because every archived capture carries the identical value `"test"` — a field whose value never varies cannot be shown to be the account name from the corpus alone. See §4 G8.

### 1.3 World and outbound — shaped for one observer (10 sites)

| id | site at HEAD `5cc0eda` | immutable | what it means |
| --- | --- | --- | --- |
| **W01** | `src/pirateforce_foundation/population.py:167` | no | `build_port_royal_membership_transition(legacy, previous_indices, player_xyz)` — scene membership is a pure function of **one** player's XYZ |
| **W02** | `src/pirateforce_foundation/population.py:245` | no | `build_port_royal_initial_population(legacy, player_xyz)` — same |
| **W03** | `src/pirateforce_foundation/population.py:23` | no | `NPC_STYLE_ACTOR_TYPE = 4` — the only actor type the server can put in an entry |
| **W04** | `src/pirateforce_foundation/population_scenario.py:58` | no | the population profile lists `"remote_player"` as an explicit **nonclaim** |
| **W05** | `src/pirateforce_foundation/scene_object.py:34` | no | `make_remote_actor_entry(4, ...)` — the scene-object lane is actor type 4 as well |
| **W06** | `src/pirateforce_foundation/scene_object.py:12` | no | the remote-actor serializer allowlists exactly two hardcoded profiles and refuses everything else |
| **W07** | `src/pirateforce_foundation/scene_load.py:98` | no | the scene-load lane is pinned to one named character (`"Arena01"`) |
| **W08** | `current/pf_login_game_server_v141.py:7558` | **yes** | `actions = state.dispatch(parsed)` — outbound frames exist **only** as the return value of the requesting connection's dispatch |
| **W09** | `current/pf_login_game_server_v141.py:7755` | **yes** | `c.sendall(out_frame)` — the only outbound socket is the requesting connection's own. **There is no push channel to another connection anywhere in the server.** |
| **W10** | `current/pf_login_game_server_v141.py:7427,7754` | **yes** | `with send_lock:` — the per-connection write lock is created **inside** the frozen listener body (`7415`) and is unreachable from Foundation, so any writer added outside it would race the heartbeat thread on the same socket |

W08–W10 are the structural answer to "how hard is broadcast". The server is a **pure request/response machine**: a frame is produced only in response to a frame, and only on the socket that sent it. The one exception, `heartbeat_worker` (`7417`–`7436`), proves an unsolicited-write path is possible — and also proves it needs `send_lock`, which is out of reach.

W10 has an honest mitigation worth recording: `AcceptedGameSocket` (`connection.py:80`) already wraps the accepted socket and already hands a raw-socket lever to state via `make_transport_socket_closer` (`connection.py:101`). Adding a locked `sendall` method there would serialize the heartbeat, the dispatch reply and any future broadcast on one lock — **one method in one Foundation-owned file**, without touching `v141`.

### 1.4 Capture and logging — one lane per process (6 sites)

| id | site at HEAD `5cc0eda` | immutable | what it means |
| --- | --- | --- | --- |
| **L01** | `current/pf_login_game_server_v141.py:7372` | **yes** | one shared `GAME_LIVE.txt` per listener, appended by every connection |
| **L02** | `current/pf_login_game_server_v141.py:7373` | **yes** | one shared `GAME_EVENTS_LIVE.txt` per listener |
| **L03** | `current/pf_login_game_server_v141.py:7435` | **yes** | live lines after `SESSION_START` carry **no connection discriminator** (`HEARTBEAT`, `SENT`, `STATE` at `7435`, `7761`, `7842`) |
| **L04** | `current/pf_login_game_server_v141.py:7867` | **yes** | `capture_v141` is resolved relative to the process CWD |
| **L05** | `src/pirateforce_foundation/app.py:208` | no | `os.chdir(capture_root)` — the whole process moves into one capture root |
| **L06** | `src/pirateforce_foundation/runtime_console.py:84` | no | `sys.stdout`/`sys.stderr` are swapped process-wide for one mirrored console |

Per-connection raw logs are already per-connection (`GAME_{stamp}_{peer_port}.txt`, `7401`). The single-lane assumption is only in the *live* files and the console — which matters, because those are exactly the artifacts every attended GT run reads. **Two concurrent players would produce one interleaved live log with no way to tell whose heartbeat was whose.**

### 1.5 The interlock — why a half-done fix is worse than none (5 sites + 2 AST facts)

| id | site at HEAD `5cc0eda` | what it means |
| --- | --- | --- |
| **X01** | `src/pirateforce_foundation/runtime.py:929` | `self.foundation.checkpoint(candidate)` — the position checkpoint is the one database write reached from `dispatch` |
| **X02** | `src/pirateforce_foundation/runtime.py:945,1306` | both `_checkpoint_exact_target` call sites |
| **X03** | `src/pirateforce_foundation/store.py:273,333` | a stale lease **raises** `PermissionError("stale or non-owning character session")` rather than returning a status |
| **X04** | `src/pirateforce_foundation/shutdown.py:269` | `controller.request_stop("server thread failure")` — an exception escaping the listener stops the **entire server** |
| **X05** | `src/pirateforce_foundation/store.py:147` | `lease_generation` is monotonic per account, so a takeover is silent to the old holder |

Two facts the verifier proves by AST rather than by regex:

- **all 3** checkpoint calls in `runtime.py` sit at **try-depth 0** — nothing catches them;
- the frozen `game_listener` contains **exactly one** `try:` with **zero** `except` handlers (`v141:7440`, `finally:` at `7847`).

Chain them: second client logs in → `open_session` (I06) closes the first client's lease → first client walks → `dispatch` → `_checkpoint_exact_target` (X02) → `save_position` → `PermissionError` (X03) → nothing catches it (X01/X02 at depth 0, `v141:7440` has no `except`) → `ManagedThread.run_target` records the failure and calls `request_stop` (X04) → **the whole server stops for both players.**

This is not a new discovery — `reports/PF_SESSION_LIMIT001_SINGLE_SESSION_SERIAL_ACCEPT_KNOWN_LIMITATION_20260817.md` recorded it in round 21 and HYP-PF-011 made the dispatch exception boundary and an explicit lease policy **preconditions, not follow-ups**. This audit re-verifies it at HEAD `5cc0eda` and states the consequence plainly: **the single-session limitation is currently acting as the safety interlock for an unguarded write. Removing the limitation without the guard converts a recoverable stale lease into a total outage.**

---

## 2. What is already ready — 17 sites, verified by reading the code, not the notes

| id | site at HEAD `5cc0eda` | what is already right |
| --- | --- | --- |
| **R01** | `migrations/001_initial.sql:6` | `sessions` is a row-per-lease table keyed by a UUID `id TEXT PRIMARY KEY` with an `account_id` foreign key — many rows, many accounts, already |
| **R02** | `migrations/002_character_integrity.sql:11` | the only uniqueness the schema enforces is `sessions_one_active_character` on `selected_character_id WHERE closed_at IS NULL` — **one live session per *character*, not per server** |
| **R03** | `src/pirateforce_foundation/store.py:324` | `_require_selected_session` gates every backpack read and write on `(session_id, character_id)` ownership |
| **R04** | `src/pirateforce_foundation/store.py:271` | position writes carry the same `EXISTS(sessions WHERE id=? AND selected_character_id=? AND closed_at IS NULL)` predicate |
| **R05** | `src/pirateforce_foundation/store.py:198` | soft delete is session-scoped and refuses a character selected by any open session |
| **R06** | `src/pirateforce_foundation/store.py:166` | selector allocation is scoped to one account |
| **R07** | `src/pirateforce_foundation/lifecycle.py:42` | `lo = 0x10000000 + account_id * 0x10000 + selector + 1` — **the character identity space is already partitioned by account** (65 536 accounts × 256 characters) |
| **R08** | `src/pirateforce_foundation/store.py:33` | `PRAGMA busy_timeout=5000` already set for contended writers |
| **R09** | `src/pirateforce_foundation/store.py:36` | `PRAGMA journal_mode=WAL` already set — concurrent readers alongside a writer |
| **R10** | `src/pirateforce_foundation/session.py:10` | all `FoundationSession` state is instance state on one per-connection object; `PersistentGameSessionState` likewise assigns everything in `__init__` — **no module-level or class-level mutable state exists in the Foundation runtime** |
| **R11** | `src/pirateforce_foundation/shutdown.py:24` | `self._accepted: set[ManagedSocket]` — the shutdown controller already tracks accepted sockets as a **set** |
| **R12** | `src/pirateforce_foundation/shutdown.py:71` | `register_accepted` already registers every accepted socket individually and shuts them all down on stop |
| **R13** | `src/pirateforce_foundation/connection.py:101` | `make_transport_socket_closer` is an existing precedent for handing one connection's raw socket to its own state |
| **R14** | `current/pf_login_game_server_v141.py:1248` | `make_remote_actor_entry(actor_type, actor_identity, attrs)` already takes an **arbitrary** actor type and attr list |
| **R15** | `current/pf_login_game_server_v141.py:1267` | `make_runtime_remote_actors(entries)` already takes an arbitrary list of entries with a u16 count |
| **R16** | `current/pf_login_game_server_v141.py:634` | `make_select_res(status, game_port, ...)` already hands each client its game port **as a response field**, so per-connection game ports are wire-legal |
| **R17** | `src/pirateforce_foundation/inventory.py` — **absent** | see the correction below |

### 2.1 Correction to a standing note

The standing note says *"ทุก read/write กระเป๋าผูกกับ session+account อยู่แล้ว (`_require_selected_session` ใน `inventory.py`)"*.

**The conclusion is right; the location is wrong.** `_require_selected_session` does **not** exist in `inventory.py` — the verifier asserts zero occurrences there (R17). It is `src/pirateforce_foundation/store.py:324`, and it is called from six places: `get_backpack:337`, `apply_v111_stack_merge:346`, `apply_hypothesized_v111_slot2_move:386`, `move_backpack_item_to_free_slot:422`, `swap_backpack_item_with_occupied_slot:474`, `merge_backpack_item_into_occupied_slot:533`. `inventory.py` holds only pure transitions and serializers and has **no** session concept at all — which is the correct layering, and worth stating correctly so nobody looks for the guard in the wrong file.

The second half of the note — *"ตาราง `sessions` รองรับหลายแถวอยู่แล้ว"* — is **confirmed** (R01/R02), with one refinement the note does not carry: the schema's uniqueness is per *character*, but `open_session` adds a **stricter, code-level, per-account** rule (I06) that the schema never asked for. **The schema is more multi-player-ready than the code that uses it.**

---

## 3. The two work packages, measured separately

### 3.1 [A] transport / session — receive many connections, keep state per connection

| measure | value |
| --- | --- |
| files touched | **7** (6 modified + **1 new**) |
| assumption sites addressed | **32** of 40 |
| of which sit in the immutable `v141` | **18** |
| test functions that must be **re-proven** (pinned set) | **89** across 7 files |
| test functions in the broad import closure | **351** of 663 at HEAD `5cc0eda` (**53 % of the suite**) |
| **risk grade** | **C** |

| file | kind | sites |
| --- | --- | --- |
| `src/pirateforce_foundation/connection.py` | modify | T08 T09 T10 T11 |
| `src/pirateforce_foundation/shutdown.py` | modify | T12 X04 |
| `src/pirateforce_foundation/store.py` | modify | I06 I07 X03 X05 |
| `src/pirateforce_foundation/session.py` | modify | I05 |
| `src/pirateforce_foundation/runtime.py` | modify | X01 X02 |
| `src/pirateforce_foundation/app.py` | modify | L05 |
| `src/pirateforce_foundation/<new concurrent listener>.py` | **new** | T01–T07, I01–I04, L01–L04, W08–W10 |

The pinned 89: `test_single_session_limitation.py` (7), `test_session_row_persistence.py` (13), `test_startup_stale_lease_recovery.py` (15), `test_connection_lifecycle.py` (12), `test_server_shutdown.py` (15), `test_runtime_console.py` (5), `test_foundation_legacy_seam.py` (22).

**Why the new file is unavoidable, and why it is the whole story.** 18 of the 32 sites are inside `current/pf_login_game_server_v141.py`. Policy forbids editing it, and the existing escape hatch — `adapt_game_listener` (`connection.py:226`), which re-executes the frozen code object against substituted globals — can swap *objects* but cannot change *control flow*. `s.accept()` already routes through Foundation (`ListeningGameSocket.accept`, `connection.py:179`); the serial part is the loop body, and the loop body is code. So the ~440-line listener body (`v141:7371`–`7850`) and the ~65-line LOGIN loop (`v141:7933`–`8007`) must be **re-implemented** in a Foundation-owned module that calls the same frozen primitives (`recv_frame`, `parse_outer`, `state.dispatch`, `frame_pc`). This is the largest single piece of work the project has ever contemplated in `src/`, and it is also the one that cannot be done in halves.

**Why C and not B.** Three independent reasons, each with a citation: (1) 18 immutable sites force a replacement rather than an edit; (2) the interlock in §1.5 means a partial landing is strictly worse than the status quo — HYP-PF-011 already encodes this as a stop rule; (3) 53 % of the test suite sits in the import closure, so a regression here is not locally contained.

**Why not D.** Nothing in [A] requires putting a guessed value on the wire. The one wire question it raises — the account field in `LSCN_LoginVitalReq` — is *decodable*, not guessable (§4 G8).

**One free move worth naming.** The dispatch exception boundary (X01/X02/X03) is a strict improvement **today**, on the single-player server, independent of everything else in [A]: it converts "stale lease kills the server" into "stale lease drops one frame". It is also HYP-PF-011's own precondition. It can be landed alone, at risk **B**, without committing to anything else in this document.

### 3.2 [B] world / visibility — broadcast a remote player

| measure | value |
| --- | --- |
| files touched | **5** (3 modified + **2 new**) |
| assumption sites addressed | **6** of 40 |
| of which sit in the immutable `v141` | **0** |
| test functions that must be **re-proven** (pinned set) | **52** across 6 files |
| test functions in the broad import closure | **320** of 663 at HEAD `5cc0eda` |
| **risk grade** | **D today**, **B** once §4 G1 and G2 are answered |

| file | kind | sites |
| --- | --- | --- |
| `src/pirateforce_foundation/<new remote player projection>.py` | **new** | W03 W04 W05 |
| `scenarios/<new opt-in profile>.json` | **new** | — |
| `src/pirateforce_foundation/runtime.py` | modify | W01 W02 |
| `src/pirateforce_foundation/app.py` | modify | — |
| `src/pirateforce_foundation/connection.py` | modify | W10 (locked `sendall`) |

The pinned 52: `test_population.py` (6), `test_population_adapter.py` (9), `test_scene_object.py` (6), `test_npc_gait_wire.py` (14), `test_remote_movement_projection_static.py` (12), `test_scene_load.py` (5).

**The arithmetic, stated so nobody has to reconstruct it.** [A] addresses 32 sites and [B] addresses 6; **W10 appears in both** (the locked writer serves the heartbeat and any broadcast alike), so the union is **37 of 40**. The three neither package touches are **W06** (`scene_object.py:12`, the two-profile allowlist), **W07** (`scene_load.py:98`, the single named character) and **L06** (`runtime_console.py:84`, the process-global console swap). All three are deliberate narrowness in opt-in test lanes rather than obstacles to a second player, and none of them needs to move for either package to work.

### 3.3 Verdict on the chief's hypothesis — and where the numbers contradict it

**Confirmed:** [A] is 7 files / 32 sites / 89 pinned tests against [B]'s 5 files / 6 sites / 52 pinned tests, and [A] carries all 18 immutable sites while [B] carries none. On raw code cost the hypothesis holds — **[A] is roughly 5× [B] in sites and 1.7× in pinned tests, and [B] genuinely is mostly "add a frame type".**

**Three corrections the numbers force:**

1. **"Cheap to bolt on later" hides where the cost actually is.** [B]'s cheap part is the plumbing. Its expensive part is **one byte**: `u8tag(0x0B, actor_type)` at `v141:1258`. Every other field in a remote-player entry is anchored (§4 F1–F4). That byte is the only field in the entire projection path with **zero evidence** — only `4` (CNetNPC) has ever been emitted or proven, and the client's `actor_type` → class dispatch is not characterised in any report in `reports/` (verified: `CNetNPC` and `actor_type` appear only in `PF_MOVE_PROJECT001_*.md` and its verifier). Shipping a candidate value makes [B] a **D-grade compositional hypothesis**, which directly contradicts the owner's stated rule *"เหมือนจริงใช้จริง ทำครั้งเดียวจบ"*.

2. **[B] is not blocked by [A] the way the roadmap says.** `docs/ROADMAP_TO_PLAYABLE.md` records *"`remote_player_movement_projection` depends on `concurrent_multi_client`"*. That is true only if "exercise [B]" means "with a second real player". It is **false** if it means "learn what the client does with a remote player entry": one client plus a server that emits a probe actor answers G1 and G2 empirically, and that is precisely how SCENE-005 through SCENE-013 and OBJECT-POP-002 were done. `scene_object.py:12` is the existing precedent — a two-profile hardcoded allowlist emitting a remote actor to a single client.

3. **The reason to do [A] is not "so players can see each other".** It is that the current single-lane behaviour is holding an unguarded write closed (§1.5) and that **no two-player fact can ever be measured on this project's own wire without it**. Those are better reasons than the visibility one, and they are independent of G1.

---

## 4. Anchors versus guesses, frame by frame — 18 entries

*Anchored* = a client-side decoder or consumer is pinned by an existing report. *Partial* = pinned, but never in the remote-actor context this feature needs. *Guess* = no decoder, no capture, no static enumeration.

### 4.1 Anchored — 7

| id | frame / attribute | wire id | evidence |
| --- | --- | --- | --- |
| **F1** | `GSCN_RunTimeProtocolRes` v4 remote-actor stream | `0x6E9D` | serializer chain `0x5F4070` → `0x5E3EE0` → `0x5E1C10`/`0x5E01D0` documented at `v141:1267`–`1288`; `movement/scene_actor_population_streaming` is `runtime_pass` |
| **F2** | remote-actor entry container | — | client serializer `0x5E21D0`: u8 actor type, qword identity, u8 attr count, per-attr u16 id + Serial (`v141:1248`–`1264`) |
| **F3** | `MovementAttr` | `0x2067` | MOVE-PROJECT-001 grade A: `Serial 0x4671C0`, apply/merge `0x467130`, delta `0x467040`, and codec `0x89A600` is **direction-agnostic**, so the same routine decodes inbound |
| **F4** | `NPCAttr` (+ `BasicAttr`) | `0x0AD5` | serializer `0x466EB0` / `BasicAttr 0x4656F0` / name → target panel `0x51F920` / visual preset → `0x45DAE0` → `0x78AA50` (`v141:1142`–`1163`); runtime-proven by OBJECT-POP-002 |
| **F5** | `Channel_LocalTalkMessageVital` | `0xAC52` | CHAT-CHANNEL-001/002: shared serializer `0x65AD40` implemented **both directions**, dispatcher `0x659870` renders LocalTalk, and a re-encode of the GT-006 capture reproduces the captured bytes and the independently pinned frame hashes |
| **F6** | actor removal by omission from the next generation | — | `population.py:202`–`204` retained/entrant/omitted; runtime-proven by OBJECT-POP-002 forward **and** reverse refresh |
| **F7** | `DeleteActorVital` | `0x36DB` | decoded by DELETE-SOFT-002 — **but it is a character-select-stage delete, not a scene despawn.** Do not reach for it as a "player left" frame |

### 4.2 Partial — 2

| id | frame | wire id | what is anchored, what is not |
| --- | --- | --- | --- |
| **F8** | `ActorAttr` | `0x12AD` | anchored on the **local-player** `StartGameRes` path (`legacy_bridge.py:47`–`75`, `player_wire.py`), and STATS-PROG-001 anchors the id. It has **never been observed inside a remote-actor entry**, so whether a remote player carries `ActorAttr`, `NPCAttr`, or both is open |
| **F9** | `AvatarAttr` | `0x16A0` | serializer `0x464560` and the common attr header `0x467790` are known (`v141:2369`–`2385`), and each character's avatar bytes are already persisted losslessly (`characters.avatar_wire`). But `character_management/appearance_and_avatar_binding` is `in_progress` with *"No field-level appearance model exists"* — the bytes can be replayed, not composed |

### 4.3 Must guess — 9

| id | question | status |
| --- | --- | --- |
| **G1** | **the `actor_type` value for a human player** | only `4` (CNetNPC) proven. **Statically answerable today** from `GameClient.local.bin` by enumerating the actor-entry consumer's type dispatch — the same method, same binary, same tooling as MOVE-PROJECT-001. **No second client required.** |
| **G2** | attr composition of a remote human-player entry (which attrs, order, masks) | no capture and no static enumeration. Answerable by a one-client probe once G1 narrows the candidates |
| **G3** | interest management — who sees whom, entry/exit radius | the coverage row calls it *"entirely unknown"* |
| **G4** | server → client remote update cadence | MOVE-CADENCE-001 measured the **client's own** TargetPos cadence per walk, not a server push rate. Different direction, different question |
| **G5** | client-side interpolation between projections | uncaptured |
| **G6** | whether the server may originate a chat channel to a **third party**, and what the client renders | CHAT-CHANNEL-002 states this as its load-bearing limit; it is GT-016 |
| **G7** | Whisper / Party / Guild membership and routing authority | explicitly not claimed; needs two concurrent sessions |
| **G8** | `LSCN_LoginVitalReq` (`0x42BF`) account and credential field roles | the bytes exist in every archived capture and the tool reproduces them byte-exact — but the value never varies (`"test"`). **Decodable with one attended run** that types a different username. Not a guess; an unrun experiment |
| **G9** | PvP damage between players | `combat/damage_and_hit_result` is `blocked` on SCENE-013's corpus negative; `combat/pvp_engagement` is `not_started`. This one is **grade E** — the corpus provably cannot answer it |

**The shape of the guess list matters more than its length.** G1 and G8 are not really guesses — they are two experiments nobody has run, each cheap, each independent of everything else. G3/G4/G5/G7 genuinely need two live sessions. G9 is E and is not coming back. **The original server is gone and there was never a publish, so no authentic two-player capture will ever exist for this project.** Static client evidence plus deliberate probes is the *only* available road, which makes answering G1 statically not merely the cheapest option but the most faithful one.

---

## 5. Three orderings for the owner to choose from

Presented with costs; **the choice is the owner's.** The chief's preference and its reasoning are stated at the end and are not a decision.

### Option 1 — "Answer the byte first" (report-only, no `src/` change)

Two static/observational milestones on the existing pattern: **(a)** enumerate the client's actor-entry `actor_type` → class dispatch from `GameClient.local.bin` (answers G1, and probably narrows G2); **(b)** decode `LSCN_LoginVitalReq 0x42BF` and run **one** attended login with a different username to make the account field variable-proven (answers G8).

- **Cost:** 0 `src/` changes, 0 existing test functions to re-prove, ~2 verifier tools + 2 tests + 2 reports, 1 short attended GT slot for (b).
- **Gets:** [B] drops from risk **D** to risk **B**; [A]'s identity layer stops being a guess before a line of it is written.
- **Does not get:** anything playable. The game is exactly as single-player afterwards.
- **Risk: A.**

### Option 2 — "One-client visibility probe" ([B] first, synthetic second actor)

Emit one probe remote actor with a candidate `actor_type` and attr composition to a **single** client under a strict opt-in scenario, and observe what renders. Precedent: `scene_object.py:12` and the SCENE-005…013 line.

- **Cost:** 5 files (2 new) / 6 sites / **52 pinned test functions**; 1 attended GT run.
- **Gets:** an empirical answer to G1 and G2 without a second client; the whole projection lane exercised end to end; `remote_player_movement_projection` gets a real runtime observation instead of a static one.
- **Does not get:** two real players, chat between players, interest management (G3), cadence (G4), interpolation (G5).
- **Risk: D** if run before Option 1 (a guessed byte on the wire, production-forbidden, hypothesis-ledger territory). **B–C** if run after Option 1.

### Option 3 — "Transport first" ([A] in full)

A Foundation-owned concurrent listener replacing `v141:7371`–`7850` and `7933`–`8007`; per-connection registry replacing the thread-local binding; a locked `sendall` on `AcceptedGameSocket`; an explicit lease policy replacing the silent per-account takeover; the dispatch exception boundary; and `LSCN_LoginVitalReq` decoded so account identity comes from the client instead of `--token`.

- **Cost:** 7 files (1 new) / 32 sites / **89 pinned + 351-closure test functions**; HYP-PF-011's two preconditions must land in the **same** change.
- **Gets:** two real clients served with isolated accounts and leases; the interlock bug fixed; and the **only** path to ever measuring a two-player fact on this project's wire.
- **Does not get:** the players seeing each other — that is still [B], and [B] still needs G1.
- **Risk: C.**

### Chief's recommendation (not a decision)

**1 → 2 → 3.** The reasoning is the owner's own rule. The only *irreversible* cost anywhere in this document is putting a guessed `actor_type` byte into a lane that later becomes production; Option 1 removes that risk entirely for the price of one report-only round, using the method the last six rounds already validated. Option 3 first would build a correct transport toward an unknown target — and if the remote-player actor turns out to want a per-scene actor registry rather than a per-connection one, that is exactly the *"ง่ายวันนี้แต่รื้อทีหลัง"* the rule forbids, just paid in a harder currency.

Two caveats against the chief's own recommendation, stated so the owner can weigh them:

- **Option 3's *shape* does not depend on G1.** A registry, a lease policy and an exception boundary look the same whatever the player actor turns out to be. A chief who wants to parallelise can start Option 3 without waiting.
- **The dispatch exception boundary should be landed regardless of which option is chosen.** It is a strict improvement on the single-player server today, it is risk **B**, and it is a precondition the ledger already recorded. Leaving it undone is the one choice this audit found no argument for.

---

## 6. What this audit could not answer

Stated plainly, because a silent gap is worse than a named one.

1. **What a second GameClient displays while queued.** Unmeasured — SESSION_LIMIT001's nonclaim 1 stands. No client was opened for this audit.
2. **Whether the original server was concurrent at all.** The original is closed and was never published; `v141` is a reconstruction notebook. **There is no ground truth for any concurrency, interest-management or fan-out policy, and there never will be.** Every design choice in [A] and [B] is therefore *our* design, not a recovered one, and must be labelled that way.
3. **Whether `LSCN_LoginVitalReq` carries a password.** The 38-byte record contains one wstring-tagged 4-byte field and one ASCII string. A single invariant capture cannot prove the absence of a field the client omits when empty.
4. **Engineering time.** Files, sites and test functions were counted. Hours were not estimated and should not be inferred from these numbers.
5. **Whether the client's `actor_type` dispatch has more than one branch.** No disassembly was run here — this audit is source-level only. The claim made is narrower and is verified: *no report or tool in the repository characterises it.* That is exactly the gap Option 1(a) fills.
6. **Whether `sqlite3` under WAL will hold up under two concurrent writers in this workload.** R08/R09 show the pragmas are set; no concurrency test exists, and none was run.

---

## 7. Reproduce

```
py -3 tools/pf_multiplayer_readiness_audit.py            # site/ready/frame tables, exit 0
py -3 tools/pf_multiplayer_readiness_audit.py --json     # machine-readable counts
py -3 -m pytest tests/test_multiplayer_readiness_audit.py -q
```

The test parses the `AUDIT_COUNTS` block below out of this file and compares it to a live run of the verifier, so no number here can drift away from the tree. **Every number in the block is compared exactly** (this changed in round 84 — see the erratum at the foot of this document; the six `*_at_head` numbers used to be compared with `>=` and that is how a stale figure survived).

**Re-pin, chief round 106 (2026-08-20): `package_b_pinned_test_functions` 52 -> 53.** Not drift and not a
correction: `tests/test_population.py` is one of the six package-B pinned files, and round 106 added one test to
it (`test_the_v94_provenance_paths_are_declared_machine_local`) so that the v94 provenance still has an assertion
on a machine whose `backups/` tree does not exist. The pinned-impact number counts test functions in those files,
so it had to move in the same commit as the test - which is the rule this block exists to enforce. Re-derived on
the gate machine by `py -3 tools/pf_multiplayer_readiness_audit.py --json`, computed and not quoted.

The `*_at_head` numbers describe commit `5cc0eda` and nothing else. They are pinned as constants in the verifier next to that commit and re-derived from it on every run with `git ls-tree` / `git cat-file`, so they can be proven wrong. The *live* suite size is reported by the verifier as `tests_total_files_today` / `tests_total_functions_today` and is deliberately not published here: a number that moves whenever anyone adds a test does not belong in a document that is not re-published when they do.

```json AUDIT_COUNTS
{
  "measured_at_head": "5cc0eda",
  "assumption_sites_total": 40,
  "assumption_sites_by_layer": {
    "transport": 12,
    "identity": 7,
    "world": 10,
    "capture": 6,
    "interlock": 5
  },
  "assumption_sites_immutable": 18,
  "assumption_sites_mutable": 22,
  "ready_sites_total": 17,
  "checkpoint_calls_at_try_depth_zero": 3,
  "game_listener_try_blocks_without_except": 1,
  "login_req_capture_guard": "reproduced",
  "frames_total": 18,
  "frames_anchored": 7,
  "frames_partial": 2,
  "frames_guess": 9,
  "package_a_files_touched": 7,
  "package_a_files_new": 1,
  "package_a_sites_covered": 32,
  "package_a_pinned_test_files": 7,
  "package_a_pinned_test_functions": 89,
  "package_b_files_touched": 5,
  "package_b_files_new": 2,
  "package_b_sites_covered": 6,
  "package_b_pinned_test_files": 6,
  "package_b_pinned_test_functions": 53,
  "package_a_closure_test_files_at_head": 29,
  "package_a_closure_test_functions_at_head": 351,
  "package_b_closure_test_files_at_head": 27,
  "package_b_closure_test_functions_at_head": 320,
  "tests_total_files_at_head": 61,
  "tests_total_functions_at_head": 663
}
```

## 8. Evidence manifest

See `PF_MULTIPLAYER_READINESS_AUDIT001_SINGLE_PLAYER_ASSUMPTIONS_20260818.manifest` (paths relative to the `Pirate Force` root).

## 9. Nonclaims

1. No claim that multiplayer should be built, or that any option here is approved. This document is input to a decision that has not been made.
2. No claim about the original server's concurrency, interest management, fan-out, routing authority or session policy. The original is gone; nothing in it can be recovered.
3. No claim that a human-player `actor_type` exists, has any particular value, or that the client would render one.
4. No claim that the ASCII field in `LSCN_LoginVitalReq` is the account name. Every archived capture carries the same value, so the field's role is an inference from the login UI, not a decoded variable.
5. No claim that the file, site and test counts here are an effort estimate.
6. No matrix row, ledger entry, hypothesis or `src/` file was changed by this audit.
7. No claim that `session_lifecycle/concurrent_multi_client` may move. It remains `blocked` behind HYP-PF-011's recorded preconditions, and this audit re-verifies rather than relaxes them.

---

## ⚠ ERRATUM 2026-08-19 (รอบ 84, SCAN-DEBT-001) — กฎเทียบตัวเลข suite เปลี่ยนจาก `>=` เป็น `==` (ตัวเลขในรายงานไม่เปลี่ยน)

**ตัวเลขที่ตีพิมพ์ไว้ถูกต้องทั้งหมด สิ่งที่ผิดคือกฎที่ใช้ค้ำมัน**

1. **สิ่งที่เน่าเงียบ** — `tests_total_files_at_head: 61` (และอีก 5 ตัวในตระกูลเดียวกัน) ถูกเทียบด้วยกฎ `>=` เทียบกับต้นไม้ **วันนี้** ด้วยเหตุผลว่า "suite โตได้ ห้ามหด" ผลคือเมื่อ suite โตเป็น **74 → 77 → 78 ไฟล์** เทสก็ยังเขียวตลอด (78 ≥ 61) ทั้งที่ตัวเลขในรายงานล้าไปแล้ว **17 ไฟล์** · คนอ่านที่เอา `package_a_closure 29/61` ไปคิดเป็นสัดส่วน "แพ็กเกจ A แตะ ~48 % ของ suite" จะได้เลขที่ผิดไปหนึ่งในสาม
   (เกรด C จาก `reports/PF_CORPUS_PIN001_DIRECTORY_SCAN_SURVEY_20260819.md` จุดที่ 6)
2. **ตัวเลขผิดไหม — ไม่ผิด** — รอบ 84 นับซ้ำจาก commit `5cc0eda` ตรง ๆ (`git ls-tree` + `git cat-file` แล้วเดิน AST ด้วยนิยามเดียวกับที่ใช้นับต้นไม้วันนี้) ได้ **61 ไฟล์ / 663 test functions · closure A 29/351 · closure B 27/320** ตรงกับที่ตีพิมพ์ทุกตัว ⇒ **ไม่มีตัวเลขไหนต้องแก้** ตัวเลขชุดนี้เป็น **ค่าประวัติศาสตร์ของ commit `5cc0eda` (2026-08-18)** ไม่ใช่ค่าปัจจุบัน และในเอกสารนี้อ่านแบบนั้นเท่านั้น
3. **กฎใหม่** — verifier ตรึงหกตัวนี้เป็นค่าคงที่คู่กับ commit + วันที่ (`HEAD_COMMIT` / `HEAD_MEASURED_AT` / `AT_HEAD` ใน `tools/pf_multiplayer_readiness_audit.py`) แล้ว **นับซ้ำจาก commit นั้นทุกครั้งที่รัน** · pin ไม่ตรงกับ commit ⇒ exit ≠ 0 · git ตอบไม่ได้ ⇒ exit ≠ 0 (ข้ออ้างเชิงประวัติศาสตร์ในเช็คเอาต์ที่มองประวัติตัวเองไม่เห็น คือข้ออ้างที่พิสูจน์ไม่ได้ คำตอบที่ซื่อสัตย์คือแดง ไม่ใช่เขียว) · เทสเทียบรายงานกับ pin แบบ **เท่ากันเป๊ะ**
4. **ค่าปัจจุบันไปอยู่ที่ไหน** — verifier ยังวัด suite วันนี้ให้ดู ในคีย์ `tests_total_files_today` / `tests_total_functions_today` แต่ **ไม่เอาเข้าบล็อก `AUDIT_COUNTS`** โดยตั้งใจ: ตัวเลขที่ขยับทุกครั้งที่ใครก็ตามเพิ่มเทส ไม่ควรอยู่ในเอกสารที่ไม่ได้ตีพิมพ์ใหม่ตอนนั้น (ณ 2026-08-19 = 78 ไฟล์ / 1142 test functions — บันทึกไว้ตรงนี้พร้อมวันที่ ไม่ใช่ pin)
5. **trap test** — `tests/test_multiplayer_readiness_audit.py::GuardWouldNoticeTests` พิสูจน์ว่า guard ยิงจริง: pin ที่เพี้ยนไป 1 ⇒ scan แดง · commit ที่ไม่มีอยู่ ⇒ scan แดง

ข้อสรุปของ audit (40 assumption sites / 18 immutable / 17 ready sites / 18 frames) **ไม่เปลี่ยน** — ตัวเลขชุดนั้นเป็น live measurement และถูกเทียบแบบเท่ากันเป๊ะมาตั้งแต่ต้น
