[LANE-B (COMBAT) round `hqzp16` · 2026-09-01T12:47+07:00 (scheduled, no one watching the screen)]

# ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้คอมเมนต์เท่านั้น ไม่แตะ `runtime.py`/`app.py`/behavior ใด ๆ

# ต้นรอบ

1. อ่าน `pf_bridge/NOW.md` ก่อนเสมอ: มีงานด่วน 3 ข้อ (PANYA-ORDER 20260901_0215, ไมล์สโตน M1-M6
   พักไว้ทั้งหมด) -- **P-1** (ของดรอปต้องอยู่บนพื้นนานพอ) เป็นของ LANE-B ตาม
   `CHIEF_CONTINUATION.md` หัวข้อ "ลำดับงานปัจจุบัน"
2. ตรวจ PR ล่าสุดของสายนี้ทั้งสองรีโป ด้วย `pull_request_read get` (ไม่ใช่ `list_pull_requests`'s
   `merged` field ซึ่งอ่านผิดเป็น `false` เสมอสำหรับ PR ที่ merge แล้ว -- tool quirk ที่ chief
   บันทึกไว้แล้ว, ยืนยันซ้ำรอบนี้): `pf_bridge#701` และ `pirate-force-server#467`
   ("register COO-RULING-20260901-1046", round `4qwc1x`) ทั้งคู่ `merged: true` -- ไม่มีงาน
   ต้องกู้คืน
3. กล่องจดหมาย `pf_bridge/notes_to_chief/`: grep `ADDRESSEE: LANE-B` ที่ยังไม่มี `.CONSUMED.txt`
   หรือสำเนาใน `consumed/` -- **ไม่พบ** (mailbox สะอาด, ไม่มีใบต้องบริโภครอบนี้)
4. ไล่ P-1/gate 1-4/pickup/Door B ซ้ำที่ HEAD ตามที่รอบ `h40iwu` (05:50) ทำไว้: ทุกเส้นยังปิดด้วย
   เหตุผลเดิม P-1 เดินสายแล้วโดย chief (`app.py:890`,
   `20260901_0507_CHIEF-REPLY-CORE-REQUEST-heartbeat-preserve-wired.md`) รอ `GT-188` (attended)
   -- ไม่มีงานโค้ดใหม่ให้ทำที่ P-1 เอง

# สิ่งที่ทำแทน (กฎ F ข้อ ง: technical debt)

พบว่า `src/pirateforce_foundation/mob_loot.py`'s หัวคอมเมนต์ `HEARTBEAT-PRESERVE-001` (ฟังก์ชัน
`preserve_ground_heartbeat_pc`/`preserve_ground_heartbeat_frame` ที่สายนี้เขียนไว้เอง) ยังพูดว่า
**"not yet wired anywhere"** -- เป็นเท็จมาตั้งแต่รอบ chief ที่เดินสายจริงแล้ว (`app.py:890`)
แก้ตามกฎเดียวกับที่ปิด R227 D5: ขีดฆ่า (`~~...~~ IS STRUCK`) ไม่ลบ แล้วเขียนสถานะจริง

**pf-adversary รอบนี้ (subagent จริง, isolated worktree) จับได้ 1 defect ในร่างแรก**: ร่างแรกเขียนว่า
"wiring... และมันเสร็จแล้ว" แล้วอ้างจดหมาย chief แต่ยกมาแค่ 1 ใน 3 ข้อที่จดหมายนั้นเองบอกว่ายังไม่พิสูจน์
(หยิบเฉพาะ `GT-188` ทิ้งข้อที่ว่า **"ยังไม่มีเทสระดับ boot ของ app.py ในรีโปนี้เลย"** -- ยกจากถ้อยคำ
จดหมายเอง) แก้แล้ว: คอมเมนต์เวอร์ชันสุดท้ายยกมาครบทั้งสามข้อของจดหมาย chief (ความถูกต้องของการอ่าน
image ของ Codex / attended proof GT-188 / ไม่มีเทสระดับ boot) และระบุตรงว่าสิ่งที่ยืนยันได้จริงมีแค่
source-order assertion กับ unit test ที่ใช้ stand-in function ชื่อ `heartbeat_worker` เอง ไม่ใช่
v141 thread ผ่าน server boot จริง -- ไม่เกินคำยืนยันของหลักฐานที่อ้างถึง

pf-adversary ตรวจเพิ่ม: citation ของ `app.py:890` ถูกต้อง (unconditional, ไม่มี flag), กลไก
caller-frame check ตรงกับโค้ดจริง, จดหมาย chief มีอยู่จริงตรงเนื้อหา, diff เป็น comment-only จริง
(เทียบ bytecode ก่อน/หลัง เท่ากันไบต์ต่อไบต์), suite เต็มผ่าน, ไม่พบจุดอื่นในคอมเมนต์บล็อกเดียวกันที่
ต้องแก้เพิ่ม

# เทส

```
targeted: tests/test_mob_loot.py -> 97 passed, 12 subtests passed (ก่อนและหลังแก้ตามที่ pf-adversary สั่ง)
full suite: 6221 passed, 323 skipped, 13162 subtests passed, 0 failed (158.47s)
git diff: comment-only ยืนยันด้วย bytecode diff ของ pf-adversary
```

# ยังไม่ได้พิสูจน์

- `GT-188` ยังไม่มีคนเทส attended -- ไม่ใช่งานของรอบนี้
- ไม่มีเทสระดับ boot ของ `app.py` ในรีโปนี้ (ตามที่คอมเมนต์ฉบับแก้ระบุไว้เอง) -- ใครเป็นเจ้าของงานนั้น
  ยังไม่มีคำตอบ เขียนเป็นคำถามปิดท้ายจดหมายรอบนี้แล้ว

# CORE-REQUEST

ไม่มี (ไม่แตะ `runtime.py`/`app.py`)

# เปิดใบให้สาย C

ไม่มี

# ไฟล์ที่แตะ

- `src/pirateforce_foundation/mob_loot.py` (คอมเมนต์เท่านั้น)
- `rounds/B_20260901_1247_hqzp16_heartbeat-preserve-doc-correction.md`

-- LANE-B (COMBAT) รอบ `hqzp16`
