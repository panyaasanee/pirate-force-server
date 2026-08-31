# LANE-B round `6cm6ry` (COMBAT)

เปิดรอบ 2026-09-01T01:06+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ) Branch:
`claude/determined-brown-6cm6ry` (repo นี้), `claude/wonderful-gauss-6cm6ry`
(pf_bridge)

## ADDENDUM 6cm6ry-3 (2026-09-01T02:45+07:00) -- pf-adversary รอบสอง: ของจริงคือ "คอนเนกชันหลุด"

**อ่านหัวข้อนี้ก่อนทุกหัวข้อ รวมทั้งก่อน ADDENDUM 6cm6ry-2 ด้านล่าง.** รีวิวรอบสองพบว่า 14 จุดใน
รอบแก้แรกยังผิด และรูปแบบของความผิดคือ *การแก้สร้างความผิดชนิดเดียวกับที่กำลังแก้* รอบนี้จึงไม่เพิ่ม
การวิเคราะห์ แต่**ตัดพื้นที่ของข้ออ้างลง** ให้เหลือเฉพาะสิ่งที่วัดเองที่ HEAD

**ของจริงที่ควรเป็นพาดหัวตั้งแต่แรก**: ลงทะเบียน Bg0015 แล้ว **สวิงแรกในฉาก 14 raise ออกจาก
`dispatch`** = คอนเนกชันผู้เล่นหลุด ไม่ใช่ "มอนตายไม่ได้" วัด end-to-end เองแล้ว (ลงทะเบียนในโปรเซส
+ login -> StartGame -> ฉาก 14 -> ActionVital):

```
runtime.py:4156  _dispatch_mob_combat: roster = self._sync_combat_scene_state()
runtime.py:4103  _sync_combat_scene_state: mob_ai_control.open_register(...)
mob_ai_control.py:403
MobAiControlError: ai_row_missing: placement 22 points at AI_COMBAT 301,
which is not in the mined rows: regenerate field_mob_ai_tables
```

ไม่มีใครจับ: `_sync_combat_scene_state` ไม่มี `try` เลย และบรรทัด 4156 อยู่เหนือ `except` ทุกตัวใน
`_dispatch_mob_combat` (ตัวแรก 4214) ทั้ง 12 แถวชี้ `AI_COMBAT` ที่ตารางขุดไม่มี (มี
`214,332,350,352` ต้องการ `102,134,273,301,323,333,472`) และ placement 87 ต้องการ `AI_WANDER 22`
(มี `11,16,21`) **แก้ได้ทางเดียวคือ regenerate `field_mob_ai_tables` = miner run กับ gamedata บน
บริดจ์ ไม่ใช่การแก้โค้ดจากทรีนี้** -- ไม่มีเอกสารไหนของรอบนี้เคยระบุเงื่อนไขนี้มาก่อน

**สิ่งที่ถอนเพิ่มในรอบแก้นี้** (ทุกข้อวัดเอง ไม่ใช่รับมาเชื่อ):

| # | ข้ออ้างในรอบแก้ที่ 2 | ที่วัดได้จริง |
|---|---|---|
| ประตู 2 | "guard ห้าม `field_mobs.py` โดยระบุชื่อ ทั้ง AST และ literal sweep / สาย B ทำเองไม่ได้เลย / เป็นคำตัดสิน COO" | **ผิด** -- โค้ดของ guard เป็น allowlist พาธเดียว ชื่อ `field_mobs.py` อยู่ใน**ดอกสตริง**เท่านั้น (บรรทัด 184/196/203) กันแบบ "ไม่อยู่ในลิสต์" เหมือนไฟล์อื่นทั้งหมด -- ถ้าส่ง COO ไปขยับ allowlist นี้คือส่งไปขยับของที่ไม่เคยกั้น |
| ประตู 4 | "composer ฉาก 14 สาย B สร้างเองได้เลย" | **ผิด** -- `ACKNOWLEDGED_WITHOUT_COMPOSER[14]` เขียนเองว่า compose "ในรอบเดียวกับที่ roster row แรกลง" = อยู่หลังการลงทะเบียน และ `recompose_gate_open()` เดิมอ่านแค่ `composer_scene_ids()` ไม่เคยอ่าน acknowledgement เลย |
| `closed_gates()` | รายงานประตู 2 | รายงานผ่าน state ที่ประตู 2 ไม่ได้ควบคุม (ต่อท้ายทุกครั้งที่ roster ปิด) -- **ตัดทิ้งทั้งฟังก์ชันและ `GATE_OWNERS`** |
| ราคา | "35 failed / 6056 passed" | **6056 มาจากทรีก่อนเปลี่ยนชื่อไฟล์เทส** วัดที่ HEAD ได้ **35 failed / 6062 passed** = 11 FAILED + 24 subtest failure |
| splice | "เปลี่ยนแค่หน้าตา 12 ตัว" (อ้างจากจดหมายสาย A) | จดหมายนั้นเขียนเองว่ายังไม่เคยมีเทสขับ -- **รันเองแล้ว**: 81 identity คงครบ, 12 entry เปลี่ยน, frame 14879 -> 15035 มีเทสปักแล้ว |
| เทส | "เทสกลายพันธุ์กันการปลอม placement" | เทสนั้น**ไม่เคยเรียกฟังก์ชันจริง** -- stub ให้คืน `()` แล้วยังเขียว 12/13 แก้ให้เรียกจริงและพิสูจน์ด้วยการ stub แล้ว (แดง 1 ใบตามต้องการ) และบันทึกตรง ๆ ว่าการเลื่อน `+1` **จับไม่ได้** (สาย A ส่ง 81 จาก 91 placement) สิ่งที่จับได้จริงคือ pin เลข 12 ตัวที่พิมพ์มือ |
| "independent" | "สาย A วัด 12 เลขนี้อย่างอิสระจากสายนี้" | จดหมายสาย A เขียนตรงข้าม ("12 placement index **ที่สาย B ระบุ**") -- สิ่งที่อิสระจริงคือ **โค้ดสองเส้นทาง** (`world_bg0015_identity._PLACEMENT_ROWS` กับ `HOSTILE_PLACEMENTS`) ที่ไม่ import กัน แก้ถ้อยคำแล้ว |
| เทส wired | "ยืนยันสำหรับ 12 identity ของ Bg0015" | จำนวนเต็มอะไรก็ได้ให้ผลเหมือนกัน -- สิ่งที่มันปักจริงคือ "ฉาก 14 resolve เป็นโฟลเดอร์ Bg0015 บน roster ว่าง" เขียนใหม่ให้ตรง และเพิ่ม assertion ที่ยิง `0xDEADBEEF/0x1/0xFFFF` ให้เห็นคาตา |
| pin ที่หาย | รอบแก้ที่ 2 อ้างว่าไฟล์ใหม่ยืนยันความต่างของ scene tag | การเปลี่ยนชื่อไฟล์ทำ pin นั้นหายไปเฉย ๆ -- **กู้กลับมาแล้ว** เป็นเทสของตัวเอง |

**การตัดสินใจเชิงกระบวนการ**: เลิกส่ง "แผนที่ความเป็นเจ้าของ" ให้ chief -- เดาผิดสองรอบติดใน
เอกสารที่มีไว้กันคนอื่นทำของพัง ต่อไปนี้ส่งข้อเท็จจริงที่วัดได้ + ระบุว่าอะไรเป็น inference + ส่ง
**คำถาม** ให้ chief/COO ตอบ (ดูหัวข้อ "รายการนี้ยังไม่ครบ" ท้ายไฟล์)

## ADDENDUM 6cm6ry-2 (2026-09-01T02:10+07:00) -- pf-adversary หักล้างข้อสรุปหลักของรอบนี้ แก้แล้ว

**อ่านหัวข้อนี้ก่อนเชื่ออะไรด้านล่าง.** pf-adversary รีวิว PR ก่อน undraft และวัดหักล้างข้ออ้างหลัก
หลายข้อของร่างแรก ทุกข้อถูกวัดซ้ำด้วยตัวเองรอบนี้ (ไม่ใช่รับมาเชื่อ) และแก้แล้วตามกฎ
"ห้ามลบประวัติเดิม ให้ขีดฆ่าแทน" -- ข้อความเดิมที่ผิดยังอยู่ในไฟล์นี้แบบขีดฆ่า พร้อมของจริงข้าง ๆ

| # | ข้ออ้างเดิม (ผิด) | สิ่งที่วัดได้จริง |
|---|---|---|
| D1 | ตีมอน Bg0015 แล้วถูกปฏิเสธด้วย `REFUSE_TARGET_NOT_IN_LEDGER` | **ผิด** -- `attack_from_observed_action` วน **roster** ก่อนและคืน `None` ถ้าไม่เจอ ดังนั้น event จริงคือ `mob_combat_target_not_a_field_mob_no_reply` (วัดสดด้วย harness จริง 12/12 ครั้ง, `target_not_in_ledger` = 0 ครั้ง) ของที่ขาดคือ **roster** ไม่ใช่ ledger |
| D2 | "ไม่มีข้อไหนผิดทางเทคนิค" + สาย B ลงทะเบียนเองใน `src/` ได้ | **ผิด** -- ลงทะเบียนจริงแล้ววัด: **35 failed / 6056 passed** (10 เทสที่ไม่ใช่ของรอบนี้ ใน 5 ไฟล์) มอนจะตายไม่ได้ (ไม่มี ruling) และสวิงแรกจะส่งเฟรมลบ actor อีก 80 ตัว และ guard ห้าม `field_mobs.py` import ตารางนี้ **โดยระบุชื่อ** -- ทำใน `src/` ลำพังไม่ได้เลย |
| D3 | bg0001/Bg0002 ชนกันอยู่แล้ว จึงเป็น "ความเสี่ยงชนิดเดิม" | **ผิด** -- `cross_scene_identity_collisions()` คืน `()` ที่ HEAD (รอบ 8ftmbx ถอนฝั่ง bg0001 ออกหมด) การลงทะเบียน Bg0015 จะสร้างการชนข้ามฉาก **ครั้งแรก** ของทรีนี้ |
| D4 | "ข้อเท็จจริงที่วัดได้ #1" (ledger จะตรงกับ splice) | **ไม่ได้วัดอะไรเลย** -- เทียบ roster กับตัวเอง (เลื่อน placement 11/12 ตัวยังเขียว) แก้เป็นเทียบกับ census จริงของสาย A (81 actor) + เทสกลายพันธุ์ |
| D5 | ลูปยืนยัน 12 identity ถูกปฏิเสธ | ไม่มีความหมาย (`0xDEADBEEF` ก็ถูกปฏิเสธเหมือนกัน) ตัดทิ้ง แทนด้วยเทส end-to-end จริง |
| D6 | "ยังไม่มีใครบันทึกการชนนี้" | **ผิด** -- `test_all_three_known_tables_together_find_one_pairwise_collision` (รอบ ua236k) ปักไว้แล้ว placement 87 / template 34 vs 924 / 1 จุด |
| D7 | CORE-REQUEST จะทำให้เกิด "12 ตัวแดงที่ตีไม่ได้" | **เล็กกว่าความจริง** -- ฉาก 14 เปิดอยู่แล้วและ census ของสาย A ส่ง **81 actor** เข้าไปทุกวันนี้ (`lane_hooks.scene_census_composer(14)`, `production_allowed=True`) ทั้ง 81 ตัวตีไม่ได้อยู่แล้ว splice แค่เปลี่ยน "หน้าตา" ของ 12 ตัว ไม่ใช่ "ตีได้" -- และจุด census ของฉาก 14 คือ `runtime.py:7626` ไม่ใช่ `7501` (7501 อยู่ในกิ่งของฉาก 2) |
| D8 | ราคา "182 assertion ใน 6 ไฟล์" | เป็นตัวเลขที่รับช่วงมาจากรอบ jqxe6v ไม่ใช่ HEAD -- วัดเองได้ **35 failed, 10 เทส, 5 ไฟล์** |
| D9 | "ไฟล์ที่แตะ 5" | จริงคือ **6** (ลืมนับไฟล์ CLAIM) |
| D10 | "cp874 sweep ผ่าน" | ผ่านเฉพาะสอง `.py` ใหม่ ไฟล์รอบนี้เองมี `①` (U+2460) ซึ่ง cp874 ไม่มี -- นอกขอบเขตกฎ (`src/ tools/ current/`) แต่คำกล่าวอ้างเดิมกว้างเกินจริง |

**สิ่งที่เปลี่ยนในโค้ดตามการแก้นี้**: เปลี่ยนชื่อโมดูล
`mob_combat_bg0015_gap.py` -> **`mob_combat_bg0015_gates.py`** (ชื่อเดิมอ้างสิ่งที่ผิด) เขียนใหม่
ทั้งไฟล์ให้รายงาน **สี่ประตู** พร้อมเจ้าของแต่ละบาน และเขียนเทสใหม่ทั้งไฟล์ (13 ใบ) รวมเทสที่ขับ
dispatch จริงในฉาก 14

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่ได้ต่อสายอะไรใหม่ให้ผู้เล่นเห็น ~~เป็นรอบที่วัดและพิสูจน์ช่องโหว่จริงที่ยังไม่มี
ใครเคยพูดถึงตรง ๆ ก่อนหน้านี้~~ (D6: การชนที่ placement 87 มีเทสปักไว้แล้วตั้งแต่รอบ ua236k --
ของใหม่จริงของรอบนี้คือ **ผลที่ตามมาถ้าลงทะเบียน** และ **จำนวนประตูที่ยังปิดอยู่**) โมดูลใหม่
(~~`mob_combat_bg0015_gap.py`~~ -> `mob_combat_bg0015_gates.py`) ไม่มี caller ใน `runtime.py`
เลย ไม่ compose เฟรม ไม่แตะ `field_mobs._SCENE_TABLE_MODULES`

## บริบท -- สิ่งที่ตรวจสอบก่อนเริ่ม

อ่าน `rounds/B_20260831_2101_jqxe6v.md`, `rounds/B_20260831_2156_iok5z1_*.md`,
`rounds/B_20260831_2341_4dsios.md` และไฟล์จริงใน `src/pirateforce_foundation/`
ครบก่อนเริ่ม ไม่เชื่อสรุปเก่า:

- BUILD-004/005 สำหรับ bg0001/Bg0002 (ฉากที่ live วันนี้): ยัง wired จริง ไม่ drift
- Bg0015 (ฉาก 14) ชั้น 1 (import gate) ปลดล็อกแล้ว, ชั้น 2/3 (การ splice ภาพหลอน + ชนกับสาย A)
  ออกแบบเสร็จและยืนยันร่วมกันแล้วทั้งสองสาย (`field_mob_hostile_bg0015.py`, รอบ jqxe6v) --
  CORE-REQUEST ส่งไปหา chief แล้วจริง
  (`pf_bridge/notes_to_chief/20260831_2151_LANE-A-TO-CHIEF-scene14-hostile-splice-core-request-
  both-halves-confirmed-built.md`) ยังไม่มี caller ใน `runtime.py` (grep ยืนยันสด: 0 hit)
- `lane_b_mob_ai_tick.py` (mob_ai_scheduler ต่อสาย): built, CORE-REQUEST ส่งแล้ว (รอบ iok5z1)
  ยังไม่มี caller ใน `runtime.py` (grep ยืนยันสด: 0 hit)
- Door B (มอนตีกลับ/ขยับบนจอ) และ KA1B defect ① (fixed attacker profile): ทั้งคู่รอ COO/เจ้าของ
  ตัดสินอย่างชัดเจนตามจดหมายรอบ 256rvs -- ไม่ relitigate รอบนี้ ไม่แตะ
- BUILD-006 (M5): ยังบล็อก `GT-146` (attended เท่านั้น) ตาม COO-DECISION 20260831_1246 --
  ไม่ relitigate รอบนี้
- Mailbox: ไม่มี `ADDRESSEE: LANE-B` ใหม่ที่ยังไม่ consumed (ตรวจซ้ำสดตอนเริ่มและก่อนปิดรอบ)
- Heartbeat: `2026-09-01T00:16:02+07:00` เทียบกับตอนเริ่มรอบ (`01:06+07:00`) ต่างกัน 50 นาที
  ไม่เกิน 60 นาทีตามกฎ

เมื่อทั้งสองงานที่เตรียมพร้อมที่สุด (bg0015 splice, mob_ai_tick) ต่างก็รอ chief แก้ `runtime.py`
อยู่แล้ว (นอกเขตของสายนี้) และ Door B/defect① รอ COO อยู่แล้ว รอบนี้จึงไล่คำถามที่ยังไม่มีใครถาม:
"ถ้า chief ต่อสาย CORE-REQUEST ของ bg0015 สำเร็จเป๊ะตามที่ขอ ผู้เล่นจะตีมอนสัตว์ 12 ตัวนั้นได้จริง
ไหม" -- คำตอบที่วัดได้คือ **ยัง** และนี่คือของใหม่ที่ยังไม่มีใครบันทึกไว้ตรง ๆ มาก่อน

## สิ่งที่พบ -- ช่องโหว่ครึ่งที่สองของ BUILD-004/005 ฉาก 14

CORE-REQUEST ที่ส่งไปแล้ว (รอบ jqxe6v/78zayw) พูดถึงแค่ครึ่ง "ภาพ" (census ที่ผู้เล่นเห็นบนจอ):
เรียก `world_population_bg0015.build_bg0015_population` แล้ว splice hostile bytes ของ 12 ตัวเข้าไป
ผ่าน `mob_scene_recompose.splice_identity_override` ไม่มีที่ไหนพูดถึงครึ่ง "ตี" เลย

ไล่โค้ดจริงพบว่า `_dispatch_mob_combat`'s call site ที่ต่อสายแล้ว (`damage_step`/`death_step`)
ดึง ledger ผ่าน `self._sync_combat_scene_state()` (`runtime.py:4027`) ซึ่ง **scene-generic เต็มรูป
แบบอยู่แล้ว**: เปิด `field_mobs.load_roster(folder)` เมื่อ `folder in field_mobs.live_scenes()`
เท่านั้น ไม่งั้นเปิด roster ว่าง `field_mobs._SCENE_TABLE_MODULES` ~~(รอบ jqxe6v วัดไว้แล้วว่ามี
182 assertion ปักอยู่ทั่วหกไฟล์เทสที่หมายถึง "สองฉากที่ ship แล้ว" -- **ตั้งใจเลื่อนการลงทะเบียนฉาก
ที่สามไปให้ chief ประสานงานเอง ไม่ทำเป็นผลข้างเคียง**)~~ **[ถอนตัวเลข: "182 assertion ใน 6 ไฟล์"
รับช่วงมาจากรอบ jqxe6v ไม่ได้วัดที่ HEAD -- วัดเองที่ HEAD ได้ 35 failed / 6062 passed = 11 บรรทัด
FAILED + 24 subtest failure, เป็นเทสที่ไม่ใช่ของรอบนี้ 10 ใบ ใน 5 ไฟล์]** ยังมีแค่ bg0001/Bg0002
ที่ HEAD ของรอบนี้

~~ผลคือ: **แม้ chief ต่อสาย CORE-REQUEST ของ census/splice สำเร็จ 100% ตามที่ขอ ผู้เล่นก็ยังคลิกตี 12
ตัวที่ดูเป็นสีแดง/hostile นั้นไม่ได้เลย** -- ทุกจังหวะตีจะถูกปฏิเสธด้วย
`mob_combat.REFUSE_TARGET_NOT_IN_LEDGER` เพราะ ledger ของฉาก 14 เปิดว่างเปล่าเสมอ~~

**[แก้ตาม D1 + D7, วัดเองซ้ำแล้ว]** สองอย่างผิดในย่อหน้าที่ขีดฆ่าไว้ข้างบน:

1. **event ที่ออกจริงไม่ใช่ `REFUSE_TARGET_NOT_IN_LEDGER`**
   `mob_combat.attack_from_observed_action` (`mob_combat.py:1667-1680`) วน **roster** ก่อน แล้วคืน
   `None` ถ้า target ไม่อยู่ในนั้น -- `REFUSE_TARGET_NOT_IN_LEDGER` ต้องการสภาพ "อยู่ใน roster แต่
   ไม่อยู่ใน ledger" ซึ่ง `_sync_combat_scene_state` สร้างไม่ได้เลย เพราะมันเติมทั้งสองอย่างจาก
   `load_roster(folder)` ครั้งเดียวกัน สิ่งที่ผู้เล่นได้จริงคือ event
   `mob_combat_target_not_a_field_mob_no_reply` (`runtime.py:4226`) -- วัดสดรอบนี้ด้วย harness จริง
   (login -> StartGame -> ฉาก 14 -> ActionVital 12 ครั้ง): ออก 12/12 ครั้ง, `target_not_in_ledger`
   0 ครั้ง และ `tests/test_scene_scoped_combat_wiring.py::test_an_addressed_tableless_scene_
   answers_over_an_empty_roster` ปักผลแบบเดียวกันนี้ไว้ก่อนหน้าแล้วสำหรับฉากประเภทนี้
   **ของที่ขาดคือ roster ไม่ใช่ ledger** (ledger เป็นผลพลอยได้ของ roster ที่จุดเรียกนั้น)
2. **ขนาดของปัญหาถูกพูดน้อยกว่าความจริง** ฉาก 14 ไม่ได้กำลังรอ splice ถึงจะมีตัวละคร --
   `lane_hooks.scene_census_composer(14)` ของสาย A live และ `production_allowed=True` **อยู่แล้ว
   วันนี้** ส่ง census **81 actor** (`0x2002`-`0x205a`, วัดสดรอบนี้) เข้าไปในไคลเอนต์จริง แปลว่า
   **ทั้ง 81 ตัวตีไม่ได้อยู่แล้วตอนนี้** และ splice จะเปลี่ยนแค่ "หน้าตา" ของ 12 ตัวในนั้น ไม่ได้
   เปลี่ยน "ตีได้" เลยสักตัว (จุด census ของฉาก 14 คือ `runtime.py:7626` ไม่ใช่ `7501` ที่จดหมาย
   CORE-REQUEST อ้าง -- `7501` อยู่ในกิ่งเฉพาะฉาก 2)

## ของจริงที่สร้างรอบนี้ -- ~~`mob_combat_bg0015_gap.py`~~ `mob_combat_bg0015_gates.py`

`src/pirateforce_foundation/mob_combat_bg0015_gates.py` (ใหม่, เปลี่ยนชื่อจาก `..._gap.py` ใน
รอบเดียวกันหลัง D1: ชื่อเดิมอ้างว่า "ledger" คือของที่ขาด ซึ่งวัดแล้วผิด): โมดูลวัดผลล้วน ๆ แบบ
เดียวกับ `mob_combat_membership.py` (ไม่มี caller, ไม่ compose เฟรม) **ไม่แตะ**
`field_mobs._SCENE_TABLE_MODULES`/`live_scenes()` เลย

**สี่ประตู ไม่ใช่ "ครึ่งที่สอง"** (D2 -- วัดเองโดยลงทะเบียนจริงบนทรีทดลองแล้วรันสวีตเต็ม:
**35 failed / 6056 passed**, 10 เทสที่ไม่ใช่ของรอบนี้ ใน 5 ไฟล์ แล้ว `git checkout` คืน):

| ประตู | สถานะวันนี้ (วัดได้) | ใครขยับได้ |
|---|---|---|
| 1. ลงทะเบียน roster (`_SCENE_TABLE_MODULES`) | ปิด (`live_scenes() = ('Bg0002','bg0001')`) | ไฟล์ของสาย B แต่ติดประตู 2 |
| 2. ขยาย guard ผู้ import ที่ได้รับอนุมัติ | ปิด -- guard ห้าม `field_mobs.py` **โดยระบุชื่อ** ทั้งทาง AST และ literal sweep (ปิดทาง importlib ด้วย) | COO/เจ้าของ (guard เข้ารหัสคำตัดสินของ COO) |
| 3. owner ruling ให้ 7 template ของ Bg0015 | ปิด -- `mob_death.ruling_for` ปฏิเสธทั้ง 12 แถวด้วย `target_outside_the_sanctioned_scope` (343/345/348/350/353/355/924) → มอนจะโดนตีแต่ **ตายไม่ได้** | เจ้าของเท่านั้น (`WIDENING_RULINGS` รับเฉพาะจดหมายเจ้าของ) |
| 4. composer ของ `mob_scene_recompose` สำหรับฉาก 14 | ปิด (`composer_scene_ids() = (1, 2)`) → สวิงแรกจะส่งเฟรมหนึ่ง-entry ที่ RE-092 พิสูจน์แล้วว่าลบ actor อีก 80 ตัวออกจากจอ | **สาย B สร้างเองได้เลย** |

~~สิ่งที่โมดูลนี้ให้ ... `recompose_gate_open()`, `closed_gates()` + `GATE_OWNERS` ...~~
**[แก้รอบที่ 3]** `GATE_OWNERS` และ `closed_gates()` **ตัดออกทั้งคู่** (`closed_gates()` รายงาน
ประตู 2 ผ่าน state ที่ประตู 2 ไม่ได้ควบคุมเลย; `GATE_OWNERS` คือแผนที่เจ้าของที่เดาผิดสองรอบ) และ
`recompose_gate_open()` เปลี่ยนเป็น `recompose_status()` ที่อ่าน **ทั้งสองครึ่ง**
(`composer_scene_ids()` + `ACKNOWLEDGED_WITHOUT_COMPOSER` + `scene_is_accounted_for`)
สิ่งที่โมดูลให้ตอนนี้ ทุกตัวคือหนึ่งการวัด: `ai_rows_missing_for_scene14()`,
`open_register_refusal_for_scene14()` (พาดหัว), `roster_gate_open()`,
`scene14_roster_size_today()`, `templates_without_a_death_ruling()`, `recompose_status()`,
`splice_identities(legacy)`, `splice_identities_missing_from(...)`,
`owner_refused_placements_for_scene14()`, `live_cross_scene_collisions_today()`,
`bg0002_bg0015_identity_collisions()`, `ENUMERATION_PROCEDURE` (ขั้นตอนที่ใช้หา + ขีดจำกัดของมัน)

~~1. `bg0015_registration_would_line_up_with_the_visual_splice()` -- ถ้าลงทะเบียน Bg0015 จริง ledger
   ที่เปิดได้จะมี identity ตรงกับ 12 ตัวที่ splice ไว้เป๊ะ~~
**[แก้ตาม D4]** ฟังก์ชันนั้นเทียบ `scene14_hostile_roster()` **กับตัวมันเอง** -- ไม่ได้วัดอะไรเลย
(pf-adversary พิสูจน์: เลื่อน placement 11 จาก 12 ตัวไป +100 แล้วเทสยังเขียวทั้ง 7 ใบ พร้อม
identity ปลอม 11 ตัว) **ตัดทิ้งแล้ว** แทนด้วย `splice_identities_missing_from(...)` ที่ฝั่งอิสระ
ต้องมาจากภายนอก + เทสที่ใช้ census จริงของสาย A (81 actor) และเทสกลายพันธุ์ที่จงใจปลอม placement
แล้วต้องแดง นอกจากนี้บันทึกจุดที่ **จะ** แตกในอนาคตด้วย: `load_roster` กรอง
`OWNER_REFUSED_PLACEMENTS` (ตัด 8 แถวของ Bg0002 อยู่แล้ว) แต่ `scene14_hostile_roster()` ไม่กรอง --
สองฝั่งตรงกันวันนี้เพราะ Bg0015 **ยังไม่มี** owner refusal เท่านั้น ไม่ใช่เพราะโค้ดรับประกัน

~~2. ... **ไม่ใช่ความเสี่ยงชนิดใหม่**: bg0001/Bg0002 ชนกันแบบนี้อยู่แล้ววันนี้ที่ `0x2068`/`0x206a`~~
**[แก้ตาม D3 + D6]** วัดเองแล้ว: `field_mobs.cross_scene_identity_collisions()` คืน `()` ที่ HEAD
(รอบ 8ftmbx ถอนแถวฝั่ง bg0001 ออกหมด, ความว่างนี้ถูกปักด้วย
`tests/test_field_mobs.py::test_default_set_is_the_two_live_known_scenes_only` และย้ำอีกครั้งใน
`tests/test_mob_death.py`) ประโยค `0x2068`/`0x206a` ที่ร่างแรกอ้างเป็นปัจจุบันนั้นเป็น
**ประวัติศาสตร์** ในดอกสตริงของ `open_ledger_for_scene_id` (`load_roster` มีคำแก้แบบขีดฆ่าอยู่แล้ว)
ข้อสรุปที่ถูกต้องจึงตรงข้ามกับร่างแรก: การลงทะเบียน Bg0015 จะสร้างการชนข้ามฉาก **ครั้งแรก** ของทรีนี้
สวนกับ property ที่สองเทสยืนยันว่าว่างอยู่ ส่วนตัวการชนเองไม่ใช่ของใหม่ --
`tests/test_field_mobs.py::test_all_three_known_tables_together_find_one_pairwise_collision`
(รอบ ua236k) ปัก placement 87 / template 34 vs 924 / 1 จุด ไว้แล้ว (D6)

~~ยังพิสูจน์ TODAY's STATE ด้วยโค้ดจริง ... `balance_of()` ปฏิเสธทั้ง 12 identity ด้วย
`REFUSE_TARGET_NOT_IN_LEDGER` จริง~~
**[แก้ตาม D5]** ลูปนั้นไม่ได้พิสูจน์อะไรเกี่ยวกับ Bg0015 เลย -- `open_ledger_for_scene_id(14)
.balance_of(x)` โยน `target_not_in_ledger` ให้ `0xDEADBEEF`, `0x1`, `0xFFFF` เหมือนกันหมด มันมีค่า
เท่ากับ `assertEqual(ledger.identities(), ())` ใบเดียว **ตัดทิ้งแล้ว** แทนด้วยเทส end-to-end จริง
(`Bg0015WiredPathTests`) ที่ขับ dispatch จริงในฉาก 14 แล้ววัด event ที่ออกมาจริง ๆ พร้อม
assertion ว่า `target_not_in_ledger` ต้อง **ไม่โผล่เลย** ในทุก event ของเซสชันนั้น

**[แก้อีกชั้น รอบที่ 3 -- เทสนั้นปักน้อยกว่าที่เคยเขียนไว้]** เทส end-to-end ใบนั้นแยก identity ของ
Bg0015 ออกจากจำนวนเต็มอะไรก็ได้**ไม่ได้**: `0xDEADBEEF`, `0x1`, `0xFFFF` ให้ event/โฟลเดอร์/ledger
ว่างชุดเดียวกันเป๊ะ สิ่งที่มันปักจริงคือ "**ฉาก 14 resolve เป็นโฟลเดอร์ Bg0015 บน roster ว่าง**"
เขียนใหม่ให้ตรงแล้ว และเพิ่ม assertion ที่ยิงสามเลขนั้นเข้าไปในเทสเอง เพื่อให้คนอ่านเห็นข้อจำกัด
ไม่ใช่ต้องเชื่อคำอธิบาย

~~(ส่วนที่ยังถูก: ... เทสในไฟล์ใหม่ยังยืนยันความต่างของ scene tag)~~ **ผิด**: การเปลี่ยนชื่อไฟล์
รอบแก้ที่ 2 ทำให้ pin ตัวนั้น (`test_open_ledger_for_scene_id_vs_sync_combat_scene_state_scene_
tag`) **หายไปเฉย ๆ** ขณะที่ประโยคนี้ยังอ้างว่ามีอยู่ -- **กู้กลับมาแล้ว** เป็นเทสของตัวเอง
(`test_the_two_scene_tag_readers_disagree_and_that_is_pinned`) ปักครบทั้งสามข้อเดิม
(`scene_folder_for_scene_id(14) == "Bg0015"`, `field_mobs.scene_for_scene_id(14) is None`,
ledger สองใบไม่เท่ากันแต่ identities ว่างเท่ากัน)

## ของแถมที่พบระหว่างตรวจ (เขตสาย B, BUILD-006) -- `DropLedger.looted` ไม่มี scene term

`mob_loot.DropLedger.looted` (`mob_loot.py:1367`, `1396-1414`) เก็บเป็น `(actor_identity,
kill_token)` **ไม่มี scene** และไม่เคยถูกล้างตอนข้ามฉาก (ต่างจาก ledger/AI register ที่
`_sync_combat_scene_state` เปิดใหม่หมด) การกันซ้ำอยู่ที่ `previous >= kill_token` →
`mob_already_looted` (`mob_loot.py:1600-1605`) วันนี้ **ไม่พัง** เพราะ
`kill_token = death_step.register.generation` เป็นตัวนับที่โตขึ้นเรื่อย ๆ ข้ามฉาก การฆ่า identity
เดิมในฉากอื่นจึงมี token สูงกว่าเสมอ → ผ่าน ไม่ใช่เพราะมีการแยกฉากใด ๆ **ข้อสรุปเดิมของรอบนี้ที่ว่า
"state ข้ามฉากปลอดภัย" ยังถูก แต่เหตุผลที่เขียนไว้ผิด** -- ถ้าวันหนึ่ง kill_token ถูกรีเซ็ตต่อฉาก
หรือถูกทำให้เป็น per-scene ของที่ดรอปในฉากที่สองจะถูกปฏิเสธเป็น `mob_already_looted` ทันที
บันทึกไว้ตรงนี้ (และในจดหมาย) ยังไม่แก้โค้ดรอบนี้: การแก้จริงคือเติม scene term ลง looted register
ซึ่งแตะ BUILD-006 ที่กำลังบล็อกด้วย `GT-146` อยู่ -- ไม่ควรขยับพร้อมกันโดยไม่มีคนดูหน้าจอ

## ตัวเลขที่วัดได้

```
[ตัวเลขชุดแรก คงไว้เป็นประวัติ ไม่ลบ]
~~tests/test_mob_combat_bg0015_gap.py : ใหม่ 7 ใบ~~
~~หลังแก้ทั้งสองไฟล์: 0 failed, 6067 passed, 327 skipped, 13094 subtests (137.99s)~~
~~ไฟล์ที่แตะรอบนี้ (pirate-force-server) รวม 5~~  <- D9: จริงคือ 6 (ลืมนับไฟล์ CLAIM)
~~cp874 sweep (โมดูลใหม่ + เทสใหม่): ผ่านทั้งคู่~~ <- D10: ผ่านจริงเฉพาะสอง .py ใหม่ ไม่ครอบคลุม
  ไฟล์รอบนี้เอง (มี U+2460 ที่ cp874 แมปไม่ได้ -- อยู่นอกขอบเขต src/ tools/ current/ ตามกฎ
  แต่คำกล่าวอ้างเดิมกว้างเกินความจริง)

[ตัวเลขชุดแก้แล้ว -- ADDENDUM 6cm6ry-2]
tests/test_mob_combat_bg0015_gates.py : ใหม่ 13 ใบ ผ่านทั้งหมด (แทน 7 ใบเดิม)
src/pirateforce_foundation/mob_combat_bg0015_gates.py : 1 ไฟล์ (เปลี่ยนชื่อ + เขียนใหม่ทั้งไฟล์)

การวัดจริง (python สด, รอบแก้):
  cross_scene_identity_collisions() ที่ HEAD          : ()            <- D3
  bg0002 x bg0015 (roster จริงที่ผ่าน owner filter)   : (0x2058,)     1 จุด, placement 87 สองฝั่ง
  live_scenes()                                       : ('Bg0002', 'bg0001')
  roster_for_scene_id(14)                             : 0 แถว
  templates_without_a_death_ruling()                  : (343,345,348,350,353,355,924)
  mob_scene_recompose.composer_scene_ids()            : (1, 2)
  census ของสาย A สำหรับฉาก 14 (สร้างจริง)            : 81 actor, 0x2002-0x205a   <- D7
  splice identities ที่ไม่มีใน census ของสาย A        : ()  (ทั้ง 12 ตัวมีตัวจริงรองรับ)
  event ที่ dispatch จริงตอบเมื่อตีในฉาก 14 (12 สวิง)  : mob_combat_target_not_a_field_mob_no_reply
                                                        12/12 ครั้ง, target_not_in_ledger 0 ครั้ง  <- D1

ราคาจริงของการลงทะเบียน Bg0015 (วัดเอง: แก้ field_mobs.py ชั่วคราว รันสวีตเต็ม แล้ว
git checkout คืน -- ไม่ commit)                                                        <- D2/D8
  ~~35 failed, 6056 passed, 327 skipped, 13166 subtests (139.78s)~~ <- 6056 มาจากทรีก่อนเปลี่ยน
    ชื่อไฟล์เทส (รอบแก้ที่ 3 วัดซ้ำที่ HEAD)
  35 failed, 6062 passed, 327 skipped, 13166 subtests (141.37s)
    แยกส่วนที่ร่างก่อนรวบเป็นตัวเลขเดียว: 11 บรรทัด FAILED (3 ในนั้นคือเทสของรอบนี้เองที่ยืนยัน
    ว่าเงื่อนไขยังปิดอยู่) + 24 subtest failure (2 ใบ ใบละ 12 identity)
  ในนั้นเป็นเทสที่ไม่ใช่ของรอบนี้ 10 ใบ ใน 5 ไฟล์:
    tests/test_field_mob_tables_bg0015.py (guard ผู้ import ที่ได้รับอนุมัติ) 1
    tests/test_field_mobs.py 1 · tests/test_field_mobs_scene_binding.py 4
    tests/test_mob_death_wired_widening.py 3 (มี 12 subfailure ต่อใบ = ทั้ง 12 แถวตายไม่ได้)
    tests/test_mob_scene_recompose.py 1
  ~~"182 assertion ใน 6 ไฟล์"~~ เป็นตัวเลขที่รับช่วงมาจากรอบ jqxe6v ไม่ได้วัดที่ HEAD

สวีตเต็ม pirate-force-server (pytest tests -q):
  baseline ก่อนรอบนี้ทั้งรอบ (git stash -u, วัดตอนต้นรอบ):
    0 failed, 6060 passed, 327 skipped, 13092 subtests passed (136.58s)
  ~~หลังแก้ตาม pf-adversary รอบแรก: 0 failed, 6073 passed, 13094 subtests (139.44s)~~
  หลังแก้ตาม pf-adversary รอบสอง (ทรีที่ commit จริง):
    0 failed, 6077 passed, 327 skipped, 13094 subtests passed
    ระหว่างทางแดง 1 ใบตามคาดแล้วแก้: tests/test_mob_ai_control.py::ContainmentTests::
    test_exactly_runtime_dispatches_this_lane_now (โมดูลนี้ import mob_ai_control เพื่อเรียก
    open_register จริง = importer ตัวที่สาม) เพิ่มชื่อในลิสต์พร้อมเหตุผลว่าไม่ใช่ dispatcher

acceptance criterion ของ pf-adversary (ทำจริง ไม่ใช่รับปาก):
  stub `splice_identities_missing_from` -> `return ()` แล้วรันไฟล์เทสของโมดูลนี้
    ก่อนแก้ : 12/13 เขียว (เทสที่ควรจับกลับไม่เรียกฟังก์ชันเลย)
    หลังแก้ : `test_the_backing_check_reports_exactly_the_identities_it_is_not_given` **แดง**
  ~~เดลต้า +13 passed~~ เดลต้าสุทธิ vs baseline: +17 passed, +0 skipped, +2 subtests, 0 failed
    -- ตรงกับ 17 เทสใหม่
    ในไฟล์เทสของโมดูลนี้เป๊ะ ไม่มีอะไรอื่นขยับ
git diff --check: silent
cp874 sweep: src/pirateforce_foundation/mob_combat_bg0015_gates.py ผ่าน,
  tests/test_mob_combat_bg0015_gates.py ผ่าน (ขอบเขตกฎคือ src/ tools/ current/ -- ไฟล์รอบ/จดหมาย
  ไม่อยู่ในขอบเขตนั้น และไฟล์นี้เองมี U+2460 อยู่จริง)
~~ไฟล์ที่แตะรอบนี้ (pirate-force-server) รวม 6~~ -> รวม **7** หลังรอบแก้ที่ 3:
  src/pirateforce_foundation/mob_combat_bg0015_gates.py [ใหม่; เปลี่ยนชื่อจาก ..._gap.py; เขียนใหม่
    ทั้งไฟล์รอบแก้ที่ 3 -- ตัด GATE_OWNERS/closed_gates, เพิ่มการวัด ai_row_missing]
  tests/test_mob_combat_bg0015_gates.py [ใหม่; เปลี่ยนชื่อ + เขียนใหม่สองครั้ง; 17 ใบ]
  tests/test_field_mobs.py [ลิสต์ importer ปัก]
  tests/test_mob_stat_fabrication_guard.py [LANE_B_MODULES]
  tests/test_mob_ai_control.py [ContainmentTests: importer ตัวที่สามพร้อมเหตุผล -- ใหม่รอบแก้ที่ 3]
  rounds/B_20260901_0106_6cm6ry_bg0015-combat-ledger-gap-measured.md [ไฟล์นี้]
  rounds/B_20260901_0106_6cm6ry_CLAIM.md  <- D9: ไฟล์ที่ลืมนับในรายการเดิม
```

`current/pf_login_game_server_v141.py`: ไม่แตะ (โมดูลนี้ไม่ต้องใช้ `legacy` เลย -- ไม่ compose
เฟรม). ไม่แตะ canonical DB, capture corpus. ไม่แตะ `runtime.py`/`app.py`. ไม่แตะ
`field_mobs._SCENE_TABLE_MODULES`/`live_scenes()`. ไม่แตะเขตสาย A (`scenarios/world_*.json`)

## ยังไม่ได้พิสูจน์

- ~~ว่า chief/สาย A จะเลือกลงทะเบียน Bg0015 ตอนไหน ... (182 assertion)~~ **[แก้]** คำถามไม่ใช่
  "ตอนไหน" แต่เป็น "ใครเปิดประตูไหน" -- สี่ประตู เจ้าของไม่เหมือนกัน สาย B สร้างได้เองบานเดียว
  (composer ของ `mob_scene_recompose` สำหรับฉาก 14) และราคาที่วัดได้คือ 35 failed / 10 เทส / 5 ไฟล์
  ไม่ใช่ 182 assertion
- ประตู 2 (ขยาย guard) กับประตู 3 (owner ruling ของ 7 template) **ไม่ใช่ของสาย B เลย** -- ยังไม่มี
  ใครรับ ต้องรอ COO/เจ้าของระบุเจ้าของก่อน
- BUILD-006 (GT-146), Door B, KA1B defect ①: ไม่เปลี่ยนจากที่บันทึกไว้ก่อนหน้า ไม่ relitigate
- ผลกระทบจริงบนจอ (ยังไม่มี caller ใน runtime.py ให้ทั้งครึ่งภาพและครึ่งตี)
- `DropLedger.looted` ไม่มี scene term (ดูหัวข้อของแถม) -- ยังไม่มีการพิสูจน์ว่าพังจริงในเซสชันจริง
  วันนี้ (วัดแล้วว่ายังไม่พังเพราะ token โตทางเดียว) แต่ก็ยังไม่มีเทสปักไว้ว่ามันจะไม่พังวันหน้า

## CORE-REQUEST

ไม่มีคำขอแก้ `runtime.py` ใหม่รอบนี้ ~~(ครึ่งภาพยังรอ chief ต่อสายที่ `runtime.py:7501` ตามเดิม)~~
**[แก้ตาม D7]** จุด census ของฉาก 14 ไม่ใช่ `runtime.py:7501` (นั่นอยู่ในกิ่งของฉาก 2) --
ฉาก 14 เดินผ่านกิ่ง `lane_hooks.scene_census_composer(scene_id)` ที่ `runtime.py:7626` ซึ่ง
**ทำงานอยู่แล้ววันนี้** ดังนั้นการ splice ของ CORE-REQUEST เดิมต้องเสียบเข้ากับเส้นทางนั้น
ไม่ใช่กิ่งของฉาก 2 -- เรื่องนี้แจ้ง chief/สาย A ในจดหมายรอบนี้ (ไม่ใช่คำขอใหม่จากสายนี้ แต่เป็นการ
แก้ที่อยู่ของคำขอเดิมที่ทั้งสองสายเขียนไว้ผิด)

## รายการเงื่อนไขนี้ยังไม่ครบ -- ตอบคำถามปิดท้ายของ pf-adversary ตรง ๆ

คำถาม: ทุก "ประตู" ที่รายงานมาคือ predicate ที่อ่านได้อยู่แล้ว ไม่มีข้อไหนเกิดจากการเดินเส้นทางที่
คำสั่งจริงเดิน -- แล้วอะไรทำให้เชื่อว่ารายการจบที่ห้าหรือหก

**ตอบ: ไม่มีอะไรทำให้เชื่ออย่างนั้น และรายการนี้ไม่ควรถูกใช้ตั้งงบ** เหตุผลที่ raise ของ
`mob_ai_control.open_register` หลุดสองรอบติดคือขั้นตอนที่ใช้ตอนนั้นอ่าน predicate อย่างเดียว
ทั้งที่ raise อยู่ต่ำกว่าบรรทัดที่ตัวเองยกมาแค่สองบรรทัด ขั้นตอนที่ใช้จริงรอบนี้ (บันทึกไว้ในโมดูล
ชื่อ `ENUMERATION_PROCEDURE` ให้รอบหน้ารันซ้ำได้):

1. อ่าน predicate ที่เกี่ยวข้อง -- เจอเฉพาะสิ่งที่มีคนเคยตั้งชื่อไว้
2. แก้บนทรีทดลอง + รันสวีตเต็ม -- เจอเฉพาะสิ่งที่สวีตปักไว้
3. **แก้แล้วขับคำขอจริงหนึ่งใบผ่าน dispatch จริง แล้วอ่าน traceback** -- ข้อ 3 เท่านั้นที่เจอข้อ 5

**ขีดจำกัดของขั้นตอนนี้เอง**: มันเดินคำขอหนึ่งใบไปถึงความล้มเหลว**ครั้งแรก** และความล้มเหลวครั้งแรก
บังทุกอย่างถัดจากนั้น เส้นทาง ฆ่า/ลูท/ซาก/สร้าง census ใหม่ ในฉาก 14 ยังไม่เคยถูกขับเลย เพราะเซสชัน
ตายก่อน -- ข้อ 6 (census rebuild ไม่มี `_apply_mob_death_census_override` ในกิ่งของฉาก 14) จึงยัง
เป็น **inference จากการอ่านโค้ด ไม่ใช่การวัด** และถูกติดป้ายแบบนั้นทั้งในโมดูลและในจดหมาย

## เปิดใบให้สาย C

ไม่มี -- ไม่มีคำถามที่ต้องรอคำตอบจากภายนอกโปรเจกต์รอบนี้ (คำถามเรื่องใคร regenerate
`field_mob_ai_tables` เป็นคำถามภายในถึง chief/COO ไม่ใช่ใบ RE ของไคลเอนต์)

## nonclaim

ไม่แตะ `runtime.py`/`app.py`/`current/pf_login_game_server_v141.py`/`scenarios/world_*.json` เลย
รอบนี้ ไม่ลงทะเบียน Bg0015 ใน `field_mobs._SCENE_TABLE_MODULES` (เจตนา ไม่ใช่การลืม) ไม่อ้าง
milestone เกมเพลย์ใหม่บนจอ -- โมดูลใหม่ไม่มี caller เลย (grep ยืนยัน `runtime.py`/`app.py`: 0 hit)

## pf-adversary (self-review, ไม่มี Agent/Task tool ให้เรียก subagent รอบนี้)

1. เช็คว่า claim "ledger เดียวกับที่ `_sync_combat_scene_state` จะเปิด" จริงไหม -- พบว่าไม่จริง
   100% (scene tag ต่างกัน) แก้คำอธิบายให้ตรงและเพิ่มเทสปักความต่างนั้นก่อน commit แทนที่จะปล่อย
   คำกล่าวอ้างที่เกินจริงไว้
2. เช็คว่าโมดูลใหม่แอบมีคำว่าชื่อไฟล์ตาราง Bg0015 หลุดเข้ามาไหม (จะชน guard ของ
   `test_field_mob_tables_bg0015.py`) -- เจอ 1 จุดในดราฟต์แรก (อ้างชื่อไฟล์เทสของโมดูลนั้นในดอก
   สตริง NONCLAIM) แก้เป็นคำอธิบายที่ไม่ต้องสะกดชื่อไฟล์ก่อน commit ยืนยันด้วย grep ซ้ำ = 0 hit
3. เช็คว่าฟังก์ชันวัดผล "vacuously true" ไหม (เช่นเทียบ ledger กับตัวเอง) -- เพิ่ม assertion เทียบกับ
   ledger ของฉากผิด (Bg0002) เพื่อพิสูจน์ว่าฟังก์ชันแยกแยะได้จริง ไม่ใช่ผ่านเพราะเงื่อนไขว่างเปล่า
4. เช็คว่าการ reload โมดูลนี้แอบ mutate `field_mobs.live_scenes()` ไหม (containment) -- ไม่พบ
   ปักด้วยเทสเปรียบเทียบก่อน/หลัง import ตรง ๆ
5. รัน cp874 sweep สองไฟล์ใหม่ตรง ๆ ก่อน commit -- ผ่านทั้งคู่
6. รันสวีตเต็มสองครั้ง (ก่อน/หลัง, `git stash -u`) แทนการเชื่อผลของเทสไฟล์เดียว -- ยืนยันไม่มีอะไร
   อื่นขยับนอกจากสองไฟล์ปักที่ตั้งใจแก้

**สิ่งที่ self-review รอบแรกจับไม่ได้ และ pf-adversary จับได้ (บันทึกไว้เพื่อไม่ให้เกิดซ้ำ)**: ทั้ง
หกข้อข้างบนตรวจ "โค้ดตรงกับที่เขียนบรรยายไหม" แต่ไม่มีข้อไหนถามว่า **ข้อความบรรยายนั้นจริงกับ
ระบบที่เดินอยู่ไหม** -- ข้อ 3 ถึงกับเขียนว่าตรวจ "vacuously true" แล้ว ทั้งที่ฟังก์ชันหลักเทียบ
roster กับตัวมันเอง บทเรียนที่บันทึกไว้เป็นข้อปฏิบัติของรอบต่อไป: (ก) ข้ออ้างเรื่อง "ระบบจะตอบ
อะไร" ต้อง**ขับของจริง**หนึ่งครั้งเสมอ (harness มีอยู่แล้วใน `tests/test_scene_scoped_combat_
wiring.py` ตั้งแต่ก่อนรอบนี้) (ข) ประโยคที่ยกมาจากดอกสตริงต้อง `grep` หาเทสที่ปักมันไว้ก่อนเชื่อ
ว่าเป็นปัจจุบัน (ดอกสตริงในโปรเจกต์นี้เก็บประวัติแบบขีดฆ่าไว้ด้วย) (ค) "ราคา" ที่จะบอกคนอื่นต้อง
วัดเองที่ HEAD ไม่ใช่รับช่วงจากรอบก่อน (ง) ฟังก์ชันเปรียบเทียบทุกตัวต้องมีเทสกลายพันธุ์คู่กัน

-- LANE-B (COMBAT) รอบ `6cm6ry` (แก้ตาม pf-adversary, ADDENDUM 6cm6ry-2)
