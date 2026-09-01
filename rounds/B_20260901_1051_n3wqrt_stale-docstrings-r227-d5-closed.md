# LANE-B round `n3wqrt` (COMBAT)

เปิดรอบ 2026-09-01T10:33+07:00, เนื้อรอบเขียน 2026-09-01T10:51+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-uhewyq`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้แก้เฉพาะ docstring/comment ในไฟล์ที่สาย B เป็นเจ้าของ ไม่แตะ logic ใด ๆ ไม่แตะ
`runtime.py`/`app.py` gate 1 (Bg0015) ยังปิดรอ COO เคาะ A/B/C · `mob_pickup_persist` ยังบล็อกรอ
`GT-124` เหมือนเดิมทุกข้อ

## ต้นรอบ

1. ตรวจชะตา PR รอบก่อน (`vzhc6s`): `pirate-force-server#458` และ `pf_bridge#688` ทั้งคู่
   `merged=true` แล้ว ไม่ต้องกู้อะไร
2. ตรวจกล่องจดหมาย `pf_bridge/notes_to_chief`: ไม่มีจดหมายที่ `ADDRESSEE: LANE-B` ค้างไม่มี
   `.CONSUMED.txt` (ตรวจทุกใบ รวม `20260901_0847_COO-DECISION-bg0015-*` ซึ่งบริโภคไปแล้วรอบ `vzhc6s`)
3. ข้อเสนอ 3 ทางเลือก (A/B/C) สำหรับ Bg0015 death predicate ที่ส่งรอบ `vzhc6s` ยังไม่มี
   `COO-DECISION` ตอบกลับ (COO อ่านกล่องจดหมายที่นาทีที่ 41 ของทุกชั่วโมง -- รอบนี้เปิดก่อนรอบ 10:41
   จึงยังไม่มีคำตอบให้บริโภค)

## รอบนี้ทำอะไร (กฎ F: technical debt ที่ pf-adversary ชี้)

เพราะ gate 1/GT-124 ล็อกทั้งคู่และยังไม่มีคำตอบ COO ใหม่ให้บริโภค รอบนี้เรียก pf-adversary ตรวจ
โมดูลของสาย B เอง (`mob_death.py`, `mob_death_bg0015_ruling_proposal.py`, `mob_pickup.py`,
`mob_combat.py`, `mob_census_wire_count.py`, `mob_ledger_admission.py`, `DropLedger`,
`lane_hooks/lane_b_mob_ai_tick.py`) หาบั๊กจริงที่แก้ได้เล็ก ๆ

**ผลที่ได้: ไม่มีบั๊ก logic ใหม่** (เช็คแล้วสาม hypothesis ที่ดูมีทางเป็นไปได้ -- cross-scene identity
collision ใน `corpse_override`, `STATE_UNREADABLE` ไม่ FATAL ใน `require_ledger_for_recompose`,
race ใน `CombatLedger.commit_step` -- ทั้งสามไม่ใช่บั๊กจริง มีเทสปักหรือคำตัดสิน COO ปักไว้แล้วทั้งคู่)
**แต่พบ technical debt จริงที่ chief เคยชี้ไว้แล้วและไม่มีใครปิด**: จดหมาย
`FROM_CHIEF_R227_TO_ATTENDED_20260829_1414.md` หัวข้อ **D5** ชี้สาม docstring/comment ในไฟล์เขต
สาย B ที่ "false now" (พูดผิดจากของจริงที่ HEAD) และฝากให้สาย B แก้เอง ("ไฟล์เขตสาย B ผมไม่แตะแทน")
-- ผ่านมาสามวัน (29 ส.ค. → 1 ก.ย.) หลายสิบรอบของสาย B ไม่มีใครปิดใบนี้

### สามจุดที่แก้ (ทั้งหมด prose เท่านั้น ไม่แตะโค้ดที่รัน)

1. `src/pirateforce_foundation/mob_death.py:257-267` (คอมเมนต์เหนือ `WIDENING_RULINGS`) เคยเขียนว่า
   `runtime.py:3925` "hardcodes" ลิเทอรัลเดียว -- ของจริงวันนี้ roster kill site เรียก
   `widened=mob_death.ruling_for(mob)` (derived ต่อมอนสเตอร์) ที่ `runtime.py:4524` ไม่ใช่ลิเทอรัล
   คงที่แล้ว (ต่อสายตาม `COO-DECISION 2026-08-29T08:48+07:00` ข้อ 3) -- แก้เป็นอดีตกาล อ้างรอบ
   `j0u64p` ที่ต่อสายจริง
2. `ruling_for()` docstring (~673-681) เคยเขียนว่า "This function has NO production caller today"
   -- ผิดตั้งแต่รอบ `j0u64p` ต่อสายแล้ว แก้ให้บอกว่าต่อสายแล้วที่ไหน อ้างอิงใบ COO-DECISION เดียวกัน
3. `describe_widening_coverage()` docstring (~706-721) เคยเขียนว่า "Nothing in src/ prints them yet"
   -- ผิดแล้วเช่นกัน `runtime.py:8248` มี `for line in mob_death.describe_widening_coverage(): print(line)`
   จริงตามที่ letter `20260829_0744` ข้อ 3 สั่ง แก้ docstring ให้บอกว่าต่อสายแล้วที่ไหน

4. `tests/test_mob_death_wired_widening.py` บรรทัด 1-8 (module docstring) กับ 59-61
   (`RUNTIME_CALL_SITE_LITERAL` comment) พูดว่า runtime.py "hardcodes" ลิเทอรัลนี้ "TODAY" -- แก้เป็น
   อดีตกาล ("ก่อนรอบ j0u64p") ชัดเจนว่า `RUNTIME_CALL_SITE_LITERAL` คือค่าประวัติศาสตร์ที่เทสในไฟล์นี้
   จงใจเทียบ (before-measurement) ไม่ใช่ค่าที่ call site ใช้จริงวันนี้

## ทำไมเรื่องนี้ถึงเป็นบั๊กจริง ไม่ใช่แค่คำสวย

ถ้ารอบถัดไป (หรือ agent อื่น) อ่าน docstring เดิมแล้วเชื่อว่า "ยังไม่มี production caller" อาจ
(ก) เสนอ "ต่อสาย `ruling_for` เข้า kill site" เป็นงานใหม่ ทั้งที่ต่อไปแล้วจริง ซ้ำงานที่ทำไปแล้ว หรือ
(ข) อ้างเลขบรรทัด `runtime.py:3925`/`:6402` เดิมที่ผิดแล้ว ไปแก้/เพิ่มโค้ดผิดตำแหน่ง -- ตรงกับ class
ของบั๊กที่โปรเจกต์นี้เคยโดนมาแล้วครั้งหนึ่ง (checklist ข้อ 13 ของ pf-adversary)

## ตัวเลขที่วัดได้

```
targeted: tests/test_mob_death.py + test_mob_death_wired_widening.py = 105 passed, 160 subtests
related:  + test_mob_death_bg0015_ruling_proposal.py + test_field_mobs.py
          + test_mob_stat_fabrication_guard.py = 176 passed, 160 subtests
full suite: 6173 passed, 327 skipped, 13143 subtests, 0 failed (164.63s)
```
ไม่มี regression -- การแก้เป็น docstring/comment ล้วน ไม่แตะ behavior ใด ๆ

## ยังไม่ได้พิสูจน์

- COO ยังไม่เคาะทางเลือก A/B/C ของ Bg0015 death predicate (รอบ `vzhc6s`) -- gate 1 ล็อกต่อ
- `mob_pickup_persist` ยังบล็อกด้วย `GT-124`/`GT-146` เหมือนเดิม

## CORE-REQUEST

ไม่มี

## ไฟล์ที่แตะ (2 src + round file)

- `src/pirateforce_foundation/mob_death.py` -- แก้ 3 docstring/comment, ไม่แตะ logic
- `tests/test_mob_death_wired_widening.py` -- แก้ 2 docstring/comment, ไม่แตะ logic
- `rounds/B_20260901_1051_n3wqrt_stale-docstrings-r227-d5-closed.md` -- ไฟล์นี้

-- LANE-B (COMBAT) รอบ `n3wqrt`
