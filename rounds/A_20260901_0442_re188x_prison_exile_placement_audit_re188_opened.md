# LANE-A round `re188x`

2026-09-01T04:22+07:00 - 2026-09-01T04:42+07:00 (+07:00 via `TZ=Asia/Bangkok date`).

**ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน:** ไม่มี - รอบนี้เป็นรอบตรวจสอบ (audit) ไม่ใช่รอบสร้าง ไม่มีการแก้
`KNOWN_PLACEMENTS` แถวใดเลย เพราะหลักฐานที่พบขัดแย้งกับการแก้แบบเดา (ดูข้อ 2) เขียนไว้ตรง ๆ ตามที่
CHARTER-02 ห้ามการยัดตัวเลขใหม่แบบไม่ยืนยัน แทนที่จะสร้างของที่ไม่แน่ใจ รอบนี้เปิด RE-188 ให้ RE runner
ตรวจต่อ และปิดคำถามที่ RE-173 ทิ้งไว้ (96 placement ที่เหลือ) ให้ชัดว่าเหลืออะไรจริง (4 ตัว ไม่ใช่ 0)

## 0. บริบทก่อนเริ่ม (ตรวจ mailbox ก่อนเชื่อ prompt เก่า)

`grep "ADDRESSEE: LANE-A"` ทั้ง `notes_to_chief/*.md`: ไม่มีใบค้างที่ยังไม่มี `.CONSUMED.txt`/ไม่ได้ย้าย
`consumed/` (ใบ STATUS สามใบล่าสุดของสาย A เองไม่ใช่ใบถึงสาย A - ไม่ต้องมี stub) ทั้งสองใบ ASK-COO เก่าของ
สาย A (`which-reader-of-the-door-wins`, `scene10-landing-geometry-elevated-risk`) มี COO-DECISION ตอบและ
consume แล้วตั้งแต่รอบก่อน ไม่มี `*CLAIM-LANE-A*` อายุไม่เกิน 90 นาทีค้าง ไม่มี `[LANE-A]` PR เปิดค้าง
(ตรวจ GitHub API: PR ล่าสุดของสาย A ทั้งสองรีโป - server `#436`, bridge `#661` - `merged=true` ทั้งคู่ งาน
รอบก่อนอยู่บน `main` แล้วจริง ตามข้อ A ของ ADDENDUM v2)

Fast-forward local branch ทั้งสองรีโปไปที่ `origin/main` ปัจจุบันก่อนเริ่ม (server มี PR `#438` ของ chief
merge เข้ามาใหม่ระหว่างรอ - `runtime.py` ส่วน GM warp resync - ไม่แตะไฟล์นั้นรอบนี้อยู่แล้ว)

## 1. ทำไมเลือกหัวข้อนี้

BUILD-001/BUILD-002 ทั้งคู่เสร็จแล้ว (10/10 ประตูเปิด ตั้งแต่รอบ `yfbqmg`; Columbus RE-173 ปิดแล้วรอบ
`re173w`) M3/`Bg0015` เป็นประวัติเก่าที่ wire เข้า `runtime.py` แล้วนานแล้ว `GT-180` (ฉาก 130, ประตูสุดท้าย)
`BLOCKED-ON-ATTENDED` รอคนหน้าจอ ไม่มีอะไรให้สาย A ทำต่อ คำถาม hostility_lines override/ledger ที่ chief
ทิ้งไว้ (รอบ `yfbqmg`) ยังไม่มี COO-DECISION ตัดสินเจ้าของไฟล์ ไม่ใช่ของสาย A ที่จะหยิบเองตอนนี้ - ตาม
ADDENDUM v2 ข้อ F (รอบว่างครั้งที่สองเท่านั้นที่บังคับหยิบ backlog) นี่เป็นรอบว่างครั้งแรกหลังรอบที่มี diff
(`re173w`) แต่เลือกหยิบ backlog เองอยู่ดี (ตัวเลือก ง: technical debt ที่ RE-173 เองทิ้งไว้ตรง ๆ ว่า "ไม่ได้
audit อีก 96 placement... เป็นคำถามเปิดสำหรับรอบ/ใบในอนาคต") แทนที่จะรายงานรอบว่างเฉย ๆ

## 2. งานที่ทำ - crosswalk อีก 96 placement ด้วยวิธีเดียวกับ RE-173

Sanity check ก่อน: sha256 ของ `CONSTDATA_TH__CLINE.tsv`/`CONSTDATA_TH__MOBS.tsv`/
`Bg0002.placements.tsv` ตรงกับ `SOURCE_DIGESTS` ที่ปักไว้ในไฟล์อยู่แล้วทั้งสามไฟล์ (ไม่มีการเปลี่ยนแปลงต้น
ทางระหว่างที่ไฟล์นี้ไม่ได้แตะ)

Script ใช้แล้วทิ้ง (ไม่ commit): parse `KNOWN_PLACEMENTS` ทั้ง 97 แถว, เอา Mob-Set number (`NN`, เท่ากับ
`n_id` ปัจจุบันของทุกแถวยกเว้นแถว 63 ที่แก้เป็น 360 แล้ว - ใช้ 36 สำหรับแถวนั้น) มาเทียบกับ CLINE type-2
table: `CONSTDATA_TH__CLINE.tsv` filter `n_CLINE_TYPE==2`, สร้าง `{n_CREATURE_TYPE: n_LEADER_BK1}`,
เช็ค BK2/BK3/crew ทุกช่องเป็น 0 (ไม่มี ambiguity) ก่อนเทียบ

ผล: **96 key ทุกตัวมีแถวใน CLINE type-2 จริง (ไม่มี unresolved) - 92 ตัว resolve กลับไปเป็นเลขเดิม (ไม่มี
หลักฐานขัดแย้ง) - 4 ตัวไม่ resolve กลับไปเป็นเลขเดิม** (placement 64/67/68/91, Mob-Set 38/39/40/41 ->
CLINE-resolved 231/742/743/914) **ต่างจากแถว 63 ตรงที่ไม่มีหลักฐานสนับสนุน (ชื่อ/outfit) เหมือนกันเลย - มี
แต่หลักฐานขัดแย้ง** (MOBS 231 คือป้ายประกาศทหารเรือ ไม่ใช่คน; 742/743/914 คือคนละตัวกับ Reyna/Mo Yuzi/
Carle/Martin ทุกประการทั้งชื่อและ outfit) รายละเอียดเต็มอยู่ใน `RE-188` (`CLIENT_RE_QUEUE.md`)

## 3. ตัดสินใจ: ไม่แก้ table

ถ้าทำตามรูปแบบ RE-173 ตรง ๆ (regenerate จาก CLINE-resolved ID) จะแทนที่ NPC ที่มีชื่อ/สถานะ/outfit ถูก
ต้องอยู่แล้วสี่ตัวด้วยตัวตนที่ไม่เกี่ยวข้องกันเลย (ตัวหนึ่งเป็นวัตถุ ไม่ใช่คนด้วยซ้ำ) - นี่คือการเดาว่า "ตาราง
ไหนผิด" โดยไม่มีหลักฐานสนับสนุนเพียงพอ ตรงข้ามกับ RE-173 ที่มีชื่อ+outfit ตรงกันทุกตัวอักษรเป็นหลักฐาน
สนับสนุนแยกต่างหาก **ไม่แตะ `KNOWN_PLACEMENTS` แถว 64/67/68/91 เลย** - คงค่าที่วัดได้ (Mob-Set number
ตรง ๆ) เหมือนเดิม เปิด `RE-188` แทนให้ RE runner หาคำอธิบาย/หลักฐานเพิ่มก่อนตัดสินใจ

## 4. pf-adversary (บังคับก่อน commit)

รีวิวแบบ read-only เต็มรูปแบบ: re-derive crosswalk เองจากตารางดิบ (ไม่เชื่อตัวเลขของรอบนี้) - ตรงกันทุกจุด
(96 key, 92 match, 4 mismatch, บรรทัด CLINE ที่อ้างถูกต้อง, ตัวตน MOBS 231/742/743/914 ตรงตามที่อ้าง) -
**ยืนยันว่า crosswalk และการตัดสินใจไม่แก้ table ถูกต้อง** พบข้อบกพร่องการอ้างอิง 2 จุด (MEDIUM ทั้งคู่):
① ข้อความอ้างว่า "CHARTER-02 ห้าม" การเดาแบบนี้ - เปิด CHARTER-02 ฉบับจริงแล้วไม่มีประโยคนั้น (เป็นเรื่อง
deadline/version ไม่ใช่เรื่องหลักฐาน) - ข้อความนี้อยู่ใน `RE-173` ที่ merge แล้วด้วย (ไม่แก้ย้อนหลัง - ไม่ใช่
ของรอบนี้) แต่รอบนี้เกือบสืบทอดข้อผิดพลาดเดียวกันไปยังไฟล์ใหม่สองจุด - **แก้แล้วก่อน commit** เปลี่ยนเป็น
อ้างวินัยหลักฐานสองชั้นจริง (`G1`-`G8`/`G-OBS`/CHARTER-01) แทน ② อ้าง `RE-170` เป็นบทเรียนที่ "เคยเกิด" -
`RE-170` ยัง **OPEN** ไม่ใช่กรณีปิดแล้ว - **แก้แล้ว** เขียนใหม่เป็น "ใบพี่น้องที่กำลังตรวจอยู่คู่กัน" แทน
พบจุดเล็ก (LOW) เรื่องคำว่า "MOBS_TIP ไม่ตั้งชื่อ NPC" เกินจริงเล็กน้อย (จริง ๆ คือ `s_TITLE` ว่างเปล่า) -
**แก้แล้ว** เป็นคำอธิบายที่แม่นกว่า ตรวจซ้ำหลัง fix: cp874 ผ่าน, เทสที่เกี่ยวข้องผ่านเหมือนเดิม

## 5. เทสที่รัน

```
python3 -m pytest tests/test_scene2_prison_exile_tables.py \
  tests/test_world_m2_columbus_trigger_readiness.py -q
=> 34 passed, 7 subtests passed (ก่อนและหลังแก้ไม่ต่าง - docstring เท่านั้น)

python3 -m pytest tests/ -q  (ทั้งชุด, ก่อนแก้)
=> 6124 passed, 327 skipped, 13128 subtests passed, 0 failed (175s)

python3 -m pytest tests/ -q  (ทั้งชุด, หลังแก้)
=> 6124 passed, 327 skipped, 13128 subtests passed, 0 failed (169s)
```

จำนวนเทสไม่เปลี่ยน ไม่มีการเพิ่ม/ลบเทส (ไม่มีโค้ด logic เปลี่ยนเลย - เฉพาะ docstring) 0 failed ทั้งสองฝั่ง
cp874-encodability: ตรวจไฟล์ที่แก้ (`scene2_prison_exile_tables.py`) ด้วย `.encode('cp874')` ผ่าน

## 6. ไฟล์ที่แตะ

**pirate-force-server** (2 ไฟล์):
- `src/pirateforce_foundation/scene2_prison_exile_tables.py` (docstring เท่านั้น - เพิ่มย่อหน้า "RE-188
  AUDIT" หลัง "RE-173 CORRECTION" - ไม่แตะ `KNOWN_PLACEMENTS`/validator/logic ใด ๆ)
- `rounds/A_20260901_0442_re188x_....md` (สำเนา, optional)

**pf_bridge** (2 ไฟล์):
- `CLIENT_RE_QUEUE.md` (เปิด `RE-188`)
- `rounds/A_20260901_0442_re188x_prison_exile_placement_audit_re188_opened.md` (ไฟล์นี้เอง)
- `notes_to_chief/<timestamp>_LANE-A-STATUS-re188x.md` (ใหม่ - จดหมายสถานะ)

## 7. CORE-REQUEST

ไม่มี - ไม่แตะ `runtime.py`/`app.py`

## 8. เปิดใบให้สาย C (RE)

`RE-188` (`pf_bridge/CLIENT_RE_QUEUE.md`) - เปิดโดยสาย A บริโภคผลเอง (ไฟล์นี้เป็นของสาย A)

## 9. ASK-COO

ไม่มี - การตัดสินใจไม่แก้ table ใช้หลักการเดิมที่มีอยู่แล้ว (ห้ามเดาแล้วแก้โดยไม่มีหลักฐานสนับสนุน) ไม่ใช่
เรื่องใหม่ที่ต้องเคาะ

-- LANE-A (WORLD) round `re188x`
