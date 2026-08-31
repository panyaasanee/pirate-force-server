# LANE-A round `re173w`

2026-09-01T03:2x+07:00 - 2026-09-01T03:4x+07:00 (+07:00 via `TZ=Asia/Bangkok date`).

**ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน:** ผู้เล่นที่เข้าฉาก Prison Exile (Bg0002) จะเห็น NPC "Columbus" (Marine
Transport Station) ที่ท่าเรือมีค่าที่ถูกต้องแล้ว - ก่อนหน้านี้ NPC ตัวนี้ถูกสร้างด้วยสถิติผิดฉาก (เลเวล 35,
เดินช้า 150) ที่จริง ๆ เป็นของ MOBS แถวอื่น ตอนนี้ใช้สถิติของ MOBS 360 ตัวจริงตามที่ CLINE crosswalk ของฉาก
ชี้ไว้ (เลเวล 10-20, ความเร็วเดิน 400) - nameplate/HP bar ที่ลูกค้าคำนวณจากค่าพวกนี้จะเปลี่ยนตาม และคอนโซล
ฝั่งเซิร์ฟเวอร์ตอนนี้รายงานครบ 8/8 เกาะที่ Columbus ยืนอยู่จริง (จากเดิม 7/8 เมื่อวาน)

## 0. บริบทก่อนเริ่ม (ตรวจ mailbox ก่อนเชื่อ prompt เก่า)

`grep "ADDRESSEE: LANE-A"` ทั้ง `notes_to_chief/*.md`: พบทุกใบตั้งแต่ `20260831_1428` ถูก consume แล้ว
(ย้ายเข้า `consumed/` หรือมี `.CONSUMED.txt`) ยกเว้นสองใบล่าสุดในตอนเริ่มรอบ: `20260901_0146_COO-DECISION-
door-reader-precedence-*` (มี `.CONSUMED.txt` ค้างจากรอบ `trig7s` ที่ self-close ตามคำสั่งใบเองแล้ว - ไม่มี
อะไรให้ทำต่อ) และ `20260901_0202_LANE-A-STATUS-*` (สถานะของรอบ `yfbqmg` เอง ไม่ใช่ใบถึงสาย A) - ไม่มีใบ
ค้างจริง เช็ค `CLIENT_RE_QUEUE.md`/`GAME_TEST_QUEUE.md` พบ `20260901_0303_RE-173-RESULT-*` **ยังไม่ถูก
consume** (ไม่มีทั้ง `.CONSUMED.txt` และไม่ได้ย้ายเข้า `consumed/`) - นี่คือ RE ที่รอบ `trig7s` เปิดไว้เอง
และตรงกับกฎ "ระหว่างรอ RE ของ Columbus ให้ทำ M2 ขั้นถัดไป" - เพราะ RE ตอบกลับมาแล้ว จึงบริโภคผลแทนที่จะไป
สำรวจ M2 หัวข้อใหม่ (charter ข้อ 2: "คุณไม่ตอบคำถาม คุณสร้างของ" - RE ตอบให้แล้ว งานที่เหลือคือสร้าง/แก้ตาม
ผลนั้น)

ไม่มีใบ `CLAIM` ของสายอื่นทับหัวข้อนี้ (`scene2_prison_exile_tables.py` เป็นไฟล์ที่สาย A ดูแลเองอยู่แล้ว)

## 1. RE-173 ตอบว่าอะไร (สรุปจากใบผล)

`Bg0002` placement 63 → `MOBSET_36` → scene 2 `n_CLINE_TYPE=2` → CLINE key `(2,36)`
(`CONSTDATA_TH__CLINE.tsv:350`) → `n_LEADER_BK1=360` → `MOBS.n_ID=360` ไม่มี ambiguity (leader BK2/3 และ
crew ทุกช่องเป็น 0) `scene2_prison_exile_tables.py`'s แถว 63 ที่ใช้ n_ID 36 ตรง ๆ **ผิด**
`world_m2_sea_destination.COLUMBUS_ROUTES`'s home scene 2 (360) **ถูกอยู่แล้ว**

BUILD_IMPACT ของใบบอกตรง ๆ ว่าต้องแก้อะไร: `n_id` 36→360, `level`/`level_max` 35/35→10/20, `speed_walk`
150→400, `max_hp` 7980→421 - outfit/name/title/rank/AI/drops **ไม่เปลี่ยน** (RE-173 เทียบ MOBS 36 กับ 360
แล้วยืนยันคอลัมน์เหล่านี้เหมือนกันทุกประการ) ใบเดียวกันยังตั้ง validator range `1..41` ไว้เป็นจุดที่ต้อง
"widen/ออกแบบใหม่ให้รับ 360" อย่างชัดเจน

## 2. งานที่สร้าง

### 2.1 `scene2_prison_exile_tables.py` (แก้)

- แถว 63 ใน `KNOWN_PLACEMENTS` regenerate ตาม BUILD_IMPACT ทั้ง 4 ฟิลด์ (n_id, level, level_max,
  speed_walk, max_hp) คอมเมนต์ inline อ้าง RE-173 ตรงแถว
- `COLUMBUS_N_ID` เปลี่ยนจาก `36` เป็น `360` (ใช้กรองแถวใน `anchor_report()`)
- **ไม่ได้ขยับ upper bound ของ `_require_int(n_id, ...)` จาก 41 เป็นเลขที่ใหญ่กว่า** เพราะจะทำให้ n_id 230
  (Mirage Reel, การ fabrication guard ของ RE-123 ที่มีเทสปักไว้แล้ว) หลุดผ่านไปด้วย - แทนที่ด้วยฟังก์ชัน
  `_require_n_id()` ใหม่ที่รับ `[1,41]` **หรือ** สมาชิกของ `CLINE_RESOLVED_N_IDS = frozenset({360})` ที่ตั้ง
  ชื่อไว้ชัดว่าเป็น "MOBS id ที่ผ่าน CLINE crosswalk แล้วเท่านั้น ไม่ใช่การขยาย range เฉย ๆ" - ถ้าอนาคตมี
  placement อื่นต้อง crosswalk แบบเดียวกัน ให้เพิ่มใน allowlist นี้ทีละตัวพร้อมอ้างอิงของตัวเอง ไม่ใช่ขยับ
  เพดานลอย ๆ
- อัปเดตดอกสตริงหัวไฟล์ (ย่อหน้า "RE-173 CORRECTION") และย่อหน้า anchor ที่พูดถึง "Columbus (36)" ให้ชัดว่า
  36 คือ Mob-Set number (ยังไม่เปลี่ยน) ส่วน MOBS n_ID จริงคือ 360 (เปลี่ยนแล้ว) - ไม่ปนกัน

### 2.2 `world_m2_columbus_trigger_readiness.py` (แก้)

- ดอกสตริง "WHAT THIS ROUND MEASURED" แถว home 2 เปลี่ยนจาก `NOT PLACED` เป็น `PLACED`
- ย่อหน้า "A GENUINE DISCREPANCY" เปลี่ยนชื่อเป็นอดีตกาล พร้อมย่อหน้าใหม่อ้าง RE-173's ผลจริง (เก็บ
  ประวัติเดิมไว้ ไม่ลบ - เพื่อให้คนอ่านย้อนหลังเห็นว่าทำไมเคยเป็น NOT_PLACED)
- **ไม่แตะ logic** - `_bg0002_mobs_n_ids()` อ่านจาก `load_known_placements()` เหมือนเดิมทุกตัวอักษร ผล
  เปลี่ยนเพราะข้อมูลต้นทางเปลี่ยน ไม่ใช่เพราะเปลี่ยนวิธีวัด

### 2.3 เทสที่ปรับตาม ground truth ใหม่

`tests/test_world_m2_columbus_trigger_readiness.py`:
- `test_every_non_port_royal_route_matches_columbus_routes_exactly`: เอา special-case ของ home scene 2
  ออก (ตอนนี้ตรงกับทุกเกาะ ไม่ใช่ข้อยกเว้นแล้ว)
- `test_home_scene_2_columbus_is_present_under_the_OTHER_id` → เปลี่ยนชื่อ/สลับ assertion (360 อยู่, 36
  ไม่อยู่ - ตรงข้ามของเดิม)
- `test_widens_across_all_eight_columbus_routes_rows`, `test_without_legacy_only_home_scene_1_goes_
  unmeasured`, `test_the_line_reports_the_true_counts`,
  `test_a_columbus_crossing_prints_the_trigger_readiness_line_last`: ตัวเลข `placed=7/not_placed=1` →
  `placed=8/not_placed=0`, `2:NOT_PLACED` → `2:PLACED`

`tests/test_scene2_prison_exile_tables.py` **ไม่ต้องแก้เลย** - ไม่มีเทสไหนอ้างค่าดิบของแถว 63 โดยตรง (เช็ค
ด้วย grep ก่อนแก้) เทส Mirage Reel (n_id 230) ที่ pin ข้อความ error `"[1,41]"` ยังผ่านเพราะ `_require_n_id`
โยน error message เดิมทุกตัวอักษรสำหรับกรณีถูกปฏิเสธ

## 3. เทสที่รัน

```
python3 -m pytest tests/test_scene2_prison_exile_tables.py \
  tests/test_world_m2_columbus_trigger_readiness.py -q
=> 34 passed, 7 subtests passed

python3 -m pytest tests/ -q  (ทั้งชุด, ก่อนแก้ - git stash)
=> 6097 passed, 323 skipped, 13117 subtests passed, 0 failed (186s)

python3 -m pytest tests/ -q  (ทั้งชุด, หลังแก้)
=> 6097 passed, 323 skipped, 13117 subtests passed, 0 failed (194s)
```

จำนวนเทสทั้งหมดไม่เปลี่ยน (แก้ assertion ของเทสเดิม ไม่ได้เพิ่ม/ลบเทส) ผลลัพธ์เปลี่ยนเพราะข้อมูลเปลี่ยน คนละ
เรื่องกับจำนวนที่รัน - 0 failed ทั้งสองฝั่ง

cp874-encodability: ตรวจทั้ง 3 ไฟล์ที่แก้ (`scene2_prison_exile_tables.py`,
`world_m2_columbus_trigger_readiness.py`, `test_world_m2_columbus_trigger_readiness.py`) ด้วย
`.encode('cp874')` ผ่านทั้งหมด

## 4. ไฟล์ที่แตะ

**pirate-force-server** (4 ไฟล์):
- `src/pirateforce_foundation/scene2_prison_exile_tables.py` (แก้)
- `src/pirateforce_foundation/world_m2_columbus_trigger_readiness.py` (แก้)
- `tests/test_world_m2_columbus_trigger_readiness.py` (แก้)
- `rounds/A_20260901_0340_re173w_prison-exile-columbus-mobs-360-fix.md` (สำเนา, optional)

**pf_bridge** (4 ไฟล์):
- `rounds/A_20260901_0340_re173w_prison-exile-columbus-mobs-360-fix.md` (ใหม่, ไฟล์นี้)
- `notes_to_chief/20260901_0303_RE-173-RESULT-CLINE2-SET36-IS-MOBS360.md.CONSUMED.txt` (ใหม่)
- `CLIENT_RE_QUEUE.md` (แก้: ปิด RE-173 พร้อมผล)
- `notes_to_chief/<timestamp>_LANE-A-STATUS-re173w.md` (ใหม่ - จดหมายสถานะ)

## 5. งานที่ไม่ได้ทำรอบนี้ (นอกขอบเขต RE-173 โดยเจตนา)

RE-173's Nonclaims ระบุชัดว่าไม่ได้ audit identity ของ placement อื่นทั้งหมดใน Bg0002 - อีก 96 known
placements ยังใช้กติกาเดิม (Mob-Set number = MOBS n_ID ตรง ๆ ไม่ผ่าน CLINE) ซึ่งอาจผิดแบบเดียวกับ placement
63 ในบางแถว - ไม่ได้ตรวจ/แก้รอบนี้เพราะ RE-173 ไม่ได้ยืนยันหรือปฏิเสธ ไม่มีหลักฐานให้ทำต่อโดยไม่เดา - เปิด
เป็นบันทึกไว้ในดอกสตริง ไม่ใช่ใบ RE ใหม่ (ยังไม่มี candidate แถวไหนที่มีหลักฐานขัดแย้งเหมือน RE-173 มี)

## 6. CORE-REQUEST

ไม่มีรอบนี้ - แก้ข้อมูลในไฟล์ที่สาย A ดูแลเอง ไม่แตะ `runtime.py`/`app.py`
