# LANE-B round `vzhc6s` (COMBAT)

เปิดรอบ 2026-09-01T09:39+07:00 (`TZ=Asia/Bangkok date`), ปิดรอบ 2026-09-01T09:44+07:00
(scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-vzhc6s` (repo นี้), `claude/wonderful-gauss-vzhc6s` (pf_bridge)
รอบก่อนของสาย B: `bdcmkf` (`pirate-force-server` merge เข้า main แล้ว ยืนยันผ่าน GitHub API ก่อนเริ่มรอบนี้
-- ไม่ต้อง cherry-pick กู้คืน)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้เป็นงานวิเคราะห์+ข้อมูลล้วน (module ใหม่ที่ derive ข้อมูลจากตารางที่มีอยู่แล้ว บวก
จดหมายข้อเสนอถึง COO) ไม่แตะ `field_mobs._SCENE_TABLE_MODULES` (gate 1 ยังปิดตามคำสั่ง
COO-DECISION 08:47 ข้อ (ค) ห้ามลงทะเบียนรอบนี้โดยเด็ดขาด) ไม่แตะ `mob_death.WIDENING_RULINGS`
เอง (ยังไม่มีจดหมายเจ้าของ/COO ที่ตั้งชื่อ ruling ให้ใส่) ไม่แตะ `runtime.py`/`app.py`

## งานที่ได้รับมอบหมายรอบนี้

`pf_bridge/notes_to_chief/20260901_0847_COO-DECISION-bg0015-death-ruling-process-plus-gate1-
ownership-and-sequencing.md` (ตอบใบ `20260901_0807_CHIEF-REPLY-*`) มอบให้สาย B:

1. **(ข)** หาระเบียบวิธีเดิมที่เคยใช้พิสูจน์ death predicate ของ Bg0001-Bg0014 แล้วประยุกต์กับ 7
   template ใหม่ของ Bg0015 (`343,345,348,350,353,355,924`) ส่งเป็น**ข้อเสนอ** (ไม่เกิน 2-3 ทาง)
   ให้ COO เคาะ -- ถ้าระเบียบวิธีเดิม generalize ไม่ได้เลย ให้บันทึกเป็นข้อเท็จจริง ไม่ใช่เดา
2. **(ค)** gate 1 (ลงทะเบียน Bg0015 เข้า `field_mobs._SCENE_TABLE_MODULES`) เป็นของสาย B แต่
   **ห้ามทำรอบนี้** จนกว่า (ข) จะมีคำตอบจาก COO

กำหนด: ส่งข้อเสนอภายในสองรอบของสาย B รอบนี้เป็นรอบแรก

## ระเบียบวิธีเดิม -- อ่านจากโค้ดจริงที่ใช้กับ bg0001/Bg0002 ไม่ใช่เดา

อ่าน `src/pirateforce_foundation/mob_death.py` (`WIDENING_RULINGS`, `WIDENING_RULING_SCENES`,
`ruling_for`, `rulings_covering`) และเทสที่ปักไว้ (`tests/test_mob_death.py`) ได้ระเบียบวิธีสี่ขั้น
ที่ใช้จริงกับทั้งสองฉากที่มี ruling แล้ว:

1. จดหมายเจ้าของ/COO ตั้งชื่อ template id เจาะจง หรือ "ทั้งเทเบิล" -- ถ้าตั้งชื่อ "ทั้งเทเบิล" ตัวเลขที่
   ใส่ใน `WIDENING_RULINGS` **re-derive จากตารางที่ mine ไว้จริงในเทส** ไม่เคย hand-copy
   (`test_the_bg0002_ruling_covers_exactly_the_real_bg0002_rosters_templates`)
2. การคัดกรองทางเทคนิค (แถวไหนถึงจะเป็น "candidate" ได้เลย) **ทำเสร็จแล้วโดยเครื่องมือ mine ก่อน
   จดหมายจะถูกขอด้วยซ้ำ**: ต้องมี rank>0 และ ai_combat!=0 (predicate ความเป็นศัตรู) บวก outfit ต้อง
   เป็นสตริงเดี่ยวไม่ใช่ variant list (";"-joined) -- แถวที่ตกกฎ outfit ไม่เคยเข้า `HOSTILE_PLACEMENTS`
   เลย ไปอยู่ `UNRESOLVED_PLACEMENTS`/`WITHDRAWN_UNDER_THIS_RULE` แทน คอมเมนต์ของ ruling Bg0002
   เขียนตรงๆ ว่า template 27/28/29/30/32/33 ถูกตัดออกด้วยเหตุผลนี้ ไม่ใช่มีใครอ่านแล้วตัดสินใจเอง
3. ชื่อ ruling ผูกกับฉากเดียวใน `WIDENING_RULING_SCENES` เพื่อกัน template id ที่ใช้ร่วมกันสองฉากไม่ให้
   ได้รับอนุญาตข้ามฉาก
4. ตัวที่ technical rule ข้อ 2 คัดออกจากเทเบิลไปแล้ว แต่ถูกวางในฉากด้วยกระบวนการอื่น (Mountain Deer/
   template 27 ของ Bg0002 ที่มาจาก diagnostic object ไม่ใช่ mined roster) จะได้ ruling แยกของตัวเอง

## ผลการวัดกับ 7 template ของ Bg0015

ขั้น 1-3 **generalize ได้สะอาด** กับ Bg0015 -- วัดจริง:

```
full_roster_template_ids()             = (343, 345, 348, 350, 353, 355, 924)
  == templates_without_a_death_ruling()  (ตรงกันเป๊ะ วัดด้วย cross-check ในเทส)
overlaps_with_registered_rulings()     = frozenset()   -- ไม่ชนกับ ruling ที่มีอยู่แล้วเลยสักตัว
  (bg0001 ruling คุม {916}, Bg0002 ruling คุม {31,34,35,103} -- คนละเซ็ตกับ 7 ตัวนี้ทั้งหมด)
```

**ขั้น 4 ไม่ generalize** กับกรณีเดียวที่มีคำถามจริงของ Bg0015: template 924 "Carlos"
(placement 87) -- Carlos **ไม่ได้** ตกกฎเทคนิคข้อ 2 เลย (`outfit = P_MALE_033_000_CARLOS` เป็น
สตริงเดี่ยว ไม่ใช่ variant list) เครื่องมือ mine จึงเลือกมันเข้า `HOSTILE_PLACEMENTS` ด้วย predicate
เดียวกับอีก 6 ตัวเป๊ะ สิ่งที่ทำให้ Carlos ต่างคือสิ่งที่เครื่องมือ mine มองไม่เห็นเลย: มี `MOBS_TIP`
title และบทพูด NPC -- ค้างเป็นคำถามเปิดจากสองจดหมายก่อนหน้านี้แล้ว
(`pf_bridge/notes_to_chief/20260829_0739_LANE-A-STATUS-lane-B-edit-confirmed-and-carlos-is-your-
call.md` ข้อ ④, และ `scene_identity_rule.py` ของสายนี้เอง จุดที่ 8: "อาจเป็นบอสจริงก็ได้ ยังไม่มีใครดู")
**การถอด Mountain Deer ออกจาก ruling ของ Bg0002 จึงไม่ใช่บรรทัดฐานสำหรับถอด Carlos ด้วยเหตุผล
เดียวกัน** -- มันเป็นบรรทัดฐานสำหรับถอดตัวที่ตกกฎเทคนิค ซึ่ง Carlos ไม่ได้ตก

ข้อเท็จจริงเชิงกลไกอย่างเดียวที่วัดได้ภายในเทเบิลของ Bg0015 เอง: 6 ใน 7 template มี outfit prefix
`M0` (โมเดลมอนสเตอร์) มีแค่ Carlos ตัวเดียวที่ prefix `P_` (โมเดลผู้เล่น) -- **ไม่ใช่กฎทั่วไป**
(โปรเจกต์นี้ ship ทหารเรือ `P_MALE_002_000_SP1` ที่ตีตายได้อยู่แล้วในที่อื่น) เป็นแค่ข้อเท็จจริงเฉพาะ
เทเบิลนี้ที่บังเอิญตรงกับตัวเดียวที่มีคำถามค้างพอดี

## สิ่งที่สร้าง (ไม่ลงทะเบียน ไม่แก้ `WIDENING_RULINGS`)

`src/pirateforce_foundation/mob_death_bg0015_ruling_proposal.py` (โมดูลใหม่, pure derivation,
ไม่ import อะไรที่จะแก้ `mob_death.WIDENING_RULINGS` ได้) เสนอ 3 ทางเลือกให้ COO เคาะ:

- **ทางเลือก A** (`option_a_full_roster`): ruling เดียวคุมทั้ง 7 template รวม Carlos -- ทำตาม
  ระเบียบวิธีเดิมแบบกลไกล้วน ไม่มีข้อยกเว้นใหม่ เหมือน bg0001/Bg0002 เป๊ะ
- **ทางเลือก B** (`option_b_roster_minus_carlos`): คุม 6 template (`343,345,348,350,353,355`)
  ก่อน แยก Carlos ไว้รอคำตอบเรื่องบทบาท (มอนหรือ NPC) -- รูปร่างเดียวกับที่ Mountain Deer เคยถูกแยก
  แต่**เหตุผลต่างกัน** ตามที่อธิบายข้างบน
- **ทางเลือก C** (`option_c_defer_the_whole_roster`): ยังไม่เคาะทั้ง 7 -- [สมมติของสาย B - รอ COO
  ยืนยัน] สายนี้เห็นว่าเป็นทางที่อ่อนที่สุดในสามทาง เพราะ 6 ใน 7 ตัวไม่มีคำถามค้างเลย การเลื่อนทั้งหมด
  จะดึง 6 ตัวที่ตอบได้แล้วไปรอด้วยตัวที่ยังตอบไม่ได้เฉยๆ

`tests/test_mob_death_bg0015_ruling_proposal.py` (17 เทสใหม่ ผ่านหมด) รวม acceptance criterion
ตามกฎ pf-adversary: stub ให้ `_template_outfits` ข้ามการเช็คความขัดแย้ง (`if False and disagreeing`)
แล้วเทส `test_disagreeing_outfits_for_one_template_raise` **แดง** ก่อนแก้กลับ ยืนยันว่าเทสจับของจริง
ไม่ใช่แค่ผ่านเฉยๆ (ทำจริง วัดจริง แล้วแก้กลับ)

## เทส

```
เฉพาะไฟล์ใหม่: tests/test_mob_death_bg0015_ruling_proposal.py
  -> 17 passed (0.08s)
ไฟล์ที่เกี่ยวข้อง (cross-check): tests/test_mob_combat_bg0015_gates.py tests/test_mob_death.py
  รวมกับไฟล์ใหม่ -> 119 passed (0.94s), ไม่มีของเดิมพัง
รอบแรกของสวีตเต็มจับได้ 2 แดง (ของเดิม ไม่ใช่ไฟล์ทดสอบใหม่): โมดูลใหม่ทำให้
  `tests/test_field_mobs.py::test_it_declares_itself_shippable_and_installs_nothing` และ
  `tests/test_mob_stat_fabrication_guard.py::test_every_lane_b_module_is_accounted_for_on_disk`
  แดง -- ทั้งสองเป็น "pinned inventory" เทสที่คาดหวังรายชื่อไฟล์ทั้งหมดใต้ src/ ที่ชื่อขึ้นต้นด้วย
  mob_/field_mob_ หรือมีคำว่า field_mobs ปรากฏในเนื้อไฟล์ (แม้แค่ในดอกสตริง) -- แก้โดยเพิ่มชื่อ
  โมดูลใหม่เข้ารายการทั้งสองไฟล์พร้อมคอมเมนต์อธิบาย (ไม่ใช่ลบ/บายพาสเทส) แล้วรันซ้ำ:
  0 failed
สวีตเต็มหลังแก้ (จบจริงแล้ว): 6173 passed, 327 skipped, 13141 subtests passed, 0 failed (144.33s)
  (รอบแรกที่แดง 2 ตัวข้างต้นนับรวม 17 เทสใหม่ไว้แล้วในฝั่ง passed: "2 failed, 6171 passed" ->
  แก้ 2 เทสที่แดงกลับเป็นผ่าน -> "6173 passed, 0 failed" เดลต้า +2 ตรงกับจำนวนเทสที่แก้พอดี ไม่มี
  regression อื่นซ่อนอยู่)
มิวเทชันพิสูจน์เทสจับของจริง: ปิด guard ใน _template_outfits -> เทส TemplateOutfitFailsClosedTests
  แดง (AssertionError: MobDeathBg0015ProposalError not raised) -- เปิด guard กลับ -> เขียวอีกครั้ง
git diff --check: silent
cp874/ascii: ทุกไฟล์ที่แตะ (โมดูลใหม่ + เทสใหม่ + สองไฟล์เทสที่แก้) encode ผ่านทั้ง ascii และ cp874
```

## Process note -- pf-adversary

ไม่มี pf-adversary agent แยกให้เรียกรอบนี้ (เหมือนรอบก่อนๆ) ทำเองตามที่ pf-adversary จะทำ: (ก) grep
หา `templates_without_a_death_ruling`/`ruling_for`/`WIDENING_RULINGS` ทั่ว repo ก่อนเขียนเพื่อไม่ให้
เข้าใจ methodology ผิด (ข) cross-check `full_roster_template_ids()` กับ
`mob_combat_bg0015_gates.templates_without_a_death_ruling()` แบบเรียกจริงสองทาง ไม่ใช่ copy ค่า
(ค) cross-check `player_body_template_ids()` กับการอ่านตาราง raw โดยตรง (ไม่ผ่าน FieldMob parser)
(ง) มิวเทตแล้ววัดว่าเทส fail-closed แดงจริงก่อนแก้กลับ (จ) ยืนยันว่าเรียกทุกฟังก์ชันในโมดูลใหม่แล้ว
`mob_death.WIDENING_RULINGS` ไม่เปลี่ยน (ฉ) ยืนยัน `git status --porcelain` ก่อน commit ว่ามีแค่ไฟล์
ใหม่สองไฟล์ ไม่แตะ `field_mobs.py`/`mob_death.py`/`runtime.py`/`app.py` เลย

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (pirate-force-server) รวม 5:
  src/pirateforce_foundation/mob_death_bg0015_ruling_proposal.py  [ใหม่]
  tests/test_mob_death_bg0015_ruling_proposal.py                  [ใหม่, 17 เทส]
  tests/test_field_mobs.py                        [แก้ pinned importer-list ให้รวมโมดูลใหม่]
  tests/test_mob_stat_fabrication_guard.py        [แก้ pinned LANE_B_MODULES ให้รวมโมดูลใหม่]
  rounds/B_20260901_0939_vzhc6s_bg0015-death-predicate-proposal.md [ไฟล์นี้]
full_roster_template_ids()          : (343, 345, 348, 350, 353, 355, 924)  -- 7 ตัว
player_body_template_ids()          : (924,)  -- 1 ตัว (Carlos)
overlaps_with_registered_rulings()  : frozenset()  -- ชนกับ ruling ที่มีอยู่แล้ว 0 ตัว
option_a (full)                     : 7 template
option_b (minus Carlos)             : 6 template
option_c (defer all)                : 0 template
เทสใหม่: 17 passed / เทสที่เกี่ยวข้องรวม: 119 passed, 0 failed
```

`current/pf_login_game_server_v141.py`: ไม่แตะ · canonical DB/capture corpus: ไม่แตะ ·
`runtime.py`/`app.py`: ไม่แตะ · `field_mobs._SCENE_TABLE_MODULES`: ไม่แตะ (gate 1 ยังปิดตามคำสั่ง) ·
`mob_death.WIDENING_RULINGS`: ไม่แตะ (ยืนยันด้วยเทสเองว่าเรียกทุกฟังก์ชันแล้วไม่เปลี่ยน) ·
`scenarios/world_*.json` (เขตสาย A): ไม่แตะ

## ยังไม่ได้พิสูจน์

- **COO ยังไม่ได้เคาะ** ว่าจะเลือกทางเลือก A/B/C หรือทางอื่น -- จดหมายรอบนี้ส่งข้อเสนอ ไม่ใช่คำตอบ
- ถ้า COO เลือก A หรือ B, **ข้อความ ruling ตัวจริง** (ชื่อจดหมาย, ถ้อยคำที่ต้อง quote เป๊ะใน
  `WIDENING_RULINGS`) ยังไม่มี -- ต้องมาจากจดหมายเจ้าของ/COO เอง ไม่ใช่สายนี้ตั้งชื่อเอง
- **gate 1** (ลงทะเบียนจริง) ยังล็อกเหมือนเดิม รออีกข้อจาก COO-DECISION 08:47 (ค) ที่บอกว่าต้องรอ (ข)
  ก่อน -- รอบนี้ตอบแค่ (ข) เป็นข้อเสนอ ยังไม่ใช่คำตอบสุดท้าย
- ประตูอื่นของ Bg0015 (AI table -- ปิดแล้วรอบ `n8kq4r`, roster registration, scene-14 composer) --
  ไม่เปลี่ยนจากที่บันทึกไว้ก่อนหน้า

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `vzhc6s`
