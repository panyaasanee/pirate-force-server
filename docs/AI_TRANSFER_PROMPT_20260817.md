# Copy-paste prompt for the receiving AI

คุณกำลังรับช่วงโปรเจกต์ Pirate Force Command 2 local-server reverse-engineering และ
implementation จาก AI ตัวก่อน เป้าหมายสุดท้ายคือทำให้เกมเล่นผ่าน GameClient ได้จริง
ครบ function-by-function พร้อม persistence/reconnect สำหรับ stateful function ไม่ใช่
เพียงทำ regression หรือ fixture แคบให้ผ่าน

Workspace หลักอยู่ที่:
`C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject`

มี worktree งาน visible console แยกอยู่ที่:
`C:\Users\Panya\Desktop\Pirate Force\Pirate Force ServerProject-console`

GameClient อยู่ที่:
`C:\Users\Panya\Desktop\Pirate Force\GameClient`

ก่อนทำอะไร ให้เปิดและอ่านตามลำดับ:

1. `AGENTS.md`
2. `docs/WORKFLOW.md`
3. `STATUS.md`
4. `docs/HYPOTHESIS_LEDGER.json`
5. `docs/EXPERIMENT_LEDGER.md`
6. `docs/COMMAND_HANDOFF.md`
7. `docs/AI_TRANSFER_HANDOFF_20260817.md`
8. `docs/AI_WORKSPACE_LEASE.json`

จากนั้นรันเฉพาะ read-only diagnostics ก่อน:

- `git status --short`
- `git worktree list`
- `git remote -v`
- `git diff --stat` ในทั้งสอง worktree
- ตรวจ ports 10188/10189 และ process GameClient/Foundation

ข้อห้ามสำคัญ:

- ใช้ workspace เดิมสามตำแหน่งที่ระบุไว้เท่านั้น ห้าม clone/copy project, สร้าง repo
  ใหม่ หรือเพิ่ม worktree/โฟลเดอร์ทำงานที่อื่น;
- โปรเจกต์นี้สลับผู้รับงานได้แต่ห้ามทำงานพร้อมกัน ก่อนเขียนไฟล์หรือรันอะไรต้องได้รับ
  การส่งมอบจากผู้ใช้และ claim `docs/AI_WORKSPACE_LEASE.json`; ถ้า lease ยัง active
  โดย executor อื่น ให้ทำ read-only และขอให้ผู้ใช้ยืนยันการสลับก่อน;
- ก่อนคืนงาน ให้หยุด process ที่คุณเปิด บันทึก Git/diff/test/runtime status และเปลี่ยน
  lease เป็น `handoff_ready` เพื่อให้ AI ถัดไปรับจากโฟลเดอร์เดิมได้ทันที;
- ห้าม `git reset --hard`, checkout ทับ, clean, stash, delete, move หรือสร้าง repo ใหม่
  ก่อนอ่าน dirty-worktree section ใน handoff;
- `references/` และ `evidence/` เป็น read-only;
- ห้ามอัปโหลด client binaries, decoded data, captures, DB, media หรือ proprietary
  evidence;
- authoritative local Git ไม่มี attached remote แต่มี private sanitized GitHub เดิม
  `panyaasanee/pirate-force-foundation-cloud` และ
  `panyaasanee/pirate-force-client-re-private` รวมถึง Codex environment
  `Pirate Force Foundation Cloud`; ห้ามสร้างของใหม่ซ้ำหรือ push local history ไปหา;
- ถ้าคุณเข้าถึง Cloud เดิมไม่ได้ ให้รายงาน limitation และทำ lane ที่ได้รับอนุญาตใน
  local workspace เดิม ห้ามสร้าง mirror/clone/Cloud environment ทดแทนเอง;
- ห้ามรัน server จริงแบบ hidden/background-only/Codex PTY;
- `--self-test-only` เท่านั้นที่ไม่ต้องมี visible console;
- ห้ามเรียก `GameClient.local.bin` ด้วย Start-Process ตรง ๆ เพราะจะเปิด Open with;
  ใช้ `GameClient\run_v142_client_only.bat`;
- ห้ามเรียก checkpoint แคบว่า feature complete.

สถานะ Git snapshot:

- implementation baseline ก่อน docs-only transfer commit คือ
  `0a91cd06d4796b6b03c414f9d31c19d3b7454063`; ให้ใช้ `git rev-parse HEAD`
  อ่าน exact current handoff commit และห้าม reset กลับ baseline
- `main` มี docs-only transfer commit อยู่เหนือ baseline และยังมี uncommitted
  partial Inventory diff 5 ไฟล์
- `codex/server-visible-console` มี uncommitted visible-console implementation และ tests
- ไม่มี server/client รันและ ports 10188/10189 ว่าง ณ handoff

ลำดับงานที่ต้องทำต่อทันที:

1. เมื่อผู้ใช้มอบสิทธิ์แล้ว claim canonical workspace lease; ห้ามสร้างโฟลเดอร์ใหม่
2. ตรวจและรักษา diff ทั้งสอง worktree
3. ทำ visible-console milestone ให้ผ่าน full verifier + Windows runtime ก่อน server run ถัดไป
4. commit console แยก แล้ว integrate เข้า main โดยไม่ทำ Inventory diff หาย
5. เพิ่ม Functional Coverage Matrix + verifier เพื่อให้ Inventory แสดง INCOMPLETE จน
   free move, same-slot, occupied swap/reject, stack/limit, split, equip/use/drop และ
   persistence/reconnect ครบตาม required rows
6. ทำ generic free-slot movement ให้รองรับ identity ที่มีจริงทุกชิ้นและช่องว่าง 0–39
7. ทดสอบ exact user request identity1 slot2→slot10, identity2, identity4, same-slot,
   occupied rejection, malformed/replay/session/account/concurrency/rollback/reconnect
8. หลัง free-slot runtime pass ให้ทำ occupied-slot swap/stack milestone ต่อ ห้ามปิด
   Inventory โดยปล่อยช่องนี้เงียบ ๆ

นโยบาย execution:

- WIP 1 milestone;
- Cloud-first เฉพาะ sanitized code/tests/static/docs/review เมื่อมี callable Cloud;
- Local-only สำหรับ proprietary/Windows/runtime/final gate;
- ห้ามรัน Cloud/Local ซ้ำโดยไม่มีเหตุผล;
- Cloud กับ Local ต้องทำงานตามลำดับภายใต้ lease เดียว ห้าม implementation พร้อมกัน;
- risk-based audit: high risk หนึ่ง independent audit หลัง frozen diff; medium targeted;
  low self-review; หนึ่ง corrective re-review เฉพาะ blocker/medium จริง;
- T0 static, T1 focused, T2 domain, T3 full verifierครั้งเดียวหลัง material diff freeze;
- runtime state ต้อง commit before success response;
- facts/inference/hypothesis/negative/superseded และ evidence grade A–E ต้องแยกกัน;
- HYP-PF-008 และ hypothesis อื่นยัง `production_allowed=false` จนหลักฐานครบ.

เมื่อเริ่มงาน ให้ตอบผู้ใช้เป็นภาษาไทยแบบสั้นโดยรายงาน:

- คุณอ่าน handoff แล้วหรือยัง;
- Git/worktree/remote/process status ที่ตรวจได้จริง;
- diff ใดที่กำลังรักษา;
- milestone เดียวที่กำลังทำ;
- blocker ที่พบจริง (ถ้าไม่มีให้บอกว่าไม่มี);
- จากนั้นดำเนินงานต่อโดยอัตโนมัติ ไม่หยุดเพียงเพราะ checkpoint แคบผ่าน.
