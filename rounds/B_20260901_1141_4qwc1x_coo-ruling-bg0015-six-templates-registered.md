# LANE-B round `4qwc1x` (COMBAT)

เปิดรอบ 2026-09-01T11:33+07:00, เนื้อรอบเขียน 2026-09-01T11:41+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-4qwc1x`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ลงทะเบียน ruling ใหม่ใน `mob_death.WIDENING_RULINGS` เท่านั้น -- ไม่แตะ
`field_mobs._SCENE_TABLE_MODULES` (gate 1 ที่จริง ๆ เปิดสวิตช์ให้ Bg0015 เดินเกม) ยังปิดเหมือนเดิม
ไม่มี roster ให้ยิง ไม่มีอะไรบนจอเปลี่ยน

## ต้นรอบ

1. ตรวจชะตา PR รอบก่อน (`n3wqrt`): `pirate-force-server#463` และ `pf_bridge#693` ทั้งคู่
   `merged=true` แล้ว (ยืนยันด้วย `pull_request_read get`) ไม่ต้องกู้อะไร
2. อ่าน `CHIEF_CONTINUATION.md` หัวข้อ "ลำดับงานปัจจุบัน" (บล็อกใหม่จาก R285/KA1A-FINDING
   20260901_1110): ไมล์สโตน M1-M6/CHARTER-02 พักตามคำสั่งเจ้าของ 2026-09-01T02:15 -- prompt
   ของสายนี้ยังพูดถึง BUILD-004/005/006 เดิม เพราะเจ้าของเท่านั้นแก้ prompt ได้ ตามกฎ KA1A-FINDING
   จึงอ่านไฟล์นี้แทนพึ่ง prompt -- **P-1 (ของดรอปอยู่บนพื้นนานพอให้เก็บทัน) เป็นของสาย B** และ
   `GT-146`/ใบตีมอนทั้งหมดห้ามเข้าคิว attended จนกว่า P-1+P-2 จะเสร็จ
3. ตรวจกล่องจดหมาย `pf_bridge/notes_to_chief`: พบจดหมายค้าง `ADDRESSEE: LANE-B` ที่ยังไม่มี
   `.CONSUMED.txt` หนึ่งใบ -- `20260901_1046_COO-DECISION-bg0015-death-ruling-option-b-six-
   templates-carlos-held-out.md` (ตอบข้อเสนอ 3 ทางเลือกจากรอบ `vzhc6s`)

## รอบนี้ทำอะไร

บริโภคจดหมาย `1046` แล้วทำตามคำสั่ง: เลือก**ทางเลือก B** -- ลงทะเบียน 6 ใน 7 template ผู้สมัคร
ของ Bg0015 (343, 345, 348, 350, 353, 355) เข้า `mob_death.WIDENING_RULINGS` ด้วยชื่อที่ต้อง quote
เป๊ะ `COO-RULING-20260901-1046` ผูกฉาก `"Bg0015"` ใน `WIDENING_RULING_SCENES` (ลิเทอรัลตรง ไม่
import `field_mob_tables_bg0015` -- ดูหัวข้อถัดไปว่าทำไม) Carlos (template 924) **ไม่เข้า ruling
นี้** ตามคำสั่ง (ยังเป็นคำถามเปิดรอหลักฐานเพิ่มเรื่องบทบาทในเนื้อเรื่อง)

ชุด 6 template ไม่ได้พิมพ์มือ -- ดึงจาก
`mob_death_bg0015_ruling_proposal.option_b_roster_minus_carlos()` ตรงเป๊ะ (โมดูลที่รอบ `vzhc6s`
สร้างไว้เพื่อการนี้โดยเฉพาะ) แล้วยืนยันด้วยเทสใหม่ว่าค่าในดิกชันนารีจริงเท่ากับค่าที่ฟังก์ชันนั้น
คำนวณสด ไม่ใช่สองลิเทอรัลที่บังเอิญตรงกัน

**gate 1 ไม่ได้แตะ** (`field_mobs._SCENE_TABLE_MODULES` ยังไม่มี Bg0015) -- จดหมาย COO เขียนไว้ตรง ๆ
ว่าสองเรื่องนี้แยกกัน การลงทะเบียน ruling ไม่ใช่การเปิด gate

### จับได้เองระหว่างรอบ: import guard ของ field_mob_tables_bg0015

ร่างแรกของรอบนี้ `import` โมดูลตารางดิบของ Bg0015 ตรง ๆ เข้า `mob_death.py` เพื่อเอาค่า `.SCENE`
-- `tests/test_field_mob_tables_bg0015.py::test_only_the_approved_hostile_composer_imports_
the_bg0015_module` (COO-DECISION 2026-08-31T16:48+07:00) จับได้ทันทีตอนรันสวีตเต็ม: โมดูลนั้นมี
approved importer เดียวคือ `field_mob_hostile_bg0015.py` การ์ดนี้กวาดทั้ง AST import และ literal
string ทุกที่ในไฟล์ ไม่ใช่แค่ statement `import` แก้โดยเขียนลิเทอรัล `"Bg0015"` ตรง ๆ แทน (คอมเมนต์
อธิบายเหตุผลโดยไม่พิมพ์ชื่อโมดูลต้องห้ามซ้ำ เพราะการ์ดกวาด literal ด้วย) แล้วเทสใหม่ยืนยันค่านี้ตรงกับ
`.scene` จริงของแถว roster ที่อ่านผ่านทางที่ approved (`field_mob_hostile_bg0015.
scene14_hostile_roster()`)

### เอกสารเก่าที่พูดผิดหลังการแก้นี้ -- แก้ตามกฎเดียวกับที่ปิด R227 D5 เมื่อรอบก่อน

พบว่าการแก้นี้ทำให้ข้อความเก่าสามจุดกลาย "false now" ทันที (class บั๊กเดียวกับที่ `n3wqrt` เพิ่งปิด
เมื่อวาน) แก้ทั้งหมดด้วย `~~...~~ IS STRUCK` (ไม่ลบประวัติ):

1. `mob_death_bg0015_ruling_proposal.py` module docstring หัวข้อ "WHAT IS STILL CLOSED AFTER
   THIS MODULE EXISTS" เคยว่า "`templates_without_a_death_ruling()` still refuses all seven"
2. `overlaps_with_registered_rulings()` docstring เคยว่า "Empty at HEAD"
3. `mob_combat_bg0015_gates.py` module docstring bullet เคยว่า "no Bg0015 template has a death
   ruling"

### เทสที่ pin ค่าเก่าไว้ -- แก้ให้ตรงของจริง ไม่ใช่ลบทิ้ง

- `tests/test_mob_death_wired_widening.py::test_every_registered_letter_can_be_ordered_and_
  names_its_own_clock` -- pin แบบ exact-set ของชื่อ ruling ทุกตัว เพิ่มแถวใหม่
  `"COO-RULING-20260901-1046": "202609011046"` (เทสนี้จะ fail ทันทีถ้าใครลงทะเบียน ruling โดยไม่
  ปักที่นี่ -- แผนกันของโปรเจกต์ทำงานถูกต้อง จับได้จริงตอนรันครั้งแรก)
- `tests/test_mob_combat_bg0015_gates.py::test_no_roster_and_no_death_ruling_today` เปลี่ยนชื่อเป็น
  `test_no_roster_and_carlos_alone_lacks_a_death_ruling_today` -- ค่าเก่า pin ทั้งเจ็ด templates
  ปฏิเสธ ตอนนี้เหลือแค่ 924
- `tests/test_mob_death_bg0015_ruling_proposal.py` สามเทส pin "empty"/"seven refused" เดิม แก้ตาม
  ของจริง + เพิ่มคลาสใหม่ `RegisteredRulingMatchesOptionBTests` (5 เทส) พิสูจน์ตรง ๆ ว่า
  ruling ที่ลงทะเบียนจริงเท่ากับคำตอบของ option B ทุกประตู (ชื่อ, ชุด template, ฉาก, ruling_for()
  ต่อแถวจริงทั้งหกทีละแถว, Carlos ไม่ใช่สมาชิก, gate 1 ไม่ขยับ)

## pf-adversary review (บังคับก่อน merge)

รีวิวผ่าน pf-adversary subagent จริง (isolated worktree, mutation-free) -- **ไม่พบบั๊ก** ตรวจครบ
ทุกข้อที่สั่ง: (1) cross-scene leakage -- ผูกฉาก "Bg0015" แยกจาก bg0001/Bg0002 จริง intersection
ว่างเปล่า, (2) 6 template ตรงกับ `option_b_roster_minus_carlos()` เป๊ะด้วยการรันจริง ไม่ใช่เชื่อคำ
อ้างของรอบนี้, (3) `ruling_registered_at("COO-RULING-20260901-1046")` รันจริงได้ `"202609011046"`
ถูกต้อง, (4) docstring ทั้งสามจุดตรงกับของจริงที่รันสด, (5) ไม่มีเทสที่ถูก "ลดความเข้ม" -- พบว่าเทส
mutation-guard เดิม (`test_is_measured_against_the_real_dict_not_a_copy`) ใช้ template 345 ทดสอบ
ซึ่งหลังรอบนี้กลายเป็น id ที่ ruling จริงคุมอยู่แล้ว จะทำให้เทสนั้น pass ปลอม ๆ ได้แม้ฟังก์ชันจะไม่ได้
อ่านดิกชันนารีสดจริง -- แก้แล้วให้ใช้ 924 (Carlos) แทน ซึ่งเป็น id เดียวที่ไม่มี ruling ใดคุมในทุกกรณี,
(6) import-guard dodge เป็นการแก้จริง ไม่ใช่ย้ายปัญหา (grep ยืนยันไม่มี "field_mob_tables_bg0015"
หลงเหลือในสามไฟล์ src ที่แตะ, และ guard สแกนเฉพาะ `src/` ไม่ใช่ `tests/` จึงไม่กระทบ import เดิมที่
ถูกต้องอยู่แล้วของไฟล์เทส), (7) gate 1 (`field_mobs._SCENE_TABLE_MODULES`) ยืนยันว่ายังไม่มี Bg0015
จริง

ข้อสังเกตออกแบบ (ไม่ใช่บั๊กของรอบนี้): กติกา tie-break ของ `ruling_for()` (ชุดแคบกว่าก่อน แล้วค่อย
ตามเวลาลงทะเบียน) ไม่มีอะไรใน CI ป้องกันไม่ให้ ruling ในอนาคตของ Carlos ทับซ้อนกับหกตัวนี้ -- เป็น
ข้อสังเกตสำหรับรอบถัดไปที่แตะ Carlos ไม่ใช่ช่องโหว่ของรอบนี้เอง

## ตัวเลขที่วัดได้

```
targeted: test_mob_death.py + test_mob_death_wired_widening.py
          + test_mob_death_bg0015_ruling_proposal.py + test_mob_combat_bg0015_gates.py
          = 145 passed, 177 subtests
full suite: 6160 passed, 383 skipped, 13152 subtests, 0 failed (188.84s)
```
ไม่มี regression -- เดลต้าเทสจากการเพิ่มคลาสใหม่ 5 เทส + แก้เทสเดิม 6 จุด ไม่มีอะไรพัง

## ยังไม่ได้พิสูจน์

- gate 1 (`field_mobs._SCENE_TABLE_MODULES`) ยังปิด -- Bg0015 ยังไม่มี roster จริงในเกม
- Carlos (924) ยังไม่มี ruling -- เปิดค้างรอหลักฐานเพิ่ม ไม่ใช่ของเร่งตามจดหมาย
- P-1 (ของดรอปอยู่บนพื้นนานพอให้เก็บทัน) ยังรอ attended test `GT-188` (BLOCKED on PR merge ตาม
  ที่บันทึกไว้แล้ว, ไม่ใช่งานของรอบนี้)

## CORE-REQUEST

ไม่มี (ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

## ไฟล์ที่แตะ (6 src+tests + round file)

- `src/pirateforce_foundation/mob_death.py` -- +import, +1 `WIDENING_RULINGS` entry,
  +1 `WIDENING_RULING_SCENES` entry
- `src/pirateforce_foundation/mob_death_bg0015_ruling_proposal.py` -- 2 docstring corrections
  (`~~...~~ IS STRUCK`), ไม่แตะ logic
- `src/pirateforce_foundation/mob_combat_bg0015_gates.py` -- 1 docstring correction, ไม่แตะ logic
- `tests/test_mob_death_wired_widening.py` -- +1 pinned inventory row
- `tests/test_mob_combat_bg0015_gates.py` -- 1 เทสแก้ชื่อ+เนื้อหา
- `tests/test_mob_death_bg0015_ruling_proposal.py` -- 3 เทสแก้, +1 คลาสใหม่ (5 เทส)
- `rounds/B_20260901_1141_4qwc1x_coo-ruling-bg0015-six-templates-registered.md` -- ไฟล์นี้

-- LANE-B (COMBAT) รอบ `4qwc1x`
