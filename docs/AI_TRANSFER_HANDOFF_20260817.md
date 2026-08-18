# Pirate Force — AI Transfer Handoff

Snapshot date: 2026-08-17 (Asia/Bangkok)

เอกสารนี้เป็นจุดเริ่มต้นสำหรับ AI ตัวใหม่ที่รับช่วง Pirate Force Command 2
ต่อจาก workspace ปัจจุบัน เป้าหมายไม่ใช่เพียงให้ regression ผ่าน แต่ต้องทำ local
server ที่เล่นผ่าน GameClient ได้จริงแบบ function-by-function พร้อม persistence และ
reconnect ในทุก stateful function

## 1. คำสั่งแรกและลำดับอ่าน

ห้ามเริ่มด้วยการ reset, clean, checkout, stash, move, delete หรือสร้าง repository ใหม่
เพราะมีงานที่ยังไม่ commit อยู่สอง worktree ให้ทำตามลำดับนี้:

1. อ่าน `AGENTS.md`
2. อ่าน `docs/WORKFLOW.md`
3. อ่าน `STATUS.md`
4. อ่าน `docs/HYPOTHESIS_LEDGER.json`
5. อ่าน `docs/EXPERIMENT_LEDGER.md`
6. อ่าน `docs/COMMAND_HANDOFF.md`
7. อ่านเอกสารนี้
8. รัน `git status --short`, `git worktree list`, `git remote -v` ทั้งสอง worktree
9. ตรวจ diff ปัจจุบันก่อนแก้ไฟล์ใด ๆ

รายงานยาวใน `reports/`, `handoff.txt`, backup manifests และ Git history เป็นหลักฐาน
ย้อนหลัง อย่าโหลดทั้งหมดหากยังไม่จำเป็นต่อ claim ปัจจุบัน

## 2. ตำแหน่งไฟล์และระบบ

### Workspace ownership — ห้ามย้ายหรือแตกโปรเจกต์

ผู้ใช้จะสลับให้ AI มากกว่าหนึ่งระบบรับช่วงงานนี้เป็นระยะ แต่จะไม่ให้ทำงานพร้อมกัน
ดังนั้นตำแหน่งด้านล่างเป็น workspace กลางชุดเดียวและต้องคงเดิม:

- ใช้ main worktree เดิมและ visible-console worktree เดิมเท่านั้น;
- ห้าม clone repository, copy project, สร้าง repository ใหม่ หรือเพิ่ม Git worktree
  ที่ตำแหน่งอื่น เว้นแต่ผู้ใช้อนุมัติเป็นกรณีเฉพาะ;
- ห้ามเปลี่ยนชื่อ ย้าย หรือสร้างสำเนา `GameClient`, `state`, `reports`, `backups`,
  `references` หรือ `evidence` เพื่อใช้เป็น workspace ใหม่;
- งาน source ต้องส่งต่อด้วย Git commit/diff ใน repository เดิม ไม่ใช่คัดลอกไฟล์ข้าม
  project clone;
- proprietary/runtime artifacts ต้องอยู่ในตำแหน่งเดิมและยังคง local-only;
- ถ้าระบบ AI อื่นไม่สามารถเข้าถึง absolute paths เหล่านี้ได้ ให้หยุดและรายงาน
  blocker ห้ามสร้าง mirror หรือจำลองสถานะใหม่เอง.

Canonical lease อยู่ที่ `docs/AI_WORKSPACE_LEASE.json` และใช้ป้องกันงานซ้อน:

1. ก่อนแก้ไฟล์หรือรัน server/client ต้องอ่าน lease, Git status, process และ ports;
2. ผู้รับช่วงแก้ lease เป็น `active` พร้อมชื่อ executor และเวลา เมื่อผู้ใช้มอบสิทธิ์แล้ว;
3. มี executor ที่สถานะ `active` ได้เพียงหนึ่งรายเท่านั้น;
4. AI ที่ไม่ได้ถือ lease ทำได้เฉพาะตอบคำถาม/read-only และห้ามแก้ไฟล์ รัน verifier,
   server หรือ Client;
5. ก่อนส่งคืน/สลับ AI ให้หยุด process ที่ตนเปิด, บันทึก diff/test/runtime status,
   แล้วเปลี่ยน lease เป็น `handoff_ready`;
6. ห้ามรับช่วงจาก lease ที่ยัง `active` โดยไม่มีคำยืนยันจากผู้ใช้ว่า executor เดิมหยุดแล้ว;
7. ห้ามใช้เวลาเดียวกันทำ implementation คนละ worktree เพราะสุดท้ายยังเป็น repository และ
   roadmap เดียวกัน; console worktreeมีไว้แยก milestone ไม่ใช่อนุญาตให้ทำงานขนาน.

### Repository และ server

- Main project/worktree:
  `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject`
- Visible-console worktree:
  `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject-console`
- Foundation package:
  `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject\src\pirateforce_foundation`
- Server entry point: `src/pirateforce_foundation/app.py`
- Immutable legacy adapter source: `current/pf_login_game_server_v141.py`
- V141 SHA-256:
  `2EB05ED2FDBDD5EE3D91F7FBB8C1D16A4C7A02A843BC97169B16A389E4EA4C22`
- Migrations: `migrations/001_initial.sql`, `002_character_integrity.sql`,
  `003_character_inventory.sql`
- Runtime databases: `state/` (ignored; never publish)
- Reports: `reports/`; frozen/backups: `backups/`
- `references/` and `evidence/` are read-only; never edit, move, rename or delete
- Default listeners: LOGIN `127.0.0.1:10188`, GAME `127.0.0.1:10189`

### GameClient

- Client root: `C:\Users\Panya\Desktop\Pirate Force\GameClient`
- Original client: `GameClient.bin`
  - SHA-256 `C528BF43070E2789170F41B6E3E28CCEC6B57BDC594EE73DFA061188A5D1E4BD`
- Local patched client: `GameClient.local.bin`
  - SHA-256 `9627211412AC60D50AD189CE5A629443CE928EC23A9F8D219DFB2B157028B623`
- Correct client launcher: `GameClient\run_v142_client_only.bat`
- Do not call `Start-Process GameClient.local.bin` directly. Windows treats `.bin`
  as a document and opens **Open with**. Use the accepted batch, which supplies:
  `-launchbypatcher -subbuildversion 132 -acc test -pwd test`.
- Captures live under `GameClient\capture_*`; they are proprietary, ignored and local-only

### Git and GitHub

- The authoritative local repository has no attached remote: `git remote -v` is
  empty. Never attach/push the full local history.
- Existing private sanitized GitHub repositories are:
  - `panyaasanee/pirate-force-foundation-cloud` — sanitized Foundation code-only;
  - `panyaasanee/pirate-force-client-re-private` — restricted private RE pilot with
    a read-only client copy and checksum-gated analyzer.
- GitHub's ChatGPT Codex Connector was configured with access limited to those two
  private repositories, not the full account.
- Existing Codex Cloud environment: `Pirate Force Foundation Cloud`, branch `main`,
  universal image, automatic setup/cache enabled, agent internet off, no secrets or
  environment variables.
- A first read-only Cloud smoke passed compile plus seven portable tests. The RE
  analyzer Cloud result remains pending/visibility-blocked and is not accepted
  evidence.
- These Cloud/GitHub locations are sanitized auxiliary workspaces, not the
  authoritative runtime repository. Never upload GameClient, decoded data,
  captures, DB, reports/evidence, media, backups, packages, secrets, machine paths
  or frozen V141 source/launcher.
- Current main branch: `main`
- Implementation baseline immediately before this docs-only transfer commit:
  `0a91cd06d4796b6b03c414f9d31c19d3b7454063`. Run `git rev-parse HEAD`
  to obtain the exact current handoff commit; do not reset back to the baseline.
- Visible-console worktree/branch remains at the implementation baseline above with
  its own preserved uncommitted diff.
- Recent commits:
  - `0a91cd0 docs: record free-slot item move request capture`
  - `49a0e1a docs: adopt lean cloud-first project workflow`
  - `14c470f docs: record second password bypass runtime pass`
  - `ea5789c fix: rate limit second password bypass pulses`
  - `cfb606b fix: pulse second password bypass on runtime polls`
  - `9290032 fix: expose second password server mode`
  - `da03625 feat: add test-only second password bypass`
- Do not create replacement GitHub repositories, Cloud environments, local clones or
  local worktrees merely because a different AI receives the task. If the receiving
  AI cannot access the existing sanitized Cloud surfaces, report that limitation and
  continue the authorized local-only lane; do not duplicate them.

## 3. Current runtime state

At this snapshot:

- no GameClient process is running;
- no Foundation server process is running;
- ports 10188/10189 are free;
- do not start another server until the mandatory visible-console milestone below
  is integrated.

Current Item Move HYP database:

- path: `state/item_move_hyp001_25690817_002012.sqlite3`
- SHA-256:
  `EA1C4459F9E88322EE4689B2C2A13C0465CF57BE35F2B47FEB1ED6D74EDD8F3B`
- SQLite integrity: `ok`; foreign-key check: empty
- exact current Backpack rows:
  - identity 1, template 2600001, quantity 2, slot 2
  - identity 2, template 2400901, quantity 1, slot 1
  - identity 4, template 2200002, quantity 1, slot 3
- all retained sessions are closed
- associated capture root:
  `C:\Users\Panya\Desktop\Pirate Force\GameClient\capture_item_move_hyp001_25690817_002012`

## 4. Evidence and claim discipline

Every claim must retain its grade:

- A — exact original capture or exact static producer/consumer proof
- B — uninstrumented emulator runtime pass
- C — instrumented runtime trace
- D — compositional hypothesis
- E — operational negative

Never broaden a claim from a narrower test. Facts, inferences, hypotheses, bounded
negatives and superseded claims must remain separated. V141 regression does not
broaden any historical claim. Unknown Avatar/job/class/equipment/skill fields remain
opaque.

Canonical hypothesis governance is in `docs/HYPOTHESIS_LEDGER.json`; all guesses are
test-only, `production_allowed=false`, have falsification/stop rules and expire after
at most 2–3 dependent experimental versions unless exact scoped approval exists.

### 4.1 ชื่อ Vital ทั้งหมดอยู่ที่ `docs/PF_VITAL_NAMES.json` (NAMES-HOME-001, 2026-08-19)

ตาราง `id -> ชื่อคลาส Vital` ของโปรเจกต์มี **ที่เดียว** คือ `docs/PF_VITAL_NAMES.json`
(52 entry = 49 ชื่อเดิมของ v141 + `0x1B40 LogoutVital`, `0x36DB DeleteActorVital`,
`0xAC52 Channel_LocalTalkMessageVital` ที่ PF-NAMEID-RESOLVE-001 แกะจาก client binary)
อ่านผ่าน `tools/pf_vital_names.py` (pure stdlib)

> **⚠️ ห้ามเติมชื่อใหม่ลง `current/pf_login_game_server_v141.py` เด็ดขาด ⚠️**
>
> `NAMES = {...}` ใน v141 เคยเป็นตารางชื่อเดียวของโปรเจกต์มา 141 เวอร์ชัน — AI ที่เขียน
> ไฟล์นั้นมาเองจะเผลอเติมที่เดิมตามความเคยชิน (**ความเสี่ยงสูงเป็นพิเศษในกะ Codex**)
> แต่ตอนนี้ v141 เป็น **snapshot ส่งมอบที่แช่แข็ง** ไว้เป็นตัวเทียบว่า rewrite ไม่หลงทาง
> ไม่ใช่หลักฐานดิบ และไม่ใช่ "original server" (server ต้นฉบับปิดไปแล้วและไม่เคย publish)
> มี sha256 guard ใน `tools/verify_hypothesis_ledger.py` กันไว้ **ห้ามแก้แม้แต่ไบต์เดียว**
>
> `tests/test_vital_names_table.py` จะจับได้ทันทีถ้ามีชื่อโผล่ใน v141 แต่ไม่มีในตารางเรา
> — จับได้ก็จริง แต่**เสียเวลาไปหนึ่งรอบ** ให้เติมที่ `docs/PF_VITAL_NAMES.json` ที่เดียว
>
> English: never add a resolved Vital name to the frozen v141 snapshot. Add it to
> `docs/PF_VITAL_NAMES.json` only. The test will catch it, but it costs a round.

เงื่อนไขการเพิ่ม entry ใหม่ (ต้องครบทั้งสองข้อ, เทสบังคับ):

1. **hash ตรง** — `wire_id(name) == id` ตามสูตรรอบ 62
   (`id = Σ_i (signed char)name[i] * (i+1) mod 2^16`)
2. **หลักฐาน literal → slot** — ชื่อเป็น string literal ตัวเดียวใน
   `GameClient/GameClient.local.bin` และ `push` ของมันอยู่ใน registration thunk
   `push <lit>; call 0x89C080; mov ecx,eax; call 0x89BD00; mov word ptr [<id-slot>], ax; ret`
   บันทึก id-slot VA ลงฟิลด์ `id_slot_va` และอ้างไฟล์ finding ในฟิลด์ `evidence`

ยาม: `python -m pytest tests/test_vital_names_table.py -q` และ
`py -3 tools/pf_vital_id_resolve_static.py` (43 guards, เดิม 35)

## 5. Architecture already accepted

Foundation is typed modular Python with SQLite behind a repository seam. Accepted
work includes:

- migration/checksum/transaction gates;
- one configured local test account (not authenticated multi-account ownership);
- Create/List/Select/StartGame identity continuity;
- lossless opaque actor/avatar persistence;
- ActorAttr/AvatarAttr/MovementAttr identity agreement;
- player ActorAttr name projection and runtime-visible local nameboard;
- finite TargetPos checkpoint before wire, reconnect and process-restart recovery;
- exact per-connection lease close, clean requested server shutdown and abrupt
  server/client process recovery within their report ceilings;
- typed authoritative NPC-style nearest-20 population transitions with omission
  removal and re-entry (not monster/remote-player semantics);
- exact Backpack seed, V111 identity3→identity1 quantity-2 merge, committed
  persistence and reconnect projection;
- server-controlled second-password mode:
  `--second-password-mode required|bypass` (default `required`), with bounded bypass
  pulses and no credential stored;
- strict capture-only item-move mode and exact original-client request for
  op4/destination slot2/identity1;
- static consumer proof that ItemOperate result routes by identity and incoming slot.

See STATUS/ledger/reports for exact ceilings. Major unresolved domains include broad
inventory movement, occupied-slot swap/stack policy, equipment, skills/hotbar,
job/class, remote player, authentic monster behavior/combat/damage/death/loot,
vehicles/portals/economy/social/quests.

## 6. User policy decisions that are now mandatory

### 6.1 Narrow checkpoint is not feature completion

The user identified that the project could mark a tuple-level checkpoint complete
while leaving the actual function unusable. From now on:

- a narrow fixture/golden proves one fact; it never closes a domain function;
- create a machine-readable and user-readable Functional Coverage Matrix;
- every required capability has `not_started`, `in_progress`, `blocked`,
  `runtime_pass` or `complete`, plus test/evidence links;
- STATUS must say `Inventory: INCOMPLETE` while any required row is not complete;
- verifier must reject `domain_complete=true` if required rows are not green;
- every handoff must name the next missing behavior;
- full stateful completion requires UI/wire, DB persistence, reconnect and negative paths.

Minimum Inventory coverage rows requested by the user:

- Backpack open/display;
- persisted projection/reconnect;
- move any known item to any free slot 0–39;
- same-slot no-op;
- missing identity/out-of-range/malformed/replay/session/account isolation;
- occupied destination with different item: swap/reject policy;
- compatible stack merge and stack limit behavior;
- split stack;
- equip/unequip;
- use/drop/sell paths (separate milestones but visible as incomplete).

### 6.2 Occupied-slot behavior is planned, not silently omitted

Free-slot move is first. Occupied destinations must remain safe-reject until exact
behavior is established. Separate cases:

- same slot → no-op;
- compatible item → merge only when stack rules/limits are proven;
- different item → capture and determine swap/displacement/reject;
- equipment destination may use another operation.

If original policy remains unavailable, expose an explicit server parameter such as
`reject|swap`; default `reject`; any swap mode remains ledgered Grade D until runtime
and persistence/reconnect evidence exist. Swap transaction must update both rows
atomically and preserve the unique `(character_id, slot)` constraint.

### 6.3 Visible server console is mandatory

The user explicitly requires **every actual server invocation**, manual or automated,
to display a visible console throughout its lifetime.

- hidden server windows and Codex-only/background PTY servers are forbidden;
- `--self-test-only` is the sole exception because it does not open listeners;
- summary stdout/stderr must mirror to deterministic UTF-8 per-run files;
- raw GAME/LOGIN/packet hex remains file-only to avoid console rendering load;
- Ctrl+C or the accepted bounded signal helper must stop the exact visible process;
- console is for observation/control; retained files are authoritative evidence.

### 6.4 Cloud/local allocation

- Cloud-first for sanitized code, portable unit tests, static analysis, docs and
  independent code review;
- Local-only for GameClient, proprietary binaries/data, raw captures, native probes,
  Windows UI/console, evidence-bound SQLite and final runtime gate;
- never run Cloud and Local duplicates without a named purpose;
- the authoritative local repository has no remote, but the existing sanitized
  GitHub repositories and `Pirate Force Foundation Cloud` environment above do
  exist. Use them only if the current AI has authorized access;
- Local worktree or sub-agent is **not Cloud**. Do not pretend otherwise;
- do not create or replace Cloud/GitHub surfaces without explicit user approval;
- Cloud and Local are sequential executors under the same workspace lease policy,
  never simultaneous competing implementations.

### 6.5 Lean review/test policy

- one active milestone/WIP limit 1;
- one implementer + one independent reviewer only when risk tier requires it;
- third reviewer only for genuinely high-risk cross-domain work;
- review only a frozen diff, one corrective re-review for real blocker/medium;
- T0 static, T1 focused, T2 domain, T3 full verifier once after frozen material diff;
- docs-only corrections use T0 + artifact rehash, not automatic T3;
- no repetitive audits/status polling that do not advance implementation.

## 7. Dirty worktree preservation — critical

### 7.1 Main worktree: partial generic free-slot Inventory implementation

Path: `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject`

Modified, uncommitted files (190 insertions / 19 deletions):

- `src/pirateforce_foundation/inventory.py`
- `src/pirateforce_foundation/lifecycle.py`
- `src/pirateforce_foundation/repository.py`
- `src/pirateforce_foundation/session.py`
- `src/pirateforce_foundation/store.py`

Intent already implemented partially:

- govern exact initial or merged item contents while allowing unique slots 0–39;
- pure `move_known_item_to_free_slot` transition;
- generic one-ItemAttr ItemOperate result builder pinned to the slot2 golden;
- repository/lifecycle/session generic free-slot move seam;
- no occupied-slot swap; occupied destination raises/rejects;
- baseline/no-scenario still rejects moved hypothesis states.

This diff is incomplete. It has not yet been integrated into runtime parser/scenario,
ledger or general tests. Do not commit or run runtime from it until completing:

- canonical op4 request parsing for any identity and destination 0–39;
- scenario profile for general known-item/free-slot behavior;
- runtime dispatch and dynamic full ItemAttr response;
- tests for identity1/2/4, multiple destinations including slot10, same slot,
  occupied destination, missing identity, malformed/envelope, replay, rollback,
  concurrency, stale/cross-account/read-only and reconnect;
- hypothesis ledger update as `ITEM-MOVE-HYP-002`, still HYP-PF-008,
  `production_allowed=false`;
- Functional Coverage Matrix.

### 7.2 Visible-console worktree: separate uncommitted platform milestone

Path: `C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject-console`

Branch: `codex/server-visible-console`, HEAD still `0a91cd0`.

Intended changed/new files:

- `.gitignore`, `AGENTS.md`, `README.md`, `STATUS.md`
- `docs/COMMAND_HANDOFF.md`, `docs/WORKFLOW.md`
- `src/pirateforce_foundation/app.py`
- new `src/pirateforce_foundation/runtime_console.py`
- new `tests/test_runtime_console.py`
- `tools/build_foundation_release.py`
- `tools/run_scene2_load_only.ps1`
- `tools/run_test_arena.ps1`
- `tools/verify_foundation.ps1`
- new `tools/run_foundation_visible.ps1`

Behavior:

- actual runtime calls Windows `ShowWindow` or `AllocConsole`;
- console title includes mode and DB name;
- stdout/stderr mirror to `server_console_live.out.txt/.err.txt` using UTF-8,
  line-buffered, locked streams;
- existing log files cause fail-closed refusal instead of overwrite;
- scenario launchers use `-WindowStyle Normal`;
- self-test-only does not open a console;
- raw protocol logs remain unchanged.

Verification already run:

- focused console/shutdown/connection suite: **32/32 PASS**;
- compile and PowerShell parser checks: PASS;
- diff-check: PASS except LF→CRLF advisories;
- full verifier discovered 234 tests and ended with three `FileNotFoundError`s only
  because the separate worktree lacks local read-only `backups/` and `evidence/`
  artifacts. The console tests themselves passed. This is not yet a T3 PASS.

Important worktree artifact note: reports were copied from main into the console
worktree only to satisfy ledger provenance. `git status` may show many manifest files
as modified due line-ending/stat-cache effects, but `git diff --name-only` and
`--numstat` show no semantic manifest diffs. Do not stage or commit those manifest
false positives.

Before the next actual server run:

1. give the console worktree read-only copies of the exact evidence files required
   by tests (never modify originals), or integrate the console commit carefully and
   run T3 from the full main workspace;
2. pass full verifier;
3. run one isolated Windows runtime proving visible console, mirrored logs, raw logs,
   Ctrl+C, one stopped marker and exit 0;
4. commit the console milestone separately;
5. integrate it into main without overwriting the dirty Inventory files.

Do not combine the platform/console commit with the protocol/Inventory commit.

## 8. Latest Item Move runtime facts

Capture-only checkpoint is committed and reported:

- report: `reports/PF_ITEM_MOVE_CAPTURE001_FREE_SLOT_REQUEST_RUNTIME_PASS_20260817.md`
- exact client request for identity1 moving to slot2:
  op4, value32=2, identity=1; no response in capture-only mode; DB unchanged.

Uncommitted HYP-PF-008 runtime in `capture_item_move_hyp001_25690817_002012`:

- Round A composed slot0→slot2 move sent one response;
- Client UI immediately showed slot0 empty and quantity-2 key at slot2;
- DB committed identity1 slot2;
- Round B reconnect projected and visually showed the same persisted slot2 state;
- then the user requested moving that key down one grid row;
- Client emitted exact frame/event at `2026-08-17T00:34:34.986`:
  op4, `value32=10`, identity1;
- current hardcoded slot2 scenario sent no response, so the Client did not commit the
  visual move and DB remained slot2;
- this exact original-client slot10 request is the new evidence justifying the
  HYP-PF-008 second bounded version/general free-slot implementation;
- runtime report/manifest for HYP-001 has not yet been authored/accepted.

## 9. Required resume order

1. Claim the canonical workspace lease after the user transfers control; do not
   create another project folder/worktree/clone.
2. Preserve and inspect both dirty worktrees; verify no runtime process/ports.
3. Finish and accept the visible-console milestone in the console worktree.
4. Integrate its separate commit into main without reset/clean and without losing the
   partial Inventory diff.
5. Add Functional Coverage Matrix + verifier before calling Inventory complete.
6. Finish generic free-slot movement in main:
   - every exact known item identity;
   - every currently empty destination 0–39;
   - full current ItemAttr response;
   - transaction commit before response;
   - persistence/reconnect;
   - safe rejection of occupied slots.
7. Run focused/domain tests, then one full verifier after frozen diff.
8. Start server only through the newly accepted visible-console path.
9. Runtime test at least:
   - identity1 slot2→slot10 (the user-requested down-one-row case);
   - identity2 to another free slot;
   - identity4 to another free slot;
   - same-slot no-op;
   - occupied destination safe rejection;
   - reconnect showing all successful slots;
   - DB integrity/FK/session/identity/content allowlist.
10. After free-slot runtime pass, keep Inventory INCOMPLETE and start the named
   occupied-slot swap/stack-policy milestone; never silently omit it.

## 10. Verification commands

Full authoritative local gate:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify_foundation.ps1
```

Normal server-only visible launcher after acceptance:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File tools\run_foundation_visible.ps1 `
  -Database state\pirateforce.sqlite3 `
  -SecondPasswordMode bypass
```

Correct Client launcher after both listeners are ready:

```powershell
cmd.exe /c "C:\Users\Panya\Desktop\Pirate Force\GameClient\run_v142_client_only.bat"
```

Never issue a destructive Git/filesystem command against a broad path. Never delete
old versions per iteration. Cleanup requires explicit approval, manifests and exact
recoverable target validation.

## 11. Communication contract with the user

- Thai is the working language unless the user changes it.
- Lead with the concrete result, not reviewer/tool chatter.
- Admit bounded gaps plainly; do not equate a passing fixture with a finished feature.
- Keep updates short and meaningful.
- Continue autonomously within the approved roadmap; ask only when a decision would
  materially change scope, external authority, upload/remote, or destructive state.
- The user expects the server console to remain visible during every runtime test and
  may interact with the Client. Identify the screen before clicking and do one bounded
  action at a time.
