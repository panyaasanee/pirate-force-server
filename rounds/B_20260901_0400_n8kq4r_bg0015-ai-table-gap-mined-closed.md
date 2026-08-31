# LANE-B round `n8kq4r` (COMBAT)

เปิดรอบ 2026-09-01T03:37+07:00, ปิดรอบ 2026-09-01T04:00+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ)
Branch: `claude/determined-brown-apti62` (repo นี้), `claude/wonderful-gauss-apti62` (pf_bridge)
Draft PR ที่ถืออยู่: `pirate-force-server#437`, `pf_bridge#662`

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่แตะ `field_mobs._SCENE_TABLE_MODULES` (การลงทะเบียนฉาก 14 ยังปิดเหมือนเดิม) และ
ไม่แตะ `runtime.py`/`app.py` เลย -- แก้เฉพาะข้อมูลที่ mine ไว้ล่วงหน้า (`field_mob_ai_tables.py`) ซึ่งไม่มี
เส้นทางใดใน production ที่อ่านมันสำหรับฉาก 14 อยู่แล้ววันนี้ แต่รอบนี้**ปิดตัวบล็อกจริงตัวหนึ่งจากสี่ตัวที่
รอบก่อน (`6cm6ry`) วัดไว้**: ก่อนรอบนี้ การลงทะเบียนฉาก 14 (เมื่อใครก็ตามได้รับอนุญาตให้ทำ) จะทำให้
swing แรกของผู้เล่น**หลุดการเชื่อมต่อ** (`MobAiControlError: ai_row_missing`, ไม่ใช่แค่ตีไม่ตาย) --
วัดซ้ำรอบนี้แล้วว่าไม่เกิดอีก (ดูตัวเลขด้านล่าง)

## ทำไมรอบนี้ไม่ว่าง (ตามกฎ "ห้ามรอบสถานะเปล่าติดกันเกิน 1 รอบ")

รอบก่อน (`62o506`) ตรวจครบทุกเส้นทางแล้วสรุปว่าทุกอย่างล็อกด้วยการตัดสินใจที่ต้องรอ COO/เจ้าของ/สาย RE
-- รอบนั้นถูกต้องสำหรับ**การลงทะเบียนฉาก 14 เอง** (gate 1 การใส่ชื่อลง `_SCENE_TABLE_MODULES` ยังต้องรอ
คนมอบหมายเจ้าของประตูตามจดหมาย `20260901_0243`) แต่มี**อีกหนึ่งงานที่จริง ไม่ต้องรอใคร และไม่ใช่
`_SCENE_TABLE_MODULES`**: `mob_combat_bg0015_gates.py` (รอบ `6cm6ry`) วัดไว้ตรง ๆ ว่าสาเหตุที่ swing
แรกหลุดคือ `field_mob_ai_tables.py` (ตารางที่ mine ไว้) ไม่มีแถวที่ Bg0015 ต้องการ -- **ไม่ใช่เพราะข้อมูล
ไม่มีอยู่ในเกม แต่เพราะเครื่องมือ mine ยังไม่เคยถูกขอให้อ่าน Bg0015** (`tools/pf_mine_mob_ai_rows.py`'s
`load_roster_modules()` union มีแค่ `field_mob_tables` + `field_mob_tables_bg0002`) นี่คือ "reuse the
encoder that already ships -- feed it a wider input set" ตรงตามกฎการทำงานของสายนี้ ไม่ต้องเขียน selector
ใหม่ ไม่ต้องแตะ `_SCENE_TABLE_MODULES` ไม่ต้องรอ COO

## ตรวจก่อนแก้ (ยืนยันสดที่ HEAD ก่อนลงมือ)

```
$ PYTHONPATH=src python3 -c "from pirateforce_foundation import mob_combat_bg0015_gates as g; print(g.ai_rows_missing_for_scene14())"
{'mined_combat': (214, 332, 350, 352), 'wanted_combat': (102, 134, 273, 301, 323, 333, 472),
 'missing_combat': (102, 134, 273, 301, 323, 333, 472),
 'mined_wander': (11, 16, 21), 'wanted_wander': (11, 16, 22), 'missing_wander': (22,)}
g.open_register_refusal_for_scene14() = 'ai_row_missing'
```

ตรวจว่าแถวที่ขาดมีอยู่จริงในตารางที่ bridge commit ไว้ (`pf_bridge/gamedata/tables/`) ก่อนแก้ทุกครั้ง --
ไม่ใช่แค่เดา:

```
CONSTDATA_TH__AI_COMBAT.tsv: n_ID 102/134/273/301/323/333/472 -> True ทุกตัว
CONSTDATA_TH__AI_WANDER.tsv: n_ID 22 -> True
```

ตรวจ digest ควบคุมของเครื่องมือ (`CONTROL_AI_DIGESTS` ใน `tools/pf_mine_mob_ai_rows.py`) เทียบกับไฟล์จริง
บนสะพาน: `ai_wander` = `0b3f1eb8...`, `ai_combat` = `19cbc17f...` -- ตรงเป๊ะทั้งคู่ ⇒ ไม่ต้องใช้
`--accept-new-digests` (ตารางเกมไม่ได้เปลี่ยน แค่ขอบเขต mine กว้างขึ้น) และ MOBS digest ของ
`field_mob_tables_bg0015.py` (`3c0d33d6...`) ตรงกับที่ `field_mob_tables.py`/`field_mob_tables_bg0002.py`
บันทึกไว้ (control 2 ของเครื่องมือผ่านโดยไม่ต้องแก้อะไรเพิ่ม)

## สิ่งที่ทำ

1. **`tools/pf_mine_mob_ai_rows.py`**: เติม `field_mob_tables_bg0015` เข้า `load_roster_modules()` union
   (จากสองโมดูลเป็นสาม) พร้อมคอมเมนต์อธิบายเหตุผลและตัวเลขที่ขาด -- ไม่แตะ control ทั้งสี่ข้อของเครื่องมือ
2. รันเครื่องมือจริงกับ `pf_bridge/gamedata/` (ไม่แตะ canonical DB, ไม่แตะ capture corpus, อ่านอย่างเดียว):
   `python3 tools/pf_mine_mob_ai_rows.py --gamedata <bridge>/gamedata --out src/pirateforce_foundation/field_mob_ai_tables.py`
   ผล: `wrote ...: 4 wander rows, 11 combat rows, 33 links` (จากเดิม 3/4/21) -- **เพิ่มล้วน ไม่มีแถวเดิมถูก
   แก้ค่า** (ตรวจ diff แล้ว: 11/16/21 wander และ 214/332/350/352 combat ค่าเดิมทุกตัวอักษร)
3. **`src/pirateforce_foundation/field_mob_ai_tables.py`**: ผลลัพธ์ generated จากข้อ 2 (ไม่แก้มือ)
4. **`src/pirateforce_foundation/mob_combat_bg0015_gates.py`**: แก้ docstring หัวไฟล์ + บรรทัด MEASURED
   หนึ่งบรรทัด ให้ตรงความจริงใหม่ -- ข้อความเดิมที่ผิดแล้ว**ขีดฆ่าไว้ ไม่ลบ** ตามกฎ พร้อมหมายเหตุ
   "ROUND n8kq4r" อธิบายว่าปิดประตูไหน และย้ำว่าสามประตูที่เหลือ (roster registration, death rulings,
   scene-14 composer) ยังไม่ขยับเลย -- โค้ดฟังก์ชันจริงในไฟล์นี้**ไม่ได้แก้แม้บรรทัดเดียว** (แก้แค่ docstring)
5. **`tests/test_mob_ai_control.py`**: อัปเดตสองเทสที่ pin ขนาด/เนื้อหาตารางเดิม
   (`test_the_links_table_agrees_with_the_roster`, `test_the_two_wander_rows_are_the_ones_this_round_read`)
   ให้สะท้อนตารางที่กว้างขึ้น -- derive ผลที่คาดจาก `field_mob_tables_bg0015.SHIPPED_PLACEMENTS` โดยตรง
   (ไม่ hand-type ตัวเลข 12 แถว) ตามสไตล์เดิมของไฟล์เอง
6. **`tests/test_mob_combat_bg0015_gates.py`**: แก้สามเทสที่ pin บั๊กเดิมไว้เป็น "ความจริง" --
   `test_open_register_refuses_every_bg0015_row` → `test_open_register_no_longer_refuses_any_bg0015_row`,
   `test_the_missing_ai_rows_are_named_not_summarised` (พลิกไปยืนยันว่า `missing_*` ว่างเปล่าแล้ว),
   `test_registering_bg0015_unwinds_the_first_swing` → `test_registering_bg0015_clears_the_ai_table_gate_
   but_the_swing_is_still_inert` (วัดสดว่า**ไม่หลุดแล้ว** roster sync จริง ledger เต็ม 12 ตัวตรงกับ
   `splice_identities`, และแพ็กเก็ตเดิมที่ไฟล์นี้เคยใช้ทดสอบ (action code 0, "wield" capture) ยังไม่มีผล
   ตอบกลับเป็นการต่อสู้จริง -- **ไม่อ้างว่าพิสูจน์การตีสำเร็จ/มอนตาย เพราะไม่มีแพ็กเก็ต strike จริงในมือ
   และการประดิษฐ์ขึ้นเองขัดกฎบท "คุณไม่ตอบคำถาม คุณสร้างของ" ที่ต้องมีของจริงรองรับ**)

## เทส

```
รันเฉพาะไฟล์ที่แก้: tests/test_mob_ai_control.py tests/test_mob_combat_bg0015_gates.py
  -> 75 passed, 37 subtests passed
สวีตเต็มก่อนแก้ (HEAD เดิม, ยืนยันด้วยตัวเอง ก่อนรัน miner):
  -> 5 failed, 6032 passed, 383 skipped, 13115 subtests passed (135.63s ช่วง 62o506 baseline ตรงกัน,
     5 ที่แดงคือห้าเทสที่รอบนี้แก้)
สวีตเต็มหลังแก้ (สองรอบ ยืนยันซ้ำ):
  -> 6037 passed, 383 skipped, 13115 subtests passed, 0 failed (190-194s)
```

ตัวเลขต่างกัน +5 passed / 0 failed ตรงกับ 5 assertion ที่แก้ใน `test_mob_ai_control.py` (2 เทส) +
`test_mob_combat_bg0015_gates.py` (3 เทส) พอดี ไม่มี regression ที่อื่น

## ตัวเลขที่วัดได้

```
ไฟล์ที่แตะ (pirate-force-server) รวม 5 + ไฟล์ round นี้ 1 = 6:
  tools/pf_mine_mob_ai_rows.py                            [แก้ 1 จุด: union เพิ่มโมดูลที่ 3]
  src/pirateforce_foundation/field_mob_ai_tables.py       [generated ใหม่, ห้ามแก้มือ]
  src/pirateforce_foundation/mob_combat_bg0015_gates.py   [แก้ docstring เท่านั้น ไม่แก้โค้ด]
  tests/test_mob_ai_control.py                            [แก้ 2 เทส]
  tests/test_mob_combat_bg0015_gates.py                   [แก้ 3 เทส]
  rounds/B_20260901_0400_n8kq4r_bg0015-ai-table-gap-mined-closed.md [ไฟล์นี้]

field_mob_ai_tables mine -- ก่อน/หลัง:
  wander rows : 3 -> 4   (เพิ่ม n_ID 22)
  combat rows : 4 -> 11  (เพิ่ม n_ID 102/134/273/301/323/333/472)
  links       : 21 -> 33 (เพิ่ม 12 -- ตรงกับ 12 hostile placement ของ Bg0015 พอดี)
mob_combat_bg0015_gates.ai_rows_missing_for_scene14() -- ก่อน/หลัง:
  missing_combat : (102,134,273,301,323,333,472) -> ()
  missing_wander : (22,) -> ()
mob_combat_bg0015_gates.open_register_refusal_for_scene14() -- ก่อน/หลัง: 'ai_row_missing' -> None
สวีตเต็ม: 6032 passed/5 failed -> 6037 passed/0 failed (383 skipped, 13115 subtests คงที่ทั้งคู่)
```

`current/pf_login_game_server_v141.py`: ไม่แตะ · canonical DB/capture corpus: ไม่แตะ (อ่าน
`pf_bridge/gamedata/tables/*.tsv` อย่างเดียว, ไฟล์เหล่านั้น commit ไว้แล้วในทรี ไม่ใช่ DB) ·
`runtime.py`/`app.py`: ไม่แตะ · `field_mobs._SCENE_TABLE_MODULES`: ไม่แตะ (gate 1 ยังปิด) ·
`scenarios/world_*.json` (เขตสาย A): ไม่แตะ

## ยังไม่ได้พิสูจน์

- **การลงทะเบียนฉาก 14 จริง (gate 1)** ยังไม่ทำ -- ยังรอคนมอบหมายเจ้าของประตูตาม
  `notes_to_chief/20260901_0243_...`; รอบนี้ปิดแค่ตัวบล็อกที่ gate 2 (ตาราง AI) จะสร้างถ้า gate 1 เปิด
  ไม่ได้เปิด gate 1 เอง
- **Death ruling ของ 7 template** (`templates_without_a_death_ruling()` ยังคืน
  `(343, 345, 348, 350, 353, 355, 924)` เหมือนเดิม -- เจ้าของเท่านั้นที่ออกได้ ไม่ขยับรอบนี้
- **Recompose composer ของฉาก 14** (`recompose_status()['has_composer']` ยังเป็น `False` เหมือนเดิม)
- **การตีจริง/มอนตายจริงในฉาก 14** -- รอบนี้ไม่มีแพ็กเก็ต strike จริงให้ทดสอบ (มีแค่แพ็กเก็ต "wield"
  ที่ไฟล์เทสเดิมใช้อยู่แล้ว) วัดได้แค่ว่า sync ไม่หลุดแล้ว ไม่ได้วัดว่าตีแล้วเลือดลดจริงในฉาก 14
- ทุกอย่างที่รอบ `62o506`/`6cm6ry` ยกไว้ (color mapping RE-067/RE-155, pickup opcode RE-125/GT-124,
  drop label re-emission) -- ไม่มีข้อไหนขยับรอบนี้เช่นกัน

## CORE-REQUEST

ไม่มี (รอบนี้ไม่แตะ `runtime.py`/`app.py`)

## เปิดใบให้สาย C

ไม่มี

-- LANE-B (COMBAT) รอบ `n8kq4r`
