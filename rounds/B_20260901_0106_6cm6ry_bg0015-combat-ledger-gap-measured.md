# LANE-B round `6cm6ry` (COMBAT)

เปิดรอบ 2026-09-01T01:06+07:00 (scheduled, ไม่มีคนเฝ้าหน้าจอ) Branch:
`claude/determined-brown-6cm6ry` (repo นี้), `claude/wonderful-gauss-6cm6ry`
(pf_bridge)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

**ไม่มี.** รอบนี้ไม่ได้ต่อสายอะไรใหม่ให้ผู้เล่นเห็น -- เป็นรอบที่วัดและพิสูจน์ช่องโหว่จริงที่ยังไม่มี
ใครเคยพูดถึงตรง ๆ ก่อนหน้านี้ (ดูหัวข้อถัดไป) โมดูลใหม่ (`mob_combat_bg0015_gap.py`) ไม่มี
caller ใน `runtime.py` เลย ไม่ compose เฟรม ไม่แตะ `field_mobs._SCENE_TABLE_MODULES`

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
เท่านั้น ไม่งั้นเปิด roster ว่าง `field_mobs._SCENE_TABLE_MODULES` (รอบ jqxe6v วัดไว้แล้วว่ามี
182 assertion ปักอยู่ทั่วหกไฟล์เทสที่หมายถึง "สองฉากที่ ship แล้ว" -- **ตั้งใจเลื่อนการลงทะเบียนฉาก
ที่สามไปให้ chief ประสานงานเอง ไม่ทำเป็นผลข้างเคียง**) ยังมีแค่ bg0001/Bg0002 ที่ HEAD ของรอบนี้

ผลคือ: **แม้ chief ต่อสาย CORE-REQUEST ของ census/splice สำเร็จ 100% ตามที่ขอ ผู้เล่นก็ยังคลิกตี 12
ตัวที่ดูเป็นสีแดง/hostile นั้นไม่ได้เลย** -- ทุกจังหวะตีจะถูกปฏิเสธด้วย
`mob_combat.REFUSE_TARGET_NOT_IN_LEDGER` เพราะ ledger ของฉาก 14 เปิดว่างเปล่าเสมอ (scene 14 ไม่มี
mob table ที่ลงทะเบียนไว้) นี่คือ "มองเห็นเป็นมอนสัตว์ร้าย แต่แตะต้องไม่ได้เลย" -- BUILD-004
(การมองเห็น) จะสำเร็จ แต่ BUILD-005 (ตี/ตาย/ซาก) จะยังไม่ทำงานเลยสำหรับฉากนี้ จนกว่าจะมีการแก้ไข
เพิ่มอีกชั้นหนึ่งที่ยังไม่มีใครพูดถึงมาก่อนในจดหมายทั้งสองฉบับที่ยืนยันร่วมกัน

## ของจริงที่สร้างรอบนี้ -- `mob_combat_bg0015_gap.py` (วัด ไม่ลงทะเบียน)

`src/pirateforce_foundation/mob_combat_bg0015_gap.py` (ใหม่): โมดูลวัดผลล้วน ๆ แบบเดียวกับ
`mob_combat_membership.py` (ไม่มี caller, ไม่ compose เฟรม) **ไม่แตะ**
`field_mobs._SCENE_TABLE_MODULES`/`live_scenes()` เลย -- เคารพการตัดสินใจของรอบ jqxe6v ที่เลื่อน
การลงทะเบียนฉากที่สามไปให้ chief/สาย A ประสานงานร่วมกันก่อน (ขนาดงาน 182 assertion ไม่ใช่เรื่องเล็ก
ที่จะแอบทำเป็นผลข้างเคียงของรอบนี้) แทนที่จะลงทะเบียนเอง โมดูลนี้ให้ **สองข้อเท็จจริงที่วัดแล้ว**
สำหรับใครก็ตามที่จะตัดสินใจเรื่องนั้นในอนาคต:

1. `bg0015_registration_would_line_up_with_the_visual_splice()` -- ถ้าลงทะเบียน Bg0015 จริง ledger
   ที่เปิดได้จะมี identity ตรงกับ 12 ตัวที่ `field_mob_hostile_bg0015.scene14_hostile_overrides()`
   splice ไว้เป๊ะ (ทั้งสองฝั่งอ่านตารางเดียวกันด้วยสูตรเดียวกัน ไม่มีทางเบี้ยว)
2. `bg0002_bg0015_identity_collisions()` -- วัดจริงแล้วพบการชนกัน **1 จุดเดียว**: placement 87
   ของ Bg0002 (Fighting Fish soldier) กับ placement 87 ของ Bg0015 คำนวณ identity เดียวกัน
   `0x2058` (`FieldMob.actor_identity` ไม่มี scene term, COO-DECISION 2026-08-27T14:41+07:00)
   **ไม่ใช่ความเสี่ยงชนิดใหม่**: bg0001/Bg0002 ชนกันแบบนี้อยู่แล้ววันนี้ที่ `0x2068`/`0x206a`
   (คอมเมนต์ของ `mob_combat.open_ledger_for_scene_id` เอง) และ `_sync_combat_scene_state` เปิด
   ledger/register ใหม่ทั้งชุดทุกครั้งที่ข้ามฉาก (M2 ข้ามฉากในเซสชันเดียวยังหยุดอยู่ตาม
   PANYA-DECISION 2026-08-27T20:10+07:00) จึงไม่มีเซสชันจริงไหนถือสองฉากพร้อมกันในเลดเจอร์เดียว

ยังพิสูจน์ TODAY's STATE ด้วยโค้ดจริง ไม่ใช่แค่อ่านคอมเมนต์: `mob_combat.open_ledger_for_scene_id
(14)` เปิด ledger ว่าง (0 identities) จริง และ `balance_of()` ปฏิเสธทั้ง 12 identity ด้วย
`REFUSE_TARGET_NOT_IN_LEDGER` จริง (`tests/test_mob_combat_bg0015_gap.py`) พบและบันทึกความต่าง
เล็กหนึ่งจุดระหว่าง `open_ledger_for_scene_id(14)` (scene tag = `None`) กับ ledger ที่
`_sync_combat_scene_state` จะเปิดจริง (scene tag = `"Bg0015"`) -- ทั้งคู่ปฏิเสธเหมือนกันทุกกรณี
เพราะ `balance_of` ไม่เคยอ่าน `.scene` เลย แต่บันทึกไว้ตรง ๆ แทนที่จะอ้างว่าเหมือนกันทุกกระเบียด
เมื่อจริง ๆ ไม่ใช่ (adversarial self-catch รอบนี้)

## ตัวเลขที่วัดได้

```
tests/test_mob_combat_bg0015_gap.py : ใหม่ 7 ใบ ผ่านทั้งหมด
src/pirateforce_foundation/mob_combat_bg0015_gap.py : ใหม่ 1 ไฟล์

การชนกันจริงที่วัดได้ (python สด, ไม่ใช่เดา):
  bg0001 x bg0015 collisions: [] (0 จุด)
  bg0002 x bg0015 collisions: [0x2058] (1 จุด, placement 87 ทั้งสองฝั่ง)

สวีตเต็ม pirate-force-server (pytest tests -q), git stash -u แยกก่อน/หลังจริง:
  ก่อน (stash -u เอาไฟล์ใหม่ทั้งสองออก):
    0 failed, 6060 passed, 327 skipped, 13092 subtests passed (136.58s)
  หลัง (stash pop คืนของ, ไม่มี pin drift เพราะโมดูลนี้ตั้งใจไม่แตะ registry):
    รอบแรก (ก่อนแก้ 2 pinned-importer test): 2 failed, 6064 passed, 327 skipped,
      13092 subtests passed (135.75s) -- คาดไว้: โมดูลใหม่มีคำว่า "field_mobs" และขึ้นต้นด้วย
      "mob_" จึงชนกับ tripwire ที่ตั้งใจให้ชน (test_field_mobs.py's importers list,
      test_mob_stat_fabrication_guard.py's LANE_B_MODULES tuple)
    หลังแก้ทั้งสองไฟล์ + เพิ่มเทสปักความต่างของ scene tag: 0 failed, 6067 passed,
      327 skipped, 13094 subtests passed (137.99s)
  เดลต้าสุทธิ (หลัง vs ก่อน): +7 passed, +0 skipped, +2 subtests, 0 failed -- ตรงกับ 7 เทสใหม่
    ในไฟล์เทสของโมดูลนี้เป๊ะ ไม่มีอะไรอื่นขยับ
git diff --check: silent
cp874 sweep (โมดูลใหม่ + เทสใหม่): ผ่านทั้งคู่
ไฟล์ที่แตะรอบนี้ (pirate-force-server) รวม 5:
  src/pirateforce_foundation/mob_combat_bg0015_gap.py [ใหม่]
  tests/test_mob_combat_bg0015_gap.py [ใหม่]
  tests/test_field_mobs.py [เพิ่ม importer ในลิสต์ปัก]
  tests/test_mob_stat_fabrication_guard.py [เพิ่มชื่อโมดูลใน LANE_B_MODULES]
  rounds/B_20260901_0106_6cm6ry_bg0015-combat-ledger-gap-measured.md [ไฟล์นี้]
```

`current/pf_login_game_server_v141.py`: ไม่แตะ (โมดูลนี้ไม่ต้องใช้ `legacy` เลย -- ไม่ compose
เฟรม). ไม่แตะ canonical DB, capture corpus. ไม่แตะ `runtime.py`/`app.py`. ไม่แตะ
`field_mobs._SCENE_TABLE_MODULES`/`live_scenes()`. ไม่แตะเขตสาย A (`scenarios/world_*.json`)

## ยังไม่ได้พิสูจน์

- ว่า chief/สาย A จะเลือกลงทะเบียน Bg0015 ตอนไหน (พร้อมกับ census splice, ก่อน, หรือหลัง) -- เป็น
  การตัดสินใจร่วมที่รอบ jqxe6v เลื่อนไว้แล้วด้วยเหตุผลเรื่องขนาดงาน (182 assertion) ไม่ใช่รอบนี้ตัดสิน
- BUILD-006 (GT-146), Door B, KA1B defect ①: ไม่เปลี่ยนจากที่บันทึกไว้ก่อนหน้า ไม่ relitigate
- ผลกระทบจริงบนจอ (ยังไม่มี caller ใน runtime.py ให้ทั้งครึ่งภาพและครึ่งตี)

## CORE-REQUEST

ไม่มีคำขอแก้ `runtime.py` ใหม่รอบนี้ (ครึ่งภาพยังรอ chief ต่อสายที่ `runtime.py:7501` ตามเดิม) --
สิ่งที่ส่งรอบนี้คือจดหมายเพิ่มเติมถึง chief/สาย A ชี้ช่องโหว่ครึ่งที่สองที่พบ พร้อมสองข้อเท็จจริงที่
วัดแล้วให้ใช้ตัดสินใจได้ทันที ไม่ต้องมาไล่หาใหม่

## เปิดใบให้สาย C

ไม่มี -- ไม่มีคำถามที่ต้องรอคำตอบจากภายนอกโปรเจกต์รอบนี้

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

-- LANE-B (COMBAT) รอบ `6cm6ry`
