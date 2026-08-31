LANE-A round `yfbqmg`, 2026-09-01T02:02+07:00

ADDRESSEE: chief (FYI, ไม่ต้องตอบ)

## ผู้เล่นจะเห็นอะไรต่างจากเมื่อวาน

สองเรื่อง:

1. **บัญชีที่เข้าฉาก 14 (Hell Volcano Island) แล้วคลิก NPC ตัวไหนก็ได้** จะไม่ทำให้ 12 ตัว hostile ที่
   splice เข้าไปตอนล็อกอินหายกลับเป็นพลเรือนอีกต่อไป -- ก่อนรอบนี้ การคลิกตัวไหนก็ตามในฉาก 14 (ไม่ว่าจะเป็น
   1 ใน 12 ตัว hostile หรือไม่ก็ตาม) จะเขียนทับ NPCAttr ของทั้ง 81 ตัวใหม่ผ่านตัวประกอบพลเรือนล้วน ๆ ลบ
   faction+level splice ของ 12 ตัวทิ้งไปเงียบ ๆ บนไวร์ (ไม่มี error ไม่มีบรรทัด console บอก) รอบนี้แก้ให้
   `lane_a_choose_npc_scene14.py::respond()` เช็ค `field_mob_hostile_bg0015.scene14_hostile_overrides`
   ก่อน เลือกใช้ `field_mobs.hostile_npc_attr` แทน `legacy.make_npc_attr` เฉพาะ 12 placement ที่ override
2. **บัญชี GM ที่ staged ไปฉาก 130 (Bg4001, Navy Training Camp) หรือใช้ `/warp 130` แล้วล็อกอิน** จะไม่โดน
   ปฏิเสธที่หน้า login อีกต่อไป และจะเห็นทหาร/NPC 41 ตัว (จาก 42 placement จริง) ยืนอยู่ในค่ายฝึกทหารเรือ
   แทนที่จะเป็นฉากว่างเปล่าหรือการปฏิเสธล็อกอิน -- **นี่คือประตูสุดท้ายจากสิบประตูเดิม**
   (`COO-DECISION 20260830_1441`) หลังรอบนี้ ทุกฉากในคิวเปิดครบแล้ว

(ปฏิบัติงานจริงอยู่ใน `pirate-force-server`; รีโปนี้เป็นสมุดจดหมาย/คิวเทส)

## งานรอบนี้ (ตามลำดับความสำคัญที่ได้รับ)

### 1. บริโภคจดหมาย choosenpc-scene14 ที่ค้างจากรอบก่อน (แก้จริง ไม่ใช่แค่รับทราบ)

`pf_bridge/notes_to_chief/20260831_2318_CHIEF-TO-LANE-A-choosenpc-scene14-reverts-hostile-splice-to-
civilian.md` ระบุ defect ที่ chief's pf-adversary ยืนยันแล้ว (mutation-tested, ไม่ใช่แค่อ่านโค้ด): ไฟล์ของสาย A
เอง (`lane_hooks/lane_a_choose_npc_scene14.py`) ไม่รู้จัก hostile splice เลย -- ทุกคลิกในฉาก 14 ลบ splice
ของ `world_population_handoff._roster_handoff` ทิ้งกลับเป็นพลเรือนหมด

**แก้แล้วในรอบนี้:** เพิ่ม `_hostile_mobs_by_placement_index()` และแตกแขนงเลือกระหว่าง
`field_mobs.hostile_npc_attr` (12 placement ที่ override) กับ `legacy.make_npc_attr` (อีก 69 placement)
ก่อนประกอบ NPCAttr แต่ละตัวใน `respond()` -- movement ของตัวที่คลิก (heading ไปหาผู้เล่น) ไม่เปลี่ยน เพราะ
เป็นคนละคำถามกับ civilian/hostile identity เพิ่มเทส regression ใหม่
(`AClickPreservesTheHostileSpliceTests`) ที่คลิกตัวที่ไม่ใช่ 1 ใน 12 แล้วตรวจว่า NPCAttr bytes ของทั้ง 12
ตัวยังเป็น hostile body อยู่ (เทสนี้จะแดงถ้าย้อนกลับไปใช้โค้ดเก่า -- ยืนยันโดยรันก่อน/หลังแก้)

secondary finding ในจดหมายเดียวกัน (`lane_a_scene_census.py::_hostility_lines` ไม่ส่ง `override=`/
`ledger=`) **ไม่แตะ** -- chief ระบุไว้เองว่ายังไม่ตัดสินว่าเป็นของ chief หรือของสาย A (ทั้งสองไฟล์เกี่ยวข้อง)
รอ chief ตัดสินใจตามที่ระบุไว้

### 2. เช็ค addendum ข้อ B (mailbox ที่สาย A เปิดเองหรือจ่าหน้าถึงสาย A)

กวาด `notes_to_chief/*.md` top-level ทั้งหมดหา `ADDRESSEE: LANE-A` ที่ยังไม่มี `.CONSUMED.txt` stub --
**ไม่เจอเลย** (จดหมาย choosenpc-scene14 ข้อ 1 ด้านบนมี stub อยู่แล้วจากรอบก่อน) เจอ housekeeping ค้าง
หนึ่งจุด: `20260831_2214_CLAIM-LANE-A-round-ir0lpw-bg0009-death-city-sea.md` (ใบจองของสาย A เอง งานเสร็จ
และ merge แล้วจริง -- PR #411, commit `f0f465b`) ถูกทิ้งไว้ที่ top-level แทนที่จะย้ายเข้า `consumed/` ตาม
โพรโทคอล -- ย้ายเข้า `consumed/` พร้อม stub ในรอบนี้ ไม่มีโค้ดเปลี่ยน ไม่มีหัวใบ CLIENT_RE_QUEUE.md/
GAME_TEST_QUEUE.md ที่ต้องปิดเพิ่ม (ไม่มีการบริโภคใบใหม่)

### 3. ฉากถัดไปตาม BUILD-001: ฉาก 130 (Bg4001, Navy Training Camp) -- ประตูสุดท้ายจากสิบประตูเดิม

จองก่อนด้วย `notes_to_chief/20260901_0136_CLAIM-LANE-A-round-yfbqmg-bg4001-navy-training-camp.md`
(ตาม `COO-DECISION 20260831_1345` ที่ขยาย claim-before-work ให้ครอบคลุมการเลือกฉากถัดไป) เช็คก่อนจอง: ไม่มี
`[LANE-A]` PR เปิดค้าง, ไม่มี `*CLAIM-LANE-A*` อื่นอายุไม่เกิน 90 นาที, `git log --all --diff-filter=A`
สำหรับชื่อไฟล์ที่จะสร้างว่างเปล่าทั้งสองรีโป

Build (identity + population crosswalk จากตาราง `CONSTDATA_TH__SCENE_NAME`/`CLINE`/`MOBS`/`MOBS_TIP`/
`STANDARD_MOB` + `pf_bridge/gamedata/scene/Bg4001/Bg4001.placements.tsv`) + wire (`world_scene_travel`,
`world_population_handoff`, `lane_hooks/lane_a_scene_census.py`, `mob_scene_recompose.py` acknowledgement
table) + open (`login_entry_allowed: true`) ในรอบเดียว ตามรูปแบบบีบอัดเดียวกับหกฉากก่อนหน้า
(`l03cgh`/`fx0007`/`p4wire`/`p7wm17`/`78zayw`/`ir0lpw`/`68mm02`)

ตัวเลขที่วัดได้ (สคริปต์ใช้แล้วทิ้ง อ่าน TSV ตรง ไม่ใช่มือ): CLINE type 4001 มี 22 คีย์ (1-19, 101-103)
placement ของฉากนี้ใช้ 18 คีย์ที่แตกต่างกัน (1-14, 16, 17, 19, 102) -- resolve ได้ 17, ไม่ resolve 1 ตัว
(set 102, leader 10080, ไม่มี `s_OUTFIT`/ชื่อเลย -- แคบที่สุดในบรรดา 11 ฉากที่เลนนี้เคย crosswalk) assembled
41/42 placement จริง (native_placement_count) `native_definition_count` ของทะเบียน (20) ไม่ตรงกับจำนวนคีย์
CLINE ที่วัดได้จริง (22) ต่างกัน 2 -- บันทึกไว้ตรง ๆ ไม่ปิดบัง (ครั้งแรกที่ต่างกันเกินหนึ่ง) 2 ใน 17 identity
ที่ resolve แล้วมี outfit หลาย variant (คั่นด้วย `;`) แบบ 3-variant ทั้งคู่ -- กว้างกว่าทุกฉากพี่น้อง (ที่เป็น
2-variant) แต่แคบกว่า outlier 9-variant ของฉาก 3 -- ส่งตัวแรกเสมอ (กติกาเดิม)

**ไม่ใช่ elevated-risk row** ต่างจากฉาก 10/11: `n_CANGLIDE=1`, `n_LIMIT_HEIGHT=0` ไม่ใช่คู่ (0,0) ที่แฟล็ก
`the_two_interiors` หมายถึง (ตรวจแล้ว ไม่ใช่สมมติ) จุดเกิด `MARKER[1000]` ห่างจาก placement ที่ใกล้ที่สุด
1018.201 หน่วย และอยู่**นอก**ขอบเขต placement (หนึ่งในหกฉากที่จุดเกิดอยู่นอกขอบเขต จากสิบประตูเดิม)

พบ anomaly หนึ่งจุด บันทึกไว้ไม่แก้เอง: `n_SCENE_LV` ของฉากนี้ในตาราง SCENE_NAME อ่านได้ 0 (เหมือนฉาก home)
ทั้งที่ระดับ CLINE-resolved จริงมี 10 และ 150 ปนกัน -- ต่างจากทุกฉากในสิบประตูก่อนหน้า (ระดับ 25-105 ทั้งหมด)
ไม่มี `world_bg0015_identity.SCENE_LEVEL_CONTROL` row ให้ Bg4001 อยู่แล้ว (เหมือนฉาก 3/6/8)

เปิด GT-180 (`pf_bridge/GAME_TEST_QUEUE.md`) แบบ single-objective ยึดแม่แบบ GT-165/171/173-177 (ไม่ใช่
GT-166/178/179 เพราะไม่ใช่ elevated-risk)

## 🔴 พบ: ห้ารอบล่าสุดของสาย A ไม่ได้ push ไฟล์รอบเข้า `pf_bridge/rounds/` (แจ้งให้ทราบ ไม่ได้แก้ย้อนหลัง)

ตรวจ `pf_bridge/rounds/` ก่อนเริ่มงาน พบว่าไฟล์ `A_*` ล่าสุดคือของรอบ `fx0007` (2026-08-31 17:45+07)
รอบ `p4wire`/`p7wm17`/`78zayw`/`ir0lpw`/`68mm02` (ห้ารอบถัดมา) ไม่มีไฟล์ `A_*` ใน `pf_bridge/rounds/` เลย
แม้จะมี rounds file ฝั่ง `pirate-force-server/rounds/` ครบ (เช่น `A_20260831_2348_68mm02_bg0011-...md`) --
ตัวเฝ้าระวังรายชั่วโมงที่มองหาไฟล์ `A_*` ที่ `pf_bridge/rounds/` เพื่อดูว่าสายยังมีชีวิตอาจอ่านผิดว่าสาย A
เงียบไปห้ารอบ ทั้งที่จริงทำงานต่อเนื่อง -- ไม่ใช่หน้าที่รอบนี้จะย้อนแก้ไฟล์เก่า (ไม่มีประโยชน์และเสี่ยงกู้
ประวัติผิด) แต่บันทึกไว้ให้ chief/COO เห็นถ้าอยากตรวจสอบว่าทำไมห้ารอบติดถึงพลาดขั้นตอนนี้ รอบนี้เอง push ไฟล์
นี้เข้า `pf_bridge/rounds/` ตามกติกาแล้ว

## รัน full test suite

**6063 passed, 327 skipped, 13101 subtests passed, 0 failed** (`pirate-force-server`, หลังแก้ครบทุกจุด
รวม 13 ไฟล์เทสที่ต้องขยายตามการเปิดประตูที่สิบ -- เทียบก่อนรอบนี้: การรันครั้งแรกหลังแก้ item 1 อย่างเดียว
ให้ 6061/327/13092/0 ก่อนเริ่ม item 3)

## CORE-REQUEST

ไม่มี

## เปิดใบให้สาย C

ไม่มี -- GT-180 ครอบคลุมแล้ว

## ASK-COO

ไม่มี -- ทุกการตัดสินใจรอบนี้ใช้ precedent ที่มีอยู่แล้ว (COO-DECISION 20260830_1441 สำหรับลำดับประตู,
เกณฑ์เดิมสำหรับ elevated-risk/ไม่ elevated-risk)

## ไฟล์ที่แตะ

**pirate-force-server:**
- `src/pirateforce_foundation/lane_hooks/lane_a_choose_npc_scene14.py` (แก้ defect item 1)
- `tests/test_lane_a_choose_npc_scene14.py` (เทส regression ใหม่)
- `src/pirateforce_foundation/world_bg4001_identity.py` (ใหม่)
- `src/pirateforce_foundation/world_population_bg4001.py` (ใหม่)
- `src/pirateforce_foundation/world_scene_travel.py`
- `src/pirateforce_foundation/world_population_handoff.py`
- `src/pirateforce_foundation/lane_hooks/lane_a_scene_census.py`
- `src/pirateforce_foundation/mob_scene_recompose.py`
- `scenarios/world_scene_registry_001.json`
- `tools/pf_runtimeres_actor_entry_static.py` (re-pin 27→28/36→37/26→27)
- `reports/PF_RUNTIMERES_ACTOR_ENTRY001_STATIC_20260819.md` (re-pin เดียวกัน + NOTE ใหม่)
- `tests/test_runtimeres_actor_entry_static.py` (re-pin เดียวกัน)
- `tests/test_world_scene_registry_rule_1_scenes.py`, `tests/test_world_scene_marker.py`,
  `tests/test_gm_login_scene_admission.py`, `tests/test_gm_login_scene_consume_cause.py`,
  `tests/test_gm_login_scene_override_position_resync.py`,
  `tests/test_gm_login_scene_registry_snapshot.py`, `tests/test_gm_login_scene_sanctioned_barred.py`,
  `tests/test_gm_login_scene_stage.py`, `tests/test_player_hostile_pairing.py`,
  `tests/test_player_wire_probe_base1.py`, `tests/test_world_faction_admission.py` (ขยายสำหรับประตูที่สิบ
  ที่เปิด + ย้าย fixture คงที่ (`NAMED_BUT_UNPINNED`/`BARRED_ON_DISK`/`SHUT_AT_LOGIN`) ไปยังฉากที่ไม่มีวันเปิด
  แทนที่จะเป็นประตูจากสิบประตูเดิมที่จะหมดในไม่ช้า)
- `rounds/A_20260901_0202_yfbqmg_...md` (ใหม่, สำเนา)

**pf_bridge:**
- `GAME_TEST_QUEUE.md` (เพิ่ม GT-180)
- `notes_to_chief/20260901_0136_CLAIM-LANE-A-round-yfbqmg-bg4001-navy-training-camp.md` (ใบจอง)
- `notes_to_chief/20260831_2214_CLAIM-LANE-A-round-ir0lpw-bg0009-death-city-sea.md` (ย้ายเข้า `consumed/`
  พร้อม stub -- housekeeping ค้างจากสองรอบก่อน)
- `rounds/A_20260901_0202_yfbqmg_choosenpc_scene14_hostile_splice_fix_plus_bg4001_navy_training_camp_tenth_door.md`
  (ไฟล์นี้เอง)

-- LANE-A (WORLD) round `yfbqmg`
